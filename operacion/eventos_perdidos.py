"""Qué se pierde al restaurar la base de la instalación y cómo se obliga a revisarlo (SEG-12).

Restaurar `instalacion.db` puede revivir claves de firma o de API revocadas, cuentas desactivadas,
roles retirados y revocaciones ajenas. `diferencias` compara la instalación **actual** con la
copia que se va a restaurar y lista solo lo que identifica (login, huella, nombre), nunca una
huella de contraseña ni un secreto. El archivo `eventos_perdidos_<fecha>.json` queda fuera de la
base y mientras tenga `revisado: false` (o no se pueda leer) las operaciones sensibles se bloquean.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from operacion import config


@dataclass(frozen=True, slots=True)
class ReglaTabla:
    clave: str
    etiqueta: str
    estado: tuple[str, ...]


TABLAS_VIGILADAS: dict[str, ReglaTabla] = {
    "usuario": ReglaTabla("id", "login", ("activo", "roles")),
    "clave_empresa": ReglaTabla("id", "huella", ("estado",)),
    "empresa_registrada": ReglaTabla("id", "huella", ("estado",)),
    "clave_api": ReglaTabla("id", "nombre", ("revocada",)),
}
_REVOCADAS = ("retirada", "revocada")


def _filas(ruta: Path, tabla: str, regla: ReglaTabla) -> dict[Any, dict[str, Any]] | None:
    if not ruta.is_file():
        return None
    columnas = [regla.clave, regla.etiqueta, *regla.estado]
    with closing(sqlite3.connect(f"{ruta.resolve().as_uri()}?mode=ro", uri=True)) as conexion:
        existe = conexion.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
        ).fetchone()
        if existe is None:
            return None
        consulta = f"SELECT {', '.join(columnas)} FROM {tabla}"  # nombres fijos, no del usuario
        return {
            fila[0]: dict(zip(columnas, fila, strict=True)) for fila in conexion.execute(consulta)
        }


def _diferencia(
    tipo: str, tabla: str, regla: ReglaTabla, antes: Mapping, despues: Mapping | None
) -> dict:
    return {
        "tipo": tipo,
        "tabla": tabla,
        "id": antes[regla.clave],
        "etiqueta": antes[regla.etiqueta],
        "actual": {c: antes[c] for c in regla.estado},
        "al_restaurar": None if despues is None else {c: despues[c] for c in regla.estado},
    }


def _tipo(tabla: str, actual: Mapping, copia: Mapping) -> list[str]:
    if tabla == "usuario":
        tipos = []
        if not actual["activo"] and copia["activo"]:
            tipos.append("cuenta_reactivada")
        if actual["roles"] != copia["roles"]:
            tipos.append("roles_distintos")
        return tipos
    if tabla == "clave_api":
        return ["clave_api_revivida"] if actual["revocada"] and not copia["revocada"] else []
    revivida = actual["estado"] in _REVOCADAS and copia["estado"] == "activa"
    return ["clave_revivida"] if revivida else []


def diferencias(actual: Path, copia: Path) -> list[dict[str, Any]]:
    """Lo que la restauración de `copia` sobre `actual` deshace en silencio. Una tabla que falta
    en cualquiera de las dos (instalación de la 0.6.0, vacía) no es una diferencia."""
    resultado: list[dict[str, Any]] = []
    for tabla, regla in TABLAS_VIGILADAS.items():
        ahora, antes = _filas(actual, tabla, regla), _filas(copia, tabla, regla)
        if ahora is None or antes is None:
            continue
        for clave, fila in ahora.items():
            otra = antes.get(clave)
            if otra is None:
                resultado.append(
                    _diferencia("registro_posterior_perdido", tabla, regla, fila, None)
                )
                continue
            resultado.extend(
                _diferencia(t, tabla, regla, fila, otra) for t in _tipo(tabla, fila, otra)
            )
    return resultado


def _leer(archivo: Path) -> dict[str, Any] | None:
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def pendientes(entorno: Mapping[str, str] | None = None) -> list[Path]:
    """Los archivos sin revisar. Uno ilegible o sin la marca `revisado: true` cuenta como
    pendiente: ante la duda, se bloquea."""
    carpeta = config.carpeta_datos(entorno)
    if not carpeta.is_dir():
        return []
    return [
        archivo
        for archivo in sorted(carpeta.glob("eventos_perdidos_*.json"))
        if (_leer(archivo) or {}).get("revisado") is not True
    ]


def bloqueadas(entorno: Mapping[str, str] | None = None) -> bool:
    return bool(pendientes(entorno))


def resumen(archivo: Path) -> dict[str, Any]:
    datos = _leer(archivo) or {}
    return {
        "archivo": archivo.name,
        "revisado": datos.get("revisado") is True,
        "eventos": len(datos.get("eventos", [])),
        "diferencias": len(datos.get("diferencias", [])),
        "juego": datos.get("juego"),
    }


def marcar_revisado(archivo: Path, *, por: str | None = None) -> None:
    datos = _leer(archivo) or {}
    datos.update(
        revisado=True, revisado_por=por, revisado_en=datetime.now().isoformat(timespec="seconds")
    )
    temporal = archivo.with_name(archivo.name + ".tmp")
    temporal.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    temporal.replace(archivo)
