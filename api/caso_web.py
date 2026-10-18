"""El caso de cada sesión del navegador (RM-2, plan de la sesión 2b).

Streamlit ya deja un caso por pestaña (`ui/caso.py`); la interfaz nueva hace lo mismo por ficha de
sesión: `POST /v1/casos/actual` guarda aquí, **en memoria del proceso**, la ruta del caso elegido
bajo la huella de la ficha (`seguridad.sesiones.huella_de`, nunca la ficha misma). Sin elección,
la ficha trabaja en el caso del proceso (`APU_BASE` o el por defecto de la carpeta de datos), que
es también el de quien entra con la clave de API.

La elección se olvida al salir, al expirar la ficha y al volver a entrar desde el mismo navegador;
al cambiar la contraseña pasa a la ficha nueva (es la misma persona). Al reiniciar la API todas
vuelven al caso por defecto (costo declarado en RM-2). Una ficha cerrada desde otro sitio (otro
navegador que cambió la contraseña, el administrador) deja su entrada hasta que ese navegador
vuelva: es inofensiva, porque una ficha cerrada no vuelve a validar.
"""

from __future__ import annotations

import threading
from pathlib import Path

_elegidos: dict[str, Path] = {}
_cerrojo = threading.Lock()


def elegido(huella: str) -> Path | None:
    """El caso que eligió la ficha de huella `huella`, o `None` si no eligió ninguno."""
    with _cerrojo:
        return _elegidos.get(huella)


def fijar(huella: str, ruta: Path) -> None:
    with _cerrojo:
        _elegidos[huella] = ruta


def olvidar(huella: str) -> None:
    with _cerrojo:
        _elegidos.pop(huella, None)


def heredar(anterior: str, nueva: str) -> None:
    """La ficha `nueva` sigue en el caso de `anterior` (cambio de contraseña), que se olvida."""
    with _cerrojo:
        ruta = _elegidos.pop(anterior, None)
        if ruta is not None:
            _elegidos[nueva] = ruta


def olvidar_todo() -> None:
    """Solo para las pruebas: ninguna hereda la elección de otra."""
    with _cerrojo:
        _elegidos.clear()
