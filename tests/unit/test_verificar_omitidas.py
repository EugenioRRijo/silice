"""Pruebas de `scripts/verificar_omitidas.py` (integracion continua).

JUnit sintetico con la forma que escribe `pytest --junitxml`; ninguna prueba ejecuta pytest.
"""

import pytest

from scripts import verificar_omitidas

JUNIT_CON_UNA_OMITIDA = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" skipped="1" tests="2" time="0.10">
    <testcase classname="tests.unit.test_a" name="test_uno" time="0.01" />
    <testcase classname="tests.unit.test_ifc" name="test_dos" time="0.00">
      <skipped type="pytest.skip" message="could not import 'ifcopenshell'">omitida</skipped>
    </testcase>
  </testsuite>
</testsuites>
"""

JUNIT_SIN_OMITIDAS = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="0" tests="2" time="0.10">
    <testcase classname="tests.unit.test_a" name="test_uno" time="0.01" />
    <testcase classname="tests.unit.test_b" name="test_dos" time="0.01">
      <failure message="boom">AssertionError: boom</failure>
    </testcase>
  </testsuite>
</testsuites>
"""

JUNIT_SIN_PRUEBAS = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" errors="0" failures="0" skipped="0" tests="0" /></testsuites>
"""


def test_omitidas_lista_cada_omitida_con_su_motivo():
    assert verificar_omitidas.omitidas(JUNIT_CON_UNA_OMITIDA) == [
        "tests.unit.test_ifc::test_dos - could not import 'ifcopenshell'"
    ]


def test_una_fallida_no_cuenta_como_omitida():
    """Las fallidas ya ponen en rojo el paso de pytest; este verificador solo mira omisiones."""
    assert verificar_omitidas.omitidas(JUNIT_SIN_OMITIDAS) == []


def test_junit_sin_pruebas_es_ausencia_de_evidencia():
    with pytest.raises(verificar_omitidas.SinEvidenciaError, match="ninguna prueba"):
        verificar_omitidas.omitidas(JUNIT_SIN_PRUEBAS)


def test_xml_ilegible_es_ausencia_de_evidencia():
    with pytest.raises(verificar_omitidas.SinEvidenciaError, match="ilegible"):
        verificar_omitidas.omitidas("<testsuites><testsuite>")


def test_main_codigos_de_salida(tmp_path):
    con_omitida = tmp_path / "con_omitida.xml"
    con_omitida.write_text(JUNIT_CON_UNA_OMITIDA, encoding="utf-8")
    limpio = tmp_path / "limpio.xml"
    limpio.write_text(JUNIT_SIN_OMITIDAS, encoding="utf-8")

    assert verificar_omitidas.main([str(tmp_path / "no_existe.xml")]) == 2
    assert verificar_omitidas.main([str(con_omitida)]) == 1
    assert verificar_omitidas.main([str(limpio)]) == 0
