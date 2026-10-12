# core/budget/valuaciones.py
"""SL-E4: línea base de control, valuaciones, costos incurridos y su entrega a S1 (spec S2 §3, §6).

Una **valuación** es la cantidad ejecutada por partida y período, con su fuente (número, inspector,
fecha). Se guarda **sin modificar ninguna anterior** y **cuenta desde su registro**, sin
conformación (RV-18, S2-R14); la única forma de sacarla del cálculo es anularla, y la anulada se
conserva. Ninguna función de este módulo emite `UPDATE` ni `DELETE` sobre `valuacion`,
`linea_valuacion` ni `anulacion_valuacion` (S2-R10).

La **línea base de control** (versión, perspectiva, calendario) fija contra qué se mide el avance;
una decisión de recuperación **no** la cambia (S2-R3). Un cambio de moneda del proyecto después de
declararla la **invalida**: `instantanea_control` lo rechaza y hay que declararla de nuevo sobre la
versión convertida (RV-11).

`ejecutado_por_periodo` entrega a S1 lo ejecutado de cada período de su cláusula: las valuaciones
registradas y no anuladas, cada una entera en el período que contiene su fecha *hasta* (S2-R16).
`leer_valuaciones_excel` es la fuente única del formato del XLSX (§6.2). Todo monto y cantidad es
`Decimal`; las divisiones, si las hubiera, irían en un contexto local de 28 dígitos.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import partial
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _buscar, _parametros_de
from core.budget.calendario import dias_habiles, numero_de_dia
from core.budget.curva import PeriodoPlan
from core.budget.edicion import _exigir_respaldo
from core.budget.excel import TablaExportable
from core.budget.instantanea import plan_de_version
from core.budget.moneda import moneda_del_proyecto
from core.budget.persistencia import cargar_presupuesto
from core.catalog import Catalogo
from core.catalog.moneda import exigir_moneda
from core.catalog.precios import PRIMERA_FILA_DE_DATOS, leer_tabla
from core.contracts.apu import ParametrosCosto
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import ReglaVerificacion
from core.models.control import PERSPECTIVAS
from core.verification import auditar
from core.verification.informe import InformeAuditoria
from core.verification.valuaciones import (
    InstantaneaDeControl,
    LineaValuacion,
    PartidaBase,
    Valuacion,
    reglas_de_control,
)

__all__ = [
    "COLUMNAS_COSTOS",
    "COLUMNAS_LINEAS",
    "COLUMNAS_VALUACIONES",
    "HOJA_COSTOS",
    "HOJA_LINEAS",
    "HOJA_VALUACIONES",
    "LIMITE_BYTES",
    "Calendario",
    "CostoLeido",
    "CostoReal",
    "EjecutadoDelPeriodo",
    "InstantaneaControl",
    "LecturaControl",
    "LineaBase",
    "LineaEjecutada",
    "LineaBaseInvalidada",
    "anexo_control",
    "anular_valuacion",
    "ejecutado_por_periodo",
    "instantanea_control",
    "leer_valuaciones_excel",
    "registrar_costo",
    "registrar_lectura",
    "registrar_linea_base",
    "registrar_valuacion",
    "tabla_valuaciones",
]

CERO = Decimal(0)
LIMITE_BYTES = 20 * 1024 * 1024  # RNF-12: el mismo límite que los planos
HOJA_VALUACIONES = "Valuaciones"
HOJA_LINEAS = "Lineas"
HOJA_COSTOS = "Costos"
COLUMNAS_VALUACIONES = ("numero", "desde", "hasta", "fecha", "inspector")
COLUMNAS_LINEAS = ("numero", "codigo_partida", "cantidad", "fecha_medicion", "observacion")
COLUMNAS_COSTOS = ("numero", "codigo_partida", "monto", "moneda", "fecha", "fuente")
ORIGEN_MANUAL = "manual"
PREFIJO_ORIGEN_EXCEL = "excel:"
MENSAJE_INVALIDADA = "linea base invalidada: declarela de nuevo"


class LineaBaseInvalidada(ValueError):  # noqa: N818
    """La moneda del proyecto cambió después de declarar la línea base de control (RV-11)."""


@dataclass(frozen=True, slots=True)
class Calendario:
    """Fecha de inicio, días hábiles por período y feriados de la obra (S2 §4.1)."""

    fecha_inicio: date
    dias_por_periodo: int
    feriados: tuple[date, ...] = ()

    def __post_init__(self) -> None:
        if self.dias_por_periodo < 1:
            raise ValueError(f"los dias por periodo deben ser 1 o mas: {self.dias_por_periodo}")
        object.__setattr__(self, "feriados", tuple(sorted(set(self.feriados))))


@dataclass(frozen=True, slots=True)
class LineaBase:
    """Una línea base de control ya guardada, con su calendario y el código de su versión."""

    id: int
    proyecto: str
    version: str
    desde: date
    perspectiva: str
    fuente: str
    responsable: str
    calendario: Calendario
    fecha_hora: datetime | None = None


@dataclass(frozen=True, slots=True)
class CostoReal:
    """Un costo real declarado (S2 §6.1): se convierte con la tasa de su fecha al calcular."""

    id: int
    monto: Decimal
    moneda: str
    fecha: date
    fuente: str
    responsable: str = ""
    codigo_partida: str | None = None
    valuacion_id: int | None = None


@dataclass(frozen=True)
class InstantaneaControl:
    """Lo que el control necesita al corte (S2 §3.4): la línea base con su presupuesto, su plan y
    su calendario; las valuaciones registradas y no anuladas y los costos reales declarados.

    Las valuaciones son **todas** las no anuladas; el valor ganado usa las de *hasta* menor o
    igual al corte y R14 marca las que terminan después (RP7-2).
    """

    proyecto: str
    corte: date
    linea_base: LineaBase
    presupuesto: Presupuesto
    plan: tuple[PeriodoPlan, ...]
    parametros_costo: ParametrosCosto
    moneda: str
    valuaciones: tuple[Valuacion, ...] = ()
    costos: tuple[CostoReal, ...] = ()

    @property
    def calendario(self) -> Calendario:
        return self.linea_base.calendario

    def para_el_valor_ganado(self) -> tuple[Valuacion, ...]:
        """Las valuaciones que cuentan al corte: registradas, no anuladas y con *hasta* <= corte."""
        return tuple(v for v in self.valuaciones if v.hasta <= self.corte)

    def auditada(self) -> InstantaneaDeControl:
        """La entrada de R13 y R14 (`core.verification.valuaciones`)."""
        programadas = {codigo for _, reparto in self.plan for codigo, f in reparto if f > CERO}
        partidas: dict[str, PartidaBase] = {}
        for renglon in self.presupuesto.partidas:
            codigo = renglon.item.codigo_partida
            unitario = (
                renglon.resultado.costo_directo
                if self.linea_base.perspectiva == "costo"
                else renglon.resultado.precio_unitario
            )
            previa = partidas.get(codigo)
            partidas[codigo] = PartidaBase(
                codigo,
                renglon.item.cantidad + (previa.cantidad if previa else CERO),
                unitario,
                previa.origen_id if previa else renglon.item.origen_id,
                codigo in programadas,
            )
        return InstantaneaDeControl(
            corte=self.corte,
            inicio=self.calendario.fecha_inicio,
            partidas=tuple(partidas.values()),
            valuaciones=self.valuaciones,
            habiles_entre=partial(dias_habiles, feriados=frozenset(self.calendario.feriados)),
        )

    def reglas(self) -> tuple[ReglaVerificacion, ...]:
        return reglas_de_control(self.auditada())

    def informe(self) -> InformeAuditoria:
        """El informe de control (principio 7): R13 y R14 sobre las valuaciones al corte."""
        return auditar(self.presupuesto, self.reglas())


# ---------------------------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------------------------


def _proyecto(session: Session, nombre: str) -> models.Proyecto:
    proyecto = session.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == nombre)
    ).one_or_none()
    if proyecto is None:
        raise KeyError(f"no hay ningun proyecto {nombre!r}")
    return proyecto


def registrar_linea_base(
    session: Session,
    proyecto_nombre: str,
    codigo_version: str,
    *,
    desde: date,
    perspectiva: str,
    calendario: Calendario,
    fuente: str,
    responsable: str,
    ahora: datetime | None = None,
) -> models.LineaBaseControl:
    """Declara la línea base de control sobre una versión guardada (RF-72). Cambiarla es declarar
    otra fila: la vigente al corte es la de mayor `desde` menor o igual al corte. La versión debe
    tener plan de trabajo y estar en la moneda del proyecto (`ValueError`). No confirma."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    if perspectiva not in PERSPECTIVAS:
        raise ValueError(f"perspectiva {perspectiva!r}: se espera costo o precio")
    version = _buscar(session, proyecto_nombre, codigo_version)
    if plan_de_version(session, version) is None:
        raise ValueError(
            f"la version {codigo_version!r} no tiene plan de trabajo: no hay con que medir"
        )
    if moneda_del_proyecto(session, version.proyecto) != version.moneda:
        raise ValueError(
            f"la version {codigo_version!r} esta en {version.moneda}, no en la moneda del "
            "proyecto: declare la linea base sobre la version convertida"
        )
    fila = models.LineaBaseControl(
        proyecto_id=version.proyecto_id,
        presupuesto_id=version.id,
        desde=desde,
        perspectiva=perspectiva,
        fuente=fuente,
        responsable=responsable,
        fecha_hora=ahora or datetime.now(),
    )
    fila.calendario = models.CalendarioObra(
        fecha_inicio=calendario.fecha_inicio,
        dias_por_periodo=calendario.dias_por_periodo,
        feriados=json.dumps([dia.isoformat() for dia in calendario.feriados]),
    )
    session.add(fila)
    session.flush()
    return fila


