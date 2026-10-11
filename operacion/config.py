"""Dónde viven los datos de Sílice (maestro §4.2; spec S5 §5.3).

En el producto, el lanzador (S5-2) fija `SILICE_DATOS` (`%LOCALAPPDATA%\\Silice\\datos`),
`SILICE_INSTALACION` y `SILICE_RESPALDOS` (`%LOCALAPPDATA%\\Silice\\respaldos`). En desarrollo,
`SILICE_DATOS` vale por defecto `data/` del repositorio, con la misma disposición: `instalacion.db`,
`casos/`, `paquetes/`, `codigo_instalacion.txt` y `respaldos/` (todos en `.gitignore`).

Las funciones reciben el entorno para que las pruebas no dependan de `os.environ`, y **ninguna crea
carpetas**: las crea quien escribe.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

VARIABLE_DATOS = "SILICE_DATOS"
VARIABLE_INSTALACION = "SILICE_INSTALACION"
VARIABLE_RESPALDOS = "SILICE_RESPALDOS"

RAIZ = Path(__file__).resolve().parents[1]
DATOS_DESARROLLO = RAIZ / "data"
NOMBRE_INSTALACION = "instalacion.db"
CARPETA_CASOS = "casos"
CARPETA_RESPALDOS = "respaldos"
CASO_POR_DEFECTO = "silice.db"
#: La base de trabajo de las versiones 0.1 a 0.5 (`scripts/seed.py`, `ui/caso.py`, `api`). No se
#: abre en su sitio: se adopta COPIÁNDOLA a la carpeta de casos con `python -m operacion adoptar`.
BASE_ANTERIOR = DATOS_DESARROLLO / "apu.db"


def _valor(nombre: str, entorno: Mapping[str, str] | None) -> str:
    fuente = os.environ if entorno is None else entorno
    return fuente.get(nombre, "").strip()


def _ruta(valor: str) -> Path:
    return Path(valor).expanduser().resolve()


def carpeta_datos(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_DATOS` si está; si no, `data/` del repositorio."""
    valor = _valor(VARIABLE_DATOS, entorno)
    return _ruta(valor) if valor else DATOS_DESARROLLO


def carpeta_casos(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_datos(entorno) / CARPETA_CASOS


def ruta_instalacion(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_INSTALACION` si está; si no, `instalacion.db` de la carpeta de datos."""
    valor = _valor(VARIABLE_INSTALACION, entorno)
    return _ruta(valor) if valor else carpeta_datos(entorno) / NOMBRE_INSTALACION


def carpeta_respaldos(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_RESPALDOS` si está; si no, `respaldos/` dentro de la carpeta de datos."""
    valor = _valor(VARIABLE_RESPALDOS, entorno)
    return _ruta(valor) if valor else carpeta_datos(entorno) / CARPETA_RESPALDOS


def ruta_caso_por_defecto(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_casos(entorno) / CASO_POR_DEFECTO
