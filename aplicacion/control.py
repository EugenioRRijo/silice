"""Control de obra sin Streamlit (UC-19 y UC-20; spec S2 §5.5).

Lo que la pantalla «Control de obra» necesita del núcleo: declarar la línea base de control,
registrar una valuación a mano o desde un XLSX, anularla, anotar costos incurridos, calcular al
corte el valor ganado, la separación del desvío, las alertas y la reproyección **siempre**,
calcular las opciones de recuperación **a pedido** y elegir una, y armar las hojas
«Valuaciones», «Valor ganado» y «Decisiones» del Excel de la hoja (`hojas_extra`).

Cada función que escribe confirma su transacción o la deshace (`rollback`) y levanta
`ControlInvalido` con un mensaje en español, sin *traceback*. Los textos que vienen de fuera
(inspector, observación y fuente de un XLSX) los muestra la página con `ui.texto_seguro` o en
celdas (RV-14). Los montos se presentan a dos decimales y los índices a cuatro, que es donde se
redondea. Sin Streamlit, sin `pandas` y sin `ui.caso`; lo vigila
`tests/unit/test_arquitectura_s2.py`.

Desde la tarea 4.3 del plan de desenredo este módulo es la fachada del control: reexporta (con
`__all__`) lo común (`control_comun`), la línea base (`control_linea_base`), el cálculo
(`control_calculo`), las tablas (`control_tablas`) y los parámetros (`control_parametros`), y
guarda las consultas cortas, las partidas del contrato y los precios del corte: estos dos leen
`aplicacion.frentes` y `aplicacion.precios_declarados`, que están en el ciclo de la mesa, y
fuera de aquí ese ciclo crecería (ola 5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.control_calculo import (
    calcular_el_control,
    calcular_las_opciones,
    elegir_opcion,
)
from aplicacion.control_comun import (
    COLUMNAS_ALERTAS,
    COLUMNAS_DECISIONES,
    COLUMNAS_INDICADORES,
    COLUMNAS_LINEAS,
    COLUMNAS_OPCIONES,
    COLUMNAS_REPROYECCION,
    COLUMNAS_VALUACIONES,
    MENSAJE_SIN_DECLARADOS,
    METODO_COMPROBACION,
    METODO_DECLARADOS,
    METODO_ESCALATORIA,
    METODO_NINGUNO,
    METODOS_DE_PRECIOS,
    NATURALEZA_DATO,
    NATURALEZA_SUPUESTO,
    NO_APLICA,
    NO_DISPONIBLE,
    ControlInvalido,
    _decimal,
    _monto,
)
from aplicacion.control_linea_base import (
    DIAS_POR_OMISION,
    DiasDelPlan,
    anular,
    declarar_linea_base,
    dias_de_las_etiquetas,
    dias_por_periodo_del_plan,
    importar_excel,
    leer_excel,
    lineas_desde_filas,
    registrar_costo_real,
    registrar_y_controlar,
    versiones_para_la_linea_base,
    versiones_revaloradas,
)
from aplicacion.control_parametros import (
    COLUMNAS_PARAMETROS,
    PARAMETROS_EDITABLES,
    curva_pv_ev_ac,
    filas_de_parametros,
    guardar_los_parametros,
    parametros_desde_filas,
)
from aplicacion.control_tablas import (
    LARGO_MAXIMO_A_CORREGIR,
    PLANTILLAS_DEL_NUCLEO,
    Hueco,
    alertas_en_filas,
    catalogo_de_frases,
    con_tildes,
    estado_de_valuaciones,
    filas_de_decisiones,
    filas_de_indicadores,
    filas_de_opciones,
    filas_de_reproyeccion,
    filas_de_valuaciones,
    impuestos_de_valuaciones,
    subtotales_de_valuaciones,
    supuestos_de_opcion,
    tablas_de_control,
)
from aplicacion.frentes import CLAVE_FRENTE
from aplicacion.precios_declarados import precios_declarados
from core import models
from core.budget.calendario import dia_habil
from core.budget.control import (
    ResultadoControl,
    parametros_de_control,
    precios_del_corte_de_version,
)
from core.budget.valor_ganado import (
    ParametrosControl,
    PreciosDelCorte,
    precios_por_escalatoria,
)
from core.budget.valuaciones import (
    instantanea_control,
    linea_base_vigente,
    valuaciones_registradas,
)
from core.catalog import Catalogo

__all__ = [
    "COLUMNAS_ALERTAS",
    "COLUMNAS_DECISIONES",
    "COLUMNAS_INDICADORES",
    "COLUMNAS_LINEAS",
    "COLUMNAS_OPCIONES",
    "COLUMNAS_PARAMETROS",
    "COLUMNAS_REPROYECCION",
    "COLUMNAS_VALUACIONES",
    "ControlInvalido",
    "DIAS_POR_OMISION",
    "DiasDelPlan",
    "Hueco",
    "LARGO_MAXIMO_A_CORREGIR",
    "MAXIMO_DE_PARTIDAS_DEL_CONTRATO",
    "MENSAJE_SIN_DECLARADOS",
    "METODOS_DE_PRECIOS",
    "METODO_COMPROBACION",
    "METODO_DECLARADOS",
    "METODO_ESCALATORIA",
    "METODO_NINGUNO",
    "NATURALEZA_DATO",
    "NATURALEZA_SUPUESTO",
    "NO_APLICA",
    "NO_DISPONIBLE",
    "PARAMETROS_EDITABLES",
    "PLANTILLAS_DEL_NUCLEO",
    "PartidaDelContrato",
    "PartidasDeUnaVersion",
    "PrecioElegido",
    "alertas_en_filas",
    "anular",
    "calcular_el_control",
    "calcular_las_opciones",
    "catalogo_de_frases",
    "con_tildes",
    "corte_por_defecto",
    "curva_pv_ev_ac",
    "declarar_linea_base",
    "describir_linea_base",
    "dia_con_fecha",
    "dias_de_las_etiquetas",
    "dias_por_periodo_del_plan",
    "elegir_opcion",
    "estado_de_valuaciones",
    "estudios_que_suma",
    "filas_de_decisiones",
    "filas_de_indicadores",
    "filas_de_opciones",
    "filas_de_parametros",
    "filas_de_reproyeccion",
    "filas_de_valuaciones",
    "filas_del_plan_reproyectado",
    "guardar_los_parametros",
    "hay_valuaciones",
    "importar_excel",
    "impuestos_de_valuaciones",
    "leer_excel",
    "lineas_desde_filas",
    "parametros_actuales",
    "parametros_desde_filas",
    "partidas_de_la_linea_base",
    "partidas_de_la_version",
    "perspectiva_de_la_linea_base",
    "precios_del_corte",
    "registrar_costo_real",
    "registrar_y_controlar",
    "renglones_de_la_version",
    "subtotales_de_valuaciones",
    "supuestos_de_opcion",
    "tablas_de_control",
    "texto_monto",
    "tiene_linea_base",
    "valuaciones_para_anular",
    "versiones_para_la_linea_base",
    "versiones_revaloradas",
]


# ---------------------------------------------------------------------------------------------
# Partidas del contrato (UC-19): leen el frente de cada renglón (`aplicacion.frentes`)
# ---------------------------------------------------------------------------------------------


#: Tope de partidas que se ofrecen en un campo con autocompletado (diseño de autocompletado §5.4).
MAXIMO_DE_PARTIDAS_DEL_CONTRATO = 2000


@dataclass(frozen=True, slots=True)
class PartidaDelContrato:
    """Una partida de una versión del contrato tal como el contrato la nombra (AC2)."""

    codigo: str
    descripcion: str
    unidad: str
    #: Por renglón (`renglones_de_la_version`): su número en el presupuesto (desde 1) y cuántos
    #: renglones tiene su código. `None` en la lista por código.
    renglon: int | None = None
    renglones: int | None = None
    #: El frente del renglón (`aplicacion.frentes`), `None` sin frente: el selector lo nombra para
    #: distinguir un código repetido en dos frentes (pasada en navegador de la ola 2, D5).
    frente: str | None = None


@dataclass(frozen=True, slots=True)
class PartidasDeUnaVersion:
    """Las partidas de una versión del contrato (AC2) y si la lista se recortó al tope: con
    `truncada`, que una partida no esté en la lista no dice que no esté en el contrato."""

    version: str
    partidas: tuple[PartidaDelContrato, ...]
    truncada: bool = False


def partidas_de_la_version(sesion: Session, version: models.Presupuesto) -> PartidasDeUnaVersion:
    """Las partidas de una versión guardada, por código y una sola vez cada una (si el contrato
    repite una partida en dos renglones, vale la primera). Una consulta ligera sobre los renglones:
    no carga el presupuesto ni calcula nada. A lo sumo `MAXIMO_DE_PARTIDAS_DEL_CONTRATO`; si había
    más, `truncada`."""
    filas = sesion.execute(
        select(
            models.ItemComputo.codigo_partida,
            models.ItemComputo.descripcion,
            models.ItemComputo.unidad,
        )
        .join(
            models.PartidaPresupuestada,
            models.PartidaPresupuestada.item_computo_id == models.ItemComputo.id,
        )
        .where(models.PartidaPresupuestada.presupuesto_id == version.id)
        .order_by(models.ItemComputo.codigo_partida, models.PartidaPresupuestada.orden)
    )
    vistas: dict[str, PartidaDelContrato] = {}
    for codigo, descripcion, unidad in filas:
        vistas.setdefault(codigo, PartidaDelContrato(codigo, descripcion, unidad))
    todas = list(vistas.values())
    tope = MAXIMO_DE_PARTIDAS_DEL_CONTRATO
    return PartidasDeUnaVersion(version.codigo, tuple(todas[:tope]), len(todas) > tope)


def _frente(especificaciones: str | None) -> str | None:
    """El frente guardado en las especificaciones (JSON) de un renglón, o `None`."""
    try:
        valor = json.loads(especificaciones or "{}").get(CLAVE_FRENTE, "")
    except (ValueError, AttributeError):
        return None
    return valor.strip() or None if isinstance(valor, str) else None


def renglones_de_la_version(sesion: Session, version: models.Presupuesto) -> PartidasDeUnaVersion:
    """Los renglones de una versión guardada, uno por renglón y en el orden del presupuesto, con su
    número y cuántos renglones tiene su código (ola 2 del 2026-11-13, RF-197): un contrato que
    repite un código en dos frentes los ofrece los dos. La valuación sigue siendo por código (el
    núcleo suma los renglones de un código, `core.budget.valuaciones`). Misma consulta ligera y
    mismo tope que `partidas_de_la_version`."""
    filas = list(
        sesion.execute(
            select(
                models.ItemComputo.codigo_partida,
                models.ItemComputo.descripcion,
                models.ItemComputo.unidad,
                models.ItemComputo.especificaciones,
            )
            .join(
                models.PartidaPresupuestada,
                models.PartidaPresupuestada.item_computo_id == models.ItemComputo.id,
            )
            .where(models.PartidaPresupuestada.presupuesto_id == version.id)
            .order_by(models.PartidaPresupuestada.orden)
        )
    )
    por_codigo: dict[str, int] = {}
    for codigo, *_ in filas:
        por_codigo[codigo] = por_codigo.get(codigo, 0) + 1
    todas = [
        PartidaDelContrato(
            codigo, descripcion, unidad, numero, por_codigo[codigo], _frente(especificaciones)
        )
        for numero, (codigo, descripcion, unidad, especificaciones) in enumerate(filas, start=1)
    ]
    tope = MAXIMO_DE_PARTIDAS_DEL_CONTRATO
    return PartidasDeUnaVersion(version.codigo, tuple(todas[:tope]), len(todas) > tope)


def partidas_de_la_linea_base(
    sesion: Session, proyecto: str, corte: date | None = None
) -> PartidasDeUnaVersion | None:
    """Las partidas de la versión de la línea base de control vigente al `corte` (la misma contra
    la que R13 juzga una valuación con ese *hasta*), o de la más reciente sin `corte`; `None` si a
    esa fecha no hay ninguna. No lee valuaciones ni revalora (`instantanea_control` falla justo en
    el uso principal: registrar la primera valuación)."""
    fila = linea_base_vigente(sesion, proyecto, date.max if corte is None else corte)
    if fila is None:
        return None
    return renglones_de_la_version(sesion, sesion.get(models.Presupuesto, fila.presupuesto_id))


# ---------------------------------------------------------------------------------------------
# Precios del corte (UC-20): leen los precios declarados (`aplicacion.precios_declarados`)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PrecioElegido:
    """Cómo se toman los precios del corte (S2 §4.3): ninguno, una versión revalorada
    (comprobación directa) o la escalatoria con un solo `Km` y `R` declarados. Son textos de la
    pantalla."""

    metodo: str = METODO_NINGUNO
    version: str = ""
    km: str = ""
    r: str = "0"
    fuente: str = ""


def perspectiva_de_la_linea_base(sesion: Session, proyecto: str, corte: date | None) -> str:
    """La perspectiva (costo o precio) de la línea base vigente al `corte` (sin `corte`, al de la
    última valuación). Sin línea base, «costo»: el cálculo dirá luego por qué no se puede."""
    fila = linea_base_vigente(sesion, proyecto, corte or corte_por_defecto(sesion, proyecto))
    return "costo" if fila is None else fila.perspectiva


def precios_del_corte(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    elegido: PrecioElegido,
    perspectiva: str,
    *,
    corte: date | None = None,
) -> PreciosDelCorte | None:
    """Los `PreciosDelCorte` que corresponden a la elección, o `None` si no se eligió ninguno.

    `perspectiva` debe ser la de la línea base (`perspectiva_de_la_linea_base`): los unitarios del
    corte se comparan con los de la línea base. `corte` lo usan los precios declarados y la
    escalatoria (sin él, el de la última valuación); sin ninguno declarado hasta el corte, o sin
    línea base vigente a él para la escalatoria, `ControlInvalido`."""
    if elegido.metodo == METODO_DECLARADOS:
        try:
            declarados = precios_declarados(sesion, proyecto, catalogo, corte, perspectiva)
        except ValueError as error:
            raise ControlInvalido(str(error)) from None
        if declarados is None:
            raise ControlInvalido(MENSAJE_SIN_DECLARADOS)
        return declarados
    if elegido.metodo == METODO_COMPROBACION:
        if not elegido.version:
            raise ControlInvalido("elija la version revalorada para la comprobacion directa")
        try:
            return precios_del_corte_de_version(
                sesion, proyecto, elegido.version, perspectiva, catalogo
            )
        except (KeyError, ValueError) as error:
            raise ControlInvalido(str(error.args[0])) from None
    if elegido.metodo == METODO_ESCALATORIA:
        if not elegido.fuente.strip():
            raise ControlInvalido("la escalatoria necesita la fuente de Km y R")
        try:
            base = instantanea_control(sesion, proyecto, catalogo=catalogo, corte=corte).presupuesto
        except ValueError as error:
            raise ControlInvalido(str(error)) from None
        unitarios = {
            p.item.codigo_partida: (
                p.resultado.costo_directo if perspectiva == "costo" else p.resultado.precio_unitario
            )
            for p in base.partidas
        }
        km = _decimal(elegido.km, "Km")
        try:
            return precios_por_escalatoria(
                unitarios, dict.fromkeys(unitarios, km), _decimal(elegido.r, "R"), elegido.fuente
            )
        except ValueError as error:
            raise ControlInvalido(str(error)) from None
    return None


# ---------------------------------------------------------------------------------------------
# Consultas cortas para la pantalla
# ---------------------------------------------------------------------------------------------


def texto_monto(valor: Decimal | None) -> str:
    """Un monto a dos decimales para mostrar; `None` es «no disponible»."""
    return _monto(valor)


def tiene_linea_base(sesion: Session, proyecto: str) -> bool:
    """True si el proyecto tiene alguna línea base de control declarada."""
    return linea_base_vigente(sesion, proyecto, date.max) is not None


def describir_linea_base(sesion: Session, proyecto: str) -> str | None:
    """La línea base vigente hoy en una frase (versión, perspectiva, calendario), o `None`.
    La fuente es texto ajeno: la pantalla la escapa con `ui.texto_seguro`."""
    fila = linea_base_vigente(sesion, proyecto, date.max)
    if fila is None:
        return None
    version = sesion.get(models.Presupuesto, fila.presupuesto_id)
    calendario = fila.calendario
    return (
        f"versión {version.codigo}, perspectiva {fila.perspectiva}, vigente desde "
        f"{fila.desde:%d/%m/%Y}; inicio de obra {calendario.fecha_inicio:%d/%m/%Y} con "
        f"{calendario.dias_por_periodo} día(s) hábil(es) por período"
    )


def hay_valuaciones(sesion: Session, proyecto: str) -> bool:
    """True si el proyecto tiene alguna valuación registrada (anulada o no)."""
    return bool(valuaciones_registradas(sesion, proyecto, con_anuladas=True))


def corte_por_defecto(sesion: Session, proyecto: str) -> date:
    """El *hasta* de la última valuación no anulada; hoy si no hay ninguna."""
    return max((v.hasta for v in valuaciones_registradas(sesion, proyecto)), default=date.today())


def valuaciones_para_anular(sesion: Session, proyecto: str) -> list[tuple[int, str]]:
    """`(id, rótulo)` de las valuaciones que cuentan y se pueden anular."""
    return [
        (v.id, f"{v.numero or '#' + str(v.id)} ({v.desde:%d/%m/%Y} a {v.hasta:%d/%m/%Y})")
        for v in valuaciones_registradas(sesion, proyecto)
    ]


def parametros_actuales(sesion: Session, proyecto: str) -> ParametrosControl:
    """Los parámetros de control del proyecto (los por defecto si no tiene fila)."""
    return parametros_de_control(sesion, proyecto)


def dia_con_fecha(resultado: ResultadoControl, dia: int | None) -> str:
    """«día N (dd/mm/aaaa)» en el calendario de la línea base; «no proyectable» si no hay día."""
    if dia is None:
        return "no proyectable"
    calendario = resultado.instantanea.calendario
    fecha = dia_habil(calendario.fecha_inicio, dia, frozenset(calendario.feriados))
    return f"día {dia} ({fecha:%d/%m/%Y})"


def filas_del_plan_reproyectado(
    resultado: ResultadoControl,
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    """Las columnas (período y una por partida) y las filas del plan reproyectado."""
    codigos = [p.codigo for p in resultado.estado.partidas]
    filas = []
    for etiqueta, reparto in resultado.reproyeccion.plan:
        fila = {"Periodo": etiqueta, **dict.fromkeys(codigos, "")}
        fila.update({codigo: format(fraccion, ".4f") for codigo, fraccion in reparto})
        filas.append(fila)
    return ("Periodo", *codigos), filas


def estudios_que_suma(resultado: ResultadoControl) -> str:
    """Una frase con los estudios de reajuste de S1 que suma V' (S2-R15), o que no suma ninguno."""
    reajuste = resultado.reajuste
    if not reajuste.estudios:
        return "Sin estudio de reajuste guardado: V' = V. Nunca se proyecta un reajuste."
    detalle = ", ".join(
        f"#{e.id} ({e.fecha_calculo:%d/%m/%Y}, {_monto(e.monto)})" for e in reajuste.estudios
    )
    return (
        f"V' suma el reajuste reconocido de {len(reajuste.estudios)} estudio(s) de reajuste "
        f"guardado(s): "
        f"{detalle}; total {_monto(reajuste.monto)} {reajuste.moneda}."
    )
