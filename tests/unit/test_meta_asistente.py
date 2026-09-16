"""Pruebas de `scripts/meta_asistente.py` (plan del asistente de presupuestos, UC-09).

Solo funciones puras sobre texto sintetico: ninguna prueba lee el disco ni ejecuta git, ruff o
pytest (la leccion de la meta M8 del sprint multidominio, que contaba mal y no tenia pruebas).
Los guiones mezclan ASCII y el no separable U+2011, como escriben los documentos del proyecto.
"""

import pytest

from scripts import meta_asistente as meta
from scripts.meta_alpha import Estado

PLAN_COMPLETO = """# PLAN_ASISTENTE.md

## 2. Compuertas

| Compuerta | Criterio |
|---|---|
| **GA0** documentacion | x |
| **GA1** herramientas | x |
| **GA2** orquestacion | x |
| **GA3** evaluacion | x |
| **GA‑datos** hibrido | x |

## Fase A0 — Documentacion

### Sesión A0.1 — ERS

**Cierre.** M3 y M4 en OK.
**Fuente única.** docs/ERS.md.
**Commit.** `docs(ers): uc-09`

## Fase A1 — Herramientas

### Sesión A1.1 — Herramientas de consulta

**Cierre.** M7 en OK.
**Fuente única.** asistente/herramientas.py.
**Commit.** `feat(asistente): herramientas`

## Fase A2 — Orquestacion

## Fase A3 — Evaluacion

## Fase A4 — Integracion y cierre

## Resumen del recorrido
"""


def test_metas_hasta_p_son_las_de_planificacion_y_las_transversales():
    assert meta.metas_hasta("P") == ["M1", "M2", "M11", "M12"]


def test_metas_hasta_a0_suman_la_documentacion():
    assert meta.metas_hasta("A0") == ["M1", "M2", "M3", "M4", "M5", "M6", "M11", "M12"]


def test_metas_hasta_fase_desconocida_falla():
    with pytest.raises(ValueError, match="fase desconocida"):
        meta.metas_hasta("A9")


def test_plan_completo_ok():
    estado, evidencia = meta.evaluar_plan(PLAN_COMPLETO)

    assert estado is Estado.OK, evidencia
    assert "2 sesiones" in evidencia


def test_plan_con_sesion_sin_commit_falla_citando_la_sesion():
    sin_commit = PLAN_COMPLETO.replace("**Commit.** `feat(asistente): herramientas`", "")

    estado, evidencia = meta.evaluar_plan(sin_commit)

    assert estado is Estado.FALLA
    assert "A1.1" in evidencia and "Commit" in evidencia


def test_el_commit_de_una_seccion_posterior_no_tapa_el_de_la_ultima_sesion():
    sin_commit = PLAN_COMPLETO.replace(
        "**Commit.** `feat(asistente): herramientas`", ""
    ).replace("## Resumen del recorrido", "## Resumen del recorrido\n\n**Commit.** ajeno")

    estado, _ = meta.evaluar_plan(sin_commit)

    assert estado is Estado.FALLA


def test_plan_sin_compuerta_ga_datos_falla():
    estado, evidencia = meta.evaluar_plan(PLAN_COMPLETO.replace("GA‑datos", ""))

    assert estado is Estado.FALLA
    assert "GA-datos" in evidencia


def test_compuerta_mencionada_solo_en_un_prompt_no_cuenta():
    """La compuerta debe estar definida en la tabla de compuertas, no solo nombrada en un prompt."""
    solo_mencion = PLAN_COMPLETO.replace("| **GA3** evaluacion | x |", "") + "\nveredicto GA3\n"

    estado, evidencia = meta.evaluar_plan(solo_mencion)

    assert estado is Estado.FALLA
    assert "GA3" in evidencia


def test_plan_ausente_pendiente():
    assert meta.evaluar_plan(None)[0] is Estado.PENDIENTE


def test_spec_existe_o_pendiente():
    assert meta.evaluar_spec(True)[0] is Estado.OK
    assert meta.evaluar_spec(False)[0] is Estado.PENDIENTE


ERS_SIN_UC09 = """#### UC‑08 — Generar escenarios
| RNF‑08 ejecución local: no invoca servicios externos | 0 y 0 |
"""

