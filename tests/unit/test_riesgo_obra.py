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

import json
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from aplicacion.costo_propio import CalculoGuardado, calcular_periodo, publicar_calculo
from aplicacion.riesgo import obra
from aplicacion.riesgo.obra import (
    MezclasPropias,
    mapa_con_variantes,
    mezclas_publicadas,
    supuesto_de_componentes,
)
from aplicacion.riesgo.proyeccion import ParametrosProyeccion, proyectar
from aplicacion.riesgo.series import MapaSeries
from core.catalog import Catalogo
from produccion.costo import costo_de_mezcla
from tests.fixtures import costo_propio as cp
from tests.fixtures.riesgo_proyeccion import (
    CASCADA,
    F_UNO,
    INICIO,
    PARAMETROS,
    PPI,
    TOLERANCIA,
    apu_ficticio,
    historia_uniforme,
    obra_ficticia,
)

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


# --- Ramas de `mezclas_publicadas` con cálculos escritos a mano ---------------------------------
#
# Los cálculos publicados se sustituyen por instantáneas mínimas escritas aquí (solo lo que lee
# `mezclas_publicadas`). Oráculos a mano:
#
# - MZ-1 (cálculo 1): 0,95 t de AGR-12 a 5 (propio) + 0,05 t de CA-30 a 600 (comprado) + planta 12
#   = 4,75 + 30 + 12 = 46,75.
# - MZ-2 (cálculo 2): 0,95 t de AGR-34 a 6 + 0,05 t de CA-30 a 650 + planta 10 = 5,7 + 32,5 + 10
#   = 48,2. El CA-30 vale 650 en este cálculo y 600 en el otro: se desdobla en «CA-30 [2]».

MZ1 = "Costo propio de mezcla MZ-1"
MZ2 = "Costo propio de mezcla MZ-2"


def _instantanea(
    producto: str,
    propio: tuple[str, str],
    ca30: str,
    planta: str,
    recetas=True,
    comprado: str = "CA-30",
):
    codigo, costo = propio
    componentes = [
        {"codigo": codigo, "unidad": "t", "tipo": "propio", "cantidad_por_t": "0.95"},
        {"codigo": comprado, "unidad": "t", "tipo": "comprado", "cantidad_por_t": "0.05"},
    ]
    receta = {
        "id": 1,
        "producto": producto,
        "toneladas": "100",
        "componentes": componentes,
        "fuente": "Dosificación ficticia",
        "vigente_desde": "2026-01-01",
    }
    return json.dumps(
        {
            "entradas": {
                "recetas": [receta] if recetas else [],
                "precios_comprados": {comprado: {"convertido": ca30}},
                "de_otro_calculo": {},
                "agregados": [codigo],
            },
            "resultado": {"planta_por_t": planta, "por_tonelada": {codigo: costo, producto: "0"}},
        }
    )


def _calculo(numero: int, instantanea: str) -> CalculoGuardado:
    return CalculoGuardado(
        id=numero,
        periodo="2026-11",
        moneda="USD",
        por_tonelada={},
        huella="",
        instantanea=instantanea,
    )


def _publicados(monkeypatch, ca30_de_mz2: str = "650", *, recetas: bool = True) -> None:
    calculos = {
        "MZP-MZ-1": _calculo(1, _instantanea("MZ-1", ("AGR-12", "5"), "600", "12", recetas)),
        "MZP-MZ-2": _calculo(2, _instantanea("MZ-2", ("AGR-34", "6"), ca30_de_mz2, "10")),
    }
    monkeypatch.setattr(obra, "costos_propios_publicados", lambda _sesion: calculos)


def test_un_componente_con_dos_precios_en_dos_mezclas_se_desdobla(monkeypatch) -> None:
    _publicados(monkeypatch)
    mezclas = mezclas_publicadas(None, None, {MZ1, MZ2}, "USD")
    assert mezclas.precio_de_componente == {
        "AGR-12": D(5),
        "CA-30": D(600),
        "AGR-34": D(6),
        "CA-30 [2]": D(650),
    }
    assert [c.codigo for c in mezclas.recetas[MZ1].componentes] == ["AGR-12", "CA-30"]
    assert [c.codigo for c in mezclas.recetas[MZ2].componentes] == ["AGR-34", "CA-30 [2]"]
    assert mezclas.componente_original == {"CA-30 [2]": "CA-30"}
    # cada mezcla se costea con los precios de su propio cálculo
    precios = mezclas.precio_de_componente
    assert costo_de_mezcla(mezclas.recetas[MZ1], precios, precios, D(12)) == D("46.75")
    assert costo_de_mezcla(mezclas.recetas[MZ2], precios, precios, D(10)) == D("48.2")
    assert supuesto_de_componentes(mezclas) is not None
    assert "CA-30 (2 precios)" in supuesto_de_componentes(mezclas)


