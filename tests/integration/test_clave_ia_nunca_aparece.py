"""RNF-18 (c): la clave de IA no aparece en ningun destino (S4 §8.3, §10.1; plan 0.9.0, T13).

Una sesion con el adaptador REAL de Claude y el SDK REAL de `anthropic`, cuyo cliente HTTP lleva un
`httpx.MockTransport` que captura la solicitud y responde como la API: ningun byte sale del equipo
y la guardia de red de `tests/conftest.py` sigue activa. La clave centinela se registra con
`ClaveDeIA`, llega al proveedor por el camino del producto (`ProveedorClaude._crear_cliente`) y
despues se busca, literalmente, en: el cuerpo de la solicitud, el archivo de la base del caso (sus
bytes y su volcado SQL), el registro `ia_*`, los registros de la aplicacion (lo capturado sin
filtro y el archivo `silice.log` de `operacion.registro`), el Excel, el anexo `ia.json` y el
paquete `.silice` entero. Control positivo: la clave SI esta en el encabezado `x-api-key` de la
solicitud capturada (prueba que la busqueda la encontraria). La pantalla se vigila en
`tests/unit/test_ui_hoja_asistente.py` y `tests/unit/test_ui_administracion_asistente.py`.
"""

from __future__ import annotations

import functools
import io
import json
import logging
import sqlite3
import zipfile
from contextlib import closing
from datetime import datetime
from decimal import Decimal

import anthropic
import httpx2 as httpx
import pytest
from sqlalchemy import select

from asistente.clave import ClaveDeIA, es_bucle_local
from asistente.orquestador import MotivoFin, Servicios
from asistente.propuestas import EstadoPropuesta
from asistente.proveedores.base import Tarifa
from asistente.proveedores.claude import ProveedorClaude
from asistente.registro import RegistroIA, anexo_ia, crear_esquema_ia, volcado
from asistente.servicio import borrador_resultante, decidir, proponer
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion import registro as registro_app
from tests.fixtures.asistente_base import PROYECTO, VERSION, sesion_en_base
from tests.fixtures.asistente_clave import AlmacenFalso, SecretosFalsos
from tests.fixtures.asistente_pedidos import AMBIENTE, FECHA, PEDIDO, catalogo
from tests.fixtures.hoja_en_base import plantilla_of001
from tests.fixtures.instalacion import instalacion
from ui import entrega, hoja
from ui.hoja import Borrador

CLAVE = "sk-ant-api03-CLAVE-QUE-NO-DEBE-APARECER-9999"


def _mensaje_de_la_api() -> dict:
    return {
        "id": "msg_prueba",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [
            {"type": "tool_use", "id": "a", "name": "proponer_ambiente", "input": AMBIENTE},
            {"type": "tool_use", "id": "t", "name": "terminar", "input": {"notas": ["listo"]}},
        ],
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 40,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
    }


@pytest.fixture
def api_falsa(monkeypatch):
    """El SDK real con un transporte que captura cada solicitud: `anthropic.Anthropic` recibe un
    `http_client` sobre `MockTransport`; `ProveedorClaude` lo construye como en el producto."""
    capturas: list[httpx.Request] = []
    respuestas: list[httpx.Response] = []

    def responder(solicitud: httpx.Request) -> httpx.Response:
        capturas.append(solicitud)
        return respuestas.pop(0) if respuestas else httpx.Response(200, json=_mensaje_de_la_api())

    cliente_http = httpx.Client(transport=httpx.MockTransport(responder))
    monkeypatch.setattr(
        anthropic, "Anthropic", functools.partial(anthropic.Anthropic, http_client=cliente_http)
    )
    yield capturas, respuestas
    cliente_http.close()


def _clave(tmp_path) -> ClaveDeIA:
    clave = ClaveDeIA(
        almacen=AlmacenFalso(),
        secretos=SecretosFalsos(),
        ruta_respaldo=tmp_path / "ia.cifrada",
        es_local=es_bucle_local,
    )
    clave.registrar("EMP", CLAVE, ip_cliente="127.0.0.1")
    return clave


def _version(sesion) -> models.Presupuesto:
    return sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == PROYECTO, models.Presupuesto.codigo == VERSION)
    ).one()


