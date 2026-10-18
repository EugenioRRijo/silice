"""RF-100 sobre las listas del caso: ADVERTENCIA, nunca ERROR; listas de proyecto fuera; la tasa
de cada precio; y sin el extra `ml`, nada (S3 §3.2 y §13.2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from core import models
from core.catalog.empresa import PrecioPropio, crear_lista_de_empresa
from core.contracts.verificacion import Severidad
from ml.anomaly.series import a_usd
from tests.fixtures.sin_extra import SinExtra
from ui import atipicos

D = Decimal
SERIE_CON_ATIPICO = [1, 2, 4, 8, 16, 32, 64, 128, 256, 257]


def _lista(
    sesion: Session,
    mes: int,
    nombre: str,
    moneda: str = "USD",
    tasa=None,
    alcance: str = models.ALCANCE_GLOBAL,
):
    lista = models.ListaPrecios(
        nombre=nombre, moneda=moneda, fecha_vigencia=date(2026, mes, 1), origen="prueba"
    )
    sesion.add(lista)
    sesion.flush()
    if tasa is not None or alcance != models.ALCANCE_GLOBAL:
        sesion.add(models.ListaPreciosOrigen(lista_id=lista.id, tasa=tasa, alcance=alcance))
    return lista


def _precio(sesion: Session, lista, insumo, valor):
    fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=D(valor))
    sesion.add(fila)
    sesion.flush()
    return fila


@pytest.fixture
def insumo(sesion: Session):
    fila = models.Insumo(
        codigo="ATIP-001", tipo=models.TipoInsumo.MATERIAL, descripcion="Arena", unidad="m3"
    )
    sesion.add(fila)
    sesion.flush()
    return fila


def _sembrar(sesion, insumo, precios) -> None:
    for mes, precio in enumerate(precios, start=1):
        _precio(sesion, _lista(sesion, mes, f"MaPreX {mes:02d}"), insumo, precio)


def test_la_serie_sembrada_de_10_precios_da_un_unico_hallazgo_advertencia(sesion, insumo) -> None:
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    [h] = atipicos.atipicos_del_insumo(sesion, "ATIP-001")
    assert (h.regla, h.severidad) == ("ATIPICO", Severidad.ADVERTENCIA)
    assert h.valor_observado == D("0.00390625") and "0.39 %" in h.descripcion
    assert h.origen_ids == ("ATIP-001|2026-09-01>2026-10-01#8",)


def test_con_serie_corta_el_conjunto_es_vacio(sesion, insumo) -> None:
    _sembrar(sesion, insumo, [1, 2, 4, 8, 16, 32, 64, 128])
    assert atipicos.atipicos_del_insumo(sesion, "ATIP-001") == []


def test_ningun_hallazgo_de_rf_100_es_error(sesion, insumo) -> None:
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    assert all(
        h.severidad is Severidad.ADVERTENCIA
        for h in atipicos.atipicos_del_insumo(sesion, "ATIP-001")
    )


def test_las_listas_de_proyecto_no_entran_en_la_serie(sesion, insumo) -> None:
    _precio(sesion, _lista(sesion, 1, "Global"), insumo, 10)
    _precio(sesion, _lista(sesion, 2, "Cotización", alcance=models.ALCANCE_PROYECTO), insumo, 99)
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.origen, p.monto) for p in puntos] == [("Global", D(10))]


def test_las_listas_de_la_empresa_y_la_de_referencia_si_entran(sesion, insumo) -> None:
    """La spec habla de «las listas de la empresa y las MaPreX»: solo `proyecto` queda fuera."""
    _precio(sesion, _lista(sesion, 1, "Global"), insumo, 10)
    _precio(sesion, _lista(sesion, 2, "Empresa", alcance=models.ALCANCE_EMPRESA), insumo, 11)
    _precio(sesion, _lista(sesion, 3, "MaPreX", alcance=models.ALCANCE_REFERENCIA), insumo, 12)
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.origen, p.monto) for p in puntos] == [
        ("Global", D(10)),
        ("Empresa", D(11)),
        ("MaPreX", D(12)),
    ]


def test_un_precio_en_bs_lleva_la_tasa_de_su_lista(sesion, insumo) -> None:
    _precio(sesion, _lista(sesion, 8, "Agosto", "Bs", tasa=D(36)), insumo, 720)
    _precio(sesion, _lista(sesion, 9, "Septiembre", "Bs", tasa=D(44)), insumo, 1100)
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.moneda, p.monto, p.tasa) for p in puntos] == [
        ("Bs", D(720), D(36)),
        ("Bs", D(1100), D(44)),
    ]


def test_el_origen_del_precio_manda_sobre_la_lista(sesion, insumo) -> None:
    lista = _lista(sesion, 5, "Empresa", "Bs", tasa=D(10))
    precio = _precio(sesion, lista, insumo, 500)
    sesion.add(
        models.PrecioOrigen(
            precio_id=precio.id,
            moneda_original="USD",
            precio_original=D(12),
            fecha_precio=date(2026, 4, 20),
            tasa=None,
        )
    )
    sesion.flush()
    [punto] = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert (punto.fecha, punto.moneda, punto.monto) == (date(2026, 4, 20), "USD", D(12))


def test_dos_listas_con_la_misma_fecha_se_ordenan_por_el_nombre_de_la_lista(sesion, insumo) -> None:
    """Memoria §5: a igual fecha manda el nombre de la lista, no el orden de las filas."""
    _precio(sesion, _lista(sesion, 6, "Zeta"), insumo, 30)
    _precio(sesion, _lista(sesion, 6, "Alfa"), insumo, 10)
    _precio(sesion, _lista(sesion, 6, "Beta"), insumo, 20)
    usd = a_usd(atipicos.puntos_del_insumo(sesion, "ATIP-001"))
    assert [(o, p) for _, p, o in usd.puntos] == [("Alfa", D(10)), ("Beta", D(20)), ("Zeta", D(30))]


def test_el_precio_heredado_por_una_lista_de_empresa_no_repite_el_punto_de_su_base(
    sesion, insumo
) -> None:
    """La lista de la empresa copia la base con el mismo `PrecioOrigen`: es la misma observación,
    no una variación de 0 entre dos listas."""
    base = _lista(sesion, 1, "Base")
    _precio(sesion, base, insumo, 10)
    empresa = crear_lista_de_empresa(
        sesion,
        "Constructora Ejemplo, C.A.",
        "J-00000000-0",
        base,
        [],
        moneda="USD",
        fecha=date(2026, 2, 1),
        fuente="prueba",
        referencia=None,
    )
    assert len(empresa.precios) == 1  # el precio heredado existe en la lista de la empresa
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.fecha, p.monto) for p in puntos] == [(date(2026, 1, 1), D(10))]


def test_el_precio_propio_de_la_empresa_si_es_un_punto_nuevo(sesion, insumo) -> None:
    base = _lista(sesion, 1, "Base")
    _precio(sesion, base, insumo, 10)
    crear_lista_de_empresa(
        sesion,
        "Constructora Ejemplo, C.A.",
        "J-00000000-0",
        base,
        [PrecioPropio(insumo.id, D(12), date(2026, 3, 1), "cotizacion de prueba")],
        moneda="USD",
        fecha=date(2026, 3, 1),
        fuente="prueba",
        referencia=None,
    )
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.fecha, p.monto) for p in puntos] == [
        (date(2026, 1, 1), D(10)),
        (date(2026, 3, 1), D(12)),
    ]


def test_los_codigos_de_la_lista_son_los_insumos_que_valora(sesion, insumo) -> None:
    otro = models.Insumo(
        codigo="ATIP-002", tipo=models.TipoInsumo.MATERIAL, descripcion="Grava", unidad="m3"
    )
    sesion.add(otro)
    sesion.flush()
    lista = _lista(sesion, 1, "Lista")
    _precio(sesion, lista, otro, 5)
    _precio(sesion, lista, insumo, 6)
    assert atipicos.codigos_de_la_lista(sesion, lista.id) == ["ATIP-001", "ATIP-002"]


def test_sin_el_extra_ml_no_hay_hallazgo_ni_traza(sesion, insumo, monkeypatch) -> None:
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    relacionados = ("ml", "ml.anomaly", "ml.anomaly.series", "ml.anomaly.detector")
    with SinExtra(monkeypatch, ("ml",), relacionados):
        assert atipicos.atipicos_del_insumo(sesion, "ATIP-001") is None


def test_un_insumo_sin_precios_no_da_nada(sesion) -> None:
    assert atipicos.atipicos_del_insumo(sesion, "NO-EXISTE") == []
