"""Importar un plano DXF o IFC al borrador vivo de la hoja (T10, 3e-2; diseno §4.6).

Es el flujo «Importar plano (DXF o IFC)» de la pagina clasica (`ui/paginas/hoja.py:1236-1374`)
hecho servicio sobre la copia `aplicacion.hoja` (Plan C) y sus mismas funciones, sin
reimplementarlas: `subir_plano` (formato antes de escribir, `guardar_subida` con nombre seguro y
`leer_plano`), `leer_plano(ruta, unidades=...)`, `cargar_alturas_desde_texto`,
`declarar_circuitos_desde_texto` y `fusionar_plano`. Contrato de las rutas:
`docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md`.

La importacion NO es parte del borrador hasta fusionarla, como
`st.session_state["hoja_importacion"]` de la clasica: vive aqui, en memoria del proceso, como
mucho UNA por borrador (leer otro plano reemplaza la anterior). Se guarda por el `id` del
borrador, que es aleatorio y solo se alcanza despues de que
`hoja_borradores.obtener(huella, id)` comprobo que es de la ficha; asi la
importacion sigue a su borrador cuando la ficha cambia de huella (`heredar`, cambio de contrasena).
Leer, reanudar, cargar alturas y declarar circuitos comprueban `rev` y NO lo suben; fusionar cambia
el borrador por el mismo nucleo de la edicion (`hoja_edicion._cambiar`: ya guardado, `rev`,
`completar_composiciones` y `reemplazar`, que sube `rev`) y descarta la importacion.

Cada importacion tiene su carpeta temporal (`tempfile.mkdtemp`, prefijo `silice_planos_`,
dentro de `DIRECTORIO_TEMPORAL`): se borra al reemplazarla, descartarla, fusionarla y cuando su
borrador sale del registro por cualquier camino (aviso `hoja_borradores.al_quitar`: descartar,
vencer, topes, olvidar la ficha o el caso). Ninguna ruta se arma con texto del usuario: el nombre
pasa por `guardar_subida`.

Orden de bloqueos (sin abrazo mortal): el cerrojo del borrador, luego el de este registro y, dentro,
el del registro de borradores; nunca al reves. El aviso `al_quitar` llega fuera del cerrojo del
registro de borradores. Leer el plano ocurre con el cerrojo del borrador y sin el de aqui; antes de
dejar la importacion se comprueba, con el cerrojo de aqui, que el borrador sigue en el registro: si
lo descartaron mientras se leia, la carpeta nueva se borra y nada queda.

Sin FastAPI ni Streamlit (RM-1).
"""

from __future__ import annotations

import re
import shutil
import tempfile
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from sqlalchemy.orm import Session

from adapters.espacio.planos import EstadoImportacion, ItemInforme, ResultadoImportacion
from aplicacion import hoja, hoja_borradores, hoja_edicion
from aplicacion.errores import HojaInvalida
from aplicacion.hoja_borradores import BorradorInexistente, BorradorVivo, RevDesactualizado
from aplicacion.subidas import Subida

__all__ = [
    "AVISO_PENDIENTES",
    "DIRECTORIO_TEMPORAL",
    "IMPORTACIONES",
    "MENSAJE_ALTURAS_AJENAS",
    "MENSAJE_CIRCUITOS_AJENOS",
    "MENSAJE_NO_DETENIDA",
    "MENSAJE_SIN_IMPORTACION",
    "MENSAJE_UNIDAD",
    "PREFIJO_CARPETA",
    "Fusion",
    "ImportacionNoFusionable",
    "NoDetenida",
    "SinImportacion",
    "cargar_alturas",
    "declarar_circuitos",
    "descartar",
    "filas_del_informe",
    "fusionar",
    "leer",
    "mensaje_sin_ruta",
    "reanudar",
    "vista_de_fusion",
    "vista_de_importacion",
]

#: Carpeta de los planos (`None`: la temporal del sistema; las pruebas la fijan).
DIRECTORIO_TEMPORAL: str | None = None
PREFIJO_CARPETA = "silice_planos_"

#: Textos de la pagina clasica (`ui/paginas/hoja.py`), copiados con el Plan C (no se importa `ui`).
AVISO_PENDIENTES = (
    "Si fusiona ahora, los ambientes sin altura entran con 2,5 m provisionales y los circuitos "
    "supuestos quedan marcados en la auditoría. Puede cargarlos antes o corregirlos después en las "
    "tablas."
)
MENSAJE_SIN_IMPORTACION = "Vuelva a subir el plano: ya no está disponible."
SUFIJO_ALTURAS = "No se cargó ninguna altura."
SUFIJO_CIRCUITOS = "No se declaró ningún circuito."
RENOMBRE = "Renombre el archivo y vuelva a subirlo."

