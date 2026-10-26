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
        [--letras normal,grande,muy-grande] [--sidebar oculto,abierto,fijado]
        [--rutas auditoria libros ...] [--especiales] [--umbrales] [--url http://127.0.0.1:8501]

Plan de módulos (MOD-5): cada pantalla se mide en su módulo (Auditoría, Presupuestos y obras,
Producción) con cada tamaño de letra (`--letras`, como lo fija `TamanoLetra`) y cada estado del
sidebar de módulos (`--sidebar oculto,abierto,fijado`: abierto = en capa tras pulsar «Sílice»;
fijado = la preferencia de la cuenta, que solo se ve desde 1366/1708/2049 px según la letra). Las
pantallas que el menú del rol no ofrece se miden solo con el sidebar oculto (H-8). Controles:
`duplicados_nav` (una pantalla repetida en la barra o en el sidebar: 0), `barra_cortada` (la
cabecera se desborda, algo suyo sale de la ventana, las áreas se montan sobre el lado derecho o un
texto con puntos suspensivos queda más corto de lo que su propio tope permite), `panel_fuera` (un
panel de área o el sidebar sale de la ventana, o la barra cedió sus áreas y el sidebar no las
muestra), `sidebar_tapa` (fijado: el contenido empieza antes del borde derecho del sidebar) y que
el sidebar sea el esperado. Libro y el inicio de Auditoría se repiten con el recorrido guiado en
curso para quien puede auditar. La interfaz se sirve desde una copia de `frontend-desktop/dist`.

Medidas aparte (`--especiales`, con `ana`): la mesa de control con datos, sin obras y con un
bloque en error; el panel de la obra y el diálogo de carpetas sin desplazamiento horizontal; Esc en
«Buscar obra»; el foco al cerrar los diálogos; la marca «Demostración» en los tres módulos y la
página de mercado (tabla de observaciones y franja de cifras). Modo `--umbrales`: el menor ancho en
que la barra de cada módulo cabe, por letra y rol, con la obra de nombre más largo de la siembra
(su texto recortado por su propio tope), en la carpeta de la empresa y en la de demostración.

Modo `--funcional` (BS-F, «que todas las herramientas funcionen»): en vez de medir, ejecuta la
acción principal de cada pantalla con la cuenta que la puede usar y comprueba el resultado visible.
Las filas viven en `scripts/recorrido_funcional.toml` (una por pantalla) y cada una entra por el
sidebar de módulos y el área de su módulo en la barra (o en el sidebar, si la barra no cabe), no
por dirección; la carpeta y la obra se eligen con el selector de obra de Presupuestos y obras:

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
# H-10): cualquier otra (ruta, regla) es nueva. El Inicio de entonces ya no existe: su bloque
# «Últimas auditorías» (la región desplazable de rita a 1056 px) vive hoy en el inicio de Auditoría.
AXE_DE_REFERENCIA = {
    ("administracion", "color-contrast"),
    ("inicio", "scrollable-region-focusable"),
    ("auditoria", "scrollable-region-focusable"),
}
# Estados del sidebar de módulos (diseño de módulos §4 y §12.4) y desde qué ancho puede quedar
# fijado con cada letra (`$fijado-desde` de `_umbrales.scss`: 1366 px y 1366 × 1,25 y × 1,5).
SIDEBARS = ("oculto", "abierto", "fijado")
FIJADO_DESDE = {"normal": 1366, "grande": 1708, "muy-grande": 2049}
# Ids del armazón (`src/shell/sidebar.ts` y `SelectorObra.tsx`).
ID_BOTON_SILICE = "silice-boton-modulos"
ID_SIDEBAR = "silice-sidebar"
ID_BOTON_OBRA = "silice-boton-obra"


def rutas_de_la_interfaz() -> list[dict[str, str | None]]:
    """Las páginas de `rutas.ts` (id, título, acción, módulo y área), leídas del texto: es la única
    lista."""
    texto = RUTAS_TS.read_text(encoding="utf-8")
    bloque = texto.split("export const PAGINAS", 1)[1].split("export function paginaPorId", 1)[0]
    paginas: list[dict[str, str | None]] = []
    # Cada entrada se lee campo a campo: el orden de los campos (y los que se agreguen, como
    # `enUnaLinea`) no importa. `ubicacion: en("<modulo>", "<area>")` o `null`.
    for entrada in re.findall(r"\{([^{}]*?\bid:\s*\"[^\"]+\"[^{}]*?)\}", bloque):
        campos = dict(re.findall(r'(\w+):\s*"([^"]*)"', entrada))
        accion = re.search(r"\baccion:\s*(null|\"[^\"]*\")", entrada)
        if "id" not in campos or "titulo" not in campos or accion is None:
            continue
        ubicacion = re.search(r'\bubicacion:\s*en\(\s*"(\w+)",\s*"(\w+)"\s*\)', entrada)
        paginas.append(
            {
                "id": campos["id"],
                "titulo": campos["titulo"],
                "seccion": campos.get("seccion"),
                "accion": None if accion[1] == "null" else accion[1].strip('"'),
                "modulo": ubicacion[1] if ubicacion else None,
                "area": ubicacion[2] if ubicacion else None,
            }
        )
    return paginas


def modulos_de_la_interfaz() -> dict[str, dict[str, Any]]:
    """Los módulos de `rutas.ts` en su orden, con su título y sus áreas (id → título)."""
    texto = RUTAS_TS.read_text(encoding="utf-8")
    bloque = texto.split("export const MODULOS", 1)[1].split("export interface PaginaDef", 1)[0]
    modulos: dict[str, dict[str, Any]] = {}
    patron = r'id:\s*"(\w+)",\s*titulo:\s*"([^"]+)",\s*enUnaLinea:\s*"[^"]*",\s*areas:\s*\[(.*?)\]'
    for id_, titulo, areas in re.findall(patron, bloque, flags=re.DOTALL):
        modulos[id_] = {
            "titulo": titulo,
            "areas": dict(re.findall(r'\{\s*id:\s*"(\w+)",\s*titulo:\s*"([^"]+)"\s*\}', areas)),
        }
    return modulos


def fijado_posible(ancho: int, letra: str) -> bool:
    """Si con ese ancho y esa letra el sidebar puede quedar fijado (si no, es como oculto)."""
    return ancho >= FIJADO_DESDE[letra]


def sidebar_esperado(estado: str, ancho: int, letra: str) -> str | None:
    """Cómo debe verse el sidebar en cada estado medido: `capa`, `fijado` o ninguno (`None`)."""
    if estado == "abierto":
        return "capa"
    if estado == "fijado" and fijado_posible(ancho, letra):
        return "fijado"
    return None


def camino_por_menu(id_: str) -> dict[str, Any]:
    """Cómo llega una persona a la pantalla: módulo en el sidebar, área en la barra y la pantalla
    (o, fuera de los módulos, la entrada del pie del sidebar)."""
    pagina = next((r for r in rutas_de_la_interfaz() if r["id"] == id_), None)
    if pagina is None:
        raise ValueError(f"no hay pantalla «{id_}» en rutas.ts")
    if pagina["modulo"] is None:
        return {"modulo": None, "area": None, "pantalla": pagina["titulo"], "inicio": False}
    modulo = modulos_de_la_interfaz()[pagina["modulo"]]
    return {
        "modulo": modulo["titulo"],
        "area": modulo["areas"][pagina["area"]],
        "pantalla": pagina["titulo"],
        "inicio": pagina["area"] == "inicio",
    }


def umbral_medido(caben: dict[int, bool]) -> float | None:
    """El umbral de `_umbrales.scss` (max-width) que sale de la medida: la barra debe ceder sus
    áreas por debajo del menor ancho desde el que cabe en TODOS los anchos medidos (una media
    consulta puede hacerla caber en un ancho y no en otro mayor). `None` si no cabe ni en el
    mayor."""
    anchos = sorted(caben)
    if not anchos or not caben[anchos[-1]]:
        return None
    desde = anchos[-1]
    for ancho in reversed(anchos):
        if not caben[ancho]:
            break
        desde = ancho
    return round(desde - 0.02, 2)


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


API_JS = """async ([metodo, ruta, cuerpo]) => {
  const s = await (await fetch('/v1/sesion', {credentials: 'same-origin'})).json();
  const cabeceras = {'X-Silice-CSRF': s.csrf || ''};
  if (cuerpo !== null) cabeceras['Content-Type'] = 'application/json';
  const r = await fetch(ruta, {method: metodo, credentials: 'same-origin', headers: cabeceras,
    body: cuerpo === null ? undefined : JSON.stringify(cuerpo)});
  let datos = null;
  try { datos = await r.json(); } catch (e) { datos = null; }
  return {estado: r.status, datos};
}"""


def api(pagina: Any, metodo: str, ruta: str, cuerpo: Any = None) -> dict[str, Any]:
    """Una llamada a la API con la sesión de la página (cookie y anti-CSRF de `GET /v1/sesion`).
    Solo prepara el escenario de una medida (preferencias, carpeta, obra); lo que se juzga se
    hace con clics."""
    return pagina.evaluate(API_JS, [metodo, ruta, cuerpo])


def api_del_contexto(contexto: Any, base: str, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
    pagina = contexto.new_page()
    try:
        pagina.goto(f"{base}/app/", wait_until="domcontentloaded")
        return api(pagina, metodo, ruta, cuerpo)
    finally:
        pagina.close()


def fijar_sidebar_de_la_cuenta(contexto: Any, base: str, fijado: bool) -> None:
    """La preferencia `sidebar_fijado` de la cuenta (la lee el armazón al cargar)."""
    r = api_del_contexto(
        contexto, base, "PUT", "/v1/sesion/preferencias", {"sidebar_fijado": fijado}
    )
    if r["estado"] != 204:
        raise RuntimeError(f"no se pudo guardar sidebar_fijado={fijado}: {r}")


def abrir_sidebar(pagina: Any) -> None:
    """Pulsa «Sílice» si el sidebar no está a la vista (en capa o fijado) y espera a verlo."""
    lado = pagina.locator(f"#{ID_SIDEBAR}")
    if lado.count() and lado.first.is_visible():
        return
    pagina.locator(f"#{ID_BOTON_SILICE}").click(timeout=LIMITE_PASO_MS)
    lado.first.wait_for(state="visible", timeout=LIMITE_PASO_MS)


def _hrefs(pagina: Any, selector: str) -> list[str]:
    hrefs = pagina.eval_on_selector_all(
        selector, "els => els.map(a => a.getAttribute('href') || '')"
    )
    return [h.split("#/")[-1].strip("/") for h in hrefs if h]


def ids_del_menu(contexto: Any, base: str) -> set[str]:
    """Las pantallas que el menú ofrece a la sesión de este contexto, leídas como las encuentra una
    persona: los módulos y el pie del sidebar y, módulo por módulo, sus áreas (la sección «Áreas de
    …» del sidebar lista las mismas pantallas que la barra)."""
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 1366, "height": ALTO})
    pagina.goto(f"{base}/app/#/", wait_until="domcontentloaded")
    pagina.wait_for_selector("main h1", timeout=LIMITE_CARGA_MS)
    abrir_sidebar(pagina)
    inicios = _hrefs(pagina, f"#{ID_SIDEBAR} a.silice-sidebar__modulo")
    ids = set(inicios) | set(_hrefs(pagina, f"#{ID_SIDEBAR} .silice-sidebar__pie a"))
    for inicio in inicios:
        ir_por_hash(pagina, inicio)
        abrir_sidebar(pagina)
        ids |= set(_hrefs(pagina, f"#{ID_SIDEBAR} .silice-sidebar__areas a"))
    pagina.close()
    return ids


