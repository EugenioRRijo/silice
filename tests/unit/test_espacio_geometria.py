"""Geometria de la hoja de metrajes (spec §6.4 y §6.5) contra la memoria a mano del bano de OF-001.

Las cifras salen del bloque JSON de `tests/fixtures/memorias/bano_of001.md`, no se copian aqui.
"""

from __future__ import annotations

import json
import re
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
    segs = unir_segmentos(replace(esp, recorridos=(r,), sobrescrituras=()))
    assert all(s.longitud > 0 for s in segs)
    assert all("P1" not in s.sirve for s in segs)


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
        superficie=SuperficiePunto.PISO,
        posicion=c("0.5", "0.5", "0"),
        fuente_id="C1",
    )
    tramos = recorrido_propuesto(replace(esp, fuentes=esp.fuentes + (colector,)), p)
    assert [t.superficie for t in tramos] == [SuperficieTramo.PISO, SuperficieTramo.PISO]
    assert cerca(longitud_tramos(tramos), "2.500")  # 1,5 en x y 1,0 en y
