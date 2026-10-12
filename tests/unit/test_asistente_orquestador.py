"""El bucle neutral con el proveedor guionado (S4 §3.1 flujos 9a-9j, §5.3; plan 0.9.0, tarea 11).

Cada flujo alterno tiene su guion; los registros esperados y el turno exacto de cada tope se
calcularon a mano. Ninguna prueba abre la red.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from asistente.orquestador import MotivoFin, Servicios, Topes, ejecutar, herramientas_visibles
from asistente.propuestas import EstadoPropuesta, TipoPropuesta
from asistente.proveedores.base import (
    ErrorDeProveedor,
    FinTurno,
    LlamadaHerramienta,
    Tarifa,
    Turno,
    Uso,
)
from asistente.proveedores.guionado import ProveedorGuionado
from asistente.registro import RegistroIA, anexo_ia, crear_esquema_ia, volcado
from tests.fixtures.asistente_pedidos import AMBIENTE, FECHA, PEDIDO, catalogo
from ui import hoja
from ui.hoja import Borrador

#: 1 USD por ficha de entrada y 2 USD por ficha de salida: el costo de un turno es un entero.
TARIFA = Tarifa(entrada=Decimal(1_000_000), salida=Decimal(2_000_000))


def llamada(id_: str, nombre: str, argumentos: dict) -> LlamadaHerramienta:
    return LlamadaHerramienta(id_, nombre, argumentos)


USO_BASE = Uso(entrada=1)


def turno(*llamadas, fin=FinTurno.HERRAMIENTAS, uso=USO_BASE, texto="") -> Turno:
    return Turno(texto, tuple(llamadas), fin, uso, "guion-1")


AMBIENTE_OK = llamada("t1", "proponer_ambiente", AMBIENTE)
AMBIENTE_MALO = llamada("t1", "proponer_ambiente", {**AMBIENTE, "largo": "2.5"})  # cita 2,4
TERMINAR = llamada("tf", "terminar", {"notas": ["listo"]})


def servicios(**kw) -> Servicios:
    base = dict(
        catalogo=catalogo(),
        tarifa=TARIFA,
        auditar=lambda b: hoja.elaborar_borrador(b).elaboracion.informe,
    )
    return Servicios(**{**base, **kw})


def correr(guion, *, topes=Topes(costo=None), **kw):  # noqa: B008
    proveedor = ProveedorGuionado(guion)
    resultado = ejecutar(
        proveedor, PEDIDO, Borrador(fecha=FECHA), servicios(**kw), topes, sesion_n=7
    )
    return proveedor, resultado


def test_camino_feliz_deja_una_propuesta_pendiente_y_el_borrador_intacto():
    proveedor, r = correr(
        [
            turno(llamada("c1", "consultar_borrador", {}), AMBIENTE_OK),
            turno(TERMINAR, uso=Uso(entrada=1, salida=1)),
        ]
    )
    assert r.motivo is MotivoFin.TERMINAR and (r.turnos, r.llamadas) == (2, 3)
    assert [(p.id, p.tipo, p.estado) for p in r.propuestas] == [
        ("P1", TipoPropuesta.AMBIENTE, EstadoPropuesta.PENDIENTE)
    ]
    assert r.costo == Decimal(1 + 3)  # turno 1: 1 USD; turno 2: 1 + 2
    assert r.uso == Uso(entrada=2, salida=1) and r.modelos == ("guion-1",)
    assert r.notas == ("listo",)
    # el segundo turno vio los resultados del primero, todos en un solo mensaje (§5.3)
    mensajes = proveedor.recibidos[1][1]
    assert [m.rol for m in mensajes] == ["usuario", "asistente", "usuario"]
    assert [x.llamada_id for x in mensajes[2].resultados] == ["c1", "t1"]
    assert not any(x.es_error for x in mensajes[2].resultados)


def test_invalida_y_luego_corregida_devuelve_el_motivo_como_error_de_la_herramienta():
    proveedor, r = correr([turno(AMBIENTE_MALO), turno(AMBIENTE_OK), turno(TERMINAR)])
    (error,) = proveedor.recibidos[1][1][2].resultados
    assert error.es_error and error.contenido.startswith("rechazada (numero_ausente_de_la_cita)")
    assert [p.id for p in r.propuestas] == ["P1"] and r.motivo is MotivoFin.TERMINAR


def test_tres_rechazos_seguidos_de_la_misma_herramienta_detienen_la_sesion():
    _, r = correr(
        [
            turno(AMBIENTE_OK),
            turno(AMBIENTE_MALO),
            turno(AMBIENTE_MALO),
            turno(AMBIENTE_MALO),
            turno(TERMINAR),
        ]
    )
    assert r.motivo is MotivoFin.RECHAZOS_SEGUIDOS and r.turnos == 4
    assert len(r.propuestas) == 1  # lo valido se conserva


def test_un_exito_entre_dos_rechazos_reinicia_la_cuenta():
    otro = llamada("t9", "proponer_ambiente", {**AMBIENTE, "id": "BAN-02"})
    _, r = correr(
        [
            turno(AMBIENTE_MALO),
            turno(AMBIENTE_MALO),
            turno(AMBIENTE_OK),
            turno(AMBIENTE_MALO),
            turno(otro),
            turno(TERMINAR),
        ]
    )
    assert r.motivo is MotivoFin.TERMINAR


def test_refusal_descarta_el_turno_y_conserva_lo_ya_validado():
    _, r = correr([turno(AMBIENTE_OK), turno(AMBIENTE_OK, fin=FinTurno.RECHAZO)])
    assert r.motivo is MotivoFin.REHUSADO and len(r.propuestas) == 1  # la del turno 1


def test_max_tokens_descarta_el_turno_entero():
    _, r = correr([turno(AMBIENTE_OK, fin=FinTurno.LIMITE)])
    assert r.motivo is MotivoFin.LIMITE_DE_SALIDA and r.propuestas == ()


def test_tope_de_turnos():
    lectura = llamada("c", "consultar_borrador", {})
    _, r = correr(
        [turno(lectura), turno(lectura), turno(lectura)], topes=Topes(turnos=2, costo=None)
    )
    assert (r.motivo, r.turnos) == (MotivoFin.TOPE_DE_TURNOS, 2)


def test_tope_de_llamadas_corta_en_la_tercera():
    lectura = [llamada(f"c{i}", "consultar_borrador", {}) for i in range(5)]
    _, r = correr([turno(*lectura)], topes=Topes(llamadas=3, costo=None))
    assert (r.motivo, r.llamadas) == (MotivoFin.TOPE_DE_LLAMADAS, 3)


def test_el_tope_de_costo_se_alcanza_en_el_turno_exacto_calculado_a_mano():
    # tope 2,50 USD; cada turno cuesta 1 USD: acumulado 1, 2, 3 -> el tercero lo alcanza (3 >= 2,5)
    lectura = llamada("c", "consultar_borrador", {})
    guion = [turno(lectura), turno(lectura), turno(AMBIENTE_OK), turno(lectura)]
    _, r = correr(guion, topes=Topes(costo=Decimal("2.5")))
    assert (r.motivo, r.turnos, r.costo) == (MotivoFin.TOPE_DE_COSTO, 3, Decimal(3))
    assert [p.id for p in r.propuestas] == ["P1"]  # el turno del tope se completo y se conserva
    _, justo = correr(
        [turno(lectura), turno(lectura), turno(TERMINAR)], topes=Topes(costo=Decimal(3))
    )
    assert (justo.motivo, justo.turnos) == (MotivoFin.TERMINAR, 3)  # 3 >= 3 pero termina antes


def test_necesidad_sin_partida_queda_pendiente_y_no_inventa_una():
    sin = llamada("s", "declarar_sin_partida", {"necesidad": "cuadro de transferencia"})
    _, r = correr([turno(sin), turno(TERMINAR)])
    assert [(p.tipo, dict(p.filas[0])) for p in r.propuestas] == [
        (TipoPropuesta.SIN_PARTIDA, {"necesidad": "cuadro de transferencia"})
    ]


def test_la_pregunta_se_responde_y_sus_cifras_se_pueden_citar():
    pregunta = llamada("q", "preguntar_al_usuario", {"pregunta": "Cual es el largo?"})
    ambiente = {
        **AMBIENTE,
        "largo": "3.1",
        "citas": [{"campo": "largo", "texto": "3,1 m"}] + AMBIENTE["citas"][1:],
    }
    _, r = correr(
        [turno(pregunta), turno(llamada("a", "proponer_ambiente", ambiente)), turno(TERMINAR)],
        responder=lambda _p: "El largo es de 3,1 m",
    )
    assert r.motivo is MotivoFin.TERMINAR and len(r.propuestas) == 1
    assert r.respuestas_de_la_persona == ("El largo es de 3,1 m",)


def test_una_respuesta_con_clave_no_se_envia_ni_se_registra():
    pregunta = llamada("q", "preguntar_al_usuario", {"pregunta": "Su clave?"})
    proveedor, r = correr(
        [turno(pregunta), turno(TERMINAR)], responder=lambda _p: "sk-ant-api03-SECRETA"
    )
    (resultado,) = proveedor.recibidos[1][1][2].resultados
    assert resultado.es_error and "SECRETA" not in resultado.contenido
    assert r.respuestas_de_la_persona == ()


def test_cancelar_la_pregunta_cancela_la_sesion():
    pregunta = llamada("q", "preguntar_al_usuario", {"pregunta": "Largo?"})
    _, r = correr([turno(pregunta), turno(TERMINAR)])  # el responder por defecto devuelve None
    assert r.motivo is MotivoFin.CANCELADO


def test_el_error_del_proveedor_se_informa_sin_reintentar_con_otro():
    _, r = correr([ErrorDeProveedor("sin_conexion", "Sin conexion con el proveedor.")])
    assert r.motivo is MotivoFin.ERROR_DE_PROVEEDOR
    assert r.mensaje == "Sin conexion con el proveedor." and r.turnos == 0


def test_en_la_condicion_a_la_herramienta_de_informe_no_se_ofrece_ni_se_atiende():
    assert "pedir_informe_auditoria" in [h.nombre for h in herramientas_visibles(True)]
    assert "pedir_informe_auditoria" not in [h.nombre for h in herramientas_visibles(False)]
    pedir = llamada("i", "pedir_informe_auditoria", {})
    proveedor, r = correr([turno(pedir), turno(TERMINAR)], informe_permitido=False)
    (resultado,) = proveedor.recibidos[1][1][2].resultados
    assert resultado.es_error


def test_el_informe_hipotetico_incluye_las_pendientes_y_no_lleva_dinero():
    pedir = llamada("i", "pedir_informe_auditoria", {})
    proveedor, _ = correr([turno(AMBIENTE_OK), turno(pedir), turno(TERMINAR)])
    contenido = proveedor.recibidos[2][1][4].resultados[0].contenido
    assert "R8" in contenido and "supuesto por la IA" in contenido
    assert "USD" not in contenido and "impacto" not in contenido


def test_el_mismo_guion_dos_veces_deja_el_mismo_registro_en_el_mismo_orden():
    def sesion():
        motor = create_engine("sqlite://")
        try:
            crear_esquema_ia(motor)
            with motor.begin() as con:
                ejecutar(
                    ProveedorGuionado([turno(AMBIENTE_OK), turno(TERMINAR)]),
                    PEDIDO,
                    Borrador(fecha=FECHA),
                    servicios(registro=RegistroIA(con), proyecto="OF", version_partida="001"),
                )
            with motor.connect() as con:
                return volcado(con)
        finally:
            motor.dispose()

    primero, segundo = sesion(), sesion()
    assert primero == segundo
    assert [t["orden"] for t in primero["ia_turnos"]] == [1, 2]
    assert [(c["herramienta"], c["resultado"]) for c in primero["ia_llamadas"]] == [
        ("proponer_ambiente", "valida"),
        ("terminar", "valida"),
    ]
    assert [(p["propuesta"], p["estado"]) for p in primero["ia_propuestas"]] == [
        ("P1", "pendiente")
    ]
    assert primero["ia_sesiones"][0]["motivo_fin"] == "terminar"


def test_el_anexo_ia_no_lleva_uso_ni_costo():
    motor = create_engine("sqlite://")
    try:
        crear_esquema_ia(motor)
        with motor.begin() as con:
            registro = RegistroIA(con)
            r = ejecutar(
                ProveedorGuionado(
                    [turno(AMBIENTE_OK, uso=Uso(entrada=5, salida=9)), turno(TERMINAR)]
                ),
                PEDIDO,
                Borrador(fecha=FECHA),
                servicios(registro=registro, proyecto="OF", version_partida="001"),
            )
            registro.decidir(r.sesion, "P1", "aceptada", "ana")
            registro.marcar_guardada(r.sesion, "002")
            anexo = anexo_ia(con, "OF", "002")
            assert anexo_ia(con, "OF", "001") is None  # aun no estaba guardada
            assert anexo_ia(con, "OTRO", "009") is None
    finally:
        motor.dispose()
    texto = anexo.decode()
    for prohibido in ("costo", "cache_lectura", "entrada", "salida", '"uso"', "topes"):
        assert prohibido not in texto
    assert '"estado":"aceptada"' in texto and '"decidida_por":"ana"' in texto


def test_una_pregunta_pausa_la_sesion_y_continuar_la_reanuda_con_el_resto_del_turno():
    from asistente.orquestador import ESPERAR, continuar

    pregunta = llamada("q", "preguntar_al_usuario", {"pregunta": "Cual es el largo?"})
    ambiente = {
        **AMBIENTE,
        "largo": "3.1",
        "citas": [{"campo": "largo", "texto": "3,1 m"}] + AMBIENTE["citas"][1:],
    }
    proveedor = ProveedorGuionado(
        [
            turno(pregunta, llamada("a", "proponer_ambiente", ambiente)),  # la 2.a espera su turno
            turno(TERMINAR),
        ]
    )
    pausada = ejecutar(
        proveedor,
        PEDIDO,
        Borrador(fecha=FECHA),
        servicios(responder=lambda _p: ESPERAR),
        Topes(costo=None),
        sesion_n=7,
    )
    assert pausada.motivo is MotivoFin.ESPERANDO_RESPUESTA
    assert pausada.pregunta == "Cual es el largo?" and pausada.propuestas == ()
    final = continuar(pausada, "El largo es de 3,1 m")
    assert final.motivo is MotivoFin.TERMINAR and [p.id for p in final.propuestas] == ["P1"]
    assert final.respuestas_de_la_persona == ("El largo es de 3,1 m",)
    # el modelo vio el resultado de la pregunta y de la propuesta en UN solo mensaje
    resultados = proveedor.recibidos[1][1][2].resultados
    assert [r.llamada_id for r in resultados] == ["q", "a"]


def test_cancelar_o_contestar_con_una_clave_tras_la_pausa():
    from asistente.orquestador import ESPERAR, continuar

    pregunta = llamada("q", "preguntar_al_usuario", {"pregunta": "Su clave?"})

    def pausada():
        proveedor = ProveedorGuionado([turno(pregunta), turno(TERMINAR)])
        resultado = ejecutar(
            proveedor,
            PEDIDO,
            Borrador(fecha=FECHA),
            servicios(responder=lambda _p: ESPERAR),
            Topes(costo=None),
        )
        return proveedor, resultado

    _, r = pausada()
    assert continuar(r, None).motivo is MotivoFin.CANCELADO
    proveedor, r = pausada()
    final = continuar(r, "sk-ant-api03-SECRETA")
    assert final.respuestas_de_la_persona == () and final.motivo is MotivoFin.TERMINAR
    assert "SECRETA" not in proveedor.recibidos[1][1][2].resultados[0].contenido
    with pytest.raises(ValueError):
        continuar(final, "x")  # ya no espera nada


def test_si_el_proveedor_cae_a_mitad_de_la_sesion_se_conserva_lo_ya_validado():
    _, r = correr([turno(AMBIENTE_OK), ErrorDeProveedor("sin_conexion", "Sin conexion.")])
    assert r.motivo is MotivoFin.ERROR_DE_PROVEEDOR and r.turnos == 1
    assert [p.id for p in r.propuestas] == ["P1"] and r.mensaje == "Sin conexion."
