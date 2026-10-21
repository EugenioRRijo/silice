"""Arranque de Sílice con un solo comando (como un `npm run dev`).

    uv run start.py              # prepara los casos de demostración la primera vez y abre la app
    uv run start.py --puerto 8600
    uv run start.py --sin-demo   # no siembra casos (usa los que ya haya en data/casos/)
    uv run start.py --reiniciar-demo   # vuelve a copiar los casos de demostración

Siembra en `data/casos/` (carpeta de datos de desarrollo, no versionada) cinco casos DIDÁCTICOS,
todos ficticios (NORMAS.md §1): `demo`, `of001`, `ti001`, `s1` (copias de las bases de prueba de
la 0.6.0) y `obra_control` (una obra generada con valuaciones y costos para Control de obra).
Nunca toca `data/apu.db`. Un solo proceso (Uvicorn, `api.main:app`) sirve la API y la interfaz
de React (`/app/`, compilada con `npm run build` en frontend-desktop) y escucha solo en 127.0.0.1.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

CASOS_COPIADOS = ("demo", "of001", "ti001", "s1")
BASES_PRUEBA = RAIZ / "tests" / "fixtures" / "bases" / "v0_6_0"
PUERTO_POR_OMISION = 8501
RUTA_INTERFAZ = "/app/"
RUTA_SALUD = "/salud"


def carpeta_casos() -> Path:
    from operacion.config import carpeta_casos as de_la_configuracion

    return de_la_configuracion()


def sembrar_obra_control(destino: Path) -> None:
    """Una obra pequeña con valuaciones y costos registrados, para la pantalla Control de obra."""
    from core.catalog.sesion import abrir_sesion, crear_motor
    from operacion.base_datos import preparar_base
    from scripts.generar_obra_control import (
        generar,
        registrar_costo_de,
        registrar_valuacion_de,
        sembrar,
    )

    destino.unlink(missing_ok=True)
    preparar_base(destino)
    obra = generar(partidas=12, periodos=10, valuaciones=5, semilla=7)
    motor = crear_motor(f"sqlite:///{destino.resolve().as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar(sesion, obra, con_valuaciones=True)
            registrar_valuacion_de(sesion, obra.valuaciones[-1])
            registrar_costo_de(sesion, obra.costos[-1])
            sesion.commit()
    finally:
        motor.dispose()


def preparar_demo(*, reiniciar: bool = False) -> list[str]:
    """Deja los casos de demostración en la carpeta de casos; devuelve lo que sembró."""
    casos = carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    sembrados: list[str] = []
    for nombre in CASOS_COPIADOS:
        origen = BASES_PRUEBA / f"{nombre}.db"
        destino = casos / f"{nombre}.db"
        if not origen.exists():
            print(f"  (no está {origen.relative_to(RAIZ)}; se omite {nombre})")
            continue
        if reiniciar or not destino.exists():
            shutil.copyfile(origen, destino)
            sembrados.append(nombre)
    destino = casos / "obra_control.db"
    if reiniciar or not destino.exists():
        sembrar_obra_control(destino)
        sembrados.append("obra_control")
    return sembrados


def _abrir_navegador_cuando_responda(puerto: int) -> None:
    direccion = f"http://127.0.0.1:{puerto}"
    for _ in range(120):
        try:
            with urllib.request.urlopen(f"{direccion}{RUTA_SALUD}", timeout=1) as respuesta:
                if respuesta.status == 200:
                    webbrowser.open(f"{direccion}{RUTA_INTERFAZ}")
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--puerto", type=int, default=PUERTO_POR_OMISION)
    analizador.add_argument("--sin-demo", action="store_true", help="no siembra casos")
    analizador.add_argument("--reiniciar-demo", action="store_true", help="recopia los casos")
    analizador.add_argument("--sin-navegador", action="store_true")
    args = analizador.parse_args(argv)

    print("Sílice: arranque de demostración (datos ficticios, solo en este equipo)")
    if not args.sin_demo:
        sembrados = preparar_demo(reiniciar=args.reiniciar_demo)
        print(f"  casos sembrados: {', '.join(sembrados) if sembrados else 'ya estaban todos'}")
    print(f"  carpeta de casos: {carpeta_casos()}")
    print(f"  http://127.0.0.1:{args.puerto}{RUTA_INTERFAZ}   (Ctrl+C para detener)")

    if not args.sin_navegador:
        threading.Thread(
            target=_abrir_navegador_cuando_responda, args=(args.puerto,), daemon=True
        ).start()
    orden = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.puerto),
        "--no-access-log",
    ]
    try:
        return subprocess.call(orden, cwd=RAIZ, env=dict(os.environ))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
