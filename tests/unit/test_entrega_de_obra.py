"""Lote G5: la fecha de entrega al cliente de una obra (`aplicacion.entrega_de_obra`).

Oráculos escritos a mano con datos ficticios («Torre Norte», Ana, Rosa):
- una obra recién creada no tiene fecha de entrega (`fecha_entrega=None`);
- fijar una fecha de hoy o futura la guarda con su responsable y momento, y se lee por código o por
  nombre de la obra;
- fijar otra fecha o limpiarla (`None`) actualiza la fila existente con quién y cuándo lo hizo;
- fijar una fecha en el pasado (`< ahora.date()`) lanza `FechaDeEntregaEnElPasado` sin guardar;
- una obra inexistente lanza `ObraNoExiste`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from aplicacion.entrega_de_obra import (
    EntregaDeLaObra,
    FechaDeEntregaEnElPasado,
    ObraNoExiste,
    cambiar_entrega,
    detalle_del_cambio,
    entregas_de_la_carpeta,
    fijar_entrega,
    leer_entrega,
)
from aplicacion.proyectos import crear_proyecto_en_sesion
from aplicacion.tablas_entrega import crear_esquema_entrega, hay_tabla_entrega
from core.catalog import abrir_sesion, crear_esquema, crear_motor

ANA = "Ana <ana>"
ROSA = "Rosa <rosa>"
AHORA = datetime(2026, 11, 27, 9, 30)
HOY = date(2026, 11, 27)


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator[Session]:
    """Base de caso en disco con el esquema del núcleo y una obra ficticia («Torre Norte», id 1)."""
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    abierta = abrir_sesion(motor)
    try:
        crear_proyecto_en_sesion(abierta, "Torre Norte", "Bs", "civil", "", ANA)
        yield abierta
    finally:
        abierta.close()
        motor.dispose()


def test_leer_sin_tabla_ni_fila_devuelve_sin_fecha_y_no_crea_la_tabla(sesion: Session) -> None:
    assert not hay_tabla_entrega(sesion)
    assert leer_entrega(sesion, "1") == EntregaDeLaObra(
        proyecto_codigo="1",
        fecha_entrega=None,
        actualizada=None,
        actualizada_por=None,
    )
    assert leer_entrega(sesion, "Torre Norte").fecha_entrega is None
    assert entregas_de_la_carpeta(sesion) == {}
    assert not hay_tabla_entrega(sesion)


def test_fijar_y_leer_fecha_futura_y_del_mismo_dia(sesion: Session) -> None:
    entrega = fijar_entrega(
        sesion,
        "Torre Norte",
        date(2026, 12, 15),
        responsable=ANA,
        ahora=AHORA,
    )
    sesion.commit()
    esperada = EntregaDeLaObra(
        proyecto_codigo="1",
        fecha_entrega=date(2026, 12, 15),
        actualizada=AHORA,
        actualizada_por=ANA,
    )
    assert entrega == esperada
    assert leer_entrega(sesion, "1") == esperada
    assert leer_entrega(sesion, "Torre Norte") == esperada
    # Con cuándo se fijó: un paquete exportado antes no cuenta como entrega (auditoría, #9).
    assert entregas_de_la_carpeta(sesion) == {1: esperada}

    # Fijar la fecha en el mismo día (hoy) no es pasado y se admite.
    later = datetime(2026, 11, 27, 14, 0)
    de_hoy = fijar_entrega(sesion, "1", HOY, responsable=ROSA, ahora=later)
    sesion.commit()
    assert de_hoy == EntregaDeLaObra(
        proyecto_codigo="1",
        fecha_entrega=HOY,
        actualizada=later,
        actualizada_por=ROSA,
    )
    assert leer_entrega(sesion, "1").fecha_entrega == HOY


def test_limpiar_la_fecha_deja_none_y_conserva_quien_la_actualizo(sesion: Session) -> None:
    crear_esquema_entrega(sesion.connection())
    # Limpiar cuando nunca tuvo fila deja todo en None.
    sin_fila = fijar_entrega(sesion, "1", None, responsable=ANA, ahora=AHORA)
    assert sin_fila == EntregaDeLaObra("1", None, None, None)

    fijar_entrega(sesion, "1", date(2026, 12, 20), responsable=ANA, ahora=AHORA)
    sesion.commit()
    despues = datetime(2026, 11, 28, 11, 0)
    limpia = fijar_entrega(sesion, "1", None, responsable=ROSA, ahora=despues)
    sesion.commit()
    assert limpia == EntregaDeLaObra(
        proyecto_codigo="1",
        fecha_entrega=None,
        actualizada=despues,
        actualizada_por=ROSA,
    )
    assert leer_entrega(sesion, "1") == limpia
    assert entregas_de_la_carpeta(sesion) == {}


def test_no_permite_fijar_una_fecha_en_el_pasado(sesion: Session) -> None:
    with pytest.raises(
        FechaDeEntregaEnElPasado,
        match="La fecha de entrega al cliente no puede estar en el pasado.",
    ):
        fijar_entrega(sesion, "1", date(2026, 11, 26), responsable=ANA, ahora=AHORA)
    assert leer_entrega(sesion, "1").fecha_entrega is None


def test_obra_inexistente_lanza_obra_no_existe(sesion: Session) -> None:
    with pytest.raises(ObraNoExiste, match="No hay ninguna obra «99»"):
        leer_entrega(sesion, "99")
    with pytest.raises(ObraNoExiste, match="No hay ninguna obra «Puente Fantasma»"):
        fijar_entrega(
            sesion,
            "Puente Fantasma",
            date(2026, 12, 10),
            responsable=ANA,
            ahora=AHORA,
        )


def test_responsable_vacio_o_demasiado_largo_se_rechaza(sesion: Session) -> None:
    with pytest.raises(ValueError, match="responsable"):
        fijar_entrega(sesion, "1", date(2026, 12, 10), responsable="   ", ahora=AHORA)
    with pytest.raises(ValueError, match="200"):
        fijar_entrega(sesion, "1", date(2026, 12, 10), responsable="a" * 201, ahora=AHORA)


def test_cambiar_entrega_dice_la_obra_y_la_fecha_que_tenia_para_el_rastro(sesion: Session) -> None:
    """T5, n.o 2: el detalle del evento «fecha de entrega» al fijar y al quitar."""
    primera = cambiar_entrega(sesion, "1", date(2026, 12, 10), responsable=ANA, ahora=AHORA)
    assert (primera.nombre, primera.anterior) == ("Torre Norte", None)
    assert detalle_del_cambio(primera, "silice.db") == (
        "obra 1 «Torre Norte» en la carpeta silice.db: antes sin fecha; ahora 2026-12-10"
    )
    quitada = cambiar_entrega(sesion, "Torre Norte", None, responsable=ROSA, ahora=AHORA)
    assert quitada.anterior == date(2026, 12, 10)
    assert detalle_del_cambio(quitada, None) == (
        "obra 1 «Torre Norte» en la carpeta de trabajo: antes 2026-12-10; ahora sin fecha"
    )
