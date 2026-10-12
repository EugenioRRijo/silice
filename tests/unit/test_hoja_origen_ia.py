"""La hoja muestra «Propuesta de IA» (S4 §5.4, RF-92; plan 0.9.0, tarea 4).

El rotulo del tipo de origen y la procedencia de una partida cuyo `origen_id` empieza por `ia:`.
Ninguna otra fila cambia su Estado (los textos de las pruebas de SF3 siguen iguales).
"""

from __future__ import annotations

from decimal import Decimal

from core.contracts import ItemComputo
from core.contracts.dominio import Dominio
from core.contracts.item_computo import OrigenTipo
from core.verification.informe import InformeAuditoria
from ui.hoja import PREFIJO_ORIGEN_IA, estado_de_items, rotulo_de_valor


def item(origen_id: str) -> ItemComputo:
    return ItemComputo(
        "AF-SALIDA", "Salida", "punto", Decimal(2), origen_id, OrigenTipo.MANUAL, Dominio.CIVIL
    )


def test_el_tipo_de_origen_ia_tiene_su_rotulo_en_espanol():
    assert rotulo_de_valor("ia") == "Propuesta de IA"
    assert PREFIJO_ORIGEN_IA == "ia:"


def test_una_partida_propuesta_por_la_ia_lleva_su_procedencia_en_el_estado():
    informe = InformeAuditoria(codigo_presupuesto="X")
    estados = estado_de_items([item("ia:7:P5"), item("manual-1")], informe)
    assert [e.texto for e in estados.values()] == ["OK | Propuesta de IA (sesion 7)", "OK"]
    assert all(e.severidad is None for e in estados.values())
