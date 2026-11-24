"""`/v1/libros/auditoria` agrupa los hallazgos por causa raíz y aparta los «no aplicable».

Campos aditivos de la respuesta: `causas` (cada una con las posiciones de sus casos en
`hallazgos`) y `no_aplicables` (posiciones de los avisos de regla no aplicable, R2 y R7 cuando el
libro no trae curva ni plan). `hallazgos` no cambia. Libros sintéticos: ningún dato real.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from operacion import config
from operacion.base_datos import Destino, preparar_base
from scripts.libro_ficticio_con_errores import construir
from tests.fixtures.libros_empresa import libro_limpio


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    plantilla = tmp_path_factory.mktemp("plantilla_causas") / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path) -> None:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_migrada, destino)


def _auditar(cliente, datos: bytes) -> dict:
    r = cliente.post("/v1/libros/auditoria", files={"libro": ("libro.xlsx", datos)},
                     data={"fecha_devolucion": "2026-11-23"})
    assert r.status_code == 200, r.text
    return r.json()


def test_cada_hallazgo_queda_en_una_causa_o_entre_los_no_aplicables(cliente) -> None:
    cuerpo = _auditar(cliente, construir())
    hallazgos, causas = cuerpo["hallazgos"], cuerpo["causas"]
    no_aplicables = cuerpo["no_aplicables"]
    posiciones = [i for causa in causas for i in causa["indices"]] + no_aplicables
    assert sorted(posiciones) == list(range(len(hallazgos)))  # cada uno, una sola vez
    assert len(causas) < len(hallazgos) - len(no_aplicables)  # el libro repite causas
    for causa in causas:
        assert {hallazgos[i]["codigo"] for i in causa["indices"]} == {causa["codigo"]}
        assert causa["ocurrencias"] == len(causa["indices"])
        assert causa["descripcion"] == hallazgos[causa["indices"][0]]["descripcion"]
    assert sorted(hallazgos[i]["codigo"] for i in no_aplicables) == ["R2", "R7"]


def test_cada_causa_trae_su_traza_celdas_observado_y_esperado(cliente) -> None:
    # El economista juzga una causa sin abrir el código: dónde está y qué valor esperaba Sílice
    # frente al que encontró. En el libro ficticio, la partida 1 guarda un P.U. de 999,99 (F1).
    cuerpo = _auditar(cliente, construir())
    hallazgos = cuerpo["hallazgos"]
    for causa in cuerpo["causas"]:
        esperadas = [hallazgos[i]["celda"] for i in causa["indices"] if hallazgos[i]["celda"]]
        assert causa["celdas"] == list(dict.fromkeys(esperadas))
    f1 = next(c for c in cuerpo["causas"] if c["codigo"] == "F1")
    assert f1["observado"] is not None and f1["esperado"] is not None
    assert f1["observado"] != f1["esperado"]
    assert "999.99" in f1["observado"]


def test_el_libro_limpio_no_tiene_causas_y_aparta_r2_y_r7(cliente) -> None:
    cuerpo = _auditar(cliente, libro_limpio().datos)
    assert cuerpo["causas"] == []
    assert sorted(cuerpo["hallazgos"][i]["codigo"] for i in cuerpo["no_aplicables"]) == ["R2", "R7"]
