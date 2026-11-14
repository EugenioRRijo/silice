"""El ayudante de plural de la capa de aplicación: cantidad con miles y la palabra que toca."""

from aplicacion.plural import plural


def test_uno_va_en_singular_y_el_resto_en_plural() -> None:
    assert plural(1, "cambio", "cambios") == "1 cambio"
    assert plural(0, "cambio", "cambios") == "0 cambios"
    assert plural(2, "cambio", "cambios") == "2 cambios"


def test_la_cantidad_lleva_punto_de_miles() -> None:
    assert plural(1200, "precio", "precios") == "1.200 precios"
