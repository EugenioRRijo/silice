"""UC-18 sin Streamlit (S1, Tarea 13): del texto de la pantalla al estudio, lado a lado y Excel."""

from datetime import date
from decimal import Decimal as D  # noqa: N817
from io import BytesIO

import openpyxl
import pytest

from aplicacion import reajuste
from aplicacion.hoja import HojaInvalida
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from tests.fixtures.reajuste_pantalla import CAMPOS, COMPONENTES, EJECUTADO, PERIODOS
from tests.fixtures.reajuste_s1 import NOMBRE, sembrar


def test_lado_a_lado_guardado_y_excel_con_sus_totales(tmp_path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'r.db').as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        sembrar(sesion)
        sesion.commit()
        clausula = reajuste.clausula_desde_textos(CAMPOS, COMPONENTES)
        periodos = reajuste.periodos_desde_filas(PERIODOS, EJECUTADO)
        resultado = reajuste.calcular(
            sesion, NOMBRE, "001", clausula, periodos, fecha_calculo=date(2027, 3, 5)
        )
        fila = reajuste.filas_lado_a_lado(resultado)[0]
        assert (fila["Escalatoria"], fila["Comprobación"], fila["Diferencia (otra)"]) == (
            "15300.00",
            "16000.00",
            "-0.82",
        )
        estudio_id = reajuste.guardar(
            sesion,
            NOMBRE,
            "001",
            clausula,
            periodos,
            fecha_calculo=date(2027, 3, 5),
            fuente="estudio",
            responsable="Ing.",
        )
        libro = openpyxl.load_workbook(
            BytesIO(reajuste.excel_en_bytes(sesion, NOMBRE, "001", resultado, periodos))
        )
        hoja = libro["Reajuste"]
        assert [c.value for c in hoja[1]][:5] == list(reajuste.COLUMNAS_REAJUSTE[:5])
        assert D(str(hoja.cell(2, 2).value)) == D(15300) and estudio_id > 0
    motor.dispose()


@pytest.mark.parametrize(
    ("cambio", "dice"),
    [
        ({"fecha_inicio": ""}, "Escriba «Inicio del contrato»"),
        ({"fecha_inicio": "15/01/2026"}, "Inicio del contrato: '15/01/2026' no es una fecha"),
        ({"duracion_meses": "dos años"}, "Duración (meses): escriba un número entero"),
        ({"mecanismo": "ninguno"}, "Mecanismo: 'ninguno'; se espera uno de"),
        ({"r": "0,10"}, "R (fracción no reajustable)"),
        ({"fuente": ""}, "Escriba «Fuente de la cláusula»"),
    ],
)
def test_un_campo_malo_se_nombra_como_lo_ve_la_persona(cambio, dice):
    with pytest.raises(HojaInvalida) as error:
        reajuste.clausula_desde_textos({**CAMPOS, **cambio}, COMPONENTES)
    assert dice in str(error.value)
    assert "_" not in str(error.value).split(":")[0]  # ningun nombre interno de campo


def test_pesos_que_no_suman_uno_se_rechazan_con_la_regla_de_la_clausula():
    componentes = [{**COMPONENTES[0], "peso": "0.9"}, *COMPONENTES[1:]]
    with pytest.raises(HojaInvalida, match="La cláusula no es válida"):
        reajuste.clausula_desde_textos(CAMPOS, componentes)


def test_lo_ejecutado_de_un_periodo_inexistente_o_sin_fuente_se_rechaza():
    with pytest.raises(HojaInvalida, match="Período 2: no hay un período"):
        reajuste.periodos_desde_filas(PERIODOS, [{**EJECUTADO[0], "periodo": "2"}])
    with pytest.raises(HojaInvalida, match="Escriba «Fuente de lo ejecutado»"):
        reajuste.periodos_desde_filas(PERIODOS, [{**EJECUTADO[0], "fuente": ""}])
    with pytest.raises(HojaInvalida, match="cantidad de S1-R01"):
        reajuste.periodos_desde_filas(PERIODOS, [{**EJECUTADO[0], "cantidad": "1.000,5"}])


@pytest.mark.parametrize(
    ("cambio", "dice"),
    [
        # VB-5: las reglas de la cláusula vienen del núcleo sin tildes; aquí solo se restituyen.
        (
            {"duracion_meses": "0"},
            "La cláusula no es válida: la duración del contrato debe ser positiva",
        ),
        (
            {"fecha_base_indices": "2026-01-15"},
            "La cláusula no es válida: el mes base de los índices se declara con su primer día "
            "(S1-R10)",
        ),
        (
            {
                "mecanismo": "escalatoria",
                "mecanismo_pagadero": "comprobacion",
                "fuente_pagadero": "x",
            },
            "La cláusula no es válida: mecanismo_pagadero solo con 'ambos', uno de los dos y con "
            "su fuente",
        ),
    ],
)
def test_las_reglas_de_la_clausula_del_nucleo_salen_con_tildes(cambio, dice):
    with pytest.raises(HojaInvalida) as error:
        reajuste.clausula_desde_textos({**CAMPOS, **cambio}, COMPONENTES)
    assert str(error.value) == dice


def test_los_rotulos_de_los_campos_llevan_tildes_y_no_nombran_la_spec():
    assert {
        campo: reajuste.ROTULOS[campo]
        for campo in (
            "duracion_meses",
            "fecha_base_indices",
            "r",
            "fuente",
            "desde",
            "hasta",
            "version_comprobacion",
            "periodo",
        )
    } == {
        "duracion_meses": "Duración (meses)",
        "fecha_base_indices": "Mes base de los índices",
        "r": "R (fracción no reajustable)",
        "fuente": "Fuente de la cláusula",
        "desde": "Período, desde",
        "hasta": "Período, hasta",
        "version_comprobacion": "Versión de comprobación",
        "periodo": "Número del período (ejecutado)",
    }
