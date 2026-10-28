"""Las observaciones del estudio de mercado en otra moneda se citan convertidas con la tasa del BCV
del mismo día de la observación (decisión de Eugenio del 2026-10-27, Tarea D3; antes quedaban fuera
y solo se contaban).

Datos ficticios (`tests/fixtures/mercado_ficticio.py`): la carpeta trabaja en Bs y hoy es el
25/10/2026. Tasas sembradas: 36,50 Bs/USD con fecha valor 20/10 y 36,00 con fecha valor 19/10; el
21/10 no tiene tasa. Oráculos a mano:

- Compra de MAT-001: 100 Bs y 200 Bs (hoy) y 3,00 USD del 20/10 → 3,00 × 36,50 = 109,50 Bs.
  Precios ordenados [100; 109,50; 200] (n = 3): mínimo 100; primer cuartil (posición 0,5) =
  100 + 0,5 × 9,50 = 104,75; mediana 109,50; promedio (100 + 109,50 + 200) / 3 = 409,50 / 3 =
  136,50; máximo 200.
- Una observación de 4,00 USD del 21/10 no tiene tasa de ese día (la del 20/10 es de un día
  anterior): queda fuera de las cifras con «sin tasa del BCV del 21/10/2026» y se cuenta aparte.
- Carpeta en USD: 146,00 Bs del 20/10 ÷ 36,50 = 4,00 USD.
- La observación original no se modifica: se convierte al leer; la tasa queda en los índices.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.mercado import (
    ReglaDeMercado,
    estadisticas,
    observaciones_leidas,
    usar_precio_de_cobro,
    usar_precio_de_compra,
)
from aplicacion.tablas_mercado import ObservacionDeMercado
from core import models
from tests.fixtures.hoja_versiones_api import registrar_tasa_en
from tests.fixtures.mercado_ficticio import (
    AHORA,
    HOY,
    RESPONSABLE,
    nueva_sesion,
    observacion_cruda,
    observar,
)

DIA_20 = date(2026, 10, 20)
DIA_21 = date(2026, 10, 21)


def _tasas(s: Session) -> None:
    registrar_tasa_en(s, date(2026, 10, 19), "36.00", huella="1" * 64)
    registrar_tasa_en(s, DIA_20, "36.50", huella="2" * 64)


@pytest.fixture
def s() -> Iterator[Session]:
    for sesion in nueva_sesion():
        _tasas(sesion)
        yield sesion


def test_una_observacion_en_usd_entra_en_las_cifras_convertida_a_bs_con_la_tasa_de_su_dia(
    s: Session,
) -> None:
    ids = observar(s, "MAT-001", ["100", "200"])
    usd = observacion_cruda(s, "MAT-001", Decimal("3.00"), moneda="USD", fecha=DIA_20)
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert (est.n, est.convertidas, est.sin_tasa) == (3, 1, 0)
    assert (est.minimo, est.q1, est.mediana, est.promedio, est.maximo) == (
        Decimal("100"),
        Decimal("104.75"),
        Decimal("109.50"),
        Decimal("136.50"),
        Decimal("200"),
    )
    assert set(est.ids) == {*ids, usd}


def test_una_observacion_con_tasa_solo_del_dia_anterior_sale_de_las_cifras_y_se_cuenta_aparte(
    s: Session,
) -> None:
    observar(s, "MAT-001", ["100", "200"])
    sin = observacion_cruda(s, "MAT-001", Decimal("4.00"), moneda="USD", fecha=DIA_21)
    est = estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    assert (est.n, est.convertidas, est.sin_tasa, est.maximo) == (2, 0, 1, Decimal("200"))
    assert sin not in est.ids
    leidas = {o.fila.id: o for o in observaciones_leidas(s, "compra", "MAT-001", HOY)}
    assert (leidas[sin].cuenta, leidas[sin].equivalencia) == (False, None)
    assert leidas[sin].sin_tasa == "sin tasa del BCV del 21/10/2026"


def test_la_equivalencia_de_la_observacion_trae_original_tasa_fecha_fuente_y_resultado(
    s: Session,
) -> None:
    usd = observacion_cruda(s, "MAT-001", Decimal("3.00"), moneda="USD", fecha=DIA_20)
    (leida,) = observaciones_leidas(s, "compra", "MAT-001", HOY)
    e = leida.equivalencia
    assert leida.fila.id == usd and leida.cuenta and leida.sin_tasa is None
    assert e is not None
    assert (e.precio_original, e.moneda_original, e.tasa, e.fecha_tasa) == (
        Decimal("3.00"),
        "USD",
        Decimal("36.50"),
        DIA_20,
    )
    assert (e.convertido, e.moneda, e.operacion) == (Decimal("109.50"), "Bs", "×")
    assert e.fuente_legible == "BCV, publicación del 20/10/2026"
    assert e.fuente_tasa.startswith("importacion:")


def test_en_una_carpeta_en_usd_una_observacion_en_bs_se_divide_por_la_tasa() -> None:
    for sesion in nueva_sesion(moneda="USD", con_lista=False):
        _tasas(sesion)
        observacion_cruda(sesion, "MAT-001", Decimal("146.00"), moneda="Bs", fecha=DIA_20)
        est = estadisticas(sesion, lado="compra", codigo="MAT-001", hoy=HOY)
        # 146,00 / 36,50 = 4,00
        assert (est.moneda, est.n, est.minimo, est.convertidas) == ("USD", 1, Decimal("4"), 1)
        (leida,) = observaciones_leidas(sesion, "compra", "MAT-001", HOY)
        assert leida.equivalencia is not None and leida.equivalencia.operacion == "÷"


def test_convertir_no_modifica_la_observacion_original(s: Session) -> None:
    usd = observacion_cruda(s, "MAT-001", Decimal("3.00"), moneda="USD", fecha=DIA_20)
    antes = (3, "USD", DIA_20)
    estadisticas(s, lado="compra", codigo="MAT-001", hoy=HOY)
    observaciones_leidas(s, "compra", "MAT-001", HOY)
    s.expire_all()
    fila = s.get(ObservacionDeMercado, usd)
    assert fila is not None
    assert (int(fila.precio), fila.moneda, fila.fecha) == antes
    assert fila.precio == Decimal("3.00")
    assert len(s.scalars(select(ObservacionDeMercado)).all()) == 1


def test_se_puede_citar_una_observacion_convertida_y_no_una_sin_tasa(s: Session) -> None:
    convertida = observacion_cruda(
        s, "OBRA-04", Decimal("3.00"), moneda="USD", lado="cobro", fecha=DIA_20
    )
    sin_tasa = observacion_cruda(
        s, "OBRA-04", Decimal("4.00"), moneda="USD", lado="cobro", fecha=DIA_21
    )
    objetivo = usar_precio_de_cobro(
        s, "OBRA-04", "109,50", observaciones=[convertida], responsable=RESPONSABLE, ahora=AHORA
    )
    assert objetivo.observaciones == f"[{convertida}]"
    with pytest.raises(ReglaDeMercado) as error:
        usar_precio_de_cobro(
            s, "OBRA-04", "109,50", observaciones=[sin_tasa], responsable=RESPONSABLE, ahora=AHORA
        )
    assert str(error.value) == (
        "La observación elegida está en USD y no hay tasa del BCV del 21/10/2026 para "
        "convertirla a Bs."
    )


def test_un_precio_de_compra_puede_citar_una_observacion_convertida(s: Session) -> None:
    """Caso positivo de compra: la observación en USD con tasa de su día se puede citar, y la fuente
    del precio la nombra; una sin tasa de su día se rechaza (cubierto arriba para el cobro)."""
    convertida = observacion_cruda(s, "MAT-001", Decimal("13.00"), moneda="USD", fecha=DIA_20)

    lista = usar_precio_de_compra(
        s,
        "MAT-001",
        "474,50",  # 13,00 USD x 36,50 Bs/USD, a mano
        observacion_id=convertida,
        fecha=HOY,
        responsable=RESPONSABLE,
    )

    fila = s.scalars(
        select(models.PrecioInsumo)
        .join(models.Insumo)
        .where(models.PrecioInsumo.lista_id == lista.id, models.Insumo.codigo == "MAT-001")
    ).one()
    assert fila.precio == Decimal("474.50")
    origen = s.get(models.PrecioOrigen, fila.id)
    assert origen is not None
    assert origen.fuente == f"Estudio de mercado: observación n.º {convertida}, por ana"
