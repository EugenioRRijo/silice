"""F5 vial, tarea 3: el desperdicio de un material, dentro de la cantidad y con su traza.

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §4 (punto 1, opción B)
y la decisión provisional 1 del 2026-11-06. El núcleo no cambia: la `LineaMaterial` lleva la
cantidad ya multiplicada y la cantidad neta y el porcentaje quedan en una tabla aditiva del caso.

Datos FICTICIOS. Oráculos a mano (el ejemplo del diseño): un ligante de 0,50 l/m² con 4 % de
desperdicio consume 0,50 × 1,04 = 0,52 l/m²; 0,333 con 4 % es 0,34632 (exacto, sin redondear).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from aplicacion.composicion import ComposicionInvalida
from aplicacion.desperdicio import (
    TrazaDesperdicio,
    aplicar_desperdicio,
    cantidad_con_desperdicio,
    con_desperdicio,
    guardar_trazas,
    leyenda,
    neta_y_porcentaje,
    trazas_de_las_filas,
    trazas_vigentes,
)
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base

D = Decimal
LIGANTE = {
    "descripcion": "Ligante ficticio",
    "unidad": "l",
    "cantidad": "0,50",
    "precio": "2,00",
    "desperdicio": "4",
}
ARENA = {"descripcion": "Arena ficticia", "unidad": "m3", "cantidad": "1,2", "precio": "10"}
TRAZA = TrazaDesperdicio("Ligante ficticio", "l", D("0.50"), D("4"), D("0.5200"))


def test_la_cantidad_con_desperdicio_es_exacta():
    assert cantidad_con_desperdicio(D("0.50"), D("4")) == D("0.52")
    assert cantidad_con_desperdicio(D("0.333"), D("4")) == D("0.34632")


def test_aplicar_multiplica_la_cantidad_y_devuelve_la_traza():
    filas, trazas = aplicar_desperdicio([LIGANTE, ARENA])
    assert filas == [
        {"descripcion": "Ligante ficticio", "unidad": "l", "cantidad": "0,5200", "precio": "2,00"},
        ARENA,
    ]
    assert trazas == [TRAZA]
    assert trazas[0].cantidad == D("0.52")


@pytest.mark.parametrize("vacio", ["", "  ", "0", "0,0"])
def test_sin_desperdicio_la_fila_no_cambia_y_no_hay_traza(vacio: str):
    filas, trazas = aplicar_desperdicio([{**LIGANTE, "desperdicio": vacio}])
    assert filas == [{k: v for k, v in LIGANTE.items() if k != "desperdicio"}]
    assert trazas == []


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("-1", "entre 0 y 100"),
        ("100", "entre 0 y 100"),
        ("cuatro", "no se entiende como número"),
        ("4.5", "no se entiende como número"),
    ],
)
def test_un_desperdicio_mal_escrito_dice_la_fila(texto: str, mensaje: str):
    lugar = r"En Materiales, fila 2 \(«Ligante ficticio»\), el desperdicio"
    with pytest.raises(ComposicionInvalida, match=rf"{lugar}.*{mensaje}"):
        aplicar_desperdicio([ARENA, {**LIGANTE, "desperdicio": texto}])


def test_la_coma_decimal_del_porcentaje():
    _, trazas = aplicar_desperdicio([{**LIGANTE, "desperdicio": "2,5"}])
    assert trazas[0].cantidad == D("0.51250")


def test_la_leyenda_de_la_traza():
    assert leyenda(TRAZA) == "0,52 (0,50 + 4 %)"
    otra = TrazaDesperdicio("Pintura", "l", D("1234.5"), D("2.5"), D("1265.3625"))
    assert leyenda(otra) == "1.265,3625 (1.234,5 + 2,5 %)"


def test_la_precarga_devuelve_la_neta_y_el_porcentaje_si_la_cantidad_sigue_igual():
    guardada = {
        "descripcion": "Ligante ficticio",
        "unidad": "l",
        "cantidad": "0,5200",
        "precio": "2,00",
    }
    assert con_desperdicio([guardada, ARENA], [TRAZA]) == [
        {**guardada, "cantidad": "0,50", "desperdicio": "4"},
        ARENA,
    ]
    # la cantidad cambió por otro camino: la traza ya no es de esa línea y no se muestra
    editada = {**guardada, "cantidad": "0,60"}
    assert con_desperdicio([editada], [TRAZA]) == [editada]


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator[Session]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            yield s
    finally:
        motor.dispose()


def test_las_trazas_se_guardan_y_manda_el_ultimo_guardado(sesion: Session):
    assert trazas_vigentes(sesion, "VIA-01") == []
    guardar_trazas(sesion, "VIA-01", [TRAZA], ahora=datetime(2026, 11, 6, 9))
    sesion.commit()
    assert trazas_vigentes(sesion, "VIA-01") == [TRAZA]
    assert trazas_vigentes(sesion, "OTRA") == []
    guardar_trazas(sesion, "VIA-01", [], ahora=datetime(2026, 11, 6, 10))
    sesion.commit()
    assert trazas_vigentes(sesion, "VIA-01") == []


def _por_fila(filas, trazas) -> list[tuple[int, str]]:
    """La fila (desde 1) y «neta + porcentaje» de cada material con traza, como en la Hoja."""
    return [(i, neta_y_porcentaje(traza)) for i, traza in trazas_de_las_filas(filas, trazas)]


def test_la_neta_y_el_porcentaje_de_la_traza():
    """Lo que la Hoja muestra junto a la cantidad: la neta y el porcentaje, sin la cantidad que
    ya está en su celda (F5 vial, lo que faltaba del punto 1)."""
    assert neta_y_porcentaje(TRAZA) == "0,50 + 4 %"
    otra = TrazaDesperdicio("Pintura", "l", D("1234.5"), D("2.5"), D("1265.3625"))
    assert neta_y_porcentaje(otra) == "1.234,5 + 2,5 %"


def test_desperdicios_por_fila_solo_en_la_linea_de_la_traza_y_cada_traza_una_vez():
    guardada = {"descripcion": "Ligante ficticio", "unidad": "l", "cantidad": "0,52"}
    # filas numeradas desde 1, como en la tabla de la Hoja
    assert _por_fila([ARENA, guardada], [TRAZA]) == [(2, "0,50 + 4 %")]
    # dos líneas iguales y una sola traza: solo la primera
    assert _por_fila([guardada, guardada], [TRAZA]) == [(1, "0,50 + 4 %")]
    # la cantidad cambió por otro camino, o la unidad, o la descripción: nada que mostrar
    assert _por_fila([{**guardada, "cantidad": "0,60"}], [TRAZA]) == []
    assert _por_fila([{**guardada, "unidad": "kg"}], [TRAZA]) == []
    assert _por_fila([{**guardada, "descripcion": "Otro"}], [TRAZA]) == []
    assert _por_fila([guardada], []) == []


def test_una_descripcion_con_espacios_en_los_bordes_casa_con_su_traza():
    """Árbitro del 2026-11-13, M3: la Hoja arma la traza con la descripción del APU tal cual
    («Ligante ficticio », con un espacio al final) y la fila se lee recortada: debe casar igual."""
    traza = TrazaDesperdicio("Ligante ficticio ", "l ", D("0.50"), D("4"), D("0.5200"))
    fila = {"descripcion": "Ligante ficticio ", "unidad": "l ", "cantidad": "0,52"}
    assert _por_fila([fila], [traza]) == [(1, "0,50 + 4 %")]
    assert con_desperdicio([fila], [traza])[0]["desperdicio"] == "4"
