"""Fronteras de R11/R12 sin base (PRU-H11) y el día sin tasa (Foco 2)."""

from datetime import date
from decimal import Decimal

from core.verification.precios import InstantaneaPrecios, PrecioAuditado, reglas_precios

T = Decimal("633.3644")


def _p(
    precio,
    fecha=date(2026, 9, 20),
    referencia=Decimal("4530.00"),
    tasa=T,
    tasa_a_su_fecha=None,
    erosion=Decimal(0),
):
    return PrecioAuditado(
        1,
        "MAT-1",
        "CODO",
        precio,
        "Bs",
        "Bs",
        precio,
        fecha,
        tasa,
        date(2026, 7, 1) if tasa else None,
        "MaPreX" if tasa else "",
        tasa_a_su_fecha,
        referencia,
        "Bs",
        T,
        "PLO035",
        erosion,
        None,
    )


def _inst(*precios, tasa_evaluacion=Decimal("860.18")):
    return InstantaneaPrecios(
        date(2026, 10, 1), "Bs", precios, tasa_evaluacion, Decimal("-0.20"), Decimal("0.30"), 30
    )


def _r(inst, codigo):
    return [h for regla in reglas_precios(inst) for h in regla.evaluar(None) if h.regla == codigo]


def test_las_fronteras_exactas_pasan_y_un_diezmilesimo_mas_no():
    assert not _r(
        _inst(
            _p(Decimal("0.8000") * Decimal("4530.00")), _p(Decimal("1.3000") * Decimal("4530.00"))
        ),
        "R11",
    )
    assert (
        len(
            _r(
                _inst(
                    _p(Decimal("0.7999") * Decimal("4530.00")),
                    _p(Decimal("1.3001") * Decimal("4530.00")),
                ),
                "R11",
            )
        )
        == 2
    )


def test_30_dias_pasa_y_31_advierte():
    assert not _r(_inst(_p(Decimal("4530"), fecha=date(2026, 9, 1))), "R12")
    assert len(_r(_inst(_p(Decimal("4530"), fecha=date(2026, 8, 31))), "R12")) == 1


def test_dia_sin_tasa_no_revienta():
    """[Foco 2] sin tasa a la fecha del precio (> 7 días) R11 lo cuenta como no contrastable y R12
    vencido sale con impacto None, diciendo por qué."""
    sin = _p(Decimal("4530"), fecha=date(2026, 8, 1), tasa=None, tasa_a_su_fecha=None, erosion=None)
    r11 = _r(_inst(sin, tasa_evaluacion=None), "R11")
    assert r11[0].severidad.name == "INFO" and "sin tasa" in r11[0].descripcion
    r12 = _r(_inst(sin, tasa_evaluacion=None), "R12")
    assert r12[0].impacto is None and "sin tasa" in r12[0].descripcion