def _lineas(lineas: Sequence[LineaValuacion | tuple]) -> list[LineaValuacion]:
    return [
        linea if isinstance(linea, LineaValuacion) else LineaValuacion(*linea) for linea in lineas
    ]


def registrar_valuacion(
    session: Session,
    proyecto_nombre: str,
    *,
    numero: str,
    desde: date,
    hasta: date,
    fecha: date | None,
    inspector: str,
    lineas: Sequence[LineaValuacion | tuple],
    fuente: str,
    responsable: str,
    origen: str = ORIGEN_MANUAL,
    ahora: datetime | None = None,
) -> models.Valuacion:
    """Registra una valuación (UC-19 4): no modifica ninguna anterior y cuenta desde ahora.

    El número, el inspector y la fecha pueden faltar: se guarda y R14 la marca (UC-19 4a). Una
    cantidad negativa o no decimal se rechaza (`ValueError`, 2b): corregir es anular. Exige una
    línea base de control declarada, fuente y responsable. No confirma."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    proyecto = _proyecto(session, proyecto_nombre)
    if _lineas_base(session, proyecto.id) == []:
        raise ValueError("declare la linea base de control antes de registrar valuaciones")
    validadas = _lineas(lineas)
    if not validadas:
        raise ValueError("una valuacion necesita al menos una linea")
    fila = models.Valuacion(
        proyecto_id=proyecto.id,
        numero=numero.strip(),
        desde=desde,
        hasta=hasta,
        fecha=fecha,
        inspector=inspector.strip(),
        origen=origen,
        fuente=fuente,
        responsable=responsable,
        fecha_hora=ahora or datetime.now(),
    )
    fila.lineas = [
        models.LineaValuacion(
            codigo_partida=linea.codigo_partida,
            cantidad=linea.cantidad,
            fecha_medicion=linea.fecha_medicion,
            observacion=linea.observacion,
        )
        for linea in validadas
    ]
    session.add(fila)
    session.flush()
    return fila


def anular_valuacion(
    session: Session,
    valuacion_id: int,
    *,
    motivo: str,
    responsable: str,
    ahora: datetime | None = None,
) -> models.AnulacionValuacion:
    """Anula una valuación (UC-19 4c): fila de anulación con motivo y responsable. La anulada se
    conserva y deja de contar; se anula una sola vez. No confirma."""
    motivo, responsable = _exigir_respaldo(motivo, responsable)
    valuacion = session.get(models.Valuacion, valuacion_id)
    if valuacion is None:
        raise KeyError(f"no hay ninguna valuacion {valuacion_id}")
    if session.get(models.AnulacionValuacion, valuacion_id) is not None:
        raise ValueError(f"la valuacion {valuacion.numero or valuacion_id} ya esta anulada")
    anulacion = models.AnulacionValuacion(
        valuacion_id=valuacion_id,
        motivo=motivo,
        responsable=responsable,
        fecha_hora=ahora or datetime.now(),
    )
    session.add(anulacion)
    session.flush()
    return anulacion


def registrar_costo(
    session: Session,
    proyecto_nombre: str,
    *,
    monto: Decimal,
    moneda: str,
    fecha: date,
    fuente: str,
    responsable: str,
    codigo_partida: str | None = None,
    valuacion_id: int | None = None,
) -> models.CostoReal:
    """Registra un costo real (RF-75): monto, moneda, fecha y fuente. No se guarda convertido:
    se convierte con `tasa_aplicable(fecha)` al calcular. `ValueError` si el monto es negativo."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    if not isinstance(monto, Decimal) or not monto.is_finite() or monto < CERO:
        raise ValueError(f"el monto de un costo real debe ser un Decimal no negativo: {monto!r}")
    proyecto = _proyecto(session, proyecto_nombre)
    fila = models.CostoReal(
        proyecto_id=proyecto.id,
        valuacion_id=valuacion_id,
        codigo_partida=codigo_partida,
        monto=monto,
        moneda=exigir_moneda(moneda),
        fecha=fecha,
        fuente=fuente,
        responsable=responsable,
    )
    session.add(fila)
    session.flush()
    return fila


