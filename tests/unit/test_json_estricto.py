"""Lector JSON estricto (spec S3 §8.4; RV-16): lo que el lector corriente deja pasar."""

from __future__ import annotations

from decimal import Decimal

import pytest

from seguridad.json_estricto import JsonRechazado, a_decimal, leer_json


def test_un_documento_normal_se_lee() -> None:
    assert leer_json(b'{"a": 1, "b": ["x", {"c": 2.50}]}') == {
        "a": 1,
        "b": ["x", {"c": Decimal("2.50")}],
    }


@pytest.mark.parametrize("constante", ["NaN", "Infinity", "-Infinity"])
def test_nan_e_infinitos_se_rechazan(constante: str) -> None:
    with pytest.raises(JsonRechazado, match="constante no admitida"):
        leer_json(f'{{"x": {constante}}}')


def test_una_clave_duplicada_se_rechaza_aunque_sea_anidada() -> None:
    with pytest.raises(JsonRechazado, match="clave JSON duplicada"):
        leer_json('{"a": 1, "a": 2}')
    with pytest.raises(JsonRechazado, match="clave JSON duplicada"):
        leer_json('{"x": {"k": 1, "k": 1}}')


@pytest.mark.parametrize("cifra", ["1E+999999999", "1e5", "1.5E3", "-1E400"])
def test_una_cifra_con_exponente_no_llega_a_decimal(cifra: str) -> None:
    with pytest.raises(JsonRechazado, match="cifra fuera del patron"):
        leer_json(f'{{"x": {cifra}}}')
    with pytest.raises(JsonRechazado, match="cifra fuera del patron"):
        a_decimal(cifra)


def test_el_patron_admite_veintiocho_decimales_y_rechaza_veintinueve() -> None:
    assert a_decimal("8." + "3" * 28) == Decimal("8." + "3" * 28)
    with pytest.raises(JsonRechazado):
        a_decimal("8." + "3" * 29)
    assert a_decimal("9" * 20) == Decimal("9" * 20)
    with pytest.raises(JsonRechazado):
        a_decimal("9" * 21)


@pytest.mark.parametrize("texto", ["+1", " 1", "1 ", "1,5", ".5", "5.", "0x10", "", "1_0", "١٢"])
def test_formas_que_no_son_una_cifra_estricta(texto: str) -> None:
    with pytest.raises(JsonRechazado):
        a_decimal(texto)


def test_anidamiento_64_pasa_y_65_se_rechaza() -> None:
    assert leer_json("[" * 64 + "]" * 64) is not None
    with pytest.raises(JsonRechazado, match="65|64 niveles"):
        leer_json("[" * 65 + "]" * 65)


def test_un_anidamiento_hostil_no_revienta_la_pila() -> None:
    with pytest.raises(JsonRechazado):
        leer_json("[" * 200_000 + "]" * 200_000)


def test_no_es_utf8_o_no_es_json() -> None:
    with pytest.raises(JsonRechazado):
        leer_json(b"\xff\xfe\x00")
    with pytest.raises(JsonRechazado):
        leer_json(b"{no es json")
    with pytest.raises(JsonRechazado):
        leer_json(b"\xef\xbb\xbf{}")  # con BOM: otro lector lo trataria distinto
