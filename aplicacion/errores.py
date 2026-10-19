"""Errores de aplicación compartidos por varias pantallas y por la API (RM-1).

`HojaInvalida` nació en `ui/hoja.py`; vive aquí para que `aplicacion/` y `api/` la usen sin
importar `ui/`. `ui.hoja` la reimporta con el mismo nombre: es la misma clase, así que todos los
`except HojaInvalida` y `pytest.raises(HojaInvalida)` siguen valiendo.
"""

from __future__ import annotations


class HojaInvalida(ValueError):  # noqa: N818
    """Una fila (o el conjunto) del borrador no forma un espacio valido; dice cual y por que."""
