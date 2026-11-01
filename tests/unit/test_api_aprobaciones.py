"""`/v1/aprobaciones`: el ciclo de aprobación por la API (MP-4, Tarea 18 del plan de montar un
presupuesto, con los cambios por el diseño de módulos; diseño §5.4 y §10).

Contrato: `POST ""` (`editar_hoja`) envía; `GET ""?proyecto=` (`editar_hoja`) da rastro, fases,
estados y eventos de la obra; `GET /pendientes` (`aprobar_version`) lista lo que espera dictamen en
todas las carpetas (índice de la instalación) y repone la carpeta abierta; `GET /mias`
(`editar_hoja`) las últimas 20 filas enviadas por la cuenta; `GET /resumen` (`aprobar_version`) la
cifra «Por aprobar» de la mesa; `POST /abrir` (`aprobar_version`) cambia la carpeta de la sesión a
la del envío; `GET /{id}` (`aprobar_version`) lo que se aprueba, en solo lectura; `POST
/{id}/dictamen` (`aprobar_version`, solo con sesión) dictamina. 404/409/422 con el mensaje de la
regla; 422 de forma fijo y sin eco; 503 fijo ante un fallo de la base; `no-store` en todo.

Carpetas: `silice.db` (la de la empresa, vacía) y `vivienda.db` con la «Vivienda Demo 80 m2»
(VIV-001 y VIV-002, seis partidas, `tests/fixtures/carpeta_aprobaciones.py`) guardadas por «Ana
<ana>». Ana elige `vivienda.db`; Rita (revisa) trabaja en la de la empresa hasta abrir un envío.
Oráculos a mano (mensajes, horas, estados, códigos y descripciones de las partidas); los montos de
la versión se leen en la prueba con `sqlite3` y se suman en `Decimal`, sin el código bajo prueba.

El router se monta aquí con el de la sesión y el de las carpetas, porque `api/main.py` es un
archivo compartido que integra el orquestador.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
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
from api.rutas import aprobaciones as rutas
from api.rutas import casos, sesion
from aplicacion import aprobaciones, indice_aprobaciones
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion import config, instalacion
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import (
    OBRA,
    PARTIDAS,
    guardar_version,
    sembrar_vivienda,
)
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    entrar,
    plantilla_con_cuentas,
    protegida,
)

RAIZ = "/v1/aprobaciones"
ANA = "Ana <ana>"
RITA = "Rita <rita>"
MARTES = datetime(2026, 10, 20, 10, 30)
MIERCOLES = datetime(2026, 10, 21, 11, 15)
CERRADO = "Este envío ya tiene dictamen o fue retirado."
SIN_ENVIO = "No se encontró ese envío."
SIN_NOTAS = "Escriba las notas: son obligatorias para devolver o aprobar con observaciones."
INTEGRO = "Rastro de aprobaciones íntegro."
MENSAJE_FORMA = (
    "Revise lo enviado: la obra y la versión van como texto, el dictamen es aprobada, aprobada "
    "con observaciones o devuelta, y las notas admiten hasta 2000 caracteres."
)
MENSAJE_BASE = "No se pudo leer o guardar la aprobación en la carpeta de trabajo."
MENSAJE_CON_CLAVE = "Esta acción se hace entrando con su cuenta, no con la clave de API."


def _aplicacion() -> FastAPI:
    aplicacion = FastAPI()
    aplicacion.add_exception_handler(HTTPException, manejar_http_exception)
    aplicacion.include_router(sesion.router)
    aplicacion.include_router(casos.router)
    aplicacion.include_router(rutas.router)
    proteger(aplicacion)
    return aplicacion


APLICACION = _aplicacion()


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_aprobaciones")
    vivienda, empresa = carpeta / "vivienda.db", carpeta / "silice.db"
    preparar_base(empresa)
    preparar_base(vivienda)
    motor = crear_motor(f"sqlite:///{vivienda.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            obra = sembrar_vivienda(s, usuario=ANA)
            guardar_version(s, obra, "VIV-002", usuario=ANA, cantidades={"OBRA-01": "90"})
    finally:
        motor.dispose()
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "vivienda.db": vivienda,
        "silice.db": empresa,
    }


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos_dir = config.carpeta_casos()
    casos_dir.mkdir(parents=True, exist_ok=True)
    for nombre in ("vivienda.db", "silice.db"):
        (casos_dir / nombre).write_bytes(_plantillas[nombre].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    _reloj(monkeypatch, MARTES)
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _reloj(monkeypatch: pytest.MonkeyPatch, cuando: datetime) -> None:
    monkeypatch.setattr(rutas, "ahora", lambda: cuando)


def _vivienda() -> Path:
    return config.carpeta_casos() / "vivienda.db"


# --- las cuentas ----------------------------------------------------------------------------------


@pytest.fixture
def ana() -> tuple[TestClient, str]:
    """Ana (arma) dentro y trabajando en `vivienda.db`."""
    navegador, ficha = con_cuenta(APLICACION, "ana")
    elegida = navegador.post(
        "/v1/casos/actual", json={"nombre": "vivienda.db"}, headers=protegida(ficha)
    )
    assert elegida.status_code == 200, elegida.text
    return navegador, ficha


@pytest.fixture
def rita() -> tuple[TestClient, str]:
    """Rita (revisa) dentro, en la carpeta de la empresa."""
    return con_cuenta(APLICACION, "rita")


def _enviar(cuenta, version: str = "VIV-001", nota: str = "Primera entrega"):
    navegador, ficha = cuenta
    return navegador.post(
        RAIZ,
        json={"proyecto": OBRA, "version": version, "nota": nota},
        headers=protegida(ficha),
    )


def _abrir(cuenta, envio_id: int, caso: str = "vivienda.db"):
    navegador, ficha = cuenta
    return navegador.post(
        f"{RAIZ}/abrir", json={"caso": caso, "envio_id": envio_id}, headers=protegida(ficha)
    )


def _dictaminar(cuenta, envio_id: int, resultado: str, notas: str = ""):
    navegador, ficha = cuenta
    return navegador.post(
        f"{RAIZ}/{envio_id}/dictamen",
        json={"resultado": resultado, "notas": notas},
        headers=protegida(ficha),
    )


def _sin_cache(respuesta) -> None:
    assert respuesta.headers.get("cache-control") == "no-store", respuesta.headers


# --- oráculos leídos con sqlite3 ------------------------------------------------------------------


def _renglones(version: str) -> list[tuple[str, str, str, str, str, str]]:
    with closing(sqlite3.connect(_vivienda())) as conexion:
        return conexion.execute(
            "SELECT ic.codigo_partida, ic.descripcion, ic.unidad, pp.cantidad, "
            "pp.precio_unitario, pp.total FROM partida_presupuestada pp "
            "JOIN item_computo ic ON ic.id = pp.item_computo_id "
            "JOIN presupuesto p ON p.id = pp.presupuesto_id "
            "WHERE p.codigo = ? ORDER BY pp.orden",
            (version,),
        ).fetchall()


def _texto(valor: str) -> str:
    return format(Decimal(valor), "f")


def _total(version: str) -> str:
    return format(sum((Decimal(r[5]) for r in _renglones(version)), Decimal(0)), "f")


def _fila(envio_id: int, **campos) -> dict:
    base = {
        "caso": "vivienda.db",
        "envio_id": envio_id,
        "proyecto": "1",
        "obra": OBRA,
        "version": "VIV-001",
        "total": _total("VIV-001"),
        "moneda": "Bs",
        "estado": "en_aprobacion",
        "enviado_por": ANA,
        "enviado_el": "2026-10-20T10:30:00",
        "dictamen_por": None,
        "dictamen_el": None,
        "nota": "Primera entrega",
        "notas": "",
        "armo": False,
    }
    return {**base, **campos}


# --- enviar, ver por aprobar, abrir y dictaminar --------------------------------------------------


def test_ana_envia_y_rita_lo_ve_por_aprobar_desde_otra_carpeta(ana, rita) -> None:
    enviado = _enviar(ana)
    assert enviado.status_code == 201, enviado.text
    assert enviado.json() == {"id": 1, "estado": "en_aprobacion", "retirada": None}
    _sin_cache(enviado)

    pendientes = rita[0].get(f"{RAIZ}/pendientes")
    assert pendientes.status_code == 200, pendientes.text
    assert pendientes.json() == [_fila(1)]
    _sin_cache(pendientes)


def test_enviar_otra_version_retira_la_pendiente(ana) -> None:
    _enviar(ana)
    otra = _enviar(ana, "VIV-002", nota="")
    assert otra.status_code == 201
    assert otra.json() == {"id": 3, "estado": "en_aprobacion", "retirada": "VIV-001"}


def test_rita_abre_el_envio_y_ve_lo_que_aprueba_en_solo_lectura(ana, rita) -> None:
    _enviar(ana)
    abierto = _abrir(rita, 1)
    assert abierto.status_code == 200, abierto.text
    assert abierto.json() == {"caso": "vivienda.db"}
    assert rita[0].get("/v1/casos").json()["actual"]["nombre"] == "vivienda.db"

    respuesta = rita[0].get(f"{RAIZ}/1")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    renglones = _renglones("VIV-001")
    claves = ("codigo", "descripcion", "unidad", "cantidad")
    assert [tuple(p[c] for c in claves) for p in cuerpo["partidas"]] == [
        (codigo, descripcion, unidad, cantidad)
        for codigo, descripcion, unidad, cantidad, *_ in PARTIDAS
    ]  # fmt: skip
    assert [(p["precio_unitario"], p["total"]) for p in cuerpo["partidas"]] == [
        (_texto(r[4]), _texto(r[5])) for r in renglones
    ]
    assert cuerpo["total"] == _total("VIV-001")
    assert isinstance(cuerpo["total"], str)
    assert (cuerpo["proyecto"], cuerpo["obra"], cuerpo["version"], cuerpo["moneda"]) == (
        "1",
        OBRA,
        "VIV-001",
        "Bs",
    )
    assert cuerpo["estado"] == "en_aprobacion"
    assert cuerpo["envio"] == {"por": ANA, "el": "2026-10-20T10:30:00", "nota": "Primera entrega"}
    assert cuerpo["rastro"] == {"integro": True, "mensaje": INTEGRO}
    assert cuerpo["armo"] is False
    with closing(sqlite3.connect(_vivienda())) as conexion:
        severidades = [
            s
            for (s,) in conexion.execute(
                "SELECT h.severidad FROM hallazgo h JOIN presupuesto p ON p.id = h.presupuesto_id "
                "WHERE p.codigo = 'VIV-001'"
            )
        ]
    assert cuerpo["hallazgos"]["error"] == sum(1 for s in severidades if s >= 3)
    assert cuerpo["hallazgos"]["advertencia"] == severidades.count(2)
    assert cuerpo["hallazgos"]["info"] == severidades.count(1)
    assert len(cuerpo["hallazgos"]["lista"]) == len(severidades)
    _sin_cache(respuesta)


def test_rita_devuelve_y_ana_ve_la_devolucion_aun_tras_reiniciar(ana, rita, monkeypatch) -> None:
    """Foco 3: el dictamen vuelve, aunque se olviden las fichas y se cierren los motores."""
    _enviar(ana)
    _abrir(rita, 1)
    _reloj(monkeypatch, MIERCOLES)
    devuelto = _dictaminar(rita, 1, "devuelta", "Falta el acero de la losa.")
    assert devuelto.status_code == 201, devuelto.text
    assert devuelto.json() == {"id": 2, "estado": "devuelta"}

    devuelta = _fila(
        1,
        estado="devuelta",
        dictamen_por=RITA,
        dictamen_el="2026-10-21T11:15:00",
        notas="Falta el acero de la losa.",
    )
    assert ana[0].get(f"{RAIZ}/mias").json() == [devuelta]

    caso_web.olvidar_todo()
    dependencias.cerrar_motores()
    instalacion.cerrar_motores()
    navegador = ana[0]
    assert entrar(navegador, "ana").status_code == 200  # la carpeta recordada vuelve

    assert navegador.get(f"{RAIZ}/mias").json() == [devuelta]
    obra = navegador.get(RAIZ, params={"proyecto": OBRA})
    assert obra.status_code == 200, obra.text
    cuerpo = obra.json()
    assert cuerpo["rastro"] == {"integro": True, "mensaje": INTEGRO}
    assert cuerpo["fases"] == "VIV-001 devuelta"
    assert cuerpo["versiones"] == {
        "VIV-001": {
            "estado": "devuelta",
            "por": RITA,
            "el": "2026-10-21T11:15:00",
            "notas": "Falta el acero de la losa.",
            "armo": False,
        },
        "VIV-002": {"estado": "guardada", "por": None, "el": None, "notas": "", "armo": False},
    }
    assert [(e["id"], e["tipo"], e["version"], e["resultado"]) for e in cuerpo["eventos"]] == [
        (1, "envio", "VIV-001", None),
        (2, "dictamen", "VIV-001", "devuelta"),
    ]
    _sin_cache(obra)


def test_dos_dictamenes_seguidos_el_segundo_es_409(ana, rita) -> None:
    _enviar(ana)
    _abrir(rita, 1)
    assert _dictaminar(rita, 1, "aprobada").status_code == 201
    segundo = _dictaminar(ana, 1, "devuelta", "Tarde.")
    assert segundo.status_code == 409
    assert segundo.json() == {"detalle": CERRADO}


def test_dos_dictamenes_a_la_vez_el_segundo_espera_y_recibe_409(
    ana, rita, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Foco 3 con dos hilos: el dictamen de Rita ya tomó la carpeta (BEGIN IMMEDIATE) y leyó el
    último eslabón cuando llega el de Ana. El de Ana espera el bloqueo de escritura, NO lee el
    envío abierto mientras tanto (no llega a leer el eslabón) y, al entrar, ve el envío cerrado:
    409 con el mensaje de la regla y un solo dictamen en el rastro."""
    _enviar(ana)
    _abrir(rita, 1)
    real = aprobaciones._cabeza
    leidas: list[int] = []
    de_ana: dict = {}
    seguia_esperando: list[bool] = []

    def dictamen_de_ana() -> None:
        de_ana["respuesta"] = _dictaminar(ana, 1, "devuelta", "Tarde.")

    def cabeza_con_carrera(sesion_caso, proyecto_id: int) -> str:
        leidas.append(proyecto_id)
        leida = real(sesion_caso, proyecto_id)
        if len(leidas) == 1:
            hilo = threading.Thread(target=dictamen_de_ana)
            hilo.start()
            hilo.join(timeout=1.0)
            seguia_esperando.append(hilo.is_alive())
            de_ana["hilo"] = hilo
        return leida

    monkeypatch.setattr(aprobaciones, "_cabeza", cabeza_con_carrera)
    primero = _dictaminar(rita, 1, "aprobada")
    de_ana["hilo"].join(timeout=10)

    assert primero.status_code == 201, primero.text
    assert seguia_esperando == [True]  # la carrera ocurrió: Ana esperaba el bloqueo
    segundo = de_ana["respuesta"]
    assert segundo.status_code == 409, segundo.text
    assert segundo.json() == {"detalle": CERRADO}
    assert len(leidas) == 1  # Ana nunca leyó el eslabón con el envío todavía abierto
    eventos = ana[0].get(RAIZ, params={"proyecto": OBRA}).json()["eventos"]
    assert [e["tipo"] for e in eventos] == ["envio", "dictamen"]


