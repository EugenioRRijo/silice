"""RF-67 y UC-17 4 (S1 §6.1, §9.2)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from core import models
from core.catalog import Catalogo, CatalogoIncompleto, leer_lista_precios
from core.catalog.empresa import (
    crear_lista_de_empresa,
    crear_lista_de_referencia,
    es_heredado,
    precios_propios_desde,
)
from core.catalog.moneda import TasaDeclarada
from scripts.lista_maprex_bs import FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX, RUTA_SALIDA, TASA_MAPREX
from tests.fixtures.apu_linea_base import APU_EXCAVACION

CSV_EMPRESA = Path(__file__).resolve().parents[1] / "fixtures" / "precios_empresa_s1.csv"


@pytest.fixture
def referencia(sesion):
    lista = crear_lista_de_referencia(
        sesion,
        RUTA_SALIDA,
        nombre="MaPreX julio 2026 en Bs",
        moneda="Bs",
        tasa=TasaDeclarada(TASA_MAPREX, FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX),
    )
    Catalogo(sesion).dar_de_alta_insumo(models.TipoInsumo.MATERIAL, "LIJA DE AGUA N 100", "pza")
    return lista


def _empresa(sesion, referencia, nombre="Constructora Ejemplo, C.A.", rif="J-00000000-0"):
    propios, desconocidos = precios_propios_desde(sesion, leer_lista_precios(CSV_EMPRESA))
    assert not desconocidos
    return crear_lista_de_empresa(
        sesion,
        nombre,
        rif,
        referencia,
        propios,
        moneda="Bs",
        fecha=date(2026, 9, 20),
        fuente="lista interna 2026-09",
        referencia=referencia,
    )


def test_ni_la_empresa_ni_la_referencia_entran_a_lista_vigente(sesion, referencia):
    _empresa(sesion, referencia)
    assert Catalogo(sesion).lista_vigente(date(2031, 1, 1)).moneda == "USD"  # la de la clínica


def test_propio_prevalece_heredado_marcado_y_empresa_como_texto(sesion, referencia):
    lista = _empresa(sesion, referencia)
    precios = {p.insumo.descripcion: p for p in lista.precios}
    assert precios["ARENA LAVADA"].precio == Decimal("49078.775")
    assert es_heredado(sesion, lista, precios["MATERIAL GRANULAR INTEGRAL"]) is True
    assert es_heredado(sesion, lista, precios["ARENA LAVADA"]) is False
    fila = sesion.get(models.ListaEmpresa, lista.id)
    assert (fila.empresa_nombre, fila.empresa_rif, fila.rango_inferior) == (
        "Constructora Ejemplo, C.A.",
        "J-00000000-0",
        Decimal("-0.20"),
    )
    pegamento = precios["PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM"]
    origen = sesion.get(models.PrecioOrigen, pegamento.id)
    assert (pegamento.precio, origen.moneda_original, origen.fecha_tasa) == (
        Decimal("21000.00"),
        "USD",
        None,
    )


def test_dos_empresas_aisladas(sesion, referencia):
    una = _empresa(sesion, referencia)
    otra = _empresa(sesion, referencia, "Otra, S.A.", "J-11111111-1")
    assert {p.id for p in una.precios}.isdisjoint({p.id for p in otra.precios})


def test_coma_decimal_se_rechaza_con_fila_y_motivo(tmp_path):
    """[Foco 4] «13288,00» o «13.288,00» nunca se leen como otro número."""
    ruta = tmp_path / "coma.csv"
    ruta.write_text(
        'tipo,insumo,unidad,precio\nmaterial,ARENA LAVADA,m3,"13.288,00"\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match=r"fila 2.*punto"):
        leer_lista_precios(ruta)


def test_moneda_ajena_se_rechaza(sesion, referencia):
    with pytest.raises(ValueError, match="4b"):
        crear_lista_de_empresa(
            sesion,
            "X",
            "J-1",
            referencia,
            [],
            moneda="EUR",
            fecha=date(2026, 9, 20),
            fuente="x",
            referencia=referencia,
        )


def test_insumo_sin_precio_en_la_moneda_de_la_lista_no_valora(sesion, referencia):
    """[Foco 5] una partida de la clínica valorada con la lista de empresa en Bs: el insumo que la
    base no trae da CatalogoIncompleto que lo nombra, sin escribir nada."""
    lista = _empresa(sesion, referencia)
    with pytest.raises(CatalogoIncompleto, match=lista.nombre):
        Catalogo(sesion).composicion(APU_EXCAVACION.codigo_partida, lista=lista)  # "LB-01-EXC"


def test_texto_en_celda_numerica_se_rechaza_con_fila(tmp_path):
    """[Foco 4] una celda de texto en `precio` o `tasa` nunca se toma como cero."""
    ruta = tmp_path / "texto.csv"
    ruta.write_text(
        "tipo,insumo,unidad,precio,tasa\n"
        "material,ARENA LAVADA,m3,100,\n"
        "material,CEMENTO,sco,consultar,\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"fila 3.*consultar"):
        leer_lista_precios(ruta)
    ruta.write_text(
        'tipo,insumo,unidad,precio,tasa\nmaterial,ARENA LAVADA,m3,100,"633,36"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"fila 2.*punto"):
        leer_lista_precios(ruta)
