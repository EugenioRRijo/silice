# tests/integration/test_estudio_reajuste.py
from datetime import date
from decimal import Decimal as D  # noqa: N817

import pytest
from sqlalchemy import select

from core import models
from core.budget.reajuste import EstadoEstudio, cargar_estudio, guardar_estudio
from tests.fixtures.reajuste_s1 import CLAUSULA, NOMBRE, PERIODO, _importar, sembrar


def _version(sesion, codigo="001"):
    return sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == NOMBRE, models.Presupuesto.codigo == codigo)
    ).one()


def _guardar(sesion, fecha=date(2027, 3, 5), reemplaza_a=None):
    return guardar_estudio(
        sesion,
        _version(sesion),
        CLAUSULA,
        [PERIODO],
        fecha_calculo=fecha,
        fuente="estudio de prueba",
        responsable="Ing.",
        reemplaza_a=reemplaza_a,
    )


def test_recargado_es_identico_y_cita_lo_que_uso(sesion):
    sembrar(sesion)
    estudio = _guardar(sesion)
    cargado = cargar_estudio(sesion, estudio.id)
    p = cargado.resultado.periodos[0]
    assert (p.escalatoria, p.comprobacion, p.reconocido) == (D(15300), D(16000), D(15300))
    assert cargado.estado is EstadoEstudio.CERRADO and p.version_comprobacion == "002"


def test_rnf14_una_revision_posterior_no_cambia_el_estudio(sesion):
    sembrar(sesion)
    estudio = _guardar(sesion)
    _importar(sesion, "FIC-MAT", [(date(2027, 2, 1), "240")], "f" * 64)  # revisión del índice
    assert cargar_estudio(sesion, estudio.id).resultado.periodos[0].escalatoria - D(15300) == 0


def test_parcial_se_reemplaza_una_sola_vez_sin_borrarse(sesion):
    sembrar(sesion)
    parcial = _guardar(sesion, fecha=date(2027, 2, 27))
    assert parcial.estado == EstadoEstudio.PARCIAL.value
    cierre = _guardar(sesion, reemplaza_a=parcial.id)
    assert (
        sesion.get(models.EstudioReajuste, parcial.id) is not None
        and cierre.reemplaza_a == parcial.id
    )
    with pytest.raises(ValueError, match="una sola vez"):
        _guardar(sesion, reemplaza_a=parcial.id)


def test_sin_fuente_o_responsable_no_se_guarda(sesion):
    sembrar(sesion)
    with pytest.raises(ValueError):
        guardar_estudio(
            sesion,
            _version(sesion),
            CLAUSULA,
            [PERIODO],
            fecha_calculo=date(2027, 3, 5),
            fuente=" ",
            responsable="Ing.",
        )
