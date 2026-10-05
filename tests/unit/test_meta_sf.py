"""Pruebas de scripts/meta_sf.py (meta del sprint final, SF0-SF5)."""

import json

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_sf import (
    FASES,
    TITULOS,
    contar_resultados,
    evaluar_s1_requisitos,
    evaluar_s2_memorias,
    evaluar_s3_especialidades,
    evaluar_s8_regresion,
    evaluar_s10_cobertura,
    main,
    metas_hasta,
    porcentaje_espacio,
)


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


def test_main_hasta_sf0_ok_y_sf2_aun_con_pendientes(capsys):
    assert main(["--hasta", "SF2"]) == 1  # S4 llega con SF2
    assert "S4" in capsys.readouterr().out


def test_s10_ok_en_la_frontera_80():
    estado, detalle = evaluar_s10_cobertura(80.0)
    assert estado is Estado.OK
    assert "80" in detalle


def test_s10_falla_justo_debajo_de_80():
    estado, detalle = evaluar_s10_cobertura(79.99)
    assert estado is Estado.FALLA
    assert "79,99" in detalle or "79.99" in detalle


def test_s10_pendiente_sin_dato_o_sin_adaptador():
    assert evaluar_s10_cobertura(None)[0] is Estado.PENDIENTE
    assert evaluar_s10_cobertura(95.0, existe_adaptador=False)[0] is Estado.PENDIENTE


def test_porcentaje_espacio_suma_solo_los_archivos_del_adaptador():
    texto = json.dumps(
        {
            "files": {
                "adapters/espacio/a.py": {"summary": {"covered_lines": 8, "num_statements": 10}},
                "adapters\\espacio\\b.py": {"summary": {"covered_lines": 2, "num_statements": 10}},
                "core/x.py": {"summary": {"covered_lines": 0, "num_statements": 100}},
            }
        }
    )
    assert porcentaje_espacio(texto) == 50.0
    assert porcentaje_espacio(json.dumps({"files": {}})) is None
    assert porcentaje_espacio("no es json") is None


def test_s10_no_ejecuta_pytest_dentro_de_la_meta(monkeypatch):
    import subprocess

    def prohibido(*a, **k):
        raise AssertionError("la meta no debe lanzar procesos")

    monkeypatch.setattr(subprocess, "run", prohibido)
    monkeypatch.setattr(subprocess, "Popen", prohibido)
    evaluar_s10_cobertura(85.0)
    from scripts.meta_sf import _s10

    _s10()  # S2, S3 y S8 si lanzan procesos (git y pytest); S10 solo lee coverage.json


# --- S2 Memorias -------------------------------------------------------------------------

_MEMORIAS_SF1 = ("bano_of001.md", "bano_drenaje_of001.md")


def test_s2_ok_si_las_memorias_del_bano_existen_y_son_anteriores_al_codigo():
    estado, detalle = evaluar_s2_memorias(
        {m: True for m in _MEMORIAS_SF1}, {m: True for m in _MEMORIAS_SF1}
    )
    assert estado is Estado.OK
    assert "bano_of001.md" in detalle


def test_s2_falla_si_la_memoria_se_versiono_despues_del_codigo():
    orden = {"bano_of001.md": True, "bano_drenaje_of001.md": False}
    estado, detalle = evaluar_s2_memorias({m: True for m in _MEMORIAS_SF1}, orden)
    assert estado is Estado.FALLA
    assert "bano_drenaje_of001.md" in detalle
    assert "despues" in detalle


def test_s2_falla_si_falta_una_memoria_y_el_codigo_ya_existe():
    presentes = {"bano_of001.md": True, "bano_drenaje_of001.md": False}
    orden = {"bano_of001.md": True, "bano_drenaje_of001.md": None}
    estado, detalle = evaluar_s2_memorias(presentes, orden)
    assert estado is Estado.FALLA
    assert "bano_drenaje_of001.md" in detalle


