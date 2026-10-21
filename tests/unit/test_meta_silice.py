"""Meta unica de Silice (maestro §6.3, RV-17; plan 0.6.0, tarea A4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_silice import (
    ARCHIVOS_REGRESION,
    PARTE_T0,
    REGRESION,
    CifraDeTiempo,
    ParTDD,
    Parte,
    evaluar_cifras,
    evaluar_diff_vacio,
    evaluar_guardia,
    evaluar_omitidas,
    evaluar_orden_tdd,
    evaluar_regresion,
    evaluar_requisitos,
    fases_hasta,
    guardia_declarada,
    main,
    orden_de_par,
    partes,
    requisitos_exigidos,
    validar_partes,
)

RAIZ = Path(__file__).resolve().parents[2]
JUNIT_LIMPIO = '<testsuites><testsuite><testcase classname="a" name="b"/></testsuite></testsuites>'
JUNIT_OMITIDA = (
    '<testsuites><testsuite><testcase classname="a" name="b">'
    '<skipped message="sin modelo"/></testcase></testsuite></testsuites>'
)
CIFRA = CifraDeTiempo(
    "RNF-11",
    "scripts/_salida_rnf11.json",
    "mediana_s",
    "uv run python scripts/medir_rnf11.py",
    "T0",
)


def test_los_archivos_de_regresion_son_los_del_bloque_literal() -> None:
    assert ARCHIVOS_REGRESION == (
        "tests/integration/test_auditoria_7_de_7.py",
        "tests/integration/test_composicion_extremo_a_extremo.py",
        "tests/unit/test_budget.py",
        "tests/unit/test_caso_ti001.py",
        "tests/unit/test_costing.py",
        "tests/unit/test_huellas_rnf04.py",
        "tests/unit/test_linea_base.py",
        "tests/unit/test_verification.py",
    )
    assert set(REGRESION) == {
        "cinco APU a +-0,01",
        "7 de 7",
        "R4 de 3/4 pulg",
        "TI-001 total, PU y PE 28 586,76 USD Dia 6",
        "dos huellas de RNF-04",
        "cuatro hojas de exportar_excel",
    }


def test_cada_prueba_de_regresion_esta_definida() -> None:
    for nodos in REGRESION.values():
        for nodo in nodos:
            archivo, _, prueba = nodo.partition("::")
            texto = (RAIZ / archivo).read_text(encoding="utf-8")
            assert not prueba or f"def {prueba}(" in texto, nodo


def test_fases_hasta_acumula_en_orden() -> None:
    assert fases_hasta("0.6.0", "T0") == ("T0",)
    assert fases_hasta("0.6.0", "S1-0") == ("T0", "S5-1", "S1-0")
    with pytest.raises(ValueError, match="fase desconocida"):
        fases_hasta("0.6.0", "S2-1")
    with pytest.raises(ValueError, match="version desconocida"):
        fases_hasta("0.5.0", "T0")


def test_la_1_0_0_acumula_todas_las_versiones_y_termina_en_s5_5() -> None:
    """Apertura de la 1.0.0 (PLAN_SILICE_100, T1): 8 + 6 + 8 + 5 fases previas y las 5 de S5."""
    fases = fases_hasta("1.0.0", "S5-5")
    assert fases[-5:] == ("S5-0", "S5-2", "S5-3", "S5-4", "S5-5")
    assert len(fases) == 8 + 6 + 8 + 5 + 5 and len(set(fases)) == len(fases)
    assert "S5-1" in fases and "S1-5" in fases  # lo de la 0.6.0 se evalúa también
    assert fases.index("S4-4") < fases.index("S5-0")  # la 0.9.0 antes que la 1.0.0
    assert fases_hasta("1.0.0", "S5-0")[-1] == "S5-0"
    assert fases_hasta("1.0.0", "S5-4")[-2:] == ("S5-3", "S5-4")
    with pytest.raises(ValueError, match="fase desconocida"):
        fases_hasta("1.0.0", "S5-1")  # S5-1 es de la 0.6.0, no de la 1.0.0


def test_los_requisitos_se_exigen_por_presencia_y_por_fase() -> None:
    parte = Parte("S5", requisitos={"S5-1": ("RF-96", "RNF-20")})
    assert requisitos_exigidos((parte,), ("T0",)) == ()
    assert requisitos_exigidos((parte,), ("T0", "S5-1")) == ("RF-96", "RNF-20")
    ers = "| RF-96 | algo | E |\n| Calidad | RNF-20 deriva | x |\n"
    assert evaluar_requisitos(ers, ("RF-96", "RNF-20"))[0] is Estado.OK
    estado, detalle = evaluar_requisitos(ers, ("RF-96", "RF-97"))
    assert estado is Estado.FALLA and "RF-97" in detalle
    assert evaluar_requisitos(None, ("RF-96",))[0] is Estado.PENDIENTE
    assert evaluar_requisitos(None, ())[0] is Estado.OK


def test_omitidas() -> None:
    assert evaluar_omitidas(JUNIT_LIMPIO)[0] is Estado.OK
    estado, detalle = evaluar_omitidas(JUNIT_OMITIDA)
    assert estado is Estado.FALLA and "sin modelo" in detalle
    assert evaluar_omitidas(None)[0] is Estado.PENDIENTE
    assert evaluar_omitidas("<roto")[0] is Estado.PENDIENTE


def test_orden_tdd() -> None:
    par = ParTDD("tests/unit/test_x.py", "ui/x.py", "T0")
    assert evaluar_orden_tdd({})[0] is Estado.OK
    assert evaluar_orden_tdd({par: True})[0] is Estado.OK
    assert evaluar_orden_tdd({par: False})[0] is Estado.FALLA
    assert evaluar_orden_tdd({par: None})[0] is Estado.PENDIENTE


def test_el_orden_de_a1_se_lee_del_historial_real() -> None:
    assert (
        orden_de_par(ParTDD("tests/unit/test_entorno_silice.py", "aplicacion/entorno.py", "T0"))
        is True
    )


def test_diff_vacio() -> None:
    assert evaluar_diff_vacio("core/contracts/", False, None)[0] is Estado.PENDIENTE
    assert evaluar_diff_vacio("core/contracts/", True, None)[0] is Estado.PENDIENTE
    cambio = " core/contracts/apu.py | 2 +-\n"
    assert evaluar_diff_vacio("core/contracts/", True, cambio)[0] is Estado.FALLA
    assert evaluar_diff_vacio("core/contracts/", True, "")[0] is Estado.OK


def test_una_prueba_de_regresion_borrada_es_falla() -> None:
    intacto = (Estado.OK, "intacto")
    grupos = {grupo: (1, 1) for grupo in REGRESION}
    assert evaluar_regresion(intacto, grupos, [])[0] is Estado.OK
    assert evaluar_regresion(intacto, {**grupos, "7 de 7": None}, ["7 de 7"])[0] is Estado.FALLA
    assert evaluar_regresion((Estado.FALLA, "cambio"), grupos, [])[0] is Estado.FALLA
    assert evaluar_regresion(intacto, {**grupos, "7 de 7": (3, 4)}, [])[0] is Estado.FALLA


def test_cifras_de_tiempo() -> None:
    assert evaluar_cifras({}, [])[0] is Estado.OK
    assert evaluar_cifras({CIFRA.ruta: None}, [CIFRA])[0] is Estado.PENDIENTE
    assert evaluar_cifras({CIFRA.ruta: {"mediana_s": "rapido"}}, [CIFRA])[0] is Estado.PENDIENTE
    estado, detalle = evaluar_cifras({CIFRA.ruta: {"mediana_s": 0.42}}, [CIFRA])
    assert estado is Estado.OK and "RNF-11" in detalle


def test_la_guardia_esta_declarada_en_el_conftest_real() -> None:
    assert guardia_declarada((RAIZ / "tests" / "conftest.py").read_text(encoding="utf-8"))


def test_una_guardia_sin_autouse_o_de_funcion_no_cuenta() -> None:
    sin_autouse = (
        "import pytest\n@pytest.fixture(scope='session')\ndef _guardia_de_red():\n    yield\n"
    )
    de_funcion = "import pytest\n@pytest.fixture(autouse=True)\ndef _guardia_de_red():\n    yield\n"
    assert not guardia_declarada(sin_autouse)
    assert not guardia_declarada(de_funcion)
    assert not guardia_declarada(None)


def test_evaluar_guardia() -> None:
    assert evaluar_guardia(False, None)[0] is Estado.FALLA
    assert evaluar_guardia(True, None)[0] is Estado.PENDIENTE
    assert evaluar_guardia(True, (5, 6))[0] is Estado.FALLA
    assert evaluar_guardia(True, (6, 6))[0] is Estado.OK


def test_las_partes_descubiertas_usan_fases_declaradas() -> None:
    validar_partes(partes())
    assert partes()[0] is PARTE_T0


def test_una_parte_con_una_fase_inexistente_se_rechaza() -> None:
    mala = Parte("X", pares_tdd=(ParTDD("a", "b", "S9-9"),))
    with pytest.raises(ValueError, match="S9-9"):
        validar_partes((mala,))


def test_los_pares_de_t0_nombran_archivos_del_repositorio() -> None:
    for par in PARTE_T0.pares_tdd:
        assert (RAIZ / par.prueba).is_file(), par.prueba
        assert (RAIZ / par.implementacion).is_file(), par.implementacion


def test_main_rechaza_una_fase_que_no_es_de_la_version(capsys) -> None:
    with pytest.raises(SystemExit) as salida:
        main(["--version", "0.6.0", "--hasta", "S2-1"])
    assert salida.value.code == 2
    assert "S2-1" in capsys.readouterr().err
