"""R15: coherencia geométrica del plano, con las fronteras exactas de S3 §11.3 (RF-89)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio.planos.dxf import importar_dxf
from adapters.espacio.planos.geometria_plano import CODIGO_R15, CoherenciaGeometrica, reglas_plano
from adapters.espacio.reglas import CoherenciaEspacial
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Severidad
from tests.fixtures.espacio_minimo import ambiente, espacio, punto_de_datos, rack
from tests.fixtures.espacio_of001 import espacio_of001

RUTA_OF001_DXF = Path(__file__).resolve().parents[1] / "fixtures" / "planos" / "of001.dxf"
PRESUPUESTO = Presupuesto(codigo="X", fecha=date(2026, 11, 1), moneda="USD", partidas=())


def r15(e):
    return CoherenciaGeometrica(e).evaluar(PRESUPUESTO)


# --- superposición (ERROR; 0,0100 m2 pasa, 0,0101 m2 falla) ---------------------------------


def test_superposicion_de_0_0100_m2_pasa() -> None:
    a, b = ambiente("A", largo="1", ancho="1"), ambiente("B", x0="0.99", largo="1", ancho="1")
    assert r15(espacio([a, b])) == []


def test_superposicion_de_0_0101_m2_falla_con_error_y_cita_los_dos_ambientes() -> None:
    a, b = ambiente("A", largo="1", ancho="1"), ambiente("B", x0="0.9899", largo="1", ancho="1")
    [h] = r15(espacio([a, b]))
    assert (h.regla, h.severidad) == (CODIGO_R15, Severidad.ERROR)
    assert h.origen_ids == ("esp_ambientes:A", "esp_ambientes:B")
    assert (h.valor_observado, h.valor_esperado) == (Decimal("0.0101"), Decimal("0.01"))


def test_ambientes_que_solo_se_tocan_o_estan_separados_no_se_superponen() -> None:
    a = ambiente("A", largo="1", ancho="1")
    juntos, lejos = ambiente("B", x0="1", largo="1", ancho="1"), ambiente("C", x0="5")
    assert r15(espacio([a, juntos, lejos])) == []


def test_la_superposicion_se_mide_en_las_dos_direcciones() -> None:
    a = ambiente("A", largo="2", ancho="2")
    b = ambiente("B", x0="1.9", y0="1.9", largo="2", ancho="2")  # 0,1 x 0,1 = 0,01: pasa
    c = ambiente("C", x0="1.89", y0="1.89", largo="2", ancho="2")  # 0,11 x 0,11 = 0,0121
    assert r15(espacio([a, b])) == []
    [h] = r15(espacio([a, c]))
    assert h.valor_observado == Decimal("0.0121")


# --- puntos duplicados (ERROR; 0,0010 m pasa, 0,0009 m falla) ----------------------------------


def test_dos_puntos_a_0_0010_m_pasan() -> None:
    puntos = [punto_de_datos("P1", "1"), punto_de_datos("P2", "1.001")]
    assert r15(espacio([ambiente("A")], puntos)) == []


def test_dos_puntos_a_0_0009_m_son_duplicados() -> None:
    e = espacio([ambiente("A")], [punto_de_datos("P1", "1"), punto_de_datos("P2", "1.0009")])
    [h] = r15(e)
    assert h.severidad is Severidad.ERROR and h.origen_ids == ("esp_puntos:P1", "esp_puntos:P2")
    assert h.valor_observado == Decimal("0.0009")


def test_puntos_de_otro_tipo_en_el_mismo_sitio_no_son_duplicados() -> None:
    from tests.fixtures.espacio_minimo import toma

    e = espacio([ambiente("A")], [punto_de_datos("P1", "1"), toma("T1", "1")])
    assert r15(e) == []


def test_el_duplicado_se_mide_en_tres_dimensiones() -> None:
    e = espacio([ambiente("A")], [punto_de_datos("P1", "1", z="0.3"),
                                  punto_de_datos("P2", "1", z="0.3009")])
    assert len(r15(e)) == 1


# --- escala imposible (ADVERTENCIA) ------------------------------------------------------------


@pytest.mark.parametrize("lado,falla", [("0.300", False), ("0.299", True), ("200.000", False),
                                        ("200.001", True)])
def test_el_lado_de_un_ambiente_tiene_fronteras_inclusivas(lado: str, falla: bool) -> None:
    hallazgos = r15(espacio([ambiente("A", largo=lado, ancho="1")]))
    assert bool(hallazgos) is falla
    if falla:
        assert hallazgos[0].severidad is Severidad.ADVERTENCIA
        assert "largo" in hallazgos[0].descripcion


@pytest.mark.parametrize("alto,falla", [("2.000", False), ("1.999", True), ("12.000", False),
                                        ("12.001", True)])
def test_la_altura_de_un_ambiente_tiene_fronteras_inclusivas(alto: str, falla: bool) -> None:
    hallazgos = r15(espacio([ambiente("A", alto=alto)]))
    assert bool(hallazgos) is falla
    if falla:
        assert hallazgos[0].severidad is Severidad.ADVERTENCIA
        assert "altura" in hallazgos[0].descripcion


# --- punto lejos de su fuente (ADVERTENCIA; 100,000 m pasa, 100,001 m falla) -------------------


@pytest.mark.parametrize("x,falla", [("100", False), ("100.001", True)])
def test_la_distancia_a_la_fuente(x: str, falla: bool) -> None:
    e = espacio([ambiente("A", largo="200")], [punto_de_datos("P1", x, y="0", z="0", fuente="R1")],
                [rack("R1", "0", "0", "0")])
    hallazgos = r15(e)
    assert bool(hallazgos) is falla
    if falla:
        assert hallazgos[0].severidad is Severidad.ADVERTENCIA
        assert hallazgos[0].origen_ids == ("esp_puntos:P1", "esp_fuentes:R1")


def test_un_punto_sin_fuente_no_se_mide() -> None:
    assert r15(espacio([ambiente("A", largo="200")], [punto_de_datos("P1", "150")])) == []


# --- R15 no repite R9 y no inventa hallazgos en el caso limpio ---------------------------------


def test_un_punto_fuera_de_su_ambiente_es_de_r9_y_no_de_r15() -> None:
    e = espacio([ambiente("A", largo="2", ancho="2")], [punto_de_datos("P1", "9", y="9")])
    assert r15(e) == [] and CoherenciaEspacial(e).evaluar(PRESUPUESTO) != []


def test_of001_limpio_no_da_hallazgos_de_r15_ni_en_la_hoja_ni_en_el_dxf() -> None:
    assert r15(espacio_of001()) == []
    importado = importar_dxf(RUTA_OF001_DXF)
    assert r15(importado.espacio()) == []


def test_reglas_plano_devuelve_solo_r15() -> None:
    reglas = reglas_plano(espacio([ambiente("A")]))
    assert [r.codigo for r in reglas] == [CODIGO_R15]


def test_el_orden_de_los_hallazgos_es_estable() -> None:
    e = espacio(
        [ambiente("B", largo="0.2"), ambiente("A", largo="0.2")],
        [punto_de_datos("P2", "1.0001"), punto_de_datos("P1", "1")],
    )
    assert [h.descripcion for h in r15(e)] == [h.descripcion for h in r15(e)]
