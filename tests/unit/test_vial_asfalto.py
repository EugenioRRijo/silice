"""Plan vial, Tarea 16b (filas 58 y 63): el porcentaje de asfalto llega de la capa a VR2. FICTICIO.

Camino de producto: la capa de carpeta o de bacheo declara el porcentaje de asfalto del proyecto
(`Capa.asfalto_pct`, columna opcional `asfalto_pct` del CSV); `derivar_tramos` lo pone en la
partida de su mezcla como directiva `_porcentaje_asfalto`; VR2 lo compara con la fórmula de trabajo
que le da quien arma la regla, por código de partida (`formulas`). Si para esa partida no hay
fórmula, `sin_formula` dice por qué y VR2 lo declara (INFO) en vez de callar.

Vía de prueba: T1, 0 a 1 km, 7 m de ancho, carpeta de 0,05 m a 2,4 t/m3 con 6,5 % de asfalto.
Oráculos a mano: con fórmula 5 %, 6,5 − 5 = 1,5 puntos > 0,5 → VR2 (6,5 contra 5); con 6,2 %,
1,2 puntos; con 5,4 %, 0,4 ≤ 0,5 → nada.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Tramo
from adapters.vial.reglas import ReglasViales, auditar_vial
from adapters.vial.tabular import leer_tramos
from core.contracts import ItemComputo
from core.contracts.apu import ComposicionAPU, ResultadoAPU
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Severidad

D = Decimal
CAPA1 = "tramo:T1:capa:1"
MEZCLA = PARTIDAS_VIALES["carpeta_mezcla"][0]
BACHEO = PARTIDAS_VIALES["bacheo_mezcla"][0]
MOTIVO = "la mezcla propia MZ-1 no tiene receta vigente al 31/10/2026"
CABECERA = (
    "tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;"
    "espesor_m;densidad_t_m3;dosis_l_m2;lineas;asfalto_pct\n"
)


def _tramo(asfalto: str | None = "6.5", tipo: str = "carpeta") -> Tramo:
    densidad = D("2.4")
    capa = Capa(tipo, D("0.05"), densidad, None, None if asfalto is None else D(asfalto))
    return Tramo("T1", D("0"), D("1"), D("7"), (capa,))


def _presupuesto(items: list[ItemComputo]) -> Presupuesto:
    cero = D("0")
    partidas = []
    for item in items:
        apu = ComposicionAPU(item.codigo_partida, item.descripcion, item.unidad, D("1"))
        resultado = ResultadoAPU(cero, cero, cero, cero, cero, D("1"))
        partidas.append(PartidaPresupuestada(item, apu, resultado))
    return Presupuesto("VIV-TEST", date(2026, 10, 31), "Bs", tuple(partidas))


def _de(tramo: Tramo) -> Presupuesto:
    return _presupuesto(derivar_tramos([tramo]))


# --- la capa y el CSV -----------------------------------------------------------------------------


def test_la_carpeta_y_el_bacheo_admiten_el_porcentaje_de_asfalto() -> None:
    assert _tramo("6.5").capas[0].asfalto_pct == D("6.5")
    assert _tramo("4,0".replace(",", "."), "bacheo").capas[0].asfalto_pct == D("4.0")
    assert _tramo(None).capas[0].asfalto_pct is None


def test_otra_capa_no_usa_el_porcentaje_de_asfalto() -> None:
    with pytest.raises(ValueError, match="la capa base_granular no usa asfalto"):
        Capa("base_granular", D("0.2"), None, None, D("5"))


@pytest.mark.parametrize("valor", ["0", "-1", "100", "120"])
def test_el_porcentaje_debe_estar_entre_0_y_100(valor: str) -> None:
    with pytest.raises(ValueError, match="asfalto"):
        Capa("carpeta", D("0.05"), D("2.4"), None, D(valor))


def test_el_csv_lee_la_columna_opcional_asfalto_pct(tmp_path: Path) -> None:
    ruta = tmp_path / "tramos.csv"
    ruta.write_text(
        CABECERA + "T1;0;1;7;;capa;carpeta;0,05;2,4;;;6,5\n" + "T1;;;;;capa;bacheo;0,10;;;;\n",
        encoding="utf-8",
    )
    (tramo,) = leer_tramos(ruta)
    assert [c.asfalto_pct for c in tramo.capas] == [D("6.5"), None]


def test_una_demarcacion_con_asfalto_se_rechaza_con_su_fila(tmp_path: Path) -> None:
    ruta = tmp_path / "tramos.csv"
    ruta.write_text(
        CABECERA + "T1;0;1;7;;capa;carpeta;0,05;2,4;;;\nT1;;;;;demarcacion;continua;;;;1;5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"fila 3: una demarcación no usa asfalto_pct"):
        leer_tramos(ruta)


# --- la derivación ------------------------------------------------------------------------------


def test_la_mezcla_lleva_el_porcentaje_como_directiva() -> None:
    items = derivar_tramos([_tramo("6.5")])
    (mezcla,) = [i for i in items if i.codigo_partida == MEZCLA]
    assert mezcla.especificaciones["_porcentaje_asfalto"] == "6.5"
    otros = [i for i in items if i.codigo_partida != MEZCLA]
    assert otros and all("_porcentaje_asfalto" not in i.especificaciones for i in otros)


def test_sin_porcentaje_no_hay_directiva() -> None:
    (mezcla,) = [i for i in derivar_tramos([_tramo(None)]) if i.codigo_partida == MEZCLA]
    assert "_porcentaje_asfalto" not in mezcla.especificaciones


# --- VR2 con la fórmula por partida -------------------------------------------------------------


def test_vr2_con_la_formula_de_la_partida() -> None:
    (h,) = auditar_vial([_tramo("6.5")], _de(_tramo("6.5")), formulas={MEZCLA: D("5")})
    assert (h.regla, h.severidad, h.origen_ids) == ("VR2", Severidad.ADVERTENCIA, (CAPA1,))
    assert (h.valor_observado, h.valor_esperado) == (D("6.5"), D("5"))
    assert auditar_vial([_tramo("5.4")], _de(_tramo("5.4")), formulas={MEZCLA: D("5")}) == []


def test_vr2_la_formula_de_otra_partida_no_vale() -> None:
    t = _tramo("6.5")
    assert auditar_vial([t], _de(t), formulas={BACHEO: D("5")}) == []


def test_vr2_sin_formula_lo_declara_con_el_motivo() -> None:
    t = _tramo("6.2")
    (h,) = auditar_vial([t], _de(t), sin_formula={MEZCLA: MOTIVO})
    assert (h.regla, h.severidad, h.origen_ids) == ("VR2", Severidad.INFO, (CAPA1,))
    assert h.valor_observado == D("6.2") and h.valor_esperado is None
    assert h.descripcion == (
        f"{CAPA1}: asfalto de 6,2 % sin comparar con la fórmula de trabajo: {MOTIVO}"
    )


def test_vr2_sin_porcentaje_declarado_no_declara_nada() -> None:
    t = _tramo(None)
    assert auditar_vial([t], _de(t), sin_formula={MEZCLA: MOTIVO}) == []


def test_la_regla_lleva_las_formulas_y_los_motivos() -> None:
    t = _tramo("6.5")
    regla = ReglasViales([t], formulas={MEZCLA: D("5")}, sin_formula={BACHEO: MOTIVO})
    assert regla.evaluar(_de(t)) == auditar_vial(
        [t], _de(t), formulas={MEZCLA: D("5")}, sin_formula={BACHEO: MOTIVO}
    )
    assert (dict(regla.formulas), dict(regla.sin_formula)) == ({MEZCLA: D("5")}, {BACHEO: MOTIVO})
