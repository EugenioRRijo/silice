from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine

from aplicacion.simulador import simular_desde_catalogo
from core import models
from core.catalog import abrir_sesion, crear_esquema
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


def _catalogo_con_homonimos_de_unidad_nula():
    """Lista vigente ficticia: un material con unidad y un equipo y una mano de obra homonimos
    sin unidad (la columna admite nulo, lo habitual en equipos y mano de obra)."""
    motor = create_engine("sqlite://")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        lista = models.ListaPrecios(
            nombre="L", moneda="USD", fecha_vigencia=date(2026, 1, 1), origen="prueba"
        )
        sesion.add(lista)
        sesion.flush()
        for codigo, tipo, unidad in [
            ("MAT-001", "material", "viaje"),
            ("EQU-001", "equipo", None),
            ("MO-001", "mano_obra", None),
        ]:
            insumo = models.Insumo(
                codigo=codigo, tipo=tipo, descripcion="Transporte", unidad=unidad
            )
            sesion.add(insumo)
            sesion.flush()
            sesion.add(
                models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=Decimal("10"))
            )
        sesion.commit()
    return motor


def test_homonimos_sin_unidad_no_revientan_ni_se_pisan():
    """Hallazgo 1: con unidad nula el orden fallaba (500) y el equipo quedaba pisado por la mano
    de obra homonima. Salen los tres insumos, la unidad nula como texto vacio."""
    with abrir_sesion(_catalogo_con_homonimos_de_unidad_nula()) as sesion:
        filas = simular_desde_catalogo(sesion, "0", 1, None)
    assert sorted(filas) == [
        ("equipo", "Transporte", "", Decimal("10.00")),
        ("mano_obra", "Transporte", "", Decimal("10.00")),
        ("material", "Transporte", "viaje", Decimal("10.00")),
    ]


def test_la_clave_con_tipo_tolera_la_unidad_nula():
    """`simular` acepta la clave con tipo y una unidad nula sin romper el orden."""
    precios = {
        ("Transporte", "viaje", "material"): ("material", Decimal("10")),
        ("Transporte", None, "equipo"): ("equipo", Decimal("20")),
    }
    filas = simular(precios, Decimal("0"), semilla=1, solo=None)
    assert filas == [
        ("equipo", "Transporte", "", Decimal("20.00")),
        ("material", "Transporte", "viaje", Decimal("10.00")),
    ]
