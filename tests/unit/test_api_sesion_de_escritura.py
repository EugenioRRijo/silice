"""La sesion de escritura se cierra antes de enviar la respuesta (tarea A.9, DS-51 y DS-56).

`SesionDeEscrituraDep` abre `BEGIN IMMEDIATE` en la primera consulta. Con el alcance por omision
de FastAPI la salida de la dependencia (cerrar la sesion) corre DESPUES de enviar la respuesta:
una lectura tras el `commit` (las rutas que releen lo guardado para responder) reabre la
transaccion inmediata y el bloqueo de escritura dura hasta que el cliente recibe la respuesta.
Con `scope="function"` la sesion se cierra al volver la ruta, ya serializada la respuesta y antes
de enviarla. El oraculo es determinista: cuando sale `http.response.start`, otra conexion toma el
bloqueo sin esperar (`timeout=0`).

Una app minima con la dependencia de verdad (sin sustituirla) sobre un caso de `tmp_path`; los
datos son construidos (NORMAS §1).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from api import dependencias
from api.dependencias import SesionDeEscrituraDep
from core import models
from core.budget.persistencia import crear_proyecto


def _bloqueo_libre(caso: Path) -> bool:
    otra = sqlite3.connect(caso, timeout=0)
    try:
        otra.execute("BEGIN IMMEDIATE")
        otra.rollback()
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        otra.close()


@pytest.fixture
def caso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    ruta = tmp_path / "caso.db"
    monkeypatch.setenv(dependencias.VARIABLE_BASE, dependencias.url_de_ruta(ruta))
    dependencias.cerrar_motores()
    yield ruta
    dependencias.cerrar_motores()


def _app() -> FastAPI:
    app = FastAPI()

    @app.post("/guarda-y-relee")
    def guarda_y_relee(sesion: SesionDeEscrituraDep) -> dict[str, object]:
        """Como las rutas que releen lo guardado para responder (`vial._respuesta`, ...)."""
        proyecto = crear_proyecto(sesion, "Obra ficticia A.9")
        sesion.commit()
        nombre_leido = proyecto.nombre  # con `expire_on_commit` esto abriria otra transaccion
        tras_leer = sesion.in_transaction()
        contadas = len(sesion.scalars(select(models.Proyecto.id)).all())  # una consulta nueva
        return {"nombre": nombre_leido, "tras_leer": tras_leer, "proyectos": contadas}

    return app


def _con_el_envio(app: FastAPI, caso: Path, libre: list[bool]):
    """La app, anotando si el bloqueo estaba libre cuando sale la cabecera de la respuesta."""

    async def envuelta(scope, receive, send):
        async def enviar(mensaje):
            if mensaje["type"] == "http.response.start":
                libre.append(_bloqueo_libre(caso))
            await send(mensaje)

        await app(scope, receive, enviar)

    return envuelta


def test_la_sesion_de_escritura_esta_cerrada_al_enviar_la_respuesta(caso: Path) -> None:
    libre: list[bool] = []
    with TestClient(_con_el_envio(_app(), caso, libre)) as navegador:
        r = navegador.post("/guarda-y-relee")
    assert r.status_code == 200, r.text
    assert r.json()["proyectos"] == 1
    assert libre == [True], "el bloqueo de escritura seguia tomado al enviar la respuesta"


def test_leer_lo_confirmado_no_abre_otra_transaccion(caso: Path) -> None:
    """`expire_on_commit=False`: leer un atributo de lo guardado no reabre `BEGIN IMMEDIATE`."""
    with TestClient(_app()) as navegador:
        r = navegador.post("/guarda-y-relee")
    assert r.status_code == 200, r.text
    assert r.json()["nombre"] == "Obra ficticia A.9"
    assert r.json()["tras_leer"] is False


def test_la_guardia_ve_el_bloqueo_tomado(caso: Path) -> None:
    """No pasa en vacio: con una transaccion inmediata abierta, el oraculo dice que no."""
    dependencias.obtener_motor(dependencias.url_de_ruta(caso))  # prepara el caso
    tomada = sqlite3.connect(caso)
    try:
        tomada.execute("BEGIN IMMEDIATE")
        assert _bloqueo_libre(caso) is False
    finally:
        tomada.rollback()
        tomada.close()
