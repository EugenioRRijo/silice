"""Ayudas para probar carreras entre dos peticiones y el orden de los bloqueos de escritura.

Solo funciones simples (sin `@pytest.fixture`): cada prueba declara sus propias fixtures. Sin
esperas largas: hilos con `threading.Event`.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Engine, event

from seguridad.base import OPCION_INMEDIATA


def dos_a_la_vez(
    monkeypatch: pytest.MonkeyPatch,
    objeto: object,
    nombre: str,
    primera: Callable[[], object],
    segunda: Callable[[], object],
) -> list[object]:
    """Corre `primera` y `segunda` (cada una devuelve una respuesta) en dos hilos y devuelve las
    respuestas en ese orden. `objeto.nombre` es una funcion que el codigo llama DESPUES de leer lo
    que decide y ANTES de escribir: la primera en llegar espera (hasta un segundo) a la segunda. La
    segunda solo arranca cuando la primera ya leyo. Con `BEGIN` diferido la segunda llega al gancho
    sin esperar (las dos leen lo mismo); con `BEGIN IMMEDIATE` la segunda espera el bloqueo ANTES
    de leer, la primera vence su espera de un segundo, escribe y confirma, y la segunda lee ya lo
    nuevo."""
    original = getattr(objeto, nombre)
    llegadas, lock = [], threading.Lock()
    primera_leyo, segunda_leyo = threading.Event(), threading.Event()

    def gancho(*args, **kwargs):
        with lock:
            llegadas.append(1)
            es_la_primera = len(llegadas) == 1
        if es_la_primera:
            primera_leyo.set()
            segunda_leyo.wait(timeout=1)
        else:
            segunda_leyo.set()
        return original(*args, **kwargs)

    monkeypatch.setattr(objeto, nombre, gancho)
    respuestas: dict[int, object] = {}

    def hilo(numero: int, peticion: Callable[[], object]) -> None:
        if numero == 1:
            primera_leyo.wait(timeout=10)
        respuestas[numero] = peticion()

    hilos = [
        threading.Thread(target=hilo, args=(0, primera)),
        threading.Thread(target=hilo, args=(1, segunda)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=30)
    return [respuestas[0], respuestas[1]]


@contextmanager
def begins_de_escritura() -> Iterator[list[str]]:
    """Los `BEGIN IMMEDIATE` que abre cualquier motor, en orden, como el nombre del archivo de la
    base (`instalacion.db`, `apu.db`, ...). Los `BEGIN` diferidos no se cuentan."""
    visto: list[str] = []

    def al_comenzar(conexion) -> None:
        if conexion.get_execution_options().get(OPCION_INMEDIATA, False):
            visto.append((conexion.engine.url.database or "").replace("\\", "/").split("/")[-1])

    event.listen(Engine, "begin", al_comenzar)
    try:
        yield visto
    finally:
        event.remove(Engine, "begin", al_comenzar)
