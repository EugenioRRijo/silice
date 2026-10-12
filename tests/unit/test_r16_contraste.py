"""R16: contraste entre dos fuentes, con las fronteras exactas de S3 §11.4 (RF-89)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from adapters.espacio.planos.contraste import CODIGO_R16, ReglaContraste, contrastar
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Severidad
from tests.fixtures.espacio_minimo import ambiente, espacio, punto_de_datos, rack, toma

PRESUPUESTO = Presupuesto(codigo="X", fecha=date(2026, 11, 1), moneda="USD", partidas=())


def un_punto(x: str):
    return espacio([ambiente("A", largo="10")], [punto_de_datos("P1", x)])


REFERENCIA = un_punto("1")


@pytest.mark.parametrize("x,tipo", [("1.10", None), ("1.11", "desplazado"), ("2.00", "desplazado"),
                                    ("2.01", "faltante")])
def test_fronteras_de_tolerancia_y_de_radio(x: str, tipo: str | None) -> None:
    """0,10 m emparejado / 0,11 desplazado; 1,00 desplazado / 1,01 faltante y sobrante."""
    contraste = contrastar(un_punto(x), REFERENCIA)
    puntos = [d for d in contraste.diferencias if d.tabla == "esp_puntos"]
    if tipo is None:
        assert puntos == [] and contraste.emparejadas == 2  # el ambiente y el punto
    elif tipo == "desplazado":
        [d] = puntos
        assert (d.tipo, d.id_plano, d.id_referencia) == ("desplazado", "P1", "P1")
        assert d.distancia == Decimal(x) - Decimal("1")
    else:
        assert sorted(d.tipo for d in puntos) == ["faltante", "sobrante"]


def test_un_elemento_borrado_entre_las_dos_fuentes_es_faltante() -> None:
    plano = espacio([ambiente("A", largo="10")], [punto_de_datos("P1", "1")])
    levantamiento = espacio([ambiente("A", largo="10")],
                            [punto_de_datos("P1", "1"), punto_de_datos("P2", "5")])
    [d] = contrastar(plano, levantamiento).diferencias
    assert (d.tipo, d.id_plano, d.id_referencia, d.clase) == (
        "faltante", None, "P2", "datos/datos")


def test_un_elemento_que_solo_esta_en_el_plano_es_sobrante() -> None:
    plano = espacio([ambiente("A", largo="10")],
                    [punto_de_datos("P1", "1"), punto_de_datos("P9", "7")])
    [d] = contrastar(plano, REFERENCIA).diferencias
    assert (d.tipo, d.id_plano, d.id_referencia) == ("sobrante", "P9", None)


def test_el_emparejamiento_es_uno_a_uno_y_por_el_vecino_mas_cercano() -> None:
    plano = espacio([ambiente("A", largo="10")],
                    [punto_de_datos("N1", "1.05"), punto_de_datos("N2", "1.5")])
    levantamiento = espacio([ambiente("A", largo="10")], [punto_de_datos("L1", "1")])
    contraste = contrastar(plano, levantamiento)
    tipos = {(d.tipo, d.id_plano, d.id_referencia) for d in contraste.diferencias}
    assert tipos == {("sobrante", "N2", None)}  # N1 se queda con L1 (0,05 m); N2 sobra


def test_no_se_empareja_entre_clases_distintas() -> None:
    plano = espacio([ambiente("A")], [toma("T1", "1")])
    levantamiento = espacio([ambiente("A")], [punto_de_datos("P1", "1")])
    tipos = sorted(d.tipo for d in contrastar(plano, levantamiento).diferencias)
    assert tipos == ["faltante", "sobrante"]


def test_ambientes_y_fuentes_tambien_se_contrastan() -> None:
    plano = espacio([ambiente("A", x0="0.5")], fuentes=[rack("R1", "0", "0", "0")])
    levantamiento = espacio([ambiente("A")], fuentes=[rack("R1", "0", "0", "0")])
    [d] = contrastar(plano, levantamiento).diferencias
    assert (d.tabla, d.tipo, d.distancia) == ("esp_ambientes", "desplazado", Decimal("0.5"))


def test_el_resultado_no_depende_del_orden_de_las_filas() -> None:
    a = [punto_de_datos("P1", "1"), punto_de_datos("P2", "1.5"), punto_de_datos("P3", "9")]
    b = [punto_de_datos("Q1", "1.02"), punto_de_datos("Q2", "1.6")]
    uno = contrastar(
        espacio([ambiente("A", largo="10")], a), espacio([ambiente("A", largo="10")], b)
    )
    otro = contrastar(espacio([ambiente("A", largo="10")], a[::-1]),
                      espacio([ambiente("A", largo="10")], b[::-1]))
    assert uno == otro


def test_dos_espacios_iguales_no_difieren() -> None:
    assert contrastar(REFERENCIA, REFERENCIA).diferencias == ()


def test_la_regla_da_advertencias_con_la_fila_citada() -> None:
    hallazgos = ReglaContraste(un_punto("1.5"), REFERENCIA, "el levantamiento").evaluar(PRESUPUESTO)
    [h] = hallazgos
    assert (h.regla, h.severidad) == (CODIGO_R16, Severidad.ADVERTENCIA)
    assert h.origen_ids == ("esp_puntos:P1",) and "desplazado 0.5 m" in h.descripcion
    assert "el levantamiento" in h.descripcion
