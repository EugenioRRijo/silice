"""Hoja del proyecto, trabajo (`aplicacion/hoja.py`): filtro de partidas y cierre del APU.

Movidas sin cambio de logica desde `tests/unit/test_ui_hoja_trabajo.py` (retiro de Streamlit, F3);
solo cambia el import (`ui.hoja` era la copia de `aplicacion.hoja`). Oraculo: OB-B a mano
(memoria `control_ob_s2.md` §1: materiales 3,00, equipos 0,15, mano de obra 1,85; costo directo
5,00; con administracion 5,75; precio unitario 6,325). Datos ficticios (NORMAS.md §1).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from aplicacion import hoja
from core.costing.motor import calcular_apu
from tests.fixtures import control_ob_s2 as ob

D = Decimal


CODIGOS = ["AF-TUB-PVC-3/4", "EL-CAB-12", "DT-UTP-CAT-6", "SIN-DESC"]


DESCRIPCIONES = {
    "AF-TUB-PVC-3/4": "Tubería PVC 3/4 pulg de agua fría",
    "EL-CAB-12": "Cable ELÉCTRICO 12 AWG",
    "DT-UTP-CAT-6": "Cable UTP categoría 6",
}


@pytest.mark.parametrize(
    ("texto", "esperados"),
    [
        ("", CODIGOS),
        ("   ", CODIGOS),
        ("tuberia", ["AF-TUB-PVC-3/4"]),  # sin acento encuentra «Tubería»
        ("ELECTRICO", ["EL-CAB-12"]),  # sin mayúsculas ni acentos
        ("cable", ["EL-CAB-12", "DT-UTP-CAT-6"]),  # el orden de entrada se conserva
        ("cab-12", ["EL-CAB-12"]),  # por código
        ("sin-desc", ["SIN-DESC"]),  # una partida sin descripción solo coincide por código
        ("  fria  ", ["AF-TUB-PVC-3/4"]),
        ("zzz", []),
    ],
)
def test_filtrar_partidas(texto, esperados):
    assert hoja.filtrar_partidas(CODIGOS, DESCRIPCIONES, texto) == esperados


def test_filtrar_partidas_no_cambia_la_lista_de_entrada():
    codigos = list(CODIGOS)
    resultado = hoja.filtrar_partidas(codigos, DESCRIPCIONES, "")
    assert resultado == codigos and resultado is not codigos


def test_el_cierre_de_ob_b_es_la_cascada_de_calcular_apu_a_mano():
    resultado = calcular_apu(ob.composiciones()["OB-B"], ob.PARAMETROS)
    filas = hoja.filas_de_cierre(resultado, ob.PARAMETROS, "USD")
    assert [(f["Concepto"], f["Monto"]) for f in filas] == [
        ("Materiales", "3.00 USD"),
        ("Equipos", "0.15 USD"),
        ("Mano de obra", "1.85 USD"),
        ("= Costo directo", "5.00 USD"),
        ("+ Administracion", "0.75 USD"),  # 5,00 × 0,15
        ("= Con administracion", "5.75 USD"),
        ("+ Utilidad", "0.58 USD"),  # 5,75 × 0,10 = 0,575: la mitad sube
        ("= Precio unitario", "6.33 USD"),  # 6,325
    ]
    notas = {f["Concepto"]: f["Nota"] for f in filas}
    assert notas["Materiales"] == "completos"
    assert notas["Equipos"] == "entre el rendimiento"
    assert notas["Mano de obra"] == "FCAS 6 y bono 1, entre el rendimiento"
    assert notas["+ Administracion"] == "15.0 % del costo directo"
    assert notas["+ Utilidad"] == "10.0 % en cascada"


def test_el_cierre_sigue_a_los_factores_y_cada_paso_suma_el_anterior():
    """Con administración 0,20 y utilidad 0,25 sobre OB-A (costo directo 10,00): 2,00 y 3,00."""
    parametros = replace(ob.PARAMETROS, administracion=D("0.20"), utilidad=D("0.25"))
    resultado = calcular_apu(ob.composiciones()["OB-A"], parametros)
    filas = {f["Concepto"]: f for f in hoja.filas_de_cierre(resultado, parametros, "Bs")}
    assert filas["= Costo directo"]["Monto"] == "10.00 Bs"
    assert filas["+ Administracion"]["Monto"] == "2.00 Bs"
    assert filas["= Con administracion"]["Monto"] == "12.00 Bs"
    assert filas["+ Utilidad"]["Monto"] == "3.00 Bs"
    assert filas["= Precio unitario"]["Monto"] == "15.00 Bs"
    assert filas["Materiales"]["Monto"] == "0.00 Bs"  # OB-A no lleva material
