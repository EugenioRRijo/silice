"""RV-3, PRU-H15: la base de prueba de la 0.6.0, generada con el codigo de la etiqueta v0.6.0,
abre por `preparar_base` y recarga igual que su ficha (seccion B,
tests/fixtures/bases_prueba.py)."""

from __future__ import annotations

from decimal import Decimal as D  # noqa: N817
from pathlib import Path

import pytest
from sqlalchemy import select

from core import models
from core.budget.reajuste import cargar_estudio
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from tests.fixtures.bases_prueba import copiar_base, diferencias_con_ficha, ficha, nombres


def test_la_ficha_es_de_la_etiqueta_v0_6_0() -> None:
    datos = ficha("0.6.0")
    assert (datos["version"], datos["etiqueta"]) == ("0.6.0", "v0.6.0")
    assert sorted(datos["bases"]) == ["demo.db", "of001.db", "s1.db", "ti001.db"]
    assert {b["revision_alembic"] for b in datos["bases"].values()} == {"caso_0004_s1_reajuste"}


@pytest.mark.parametrize("nombre", nombres("0.6.0"))
def test_cada_base_0_6_0_abre_en_head_y_recarga_su_ficha(tmp_path: Path, nombre: str) -> None:
    ruta = copiar_base("0.6.0", nombre, tmp_path / nombre)
    preparar_base(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert diferencias_con_ficha(ruta, ficha("0.6.0")["bases"][nombre]) == []


def test_el_estudio_de_la_base_s1_recalcula_igual(tmp_path: Path) -> None:
    ruta = copiar_base("0.6.0", "s1.db", tmp_path / "s1.db")
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            estudio = sesion.scalars(select(models.EstudioReajuste)).one()
            assert cargar_estudio(sesion, estudio.id).resultado.total_escalatoria == D("15300")
    finally:
        motor.dispose()
