"""La capa del recorrido que conoce el marco del front (partida de
`recorrido_ux_playwright.py` el 2026-11-27, como `recorrido_carga.py`): lee las rutas de
`rutas.ts`, `espacios.ts`, `secciones.ts` y `herramientas.ts`, arma el mapa del marco, la ruta
canónica de cada pantalla, los caminos para llegar a ella como una persona y el umbral medido.
`recorrido_ux_playwright.py` la reexporta: las pruebas siguen tomando los nombres de allí."""

from __future__ import annotations

import functools
import re
import urllib.parse
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]

RUTAS_TS = RAIZ / "frontend-desktop" / "src" / "shell" / "rutas.ts"
# Dónde vive cada pantalla desde F6 (contrato de rutas 2026-11-04): los espacios, las subvistas y la
# Cuenta en `espacios.ts`; las secciones de la obra y la Vista general en `secciones.ts`.
ESPACIOS_TS = RAIZ / "frontend-desktop" / "src" / "marco" / "espacios.ts"
SECCIONES_TS = RAIZ / "frontend-desktop" / "src" / "marco" / "secciones.ts"
# La barra de la obra en dos filas (lote C4, cara «Papel y resaltador», 2026-11-26): las
# herramientas Presupuestar, Auditar y Anticipar y las opciones de cada una.
HERRAMIENTAS_TS = RAIZ / "frontend-desktop" / "src" / "marco" / "herramientas.ts"

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
# La sección que no es de ninguna herramienta y se abre desde el menú «Versión» (`herramientaDe`).
SECCION_DEL_MENU_DE_VERSION = "versiones"
# Los nombres accesibles que el marco escribe en su JSX (no en una tabla), con el archivo de
# `frontend-desktop/src/marco/` donde están: la prueba del recorrido comprueba que sigan allí.
ROTULOS_DEL_MARCO: dict[str, tuple[str, str]] = {
    # La primera opción de la barra lateral, la de la Vista general (se pulsa por su dirección).
    "inicio": ('texto: "Inicio"', "BarraLateral.tsx"),
    "herramientas": ('aria-label="Herramientas de la obra"', "BarraDeObra.tsx"),
    "opciones": ("aria-label={`Opciones de ${tituloDeLaFila}`}", "BarraDeObra.tsx"),
    "opciones_de_la_portada": ('actual === "portada" ? "la portada"', "BarraDeObra.tsx"),
    "portada": ("Portada de la obra", "BarraDeObra.tsx"),
    "version": ('MenuButton label="Versión"', "BarraDeObra.tsx"),
    "versiones": (
        'titulo: "Versiones", ruta: rutaDeObra(carpeta, obraId, "versiones")',
        "BarraDeObra.tsx",
    ),
    "vistas": ("etiqueta={`Vistas de ${def.titulo}`}", "EspacioDeObra.tsx"),
    "cuenta": ('etiqueta="Secciones de la cuenta"', "EspacioDeCuenta.tsx"),
}
NOMBRE_DE_INICIO = "Inicio"
BARRA_DE_HERRAMIENTAS = "Herramientas de la obra"
OPCIONES_DE = "Opciones de "
OPCIONES_DE_LA_PORTADA = "la portada"
PORTADA_DE_LA_OBRA = "Portada de la obra"
MENU_DE_VERSION = "Versión"
OPCION_VERSIONES = "Versiones"
VISTAS_DE = "Vistas de "
SECCIONES_DE_LA_CUENTA = "Secciones de la cuenta"


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
    entrada = re.search(r'SECCION_DE_ENTRADA:\s*SeccionId\s*=\s*"([^"]+)"', secciones)
    if entrada is None:
        raise ValueError(f"{SECCIONES_TS.name}: no se encuentra SECCION_DE_ENTRADA")
    texto = HERRAMIENTAS_TS.read_text(encoding="utf-8")
    bloque = _bloque_ts(
        texto, "export const HERRAMIENTAS_DE_OBRA", "export function herramientaDe", HERRAMIENTAS_TS
    )
    herramientas = [
        {"id": id_, "titulo": titulo, "secciones": re.findall(r'"([^"]+)"', lista)}
        for id_, titulo, lista in re.findall(
            r'\{\s*id:\s*"(\w+)",\s*titulo:\s*"([^"]*)",\s*secciones:\s*\[([^\]]*)\]', bloque
        )
    ]
    bloque = _bloque_ts(
        texto,
        "export const OPCIONES_DE_HERRAMIENTA",
        "export function rutaDeOpcion",
        HERRAMIENTAS_TS,
    ).split("= {", 1)[-1]
    opciones = {
        grupo: [
            {"id": id_, "titulo": titulo, "seccion": seccion, "subvista": subvista}
            for id_, titulo, seccion, subvista in re.findall(
                r'\{\s*id:\s*"([^"]*)",\s*titulo:\s*"([^"]*)",\s*seccion:\s*"([^"]*)",'
                r'\s*subvista:\s*"([^"]*)"\s*\}',
                lista,
            )
        ]
        for grupo, lista in re.findall(r"(\w+):\s*\[(.*?)\]", bloque, flags=re.DOTALL)
    }
    if not herramientas or "portada" not in opciones:
        raise ValueError(f"{HERRAMIENTAS_TS.name}: no se leen las herramientas de la obra")
    return {
        "vista_general": vista[1],
        "entrada": entrada[1],
        "herramientas": herramientas,
        "opciones": opciones,
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


def pagina_de_entrada_de_la_obra() -> str:
    """La pantalla con que abre una obra desde la barra lateral (`SECCION_DE_ENTRADA`, B1-10)."""
    mapa = mapa_del_marco()
    return next(p for p, s in mapa["obra"].items() if s == mapa["entrada"])


def ruta_de_entrada(obra: tuple[str | None, int]) -> str:
    """El `href` de la fila de la obra en la barra lateral: su sección de entrada."""
    return "#" + ruta_canonica(pagina_de_entrada_de_la_obra(), obra)


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
    pantalla del registro (Pendientes, «Configuración», un segmento desconocido o una
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


def _grupo_de_la_seccion(seccion: str) -> dict[str, Any] | None:
    """La herramienta de la obra (Presupuestar, Auditar, Anticipar) que agrupa la sección, o
    `None` si no es de ninguna (la portada o Versiones), como `herramientaDe`."""
    return next((h for h in mapa_del_marco()["herramientas"] if seccion in h["secciones"]), None)


def _camino_en_la_obra(seccion: str, subvista: str) -> list[dict[str, str]]:
    """Los clics dentro de la barra de la obra desde su sección de entrada (C4): la herramienta en
    «Herramientas de la obra» (o el nombre de la obra, que lleva a la portada), su opción en
    «Opciones de …» y, si la subvista no es opción de esa fila (Mercado › Actualizar precios), su
    pestaña en «Vistas de …». Versiones se abre en el menú «Versión». No se pulsa lo que ya está
    abierto."""
    mapa = mapa_del_marco()
    if seccion == SECCION_DEL_MENU_DE_VERSION:
        return [{"donde": "menu", "menu": MENU_DE_VERSION, "nombre": OPCION_VERSIONES}]
    grupo, de_entrada = _grupo_de_la_seccion(seccion), _grupo_de_la_seccion(mapa["entrada"])
    camino: list[dict[str, str]] = []
    if grupo is None:
        camino.append({"donde": "portada", "nombre": PORTADA_DE_LA_OBRA})
        clave, fila, abierta = "portada", OPCIONES_DE + OPCIONES_DE_LA_PORTADA, ("resumen", "")
    else:
        clave, fila = grupo["id"], OPCIONES_DE + grupo["titulo"]
        abierta = (mapa["entrada"], "")
        if de_entrada is None or grupo["id"] != de_entrada["id"]:
            camino.append(
                {"donde": "barra", "barra": BARRA_DE_HERRAMIENTAS, "nombre": grupo["titulo"]}
            )
            abierta = (grupo["secciones"][0], "")
    opciones = mapa["opciones"][clave]
    por_lugar = {(o["seccion"], o["subvista"]): o for o in opciones}
    exacta, principal = por_lugar.get((seccion, subvista)), por_lugar.get((seccion, ""))
    elegida = exacta or principal
    if elegida is not None and (elegida["seccion"], elegida["subvista"]) != abierta:
        camino.append({"donde": "barra", "barra": fila, "nombre": elegida["titulo"]})
    if exacta is None and subvista:
        barra = VISTAS_DE + mapa["titulos"]["seccion"][seccion]
        nombre = mapa["titulos"]["subvista"][(seccion, subvista)]
        camino.append({"donde": "barra", "barra": barra, "nombre": nombre})
    return camino


def camino_por_el_marco(id_: str) -> list[dict[str, str]]:
    """Los clics con que una persona llega a la pantalla en el marco de hoy. Cada paso dice dónde
    se pulsa: `lateral` (la barra lateral: «Inicio», la obra elegida —`nombre` «obra»— o un
    espacio de «Costos y producción»), `cuenta` (el botón de la persona en la barra de arriba),
    `barra` (la barra de enlaces cuyo nombre accesible es `barra`), `portada` (el nombre de la obra
    en su barra) o `menu` (el menú de botón `menu` y su opción), y el texto del enlace. La obra
    abre en su sección de entrada (el Presupuesto, B1-10) y la Cuenta en su primera sección; un
    espacio, en su primera herramienta usable, y se pulsa siempre su pestaña."""
    if id_ not in {r["id"] for r in rutas_de_la_interfaz()}:
        raise ValueError(f"no hay pantalla «{id_}» en rutas.ts")
    mapa = mapa_del_marco()
    titulos = mapa["titulos"]
    if id_ == PAGINA_DE_LA_VISTA_GENERAL:
        return [{"donde": "lateral", "nombre": NOMBRE_DE_INICIO}]
    if es_de_la_obra(id_):
        seccion, subvista = mapa["obra"].get(id_), ""
        if seccion is None:
            seccion, subvista = mapa["subvista"][id_]
        return [{"donde": "lateral", "nombre": "obra"}, *_camino_en_la_obra(seccion, subvista)]
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
            "barra": SECCIONES_DE_LA_CUENTA,
            "nombre": titulos["cuenta"][seccion],
        },
    ]


def obra_para(
    obras: list[dict[str, Any]], carpeta: str | None, nombre: str | None
) -> dict[str, Any] | None:
    """La obra de `GET /v1/obras/todas` con que se recorre: la de esa carpeta (None, la de la
    empresa) cuyo nombre es `nombre` o, si ninguna se llama así, la primera cuyo nombre lo contiene
    (como el selector de obra de antes); sin nombre, la primera de la carpeta. Un nombre que no
    está en la carpeta da `None`: no se cambia por otra obra."""
    de_la_carpeta = [o for o in obras if o.get("carpeta") == carpeta]
    if nombre is None:
        return de_la_carpeta[0] if de_la_carpeta else None
    exacta = next((o for o in de_la_carpeta if o.get("obra") == nombre), None)
    return exacta or next((o for o in de_la_carpeta if nombre in str(o.get("obra", ""))), None)


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
