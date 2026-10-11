"""Consistencia interna de la memoria de calculo a mano del bano de OF-001.

No usa codigo de produccion: lee el bloque JSON de la memoria y comprueba que sus cifras
se sostienen entre si (oraculo de las tareas 1.2 a 1.5 del sprint final).
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

MEMORIA = Path(__file__).resolve().parents[1] / "fixtures" / "memorias" / "bano_of001.md"


def _cargar() -> dict:
    assert MEMORIA.is_file(), f"falta la memoria de calculo: {MEMORIA}"
    texto = MEMORIA.read_text(encoding="utf-8")
    bloques = re.findall(r"```json\n(.*?)\n```", texto, flags=re.DOTALL)
    assert len(bloques) == 1, "debe haber exactamente un bloque json"
    return json.loads(bloques[0])


@pytest.fixture(scope="module")
def memoria() -> dict:
    return _cargar()


def _d(valor: str) -> Decimal:
    return Decimal(valor)


def test_la_memoria_existe_y_el_json_es_valido(memoria: dict) -> None:
    assert memoria["unidades"] == "m"
    assert len(memoria["segmentos"]) == 6


def test_suma_de_segmentos_unicos_es_el_total_declarado(memoria: dict) -> None:
    total = sum((_d(s["longitud"]) for s in memoria["segmentos"]), Decimal(0))
    assert total == _d(memoria["longitud_unida_total"])


def test_claves_de_segmento_unicas(memoria: dict) -> None:
    claves = [s["clave"] for s in memoria["segmentos"]]
    assert len(set(claves)) == len(claves)


def test_la_union_ahorra_el_tramo_compartido(memoria: dict) -> None:
    """[FR-3]: lo compartido no se cuenta dos veces."""
    sin_unir = sum((_d(r["longitud"]) for r in memoria["recorridos"].values()), Decimal(0))
    assert sin_unir == _d(memoria["longitud_sin_unir"])
    compartido = sum(
        (_d(s["longitud"]) for s in memoria["segmentos"] if len(s["sirve"]) > 1),
        Decimal(0),
    )
    assert compartido > 0
    assert sin_unir - _d(memoria["longitud_unida_total"]) == compartido


def test_tramos_de_cada_recorrido_suman_su_longitud(memoria: dict) -> None:
    for recorrido in memoria["recorridos"].values():
        assert sum((_d(t) for t in recorrido["tramos"]), Decimal(0)) == _d(recorrido["longitud"])


def test_longitud_por_diametro_y_empotrada(memoria: dict) -> None:
    por_diametro: dict[str, Decimal] = {}
    for s in memoria["segmentos"]:
        previo = por_diametro.get(s["diametro"], Decimal(0))
        por_diametro[s["diametro"]] = previo + _d(s["longitud"])
    declarado = {k: _d(v) for k, v in memoria["longitud_unida_por_diametro"].items()}
    assert por_diametro == declarado
    empotrada = sum((_d(s["longitud"]) for s in memoria["segmentos"] if s["empotrado"]), Decimal(0))
    assert empotrada == _d(memoria["longitud_empotrada"])


def test_partidas_con_desperdicio_en_decimal_exacto(memoria: dict) -> None:
    factor = 1 + _d(memoria["desperdicio_tuberia"])
    partidas = {p["partida"]: _d(p["cantidad"]) for p in memoria["partidas"]}
    for diametro, longitud in memoria["longitud_unida_por_diametro"].items():
        assert partidas[f"tuberia_{diametro}"] == _d(longitud) * factor
    for diametro, n in memoria["codos"].items():
        assert partidas[f"codo_{diametro}"] == n
    for diametro, n in memoria["tees"].items():
        assert partidas[f"tee_{diametro}"] == n
    assert partidas["picado_resane_pared"] == _d(memoria["longitud_empotrada"])
    puntos = {p for s in memoria["segmentos"] for p in s["sirve"]}
    assert partidas["salida_agua"] == memoria["salidas_agua"] == len(puntos)
    assert partidas["llave_de_paso"] == len(memoria["puntos_con_llave"])
    assert set(memoria["puntos_con_llave"]) <= puntos
    assert memoria["cajas"] == len(puntos)  # una caja por punto (spec 6.5), concepto distinto


def test_casos_degenerados_sin_tramos(memoria: dict) -> None:
    """[FR-2]: fuente sin puntos y punto sin recorrido dan cero, sin division por cero."""
    assert memoria["degenerados"]["espacio_vacio"]["items"] == 0
    for caso in ("fuente_sin_puntos", "punto_sin_recorrido"):
        d = memoria["degenerados"][caso]
        assert d["tramos"] == 0
        assert _d(d["longitud"]) == 0
        assert d["codos"] == 0
        assert d["tees"] == 0


def _extremos(clave: str) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    _, a, b = clave.split("|")
    return tuple(_d(v) for v in a.split(",")), tuple(_d(v) for v in b.split(","))


def _direccion(a: tuple[Decimal, ...], b: tuple[Decimal, ...]) -> tuple[int, ...]:
    """Eje y sentido unitario de un segmento ortogonal (desde a hacia b)."""
    return tuple((v > 0) - (v < 0) for v in (y - x for x, y in zip(a, b, strict=True)))


def test_codos_y_tees_por_grado_de_nodo(memoria: dict) -> None:
    """Spec 6.5: tee = nodo de grado d>=3 aporta d-2; codo = nodo de grado 2 no colineal."""
    nodos: dict[tuple[Decimal, ...], list[dict]] = {}
    for s in memoria["segmentos"]:
        for extremo in _extremos(s["clave"]):
            nodos.setdefault(extremo, []).append(s)
    codos: dict[str, int] = {}
    tees: dict[str, int] = {}
    for nodo, segs in nodos.items():
        diametro = max((s["diametro"] for s in segs), key=Fraction)
        if len(segs) >= 3:
            tees[diametro] = tees.get(diametro, 0) + len(segs) - 2
        elif len(segs) == 2:
            vectores = []
            for s in segs:
                a, b = _extremos(s["clave"])
                otro = b if a == nodo else a
                vectores.append(_direccion(nodo, otro))
            if vectores[0] != tuple(-v for v in vectores[1]):  # no colineales
                codos[diametro] = codos.get(diametro, 0) + 1
    assert codos == memoria["codos"]
    assert tees == memoria["tees"]


def test_claves_de_la_tabla_markdown_coinciden_con_el_json(memoria: dict) -> None:
    texto = MEMORIA.read_text(encoding="utf-8")
    impresas = dict(re.findall(r"^\| (S\d) \| `([^`]+)` \|$", texto, flags=re.MULTILINE))
    impresas = {k: v.replace("\\|", "|") for k, v in impresas.items()}
    assert impresas == {s["id"]: s["clave"] for s in memoria["segmentos"]}
