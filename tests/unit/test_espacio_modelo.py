"""Modelo espacial de `adapters/espacio` (spec §6.1 y §6.2): inmutable, Decimal, validado."""

from __future__ import annotations

import dataclasses
from decimal import Decimal as D
from pathlib import Path

import pytest

from adapters.espacio import (
    Ambiente,
    Circuito,
    Coord,
    Especialidad,
    Espacio,
    Fuente,
    ModoRecorrido,
    OrigenMedida,
    Punto,
    Recorrido,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
    Tramo,
)
from tests.fixtures.espacio_bano import espacio_bano


def _ambiente(**cambios):
    datos = {
        "id": "A",
        "nombre": "A",
        "x0": D("0"),
        "y0": D("0"),
        "largo": D("2"),
        "ancho": D("1"),
        "alto": D("2.5"),
        "origen_id": "O1",
    }
    datos.update(cambios)
    return Ambiente(**datos)


def _origen():
    return OrigenMedida(id="O1", tipo=TipoOrigen.SUPUESTO, referencia={"motivo": "m"})


def _punto(**cambios):
    datos = {
        "id": "P",
        "nombre": "p",
        "especialidad": Especialidad.AGUA,
        "tipo": TipoPunto.AGUA_FRIA,
        "ambiente_id": "A",
        "superficie": SuperficiePunto.PARED,
        "posicion": Coord(D("1"), D("0"), D("0.6")),
        "origen_id": "O1",
    }
    datos.update(cambios)
    return Punto(**datos)


def _tramo(orden, superficie, a, b):
    return Tramo(
        orden=orden,
        superficie=superficie,
        vertices=(Coord(*(D(v) for v in a)), Coord(*(D(v) for v in b))),
    )


def test_el_espacio_es_inmutable():
    espacio = espacio_bano()
    with pytest.raises(dataclasses.FrozenInstanceError):
        espacio.ambientes = ()  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        espacio.ambientes[0].alto = D("3")  # type: ignore[misc]


def test_el_espacio_es_hashable_y_comparable_por_valor():
    assert espacio_bano() == espacio_bano()
    assert hash(espacio_bano()) == hash(espacio_bano())


def test_el_espacio_vacio_es_valido():
    espacio = Espacio()
    assert espacio.vacio
    assert espacio.validar() == []


@pytest.mark.parametrize("valor", [1.5, 1, "1.5", None, True])
def test_las_coordenadas_deben_ser_decimal(valor):
    with pytest.raises(TypeError, match="Decimal"):
        Coord(valor, D("0"), D("0"))
    with pytest.raises(TypeError, match="Decimal"):
        Coord(D("0"), D("0"), valor)


def test_las_coordenadas_no_admiten_valores_no_finitos():
    with pytest.raises(ValueError, match="finit"):
        Coord(D("NaN"), D("0"), D("0"))
    with pytest.raises(ValueError, match="finit"):
        Coord(D("Infinity"), D("0"), D("0"))


@pytest.mark.parametrize("campo", ["largo", "ancho", "alto"])
def test_las_dimensiones_del_ambiente_deben_ser_decimal_positivas(campo):
    with pytest.raises(TypeError, match="Decimal"):
        _ambiente(**{campo: 2.0})
    with pytest.raises(ValueError, match="positiv"):
        _ambiente(**{campo: D("0")})
    with pytest.raises(ValueError, match="positiv"):
        _ambiente(**{campo: D("-1")})


def test_el_origen_x0_del_ambiente_debe_ser_decimal():
    with pytest.raises(TypeError, match="Decimal"):
        _ambiente(x0=0)


def test_la_pendiente_del_tramo_debe_ser_decimal():
    vertices = (Coord(D("0"), D("0"), D("0")), Coord(D("1"), D("0"), D("0")))
    with pytest.raises(TypeError, match="Decimal"):
        Tramo(orden=1, superficie=SuperficieTramo.PISO, vertices=vertices, pendiente=0.01)


def test_un_tramo_necesita_al_menos_dos_vertices():
    with pytest.raises(ValueError, match="dos vértices"):
        Tramo(orden=1, superficie=SuperficieTramo.PISO, vertices=(Coord(D("0"), D("0"), D("0")),))


def test_la_longitud_del_tramo_se_calcula_y_no_se_escribe():
    tramo = _tramo(1, SuperficieTramo.PARED, ("0", "0", "0"), ("0", "0", "2.5"))
    assert tramo.longitud == D("2.5")
    diagonal = _tramo(1, SuperficieTramo.PISO, ("0", "0", "0"), ("3", "4", "0"))
    assert diagonal.longitud == D("5")
    with pytest.raises(TypeError):
        Tramo(
            orden=1,
            superficie=SuperficieTramo.PISO,
            vertices=diagonal.vertices,
            longitud=D("1"),  # type: ignore[call-arg]
        )


