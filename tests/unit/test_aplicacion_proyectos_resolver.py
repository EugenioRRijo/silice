"""`aplicacion.proyectos.resolver_proyecto` (V-11): del `codigo` de `GET /v1/proyectos` o del
nombre exacto al proyecto. Oraculos escritos a mano; datos ficticios."""

from __future__ import annotations

from pathlib import Path

from aplicacion.proyectos import resolver_proyecto
from core import models
from core.budget import crear_proyecto
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base


def _caso(ruta: Path, nombres: list[str]):
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    sesion = abrir_sesion(motor)
    for nombre in nombres:
        crear_proyecto(sesion, nombre)
    sesion.commit()
    return motor, sesion


def test_resuelve_por_codigo_por_nombre_y_devuelve_none_si_no_hay(tmp_path: Path) -> None:
    motor, sesion = _caso(tmp_path / "c.db", ["Torre Demo", "Galpon Demo"])
    try:
        torre = sesion.query(models.Proyecto).filter_by(nombre="Torre Demo").one()
        assert resolver_proyecto(sesion, str(torre.id)).nombre == "Torre Demo"
        assert resolver_proyecto(sesion, "Torre Demo").id == torre.id
        assert resolver_proyecto(sesion, " Torre Demo ") is None  # el nombre es exacto
        assert resolver_proyecto(sesion, "999999") is None
        assert resolver_proyecto(sesion, "Inexistente") is None
        assert resolver_proyecto(sesion, "") is None
    finally:
        sesion.close()
        motor.dispose()


def test_si_el_nombre_es_un_numero_el_codigo_gana(tmp_path: Path) -> None:
    motor, sesion = _caso(tmp_path / "c.db", ["Primero", "1"])
    try:
        primero = sesion.query(models.Proyecto).filter_by(nombre="Primero").one()
        numerico = sesion.query(models.Proyecto).filter_by(nombre="1").one()
        # «1» es el codigo (id) de «Primero»: gana el codigo, no el nombre «1».
        assert primero.id == 1 and numerico.id == 2
        assert resolver_proyecto(sesion, "1").nombre == "Primero"
        # el proyecto cuyo nombre es un numero sin id igual sigue alcanzable por su codigo.
        assert resolver_proyecto(sesion, str(numerico.id)).nombre == "1"
    finally:
        sesion.close()
        motor.dispose()
