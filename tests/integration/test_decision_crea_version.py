# tests/integration/test_decision_crea_version.py
"""SL-E6: elegir una opción crea una versión nueva con su plan, su curva, su informe y su registro
(spec S2 §5.3, RF-79), y la línea base no cambia (S2-R3).

Decisión «más cuadrillas» de OB-S2: versión `OB-002` de motivo `recuperacion`, un `RegistroCambio`
(objeto `plan`) por cada fracción que cambió, R2 y R7 sin hallazgos, la curva que cierra en el total
y el SPI al mismo corte en 0,80.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core import models
from core.budget import edicion, guardar_edicion
from core.budget.control import (
    calcular_control,
    composiciones_de_la_linea_base,
    contexto_de_recuperacion,
)
from core.budget.decision import aplicar_decision, cambios_de_plan, decisiones
from core.budget.edicion import CambioEditado, registros_de_version, version_vigente
from core.budget.instantanea import plan_de_version
from core.budget.persistencia import cargar_elaboracion
from core.budget.recuperacion import opciones
from core.catalog import Catalogo
from core.verification import REGLAS
from tests.fixtures import control_ob_s2 as ob

D = Decimal
PLAN_DE_LA_DECISION = [
    ("Semana 1", [("OB-A", "0.4")]),
    ("Semana 2", [("OB-A", "0.5"), ("OB-B", "0.3")]),
    ("Semana 3", [("OB-A", "0.1"), ("OB-B", "0.54"), ("OB-C", "0.72")]),
    ("Semana 4", [("OB-B", "0.16"), ("OB-C", "0.28")]),
]
REGISTROS_DEL_PLAN = [
    ("Semana 1|OB-A", "0.5", "0.4"),
    ("Semana 2|OB-B", "0.5", "0.3"),
    ("Semana 3|OB-A", "0", "0.1"),
    ("Semana 3|OB-B", "0.5", "0.54"),
    ("Semana 3|OB-C", "0.5", "0.72"),
    ("Semana 4|OB-B", "0", "0.16"),
    ("Semana 4|OB-C", "0.5", "0.28"),
]


@pytest.fixture
def decidida(obra):
    """OB-S2 con V-01 y V-02 y el control al corte, listo para elegir una opción."""
    ob.registrar_v01_y_v02(obra)
    catalogo = Catalogo(obra)
    resultado = calcular_control(obra, ob.NOMBRE, catalogo=catalogo, precios=ob.precios_del_corte())
    contexto = contexto_de_recuperacion(resultado, composiciones_de_la_linea_base(resultado))
    return obra, catalogo, resultado, {o.nombre: o for o in opciones(contexto)}


def _decidir(decidida, nombre="cuadrillas", **extra):
    sesion, catalogo, resultado, por_nombre = decidida
    extra.setdefault("fuente", "decision ficticia del residente")
    extra.setdefault("responsable", "Residente Ficticio")
    return aplicar_decision(sesion, resultado, por_nombre[nombre], catalogo=catalogo, **extra)


def test_mas_cuadrillas_crea_la_version_ob_002_con_motivo_recuperacion(decidida):
    sesion = decidida[0]
    decision = _decidir(decidida)
    version = sesion.get(models.Presupuesto, decision.version_resultante_id)
    assert version.codigo == "OB-002" and version_vigente(sesion, ob.NOMBRE).codigo == "OB-002"
    origen = sesion.get(models.VersionOrigen, version.id)
    assert (origen.motivo, sesion.get(models.Presupuesto, origen.origen_id).codigo) == (
        "recuperacion",
        "OB-001",
    )


def test_un_registro_de_cambio_por_cada_fraccion_del_plan_que_cambio(decidida):
    sesion = decidida[0]
    decision = _decidir(decidida)
    version = sesion.get(models.Presupuesto, decision.version_resultante_id)
    registros = registros_de_version(sesion, version)
    assert [(r.clave, r.valor_anterior, r.valor_nuevo) for r in registros] == REGISTROS_DEL_PLAN
    assert {(r.objeto, r.campo) for r in registros} == {("plan", "fraccion")}
    assert {(r.fuente, r.responsable) for r in registros} == {
        ("decision ficticia del residente", "Residente Ficticio")
    }


def test_el_informe_de_la_version_nueva_no_tiene_hallazgos_de_r2_ni_de_r7_y_la_curva_cierra(
    decidida,
):
    sesion, catalogo, *_ = decidida
    _decidir(decidida)
    nueva = cargar_elaboracion(sesion, ob.NOMBRE, "OB-002", catalogo)
    assert [h for h in nueva.informe.hallazgos if h.regla in ("R2", "R7")] == []
    assert nueva.presupuesto.total_curva == nueva.presupuesto.total
    assert [p.periodo.split(" [")[0] for p in nueva.presupuesto.curva] == [
        "Semana 1", "Semana 2", "Semana 3", "Semana 4",
    ]  # fmt: skip
    # El plan se guardo con la version: el reparto se recupera tal cual.
    version = sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == "OB-002")
    ).one()
    plan = plan_de_version(sesion, version)
    assert [(e, list(r)) for e, r in plan] == [
        (e, [(c, D(f)) for c, f in r]) for e, r in PLAN_DE_LA_DECISION
    ]


def test_la_linea_base_no_cambia_y_el_spi_al_mismo_corte_sigue_en_0_80(decidida):
    sesion, catalogo, *_ = decidida
    _decidir(decidida)
    despues = calcular_control(
        sesion, ob.NOMBRE, catalogo=catalogo, precios=ob.precios_del_corte(), corte=ob.CORTE
    )
    assert despues.instantanea.linea_base.version == "OB-001"
    assert abs(despues.indicadores.spi - D("0.8")) <= D("0.0001")
    assert despues.reproyeccion.termino == 23  # el retraso no desaparece del control (S2-R3)
    assert sesion.scalar(select(func.count()).select_from(models.LineaBaseControl)) == 1


def test_la_decision_recarga_identica_con_la_foto_de_lo_que_el_usuario_vio(decidida):
    sesion, _, resultado, por_nombre = decidida
    opcion = por_nombre["cuadrillas"]
    _decidir(decidida)
    (cargada,) = decisiones(sesion, ob.NOMBRE)
    assert (cargada.version, cargada.opcion, cargada.fecha_corte) == (
        "OB-002",
        "cuadrillas",
        ob.CORTE,
    )
    assert cargada.termino == date(2026, 11, 24)  # dia habil 17
    assert (cargada.costo_directo_adicional, cargada.costo_indirecto) == (
        opcion.costo_directo_adicional,
        opcion.costo_indirecto,
    )
    assert (cargada.spi, cargada.cpi, cargada.eac) == (
        resultado.indicadores.spi,
        resultado.indicadores.cpi,
        opcion.eac,
    )
    assert cargada.pe == opcion.equilibrio.punto
    assert cargada.detalle["detalle"]["partidas"]["OB-B"]["k"] == 2
    assert cargada.detalle["plan"][2] == [
        "Semana 3",
        [["OB-A", "0.1"], ["OB-B", "0.54"], ["OB-C", "0.72"]],
    ]
    nombres = {s["nombre"]: s for s in cargada.supuestos}
    assert nombres["eta de cuadrillas"] == {
        "nombre": "eta de cuadrillas",
        "valor": "0.80",
        "naturaleza": "SUPUESTO_DECLARADO",
        "fuente": "Lee (2022) es la base del metodo, no del valor",
    }
    assert (cargada.fuente, cargada.responsable) == (
        "decision ficticia del residente",
        "Residente Ficticio",
    )
    assert cargada == decisiones(sesion, ob.NOMBRE)[0]  # recargar da lo mismo


@pytest.mark.parametrize(("fuente", "responsable"), [("", "Ing."), ("acta", " "), (" ", " ")])
def test_sin_fuente_o_sin_responsable_se_rechaza_y_no_se_escribe_nada(
    decidida, fuente, responsable
):
    sesion = decidida[0]
    versiones = sesion.scalar(select(func.count()).select_from(models.Presupuesto))
    with pytest.raises(ValueError, match="obligatori"):
        _decidir(decidida, fuente=fuente, responsable=responsable)
    assert sesion.scalar(select(func.count()).select_from(models.Presupuesto)) == versiones
    assert decisiones(sesion, ob.NOMBRE) == []


def test_una_opcion_que_no_aplica_no_se_puede_elegir(decidida):
    with pytest.raises(ValueError, match="la opcion 'paralelo' no aplica"):
        _decidir(decidida, "paralelo")


def test_las_partidas_en_paralelo_exigen_la_declaracion_de_independencia(decidida):
    sesion, catalogo, resultado, por_nombre = decidida
    adelantada = replace(
        por_nombre["cuadrillas"], nombre="paralelo", requiere_declaracion=True, detalle={}
    )
    with pytest.raises(ValueError, match="no dependen"):
        aplicar_decision(
            sesion, resultado, adelantada, catalogo=catalogo, fuente="acta", responsable="Ing."
        )
    decision = aplicar_decision(
        sesion, resultado, adelantada, catalogo=catalogo, fuente="acta", responsable="Ing.",
        declaracion_independencia="el residente declara que C no depende de A ni de B",
    )  # fmt: skip
    (cargada,) = decisiones(sesion, ob.NOMBRE)
    assert cargada.id == decision.id
    assert "no depende" in cargada.detalle["declaracion_independencia"]


def test_aceptar_el_retraso_tambien_deja_su_version_y_su_decision(decidida):
    decision = _decidir(decidida, "aceptar")
    assert decision.opcion == "aceptar" and decision.termino == date(2026, 12, 2)
    assert (decision.costo_directo_adicional, decision.costo_indirecto) == (0, D(90))


def test_la_segunda_decision_sale_de_la_version_vigente_y_registra_sus_propios_cambios(decidida):
    sesion = decidida[0]
    _decidir(decidida)
    segunda = _decidir(decidida, "aceptar")
    version = sesion.get(models.Presupuesto, segunda.version_resultante_id)
    assert version.codigo == "OB-003"
    origen = sesion.get(models.VersionOrigen, version.id)
    assert sesion.get(models.Presupuesto, origen.origen_id).codigo == "OB-002"
    assert [d.version for d in decisiones(sesion, ob.NOMBRE)] == ["OB-002", "OB-003"]


def test_la_version_nace_en_el_unico_embudo_una_sola_vez(decidida, monkeypatch):
    llamadas = []
    original = edicion.guardar_presupuesto

    def contar(*args, **kwargs):
        llamadas.append(kwargs.get("motivo"))
        return original(*args, **kwargs)

    monkeypatch.setattr(edicion, "guardar_presupuesto", contar)
    _decidir(decidida)
    assert llamadas == ["recuperacion"]


def test_una_opcion_sin_cambios_en_el_plan_no_crea_version(decidida):
    sesion, catalogo, resultado, por_nombre = decidida
    igual = replace(por_nombre["cuadrillas"], plan=tuple(ob.PLAN))
    with pytest.raises(ValueError, match="no cambia el plan"):
        aplicar_decision(
            sesion, resultado, igual, catalogo=catalogo, fuente="acta", responsable="Ing."
        )
    assert version_vigente(sesion, ob.NOMBRE).codigo == "OB-001"


def test_guardar_edicion_sin_motivo_sigue_siendo_edicion_y_rechaza_un_motivo_desconocido(obra):
    assert "recuperacion" in models.MOTIVOS_VERSION
    resultado = ob.elaborar_ob_s2("OB-002")
    cambio = [CambioEditado("cantidad", "OB-A", "cantidad", "100", "101")]
    nueva = guardar_edicion(
        obra, ob.NOMBRE, ob.CODIGO, resultado, ob.PARAMETROS, cambio, fuente="acta",
        responsable="Ing.", plan=ob.PLAN,
    )  # fmt: skip
    assert obra.get(models.VersionOrigen, nueva.id).motivo == "edicion"
    with pytest.raises(ValueError, match="motivo 'otra' desconocido"):
        guardar_edicion(
            obra, ob.NOMBRE, ob.CODIGO, ob.elaborar_ob_s2("OB-003"), ob.PARAMETROS, cambio,
            fuente="acta", responsable="Ing.", plan=ob.PLAN, motivo="otra",
        )  # fmt: skip


def test_cambios_de_plan_compara_por_celda_y_por_etiqueta():
    anterior = [("S1", (("A", D("0.5")),)), ("S2", (("A", D("0.5")), ("B", D(1))))]
    nuevo = [
        ("S1", (("A", D("0.50")),)),
        ("S2", (("A", D("0.25")), ("B", D(1)))),
        ("S3", (("A", D("0.25")),)),
    ]
    assert [
        (c.clave, c.valor_anterior, c.valor_nuevo) for c in cambios_de_plan(anterior, nuevo)
    ] == [
        ("S2|A", "0.5", "0.25"),
        ("S3|A", "0", "0.25"),
    ]
    assert cambios_de_plan(anterior, anterior) == []
    assert cambios_de_plan(None, [("S1", (("A", D(1)),))])[0].valor_anterior == "0"


def test_r13_y_r14_no_entran_a_regla_ni_al_informe_guardado_de_ninguna_version(decidida):
    """RF-62 y RV-9: son reglas externas que se recalculan en memoria; el 7 de 7 no se mueve."""
    sesion, catalogo, *_ = decidida
    ob.registrar(sesion, ob.VS)  # V-S da seis hallazgos de R13 y R14 en la instantanea
    _decidir(decidida)
    guardados = {
        h.regla for h in cargar_elaboracion(sesion, ob.NOMBRE, "OB-002", catalogo).informe.hallazgos
    }
    guardados |= set(sesion.scalars(select(models.Hallazgo.regla)))
    assert not guardados & {"R13", "R14"}
    assert [r.codigo for r in REGLAS] == ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
