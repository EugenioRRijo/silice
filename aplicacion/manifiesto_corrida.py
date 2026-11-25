"""Manifiesto determinista de una corrida de evaluación o auditoría (Fase 1).

Registra la versión de Sílice, el SHA-256 de cada archivo de reglas y umbrales, un SHA-256 global,
la versión del motor externo (LibreOffice), la semilla y la configuración regional. No consulta el
reloj ni incluye fechas: mismas entradas producen exactamente el mismo diccionario.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

__all__ = [
    "ARCHIVOS_REGLAS",
    "RAIZ",
    "manifiesto",
]

RAIZ = Path(__file__).resolve().parents[1]

ARCHIVOS_REGLAS: tuple[Path, ...] = (
    RAIZ / "core" / "verification" / "reglas.py",
    RAIZ / "adapters" / "hoja_empresa" / "reglas.py",
    RAIZ / "adapters" / "hoja_empresa" / "reglas_calculo.py",
    RAIZ / "adapters" / "hoja_empresa" / "reglas_contexto.py",
    RAIZ / "adapters" / "vial" / "reglas.py",
    RAIZ / "adapters" / "vial" / "constantes.py",
    RAIZ / "aplicacion" / "causas_raiz.py",
)


def _version_silice() -> str | None:
    try:
        from operacion.version import version
    except ImportError:
        return None
    try:
        return version()
    except OSError:
        return None


def _clave_y_ruta(entrada: Path | str, raiz: Path) -> tuple[str, Path]:
    ruta = Path(entrada)
    if not ruta.is_absolute():
        return ruta.as_posix(), raiz / ruta
    resuelta = ruta.resolve()
    raiz_resuelta = raiz.resolve()
    if resuelta.is_relative_to(raiz_resuelta):
        return resuelta.relative_to(raiz_resuelta).as_posix(), ruta
    return ruta.as_posix(), ruta


def _huellas_reglas() -> dict[str, str]:
    pares: dict[str, str] = {}
    for entrada in ARCHIVOS_REGLAS:
        clave, ruta = _clave_y_ruta(entrada, RAIZ)
        if not ruta.is_file():
            raise FileNotFoundError(f"No existe el archivo de reglas: {ruta}")
        pares[clave] = hashlib.sha256(ruta.read_bytes()).hexdigest()
    return dict(sorted(pares.items()))


def manifiesto(
    *,
    version_libreoffice: str | None = None,
    semilla: int | None = None,
    configuracion_regional: str = "es-VE",
) -> dict[str, Any]:
    """Construye el manifiesto determinista de la corrida (sin reloj ni fecha)."""
    contenido: dict[str, Any] = {
        "version_silice": _version_silice(),
        "reglas": _huellas_reglas(),
        "version_libreoffice": version_libreoffice,
        "semilla": semilla,
        "configuracion_regional": configuracion_regional,
    }
    canonico = json.dumps(contenido, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    huella_global = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
    return {
        **contenido,
        "sha256": huella_global,
    }
