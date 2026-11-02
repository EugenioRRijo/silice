"""Los tramos viales guardados por versión (plan vial, Tarea 8).

Cada versión de una obra puede llevar los tramos de su vía (`adapters.vial.Tramo`). Se guardan en
la base del caso (`aplicacion/tablas_vial.py`) y se leen idénticos: las cifras son `Decimal` y se
persisten como texto, así que el «7.30» vuelve como «7.30».

- **Nada se sobrescribe.** Guardar otra vez los tramos de una versión inserta un guardado nuevo con
  su usuario, su hora y su fuente; al leer manda el último y los anteriores quedan en la base como
  rastro. (La Hoja tampoco pisa una versión: cada cambio es una versión nueva. Los tramos no
  forman parte del sello de la versión: son un anexo suyo, como el estudio de mercado.)
- **Herencia al leer, sin copiar.** Una versión sin guardado propio usa el último guardado de la
  versión anterior más cercana de la misma obra que tenga uno (`heredados_de` dice cuál). Leer no
  escribe filas ni cuenta como guardado de nadie. Para que lo heredado no cambie bajo los pies de
  una versión posterior, solo se guardan tramos en la versión más reciente de la obra.
- **Versión enviada, aprobada o devuelta: no se edita** (`VersionBloqueada`, la API responde 409).
  Solo se editan los tramos de una versión guardada o cuyo envío se retiró. La Hoja no crea ese
  bloqueo por sí sola (cada edición suya ya es una versión nueva); aquí sí hace falta porque los
  tramos se guardan sobre la misma versión que ve quien aprueba.
- **Todo o nada.** Un guardado que falla no deja filas; `guardar_tramos` confirma al terminar.
- **Importar un CSV** (`tramos_desde_csv`) lee con `adapters.vial.leer_tramos`: un solo error de
  cualquier fila y no se guarda nada; el mensaje nombra la fila como la numera una hoja de cálculo.
  Aplica los mismos topes que la API (`MAX_TRAMOS`, `MAX_CAPAS`, `MAX_LINEAS_DE_DEMARCACION`).
- **Llevar al presupuesto** (Tarea 8b) vive en `aplicacion/hoja_vial.py`: este módulo lo importa
  la Hoja (`reglas_viales`) y no puede importarla a ella.
- **La fórmula de trabajo de VR2** (Tarea 16b, filas 58 y 63; `formulas_de_trabajo`): por cada
  partida de mezcla que dan los tramos (carpeta y bacheo), su APU en el catálogo de la carpeta dice
  qué mezcla propia usa (la línea «Costo propio de mezcla <producto>», la de la publicación); la
  receta **vigente** de ese producto sale de la base de la instalación, y el ligante es su único
  componente comprado en t (la fórmula, su cantidad por tonelada × 100). No se adivina: si el APU
  no usa una mezcla propia o usa varias, si no hay receta vigente, o si la receta no tiene un único
  comprado en t, esa partida queda sin fórmula y el motivo va a VR2, que lo declara. La
  instalación solo se abre si algún APU usa una mezcla propia. El porcentaje que se compara lo
  declara la capa (`Capa.asfalto_pct`, columna `asfalto_pct` del CSV).

Cuándo se hace cada cosa lo decide quien llama: aquí no hay reloj ni usuario implícitos, salvo
la fecha con que `reglas_viales` busca la receta vigente cuando la Hoja abre una versión sin pasarla
(fila 110 de las preguntas: esa llamada es parte del experimento congelado).
"""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Sequence
from contextlib import AbstractContextManager, ExitStack
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Demarcacion, Tramo
from adapters.vial.reglas import ReglasViales
from adapters.vial.tabular import leer_tramos
from aplicacion import aprobaciones
from aplicacion.cifras import texto_de_cifra
from aplicacion.costo_propio import PREFIJO_DE_MEZCLA, descripcion_de_costo_propio
from aplicacion.proyectos import resolver_proyecto
from aplicacion.tablas_vial import (
    GuardadoDeTramos,
    TramoGuardado,
    crear_esquema_vial,
    hay_tablas_viales,
)
from core import models
from core.catalog import Catalogo
from produccion.receta import Receta, receta_vigente

