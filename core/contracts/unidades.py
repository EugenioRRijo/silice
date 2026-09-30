"""Normalización de unidades de medida.

Única tabla de alias del sistema (principio DRY, NORMAS.md §2). Solo unifica grafías de la MISMA
unidad (m³ ≡ m3, mts ≡ m). Unidades distintas siguen siendo distintas: "pieza" nunca equivale a "m",
porque la regla R3 (coherencia dimensional) necesita detectar exactamente esa diferencia.
"""

from __future__ import annotations

_ALIAS: dict[str, str] = {
    # volumen
    "m3": "m3",
    "m³": "m3",
    "mts3": "m3",
    "mt3": "m3",
    "metro cubico": "m3",
    "metros cubicos": "m3",
    # superficie
    "m2": "m2",
    "m²": "m2",
    "mts2": "m2",
    "mt2": "m2",
    "metro cuadrado": "m2",
    "metros cuadrados": "m2",
    # longitud
    "m": "m",
    "ml": "m",
    "mts": "m",
    "mt": "m",
    "metro": "m",
    "metros": "m",
    "metro lineal": "m",
    "metros lineales": "m",
    # conteo
    "pieza": "pieza",
    "pza": "pieza",
    "pzas": "pieza",
    "piezas": "pieza",
    "unidad": "unidad",
    "und": "unidad",
    "un": "unidad",
    "u": "unidad",
    "unidades": "unidad",
    "punto": "punto",
    "pto": "punto",
    "puntos": "punto",
    "saco": "saco",
    "sacos": "saco",
    # masa
    "kg": "kg",
    "kgs": "kg",
    "kilogramo": "kg",
    "kilogramos": "kg",
    # tiempo
    "dia": "dia",
    "día": "dia",
    "dias": "dia",
    "días": "dia",
    "h": "h",
    "hora": "h",
    "horas": "h",
    "hh": "h",
    # global
    "sg": "sg",
    "s.g.": "sg",
    "suma global": "sg",
    "global": "sg",
}


def normalizar_unidad(unidad: str) -> str:
    """Devuelve la forma canónica de una unidad (minúsculas, sin espacios extra, alias resuelto).

    Una unidad desconocida se devuelve normalizada en grafía pero sin traducir, para no ocultar
    errores de transcripción.
    """
    clave = " ".join(unidad.strip().lower().split())
    if not clave:
        raise ValueError("La unidad no puede estar vacía")
    return _ALIAS.get(clave, clave)


def unidades_equivalentes(una: str, otra: str) -> bool:
    """True si ambas unidades son la misma tras normalizar."""
    return normalizar_unidad(una) == normalizar_unidad(otra)
