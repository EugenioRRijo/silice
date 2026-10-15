"""Administración (UC-21; RF-80, RF-84, RF-88; spec S3 §5.7): rol, equipo local y secretos.

Adaptado a lo construido (nota de ejecución de la tarea 17): las pestañas son un
`st.segmented_control` (`adm_pestana`) que dibuja solo la elegida, y son siete (S3 §5.7 más la
de IA de S4 y la de Instalación de S5); el rechazo desde otra máquina es el mensaje de
`ui.cliente.operacion_sensible_permitida` (`MENSAJE_REMOTO`), y la IP que decide es la de
`ui.cliente.ip_del_cliente`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from seguridad import empresas, firma
from seguridad.modelo import ClaveApi, ClaveEmpresa, Usuario
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import cliente
from ui import sesion as ui_sesion
from ui.sesion import MENSAJE_SIN_ENTRAR, MENSAJE_SIN_PERMISO

#: A mano, del spec S3 §5.7 (cinco), S4 §3.1 (Asistente de IA) y S5 (Instalación).
PESTANAS = [
    "Cuentas",
    "Empresa y clave de firma",
    "Empresas registradas",
    "Claves de API",
    "Asistente de IA",
    "Accesos",
    "Instalación",
]
CONTRASENA_CLAVE = "una clave de firma larga y unica"
HUELLA_CORTA = re.compile(r"^[0-9A-Z]{4}(-[0-9A-Z]{4}){4}$")  # 5 grupos de 4 = 20 x 5 bits


def _pagina() -> None:
    from ui.paginas import administracion

    administracion.render()


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


def _abrir(monkeypatch, tmp_path: Path, *roles: str, ip: str = "127.0.0.1") -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, *roles, ip=ip)
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: ip)
    return con_ficha(AppTest.from_function(_pagina, default_timeout=60), ficha).run()


def _ir(at: AppTest, pestana: str) -> AppTest:
    at.segmented_control(key="adm_pestana").set_value(pestana)
    return at.run()


def _guardar_empresa(at: AppTest) -> AppTest:
    at = _ir(at, "Empresa y clave de firma")
    at.text_input(key="adm_empresa_nombre").input("Contratista Demo, C.A.")
    at.text_input(key="adm_empresa_rif").input("J-00000000-0")
    at.button(key="adm_empresa_enviar").click()
    return at.run()


def _crear_cuenta(at: AppTest, login: str, roles: list[str], temporal: str) -> AppTest:
    at.text_input(key="adm_login").input(login)
    at.text_input(key="adm_nombre").input(login.title())
    at.multiselect(key="adm_roles").set_value(roles)
    at.text_input(key="adm_temporal").input(temporal)
    at.button(key="adm_crear_enviar").click()
    return at.run()


def test_el_administrador_ve_las_siete_pestanas_y_empieza_en_cuentas(monkeypatch, tmp_path):
    at = _abrir(monkeypatch, tmp_path, "administrador")
    assert not at.exception, [e.value for e in at.exception]
    selector = at.segmented_control(key="adm_pestana")
    assert list(selector.options) == PESTANAS
    assert selector.value == "Cuentas"


@pytest.mark.parametrize("rol", ["arma", "revisa"])
def test_un_rol_que_no_es_administrador_no_ve_nada_aunque_llegue_por_la_url(
    monkeypatch, tmp_path, rol
) -> None:
    at = _abrir(monkeypatch, tmp_path, rol)
    assert [e.value for e in at.error] == [MENSAJE_SIN_PERMISO]
    assert not at.get("button_group")


def test_sin_sesion_pide_entrar(monkeypatch, tmp_path) -> None:
    preparar(monkeypatch, tmp_path, "administrador")
    at = AppTest.from_function(_pagina, default_timeout=60).run()
    assert [e.value for e in at.error] == [MENSAJE_SIN_ENTRAR] and not at.get("button_group")


def test_crear_una_cuenta_la_deja_con_contrasena_temporal_y_avisa_si_arma_y_revisa(
    monkeypatch, tmp_path
) -> None:
    temporal = "una contrasena temporal larga"
    at = _crear_cuenta(
        _abrir(monkeypatch, tmp_path, "administrador"), "pedro", ["arma", "revisa"], temporal
    )
    assert not at.exception and any("Cuenta creada" in s.value for s in at.success)
    assert any("revisar paquetes que ella misma armó" in w.value for w in at.warning)
    with ui_sesion.instalacion() as bd:
        pedro = bd.query(Usuario).filter_by(login="pedro").one()
        assert pedro.debe_cambiar_clave and temporal not in pedro.huella_clave
        assert pedro.roles == "arma,revisa"


def test_una_cuenta_con_un_solo_rol_no_lleva_el_aviso(monkeypatch, tmp_path) -> None:
    at = _crear_cuenta(
        _abrir(monkeypatch, tmp_path, "administrador"), "rosa", ["revisa"], "diez letra"
    )
    assert any("Cuenta creada" in s.value for s in at.success)
    assert not any("ella misma armó" in w.value for w in at.warning)


def test_la_contrasena_temporal_de_9_se_rechaza_y_la_de_10_no(monkeypatch, tmp_path) -> None:
    """Frontera de `MINIMO_CONTRASENA` = 10 (S3 §5.2): 9 caracteres no, 10 sí."""
    at = _crear_cuenta(
        _abrir(monkeypatch, tmp_path, "administrador"), "pedro", ["arma"], "pqzx7wvk2"
    )
    assert at.error and not at.exception
    assert any("al menos 10" in e.value for e in at.error)
    with ui_sesion.instalacion() as bd:
        assert bd.query(Usuario).filter_by(login="pedro").count() == 0
    at = _crear_cuenta(at, "pedro", ["arma"], "pqzx7wvk2m")
    assert any("Cuenta creada" in s.value for s in at.success)
    with ui_sesion.instalacion() as bd:
        assert bd.query(Usuario).filter_by(login="pedro").count() == 1


def test_la_clave_de_firma_no_se_genera_sin_empresa(monkeypatch, tmp_path) -> None:
    at = _ir(_abrir(monkeypatch, tmp_path, "administrador"), "Empresa y clave de firma")
    assert any("Primero guarde el nombre y el RIF" in i.value for i in at.info)
    assert not at.text_input(key="adm_empresa_nombre").value


def test_la_clave_de_firma_solo_se_genera_desde_el_propio_equipo(monkeypatch, tmp_path) -> None:
    at = _guardar_empresa(_abrir(monkeypatch, tmp_path, "administrador", ip="192.168.1.20"))
    at.text_input(key="adm_clave_uno").input(CONTRASENA_CLAVE)
    at.text_input(key="adm_clave_dos").input(CONTRASENA_CLAVE)
    at.button(key="adm_generar_enviar").click()
    at = at.run()
    assert cliente.MENSAJE_REMOTO in [e.value for e in at.error]
    with ui_sesion.instalacion() as bd:
        assert bd.query(ClaveEmpresa).count() == 0


def test_dos_contrasenas_distintas_no_generan_clave(monkeypatch, tmp_path) -> None:
    at = _guardar_empresa(_abrir(monkeypatch, tmp_path, "administrador"))
    at.text_input(key="adm_clave_uno").input(CONTRASENA_CLAVE)
    at.text_input(key="adm_clave_dos").input(CONTRASENA_CLAVE + "!")
    at.button(key="adm_generar_enviar").click()
    at = at.run()
    assert "Las dos contraseñas no coinciden." in [e.value for e in at.error]
    with ui_sesion.instalacion() as bd:
        assert bd.query(ClaveEmpresa).count() == 0


def test_generar_la_clave_en_el_equipo_muestra_la_huella_y_nunca_la_privada(
    monkeypatch, tmp_path
) -> None:
    at = _guardar_empresa(_abrir(monkeypatch, tmp_path, "administrador"))
    at.text_input(key="adm_clave_uno").input(CONTRASENA_CLAVE)
    at.text_input(key="adm_clave_dos").input(CONTRASENA_CLAVE)
    at.button(key="adm_generar_enviar").click()
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    with ui_sesion.instalacion() as bd:
        clave = empresas.clave_activa(bd)
        assert clave is not None and clave.privada_cifrada
        assert CONTRASENA_CLAVE.encode() not in clave.privada_cifrada
        publica = clave.publica
    textos = [
        *(m.value for m in at.markdown),
        *(m.value for m in at.metric),
        *(c.value for c in at.caption),
        *(s.value for s in at.success),
    ]
    assert not any(CONTRASENA_CLAVE in t for t in textos)
    [huella] = [m.value for m in at.metric if m.label == "Huella de la clave de firma"]
    assert len(huella) == 24 and HUELLA_CORTA.match(huella)  # 5 grupos de 4 y 4 guiones
    assert huella == firma.huella_corta(publica)


def test_la_clave_de_api_se_muestra_una_vez_y_la_base_guarda_solo_su_huella(
    monkeypatch, tmp_path
) -> None:
    import hashlib

    at = _ir(_abrir(monkeypatch, tmp_path, "administrador"), "Claves de API")
    at.text_input(key="adm_api_nombre").input("plugin de Revit")
    at.button(key="adm_api_enviar").click()
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    secreto = at.code[0].value
    assert secreto.count(".") == 1
    assert any("no se vuelve a mostrar" in s.value for s in at.success)
    identificador, en_claro = secreto.split(".")
    with ui_sesion.instalacion() as bd:
        fila = bd.query(ClaveApi).one()
        assert fila.identificador == identificador and not fila.revocada
        assert en_claro not in fila.huella_secreto
        assert fila.huella_secreto == hashlib.sha256(en_claro.encode()).hexdigest()
    assert not at.run().code  # el siguiente ciclo ya no la muestra


def test_una_clave_de_api_sin_nombre_no_se_crea(monkeypatch, tmp_path) -> None:
    at = _ir(_abrir(monkeypatch, tmp_path, "administrador"), "Claves de API")
    at.text_input(key="adm_api_nombre").input("   ")
    at.button(key="adm_api_enviar").click()
    at = at.run()
    assert at.error and not at.code
    with ui_sesion.instalacion() as bd:
        assert bd.query(ClaveApi).count() == 0


def test_la_clave_de_api_no_se_crea_desde_otra_maquina(monkeypatch, tmp_path) -> None:
    at = _ir(_abrir(monkeypatch, tmp_path, "administrador", ip="10.0.0.5"), "Claves de API")
    at.text_input(key="adm_api_nombre").input("plugin")
    at.button(key="adm_api_enviar").click()
    at = at.run()
    assert cliente.MENSAJE_REMOTO in [e.value for e in at.error]
    with ui_sesion.instalacion() as bd:
        assert bd.query(ClaveApi).count() == 0


def test_revocar_una_clave_de_api_la_deja_revocada(monkeypatch, tmp_path) -> None:
    at = _ir(_abrir(monkeypatch, tmp_path, "administrador"), "Claves de API")
    at.text_input(key="adm_api_nombre").input("plugin")
    at.button(key="adm_api_enviar").click()
    at = at.run().run()  # la lista de vigentes se lee antes de crear: aparece en el ciclo siguiente
    at.button(key="adm_api_boton_revocar").click()
    at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    with ui_sesion.instalacion() as bd:
        assert bd.query(ClaveApi).one().revocada


def test_la_pestana_de_accesos_muestra_el_registro(monkeypatch, tmp_path) -> None:
    at = _ir(_abrir(monkeypatch, tmp_path, "administrador"), "Accesos")
    assert not at.exception, [e.value for e in at.exception]
    assert any("solo se agrega" in c.value for c in at.caption)
    assert len(at.dataframe) == 1
