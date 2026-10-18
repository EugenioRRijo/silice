"""El respaldo de la clave de IA con `seguridad.secretos` REAL (S4 §8.3, RV-13; plan 0.9.0, T13).

Sin almacen de credenciales, la clave se cifra con Argon2id -> AES-GCM y una contrasena propia. Se
ajusto a la interfaz real de `secretos` (bitacora 0.9.0, T13): la contrasena erronea o el respaldo
de otra empresa dan `InvalidTag`, que `asistente.clave` convierte en un mensaje fijo sin traza
(ruta, sesion 1, tarea 1.2); la politica de S3 rechaza una contrasena corta o comun.
"""

from __future__ import annotations

import base64
import json

import pytest

from asistente.clave import NO_ABRE_EL_RESPALDO, ClaveDeIA, ClaveNoRegistrable, es_bucle_local
from seguridad import secretos
from tests.fixtures.asistente_clave import AlmacenFalso

CLAVE = "sk-ant-api03-RESPALDO-1234"
CONTRASENA = "una contrasena larga 1"


def _clave(tmp_path):
    ruta = tmp_path / "ia_clave.cifrada"
    clave = ClaveDeIA(
        almacen=AlmacenFalso(cae=True),
        secretos=secretos,
        ruta_respaldo=ruta,
        es_local=es_bucle_local,
    )
    return clave, ruta


def test_el_respaldo_cifrado_no_trae_la_clave_y_la_contrasena_erronea_da_el_mensaje_fijo(
    tmp_path,
):
    clave, ruta = _clave(tmp_path)
    clave.registrar("EMP", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=CONTRASENA)
    crudo = ruta.read_bytes()
    assert CLAVE.encode() not in crudo
    assert base64.b64encode(CLAVE.encode()) not in crudo  # tampoco en base64 sin cifrar
    datos = json.loads(crudo)
    assert json.loads(datos["kdf"]) == {"alg": "argon2id", "v": 19, "m": 65536, "t": 3, "p": 4}
    assert len(base64.b64decode(datos["sal"])) == 16
    assert len(base64.b64decode(datos["nonce"])) == 12
    # AES-GCM: el cifrado mide lo que la clave mas la etiqueta de 16 bytes
    assert len(base64.b64decode(datos["cifrado"])) == len(CLAVE) + 16
    clave.desactivar()
    with pytest.raises(ClaveNoRegistrable) as error:  # InvalidTag de AES-GCM, convertida
        clave.activar("EMP", "otra contrasena larga 2")
    assert str(error.value) == NO_ABRE_EL_RESPALDO and error.value.__suppress_context__
    assert clave.vigente is None
    with pytest.raises(ClaveNoRegistrable, match=r"^La contraseña no abre"):  # atado a la empresa
        clave.activar("OTRA", CONTRASENA)
    clave.activar("EMP", CONTRASENA)
    assert clave.vigente == CLAVE


@pytest.mark.parametrize(
    "contrasena",
    [
        "a" * 11,  # 11 caracteres: uno menos que el minimo de S3
        "contrasena123",  # 13 caracteres, pero en la lista de comunes
        "x" * 129,  # uno mas que el maximo
    ],
)
def test_la_contrasena_del_respaldo_cumple_la_politica_de_s3(tmp_path, contrasena):
    clave, ruta = _clave(tmp_path)
    with pytest.raises(secretos.ContrasenaRechazada):
        clave.registrar("EMP", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=contrasena)
    assert not ruta.exists() and clave.vigente is None


def test_la_contrasena_de_doce_caracteres_es_el_minimo_admitido(tmp_path):
    clave, ruta = _clave(tmp_path)
    clave.registrar("EMP", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo="b" * 12)
    assert ruta.exists() and clave.vigente == CLAVE


# --- reactivar con el modulo real (ruta, sesion 1, tarea 1.2; revision de seguridad) -----------


def test_reactivar_con_el_modulo_real(tmp_path):
    clave, _ = _clave(tmp_path)
    clave.registrar("EMP", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=CONTRASENA)
    clave.desactivar()
    assert clave.pide_contrasena("EMP")
    with pytest.raises(ClaveNoRegistrable) as error:
        clave.reactivar("EMP", "otra contrasena larga 2", ip_cliente="127.0.0.1")
    assert str(error.value) == NO_ABRE_EL_RESPALDO and clave.vigente is None
    assert "otra contrasena larga 2" not in str(error.value)
    assert clave.reactivar("EMP", CONTRASENA, ip_cliente="127.0.0.1") == "…1234"
    assert clave.vigente == CLAVE and not clave.pide_contrasena("EMP")


KDF_BUENO = json.dumps({"alg": "argon2id", "v": 19, "m": 65536, "t": 3, "p": 4}, sort_keys=True)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("kdf", json.dumps({"alg": "argon2id", "v": 19, "m": 1024, "t": 3, "p": 4})),  # bajo m
        ("kdf", "[1]"),  # JSON que no es un objeto: AttributeError en `de_json`
        ("kdf", "no es json"),
        ("kdf", json.dumps({"alg": "argon2id", "v": 19})),  # faltan m, t y p
        ("sal", base64.b64encode(b"abc").decode()),  # sal corta: HashingError de argon2
        ("nonce", ""),  # nonce vacio: ValueError de AES-GCM
    ],
)
def test_un_respaldo_manipulado_da_el_mensaje_fijo_con_el_modulo_real(tmp_path, campo, valor):
    clave, ruta = _clave(tmp_path)
    clave.registrar("EMP", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=CONTRASENA)
    clave.desactivar()
    datos = json.loads(ruta.read_bytes())
    assert datos["kdf"] == KDF_BUENO
    datos[campo] = valor
    ruta.write_bytes(json.dumps(datos).encode())
    with pytest.raises(ClaveNoRegistrable) as error:
        clave.reactivar("EMP", CONTRASENA, ip_cliente="127.0.0.1")
    assert str(error.value) == NO_ABRE_EL_RESPALDO and clave.vigente is None