def test_ana_aprueba_su_propia_version_y_queda_rotulado(ana) -> None:
    _enviar(ana)
    assert ana[0].get(f"{RAIZ}/1").json()["armo"] is True
    assert _dictaminar(ana, 1, "aprobada").status_code == 201
    (fila,) = ana[0].get(f"{RAIZ}/mias").json()
    assert (fila["estado"], fila["dictamen_por"], fila["armo"]) == ("aprobada", ANA, True)
    versiones = ana[0].get(RAIZ, params={"proyecto": OBRA}).json()["versiones"]
    assert versiones["VIV-001"]["armo"] is True


def test_la_obra_dice_cual_es_su_ultima_version_aprobada(ana, rita) -> None:
    assert ana[0].get(RAIZ, params={"proyecto": OBRA}).json()["ultima_aprobada"] is None
    _enviar(ana)
    assert ana[0].get(RAIZ, params={"proyecto": OBRA}).json()["ultima_aprobada"] is None
    _abrir(rita, 1)
    assert _dictaminar(rita, 1, "aprobada_con_observaciones", "Revisar el flete").status_code == 201
    assert ana[0].get(RAIZ, params={"proyecto": OBRA}).json()["ultima_aprobada"] == "VIV-001"


def test_pendientes_repone_la_fila_borrada_de_la_carpeta_abierta(ana, rita) -> None:
    _enviar(ana)
    _abrir(rita, 1)
    with closing(sqlite3.connect(config.ruta_instalacion())) as conexion:
        conexion.execute("DELETE FROM mp_indice_aprobacion")
        conexion.commit()
    assert rita[0].get(f"{RAIZ}/pendientes").json() == [_fila(1)]