# Por qué la barra no cabe (vacío si cabe), con la navegación medida (`nav`) o sin ella (`null`, la
# barra ya cedió sus áreas). Va dentro de `NAV_JS` y de `CABE_JS` (la medida de umbrales):
# Playwright evalúa una sola función.
MOTIVOS_DE_CORTE_JS = """function motivosDeCorte(header, nav) {
  const de = document.documentElement, ancho = de.clientWidth;
  const limpio = t => (t || '').replace(/\\s+/g, ' ').trim();
  const caja = r => [r.left, r.top, r.right, r.bottom].map(Math.round);
  const visible = el => { if (!el) return false; const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
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
    for (const el of header.querySelectorAll('a, button')) {
      if (!visible(el) || el.closest('.silice-panel-area')) continue;
      // Solo el área actual tiene holgura: su raya (::after) sobresale 2 px a propósito.
      const holgura = el.classList.contains('silice-barra__area--actual') ? 2 : 0;
      if (getComputedStyle(el).overflowX === 'visible' && el.scrollWidth > el.clientWidth + holgura)
        motivos.push('«' + limpio(el.textContent).slice(0, 30) + '» se sale de su botón ('
          + el.scrollWidth + ' de ' + el.clientWidth + ' px)');
    }
    for (const el of header.querySelectorAll('*')) {
      if (!visible(el) || el.closest('.silice-panel-area')) continue;
      const cs = getComputedStyle(el);
      if (cs.textOverflow !== 'ellipsis') continue;
      // Sin holgura y en fracciones de píxel: el ancho del texto (un Range da su caja completa,
      // aunque la vista lo corte) frente al hueco de contenido de su caja. Recortado por su propio
      // tope (`max-inline-size`) es a propósito y no cuenta.
      const rango = document.createRange();
      rango.selectNodeContents(el);
      const texto = rango.getBoundingClientRect().width;
      const caja = el.getBoundingClientRect().width;
      const relleno = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight)
        + parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
      if (texto <= caja - relleno + 0.01) continue;
      const tope = cs.maxWidth.endsWith('px') ? parseFloat(cs.maxWidth) : Infinity;
      const medida = cs.boxSizing === 'border-box' ? caja : caja - relleno;
      if (medida >= tope - 0.01) continue;
      motivos.push('«' + limpio(el.textContent).slice(0, 30) + '» recortado a '
        + (caja - relleno).toFixed(1) + ' de ' + texto.toFixed(1) + ' px');
    }
    const global = header.querySelector('.cds--header__global');
    const items = nav ? [...nav.querySelectorAll('.silice-barra__item')] : [];
    if (global && items.length) {
      const hijos = [...global.children].filter(visible);
      const borde = Math.min(...hijos.map(h => h.getBoundingClientRect().left));
      const ultimo = items[items.length - 1].getBoundingClientRect();
      if (ultimo.right > borde + 1) motivos.push('las áreas se montan sobre el lado derecho');
    }
  }
  return motivos;
}"""


# Controles de la barra superior y del sidebar de módulos sobre la pantalla ya cargada. Abre cada
# área con su botón (el mismo `onClick` de React que un clic), mide su panel y lo cierra. Si la
# barra cedió sus áreas (umbral del módulo y la letra), abre el sidebar con «Sílice» y comprueba
# que las muestra. Las listas de nombres (barra y sidebar) se revisan por separado: cada pantalla
# debe salir una sola vez en cada una. Un texto con puntos suspensivos de la cabecera cuenta como
# barra cortada si queda más corto que su propio tope (el nombre de la obra se recorta a 18 rem a
# propósito; más corto es que la barra lo aprieta).
NAV_JS = (
    """async ({paneles}) => {
"""
    + MOTIVOS_DE_CORTE_JS
    + """
  const cuadros = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  const de = document.documentElement, ancho = de.clientWidth, alto = window.innerHeight;
  const limpio = t => (t || '').replace(/\\s+/g, ' ').trim();
  const caja = r => [r.left, r.top, r.right, r.bottom].map(Math.round);
  const dentro = r => r.left >= -1 && r.top >= -1 && r.right <= ancho + 1 && r.bottom <= alto + 1;
  const visible = el => { if (!el) return false; const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
  const repetidos = nombres => { const c = {};
    for (const n of nombres) c[n] = (c[n] || 0) + 1;
    return Object.entries(c).filter(([, k]) => k > 1).map(([n, k]) => n + ' x' + k); };
  const header = document.querySelector('header.silice-barra');
  const nav = header && header.querySelector('nav[aria-label="Menú principal"]');
  const marco = document.querySelector('.silice-marco');
  const modulo = header && header.querySelector('.silice-barra__modulo');
  const s = { letra_aplicada: de.dataset.siliceLetra || null,
    modulo: marco ? (marco.dataset.modulo || null) : null,
    modulo_titulo: modulo ? limpio(modulo.textContent) : null,
    modo_nav: visible(nav) ? 'barra' : 'sidebar' };
  const motivos = motivosDeCorte(header, s.modo_nav === 'barra' ? nav : null);
  s.barra_cortada = motivos.length > 0;
  s.barra_motivos = motivos.slice(0, 4);
  const nombresBarra = [], panelesMedidos = [];
  if (s.modo_nav === 'barra') {
    for (const a of nav.querySelectorAll('li.silice-barra__item > a'))
      nombresBarra.push(limpio(a.textContent));
    for (const b of nav.querySelectorAll('button.silice-barra__area')) {
      const area = limpio(b.textContent);
      nombresBarra.push(area);
      if (!paneles) continue;
      if (b.getAttribute('aria-expanded') !== 'true') b.click();
      await cuadros();
      const panel = document.getElementById(b.getAttribute('aria-controls') || '');
      if (!panel) { panelesMedidos.push({ area, abierto: false, dentro: false }); continue; }
      const r = panel.getBoundingClientRect();
      panelesMedidos.push({ area, abierto: true, dentro: dentro(r), caja: caja(r),
        columnas: getComputedStyle(panel.querySelector('ul')).gridTemplateColumns
          .split(' ').length });
      for (const t of panel.querySelectorAll('.silice-panel-area__titulo'))
        nombresBarra.push(limpio(t.textContent));
    }
    const abierto = nav.querySelector('button.silice-barra__area[aria-expanded="true"]');
    if (abierto) { abierto.click(); await cuadros(); }
  }
  s.paneles = panelesMedidos;
  // Sidebar: como estaba al cargar (capa, fijado o ninguno) y, si hace falta, abierto con «Sílice».
  const boton = document.getElementById('silice-boton-modulos');
  let lado = document.getElementById('silice-sidebar');
  s.sidebar_modo = lado ? (lado.getAttribute('role') === 'dialog' ? 'capa' : 'fijado') : null;
  const main = document.querySelector('main#contenido');
  s.sidebar_tapa = false;
  if (s.sidebar_modo === 'fijado' && main) {
    const rl = lado.getBoundingClientRect(), rm = main.getBoundingClientRect();
    s.sidebar_tapa = rm.left < rl.right - 1;
    s.sidebar_caja = caja(rl);
    s.main_caja = caja(rm);
  }
  let abiertoAqui = false;
  if (!lado && boton && visible(boton)) {
    boton.click();
    for (let i = 0; i < 20 && !document.getElementById('silice-sidebar'); i++) await cuadros();
    lado = document.getElementById('silice-sidebar');
    abiertoAqui = Boolean(lado);
  }
  const nombresLado = [], ladoMal = [];
  if (!lado) ladoMal.push('sin sidebar');
  else {
    const r = lado.getBoundingClientRect();
    if (!(r.left >= -1 && r.right <= ancho + 1 && r.top >= -1 && r.bottom <= alto + 1))
      ladoMal.push('sidebar fuera ' + caja(r));
    const salen = [...lado.querySelectorAll('a, button')].filter(visible).filter(e => {
      const q = e.getBoundingClientRect(); return q.left < r.left - 1 || q.right > r.right + 1; });
    if (salen.length) ladoMal.push(salen.length + ' enlaces salen del sidebar');
    const areas = lado.querySelector('.silice-sidebar__areas');
    s.areas_en_sidebar = visible(areas);
    if (s.modo_nav === 'sidebar' && areas && !s.areas_en_sidebar)
      ladoMal.push('la barra cedió sus áreas y el sidebar no las muestra');
    for (const e of lado.querySelectorAll('.silice-sidebar__nombre, .silice-sidebar__rotulo-area,'
        + ' .silice-sidebar__titulo, .silice-sidebar__enlace'))
      nombresLado.push(limpio(e.textContent));
    s.sidebar_ancho = Math.round(r.width);
  }
  if (abiertoAqui) {
    boton.click();
    for (let i = 0; i < 20 && document.getElementById('silice-sidebar'); i++) await cuadros();
  }
  const fueraPaneles = panelesMedidos.filter(p => !p.dentro).map(p => p.area);
  s.panel_fuera = fueraPaneles.length > 0 || ladoMal.length > 0;
  s.paneles_fuera = fueraPaneles.concat(ladoMal);
  const dupBarra = repetidos(nombresBarra), dupLado = repetidos(nombresLado);
  s.duplicados_nav = dupBarra.length + dupLado.length;
  s.duplicados_detalle = { barra: dupBarra, sidebar: dupLado };
  s.nombres_barra = nombresBarra.length;
  s.nombres_sidebar = nombresLado.length;
  return s;
}"""
)

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
    # Chromium avisa `net::ERR_ABORTED` de una petición que ya tuvo respuesta (el 204 de
    # `PUT /v1/sesion/preferencias`, cuyo cuerpo vacío nadie lee): eso no es un fallo de red.
    # Se guarda la petición misma, no su `id()`: una petición nueva podría heredar la dirección
    # de una ya liberada y su fallo se perdería.
    respondidas: list[Any] = []

    def al_responder(r: Any) -> None:
        respondidas.append(r.request)
        if r.status >= 400:
            red.append(f"{r.status} {r.request.method} {r.url[:120]}")

    def al_fallar(r: Any) -> None:
        if not any(r is q for q in respondidas):
            red.append(f"FALLA {r.method} {r.url[:120]} {r.failure}")

    pagina.on("console", lambda m: consola.append(m.text[:200]) if m.type == "error" else None)
    pagina.on("pageerror", lambda e: consola.append(f"pageerror: {str(e)[:200]}"))
    pagina.on("response", al_responder)
    pagina.on("requestfailed", al_fallar)


