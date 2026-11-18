"""`api/presentacion.py`: el único sitio de la API que presenta cifras (tarea 2.2 del plan de
desenredo). Dos decimales con `ROUND_HALF_UP` (decisión de Eugenio, 2026-11-17), el cero sin signo
y, si el monto no cabe al cuantizar, el exacto en vez de una excepción."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from api import presentacion
from api.presentacion import (
    cifra_presentada,
    exacto,
    exacto_o_nada,
    exacto_sin_ceros,
    monto,
    monto_o_nada,
    porcentaje,
    porcentaje_o_nada,
    redondeado,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("0.125", "0.13"),
        ("-0.125", "-0.13"),
        ("2.675", "2.68"),
        ("-0.001", "0.00"),
        ("1E+3", "1000.00"),
        ("1" + "0" * 30, "1" + "0" * 30),
    ],
)
def test_monto_a_dos_decimales_al_alza(valor, esperado):
    assert monto(Decimal(valor)) == esperado


def test_monto_o_nada():
    assert monto_o_nada(None) is None
    assert monto_o_nada(Decimal("0.005")) == "0.01"


def test_exacto_no_redondea_ni_recorta():
    assert exacto(Decimal("12.50")) == "12.50"
    assert exacto(Decimal("1E+3")) == "1000"
    assert exacto_o_nada(None) is None
    assert exacto_o_nada(Decimal("0.125")) == "0.125"


def test_exacto_sin_ceros():
    assert exacto_sin_ceros(Decimal("4358.2082500")) == "4358.20825"
    assert exacto_sin_ceros(Decimal("-0.000")) == "0"
    assert exacto_sin_ceros(Decimal("1E+3")) == "1000"


def test_porcentaje():
    assert porcentaje(Decimal("1.25"), Decimal("1000"), 2) == "0.13"
    assert porcentaje(Decimal("1"), Decimal("0")) is None
    assert porcentaje(Decimal("-0.00001"), Decimal("1000")) == "0.00"
    assert porcentaje(Decimal("1"), Decimal("8"), 1) == "12.5"
    assert porcentaje(Decimal("1" + "0" * 30), Decimal("1")) is None  # no cabe: sin porcentaje


def test_porcentaje_o_nada():
    assert porcentaje_o_nada(None, Decimal("10")) is None
    assert porcentaje_o_nada(Decimal("1"), None) is None
    assert porcentaje_o_nada(Decimal("1"), Decimal("0"), 1) is None
    assert porcentaje_o_nada(Decimal("1"), Decimal("16"), 1) == "6.3"  # 6,25 -> 6,3 al alza


def test_cifra_presentada_y_redondeado():
    assert cifra_presentada(Decimal("1234.565")) == "1.234,57"
    assert cifra_presentada(Decimal("-0.001")) == "0,00"
    assert redondeado(Decimal("1.2345"), 3) == "1.235"


def test_presentacion_no_redondea_al_par():
    fuente = Path(presentacion.__file__).read_text(encoding="utf-8")
    assert "ROUND_HALF_EVEN" not in fuente


# --- Bordes que cambiaron al unificar la presentación (revisión de la ola 2, hallazgo 1) -------
# Antes de `api/presentacion.py`, las rutas daban «-0.00» para un monto que redondea a cero y un
# 500 (`InvalidOperation`) para un monto de más de ~26 cifras enteras. Ahora: «0.00» y el exacto.


def _obra_con(total: Decimal | None, ev: Decimal | None, bac: Decimal | None):
    from aplicacion.mesa import ETAPA_TEXTO, ObraEnMesa

    return ObraEnMesa(
        codigo="OB-1",
        nombre="Obra ficticia",
        cliente="Cliente ficticio",
        moneda="USD",
        etapa=next(iter(ETAPA_TEXTO)),
        version=None,
        total=total,
        corte=None,
        ev=ev,
        pv=None,
        bac=bac,
        spi=None,
        retraso_dias=None,
        que_pasa=None,
        siguiente=None,
    )


def test_la_ruta_de_obras_presenta_el_cero_sin_signo():
    from api.rutas.obras import _obra

    r = _obra(_obra_con(Decimal("-0.001"), Decimal("-0.0001"), Decimal("1000")))
    assert (r.total, r.avance_real) == ("0.00", "0.0")


def test_la_ruta_de_obras_presenta_exacto_un_monto_que_no_cabe():
    from api.rutas.obras import _obra

    enorme = Decimal("1" + "0" * 30)
    assert _obra(_obra_con(enorme, None, None)).total == "1" + "0" * 30
