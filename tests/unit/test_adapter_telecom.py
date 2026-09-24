"""Adaptador del dominio telecom: topologia de red en CSV (Sesion I5).

Reproduce, a partir de la muestra `data/samples/telecom/topologia_arenaza.csv` (derivada de los dos
presupuestos ARENAZA, ver `data/samples/telecom/README.md`), 8 nodos (puntos WiFi, switches, rack,
UPS) y 5 enlaces de cable UTP. Cada nodo es una cantidad tabular directa; cada enlace deriva su
cantidad de la regla `longitud_m * (1 + reserva)`, evaluada por `adapters/telecom/evaluador.py`
(independiente del de `adapters/civil`: cada adaptador es autonomo, CLAUDE.md paragrafo 2).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from adapters.telecom.adaptador import AdaptadorTelecom
from adapters.telecom.evaluador import evaluar_regla
from core.contracts import Dominio, OrigenTipo

RAIZ = Path(__file__).resolve().parents[2]
RUTA_MUESTRA = RAIZ / "data" / "samples" / "telecom" / "topologia_arenaza.csv"

_ENCABEZADO_CSV = (
    "tipo,id,descripcion,codigo_partida,unidad,cantidad,origen,destino,longitud_m,reserva,"
    "especificaciones"
)


def _extraer():
    return AdaptadorTelecom().extraer(RUTA_MUESTRA)


def _csv_minimo(tmp_path: Path, filas_enlace: list[str]) -> Path:
    """Un CSV con dos nodos (`N-01`, `N-02`) y las filas de enlace que se le pasen, para pruebas de
    casos borde que no necesitan la muestra completa.
    """
    lineas = [
        _ENCABEZADO_CSV,
        "nodo,N-01,Nodo de prueba 1,TC-N-01,pieza,1,,,,,",
        "nodo,N-02,Nodo de prueba 2,TC-N-02,pieza,1,,,,,",
        *filas_enlace,
    ]
    ruta = tmp_path / "topologia_prueba.csv"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def test_extrae_nodos_y_enlaces_de_la_muestra():
    adaptador = AdaptadorTelecom()
    assert adaptador.dominio is Dominio.TELECOM

    items = adaptador.extraer(RUTA_MUESTRA)
    assert len(items) == 13

    nodos = [item for item in items if item.origen_tipo is OrigenTipo.CSV]
    enlaces = [item for item in items if item.origen_tipo is OrigenTipo.REGLA]
    assert len(nodos) == 8
    assert len(enlaces) == 5

    for item in items:
        assert item.dominio is Dominio.TELECOM
        assert item.codigo_partida.startswith("TC-")
        assert isinstance(item.cantidad, Decimal)

    rack = next(item for item in nodos if item.origen_id == "RACK-01")
    assert rack.unidad == "pieza"
    assert rack.cantidad == Decimal("1")
    assert rack.especificaciones["tipo_equipo"] == "rack"


def test_los_enlaces_son_trazables_por_regla():
    items = _extraer()
    enlaces = {item.origen_id: item for item in items if item.origen_tipo is OrigenTipo.REGLA}

    esperado = {
        "ENL-01": Decimal("5.50"),
        "ENL-02": Decimal("33.00"),
        "ENL-03": Decimal("23.00"),
        "ENL-04": Decimal("28.75"),
        "ENL-05": Decimal("15"),
    }
    assert set(enlaces) == set(esperado)

    for origen_id, cantidad_esperada in esperado.items():
        enlace = enlaces[origen_id]
        assert enlace.regla is not None
        assert enlace.cantidad == cantidad_esperada
        # la cantidad declarada se reproduce evaluando la regla contra sus propios parametros
        # (regla R1 de verificacion: trazabilidad geometrica)
        assert evaluar_regla(enlace.regla, enlace.parametros) == enlace.cantidad
        assert enlace.unidad == "m"
        assert enlace.especificaciones["origen"]
        assert enlace.especificaciones["destino"]


def test_origen_id_es_la_clave_de_fila():
    items = _extraer()
    ids_esperados = {
        "RACK-01",
        "SW-CORE",
        "SW-DIST",
        "AP-01",
        "AP-02",
        "AP-03",
        "AP-04",
        "UPS-01",
        "ENL-01",
        "ENL-02",
        "ENL-03",
        "ENL-04",
        "ENL-05",
    }
    ids_obtenidos = {item.origen_id for item in items}
    assert ids_obtenidos == ids_esperados
    # cada origen_id es unico: es la clave de fila del CSV, no un valor repetido entre filas
    assert len(ids_obtenidos) == len(items)


def test_reserva_vacia_es_cero(tmp_path):
    ruta = _csv_minimo(
        tmp_path,
        ["enlace,E-01,Enlace sin reserva declarada,TC-E-01,m,,N-01,N-02,10,,"],
    )
    items = AdaptadorTelecom().extraer(ruta)

    enlace = next(item for item in items if item.origen_id == "E-01")
    assert enlace.parametros["reserva"] == Decimal("0")
    assert enlace.cantidad == Decimal("10")


def test_longitud_vacia_falla_con_fila_y_columna(tmp_path):
    ruta = _csv_minimo(
        tmp_path,
        ["enlace,E-02,Enlace sin longitud,TC-E-02,m,,N-01,N-02,,0.10,"],
    )

    with pytest.raises(ValueError, match=r"E-02.*longitud_m"):
        AdaptadorTelecom().extraer(ruta)