def test_la_variante_no_se_funde_con_un_componente_real_con_ese_nombre(monkeypatch) -> None:
    """Menor 1 del arbitro de cierre de la fase C: MZ-3 trae un componente que de verdad se llama
    «CA-30 [2]» (650). La variante del CA-30 de MZ-2 (650) no puede tomar ese nombre: se reservan
    antes todos los codigos de todas las recetas y la variante pasa a «CA-30 [3]». Oraculo a mano:
    MZ-3 = 0,95 x 7 + 0,05 x 650 + 9 = 6,65 + 32,5 + 9 = 48,15, con el precio de su calculo."""
    calculos = {
        "MZP-MZ-1": _calculo(1, _instantanea("MZ-1", ("AGR-12", "5"), "600", "12")),
        "MZP-MZ-2": _calculo(2, _instantanea("MZ-2", ("AGR-34", "6"), "650", "10")),
        "MZP-MZ-3": _calculo(
            3, _instantanea("MZ-3", ("AGR-56", "7"), "650", "9", comprado="CA-30 [2]")
        ),
    }
    monkeypatch.setattr(obra, "costos_propios_publicados", lambda _sesion: calculos)
    mz3 = "Costo propio de mezcla MZ-3"
    mezclas = mezclas_publicadas(None, None, {MZ1, MZ2, mz3}, "USD")
    assert [c.codigo for c in mezclas.recetas[MZ2].componentes] == ["AGR-34", "CA-30 [3]"]
    assert [c.codigo for c in mezclas.recetas[mz3].componentes] == ["AGR-56", "CA-30 [2]"]
    assert mezclas.componente_original == {"CA-30 [3]": "CA-30"}
    assert mezclas.precio_de_componente == {
        "AGR-12": D(5),
        "CA-30": D(600),
        "AGR-34": D(6),
        "CA-30 [3]": D(650),
        "AGR-56": D(7),
        "CA-30 [2]": D(650),
    }
    precios = mezclas.precio_de_componente
    assert costo_de_mezcla(mezclas.recetas[mz3], precios, precios, D(9)) == D("48.15")


def test_un_componente_con_el_mismo_precio_en_dos_mezclas_no_se_desdobla(monkeypatch) -> None:
    _publicados(monkeypatch, ca30_de_mz2="600")
    mezclas = mezclas_publicadas(None, None, {MZ1, MZ2}, "USD")
    assert mezclas.precio_de_componente["CA-30"] == D(600)
    assert "CA-30 [2]" not in mezclas.precio_de_componente
    assert mezclas.componente_original == {}
    assert supuesto_de_componentes(mezclas) is None


def test_un_calculo_que_no_guarda_la_receta_del_producto_se_niega(monkeypatch) -> None:
    _publicados(monkeypatch, recetas=False)
    with pytest.raises(ValueError, match=r"n\.º 1 no guarda la receta de MZ-1"):
        mezclas_publicadas(None, None, {MZ1, MZ2}, "USD")


def test_la_variante_del_componente_sigue_la_serie_del_original() -> None:
    mapa = mapa_con_variantes({"CA-30": PPI, "Gasoil": "GASOIL_USD"}, {"CA-30 [2]": "CA-30"})
    assert dict(mapa.serie_por_insumo) == {
        "CA-30": PPI,
        "CA-30 [2]": PPI,
        "Gasoil": "GASOIL_USD",
    }
    # sin serie para el original, la variante tampoco la tiene (aunque el pedido la nombre)
    sin = mapa_con_variantes({"CA-30 [2]": PPI}, {"CA-30 [2]": "CA-30"})
    assert dict(sin.serie_por_insumo) == {}


def test_dos_mezclas_con_el_componente_desdoblado_se_proyectan_a_mano(monkeypatch) -> None:
    # 1.000 t de cada mezcla, el CA-30 sigue el PPI (+1 % mensual) en las dos. A mano:
    # MZ-1 pasa a 16,75 + 30 × F y MZ-2 a 15,7 + 32,5 × F; total 1.000 × (32,45 + 62,5 × F) × 1,265
    _publicados(monkeypatch)
    mezclas = mezclas_publicadas(None, None, {MZ1, MZ2}, "USD")
    presupuesto, composiciones = obra_ficticia(
        {
            apu_ficticio("VIA-01", [(MZ1, "t", D(1), D("46.75"))]): D(1000),
            apu_ficticio("VIA-02", [(MZ2, "t", D(1), D("48.2"))]): D(1000),
        }
    )
    mapa = mapa_con_variantes({"CA-30": PPI}, mezclas.componente_original)

    p = proyectar(
        presupuesto,
        composiciones,
        PARAMETROS,
        historia_uniforme(ppi=D("1.01")),
        mapa,
        ParametrosProyeccion(inicio=INICIO, trayectorias=50),
        recetas=mezclas.recetas,
        costo_planta_por_t=mezclas.costo_planta_por_t,
        precio_de_componente=mezclas.precio_de_componente,
    )

    assert p.total_base == D(1000) * D("94.95") * CASCADA
    esperado = D(1000) * (D("32.45") + D("62.5") * F_UNO) * CASCADA
    assert abs(p.percentiles[80] - esperado) < TOLERANCIA
    assert isinstance(mapa, MapaSeries)
