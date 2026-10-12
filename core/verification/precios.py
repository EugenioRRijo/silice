"""R11 (PrecioFueraDeRango) y R12 (PrecioVencido), reglas EXTERNAS (S1-R7, spec S1 §6.3).

No entran en `REGLAS`: la línea base sigue dando 7 de 7 y las huellas de RNF-04 no se mueven. Cada
regla guarda su instantánea con la fecha de evaluación EXPLÍCITA (M §3.3; nunca el reloj) y no lee
el presupuesto que recibe. Reevaluar a otra fecha es construir otra instantánea: nada se reescribe.

Importa solo contratos y el motor: la erosión llega precalculada en `PrecioAuditado.erosion`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad
from core.costing import calcular_apu

CODIGO_R11, CODIGO_R12 = "R11", "R12"

__all__ = [
    "CODIGO_R11",
    "CODIGO_R12",
    "InstantaneaPrecios",
    "PartidaPrecios",
    "PrecioAuditado",
    "PrecioFueraDeRango",
    "PrecioVencido",
    "estado_por_insumo",
    "reglas_precios",
]


@dataclass(frozen=True, slots=True)
class PrecioAuditado:
    """Un precio de la lista con todo lo que R11 y R12 necesitan, ya leído de la base."""

    insumo_id: int
    codigo: str
    descripcion: str
    precio: Decimal  # en la moneda de la lista
    moneda: str
    moneda_original: str
    precio_original: Decimal
    fecha_precio: date
    tasa: Decimal | None  # declarada (por precio o por la lista)
    fecha_tasa: date | None
    fuente_tasa: str
    tasa_a_su_fecha: Decimal | None  # importada, si no declara
    referencia: Decimal | None  # precio MaPreX en su moneda
    moneda_referencia: str
    tasa_referencia: Decimal | None
    codigo_referencia: str
    erosion: Decimal | None  # Δ por unidad en la moneda de la lista (0 si USD; None sin tasa)
    heredado: bool | None


@dataclass(frozen=True, slots=True)
class PartidaPrecios:
    """Una partida de la versión: su cantidad, su composición y el insumo de cada línea."""

    codigo: str
    cantidad: Decimal
    composicion: ComposicionAPU
    insumos: tuple[int | None, ...]  # alineados con (*materiales, *equipos, *mano_obra)


@dataclass(frozen=True, slots=True)
class InstantaneaPrecios:
    """Los precios auditados a una fecha de evaluación; con `partidas`, el impacto va al total."""

    fecha_evaluacion: date
    moneda: str
    precios: tuple[PrecioAuditado, ...]
    tasa_evaluacion: Decimal | None
    rango_inferior: Decimal
    rango_superior: Decimal
    plazo_vigencia_dias: int
    partidas: tuple[PartidaPrecios, ...] = ()
    parametros: ParametrosCosto = field(default_factory=ParametrosCosto)


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


def _con_delta(p: PartidaPrecios, insumo_id: int, delta: Decimal) -> ComposicionAPU:
    """La composición de `p` con `delta` sumado al precio de cada línea de `insumo_id`."""
    c = p.composicion
    nm, ne = len(c.materiales), len(c.equipos)
    lineas = [*c.materiales, *c.equipos, *c.mano_obra]
    nuevas = []
    for i, (linea, insumo) in enumerate(zip(lineas, p.insumos, strict=True)):
        if insumo != insumo_id:
            nuevas.append(linea)
        elif i >= nm + ne:
            nuevas.append(replace(linea, sueldo=linea.sueldo + delta))
        else:
            nuevas.append(replace(linea, precio=linea.precio + delta))
    return replace(
        c,
        materiales=tuple(nuevas[:nm]),
        equipos=tuple(nuevas[nm : nm + ne]),
        mano_obra=tuple(nuevas[nm + ne :]),
    )


def _usan(inst: InstantaneaPrecios, insumo_id: int) -> tuple[str, ...]:
    return tuple(p.codigo for p in inst.partidas if insumo_id in p.insumos)


def _impacto(inst: InstantaneaPrecios, insumo_id: int, delta: Decimal | None) -> Decimal | None:
    """Con versión, el Δ del total por `calcular_apu`; sin versión (lista sola), Δ por unidad."""
    if delta is None:
        return None
    if not inst.partidas:
        return abs(delta)
    total = Decimal(0)
    for p in inst.partidas:
        if insumo_id in p.insumos:
            antes = calcular_apu(p.composicion, inst.parametros).precio_unitario
            despues = calcular_apu(_con_delta(p, insumo_id, delta), inst.parametros).precio_unitario
            total += p.cantidad * (despues - antes)
    return abs(total)


def _pct(x: Decimal) -> str:
    return f"{x * 100:+.2f} %"


def _r11(inst: InstantaneaPrecios) -> list[tuple[int | None, Hallazgo]]:
    salida: list[tuple[int | None, Hallazgo]] = []
    sin_ref: list[str] = []
    sin_tasa: list[str] = []
    for p in inst.precios:
        if p.referencia is None:
            sin_ref.append(p.descripcion)
            continue
        t_p = Decimal(1) if p.moneda == "USD" else (p.tasa or p.tasa_a_su_fecha)
        t_r = Decimal(1) if p.moneda_referencia == "USD" else p.tasa_referencia
        if t_p is None or t_r is None:
            sin_tasa.append(p.descripcion)
            continue
        with _contexto():
            desvio = (p.precio * t_r) / (p.referencia * t_p) - 1  # una división, sin cuantizar
            if inst.rango_inferior <= desvio <= inst.rango_superior:
                continue
            delta = p.referencia * t_p / t_r - p.precio
        salida.append(
            (
                p.insumo_id,
                Hallazgo(
                    CODIGO_R11,
                    Severidad.ADVERTENCIA,
                    f"{p.descripcion}: {_pct(desvio)} frente a MaPreX {p.codigo_referencia} "
                    f"(precio del {p.fecha_precio:%d/%m/%Y}; "
                    f"evaluado al {inst.fecha_evaluacion:%d/%m/%Y})",
                    impacto=_impacto(inst, p.insumo_id, delta),
                    origen_ids=_usan(inst, p.insumo_id),
                    valor_observado=desvio,
                ),
            )
        )
    if sin_ref or sin_tasa:
        n = len(sin_ref) + len(sin_tasa)
        salida.append(
            (
                None,
                Hallazgo(
                    CODIGO_R11,
                    Severidad.INFO,
                    f"{n} insumos no contrastables: {len(sin_ref)} sin referencia MaPreX "
                    f"({', '.join(sin_ref)}), {len(sin_tasa)} sin tasa a su fecha "
                    f"({', '.join(sin_tasa)})",
                    valor_observado=Decimal(n),
                ),
            )
        )
    return salida


def _r12(inst: InstantaneaPrecios) -> list[tuple[int | None, Hallazgo]]:
    salida: list[tuple[int | None, Hallazgo]] = []
    for p in inst.precios:
        dias = (inst.fecha_evaluacion - p.fecha_precio).days
        motivo = "" if p.erosion is not None else "; sin tasa a la fecha del precio o de evaluacion"
        if dias > inst.plazo_vigencia_dias:
            salida.append(
                (
                    p.insumo_id,
                    Hallazgo(
                        CODIGO_R12,
                        Severidad.ADVERTENCIA,
                        f"{p.descripcion}: precio del {p.fecha_precio:%d/%m/%Y} con {dias} dias "
                        f"al {inst.fecha_evaluacion:%d/%m/%Y} (plazo {inst.plazo_vigencia_dias})"
                        f"{motivo}",
                        impacto=_impacto(inst, p.insumo_id, p.erosion),
                        origen_ids=_usan(inst, p.insumo_id),
                        valor_observado=Decimal(dias),
                        valor_esperado=Decimal(inst.plazo_vigencia_dias),
                    ),
                )
            )
        if p.tasa is not None and p.fecha_tasa is None:
            salida.append(
                (
                    p.insumo_id,
                    Hallazgo(
                        CODIGO_R12,
                        Severidad.ERROR,
                        f"{p.descripcion}: la tasa {p.tasa} no tiene fecha; el precio no es "
                        "trazable",
                        origen_ids=_usan(inst, p.insumo_id),
                    ),
                )
            )
        elif p.tasa is not None and not p.fuente_tasa.strip():
            usd = " (precio original en USD: erosion 0 declarada)"
            salida.append(
                (
                    p.insumo_id,
                    Hallazgo(
                        CODIGO_R12,
                        Severidad.ADVERTENCIA,
                        f"{p.descripcion}: la tasa {p.tasa} del {p.fecha_tasa:%d/%m/%Y} no "
                        f"declara fuente{usd if p.moneda_original == 'USD' else ''}",
                        impacto=_impacto(inst, p.insumo_id, p.erosion),
                        origen_ids=_usan(inst, p.insumo_id),
                    ),
                )
            )
    return salida


class PrecioFueraDeRango(ReglaVerificacion):
    """R11: el precio de la lista frente a su referencia, fuera de [rango inferior, superior]."""

    codigo = CODIGO_R11
    nombre = "Precio fuera de rango frente a MaPreX"

    def __init__(self, instantanea: InstantaneaPrecios) -> None:
        self.instantanea = instantanea

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return [h for _, h in _r11(self.instantanea)]


class PrecioVencido(ReglaVerificacion):
    """R12: precio más viejo que el plazo, o con tasa sin fecha o sin fuente."""

    codigo = CODIGO_R12
    nombre = "Precio vencido o sin trazabilidad de tasa"

    def __init__(self, instantanea: InstantaneaPrecios) -> None:
        self.instantanea = instantanea

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return [h for _, h in _r12(self.instantanea)]


def reglas_precios(instantanea: InstantaneaPrecios) -> tuple[ReglaVerificacion, ...]:
    return (PrecioFueraDeRango(instantanea), PrecioVencido(instantanea))


def estado_por_insumo(instantanea: InstantaneaPrecios) -> dict[int, list[str]]:
    """Textos de R11/R12 por insumo, de la MISMA evaluación (columna Estado de Precios)."""
    estado: dict[int, list[str]] = {}
    for insumo_id, h in [*_r11(instantanea), *_r12(instantanea)]:
        if insumo_id is not None:
            estado.setdefault(insumo_id, []).append(
                f"{h.regla} {h.severidad.name}: {h.descripcion}"
            )
    return estado