# --- la cifra «Por aprobar» de la mesa ------------------------------------------------------------


@pytest.mark.parametrize(
    "hoy,delta,marcada,dias",
    [
        (datetime(2026, 10, 23, 9, 0), "3", True, "3 días hábiles"),
        (datetime(2026, 10, 22, 9, 0), "2", False, "2 días hábiles"),
        (datetime(2026, 10, 21, 9, 0), "1", False, "1 día hábil"),
    ],
)
def test_la_cifra_por_aprobar_cuenta_los_dias_habiles_de_la_mas_antigua(
    ana, rita, monkeypatch, hoy, delta, marcada, dias
) -> None:
    _enviar(ana)  # martes 2026-10-20
    _reloj(monkeypatch, hoy)
    respuesta = rita[0].get(f"{RAIZ}/resumen")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "clave": "por_aprobar",
        "titulo": "Por aprobar",
        "actual": "1",
        "meta": "0",
        "delta": delta,
        "delta_pct": None,
        "sentido": "costo",
        "detalle": f"La más antigua: {OBRA} VIV-001, {dias}",
        "marcada": marcada,
    }
    _sin_cache(respuesta)


def test_sin_nada_por_aprobar_la_cifra_es_cero(rita) -> None:
    assert rita[0].get(f"{RAIZ}/resumen").json() == {
        "clave": "por_aprobar",
        "titulo": "Por aprobar",
        "actual": "0",
        "meta": "0",
        "delta": "0",
        "delta_pct": None,
        "sentido": "costo",
        "detalle": None,
        "marcada": False,
    }


# --- permisos y sesión ----------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["/pendientes", "/resumen", "/1"])
def test_el_administrador_no_aprueba(ruta: str) -> None:
    admin, _ = con_cuenta(APLICACION, "admin")
    respuesta = admin.get(f"{RAIZ}{ruta}")
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}
    _sin_cache(respuesta)


def test_rita_no_envia_ni_tiene_versiones_propias(rita) -> None:
    respuesta = _enviar(rita)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert rita[0].get(f"{RAIZ}/mias").status_code == 403
    # F4 2b: el rastro de la obra lo lee quien revisa (Versiones en solo lectura). Pasa el
    # acceso (no 403); en su carpeta, la de la empresa, esa obra no existe: 404.
    assert rita[0].get(RAIZ, params={"proyecto": OBRA}).status_code == 404


def test_sin_sesion_es_401() -> None:
    respuesta = cliente(APLICACION).get(f"{RAIZ}/pendientes")
    assert respuesta.status_code == 401
    _sin_cache(respuesta)


def test_enviar_sin_la_comprobacion_anti_csrf_es_403(ana) -> None:
    navegador, _ = ana
    respuesta = navegador.post(RAIZ, json={"proyecto": OBRA, "version": "VIV-001", "nota": ""})
    assert respuesta.status_code == 403
    assert navegador.get(f"{RAIZ}/mias").json() == []