__all__ = [
    "MAX_CAPAS",
    "MAX_LINEAS_DE_DEMARCACION",
    "MAX_TRAMOS",
    "CantidadVial",
    "RastroDeGuardado",
    "VersionBloqueada",
    "VersionInexistente",
    "bloqueo_de_version",
    "cantidades_de_tramos",
    "formula_asfalto_de_receta",
    "formulas_de_trabajo",
    "guardado_de_version",
    "heredados_de",
    "guardar_tramos",
    "obras_con_tramos",
    "reglas_viales",
    "texto_decimal",
    "tramos_de_version",
    "tramos_desde_csv",
    "version_de",
]

#: Cómo se dice el estado de una versión que ya no admite cambios en sus tramos.
_NO_EDITABLES = {
    "en_aprobacion": "en aprobación",
    "aprobada": "aprobada",
    "aprobada_con_observaciones": "aprobada con observaciones",
    "devuelta": "devuelta",
}

LARGO_FUENTE = 300
LARGO_USUARIO = 200
#: Topes de lo que se guarda de una vez, por la API o desde un CSV (Tarea 8b, menor 2 del árbitro).
MAX_TRAMOS = 2000
MAX_CAPAS = 50
MAX_LINEAS_DE_DEMARCACION = 20
_NOMBRE_INVALIDO = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class VersionInexistente(LookupError):  # noqa: N818
    """La obra o la versión no existen en este caso (la API responde 404)."""


class VersionBloqueada(ValueError):  # noqa: N818
    """La versión ya no admite cambios en sus tramos (la API responde 409)."""


@dataclass(frozen=True, slots=True)
class RastroDeGuardado:
    """Quién guardó los tramos de una versión, cuándo y de dónde salieron."""

    usuario: str
    fecha_hora: datetime
    fuente: str


@dataclass(frozen=True, slots=True)
class CantidadVial:
    """Una cantidad de obra derivada de un tramo, con el origen y la regla que la producen."""

    tramo: str
    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    origen_id: str
    regla: str


def texto_decimal(valor: Decimal) -> str:
    """El decimal en notación fija y sin ceros de sobra («857.75», «7300»), sin redondear nada."""
    texto = format(valor, "f")
    return texto.rstrip("0").rstrip(".") if "." in texto else texto


# --- resolver la versión --------------------------------------------------------------------------


def version_de(sesion: Session, proyecto: str, codigo: str) -> int:
    """El `id` de la versión `codigo` de la obra `proyecto` (su código de `/v1/proyectos` o su
    nombre). `VersionInexistente` con el texto que se le dice a la persona si no existe."""
    obra = resolver_proyecto(sesion, proyecto)
    if obra is None:
        raise VersionInexistente(f"El proyecto «{proyecto}» no existe en este caso.")
    id_ = sesion.scalars(
        select(models.Presupuesto.id).where(
            models.Presupuesto.proyecto_id == obra.id, models.Presupuesto.codigo == codigo
        )
    ).first()
    if id_ is None:
        raise VersionInexistente(f"La versión {codigo} no existe en la obra «{obra.nombre}».")
    return id_


def _presupuesto(sesion: Session, version_id: int) -> models.Presupuesto:
    presupuesto = sesion.get(models.Presupuesto, version_id)
    if presupuesto is None:
        raise VersionInexistente(f"La versión n.º {version_id} no existe en este caso.")
    return presupuesto


def bloqueo_de_version(sesion: Session, version_id: int) -> str | None:
    """Por qué los tramos de la versión ya no se editan, o `None` si se pueden editar. Solo se
    editan los de la versión más reciente de la obra (las anteriores quedan fijas, así lo que una
    versión nueva hereda no cambia) y, en ella, mientras no se haya enviado a aprobación."""
    presupuesto = _presupuesto(sesion, version_id)
    obra = sesion.get(models.Proyecto, presupuesto.proyecto_id)
    if obra is None:  # una versión sin obra no existe a efectos de la API
        raise VersionInexistente(f"La versión n.º {version_id} no existe en este caso.")
    reciente = sesion.scalars(
        select(models.Presupuesto)
        .where(models.Presupuesto.proyecto_id == obra.id)
        .order_by(models.Presupuesto.id.desc())
    ).first()
    if reciente is not None and reciente.id != presupuesto.id:
        return f"Solo se editan los tramos de la versión más reciente ({reciente.codigo})."
    estado = aprobaciones.estados(sesion, obra.nombre)[presupuesto.codigo].estado
    texto = _NO_EDITABLES.get(estado)
    if texto is None:
        return None
    return (
        f"La versión {presupuesto.codigo} está {texto}: sus tramos ya no se editan. Guarde una "
        "versión nueva y cargue los tramos allí."
    )


