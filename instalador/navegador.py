"""Navegador sin interfaz de la prueba de humo (spec S5 §11.2 paso 5; solo en la CI).

Carga páginas de la interfaz de Sílice con Edge sin interfaz (Playwright) y anota **toda**
petición y todo websocket: la lista de anfitriones fuera de 127.0.0.1 debe quedar vacía (lo que
el navegador pide por su cuenta, el proxy no lo ve). Sale con 1 si hay alguno. La interfaz es la
de React, que sirve Uvicorn en `/app/` con rutas por almohadilla (`/app/#/precios/catalogo`).

    uv run --no-project --with playwright python instalador/navegador.py \\
        --url http://127.0.0.1:8501/app --salida humo-salida/peticiones.json

En modo ventana (`--cdp`, V4 de la ventana de escritorio) se conecta por CDP al WebView2 de la
ventana de Sílice ya abierta (sin cerrarla: solo se desconecta), recorre las mismas páginas y, con
`--codigo`, reclama el primer administrador y baja un respaldo con `fetch` dentro de la ventana
(misma cookie, misma CSP). El diálogo «Guardar como» de pywebview no se toca: queda para la prueba
en el equipo (V5). Sale con 1 si hay externos o si la descarga no es un zip adjunto.

    uv run --no-project --with playwright python instalador/navegador.py \\
        --url http://127.0.0.1:8501/app --cdp http://127.0.0.1:9333 \\
        --codigo datos/codigo_instalacion.txt --salida humo-salida/ventana-peticiones.json
"""

from __future__ import annotations

import argparse
import json
import secrets
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

LOCALES = {"127.0.0.1", "localhost", "::1"}
ESQUEMAS_DE_RED = {"http", "https", "ws", "wss", "ftp"}
PLAZO_VENTANA_S = 60.0

#: Corre dentro de la ventana: reclama el primer administrador con el código de instalación, crea
#: un respaldo y lo baja. Devuelve solo estados y cabeceras (nunca el código ni la contraseña); si
#: un paso no es 2xx devuelve lo que tenga, con el resto en `null`, y nunca lanza.
GUION_DESCARGA = """\
async ({codigo, usuario, nombre, contrasena}) => {
  const res = {
    reclamo: null,
    respaldo: null,
    bajada: null,
    tipo: null,
    disposicion: null,
    bytes: null,
    firma: null,
  };
  try {
    const r1 = await fetch("/v1/primer-arranque/reclamo", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({codigo, usuario, nombre, contrasena, tambien_arma: false}),
    });
    res.reclamo = r1.status;
    if (!r1.ok) return res;
    const sesion = await r1.json();
    const r2 = await fetch("/v1/admin/instalacion/respaldos", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json", "X-Silice-CSRF": sesion.csrf},
      body: "{}",
    });
    res.respaldo = r2.status;
    if (!r2.ok) return res;
    const creado = await r2.json();
    const r3 = await fetch(
      `/v1/admin/instalacion/respaldos/${encodeURIComponent(creado.nombre)}`,
      {credentials: "same-origin"},
    );
    res.bajada = r3.status;
    if (!r3.ok) return res;
    res.tipo = r3.headers.get("content-type");
    res.disposicion = r3.headers.get("content-disposition");
    const buf = await r3.arrayBuffer();
    res.bytes = buf.byteLength;
    res.firma = String.fromCharCode(...new Uint8Array(buf.slice(0, 2)));
    return res;
  } catch {
    return res;
  }
}"""


def externos(urls: Iterable[str]) -> list[str]:
    anfitriones = set()
    for url in urls:
        analizada = urlparse(url)
        if analizada.scheme in ESQUEMAS_DE_RED and analizada.hostname not in LOCALES:
            anfitriones.add(analizada.hostname or url)
    return sorted(anfitriones)


