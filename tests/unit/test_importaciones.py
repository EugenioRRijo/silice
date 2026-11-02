"""El registro de importaciones de la obra, sin la API (rediseño del front, F4, Tarea 10).

`aplicacion/importaciones.py` anota cada importación en el borrador vivo (`anotar`), la escribe con
la versión que la guarda (`registrar_al_guardar`, sin `commit`: viaja en la transacción de la
versión) y lista las guardadas de la obra más las que siguen en borradores vivos
(`importaciones_de_la_obra`). Aquí se prueba con la OF-001 de la memoria (versión 001) y borradores
de juguete (`SimpleNamespace`): lo que importa es el contrato, no el borrador entero.

Oráculos a mano: las fechas y horas fijas de abajo y el orden que sale de ellas (la más nueva
primero); las filas de la tabla se leen con `sqlite3` directo.
"""

from __future__ import annotations

import importlib
import shutil
import sqlite3
from contextlib import closing
from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.catalog import abrir_sesion, crear_motor
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001

TABLA = "hoja_importaciones"
A = datetime(2026, 10, 30, 10, 0)
B = datetime(2026, 10, 30, 11, 0)
C = datetime(2026, 10, 30, 12, 0)


def _modulo():
    try:
        return importlib.import_module("aplicacion.importaciones")
    except ModuleNotFoundError:
        pytest.fail("falta aplicacion/importaciones.py")


def _imp(archivo: str, cuando: datetime, tipo: str = "plano"):
    m = _modulo()
    return m.ImportacionDeObra(
        tipo=tipo,
        archivo=archivo,
        fecha_hora=cuando,
        usuario="ana",
        resumen=f"resumen de {archivo}",
        version=None,
        guardada=False,
    )


def _vivo(*importaciones, proyecto: str = NOMBRE_OF001, guardado_como: str | None = None):
    return SimpleNamespace(
        importaciones=tuple(importaciones), proyecto=proyecto, guardado_como=guardado_como
    )


@pytest.fixture
def base(tmp_path: Path) -> Path:
    ruta = tmp_path / "of001.db"
    shutil.copyfile(plantilla_of001(tmp_path / "plantilla.db"), ruta)
    return ruta


def _id_de_la_version(ruta: Path, codigo: str = "001") -> int:
    with closing(sqlite3.connect(ruta)) as bd:
        ((id_,),) = bd.execute("SELECT id FROM presupuesto WHERE codigo = ?", (codigo,)).fetchall()
    return id_


def _filas(ruta: Path) -> list[tuple]:
    with closing(sqlite3.connect(ruta)) as bd:
        if not bd.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (TABLA,)).fetchall():
            return []
        return bd.execute(
            f"SELECT version_id, tipo, archivo, usuario, resumen FROM {TABLA} ORDER BY id"
        ).fetchall()


def test_la_importacion_es_inmutable() -> None:
    imp = _imp("planta.dxf", A)
    with pytest.raises(FrozenInstanceError):
        imp.archivo = "otra.dxf"  # type: ignore[misc]
    assert (imp.version, imp.guardada) == (None, False)


def test_anotar_suma_a_las_del_borrador_y_devuelve_el_mismo() -> None:
    m = _modulo()
    vivo = _vivo(_imp("uno.dxf", A))
    devuelto = m.anotar(vivo, _imp("dos.csv", B, "computo"))
    assert devuelto is vivo
    assert [i.archivo for i in vivo.importaciones] == ["uno.dxf", "dos.csv"]
    assert isinstance(vivo.importaciones, tuple)


def test_anotar_no_cambia_lo_ya_anotado() -> None:
    m = _modulo()
    primero = _imp("uno.dxf", A)
    vivo = _vivo(primero)
    m.anotar(vivo, replace(primero, archivo="dos.dxf"))
    assert vivo.importaciones[0] is primero


