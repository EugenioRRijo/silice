"""Parte S1 de la meta unica de Silice (spec S1 §9.4; plan 0.6.0, seccion C, tarea 1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.meta_alpha import Estado
from scripts.meta_silice import partes, validar_partes
from scripts.meta_silice_s1 import (
    MEMORIAS_S1,
    PARTE,
    REQUISITOS_S1,
    evaluar_base_060,
    evaluar_fuente_bcv,
)


def test_la_parte_s1_se_descubre_y_usa_fases_de_la_0_6_0() -> None:
    validar_partes((PARTE,))
    assert any(parte is PARTE for parte in partes())
    assert PARTE.requisitos == {"S1-0": REQUISITOS_S1}
    assert {par.fase for par in PARTE.pares_tdd} == {"S1-0", "S1-1", "S1-2", "S1-3", "S1-4"}
    assert [(c.codigo, c.fase) for c in PARTE.comprobaciones] == [
        ("S1-MEM", "S1-0"),
        ("S1-FUENTE", "S1-0"),
        ("S1-BASE-060", "S1-5"),
    ]


def test_los_once_requisitos_y_las_cuatro_memorias() -> None:
    assert REQUISITOS_S1 == (
        "UC-17",
        "UC-18",
        "RF-64",
        "RF-65",
        "RF-66",
        "RF-67",
        "RF-68",
        "RF-69",
        "RF-70",
        "RF-71",
        "RNF-14",
    )
    assert sorted(MEMORIAS_S1) == [
        "s1_conversion.md",
        "s1_precios_empresa.md",
        "s1_reajuste.md",
        "s1_reajuste_por_partida.md",
    ]


def test_la_fuente_del_bcv_entra_antes_que_el_primer_interprete() -> None:
    assert evaluar_fuente_bcv(False, False, None)[0] is Estado.FALLA
    assert evaluar_fuente_bcv(True, False, None)[0] is Estado.OK
    assert evaluar_fuente_bcv(True, True, None)[0] is Estado.PENDIENTE
    assert evaluar_fuente_bcv(True, True, False)[0] is Estado.FALLA
    assert evaluar_fuente_bcv(True, True, True)[0] is Estado.OK


def test_la_base_0_6_0_exige_su_ficha_y_la_huella_de_cada_base(tmp_path: Path) -> None:
    assert evaluar_base_060(tmp_path / "v0_6_0")[0] is Estado.PENDIENTE
    carpeta = tmp_path / "v0_6_0"
    carpeta.mkdir()
    (carpeta / "s1.db").write_bytes(b"x")
    ficha = {
        "version": "0.6.0",
        "etiqueta": "v0.6.0",
        "commit": "abc1234",
        "bases": {"s1.db": {"sha256_base": hashlib.sha256(b"x").hexdigest()}},
    }
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    assert evaluar_base_060(carpeta)[0] is Estado.OK
    (carpeta / "s1.db").write_bytes(b"y")
    estado, detalle = evaluar_base_060(carpeta)
    assert estado is Estado.FALLA and "s1.db" in detalle


def test_la_ers_define_los_once_requisitos_y_una_ers_sin_ellos_falla() -> None:
    from scripts.meta_silice import evaluar_requisitos

    raiz = Path(__file__).resolve().parents[2]
    ers = (raiz / "docs" / "ERS.md").read_text(encoding="utf-8")
    assert evaluar_requisitos(ers, REQUISITOS_S1)[0] is Estado.OK
    # una mencion suelta no define: la meta exige el encabezado, la fila o la celda
    estado, detalle = evaluar_requisitos("Se menciona UC-17 y RF-64 sin definirlos.", REQUISITOS_S1)
    assert estado is Estado.FALLA and "RNF-14" in detalle and "UC-18" in detalle


def test_la_base_060_rechaza_una_ficha_de_otra_version(tmp_path: Path) -> None:
    (tmp_path / "ficha.json").write_text(
        json.dumps({"version": "0.5.0", "etiqueta": "v0.5.0", "bases": {}}), encoding="utf-8"
    )
    assert evaluar_base_060(tmp_path)[0] is Estado.FALLA
    (tmp_path / "ficha.json").write_text(
        json.dumps({"version": "0.6.0", "etiqueta": "v0.6.0", "bases": {}}), encoding="utf-8"
    )
    assert evaluar_base_060(tmp_path)[0] is Estado.FALLA  # sin bases no hay huella que comprobar
