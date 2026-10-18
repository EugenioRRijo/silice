"""La pestana «Asistente de IA» de Administracion (S4 §3.1, §8.3, RV-15; plan 0.9.0, tarea 15).

Con el almacen y los secretos en memoria: la pestana NO toca el almacen de credenciales real.
Ajustes a lo construido (bitacora 0.9.0, T15 y su ronda 1): quien es administrador lo decide
`ui.sesion` con la matriz de roles de S3 (aqui se reemplaza `sesion_actual`), la IP sale de
`ui.cliente` y la operacion sensible exige ademas que no haya eventos de seguridad perdidos sin
revisar (SEG-12).
La carpeta de datos es temporal (conftest): `ia_config.json` y los eventos perdidos viven ahi.
"""

from __future__ import annotations

import dataclasses
import importlib
import json
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from asistente import instalacion
from asistente.clave import SERVICIO, ClaveDeIA, es_bucle_local
from asistente.configuracion import ConfiguracionIA, guardar, leer
from operacion.config import carpeta_datos
from seguridad.permisos import Rol
from seguridad.sesiones import SesionActiva
from tests.fixtures.asistente_clave import AlmacenFalso, SecretosFalsos

SCRIPT = "from ui.paginas.administracion import pestana_asistente\npestana_asistente()\n"
CLAVE = "sk-ant-api03-ABCD1234efgh5678"


def limpio(texto: str) -> str:
    return texto.replace("\\", "")


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    almacen = AlmacenFalso()
    clave = ClaveDeIA(
        almacen=almacen,
        secretos=SecretosFalsos(),
        ruta_respaldo=tmp_path / "ia.cifrada",
        es_local=es_bucle_local,
    )
    pagina = importlib.import_module("ui.paginas.administracion")
    monkeypatch.setattr(pagina, "clave_de_la_instalacion", lambda *a, **k: clave)
    monkeypatch.setattr(instalacion, "clave_de_la_instalacion", lambda *a, **k: clave)
    cliente = importlib.import_module("ui.cliente")
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: "127.0.0.1")
    return SimpleNamespace(
        ruta=instalacion.ruta_de_configuracion(),
        clave=clave,
        almacen=almacen,
        pagina=pagina,
        cliente=cliente,
    )


def con_roles(monkeypatch, *roles: Rol) -> None:
    sesion = SesionActiva(
        huella_ficha="f",
        usuario_id=7,
        login="ana",
        nombre="Ana",
        roles=frozenset(roles),
        debe_cambiar_clave=False,
        restablecida_por_admin=False,
    )
    monkeypatch.setattr(importlib.import_module("ui.sesion"), "sesion_actual", lambda: sesion)


def arrancar() -> AppTest:
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def textos(at: AppTest) -> str:
    return limpio(
        " ".join(
            [c.value for c in at.caption]
            + [s.value for s in at.success]
            + [e.value for e in at.error]
            + [i.value for i in at.info]
            + [w.value for w in at.warning]
        )
    )


def alcanza(objeto, buscado: str, vistos=None) -> bool:
    """True si el texto `buscado` se alcanza desde `objeto` (contenedores, atributos, campos)."""
    vistos = set() if vistos is None else vistos
    if id(objeto) in vistos:
        return False
    vistos.add(id(objeto))
    if isinstance(objeto, str):
        return buscado in objeto
    if isinstance(objeto, bytes):
        return buscado.encode() in objeto
    hijos: list = []
    if isinstance(objeto, dict):
        hijos += list(objeto.keys()) + list(objeto.values())
    elif isinstance(objeto, (list, tuple, set, frozenset)):
        hijos += list(objeto)
    if dataclasses.is_dataclass(objeto) and not isinstance(objeto, type):
        hijos += [getattr(objeto, f.name, None) for f in dataclasses.fields(objeto)]
    hijos += list(getattr(objeto, "__dict__", {}).values())
    return any(alcanza(h, buscado, vistos) for h in hijos)