def _medir_cargada(
    pagina: Any, fila: dict[str, Any], axe: str | None, captura: Path, paneles: bool = True
) -> None:
    """Medidas, axe, captura y controles de la barra y el sidebar de una pantalla ya cargada."""
    en_menu = fila.get("en_menu")
    fila.update(pagina.evaluate(MEDIR_JS))
    fila["en_menu"] = en_menu
    if axe:
        try:
            pagina.evaluate(axe)
            fila["axe"] = pagina.evaluate(
                "async () => (await axe.run(document, "
                "{runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}))"
                ".violations.map(v => ({id: v.id, impacto: v.impact, nodos: v.nodes.length,"
                " objetivos: v.nodes.slice(0, 3).map(n => n.target.join(' '))}))"
            )
        except Exception as error:
            fila["axe_error"] = str(error)[:150]
    pagina.screenshot(path=str(captura), full_page=True)
    fila["captura"] = captura.name
    # Después de axe y de la captura, para que sean comparables con la corrida de referencia.
    fila.update(pagina.evaluate(NAV_JS, {"paneles": paneles}))


def capturar_paneles(pagina: Any, prefijo: str, capturas: Path) -> list[str]:
    """Una captura con cada panel de área abierto y otra con el sidebar en capa (o fijado), con
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
    if not pagina.locator(f"#{ID_SIDEBAR}").count():
        pagina.locator(f"#{ID_BOTON_SILICE}").click()
        pagina.wait_for_timeout(250)
        destino = capturas / f"{prefijo}_sidebar_capa.png"
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
    sidebar: str = "oculto",
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
        "sidebar": sidebar,
        "sidebar_esperado": sidebar_esperado(sidebar, ancho, letra),
        "id": ruta["id"],
        "titulo": ruta["titulo"],
        "seccion": ruta["seccion"],
        "accion": ruta["accion"],
        "modulo_de_la_ruta": ruta.get("modulo"),
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
        if sidebar == "abierto":
            abrir_sidebar(pagina)
        captura = capturas / f"{rol}_{ancho}_{letra}_{sidebar}_{ruta['id']}.png"
        _medir_cargada(pagina, fila, axe, captura, paneles=sidebar != "abierto")
        if sidebar == "abierto":
            # Esc cierra la capa y el foco vuelve a «Sílice» (MOD-2).
            pagina.keyboard.press("Escape")
            pagina.wait_for_timeout(150)
            fila["foco_tras_cerrar_sidebar"] = pagina.evaluate(
                "id => !document.getElementById('silice-sidebar')"
                " && document.activeElement && document.activeElement.id === id",
                ID_BOTON_SILICE,
            )
        if ruta.get("area") == "inicio" and sidebar == "oculto":
            fila["capturas_paneles"] = capturar_paneles(
                pagina, f"{rol}_{ancho}_{letra}_{ruta['id']}", capturas
            )
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
    """Inicio de Auditoría → soltar el libro → «Auditar con recorrido guiado»: mide Libro con el
    recorrido en curso y vuelve al inicio sin recargar (el recorrido vive en la memoria de la
    interfaz)."""
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": ancho, "height": ALTO})
    fijar_letra(pagina, letra)
    consola: list[str] = []
    red: list[str] = []
    _escuchar(pagina, consola, red)
    filas: list[dict[str, Any]] = []
    base_fila = {
        "rol": rol,
        "ancho": ancho,
        "letra": letra,
        "sidebar": "oculto",
        "sidebar_esperado": None,
        "recorrido": True,
        "en_menu": True,
    }
    try:
        pagina.goto(f"{base}/app/#/auditoria", wait_until="domcontentloaded")
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
        for id_ in ("libros", "auditoria"):
            if id_ == "auditoria":
                ir_por_hash(pagina, "auditoria")
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


# --------------------------- medidas aparte (MOD-5) ----------------------------------------------
#
# Lo que pidieron los árbitros de MOD-3b, MOD-4b y T15: la mesa a 1056 px, el panel de la obra y el
# diálogo de carpetas sin desplazamiento horizontal, Esc en «Buscar obra», el foco al cerrar los
# diálogos, la marca «Demostración» y la página de mercado. El escenario (carpeta, obra, una
# observación de mercado) se prepara por la API; lo medido se hace con clics.

CARPETA_DEMOSTRACION = "demostracion.db"

ESCENARIO_JS = """() => {
  const de = document.documentElement;
  return { scroll_x: de.scrollWidth > de.clientWidth, scroll_width: de.scrollWidth,
    client_width: de.clientWidth, h1: document.querySelectorAll('h1').length };
}"""

# Rectángulo de un elemento frente a la ventana y su propio desplazamiento horizontal.
CAJA_JS = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return { existe: false };
  const r = el.getBoundingClientRect(), de = document.documentElement;
  return { existe: true, caja: [r.left, r.top, r.right, r.bottom].map(Math.round),
    ancho: Math.round(r.width),
    dentro: r.left >= -1 && r.top >= -1 && r.right <= de.clientWidth + 1
      && r.bottom <= window.innerHeight + 1,
    desborda_dentro: el.scrollWidth > el.clientWidth + 1,
    scroll_x: de.scrollWidth > de.clientWidth, rem: parseFloat(getComputedStyle(de).fontSize) };
}"""

MESA_JS = """() => {
  const de = document.documentElement;
  const rej = document.querySelector('.silice-mesa__rejilla');
  const tabla = document.querySelector('.silice-mesa__tabla table');
  let cont = tabla ? tabla.parentElement : null;
  while (cont && cont !== document.body) {
    const o = getComputedStyle(cont).overflowX;
    if (o === 'auto' || o === 'scroll') break;
    cont = cont.parentElement;
  }
  if (cont === document.body) cont = null;
  const pend = document.querySelector('.silice-mesa__pendientes');
  const princ = document.querySelector('.silice-mesa__principal');
  const al_lado = Boolean(pend && princ)
    && pend.getBoundingClientRect().left >= princ.getBoundingClientRect().right - 1;
  const textos = sel => [...document.querySelectorAll(sel)]
    .map(e => e.textContent.replace(/\\s+/g, ' ').trim()).filter(Boolean);
  return {
    columnas_mesa: rej ? getComputedStyle(rej).gridTemplateColumns.split(' ').length : 0,
    pendientes_al_lado: al_lado,
    scroll_x: de.scrollWidth > de.clientWidth,
    filas_de_obras: tabla ? tabla.querySelectorAll('tbody tr').length : 0,
    tabla_ancho: tabla ? Math.round(tabla.scrollWidth) : null,
    contenedor_ancho: cont ? cont.clientWidth : null,
    tabla_desplaza_dentro: Boolean(cont) && cont.scrollWidth > cont.clientWidth + 1,
    tabla_cabe: Boolean(tabla) && (!cont || cont.scrollWidth <= cont.clientWidth + 1),
    h2: textos('main h2'),
    avisos: textos('main [role=alert], main .cds--inline-notification'),
    cifras: document.querySelectorAll('.silice-mesa__cifra:not(.silice-mesa__cifra--esqueleto)')
      .length,
  };
}"""