# --- guardar y leer -------------------------------------------------------------------------------


def _capas_a_texto(capas: Sequence[Capa]) -> str:
    return json.dumps(
        [
            {
                "tipo": c.tipo,
                "espesor_m": None if c.espesor_m is None else str(c.espesor_m),
                "densidad_t_m3": None if c.densidad_t_m3 is None else str(c.densidad_t_m3),
                "dosis_l_m2": None if c.dosis_l_m2 is None else str(c.dosis_l_m2),
                # Tarea 16b: solo si la capa lo declara, así lo guardado antes no cambia
                **({} if c.asfalto_pct is None else {"asfalto_pct": str(c.asfalto_pct)}),
            }
            for c in capas
        ],
        ensure_ascii=False,
    )


def _capas_de_texto(texto: str) -> tuple[Capa, ...]:
    def cifra(valor: str | None) -> Decimal | None:
        return None if valor is None else Decimal(valor)

    return tuple(
        Capa(
            c["tipo"],
            cifra(c["espesor_m"]),
            cifra(c["densidad_t_m3"]),
            cifra(c["dosis_l_m2"]),
            cifra(c.get("asfalto_pct")),
        )
        for c in json.loads(texto)
    )


def _demarcacion_a_texto(demarcacion: Sequence[Demarcacion]) -> str:
    return json.dumps([{"tipo": d.tipo, "lineas": d.lineas} for d in demarcacion])


def _demarcacion_de_texto(texto: str) -> tuple[Demarcacion, ...]:
    return tuple(Demarcacion(d["tipo"], d["lineas"]) for d in json.loads(texto))


def guardar_tramos(
    sesion: Session,
    version_id: int,
    tramos: Sequence[Tramo],
    *,
    usuario: str,
    ahora: datetime,
    fuente: str = "",
) -> None:
    """Guarda `tramos` como los de la versión `version_id` y confirma. Es un guardado nuevo: el
    anterior no se borra. `VersionInexistente`, `VersionBloqueada` y `ValueError` (un id de tramo
    repetido, un usuario o una fuente demasiado largos); en cualquier fallo no queda nada."""
    try:
        _presupuesto(sesion, version_id)
        bloqueo = bloqueo_de_version(sesion, version_id)
        if bloqueo is not None:
            raise VersionBloqueada(bloqueo)
        _validar(tramos, usuario, fuente)
        if not hay_tablas_viales(sesion):
            crear_esquema_vial(sesion.connection())
        guardado = GuardadoDeTramos(
            version_id=version_id, usuario=usuario, fecha_hora=ahora, fuente=fuente
        )
        sesion.add(guardado)
        sesion.flush()
        for orden, tramo in enumerate(tramos, start=1):
            sesion.add(
                TramoGuardado(
                    guardado_id=guardado.id,
                    orden=orden,
                    tramo_id=tramo.id,
                    progresiva_ini_km=tramo.progresiva_ini_km,
                    progresiva_fin_km=tramo.progresiva_fin_km,
                    ancho_m=tramo.ancho_m,
                    distancia_planta_km=tramo.distancia_planta_km,
                    capas=_capas_a_texto(tramo.capas),
                    demarcacion=_demarcacion_a_texto(tramo.demarcacion),
                )
            )
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise


def _validar(tramos: Sequence[Tramo], usuario: str, fuente: str) -> None:
    vistos: set[str] = set()
    for tramo in tramos:
        if tramo.id in vistos:
            raise ValueError(f"el tramo {tramo.id} está repetido: cada tramo lleva un id propio")
        vistos.add(tramo.id)
    if len(usuario) > LARGO_USUARIO:
        raise ValueError(f"el usuario pasa de {LARGO_USUARIO} caracteres")
    if len(fuente) > LARGO_FUENTE:
        raise ValueError(f"la fuente pasa de {LARGO_FUENTE} caracteres")


def _propio(sesion: Session, version_id: int) -> GuardadoDeTramos | None:
    """El último guardado de la versión misma, sin herencia."""
    if not hay_tablas_viales(sesion):
        return None
    return sesion.scalars(
        select(GuardadoDeTramos)
        .where(GuardadoDeTramos.version_id == version_id)
        .order_by(GuardadoDeTramos.id.desc())
    ).first()


