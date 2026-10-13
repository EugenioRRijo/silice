"""La sesion del asistente para la pantalla (S4 §3.1 pasos 5-7, 9g, 9h; plan 0.9.0, tarea 14).

Con el proveedor guionado (sin red). Ajustes registrados en la bitacora de la 0.9.0 (revision final
de S4.3): `responder(..., proveedor=)` recibe el proveedor VIGENTE porque la sesion no lo retiene
(por la clave), y `decidir(..., sobre=)` aplica una sola propuesta sobre la hoja editada a mano.
Oraculos: los literales de `tests/fixtures/asistente_pedidos.py` y la cuenta de costo a mano.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from asistente.orquestador import ESPERAR, MotivoFin, Servicios
from asistente.propuestas import EstadoPropuesta, Propuesta, TipoPropuesta
from asistente.proveedores.base import FinTurno, LlamadaHerramienta, Tarifa, Turno, Uso
from asistente.proveedores.guionado import ProveedorGuionado
from asistente.registro import RegistroIA, anexo_ia, crear_esquema_ia
from asistente.servicio import (
    TURNOS_ESTIMADOS,
    DependenciaPendiente,
    borrador_resultante,
    decidir,
    descripcion,
    estimar_costo,
    fuente_del_cambio,
    hipotetico,
    proponer,
    responder,
    resumen_hipotetico,
)
from asistente.tarifas import cargar_tarifas
from tests.fixtures.asistente_pedidos import AMBIENTE, FECHA, PEDIDO, catalogo
from ui import hoja
from ui.hoja import Borrador, HojaInvalida

TARIFA = Tarifa(entrada=Decimal(1_000_000), salida=Decimal(2_000_000))
FUENTE = {
    "id": "F1",
    "especialidad": "agua",
    "tipo": "montante_agua",
    "ambiente_id": "BAN-01",
    "x": "0",
    "y": "0",
    "z": "0",
    "citas": [],
    "supuestos": [{"campo": c, "motivo": "montante en la esquina"} for c in "xyz"],
}


def _servicios(registro=None, **mas) -> Servicios:
    return Servicios(
        catalogo=catalogo(),
        tarifa=TARIFA,
        auditar=lambda b: hoja.elaborar_borrador(b).elaboracion.informe,
        registro=registro,
        proyecto="OF",
        version_partida="001",
        **mas,
    )


def sesion(con=None):
    llamadas = (
        LlamadaHerramienta("a", "proponer_ambiente", AMBIENTE),
        LlamadaHerramienta("b", "proponer_fuente", FUENTE),
        LlamadaHerramienta("t", "terminar", {"notas": []}),
    )
    proveedor = ProveedorGuionado([Turno("", llamadas, FinTurno.HERRAMIENTAS, Uso(entrada=1))])
    registro = RegistroIA(con) if con is not None else None
    return proponer(proveedor, PEDIDO, Borrador(fecha=FECHA), _servicios(registro))


def test_proponer_no_cambia_el_borrador_y_rechazar_todo_lo_deja_identico():
    s = sesion()
    assert [p.id for p in s.pendientes.vigentes()] == ["P1", "P2"]
    assert borrador_resultante(s) == s.base == Borrador(fecha=FECHA)
    assert decidir(s, "P1", EstadoPropuesta.RECHAZADA, "ana") is None  # rechazar no lo toca
    assert decidir(s, "P2", EstadoPropuesta.RECHAZADA, "ana") is None
    assert borrador_resultante(s) == Borrador(fecha=FECHA)
    assert not s.pendientes.vigentes()


def test_aceptar_una_propuesta_que_depende_de_otra_pendiente_avisa_cual():
    s = sesion()
    with pytest.raises(DependenciaPendiente, match="P2 depende"):
        decidir(s, "P2", EstadoPropuesta.ACEPTADA, "ana")  # la fuente necesita el ambiente
    assert s.pendientes.buscar("P2").estado is EstadoPropuesta.PENDIENTE  # no cambio nada
    nuevo = decidir(s, "P1", EstadoPropuesta.ACEPTADA, "ana")
    assert [a.id for a in nuevo.espacio.ambientes] == ["BAN-01"]
    decidir(s, "P2", EstadoPropuesta.EDITADA, "ana")
    assert [a.id for a in borrador_resultante(s).espacio.ambientes] == ["BAN-01"]
    assert [f.id for f in borrador_resultante(s).espacio.fuentes] == ["F1"]


def test_lo_aceptado_lleva_el_origen_de_ia_con_la_sesion_y_la_propuesta():
    s = sesion()
    decidir(s, "P1", EstadoPropuesta.ACEPTADA, "ana")
    (origen,) = borrador_resultante(s).espacio.origenes
    assert origen.tipo.value == "ia" and origen.id == "IA-0-P1"


def test_el_hipotetico_incluye_lo_pendiente_y_el_sistema_calcula_el_resultado():
    s = sesion()
    decidir(s, "P1", EstadoPropuesta.ACEPTADA, "ana")
    assert borrador_resultante(s).espacio.fuentes == ()
    assert [f.id for f in hipotetico(s).espacio.fuentes] == ["F1"]
    resumen = resumen_hipotetico(hipotetico(s))
    # R8: un hallazgo por supuesto declarado: 2 del ambiente (x0, y0) + 3 de la fuente (x, y, z)
    assert resumen.hallazgos.get("ADVERTENCIA") == 5
    assert resumen.moneda == Borrador(fecha=FECHA).moneda
    assert resumen.total == Decimal(0)  # sin partidas: el sistema no inventa montos


def test_decidir_dos_veces_o_una_inexistente_es_un_error_y_la_fuente_nombra_la_sesion():
    s = sesion()
    decidir(s, "P1", EstadoPropuesta.ACEPTADA, "ana")
    with pytest.raises(KeyError):
        decidir(s, "P1", EstadoPropuesta.RECHAZADA, "ana")
    with pytest.raises(KeyError):
        decidir(s, "P9", EstadoPropuesta.ACEPTADA, "ana")
    with pytest.raises(ValueError, match="aceptada, editada o rechazada"):
        decidir(s, "P2", EstadoPropuesta.PENDIENTE, "ana")
    assert fuente_del_cambio(s) == "propuesta de IA, sesion 0, guionado/guion-1"


def test_las_decisiones_quedan_en_el_registro_y_viajan_en_el_anexo():
    motor = create_engine("sqlite://")
    try:
        crear_esquema_ia(motor)
        with motor.begin() as con:
            s = sesion(con)
            registro = RegistroIA(con)  # la conexion vigente al decidir
            decidir(s, "P1", EstadoPropuesta.ACEPTADA, "ana", registro)
            decidir(s, "P2", EstadoPropuesta.RECHAZADA, "ana", registro)
            registro.marcar_guardada(s.resultado.sesion, "002")
            anexo = anexo_ia(con, "OF", "002").decode()
            assert anexo_ia(con, "OF", "001") is None  # guardada en 002: no entra en la 001
    finally:
        motor.dispose()
    assert '"estado":"aceptada"' in anexo and '"estado":"rechazada"' in anexo
    assert anexo.count('"decidida_por":"ana"') == 2


class _RegistroQueFalla:
    def decidir(self, *args, **kwargs):
        raise OperationalError("UPDATE", {}, Exception("base bloqueada"))


def test_si_el_registro_falla_nada_queda_decidido():
    s = sesion()
    with pytest.raises(OperationalError):
        decidir(s, "P1", EstadoPropuesta.ACEPTADA, "ana", _RegistroQueFalla())
    assert s.pendientes.buscar("P1").estado is EstadoPropuesta.PENDIENTE


def test_con_la_hoja_editada_a_mano_aceptar_aplica_solo_esa_propuesta_sobre_ella():
    s = sesion()
    aceptado = decidir(s, "P1", EstadoPropuesta.ACEPTADA, "ana")
    editada = replace(aceptado, moneda="VES")  # una edicion a mano despues de aceptar
    nuevo = decidir(s, "P2", EstadoPropuesta.ACEPTADA, "ana", sobre=editada)
    assert nuevo.moneda == "VES"  # la edicion se conserva
    assert [f.id for f in nuevo.espacio.fuentes] == ["F1"]
    assert [p.id for p in hipotetico(s, sobre=nuevo).espacio.fuentes] == ["F1"]


def test_si_la_propuesta_no_cabe_en_la_hoja_editada_nada_queda_decidido():
    s = sesion()
    decidir(s, "P1", EstadoPropuesta.ACEPTADA, "ana")
    sin_ambiente = Borrador(fecha=FECHA)  # la persona quito el ambiente a mano
    with pytest.raises(HojaInvalida):
        decidir(s, "P2", EstadoPropuesta.ACEPTADA, "ana", sobre=sin_ambiente)
    assert s.pendientes.buscar("P2").estado is EstadoPropuesta.PENDIENTE


def _propuesta(tipo: TipoPropuesta, fila: dict, **mas) -> Propuesta:
    return Propuesta("P1", tipo, (fila,), **mas)


def test_descripcion_de_cada_tipo():
    s = sesion()
    assert [descripcion(p) for p in s.pendientes.propuestas] == [
        "Ambiente BAN-01: 2.4 x 1.5 x 2.5 m",
        "Fuente F1 (montante_agua) en (0; 0; 0)",
    ]
    punto = {
        "id": "LV1",
        "nombre": "Lavamanos",
        "tipo": "lavamanos",
        "x": "1",
        "y": "0",
        "z": "0.6",
    }
    assert descripcion(_propuesta(TipoPropuesta.PUNTO, punto)) == (
        "Punto LV1 Lavamanos (lavamanos) en (1; 0; 0.6)"
    )
    recorrido = {"punto_id": "LV1", "circuito_id": ""}
    assert descripcion(_propuesta(TipoPropuesta.RECORRIDO, recorrido)) == (
        "Recorrido de LV1 (calculado por el sistema)"
    )
    declarado = {"punto_id": "", "circuito_id": "C1"}
    assert descripcion(_propuesta(TipoPropuesta.RECORRIDO, declarado, declarado=True)) == (
        "Recorrido de C1 (declarado)"
    )
    partida = {"codigo": "AF-SALIDA", "cantidad": "2", "unidad": "punto"}
    assert descripcion(_propuesta(TipoPropuesta.PARTIDA, partida)) == ("Partida AF-SALIDA: 2 punto")
    sin = {"necesidad": "rejilla de piso"}
    assert descripcion(_propuesta(TipoPropuesta.SIN_PARTIDA, sin)) == (
        "Sin partida en el catalogo: rejilla de piso"
    )


def test_estimacion_de_costo_a_mano():
    # §8.4, tarifa de Opus 5.5 (4 / 20 / 0,20 USD por MTok): por turno
    # 10000*4 + 3000*20 + 6000*0,2 = 101 200 / 1e6 = 0,1012; por 12 turnos = 1,2144 USD
    assert TURNOS_ESTIMADOS == 12
    assert estimar_costo(cargar_tarifas()["claude-opus-5-5"]) == Decimal("1.2144")
    assert estimar_costo(cargar_tarifas()["local"]) == Decimal(0)


def _pregunton() -> ProveedorGuionado:
    llamadas = (
        LlamadaHerramienta("q", "preguntar_al_usuario", {"pregunta": "Alto del bano?"}),
        LlamadaHerramienta("a", "proponer_ambiente", AMBIENTE),
    )
    return ProveedorGuionado(
        [
            Turno("", llamadas, FinTurno.HERRAMIENTAS, Uso(entrada=1)),
            Turno("", (LlamadaHerramienta("t", "terminar", {"notas": []}),), FinTurno.HERRAMIENTAS),
        ]
    )


def test_una_pregunta_pausa_y_responder_reanuda_con_las_propuestas_pendientes():
    proveedor = _pregunton()
    servicios = _servicios(responder=lambda _p: ESPERAR)
    s = proponer(proveedor, PEDIDO, Borrador(fecha=FECHA), servicios)
    assert s.resultado.motivo is MotivoFin.ESPERANDO_RESPUESTA
    assert s.resultado.pregunta == "Alto del bano?" and s.pendientes.propuestas == []
    assert borrador_resultante(s) == s.base  # pausada: el borrador no cambia
    assert s.resultado.continuacion.proveedor is None  # la sesion no retiene el proveedor (§8.3)
    with pytest.raises(ValueError, match="proveedor vigente"):
        responder(s, "El alto es 2,5 m")
    responder(s, "El alto es 2,5 m", proveedor=proveedor)
    assert s.resultado.motivo is MotivoFin.TERMINAR and s.resultado.pregunta is None
    assert [p.id for p in s.pendientes.vigentes()] == ["P1"]
    assert s.resultado.respuestas_de_la_persona == ("El alto es 2,5 m",)
    with pytest.raises(ValueError, match="no esta esperando"):
        responder(s, "otra", proveedor=proveedor)


def test_responder_none_cancela_sin_proveedor():
    s = proponer(
        _pregunton(), PEDIDO, Borrador(fecha=FECHA), _servicios(responder=lambda _p: ESPERAR)
    )
    responder(s, None)
    assert s.resultado.motivo is MotivoFin.CANCELADO and s.pendientes.propuestas == []


class _RegistroQueFallaAlResponder:
    def llamada(self, *args, **kwargs):
        raise OperationalError("INSERT", {}, Exception("base bloqueada"))

    def __getattr__(self, nombre):
        return lambda *a, **k: None


def test_si_responder_falla_la_sesion_sigue_esperando_la_misma_pregunta():
    proveedor = _pregunton()
    s = proponer(proveedor, PEDIDO, Borrador(fecha=FECHA), _servicios(responder=lambda _p: ESPERAR))
    with pytest.raises(OperationalError):
        responder(s, "2,5 m", _RegistroQueFallaAlResponder(), proveedor=proveedor)
    assert s.resultado.motivo is MotivoFin.ESPERANDO_RESPUESTA
    assert s.resultado.pregunta == "Alto del bano?"
    assert s.resultado.continuacion.proveedor is None
    responder(s, "2,5 m", None, proveedor=proveedor)  # reintento sin registro: sigue la sesion
    assert s.resultado.motivo is MotivoFin.TERMINAR
    assert [p.id for p in s.pendientes.vigentes()] == ["P1"]


def test_una_respuesta_con_clave_no_llega_al_modelo():
    proveedor = _pregunton()
    s = proponer(proveedor, PEDIDO, Borrador(fecha=FECHA), _servicios(responder=lambda _p: ESPERAR))
    responder(s, "mi clave es sk-ant-api03-SECRETA", proveedor=proveedor)
    resultado = proveedor.recibidos[1][1][2].resultados[0]  # lo que recibio el modelo
    assert resultado.es_error and "SECRETA" not in resultado.contenido
    assert "SECRETA" not in repr(proveedor.recibidos)
    assert s.resultado.respuestas_de_la_persona == ()