MERCADO_JS = """() => {
  const de = document.documentElement;
  const tabla = document.querySelector('.silice-mercado table');
  let cont = tabla ? tabla.parentElement : null;
  while (cont && cont !== document.body) {
    const o = getComputedStyle(cont).overflowX;
    if (o === 'auto' || o === 'scroll') break;
    cont = cont.parentElement;
  }
  if (cont === document.body) cont = null;
  const franja = document.querySelector('.silice-mercado__cifras');
  return {
    columnas_tabla: tabla ? tabla.querySelectorAll('thead th').length : 0,
    filas_tabla: tabla ? tabla.querySelectorAll('tbody tr').length : 0,
    cifras_franja: franja ? franja.querySelectorAll('.silice-mercado__cifra').length : 0,
    filas_de_la_franja: franja ? new Set([...franja.querySelectorAll('.silice-mercado__cifra')]
      .map(c => Math.round(c.getBoundingClientRect().top))).size : 0,
    scroll_x: de.scrollWidth > de.clientWidth,
    tabla_desplaza_dentro: Boolean(cont) && cont.scrollWidth > cont.clientWidth + 1,
  };
}"""


def _foco_en(pagina: Any, id_: str) -> bool:
    return bool(
        pagina.evaluate(
            "id => Boolean(document.activeElement) && document.activeElement.id === id", id_
        )
    )


def _ir_y_esperar(pagina: Any, base: str, ruta: str) -> None:
    pagina.goto(f"{base}/app/#/{ruta}", wait_until="domcontentloaded")
    pagina.wait_for_selector("main h1:not([data-esqueleto])", timeout=LIMITE_CARGA_MS)
    with contextlib.suppress(Exception):
        pagina.wait_for_load_state("networkidle", timeout=4000)


def escenario_de_obras(contexto: Any, base: str) -> dict[str, Any]:
    """Las carpetas sembradas con sus obras: la que tiene más obras (mesa con datos), la obra de
    nombre más largo (umbrales) y la carpeta de la empresa (sin obras)."""
    pagina = contexto.new_page()
    try:
        pagina.goto(f"{base}/app/", wait_until="domcontentloaded")
        casos = api(pagina, "GET", "/v1/casos")["datos"]
        empresa = casos["actual"]["nombre"]
        obras: dict[str, list[dict[str, Any]]] = {}
        cifras: dict[str, int] = {}
        for caso in casos["casos"]:
            nombre = caso["nombre"]
            if api(pagina, "POST", "/v1/casos/actual", {"nombre": nombre})["estado"] != 200:
                continue
            respuesta = api(pagina, "GET", "/v1/proyectos")
            obras[nombre] = respuesta["datos"] if respuesta["estado"] == 200 else []
            resumen = api(pagina, "GET", "/v1/obras/resumen")["datos"] or {}
            cifras[nombre] = len(resumen.get("cifras") or [])
        api(pagina, "DELETE", "/v1/casos/actual")
    finally:
        pagina.close()
    # La mesa «con datos»: la carpeta con más cifras (obras en ejecución) y, a igualdad, más obras.
    con_obras = max(obras, key=lambda c: (cifras.get(c, 0), len(obras[c])))
    larga = max(
        ((c, o) for c, lista in obras.items() for o in lista), key=lambda par: len(par[1]["nombre"])
    )
    return {
        "empresa": empresa,
        "obras_por_carpeta": {c: [o["nombre"] for o in lista] for c, lista in obras.items()},
        "cifras_por_carpeta": cifras,
        "carpeta_con_obras": con_obras,
        "carpeta_obra_larga": larga[0],
        "obra_larga": larga[1]["codigo"],
        "obra_larga_nombre": larga[1]["nombre"],
    }


def elegir_por_api(contexto: Any, base: str, carpeta: str | None, obra: str | None) -> None:
    """Carpeta (`None` = la de la empresa) y obra de la cuenta, para preparar una medida."""
    pagina = contexto.new_page()
    try:
        pagina.goto(f"{base}/app/", wait_until="domcontentloaded")
        r = (
            api(pagina, "DELETE", "/v1/casos/actual")
            if carpeta is None
            else api(pagina, "POST", "/v1/casos/actual", {"nombre": carpeta})
        )
        if r["estado"] not in (200, 204):
            raise RuntimeError(f"no se pudo abrir la carpeta {carpeta}: {r}")
        api(pagina, "PUT", "/v1/sesion/proyecto", {"proyecto": obra})
    finally:
        pagina.close()


def estrenar_demostracion(contexto: Any, base: str) -> dict[str, Any]:
    """`POST /v1/casos/demostracion` (la primera vez tarda hasta dos minutos) y sus obras."""
    pagina = contexto.new_page()
    try:
        pagina.goto(f"{base}/app/", wait_until="domcontentloaded")
        pagina.set_default_timeout(240_000)
        r = api(pagina, "POST", "/v1/casos/demostracion")
        if r["estado"] not in (200, 201):
            return {"estado": r["estado"], "detalle": r["datos"]}
        nombre = r["datos"]["nombre"]
        api(pagina, "POST", "/v1/casos/actual", {"nombre": nombre})
        proyectos = api(pagina, "GET", "/v1/proyectos")["datos"] or []
        carpeta = api(pagina, "GET", "/v1/carpeta")["datos"]
        api(pagina, "DELETE", "/v1/casos/actual")
        return {
            "estado": r["estado"],
            "nombre": nombre,
            "obras": [(o["codigo"], o["nombre"]) for o in proyectos],
            "moneda": (carpeta or {}).get("moneda"),
        }
    finally:
        pagina.close()


def _nueva_pagina(contexto: Any, ancho: int, letra: str) -> tuple[Any, list[str], list[str]]:
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": ancho, "height": ALTO})
    fijar_letra(pagina, letra)
    consola: list[str] = []
    red: list[str] = []
    _escuchar(pagina, consola, red)
    return pagina, consola, red


def medir_mesa(
    contexto: Any, base: str, capturas: Path, ancho: int, letra: str, escenario: dict[str, Any]
) -> list[dict[str, Any]]:
    """La mesa con datos, con el bloque de pendientes en error (500 simulado) y sin obras."""
    filas: list[dict[str, Any]] = []
    casos = [
        ("mesa_con_datos", escenario["carpeta_con_obras"], False),
        ("mesa_bloque_en_error", escenario["carpeta_con_obras"], True),
        ("mesa_sin_obras", None, False),
    ]
    for nombre, carpeta, con_error in casos:
        elegir_por_api(contexto, base, carpeta, None)
        pagina, consola, red = _nueva_pagina(contexto, ancho, letra)
        fila: dict[str, Any] = {
            "medida": nombre,
            "ancho": ancho,
            "letra": letra,
            "carpeta": carpeta,
        }
        try:
            if con_error:
                pagina.route(
                    "**/v1/obras/pendientes",
                    lambda r: r.fulfill(
                        status=500,
                        content_type="application/json",
                        body=json.dumps({"detail": "Fallo simulado por el recorrido visual."}),
                    ),
                )
            _ir_y_esperar(pagina, base, "obras")
            pagina.wait_for_timeout(600)
            fila.update(pagina.evaluate(MESA_JS))
            fila["desbordan"] = pagina.evaluate(MEDIR_JS)["desbordan"]
            captura = capturas / f"ana_{ancho}_{letra}_{nombre}.png"
            pagina.screenshot(path=str(captura), full_page=True)
            fila["captura"] = captura.name
        except Exception as error:
            fila["error"] = str(error)[:300]
        fila["consola"] = consola[:6]
        fila["red"] = red[:6]
        pagina.close()
        filas.append(fila)
    return filas


def medir_selector_y_dialogos(
    contexto: Any, base: str, capturas: Path, ancho: int, letra: str, escenario: dict[str, Any]
) -> dict[str, Any]:
    """Panel de la obra (22 rem), Esc en «Buscar obra», diálogo de carpetas (44 rem) y «Nueva
    obra», y a dónde vuelve el foco al cerrar cada uno."""
    elegir_por_api(contexto, base, escenario["carpeta_obra_larga"], escenario["obra_larga"])
    pagina, consola, red = _nueva_pagina(contexto, ancho, letra)
    fila: dict[str, Any] = {"medida": "selector_y_dialogos", "ancho": ancho, "letra": letra}
    prefijo = capturas / f"ana_{ancho}_{letra}"
    boton = pagina.locator(f"#{ID_BOTON_OBRA}")
    try:
        _ir_y_esperar(pagina, base, "catalogo")
        fila["boton_obra"] = boton.get_attribute("aria-label")
        boton.click()
        fila["panel_obra"] = pagina.evaluate(CAJA_JS, ".silice-obra__panel")
        pagina.screenshot(path=f"{prefijo}_panel_obra.png")
        busqueda = pagina.get_by_role("searchbox", name="Buscar obra")
        busqueda.fill("zz")
        busqueda.press("Escape")
        pagina.wait_for_timeout(150)
        fila["esc_buscar_cierra_panel"] = pagina.locator(".silice-obra__panel").count() == 0
        fila["foco_tras_esc_buscar"] = _foco_en(pagina, ID_BOTON_OBRA)

        boton.click()
        pagina.get_by_role("button", name="Cambiar carpeta…").click()
        dialogo = pagina.get_by_role("dialog", name="Carpetas de trabajo")
        dialogo.wait_for(state="visible", timeout=LIMITE_PASO_MS)
        pagina.locator(".silice-carpetas__lista").wait_for(timeout=LIMITE_PASO_MS)
        fila["dialogo_carpetas"] = pagina.evaluate(CAJA_JS, ".silice-dialogo")
        fila["dialogo_carpetas_cuerpo"] = pagina.evaluate(CAJA_JS, ".silice-dialogo__cuerpo")
        pagina.screenshot(path=f"{prefijo}_dialogo_carpetas.png")
        pagina.keyboard.press("Escape")
        pagina.wait_for_timeout(150)
        fila["esc_cierra_carpetas"] = dialogo.count() == 0
        fila["foco_tras_carpetas_esc"] = _foco_en(pagina, ID_BOTON_OBRA)
        boton.click()
        pagina.get_by_role("button", name="Cambiar carpeta…").click()
        dialogo.wait_for(state="visible", timeout=LIMITE_PASO_MS)
        dialogo.get_by_role("button", name="Cerrar", exact=True).click()
        pagina.wait_for_timeout(150)
        fila["foco_tras_carpetas_cerrar"] = _foco_en(pagina, ID_BOTON_OBRA)

        boton.click()
        pagina.locator(".silice-obra__panel").get_by_role("button", name="Nueva obra").click()
        nueva = pagina.get_by_role("dialog", name="Nueva obra")
        nueva.wait_for(state="visible", timeout=LIMITE_PASO_MS)
        fila["dialogo_nueva_obra"] = pagina.evaluate(CAJA_JS, ".silice-dialogo")
        pagina.screenshot(path=f"{prefijo}_dialogo_nueva_obra.png")
        nueva.get_by_role("button", name="Cancelar", exact=True).click()
        pagina.wait_for_timeout(150)
        fila["foco_tras_nueva_obra"] = _foco_en(pagina, ID_BOTON_OBRA)
        fila.update(pagina.evaluate(ESCENARIO_JS))
    except Exception as error:
        fila["error"] = str(error)[:300]
    fila["consola"] = consola[:6]
    fila["red"] = red[:6]
    pagina.close()
    return fila


