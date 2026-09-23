"""La meta del sprint del prototipo: que audite fases y no se salte ninguna."""

from __future__ import annotations

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_prototipo import (
    FASES,
    TITULOS,
    _archivos_de_fuentes,
    _generador_corpus_simulado,
    _referencias_ml_a_corpus,
    evaluar_p2_fuentes_referenciadas,
    evaluar_p11_ml_sin_corpus_simulado,
    main,
)


def test_toda_meta_declarada_tiene_titulo():
    for codigo in (codigo for metas in FASES.values() for codigo in metas):
        assert codigo in TITULOS, f"la meta {codigo} no tiene titulo"


def test_las_fases_van_de_p0_a_p5():
    assert list(FASES) == ["P0", "P1", "P2", "P3", "P4", "P5"]


def test_hasta_una_fase_inexistente_se_rechaza():
    with pytest.raises(SystemExit):
        main(["--hasta", "P9"])


# ------------------------------------------------------------------------------------------
# Ronda 1 de correcciones: un `.md` externo no fichado debe hacer fallar P2 (hallazgo 1) y
# `scripts/simular_corpus.py` debe ser detectado como generador del corpus simulado (hallazgo 2).
# ------------------------------------------------------------------------------------------


def test_p2_un_md_nuevo_no_fichado_hace_fallar(tmp_path):
    """Un `.md` archivado como fuente (no el indice ni la nota de campo) que el README no
    mencione debe dar FALLA: P2 no puede quedar ciega ante nuevas fuentes en Markdown.
    """
    raiz_fuentes = tmp_path / "fuentes"
    raiz_fuentes.mkdir()
    (raiz_fuentes / "README.md").write_text("indice", encoding="utf-8")
    (raiz_fuentes / "2026-09-16-nota-practica-apu.md").write_text("nota", encoding="utf-8")
    (raiz_fuentes / "captura_pagina_precios.md").write_text("captura archivada", encoding="utf-8")

    archivos = _archivos_de_fuentes(raiz_fuentes)
    assert "captura_pagina_precios.md" in archivos
    assert "README.md" not in archivos
    assert "2026-09-16-nota-practica-apu.md" not in archivos

    estado, evidencia = evaluar_p2_fuentes_referenciadas(archivos, "el readme no la menciona")
    assert estado is Estado.FALLA
    assert "captura_pagina_precios.md" in evidencia


def test_generador_corpus_detecta_simular_corpus(tmp_path):
    (tmp_path / "scripts").mkdir()
    ruta_generador = tmp_path / "scripts" / "simular_corpus.py"
    ruta_generador.write_text("# genera el corpus simulado", encoding="utf-8")

    assert _generador_corpus_simulado(tmp_path) == ruta_generador


def test_generador_corpus_ausente_da_none(tmp_path):
    assert _generador_corpus_simulado(tmp_path) is None


# ------------------------------------------------------------------------------------------
# Meta P11 (Sesion P4.3): sus tres ramas y la deteccion sobre una carpeta `ml/` temporal.
# ------------------------------------------------------------------------------------------


def test_p11_sin_generador_es_pendiente():
    estado, _ = evaluar_p11_ml_sin_corpus_simulado(None, ())
    assert estado is Estado.PENDIENTE


def test_p11_con_una_referencia_es_falla():
    estado, evidencia = evaluar_p11_ml_sin_corpus_simulado(
        "scripts/simular_corpus.py", ("ml/prediction/modelo.py",)
    )
    assert estado is Estado.FALLA
    assert "ml/prediction/modelo.py" in evidencia


def test_p11_sin_referencias_es_ok():
    estado, _ = evaluar_p11_ml_sin_corpus_simulado("scripts/simular_corpus.py", ())
    assert estado is Estado.OK


def test_referencias_ml_a_corpus_detecta_un_modulo_de_un_ml_temporal(tmp_path):
    """La carpeta `ml/` vive fuera del repositorio: la ruta relativa se calcula respecto de su
    padre, no de `RAIZ` (hecho verificado 11), y se reporta como `ml/<archivo>`."""
    raiz_ml = tmp_path / "ml"
    (raiz_ml / "prediction").mkdir(parents=True)
    (raiz_ml / "prediction" / "entrena.py").write_text(
        "from scripts.simular_corpus import generar_corpus\n", encoding="utf-8"
    )
    (raiz_ml / "limpio.py").write_text("VALOR = 1\n", encoding="utf-8")
    generador = tmp_path / "scripts" / "simular_corpus.py"

    assert _referencias_ml_a_corpus(raiz_ml, generador) == ("ml/prediction/entrena.py",)
