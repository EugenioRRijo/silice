"""Tramos y cantidades viales (plan vial, Tarea 7): `adapters/vial/modelo.py` y `derivacion.py`.

Oraculos calculados a mano y escritos como literales (nunca con la formula del codigo):

- area del tramo T1: 1 km = 1000 m; 1000 x 7,3 = 7300 m2
- carpeta: 7300 x 0,05 = 365 m3; 365 x 2,35 = 857,75 t
- base granular: 7300 x 0,20 = 1460 m3
- riego de adherencia: 7300 m2; 7300 x 0,5 = 3650 l
- demarcacion continua: 1000 m x 2 lineas = 2000 m; su pintura, 2000 x 0,0365 = 73 l
- transporte de la mezcla: 857,75 t x 12 km = 10293 t.km
"""

from __future__ import annotations

import re
import time
from decimal import Decimal

import pytest

from adapters.vial.constantes import (
    FRACCION_PINTADA_DISCONTINUA,
    FUENTE_CODIGOS_VIALES,
    PARTIDAS_VIALES,
    PINTURA_POR_DEFECTO_L_KM,
    SUPUESTO_DECLARADO,
)
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import TIPOS_CAPA, Capa, Demarcacion, Tramo
from core.contracts import Dominio, ItemComputo, OrigenTipo

TRAMO = Tramo(
    "T1",
    Decimal("0"),
    Decimal("1"),
    Decimal("7.3"),
    (
        Capa("carpeta", Decimal("0.05"), Decimal("2.35"), None),
        Capa("base_granular", Decimal("0.20"), None, None),
        Capa("riego_adherencia", None, None, Decimal("0.5")),
    ),
    (Demarcacion("continua", 2),),
    Decimal("12"),
)


def _codigo(clave: str) -> str:
    return PARTIDAS_VIALES[clave][0]


def _uno(items: list[ItemComputo], clave: str) -> ItemComputo:
    encontrados = [i for i in items if i.codigo_partida == _codigo(clave)]
    assert len(encontrados) == 1, f"{clave}: {encontrados}"
    return encontrados[0]


def test_carpeta_en_m2_y_toneladas():  # 1000 x 7,3 = 7300 m2; x 0,05 x 2,35 = 857,75 t
    items = derivar_tramos([TRAMO])
    area = _uno(items, "carpeta")
    masa = _uno(items, "carpeta_mezcla")
    assert (area.cantidad, area.unidad) == (Decimal("7300"), "m2")
    assert (masa.cantidad, masa.unidad) == (Decimal("857.75"), "t")
    assert masa.regla == "longitud*ancho*espesor*densidad"
    assert dict(masa.parametros) == {
        "longitud": Decimal("1000"),
        "ancho": Decimal("7.3"),
        "espesor": Decimal("0.05"),
        "densidad": Decimal("2.35"),
    }


def test_base_en_m3():  # 7300 x 0,20 = 1460 m3
    base = _uno(derivar_tramos([TRAMO]), "base_granular")
    assert (base.cantidad, base.unidad) == (Decimal("1460"), "m3")
    assert base.regla == "longitud*ancho*espesor"


def test_riego_en_m2_y_litros():  # 7300 m2; 3650 l
    items = derivar_tramos([TRAMO])
    area = _uno(items, "riego_adherencia")
    litros = _uno(items, "riego_adherencia_ligante")
    assert (area.cantidad, area.unidad) == (Decimal("7300"), "m2")
    assert (litros.cantidad, litros.unidad) == (Decimal("3650"), "l")
    assert litros.regla == "longitud*ancho*dosis"


def test_demarcacion_continua_en_m():  # 2000 m
    linea = _uno(derivar_tramos([TRAMO]), "demarcacion_continua")
    assert (linea.cantidad, linea.unidad) == (Decimal("2000"), "m")
    assert linea.origen_id == "tramo:T1:demarcacion:1"


def test_demarcacion_discontinua_usa_la_fraccion_declarada():
    # 1000 m x 1 linea x 0,375 (3 m pintados de cada 8 m, supuesto declarado) = 375 m
    tramo = Tramo(
        "D1",
        Decimal("0"),
        Decimal("1"),
        Decimal("7.3"),
        (Capa("carpeta", Decimal("0.05"), Decimal("2.35"), None),),
        (Demarcacion("discontinua", 1),),
    )
    linea = _uno(derivar_tramos([tramo]), "demarcacion_discontinua")
    assert linea.cantidad == Decimal("375")
    assert linea.regla == "longitud*lineas*fraccion_pintada"
    assert FRACCION_PINTADA_DISCONTINUA.fuente == SUPUESTO_DECLARADO
    assert "supuesto declarado" in linea.descripcion


# --- Tarea 16b (filas 51 y 63): la pintura de cada linea, en litros -------------------------------
# Rendimiento por defecto 36,5 l por km de linea de 10 cm (punto medio de 29 y 44, V-11 y V-12, a
# cotejar), es decir 0,0365 l por m; sin ancho en la linea, 10 cm (V-14).


def test_cada_linea_continua_da_su_pintura_en_litros():  # 2000 m x 0,0365 = 73 l
    pintura = _uno(derivar_tramos([TRAMO]), "pintura_demarcacion")
    assert (pintura.codigo_partida, pintura.unidad) == ("C-000.000.015", "l")
    assert pintura.cantidad == Decimal("73")
    assert pintura.origen_id == "tramo:T1:demarcacion:1"
    assert pintura.regla == "longitud*lineas*pintura_l_m"
    assert dict(pintura.parametros) == {
        "longitud": Decimal("1000"),
        "lineas": Decimal("2"),
        "pintura_l_m": Decimal("0.0365"),
    }
    assert dict(pintura.especificaciones) == {
        "_especialidad": "vial",
        "_demarcacion": "continua",
        "_ancho_linea_cm": "10",
    }


def test_la_discontinua_pinta_solo_su_fraccion():  # 1000 x 1 x 0,375 x 0,0365 = 13,6875 l
    tramo = Tramo(
        "D1",
        Decimal("0"),
        Decimal("1"),
        Decimal("7.3"),
        (),
        (Demarcacion("discontinua", 1),),
    )
    pintura = _uno(derivar_tramos([tramo]), "pintura_demarcacion")
    assert pintura.cantidad == Decimal("13.6875")
    assert pintura.regla == "longitud*lineas*fraccion_pintada*pintura_l_m"


def test_la_partida_y_el_rendimiento_de_la_pintura_tienen_fuente():
    assert PARTIDAS_VIALES["pintura_demarcacion"] == (
        "C-000.000.015",
        "Pintura de demarcación",
        "l",
    )
    assert PINTURA_POR_DEFECTO_L_KM.valor == Decimal("36.5")
    assert "a cotejar" in PINTURA_POR_DEFECTO_L_KM.fuente


def test_transporte_t_km():  # 857,75 x 12 = 10293 t.km
    transporte = _uno(derivar_tramos([TRAMO]), "transporte_mezcla")
    assert (transporte.cantidad, transporte.unidad) == (Decimal("10293"), "t·km")
    assert transporte.origen_id == "tramo:T1:capa:1"


def test_sin_distancia_no_hay_transporte():
    tramo = Tramo(
        "T9",
        Decimal("0"),
        Decimal("1"),
        Decimal("7.3"),
        (Capa("carpeta", Decimal("0.05"), Decimal("2.35"), None),),
    )
    codigos = {i.codigo_partida for i in derivar_tramos([tramo])}
    assert _codigo("transporte_mezcla") not in codigos


def test_origen_y_especialidad():  # origen_id "tramo:T1:capa:1", especialidad "vial"
    items = derivar_tramos([TRAMO])
    carpeta = _uno(items, "carpeta")
    assert carpeta.origen_id == "tramo:T1:capa:1"
    assert carpeta.origen_tipo is OrigenTipo.REGLA
    assert carpeta.dominio is Dominio.CIVIL
    # Directivas DA-SF-3 (claves con «_»): clasifican sin que R4 las contraste con el APU.
    assert dict(carpeta.especificaciones) == {"_especialidad": "vial", "_capa": "carpeta"}
    assert dict(_uno(items, "demarcacion_continua").especificaciones) == {
        "_especialidad": "vial",
        "_demarcacion": "continua",
    }
    assert _uno(items, "base_granular").origen_id == "tramo:T1:capa:2"
    assert _uno(items, "riego_adherencia").origen_id == "tramo:T1:capa:3"
    assert all(i.especificaciones["_especialidad"] == "vial" for i in items)
    assert all(i.dominio is Dominio.CIVIL for i in items)


def test_orden_determinista():
    """Mismo tramo, mismos items en el mismo orden: capas en su orden, luego la demarcacion."""
    items = derivar_tramos([TRAMO])
    assert [(i.codigo_partida, i.origen_id) for i in items] == [
        (_codigo("carpeta"), "tramo:T1:capa:1"),
        (_codigo("carpeta_mezcla"), "tramo:T1:capa:1"),
        (_codigo("transporte_mezcla"), "tramo:T1:capa:1"),
        (_codigo("base_granular"), "tramo:T1:capa:2"),
        (_codigo("riego_adherencia"), "tramo:T1:capa:3"),
        (_codigo("riego_adherencia_ligante"), "tramo:T1:capa:3"),
        (_codigo("demarcacion_continua"), "tramo:T1:demarcacion:1"),
        (_codigo("pintura_demarcacion"), "tramo:T1:demarcacion:1"),
    ]
    assert derivar_tramos([TRAMO]) == items


