"""Geometria de los circuitos (tarea 2.2, spec §6.4 y §6.5) contra la memoria `of001.md`.

La cadena de un circuito es el recorrido del tablero por sus puntos en orden: cada paso sube al
techo, cruza en x y en y, y baja. Sin orden declarado lo propone el vecino mas cercano (D-14).
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio import Circuito, Coord, Espacio, ModoRecorrido, Recorrido, Tramo
from adapters.espacio.geometria import (
    analizar,
    longitud_tramos,
    orden_de_cadena,
    recorrido_de_circuito,
    tramos_de_circuito,
    unir_segmentos,
)
from tests.fixtures.espacio_of001 import espacio_of001

MEMORIAS = Path(__file__).resolve().parents[1] / "fixtures" / "memorias"
TOLERANCIA = Decimal("0.001")
D = Decimal


@pytest.fixture(scope="module")
def memoria() -> dict:
    texto = (MEMORIAS / "of001.md").read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", texto, flags=re.DOTALL)[0])


def _circuito(espacio: Espacio, id_: str) -> Circuito:
    return next(c for c in espacio.circuitos if c.id == id_)


def _con_circuito(espacio: Espacio, id_: str, **cambios: object) -> Espacio:
    return replace(
        espacio,
        circuitos=tuple(replace(c, **cambios) if c.id == id_ else c for c in espacio.circuitos),
    )


def test_el_orden_declarado_manda(memoria: dict) -> None:
    espacio = espacio_of001()
    assert orden_de_cadena(espacio, _circuito(espacio, "C1")) == ("TA1", "TA2", "TB1", "TB2")
    invertido = _con_circuito(espacio, "C1", orden=("TB2", "TB1", "TA2", "TA1"))
    assert orden_de_cadena(invertido, _circuito(invertido, "C1")) == (
        "TB2",
        "TB1",
        "TA2",
        "TA1",
    )
    # y la cadena cambia con el: ir primero al mas lejano alarga el recorrido
    larga = longitud_tramos(tramos_de_circuito(invertido, _circuito(invertido, "C1")))
    assert larga > D(memoria["electricidad"]["circuitos"]["C1"]["cadena"])


def test_sin_orden_lo_propone_el_vecino_mas_cercano(memoria: dict) -> None:
    espacio = espacio_of001()
    c2 = _circuito(espacio, "C2")
    assert c2.orden == ()
    assert orden_de_cadena(espacio, c2) == tuple(
        memoria["electricidad"]["circuitos"]["C2"]["orden"]
    )


def test_el_vecino_mas_cercano_desempata_por_id() -> None:
    """Desde T1, LZ1 y LZ2 cuestan 4,0: gana LZ1. Desde LZ1, LZ2 y LZ4 cuestan 2,0: gana LZ2."""
    espacio = espacio_of001()
    orden = orden_de_cadena(espacio, _circuito(espacio, "C2"))
    assert orden[:2] == ("LZ1", "LZ2")


def test_un_punto_del_circuito_fuera_del_orden_se_agrega_al_final() -> None:
    espacio = _con_circuito(espacio_of001(), "C1", orden=("TA1", "TA2"))
    orden = orden_de_cadena(espacio, _circuito(espacio, "C1"))
    assert orden == ("TA1", "TA2", "TB1", "TB2")  # los que faltan, por vecino mas cercano


def test_un_circuito_sin_puntos_no_tiene_cadena() -> None:
    espacio = replace(
        espacio_of001(),
        circuitos=espacio_of001().circuitos
        + (
            Circuito(
                id="C9",
                tablero="T1",
                numero=9,
                conductores=(1, 1, 1),
                calibre="12 AWG",
                puntos_maximos=4,
            ),  # fmt: skip
        ),
    )
    c9 = _circuito(espacio, "C9")
    assert orden_de_cadena(espacio, c9) == ()
    assert recorrido_de_circuito(espacio, c9) == ()


def test_un_tablero_inexistente_no_tiene_cadena() -> None:
    espacio = _con_circuito(espacio_of001(), "C1", tablero="NO-EXISTE")
    assert recorrido_de_circuito(espacio, _circuito(espacio, "C1")) == ()
    assert unir_segmentos(espacio, "T1")  # el otro circuito sigue en el tablero T1


def test_la_cadena_de_cada_circuito_iguala_la_memoria(memoria: dict) -> None:
    espacio = espacio_of001()
    for id_, c in memoria["electricidad"]["circuitos"].items():
        tramos = recorrido_de_circuito(espacio, _circuito(espacio, id_))
        assert abs(longitud_tramos(tramos) - D(c["cadena"])) <= TOLERANCIA, id_
        # los tramos, paso a paso: sube, cruza en x, cruza en y, baja; el largo cero se omite
        esperado = [D(t) for paso in c["pasos"] for t in paso["tramos"]]
        assert len(tramos) == len(esperado), id_
        for t, e in zip(tramos, esperado, strict=True):
            assert abs(t.longitud - e) <= TOLERANCIA, id_
        assert [t.orden for t in tramos] == list(range(1, len(tramos) + 1))


def test_los_tramos_de_la_cadena_son_ortogonales_y_encadenan() -> None:
    espacio = espacio_of001()
    for c in espacio.circuitos:
        tramos = recorrido_de_circuito(espacio, c)
        for t in tramos:
            a, b = t.vertices
            cambios = sum(
                1 for p, q in zip((a.x, a.y, a.z), (b.x, b.y, b.z), strict=True) if p != q
            )
            assert cambios == 1
        for t, u in zip(tramos, tramos[1:], strict=False):
            assert t.vertices[-1] == u.vertices[0]
        assert tramos[0].vertices[0] == espacio.fuentes[-1].posicion  # el tablero T1


def test_la_cadena_marca_la_superficie_y_el_empotrado_por_defecto() -> None:
    espacio = espacio_of001()
    tramos = recorrido_de_circuito(espacio, _circuito(espacio, "C1"))
    sube, en_x = tramos[0], tramos[1]
    assert sube.superficie.value == "pared" and sube.empotrado is True  # D-4
    assert en_x.superficie.value == "techo" and en_x.empotrado is False


def test_la_union_de_las_cadenas_iguala_la_memoria(memoria: dict) -> None:
    espacio = espacio_of001()
    segmentos = {s.clave: s for s in unir_segmentos(espacio, "T1")}
    esperado = {s["clave"]: s for s in memoria["electricidad"]["segmentos"]}
    assert set(segmentos) == set(esperado)
    for clave, s in esperado.items():
        seg = segmentos[clave]
        assert abs(seg.longitud - D(s["longitud"])) <= TOLERANCIA, clave
        assert seg.diametro == s["diametro"], clave
        assert list(seg.sirve) == sorted(s["sirve"]), clave


def test_analizar_electricidad_iguala_la_memoria(memoria: dict) -> None:
    ele = memoria["electricidad"]
    g = analizar(espacio_of001(), "electricidad")
    assert abs(g.longitud_sin_unir - D(ele["longitud_sin_unir"])) <= TOLERANCIA
    assert abs(g.longitud_unida - D(ele["longitud_unida_total"])) <= TOLERANCIA
    for diametro, longitud in ele["longitud_unida_por_diametro"].items():
        assert abs(g.longitud_por_diametro[diametro] - D(longitud)) <= TOLERANCIA
    assert g.codos == ele["codos"]
    assert g.tees == ele["tees"]
    assert g.cajas == ele["cajas"]


def test_la_subida_y_la_bajada_coincidentes_se_unen_una_vez() -> None:
    """D-15: bajar a un punto y volver a subir es un solo segmento para la tuberia."""
    espacio = espacio_of001()
    g = analizar(espacio, "electricidad")
    conductor = sum(longitud_tramos(recorrido_de_circuito(espacio, c)) for c in espacio.circuitos)
    assert abs(conductor - g.longitud_unida - D("7.6")) <= TOLERANCIA


def test_el_diametro_de_un_circuito_es_el_mayor_de_sus_puntos() -> None:
    espacio = espacio_of001()
    puntos = tuple(
        replace(p, especificaciones=(("diametro", '1"'),)) if p.id == "LZ4" else p
        for p in espacio.puntos
    )
    espacio = replace(espacio, puntos=puntos)
    por_diametro = analizar(espacio, "electricidad").longitud_por_diametro
    # C2 pasa a ser de 1": sus 9,0 m y la subida comun (1,0 m, el mayor de C1 y C2) son de 1"
    assert set(por_diametro) == {"1", "3/4"}
    assert abs(por_diametro["1"] - D("10.0")) <= TOLERANCIA
    assert abs(por_diametro["3/4"] - D("15.3")) <= TOLERANCIA


def test_un_circuito_sin_diametros_declarados_no_inventa_uno() -> None:
    espacio = espacio_of001()
    puntos = tuple(
        replace(p, especificaciones=()) if p.circuito_id == "C2" else p for p in espacio.puntos
    )
    g = analizar(replace(espacio, puntos=puntos), "electricidad")
    assert abs(g.longitud_por_diametro["sin_diametro"] - D("9.0")) <= TOLERANCIA


def test_un_recorrido_declarado_de_circuito_manda_sobre_la_cadena() -> None:
    espacio = espacio_of001()
    tramo = Tramo(
        orden=1,
        superficie="techo",
        vertices=(Coord(D("4"), D("1"), D("1.5")), Coord(D("4"), D("1"), D("2.5"))),
    )
    declarado = Recorrido(
        id="R-C2", circuito_id="C2", modo=ModoRecorrido.DECLARADO, tramos=(tramo,)
    )
    espacio = replace(espacio, recorridos=(declarado,))
    assert tramos_de_circuito(espacio, _circuito(espacio, "C2")) == (tramo,)
    assert recorrido_de_circuito(espacio, _circuito(espacio, "C2")) != (
        tramo,
    )  # el propuesto sigue
    # la union ya no ve las luminarias: solo queda la subida comun y la cadena de C1
    g = analizar(espacio, "electricidad")
    assert abs(g.longitud_unida - D("16.3")) <= TOLERANCIA


def test_el_techo_es_el_mayor_de_los_dos_ambientes_del_paso() -> None:
    """Un paso entre un ambiente de 2,5 m y otro de 3,0 m sube a 3,0 m."""
    espacio = espacio_of001()
    ambientes = tuple(replace(a, alto=D("3.0")) if a.id == "ZB" else a for a in espacio.ambientes)
    espacio = replace(espacio, ambientes=ambientes)
    tramos = recorrido_de_circuito(espacio, _circuito(espacio, "C1"))
    assert max(v.z for t in tramos for v in t.vertices) == D("3.0")
