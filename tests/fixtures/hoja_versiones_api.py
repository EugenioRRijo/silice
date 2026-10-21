"""Ayudas de las pruebas de S2 a S6 de la hoja (T10, 3d-2): lo que comparten la prueba de la API y la
de paridad contra la clasica.

Nada de esto sale del codigo bajo prueba: el volcado y los registros se leen de la base con
consultas propias (sqlite3 y `models.*`), la cadena con `estado_de_la_cadena` y las tasas se
siembran con `registrar_importacion` (el mismo camino que la importacion de UC-17).
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from aplicacion.entrega import estado_de_la_cadena
from core import models
from core.catalog import abrir_sesion, crear_motor
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion


def volcado(ruta: Path) -> dict[str, list[tuple]]:
    """Todas las filas de todas las tablas, para comprobar que NO se escribio nada."""
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


@contextmanager
def base(ruta: Path) -> Iterator:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            yield sesion
    finally:
        motor.dispose()


def registros(ruta: Path, proyecto: str, codigo: str) -> list[tuple]:
    """Los RegistroCambio que dejo la version `codigo`, en orden: (objeto, clave, campo, antes,
    despues, fuente, responsable)."""
    r = models.RegistroCambio
    with base(ruta) as sesion:
        return [
            tuple(f)
            for f in sesion.execute(
                select(
                    r.objeto,
                    r.clave,
                    r.campo,
                    r.valor_anterior,
                    r.valor_nuevo,
                    r.fuente,
                    r.responsable,
                )
                .join(models.Presupuesto, models.Presupuesto.id == r.version_resultante_id)
                .join(models.Proyecto, models.Proyecto.id == models.Presupuesto.proyecto_id)
                .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
                .order_by(r.id)
            )
        ]


def cadena(ruta: Path, proyecto: str):
    with base(ruta) as sesion:
        return estado_de_la_cadena(sesion, proyecto)


def a_la_vez(*peticiones) -> list:
    """Lanza las peticiones juntas (una barrera las suelta a la vez) y devuelve sus respuestas."""
    respuestas: list = [None] * len(peticiones)
    inicio = threading.Barrier(len(peticiones))

    def correr(n: int) -> None:
        inicio.wait()
        respuestas[n] = peticiones[n]()

    hilos = [threading.Thread(target=correr, args=(n,)) for n in range(len(peticiones))]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=120)
        assert not hilo.is_alive()
    return respuestas


def registrar_tasa(
    ruta: Path, fecha: date, valor: str, lado: str = "venta", huella: str = "f" * 64
) -> None:
    """Una tasa del BCV (Bs por USD) con fecha valor `fecha` en la base del caso."""
    with base(ruta) as sesion:
        registrar_importacion(
            sesion,
            definicion_tasa(lado),
            [Observacion(fecha, Decimal(valor))],
            archivo="FUENTE.md",
            huella=huella,
            fuente="https://www.bcv.org.ve/",
            fecha_descarga=fecha,
            responsable="Admin",
            filas_leidas=1,
            filas_rechazadas=0,
        )
        sesion.commit()


def sin_float(valor) -> None:
    """Falla si el JSON (leido con `parse_float=float`) trae un numero decimal."""
    if isinstance(valor, float):
        raise AssertionError(f"float en el JSON: {valor!r}")
    if isinstance(valor, dict):
        for v in valor.values():
            sin_float(v)
    elif isinstance(valor, list):
        for v in valor:
            sin_float(v)
