"""`POST /v1/proyectos` (BCP-3; diseño `2026-10-21-bienvenida-casos-proyectos-design.md` §5, §9.3).

Pruebas B19 y B20, la parte J1 de S8 y la propiedad P-13 (crear un proyecto: nombre único sin
distinguir mayúsculas, moneda elegida, responsable humano, en el caso de la ficha).

Oráculos escritos a mano: lo guardado se lee con `sqlite3` directo del archivo del caso (sin
SQLAlchemy ni `core`); los textos de error, con tildes (DV-BCP-3), están copiados del diseño; los
roles de cada cuenta son los de `tests/fixtures/sesion_web.py` (`ana` arma, `rita` revisa, `admin`
administra; `ana` se llama «Ana» y su responsable es «Ana <ana>»).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.sesion_web import MENSAJE_CAMBIAR_CLAVE
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
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
VACIO = "Escriba un nombre para la obra: no puede quedar vacío."


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_proyectos_crear")
    casos = {}
    for nombre in ("silice.db", "Obra Norte.db"):
        casos[nombre] = carpeta / nombre
        preparar_base(casos[nombre])
    return {"instalacion": plantilla_con_cuentas(carpeta), **casos}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in ("silice.db", "Obra Norte.db"):
        (carpeta / nombre).write_bytes(_plantillas[nombre].read_bytes())
    caso_web.olvidar_todo()
    yield carpeta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _crear(navegador: TestClient, ficha: str, cuerpo: dict, **extra):
    return navegador.post(RUTA, json=cuerpo, headers=protegida(ficha), **extra)


def _filas(caso: str, consulta: str) -> list[tuple]:
    with closing(sqlite3.connect(config.carpeta_casos() / caso)) as base:
        return base.execute(consulta).fetchall()


def _nombres(caso: str) -> list[str]:
    return sorted(f[0] for f in _filas(caso, "select nombre from proyecto"))


# --- B19: la ruta -----------------------------------------------------------------------------


def test_crea_con_la_forma_de_la_lista_y_la_moneda_con_responsable_humano() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, {"nombre": "Torre B", "moneda": "Bs"})
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == FORMA
    assert cuerpo["nombre"] == "Torre B"
    assert cuerpo["version_vigente"] is None
    assert cuerpo["version_codigo"] is None
    assert cuerpo["actualizado"] is None
    assert cuerpo["codigo"] == "1"  # el primer proyecto de una base vacía
    # el elemento de GET /v1/proyectos es el mismo
    assert navegador.get(RUTA).json() == [cuerpo]
    assert _filas("silice.db", "select nombre, dominio, descripcion from proyecto") == [
        ("Torre B", "", "")
    ]
    assert _filas("silice.db", "select proyecto_id, moneda, responsable from moneda_proyecto") == [
        (1, "Bs", "Ana <ana>")
    ]


def test_sin_moneda_crea_el_proyecto_sin_declararla() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, {"nombre": "Sin moneda", "moneda": None})
    assert respuesta.status_code == 201, respuesta.text
    assert _nombres("silice.db") == ["Sin moneda"]
    assert _filas("silice.db", "select count(*) from moneda_proyecto") == [(0,)]


def test_dominio_y_descripcion_se_guardan() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    cuerpo = {"nombre": "Nodo", "moneda": "USD", "dominio": "telecom", "descripcion": "Fibra"}
    assert _crear(navegador, ficha, cuerpo).status_code == 201
    assert _filas("silice.db", "select dominio, descripcion from proyecto") == [
        ("telecom", "Fibra")
    ]
    assert _filas("silice.db", "select moneda from moneda_proyecto") == [("USD",)]


def test_el_nombre_se_guarda_sin_espacios_sobrantes() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, {"nombre": "  Torre    B  ", "moneda": "Bs"})
    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "Torre B"
    assert _nombres("silice.db") == ["Torre B"]


@pytest.mark.parametrize("nombre", ["   ", "", "\t \n"])
def test_nombre_vacio_da_422_con_el_texto_y_no_crea(nombre: str) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, {"nombre": nombre, "moneda": "Bs"})
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": VACIO}
    assert _nombres("silice.db") == []


@pytest.mark.parametrize("otro", ["Torre B", "  torre   b ", "TORRE B"])
def test_nombre_repetido_sin_distinguir_mayusculas_da_409(otro: str) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _crear(navegador, ficha, {"nombre": "Torre B", "moneda": "Bs"}).status_code == 201
    respuesta = _crear(navegador, ficha, {"nombre": otro, "moneda": "USD"})
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": "Ya existe una obra llamada «Torre B»: elija otro nombre o abra esa."
    }
    assert _nombres("silice.db") == ["Torre B"]


def test_el_409_nombra_al_proyecto_que_ya_existe() -> None:
    """Ruling: «abra ese» apunta al existente, así que el texto lleva SU nombre (B19)."""
    navegador, ficha = con_cuenta(app, "ana")
    _crear(navegador, ficha, {"nombre": "Torre B", "moneda": "Bs"})
    respuesta = _crear(navegador, ficha, {"nombre": "  torre   b ", "moneda": "Bs"})
    assert respuesta.status_code == 409
    assert "«Torre B»" in respuesta.json()["detalle"]
    assert "torre b" not in respuesta.json()["detalle"]


def test_la_mayuscula_no_ascii_tambien_cuenta_como_repetida() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _crear(navegador, ficha, {"nombre": "Clínica", "moneda": "Bs"}).status_code == 201
    assert _crear(navegador, ficha, {"nombre": "CLÍNICA", "moneda": "Bs"}).status_code == 409


@pytest.mark.parametrize("moneda", ["EUR", "bs", "usd", "Bs "])
def test_moneda_fuera_de_bs_usd_da_422_y_no_crea(moneda: str) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, {"nombre": "Torre C", "moneda": moneda})
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "Elija la moneda: Bs o USD."}
    assert _nombres("silice.db") == []  # todo o nada
    assert _filas("silice.db", "select count(*) from moneda_proyecto") == [(0,)]


@pytest.mark.parametrize("dominio", ["x", "Civil", "telecomunicaciones"])
def test_tipo_de_obra_desconocido_da_422_y_no_crea(dominio: str) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, {"nombre": "Torre C", "moneda": "Bs", "dominio": dominio})
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "El tipo de obra no es uno de los de la lista."}
    assert _nombres("silice.db") == []


@pytest.mark.parametrize("dominio", ["", "civil", "telecom", "industrial", "sistemas"])
def test_los_cinco_tipos_de_obra_validos(dominio: str) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    cuerpo = {"nombre": "Obra", "moneda": "Bs", "dominio": dominio}
    assert _crear(navegador, ficha, cuerpo).status_code == 201
    assert _filas("silice.db", "select dominio from proyecto") == [(dominio,)]


def test_limites_de_longitud_del_cuerpo_sin_eco() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    eco = "SECRETO-NO-DEBE-VOLVER"
    for cuerpo in (
        {"nombre": "a" * 121, "moneda": "Bs"},
        {"nombre": eco, "moneda": "Bs", "descripcion": "d" * 501},
        {"nombre": eco, "moneda": 5},
        {"moneda": "Bs"},
    ):
        respuesta = _crear(navegador, ficha, cuerpo)
        assert respuesta.status_code == 422
        assert eco not in respuesta.text
    assert _crear(navegador, ficha, {"nombre": "a" * 120, "moneda": "Bs"}).status_code == 201
    assert _crear(navegador, ficha, {"nombre": "b", "descripcion": "d" * 500}).status_code == 201


def test_dos_peticiones_simultaneas_con_el_mismo_nombre_dan_201_y_409() -> None:
    uno, ficha_uno = con_cuenta(app, "ana")
    otro, ficha_otro = con_cuenta(app, "ana")
    cuerpos = [
        (uno, ficha_uno, {"nombre": "Torre B", "moneda": "Bs"}),
        (otro, ficha_otro, {"nombre": "torre b", "moneda": "USD"}),
    ]
    with ThreadPoolExecutor(max_workers=2) as piscina:
        codigos = sorted(
            r.status_code for r in piscina.map(lambda c: _crear(c[0], c[1], c[2]), cuerpos)
        )
    assert codigos == [201, 409]
    assert len(_nombres("silice.db")) == 1
    assert _filas("silice.db", "select count(*) from moneda_proyecto") == [(1,)]


def test_con_clave_de_api_el_responsable_es_la_api_y_crea_en_el_caso_del_proceso() -> None:
    respuesta = cliente(app).post(
        RUTA,
        json={"nombre": "Integración", "moneda": "USD"},
        headers={CABECERA: crear_clave_de_prueba()},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert _nombres("silice.db") == ["Integración"]
    assert _filas("silice.db", "select responsable from moneda_proyecto") == [
        ("api (clave de API)",)
    ]


# --- B20: el caso de la ficha ----------------------------------------------------------------


def test_crea_en_el_caso_de_la_ficha_y_no_en_el_del_proceso() -> None:
    ana, ficha = con_cuenta(app, "ana")
    elegido = ana.post(
        "/v1/casos/actual", json={"nombre": "Obra Norte.db"}, headers=protegida(ficha)
    )
    assert elegido.status_code == 200, elegido.text
    assert _crear(ana, ficha, {"nombre": "Torre B", "moneda": "Bs"}).status_code == 201
    assert _nombres("Obra Norte.db") == ["Torre B"]
    assert _nombres("silice.db") == []
    assert [p["nombre"] for p in ana.get(RUTA).json()] == ["Torre B"]
    # otra persona, sin elegir caso, sigue en el del proceso y no ve el proyecto
    rita, _ = con_cuenta(app, "rita")
    assert rita.get(RUTA).json() == []


# --- S8 (parte J1) y P-13 ---------------------------------------------------------------------


def test_sin_sesion_ni_clave_da_401() -> None:
    assert cliente(app).post(RUTA, json={"nombre": "X", "moneda": "Bs"}).status_code == 401


@pytest.mark.parametrize("login", ["rita", "admin"])
def test_sin_editar_hoja_da_403_y_no_crea(login: str) -> None:
    navegador, ficha = con_cuenta(app, login)
    respuesta = _crear(navegador, ficha, {"nombre": "Torre B", "moneda": "Bs"})
    assert respuesta.status_code == 403
    assert respuesta.json()["detalle"] == MENSAJE_PERMISO
    assert _nombres("silice.db") == []


def test_sin_csrf_o_sin_origin_da_403_y_no_crea() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    cuerpo = {"nombre": "Torre B", "moneda": "Bs"}
    sin_csrf = navegador.post(RUTA, json=cuerpo, headers={"Origin": protegida(ficha)["Origin"]})
    assert sin_csrf.status_code == 403
    sin_origen = navegador.post(RUTA, json=cuerpo, headers=protegida(ficha, origen=None))
    assert sin_origen.status_code == 403
    assert _nombres("silice.db") == []


def test_contrasena_temporal_pendiente_da_403() -> None:
    navegador, ficha = con_cuenta(app, "tomas")
    respuesta = _crear(navegador, ficha, {"nombre": "Torre B", "moneda": "Bs"})
    assert respuesta.status_code == 403
    assert respuesta.json()["detalle"] == MENSAJE_CAMBIAR_CLAVE
    assert _nombres("silice.db") == []


def test_p13_el_historico_y_el_get_no_cambian() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    historico = navegador.post("/proyectos", json={"nombre": "Histórico"}, headers=protegida(ficha))
    assert historico.status_code == 201, historico.text
    assert [p["nombre"] for p in navegador.get(RUTA).json()] == ["Histórico"]


def test_el_422_de_forma_habla_de_obra() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, {"moneda": "Bs"})
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": "Indique el nombre de la obra (hasta 120 caracteres), la moneda (Bs o USD), "
        "el tipo de obra y una descripción de hasta 500 caracteres."
    }
