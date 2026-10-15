"""Los proveedores que la instalacion ofrece y por que no (S4 §3.1 flujos 9a y 9b; plan 0.9.0, T14).

Cubre `asistente/fabrica.py` y `asistente/instalacion.py`. Nunca se cambia de proveedor en silencio
(RS4-5): se ofrecen los disponibles y se dice por que no lo esta cada uno de los otros. Apagado de
fabrica, no se toca ni la clave ni `keyring`. Ollama con resolvedor, version y cliente falsos: sin
red. El almacen de credenciales del sistema se reemplaza siempre por uno en memoria (la clave de la
instalacion es UNA por proceso: `instalacion._CLAVE` se reinicia en cada prueba).
"""

from __future__ import annotations

import logging
import socket
from decimal import Decimal
from types import SimpleNamespace

import pytest

from asistente import instalacion
from asistente.clave import SERVICIO, ClaveDeIA, es_bucle_local
from asistente.configuracion import ConfiguracionIA, guardar
from asistente.fabrica import proveedores
from asistente.proveedores.base import FALTA_EL_COMPONENTE
from tests.fixtures.asistente_clave import AlmacenFalso, AlmacenRoto, SecretosFalsos

MINIMA = (0, 35, 0)  # la de `asistente/config_ia.json` (0.35.0, CVE-2026-103663; bitacora T3)
APAGADO = "El asistente esta apagado: lo activa el administrador de la instalacion."
CLAVE = "sk-ant-api03-INSTALACION-1234"


def clave_de(tmp_path, *, con_clave: bool, almacen: AlmacenFalso | None = None) -> ClaveDeIA:
    clave = ClaveDeIA(
        almacen=almacen if almacen is not None else AlmacenFalso(),
        secretos=SecretosFalsos(),
        ruta_respaldo=tmp_path / "ia.cifrada",
        es_local=es_bucle_local,
    )
    if con_clave:
        clave.registrar("EMP", CLAVE, ip_cliente="127.0.0.1")
    return clave


def _resolver(ip: str):
    familia = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return lambda nombre, puerto: [(familia, 1, 6, "", (ip, 0))]


def local(**extra):
    cliente = SimpleNamespace(list=lambda: SimpleNamespace(models=[SimpleNamespace(model="m")]))
    return {
        "resolver": _resolver("127.0.0.1"),
        "obtener_version": lambda: "0.35.0",
        "cliente": cliente,
        **extra,
    }


# --- fabrica.proveedores --------------------------------------------------------------------


def test_apagado_no_ofrece_ninguno_y_lo_dice_sin_tocar_la_clave():
    ofertas = proveedores(ConfiguracionIA(), None, MINIMA)
    assert ofertas == {"claude": (None, APAGADO), "ollama": (None, APAGADO)}


def test_activo_sin_clave_ofrece_solo_el_local_y_dice_que_falta_la_clave(tmp_path):
    cfg = ConfiguracionIA(activo=True, modelo_local="m")
    ofertas = proveedores(cfg, clave_de(tmp_path, con_clave=False), MINIMA, **local())
    assert ofertas["claude"] == (None, "Falta registrar la clave de IA de la empresa.")
    proveedor, motivo = ofertas["ollama"]
    assert motivo == "" and proveedor.modelo == "m" and not proveedor.envia_fuera_del_equipo


def test_activo_sin_objeto_clave_tampoco_ofrece_claude():
    ofertas = proveedores(ConfiguracionIA(activo=True), None, MINIMA)
    assert ofertas["claude"] == (None, "Falta registrar la clave de IA de la empresa.")


def test_activo_con_clave_ofrece_claude_con_el_modelo_configurado(tmp_path):
    cfg = ConfiguracionIA(activo=True, modelo_claude="claude-otro")
    ofertas = proveedores(cfg, clave_de(tmp_path, con_clave=True), MINIMA)
    claude, motivo = ofertas["claude"]
    assert motivo == "" and claude.envia_fuera_del_equipo and claude.modelo == "claude-otro"
    assert ofertas["ollama"] == (None, "No hay un modelo local configurado.")


