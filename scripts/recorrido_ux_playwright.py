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
        [--rutas inicio libros ...] [--url http://127.0.0.1:8501]

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


def rutas_de_la_interfaz() -> list[dict[str, str | None]]:
    """Las páginas de `rutas.ts` (id, título, acción), leídas del texto: es la única lista."""
    texto = RUTAS_TS.read_text(encoding="utf-8")
    bloque = texto.split("export const PAGINAS", 1)[1].split("export function paginaPorId", 1)[0]
    paginas: list[dict[str, str | None]] = []
    patron = re.compile(
        r'id:\s*"(?P<id>[^"]+)",\s*titulo:\s*"(?P<titulo>[^"]+)",\s*seccion:\s*"(?P<seccion>[^"]+)",'
        r"\s*accion:\s*(?P<accion>null|\"[^\"]+\")"
    )
    for m in patron.finditer(bloque):
        accion = m["accion"]
        paginas.append(
            {
                "id": m["id"],
                "titulo": m["titulo"],
                "seccion": m["seccion"],
                "accion": None if accion == "null" else accion.strip('"'),
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


def medir_pantalla(
    contexto: Any,
    base: str,
    ruta: dict[str, Any],
    ancho: int,
    rol: str,
    capturas: Path,
    axe: str | None,
    en_menu: set[str],
) -> dict[str, Any]:
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": ancho, "height": ALTO})
    consola: list[str] = []
    red: list[str] = []
    pagina.on("console", lambda m: consola.append(m.text[:200]) if m.type == "error" else None)
    pagina.on("pageerror", lambda e: consola.append(f"pageerror: {str(e)[:200]}"))
    pagina.on("requestfailed", lambda r: red.append(f"FALLA {r.method} {r.url[:120]}"))
    pagina.on(
        "response",
        lambda r: (
            red.append(f"{r.status} {r.request.method} {r.url[:120]}") if r.status >= 400 else None
        ),
    )
    fila: dict[str, Any] = {
        "rol": rol,
        "ancho": ancho,
        "id": ruta["id"],
        "titulo": ruta["titulo"],
        "seccion": ruta["seccion"],
        "accion": ruta["accion"],
    }
    try:
        inicio = time.monotonic()
        pagina.goto(f"{base}/app/#/{ruta['id']}", wait_until="domcontentloaded")
        try:
            # Una ruta que el menú del rol no ofrece se espera poco: no es un error de carga.
            espera = LIMITE_CARGA_MS if ruta["id"] in en_menu else 3000
            pagina.wait_for_selector("h1", timeout=espera)
            fila["ms_hasta_h1"] = round((time.monotonic() - inicio) * 1000)
        except Exception:
            fila["ms_hasta_h1"] = None
        with contextlib.suppress(Exception):
            pagina.wait_for_load_state("networkidle", timeout=3000)
        fila["ms_hasta_reposo"] = round((time.monotonic() - inicio) * 1000)
        fila.update(pagina.evaluate(MEDIR_JS))
        fila.pop("en_menu")
        fila["en_menu"] = ruta["id"] in en_menu
        if axe:
            try:
                pagina.evaluate(axe)
                r = pagina.evaluate(
                    "async () => (await axe.run(document, "
                    "{runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}))"
                    ".violations.map(v => ({id: v.id, impacto: v.impact, nodos: v.nodes.length}))"
                )
                fila["axe"] = r
            except Exception as error:
                fila["axe_error"] = str(error)[:150]
        destino = capturas / f"{rol}_{ancho}_{ruta['id']}.png"
        pagina.screenshot(path=str(destino), full_page=True)
        fila["captura"] = destino.name
    except Exception as error:
        fila["error"] = str(error)[:300]
    fila["consola"] = consola[:8]
    fila["red"] = red[:8]
    pagina.close()
    return fila


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


# --------------------------- orquestación -------------------------------------------------------


def resumir(filas: list[dict[str, Any]]) -> dict[str, Any]:
    def n(pred: Any) -> int:
        return sum(1 for f in filas if pred(f))

    return {
        "pantallas_medidas": len(filas),
        "con_error_de_carga": n(lambda f: "error" in f),
        "sin_h1": n(lambda f: f.get("h1") == 0),
        "con_varios_h1": n(lambda f: (f.get("h1") or 0) > 1),
        "con_scroll_horizontal": n(lambda f: f.get("scroll_x")),
        "con_errores_de_consola": n(lambda f: f.get("consola")),
        "con_errores_de_red": n(lambda f: f.get("red")),
        "con_violaciones_axe": n(lambda f: f.get("axe")),
        "sin_axe": n(lambda f: "axe" not in f),
    }


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--salida", type=Path, required=True)
    a.add_argument("--roles", nargs="+", default=list(ROLES), choices=list(ROLES))
    a.add_argument("--anchos", nargs="+", type=int, default=[1366, 1056])
    a.add_argument("--rutas", nargs="*", help="ids de página; por omisión todas las de rutas.ts")
    a.add_argument("--sin-axe", action="store_true")
    a.add_argument("--sin-flujo", action="store_true")
    a.add_argument("--url", help="servidor ya en marcha (usa las cuentas ficticias por omisión)")
    args = a.parse_args(argv)

    salida: Path = args.salida
    capturas = salida / "capturas"
    capturas.mkdir(parents=True, exist_ok=True)
    rutas = [r for r in rutas_de_la_interfaz() if not args.rutas or r["id"] in args.rutas]
    axe = None if args.sin_axe else bajar_axe(salida)

    temporal = Path(tempfile.mkdtemp(prefix="datos_ux_", dir=salida))  # se borra al final
    claves = sembrar_datos(temporal)
    servidor: Servidor | None = None
    base = args.url.rstrip("/") if args.url else ""
    if not args.url:
        servidor = Servidor(temporal, puerto_libre())
        base = servidor.url
    resultado: dict[str, Any] = {
        "base": base,
        "rutas": len(rutas),
        "axe": bool(axe),
        "pantallas": [],
        "flujos": [],
    }
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
                    for ancho in args.anchos:
                        for ruta in rutas:
                            fila = medir_pantalla(
                                contexto, base, ruta, ancho, rol, capturas, axe, en_menu
                            )
                            resultado["pantallas"].append(fila)
                            print(
                                f"{rol:5} {ancho} {ruta['id']:15} h1={fila.get('h1')} "
                                f"scrollX={fila.get('scroll_x')} {fila.get('ms_hasta_h1')}ms"
                            )
                    if not args.sin_flujo and rol in ("ana", "rita"):
                        libros = libros_ficticios(salida / "libros_ficticios")
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
        shutil.rmtree(temporal, ignore_errors=True)
    resultado["resumen"] = resumir(resultado["pantallas"])
    (salida / "recorrido.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(resultado["resumen"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