def test_registrar_al_guardar_escribe_una_fila_por_importacion_con_la_version(base: Path) -> None:
    m = _modulo()
    vivo = _vivo(_imp("planta.dxf", A), _imp("computo.csv", B, "computo"))
    id_version = _id_de_la_version(base)
    sesion = abrir_sesion(crear_motor(base))
    try:
        m.registrar_al_guardar(sesion, vivo, id_version)
        sesion.commit()
    finally:
        sesion.close()
    assert _filas(base) == [
        (id_version, "plano", "planta.dxf", "ana", "resumen de planta.dxf"),
        (id_version, "computo", "computo.csv", "ana", "resumen de computo.csv"),
    ]


def test_registrar_al_guardar_no_confirma_por_su_cuenta(base: Path) -> None:
    m = _modulo()
    sesion = abrir_sesion(crear_motor(base))
    try:
        m.registrar_al_guardar(sesion, _vivo(_imp("planta.dxf", A)), _id_de_la_version(base))
        sesion.rollback()
    finally:
        sesion.close()
    assert _filas(base) == []


def test_sin_importaciones_no_toca_la_base(base: Path) -> None:
    m = _modulo()
    sesion = abrir_sesion(crear_motor(base))
    try:
        m.registrar_al_guardar(sesion, _vivo(), _id_de_la_version(base))
        sesion.commit()
    finally:
        sesion.close()
    with closing(sqlite3.connect(base)) as bd:
        assert not bd.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (TABLA,)).fetchall()


def test_lista_guardadas_y_sin_guardar_de_la_mas_nueva_a_la_mas_vieja(base: Path) -> None:
    m = _modulo()
    id_version = _id_de_la_version(base)
    sesion = abrir_sesion(crear_motor(base))
    try:
        m.registrar_al_guardar(
            sesion, _vivo(_imp("planta.dxf", A), _imp("computo.csv", C, "computo")), id_version
        )
        sesion.commit()
        lista = m.importaciones_de_la_obra(sesion, NOMBRE_OF001, [_vivo(_imp("nuevo.dxf", B))])
    finally:
        sesion.close()
    assert [(i.archivo, i.fecha_hora, i.version, i.guardada) for i in lista] == [
        ("computo.csv", C, "001", True),
        ("nuevo.dxf", B, None, False),
        ("planta.dxf", A, "001", True),
    ]


def test_los_borradores_de_otra_obra_o_ya_guardados_no_cuentan(base: Path) -> None:
    m = _modulo()
    sesion = abrir_sesion(crear_motor(base))
    try:
        lista = m.importaciones_de_la_obra(
            sesion,
            NOMBRE_OF001,
            [
                _vivo(_imp("ajeno.dxf", A), proyecto="Otra obra"),
                _vivo(_imp("cerrado.dxf", B), guardado_como="002"),
                _vivo(_imp("mio.dxf", C)),
            ],
        )
    finally:
        sesion.close()
    assert [i.archivo for i in lista] == ["mio.dxf"]


def test_una_base_sin_la_tabla_lista_solo_lo_sin_guardar(base: Path) -> None:
    m = _modulo()
    sesion = abrir_sesion(crear_motor(base))
    try:
        assert m.importaciones_de_la_obra(sesion, NOMBRE_OF001, []) == []
        lista = m.importaciones_de_la_obra(sesion, NOMBRE_OF001, [_vivo(_imp("a.dxf", A))])
    finally:
        sesion.close()
    assert [i.archivo for i in lista] == ["a.dxf"]
    assert _filas(base) == []  # leer no crea la tabla


def test_los_resumenes_se_escriben_en_singular_y_plural() -> None:
    m = _modulo()
    assert (
        m.resumen_de_plano(filas=34, sin_reconocer=2) == "34 filas en el espacio; 2 sin reconocer"
    )
    assert m.resumen_de_plano(filas=1, sin_reconocer=0) == "1 fila en el espacio"
    assert m.resumen_de_computo(18) == "18 partidas llevadas"
    assert m.resumen_de_computo(1) == "1 partida llevada"
