"""Pagina de historico de cambios de precio (UC-02): `CambioPrecio` con filtros (Sesion F.1).

Solo lectura, la misma consulta que expone `api/rutas/listas.py::listar_cambios_precio`, pero
llamando a `core` directo: la UI no consume la API por HTTP (decision del usuario, 2026-08-31, spec
F.1 §4). La consulta vive una sola vez en `core.catalog.cambios_precio` (hallazgo menor diferido
de la bitacora F.1, consolidado); esta pagina solo presenta.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core import models
from core.catalog import abrir_sesion, cambios_precio, crear_motor
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from operacion.base_datos import preparar_base
from ui.caso import ruta_caso

CIEN = Decimal(100)


def render() -> None:
    """Filtros en la barra lateral; la tabla de cambios en el cuerpo."""
    st.caption(
        "Cada fila es un insumo que cambio de precio entre la lista anterior y la lista nueva de "
        "una actualizacion (UC-02)."
    )

    ruta = ruta_caso()
    insumo, desde, hasta = _filtros()

    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        preparar_base(ruta)
        with abrir_sesion(motor) as sesion:
            cambios = cambios_precio(sesion, insumo=insumo or None, desde=desde, hasta=hasta)
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # Mismo criterio que `ui/paginas/actualizacion.py`: un archivo de base de datos corrupto
        # o inaccesible (`ErrorDeBase` de `preparar_base`) es un mensaje, no una traza cruda.
        # `return` aqui no salta el `finally`: `motor.dispose()` corre igual antes de salir.
        st.error(str(error))
        return
    finally:
        motor.dispose()

    _mostrar(cambios)


def _filtros() -> tuple[str, date | None, date | None]:
    with st.sidebar:
        st.header("Filtros")
        insumo = st.text_input("Insumo (descripcion exacta)", value="")

        con_desde = st.checkbox("Filtrar desde una fecha", value=False)
        desde = st.date_input("Desde", value=date.today()) if con_desde else None

        con_hasta = st.checkbox("Filtrar hasta una fecha", value=False)
        hasta = st.date_input("Hasta", value=date.today()) if con_hasta else None

    return insumo, desde, hasta


def _mostrar(cambios: list[models.CambioPrecio]) -> None:
    if not cambios:
        st.info("No hay cambios de precio registrados con esos filtros.")
        return

    tabla = DataFrame(
        [
            {
                "fecha": cambio.fecha,
                "insumo": cambio.insumo.descripcion,
                "precio_anterior": formatear_decimal(
                    cambio.precio_anterior, DECIMALES_PRESENTACION
                ),
                "precio_nuevo": formatear_decimal(cambio.precio_nuevo, DECIMALES_PRESENTACION),
                "variacion_pct": formatear_decimal(cambio.variacion * CIEN, DECIMALES_PRESENTACION),
            }
            for cambio in cambios
        ]
    )
    st.dataframe(tabla, hide_index=True)