@pytest.mark.parametrize(
    "metodo,ruta,cuerpo",
    [
        ("post", "/1/dictamen", {"resultado": "aprobada", "notas": ""}),
        ("post", "/abrir", {"caso": "vivienda.db", "envio_id": 1}),
        ("get", "/mias", None),
    ],
)
def test_con_la_clave_de_api_no_se_dictamina_ni_se_abre(metodo, ruta, cuerpo) -> None:
    integracion = TestClient(
        APLICACION,
        base_url=ANFITRION,
        client=IP_LOCAL,
        headers={CABECERA: crear_clave_de_prueba()},
    )
    respuesta = getattr(integracion, metodo)(
        f"{RAIZ}{ruta}", **({} if cuerpo is None else {"json": cuerpo})
    )
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_CON_CLAVE}


# --- errores --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"proyecto": OBRA, "version": "VIV-001", "nota": "secreto " * 300},
        {"proyecto": OBRA, "version": 1, "nota": ""},
        {"version": "VIV-001"},
    ],
)
def test_un_envio_mal_formado_es_422_sin_eco(ana, cuerpo) -> None:
    navegador, ficha = ana
    respuesta = navegador.post(RAIZ, json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_FORMA}
    assert "secreto" not in respuesta.text
    _sin_cache(respuesta)


def test_un_dictamen_desconocido_es_422_sin_eco(ana) -> None:
    _enviar(ana)
    respuesta = _dictaminar(ana, 1, "aprobadisima-secreta", "x")
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_FORMA}
    assert "secreta" not in respuesta.text