def _vigente(sesion: Session, version_id: int) -> tuple[GuardadoDeTramos | None, str | None]:
    """El guardado que vale para la versión y, si no es el suyo, el código de la versión de la que
    se hereda. Una versión sin guardado propio usa el último guardado de la versión anterior más
    cercana de la misma obra que tenga uno. Heredar no copia ni escribe nada."""
    propio = _propio(sesion, version_id)
    if propio is not None:
        return propio, None
    presupuesto = _presupuesto(sesion, version_id)
    anteriores = sesion.execute(
        select(models.Presupuesto.id, models.Presupuesto.codigo)
        .where(
            models.Presupuesto.proyecto_id == presupuesto.proyecto_id,
            models.Presupuesto.id < version_id,
        )
        .order_by(models.Presupuesto.id.desc())
    )
    for id_, codigo in anteriores:
        guardado = _propio(sesion, id_)
        if guardado is not None:
            return guardado, codigo
    return None, None


def heredados_de(sesion: Session, version_id: int) -> str | None:
    """El código de la versión de la que la versión hereda sus tramos, o `None` si tiene los suyos
    o no hay ninguno que heredar."""
    _presupuesto(sesion, version_id)
    return _vigente(sesion, version_id)[1]


def guardado_de_version(sesion: Session, version_id: int) -> RastroDeGuardado | None:
    """Quién, cuándo y de dónde salió el guardado que vale para la versión (el propio o el
    heredado); `None` si no hay."""
    _presupuesto(sesion, version_id)
    ultimo = _vigente(sesion, version_id)[0]
    if ultimo is None:
        return None
    return RastroDeGuardado(ultimo.usuario, ultimo.fecha_hora, ultimo.fuente)


def tramos_de_version(sesion: Session, version_id: int) -> list[Tramo]:
    """Los tramos que valen para la versión, en su orden: los de su último guardado o, si no tiene
    uno propio, los de la versión anterior más cercana que lo tenga (`heredados_de`); vacío si
    ninguna lo tiene."""
    _presupuesto(sesion, version_id)
    ultimo = _vigente(sesion, version_id)[0]
    if ultimo is None:
        return []
    filas = sesion.scalars(
        select(TramoGuardado)
        .where(TramoGuardado.guardado_id == ultimo.id)
        .order_by(TramoGuardado.orden)
    )
    return [
        Tramo(
            f.tramo_id,
            f.progresiva_ini_km,
            f.progresiva_fin_km,
            f.ancho_m,
            _capas_de_texto(f.capas),
            _demarcacion_de_texto(f.demarcacion),
            f.distancia_planta_km,
        )
        for f in filas
    ]


def obras_con_tramos(sesion: Session) -> list[int]:
    """Los `id` de las obras que tienen alguna versión con tramos en su último guardado."""
    if not hay_tablas_viales(sesion):
        return []
    ultimos = select(func.max(GuardadoDeTramos.id)).group_by(GuardadoDeTramos.version_id)
    con_tramos = (
        select(GuardadoDeTramos.version_id)
        .join(TramoGuardado, TramoGuardado.guardado_id == GuardadoDeTramos.id)
        .where(GuardadoDeTramos.id.in_(ultimos))
    )
    return sorted(
        set(
            sesion.scalars(
                select(models.Presupuesto.proyecto_id).where(models.Presupuesto.id.in_(con_tramos))
            )
        )
    )


# --- cantidades y CSV -----------------------------------------------------------------------------


def cantidades_de_tramos(tramos: Sequence[Tramo]) -> list[CantidadVial]:
    """Las cantidades de obra de `tramos` (las de `adapters.vial.derivar_tramos`), cada una con su
    tramo, su origen y la regla que la produce."""
    return [
        CantidadVial(
            tramo=item.origen_id.split(":")[1],
            codigo=item.codigo_partida,
            descripcion=item.descripcion,
            unidad=item.unidad,
            cantidad=item.cantidad,
            origen_id=item.origen_id,
            regla=item.regla or "",
        )
        for item in derivar_tramos(tramos)
    ]


