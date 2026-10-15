"""La base de prueba con una sesion del asistente (la que usa el paquete; plan 0.9.0, tarea 16).

Oraculo: el guion de `tests/fixtures/asistente_base.py` (un ambiente y `terminar`) y los literales
de `tests/fixtures/asistente_pedidos.py`, leidos a mano; nunca lo que `anexo_ia` produce de otra
corrida.
"""

from __future__ import annotations

import json

from sqlalchemy import select

from asistente.propuestas import EstadoPropuesta
from asistente.registro import anexo_ia, ia_llamadas, ia_propuestas, ia_sesiones, ia_turnos
from core.catalog import abrir_sesion, crear_motor
from tests.fixtures.asistente_base import PROYECTO, QUIEN, VERSION, plantilla_s4
from tests.fixtures.asistente_pedidos import AMBIENTE, PEDIDO


def _leer(base):
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sesiones = sesion.execute(
                select(
                    ia_sesiones.c.proyecto,
                    ia_sesiones.c.version_partida,
                    ia_sesiones.c.version_guardada,
                    ia_sesiones.c.proveedor,
                    ia_sesiones.c.motivo_fin,
                )
            ).all()
            propuestas = sesion.execute(
                select(
                    ia_propuestas.c.propuesta, ia_propuestas.c.estado, ia_propuestas.c.decidida_por
                )
            ).all()
            llamadas = sesion.execute(
                select(ia_llamadas.c.herramienta, ia_llamadas.c.resultado).order_by(
                    ia_llamadas.c.id
                )
            ).all()
            turnos = sesion.execute(select(ia_turnos.c.entrada, ia_turnos.c.salida)).all()
            anexo = anexo_ia(sesion.connection(), PROYECTO, VERSION)
    finally:
        motor.dispose()
    return sesiones, propuestas, llamadas, turnos, anexo


def test_la_base_deja_una_sesion_aceptada_y_guardada_en_la_version_001(tmp_path):
    base = plantilla_s4(tmp_path / "s4.db")
    sesiones, propuestas, llamadas, turnos, anexo = _leer(base)
    assert sesiones == [(PROYECTO, "001", "001", "claude", "terminar")]
    assert propuestas == [("P1", "aceptada", QUIEN)]
    assert llamadas == [("proponer_ambiente", "valida"), ("terminar", "valida")]
    assert turnos == [(10, 5)]
    documento = json.loads(anexo)
    assert documento["formato"] == "silice-ia" and documento["version_formato"] == 1
    (sesion,) = documento["sesiones"]
    assert sesion["pedido"] == PEDIDO and sesion["version_guardada"] == "001"
    assert [c["herramienta"] for c in sesion["llamadas"]] == ["proponer_ambiente", "terminar"]
    (propuesta,) = sesion["propuestas"]
    assert propuesta["decidida_por"] == QUIEN and propuesta["estado"] == "aceptada"
    # las citas viajan como pares [campo, texto] (la forma de `Propuesta.citas`)
    assert propuesta["citas"] == [[c["campo"], c["texto"]] for c in AMBIENTE["citas"]]


def test_con_la_propuesta_rechazada_no_hay_anexo(tmp_path):
    base = plantilla_s4(tmp_path / "s4.db", estado=EstadoPropuesta.RECHAZADA)
    _, propuestas, _, _, anexo = _leer(base)
    assert propuestas == [("P1", "rechazada", QUIEN)]
    assert anexo is None  # el anexo solo trae sesiones con algo aceptado o editado
