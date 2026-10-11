"""Parte S5 de la meta unica de Silice (spec S5 §12 y §13; plan 0.6.0, seccion B, tarea 7)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.meta_alpha import Estado
from scripts.meta_silice import partes, validar_partes
from scripts.meta_silice_s5 import BASES_050, PARTE, evaluar_base_050

RAIZ = Path(__file__).resolve().parents[2]


def test_la_parte_s5_se_descubre_y_usa_solo_la_fase_s5_1() -> None:
    validar_partes((PARTE,))
    assert any(parte is PARTE for parte in partes())
    assert PARTE.requisitos == {"S5-1": ("RF-96", "RNF-20")}
    assert {par.fase for par in PARTE.pares_tdd} == {"S5-1"}
    assert [(c.codigo, c.fase) for c in PARTE.comprobaciones] == [("S5-M3", "S5-1")]


def test_los_pares_nombran_archivos_del_repositorio() -> None:
    for par in PARTE.pares_tdd:
        assert (RAIZ / par.prueba).is_file(), par.prueba
        assert (RAIZ / par.implementacion).is_file(), par.implementacion


def _carpeta(tmp_path: Path, commit: str = "8610053abcdef") -> Path:
    carpeta = tmp_path / "v0_5_0"
    carpeta.mkdir()
    bases = {}
    for nombre in BASES_050:
        (carpeta / nombre).write_bytes(nombre.encode())
        bases[nombre] = {"sha256_base": hashlib.sha256(nombre.encode()).hexdigest()}
    ficha = {"version": "0.5.0", "etiqueta": "v0.5.0", "commit": commit, "bases": bases}
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    return carpeta


def test_la_base_de_prueba_0_5_0_es_la_de_la_etiqueta(tmp_path: Path) -> None:
    assert evaluar_base_050(tmp_path / "no")[0] is Estado.FALLA
    carpeta = _carpeta(tmp_path)
    assert evaluar_base_050(carpeta)[0] is Estado.OK
    (carpeta / "of001.db").write_bytes(b"otra")
    estado, detalle = evaluar_base_050(carpeta)
    assert estado is Estado.FALLA and "of001.db" in detalle


def test_una_ficha_de_otro_commit_falla(tmp_path: Path) -> None:
    estado, detalle = evaluar_base_050(_carpeta(tmp_path, commit="1234567"))
    assert estado is Estado.FALLA and "8610053" in detalle


def test_la_base_versionada_del_repositorio_pasa() -> None:
    assert evaluar_base_050(RAIZ / "tests" / "fixtures" / "bases" / "v0_5_0")[0] is Estado.OK