def medir_marca_demostracion(
    contexto: Any, base: str, capturas: Path, ancho: int, letra: str, demo: str
) -> list[dict[str, Any]]:
    """La marca «Demostración» en la barra de los tres módulos: a la vista, con su texto, dentro
    de la ventana, sin cortar la barra; su panel dentro de la ventana y el foco al cerrarlo."""
    elegir_por_api(contexto, base, demo, None)
    filas: list[dict[str, Any]] = []
    for modulo in ("auditoria", "obras", "produccion"):
        pagina, consola, red = _nueva_pagina(contexto, ancho, letra)
        fila: dict[str, Any] = {"medida": f"marca_{modulo}", "ancho": ancho, "letra": letra}
        try:
            _ir_y_esperar(pagina, base, modulo)
            marca = pagina.locator(".silice-demo__boton")
            fila["marca"] = pagina.evaluate(CAJA_JS, ".silice-demo__boton")
            fila["marca_texto_visible"] = (
                marca.count() > 0 and marca.get_by_text("Demostración", exact=True).is_visible()
            )
            fila.update(pagina.evaluate(NAV_JS, {"paneles": False}))
            pagina.screenshot(path=str(capturas / f"ana_{ancho}_{letra}_marca_{modulo}.png"))
            if marca.count():
                marca.click()
                fila["panel_marca"] = pagina.evaluate(CAJA_JS, ".silice-demo__panel")
                pagina.keyboard.press("Escape")
                pagina.wait_for_timeout(150)
                fila["foco_tras_marca"] = pagina.evaluate(
                    "() => Boolean(document.activeElement)"
                    " && document.activeElement.classList.contains('silice-demo__boton')"
                )
        except Exception as error:
            fila["error"] = str(error)[:300]
        fila["consola"] = consola[:6]
        fila["red"] = red[:6]
        pagina.close()
        filas.append(fila)
    elegir_por_api(contexto, base, None, None)
    return filas


def preparar_mercado(contexto: Any, base: str, carpeta: str) -> dict[str, Any]:
    """Moneda de la carpeta (si falta) y dos observaciones ficticias del primer insumo."""
    elegir_por_api(contexto, base, carpeta, None)
    pagina = contexto.new_page()
    try:
        pagina.goto(f"{base}/app/", wait_until="domcontentloaded")
        moneda = (api(pagina, "GET", "/v1/carpeta")["datos"] or {}).get("moneda")
        declarada = None
        if not moneda:
            declarada = api(pagina, "PUT", "/v1/carpeta/moneda", {"moneda": "Bs"})["estado"]
        insumos = api(pagina, "GET", "/insumos")["datos"] or []
        if not insumos:
            return {"error": "la carpeta no tiene insumos"}
        insumo = insumos[0]
        hoy = time.strftime("%Y-%m-%d")
        creadas = [
            api(
                pagina,
                "POST",
                "/v1/mercado/observaciones",
                {
                    "lado": "compra",
                    "codigo": insumo["codigo"],
                    "fuente_tipo": "proveedor",
                    "fuente": f"Proveedor ficticio {letra_}",
                    "fecha": hoy,
                    "precio": precio,
                    "nota": "Observación ficticia del recorrido visual",
                },
            )
            for letra_, precio in (("A", "120,50"), ("B", "131,25"))
        ]
        return {
            "carpeta": carpeta,
            "moneda": moneda,
            "moneda_declarada": declarada,
            "insumo": insumo["codigo"],
            "descripcion": insumo.get("descripcion", ""),
            "observaciones": [c["estado"] for c in creadas],
            "rechazo": next((c["datos"] for c in creadas if c["estado"] != 201), None),
        }
    finally:
        pagina.close()


def medir_mercado(
    contexto: Any, base: str, capturas: Path, ancho: int, letra: str, mercado: dict[str, Any]
) -> dict[str, Any]:
    """Estudio de mercado con un insumo elegido: tabla de observaciones y franja de cifras."""
    elegir_por_api(contexto, base, mercado["carpeta"], None)
    pagina, consola, red = _nueva_pagina(contexto, ancho, letra)
    fila: dict[str, Any] = {"medida": "mercado", "ancho": ancho, "letra": letra}
    try:
        _ir_y_esperar(pagina, base, "mercado")
        campo = pagina.locator("main [role=combobox]").first
        campo.fill(mercado["insumo"])
        opcion = pagina.get_by_role("option").first
        opcion.wait_for(state="visible", timeout=LIMITE_PASO_MS)
        opcion.click()
        pagina.get_by_text("Cifras de los últimos", exact=False).first.wait_for(
            timeout=LIMITE_PASO_MS
        )
        pagina.wait_for_timeout(400)
        fila.update(pagina.evaluate(MERCADO_JS))
        fila["desbordan"] = pagina.evaluate(MEDIR_JS)["desbordan"]
        captura = capturas / f"ana_{ancho}_{letra}_mercado.png"
        pagina.screenshot(path=str(captura), full_page=True)
        fila["captura"] = captura.name
    except Exception as error:
        fila["error"] = str(error)[:300]
    fila["consola"] = consola[:6]
    fila["red"] = red[:6]
    pagina.close()
    return fila


def medir_especiales(
    contexto: Any, base: str, capturas: Path, anchos: list[int], letras: list[str]
) -> dict[str, Any]:
    """Todas las medidas aparte, con la cuenta `ana` (la única que ve todo lo medido)."""
    fijar_sidebar_de_la_cuenta(contexto, base, False)
    escenario = escenario_de_obras(contexto, base)
    demo = estrenar_demostracion(contexto, base)
    salida: dict[str, Any] = {"escenario": escenario, "demostracion": demo, "medidas": []}
    carpeta_mercado = demo.get("nombre") or escenario["carpeta_con_obras"]
    salida["mercado"] = preparar_mercado(contexto, base, carpeta_mercado)
    for letra in letras:
        for ancho in anchos:
            medidas = salida["medidas"]
            medidas += medir_mesa(contexto, base, capturas, ancho, letra, escenario)
            medidas.append(
                medir_selector_y_dialogos(contexto, base, capturas, ancho, letra, escenario)
            )
            if demo.get("nombre"):
                medidas += medir_marca_demostracion(
                    contexto, base, capturas, ancho, letra, demo["nombre"]
                )
            if "error" not in salida["mercado"]:
                medidas.append(
                    medir_mercado(contexto, base, capturas, ancho, letra, salida["mercado"])
                )
            for m in medidas[-6:]:
                print(f"especial {letra:10} {ancho} {m['medida']:22} {resumen_especial(m)}")
    elegir_por_api(contexto, base, None, None)
    salida["fallos"] = [
        f"{m['ancho']} {m['letra']} {m['medida']}: {f}"
        for m in salida["medidas"]
        for f in fallos_especiales(m)
    ]
    return salida


def fallos_especiales(m: dict[str, Any]) -> list[str]:
    """Lo que una medida aparte deja en rojo (lista vacía si todo está bien)."""
    fallos: list[str] = []
    if "error" in m:
        fallos.append(f"error {m['error']}")
    if m.get("scroll_x"):
        fallos.append("desplazamiento horizontal de la página")
    for clave in ("panel_obra", "dialogo_carpetas", "dialogo_nueva_obra", "marca", "panel_marca"):
        caja = m.get(clave)
        if isinstance(caja, dict) and (not caja.get("existe") or not caja.get("dentro")):
            fallos.append(f"{clave} fuera de la ventana o ausente {caja.get('caja')}")
        if isinstance(caja, dict) and caja.get("scroll_x"):
            fallos.append(f"{clave}: desplazamiento horizontal de la página")
    marca = m.get("marca")
    if isinstance(marca, dict) and marca.get("desborda_dentro"):
        fallos.append(f"el texto de la marca se sale de su botón de {marca.get('ancho')} px")
    cuerpo = m.get("dialogo_carpetas_cuerpo")
    if isinstance(cuerpo, dict) and cuerpo.get("desborda_dentro"):
        fallos.append("el cuerpo del diálogo de carpetas se desplaza a lo ancho")
    for clave in (
        "esc_buscar_cierra_panel",
        "foco_tras_esc_buscar",
        "esc_cierra_carpetas",
        "foco_tras_carpetas_esc",
        "foco_tras_carpetas_cerrar",
        "foco_tras_nueva_obra",
        "marca_texto_visible",
        "foco_tras_marca",
    ):
        if clave in m and not m[clave]:
            fallos.append(f"{clave} = False")
    if m.get("barra_cortada"):
        fallos.append(f"barra cortada {m.get('barra_motivos')}")
    if m.get("medida") == "mesa_bloque_en_error" and not m.get("avisos"):
        fallos.append("el bloque en error no muestra su aviso")
    if m.get("medida") == "mercado" and "error" not in m:
        if m.get("cifras_franja") != 6:
            fallos.append(f"franja con {m.get('cifras_franja')} cifras (se esperaban 6)")
        if m.get("columnas_tabla") != 8:
            fallos.append(f"tabla con {m.get('columnas_tabla')} columnas (se esperaban 8)")
    return fallos


