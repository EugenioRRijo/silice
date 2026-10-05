"""Geometria de la hoja de metrajes (spec §6.4 y §6.5) contra la memoria a mano del bano de OF-001.

Las cifras salen del bloque JSON de `tests/fixtures/memorias/bano_of001.md`, no se copian aqui.
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio import (
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    ModoRecorrido,
    Punto,
    Recorrido,
    SobrescrituraSegmento,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoPunto,
    Tramo,
    derivar,
    geometria,
)
from adapters.espacio.geometria import (
    analizar,
    clave_segmento,
    longitud_tramos,
    recorrido_propuesto,
    sobrescrituras_huerfanas,
    tramos_de,
    unir_segmentos,
)
from adapters.espacio.reglas import reglas_espacio
from tests.fixtures.espacio_bano import espacio_bano

D = Decimal
TOL = D("0.001")
MEMORIA = Path(__file__).resolve().parents[1] / "fixtures" / "memorias" / "bano_of001.md"


@pytest.fixture(scope="module")
def memoria() -> dict:
    texto = MEMORIA.read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", texto, flags=re.DOTALL)[0])


def cerca(a: Decimal, b: str | Decimal) -> bool:
    return abs(a - D(b)) <= TOL


def c(x: str, y: str, z: str) -> Coord:
    return Coord(D(x), D(y), D(z))


def punto(espacio: Espacio, pid: str) -> Punto:
    return next(p for p in espacio.puntos if p.id == pid)


def sin_recorridos(espacio: Espacio) -> Espacio:
    return replace(espacio, recorridos=(), sobrescrituras=())


def fuente_f2() -> Fuente:
    return Fuente(
        id="F2",
        especialidad=Especialidad.AGUA,
        tipo=TipoFuente.MONTANTE_AGUA,
        ambiente_id="BAN-01",
        posicion=c("2", "1.5", "0"),
        origen_id="O1",
    )


# --- recorrido propuesto -----------------------------------------------------------------


def test_recorrido_propuesto_de_cada_punto_del_oraculo(memoria: dict) -> None:
    esp = espacio_bano()
    for pid, esperado in memoria["recorridos"].items():
        tramos = recorrido_propuesto(esp, punto(esp, pid))
        assert len(tramos) == len(esperado["tramos"])
        assert all(cerca(t.longitud, e) for t, e in zip(tramos, esperado["tramos"], strict=True))
        assert cerca(longitud_tramos(tramos), esperado["longitud"])


def test_recorrido_propuesto_omite_el_tramo_en_y_de_largo_cero() -> None:
    esp = espacio_bano()
    tramos = recorrido_propuesto(esp, punto(esp, "P1"))
    assert [t.superficie for t in tramos] == [
        SuperficieTramo.PARED,
        SuperficieTramo.TECHO,
        SuperficieTramo.PARED,
    ]
    assert all(t.longitud > 0 for t in tramos)


def test_tramo_vertical_baja_hasta_la_altura_del_punto() -> None:
    esp = espacio_bano()
    ultimo = recorrido_propuesto(esp, punto(esp, "P2"))[-1]
    assert ultimo.vertices[0] == c("1", "1.5", "2.5")
    assert ultimo.vertices[-1] == c("1", "1.5", "1.2")
    assert cerca(ultimo.longitud, "1.300")


def test_punto_sin_fuente_no_tiene_recorrido() -> None:
    esp = espacio_bano()
    p3 = replace(punto(esp, "P1"), id="P3", nombre="llave de manguera", fuente_id=None)
    assert recorrido_propuesto(esp, p3) == ()


def test_punto_sin_recorrido_no_aporta_segmentos(memoria: dict) -> None:
    esp = espacio_bano()
    p3 = replace(punto(esp, "P1"), id="P3", fuente_id=None, posicion=c("1.8", "1.5", "0.4"))
    esp3 = replace(esp, puntos=esp.puntos + (p3,), recorridos=(), sobrescrituras=())
    g = analizar(esp3, Especialidad.AGUA)
    d = memoria["degenerados"]["punto_sin_recorrido"]
    assert cerca(g.longitud_unida, memoria["longitud_unida_total"])
    assert g.cajas == 3  # una por punto, aunque P3 no tenga recorrido
    assert d["tramos"] == 0 and d["codos"] == 0 and d["tees"] == 0


def test_fuente_sin_puntos_produce_cero(memoria: dict) -> None:
    esp = espacio_bano()
    esp2 = replace(esp, fuentes=esp.fuentes + (fuente_f2(),), recorridos=(), sobrescrituras=())
    assert unir_segmentos(esp2, "F2") == ()
    d = memoria["degenerados"]["fuente_sin_puntos"]
    g = analizar(replace(esp2, puntos=()), Especialidad.AGUA)
    assert (g.segmentos, g.codos, g.tees) == ((), {}, {})
    assert cerca(g.longitud_unida, d["longitud"]) and d["tramos"] == 0


def test_espacio_vacio_no_produce_nada(memoria: dict) -> None:
    g = analizar(Espacio(), Especialidad.AGUA)
    assert g.segmentos == ()
    assert g.longitud_unida == 0 and g.longitud_sin_unir == 0
    assert g.codos == {} and g.tees == {} and g.cajas == 0
    assert unir_segmentos(Espacio()) == ()
    assert memoria["degenerados"]["espacio_vacio"]["items"] == 0


def test_tramo_declarado_de_largo_cero_se_omite() -> None:
    esp = espacio_bano()
    cero = Tramo(
        orden=1,
        superficie=SuperficieTramo.TECHO,
        vertices=(c("0", "0", "2.5"), c("0", "0", "2.5")),
    )
    r = Recorrido(id="R-P1", punto_id="P1", modo=ModoRecorrido.DECLARADO, tramos=(cero,))
    solo_p1 = replace(esp, puntos=(punto(esp, "P1"),), recorridos=(r,), sobrescrituras=())
    assert unir_segmentos(solo_p1) == ()
    g = analizar(solo_p1, Especialidad.AGUA)
    assert g.segmentos == () and g.accesorios == ()
    assert g.longitud_sin_unir == 0 and g.longitud_unida == 0


def test_tramos_de_prefiere_el_declarado_y_si_no_propone() -> None:
    esp = espacio_bano()
    assert tramos_de(esp, punto(esp, "P1")) == esp.recorridos[0].tramos
    assert tramos_de(esp, punto(esp, "P2")) == recorrido_propuesto(esp, punto(esp, "P2"))


# --- union de segmentos (FR-3) -----------------------------------------------------------


def test_claves_y_longitudes_de_los_seis_segmentos(memoria: dict) -> None:
    segs = unir_segmentos(espacio_bano())
    por_clave = {s.clave: s for s in segs}
    assert len(segs) == len(memoria["segmentos"]) == 6
    for esperado in memoria["segmentos"]:
        s = por_clave[esperado["clave"]]
        assert cerca(s.longitud, esperado["longitud"]), esperado["id"]
        assert s.diametro == esperado["diametro"], esperado["id"]
        assert s.empotrado is esperado["empotrado"], esperado["id"]
        assert set(s.sirve) == set(esperado["sirve"]), esperado["id"]


def test_la_tuberia_compartida_no_se_cuenta_dos_veces(memoria: dict) -> None:
    g = analizar(espacio_bano(), Especialidad.AGUA)
    assert cerca(g.longitud_sin_unir, memoria["longitud_sin_unir"])
    assert cerca(g.longitud_unida, memoria["longitud_unida_total"])
    assert cerca(g.longitud_sin_unir - g.longitud_unida, "3.500")


def test_longitudes_por_diametro_y_por_superficie(memoria: dict) -> None:
    g = analizar(espacio_bano(), Especialidad.AGUA)
    assert set(g.longitud_por_diametro) == set(memoria["longitud_unida_por_diametro"])
    for diam, esperado in memoria["longitud_unida_por_diametro"].items():
        assert cerca(g.longitud_por_diametro[diam], esperado)
    assert cerca(g.longitud_empotrada, memoria["longitud_empotrada"])
    assert cerca(g.longitud_expuesta, D(memoria["longitud_unida_total"]) - D("5.700"))


def test_codos_tees_y_cajas_del_oraculo(memoria: dict) -> None:
    g = analizar(espacio_bano(), Especialidad.AGUA)
    assert g.codos == memoria["codos"]
    assert g.tees == memoria["tees"]
    assert g.cajas == memoria["cajas"]


def test_clave_segmento_formato_exacto() -> None:
    clave = clave_segmento("F1", c("1.5", "0", "2.5"), c("1.5", "0", "0.6"))
    assert clave == "F1|1.500,0.000,0.600|1.500,0.000,2.500"
    # el orden de los extremos no importa y se redondea a 0,001
    assert clave == clave_segmento("F1", c("1.5004", "0", "0.6"), c("1.5", "0", "2.5"))
    assert clave_segmento("F1", c("-0.0001", "0", "0"), c("1", "0", "0")).startswith(
        "F1|0.000,0.000,0.000|"
    )


def test_solape_total_une_dos_recorridos_identicos() -> None:
    esp = sin_recorridos(espacio_bano())
    copia = replace(punto(esp, "P2"), id="P9", nombre="copia")
    g = analizar(replace(esp, puntos=esp.puntos + (copia,)), Especialidad.AGUA)
    segs = {s.clave: s for s in g.segmentos}
    assert len(segs) == 6
    assert set(segs["F1|1.000,1.500,1.200|1.000,1.500,2.500"].sirve) == {"P2", "P9"}
    assert cerca(g.longitud_unida, "8.700")
    assert cerca(g.longitud_sin_unir, "18.500")
    assert g.codos == {"3/4": 2, "1/2": 1} and g.tees == {"3/4": 1}


def test_solape_parcial_parte_el_segmento_mas_largo() -> None:
    claves = {s.clave for s in unir_segmentos(sin_recorridos(espacio_bano()))}
    # P1-2 (0 a 1,5 en x) se parte en el nodo (1; 0; 2,5), donde termina P2-2
    assert "F1|0.000,0.000,2.500|1.000,0.000,2.500" in claves
    assert "F1|1.000,0.000,2.500|1.500,0.000,2.500" in claves
    assert "F1|0.000,0.000,2.500|1.500,0.000,2.500" not in claves


def test_dos_recorridos_sin_solape_suman_sus_longitudes() -> None:
    esp = sin_recorridos(espacio_bano())
    p2 = replace(punto(esp, "P2"), fuente_id="F2")
    esp2 = replace(
        esp,
        fuentes=esp.fuentes + (fuente_f2(),),
        puntos=tuple(p2 if p.id == "P2" else p for p in esp.puntos),
    )
    g = analizar(esp2, Especialidad.AGUA)
    assert cerca(g.longitud_unida, g.longitud_sin_unir)
    assert {s.fuente_id for s in g.segmentos} == {"F1", "F2"}


def test_un_solo_punto_no_forma_tee() -> None:
    esp = sin_recorridos(espacio_bano())
    g = analizar(replace(esp, puntos=(punto(esp, "P1"),)), Especialidad.AGUA)
    assert g.tees == {}
    assert g.codos == {"1/2": 2}
    assert cerca(g.longitud_unida, "5.900")


# --- sobrescrituras ----------------------------------------------------------------------


def test_sobrescritura_de_diametro_y_empotrado_por_clave(memoria: dict) -> None:
    esp = sin_recorridos(espacio_bano())
    clave_s5 = "F1|1.000,0.000,2.500|1.000,1.500,2.500"
    esp2 = replace(
        esp,
        sobrescrituras=(SobrescrituraSegmento(clave=clave_s5, diametro='1"', empotrado=True),),
    )
    g = analizar(esp2, Especialidad.AGUA)
    s5 = next(s for s in g.segmentos if s.clave == clave_s5)
    assert s5.diametro == "1" and s5.empotrado is True
    assert cerca(g.longitud_por_diametro["1"], "1.500")
    assert cerca(g.longitud_por_diametro["3/4"], D("6.300") - D("1.500"))
    assert cerca(g.longitud_empotrada, D(memoria["longitud_empotrada"]) + D("1.500"))


def test_sobrescritura_resuelve_conflicto_de_empotrado() -> None:
    esp = sin_recorridos(espacio_bano())
    # P1 declara su tramo de techo como expuesto y P2 como empotrado: conflicto en S2
    t_exp = Tramo(
        orden=1,
        superficie=SuperficieTramo.TECHO,
        empotrado=False,
        vertices=(c("0", "0", "2.5"), c("1", "0", "2.5")),
    )
    rec = (
        Recorrido(id="R-P1", punto_id="P1", modo=ModoRecorrido.DECLARADO, tramos=(t_exp,)),
        Recorrido(
            id="R-P2",
            punto_id="P2",
            modo=ModoRecorrido.DECLARADO,
            tramos=(replace(t_exp, empotrado=True),),
        ),
    )
    clave = "F1|0.000,0.000,2.500|1.000,0.000,2.500"
    con_conflicto = replace(esp, recorridos=rec)
    s = next(x for x in unir_segmentos(con_conflicto) if x.clave == clave)
    assert s.conflicto_empotrado is True
    resuelto = replace(
        con_conflicto, sobrescrituras=(SobrescrituraSegmento(clave, empotrado=True),)
    )
    s = next(x for x in unir_segmentos(resuelto) if x.clave == clave)
    assert s.conflicto_empotrado is False and s.empotrado is True


def test_sobrescritura_huerfana_cuando_la_clave_desaparece() -> None:
    esp = espacio_bano()  # la sobrescritura del fixture apunta a S1, que existe
    assert sobrescrituras_huerfanas(esp) == ()
    huerfana = SobrescrituraSegmento(clave="F1|9.000,9.000,9.000|9.000,9.000,9.500", diametro='1"')
    esp2 = replace(esp, sobrescrituras=esp.sobrescrituras + (huerfana,))
    assert sobrescrituras_huerfanas(esp2) == (huerfana.clave,)


# --- drenaje -----------------------------------------------------------------------------


def test_drenaje_baja_al_piso_y_recorre_por_el_piso() -> None:
    esp = espacio_bano()
    colector = Fuente(
        id="C1",
        especialidad=Especialidad.AGUA,
        tipo=TipoFuente.COLECTOR_DRENAJE,
        ambiente_id="BAN-01",
        posicion=c("2", "1.5", "0"),
        origen_id="O1",
    )
    p = replace(
        punto(esp, "P1"),
        id="D1",
        tipo=TipoPunto.DRENAJE,
        superficie=SuperficiePunto.PARED,
        posicion=c("0.5", "0.5", "0.4"),
        fuente_id="C1",
    )
    tramos = recorrido_propuesto(replace(esp, fuentes=esp.fuentes + (colector,)), p)
    assert [t.superficie for t in tramos] == [
        SuperficieTramo.PARED,
        SuperficieTramo.PISO,
        SuperficieTramo.PISO,
    ]
    assert [t.vertices for t in tramos] == [
        (c("0.5", "0.5", "0.4"), c("0.5", "0.5", "0")),  # baja al piso
        (c("0.5", "0.5", "0"), c("2", "0.5", "0")),  # en x
        (c("2", "0.5", "0"), c("2", "1.5", "0")),  # luego en y
    ]
    assert cerca(longitud_tramos(tramos), "2.900")


def test_recorrido_propuesto_no_recibe_pendiente() -> None:
    with pytest.raises(TypeError):
        recorrido_propuesto(espacio_bano(), punto(espacio_bano(), "P1"), D("0.02"))  # type: ignore[call-arg]


def test_recorrido_modo_propuesto_con_tramos_se_trata_como_declarado() -> None:
    esp = espacio_bano()
    raro = Tramo(
        orden=1,
        superficie=SuperficieTramo.TECHO,
        vertices=(c("0", "0", "2.5"), c("1", "0", "2.5")),
    )
    r = Recorrido(id="R-P2", punto_id="P2", modo=ModoRecorrido.PROPUESTO, tramos=(raro,))
    esp2 = replace(esp, recorridos=(r,), sobrescrituras=())
    assert tramos_de(esp2, punto(esp2, "P2")) == (raro,)


# --- nodos por vecindad y cortes con una sola tolerancia ----------------------------------


def espacio_rutas(rutas: dict[str, list[tuple[str, str, str]]]) -> Espacio:
    """Espacio con la fuente F1 en (0; 0; 2,5) y un punto por ruta con tramos declarados."""
    base = espacio_bano()
    puntos, recorridos = [], []
    for pid, vertices in rutas.items():
        puntos.append(
            replace(
                punto(base, "P1"),
                id=pid,
                posicion=c(*vertices[-1]),
                especificaciones=(("diametro", '1/2"'),),
            )
        )
        tramo = Tramo(
            orden=1,
            superficie=SuperficieTramo.TECHO,
            empotrado=False,
            vertices=tuple(c(*v) for v in vertices),
        )
        recorridos.append(
            Recorrido(id=f"R-{pid}", punto_id=pid, modo=ModoRecorrido.DECLARADO, tramos=(tramo,))
        )
    fuente = replace(base.fuentes[0], posicion=c("0", "0", "2.5"))
    return replace(
        base,
        fuentes=(fuente,),
        puntos=tuple(puntos),
        recorridos=tuple(recorridos),
        sobrescrituras=(),
    )


def _l(segs) -> list[Decimal]:
    return [s.longitud for s in segs]


def test_nodos_a_menos_de_un_milimetro_en_celdas_distintas_se_unen() -> None:
    esp = espacio_rutas(
        {
            "P1": [("0", "0", "2.5"), ("1.0004", "0", "2.5")],
            "P2": [("0", "0", "2.5"), ("1.0006", "0", "2.5")],
        }
    )
    g = analizar(esp, Especialidad.AGUA)
    assert len(g.segmentos) == 1  # sin segmento fantasma de 0,0002 m
    assert cerca(g.longitud_unida, "1.0005")
    assert g.codos == {} and g.tees == {}


def test_ramas_en_y_desde_nodos_que_se_unen_dan_un_codo_y_ninguna_tee() -> None:
    esp = espacio_rutas(
        {
            "P1": [("0", "0", "2.5"), ("1.0004", "0", "2.5"), ("1.0004", "1", "2.5")],
            "P2": [("0", "0", "2.5"), ("1.0006", "0", "2.5"), ("1.0006", "1", "2.5")],
        }
    )
    g = analizar(esp, Especialidad.AGUA)
    assert len(g.segmentos) == 2
    assert sum(g.codos.values()) == 1 and g.tees == {}


def test_nodos_en_1_00049_y_1_00051_con_ramas_de_1_y_2_m() -> None:
    esp = espacio_rutas(
        {
            "P1": [("0", "0", "2.5"), ("1.00049", "0", "2.5"), ("1.00049", "1", "2.5")],
            "P2": [("0", "0", "2.5"), ("1.00051", "0", "2.5"), ("1.00051", "2", "2.5")],
        }
    )
    g = analizar(esp, Especialidad.AGUA)
    assert len(g.segmentos) == 3  # x, y de 0 a 1 e y de 1 a 2
    assert all(abs(longitud - 1) <= TOL for longitud in _l(g.segmentos))  # sin diagonales
    assert g.tees == {} and sum(g.codos.values()) == 1


def test_una_t_a_0_0009_m_de_la_recta_no_dobla_el_tubo_principal() -> None:
    esp = espacio_rutas(
        {
            "P1": [("0", "0", "2.5"), ("2", "0", "2.5")],
            "P2": [("1", "1", "2.5"), ("1", "0.0009", "2.5")],
        }
    )
    g = analizar(esp, Especialidad.AGUA)
    principales = sorted(s.longitud for s in g.segmentos if s.sirve == ("P1",))
    assert len(g.segmentos) == 3
    assert principales == [D("1"), D("1")]  # exactos: sin diagonales de 1,0000004 m
    assert g.tees == {"1/2": 1} and g.codos == {}


def test_tres_solapes_parciales_colineales() -> None:
    esp = espacio_rutas(
        {
            "P1": [("0", "0", "2.5"), ("2.5", "0", "2.5")],
            "P2": [("1", "0", "2.5"), ("3", "0", "2.5")],
            "P3": [("2", "0", "2.5"), ("4", "0", "2.5")],
        }
    )
    g = analizar(esp, Especialidad.AGUA)
    assert cerca(g.longitud_sin_unir, "6.500")
    assert cerca(g.longitud_unida, "4.000")
    assert g.codos == {} and g.tees == {}


def test_solape_colineal_en_diagonal() -> None:
    esp = espacio_rutas(
        {
            "P1": [("0", "0", "0"), ("3", "4", "0")],
            "P2": [("0", "0", "0"), ("1.5", "2", "0")],
        }
    )
    g = analizar(esp, Especialidad.AGUA)
    assert cerca(g.longitud_sin_unir, "7.500")
    assert cerca(g.longitud_unida, "5.000")
    assert len(g.segmentos) == 2
    assert g.codos == {} and g.tees == {}


def test_t_sin_nodo_previo_parte_el_principal_con_una_tee_y_sin_codo() -> None:
    esp = espacio_rutas(
        {
            "P1": [("0", "0", "2.5"), ("2", "0", "2.5")],
            "P2": [("1", "0", "2.5"), ("1", "1", "2.5")],
        }
    )
    g = analizar(esp, Especialidad.AGUA)
    assert len(g.segmentos) == 3
    assert cerca(g.longitud_unida, "3.000")
    assert g.tees == {"1/2": 1} and g.codos == {}


def test_cruce_en_x_sin_nodo_no_parte_ni_cuenta_tees() -> None:
    esp = espacio_rutas(
        {
            "P1": [("0", "0", "2.5"), ("2", "0", "2.5")],
            "P2": [("1", "-1", "2.5"), ("1", "1", "2.5")],
        }
    )
    g = analizar(esp, Especialidad.AGUA)
    assert len(g.segmentos) == 2
    assert cerca(g.longitud_unida, "4.000")
    assert g.tees == {} and g.codos == {}


# --- indice de nodos: equivalencia con el barrido completo y escala -----------------------


def _rutas_aleatorias(
    semilla: int, n: int, ruido: bool, rango: int = 6
) -> dict[str, list[tuple[str, str, str]]]:
    rng = random.Random(semilla)

    def v(paso: int) -> str:
        valor = D(rng.randint(0, rango)) * D("0.5")
        if ruido and rng.random() < 0.5:
            valor += D(rng.randint(-9, 9)) / D(10000)
        return f"{valor:.5f}"

    rutas = {}
    for i in range(n):
        vertices = [("0", "0", "2.5")]
        x, y = v(0), v(1)
        vertices += [(x, "0", "2.5"), (x, y, "2.5")]
        if rng.random() < 0.5:
            vertices.append((x, y, v(2)))
        rutas[f"Q{i}"] = vertices
    return rutas


def _resumen(esp: Espacio) -> tuple:
    g = analizar(esp, Especialidad.AGUA)
    return (
        [(s.clave, s.longitud, s.sirve, s.diametro, s.empotrado) for s in g.segmentos],
        g.codos,
        g.tees,
        g.longitud_sin_unir,
        g.longitud_unida,
    )


def _agrupar_referencia(coords) -> dict[Coord, Coord]:
    """El agrupamiento de nodos como era antes de la cuadricula hash: barrido completo de pares.

    Single-linkage (distancia <= TOLERANCIA) con la minima lexicografica como representante."""
    unicas = sorted(set(coords), key=lambda k: (k.x, k.y, k.z))
    padre = list(range(len(unicas)))

    def raiz(i: int) -> int:
        while padre[i] != i:
            i = padre[i]
        return i

    for i, a in enumerate(unicas):
        for j in range(i + 1, len(unicas)):
            b = unicas[j]
            if (b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2 <= TOL * TOL:
                ri, rj = raiz(i), raiz(j)
                if ri != rj:
                    padre[max(ri, rj)] = min(ri, rj)
    return {k: unicas[raiz(i)] for i, k in enumerate(unicas)}


def _nube(semilla: int, n: int, paso: str, ancho: int, ruido: bool) -> list[Coord]:
    """`n` coordenadas en una reticula de `paso` m con `ancho` pasos por eje; con `ruido`, algunas
    se desplazan hasta 0,0009 m (a veces dentro de la tolerancia, a veces fuera, y en cadena)."""
    rng = random.Random(semilla)
    pts = []
    for _ in range(n):
        v = [D(rng.randint(0, ancho)) * D(paso) for _ in range(3)]
        if ruido:
            v = [x + D(rng.randint(-9, 9)) / D(10000) if rng.random() < 0.6 else x for x in v]
        pts.append(Coord(*v))
    return pts


@pytest.mark.parametrize("semilla", range(8))
@pytest.mark.parametrize(
    ("paso", "ancho"), [("0.5", 6), ("0.001", 5), ("0.0005", 8), ("1", 1)], ids=str
)
def test_la_cuadricula_hash_agrupa_igual_que_el_barrido_completo(semilla, paso, ancho) -> None:
    nube = _nube(semilla, 150, paso, ancho, ruido=semilla % 2 == 1)
    assert geometria._agrupar_nodos(nube) == _agrupar_referencia(nube)


def test_la_cuadricula_hash_agrupa_igual_cuando_muchos_nodos_comparten_x() -> None:
    nube = [Coord(D("1"), D(i) * D("0.00095"), D("2.5")) for i in range(300)]  # cadena en y
    nube += [Coord(D("1"), D(i) * D("0.01"), D("2.5")) for i in range(300)]
    assert geometria._agrupar_nodos(nube) == _agrupar_referencia(nube)


def test_el_agrupamiento_es_single_linkage_y_el_representante_es_la_minima_lexicografica() -> None:
    """Limite documentado en `_agrupar_nodos`: una hilera de extremos a <= 0,001 m del siguiente
    colapsa en un solo nodo aunque los de las puntas queden a mas de 0,001 m entre si."""
    hilera = [Coord(D("1") + D(i) * D("0.0009"), D("0"), D("0")) for i in range(4)]
    rep = geometria._agrupar_nodos(reversed(hilera))  # el orden de entrada no importa
    assert set(rep.values()) == {hilera[0]}  # un solo grupo, con la minima lexicografica
    assert hilera[0].distancia(hilera[-1]) > TOL  # las puntas estan a mas de la tolerancia
    # a mas de TOLERANCIA de la hilera no se une: vecindad estricta de <= TOLERANCIA
    lejos = Coord(hilera[-1].x + D("0.0011"), D("0"), D("0"))
    assert geometria._agrupar_nodos([*hilera, lejos])[lejos] == lejos


@pytest.fixture
def sin_cache():
    """La union se calcula una vez por `Espacio`: cada prueba parte de una cache vacia."""
    geometria._segmentos_de_fuente.cache_clear()
    yield
    geometria._segmentos_de_fuente.cache_clear()


def _con_referencias(monkeypatch) -> None:
    """Sustituye la cuadricula hash por el barrido completo (agrupar y probar todos los nodos)."""
    monkeypatch.setattr(geometria, "_agrupar_nodos", _agrupar_referencia)
    monkeypatch.setattr(
        geometria._IndiceNodos, "cercanos", lambda self, a, b: list(range(len(self.todos)))
    )


@pytest.mark.parametrize("semilla", range(6))
def test_el_indice_da_lo_mismo_que_el_barrido_completo(monkeypatch, sin_cache, semilla) -> None:
    esp = espacio_rutas(_rutas_aleatorias(semilla, 12, ruido=semilla % 2 == 1))
    indexado = _resumen(esp)
    geometria._segmentos_de_fuente.cache_clear()
    _con_referencias(monkeypatch)
    assert _resumen(esp) == indexado


def test_el_indice_da_lo_mismo_en_el_bano(monkeypatch, sin_cache) -> None:
    esp = espacio_bano()
    indexado = _resumen(esp)
    geometria._segmentos_de_fuente.cache_clear()
    _con_referencias(monkeypatch)
    assert _resumen(esp) == indexado


def test_el_indice_da_lo_mismo_en_el_pasillo(monkeypatch, sin_cache) -> None:
    esp = _pasillo(60)
    indexado = _resumen(esp)
    geometria._segmentos_de_fuente.cache_clear()
    _con_referencias(monkeypatch)
    assert _resumen(esp) == indexado


def test_cercanos_da_los_mismos_nodos_que_probar_todos_en_la_caja() -> None:
    rng = random.Random(3)
    nodos = sorted(
        {Coord(*(D(rng.randint(0, 40)) * D("0.25") for _ in range(3))) for _ in range(400)},
        key=lambda k: (k.x, k.y, k.z),
    )
    indice = geometria._IndiceNodos(nodos)
    for _ in range(60):
        a, b = rng.choice(nodos), rng.choice(nodos)
        t = TOL
        esperados = [
            r
            for r, n in enumerate(nodos)
            if min(a.x, b.x) - t <= n.x <= max(a.x, b.x) + t
            and min(a.y, b.y) - t <= n.y <= max(a.y, b.y) + t
            and min(a.z, b.z) - t <= n.z <= max(a.z, b.z) + t
        ]
        assert sorted(indice.cercanos(a, b)) == esperados


# --- escala (RNF-11) ------------------------------------------------------------------------


def _pasillo(n: int) -> Espacio:
    """`n` puntos cuyos recorridos comparten el tramo en x y el eje en y: todos los nodos con la
    misma x (el peor caso del barrido por x) y tramos nunca partidos en un solo nodo."""
    rutas = {
        f"Q{i}": [("0", "0", "2.5"), ("1", "0", "2.5"), ("1", f"{D(i) * D('0.01'):.2f}", "2.5")]
        for i in range(1, n + 1)
    }
    return espacio_rutas(rutas)


def _con_trazado() -> bool:
    """True si hay un trazador de cobertura o de depuracion: el pure-Python va 2 a 4 veces mas lento
    y un umbral de segundos no mide el algoritmo sino la instrumentacion."""
    if sys.gettrace() is not None:
        return True
    try:
        import coverage
    except ImportError:  # pragma: no cover
        return False
    return coverage.Coverage.current() is not None


sin_trazado = pytest.mark.skipif(
    _con_trazado(),
    reason="la cobertura (--cov, como en la CI) o un depurador ralentizan el pure-Python; el "
    "umbral de RNF-11 se verifica en la corrida sin trazador (uv run pytest -q)",
)


#: Lo que tarda en una maquina de desarrollo sin carga la carga de referencia de `_lentitud()`.
_REFERENCIA_S = 0.19


def _lentitud() -> float:
    """Cuanto mas lenta esta la maquina (o el proceso: heap grande de una suite larga, otros
    procesos) que cuando se fijaron los umbrales: 1 o mas. Mide una carga fija de Decimal y orden
    (el mismo tipo de trabajo que la geometria) y toma la mejor de tres."""
    mejor = float("inf")
    for _ in range(3):
        a, b, acumulado, filas = D("1.234567"), D("0.000123"), D(0), []
        inicio = time.perf_counter()
        for i in range(150_000):
            c = (a - b) * a + b
            acumulado += c
            filas.append((c, i))
        filas.sort()
        mejor = min(mejor, time.perf_counter() - inicio)
    return max(1.0, mejor / _REFERENCIA_S)


def _mediana_de_tres(trabajo) -> float:
    """Mediana de tres corridas, cada una con la cache vacia (si no, la 2.a y la 3.a medirian un
    acierto de cache y no el calculo)."""
    tiempos = []
    for _ in range(3):
        geometria._segmentos_de_fuente.cache_clear()
        inicio = time.perf_counter()
        trabajo()
        tiempos.append(time.perf_counter() - inicio)
    return sorted(tiempos)[1]


def _umbral() -> float:
    """1,5 s en la maquina de referencia, escalado por su lentitud actual: el umbral es relativo.
    Una regresion cuadratica (11 s en el pasillo) lo supera aun con la maquina 5 veces mas lenta."""
    return 1.5 * _lentitud()


def _ciclo(esp: Espacio) -> None:
    """Lo que hace un ciclo de la hoja con el mismo espacio: derivar, R8 y R9."""
    derivar(esp, "agua")
    for regla in reglas_espacio(esp):
        regla.evaluar(None)  # type: ignore[arg-type]


def _cuadricula_500() -> Espacio:
    return espacio_rutas(_rutas_aleatorias(7, 500, ruido=True, rango=80))


@sin_trazado
def test_escala_500_puntos_en_menos_de_un_segundo_y_medio() -> None:
    """`analizar` con 500 puntos (cuadricula): mediana de tres corridas, umbral laxo y relativo
    (1,5 s en la maquina de referencia, escalado por su lentitud actual)."""
    esp = _cuadricula_500()
    segs = []

    def trabajo() -> None:
        segs[:] = analizar(esp, Especialidad.AGUA).segmentos

    umbral = _umbral()
    segundos = _mediana_de_tres(trabajo)
    assert len(segs) > 500
    assert segundos < umbral, f"analizar tardo {segundos:.2f} s (mediana de 3; umbral {umbral:.2f})"


@sin_trazado
@pytest.mark.parametrize("forma", ["cuadricula", "pasillo"])
def test_el_ciclo_derivar_r8_r9_con_500_puntos_cabe_en_un_segundo_y_medio(forma) -> None:
    """RNF-11: derivar + R8 + R9 sobre el mismo espacio, union calculada una sola vez.

    Antes de la correccion: 2,3 s (cuadricula) y 11,6 s (pasillo), por tres uniones y un indice
    cuadratico cuando muchos nodos comparten x."""
    esp = _cuadricula_500() if forma == "cuadricula" else _pasillo(500)
    umbral = _umbral()
    segundos = _mediana_de_tres(lambda: _ciclo(esp))
    assert segundos < umbral, f"{forma}: el ciclo tardo {segundos:.2f} s (umbral {umbral:.2f})"


def test_derivar_r8_y_r9_comparten_una_sola_union(monkeypatch, sin_cache) -> None:
    llamadas = []
    original = geometria._agrupar_nodos
    monkeypatch.setattr(
        geometria, "_agrupar_nodos", lambda coords: llamadas.append(1) or original(coords)
    )
    esp = espacio_bano()  # una sola fuente con recorridos
    _ciclo(esp)
    assert len(llamadas) == 1  # antes: derivar, R8 y R9 la repetian (3)
    _ciclo(esp)  # el mismo Espacio no se recalcula
    assert len(llamadas) == 1


def test_drenaje_por_el_piso_va_empotrado_por_defecto() -> None:
    """D-4 corregida (tarea 1.5): pared y piso se empotran; techo, plafon y bandeja no."""
    esp = espacio_bano()
    colector = Fuente(
        id="C1",
        especialidad=Especialidad.AGUA,
        tipo=TipoFuente.COLECTOR_DRENAJE,
        ambiente_id="BAN-01",
        posicion=c("2", "1.5", "0"),
        origen_id="O1",
    )
    p = replace(
        punto(esp, "P1"),
        id="D1",
        tipo=TipoPunto.DRENAJE,
        superficie=SuperficiePunto.PARED,
        posicion=c("0.5", "0.5", "0.4"),
        fuente_id="C1",
    )
    esp = replace(esp, fuentes=esp.fuentes + (colector,))
    assert [t.empotrado for t in recorrido_propuesto(esp, p)] == [True, True, True]
    sin_declarar = Tramo(
        orden=1,
        superficie=SuperficieTramo.PISO,
        vertices=(c("0.5", "0.5", "0"), c("2", "0.5", "0")),
    )
    declarado = replace(
        esp,
        puntos=esp.puntos + (p,),
        recorridos=esp.recorridos
        + (
            Recorrido(
                id="R-D1", punto_id="D1", modo=ModoRecorrido.DECLARADO, tramos=(sin_declarar,)
            ),
        ),
    )
    (segmento,) = [s for s in analizar(declarado, "agua").segmentos if s.sirve == ("D1",)]
    assert segmento.empotrado is True


def test_d4_vale_por_superficie_declarada_a_cualquier_cota() -> None:
    """El empotrado por defecto depende de la superficie del tramo, no de su cota (pendiente,
    drenaje enterrado): un tramo de piso a z = -0,30 va empotrado y uno de techo, no."""
    esp = espacio_bano()
    colector = Fuente(
        id="C1",
        especialidad=Especialidad.AGUA,
        tipo=TipoFuente.COLECTOR_DRENAJE,
        ambiente_id="BAN-01",
        posicion=c("2", "1.5", "0"),
        origen_id="O1",
    )
    p = replace(
        punto(esp, "P1"),
        id="D1",
        tipo=TipoPunto.DRENAJE,
        superficie=SuperficiePunto.PISO,
        posicion=c("0.5", "0.5", "0"),
        fuente_id="C1",
    )
    esp = replace(esp, fuentes=esp.fuentes + (colector,), puntos=esp.puntos + (p,))
    for superficie, z, esperado in (
        (SuperficieTramo.PISO, "-0.3", True),
        (SuperficieTramo.TECHO, "2.5", False),
    ):
        tramo = Tramo(orden=1, superficie=superficie, vertices=(c("0", "0", z), c("1", "0", z)))
        r = Recorrido(id="R-D1", punto_id="D1", modo=ModoRecorrido.DECLARADO, tramos=(tramo,))
        segmentos = analizar(replace(esp, recorridos=esp.recorridos + (r,)), "agua").segmentos
        (segmento,) = [s for s in segmentos if s.sirve == ("D1",)]
        assert segmento.empotrado is esperado, superficie
        assert segmento.superficie is superficie
