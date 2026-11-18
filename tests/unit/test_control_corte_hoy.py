"""El corte del control nunca pasa de hoy y no se registra una valuación del futuro.

Prueba en vivo del 2026-11-18 (frente C, hallazgo 1): una valuación con «hasta» el 04/12 hacía que
la Vista general y el Resumen midieran el plan al 04/12 («Plan 76,7 %») cuando hoy era el 18/11.
La regla R14 (`core/verification/valuaciones.py`) no se toca: el arreglo vive en `aplicacion`.

Obra ficticia OB-S2 (`tests/fixtures/control_ob_s2.py`): V-01 hasta el 2026-11-06, V-02 hasta el
2026-11-13 y la sembrada V-03 (por el núcleo, sin pasar por la pantalla) hasta el 2026-11-20. «Hoy»
se inyecta: ninguna prueba depende del reloj.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from aplicacion import control, mesa
from core.budget.valuaciones import valuaciones_registradas
from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob

HOY = date(2026, 11, 18)


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as abierta:
            ob.sembrar(abierta)
            ob.declarar_linea_base(abierta)
            ob.registrar_v01_y_v02(abierta)
            abierta.commit()
            yield abierta
            abierta.rollback()
    finally:
        motor.dispose()


def _con_v03_futura(sesion) -> None:
    ob.registrar(sesion, ob.VS)  # hasta el 2026-11-20: posterior a HOY
    sesion.commit()


# --- (a) el corte por defecto -------------------------------------------------------------------


def test_el_corte_por_defecto_es_el_ultimo_hasta_si_no_pasa_de_hoy(sesion) -> None:
    assert control.corte_por_defecto(sesion, ob.NOMBRE, hoy=HOY) == date(2026, 11, 13)


def test_el_corte_por_defecto_no_pasa_de_hoy_aunque_la_ultima_valuacion_sea_futura(sesion) -> None:
    _con_v03_futura(sesion)
    assert control.corte_por_defecto(sesion, ob.NOMBRE, hoy=HOY) == HOY
    # pasado el «hasta», el corte vuelve a ser el de la última valuación
    assert control.corte_por_defecto(sesion, ob.NOMBRE, hoy=date(2026, 11, 30)) == date(
        2026, 11, 20
    )


def test_el_calculo_sin_corte_se_hace_a_hoy_y_no_al_hasta_futuro(sesion) -> None:
    _con_v03_futura(sesion)
    resultado = control.calcular_el_control(sesion, ob.NOMBRE, Catalogo(sesion), hoy=HOY)
    assert resultado.instantanea.corte == HOY
    # la futura no cuenta para el valor ganado y R14 la señala
    assert [v.numero for v in resultado.instantanea.para_el_valor_ganado()] == ["V-01", "V-02"]
    assert any(
        h.regla == "R14" and "despues del corte" in h.descripcion
        for h in resultado.informe.hallazgos
    )


def test_sin_valuaciones_el_calculo_sin_corte_sigue_pidiendo_la_fecha(tmp_path: Path) -> None:
    ruta = tmp_path / "solo_linea.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            ob.declarar_linea_base(sesion)
            sesion.commit()
            with pytest.raises(control.ControlInvalido, match="elija la fecha de corte"):
                control.calcular_el_control(sesion, ob.NOMBRE, Catalogo(sesion), hoy=HOY)
    finally:
        motor.dispose()


def test_la_mesa_mide_la_obra_a_hoy_y_no_al_hasta_futuro(sesion) -> None:
    _con_v03_futura(sesion)
    (obra,) = mesa.obras_de_la_mesa(sesion, Catalogo(sesion), HOY)
    assert obra.corte == HOY


# --- (b) no se registra una valuación del futuro -------------------------------------------------


def _registrar(sesion, *, desde: str, hasta: str, fecha: str):
    return control.registrar_y_controlar(
        sesion,
        ob.NOMBRE,
        Catalogo(sesion),
        numero="V-03",
        desde=desde,
        hasta=hasta,
        fecha=fecha,
        inspector=ob.INSPECTOR,
        filas=[{"Partida": "OB-B", "Cantidad": "10"}],
        fuente=ob.FUENTE,
        responsable=ob.RESPONSABLE,
        hoy=HOY,
    )


def _numeros(sesion) -> list[str]:
    return [v.numero for v in valuaciones_registradas(sesion, ob.NOMBRE)]


def test_una_valuacion_que_termina_despues_de_hoy_se_rechaza_y_no_se_guarda(sesion) -> None:
    with pytest.raises(control.ControlInvalido) as error:
        _registrar(sesion, desde="2026-11-16", hasta="2026-11-20", fecha="2026-11-20")
    assert str(error.value) == (
        "El «Período hasta» (20/11/2026) es posterior a hoy (18/11/2026): una valuación solo "
        "mide obra ya ejecutada. Regístrela cuando termine el período."
    )
    assert _numeros(sesion) == ["V-01", "V-02"]


def test_una_fecha_de_valuacion_posterior_a_hoy_se_rechaza(sesion) -> None:
    with pytest.raises(control.ControlInvalido) as error:
        _registrar(sesion, desde="2026-11-16", hasta="2026-11-18", fecha="2026-11-19")
    assert str(error.value) == (
        "La «Fecha de la valuación» (19/11/2026) es posterior a hoy (18/11/2026): use la fecha "
        "en que se firmó, que no puede ser futura."
    )
    assert _numeros(sesion) == ["V-01", "V-02"]


def test_una_valuacion_hasta_hoy_se_registra(sesion) -> None:
    resultado = _registrar(sesion, desde="2026-11-16", hasta="2026-11-18", fecha="2026-11-18")
    assert resultado.instantanea.corte == HOY
    assert _numeros(sesion) == ["V-01", "V-02", "V-03"]
