"""El manejador de fallos de la base deja la traza en el registro (prueba en vivo 2026-11-18).

Starlette corre un manejador sincrono en el threadpool, fuera del `except` donde nacio la
excepcion: `logger.exception` sin `exc_info` registraba «NoneType: None» y la causa se perdia. Aqui
se llama al manejador igual que alli, fuera de cualquier `except`.
"""

from __future__ import annotations

import logging

import pytest
from sqlalchemy.exc import OperationalError
from starlette.requests import Request

from api.main import MENSAJE_BASE, manejar_error_de_base


def _pedido(ruta: str) -> Request:
    return Request(
        {"type": "http", "method": "GET", "path": ruta, "headers": [], "query_string": b""}
    )


def _fallo() -> OperationalError:
    try:
        raise OperationalError("SELECT secreto FROM tabla_interna", {}, Exception("disco lleno"))
    except OperationalError as error:
        return error


def test_el_registro_trae_la_traza_del_fallo_y_la_respuesta_no(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fallo = _fallo()
    with caplog.at_level(logging.ERROR, logger="silice.api"):
        respuesta = manejar_error_de_base(_pedido("/v1/produccion/calculos"), fallo)

    assert respuesta.status_code == 503
    assert MENSAJE_BASE.encode() in respuesta.body and b"tabla_interna" not in respuesta.body
    (registro,) = [r for r in caplog.records if r.name == "silice.api"]
    assert "/v1/produccion/calculos" in registro.getMessage()
    assert registro.exc_info is not None and registro.exc_info[1] is fallo
    assert "NoneType: None" not in caplog.text
    assert "disco lleno" in caplog.text and "Traceback" in caplog.text
