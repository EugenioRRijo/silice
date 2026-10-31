"""Plan vial, Tarea 16: lo que la proyección de una obra saca del cálculo publicado de la Tarea 4.

`mezclas_publicadas` lee el último cálculo **publicado** de cada mezcla propia que usa el
presupuesto y devuelve su receta, su costo de planta por tonelada y el precio de cada componente,
en la moneda del presupuesto (el cálculo guarda sus cifras en la suya; se convierten con la tasa
del cierre de su mes). Sin mezcla propia, todo vacío. Datos FICTICIOS
(`tests/fixtures/costo_propio.py`); oráculos a mano:

- noviembre de 2026 en USD: cantera 1.000 ÷ 200 t = 5 USD/t de `AGR-12`; planta 1.200 ÷ 100 t = 12
  USD/t; `CA-30` a 600 y `GO` a 0,5 de la lista. MZ-1 = 0,94 × 5 + 0,05 × 600 + 8 × 0,5 + 12 =
  50,70.
- En Bs con la tasa ficticia del cierre de noviembre, 36,50: planta 438, `AGR-12` 182,5, `CA-30`
  21.900 y `GO` 18,25.
- Dos recetas en el mes (60 t con A y 40 t con B): la receta del período pondera por toneladas,
  `AGR-12` (60 × 0,94 + 40 × 0,95) ÷ 100 = 0,944; `CA-30` (60 × 0,05 + 40 × 0,04) ÷ 100 = 0,046;
  `GO` (60 × 8 + 40 × 10) ÷ 100 = 8,8; y el costo da otra vez el del cálculo, 48,72.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from aplicacion.costo_propio import CalculoGuardado, calcular_periodo, publicar_calculo
from aplicacion.riesgo.obra import MezclasPropias, mezclas_publicadas
from core.catalog import Catalogo
from produccion.costo import costo_de_mezcla
from tests.fixtures import costo_propio as cp

D = Decimal
MEZCLA = "Costo propio de mezcla MZ-1"


@pytest.fixture
def ins() -> Iterator[Session]:
    with cp.instalacion_en_memoria() as sesion:
        yield sesion


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[Session]:
    with cp.carpeta_del_caso(tmp_path) as sesion:
        yield sesion


def _calcular(ins: Session, caso: Session) -> CalculoGuardado:
    return calcular_periodo(ins, caso, cp.PERIODO, "USD", usuario="ana", ahora=cp.AHORA)


def _publicar(ins: Session, caso: Session, calculo: CalculoGuardado) -> None:
    publicar_calculo(
        caso,
        calculo,
        sesion_ins=ins,
        nombre_del_caso="carpeta.db",
        base=Catalogo(caso).lista_vigente(date(2026, 11, 30)),
        empresa_nombre="Constructora Ejemplo, C.A.",
        empresa_rif="J-00000000-0",
        usuario="admin",
        ahora=cp.AHORA,
    )


def _componentes(mezclas: MezclasPropias) -> list[tuple[str, Decimal, str, str]]:
    receta = mezclas.recetas[MEZCLA]
    return [(c.codigo, c.cantidad_por_t, c.unidad, c.tipo) for c in receta.componentes]


def test_sin_mezcla_propia_todo_vacio(ins, caso) -> None:
    mezclas = mezclas_publicadas(ins, caso, {"Cemento asfáltico", "Gasoil"}, "USD")
    assert mezclas == MezclasPropias({}, {}, {}, {})


def test_la_mezcla_publicada_da_receta_planta_y_componentes_en_usd(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    calculo = _calcular(ins, caso)
    _publicar(ins, caso, calculo)
    mezclas = mezclas_publicadas(ins, caso, {MEZCLA, "Gasoil"}, "USD")
    assert _componentes(mezclas) == [
        ("AGR-12", D("0.94"), "t", "propio"),
        ("CA-30", D("0.05"), "t", "comprado"),
        ("GO", D("8"), "l", "comprado"),
    ]
    assert mezclas.costo_planta_por_t == {MEZCLA: D(12)}
    assert mezclas.precio_de_componente == {"AGR-12": D(5), "CA-30": D(600), "GO": D("0.5")}
    assert mezclas.calculos == {MEZCLA: calculo.id}


def test_un_calculo_sin_publicar_no_cuenta(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    _calcular(ins, caso)
    assert mezclas_publicadas(ins, caso, {MEZCLA}, "USD") == MezclasPropias({}, {}, {}, {})


def test_una_mezcla_que_el_presupuesto_no_usa_no_entra(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    _publicar(ins, caso, _calcular(ins, caso))
    assert mezclas_publicadas(ins, caso, {"Gasoil"}, "USD") == MezclasPropias({}, {}, {}, {})


def test_en_bs_con_la_tasa_del_cierre_del_mes_del_calculo(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    _publicar(ins, caso, _calcular(ins, caso))
    cp.tasas(caso, {cp.dia(30): cp.TASA})
    mezclas = mezclas_publicadas(ins, caso, {MEZCLA}, "Bs")
    assert mezclas.costo_planta_por_t == {MEZCLA: D("438")}
    assert mezclas.precio_de_componente == {
        "AGR-12": D("182.5"),
        "CA-30": D("21900"),
        "GO": D("18.25"),
    }


def test_en_bs_sin_tasa_del_cierre_se_niega_y_dice_el_mes(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    _publicar(ins, caso, _calcular(ins, caso))
    with pytest.raises(ValueError, match="2026-11"):
        mezclas_publicadas(ins, caso, {MEZCLA}, "Bs")


def test_dos_recetas_en_el_mes_se_ponderan_por_toneladas(ins, caso) -> None:
    cp.materiales(ins)
    cp.receta(ins)
    cp.receta(ins, cp.RECETA_B, cp.dia(16))
    cp.entrada(ins, "AGR-12", "150", cp.dia(5))
    cp.entrada(ins, "AGR-34", "50", cp.dia(5))
    cp.producir(ins, "60", cp.dia(10))  # receta A
    cp.producir(ins, "40", cp.dia(20))  # receta B
    cp.costos_usd(ins)
    cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
    _publicar(ins, caso, _calcular(ins, caso))
    mezclas = mezclas_publicadas(ins, caso, {MEZCLA}, "USD")
    assert [(c, q) for c, q, *_ in _componentes(mezclas)] == [
        ("AGR-12", D("0.944")),
        ("CA-30", D("0.046")),
        ("GO", D("8.8")),
    ]
    precios = mezclas.precio_de_componente
    receta = mezclas.recetas[MEZCLA]
    planta = mezclas.costo_planta_por_t[MEZCLA]
    assert costo_de_mezcla(receta, precios, precios, planta) == D("48.72")
