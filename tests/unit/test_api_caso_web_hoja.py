"""`api.caso_web` descarta, hereda y olvida los borradores de la hoja (T10, 3b-1; diseno §3.1).

Cambiar de caso (`fijar`), cerrar sesion o vencer la ficha (`olvidar`), cambiar de contrasena
(`heredar`) y la limpieza de las pruebas (`olvidar_todo`) tocan tambien los borradores vivos de
esa ficha: un borrador jamas sobrevive a un cambio de caso.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from api import caso_web
from aplicacion import hoja_borradores
from aplicacion.hoja import Borrador


@pytest.fixture(autouse=True)
def _limpio():
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()


def _vivo(huella: str):
    return hoja_borradores.crear(
        huella, "caso-a", "P", "001", Borrador(fecha=date(2026, 10, 19)), None
    )


def test_fijar_un_caso_descarta_los_borradores_de_esa_ficha_y_solo_ellos():
    mio, ajeno = _vivo("ficha-a"), _vivo("ficha-b")
    caso_web.fijar("ficha-a", Path("otro.db"))
    assert hoja_borradores.listar("ficha-a") == []
    assert hoja_borradores.listar("ficha-b") == [ajeno]
    assert mio.id != ajeno.id


def test_olvidar_la_ficha_descarta_sus_borradores():
    _vivo("ficha-a")
    caso_web.olvidar("ficha-a")
    assert hoja_borradores.listar("ficha-a") == []


def test_heredar_pasa_los_borradores_a_la_ficha_nueva():
    vivo = _vivo("ficha-a")
    caso_web.heredar("ficha-a", "ficha-b")
    assert hoja_borradores.obtener("ficha-b", vivo.id) is vivo
    assert hoja_borradores.listar("ficha-a") == []


def test_olvidar_todo_vacia_tambien_los_borradores():
    _vivo("ficha-a")
    caso_web.olvidar_todo()
    assert hoja_borradores.listar("ficha-a") == []
