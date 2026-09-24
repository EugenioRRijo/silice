"""Sesion I6.3: el informe `docs/resultados_ml.md` (RF-28, meta M8 de `scripts/meta_i6.py`).

`scripts/generar_resultados_ml.py` separa el armado del texto (`generar_informe`, puro y probado
aqui) del acopio de datos (conteo por dominio y evaluacion sobre la linea base, que corren contra
una base sembrada al ejecutar el script). El informe declara el conteo de la compuerta G2, la
tecnica elegida, las metricas obligatorias (MAPE, RMSE, R2) y la limitacion de la tecnica de
reglas, como exige CLAUDE.md §8.1.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("sklearn")  # scripts/generar_resultados_ml.py importa ml (extra `ml`)


def _informe(conteos: dict[str, int] | None = None) -> str:
    from ml.prediction import PrediccionPrecio, contrastar_aace, metricas
    from scripts.generar_resultados_ml import generar_informe

    if conteos is None:
        conteos = {"civil": 5, "telecom": 0, "industrial": 0, "sistemas": 0}
    estimados = {"LB-04-CON": Decimal("279.04")}
    reales = {"LB-04-CON": Decimal("272.81")}
    predicciones = [
        PrediccionPrecio(
            codigo_partida="LB-04-CON",
            pu_base=Decimal("242.64"),
            pu_estimado=Decimal("279.04"),
            pu_minimo=Decimal("266.90"),
            pu_maximo=Decimal("291.17"),
        )
    ]
    hallazgos = [
        h
        for codigo in reales
        if (h := contrastar_aace(codigo, reales[codigo], estimados[codigo])) is not None
    ]
    return generar_informe(
        conteos=conteos,
        metricas=metricas(estimados=estimados, reales=reales),
        predicciones=predicciones,
        hallazgos=hallazgos,
    )


def test_el_informe_declara_conteo_tecnica_y_metricas():
    informe = _informe()

    # Compuerta G2 (INV-017): la fila exacta de cada dominio con su conteo y la tecnica que dicta
    # la tabla de CLAUDE.md §8.1 (menos de 50 registros: reglas). Oraculo escrito a mano desde esa
    # tabla, no con `tecnica_para`: una fila con otro conteo u otra tecnica no pasa.
    assert "| civil | 5 | reglas |" in informe
    for dominio in ("industrial", "sistemas", "telecom"):
        assert f"| {dominio} | 0 | reglas |" in informe

    # RF-28: las tres metricas obligatorias, con su fila exacta. Oraculo a mano sobre `_informe()`
    # (un solo par estimado/real de LB-04-CON):
    # - MAPE = |279.04 - 272.81| / 272.81 = 6.23 / 272.81 = 0.022836..., es decir 2.28 %;
    # - RMSE = raiz(6.23 ** 2) = 6.23 USD;
    # - R2 no se define con un solo real (varianza nula): el informe lo dice con palabras.
    assert "| MAPE | 2.28 % |" in informe
    assert "| RMSE | 6.23 USD |" in informe
    assert "| R2 | sin varianza en los reales |" in informe

    # La tecnica de reglas se declara como limitacion, no como logro (CLAUDE.md §8.1): la frase
    # exacta, no la palabra suelta, que tambien aparece en otros parrafos del informe.
    assert "como **limitacion** del trabajo, no como logro" in informe


def test_el_informe_tabula_las_predicciones_con_su_rango():
    informe = _informe()
    assert "LB-04-CON" in informe
    assert "279.04" in informe  # estimado
    assert "266.90" in informe and "291.17" in informe  # rango de sensibilidad


def test_con_un_dominio_en_el_umbral_el_informe_no_afirma_que_todos_estan_por_debajo():
    """INV-079: el parrafo de G2 se deriva de los conteos. Con telecom en 50 registros (el umbral de
    CLAUDE.md §8.1, que ya dicta razonamiento basado en casos) no puede afirmar que todos los
    dominios estan por debajo de 50 ni declarar la tecnica de reglas como la que dicta la tabla."""
    informe = _informe({"civil": 5, "telecom": 50, "industrial": 4, "sistemas": 9})

    assert "| telecom | 50 | casos |" in informe  # oraculo a mano desde la tabla de §8.1
    assert "Todos los dominios estan por debajo" not in informe
    assert "Al menos un dominio alcanza los 50 registros" in informe
