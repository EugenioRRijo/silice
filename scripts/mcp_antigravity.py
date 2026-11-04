"""Servidor MCP que le da a Claude Code una herramienta para encargarle trabajo a Antigravity.

Antigravity solo consume servidores MCP; no expone uno propio. Este puente envuelve su CLI
(`agy -p`) para que el orquestador lo llame como herramienta (`mcp__antigravity__...`). Siempre en
`--sandbox` y en solo lectura: Antigravity es el auditor independiente (`AGENTS.md`).

Dos cosas que se aprendieron a mano el 2026-11-04 y vigilan las pruebas:
- sin `stdin` cerrado, `agy -p` espera la entrada y no responde nunca;
- el encargo empieza por las reglas del repositorio, para que no lea planes viejos.

Arranque (lo hace Claude Code desde `.mcp.json`; el paquete `mcp` no es dependencia del producto):
`uv run --no-project --with "mcp>=1.2,<2" python scripts/mcp_antigravity.py`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
AGY = shutil.which("agy") or "agy"
MINUTOS_MAXIMOS = 30

_REGLAS = (
    "Lee AGENTS.md y docs/ESTADO.md antes de nada y activa las skills metodologia-silice, "
    "arbitro-independiente y colaboracion-con-claude. Trabajas en solo lectura: no edites "
    "archivos, no hagas commits ni cambies de rama. Cita archivo:linea del arbol actual y di que "
    "comandos corriste.\n\nEncargo de Claude (orquestador):\n"
)

Correr = Callable[..., subprocess.CompletedProcess[bytes]]


def armar_encargo(pedido: str) -> str:
    """El texto que recibe Antigravity: las reglas del repositorio y despues el pedido entero."""
    if not pedido.strip():
        raise ValueError("el encargo esta vacio")
    return _REGLAS + pedido.strip()


def armar_comando(encargo: str, *, continuar: bool, minutos: int) -> list[str]:
    if not 1 <= minutos <= MINUTOS_MAXIMOS:
        raise ValueError(f"minutos debe estar entre 1 y {MINUTOS_MAXIMOS}")
    comando = [AGY, "-p", encargo, "--sandbox", "--print-timeout", f"{minutos}m0s"]
    if continuar:
        comando.append("--continue")
    return comando


def _texto(crudo: bytes | str | None) -> str:
    """Por una tuberia `agy` escribe en cp1252 (la pagina de codigos de Windows), no en UTF-8."""
    if crudo is None:
        return ""
    if isinstance(crudo, str):
        return crudo
    try:
        return crudo.decode("utf-8")
    except UnicodeDecodeError:
        return crudo.decode("cp1252", errors="replace")


def ejecutar(comando: list[str], *, minutos: int, correr: Correr = subprocess.run) -> str:
    """Corre `agy` con stdin cerrado y devuelve su respuesta, o una explicacion si no la hubo."""
    try:
        resultado = correr(
            comando,
            cwd=RAIZ,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=minutos * 60 + 30,
        )
    except subprocess.TimeoutExpired:
        return f"Antigravity no respondio a tiempo ({minutos} min); prueba un encargo mas corto."
    salida = _texto(resultado.stdout).strip()
    if resultado.returncode != 0:
        error = _texto(resultado.stderr).strip()[-1500:]
        return f"agy termino con codigo {resultado.returncode}.\n{salida}\n{error}".strip()
    return salida or "Antigravity no devolvio texto."


def encargar(pedido: str, continuar: bool = False, minutos: int = 10) -> str:
    return ejecutar(
        armar_comando(armar_encargo(pedido), continuar=continuar, minutos=minutos),
        minutos=minutos,
    )


def main() -> None:  # pragma: no cover - lo arranca Claude Code; se prueba a mano
    from mcp.server.fastmcp import FastMCP

    servidor = FastMCP("antigravity")

    @servidor.tool()
    def encargar_a_antigravity(encargo: str, continuar: bool = False, minutos: int = 10) -> str:
        """Encarga a Antigravity (Gemini) una tarea de solo lectura en el repositorio TESIS:
        auditoria, segunda opinion, verificacion de hechos o revision de un diff. Devuelve su
        respuesta literal; verificala antes de actuar. `continuar` retoma su ultima conversacion.
        Nunca incluyas datos de la empresa en el encargo."""
        return encargar(encargo, continuar=continuar, minutos=minutos)

    @servidor.tool()
    def arbitrar_rama(rama: str, base: str = "main", foco: str = "", minutos: int = 15) -> str:
        """Pide a Antigravity un veredicto de arbitro (APROBADO/DEVUELTO, docs/planes/
        MANUAL_ARBITRO.md) sobre `git diff base..rama`, con un foco opcional."""
        pedido = (
            f"Arbitra la rama {rama} contra {base} con la skill arbitro-independiente "
            f"(git log {base}..{rama} y git diff {base}..{rama}; lee con git show, no cambies de "
            f"rama). Devuelve el veredicto en el formato del manual."
        )
        if foco.strip():
            pedido += f" Foco: {foco.strip()}"
        return encargar(pedido, minutos=minutos)

    servidor.run()


if __name__ == "__main__":
    sys.exit(main())
