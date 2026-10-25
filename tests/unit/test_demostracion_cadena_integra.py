"""D3 del recorrido funcional: toda demostración nace con su cadena de sellos íntegra.

`start.py` copia bases de antes de la cadena (`tests/fixtures/bases/v0_6_0`); sin sellarlas,
«Entregar paquete» decía «Cadena rota… no tiene eslabón» y no dejaba generar el paquete. Aquí se
siembra en una carpeta temporal y se exige, por proyecto, cadena íntegra, sellado en formato actual
(VB-1: cifras a 28 decimales) y que la función que usa la ruta de entregas acepte cada versión.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select

import start
from aplicacion import entrega
from core import models
from core.budget import cadena
from core.catalog import abrir_sesion, crear_motor
from tests.fixtures.instalacion import instalacion

CUANDO = datetime(2026, 11, 10, 9, 30)
# Oráculo a mano: los cinco casos que `preparar_demo` deja en la carpeta de casos.
CASOS = ("demo", "of001", "ti001", "s1", "obra_control")


def _verificar_todo(ruta: Path, tmp_path: Path) -> int:
    """Comprueba cada proyecto y versión de la base; devuelve cuántas versiones entregó."""
    motor = crear_motor(f"sqlite:///{ruta.resolve().as_posix()}")
    entregadas = 0
    try:
        with abrir_sesion(motor) as caso, instalacion(tmp_path / f"emisor_{ruta.stem}") as bd:
            proyectos = list(caso.scalars(select(models.Proyecto)))
            assert proyectos, f"{ruta.name} no trae proyectos"
            for proyecto in proyectos:
                resultado = cadena.verificar_cadena(
                    caso, proyecto, anexos_de=entrega.anexos_de_cadena
                )
                assert resultado.integra, cadena.mensaje_de_cadena(resultado)
                for version in proyecto.presupuestos:
                    assert cadena.formato_de_sellado(caso, version) == "actual"
                    paquete = entrega.entregar(
                        caso,
                        bd,
                        version,
                        usuario="Ana Pérez <ana>",
                        ahora=CUANDO,
                        version_silice="0.8.0",
                    )
                    assert paquete.datos
                    entregadas += 1
    finally:
        motor.dispose()
    assert entregadas >= 1, f"{ruta.name} no trae ninguna versión"
    return entregadas


@pytest.fixture
def datos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path / "datos"))
    monkeypatch.setenv("SILICE_RESPALDOS", str(tmp_path / "respaldos"))
    return tmp_path


def test_preparar_demo_deja_cadena_integra_y_entregable_en_cada_caso(datos: Path) -> None:
    sembrados = start.preparar_demo()
    assert sorted(sembrados) == sorted(CASOS)
    for nombre in CASOS:
        assert _verificar_todo(start.carpeta_casos() / f"{nombre}.db", datos) >= 1, nombre


def test_la_demo_de_start_tiene_su_version_demo_001_entregable(datos: Path) -> None:
    start.preparar_demo()
    ruta = start.carpeta_casos() / "demo.db"
    with closing(sqlite3.connect(ruta)) as con:
        codigos = {f[0] for f in con.execute("select codigo from presupuesto")}
    assert "DEMO-001" in codigos
    assert _verificar_todo(ruta, datos) == len(codigos)


def test_la_orden_demostracion_deja_cadena_integra_y_entregable(datos: Path) -> None:
    from operacion import ordenes_100

    salida = datos / "salida.db"
    argumentos = type("A", (), {"salida": str(salida)})()
    assert ordenes_100._demostracion(argumentos) == 0
    assert _verificar_todo(salida, datos) >= 1