# ---------------------------------------------------------------------------------------------
# Lectura: la instantánea de control
# ---------------------------------------------------------------------------------------------


def _lineas_base(session: Session, proyecto_id: int) -> list[models.LineaBaseControl]:
    return list(
        session.scalars(
            select(models.LineaBaseControl)
            .where(models.LineaBaseControl.proyecto_id == proyecto_id)
            .order_by(models.LineaBaseControl.desde, models.LineaBaseControl.id)
        )
    )


def _a_linea_base(fila: models.LineaBaseControl, proyecto: str, version: str) -> LineaBase:
    calendario = fila.calendario
    return LineaBase(
        id=fila.id,
        proyecto=proyecto,
        version=version,
        desde=fila.desde,
        perspectiva=fila.perspectiva,
        fuente=fila.fuente,
        responsable=fila.responsable,
        calendario=Calendario(
            calendario.fecha_inicio,
            calendario.dias_por_periodo,
            tuple(date.fromisoformat(dia) for dia in json.loads(calendario.feriados)),
        ),
        fecha_hora=fila.fecha_hora,
    )


def _a_valuacion(fila: models.Valuacion) -> Valuacion:
    return Valuacion(
        id=fila.id,
        numero=fila.numero,
        desde=fila.desde,
        hasta=fila.hasta,
        fecha=fila.fecha,
        inspector=fila.inspector,
        lineas=tuple(
            LineaValuacion(
                linea.codigo_partida, linea.cantidad, linea.fecha_medicion, linea.observacion
            )
            for linea in fila.lineas
        ),
        origen=fila.origen,
        fuente=fila.fuente,
        responsable=fila.responsable,
        fecha_hora=fila.fecha_hora,
    )