#: Textos nuevos de la API (la clasica solo ofrecia los campos de lo pendiente).
MENSAJE_UNIDAD = (
    "Elija una unidad de la lista: "
    + ", ".join(hoja.UNIDADES_DE_PLANO[:-1])
    + f" o {hoja.UNIDADES_DE_PLANO[-1]}."
)
MENSAJE_ALTURAS_AJENAS = (
    "Las alturas enviadas no son de los ambientes pendientes de esta importación: vuelva a "
    "cargarla."
)
MENSAJE_CIRCUITOS_AJENOS = (
    "Los circuitos enviados no son los supuestos de esta importación: vuelva a cargarla."
)
MENSAJE_NO_DETENIDA = "Esta importación no está detenida: no hace falta elegir una unidad."
MENSAJE_NO_GUARDADO = f"No se pudo guardar el plano en el servidor. {RENOMBRE}"


class SinImportacion(Exception):  # noqa: N818
    """El borrador no tiene una importacion vigente (o su archivo ya no esta)."""


class NoDetenida(Exception):  # noqa: N818
    """Se pide la unidad del dibujo de una importacion que no la pide."""


class ImportacionNoFusionable(Exception):  # noqa: N818
    """La importacion esta detenida o rechazada: no se fusiona (el texto es el de la clasica)."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


@dataclass(frozen=True, slots=True)
class Importacion:
    """La importacion vigente de un borrador: su carpeta, el archivo guardado y lo que se leyo."""

    carpeta: Path
    ruta: Path
    resultado: ResultadoImportacion


@dataclass(frozen=True, slots=True)
class Fusion:
    """Lo que deja fusionar: el borrador vivo (con su `rev` nuevo) y lo que se muestra."""

    vivo: BorradorVivo
    resultado: ResultadoImportacion
    informe: tuple[ItemInforme, ...]
    resumen: hoja.ResumenDeFusion


def _borrar(carpeta: Path) -> None:
    """Borra la carpeta de un plano. Un archivo abierto por otro hilo (Windows) puede impedirlo: el
    que lo tiene abierto la vuelve a borrar al terminar (`_Importaciones.poner`)."""
    shutil.rmtree(carpeta, ignore_errors=True)


class _Importaciones:
    """Las importaciones vigentes del proceso, una por borrador (por su `id`)."""

    def __init__(self) -> None:
        self._de: dict[str, Importacion] = {}
        self._cerrojo = threading.RLock()

    def vigente(self, vivo: BorradorVivo) -> Importacion | None:
        with self._cerrojo:
            return self._de.get(vivo.id)

    def poner(self, vivo: BorradorVivo, nueva: Importacion) -> None:
        """Deja `nueva` como la importacion de `vivo` si `vivo` sigue en el registro; si no (lo
        descartaron o vencio mientras se leia), borra la carpeta de `nueva` y lanza
        `BorradorInexistente`. La carpeta de la anterior, si es otra, se borra."""
        with self._cerrojo:
            try:
                sigue = hoja_borradores.obtener(vivo.huella, vivo.id) is vivo
            except BorradorInexistente:
                sigue = False
            anterior = self._de.get(vivo.id)
            if sigue:
                self._de[vivo.id] = nueva
        if not sigue:
            _borrar(nueva.carpeta)
            raise BorradorInexistente(vivo.id)
        if anterior is not None and anterior.carpeta != nueva.carpeta:
            _borrar(anterior.carpeta)

    def quitar(self, id_: str) -> None:
        """Olvida la importacion del borrador `id_` y borra su carpeta (idempotente)."""
        with self._cerrojo:
            anterior = self._de.pop(id_, None)
        if anterior is not None:
            _borrar(anterior.carpeta)


IMPORTACIONES = _Importaciones()
hoja_borradores.al_quitar.append(lambda vivo: IMPORTACIONES.quitar(vivo.id))


def _exigir_rev(vivo: BorradorVivo, rev: int) -> None:
    if vivo.rev != rev:
        raise RevDesactualizado(vivo.id)


def _vigente(vivo: BorradorVivo) -> Importacion:
    actual = IMPORTACIONES.vigente(vivo)
    if actual is None:
        raise SinImportacion
    return actual


def mensaje_sin_ruta(archivo: str) -> str:
    """El mensaje que reemplaza al del lector cuando este repite una ruta del servidor."""
    return f"{archivo}: no se pudo leer el plano guardado en el servidor; vuelva a subirlo."


#: Lo que lleva el texto de todo `OSError` con numero de error (`[Errno 13] ...: 'C:\...'`).
_MARCAS_DE_OSERROR = ("[Errno ", "[WinError ")


def _rastros_de_la_raiz(raiz: Path) -> tuple[str, ...]:
    """La raiz temporal y su comienzo (el ancla mas el primer componente, p. ej. la unidad con
    `Users`, o `/tmp`), en las tres escrituras en que puede salir: tal cual, con las barras
    dobladas de `repr` y con barras normales. El comienzo no depende del largo de la raiz: sale aunque el lector recorte el
    texto (`en_una_linea`, 120 caracteres) dentro de ella."""
    comienzo = str(Path(*raiz.parts[:2])) if len(raiz.parts) > 1 else str(raiz)
    rastros = []
    for texto in (str(raiz), comienzo):
        rastros += [texto, texto.replace("\\", "\\\\"), texto.replace("\\", "/")]
    return tuple(rastros)


def _sin_rutas(resultado: ResultadoImportacion, carpeta: Path) -> ResultadoImportacion:
    """El lector repite el texto de su excepcion, recortado a 120 caracteres: un `OSError` trae la
    ruta del servidor. Si el mensaje trae la marca de un `OSError` (`[Errno `, `[WinError `) o un
    rastro de la raiz temporal, se cambia ENTERO por uno fijo. Solo se BUSCAN textos fijos (`in`,
    costo lineal); el mensaje no se reescribe por trozos."""
    mensaje = resultado.mensaje
    if any(m in mensaje for m in (*_MARCAS_DE_OSERROR, *_rastros_de_la_raiz(carpeta.parent))):
        return replace(resultado, mensaje=mensaje_sin_ruta(resultado.archivo))
    return resultado


def leer(vivo: BorradorVivo, rev: int, subida: Subida) -> ResultadoImportacion:
    """P1: guarda el plano subido en una carpeta nueva del borrador y lo lee (`subir_plano`).

    En este orden: `rev` (`RevDesactualizado`), la extension ANTES de escribir nada
    (`HojaInvalida` con el texto de la clasica), la carpeta, el guardado (`HojaInvalida`
    «... Renombre el archivo y vuelva a subirlo.», P:1293-1295) y la lectura (`HojaInvalida` si
    falta el lector). Un archivo corrupto no es error: es un resultado `RECHAZADA`. Reemplaza la
    importacion anterior y su carpeta; si algo falla, la carpeta nueva no queda.
    """
    with vivo.cerrojo:
        _exigir_rev(vivo, rev)
        hoja.formato_de_plano(subida.name or "")
        carpeta = Path(tempfile.mkdtemp(prefix=PREFIJO_CARPETA, dir=DIRECTORIO_TEMPORAL))
        try:
            try:
                ruta, resultado = hoja.subir_plano(subida, carpeta)
            except HojaInvalida:
                raise
            except ValueError as error:  # el nombre no deja nada utilizable (P:1293)
                raise HojaInvalida(f"{error}. {RENOMBRE}") from None
            except OSError:  # su texto trae la ruta del servidor: no se repite
                raise HojaInvalida(MENSAJE_NO_GUARDADO) from None
            resultado = _sin_rutas(resultado, carpeta)
            IMPORTACIONES.poner(vivo, Importacion(carpeta, ruta, resultado))
        except BaseException:
            _borrar(carpeta)
            raise
        return resultado


def reanudar(vivo: BorradorVivo, rev: int, unidades: str) -> ResultadoImportacion:
    """P2: vuelve a leer el plano guardado con la unidad del dibujo (`_continuar_con_unidad`,
    P:1301-1311). `HojaInvalida(MENSAJE_UNIDAD)` si no es una de `UNIDADES_DE_PLANO`;
    `SinImportacion` sin importacion o si su archivo ya no esta en el disco; `NoDetenida` si la
    importacion no pide la unidad (la clasica solo la ofrece entonces: volver a leer perderia las
    alturas y los circuitos ya cargados)."""
    with vivo.cerrojo:
        _exigir_rev(vivo, rev)
        if unidades not in hoja.UNIDADES_DE_PLANO:
            raise HojaInvalida(MENSAJE_UNIDAD)
        actual = _vigente(vivo)
        if not actual.resultado.pide_unidad:
            raise NoDetenida
        if not actual.ruta.is_file():  # alguien limpio la carpeta temporal: como la clasica
            IMPORTACIONES.quitar(vivo.id)
            raise SinImportacion
        resultado = _sin_rutas(hoja.leer_plano(actual.ruta, unidades=unidades), actual.carpeta)
        IMPORTACIONES.poner(vivo, replace(actual, resultado=resultado))
        return resultado


def cargar_alturas(
    vivo: BorradorVivo, rev: int, alturas: Mapping[str, str]
) -> ResultadoImportacion:
    """P3: carga las alturas escritas (`_cargar_alturas_escritas`, P:1319-1330). Solo se aceptan
    ambientes pendientes (como la clasica, que solo ofrece esos campos); uno que falta cuenta como
    en blanco y sigue pendiente. Todo o nada: `HojaInvalida` con el texto de la clasica y
    « No se cargó ninguna altura.», y la importacion queda como estaba."""
    with vivo.cerrojo:
        _exigir_rev(vivo, rev)
        actual = _vigente(vivo)
        pendientes = [i for i, _ in hoja.alturas_pendientes(actual.resultado)]
        if not set(alturas) <= set(pendientes):
            raise HojaInvalida(MENSAJE_ALTURAS_AJENAS)
        textos = {i: alturas.get(i, "") for i in pendientes}
        try:
            resultado = hoja.cargar_alturas_desde_texto(actual.resultado, textos)
        except HojaInvalida as error:
            raise HojaInvalida(f"{error} {SUFIJO_ALTURAS}") from None
        IMPORTACIONES.poner(vivo, replace(actual, resultado=resultado))
        return resultado


def declarar_circuitos(
    vivo: BorradorVivo, rev: int, circuitos: Mapping[str, Sequence[str]]
) -> ResultadoImportacion:
    """P4: declara conductores (fase, neutro, tierra) y puntos maximos de los circuitos supuestos
    (`_declarar_circuitos_escritos`, P:1333-1350). Solo se aceptan circuitos supuestos; los que no
    se envian siguen supuestos. Todo o nada: `HojaInvalida` con el texto de la clasica y
    « No se declaró ningún circuito.»."""
    with vivo.cerrojo:
        _exigir_rev(vivo, rev)
        actual = _vigente(vivo)
        supuestos = {c.id for c in hoja.circuitos_supuestos(actual.resultado)}
        if not set(circuitos) <= supuestos:
            raise HojaInvalida(MENSAJE_CIRCUITOS_AJENOS)
        valores = {i: tuple(v) for i, v in circuitos.items()}
        try:
            resultado = hoja.declarar_circuitos_desde_texto(actual.resultado, valores)  # type: ignore[arg-type]
        except HojaInvalida as error:
            raise HojaInvalida(f"{error} {SUFIJO_CIRCUITOS}") from None
        IMPORTACIONES.poner(vivo, replace(actual, resultado=resultado))
        return resultado


def fusionar(sesion: Session, vivo: BorradorVivo, rev: int) -> Fusion:
    """P5: funde la importacion con el espacio del borrador (`_fusionar_importacion`,
    P:1353-1374) por el nucleo comun de la edicion: ya guardado (`BorradorYaGuardado`), `rev`,
    `SinImportacion`, una importacion detenida o rechazada (`ImportacionNoFusionable` con el texto
    de la clasica) o un espacio que no vale (`HojaInvalida`/`ValueError`); y, si cambia,
    `completar_composiciones` y `reemplazar` (sube `rev`). Luego descarta la importacion."""
    hechas: dict[str, object] = {}

    def construir(actual: BorradorVivo) -> hoja.Borrador:
        importacion = _vigente(actual)
        try:
            nuevo, informe = hoja.fusionar_plano(actual.borrador, importacion.resultado)
        except HojaInvalida as error:
            if importacion.resultado.estado is not EstadoImportacion.IMPORTADA:
                raise ImportacionNoFusionable(str(error)) from None
            raise
        hechas.update(resultado=importacion.resultado, informe=informe)
        return nuevo

    with vivo.cerrojo:
        fundido = hoja_edicion._cambiar(sesion, vivo.huella, vivo.id, rev, construir)
        IMPORTACIONES.quitar(vivo.id)
    resultado: ResultadoImportacion = hechas["resultado"]  # type: ignore[assignment]
    informe: tuple[ItemInforme, ...] = hechas["informe"]  # type: ignore[assignment]
    return Fusion(fundido, resultado, informe, hoja.resumen_de_la_fusion(resultado, informe))


def descartar(vivo: BorradorVivo) -> None:
    """P6: olvida la importacion del borrador y borra su carpeta (idempotente; P:1314-1316)."""
    with vivo.cerrojo:
        IMPORTACIONES.quitar(vivo.id)


# --- lo que se muestra ----------------------------------------------------------------------------


#: La referencia interna de un mensaje del lector, p. ej. `(SF5-1, SF5-2)`: la misma de
#: `hoja._REFERENCIA_INTERNA` SIN el `\s*` inicial, que hace cuadratica la sustitucion de la
#: clasica ante una corrida larga de espacios (100 000 espacios: decenas de segundos).
_REFERENCIA = re.compile(r"\((?:SF\d+-\d+(?:,\s*)?)+\)")


def _sin_referencias(mensaje: str) -> str:
    """`hoja._REFERENCIA_INTERNA.sub("", mensaje)` en tiempo lineal: quita cada referencia y los
    espacios que la preceden (los que toma la clase de espacios de `re`, que con texto es la
    misma que `str.isspace`). Solo actua en la ranura de la referencia; el resto queda igual."""
    trozos: list[str] = []
    desde = 0
    for coincidencia in _REFERENCIA.finditer(mensaje):
        trozos.append(mensaje[desde : coincidencia.start()].rstrip())
        desde = coincidencia.end()
    trozos.append(mensaje[desde:])
    return "".join(trozos)


def filas_del_informe(informe: Sequence[ItemInforme]) -> list[dict[str, str]]:
    """Las filas de `hoja.filas_del_informe` (mismos rotulos y textos; prueba de paridad con la
    clasica) con las claves de la API, `tipo`, `referencia`, `fila` y `mensaje`, en tiempo
    lineal (el mensaje sale del plano subido)."""
    return [
        {
            "tipo": hoja.ROTULOS_DEL_INFORME[i.tipo],
            "referencia": i.referencia,
            "fila": i.fila,
            "mensaje": _sin_referencias(i.mensaje),
        }
        for i in informe
    ]


def vista_de_importacion(resultado: ResultadoImportacion) -> dict:
    """Lo que pinta `_pintar_importacion` (P:1442-1461): estado, mensaje, unidad pedida, los
    conteos, el informe, lo pendiente y el aviso. Todo como texto o entero."""
    alturas = hoja.alturas_pendientes(resultado)
    circuitos = hoja.circuitos_supuestos(resultado)
    return {
        "estado": resultado.estado.value,
        "archivo": resultado.archivo,
        "mensaje": resultado.mensaje or "",
        "pide_unidad": resultado.pide_unidad,
        "unidades": list(hoja.UNIDADES_DE_PLANO) if resultado.pide_unidad else [],
        "conteos": [
            {"rotulo": r, "cantidad": n} for r, n in hoja.resumen_de_importacion(resultado)
        ],
        "informe": filas_del_informe(resultado.informe),
        "alturas_pendientes": [{"id": i, "nombre": n} for i, n in alturas],
        "circuitos_supuestos": [
            {
                "id": c.id,
                "fase": str(c.conductores[0]),
                "neutro": str(c.conductores[1]),
                "tierra": str(c.conductores[2]),
                "puntos": str(c.puntos_maximos),
            }
            for c in circuitos
        ],
        "aviso_pendientes": AVISO_PENDIENTES if alturas or circuitos else None,
    }


def vista_de_fusion(fusion: Fusion) -> dict:
    """El informe de la ultima fusion (P:1480-1485) y el mensaje de exito (P:1367-1373)."""
    filas = fusion.resultado.filas
    return {
        "fusion": {
            "por_tipo": [{"rotulo": r, "cantidad": n} for r, n in fusion.resumen.por_tipo],
            "filas_por_tabla": [
                {"rotulo": r, "cantidad": n} for r, n in fusion.resumen.filas_por_tabla
            ],
            "origenes": fusion.resumen.origenes,
        },
        "informe": filas_del_informe(fusion.informe),
        "mensaje": (
            f"Se fusionó «{fusion.resultado.archivo}» con el borrador de la hoja: "
            f"{filas['esp_ambientes']} ambientes, {filas['esp_fuentes']} fuentes y "
            f"{filas['esp_puntos']} puntos. Revise las filas en las tablas de abajo; la auditoría "
            "las evalúa como a las demás. Todavía no se guardó ninguna versión: use Guardar "
            "versión cuando esté conforme."
        ),
    }
