"""La ficha de la obra por la API: `cliente` y `ubicacion` en `POST` y `GET /v1/proyectos` (MOD-3a).

Oráculos a mano: lo guardado se lee con `sqlite3` directo del archivo del caso; los textos de
ejemplo son ficticios; los roles son los de `tests/fixtures/sesion_web.py`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.main import app
from aplicacion import obras
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

RUTA = "/v1/proyectos"
FORMA = {
    "codigo",
    "nombre",
    "version_vigente",
    "version_codigo",
    "actualizado",
    "cliente",
    "ubicacion",
}
CUERPO = {
    "nombre": "Casa Demo",
    "moneda": "Bs",
    "dominio": "civil",
    "cliente": "Contratista Demo, C.A.",
    "ubicacion": "Maracay",
}


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_ficha_obra")
    caso = carpeta / "silice.db"
    preparar_base(caso)
    return {"instalacion": plantilla_con_cuentas(carpeta), "silice.db": caso}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "silice.db").write_bytes(_plantillas["silice.db"].read_bytes())
    caso_web.olvidar_todo()
    yield carpeta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _filas(consulta: str) -> list[tuple]:
    with closing(sqlite3.connect(config.carpeta_casos() / "silice.db")) as base:
        return base.execute(consulta).fetchall()


def test_crear_con_ficha_la_devuelve_y_la_lista_la_repite() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.post(RUTA, json=CUERPO, headers=protegida(ficha))
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == FORMA
    assert cuerpo["cliente"] == "Contratista Demo, C.A."
    assert cuerpo["ubicacion"] == "Maracay"
    lista = navegador.get(RUTA).json()
    assert [(o["nombre"], o["cliente"], o["ubicacion"]) for o in lista] == [
        ("Casa Demo", "Contratista Demo, C.A.", "Maracay")
    ]
    assert _filas("select cliente, ubicacion from ficha_obra") == [
        ("Contratista Demo, C.A.", "Maracay")
    ]


def test_sin_los_campos_quedan_vacios() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    cuerpo = {"nombre": "Casa Demo", "moneda": "Bs", "dominio": "civil"}
    respuesta = navegador.post(RUTA, json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 201, respuesta.text
    assert (respuesta.json()["cliente"], respuesta.json()["ubicacion"]) == ("", "")
    lista = navegador.get(RUTA).json()
    assert (lista[0]["cliente"], lista[0]["ubicacion"]) == ("", "")


def test_una_obra_sin_fila_de_ficha_lista_vacios() -> None:
    with closing(sqlite3.connect(config.carpeta_casos() / "silice.db")) as base:
        base.execute(
            "INSERT INTO proyecto (id, nombre, descripcion, dominio) VALUES (9, 'Vieja', '', '')"
        )
        base.commit()
    navegador, _ = con_cuenta(app, "ana")
    lista = navegador.get(RUTA).json()
    assert [(o["nombre"], o["cliente"], o["ubicacion"]) for o in lista] == [("Vieja", "", "")]


@pytest.mark.parametrize("campo", ["cliente", "ubicacion"])
def test_mas_de_200_caracteres_es_422_sin_eco(campo: str) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    texto = "Zeta-" + "x" * 196  # 201 caracteres
    assert len(texto) == 201
    respuesta = navegador.post(RUTA, json={**CUERPO, campo: texto}, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert "Zeta-" not in respuesta.text
    assert _filas("select count(*) from proyecto") == [(0,)]


def test_200_caracteres_se_aceptan() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.post(
        RUTA, json={**CUERPO, "cliente": "c" * 200}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["cliente"] == "c" * 200


def test_todo_o_nada_si_falla_guardar_la_ficha() -> None:
    def falla(*_args, **_kwargs) -> None:
        raise RuntimeError("falla simulada")

    navegador, ficha = con_cuenta(app, "ana")
    with pytest.MonkeyPatch.context() as parche:  # solo esta sustitución, no el entorno
        parche.setattr(obras, "guardar_ficha", falla)
        respuesta = navegador.post(RUTA, json=CUERPO, headers=protegida(ficha))
    assert respuesta.status_code == 500
    assert "falla simulada" not in respuesta.text
    assert navegador.get(RUTA).json() == []
    assert _filas("select count(*) from proyecto") == [(0,)]
    assert _filas("select count(*) from ficha_obra") == [(0,)]


def test_un_nombre_repetido_no_deja_ficha_huerfana() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert navegador.post(RUTA, json=CUERPO, headers=protegida(ficha)).status_code == 201
    otra = {**CUERPO, "nombre": "casa demo", "cliente": "Otro, C.A."}
    assert navegador.post(RUTA, json=otra, headers=protegida(ficha)).status_code == 409
    assert _filas("select cliente from ficha_obra") == [("Contratista Demo, C.A.",)]


def test_rita_no_crea_y_no_deja_ficha() -> None:
    navegador, ficha = con_cuenta(app, "rita")
    assert navegador.post(RUTA, json=CUERPO, headers=protegida(ficha)).status_code == 403
    assert _filas("select count(*) from ficha_obra") == [(0,)]
