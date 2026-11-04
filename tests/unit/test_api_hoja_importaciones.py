"""El registro de importaciones de la obra, por la API (rediseño del front, F4, Tarea 10).

Contrato (`docs/planes/PLAN_REDISENO_F4.md`, Tarea 10): `GET /v1/hoja/importaciones?proyecto=`
(`leer_proyecto`, como `GET /v1/hoja/versiones`) devuelve `{"importaciones": [{tipo, archivo,
fecha_hora, usuario, resumen, version, guardada}]}`, de la más nueva a la más vieja. Se registra
lo que entra por el plano (fusionar) y por el cómputo (`POST /v1/hoja/llevar` con `archivo`); las
filas se escriben al guardar la versión, en la misma transacción, y lo que sigue en un borrador sale
como «sin guardar» (`version: null`, `guardada: false`). Un borrador descartado no deja rastro.

Datos FICTICIOS: la carpeta en Bs de `tests/fixtures/carpeta_bs_con_obras.py` (obra VIVIENDA, sin
versiones) y la OF-001 de la memoria, con su plano. Oráculos a mano: los resúmenes escritos aquí
(«2 partidas llevadas»), las cuentas de la fusión que da la propia respuesta de `plano/fusionar`
(ya probada en `test_api_hoja_plano.py`) y las filas leídas con `sqlite3` directo.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.rutas import hoja as rutas_hoja
from api.rutas import hoja_llevar as rutas_llevar
from api.rutas import hoja_plano as rutas_plano
from aplicacion import hoja_borradores, hoja_plano
from operacion import config
from tests.fixtures.app_de_prueba import app_con
from tests.fixtures.carpeta_bs_con_obras import VIVIENDA, carpeta_en_bs
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from tests.fixtures.planos_de_la_hoja import (
    AMBIENTES_OF001,
    CIRCUITOS_OF001,
    DXF_OF001,
    altura_de_la_memoria,
)
from tests.fixtures.sesion_web import (
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

APP = app_con(rutas_hoja.router, rutas_llevar.router, rutas_plano.router)
RUTA = "/v1/hoja/importaciones"
HOY = date(2026, 10, 25)
TABLA = "hoja_importaciones"
CLAVES = {"tipo", "archivo", "fecha_hora", "usuario", "resumen", "version", "guardada"}
CIRCUITO_BIEN = ["1", "1", "1", "6"]
FORMA_LLEVAR = (
    "Lo que se lleva a la Hoja no tiene la forma esperada: envíe la obra y de 1 a 2000 partidas, "
    "cada una con su código y su cantidad tal como salen del cómputo."
)
SIN_OBRA = "El proyecto «NO-EXISTE» no existe en este caso."


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_importaciones")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "bs": carpeta_en_bs(carpeta / "bs.db", con_tasa=True),
        "of001": plantilla_of001(carpeta / "of001.db"),
    }


@pytest.fixture(autouse=True)
def _entorno(
    _casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Path]:
    """La instalación con cuentas y la carpeta en Bs como caso por defecto; los planos van a una
    carpeta de la prueba."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: HOY)
    monkeypatch.setattr(rutas_llevar, "_hoy", lambda: HOY)
    planos = tmp_path / "planos_temporales"
    planos.mkdir()
    monkeypatch.setattr(hoja_plano, "DIRECTORIO_TEMPORAL", str(planos))
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["bs"], ruta)
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def con_of001(_casos: dict[str, Path]) -> Path:
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    shutil.copyfile(_casos["of001"], ruta)
    return ruta


def _consulta(ruta: Path, sql: str, *parametros) -> list[tuple]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        return bd.execute(sql, parametros).fetchall()


def _filas_del_registro(ruta: Path) -> list[tuple]:
    """Las filas de la tabla del registro; una base sin la tabla no tiene ninguna."""
    if not _consulta(ruta, "SELECT name FROM sqlite_master WHERE name = ?", TABLA):
        return []
    return _consulta(
        ruta, f"SELECT version_id, tipo, archivo, usuario, resumen FROM {TABLA} ORDER BY id"
    )


def _ana() -> tuple[TestClient, str]:
    return con_cuenta(APP, "ana")


def _llevar(navegador: TestClient, ficha: str, partidas: list[tuple[str, str]], **extra):
    cuerpo = {
        "proyecto": VIVIENDA,
        "partidas": [{"codigo": c, "cantidad": n, "calculo": ""} for c, n in partidas],
        **extra,
    }
    return navegador.post("/v1/hoja/llevar", json=cuerpo, headers=protegida(ficha))


def _guardar(navegador: TestClient, ficha: str, id_: str, rev: int, **extra):
    return navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": rev, "fuente": "Medición del 24/10/2026", **extra},
        headers=protegida(ficha),
    )


def _rev(navegador: TestClient, id_: str) -> int:
    return navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]["rev"]


