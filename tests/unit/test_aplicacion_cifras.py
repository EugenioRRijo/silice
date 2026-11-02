"""El intérprete único de las cifras que teclea la persona (regla de Eugenio, 2026-10-25).

«La coma para decimales y el punto para las decenas y centenas (miles), para que no haya
equivocaciones». Los oráculos están escritos a mano en `tests/fixtures/cifras_escritas.json`, que
también lee la prueba del navegador (`frontend-desktop/src/indicadores/cifraEscrita.test.ts`): las
dos implementaciones de la regla no pueden separarse sin que una de las dos pruebas falle.
"""

from __future__ import annotations

import inspect
import json
from decimal import Decimal
from pathlib import Path

import pytest

from aplicacion import cifras
from aplicacion.cifras import (
    AYUDA_CIFRAS,
    BLANCOS,
    MENSAJE_CIFRA,
    MENSAJE_CIFRA_VACIA,
    CifraInvalida,
    cifra_escrita,
    texto_de_cifra,
)

ORACULO = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "cifras_escritas.json").read_text(encoding="utf-8")
)
MENSAJES = {"vacio": MENSAJE_CIFRA_VACIA, "formato": MENSAJE_CIFRA}


def test_los_mensajes_son_los_del_oraculo_compartido():
    assert ORACULO["mensajes"] == {"vacio": MENSAJE_CIFRA_VACIA, "formato": MENSAJE_CIFRA}
    assert ORACULO["ayuda"] == AYUDA_CIFRAS
    # El mensaje lleva tildes y los dos ejemplos de la regla, en lenguaje llano.
    assert "2,5" in MENSAJE_CIFRA and "1.234,56" in MENSAJE_CIFRA
    assert "número" in MENSAJE_CIFRA_VACIA


@pytest.mark.parametrize(
    ("texto", "valor"), [(c["texto"], c["valor"]) for c in ORACULO["aceptados"]]
)
def test_una_cifra_bien_escrita_se_lee_exacta(texto, valor):
    leido = cifra_escrita(texto)

    assert isinstance(leido, Decimal)
    # `format(..., "f")`: sin exponente y con los decimales que escribio la persona (2,50 -> 2.50).
    assert format(leido, "f") == valor


@pytest.mark.parametrize(
    ("texto", "error"), [(c["texto"], c["error"]) for c in ORACULO["rechazados"]]
)
def test_lo_ambiguo_o_anglosajon_se_rechaza_con_el_mensaje_llano(texto, error):
    with pytest.raises(CifraInvalida) as excinfo:
        cifra_escrita(texto)

    assert str(excinfo.value) == MENSAJES[error]
    # Es un ValueError: las capas que ya traducen ValueError a 422 o a su propio error lo atrapan.
    assert isinstance(excinfo.value, ValueError)


def test_el_mil_con_punto_no_se_lee_como_uno():
    """El defecto que motivó la regla: Componer leía «1.000» como 1 (un precio mil veces menor)."""
    assert cifra_escrita("1.000") == Decimal(1000)
    assert cifra_escrita("1.000,00") == Decimal(1000)


@pytest.mark.parametrize(
    ("valor", "texto"), [(c["valor"], c["texto"]) for c in ORACULO["escritura"]]
)
def test_un_decimal_se_escribe_como_lo_teclearia_la_persona(valor, texto):
    assert texto_de_cifra(Decimal(valor)) == texto


def test_los_blancos_que_se_recortan_son_los_del_oraculo():
    """El mismo conjunto en el servidor y en el navegador (`str.strip()` y `String.trim()` recortan
    conjuntos distintos: «﻿2,5» y «2,5» daban resultados distintos, árbitro ronda 1)."""
    assert BLANCOS == ORACULO["blancos"]


@pytest.mark.parametrize(
    ("valor", "texto"), [(c["valor"], c["texto"]) for c in ORACULO["escritura_no_canonica"]]
)
def test_un_decimal_no_canonico_se_escribe_igual_en_los_dos_lados(valor, texto):
    assert texto_de_cifra(Decimal(valor)) == texto


# Solo el servidor: la API nunca manda exponente; el navegador lo deja como llegó (oráculo).
@pytest.mark.parametrize(
    ("valor", "texto"), [("1E+2", "100"), ("1E+3", "1.000"), ("1E-7", "0,0000001"), ("-0", "0")]
)
def test_la_escritura_nunca_usa_exponente_ni_cero_negativo(valor, texto):
    assert texto_de_cifra(Decimal(valor)) == texto


@pytest.mark.parametrize(
    "valor",
    [c["valor"] for c in ORACULO["escritura"]] + [c["valor"] for c in ORACULO["aceptados"]],
)
def test_ida_y_vuelta_sin_perder_nada(valor):
    """Lo que la API pone en un campo editable y la persona no toca vuelve igual: «3.000» (tres
    con tres decimales) se escribe «3,000» y se vuelve a leer 3.000, nunca 3000."""
    decimal = Decimal(valor)
    assert format(cifra_escrita(texto_de_cifra(decimal)), "f") == format(decimal, "f")


@pytest.mark.parametrize("valor", ["NaN", "Infinity", "-Infinity"])
def test_escribir_algo_que_no_es_un_monto_es_un_error_de_programacion(valor):
    with pytest.raises(ValueError, match="finito"):
        texto_de_cifra(Decimal(valor))


def test_nunca_pasa_por_float():
    assert "float(" not in inspect.getsource(cifras)