def test_las_longitudes_de_la_memoria_del_bano():
    espacio = espacio_bano()
    p1 = next(r for r in espacio.recorridos if r.id == "R-P1")
    assert [t.longitud for t in p1.tramos] == [D("2.5"), D("1.5"), D("1.9")]
    assert sum((t.longitud for t in p1.tramos), D(0)) == D("5.9")


def test_un_recorrido_apunta_a_un_punto_o_a_un_circuito_pero_no_a_ambos():
    with pytest.raises(ValueError, match="punto o a un circuito"):
        Recorrido(id="R", modo=ModoRecorrido.PROPUESTO)
    with pytest.raises(ValueError, match="punto o a un circuito"):
        Recorrido(id="R", punto_id="P", circuito_id="C", modo=ModoRecorrido.PROPUESTO)


def test_los_tramos_de_un_recorrido_quedan_ordenados():
    a = _tramo(2, SuperficieTramo.TECHO, ("0", "0", "1"), ("1", "0", "1"))
    b = _tramo(1, SuperficieTramo.PARED, ("0", "0", "0"), ("0", "0", "1"))
    recorrido = Recorrido(id="R", punto_id="P", modo=ModoRecorrido.DECLARADO, tramos=(a, b))
    assert [t.orden for t in recorrido.tramos] == [1, 2]


def test_ids_repetidos_se_rechazan():
    with pytest.raises(ValueError, match="repetid"):
        Espacio(origenes=(_origen(),), ambientes=(_ambiente(), _ambiente()))


def test_referencias_a_filas_inexistentes_se_rechazan():
    with pytest.raises(ValueError, match="origen"):
        Espacio(ambientes=(_ambiente(),))
    with pytest.raises(ValueError, match="ambiente"):
        Espacio(origenes=(_origen(),), puntos=(_punto(),))
    with pytest.raises(ValueError, match="fuente"):
        Espacio(
            origenes=(_origen(),),
            ambientes=(_ambiente(),),
            puntos=(_punto(fuente_id="F9"),),
        )
    with pytest.raises(ValueError, match="punto"):
        Espacio(
            origenes=(_origen(),),
            ambientes=(_ambiente(),),
            recorridos=(Recorrido(id="R", punto_id="X", modo=ModoRecorrido.PROPUESTO),),
        )


def test_un_circuito_cita_puntos_que_existen():
    circuito = Circuito(
        id="C1",
        tablero="T1",
        numero=1,
        conductores=(1, 1, 1),
        calibre="12 AWG",
        puntos_maximos=8,
        orden=("P9",),
    )
    with pytest.raises(ValueError, match="punto"):
        Espacio(origenes=(_origen(),), ambientes=(_ambiente(),), circuitos=(circuito,))


def test_ambiente_sin_puntos_se_informa_en_validar():
    espacio = Espacio(origenes=(_origen(),), ambientes=(_ambiente(),))
    problemas = espacio.validar()
    assert len(problemas) == 1
    assert "A" in problemas[0] and "sin puntos" in problemas[0]


def test_punto_fuera_de_su_ambiente_se_informa_en_validar():
    fuera = _punto(posicion=Coord(D("5"), D("0"), D("0.6")))
    espacio = Espacio(origenes=(_origen(),), ambientes=(_ambiente(),), puntos=(fuera,))
    assert any("fuera" in p and "P" in p for p in espacio.validar())


def test_el_punto_en_el_limite_del_ambiente_es_valido():
    limite = _punto(posicion=Coord(D("2"), D("1"), D("2.5")))
    espacio = Espacio(origenes=(_origen(),), ambientes=(_ambiente(),), puntos=(limite,))
    assert espacio.validar() == []


def test_el_bano_de_la_memoria_valida_limpio():
    assert espacio_bano().validar() == []


def test_fuente_sin_posicion_decimal_se_rechaza():
    with pytest.raises(TypeError):
        Fuente(
            id="F",
            especialidad=Especialidad.AGUA,
            tipo=TipoFuente.MONTANTE_AGUA,
            ambiente_id="A",
            posicion=(0, 0, 0),  # type: ignore[arg-type]
            origen_id="O1",
        )


def test_el_modelo_no_usa_float():
    import adapters.espacio.modelo as modelo

    assert "float(" not in Path(modelo.__file__).read_text(encoding="utf-8")