def tramos_desde_csv(contenido: bytes, nombre: str) -> list[Tramo]:
    """Los tramos del CSV `contenido` (formato de `data/samples/vial/README.md`). Todo o nada:
    un error en cualquier fila es un `ValueError` que nombra el archivo y la fila."""
    limpio = _NOMBRE_INVALIDO.sub("_", nombre.replace("\\", "/").rsplit("/", 1)[-1]).strip()
    seguro = (limpio or "tramos.csv")[:100]
    with tempfile.TemporaryDirectory(prefix="silice-tramos-") as carpeta:
        ruta = Path(carpeta) / seguro
        ruta.write_bytes(contenido)
        try:
            tramos = leer_tramos(ruta)
        except ValueError as error:
            raise ValueError(str(error).replace(repr(seguro), repr(nombre[:100]))) from None
    _dentro_de_los_topes(tramos, nombre[:100])
    return tramos


def _dentro_de_los_topes(tramos: Sequence[Tramo], nombre: str) -> None:
    """`ValueError` que dice el tope si el archivo trae más tramos, o un tramo más capas o líneas
    de demarcación, de los que acepta la API."""
    if len(tramos) > MAX_TRAMOS:
        raise ValueError(
            f"el archivo {nombre!r} tiene {texto_de_cifra(Decimal(len(tramos)))} tramos: el máximo "
            f"es {texto_de_cifra(Decimal(MAX_TRAMOS))}. Divídalo en varios."
        )
    for tramo in tramos:
        if len(tramo.capas) > MAX_CAPAS:
            raise ValueError(
                f"el archivo {nombre!r}, tramo {tramo.id}: tiene {len(tramo.capas)} capas; el "
                f"máximo es {MAX_CAPAS}."
            )
        if len(tramo.demarcacion) > MAX_LINEAS_DE_DEMARCACION:
            raise ValueError(
                f"el archivo {nombre!r}, tramo {tramo.id}: tiene {len(tramo.demarcacion)} líneas "
                f"de demarcación; el máximo es {MAX_LINEAS_DE_DEMARCACION}."
            )


# --- reglas del auditor ---------------------------------------------------------------------------

#: Partidas de mezcla asfáltica cuyo porcentaje de asfalto mide VR2.
_PARTIDAS_DE_MEZCLA = (PARTIDAS_VIALES["carpeta_mezcla"][0], PARTIDAS_VIALES["bacheo_mezcla"][0])
#: «Costo propio de mezcla »: lo que precede al producto en la línea del APU de una mezcla propia.
_LINEA_DE_MEZCLA_PROPIA = descripcion_de_costo_propio(PREFIJO_DE_MEZCLA)


def _abrir_instalacion() -> AbstractContextManager[Session]:
    """La base de la instalación (importada aquí: solo hace falta si un APU usa mezcla propia)."""
    from operacion.instalacion import sesion_de_instalacion

    return sesion_de_instalacion()


def formula_asfalto_de_receta(receta: Receta | None, codigo_ligante: str | None) -> Decimal | None:
    """El porcentaje de asfalto (en puntos: 5,5 es 5,5 %) de la fórmula de trabajo de `receta`.

    La fórmula es el componente ligante de la receta: el que lleva `codigo_ligante`, en t por
    tonelada de mezcla. Sin receta, sin código o sin ese componente en t, `None` (VR2 no se evalúa).
    """
    if receta is None or not codigo_ligante:
        return None
    for componente in receta.componentes:
        if componente.codigo == codigo_ligante and componente.unidad == "t":
            return componente.cantidad_por_t * 100
    return None


def _mezclas_del_apu(sesion: Session, codigo: str) -> list[str]:
    """Los productos de las mezclas propias que usa el APU de la partida `codigo` (`KeyError` si
    la partida no está en el catálogo)."""
    partida = Catalogo(sesion).partida(codigo)
    largo = len(_LINEA_DE_MEZCLA_PROPIA)
    return sorted(
        {
            linea.insumo.descripcion[largo:]
            for linea in partida.composicion
            if linea.insumo.descripcion.startswith(_LINEA_DE_MEZCLA_PROPIA)
            and len(linea.insumo.descripcion) > largo
        }
    )


def _formula_de_la_receta(receta: Receta | None, producto: str, hoy: date) -> Decimal | str:
    """La fórmula de trabajo de la receta vigente de `producto`, o el motivo de no tenerla."""
    if receta is None:
        return f"la mezcla propia {producto} no tiene receta vigente al {hoy:%d/%m/%Y}"
    comprados = [c for c in receta.componentes if c.tipo == "comprado" and c.unidad == "t"]
    if len(comprados) != 1:
        cuales = f" ({', '.join(c.codigo for c in comprados)})" if comprados else ""
        return (
            f"la receta n.º {receta.id} de {producto} tiene {len(comprados)} componentes "
            f"comprados en t{cuales} y no se sabe cuál es el ligante"
        )
    # el único comprado en t es el ligante: lo mismo que `formula_asfalto_de_receta` con su código
    return comprados[0].cantidad_por_t * 100


