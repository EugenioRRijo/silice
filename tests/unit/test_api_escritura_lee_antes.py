"""Las rutas de A.8 con archivo subido lo leen antes de tomar el bloqueo de escritura (DS-32).

Con `SesionDeEscrituraDep` la primera consulta abre `BEGIN IMMEDIATE`. Si la ruta consulta el caso
antes de leer lo subido (hasta 20 MiB), quien guarda en el mismo caso espera todo ese rato. Cada
prueba envuelve el paso que lee el archivo y, en ese momento, intenta tomar el bloqueo desde otra
conexion sin esperar (`timeout=0`): tiene que poder. Es la prueba de
`tests/unit/test_api_control.py::test_importar_lee_el_libro_antes_de_tomar_el_bloqueo_de_escritura`
para las demas rutas. Casos construidos a mano; el archivo no tiene que ser valido: basta con que
la ruta llegue a leerlo.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.main import app
from api.rutas import listas, precios_empresa, revision, vial
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

CSV = b"tipo,descripcion,unidad,precio\nmaterial,Cemento de prueba,saco,10.00\n"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("lee_antes"))


@pytest.fixture(autouse=True)
def _caso(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


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


def _mirar(monkeypatch, modulo, nombre: str, caso: Path) -> list[bool]:
    """Envuelve `modulo.nombre` (sincrona o asincrona) y anota si el bloqueo estaba libre."""
    import inspect

    de_verdad = getattr(modulo, nombre)
    libre: list[bool] = []
    if inspect.iscoroutinefunction(de_verdad):

        async def envuelta(*args, **kwargs):
            libre.append(_bloqueo_libre(caso))
            return await de_verdad(*args, **kwargs)

    else:

        def envuelta(*args, **kwargs):
            libre.append(_bloqueo_libre(caso))
            return de_verdad(*args, **kwargs)

    monkeypatch.setattr(modulo, nombre, envuelta)
    return libre


def _comprobar(respuesta, libre: list[bool]) -> None:
    assert respuesta.status_code < 500, respuesta.text
    assert libre == [True], "la ruta tenia tomado el bloqueo de escritura mientras leia"


def test_cargar_una_lista_lee_el_archivo_antes_del_bloqueo(_caso: Path, monkeypatch) -> None:
    libre = _mirar(monkeypatch, listas, "comprobar_libro_legible", _caso)
    navegador, ficha = con_cuenta(app, "ana")

    respuesta = navegador.post(
        "/listas-precios",
        files={"archivo": ("precios.csv", CSV, "text/csv")},
        data={"nombre": "Lista de prueba", "moneda": "Bs", "fecha_vigencia": "2026-11-01"},
        headers=protegida(ficha),
    )

    _comprobar(respuesta, libre)


def test_crear_la_lista_de_empresa_lee_el_archivo_antes_del_bloqueo(
    _caso: Path, monkeypatch
) -> None:
    libre = _mirar(monkeypatch, precios_empresa, "comprobar_libro_legible", _caso)
    navegador, ficha = con_cuenta(app, "admin")

    respuesta = navegador.post(
        "/v1/precios-empresa/listas",
        files={"archivo": ("precios.csv", CSV, "text/csv")},
        data={"base_id": "1", "fecha": "2026-11-01", "moneda": "Bs", "empresa": "Empresa X"},
        headers=protegida(ficha),
    )

    _comprobar(respuesta, libre)


def test_importar_tramos_lee_el_archivo_antes_del_bloqueo(_caso: Path, monkeypatch) -> None:
    libre = _mirar(monkeypatch, vial, "_leer_archivo", _caso)
    navegador, ficha = con_cuenta(app, "ana")

    respuesta = navegador.post(
        "/v1/vial/tramos/importar",
        params={"proyecto": "Obra de prueba", "version": "V1"},
        files={"archivo": ("tramos.csv", b"desde,hasta\n0,100\n", "text/csv")},
        headers=protegida(ficha),
    )

    _comprobar(respuesta, libre)


def test_dictaminar_lee_el_paquete_antes_del_bloqueo(_caso: Path, monkeypatch) -> None:
    libre = _mirar(monkeypatch, revision, "_leer", _caso)
    navegador, ficha = con_cuenta(app, "rita")

    respuesta = navegador.post(
        "/v1/revision/dictamen",
        files={"paquete": ("entrega.silice", b"no es un paquete", "application/octet-stream")},
        data={"resultado": "conforme"},
        headers=protegida(ficha),
    )

    _comprobar(respuesta, libre)
