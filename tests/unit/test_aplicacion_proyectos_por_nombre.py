"""`aplicacion.proyectos.proyecto_por_nombre` (tarea 2.5 del plan de desenredo): la unica busqueda
de obra por nombre. Es exacta y nunca lee los digitos como el `id`, a diferencia de
`resolver_proyecto`. Obras ficticias."""

from __future__ import annotations

from pathlib import Path

from aplicacion.proyectos import proyecto_por_nombre, resolver_proyecto
from core.budget import crear_proyecto
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base


def test_proyecto_por_nombre_no_lee_digitos_como_codigo(tmp_path: Path) -> None:
    ruta = tmp_path / "c.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    sesion = abrir_sesion(motor)
    try:
        torre = crear_proyecto(sesion, "Torre B")
        uno = crear_proyecto(sesion, "1")
        sesion.commit()
        assert (torre.id, uno.id) == (1, 2)
        assert proyecto_por_nombre(sesion, "1").id == 2
        assert resolver_proyecto(sesion, "1").id == 1  # el codigo gana en resolver_proyecto
        assert proyecto_por_nombre(sesion, "Torre B").id == 1
        assert proyecto_por_nombre(sesion, "torre b") is None  # exacto
        assert proyecto_por_nombre(sesion, " Torre B") is None
        assert proyecto_por_nombre(sesion, "2") is None  # no hay obra de nombre «2»
    finally:
        sesion.close()
        motor.dispose()
