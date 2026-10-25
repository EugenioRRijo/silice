"""La carpeta de demostración se construye en un proceso hijo (BCP-2; diseño §4.5, §16 9.1).

La API no puede importar `scripts/` (ARQ-5: `scripts.seed_demo` importa `scripts.seed`, que importa
`tests.fixtures`), así que la demostración la siembra la orden de siempre,
`python -m operacion demostracion`, en otro proceso y sobre una ruta absoluta que arma el servidor
(`--salida`, dentro de la cuarentena de la carpeta de datos): **ningún texto de la persona llega al
hijo**. Mismos indicadores que el acceso directo del instalador (`-E -s -B -X utf8`), sin shell, sin
consola en Windows, con la carpeta del programa como directorio de trabajo y un plazo de 120 s
(supuesto D-4); vencido, el hijo se mata.

La salida del hijo (lo que imprime el sembrador) no se reenvía a nadie ni se registra: solo el
código de salida. Quien valida y publica el archivo es `aplicacion.casos.demostracion`.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from operacion import config

__all__ = ["PLAZO_S", "DemostracionFallida", "construir", "entorno_hijo", "orden"]

#: Segundos que puede tardar el hijo (D-4: supuesto, por medir en BCP-10; en este equipo, ~8 s).
PLAZO_S = 120
_SIN_CONSOLA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_registro = logging.getLogger("silice.casos")


class DemostracionFallida(Exception):  # noqa: N818
    """El hijo no dejó una demostración: terminó con error, pasó el plazo o no escribió nada."""


def orden(salida: Path) -> list[str]:
    """La orden del hijo: el intérprete de este proceso y `--salida` absoluta."""
    return [
        sys.executable,
        "-E",
        "-s",
        "-B",
        "-X",
        "utf8",
        "-m",
        "operacion",
        "demostracion",
        "--salida",
        str(salida),
    ]


def entorno_hijo(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """El entorno de este proceso sin `PYTHON*` ni `VIRTUAL_ENV` (como el del lanzador): conserva
    `SILICE_*`, así el hijo ve la misma carpeta de datos."""
    origen = os.environ if base is None else base
    return {
        clave: valor
        for clave, valor in origen.items()
        if not clave.upper().startswith("PYTHON") and clave.upper() != "VIRTUAL_ENV"
    }


def construir(salida: Path, *, plazo: float = PLAZO_S) -> None:
    """Corre el hijo que siembra la demostración en `salida` (absoluta). `DemostracionFallida` si
    termina con error, pasa `plazo` o no deja el archivo."""
    salida = Path(salida)
    if not salida.is_absolute():
        raise DemostracionFallida("la salida de la demostración debe ser una ruta absoluta")
    try:
        resultado = subprocess.run(  # noqa: S603 - orden fija, sin shell ni texto de la persona
            orden(salida),
            cwd=config.RAIZ,
            env=entorno_hijo(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=plazo,
            check=False,
            creationflags=_SIN_CONSOLA,
        )
    except subprocess.TimeoutExpired:
        _registro.warning("la demostración pasó su plazo de %s s", plazo)
        raise DemostracionFallida("la demostración pasó su plazo") from None
    except OSError as error:
        _registro.warning("no se pudo lanzar la demostración: %s", type(error).__name__)
        raise DemostracionFallida("no se pudo lanzar la demostración") from None
    if resultado.returncode != 0:
        _registro.warning("la demostración terminó con el código %s", resultado.returncode)
        raise DemostracionFallida(f"el hijo terminó con {resultado.returncode}")
    if not salida.is_file():
        raise DemostracionFallida("el hijo no dejó la base de la demostración")