def formulas_de_trabajo(
    sesion: Session,
    tramos: Sequence[Tramo],
    hoy: date,
    instalacion: Session | None = None,
) -> tuple[dict[str, Decimal], dict[str, str]]:
    """Por código de partida de mezcla de `tramos`, la fórmula de trabajo (puntos de asfalto) de la
    receta vigente a `hoy` de la mezcla propia que usa su APU, y, de las que no la tienen, el motivo
    (véase el encabezado del módulo). `instalacion` es la sesión de la base de la instalación; sin
    ella se abre una, y solo si algún APU usa una mezcla propia."""
    presentes = {item.codigo_partida for item in derivar_tramos(tramos)}
    formulas: dict[str, Decimal] = {}
    sin_formula: dict[str, str] = {}
    productos: dict[str, str] = {}
    for codigo in (c for c in _PARTIDAS_DE_MEZCLA if c in presentes):
        try:
            mezclas = _mezclas_del_apu(sesion, codigo)
        except KeyError:
            sin_formula[codigo] = f"la partida {codigo} no está en el catálogo"
            continue
        if len(mezclas) == 1:
            productos[codigo] = mezclas[0]
        elif mezclas:
            sin_formula[codigo] = (
                f"el APU de la partida {codigo} usa varias mezclas propias ({', '.join(mezclas)})"
            )
        else:
            sin_formula[codigo] = (
                f"el APU de la partida {codigo} no usa una mezcla propia (una línea "
                f"«{_LINEA_DE_MEZCLA_PROPIA}…»)"
            )
    if not productos:
        return formulas, sin_formula
    try:
        with ExitStack() as pila:
            ins = (
                instalacion if instalacion is not None else pila.enter_context(_abrir_instalacion())
            )
            recetas = {p: receta_vigente(ins, p, hoy) for p in set(productos.values())}
    except (SQLAlchemyError, OSError):
        # VR2 es un aviso: una instalación que no se puede leer (la base bloqueada o el archivo sin
        # permiso) no impide auditar ni abrir la Hoja
        for codigo, producto in productos.items():
            sin_formula[codigo] = (
                f"no se pudo leer la base de la instalación para buscar la receta de {producto}"
            )
        return formulas, sin_formula
    for codigo, producto in productos.items():
        formula = _formula_de_la_receta(recetas[producto], producto, hoy)
        if isinstance(formula, str):
            sin_formula[codigo] = formula
        else:
            formulas[codigo] = formula
    return formulas, sin_formula


def reglas_viales(
    sesion: Session,
    version_id: int,
    *,
    receta: Receta | None = None,
    codigo_ligante: str | None = None,
    hoy: date | None = None,
    instalacion: Session | None = None,
) -> tuple[ReglasViales, ...]:
    """Las reglas VR1 a VR7 de la versión, para `elaborar(reglas=(*REGLAS, *reglas_viales(…)))` o
    `reglas_extra` de la Hoja: sus hallazgos entran en la auditoría como los de `Espacio` (regla
    ajena a `REGLAS`, que `hallazgos_externos` vuelve a declarar). Vacío si la versión no tiene
    tramos (propios o heredados).

    Con `receta` o `codigo_ligante` (la forma de la Tarea 9), VR2 usa esa fórmula para todas las
    mezclas. Sin ellos (llevar los tramos y abrir una versión, Tarea 16b), cada partida de mezcla
    recibe la de la receta vigente a `hoy` de su mezcla propia (`formulas_de_trabajo`). `hoy` lo
    pasa quien llama; `abrir_version` de la Hoja no lo pasa (su llamada es parte del experimento
    congelado) y entonces es la fecha del día."""
    tramos = tramos_de_version(sesion, version_id)
    if not tramos:
        return ()
    if receta is not None or codigo_ligante is not None:
        return (ReglasViales(tramos, formula_asfalto_de_receta(receta, codigo_ligante)),)
    dia = hoy if hoy is not None else date.today()
    formulas, sin_formula = formulas_de_trabajo(sesion, tramos, dia, instalacion)
    return (ReglasViales(tramos, formulas=formulas, sin_formula=sin_formula),)
