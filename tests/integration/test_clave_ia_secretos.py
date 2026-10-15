"""El respaldo de la clave de IA con `seguridad.secretos` REAL (S4 §8.3, RV-13; plan 0.9.0, T13).

Sin almacen de credenciales, la clave se cifra con Argon2id -> AES-GCM y una contrasena propia. Se
ajusto a la interfaz real de `secretos` (bitacora 0.9.0, T13): la contrasena erronea o el respaldo
de otra empresa dan `InvalidTag`; la politica de S3 rechaza una contrasena corta o comun.
"""

from __future__ import annotations

import base64
import json

import pytest
from cryptography.exceptions import InvalidTag

from asistente.clave import ClaveDeIA, es_bucle_local
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


def test_el_respaldo_cifrado_no_trae_la_clave_y_la_contrasena_erronea_da_invalidtag(tmp_path):
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
    with pytest.raises(InvalidTag):
        clave.activar("EMP", "otra contrasena larga 2")
    assert clave.vigente is None
    with pytest.raises(InvalidTag):  # el dato asociado ata el respaldo a la empresa
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