def _registro(navegador: TestClient, proyecto: str = VIVIENDA) -> list[dict]:
    respuesta = navegador.get(RUTA, params={"proyecto": proyecto})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["importaciones"]


# --- el cómputo ---


def test_llevar_un_computo_lo_anota_como_sin_guardar(_entorno: Path) -> None:
    navegador, ficha = _ana()
    llevado = _llevar(
        navegador, ficha, [("OBRA-04", "210"), ("OBRA-06", "1.125")], archivo="computo.csv"
    )
    assert llevado.status_code == 200, llevado.text

    respuesta = navegador.get(RUTA, params={"proyecto": VIVIENDA})

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert list(cuerpo) == ["importaciones"]
    ((fila,),) = [[f] for f in cuerpo["importaciones"]]
    assert set(fila) == CLAVES
    assert (fila["tipo"], fila["archivo"], fila["usuario"], fila["resumen"]) == (
        "computo",
        "computo.csv",
        "Ana <ana>",
        "2 partidas llevadas",
    )
    assert (fila["version"], fila["guardada"]) == (None, False)
    assert abs((datetime.now() - datetime.fromisoformat(fila["fecha_hora"])).total_seconds()) < 120
    assert _filas_del_registro(_entorno) == []  # nada se escribe hasta guardar


def test_llevar_sin_archivo_no_registra_nada() -> None:
    navegador, ficha = _ana()
    assert _llevar(navegador, ficha, [("OBRA-04", "210")]).status_code == 200
    assert _registro(navegador) == []


@pytest.mark.parametrize(
    "archivo",
    ["C:/x/planta.dxf", "..\\planta.dxf", "a/b.csv", "../x.csv", "x\\y.csv", "", "a" * 256],
)
def test_el_nombre_no_lleva_rutas(archivo: str) -> None:
    navegador, ficha = _ana()
    respuesta = _llevar(navegador, ficha, [("OBRA-04", "210")], archivo=archivo)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA_LLEVAR}
    assert _registro(navegador) == []


# --- guardar ---


