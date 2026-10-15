"""SL-E8 sin base: el patrón de cifras del documento canónico no diverge del lector estricto del
paquete, sus fronteras (20 enteros, 28 decimales, sin exponente) y la lectura del vector escrito a
mano (RF-85, RP8-2, RP8-13; spec S3 §6.1).

`core` no puede importar `seguridad` (RP8-2): el patrón vive repetido en
`core/budget/canonico.py` y en `seguridad/json_estricto.py`. Esta prueba vigila que los dos acepten
y rechacen exactamente lo mismo. Oráculo de las cifras: la memoria a mano del docstring de
`tests/fixtures/canonico/ejemplo_v1.py`.
"""

from __future__ import annotations

import copy
import hashlib
from decimal import Decimal

import pytest

from core.budget import canonico
from seguridad import json_estricto
from tests.fixtures.canonico.ejemplo_v1 import BYTES_EJEMPLO_V1, EJEMPLO_V1, HUELLA_EJEMPLO_V1
from tests.fixtures.canonico_minimo import RELLENO

#: Cifras que el patrón ACEPTA: fronteras de 20 enteros y 28 decimales incluidas.
VALIDAS = (
    "0",
    "-0",
    "1",
    "-1.5",
    "836.79750000",
    "9" * 20,
    "-" + "9" * 20,
    "0." + "1" * 28,
    "9" * 20 + "." + "9" * 28,
)

#: Cifras que RECHAZA: una cifra más que la frontera, exponentes, comas, signos y alfabetos
#: distintos de ASCII (`\d` aceptaría los dígitos árabe-índicos).
INVALIDAS = (
    "",
    "9" * 21,
    "0." + "1" * 29,
    "1E+3",
    "1e3",
    "1,5",
    "+1",
    ".5",
    "5.",
    " 1",
    "1 ",
    "NaN",
    "Infinity",
    "--1",
    "١٢",  # ١٢
    "1\n",
)


@pytest.mark.parametrize("texto", VALIDAS)
def test_el_patron_acepta_las_cifras_hasta_la_frontera(texto: str) -> None:
    assert canonico.PATRON_CIFRA.fullmatch(texto)
    assert json_estricto.PATRON_CIFRA.fullmatch(texto)


@pytest.mark.parametrize("texto", INVALIDAS)
def test_el_patron_rechaza_lo_que_pasa_la_frontera_o_no_es_posicional(texto: str) -> None:
    assert not canonico.PATRON_CIFRA.fullmatch(texto)
    assert not json_estricto.PATRON_CIFRA.fullmatch(texto)


def test_los_dos_patrones_son_el_mismo_texto() -> None:
    assert canonico.PATRON_CIFRA.pattern == json_estricto.PATRON_CIFRA.pattern
    assert canonico.PATRON_CIFRA.flags == json_estricto.PATRON_CIFRA.flags


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("1E+3"), "1000"),
        (Decimal("0.00001"), "0.00001"),
        (Decimal("1E-7"), "0.0000001"),
        (Decimal("14.0000"), "14.0000"),
        (Decimal("-2.50"), "-2.50"),
        (None, None),
    ],
)
def test_texto_decimal_es_posicional_y_conserva_los_ceros(valor, esperado) -> None:
    assert canonico.texto_decimal(valor) == esperado


def test_json_canonico_es_compacto_ordenado_y_utf8_sin_escapar() -> None:
    assert canonico.json_canonico({"b": 1, "a": "Ñ", "c": [None, True]}) == (
        '{"a":"Ñ","b":1,"c":[null,true]}'.encode()
    )


def test_huella_es_el_sha256_hexadecimal() -> None:
    assert canonico.huella(b"") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert canonico.huella(b"abc") == hashlib.sha256(b"abc").hexdigest()


def test_el_vector_a_mano_serializado_tiene_su_longitud_y_su_huella() -> None:
    datos = canonico.json_canonico(EJEMPLO_V1)
    assert len(datos) == BYTES_EJEMPLO_V1
    assert canonico.huella(datos) == HUELLA_EJEMPLO_V1


def test_leer_el_vector_a_mano_da_las_cifras_de_la_memoria() -> None:
    leido = canonico.leer(copy.deepcopy(EJEMPLO_V1))
    assert leido.composiciones["MIN-001"] == RELLENO
    renglon = leido.declarados[0]
    assert (
        renglon.materiales,
        renglon.equipos,
        renglon.mano_obra,
        renglon.costo_directo,
        renglon.con_administracion,
        renglon.precio_unitario,
        renglon.total,
    ) == (
        Decimal("14.0000"),
        Decimal("0.8875"),
        Decimal("18.1875"),
        Decimal("33.0750"),
        Decimal("38.036250"),
        Decimal("41.83987500"),
        Decimal("836.79750000"),
    )
    # aritmética aparte: 20 x 41,83987500 = 836,79750000
    assert renglon.cantidad * renglon.precio_unitario == renglon.total


def test_leer_rechaza_lo_que_no_es_un_objeto_ni_un_presupuesto() -> None:
    for objeto in ([], "texto", {}, {"formato": "silice-presupuesto", "version_formato": 0}):
        with pytest.raises(canonico.DocumentoInvalido):
            canonico.leer(objeto)  # type: ignore[arg-type]


def test_leer_rechaza_una_cifra_de_hallazgo_fuera_del_patron() -> None:
    objeto = copy.deepcopy(EJEMPLO_V1)
    objeto["hallazgos"] = [
        {
            "regla": "R1",
            "severidad": 2,
            "descripcion": "x",
            "impacto": "1e2",
            "origen_ids": [],
            "valor_observado": None,
            "valor_esperado": None,
        }
    ]
    with pytest.raises(canonico.DocumentoInvalido, match="patron"):
        canonico.leer(objeto)


def test_contar_filas_no_valida_y_tolera_formas_raras() -> None:
    assert canonico.contar_filas(EJEMPLO_V1) == 1 + 3
    assert canonico.contar_filas({"renglones": [1, 2], "composiciones": [{"lineas": "x"}]}) == 2
    assert canonico.contar_filas({"composiciones": ["no", {"lineas": [1]}]}) == 1
