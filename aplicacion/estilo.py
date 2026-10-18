"""Paleta y formatos de la interfaz de trabajo (PLAN_SILICE_UI, tarea 1). Sin Streamlit.

Una sola copia de los colores para los graficos (`ui.graficos`) y las pantallas. El tema de
`.streamlit/config.toml` repite `COLOR_PRIMARIO` y los fondos porque Streamlit no lee Python.

Los formatos devuelven texto para mostrar; el monto sigue siendo `Decimal` hasta aqui.
"""

from __future__ import annotations

from decimal import Decimal

from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal

COLOR_PRIMARIO = "#1F4E79"
COLOR_TENUE = "#E6E9EE"
COLOR_BIEN = "#2E7D5B"
COLOR_ATENCION = "#D9A441"

COLORES_RUBRO: dict[str, str] = {
    "Materiales": "#1F4E79",
    "Equipos": "#5B8DB8",
    "Mano de obra": "#D9A441",
    "Administracion": "#7A7F87",
    "Utilidad": "#2E7D5B",
}
COLORES_SERIE: dict[str, str] = {
    "Plan": "#1F4E79",
    "PV": "#7A7F87",
    "EV": "#D9A441",
    "AC": "#B5443A",
}

NO_DISPONIBLE = "no disponible"


def dinero(valor: Decimal | None, moneda: str) -> str:
    """Un monto con los decimales de presentacion y su moneda; `None` es «no disponible»."""
    if valor is None:
        return NO_DISPONIBLE
    return f"{formatear_decimal(valor, DECIMALES_PRESENTACION)} {moneda}"


def porcentaje(fraccion: Decimal | None) -> str:
    """Una fraccion (0.15) como porcentaje con un decimal (15.0 %)."""
    if fraccion is None:
        return NO_DISPONIBLE
    return f"{formatear_decimal(fraccion * 100, 1)} %"


def indice(valor: Decimal | None) -> str:
    """Un indice (SPI, CPI) con dos decimales."""
    if valor is None:
        return NO_DISPONIBLE
    return formatear_decimal(valor, 2)
