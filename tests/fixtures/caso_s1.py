"""El caso S1 de la base de prueba de la 0.6.0 (RV-3, PRU-H15; plan 0.6.0, seccion C, tarea 14).

Una base en `head` con lo que agrega S1: la clinica (linea base) con su 001 en USD convertida a Bs
(002), la lista de empresa de `s1_precios_empresa.md` y el estudio de `s1_reajuste.md` guardado.
`scripts/generar_base_prueba.py` la construye con el codigo de la etiqueta `v0.6.0`, despues de que
`preparar_base` la creo en `head`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import select

from core import models
from core.budget.moneda import convertir_version
from core.budget.reajuste import guardar_estudio
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.catalog.indices import tasa_aplicable
from core.catalog.moneda import TasaDeclarada
from scripts.seed import sembrar as sembrar_linea_base
from tests.fixtures import precios_empresa_s1, reajuste_s1
from tests.fixtures.versiones import elaborar_001, guardar_001

FECHA_CONVERSION = date(2026, 10, 1)  # tasa venta 860,18 (BCV, verificada; s1_conversion.md)


def sembrar_caso_s1(sesion) -> None:
    """Clinica convertida, lista de empresa y estudio de reajuste. No hace `commit`."""
    proyecto = sembrar_linea_base(sesion)
    guardar_001(sesion, proyecto, elaborar_001(sesion))
    precios_empresa_s1.sembrar(sesion)
    tasa = TasaDeclarada.de_importacion(tasa_aplicable(sesion, FECHA_CONVERSION))
    convertir_version(
        sesion,
        proyecto.nombre,
        "001",
        "002",
        "Bs",
        tasa,
        fuente="base de prueba 0.6.0",
        responsable="Ing. Prueba",
        catalogo=Catalogo(sesion),
    )
    reajuste_s1.sembrar(sesion)
    contrato = sesion.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == reajuste_s1.NOMBRE, models.Presupuesto.codigo == "001")
    ).one()
    guardar_estudio(
        sesion,
        contrato,
        reajuste_s1.CLAUSULA,
        [reajuste_s1.PERIODO],
        fecha_calculo=date(2027, 3, 5),
        fuente="base de prueba 0.6.0",
        responsable="Ing. Prueba",
    )


def plantilla_s1(ruta: Path) -> Path:
    """Siembra el caso S1 en `ruta` (ya en `head`) y confirma."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_caso_s1(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta
