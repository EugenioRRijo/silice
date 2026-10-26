"""Elección y preferencias por cuenta (MOD-0 de `docs/planes/PLAN_MODULOS.md`; absorbe la Tarea 5 de
`docs/planes/PLAN_MONTAR_PRESUPUESTO.md`).

Contrato del plan:

- `POST /v1/sesion` y `GET /v1/sesion` agregan `eleccion: {caso, proyecto, aviso}` y
  `preferencias: {modulo, sidebar_fijado}`. Si la ficha no eligió carpeta y la recordada está en la
  carpeta de casos, la restauran. Carpeta recordada que ya no existe → `caso: null` y el aviso
  exacto; obra que ya no existe en la carpeta → `proyecto: null`. Con la contraseña temporal:
  `eleccion: null` y las preferencias por omisión.
- `POST /v1/casos/actual` recuerda la carpeta (y olvida la obra recordada).
- `PUT /v1/sesion/proyecto` `{proyecto}` → 204; `PUT /v1/sesion/preferencias`
  `{modulo?, sidebar_fijado?}` → 204 (lo que no viene no cambia); 422 con el mensaje fijo y sin
  repetir lo enviado; las dos exigen la sesión completa y el anti-CSRF (la clave de API no tiene
  cuenta a la que recordar).

Oráculos escritos a mano: los mensajes, los nombres de las carpetas y la obra «7» que la prueba
inserta con `sqlite3` en `s1.db` (sin SQLAlchemy ni el código bajo prueba).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.rutas import casos as rutas_casos
from api.rutas import sesion as rutas_sesion
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import sesiones
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    ORIGEN,
    cliente,
    con_cuenta,
    copiar_instalacion,
    entrar,
    ficha_de,
    plantilla_con_cuentas,
    protegida,
)

MENSAJE_MODULO = "Ese módulo no existe."
AVISO_S1 = "La carpeta de trabajo «s1» ya no existe; se abrió la de siempre."
MENSAJE_CAMBIAR_CLAVE = "Su contraseña es temporal: elija una propia antes de seguir."
MENSAJE_CSRF = "Falta la comprobación anti-CSRF de la sesión o no coincide."
SIN_PREFERENCIAS = {"modulo": None, "sidebar_fijado": False}
SIN_ELECCION = {"caso": None, "proyecto": None, "aviso": None}
CARPETAS = ("s1.db", "s2.db", "silice.db")


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    """La instalación con cuentas y tres carpetas al día; `s1.db` trae la obra 7 «Torre B»."""
    carpeta = tmp_path_factory.mktemp("plantillas_eleccion")
    casos = {}
    for nombre in CARPETAS:
        casos[nombre] = carpeta / nombre
        preparar_base(casos[nombre])
    with closing(sqlite3.connect(casos["s1.db"])) as conexion:
        conexion.execute(
            "INSERT INTO proyecto (id, nombre, descripcion, dominio) VALUES (7, 'Torre B', '', '')"
        )
        conexion.commit()
    # la carpeta por omisión trae otra obra con el mismo código 7, y la obra 3
    with closing(sqlite3.connect(casos["silice.db"])) as conexion:
        conexion.executemany(
            "INSERT INTO proyecto (id, nombre, descripcion, dominio) VALUES (?, ?, '', '')",
            [(3, "Casa Demo"), (7, "Otra obra con el código 7")],
        )
        conexion.commit()
    return {"instalacion": plantilla_con_cuentas(carpeta), **casos}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in CARPETAS:
        (carpeta / nombre).write_bytes(_plantillas[nombre].read_bytes())
    caso_web.olvidar_todo()
    yield carpeta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _elegir(navegador: TestClient, ficha: str, nombre: str):
    return navegador.post("/v1/casos/actual", json={"nombre": nombre}, headers=protegida(ficha))


def _obra(navegador: TestClient, ficha: str, proyecto: str | None):
    return navegador.put(
        "/v1/sesion/proyecto", json={"proyecto": proyecto}, headers=protegida(ficha)
    )


def _preferencias(navegador: TestClient, ficha: str, cuerpo: dict):
    return navegador.put("/v1/sesion/preferencias", json=cuerpo, headers=protegida(ficha))


def _salir(navegador: TestClient, ficha: str) -> None:
    assert navegador.delete("/v1/sesion", headers=protegida(ficha)).status_code == 204


# --- la carpeta y la obra se recuerdan por cuenta ---------------------------------------------


def test_la_carpeta_y_la_obra_vuelven_al_salir_y_entrar() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    assert _obra(navegador, ficha, "7").status_code == 204
    _salir(navegador, ficha)

    respuesta = entrar(navegador, "ana")

    esperado = {"caso": "s1.db", "proyecto": "7", "aviso": None}
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["eleccion"] == esperado
    assert navegador.get("/v1/sesion").json()["eleccion"] == esperado
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "s1.db"


def test_el_administrador_tambien_recuerda_su_carpeta() -> None:
    navegador, ficha = con_cuenta(app, "admin")
    assert _elegir(navegador, ficha, "s2.db").status_code == 200
    _salir(navegador, ficha)
    assert entrar(navegador, "admin").json()["eleccion"] == {
        "caso": "s2.db",
        "proyecto": None,
        "aviso": None,
    }
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "s2.db"


def test_tras_reiniciar_la_api_la_misma_ficha_recupera_su_carpeta() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    caso_web.olvidar_todo()  # lo que se pierde al reiniciar el proceso
    dependencias.cerrar_motores()

    respuesta = navegador.get("/v1/sesion")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["eleccion"]["caso"] == "s1.db"
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "s1.db"


def test_una_carpeta_borrada_entre_sesiones_avisa_una_vez_y_abre_la_de_siempre(
    _entorno: Path,
) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    assert _obra(navegador, ficha, "7").status_code == 204
    _salir(navegador, ficha)
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo
    (_entorno / "s1.db").unlink()

    respuesta = entrar(navegador, "ana")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["eleccion"] == {"caso": None, "proyecto": None, "aviso": AVISO_S1}
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "silice.db"
    # el aviso se da una vez: la elección perdida se olvida
    assert navegador.get("/v1/sesion").json()["eleccion"] == SIN_ELECCION
    assert not (_entorno / "s1.db").exists()  # nadie la vuelve a crear vacía


def test_una_carpeta_borrada_con_la_ficha_abierta_no_se_recrea_vacia(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    dependencias.cerrar_motores()
    (_entorno / "s1.db").unlink()

    respuesta = navegador.get("/v1/sesion")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["eleccion"] == {"caso": None, "proyecto": None, "aviso": AVISO_S1}
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "silice.db"
    assert not (_entorno / "s1.db").exists()


def test_elegir_otra_carpeta_olvida_la_obra() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    assert _obra(navegador, ficha, "7").status_code == 204
    assert _elegir(navegador, ficha, "s2.db").status_code == 200
    assert navegador.get("/v1/sesion").json()["eleccion"] == {
        "caso": "s2.db",
        "proyecto": None,
        "aviso": None,
    }


def test_una_obra_que_ya_no_esta_en_la_carpeta_vuelve_nula() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    assert _obra(navegador, ficha, "99").status_code == 204
    assert navegador.get("/v1/sesion").json()["eleccion"] == {
        "caso": "s1.db",
        "proyecto": None,
        "aviso": None,
    }


def test_la_obra_se_puede_soltar_con_null() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    assert _obra(navegador, ficha, "7").status_code == 204
    assert _obra(navegador, ficha, None).status_code == 204
    assert navegador.get("/v1/sesion").json()["eleccion"]["proyecto"] is None


def test_sin_nada_recordado_la_eleccion_viene_vacia() -> None:
    navegador, _ = con_cuenta(app, "rita")
    datos = navegador.get("/v1/sesion").json()
    assert datos["eleccion"] == SIN_ELECCION
    assert datos["preferencias"] == SIN_PREFERENCIAS


def test_con_la_clave_de_api_elegir_carpeta_sigue_en_409_y_no_recuerda_nada() -> None:
    respuesta = cliente(app).post(
        "/v1/casos/actual",
        json={"nombre": "s1.db"},
        headers={CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN},
    )
    assert respuesta.status_code == 409
    navegador, _ = con_cuenta(app, "ana")
    assert navegador.get("/v1/sesion").json()["eleccion"] == SIN_ELECCION


def test_el_cuerpo_de_la_obra_invalido_da_422_sin_eco() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _obra(navegador, ficha, "x" * 121 + "secreto")
    assert respuesta.status_code == 422
    assert "secreto" not in respuesta.text
    assert set(respuesta.json()) == {"detalle"}


# --- preferencias: módulo y sidebar fijado ------------------------------------------------------


def test_las_preferencias_se_guardan_y_lo_que_no_viene_no_cambia() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert (
        _preferencias(navegador, ficha, {"modulo": "obras", "sidebar_fijado": True}).status_code
        == 204
    )
    assert navegador.get("/v1/sesion").json()["preferencias"] == {
        "modulo": "obras",
        "sidebar_fijado": True,
    }
    assert _preferencias(navegador, ficha, {"sidebar_fijado": False}).status_code == 204
    assert navegador.get("/v1/sesion").json()["preferencias"] == {
        "modulo": "obras",
        "sidebar_fijado": False,
    }
    assert _preferencias(navegador, ficha, {"modulo": "produccion"}).status_code == 204
    assert navegador.get("/v1/sesion").json()["preferencias"] == {
        "modulo": "produccion",
        "sidebar_fijado": False,
    }


def test_las_preferencias_vuelven_al_entrar_de_nuevo() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert (
        _preferencias(navegador, ficha, {"modulo": "auditoria", "sidebar_fijado": True}).status_code
        == 204
    )
    _salir(navegador, ficha)
    assert entrar(navegador, "ana").json()["preferencias"] == {
        "modulo": "auditoria",
        "sidebar_fijado": True,
    }


def test_un_modulo_que_no_existe_da_422_sin_repetir_lo_enviado() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _preferencias(navegador, ficha, {"modulo": "tablero"})
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_MODULO}
    assert "tablero" not in respuesta.text
    assert navegador.get("/v1/sesion").json()["preferencias"] == SIN_PREFERENCIAS


def test_un_fijado_que_no_es_booleano_da_422_sin_eco() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _preferencias(navegador, ficha, {"sidebar_fijado": "quizas"})
    assert respuesta.status_code == 422
    assert "quizas" not in respuesta.text
    assert set(respuesta.json()) == {"detalle"}


def test_las_preferencias_son_de_cada_cuenta() -> None:
    ana, ficha_ana = con_cuenta(app, "ana")
    rita, ficha_rita = con_cuenta(app, "rita")
    assert _preferencias(ana, ficha_ana, {"modulo": "obras"}).status_code == 204
    assert _preferencias(rita, ficha_rita, {"modulo": "auditoria"}).status_code == 204
    assert ana.get("/v1/sesion").json()["preferencias"]["modulo"] == "obras"
    assert rita.get("/v1/sesion").json()["preferencias"]["modulo"] == "auditoria"
    admin, _ = con_cuenta(app, "admin")
    assert admin.get("/v1/sesion").json()["preferencias"] == SIN_PREFERENCIAS


# --- acceso ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ruta", "cuerpo"),
    [("/v1/sesion/proyecto", {"proyecto": "7"}), ("/v1/sesion/preferencias", {"modulo": "obras"})],
)
def test_sin_csrf_las_dos_escrituras_dan_403(ruta: str, cuerpo: dict) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.put(ruta, json=cuerpo, headers={"Origin": ORIGEN})
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_CSRF}
    assert navegador.get("/v1/sesion").json()["preferencias"] == SIN_PREFERENCIAS


@pytest.mark.parametrize(
    ("ruta", "cuerpo"),
    [("/v1/sesion/proyecto", {"proyecto": "7"}), ("/v1/sesion/preferencias", {"modulo": "obras"})],
)
def test_sin_sesion_o_con_la_clave_de_api_dan_401(ruta: str, cuerpo: dict) -> None:
    assert cliente(app).put(ruta, json=cuerpo, headers={"Origin": ORIGEN}).status_code == 401
    con_clave = cliente(app).put(
        ruta, json=cuerpo, headers={CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN}
    )
    assert con_clave.status_code == 401


def test_con_la_contrasena_temporal_no_hay_eleccion_ni_se_puede_guardar() -> None:
    navegador = cliente(app)
    respuesta = entrar(navegador, "tomas")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["eleccion"] is None
    assert respuesta.json()["preferencias"] == SIN_PREFERENCIAS
    ficha = ficha_de(respuesta)
    assert navegador.get("/v1/sesion").json()["eleccion"] is None
    for ruta, cuerpo in (
        ("/v1/sesion/proyecto", {"proyecto": "7"}),
        ("/v1/sesion/preferencias", {"modulo": "obras"}),
    ):
        bloqueada = navegador.put(ruta, json=cuerpo, headers=protegida(ficha))
        assert bloqueada.status_code == 403
        assert bloqueada.json() == {"detalle": MENSAJE_CAMBIAR_CLAVE}


# --- ronda 2 del árbitro: permisos (C1) y memoria solo tras confirmar (C2) ---------------------


def _cambiar_roles(login: str, roles: list[str]) -> None:
    """El administrador cambia los roles de `login` (lo que cierra sus sesiones)."""
    admin, ficha = con_cuenta(app, "admin")
    cuentas = admin.get("/v1/cuentas").json()["cuentas"]
    destino = next(c["id"] for c in cuentas if c["login"] == login)
    respuesta = admin.post(
        f"/v1/cuentas/{destino}/roles", json={"roles": roles}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 200, respuesta.text


def test_sin_cambiar_caso_no_se_restaura_la_carpeta_recordada() -> None:
    """§12.2: quien perdió `cambiar_caso` no vuelve a una carpeta que ya no podría elegir."""
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    assert _obra(navegador, ficha, "7").status_code == 204
    _cambiar_roles("ana", ["revisa"])

    respuesta = entrar(navegador, "ana")

    assert respuesta.status_code == 200, respuesta.text
    # la obra 7 no está en la carpeta por omisión: tampoco vuelve
    assert respuesta.json()["eleccion"] == SIN_ELECCION
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "silice.db"


def test_la_fila_se_conserva_y_vuelve_si_recupera_cambiar_caso() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    assert _obra(navegador, ficha, "7").status_code == 204
    _cambiar_roles("ana", ["revisa"])
    assert entrar(navegador, "ana").json()["eleccion"]["caso"] is None
    _cambiar_roles("ana", ["arma"])

    respuesta = entrar(navegador, "ana")

    assert respuesta.json()["eleccion"] == {"caso": "s1.db", "proyecto": "7", "aviso": None}
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "s1.db"


def test_si_no_se_puede_recordar_la_carpeta_la_ficha_no_cambia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    navegador, ficha = con_cuenta(app, "ana")

    def falla(*_args, **_kwargs) -> None:
        raise RuntimeError("la instalación no confirmó")

    monkeypatch.setattr(rutas_casos, "recordar_caso", falla)
    assert _elegir(navegador, ficha, "s1.db").status_code == 500
    assert caso_web.elegido(sesiones.huella_de(ficha)) is None
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "silice.db"


def test_si_la_restauracion_no_se_confirma_la_ficha_no_cambia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    assert _obra(navegador, ficha, "99").status_code == 204  # una obra que no está en s1
    caso_web.olvidar_todo()  # reinicio de la API

    def falla(*_args, **_kwargs) -> None:
        raise RuntimeError("la instalación no confirmó")

    monkeypatch.setattr(rutas_sesion, "recordar_proyecto", falla)
    assert navegador.get("/v1/sesion").status_code == 500
    assert caso_web.elegido(sesiones.huella_de(ficha)) is None


# --- menor 1 del árbitro: un código de obra es de su carpeta ------------------------------------


def test_sin_cambiar_caso_la_obra_de_otra_carpeta_no_se_cruza_con_la_por_omision() -> None:
    """El «7» de s1 no es el «7» de silice.db; y una obra guardada sin el permiso es de la carpeta
    por omisión, así que no vuelve pegada a s1 cuando lo recupera."""
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    assert _obra(navegador, ficha, "7").status_code == 204
    _cambiar_roles("ana", ["revisa"])

    respuesta = entrar(navegador, "ana")
    assert respuesta.json()["eleccion"]["proyecto"] is None

    ficha = ficha_de(respuesta)
    assert _obra(navegador, ficha, "3").status_code == 204  # la obra 3 de silice.db
    _cambiar_roles("ana", ["arma"])

    respuesta = entrar(navegador, "ana")
    assert respuesta.json()["eleccion"] == {"caso": None, "proyecto": "3", "aviso": None}
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "silice.db"


def test_quien_nunca_cambia_de_carpeta_recuerda_su_obra() -> None:
    """Plan de montar, T5: todas las cuentas recuerdan; rita trabaja en la carpeta por omisión."""
    navegador, ficha = con_cuenta(app, "rita")
    assert _obra(navegador, ficha, "3").status_code == 204
    _salir(navegador, ficha)
    assert entrar(navegador, "rita").json()["eleccion"] == {
        "caso": None,
        "proyecto": "3",
        "aviso": None,
    }
