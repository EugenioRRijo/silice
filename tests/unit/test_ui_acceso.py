"""Pantalla de acceso, primer administrador, sesión expirada y 'solo desde el propio equipo'
(RF-80, RF-81, UC-21; spec S3 §5.3 a §5.7). `AppTest` con el reloj y la IP inyectados."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from seguridad import cuentas
from seguridad.modelo import Usuario
from tests.fixtures.instalacion import AHORA, CONTRASENA
from ui import sesion as ui_sesion
from ui.acceso import AVISO_EXPIRADA, AVISO_OTRO_USUARIO, AVISO_SIN_CIFRAR


def _app() -> None:
    import streamlit as st

    from ui import acceso

    sesion = acceso.exigir_sesion()
    acceso.pintar_sesion(sesion)
    st.write(f"hola {sesion.login}")
    st.session_state.setdefault("borrador", "mi borrador")


@pytest.fixture
def entorno(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SILICE_ACCESO", "1")
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path))
    monkeypatch.setenv("SILICE_INSTALACION", str(tmp_path / "instalacion.db"))
    reloj = {"ahora": AHORA}
    monkeypatch.setattr(ui_sesion, "ahora", lambda: reloj["ahora"])
    monkeypatch.setattr(ui_sesion, "ip_del_cliente", lambda: "127.0.0.1")
    ui_sesion.limpiar_motores()
    yield tmp_path, reloj
    ui_sesion.limpiar_motores()


def _arrancar() -> AppTest:
    return AppTest.from_function(_app, default_timeout=60).run()


def _texto(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def _crear_administrador(at: AppTest, carpeta: Path) -> AppTest:
    codigo = (carpeta / "codigo_instalacion.txt").read_text().strip()
    at.text_input(key="acceso_codigo").input(codigo)
    at.text_input(key="acceso_nuevo_login").input("admin")
    at.text_input(key="acceso_nuevo_nombre").input("Ana Admin")
    at.text_input(key="acceso_nueva_clave").input(CONTRASENA)
    at.text_input(key="acceso_repetida").input(CONTRASENA)
    at.button[0].click()
    return at.run()


def _entrar(at: AppTest, login: str, clave: str = CONTRASENA) -> AppTest:
    at.text_input(key="acceso_login").input(login)
    at.text_input(key="acceso_contrasena").input(clave)
    at.button[0].click()
    return at.run()


def _alta(carpeta: Path, login: str, roles: tuple[str, ...]) -> None:
    with ui_sesion.instalacion() as bd:
        admin = bd.query(Usuario).filter_by(login="admin").one()
        cuentas.crear_usuario(bd, admin, login, login.title(), roles, CONTRASENA, AHORA)
        usuario = bd.query(Usuario).filter_by(login=login).one()
        usuario.debe_cambiar_clave = False
        bd.commit()


def test_con_el_acceso_apagado_nada_pide_entrar(monkeypatch) -> None:
    monkeypatch.setenv("SILICE_ACCESO", "0")
    at = _arrancar()
    assert "hola desarrollo" in _texto(at) and not at.text_input


def test_la_primera_vez_pide_el_codigo_y_deja_al_administrador_dentro(entorno) -> None:
    carpeta, _ = entorno
    at = _arrancar()
    assert at.title[0].value == "Sílice: acceso" and "Primera vez" in at.subheader[0].value
    at = _crear_administrador(at, carpeta)
    assert "hola admin" in _texto(at) and not at.error
    assert not (carpeta / "codigo_instalacion.txt").exists()  # el código se usó y se borró


def test_el_primer_administrador_con_codigo_malo_o_claves_distintas_no_entra(entorno) -> None:
    at = _arrancar()
    at.text_input(key="acceso_codigo").input("A" * 20)
    at.text_input(key="acceso_nuevo_login").input("admin")
    at.text_input(key="acceso_nueva_clave").input(CONTRASENA)
    at.text_input(key="acceso_repetida").input(CONTRASENA + "x")
    at.button[0].click()
    at = at.run()
    assert at.error[0].value == "Las dos contraseñas no coinciden."
    at.text_input(key="acceso_repetida").input(CONTRASENA)
    at.button[0].click()
    at = at.run()
    assert "no es válido" in at.error[0].value and "hola" not in _texto(at)


def test_entrar_con_usuario_y_contrasena(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    assert "hola admin" in _texto(at)
    assert any("Sesión: Ana Admin (administrador)" in c.value for c in at.sidebar.caption)


def test_contrasena_erronea_da_el_mismo_mensaje_exista_o_no_el_usuario(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    at.button(key="silice_cerrar_sesion").click()
    at = at.run()
    mensajes = []
    for login in ("admin", "fantasma"):
        at = _entrar(at, login, "mala contrasena larga")
        mensajes.append(at.error[0].value)
    assert mensajes == [cuentas.MENSAJE_FALLO, cuentas.MENSAJE_FALLO]


def test_cerrar_sesion_vuelve_al_acceso(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    at.button(key="silice_cerrar_sesion").click()
    at = at.run()
    assert at.title[0].value == "Sílice: acceso" and "hola" not in _texto(at)


def test_sesion_expirada_vuelve_al_acceso_conservando_el_borrador_del_mismo_usuario(entorno):
    carpeta, reloj = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    at.session_state["borrador"] = "cambios sin guardar"
    reloj["ahora"] = AHORA + timedelta(minutes=30)  # 30:00 exacto: expira
    at = at.run()
    assert at.title[0].value == "Sílice: acceso" and any(AVISO_EXPIRADA in i.value for i in at.info)
    assert at.session_state["borrador"] == "cambios sin guardar"
    at = _entrar(at, "admin")
    assert "hola admin" in _texto(at) and at.session_state["borrador"] == "cambios sin guardar"


def test_otro_usuario_en_la_pestana_descarta_el_borrador_con_aviso(entorno) -> None:
    carpeta, reloj = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    _alta(carpeta, "luis", ("arma",))
    at.session_state["borrador"] = "cambios del admin"
    reloj["ahora"] = AHORA + timedelta(minutes=31)
    at = at.run()
    at = _entrar(at, "luis")
    assert "hola luis" in _texto(at)
    assert at.session_state["borrador"] == "mi borrador"  # el del admin no sobrevivió
    assert any(AVISO_OTRO_USUARIO in i.value for i in at.info) or "hola luis" in _texto(at)


def test_una_contrasena_temporal_obliga_a_cambiarla_antes_de_seguir(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    with ui_sesion.instalacion() as bd:
        admin = bd.query(Usuario).filter_by(login="admin").one()
        cuentas.crear_usuario(bd, admin, "luis", "Luis", ["arma"], CONTRASENA, AHORA)
    at.button(key="silice_cerrar_sesion").click()
    at = _entrar(at.run(), "luis")
    assert at.title[0].value == "Cambie su contraseña" and "hola" not in _texto(at)
    at.text_input(key="cambio_actual").input(CONTRASENA)
    at.text_input(key="cambio_nueva").input("otra contrasena larga y nueva")
    at.text_input(key="cambio_repetida").input("otra contrasena larga y nueva")
    at.button[0].click()
    at = at.run()
    assert "hola luis" in _texto(at)


@pytest.mark.parametrize("ip,aviso", [("127.0.0.1", False), ("::1", False), ("192.168.1.20", True)])
def test_el_aviso_de_conexion_sin_cifrar_solo_para_clientes_remotos(
    entorno, monkeypatch, ip, aviso
):
    monkeypatch.setattr(ui_sesion, "ip_del_cliente", lambda: ip)
    at = _arrancar()
    assert any(AVISO_SIN_CIFRAR in w.value for w in at.warning) is aviso


def test_el_nombre_de_una_cuenta_con_markdown_no_se_interpreta(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    with ui_sesion.instalacion() as bd:
        bd.query(Usuario).filter_by(login="admin").one().nombre = "![x](http://127.0.0.1:9/p.png)"
        bd.commit()
    at = at.run()
    pie = [c.value for c in at.sidebar.caption if c.value.startswith("Sesión:")][0]
    assert "![" not in pie and "\\!\\[x\\]" in pie


def test_sin_cambio_de_hora_la_ficha_sigue_valiendo_entre_ejecuciones(entorno) -> None:
    carpeta, reloj = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    reloj["ahora"] = AHORA + timedelta(minutes=29, seconds=59)
    assert "hola admin" in _texto(at.run())


def test_la_fecha_inyectada_es_la_del_reloj_de_la_prueba(entorno) -> None:
    _, reloj = entorno
    assert ui_sesion.ahora() == reloj["ahora"] == datetime(2026, 11, 10, 9, 0, 0)
