"""El gancho `lifespan` de `api.main` (BCP-1; B23 y P-1 del diseño §10.2).

Al arrancar la API, sin cuentas y sin `codigo_instalacion.txt`, se emite el código de instalación
(el camino de desarrollo, `uvicorn api.main:app`, y el de un archivo borrado). Con cuentas, o con el
archivo ya escrito, no se hace nada. Un fallo se registra sin el código y no impide servir.

Oráculos a mano: el archivo es `XXXX-XXXX-XXXX-XXXX-XXXX` + salto de línea (25 caracteres), solo el
alfabeto base32; la base guarda una fila por código y una sola vigente; solo hay UN `lifespan`.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from api import main
from api.main import app
from operacion import config, primer_arranque
from operacion.instalacion import cerrar_motores, sesion_de_instalacion
from seguridad.modelo import CodigoInstalacion
from tests.fixtures.claves_api import ANFITRION
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

FORMATO = re.compile(r"^(?:[A-Z2-7]{4}-){4}[A-Z2-7]{4}\n$")


@pytest.fixture(autouse=True)
def _motores_cerrados():
    yield
    cerrar_motores()


def _archivo() -> Path:
    return config.carpeta_datos() / "codigo_instalacion.txt"


def _filas() -> tuple[int, int]:
    with sesion_de_instalacion() as sesion:
        total = sesion.scalar(select(func.count()).select_from(CodigoInstalacion))
        vigentes = sesion.scalar(
            select(func.count())
            .select_from(CodigoInstalacion)
            .where(CodigoInstalacion.usado.is_(None))
        )
    return total, vigentes


def _arrancar() -> None:
    with TestClient(app, base_url=ANFITRION, client=("127.0.0.1", 50000)) as cliente:
        assert cliente.get("/salud").json() == {"estado": "ok"}


def test_arrancar_la_api_sin_cuentas_emite_el_codigo() -> None:
    assert not _archivo().exists()
    _arrancar()
    assert FORMATO.fullmatch(_archivo().read_text(encoding="ascii"))
    assert _filas() == (1, 1)


def test_arrancar_dos_veces_no_cambia_el_codigo() -> None:
    _arrancar()
    primero = _archivo().read_bytes()
    _arrancar()
    _arrancar()
    assert _archivo().read_bytes() == primero
    assert _filas() == (1, 1)


def test_si_se_borro_el_archivo_se_emite_otro_y_solo_el_ultimo_sirve() -> None:
    _arrancar()
    viejo = _archivo().read_bytes()
    _archivo().unlink()
    _arrancar()
    assert FORMATO.fullmatch(_archivo().read_text(encoding="ascii"))
    assert _archivo().read_bytes() != viejo
    assert _filas() == (2, 1)


def test_con_cuentas_no_emite_nada(tmp_path_factory) -> None:
    copiar_instalacion(plantilla_con_cuentas(tmp_path_factory.mktemp("lifespan_cuentas")))
    _arrancar()
    assert not _archivo().exists()
    assert _filas() == (1, 0)  # solo el código que usó el primer administrador de la plantilla


def test_un_fallo_se_registra_sin_el_codigo_y_no_impide_servir(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    secreto = "ZZZZ-ZZZZ-ZZZZ-ZZZZ-ZZZZ"

    def falla(*_args, **_kwargs) -> bool:
        raise RuntimeError("la base se rompió: " + "no hay código aquí")

    monkeypatch.setattr(primer_arranque, "asegurar_codigo", falla)
    caplog.set_level(logging.DEBUG)
    _arrancar()  # el servidor sirve igual
    mensajes = [r for r in caplog.records if r.name == "silice.api"]
    assert any("no se pudo preparar el primer arranque" in r.getMessage() for r in mensajes)
    assert secreto not in caplog.text and not _archivo().exists()


def test_la_api_tiene_un_solo_lifespan() -> None:
    """RULING: un solo gancho; otros (el `apagar()` del asistente) se registran en él."""
    assert main._arranque.__name__ == "_arranque"
    # el `on_startup` del router de planos (barrido de temporales) convive, fusionado por FastAPI
    assert [f.__name__ for f in app.router.on_startup] == ["barrer_al_arrancar"]
    assert app.router.on_shutdown == []
