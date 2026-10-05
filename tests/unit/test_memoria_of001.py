"""Consistencia interna de la memoria de calculo a mano de OF-001 completa (SF2, tarea 2.0).

No usa codigo de produccion: lee el bloque JSON de `of001.md`, recalcula con aritmetica exacta lo
que se puede recalcular desde las coordenadas y comprueba que las cifras se sostienen entre si y con
las memorias del bano (oraculo de las tareas 2.1 a 2.5 del sprint final).
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

MEMORIAS = Path(__file__).resolve().parents[1] / "fixtures" / "memorias"
MEMORIA = MEMORIAS / "of001.md"


def _cargar(nombre: str = "of001.md") -> dict:
    ruta = MEMORIAS / nombre
    assert ruta.is_file(), f"falta la memoria de calculo: {ruta}"
    bloques = re.findall(r"```json\n(.*?)\n```", ruta.read_text(encoding="utf-8"), flags=re.DOTALL)
    assert len(bloques) == 1, "debe haber exactamente un bloque json"
    return json.loads(bloques[0])


@pytest.fixture(scope="module")
def memoria() -> dict:
    return _cargar()


def _d(valor: str) -> Decimal:
    return Decimal(valor)


def _pos(memoria: dict, nombre: str) -> tuple[Decimal, Decimal, Decimal]:
    x, y, z = (_d(v) for v in memoria["posiciones"][nombre])
    return x, y, z


def _paso(memoria: dict, a: str, b: str) -> list[Decimal]:
    """Tramos de un paso a -> b (sube, cruza en x, cruza en y, baja); el largo cero se omite."""
    techo = _d(memoria["techo"])
    (ax, ay, az), (bx, by, bz) = _pos(memoria, a), _pos(memoria, b)
    tramos = [techo - az, abs(bx - ax), abs(by - ay), techo - bz]
    return [t for t in tramos if t != 0]


def test_el_json_es_valido_y_tiene_las_tres_especialidades(memoria: dict) -> None:
    assert memoria["unidades"] == "m"
    assert {"agua", "datos", "electricidad"} <= set(memoria)
    assert len(memoria["datos"]["segmentos"]) == 17
    assert len(memoria["electricidad"]["segmentos"]) == 15


# --- agua: se cruza con las memorias del bano ------------------------------------------------


def test_agua_de_la_oficina_es_bano_mas_cocineta(memoria: dict) -> None:
    agua_bano = {p["partida"]: _d(p["cantidad"]) for p in _cargar("bano_of001.md")["partidas"]}
    drenaje_bano = {
        p["partida"]: _d(p["cantidad"]) for p in _cargar("bano_drenaje_of001.md")["partidas"]
    }
    coc = memoria["agua"]["cocineta"]
    factor = 1 + _d(memoria["constantes"]["desperdicio_tuberia"])
    af, dr = coc["agua_fria"], coc["drenaje"]
    assert sum((_d(t) for t in af["tramos"]), Decimal(0)) == _d(af["recorrido"])
    assert sum((_d(t) for t in dr["tramos"]), Decimal(0)) == _d(dr["recorrido"])
    assert _d(dr["piso"]) + _d(dr["pared"]) == _d(dr["recorrido"])  # todo empotrado (D-4)
    assert _d(af["empotrado"]) == _d(af["tramos"][0]) + _d(af["tramos"][2])  # pared; el techo no

    esperado = {
        "af_tuberia_3/4": agua_bano["tuberia_3/4"],
        "af_tuberia_1/2": agua_bano["tuberia_1/2"] + _d(af["recorrido"]) * factor,
        "af_codo_3/4": agua_bano["codo_3/4"],
        "af_codo_1/2": agua_bano["codo_1/2"] + af["codos"]["1/2"],
        "af_tee_3/4": agua_bano["tee_3/4"],
        "af_llave_de_paso": agua_bano["llave_de_paso"] + 1,
        "af_picado_pared": agua_bano["picado_resane_pared"] + _d(af["empotrado"]),
        "af_salida": agua_bano["salida_agua"] + 1,
        "dr_tuberia_2": drenaje_bano["tuberia_2"] + _d(dr["recorrido"]) * factor,
        "dr_tuberia_1 1/2": drenaje_bano["tuberia_1 1/2"],
        "dr_codo_2": drenaje_bano["codo_2"] + dr["codos"]["2"],
        "dr_codo_1 1/2": drenaje_bano["codo_1 1/2"],
        "dr_picado_piso": drenaje_bano["picado_resane_piso"] + _d(dr["piso"]),
        "dr_picado_pared": drenaje_bano["picado_resane_pared"] + _d(dr["pared"]),
        "dr_salida": drenaje_bano["salida_drenaje"] + 1,
    }
    declaradas = {p["partida"]: _d(p["cantidad"]) for p in memoria["agua"]["partidas"]}
    assert declaradas == esperado


# --- utilidades de geometria independientes -----------------------------------------------------


def _extremos(clave: str) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    _, a, b = clave.split("|")
    return tuple(_d(v) for v in a.split(",")), tuple(_d(v) for v in b.split(","))


def _longitud_clave(clave: str) -> Decimal:
    a, b = _extremos(clave)
    return sum((abs(q - p) for p, q in zip(a, b, strict=True)), Decimal(0))


def _contar_accesorios(segmentos: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    nodos: dict[tuple[Decimal, ...], list[dict]] = defaultdict(list)
    for s in segmentos:
        for extremo in _extremos(s["clave"]):
            nodos[extremo].append(s)
    codos: dict[str, int] = defaultdict(int)
    tees: dict[str, int] = defaultdict(int)
    for nodo, segs in nodos.items():
        diametro = max((s["diametro"] for s in segs), key=Fraction)
        if len(segs) >= 3:
            tees[diametro] += len(segs) - 2
        elif len(segs) == 2:
            vectores = []
            for s in segs:
                a, b = _extremos(s["clave"])
                otro = b if a == nodo else a
                vectores.append(tuple((y > x) - (y < x) for x, y in zip(nodo, otro, strict=True)))
            if vectores[0] != tuple(-v for v in vectores[1]):
                codos[diametro] += 1
    return dict(codos), dict(tees)


def _por_diametro(segmentos: list[dict]) -> dict[str, Decimal]:
    total: dict[str, Decimal] = defaultdict(Decimal)
    for s in segmentos:
        total[s["diametro"]] += _d(s["longitud"])
    return dict(total)


def _validar_segmentos(bloque: dict) -> None:
    claves = [s["clave"] for s in bloque["segmentos"]]
    assert len(set(claves)) == len(claves)
    for s in bloque["segmentos"]:
        # la longitud declarada sale de los extremos de la clave (segmentos ortogonales)
        assert _longitud_clave(s["clave"]) == _d(s["longitud"]), s["id"]
        a, b = _extremos(s["clave"])
        assert a < b  # orden (x, y, z)
    total = sum((_d(s["longitud"]) for s in bloque["segmentos"]), Decimal(0))
    assert total == _d(bloque["longitud_unida_total"])
    declarado = {k: _d(v) for k, v in bloque["longitud_unida_por_diametro"].items()}
    assert _por_diametro(bloque["segmentos"]) == declarado
    assert sum(declarado.values(), Decimal(0)) == total
    codos, tees = _contar_accesorios(bloque["segmentos"])
    assert codos == bloque["codos"]
    assert tees == bloque["tees"]


# --- datos -----------------------------------------------------------------------------------


def test_datos_recorridos_desde_las_coordenadas(memoria: dict) -> None:
    datos = memoria["datos"]
    k = memoria["constantes"]
    holgura = _d(k["holgura_rack"]) + _d(k["holgura_punto"])
    for punto, r in datos["recorridos"].items():
        tramos = _paso(memoria, "RK1", punto)
        assert tramos == [_d(v) for v in r["tramos"]], punto
        assert sum(tramos, Decimal(0)) == _d(r["longitud"]), punto
        assert _d(r["longitud"]) + holgura == _d(r["enlace"]), punto
        assert _d(r["enlace"]) * (1 + _d(k["reserva_cable"])) == _d(r["cable"]), punto
        assert _d(r["enlace"]) <= 90  # R10: muy por debajo del limite


def test_datos_cable_y_sin_unir(memoria: dict) -> None:
    datos = memoria["datos"]
    k = memoria["constantes"]
    recorridos = datos["recorridos"]
    suma = sum((_d(r["longitud"]) for r in recorridos.values()), Decimal(0))
    assert suma == _d(datos["longitud_sin_unir"])
    holgura = _d(k["holgura_rack"]) + _d(k["holgura_punto"])
    base = suma + holgura * len(recorridos)
    partidas = {p["partida"]: _d(p["cantidad"]) for p in datos["partidas"]}
    assert partidas["cable_cat_6"] == base * (1 + _d(k["reserva_cable"]))
    assert partidas["cable_cat_6"] == sum((_d(r["cable"]) for r in recorridos.values()), Decimal(0))


def test_datos_union_y_accesorios(memoria: dict) -> None:
    datos = memoria["datos"]
    _validar_segmentos(datos)
    # cada recorrido pasa una vez por cada segmento que lo sirve
    por_servicio = sum(
        (_d(s["longitud"]) * len(s["sirve"]) for s in datos["segmentos"]), Decimal(0)
    )
    assert por_servicio == _d(datos["longitud_sin_unir"])
    assert _d(datos["longitud_sin_unir"]) > _d(datos["longitud_unida_total"])  # [FR-3]
    for s in datos["segmentos"]:
        assert s["clave"].startswith("RK1|")
        assert set(s["sirve"]) <= set(datos["recorridos"])


def test_datos_diametro_de_un_segmento_es_el_mayor_que_sirve(memoria: dict) -> None:
    diametro_punto = {
        "PA1": "3/4",
        "PA2": "3/4",
        "PA3": "3/4",
        "PB1": "3/4",
        "PB2": "3/4",
        "PB3": "3/4",
        "PR1": "1/2",
    }
    for s in memoria["datos"]["segmentos"]:
        esperado = max((diametro_punto[p] for p in s["sirve"]), key=Fraction)
        assert s["diametro"] == esperado, s["id"]


def test_datos_partidas_por_punto(memoria: dict) -> None:
    datos = memoria["datos"]
    n = len(datos["recorridos"])
    assert datos["cajas"] == n
    partidas = {p["partida"]: _d(p["cantidad"]) for p in datos["partidas"]}
    for nombre in ("caja", "faceplate", "jack", "certificacion"):
        assert partidas[nombre] == n
    for diametro, longitud in datos["longitud_unida_por_diametro"].items():
        assert partidas[f"canalizacion_{diametro}"] == _d(longitud)  # sin desperdicio (D-18)


# --- electricidad -----------------------------------------------------------------------------


def _costo(memoria: dict, a: str, b: str) -> Decimal:
    return sum(_paso(memoria, a, b), Decimal(0))


def _vecino_mas_cercano(memoria: dict, puntos: list[str]) -> list[str]:
    restantes, actual, orden = sorted(puntos), "T1", []
    while restantes:
        elegido = min(restantes, key=lambda p: (_costo(memoria, actual, p), p))
        orden.append(elegido)
        restantes.remove(elegido)
        actual = elegido
    return orden


def test_electricidad_el_orden_es_el_del_vecino_mas_cercano(memoria: dict) -> None:
    for circuito in memoria["electricidad"]["circuitos"].values():
        assert _vecino_mas_cercano(memoria, circuito["orden"]) == circuito["orden"]


def test_electricidad_empate_de_c2_lo_gana_el_id_menor(memoria: dict) -> None:
    assert _costo(memoria, "T1", "LZ1") == _costo(memoria, "T1", "LZ2") == Decimal(4)
    assert _costo(memoria, "LZ1", "LZ2") == _costo(memoria, "LZ1", "LZ4") == Decimal(2)


def test_electricidad_pasos_y_cadena_desde_las_coordenadas(memoria: dict) -> None:
    for c in memoria["electricidad"]["circuitos"].values():
        anterior = "T1"
        for paso, punto in zip(c["pasos"], c["orden"], strict=True):
            assert (paso["de"], paso["a"]) == (anterior, punto)
            tramos = _paso(memoria, anterior, punto)
            assert tramos == [_d(t) for t in paso["tramos"]]
            assert sum(tramos, Decimal(0)) == _d(paso["longitud"])
            anterior = punto
        assert sum((_d(p["longitud"]) for p in c["pasos"]), Decimal(0)) == _d(c["cadena"])
        assert len(c["orden"]) <= c["puntos_maximos"]  # R10 de OF-001 limpio


def test_electricidad_conductor_y_union(memoria: dict) -> None:
    ele = memoria["electricidad"]
    k = memoria["constantes"]
    suma = sum((_d(c["cadena"]) for c in ele["circuitos"].values()), Decimal(0))
    assert suma == _d(ele["longitud_sin_unir"])
    partidas = {p["partida"]: _d(p["cantidad"]) for p in ele["partidas"]}
    for c in ele["circuitos"].values():
        esperado = _d(c["cadena"]) * sum(c["conductores"]) * (1 + _d(k["desperdicio_conductor"]))
        assert partidas[f"conductor_{c['calibre']}"] == esperado
    _validar_segmentos(ele)
    for s in ele["segmentos"]:
        assert s["clave"].startswith("T1|")
        assert set(s["sirve"]) <= set(ele["circuitos"])
    # lo ahorrado por la union: bajar a un punto y volver a subir, y la subida comun
    assert suma - _d(ele["longitud_unida_total"]) == Decimal("7.6")


def test_electricidad_partidas_por_punto_y_circuito(memoria: dict) -> None:
    ele = memoria["electricidad"]
    puntos = [p for c in ele["circuitos"].values() for p in c["orden"]]
    partidas = {p["partida"]: _d(p["cantidad"]) for p in ele["partidas"]}
    assert ele["cajas"] == len(puntos) == partidas["caja"]
    assert partidas["salida_tomacorriente"] == ele["salidas_tomacorriente"] == 4
    assert partidas["salida_iluminacion"] == ele["salidas_iluminacion"] == 4
    assert ele["salidas_tomacorriente"] + ele["salidas_iluminacion"] == len(puntos)
    assert partidas["proteccion"] == ele["proteccion"] == len(ele["circuitos"])
    for diametro, longitud in ele["longitud_unida_por_diametro"].items():
        assert partidas[f"tuberia_{diametro}"] == _d(longitud)  # sin desperdicio (D-18)


def test_claves_de_la_memoria_no_chocan_entre_especialidades(memoria: dict) -> None:
    claves = [s["clave"] for e in ("datos", "electricidad") for s in memoria[e]["segmentos"]]
    assert len(set(claves)) == len(claves)


def test_las_tablas_markdown_coinciden_con_el_json(memoria: dict) -> None:
    texto = MEMORIA.read_text(encoding="utf-8")
    for prefijo, bloque in (("DS", "datos"), ("ES", "electricidad")):
        filas = re.findall(rf"^\| ({prefijo}\d+) \| .* \| ([\d,]+) \| ", texto, flags=re.MULTILINE)
        impresas = {i: Decimal(v.replace(",", ".")) for i, v in filas}
        declaradas = {s["id"]: _d(s["longitud"]) for s in memoria[bloque]["segmentos"]}
        assert impresas == declaradas, prefijo
