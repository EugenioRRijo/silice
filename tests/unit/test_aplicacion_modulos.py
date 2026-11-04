"""`aplicacion.modulos`: el estado de los módulos de una instalación (plan vial, Tarea 19).

Base de instalación en memoria. Oráculos a mano: sin ninguna fila, los cuatro módulos están activos;
cada cambio es una fila nueva (nada se sobrescribe) y vale la última de cada clave.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from aplicacion.modulos import (
    MENSAJE_APAGADO,
    MODULOS,
    ModuloDesconocido,
    cambios_de,
    fijar_modulo,
    modulos_activos,
    nombre_de,
)
from aplicacion.tablas_modulos import METADATA_MODULOS, FilaModulo

LUNES = datetime(2026, 10, 26, 8, 0)
MARTES = datetime(2026, 10, 27, 9, 30)


@pytest.fixture
def sesion() -> Session:
    motor = create_engine("sqlite://")
    METADATA_MODULOS.create_all(motor)
    with Session(motor) as s:
        yield s
    motor.dispose()


def test_los_modulos_son_cuatro_y_estan_en_este_orden() -> None:
    assert MODULOS == ("produccion", "vial", "edificacion", "riesgo")


def test_sin_filas_todos_estan_activos(sesion: Session) -> None:
    assert modulos_activos(sesion) == frozenset(MODULOS)


def test_apagar_uno_deja_los_otros_tres(sesion: Session) -> None:
    fijar_modulo(sesion, "vial", False, usuario="admin", ahora=LUNES)
    assert modulos_activos(sesion) == frozenset({"produccion", "edificacion", "riesgo"})


def test_encender_vuelve_a_dejarlo_activo_y_el_historial_conserva_los_dos_cambios(
    sesion: Session,
) -> None:
    fijar_modulo(sesion, "vial", False, usuario="admin", ahora=LUNES)
    fijar_modulo(sesion, "vial", True, usuario="otro", ahora=MARTES)
    assert "vial" in modulos_activos(sesion)
    assert sesion.scalar(select(func.count()).select_from(FilaModulo)) == 2
    historial = cambios_de(sesion, "vial")
    assert [(c.activo, c.usuario, c.registrado) for c in historial] == [
        (False, "admin", LUNES),
        (True, "otro", MARTES),
    ]


def test_un_cambio_en_el_mismo_instante_gana_el_ultimo_registrado(sesion: Session) -> None:
    fijar_modulo(sesion, "riesgo", False, usuario="a", ahora=LUNES)
    fijar_modulo(sesion, "riesgo", True, usuario="b", ahora=LUNES)
    assert "riesgo" in modulos_activos(sesion)


def test_una_clave_desconocida_se_rechaza_y_no_guarda_nada(sesion: Session) -> None:
    with pytest.raises(ModuloDesconocido):
        fijar_modulo(sesion, "astronomia", False, usuario="admin", ahora=LUNES)
    assert sesion.scalar(select(func.count()).select_from(FilaModulo)) == 0


def test_el_mensaje_de_dv4_lleva_el_nombre_del_modulo() -> None:
    assert MENSAJE_APAGADO.format(nombre=nombre_de("vial")) == (
        "El módulo vial está apagado en esta instalación."
    )
    assert nombre_de("produccion") == "producción"
