"""UC-06, nucleo (Sesion I6.2): registro, dispersion y propuesta de rendimientos.

RF-25: el registro persiste partida, valor, condiciones, fecha y referencia a la ejecucion, y un
rendimiento MEDIDO sin referencia se rechaza (la invariante vive en el contrato
`core.contracts.apu.Rendimiento`; aqui se comprueba que la frontera del catalogo la aplica y que
la referencia apunta a una `Ejecucion` real, trazabilidad total de CLAUDE.md §2).

RF-26: la dispersion trae numero de observaciones, media, minimo y maximo (todo `Decimal`, sin
redondeos: los dos decimales son de presentacion), y cuantas observaciones son medidas y cuantas
estimadas -- estimado y medido nunca se mezclan sin declararse (metas M1, M2 y M4 de
`scripts/meta_i6.py`).

La siembra de la linea base deja un rendimiento ESTIMADO por partida (80 m3/dia en la
excavacion): las pruebas registran valores alrededor de ese.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from core import models
from core.catalog import (
    Catalogo,
    dispersion_rendimientos,
    proponer_rendimiento,
    registrar_ejecucion,
    registrar_rendimiento,
)
from core.contracts.apu import Rendimiento, TipoRendimiento
from tests.fixtures import apu_linea_base as linea_base

EXCAVACION = linea_base.APU_EXCAVACION.codigo_partida  # sembrada con su rendimiento estimado
SEMBRADO = linea_base.APU_EXCAVACION.rendimiento
FECHA = date(2026, 7, 1)


@pytest.fixture
def ejecucion(sesion):
    """Una obra ejecutada registrada, de la que pueden medirse rendimientos."""
    return registrar_ejecucion(
        sesion,
        referencia="OBRA-2026-01",
        fecha_inicio=date(2026, 6, 15),
        descripcion="Drenaje de la clinica, zanja norte",
    )


def test_registrar_estimado_queda_en_el_historico_de_la_partida(sesion):
    registrado = registrar_rendimiento(
        sesion,
        EXCAVACION,
        valor=Decimal("75"),
        tipo=TipoRendimiento.ESTIMADO,
        fecha=FECHA,
        condiciones="terreno humedo",
    )

    assert registrado.tipo is TipoRendimiento.ESTIMADO
    assert registrado.referencia_ejecucion is None
    historico = Catalogo(sesion).rendimientos(EXCAVACION)
    assert len(historico) == 2  # el sembrado mas este
    assert historico[-1].valor == Decimal("75")
    assert historico[-1].condiciones == "terreno humedo"


def test_registrar_medido_sin_referencia_se_rechaza(sesion):
    """RF-25: la invariante del contrato llega hasta la frontera del catalogo."""
    with pytest.raises(ValueError, match="MEDIDO"):
        registrar_rendimiento(
            sesion, EXCAVACION, valor=Decimal("70"), tipo=TipoRendimiento.MEDIDO, fecha=FECHA
        )


def test_registrar_medido_traza_la_ejecucion(sesion, ejecucion):
    registrado = registrar_rendimiento(
        sesion,
        EXCAVACION,
        valor=Decimal("72"),
        tipo=TipoRendimiento.MEDIDO,
        fecha=FECHA,
        referencia_ejecucion="OBRA-2026-01",
    )

    assert registrado.tipo is TipoRendimiento.MEDIDO
    assert registrado.referencia_ejecucion == "OBRA-2026-01"
    # El renglon persistido enlaza la ejecucion por clave foranea, no por texto suelto.
    modelo = sesion.scalars(
        select(models.Rendimiento).where(models.Rendimiento.tipo == "medido")
    ).one()
    assert modelo.ejecucion_id == ejecucion.id


def test_referencia_de_ejecucion_inexistente_se_rechaza(sesion):
    with pytest.raises(LookupError, match="OBRA-FANTASMA"):
        registrar_rendimiento(
            sesion,
            EXCAVACION,
            valor=Decimal("70"),
            tipo=TipoRendimiento.MEDIDO,
            fecha=FECHA,
            referencia_ejecucion="OBRA-FANTASMA",
        )


def test_valor_no_positivo_se_rechaza(sesion):
    with pytest.raises(ValueError, match="mayor que cero"):
        registrar_rendimiento(
            sesion, EXCAVACION, valor=Decimal("0"), tipo=TipoRendimiento.ESTIMADO, fecha=FECHA
        )


def test_partida_inexistente_se_rechaza(sesion):
    with pytest.raises(LookupError):
        registrar_rendimiento(
            sesion, "NO-EXISTE", valor=Decimal("10"), tipo=TipoRendimiento.ESTIMADO, fecha=FECHA
        )


def test_el_registro_del_modulo_delega_en_el_del_catalogo(sesion, monkeypatch):
    """INV‑005: una sola implementación del registro, la de `Catalogo`."""
    llamadas = []
    original = Catalogo.registrar_rendimiento

    def espia(self, rendimiento):
        llamadas.append(rendimiento)
        return original(self, rendimiento)

    monkeypatch.setattr(Catalogo, "registrar_rendimiento", espia)
    registrado = registrar_rendimiento(
        sesion, EXCAVACION, valor=Decimal("75"), tipo=TipoRendimiento.ESTIMADO, fecha=FECHA
    )

    assert llamadas == [registrado]


def test_una_ejecucion_inexistente_se_rechaza_igual_por_las_dos_puertas(sesion):
    contrato = Rendimiento(
        codigo_partida=EXCAVACION,
        valor=Decimal("70"),
        tipo=TipoRendimiento.MEDIDO,
        fecha=FECHA,
        referencia_ejecucion="OBRA-FANTASMA",
    )
    with pytest.raises(LookupError, match="registre la obra") as desde_catalogo:
        Catalogo(sesion).registrar_rendimiento(contrato)
    with pytest.raises(LookupError, match="registre la obra") as desde_modulo:
        registrar_rendimiento(
            sesion,
            EXCAVACION,
            valor=Decimal("70"),
            tipo=TipoRendimiento.MEDIDO,
            fecha=FECHA,
            referencia_ejecucion="OBRA-FANTASMA",
        )
    assert type(desde_catalogo.value) is LookupError
    assert type(desde_modulo.value) is LookupError


def test_dispersion_exacta_y_con_tipos_contados(sesion, ejecucion):
    """RF-26: n, media, minimo y maximo en `Decimal` exacto, y el desglose estimado/medido."""
    registrar_rendimiento(
        sesion, EXCAVACION, valor=Decimal("75"), tipo=TipoRendimiento.ESTIMADO, fecha=FECHA
    )
    registrar_rendimiento(
        sesion,
        EXCAVACION,
        valor=Decimal("82"),
        tipo=TipoRendimiento.MEDIDO,
        fecha=date(2026, 7, 2),
        referencia_ejecucion="OBRA-2026-01",
    )
    registrar_rendimiento(
        sesion,
        EXCAVACION,
        valor=Decimal("90"),
        tipo=TipoRendimiento.ESTIMADO,
        fecha=date(2026, 7, 3),
    )

    dispersion = dispersion_rendimientos(sesion, EXCAVACION)

    assert dispersion is not None
    assert dispersion.observaciones == 4  # el 80 sembrado + los tres registrados
    assert dispersion.media == (SEMBRADO + Decimal("75") + Decimal("82") + Decimal("90")) / 4
    assert dispersion.minimo == Decimal("75")
    assert dispersion.maximo == Decimal("90")
    assert dispersion.medidos == 1 and dispersion.estimados == 3


def test_dispersion_de_partida_sin_rendimientos_es_none(sesion):
    sesion.add(
        models.Partida(
            codigo="X-SIN-REN", descripcion="sin historial", unidad="m3", dominio="civil"
        )
    )
    sesion.flush()
    assert dispersion_rendimientos(sesion, "X-SIN-REN") is None


def test_propuesta_prefiere_el_medido_mas_reciente(sesion, ejecucion):
    """RF-26 + UC-06: lo observado en obra pesa mas que lo declarado; el tipo viaja declarado."""
    registrar_rendimiento(
        sesion,
        EXCAVACION,
        valor=Decimal("72"),
        tipo=TipoRendimiento.MEDIDO,
        fecha=FECHA,
        referencia_ejecucion="OBRA-2026-01",
    )
    registrar_rendimiento(
        sesion,
        EXCAVACION,
        valor=Decimal("95"),
        tipo=TipoRendimiento.ESTIMADO,
        fecha=date(2026, 7, 9),
    )

    propuesta = proponer_rendimiento(sesion, EXCAVACION)

    assert propuesta is not None
    assert propuesta.rendimiento.tipo is TipoRendimiento.MEDIDO
    assert propuesta.rendimiento.valor == Decimal("72")
    assert propuesta.dispersion.observaciones == 3


def test_propuesta_sin_medidos_cae_al_estimado_mas_reciente(sesion):
    propuesta = proponer_rendimiento(sesion, EXCAVACION)

    assert propuesta is not None
    assert propuesta.rendimiento.tipo is TipoRendimiento.ESTIMADO
    assert propuesta.rendimiento.valor == SEMBRADO


def test_registrar_no_confirma_la_transaccion(sesion):
    """Mismo criterio que `crear_lista_desde_archivo`: la confirmacion es de la capa que
    representa la decision del usuario (la API o la UI), no del catalogo.
    """
    registrar_rendimiento(
        sesion, EXCAVACION, valor=Decimal("75"), tipo=TipoRendimiento.ESTIMADO, fecha=FECHA
    )
    sesion.rollback()
    assert len(Catalogo(sesion).rendimientos(EXCAVACION)) == 1  # solo el sembrado


def test_advertencia_cuando_el_valor_se_aparta_del_rango_observado(sesion, ejecucion):
    """RF-27: fuera del rango observado hay advertencia con el rango citado; dentro, ninguna."""
    from core.catalog import advertencia_rendimiento

    registrar_rendimiento(
        sesion, EXCAVACION, valor=Decimal("75"), tipo=TipoRendimiento.ESTIMADO, fecha=FECHA
    )
    dispersion = dispersion_rendimientos(sesion, EXCAVACION)  # rango [75, 80], 2 observaciones

    advertencia = advertencia_rendimiento(dispersion, Decimal("300"))
    assert advertencia is not None
    assert "75" in advertencia and "80" in advertencia  # cita el rango observado
    assert advertencia_rendimiento(dispersion, Decimal("78")) is None


def test_una_sola_observacion_no_es_comportamiento_del_cual_apartarse(sesion):
    """Con menos de MINIMO_OBSERVADO_PARA_ADVERTIR observaciones no se advierte: un punto no
    define comportamiento observado (mismo criterio de abstencion que ml.anomaly).
    """
    from core.catalog import advertencia_rendimiento

    dispersion = dispersion_rendimientos(sesion, EXCAVACION)  # solo el 80 sembrado
    assert dispersion.observaciones == 1
    assert advertencia_rendimiento(dispersion, Decimal("300")) is None
    assert advertencia_rendimiento(None, Decimal("300")) is None