@pytest.mark.parametrize(
    ("version", "disponible"),
    [("0.34.9", False), ("0.35.0", True), ("0.35.1", True), ("0.35.0-rc1", True)],
)
def test_la_version_minima_de_ollama_es_la_frontera(tmp_path, version, disponible):
    cfg = ConfiguracionIA(activo=True, modelo_local="m")
    datos = local(obtener_version=lambda: version)
    ofertas = proveedores(cfg, clave_de(tmp_path, con_clave=True), MINIMA, **datos)
    if disponible:
        assert ofertas["ollama"][0] is not None and ofertas["ollama"][1] == ""
    else:
        assert ofertas["ollama"] == (None, "Ollama 0.34.9 es anterior a la minima (0.35.0).")
    assert ofertas["claude"][0] is not None  # el otro sigue ofrecido, sin cambiar en silencio


def test_un_anfitrion_que_resuelve_fuera_del_equipo_se_trata_como_nube(tmp_path):
    cfg = ConfiguracionIA(activo=True, modelo_local="m", anfitrion_ollama="http://ollama.lan:11434")
    datos = local(resolver=_resolver("192.168.1.20"))
    proveedor, motivo = proveedores(cfg, None, MINIMA, **datos)["ollama"]
    assert motivo == "" and proveedor.envia_fuera_del_equipo
    assert proveedor.anfitrion == "http://ollama.lan:11434"


def test_un_modelo_local_que_no_esta_instalado_no_se_ofrece(tmp_path):
    cfg = ConfiguracionIA(activo=True, modelo_local="otro-modelo")
    proveedor, motivo = proveedores(cfg, None, MINIMA, **local())["ollama"]
    assert proveedor is None and "otro-modelo" in motivo


# --- instalacion ----------------------------------------------------------------------------


@pytest.fixture
def datos(monkeypatch, tmp_path):
    """La carpeta de datos es temporal (conftest); la clave de la instalacion, en memoria."""
    almacen = AlmacenFalso()
    monkeypatch.setattr(instalacion, "_CLAVE", None)
    monkeypatch.setattr(instalacion, "almacen_del_sistema", lambda: almacen)
    return SimpleNamespace(ruta=instalacion.ruta_de_configuracion(), almacen=almacen)


def test_la_configuracion_vive_en_la_carpeta_de_datos(datos, tmp_path):
    from operacion.config import carpeta_datos

    assert datos.ruta == carpeta_datos() / "ia_config.json"


def test_de_la_instalacion_apagado_no_toca_la_clave_ni_seguridad(datos, monkeypatch):
    def no_debe_llamarse(*args, **kwargs):
        raise AssertionError("apagado: no se toca la clave")

    monkeypatch.setattr(instalacion, "clave_de_la_instalacion", no_debe_llamarse)
    assert instalacion.proveedores_de_la_instalacion() == {
        "claude": (None, APAGADO),
        "ollama": (None, APAGADO),
    }
    guardar(datos.ruta, ConfiguracionIA(prefijos_de_maprex=("MPX-",)))
    assert instalacion.prefijos_de_maprex() == ("MPX-",)


def test_al_reiniciar_la_clave_guardada_vuelve_del_almacen(datos):
    """Ronda 1 de T15: el proceso arranca sin la clave en memoria y la trae del almacen."""
    datos.almacen.set_password(SERVICIO, instalacion.EMPRESA_DE_LA_CLAVE, CLAVE)
    guardar(datos.ruta, ConfiguracionIA(activo=True))
    ofertas = instalacion.proveedores_de_la_instalacion()
    assert ofertas["claude"][0] is not None and ofertas["claude"][1] == ""
    assert instalacion.clave_de_la_instalacion().vigente == CLAVE


