"""Recorrido de UX/UI de la interfaz de Sílice con Playwright (repetible tras cada cambio).

Arranca un servidor de Sílice en 127.0.0.1 con una carpeta de datos TEMPORAL sembrada con la
demostración ficticia (cuentas de `tests/fixtures/sesion_web.py` y los casos de `start.py`), entra
con cuentas ficticias y recorre TODAS las rutas de `frontend-desktop/src/shell/rutas.ts` a dos
anchos y como cada rol. Por pantalla anota: captura, número de h1, desplazamiento horizontal,
alto total, errores de consola y de red, tiempo hasta el primer h1 y, si se puede bajar axe-core
de un CDN, la revisión de accesibilidad. Además recorre el flujo de la empresa de hoy (subir un
presupuesto y auditarlo) contando clics, pantallas y decisiones.

    uv run --active --with playwright python scripts/recorrido_ux_playwright.py \\
        --salida <carpeta> [--roles admin ana rita] [--anchos 1366 1056] [--sin-axe] [--sin-flujo]
        [--letras normal,grande,muy-grande] [--rutas inicio libros ...] [--url http://127.0.0.1:8501]

Cada medición se repite con cada tamaño de letra (`--letras`, como lo fija `TamanoLetra`) y
comprueba la navegación de la barra superior: `duplicados_nav` (una pantalla repetida dentro de la
barra o dentro de su capa: debe ser 0), `barra_cortada` (la cabecera se desborda o algo suyo sale
de la ventana o se monta sobre el lado derecho), `panel_fuera` (cada panel de área, o la capa
cuando la barra no cabe, sale de la ventana). Inicio y Libro se repiten con el recorrido guiado
en curso (columna «Recorrido» a la vista) para quien puede auditar. La interfaz se sirve desde una
copia de `frontend-desktop/dist` (una recompilación a mitad de la corrida no la rompe).

Modo `--funcional` (BS-F, «que todas las herramientas funcionen»): en vez de medir, ejecuta la
acción principal de cada pantalla con la cuenta que la puede usar y comprueba el resultado visible.
Las filas viven en `scripts/recorrido_funcional.toml` (una por pantalla) y se recorren navegando por
URL (`#/<id>`), no por el menú:

    uv run --active --with playwright python scripts/recorrido_ux_playwright.py --funcional \\
        --salida <carpeta> [--acciones scripts/recorrido_funcional.toml] [--solo componer,catalogo]

No usa `data/` del árbol ni datos reales; solo libros ficticios (`tests/fixtures/`). Cierra el
servidor por su PID y el navegador que lanzó; nunca cierra Chrome/Edge por nombre.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

RUTAS_TS = RAIZ / "frontend-desktop" / "src" / "shell" / "rutas.ts"
AXE_URL = "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js"
ALTO = 768
ROLES = {"admin": "administra", "ana": "arma", "rita": "revisa"}
LIMITE_CARGA_MS = 20_000
# Los tamaños de letra de `frontend-desktop/src/comun/preferenciaDeLetra.ts` y su clave de
# localStorage.
LETRAS = ("normal", "grande", "muy-grande")
CLAVE_LETRA = "silice.tamano-letra"
# Violaciones axe de la corrida de referencia (bitácora 2026-10-25-recorrido-ux-playwright.md,
# H-10): cualquier otra (ruta, regla) es nueva.
AXE_DE_REFERENCIA = {
    ("administracion", "color-contrast"),
    ("inicio", "scrollable-region-focusable"),
}


def rutas_de_la_interfaz() -> list[dict[str, str | None]]:
    """Las páginas de `rutas.ts` (id, título, acción), leídas del texto: es la única lista."""
    texto = RUTAS_TS.read_text(encoding="utf-8")
    bloque = texto.split("export const PAGINAS", 1)[1].split("export function paginaPorId", 1)[0]
    paginas: list[dict[str, str | None]] = []
    # Cada entrada se lee campo a campo: el orden de los campos (y los que se agreguen, como
    # `enUnaLinea`) no importa.
    for entrada in re.findall(r"\{([^{}]*?\bid:\s*\"[^\"]+\"[^{}]*?)\}", bloque):
        campos = dict(re.findall(r'(\w+):\s*"([^"]*)"', entrada))
        accion = re.search(r"\baccion:\s*(null|\"[^\"]*\")", entrada)
        if "id" not in campos or "titulo" not in campos or accion is None:
            continue
        paginas.append(
            {
                "id": campos["id"],
                "titulo": campos["titulo"],
                "seccion": campos.get("seccion"),
                "accion": None if accion[1] == "null" else accion[1].strip('"'),
            }
        )
    return paginas


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def sembrar_datos(datos: Path) -> dict[str, str]:
    """Carpeta temporal con instalación (admin, ana, rita) y los casos de demostración."""
    os.environ["SILICE_DATOS"] = str(datos)
    os.environ["SILICE_USUARIO"] = str(datos / "usuario")
    os.environ.pop("SILICE_INSTALACION", None)
    datos.mkdir(parents=True, exist_ok=True)
    from start import preparar_demo
    from tests.fixtures.instalacion import CONTRASENA
    from tests.fixtures.sesion_web import NUEVA, plantilla_con_cuentas

    plantilla_con_cuentas(datos)
    preparar_demo()
    return {"admin": CONTRASENA, "ana": NUEVA, "rita": NUEVA}


class Servidor:
    def __init__(self, datos: Path, puerto: int) -> None:
        entorno = dict(os.environ)
        entorno["SILICE_DATOS"] = str(datos)
        entorno["SILICE_USUARIO"] = str(datos / "usuario")
        entorno.pop("SILICE_INSTALACION", None)
        self.puerto = puerto
        self.proceso = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(puerto),
                "--no-access-log",
            ],
            cwd=RAIZ,
            env=entorno,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.url = f"http://127.0.0.1:{puerto}"

    def esperar(self, segundos: float = 90) -> None:
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            if self.proceso.poll() is not None:
                raise RuntimeError("el servidor salió al arrancar")
            with contextlib.suppress(OSError):
                with urllib.request.urlopen(f"{self.url}/salud", timeout=1) as r:
                    if r.status == 200:
                        return
            time.sleep(0.5)
        raise RuntimeError("el servidor no respondió a tiempo")

    def cerrar(self) -> None:
        """Por su PID (nunca por nombre de programa)."""
        if self.proceso.poll() is None:
            self.proceso.terminate()
            try:
                self.proceso.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proceso.kill()


def lanzar_navegador(p: Any) -> Any:
    """Chromium de Playwright; si la versión pedida no está, cualquiera de ms-playwright."""
    try:
        return p.chromium.launch(headless=True)
    except Exception:
        base = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
        candidatos = sorted(base.glob("chromium-*/chrome-win*/chrome.exe"), reverse=True)
        if not candidatos:
            raise
        return p.chromium.launch(headless=True, executable_path=str(candidatos[0]))


def bajar_axe(carpeta: Path) -> str | None:
    destino = carpeta / "axe.min.js"
    try:
        if not destino.exists():
            with urllib.request.urlopen(AXE_URL, timeout=20) as r:
                destino.write_bytes(r.read())
        return destino.read_text(encoding="utf-8")
    except Exception as error:
        print(f"axe-core no disponible ({error}); se omite la revisión de accesibilidad")
        return None


def entrar(pagina: Any, base: str, login: str, contrasena: str) -> None:
    pagina.goto(f"{base}/app/", wait_until="load")
    pagina.wait_for_selector("#entrar-usuario", timeout=30_000)
    pagina.fill("#entrar-usuario", login)
    pagina.fill("#entrar-contrasena", contrasena)
    pagina.click("button[type=submit]")
    pagina.wait_for_selector("#entrar-usuario", state="detached", timeout=30_000)


MEDIR_JS = """() => {
  const de = document.documentElement, ancho = de.clientWidth;
  const fuera = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && r.right > ancho + 1 && fuera.length < 4) {
      let anc = el, oculto = false;
      while ((anc = anc.parentElement)) {
        const o = getComputedStyle(anc).overflowX;
        if (o === 'auto' || o === 'scroll' || o === 'hidden') { oculto = true; break; }
      }
      const cl = typeof el.className === 'string' && el.className
        ? '.' + el.className.split(' ').slice(0, 2).join('.') : '';
      if (!oculto) fuera.push(el.tagName.toLowerCase() + cl);
    }
  }
  const h1 = [...document.querySelectorAll('h1')];
  return {
    h1: h1.length, h1_texto: h1.map(h => h.textContent.trim()).slice(0, 3),
    scroll_x: de.scrollWidth > de.clientWidth,
    scroll_width: de.scrollWidth, client_width: de.clientWidth,
    alto: de.scrollHeight, desbordan: fuera,
    en_menu: [...document.querySelectorAll('nav a, aside a')]
      .map(a => a.getAttribute('href') || ''),
    texto: (document.body.innerText || '').slice(0, 200),
  };
}"""


def ids_del_menu(contexto: Any, base: str) -> set[str]:
    """Las rutas que el menú lateral ofrece a la sesión de este contexto."""
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 1366, "height": ALTO})
    pagina.goto(f"{base}/app/#/inicio", wait_until="domcontentloaded")
    pagina.wait_for_selector("h1", timeout=LIMITE_CARGA_MS)
    pagina.wait_for_timeout(500)
    hrefs = pagina.eval_on_selector_all(
        "nav a, aside a", "els => els.map(a => a.getAttribute('href') || '')"
    )
    pagina.close()
    return {h.split("#/")[-1].strip("/") for h in hrefs if "#/" in h or h.startswith("/")} | {
        h.strip("/") for h in hrefs if h.startswith("/")
    }


# Controles de la barra superior sobre la pantalla ya cargada. Abre cada área con su botón (el mismo
# `onClick` de React que un clic), mide su panel y lo cierra; si la barra no cabe (umbral de cada
# letra), abre la capa y la mide. Las dos listas de nombres (barra y capa) se revisan por separado:
# cada pantalla debe salir una sola vez en cada una, y un área no debe repetir el nombre de su
# única pantalla («Inicio / Inicio»).
NAV_JS = """async () => {
  const cuadros = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  const de = document.documentElement, ancho = de.clientWidth, alto = window.innerHeight;
  const limpio = t => (t || '').replace(/\\s+/g, ' ').trim();
  const caja = r => [r.left, r.top, r.right, r.bottom].map(Math.round);
  const dentro = r => r.left >= -1 && r.top >= -1 && r.right <= ancho + 1 && r.bottom <= alto + 1;
  const visible = el => { const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
  const repetidos = nombres => { const c = {};
    for (const n of nombres) c[n] = (c[n] || 0) + 1;
    return Object.entries(c).filter(([, k]) => k > 1).map(([n, k]) => n + ' x' + k); };
  const header = document.querySelector('header.cds--header');
  const nav = document.querySelector('nav[aria-label="Menú principal"]');
  const capa = document.querySelector('nav[aria-label="Menú principal (capa)"]');
  const s = { letra_aplicada: de.dataset.siliceLetra || null,
    modo_nav: nav && getComputedStyle(nav).display !== 'none'
      && nav.getBoundingClientRect().width > 0 ? 'barra' : 'capa' };
  const motivos = [];
  if (!header) motivos.push('sin cabecera');
  else {
    if (header.scrollWidth > header.clientWidth + 1)
      motivos.push('scrollWidth ' + header.scrollWidth + ' > clientWidth ' + header.clientWidth);
    for (const el of header.querySelectorAll('a, button')) {
      if (!visible(el) || el.closest('.silice-panel-area')) continue;
      const r = el.getBoundingClientRect();
      if (r.right > ancho + 1 || r.left < -1)
        motivos.push(limpio(el.getAttribute('aria-label') || el.textContent).slice(0, 40)
          + ' fuera ' + caja(r));
    }
    const global = header.querySelector('.cds--header__global');
    const items = s.modo_nav === 'barra' ? [...nav.querySelectorAll('.silice-barra__item')] : [];
    if (global && items.length) {
      const hijos = [...global.children].filter(visible);
      const borde = Math.min(...hijos.map(h => h.getBoundingClientRect().left));
      const ultimo = items[items.length - 1].getBoundingClientRect();
      if (ultimo.right > borde + 1) motivos.push('las áreas se montan sobre el lado derecho');
    }
  }
  s.barra_cortada = motivos.length > 0;
  s.barra_motivos = motivos.slice(0, 4);
  const nombresBarra = [], paneles = [];
  if (s.modo_nav === 'barra') {
    for (const a of nav.querySelectorAll('li.silice-barra__item > a'))
      nombresBarra.push(limpio(a.textContent));
    for (const b of nav.querySelectorAll('button.silice-barra__area')) {
      const area = limpio(b.textContent);
      nombresBarra.push(area);
      if (b.getAttribute('aria-expanded') !== 'true') b.click();
      await cuadros();
      const panel = document.getElementById(b.getAttribute('aria-controls') || '');
      if (!panel) { paneles.push({ area, abierto: false, dentro: false }); continue; }
      const r = panel.getBoundingClientRect();
      paneles.push({ area, abierto: true, dentro: dentro(r), caja: caja(r),
        columnas: getComputedStyle(panel.querySelector('ul')).gridTemplateColumns
          .split(' ').length });
      for (const t of panel.querySelectorAll('.silice-panel-area__titulo'))
        nombresBarra.push(limpio(t.textContent));
    }
    const abierto = nav.querySelector('button.silice-barra__area[aria-expanded="true"]');
    if (abierto) { abierto.click(); await cuadros(); }
  }
  const nombresCapa = capa
    ? [...capa.querySelectorAll('.silice-capa__nombre, .silice-capa__rotulo')]
        .map(e => limpio(e.textContent))
    : [];
  s.paneles = paneles;
  if (s.modo_nav === 'capa') {
    const boton = document.querySelector('header button[aria-label="Abrir el menú"]');
    if (!boton || !visible(boton))
      s.capa = { abierta: false, motivo: 'no hay botón de menú visible' };
    else {
      boton.click();
      // El SideNav de Carbon se despliega con una transición de 110 ms: se mide ya asentado.
      let previo = -1;
      for (let i = 0; i < 40; i++) {
        await cuadros();
        const w = Math.round(capa.getBoundingClientRect().width);
        if (w > 0 && w === previo) break;
        previo = w;
      }
      const r = capa.getBoundingClientRect();
      const enlaces = [...capa.querySelectorAll('a')];
      s.capa = { abierta: capa.classList.contains('cds--side-nav--expanded'),
        dentro: dentro(r), caja: caja(r), enlaces: enlaces.length,
        enlaces_visibles: enlaces.filter(visible).length };
      const cerrar = document.querySelector('header button[aria-label="Cerrar el menú"]');
      if (cerrar) {
        cerrar.click();
        for (let i = 0; i < 40 && capa.getBoundingClientRect().width > 0; i++) await cuadros();
      }
    }
  }
  const fueraPaneles = paneles.filter(p => !p.dentro).map(p => p.area);
  const capaMal = s.capa && !(s.capa.abierta && s.capa.dentro && s.capa.caja[2] > s.capa.caja[0]
    && s.capa.enlaces > 0
    && s.capa.enlaces_visibles === s.capa.enlaces);
  s.panel_fuera = fueraPaneles.length > 0 || Boolean(capaMal);
  s.paneles_fuera = fueraPaneles.concat(capaMal ? ['capa'] : []);
  const dupBarra = repetidos(nombresBarra), dupCapa = repetidos(nombresCapa);
  s.duplicados_nav = dupBarra.length + dupCapa.length;
  s.duplicados_detalle = { barra: dupBarra, capa: dupCapa };
  s.nombres_barra = nombresBarra.length;
  s.nombres_capa = nombresCapa.length;
  return s;
}"""

# La columna «Recorrido» con un recorrido guiado en curso: a la vista, dentro de la ventana y sin
# tapar el contenido (columna fija a la derecha, o franja bajo la barra por debajo del umbral).
COLUMNA_JS = """() => {
  const col = document.querySelector('aside[aria-label="Recorrido"]');
  const main = document.querySelector('main#contenido');
  if (!col || !main) return { recorrido_visible: false };
  const ancho = document.documentElement.clientWidth;
  const r = col.getBoundingClientRect(), m = main.getBoundingClientRect();
  const fija = getComputedStyle(col).position === 'fixed';
  return {
    recorrido_visible: r.width > 0 && r.height > 0 && r.left >= -1 && r.right <= ancho + 1,
    recorrido_modo: fija ? 'columna' : 'franja',
    recorrido_solapa: fija ? m.right > r.left + 1 : m.top < r.bottom - 1,
    recorrido_caja: [r.left, r.top, r.right, r.bottom].map(Math.round),
  };
}"""


def fijar_letra(pagina: Any, letra: str) -> None:
    """El tamaño de letra guardado, antes de que cargue la interfaz (`main.tsx` lo aplica al
    arrancar y pone `<html data-silice-letra>`, como `TamanoLetra`)."""
    clave, valor = json.dumps(CLAVE_LETRA), json.dumps(letra)
    pagina.add_init_script(f"try {{ localStorage.setItem({clave}, {valor}); }} catch (e) {{}}")


def _escuchar(pagina: Any, consola: list[str], red: list[str]) -> None:
    pagina.on("console", lambda m: consola.append(m.text[:200]) if m.type == "error" else None)
    pagina.on("pageerror", lambda e: consola.append(f"pageerror: {str(e)[:200]}"))
    pagina.on("requestfailed", lambda r: red.append(f"FALLA {r.method} {r.url[:120]}"))
    pagina.on(
        "response",
        lambda r: (
            red.append(f"{r.status} {r.request.method} {r.url[:120]}") if r.status >= 400 else None
        ),
    )


def _medir_cargada(pagina: Any, fila: dict[str, Any], axe: str | None, captura: Path) -> None:
    """Medidas, axe, captura y controles de la barra de una pantalla ya cargada."""
    en_menu = fila.get("en_menu")
    fila.update(pagina.evaluate(MEDIR_JS))
    fila["en_menu"] = en_menu
    if axe:
        try:
            pagina.evaluate(axe)
            fila["axe"] = pagina.evaluate(
                "async () => (await axe.run(document, "
                "{runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}))"
                ".violations.map(v => ({id: v.id, impacto: v.impact, nodos: v.nodes.length}))"
            )
        except Exception as error:
            fila["axe_error"] = str(error)[:150]
    pagina.screenshot(path=str(captura), full_page=True)
    fila["captura"] = captura.name
    # Después de axe y de la captura, para que sean comparables con la corrida de referencia.
    fila.update(pagina.evaluate(NAV_JS))


def capturar_paneles(pagina: Any, prefijo: str, capturas: Path) -> list[str]:
    """Una captura con cada panel de área abierto (o con la capa abierta, si la barra no cabe), con
    clics de verdad: insumo del revisor de diseño."""
    hechas: list[str] = []
    botones = pagina.locator('nav[aria-label="Menú principal"] button.silice-barra__area')
    if botones.count() and botones.first.is_visible():
        for i in range(botones.count()):
            boton = botones.nth(i)
            area = re.sub(r"\W+", "_", boton.inner_text().strip().lower()) or str(i)
            boton.click()
            pagina.wait_for_timeout(250)
            destino = capturas / f"{prefijo}_panel_{area}.png"
            pagina.screenshot(path=str(destino))
            hechas.append(destino.name)
            pagina.keyboard.press("Escape")
            pagina.wait_for_timeout(150)
        return hechas
    menu = pagina.locator('header button[aria-label="Abrir el menú"]')
    if menu.count() and menu.first.is_visible():
        menu.first.click()
        pagina.wait_for_timeout(250)
        destino = capturas / f"{prefijo}_capa.png"
        pagina.screenshot(path=str(destino))
        hechas.append(destino.name)
        pagina.keyboard.press("Escape")
        pagina.wait_for_timeout(150)
    return hechas


def medir_pantalla(
    contexto: Any,
    base: str,
    ruta: dict[str, Any],
    ancho: int,
    rol: str,
    capturas: Path,
    axe: str | None,
    en_menu: set[str],
    letra: str = "normal",
) -> dict[str, Any]:
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": ancho, "height": ALTO})
    fijar_letra(pagina, letra)
    consola: list[str] = []
    red: list[str] = []
    _escuchar(pagina, consola, red)
    fila: dict[str, Any] = {
        "rol": rol,
        "ancho": ancho,
        "letra": letra,
        "id": ruta["id"],
        "titulo": ruta["titulo"],
        "seccion": ruta["seccion"],
        "accion": ruta["accion"],
        "en_menu": ruta["id"] in en_menu,
    }
    try:
        inicio = time.monotonic()
        pagina.goto(f"{base}/app/#/{ruta['id']}", wait_until="domcontentloaded")
        try:
            # Una ruta que el menú del rol no ofrece se espera poco: no es un error de carga.
            espera = LIMITE_CARGA_MS if fila["en_menu"] else 3000
            pagina.wait_for_selector("h1", timeout=espera)
            fila["ms_hasta_h1"] = round((time.monotonic() - inicio) * 1000)
        except Exception:
            fila["ms_hasta_h1"] = None
        with contextlib.suppress(Exception):
            pagina.wait_for_load_state("networkidle", timeout=3000)
        fila["ms_hasta_reposo"] = round((time.monotonic() - inicio) * 1000)
        _medir_cargada(pagina, fila, axe, capturas / f"{rol}_{ancho}_{letra}_{ruta['id']}.png")
        if ruta["id"] == "inicio":
            fila["capturas_paneles"] = capturar_paneles(pagina, f"{rol}_{ancho}_{letra}", capturas)
    except Exception as error:
        fila["error"] = str(error)[:300]
    fila["consola"] = consola[:8]
    fila["red"] = red[:8]
    pagina.close()
    return fila


def medir_con_recorrido(
    contexto: Any,
    base: str,
    libro: Path,
    ancho: int,
    rol: str,
    capturas: Path,
    axe: str | None,
    letra: str,
) -> list[dict[str, Any]]:
    """Inicio → soltar el libro → «Auditar con recorrido guiado»: mide Libro con el recorrido en
    curso y vuelve a Inicio sin recargar (el recorrido vive en la memoria de la interfaz)."""
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": ancho, "height": ALTO})
    fijar_letra(pagina, letra)
    consola: list[str] = []
    red: list[str] = []
    _escuchar(pagina, consola, red)
    filas: list[dict[str, Any]] = []
    base_fila = {"rol": rol, "ancho": ancho, "letra": letra, "recorrido": True, "en_menu": True}
    try:
        pagina.goto(f"{base}/app/#/inicio", wait_until="domcontentloaded")
        pagina.wait_for_selector("main h1", timeout=LIMITE_CARGA_MS)
        pagina.locator("main input[type=file]").first.set_input_files(str(libro))
        pagina.get_by_role("button", name="Auditar con recorrido guiado").click()
        pagina.wait_for_function(
            "() => location.hash === '#/libros' && document.querySelector('main h1') !== null",
            timeout=LIMITE_CARGA_MS,
        )
        for _ in range(80):
            if pagina.locator("[role=alert]").count() or pagina.locator(".visor__cuerpo").count():
                break
            pagina.wait_for_timeout(500)
        for id_ in ("libros", "inicio"):
            if id_ == "inicio":
                ir_por_hash(pagina, "inicio")
            pagina.wait_for_timeout(500)
            antes_consola, antes_red = len(consola), len(red)
            fila: dict[str, Any] = {**base_fila, "id": id_}
            try:
                captura = capturas / f"{rol}_{ancho}_{letra}_recorrido_{id_}.png"
                _medir_cargada(pagina, fila, axe, captura)
                fila.update(pagina.evaluate(COLUMNA_JS))
            except Exception as error:
                fila["error"] = str(error)[:300]
            fila["consola"] = consola[antes_consola:][:8]
            fila["red"] = red[antes_red:][:8]
            filas.append(fila)
    except Exception as error:
        filas.append(
            {**base_fila, "id": "libros", "error": str(error)[:300], "consola": consola[:8]}
            | {"red": red[:8]}
        )
    pagina.close()
    return filas


# --------------------------- flujo de la empresa de hoy ----------------------------------------


class Contador:
    """Cuenta lo que el flujo le exige a la persona."""

    def __init__(self) -> None:
        self.pasos: list[dict[str, Any]] = []

    def anotar(self, tipo: str, texto: str, **extra: Any) -> None:
        self.pasos.append({"n": len(self.pasos) + 1, "tipo": tipo, "texto": texto, **extra})

    def resumen(self) -> dict[str, Any]:
        tipos = [p["tipo"] for p in self.pasos]
        return {
            "clics": tipos.count("clic"),
            "archivos_elegidos": tipos.count("archivo"),
            "campos": tipos.count("campo"),
            "decisiones": tipos.count("decision"),
            "pantallas": len({p.get("pantalla") for p in self.pasos if p.get("pantalla")}),
            "pasos": self.pasos,
        }


def libros_ficticios(carpeta: Path) -> dict[str, Path]:
    from tests.fixtures.libros_empresa import libro_limpio

    carpeta.mkdir(parents=True, exist_ok=True)
    limpio = carpeta / "libro_plantilla_empresa_ficticio.xlsx"
    limpio.write_bytes(libro_limpio().datos)
    otros: dict[str, Path] = {"limpio": limpio}
    ajeno = RAIZ / "tests" / "fixtures" / "control" / "ob_s2.xlsx"
    if ajeno.exists():
        otros["ajeno_control"] = ajeno
    csv = carpeta / "presupuesto.csv"
    csv.write_text("codigo,descripcion,cantidad,precio\nP-1,Friso,10,5\n", encoding="utf-8")
    otros["csv"] = csv
    return otros


def aviso_visible(pagina: Any) -> str:
    textos = pagina.eval_on_selector_all(
        "[role=alert], .cds--inline-notification, .cds--actionable-notification",
        "els => els.map(e => e.innerText.replace(/\\s+/g, ' ').trim().slice(0, 300))",
    )
    return " | ".join(textos)


def flujo_libros(
    contexto: Any, base: str, libro: Path, capturas: Path, etiqueta: str, desde: str = "libros"
) -> dict[str, Any]:
    """Subir un libro y esperar la auditoría (desde el Inicio o desde «Libro de la empresa»)."""
    c = Contador()
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 1366, "height": ALTO})
    red: list[str] = []
    pagina.on(
        "response",
        lambda r: (
            red.append(f"{r.status} {r.request.method} {r.url[:110]}") if r.status >= 400 else None
        ),
    )
    inicio = time.monotonic()
    pagina.goto(f"{base}/app/#/inicio", wait_until="domcontentloaded")
    pagina.wait_for_selector("h1", timeout=LIMITE_CARGA_MS)
    c.anotar("pantalla", "Inicio", pantalla="inicio")
    c.anotar(
        "decision",
        "elegir entre las herramientas/áreas del Inicio y del menú (5 áreas, 22 pantallas)",
    )
    if desde == "libros":
        enlace = pagina.locator("a[href*='#/libros']").first
        enlace.click()
        c.anotar("clic", "ir a «Libro de la empresa»", pantalla="libros")
        pagina.wait_for_selector("h1:has-text('Libro de la empresa')", timeout=LIMITE_CARGA_MS)
        pagina.wait_for_timeout(800)
        c.anotar("decision", "fecha de devolución (campo con valor por omisión)")
    entrada = pagina.locator("input[type=file]").first
    entrada.set_input_files(str(libro))
    c.anotar("archivo", f"elegir el libro ({libro.name})")
    if desde == "inicio":
        boton = pagina.get_by_role("button", name="Auditar por mi cuenta")
        if boton.count():
            c.anotar("decision", "«Auditar con recorrido guiado» o «Auditar por mi cuenta»")
            boton.click()
            c.anotar("clic", "«Auditar por mi cuenta»", pantalla="libros")
    t0 = time.monotonic()
    resultado = "sin resultado"
    for _ in range(80):
        pagina.wait_for_timeout(500)
        if pagina.locator("[role=alert]").count() or pagina.locator(".visor__cuerpo").count():
            break
    aviso = aviso_visible(pagina)
    if pagina.locator(".visor__cuerpo").count():
        resultado = "visor con hoja y hallazgos"
    elif aviso:
        resultado = "error: " + aviso
    pagina.wait_for_timeout(1500)
    nombre = capturas / f"flujo_{etiqueta}_libros.png"
    pagina.screenshot(path=str(nombre), full_page=True)
    if "visor con hoja" in resultado:
        c.anotar("clic", "leer hallazgos en la lista/hoja (sin informe accionable ni exportación)")
    salida = c.resumen()
    salida.update(
        {
            "etiqueta": etiqueta,
            "archivo": libro.name,
            "resultado": resultado,
            "hash_final": pagina.evaluate("location.hash"),
            "h1_final": pagina.locator("h1").all_inner_texts()[:2],
            "segundos_hasta_resultado": round(time.monotonic() - t0, 1),
            "segundos_totales": round(time.monotonic() - inicio, 1),
            "red": red[:6],
            "captura": nombre.name,
        }
    )
    pagina.close()
    return salida


def flujo_revisar_excel(
    contexto: Any, base: str, libro: Path, capturas: Path, etiqueta: str
) -> dict[str, Any]:
    """«Revisar un paquete» -> pestaña «Presupuesto en Excel» -> subir."""
    c = Contador()
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 1366, "height": ALTO})
    inicio = time.monotonic()
    pagina.goto(f"{base}/app/#/revisar", wait_until="domcontentloaded")
    pagina.wait_for_selector("h1", timeout=LIMITE_CARGA_MS)
    c.anotar("pantalla", "Revisar un paquete", pantalla="revisar")
    c.anotar("decision", "entre «Paquete .silice» y «Presupuesto en Excel»")
    pagina.get_by_role("tab", name="Presupuesto en Excel").click()
    c.anotar("clic", "pestaña «Presupuesto en Excel»")
    pagina.wait_for_timeout(500)
    pagina.locator("#revisar-excel, input[type=file]").last.set_input_files(str(libro))
    c.anotar("archivo", f"elegir el presupuesto ({libro.name})")
    t0 = time.monotonic()
    for _ in range(60):
        pagina.wait_for_timeout(500)
        if pagina.locator("[role=alert]").count() or pagina.locator("table").count():
            break
    pagina.wait_for_timeout(800)
    aviso = aviso_visible(pagina)
    filas = pagina.locator("table tbody tr").count()
    resultado = ("error: " + aviso) if aviso else f"tabla de hallazgos con {filas} filas"
    nombre = capturas / f"flujo_{etiqueta}_revisar_excel.png"
    pagina.screenshot(path=str(nombre), full_page=True)
    salida = c.resumen()
    salida.update(
        {
            "etiqueta": etiqueta,
            "archivo": libro.name,
            "resultado": resultado,
            "segundos_hasta_resultado": round(time.monotonic() - t0, 1),
            "segundos_totales": round(time.monotonic() - inicio, 1),
            "captura": nombre.name,
        }
    )
    pagina.close()
    return salida


# --------------------------- modo funcional (BS-F) ----------------------------------------------
#
# Cada fila de `recorrido_funcional.toml` dice: la ruta, la cuenta que la usa, la carpeta de trabajo
# y el proyecto (si hacen falta), los pasos y lo que debe verse al final. Las filas se ejecutan en
# el orden del archivo, con UNA página por cuenta (el proyecto elegido vive en la memoria de la
# interfaz, RT-9): se navega cambiando `location.hash`, sin recargar.

ACCIONES_TOML = Path(__file__).with_name("recorrido_funcional.toml")
# El botón de la barra superior que abre «Carpeta y proyecto» (su aria-label empieza así).
BOTON_CARPETA = 'button[aria-label^="Carpeta de trabajo"]'
ACCIONES_ADMITIDAS = {"llenar", "elegir", "pulsar", "marcar", "subir", "ir", "esperar", "tecla"}
LIMITE_PASO_MS = 15_000
LIMITE_ESPERA_MS = 30_000


class ServidorCongelado(Servidor):
    """El mismo servidor, pero sirviendo una COPIA de `frontend-desktop/dist`: si otro proceso
    recompila la interfaz a mitad del recorrido, los trozos perezosos no desaparecen (404)."""

    def __init__(self, datos: Path, puerto: int, dist: Path) -> None:
        entorno = dict(os.environ)
        entorno["SILICE_DATOS"] = str(datos)
        entorno["SILICE_USUARIO"] = str(datos / "usuario")
        entorno.pop("SILICE_INSTALACION", None)
        arranque = (
            "import sys; from pathlib import Path; import api.interfaz as i; "
            "i.DIST = Path(sys.argv[1]); import uvicorn; "
            "uvicorn.run('api.main:app', host='127.0.0.1', port=int(sys.argv[2]), "
            "access_log=False)"
        )
        self.puerto = puerto
        self.proceso = subprocess.Popen(
            [sys.executable, "-c", arranque, str(dist), str(puerto)],
            cwd=RAIZ,
            env=entorno,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.url = f"http://127.0.0.1:{puerto}"


def congelar_interfaz(destino: Path) -> dict[str, str]:
    """Copia el `dist` compilado y devuelve de cuándo es (para la bitácora)."""
    origen = RAIZ / "frontend-desktop" / "dist"
    if not (origen / "index.html").exists():
        raise SystemExit("falta frontend-desktop/dist: corra «npm run build» en frontend-desktop")
    shutil.rmtree(destino, ignore_errors=True)
    shutil.copytree(origen, destino)
    momento = time.localtime((origen / "index.html").stat().st_mtime)
    return {"dist_compilado": time.strftime("%Y-%m-%d %H:%M:%S", momento)}


def cargar_filas_funcionales(ruta: Path) -> dict[str, list[dict[str, Any]]]:
    """Las filas de siembra y de pantalla, con una validación mínima del formato."""
    import tomllib

    datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    filas = {"siembra": datos.get("siembra", []), "pantalla": datos.get("pantalla", [])}
    for tipo, lista in filas.items():
        for n, fila in enumerate(lista, 1):
            for clave in ("ruta", "cuenta", "espera"):
                if clave not in fila:
                    raise ValueError(f"{tipo} {n}: falta «{clave}»")
            if fila["cuenta"] not in ROLES:
                raise ValueError(f"{tipo} {n}: cuenta desconocida «{fila['cuenta']}»")
            for paso in fila.get("pasos", []):
                if paso.get("accion") not in ACCIONES_ADMITIDAS:
                    raise ValueError(f"{tipo} {n}: acción no admitida {paso!r}")
    rutas = [f["ruta"] for f in filas["pantalla"]]
    for fila in filas["pantalla"]:
        for previa in fila.get("requiere", []):
            if previa not in rutas or rutas.index(previa) >= rutas.index(fila["ruta"]):
                raise ValueError(f"{fila['ruta']}: «requiere» {previa!r} no es una fila anterior")
    return filas


def seleccionar_pantallas(
    filas: list[dict[str, Any]], solo: list[str] | None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Las filas de `--solo` (con espacios o con comas) más las que ellas `requiere`, en el orden
    del archivo. Un nombre que no es una fila, o quedarse sin filas, es un error (no un verde)."""
    if solo is None:
        return list(filas), []
    pedidas = [n.strip() for parte in solo for n in parte.split(",") if n.strip()]
    rutas = [f["ruta"] for f in filas]
    desconocidas = [n for n in pedidas if n not in rutas]
    if desconocidas:
        raise ValueError(
            f"--solo: no hay fila para {', '.join(desconocidas)}; las filas son: {', '.join(rutas)}"
        )
    if not pedidas:
        raise ValueError("--solo sin rutas: no quedaría ninguna fila que ejecutar")
    elegidas = set(pedidas)
    for fila in reversed(filas):  # las dependencias siempre son filas anteriores
        if fila["ruta"] in elegidas:
            elegidas.update(fila.get("requiere", []))
    agregadas = [r for r in rutas if r in elegidas and r not in pedidas]
    return [f for f in filas if f["ruta"] in elegidas], agregadas


def archivos_de_entrada(carpeta: Path) -> dict[str, Path]:
    """Los archivos ficticios que suben las filas (`archivo = "<clave>"`), todos de fixtures."""
    carpeta.mkdir(parents=True, exist_ok=True)
    archivos = {k: v for k, v in libros_ficticios(carpeta).items() if k == "limpio"}
    archivos["libro_limpio"] = archivos.pop("limpio")
    fijos = {
        # Tasa de referencia del BCV (archivo público de fixture; tests/fixtures/bcv/FUENTE.md)
        "bcv_tasa": RAIZ / "tests" / "fixtures" / "bcv" / "2_1_2c26_smc.xls",
        # Lista ficticia de la empresa del caso S1 (tests/fixtures/precios_empresa_s1.py)
        "precios_empresa_s1": RAIZ / "tests" / "fixtures" / "precios_empresa_s1.csv",
        # Muestras ficticias de las pruebas (tests/fixtures/actualizacion_uc02.py, caso_ti001.py)
        "lista_precios": RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv",
        "topologia_ti001": RAIZ / "data" / "samples" / "telecom" / "topologia_ti001.csv",
    }
    for clave, ruta in fijos.items():
        if ruta.exists():
            archivos[clave] = ruta
    return archivos


def _principal(pagina: Any) -> Any:
    """El contenido de la pantalla (sin la cabecera, que también tiene «Proyecto»)."""
    return pagina.locator("main").first


def _rellenable(donde: Any, rotulo: str) -> Any:
    """El campo con esa etiqueta exacta que se puede escribir (no su envoltorio de búsqueda)."""
    return donde.get_by_label(rotulo, exact=True).and_(
        donde.locator("input:not([type=file]), textarea, [contenteditable=true]")
    )


def elegir_opcion(campo: Any, opcion: str) -> str:
    """Elige en un `select` la opción cuyo valor o texto es `opcion` o, si no, la primera cuyo texto
    la contiene. Espera a que la opción exista (las listas llegan de la API)."""
    fin = time.monotonic() + LIMITE_PASO_MS / 1000
    while True:
        opciones = campo.evaluate(
            "s => [...s.options].map(o => ({v: o.value, t: o.textContent.trim(), d: o.disabled}))"
        )
        exacta = [o for o in opciones if not o["d"] and opcion in (o["v"], o["t"])]
        parcial = [o for o in opciones if not o["d"] and opcion.lower() in o["t"].lower()]
        elegida = (exacta or parcial or [None])[0]
        if elegida is not None:
            campo.select_option(value=elegida["v"], timeout=LIMITE_PASO_MS)
            return elegida["t"]
        if time.monotonic() > fin:
            raise RuntimeError(f"no hay opción «{opcion}» en {[o['t'] for o in opciones]}")
        time.sleep(0.3)


def ir_por_hash(pagina: Any, ruta: str) -> None:
    pagina.evaluate("r => { location.hash = '#/' + r; }", ruta)
    pagina.wait_for_function(
        "r => location.hash === '#/' + r && document.querySelector('main h1') !== null",
        arg=ruta,
        timeout=LIMITE_CARGA_MS,
    )
    with contextlib.suppress(Exception):
        pagina.wait_for_load_state("networkidle", timeout=3000)


def caso_de_la_sesion(pagina: Any) -> str | None:
    """La carpeta de trabajo que la API tiene para esta sesión (no la que muestra el selector)."""
    return pagina.evaluate(
        "async () => { const r = await fetch('/v1/casos', {credentials: 'same-origin'});"
        " if (!r.ok) return null; const d = await r.json();"
        " return d && d.actual ? d.actual.nombre : null; }"
    )


def carpeta_mostrada_y_real(pagina: Any) -> dict[str, Any]:
    """Control del armazón en cada fila: la carpeta que el selector MUESTRA frente a la que la API
    tiene para la sesión (sin la extensión `.db`, que la interfaz no muestra)."""
    mostrada = pagina.evaluate(
        "() => { const s = document.querySelector('#selector-caso');"
        " if (s && s.selectedIndex >= 0) return s.options[s.selectedIndex].textContent.trim();"
        " const b = document.querySelector('button[aria-label^=\"Carpeta de trabajo\"]');"
        " return b ? b.textContent.trim() : null; }"
    )
    real = caso_de_la_sesion(pagina)
    corta = (real or "").removesuffix(".db")
    return {
        "carpeta_mostrada": mostrada,
        "carpeta_api": real,
        "carpeta_coincide": bool(mostrada) and bool(corta) and mostrada.startswith(corta),
    }


def elegir_contexto(pagina: Any, carpeta: str | None, proyecto: str | None) -> None:
    """Carpeta de trabajo y proyecto, con la cabecera de hoy (dos `select`) o con la barra superior
    (los mismos `select` dentro del panel «Carpeta y proyecto», que se abre con su botón)."""

    def asegurar(selector: str) -> Any:
        control = pagina.locator(selector)
        if not control.is_visible():
            boton = pagina.locator(BOTON_CARPETA)
            if boton.count() and boton.first.get_attribute("aria-expanded") != "true":
                boton.first.click()
        control.wait_for(state="visible", timeout=LIMITE_PASO_MS)
        return control

    if carpeta:
        control = asegurar("#selector-caso")
        if caso_de_la_sesion(pagina) != carpeta:
            # El selector puede MOSTRAR la carpeta pedida sin que sea la de la sesión (defecto
            # anotado en la bitácora): se elige igual y se comprueba contra la API, no contra él.
            control.select_option(carpeta)
            fin = time.monotonic() + LIMITE_PASO_MS / 1000
            while caso_de_la_sesion(pagina) != carpeta:
                if time.monotonic() > fin:
                    raise RuntimeError(f"la carpeta de trabajo no cambió a «{carpeta}»")
                pagina.wait_for_timeout(300)
            pagina.wait_for_function(
                "() => { const s = document.querySelector('#selector-caso');"
                " return s && !s.disabled; }",
                timeout=LIMITE_PASO_MS,
            )
            pagina.wait_for_timeout(800)
    if proyecto:
        elegir_opcion(asegurar("#selector-proyecto"), proyecto)
        pagina.wait_for_timeout(800)
    boton = pagina.locator(BOTON_CARPETA)
    if boton.count() and boton.first.get_attribute("aria-expanded") == "true":
        pagina.keyboard.press("Escape")


def _texto_principal(pagina: Any) -> str:
    try:
        return re.sub(r"\s+", " ", _principal(pagina).inner_text(timeout=2000))
    except Exception:
        return ""


def esperar_textos(pagina: Any, textos: list[str], limite_ms: int) -> list[str]:
    """Espera a que cada texto se vea en la pantalla; devuelve los que no aparecieron."""
    fin = time.monotonic() + limite_ms / 1000
    faltan = list(textos)
    while True:
        visible = _texto_principal(pagina)
        faltan = [t for t in textos if re.sub(r"\s+", " ", t) not in visible]
        if not faltan or time.monotonic() > fin:
            return faltan
        pagina.wait_for_timeout(400)


def esperar_ausentes(pagina: Any, textos: list[str], limite_ms: int) -> list[str]:
    """Espera a que ningún texto se vea (un filtro que sí filtra); devuelve los que siguen."""
    fin = time.monotonic() + limite_ms / 1000
    while True:
        visible = _texto_principal(pagina)
        siguen = [t for t in textos if re.sub(r"\s+", " ", t) in visible]
        if not siguen or time.monotonic() > fin:
            return siguen
        pagina.wait_for_timeout(400)


def ejecutar_paso(
    pagina: Any, paso: dict[str, Any], archivos: dict[str, Path], descargas: Path
) -> str:
    """Un paso de una fila; devuelve una línea para la bitácora. Falla con excepción."""
    accion = paso["accion"]
    zona = _principal(pagina)
    indice = int(paso.get("indice", 0))
    if accion == "ir":
        ir_por_hash(pagina, paso["ruta"])
        return f"ir #/{paso['ruta']}"
    if accion == "llenar":
        donde = pagina if paso.get("fuera") else zona
        valor = str(paso["valor"]).replace("{hoy}", time.strftime("%Y-%m-%d"))
        campo = _rellenable(donde, paso["rotulo"]).nth(indice)
        campo.fill(valor, timeout=LIMITE_PASO_MS)
        return f"llenar «{paso['rotulo']}» = {valor!r}"
    if accion == "elegir":
        campo = zona.get_by_label(paso["rotulo"], exact=True).and_(zona.locator("select"))
        campo = campo.nth(indice)
        elegido = elegir_opcion(campo, str(paso["opcion"]))
        return f"elegir «{paso['rotulo']}» = {elegido!r}"
    if accion == "marcar":
        campo = zona.get_by_label(paso["rotulo"], exact=True).nth(indice)
        try:
            campo.check(timeout=4000)
        except Exception:
            zona.get_by_text(paso["rotulo"], exact=True).nth(indice).click(timeout=LIMITE_PASO_MS)
        return f"marcar «{paso['rotulo']}»"
    if accion == "pulsar":
        rol = paso.get("rol", "button")
        exacto = bool(paso.get("exacto", True))
        donde = pagina if paso.get("fuera") else zona
        boton = donde.get_by_role(rol, name=paso["nombre"], exact=exacto).nth(indice)
        if paso.get("descarga"):
            with pagina.expect_download(timeout=LIMITE_ESPERA_MS) as bajada:
                boton.click(timeout=LIMITE_PASO_MS)
            destino = descargas / bajada.value.suggested_filename
            bajada.value.save_as(str(destino))
            archivos[paso["descarga"]] = destino
            tamano = destino.stat().st_size
            return f"pulsar «{paso['nombre']}» -> descarga {destino.name} ({tamano} B)"
        boton.click(timeout=LIMITE_PASO_MS)
        return f"pulsar {rol} «{paso['nombre']}»"
    if accion == "subir":
        archivo = archivos.get(paso["archivo"])
        if archivo is None:
            raise RuntimeError(f"no hay «{paso['archivo']}» (¿falló la fila que lo genera?)")
        boton = zona.get_by_role("button", name=paso["zona"], exact=False).first
        with pagina.expect_file_chooser(timeout=LIMITE_PASO_MS) as elector:
            boton.click(timeout=LIMITE_PASO_MS)
        elector.value.set_files(str(archivo))
        return f"subir {archivo.name}"
    if accion == "esperar":
        faltan = esperar_textos(pagina, [paso["texto"]], int(paso.get("ms", LIMITE_ESPERA_MS)))
        if faltan:
            raise RuntimeError(f"no apareció «{paso['texto']}»")
        return f"esperar «{paso['texto']}»"
    if accion == "tecla":
        pagina.keyboard.press(paso["nombre"])
        return f"tecla {paso['nombre']}"
    raise ValueError(f"acción no admitida: {accion}")


def comprobar_espera(
    pagina: Any, espera: dict[str, Any], archivos: dict[str, Path]
) -> tuple[bool, str]:
    """El resultado visible de la fila: textos en pantalla y, si se pide, el archivo bajado."""
    textos = list(espera.get("textos", []))
    if "texto" in espera:
        textos.insert(0, espera["texto"])
    detalle: list[str] = []
    ok = True
    if textos:
        faltan = esperar_textos(pagina, textos, int(espera.get("ms", LIMITE_ESPERA_MS)))
        if faltan:
            ok = False
            detalle.append("no se ve: " + " | ".join(f"«{t}»" for t in faltan))
        else:
            detalle.append("se ve: " + " | ".join(f"«{t}»" for t in textos))
    ausentes = list(espera.get("ausentes", []))
    if ausentes:
        siguen = esperar_ausentes(pagina, ausentes, int(espera.get("ms_ausentes", 5000)))
        if siguen:
            ok = False
            detalle.append("todavía se ve: " + " | ".join(f"«{t}»" for t in siguen))
        else:
            detalle.append("ya no se ve: " + " | ".join(f"«{t}»" for t in ausentes))
    if espera.get("descarga"):
        archivo = archivos.get(espera["descarga"])
        if archivo is None or not archivo.exists() or archivo.stat().st_size == 0:
            ok = False
            detalle.append(f"no se descargó «{espera['descarga']}»")
        else:
            import hashlib

            huella = hashlib.sha256(archivo.read_bytes()).hexdigest()
            detalle.append(f"descargado {archivo.name} ({archivo.stat().st_size} B)")
            if espera.get("huella"):
                if huella in _texto_principal(pagina):
                    detalle.append(f"la huella en pantalla es la del archivo ({huella[:12]}…)")
                else:
                    ok = False
                    detalle.append(f"la huella del archivo ({huella[:12]}…) no está en pantalla")
    if not espera.get("admite_error"):
        errores = pagina.eval_on_selector_all(
            ".cds--inline-notification--error, .cds--actionable-notification--error,"
            " .cds--toast-notification--error",
            "els => els.filter(e => e.offsetParent !== null)"
            r".map(e => e.innerText.replace(/\s+/g, ' ').trim().slice(0, 300))",
        )
        if errores:
            ok = False
            detalle.append("aviso de error en pantalla: " + " | ".join(errores))
    return ok, "; ".join(detalle)


def ejecutar_fila(
    pagina: Any,
    fila: dict[str, Any],
    archivos: dict[str, Path],
    salida: Path,
    etiqueta: str,
) -> dict[str, Any]:
    consola: list[str] = []
    red: list[str] = []

    def al_consola(m: Any) -> None:
        if m.type == "error":
            consola.append(m.text[:200])

    def al_error(e: Any) -> None:
        consola.append(f"pageerror: {str(e)[:200]}")

    def al_responder(r: Any) -> None:
        if r.status >= 400:
            red.append(f"{r.status} {r.request.method} {r.url.split('127.0.0.1')[-1][:100]}")

    pagina.on("console", al_consola)
    pagina.on("pageerror", al_error)
    pagina.on("response", al_responder)
    resultado: dict[str, Any] = {
        "ruta": fila["ruta"],
        "cuenta": fila["cuenta"],
        "carpeta": fila.get("carpeta"),
        "proyecto": fila.get("proyecto"),
        "accion": fila.get("accion", ""),
        "pasos": [],
    }
    inicio = time.monotonic()
    try:
        ir_por_hash(pagina, fila["ruta"])
        elegir_contexto(pagina, fila.get("carpeta"), fila.get("proyecto"))
        ir_por_hash(pagina, fila["ruta"])
        for paso in fila.get("pasos", []):
            resultado["pasos"].append(ejecutar_paso(pagina, paso, archivos, salida / "descargas"))
        ok, detalle = comprobar_espera(pagina, fila["espera"], archivos)
        resultado["paso"] = ok
        resultado["salida"] = detalle
    except Exception as error:
        resultado["paso"] = False
        resultado["salida"] = f"error en el paso {len(resultado['pasos']) + 1}: {str(error)[:400]}"
    resultado["segundos"] = round(time.monotonic() - inicio, 1)
    with contextlib.suppress(Exception):
        resultado.update(carpeta_mostrada_y_real(pagina))
    resultado["avisos"] = aviso_visible(pagina)[:600]
    resultado["consola"] = consola[:6]
    resultado["red"] = red[:6]
    captura = salida / "capturas" / f"{etiqueta}.png"
    with contextlib.suppress(Exception):
        pagina.screenshot(path=str(captura), full_page=True)
        resultado["captura"] = captura.name
    if not resultado["paso"]:
        with contextlib.suppress(Exception):
            (salida / "arbol" / f"{etiqueta}.txt").write_text(
                _principal(pagina).aria_snapshot(timeout=5000), encoding="utf-8"
            )
            resultado["arbol"] = f"{etiqueta}.txt"
    pagina.remove_listener("console", al_consola)
    pagina.remove_listener("pageerror", al_error)
    pagina.remove_listener("response", al_responder)
    return resultado


def main_funcional(salida: Path, acciones: Path, solo: list[str] | None) -> int:
    """Siembra, ejecuta las filas en orden y escribe `funcional.json`; 1 si alguna falla."""
    filas = cargar_filas_funcionales(acciones)
    try:
        pantallas, agregadas = seleccionar_pantallas(filas["pantalla"], solo)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if agregadas:
        print(f"--solo: se agregan las filas que se requieren: {', '.join(agregadas)}")
    for sub in ("capturas", "arbol", "descargas"):
        (salida / sub).mkdir(parents=True, exist_ok=True)
    rutas = [r["id"] for r in rutas_de_la_interfaz()]
    sin_fila = [r for r in rutas if r not in {f["ruta"] for f in filas["pantalla"]}]
    archivos = archivos_de_entrada(salida / "entradas")
    temporal = Path(tempfile.mkdtemp(prefix="datos_funcional_", dir=salida))
    claves = sembrar_datos(temporal)
    compilado = congelar_interfaz(temporal / "dist")
    servidor = ServidorCongelado(temporal, puerto_libre(), temporal / "dist")
    informe: dict[str, Any] = {
        "base": servidor.url,
        **compilado,
        "rutas_de_la_interfaz": len(rutas),
        "sin_fila": sin_fila,
        "solo": solo,
        "agregadas_por_requiere": agregadas,
        "siembra": [],
        "pantallas": [],
    }
    try:
        servidor.esperar()
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            navegador = lanzar_navegador(p)
            paginas: dict[str, Any] = {}
            try:

                def pagina_de(cuenta: str) -> Any:
                    if cuenta not in paginas:
                        contexto = navegador.new_context(
                            viewport={"width": 1366, "height": ALTO}, accept_downloads=True
                        )
                        pagina = contexto.new_page()
                        pagina.set_default_timeout(LIMITE_PASO_MS)
                        entrar(pagina, servidor.url, cuenta, claves[cuenta])
                        paginas[cuenta] = pagina
                    return paginas[cuenta]

                for n, fila in enumerate(filas["siembra"], 1):
                    r = ejecutar_fila(
                        pagina_de(fila["cuenta"]), fila, archivos, salida, f"siembra{n:02}"
                    )
                    informe["siembra"].append(r)
                    print(f"siembra {n:2} {fila['ruta']:15} {'ok' if r['paso'] else 'FALLA'}")
                for n, fila in enumerate(pantallas, 1):
                    etiqueta = f"{n:02}_{fila['ruta']}"
                    r = ejecutar_fila(pagina_de(fila["cuenta"]), fila, archivos, salida, etiqueta)
                    informe["pantallas"].append(r)
                    print(
                        f"{n:2} {fila['ruta']:15} {fila['cuenta']:5} "
                        f"{'PASA ' if r['paso'] else 'FALLA'} {r['salida'][:150]}"
                    )
            finally:
                for pagina in paginas.values():
                    with contextlib.suppress(Exception):
                        pagina.context.close()
                navegador.close()
    finally:
        servidor.cerrar()
        for _ in range(10):  # Windows suelta las bases un momento después de cerrar el servidor
            shutil.rmtree(temporal, ignore_errors=True)
            if not temporal.exists():
                break
            time.sleep(1)
    informe["resumen"] = {
        "filas": len(informe["pantallas"]),
        "pasan": sum(1 for r in informe["pantallas"] if r["paso"]),
        "fallan": [r["ruta"] for r in informe["pantallas"] if not r["paso"]],
        "siembra_fallida": [r["ruta"] for r in informe["siembra"] if not r["paso"]],
        "carpeta_mostrada_distinta": [
            f"{r['ruta']} ({r['cuenta']}): muestra {r.get('carpeta_mostrada')!r}, "
            f"la sesión usa {r.get('carpeta_api')!r}"
            for r in informe["pantallas"]
            if r.get("carpeta_coincide") is False
        ],
        "sin_fila": sin_fila,
    }
    (salida / "funcional.json").write_text(
        json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(informe["resumen"], indent=2, ensure_ascii=False))
    resumen = informe["resumen"]
    return 0 if not (resumen["fallan"] or resumen["siembra_fallida"] or sin_fila) else 1


# --------------------------- orquestación -------------------------------------------------------


def axe_nuevas(fila: dict[str, Any]) -> list[str]:
    """Las reglas axe violadas en esta pantalla que no estaban en la corrida de referencia."""
    return [v["id"] for v in fila.get("axe", []) if (fila["id"], v["id"]) not in AXE_DE_REFERENCIA]


def resumir(filas: list[dict[str, Any]]) -> dict[str, Any]:
    def n(pred: Any, grupo: list[dict[str, Any]] | None = None) -> int:
        return sum(1 for f in (filas if grupo is None else grupo) if pred(f))

    def controles(grupo: list[dict[str, Any]]) -> dict[str, Any]:
        accesibles = [f for f in grupo if f.get("en_menu")]
        return {
            "mediciones": len(grupo),
            "en_menu": len(accesibles),
            "con_error_de_carga": n(lambda f: "error" in f, grupo),
            "en_menu_sin_un_h1": n(lambda f: f.get("h1") != 1, accesibles),
            "fuera_de_menu_sin_h1": n(lambda f: not f.get("en_menu") and f.get("h1") == 0, grupo),
            "con_varios_h1": n(lambda f: (f.get("h1") or 0) > 1, grupo),
            "con_scroll_horizontal": n(lambda f: f.get("scroll_x"), grupo),
            "con_errores_de_consola": n(lambda f: f.get("consola"), grupo),
            "con_errores_de_red": n(lambda f: f.get("red"), grupo),
            "letra_no_aplicada": n(lambda f: f.get("letra_aplicada") != f.get("letra"), grupo),
            "duplicados_nav": sum(f.get("duplicados_nav") or 0 for f in grupo),
            "sin_control_nav": n(lambda f: "duplicados_nav" not in f, grupo),
            "barra_cortada": n(lambda f: f.get("barra_cortada") is not False, grupo),
            "panel_fuera": n(lambda f: f.get("panel_fuera") is not False, grupo),
            "modo_nav": {
                m: n(lambda f, m=m: f.get("modo_nav") == m, grupo) for m in ("barra", "capa")
            },
            "con_violaciones_axe": n(lambda f: f.get("axe"), grupo),
            "con_violaciones_axe_nuevas": n(lambda f: axe_nuevas(f), grupo),
            "sin_axe": n(lambda f: "axe" not in f, grupo),
        }

    normales = [f for f in filas if not f.get("recorrido")]
    con_recorrido = [f for f in filas if f.get("recorrido")]
    letras = sorted({f.get("letra") for f in filas}, key=lambda x: LETRAS.index(x))
    resumen = controles(normales)
    resumen["por_letra"] = {
        letra: controles([f for f in normales if f.get("letra") == letra]) for letra in letras
    }
    resumen["con_recorrido"] = controles(con_recorrido)
    resumen["con_recorrido"]["columna_no_visible"] = n(
        lambda f: not f.get("recorrido_visible"), con_recorrido
    )
    resumen["con_recorrido"]["columna_solapa"] = n(
        lambda f: f.get("recorrido_solapa") is not False, con_recorrido
    )
    resumen["axe_nuevas"] = sorted(
        {
            f"{f['rol']} {f['ancho']} {f['letra']} {f['id']}: {r}"
            for f in filas
            for r in axe_nuevas(f)
        }
    )
    resumen["fallos_nav"] = sorted(filter(None, map(fallo_nav, filas)))
    return resumen


def fallo_nav(fila: dict[str, Any]) -> str | None:
    """Una línea por medición con un control de la barra en rojo (o sin medir)."""
    motivos = []
    if "duplicados_nav" not in fila:
        motivos.append("sin control de la barra: " + str(fila.get("error", "")))
    if fila.get("duplicados_nav"):
        motivos.append(f"duplicados {fila.get('duplicados_detalle')}")
    if fila.get("barra_cortada"):
        motivos.append(f"cortada {fila.get('barra_motivos')}")
    if fila.get("panel_fuera"):
        motivos.append(f"fuera {fila.get('paneles_fuera')} {fila.get('capa', '')}")
    if not motivos:
        return None
    marca = " (recorrido)" if fila.get("recorrido") else ""
    return f"{fila['rol']} {fila['ancho']} {fila['letra']} {fila['id']}{marca}: " + "; ".join(
        motivos
    )


def letras_pedidas(valores: list[str]) -> list[str]:
    """`--letras normal,grande` o `--letras normal grande`; en el orden de `LETRAS`."""
    pedidas = {v.strip() for parte in valores for v in parte.split(",") if v.strip()}
    desconocidas = pedidas - set(LETRAS)
    if desconocidas or not pedidas:
        raise SystemExit(
            f"--letras: use {', '.join(LETRAS)} (no {', '.join(sorted(desconocidas))})"
        )
    return [letra for letra in LETRAS if letra in pedidas]


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--salida", type=Path, required=True)
    a.add_argument("--roles", nargs="+", default=list(ROLES), choices=list(ROLES))
    a.add_argument("--anchos", nargs="+", type=int, default=[1366, 1056])
    a.add_argument(
        "--letras",
        nargs="+",
        default=[",".join(LETRAS)],
        help="tamaños de letra (con comas o espacios): normal, grande, muy-grande",
    )
    a.add_argument("--rutas", nargs="*", help="ids de página; por omisión todas las de rutas.ts")
    a.add_argument("--sin-axe", action="store_true")
    a.add_argument("--sin-flujo", action="store_true")
    a.add_argument(
        "--sin-recorrido", action="store_true", help="no repite Inicio y Libro con el recorrido"
    )
    a.add_argument("--url", help="servidor ya en marcha (usa las cuentas ficticias por omisión)")
    a.add_argument(
        "--funcional", action="store_true", help="ejecuta la acción principal de cada pantalla"
    )
    a.add_argument("--acciones", type=Path, default=ACCIONES_TOML, help="filas del modo funcional")
    a.add_argument(
        "--solo",
        nargs="*",
        help="modo funcional: solo estas rutas (con espacios o comas), las que requieren y la "
        "siembra; un nombre desconocido o ninguna ruta sale con 1",
    )
    args = a.parse_args(argv)
    if args.funcional:
        return main_funcional(args.salida, args.acciones, args.solo)

    letras = letras_pedidas(args.letras)
    salida: Path = args.salida
    capturas = salida / "capturas"
    capturas.mkdir(parents=True, exist_ok=True)
    rutas = [r for r in rutas_de_la_interfaz() if not args.rutas or r["id"] in args.rutas]
    axe = None if args.sin_axe else bajar_axe(salida)

    temporal = Path(tempfile.mkdtemp(prefix="datos_ux_", dir=salida))  # se borra al final
    claves = sembrar_datos(temporal)
    servidor: Servidor | None = None
    base = args.url.rstrip("/") if args.url else ""
    compilado: dict[str, str] = {}
    if not args.url:
        compilado = congelar_interfaz(temporal / "dist")
        servidor = ServidorCongelado(temporal, puerto_libre(), temporal / "dist")
        base = servidor.url
    resultado: dict[str, Any] = {
        "base": base,
        **compilado,
        "rutas": len(rutas),
        "letras": letras,
        "anchos": args.anchos,
        "axe": bool(axe),
        "pantallas": [],
        "flujos": [],
    }
    libros = libros_ficticios(salida / "libros_ficticios")
    try:
        if servidor:
            servidor.esperar()
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            navegador = lanzar_navegador(p)
            try:
                for rol in args.roles:
                    contexto = navegador.new_context(viewport={"width": 1366, "height": ALTO})
                    pagina = contexto.new_page()
                    entrar(pagina, base, rol, claves[rol])
                    pagina.close()
                    en_menu = ids_del_menu(contexto, base)
                    resultado.setdefault("menu_por_rol", {})[rol] = sorted(en_menu)
                    for letra in letras:
                        for ancho in args.anchos:
                            for ruta in rutas:
                                fila = medir_pantalla(
                                    contexto, base, ruta, ancho, rol, capturas, axe, en_menu, letra
                                )
                                resultado["pantallas"].append(fila)
                                print(
                                    f"{rol:5} {letra:10} {ancho} {ruta['id']:15} "
                                    f"h1={fila.get('h1')} scrollX={fila.get('scroll_x')} "
                                    f"nav={fila.get('modo_nav')} dup={fila.get('duplicados_nav')} "
                                    f"cortada={fila.get('barra_cortada')} "
                                    f"fuera={fila.get('panel_fuera')} {fila.get('ms_hasta_h1')}ms"
                                )
                            # El recorrido empieza al auditar desde el Inicio: solo quien audita.
                            if not args.sin_recorrido and "libros" in en_menu:
                                for fila in medir_con_recorrido(
                                    contexto,
                                    base,
                                    libros["limpio"],
                                    ancho,
                                    rol,
                                    capturas,
                                    axe,
                                    letra,
                                ):
                                    resultado["pantallas"].append(fila)
                                    print(
                                        f"{rol:5} {letra:10} {ancho} recorrido/{fila['id']:9} "
                                        f"h1={fila.get('h1')} columna={fila.get('recorrido_modo')} "
                                        f"visible={fila.get('recorrido_visible')} "
                                        f"solapa={fila.get('recorrido_solapa')} "
                                        f"dup={fila.get('duplicados_nav')} "
                                        f"fuera={fila.get('panel_fuera')} {fila.get('error', '')}"
                                    )
                    if not args.sin_flujo and rol in ("ana", "rita"):
                        if rol == "ana":
                            for clave in ("limpio", "ajeno_control", "csv"):
                                if clave not in libros:
                                    continue
                                for desde in ("libros", "inicio"):
                                    resultado["flujos"].append(
                                        flujo_libros(
                                            contexto,
                                            base,
                                            libros[clave],
                                            capturas,
                                            f"ana_{desde}_{clave}",
                                            desde,
                                        )
                                    )
                        else:
                            for clave in ("limpio", "ajeno_control"):
                                if clave in libros:
                                    resultado["flujos"].append(
                                        flujo_revisar_excel(
                                            contexto, base, libros[clave], capturas, f"rita_{clave}"
                                        )
                                    )
                    contexto.close()
            finally:
                navegador.close()
    finally:
        if servidor:
            servidor.cerrar()
        for _ in range(10):  # Windows suelta las bases un momento después de cerrar el servidor
            shutil.rmtree(temporal, ignore_errors=True)
            if not temporal.exists():
                break
            time.sleep(1)
    resultado["resumen"] = resumir(resultado["pantallas"])
    (salida / "recorrido.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(resultado["resumen"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
