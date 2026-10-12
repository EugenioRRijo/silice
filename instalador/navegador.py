"""Navegador sin interfaz de la prueba de humo (spec S5 §11.2 paso 5; solo en la CI).

Carga páginas de Sílice con Edge sin interfaz (Playwright) y anota **toda** petición y todo
websocket: la lista de anfitriones fuera de 127.0.0.1 debe quedar vacía (telemetría de Streamlit y
three.js son del navegador y el proxy no los ve). Sale con 1 si hay alguno.

    uv run --no-project --with playwright python instalador/navegador.py \\
        --url http://127.0.0.1:8501 --salida humo-salida/peticiones.json
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

LOCALES = {"127.0.0.1", "localhost", "::1"}
ESQUEMAS_DE_RED = {"http", "https", "ws", "wss", "ftp"}


def externos(urls: Iterable[str]) -> list[str]:
    anfitriones = set()
    for url in urls:
        analizada = urlparse(url)
        if analizada.scheme in ESQUEMAS_DE_RED and analizada.hostname not in LOCALES:
            anfitriones.add(analizada.hostname or url)
    return sorted(anfitriones)


def recorrer(url: str, paginas: list[str]) -> list[str]:
    from playwright.sync_api import sync_playwright

    vistas: list[str] = []
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="msedge", headless=True)
        try:
            pagina = navegador.new_context().new_page()
            pagina.on("request", lambda peticion: vistas.append(peticion.url))
            pagina.on("websocket", lambda ws: vistas.append(ws.url))
            for ruta in paginas:
                pagina.goto(f"{url}/{ruta}", wait_until="networkidle", timeout=60_000)
                pagina.wait_for_timeout(1500)
        finally:
            navegador.close()
    return vistas


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--url", required=True)
    analizador.add_argument("--paginas", nargs="+", default=["", "visor", "similares"])
    analizador.add_argument("--salida", type=Path, required=True)
    argumentos = analizador.parse_args(argv)
    vistas = recorrer(argumentos.url.rstrip("/"), argumentos.paginas)
    fuera = externos(vistas)
    argumentos.salida.write_text(
        json.dumps({"peticiones": len(vistas), "externos": fuera, "urls": vistas}, indent=2),
        encoding="utf-8",
    )
    print(f"{len(vistas)} peticiones; anfitriones fuera del equipo: {fuera or 'ninguno'}")
    return 1 if fuera else 0


if __name__ == "__main__":
    raise SystemExit(main())
