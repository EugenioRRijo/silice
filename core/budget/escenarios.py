"""UC‑08: escenarios de sensibilidad sobre un presupuesto base (RF‑30, RF‑31).

Un escenario responde «¿qué pasa con este presupuesto si cambian los factores de costo o unos
precios?» sin tocar nada de lo que existe: recibe el presupuesto base y sus composiciones,
recalcula **el presupuesto completo** con el motor de costos y devuelve el resultado en memoria.
Nada se persiste (decisión del diseño de F.1: los escenarios usan el mecanismo de UC‑02 sin
guardar la lista como vigente); promover un escenario a presupuesto (flujo 4a de la ERS) es
exactamente UC‑02 con la lista nueva, y ese camino ya existe en `actualizar_precios`.

Las dos variaciones del flujo principal de UC‑08:

- **`ParametrosCosto` nuevos** (FCAS, bono, administración, utilidad): mismos renglones y mismos
  desgloses, otra estructura de costos. Un parámetro fuera de rango se rechaza en el contrato
  (flujo 1a): aquí no hay nada que validar dos veces.
- **Precios de insumos nuevos** (`precios`, por descripción del insumo): se reconstruyen las
  composiciones con esos precios —material y equipo por `precio`, mano de obra por `sueldo`— y
  se recalcula. Las composiciones recibidas quedan intactas: son dataclasses congeladas y aquí
  solo se crean copias.

`elaborar` audita siempre, así que cada escenario trae su informe (principio 7 de CLAUDE.md §2):
un escenario con hallazgos nuevos es información de sensibilidad, no un defecto.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from pandas import DataFrame

# `_porcentaje` y `_comparar` son ayudantes del módulo hermano del mismo paquete: la fórmula de
# variación porcentual y la tabla por renglón tienen una sola definición (CLAUDE.md §2.1) y
# duplicarlas aquí sería repetirla. Mismo patrón que `actualizacion` con `persistencia`.
from core.budget.actualizacion import Comparativo, _comparar, _porcentaje
from core.budget.presupuesto import elaborar, exigir_composiciones
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.presupuesto import Presupuesto
from core.verification.informe import InformeAuditoria

__all__ = [
    "COLUMNAS_ESCENARIOS",
    "Escenario",
    "comparar_escenarios",
    "comparar_por_partida",
    "generar_escenario",
]

#: Columnas de la tabla comparativa de escenarios (RF‑31), en el orden en que se presentan.
COLUMNAS_ESCENARIOS = ("escenario", "total", "variacion", "variacion_pct")

CERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class Escenario:
    """Un presupuesto recalculado bajo supuestos declarados, con el informe que lo acompaña.

    `insumos_variados` cuenta los insumos cuyo precio del escenario difiere del de las
    composiciones base (análogo a `Comparativo.insumos_afectados` en UC‑02): un precio declarado
    igual al vigente no varía nada.
    """

    nombre: str
    presupuesto: Presupuesto
    informe: InformeAuditoria
    parametros: ParametrosCosto
    insumos_variados: int = 0


def generar_escenario(
    nombre: str,
    base: Presupuesto,
    composiciones: Mapping[str, ComposicionAPU],
    parametros: ParametrosCosto,
    *,
    precios: Mapping[str, Decimal] | None = None,
) -> Escenario:
    """Recalcula el presupuesto completo con `parametros` y, si se dan, `precios` nuevos (RF‑30).

    El escenario conserva los renglones del base (mismos ítems, mismo orden, misma fecha y
    moneda); su código es `«base»-«nombre»` para que ningún informe lo confunda con el base.
    El base no se altera: todos los contratos involucrados son inmutables. Exige composición
    para todo renglón del base (`ValueError`): un escenario con renglones pendientes no sería
    comparable con su base (INV‑013).
    """
    precios = dict(precios or {})
    ajustadas = (
        {codigo: _con_precios(apu, precios) for codigo, apu in composiciones.items()}
        if precios
        else dict(composiciones)
    )
    items = [partida.item for partida in base.partidas]
    exigir_composiciones(items, ajustadas)
    resultado = elaborar(
        items,
        ajustadas,
        parametros,
        codigo=f"{base.codigo}-{nombre}",
        fecha=base.fecha,
        moneda=base.moneda,
    )
    return Escenario(
        nombre=nombre,
        presupuesto=resultado.presupuesto,
        informe=resultado.informe,
        parametros=parametros,
        insumos_variados=_variados(composiciones, precios),
    )


def comparar_escenarios(base: Presupuesto, escenarios: Sequence[Escenario]) -> DataFrame:
    """La tabla de RF‑31: el base en la primera fila y una fila por escenario.

    Celdas `Decimal` (dtype `object`), como el comparativo de UC‑02: una tabla de sensibilidad
    que redondea al pasar por pandas dejaría de cuadrar con los presupuestos que compara. Se
    exporta con los medios de `DataFrame` (`to_csv`, `to_excel`).
    """
    filas = [
        {"escenario": base.codigo, "total": base.total, "variacion": CERO, "variacion_pct": CERO}
    ]
    for escenario in escenarios:
        variacion = escenario.presupuesto.total - base.total
        filas.append(
            {
                "escenario": escenario.nombre,
                "total": escenario.presupuesto.total,
                "variacion": variacion,
                "variacion_pct": _porcentaje(variacion, base.total),
            }
        )
    return DataFrame(filas, columns=list(COLUMNAS_ESCENARIOS))


def comparar_por_partida(base: Presupuesto, escenario: Escenario) -> Comparativo:
    """El detalle del paso 3 del flujo: variación por renglón entre el base y el escenario."""
    return _comparar(base, escenario.presupuesto, escenario.insumos_variados)


# ---------------------------------------------------------------------------------------------
# Variación de precios sobre composiciones congeladas
# ---------------------------------------------------------------------------------------------


def _con_precios(composicion: ComposicionAPU, precios: Mapping[str, Decimal]) -> ComposicionAPU:
    """Una copia de la composición con los precios del escenario; lo no mencionado queda igual."""
    return replace(
        composicion,
        materiales=tuple(
            replace(linea, precio=precios.get(linea.descripcion, linea.precio))
            for linea in composicion.materiales
        ),
        equipos=tuple(
            replace(linea, precio=precios.get(linea.descripcion, linea.precio))
            for linea in composicion.equipos
        ),
        mano_obra=tuple(
            replace(linea, sueldo=precios.get(linea.descripcion, linea.sueldo))
            for linea in composicion.mano_obra
        ),
    )


def _variados(
    composiciones: Mapping[str, ComposicionAPU], precios: Mapping[str, Decimal]
) -> int:
    """Cuántos insumos del escenario difieren de algún precio vigente en las composiciones."""
    return len(
        {
            descripcion
            for composicion in composiciones.values()
            for descripcion, vigente in _precios_de(composicion)
            if descripcion in precios and precios[descripcion] != vigente
        }
    )


def _precios_de(composicion: ComposicionAPU) -> Iterator[tuple[str, Decimal]]:
    for linea in composicion.materiales:
        yield linea.descripcion, linea.precio
    for linea in composicion.equipos:
        yield linea.descripcion, linea.precio
    for linea in composicion.mano_obra:
        yield linea.descripcion, linea.sueldo