def valuaciones_registradas(
    session: Session, proyecto_nombre: str, *, con_anuladas: bool = False
) -> list[Valuacion]:
    """Las valuaciones del proyecto en el orden en que se registraron. Por defecto, solo las no
    anuladas (las que cuentan)."""
    proyecto = _proyecto(session, proyecto_nombre)
    filas = session.scalars(
        select(models.Valuacion)
        .where(models.Valuacion.proyecto_id == proyecto.id)
        .order_by(models.Valuacion.id)
    )
    return [_a_valuacion(fila) for fila in filas if con_anuladas or fila.anulacion is None]


def instantanea_control(
    session: Session,
    proyecto_nombre: str,
    *,
    catalogo: Catalogo,
    corte: date | None = None,
) -> InstantaneaControl:
    """La instantánea de control al `corte` (por defecto, el *hasta* de la última valuación no
    anulada). Usa la línea base vigente al corte: la de mayor `desde` menor o igual a él.

    `LineaBaseInvalidada` si la moneda del proyecto ya no es la de la versión de esa línea base
    (RV-11): hay que declararla de nuevo sobre la versión convertida. `ValueError` si no hay línea
    base a esa fecha o, sin `corte`, ninguna valuación."""
    proyecto = _proyecto(session, proyecto_nombre)
    cuentan = valuaciones_registradas(session, proyecto_nombre)
    if corte is None:
        if not cuentan:
            raise ValueError("no hay valuaciones registradas: elija la fecha de corte")
        corte = max(v.hasta for v in cuentan)
    candidatas = [fila for fila in _lineas_base(session, proyecto.id) if fila.desde <= corte]
    if not candidatas:
        raise ValueError(f"no hay linea base de control declarada al {corte.isoformat()}")
    fila = candidatas[-1]
    version = session.get(models.Presupuesto, fila.presupuesto_id)
    moneda = moneda_del_proyecto(session, proyecto)
    if version.moneda != moneda:
        raise LineaBaseInvalidada(f"{MENSAJE_INVALIDADA} sobre la version en {moneda}")
    plan = plan_de_version(session, version)
    if plan is None:
        raise ValueError(f"la version {version.codigo!r} no tiene plan de trabajo")
    presupuesto = cargar_presupuesto(session, proyecto_nombre, version.codigo, catalogo)
    costos = tuple(
        CostoReal(
            c.id,
            c.monto,
            c.moneda,
            c.fecha,
            c.fuente,
            c.responsable,
            c.codigo_partida,
            c.valuacion_id,
        )
        for c in session.scalars(
            select(models.CostoReal)
            .where(models.CostoReal.proyecto_id == proyecto.id)
            .order_by(models.CostoReal.id)
        )
    )
    return InstantaneaControl(
        proyecto=proyecto_nombre,
        corte=corte,
        linea_base=_a_linea_base(fila, proyecto_nombre, version.codigo),
        presupuesto=presupuesto,
        plan=tuple((etiqueta, tuple(reparto)) for etiqueta, reparto in plan),
        parametros_costo=_parametros_de(version),
        moneda=moneda,
        valuaciones=tuple(cuentan),
        costos=costos,
    )


