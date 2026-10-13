"""RF-82 en la hoja: con el acceso encendido el responsable es el usuario de la sesión y no hay
cuadro «Responsable» (S3 §3.2, §5.7). Con el acceso apagado (transición, RP8-4) el cuadro sigue y
manda lo escrito (bitácora S3-3, primer PR: tarea 18).

El responsable esperado («Luis <luis>») es el nombre y el login con que `tests/fixtures/paginas_s3`
crea la cuenta, escritos a mano; no se lee de `ui.sesion`."""

from __future__ import annotations

import importlib
import shutil
from pathlib import Path

import pytest
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from core import models
from core.budget.cadena import verificar_cadena
from core.catalog import abrir_sesion, crear_motor
from tests.fixtures.hoja_en_base import NOMBRE_OF001, USUARIO_DE_LA_PLANTILLA, plantilla_of001
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import entrega
from ui import sesion as ui_sesion
from ui.paginas.hoja import (
    CLAVE_FUENTE,
    CLAVE_GENERACION,
    CLAVE_PESTANA,
    CLAVE_PROYECTO,
    CLAVE_RESPONSABLE,
)

SCRIPT = "from ui.paginas.hoja import render\nrender()\n"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_of001(tmp_path_factory.mktemp("resp") / "of001.db")


@pytest.fixture
def base_of(_plantilla, tmp_path, monkeypatch) -> Path:
    copia = tmp_path / "of001.db"
    shutil.copy(_plantilla, copia)
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(copia))
    return copia


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


def _abrir(ficha: str | None = None) -> AppTest:
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_PROYECTO] = NOMBRE_OF001
    at.session_state[CLAVE_PESTANA] = "Parámetros"
    if ficha:
        con_ficha(at, ficha)
    return at.run()


def _leer(base: Path, consulta):
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return consulta(sesion)
    finally:
        motor.dispose()


def _responsables(base: Path) -> list[str]:
    return _leer(base, lambda s: list(s.scalars(select(models.RegistroCambio.responsable))))


def _usuarios_de_los_eslabones(base: Path) -> list[str]:
    from core.models.cadena import EslabonVersion

    return _leer(
        base,
        lambda s: list(
            s.scalars(select(EslabonVersion.usuario).order_by(EslabonVersion.presupuesto_id))
        ),
    )


def _guardar(at: AppTest) -> AppTest:
    generacion = at.session_state[CLAVE_GENERACION]
    at.text_input(key=f"hoja_editor_param_administracion_{generacion}").set_value("0.20").run()
    at.text_input(key=CLAVE_FUENTE).set_value("memoria rev. D").run()
    next(b for b in at.button if b.label == "Guardar version").click().run()
    return at


def test_guardar_registra_al_usuario(monkeypatch, base_of, tmp_path) -> None:
    assert _responsables(base_of) == []  # la plantilla no trae cambios registrados
    ficha = preparar(monkeypatch, tmp_path, "arma", login="luis")
    at = _abrir(ficha)
    assert not at.exception, [e.value for e in at.exception]
    assert CLAVE_RESPONSABLE not in [t.key for t in at.text_input]  # no hay cuadro
    assert any("Responsable: Luis" in c.value for c in at.caption)
    _guardar(at)
    assert not at.exception, [e.value for e in at.exception]
    assert any("Se guardo la version 002" in s.value for s in at.success)
    assert _responsables(base_of) == ["Luis <luis>"]
    # el eslabón de la versión nueva lo sella la misma persona; la 001 es de la plantilla
    assert _usuarios_de_los_eslabones(base_of)[-1] == "Luis <luis>"
    assert _usuarios_de_los_eslabones(base_of)[0] == USUARIO_DE_LA_PLANTILLA


def test_la_cadena_queda_integra_tras_guardar_desde_la_hoja(monkeypatch, base_of, tmp_path):
    ficha = preparar(monkeypatch, tmp_path, "arma", login="luis")
    _guardar(_abrir(ficha))

    def integra(sesion) -> bool:
        proyecto = sesion.scalars(
            select(models.Proyecto).where(models.Proyecto.nombre == NOMBRE_OF001)
        ).one()
        return verificar_cadena(sesion, proyecto, anexos_de=entrega.anexos_de_cadena).integra

    assert _leer(base_of, integra)


def test_lo_que_alguien_escriba_a_mano_no_cambia_al_responsable(monkeypatch, base_of, tmp_path):
    ficha = preparar(monkeypatch, tmp_path, "arma", login="luis")
    at = _abrir(ficha)
    at.session_state[CLAVE_RESPONSABLE] = "Otra Persona <otra>"  # el cuadro ya no existe
    _guardar(at)
    assert not at.exception, [e.value for e in at.exception]
    assert _responsables(base_of) == ["Luis <luis>"]


def test_con_el_acceso_apagado_el_cuadro_de_siempre_sigue_y_manda_lo_escrito(
    monkeypatch, base_of
) -> None:
    monkeypatch.setenv("SILICE_ACCESO", "0")
    at = _abrir()
    assert not at.exception, [e.value for e in at.exception]
    assert CLAVE_RESPONSABLE in [t.key for t in at.text_input]
    at.text_input(key=CLAVE_RESPONSABLE).set_value("Ing. Prueba").run()
    _guardar(at)
    assert not at.exception, [e.value for e in at.exception]
    assert _responsables(base_of) == ["Ing. Prueba"]