def resumen_especial(m: dict[str, Any]) -> str:
    fallos = fallos_especiales(m)
    return "ok" if not fallos else "; ".join(fallos)[:200]


# --------------------------- umbrales de la barra por módulo (MOD-5) ----------------------------

# Muestra la navegación de la barra aunque el umbral actual la esconda (y Carbon por debajo de
# 1056 px): así se mide si cabe, no si está escondida.
FORZAR_BARRA_CSS = (
    "html .silice-marco .silice-barra__nav, html .silice-marco .cds--header__nav "
    "{ display: block !important; }"
)
# Los botones de la obra, la cuenta y la demostración declaran `inline-size: auto`, pero la regla
# `.cds--header__action { inline-size: 3rem }` de Carbon llega después y gana: su texto queda
# recortado a cualquier ancho (defecto anotado en la bitácora de módulos). El umbral se mide también
# con su ancho declarado, el de cuando se corrija, y se fija el mayor de los dos.
ANCHO_DECLARADO_CSS = (
    ".silice-barra .cds--header__action.silice-obra__boton, "
    ".silice-barra .cds--header__action.silice-cuenta__boton, "
    ".silice-barra .cds--header__action.silice-demo__boton { inline-size: auto !important; }"
)
# Un nombre de cuenta ficticio más largo que el tope de `.silice-cuenta__nombre` (10 rem): el umbral
# cuenta con la cuenta de nombre más largo posible, no con «Ana».
CUENTA_LARGA_JS = """() => document.querySelectorAll('.silice-cuenta__nombre').forEach(e => {
  e.textContent = 'Persona Ficticia de Nombre Muy Largo para Medir'; })"""
# Las tres medidas de cada pantalla: tal cual, con la cuenta larga y, además, con el ancho que
# declaran los botones (si D-1 está corregido, debe dar lo mismo que la anterior).
MEDIDAS_DE_UMBRAL = ("tal_cual", "cuenta_larga", "cuenta_larga_y_ancho_declarado")
CABE_JS = (
    """async () => {
"""
    + MOTIVOS_DE_CORTE_JS
    + """
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  const header = document.querySelector('header.silice-barra');
  const nav = header && header.querySelector('nav[aria-label="Menú principal"]');
  return motivosDeCorte(header, nav);
}"""
)
UMBRAL_MINIMO = 1055.98  # por debajo de 1056 px Carbon esconde `cds--header__nav` (66 rem)


def motivos_por_espacio(motivos: list[str], de_fondo: list[str]) -> list[str]:
    """Los motivos de corte que se deben a la falta de ancho: un texto que sale recortado también
    en la ventana más ancha no lo arregla ningún umbral (es un defecto de su componente) y no
    cuenta para medirlo."""

    def clave(motivo: str) -> str:
        return motivo.split("»", 1)[0] if motivo.startswith("«") else motivo

    fijos = {clave(m) for m in de_fondo}
    return [m for m in motivos if clave(m) not in fijos]


# Anchos donde cambian las consultas de la interfaz (texto de la obra y la cuenta, navegación de
# Carbon): se miden siempre, para que un hueco entre dos pasos del barrido no se pierda.
BORDES_DE_CONSULTA = (1366, 1365, 1056, 1055)


def barrido(cabe: Any, desde: int, hasta: int, paso: int) -> dict[int, bool]:
    """Si la barra cabe, medido de `hasta` hacia abajo de `paso` en `paso` px hasta el primer ancho
    en que no cabe; entre ese y el anterior se afina de 1 en 1 (el mayor que no cabe es el que
    fija el umbral; lo de debajo no lo cambia). Se miden también `desde` y los bordes de las
    consultas por encima del corte."""
    caben: dict[int, bool] = {}
    ancho = hasta
    while True:
        caben[ancho] = cabe(ancho)
        if not caben[ancho]:
            for fino in range(min(ancho + paso - 1, hasta), ancho, -1):
                if fino not in caben:
                    caben[fino] = cabe(fino)
                if not caben[fino]:
                    break
            break
        if ancho == desde:
            break
        ancho = max(ancho - paso, desde)
    corte = max((a for a, si in caben.items() if not si), default=desde - 1)
    for borde in BORDES_DE_CONSULTA:
        if corte < borde <= hasta and borde >= desde and borde not in caben:
            caben[borde] = cabe(borde)
    # Si un borde no cabe, se afina también por encima de él, hasta el ancho medido siguiente.
    nuevo = max((a for a, si in caben.items() if not si), default=desde - 1)
    if nuevo > corte:
        siguiente = min((a for a in caben if a > nuevo), default=nuevo + 1)
        for fino in range(siguiente - 1, nuevo, -1):
            caben[fino] = cabe(fino)
            if not caben[fino]:
                break
    return caben


def medir_umbral(pagina: Any, desde: int = 1000, hasta: int = 3000) -> dict[str, Any]:
    """El menor ancho desde el que la barra cabe en todos los anchos (`barrido` de 8 en 8 px y
    afinado de 1 en 1). Lo que sale cortado ya en `hasta` se anota aparte y no cuenta."""
    pagina.set_viewport_size({"width": hasta, "height": ALTO})
    de_fondo = pagina.evaluate(CABE_JS)
    motivos: dict[int, list[str]] = {}

    def cabe(ancho: int) -> bool:
        pagina.set_viewport_size({"width": ancho, "height": ALTO})
        motivos[ancho] = motivos_por_espacio(pagina.evaluate(CABE_JS), de_fondo)
        return not motivos[ancho]

    umbral = umbral_medido(barrido(cabe, desde, hasta, 8))
    cabe_desde = None if umbral is None else round(umbral + 0.02)
    no_cabe = (
        None if cabe_desde is None else max((a for a in motivos if a < cabe_desde), default=None)
    )
    return {
        "umbral": umbral,
        "cabe_desde": cabe_desde,
        "motivos_justo_debajo": motivos.get(no_cabe, []) if no_cabe else [],
        "cortado_a_cualquier_ancho": de_fondo,
    }


def umbral_de_la_fila(umbrales: list[float | None]) -> float | None:
    """El más exigente de las medidas de una misma pantalla; si una no tiene umbral (no cabe ni
    en la ventana más ancha), la fila tampoco."""
    if not umbrales or any(u is None for u in umbrales):
        return None
    return max(u for u in umbrales if u is not None)


def medir_umbrales(
    navegador: Any,
    base: str,
    claves: dict[str, str],
    roles: list[str],
    letras: list[str],
    capturas: Path,
) -> dict[str, Any]:
    """Por rol, carpeta (la de la obra más larga y la de demostración), módulo y letra: el menor
    ancho en que la barra cabe con la obra de nombre más largo elegida."""
    medidas: list[dict[str, Any]] = []
    contexto = navegador.new_context(viewport={"width": 1366, "height": ALTO})
    pagina = contexto.new_page()
    entrar(pagina, base, "ana", claves["ana"])
    pagina.close()
    escenario = escenario_de_obras(contexto, base)
    demo = estrenar_demostracion(contexto, base)
    contexto.close()
    rutas = rutas_de_la_interfaz()
    for rol in roles:
        contexto = navegador.new_context(viewport={"width": 1366, "height": ALTO})
        pagina = contexto.new_page()
        entrar(pagina, base, rol, claves[rol])
        pagina.close()
        fijar_sidebar_de_la_cuenta(contexto, base, False)
        en_menu = ids_del_menu(contexto, base)
        acciones = api_del_contexto(contexto, base, "GET", "/v1/sesion")["datos"]["acciones"]
        carpetas: list[tuple[str, str | None, str | None]] = [("empresa", None, None)]
        if "cambiar_caso" in acciones:
            obra_larga = escenario["obra_larga"] if "leer_proyecto" in acciones else None
            carpetas = [("obra_larga", escenario["carpeta_obra_larga"], obra_larga)]
            if demo.get("nombre"):
                larga_demo = max(demo["obras"], key=lambda o: len(o[1]), default=(None, ""))[0]
                carpetas.append(("demostracion", demo["nombre"], larga_demo))
        for etiqueta, carpeta, obra in carpetas:
            if carpeta is not None:
                elegir_por_api(contexto, base, carpeta, obra)
            for modulo in modulos_de_la_interfaz():
                # Una pantalla del módulo que no sea su inicio: ahí la obra se nombra entera.
                suyas = [r for r in rutas if r["modulo"] == modulo and r["id"] in en_menu]
                if not suyas:
                    continue
                ruta = next((r for r in suyas if r["area"] != "inicio"), suyas[0])
                for letra in letras:
                    pagina = contexto.new_page()
                    fijar_letra(pagina, letra)
                    pagina.set_viewport_size({"width": 3000, "height": ALTO})
                    fila: dict[str, Any] = {
                        "rol": rol,
                        "carpeta": etiqueta,
                        "modulo": modulo,
                        "letra": letra,
                        "ruta": ruta["id"],
                    }
                    try:
                        _ir_y_esperar(pagina, base, ruta["id"])
                        pagina.add_style_tag(content=FORZAR_BARRA_CSS)
                        fila["boton_obra"] = pagina.evaluate(
                            "id => { const b = document.getElementById(id);"
                            " return b ? b.getAttribute('aria-label') : null; }",
                            ID_BOTON_OBRA,
                        )
                        fila["tal_cual"] = medir_umbral(pagina)
                        # La cuenta con un nombre en su tope de 10 rem (solo en esta medida).
                        pagina.evaluate(CUENTA_LARGA_JS)
                        fila["cuenta_larga"] = medir_umbral(pagina)
                        pagina.add_style_tag(content=ANCHO_DECLARADO_CSS)
                        fila["cuenta_larga_y_ancho_declarado"] = medir_umbral(pagina)
                        fila["umbral"] = umbral_de_la_fila(
                            [fila[m]["umbral"] for m in MEDIDAS_DE_UMBRAL]
                        )
                        fila["cabe_desde"] = (
                            None if fila["umbral"] is None else round(fila["umbral"] + 0.02)
                        )
                        if fila["cabe_desde"]:
                            pagina.set_viewport_size({"width": fila["cabe_desde"], "height": ALTO})
                            pagina.screenshot(
                                path=str(capturas / f"umbral_{rol}_{etiqueta}_{modulo}_{letra}.png")
                            )
                    except Exception as error:
                        fila["error"] = str(error)[:300]
                    pagina.close()
                    medidas.append(fila)
                    print(
                        f"umbral {rol:5} {etiqueta:12} {modulo:10} {letra:10} "
                        + " ".join(
                            f"{m} {fila.get(m, {}).get('cabe_desde')}" for m in MEDIDAS_DE_UMBRAL
                        )
                        + f" "
                        f"{fila.get('error', '')}"
                    )
        contexto.close()
    return {
        "escenario": escenario,
        "demostracion": demo,
        "medidas": medidas,
        "umbrales": umbrales_por_modulo(medidas),
        "sin_medir": umbrales_sin_medir(medidas),
    }