def dia_del_corte(instantanea: InstantaneaControl) -> int:
    """El número de día hábil del corte en el calendario de la línea base."""
    calendario = instantanea.calendario
    return numero_de_dia(calendario.fecha_inicio, instantanea.corte, frozenset(calendario.feriados))


# ---------------------------------------------------------------------------------------------
# Lo que se entrega a S1: lo ejecutado por período (RF-72, S2-R16)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LineaEjecutada:
    """Lo ejecutado de una partida en un período: `cantidad` es la del período y `reajustable`
    `min(Q al cierre, q) - min(Q al cierre anterior, q)`; `valuaciones` son las que la aportan.
    Una partida que la línea base no tiene (`en_linea_base` falso) no tiene reajustable: R13 la
    marca y no se entrega a S1, que no tiene PU del contrato para ella."""

    codigo: str
    cantidad: Decimal
    reajustable: Decimal
    valuaciones: tuple[str, ...]
    en_linea_base: bool = True


@dataclass(frozen=True, slots=True)
class EjecutadoDelPeriodo:
    """Lo ejecutado de un período de la cláusula: las valuaciones citadas, las partidas y los
    avisos (por ejemplo, lo ejecutado por encima de lo presupuestado, que R13 marca)."""

    desde: date
    hasta: date
    valuaciones: tuple[Valuacion, ...]
    lineas: tuple[LineaEjecutada, ...]
    avisos: tuple[str, ...] = field(default=())


def _cantidades_de_la_linea_base(version: models.Presupuesto) -> dict[str, Decimal]:
    cantidades: dict[str, Decimal] = defaultdict(lambda: CERO)
    for renglon in version.partidas:
        cantidades[renglon.partida.codigo] += renglon.cantidad
    return cantidades


def ejecutado_por_periodo(
    session: Session,
    proyecto_nombre: str,
    periodos: Sequence[tuple[date, date]],
) -> tuple[EjecutadoDelPeriodo, ...]:
    """Lo ejecutado de cada período `(desde, hasta)` de la cláusula, con las valuaciones
    registradas y no anuladas, cada una entera en el período que contiene su *hasta* (S2-R16).

    La cantidad reajustable usa lo acumulado desde el inicio de la obra (incluidas las valuaciones
    de períodos anteriores al primero que se pide) contra lo presupuestado de la línea base
    vigente al último cierre. `LineaBaseInvalidada` si un cambio de moneda la invalidó."""
    if not periodos:
        raise ValueError("pida al menos un periodo")
    ordenados = sorted(periodos)
    proyecto = _proyecto(session, proyecto_nombre)
    cierre = ordenados[-1][1]
    candidatas = [f for f in _lineas_base(session, proyecto.id) if f.desde <= cierre]
    if not candidatas:
        raise ValueError(f"no hay linea base de control declarada al {cierre.isoformat()}")
    version = session.get(models.Presupuesto, candidatas[-1].presupuesto_id)
    if version.moneda != moneda_del_proyecto(session, proyecto):
        raise LineaBaseInvalidada(MENSAJE_INVALIDADA)
    presupuestado = _cantidades_de_la_linea_base(version)
    cuentan = valuaciones_registradas(session, proyecto_nombre)
    acumulado: dict[str, Decimal] = defaultdict(lambda: CERO)
    for valuacion in cuentan:
        if valuacion.hasta < ordenados[0][0]:
            for linea in valuacion.lineas:
                acumulado[linea.codigo_partida] += linea.cantidad
    salida: list[EjecutadoDelPeriodo] = []
    for desde, hasta in ordenados:
        del_periodo = [v for v in cuentan if desde <= v.hasta <= hasta]
        cantidades: dict[str, Decimal] = defaultdict(lambda: CERO)
        citas: dict[str, list[str]] = defaultdict(list)
        for valuacion in del_periodo:
            for linea in valuacion.lineas:
                cantidades[linea.codigo_partida] += linea.cantidad
                if valuacion.clave not in citas[linea.codigo_partida]:
                    citas[linea.codigo_partida].append(valuacion.clave)
        lineas: list[LineaEjecutada] = []
        avisos: list[str] = []
        for codigo, cantidad in cantidades.items():
            q = presupuestado.get(codigo, CERO)
            antes = acumulado[codigo]
            despues = antes + cantidad
            reajustable = min(despues, q) - min(antes, q)
            acumulado[codigo] = despues
            lineas.append(
                LineaEjecutada(
                    codigo, cantidad, reajustable, tuple(citas[codigo]), codigo in presupuestado
                )
            )
            if reajustable != cantidad:
                avisos.append(
                    f"{codigo}: ejecutado {cantidad} en el periodo y solo {reajustable} es "
                    f"reajustable (presupuestado {q}; lo que excede lo marca R13)"
                )
        salida.append(
            EjecutadoDelPeriodo(desde, hasta, tuple(del_periodo), tuple(lineas), tuple(avisos))
        )
    return tuple(salida)


# ---------------------------------------------------------------------------------------------
# Importación de Excel (RF-73, §6.2)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CostoLeido:
    """Una fila de la hoja `Costos`: el costo, y el número de la valuación que lo cita si lo hay."""

    numero: str
    codigo_partida: str | None
    monto: Decimal
    moneda: str
    fecha: date
    fuente: str


@dataclass(frozen=True, slots=True)
class LecturaControl:
    """Lo que se lee del XLSX antes de escribir nada: las valuaciones (sin registrar), los costos
    y el informe previo (una línea por hoja)."""

    valuaciones: tuple[Valuacion, ...]
    costos: tuple[CostoLeido, ...]
    informe: tuple[str, ...]


def _donde(ruta: Path, hoja: str, fila: int | None = None) -> str:
    return f"{ruta.name}, hoja {hoja}" + (f", fila {fila}" if fila is not None else "")


def _decimal(texto: str, donde: str, columna: str) -> Decimal:
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ValueError(f"{donde}: {columna} {texto!r} no es un numero decimal") from None
    if not valor.is_finite():
        raise ValueError(f"{donde}: {columna} {texto!r} no es un numero finito")
    return valor


def _fecha(texto: str, donde: str, columna: str, *, opcional: bool = False) -> date | None:
    if not texto and opcional:
        return None
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        raise ValueError(f"{donde}: {columna} {texto!r} no es una fecha ISO (AAAA-MM-DD)") from None


def _filas(ruta: Path, hoja: str, columnas: tuple[str, ...]) -> list[tuple[int, dict[str, str]]]:
    tabla = leer_tabla(ruta, hoja)
    faltan = [c for c in columnas if c not in tabla.columns]
    if faltan:
        raise ValueError(
            f"{_donde(ruta, hoja)}: faltan las columnas {', '.join(faltan)}; "
            f"se esperan {', '.join(columnas)}"
        )
    return [
        (numero, {c: str(fila[c]).strip() for c in columnas})
        for numero, fila in enumerate(tabla.to_dict("records"), start=PRIMERA_FILA_DE_DATOS)
    ]


def leer_valuaciones_excel(ruta: Path) -> LecturaControl:
    """Lee un XLSX de valuaciones (y costos) con las hojas y columnas de §6.2. No toca la base.

    Todo error de forma es `ValueError` con el archivo, la hoja y la fila, sin *traceback* útil
    para el usuario: archivo de más de 20 MB, formato que no es XLSX, hoja o columna ausente,
    número repetido, número de `Lineas` sin su valuación, fecha o número ilegibles, cantidad
    negativa. Un archivo malformado se rechaza entero."""
    if ruta.suffix.lower() not in (".xlsx", ".xlsm"):
        raise ValueError(f"{ruta.name}: las valuaciones se importan de un libro .xlsx")
    if ruta.stat().st_size > LIMITE_BYTES:
        raise ValueError(f"{ruta.name}: pesa mas de {LIMITE_BYTES // (1024 * 1024)} MB")
    cabeceras: dict[str, dict[str, str]] = {}
    for numero, fila in _filas(ruta, HOJA_VALUACIONES, COLUMNAS_VALUACIONES):
        donde = _donde(ruta, HOJA_VALUACIONES, numero)
        if not fila["numero"]:
            raise ValueError(f"{donde}: falta el numero de la valuacion")
        if fila["numero"] in cabeceras:
            raise ValueError(f"{donde}: el numero {fila['numero']} esta repetido en el archivo")
        _fecha(fila["desde"], donde, "desde")
        _fecha(fila["hasta"], donde, "hasta")
        _fecha(fila["fecha"], donde, "fecha", opcional=True)
        cabeceras[fila["numero"]] = fila
    lineas: dict[str, list[LineaValuacion]] = defaultdict(list)
    for numero, fila in _filas(ruta, HOJA_LINEAS, COLUMNAS_LINEAS):
        donde = _donde(ruta, HOJA_LINEAS, numero)
        if fila["numero"] not in cabeceras:
            raise ValueError(
                f"{donde}: la valuacion {fila['numero']!r} no esta en la hoja {HOJA_VALUACIONES}"
            )
        cantidad = _decimal(fila["cantidad"], donde, "cantidad")
        try:
            lineas[fila["numero"]].append(
                LineaValuacion(
                    fila["codigo_partida"],
                    cantidad,
                    _fecha(fila["fecha_medicion"], donde, "fecha_medicion", opcional=True),
                    fila["observacion"],
                )
            )
        except ValueError as error:
            raise ValueError(f"{donde}: {error}") from None
    sin_lineas = [n for n in cabeceras if not lineas[n]]
    if sin_lineas:
        raise ValueError(
            f"{_donde(ruta, HOJA_LINEAS)}: las valuaciones {', '.join(sin_lineas)} no tienen lineas"
        )
    valuaciones = tuple(
        Valuacion(
            id=0,
            numero=n,
            desde=_fecha(c["desde"], "", "desde"),
            hasta=_fecha(c["hasta"], "", "hasta"),
            fecha=_fecha(c["fecha"], "", "fecha", opcional=True),
            inspector=c["inspector"],
            lineas=tuple(lineas[n]),
            origen=f"{PREFIJO_ORIGEN_EXCEL}{ruta.name}",
        )
        for n, c in cabeceras.items()
    )
    costos = _leer_costos(ruta, cabeceras)
    informe = (
        f"{HOJA_VALUACIONES}: {len(valuaciones)} valuacion(es)",
        f"{HOJA_LINEAS}: {sum(len(v.lineas) for v in valuaciones)} linea(s)",
        f"{HOJA_COSTOS}: {len(costos)} costo(s)",
    )
    return LecturaControl(valuaciones, costos, informe)


