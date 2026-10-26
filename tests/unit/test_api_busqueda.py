"""`GET /v1/buscar/partidas`: el buscador de partidas del catálogo (Tarea 10 del plan de montar un
presupuesto; diseño de autocompletado 2026-10-21 §5.1, §5.2, §5.4 y §8.1).

Contrato: `?q=&dominio=&limite=` con `LEER_PROYECTO` (arma y revisa; el administrador recibe 403);
`{"rotulo": "Partidas del catálogo", "resultados": [{clave, codigo, descripcion, unidad, dominio,
tiene_composicion}], "hay_mas"}`; `q` de menos de 2 letras → 200 vacío; `limite` de 1 a 50 (por
omisión 20); `q` de más de 80 caracteres, un dominio que no existe o un límite fuera de rango → 422
con un mensaje fijo que no repite lo enviado; `Cache-Control: no-store` en toda respuesta; un fallo
de la base → 503 sin SQL ni rutas.

El router se monta aquí en una aplicación propia con los manejadores de `api.main`, porque
`api/main.py` es un archivo compartido que integra el orquestador; la cadena de acceso de la
aplicación real la vigila `tests/unit/test_api_acceso_por_ruta.py` cuando gana su fila.

Caso: la línea base (`scripts.seed.sembrar`, cinco partidas civiles con APU) más nueve partidas
ficticias sin composición, «Partida ficticia de prueba 01» a «09» (`PRU-01` a `PRU-09`). Oráculos
leídos a mano de las descripciones de `tests/fixtures/apu_linea_base.py`:

- «tub»: LB-01-EXC («Excavación en tierra para zanja de tubería…») y LB-02-TUB («Suministro e
  instalación de tubería PVC…»); las dos tienen rango 3 (la palabra «tubería» empieza por «tub») y
  «excavacion…» < «suministro…». El código LB-02-TUB contiene «tub» pero no empieza por él.
- «tanquillas»: LB-03-ENC («Encofrado…»), LB-01-EXC («Excavación…») y LB-04-CON («Vaciado…»),
  todas de rango 3, en ese orden alfabético.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.main import manejar_http_exception
from api.proteccion import proteger
from api.rutas import busqueda
from core.catalog import abrir_sesion, crear_motor
from core.models import Partida
from operacion.base_datos import preparar_base
from scripts.seed import sembrar
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)

RUTA = "/v1/buscar/partidas"
ROTULO = "Partidas del catálogo"
MENSAJE_FORMA = (
    "La búsqueda no es válida: el texto admite hasta 80 caracteres, el dominio es civil, "
    "telecom, industrial o sistemas y el límite va de 1 a 50."
)
MENSAJE_BASE = "No se pudo leer el catálogo de la carpeta de trabajo."
VACIO = {"rotulo": ROTULO, "resultados": [], "hay_mas": False}
EXCAVACION = {
    "clave": "partida:LB-01-EXC",
    "codigo": "LB-01-EXC",
    "descripcion": "Excavación en tierra para zanja de tubería y fosos de tanquillas",
    "unidad": "m3",
    "dominio": "civil",
    "tiene_composicion": True,
}
TUBERIA = {
    "clave": "partida:LB-02-TUB",
    "codigo": "LB-02-TUB",
    "descripcion": "Suministro e instalación de tubería PVC de 4 pulgadas",
    "unidad": "pieza",
    "dominio": "civil",
    "tiene_composicion": True,
}


def _aplicacion() -> FastAPI:
    """El router de búsqueda con el mismo formato de error (`{"detalle": ...}`) y la misma
    protección que `api.main.app`."""
    aplicacion = FastAPI()
    aplicacion.add_exception_handler(HTTPException, manejar_http_exception)
    aplicacion.include_router(busqueda.router)
    proteger(aplicacion)
    return aplicacion


APLICACION = _aplicacion()


def _caso(ruta: Path) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            for n in range(1, 10):
                sesion.add(
                    Partida(
                        codigo=f"PRU-{n:02d}",
                        descripcion=f"Partida ficticia de prueba {n:02d}",
                        unidad="m2",
                        dominio="civil",
                    )
                )
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("api_busqueda"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    copiar_instalacion(_plantilla)
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    ruta = _caso(tmp_path / "caso.db")
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


@pytest.fixture
def ana() -> TestClient:
    return con_cuenta(APLICACION, "ana")[0]


def _sin_cache(respuesta) -> None:
    assert respuesta.headers.get("cache-control") == "no-store", respuesta.headers


# --- resultados -----------------------------------------------------------------------------------


def test_busca_en_codigo_y_descripcion_y_ordena_por_relevancia(ana: TestClient) -> None:
    respuesta = ana.get(RUTA, params={"q": "tub"})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"rotulo": ROTULO, "resultados": [EXCAVACION, TUBERIA], "hay_mas": False}
    _sin_cache(respuesta)


def test_el_codigo_exacto_va_primero(ana: TestClient) -> None:
    respuesta = ana.get(RUTA, params={"q": "lb-02-tub"})
    assert respuesta.json()["resultados"] == [TUBERIA]


def test_una_partida_sin_composicion_se_ofrece_y_lo_dice(ana: TestClient) -> None:
    respuesta = ana.get(RUTA, params={"q": "PRU-03"})
    assert respuesta.json()["resultados"] == [
        {
            "clave": "partida:PRU-03",
            "codigo": "PRU-03",
            "descripcion": "Partida ficticia de prueba 03",
            "unidad": "m2",
            "dominio": "civil",
            "tiene_composicion": False,
        }
    ]


@pytest.mark.parametrize("q", ["t", "", "  t  "])
def test_menos_de_dos_letras_responde_vacio(ana: TestClient, q: str) -> None:
    respuesta = ana.get(RUTA, params={"q": q})
    assert respuesta.status_code == 200
    assert respuesta.json() == VACIO


def test_sin_q_responde_vacio(ana: TestClient) -> None:
    assert ana.get(RUTA).json() == VACIO


def test_el_limite_es_por_grupo_y_dice_si_hay_mas(ana: TestClient) -> None:
    ocho = ana.get(RUTA, params={"q": "ficticia", "limite": 8}).json()
    assert [r["codigo"] for r in ocho["resultados"]] == [f"PRU-{n:02d}" for n in range(1, 9)]
    assert ocho["hay_mas"] is True
    por_omision = ana.get(RUTA, params={"q": "ficticia"}).json()  # 20 por omisión: caben las 9
    assert len(por_omision["resultados"]) == 9
    assert por_omision["hay_mas"] is False
    dos = ana.get(RUTA, params={"q": "tanquillas", "limite": 2}).json()
    assert [r["codigo"] for r in dos["resultados"]] == ["LB-03-ENC", "LB-01-EXC"]
    assert dos["hay_mas"] is True
    tres = ana.get(RUTA, params={"q": "tanquillas", "limite": 3}).json()
    assert [r["codigo"] for r in tres["resultados"]] == ["LB-03-ENC", "LB-01-EXC", "LB-04-CON"]
    assert tres["hay_mas"] is False


def test_el_dominio_filtra(ana: TestClient) -> None:
    assert ana.get(RUTA, params={"q": "tub", "dominio": "telecom"}).json() == VACIO
    civil = ana.get(RUTA, params={"q": "tub", "dominio": "civil"}).json()
    assert civil["resultados"] == [EXCAVACION, TUBERIA]


def test_sin_coincidencias_responde_vacio(ana: TestClient) -> None:
    assert ana.get(RUTA, params={"q": "fusionadora"}).json() == VACIO


# --- validación sin eco ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "parametros",
    [
        {"q": "X" * 81},
        {"q": "tub", "limite": 0},
        {"q": "tub", "limite": 51},
        {"q": "tub", "limite": "muchos"},
        {"q": "tub", "dominio": "<script>alert(1)</script>"},
    ],
)
def test_un_parametro_invalido_es_un_422_fijo_sin_eco(ana: TestClient, parametros: dict) -> None:
    respuesta = ana.get(RUTA, params=parametros)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_FORMA}
    assert "XXXX" not in respuesta.text
    assert "script" not in respuesta.text
    assert "muchos" not in respuesta.text
    _sin_cache(respuesta)


def test_ochenta_caracteres_si_se_admiten(ana: TestClient) -> None:
    assert ana.get(RUTA, params={"q": "X" * 80}).json() == VACIO


# --- acceso ---------------------------------------------------------------------------------------


def test_revisa_tambien_busca() -> None:
    rita = con_cuenta(APLICACION, "rita")[0]
    respuesta = rita.get(RUTA, params={"q": "tub"})
    assert respuesta.status_code == 200
    assert [r["codigo"] for r in respuesta.json()["resultados"]] == ["LB-01-EXC", "LB-02-TUB"]


def test_el_administrador_recibe_403() -> None:
    admin = con_cuenta(APLICACION, "admin")[0]
    respuesta = admin.get(RUTA, params={"q": "tub"})
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert "tub" not in respuesta.text
    _sin_cache(respuesta)


def test_sin_sesion_ni_clave_es_401() -> None:
    respuesta = cliente(APLICACION).get(RUTA, params={"q": "tub"})
    assert respuesta.status_code == 401
    _sin_cache(respuesta)


def test_con_clave_de_api_busca() -> None:
    integracion = TestClient(
        APLICACION,
        base_url=ANFITRION,
        client=IP_LOCAL,
        headers={CABECERA: crear_clave_de_prueba()},
    )
    respuesta = integracion.get(RUTA, params={"q": "tub"})
    assert respuesta.status_code == 200
    assert respuesta.json()["resultados"] == [EXCAVACION, TUBERIA]


# --- base que falla -------------------------------------------------------------------------------


def test_un_fallo_de_la_base_es_un_503_sin_sql_ni_rutas(
    ana: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def falla(*_args, **_kwargs):
        raise OperationalError(
            "SELECT partida.codigo FROM partida", {}, Exception("C:/datos/casos/caso.db")
        )

    monkeypatch.setattr(busqueda, "buscar_partidas", falla)
    respuesta = ana.get(RUTA, params={"q": "tub"})
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detalle": MENSAJE_BASE}
    assert "SELECT" not in respuesta.text
    assert "caso.db" not in respuesta.text
    _sin_cache(respuesta)