def descarga_valida(resultado: dict[str, Any]) -> bool:
    """Reclamo 201, respaldo 200 y una bajada 200 que es un zip adjunto y no vacío."""
    tipo = resultado.get("tipo")
    disposicion = resultado.get("disposicion")
    tamano = resultado.get("bytes")
    return (
        resultado.get("reclamo") == 201
        and resultado.get("respaldo") == 200
        and resultado.get("bajada") == 200
        and isinstance(tipo, str)
        and tipo.startswith("application/zip")
        and isinstance(disposicion, str)
        and disposicion.startswith("attachment")
        and isinstance(tamano, int)
        and not isinstance(tamano, bool)
        and tamano > 0
        and resultado.get("firma") == "PK"
    )


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


def recorrer_ventana(
    cdp: str,
    url: str,
    paginas: list[str],
    codigo: str | None,
    *,
    abrir_playwright: Callable[[], Any] | None = None,
) -> tuple[list[str], dict[str, Any] | None]:
    """Recorre la ventana ya abierta por CDP; con `codigo`, corre `GUION_DESCARGA` en ella.

    No cierra el navegador: es la ventana de Sílice, que la prueba de humo cierra después como lo
    haría el usuario (`WM_CLOSE`). Al salir del gestor de Playwright solo se desconecta."""
    if abrir_playwright is None:
        from playwright.sync_api import sync_playwright

        abrir_playwright = sync_playwright

    vistas: list[str] = []
    resultado: dict[str, Any] | None = None
    base = url.rstrip("/")
    with abrir_playwright() as p:
        navegador = p.chromium.connect_over_cdp(cdp, timeout=60_000)
        pagina = None
        limite = time.monotonic() + PLAZO_VENTANA_S
        while pagina is None:
            if navegador.contexts:
                pagina = next(
                    (pg for pg in navegador.contexts[0].pages if pg.url.startswith(base)), None
                )
            if pagina is not None:
                break
            if time.monotonic() >= limite:
                raise TimeoutError(f"La ventana no abrió {base} en {PLAZO_VENTANA_S:.0f} s")
            time.sleep(0.5)
        pagina.on("request", lambda peticion: vistas.append(peticion.url))
        pagina.on("websocket", lambda ws: vistas.append(ws.url))
        for ruta in paginas:
            pagina.goto(f"{base}/{ruta}", wait_until="networkidle", timeout=60_000)
            pagina.wait_for_timeout(1500)
        if codigo is not None:
            resultado = pagina.evaluate(
                GUION_DESCARGA,
                {
                    "codigo": codigo,
                    "usuario": "humo.ventana",
                    "nombre": "Prueba de humo",
                    "contrasena": secrets.token_urlsafe(24),
                },
            )
    return vistas, resultado


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--url", required=True)
    analizador.add_argument(
        "--paginas", nargs="+", default=["", "#/precios/catalogo", "#/precios/simulador"]
    )
    analizador.add_argument("--salida", type=Path, required=True)
    analizador.add_argument("--cdp", help="modo ventana: dirección CDP del WebView2 de Sílice")
    analizador.add_argument("--codigo", type=Path, help="modo ventana: codigo_instalacion.txt")
    argumentos = analizador.parse_args(argv)
    url = argumentos.url.rstrip("/")
    resultado: dict[str, Any] | None = None
    codigo: str | None = None
    if argumentos.cdp:
        if argumentos.codigo is not None:
            codigo = argumentos.codigo.read_text(encoding="utf-8").strip()
        vistas, resultado = recorrer_ventana(argumentos.cdp, url, argumentos.paginas, codigo)
    else:
        vistas = recorrer(url, argumentos.paginas)
    fuera = externos(vistas)
    informe: dict[str, Any] = {"peticiones": len(vistas), "externos": fuera, "urls": vistas}
    if argumentos.cdp:
        informe["descarga"] = resultado
    argumentos.salida.write_text(json.dumps(informe, indent=2), encoding="utf-8")
    print(f"{len(vistas)} peticiones; anfitriones fuera del equipo: {fuera or 'ninguno'}")
    if argumentos.cdp:
        print(f"descarga en la ventana: {resultado}")
    descarga_mal = codigo is not None and (resultado is None or not descarga_valida(resultado))
    return 1 if (fuera or descarga_mal) else 0


if __name__ == "__main__":
    raise SystemExit(main())
