"""La Hoja en solo lectura para quien revisa (rediseño del front, F4, Tarea 2b).

Eugenio decidió el 2026-10-31 que el rol «revisa» vea Presupuesto, Archivos y planos y Versiones
en solo lectura. Las lecturas de `/v1/hoja` (y `GET /v1/aprobaciones?proyecto=`, que lee
Versiones) pasan de `EDITAR_HOJA` a `LEER_PROYECTO`, que ya tienen arma y revisa; todo lo que
escribe sigue en `EDITAR_HOJA`. Quien revisa abre su propio borrador (vive en memoria, es de su
ficha) para ver las vistas calculadas, pero no lo cambia, no guarda y no escribe en la base.

Abrir una versión sin instantánea la escribe (UC-15e: composiciones, plan y un registro de
cambio a nombre de quien abre). Eso es escribir en la base del caso, así que quien revisa no
puede provocarlo: recibe un 409 y la base queda igual byte a byte; cuando quien arma la abre una
vez, quien revisa ya puede verla.

Oráculos a mano: los roles de cada cuenta (`tests.fixtures.sesion_web.CUENTAS`), los textos de
error escritos aquí y el volcado de la base con `sqlite3` directo (no con el código probado).
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.hoja_en_base import NOMBRE_OF001, borrar_instantanea, plantilla_of001
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

VERSION = "001"
FALTA = (
    "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). "
    "Lo que no guardó se perdió: abra la versión otra vez."
)
SIN_PREPARAR = (
    "Esta versión todavía no se puede ver en solo lectura: quien arma el presupuesto tiene que "
    "abrirla una vez para prepararla."
)
VISTAS = ("espacio", "presupuesto", "apu", "plan", "equilibrio", "parametros", "auditoria")


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("hoja_lectura_revisa")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
    }


@pytest.fixture(autouse=True)
def _caso(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalación con cuentas y la obra ficticia OF-001 (versión 001 guardada) como caso."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["of001"], ruta)
    preparar_base(ruta)  # la primera petición la migraría; lo que se compara es lo que escribe
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def _abrir(navegador: TestClient, ficha: str):
    return navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": VERSION},
        headers=protegida(ficha),
    )


def _rev(navegador: TestClient, id_: str) -> int:
    respuesta = navegador.get(f"/v1/hoja/borradores/{id_}")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["resumen"]["rev"]


def test_revisa_lee_las_versiones_y_la_trazabilidad() -> None:
    rita, _ = con_cuenta(app, "rita")
    obra = {"proyecto": NOMBRE_OF001}
    de_la_version = {**obra, "version": VERSION}
    respuestas = {
        "versiones": rita.get("/v1/hoja/versiones", params=obra),
        "trazabilidad": rita.get("/v1/hoja/trazabilidad", params=de_la_version),
        "cadena": rita.get("/v1/hoja/cadena", params=obra),
        "precios": rita.get("/v1/hoja/precios", params=de_la_version),
        "atipicos": rita.get("/v1/hoja/precios/atipicos", params=de_la_version),
        "antes y después": rita.get("/v1/hoja/antes-y-despues", params=obra),
    }
    assert {nombre: r.status_code for nombre, r in respuestas.items()} == {
        nombre: 200 for nombre in respuestas
    }
    assert [v["codigo"] for v in respuestas["versiones"].json()["versiones"]] == [VERSION]
    assert respuestas["cadena"].json()["integra"] is True
    assert all(r.headers["cache-control"] == "no-store" for r in respuestas.values())


def test_revisa_abre_su_borrador_y_ve_las_vistas() -> None:
    rita, ficha = con_cuenta(app, "rita")
    abierto = _abrir(rita, ficha)
    assert abierto.status_code == 201, abierto.text
    id_ = abierto.json()["id"]
    assert abierto.json()["instantanea"] == {"creadas": 0, "mensaje": None}
    vistas = {v: rita.get(f"/v1/hoja/borradores/{id_}/vistas/{v}").status_code for v in VISTAS}
    assert vistas == dict.fromkeys(VISTAS, 200)
    otras = {
        "borrador": rita.get(f"/v1/hoja/borradores/{id_}"),
        "cambios": rita.get(f"/v1/hoja/borradores/{id_}/cambios"),
        "insumos": rita.get(f"/v1/hoja/borradores/{id_}/insumos", params={"tipo": "material"}),
        "excel": rita.get(f"/v1/hoja/borradores/{id_}/excel"),
        "retomar": rita.get("/v1/hoja/borradores"),
    }
    assert {nombre: r.status_code for nombre, r in otras.items()} == dict.fromkeys(otras, 200)
    assert [b["id"] for b in otras["retomar"].json()["borradores"]] == [id_]
    cerrado = rita.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha))
    assert cerrado.status_code == 204
    assert rita.get(f"/v1/hoja/borradores/{id_}").status_code == 404


def _escrituras(id_: str) -> list[tuple[str, str, dict]]:
    """Cada ruta de `/v1/hoja` que cambia el borrador o la base, con un cuerpo de su forma."""
    borrador = f"/v1/hoja/borradores/{id_}"
    apu = f"{borrador}/apu/AF-LLAVE"
    version = {"proyecto": NOMBRE_OF001, "version": VERSION}
    return [
        ("PUT", f"{borrador}/cantidades", {"rev": 0, "filas": []}),
        ("PUT", f"{borrador}/espacio", {"rev": 0}),
        ("PUT", f"{borrador}/parametros", {"rev": 0}),
        ("PUT", f"{borrador}/plan", {"rev": 0}),
        ("POST", f"{borrador}/plan/secuencial", {"rev": 0}),
        ("POST", f"{borrador}/plan/rendimientos", {"rev": 0}),
        ("POST", f"{borrador}/partidas", {"rev": 0, "codigo": "AF-LLAVE", "cantidad": "1"}),
        ("POST", f"{borrador}/partidas/quitar", {"rev": 0, "clave": "x"}),
        ("PUT", apu, {"rev": 0}),
        ("POST", f"{apu}/insumo", {"rev": 0, "tipo": "material", "indice": 0, "insumo": "x"}),
        ("POST", f"{apu}/lineas", {"rev": 0, "tipo": "material"}),
        ("POST", f"{apu}/lineas/quitar", {"rev": 0, "tipo": "material", "indice": 0}),
        ("POST", f"{borrador}/guardar", {"rev": 0, "fuente": "revisión"}),
        ("POST", f"{borrador}/plano", {}),
        ("POST", f"{borrador}/plano/unidad", {}),
        ("POST", f"{borrador}/plano/alturas", {}),
        ("POST", f"{borrador}/plano/circuitos", {}),
        ("POST", f"{borrador}/plano/fusionar", {}),
        ("DELETE", f"{borrador}/plano", {}),
        ("POST", "/v1/hoja/llevar", {"borrador": id_, "rev": 0}),
        ("POST", "/v1/hoja/versiones/restaurar", {**version, "fuente": "revisión"}),
        ("POST", "/v1/hoja/versiones/cotizar", version),
        ("POST", "/v1/hoja/versiones/retirar-cotizacion", version),
        ("POST", "/v1/hoja/versiones/convertir", version),
    ]


def test_revisa_no_escribe(_caso: Path) -> None:
    rita, ficha = con_cuenta(app, "rita")
    abierto = _abrir(rita, ficha)
    assert abierto.status_code == 201, abierto.text
    id_ = abierto.json()["id"]
    antes = _volcado(_caso)
    negadas = {}
    for metodo, ruta, cuerpo in _escrituras(id_):
        respuesta = rita.request(metodo, ruta, json=cuerpo, headers=protegida(ficha))
        negadas[(metodo, ruta)] = (respuesta.status_code, respuesta.json())
    esperado = (403, {"detalle": MENSAJE_PERMISO})
    assert {par: r for par, r in negadas.items() if r != esperado} == {}
    assert _rev(rita, id_) == 0
    assert rita.get(f"/v1/hoja/borradores/{id_}/cambios").json()["cambios"] == []
    assert _volcado(_caso) == antes


def test_revisa_no_crea_la_instantanea_al_abrir(_caso: Path) -> None:
    """UC-15e escribe en la base: quien revisa no la provoca; quien arma, sí, y luego se ve."""
    motor = crear_motor(f"sqlite:///{_caso.as_posix()}")
    with abrir_sesion(motor) as sesion:
        borrar_instantanea(sesion, NOMBRE_OF001)
    motor.dispose()
    dependencias.cerrar_motores()
    antes = _volcado(_caso)
    rita, ficha_rita = con_cuenta(app, "rita")
    negado = _abrir(rita, ficha_rita)
    assert (negado.status_code, negado.json()) == (409, {"detalle": SIN_PREPARAR})
    assert negado.headers["cache-control"] == "no-store"
    assert _volcado(_caso) == antes
    assert rita.get("/v1/hoja/borradores").json()["borradores"] == []
    ana, ficha_ana = con_cuenta(app, "ana")
    preparado = _abrir(ana, ficha_ana)
    assert preparado.status_code == 201 and preparado.json()["instantanea"]["creadas"] > 0
    despues = _abrir(rita, ficha_rita)
    assert despues.status_code == 201, despues.text
    assert despues.json()["instantanea"] == {"creadas": 0, "mensaje": None}


def test_el_administrador_no_ve_la_hoja() -> None:
    admin, ficha = con_cuenta(app, "admin")
    respuestas = [
        admin.get("/v1/hoja/versiones", params={"proyecto": NOMBRE_OF001}),
        _abrir(admin, ficha),
        admin.get("/v1/hoja/borradores"),
        admin.get("/v1/aprobaciones", params={"proyecto": NOMBRE_OF001}),
    ]
    assert [(r.status_code, r.json()) for r in respuestas] == [
        (403, {"detalle": MENSAJE_PERMISO})
    ] * len(respuestas)


def test_revisa_no_ve_el_borrador_de_otra_ficha() -> None:
    ana, ficha_ana = con_cuenta(app, "ana")
    id_ = _abrir(ana, ficha_ana).json()["id"]
    rita, ficha_rita = con_cuenta(app, "rita")
    ajenos = [
        rita.get(f"/v1/hoja/borradores/{id_}"),
        rita.get(f"/v1/hoja/borradores/{id_}/vistas/presupuesto"),
        rita.get(f"/v1/hoja/borradores/{id_}/cambios"),
        rita.get(f"/v1/hoja/borradores/{id_}/excel"),
    ]
    assert [(r.status_code, r.json()) for r in ajenos] == [(404, {"detalle": FALTA})] * 4
    assert id_ not in "".join(r.text for r in ajenos)
    assert rita.get("/v1/hoja/borradores").json()["borradores"] == []
    # cerrar uno ajeno es 204 (idempotente) y no lo cierra: el dueño lo sigue viendo
    cerrado = rita.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha_rita))
    assert cerrado.status_code == 204
    assert _rev(ana, id_) == 0


def test_revisa_lee_las_aprobaciones_de_la_obra() -> None:
    rita, _ = con_cuenta(app, "rita")
    respuesta = rita.get("/v1/aprobaciones", params={"proyecto": NOMBRE_OF001})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["eventos"] == [] and respuesta.json()["ultima_aprobada"] is None
