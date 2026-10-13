"""El caso S2 de la base de prueba de la 0.7.0 (RV-3, PRU-H15; plan 0.7.0, tarea 15).

Una base en `head` con lo que agrega S2: la obra OB-S2 de la memoria `control_ob_s2.md` con su
línea base de control, V-01 y V-02 registradas, el costo incurrido de 1 280,00 USD y la decisión
«más cuadrillas» tomada al corte (versión `OB-002`, motivo `recuperacion`, siete cambios de
plan). Las fechas de registro son fijas, así que la base se reconstruye igual.
El plan pide que `scripts/generar_base_prueba.py` la construya con el código de la etiqueta
`v0.7.0` (`CONSTRUCTORES` con `"s2.db"`); esa parte de la tarea 15 no se construyó (la versión sigue
en 0.6.0 y no hay etiqueta), así que hoy solo la usa `tests/integration/test_caso_s2.py`, escrita en
la auditoría final (2026-10-13). Datos ficticios (NORMAS.md §1).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.budget.control import (
    calcular_control,
    composiciones_de_la_linea_base,
    contexto_de_recuperacion,
)
from core.budget.decision import aplicar_decision
from core.budget.recuperacion import opciones
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures import control_ob_s2 as ob

MOMENTO_DE_LA_DECISION = datetime(2026, 11, 16, 10, 0)


def sembrar_caso_s2(sesion) -> None:
    """OB-S2 con sus dos valuaciones, su costo y la decisión «más cuadrillas». No confirma."""
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion)
    ob.registrar_v01_y_v02(sesion)
    catalogo = Catalogo(sesion)
    resultado = calcular_control(
        sesion, ob.NOMBRE, catalogo=catalogo, precios=ob.precios_del_corte()
    )
    contexto = contexto_de_recuperacion(resultado, composiciones_de_la_linea_base(resultado))
    cuadrillas = next(o for o in opciones(contexto) if o.nombre == "cuadrillas")
    aplicar_decision(
        sesion,
        resultado,
        cuadrillas,
        catalogo=catalogo,
        fuente="base de prueba 0.7.0",
        responsable=ob.RESPONSABLE,
        ahora=MOMENTO_DE_LA_DECISION,
    )


def plantilla_s2(ruta: Path) -> Path:
    """Siembra el caso S2 en `ruta` (ya en `head`) y confirma."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_caso_s2(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta
