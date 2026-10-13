"""«Solo desde el propio equipo» y el aviso «sin cifrar» (RF-98; spec S5 §8.2).

Incluye el ruling de la bitácora (S5-2 · T9, T10 y T12): `st.context.ip_address` de Streamlit
1.62 devuelve `None` para el bucle local, así que `ui.cliente` lo lee como `127.0.0.1`; «no se
pudo leer» (una excepción o un valor que no es texto) se trata como remoto salvo con la red
local apagada.
"""

from __future__ import annotations

import ast
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from operacion import config, red
from tests.fixtures.arquitectura import RAIZ, archivos, ruta
from ui import cliente


@pytest.fixture
def con_red_local() -> None:
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="192.168.1.20")
    )


class _ContextoQueFalla:
    @property
    def ip_address(self) -> str:
        raise RuntimeError("sin contexto de cliente")


@pytest.mark.parametrize(
    ("contexto", "esperada"),
    [
        (SimpleNamespace(ip_address=None), "127.0.0.1"),  # bucle local según Streamlit 1.62
        (SimpleNamespace(ip_address="192.168.1.30"), "192.168.1.30"),
        (SimpleNamespace(ip_address=b"192.168.1.30"), None),  # no es texto: ilegible
        (SimpleNamespace(), None),  # sin el atributo
        (_ContextoQueFalla(), None),
    ],
)
def test_ip_del_cliente_sigue_el_ruling_de_streamlit(monkeypatch, contexto, esperada) -> None:
    monkeypatch.setattr(cliente, "st", SimpleNamespace(context=contexto))
    assert cliente.ip_del_cliente() == esperada


@pytest.mark.parametrize(
    ("ip", "esperado"),
    [
        ("127.0.0.1", True),
        ("::1", True),
        ("192.168.1.20", True),
        ("192.168.1.30", False),
        ("8.8.8.8", False),
    ],
)
def test_con_la_red_encendida_solo_cuentan_el_bucle_y_la_ip_elegida(
    monkeypatch, con_red_local, ip: str, esperado: bool
) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: ip)
    assert cliente.cliente_es_local() is esperado


def test_con_la_red_apagada_la_ip_guardada_no_cuenta_como_propia(monkeypatch) -> None:
    """Con la red apagada nadie de la red llega; aun así, una IP que no es de bucle no es «el
    propio equipo» aunque coincida con una dirección vieja."""
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: "192.168.1.20")
    assert cliente.cliente_es_local() is False


def test_si_no_se_puede_leer_la_ip_solo_es_local_con_la_red_apagada(monkeypatch) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: None)
    assert cliente.cliente_es_local() is True  # red apagada: solo el propio equipo puede llegar
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="192.168.1.20")
    )
    assert cliente.cliente_es_local() is False


def test_un_silice_toml_danado_se_lee_con_la_red_apagada(monkeypatch) -> None:
    ruta = config.ruta_ajustes()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("[servidor\nred_local = true", encoding="utf-8")
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: None)
    assert cliente.cliente_es_local() is True


def test_una_operacion_sensible_se_rechaza_desde_una_ip_remota(monkeypatch, con_red_local) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: "192.168.1.30")
    permitida, motivo = cliente.operacion_sensible_permitida()
    assert permitida is False and motivo == cliente.MENSAJE_REMOTO


def test_una_operacion_sensible_se_bloquea_con_eventos_sin_revisar(monkeypatch) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: "127.0.0.1")
    assert cliente.operacion_sensible_permitida() == (True, "")
    pendiente = config.carpeta_datos() / "eventos_perdidos_20261011-090000.json"
    pendiente.parent.mkdir(parents=True, exist_ok=True)
    pendiente.write_text('{"revisado": false}', encoding="utf-8")
    assert cliente.operacion_sensible_permitida() == (False, cliente.MENSAJE_PENDIENTE)


