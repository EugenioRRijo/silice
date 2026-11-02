"""`POST /v1/libros/replica` responde el oráculo a mano (Sílice 1.2.0, Task 2.6; RF-111, RS2-1).

La misma salida esperada que fija `tests/unit/test_replica_oraculo.py` para `replicar_libro`
(`tests/fixtures/replica/libro_minimo.json`, escrita a mano desde `ORACULO.md`), ahora vista desde
la frontera HTTP: el cuerpo de la respuesta es `LibroVisual` serializado, con las claves enteras
de `anchos` y `altos` como texto. El `sha256` no se puede escribir a mano y se compara aparte,
calculado de los bytes que se suben.

Depende de la ruta de la Task 2.3b (`POST /v1/libros/replica`, entrada multipart con el campo
`libro`, como las demás rutas de `/v1/libros`, y clave de API).
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from operacion import config
from operacion.base_datos import Destino, preparar_base
from tests.fixtures.replica.libro_minimo import NOMBRE, libro_minimo
from tests.fixtures.replica.oraculo import cargar_json, diferencias


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    """Una `instalacion.db` ya migrada, una vez por módulo (mismo patrón que `test_api_libros.py`):
    la clave de API de la prueba vive en ella."""
    plantilla = tmp_path_factory.mktemp("plantilla_replica") / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path) -> None:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_migrada, destino)


def test_la_api_responde_el_oraculo(cliente) -> None:
    datos = libro_minimo()
    r = cliente.post("/v1/libros/replica", files={"libro": (NOMBRE, datos)})
    assert r.status_code == 200, r.text
    obtenido = r.json()
    assert obtenido.pop("sha256") == hashlib.sha256(datos).hexdigest()
    dif = diferencias(cargar_json(), obtenido)
    assert not dif, f"{len(dif)} diferencia(s) con el oráculo a mano:\n" + "\n".join(dif)
