"""Los textos del control de obra que ve el usuario llevan tildes (V-20 de la auditoría visual)."""

from aplicacion.control import PARAMETROS_EDITABLES

QUE_ES_ESPERADO = {
    "spi_error": "SPI por debajo del cual el retraso es ERROR (AL-1)",
    "cpi_error": "CPI por debajo del cual el sobrecosto es ERROR (AL-2)",
    "retraso_error": "Retraso del término, fracción de D, que pasa a ERROR (AL-3)",
    "precio_info": "Desvío de precio, fracción del EV, que avisa (AL-5)",
    "equilibrio_puntos": "Puntos porcentuales de subida del PE que advierten (AL-4)",
    "eta_cuadrilla": "Eficiencia de cada cuadrilla adicional (eta)",
    "cuadrillas_max": "Cuadrillas máximas por frente",
    "eta_horas_extra": "Eficiencia de la hora extra (eta_he)",
    "horas_extra_dia": "Horas extra por día (tope legal 2)",
    "recargo_horas_extra": "Recargo de las horas extra (mínimo legal 0,50)",
    "fcas_en_horas_extra": "FCAS sobre las horas extra (sí o no)",
    "penalizacion_diaria": "Penalización por día de retraso del contrato",
    "fuente_penalizacion": "Fuente de la penalización",
}


def test_los_parametros_de_control_se_explican_con_tildes() -> None:
    assert {campo: que_es for campo, que_es, _ in PARAMETROS_EDITABLES} == QUE_ES_ESPERADO
