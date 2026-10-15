"""Un caso con una sesion del asistente decidida y guardada (S4 §5.5; plan 0.9.0, tareas 16 y 20).

`plantilla_s4(ruta)` parte de OF-001 con su version `001` y su espacio
(`hoja_en_base.plantilla_of001`), crea las tablas `ia_*` y deja UNA sesion: el asistente propuso
un ambiente, la persona (`ana`) lo decidio (aceptado, por omision) y la sesion quedo guardada en la
version `001`. Con `proveedor` se usa otro proveedor (el adaptador real de Claude con un transporte
falso, en `test_clave_ia_nunca_aparece.py`); por omision, el guionado. Nada escribe en `data/`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from asistente.orquestador import Servicios
from asistente.propuestas import EstadoPropuesta
from asistente.proveedores.base import (
    FinTurno,
    LlamadaHerramienta,
    ProveedorIA,
    Tarifa,
    Turno,
    Uso,
)
from asistente.proveedores.guionado import ProveedorGuionado
from asistente.registro import RegistroIA, crear_esquema_ia
from asistente.servicio import decidir, proponer
from core.catalog import crear_motor
from tests.fixtures.asistente_pedidos import AMBIENTE, PEDIDO, catalogo
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from ui import hoja
from ui.hoja import Borrador

FECHA = date(2026, 10, 5)
PROYECTO = NOMBRE_OF001
VERSION = "001"
QUIEN = "ana"


def proveedor_guionado() -> ProveedorGuionado:
    llamadas = (
        LlamadaHerramienta("a", "proponer_ambiente", AMBIENTE),
        LlamadaHerramienta("t", "terminar", {"notas": []}),
    )
    return ProveedorGuionado(
        [Turno("", llamadas, FinTurno.HERRAMIENTAS, Uso(entrada=10, salida=5))],
        nombre="claude",
        modelo="claude-opus-5-5",
    )


def sesion_en_base(
    ruta: Path,
    *,
    proveedor: ProveedorIA | None = None,
    estado: EstadoPropuesta = EstadoPropuesta.ACEPTADA,
    version: str | None = VERSION,
) -> int:
    """Corre una sesion sobre la base `ruta` (ya con las tablas `ia_*`), decide `P1` con `estado`
    y, si `version` no es `None`, la marca guardada en esa version. Devuelve su numero."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with motor.begin() as con:
            registro = RegistroIA(con)
            servicios = Servicios(
                catalogo=catalogo(),
                tarifa=Tarifa(Decimal(4), Decimal(20)),
                registro=registro,
                auditar=lambda b: hoja.elaborar_borrador(b).elaboracion.informe,
                proyecto=PROYECTO,
                version_partida=VERSION,
            )
            sesion = proponer(
                proveedor if proveedor is not None else proveedor_guionado(),
                PEDIDO,
                Borrador(fecha=FECHA),
                servicios,
            )
            decidir(sesion, "P1", estado, QUIEN, registro)
            if version is not None:
                registro.marcar_guardada(sesion.resultado.sesion, version)
            return sesion.resultado.sesion
    finally:
        motor.dispose()


def plantilla_s4(
    ruta: Path,
    *,
    proveedor: ProveedorIA | None = None,
    estado: EstadoPropuesta = EstadoPropuesta.ACEPTADA,
) -> Path:
    plantilla_of001(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema_ia(motor)
    finally:
        motor.dispose()
    sesion_en_base(ruta, proveedor=proveedor, estado=estado)
    return ruta
