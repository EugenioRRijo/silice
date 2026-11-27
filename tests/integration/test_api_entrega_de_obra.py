"""Lote G5 por la API: `GET` y `PUT /v1/obras/{codigo}/entrega`.

Oráculos escritos a mano con datos ficticios («Torre Norte», Ana, Rita, Admin):
- `GET /v1/obras/{codigo}/entrega` (`LEER_PROYECTO`: arma y revisa, o clave de API) devuelve
  `{proyecto, fecha_entrega, actualizada, actualizada_por}`;
- `PUT /v1/obras/{codigo}/entrega` (`EDITAR_HOJA`: arma, o clave de API) fija o quita (`null`) la
  fecha de entrega al cliente;
- rechaza una fecha en el pasado con 422 y un formato mal formado con 422 sin eco;
- responde 404 si la obra no existe, 401 sin sesión y 403 sin permiso o sin CSRF.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.dependencias import USUARIO_API
from api.main import app
from api.rutas import obras_entrega
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    ORIGEN,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

MOMENTO = datetime(2026, 11, 27, 10, 0, 0)
AJENO = "http://otro.sitio.example"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("entrega_de_obra_api")
    empresa = carpeta / "silice.db"
    preparar_base(empresa)
    return {"instalacion": plantilla_con_cuentas(carpeta), "silice.db": empresa}


@pytest.fixture(autouse=True)
def _entorno(_plantilla: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla["instalacion"])
    casos_dir = config.carpeta_casos()
    casos_dir.mkdir(parents=True, exist_ok=True)
    ruta_empresa = casos_dir / "silice.db"
    ruta_empresa.write_bytes(_plantilla["silice.db"].read_bytes())
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta_empresa.as_posix()}")
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    monkeypatch.setattr(obras_entrega, "ahora", lambda: MOMENTO)
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _crear_obra(ana, ficha: str, nombre: str = "Torre Norte") -> str:
    creada = ana.post(
        "/v1/proyectos",
        json={"nombre": nombre, "moneda": "Bs", "dominio": "civil"},
        headers=protegida(ficha),
    )
    assert creada.status_code == 201, creada.text
    return creada.json()["codigo"]


def test_leer_fijar_y_limpiar_la_fecha_de_entrega() -> None:
    ana, ficha_ana = con_cuenta(app, "ana")
    codigo = _crear_obra(ana, ficha_ana)
    ruta = f"/v1/obras/{codigo}/entrega"

    inicial = ana.get(ruta)
    assert inicial.status_code == 200, inicial.text
    assert inicial.headers["cache-control"] == "no-store"
    assert inicial.json() == {
        "proyecto": codigo,
        "fecha_entrega": None,
        "actualizada": None,
        "actualizada_por": None,
    }

    fijada = ana.put(
        ruta,
        json={"fecha_entrega": "2026-12-15"},
        headers=protegida(ficha_ana),
    )
    assert fijada.status_code == 200, fijada.text
    assert fijada.headers["cache-control"] == "no-store"
    cuerpo = fijada.json()
    assert cuerpo["proyecto"] == codigo
    assert cuerpo["fecha_entrega"] == "2026-12-15"
    assert cuerpo["actualizada"] == MOMENTO.isoformat()
    assert "<ana>" in cuerpo["actualizada_por"]

    # También se puede consultar por el nombre de la obra y con una cuenta que revisa.
    rita, _ = con_cuenta(app, "rita")
    por_nombre = rita.get("/v1/obras/Torre%20Norte/entrega")
    assert por_nombre.status_code == 200, por_nombre.text
    assert por_nombre.json() == cuerpo

    # Limpiar la fecha (null) la deja en None.
    limpia = ana.put(
        ruta,
        json={"fecha_entrega": None},
        headers=protegida(ficha_ana),
    )
    assert limpia.status_code == 200, limpia.text
    assert limpia.json()["fecha_entrega"] is None
    assert ana.get(ruta).json()["fecha_entrega"] is None


def test_fecha_en_el_pasado_o_mal_formada_da_422_sin_eco() -> None:
    ana, ficha_ana = con_cuenta(app, "ana")
    codigo = _crear_obra(ana, ficha_ana)
    ruta = f"/v1/obras/{codigo}/entrega"

    pasada = ana.put(
        ruta,
        json={"fecha_entrega": "2026-11-26"},
        headers=protegida(ficha_ana),
    )
    assert pasada.status_code == 422, pasada.text
    assert pasada.json() == {
        "detalle": "La fecha de entrega al cliente no puede estar en el pasado."
    }

    mal_formada = ana.put(
        ruta,
        json={"fecha_entrega": "no-es-una-fecha-secreta"},
        headers=protegida(ficha_ana),
    )
    assert mal_formada.status_code == 422
    assert "no-es-una-fecha-secreta" not in mal_formada.text
    assert ana.get(ruta).json()["fecha_entrega"] is None


def test_obra_inexistente_da_404() -> None:
    ana, ficha_ana = con_cuenta(app, "ana")
    assert ana.get("/v1/obras/999/entrega").status_code == 404
    respuesta = ana.put(
        "/v1/obras/999/entrega",
        json={"fecha_entrega": "2026-12-15"},
        headers=protegida(ficha_ana),
    )
    assert respuesta.status_code == 404


def test_permisos_csrf_y_clave_de_api() -> None:
    ana, ficha_ana = con_cuenta(app, "ana")
    codigo = _crear_obra(ana, ficha_ana)
    ruta = f"/v1/obras/{codigo}/entrega"

    # Sin sesión ni clave -> 401.
    sin = cliente(app)
    assert sin.get(ruta).status_code == 401
    assert (
        sin.put(ruta, json={"fecha_entrega": "2026-12-15"}, headers={"Origin": ORIGEN}).status_code
        == 401
    )

    # Rita (revisa) lee pero no puede fijar (403).
    rita, ficha_rita = con_cuenta(app, "rita")
    assert rita.get(ruta).status_code == 200
    assert (
        rita.put(
            ruta, json={"fecha_entrega": "2026-12-15"}, headers=protegida(ficha_rita)
        ).status_code
        == 403
    )

    # Sin CSRF o con Origin ajeno -> 403.
    assert (
        ana.put(ruta, json={"fecha_entrega": "2026-12-15"}, headers={"Origin": ORIGEN}).status_code
        == 403
    )
    assert (
        ana.put(
            ruta,
            json={"fecha_entrega": "2026-12-15"},
            headers=protegida(ficha_ana, origen=AJENO),
        ).status_code
        == 403
    )

    # Con clave de API -> 200 y consta como USUARIO_API.
    clave = crear_clave_de_prueba()
    con_clave = cliente(app).put(
        ruta,
        json={"fecha_entrega": "2026-12-20"},
        headers={CABECERA: clave},
    )
    assert con_clave.status_code == 200, con_clave.text
    assert con_clave.json()["fecha_entrega"] == "2026-12-20"
    assert con_clave.json()["actualizada_por"] == USUARIO_API
