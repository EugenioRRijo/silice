"""`/v1/modulos`: especialidades y módulos activables (plan vial, Tarea 19). Datos FICTICIOS.

Oráculos a mano. Por defecto los cuatro módulos (producción, vial, edificación y riesgo) están
activos. Apagar uno es cosa del administrador (`activar_modulos`): `ana` (arma) y `rita` (revisa)
reciben 403. Un módulo apagado responde 404 con el detalle exacto de D-V-4, «El módulo <nombre>
está apagado en esta instalación.», y **no borra nada**: los tramos de la base siguen ahí y, al
encender, la misma lectura devuelve lo mismo (Foco de revisión 5). Los tramos usan la carpeta
`vivienda.db` (la «Vivienda Demo 80 m2» ficticia) con la misma forma de `test_api_vial.py`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import OBRA, guardar_version, sembrar_vivienda
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

ANA = "Ana <ana>"
CLAVES = ("produccion", "vial", "edificacion", "riesgo")
APAGADO_VIAL = "El módulo vial está apagado en esta instalación."
APAGADO_PRODUCCION = "El módulo producción está apagado en esta instalación."
APAGADO_RIESGO = "El módulo riesgo está apagado en esta instalación."
TRAMO = {
    "id": "T1",
    "progresiva_ini_km": "0",
    "progresiva_fin_km": "1",
    "ancho_m": "7.3",
    "distancia_planta_km": "12",
    "capas": [
        {"tipo": "carpeta", "espesor_m": "0.05", "densidad_t_m3": "2.35", "dosis_l_m2": None},
    ],
    "demarcacion": [],
}
MEJORA = {
    "costo_final_real": "130",
    "presupuesto_original": "100",
    "estimacion_silice": "126.92",
}


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_modulos")
    vivienda = carpeta / "vivienda.db"
    preparar_base(vivienda)
    motor = crear_motor(f"sqlite:///{vivienda.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            obra = sembrar_vivienda(s, usuario=ANA)
            guardar_version(s, obra, "VIV-002", usuario=ANA)
    finally:
        motor.dispose()
    return {"instalacion": plantilla_con_cuentas(carpeta), "vivienda.db": vivienda}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / "vivienda.db").write_bytes(_plantillas["vivienda.db"].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def ana() -> tuple[TestClient, str]:
    navegador, ficha = con_cuenta(app, "ana")
    elegida = navegador.post(
        "/v1/casos/actual", json={"nombre": "vivienda.db"}, headers=protegida(ficha)
    )
    assert elegida.status_code == 200, elegida.text
    return navegador, ficha


@pytest.fixture
def admin() -> tuple[TestClient, str]:
    return con_cuenta(app, "admin")


def _poner(cuenta, clave: str, activo: bool):
    navegador, ficha = cuenta
    return navegador.put(f"/v1/modulos/{clave}", json={"activo": activo}, headers=protegida(ficha))


def _estado(cuenta) -> dict[str, bool]:
    navegador, _ = cuenta
    r = navegador.get("/v1/modulos")
    assert r.status_code == 200, r.text
    return {m["clave"]: m["activo"] for m in r.json()["modulos"]}


def _tramos(cuenta):
    navegador, _ = cuenta
    return navegador.get("/v1/vial/tramos", params={"proyecto": OBRA, "version": "VIV-002"})


def _guardar_tramos(cuenta):
    navegador, ficha = cuenta
    return navegador.put(
        "/v1/vial/tramos",
        params={"proyecto": OBRA, "version": "VIV-002"},
        json={"tramos": [TRAMO], "fuente": "plano 3 (ficticio)"},
        headers=protegida(ficha),
    )


def _filas_de_tramos() -> int:
    with closing(sqlite3.connect(config.carpeta_casos() / "vivienda.db")) as conexion:
        return conexion.execute("SELECT COUNT(*) FROM vial_tramos_guardado").fetchone()[0]


def test_por_defecto_los_cuatro_modulos_estan_activos(ana) -> None:
    navegador, _ = ana
    r = navegador.get("/v1/modulos")
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    assert [m["clave"] for m in r.json()["modulos"]] == list(CLAVES)
    assert all(m["activo"] for m in r.json()["modulos"])
    assert [m["nombre"] for m in r.json()["modulos"]] == [
        "producción",
        "vial",
        "edificación",
        "riesgo",
    ]
    assert all(m["cambiado_por"] is None for m in r.json()["modulos"])


def test_sin_sesion_401() -> None:
    assert cliente(app).get("/v1/modulos").status_code == 401


def test_el_administrador_apaga_y_enciende_y_queda_quien_y_cuando(admin) -> None:
    r = _poner(admin, "vial", False)
    assert r.status_code == 200, r.text
    fila = {m["clave"]: m for m in r.json()["modulos"]}["vial"]
    assert fila["activo"] is False
    assert fila["cambiado_por"] == "admin"
    assert abs(datetime.fromisoformat(fila["cambiado_el"]) - datetime.now()) < timedelta(minutes=2)
    assert _estado(admin) == {
        "produccion": True,
        "vial": False,
        "edificacion": True,
        "riesgo": True,
    }
    assert _poner(admin, "vial", True).status_code == 200
    assert _estado(admin)["vial"] is True


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_quien_no_administra_recibe_403(login: str, admin) -> None:
    quien = con_cuenta(app, login)
    r = _poner(quien, "vial", False)
    assert r.status_code == 403, r.text
    assert r.json()["detalle"] == MENSAJE_PERMISO
    assert _estado(admin)["vial"] is True


def test_modulo_desconocido_404_y_cuerpo_malo_422(admin) -> None:
    assert _poner(admin, "astronomia", False).status_code == 404
    navegador, ficha = admin
    malo = navegador.put("/v1/modulos/vial", json={"activo": "quizas"}, headers=protegida(ficha))
    assert malo.status_code == 422, malo.text
    assert _estado(admin)["vial"] is True


def test_vial_apagado_404_con_el_detalle_de_dv4_y_los_tramos_siguen(ana, admin) -> None:
    """Foco 5: el módulo apagado no borra nada y al encender todo vuelve igual."""
    guardado = _guardar_tramos(ana)
    assert guardado.status_code == 200, guardado.text
    antes = _tramos(ana)
    assert antes.status_code == 200 and [t["id"] for t in antes.json()["tramos"]] == ["T1"]

    assert _poner(admin, "vial", False).status_code == 200
    apagado = _tramos(ana)
    assert apagado.status_code == 404, apagado.text
    assert apagado.json() == {"detalle": APAGADO_VIAL}
    assert _guardar_tramos(ana).status_code == 404
    assert ana[0].get("/v1/vial/obras").status_code == 404
    assert _filas_de_tramos() == 1  # nada se borró

    assert _poner(admin, "vial", True).status_code == 200
    despues = _tramos(ana)
    assert despues.status_code == 200, despues.text
    assert despues.json() == antes.json()


def test_el_modulo_apagado_no_adelanta_al_acceso(admin) -> None:
    """Sin sesión sigue siendo 401: apagado o no, el módulo no se anuncia a quien no entró."""
    assert _poner(admin, "vial", False).status_code == 200
    anonimo = cliente(app).get("/v1/vial/tramos", params={"proyecto": OBRA, "version": "VIV-002"})
    assert anonimo.status_code == 401


def test_produccion_apagada_cierra_la_arenera_y_los_costos(ana, admin) -> None:
    navegador, _ = ana
    assert navegador.get("/v1/produccion/materiales").status_code == 200
    assert _poner(admin, "produccion", False).status_code == 200
    for ruta in ("/v1/produccion/materiales", "/v1/produccion/costos", "/v1/produccion/calculos"):
        r = navegador.get(ruta)
        assert r.status_code == 404, (ruta, r.text)
        assert r.json() == {"detalle": APAGADO_PRODUCCION}
    assert _poner(admin, "produccion", True).status_code == 200
    assert navegador.get("/v1/produccion/materiales").status_code == 200


def test_riesgo_apagado_404_y_al_encender_vuelve(ana, admin) -> None:
    navegador, ficha = ana
    assert (
        navegador.post("/v1/riesgo/mejora", json=MEJORA, headers=protegida(ficha)).status_code
        == 200
    )
    assert _poner(admin, "riesgo", False).status_code == 200
    r = navegador.post("/v1/riesgo/mejora", json=MEJORA, headers=protegida(ficha))
    assert r.status_code == 404 and r.json() == {"detalle": APAGADO_RIESGO}
    assert _poner(admin, "riesgo", True).status_code == 200
    assert (
        navegador.post("/v1/riesgo/mejora", json=MEJORA, headers=protegida(ficha)).status_code
        == 200
    )


def test_la_aplicacion_arranca_y_responde_con_todo_apagado(ana, admin) -> None:
    for clave in CLAVES:
        assert _poner(admin, clave, False).status_code == 200
    assert _estado(admin) == dict.fromkeys(CLAVES, False)
    navegador, _ = ana
    assert navegador.get("/salud").status_code == 200
    assert navegador.get("/v1/acerca").status_code == 200
    assert navegador.get("/v1/sesion").status_code == 200
    assert navegador.get("/openapi.json").status_code == 200
    assert navegador.get("/v1/modulos").status_code == 200


def test_lo_apagado_sobrevive_al_reinicio_del_proceso(admin) -> None:
    assert _poner(admin, "riesgo", False).status_code == 200
    dependencias.cerrar_motores()
    from operacion import instalacion

    instalacion.cerrar_motores()
    assert _estado(admin)["riesgo"] is False


APAGADO_EDIFICACION = "El módulo edificación está apagado en esta instalación."
ID_BORRADOR = "id-borrador-plano-0001"
#: Las rutas que SOLO sirven a edificación (planos DXF/IFC y el editor del espacio).
RUTAS_DE_EDIFICACION = [
    ("POST", f"/v1/hoja/borradores/{ID_BORRADOR}/plano"),
    ("POST", f"/v1/hoja/borradores/{ID_BORRADOR}/plano/unidad"),
    ("POST", f"/v1/hoja/borradores/{ID_BORRADOR}/plano/alturas"),
    ("POST", f"/v1/hoja/borradores/{ID_BORRADOR}/plano/circuitos"),
    ("POST", f"/v1/hoja/borradores/{ID_BORRADOR}/plano/fusionar"),
    ("DELETE", f"/v1/hoja/borradores/{ID_BORRADOR}/plano"),
    ("PUT", f"/v1/hoja/borradores/{ID_BORRADOR}/espacio"),
]


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_DE_EDIFICACION)
def test_edificacion_apagada_cierra_planos_y_espacio(metodo: str, ruta: str, ana, admin) -> None:
    assert _poner(admin, "edificacion", False).status_code == 200
    navegador, ficha = ana
    r = navegador.request(metodo, ruta, headers=protegida(ficha))
    assert r.status_code == 404, (ruta, r.text)
    assert r.json() == {"detalle": APAGADO_EDIFICACION}


def test_edificacion_apagada_no_cierra_la_hoja_ni_el_presupuesto(ana, admin) -> None:
    """Una obra vial también usa la Hoja: sus lecturas y sus ediciones de presupuesto siguen."""
    assert _poner(admin, "edificacion", False).status_code == 200
    navegador, ficha = ana
    v = navegador.get("/v1/hoja/versiones", params={"proyecto": OBRA})
    assert v.status_code == 200, v.text
    assert navegador.get("/v1/hoja/borradores").status_code == 200
    # Una edición de presupuesto llega a su ruta (borrador inexistente: error de la hoja).
    r = navegador.put(
        f"/v1/hoja/borradores/{ID_BORRADOR}/cantidades",
        json={"rev": 0, "filas": []},
        headers=protegida(ficha),
    )
    assert r.json().get("detalle") != APAGADO_EDIFICACION


def test_edificacion_apagada_y_luego_encendida_vuelve_a_abrir_los_planos(ana, admin) -> None:
    assert _poner(admin, "edificacion", False).status_code == 200
    assert _poner(admin, "edificacion", True).status_code == 200
    navegador, ficha = ana
    r = navegador.delete(f"/v1/hoja/borradores/{ID_BORRADOR}/plano", headers=protegida(ficha))
    assert r.json().get("detalle") != APAGADO_EDIFICACION


def test_vial_apagado_sin_editar_hoja_recibe_403_antes_que_404(admin) -> None:
    """El módulo se comprueba DESPUÉS del acceso: `rita` (revisa) no edita la hoja."""
    assert _poner(admin, "vial", False).status_code == 200
    rita = con_cuenta(app, "rita")
    r = _tramos(rita)
    assert r.status_code == 403, r.text
    assert r.json() == {"detalle": MENSAJE_PERMISO}
    assert rita[0].get("/v1/vial/obras").status_code == 403


def test_vial_apagado_con_el_rol_correcto_sigue_siendo_404(ana, admin) -> None:
    assert _poner(admin, "vial", False).status_code == 200
    r = _tramos(ana)
    assert r.status_code == 404 and r.json() == {"detalle": APAGADO_VIAL}
    llevar = ana[0].post(
        "/v1/vial/tramos/llevar",
        json={"proyecto": OBRA, "version": "VIV-002"},
        headers=protegida(ana[1]),
    )
    assert llevar.status_code == 404 and llevar.json() == {"detalle": APAGADO_VIAL}
