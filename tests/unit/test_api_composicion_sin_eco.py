"""Los 422 de forma de `/v1/composicion/*` no repiten lo enviado (RM-4; deuda de la Tarea 3 que
cierra la Tarea 4 del plan de montar un presupuesto).

Hasta la Tarea 3 solo `prever` usaba `RutaSinEco`: `guardar`, `evaluar`, `referencia` y `similares`
devolvían el 422 de FastAPI, que trae cada valor rechazado en `input`, y la pantalla mostraba «El
programa de Sílice respondió con el estado 422» (su `detail` es una lista). Ahora todo el router
contesta `{"detalle": <mensaje fijo>}`: `guardar` con el mismo mensaje que `prever` (reciben el
mismo cuerpo) y las demás con el de omisión de `RutaSinEco`. Los 422 con motivo (sin condiciones,
composición inválida) no cambian: los vigila `tests/unit/test_api_composicion.py`.

La API se usa con una clave (como `tests/unit/test_api_composicion.py`) sobre una base temporal en
`tmp_path` preparada con `preparar_base` (nunca `data/`). Oráculos escritos a mano.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from operacion.base_datos import preparar_base
from tests.fixtures.claves_api import cliente_de_prueba
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

SECRETO = "valor-inventado-que-no-debe-volver"
MENSAJE_FORMA = (
    "La composición enviada no tiene la forma esperada: revise la cabecera, las tres tablas, la "
    "fecha y las condiciones."
)
MENSAJE_OMISION = "Los datos enviados no son válidos."


def _cuerpo(**extra) -> dict:
    return {
        "codigo": "FIC-1",
        "descripcion": "Partida ficticia",
        "unidad": "m2",
        "dominio": "civil",
        "rendimiento": "10",
        "materiales": [],
        "equipos": [],
        "mano_obra": [],
        "fecha": "2026-10-26",
        "condiciones": "Condiciones ficticias",
        **extra,
    }


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("api_composicion_sin_eco"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path) -> Iterator[None]:
    copiar_instalacion(_plantilla)
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
    with cliente_de_prueba() as cliente:
        yield cliente


def test_guardar_con_un_dominio_desconocido_es_422_sin_eco(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/guardar", json=_cuerpo(dominio=SECRETO))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_FORMA}
    assert SECRETO not in respuesta.text


def test_guardar_sin_fecha_valida_es_422_sin_eco(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/guardar", json=_cuerpo(fecha=SECRETO))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_FORMA}
    assert SECRETO not in respuesta.text


def test_evaluar_con_una_tabla_sin_forma_es_422_sin_eco(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/evaluar", json=_cuerpo(materiales=SECRETO))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_OMISION}
    assert SECRETO not in respuesta.text


def test_la_referencia_con_un_tipo_desconocido_es_422_sin_eco(api: TestClient) -> None:
    respuesta = api.get("/v1/composicion/referencia", params={"tipo": SECRETO, "q": "x"})
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_OMISION}
    assert SECRETO not in respuesta.text


def test_las_similares_con_un_dominio_desconocido_son_422_sin_eco(api: TestClient) -> None:
    respuesta = api.get(
        "/v1/composicion/similares", params={"dominio": SECRETO, "descripcion": "muro"}
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_OMISION}
    assert SECRETO not in respuesta.text


def test_prever_sigue_con_su_mensaje(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/prever", json=_cuerpo(dominio=SECRETO))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_FORMA}
    assert SECRETO not in respuesta.text
