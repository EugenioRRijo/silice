"""Configuracion del asistente de la INSTALACION (S4 §3.1: la fija el administrador).

No guarda secretos: la clave de IA de la empresa vive en `asistente.clave`. El asistente viene
APAGADO (excepcion declarada a RNF-08, S4 §3.3); solo se activa cuando el administrador lo decide.
Archivo JSON en la carpeta de datos (`ia_config.json`).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

PROVEEDORES = ("claude", "ollama")
NOMBRE_DEL_ARCHIVO = "ia_config.json"


@dataclass(frozen=True, slots=True)
class ConfiguracionIA:
    activo: bool = False
    proveedor: str = "claude"
    modelo_claude: str = "claude-opus-5-5"
    modelo_local: str = ""
    anfitrion_ollama: str = "http://127.0.0.1:11434"
    tope_usd: Decimal = Decimal(2)
    #: Prefijos de codigo de las partidas que vienen de MaPreX: en modo nube viajan SOLO con codigo
    #: y unidad (P7). Ninguna partida del catalogo actual lo es (`test_asistente_catalogo.py`).
    prefijos_de_maprex: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.proveedor not in PROVEEDORES:
            raise ValueError(f"proveedor desconocido: {self.proveedor!r}")
        if self.tope_usd <= 0:
            raise ValueError("el tope de costo debe ser positivo")


def leer(ruta: Path) -> ConfiguracionIA:
    """La configuracion guardada, o la de fabrica (apagada) si falta el archivo o no se lee."""
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["tope_usd"] = Decimal(str(datos.get("tope_usd", "2")))
        datos["prefijos_de_maprex"] = tuple(datos.get("prefijos_de_maprex", ()))
        return ConfiguracionIA(**datos)
    except (OSError, ValueError, TypeError, ArithmeticError):
        return ConfiguracionIA()


def de_maprex(codigo: str, configuracion: ConfiguracionIA) -> bool:
    """True si el codigo de la partida cae bajo un prefijo de MaPreX de la configuracion."""
    return any(codigo.startswith(p) for p in configuracion.prefijos_de_maprex)


def guardar(ruta: Path, configuracion: ConfiguracionIA) -> None:
    datos = asdict(configuracion)
    datos["tope_usd"] = str(configuracion.tope_usd)
    ruta.write_text(json.dumps(datos, indent=2, sort_keys=True) + "\n", encoding="utf-8")
