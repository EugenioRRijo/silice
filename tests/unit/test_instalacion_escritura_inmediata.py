"""La sesion de escritura de `instalacion.db` toma el bloqueo de escritura AL EMPEZAR.

Con `BEGIN` diferido dos peticiones leen el mismo estado (el ultimo conteo, un contador) y la
segunda pierde al escribir (`database is locked` tarde, sobre una lectura vieja). Con
`BEGIN IMMEDIATE` la segunda espera antes de leer y ve lo que confirmo la primera. Sin esperas
largas: hilos con `threading.Event`. Cada base vive en `tmp_path`.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from seguridad import base as modulo_base
from seguridad.base import abrir_sesion, abrir_sesion_de_escritura, crear_motor


def _motor(tmp_path: Path):
    motor = crear_motor(tmp_path / "instalacion.db")
    with motor.begin() as conexion:
        conexion.exec_driver_sql("CREATE TABLE contador (n INTEGER NOT NULL)")
        conexion.exec_driver_sql("INSERT INTO contador VALUES (0)")
    return motor


def test_la_segunda_escritura_falla_al_empezar_no_al_confirmar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(modulo_base, "ESPERA_OCUPADA_MS", 50)
    motor = _motor(tmp_path)
    primera, segunda = abrir_sesion_de_escritura(motor), abrir_sesion_de_escritura(motor)
    try:
        primera.execute(text("SELECT n FROM contador")).scalar_one()
        with pytest.raises(OperationalError, match="database is locked"):
            segunda.execute(text("SELECT n FROM contador")).scalar_one()
    finally:
        segunda.close()
        primera.close()
        motor.dispose()


def test_las_sesiones_de_lectura_siguen_diferidas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(modulo_base, "ESPERA_OCUPADA_MS", 50)
    motor = _motor(tmp_path)
    escritora, lectora = abrir_sesion_de_escritura(motor), abrir_sesion(motor)
    try:
        escritora.execute(text("SELECT n FROM contador")).scalar_one()
        assert lectora.execute(text("SELECT n FROM contador")).scalar_one() == 0  # WAL: no espera
    finally:
        lectora.close()
        escritora.close()
        motor.dispose()


def test_dos_escrituras_leen_y_suman_sin_perder_ninguna(tmp_path: Path) -> None:
    """La primera lee y espera a que la segunda lea; con `BEGIN` diferido la segunda lee de
    inmediato el 0 viejo y su escritura falla; con `BEGIN IMMEDIATE` la segunda espera, la
    primera vence su espera de un segundo, escribe y confirma, y la segunda lee 1 y escribe 2."""
    motor = _motor(tmp_path)
    segunda_leyo, errores = threading.Event(), []

    def sumar(sesion) -> int:
        n = sesion.execute(text("SELECT n FROM contador")).scalar_one()
        return n

    def segunda() -> None:
        try:
            with abrir_sesion_de_escritura(motor) as sesion:
                n = sumar(sesion)
                segunda_leyo.set()
                sesion.execute(text("UPDATE contador SET n = :n"), {"n": n + 1})
                sesion.commit()
        except OperationalError as error:
            errores.append(error)

    with abrir_sesion_de_escritura(motor) as primera:
        n = sumar(primera)
        hilo = threading.Thread(target=segunda)
        hilo.start()
        segunda_leyo.wait(timeout=1)  # diferida: ya leyo; inmediata: sigue esperando el bloqueo
        primera.execute(text("UPDATE contador SET n = :n"), {"n": n + 1})
        primera.commit()
    hilo.join(timeout=10)
    try:
        assert errores == []
        with abrir_sesion(motor) as lectora:
            assert lectora.execute(text("SELECT n FROM contador")).scalar_one() == 2
    finally:
        motor.dispose()
