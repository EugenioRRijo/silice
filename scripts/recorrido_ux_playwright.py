"""Recorrido de UX/UI de la interfaz de Sílice con Playwright (repetible tras cada cambio).

Arranca un servidor de Sílice en 127.0.0.1 con una carpeta de datos TEMPORAL sembrada con la
demostración ficticia (cuentas de `tests/fixtures/sesion_web.py` y los casos de `start.py`), entra
con cuentas ficticias y mide TODAS las pantallas de `frontend-desktop/src/shell/rutas.ts` en los
espacios del marco de F6 (contrato de rutas 2026-11-04): Inicio, la obra (secciones y subvistas),
Producción, Auditoría, Precios y la Cuenta. Cada pantalla se abre por su ruta canónica
(`ruta_canonica`, espejo de `rutaCanonica` de `marco/espacios.ts`) con una obra de la siembra, a
cada ancho y con cada tamaño de letra, como cada rol. Por pantalla anota: captura, número de h1,
desplazamiento horizontal, errores de consola y de red, tiempo hasta el primer h1, si el marco se la
ofrece al rol (enlaces de la barra lateral y de las barras de cada espacio), las barras de pestañas
que desbordan, que salen de la ventana o repiten un nombre, los botones y enlaces sin nombre
accesible (sin contar lo que está dentro de un `aria-hidden="true"`, como axe) y, si se puede bajar
axe-core de un CDN, la revisión de accesibilidad. Además repite Libro y el inicio de Auditoría con
el recorrido guiado en curso y recorre el flujo de la empresa de hoy (subir un presupuesto y
auditarlo) contando clics, pantallas y decisiones.

    uv run --no-sync --with playwright python scripts/recorrido_ux_playwright.py \\
        --salida <carpeta> [--roles admin ana rita] [--anchos 1056,1366,1920]
        [--letras normal,grande,muy-grande] [--rutas hoja riesgo ...] [--sin-axe] [--sin-flujo]
        [--sin-recorrido] [--sin-pantallas] [--visor] [--umbrales] [--url http://127.0.0.1:8501]

Modo `--umbrales`: por rol y letra, el menor ancho en que caben la barra de arriba y las barras de
pestañas de cada lugar (la obra en Control de obra, que tiene sección y subvistas; los espacios de
Producción, Auditoría y Precios; la Cuenta), con la obra de nombre más largo de la siembra.

Modo `--funcional` (BS-F, «que todas las herramientas funcionen»): en vez de medir, ejecuta la
acción principal de cada pantalla con la cuenta que la puede usar y comprueba el resultado visible.
Las filas viven en `scripts/recorrido_funcional.toml` (una por pantalla) y cada una entra como una
persona, por el marco y no por dirección: la obra en la barra lateral (que fija también su carpeta),
la sección y la subvista en las barras de la obra; un espacio de la empresa en «Costos y
producción» y su herramienta en su barra; la Cuenta con el botón de la persona. Una fila con
carpeta y sin obra entra en una obra de esa carpeta para abrirla (quien no ve obras la abre en
Cuenta › Carpetas):

    uv run --no-sync --with playwright python scripts/recorrido_ux_playwright.py --funcional \\
        --salida <carpeta> [--acciones scripts/recorrido_funcional.toml] [--solo componer,catalogo]

F8 (C2) retiró lo que medía el menú de módulos de antes de F6: los estados del sidebar
(`--sidebar`), los paneles de área de la barra y las medidas aparte del selector de obra y del
diálogo de carpetas (`--especiales`).

No usa `data/` del árbol ni datos reales; solo libros ficticios (`tests/fixtures/`). Cierra el
servidor por su PID y el navegador que lanzó; nunca cierra Chrome/Edge por nombre.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

RUTAS_TS = RAIZ / "frontend-desktop" / "src" / "shell" / "rutas.ts"
# Dónde vive cada pantalla desde F6 (contrato de rutas 2026-11-04): los espacios, las subvistas y la
# Cuenta en `espacios.ts`; las secciones de la obra y la Vista general en `secciones.ts`.
ESPACIOS_TS = RAIZ / "frontend-desktop" / "src" / "marco" / "espacios.ts"
SECCIONES_TS = RAIZ / "frontend-desktop" / "src" / "marco" / "secciones.ts"
AXE_URL = "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js"
ALTO = 768
ROLES = {"admin": "administra", "ana": "arma", "rita": "revisa"}
LIMITE_CARGA_MS = 20_000
# Los anchos de la pasada en navegador del cierre del rediseño (plan de la tanda, F8 C3): el menor
# para el que se diseña el marco (DESIGN.md), el portátil de la empresa y una pantalla grande.
ANCHOS = (1056, 1366, 1920)
# Los tamaños de letra de `frontend-desktop/src/comun/preferenciaDeLetra.ts` y su clave de
# localStorage.
LETRAS = ("normal", "grande", "muy-grande")
CLAVE_LETRA = "silice.tamano-letra"
# Violaciones axe de la corrida de referencia (bitácora 2026-10-25-recorrido-ux-playwright.md,
# H-10): cualquier otra (ruta, regla) es nueva. El Inicio de entonces ya no existe: su bloque
# «Últimas auditorías» (la región desplazable de rita a 1056 px) vive hoy en el inicio de Auditoría.
# Desde F6 (T8) el id «inicio» es la Vista general, que vuelve a mostrar «Últimas auditorías»; su
# fila de la referencia no se volvió a medir con ella.
AXE_DE_REFERENCIA = {
    ("administracion", "color-contrast"),
    ("inicio", "scrollable-region-focusable"),
    ("auditoria", "scrollable-region-focusable"),
}


def rutas_de_la_interfaz() -> list[dict[str, str | None]]:
    """Las páginas de `rutas.ts` (id, título, sección de permisos, acción y módulo activable),
    leídas del texto: es la única lista."""
    texto = RUTAS_TS.read_text(encoding="utf-8")
    bloque = texto.split("export const PAGINAS", 1)[1].split("export function paginaPorId", 1)[0]
    paginas: list[dict[str, str | None]] = []
    # Cada entrada se lee campo a campo: el orden de los campos no importa.
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
                "modulo": campos.get("modulo"),
            }
        )
    return paginas


# --------------------------- rutas canónicas (F6) -----------------------------------------------
#
# El espejo de `rutaCanonica` (`marco/espacios.ts`): la ruta de cada pantalla se lee de las tablas
# del marco como texto (como `PAGINAS`) y no se escribe a mano en el recorrido.

# Una entrada `{ id: "…", titulo: "…", pagina: "…" | null` de las tablas de `espacios.ts` y de
# `secciones.ts`.
_ENTRADA_DEL_MARCO = r'\{\s*id:\s*"([^"]*)",\s*titulo:\s*"([^"]*)",\s*pagina:\s*(?:"([^"]*)"|null)'
# La pantalla de la Vista general (`rutaCanonica`: `paginaId === "inicio"`).
PAGINA_DE_LA_VISTA_GENERAL = "inicio"
# Así se escribe la carpeta de la empresa en `/obra/<carpeta>/…` (`secciones.ts`).
SEGMENTO_DE_LA_EMPRESA = "empresa"


def _bloque_ts(texto: str, desde: str, hasta: str, archivo: Path) -> str:
    if desde not in texto or hasta not in texto.split(desde, 1)[1]:
        raise ValueError(f"{archivo.name}: no se encuentra «{desde}» … «{hasta}»")
    return texto.split(desde, 1)[1].split(hasta, 1)[0]


@functools.cache
def mapa_del_marco() -> dict[str, Any]:
    """Dónde vive cada pantalla: `obra` (pantalla → sección), `subvista` (pantalla → sección y
    segmento), `espacio` (pantalla → espacio y segmento), `cuenta` (pantalla → su primera sección
    de la Cuenta), la ruta de la Vista general y los títulos con que se ven en las barras."""
    espacios = ESPACIOS_TS.read_text(encoding="utf-8")
    secciones = SECCIONES_TS.read_text(encoding="utf-8")
    vista = re.search(r'RUTA_DE_VISTA_GENERAL\s*=\s*"([^"]+)"', secciones)
    if vista is None:
        raise ValueError(f"{SECCIONES_TS.name}: no se encuentra RUTA_DE_VISTA_GENERAL")
    de_obra = _bloque_ts(
        secciones, "export const SECCIONES_DE_OBRA", "export function seccionPorId", SECCIONES_TS
    )
    entradas_de_obra = re.findall(_ENTRADA_DEL_MARCO, de_obra)
    obra = {pagina: id_ for id_, _, pagina in entradas_de_obra if pagina}
    titulo_de_seccion = {id_: titulo for id_, titulo, _ in entradas_de_obra}
    subvista: dict[str, tuple[str, str]] = {}
    titulo_de_subvista: dict[tuple[str, str], str] = {}
    bloque = _bloque_ts(
        espacios, "export const SUBVISTAS", "export function subvistaDeLaPagina", ESPACIOS_TS
    )
    for seccion, vistas in re.findall(r"(\w+):\s*\[(.*?)\]", bloque, flags=re.DOTALL):
        for id_, titulo, pagina in re.findall(_ENTRADA_DEL_MARCO, vistas):
            titulo_de_subvista[(seccion, id_)] = titulo
            if id_ and pagina:
                subvista[pagina] = (seccion, id_)
    espacio: dict[str, tuple[str, str]] = {}
    titulo_de_espacio: dict[str, str] = {}
    titulo_de_herramienta: dict[tuple[str, str], str] = {}
    bloque = _bloque_ts(espacios, "export const ESPACIOS:", "export const SUBVISTAS", ESPACIOS_TS)
    patron = r'(\w+):\s*\{\s*titulo:\s*"([^"]*)",\s*herramientas:\s*\[(.*?)\]'
    for nombre, titulo_espacio, herramientas in re.findall(patron, bloque, flags=re.DOTALL):
        titulo_de_espacio[nombre] = titulo_espacio
        for id_, titulo, pagina in re.findall(_ENTRADA_DEL_MARCO, herramientas):
            espacio[pagina] = (nombre, id_)
            titulo_de_herramienta[(nombre, id_)] = titulo
    bloque = _bloque_ts(
        espacios, "export const SECCIONES_DE_CUENTA", "export function esCuenta", ESPACIOS_TS
    )
    secciones_de_cuenta = re.findall(_ENTRADA_DEL_MARCO, bloque)
    cuenta: dict[str, str] = {}
    for id_, _, pagina in secciones_de_cuenta:
        if pagina:
            cuenta.setdefault(pagina, id_)
    return {
        "vista_general": vista[1],
        "obra": obra,
        "subvista": subvista,
        "espacio": espacio,
        "cuenta": cuenta,
        "secciones_de_cuenta": {id_: pagina for id_, _, pagina in secciones_de_cuenta},
        "titulos": {
            "seccion": titulo_de_seccion,
            "subvista": titulo_de_subvista,
            "espacio": titulo_de_espacio,
            "herramienta": titulo_de_herramienta,
            "cuenta": {id_: titulo for id_, titulo, _ in secciones_de_cuenta},
        },
    }


def _segmento_de_carpeta(carpeta: str | None) -> str:
    if carpeta is None:
        return SEGMENTO_DE_LA_EMPRESA
    return urllib.parse.quote(carpeta, safe="!~*'()")  # como encodeURIComponent


def ruta_canonica(id_: str, obra: tuple[str | None, int] | None = None) -> str:
    """La ruta de la pantalla (sin «#»), como `rutaCanonica(id, obra)`: una sección o subvista de la
    obra va a `/obra/<carpeta>/<obra>/<sección>[/<subvista>]` y, sin obra, a su dirección corta
    (`/<id>`), que el marco lleva a la obra de la sesión; una herramienta de Producción, Auditoría
    o Precios, a `/<espacio>/<segmento>`; Administración y Acerca de, a la Cuenta; la Vista general,
    a `/inicio/general`. `obra` es (carpeta, id); carpeta `None` es la de la empresa."""
    if id_ not in {r["id"] for r in rutas_de_la_interfaz()}:
        raise ValueError(f"no hay pantalla «{id_}» en rutas.ts")
    mapa = mapa_del_marco()
    if id_ == PAGINA_DE_LA_VISTA_GENERAL:
        return mapa["vista_general"]
    seccion, subvista = mapa["obra"].get(id_), None
    if seccion is None and id_ in mapa["subvista"]:
        seccion, subvista = mapa["subvista"][id_]
    if seccion is not None:
        if obra is None:
            return f"/{id_}"
        carpeta, obra_id = obra
        base = f"/obra/{_segmento_de_carpeta(carpeta)}/{obra_id}/{seccion}"
        return f"{base}/{subvista}" if subvista else base
    if id_ in mapa["espacio"]:
        nombre, herramienta = mapa["espacio"][id_]
        return f"/{nombre}/{herramienta}"
    if id_ in mapa["cuenta"]:
        return f"/cuenta/{mapa['cuenta'][id_]}"
    return f"/{id_}"


def es_de_la_obra(id_: str) -> bool:
    mapa = mapa_del_marco()
    return id_ in mapa["obra"] or id_ in mapa["subvista"]


def hash_de(id_: str, obra: tuple[str | None, int] | None = None) -> str:
    """El `location.hash` con que se abre la pantalla (sin obra: la de la sesión)."""
    return "#" + ruta_canonica(id_, obra)


def patron_de_hash(id_: str) -> str:
    """La expresión (vale para `re` y para `RegExp`) del `location.hash` en que queda la pantalla
    abierta, con o sin consulta: la de la obra, con cualquier carpeta y obra (su dirección corta
    redirige a la obra de la sesión)."""
    consulta = r"(?:\?.*)?$"
    if es_de_la_obra(id_):
        cola = ruta_canonica(id_, ("x", 0)).split("/", 4)[4]
        return r"^#/obra/[^/?#]+/\d+/" + re.escape(cola) + consulta
    return "^" + re.escape(hash_de(id_)) + consulta


def pagina_de_la_ruta(enlace: str) -> str | None:
    """La pantalla a la que lleva un enlace (`href` o `location.hash`), o `None` si no lleva a una
    pantalla del registro (Pendientes, «Pantalla y tamaño de letra», un segmento desconocido o una
    dirección vieja que F8 retiró, como `#/catalogo`)."""
    ruta = enlace.split("#", 1)[1] if "#" in enlace else enlace
    partes = [p for p in ruta.split("?", 1)[0].split("/") if p]
    mapa = mapa_del_marco()
    if "/" + "/".join(partes) == mapa["vista_general"]:
        return PAGINA_DE_LA_VISTA_GENERAL
    if len(partes) in (4, 5) and partes[0] == "obra":
        seccion = partes[3]
        if len(partes) == 4:
            return next((p for p, s in mapa["obra"].items() if s == seccion), None)
        return next((p for p, sv in mapa["subvista"].items() if sv == (seccion, partes[4])), None)
    if len(partes) == 2 and partes[0] == "cuenta":
        return mapa["secciones_de_cuenta"].get(partes[1]) or None
    if len(partes) == 2:
        return next((p for p, e in mapa["espacio"].items() if e == tuple(partes)), None)
    # Solo las pantallas de la obra conservan su dirección corta (contrato 2.4, enmienda de F8).
    if len(partes) == 1 and es_de_la_obra(partes[0]):
        return partes[0]
    return None


def obra_de_la_direccion(enlace: str) -> tuple[str | None, int] | None:
    """La obra (carpeta, id) de una dirección `#/obra/<carpeta>/<obra>/…`, o `None`."""
    ruta = enlace.split("#", 1)[1] if "#" in enlace else enlace
    partes = [p for p in ruta.split("?", 1)[0].split("/") if p]
    if len(partes) < 3 or partes[0] != "obra" or not partes[2].isdigit():
        return None
    carpeta = urllib.parse.unquote(partes[1])
    return (None if carpeta == SEGMENTO_DE_LA_EMPRESA else carpeta, int(partes[2]))


# --------------------------- cómo llega una persona (F6) ----------------------------------------


def camino_por_el_marco(id_: str) -> list[dict[str, str]]:
    """Los clics con que una persona llega a la pantalla en el marco de F6. Cada paso dice dónde se
    pulsa: `lateral` (la barra lateral: «Vista general», la obra elegida —`nombre` «obra»— o un
    espacio de «Costos y producción»), `cuenta` (el botón de la persona en la barra de arriba) o
    `barra` (la barra de pestañas cuyo nombre accesible es `barra`), y el texto del enlace. La obra
    abre su Resumen y la Cuenta su primera sección; un espacio, su primera herramienta usable, y se
    pulsa siempre su pestaña."""
    if id_ not in {r["id"] for r in rutas_de_la_interfaz()}:
        raise ValueError(f"no hay pantalla «{id_}» en rutas.ts")
    mapa = mapa_del_marco()
    titulos = mapa["titulos"]
    if id_ == PAGINA_DE_LA_VISTA_GENERAL:
        return [{"donde": "lateral", "nombre": "Vista general"}]
    if es_de_la_obra(id_):
        camino = [{"donde": "lateral", "nombre": "obra"}]
        seccion, subvista = mapa["obra"].get(id_), None
        if seccion is None:
            seccion, subvista = mapa["subvista"][id_]
        titulo = titulos["seccion"][seccion]
        if seccion != "resumen":
            camino.append({"donde": "barra", "barra": "Secciones de la obra", "nombre": titulo})
        if subvista:
            nombre = titulos["subvista"][(seccion, subvista)]
            camino.append({"donde": "barra", "barra": f"Vistas de {titulo}", "nombre": nombre})
        return camino
    if id_ in mapa["espacio"]:
        espacio, herramienta = mapa["espacio"][id_]
        titulo = titulos["espacio"][espacio]
        return [
            {"donde": "lateral", "nombre": titulo},
            {
                "donde": "barra",
                "barra": titulo,
                "nombre": titulos["herramienta"][(espacio, herramienta)],
            },
        ]
    seccion = mapa["cuenta"][id_]
    return [
        {"donde": "cuenta", "nombre": "Cuenta"},
        {
            "donde": "barra",
            "barra": "Secciones de la cuenta",
            "nombre": titulos["cuenta"][seccion],
        },
    ]


def obra_para(
    obras: list[dict[str, Any]], carpeta: str | None, nombre: str | None
) -> dict[str, Any] | None:
    """La obra de `GET /v1/obras/todas` con que se recorre: la de esa carpeta (None, la de la
    empresa) cuyo nombre es `nombre` o, sin nombre, la primera de la carpeta. Un nombre que no
    está en la carpeta da `None`: no se cambia por otra obra."""
    de_la_carpeta = [o for o in obras if o.get("carpeta") == carpeta]
    if nombre is None:
        return de_la_carpeta[0] if de_la_carpeta else None
    return next((o for o in de_la_carpeta if o.get("obra") == nombre), None)


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
    letra_aplicada: de.dataset.siliceLetra || null,
    hash: location.hash,
    texto: (document.body.innerText || '').slice(0, 200),
  };
}"""


# Las barras del marco de F6 sobre la pantalla ya cargada: la barra de arriba
# (`header.silice-marco-barra`), la barra lateral y cada barra de pestañas de un espacio
# (`nav.silice-barra-espacio`: secciones de la obra, vistas de una sección, herramientas de un
# espacio, secciones de la Cuenta). Por barra: si desborda (su contenido es más ancho que ella), qué
# pestañas salen de la ventana y qué nombres se repiten. Un texto con puntos suspensivos cuenta como
# recortado si queda más corto que su propio tope (`max-inline-size`); recortado por su tope es a
# propósito. Chromium guarda las medidas en unidades de 1/64 px: las dos comparaciones del recorte
# toleran esa diferencia (un recorte real mide décimas).
TOLERANCIA_SUBPIXEL = 0.05
BARRAS_JS = """() => {
  const de = document.documentElement, ancho = de.clientWidth;
  const limpio = t => (t || '').replace(/\\s+/g, ' ').trim();
  const visible = el => { if (!el) return false; const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
  const caja = r => [r.left, r.top, r.right, r.bottom].map(Math.round);
  const recortes = raiz => {
    const salida = [];
    for (const el of raiz.querySelectorAll('*')) {
      if (!visible(el)) continue;
      const cs = getComputedStyle(el);
      if (cs.textOverflow !== 'ellipsis') continue;
      const rango = document.createRange();
      rango.selectNodeContents(el);
      const texto = rango.getBoundingClientRect().width;
      const caja = el.getBoundingClientRect().width;
      // Un texto solo para lectores de pantalla (1 px, con clip-path) no se ve: no cuenta.
      if (caja <= 1 || (cs.clipPath && cs.clipPath !== 'none')) continue;
      const relleno = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight)
        + parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
      if (texto <= caja - relleno + __TOL__) continue;
      const tope = cs.maxWidth.endsWith('px') ? parseFloat(cs.maxWidth) : Infinity;
      const medida = cs.boxSizing === 'border-box' ? caja : caja - relleno;
      if (medida >= tope - __TOL__) continue;
      salida.push('«' + limpio(el.textContent).slice(0, 30) + '» recortado a '
        + (caja - relleno).toFixed(1) + ' de ' + texto.toFixed(1) + ' px');
    }
    return salida;
  };
  const medir = (el, nombre) => {
    const enlaces = [...el.querySelectorAll('a, button')].filter(visible);
    const nombres = enlaces.map(a => limpio(a.textContent)).filter(Boolean);
    const cuenta = {};
    for (const n of nombres) cuenta[n] = (cuenta[n] || 0) + 1;
    return {
      barra: nombre,
      desborda: el.scrollWidth > el.clientWidth + 1,
      fuera: enlaces.filter(a => { const r = a.getBoundingClientRect();
        return r.right > ancho + 1 || r.left < -1; }).map(a => limpio(a.textContent).slice(0, 40)),
      repetidas: Object.entries(cuenta).filter(([, k]) => k > 1).map(([n, k]) => n + ' x' + k),
      recortes: recortes(el),
      caja: caja(el.getBoundingClientRect()),
    };
  };
  const barras = [];
  const arriba = document.querySelector('header.silice-marco-barra');
  if (arriba) barras.push(medir(arriba, 'Barra de arriba'));
  const lateral = document.querySelector('aside.silice-marco-lateral');
  if (lateral) {
    const m = medir(lateral, 'Barra lateral');
    // La barra lateral lista las obras: sus nombres pueden repetirse (homónimas en dos carpetas).
    m.repetidas = [];
    barras.push(m);
  }
  for (const nav of document.querySelectorAll('nav.silice-barra-espacio'))
    if (visible(nav)) barras.push(medir(nav, nav.getAttribute('aria-label') || 'barra sin nombre'));
  return barras;
}""".replace("__TOL__", str(TOLERANCIA_SUBPIXEL))


# Los controles de la pantalla (botones, enlaces y lo que hace de botón) con su nombre accesible
# aproximado (aria-label, aria-labelledby, el texto, el `alt` de una imagen, `title` o el valor de
# un botón de formulario), si están a la vista y si cuelgan de un `aria-hidden="true"`: axe no
# revisa lo que el árbol de accesibilidad no expone, y este detector tampoco (`sin_nombre`).
CONTROLES_JS = """() => {
  const limpio = t => (t || '').replace(/\\s+/g, ' ').trim();
  const nombre = el => {
    const etiqueta = el.getAttribute('aria-label');
    if (limpio(etiqueta)) return limpio(etiqueta);
    const ids = (el.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean);
    const de = ids.map(i => {
      const r = document.getElementById(i); return r ? r.textContent : ''; });
    if (limpio(de.join(' '))) return limpio(de.join(' '));
    if (limpio(el.textContent)) return limpio(el.textContent);
    const img = el.querySelector('img[alt], [role="img"][aria-label]');
    if (img && limpio(img.getAttribute('alt') || img.getAttribute('aria-label')))
      return limpio(img.getAttribute('alt') || img.getAttribute('aria-label'));
    if (limpio(el.getAttribute('title'))) return limpio(el.getAttribute('title'));
    if (el.tagName === 'INPUT') return limpio(el.value);
    return '';
  };
  const selector = 'button, a[href], [role="button"], [role="link"], input[type="button"],'
    + ' input[type="submit"]';
  return [...document.querySelectorAll(selector)].map(el => {
    const r = el.getBoundingClientRect();
    return {
      rol: el.getAttribute('role') || (el.tagName === 'A' ? 'link' : 'button'),
      nombre: nombre(el),
      oculto: el.closest('[aria-hidden="true"]') !== null,
      visible: r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden',
      html: el.outerHTML.slice(0, 120),
    };
  });
}"""


def sin_nombre(controles: list[dict[str, Any]]) -> list[str]:
    """Los botones y enlaces a la vista sin nombre accesible. Lo que cuelga de un
    `aria-hidden="true"` (un portal cerrado de Carbon, un icono decorativo) se salta, como axe."""
    return [
        f"{c['rol']} {c['html']}"
        for c in controles
        if c.get("visible") and not c.get("oculto") and not str(c.get("nombre", "")).strip()
    ]


def _ir_y_esperar(pagina: Any, base: str, ruta: str) -> None:
    """`ruta` es el id de la pantalla; se abre su ruta canónica."""
    pagina.goto(f"{base}/app/{hash_de(ruta)}", wait_until="domcontentloaded")
    pagina.wait_for_selector("main h1:not([data-esqueleto])", timeout=LIMITE_CARGA_MS)
    with contextlib.suppress(Exception):
        pagina.wait_for_load_state("networkidle", timeout=4000)


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


def _medir_cargada(pagina: Any, fila: dict[str, Any], axe: str | None, captura: Path) -> None:
    """Medidas, axe, captura, barras y controles de una pantalla ya cargada."""
    fila.update(pagina.evaluate(MEDIR_JS))
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
    fila["barras"] = pagina.evaluate(BARRAS_JS)
    fila["controles"] = pagina.evaluate(CONTROLES_JS)
    fila["sin_nombre"] = sin_nombre(fila["controles"])


def oferta_del_marco(contexto: Any, base: str, obra: tuple[str | None, int] | None) -> set[str]:
    """Las pantallas que el marco ofrece a la sesión de este contexto, leídas como las encuentra
    una persona: los enlaces de la barra lateral y de la barra de arriba; dentro de la obra, sus
    secciones y las vistas de cada una; en cada espacio y en la Cuenta, sus pestañas."""
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": 1920, "height": ALTO})
    ids: set[str] = set()

    def leer(hash_: str) -> list[str]:
        pagina.goto(f"{base}/app/{hash_}", wait_until="domcontentloaded")
        with contextlib.suppress(Exception):
            pagina.wait_for_selector("main h1", timeout=LIMITE_CARGA_MS)
        hrefs = pagina.eval_on_selector_all(
            "aside.silice-marco-lateral a[href], header.silice-marco-barra a[href],"
            " nav.silice-barra-espacio a[href]",
            "els => els.map(a => a.getAttribute('href') || '')",
        )
        return [h for h in hrefs if h]

    vistos: set[str] = set()
    pendientes = [hash_de(PAGINA_DE_LA_VISTA_GENERAL)]
    if obra is not None:
        pendientes.append("#" + f"/obra/{_segmento_de_carpeta(obra[0])}/{obra[1]}/resumen")
    pendientes.append("#/cuenta/preferencias")
    pendientes += ["#/produccion", "#/auditoria", "#/precios"]
    try:
        while pendientes:
            hash_ = pendientes.pop(0)
            if hash_ in vistos:
                continue
            vistos.add(hash_)
            for href in leer(hash_):
                id_ = pagina_de_la_ruta(href)
                if id_ is None:
                    continue
                ids.add(id_)
                # Las secciones de la obra elegida se abren para leer sus vistas.
                destino = href if href.startswith("#") else "#" + href.split("#", 1)[-1]
                if obra is not None and obra_de_la_direccion(destino) == obra:
                    pendientes.append(destino.split("?", 1)[0])
    finally:
        pagina.close()
    return ids


def obras_de_la_siembra(contexto: Any, base: str) -> list[dict[str, Any]]:
    """`GET /v1/obras/todas` con la sesión de este contexto (vacía si la cuenta no lee obras)."""
    r = api_del_contexto(contexto, base, "GET", "/v1/obras/todas")
    if r["estado"] != 200 or not isinstance(r["datos"], dict):
        return []
    return list(r["datos"].get("obras", []))


def obra_del_recorrido(obras: list[dict[str, Any]]) -> tuple[str | None, int] | None:
    """La obra con que se miden las pantallas de la obra: la de nombre más largo (la que más
    aprieta la cabecera de la obra y la barra lateral)."""
    if not obras:
        return None
    larga = max(obras, key=lambda o: len(str(o.get("obra", ""))))
    return (larga.get("carpeta"), int(larga["obra_id"]))


def medir_pantalla(
    contexto: Any,
    base: str,
    ruta: dict[str, Any],
    ancho: int,
    rol: str,
    capturas: Path,
    axe: str | None,
    oferta: set[str],
    letra: str,
    obra: tuple[str | None, int] | None,
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
        "accion": ruta["accion"],
        "modulo": ruta.get("modulo"),
        "ofrecida": ruta["id"] in oferta,
        "obra": list(obra) if obra and es_de_la_obra(ruta["id"]) else None,
    }
    try:
        inicio = time.monotonic()
        destino = hash_de(ruta["id"], obra if es_de_la_obra(ruta["id"]) else None)
        pagina.goto(f"{base}/app/{destino}", wait_until="domcontentloaded")
        try:
            # Una pantalla que el marco no ofrece al rol se espera poco: no es un error de carga.
            espera = LIMITE_CARGA_MS if fila["ofrecida"] else 3000
            pagina.wait_for_selector("main h1:not([data-esqueleto])", timeout=espera)
            fila["ms_hasta_h1"] = round((time.monotonic() - inicio) * 1000)
        except Exception:
            fila["ms_hasta_h1"] = None
        with contextlib.suppress(Exception):
            pagina.wait_for_load_state("networkidle", timeout=3000)
        fila["ms_hasta_reposo"] = round((time.monotonic() - inicio) * 1000)
        captura = capturas / f"{rol}_{ancho}_{letra}_{ruta['id']}.png"
        _medir_cargada(pagina, fila, axe, captura)
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
    base_fila = {"rol": rol, "ancho": ancho, "letra": letra, "recorrido": True, "ofrecida": True}
    try:
        pagina.goto(f"{base}/app/{hash_de('auditoria')}", wait_until="domcontentloaded")
        pagina.wait_for_selector("main h1", timeout=LIMITE_CARGA_MS)
        pagina.locator("main input[type=file]").first.set_input_files(str(libro))
        pagina.get_by_role("button", name="Auditar con recorrido guiado").click()
        pagina.wait_for_function(
            "p => new RegExp(p).test(location.hash) && document.querySelector('main h1') !== null",
            arg=patron_de_hash("libros"),
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


# --------------------------- umbrales de las barras ----------------------------------------------

# Un nombre de cuenta ficticio más largo que el tope de `.silice-cuenta__nombre`: el umbral cuenta
# con la cuenta de nombre más largo posible, no con «Ana».
CUENTA_LARGA_JS = """() => document.querySelectorAll('.silice-cuenta__nombre').forEach(e => {
  e.textContent = 'Persona Ficticia de Nombre Muy Largo para Medir'; })"""
# Por qué las barras no caben (vacío si caben): las de `BARRAS_JS`, después de dos cuadros.
CABE_JS = (
    """async () => {
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  const barras = ("""
    + BARRAS_JS
    + """)();
  const motivos = [];
  for (const b of barras) {
    if (b.desborda) motivos.push('barra «' + b.barra + '» desborda');
    for (const f of b.fuera) motivos.push('barra «' + b.barra + '»: ' + f + ' fuera de la ventana');
    for (const r of b.recortes) motivos.push(r);
  }
  return motivos;
}"""
)
# El marco se diseña desde 1056 px (DESIGN.md): por debajo no se mide ni se fija umbral.
UMBRAL_MINIMO = 1055.98


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
    """El menor ancho desde el que las barras caben en todos los anchos (`barrido` de 8 en 8 px y
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


# Dónde se mide el umbral: la obra en una subvista de Control de obra (cabecera de la obra, nueve
# secciones y tres vistas), cada espacio de la empresa y la Cuenta (seis secciones).
LUGARES_DE_UMBRAL = ("obra", "produccion", "auditoria", "precios", "cuenta")


def _hash_del_lugar(lugar: str, obra: tuple[str | None, int] | None) -> str | None:
    if lugar == "obra":
        return None if obra is None else hash_de("reajuste", obra)
    if lugar == "cuenta":
        return "#/cuenta/preferencias"
    return f"#/{lugar}"


def medir_umbrales(
    navegador: Any,
    base: str,
    claves: dict[str, str],
    roles: list[str],
    letras: list[str],
    capturas: Path,
) -> dict[str, Any]:
    """Por rol, lugar y letra: el menor ancho en que la barra de arriba y las barras de pestañas
    caben, con la obra de nombre más largo de la siembra y la cuenta de nombre más largo."""
    medidas: list[dict[str, Any]] = []
    for rol in roles:
        contexto = navegador.new_context(viewport={"width": 1366, "height": ALTO})
        pagina = contexto.new_page()
        entrar(pagina, base, rol, claves[rol])
        pagina.close()
        obra = obra_del_recorrido(obras_de_la_siembra(contexto, base))
        for lugar in LUGARES_DE_UMBRAL:
            hash_ = _hash_del_lugar(lugar, obra)
            if hash_ is None:
                continue
            for letra in letras:
                pagina = contexto.new_page()
                fijar_letra(pagina, letra)
                pagina.set_viewport_size({"width": 3000, "height": ALTO})
                fila: dict[str, Any] = {"rol": rol, "lugar": lugar, "letra": letra, "hash": hash_}
                try:
                    pagina.goto(f"{base}/app/{hash_}", wait_until="domcontentloaded")
                    pagina.wait_for_selector(
                        "main h1:not([data-esqueleto])", timeout=LIMITE_CARGA_MS
                    )
                    with contextlib.suppress(Exception):
                        pagina.wait_for_load_state("networkidle", timeout=4000)
                    fila["tal_cual"] = medir_umbral(pagina)
                    pagina.evaluate(CUENTA_LARGA_JS)
                    fila["cuenta_larga"] = medir_umbral(pagina)
                    fila["umbral"] = umbral_de_la_fila(
                        [fila[m]["umbral"] for m in ("tal_cual", "cuenta_larga")]
                    )
                    fila["cabe_desde"] = (
                        None if fila["umbral"] is None else round(fila["umbral"] + 0.02)
                    )
                    if fila["cabe_desde"]:
                        pagina.set_viewport_size({"width": fila["cabe_desde"], "height": ALTO})
                        pagina.screenshot(path=str(capturas / f"umbral_{rol}_{lugar}_{letra}.png"))
                except Exception as error:
                    fila["error"] = str(error)[:300]
                pagina.close()
                medidas.append(fila)
                print(
                    f"umbral {rol:5} {lugar:10} {letra:10} cabe desde {fila.get('cabe_desde')} "
                    f"{fila.get('error', '')}"
                )
        contexto.close()
    return {
        "medidas": medidas,
        "umbrales": umbrales_por_lugar(medidas),
        "sin_medir": umbrales_sin_medir(medidas),
    }


def umbrales_por_lugar(medidas: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    """Por lugar y letra, el umbral más exigente de los medidos (roles), nunca por debajo de
    1055,98 px. Una medida sin umbral o con error deja la casilla en `None` (sin umbral): no se
    descarta en silencio (`umbrales_sin_medir` dice cuál y por qué)."""
    grupos: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for m in medidas:
        grupos.setdefault((m["lugar"], m["letra"]), []).append(m)
    salida: dict[str, dict[str, float | None]] = {}
    for (lugar, letra), grupo in grupos.items():
        umbral = umbral_de_la_fila([None if "error" in m else m.get("umbral") for m in grupo])
        salida.setdefault(lugar, {})[letra] = None if umbral is None else max(umbral, UMBRAL_MINIMO)
    return salida


def umbrales_sin_medir(medidas: list[dict[str, Any]]) -> list[str]:
    """Las medidas que dejan su casilla sin umbral, con su causa."""
    salida = []
    for m in medidas:
        cabeza = f"{m['lugar']} {m['letra']} ({m['rol']})"
        if "error" in m:
            salida.append(f"{cabeza}: error {m['error']}")
        elif m.get("umbral") is None:
            salida.append(f"{cabeza}: no cabe ni en la ventana más ancha")
    return salida


def umbral_de_la_fila(umbrales: list[float | None]) -> float | None:
    """El más exigente de las medidas de una misma pantalla; si una no tiene umbral (no cabe ni
    en la ventana más ancha), la fila tampoco."""
    if not umbrales or any(u is None for u in umbrales):
        return None
    return max(u for u in umbrales if u is not None)


LIENZO_JS = """() => {
  const de = document.documentElement;
  const lienzos = [...document.querySelectorAll('.visor__hoja canvas')]
    .map(c => c.getBoundingClientRect()).filter(r => r.width > 0 && r.height > 0);
  const mayor = lienzos.sort((a, b) => b.width * b.height - a.width * a.height)[0];
  const hoja = document.querySelector('.visor__hoja');
  const rh = hoja ? hoja.getBoundingClientRect() : null;
  return {
    lienzo: mayor ? { ancho: Math.round(mayor.width), alto: Math.round(mayor.height),
      caja: [mayor.left, mayor.top, mayor.right, mayor.bottom].map(Math.round) } : null,
    hoja: rh ? [rh.left, rh.top, rh.right, rh.bottom].map(Math.round) : null,
    scroll_x: de.scrollWidth > de.clientWidth,
    scroll_y: de.scrollHeight > de.clientHeight,
    alto_documento: de.scrollHeight,
  };
}"""


def _axe_ids(pagina: Any, axe: str | None) -> list[str] | None:
    if not axe:
        return None
    pagina.evaluate(axe)
    return pagina.evaluate(
        "async () => (await axe.run(document, "
        "{runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa']})).violations.map(v => v.id)"
    )


def _esperar_visor(pagina: Any) -> None:
    pagina.locator(".visor__cuerpo").wait_for(timeout=LIMITE_ESPERA_MS)
    pagina.locator(".visor__hoja canvas").first.wait_for(timeout=LIMITE_ESPERA_MS)
    pagina.wait_for_timeout(1200)


def medir_visor(
    contexto: Any,
    base: str,
    libro: Path,
    ancho: int,
    letra: str,
    rol: str,
    capturas: Path,
    axe: str | None,
) -> dict[str, Any]:
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": ancho, "height": ALTO})
    fijar_letra(pagina, letra)
    errores: list[str] = []
    avisos: list[str] = []
    # En qué momento del recorrido llega cada error o aviso (abrir, otra hoja, salir 1, volver 1…).
    fase = ["abrir"]
    pagina.on("pageerror", lambda e: errores.append(f"[{fase[0]}] pageerror: {str(e)[:200]}"))
    pagina.on(
        "console",
        lambda m: (
            errores.append(f"[{fase[0]}] {m.text[:200]}")
            if m.type == "error"
            else avisos.append(f"[{fase[0]}] {m.text[:200]}")
            if m.type == "warning"
            else None
        ),
    )
    fila: dict[str, Any] = {"rol": rol, "ancho": ancho, "letra": letra, "vueltas": 0}
    prefijo = capturas / f"visor_{rol}_{ancho}_{letra}"
    try:
        _ir_y_esperar(pagina, base, "libros")
        pagina.locator("main input[type=file]").first.set_input_files(str(libro))
        _esperar_visor(pagina)
        fila.update(pagina.evaluate(LIENZO_JS))
        fila["axe_libro"] = _axe_ids(pagina, axe)
        pagina.screenshot(path=f"{prefijo}_hoja1.png")
        pestanas = pagina.get_by_role("tablist", name="Hojas del libro").get_by_role("tab")
        fila["hojas"] = pestanas.count()
        if fila["hojas"] > 1:
            fase[0] = "otra hoja"
            pestanas.nth(1).click()
            pagina.wait_for_timeout(1200)
            fila["axe_segunda_hoja"] = _axe_ids(pagina, axe)
            fila["segunda_hoja"] = pagina.evaluate(LIENZO_JS)
            pagina.screenshot(path=f"{prefijo}_hoja2.png")
        for vuelta in (1, 2):
            fase[0] = f"salir {vuelta}"
            ir_por_hash(pagina, "auditoria")
            pagina.wait_for_timeout(1500)
            fase[0] = f"volver {vuelta}"
            ir_por_hash(pagina, "libros")
            _esperar_visor(pagina)
            fila["vueltas"] += 1
        fase[0] = "salir 3"
        ir_por_hash(pagina, "auditoria")
        pagina.wait_for_timeout(1500)
    except Exception as error:
        fila["error"] = str(error)[:300]
    # Cuántos hay por fase, sin tope; de texto, una muestra de 12.
    fila["errores_por_fase"] = contar_por_fase(errores)
    fila["avisos_por_fase"] = contar_por_fase(avisos)
    fila["errores"] = errores[:12]
    fila["avisos"] = avisos[:12]
    pagina.close()
    return fila


def contar_por_fase(textos: list[str]) -> dict[str, int]:
    """Cuántos errores o avisos llegaron en cada fase («[abrir] …» → «abrir»), sin tope."""
    cuenta: dict[str, int] = {}
    for texto in textos:
        fase = texto[1:].split("]", 1)[0] if texto.startswith("[") and "]" in texto else "sin fase"
        cuenta[fase] = cuenta.get(fase, 0) + 1
    return cuenta


def fallos_visor(m: dict[str, Any]) -> list[str]:
    """Lo que la medida del visor deja en rojo (vacío si todo está bien)."""
    fallos: list[str] = []
    if "error" in m:
        fallos.append(f"error {m['error']}")
    for clave in ("axe_libro", "axe_segunda_hoja"):
        if "aria-valid-attr-value" in (m.get(clave) or []):
            fallos.append(f"{clave}: aria-valid-attr-value")
    if m.get("errores_por_fase"):
        fallos.append(
            "errores por fase: "
            + ", ".join(f"{fase} {n}" for fase, n in m["errores_por_fase"].items())
        )
    fallos += [f"error en la página: {e}" for e in m.get("errores", [])]
    fallos += [
        f"aviso de consola: {a}" for a in m.get("avisos", []) if re.search(r"Univer lanz", a)
    ]
    lienzo = m.get("lienzo")
    if not lienzo or not lienzo.get("ancho") or not lienzo.get("alto"):
        fallos.append(f"sin lienzo de la hoja: {lienzo}")
    # El alto del documento se anota (`scroll_y`, `alto_documento`); a lo ancho no debe desplazarse.
    if m.get("scroll_x"):
        fallos.append("desplazamiento horizontal de la página con el libro abierto")
    if m.get("vueltas", 0) < 2:
        fallos.append(f"solo {m.get('vueltas', 0)} vueltas de salir y volver a «libros»")
    return fallos


# --------------------------- umbrales de la barra por módulo (MOD-5) ----------------------------

# Muestra la navegación de la barra aunque el umbral actual la esconda (y Carbon por debajo de
# 1056 px): así se mide si cabe, no si está escondida.
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
    pagina.goto(f"{base}/app/{hash_de('auditoria')}", wait_until="domcontentloaded")
    pagina.wait_for_selector("h1", timeout=LIMITE_CARGA_MS)
    c.anotar("pantalla", "Inicio de auditoría", pantalla="auditoria")
    c.anotar("decision", "soltar el Excel aquí o ir al área «Auditar» de la barra")
    if desde == "libros":
        enlace = pagina.locator(f"a[href$='{hash_de('libros')}']").first
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
    pagina.goto(f"{base}/app/{hash_de('revisar')}", wait_until="domcontentloaded")
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
    """A la pantalla `ruta` (su id) por su ruta canónica, sin recargar; espera a que la dirección
    sea la suya (la de la obra, si redirige) y a su h1."""
    pagina.evaluate("h => { location.hash = h; }", hash_de(ruta))
    pagina.wait_for_function(
        "p => new RegExp(p).test(location.hash) && document.querySelector('main h1') !== null",
        arg=patron_de_hash(ruta),
        timeout=LIMITE_CARGA_MS,
    )
    with contextlib.suppress(Exception):
        pagina.wait_for_load_state("networkidle", timeout=3000)


def esperar_ruta(pagina: Any, ruta: str) -> None:
    """Hasta que la dirección es la de la pantalla y su h1 (no el del esqueleto) está a la vista."""
    pagina.wait_for_function(
        "p => new RegExp(p).test(location.hash)"
        " && document.querySelector('main h1:not([data-esqueleto])') !== null",
        arg=patron_de_hash(ruta),
        timeout=LIMITE_CARGA_MS,
    )
    with contextlib.suppress(Exception):
        pagina.wait_for_load_state("networkidle", timeout=3000)


def _abrir_costos(lateral: Any) -> None:
    """«Costos y producción» de la barra lateral es plegable: se despliega si hace falta."""
    grupo = lateral.locator("nav.silice-marco-lateral__costos")
    boton = grupo.locator("button[aria-expanded]")
    if boton.count() and boton.first.get_attribute("aria-expanded") != "true":
        boton.first.click(timeout=LIMITE_PASO_MS)


def _enlace_de_la_obra(pagina: Any, obra: tuple[str | None, int]) -> Any:
    """La fila de la obra en la barra lateral (su enlace lleva a su Resumen)."""
    destino = f"#/obra/{_segmento_de_carpeta(obra[0])}/{obra[1]}/resumen"
    return pagina.locator(f'aside.silice-marco-lateral a[href="{destino}"]').first


def ir_por_el_marco(pagina: Any, ruta: str, obra: tuple[str | None, int] | None = None) -> str:
    """Como una persona, por el marco de F6 (`camino_por_el_marco`): la obra en la barra lateral
    (la dada o, sin ella, la de la dirección actual), un espacio en «Costos y producción», la
    Cuenta con el botón de la persona y, después, cada pestaña en su barra. Devuelve el camino."""
    lateral = pagina.locator("aside.silice-marco-lateral")
    pasos: list[str] = []
    for paso in camino_por_el_marco(ruta):
        if paso["donde"] == "lateral" and paso["nombre"] == "obra":
            obra = obra or obra_de_la_direccion(pagina.evaluate("() => location.hash"))
            if obra is None:
                raise RuntimeError(f"«{ruta}» es de una obra y no hay obra elegida")
            enlace = _enlace_de_la_obra(pagina, obra)
            pasos.append(f"barra lateral › {enlace.inner_text(timeout=LIMITE_PASO_MS).strip()}")
            enlace.click(timeout=LIMITE_PASO_MS)
            pagina.wait_for_function(
                "p => location.hash.startsWith(p)",
                arg=f"#/obra/{_segmento_de_carpeta(obra[0])}/{obra[1]}/",
                timeout=LIMITE_CARGA_MS,
            )
        elif paso["donde"] == "lateral":
            if paso["nombre"] != "Vista general":
                _abrir_costos(lateral)
            lateral.get_by_role("link", name=paso["nombre"], exact=False).first.click(
                timeout=LIMITE_PASO_MS
            )
            pasos.append(f"barra lateral › {paso['nombre']}")
        elif paso["donde"] == "cuenta":
            pagina.locator("header.silice-marco-barra a.silice-cuenta__boton").click(
                timeout=LIMITE_PASO_MS
            )
            pasos.append("Cuenta")
        else:
            barra = pagina.get_by_role("navigation", name=paso["barra"], exact=True)
            barra.get_by_role("link", name=paso["nombre"], exact=True).click(timeout=LIMITE_PASO_MS)
            pasos.append(f"{paso['barra']} › {paso['nombre']}")
        with contextlib.suppress(Exception):
            pagina.wait_for_load_state("networkidle", timeout=3000)
    esperar_ruta(pagina, ruta)
    return " / ".join(pasos)


def caso_de_la_sesion(pagina: Any) -> str | None:
    """La carpeta que la API tiene para esta sesión (no la que muestra la barra de arriba)."""
    return pagina.evaluate(
        "async () => { const r = await fetch('/v1/casos', {credentials: 'same-origin'});"
        " if (!r.ok) return null; const d = await r.json();"
        " return d && d.actual ? d.actual.nombre : null; }"
    )


def carpeta_mostrada_y_real(pagina: Any) -> dict[str, Any]:
    """Control del marco en cada fila: la carpeta que la barra de arriba MUESTRA («Carpeta activa:
    …», con el título que da el servidor) frente al título de la carpeta de la sesión
    (`GET /v1/obras/todas`, `carpeta_actual_titulo`). Sin lectura de obras no se compara."""
    texto = pagina.locator("header.silice-marco-barra .silice-marco-barra__carpeta").first
    mostrada = texto.inner_text(timeout=4000).removeprefix("Carpeta activa:").strip() or None
    real = pagina.evaluate(
        "async () => { const r = await fetch('/v1/obras/todas', {credentials: 'same-origin'});"
        " if (!r.ok) return null; const d = await r.json();"
        " return d ? d.carpeta_actual_titulo : null; }"
    )
    return {
        "carpeta_mostrada": mostrada,
        "carpeta_api": real,
        "carpeta_coincide": None if mostrada is None or real is None else mostrada == real,
    }


def elegir_contexto(
    pagina: Any, carpeta: str | None, proyecto: str | None
) -> tuple[str | None, int] | None:
    """La carpeta y la obra de la fila, por el marco: se entra en la obra desde la barra lateral
    (con `proyecto`, esa; sin él, la primera de la carpeta), lo que fija también su carpeta en la
    sesión. Quien no lee obras (el administrador) abre la carpeta en Cuenta › Carpetas. Devuelve la
    obra elegida (None si no hace falta ninguna). Se comprueba contra la API."""
    if not carpeta and not proyecto:
        return None
    respuesta = api(pagina, "GET", "/v1/obras/todas")
    obras = respuesta["datos"].get("obras", []) if respuesta["estado"] == 200 else []
    elegida = obra_para(obras, carpeta, proyecto)
    if elegida is not None:
        obra = (elegida.get("carpeta"), int(elegida["obra_id"]))
        ir_por_hash(pagina, PAGINA_DE_LA_VISTA_GENERAL)
        _enlace_de_la_obra(pagina, obra).click(timeout=LIMITE_PASO_MS)
        esperar_ruta(pagina, "obras")
    elif proyecto:
        raise RuntimeError(f"no hay obra «{proyecto}» en la carpeta «{carpeta}»")
    else:
        obra = None
        pagina.goto(pagina.url.split("#", 1)[0] + "#/cuenta/carpetas")
        nombre = (carpeta or "").removesuffix(".db")
        pagina.get_by_role("button", name=f"Abrir {nombre}", exact=True).click(
            timeout=LIMITE_PASO_MS
        )
    fin = time.monotonic() + LIMITE_PASO_MS / 1000
    while carpeta and caso_de_la_sesion(pagina) != carpeta:
        if time.monotonic() > fin:
            raise RuntimeError(f"la carpeta de la sesión no cambió a «{carpeta}»")
        pagina.wait_for_timeout(300)
    return obra


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
        return "ir por el marco: " + ir_por_el_marco(pagina, paso["ruta"])
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
        obra = elegir_contexto(pagina, fila.get("carpeta"), fila.get("proyecto"))
        resultado["camino"] = ir_por_el_marco(pagina, fila["ruta"], obra)
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


def fallos_de_la_fila(fila: dict[str, Any]) -> list[str]:
    """Lo que está mal en una medición, en el orden en que se revisa. Una pantalla que el marco no
    ofrece al rol (escrita a mano) puede quedar sin h1 propio: no cuenta como fallo de diseño."""
    if "error" in fila:
        return [f"error: {fila['error']}"]
    fallos: list[str] = []
    if fila.get("ofrecida") and fila.get("h1") != 1:
        fallos.append("sin un h1" if not fila.get("h1") else f"{fila['h1']} h1")
    if fila.get("scroll_x"):
        fallos.append("desplazamiento horizontal")
    if fila.get("letra_aplicada") != fila.get("letra"):
        fallos.append(f"letra no aplicada ({fila.get('letra_aplicada')} en vez de {fila['letra']})")
    for b in fila.get("barras", []):
        if b.get("desborda"):
            fallos.append(f"barra «{b['barra']}» desborda")
        if b.get("fuera"):
            fallos.append(f"barra «{b['barra']}»: fuera de la ventana {', '.join(b['fuera'])}")
        if b.get("repetidas"):
            fallos.append(f"barra «{b['barra']}»: repetidas {', '.join(b['repetidas'])}")
        for recorte in b.get("recortes", []):
            fallos.append(f"barra «{b['barra']}»: {recorte}")
    nombres = sin_nombre(fila.get("controles", []))
    if nombres:
        fallos.append("sin nombre: " + "; ".join(nombres[:4]))
    nuevas = axe_nuevas(fila)
    if nuevas:
        fallos.append("axe nuevas: " + ", ".join(nuevas))
    if fila.get("consola"):
        fallos.append(f"consola: {len(fila['consola'])}")
    if fila.get("red"):
        fallos.append(f"red: {len(fila['red'])}")
    return fallos


def resumir(filas: list[dict[str, Any]]) -> dict[str, Any]:
    """Cuántas mediciones y cuántas con fallos, por letra y por ancho; las filas con el recorrido
    guiado en curso se cuentan aparte (columna visible y sin tapar el contenido)."""
    medidas = [f for f in filas if not f.get("recorrido")]
    con_recorrido = [f for f in filas if f.get("recorrido")]

    def cuenta(grupo: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "mediciones": len(grupo),
            "con_fallos": sum(1 for f in grupo if fallos_de_la_fila(f)),
        }

    por_letra: dict[str, list[dict[str, Any]]] = {}
    por_ancho: dict[str, list[dict[str, Any]]] = {}
    for f in medidas:
        por_letra.setdefault(f["letra"], []).append(f)
        por_ancho.setdefault(str(f["ancho"]), []).append(f)
    return {
        **cuenta(medidas),
        "no_ofrecidas": sum(1 for f in medidas if not f.get("ofrecida")),
        "por_letra": {k: cuenta(v) for k, v in por_letra.items()},
        "por_ancho": {k: cuenta(v) for k, v in por_ancho.items()},
        "con_recorrido": {
            "mediciones": len(con_recorrido),
            "columna_no_visible": sum(1 for f in con_recorrido if not f.get("recorrido_visible")),
            "columna_solapa": sum(1 for f in con_recorrido if f.get("recorrido_solapa")),
        },
        "fallos": [
            f"{f['rol']} {f['ancho']} {f['letra']} {f['id']}: {'; '.join(fallos)}"
            for f in medidas
            if (fallos := fallos_de_la_fila(f))
        ],
    }


def letras_pedidas(valores: list[str]) -> list[str]:
    """`--letras normal,grande` o `--letras normal grande`; en el orden de `LETRAS`."""
    pedidas = {v.strip() for parte in valores for v in parte.split(",") if v.strip()}
    desconocidas = pedidas - set(LETRAS)
    if desconocidas or not pedidas:
        raise SystemExit(
            f"--letras: use {', '.join(LETRAS)} (no {', '.join(sorted(desconocidas))})"
        )
    return [letra for letra in LETRAS if letra in pedidas]


def anchos_pedidos(valores: list[str]) -> list[int]:
    """`--anchos 1056,1366` o `--anchos 1056 1366`: enteros positivos, ordenados y sin repetir."""
    partes = [v.strip() for parte in valores for v in str(parte).split(",") if v.strip()]
    if not partes or not all(p.isdigit() and int(p) > 0 for p in partes):
        raise SystemExit(f"--anchos: use enteros positivos en píxeles (no {', '.join(partes)!r})")
    return sorted({int(p) for p in partes})


def recorrer_rol(
    contexto: Any,
    base: str,
    rol: str,
    rutas: list[dict[str, Any]],
    args: argparse.Namespace,
    letras: list[str],
    anchos: list[int],
    capturas: Path,
    axe: str | None,
    libros: dict[str, Path],
    resultado: dict[str, Any],
) -> None:
    """Todas las medidas de un rol: por letra, ancho y pantalla, en la obra de nombre más largo."""
    obra = obra_del_recorrido(obras_de_la_siembra(contexto, base))
    oferta = oferta_del_marco(contexto, base, obra)
    resultado.setdefault("oferta_por_rol", {})[rol] = sorted(oferta)
    resultado.setdefault("obra_por_rol", {})[rol] = list(obra) if obra else None
    for letra in letras:
        for ancho in anchos:
            for ruta in rutas:
                fila = medir_pantalla(
                    contexto, base, ruta, ancho, rol, capturas, axe, oferta, letra, obra
                )
                resultado["pantallas"].append(fila)
                fallos = fallos_de_la_fila(fila)
                print(
                    f"{rol:5} {letra:10} {ancho} {ruta['id']:15} h1={fila.get('h1')} "
                    f"{fila.get('ms_hasta_h1')}ms {'; '.join(fallos) or 'ok'}"
                )
            # El recorrido empieza al auditar desde el inicio de Auditoría: solo quien audita.
            if not args.sin_recorrido and "libros" in oferta:
                for fila in medir_con_recorrido(
                    contexto, base, libros["limpio"], ancho, rol, capturas, axe, letra
                ):
                    resultado["pantallas"].append(fila)
                    print(
                        f"{rol:5} {letra:10} {ancho} recorrido/{fila['id']:9} "
                        f"h1={fila.get('h1')} columna={fila.get('recorrido_modo')} "
                        f"visible={fila.get('recorrido_visible')} "
                        f"solapa={fila.get('recorrido_solapa')} {fila.get('error', '')}"
                    )
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


def analizador() -> argparse.ArgumentParser:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--salida", type=Path, required=True)
    a.add_argument("--roles", nargs="+", default=list(ROLES), choices=list(ROLES))
    a.add_argument(
        "--anchos",
        nargs="+",
        default=[",".join(str(x) for x in ANCHOS)],
        help="anchos de la ventana en píxeles (con comas o espacios)",
    )
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
        "--sin-recorrido",
        action="store_true",
        help="no repite Libro y el inicio de Auditoría con el recorrido",
    )
    a.add_argument("--sin-pantallas", action="store_true", help="solo las medidas aparte")
    a.add_argument(
        "--umbrales", action="store_true", help="mide el umbral de las barras de cada lugar"
    )
    a.add_argument(
        "--visor", action="store_true", help="el visor del libro: axe, lienzo, salir y volver"
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
    return a


def main(argv: list[str] | None = None) -> int:
    args = analizador().parse_args(argv)
    if args.funcional:
        return main_funcional(args.salida, args.acciones, args.solo)

    letras = letras_pedidas(args.letras)
    anchos = anchos_pedidos(args.anchos)
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
        "anchos": anchos,
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
                        anchos,
                        capturas,
                        axe,
                        libros,
                        resultado,
                    )
                    contexto.close()
                if args.visor:
                    resultado["visor"] = []
                    for rol in [r for r in args.roles if r in ("ana", "rita")]:
                        contexto = navegador.new_context(viewport={"width": 1366, "height": ALTO})
                        pagina = contexto.new_page()
                        entrar(pagina, base, rol, claves[rol])
                        pagina.close()
                        for letra in letras:
                            for ancho in anchos:
                                m = medir_visor(
                                    contexto,
                                    base,
                                    libros["limpio"],
                                    ancho,
                                    letra,
                                    rol,
                                    capturas,
                                    axe or bajar_axe(salida),
                                )
                                m["fallos"] = fallos_visor(m)
                                resultado["visor"].append(m)
                                print(
                                    f"visor {rol:5} {letra:10} {ancho} lienzo={m.get('lienzo')} "
                                    f"{'; '.join(m['fallos']) or 'ok'}"
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
    (salida / "recorrido.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(resultado["resumen"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
