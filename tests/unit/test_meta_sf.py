"""Pruebas de scripts/meta_sf.py (meta del sprint final, SF0-SF5)."""

import json

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_sf import (
    FASES,
    GRUPOS_S5,
    TITULOS,
    base_de_core,
    contar_resultados,
    evaluar_s1_requisitos,
    evaluar_s2_memorias,
    evaluar_s3_especialidades,
    evaluar_s4_core,
    evaluar_s5_nucleo,
    evaluar_s8_regresion,
    evaluar_s10_cobertura,
    main,
    memorias_exigidas,
    metas_hasta,
    porcentaje_espacio,
    punta_de_s4,
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


def test_main_hasta_sf0_ok(capsys):
    assert main(["--hasta", "SF0"]) == 0
    assert "S1" in capsys.readouterr().out


def test_hasta_sf2_evalua_seis_metas_incluida_s4():
    assert metas_hasta("SF2") == ["S1", "S2", "S3", "S8", "S10", "S4"]


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


# --- S10: el coverage.json debe ser posterior al codigo que mide -------------------------------


def test_s10_pendiente_si_el_coverage_json_es_anterior_al_codigo():
    estado, detalle = evaluar_s10_cobertura(95.0, vigente=False)
    assert estado is Estado.PENDIENTE
    assert "anterior" in detalle


def test_s10_ok_si_el_dato_esta_vigente():
    assert evaluar_s10_cobertura(95.0, vigente=True)[0] is Estado.OK


def test_cobertura_vigente_compara_con_el_codigo_mas_reciente(tmp_path):
    import os

    from scripts.meta_sf import cobertura_vigente

    codigo = tmp_path / "adapters" / "espacio"
    (codigo / "especialidades").mkdir(parents=True)
    viejo, nuevo = codigo / "a.py", codigo / "especialidades" / "b.py"
    viejo.write_text("x = 1\n")
    nuevo.write_text("y = 2\n")
    informe = tmp_path / "coverage.json"
    informe.write_text("{}")
    os.utime(viejo, (1_000, 1_000))
    os.utime(nuevo, (3_000, 3_000))
    os.utime(informe, (2_000, 2_000))
    assert not cobertura_vigente(informe, codigo)  # el codigo de un subpaquete es mas nuevo
    os.utime(informe, (4_000, 4_000))
    assert cobertura_vigente(informe, codigo)
    assert not cobertura_vigente(tmp_path / "no_existe.json", codigo)


# --- S8: un nodeid declarado que ya no esta en disco es una FALLA ------------------------------


def test_s8_falla_si_una_prueba_de_regresion_declarada_no_esta_en_disco():
    estado, detalle = evaluar_s8_regresion({"linea base": (10, 10), "R4": None}, ausentes=["R4"])
    assert estado is Estado.FALLA
    assert "R4" in detalle and "disco" in detalle


def test_cada_prueba_de_regresion_declarada_existe_en_disco():
    from scripts.meta_sf import REGRESION, _existe

    ausentes = [i for ids in REGRESION.values() for i in ids if not _existe(i)]
    assert ausentes == []


def test_existe_exige_la_funcion_y_no_solo_el_archivo():
    from scripts.meta_sf import _existe

    assert _existe("tests/unit/test_meta_sf.py")
    assert _existe("tests/unit/test_meta_sf.py::test_s10_ok_si_el_dato_esta_vigente")
    assert not _existe("tests/unit/test_meta_sf.py::test_que_no_existe")
    assert not _existe("tests/unit/no_existe.py")


# --- SF2: S3 con datos y electricidad ----------------------------------------------------------


def _s3_sf2(**cambios):
    datos = dict(
        existe_agua=True,
        resultado_agua=(31, 31),
        existe_datos=True,
        resultado_datos=(22, 22),
        existe_electricidad=True,
        resultado_electricidad=(40, 40),
    )
    datos.update(cambios)
    return evaluar_s3_especialidades(**datos)


def test_s3_sf2_ok_si_pasan_agua_datos_y_electricidad():
    estado, detalle = _s3_sf2()
    assert estado is Estado.OK
    assert "agua (31/31)" in detalle and "datos (22/22)" in detalle
    assert "electricidad (40/40)" in detalle


def test_s3_sf2_pendiente_si_faltan_las_pruebas_de_datos_o_de_electricidad():
    estado, detalle = _s3_sf2(existe_datos=False, resultado_datos=None)
    assert estado is Estado.PENDIENTE and "datos" in detalle
    estado, detalle = _s3_sf2(existe_electricidad=False, resultado_electricidad=None)
    assert estado is Estado.PENDIENTE and "electricidad" in detalle


def test_s3_sf2_pendiente_si_no_se_recolecto_ninguna_prueba_de_datos():
    estado, _ = _s3_sf2(resultado_datos=(0, 0))
    assert estado is Estado.PENDIENTE


def test_s3_sf2_falla_y_nombra_la_especialidad_que_falla():
    estado, detalle = _s3_sf2(resultado_electricidad=(39, 40))
    assert estado is Estado.FALLA and "electricidad" in detalle and "39" in detalle
    estado, detalle = _s3_sf2(resultado_datos=(21, 22))
    assert estado is Estado.FALLA and "datos" in detalle


def test_s3_falla_pesa_mas_que_pendiente():
    estado, _ = _s3_sf2(
        resultado_datos=(21, 22), existe_electricidad=False, resultado_electricidad=None
    )
    assert estado is Estado.FALLA


def test_s3_sin_exigir_sf2_conserva_el_mensaje_de_sf1():
    estado, detalle = evaluar_s3_especialidades(existe_agua=True, resultado_agua=(31, 31))
    assert estado is Estado.OK and "SF2" in detalle


# --- SF2: S2 reconoce of001.md -------------------------------------------------------------------


def test_s2_en_sf1_exige_solo_las_memorias_del_bano():
    assert set(memorias_exigidas(False)) == {"bano_of001.md", "bano_drenaje_of001.md"}


def test_s2_en_sf2_exige_tambien_of001_antes_del_primer_codigo_de_datos():
    exigidas = memorias_exigidas(True)
    assert set(exigidas) == {"bano_of001.md", "bano_drenaje_of001.md", "of001.md"}
    assert exigidas["of001.md"][-1] == "adapters/espacio/especialidades/datos.py"
    assert "--diff-filter=A" in exigidas["of001.md"]


def test_s2_sf2_falla_si_of001_se_versiono_despues_del_codigo():
    presentes = {"bano_of001.md": True, "bano_drenaje_of001.md": True, "of001.md": True}
    orden = {"bano_of001.md": True, "bano_drenaje_of001.md": True, "of001.md": False}
    estado, detalle = evaluar_s2_memorias(presentes, orden)
    assert estado is Estado.FALLA and "of001.md" in detalle


# --- SF2: S4 core intacto ---------------------------------------------------------------------


def test_s4_ok_si_el_diff_de_core_esta_vacio():
    estado, detalle = evaluar_s4_core("gsf1", "")
    assert estado is Estado.OK and "gsf1" in detalle
    assert evaluar_s4_core("inc/sf1", "  " + chr(10))[0] is Estado.OK


def test_s4_falla_si_core_cambio_y_lo_dice():
    estado, detalle = evaluar_s4_core(
        "gsf1", " core/budget/curva.py | 3 ++-" + chr(10) + " 1 file changed"
    )
    assert estado is Estado.FALLA
    assert "core/budget/curva.py" in detalle


def test_s4_pendiente_sin_base_o_si_git_no_responde():
    assert evaluar_s4_core(None, "")[0] is Estado.PENDIENTE
    assert evaluar_s4_core("gsf1", None)[0] is Estado.PENDIENTE


def test_la_base_de_s4_es_gsf1_y_si_no_existe_inc_sf1():
    assert base_de_core(lambda ref: True) == "gsf1"
    assert base_de_core(lambda ref: ref == "inc/sf1") == "inc/sf1"
    assert base_de_core(lambda ref: False) is None


def test_s4_sobre_el_repositorio_real_no_falla():
    """En este arbol `core/` no cambio desde gsf1 (o inc/sf1): OK; sin la base (clon superficial),
    PENDIENTE. Un FALLA aqui es una violacion real del invariante de SF2."""
    from scripts.meta_sf import _s4

    estado, detalle = _s4()
    assert estado is not Estado.FALLA, detalle


# --- SF3 (rama de nucleo): S4 solo vigila SF2 y SF5; S5 parcial; S9 pendiente ------------------


def test_la_punta_de_s4_es_el_fin_de_sf2_y_si_no_existe_head():
    """S4 vigila SF2 (y SF5): en una rama de SF3 que SI toca `core/` (expedientes SF-E2 a SF-E7,
    spec 12.2) se compara el fin de SF2, no la punta de la rama."""
    assert punta_de_s4(lambda ref: True) == "gsf2"
    assert punta_de_s4(lambda ref: ref == "inc/sf2") == "inc/sf2"
    assert punta_de_s4(lambda ref: False) == "HEAD"


def test_s4_nombra_la_punta_con_que_comparo():
    estado, detalle = evaluar_s4_core("inc/sf1", "", "inc/sf2")
    assert estado is Estado.OK and "inc/sf1..inc/sf2" in detalle
    estado, detalle = evaluar_s4_core("inc/sf1", " core/x.py | 1 +", "inc/sf2")
    assert estado is Estado.FALLA and "inc/sf1..inc/sf2" in detalle


def test_hasta_sf3_agrega_s5_y_s9():
    assert metas_hasta("SF3") == ["S1", "S2", "S3", "S8", "S10", "S4", "S5", "S9"]


def test_s5_ok_si_pasan_todos_los_grupos_del_nucleo():
    grupos = {g: (4, 4) for g in GRUPOS_S5}
    estado, detalle = evaluar_s5_nucleo(grupos)
    assert estado is Estado.OK
    assert "nucleo" in detalle and "SF3" in detalle


def test_s5_falla_y_nombra_el_grupo_que_falla():
    grupos = {g: (4, 4) for g in GRUPOS_S5}
    grupos["punto de equilibrio"] = (3, 4)
    estado, detalle = evaluar_s5_nucleo(grupos)
    assert estado is Estado.FALLA and "punto de equilibrio (3/4)" in detalle


def test_s5_pendiente_si_un_grupo_no_tiene_pruebas():
    grupos = {g: (4, 4) for g in GRUPOS_S5}
    grupos["Excel"] = None
    estado, detalle = evaluar_s5_nucleo(grupos)
    assert estado is Estado.PENDIENTE and "Excel" in detalle
    grupos["Excel"] = (0, 0)
    assert evaluar_s5_nucleo(grupos)[0] is Estado.PENDIENTE


def test_s5_falla_pesa_mas_que_pendiente():
    grupos = {g: None for g in GRUPOS_S5}
    grupos["Excel"] = (1, 2)
    assert evaluar_s5_nucleo(grupos)[0] is Estado.FALLA


def test_los_grupos_de_s5_cubren_edicion_restauracion_pe_y_excel():
    assert {"edicion, versiones y restauracion", "punto de equilibrio", "Excel"} <= set(GRUPOS_S5)
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    for ids in GRUPOS_S5.values():
        for ruta in ids:
            assert (raiz / ruta).is_file(), ruta