def estado(at: AppTest) -> dict:
    return {k: at.session_state[k] for k in at.session_state.filtered_state}


def registrar(at: AppTest, texto: str = CLAVE, contrasena: str = "") -> AppTest:
    at.text_input(key="ia_clave_nueva").set_value(texto)
    at.text_input(key="ia_contrasena_respaldo").set_value(contrasena)
    at.button(key="ia_registrar").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


# --- permisos --------------------------------------------------------------------------------


@pytest.mark.parametrize("roles", [(Rol.ARMA,), (Rol.REVISA,), (Rol.ARMA, Rol.REVISA)])
def test_quien_no_es_administrador_solo_ve_el_aviso(entorno, monkeypatch, roles):
    con_roles(monkeypatch, *roles)
    at = arrancar()
    assert [limpio(i.value) for i in at.info] == [
        "El asistente de IA lo configura el administrador de la instalación."
    ]
    assert not at.button and not at.text_input and not at.checkbox


def test_sin_sesion_tampoco_se_configura(entorno, monkeypatch):
    monkeypatch.setattr(importlib.import_module("ui.sesion"), "sesion_actual", lambda: None)
    at = arrancar()
    assert not at.button and at.info


# --- configuracion ---------------------------------------------------------------------------


def test_el_administrador_activa_el_asistente_y_fija_el_tope(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    at = arrancar()
    assert any("excepción declarada" in w.value for w in at.warning)  # el aviso de la nube
    assert not leer(entorno.ruta).activo and not entorno.ruta.exists()  # apagado de fabrica
    at.checkbox(key="ia_activo").set_value(True)
    at.text_input(key="ia_tope").set_value("3,5").run()
    at.button(key="ia_guardar").click().run()
    guardada = leer(entorno.ruta)
    assert guardada.activo and str(guardada.tope_usd) == "3.5"
    assert "Configuración del asistente guardada." in textos(at)
    for malo in ("cero", "0", "-2", "NaN", "Infinity"):
        at.text_input(key="ia_tope").set_value(malo).run()
        at.button(key="ia_guardar").click().run()
        assert at.error, malo
        assert str(leer(entorno.ruta).tope_usd) == "3.5"  # conserva el ultimo valido


def test_desactivar_saca_la_clave_de_la_memoria(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    guardar(entorno.ruta, ConfiguracionIA(activo=True))
    at = registrar(arrancar())
    assert entorno.clave.vigente == CLAVE
    at.checkbox(key="ia_activo").set_value(False)
    at.button(key="ia_guardar").click().run()
    assert entorno.clave.vigente is None and not leer(entorno.ruta).activo
    assert entorno.almacen.datos == {(SERVICIO, instalacion.EMPRESA_DE_LA_CLAVE): CLAVE}
    assert "no se carga mientras el asistente esté apagado" in textos(at)


# --- la clave de IA --------------------------------------------------------------------------


def test_la_clave_se_registra_desde_el_propio_equipo_y_solo_se_ven_cuatro_caracteres(
    entorno, monkeypatch
):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    at = registrar(arrancar())
    assert entorno.clave.vigente == CLAVE
    assert entorno.almacen.datos == {(SERVICIO, instalacion.EMPRESA_DE_LA_CLAVE): CLAVE}
    leido = textos(at)
    assert "Clave de IA registrada (…5678)." in leido and "Clave registrada: …5678" in leido
    assert CLAVE not in leido
    assert not at.session_state["ia_clave_nueva"]
    assert not alcanza(estado(at), CLAVE)  # nunca en el estado de la pantalla
    assert not alcanza(estado(at), "ABCD1234efgh")


def test_desde_otro_equipo_la_clave_se_rechaza(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    monkeypatch.setattr(entorno.cliente, "ip_del_cliente", lambda: "192.168.1.40")
    at = arrancar()
    assert at.text_input(key="ia_clave_nueva").disabled  # el formulario ni se ofrece
    assert at.button(key="ia_registrar").disabled and at.button(key="ia_olvidar").disabled
    assert any(entorno.cliente.MENSAJE_REMOTO == limpio(i.value) for i in at.info)
    registrar(at)  # aunque se fuerce el envio, el callback vuelve a comprobarlo
    assert entorno.clave.vigente is None and entorno.almacen.datos == {}
    assert entorno.cliente.MENSAJE_REMOTO in textos(at)
    assert not alcanza(estado(at), CLAVE)


def test_con_eventos_de_seguridad_perdidos_sin_revisar_no_se_registra(entorno, monkeypatch):
    """SEG-12: tras restaurar un respaldo con eventos perdidos, la operacion sensible se bloquea."""
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    perdidos = carpeta_datos() / "eventos_perdidos_20261013.json"
    perdidos.write_text(json.dumps({"eventos": [], "revisado": False}), encoding="utf-8")
    at = registrar(arrancar())
    assert entorno.clave.vigente is None and entorno.almacen.datos == {}
    assert entorno.cliente.MENSAJE_PENDIENTE in textos(at)


def test_una_clave_en_blanco_se_rechaza_con_mensaje(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    at = registrar(arrancar(), texto="   ")
    assert entorno.clave.vigente is None
    assert "Escriba la clave de IA de la empresa." in textos(at)


def test_sin_almacen_pide_la_contrasena_del_respaldo_y_cifra(entorno, monkeypatch, tmp_path):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    entorno.almacen.cae = True
    at = registrar(arrancar())
    assert entorno.clave.vigente is None
    assert "indique una contrasena para guardar la clave cifrada" in textos(at)
    registrar(at, contrasena="una contrasena larga")
    assert entorno.clave.vigente == CLAVE
    assert CLAVE.encode() not in (tmp_path / "ia.cifrada").read_bytes()
    assert not alcanza(estado(at), CLAVE) and not alcanza(estado(at), "una contrasena larga")


def test_olvidar_la_clave_la_borra(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    at = registrar(arrancar())
    at.button(key="ia_olvidar").click().run()
    assert entorno.clave.vigente is None and entorno.almacen.datos == {}
    leido = textos(at)
    assert "Clave registrada: ninguna" in leido
    assert "La clave de IA se olvidó: ya no está en este equipo." in leido


def test_al_reiniciar_con_el_asistente_activo_la_clave_guardada_se_recarga(entorno, monkeypatch):
    """Ronda 1 de T15: la pestana trae la clave del almacen al abrirse (un proceso nuevo)."""
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    guardar(entorno.ruta, ConfiguracionIA(activo=True))
    entorno.almacen.set_password(SERVICIO, instalacion.EMPRESA_DE_LA_CLAVE, CLAVE)
    at = arrancar()
    assert entorno.clave.vigente == CLAVE and "Clave registrada: …5678" in textos(at)


def test_apagado_la_clave_guardada_no_vuelve_a_la_memoria(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    entorno.almacen.set_password(SERVICIO, instalacion.EMPRESA_DE_LA_CLAVE, CLAVE)
    at = arrancar()
    assert entorno.clave.vigente is None
    assert "hay una guardada, pero no se carga mientras el asistente esté apagado" in textos(at)


def test_sin_el_extra_ia_la_pestana_lo_dice_y_la_configuracion_sigue(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)

    def sin_keyring(*args, **kwargs):
        raise ImportError("No module named 'keyring'")

    monkeypatch.setattr(entorno.pagina, "clave_de_la_instalacion", sin_keyring)
    at = arrancar()
    assert entorno.pagina.SIN_EXTRA_IA in textos(at)
    assert at.button(key="ia_guardar") is not None
    assert not [b for b in at.button if b.key == "ia_registrar"]


# --- reactivar la clave desde el respaldo cifrado (ruta, sesion 1, tarea 1.2) -----------------

CONTRASENA = "una contrasena larga"


def con_solo_el_respaldo(entorno) -> None:
    """Asistente activo, almacen caido, la clave en el respaldo cifrado y un proceso nuevo."""
    guardar(entorno.ruta, ConfiguracionIA(activo=True))
    entorno.almacen.cae = True
    entorno.clave.registrar(
        instalacion.EMPRESA_DE_LA_CLAVE,
        CLAVE,
        ip_cliente="127.0.0.1",
        contrasena_respaldo=CONTRASENA,
    )
    entorno.clave.desactivar()


def hay_reactivar(at: AppTest) -> bool:
    return any(t.key == "ia_contrasena_reactivar" for t in at.text_input)


def reactivar(at: AppTest, contrasena: str = CONTRASENA) -> AppTest:
    at.text_input(key="ia_contrasena_reactivar").set_value(contrasena)
    at.button(key="ia_reactivar").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_la_contrasena_de_reactivar_no_queda_en_la_pantalla(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    con_solo_el_respaldo(entorno)
    at = arrancar()
    assert entorno.clave.vigente is None and hay_reactivar(at)
    at.text_input(key="ia_contrasena_reactivar").set_value("otra contrasena larga")
    at.button(key="ia_reactivar").click().run()
    assert entorno.clave.vigente is None
    assert "La contraseña no abre el respaldo de la clave de IA." in textos(at)
    assert at.session_state["ia_contrasena_reactivar"] == ""
    assert not alcanza(estado(at), "otra contrasena larga")
    reactivar(at)
    assert entorno.clave.vigente == CLAVE
    leido = textos(at)
    assert "Clave de IA reactivada (…5678)." in leido and "Clave registrada: …5678" in leido
    assert CLAVE not in leido and CONTRASENA not in leido
    assert at.session_state["ia_contrasena_reactivar"] == ""
    assert not alcanza(estado(at), CONTRASENA) and not alcanza(estado(at), CLAVE)
    assert not alcanza(estado(at), "ABCD1234efgh")
    assert not hay_reactivar(at)  # cargada: la seccion ya no se pide


def test_la_seccion_solo_aparece_si_pide_contrasena(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    guardar(entorno.ruta, ConfiguracionIA(activo=True))
    assert not hay_reactivar(arrancar())  # nada guardado
    entorno.almacen.set_password(SERVICIO, instalacion.EMPRESA_DE_LA_CLAVE, CLAVE)
    at = arrancar()
    assert entorno.clave.vigente == CLAVE and not hay_reactivar(at)  # el almacen la tenia
    entorno.almacen.datos.clear()
    entorno.clave.olvidar(instalacion.EMPRESA_DE_LA_CLAVE)
    con_solo_el_respaldo(entorno)
    assert hay_reactivar(arrancar())  # solo el respaldo cifrado
    guardar(entorno.ruta, ConfiguracionIA(activo=False))
    assert not hay_reactivar(arrancar())  # apagado, la clave no vuelve a la memoria (§8.3)
    assert entorno.clave.vigente is None


@pytest.mark.parametrize("roles", [(Rol.ARMA,), (Rol.REVISA,)])
def test_la_seccion_no_aparece_para_quien_no_es_administrador(entorno, monkeypatch, roles):
    con_solo_el_respaldo(entorno)
    con_roles(monkeypatch, *roles)
    assert not hay_reactivar(arrancar())


def test_la_seccion_no_aparece_si_el_cliente_no_es_local(entorno, monkeypatch):
    con_roles(monkeypatch, Rol.ADMINISTRADOR)
    con_solo_el_respaldo(entorno)
    monkeypatch.setattr(entorno.cliente, "ip_del_cliente", lambda: "192.168.1.40")
    at = arrancar()
    assert not hay_reactivar(at) and not [b for b in at.button if b.key == "ia_reactivar"]
    assert entorno.clave.vigente is None