def test_remota_y_con_pendientes_manda_el_motivo_remoto(monkeypatch, con_red_local) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: "192.168.1.30")
    pendiente = config.carpeta_datos() / "eventos_perdidos_20261011-090000.json"
    pendiente.parent.mkdir(parents=True, exist_ok=True)
    pendiente.write_text('{"revisado": false}', encoding="utf-8")
    assert cliente.operacion_sensible_permitida() == (False, cliente.MENSAJE_REMOTO)


def _aviso() -> None:
    from ui import cliente as c

    c.pintar_aviso_sin_cifrar()


@pytest.mark.parametrize(
    ("ip", "visible"), [("192.168.1.30", True), ("192.168.1.20", False), ("127.0.0.1", False)]
)
def test_el_cliente_remoto_ve_el_aviso_sin_cifrar(monkeypatch, con_red_local, ip, visible) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: ip)
    at = AppTest.from_function(_aviso).run()
    assert not at.exception
    assert [e.value for e in at.warning] == ([red.AVISO_ACCESO] if visible else [])


def _aviso_a_una_ip_publica() -> None:
    from ui import cliente as c

    c.pintar_aviso_sin_cifrar("8.8.8.8")


def test_el_aviso_con_ip_explicita_no_lee_streamlit(monkeypatch, con_red_local) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: pytest.fail("no debe leer la IP"))
    at = AppTest.from_function(_aviso_a_una_ip_publica).run()
    assert not at.exception
    assert [e.value for e in at.warning] == [red.AVISO_ACCESO]


def _crear_clave_de_api() -> None:
    import streamlit as st

    from seguridad.permisos import Sensible
    from ui import sesion

    sesion.exigir_local(Sensible.CLAVE_DE_API)
    st.success("clave creada")


@pytest.mark.parametrize(("ip", "creada"), [("192.168.1.30", False), ("127.0.0.1", True)])
def test_crear_una_clave_de_api_desde_una_ip_remota_se_rechaza(
    monkeypatch, con_red_local, ip: str, creada: bool
) -> None:
    """RF-98 (spec §12): la guardia de lo sensible de S3 pasa por `ui.cliente`."""
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: ip)
    at = AppTest.from_function(_crear_clave_de_api).run()
    assert not at.exception
    assert [e.value for e in at.error] == ([] if creada else [cliente.MENSAJE_REMOTO])
    assert [s.value for s in at.success] == (["clave creada"] if creada else [])


def test_administracion_exige_el_propio_equipo_antes_de_crear_una_clave_de_api() -> None:
    fuente = (RAIZ / "ui" / "paginas" / "administracion.py").read_text(encoding="utf-8")
    for funcion in ast.walk(ast.parse(fuente)):
        if not isinstance(funcion, ast.FunctionDef):
            continue
        texto = ast.unparse(funcion)
        if "claves_api.crear(" in texto:
            assert "exigir_local(Sensible.CLAVE_DE_API)" in texto, funcion.name
            assert texto.index("exigir_local(Sensible.CLAVE_DE_API)") < texto.index(
                "claves_api.crear("
            )
            return
    pytest.fail("administracion.py no crea claves de API: ¿se movió la pantalla?")


def test_ningun_modulo_de_ui_ni_api_llama_a_es_local_de_seguridad_directamente() -> None:
    infractores = []
    for paquete in ("ui", "api"):
        for archivo in archivos(paquete):
            for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
                usa_import = isinstance(nodo, ast.ImportFrom) and nodo.module == "seguridad.red"
                usa_llamada = (
                    isinstance(nodo, ast.Call)
                    and isinstance(nodo.func, (ast.Name, ast.Attribute))
                    and ast.unparse(nodo.func)
                    in {"es_local", "red.es_local", "seguridad.red.es_local"}
                )
                if usa_import or usa_llamada:
                    infractores.append(f"{ruta(archivo)}:{nodo.lineno}")
    assert infractores == []


def test_la_pantalla_de_acceso_de_s3_usa_el_aviso_de_s5() -> None:
    assert "pintar_aviso_sin_cifrar" in (RAIZ / "ui" / "acceso.py").read_text(encoding="utf-8")
