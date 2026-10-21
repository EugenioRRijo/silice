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
