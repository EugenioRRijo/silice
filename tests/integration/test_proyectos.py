"""UC-01, paso 1 (INV-086, expediente C6.3): el proyectista crea el proyecto.

`docs/ERS.md` UC-01 1: «El proyectista crea el proyecto y selecciona la fuente de cantidades y su
dominio». `crear_proyecto` es la unica via fuera de los sembradores; sobre el proyecto creado se
guarda el presupuesto de la linea base (oraculo: su total exacto de la fixture).
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from core import models
from core.budget import cargar_presupuesto, crear_proyecto
from core.catalog import Catalogo
from core.contracts import Dominio
from scripts.seed import NOMBRE_PROYECTO
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.base_con_pendiente import elaborar_en, guardar_en
from tests.fixtures.computo_auditado import items_auditados

NOMBRE = "Ampliacion del drenaje"


def _contar_proyectos(sesion) -> int:
    return sesion.scalar(select(func.count()).select_from(models.Proyecto))


def test_crear_el_proyecto_y_guardar_sobre_el(sesion):
    proyecto = crear_proyecto(
        sesion, f"  {NOMBRE}  ", descripcion="Segunda etapa", dominio=Dominio.CIVIL
    )

    guardado = sesion.scalars(select(models.Proyecto).where(models.Proyecto.nombre == NOMBRE)).one()
    assert guardado is proyecto
    assert (guardado.descripcion, guardado.dominio) == ("Segunda etapa", "civil")

    guardar_en(sesion, proyecto, elaborar_en(sesion, items_auditados()))
    recargado = cargar_presupuesto(sesion, NOMBRE, linea_base.CODIGO_PRESUPUESTO, Catalogo(sesion))
    assert recargado.total == linea_base.TOTAL_EXACTO_LINEA_BASE


def test_dominio_opcional(sesion):
    assert crear_proyecto(sesion, NOMBRE).dominio == ""


@pytest.mark.parametrize(
    ("nombre", "dominio", "patron"),
    [
        (NOMBRE_PROYECTO, "", "ya existe"),
        (f" {NOMBRE_PROYECTO} ", "", "ya existe"),
        ("", "", "vacio"),
        ("   ", "", "vacio"),
        (NOMBRE, "naval", "dominio"),
    ],
)
def test_nombre_repetido_o_vacio_o_dominio_desconocido(sesion, nombre, dominio, patron):
    antes = _contar_proyectos(sesion)

    with pytest.raises(ValueError, match=patron):
        crear_proyecto(sesion, nombre, dominio=dominio)

    assert _contar_proyectos(sesion) == antes