def test_s2_pendiente_si_falta_la_memoria_y_aun_no_hay_codigo():
    estado, _ = evaluar_s2_memorias({m: False for m in _MEMORIAS_SF1}, {}, codigo_existe=False)
    assert estado is Estado.PENDIENTE


def test_s2_la_memoria_de_sf2_ausente_no_hace_fallar_ni_pendiente_sf1():
    estado, detalle = evaluar_s2_memorias(
        {m: True for m in _MEMORIAS_SF1},
        {m: True for m in _MEMORIAS_SF1},
        posteriores={"of001.md": False},
    )
    assert estado is Estado.OK
    assert "of001.md" in detalle and "SF2" in detalle


def test_s2_memoria_presente_sin_commit_es_falla():
    estado, detalle = evaluar_s2_memorias(
        {m: True for m in _MEMORIAS_SF1}, {m: None for m in _MEMORIAS_SF1}
    )
    assert estado is Estado.FALLA  # presentes pero sin commit de memoria: no versionadas
    assert "sin versionar" in detalle


# --- S3 Especialidades -------------------------------------------------------------------


def test_s3_ok_si_las_pruebas_de_agua_pasan():
    estado, detalle = evaluar_s3_especialidades(existe_agua=True, resultado_agua=(31, 31))
    assert estado is Estado.OK
    assert "31" in detalle


def test_s3_falla_si_alguna_prueba_de_agua_falla():
    estado, detalle = evaluar_s3_especialidades(existe_agua=True, resultado_agua=(30, 31))
    assert estado is Estado.FALLA
    assert "30" in detalle


def test_s3_pendiente_si_no_hay_pruebas_de_agua():
    estado, _ = evaluar_s3_especialidades(existe_agua=False, resultado_agua=None)
    assert estado is Estado.PENDIENTE


def test_s3_pendiente_si_no_se_recolecto_ninguna_prueba():
    estado, _ = evaluar_s3_especialidades(existe_agua=True, resultado_agua=(0, 0))
    assert estado is Estado.PENDIENTE


# --- S8 Regresion ------------------------------------------------------------------------


def test_s8_ok_si_todos_los_grupos_pasan():
    grupos = {"linea base": (10, 10), "7 de 7": (4, 4)}
    estado, detalle = evaluar_s8_regresion(grupos)
    assert estado is Estado.OK
    assert "14" in detalle


def test_s8_falla_y_nombra_el_grupo_que_falla():
    grupos = {"linea base": (10, 10), "7 de 7": (3, 4), "R4": (1, 1)}
    estado, detalle = evaluar_s8_regresion(grupos)
    assert estado is Estado.FALLA
    assert "7 de 7" in detalle
    assert "linea base" not in detalle


def test_s8_pendiente_si_un_grupo_no_tiene_prueba_y_el_resto_pasa():
    grupos = {"linea base": (10, 10), "cuatro hojas": None}
    estado, detalle = evaluar_s8_regresion(grupos)
    assert estado is Estado.PENDIENTE
    assert "cuatro hojas" in detalle


def test_s8_falla_pesa_mas_que_pendiente():
    estado, _ = evaluar_s8_regresion({"a": (0, 1), "b": None})
    assert estado is Estado.FALLA


def test_s8_un_grupo_sin_pruebas_recolectadas_es_pendiente():
    estado, _ = evaluar_s8_regresion({"a": (0, 0)})
    assert estado is Estado.PENDIENTE


def test_contar_resultados_agrupa_por_prefijo_de_nodeid():
    salida = (
        "PASSED tests/unit/test_a.py::test_x\n"
        "FAILED tests/unit/test_a.py::test_y - assert 0\n"
        "PASSED tests/unit/test_b.py::test_z\n"
    )
    cuenta = contar_resultados(
        salida, {"A": ("tests/unit/test_a.py",), "B": ("tests/unit/test_b.py",)}
    )
    assert cuenta == {"A": (1, 2), "B": (1, 1)}


def test_contar_resultados_grupo_ausente_es_cero():
    assert contar_resultados("", {"A": ("tests/unit/test_a.py",)}) == {"A": (0, 0)}
