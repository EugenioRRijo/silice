"""Las bases de prueba de la 0.5.0 y su ficha, generadas con el código de `v0.5.0` (RV-3, PRU-H15).

Fijan que los archivos versionados son los de la ficha. Las pruebas de adopción (Tarea 5) los llevan
a `head` y comparan contra esta ficha, nunca contra un recálculo con el código nuevo.
"""

from __future__ import annotations

import hashlib

import pytest

from tests.fixtures import bases_prueba

FICHA = bases_prueba.ficha("0.5.0")
NOMBRE_OF001 = "OF-001: oficina con baño, cocineta y puestos (caso de prueba)"
NOMBRE_TI001 = "TI-001: telecomunicaciones (caso de prueba)"


def test_la_ficha_es_de_la_etiqueta_v0_5_0() -> None:
    assert (FICHA["version"], FICHA["etiqueta"]) == ("0.5.0", "v0.5.0")
    assert FICHA["commit"].startswith("8610053")
    assert sorted(FICHA["bases"]) == ["demo.db", "of001.db", "ti001.db"]


@pytest.mark.parametrize("nombre", bases_prueba.nombres("0.5.0"))
def test_cada_base_versionada_es_la_de_su_ficha(nombre: str) -> None:
    base = bases_prueba.carpeta_version("0.5.0") / nombre
    datos = FICHA["bases"][nombre]
    assert hashlib.sha256(base.read_bytes()).hexdigest() == datos["sha256_base"]
    assert datos["revision_alembic"] is None
    assert "alembic_version" not in datos["filas_por_tabla"]
    assert datos["presupuestos"], f"{nombre} no trae ningún presupuesto"
    for presupuesto in datos["presupuestos"]:
        assert presupuesto["total"] and len(presupuesto["huella_informe"]) == 64


def test_las_bases_cubren_el_espacio_la_demostracion_y_ti001() -> None:
    of001 = FICHA["bases"]["of001.db"]
    assert of001["filas_por_tabla"]["esp_ambientes"] > 0
    assert len(of001["filas_por_tabla"]) == 33  # 25 tablas de core/models + 8 esp_* (spec S5 §6.1)
    assert (NOMBRE_OF001, "001") in {(p["proyecto"], p["codigo"]) for p in of001["presupuestos"]}
    assert "DEMO-001" in {p["codigo"] for p in FICHA["bases"]["demo.db"]["presupuestos"]}
    ti001 = {(p["proyecto"], p["codigo"]) for p in FICHA["bases"]["ti001.db"]["presupuestos"]}
    assert (NOMBRE_TI001, "001") in ti001
