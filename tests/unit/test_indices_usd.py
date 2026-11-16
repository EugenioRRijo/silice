"""Un índice del BCV expresado en USD (RF-214; ola 2, línea 4, 2026-11-13).

Regla (simulada en la bitácora `2026-11-13-ola2-pdf-e-indices.md` §2): el valor en USD de un mes es
el índice en Bs ÷ el promedio de la tasa del BCV de cada día del mes, y la tasa de cada día es la
aplicable (S1-R1: la de mayor fecha ≤ ese día; S1-R2: con más de 7 días naturales no vale). Un mes
con un día sin tasa aplicable no se expresa y se dice por qué.

Oráculos a mano, con datos FICTICIOS:
- febrero de 2027 (28 días): tasa 40 el 1, el 8 y el 15 (cubren del 1 al 21: 21 días) y 54 el 22
  (del 22 al 28: 7 días): promedio (21 × 40 + 7 × 54) ÷ 28 = 1.218 ÷ 28 = 43,5; con el índice en 87,
  87 ÷ 43,5 = 2.
- tasas solo el 1 y el 15 de febrero: del 9 al 14 y del 23 al 28 no hay tasa de los 7 días
  anteriores (la del 15 cubre hasta el 22).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from aplicacion import indices_usd
from aplicacion.indices_usd import MesEnUsd, MesOmitido, expresar_en_usd
from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.catalog.indices import (
    DefinicionSerie,
    Observacion,
    definicion_tasa,
    registrar_importacion,
    tasa_aplicable,
)

D = Decimal
FEB = date(2027, 2, 1)
AHORA = datetime(2027, 3, 5, 10, 0)


def _tasas(*pares: tuple[str, str]) -> list[tuple[date, Decimal, bool]]:
    return [(date.fromisoformat(f), D(v), False) for f, v in pares]


def test_el_promedio_del_mes_pesa_cada_dia_con_su_tasa_aplicable():
    tasas = _tasas(
        ("2027-02-01", "40"), ("2027-02-08", "40"), ("2027-02-15", "40"), ("2027-02-22", "54")
    )
    meses, omitidos = expresar_en_usd({FEB: (D("87"), False)}, tasas)
    assert omitidos == []
    assert meses == [
        MesEnUsd(
            mes=FEB,
            indice_bs=D("87"),
            tasa_promedio=D("43.5"),
            dias=28,
            valor=D(2),
            provisional=False,
        )
    ]


def test_los_primeros_dias_del_mes_toman_la_ultima_tasa_del_mes_anterior():
    # la del 29/01 cubre del 1 al 4 de febrero (S1-R1); 46 todos los días
    tasas = _tasas(
        ("2027-01-29", "46"),
        ("2027-02-05", "46"),
        ("2027-02-12", "46"),
        ("2027-02-19", "46"),
        ("2027-02-26", "46"),
    )
    meses, omitidos = expresar_en_usd({FEB: (D("276"), False)}, tasas)
    assert omitidos == [] and meses[0].valor == D(6) and meses[0].tasa_promedio == D(46)


def test_un_mes_con_dias_sin_tasa_de_los_siete_anteriores_no_se_expresa_y_dice_cuales():
    tasas = _tasas(("2027-02-01", "40"), ("2027-02-15", "40"))
    meses, omitidos = expresar_en_usd({FEB: (D("87"), False)}, tasas)
    assert meses == []
    assert omitidos == [
        MesOmitido(
            FEB,
            "02/2027: del 09/02/2027 al 14/02/2027, del 23/02/2027 al 28/02/2027 no hay tasa del "
            "BCV de los 7 días anteriores (S1-R2)",
        )
    ]


def test_sin_ninguna_tasa_anterior_el_mes_tampoco_se_expresa():
    meses, omitidos = expresar_en_usd({FEB: (D("87"), False)}, _tasas(("2027-03-01", "40")))
    assert meses == []
    assert omitidos[0].motivo == (
        "02/2027: del 01/02/2027 al 28/02/2027 no hay tasa del BCV de los 7 días anteriores (S1-R2)"
    )


def test_un_indice_provisional_o_una_tasa_provisional_dan_un_valor_provisional():
    tasas = [(date(2027, 1, 29), D(46), False), (date(2027, 2, 5), D(46), True)] + _tasas(
        ("2027-02-12", "46"), ("2027-02-19", "46"), ("2027-02-26", "46")
    )
    (mes,), _ = expresar_en_usd({FEB: (D("276"), False)}, tasas)
    assert mes.provisional is True
    (mes,), _ = expresar_en_usd(
        {FEB: (D("276"), True)},
        _tasas(
            ("2027-01-29", "46"),
            ("2027-02-05", "46"),
            ("2027-02-12", "46"),
            ("2027-02-19", "46"),
            ("2027-02-26", "46"),
        ),
    )
    assert mes.provisional is True


def test_la_division_tiene_28_digitos_como_el_nucleo():
    tasas = _tasas(
        ("2027-01-29", "3"),
        ("2027-02-05", "3"),
        ("2027-02-12", "3"),
        ("2027-02-19", "3"),
        ("2027-02-26", "3"),
    )
    (mes,), _ = expresar_en_usd({FEB: (D(1), False)}, tasas)
    assert mes.valor == D("0.3333333333333333333333333333")


# --- en la base -----------------------------------------------------------------------------------


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as s:
        yield s
    motor.dispose()


def _importar(sesion, definicion, valores, huella, provisional=False):
    registrar_importacion(
        sesion,
        definicion,
        [Observacion(f, D(v), provisional) for f, v in valores],
        archivo="ficticio",
        huella=huella,
        fuente="ficticio",
        fecha_descarga=date(2027, 3, 1),
        responsable="A",
        filas_leidas=len(valores),
        filas_rechazadas=0,
    )


INPC = DefinicionSerie("FIC-INPC", "INPC ficticio", "BCV (ficticio)", "indice_bs", "mensual")


def _sembrar(sesion):
    _importar(sesion, INPC, [(date(2026, 1, 1), "200"), (FEB, "276")], "1" * 64)
    _importar(
        sesion,
        definicion_tasa("venta"),
        [
            (date(2025, 12, 29), "40"),
            *((date(2026, 1, d), "40") for d in (5, 12, 19, 26)),
            (date(2027, 1, 29), "46"),
            *((date(2027, 2, d), "46") for d in (5, 12, 19, 26)),
        ],
        "2" * 64,
    )
    sesion.flush()


def test_la_tasa_de_cada_dia_es_la_misma_que_da_tasa_aplicable_del_nucleo(sesion):
    """El promedio no reinventa S1-R1 ni S1-R2: cada día del mes usa lo que daría el núcleo."""
    _sembrar(sesion)
    vista = indices_usd.ver(sesion, "FIC-INPC")
    feb = next(m for m in vista.meses if m.mes == FEB)
    dias = [date(2027, 2, d) for d in range(1, 29)]
    esperado = sum((tasa_aplicable(sesion, d).valor for d in dias), D(0)) / len(dias)
    assert feb.tasa_promedio == esperado == D(46)


def test_ver_dice_la_serie_nueva_sus_meses_y_no_escribe(sesion):
    _sembrar(sesion)
    antes = sesion.scalar(
        select(models.ImportacionIndice.id).order_by(models.ImportacionIndice.id.desc())
    )
    vista = indices_usd.ver(sesion, "FIC-INPC")
    assert vista.serie_nueva == "FIC-INPC-USD"
    assert [(m.mes, m.valor) for m in vista.meses] == [(date(2026, 1, 1), D(5)), (FEB, D(6))]
    assert vista.omitidos == [] and len(vista.huella) == 64 and vista.ya_guardada is False
    despues = sesion.scalar(
        select(models.ImportacionIndice.id).order_by(models.ImportacionIndice.id.desc())
    )
    assert despues == antes


def test_con_la_tasa_de_compra_la_serie_nueva_lo_dice_en_su_codigo(sesion):
    _sembrar(sesion)
    _importar(sesion, definicion_tasa("compra"), [(date(2027, 1, 29), "45")], "3" * 64)
    vista = indices_usd.ver(sesion, "FIC-INPC", lado="compra")
    assert vista.serie_nueva == "FIC-INPC-USD-COMPRA"
    assert vista.meses == [] and len(vista.omitidos) == 2


def test_guardar_registra_la_serie_en_usd_como_una_importacion_y_es_idempotente(sesion):
    _sembrar(sesion)
    vista = indices_usd.ver(sesion, "FIC-INPC")
    mensaje = indices_usd.guardar(
        sesion, "FIC-INPC", huella=vista.huella, responsable="admin", ahora=AHORA
    )
    assert mensaje == "FIC-INPC-USD: guardada con 2 meses en USD."
    serie = sesion.scalars(
        select(models.SerieIndice).where(models.SerieIndice.codigo == "FIC-INPC-USD")
    ).one()
    assert (serie.unidad, serie.periodicidad) == ("indice_usd", "mensual")
    importacion = sesion.scalars(
        select(models.ImportacionIndice).where(models.ImportacionIndice.serie_id == serie.id)
    ).one()
    assert importacion.responsable == "admin" and importacion.huella == vista.huella
    assert "FIC-INPC" in importacion.fuente and "BCV-USD-VENTA" in importacion.fuente
    assert "02/2027: 276 ÷ 46 = 6" in importacion.informe
    valores = sesion.scalars(
        select(models.ValorIndice.valor)
        .where(models.ValorIndice.serie_id == serie.id)
        .order_by(models.ValorIndice.fecha)
    ).all()
    assert valores == [D(5), D(6)]
    assert indices_usd.ver(sesion, "FIC-INPC").ya_guardada is True
    otra = indices_usd.guardar(
        sesion, "FIC-INPC", huella=vista.huella, responsable="admin", ahora=AHORA
    )
    assert otra == "FIC-INPC-USD: ya estaba guardada con estos mismos valores; no se escribió nada."


def test_guardar_con_una_huella_vieja_no_escribe(sesion):
    _sembrar(sesion)
    vista = indices_usd.ver(sesion, "FIC-INPC")
    _importar(sesion, INPC, [(FEB, "299")], "4" * 64)  # una revisión del índice de febrero
    with pytest.raises(indices_usd.HuellaCambiada, match="cambiaron desde que lo revisó"):
        indices_usd.guardar(
            sesion, "FIC-INPC", huella=vista.huella, responsable="admin", ahora=AHORA
        )
    assert (
        sesion.scalars(
            select(models.SerieIndice).where(models.SerieIndice.codigo == "FIC-INPC-USD")
        ).first()
        is None
    )


def test_los_errores_dicen_que_hacer(sesion):
    with pytest.raises(indices_usd.SerieInexistente, match="No hay una serie «NO-HAY» importada"):
        indices_usd.ver(sesion, "NO-HAY")
    _sembrar(sesion)
    with pytest.raises(ValueError, match="no es un índice mensual en bolívares"):
        indices_usd.ver(sesion, "BCV-USD-VENTA")
    with pytest.raises(ValueError, match="se espera compra o venta"):
        indices_usd.ver(sesion, "FIC-INPC", lado="medio")
    with pytest.raises(ValueError, match="No hay tasa compra del BCV importada"):
        indices_usd.ver(sesion, "FIC-INPC", lado="compra")


def test_los_origenes_son_los_indices_mensuales_en_bolivares(sesion):
    _sembrar(sesion)
    vista = indices_usd.ver(sesion, "FIC-INPC")
    indices_usd.guardar(sesion, "FIC-INPC", huella=vista.huella, responsable="admin", ahora=AHORA)
    assert [s.codigo for s in indices_usd.origenes(sesion)] == ["FIC-INPC"]