def test_guardar_registra_las_importaciones_con_la_version(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _llevar(navegador, ficha, [("OBRA-04", "210")], archivo="computo.csv").json()[
        "borrador_id"
    ]
    guardado = _guardar(navegador, ficha, id_, _rev(navegador, id_), codigo="VIV-001")
    assert guardado.status_code == 200, guardado.text

    ((id_001,),) = _consulta(
        _entorno, "SELECT pr.id FROM presupuesto pr WHERE pr.codigo = ?", "VIV-001"
    )
    assert _filas_del_registro(_entorno) == [
        (id_001, "computo", "computo.csv", "Ana <ana>", "1 partida llevada")
    ]
    ((fila,),) = [[f] for f in _registro(navegador)]
    assert (fila["version"], fila["guardada"], fila["archivo"]) == ("VIV-001", True, "computo.csv")


def test_lista_guardadas_y_sin_guardar_de_la_mas_nueva_a_la_mas_vieja(_entorno: Path) -> None:
    navegador, ficha = _ana()
    primero = _llevar(navegador, ficha, [("OBRA-04", "210")], archivo="uno.csv").json()
    assert (
        _guardar(navegador, ficha, primero["borrador_id"], 1, codigo="VIV-001").status_code == 200
    )
    segundo = _llevar(navegador, ficha, [("OBRA-06", "90")], archivo="dos.csv").json()
    assert _guardar(navegador, ficha, segundo["borrador_id"], 1).status_code == 200
    assert _llevar(navegador, ficha, [("OBRA-01", "5")], archivo="tres.csv").status_code == 200

    lista = _registro(navegador)

    assert [(f["archivo"], f["version"], f["guardada"]) for f in lista] == [
        ("tres.csv", None, False),
        ("dos.csv", "VIV-002", True),
        ("uno.csv", "VIV-001", True),
    ]
    fechas = [f["fecha_hora"] for f in lista]
    assert fechas == sorted(fechas, reverse=True)
    assert [f[2] for f in _filas_del_registro(_entorno)] == ["uno.csv", "dos.csv"]


def test_si_guardar_falla_no_queda_ninguna_fila(
    _entorno: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Todo o nada (C2): las filas del registro viajan en la transacción de la versión. Si algo
    falla después de escribirlas y antes de confirmar, ni la versión ni el registro quedan."""
    from aplicacion import importaciones

    navegador, ficha = _ana()
    id_ = _llevar(navegador, ficha, [("OBRA-04", "210")], archivo="computo.csv").json()[
        "borrador_id"
    ]
    escribir = importaciones.registrar_al_guardar

    def escribe_y_falla(sesion, vivo, version_id) -> None:
        escribir(sesion, vivo, version_id)
        raise RuntimeError("falla justo después de escribir el registro")

    monkeypatch.setattr(importaciones, "registrar_al_guardar", escribe_y_falla)
    respuesta = _guardar(navegador, ficha, id_, 1, codigo="VIV-001")

    assert respuesta.status_code >= 500
    assert _consulta(_entorno, "SELECT COUNT(*) FROM presupuesto WHERE codigo = 'VIV-001'") == [
        (0,)
    ]
    assert _filas_del_registro(_entorno) == []


def test_un_borrador_descartado_no_deja_registro(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _llevar(navegador, ficha, [("OBRA-04", "210")], archivo="computo.csv").json()[
        "borrador_id"
    ]
    assert len(_registro(navegador)) == 1
    borrado = navegador.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha))
    assert borrado.status_code == 204
    assert _registro(navegador) == []
    assert _filas_del_registro(_entorno) == []


# --- el plano ---


def _abrir(navegador: TestClient, ficha: str) -> str:
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": "001"},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _plano_fusionado(navegador: TestClient, ficha: str, id_: str) -> dict:
    base = f"/v1/hoja/borradores/{id_}/plano"
    subido = navegador.post(
        base,
        files={"archivo": ("planta.dxf", DXF_OF001.read_bytes(), "application/octet-stream")},
        data={"rev": "0"},
        headers=protegida(ficha),
    )
    assert subido.status_code == 200, subido.text
    alturas = {a: altura_de_la_memoria() for a in AMBIENTES_OF001}
    cuerpo = {"rev": 0, "alturas": alturas}
    assert (
        navegador.post(f"{base}/alturas", json=cuerpo, headers=protegida(ficha)).status_code == 200
    )
    circuitos = {"rev": 0, "circuitos": {c: CIRCUITO_BIEN for c in CIRCUITOS_OF001}}
    assert (
        navegador.post(f"{base}/circuitos", json=circuitos, headers=protegida(ficha)).status_code
        == 200
    )
    fusion = navegador.post(f"{base}/fusionar", json={"rev": 0}, headers=protegida(ficha))
    assert fusion.status_code == 200, fusion.text
    return fusion.json()


def test_fusionar_un_plano_lo_anota_en_el_borrador(con_of001: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    fusion = _plano_fusionado(navegador, ficha, id_)

    # a mano: el plano de la memoria trae 6 ambientes, 6 fuentes y 21 puntos (33 importados)
    por_tipo = {f["rotulo"]: f["cantidad"] for f in fusion["fusion"]["por_tipo"]}
    assert (por_tipo["Importado"], por_tipo["No reconocido"]) == (33, 0)
    ((fila,),) = [[f] for f in _registro(navegador, NOMBRE_OF001)]
    assert set(fila) == CLAVES
    assert (fila["tipo"], fila["archivo"], fila["usuario"]) == ("plano", "planta.dxf", "Ana <ana>")
    assert fila["resumen"] == "33 filas en el espacio"
    assert (fila["version"], fila["guardada"]) == (None, False)
    assert _filas_del_registro(con_of001) == []  # nada se escribe hasta guardar


def test_descartar_el_plano_sin_fusionar_no_registra_nada(con_of001: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    base = f"/v1/hoja/borradores/{id_}/plano"
    navegador.post(
        base,
        files={"archivo": ("planta.dxf", DXF_OF001.read_bytes(), "application/octet-stream")},
        data={"rev": "0"},
        headers=protegida(ficha),
    )
    assert navegador.delete(base, headers=protegida(ficha)).status_code == 204
    assert _registro(navegador, NOMBRE_OF001) == []


# --- acceso ---


def test_sin_sesion_es_401() -> None:
    assert cliente(APP).get(RUTA, params={"proyecto": VIVIENDA}).status_code == 401


def test_quien_revisa_ve_el_registro() -> None:
    navegador, ficha = _ana()
    assert _llevar(navegador, ficha, [("OBRA-04", "210")], archivo="computo.csv").status_code == 200
    rita, _ = con_cuenta(APP, "rita")
    assert rita.get(RUTA, params={"proyecto": VIVIENDA}).status_code == 200


def test_la_clave_de_api_solo_lee_y_no_ve_borradores_ajenos() -> None:
    navegador, ficha = _ana()
    assert _llevar(navegador, ficha, [("OBRA-04", "210")], archivo="computo.csv").status_code == 200
    respuesta = cliente(APP).get(
        RUTA, params={"proyecto": VIVIENDA}, headers={CABECERA: crear_clave_de_prueba()}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"importaciones": []}  # lo sin guardar es de la ficha que lo abrió


def test_una_obra_que_no_existe_da_404() -> None:
    navegador, _ = _ana()
    respuesta = navegador.get(RUTA, params={"proyecto": "NO-EXISTE"})
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": SIN_OBRA}


def test_la_ruta_pide_proyecto() -> None:
    navegador, _ = _ana()
    assert navegador.get(RUTA).status_code == 422