def test_la_clave_de_la_instalacion_es_una_por_proceso_y_su_respaldo_esta_en_los_datos(datos):
    from operacion.config import carpeta_datos

    primera = instalacion.clave_de_la_instalacion()
    assert instalacion.clave_de_la_instalacion() is primera
    assert primera._ruta == carpeta_datos() / "ia_clave.cifrada"


def test_sin_el_extra_ia_la_hoja_no_se_cae(datos, monkeypatch):
    def sin_keyring(*args, **kwargs):
        raise ImportError("No module named 'keyring'")

    monkeypatch.setattr(instalacion, "clave_de_la_instalacion", sin_keyring)
    guardar(datos.ruta, ConfiguracionIA(activo=True))
    assert instalacion.proveedores_de_la_instalacion() == {
        "claude": (None, FALTA_EL_COMPONENTE),
        "ollama": (None, FALTA_EL_COMPONENTE),
    }


def test_cargar_la_clave_guardada_no_vuelve_a_leer_si_ya_esta_en_memoria(tmp_path):
    almacen = AlmacenFalso()
    clave = clave_de(tmp_path, con_clave=True, almacen=almacen)
    instalacion.cargar_clave_guardada(clave, "EMP")
    assert almacen.lecturas == 0 and clave.vigente == CLAVE


def test_cargar_sin_nada_guardado_no_hace_nada_y_no_registra(tmp_path, caplog):
    clave = clave_de(tmp_path, con_clave=False)
    with caplog.at_level(logging.WARNING):
        instalacion.cargar_clave_guardada(clave, "EMP")
    assert clave.vigente is None and caplog.text == ""


def test_con_solo_el_respaldo_cifrado_la_clave_no_vuelve_sin_contrasena(tmp_path, caplog):
    """Hueco funcional abierto (bitacora 0.9.0, ronda 1 de T15): sin almacen, el respaldo cifrado
    pide una contrasena que ninguna pantalla pide; tras reiniciar, Claude queda sin clave."""
    almacen = AlmacenFalso(cae=True)
    clave = clave_de(tmp_path, con_clave=False, almacen=almacen)
    clave.registrar("EMP", CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo="contrasena larga 1")
    clave.desactivar()  # el reinicio
    with caplog.at_level(logging.WARNING):
        instalacion.cargar_clave_guardada(clave, "EMP")
    assert clave.vigente is None and clave.hay_guardada("EMP") and caplog.text == ""


def test_un_fallo_del_almacen_se_anota_enmascarado_y_no_llega_a_la_pantalla(tmp_path, caplog):
    class AlmacenQueDelata(AlmacenRoto):
        def get_password(self, servicio, usuario):
            raise RuntimeError(f"backend roto con {CLAVE}")

    clave = clave_de(tmp_path, con_clave=False, almacen=AlmacenQueDelata())
    with caplog.at_level(logging.WARNING):
        instalacion.cargar_clave_guardada(clave, "EMP")  # no lanza
    assert clave.vigente is None
    assert "No se pudo cargar la clave de IA guardada" in caplog.text
    assert CLAVE not in caplog.text and "sk-ant-…1234" in caplog.text


def test_los_topes_y_el_proveedor_por_defecto_salen_de_la_configuracion(datos):
    assert instalacion.topes_de_la_instalacion().costo == Decimal(2)  # de fabrica
    assert instalacion.proveedor_por_defecto() == "claude"
    guardar(datos.ruta, ConfiguracionIA(tope_usd=Decimal("3.5"), proveedor="ollama"))
    topes = instalacion.topes_de_la_instalacion()
    assert topes.costo == Decimal("3.5") and topes.turnos == 12 and topes.llamadas == 60
    assert instalacion.proveedor_por_defecto() == "ollama"


def test_la_version_minima_sale_de_config_ia_json(tmp_path):
    ruta = tmp_path / "config_ia.json"
    ruta.write_text('{"estructurado": false, "version_minima_ollama": "0.9.2"}', encoding="utf-8")
    assert instalacion.version_minima_ollama(ruta) == (0, 9, 2)
    assert instalacion.version_minima_ollama() == MINIMA  # la del repositorio
