"""Servicio de inventario de la arenera. Serie de ARENA: ejemplo construido, oraculo a mano."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from produccion.inventario import (
    ErrorDeInventario,
    crear_material,
    existencia,
    registrar_ajuste_por_conteo,
    registrar_consumo,
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


def test_conteo_igual_a_lo_teorico_deja_un_ajuste_en_cero_y_cierra_el_pasado(
    sesion: Session,
) -> None:
    """Arbitraje 2026-11-18: el conteo que coincide tambien se guarda (un ajuste en 0): sin fila no
    cerraba el pasado y una entrada retroactiva cambiaba la existencia posterior al conteo."""
    mid = _arena(sesion)
    _serie(sesion, mid)
    ajuste = registrar_ajuste_por_conteo(sesion, mid, date(2026, 10, 5), D("34.5"), usuario=USUARIO)
    assert ajuste is not None and ajuste.tipo == "ajuste"
    assert ajuste.cantidad == D("0") and str(ajuste.cantidad) == "0"
    assert existencia(sesion, mid) == D("34.5")
    with pytest.raises(ErrorDeInventario, match="conteo físico del 05/10/2026"):
        registrar_entrada(sesion, mid, date(2026, 10, 4), D("10"), usuario=USUARIO)
    assert existencia(sesion, mid) == D("34.5")


def test_un_material_sin_movimientos_contado_en_cero_tambien_cierra(sesion: Session) -> None:
    mid = _arena(sesion)
    ajuste = registrar_ajuste_por_conteo(sesion, mid, date(2026, 10, 5), D("0"), usuario=USUARIO)
    assert ajuste is not None and ajuste.cantidad == D("0")
    assert existencia(sesion, mid) == D("0")
    with pytest.raises(ErrorDeInventario, match="conteo físico del 05/10/2026"):
        registrar_despacho(sesion, mid, date(2026, 10, 1), D("3"), usuario=USUARIO)


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
    with pytest.raises(ErrorDeInventario, match="mínima"):
        crear_material(sesion, codigo="Y", nombre="Y", unidad_venta="t", existencia_minima=D("-1"))


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


def test_entradas_del_periodo_una_por_entrada_en_toneladas(sesion: Session) -> None:
    """Plan vial, Tarea 4: lo mismo que suma `producido_en_periodo`, entrada por entrada (con su
    fecha), para buscar la receta vigente en la fecha de cada produccion. Oraculo a mano: 10 m3 de
    ARENA a 1,6 t/m3 son 16 t; el despacho y lo de otro mes no aparecen."""
    from produccion.inventario import EntradaDelPeriodo, entradas_del_periodo

    arena = crear_material(
        sesion,
        codigo="ARENA",
        nombre="Arena",
        unidad_venta="m3",
        existencia_minima=D(0),
        densidad_t_m3=D("1.6"),
    ).id
    piedra = crear_material(
        sesion, codigo="PIEDRA", nombre="Piedra", unidad_venta="t", existencia_minima=D(0)
    ).id
    registrar_entrada(sesion, piedra, date(2026, 11, 2), D("50"), usuario=USUARIO)
    registrar_entrada(sesion, arena, date(2026, 11, 9), D("10"), usuario=USUARIO)
    registrar_entrada(sesion, arena, date(2026, 11, 3), D("5"), usuario=USUARIO)
    registrar_despacho(sesion, arena, date(2026, 11, 4), D("3"), usuario=USUARIO)
    registrar_entrada(sesion, arena, date(2026, 12, 1), D("99"), usuario=USUARIO)
    assert entradas_del_periodo(sesion, "2026-11") == [
        EntradaDelPeriodo("ARENA", date(2026, 11, 9), D("16.0")),
        EntradaDelPeriodo("ARENA", date(2026, 11, 3), D("8.0")),
        EntradaDelPeriodo("PIEDRA", date(2026, 11, 2), D("50")),
    ]
    assert entradas_del_periodo(sesion, "2026-10") == []


def test_material_por_id_da_la_fila_o_nada(sesion: Session) -> None:
    """Anexo A.7: la ruta que resuelve un sospechoso lee el material por aqui."""
    from produccion.inventario import material_por_id

    mid = _arena(sesion)

    assert material_por_id(sesion, mid).codigo == "ARENA"
    assert material_por_id(sesion, mid + 1) is None


# Prueba en vivo 2026-11-18 (frente D): el conteo se guarda como un ajuste con la diferencia del
# dia en que se registra, asi que un movimiento con fecha anterior registrado despues cambiaba la
# existencia posterior al conteo. Ejemplo del hallazgo: entrada 150,5 (03/11), conteo 148 (06/11);
# luego entrada 90 (06/10) y consumo 20 (20/10) dejaban 218 al 06/11 en vez de 148. Decision: el
# conteo fisico cierra el pasado de ese material (practica de cierre de inventario de los ERP).


def _con_conteo(sesion: Session) -> int:
    mid = crear_material(
        sesion, codigo="PIEDRA", nombre="Piedra", unidad_venta="t", existencia_minima=D("0")
    ).id
    registrar_entrada(sesion, mid, date(2026, 11, 3), D("150.5"), usuario=USUARIO)
    registrar_ajuste_por_conteo(sesion, mid, date(2026, 11, 6), D("148"), usuario=USUARIO)
    return mid


def test_un_conteo_fisico_cierra_el_pasado_del_material(sesion: Session) -> None:
    mid = _con_conteo(sesion)
    cerrado = r"conteo físico del 06/11/2026.*posterior al 06/11/2026"
    with pytest.raises(ErrorDeInventario, match=cerrado):
        registrar_entrada(sesion, mid, date(2026, 10, 6), D("90"), usuario=USUARIO)
    with pytest.raises(ErrorDeInventario, match=cerrado):
        registrar_consumo(
            sesion, mid, date(2026, 10, 20), D("20"), usuario=USUARIO, ahora=datetime(2026, 11, 7)
        )
    with pytest.raises(ErrorDeInventario, match=cerrado):  # el mismo dia del conteo, tambien
        registrar_despacho(sesion, mid, date(2026, 11, 6), D("5"), usuario=USUARIO)
    assert existencia(sesion, mid, date(2026, 11, 6)) == D("148")
    registrar_despacho(sesion, mid, date(2026, 11, 7), D("8"), usuario=USUARIO)
    assert existencia(sesion, mid) == D("140")


def test_el_cierre_es_solo_del_material_contado(sesion: Session) -> None:
    _con_conteo(sesion)
    otro = _arena(sesion)
    registrar_entrada(sesion, otro, date(2026, 10, 6), D("90"), usuario=USUARIO)
    assert existencia(sesion, otro) == D("90")


def test_un_conteo_no_va_antes_del_ultimo_y_el_mismo_dia_es_un_reconteo(sesion: Session) -> None:
    mid = _con_conteo(sesion)
    with pytest.raises(ErrorDeInventario, match="conteo físico del 06/11/2026"):
        registrar_ajuste_por_conteo(sesion, mid, date(2026, 11, 5), D("100"), usuario=USUARIO)
    reconteo = registrar_ajuste_por_conteo(
        sesion, mid, date(2026, 11, 6), D("146.5"), usuario=USUARIO
    )
    assert reconteo is not None and reconteo.cantidad == D("-1.5")
    assert existencia(sesion, mid) == D("146.5")
