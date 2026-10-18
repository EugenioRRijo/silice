"""`POST /v1/simulador` y `POST /v1/simulador/csv` (migracion de la pagina «Simulador de listas»).

Paridad con `ui/paginas/simulador.py`: mismos datos, validaciones y mensajes. Datos ficticios.

Oraculos independientes del codigo bajo prueba:

- La lista vigente se escribe aqui a mano (`LISTA`): tres insumos con precio conocido.
- Con variacion maxima 0 el unico sorteo posible es 0 pb: cada precio vuelve a dos decimales
  (redondeo al par del contexto, como el CLI) y el orden es el alfabetico del insumo.
- Con semilla 42 y variacion 5 el sorteo sale de `random.Random(42)` de la biblioteca estandar:
  `randint(-500, 500)` una vez por insumo en orden alfabetico, y el precio es
  `precio x (1 + pb / 10000)` a dos decimales, hecho aqui con `Decimal`.
"""

from __future__ import annotations

import csv
import hashlib
import io
import random
import shutil
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.pool import StaticPool

from api.dependencias import sesion_api
from api.main import app
from aplicacion import simulador as aplicacion_simulador
from core import models
from core.catalog import abrir_sesion, crear_esquema
from operacion import config
from operacion.base_datos import Destino, preparar_base
from scripts import simular_lista
from seguridad import cuentas, sesiones
from seguridad.base import abrir_sesion as abrir_sesion_instalacion
from seguridad.base import crear_motor as crear_motor_instalacion
from seguridad.modelo import Usuario
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona

RUTA = "/v1/simulador"
RUTA_CSV = "/v1/simulador/csv"
COOKIE = "silice_sesion"
NUEVA = "otra contrasena larga de prueba"
CUENTAS = {"admin": CONTRASENA, "ana": NUEVA, "rita": NUEVA}
MENSAJE_SIN_SESION = "Sesión ausente o vencida: entre de nuevo con su cuenta."
MENSAJE_CSRF = "Falta la comprobación anti-CSRF de la sesión o no coincide."
MENSAJE_PERMISO = "Su cuenta no tiene permiso para esta acción."
MENSAJE_SIN_FILAS = "La simulacion no produjo ninguna fila (revise el filtro de insumos)."

#: {descripcion: (codigo, tipo, unidad, precio)}: la lista vigente ficticia de las pruebas.
LISTA = {
    "Arena lavada": ("MAT-901", "material", "m3", Decimal("30.005")),
    "Cemento ficticio": ("MAT-902", "material", "saco", Decimal("15")),
    "Peon ficticio": ("MO-901", "mano_obra", "jornal", Decimal("12.50")),
}
ORDEN = sorted(LISTA)
CENTAVO = Decimal("0.01")


# --- Ayudas -------------------------------------------------------------------------------


def _poblar(sesion) -> None:
    lista = models.ListaPrecios(
        nombre="Lista ficticia", moneda="USD", fecha_vigencia=date(2026, 1, 1), origen="prueba"
    )
    sesion.add(lista)
    sesion.flush()
    for descripcion, (codigo, tipo, unidad, precio) in LISTA.items():
        insumo = models.Insumo(codigo=codigo, tipo=tipo, descripcion=descripcion, unidad=unidad)
        sesion.add(insumo)
        sesion.flush()
        sesion.add(models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=precio))
    sesion.commit()


def _motor_en_memoria():
    from sqlalchemy import create_engine, event

    from core.catalog.sesion import _activar_claves_foraneas

    motor = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    event.listen(motor, "connect", _activar_claves_foraneas)
    crear_esquema(motor)
    return motor


@pytest.fixture
def motor():
    motor = _motor_en_memoria()
    with abrir_sesion(motor) as sesion:
        _poblar(sesion)
    yield motor
    motor.dispose()


@pytest.fixture
def motor_vacio():
    motor = _motor_en_memoria()
    yield motor
    motor.dispose()


def _usar(motor) -> None:
    def _sesion():
        with abrir_sesion(motor) as sesion:
            yield sesion

    app.dependency_overrides[sesion_api] = _sesion


@pytest.fixture(autouse=True)
def _limpiar_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    carpeta = tmp_path_factory.mktemp("plantilla_simulador")
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor_instalacion(plantilla)
    sesion = abrir_sesion_instalacion(motor)
    try:
        admin = administrador(sesion, carpeta)
        for login, roles in (("ana", ("arma",)), ("rita", ("revisa",))):
            usuario = persona(sesion, admin, login, roles)
            cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        for usuario in sesion.scalars(select(Usuario)):
            sesiones.cerrar_todas(sesion, usuario.id, "plantilla")
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path) -> Iterator[None]:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_plantilla, destino)
    cuentas.FRENO.reiniciar()
    yield
    cuentas.FRENO.reiniciar()


