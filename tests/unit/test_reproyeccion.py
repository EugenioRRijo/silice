# tests/unit/test_reproyeccion.py
"""SL-E5: reproyección al ritmo real (spec S2 §4.4; RF-77).

El plan reproyectado, los fines por partida y el término de OB-S2 salen de la memoria
`control_ob_s2.md` (§7.1). Casos de frontera: partida detenida (AL-6), SPI global 0, corte a mitad
de período, obra terminada, partida sin plan y plan que cierra exacto en el total.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from core.budget.control import construir_estado
from core.budget.curva import generar_curva
from core.budget.valor_ganado import reproyectar
from tests.fixtures import control_ob_s2 as ob

D = Decimal
PLAN_REPROYECTADO = [
    ("Semana 1", [("OB-A", D("0.4"))]),
    ("Semana 2", [("OB-A", D("0.5")), ("OB-B", D("0.3"))]),
    ("Semana 3", [("OB-A", D("0.1")), ("OB-B", D("0.3")), ("OB-C", D("0.4"))]),
    ("Semana 4", [("OB-B", D("0.3")), ("OB-C", D("0.4"))]),
    ("Semana 5", [("OB-B", D("0.1")), ("OB-C", D("0.2"))]),
]


def _estado(valuaciones=None, *, corte=ob.CORTE):
    instantanea = ob.instantanea(ob.v01_v02() if valuaciones is None else valuaciones, corte=corte)
    return construir_estado(instantanea, costo_real=ob.COSTO_REAL, precios=ob.precios_del_corte())


def _plan(reproyeccion):
    return [(etiqueta, list(reparto)) for etiqueta, reparto in reproyeccion.plan]


def test_el_plan_reproyectado_de_la_memoria():
    reproyeccion = reproyectar(_estado())
    assert _plan(reproyeccion) == PLAN_REPROYECTADO
    assert reproyeccion.termino == 23  # dia habil 23 = 2026-12-02
    assert reproyeccion.motivo_termino == ""


def test_los_fines_ritmos_e_indices_por_partida():
    reproyeccion = reproyectar(_estado())
    a, b, c = (reproyeccion.de(codigo) for codigo in ("OB-A", "OB-B", "OB-C"))
    assert [p.indice for p in (a, b, c)] == [D("0.9"), D("0.6"), D("0.8")]
    assert [p.ritmo for p in (a, b, c)] == [D("0.45"), D("0.3"), D("0.4")]
    assert [round(p.fin, 2) for p in (a, b, c)] == [D("11.11"), D("21.67"), D("22.50")]
    assert (a.sin_evidencia, b.sin_evidencia, c.sin_evidencia) == (False, False, True)
    assert reproyeccion.detenidas == () and reproyeccion.no_proyectables == ()


def test_el_plan_reproyectado_es_valido_para_la_curva_y_cierra_en_el_total():
    estado = _estado()
    reproyeccion = reproyectar(estado)
    presupuesto = ob.elaborar_ob_s2().presupuesto
    curva = generar_curva(presupuesto, reproyeccion.plan)
    assert curva[-1].acumulado == presupuesto.total
    sumas = {}
    for _, reparto in reproyeccion.plan:
        for codigo, fraccion in reparto:
            sumas[codigo] = sumas.get(codigo, D(0)) + fraccion
    assert sumas == {"OB-A": 1, "OB-B": 1, "OB-C": 1}  # exacto, no a +- epsilon


def test_una_partida_detenida_se_reproyecta_al_ritmo_global_y_se_marca():
    """A tiene PV > 0 y EV = 0 (AL-6) y sigue al SPI global: EV 300 / PV 1500 = 0,2, o sea 0,2 / 2
    periodos = 0,1 por periodo; con 1 por ejecutar termina en el dia habil 60."""
    solo_b = ob.valuacion({**ob.V02, "lineas": ob.V02["lineas"][1:]}, 2)  # solo B 60
    reproyeccion = reproyectar(_estado([solo_b]))
    assert reproyeccion.detenidas == ("OB-A",)
    detenida = reproyeccion.de("OB-A")
    assert (detenida.detenida, detenida.indice, detenida.ritmo) == (True, D("0.2"), D("0.1"))
    assert detenida.fin == D(60) and reproyeccion.termino == 60


def test_un_spi_global_cero_hace_el_termino_no_proyectable():
    estado = _estado([], corte=date(2026, 11, 13))  # PV > 0 y nada ejecutado: SPI = 0
    reproyeccion = reproyectar(estado)
    assert reproyeccion.termino is None
    assert "no proyectable" in reproyeccion.motivo_termino
    assert set(reproyeccion.no_proyectables) == {"OB-A", "OB-B", "OB-C"}
    assert reproyeccion.de("OB-A").motivo.startswith("el SPI global es 0")


def test_antes_de_empezar_sin_spi_cada_partida_va_a_su_ritmo_planificado():
    estado = _estado([], corte=date(2026, 11, 1))  # PV = 0: el SPI no aplica, indice 1
    reproyeccion = reproyectar(estado)
    assert reproyeccion.termino == 20  # el plan base, intacto
    assert _plan(reproyeccion) == [
        ("Semana 1", [("OB-A", D("0.5"))]),
        ("Semana 2", [("OB-A", D("0.5")), ("OB-B", D("0.5"))]),
        ("Semana 3", [("OB-B", D("0.5")), ("OB-C", D("0.5"))]),
        ("Semana 4", [("OB-C", D("0.5"))]),
    ]


def test_corte_a_mitad_de_periodo_el_periodo_en_curso_aporta_solo_lo_que_le_queda():
    """Dia 8 (3 de 5 dias de la semana 2): lo pendiente arranca en la semana 2 con 2/5 de ritmo."""
    valuacion = ob.valuacion({**ob.V01, "lineas": ob.V01["lineas"]}, 1)
    estado = _estado([valuacion], corte=date(2026, 11, 11))
    assert estado.dia == 8
    reproyeccion = reproyectar(estado)
    a = reproyeccion.de("OB-A")
    # A: planificado 0,8, ejecutado 0,4 -> s = 0,5; ritmo 0,25; la semana 2 aporta 0,25 x 2/5.
    assert a.indice == D("0.5") and a.ritmo == D("0.25")
    semana_2 = dict(reproyeccion.plan[1][1])
    assert semana_2["OB-A"] == D("0.25") * D(2) / D(5)
    assert round(a.fin, 4) > D(8)  # termina despues del corte


def test_la_obra_terminada_termina_en_la_fecha_de_la_ultima_valuacion():
    completa = [
        ob.valuacion(
            dict(
                numero="V-01", desde=ob.INICIO, hasta=date(2026, 11, 27), fecha=date(2026, 11, 30),
                inspector=ob.INSPECTOR,
                lineas=[
                    ob.LineaValuacion("OB-A", D(100)),
                    ob.LineaValuacion("OB-B", D(200)),
                    ob.LineaValuacion("OB-C", D(100)),
                ],
            ),
            1,
        )
    ]  # fmt: skip
    reproyeccion = reproyectar(_estado(completa, corte=date(2026, 11, 27)))
    assert reproyeccion.termino == 20
    assert "nada queda pendiente" in reproyeccion.motivo_termino
    assert all(p.fin is None and p.pendiente == 0 for p in reproyeccion.partidas)


def test_adelantar_lleva_una_partida_sin_empezar_al_periodo_siguiente_al_corte():
    estado = _estado()
    adelantada = reproyectar(estado, adelantar=["OB-C"])
    # C ya empieza en la semana 3 (= c + 1): adelantar no cambia nada en OB-S2.
    assert _plan(adelantada) == PLAN_REPROYECTADO
    atrasada = replace(
        estado,
        partidas=tuple(
            replace(p, plan=(D(0), D(0), D(0), D(0), D("0.5"), D("0.5")))
            if p.codigo == "OB-C"
            else p
            for p in estado.partidas
        ),
        etiquetas=(*estado.etiquetas, "Semana 5", "Semana 6"),
    )
    assert _plan(reproyectar(atrasada))[2][1] == [("OB-A", D("0.1")), ("OB-B", D("0.3"))]
    assert dict(_plan(reproyectar(atrasada, adelantar=["OB-C"]))[2][1])["OB-C"] == D("0.4")


def test_las_etiquetas_del_plan_continuan_la_numeracion_y_si_no_hay_numero_usan_periodo():
    estado = _estado()
    assert reproyectar(estado).plan[4][0] == "Semana 5"
    sin_numero = replace(estado, etiquetas=("Inicio", "Medio", "Fin", "Cierre"))
    assert reproyectar(sin_numero).plan[4][0] == "Periodo 5"


def test_un_multiplicador_acelera_solo_esa_partida():
    estado = _estado()
    rapido = reproyectar(estado, multiplicador={"OB-B": D("1.8"), "OB-C": D("1.8")})
    assert rapido.termino == 17
    assert rapido.de("OB-A").fin == reproyectar(estado).de("OB-A").fin
    assert dict(rapido.plan[2][1]) == {"OB-A": D("0.1"), "OB-B": D("0.54"), "OB-C": D("0.72")}
