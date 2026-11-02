"""MP-1, Tarea 3: Componer guarda en la lista de hoy y avisa las variantes antes de guardar.

Diseño de montar un presupuesto §5.1 y §10 (D-MP1, D-MP2) y hallazgo O-13: un precio tecleado hoy
va a la lista para armar **de hoy** (derivada de la vigente si hace falta), nunca a una lista vieja;
un precio distinto para un insumo que ya existe crea una variante solo para ese APU, y
`prever_guardado` lo dice antes de guardar sin dejar nada escrito (ni la variante ni la lista
nueva), también si el guardado falla a mitad.

Base en memoria con `crear_esquema` + `crear_esquema_carpeta`; datos ficticios de
`tests/fixtures/lista_de_julio.py` («Cemento gris» a 18,00 Bs el saco en «MaPreX julio 2026 en Bs»
del 01/07/2026). Los oráculos están escritos a mano: el nombre de la lista de hoy sigue la
regla de la Tarea 1 («{raíz} al dd/mm/aaaa»), los códigos siguen la regla del núcleo (el insumo
nuevo de material es MAT-003, la primera variante de MAT-001 es MAT-001-B) y los mensajes son los
del plan.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from aplicacion.composicion import (
    MENSAJE_CONDICIONES_OBLIGATORIAS,
    AvisoVariante,
    ComposicionInvalida,
    guardar_desde_tablas,
    prever_guardado,
)
from aplicacion.listas_para_armar import SinListaParaArmar
from aplicacion.tablas_carpeta import crear_esquema_carpeta
from core import models
from core.catalog import CatalogoIncompleto, abrir_sesion, crear_esquema, crear_motor
from core.contracts.dominio import Dominio
from tests.fixtures.lista_de_julio import (
    CONDICIONES,
    DE_HOY,
    HOY,
    JULIO,
    MAPREX,
    OTRA_MONEDA,
    PRECIOS_DE_JULIO,
    SIN_LISTA,
    sembrar,
)
from tests.fixtures.lista_de_julio import codigos_de_insumos as _codigos
from tests.fixtures.lista_de_julio import cuentas as _cuentas
from tests.fixtures.lista_de_julio import nombres_de_listas as _nombres
from tests.fixtures.lista_de_julio import precios_de as _precios

MURO = "PRU-01-MUR"


def _motor_con_esquema():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    crear_esquema_carpeta(motor)
    return motor


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = _motor_con_esquema()
    try:
        with abrir_sesion(motor) as s:
            sembrar(s)
            yield s
    finally:
        motor.dispose()


@pytest.fixture
def sesion_usd() -> Iterator[Session]:
    """Foco 1 del plan: carpeta que trabaja en USD con la lista vigente en Bs."""
    motor = _motor_con_esquema()
    try:
        with abrir_sesion(motor) as s:
            sembrar(s, moneda_declarada="USD")
            yield s
    finally:
        motor.dispose()


def _fila(descripcion: str, unidad: str, cantidad: str, precio: str) -> dict[str, str]:
    return {"descripcion": descripcion, "unidad": unidad, "cantidad": cantidad, "precio": precio}


def _argumentos(materiales, codigo=MURO, descripcion="Muro ficticio de bloques"):
    return (codigo, descripcion, "m2", Dominio.CIVIL, "10", materiales, [], [])


def _guardar(s: Session, materiales, *, fecha: date = HOY, **cabecera):
    return guardar_desde_tablas(
        s, *_argumentos(materiales, **cabecera), fecha=fecha, condiciones=CONDICIONES
    )


def _prever(s: Session, materiales, *, fecha: date = HOY, condiciones: str = CONDICIONES, **cab):
    return prever_guardado(s, *_argumentos(materiales, **cab), fecha=fecha, condiciones=condiciones)


# --- guardar: el precio nuevo va a la lista de hoy (O-13) ---------------------------------------


def test_el_precio_nuevo_queda_en_la_lista_de_hoy_y_no_en_la_de_julio(sesion: Session) -> None:
    resultado = _guardar(sesion, [_fila("Bloque de arcilla ficticio", "pieza", "12,5", "18,00")])

    assert resultado.motivo is None
    assert _nombres(sesion) == [MAPREX, DE_HOY]
    assert _precios(sesion, MAPREX) == PRECIOS_DE_JULIO  # la de julio no cambia
    assert _precios(sesion, DE_HOY) == {**PRECIOS_DE_JULIO, "MAT-003": Decimal("18.00")}


def test_otro_guardado_el_mismo_dia_usa_la_misma_lista_de_hoy(sesion: Session) -> None:
    _guardar(sesion, [_fila("Bloque de arcilla ficticio", "pieza", "12,5", "18,00")])
    _guardar(
        sesion,
        [_fila("Cabilla ficticia", "kg", "2", "35,50")],
        codigo="PRU-02-COL",
        descripcion="Columna ficticia",
    )

    assert _nombres(sesion) == [MAPREX, DE_HOY]
    assert _precios(sesion, DE_HOY) == {
        **PRECIOS_DE_JULIO,
        "MAT-003": Decimal("18.00"),
        "MAT-004": Decimal("35.50"),
    }


def test_sin_lista_para_armar_no_guarda_nada(sesion: Session) -> None:
    antes = _cuentas(sesion)
    with pytest.raises(SinListaParaArmar) as error:
        _guardar(sesion, [_fila("Cemento gris", "saco", "0,25", "18,00")], fecha=date(2026, 6, 30))
    assert str(error.value) == SIN_LISTA
    assert _cuentas(sesion) == antes


def test_foco_1_carpeta_en_usd_con_la_vigente_en_bs_no_guarda_y_lo_dice(
    sesion_usd: Session,
) -> None:
    antes = _cuentas(sesion_usd)
    with pytest.raises(SinListaParaArmar) as error:
        _guardar(sesion_usd, [_fila("Cemento gris", "saco", "0,25", "18,00")])
    assert str(error.value) == OTRA_MONEDA
    assert _cuentas(sesion_usd) == antes


# --- prever: la variante se avisa y nada queda escrito ------------------------------------------


def test_prever_avisa_la_variante_con_los_dos_precios_y_no_deja_nada(sesion: Session) -> None:
    antes = _cuentas(sesion)

    prevision = _prever(sesion, [_fila("Cemento gris", "saco", "0,25", "20,00")])

    assert prevision.variantes == [
        AvisoVariante("Cemento gris", "saco", Decimal("18"), Decimal("20"), "MAT-001-B")
    ]
    assert prevision.lista_nueva is True
    assert (prevision.lista.nombre, prevision.lista.moneda, prevision.lista.fecha) == (
        DE_HOY,
        "Bs",
        HOY,
    )
    assert prevision.lista.origen == "derivada de «MaPreX julio 2026 en Bs»"
    # se deshizo: ni la variante, ni la lista de hoy, ni la partida
    assert _cuentas(sesion) == antes
    assert "MAT-001-B" not in _codigos(sesion)
    assert _nombres(sesion) == [MAPREX]
    assert not sesion.new and not sesion.dirty


def test_lo_previsto_es_lo_que_el_guardado_hace(sesion: Session) -> None:
    filas = [_fila("Cemento gris", "saco", "0,25", "20,00")]
    _prever(sesion, filas)

    _guardar(sesion, filas)

    precios = _precios(sesion, DE_HOY)
    assert precios["MAT-001-B"] == Decimal("20.00")
    assert precios["MAT-001"] == Decimal("18.00")


def test_prever_sin_variantes_en_la_lista_de_hoy_que_ya_existe(sesion: Session) -> None:
    prevision = _prever(sesion, [_fila("Cemento gris", "saco", "0,25", "18,00")], fecha=JULIO)

    assert prevision.variantes == []
    assert prevision.lista_nueva is False
    assert (prevision.lista.nombre, prevision.lista.fecha) == (MAPREX, JULIO)


def test_prever_deshace_tambien_si_el_guardado_falla_a_mitad(sesion: Session) -> None:
    """Las 25 letras de variante de MAT-001 ya están ocupadas: el núcleo falla al crear la variante,
    después de crear la lista de hoy y la partida. Nada de eso queda."""
    for letra in "BCDEFGHIJKLMNOPQRSTUVWXYZ":
        sesion.add(
            models.Insumo(
                codigo=f"MAT-001-{letra}",
                tipo="material",
                descripcion=f"Relleno ficticio {letra}",
                unidad="kg",
            )
        )
    sesion.flush()
    antes = _cuentas(sesion)

    with pytest.raises(
        CatalogoIncompleto, match="se agotaron los sufijos de variante para MAT-001"
    ):
        _prever(sesion, [_fila("Cemento gris", "saco", "0,25", "20,00")])

    assert _cuentas(sesion) == antes
    assert _nombres(sesion) == [MAPREX]
    assert not sesion.new and not sesion.dirty


def test_prever_sin_condiciones_es_el_mismo_error_que_guardar(sesion: Session) -> None:
    with pytest.raises(ComposicionInvalida) as error:
        _prever(sesion, [_fila("Cemento gris", "saco", "0,25", "20,00")], condiciones="  ")
    assert str(error.value) == MENSAJE_CONDICIONES_OBLIGATORIAS


def test_prever_con_otra_cabecera_sobre_una_existente_da_el_motivo(sesion: Session) -> None:
    _guardar(sesion, [_fila("Cemento gris", "saco", "0,25", "18,00")])
    antes = _cuentas(sesion)

    with pytest.raises(ComposicionInvalida) as error:
        _prever(sesion, [_fila("Cemento gris", "saco", "0,25", "20,00")], descripcion="Otra")

    assert str(error.value).startswith(f"la partida {MURO} ya existe con la descripcion")
    assert _cuentas(sesion) == antes


def test_foco_1_prever_en_carpeta_usd_con_la_vigente_en_bs(sesion_usd: Session) -> None:
    antes = _cuentas(sesion_usd)
    with pytest.raises(SinListaParaArmar) as error:
        _prever(sesion_usd, [_fila("Cemento gris", "saco", "0,25", "20,00")])
    assert str(error.value) == OTRA_MONEDA
    assert _cuentas(sesion_usd) == antes
