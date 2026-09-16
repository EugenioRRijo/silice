"""Sesion I6.3: prediccion de precio por sistema de reglas (UC-07, compuerta G2).

La compuerta G2 (CLAUDE.md §8.1) elige la tecnica por el conteo de registros de APU del dominio:
`tecnica_para` ES esa tabla hecha codigo (meta M5 de `scripts/meta_i6.py`). Con los conteos
del proyecto (civil = 5, el resto 0) toca **sistema de reglas con analisis de sensibilidad,
declarado como limitacion** (metas M6 y M7).

`ml/prediction` recibe datos planos, como el resto de `ml/` (CLAUDE.md §2): precios unitarios
base por partida y la serie de variaciones del historico de cambios; devuelve predicciones con su
rango de sensibilidad, metricas (MAPE, RMSE, R2, en `Decimal`) y el contraste AACE clase 3, que
produce un `Hallazgo` de severidad ADVERTENCIA del contrato `core.contracts.verificacion` cuando
el precio construido se aparta del estimado mas alla del rango declarado (RF-29).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.contracts.verificacion import Severidad


def test_tecnica_para_es_la_tabla_de_la_compuerta_g2():
    """CLAUDE.md §8.1: < 50 reglas; 50-200 casos; > 200 XGBoost. Bordes incluidos."""
    from ml.prediction import Tecnica, tecnica_para

    assert tecnica_para(0) is Tecnica.REGLAS
    assert tecnica_para(5) is Tecnica.REGLAS  # el conteo real del dominio civil
    assert tecnica_para(49) is Tecnica.REGLAS
    assert tecnica_para(50) is Tecnica.CASOS
    assert tecnica_para(200) is Tecnica.CASOS
    assert tecnica_para(201) is Tecnica.XGBOOST


def test_prediccion_por_reglas_con_rango_de_sensibilidad():
    """La regla: PU estimado = PU base x (1 + media de las variaciones del historico); el rango
    de sensibilidad recorre la variacion minima y la maxima observadas. Todo `Decimal` exacto.
    """
    from ml.prediction import predecir_por_reglas

    predicciones = predecir_por_reglas({"A": Decimal("100")}, [Decimal("0.2"), Decimal("0.1")])

    assert len(predicciones) == 1
    prediccion = predicciones[0]
    assert prediccion.codigo_partida == "A"
    assert prediccion.pu_base == Decimal("100")
    assert prediccion.pu_estimado == Decimal("115.0")  # media(0.2, 0.1) = 0.15
    assert prediccion.pu_minimo == Decimal("110.0") and prediccion.pu_maximo == Decimal("120.0")


def test_sin_historico_de_variaciones_la_prediccion_es_el_precio_base():
    from ml.prediction import predecir_por_reglas

    (prediccion,) = predecir_por_reglas({"A": Decimal("100")}, [])
    assert prediccion.pu_estimado == Decimal("100")
    assert prediccion.pu_minimo == prediccion.pu_maximo == Decimal("100")


def test_metricas_exactas_mape_rmse_r2():
    """RF-28: MAPE, RMSE y R2 sobre un ejemplo calculable a mano, en `Decimal` exacto."""
    from ml.prediction import metricas

    resultado = metricas(
        estimados={"A": Decimal("110"), "B": Decimal("190")},
        reales={"A": Decimal("100"), "B": Decimal("200")},
    )

    assert resultado.mape == Decimal("0.075")  # media(10 %, 5 %)
    assert resultado.rmse == Decimal("10")  # sqrt((10^2 + 10^2) / 2)
    assert resultado.r2 == Decimal("0.96")  # 1 - 200 / 5000


def test_metricas_exigen_las_mismas_partidas():
    from ml.prediction import metricas

    with pytest.raises(ValueError, match="mismas partidas"):
        metricas(estimados={"A": Decimal("1")}, reales={"B": Decimal("1")})


def test_contraste_aace_dentro_del_rango_no_produce_hallazgo():
    from ml.prediction import contrastar_aace

    # Desviacion (construido - estimado) / estimado = -2.944 %: dentro de la clase 3.
    assert contrastar_aace("LB-04-CON", Decimal("242.64"), Decimal("250")) is None
    # Los limites declarados (-20 %, +30 %) son inclusivos.
    assert contrastar_aace("X", Decimal("130"), Decimal("100")) is None
    assert contrastar_aace("X", Decimal("80"), Decimal("100")) is None


def test_contraste_aace_fuera_del_rango_es_hallazgo_advertencia():
    """RF-29: la desviacion se expresa en porcentaje y el hallazgo es ADVERTENCIA, con el
    construido como valor observado y el estimado como valor esperado.
    """
    from ml.prediction import contrastar_aace

    hallazgo = contrastar_aace("LB-04-CON", Decimal("350"), Decimal("250"))

    assert hallazgo is not None
    assert hallazgo.severidad is Severidad.ADVERTENCIA
    assert "40" in hallazgo.descripcion and "AACE" in hallazgo.descripcion
    assert hallazgo.valor_observado == Decimal("350")
    assert hallazgo.valor_esperado == Decimal("250")
    assert hallazgo.origen_ids == ("LB-04-CON",)

    por_debajo = contrastar_aace("X", Decimal("75"), Decimal("100"))
    assert por_debajo is not None and por_debajo.severidad is Severidad.ADVERTENCIA


def test_contraste_aace_presenta_a_dos_decimales_con_redondeo_hacia_arriba():
    """Sesion M4.1: la descripcion presenta importes y desviacion a dos decimales con
    ROUND_HALF_UP, la convencion de `core.verification.texto.formatear_decimal`; el formato
    `:.2f` de `Decimal` redondea al par y presentaria 2.125 como 2.12. Los valores del hallazgo
    siguen exactos.
    """
    from ml.prediction import contrastar_aace

    importe_empatado = contrastar_aace("X", Decimal("2.125"), Decimal("1"))
    assert importe_empatado is not None
    assert "(2.13)" in importe_empatado.descripcion
    assert "(1.00)" in importe_empatado.descripcion
    assert importe_empatado.valor_observado == Decimal("2.125")

    # (1400.25 - 1000) / 1000 = 40.025 %: al par seria +40.02.
    desviacion_empatada = contrastar_aace("X", Decimal("1400.25"), Decimal("1000"))
    assert desviacion_empatada is not None
    assert "+40.03 %" in desviacion_empatada.descripcion


def test_contraste_con_estimado_no_positivo_se_rechaza():
    from ml.prediction import contrastar_aace

    with pytest.raises(ValueError, match="estimado"):
        contrastar_aace("X", Decimal("100"), Decimal("0"))
