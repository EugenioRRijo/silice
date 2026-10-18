"""Modelo de la arenera (Tarea 4.2): tablas, columnas, restricciones y decimales exactos."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from produccion.modelo import METADATA_PRODUCCION, Material, Movimiento, PesajeSospechoso

COLUMNAS = {
    "prod_material": {"id", "codigo", "nombre", "unidad_venta", "densidad_t_m3",
                      "existencia_minima", "activo"},
    "prod_movimiento": {"id", "material_id", "fecha", "tipo", "cantidad", "ticket", "placa",
                        "cliente", "nota", "origen", "usuario", "registrado"},
    "prod_pesaje_sospechoso": {"id", "huella_archivo", "fila", "ticket", "fecha_texto", "placa",
                               "material_texto", "bruto_texto", "tara_texto", "neto_texto",
                               "motivo", "estado", "resuelto_por", "resuelto_en"},
}


@pytest.fixture
def sesion():
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    with Session(motor) as s:
        yield s


def _material(sesion, codigo="ARENA"):
    m = Material(codigo=codigo, nombre="Arena lavada", unidad_venta="m3",
                 existencia_minima=Decimal("20"), activo=True)
    sesion.add(m)
    sesion.flush()
    return m


def _mov(material, **extra):
    datos = dict(material_id=material.id, fecha=date(2026, 10, 1), tipo="entrada",
                 cantidad=Decimal("1"), origen="manual", usuario="u",
                 registrado=datetime(2026, 10, 1, 8, 0))
    datos.update(extra)
    return Movimiento(**datos)


def test_las_tres_tablas_existen_con_sus_columnas():
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    insp = inspect(motor)
    assert set(insp.get_table_names()) == set(COLUMNAS)
    for tabla, esperadas in COLUMNAS.items():
        assert {c["name"] for c in insp.get_columns(tabla)} == esperadas


def test_un_ticket_repetido_choca(sesion):
    m = _material(sesion)
    sesion.add_all([_mov(m, tipo="despacho", ticket="TCK-1"),
                    _mov(m, tipo="despacho", ticket="TCK-1")])
    with pytest.raises(IntegrityError):
        sesion.flush()


def test_dos_movimientos_sin_ticket_conviven(sesion):
    m = _material(sesion)
    sesion.add_all([_mov(m), _mov(m)])
    sesion.flush()


def test_la_cantidad_conserva_los_decimales(sesion):
    m = _material(sesion)
    sesion.add(_mov(m, cantidad=Decimal("28.300")))
    sesion.commit()
    sesion.expire_all()
    assert sesion.query(Movimiento).one().cantidad == Decimal("28.300")
    assert str(sesion.query(Movimiento).one().cantidad) == "28.300"


def test_la_cantidad_rechaza_float(sesion):
    m = _material(sesion)
    sesion.add(_mov(m, cantidad=1.5))
    with pytest.raises(Exception, match="Decimal"):
        sesion.flush()


def test_tipo_invalido_choca(sesion):
    m = _material(sesion)
    sesion.add(_mov(m, tipo="regalo"))
    with pytest.raises(IntegrityError):
        sesion.flush()


def test_unidad_de_venta_invalida_choca(sesion):
    sesion.add(Material(codigo="X", nombre="X", unidad_venta="kg",
                        existencia_minima=Decimal("0"), activo=True))
    with pytest.raises(IntegrityError):
        sesion.flush()


def test_el_estado_del_sospechoso_se_restringe(sesion):
    sesion.add(PesajeSospechoso(huella_archivo="a" * 64, fila=2, motivo="m", estado="raro"))
    with pytest.raises(IntegrityError):
        sesion.flush()
