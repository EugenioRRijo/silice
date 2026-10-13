"""La clave de IA de la empresa (S4 §8.3, RNF-18 c, RV-15; plan 0.9.0, tarea 13).

`keyring` con un almacen falso en memoria y `seguridad.secretos` con un doble reversible que sigue
la interfaz REAL (bitacora 0.9.0, T13); la prueba con el modulo real esta en
`tests/integration/test_clave_ia_secretos.py`. Los oraculos son literales: la clave de prueba,
sus cuatro ultimos caracteres escritos a mano y el JSON del respaldo leido campo por campo.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import pytest

from asistente.clave import (
    ASOCIADO,
    SERVICIO,
    ClaveDeIA,
    ClaveNoRegistrable,
    FiltroDeSecretos,
    enmascarar,
    es_bucle_local,
    ultimos_cuatro,
)
from tests.fixtures.asistente_clave import (
    AlmacenFalso,
    AlmacenRoto,
    ContrasenaCorta,
    SecretosFalsos,
)

CLAVE = "sk-ant-api03-CLAVE-DE-PRUEBA-1234"
CONTRASENA = "contrasena larga 1"


def clave_de(
    tmp_path: Path, almacen: AlmacenFalso | None = None, secretos: SecretosFalsos | None = None
) -> tuple[ClaveDeIA, AlmacenFalso, Path]:
    almacen = almacen if almacen is not None else AlmacenFalso()
    ruta = tmp_path / "ia_clave.cifrada"
    clave = ClaveDeIA(
        almacen=almacen,
        secretos=secretos if secretos is not None else SecretosFalsos(),
        ruta_respaldo=ruta,
        es_local=lambda ip: ip in ("127.0.0.1", "::1"),
    )
    return clave, almacen, ruta


# --- registrar ------------------------------------------------------------------------------


def test_registrar_desde_el_propio_equipo_guarda_en_el_almacen_bajo_el_servicio_de_ia(tmp_path):
    clave, almacen, ruta = clave_de(tmp_path)
    assert SERVICIO == "silice-ia"
    assert clave.registrar("EMP-1", CLAVE, ip_cliente="127.0.0.1") == "…1234"
    assert almacen.datos == {("silice-ia", "EMP-1"): CLAVE} and not ruta.exists()
    assert clave.vigente == CLAVE and clave.mostrada() == "…1234"


@pytest.mark.parametrize("ip", ["192.168.1.40", "10.0.0.2", None, ""])
def test_registrar_desde_un_cliente_que_no_es_de_bucle_local_se_rechaza(tmp_path, ip):
    clave, almacen, ruta = clave_de(tmp_path)
    with pytest.raises(ClaveNoRegistrable, match="propio equipo"):
        clave.registrar("EMP-1", CLAVE, ip_cliente=ip)
    assert almacen.datos == {} and clave.vigente is None and not ruta.exists()


@pytest.mark.parametrize("vacia", ["", "   ", "\t\n"])
def test_una_clave_vacia_o_en_blanco_no_se_registra(tmp_path, vacia):
    clave, almacen, _ = clave_de(tmp_path)
    with pytest.raises(ClaveNoRegistrable, match="Escriba la clave"):
        clave.registrar("EMP-1", vacia, ip_cliente="127.0.0.1")
    assert almacen.datos == {} and clave.vigente is None


def test_sin_almacen_exige_contrasena_y_guarda_solo_el_cifrado(tmp_path):
    secretos = SecretosFalsos()
    clave, _, ruta = clave_de(tmp_path, AlmacenFalso(cae=True), secretos)
    with pytest.raises(ClaveNoRegistrable, match="contrasena"):
        clave.registrar("EMP-1", CLAVE, ip_cliente="::1")
    assert not ruta.exists() and clave.vigente is None
    clave.registrar("EMP-1", CLAVE, ip_cliente="::1", contrasena_respaldo=CONTRASENA)
    assert secretos.politica_vista == [CONTRASENA]  # la politica de S3 se aplico
    crudo = ruta.read_bytes()
    assert CLAVE.encode() not in crudo  # nunca en texto plano
    assert set(json.loads(crudo)) == {"kdf", "sal", "nonce", "cifrado"}
    # el cifrado del doble es la clave con XOR 0x5A: se reconstruye aparte para ver el formato
    cifrado = base64.b64decode(json.loads(crudo)["cifrado"])
    assert bytes(b ^ 0x5A for b in cifrado) == CLAVE.encode()
    clave.desactivar()
    assert clave.vigente is None and clave.mostrada() is None
    with pytest.raises(ClaveNoRegistrable, match="contrasena"):
        clave.activar("EMP-1")
    with pytest.raises(ValueError, match="erronea"):
        clave.activar("EMP-1", "otra contrasena larga")
    assert clave.vigente is None
    clave.activar("EMP-1", CONTRASENA)
    assert clave.vigente == CLAVE


def test_el_respaldo_queda_atado_a_la_empresa(tmp_path):
    """El dato asociado es `silice-ia-clave-v1:` + empresa: el respaldo de una no abre otra."""
    clave, _, _ = clave_de(tmp_path, AlmacenFalso(cae=True))
    assert ASOCIADO == "silice-ia-clave-v1:"
    clave.registrar("EMP-1", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=CONTRASENA)
    clave.desactivar()
    with pytest.raises(ValueError, match="erronea"):
        clave.activar("EMP-2", CONTRASENA)


def test_sin_almacen_una_contrasena_corta_se_rechaza_y_no_se_escribe_nada(tmp_path):
    clave, _, ruta = clave_de(tmp_path, AlmacenFalso(cae=True))
    with pytest.raises(ContrasenaCorta):
        clave.registrar("EMP-1", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo="corta")
    assert not ruta.exists() and clave.vigente is None


def test_registrar_con_el_almacen_de_vuelta_borra_el_respaldo_anterior(tmp_path):
    almacen = AlmacenFalso(cae=True)
    clave, _, ruta = clave_de(tmp_path, almacen)
    clave.registrar("EMP-1", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=CONTRASENA)
    assert ruta.exists()
    almacen.cae = False
    clave.registrar("EMP-1", "sk-ant-api03-NUEVA-5678", ip_cliente="127.0.0.1")
    assert not ruta.exists()
    assert almacen.datos == {(SERVICIO, "EMP-1"): "sk-ant-api03-NUEVA-5678"}
    assert clave.mostrada() == "…5678"


def test_un_error_del_almacen_que_no_es_de_keyring_no_se_traga(tmp_path):
    clave, _, ruta = clave_de(tmp_path, AlmacenRoto())
    with pytest.raises(RuntimeError, match="inesperado"):
        clave.registrar("EMP-1", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=CONTRASENA)
    assert clave.vigente is None and not ruta.exists()
    with pytest.raises(RuntimeError, match="inesperado"):
        clave.activar("EMP-1")
    with pytest.raises(RuntimeError, match="inesperado"):
        clave.hay_guardada("EMP-1")


# --- activar, hay_guardada y olvidar ---------------------------------------------------------


def test_activar_desde_el_almacen_y_olvidar_borra_todo(tmp_path):
    clave, almacen, ruta = clave_de(tmp_path)
    almacen.set_password(SERVICIO, "EMP-1", CLAVE)
    clave.activar("EMP-1")
    assert clave.vigente == CLAVE
    clave.olvidar("EMP-1")
    assert clave.vigente is None and almacen.datos == {} and not ruta.exists()
    with pytest.raises(ClaveNoRegistrable, match="No hay una clave"):
        clave.activar("EMP-1")


def test_olvidar_lo_que_no_estaba_o_con_el_almacen_caido_no_falla_y_borra_el_respaldo(tmp_path):
    almacen = AlmacenFalso(cae=True)
    clave, _, ruta = clave_de(tmp_path, almacen)
    clave.registrar("EMP-1", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=CONTRASENA)
    clave.olvidar("EMP-1")  # el almacen cae: KeyringError tolerado
    assert not ruta.exists() and clave.vigente is None
    almacen.cae = False
    clave.olvidar("EMP-1")  # nada guardado: PasswordDeleteError tolerado
    assert almacen.datos == {}


def test_hay_guardada_no_carga_la_clave_en_memoria(tmp_path):
    almacen = AlmacenFalso()
    clave, _, _ = clave_de(tmp_path, almacen)
    assert not clave.hay_guardada("EMP-1")
    almacen.set_password(SERVICIO, "EMP-1", CLAVE)
    assert clave.hay_guardada("EMP-1") and clave.vigente is None
    assert not clave.hay_guardada("EMP-2")
    almacen.cae = True
    assert not clave.hay_guardada("EMP-1")  # almacen caido y sin respaldo: no hay


def test_hay_guardada_con_solo_el_respaldo_cifrado(tmp_path):
    clave, almacen, _ = clave_de(tmp_path, AlmacenFalso(cae=True))
    clave.registrar("EMP-1", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=CONTRASENA)
    clave.desactivar()
    assert clave.hay_guardada("EMP-1") and clave.vigente is None


# --- lo que se muestra y lo que se registra --------------------------------------------------


def test_la_representacion_y_la_pantalla_nunca_muestran_la_clave_completa(tmp_path):
    clave, _, _ = clave_de(tmp_path)
    assert repr(clave) == "ClaveDeIA(activa=False)"
    clave.registrar("EMP-1", CLAVE, ip_cliente="127.0.0.1")
    assert repr(clave) == "ClaveDeIA(activa=True)" and CLAVE not in str(clave)
    assert clave.mostrada() == "…1234"
    assert ultimos_cuatro("sk-ant-abcdef") == "…cdef"


def test_el_filtro_enmascara_la_clave_en_los_registros(caplog):
    caplog.handler.addFilter(FiltroDeSecretos())
    with caplog.at_level(logging.INFO):
        logging.getLogger("prueba").info("llamando con %s al proveedor", CLAVE)
    assert CLAVE not in caplog.text and "sk-ant-…1234" in caplog.text


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("sin clave", "sin clave"),
        (f"a {CLAVE} b", "a sk-ant-…1234 b"),
        # dos claves en el mismo texto: las dos se enmascaran
        (f"{CLAVE},sk-ant-OTRA_9876", "sk-ant-…1234,sk-ant-…9876"),
        # el prefijo solo, sin cuerpo, no es una clave
        ("sk-ant-", "sk-ant-"),
    ],
)
def test_enmascarar(texto, esperado):
    assert enmascarar(texto) == esperado


@pytest.mark.parametrize(
    ("ip", "local"),
    [
        ("127.0.0.1", True),
        ("127.8.8.8", True),
        ("127.255.255.255", True),  # borde superior de 127.0.0.0/8
        ("128.0.0.1", False),  # el siguiente bloque
        ("126.255.255.255", False),
        ("::1", True),
        ("::1%lo", True),
        ("::2", False),
        ("192.168.0.4", False),
        ("10.0.0.1", False),
        ("0.0.0.0", False),
        ("", False),
        (None, False),
        ("no-es-ip", False),
        ("localhost", False),  # un nombre no se resuelve: solo IP
    ],
)
def test_es_bucle_local_acepta_solo_127_y_loopback_v6(ip, local):
    assert es_bucle_local(ip) is local