def _cliente(**extra) -> TestClient:
    return TestClient(
        app, base_url=ANFITRION, client=IP_LOCAL, raise_server_exceptions=False, **extra
    )


def _con_clave() -> TestClient:
    return _cliente(headers={CABECERA: crear_clave_de_prueba()})


def _con_cuenta(login: str) -> tuple[TestClient, str]:
    cliente = _cliente()
    r = cliente.post("/v1/sesion", json={"login": login, "contrasena": CUENTAS[login]})
    assert r.status_code == 200, r.text
    ficha = r.cookies.get(COOKIE)
    assert ficha
    return cliente, ficha


def _protegida(ficha: str) -> dict[str, str]:
    csrf = hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()
    return {"X-Silice-CSRF": csrf, "Origin": ANFITRION}


def _cuerpo(**extra) -> dict:
    return {"semilla": 42, "variacion_max": "5", "insumos": None, **extra}


def _esperado(semilla: int, variacion: int, solo: set[str] | None = None) -> list[dict]:
    """El oraculo: `random` + `Decimal`, un sorteo por insumo incluido, en orden alfabetico."""
    generador = random.Random(semilla)
    filas = []
    for descripcion in ORDEN:
        _codigo, tipo, unidad, precio = LISTA[descripcion]
        if solo is not None and descripcion not in solo:
            continue  # el insumo filtrado no consume sorteo
        puntos = generador.randint(-variacion * 100, variacion * 100)
        nuevo = (precio * (1 + Decimal(puntos) / Decimal(10000))).quantize(CENTAVO)
        filas.append({"tipo": tipo, "insumo": descripcion, "unidad": unidad, "precio": str(nuevo)})
    return filas


def _conteos(motor) -> tuple[int, int, int]:
    with abrir_sesion(motor) as sesion:
        return tuple(
            sesion.scalar(select(func.count()).select_from(m))
            for m in (models.ListaPrecios, models.PrecioInsumo, models.Insumo)
        )


# --- POST /v1/simulador: datos ------------------------------------------------------------


def test_variacion_cero_devuelve_la_lista_vigente_ordenada_a_dos_decimales(motor) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA, json=_cuerpo(variacion_max="0"))
    assert r.status_code == 200, r.text
    assert r.json() == {
        "filas": [
            {"tipo": "material", "insumo": "Arena lavada", "unidad": "m3", "precio": "30.00"},
            {"tipo": "material", "insumo": "Cemento ficticio", "unidad": "saco", "precio": "15.00"},
            {"tipo": "mano_obra", "insumo": "Peon ficticio", "unidad": "jornal", "precio": "12.50"},
        ]
    }


def test_semilla_42_variacion_5_sigue_el_sorteo_de_random(motor) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA, json=_cuerpo())
    assert r.status_code == 200, r.text
    assert r.json()["filas"] == _esperado(42, 5)
    assert all(isinstance(f["precio"], str) for f in r.json()["filas"])


def test_es_determinista_y_otra_semilla_cambia_la_lista(motor) -> None:
    _usar(motor)
    cliente = _con_clave()
    a = cliente.post(RUTA, json=_cuerpo()).json()
    assert a == cliente.post(RUTA, json=_cuerpo()).json()
    b = cliente.post(RUTA, json=_cuerpo(semilla=43)).json()
    assert b["filas"] == _esperado(43, 5)
    assert a != b


def test_filtro_de_insumos_con_espacios_y_comas_vacias(motor) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA, json=_cuerpo(insumos=" Peon ficticio , ,Arena lavada,"))
    assert r.status_code == 200, r.text
    assert r.json()["filas"] == _esperado(42, 5, {"Peon ficticio", "Arena lavada"})


@pytest.mark.parametrize("insumos", [None, "", "   "])
def test_insumos_vacios_son_todos(motor, insumos) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA, json=_cuerpo(insumos=insumos))
    assert [f["insumo"] for f in r.json()["filas"]] == ORDEN


def test_filtro_que_no_coincide_con_nada_da_filas_vacias_con_200(motor) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA, json=_cuerpo(insumos="Insumo inexistente"))
    assert r.status_code == 200, r.text
    assert r.json() == {"filas": []}


def test_no_escribe_en_la_base(motor) -> None:
    _usar(motor)
    antes = _conteos(motor)
    cliente = _con_clave()
    assert cliente.post(RUTA, json=_cuerpo()).status_code == 200
    assert cliente.post(RUTA_CSV, json=_cuerpo()).status_code == 200
    assert _conteos(motor) == antes == (1, 3, 3)


