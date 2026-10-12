# tests/integration/test_control.py
"""SL-E5: el control de OB-S2 de la base al resultado (spec S2 §4, §5.3; RF-75 a RF-77).

`calcular_control` lee la base, convierte los costos con la tasa de su fecha (S1) y devuelve
indicadores, separación, reproyección, punto de equilibrio y alertas, sin escribir nada.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core import models
from core.budget.control import (
    calcular_control,
    guardar_parametros,
    parametros_de_control,
    precios_del_corte_de_version,
)
from core.budget.puente import estudio_con_valuaciones
from core.budget.valor_ganado import ParametrosControl
from core.budget.valuaciones import anular_valuacion, registrar_costo
from core.catalog import Catalogo
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz

D = Decimal
MONTOS = D("0.01")


def _control(sesion, **extra):
    extra.setdefault("precios", ob.precios_del_corte())
    return calcular_control(sesion, ob.NOMBRE, catalogo=Catalogo(sesion), **extra)


def _tasa(sesion, fecha: date, valor: str = "850"):
    registrar_importacion(
        sesion, definicion_tasa("venta"), [Observacion(fecha, D(valor))], archivo="tasa.xls",
        huella=f"{fecha.day:02d}" * 32, fuente="https://www.bcv.org.ve/",
        fecha_descarga=date(2026, 11, 20), responsable="Admin", filas_leidas=1, filas_rechazadas=0,
    )  # fmt: skip


def _sin_costos(sesion):
    sesion.query(models.CostoReal).delete()
    sesion.flush()


def test_ob_s2_de_punta_a_punta_da_la_memoria(obra):
    ob.registrar_v01_y_v02(obra)
    r = _control(obra)
    assert r.instantanea.corte == ob.CORTE
    ind = r.indicadores
    assert (ind.pv, ind.ev, ind.ac) == (D(1500), D(1200), D(1280))
    assert abs(ind.eac_sistema - D(4480)) <= MONTOS and r.reproyeccion.termino == 23
    assert (r.separacion.precio, r.separacion.consumo) == (D(-60), D(-20))
    assert {a.codigo for a in r.alertas.alertas} == {"AL-1", "AL-2", "AL-3", "AL-4", "AL-5"}
    assert abs(r.equilibrio_base.punto - D("2864.15")) <= MONTOS
    assert abs(r.equilibrio_proyectado.punto - D("6019.66")) <= MONTOS  # sin reajuste reconocido
    assert r.reajuste.monto == 0 and r.reajuste.estudios == ()
    assert r.informe.hallazgos == () and r.informe.cumple
    assert (r.venta, r.costo_fijo) == (D(5060), D(600))


def test_una_valuacion_anulada_deja_de_contar_y_al_registrarla_de_nuevo_ev_vuelve(obra):
    _, segunda = ob.registrar_v01_y_v02(obra)
    anular_valuacion(obra, segunda.id, motivo="no aprobada", responsable="Ing.")
    anulada = _control(obra, corte=ob.CORTE)
    assert anulada.indicadores.ev == D(400)  # solo V-01: A 40 x 10
    ob.registrar(obra, ob.V02, ahora=None)
    assert _control(obra, corte=ob.CORTE).indicadores.ev == D(1200)  # el EV de la memoria


def test_calcular_el_control_no_escribe_nada(obra):
    ob.registrar_v01_y_v02(obra)
    tablas = (models.Valuacion, models.LineaValuacion, models.RegistroCambio, models.Presupuesto)

    def cuentas():
        return [obra.scalar(select(func.count()).select_from(t)) for t in tablas]

    antes = cuentas()
    _control(obra)
    assert cuentas() == antes


def test_un_costo_en_bs_se_convierte_con_la_tasa_de_su_fecha(obra):
    ob.registrar_v01_y_v02(obra)
    _sin_costos(obra)
    _tasa(obra, date(2026, 11, 13), "850")
    registrar_costo(
        obra, ob.NOMBRE, monto=D("1088000"), moneda="Bs", fecha=date(2026, 11, 13),
        fuente="factura ficticia", responsable="Ing.",
    )  # fmt: skip
    r = _control(obra)
    assert r.indicadores.ac == D(1280)  # 1 088 000 Bs / 850
    assert r.indicadores.cpi == D("0.9375") and r.costos_sin_tasa == ()


def test_un_costo_en_bs_sin_tasa_aplicable_deja_el_ac_no_disponible_y_lo_declara(obra):
    ob.registrar_v01_y_v02(obra)
    _tasa(obra, date(2026, 11, 4), "850")  # 9 dias antes del 13: mas de 7, se rechaza (S1-R2)
    registrar_costo(
        obra, ob.NOMBRE, monto=D("1000"), moneda="Bs", fecha=date(2026, 11, 13),
        fuente="factura ficticia", responsable="Ing.",
    )  # fmt: skip
    r = _control(obra)
    ind = r.indicadores
    assert (ind.ac, ind.cv, ind.cpi, ind.eac_sistema, ind.vac) == (None,) * 5
    assert (r.separacion.consumo, r.equilibrio_proyectado) == (None, None)
    assert [c.monto for c in r.costos_sin_tasa] == [D(1000)]
    assert "sin tasa aplicable para: 1000 Bs del 2026-11-13" in ind.no_disponible["AC"]
    assert (ind.pv, ind.ev) == (D(1500), D(1200)) and abs(ind.spi - D("0.8")) <= D("0.0001")
    assert r.reproyeccion.termino == 23 and r.separacion.precio == D(-60)
    assert "AL-2" in r.alertas.no_evaluadas and "AL-4" in r.alertas.no_evaluadas


def test_un_costo_posterior_al_corte_no_cuenta(obra):
    ob.registrar_v01_y_v02(obra)
    registrar_costo(
        obra, ob.NOMBRE, monto=D(999), moneda="USD", fecha=date(2026, 11, 14),
        fuente="factura ficticia", responsable="Ing.",
    )  # fmt: skip
    assert _control(obra).indicadores.ac == D(1280)


def test_los_precios_del_corte_por_comprobacion_directa_salen_de_una_version_revalorada(obra):
    ob.registrar_v01_y_v02(obra)
    rz.sembrar_revaloracion(obra)
    precios = precios_del_corte_de_version(obra, ob.NOMBRE, rz.REVALORADA, "costo", Catalogo(obra))
    assert precios.metodo == "comprobacion"
    assert precios.unitarios == ob.UNITARIOS_DEL_CORTE
    assert "OB-R01" in precios.fuente and "OB-S2 revalorada" in precios.fuente
    r = _control(obra, precios=precios)
    assert (r.separacion.precio, r.separacion.consumo) == (D(-60), D(-20))
    pu = precios_del_corte_de_version(obra, ob.NOMBRE, rz.REVALORADA, "precio", Catalogo(obra))
    assert pu.unitarios["OB-B"] == D("7.59")  # 6,00 x 1,265


def test_con_el_estudio_guardado_el_reajuste_reconocido_entra_al_pe_proyectado(obra):
    ob.registrar_v01_y_v02(obra)
    rz.sembrar_revaloracion(obra)
    estudio_con_valuaciones(
        obra, ob.NOMBRE, ob.CODIGO, rz.CLAUSULA, [rz.NOVIEMBRE], fecha_calculo=date(2026, 11, 13),
        fuente="estudio ficticio", responsable="Ing.",
    )  # fmt: skip
    r = _control(obra)
    assert r.reajuste.monto == D("75.90") and len(r.reajuste.estudios) == 1
    assert r.equilibrio_proyectado.venta == D("5135.90")
    assert abs(r.equilibrio_proyectado.punto - D("5402.91")) <= MONTOS
    assert {a.codigo for a in r.alertas.alertas} == {"AL-1", "AL-2", "AL-3", "AL-4", "AL-5"}


def test_la_perspectiva_precio_no_tiene_punto_de_equilibrio_y_el_consumo_es_cero(obra):
    ob.registrar_v01_y_v02(obra)
    ob.declarar_linea_base(obra, perspectiva="precio", desde=date(2026, 11, 10))
    pu = {c: u * D("1.265") for c, u in ob.UNITARIOS_DEL_CORTE.items()}
    r = _control(obra, precios=replace(ob.precios_del_corte(), unitarios=pu))
    assert r.instantanea.linea_base.perspectiva == "precio"
    assert (r.equilibrio_base, r.equilibrio_proyectado) == (None, None)
    assert r.separacion.consumo == 0
    assert "AL-4" in r.alertas.no_evaluadas


def test_los_parametros_de_control_se_guardan_con_su_registro_de_cambio(obra):
    assert parametros_de_control(obra, ob.NOMBRE) == ParametrosControl()  # sin fila: por defecto
    nuevos = replace(ParametrosControl(), spi_error=D("0.85"), horas_extra_dia=D("1.5"))
    cambios = guardar_parametros(
        obra, ob.NOMBRE, nuevos, fuente="criterio de la empresa", responsable="Ing.",
    )  # fmt: skip
    assert [(c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("spi_error", "0.90", "0.85"),
        ("horas_extra_dia", "2", "1.5"),
    ]
    assert parametros_de_control(obra, ob.NOMBRE) == nuevos
    registros = obra.scalars(
        select(models.RegistroCambio).where(models.RegistroCambio.objeto == "parametro")
    ).all()
    assert [r.clave for r in registros] == ["control|spi_error", "control|horas_extra_dia"]
    assert {r.fuente for r in registros} == {"criterio de la empresa"}
    assert guardar_parametros(obra, ob.NOMBRE, nuevos, fuente="x", responsable="y") == []
    with pytest.raises(ValueError, match="obligatoria"):
        guardar_parametros(obra, ob.NOMBRE, ParametrosControl(), fuente="", responsable="Ing.")


def test_los_parametros_guardados_gobiernan_las_alertas(obra):
    ob.registrar_v01_y_v02(obra)
    guardar_parametros(
        obra, ob.NOMBRE, replace(ParametrosControl(), spi_error=D("0.70")), fuente="f",
        responsable="Ing.",
    )  # fmt: skip
    alertas = {a.codigo: a for a in _control(obra).alertas.alertas}
    assert alertas["AL-1"].severidad.name == "ADVERTENCIA"  # SPI 0,80 >= 0,70
