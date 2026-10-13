"""Claves de API y 'solo desde el propio equipo' (RF-88, RNF-16; spec S3 §5.6 y §10; RV-15).

Oráculo de la huella: el SHA-256 del secreto calculado aquí con `hashlib` (S3 §10: «se guarda el
SHA-256 del secreto»), nunca con la función privada del módulo.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta
from pathlib import Path

import pytest

from operacion.red import es_cliente_local
from seguridad import claves_api
from seguridad.modelo import ClaveApi, EventoAcceso
from seguridad.red import es_bucle_local, es_local, red_local_activa
from tests.fixtures.instalacion import AHORA, instalacion

BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # RFC 4648, escrito aquí como literal


def _bytes_de_la_base(carpeta: Path) -> bytes:
    return b"".join(p.read_bytes() for p in sorted(carpeta.glob("instalacion.db*")))


# --- claves de API ---------------------------------------------------------------------------


def test_la_clave_se_muestra_una_vez_y_la_base_guarda_solo_la_huella(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        clave, fila = claves_api.crear(sesion, "plugin de AutoCAD", "admin", AHORA)
        identificador, secreto = clave.split(".")
        assert len(identificador) == 8 and set(identificador) <= set(BASE32)
        assert len(secreto) >= 43  # 32 B aleatorios = 256 bits en base64 url (43 caracteres)
        assert fila.identificador == identificador and fila.nombre == "plugin de AutoCAD"
        assert fila.huella_secreto == hashlib.sha256(secreto.encode()).hexdigest()
        assert fila.huella_secreto != secreto and secreto not in fila.huella_secreto
        assert claves_api.verificar(sesion, clave, AHORA).id == fila.id
        sesion.commit()
    bruto = _bytes_de_la_base(tmp_path)
    assert secreto.encode() not in bruto and clave.encode() not in bruto


def test_el_secreto_no_queda_en_el_registro_de_accesos_ni_en_los_registros(
    tmp_path: Path, caplog
) -> None:
    caplog.set_level(logging.DEBUG)
    with instalacion(tmp_path) as sesion:
        clave, fila = claves_api.crear(sesion, "plugin", "admin", AHORA)
        claves_api.verificar(sesion, clave, AHORA)
        claves_api.revocar(sesion, fila.id, "admin", AHORA)
        secreto = clave.split(".")[1]
        detalles = [e.detalle for e in sesion.query(EventoAcceso).order_by(EventoAcceso.id)]
    assert detalles == [f"creada {fila.identificador}; admin", f"revocada {fila.identificador}"]
    assert all(secreto not in d for d in detalles)
    assert secreto not in caplog.text


def test_dos_claves_tienen_identificador_y_secreto_distintos(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        claves = [claves_api.crear(sesion, f"plugin {i}", "admin", AHORA)[0] for i in range(20)]
        identificadores = {c.split(".")[0] for c in claves}
        secretos = {c.split(".")[1] for c in claves}
        assert len(identificadores) == len(secretos) == 20
        assert sesion.query(ClaveApi).count() == 20


@pytest.mark.parametrize(
    "presentada", [None, "", "sinpunto", "a.b.c", "ABCDEFGH.secreto-equivocado", "ZZZZZZZZ.x"]
)
def test_clave_ausente_mal_formada_o_desconocida_no_vale(tmp_path: Path, presentada) -> None:
    with instalacion(tmp_path) as sesion:
        claves_api.crear(sesion, "plugin", "admin", AHORA)
        assert claves_api.verificar(sesion, presentada, AHORA) is None


def test_el_identificador_bueno_con_otro_secreto_no_vale(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        clave, _ = claves_api.crear(sesion, "plugin", "admin", AHORA)
        otra, _ = claves_api.crear(sesion, "otro plugin", "admin", AHORA)
        identificador, secreto = clave.split(".")
        assert claves_api.verificar(sesion, f"{identificador}.{otra.split('.')[1]}", AHORA) is None
        assert claves_api.verificar(sesion, f"{identificador}.{secreto[:-1]}", AHORA) is None
        assert claves_api.verificar(sesion, f"{identificador}.{secreto}x", AHORA) is None
        assert claves_api.verificar(sesion, f"{identificador}.", AHORA) is None
        assert claves_api.verificar(sesion, f".{secreto}", AHORA) is None
        assert claves_api.verificar(sesion, clave, AHORA) is not None  # la buena, sí


def test_una_clave_revocada_no_vale_y_el_ultimo_uso_se_registra(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        clave, fila = claves_api.crear(sesion, "plugin", "admin", AHORA)
        assert fila.ultimo_uso is None
        claves_api.verificar(sesion, clave, AHORA + timedelta(minutes=5))
        assert fila.ultimo_uso == AHORA + timedelta(minutes=5)
        claves_api.revocar(sesion, fila.id, "admin", AHORA)
        assert claves_api.verificar(sesion, clave, AHORA) is None
        assert sesion.get(ClaveApi, fila.id).revocada
        assert claves_api.etiqueta(fila) == f"api:{fila.identificador}"


def test_el_ultimo_uso_se_renueva_a_partir_del_minuto(tmp_path: Path) -> None:
    """Frontera de RENOVACION_MINIMA: 59 s después no se escribe; 60 s después, sí."""
    with instalacion(tmp_path) as sesion:
        clave, fila = claves_api.crear(sesion, "plugin", "admin", AHORA)
        claves_api.verificar(sesion, clave, AHORA)
        assert fila.ultimo_uso == AHORA
        claves_api.verificar(sesion, clave, AHORA + timedelta(seconds=59))
        assert fila.ultimo_uso == AHORA
        claves_api.verificar(sesion, clave, AHORA + timedelta(seconds=60))
        assert fila.ultimo_uso == AHORA + timedelta(seconds=60)


def test_revocar_una_clave_no_toca_las_demas(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        una, fila_una = claves_api.crear(sesion, "uno", "admin", AHORA)
        otra, _ = claves_api.crear(sesion, "otro", "admin", AHORA)
        claves_api.revocar(sesion, fila_una.id, "admin", AHORA)
        assert claves_api.verificar(sesion, una, AHORA) is None
        assert claves_api.verificar(sesion, otra, AHORA) is not None


def test_revocar_una_clave_que_no_existe(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion, pytest.raises(LookupError, match="No hay una clave"):
        claves_api.revocar(sesion, 999, "admin", AHORA)


@pytest.mark.parametrize("nombre", ["", "  "])
def test_una_clave_necesita_nombre(tmp_path: Path, nombre: str) -> None:
    with instalacion(tmp_path) as sesion:
        with pytest.raises(ValueError, match="nombre"):
            claves_api.crear(sesion, nombre, "admin", AHORA)
        assert sesion.query(ClaveApi).count() == 0


def test_la_cabecera_es_la_del_spec() -> None:
    assert claves_api.CABECERA == "X-Silice-Clave"


# --- el propio equipo (seguridad.red) --------------------------------------------------------


@pytest.mark.parametrize(
    "ip,bucle",
    [
        ("127.0.0.1", True),
        ("127.1.2.3", True),
        ("127.255.255.255", True),  # último de 127.0.0.0/8
        ("128.0.0.1", False),  # primero fuera de 127.0.0.0/8
        ("126.255.255.255", False),
        ("::1", True),
        ("::ffff:127.0.0.1", True),
        ("::ffff:192.168.1.20", False),
        (" 127.0.0.1 ", True),
        ("192.168.1.20", False),
        ("10.0.0.5", False),
        ("0.0.0.0", False),
        ("::", False),
        ("fe80::1%eth0", False),
        ("", False),
        ("no es ip", False),
        (None, False),
    ],
)
def test_solo_el_bucle_local_es_el_propio_equipo(ip, bucle: bool) -> None:
    assert es_bucle_local(ip) is bucle


def test_sin_ip_manda_si_la_red_local_esta_encendida() -> None:
    assert es_local(None, red_local_encendida=False) is True
    assert es_local(None, red_local_encendida=True) is False
    assert es_local("  ", red_local_encendida=False) is True
    assert es_local("  ", red_local_encendida=True) is False
    assert es_local("192.168.1.20", red_local_encendida=False) is False
    assert es_local("127.0.0.1", red_local_encendida=True) is True


@pytest.mark.parametrize(
    "entorno,activa",
    [
        ({}, False),
        ({"SILICE_RED_LOCAL": "1"}, True),
        ({"SILICE_RED_LOCAL": "true"}, False),
        ({"SILICE_RED_LOCAL": "0"}, False),
        ({"SILICE_RED_LOCAL": ""}, False),
        ({"SILICE_RED_LOCAL": " 1"}, False),
    ],
)
def test_la_red_local_esta_apagada_por_defecto(entorno: dict, activa: bool) -> None:
    assert red_local_activa(entorno) is activa


def test_sin_entorno_explicito_lee_las_variables_del_proceso(monkeypatch) -> None:
    monkeypatch.delenv("SILICE_RED_LOCAL", raising=False)
    assert red_local_activa() is False
    monkeypatch.setenv("SILICE_RED_LOCAL", "1")
    assert red_local_activa() is True


# --- el propio equipo con la red local de S5 (operacion.red, RV-15) --------------------------


@pytest.mark.parametrize(
    "ip,direccion,local",
    [
        ("127.0.0.1", "", True),
        ("::1", "", True),
        ("::ffff:127.0.0.1", "", True),
        ("127.0.0.1", "192.168.1.20", True),
        ("192.168.1.20", "192.168.1.20", True),  # la IP de la interfaz elegida es el servidor
        ("::ffff:192.168.1.20", "192.168.1.20", True),
        ("192.168.1.21", "192.168.1.20", False),  # el vecino de al lado
        ("192.168.1.20", "", False),
        ("8.8.8.8", "8.8.8.8", False),  # una dirección pública no se acepta como propia
        ("0.0.0.0", "0.0.0.0", False),
        (None, "192.168.1.20", False),  # sin IP: remota
        ("", "", False),
        ("no es ip", "", False),
    ],
)
def test_es_cliente_local(ip, direccion: str, local: bool) -> None:
    assert es_cliente_local(ip, direccion) is local
