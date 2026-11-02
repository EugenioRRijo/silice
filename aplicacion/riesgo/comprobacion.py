"""Comprobación hacia atrás de la proyección del riesgo (plan vial, Tarea 14; especificación §5.1).

**Método: cortes móviles.** Para cada mes `c` de la historia se hace como si hoy fuera el primer día
de `c`: se proyecta **solo con la historia anterior a `c`** (`proyectar` con `inicio = c` no ve ese
mes ni lo posterior) y se compara el P80 con el total del mismo presupuesto revalorizado con lo que
de verdad pasó en los `meses` meses siguientes (`total_con_variaciones_reales`: el mismo motor, la
misma regla de la moneda, de la mezcla y del gasto uniforme, con las variaciones reales en lugar de
las remuestreadas). Un corte está **dentro** si `real <= P80`.

**Qué cortes entran.** Los que tienen ventana suficiente (al menos `MINIMO_DE_MESES` meses completos
antes, contados con la misma regla que la proyección) y el plazo completo después (valor de
todas las series desde el mes anterior al corte hasta el último mes del plazo). Las series son las
de la proyección (`series_presentes`): una entrada vieja del mapa no quita cortes. Los demás no
se cuentan:
`n_cortes` informa cuántos entraron. La cobertura es `dentro / n_cortes`, en `Decimal`, sin
redondear.

`p.inicio` no interviene (cada corte pone el suyo) y `p.percentiles` se ignora: cada corte reporta
P50 y P80. `trayectorias`, `semilla`, `ventana_meses` y `meses` valen para cada corte. Los cortes se
solapan (el mismo mes cae en plazos de varios cortes), así que no son observaciones independientes:
la cobertura es un indicador, no una probabilidad con intervalo.

Con los casos ficticios solo se prueba la mecánica; la cobertura que va a la tesis se calcula con
datos reales en local.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from aplicacion.riesgo.proyeccion import (
    MINIMO_DE_MESES,
    ParametrosProyeccion,
    meses_completos,
    proyectar,
    series_presentes,
    total_con_variaciones_reales,
)
from aplicacion.riesgo.series import MapaSeries
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.presupuesto import Presupuesto
from produccion.receta import Receta

__all__ = ["Comprobacion", "ResultadoCorte", "comprobar_hacia_atras"]


@dataclass(frozen=True)
class ResultadoCorte:
    corte: date
    p50: Decimal
    p80: Decimal
    real: Decimal
    dentro: bool


@dataclass(frozen=True)
class Comprobacion:
    cortes: tuple[ResultadoCorte, ...]
    cobertura: Decimal
    n_cortes: int


def _mes(base: date, desplazamiento: int) -> date:
    indice = base.year * 12 + base.month - 1 + desplazamiento
    return date(indice // 12, indice % 12 + 1, 1)


def _cortes_posibles(
    historia: Mapping[str, Mapping[date, Decimal]], series: list[str], p: ParametrosProyeccion
) -> tuple[list[date], int]:
    """Los meses que pueden ser corte y cuántos meses tienen valor en todas las series."""
    todos = [set(historia.get(s, {})) for s in series]
    comunes = set.intersection(*todos)
    if not any(todos):
        return [], len(comunes)
    primero = min(min(t) for t in todos if t)
    ultimo = max(max(t) for t in todos if t)
    minimo = int(MINIMO_DE_MESES.valor)
    cortes = []
    c = _mes(primero, 1)
    while c <= ultimo:
        pc = replace(p, inicio=c)
        plazo = [_mes(c, k) for k in range(-1, p.meses)]
        if len(meses_completos(historia, series, pc)) >= minimo and all(
            m in historia.get(s, {}) for s in series for m in plazo
        ):
            cortes.append(c)
        c = _mes(c, 1)
    return cortes, len(comunes)


def comprobar_hacia_atras(
    presupuesto: Presupuesto,
    composiciones: Mapping[str, ComposicionAPU],
    parametros_costo: ParametrosCosto,
    historia: Mapping[str, Mapping[date, Decimal]],
    mapa: MapaSeries,
    p: ParametrosProyeccion,
    *,
    recetas: Mapping[str, Receta] | None = None,
    costo_planta_por_t: Mapping[str, Decimal] | None = None,
    precio_de_componente: Mapping[str, Decimal] | None = None,
) -> Comprobacion:
    """Proyecta en cada corte móvil con la historia anterior y compara el P80 con lo que pasó.

    `historia` es la **completa** (`{serie: {primer día del mes: valor}}`), también lo posterior a
    cada corte: la proyección no lo ve, y lo real sí lo necesita. Los argumentos opcionales son los
    de `proyectar`. Las reglas están en el encabezado del módulo."""
    series = series_presentes(mapa, composiciones, recetas)
    cortes, hay = _cortes_posibles(historia, series, p)
    if not cortes:
        minimo = int(MINIMO_DE_MESES.valor)
        raise ValueError(
            f"no hay ningún corte posible: solo hay {hay} meses con todas las series y hacen "
            f"falta al menos {minimo + 1 + p.meses} ({minimo} meses completos y su mes base antes "
            f"de un corte, y {p.meses} meses del plazo después)"
        )
    kw = {
        "recetas": recetas,
        "costo_planta_por_t": costo_planta_por_t,
        "precio_de_componente": precio_de_componente,
    }
    resultados = []
    for c in cortes:
        pc = replace(p, inicio=c, percentiles=(50, 80))
        proyeccion = proyectar(
            presupuesto, composiciones, parametros_costo, historia, mapa, pc, **kw
        )
        real = total_con_variaciones_reales(
            presupuesto, composiciones, parametros_costo, historia, mapa, c, p.meses, **kw
        )
        p80 = proyeccion.percentiles[80]
        resultados.append(
            ResultadoCorte(c, proyeccion.percentiles[50], p80, real, dentro=real <= p80)
        )
    dentro = sum(1 for r in resultados if r.dentro)
    return Comprobacion(
        cortes=tuple(resultados),
        cobertura=Decimal(dentro) / Decimal(len(resultados)),
        n_cortes=len(resultados),
    )
