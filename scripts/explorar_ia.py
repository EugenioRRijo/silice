"""Prueba exploratoria de S4.0 (spec S4 §8.3, §8.6): `keyring` y el modelo local de Ollama.

No llama a ninguna API de pago. Imprime un informe en Markdown para pegarlo en
`docs/fuentes/asistente_verificacion.md` con la fecha y el equipo. Lo que NO se pueda comprobar se
dice como «no comprobado»: ninguna capacidad se afirma sin probarla.

    uv run python scripts/explorar_ia.py keyring
    uv run python scripts/explorar_ia.py ollama --modelo <nombre>
        [--anfitrion http://127.0.0.1:11434]
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

SERVICIO_DE_PRUEBA = "silice-ia-exploracion"
HERRAMIENTA = {
    "type": "function",
    "function": {
        "name": "saludar",
        "description": "Saluda a una persona por su nombre.",
        "parameters": {
            "type": "object",
            "properties": {"nombre": {"type": "string"}},
            "required": ["nombre"],
            "additionalProperties": False,
        },
    },
}
ESQUEMA_JSON = {
    "type": "object",
    "properties": {"herramienta": {"type": "string"}, "argumentos": {"type": "object"}},
    "required": ["herramienta", "argumentos"],
}


def informe_de_keyring(almacen: Any) -> dict[str, Any]:
    """Ida y vuelta de una clave de prueba en el almacen del sistema (y su borrado)."""
    informe: dict[str, Any] = {"backend": type(almacen.get_keyring()).__name__}
    try:
        almacen.set_password(SERVICIO_DE_PRUEBA, "prueba", "clave-de-prueba")
        informe["ida_y_vuelta"] = almacen.get_password(SERVICIO_DE_PRUEBA, "prueba") == (
            "clave-de-prueba"
        )
        almacen.delete_password(SERVICIO_DE_PRUEBA, "prueba")
        informe["borrado"] = almacen.get_password(SERVICIO_DE_PRUEBA, "prueba") is None
    except Exception as error:  # noqa: BLE001 - se informa, no se oculta
        informe["error"] = type(error).__name__
    return informe


def informe_de_ollama(cliente: Any, modelo: str, version: str, reloj: Callable[[], float]) -> dict:
    """Llamadas a herramientas, salida restringida a un esquema, tiempo y tamano por turno."""
    informe: dict[str, Any] = {"modelo": modelo, "version": version}
    pregunta = [{"role": "user", "content": "Saluda a Ana usando la herramienta saludar."}]
    inicio = reloj()
    try:
        respuesta = cliente.chat(model=modelo, messages=pregunta, tools=[HERRAMIENTA])
        llamadas = respuesta.message.tool_calls or []
        informe["herramientas"] = bool(llamadas) and llamadas[0].function.name == "saludar"
        informe["segundos_por_turno"] = round(reloj() - inicio, 2)
        informe["fichas_de_salida"] = getattr(respuesta, "eval_count", None)
    except Exception as error:  # noqa: BLE001
        informe["herramientas"] = f"no comprobado ({type(error).__name__})"
    try:
        respuesta = cliente.chat(
            model=modelo,
            messages=[{"role": "user", "content": "Responde con la herramienta saludar y Ana."}],
            format=ESQUEMA_JSON,
        )
        objeto = json.loads(respuesta.message.content)
        informe["salida_restringida"] = set(objeto) == {"herramienta", "argumentos"}
    except Exception as error:  # noqa: BLE001
        informe["salida_restringida"] = f"no comprobado ({type(error).__name__})"
    return informe


def a_markdown(titulo: str, informe: dict[str, Any]) -> str:
    equipo = f"{platform.system()} {platform.release()}, {platform.machine()}"
    lineas = [f"### {titulo}", "", f"Equipo: {equipo}.", "", "| Dato | Valor |", "|---|---|"]
    lineas += [f"| {clave} | {valor} |" for clave, valor in informe.items()]
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="que", required=True)
    sub.add_parser("keyring")
    ollama = sub.add_parser("ollama")
    ollama.add_argument("--modelo", required=True)
    ollama.add_argument("--anfitrion", default="http://127.0.0.1:11434")
    args = parser.parse_args(argv)
    if args.que == "keyring":
        import keyring

        print(a_markdown("keyring", informe_de_keyring(keyring)))
        return 0
    import ollama as cliente_ollama

    from asistente.proveedores.ollama_local import es_bucle_local

    if not es_bucle_local(args.anfitrion):
        print("El anfitrion no resuelve a bucle local: no se explora (RNF-18 a).", file=sys.stderr)
        return 2
    cliente = cliente_ollama.Client(host=args.anfitrion)
    informe = informe_de_ollama(cliente, args.modelo, _version(args.anfitrion), time.monotonic)
    print(a_markdown("ollama", informe))
    return 0


def _version(anfitrion: str) -> str:
    from urllib.request import urlopen

    with urlopen(f"{anfitrion}/api/version", timeout=5) as respuesta:
        return json.load(respuesta)["version"]


if __name__ == "__main__":
    sys.exit(main())