def _leer_costos(ruta: Path, cabeceras: Mapping[str, object]) -> tuple[CostoLeido, ...]:
    if HOJA_COSTOS not in _hojas(ruta):
        return ()
    costos: list[CostoLeido] = []
    for numero, fila in _filas(ruta, HOJA_COSTOS, COLUMNAS_COSTOS):
        donde = _donde(ruta, HOJA_COSTOS, numero)
        if fila["numero"] and fila["numero"] not in cabeceras:
            raise ValueError(f"{donde}: la valuacion {fila['numero']!r} no esta en el archivo")
        if not fila["fuente"]:
            raise ValueError(f"{donde}: falta la fuente del costo")
        monto = _decimal(fila["monto"], donde, "monto")
        if monto < CERO:
            raise ValueError(f"{donde}: el monto no puede ser negativo ({monto})")
        try:
            moneda = exigir_moneda(fila["moneda"])
        except ValueError as error:
            raise ValueError(f"{donde}: {error}") from None
        costos.append(
            CostoLeido(
                fila["numero"],
                fila["codigo_partida"] or None,
                monto,
                moneda,
                _fecha(fila["fecha"], donde, "fecha"),
                fila["fuente"],
            )
        )
    return tuple(costos)


def _hojas(ruta: Path) -> list[str]:
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True)
    try:
        return list(libro.sheetnames)
    finally:
        libro.close()


