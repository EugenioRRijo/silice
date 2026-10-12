"""Pantalla «Acerca de»: versión, revisiones de los dos esquemas, carpeta de datos y módulos
instalados (RF-99; spec S5 §5.2). Solo lee: no crea ni migra nada."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from operacion import config
from operacion.base_datos import Destino, ErrorDeBase, leer_estado, revision_head
from operacion.version import a_semver, version
from ui.caso import ruta_caso

#: (rótulo, paquete de Python que lo habilita)
MODULOS: tuple[tuple[str, str], ...] = (
    ("Similitud de partidas", "sentence_transformers"),
    ("Anomalías de precios", "sklearn"),
    ("Planos IFC", "ifcopenshell"),
    ("Planos DXF", "ezdxf"),
    ("Informes PDF", "reportlab"),
    ("Datos del BCV", "xlrd"),
    ("Asistente de IA", "anthropic"),
)


@dataclass(frozen=True, slots=True)
class DatosAcerca:
    version: str
    semver: str
    revision_instalacion: str
    head_instalacion: str
    revision_caso: str
    head_caso: str
    carpeta_datos: str
    modulos: tuple[tuple[str, bool], ...]


def _instalado(nombre: str) -> bool:
    try:
        return importlib.util.find_spec(nombre) is not None
    except (ImportError, ValueError):
        return False


def _revision(ruta: Path, destino: Destino) -> tuple[str, str]:
    """`(revisión de la base, última revisión que conoce esta versión)`; sin escribir nada."""
    head = revision_head(destino) or "sin revisiones"
    try:
        estado = leer_estado(ruta)
    except ErrorDeBase:
        return "ilegible", head
    if not estado.existe:
        return "sin base", head
    return (estado.revision or "sin alembic_version"), head


def datos_acerca(
    entorno: Mapping[str, str] | None = None,
    *,
    modulo_instalado: Callable[[str], bool] = _instalado,
) -> DatosAcerca:
    instalacion, head_instalacion = _revision(config.ruta_instalacion(entorno), Destino.INSTALACION)
    caso, head_caso = _revision(ruta_caso(), Destino.CASO)
    return DatosAcerca(
        version=version(),
        semver=a_semver(version()),
        revision_instalacion=instalacion,
        head_instalacion=head_instalacion,
        revision_caso=caso,
        head_caso=head_caso,
        carpeta_datos=str(config.carpeta_datos(entorno)),
        modulos=tuple((nombre, modulo_instalado(paquete)) for nombre, paquete in MODULOS),
    )


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
