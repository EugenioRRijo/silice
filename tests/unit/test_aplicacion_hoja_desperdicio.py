"""Editar la neta y el porcentaje del desperdicio en la Hoja (F5 vial, punto 1; 2026-11-13).

Decisión de `docs/bitacora/2026-11-13-desperdicio-en-la-hoja.md` (opción a): la edición del APU
de la versión lleva la neta y el porcentaje de cada material; el servidor calcula la cantidad
(`neta × (1 + porcentaje / 100)`, exacta) y la traza viaja en el borrador, en memoria. Se escribe
en la base del caso al guardar la versión, unida a las trazas vigentes de la partida para que el
catálogo y las otras versiones no pierdan la suya.

Datos FICTICIOS. Oráculos a mano: 2 × 1,05 = 2,10; 0,50 × 1,04 = 0,52; 0,60 × 1,05 = 0,63.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from aplicacion.desperdicio import TrazaDesperdicio
from aplicacion.errores import HojaInvalida
from aplicacion.hoja import Borrador
from aplicacion.hoja_desperdicio import (
    MENSAJE_DESPERDICIOS,
    con_desperdicio_en_materiales,
    por_guardar,
    unir,
)
from core.contracts.apu import ComposicionAPU, LineaEquipo, LineaMaterial

D = Decimal

ARENA = LineaMaterial("Arena ficticia", "m3", D("1.2"), D("10"))
LIGANTE = LineaMaterial("Ligante ficticio", "l", D("2"), D("3"))
APU = ComposicionAPU(
    "VIA-01",
    "Riego ficticio",
    "m2",
    D("100"),
    materiales=(ARENA, LIGANTE),
    equipos=(LineaEquipo("Camión ficticio", D("1"), D("50"), D("0.001")),),
)
DE_COMPONER = TrazaDesperdicio("Ligante ficticio", "l", D("0.50"), D("4"), D("0.5200"))
DE_LA_HOJA = TrazaDesperdicio("Ligante ficticio", "l", D("0.60"), D("5"), D("0.6300"))
FECHA = date(2026, 11, 13)


def test_el_porcentaje_convierte_la_neta_en_la_cantidad_y_deja_la_traza():
    nueva, trazas = con_desperdicio_en_materiales(APU, ["", "5"])
    assert nueva.materiales[0] == ARENA  # sin porcentaje, la línea queda como está
    assert nueva.materiales[1].cantidad == D("2.10")  # 2 × 1,05, a mano
    assert nueva.materiales[1].precio == LIGANTE.precio
    assert nueva.equipos == APU.equipos and nueva.rendimiento == APU.rendimiento
    assert trazas == (TrazaDesperdicio("Ligante ficticio", "l", D("2"), D("5"), D("2.10")),)


@pytest.mark.parametrize("vacio", ["", "  ", "0", "0,0", "﻿", " "])
def test_un_porcentaje_vacio_o_cero_no_es_desperdicio(vacio: str):
    nueva, trazas = con_desperdicio_en_materiales(APU, [vacio, vacio])
    assert nueva == APU and trazas == ()


def test_la_coma_decimal_del_porcentaje():
    nueva, trazas = con_desperdicio_en_materiales(APU, ["", "2,5"])
    assert nueva.materiales[1].cantidad == D("2.050")  # 2 × 1,025
    assert trazas[0].desperdicio_pct == D("2.5")


@pytest.mark.parametrize(
    ("texto", "final"),
    [
        ("cuatro", "no se entiende como número."),
        ("4.5", "no se entiende como número."),
        ("100", "debe estar entre 0 y 100 (es un porcentaje: 4 es 4 %)."),
        ("-1", "debe estar entre 0 y 100 (es un porcentaje: 4 es 4 %)."),
    ],
)
def test_un_porcentaje_mal_escrito_dice_la_fila_como_las_cantidades(texto: str, final: str):
    """«materiales, fila N: …» es el prefijo con que la Hoja ubica el error en su campo."""
    with pytest.raises(HojaInvalida) as error:
        con_desperdicio_en_materiales(APU, ["", texto])
    mensaje = str(error.value)
    assert mensaje.startswith(f"materiales, fila 2: el desperdicio «{texto}» ")
    assert final in mensaje


def test_un_porcentaje_por_cada_material_ni_mas_ni_menos():
    for porcentajes in (["4"], ["", "4", ""]):
        with pytest.raises(HojaInvalida) as error:
            con_desperdicio_en_materiales(APU, porcentajes)
        assert str(error.value) == MENSAJE_DESPERDICIOS


def test_unir_pone_primero_las_del_borrador_y_no_repite_la_misma_linea():
    assert unir([DE_LA_HOJA], [DE_COMPONER]) == [DE_LA_HOJA, DE_COMPONER]
    assert unir([DE_COMPONER], [DE_COMPONER]) == [DE_COMPONER]
    # otro desglose de la misma cantidad (0,40 + 30 % = 0,52): manda el más nuevo, el del borrador
    otra = TrazaDesperdicio("Ligante ficticio", "l", D("0.40"), D("30"), D("0.520"))
    assert unir([otra], [DE_COMPONER]) == [otra]
    assert unir([], [DE_COMPONER]) == [DE_COMPONER]


def _borrador(cantidad: str) -> Borrador:
    linea = LineaMaterial("Ligante ficticio", "l", D(cantidad), D("2"))
    apu = ComposicionAPU("VIA-01", "Riego", "m2", D("1"), (linea,))
    return Borrador(fecha=FECHA, composiciones={"VIA-01": apu})


def test_al_guardar_se_escribe_la_traza_del_borrador_unida_a_las_vigentes():
    vigentes = {"VIA-01": [DE_COMPONER]}
    assert por_guardar(_borrador("0.63"), {"VIA-01": (DE_LA_HOJA,)}, vigentes.__getitem__) == {
        "VIA-01": [DE_LA_HOJA, DE_COMPONER]
    }


def test_no_se_guarda_la_traza_de_una_linea_que_cambio_despues_por_otro_camino():
    """La traza del borrador vale solo si la línea guardada sigue siendo la que resultó: si luego
    se escribió otra cantidad (o se cambió el insumo), no hay nada nuevo que guardar."""
    vigentes = {"VIA-01": [DE_COMPONER]}
    assert por_guardar(_borrador("0.70"), {"VIA-01": (DE_LA_HOJA,)}, vigentes.__getitem__) == {}


def test_sin_trazas_nuevas_o_iguales_a_las_vigentes_no_se_escribe_nada():
    vigentes = {"VIA-01": [DE_COMPONER]}
    assert por_guardar(_borrador("0.52"), {}, vigentes.__getitem__) == {}
    assert por_guardar(_borrador("0.52"), {"VIA-01": (DE_COMPONER,)}, vigentes.__getitem__) == {}
    # una partida que el borrador ya no tiene (se quitó): nada
    assert por_guardar(Borrador(fecha=FECHA), {"VIA-01": (DE_LA_HOJA,)}, vigentes.__getitem__) == {}


def test_la_traza_de_la_hoja_se_arma_recortada_como_la_de_componer():
    """Argon, ronda 2 del árbitro (2026-11-13): la Hoja armaba la traza con la descripción y la
    unidad del APU tal cual («Ligante ficticio », «l »); unir y por_guardar las comparaban crudas
    con las de Componer, que vienen recortadas, y dejaban dos trazas de la misma línea."""
    con_espacios = LineaMaterial("Ligante ficticio ", "l ", D("2"), D("3"))
    apu = replace(APU, materiales=(ARENA, con_espacios))
    _, trazas = con_desperdicio_en_materiales(apu, ["", "5"])
    assert trazas == (TrazaDesperdicio("Ligante ficticio", "l", D("2"), D("5"), D("2.10")),)
    vigente = TrazaDesperdicio("Ligante ficticio", "l", D("1"), D("110"), D("2.10"))
    assert unir(trazas, [vigente]) == list(trazas)  # misma línea y cantidad: manda la nueva