def test_la_clave_no_aparece_en_ningun_destino(tmp_path, caplog, api_falsa):
    capturas, _ = api_falsa
    clave = _clave(tmp_path)
    proveedor = ProveedorClaude(clave.vigente)  # sin cliente: lo crea el SDK, como en el producto
    assert proveedor.disponible().disponible

    base = tmp_path / "caso.db"
    plantilla_of001(base)
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema_ia(motor)
    finally:
        motor.dispose()

    registro_app.configurar(tmp_path / "registros", "DEBUG")  # el archivo real de la aplicacion
    silice = logging.getLogger("silice.asistente")
    with caplog.at_level(logging.DEBUG):  # todo lo que se registre en el proceso, sin filtro
        silice.info("usando la clave %s", clave.vigente)  # un descuido: el archivo la enmascara
        try:
            raise RuntimeError(f"fallo con {clave.vigente}")
        except RuntimeError:
            silice.exception("otro descuido, con traza")  # la traza tambien se enmascara
        numero = sesion_en_base(base, proveedor=proveedor)
        motor = crear_motor(f"sqlite:///{base.as_posix()}")
        try:
            with abrir_sesion(motor) as sesion:
                registrado = json.dumps(volcado(sesion.connection()), default=str)
                anexo = anexo_ia(sesion.connection(), PROYECTO, VERSION)
                with instalacion(tmp_path / "instalacion") as bd:
                    paquete = entrega.entregar(
                        sesion,
                        bd,
                        _version(sesion),
                        usuario="ana",
                        ahora=datetime(2026, 10, 13, 9, 0),
                        version_silice="0.9.0",
                    )
        finally:
            motor.dispose()
        # el Excel de la hoja con lo aceptado: el mismo borrador que la pantalla exportaria
        motor = crear_motor("sqlite://")
        try:
            crear_esquema_ia(motor)
            with motor.begin() as con:
                servicios = Servicios(
                    catalogo=catalogo(),
                    tarifa=Tarifa(Decimal(4), Decimal(20)),
                    registro=RegistroIA(con),
                    auditar=lambda b: hoja.elaborar_borrador(b).elaboracion.informe,
                )
                s = proponer(proveedor, PEDIDO, Borrador(fecha=FECHA), servicios)
                decidir(s, "P1", EstadoPropuesta.ACEPTADA, "ana")
                borrador = borrador_resultante(s)
        finally:
            motor.dispose()
        excel = hoja.excel_de_hoja_en_bytes(hoja.elaborar_borrador(borrador), borrador)
    for manejador in list(logging.getLogger("silice").handlers):  # el archivo se cierra aqui
        manejador.close()
        logging.getLogger("silice").removeHandler(manejador)

    assert numero >= 1 and anexo is not None and len(capturas) == 2
    # control positivo: la clave viajo, y solo en el encabezado de autenticacion
    assert {c.headers["x-api-key"] for c in capturas} == {CLAVE}
    with closing(sqlite3.connect(base)) as con:
        copia_sql = "\n".join(con.iterdump())
    destinos = {
        "cuerpo de la solicitud": b"".join(c.content for c in capturas).decode("utf-8"),
        "otros encabezados": " ".join(
            f"{k}: {v}" for c in capturas for k, v in c.headers.items() if k != "x-api-key"
        ),
        "archivo de la base": base.read_bytes().decode("latin-1"),
        "volcado SQL de la base": copia_sql,
        "registro ia_*": registrado,
        "registros capturados (sin filtro)": caplog.text,
        "silice.log": (tmp_path / "registros" / "silice.log").read_text(encoding="utf-8"),
        "anexo ia.json": anexo.decode("utf-8"),
        "repr de la clave": repr(clave) + repr(proveedor),
    }
    with zipfile.ZipFile(io.BytesIO(excel)) as libro:  # el Excel es un ZIP de XML
        destinos["Excel"] = "\n".join(
            libro.read(n).decode("utf-8", "ignore") for n in libro.namelist()
        )
    with zipfile.ZipFile(io.BytesIO(paquete.datos)) as archivo:
        nombres = archivo.namelist()
        destinos["paquete .silice"] = "\n".join(
            archivo.read(n).decode("utf-8", "ignore") for n in nombres
        )
    assert "anexos/ia.json" in nombres
    for nombre, contenido in destinos.items():
        assert CLAVE not in contenido, f"la clave de IA aparece en: {nombre}"
        assert "CLAVE-QUE-NO-DEBE-APARECER" not in contenido, f"un trozo aparece en: {nombre}"
    assert "[omitido]" in destinos["silice.log"]  # el descuido quedo enmascarado en el archivo


def test_una_clave_rechazada_por_el_proveedor_no_se_filtra_en_el_error(tmp_path, api_falsa):
    _, respuestas = api_falsa
    cuerpo = {
        "type": "error",
        "error": {"type": "authentication_error", "message": "invalid x-api-key"},
    }
    respuestas.append(httpx.Response(401, json=cuerpo))
    clave = _clave(tmp_path)
    proveedor = ProveedorClaude(clave.vigente)
    servicios = Servicios(
        catalogo=catalogo(),
        tarifa=Tarifa(Decimal(4), Decimal(20)),
        auditar=lambda b: hoja.elaborar_borrador(b).elaboracion.informe,
    )
    sesion = proponer(proveedor, PEDIDO, Borrador(fecha=FECHA), servicios)
    assert sesion.resultado.motivo is MotivoFin.ERROR_DE_PROVEEDOR
    assert sesion.resultado.mensaje == "El proveedor rechazo la clave de IA."
    assert CLAVE not in repr(sesion) and sesion.resultado.continuacion is None
