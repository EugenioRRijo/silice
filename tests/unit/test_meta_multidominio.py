"""Pruebas de `scripts/meta_multidominio.py` (sprint multidominio).

Como `test_meta_alpha.py`, solo se ejercitan funciones puras: nunca se ejecuta pytest, ruff ni git
desde estas pruebas. El texto es sintético a propósito, para no acoplar la meta a cuántas partidas
tenga hoy el fixture industrial.
"""

from scripts import meta_multidominio


def test_codigos_partida_industrial_distingue_partidas_del_mismo_activo():
    """`MNT-\\w+` cortaba en el segundo guion y contaba MNT-BOM-CEN y MNT-BOM-SUM como una."""
    texto = (
        '"MNT-BOM-CEN": 20, "MNT-BOM-SUM": 30, "MNT-COM-REC": 30, "MNT-MOT-TRI": 20, "MNT-BOM-CEN"'
    )

    assert meta_multidominio.codigos_partida_industrial(texto) == [
        "MNT-BOM-CEN",
        "MNT-BOM-SUM",
        "MNT-COM-REC",
        "MNT-MOT-TRI",
    ]


def test_codigos_partida_industrial_ignora_prefijo_suelto_y_codigo_de_presupuesto():
    texto = 'PREFIJO = "MNT-"  # presupuesto MNT-001 con partidas MNT-*'

    assert meta_multidominio.codigos_partida_industrial(texto) == []
