"""Prueba de punta a punta del 2026-11-13, defecto D1: VR8, una partida que el presupuesto trae a
la vez derivada de los tramos y de otro renglón (a mano o de otro cómputo). Datos FICTICIOS.

Vía de prueba: T1, de 0 a 1 km (1.000 m), ancho 1 m, riego de adherencia de 0,40 l/m². Oráculos a
mano: área 1.000 × 1 = 1.000 m²; ligante 1.000 × 0,40 = 400 l. Con el riego escrito a mano
(1.000 m², «a-mano:1») y el mismo riego llevado de los tramos, el presupuesto suma 2.000 m²: VR8 lo
advierte una vez, con las dos cantidades y los dos orígenes. Decisión simulada en
`docs/bitacora/2026-11-13-e2e-vial.md` (D1).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Tramo
from adapters.vial.reglas import auditar_vial
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.contracts.apu import ComposicionAPU, ResultadoAPU
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Severidad

D = Decimal
RIEGO = PARTIDAS_VIALES["riego_adherencia"][0]


def _tramo(id: str = "T1", ini: str = "0", fin: str = "1") -> Tramo:
    return Tramo(id, D(ini), D(fin), D("1"), (Capa("riego_adherencia", None, None, D("0.4")),))


T1 = _tramo()


def _a_mano(clave: str, cantidad: str, n: int = 1, unidad: str | None = None) -> ItemComputo:
    codigo, descripcion, de_siempre = PARTIDAS_VIALES[clave]
    return ItemComputo(
        codigo,
        descripcion,
        unidad or de_siempre,
        D(cantidad),
        f"a-mano:{n}",
        OrigenTipo.MANUAL,
        Dominio.CIVIL,
    )


def _presupuesto(items: list[ItemComputo]) -> Presupuesto:
    cero = D("0")
    return Presupuesto(
        "VIA-TEST",
        date(2026, 11, 13),
        "Bs",
        tuple(
            PartidaPresupuestada(
                i,
                ComposicionAPU(i.codigo_partida, i.descripcion, i.unidad, D("1")),
                ResultadoAPU(cero, cero, cero, cero, cero, D("1")),
            )
            for i in items
        ),
    )


def _vr8(tramos: list[Tramo], items: list[ItemComputo]) -> list[tuple[Severidad, tuple, str]]:
    return [
        (h.severidad, h.origen_ids, h.descripcion)
        for h in auditar_vial(tramos, _presupuesto(items))
        if h.regla == "VR8"
    ]


def test_el_riego_a_mano_y_el_de_los_tramos_se_advierten_una_vez():
    items = [_a_mano("riego_adherencia", "1000"), *derivar_tramos([T1])]
    assert _vr8([T1], items) == [
        (
            Severidad.ADVERTENCIA,
            ("tramo:T1:capa:1", "a-mano:1"),
            f"{RIEGO} (Riego de adherencia): 1.000 m2 vienen de los tramos (tramo:T1:capa:1) y "
            "1.000 m2 de otro renglón (a-mano:1); el presupuesto suma 2.000 m2. Si es la misma "
            "obra, quite el renglón que sobra; si no, este aviso no aplica.",
        )
    ]


def test_el_renglon_a_mano_agregado_despues_de_llevar_tambien_se_advierte():
    items = [*derivar_tramos([T1]), _a_mano("riego_adherencia", "250.5", n=3)]
    ((severidad, origenes, texto),) = _vr8([T1], items)
    assert (severidad, origenes) == (Severidad.ADVERTENCIA, ("tramo:T1:capa:1", "a-mano:3"))
    assert "250,5 m2 de otro renglón (a-mano:3); el presupuesto suma 1.250,5 m2" in texto


def test_varios_tramos_y_varios_renglones_a_mano_van_en_un_solo_aviso():
    t2 = _tramo("T2", "1", "1.5")
    items = [
        _a_mano("riego_adherencia", "100", 1),
        *derivar_tramos([T1, t2]),
        _a_mano("riego_adherencia", "50", 2),
    ]
    assert _vr8([T1, t2], items) == [
        (
            Severidad.ADVERTENCIA,
            ("tramo:T1:capa:1", "tramo:T2:capa:1", "a-mano:1", "a-mano:2"),
            f"{RIEGO} (Riego de adherencia): 1.500 m2 vienen de los tramos (tramo:T1:capa:1, "
            "tramo:T2:capa:1) y 150 m2 de otro renglón (a-mano:1, a-mano:2); el presupuesto suma "
            "1.650 m2. Si es la misma obra, quite el renglón que sobra; si no, este aviso no "
            "aplica.",
        )
    ]


def test_con_otra_unidad_no_suma_lo_que_no_se_puede_sumar():
    items = [_a_mano("riego_adherencia", "2", unidad="ha"), *derivar_tramos([T1])]
    ((_, _, texto),) = _vr8([T1], items)
    assert texto == (
        f"{RIEGO} (Riego de adherencia): 1.000 m2 vienen de los tramos (tramo:T1:capa:1) y "
        "2 ha de otro renglón (a-mano:1). Si es la misma obra, quite el renglón que sobra; si no, "
        "este aviso no aplica."
    )


def test_sin_aviso_si_la_partida_solo_viene_de_los_tramos_o_solo_a_mano():
    assert _vr8([T1, _tramo("T2", "1", "2")], derivar_tramos([T1, _tramo("T2", "1", "2")])) == []
    # los tramos aún no se llevaron: el riego a mano es el único del presupuesto
    assert _vr8([T1], [_a_mano("riego_adherencia", "1000")]) == []


def test_sin_aviso_por_una_partida_que_los_tramos_no_derivan():
    items = [_a_mano("movilizacion_equipos", "2"), *derivar_tramos([T1])]
    assert _vr8([T1], items) == []


def test_un_presupuesto_coherente_sigue_sin_hallazgos():
    assert auditar_vial([T1], _presupuesto(derivar_tramos([T1]))) == []
