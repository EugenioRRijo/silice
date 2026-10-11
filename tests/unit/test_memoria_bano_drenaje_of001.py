"""Consistencia interna de la memoria de calculo a mano del drenaje del bano de OF-001.

No usa codigo de produccion: lee el bloque JSON y comprueba que sus cifras se sostienen entre si
(oraculo del drenaje de la tarea 1.5 del sprint final).
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

MEMORIA = Path(__file__).resolve().parents[1] / "fixtures" / "memorias" / "bano_drenaje_of001.md"


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


def _magnitud(diametro: str) -> Fraction:
    return sum((Fraction(t) for t in diametro.split()), Fraction(0))


def test_la_memoria_existe_y_el_json_es_valido(memoria: dict) -> None:
    assert memoria["unidades"] == "m"
    assert len(memoria["segmentos"]) == 5


def test_suma_de_segmentos_es_el_total_y_no_hay_pendiente(memoria: dict) -> None:
    total = sum((_d(s["longitud"]) for s in memoria["segmentos"]), Decimal(0))
    assert total == _d(memoria["longitud_unida_total"])
    sin_unir = sum((_d(r["longitud"]) for r in memoria["recorridos"].values()), Decimal(0))
    assert sin_unir == _d(memoria["longitud_sin_unir"])
    compartido = sum(
        (_d(s["longitud"]) for s in memoria["segmentos"] if len(s["sirve"]) > 1), Decimal(0)
    )
    assert sin_unir - total == compartido


def test_tramos_de_cada_recorrido_suman_su_longitud(memoria: dict) -> None:
    for recorrido in memoria["recorridos"].values():
        assert sum((_d(t) for t in recorrido["tramos"]), Decimal(0)) == _d(recorrido["longitud"])


def test_longitud_por_diametro_y_por_superficie(memoria: dict) -> None:
    por_diametro: dict[str, Decimal] = {}
    for s in memoria["segmentos"]:
        por_diametro[s["diametro"]] = por_diametro.get(s["diametro"], Decimal(0)) + _d(
            s["longitud"]
        )
    assert por_diametro == {k: _d(v) for k, v in memoria["longitud_unida_por_diametro"].items()}
    por_superficie: dict[str, Decimal] = {}
    for s in memoria["segmentos"]:
        if s["empotrado"]:
            por_superficie[s["superficie"]] = por_superficie.get(s["superficie"], Decimal(0)) + _d(
                s["longitud"]
            )
    assert por_superficie == {k: _d(v) for k, v in memoria["longitud_empotrada"].items()}


def test_partidas_con_desperdicio_en_decimal_exacto(memoria: dict) -> None:
    factor = 1 + _d(memoria["desperdicio_tuberia"])
    partidas = {p["partida"]: _d(p["cantidad"]) for p in memoria["partidas"]}
    for diametro, longitud in memoria["longitud_unida_por_diametro"].items():
        assert partidas[f"tuberia_{diametro}"] == _d(longitud) * factor
    for diametro, n in memoria["codos"].items():
        assert partidas[f"codo_{diametro}"] == n
    for superficie, longitud in memoria["longitud_empotrada"].items():
        assert partidas[f"picado_resane_{superficie}"] == _d(longitud)
    puntos = {p for s in memoria["segmentos"] for p in s["sirve"]}
    assert partidas["salida_drenaje"] == memoria["salidas_drenaje"] == len(puntos)
    assert not any(k.startswith("llave") for k in partidas)  # el drenaje no lleva llave de paso
    assert not any(k.startswith("tee") for k in partidas) and memoria["tees"] == {}


def _extremos(clave: str) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    _, a, b = clave.split("|")
    return tuple(_d(v) for v in a.split(",")), tuple(_d(v) for v in b.split(","))


def _direccion(a: tuple[Decimal, ...], b: tuple[Decimal, ...]) -> tuple[int, ...]:
    return tuple((v > 0) - (v < 0) for v in (y - x for x, y in zip(a, b, strict=True)))


def test_codos_y_tees_por_grado_de_nodo(memoria: dict) -> None:
    nodos: dict[tuple[Decimal, ...], list[dict]] = {}
    for s in memoria["segmentos"]:
        for extremo in _extremos(s["clave"]):
            nodos.setdefault(extremo, []).append(s)
    codos: dict[str, int] = {}
    tees: dict[str, int] = {}
    for nodo, segs in nodos.items():
        diametro = max((s["diametro"] for s in segs), key=_magnitud)
        if len(segs) >= 3:
            tees[diametro] = tees.get(diametro, 0) + len(segs) - 2
        elif len(segs) == 2:
            vectores = []
            for s in segs:
                a, b = _extremos(s["clave"])
                vectores.append(_direccion(nodo, b if a == nodo else a))
            if vectores[0] != tuple(-v for v in vectores[1]):
                codos[diametro] = codos.get(diametro, 0) + 1
    assert codos == memoria["codos"]
    assert tees == memoria["tees"]


def test_claves_de_la_tabla_markdown_coinciden_con_el_json(memoria: dict) -> None:
    texto = MEMORIA.read_text(encoding="utf-8")
    impresas = dict(re.findall(r"^\| (SD\d) \| `([^`]+)` \|$", texto, flags=re.MULTILINE))
    impresas = {k: v.replace("\\|", "|") for k, v in impresas.items()}
    assert impresas == {s["id"]: s["clave"] for s in memoria["segmentos"]}


def test_la_pendiente_no_altera_ninguna_longitud(memoria: dict) -> None:
    """Cada segmento mide la distancia entre sus extremos: sin pendiente numerica."""
    for s in memoria["segmentos"]:
        a, b = _extremos(s["clave"])
        suma = sum(((q - p) ** 2 for p, q in zip(a, b, strict=True)), Decimal(0))
        assert suma.sqrt() == _d(s["longitud"]), s["id"]
