"""Publicar el costo propio al catalogo como precio de la empresa (Tarea 5 del plan vial).

Datos FICTICIOS: la planta de noviembre de 2026 de `tests/fixtures/costo_propio.py` y una empresa
inventada. Oraculos a mano, ninguno sacado del codigo bajo prueba:

- En USD el calculo da `AGR-12` 5, `AGR-34` 5 y `MZ-1` 50,70 (ver `test_aplicacion_costo_propio`).
  Los insumos propios son `AGP-AGR-12`, `AGP-AGR-34` y `MZP-MZ-1` (D-V-2), material en t.
- Con un costo extra de cantera de 1 USD: 1.001 / 200 t = 5,005 por tonelada (presentado: 5,01) y la
  mezcla 0,94 x 5,005 + 30 + 4 + 12 = 4,7047 + 46 = 50,7047. Se publica el exacto (decision del
  orquestador, pregunta 18 de la bitacora).
- En Bs con la tasa de 36,50: lo publicado es 5 x 36,50 = 182,5 y 50,70 x 36,50 = 1.850,55; el
  cemento asfaltico heredado de la lista en USD es 600 x 36,50 = 21.900.
- La fuente de cada precio es «Producción, período 2026-11, cálculo n.º 7» cuando el cálculo es el
  septimo.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aplicacion.costo_propio import CalculoGuardado, calcular_periodo, publicar_calculo
from core import models
from core.catalog import Catalogo
from produccion.costo import ErrorDeCalculo
from produccion.costos import CostoDelPeriodo, registrar_costo
from tests.fixtures import costo_propio as cp

D = Decimal
P = cp.PERIODO
EMPRESA = ("Constructora Ejemplo, C.A.", "J-00000000-0")
FUENTE_7 = "Producción, período 2026-11, cálculo n.º 7"


@pytest.fixture
def ins() -> Iterator[Session]:
    with cp.instalacion_en_memoria() as sesion:
        yield sesion


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[Session]:
    with cp.carpeta_del_caso(tmp_path) as sesion:
        yield sesion


def _calcular(ins, caso, moneda="USD") -> CalculoGuardado:
    return calcular_periodo(ins, caso, P, moneda, usuario="ana", ahora=cp.AHORA)


def _publicar(caso, calculo, base=None) -> models.ListaPrecios:
    base = base or Catalogo(caso).lista_vigente(date(2026, 11, 30))
    return publicar_calculo(
        caso,
        calculo,
        base=base,
        empresa_nombre=EMPRESA[0],
        empresa_rif=EMPRESA[1],
        usuario="admin",
        ahora=cp.AHORA,
    )


def _precios(lista: models.ListaPrecios) -> dict[str, Decimal]:
    return {p.insumo.codigo: p.precio for p in lista.precios}


def _insumos(caso, codigo: str) -> list[models.Insumo]:
    return list(caso.scalars(select(models.Insumo).where(models.Insumo.codigo == codigo)))


def _listas(caso) -> int:
    return caso.scalar(select(func.count()).select_from(models.ListaPrecios)) or 0


# --- Lo que se publica ----------------------------------------------------------------------------


def test_publica_con_la_fuente_exacta(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    for _ in range(6):
        _calcular(ins, caso)
    septimo = _calcular(ins, caso)
    assert septimo.id == 7
    lista = _publicar(caso, septimo)
    publicados = [p for p in lista.precios if p.insumo.codigo.startswith(("AGP-", "MZP-"))]
    assert len(publicados) == 3
    for precio in publicados:
        origen = caso.get(models.PrecioOrigen, precio.id)
        assert origen.fuente == FUENTE_7
        assert origen.fecha_precio == date(2026, 11, 30)
        assert origen.moneda_original == "USD"


def test_los_precios_son_los_del_calculo_y_la_lista_la_de_la_empresa(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    lista = _publicar(caso, _calcular(ins, caso))
    precios = _precios(lista)
    assert precios["AGP-AGR-12"] == D("5")
    assert precios["AGP-AGR-34"] == D("5")
    assert precios["MZP-MZ-1"] == D("50.70")
    assert precios["CA-30"] == D("600") and precios["GO"] == D("0.5")  # heredados de la base
    assert (lista.moneda, lista.fecha_vigencia) == ("USD", date(2026, 11, 30))
    empresa = caso.scalar(
        select(models.ListaEmpresa).where(models.ListaEmpresa.lista_id == lista.id)
    )
    assert (empresa.empresa_nombre, empresa.empresa_rif) == EMPRESA
    origen = caso.get(models.ListaPreciosOrigen, lista.id)
    assert origen.alcance == models.ALCANCE_EMPRESA


def test_los_insumos_propios_son_material_en_toneladas(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    _publicar(caso, _calcular(ins, caso))
    for codigo in ("AGP-AGR-12", "AGP-AGR-34", "MZP-MZ-1"):
        (insumo,) = _insumos(caso, codigo)
        assert (insumo.tipo, insumo.unidad) == ("material", "t")


def test_se_publica_el_valor_exacto_y_no_el_redondeado(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    cp.costo(ins, "cantera", "1", "USD", cp.dia(6))
    calculo = _calcular(ins, caso)
    assert calculo.por_tonelada["AGR-12"] == D("5.005")
    precios = _precios(_publicar(caso, calculo))
    assert precios["AGP-AGR-12"] == D("5.005")  # no 5,01
    assert precios["MZP-MZ-1"] == D("50.7047")


# --- Nada se sobrescribe --------------------------------------------------------------------------


def test_da_de_alta_el_insumo_una_sola_vez(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso)
    _publicar(caso, calculo)
    _publicar(caso, calculo)
    for codigo in ("AGP-AGR-12", "AGP-AGR-34", "MZP-MZ-1"):
        assert len(_insumos(caso, codigo)) == 1


def test_cada_publicacion_es_una_lista_nueva(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso)
    antes = _listas(caso)
    primera = _publicar(caso, calculo)
    cp.costo(ins, "cantera", "1", "USD", cp.dia(6))
    segunda = _publicar(caso, _calcular(ins, caso))
    assert _listas(caso) == antes + 2 and primera.id != segunda.id
    assert _precios(primera)["AGP-AGR-12"] == D("5")  # la primera quedo como estaba
    assert _precios(segunda)["AGP-AGR-12"] == D("5.005")


def test_la_lista_publicada_no_es_la_vigente_de_los_calculos_siguientes(ins, caso) -> None:
    """Nota 2 del arbitro: con alcance de empresa, `lista_vigente` no la resuelve y el calculo de
    diciembre sigue leyendo el cemento asfaltico y el gasoil de la lista de la carpeta."""
    cp.noviembre_usd(ins, caso)
    base = Catalogo(caso).lista_vigente(date(2026, 11, 30))
    publicada = _publicar(caso, _calcular(ins, caso), base)
    assert publicada.id != base.id and publicada.fecha_vigencia >= base.fecha_vigencia
    assert Catalogo(caso).lista_vigente(date(2026, 12, 31)).id == base.id
    cp.entrada(ins, "AGR-12", "150", date(2026, 12, 5))
    cp.entrada(ins, "AGR-34", "50", date(2026, 12, 5))
    cp.producir(ins, "100", date(2026, 12, 10))
    for centro, monto in (("cantera", "1000"), ("planta", "1200")):
        diciembre = CostoDelPeriodo(
            "2026-12", centro, "otro", D(monto), "USD", date(2026, 12, 8), "f"
        )
        registrar_costo(ins, diciembre, usuario="ana", ahora=cp.AHORA)
    siguiente = calcular_periodo(ins, caso, "2026-12", "USD", usuario="ana", ahora=cp.AHORA)
    assert siguiente.por_tonelada["MZ-1"] == D("50.70")
    usados = {c: d["lista"]["id"] for c, d in _instantanea(siguiente)["precios_comprados"].items()}
    assert usados == {"CA-30": base.id, "GO": base.id}


def _instantanea(calculo: CalculoGuardado) -> dict:
    return json.loads(calculo.instantanea)["entradas"]


# --- El APU usa el costo publicado ----------------------------------------------------------------


def test_el_apu_usa_el_costo_publicado(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    lista = _publicar(caso, _calcular(ins, caso))
    mezcla = _insumos(caso, "MZP-MZ-1")[0]
    partida = models.Partida(
        codigo="VIAL-01", descripcion="Carpeta asfaltica ficticia", unidad="m3", dominio="civil"
    )
    caso.add(partida)
    caso.flush()
    caso.add(
        models.ComposicionAPU(partida_id=partida.id, insumo_id=mezcla.id, cantidad=D("2"), orden=1)
    )
    caso.add(
        models.Rendimiento(partida_id=partida.id, valor=D("10"), tipo="estimado", fecha=cp.dia(1))
    )
    caso.flush()
    caso.expire(partida)
    apu = Catalogo(caso).composicion("VIAL-01", date(2026, 12, 1), lista=lista)
    assert [(m.cantidad, m.precio) for m in apu.materiales] == [(D("2"), D("50.70"))]


# --- Moneda y negativas ---------------------------------------------------------------------------


def test_en_bs_la_base_en_usd_se_convierte_con_la_tasa_del_dia(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    cp.tasas(
        caso,
        {
            cp.dia(1): cp.TASA,
            cp.dia(3): cp.TASA,
            cp.dia(4): cp.TASA,
            cp.dia(12): cp.TASA,
            cp.dia(28): cp.TASA,
        },
    )
    calculo = _calcular(ins, caso, "Bs")
    lista = _publicar(caso, calculo)
    precios = _precios(lista)
    assert lista.moneda == "Bs"
    assert precios["AGP-AGR-12"] == D("182.5") and precios["MZP-MZ-1"] == D("1850.55")
    assert precios["CA-30"] == D("21900")


def test_sin_tasa_para_convertir_la_base_no_se_escribe_nada(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    # la ultima tasa es del 12/11: a mas de 7 dias del 30/11 no sirve para llevar la base a Bs
    cp.tasas(caso, {fecha: cp.TASA for fecha in (cp.dia(1), cp.dia(3), cp.dia(4), cp.dia(12))})
    calculo = _calcular(ins, caso, "Bs")
    antes = _listas(caso)
    with pytest.raises(ValueError, match="tasa"):
        _publicar(caso, calculo, Catalogo(caso).lista_vigente(date(2026, 11, 30)))
    assert _listas(caso) == antes and _insumos(caso, "MZP-MZ-1") == []


def test_codigo_de_insumo_demasiado_largo_se_niega_y_lo_nombra(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso)
    largo = CalculoGuardado(
        calculo.id,
        P,
        "USD",
        {"AGR-MUY-LARGO-123456": D("5")},
        calculo.huella,
        instantanea=calculo.instantanea,
    )
    antes = _listas(caso)
    with pytest.raises(ErrorDeCalculo, match="AGP-AGR-MUY-LARGO-123456"):
        _publicar(caso, largo)
    assert _listas(caso) == antes


def test_la_empresa_vacia_se_niega_sin_escribir(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso)
    antes = _listas(caso)
    with pytest.raises(ValueError, match="empresa"):
        publicar_calculo(
            caso,
            calculo,
            base=Catalogo(caso).lista_vigente(date(2026, 11, 30)),
            empresa_nombre=" ",
            empresa_rif=EMPRESA[1],
            usuario="admin",
            ahora=cp.AHORA,
        )
    assert _listas(caso) == antes
