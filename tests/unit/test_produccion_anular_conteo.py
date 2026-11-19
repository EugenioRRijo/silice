"""Anular un conteo fisico (tanda 2026-11-19, hueco declarado en la prueba en vivo del 2026-11-18).

Como en los ERP, nada se borra: la anulacion es un ajuste nuevo que compensa el del conteo (misma
fecha, cantidad con el signo contrario) con `anula_id`, quien, cuando y el motivo. El conteo
anulado deja de cerrar el pasado: lo cierra el anterior no anulado. Solo se anula el ultimo conteo
vigente de cada material (el siguiente se calculo sobre la existencia que el incluia).

Serie FICTICIA de PIEDRA (en t), oraculos a mano: entrada 150,5 el 03/11; conteo 148 el 06/11
(ajuste -2,5); entrada 10 el 08/11; conteo 160 el 10/11 (lo teorico era 148 + 10 = 158: ajuste +2).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from produccion.inventario import (
    Conflicto,
    ConteoInexistente,
    ErrorDeInventario,
    anular_conteo,
    conteo_vigente,
    crear_material,
    existencia,
    registrar_ajuste_por_conteo,
    registrar_despacho,
    registrar_entrada,
    tablero,
    ultimo_conteo,
)
from produccion.modelo import METADATA_PRODUCCION, Movimiento

D = Decimal
USUARIO = "prueba"
QUIEN_ANULA = "Ana Pérez <ana>"
AHORA = datetime(2026, 11, 12, 9, 30, 0)
MOTIVO = "Se contó la pila de la otra planta."


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    with Session(motor) as s:
        yield s
    motor.dispose()


def _serie(sesion: Session) -> tuple[int, Movimiento, Movimiento]:
    mid = crear_material(
        sesion, codigo="PIEDRA", nombre="Piedra", unidad_venta="t", existencia_minima=D("0")
    ).id
    registrar_entrada(sesion, mid, date(2026, 11, 3), D("150.5"), usuario=USUARIO)
    primero = registrar_ajuste_por_conteo(sesion, mid, date(2026, 11, 6), D("148"), usuario=USUARIO)
    registrar_entrada(sesion, mid, date(2026, 11, 8), D("10"), usuario=USUARIO)
    segundo = registrar_ajuste_por_conteo(
        sesion, mid, date(2026, 11, 10), D("160"), usuario=USUARIO
    )
    return mid, primero, segundo


def _anular(sesion: Session, movimiento_id: int, motivo: str = MOTIVO) -> Movimiento:
    return anular_conteo(sesion, movimiento_id, motivo=motivo, usuario=QUIEN_ANULA, ahora=AHORA)


def test_la_serie_de_partida(sesion: Session) -> None:
    mid, primero, segundo = _serie(sesion)
    assert (primero.cantidad, segundo.cantidad) == (D("-2.5"), D("2"))
    assert existencia(sesion, mid) == D("160")
    assert conteo_vigente(sesion, mid) == segundo


def test_anular_el_ultimo_conteo_lo_compensa_sin_borrar_nada(sesion: Session) -> None:
    mid, _, segundo = _serie(sesion)
    anulacion = _anular(sesion, segundo.id)
    assert (anulacion.tipo, anulacion.fecha, anulacion.cantidad) == (
        "ajuste",
        date(2026, 11, 10),
        D("-2"),
    )
    assert (anulacion.anula_id, anulacion.motivo) == (segundo.id, MOTIVO)
    assert (anulacion.usuario, anulacion.registrado) == (QUIEN_ANULA, AHORA)
    # el conteo original queda como estaba
    sesion.refresh(segundo)
    assert (segundo.cantidad, segundo.anula_id, segundo.motivo) == (D("2"), None, "")
    assert existencia(sesion, mid, date(2026, 11, 10)) == D("158")
    assert existencia(sesion, mid) == D("158")


def test_el_pasado_lo_cierra_el_conteo_anterior_no_anulado(sesion: Session) -> None:
    mid, primero, segundo = _serie(sesion)
    _anular(sesion, segundo.id)
    assert ultimo_conteo(sesion, mid) == date(2026, 11, 6)
    assert conteo_vigente(sesion, mid) == primero
    registrar_despacho(sesion, mid, date(2026, 11, 9), D("8"), usuario=USUARIO)  # ya se puede
    assert existencia(sesion, mid) == D("150")
    with pytest.raises(ErrorDeInventario, match="conteo físico del 06/11/2026"):
        registrar_despacho(sesion, mid, date(2026, 11, 6), D("1"), usuario=USUARIO)


def test_tras_anular_se_puede_contar_de_nuevo_antes_de_la_fecha_anulada(sesion: Session) -> None:
    mid, _, segundo = _serie(sesion)
    _anular(sesion, segundo.id)
    nuevo = registrar_ajuste_por_conteo(sesion, mid, date(2026, 11, 9), D("157"), usuario=USUARIO)
    assert nuevo.cantidad == D("-1")  # 148 + 10 = 158 teorico al 09/11
    assert conteo_vigente(sesion, mid) == nuevo


def test_solo_se_anula_el_ultimo_conteo_vigente(sesion: Session) -> None:
    mid, primero, segundo = _serie(sesion)
    with pytest.raises(Conflicto, match=r"último conteo vigente.*10/11/2026"):
        _anular(sesion, primero.id)
    _anular(sesion, segundo.id)
    _anular(sesion, primero.id)  # ahora si es el ultimo vigente
    assert existencia(sesion, mid) == D("160.5")
    assert ultimo_conteo(sesion, mid) is None
    assert conteo_vigente(sesion, mid) is None


def test_un_reconteo_del_mismo_dia_es_el_ultimo_y_se_anula_primero(sesion: Session) -> None:
    mid, _, segundo = _serie(sesion)
    reconteo = registrar_ajuste_por_conteo(
        sesion, mid, date(2026, 11, 10), D("159"), usuario=USUARIO
    )
    assert reconteo.cantidad == D("-1")
    with pytest.raises(Conflicto, match="último conteo vigente"):
        _anular(sesion, segundo.id)
    _anular(sesion, reconteo.id)
    assert conteo_vigente(sesion, mid) == segundo
    assert existencia(sesion, mid) == D("160")


def test_un_conteo_ya_anulado_o_una_anulacion_no_se_anulan(sesion: Session) -> None:
    _, _, segundo = _serie(sesion)
    anulacion = _anular(sesion, segundo.id)
    with pytest.raises(Conflicto, match="ya fue anulado"):
        _anular(sesion, segundo.id)
    with pytest.raises(Conflicto, match="es la anulación de un conteo"):
        _anular(sesion, anulacion.id)


def test_lo_que_no_es_un_conteo_no_se_anula(sesion: Session) -> None:
    mid, _, _ = _serie(sesion)
    entrada = registrar_entrada(sesion, mid, date(2026, 11, 11), D("1"), usuario=USUARIO)
    with pytest.raises(ConteoInexistente, match="No existe ese conteo físico"):
        _anular(sesion, entrada.id)
    with pytest.raises(ConteoInexistente, match="No existe ese conteo físico"):
        _anular(sesion, 9999)


@pytest.mark.parametrize("motivo", ["", "   "])
def test_el_motivo_es_obligatorio(sesion: Session, motivo: str) -> None:
    _, _, segundo = _serie(sesion)
    with pytest.raises(ErrorDeInventario, match="Escriba el motivo"):
        _anular(sesion, segundo.id, motivo)


def test_el_motivo_tiene_un_tope_y_se_guarda_sin_blancos_en_los_extremos(sesion: Session) -> None:
    _, _, segundo = _serie(sesion)
    with pytest.raises(ErrorDeInventario, match="300 caracteres"):
        _anular(sesion, segundo.id, "x" * 301)
    assert _anular(sesion, segundo.id, f"  {'x' * 300}  ").motivo == "x" * 300


def test_anular_un_conteo_en_cero_deja_la_compensacion_en_cero(sesion: Session) -> None:
    mid = crear_material(
        sesion, codigo="ARENA", nombre="Arena", unidad_venta="m3", existencia_minima=D("0")
    ).id
    conteo = registrar_ajuste_por_conteo(sesion, mid, date(2026, 11, 6), D("0"), usuario=USUARIO)
    anulacion = _anular(sesion, conteo.id)
    assert str(anulacion.cantidad) == "0"  # no «-0»
    assert ultimo_conteo(sesion, mid) is None


def test_el_tablero_trae_el_conteo_vigente_de_cada_material(sesion: Session) -> None:
    mid, primero, segundo = _serie(sesion)
    otro = crear_material(
        sesion, codigo="ARENA", nombre="Arena", unidad_venta="m3", existencia_minima=D("0")
    )
    filas = {f.material.codigo: f for f in tablero(sesion)}
    assert filas["PIEDRA"].conteo == segundo
    assert filas["ARENA"].conteo is None and otro.id != mid
    _anular(sesion, segundo.id)
    assert {f.material.codigo: f for f in tablero(sesion)}["PIEDRA"].conteo == primero


def test_el_cierre_dice_que_un_conteo_mal_hecho_se_anula(sesion: Session) -> None:
    """El mensaje del cierre ya no manda a «hacer un conteo nuevo», que no reabre el pasado."""
    mid, _, _ = _serie(sesion)
    with pytest.raises(ErrorDeInventario) as error:
        registrar_entrada(sesion, mid, date(2026, 11, 9), D("1"), usuario=USUARIO)
    assert str(error.value).endswith(
        "o, si el conteo estaba mal, anúlelo en «Existencias» con su motivo."
    )
