"""`GET /v1/obras/todas`: las obras de todas las carpetas (rediseño del marco, Tarea 3; spec §8 ter).

Carpetas ficticias en temporal: la de la empresa (`silice.db`, la del proceso) con «Edificio
Central»; «Carpeta Norte» con «Galpón» y «Clínica»; «Carpeta Sur» con «Vialidad». Oráculos a mano:
el orden (empresa primero, luego carpetas por nombre y obras por nombre sin distinguir
mayúsculas) y el nombre que acepta `POST /v1/casos/actual` (`Carpeta Norte.db`).

Clave de API: como en las demás rutas de `obras` y en `GET /v1/casos`, la clave ve el caso del
proceso (no elige carpeta: `POST /v1/casos/actual` le da 409), así que lista solo la carpeta de la
empresa. Sin `CAMBIAR_CASO` (revisa) solo se ve la carpeta abierta en la sesión: nunca una obra
que al abrirla diera 403 (foco de revisión 1).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.main import app
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import sesiones
from tests.fixtures.carpetas_trabajo import arbol
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)

NORTE, SUR, EMPRESA = "Carpeta Norte.db", "Carpeta Sur.db", "silice.db"
OBRAS = {
    EMPRESA: ["Edificio Central"],
    NORTE: ["Galpón", "Clínica"],
    SUR: ["Vialidad"],
}
TITULO_EMPRESA = "Carpeta de la empresa"


def _obra(carpeta: str | None, titulo: str, obra: str) -> dict:
    return {"carpeta": carpeta, "carpeta_titulo": titulo, "obra": obra}


EMPRESA_1 = _obra(None, TITULO_EMPRESA, "Edificio Central")
CLINICA = _obra(NORTE, NORTE, "Clínica")
GALPON = _obra(NORTE, NORTE, "Galpón")
VIALIDAD = _obra(SUR, SUR, "Vialidad")


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_obras_todas")
    plantillas = {"instalacion": plantilla_con_cuentas(carpeta)}
    for nombre, obras in OBRAS.items():
        ruta = carpeta / nombre
        preparar_base(ruta)
        with closing(sqlite3.connect(ruta)) as conexion:
            for n, obra in enumerate(obras, 1):
                conexion.execute(
                    "INSERT INTO proyecto (id, nombre, descripcion, dominio) VALUES (?, ?, '', '')",
                    (n, obra),
                )
            conexion.commit()
            conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        plantillas[nombre] = ruta
    return plantillas


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in OBRAS:
        (carpeta / nombre).write_bytes(_plantillas[nombre].read_bytes())
    caso_web.olvidar_todo()
    yield carpeta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _abrir(ficha: str, nombre: str) -> None:
    """Deja la carpeta abierta en la ficha sin pasar por la ruta (que exige `CAMBIAR_CASO`)."""
    caso_web.fijar(sesiones.huella_de(ficha), config.carpeta_casos() / nombre)


def _filas(cuerpo: dict) -> list[dict]:
    return [
        {k: fila[k] for k in ("carpeta", "carpeta_titulo", "obra")} for fila in cuerpo["obras"]
    ]


def test_lista_obras_de_todas_las_carpetas() -> None:
    navegador, _ = con_cuenta(app, "ana")  # arma: tiene CAMBIAR_CASO
    respuesta = navegador.get("/v1/obras/todas")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert _filas(cuerpo) == [EMPRESA_1, CLINICA, GALPON, VIALIDAD]
    assert cuerpo["carpeta_actual"] is None  # la sesión trabaja en la carpeta de la empresa
    assert set(cuerpo["obras"][0]) == {
        "carpeta",
        "carpeta_titulo",
        "obra_id",
        "obra",
        "version_codigo",
    }
    assert [f["obra_id"] for f in cuerpo["obras"]] == [1, 2, 1, 1]  # Clínica es la 2.ª de Norte
    assert all(f["version_codigo"] is None for f in cuerpo["obras"])  # ninguna tiene versión
    assert respuesta.headers["cache-control"] == "no-store"


def test_la_carpeta_actual_es_la_abierta_en_la_sesion() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    _abrir(ficha, SUR)
    assert navegador.get("/v1/obras/todas").json()["carpeta_actual"] == SUR


def test_sin_cambiar_caso_solo_la_carpeta_abierta() -> None:
    navegador, ficha = con_cuenta(app, "rita")  # revisa: LEER sí, CAMBIAR_CASO no
    _abrir(ficha, SUR)
    cuerpo = navegador.get("/v1/obras/todas").json()
    assert _filas(cuerpo) == [VIALIDAD]
    assert cuerpo["carpeta_actual"] == SUR


def test_sin_cambiar_caso_y_sin_carpeta_abierta_solo_la_de_la_empresa() -> None:
    navegador, _ = con_cuenta(app, "rita")
    assert _filas(navegador.get("/v1/obras/todas").json()) == [EMPRESA_1]


def test_con_la_clave_solo_la_carpeta_del_proceso() -> None:
    respuesta = cliente(app).get("/v1/obras/todas", headers={CABECERA: crear_clave_de_prueba()})
    assert respuesta.status_code == 200, respuesta.text
    assert _filas(respuesta.json()) == [EMPRESA_1]


def test_el_administrador_no_tiene_leer() -> None:
    navegador, _ = con_cuenta(app, "admin")
    assert navegador.get("/v1/obras/todas").status_code == 403


@pytest.mark.parametrize(
    "contenido",
    [b"esto no es SQLite, es texto " * 40, b""],
    ids=["texto", "vacio"],
)
def test_carpeta_ilegible_se_omite(_entorno: Path, contenido: bytes) -> None:
    (_entorno / "Carpeta Rota.db").write_bytes(contenido)
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.get("/v1/obras/todas")
    assert respuesta.status_code == 200, respuesta.text
    assert _filas(respuesta.json()) == [EMPRESA_1, CLINICA, GALPON, VIALIDAD]


def test_no_escribe(_entorno: Path) -> None:
    antes = arbol(_entorno)
    fechas = {p.name: p.stat().st_mtime_ns for p in _entorno.glob("*.db")}
    navegador, _ = con_cuenta(app, "ana")
    assert navegador.get("/v1/obras/todas").status_code == 200
    assert arbol(_entorno) == antes  # ni -wal ni -shm nuevos, ni cambio de tamaño
    assert {p.name: p.stat().st_mtime_ns for p in _entorno.glob("*.db")} == fechas


def test_sin_sesion_401() -> None:
    respuesta = cliente(app).get("/v1/obras/todas")
    assert respuesta.status_code == 401
    assert "detalle" in respuesta.json()
