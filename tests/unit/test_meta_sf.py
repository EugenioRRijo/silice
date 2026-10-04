"""Pruebas de scripts/meta_sf.py (meta del sprint final, SF0-SF5)."""

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_sf import FASES, TITULOS, evaluar_s1_requisitos, main, metas_hasta


def test_metas_hasta_acumula_fases_en_orden():
    assert metas_hasta("SF0") == list(FASES["SF0"])
    assert set(FASES["SF0"]) <= set(metas_hasta("SF3"))
    assert set(metas_hasta("SF5")) == set(TITULOS)


def test_metas_hasta_rechaza_fase_desconocida():
    with pytest.raises(ValueError):
        metas_hasta("SF9")


def test_toda_meta_de_las_fases_tiene_titulo():
    asignadas = {meta for metas in FASES.values() for meta in metas}
    assert asignadas == set(TITULOS)
    assert len(asignadas) == 10


def test_s1_ok_con_todos_los_uc_y_rf_nuevos():
    ers = (
        " ".join(f"UC‑{n}" for n in range(13, 17))
        + " "
        + " ".join(f"RF‑{n}" for n in range(44, 64))
    )
    ers += " RNF‑11 RNF‑12 RNF‑13"
    estado, _ = evaluar_s1_requisitos(ers)
    assert estado is Estado.OK


def test_s1_acepta_guion_normal():
    ers = (
        " ".join(f"UC-{n}" for n in range(13, 17))
        + " "
        + " ".join(f"RF-{n}" for n in range(44, 64))
    )
    ers += " RNF-11 RNF-12 RNF-13"
    assert evaluar_s1_requisitos(ers)[0] is Estado.OK


def test_s1_falla_si_falta_un_requisito_y_pendiente_sin_ers():
    assert evaluar_s1_requisitos("UC‑13")[0] is Estado.FALLA
    assert evaluar_s1_requisitos(None)[0] is Estado.PENDIENTE


def test_s1_no_confunde_rf_44_con_rf_440():
    ers = (
        " ".join(f"UC‑{n}" for n in range(13, 17))
        + " "
        + " ".join(f"RF‑{n}" for n in range(45, 64))
    )
    ers += " RF‑440 RNF‑11 RNF‑12 RNF‑13"
    estado, detalle = evaluar_s1_requisitos(ers)
    assert estado is Estado.FALLA
    assert "RF‑44" in detalle


def test_main_devuelve_codigo_distinto_de_cero_con_pendientes(capsys):
    assert main(["--hasta", "SF1"]) == 1
    assert "S2" in capsys.readouterr().out
