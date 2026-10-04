"""Pruebas de scripts/meta_sf.py (meta del sprint final, SF0-SF5)."""

import json

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


def _ers_definida(guion="‑", sin=None):
    """ERS mínima que DEFINE cada requisito (UC por encabezado, RF y RNF por fila de tabla)."""
    lineas = [f"#### UC{guion}{n} — caso" for n in range(13, 17)]
    lineas += [f"| RF{guion}{n} | texto | Esencial |" for n in range(44, 64)]
    lineas += [f"| Seguridad | RNF{guion}{n} criterio | medida |" for n in range(11, 14)]
    return "\n".join(linea for linea in lineas if sin is None or sin not in linea)


def test_s1_ok_con_todos_los_uc_y_rf_nuevos():
    assert evaluar_s1_requisitos(_ers_definida())[0] is Estado.OK


def test_s1_acepta_guion_normal():
    assert evaluar_s1_requisitos(_ers_definida("-"))[0] is Estado.OK


def test_s1_falla_si_falta_un_requisito_y_pendiente_sin_ers():
    assert evaluar_s1_requisitos("#### UC‑13 — caso")[0] is Estado.FALLA
    assert evaluar_s1_requisitos(None)[0] is Estado.PENDIENTE


def test_s1_no_confunde_rf_44_con_rf_440():
    ers = _ers_definida(sin="RF‑44 |") + "\n| RF‑440 | otro | Esencial |"
    estado, detalle = evaluar_s1_requisitos(ers)
    assert estado is Estado.FALLA
    assert "RF-44" in detalle


def test_s1_falla_si_solo_se_menciona_sin_definir():
    ers = _ers_definida(sin="RF‑50 |") + "\nVer RF‑50 y UC‑13 en el texto."
    estado, detalle = evaluar_s1_requisitos(ers)
    assert estado is Estado.FALLA
    assert "RF-50" in detalle
    assert "UC-13" not in detalle


def test_titulos_igualan_la_spec_12_2():
    assert "SF1-SF2" in TITULOS["S3"]
    assert "todas" in TITULOS["S8"]


def test_s1_sobre_la_ers_real_y_json(capsys):
    assert main(["--hasta", "SF0"]) == 0
    capsys.readouterr()
    assert main(["--hasta", "SF0", "--json"]) == 0
    datos = json.loads(capsys.readouterr().out)
    assert "S1" in json.dumps(datos)


def test_main_devuelve_codigo_distinto_de_cero_con_pendientes(capsys):
    assert main(["--hasta", "SF1"]) == 1
    assert "S2" in capsys.readouterr().out
