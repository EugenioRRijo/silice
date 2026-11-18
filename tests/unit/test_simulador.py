from decimal import Decimal

from scripts.simular_lista import simular

PRECIOS = {
    ("Cemento Portland", "saco"): ("material", Decimal("15")),
    ("Arena lavada", "m3"): ("material", Decimal("30")),
}

PRECIOS_HOMONIMOS = {
    ("Arena lavada", "m3"): ("material", Decimal("30")),
    ("Arena lavada", "saco"): ("material", Decimal("4.50")),
    ("Cemento Portland", "saco"): ("material", Decimal("15")),
}


def test_es_determinista_con_la_misma_semilla():
    a = simular(PRECIOS, Decimal("10"), semilla=42, solo=None)
    assert a == simular(PRECIOS, Decimal("10"), semilla=42, solo=None)
    assert a != simular(PRECIOS, Decimal("10"), semilla=43, solo=None)


def test_respeta_el_filtro_y_el_formato():
    filas = simular(PRECIOS, Decimal("10"), semilla=1, solo={"Cemento Portland"})
    nuevos = {(insumo, unidad): precio for _tipo, insumo, unidad, precio in filas}
    # INV-025: con la semilla fija la variacion es exacta; la lista vacia ya no se acepta.
    assert [
        clave for clave, precio in nuevos.items() if precio != PRECIOS[clave][1]
    ] == [("Cemento Portland", "saco")]
    # Arena no se pidio: no sale en la lista simulada (conserva su precio vigente). Esta asercion
    # cae con el filtro retirado sea cual sea el sorteo.
    assert [insumo for insumo, _unidad in nuevos] == ["Cemento Portland"]
    for _tipo, _insumo, _unidad, precio in filas:
        assert isinstance(precio, Decimal) and precio >= 0
        assert precio == precio.quantize(Decimal("0.01"))


def test_sin_homonimos_conserva_la_serie_actual():
    """Oraculo de no-regresion: mismos valores calculados con la version previa."""
    precios = {
        ("Cemento Portland", "saco"): ("material", Decimal("15")),
        ("Arena lavada", "m3"): ("material", Decimal("30")),
        ("Peon", "jornal"): ("mano_obra", Decimal("12.50")),
    }
    filas = simular(precios, Decimal("10"), semilla=42, solo=None)
    assert filas == [
        ("material", "Arena lavada", "m3", Decimal("30.93")),
        ("material", "Cemento Portland", "saco", Decimal("13.84")),
        ("mano_obra", "Peon", "jornal", Decimal("11.31")),
    ]


def test_homonimos_con_distinta_unidad_salen_ambos():
    filas = simular(PRECIOS_HOMONIMOS, Decimal("10"), semilla=42, solo=None)
    assert filas == [
        ("material", "Arena lavada", "m3", Decimal("30.93")),
        ("material", "Arena lavada", "saco", Decimal("4.15")),
        ("material", "Cemento Portland", "saco", Decimal("13.58")),
    ]


def test_filtro_solo_incluye_todos_los_homonimos():
    filas = simular(PRECIOS_HOMONIMOS, Decimal("10"), semilla=42, solo={"Arena lavada"})
    assert filas == [
        ("material", "Arena lavada", "m3", Decimal("30.93")),
        ("material", "Arena lavada", "saco", Decimal("4.15")),
    ]
