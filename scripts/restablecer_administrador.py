"""Devuelve el acceso de un administrador que perdió su contraseña o quedó bloqueado (S3 §5.4).

Exige **acceso al equipo**: corre en la máquina donde está instalado Sílice, con Sílice detenido o
no. Emite un código de instalación nuevo de un solo uso (20 caracteres base32, 100 bits) en
`<datos>/codigo_instalacion.txt` y en la consola, y **cierra las sesiones de los
administradores**. Con ese código, la pantalla de acceso deja crear de nuevo una cuenta de
administrador (o devolverle el acceso a la que existe) aunque ya haya usuarios; el código se
borra al usarse. Quien lo corre queda en `evento_acceso` (tipo `codigo de instalacion`, motivo
`restablecimiento`).

    uv run python scripts/restablecer_administrador.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion.config import carpeta_datos  # noqa: E402
from operacion.instalacion import cerrar_motores, sesion_de_instalacion  # noqa: E402
from seguridad import cuentas  # noqa: E402


def restablecer(ahora: datetime | None = None) -> tuple[str, Path]:
    """`(código, archivo)`: emite el código de restablecimiento y cierra las sesiones de los
    administradores de la instalación de `SILICE_INSTALACION` / la carpeta de datos."""
    carpeta = carpeta_datos()
    with sesion_de_instalacion() as bd:
        codigo = cuentas.emitir_codigo_de_restablecimiento(bd, carpeta, ahora or datetime.now())
    return codigo, carpeta / cuentas.NOMBRE_ARCHIVO_CODIGO


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        codigo, archivo = restablecer()
    finally:
        cerrar_motores()
    print("Código de instalación nuevo (de un solo uso):")
    print(f"  {cuentas.formato_codigo(codigo)}")
    print(f"También está en {archivo}. Las sesiones de los administradores quedaron cerradas.")
    print("Escríbalo en la pantalla de acceso de Sílice para crear o recuperar la cuenta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
