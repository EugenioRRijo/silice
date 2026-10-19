"""Pantalla «Acerca de»: versión, revisiones de los dos esquemas, carpeta de datos y módulos
instalados (RF-99; spec S5 §5.2). Solo lee: no crea ni migra nada."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import streamlit as st

# RM-1: la lógica vive en aplicacion/acerca.py
from aplicacion.acerca import MODULOS, DatosAcerca, _instalado
from aplicacion.acerca import datos_acerca as _datos_acerca
from ui.caso import ruta_caso

__all__ = ["MODULOS", "DatosAcerca", "_instalado", "datos_acerca", "render"]


def datos_acerca(
    entorno: Mapping[str, str] | None = None,
    *,
    modulo_instalado: Callable[[str], bool] = _instalado,
) -> DatosAcerca:
    """Los datos del caso abierto en esta sesión de Streamlit."""
    return _datos_acerca(ruta_caso(), entorno, modulo_instalado=modulo_instalado)


def render() -> None:
    datos = datos_acerca()
    st.markdown(f"**Sílice {datos.semver}** (versión de `pyproject.toml`: {datos.version})")
    st.markdown(
        f"- Base de la instalación: `{datos.revision_instalacion}` "
        f"(la última es `{datos.head_instalacion}`)\n"
        f"- Base del caso abierto: `{datos.revision_caso}` "
        f"(la última es `{datos.head_caso}`)\n"
        f"- Carpeta de datos: `{datos.carpeta_datos}`"
    )
    st.subheader("Módulos")
    for nombre, instalado in datos.modulos:
        st.markdown(f"- {nombre}: {'instalado' if instalado else 'no instalado'}")
    st.caption("Sílice es software propietario; las licencias de terceros están en LICENCIAS.")
