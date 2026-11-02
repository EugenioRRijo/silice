"""Costo por tonelada, puro (Tarea 4 del plan vial). Datos FICTICIOS; oraculos a mano.

- Reparto D-V-1 sin pesos: 1.000 / (150 + 50) t = 5 por tonelada para los dos agregados.
- Con pesos 0,75 y 0,25 sobre 100 t cada uno: 1.000 x 0,75 / 100 = 7,5 y 1.000 x 0,25 / 100 = 2,5.
- Mezcla `MZ-1` (receta A): 0,94 t de `AGR-12` a 5 + 0,05 t de `CA-30` a 600 + 8 l de `GO` a 0,5 +
  planta 12 = 4,70 + 30 + 4 + 12 = 50,70.
- Receta B (0,95 / 0,04 / 10 l): 4,75 + 24 + 5 = 33,75 sin planta. Con 60 t de A y 40 t de B y
  planta 12: (60 x 38,70 + 40 x 33,75) / 100 + 12 = (2.322 + 1.350) / 100 + 12 = 48,72.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from produccion.costo import (
    ErrorDeCalculo,
    costo_de_mezcla,
    costo_de_mezcla_del_periodo,
    costo_por_tonelada,
    presentar,
)
from produccion.receta import Componente, Receta

D = Decimal


def _receta(id_: int, agr: str, ca: str, go: str) -> Receta:
    return Receta(
        id=id_,
        producto="MZ-1",
        componentes=(
            Componente("AGR-12", D(agr), "t", "propio"),
            Componente("CA-30", D(ca), "t", "comprado"),
            Componente("GO", D(go), "l", "comprado"),
        ),
        fuente="dosificacion ficticia",
        vigente_desde=date(2026, 10, 1),
    )


RECETA_A = _receta(1, "0.94", "0.05", "8")
RECETA_B = _receta(2, "0.95", "0.04", "10")
PROPIO = {"AGR-12": D("5")}
COMPRADO = {"CA-30": D("600"), "GO": D("0.5")}


# --- Reparto de la cantera ------------------------------------------------------------------------


def test_reparto_por_tonelada() -> None:
    assert costo_por_tonelada(D("1000"), {"AGR-12": D("150"), "AGR-34": D("50")}) == {
        "AGR-12": D("5"),
        "AGR-34": D("5"),
    }


def test_reparto_por_pesos() -> None:
    r = costo_por_tonelada(
        D("1000"),
        {"A": D("100"), "B": D("100")},
        pesos={"A": D("0.75"), "B": D("0.25")},
    )
    assert r == {"A": D("7.5"), "B": D("2.5")}


def test_el_reparto_se_guarda_exacto_a_28_cifras() -> None:
    # 1.000 / 300 = 3,333... con 28 cifras significativas: un 3 y veintisiete 3 decimales
    assert costo_por_tonelada(D("1000"), {"AGR-12": D("300")}) == {"AGR-12": D("3." + "3" * 27)}


def test_sin_productos_o_con_toneladas_no_positivas_no_reparte() -> None:
    with pytest.raises(ErrorDeCalculo, match="ningún producto"):
        costo_por_tonelada(D("1000"), {})
    with pytest.raises(ErrorDeCalculo, match="AGR-34"):
        costo_por_tonelada(D("1000"), {"AGR-12": D("150"), "AGR-34": D("0")})


def test_total_negativo_no_reparte() -> None:
    with pytest.raises(ErrorDeCalculo, match="total"):
        costo_por_tonelada(D("-1"), {"AGR-12": D("150")})


def test_los_pesos_suman_uno_y_cubren_los_mismos_productos() -> None:
    toneladas = {"A": D("100"), "B": D("100")}
    with pytest.raises(ErrorDeCalculo, match="suman 0,9"):
        costo_por_tonelada(D("1000"), toneladas, pesos={"A": D("0.6"), "B": D("0.3")})
    with pytest.raises(ErrorDeCalculo, match="B"):
        costo_por_tonelada(D("1000"), toneladas, pesos={"A": D("1")})
    with pytest.raises(ErrorDeCalculo, match="C"):
        costo_por_tonelada(D("1000"), toneladas, pesos={"A": D("0.5"), "B": D("0.5"), "C": D("0")})
    with pytest.raises(ErrorDeCalculo, match="B"):  # un peso cero daria un costo cero
        costo_por_tonelada(D("1000"), toneladas, pesos={"A": D("1"), "B": D("0")})


# --- Mezcla ---------------------------------------------------------------------------------------


def test_costo_de_mezcla() -> None:
    # 4,70 + 30 + 4 + 12
    assert costo_de_mezcla(RECETA_A, PROPIO, COMPRADO, D("12")) == D("50.70")


def test_costo_de_mezcla_nombra_lo_que_falta() -> None:
    with pytest.raises(ErrorDeCalculo, match="AGR-12"):
        costo_de_mezcla(RECETA_A, {}, COMPRADO, D("12"))
    with pytest.raises(ErrorDeCalculo, match="CA-30"):
        costo_de_mezcla(RECETA_A, PROPIO, {"GO": D("0.5")}, D("12"))


def test_la_mezcla_del_periodo_pondera_por_las_toneladas_de_cada_receta() -> None:
    usos = [(RECETA_A, D("60")), (RECETA_B, D("40"))]
    assert costo_de_mezcla_del_periodo(usos, PROPIO, COMPRADO, D("12")) == D("48.72")


def test_con_una_sola_receta_la_mezcla_del_periodo_es_la_de_esa_receta() -> None:
    # 100,00009 t (43,4783 m3 x 2,3): (38,70 x 100,00009) / 100,00009 + 12 vuelve a 50,70 exacto
    usos = [(RECETA_A, D("100.00009"))]
    assert costo_de_mezcla_del_periodo(usos, PROPIO, COMPRADO, D("12")) == D("50.70")


def test_la_mezcla_del_periodo_sin_producciones_no_se_calcula() -> None:
    with pytest.raises(ErrorDeCalculo, match="producción"):
        costo_de_mezcla_del_periodo([], PROPIO, COMPRADO, D("12"))


# --- Presentar ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exacto", "presentado"),
    [
        ("0.125", "0.13"),  # mitad hacia arriba (al par seria 0,12)
        ("2.675", "2.68"),
        ("0.005", "0.01"),
        ("3." + "3" * 27, "3.33"),
        ("50.70", "50.70"),
        ("5", "5.00"),
    ],
)
def test_presentar_redondea_a_dos_decimales_mitad_hacia_arriba(exacto, presentado) -> None:
    assert str(presentar(D(exacto))) == presentado
