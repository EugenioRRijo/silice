# tests/integration/test_valuaciones.py
"""SL-E4: valuaciones registradas, anuladas y la instantánea de control (spec S2 §3, RF-72).

OB-S2 a mano (memoria `control_ob_s2.md`): V-01 y V-02 cuentan desde su registro, la anulada se
conserva y deja de contar, nada se edita ni se borra, y un cambio de moneda invalida la línea base.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import event, func, select

from core import models
from core.budget import elaborar, guardar_edicion
from core.budget.edicion import CambioEditado
from core.budget.valuaciones import (
    Calendario,
    LineaBaseInvalidada,
    anexo_control,
    anular_valuacion,
    instantanea_control,
    registrar_costo,
    registrar_linea_base,
    registrar_valuacion,
    valuaciones_registradas,
)
from core.catalog import Catalogo
from core.verification.valuaciones import LineaValuacion
from tests.fixtures import control_ob_s2 as ob

D = Decimal
TABLAS_SOLO_AGREGAR = ("valuacion", "linea_valuacion", "anulacion_valuacion")


def _instantanea(sesion, corte=None):
    return instantanea_control(sesion, ob.NOMBRE, catalogo=Catalogo(sesion), corte=corte)


def test_v01_y_v02_cuentan_desde_su_registro_con_su_fecha_hora(obra):
    primera, segunda = ob.registrar_v01_y_v02(obra)
    assert (primera.fecha_hora, segunda.fecha_hora) == (
        datetime(2026, 11, 9, 9, 0),
        datetime(2026, 11, 16, 9, 0),
    )
    instantanea = _instantanea(obra)
    assert instantanea.corte == date(2026, 11, 13)  # el hasta de la ultima valuacion
    assert [v.numero for v in instantanea.valuaciones] == ["V-01", "V-02"]
    assert instantanea.linea_base.version == "OB-001"
    assert instantanea.moneda == "USD" and len(instantanea.costos) == 1
    assert [v.fecha_hora for v in instantanea.valuaciones] == [
        primera.fecha_hora,
        segunda.fecha_hora,
    ]


def test_una_valuacion_anulada_se_conserva_y_deja_de_contar(obra):
    _, segunda = ob.registrar_v01_y_v02(obra)
    anulacion = anular_valuacion(
        obra, segunda.id, motivo="el cliente no la aprobo", responsable=ob.RESPONSABLE
    )
    assert anulacion.valuacion_id == segunda.id
    assert [v.numero for v in valuaciones_registradas(obra, ob.NOMBRE)] == ["V-01"]
    todas = valuaciones_registradas(obra, ob.NOMBRE, con_anuladas=True)
    assert [v.numero for v in todas] == ["V-01", "V-02"]
    assert obra.scalar(select(func.count()).select_from(models.Valuacion)) == 2
    with pytest.raises(ValueError, match="ya esta anulada"):
        anular_valuacion(obra, segunda.id, motivo="otra vez", responsable=ob.RESPONSABLE)


def test_anular_exige_motivo_y_responsable_y_una_valuacion_que_exista(obra):
    _, segunda = ob.registrar_v01_y_v02(obra)
    with pytest.raises(ValueError, match="obligatoria"):
        anular_valuacion(obra, segunda.id, motivo=" ", responsable=ob.RESPONSABLE)
    with pytest.raises(ValueError, match="responsable"):
        anular_valuacion(obra, segunda.id, motivo="x", responsable="")
    with pytest.raises(KeyError):
        anular_valuacion(obra, 999, motivo="x", responsable="Ing.")


def test_registrar_rechaza_cantidad_negativa_sin_fuente_y_sin_lineas(obra):
    base = dict(numero="V-09", desde=ob.INICIO, hasta=date(2026, 11, 6), fecha=None, inspector="")
    with pytest.raises(ValueError, match="no puede ser negativa"):
        registrar_valuacion(
            obra, ob.NOMBRE, lineas=[("OB-A", D("-1"))], fuente="acta", responsable="Ing.", **base
        )
    with pytest.raises(ValueError, match="obligatoria"):
        registrar_valuacion(
            obra, ob.NOMBRE, lineas=[("OB-A", D(1))], fuente="", responsable="Ing.", **base
        )
    with pytest.raises(ValueError, match="al menos una linea"):
        registrar_valuacion(obra, ob.NOMBRE, lineas=[], fuente="acta", responsable="Ing.", **base)
    assert obra.scalar(select(func.count()).select_from(models.Valuacion)) == 0


def test_sin_linea_base_no_se_registra_ninguna_valuacion(obra_sin_linea_base):
    with pytest.raises(ValueError, match="linea base de control"):
        ob.registrar(obra_sin_linea_base, ob.V01)


def test_sin_numero_ni_inspector_se_guarda_y_r14_la_marca(obra):
    registrar_valuacion(
        obra,
        ob.NOMBRE,
        numero="",
        desde=ob.INICIO,
        hasta=date(2026, 11, 6),
        fecha=None,
        inspector="",
        lineas=[LineaValuacion("OB-A", D(1))],
        fuente="acta",
        responsable="Ing.",
    )
    informe = _instantanea(obra, corte=date(2026, 11, 6)).informe()
    assert sorted(h.descripcion.split(" no tiene ")[1] for h in informe.hallazgos) == [
        "fecha",
        "inspector",
        "numero",
    ]


def test_la_linea_base_vigente_al_corte_es_la_de_mayor_desde(obra):
    ob.registrar_v01_y_v02(obra)
    registrar_linea_base(
        obra,
        ob.NOMBRE,
        ob.CODIGO,
        desde=date(2026, 11, 10),
        perspectiva="precio",
        calendario=Calendario(date(2026, 11, 2), 5),
        fuente="nueva linea base",
        responsable="Ing.",
    )
    assert _instantanea(obra, corte=date(2026, 11, 9)).linea_base.perspectiva == "costo"
    assert _instantanea(obra, corte=date(2026, 11, 10)).linea_base.perspectiva == "precio"
    with pytest.raises(ValueError, match="no hay linea base"):
        _instantanea(obra, corte=date(2026, 11, 1))


def test_la_linea_base_exige_perspectiva_valida_fuente_y_version_existente(obra_sin_linea_base):
    sesion = obra_sin_linea_base
    base = dict(desde=ob.INICIO, calendario=ob.CALENDARIO, responsable="Ing.")
    with pytest.raises(ValueError, match="perspectiva"):
        registrar_linea_base(sesion, ob.NOMBRE, ob.CODIGO, perspectiva="otra", fuente="x", **base)
    with pytest.raises(ValueError, match="obligatoria"):
        registrar_linea_base(sesion, ob.NOMBRE, ob.CODIGO, perspectiva="costo", fuente="", **base)
    with pytest.raises(KeyError):
        registrar_linea_base(sesion, ob.NOMBRE, "NO-HAY", perspectiva="costo", fuente="x", **base)
    with pytest.raises(ValueError, match="1 o mas"):
        Calendario(ob.INICIO, 0)


def test_sin_valuaciones_y_sin_corte_pide_la_fecha(obra):
    with pytest.raises(ValueError, match="elija la fecha de corte"):
        _instantanea(obra)
    assert _instantanea(obra, corte=ob.CORTE).valuaciones == ()


def test_un_cambio_de_moneda_invalida_la_linea_base(obra):
    """RV-11: con el proyecto en Bs, la línea base sobre OB-001 (USD) queda invalidada."""
    ob.registrar_v01_y_v02(obra)
    proyecto = obra.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == ob.NOMBRE)
    ).one()
    obra.add(
        models.MonedaProyecto(
            proyecto_id=proyecto.id,
            moneda="Bs",
            desde=datetime(2026, 11, 14),
            version_id=None,
            responsable="Ing.",
            fuente="conversion ficticia",
        )
    )
    obra.flush()
    with pytest.raises(LineaBaseInvalidada, match="linea base invalidada: declarela de nuevo"):
        _instantanea(obra)


def test_costo_real_con_moneda_y_monto_validos(obra):
    registrar_costo(
        obra,
        ob.NOMBRE,
        monto=D("10.50"),
        moneda="Bs",
        fecha=ob.CORTE,
        fuente="factura 1",
        responsable="Ing.",
        codigo_partida="OB-A",
    )
    base = dict(fecha=ob.CORTE, fuente="f", responsable="I")
    with pytest.raises(ValueError, match="no negativo"):
        registrar_costo(obra, ob.NOMBRE, monto=D("-1"), moneda="USD", **base)
    with pytest.raises(ValueError, match="moneda"):
        registrar_costo(obra, ob.NOMBRE, monto=D(1), moneda="EUR", **base)


def test_el_anexo_de_control_trae_todo_con_las_anuladas_marcadas(obra):
    primera, _ = ob.registrar_v01_y_v02(obra)
    anular_valuacion(obra, primera.id, motivo="error de medicion", responsable="Ing.")
    anexo = anexo_control(obra, ob.NOMBRE)
    assert [v["numero"] for v in anexo["valuaciones"]] == ["V-01", "V-02"]
    assert anexo["valuaciones"][0]["anulada"]["motivo"] == "error de medicion"
    assert anexo["valuaciones"][1]["anulada"] is None
    assert anexo["valuaciones"][1]["fecha_hora"] == "2026-11-16T09:00:00"
    assert anexo["valuaciones"][1]["lineas"][1] == {
        "partida": "OB-B",
        "cantidad": "60",
        "fecha_medicion": None,
        "observacion": "",
    }
    assert anexo["lineas_base"][0]["version"] == "OB-001"
    assert anexo["costos"][0]["monto"] == "1280.00"
    assert anexo == anexo_control(obra, ob.NOMBRE)  # determinista


def test_ninguna_funcion_emite_update_ni_delete_sobre_las_tablas_solo_agregar(motor, obra):
    """S2-R10: se ejercen las operaciones de escritura y lectura y se miran los SQL emitidos."""
    emitidos: list[str] = []

    @event.listens_for(motor, "before_cursor_execute")
    def _guardar(conexion, cursor, sentencia, parametros, contexto, varias):
        emitidos.append(sentencia)

    primera, _ = ob.registrar_v01_y_v02(obra)
    anular_valuacion(obra, primera.id, motivo="prueba", responsable="Ing.")
    _instantanea(obra, corte=ob.CORTE)
    anexo_control(obra, ob.NOMBRE)
    obra.flush()
    patron = re.compile(rf"^\s*(UPDATE|DELETE FROM)\s+({'|'.join(TABLAS_SOLO_AGREGAR)})\b", re.I)
    assert [sentencia for sentencia in emitidos if patron.match(sentencia)] == []
    assert any(s.lstrip().upper().startswith("INSERT INTO VALUACION") for s in emitidos)


def test_una_variacion_de_obra_declarada_como_linea_base_hace_pasar_r13(obra):
    """UC-19 4b: lo valuado sobre lo presupuestado se guarda con R13 ERROR; registrar la variación
    por la hoja (versión nueva con la cantidad) y declararla línea base lo resuelve."""
    ob.registrar_v01_y_v02(obra)
    ob.registrar(obra, ob.VS)
    antes = _instantanea(obra, corte=ob.CORTE_DE_VS).informe()
    assert [h.origen_ids[0] for h in antes.hallazgos if h.regla == "R13"] == [
        "valuacion:V-03:OB-B",
        "valuacion:V-03:OB-D",
    ]
    mayor = [replace(i, cantidad=D(210)) if i.codigo_partida == "OB-B" else i for i in ob.items()]
    variacion = elaborar(
        mayor, ob.composiciones(), ob.PARAMETROS, codigo="OB-002", fecha=ob.FECHA,
        moneda=ob.MONEDA, plan=ob.PLAN,
    )  # fmt: skip
    guardar_edicion(
        obra, ob.NOMBRE, ob.CODIGO, variacion, ob.PARAMETROS,
        [CambioEditado("cantidad", "OB-B", "cantidad", "200", "210")],
        fuente="acta de variacion ficticia", responsable=ob.RESPONSABLE, plan=ob.PLAN,
    )  # fmt: skip
    registrar_linea_base(
        obra, ob.NOMBRE, "OB-002", desde=date(2026, 11, 12), perspectiva="costo",
        calendario=ob.CALENDARIO, fuente="la variacion pasa a ser la linea base",
        responsable=ob.RESPONSABLE,
    )  # fmt: skip
    despues = _instantanea(obra, corte=ob.CORTE_DE_VS)
    assert despues.linea_base.version == "OB-002"
    assert [h.origen_ids[0] for h in despues.informe().hallazgos if h.regla == "R13"] == [
        "valuacion:V-03:OB-D"
    ]  # B ya cabe; D sigue sin estar presupuestada
    # Al corte anterior a la variacion rige la linea base anterior.
    assert _instantanea(obra, corte=date(2026, 11, 11)).linea_base.version == "OB-001"
