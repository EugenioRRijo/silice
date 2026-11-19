"""Quien toma `BEGIN IMMEDIATE` sobre `instalacion.db` lo decide la ruta, no el metodo.

`SesionInstalacionDep` es la diferida de siempre (la usan las rutas que solo leen, y el control de
modulos de TODA ruta: editor de la Hoja, vial, riesgo, produccion). `SesionInstalacionEscrituraDep`
es la de escritura: solo las rutas que escriben tras leer algo que deciden. Se mira lo que abren de
verdad los motores (`tests/fixtures/carrera.py`), con la autenticacion real.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from api import caso_web, dependencias
from api.main import app
from api.rutas import entregas as ruta_entregas
from operacion import config
from operacion.instalacion import sesion_de_instalacion
from produccion import inventario
from produccion.modelo import Movimiento
from seguridad import cuentas, empresas, firma
from tests.fixtures.carrera import begins_de_escritura, dos_a_la_vez
from tests.fixtures.instalacion import AHORA
from tests.fixtures.produccion_api import cliente_con_clave
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)
from tests.integration.test_api_produccion_publicar import CALCULOS, _calcular, _noviembre

MATERIAL = {"codigo": "ARENA", "nombre": "Arena", "unidad_venta": "m3", "existencia_minima": "0"}
FRASE = "frase de firma larga y propia"


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("plantilla_escritura_por_ruta"))


@pytest.fixture(autouse=True)
def _entorno(_instalacion_migrada: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_instalacion_migrada)
    caso_web.olvidar_todo()
    ruta_entregas.FRENO_FIRMA.reiniciar()
    cuentas.FRENO.reiniciar()
    yield
    caso_web.olvidar_todo()
    ruta_entregas.FRENO_FIRMA.reiniciar()
    cuentas.FRENO.reiniciar()
    dependencias.cerrar_motores()


def _admin() -> tuple[TestClient, dict[str, str]]:
    navegador, ficha = con_cuenta(app, "admin")
    return navegador, protegida(ficha)


def _la_instalacion() -> str:
    return config.ruta_instalacion().name


def test_existe_la_dependencia_de_escritura_y_no_es_la_diferida() -> None:
    assert dependencias.SesionInstalacionEscrituraDep is not dependencias.SesionInstalacionDep
    assert dependencias.sesion_instalacion_escritura_api is not dependencias.sesion_instalacion_api


def test_una_ruta_que_no_comprueba_nada_no_toma_el_bloqueo_de_escritura() -> None:
    """El cambio de un modulo es PUT y usa la sesion comun: sigue diferida."""
    navegador, cab = _admin()
    with begins_de_escritura() as tomados:
        r = navegador.put("/v1/modulos/vial", json={"activo": True}, headers=cab)
    assert r.status_code == 200, r.text
    assert _la_instalacion() not in tomados


def test_un_post_de_produccion_toma_una_sola_escritura_y_su_control_de_modulo_solo_lee() -> None:
    """La ruta pide las dos: la diferida (el modulo, solo lee: en WAL no bloquea) y la de
    escritura (la de la ruta). Son dos sesiones y solo una toma `BEGIN IMMEDIATE`."""
    http = cliente_con_clave()
    assert http.get("/salud").status_code == 200
    with begins_de_escritura() as tomados:
        r = http.post("/v1/produccion/materiales", json=MATERIAL)
    assert r.status_code == 201, r.text
    assert tomados.count(_la_instalacion()) == 1


def test_dos_conteos_a_la_vez_no_se_pisan_por_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los dos leen que el material no tiene conteo; con la sesion diferida los dos guardan y el
    de fecha anterior queda DESPUES del posterior. Con la de escritura el segundo espera, ve el
    primero y se rechaza."""
    uno, otro = cliente_con_clave(), cliente_con_clave()
    assert uno.post("/v1/produccion/materiales", json=MATERIAL).status_code == 201

    def conteo(http: TestClient, fecha: str):
        cuerpo = {"material_codigo": "ARENA", "tipo": "ajuste", "fecha": fecha, "cantidad": "40"}
        return lambda: http.post("/v1/produccion/movimientos", json=cuerpo)

    primera, segunda = dos_a_la_vez(
        monkeypatch, inventario, "existencia", conteo(uno, "2026-10-05"), conteo(otro, "2026-10-04")
    )
    assert primera.status_code == 201, primera.text
    assert segunda.status_code in (409, 422), segunda.text  # un conteo anterior al ultimo
    with sesion_de_instalacion() as ins:
        assert ins.scalar(select(func.count()).select_from(Movimiento)) == 1


@pytest.mark.parametrize(
    ("ruta", "cuerpo"),
    [
        ("/v1/admin/empresa", {"nombre": "Demo, C.A.", "rif": "J-00000000-0", "ciudad": ""}),
        ("/v1/admin/empresa/clave", {"contrasena": FRASE}),
        ("/v1/admin/empresa/clave/retirar", {"motivo": "cambio"}),
        ("/v1/admin/empresa/clave/revocar", {"motivo": "perdida"}),
        ("/v1/admin/empresas-registradas/1/retirar", {"fecha": "2026-10-01"}),
        ("/v1/admin/empresas-registradas/1/revocar", {"motivo": "perdida"}),
    ],
    ids=["guardar", "generar", "retirar", "revocar", "retirar-ajena", "revocar-ajena"],
)
def test_las_escrituras_de_la_empresa_abren_begin_immediate(ruta: str, cuerpo: dict) -> None:
    """Sea cual sea el resultado (aqui varias terminan en 400 porque no hay clave ni empresa
    ajena), la sesion que comprueba y escribe se abrio con `BEGIN IMMEDIATE`."""
    navegador, cab = _admin()
    with begins_de_escritura() as tomados:
        if ruta.endswith("empresas-registradas/1/revocar"):  # esa lleva formulario, no JSON
            navegador.post(ruta, data=cuerpo, headers=cab)
        else:
            navegador.post(ruta, json=cuerpo, headers=cab)
    assert tomados.count(_la_instalacion()) == 1


def test_registrar_la_clave_de_otra_empresa_abre_begin_immediate() -> None:
    with sesion_de_instalacion() as ins:
        empresas.guardar_empresa_propia(ins, "Demo, C.A.", "J-00000000-0", "", "admin", AHORA)
        clave = empresas.generar_clave(ins, FRASE, "admin", AHORA)
        archivo = empresas.exportar_clave_publica_propia(ins, AHORA)
        huella = firma.huella_corta(clave.publica)
    navegador, cab = _admin()
    with begins_de_escritura() as tomados:
        navegador.post(
            "/v1/admin/empresas-registradas",
            data={"huella": huella, "metodo": "telefono", "comprobada_con": "Ana"},
            files={"archivo": ("clave.silice-clave", archivo)},
            headers=cab,
        )
    assert tomados.count(_la_instalacion()) == 1


def test_publicar_toma_primero_la_carpeta_del_caso_y_luego_la_instalacion() -> None:
    """Un solo orden de bloqueos (caso -> instalacion), el mismo de `aprobaciones` y `dictamen`:
    dos peticiones que escriben en las dos bases no se esperan en cruz."""
    _noviembre()
    http = cliente_con_clave()
    calculo = _calcular(http)
    navegador, cab = _admin()
    with begins_de_escritura() as tomados:
        r = navegador.post(f"{CALCULOS}/{calculo}/publicar", json={}, headers=cab)
    assert r.status_code == 201, r.text
    instalacion = _la_instalacion()
    assert instalacion in tomados and len(tomados) >= 2
    assert tomados.index(instalacion) > 0, tomados  # antes se tomo la base del caso
