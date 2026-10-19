"""RV-3, PRU-H15: la base de prueba de la 1.0.0, generada con el codigo de la etiqueta v1.0.0,
abre por `preparar_base` y recarga igual que su ficha (seccion B,
tests/fixtures/bases_prueba.py). No hubo etiqueta v0.9.0: la 1.0.0 es la base que el humo del
instalador actualiza junto con la de la 0.5.0 (spec S5 §11.2 paso 7)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from core import models
from core.budget.cadena import verificar_cadena
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from tests.fixtures.bases_prueba import copiar_base, diferencias_con_ficha, ficha, nombres


def test_la_ficha_es_de_la_etiqueta_v1_0_0() -> None:
    datos = ficha("1.0.0")
    assert (datos["version"], datos["etiqueta"]) == ("1.0.0", "v1.0.0")
    assert datos["commit"] == "5aa3da2006f1211f463e6fa43fc55de5a7cefa1a"
    assert sorted(datos["bases"]) == ["demo.db", "of001.db", "s1.db", "ti001.db"]
    assert {b["revision_alembic"] for b in datos["bases"].values()} == {"caso_0009_s3_paquete"}


@pytest.mark.parametrize("nombre", nombres("1.0.0"))
def test_cada_base_1_0_0_abre_en_head_y_recarga_su_ficha(tmp_path: Path, nombre: str) -> None:
    ruta = copiar_base("1.0.0", nombre, tmp_path / nombre)
    preparar_base(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert diferencias_con_ficha(ruta, ficha("1.0.0")["bases"][nombre]) == []


def test_la_cadena_de_la_base_s1_sigue_integra(tmp_path: Path) -> None:
    """Las versiones de `s1.db` se sellaron con el codigo de la etiqueta (RF-83): el de hoy
    recalcula cada huella y la cadena de cada proyecto cuadra."""
    ruta = copiar_base("1.0.0", "s1.db", tmp_path / "s1.db")
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            proyectos = sesion.scalars(select(models.Proyecto)).all()
            assert proyectos
            for proyecto in proyectos:
                resultado = verificar_cadena(sesion, proyecto)
                assert resultado.integra, (proyecto.nombre, resultado.fallo)
    finally:
        motor.dispose()
