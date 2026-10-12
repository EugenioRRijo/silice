"""Única función para mostrar texto ajeno en Markdown (M §4.6, RV‑14): escapa sus caracteres."""

import re

_ESPECIALES = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$])")


def texto_seguro(texto: str) -> str:
    return _ESPECIALES.sub(r"\\\1", texto)
