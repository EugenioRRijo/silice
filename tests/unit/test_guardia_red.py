"""Guardia de red unica de la suite (maestro §6.3, RV-17; `tests/conftest.py`).

Solo admite conexiones a 127.0.0.1 y ::1. Una conexion afuera falla con un error que lo dice, y
queda registrada: si una prueba se traga el error con `except OSError`, la sesion falla igual al
cerrar. Limite declarado: no vigila los subprocesos ni la resolucion de nombres (`getaddrinfo`).
"""

from __future__ import annotations

import _socket
import socket

import pytest

from tests.conftest import (
    DESTINOS_PERMITIDOS,
    INTENTOS_BLOQUEADOS,
    ConexionSalienteBloqueada,
    destino_permitido,
    veredicto_de_la_guardia,
)


def test_la_guardia_esta_puesta_durante_toda_la_sesion() -> None:
    assert socket.socket.connect is not _socket.socket.connect
    assert socket.socket.connect_ex is not _socket.socket.connect_ex


def test_solo_se_admiten_el_bucle_local_ipv4_e_ipv6() -> None:
    assert DESTINOS_PERMITIDOS == frozenset({"127.0.0.1", "::1", "localhost"})


def test_una_conexion_fuera_del_equipo_falla_con_un_error_claro() -> None:
    antes = len(INTENTOS_BLOQUEADOS)
    try:
        with pytest.raises(
            ConexionSalienteBloqueada, match=r"203\.0\.113\.1.*solo admite 127\.0\.0\.1 y ::1"
        ):
            socket.create_connection(("203.0.113.1", 80), timeout=1)
        assert INTENTOS_BLOQUEADOS[antes:] == ["('203.0.113.1', 80)"]
    finally:
        del INTENTOS_BLOQUEADOS[antes:]


def test_una_conexion_al_bucle_local_pasa() -> None:
    with socket.create_server(("127.0.0.1", 0)) as servidor:
        puerto = servidor.getsockname()[1]
        with socket.create_connection(("127.0.0.1", puerto), timeout=5) as cliente:
            conexion, _ = servidor.accept()
            with conexion:
                cliente.sendall(b"ok")
                assert conexion.recv(2) == b"ok"


def test_un_intento_tragado_queda_registrado_y_falla_la_sesion() -> None:
    antes = len(INTENTOS_BLOQUEADOS)
    try:
        try:
            socket.create_connection(("198.51.100.7", 443), timeout=1)
        except OSError:
            pass  # una prueba descuidada que se traga el error
        assert INTENTOS_BLOQUEADOS[antes:] == ["('198.51.100.7', 443)"]
        mensaje = veredicto_de_la_guardia(INTENTOS_BLOQUEADOS[antes:])
        assert mensaje is not None and "198.51.100.7" in mensaje
    finally:
        del INTENTOS_BLOQUEADOS[antes:]
    assert veredicto_de_la_guardia([]) is None


@pytest.mark.parametrize(
    ("familia", "direccion", "permitido"),
    [
        (socket.AF_INET, ("127.0.0.1", 80), True),
        (socket.AF_INET6, ("::1", 80, 0, 0), True),
        (socket.AF_INET6, ("::1%1", 80, 0, 1), True),
        (socket.AF_INET, ("localhost", 80), True),
        (socket.AF_INET, ("203.0.113.1", 80), False),
        (socket.AF_INET, ("127.0.0.2", 80), False),
        (socket.AF_INET, ("ejemplo.com", 443), False),
        (socket.AF_INET6, ("2001:db8::1", 443, 0, 0), False),
        (socket.AF_INET6, ("fe80::1%eth0", 80, 0, 0), False),
        (socket.AF_INET6, ("::ffff:127.0.0.1", 80, 0, 0), False),
    ],
)
def test_destinos(familia: int, direccion: tuple, permitido: bool) -> None:
    assert destino_permitido(familia, direccion) is permitido