def registrar_lectura(
    session: Session,
    proyecto_nombre: str,
    lectura: LecturaControl,
    *,
    fuente: str,
    responsable: str,
    ahora: datetime | None = None,
) -> tuple[list[models.Valuacion], list[models.CostoReal]]:
    """Registra todo lo leído, o nada: una valuación del archivo con el mismo número que una
    guardada y no anulada se rechaza (el archivo no corrige: se anula y se vuelve a registrar)."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    guardadas = {v.numero for v in valuaciones_registradas(session, proyecto_nombre)}
    repetidas = sorted(v.numero for v in lectura.valuaciones if v.numero in guardadas)
    if repetidas:
        raise ValueError(
            f"las valuaciones {', '.join(repetidas)} ya estan registradas: anule la anterior y "
            "vuelva a importar"
        )
    registradas = [
        registrar_valuacion(
            session,
            proyecto_nombre,
            numero=v.numero,
            desde=v.desde,
            hasta=v.hasta,
            fecha=v.fecha,
            inspector=v.inspector,
            lineas=v.lineas,
            fuente=fuente,
            responsable=responsable,
            origen=v.origen,
            ahora=ahora,
        )
        for v in lectura.valuaciones
    ]
    por_numero = {fila.numero: fila.id for fila in registradas}
    costos = [
        registrar_costo(
            session,
            proyecto_nombre,
            monto=c.monto,
            moneda=c.moneda,
            fecha=c.fecha,
            fuente=c.fuente,
            responsable=responsable,
            codigo_partida=c.codigo_partida,
            valuacion_id=por_numero.get(c.numero),
        )
        for c in lectura.costos
    ]
    return registradas, costos


# ---------------------------------------------------------------------------------------------
# Tablas para el Excel y el paquete
# ---------------------------------------------------------------------------------------------

TITULO_VALUACIONES = "Valuaciones"
COLUMNAS_TABLA_VALUACIONES = (
    "Numero",
    "Desde",
    "Hasta",
    "Fecha",
    "Inspector",
    "Partida",
    "Cantidad",
    "Fecha de medicion",
    "Observacion",
    "Origen",
    "Registrada",
    "Estado",
)


def tabla_valuaciones(
    valuaciones: Sequence[Valuacion],
    *,
    anuladas: Sequence[Valuacion] = (),
    estados: Mapping[str, str] | None = None,
) -> TablaExportable:
    """Las valuaciones como la hoja «Valuaciones» del Excel (una fila por línea), con su fecha de
    registro y, si se pasa, el peor hallazgo de R13-R14 de cada una (`estados`, por su clave)."""
    estados = estados or {}
    filas = []
    for valuacion, estado_base in [(v, None) for v in valuaciones] + [
        (v, "ANULADA") for v in anuladas
    ]:
        for linea in valuacion.lineas:
            filas.append(
                (
                    valuacion.numero,
                    valuacion.desde,
                    valuacion.hasta,
                    valuacion.fecha,
                    valuacion.inspector,
                    linea.codigo_partida,
                    linea.cantidad,
                    linea.fecha_medicion,
                    linea.observacion,
                    valuacion.origen,
                    valuacion.fecha_hora,
                    estado_base or estados.get(valuacion.clave, ""),
                )
            )
    return TablaExportable(TITULO_VALUACIONES, COLUMNAS_TABLA_VALUACIONES, tuple(filas))


def anexo_control(session: Session, proyecto_nombre: str) -> dict[str, object]:
    """Todas las filas de control del proyecto como datos planos (textos y listas), para
    `anexos/control.json` del paquete de S3 (RV-8): líneas base con su calendario, parámetros,
    valuaciones con sus líneas y anulaciones, costos reales y citas. Las anuladas se incluyen,
    marcadas, con su fecha de registro. Es de solo lectura y determinista."""
    proyecto = _proyecto(session, proyecto_nombre)
    codigos = {
        fila.id: fila.codigo
        for fila in session.scalars(
            select(models.Presupuesto).where(models.Presupuesto.proyecto_id == proyecto.id)
        )
    }
    return {
        "lineas_base": [
            {
                "id": f.id,
                "version": codigos[f.presupuesto_id],
                "desde": f.desde.isoformat(),
                "perspectiva": f.perspectiva,
                "fuente": f.fuente,
                "responsable": f.responsable,
                "fecha_hora": f.fecha_hora.isoformat(),
                "inicio": f.calendario.fecha_inicio.isoformat(),
                "dias_por_periodo": f.calendario.dias_por_periodo,
                "feriados": json.loads(f.calendario.feriados),
            }
            for f in _lineas_base(session, proyecto.id)
        ],
        "valuaciones": [
            {
                "id": v.id,
                "numero": v.numero,
                "desde": v.desde.isoformat(),
                "hasta": v.hasta.isoformat(),
                "fecha": None if v.fecha is None else v.fecha.isoformat(),
                "inspector": v.inspector,
                "origen": v.origen,
                "fuente": v.fuente,
                "responsable": v.responsable,
                "fecha_hora": v.fecha_hora.isoformat(),
                "anulada": None
                if v.anulacion is None
                else {
                    "motivo": v.anulacion.motivo,
                    "responsable": v.anulacion.responsable,
                    "fecha_hora": v.anulacion.fecha_hora.isoformat(),
                },
                "lineas": [
                    {
                        "partida": linea.codigo_partida,
                        "cantidad": str(linea.cantidad),
                        "fecha_medicion": None
                        if linea.fecha_medicion is None
                        else linea.fecha_medicion.isoformat(),
                        "observacion": linea.observacion,
                    }
                    for linea in v.lineas
                ],
            }
            for v in session.scalars(
                select(models.Valuacion)
                .where(models.Valuacion.proyecto_id == proyecto.id)
                .order_by(models.Valuacion.id)
            )
        ],
        "costos": [
            {
                "id": c.id,
                "valuacion_id": c.valuacion_id,
                "partida": c.codigo_partida,
                "monto": str(c.monto),
                "moneda": c.moneda,
                "fecha": c.fecha.isoformat(),
                "fuente": c.fuente,
                "responsable": c.responsable,
            }
            for c in session.scalars(
                select(models.CostoReal)
                .where(models.CostoReal.proyecto_id == proyecto.id)
                .order_by(models.CostoReal.id)
            )
        ],
    }


def linea_base_vigente(
    session: Session, proyecto_nombre: str, corte: date
) -> models.LineaBaseControl | None:
    """La línea base de control vigente al `corte`, o `None` si no hay."""
    proyecto = _proyecto(session, proyecto_nombre)
    candidatas = [f for f in _lineas_base(session, proyecto.id) if f.desde <= corte]
    return candidatas[-1] if candidatas else None
