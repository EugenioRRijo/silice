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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import partial

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
    "Calendario",
    "CostoReal",
    "InstantaneaControl",
    "LineaBase",
    "LineaBaseInvalidada",
    "anexo_control",
    "anular_valuacion",
    "instantanea_control",
    "registrar_costo",
    "registrar_linea_base",
    "registrar_valuacion",
    "tabla_valuaciones",
]

CERO = Decimal(0)
ORIGEN_MANUAL = "manual"
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


# ---------------------------------------------------------------------------------------------
# Importación de Excel (RF-73, §6.2)
# ---------------------------------------------------------------------------------------------


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
