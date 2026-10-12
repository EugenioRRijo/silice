"""Fichas de sesión: expiración exacta, roles leídos de la base e invalidaciones (RF-81)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from seguridad import cuentas, sesiones
from seguridad.modelo import Sesion
from seguridad.permisos import Rol
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, instalacion, persona


@pytest.fixture
def abierta(tmp_path: Path):
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        ficha = sesiones.abrir(sesion, luis, AHORA)
        yield sesion, admin, luis, ficha


def test_la_ficha_es_aleatoria_y_la_base_guarda_solo_su_huella(abierta) -> None:
    sesion, _, luis, ficha = abierta
    otra = sesiones.abrir(sesion, luis, AHORA)
    assert ficha != otra and len(ficha) >= 43  # 256 bits en base64url
    guardadas = {fila.huella_ficha for fila in sesion.query(Sesion)}
    assert sesiones.huella_de(ficha) in guardadas and ficha not in guardadas


def test_valida_con_los_datos_de_la_cuenta(abierta) -> None:
    sesion, _, luis, ficha = abierta
    activa = sesiones.validar(sesion, ficha, AHORA)
    assert (activa.login, activa.roles) == ("luis", frozenset({Rol.ARMA}))
    assert sesiones.validar(sesion, None, AHORA) is None
    assert sesiones.validar(sesion, "ficha inventada", AHORA) is None


def test_la_sesion_da_el_usuario_con_la_forma_del_responsable(abierta) -> None:
    """S4 lee `.usuario` y `.roles` de la ficha de sesión (interfaz supuesta por su plan)."""
    sesion, _, luis, ficha = abierta
    activa = sesiones.validar(sesion, ficha, AHORA)
    assert activa.usuario == cuentas.responsable_de(luis) and activa.usuario.endswith("<luis>")
    assert "arma" in activa.roles  # `Rol` es un `StrEnum`: la comparación con texto vale


def test_inactividad_29_59_sigue_y_30_00_expira(abierta) -> None:
    sesion, *_, ficha = abierta
    assert sesiones.validar(sesion, ficha, AHORA + timedelta(minutes=29, seconds=59))
    # la actividad se renovó a los 29:59; 30:00 de silencio después ya expira
    renovada = AHORA + timedelta(minutes=29, seconds=59)
    assert sesiones.validar(sesion, ficha, renovada + timedelta(minutes=30)) is None
    assert sesiones.validar(sesion, ficha, renovada + timedelta(seconds=1)) is None  # ya cerrada


def test_la_actividad_se_renueva_como_mucho_una_vez_por_minuto(abierta) -> None:
    sesion, *_, ficha = abierta
    sesiones.validar(sesion, ficha, AHORA + timedelta(seconds=59))
    fila = sesion.get(Sesion, sesiones.huella_de(ficha))
    assert fila.ultima_actividad == AHORA  # menos de un minuto: no escribe
    sesiones.validar(sesion, ficha, AHORA + timedelta(seconds=60))
    assert fila.ultima_actividad == AHORA + timedelta(seconds=60)


def test_antiguedad_11_59_59_sigue_y_12_00_00_expira(abierta) -> None:
    sesion, *_, ficha = abierta
    cuando = AHORA
    while cuando + timedelta(minutes=29) < AHORA + timedelta(hours=11, minutes=59):
        cuando += timedelta(minutes=29)
        assert sesiones.validar(sesion, ficha, cuando)  # activa de continuo: renueva
    assert sesiones.validar(sesion, ficha, AHORA + timedelta(hours=11, minutes=59, seconds=59))
    assert sesiones.validar(sesion, ficha, AHORA + timedelta(hours=12)) is None


def test_los_roles_se_leen_de_la_base_en_cada_validacion(abierta) -> None:
    sesion, admin, luis, ficha = abierta
    cuentas.cambiar_roles(sesion, admin, luis.id, ["revisa"], AHORA)
    # cambiar roles cierra las fichas: hay que entrar de nuevo, y trae los roles nuevos
    assert sesiones.validar(sesion, ficha, AHORA) is None
    nueva = sesiones.abrir(sesion, luis, AHORA)
    assert sesiones.validar(sesion, nueva, AHORA).roles == frozenset({Rol.REVISA})
    luis.roles = "arma,revisa"  # un cambio hecho en la base fuera de las funciones
    sesion.commit()
    assert sesiones.validar(sesion, nueva, AHORA).roles == frozenset({Rol.ARMA, Rol.REVISA})


@pytest.mark.parametrize("como", ["restablecer", "desactivar", "roles", "contrasena"])
def test_cuatro_cambios_de_cuenta_cierran_las_fichas(abierta, como: str) -> None:
    sesion, admin, luis, ficha = abierta
    otra = sesiones.abrir(sesion, luis, AHORA)
    if como == "restablecer":
        cuentas.restablecer(sesion, admin, luis.id, "temporal larga y nueva", AHORA)
    elif como == "desactivar":
        cuentas.desactivar(sesion, admin, luis.id, AHORA)
    elif como == "roles":
        cuentas.cambiar_roles(sesion, admin, luis.id, ["arma", "revisa"], AHORA)
    else:
        nueva = cuentas.cambiar_contrasena(sesion, luis.id, CONTRASENA, "otra larga y nueva", AHORA)
        assert nueva not in {ficha, otra}
        assert sesiones.validar(sesion, nueva, AHORA)  # la ficha nueva sí vale
    assert sesiones.validar(sesion, ficha, AHORA) is None
    assert sesiones.validar(sesion, otra, AHORA) is None


def test_cerrar_sesion_marca_la_ficha_y_no_vuelve_a_valer(abierta) -> None:
    sesion, *_, ficha = abierta
    assert sesiones.cerrar(sesion, ficha, "salida", AHORA) is True
    assert sesiones.cerrar(sesion, ficha, "salida", AHORA) is False
    assert sesiones.validar(sesion, ficha, AHORA) is None