def umbrales_por_modulo(medidas: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    """Por módulo y letra, el umbral más exigente de los medidos (roles y carpetas), nunca por
    debajo de 1055,98 px. Una medida sin umbral o con error deja la casilla en `None` (sin
    umbral): no se descarta en silencio (`umbrales_sin_medir` dice cuál y por qué)."""
    grupos: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for m in medidas:
        grupos.setdefault((m["modulo"], m["letra"]), []).append(m)
    salida: dict[str, dict[str, float | None]] = {}
    for (modulo, letra), grupo in grupos.items():
        umbral = umbral_de_la_fila([None if "error" in m else m.get("umbral") for m in grupo])
        salida.setdefault(modulo, {})[letra] = (
            None if umbral is None else max(umbral, UMBRAL_MINIMO)
        )
    return salida


def umbrales_sin_medir(medidas: list[dict[str, Any]]) -> list[str]:
    """Las medidas que dejan su casilla sin umbral, con su causa."""
    salida = []
    for m in medidas:
        cabeza = f"{m['modulo']} {m['letra']} ({m['rol']}, {m['carpeta']})"
        if "error" in m:
            salida.append(f"{cabeza}: error {m['error']}")
        elif m.get("umbral") is None:
            salida.append(f"{cabeza}: no cabe ni en la ventana más ancha")
    return salida


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
    """Subir un libro y esperar la auditoría (desde el inicio de Auditoría o desde «Libro de la
    empresa»; `desde="inicio"` es el inicio del módulo)."""
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
    pagina.goto(f"{base}/app/#/auditoria", wait_until="domcontentloaded")
    pagina.wait_for_selector("h1", timeout=LIMITE_CARGA_MS)
    c.anotar("pantalla", "Inicio de auditoría", pantalla="auditoria")
    c.anotar("decision", "soltar el Excel aquí o ir al área «Auditar» de la barra")
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


def esperar_ruta(pagina: Any, ruta: str) -> None:
    """Hasta que la dirección es la de la pantalla y su h1 (no el del esqueleto) está a la vista."""
    pagina.wait_for_function(
        "r => location.hash === '#/' + r"
        " && document.querySelector('main h1:not([data-esqueleto])') !== null",
        arg=ruta,
        timeout=LIMITE_CARGA_MS,
    )
    with contextlib.suppress(Exception):
        pagina.wait_for_load_state("networkidle", timeout=3000)


def ir_por_menu(pagina: Any, ruta: str) -> str:
    """Como una persona: «Sílice» abre el sidebar, se elige el módulo (va a su inicio) y, en la
    barra, el área y la pantalla de su panel; si la barra cedió sus áreas, la pantalla se elige en
    la sección «Áreas de …» del sidebar. Fuera de los módulos, el pie del sidebar. Devuelve el
    camino seguido."""
    camino = camino_por_menu(ruta)
    lado = pagina.locator(f"#{ID_SIDEBAR}")
    abrir_sidebar(pagina)
    if camino["modulo"] is None:
        pie = lado.locator(".silice-sidebar__pie")
        pie.get_by_role("link", name=camino["pantalla"], exact=True).click()
        esperar_ruta(pagina, ruta)
        return f"Sílice › {camino['pantalla']}"
    lado.get_by_role("link", name=camino["modulo"], exact=True).click()
    modulo = next(r for r in rutas_de_la_interfaz() if r["id"] == ruta)["modulo"]
    inicio = next(
        r["id"] for r in rutas_de_la_interfaz() if (r["modulo"], r["area"]) == (modulo, "inicio")
    )
    esperar_ruta(pagina, inicio)
    pasos = [f"Sílice › {camino['modulo']}"]
    if not camino["inicio"]:
        nav = pagina.locator('header nav[aria-label="Menú principal"]')
        if nav.is_visible():
            enlace = nav.get_by_role("link", name=camino["area"], exact=True)
            if enlace.count():
                enlace.click()
                pasos.append(f"barra › {camino['area']}")
            else:
                nav.get_by_role("button", name=camino["area"], exact=True).click()
                panel = pagina.locator(".silice-panel-area")
                panel.get_by_role("link", name=camino["pantalla"], exact=True).click()
                pasos.append(f"barra › {camino['area']} › {camino['pantalla']}")
        else:
            abrir_sidebar(pagina)
            areas = lado.locator(".silice-sidebar__areas")
            areas.get_by_role("link", name=camino["pantalla"], exact=True).click()
            pasos.append(f"Sílice › Áreas › {camino['pantalla']}")
    esperar_ruta(pagina, ruta)
    return " / ".join(pasos)


def caso_de_la_sesion(pagina: Any) -> str | None:
    """La carpeta de trabajo que la API tiene para esta sesión (no la que muestra el selector)."""
    return pagina.evaluate(
        "async () => { const r = await fetch('/v1/casos', {credentials: 'same-origin'});"
        " if (!r.ok) return null; const d = await r.json();"
        " return d && d.actual ? d.actual.nombre : null; }"
    )


def carpeta_mostrada_y_real(pagina: Any) -> dict[str, Any]:
    """Control del armazón en cada fila: la carpeta que el selector de obra MUESTRA al pie de su
    panel frente a la que la API tiene para la sesión (sin `.db`, que la interfaz no muestra).
    Fuera de Presupuestos y obras no hay selector: no se compara."""
    mostrada = None
    boton = pagina.locator(f"#{ID_BOTON_OBRA}")
    if boton.count() and boton.is_visible():
        if boton.get_attribute("aria-expanded") != "true":
            boton.click()
        texto = pagina.locator(".silice-obra__carpeta span").first.inner_text(timeout=4000)
        mostrada = texto.removeprefix("Carpeta:").strip()
        boton.click()
    real = caso_de_la_sesion(pagina)
    corta = (real or "").removesuffix(".db")
    return {
        "carpeta_mostrada": mostrada,
        "carpeta_api": real,
        "carpeta_coincide": None if mostrada is None else mostrada == corta,
    }


def elegir_contexto(pagina: Any, carpeta: str | None, proyecto: str | None) -> None:
    """Carpeta de trabajo y obra con el selector de obra de la barra de Presupuestos y obras (el
    único sitio donde vive): se entra al módulo por el sidebar, «Cambiar carpeta…» abre el diálogo
    de carpetas y la obra se elige en la lista del panel. Se comprueba contra la API."""
    if not carpeta and not proyecto:
        return
    ir_por_menu(pagina, "obras")
    boton = pagina.locator(f"#{ID_BOTON_OBRA}")
    if carpeta and caso_de_la_sesion(pagina) != carpeta:
        boton.click()
        pagina.get_by_role("button", name="Cambiar carpeta…").click()
        dialogo = pagina.get_by_role("dialog", name="Carpetas de trabajo")
        nombre = carpeta.removesuffix(".db")
        dialogo.get_by_role("button", name=f"Abrir {nombre}", exact=True).click(
            timeout=LIMITE_PASO_MS
        )
        fin = time.monotonic() + LIMITE_PASO_MS / 1000
        while caso_de_la_sesion(pagina) != carpeta:
            if time.monotonic() > fin:
                raise RuntimeError(f"la carpeta de trabajo no cambió a «{carpeta}»")
            pagina.wait_for_timeout(300)
        dialogo.wait_for(state="detached", timeout=LIMITE_PASO_MS)
        esperar_ruta(pagina, "obras")
    if proyecto:
        if boton.get_attribute("aria-expanded") != "true":
            boton.click()
        opcion = pagina.locator(".silice-obra__panel .silice-obra__opcion").filter(
            has_text=proyecto
        )
        opcion.first.click(timeout=LIMITE_PASO_MS)
        pagina.locator(".silice-obra__panel").wait_for(state="detached", timeout=LIMITE_PASO_MS)
        pagina.wait_for_timeout(500)


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
        return "ir por el menú: " + ir_por_menu(pagina, paso["ruta"])
    if accion == "llenar":
        donde = pagina if paso.get("fuera") else zona
        valor = str(paso["valor"]).replace("{hoy}", time.strftime("%Y-%m-%d"))
        campo = _rellenable(donde, paso["rotulo"]).nth(indice)
        campo.fill(valor, timeout=LIMITE_PASO_MS)
        return f"llenar «{paso['rotulo']}» = {valor!r}"
    if accion == "elegir":
        donde = pagina if paso.get("fuera") else zona
        campo = donde.get_by_label(paso["rotulo"], exact=True).and_(donde.locator("select"))
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
        elegir_contexto(pagina, fila.get("carpeta"), fila.get("proyecto"))
        resultado["camino"] = ir_por_menu(pagina, fila["ruta"])
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
                m: n(lambda f, m=m: f.get("modo_nav") == m, grupo) for m in ("barra", "sidebar")
            },
            "sidebar_tapa": n(lambda f: f.get("sidebar_tapa"), grupo),
            "sidebar_distinto": n(sidebar_distinto, grupo),
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
    estados = [e for e in SIDEBARS if any(f.get("sidebar") == e for f in normales)]
    resumen["por_sidebar"] = {
        e: controles([f for f in normales if f.get("sidebar") == e]) for e in estados
    }
    modulos: dict[str, list[dict[str, Any]]] = {}
    for f in normales:
        modulos.setdefault(f.get("modulo_de_la_ruta", f.get("modulo")) or "fuera", []).append(f)
    resumen["por_modulo"] = {m: controles(grupo) for m, grupo in modulos.items()}
    resumen["con_recorrido"] = controles(con_recorrido)
    resumen["con_recorrido"]["columna_no_visible"] = n(
        lambda f: not f.get("recorrido_visible"), con_recorrido
    )
    resumen["con_recorrido"]["columna_solapa"] = n(
        lambda f: f.get("recorrido_solapa") is not False, con_recorrido
    )
    resumen["axe_nuevas"] = sorted(
        {
            f"{f['rol']} {f['ancho']} {f['letra']} {f.get('sidebar', '')} {f['id']}: {r}"
            for f in filas
            for r in axe_nuevas(f)
        }
    )
    resumen["fallos_nav"] = sorted(filter(None, map(fallo_nav, filas)))
    return resumen


