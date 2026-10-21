"""Arranque y parada de Sílice (RF-98; spec S5 §5.4, §8.1 y §10.1).

`python -m operacion arrancar` prepara las bases, elige la dirección (siempre el bucle local salvo
la IP explícita de la red local), lanza **un solo proceso** hijo (Uvicorn, `api.main:app`, que sirve
la API y la interfaz de React en `/app/`, todo en un solo puerto), espera `GET /salud` y abre el
navegador en `/app/`. Cerrar la ventana detiene todo; `parar` lo hace desde otro proceso. Nunca
importa FastAPI: solo lo lanza.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from operacion import base_datos, config, red, registro

LOOPBACK = "127.0.0.1"
BANDERAS_PYTHON = ("-E", "-s", "-B", "-X", "utf8")
PLAZO_SALUD_S = 60
DIRECCIONES_PROHIBIDAS = frozenset({"", "0.0.0.0", "::"})
RUTA_INTERFAZ = "/app/"
RUTA_SALUD = "/salud"


def elegir_direccion(
    ajustes: config.Ajustes, ips_locales: Iterable[str]
) -> tuple[str, tuple[str, ...]]:
    """`127.0.0.1`, o la IP guardada si la red local está encendida y esa IP sigue existiendo."""
    if not ajustes.red_local or ajustes.direccion in DIRECCIONES_PROHIBIDAS:
        return LOOPBACK, ()
    if ajustes.direccion in set(ips_locales):
        return ajustes.direccion, ()
    return LOOPBACK, (
        f"La IP {ajustes.direccion} de la red local ya no existe en este equipo (la red cambió): "
        f"Sílice arranca solo en {LOOPBACK}. Vuelva a activar la red local para elegir otra IP.",
    )


def orden_uvicorn(python: Path, direccion: str, puerto: int) -> list[str]:
    return [
        str(python),
        *BANDERAS_PYTHON,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        direccion,
        "--port",
        str(puerto),
        "--no-access-log",
    ]


def variables_de_similitud(raiz: Path | None = None) -> dict[str, str]:
    """El módulo de similitud (si está instalado) trae su caché del modelo: sin red, nunca."""
    modelo = (raiz or config.RAIZ).parent / "modulos" / "similitud" / "hf"
    variables = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    if modelo.is_dir():
        variables["HF_HOME"] = str(modelo)
    return variables


def entorno_hijos(
    ajustes: config.Ajustes,
    direccion: str,
    entorno: Mapping[str, str] | None = None,
    *,
    base: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """El entorno de Uvicorn: ninguna escritura cae en la carpeta del programa y nada del entorno
    del usuario (`PYTHON*`, `VIRTUAL_ENV`) cambia su comportamiento."""
    origen = os.environ if base is None else base
    env = {
        k: v
        for k, v in origen.items()
        if not k.upper().startswith("PYTHON") and k.upper() != "VIRTUAL_ENV"
    }
    caso = config.ruta_caso_por_defecto(entorno)
    env.update(
        {
            "SILICE_DATOS": str(config.carpeta_datos(entorno)),
            "SILICE_INSTALACION": str(config.ruta_instalacion(entorno)),
            "SILICE_RESPALDOS": str(config.carpeta_respaldos(entorno)),
            "SILICE_USUARIO": str(config.carpeta_usuario(entorno)),
            "SILICE_CASO": str(caso),
            "APU_BASE": f"sqlite:///{caso.as_posix()}",
            "SILICE_DIRECCION": direccion,
            "SILICE_PRODUCTO": "1" if config.es_producto() else "0",
            **variables_de_similitud(),
        }
    )
    if config.es_producto():
        # SEG-1 (auditoria 2026-10-13): en el producto el acceso con cuentas siempre esta encendido.
        env["SILICE_ACCESO"] = "1"
    env.pop("SILICE_MODO_ENTREGA", None)
    if not ajustes.mostrar_investigacion:
        env["SILICE_MODO_ENTREGA"] = "1"
    return env


@dataclass(frozen=True, slots=True)
class EstadoServidor:
    pids: tuple[int, ...]
    direccion: str
    puerto: int
    inicio: str


def leer_estado(entorno: Mapping[str, str] | None = None) -> EstadoServidor | None:
    try:
        datos = json.loads(config.ruta_estado(entorno).read_text(encoding="utf-8"))
        return EstadoServidor(
            tuple(int(p) for p in datos["pids"]),
            str(datos["direccion"]),
            int(datos["puerto"]),
            str(datos["inicio"]),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None


def escribir_estado(estado: EstadoServidor, entorno: Mapping[str, str] | None = None) -> None:
    ruta = config.ruta_estado(entorno)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(asdict(estado), indent=2), encoding="utf-8")


def borrar_estado(entorno: Mapping[str, str] | None = None) -> None:
    config.ruta_estado(entorno).unlink(missing_ok=True)


def _url(direccion: str, puerto: int) -> str:
    return f"http://{direccion}:{puerto}"


def _sonda(url: str) -> bool:
    """`GET /salud` de Sílice: 200 y `{"estado": "ok"}` (otro programa en ese puerto no pasa)."""
    try:
        with urllib.request.urlopen(url + RUTA_SALUD, timeout=2) as respuesta:  # noqa: S310
            if respuesta.status != 200:
                return False
            cuerpo = json.loads(respuesta.read(1024).decode("utf-8", errors="replace"))
            return isinstance(cuerpo, dict) and cuerpo.get("estado") == "ok"
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return False


def _puerto_libre(direccion: str, puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as zocalo:
        try:
            zocalo.bind((direccion, puerto))
        except OSError:
            return False
    return True


def _lanzar(orden: list[str], entorno: dict[str, str], cwd: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(  # noqa: S603
        orden,
        cwd=cwd,
        env=entorno,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _matar(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def hay_instancia(
    entorno: Mapping[str, str] | None = None, *, sonda: Callable[[str], bool] = _sonda
) -> bool:
    estado = leer_estado(entorno)
    return estado is not None and sonda(_url(estado.direccion, estado.puerto))


def _terminar(procesos: Iterable[Any]) -> None:
    for proceso in procesos:
        if proceso.poll() is None:
            proceso.terminate()
    for proceso in procesos:
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()


def arrancar(
    entorno: Mapping[str, str] | None = None,
    *,
    sin_navegador: bool = False,
    lanzar: Callable[..., Any] = _lanzar,
    sonda: Callable[[str], bool] = _sonda,
    abrir: Callable[[str], Any] = webbrowser.open,
    ips: Callable[[], list[str]] = red.ips_del_equipo,
    tuneles: Callable[[], list[str]] = red.tuneles_en_ejecucion,
    puerto_libre: Callable[[str, int], bool] = _puerto_libre,
    dormir: Callable[[float], None] = time.sleep,
    reloj: Callable[[], float] = time.monotonic,
    salida: Callable[[str], Any] = print,
) -> int:
    estado = leer_estado(entorno)
    if estado is not None:
        url = _url(estado.direccion, estado.puerto)
        if sonda(url):
            salida(f"Sílice ya está en marcha: {url}{RUTA_INTERFAZ}")
            if not sin_navegador:
                abrir(url + RUTA_INTERFAZ)
            return 0
        borrar_estado(entorno)  # un registro viejo de una instancia que ya no existe
    ruta_ajustes = config.ruta_ajustes(entorno)
    if not ruta_ajustes.exists():
        config.guardar_ajustes(ruta_ajustes, config.Ajustes())
    ajustes = config.cargar_ajustes(ruta_ajustes)
    logger = registro.configurar(config.carpeta_registros(entorno), ajustes.nivel_registro)
    avisos = list(ajustes.avisos)
    if red.es_ruta_unc(str(config.carpeta_datos(entorno))):
        avisos.append("La carpeta de datos está en una ruta de red (UNC): SQLite no es fiable ahí.")
    if encontrados := tuneles():
        avisos.append(
            f"Hay un túnel en ejecución ({', '.join(encontrados)}): anula el filtro de IP y la "
            "regla «solo desde este equipo». Ciérrelo o publique Sílice por su cuenta y riesgo."
        )
    try:
        base_datos.preparar_base(
            config.ruta_instalacion(entorno), base_datos.Destino.INSTALACION, entorno=entorno
        )
        base_datos.preparar_base(config.ruta_caso_por_defecto(entorno), entorno=entorno)
    except base_datos.ErrorDeBase as error:
        logger.error("no se pudieron preparar las bases: %s", error)
        salida(f"Sílice no arrancó: {error}")
        return 1
    codigo = config.ruta_codigo_instalacion(entorno)
    if codigo.is_file():
        texto = codigo.read_text(encoding="utf-8").strip()
        registro.registrar_secreto(texto)  # a la consola, nunca al registro
        salida(f"Código de instalación (un solo uso, para crear el primer administrador): {texto}")
    direccion, de_direccion = elegir_direccion(ajustes, ips())
    avisos.extend(de_direccion)
    for aviso in avisos:
        logger.warning("%s", aviso)
        salida(f"AVISO: {aviso}")
    if not puerto_libre(direccion, ajustes.puerto):
        salida(
            f"El puerto {ajustes.puerto} lo usa otro programa. Cierre ese programa "
            f"o cambie el puerto en {ruta_ajustes}."
        )
        return 1
    python = Path(sys.executable)
    env = entorno_hijos(ajustes, direccion, entorno)
    ordenes = [("uvicorn", orden_uvicorn(python, direccion, ajustes.puerto))]
    procesos = []
    for nombre, orden in ordenes:
        proceso = lanzar(orden, env, config.RAIZ)
        procesos.append(proceso)
        threading.Thread(
            target=registro.copiar_salida,
            args=(proceso.stdout, logger, logging.INFO, nombre),
            daemon=True,
        ).start()
    escribir_estado(
        EstadoServidor(
            (os.getpid(), *(p.pid for p in procesos)),
            direccion,
            ajustes.puerto,
            datetime.now().isoformat(timespec="seconds"),
        ),
        entorno,
    )
    url = _url(direccion, ajustes.puerto)
    try:
        limite = reloj() + PLAZO_SALUD_S
        while not sonda(url):
            if reloj() >= limite or any(p.poll() is not None for p in procesos):
                logger.error("Uvicorn no respondió en %s s", PLAZO_SALUD_S)
                salida(
                    f"Sílice no respondió en {PLAZO_SALUD_S} s. Mire el registro en "
                    f"{config.carpeta_registros(entorno)}."
                )
                return 1
            dormir(0.5)
        salida(f"Sílice está en marcha: {url}{RUTA_INTERFAZ}")
        salida("Para detener Sílice, cierre esta ventana.")
        if not sin_navegador:
            abrir(url + RUTA_INTERFAZ)
        while all(p.poll() is None for p in procesos):
            dormir(1)
        logger.error("un proceso de Sílice terminó solo")
        salida("Un proceso de Sílice terminó. Mire el registro y vuelva a abrir Sílice.")
    except KeyboardInterrupt:
        salida("Sílice se detuvo.")
    finally:
        _terminar(procesos)
        borrar_estado(entorno)
    return 0


def parar(
    entorno: Mapping[str, str] | None = None,
    *,
    sonda: Callable[[str], bool] = _sonda,
    matar: Callable[[int], Any] = _matar,
    dormir: Callable[[float], None] = time.sleep,
    salida: Callable[[str], Any] = print,
) -> int:
    """Detiene la instancia de `servidor.json`. Solo mata procesos si la instancia **responde**:
    un registro viejo, con PID que otro programa pudo reutilizar, no autoriza a matar nada."""
    estado = leer_estado(entorno)
    if estado is None:
        salida("Sílice no está en marcha.")
        return 0
    url = _url(estado.direccion, estado.puerto)
    if not sonda(url):
        borrar_estado(entorno)
        salida("Sílice no estaba en marcha (se limpió un registro viejo).")
        return 0
    propio = os.getpid()
    for pid in reversed(estado.pids):  # primero los hijos, el lanzador al final
        if pid != propio:
            matar(pid)
    for _ in range(20):
        if not sonda(url):
            break
        dormir(0.5)
    borrar_estado(entorno)
    salida("Sílice se detuvo.")
    return 0
