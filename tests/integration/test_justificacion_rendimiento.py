"""UC-06, flujo 4a (INV-093, expediente C6.1): la justificacion de la advertencia de rendimiento.

`docs/ERS.md` UC-06 4a: «El proyectista acepta la advertencia: se registra su justificacion junto
al APU». La justificacion vive en la tabla aditiva `justificacion_rendimiento`, ligada al ultimo
rendimiento registrado de la partida; una base creada antes de C6 la gana con `crear_esquema` sin
perder sus filas. Oraculos: la siembra de la linea base (un rendimiento ESTIMADO por partida, 80
m3/dia en la excavacion) y los valores que registra cada prueba.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, inspect, select

from core import models
from core.catalog import (
    abrir_sesion,
    advertencia_rendimiento,
    crear_esquema,
    crear_motor,
    dispersion_rendimientos,
    justificar_rendimiento,
    registrar_rendimiento,
)
from core.contracts.apu import TipoRendimiento
from scripts.seed import sembrar
from tests.fixtures import apu_linea_base as linea_base

EXCAVACION = linea_base.APU_EXCAVACION.codigo_partida
FECHA = date(2026, 7, 1)
TEXTO = "terreno rocoso en el tramo norte: se acepta el rendimiento bajo"


def _contar(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


def _rendimientos_de(sesion, codigo: str) -> list[models.Rendimiento]:
    return list(
        sesion.scalars(
            select(models.Rendimiento)
            .join(models.Partida)
            .where(models.Partida.codigo == codigo)
            .order_by(models.Rendimiento.id)
        )
    )


def _registrar_con_advertencia(sesion) -> str:
    """Dos rendimientos mas (80 sembrado, 75, 85) y un cuarto, 20, fuera del rango [75, 85].

    Devuelve la advertencia de RF-27 que el cuarto dispara contra lo observado antes de el.
    """
    for valor in ("75", "85"):
        registrar_rendimiento(
            sesion, EXCAVACION, valor=Decimal(valor), tipo=TipoRendimiento.ESTIMADO, fecha=FECHA
        )
    advertencia = advertencia_rendimiento(dispersion_rendimientos(sesion, EXCAVACION), Decimal(20))
    assert advertencia is not None, "20 m3/dia debe apartarse del rango [75, 85]"
    registrar_rendimiento(
        sesion, EXCAVACION, valor=Decimal("20"), tipo=TipoRendimiento.ESTIMADO, fecha=FECHA
    )
    return advertencia


def test_la_justificacion_queda_ligada_al_ultimo_rendimiento(sesion):
    advertencia = _registrar_con_advertencia(sesion)

    justificacion = justificar_rendimiento(sesion, EXCAVACION, TEXTO, advertencia, FECHA)

    rendimientos = _rendimientos_de(sesion, EXCAVACION)
    assert [r.valor for r in rendimientos] == [Decimal(80), Decimal(75), Decimal(85), Decimal(20)]
    guardada = sesion.get(models.JustificacionRendimiento, rendimientos[-1].id)
    assert guardada is justificacion
    assert (guardada.texto, guardada.advertencia, guardada.fecha) == (TEXTO, advertencia, FECHA)
    assert guardada.rendimiento.valor == Decimal(20)
    for anterior in rendimientos[:-1]:
        assert sesion.get(models.JustificacionRendimiento, anterior.id) is None
    assert _contar(sesion, models.JustificacionRendimiento) == 1


@pytest.mark.parametrize(
    ("texto", "advertencia", "patron"),
    [
        ("", "se aparta", "justificacion"),
        ("   ", "se aparta", "justificacion"),
        (TEXTO, "", "advertencia"),
    ],
)
def test_texto_o_advertencia_vacios_se_rechazan(sesion, texto, advertencia, patron):
    _registrar_con_advertencia(sesion)

    with pytest.raises(ValueError, match=patron):
        justificar_rendimiento(sesion, EXCAVACION, texto, advertencia, FECHA)

    assert _contar(sesion, models.JustificacionRendimiento) == 0


def test_un_rendimiento_ya_justificado_se_rechaza(sesion):
    advertencia = _registrar_con_advertencia(sesion)
    justificar_rendimiento(sesion, EXCAVACION, TEXTO, advertencia, FECHA)

    with pytest.raises(ValueError, match="ya tiene justificacion"):
        justificar_rendimiento(sesion, EXCAVACION, "otra razon", advertencia, FECHA)

    assert _contar(sesion, models.JustificacionRendimiento) == 1


def test_partida_sin_rendimientos_o_inexistente(sesion):
    sin_rendimientos = models.Partida(
        codigo="C6-SIN-REND", descripcion="Partida sin rendimientos", unidad="m3", dominio="civil"
    )
    sesion.add(sin_rendimientos)
    sesion.flush()

    with pytest.raises(LookupError, match="no tiene rendimientos"):
        justificar_rendimiento(sesion, "C6-SIN-REND", TEXTO, "se aparta", FECHA)
    with pytest.raises(KeyError):
        justificar_rendimiento(sesion, "NO-EXISTE", TEXTO, "se aparta", FECHA)
    assert _contar(sesion, models.JustificacionRendimiento) == 0


def test_una_base_anterior_gana_la_tabla_y_conserva_sus_filas(tmp_path):
    """GC6: una base de antes de C6 (dieciseis tablas) se abre, gana la tabla y no pierde nada."""
    motor = crear_motor(f"sqlite:///{(tmp_path / 'anterior.db').as_posix()}")
    try:
        anteriores = [
            t for t in models.Base.metadata.sorted_tables if t.name != "justificacion_rendimiento"
        ]
        models.Base.metadata.create_all(motor, tables=anteriores)
        assert "justificacion_rendimiento" not in inspect(motor).get_table_names()
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
            antes = (_contar(sesion, models.Partida), _contar(sesion, models.Rendimiento))

        crear_esquema(motor)

        assert "justificacion_rendimiento" in inspect(motor).get_table_names()
        with abrir_sesion(motor) as sesion:
            despues = (_contar(sesion, models.Partida), _contar(sesion, models.Rendimiento))
            assert despues == antes == (len(linea_base.APUS_LINEA_BASE),) * 2
            justificar_rendimiento(sesion, EXCAVACION, TEXTO, "se aparta", FECHA)
            sesion.commit()
            assert _contar(sesion, models.JustificacionRendimiento) == 1
        (clave,) = inspect(motor).get_foreign_keys("justificacion_rendimiento")
        assert clave["referred_table"] == "rendimiento"
        assert clave["options"].get("ondelete") == "CASCADE"
    finally:
        motor.dispose()


def test_borrar_el_rendimiento_borra_su_justificacion(sesion):
    """`ondelete="CASCADE"` por comportamiento, con el `PRAGMA foreign_keys=ON` de `crear_motor`."""
    advertencia = _registrar_con_advertencia(sesion)
    justificar_rendimiento(sesion, EXCAVACION, TEXTO, advertencia, FECHA)
    sesion.commit()
    assert sesion.connection().exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1

    sesion.delete(_rendimientos_de(sesion, EXCAVACION)[-1])
    sesion.commit()
    sesion.expunge_all()

    assert _contar(sesion, models.JustificacionRendimiento) == 0
    assert len(_rendimientos_de(sesion, EXCAVACION)) == 3
