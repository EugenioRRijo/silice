"""Sesion M4.1: la seccion por dominio de `docs/resultados_ml.md` (compuerta GM4).

`generar_informe` sigue siendo pura: con `por_dominio` tabula, para cada dominio distinto de
civil, sus metricas sobre el historico observado (telecom) o el motivo por el que no se evalua
(industrial y sistemas: una sola lista publicada). Los conteos nuevos siguen todos por debajo
del umbral, asi que la tecnica sigue siendo reglas y la limitacion sigue declarada, ahora con
catalogos poblados.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("sklearn")  # scripts/generar_resultados_ml.py importa ml (extra `ml`)


def _evaluacion_telecom():
    from ml.prediction import PrediccionPrecio, contrastar_aace, metricas
    from scripts.generar_resultados_ml import EvaluacionDominio

    base = {"TC-P1-11": Decimal("3.96"), "TC-P1-01": Decimal("82.68")}
    reales = {"TC-P1-11": Decimal("9.5364"), "TC-P1-01": Decimal("82.68")}
    predicciones = [
        PrediccionPrecio(
            "TC-P1-01", base["TC-P1-01"], Decimal("104.05"), Decimal("65.24"), Decimal("199.09")
        ),
        PrediccionPrecio(
            "TC-P1-11", base["TC-P1-11"], Decimal("4.98"), Decimal("3.12"), Decimal("9.54")
        ),
    ]
    estimados = {p.codigo_partida: p.pu_estimado for p in predicciones}
    hallazgos = [
        h
        for codigo in sorted(reales)
        if (h := contrastar_aace(codigo, reales[codigo], estimados[codigo])) is not None
    ]
    return EvaluacionDominio(
        dominio="telecom",
        lista_base="Precios ARENAZA (2026-05-18)",
        lista_nueva="Precios MaPreX 2026-07 (2026-07-09)",
        partidas=2,
        cambios_de_precio=1,
        metricas=metricas(estimados=estimados, reales=reales),
        predicciones=predicciones,
        reales=reales,
        hallazgos=hallazgos,
    )


def _informe() -> str:
    from ml.prediction import metricas
    from scripts.generar_resultados_ml import SIN_HISTORICO, generar_informe

    conteos = {"civil": 5, "telecom": 40, "industrial": 4, "sistemas": 9}
    civil = metricas(
        estimados={"LB-04-CON": Decimal("279.04")}, reales={"LB-04-CON": Decimal("272.81")}
    )
    return generar_informe(
        conteos=conteos,
        metricas=civil,
        predicciones=[],
        hallazgos=[],
        por_dominio={
            "telecom": _evaluacion_telecom(),
            "industrial": SIN_HISTORICO,
            "sistemas": SIN_HISTORICO,
        },
    )


def test_los_conteos_nuevos_siguen_dictando_reglas():
    informe = _informe()

    assert "| telecom | 40 | reglas |" in informe
    assert "| industrial | 4 | reglas |" in informe
    assert "| sistemas | 9 | reglas |" in informe
    assert "limitacion" in informe.lower()


def test_la_seccion_por_dominio_tabula_telecom_y_declara_los_no_evaluables():
    from scripts.generar_resultados_ml import SIN_HISTORICO

    informe = _informe()

    assert "## Metricas por dominio" in informe
    assert "Precios ARENAZA (2026-05-18) -> Precios MaPreX 2026-07 (2026-07-09)" in informe
    assert f"| industrial | {SIN_HISTORICO} | — | — | no evaluable |" in informe
    assert f"| sistemas | {SIN_HISTORICO} | — | — | no evaluable |" in informe
    # Solo la partida cuyo PU cambio aparece en la tabla de detalle (1 de 2).
    assert "(1 de 2)" in informe
    assert "| TC-P1-11 | 3.96 | 9.54 | 4.98 | [3.12, 9.54] |" in informe
    assert "TC-P1-01 | 82.68 | 82.68" not in informe


def test_partidas_con_cambio_distingue_las_que_cambiaron():
    evaluacion = _evaluacion_telecom()

    assert [p.codigo_partida for p in evaluacion.partidas_con_cambio] == ["TC-P1-11"]


def test_sin_por_dominio_el_informe_es_el_de_i63():
    from ml.prediction import metricas
    from scripts.generar_resultados_ml import generar_informe

    informe = generar_informe(
        conteos={"civil": 5, "telecom": 0, "industrial": 0, "sistemas": 0},
        metricas=metricas(estimados={"X": Decimal("1")}, reales={"X": Decimal("1")}),
        predicciones=[],
        hallazgos=[],
    )

    assert "Metricas por dominio" not in informe
