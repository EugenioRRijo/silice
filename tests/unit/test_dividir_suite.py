"""El reparto de la suite en tramos de CI es completo, sin repetidos y determinista."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts import dividir_suite, unir_junit

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("total", [1, 3, 4, 7])
def test_la_union_de_los_tramos_es_toda_la_suite_sin_repetidos(total: int) -> None:
    todos = dividir_suite.listar_archivos(RAIZ)
    unidos = [a for i in range(1, total + 1) for a in dividir_suite.tramo(i, total, RAIZ)]
    assert sorted(unidos) == todos
    assert len(unidos) == len(set(unidos))
    assert all(dividir_suite.tramo(i, total, RAIZ) for i in range(1, total + 1))


def test_el_reparto_es_determinista() -> None:
    assert dividir_suite.tramo(2, 4, RAIZ) == dividir_suite.tramo(2, 4, RAIZ)


def test_el_voraz_mayor_primero_balancea() -> None:
    pesos = {"a": 10.0, "b": 9.0, "c": 5.0, "d": 5.0, "e": 1.0}
    tramos = dividir_suite.repartir(pesos, 2)
    sumas = sorted(sum(pesos[a] for a in t) for t in tramos)
    assert sumas == [15.0, 15.0]
    assert sorted(a for t in tramos for a in t) == sorted(pesos)


def test_los_pesos_medidos_mandan_y_los_ausentes_pesan_la_media(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    for nombre in ("test_a.py", "test_b.py", "test_c.py"):
        (tmp_path / "tests" / nombre).write_text("x" * 5, encoding="utf-8")
    ruta = tmp_path / "pesos.json"
    ruta.write_text(json.dumps({"tests/test_a.py": 30, "tests/test_b.py": 10}), encoding="utf-8")
    archivos = dividir_suite.listar_archivos(tmp_path)
    pesos = dividir_suite.pesos_de(archivos, dividir_suite.cargar_pesos(ruta), tmp_path)
    assert pesos == {"tests/test_a.py": 30, "tests/test_b.py": 10, "tests/test_c.py": 20}
    assert dividir_suite.tramo(1, 2, tmp_path, ruta) == ["tests/test_a.py"]


def test_indice_fuera_de_rango() -> None:
    with pytest.raises(ValueError):
        dividir_suite.tramo(0, 3, RAIZ)
    with pytest.raises(ValueError):
        dividir_suite.tramo(4, 3, RAIZ)


def _junit(*casos: tuple[str, str, float]) -> str:
    cuerpo = "".join(f'<testcase classname="{c}" name="{n}" time="{t}"/>' for c, n, t in casos)
    return (
        f'<testsuites><testsuite name="pytest" tests="{len(casos)}" failures="0" errors="0" '
        f'skipped="0" time="1.5">{cuerpo}</testsuite></testsuites>'
    )


def test_unir_junit_suma_pruebas_y_exige_los_tramos_esperados() -> None:
    uno = _junit(("tests.unit.test_a", "t1", 1.0))
    dos = _junit(("tests.unit.test_b.TestX", "t2", 2.0), ("tests.unit.test_b", "t3", 1.0))
    unido = ET.fromstring(unir_junit.unir([uno, dos], esperados=2))
    suite = unido.find("testsuite")
    assert suite is not None and suite.get("tests") == "3"
    assert len(unido.findall(".//testcase")) == 3
    with pytest.raises(unir_junit.TramosFaltantesError):
        unir_junit.unir([uno], esperados=2)


def test_pesos_por_archivo_suma_por_modulo_incluidas_las_clases() -> None:
    texto = _junit(
        ("tests.unit.test_b.TestX", "t2", 2.0),
        ("tests.unit.test_b", "t3", 1.0),
        ("tests.unit.test_a", "t1", 0.5),
    )
    pesos = unir_junit.pesos_por_archivo(texto, ["tests/unit/test_a.py", "tests/unit/test_b.py"])
    assert pesos == {"tests/unit/test_a.py": 0.5, "tests/unit/test_b.py": 3.0}
