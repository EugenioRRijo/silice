"""Pruebas del adaptador industrial (Sesión I5): registro de activos de planta con frecuencia de
intervención de mantenimiento. La muestra y sus supuestos están en
`data/samples/industrial/README.md`.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from adapters.industrial import AdaptadorIndustrial
from adapters.industrial.adaptador import REGLA_INTERVENCIONES
from adapters.industrial.evaluador import evaluar_regla
from core.contracts import Dominio, OrigenTipo

RUTA_MUESTRA = (
    Path(__file__).resolve().parents[2] / "data" / "samples" / "industrial" / "activos_planta.csv"
)


def _extraer():
    return AdaptadorIndustrial().extraer(RUTA_MUESTRA)


def test_extrae_los_activos_de_la_muestra():
    adaptador = AdaptadorIndustrial()
    assert adaptador.dominio is Dominio.INDUSTRIAL

    items = _extraer()

    assert len(items) == 10
    assert all(item.origen_id.startswith("IN-") for item in items)
    assert all(item.codigo_partida.startswith("MNT-") for item in items)
    assert all(item.unidad == "intervencion" for item in items)
    assert all(item.dominio is Dominio.INDUSTRIAL for item in items)


def test_la_cantidad_es_frecuencia_por_horizonte():
    items = _extraer()

    # invariante general: la cantidad de cada item es el producto de sus propios parametros.
    for item in items:
        frecuencia = item.parametros["frecuencia_anual"]
        horizonte = item.parametros["horizonte_anios"]
        assert item.cantidad == frecuencia * horizonte

    # valores concretos de la muestra (data/samples/industrial/README.md): sirven de guardia
    # contra una implementacion que sume en vez de multiplicar.
    por_id = {item.origen_id: item for item in items}
    assert por_id["IN-001"].cantidad == Decimal("20")  # 4 * 5
    assert por_id["IN-004"].cantidad == Decimal("5")  # 1 * 5
    assert por_id["IN-005"].cantidad == Decimal("60")  # 12 * 5
    assert por_id["IN-010"].cantidad == Decimal("3")  # 1 * 3


def test_items_trazables_por_regla():
    items = _extraer()

    assert items  # la muestra no esta vacia
    for item in items:
        assert item.origen_tipo is OrigenTipo.REGLA
        assert item.regla == REGLA_INTERVENCIONES
        assert evaluar_regla(item.regla, item.parametros) == item.cantidad
