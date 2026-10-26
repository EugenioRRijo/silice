"""`/v1/procura`: necesidades con fechas, compras y plazos por la API (MP-7, Tarea 23 del plan de
montar un presupuesto; diseño §11, meta 3).

Contrato (todas con `CONTROL_DE_OBRA`: arma o la clave de API; revisa y administra reciben 403;
`Cache-Control: no-store` en toda respuesta; 422 de forma con un mensaje fijo que no repite lo
enviado; cantidades y fechas como texto; un fallo de la base es un 503 sin SQL ni rutas):

- `GET /v1/procura?proyecto=&corte=` → `{necesidades, alertas, aviso}`.
- `POST /v1/procura/compras` `{proyecto, descripcion, unidad, evento, fecha, cantidad, precio}`
  → 204.
- `PUT /v1/procura/plazos` `{proyecto, descripcion, unidad, dias}` → 204.

El router se monta en una aplicación propia con el de la sesión (para entrar) y los manejadores de
`api.main`, porque `api/main.py` es un archivo compartido que integra el orquestador.

Caso FICTICIO: la vivienda de `tests/fixtures/procura_vivienda.py` con su línea base desde el lunes
2026-11-02 (días hábiles) y la carpeta en Bs; otra obra igual, sin línea base. Oráculos a mano (las
cuentas, en `tests/unit/test_procura.py`): Cemento gris 12 × 7 + 210 × 0,2 = 126 sacos, se necesita
el vie 06/11 (OBRA-02 empieza el día 5) y se pide a más tardar el mar 03/11 (3 días hábiles antes);
con plazo de 5, el vie 30/10. Hoy es 02/11/2026 (`ahora` fijado).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.main import manejar_http_exception
from api.proteccion import proteger
from api.rutas import procura as rutas_procura
from api.rutas import sesion
from aplicacion.cifras import MENSAJE_CIFRA
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from aplicacion.mercado import MENSAJE_SIN_MONEDA, CarpetaSinMoneda
from aplicacion.tablas_procura import CompraDeInsumo, crear_esquema_procura
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import procura_vivienda as pv
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

AHORA = datetime(2026, 11, 2, 9, 30)
RUTA = "/v1/procura"
SIN_LINEA_BASE = "Otra vivienda demo"
MENSAJE_FORMA = (
    "Los datos de la procura no son válidos: el evento es pedida o recibida; las fechas van como "
    "aaaa-mm-dd; la cantidad, el precio y el plazo van como texto; la descripción admite hasta "
    "300 caracteres y la unidad hasta 20."
)
MENSAJE_BASE = "No se pudo leer ni guardar la procura de la carpeta de trabajo."
MENSAJE_INESPERADO = "No se pudo procesar la procura con esos datos."
PRIVADO = "valor-que-nunca-debe-volver"
CEMENTO = {"descripcion": "Cemento gris", "unidad": "saco"}


def _aplicacion() -> FastAPI:
    aplicacion = FastAPI()
    aplicacion.add_exception_handler(HTTPException, manejar_http_exception)
    aplicacion.include_router(sesion.router)
    aplicacion.include_router(rutas_procura.router)
    proteger(aplicacion)
    return aplicacion


APLICACION = _aplicacion()


def _caso(ruta: Path) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema_procura(motor)  # sin efecto cuando la migración ya la creó
    try:
        with abrir_sesion(motor) as s:
            _, lista = pv.sembrar(s)
            pv.declarar_linea_base(s)
            pv.sembrar(s, nombre=SIN_LINEA_BASE, lista=lista)
            declarar_moneda_de_la_carpeta(s, "Bs", responsable="Ana <ana>", ahora=AHORA)
            s.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_procura")
    return {"instalacion": plantilla_con_cuentas(carpeta), "caso": _caso(carpeta / "caso.db")}


@pytest.fixture(autouse=True)
def caso(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    copiar_instalacion(_plantillas["instalacion"])
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    copia = tmp_path / "caso.db"
    copia.write_bytes(_plantillas["caso"].read_bytes())
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{copia.as_posix()}")
    monkeypatch.setattr(rutas_procura, "ahora", lambda: AHORA)
    yield copia
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


@pytest.fixture
def ana() -> tuple[TestClient, dict[str, str]]:
    navegador, ficha = con_cuenta(APLICACION, "ana")
    return navegador, protegida(ficha)


def _sin_cache(respuesta) -> None:
    assert respuesta.headers.get("cache-control") == "no-store", respuesta.headers


def _compras(ruta: Path) -> list[CompraDeInsumo]:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            filas = list(s.scalars(select(CompraDeInsumo).order_by(CompraDeInsumo.id)))
            s.expunge_all()
            return filas
    finally:
        motor.dispose()


def _cemento(cuerpo: dict) -> dict:
    (fila,) = [n for n in cuerpo["necesidades"] if n["descripcion"] == "Cemento gris"]
    return fila


def _compra(**cambios) -> dict:
    datos = {
        "proyecto": pv.OBRA,
        **CEMENTO,
        "evento": "pedida",
        "fecha": "2026-11-02",
        "cantidad": "",
        "precio": "",
    }
    datos.update(cambios)
    return datos


# --- leer ---------------------------------------------------------------------------------------


def test_la_procura_al_corte_del_02_11(ana) -> None:
    respuesta = ana[0].get(RUTA, params={"proyecto": pv.OBRA, "corte": "2026-11-02"})
    assert respuesta.status_code == 200, respuesta.text
    _sin_cache(respuesta)
    cuerpo = respuesta.json()
    cemento = _cemento(cuerpo)
    assert Decimal(cemento.pop("cantidad")) == Decimal("126")
    assert cemento == {
        "descripcion": "Cemento gris",
        "unidad": "saco",
        "partidas": ["OBRA-02", "OBRA-04"],
        "se_necesita": "2026-11-06",
        "pedir_a_mas_tardar": "2026-11-03",
        "plazo": 3,
        "pedida": None,
        "recibida": None,
    }
    assert cuerpo["alertas"] == [
        {"severidad": "ERROR", "texto": "Agua no está pedido y debía pedirse el 28/10/2026."},
        {"severidad": "AVISO", "texto": "Pida Cemento gris antes del 03/11/2026."},
        {"severidad": "AVISO", "texto": "Pida Arena lavada antes del 03/11/2026."},
    ]
    assert cuerpo["aviso"] is None
    assert [n["descripcion"] for n in cuerpo["necesidades"]] == [
        "Agua",
        "Cemento gris",
        "Arena lavada",
        "Cabilla de 1/2 pulgada",
        "Bloque de arcilla de 15 cm",
        "Mortero premezclado",
        "Pintura de caucho",
    ]


def test_sin_corte_vale_hoy_y_la_obra_se_nombra_por_su_codigo(ana, caso: Path) -> None:
    con_nombre = ana[0].get(RUTA, params={"proyecto": pv.OBRA}).json()
    motor = crear_motor(f"sqlite:///{caso.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            codigo = str(
                s.scalars(select(models.Proyecto.id).where(models.Proyecto.nombre == pv.OBRA)).one()
            )
    finally:
        motor.dispose()
    con_codigo = ana[0].get(RUTA, params={"proyecto": codigo}).json()
    assert con_codigo == con_nombre
    assert {"severidad": "AVISO", "texto": "Pida Cemento gris antes del 03/11/2026."} in (
        con_nombre["alertas"]
    )


def test_sin_linea_base_lo_dice_y_no_hay_fechas(ana) -> None:
    cuerpo = ana[0].get(RUTA, params={"proyecto": SIN_LINEA_BASE}).json()
    assert cuerpo["aviso"] == "Declare la línea base para calcular las fechas de compra."
    assert cuerpo["alertas"] == []
    cemento = _cemento(cuerpo)
    assert (cemento["se_necesita"], cemento["pedir_a_mas_tardar"]) == (None, None)


# --- escribir -----------------------------------------------------------------------------------


def test_registrar_un_pedido_quita_la_alerta(ana, caso: Path) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(f"{RUTA}/compras", json=_compra(), headers=cabeceras)
    assert respuesta.status_code == 204, respuesta.text
    _sin_cache(respuesta)
    (compra,) = _compras(caso)
    assert (compra.evento, compra.fecha, compra.responsable) == (
        "pedida",
        date(2026, 11, 2),
        "Ana <ana>",
    )
    cuerpo = navegador.get(RUTA, params={"proyecto": pv.OBRA, "corte": "2026-11-03"}).json()
    assert _cemento(cuerpo)["pedida"] == "2026-11-02"
    assert not [a for a in cuerpo["alertas"] if "Cemento gris" in a["texto"]]


def test_una_recepcion_con_precio_guarda_cantidad_precio_y_moneda(ana, caso: Path) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(
        f"{RUTA}/compras",
        json=_compra(evento="recibida", cantidad="126", precio="1.020,50"),
        headers=cabeceras,
    )
    assert respuesta.status_code == 204, respuesta.text
    (compra,) = _compras(caso)
    assert (compra.evento, compra.cantidad, compra.precio, compra.moneda) == (
        "recibida",
        Decimal("126"),
        Decimal("1020.50"),
        "Bs",
    )


def test_cambiar_el_plazo_corre_la_fecha_de_pedido(ana) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.put(
        f"{RUTA}/plazos", json={"proyecto": pv.OBRA, **CEMENTO, "dias": "5"}, headers=cabeceras
    )
    assert respuesta.status_code == 204, respuesta.text
    _sin_cache(respuesta)
    cemento = _cemento(navegador.get(RUTA, params={"proyecto": pv.OBRA}).json())
    assert (cemento["plazo"], cemento["pedir_a_mas_tardar"]) == (5, "2026-10-30")


# --- errores ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cambio",
    [
        {"evento": PRIVADO},
        {"fecha": PRIVADO},
        {"cantidad": 20},
        {"precio": 20},
        {"descripcion": PRIVADO * 12},
        {"unidad": PRIVADO},
        {"proyecto": None},
    ],
)
def test_una_compra_mal_formada_es_422_fijo_sin_eco(ana, cambio: dict) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(f"{RUTA}/compras", json=_compra(**cambio), headers=cabeceras)
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_FORMA})
    assert PRIVADO not in respuesta.text
    _sin_cache(respuesta)


@pytest.mark.parametrize(
    ("metodo", "ruta", "datos"),
    [
        ("get", f"{RUTA}?proyecto={pv.OBRA}&corte={PRIVADO}", None),
        ("get", RUTA, None),
        ("put", f"{RUTA}/plazos", {"proyecto": pv.OBRA, **CEMENTO, "dias": 5}),
    ],
)
def test_otras_formas_malas_son_422_fijo(ana, metodo: str, ruta: str, datos) -> None:
    navegador, cabeceras = ana
    if metodo == "get":
        respuesta = navegador.get(ruta)
    else:
        respuesta = navegador.put(ruta, json=datos, headers=cabeceras)
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_FORMA})
    assert PRIVADO not in respuesta.text


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        ({"fecha": "2026-11-03"}, "La fecha de la compra no puede ser posterior a hoy."),
        ({"precio": "2.5"}, MENSAJE_CIFRA),
        ({"cantidad": "0"}, "La cantidad debe ser mayor que cero."),
    ],
)
def test_una_regla_de_la_compra_es_422_con_su_mensaje(ana, cambio: dict, mensaje: str) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(f"{RUTA}/compras", json=_compra(**cambio), headers=cabeceras)
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": mensaje})


def test_un_plazo_fuera_de_lo_admitido_es_422_con_su_mensaje(ana) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.put(
        f"{RUTA}/plazos", json={"proyecto": pv.OBRA, **CEMENTO, "dias": "366"}, headers=cabeceras
    )
    assert (respuesta.status_code, respuesta.json()) == (
        422,
        {"detalle": "El plazo de entrega es un número entero de días hábiles, de 0 a 365."},
    )


def test_lo_que_no_existe_es_404(ana, caso: Path) -> None:
    navegador, cabeceras = ana
    for respuesta in (
        navegador.get(RUTA, params={"proyecto": "Obra fantasma"}),
        navegador.post(
            f"{RUTA}/compras", json=_compra(proyecto="Obra fantasma"), headers=cabeceras
        ),
        navegador.post(
            f"{RUTA}/compras",
            json=_compra(descripcion="Mezcladora de concreto", unidad=""),
            headers=cabeceras,
        ),
        navegador.put(
            f"{RUTA}/plazos",
            json={"proyecto": pv.OBRA, "descripcion": "Obrero", "unidad": "", "dias": "2"},
            headers=cabeceras,
        ),
    ):
        assert respuesta.status_code == 404, respuesta.text
        _sin_cache(respuesta)
    assert _compras(caso) == []


def test_sin_moneda_en_la_carpeta_es_409_con_su_mensaje(
    ana, monkeypatch: pytest.MonkeyPatch
) -> None:
    def sin_moneda(*_args, **_kwargs):
        raise CarpetaSinMoneda(MENSAJE_SIN_MONEDA)

    monkeypatch.setattr(rutas_procura, "registrar_compra", sin_moneda)
    navegador, cabeceras = ana
    respuesta = navegador.post(
        f"{RUTA}/compras", json=_compra(evento="recibida", precio="20,00"), headers=cabeceras
    )
    assert (respuesta.status_code, respuesta.json()) == (409, {"detalle": MENSAJE_SIN_MONEDA})


@pytest.mark.parametrize("login", ["rita", "admin"])
def test_quien_no_arma_recibe_403(login: str) -> None:
    navegador, ficha = con_cuenta(APLICACION, login)
    for respuesta in (
        navegador.get(RUTA, params={"proyecto": pv.OBRA}),
        navegador.post(f"{RUTA}/compras", json=_compra(), headers=protegida(ficha)),
        navegador.put(
            f"{RUTA}/plazos",
            json={"proyecto": pv.OBRA, **CEMENTO, "dias": "5"},
            headers=protegida(ficha),
        ),
    ):
        assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": MENSAJE_PERMISO})
        _sin_cache(respuesta)


def test_escribir_sin_csrf_es_403(ana, caso: Path) -> None:
    respuesta = ana[0].post(
        f"{RUTA}/compras", json=_compra(), headers={"Origin": "http://127.0.0.1:8000"}
    )
    assert respuesta.status_code == 403
    assert _compras(caso) == []


def test_con_la_clave_de_api_consta_el_usuario_de_la_api(caso: Path) -> None:
    navegador = cliente(APLICACION)
    respuesta = navegador.post(
        f"{RUTA}/compras", json=_compra(), headers={CABECERA: crear_clave_de_prueba()}
    )
    assert respuesta.status_code == 204, respuesta.text
    assert [c.responsable for c in _compras(caso)] == ["api (clave de API)"]


def test_un_fallo_de_la_base_es_un_503_sin_sql_ni_rutas(
    ana, monkeypatch: pytest.MonkeyPatch
) -> None:
    def falla(*_args, **_kwargs):
        raise OperationalError("SELECT mp_compra.fecha FROM mp_compra", {}, Exception("C:/caso.db"))

    monkeypatch.setattr(rutas_procura, "procura", falla)
    monkeypatch.setattr(rutas_procura, "registrar_compra", falla)
    monkeypatch.setattr(rutas_procura, "fijar_plazo", falla)
    navegador, cabeceras = ana
    for respuesta in (
        navegador.get(RUTA, params={"proyecto": pv.OBRA}),
        navegador.post(f"{RUTA}/compras", json=_compra(), headers=cabeceras),
        navegador.put(
            f"{RUTA}/plazos", json={"proyecto": pv.OBRA, **CEMENTO, "dias": "5"}, headers=cabeceras
        ),
    ):
        assert (respuesta.status_code, respuesta.json()) == (503, {"detalle": MENSAJE_BASE})
        assert "SELECT" not in respuesta.text and "caso.db" not in respuesta.text
        _sin_cache(respuesta)


def test_un_value_error_que_no_es_una_regla_no_sale_por_la_api(
    ana, monkeypatch: pytest.MonkeyPatch
) -> None:
    def falla(*_args, **_kwargs):
        raise ValueError("evento 'x'; detalle interno que no debe salir")

    monkeypatch.setattr(rutas_procura, "registrar_compra", falla)
    navegador, cabeceras = ana
    respuesta = navegador.post(f"{RUTA}/compras", json=_compra(), headers=cabeceras)
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_INESPERADO})
    assert "interno" not in respuesta.text
    _sin_cache(respuesta)