def test_progresiva_invertida():  # Tramo("T2", 2, 1, ...) -> ValueError("T2")
    with pytest.raises(ValueError, match="T2"):
        Tramo("T2", Decimal("2"), Decimal("1"), Decimal("7.3"), ())


def test_progresiva_igual_tambien_se_rechaza():
    with pytest.raises(ValueError, match="T3"):
        Tramo("T3", Decimal("1"), Decimal("1"), Decimal("7.3"), ())


def test_id_con_dos_puntos_se_rechaza():
    """«:» separa las partes de `origen_id` («tramo:<id>:capa:<n>»): un id con «:» lo haria
    ambiguo («tramo:A:capa:1:capa:2»)."""
    with pytest.raises(ValueError, match="A:capa"):
        Tramo("A:capa", Decimal("0"), Decimal("1"), Decimal("7.3"), ())


@pytest.mark.parametrize(("ini", "fin"), [("-1", "1"), ("-2", "-1")])
def test_progresiva_negativa_se_rechaza(ini, fin):
    with pytest.raises(ValueError, match=r"N1.*negativa"):
        Tramo("N1", Decimal(ini), Decimal(fin), Decimal("7.3"), ())


def test_longitud_en_metros():
    assert TRAMO.longitud_m == Decimal("1000")
    tramo = Tramo("T4", Decimal("1.2"), Decimal("2.05"), Decimal("6"), ())
    assert tramo.longitud_m == Decimal("850")


@pytest.mark.parametrize(
    ("capa", "falta"),
    [
        (("carpeta", Decimal("0.05"), None, None), "densidad"),
        (("carpeta", None, Decimal("2.35"), None), "espesor"),
        (("base_granular", None, None, None), "espesor"),
        (("riego_adherencia", None, None, None), "dosis"),
        (("imprimacion", Decimal("0.05"), None, Decimal("1")), "espesor"),
        (("base_granular", Decimal("0.2"), Decimal("2.2"), None), "densidad"),
    ],
)
def test_capa_con_datos_que_su_tipo_no_admite(capa, falta):
    """Lo que falta o sobra para el tipo se rechaza nombrando el dato: nada se adivina."""
    with pytest.raises(ValueError, match=falta):
        Capa(*capa)


def test_capa_desconocida_y_valores_no_positivos():
    with pytest.raises(ValueError, match="asfalto"):
        Capa("asfalto", Decimal("0.05"), Decimal("2.35"), None)
    with pytest.raises(ValueError, match="espesor"):
        Capa("base_granular", Decimal("0"), None, None)
    with pytest.raises(ValueError, match="ancho"):
        Tramo("T5", Decimal("0"), Decimal("1"), Decimal("-7"), ())
    with pytest.raises(ValueError, match="lineas"):
        Demarcacion("continua", 0)
    with pytest.raises(ValueError, match="punteada"):
        Demarcacion("punteada", 1)


def test_tipos_de_capa():
    assert TIPOS_CAPA == (
        "fresado",
        "base_granular",
        "subbase_granular",
        "imprimacion",
        "riego_adherencia",
        "carpeta",
        "bacheo",
    )


def test_codigos_con_la_forma_de_la_norma_y_fuente_a_cotejar():
    assert PARTIDAS_VIALES
    for clave, (codigo, descripcion, unidad) in PARTIDAS_VIALES.items():
        assert re.fullmatch(r"C-\d{3}\.\d{3}\.\d{3}", codigo), clave
        assert descripcion.strip() and unidad.strip(), clave
    codigos = [codigo for codigo, _, _ in PARTIDAS_VIALES.values()]
    assert len(set(codigos)) == len(codigos)
    assert FUENTE_CODIGOS_VIALES.fuente == (
        "COVENIN 2000-1:1987, Parte I Carreteras: código a cotejar con el texto de la norma"
    )


def test_rendimiento_quinientos_tramos():
    """RNF-11 (adaptado): 500 tramos con tres capas y demarcacion se derivan en menos de 2 s."""
    tramos = [
        Tramo(
            f"R{n}",
            Decimal(n),
            Decimal(n + 1),
            Decimal("7.3"),
            TRAMO.capas,
            TRAMO.demarcacion,
            Decimal("12"),
        )
        for n in range(500)
    ]
    inicio = time.perf_counter()
    items = derivar_tramos(tramos)
    assert time.perf_counter() - inicio < 2
    assert len(items) == 500 * 8
