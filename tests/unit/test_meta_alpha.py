"""Pruebas de `scripts/meta_alpha.py` (Task 1 del sprint alpha).

Solo se ejercitan funciones puras: parseo de JUnit y las funciones `estado_*` y `render_tabla`.
Nunca se ejecuta el pytest real (ni ruff ni git) desde estas pruebas: eso lo hace `main()`, que
el cierre de la tarea ejercita manualmente con `uv run python scripts/meta_alpha.py`.
"""

from decimal import Decimal

from scripts import meta_alpha

XML_DOS_ARCHIVOS_CLASE_ANIDADA_UN_FALLO = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="0" tests="3" time="0.12">
    <testcase classname="tests.unit.test_a" name="test_uno" time="0.01" />
    <testcase classname="tests.unit.test_a.TestGrupo.TestAnidada" name="test_dos" time="0.01" />
    <testcase classname="tests.unit.test_b" name="test_tres" time="0.01">
      <failure message="boom">AssertionError: boom</failure>
    </testcase>
  </testsuite>
</testsuites>
"""


def test_parsear_junit_asigna_cada_testcase_al_archivo_conocido_mas_especifico():
    archivos_conocidos = ["tests/unit/test_a.py", "tests/unit/test_b.py"]

    resumenes = meta_alpha.parsear_junit(
        XML_DOS_ARCHIVOS_CLASE_ANIDADA_UN_FALLO, archivos_conocidos
    )

    assert resumenes["tests/unit/test_a.py"] == meta_alpha.ResumenArchivo(
        pasadas=2, fallidas=0, errores=0, omitidas=0
    )
    assert resumenes["tests/unit/test_b.py"] == meta_alpha.ResumenArchivo(
        pasadas=0, fallidas=1, errores=0, omitidas=0
    )


def test_parsear_junit_no_pierde_archivos_conocidos_sin_testcases():
    archivos_conocidos = ["tests/unit/test_a.py", "tests/unit/test_b.py", "tests/unit/test_c.py"]

    resumenes = meta_alpha.parsear_junit(
        XML_DOS_ARCHIVOS_CLASE_ANIDADA_UN_FALLO, archivos_conocidos
    )

    assert resumenes["tests/unit/test_c.py"] == meta_alpha.ResumenArchivo(
        pasadas=0, fallidas=0, errores=0, omitidas=0
    )


def test_estado_pruebas_pendiente_si_falta_el_archivo_en_disco(tmp_path):
    archivo_inexistente = str(tmp_path / "no_existe" / "test_x.py")

    estado, detalle = meta_alpha.estado_pruebas({}, [archivo_inexistente])

    assert estado is meta_alpha.Estado.PENDIENTE
    assert archivo_inexistente in detalle


def test_estado_pruebas_falla_si_algun_archivo_tiene_fallidas_o_errores(tmp_path):
    archivo = tmp_path / "test_x.py"
    archivo.write_text("# archivo de prueba, contenido irrelevante\n", encoding="utf-8")
    resumenes = {
        str(archivo): meta_alpha.ResumenArchivo(pasadas=4, fallidas=1, errores=0, omitidas=0)
    }

    estado, detalle = meta_alpha.estado_pruebas(resumenes, [str(archivo)])

    assert estado is meta_alpha.Estado.FALLA
    assert "4 pasadas" in detalle


def test_estado_pruebas_ok_si_ningun_archivo_tiene_fallidas_ni_errores(tmp_path):
    archivo = tmp_path / "test_y.py"
    archivo.write_text("# archivo de prueba, contenido irrelevante\n", encoding="utf-8")
    resumenes = {
        str(archivo): meta_alpha.ResumenArchivo(pasadas=5, fallidas=0, errores=0, omitidas=0)
    }

    estado, _ = meta_alpha.estado_pruebas(resumenes, [str(archivo)])

    assert estado is meta_alpha.Estado.OK


def test_estado_pruebas_pendiente_si_un_archivo_existe_y_otro_no(tmp_path):
    """Caso multi-archivo (afecta a M3/M5/M6): un archivo con resultados en verde no basta
    para tapar que otro archivo de evidencia todavia no existe."""
    archivo_existente = tmp_path / "test_existe.py"
    archivo_existente.write_text("# archivo de prueba, contenido irrelevante\n", encoding="utf-8")
    archivo_inexistente = str(tmp_path / "test_no_existe.py")
    resumenes = {
        str(archivo_existente): meta_alpha.ResumenArchivo(
            pasadas=3, fallidas=0, errores=0, omitidas=0
        )
    }

    estado, detalle = meta_alpha.estado_pruebas(
        resumenes, [str(archivo_existente), archivo_inexistente]
    )

    assert estado is meta_alpha.Estado.PENDIENTE
    assert archivo_inexistente in detalle


def test_estado_pruebas_falla_si_un_archivo_existente_no_tiene_resultados_registrados(tmp_path):
    """Un archivo que existe en disco pero sin ningun testcase en el reporte JUnit (0 pasadas /
    0 fallidas / 0 errores / 0 omitidas) no es un OK real: es ausencia de evidencia, y debe
    reportarse como FALLA explicita en vez de leerse como 'corrio sin fallos'."""
    archivo = tmp_path / "test_sin_resultados.py"
    archivo.write_text("# archivo de prueba, contenido irrelevante\n", encoding="utf-8")

    estado, detalle = meta_alpha.estado_pruebas({}, [str(archivo)])

    assert estado is meta_alpha.Estado.FALLA
    assert "sin resultados" in detalle


def test_estado_ejecucion_pytest_none_si_corre_normal_con_exito():
    assert meta_alpha.estado_ejecucion_pytest(0, "<testsuites></testsuites>") is None


def test_estado_ejecucion_pytest_none_si_hay_pruebas_fallidas_normales():
    """El codigo 1 es la salida normal de pytest cuando hay pruebas en rojo: no es catastrofico."""
    assert meta_alpha.estado_ejecucion_pytest(1, "<testsuites></testsuites>") is None


def test_estado_ejecucion_pytest_falla_explicita_si_el_codigo_no_es_0_ni_1():
    """INTERNALERROR, conftest.py roto, señal del SO: codigos fuera de {0, 1}."""
    estado, detalle = meta_alpha.estado_ejecucion_pytest(3, "")

    assert estado is meta_alpha.Estado.FALLA
    assert "3" in detalle


def test_estado_ejecucion_pytest_falla_explicita_si_no_hay_junit():
    """Corrida catastrofica sin junit.xml, aunque el codigo de salida sea 0."""
    estado, detalle = meta_alpha.estado_ejecucion_pytest(0, "")

    assert estado is meta_alpha.Estado.FALLA
    assert "pytest no produjo resultados" in detalle


def test_estado_nucleo_intacto_falla_con_un_commit_que_toca_adapters_y_core():
    commits = [("abc123def", ["adapters/civil/extractor.py", "core/costing/motor.py"])]

    estado, detalle = meta_alpha.estado_nucleo_intacto(commits)

    assert estado is meta_alpha.Estado.FALLA
    assert "abc123de" in detalle


def test_estado_nucleo_intacto_ok_con_commits_que_solo_tocan_adapters():
    commits = [
        ("abc123def", ["adapters/civil/extractor.py"]),
        ("fed321cba", ["ml/anomaly/deteccion.py"]),
    ]

    estado, detalle = meta_alpha.estado_nucleo_intacto(commits)

    assert estado is meta_alpha.Estado.OK
    assert "2 commits" in detalle


def test_estado_nucleo_intacto_pendiente_sin_commits():
    estado, _ = meta_alpha.estado_nucleo_intacto([])

    assert estado is meta_alpha.Estado.PENDIENTE


def test_estado_nucleo_intacto_falla_si_una_rama_de_adaptador_cambia_core():
    """El agujero que cerró la revisión final (ítem 3): un commit que toca **solo** `core/`.

    `git log -- adapters ml` no lo lista, así que la regla por commit no lo ve; el `git diff
    core/` del rango completo de la rama sí. Es la evidencia que NORMAS.md §1 atribuye a M9.
    """
    ramas = [("9c54669e merge: I5 adaptador telecom (inc/I5-telecom)", ["core/costing/motor.py"])]

    estado, detalle = meta_alpha.estado_nucleo_intacto([], ramas)

    assert estado is meta_alpha.Estado.FALLA
    assert "core/costing/motor.py" in detalle
    assert "inc/I5-telecom" in detalle


def test_estado_nucleo_intacto_ok_con_ramas_de_adaptador_con_diff_de_core_vacio():
    commits = [("abc123def", ["adapters/telecom/adaptador.py"])]
    ramas = [("abc123de merge: I5 adaptador telecom (inc/I5-telecom)", [])]

    estado, detalle = meta_alpha.estado_nucleo_intacto(commits, ramas)

    assert estado is meta_alpha.Estado.OK
    assert "1 commits" in detalle
    assert "1 ramas" in detalle


def test_estado_nucleo_intacto_pendiente_sin_commits_ni_ramas():
    estado, _ = meta_alpha.estado_nucleo_intacto([], [])

    assert estado is meta_alpha.Estado.PENDIENTE


def test_estado_cobertura_falla_bajo_el_umbral():
    estado, _ = meta_alpha.estado_cobertura(Decimal("79.9"), 80)

    assert estado is meta_alpha.Estado.FALLA


def test_estado_cobertura_ok_exactamente_en_el_umbral():
    estado, _ = meta_alpha.estado_cobertura(Decimal("80"), 80)

    assert estado is meta_alpha.Estado.OK


def test_estado_ruff_ok_con_ambos_codigos_en_cero():
    estado, _ = meta_alpha.estado_ruff(0, 0)

    assert estado is meta_alpha.Estado.OK


def test_estado_ruff_falla_si_algun_codigo_no_es_cero():
    estado, detalle = meta_alpha.estado_ruff(1, 0)

    assert estado is meta_alpha.Estado.FALLA
    assert "ruff check" in detalle


def test_estado_suite_pendiente_sin_pruebas():
    estado, _ = meta_alpha.estado_suite(0, 0, 0)

    assert estado is meta_alpha.Estado.PENDIENTE


def test_estado_suite_falla_con_fallidas_o_errores():
    estado, _ = meta_alpha.estado_suite(95, 2, 1)

    assert estado is meta_alpha.Estado.FALLA


def test_estado_suite_ok_sin_fallidas_ni_errores():
    estado, _ = meta_alpha.estado_suite(95, 0, 0)

    assert estado is meta_alpha.Estado.OK


def test_render_tabla_contiene_los_12_codigos_y_la_linea_resultado():
    filas = [
        meta_alpha.Fila(meta.codigo, meta.titulo, meta_alpha.Estado.PENDIENTE, "sin evidencia")
        for meta in meta_alpha.METAS
    ]

    tabla = meta_alpha.render_tabla(filas)

    for codigo in (f"M{n}" for n in range(1, 13)):
        assert codigo in tabla
    assert "RESULTADO" in tabla


def test_render_tabla_cuenta_las_metas_en_ok_en_la_linea_resultado():
    filas = [
        meta_alpha.Fila("M1", "titulo", meta_alpha.Estado.OK, "ev"),
        meta_alpha.Fila("M2", "titulo", meta_alpha.Estado.FALLA, "ev"),
    ]

    tabla = meta_alpha.render_tabla(filas)

    assert "RESULTADO: 1/2 metas OK" in tabla
