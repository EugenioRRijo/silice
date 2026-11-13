"""Lo que el segundo re-congelado del 2026-11-13 cambia en `aplicacion/hoja.py` (ESTADO §5, punto 6).

- `estado_de_items`: un hallazgo que cita el renglón (su `origen_id`) es de ese renglón y no se
  reparte además a los demás renglones de la misma partida (E2E-3f de la prueba de punta a punta).
- `con_plan_por_rendimientos`: arma el plan en la primera unidad que cabe (días, semanas, meses),
  como la ruta del producto (`plan_rendimientos.plan_que_cabe`, D-2), y si ni en meses cabe lo
  dice con `HojaInvalida` y la salida.
- Los textos del cierre del APU y del 422 de guardar, con tildes.

Datos FICTICIOS: la vivienda de `tests/fixtures/obra_vivienda.py`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from aplicacion import hoja
from aplicacion.errores import HojaInvalida
from core.contracts import ParametrosCosto, Severidad
from core.contracts.apu import ResultadoAPU
from core.contracts.verificacion import Hallazgo
from core.verification.informe import InformeAuditoria
from tests.fixtures.obra_vivienda import COMPOSICIONES, FECHA, ITEMS, item

D = Decimal

# --- estado_de_items --------------------------------------------------------------------------

#: Tres renglones de OBRA-04 (como un mismo código en tres frentes) y uno de OBRA-05.
RENGLONES = (item("OBRA-04", "10", 1), item("OBRA-04", "20", 2), item("OBRA-04", "30", 3))
OTRA = item("OBRA-05", "40", 4)


def _r1(fila: int) -> Hallazgo:
    return Hallazgo("R1", Severidad.ADVERTENCIA, f"R1 ficticio del renglón {fila}", origen_ids=(f"FILA-{fila}",))


def _informe(*hallazgos: Hallazgo, de_partida: dict[Hallazgo, str] | None = None) -> InformeAuditoria:
    """El informe como lo arma el núcleo: cada renglón atribuido a su partida por su origen."""
    return InformeAuditoria(
        codigo_presupuesto="HOJA",
        hallazgos=hallazgos,
        partida_por_origen={i.origen_id: i.codigo_partida for i in (*RENGLONES, OTRA)},
        partida_por_hallazgo=de_partida or {},
    )


def _textos(informe: InformeAuditoria) -> list[str]:
    return [e.texto for e in hoja.estado_de_items([*RENGLONES, OTRA], informe).values()]


def test_un_hallazgo_que_cita_su_renglon_es_solo_de_ese_renglon():
    informe = _informe(_r1(1), _r1(2), _r1(3))
    assert _textos(informe) == [
        "ADVERTENCIA: R1 ficticio del renglón 1",
        "ADVERTENCIA: R1 ficticio del renglón 2",
        "ADVERTENCIA: R1 ficticio del renglón 3",
        "OK",
    ]


def test_aunque_la_regla_declare_la_partida_el_que_cita_su_renglon_no_se_reparte():
    hallazgo = _r1(2)
    informe = _informe(hallazgo, de_partida={hallazgo: "OBRA-04"})
    assert _textos(informe) == ["OK", "ADVERTENCIA: R1 ficticio del renglón 2", "OK", "OK"]


def test_un_hallazgo_de_la_partida_que_no_cita_un_renglon_sigue_en_todos_sus_renglones():
    de_partida = Hallazgo(
        "R5", Severidad.ERROR, "R5 ficticio de la partida", origen_ids=("OBRA-04",)
    )
    informe = _informe(de_partida, de_partida={de_partida: "OBRA-04"})
    assert _textos(informe) == ["ERROR: R5 ficticio de la partida"] * 3 + ["OK"]


# --- con_plan_por_rendimientos ------------------------------------------------------------------


def _borrador(*items) -> hoja.Borrador:
    return hoja.Borrador(fecha=FECHA, moneda="Bs", items_base=items, composiciones=COMPOSICIONES)


def test_la_vivienda_sigue_por_dias():
    plan = hoja.con_plan_por_rendimientos(_borrador(*ITEMS)).plan
    assert [e for e, _ in plan] == [f"Dia {n}" for n in range(1, 59)]


def test_una_obra_de_654_dias_se_arma_por_semanas_como_la_ruta_del_producto():
    # OBRA-01: 2.700 ÷ 4,5 = 600 días; con las otras cinco (54) son 654 → 131 semanas de 5 días
    plan = hoja.con_plan_por_rendimientos(_borrador(item("OBRA-01", "2700"), *ITEMS[1:])).plan
    assert [e for e, _ in plan] == [f"Semana {n}" for n in range(1, 132)]


def test_una_obra_de_3054_dias_se_arma_por_meses():
    # OBRA-01: 13.500 ÷ 4,5 = 3.000 días; con las otras 54, 3.054 → 153 meses de 20 días hábiles
    plan = hoja.con_plan_por_rendimientos(_borrador(item("OBRA-01", "13500"), *ITEMS[1:])).plan
    assert [e for e, _ in plan] == [f"Mes {n}" for n in range(1, 154)]


def test_si_ni_en_meses_cabe_es_hoja_invalida_con_la_salida():
    # 45.004,5 ÷ 4,5 = 10.001 días; con las otras 54, 10.055 ÷ 20 = 502,75 → 503 meses
    with pytest.raises(HojaInvalida) as error:
        hoja.con_plan_por_rendimientos(_borrador(item("OBRA-01", "45004.5"), *ITEMS[1:]))
    assert "503 meses" in str(error.value)
    assert "asigne más cuadrillas" in str(error.value)


# --- textos con tildes --------------------------------------------------------------------------


def test_el_cierre_dice_administracion_con_tilde():
    resultado = ResultadoAPU(
        materiales=D("2"),
        equipos=D("1"),
        mano_obra=D("2"),
        costo_directo=D("5"),
        con_administracion=D("5.75"),
        precio_unitario=D("6.325"),
    )
    conceptos = [f["Concepto"] for f in hoja.filas_de_cierre(resultado, ParametrosCosto(), "Bs")]
    assert "+ Administración" in conceptos and "= Con administración" in conceptos


@pytest.mark.parametrize(
    ("fuente", "responsable", "mensaje"),
    [
        ("", "Ana", "Escriba la fuente del cambio: por qué se cambia y con qué respaldo."),
        ("acta 1", "", "Escriba el responsable del cambio: quién lo hace."),
    ],
)
def test_los_422_de_guardar_van_con_tildes(fuente, responsable, mensaje):
    base = _borrador(*ITEMS)
    actual = hoja.Borrador(
        fecha=FECHA, moneda="Bs", items_base=(item("OBRA-01", "19"), *ITEMS[1:]),
        composiciones=COMPOSICIONES,
    )  # fmt: skip
    assert hoja.motivo_para_no_guardar(base, actual, fuente, responsable) == mensaje
