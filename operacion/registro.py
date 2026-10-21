"""Registro de errores sin datos sensibles (RF-98; spec S5 §8.4).

`registros/silice.log`, rotativo (1 MB × 5), con el formato `fecha nivel módulo mensaje`. Nunca se
escriben contraseñas, códigos de instalación, claves de API o de IA, bloques PEM, cuerpos de
petición ni cadenas de consulta; la carpeta del usuario se reescribe como `%USERPROFILE%`. Las
trazas guardan el tipo, el mensaje (también filtrado) y `archivo:línea`, nunca el texto de la
línea ni los valores de las variables. El lanzador pasa por el mismo filtro la salida de Uvicorn
(`copiar_salida`).
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import re
import traceback
from collections.abc import Iterable
from pathlib import Path

NOMBRE_LOGGER = "silice"
MARCA = "[omitido]"

_PATRONES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"-----BEGIN [A-Z0-9 ]+-----.*?(?:-----END [A-Z0-9 ]+-----|\Z)", re.DOTALL), MARCA),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]+"), MARCA),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=\-]+"), "Bearer " + MARCA),
    (re.compile(r"(?i)(x-silice-clave\s*[:=]\s*)\S+"), r"\1" + MARCA),
    (
        re.compile(
            r"(?i)\b(contrase[nñ]a|password|passwd|clave|secreto|token"
            r"|codigo(?:_de)?_instalaci[oó]n)(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|\S+)"
        ),
        r"\1\2" + MARCA,
    ),
    (re.compile(r"(https?://[^\s?\"']+)\?[^\s\"'<>]+"), r"\1?" + MARCA),
)
_SECRETOS_CONOCIDOS: set[str] = set()


def registrar_secreto(valor: str) -> None:
    """Un valor concreto (el código de instalación) que no debe aparecer jamás en el archivo."""
    if len(valor) >= 8:
        _SECRETOS_CONOCIDOS.add(valor)


def olvidar_secretos() -> None:
    _SECRETOS_CONOCIDOS.clear()


def _perfil() -> str:
    return os.environ.get("USERPROFILE") or str(Path.home())


def limpiar(texto: str, perfil: str | None = None) -> str:
    for valor in _SECRETOS_CONOCIDOS:
        texto = texto.replace(valor, MARCA)
    for patron, sustituto in _PATRONES:
        texto = patron.sub(sustituto, texto)
    base = _perfil() if perfil is None else perfil
    if base:
        for variante in {base, base.replace("\\", "/")}:
            texto = re.sub(re.escape(variante), lambda _: "%USERPROFILE%", texto, flags=re.I)
    return texto


class FormatoSeguro(logging.Formatter):
    """`fecha nivel módulo mensaje`, con el mensaje y la excepción pasados por `limpiar`."""

    def __init__(self) -> None:
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        texto = (
            f"{self.formatTime(record, self.datefmt)} {record.levelname} {record.name} "
            f"{limpiar(record.getMessage())}"
        )
        if record.exc_info and record.exc_info[1] is not None:
            tipo, valor, cola = record.exc_info
            lineas = [f"{tipo.__name__}: {limpiar(str(valor))}"]
            for marco in traceback.extract_tb(cola):
                lineas.append(f"  en {limpiar(marco.filename)}:{marco.lineno} ({marco.name})")
            texto += "\n" + "\n".join(lineas)
        return texto


def configurar(
    carpeta: Path, nivel: str = "INFO", *, max_bytes: int = 1_000_000, copias: int = 5
) -> logging.Logger:
    if nivel.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise ValueError(f"nivel de registro desconocido: {nivel!r}")
    carpeta.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(NOMBRE_LOGGER)
    for manejador in list(logger.handlers):
        logger.removeHandler(manejador)
        manejador.close()
    manejador = logging.handlers.RotatingFileHandler(
        carpeta / "silice.log", maxBytes=max_bytes, backupCount=copias, encoding="utf-8"
    )
    manejador.setFormatter(FormatoSeguro())
    logger.addHandler(manejador)
    logger.setLevel(nivel.upper())
    logger.propagate = False
    return logger


def copiar_salida(
    flujo: Iterable[str], logger: logging.Logger, nivel: int = logging.ERROR, origen: str = ""
) -> int:
    """Pasa por el filtro cada línea de la salida de un proceso hijo. Un bloque PEM repartido en
    varias líneas se descarta entero. Devuelve cuántas líneas leyó."""
    leidas = 0
    dentro_de_pem = False
    for linea in flujo:
        leidas += 1
        texto = linea.rstrip("\r\n")
        if dentro_de_pem:
            dentro_de_pem = "-----END" not in texto
            continue
        if "-----BEGIN" in texto and "-----END" not in texto:
            dentro_de_pem = True
            texto = texto[: texto.index("-----BEGIN")] + "-----BEGIN " + MARCA
        if texto.strip():
            logger.log(nivel, "%s %s", origen, texto)
    return leidas
