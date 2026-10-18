"""Servicio de inventario de la arenera. Serie de ARENA: ejemplo construido, oraculo a mano."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from produccion.inventario import (
    ErrorDeInventario,
    crear_material,
    existencia,
    registrar_ajuste_por_conteo,
    registrar_despacho,
    registrar_entrada,
    tablero,
)
from produccion.modelo import METADATA_PRODUCCION

D = Decimal
USUARIO = "prueba"


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    with Session(motor) as s:
        yield s
    motor.dispose()


def _arena(sesion: Session) -> int:
    m = crear_material(
        sesion,
        codigo="ARENA",
        nombre="Arena lavada",
        unidad_venta="m3",
        existencia_minima=D("20"),
    )
    return m.id


def _serie(sesion: Session, mid: int) -> None:
    registrar_entrada(sesion, mid, date(2026, 10, 1), D("100"), usuario=USUARIO)
    registrar_despacho(sesion, mid, date(2026, 10, 2), D("30"), usuario=USUARIO)
    registrar_despacho(sesion, mid, date(2026, 10, 3), D("45.5"), usuario=USUARIO)
    registrar_entrada(sesion, mid, date(2026, 10, 4), D("10"), usuario=USUARIO)


def test_existencia_por_fecha_con_la_serie_a_mano(sesion: Session) -> None:
    mid = _arena(sesion)
    _serie(sesion, mid)
    ajuste = registrar_ajuste_por_conteo(sesion, mid, date(2026, 10, 5), D("40"), usuario=USUARIO)
    assert existencia(sesion, mid, date(2026, 10, 1)) == D("100")
    assert existencia(sesion, mid, date(2026, 10, 2)) == D("70")
    assert existencia(sesion, mid, date(2026, 10, 3)) == D("24.5")
    assert existencia(sesion, mid, date(2026, 10, 4)) == D("34.5")
    assert ajuste is not None
    assert ajuste.cantidad == D("5.5")
    assert existencia(sesion, mid, date(2026, 10, 5)) == D("40")
    assert existencia(sesion, mid) == D("40")


def test_el_ajuste_guarda_la_diferencia_con_signo(sesion: Session) -> None:
    mid = _arena(sesion)
    _serie(sesion, mid)
    ajuste = registrar_ajuste_por_conteo(sesion, mid, date(2026, 10, 5), D("20"), usuario=USUARIO)
    assert ajuste is not None
    assert ajuste.tipo == "ajuste"
    assert ajuste.cantidad == D("-14.5")
    assert existencia(sesion, mid) == D("20")


def test_conteo_igual_a_lo_teorico_no_crea_ajuste(sesion: Session) -> None:
    mid = _arena(sesion)
    _serie(sesion, mid)
    assert (
        registrar_ajuste_por_conteo(sesion, mid, date(2026, 10, 5), D("34.5"), usuario=USUARIO)
        is None
    )
    assert existencia(sesion, mid) == D("34.5")


def test_queda_poco_incluye_el_minimo_exacto(sesion: Session) -> None:
    mid = _arena(sesion)
    registrar_entrada(sesion, mid, date(2026, 10, 1), D("20"), usuario=USUARIO)
    fila = tablero(sesion)[0]
    assert fila.existencia == D("20")
    assert fila.minima == D("20")
    assert fila.queda_poco is True
    assert fila.negativa is False
    registrar_entrada(sesion, mid, date(2026, 10, 2), D("0.5"), usuario=USUARIO)
    assert tablero(sesion)[0].queda_poco is False


def test_despacho_que_deja_negativo_se_registra_y_marca(sesion: Session) -> None:
    """RT-S4-2: un despacho nunca se bloquea."""
    mid = _arena(sesion)
    registrar_entrada(sesion, mid, date(2026, 10, 1), D("10"), usuario=USUARIO)
    mov = registrar_despacho(sesion, mid, date(2026, 10, 2), D("24.5"), usuario=USUARIO)
    assert mov.id is not None
    assert existencia(sesion, mid) == D("-14.5")
    fila = tablero(sesion)[0]
    assert fila.negativa is True
    assert fila.queda_poco is True


def test_cantidad_cero_o_negativa_se_rechaza(sesion: Session) -> None:
    mid = _arena(sesion)
    for mala in (D("0"), D("-1")):
        with pytest.raises(ErrorDeInventario, match="mayor que cero"):
            registrar_entrada(sesion, mid, date(2026, 10, 1), mala, usuario=USUARIO)
        with pytest.raises(ErrorDeInventario, match="mayor que cero"):
            registrar_despacho(sesion, mid, date(2026, 10, 1), mala, usuario=USUARIO)
    assert existencia(sesion, mid) == D("0")


def test_codigo_repetido_se_rechaza(sesion: Session) -> None:
    _arena(sesion)
    with pytest.raises(ErrorDeInventario, match="ARENA"):
        crear_material(
            sesion,
            codigo="ARENA",
            nombre="Otra",
            unidad_venta="t",
            existencia_minima=D("1"),
        )


def test_unidad_densidad_y_minima_invalidas_se_rechazan(sesion: Session) -> None:
    base = {"codigo": "X", "nombre": "X", "existencia_minima": D("1")}
    with pytest.raises(ErrorDeInventario, match="m3"):
        crear_material(sesion, unidad_venta="kg", **base)  # type: ignore[arg-type]
    for mala in (D("0"), D("-1.6")):
        with pytest.raises(ErrorDeInventario, match="densidad"):
            crear_material(sesion, unidad_venta="m3", densidad_t_m3=mala, **base)  # type: ignore[arg-type]
    with pytest.raises(ErrorDeInventario, match="minima"):
        crear_material(
            sesion, codigo="Y", nombre="Y", unidad_venta="t", existencia_minima=D("-1")
        )


def test_material_inexistente_y_ajuste_con_conteo_negativo(sesion: Session) -> None:
    with pytest.raises(ErrorDeInventario, match="material"):
        registrar_entrada(sesion, 999, date(2026, 10, 1), D("1"), usuario=USUARIO)
    mid = _arena(sesion)
    with pytest.raises(ErrorDeInventario, match="conteo"):
        registrar_ajuste_por_conteo(sesion, mid, date(2026, 10, 1), D("-1"), usuario=USUARIO)


def test_tablero_omite_materiales_inactivos(sesion: Session) -> None:
    mid = _arena(sesion)
    otro = crear_material(
        sesion,
        codigo="BASE",
        nombre="Base granular",
        unidad_venta="t",
        existencia_minima=D("5"),
        densidad_t_m3=D("1.8"),
    )
    assert [f.material.codigo for f in tablero(sesion)] == ["ARENA", "BASE"]
    otro.activo = False
    sesion.flush()
    filas = tablero(sesion)
    assert [f.material.codigo for f in filas] == ["ARENA"]
    assert filas[0].material.id == mid
