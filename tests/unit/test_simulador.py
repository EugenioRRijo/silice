from decimal import Decimal

from scripts.simular_lista import simular

PRECIOS = {
    "Cemento Portland": ("material", "saco", Decimal("15")),
    "Arena lavada": ("material", "m3", Decimal("30")),
}


def test_es_determinista_con_la_misma_semilla():
    a = simular(PRECIOS, Decimal("10"), semilla=42, solo=None)
    assert a == simular(PRECIOS, Decimal("10"), semilla=42, solo=None)
    assert a != simular(PRECIOS, Decimal("10"), semilla=43, solo=None)


def test_respeta_el_filtro_y_el_formato():
    filas = simular(PRECIOS, Decimal("10"), semilla=1, solo={"Cemento Portland"})
    nuevos = {insumo: precio for _tipo, insumo, _unidad, precio in filas}
    # INV-025: con la semilla fija la variacion es exacta; la lista vacia ya no se acepta.
    assert [i for i, precio in nuevos.items() if precio != PRECIOS[i][2]] == ["Cemento Portland"]
    # Arena no se pidio: no sale en la lista simulada, asi que conserva su precio vigente.
    assert nuevos.get("Arena lavada", PRECIOS["Arena lavada"][2]) == Decimal("30.00")
    for _tipo, _insumo, _unidad, precio in filas:
        assert isinstance(precio, Decimal) and precio >= 0
        assert precio == precio.quantize(Decimal("0.01"))
