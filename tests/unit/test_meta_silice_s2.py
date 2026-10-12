# tests/unit/test_meta_silice_s2.py
"""Parte S2 de la meta única de Sílice (spec S2 §8; plan 0.7.0, tarea 1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_silice import FASES, fases_hasta, partes, requisitos_exigidos, validar_partes
from scripts.meta_silice_s2 import (
    CIFRAS_S2,
    EXPEDIENTES,
    MEMORIAS_S2,
    PARES_S2,
    PARTE,
    REQUISITOS_S2,
    evaluar_base_070,
    evaluar_expedientes,
    evaluar_memorias_de_s1,
    evaluar_reglas_en_ers,
)

FASES_S2 = ("S2-0", "S2-1", "S2-2", "S2-3", "S2-4", "S2-5")


def test_la_0_7_0_abre_sus_seis_fases_despues_de_las_de_la_0_6_0():
    assert FASES["0.7.0"] == FASES_S2
    acumuladas = fases_hasta("0.7.0", "S2-1")
    assert acumuladas[: len(FASES["0.6.0"])] == FASES["0.6.0"]
    assert acumuladas[len(FASES["0.6.0"]) :] == ("S2-0", "S2-1")


def test_la_parte_s2_se_descubre_y_usa_fases_de_la_0_7_0():
    validar_partes((PARTE,))
    assert any(parte is PARTE for parte in partes())
    assert PARTE.requisitos == {"S2-0": REQUISITOS_S2}
    assert {par.fase for par in PARTE.pares_tdd} == set(FASES_S2[:5])
    assert [(c.codigo, c.fase) for c in PARTE.comprobaciones] == [
        ("S2-MEM", "S2-0"),
        ("S2-REGLAS", "S2-0"),
        ("S2-EXPEDIENTES", "S2-0"),
        ("S2-REG-S1", "S2-0"),
        ("S2-BASE-070", "S2-5"),
    ]


def test_los_requisitos_de_s2_son_los_diez_de_la_ers_y_se_exigen_desde_s2_0():
    assert REQUISITOS_S2 == (
        "UC-19", "UC-20", "RF-72", "RF-73", "RF-74", "RF-75", "RF-76", "RF-77", "RF-78", "RF-79",
        "RNF-15",
    )  # fmt: skip
    assert set(REQUISITOS_S2) <= set(requisitos_exigidos(partes(), fases_hasta("0.7.0", "S2-0")))
    assert not set(REQUISITOS_S2) & set(requisitos_exigidos(partes(), fases_hasta("0.6.0", "S1-5")))


def test_cada_par_nombra_una_prueba_y_un_modulo_distintos_en_su_fase():
    assert len({(p.prueba, p.implementacion) for p in PARES_S2}) == len(PARES_S2)
    assert all(p.prueba != p.implementacion for p in PARES_S2)
    nuevos = {p.implementacion for p in PARES_S2}
    assert {
        "core/models/control.py",
        "core/budget/valuaciones.py",
        "core/budget/valor_ganado.py",
        "core/budget/recuperacion.py",
        "core/budget/decision.py",
        "ui/control.py",
    } <= nuevos


def test_rnf_15_deja_dos_cifras_en_la_fase_s2_4():
    assert {(c.ruta, c.clave, c.fase) for c in CIFRAS_S2} == {
        ("scripts/_salida_rnf15.json", "mediana_registro_s", "S2-4"),
        ("scripts/_salida_rnf15.json", "mediana_opciones_s", "S2-4"),
    }


def test_las_memorias_de_s2_se_ligan_al_primer_modulo_del_valor_ganado():
    assert MEMORIAS_S2 == {"control_ob_s2.md": ("--", "core/budget/valor_ganado.py")}


def test_r13_y_r14_deben_estar_en_la_fila_de_rf_74():
    ers = "| RF‑74 | El sistema ejecutará **R13 y R14** sobre las valuaciones | UC-19 |\n"
    assert evaluar_reglas_en_ers(ers)[0] is Estado.OK
    assert evaluar_reglas_en_ers(ers.replace("R14", "R15"))[0] is Estado.FALLA
    assert evaluar_reglas_en_ers("| RF-73 | otra |\n")[0] is Estado.FALLA
    assert evaluar_reglas_en_ers(None)[0] is Estado.PENDIENTE


def test_los_tres_expedientes_se_exigen_como_encabezados():
    texto = "\n".join(f"## {e} Titulo\ntexto" for e in EXPEDIENTES)
    assert evaluar_expedientes(texto)[0] is Estado.OK
    assert evaluar_expedientes(texto.replace("## SL-E6", "texto SL-E6"))[0] is Estado.FALLA
    assert "SL-E6" in evaluar_expedientes(texto.replace("## SL-E6", "texto"))[1]
    assert evaluar_expedientes(None)[0] is Estado.PENDIENTE


@pytest.mark.parametrize(
    ("existe", "diff", "estado"),
    [
        (False, None, Estado.PENDIENTE),
        (True, None, Estado.PENDIENTE),
        (True, "", Estado.OK),
        (True, " \n", Estado.OK),
        (True, " tests/fixtures/memorias/s1_reajuste.md | 2 +-", Estado.FALLA),
    ],
)
def test_las_memorias_de_s1_no_se_editan_desde_v0_6_0(existe, diff, estado):
    assert evaluar_memorias_de_s1(existe, diff)[0] is estado


def test_la_base_070_exige_su_ficha_s2_db_y_la_huella_de_cada_base(tmp_path: Path):
    carpeta = tmp_path / "v0_7_0"
    assert evaluar_base_070(carpeta)[0] is Estado.PENDIENTE
    carpeta.mkdir()
    (carpeta / "s2.db").write_bytes(b"x")
    ficha = {
        "version": "0.7.0",
        "etiqueta": "v0.7.0",
        "commit": "abc1234",
        "bases": {"s2.db": {"sha256_base": hashlib.sha256(b"x").hexdigest()}},
    }
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    assert evaluar_base_070(carpeta)[0] is Estado.OK
    (carpeta / "s2.db").write_bytes(b"y")
    estado, detalle = evaluar_base_070(carpeta)
    assert estado is Estado.FALLA and "s2.db" in detalle
    ficha["bases"] = {}
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    assert "no trae la base s2.db" in evaluar_base_070(carpeta)[1]
    ficha["version"] = "0.6.0"
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    assert evaluar_base_070(carpeta)[0] is Estado.FALLA
