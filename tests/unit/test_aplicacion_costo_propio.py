"""Costo por tonelada del periodo, convertido y guardado con sus entradas (Tarea 4 del plan vial).

Datos FICTICIOS: la planta de noviembre de 2026 de `tests/fixtures/costo_propio.py`. Oraculos a
mano, ninguno sacado del codigo bajo prueba:

- En USD, cantera 600 + 400 = 1.000 sobre los agregados (150 + 50 t; la mezcla NO entra al reparto
  aunque `producido_en_periodo` la traiga): 5 por tonelada. Planta 1.200 / 100 t de mezcla = 12.
  Mezcla: 0,94 x 5 + 0,05 x 600 + 8 x 0,5 + 12 = 50,70.
- Un costo de 36.500 Bs del 03/11 con tasa de 36,50 Bs/USD ese dia son 1.000 USD.
- En Bs con todo en USD del 03/11 a 36,50: cantera 36.500 / 200 = 182,5; planta 43.800 / 100 = 438;
  mezcla con la lista en Bs: 0,94 x 182,5 + 0,05 x 21.900 + 8 x 18,25 + 438 = 171,55 + 1.095 + 146 +
  438 = 1.850,55 (= 50,70 x 36,50).
- Receta que cambia el 16/11: 60 t con A (38,70 sin planta) y 40 t con B (0,95 x 5 + 0,04 x 600 +
  10 x 0,5 = 33,75): (2.322 + 1.350) / 100 + 12 = 48,72.
- Pesos 0,6 y 0,4: 1.000 x 0,6 / 150 = 4 y 1.000 x 0,4 / 50 = 8; mezcla 0,94 x 4 + 30 + 4 + 12 =
  49,76.
- Mezcla en m3 con densidad 2,3: 100 t se guardan como 100 / 2,3 = 43,4783 m3 (cuatro decimales) y
  vuelven como 43,4783 x 2,3 = 100,00009 t; la planta queda en 1.200 / 100,00009 por tonelada.
- El 07/11/2026 es sabado y el 08/11 domingo: sin tasa BCV esos dias.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from aplicacion.costo_propio import (
    CalculoInexistente,
    FaltanTasas,
    calcular_periodo,
    calculo_guardado,
    ultimo_calculo,
)
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from produccion.costo import ErrorDeCalculo
from produccion.costos import anular_costo
from produccion.modelo import METADATA_PRODUCCION, Calculo
from produccion.receta import producido_en_periodo
from tests.fixtures import costo_propio as cp

D = Decimal
P = cp.PERIODO


@pytest.fixture
def ins() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    with Session(motor) as s:
        yield s
    motor.dispose()


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[Session]:
    ruta = tmp_path / "carpeta.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            yield sesion
            sesion.rollback()
    finally:
        motor.dispose()


def _calcular(ins, caso, moneda="USD", **kw):
    return calcular_periodo(ins, caso, P, moneda, usuario="ana", ahora=cp.AHORA, **kw)


def _calculos(ins) -> int:
    return ins.scalar(select(func.count()).select_from(Calculo)) or 0


def _instantanea(ins, calculo_id: int) -> dict:
    return json.loads(ins.get(Calculo, calculo_id).instantanea)


def _noviembre_usd(ins, caso) -> None:
    cp.planta(ins)
    cp.costos_usd(ins)
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)


# --- El calculo -----------------------------------------------------------------------------------


def test_costo_por_tonelada_del_periodo_en_usd(ins, caso) -> None:
    _noviembre_usd(ins, caso)
    assert producido_en_periodo(ins, P)["MZ-1"] == D("100")  # la mezcla esta en lo producido...
    calculo = _calcular(ins, caso)
    # ...pero no recibe costo de cantera: 1.000 / 200 = 5, no 1.000 / 300
    assert calculo.por_tonelada == {"AGR-12": D("5"), "AGR-34": D("5"), "MZ-1": D("50.70")}
    assert (calculo.periodo, calculo.moneda) == (P, "USD")
    assert (calculo.usuario, calculo.registrado) == ("ana", cp.AHORA)
    assert _calculos(ins) == 1


def test_un_costo_en_bs_se_convierte_con_la_tasa_de_su_dia(ins, caso) -> None:
    cp.planta(ins)
    cp.costo(ins, "cantera", "36500", "Bs", cp.dia(3))
    cp.costo(ins, "planta", "1200", "USD", cp.dia(12))
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    cp.tasas(caso, {cp.dia(2): "30", cp.dia(3): cp.TASA, cp.dia(4): "40"})
    calculo = _calcular(ins, caso)
    assert calculo.por_tonelada == {"AGR-12": D("5"), "AGR-34": D("5"), "MZ-1": D("50.70")}
    bs = [c for c in _instantanea(ins, calculo.id)["entradas"]["costos"] if c["moneda"] == "Bs"]
    assert len(bs) == 1
    assert bs[0]["tasa"]["valor"] == "36.50" and bs[0]["tasa"]["fecha"] == "2026-11-03"
    assert D(bs[0]["convertido"]) == D("1000")


def test_costo_en_bs_sin_tasa_ese_dia_falla_y_lo_nombra(ins, caso) -> None:
    """Foco 1: dos monedas y dos dias sin tasa (sabado y domingo): no se calcula a medias y el error
    nombra CADA costo sin tasa con su fecha; el que si tiene tasa no aparece."""
    cp.planta(ins)
    con_tasa = cp.costo(ins, "cantera", "36500", "Bs", cp.dia(3))
    sabado = cp.costo(ins, "cantera", "100", "Bs", cp.dia(7))
    domingo = cp.costo(ins, "planta", "200", "Bs", cp.dia(8))
    cp.costo(ins, "planta", "1200", "USD", cp.dia(12))
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    cp.tasas(caso, {cp.dia(3): cp.TASA, cp.dia(6): cp.TASA, cp.dia(9): cp.TASA})
    with pytest.raises(FaltanTasas) as error:
        _calcular(ins, caso)
    mensaje = str(error.value)
    assert f"n.º {sabado} del 07/11/2026" in mensaje
    assert f"n.º {domingo} del 08/11/2026" in mensaje
    assert f"n.º {con_tasa} " not in mensaje
    assert error.value.faltan == (
        f"costo n.º {sabado} del 07/11/2026",
        f"costo n.º {domingo} del 08/11/2026",
    )
    assert _calculos(ins) == 0


def test_calculo_en_bs(ins, caso) -> None:
    cp.planta(ins)
    cp.costo(ins, "cantera", "1000", "USD", cp.dia(3))
    cp.costo(ins, "planta", "1200", "USD", cp.dia(3))
    cp.lista(caso, "Bs", cp.dia(1), cp.LISTA_BS)
    cp.tasas(caso, {cp.dia(3): cp.TASA})
    calculo = _calcular(ins, caso, "Bs")
    assert calculo.por_tonelada == {
        "AGR-12": D("182.5"),
        "AGR-34": D("182.5"),
        "MZ-1": D("1850.55"),
    }


def test_la_receta_que_cambia_a_mitad_de_mes_pondera_por_toneladas(ins, caso) -> None:
    """Decision del orquestador: cada produccion usa la receta vigente en SU fecha y la mezcla del
    periodo es el promedio ponderado por las toneladas hechas con cada receta."""
    cp.materiales(ins)
    a = cp.receta(ins)
    b = cp.receta(ins, cp.RECETA_B, cp.dia(16))
    cp.entrada(ins, "AGR-12", "150", cp.dia(5))
    cp.entrada(ins, "AGR-34", "50", cp.dia(5))
    cp.producir(ins, "60", cp.dia(10))  # receta A
    cp.producir(ins, "40", cp.dia(20))  # receta B
    cp.costos_usd(ins)
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    calculo = _calcular(ins, caso)
    assert calculo.por_tonelada["MZ-1"] == D("48.72")
    usadas = _instantanea(ins, calculo.id)["entradas"]["recetas"]
    assert [(r["id"], r["producto"], D(r["toneladas"])) for r in usadas] == [
        (a, "MZ-1", D("60")),
        (b, "MZ-1", D("40")),
    ]


def test_la_mezcla_en_m3_cuenta_las_toneladas_redondeadas(ins, caso) -> None:
    cp.planta(ins, mezcla_en="m3", densidad="2.3")
    cp.costos_usd(ins)
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    calculo = _calcular(ins, caso)
    assert calculo.por_tonelada["AGR-12"] == D("5")
    assert calculo.por_tonelada["MZ-1"] == D("38.70") + D("1200") / D("100.00009")
    entradas = _instantanea(ins, calculo.id)["entradas"]
    assert entradas["producido"]["MZ-1"] == "100.00009"


def test_reparto_por_pesos_en_el_periodo(ins, caso) -> None:
    _noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso, pesos={"AGR-12": D("0.6"), "AGR-34": D("0.4")})
    assert calculo.por_tonelada == {"AGR-12": D("4"), "AGR-34": D("8"), "MZ-1": D("49.76")}
    assert _instantanea(ins, calculo.id)["entradas"]["pesos"] == {"AGR-12": "0.6", "AGR-34": "0.4"}


def test_los_pesos_no_admiten_la_mezcla(ins, caso) -> None:
    _noviembre_usd(ins, caso)
    with pytest.raises(ErrorDeCalculo, match="MZ-1"):
        _calcular(ins, caso, pesos={"AGR-12": D("0.5"), "AGR-34": D("0.25"), "MZ-1": D("0.25")})


def test_moneda_invalida(ins, caso) -> None:
    _noviembre_usd(ins, caso)
    with pytest.raises(ValueError, match="Bs o USD"):
        _calcular(ins, caso, "EUR")


# --- Foco 2: nunca division entre cero ni costo cero ----------------------------------------------


def test_periodo_sin_produccion(ins, caso) -> None:
    cp.materiales(ins)
    cp.costos_usd(ins)
    with pytest.raises(ErrorDeCalculo, match=r"^No hubo producción en 2026-11\.$"):
        _calcular(ins, caso)
    assert _calculos(ins) == 0


def test_periodo_sin_costos(ins, caso) -> None:
    cp.planta(ins)
    with pytest.raises(ErrorDeCalculo, match=r"^No hay costos registrados en 2026-11\.$"):
        _calcular(ins, caso)
    assert _calculos(ins) == 0


def test_solo_costos_en_cero(ins, caso) -> None:
    cp.planta(ins)
    cp.costo(ins, "cantera", "0", "USD", cp.dia(3))
    cp.costo(ins, "planta", "0", "Bs", cp.dia(7))
    with pytest.raises(ErrorDeCalculo, match=r"^No hay costos registrados en 2026-11\.$"):
        _calcular(ins, caso)


def test_todos_los_costos_anulados(ins, caso) -> None:
    cp.planta(ins)
    for centro, monto in (("cantera", "1000"), ("planta", "1200")):
        i = cp.costo(ins, centro, monto, "USD", cp.dia(3))
        anular_costo(ins, i, motivo="duplicado", usuario="ana", ahora=cp.AHORA)
    with pytest.raises(ErrorDeCalculo, match=r"^No hay costos registrados en 2026-11\.$"):
        _calcular(ins, caso)


def test_costos_de_cantera_sin_agregados_producidos(ins, caso) -> None:
    cp.materiales(ins)
    cp.receta(ins)
    cp.producir(ins, "100", cp.dia(10))
    cp.costos_usd(ins)
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    with pytest.raises(ErrorDeCalculo, match="cantera.*ningún agregado"):
        _calcular(ins, caso)


def test_agregados_sin_costos_de_cantera(ins, caso) -> None:
    cp.planta(ins)
    cp.costo(ins, "planta", "1200", "USD", cp.dia(12))
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    with pytest.raises(ErrorDeCalculo, match="No hay costos de cantera.*AGR-12, AGR-34"):
        _calcular(ins, caso)


def test_costos_de_planta_sin_mezcla(ins, caso) -> None:
    cp.materiales(ins)
    cp.entrada(ins, "AGR-12", "150", cp.dia(5))
    cp.costos_usd(ins)
    with pytest.raises(ErrorDeCalculo, match="planta.*no se produjo mezcla"):
        _calcular(ins, caso)


def test_la_mezcla_usa_un_agregado_que_no_se_produjo(ins, caso) -> None:
    cp.materiales(ins)
    cp.receta(ins)
    cp.entrada(ins, "AGR-34", "50", cp.dia(5))
    cp.producir(ins, "100", cp.dia(10))
    cp.costos_usd(ins)
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    with pytest.raises(ErrorDeCalculo, match="AGR-12"):
        _calcular(ins, caso)


# --- Precio de lo comprado ------------------------------------------------------------------------


def test_comprado_sin_precio_en_la_lista(ins, caso) -> None:
    cp.planta(ins)
    cp.costos_usd(ins)
    cp.lista(caso, "USD", cp.dia(1), {"GO": ("0.5", "l")})
    with pytest.raises(ValueError, match="CA-30"):
        _calcular(ins, caso)
    assert _calculos(ins) == 0


def test_sin_lista_vigente_nombra_los_comprados(ins, caso) -> None:
    cp.planta(ins)
    cp.costos_usd(ins)
    cp.lista(caso, "USD", date(2026, 12, 1), cp.LISTA_USD)  # aun no rige
    with pytest.raises(ValueError, match="CA-30, GO"):
        _calcular(ins, caso)


def test_la_unidad_del_comprado_debe_ser_la_de_la_receta(ins, caso) -> None:
    cp.planta(ins)
    cp.costos_usd(ins)
    cp.lista(caso, "USD", cp.dia(1), {"CA-30": ("0.6", "kg"), "GO": ("0.5", "l")})
    with pytest.raises(ErrorDeCalculo, match="CA-30.*kg"):
        _calcular(ins, caso)


def test_la_lista_en_otra_moneda_usa_la_tasa_de_su_fecha_de_vigencia(ins, caso) -> None:
    cp.planta(ins)
    cp.costos_usd(ins)
    cp.lista(caso, "Bs", cp.dia(2), cp.LISTA_BS)
    cp.tasas(caso, {cp.dia(2): cp.TASA, cp.dia(30): "99"})
    calculo = _calcular(ins, caso)
    assert calculo.por_tonelada["MZ-1"] == D("50.70")
    precio = _instantanea(ins, calculo.id)["entradas"]["precios_comprados"]["CA-30"]
    assert (precio["precio"], precio["moneda"], precio["tasa"]["fecha"]) == (
        "21900",
        "Bs",
        "2026-11-02",
    )


def test_la_lista_en_otra_moneda_sin_tasa_de_su_fecha(ins, caso) -> None:
    cp.planta(ins)
    cp.costos_usd(ins)
    cp.lista(caso, "Bs", cp.dia(1), cp.LISTA_BS, nombre="Lista Bs ficticia")  # domingo 01/11
    cp.tasas(caso, {cp.dia(2): cp.TASA})
    with pytest.raises(FaltanTasas, match="Lista Bs ficticia.*01/11/2026"):
        _calcular(ins, caso)


# --- La instantanea -------------------------------------------------------------------------------


def test_mismo_calculo_misma_huella(ins, caso) -> None:
    _noviembre_usd(ins, caso)
    primero = _calcular(ins, caso)
    segundo = _calcular(ins, caso)
    assert primero.id != segundo.id
    assert primero.huella == segundo.huella
    assert _calculos(ins) == 2


def test_recalcular_crea_otro_calculo_y_el_primero_queda_intacto(ins, caso) -> None:
    _noviembre_usd(ins, caso)
    primero = _calcular(ins, caso)
    fila = ins.get(Calculo, primero.id)
    antes = (
        fila.periodo,
        fila.moneda,
        fila.huella,
        fila.instantanea,
        fila.usuario,
        fila.registrado,
    )
    cp.costo(ins, "cantera", "200", "USD", cp.dia(20))
    segundo = _calcular(ins, caso)
    assert segundo.id != primero.id and segundo.huella != primero.huella
    # cantera 1.200 / 200 = 6
    assert segundo.por_tonelada["AGR-12"] == D("6")
    ins.expire_all()
    fila = ins.get(Calculo, primero.id)
    despues = (
        fila.periodo,
        fila.moneda,
        fila.huella,
        fila.instantanea,
        fila.usuario,
        fila.registrado,
    )
    assert despues == antes
    assert calculo_guardado(ins, primero.id).por_tonelada["AGR-12"] == D("5")


def test_la_instantanea_es_json_canonico_con_su_huella(ins, caso) -> None:
    _noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso)
    texto = ins.get(Calculo, calculo.id).instantanea

    def sin_float(_valor):
        raise AssertionError("un numero JSON en la instantanea: los decimales van como texto")

    datos = json.loads(texto, parse_float=sin_float, parse_int=sin_float)
    canonico = json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    assert texto == canonico
    assert calculo.huella == hashlib.sha256(texto.encode("utf-8")).hexdigest()
    assert set(datos) == {"entradas", "resultado"}
    assert datos["resultado"]["por_tonelada"] == {"AGR-12": "5", "AGR-34": "5", "MZ-1": "50.70"}


def test_se_guarda_exacto(ins, caso) -> None:
    cp.materiales(ins)
    cp.entrada(ins, "AGR-12", "300", cp.dia(5))
    cp.costo(ins, "cantera", "1000", "USD", cp.dia(3))
    calculo = _calcular(ins, caso)
    tres = "3." + "3" * 27  # 1.000 / 300 con 28 cifras
    assert calculo.por_tonelada == {"AGR-12": D(tres)}
    assert _instantanea(ins, calculo.id)["resultado"]["por_tonelada"] == {"AGR-12": tres}


def test_ultimo_calculo_de_un_producto(ins, caso) -> None:
    _noviembre_usd(ins, caso)
    _calcular(ins, caso)
    cp.costo(ins, "cantera", "200", "USD", cp.dia(20))
    segundo = _calcular(ins, caso)
    ultimo = ultimo_calculo(ins, "MZ-1")
    assert ultimo is not None and ultimo.id == segundo.id
    assert ultimo.por_tonelada == segundo.por_tonelada
    assert ultimo_calculo(ins, "NO-EXISTE") is None


def test_un_calculo_inexistente(ins) -> None:
    with pytest.raises(CalculoInexistente):
        calculo_guardado(ins, 99)


def test_un_calculo_alterado_se_detecta(ins, caso) -> None:
    _noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso)
    ins.execute(
        text("UPDATE prod_calculo SET instantanea = replace(instantanea, '50.70', '40.70')")
    )
    ins.expire_all()
    with pytest.raises(ErrorDeCalculo, match="alterado"):
        calculo_guardado(ins, calculo.id)
