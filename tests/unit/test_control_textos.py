"""Los textos del control de obra que ve el usuario llevan tildes (V-20 de la auditoría visual)."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from aplicacion import control
from aplicacion.control import PARAMETROS_EDITABLES
from core.budget.valor_ganado import ParametrosControl

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


def test_el_si_de_los_parametros_se_lee_con_tilde_y_se_acepta_de_vuelta() -> None:
    # VB-5: «si» a la vista; las filas vuelven tal cual a `parametros_desde_filas`.
    filas = control.filas_de_parametros(ParametrosControl())
    por_campo = {f["Parametro"]: f for f in filas}
    assert por_campo["fcas_en_horas_extra"]["Valor"] == "sí"
    assert control.parametros_desde_filas(filas) == ParametrosControl()
    for escrito, esperado in (("sí", True), ("Sí", True), ("si", True), ("no", False)):
        cambiadas = [
            {**f, "Valor": escrito} if f["Parametro"] == "fcas_en_horas_extra" else f for f in filas
        ]
        assert control.parametros_desde_filas(cambiadas).fcas_en_horas_extra is esperado


def test_un_si_o_no_ilegible_se_rechaza_con_el_mensaje_acentuado() -> None:
    filas = [
        {**f, "Valor": "quizas"} if f["Parametro"] == "fcas_en_horas_extra" else f
        for f in control.filas_de_parametros(ParametrosControl())
    ]
    with pytest.raises(control.ControlInvalido, match="escriba sí o no"):
        control.parametros_desde_filas(filas)


def test_los_estudios_que_suma_no_nombran_la_spec() -> None:
    # VB-5: «estudio(s) de S1» era jerga de la especificación.
    estudio = SimpleNamespace(id=3, fecha_calculo=date(2027, 3, 1), monto=Decimal("120.50"))
    resultado = SimpleNamespace(
        reajuste=SimpleNamespace(estudios=[estudio], monto=Decimal("120.50"), moneda="Bs")
    )
    texto = control.estudios_que_suma(resultado)  # type: ignore[arg-type]
    assert texto == (
        "V' suma el reajuste reconocido de 1 estudio(s) de reajuste guardado(s): "
        "#3 (01/03/2027, 120.50); total 120.50 Bs."
    )


def test_la_descripcion_de_la_linea_base_formatea_solo_sus_fechas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Ronda 1, punto 1: el código de la versión lo escribió el usuario («2026-11-10») y no cambia;
    # las dos fechas del sistema (vigente desde, inicio de obra) salen en dd/mm/aaaa.
    fila = SimpleNamespace(
        presupuesto_id=1,
        perspectiva="costo",
        desde=date(2026, 11, 2),
        calendario=SimpleNamespace(fecha_inicio=date(2026, 11, 3), dias_por_periodo=5),
    )
    monkeypatch.setattr(control, "linea_base_vigente", lambda sesion, proyecto, dia: fila)
    sesion = SimpleNamespace(get=lambda modelo, ident: SimpleNamespace(codigo="2026-11-10"))
    assert control.describir_linea_base(sesion, "P") == (  # type: ignore[arg-type]
        "versión 2026-11-10, perspectiva costo, vigente desde 02/11/2026; inicio de obra "
        "03/11/2026 con 5 día(s) hábil(es) por período"
    )


def test_el_dia_con_fecha_lleva_la_fecha_en_dd_mm_aaaa() -> None:
    resultado = SimpleNamespace(
        instantanea=SimpleNamespace(
            calendario=SimpleNamespace(fecha_inicio=date(2026, 11, 2), feriados=())
        )
    )
    # día 1 = lunes 02/11/2026; día 6 = lunes 09/11/2026 (sábado y domingo no son hábiles)
    assert control.dia_con_fecha(resultado, 1) == "día 1 (02/11/2026)"  # type: ignore[arg-type]
    assert control.dia_con_fecha(resultado, 6) == "día 6 (09/11/2026)"  # type: ignore[arg-type]
    assert control.dia_con_fecha(resultado, None) == "no proyectable"  # type: ignore[arg-type]
