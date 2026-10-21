"""Arranque real de Uvicorn (`api.main:app`): la salud de §11.2 en `/salud`, la interfaz en `/app/`.

Acotada: puerto libre elegido por el sistema, un plazo máximo para la salud, la parada por la
orden del producto (`operacion parar`) y, si algo queda vivo, se terminan SOLO los procesos que
esta prueba lanzó (el suyo y los PID que su propia instancia anotó en `servidor.json` de la
carpeta temporal). No toca el cortafuegos ni pide permisos: escucha en `127.0.0.1`.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from operacion import config
from operacion.config import Ajustes

RAIZ = Path(__file__).resolve().parents[2]
BANDERAS = ["-E", "-s", "-B", "-X", "utf8", "-m", "operacion"]
#: Uvicorn con la API tarda unos segundos en frío (más con cobertura): margen holgado y acotado.
PLAZO_ARRANQUE_S = 150
PLAZO_PARADA_S = 60


def _puerto_libre() -> int:
    with socket.socket() as zocalo:
        zocalo.bind(("127.0.0.1", 0))
        return int(zocalo.getsockname()[1])


def _salud(puerto: int) -> bool:
    try:
        with urllib.request.urlopen(  # noqa: S310 (bucle local)
            f"http://127.0.0.1:{puerto}/salud", timeout=2
        ) as respuesta:
            return respuesta.status == 200
    except OSError:
        return False


def _terminar(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)  # en Windows: TerminateProcess
    except OSError:
        pass


def test_arranca_en_el_bucle_local_y_se_detiene() -> None:
    puerto = _puerto_libre()
    config.guardar_ajustes(
        config.ruta_ajustes(), Ajustes(puerto=puerto, mostrar_investigacion=True)
    )
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    servidor = subprocess.Popen(
        [sys.executable, *BANDERAS, "arrancar", "--sin-navegador"],
        cwd=RAIZ,
        env=entorno,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pids_propios: tuple[int, ...] = ()
    parada: subprocess.CompletedProcess[bytes] | None = None
    try:
        limite = time.monotonic() + PLAZO_ARRANQUE_S
        while time.monotonic() < limite and not _salud(puerto) and servidor.poll() is None:
            time.sleep(1)
        assert _salud(puerto), (
            f"Uvicorn no respondió en {PLAZO_ARRANQUE_S} s (código del lanzador: "
            f"{servidor.poll()}): ¿falló api.main:app al importarse?"
        )
        estado = json.loads(config.ruta_estado().read_text(encoding="utf-8"))
        pids_propios = tuple(int(p) for p in estado["pids"])
        assert estado["direccion"] == "127.0.0.1" and estado["puerto"] == puerto
        assert "puerto_api" not in estado and len(pids_propios) == 2  # lanzador + Uvicorn
        if (RAIZ / "frontend-desktop" / "dist" / "index.html").is_file():  # compilada (CI: no)
            with urllib.request.urlopen(  # noqa: S310 (bucle local)
                f"http://127.0.0.1:{puerto}/app/", timeout=5
            ) as interfaz:  # la interfaz de React, en el mismo puerto
                assert interfaz.status == 200
                assert interfaz.headers["content-type"].startswith("text/html")
        # Una segunda orden «arrancar» no lanza otra instancia: ve la viva y sale con 0.
        segunda = subprocess.run(
            [sys.executable, *BANDERAS, "arrancar", "--sin-navegador"],
            cwd=RAIZ,
            env=entorno,
            capture_output=True,
            timeout=PLAZO_PARADA_S,
            check=False,
        )
        assert segunda.returncode == 0
        assert "ya está en marcha" in segunda.stdout.decode("utf-8", errors="replace")
    finally:
        parada = subprocess.run(
            [sys.executable, *BANDERAS, "parar"],
            cwd=RAIZ,
            env=entorno,
            capture_output=True,
            check=False,
            timeout=PLAZO_PARADA_S,
        )
        try:
            servidor.wait(timeout=30)
        except subprocess.TimeoutExpired:
            servidor.kill()  # solo el hijo que esta misma prueba lanzó
            servidor.wait(timeout=10)
        if _salud(puerto):  # red de seguridad: los PID que anotó nuestra propia instancia
            for pid in reversed(pids_propios):
                _terminar(pid)
    assert parada is not None and parada.returncode == 0, parada
    limite = time.monotonic() + 15
    while time.monotonic() < limite and _salud(puerto):
        time.sleep(0.5)
    assert not _salud(puerto)
    assert not config.ruta_estado().exists()
    assert servidor.returncode is not None
