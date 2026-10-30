"""Costos del periodo del gestor de produccion (Tarea 1 del plan vial). Datos FICTICIOS.

Oraculos a mano: ningun valor sale de la funcion bajo prueba.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from produccion.costos import (
    CENTROS,
    CONCEPTOS,
    CostoDelPeriodo,
    anular_costo,
    costos_del_periodo,
    registrar_costo,
)
from produccion.modelo import METADATA_PRODUCCION, Costo

D = Decimal
AHORA = datetime(2026, 11, 20, 9, 0, 0)
FECHA = date(2026, 11, 3)


def _costo(**cambios) -> CostoDelPeriodo:
    base = {
        "periodo": "2026-11",
        "centro": "cantera",
        "concepto": "gasoil",
        "monto": D("1250.50"),
        "moneda": "USD",
        "fecha": FECHA,
        "fuente": "factura 12 (ficticia)",
    }
    return CostoDelPeriodo(**{**base, **cambios})


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    with Session(motor) as s:
        yield s
    motor.dispose()


def test_los_catalogos_son_los_del_plan() -> None:
    assert CONCEPTOS == (
        "gasoil",
        "equipo",
        "nomina",
        "mantenimiento",
        "explosivos",
        "energia",
        "otro",
    )
    assert CENTROS == ("cantera", "planta")


def test_costo_exige_fuente_fecha_y_periodo_valido() -> None:
    with pytest.raises(ValueError, match="fuente"):
        _costo(fuente=" ")
    with pytest.raises(ValueError, match="periodo"):
        _costo(periodo="2026-13")
    with pytest.raises(ValueError, match="periodo"):
        _costo(periodo="2026-1")
    with pytest.raises(ValueError, match="fecha"):
        _costo(fecha="2026-11-03")


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("concepto", "voladura"),
        ("centro", "oficina"),
        ("moneda", "EUR"),
        ("monto", D("-1")),
        ("monto", D("NaN")),
        ("monto", 10.5),
    ],
)
def test_rechaza_concepto_centro_moneda_y_monto_invalido(campo: str, valor: object) -> None:
    with pytest.raises(ValueError, match=campo):
        _costo(**{campo: valor})


def test_la_fecha_debe_caer_en_el_periodo() -> None:
    with pytest.raises(ValueError, match="fuera del periodo"):
        _costo(fecha=date(2026, 12, 1))
    _costo(fecha=date(2026, 11, 30))  # el ultimo dia del mes sigue dentro


def test_registrar_y_leer_conserva_cada_campo(sesion: Session) -> None:
    i = registrar_costo(sesion, _costo(nota="tanque 2"), usuario="ana", ahora=AHORA)
    [fila] = costos_del_periodo(sesion, "2026-11")
    assert fila.id == i
    assert fila.costo == _costo(nota="tanque 2")
    assert (fila.usuario, fila.registrado, fila.anulado) == ("ana", AHORA, False)
    assert costos_del_periodo(sesion, "2026-10") == []


def test_el_monto_se_guarda_exacto(sesion: Session) -> None:
    registrar_costo(sesion, _costo(monto=D("0.1") + D("0.2")), usuario="ana", ahora=AHORA)
    [fila] = costos_del_periodo(sesion, "2026-11")
    assert fila.costo.monto == D("0.3")


def test_anular_no_borra(sesion: Session) -> None:
    i = registrar_costo(sesion, _costo(), usuario="ana", ahora=AHORA)
    n = anular_costo(sesion, i, motivo="duplicado", usuario="ana", ahora=AHORA)
    assert n != i
    assert costos_del_periodo(sesion, "2026-11") == []
    todos = costos_del_periodo(sesion, "2026-11", incluir_anulados=True)
    assert len(todos) == 2
    assert all(f.anulado for f in todos)
    assert {f.id for f in todos} == {i, n}


def test_anular_exige_motivo_y_que_exista_y_no_se_repite(sesion: Session) -> None:
    i = registrar_costo(sesion, _costo(), usuario="ana", ahora=AHORA)
    with pytest.raises(ValueError, match="motivo"):
        anular_costo(sesion, i, motivo="  ", usuario="ana", ahora=AHORA)
    with pytest.raises(ValueError, match="No existe"):
        anular_costo(sesion, 999, motivo="x", usuario="ana", ahora=AHORA)
    n = anular_costo(sesion, i, motivo="duplicado", usuario="ana", ahora=AHORA)
    with pytest.raises(ValueError, match="ya fue anulado"):
        anular_costo(sesion, i, motivo="otra vez", usuario="ana", ahora=AHORA)
    with pytest.raises(ValueError, match="ya fue anulado"):
        anular_costo(sesion, n, motivo="anular la anulacion", usuario="ana", ahora=AHORA)


def test_un_costo_corregido_es_un_registro_nuevo(sesion: Session) -> None:
    malo = registrar_costo(sesion, _costo(monto=D("1200")), usuario="ana", ahora=AHORA)
    anular_costo(sesion, malo, motivo="monto mal digitado", usuario="ana", ahora=AHORA)
    registrar_costo(sesion, _costo(monto=D("1250.50")), usuario="ana", ahora=AHORA)
    vigentes = costos_del_periodo(sesion, "2026-11")
    assert [f.costo.monto for f in vigentes] == [D("1250.50")]


def test_los_costos_salen_en_orden_de_registro(sesion: Session) -> None:
    a = registrar_costo(sesion, _costo(concepto="equipo"), usuario="ana", ahora=AHORA)
    b = registrar_costo(sesion, _costo(concepto="nomina"), usuario="ana", ahora=AHORA)
    assert [f.id for f in costos_del_periodo(sesion, "2026-11")] == [a, b]


def test_periodo_invalido_al_consultar(sesion: Session) -> None:
    with pytest.raises(ValueError, match="periodo"):
        costos_del_periodo(sesion, "noviembre")


def test_el_motivo_de_la_anulacion_queda_en_su_registro(sesion: Session) -> None:
    i = registrar_costo(sesion, _costo(), usuario="ana", ahora=AHORA)
    n = anular_costo(sesion, i, motivo="  duplicado ", usuario="ana", ahora=AHORA)
    por_id = {f.id: f for f in costos_del_periodo(sesion, "2026-11", incluir_anulados=True)}
    assert (por_id[i].motivo, por_id[i].anula_id) == ("", None)
    assert (por_id[n].motivo, por_id[n].anula_id) == ("duplicado", i)


def test_dos_anulaciones_directas_del_mismo_costo_fallan_en_la_base(sesion: Session) -> None:
    i = registrar_costo(sesion, _costo(), usuario="ana", ahora=AHORA)
    anular_costo(sesion, i, motivo="duplicado", usuario="ana", ahora=AHORA)

    def fila() -> Costo:
        return Costo(
            periodo="2026-11",
            centro="cantera",
            concepto="gasoil",
            monto=D("1"),
            moneda="USD",
            fecha=FECHA,
            fuente="f",
            nota="",
            usuario="x",
            registrado=AHORA,
            anula_id=i,
            motivo="otra",
        )

    sesion.add(fila())
    with pytest.raises(IntegrityError):
        sesion.flush()


def test_menos_cero_se_normaliza_a_cero(sesion: Session) -> None:
    assert str(_costo(monto=D("-0")).monto) == "0"
    assert str(_costo(monto=D("-0.00")).monto) == "0.00"
    registrar_costo(sesion, _costo(monto=D("-0")), usuario="ana", ahora=AHORA)
    [fila] = costos_del_periodo(sesion, "2026-11")
    assert str(fila.costo.monto) == "0"
