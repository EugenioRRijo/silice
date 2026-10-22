"""Un Uvicorn REAL en 127.0.0.1 con datos temporales: el primer arranque de punta a punta (BCP-1;
S7 y §16 9.5 del diseño).

El servidor arranca sin cuentas, el gancho `lifespan` emite el código, un reclamo por HTTP crea el
primer administrador y, al apagarlo, se busca el código y la contraseña en TODO lo que el proceso
imprimió (salida estándar y de error, mezcladas). Nada toca `data/`: `SILICE_DATOS`,
`SILICE_USUARIO` y las demás rutas apuntan a la carpeta temporal de la prueba, y el proceso se
detiene por su PID (nunca por nombre).
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from operacion import config, lanzador

PLAZO_S = 120
CLAVE = "una clave larga de prueba del servidor 4417"


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as zocalo:
        zocalo.bind(("127.0.0.1", 0))
        return int(zocalo.getsockname()[1])


def _esperar_salud(url: str, proceso: subprocess.Popen[str]) -> None:
    limite = time.monotonic() + PLAZO_S
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            raise AssertionError("el servidor terminó antes de responder")
        try:
            with urllib.request.urlopen(url + "/salud", timeout=2) as respuesta:  # noqa: S310
                if respuesta.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    raise AssertionError("el servidor no respondió a tiempo")


def _pedir(url: str, ruta: str, datos: dict | None = None, origen: str | None = None):
    cabeceras = {"Content-Type": "application/json"}
    if origen:
        cabeceras["Origin"] = origen
    cuerpo = None if datos is None else json.dumps(datos).encode("utf-8")
    peticion = urllib.request.Request(url + ruta, data=cuerpo, headers=cabeceras)  # noqa: S310
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:  # noqa: S310
            cabeceras_ = {k.lower(): v for k, v in respuesta.headers.items()}
            return respuesta.status, json.loads(respuesta.read()), cabeceras_
    except urllib.error.HTTPError as error:
        return (
            error.code,
            json.loads(error.read()),
            {k.lower(): v for k, v in error.headers.items()},
        )


def test_un_servidor_real_emite_el_codigo_crea_al_administrador_y_no_imprime_secretos(
    tmp_path: Path,
) -> None:
    puerto = _puerto_libre()
    url = f"http://127.0.0.1:{puerto}"
    entorno = {
        config.VARIABLE_DATOS: str(tmp_path / "datos"),
        config.VARIABLE_USUARIO: str(tmp_path / "usuario"),
    }
    env = lanzador.entorno_hijos(config.Ajustes(), "127.0.0.1", entorno)
    orden = lanzador.orden_uvicorn(Path(sys.executable), "127.0.0.1", puerto)
    orden.insert(
        1, "-u"
    )  # sin búfer: se detiene por PID y lo no volcado se perdería (`-E` ignora PYTHONUNBUFFERED)
    proceso = subprocess.Popen(  # noqa: S603
        orden,
        cwd=config.RAIZ,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    salida = ""
    codigo = escrito = "<sin-codigo>"  # si algo falla antes de leerlo, no es un falso hallazgo
    try:
        _esperar_salud(url, proceso)
        archivo = tmp_path / "datos" / "codigo_instalacion.txt"
        assert archivo.is_file()  # lo emitió el gancho `lifespan`, sin que nadie lo pidiera
        escrito = archivo.read_text(encoding="ascii").strip()
        codigo = escrito.replace("-", "")
        assert len(escrito) == 24 and len(codigo) == 20

        estado, cuerpo, _ = _pedir(url, "/v1/primer-arranque")
        assert (
            estado == 200 and cuerpo["sin_cuentas"] is True and cuerpo["archivo_presente"] is True
        )

        estado, _, _ = _pedir(  # sin Origin: 403, aunque el código sea el bueno
            url,
            "/v1/primer-arranque/reclamo",
            {"codigo": escrito, "usuario": "dueno", "nombre": "Dueña Demo", "contrasena": CLAVE},
        )
        assert estado == 403

        estado, cuerpo, cabeceras = _pedir(
            url,
            "/v1/primer-arranque/reclamo",
            {"codigo": escrito, "usuario": "dueno", "nombre": "Dueña Demo", "contrasena": CLAVE},
            origen=url,
        )
        assert estado == 201, cuerpo
        assert cuerpo["roles"] == ["administrador"] and "silice_sesion=" in cabeceras["set-cookie"]
        assert not archivo.exists()  # el código se borra al usarse

        estado, cuerpo, _ = _pedir(url, "/v1/primer-arranque")
        assert (
            estado == 200 and cuerpo["sin_cuentas"] is False and cuerpo["archivo_presente"] is False
        )

        estado, _, _ = _pedir(  # ya usado: el mismo 401 de siempre
            url,
            "/v1/primer-arranque/reclamo",
            {"codigo": escrito, "usuario": "otro", "nombre": "Otro", "contrasena": CLAVE},
            origen=url,
        )
        assert estado == 401
    finally:
        proceso.terminate()
        try:
            salida, _ = proceso.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proceso.kill()
            salida, _ = proceso.communicate(timeout=30)
    for secreto in (codigo, escrito, CLAVE):
        assert secreto not in salida, "el servidor imprimió un secreto"
    assert "Traceback" not in salida