ERS_CON_UC09 = """#### UC‑09 — Generar presupuesto asistido
| RF‑32 | El sistema recibira las necesidades | Esencial | UC‑09 | A2 | prueba |
| RF‑33 | El sistema propondra partidas del catalogo | Esencial | UC‑09 | A1 | prueba |
| RF-34 | El sistema auditara el borrador | Esencial | UC-09 | A1 | prueba |
| RF‑35 | Otro requisito | Esencial | UC‑05 | I4 | prueba |
"""


def test_uc09_ausente_pendiente():
    assert meta.evaluar_uc09(ERS_SIN_UC09)[0] is Estado.PENDIENTE
    assert meta.evaluar_uc09(None)[0] is Estado.PENDIENTE


def test_uc09_con_tres_rf_ok():
    estado, evidencia = meta.evaluar_uc09(ERS_CON_UC09)

    assert estado is Estado.OK, evidencia
    assert "3 RF" in evidencia


def test_uc09_con_dos_rf_falla():
    con_dos = ERS_CON_UC09.replace(
        "| RF-34 | El sistema auditara el borrador | Esencial | UC-09 |", ""
    )

    assert meta.evaluar_uc09(con_dos)[0] is Estado.FALLA


def test_rnf08_sin_excepcion_del_extra_ia_pendiente():
    assert meta.evaluar_rnf08(ERS_SIN_UC09)[0] is Estado.PENDIENTE


def test_rnf08_con_excepcion_del_extra_ia_ok():
    texto = "| RNF‑08 ejecución local; excepcion declarada: el extra `ia` llama a la API | 0 |"

    assert meta.evaluar_rnf08(texto)[0] is Estado.OK


def test_rnf08_sin_fila_falla():
    assert meta.evaluar_rnf08("# ERS sin requisitos no funcionales")[0] is Estado.FALLA


def test_arquitectura_con_seccion_del_asistente_ok():
    assert meta.evaluar_arquitectura("## 2. Vista logica\n### 2.4 El asistente")[0] is Estado.OK
    assert meta.evaluar_arquitectura("## 2. Vista logica")[0] is Estado.PENDIENTE
    assert meta.evaluar_arquitectura(None)[0] is Estado.PENDIENTE


PROTOCOLO_COMPLETO = """# Protocolo de evaluacion del asistente
Casos dorados: línea base (civil), ARENAZA (telecom), MNT‑001 (industrial), SIS‑001 (sistemas).
Cada umbral se congela antes de la primera corrida.
"""


def test_protocolo_completo_ok():
    assert meta.evaluar_protocolo(PROTOCOLO_COMPLETO)[0] is Estado.OK


def test_protocolo_sin_un_caso_dorado_falla_nombrandolo():
    estado, evidencia = meta.evaluar_protocolo(PROTOCOLO_COMPLETO.replace("SIS‑001", "otro"))

    assert estado is Estado.FALLA
    assert "SIS-001" in evidencia


def test_protocolo_ausente_pendiente():
    assert meta.evaluar_protocolo(None)[0] is Estado.PENDIENTE


def test_guardia_de_arquitectura_segun_la_tupla_vigilada():
    actual = 'PAQUETES_FUERA_DEL_NUCLEO = ("adapters", "ml", "ui", "api")'
    ampliada = 'PAQUETES_FUERA_DEL_NUCLEO = ("adapters", "ml", "ui", "api", "asistente")'

    assert meta.evaluar_guardia_arquitectura(actual)[0] is Estado.PENDIENTE
    assert meta.evaluar_guardia_arquitectura(ampliada)[0] is Estado.OK
    assert meta.evaluar_guardia_arquitectura("sin constante")[0] is Estado.FALLA


def test_resultados_segun_tabla_y_recuento_g2():
    completo = (
        "## Metricas\n\n| Metrica | Valor |\n|---|---|\n| exhaustividad | 80 % |\n\nRecuento G2."
    )

    assert meta.evaluar_resultados(None)[0] is Estado.PENDIENTE
    assert meta.evaluar_resultados(completo)[0] is Estado.OK
    assert meta.evaluar_resultados("Recuento G2 sin tabla")[0] is Estado.FALLA
