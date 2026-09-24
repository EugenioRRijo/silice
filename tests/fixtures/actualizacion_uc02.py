"""UC‑02 sobre la línea base con la muestra `data/samples/precios/lista_2026-06-01.csv`.

Única copia (INV‑009) de lo que esa muestra cambia y de su efecto, calculado a mano. La usan la
prueba de integración de UC‑02, la de escenarios de UC‑08 y la de la API.
"""

from __future__ import annotations

from decimal import Decimal

from tests.fixtures import apu_linea_base as linea_base

CEMENTO = "Cemento Portland"
ARENA = "Arena lavada"

#: Lo que sube la muestra, y la fracción de variación de docs/modelo_datos.md §6:
#: (nuevo − anterior) / anterior.
PRECIOS_NUEVOS = {CEMENTO: Decimal("18"), ARENA: Decimal("33")}
VARIACIONES = {CEMENTO: Decimal("0.2"), ARENA: Decimal("0.1")}

#: 7,5 sacos × (18 − 15) + 0,45 m3 × (33 − 30) = 23,85 USD de material por m3 de concreto; el
#: incremento atraviesa administración y utilidad en cascada: 23,85 × 1,15 × 1,10 = 30,17025.
INCREMENTO_PU_CONCRETO = Decimal("30.17025")

_CANTIDAD_CONCRETO = next(
    linea.cantidad
    for linea in linea_base.PRESUPUESTO_AUDITADO
    if linea.codigo_partida == linea_base.APU_CONCRETO.codigo_partida
)
#: El cómputo auditado lleva 1,66 m3 de concreto: 1,66 × 30,17025 = 50,082615.
INCREMENTO_TOTAL = INCREMENTO_PU_CONCRETO * _CANTIDAD_CONCRETO
