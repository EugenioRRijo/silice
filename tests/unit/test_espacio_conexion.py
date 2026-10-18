"""R17 «Conexion de cada punto» (tarea 1.7, pedido de Eugenio del 2026-10-18).

Oraculo escrito a mano antes del codigo. Ruling de que exige cada punto (por el par
especialidad-tipo que consume una derivacion de `adapters/espacio/especialidades`):

* agua fria y drenaje (especialidad agua) y datos (especialidad datos): **fuente** (`fuente_id`);
  sin ella `recorrido_propuesto` no da camino y no se mide tuberia ni cable;
* tomacorriente e iluminacion (especialidad electricidad): **circuito** (`circuito_id` o estar en
  el `orden` de un circuito); su `fuente_id` no se exige: el conductor va por la cadena del
  circuito desde el tablero;
* cualquier otro par (p. ej. un punto de electricidad con tipo de agua): no lo deriva ninguna
  especialidad y R17 no exige nada.

Cada falta da UN hallazgo ADVERTENCIA (nunca ERROR: el usuario decide si corrige), con
`origen_ids = ("esp_puntos:<id>",)` y una descripcion en lenguaje llano.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from adapters.espacio.conexion import _EXIGE, CODIGO_R17, ConexionDeCadaPunto, reglas_conexion
from adapters.espacio.derivacion import ESPECIALIDADES, derivar
from adapters.espacio.modelo import (
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    ModoRecorrido,
    Punto,
    Recorrido,
    SuperficiePunto,
    TipoFuente,
    TipoPunto,
)
from adapters.espacio.origen import OrigenMedida, TipoOrigen
from core.contracts import Hallazgo, ReglaVerificacion, Severidad
from core.contracts.presupuesto import Presupuesto

D = Decimal
VACIO = Presupuesto(codigo="X", fecha=date(2026, 1, 1), moneda="USD", partidas=())
AMBIENTE = Ambiente("A", "Bano", D("0"), D("0"), D("3"), D("2"), D("2.5"), "LEV")
FUENTES = (
    Fuente("F", Especialidad.AGUA, TipoFuente.ACOMETIDA_AGUA, "A", Coord(D(0), D(0), D(0)), "LEV"),
    Fuente(
        "K", Especialidad.AGUA, TipoFuente.COLECTOR_DRENAJE, "A", Coord(D(0), D(1), D(0)), "LEV"
    ),
    Fuente("RK", Especialidad.DATOS, TipoFuente.RACK, "A", Coord(D(0), D(2), D(1)), "LEV"),
    Fuente(
        "T1", Especialidad.ELECTRICIDAD, TipoFuente.TABLERO, "A", Coord(D(3), D(0), D(1)), "LEV"
    ),
)
C1 = Circuito("C1", "T1", 1, (1, 1, 1), "12 AWG", 6)

AVISO_AGUA = (
    "no tiene fuente: el presupuesto no incluye cómo le llega el agua. Asígnele su acometida "
    "o montante, o déjelo así si es a propósito."
)
AVISO_DRENAJE = (
    "no tiene fuente: el presupuesto no incluye la tubería que lo lleva al colector de drenaje. "
    "Asígnele su colector, o déjelo así si es a propósito."
)
AVISO_DATOS = (
    "no tiene fuente: el presupuesto no incluye el cable que lo une al rack. Asígnele su rack, "
    "o déjelo así si es a propósito."
)
AVISO_ELECTRICIDAD = (
    "no tiene circuito: el presupuesto no incluye el cable que lo alimenta desde el tablero. "
    "Asígnele su circuito, o déjelo así si es a propósito."
)


def punto(id_, nombre, especialidad, tipo, fuente_id=None, circuito_id=None) -> Punto:
    return Punto(
        id=id_,
        nombre=nombre,
        especialidad=especialidad,
        tipo=tipo,
        ambiente_id="A",
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D("1"), D("0"), D("1")),
        origen_id="LEV",
        fuente_id=fuente_id,
        circuito_id=circuito_id,
    )


def espacio(*puntos: Punto, circuitos=(C1,)) -> Espacio:
    return Espacio(ambientes=(AMBIENTE,), fuentes=FUENTES, circuitos=circuitos, puntos=puntos)


def r17(e: Espacio) -> list[Hallazgo]:
    return ConexionDeCadaPunto(e).evaluar(VACIO)


def esperado(id_: str, texto: str) -> Hallazgo:
    return Hallazgo(
        regla="R17",
        severidad=Severidad.ADVERTENCIA,
        descripcion=texto,
        origen_ids=(f"esp_puntos:{id_}",),
    )


# --- agua y datos: fuente ------------------------------------------------------------------------


def test_un_punto_de_agua_fria_sin_fuente_da_exactamente_un_aviso_con_ese_punto():
    e = espacio(punto("P2", "lavamanos", Especialidad.AGUA, TipoPunto.AGUA_FRIA))
    assert r17(e) == [esperado("P2", f"El punto P2 (lavamanos) {AVISO_AGUA}")]


def test_un_punto_de_agua_fria_con_fuente_no_da_aviso():
    e = espacio(punto("P2", "lavamanos", Especialidad.AGUA, TipoPunto.AGUA_FRIA, fuente_id="F"))
    assert r17(e) == []


def test_un_drenaje_sin_fuente_da_un_aviso_y_con_colector_ninguno():
    sin = espacio(punto("P3", "rejilla", Especialidad.AGUA, TipoPunto.DRENAJE))
    con = espacio(punto("P3", "rejilla", Especialidad.AGUA, TipoPunto.DRENAJE, fuente_id="K"))
    assert r17(sin) == [esperado("P3", f"El punto P3 (rejilla) {AVISO_DRENAJE}")]
    assert r17(con) == []


def test_un_punto_de_datos_sin_fuente_da_un_aviso_y_con_rack_ninguno():
    sin = espacio(punto("D1", "datos 1", Especialidad.DATOS, TipoPunto.DATOS))
    con = espacio(punto("D1", "datos 1", Especialidad.DATOS, TipoPunto.DATOS, fuente_id="RK"))
    assert r17(sin) == [esperado("D1", f"El punto D1 (datos 1) {AVISO_DATOS}")]
    assert r17(con) == []


def test_un_circuito_no_reemplaza_la_fuente_de_un_punto_de_agua():
    e = espacio(punto("P2", "lavamanos", Especialidad.AGUA, TipoPunto.AGUA_FRIA, circuito_id="C1"))
    assert r17(e) == [esperado("P2", f"El punto P2 (lavamanos) {AVISO_AGUA}")]


# --- electricidad: circuito ----------------------------------------------------------------------


def test_un_tomacorriente_sin_circuito_da_un_aviso_aunque_tenga_fuente():
    e = espacio(
        punto("E1", "toma 1", Especialidad.ELECTRICIDAD, TipoPunto.TOMACORRIENTE, fuente_id="T1")
    )
    assert r17(e) == [esperado("E1", f"El punto E1 (toma 1) {AVISO_ELECTRICIDAD}")]


def test_una_luminaria_sin_circuito_ni_fuente_da_un_solo_aviso_el_del_circuito():
    e = espacio(punto("E4", "luminaria", Especialidad.ELECTRICIDAD, TipoPunto.ILUMINACION))
    assert r17(e) == [esperado("E4", f"El punto E4 (luminaria) {AVISO_ELECTRICIDAD}")]


def test_un_punto_electrico_con_circuito_no_da_aviso_y_no_se_le_exige_fuente():
    e = espacio(
        punto("E1", "toma 1", Especialidad.ELECTRICIDAD, TipoPunto.TOMACORRIENTE, circuito_id="C1")
    )
    assert r17(e) == []


def test_un_punto_electrico_en_el_orden_de_un_circuito_tiene_circuito():
    c = Circuito("C1", "T1", 1, (1, 1, 1), "12 AWG", 6, orden=("E1",))
    e = espacio(
        punto("E1", "toma 1", Especialidad.ELECTRICIDAD, TipoPunto.TOMACORRIENTE), circuitos=(c,)
    )
    assert r17(e) == []


# --- puntos que no exigen nada, forma y orden ----------------------------------------------------


def test_los_pares_que_ninguna_especialidad_deriva_no_exigen_nada():
    e = espacio(
        punto("X1", "x", Especialidad.ELECTRICIDAD, TipoPunto.AGUA_FRIA),
        punto("X2", "x", Especialidad.AGUA, TipoPunto.TOMACORRIENTE),
        punto("X3", "x", Especialidad.DATOS, TipoPunto.DRENAJE),
        punto("X4", "x", Especialidad.AGUA, TipoPunto.DATOS),
    )
    assert r17(e) == []


def test_el_espacio_vacio_no_da_avisos():
    assert r17(Espacio()) == []


def test_varios_puntos_sin_conexion_dan_un_aviso_cada_uno_en_orden_de_id():
    e = espacio(
        punto("P9", "ducha", Especialidad.AGUA, TipoPunto.AGUA_FRIA),
        punto("E1", "toma 1", Especialidad.ELECTRICIDAD, TipoPunto.TOMACORRIENTE),
        punto("P1", "lavamanos", Especialidad.AGUA, TipoPunto.AGUA_FRIA, fuente_id="F"),
    )
    assert r17(e) == [
        esperado("E1", f"El punto E1 (toma 1) {AVISO_ELECTRICIDAD}"),
        esperado("P9", f"El punto P9 (ducha) {AVISO_AGUA}"),
    ]


def test_sin_nombre_propio_el_aviso_nombra_solo_el_id():
    e = espacio(
        punto("P2", "P2", Especialidad.AGUA, TipoPunto.AGUA_FRIA),
        punto("P3", "   ", Especialidad.AGUA, TipoPunto.AGUA_FRIA),
    )
    assert r17(e) == [
        esperado("P2", f"El punto P2 {AVISO_AGUA}"),
        esperado("P3", f"El punto P3 {AVISO_AGUA}"),
    ]


def test_r17_nunca_es_error():
    e = espacio(
        punto("P1", "a", Especialidad.AGUA, TipoPunto.AGUA_FRIA),
        punto("P2", "b", Especialidad.AGUA, TipoPunto.DRENAJE),
        punto("D1", "c", Especialidad.DATOS, TipoPunto.DATOS),
        punto("E1", "d", Especialidad.ELECTRICIDAD, TipoPunto.TOMACORRIENTE),
    )
    assert {h.severidad for h in r17(e)} == {Severidad.ADVERTENCIA}
    assert len(r17(e)) == 4


def test_reglas_conexion_da_la_regla_r17_ligada_al_espacio_que_recibe():
    e = espacio(punto("P2", "lavamanos", Especialidad.AGUA, TipoPunto.AGUA_FRIA))
    reglas = reglas_conexion(e)
    assert len(reglas) == 1
    (regla,) = reglas
    assert isinstance(regla, ReglaVerificacion)
    assert regla.codigo == CODIGO_R17 == "R17"
    assert regla.nombre == "Conexión de cada punto"
    assert regla.espacio is e
    assert regla.evaluar(VACIO) == r17(e)


# --- coherencia del ruling con lo que derivan las especialidades ---------------------------------

LEV = OrigenMedida(
    id="LEV", tipo=TipoOrigen.LEVANTAMIENTO, referencia={"fecha": "2026-10-01", "responsable": "EP"}
)
_FUENTE_DE = {Especialidad.AGUA: "F", Especialidad.DATOS: "RK", Especialidad.ELECTRICIDAD: "T1"}


def _derivado(especialidad, tipo, *, fuente=True, circuito=True) -> list[tuple]:
    """Todo lo que derivan las tres especialidades de un espacio con UN punto del par."""
    fuente_id = "K" if tipo is TipoPunto.DRENAJE else _FUENTE_DE[especialidad]
    p = replace(
        punto("X", "x", especialidad, tipo),
        fuente_id=fuente_id if fuente else None,
        circuito_id="C1" if circuito else None,
        especificaciones={"diametro": '1/2"'},
    )
    e = Espacio(
        origenes=(LEV,),
        ambientes=(AMBIENTE,),
        fuentes=FUENTES,
        circuitos=(C1,),
        puntos=(p,),
        recorridos=(Recorrido("R-X", ModoRecorrido.PROPUESTO, punto_id="X"),),
    )
    return [
        (i.codigo_partida, i.cantidad, i.origen_id) for s in ESPECIALIDADES for i in derivar(e, s)
    ]


def test_exige_algo_justo_de_los_pares_cuyo_punto_derivan_las_especialidades():
    """Si una especialidad gana un tipo de punto (o deja uno), esta prueba avisa: `_EXIGE` debe
    cambiar con ella."""
    derivados = {
        (e, t)
        for e in Especialidad
        for t in TipoPunto
        if any("esp_puntos:X" in origen for *_, origen in _derivado(e, t))
    }
    assert derivados == set(_EXIGE)


@pytest.mark.parametrize("par", sorted(_EXIGE), ids=lambda par: f"{par[0]}-{par[1]}")
def test_lo_que_r17_exige_es_lo_que_cambia_el_presupuesto(par):
    especialidad, tipo = par
    completo = _derivado(especialidad, tipo)
    if _EXIGE[par][0] == "fuente":
        assert _derivado(especialidad, tipo, fuente=False) != completo
    else:  # circuito: sin el cambia el cable; sin fuente no cambia nada (no se le exige)
        assert _derivado(especialidad, tipo, circuito=False) != completo
        assert _derivado(especialidad, tipo, fuente=False) == completo
