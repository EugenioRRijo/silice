"""RF-100 sobre las listas del caso: ADVERTENCIA, nunca ERROR; listas de proyecto fuera; la tasa
de cada precio; y sin el extra `ml`, nada (S3 §3.2 y §13.2)."""

from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core import models
from core.catalog.empresa import PrecioPropio, crear_lista_de_empresa
from core.contracts.verificacion import Severidad
from ml.anomaly.series import a_usd, variaciones
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


def _otro_insumo(sesion):
    fila = models.Insumo(
        codigo="ATIP-002", tipo=models.TipoInsumo.MATERIAL, descripcion="Grava", unidad="m3"
    )
    sesion.add(fila)
    sesion.flush()
    return fila


def _empresa(sesion, base, insumo, precio, dia, nombre):
    """Una lista de empresa con un precio propio del insumo (fecha y fuente suyas)."""
    return crear_lista_de_empresa(
        sesion,
        "Constructora Ejemplo, C.A.",
        "J-00000000-0",
        base,
        [PrecioPropio(insumo.id, D(precio), dia, "cotizacion de prueba")],
        moneda="USD",
        fecha=dia,
        fuente="prueba",
        referencia=None,
        nombre=nombre,
    )


def test_dos_listas_independientes_con_el_mismo_precio_y_fecha_son_dos_puntos(
    sesion, insumo
) -> None:
    """Solo lo heredado de la base es la misma observación: dos empresas que cotizan lo mismo el
    mismo día son dos observaciones distintas."""
    base = _lista(sesion, 1, "Base")
    _precio(sesion, base, insumo, 10)
    _empresa(sesion, base, insumo, 12, date(2026, 3, 1), "Empresa A")
    _empresa(sesion, base, insumo, 12, date(2026, 3, 1), "Empresa B")
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.origen, p.monto) for p in puntos] == [
        ("Base", D(10)),
        ("Empresa A", D(12)),
        ("Empresa B", D(12)),
    ]


def test_el_mismo_precio_en_dos_fechas_deja_su_variacion_de_cero(sesion, insumo) -> None:
    _precio(sesion, _lista(sesion, 1, "Enero"), insumo, 10)
    _precio(sesion, _lista(sesion, 2, "Febrero"), insumo, 10)
    usd = a_usd(atipicos.puntos_del_insumo(sesion, "ATIP-001"))
    assert list(variaciones(usd).values()) == [D(0)]


def test_lo_heredado_de_una_lista_de_empresa_que_a_su_vez_hereda_tampoco_se_repite(
    sesion, insumo
) -> None:
    base = _lista(sesion, 1, "Base")
    _precio(sesion, base, insumo, 10)
    primera = crear_lista_de_empresa(
        sesion,
        "Constructora Ejemplo, C.A.",
        "J-00000000-0",
        base,
        [],
        moneda="USD",
        fecha=date(2026, 2, 1),
        fuente="prueba",
        referencia=None,
        nombre="Primera",
    )
    crear_lista_de_empresa(
        sesion,
        "Constructora Ejemplo, C.A.",
        "J-00000000-0",
        primera,
        [],
        moneda="USD",
        fecha=date(2026, 3, 1),
        fuente="prueba",
        referencia=None,
        nombre="Segunda",
    )
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.origen, p.monto) for p in puntos] == [("Base", D(10))]


def test_un_precio_en_bs_sin_tasa_se_omite_y_la_busqueda_lo_nombra(sesion, insumo) -> None:
    """«Se nombra» llega al usuario, no solo a `SerieEnUsd.sin_tasa`."""
    _precio(sesion, _lista(sesion, 1, "Lista en USD"), insumo, 10)
    _precio(sesion, _lista(sesion, 2, "Lista en Bs sin tasa", "Bs"), insumo, 720)
    busqueda = atipicos.atipicos_de_insumos(sesion, ["ATIP-001"])
    assert busqueda.sin_tasa == ("Lista en Bs sin tasa",) and busqueda.hallazgos == ()


def test_la_busqueda_de_varios_insumos_junta_hallazgos_y_no_repite_listas_sin_tasa(
    sesion, insumo
) -> None:
    otro = _otro_insumo(sesion)
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    sin_tasa = _lista(sesion, 11, "Lista en Bs sin tasa", "Bs")
    _precio(sesion, sin_tasa, insumo, 720)
    _precio(sesion, sin_tasa, otro, 90)
    busqueda = atipicos.atipicos_de_insumos(sesion, ["ATIP-001", "ATIP-002"])
    assert [h.origen_ids for h in busqueda.hallazgos] == [("ATIP-001|2026-09-01>2026-10-01#8",)]
    assert busqueda.sin_tasa == ("Lista en Bs sin tasa",)