# --- POST /v1/simulador: validaciones y mensajes ------------------------------------------


def test_variacion_que_no_es_decimal_da_el_mensaje_de_streamlit(motor) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA, json=_cuerpo(variacion_max="cinco"))
    assert r.status_code == 422
    assert r.json()["detalle"].startswith("La variacion maxima no es un numero decimal: ")


@pytest.mark.parametrize("variacion", ["-5", "NaN", "Infinity", ""])
def test_variaciones_invalidas_dan_422_con_detalle_en_texto(motor, variacion) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA, json=_cuerpo(variacion_max=variacion))
    assert r.status_code == 422, r.text
    assert isinstance(r.json()["detalle"], str) and r.json()["detalle"]


def test_sin_lista_vigente_da_409_con_el_texto_del_error(motor_vacio) -> None:
    _usar(motor_vacio)
    r = _con_clave().post(RUTA, json=_cuerpo())
    assert r.status_code == 409, r.text
    assert r.json()["detalle"].startswith("no hay ninguna lista de precios vigente al ")


@pytest.mark.parametrize("semilla", [-1, "42", 1.5, None])
def test_semilla_negativa_o_no_entera_da_422(motor, semilla) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA, json=_cuerpo(semilla=semilla))
    assert r.status_code == 422, r.text


# --- POST /v1/simulador/csv ---------------------------------------------------------------


def test_csv_trae_el_formato_canonico_y_el_nombre_de_archivo(motor) -> None:
    _usar(motor)
    cliente = _con_clave()
    r = cliente.post(RUTA_CSV, json=_cuerpo())
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert 'filename="lista_simulada.csv"' in r.headers["content-disposition"]
    assert r.content.decode("utf-8").startswith("tipo,insumo,unidad,precio\r\n")
    leidas = list(csv.DictReader(io.StringIO(r.content.decode("utf-8"))))
    assert leidas == _esperado(42, 5)
    assert leidas == cliente.post(RUTA, json=_cuerpo()).json()["filas"]


def test_csv_sin_filas_da_422_con_el_mensaje_de_streamlit(motor) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA_CSV, json=_cuerpo(insumos="Insumo inexistente"))
    assert r.status_code == 422
    assert r.json() == {"detalle": MENSAJE_SIN_FILAS}


def test_csv_con_variacion_invalida_da_el_mismo_error(motor) -> None:
    _usar(motor)
    r = _con_clave().post(RUTA_CSV, json=_cuerpo(variacion_max="x"))
    assert r.status_code == 422
    assert r.json()["detalle"].startswith("La variacion maxima no es un numero decimal: ")


# --- Acceso -------------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", [RUTA, RUTA_CSV])
def test_sin_credenciales_da_401(motor, ruta) -> None:
    _usar(motor)
    r = _cliente().post(ruta, json=_cuerpo())
    assert r.status_code == 401
    assert r.json() == {"detalle": MENSAJE_SIN_SESION}


def test_clave_invalida_da_401(motor) -> None:
    _usar(motor)
    r = _cliente(headers={CABECERA: "mala.clave"}).post(RUTA, json=_cuerpo())
    assert r.status_code == 401


@pytest.mark.parametrize("ruta", [RUTA, RUTA_CSV])
def test_quien_arma_entra_con_cookie_y_csrf(motor, ruta) -> None:
    _usar(motor)
    cliente, ficha = _con_cuenta("ana")
    r = cliente.post(ruta, json=_cuerpo(), headers=_protegida(ficha))
    assert r.status_code == 200, r.text


def test_con_cookie_pero_sin_csrf_da_403(motor) -> None:
    _usar(motor)
    cliente, _ficha = _con_cuenta("ana")
    r = cliente.post(RUTA, json=_cuerpo())
    assert r.status_code == 403
    assert r.json() == {"detalle": MENSAJE_CSRF}


def test_quien_solo_revisa_no_puede_simular(motor) -> None:
    _usar(motor)
    cliente, ficha = _con_cuenta("rita")
    r = cliente.post(RUTA, json=_cuerpo(), headers=_protegida(ficha))
    assert r.status_code == 403
    assert r.json() == {"detalle": MENSAJE_PERMISO}


# --- La logica compartida con el CLI ------------------------------------------------------


def test_el_cli_reexporta_la_logica_de_aplicacion() -> None:
    assert simular_lista.simular is aplicacion_simulador.simular
    assert simular_lista.PASO_DE_PRESENTACION == CENTAVO
