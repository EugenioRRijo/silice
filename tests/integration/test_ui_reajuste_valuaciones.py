"""UC-18 enmendado por S2 (RF-72): la pantalla de reajuste toma lo ejecutado de las valuaciones.

`ui.reajuste.periodos_desde_valuaciones` calcula en memoria y `guardar_con_valuaciones` guarda el
estudio citando cada valuación. El monto reconocido de noviembre es 75,90 (memoria OB-S2).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from aplicacion import reajuste
from core import models
from core.budget.puente import valuaciones_citadas
from core.budget.reajuste import cargar_estudio
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz
from ui.hoja import HojaInvalida

D = Decimal
FILAS = [
    {"desde": "2026-11-01", "hasta": "2026-11-30", "version_comprobacion": rz.REVALORADA,
     "excepcion": ""},
    {"desde": "", "hasta": "", "version_comprobacion": "", "excepcion": ""},
]  # fmt: skip


@pytest.fixture
def con_valuaciones(obra):
    rz.sembrar_revaloracion(obra)
    ob.registrar_v01_y_v02(obra)
    return obra


def test_los_periodos_salen_de_las_valuaciones_sin_escribir_nada(con_valuaciones):
    antes = con_valuaciones.scalar(select(func.count()).select_from(models.CitaValuacion))
    periodos = reajuste.periodos_desde_valuaciones(con_valuaciones, ob.NOMBRE, FILAS)
    assert len(periodos) == 1
    ejecutado = periodos[0].ejecutado
    assert {e.codigo: e.cantidad for e in ejecutado} == {"OB-A": D(90), "OB-B": D(60)}
    assert [e.fuente for e in ejecutado] == ["valuaciones V-01, V-02", "valuaciones V-02"]
    despues = con_valuaciones.scalar(select(func.count()).select_from(models.CitaValuacion))
    assert antes == despues == 0


def test_el_calculo_en_memoria_da_el_reconocido_de_la_memoria(con_valuaciones):
    periodos = reajuste.periodos_desde_valuaciones(con_valuaciones, ob.NOMBRE, FILAS)
    resultado = reajuste.calcular(
        con_valuaciones, ob.NOMBRE, ob.CODIGO, rz.CLAUSULA, periodos,
        fecha_calculo=date(2026, 11, 13),
    )  # fmt: skip
    assert resultado.periodos[0].reconocido == rz.RECONOCIDO_DE_NOVIEMBRE


def test_guardar_con_valuaciones_cita_cada_una_y_confirma(con_valuaciones):
    id_estudio = reajuste.guardar_con_valuaciones(
        con_valuaciones, ob.NOMBRE, ob.CODIGO, rz.CLAUSULA, FILAS,
        fecha_calculo=date(2026, 11, 13), fuente="estudio ficticio", responsable="Ing.",
    )  # fmt: skip
    periodo = cargar_estudio(con_valuaciones, id_estudio).resultado.periodos[0]
    assert periodo.reconocido == D("75.90")
    assert valuaciones_citadas(con_valuaciones, id_estudio) == {0: ["V-01", "V-02"]}


def test_guardar_sin_fuente_se_rechaza_y_no_deja_estudio(con_valuaciones):
    with pytest.raises(HojaInvalida, match="No se guardó el estudio"):
        reajuste.guardar_con_valuaciones(
            con_valuaciones, ob.NOMBRE, ob.CODIGO, rz.CLAUSULA, FILAS,
            fecha_calculo=date(2026, 11, 13), fuente="", responsable="Ing.",
        )  # fmt: skip
    assert con_valuaciones.scalar(select(func.count()).select_from(models.EstudioReajuste)) == 0