def test_la_busqueda_de_varios_insumos_lee_los_origenes_de_cada_lista_una_sola_vez(
    sesion, insumo, monkeypatch
) -> None:
    otro = _otro_insumo(sesion)
    for mes in (1, 2, 3):
        lista = _lista(sesion, mes, f"Lista {mes}")
        _precio(sesion, lista, insumo, mes)
        _precio(sesion, lista, otro, mes)
    llamadas = []
    original = atipicos.origenes_efectivos

    def contado(s, lista):
        llamadas.append(lista.id)
        return original(s, lista)

    monkeypatch.setattr(atipicos, "origenes_efectivos", contado)
    atipicos.atipicos_de_insumos(sesion, ["ATIP-001", "ATIP-002"])
    assert len(llamadas) == 3 == len(set(llamadas))


def test_sin_el_extra_ml_la_busqueda_de_insumos_devuelve_none(sesion, insumo, monkeypatch) -> None:
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    relacionados = ("ml", "ml.anomaly", "ml.anomaly.series", "ml.anomaly.detector")
    with SinExtra(monkeypatch, ("ml",), relacionados):
        assert atipicos.atipicos_de_insumos(sesion, ["ATIP-001"]) is None


def test_la_busqueda_no_escribe_nada_en_la_base(sesion, insumo) -> None:
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    sesion.flush()
    tablas = (models.PrecioInsumo, models.ListaPrecios, models.PrecioOrigen)
    antes = {t: sesion.scalar(select(func.count()).select_from(t)) for t in tablas}
    atipicos.atipicos_de_insumos(sesion, ["ATIP-001"])
    assert not (sesion.new or sesion.dirty or sesion.deleted)
    assert {t: sesion.scalar(select(func.count()).select_from(t)) for t in tablas} == antes


def test_solo_las_dos_pantallas_de_precios_importan_la_busqueda_de_rf_100() -> None:
    """RF-100 no entra al informe de verificación, a la entrega ni al guardado: ningún módulo de
    `core/`, `paquete/`, `api/`, `seguridad/`, `operacion/`, `asistente/`, `ui/` (salvo las dos
    pantallas) ni `ml/` importa `ui.atipicos` ni `ml.anomaly.series`."""
    raiz = Path(__file__).resolve().parents[2]
    permitidos = {"ui/paginas/hoja.py", "ui/paginas/precios_empresa.py", "ui/atipicos.py"}
    importadores = set()
    for carpeta in ("core", "paquete", "api", "seguridad", "operacion", "asistente", "ui", "ml"):
        for archivo in (raiz / carpeta).rglob("*.py"):
            nombres = set()
            for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
                if isinstance(nodo, ast.Import):
                    nombres.update(a.name for a in nodo.names)
                elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                    nombres.add(nodo.module)
                    nombres.update(f"{nodo.module}.{a.name}" for a in nodo.names)
            if nombres & {"ui.atipicos", "ml.anomaly.series"}:
                importadores.add(archivo.relative_to(raiz).as_posix())
    assert importadores <= permitidos, importadores - permitidos


def test_un_propio_igual_al_de_la_base_pero_de_otra_fecha_no_es_herencia(sesion, insumo) -> None:
    """Cada campo del criterio de herencia cuenta: la fecha del precio distingue la observación."""
    base = _lista(sesion, 1, "Base")
    _precio(sesion, base, insumo, 10)
    _empresa(sesion, base, insumo, 10, date(2026, 3, 1), "Empresa")
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.origen, p.fecha, p.monto) for p in puntos] == [
        ("Base", date(2026, 1, 1), D(10)),
        ("Empresa", date(2026, 3, 1), D(10)),
    ]
    assert list(variaciones(a_usd(puntos)).values()) == [D(0)]


def test_un_propio_igual_al_de_la_base_con_otra_fuente_no_es_herencia(sesion, insumo) -> None:
    """Misma moneda, precio y fecha, pero la fuente es otra (la cotización de la empresa)."""
    base = _lista(sesion, 1, "Base")
    _precio(sesion, base, insumo, 10)
    _empresa(sesion, base, insumo, 10, date(2026, 1, 1), "Empresa")
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [p.origen for p in puntos] == ["Base", "Empresa"]


def test_el_criterio_de_herencia_es_el_mismo_que_el_del_nucleo() -> None:
    """La tupla de la interfaz es copia de la del núcleo (que es privada): no se separan."""
    from core.catalog import empresa

    assert atipicos._CAMPOS_DE_HERENCIA == empresa._CAMPOS_DE_HERENCIA


def test_una_moneda_invalida_no_tumba_la_busqueda_de_los_demas_insumos(sesion, insumo) -> None:
    otro = _otro_insumo(sesion)
    _precio(sesion, _lista(sesion, 1, "Lista en euros", "EUR"), otro, 5)
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    busqueda = atipicos.atipicos_de_insumos(sesion, ["ATIP-002", "ATIP-001"])
    assert [h.origen_ids for h in busqueda.hallazgos] == [("ATIP-001|2026-09-01>2026-10-01#8",)]
    [(codigo, motivo)] = busqueda.no_analizados
    assert codigo == "ATIP-002" and "EUR" in motivo
    avisos = atipicos.avisos(busqueda)
    assert avisos[0][0] == "info" and avisos[0][1].startswith("ATIP\\-002: no se pudo analizar")
    assert [nivel for nivel, _ in avisos[1:]] == ["warning"]
