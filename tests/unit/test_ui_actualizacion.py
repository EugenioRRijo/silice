"""UC-02 7a en la interfaz (INV-015): el boton marca la version y conserva el historial."""

from __future__ import annotations

import importlib
from datetime import date
from pathlib import Path

from pandas import DataFrame
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from core import models
from core.budget import actualizar_precios, elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import (
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
)
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.conftest import RUTA_BASE_REAL, huella
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import PRECIOS_NUEVOS
from tests.fixtures.computo_auditado import items_auditados

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
SCRIPT = "from ui.paginas.actualizacion import render\nrender()\n"
CODIGO_NUEVO = "002"


def _base_con_version_nueva(ruta: Path) -> None:
    """001 guardado y 002 revalorado con la muestra, ambos confirmados, por el nucleo directo."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            catalogo = Catalogo(sesion)
            codigos = [apu.codigo_partida for apu in linea_base.APUS_LINEA_BASE]
            resultado = elaborar(
                items_auditados(),
                catalogo.composiciones(codigos, fecha=linea_base.FECHA_LINEA_BASE),
                linea_base.PARAMETROS_LINEA_BASE,
                codigo=linea_base.CODIGO_PRESUPUESTO,
                fecha=linea_base.FECHA_LINEA_BASE,
                moneda=linea_base.MONEDA,
                plan=plan_secuencial,
            )
            guardar_presupuesto(
                sesion,
                resultado.presupuesto,
                resultado.informe,
                proyecto=proyecto,
                lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
                parametros=linea_base.PARAMETROS_LINEA_BASE,
            )
            lista = crear_lista_desde_archivo(
                sesion,
                MUESTRA,
                nombre="Lista 01/06/2026",
                moneda=linea_base.MONEDA,
                fecha_vigencia=date(2026, 6, 1),
                origen=MUESTRA.name,
            )
            actualizar_precios(
                sesion, NOMBRE_PROYECTO, linea_base.CODIGO_PRESUPUESTO, lista.lista, CODIGO_NUEVO
            )
            sesion.commit()
    finally:
        motor.dispose()


def _contar(ruta: Path, entidad) -> int:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return len(sesion.scalars(select(entidad)).all())
    finally:
        motor.dispose()


def test_descartar_version_marca_la_version_y_conserva_el_historial(monkeypatch, tmp_path):
    base = tmp_path / "caso.db"
    _base_con_version_nueva(base)
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    pagina = importlib.import_module("ui.paginas.actualizacion")
    antes = huella(RUTA_BASE_REAL)

    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.session_state[pagina.CLAVE_RESULTADO] = pagina.Presentacion(
        tabla=DataFrame(),
        resumen="",
        informe="",
        desconocidos=(),
        libro=b"",
        nombre_libro="presupuesto_002.xlsx",
        proyecto=NOMBRE_PROYECTO,
        version_guardada=CODIGO_NUEVO,
    )
    at.run()
    boton = next(b for b in at.button if b.label == "Descartar version")
    boton.click().run()

    assert not at.exception
    assert _contar(base, models.DescarteVersion) == 1
    assert _contar(base, models.CambioPrecio) == len(PRECIOS_NUEVOS)
    assert huella(RUTA_BASE_REAL) == antes


def test_sin_version_guardada_no_hay_boton_de_descartar(monkeypatch, tmp_path):
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "vacio.db"))
    pagina = importlib.import_module("ui.paginas.actualizacion")

    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.session_state[pagina.CLAVE_RESULTADO] = pagina.Presentacion(
        tabla=DataFrame(),
        resumen="",
        informe="",
        desconocidos=(),
        libro=b"",
        nombre_libro="presupuesto_002.xlsx",
        proyecto=NOMBRE_PROYECTO,
        version_guardada=None,
    )
    at.run()

    assert not at.exception
    assert "Descartar version" not in [b.label for b in at.button]