def test_devolver_sin_notas_es_422_con_el_mensaje_de_la_regla(ana) -> None:
    _enviar(ana)
    respuesta = _dictaminar(ana, 1, "devuelta", "   ")
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": SIN_NOTAS}


def test_reenviar_la_que_esta_en_aprobacion_es_409(ana) -> None:
    _enviar(ana)
    respuesta = _enviar(ana)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "La versión VIV-001 ya está en aprobación."}


def test_lo_que_no_existe_es_404(ana, rita) -> None:
    respuesta = ana[0].post(
        RAIZ,
        json={"proyecto": "Obra fantasma", "version": "VIV-001", "nota": ""},
        headers=protegida(ana[1]),
    )
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "No se encontró la obra «Obra fantasma»."}
    assert ana[0].get(f"{RAIZ}/999").json() == {"detalle": SIN_ENVIO}
    assert ana[0].get(f"{RAIZ}/999").status_code == 404
    assert _dictaminar(ana, 999, "aprobada").status_code == 404
    assert ana[0].get(RAIZ, params={"proyecto": "Obra fantasma"}).status_code == 404
    _enviar(ana)
    for caso, envio_id in (("vivienda.db", 999), ("otra.db", 1), ("../vivienda.db", 1)):
        abierto = _abrir(rita, envio_id, caso)
        assert abierto.status_code == 404, (caso, abierto.text)
        assert abierto.json() == {"detalle": SIN_ENVIO}
    assert rita[0].get("/v1/casos").json()["actual"]["nombre"] == "silice.db"  # no cambió


