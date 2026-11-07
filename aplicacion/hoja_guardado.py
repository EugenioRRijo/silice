"""Guardar el borrador vivo de la hoja como version en la base del caso (T10, 3d-1; diseno §4.5).

Es el botón «Guardar version» / «Guardar primera version» de la pagina clasica (`_guardar` y
`_guardar_primera`, P:472-545) hecho servicio. La primera ruta de la hoja que ESCRIBE versiones,
y por eso la que cuida cuatro cosas:

* **Una sola transaccion que empieza con `BEGIN IMMEDIATE`.** La sesion que llega es la de
  `core.catalog.abrir_sesion_de_escritura` (SL-E12): su primera sentencia toma el bloqueo de
  escritura ANTES de leer la version vigente y el ultimo codigo. Asi la comprobacion de «hay una
  version mas nueva», `siguiente_codigo` y la escritura son atomicas respecto de otra persona que
  guarda a la vez (el segundo espera y ve lo del primero). Nada de esto toca la base antes de la
  primera lectura: las comprobaciones que no necesitan la base (ya guardado, `rev`, fuente, sin
  cambios, solo lectura) van antes y no abren transaccion.
* **La sesion envuelta en `con_anexos_de_cadena`** (diseno §1.2): sin ella, la cadena sella la
  version con «anexos ninguno» y `verificar_cadena` la da por rota si copio filas `esp_*`.
  Se envuelve AQUI, para que ninguna ruta pueda olvidarlo.
* **Todo o nada.** `guardar_version` y `crear_primera_version` confirman o deshacen; lo que este
  modulo comprueba antes de llamarlas deshace la transaccion abierta.
* **R17 en lo que se guarda.** El borrador se liga a la conexion de SU espacio (`con_r17`, el
  `_con_conexion` de la clasica) antes de guardar; la version conserva el hallazgo.

Una peticion a la vez por borrador (su cerrojo). El responsable es siempre el de la sesion (RF-82).
Despues de guardar el borrador queda cerrado (`guardado_como`): ni se edita ni se guarda otra vez.

Diferencia deliberada con la clasica (D-5): la clasica guardaba «de la version abierta» aunque ya
existiera una mas nueva (la nueva quedaba vigente sin lo de la otra persona); aqui hace falta
confirmarlo. La regla (afinada por Eugenio el 2026-10-21) es la de `hoja_vista.version_mas_nueva`,
la misma del `Resumen`: la vigente de AHORA es otra que la vigente AL ABRIR el borrador
(`BorradorVivo.vigente_al_abrir`). Abrir a proposito una version vieja o descartada no pide
confirmar si nadie guardo entretanto, y el texto «Otra persona guardó la versión X…» es cierto.

Tarea 9 (montar un presupuesto): la primera version de una obra se valora con
`lista_para_el_proyecto` (la lista para armar de la carpeta o, si la obra esta en la otra moneda,
su conversion de alcance proyecto con la tasa del BCV, que se escribe en la misma transaccion); sin
tasa de los ultimos 7 dias o sin lista, `SinListaDeLaObra` y nada se guarda. Su codigo se puede
elegir («VIV-001»); las siguientes siguen la numeracion. Las notas de medicion se guardan con la
version (`hoja.guardar_version` y `hoja.crear_primera_version`).

Tarea 10 de F4 (registro de importaciones): las importaciones anotadas en el borrador (plano
fusionado, cómputo llevado) se escriben con la versión, en esta misma transaccion
(`importaciones.con_la_version` las engancha al `commit` de `guardar_version` y de
`crear_primera_version`, sin tocar `aplicacion/hoja.py`): si algo falla no queda ni la version ni
el registro.

Sin FastAPI ni Streamlit (RM-1).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from aplicacion import hoja, hoja_borradores, hoja_vista, importaciones
from aplicacion.entrega import con_anexos_de_cadena
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import BorradorVivo, RevDesactualizado
from aplicacion.hoja_edicion import BorradorYaGuardado, SinListaDeLaObra
from aplicacion.listas_para_armar import SinListaParaArmar, lista_para_el_proyecto
from aplicacion.plural import plural
from core.catalog import Catalogo

__all__ = [
    "CODIGO_SOLO_PRIMERA",
    "MENSAJE_SOLO_LECTURA",
    "BorradorYaGuardado",
    "Guardado",
    "RevDesactualizado",
    "SinListaDeLaObra",
    "VersionMasNueva",
    "VersionSoloLectura",
    "guardar",
]

#: El texto de H:1849: la version tiene una partida sin composicion vigente en el catalogo.
MENSAJE_SOLO_LECTURA = (
    "Esta versión está en solo lectura: alguna de sus partidas ya no tiene composición vigente "
    "en el catálogo, así que recalcularla cambiaría sus precios."
)
CODIGO_SOLO_PRIMERA = (
    "El código se elige solo al guardar la primera versión; las siguientes siguen su numeración."
)


class VersionSoloLectura(Exception):  # noqa: N818
    """La version abierta es de solo lectura (recalcularla cambiaria sus precios)."""


class VersionMasNueva(Exception):  # noqa: N818
    """Otra persona guardo una version despues de que esta se abrio y no se confirmo."""

    def __init__(self, vigente: str, abierta: str) -> None:
        super().__init__(vigente, abierta)
        self.vigente = vigente
        self.abierta = abierta

    def __str__(self) -> str:
        return (
            f"Otra persona guardó la versión {self.vigente} después de que usted abrió la "
            f"{self.abierta}. Si guarda, su versión saldrá de la {self.abierta} y quedará como "
            f"vigente sin lo de la {self.vigente}."
        )


@dataclass(frozen=True, slots=True)
class Guardado:
    """Lo que dejo S1: la version creada, cuantas celdas registro, su total y el aviso."""

    codigo: str
    proyecto: str
    cambios: int
    total: hoja_vista.Monto
    primera: bool
    mensaje: str


def _mensaje(codigo: str, cambios: int, total: hoja_vista.Monto, proyecto: str, primera: bool):
    if primera:
        return (
            f"Se guardó la primera versión {codigo} de la obra {proyecto} (total {total.texto}). "
            "Quedó registrada su creación, con su fuente y su responsable."
        )
    registrados = plural(cambios, "cambio registrado", "cambios registrados")
    return f"Se guardó la versión {codigo} con {registrados}."


def guardar(
    sesion: Session,
    huella: str,
    id: str,
    rev: int,
    *,
    fuente: str,
    responsable: str,
    confirmar_version_mas_nueva: bool = False,
    codigo: str | None = None,
) -> Guardado:
    """Guarda el borrador `id` de la ficha `huella` como version nueva (o como la primera si el
    proyecto no tenia versiones, con el `codigo` elegido o el siguiente) y lo cierra.

    `sesion` debe ser la de escritura de `abrir_sesion_de_escritura`. Lanza `BorradorInexistente`,
    `BorradorYaGuardado`, `RevDesactualizado`, `HojaInvalida` (sin cambios, sin fuente, hoja vacia,
    el proyecto ya tiene versiones, otra moneda: el texto de la clasica; un `codigo` para una
    version que no es la primera), `SinListaDeLaObra` (la primera, sin lista o sin tasa),
    `VersionSoloLectura`, `VersionMasNueva`, y lo que levante el nucleo (`ValueError`,
    `CatalogoIncompleto`, `SQLAlchemyError`) tras deshacer la transaccion.
    """
    con_anexos_de_cadena(sesion)  # el sello de lo que se escriba cubre el espacio (§1.2)
    # `guardar_version` lee `nueva.codigo` DESPUES de confirmar: con la expiracion por omision eso
    # abriria otra transaccion (otro `BEGIN IMMEDIATE`, de lectura) que retendria el bloqueo de
    # escritura hasta cerrar la sesion y haria esperar a la siguiente persona sin motivo.
    sesion.expire_on_commit = False
    vivo = hoja_borradores.obtener(huella, id)
    with vivo.cerrojo:
        if vivo.guardado_como is not None:
            raise BorradorYaGuardado(vivo.guardado_como)
        if vivo.rev != rev:
            raise RevDesactualizado(id)
        borrador = hoja_vista.con_r17(vivo.borrador)
        if vivo.abierta is None:
            guardado = _primera(sesion, vivo, borrador, fuente, responsable, codigo)
        elif codigo is not None:
            raise HojaInvalida(CODIGO_SOLO_PRIMERA)
        else:
            guardado = _version(
                sesion, vivo, borrador, fuente, responsable, confirmar_version_mas_nueva
            )
        vivo.guardado_como = guardado.codigo
        return guardado


def _version(
    sesion: Session,
    vivo: BorradorVivo,
    borrador: hoja.Borrador,
    fuente: str,
    responsable: str,
    confirmar: bool,
) -> Guardado:
    abierta = vivo.abierta
    assert abierta is not None
    motivo = hoja.motivo_para_no_guardar(abierta.borrador, borrador, fuente, responsable)
    if motivo is not None:
        raise HojaInvalida(motivo)
    if abierta.solo_lectura:
        raise VersionSoloLectura(MENSAJE_SOLO_LECTURA)
    try:
        if not confirmar:  # la primera lectura: antes, `BEGIN IMMEDIATE` (la sesion de escritura)
            mas_nueva = hoja_vista.version_mas_nueva(
                vivo, hoja.codigo_vigente(sesion, vivo.proyecto)
            )
            if mas_nueva is not None:
                raise VersionMasNueva(mas_nueva, abierta.codigo)
        with importaciones.con_la_version(sesion, vivo):  # F4 T10: el registro viaja con la version
            guardada = hoja.guardar_version(
                sesion, Catalogo(sesion), abierta, borrador, fuente=fuente, responsable=responsable
            )
    except BaseException:
        sesion.rollback()  # guardar_version ya deshizo lo suyo; esto cubre lo de antes
        raise
    assert guardada is not None  # `motivo_para_no_guardar` ya exigio cambios
    total = hoja_vista.monto(guardada.total)
    return Guardado(
        codigo=guardada.codigo,
        proyecto=vivo.proyecto,
        cambios=guardada.cambios,
        total=total,
        primera=False,
        mensaje=_mensaje(guardada.codigo, guardada.cambios, total, vivo.proyecto, False),
    )


def _primera(
    sesion: Session,
    vivo: BorradorVivo,
    borrador: hoja.Borrador,
    fuente: str,
    responsable: str,
    codigo: str | None,
) -> Guardado:
    motivo = hoja.motivo_para_no_crear_primera(borrador, fuente, responsable)
    if motivo is not None:
        raise HojaInvalida(motivo)
    try:
        # la primera lectura: antes, `BEGIN IMMEDIATE`; la conversion (si la obra esta en la otra
        # moneda) queda en esta transaccion y se confirma o se deshace con la version
        try:
            lista = lista_para_el_proyecto(
                sesion, vivo.proyecto, borrador.fecha, responsable=responsable
            )
        except SinListaParaArmar as error:
            raise SinListaDeLaObra(str(error)) from None
        # los APU con los precios de la lista que la version declara (su tasa y su fecha), aunque
        # al agregar se hayan valorado con otra (una tasa del BCV llegada despues)
        try:
            borrador = hoja.con_precios_de_la_lista(Catalogo(sesion), borrador, lista)
        except hoja.ApuSinPreciosDeLaLista as error:
            raise SinListaDeLaObra(str(error)) from None
        with importaciones.con_la_version(sesion, vivo):  # F4 T10: el registro viaja con la version
            guardada = hoja.crear_primera_version(
                sesion,
                Catalogo(sesion),
                vivo.proyecto,
                borrador,
                codigo=codigo,
                fuente=fuente,
                responsable=responsable,
                lista=lista,
            )
    except BaseException:
        sesion.rollback()
        raise
    total = hoja_vista.monto(guardada.total)
    return Guardado(
        codigo=guardada.codigo,
        proyecto=vivo.proyecto,
        cambios=guardada.cambios,
        total=total,
        primera=True,
        mensaje=_mensaje(guardada.codigo, guardada.cambios, total, vivo.proyecto, True),
    )
