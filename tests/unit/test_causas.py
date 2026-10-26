"""Causas de retraso y atraso por partida (MP-7, Tarea 22; diseño §11, meta 2).

`aplicacion/causas.py` guarda la causa elegida en cada línea de una valuación (en la misma
transacción que la valuación, `aplicacion.control.registrar_y_controlar`) y dice, por partida,
cuántos días hábiles termina después de su plan y por qué.

Oráculos escritos a mano, con la cuenta al lado; ninguno sale del código bajo prueba. La
reproyección es la del núcleo (`core/budget/valor_ganado.py:623-697`): ritmo `r = índice / n` por
período, `fin = base + última · L / r`. `fin_plan` es el último período del plan con fracción mayor
que 0 por los días del período (1: el plan es en días hábiles). Obras de
`tests/fixtures/obra_atrasada.py`.

Las bases viven en `tmp_path` (`preparar_base`): nada en `data/`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import inspect, select, text

from aplicacion import control
from aplicacion.causas import CAUSAS, Atraso, atrasos, texto_de_atraso
from aplicacion.tablas_causas import CausaDeRetraso
from core import models
from core.budget.valuaciones import valuaciones_registradas
from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import obra_atrasada as obra

D = Decimal
TABLA = "mp_causa_retraso"
MENSAJE_DESCONOCIDA = "La causa del retraso no está en la lista de causas."


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator:
    ruta = tmp_path / "carpeta.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as abierta:
            yield abierta
            abierta.rollback()
    finally:
        motor.dispose()


@pytest.fixture
def dos(sesion):
    obra.sembrar_dos_partidas(sesion)
    sesion.commit()
    return sesion


def _registrar(
    sesion,
    lineas: list[dict[str, object]],
    *,
    numero: str = "V-01",
    desde: str = "2026-11-02",
    hasta: str = "2026-11-06",
    nombre: str = obra.NOMBRE,
):
    return control.registrar_y_controlar(
        sesion,
        nombre,
        Catalogo(sesion),
        numero=numero,
        desde=desde,
        hasta=hasta,
        fecha=hasta,
        inspector="Ing. Ficticio",
        filas=lineas,
        fuente=obra.FUENTE,
        responsable=obra.RESPONSABLE,
    )


def _linea(partida: str, cantidad: str, causa: str | None = None) -> dict[str, object]:
    return {"Partida": partida, "Cantidad": cantidad, "Causa": causa}


def _filas_de_causas(sesion) -> list[tuple[int, str, str]]:
    return [
        (fila.valuacion_id, fila.codigo_partida, fila.causa)
        for fila in sesion.scalars(select(CausaDeRetraso).order_by(CausaDeRetraso.id))
    ]


# --- el catálogo de causas y el texto ---------------------------------------------------------


def test_las_siete_causas_del_plan_en_su_orden() -> None:
    assert list(CAUSAS.items()) == [
        ("compra_tardia", "Compra tardía"),
        ("precio", "Precio"),
        ("clima", "Lluvia o clima"),
        ("cambio_cliente", "Cambio del cliente"),
        ("falta_personal", "Falta de personal"),
        ("falla_equipo", "Falla de equipo"),
        ("otra", "Otra"),
    ]


@pytest.mark.parametrize(
    ("codigo", "dias", "causa", "esperado"),
    [
        ("A", 5, "compra_tardia", "A atrasada 5 días: Compra tardía"),
        ("A", 1, None, "A atrasada 1 día: sin causa declarada"),
        # los enteros llevan punto de miles, como en la mesa
        ("OBRA-05", 1200, "clima", "OBRA-05 atrasada 1.200 días: Lluvia o clima"),
    ],
)
def test_el_texto_de_un_atraso(codigo: str, dias: int, causa: str | None, esperado: str) -> None:
    assert texto_de_atraso(codigo, dias, causa) == esperado


# --- la obra de dos partidas -----------------------------------------------------------------


def test_a_a_la_mitad_al_fin_de_su_plan_con_compra_tardia(dos) -> None:
    # Corte: viernes 2026-11-06, día hábil 5. PV = A 10 × 60 × 1 (sus 5 días) + B 0 = 600;
    # EV = 5 × 60 = 300; SPI = 300 / 600 = 0,5.
    resultado = _registrar(dos, [_linea("A", "5", "compra_tardia")])
    assert resultado.estado.dia == 5
    assert resultado.indicadores.spi == D("0.5")
    # A: índice 5 / (10 × 1) = 0,5; n = 5; r = 0,1; pendiente 0,5 desde el período 6: 0,1 en los
    # períodos 6 a 10; fin = (10 − 1) × 1 + 0,1 × 1 / 0,1 = 10. Plan: último período 5 → fin_plan 5.
    # ⌈10 − 5⌉ = 5 días.
    assert resultado.reproyeccion.de("A").fin == D("10")
    # B: sin avance propio, índice = SPI 0,5; n = 2; r = 0,25; períodos 6 a 9;
    # fin = (9 − 1) + 0,25 / 0,25 = 9; fin_plan 7 → ⌈2⌉ = 2 días.
    assert resultado.reproyeccion.de("B").fin == D("9")
    assert atrasos(dos, resultado) == [
        Atraso("A", 5, "compra_tardia", "A atrasada 5 días: Compra tardía"),
        Atraso("B", 2, None, "B atrasada 2 días: sin causa declarada"),
    ]


def test_la_causa_se_guarda_con_la_valuacion_y_su_momento(dos) -> None:
    _registrar(dos, [_linea("A", "5", "compra_tardia"), _linea("B", "0")])
    (valuacion,) = valuaciones_registradas(dos, obra.NOMBRE)
    assert _filas_de_causas(dos) == [(valuacion.id, "A", "compra_tardia")]
    fila = dos.scalars(select(CausaDeRetraso)).one()
    assert fila.fecha_hora == dos.get(models.Valuacion, valuacion.id).fecha_hora


def test_un_dia_se_dice_en_singular(dos) -> None:
    # A 9 de 10: índice 0,9, r = 0,18, pendiente 0,1: cabe en el período 6 (el siguiente al
    # corte), así que fin = día del corte 5 + 0,1 / 0,18 = 5,5556 → ⌈0,5556⌉ = 1 día.
    # B con el SPI 0,9: r = 0,45; 0,45 + 0,45 + 0,1 en los períodos 6 a 8;
    # fin = 7 + 0,1 / 0,45 = 7,2222; fin_plan 7 → ⌈0,2222⌉ = 1 día.
    resultado = _registrar(dos, [_linea("A", "9", "compra_tardia")])
    assert atrasos(dos, resultado) == [
        Atraso("A", 1, "compra_tardia", "A atrasada 1 día: Compra tardía"),
        Atraso("B", 1, None, "B atrasada 1 día: sin causa declarada"),
    ]


def test_sin_atraso_no_hay_filas(dos) -> None:
    # A completa a tiempo: SPI 1; A no tiene fin (nada pendiente). B con r = 1 / 2 en los
    # períodos 6 y 7: fin = 6 + 0,5 / 0,5 = 7 = fin_plan → 0 días: no entra.
    resultado = _registrar(dos, [_linea("A", "10", "clima")])
    assert resultado.indicadores.spi == D("1")
    assert atrasos(dos, resultado) == []


def test_manda_la_ultima_causa_declarada_para_la_partida(dos) -> None:
    # V-01 (hasta el miércoles 2026-11-04) A 3 por la lluvia; V-02 (hasta el viernes) A 2 por la
    # compra tardía. Al día 5: A 5 de 10, igual que la primera prueba → 5 días.
    _registrar(dos, [_linea("A", "3", "clima")], hasta="2026-11-04")
    resultado = _registrar(
        dos, [_linea("A", "2", "compra_tardia")], numero="V-02", desde="2026-11-05"
    )
    assert atrasos(dos, resultado)[0] == Atraso(
        "A", 5, "compra_tardia", "A atrasada 5 días: Compra tardía"
    )


def test_la_causa_de_una_valuacion_anulada_no_cuenta(dos) -> None:
    _registrar(dos, [_linea("A", "5", "compra_tardia")])
    ((primera, _),) = control.valuaciones_para_anular(dos, obra.NOMBRE)
    control.anular(dos, primera, motivo="mal medida", responsable=obra.RESPONSABLE)
    resultado = _registrar(dos, [_linea("A", "5")], numero="V-02")
    # el rastro conserva la fila de la anulada (solo inserción), pero ya no cuenta
    assert _filas_de_causas(dos) == [(primera, "A", "compra_tardia")]
    assert atrasos(dos, resultado)[0] == Atraso(
        "A", 5, None, "A atrasada 5 días: sin causa declarada"
    )


def test_la_causa_de_una_valuacion_posterior_al_corte_no_cuenta(dos) -> None:
    _registrar(dos, [_linea("A", "5")])
    _registrar(
        dos,
        [_linea("A", "1", "clima")],
        numero="V-02",
        desde="2026-11-09",
        hasta="2026-11-10",
    )
    resultado = control.calcular_el_control(
        dos, obra.NOMBRE, Catalogo(dos), corte=date(2026, 11, 6)
    )
    assert atrasos(dos, resultado)[0] == Atraso(
        "A", 5, None, "A atrasada 5 días: sin causa declarada"
    )


@pytest.mark.parametrize("causa", [None, "", "  "])
def test_sin_causa_no_queda_rastro(dos, causa: str | None) -> None:
    resultado = _registrar(dos, [_linea("A", "5", causa)])
    assert _filas_de_causas(dos) == []
    assert atrasos(dos, resultado)[0].causa is None


def test_una_causa_desconocida_se_rechaza_sin_eco_y_no_se_guarda_nada(dos) -> None:
    with pytest.raises(control.ControlInvalido) as error:
        _registrar(dos, [_linea("A", "5", "<b>inventada</b>")])
    assert str(error.value) == MENSAJE_DESCONOCIDA
    assert "inventada" not in str(error.value)
    # todo o nada: ni la valuación ni la causa
    assert valuaciones_registradas(dos, obra.NOMBRE) == []
    assert _filas_de_causas(dos) == []


def test_una_base_sin_la_tabla_se_lee_sin_causas_y_la_crea_al_registrar_una(dos) -> None:
    dos.execute(text(f"DROP TABLE {TABLA}"))
    dos.commit()
    resultado = _registrar(dos, [_linea("A", "5")])
    assert atrasos(dos, resultado)[0].causa is None
    assert not inspect(dos.connection()).has_table(TABLA)  # leer no la crea
    resultado = _registrar(
        dos,
        [_linea("A", "1", "falla_equipo")],
        numero="V-02",
        desde="2026-11-09",
        hasta="2026-11-09",
    )
    assert inspect(dos.connection()).has_table(TABLA)
    assert atrasos(dos, resultado)[0].causa == "falla_equipo"


# --- foco 4: la vivienda con el concreto atrasado ----------------------------------------------


def test_la_vivienda_con_el_concreto_a_la_mitad_dice_atrasada_y_nombra_obra_02(sesion) -> None:
    # Plan desde los rendimientos (T21): OBRA-01 días 1-4, OBRA-02 días 5-6, OBRA-03 días 7-10,
    # OBRA-04 días 11-28 (17,5), OBRA-05 días 28-51 (23,5), OBRA-06 días 52-58.
    # Corte: lunes 2026-11-09, día hábil 6 (el fin del plan de OBRA-02), con OBRA-01 completa (18)
    # y OBRA-02 a la mitad (6 de 12) por una compra tardía.
    obra.sembrar_vivienda(sesion)
    sesion.commit()
    resultado = _registrar(
        sesion,
        [_linea("OBRA-01", "18"), _linea("OBRA-02", "6", "compra_tardia")],
        hasta="2026-11-09",
        nombre=obra.VIVIENDA,
    )
    # Costo directo con FCAS 0 y bono 0: OBRA-01 u = (2 × 40 + 3) / 4,5 + 2; × 18 = 332 + 36 = 368;
    # OBRA-02 u = (2 × 45 + 60) / 6 + 95 = 120; × 12 = 1 440.
    # PV = 368 + 1 440 = 1 808; EV = 368 + 720 = 1 088; SPI = 1 088 / 1 808 = 0,60177 → 0,6018 < 1
    spi = resultado.indicadores.spi
    assert spi is not None and spi < 1
    assert spi.quantize(D("0.0001")) == D("0.6018")
    # OBRA-02: índice 6 / 12 = 0,5; r = 0,25; 0,25 en los períodos 7 y 8; fin = 7 + 1 = 8;
    # fin_plan 6 → 2 días. Las demás, sin avance propio, van al SPI s = 0,60177 (1 / s = 1,66176):
    # OBRA-03 desde el 7: fin = 6 + 4 / s = 12,647; fin_plan 10 → ⌈2,647⌉ = 3.
    # OBRA-04 desde el 11: fin = 10 + 18 / s = 39,912; fin_plan 28 → ⌈11,912⌉ = 12.
    # OBRA-05 desde el 28: fin = 27 + 24 / s = 66,882; fin_plan 51 → ⌈15,882⌉ = 16.
    # OBRA-06 desde el 52: fin = 51 + 7 / s = 62,632; fin_plan 58 → ⌈4,632⌉ = 5.
    # OBRA-01 está completa: no tiene fin.
    assert resultado.reproyeccion.de("OBRA-02").fin == D("8")
    assert atrasos(sesion, resultado) == [
        Atraso("OBRA-02", 2, "compra_tardia", "OBRA-02 atrasada 2 días: Compra tardía"),
        Atraso("OBRA-03", 3, None, "OBRA-03 atrasada 3 días: sin causa declarada"),
        Atraso("OBRA-04", 12, None, "OBRA-04 atrasada 12 días: sin causa declarada"),
        Atraso("OBRA-05", 16, None, "OBRA-05 atrasada 16 días: sin causa declarada"),
        Atraso("OBRA-06", 5, None, "OBRA-06 atrasada 5 días: sin causa declarada"),
    ]