def test_un_fallo_de_la_base_es_503_sin_sql(ana, monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(*_args, **_kwargs):
        raise OperationalError(
            "SELECT mp_aprobacion_evento.id FROM mp_aprobacion_evento",
            {},
            Exception("C:/datos/casos/vivienda.db"),
        )

    monkeypatch.setattr(aprobaciones, "historial", falla)
    respuesta = ana[0].get(RAIZ, params={"proyecto": OBRA})
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detalle": MENSAJE_BASE}
    assert "SELECT" not in respuesta.text and "vivienda.db" not in respuesta.text
    _sin_cache(respuesta)


# --- menores del árbitro de T18 -------------------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        OperationalError("INSERT INTO mp_indice_aprobacion ...", {}, Exception("disco lleno")),
        ValueError("un fallo que no es de la base"),
        KeyError("otro fallo"),
    ],
)
def test_el_envio_vale_aunque_el_reflejo_falle_y_mias_lo_repone(
    ana, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """La carpeta ya confirmó el envío: un fallo al reflejar el índice no lo convierte en error;
    queda en el registro y la próxima lectura lo repone."""
    real = indice_aprobaciones.reflejar
    llamadas: list[int] = []

    def falla_la_primera_vez(*args, **kwargs):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise error
        return real(*args, **kwargs)

    monkeypatch.setattr(indice_aprobaciones, "reflejar", falla_la_primera_vez)
    enviado = _enviar(ana)
    assert enviado.status_code == 201, enviado.text
    with closing(sqlite3.connect(config.ruta_instalacion())) as conexion:
        assert conexion.execute("SELECT count(*) FROM mp_indice_aprobacion").fetchone() == (0,)
    assert ana[0].get(f"{RAIZ}/mias").json() == [_fila(1)]


def _alterar_un_renglon(version: str) -> None:
    with closing(sqlite3.connect(_vivienda())) as conexion:
        conexion.execute(
            "UPDATE partida_presupuestada SET cantidad = '81' WHERE presupuesto_id = "
            "(SELECT id FROM presupuesto WHERE codigo = ?) AND orden = "
            "(SELECT MIN(orden) FROM partida_presupuestada WHERE presupuesto_id = "
            "(SELECT id FROM presupuesto WHERE codigo = ?))",
            (version, version),
        )
        conexion.commit()


def test_el_detalle_dice_si_la_cadena_de_versiones_esta_integra(ana) -> None:
    _enviar(ana)
    assert ana[0].get(f"{RAIZ}/1").json()["cadena"] == {
        "integra": True,
        "mensaje": "Cadena íntegra: 2 versiones",
    }


def test_una_version_alterada_lo_dice_y_no_se_dictamina(ana) -> None:
    _enviar(ana)
    _alterar_un_renglon("VIV-001")

    assert ana[0].get(f"{RAIZ}/1").json()["cadena"] == {
        "integra": False,
        "mensaje": "Cadena rota en la versión VIV-001: su contenido no coincide con su huella; "
        "alguien cambió la base fuera del sistema. Revíselo con el administrador antes de "
        "entregar un paquete.",
    }
    dictamen = _dictaminar(ana, 1, "aprobada")
    assert dictamen.status_code == 409
    assert dictamen.json() == {
        "detalle": "No se puede dictaminar VIV-001: la cadena de versiones de esta obra está rota "
        "en la versión VIV-001 (su contenido no coincide con su huella). Revíselo con el "
        "administrador."
    }
    eventos = ana[0].get(RAIZ, params={"proyecto": OBRA}).json()["eventos"]
    assert [e["tipo"] for e in eventos] == ["envio"]


def test_con_la_cadena_rota_se_puede_devolver_con_notas(ana) -> None:
    _enviar(ana)
    _alterar_un_renglon("VIV-001")

    sin_notas = _dictaminar(ana, 1, "devuelta")
    assert sin_notas.status_code == 422
    assert sin_notas.json() == {"detalle": SIN_NOTAS}

    devuelta = _dictaminar(ana, 1, "devuelta", "La cadena se rompió; se rehace la versión.")
    assert devuelta.status_code == 201, devuelta.text
    eventos = ana[0].get(RAIZ, params={"proyecto": OBRA}).json()["eventos"]
    assert [(e["tipo"], e["resultado"]) for e in eventos] == [
        ("envio", None),
        ("dictamen", "devuelta"),
    ]
    assert ana[0].get(f"{RAIZ}/1").json()["estado"] == "devuelta"


def test_con_la_cadena_rota_aprobar_con_observaciones_sigue_en_409(ana) -> None:
    _enviar(ana)
    _alterar_un_renglon("VIV-001")

    dictamen = _dictaminar(ana, 1, "aprobada_con_observaciones", "Con notas igual.")
    assert dictamen.status_code == 409
    assert dictamen.json()["detalle"].startswith("No se puede dictaminar VIV-001: la cadena")
    eventos = ana[0].get(RAIZ, params={"proyecto": OBRA}).json()["eventos"]
    assert [e["tipo"] for e in eventos] == ["envio"]


def test_el_detalle_muestra_los_items_pendientes_sin_precio(ana) -> None:
    motor = crear_motor(f"sqlite:///{_vivienda().as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            guardar_version(
                s,
                s.scalars(select(models.Proyecto).where(models.Proyecto.nombre == OBRA)).one(),
                "VIV-003",
                extra=(("OBRA-99", "Partida sin APU de prueba", "m2", "10"),),
            )
    finally:
        motor.dispose()
    enviado = _enviar(ana, "VIV-003")
    assert enviado.status_code == 201, enviado.text

    cuerpo = ana[0].get(f"{RAIZ}/1").json()
    assert [p["pendiente"] for p in cuerpo["partidas"]] == [False] * 6 + [True]
    assert cuerpo["partidas"][-1] == {
        "codigo": "OBRA-99",
        "descripcion": "Partida sin APU de prueba",
        "unidad": "m2",
        "cantidad": "10",
        "precio_unitario": None,
        "total": None,
        "pendiente": True,
    }
    assert cuerpo["total"] == _total("VIV-003")


def test_una_version_alterada_no_se_envia(ana) -> None:
    _alterar_un_renglon("VIV-001")
    enviado = _enviar(ana)
    assert enviado.status_code == 409
    assert enviado.json() == {
        "detalle": "No se puede enviar VIV-001: la cadena de versiones de esta obra está rota en "
        "la versión VIV-001 (su contenido no coincide con su huella). Revíselo con el "
        "administrador."
    }
    assert ana[0].get(f"{RAIZ}/mias").json() == []


def test_el_fallo_del_reflejo_queda_en_el_registro(
    ana, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def falla(*_args, **_kwargs):
        raise ValueError("un fallo que no es de la base")

    monkeypatch.setattr(indice_aprobaciones, "reflejar", falla)
    with caplog.at_level(logging.WARNING, logger="api.rutas.aprobaciones"):
        assert _enviar(ana).status_code == 201
    avisos = [r for r in caplog.records if r.name == "api.rutas.aprobaciones"]
    assert [(r.levelno, r.getMessage()) for r in avisos] == [
        (logging.WARNING, "No se pudo reflejar el índice de aprobaciones de vivienda.db.")
    ]
    assert avisos[0].exc_info is not None and avisos[0].exc_info[0] is ValueError
