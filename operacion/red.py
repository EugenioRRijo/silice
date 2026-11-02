"""Red local de Sílice: interfaces, cortafuegos y quién es «el propio equipo» (RF-98; spec S5 §8.2).

Apagada por defecto. Al activarla, Uvicorn (la API y la interfaz) escucha en la IP **explícita** de
la interfaz elegida (nunca en todas) y el cortafuegos de Windows solo deja entrar a esa IP, a la
subred local y al perfil Privado. Sin TLS: el aviso lo dice. Solo IPv4 en la 1.0.0.
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from operacion import config

AVISO_SIN_CIFRAR = (
    "Sílice quedará visible para los equipos de esta red. Las contraseñas viajan sin cifrar "
    "(sin TLS): úselo solo en una red de confianza."
)
AVISO_ACCESO = "Esta conexión no está cifrada. Use Sílice solo en una red de confianza."
PREFIJO_REGLA = "Silice red local"
TUNELES_CONOCIDOS = ("cloudflared", "ngrok", "frpc")
_CONSULTA = (
    "Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias,IPAddress "
    "| ConvertTo-Json -Compress"
)


@dataclass(frozen=True, slots=True, order=True)
class Interfaz:
    nombre: str
    ip: str


def _powershell(comando: str) -> str:
    resultado = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", comando],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    return resultado.stdout


def _es_privada(texto: str) -> bool:
    try:
        ip = ipaddress.ip_address(texto)
    except ValueError:
        return False
    return ip.version == 4 and ip.is_private and not (ip.is_loopback or ip.is_link_local)


def ips_del_equipo() -> list[str]:
    """Todas las IPv4 que el equipo tiene hoy (para saber si la IP guardada sigue existiendo)."""
    try:
        bruto = _powershell(_CONSULTA)
        crudo = json.loads(bruto) if bruto.strip() else []
        crudo = [crudo] if isinstance(crudo, dict) else crudo
        ips = [str(fila["IPAddress"]) for fila in crudo]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        ips = []
    if not ips:
        ips = _ips_por_nombre_de_equipo()
    return sorted({*ips, "127.0.0.1"})


def _ips_por_nombre_de_equipo() -> list[str]:
    try:
        filas = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    return sorted({str(fila[4][0]) for fila in filas})


def interfaces_privadas(ejecutor: Callable[[str], str] = _powershell) -> list[Interfaz]:
    """Las interfaces IPv4 con dirección privada (sin bucle local ni enlace local), por nombre."""
    try:
        bruto = ejecutor(_CONSULTA)
        crudo = json.loads(bruto) if bruto.strip() else []
        crudo = [crudo] if isinstance(crudo, dict) else crudo
        halladas = [Interfaz(str(f["InterfaceAlias"]), str(f["IPAddress"])) for f in crudo]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        halladas = [Interfaz("(sin nombre)", ip) for ip in _ips_por_nombre_de_equipo()]
    return sorted(i for i in halladas if _es_privada(i.ip))


def _ip(texto: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    if not texto:
        return None
    try:
        ip = ipaddress.ip_address(texto)
    except ValueError:
        return None
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def es_cliente_local(ip_cliente: str | None, direccion: str = "") -> bool:
    """«Es el propio equipo»: bucle local o la IP de la interfaz elegida, que solo tiene el
    servidor (RV-15). Una IP ilegible o ausente se trata como remota."""
    ip = _ip(ip_cliente)
    if ip is None:
        return False
    if ip.is_loopback:
        return True
    propia = _ip(direccion)
    return propia is not None and propia.is_private and not propia.is_unspecified and ip == propia


def _nombre_regla(puerto: int) -> str:
    return f"{PREFIJO_REGLA} TCP {puerto}"


def ordenes_activar(programa: Path, ip: str, puertos: Sequence[int]) -> list[list[str]]:
    return [
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={_nombre_regla(p)}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={p}",
            f"localip={ip}",
            "remoteip=localsubnet",
            "profile=private",
            f"program={programa}",
            "enable=yes",
        ]
        for p in sorted(set(puertos))
    ]


def ordenes_desactivar() -> list[list[str]]:
    comando = (
        f"Get-NetFirewallRule -DisplayName '{PREFIJO_REGLA}*' -ErrorAction SilentlyContinue "
        "| Remove-NetFirewallRule"
    )
    return [["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", comando]]


def es_administrador() -> bool:
    if os.name != "nt":
        return os.geteuid() == 0  # type: ignore[attr-defined]
    import ctypes

    return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]


def relanzar_elevado(argumentos: Sequence[str]) -> bool:
    """Pide a Windows (UAC) abrir `python -m operacion <argumentos>` con permisos de
    administrador en una ventana nueva. `True` si el usuario aceptó."""
    import ctypes

    parametros = subprocess.list2cmdline(
        ["-E", "-s", "-B", "-X", "utf8", "-m", "operacion", *argumentos]
    )
    codigo = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
        None, "runas", sys.executable, parametros, str(config.RAIZ), 1
    )
    return int(codigo) > 32


def _ejecutar(orden: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        orden,
        capture_output=True,
        text=True,
        encoding="oem" if os.name == "nt" else "utf-8",
        errors="replace",
        check=False,
    )


@dataclass(frozen=True, slots=True)
class ResultadoRed:
    ok: bool
    mensaje: str


_SIN_PERMISOS = (
    "Cambiar la red local necesita permisos de administrador de Windows. No se cambió nada: use "
    "el acceso «Sílice: red local (administrador)» y acepte el aviso."
)


def activar(
    ip: str,
    *,
    programa: Path,
    puertos: Sequence[int],
    ruta_ajustes: Path,
    interfaces: Sequence[Interfaz],
    ejecutor: Callable[[list[str]], subprocess.CompletedProcess[str]] = _ejecutar,
    es_admin: Callable[[], bool] = es_administrador,
) -> ResultadoRed:
    if ip not in {i.ip for i in interfaces}:
        return ResultadoRed(
            False, f"La IP {ip} no pertenece a ninguna interfaz privada del equipo."
        )
    if not es_admin():
        return ResultadoRed(False, _SIN_PERMISOS)
    for orden in ordenes_activar(programa, ip, puertos):
        resultado = ejecutor(orden)
        if resultado.returncode != 0:
            for deshacer in ordenes_desactivar():
                ejecutor(deshacer)
            detalle = (resultado.stderr or resultado.stdout or "").strip()
            return ResultadoRed(
                False, f"El cortafuegos rechazó la regla ({detalle}). No se activó."
            )
    actuales = config.cargar_ajustes(ruta_ajustes)
    config.guardar_ajustes(ruta_ajustes, replace(actuales, red_local=True, direccion=ip, avisos=()))
    return ResultadoRed(
        True,
        f"{AVISO_SIN_CIFRAR} Reinicie Sílice. Los otros equipos abren "
        f"http://{ip}:{actuales.puerto}. "
        "La red debe estar marcada como Privada en Windows.",
    )


def desactivar(
    *,
    ruta_ajustes: Path,
    ejecutor: Callable[[list[str]], subprocess.CompletedProcess[str]] = _ejecutar,
    es_admin: Callable[[], bool] = es_administrador,
) -> ResultadoRed:
    if not es_admin():
        return ResultadoRed(False, _SIN_PERMISOS)
    for orden in ordenes_desactivar():
        ejecutor(orden)
    actuales = config.cargar_ajustes(ruta_ajustes)
    config.guardar_ajustes(
        ruta_ajustes, replace(actuales, red_local=False, direccion="", avisos=())
    )
    return ResultadoRed(True, "Red local apagada: Sílice escucha solo en este equipo. Reinícielo.")


def procesos_en_ejecucion() -> list[str]:
    orden = ["tasklist", "/FO", "CSV", "/NH"] if os.name == "nt" else ["ps", "-e", "-o", "comm="]
    try:
        salida = subprocess.run(
            orden, capture_output=True, text=True, errors="replace", check=False
        )
    except OSError:
        return []
    if os.name != "nt":
        return [Path(linea.strip()).name for linea in salida.stdout.splitlines() if linea.strip()]
    return [linea.split('","')[0].strip('"') for linea in salida.stdout.splitlines() if linea]


def tuneles_en_ejecucion(
    listar: Callable[[], list[str]] = procesos_en_ejecucion,
) -> list[str]:
    """Los túneles locales conocidos que están corriendo: anulan el filtro de IP (spec S5 §8.2)."""
    nombres = {Path(p).stem.lower() for p in listar()}
    return [t for t in TUNELES_CONOCIDOS if t in nombres]


def es_ruta_unc(ruta: str) -> bool:
    texto = ruta.replace("/", "\\")
    if texto.startswith("\\\\?\\"):
        return texto[4:].upper().startswith("UNC\\")
    return texto.startswith("\\\\")
