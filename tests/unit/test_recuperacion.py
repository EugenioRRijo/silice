# tests/unit/test_recuperacion.py
"""SL-E6: opciones de recuperación (spec S2 §4.6; RF-78).

Las cuatro opciones de OB-S2 con su término, su costo directo adicional, su `CF'` y su `PE'` en los
dos escenarios (memoria `control_ob_s2.md`, §7.1); los límites de la LOTTT; la monotonía en `k`;
«no aplica» tipado, sin dividir, para partidas sin mano de obra a jornal de TI-001 y SIS-001.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from core.budget.control import construir_estado
from core.budget.equilibrio import EstadoEquilibrio
from core.budget.recuperacion import (
    HORAS_EXTRA_ANIO_MAX,
    ContextoRecuperacion,
    LimiteLegal,
    costo_diario,
    eficiencia_de_cuadrillas,
    exigir_horas_extra_legales,
    opcion_aceptar,
    opcion_cuadrillas,
    opcion_horas_extra,
    opcion_paralelo,
    opciones,
)
from core.budget.valor_ganado import (
    ParametrosControl,
    indicadores,
    proyectar_partida,
    reproyectar,
)
from core.contracts.apu import ModalidadManoObra
from tests.fixtures import control_fronteras as fronteras
from tests.fixtures import control_ob_s2 as ob

D = Decimal
MONTOS = D("0.01")
SIN_REAJUSTE = D(0)


def _contexto(
    *, reajuste=SIN_REAJUSTE, valuaciones=None, corte=ob.CORTE, composiciones=None, **extra
):
    instantanea = ob.instantanea(ob.v01_v02() if valuaciones is None else valuaciones, corte=corte)
    estado = construir_estado(instantanea, costo_real=ob.COSTO_REAL, precios=ob.precios_del_corte())
    presupuesto = instantanea.presupuesto
    parametros = extra.pop("parametros", ParametrosControl())
    return ContextoRecuperacion(
        estado=estado,
        base=reproyectar(estado),
        indicadores=indicadores(estado),
        composiciones=composiciones or {p.item.codigo_partida: p.apu for p in presupuesto.partidas},
        parametros_costo=ob.PARAMETROS,
        parametros=parametros,
        presupuesto=presupuesto,
        venta=presupuesto.total,
        costo_fijo=D(600),
        reajuste=reajuste,
        **extra,
    )


def _resumen(opcion):
    return (
        opcion.termino,
        round(opcion.costo_directo_adicional, 4),
        opcion.eac,
        opcion.costo_indirecto,
    )


@pytest.mark.parametrize(
    ("nombre", "termino", "adicional", "cv", "cf"),
    [
        ("aceptar", 23, D(0), D(4480), D(690)),
        ("cuadrillas", 17, D(120), D(4600), D(510)),
        ("horas_extra", 21, D("115.3125"), D("4595.3125"), D(630)),
    ],
)
def test_los_resultados_de_la_memoria_ob_s2(nombre, termino, adicional, cv, cf):
    opcion = {o.nombre: o for o in opciones(_contexto())}[nombre]
    assert opcion.aplica and opcion.termino == termino
    assert abs(opcion.costo_directo_adicional - adicional) <= D("0.0001")
    assert abs(opcion.eac - cv) <= D("0.0001")
    assert opcion.costo_indirecto == cf - 600  # CF' - CF
    assert opcion.retraso == max(0, termino - 20)


def test_los_pe_de_cada_opcion_en_los_dos_escenarios_de_la_memoria():
    sin = {o.nombre: o for o in opciones(_contexto())}
    con = {o.nombre: o for o in opciones(_contexto(reajuste=D("75.90")))}
    esperado = {
        "aceptar": (D("6019.66"), D("5402.91")),
        "cuadrillas": (D("5610.00"), D("4887.68")),
        "horas_extra": (D("6860.09"), D("5985.37")),
    }
    for nombre, (punto_sin, punto_con) in esperado.items():
        assert abs(sin[nombre].equilibrio.punto - punto_sin) <= MONTOS, nombre
        assert abs(con[nombre].equilibrio.punto - punto_con) <= MONTOS, nombre
        assert sin[nombre].equilibrio.estado is EstadoEquilibrio.NO_SE_ALCANZA
    # Con el reajuste reconocido solo «mas cuadrillas» alcanza el equilibrio, y en la semana 4.
    alcanzan = [
        n
        for n, o in con.items()
        if o.equilibrio and o.equilibrio.estado is EstadoEquilibrio.CALCULADO
    ]
    assert alcanzan == ["cuadrillas"]
    assert con["cuadrillas"].equilibrio.periodo.startswith("Semana 4")
    assert abs(con["cuadrillas"].equilibrio.porcentaje - D("95.17")) <= MONTOS


def test_partidas_en_paralelo_no_aplica_si_ninguna_empieza_despues_del_periodo_siguiente():
    paralelo = opcion_paralelo(_contexto())
    assert not paralelo.aplica and "ninguna partida sin empezar" in paralelo.motivo


def test_mas_cuadrillas_usa_k_2_con_e_igual_a_1_8_en_b_y_c():
    opcion = opcion_cuadrillas(_contexto())
    assert opcion.detalle["partidas"]["OB-B"]["k"] == 2
    assert opcion.detalle["partidas"]["OB-C"]["k"] == 2
    assert opcion.detalle["partidas"]["OB-B"]["eficiencia"] == "1.80"
    assert "OB-A" not in opcion.detalle["partidas"]  # A termina en 11,11: no determina el termino
    assert dict(opcion.plan[2][1]) == {"OB-A": D("0.1"), "OB-B": D("0.54"), "OB-C": D("0.72")}


def test_cada_opcion_lista_sus_supuestos_con_su_naturaleza():
    por_opcion = {o.nombre: o for o in opciones(_contexto())}
    cuadrillas = {s.nombre: s for s in por_opcion["cuadrillas"].supuestos}
    assert cuadrillas["eta de cuadrillas"].naturaleza == "SUPUESTO_DECLARADO"
    assert cuadrillas["eta de cuadrillas"].valor == "0.80"
    assert "Lee (2022)" in cuadrillas["eta de cuadrillas"].fuente
    assert cuadrillas["penalizacion diaria"].naturaleza == "DATO_DEL_CONTRATO"
    horas = {s.nombre: s for s in por_opcion["horas_extra"].supuestos}
    assert (
        horas["recargo"].naturaleza == "FUENTE_VERIFICADA" and "art. 118" in horas["recargo"].fuente
    )
    assert horas["limites de horas extra"].fuente == "LOTTT art. 178"
    assert any("art. 182" in requisito for requisito in por_opcion["horas_extra"].requisitos)


def test_aceptar_el_retraso_suma_la_penalizacion_del_contrato_por_dia_de_retraso():
    contexto = _contexto(parametros=ParametrosControl(penalizacion_diaria=D(100)))
    assert opcion_aceptar(contexto).penalizacion == D(300)  # 3 dias sobre el dia 20
    assert opcion_cuadrillas(contexto).penalizacion == 0  # llega antes del plan base


def test_el_termino_objetivo_declarado_cambia_que_partidas_lo_determinan():
    sin_objetivo = opcion_cuadrillas(_contexto())
    amplio = opcion_cuadrillas(_contexto(objetivo=25))
    assert sin_objetivo.aplica and not amplio.aplica
    assert "ninguna partida pasa del objetivo" in amplio.motivo
    estricto = opcion_cuadrillas(_contexto(objetivo=10))
    assert estricto.aplica and estricto.retraso > 0  # ni k_max alcanza: devuelve lo que queda (4a)
    assert estricto.detalle["partidas"]["OB-B"]["k"] == 3


def test_un_fin_igual_al_objetivo_cuenta_como_recuperado():
    """Antes de empezar (indice 1) A termina exacto en el dia 10: con objetivo 10 no determina."""
    contexto = _contexto(valuaciones=[], corte=date(2026, 11, 1), objetivo=10)
    assert contexto.base.de("OB-A").fin == D(10)
    assert set(opcion_cuadrillas(contexto).detalle["partidas"]) == {"OB-B", "OB-C"}
    contexto_9 = _contexto(valuaciones=[], corte=date(2026, 11, 1), objetivo=9)
    assert set(opcion_cuadrillas(contexto_9).detalle["partidas"]) == {"OB-A", "OB-B", "OB-C"}


def test_mas_cuadrillas_nunca_alargan_el_termino_de_una_partida():
    contexto = _contexto()
    fines = [
        proyectar_partida(
            contexto.estado,
            "OB-B",
            multiplicador=eficiencia_de_cuadrillas(k, D("0.80")),
            spi_global=contexto.indicadores.spi,
        ).fin
        for k in range(1, 6)
    ]
    assert fines == sorted(fines, reverse=True) and len(set(fines)) == 5  # estrictamente menor
    assert eficiencia_de_cuadrillas(1, D("0.80")) == 1
    assert eficiencia_de_cuadrillas(3, D("0.80")) == D("2.44")


@pytest.mark.parametrize("horas", [D("2.2"), D(3)])
def test_las_horas_extra_por_dia_sobre_el_limite_se_rechazan(horas):
    with pytest.raises(LimiteLegal):
        opcion_horas_extra(_contexto(parametros=ParametrosControl(horas_extra_dia=horas)))
    with pytest.raises(LimiteLegal, match="negativas"):
        exigir_horas_extra_legales(D("-1"), 0, D(0))


def test_dos_horas_por_dia_son_el_limite_y_pasan_y_se_citan_los_articulos():
    exigir_horas_extra_legales(D(2), 0, D(0))  # 10 h extra en la semana de cinco dias: pasa
    with pytest.raises(LimiteLegal, match="art. 178"):
        exigir_horas_extra_legales(D("2.2"), 0, D(0))  # 11 h por semana
    assert opcion_horas_extra(_contexto()).aplica


def test_cien_horas_extra_en_el_anio_pasan_y_ciento_una_se_rechazan():
    # B termina en el dia 20 y C en el 21: C trabaja 11 dias con 2 h extra = 22 h.
    pasa = opcion_horas_extra(_contexto(horas_previas=HORAS_EXTRA_ANIO_MAX - 22))
    assert pasa.aplica
    assert pasa.detalle["partidas"]["OB-C"]["horas_extra_del_obrero"] == "22"
    falla = opcion_horas_extra(_contexto(horas_previas=HORAS_EXTRA_ANIO_MAX - 21))
    assert not falla.aplica and "101" in falla.motivo and "art. 178" in falla.motivo
    exigir_horas_extra_legales(D(1), 100, D(0))
    with pytest.raises(LimiteLegal, match="101"):
        exigir_horas_extra_legales(D(1), 101, D(0))


def test_las_horas_extra_de_la_memoria_ninguna_supera_los_limites():
    opcion = opcion_horas_extra(_contexto())
    for datos in opcion.detalle["partidas"].values():
        assert D(datos["horas_extra_del_obrero"]) <= HORAS_EXTRA_ANIO_MAX


def test_fcas_en_horas_extra_es_un_parametro_que_cambia_el_costo():
    con = opcion_horas_extra(_contexto())
    sin = opcion_horas_extra(_contexto(parametros=ParametrosControl(fcas_en_horas_extra=False)))
    assert sin.costo_directo_adicional < con.costo_directo_adicional


def test_una_partida_de_ti_001_a_destajo_no_aplica_en_cuadrillas_ni_horas_extra():
    costo = costo_diario(fronteras.ti001_a_destajo(), fronteras.caso_ti001.PARAMETROS)
    assert (costo.aplica, costo.motivo, costo.salario) == (False, "sin mano de obra a jornal", 0)
    assert fronteras.ti001_a_destajo().mano_obra[0].modalidad is ModalidadManoObra.DESTAJO


def test_una_partida_de_sis_001_sin_mano_de_obra_no_aplica_sin_dividir():
    costo = costo_diario(fronteras.sis001_sin_mano_de_obra(), fronteras.sis.PARAMETROS_SISTEMAS)
    assert (costo.aplica, costo.motivo) == (False, "sin mano de obra a jornal")


def test_si_las_partidas_que_determinan_el_termino_no_tienen_jornal_la_opcion_no_aplica():
    ti, sis = fronteras.ti001_a_destajo(), fronteras.sis001_sin_mano_de_obra()
    base = {p.item.codigo_partida: p.apu for p in ob.elaborar_ob_s2().presupuesto.partidas}
    # OB-B y OB-C, las que determinan el termino, toman las variantes de otros dominios.
    cambiadas = {
        **base,
        "OB-B": replace(ti, codigo_partida="OB-B"),
        "OB-C": replace(sis, codigo_partida="OB-C"),
    }
    contexto = _contexto(composiciones=cambiadas)
    for opcion in (opcion_cuadrillas(contexto), opcion_horas_extra(contexto)):
        assert not opcion.aplica
        assert "OB-B: sin mano de obra a jornal" in opcion.motivo
        assert "OB-C: sin mano de obra a jornal" in opcion.motivo
    # «Aceptar el retraso» no depende de la cuadrilla y se calcula igual.
    assert opcion_aceptar(contexto).aplica and opcion_aceptar(contexto).termino == 23


def test_si_solo_una_partida_no_tiene_jornal_la_otra_se_calcula_y_la_primera_se_declara():
    base = {p.item.codigo_partida: p.apu for p in ob.elaborar_ob_s2().presupuesto.partidas}
    cambiadas = {**base, "OB-B": replace(fronteras.ti001_a_destajo(), codigo_partida="OB-B")}
    opcion = opcion_cuadrillas(_contexto(composiciones=cambiadas))
    assert opcion.aplica
    assert set(opcion.detalle["partidas"]) == {"OB-C"}
    assert opcion.detalle["sin_cuadrilla"] == {"OB-B": "sin mano de obra a jornal"}


def test_el_costo_diario_de_los_apu_de_ob_s2_es_el_de_la_memoria():
    apus = {p.item.codigo_partida: p.apu for p in ob.elaborar_ob_s2().presupuesto.partidas}
    esperados = {"OB-A": (100, 12, 10), "OB-B": (40, 5, 20), "OB-C": (80, 10, 10)}
    for codigo, (cd, s, r) in esperados.items():
        costo = costo_diario(apus[codigo], ob.PARAMETROS)
        assert (costo.costo_dia, costo.salario, costo.rendimiento) == (D(cd), D(s), D(r))


def test_partidas_en_paralelo_cuando_una_partida_empieza_mas_tarde_se_adelanta():
    contexto = _contexto()
    estado = contexto.estado
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
    contexto = replace(contexto, estado=atrasada, base=reproyectar(atrasada))
    opcion = opcion_paralelo(contexto)
    assert opcion.aplica and opcion.requiere_declaracion
    assert opcion.detalle["adelantadas"] == ["OB-C"]
    assert opcion.detalle["partidas_simultaneas_maximas"] == 3
    assert opcion.costo_directo_adicional == 0
    assert opcion.termino < contexto.base.termino
