"""Los hallazgos de una valuación se leen: regla, severidad y un mensaje legible.

Prueba en vivo del 2026-11-18 (frente C, hallazgo 2): al registrar salía en verde «Valuación
registrada… 4 hallazgo(s) (4 con severidad Error)» y la tabla solo decía «ERROR: R14», sin decir
qué estaba mal. Los mensajes de R13 y R14 nacen en `core/verification/valuaciones.py` sin tildes,
con fechas ISO y punto decimal, y `core/` no se toca: `aplicacion` los presenta.

Oráculos escritos a mano. La obra es OB-S2 (`tests/fixtures/control_ob_s2.py`) con V-01, V-02 y la
V-03 sembrada por el núcleo (sin inspector, con OB-D que la línea base no tiene, OB-B por encima de
lo presupuestado, una medición fuera de su período y un período que se solapa con el de V-02).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from aplicacion import control
from aplicacion.control_hallazgos import hallazgos_de_valuaciones, mensaje_de_hallazgo
from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob

HOY = date(2026, 11, 18)


@pytest.mark.parametrize(
    ("del_nucleo", "legible"),
    [
        (
            "la valuacion V-03 valua la partida OB-D, que la linea base no tiene: sin unitario, "
            "no se cuantifica",
            "La valuación V-03 valúa la partida OB-D, que la línea base no tiene: sin unitario, "
            "no se cuantifica.",
        ),
        (
            "la partida OB-B lleva 1234.5 valuados y la linea base presupuesta 200: exceso de "
            "1034.5 desde la valuacion V-03",
            "La partida OB-B lleva 1.234,5 valuados y la línea base presupuesta 200: exceso de "
            "1.034,5 desde la valuación V-03.",
        ),
        (
            "la partida OB-C esta presupuestada y el plan de la linea base no la programa en "
            "ningun periodo",
            "La partida OB-C está presupuestada y el plan de la línea base no la programa en "
            "ningún período.",
        ),
        ("la valuacion V-03 no tiene numero", "La valuación V-03 no tiene número."),
        ("la valuacion V-03 no tiene inspector", "La valuación V-03 no tiene inspector."),
        ("la valuacion #7 no tiene fecha", "La valuación #7 no tiene fecha."),
        (
            "la valuacion V-03 empieza el 2026-11-20, despues de su fin (2026-11-12)",
            "La valuación V-03 empieza el 20/11/2026, después de su fin (12/11/2026).",
        ),
        (
            "la valuacion V-03 tiene fecha 2026-11-19, anterior a su fin (2026-11-20)",
            "La valuación V-03 tiene fecha 19/11/2026, anterior a su fin (20/11/2026).",
        ),
        (
            "la valuacion V-03 termina el 2026-11-20, despues del corte (2026-11-18)",
            "La valuación V-03 termina el 20/11/2026, después del corte (18/11/2026).",
        ),
        (
            "la valuacion V-03 empieza el 2026-10-26, antes del inicio del calendario "
            "(2026-11-02)",
            "La valuación V-03 empieza el 26/10/2026, antes del inicio del calendario "
            "(02/11/2026).",
        ),
        (
            "la medicion de OB-C en la valuacion V-03 es del 2026-11-23, fuera de su periodo "
            "2026-11-12 a 2026-11-20",
            "La medición de OB-C en la valuación V-03 es del 23/11/2026, fuera de su período "
            "12/11/2026 a 20/11/2026.",
        ),
        ("el numero V-02 esta repetido", "El número V-02 está repetido."),
        (
            "el periodo de la valuacion V-03 (2026-11-12 a 2026-11-20) se solapa con el de la "
            "V-02 (2026-11-09 a 2026-11-13)",
            "El período de la valuación V-03 (12/11/2026 a 20/11/2026) se solapa con el de la "
            "V-02 (09/11/2026 a 13/11/2026).",
        ),
        (
            "las valuaciones V-01 y V-03 no son consecutivas: falta al menos un numero",
            "Las valuaciones V-01 y V-03 no son consecutivas: falta al menos un número.",
        ),
        (
            "entre las valuaciones V-01 y V-02 hay 3 dia(s) habil(es) sin cubrir (2026-11-09 a "
            "2026-11-11)",
            "Entre las valuaciones V-01 y V-02 hay 3 día(s) hábil(es) sin cubrir (09/11/2026 a "
            "11/11/2026).",
        ),
    ],
)
def test_cada_frase_de_r13_y_r14_sale_con_tildes_fechas_del_sistema_y_coma(
    del_nucleo: str, legible: str
) -> None:
    assert mensaje_de_hallazgo(del_nucleo) == legible


def test_una_frase_que_no_es_del_nucleo_solo_se_cierra_con_mayuscula_y_punto() -> None:
    assert mensaje_de_hallazgo("algo nuevo del nucleo") == "Algo nuevo del nucleo."


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
            ob.registrar(abierta, ob.VS)
            abierta.commit()
            yield abierta
            abierta.rollback()
    finally:
        motor.dispose()


def test_los_hallazgos_de_las_valuaciones_dicen_valuacion_regla_severidad_y_mensaje(
    sesion,
) -> None:
    resultado = control.calcular_el_control(sesion, ob.NOMBRE, Catalogo(sesion), hoy=HOY)
    filas = hallazgos_de_valuaciones(resultado)
    assert {tuple(f.values()) for f in filas} == {
        (
            "V-03",
            "R13",
            "Error",
            "La valuación V-03 valúa la partida OB-D, que la línea base no tiene: sin unitario, "
            "no se cuantifica.",
        ),
        (
            "V-03",
            "R13",
            "Error",
            "La partida OB-B lleva 210 valuados y la línea base presupuesta 200: exceso de 10 "
            "desde la valuación V-03.",
        ),
        ("V-03", "R14", "Error", "La valuación V-03 no tiene inspector."),
        (
            "V-03",
            "R14",
            "Error",
            "La valuación V-03 tiene fecha 19/11/2026, anterior a su fin (20/11/2026).",
        ),
        (
            "V-03",
            "R14",
            "Error",
            "La valuación V-03 termina el 20/11/2026, después del corte (18/11/2026).",
        ),
        (
            "V-03",
            "R14",
            "Error",
            "La medición de OB-C en la valuación V-03 es del 23/11/2026, fuera de su período "
            "12/11/2026 a 20/11/2026.",
        ),
        (
            "V-03",
            "R14",
            "Error",
            "El período de la valuación V-03 (12/11/2026 a 20/11/2026) se solapa con el de la "
            "V-02 (09/11/2026 a 13/11/2026).",
        ),
    }
    assert list(filas[0]) == ["Valuacion", "Regla", "Severidad", "Mensaje"]
    # los errores primero
    rangos = {"Error": 0, "Advertencia": 1, "Información": 2}
    assert [rangos[f["Severidad"]] for f in filas] == sorted(rangos[f["Severidad"]] for f in filas)