def sidebar_distinto(fila: dict[str, Any]) -> bool:
    """El sidebar no estaba como debía en el estado medido (capa, fijado o ninguno)."""
    return "sidebar" in fila and fila.get("sidebar_modo") != fila.get("sidebar_esperado")


def fallo_nav(fila: dict[str, Any]) -> str | None:
    """Una línea por medición con un control de la barra o del sidebar en rojo (o sin medir)."""
    motivos = []
    if "duplicados_nav" not in fila:
        motivos.append("sin control de la barra: " + str(fila.get("error", "")))
    if fila.get("duplicados_nav"):
        motivos.append(f"duplicados {fila.get('duplicados_detalle')}")
    if fila.get("barra_cortada"):
        motivos.append(f"cortada {fila.get('barra_motivos')}")
    if fila.get("panel_fuera"):
        motivos.append(f"fuera {fila.get('paneles_fuera')}")
    if fila.get("sidebar_tapa"):
        motivos.append(f"el sidebar fijado tapa el contenido {fila.get('main_caja')}")
    if sidebar_distinto(fila):
        modo = fila.get("sidebar_modo") or "ninguno"
        esperado = fila.get("sidebar_esperado") or "ninguno"
        motivos.append(f"sidebar {modo} (se esperaba {esperado})")
    if not motivos:
        return None
    marca = " (recorrido)" if fila.get("recorrido") else ""
    estado = f" {fila['sidebar']}" if fila.get("sidebar") else ""
    cabeza = f"{fila['rol']} {fila['ancho']} {fila['letra']}{estado} {fila['id']}{marca}: "
    return cabeza + "; ".join(motivos)


def sidebars_pedidos(valores: list[str]) -> list[str]:
    """`--sidebar oculto,fijado` o `--sidebar oculto fijado`; en el orden de `SIDEBARS`."""
    pedidos = {v.strip() for parte in valores for v in parte.split(",") if v.strip()}
    desconocidos = pedidos - set(SIDEBARS)
    if desconocidos or not pedidos:
        raise SystemExit(
            f"--sidebar: use {', '.join(SIDEBARS)} (no {', '.join(sorted(desconocidos))})"
        )
    return [e for e in SIDEBARS if e in pedidos]


def letras_pedidas(valores: list[str]) -> list[str]:
    """`--letras normal,grande` o `--letras normal grande`; en el orden de `LETRAS`."""
    pedidas = {v.strip() for parte in valores for v in parte.split(",") if v.strip()}
    desconocidas = pedidas - set(LETRAS)
    if desconocidas or not pedidas:
        raise SystemExit(
            f"--letras: use {', '.join(LETRAS)} (no {', '.join(sorted(desconocidas))})"
        )
    return [letra for letra in LETRAS if letra in pedidas]


def recorrer_rol(
    contexto: Any,
    base: str,
    rol: str,
    rutas: list[dict[str, Any]],
    args: argparse.Namespace,
    letras: list[str],
    sidebars: list[str],
    capturas: Path,
    axe: str | None,
    libros: dict[str, Path],
    resultado: dict[str, Any],
) -> None:
    """Todas las medidas de un rol: por estado del sidebar, letra, ancho y pantalla."""
    fijar_sidebar_de_la_cuenta(contexto, base, False)
    en_menu = ids_del_menu(contexto, base)
    resultado.setdefault("menu_por_rol", {})[rol] = sorted(en_menu)
    for sidebar in sidebars:
        fijar_sidebar_de_la_cuenta(contexto, base, sidebar == "fijado")
        for letra in letras:
            for ancho in args.anchos:
                for ruta in rutas:
                    # Fuera del menú del rol solo interesa el aviso «Sin permiso» (H-8).
                    if ruta["id"] not in en_menu and sidebar != "oculto":
                        continue
                    fila = medir_pantalla(
                        contexto, base, ruta, ancho, rol, capturas, axe, en_menu, letra, sidebar
                    )
                    resultado["pantallas"].append(fila)
                    print(
                        f"{rol:5} {sidebar:7} {letra:10} {ancho} {ruta['id']:15} "
                        f"h1={fila.get('h1')} scrollX={fila.get('scroll_x')} "
                        f"nav={fila.get('modo_nav')} lado={fila.get('sidebar_modo')} "
                        f"dup={fila.get('duplicados_nav')} cortada={fila.get('barra_cortada')} "
                        f"fuera={fila.get('panel_fuera')} tapa={fila.get('sidebar_tapa')} "
                        f"{fila.get('ms_hasta_h1')}ms {fila.get('error', '')}"
                    )
                # El recorrido empieza al auditar desde el inicio de Auditoría: solo quien audita.
                if sidebar == "oculto" and not args.sin_recorrido and "libros" in en_menu:
                    for fila in medir_con_recorrido(
                        contexto, base, libros["limpio"], ancho, rol, capturas, axe, letra
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
    fijar_sidebar_de_la_cuenta(contexto, base, False)
    if args.sin_flujo or rol not in ("ana", "rita"):
        return
    if rol == "ana":
        for clave in ("limpio", "ajeno_control", "csv"):
            if clave not in libros:
                continue
            for desde in ("libros", "inicio"):
                resultado["flujos"].append(
                    flujo_libros(
                        contexto, base, libros[clave], capturas, f"ana_{desde}_{clave}", desde
                    )
                )
        return
    for clave in ("limpio", "ajeno_control"):
        if clave in libros:
            resultado["flujos"].append(
                flujo_revisar_excel(contexto, base, libros[clave], capturas, f"rita_{clave}")
            )


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
    a.add_argument(
        "--sidebar",
        nargs="+",
        default=[",".join(SIDEBARS)],
        help="estados del sidebar de módulos (con comas o espacios): oculto, abierto, fijado",
    )
    a.add_argument("--rutas", nargs="*", help="ids de página; por omisión todas las de rutas.ts")
    a.add_argument("--sin-axe", action="store_true")
    a.add_argument("--sin-flujo", action="store_true")
    a.add_argument(
        "--sin-recorrido",
        action="store_true",
        help="no repite Libro y el inicio de Auditoría con el recorrido",
    )
    a.add_argument("--sin-pantallas", action="store_true", help="solo las medidas aparte")
    a.add_argument(
        "--especiales", action="store_true", help="mesa, selector de obra, diálogos, marca, mercado"
    )
    a.add_argument(
        "--umbrales", action="store_true", help="mide el umbral de la barra de cada módulo"
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
    sidebars = sidebars_pedidos(args.sidebar)
    salida: Path = args.salida
    capturas = salida / "capturas"
    capturas.mkdir(parents=True, exist_ok=True)
    rutas = [r for r in rutas_de_la_interfaz() if not args.rutas or r["id"] in args.rutas]
    axe = None if args.sin_axe or args.sin_pantallas else bajar_axe(salida)

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
        "sidebar": sidebars,
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
                if args.umbrales:
                    resultado["umbrales"] = medir_umbrales(
                        navegador, base, claves, args.roles, letras, capturas
                    )
                    print(json.dumps(resultado["umbrales"]["umbrales"], indent=2))
                for rol in [] if args.sin_pantallas else args.roles:
                    contexto = navegador.new_context(viewport={"width": 1366, "height": ALTO})
                    pagina = contexto.new_page()
                    entrar(pagina, base, rol, claves[rol])
                    pagina.close()
                    recorrer_rol(
                        contexto,
                        base,
                        rol,
                        rutas,
                        args,
                        letras,
                        sidebars,
                        capturas,
                        axe,
                        libros,
                        resultado,
                    )
                    contexto.close()
                if args.especiales:
                    contexto = navegador.new_context(viewport={"width": 1366, "height": ALTO})
                    pagina = contexto.new_page()
                    entrar(pagina, base, "ana", claves["ana"])
                    pagina.close()
                    resultado["especiales"] = medir_especiales(
                        contexto, base, capturas, args.anchos, letras
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
    resultado["resumen"] = resumir(resultado["pantallas"]) if resultado["pantallas"] else {}
    if "especiales" in resultado:
        resultado["resumen"]["especiales_fallos"] = resultado["especiales"]["fallos"]
    (salida / "recorrido.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(resultado["resumen"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
