"""Comparador del borrador con la referencia: emparejamiento, E1-E8, hallazgos (S4 §9.5).

Oraculo: cada caso se resolvio a mano antes del codigo (memoria `tests/fixtures/memorias/
asistente_metricas.md`). La prueba central: la MISMA corrida con los ids renombrados y las filas en
otro orden da exactamente la misma clasificacion (el comparador nunca empareja por id).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from adapters.espacio import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    OrigenMedida,
    Punto,
    SuperficiePunto,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
)
from asistente.experimento.comparador import comparar, evaluar_hallazgos
from asistente.experimento.modelo import Referencia, Sembrado
from core.contracts import Hallazgo, Severidad
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo

D = Decimal
ORIGEN = OrigenMedida(id="O", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "m"})


def ambiente(id_="A", x0="0", y0="0", largo="2.4", ancho="1.5", alto="2.5"):
    return Ambiente(
        id=id_,
        nombre="n",
        x0=D(x0),
        y0=D(y0),
        largo=D(largo),
        ancho=D(ancho),
        alto=D(alto),
        origen_id="O",
    )


def fuente(id_="F", amb="A", x="0", y="0", z="0"):
    return Fuente(
        id=id_,
        especialidad=Especialidad.AGUA,
        tipo=TipoFuente.MONTANTE_AGUA,
        ambiente_id=amb,
        posicion=Coord(D(x), D(y), D(z)),
        origen_id="O",
    )


def punto(id_, x, y="0", z="0.6", amb="A", fuente_id="F"):
    return Punto(
        id=id_,
        nombre="p",
        especialidad=Especialidad.AGUA,
        tipo=TipoPunto.AGUA_FRIA,
        ambiente_id=amb,
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D(x), D(y), D(z)),
        fuente_id=fuente_id,
        origen_id="O",
    )


def espacio(ambientes, fuentes, puntos):
    return Espacio(
        origenes=(ORIGEN,), ambientes=tuple(ambientes), fuentes=tuple(fuentes), puntos=tuple(puntos)
    )


REF = espacio([ambiente()], [fuente()], [punto("P1", "1.5"), punto("P2", "1.0", "1.5", "1.2")])


def tipos(c):
    return sorted((e.tipo, e.clase, e.campo) for e in c.errores)


def test_una_corrida_identica_con_los_ids_renombrados_y_las_filas_en_otro_orden_no_tiene_errores():
    renombrada = espacio(
        [ambiente("AMB-9")],
        [fuente("FUENTE-9", "AMB-9")],
        [
            punto("zz", "1.0", "1.5", "1.2", "AMB-9", "FUENTE-9"),
            punto("aa", "1.5", "0", "0.6", "AMB-9", "FUENTE-9"),
        ],
    )
    c = comparar(Referencia(REF), renombrada, [])
    assert c.errores == ()
    assert c.pares[("punto", "zz")] == "P2" and c.pares[("punto", "aa")] == "P1"
    assert c.pares[("ambiente", "AMB-9")] == "A"


def test_la_clasificacion_no_depende_de_los_ids_ni_del_orden():
    def variante(prefijo, invertir):
        puntos = [
            punto(f"{prefijo}1", "1.55", amb=f"{prefijo}A", fuente_id=f"{prefijo}F"),
            punto(f"{prefijo}2", "1.0", "1.5", "1.2", f"{prefijo}A", f"{prefijo}F"),
        ]
        return espacio(
            [ambiente(f"{prefijo}A")],
            [fuente(f"{prefijo}F", f"{prefijo}A")],
            puntos[::-1] if invertir else puntos,
        )

    a = comparar(Referencia(REF), variante("X", False), [])
    b = comparar(Referencia(REF), variante("Y", True), [])
    assert tipos(a) == tipos(b) == [("E3", "punto", "x")]


@pytest.mark.parametrize(
    ("desplazamiento", "esperado"),
    [
        ("0.10", [("E3", "punto", "x")]),  # frontera: 0,10 m aun empareja
        ("0.11", [("E6", "punto", ""), ("E7", "punto", "")]),  # 0,11 m: omitido + sobrante (RS4-12)
        ("0.001", []),  # dentro de la tolerancia de medida
        ("0.002", [("E3", "punto", "x")]),
    ],
)
def test_frontera_del_emparejamiento_y_de_la_tolerancia_de_medida(desplazamiento, esperado):
    x = D("1.5") + D(desplazamiento)
    b = espacio([ambiente()], [fuente()], [punto("Q1", str(x)), punto("Q2", "1.0", "1.5", "1.2")])
    assert tipos(comparar(Referencia(REF), b, [])) == esperado


@pytest.mark.parametrize("orden", [False, True])
def test_empate_de_distancias_se_resuelve_por_coordenadas_nunca_por_id(orden):
    ref = espacio([ambiente()], [fuente()], [punto("P1", "1.0"), punto("P2", "1.1")])
    if orden:
        ref = replace(ref, puntos=tuple(reversed(ref.puntos)))
    b = espacio([ambiente()], [fuente()], [punto("ZZZ", "1.05")])  # a 0,05 de P1 y de P2
    c = comparar(Referencia(ref), b, [])
    assert c.pares[("punto", "ZZZ")] == "P1"  # coordenada menor primero
    assert tipos(c) == [("E3", "punto", "x"), ("E6", "punto", "")]


def test_un_segundo_punto_a_menos_de_una_milesima_es_duplicado_e7():
    b = espacio(
        [ambiente()],
        [fuente()],
        [punto("a", "1.5"), punto("b", "1.5"), punto("c", "1.0", "1.5", "1.2")],
    )
    assert tipos(comparar(Referencia(REF), b, [])) == [("E7", "punto", "")]


def test_e4_ambiente_equivocado_y_e5_fuente_equivocada():
    ref = espacio(
        [ambiente("A"), ambiente("B", x0="5")],
        [fuente("F"), fuente("G", "B", "5")],
        [punto("P1", "1.5")],
    )
    mal = espacio(
        [ambiente("a"), ambiente("b", x0="5")],
        [fuente("f", "a"), fuente("g", "b", "5")],
        [punto("p", "1.5", amb="b", fuente_id="g")],
    )
    assert tipos(comparar(Referencia(ref), mal, [])) == [
        ("E4", "punto", "ambiente_id"),
        ("E5", "punto", "fuente_id"),
    ]


def test_un_punto_fuera_de_todo_ambiente_es_e4():
    ref = espacio([ambiente()], [fuente()], [punto("P1", "2.4")])
    b = espacio([ambiente()], [fuente()], [punto("p", "2.45")])  # 0,05: empareja, fuera del muro
    assert tipos(comparar(Referencia(ref), b, [])) == [
        ("E3", "punto", "x"),
        ("E4", "punto", "fuera"),
    ]


def test_posicion_libre_traslada_el_borrador_y_lo_registra():
    b = espacio(
        [ambiente(x0="10", y0="20")],
        [fuente(x="10", y="20")],
        [punto("p", "11.5", "20"), punto("q", "11", "21.5", "1.2")],
    )
    sin = comparar(Referencia(REF), b, [])
    con = comparar(Referencia(REF, posicion_libre=True), b, [])
    assert len(sin.errores) > 0
    assert con.errores == () and con.traslacion == (D("-10"), D("-20"))


def partida(origen, codigo="AF-SALIDA", unidad="punto", cantidad="2"):
    return ItemComputo(codigo, "d", unidad, D(cantidad), origen, OrigenTipo.MANUAL, Dominio.CIVIL)


def test_partidas_codigo_unidad_cantidad_omitida_y_sobrante():
    ref = Referencia(REF, items=(partida("r1"), partida("r2", "EL-1", "pieza", "1")))
    mismo = [partida("ia:1:P1"), partida("ia:1:P2", "EL-1", "pieza", "1")]
    assert comparar(ref, REF, mismo).errores == ()
    cambio = [partida("x1", "OTRA", "punto", "2"), partida("x2", "EL-1", "m", "1")]
    c = comparar(ref, REF, cambio)
    assert tipos(c) == [("E1", "partida", ""), ("E2", "partida", "")]  # unidad compatible / no
    omitida = comparar(ref, REF, [partida("x1")])
    assert tipos(omitida) == [("E6", "partida", "")]
    cantidad = comparar(ref, REF, [partida("x1", cantidad="3"), mismo[1]])
    assert tipos(cantidad) == [("E3", "partida", "cantidad")]


# --- E8: el valor sembrado que queda en el borrador ---------------------------------------------

SEMBRADO = Sembrado("punto", "P1", "x", D("3.00"))


@pytest.mark.parametrize(
    ("x", "esperado"),
    [
        ("3.00", [("E8", "punto", "x")]),  # el sembrado quedo: E8, no E3
        ("1.5", []),  # lo corrigio
        ("2.0", [("E6", "punto", ""), ("E7", "punto", "")]),  # otro valor lejano: paso 4 y 5
    ],
)
def test_e8_es_el_valor_sembrado_que_queda_en_el_borrador(x, esperado):
    b = espacio([ambiente()], [fuente()], [punto("p", x), punto("q", "1.0", "1.5", "1.2")])
    assert tipos(comparar(Referencia(REF, sembrados=(SEMBRADO,)), b, [])) == esperado


def test_e8_si_el_elemento_no_aparece_es_e6_y_lo_que_diga_el_texto_no_cuenta():
    b = espacio([ambiente()], [fuente()], [punto("q", "1.0", "1.5", "1.2")])
    assert tipos(comparar(Referencia(REF, sembrados=(SEMBRADO,)), b, [])) == [("E6", "punto", "")]


# --- hallazgos esperados por construccion, detecciones y falsas alarmas --------------------------


def hallazgo(regla, severidad, *claves):
    return Hallazgo(regla, severidad, "texto con ids del modelo", origen_ids=tuple(claves))


def test_deteccion_falsa_alarma_y_esperados_por_construccion():
    ref_h = [
        hallazgo("R8", Severidad.ADVERTENCIA, "esp_ambientes:A"),
        hallazgo("R8", Severidad.ADVERTENCIA, "esp_ambientes:A"),
    ]
    b = espacio(
        [ambiente("AMB")],
        [fuente("FF", "AMB")],
        [
            punto("q1", "1.55", amb="AMB", fuente_id="FF"),
            punto("q2", "1.0", "1.5", "1.2", "AMB", "FF"),
        ],
    )
    c = comparar(Referencia(REF), b, [])  # un solo error: E3 en el punto q1
    assert [(e.tipo, e.clave_borrador) for e in c.errores] == [("E3", "esp_puntos:q1")]
    hallazgos = [
        hallazgo("R8", Severidad.ADVERTENCIA, "esp_ambientes:AMB"),  # esperado (1 de 2)
        hallazgo("R8", Severidad.ADVERTENCIA, "esp_ambientes:AMB"),  # esperado (2 de 2)
        hallazgo("R8", Severidad.ADVERTENCIA, "esp_ambientes:AMB"),  # un tercero: NO esperado
        hallazgo("R9", Severidad.ERROR, "esp_puntos:q1"),  # cita la fila con error
        hallazgo("R10", Severidad.ADVERTENCIA, "esp_puntos:q2"),  # fila limpia: falsa alarma
    ]
    v = evaluar_hallazgos(c, hallazgos, ref_h)
    assert (len(v.detectados), len(v.escapan)) == (1, 0)
    assert (v.inesperados, v.falsas_alarmas) == (3, 2)


def test_un_error_sin_fila_o_sin_hallazgo_escapa():
    b = espacio([ambiente()], [fuente()], [punto("q", "1.0", "1.5", "1.2")])  # falta P1: E6
    c = comparar(Referencia(REF), b, [])
    v = evaluar_hallazgos(c, [], [])
    assert [e.tipo for e in v.escapan] == ["E6"] and v.detectados == ()
