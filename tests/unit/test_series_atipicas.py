"""RF-100 contra `tests/fixtures/memorias/atipicos_s3.md`: series sembradas, conjunto exacto de
hallazgos, abstención por debajo de 8 variaciones, conversión a USD con la tasa de cada precio y
ningún hallazgo ERROR. El detector y sus umbrales son los de I6.1 y no se tocan."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ml.anomaly.series import PuntoDePrecio, a_usd, analizar, variaciones

D = Decimal


def serie(precios, moneda="USD"):
    """Un precio por mes, desde enero de 2026."""
    return [
        PuntoDePrecio(date(2026, k + 1, 1), D(p), moneda, None, f"L{k + 1:02d}")
        for k, p in enumerate(precios)
    ]


def test_una_serie_de_10_con_un_atipico_marca_solo_la_ultima_variacion() -> None:
    r = analizar(serie([1, 2, 4, 8, 16, 32, 64, 128, 256, 257]))
    assert [a.id for a in r.atipicas] == ["2026-09-01>2026-10-01#8"]
    assert r.atipicas[0].valor == D("0.00390625") and not r.se_abstuvo
    assert len(r.variaciones) == 9
    assert [v for k, v in r.variaciones.items() if not k.endswith("#8")] == [D(1)] * 8


def test_una_serie_de_10_sin_atipico_da_el_conjunto_vacio() -> None:
    r = analizar(serie([1, 2, 4, 8, 16, 32, 64, 128, 256, 512]))
    assert r.atipicas == () and not r.se_abstuvo and set(r.variaciones.values()) == {D(1)}


def test_con_8_precios_hay_7_variaciones_y_el_detector_se_abstiene() -> None:
    r = analizar(serie([1, 2, 4, 8, 16, 32, 64, 128]))
    assert len(r.variaciones) == 7 and r.atipicas == () and r.se_abstuvo
    con_raro = analizar(serie([1, 2, 4, 8, 16, 32, 64, 65]))
    assert con_raro.atipicas == () and con_raro.se_abstuvo  # la serie corta no es sospechosa


def test_el_noveno_precio_da_8_variaciones_y_ya_juzga() -> None:
    r = analizar(serie([1, 2, 4, 8, 16, 32, 64, 128, 129]))
    assert len(r.variaciones) == 8 and not r.se_abstuvo
    assert [a.id.split("#")[0] for a in r.atipicas] == ["2026-08-01>2026-09-01"]


def test_dos_precios_en_bs_con_tasas_distintas_dan_la_variacion_en_usd() -> None:
    puntos = [
        PuntoDePrecio(date(2026, 8, 3), D(720), "Bs", D(36), "Lista agosto"),
        PuntoDePrecio(date(2026, 9, 7), D(1100), "Bs", D(44), "Lista septiembre"),
    ]
    usd = a_usd(puntos)
    assert [(f.isoformat(), p) for f, p, _ in usd.puntos] == [
        ("2026-08-03", D(20)),
        ("2026-09-07", D(25)),
    ]
    [valor] = variaciones(usd).values()
    assert valor == D("0.25") != (D(1100) - D(720)) / D(720)


def test_un_precio_en_bs_sin_tasa_se_omite_y_se_nombra_sin_inventarla() -> None:
    puntos = [
        PuntoDePrecio(date(2026, 8, 3), D(720), "Bs", None, "Lista sin tasa"),
        PuntoDePrecio(date(2026, 9, 7), D(25), "USD", None, "Lista en USD"),
        PuntoDePrecio(date(2026, 10, 7), D(500), "Bs", D(0), "Tasa cero"),
    ]
    usd = a_usd(puntos)
    assert usd.sin_tasa == ("Lista sin tasa", "Tasa cero")
    assert [p for _, p, _ in usd.puntos] == [D(25)] and variaciones(usd) == {}


def test_los_puntos_se_ordenan_por_fecha_sin_importar_como_llegan() -> None:
    desordenada = list(reversed(serie([1, 2, 4])))
    assert [p for _, p, _ in a_usd(desordenada).puntos] == [D(1), D(2), D(4)]


def test_a_igual_fecha_se_ordena_por_el_nombre_de_la_lista() -> None:
    """Memoria §5: fecha y, a igual fecha, nombre de la lista; así la variación no depende del
    orden en que la base devuelva las filas."""
    mismo_dia = date(2026, 5, 4)
    puntos = [
        PuntoDePrecio(mismo_dia, D(30), "USD", None, "Lista C"),
        PuntoDePrecio(mismo_dia, D(10), "USD", None, "Lista A"),
        PuntoDePrecio(mismo_dia, D(20), "USD", None, "Lista B"),
    ]
    for orden in (puntos, list(reversed(puntos))):
        usd = a_usd(orden)
        assert [(p, o) for _, p, o in usd.puntos] == [
            (D(10), "Lista A"),
            (D(20), "Lista B"),
            (D(30), "Lista C"),
        ]
        assert list(variaciones(usd).values()) == [D(1), D("0.5")]


def test_un_precio_anterior_igual_a_cero_no_genera_variacion() -> None:
    assert variaciones(a_usd(serie([0, 5, 10]))) == {"2026-02-01>2026-03-01#1": D(1)}


@pytest.mark.parametrize(
    "precios",
    [[1, 2, 4, 8, 16, 32, 64, 128, 256, 257], [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]],
)
def test_la_misma_serie_da_siempre_el_mismo_resultado(precios) -> None:
    assert analizar(serie(precios)) == analizar(serie(precios))
