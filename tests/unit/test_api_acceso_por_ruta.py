"""Acceso por ruta, no por router (RM-3; ola 0a de la sesión 2b).

Cada ruta de la API acepta la clave de API (`X-Silice-Clave`, las integraciones) o la cookie de
sesión con el rol de la acción que corresponde a la página Streamlit que hace lo mismo. La tabla de
abajo es el oráculo, escrita a mano (no se lee de `api/acceso.py`), y los roles de cada acción
también (`seguridad.permisos.PERMISOS` es lo que se prueba, no la fuente):

- lectura (`LEER_PROYECTO`, arma y revisa): Catálogo, Histórico, Tablero y el libro de la empresa;
- escritura de la hoja (`EDITAR_HOJA`, arma): Elaborar, Actualizar precios (que es quien carga una
  lista con `crear_lista_desde_archivo`, `ui/paginas/actualizacion.py:121`), Escenarios, Componer;
- `POST /v1/auditorias` reaudita un paquete como «Revisar un paquete» (`REVISAR_PAQUETE`, revisa);
- `POST /v1/casos/actual`, `CAMBIAR_CASO` (arma y administrador); `GET /v1/casos`, cualquier rol.

Tres pruebas: (1) la tabla cubre exactamente las rutas de la aplicación; (2) por rol, cada ruta deja
pasar o rechaza con 403 según la tabla; (3) ninguna ruta queda abierta salvo `/salud` y la entrada
(`POST /v1/sesion`), y fuera de las rutas de la API solo están la documentación y `/app`. La
regresión «con clave, igual que antes» se mide contra una aplicación de referencia que monta los
mismos puntos finales con solo `exigir_clave_api` (el `CON_CLAVE` de antes de la ola 0a).

Para no depender de una base de caso, `sesion_api` se sustituye por una que responde 418: quien
llega a 418 pasó el acceso (la dependencia de acceso corre antes que las del punto final).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.routing import APIRoute
from starlette.routing import Mount, Route

from api import dependencias
from api.dependencias import sesion_api
from api.main import (
    app,
    manejar_catalogo_incompleto,
    manejar_http_exception,
    manejar_lookup_error,
    manejar_value_error,
)
from api.proteccion import exigir_clave_api
from api.rutas import auditorias, catalogo, computos, listas, presupuestos, rendimientos
from core.catalog import CatalogoIncompleto
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    CUENTAS,
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

LEER, EDITAR, REVISAR, CAMBIAR_CASO, CUALQUIERA, CONTROLAR, DECIDIR = (
    "leer_proyecto", "editar_hoja", "revisar_paquete", "cambiar_caso", "cualquier rol",
    "control_de_obra", "decidir_recuperacion",
)
ENTREGAR = "entregar_paquete"
#: Los roles de cada acción, a mano (spec S3 §5.1).
ROLES = {
    LEER: {"arma", "revisa"},
    EDITAR: {"arma"},
    REVISAR: {"revisa"},
    ENTREGAR: {"arma"},
    CAMBIAR_CASO: {"arma", "administrador"},
    CONTROLAR: {"arma"},
    DECIDIR: {"arma"},
    CUALQUIERA: {"arma", "revisa", "administrador"},
}
#: (método, ruta) -> acción. Las rutas sin sesión (`/salud`, `/v1/sesion*`) van aparte.
TABLA = {
    ("GET", "/partidas"): LEER,
    ("GET", "/insumos"): LEER,
    ("GET", "/listas-precios"): LEER,
    ("POST", "/listas-precios"): EDITAR,
    ("POST", "/listas-precios/vista-previa"): EDITAR,  # ola 2: Actualizar precios
    ("GET", "/cambios-precio"): LEER,
    ("POST", "/computos/{dominio}"): EDITAR,
    ("POST", "/proyectos"): EDITAR,
    ("POST", "/presupuestos"): EDITAR,
    ("POST", "/presupuestos/importar"): EDITAR,
    ("GET", "/presupuestos"): LEER,
    ("GET", "/presupuestos/{codigo}"): LEER,
    ("GET", "/presupuestos/{codigo}/informe"): LEER,
    ("GET", "/presupuestos/{codigo}/excel"): LEER,
    ("POST", "/presupuestos/{codigo}/actualizacion"): EDITAR,
    ("POST", "/presupuestos/calcular"): EDITAR,  # ola 2: Elaborar
    ("POST", "/presupuestos/calcular/excel"): EDITAR,  # ola 2: Elaborar
    ("POST", "/presupuestos/calcular/declarar-rendimiento"): EDITAR,  # ola 2: Elaborar
    ("GET", "/presupuestos/{codigo}/escenarios/base"): LEER,  # ola 2: Escenarios
    ("POST", "/presupuestos/{codigo}/escenarios/csv"): EDITAR,  # ola 2: Escenarios
    ("POST", "/presupuestos/revalorar"): EDITAR,  # ola 2: Actualizar precios
    ("POST", "/presupuestos/{codigo}/descartar"): EDITAR,  # ola 2: Actualizar precios
    ("POST", "/presupuestos/{codigo}/escenarios"): EDITAR,
    ("POST", "/ejecuciones"): EDITAR,
    ("GET", "/ejecuciones"): LEER,
    ("GET", "/partidas/{codigo}/rendimientos"): LEER,
    ("POST", "/partidas/{codigo}/rendimientos"): EDITAR,
    ("POST", "/v1/auditorias"): REVISAR,
    ("POST", "/v1/libros/auditoria"): LEER,
    ("POST", "/v1/libros/devolucion"): LEER,
    ("POST", "/v1/libros/pdf"): LEER,
    ("POST", "/v1/libros/replica"): LEER,
    ("GET", "/v1/tablero"): LEER,  # ola 4: Tablero
    ("GET", "/v1/control/linea-base"): CONTROLAR,  # ola 4: Control de obra
    ("POST", "/v1/control/linea-base"): CONTROLAR,
    ("POST", "/v1/control/parametros"): CONTROLAR,
    ("GET", "/v1/control/valuaciones"): CONTROLAR,
    ("POST", "/v1/control/valuaciones"): CONTROLAR,
    ("POST", "/v1/control/valuaciones/{valuacion_id}/anular"): CONTROLAR,
    ("POST", "/v1/control/costos"): CONTROLAR,
    ("POST", "/v1/control/importar/informe"): CONTROLAR,
    ("POST", "/v1/control/importar"): CONTROLAR,
    ("GET", "/v1/control/calculo"): CONTROLAR,
    ("POST", "/v1/control/recuperacion/opciones"): CONTROLAR,
    ("POST", "/v1/control/recuperacion/elegir"): DECIDIR,
    ("GET", "/v1/casos"): CUALQUIERA,
    ("POST", "/v1/casos/actual"): CAMBIAR_CASO,
    ("GET", "/v1/proyectos"): LEER,
    ("POST", "/v1/similares"): EDITAR,
    ("POST", "/v1/simulador"): EDITAR,
    ("POST", "/v1/simulador/csv"): EDITAR,
    # Ola 3 (S2-B): «Componer una partida» es de quien arma (`ui/paginas/componer.py`)
    ("GET", "/v1/composicion/opciones"): EDITAR,
    ("POST", "/v1/composicion/evaluar"): EDITAR,
    ("GET", "/v1/composicion/partidas/{codigo}"): EDITAR,
    ("GET", "/v1/composicion/referencia"): EDITAR,
    ("GET", "/v1/composicion/similares"): EDITAR,
    ("POST", "/v1/composicion/guardar"): EDITAR,
    ("GET", "/v1/entregas/versiones"): ENTREGAR,
    ("GET", "/v1/entregas/resumen"): ENTREGAR,
    ("POST", "/v1/entregas"): ENTREGAR,
}
#: Las de la puerta de entrada: la sesión misma (con su propia regla) y el ping.
DE_LA_SESION = {
    ("GET", "/salud"),
    ("POST", "/v1/sesion"),
    ("GET", "/v1/sesion"),
    ("DELETE", "/v1/sesion"),
    ("POST", "/v1/sesion/contrasena"),
}
SIN_NADA = {("GET", "/salud"), ("POST", "/v1/sesion")}  # las únicas abiertas


def _rutas(router) -> Iterator[APIRoute]:
    """Como `tests/integration/test_api_clave.py`: FastAPI >= 0.140 no aplana `include_router`."""
    for ruta in router.routes:
        if isinstance(ruta, APIRoute):
            yield ruta
        elif hasattr(ruta, "original_router"):
            yield from _rutas(ruta.original_router)


def _pares(aplicacion: FastAPI) -> list[tuple[str, str]]:
    return sorted(
        (metodo, ruta.path)
        for ruta in _rutas(aplicacion.router)
        for metodo in ruta.methods - {"HEAD", "OPTIONS"}
    )


PARES = _pares(app)


def _concreta(ruta: str) -> str:
    return re.sub(r"\{[^}]+\}", "x", ruta)


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("acceso_por_ruta"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    yield
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


def _llego() -> None:
    raise HTTPException(status_code=418, detail="llegó al punto final")


@pytest.fixture
def _sin_base() -> Iterator[None]:
    app.dependency_overrides[sesion_api] = _llego
    try:
        yield
    finally:
        app.dependency_overrides.pop(sesion_api, None)


def test_la_tabla_cubre_exactamente_las_rutas_de_la_api() -> None:
    assert set(PARES) == set(TABLA) | DE_LA_SESION


def test_fuera_de_las_rutas_de_la_api_solo_hay_documentacion_y_la_interfaz() -> None:
    """Lo que no es `APIRoute` (ni un router incluido) no lleva la dependencia de acceso: solo
    puede ser la documentación (que el producto apaga) y el montaje estático de `/app`."""
    otras = {
        (type(ruta), ruta.path)
        for ruta in app.router.routes
        if not isinstance(ruta, APIRoute) and not hasattr(ruta, "original_router")
    }
    documentacion = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    permitidas = {(Route, camino) for camino in documentacion} | {(Route, "/app"), (Mount, "/app")}
    assert otras <= permitidas and (Mount, "/app") in otras


@pytest.mark.parametrize(("metodo", "ruta"), PARES, ids=[f"{m} {r}" for m, r in PARES])
def test_ninguna_ruta_queda_abierta_salvo_salud_y_la_entrada(metodo: str, ruta: str) -> None:
    respuesta = cliente(app).request(
        metodo, _concreta(ruta), json={}, headers={"Origin": "http://127.0.0.1:8000"}
    )
    if (metodo, ruta) in SIN_NADA:
        assert respuesta.status_code != 401
    else:
        assert respuesta.status_code == 401, respuesta.text
        assert "detalle" in respuesta.json()


@pytest.mark.usefixtures("_sin_base")
@pytest.mark.parametrize("login", ["admin", "ana", "rita"])
def test_cada_ruta_exige_el_rol_de_su_accion(login: str) -> None:
    navegador, ficha = con_cuenta(app, login)
    roles = CUENTAS[login][1]
    discrepancias = []
    for (metodo, ruta), accion in sorted(TABLA.items()):
        respuesta = navegador.request(
            metodo, _concreta(ruta), json={}, headers=protegida(ficha)
        )
        if roles & ROLES[accion]:
            paso = respuesta.status_code not in (401, 403)
        else:
            paso = respuesta.status_code != 403 or respuesta.json() != {"detalle": MENSAJE_PERMISO}
        if paso != bool(roles & ROLES[accion]):
            discrepancias.append((metodo, ruta, accion, respuesta.status_code, respuesta.text))
    assert discrepancias == []


@pytest.mark.usefixtures("_sin_base")
def test_un_metodo_que_escribe_exige_csrf_con_la_cookie() -> None:
    navegador, _ = con_cuenta(app, "ana")
    for (metodo, ruta), accion in sorted(TABLA.items()):
        if metodo == "GET" or "arma" not in ROLES[accion]:
            continue
        respuesta = navegador.request(
            metodo, _concreta(ruta), json={}, headers={"Origin": "http://127.0.0.1:8000"}
        )
        assert respuesta.status_code == 403, (metodo, ruta, respuesta.text)


def _referencia() -> FastAPI:
    """Los puntos finales de los seis routers antiguos con solo `exigir_clave_api`, sin las
    dependencias por ruta de la ola 0a: lo que la API respondía antes con `CON_CLAVE`."""
    referencia = FastAPI()
    referencia.add_exception_handler(CatalogoIncompleto, manejar_catalogo_incompleto)
    referencia.add_exception_handler(HTTPException, manejar_http_exception)
    referencia.add_exception_handler(LookupError, manejar_lookup_error)
    referencia.add_exception_handler(ValueError, manejar_value_error)
    for modulo in (catalogo, listas, computos, presupuestos, rendimientos, auditorias):
        for ruta in _rutas(modulo.router):
            referencia.add_api_route(
                ruta.path,
                ruta.endpoint,
                methods=list(ruta.methods),
                response_model=ruta.response_model,
                status_code=ruta.status_code,
                response_class=ruta.response_class,
                dependencies=[Depends(exigir_clave_api)],
            )
    return referencia


REFERENCIA = _referencia()
ANTIGUAS = sorted(
    par for par in TABLA if par in set(_pares(REFERENCIA))
)


def test_la_referencia_monta_las_rutas_de_los_routers_de_siempre() -> None:
    assert len(ANTIGUAS) == 20 + 8  # + ola 2 (vista previa, revalorar, ...)
    assert set(_pares(REFERENCIA)) == set(ANTIGUAS)


def test_con_clave_de_api_las_rutas_antiguas_responden_igual_que_antes() -> None:
    """Con una clave válida, una falsa y una vacía; sobre la base real del caso por defecto (la
    misma para las dos aplicaciones), cuerpo `{}` en los POST."""
    clave = crear_clave_de_prueba()
    distintas = []
    for cabecera in (clave, "AB12CD34.no-es-la-clave", ""):
        for metodo, ruta in ANTIGUAS:
            pedir = {"json": {}, "headers": {CABECERA: cabecera}}
            antes = cliente(REFERENCIA).request(metodo, _concreta(ruta), **pedir)
            ahora = cliente(app).request(metodo, _concreta(ruta), **pedir)
            if (antes.status_code, antes.content) != (ahora.status_code, ahora.content):
                distintas.append((cabecera[:8], metodo, ruta, antes.status_code, ahora.status_code))
    assert distintas == []
