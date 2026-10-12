"""La vista del catalogo del asistente y la procedencia MaPreX (S4 §6, §8.1; pregunta P7).

P7 (ratificada por Eugenio el 2026-10-11): en modo nube, de MaPreX solo viajan codigo y unidad. Los
listados de MaPreX son de INSUMOS: ninguna partida del catalogo actual lleva un codigo de MaPreX,
y `consultar_partida` devuelve tipos de insumo, nunca sus descripciones. Esta prueba lo vigila: si
un dia una partida entra con un codigo de MaPreX, falla y hay que configurar `prefijos_de_maprex`.
"""

from __future__ import annotations

import csv

from asistente.catalogo import CatalogoDeLaBase, PartidaVista
from asistente.configuracion import ConfiguracionIA, de_maprex
from core.contracts.dominio import Dominio
from tests.fixtures import caso_of001, caso_ti001
from tests.fixtures.arquitectura import RAIZ

CARPETA = RAIZ / "data" / "precios" / "maprex_2026-07"


def _referencias_de_maprex() -> set[str]:
    refs: set[str] = set()
    for ruta in sorted(CARPETA.glob("referencia_*.csv")):
        with ruta.open(encoding="utf-8", newline="") as archivo:
            refs.update(f["ref_maprex"] for f in csv.DictReader(archivo) if f["ref_maprex"])
    return refs


def test_ningun_codigo_de_partida_del_catalogo_de_prueba_es_una_referencia_de_maprex():
    refs = _referencias_de_maprex()
    assert len(refs) > 50  # la lectura funciono
    codigos = set(caso_of001.COMPOSICIONES) | set(caso_ti001.COMPOSICIONES)
    assert codigos and not codigos & refs


def test_de_maprex_se_decide_por_los_prefijos_que_configura_el_administrador():
    sin = ConfiguracionIA()
    con = ConfiguracionIA(prefijos_de_maprex=("MPX-", "PLO"))
    assert not de_maprex("AF-SALIDA", sin) and not de_maprex("MPX-1", sin)
    assert de_maprex("MPX-1", con) and de_maprex("PLOA38", con) and not de_maprex("AF-SALIDA", con)


def partidas():
    return [
        PartidaVista("AF-SALIDA", "Salida de agua fria", "punto", Dominio.CIVIL),
        PartidaVista("EL-TOMA", "Salida de toma electrica", "punto", Dominio.CIVIL),
        PartidaVista("TI-RACK", "Rack de datos", "pieza", Dominio.TELECOM),
    ]


def test_la_busqueda_semantica_manda_y_la_de_palabras_es_el_respaldo_declarado():
    semantica = CatalogoDeLaBase(partidas(), lambda texto: [("TI-RACK", 0.9), ("NO-ESTA", 0.8)])
    encontradas, es_semantica = semantica.buscar("gabinete", 5)
    assert [(p.codigo, p.puntaje) for p in encontradas] == [("TI-RACK", 0.9)] and es_semantica
    sin_resultado = CatalogoDeLaBase(partidas(), lambda texto: [])
    encontradas, es_semantica = sin_resultado.buscar("salida de agua", 5)
    assert [p.codigo for p in encontradas] == ["AF-SALIDA", "EL-TOMA"] and not es_semantica
    assert CatalogoDeLaBase(partidas()).buscar("zzz", 5) == ([], False)
    assert CatalogoDeLaBase(partidas()).partida("TI-RACK").unidad == "pieza"
    assert CatalogoDeLaBase(partidas()).partida("XX") is None
