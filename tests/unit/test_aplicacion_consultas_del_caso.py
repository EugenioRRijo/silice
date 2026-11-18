"""Las consultas del caso que salieron de `api/rutas` (tarea 3.1 del plan de desenredo).

`aplicacion.elaboracion` lista los presupuestos guardados, busca uno por codigo y lista las
ejecuciones; `aplicacion.listas_para_armar` lista las listas de precios y busca una por nombre.
Cada prueba arma a mano una base en memoria con filas fuera de orden. Obras ficticias.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from aplicacion import elaboracion, listas_para_armar
from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    with abrir_sesion(motor) as abierta:
        yield abierta
    motor.dispose()


def _lista(sesion: Session, nombre: str, vigencia: date) -> models.ListaPrecios:
    lista = models.ListaPrecios(nombre=nombre, moneda="Bs", fecha_vigencia=vigencia)
    sesion.add(lista)
    sesion.flush()
    return lista


def _presupuesto(
    sesion: Session, obra: models.Proyecto, codigo: str, lista: models.ListaPrecios
) -> models.Presupuesto:
    presupuesto = models.Presupuesto(
        codigo=codigo,
        proyecto=obra,
        fecha=date(2026, 3, 1),
        moneda="Bs",
        lista_precios=lista,
        fcas=Decimal("1.5"),
        bono_alimentacion=Decimal("0"),
        administracion=Decimal("0.1"),
        utilidad=Decimal("0.1"),
    )
    sesion.add(presupuesto)
    sesion.flush()
    return presupuesto


def _obra(sesion: Session, nombre: str) -> models.Proyecto:
    obra = models.Proyecto(nombre=nombre)
    sesion.add(obra)
    sesion.flush()
    return obra


def test_presupuestos_guardados_salen_por_codigo(sesion: Session) -> None:
    lista = _lista(sesion, "Lista marzo", date(2026, 3, 1))
    obra = _obra(sesion, "Galpon Ficticio")
    for codigo in ("P-03", "P-01", "P-02"):
        _presupuesto(sesion, obra, codigo, lista)
    assert [p.codigo for p in elaboracion.presupuestos_guardados(sesion)] == [
        "P-01",
        "P-02",
        "P-03",
    ]


def test_presupuesto_por_codigo_acota_por_obra_y_declara_lo_que_falta(sesion: Session) -> None:
    lista = _lista(sesion, "Lista marzo", date(2026, 3, 1))
    norte, sur = _obra(sesion, "Obra Norte"), _obra(sesion, "Obra Sur")
    _presupuesto(sesion, norte, "P-01", lista)
    del_sur = _presupuesto(sesion, sur, "P-01", lista)
    solo_norte = _presupuesto(sesion, norte, "P-02", lista)

    assert elaboracion.presupuesto_por_codigo(sesion, "P-02", None) is solo_norte
    assert elaboracion.presupuesto_por_codigo(sesion, "P-01", "Obra Sur") is del_sur
    with pytest.raises(LookupError, match="'P-09'"):
        elaboracion.presupuesto_por_codigo(sesion, "P-09", None)
    with pytest.raises(LookupError, match="'P-02' en la obra 'Obra Sur'"):
        elaboracion.presupuesto_por_codigo(sesion, "P-02", "Obra Sur")
    with pytest.raises(elaboracion.PresupuestoAmbiguo) as ambiguo:
        elaboracion.presupuesto_por_codigo(sesion, "P-01", None)
    assert ambiguo.value.obras == ("Obra Norte", "Obra Sur")
    assert not isinstance(ambiguo.value, LookupError)  # el 409 no se vuelve un 404


def test_ejecuciones_salen_por_fecha_de_inicio_y_luego_por_id(sesion: Session) -> None:
    for referencia, inicio in (
        ("EJ-C", date(2026, 5, 1)),
        ("EJ-A", date(2026, 1, 1)),
        ("EJ-B", date(2026, 5, 1)),
    ):
        sesion.add(models.Ejecucion(referencia=referencia, fecha_inicio=inicio))
        sesion.flush()
    assert [e.referencia for e in elaboracion.ejecuciones(sesion)] == ["EJ-A", "EJ-C", "EJ-B"]


def test_listas_de_precios_salen_por_vigencia_y_luego_por_id(sesion: Session) -> None:
    _lista(sesion, "Junio", date(2026, 6, 1))
    _lista(sesion, "Enero", date(2026, 1, 1))
    _lista(sesion, "Junio bis", date(2026, 6, 1))
    assert [lista.nombre for lista in listas_para_armar.listas_de_precios(sesion)] == [
        "Enero",
        "Junio",
        "Junio bis",
    ]


def test_lista_por_nombre_es_exacta(sesion: Session) -> None:
    junio = _lista(sesion, "Junio", date(2026, 6, 1))
    _lista(sesion, "Enero", date(2026, 1, 1))
    assert listas_para_armar.lista_por_nombre(sesion, "Junio") is junio
    assert listas_para_armar.lista_por_nombre(sesion, "junio") is None
    assert listas_para_armar.lista_por_nombre(sesion, "Marzo") is None


def test_lista_por_id_devuelve_la_lista_o_nada(sesion: Session) -> None:
    """Tarea 3.4: `api/rutas/revision.py` pedia la lista con `caso.get(models.ListaPrecios, id)`."""
    _lista(sesion, "Enero", date(2026, 1, 1))
    junio = _lista(sesion, "Junio", date(2026, 6, 1))
    assert listas_para_armar.lista_por_id(sesion, junio.id) is junio
    assert listas_para_armar.lista_por_id(sesion, 999) is None
