"""Arma todas las vistas de Silice con la paleta «Papel y resaltador», en claro y en oscuro.

Cada vista es un fragmento en fragmentos/<id>.html:
  linea 1: <!--{json con metadatos}-->
  luego el contenido de <main>, una linea <!--MARGEN--> y el contenido del margen (opcional).
El marco (barras, opciones al margen izquierdo) sale de los metadatos; el color, de los tokens.
Uso: python -I generar_vistas.py <carpeta project del lienzo> (CSS en estilos.css)
"""

import json
import sys
from pathlib import Path
from string import Template

RAIZ = Path(__file__).resolve().parent
FRAGMENTOS = RAIZ / "fragmentos"

TOKENS = {
    "claro": dict(
        esquema="light",
        fondo="#F7F4EE",
        hoja="#FDFBF7",
        alzado="#EFE9DF",
        linea="rgba(31,27,22,.10)",
        t1="#1F1B16",
        t2="#5E554A",
        t3="#9A9184",
        barra="#1F1B16",
        barra_t1="#EFE9DE",
        barra_t2="#AAA398",
        barra_linea="rgba(239,233,222,.18)",
        lateral="#EFE9DF",
        s1="#2A78D6",
        s2="#1BAF7A",
        s3="#EB6834",
        hover_tinta="#3A342C",
        acento="#1F1B16",
        acento_t="#FFFFFF",
        sel="#FFF4C2",
        sel_borde="#C9A227",
        nota_act="#FFF4C2",
        error="#B42318",
        adv="#8A5A00",
        ok="#2F6B3F",
        error_borde="#F2C4C0",
        adv_borde="#E6D3A6",
        ok_borde="#BFD8C6",
    ),
    "oscuro": dict(
        esquema="dark",
        fondo="#161513",
        hoja="#1C1A18",
        alzado="#262421",
        linea="rgba(239,233,222,.09)",
        t1="#EFE9DE",
        t2="#AAA398",
        t3="#8A847A",
        barra="#12110F",
        barra_t1="#EFE9DE",
        barra_t2="#AAA398",
        barra_linea="rgba(239,233,222,.14)",
        lateral="#12110F",
        s1="#3987E5",
        s2="#199E70",
        s3="#D95926",
        hover_tinta="#FFFFFF",
        acento="#EFE9DE",
        acento_t="#1C1A18",
        sel="#2E2919",
        sel_borde="#C9A227",
        nota_act="#2E2919",
        error="#F0857C",
        adv="#DDB25E",
        ok="#7FBF8E",
        error_borde="rgba(240,133,124,.35)",
        adv_borde="rgba(221,178,94,.35)",
        ok_borde="rgba(127,191,142,.35)",
    ),
}

FUENTES = (
    "https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600"
    "&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap"
)

# El CSS vive en estilos.css; sus $tokens salen de TOKENS segun el modo.
CSS = Template((RAIZ / "estilos.css").read_text(encoding="utf-8"))

ICONO_CHEVRON = (
    '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'
)
ICONO_MAS = (
    '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>'
)
ICONO_LUPA = (
    '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">'
    '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'
)

ESPACIOS = [
    ("obras", "Obras"),
    ("auditar", "Auditar un libro"),
    ("precios", "Precios y catálogo"),
    ("produccion", "Producción"),
]
HERRAMIENTAS = [
    ("presupuestar", "Presupuestar"),
    ("auditar", "Auditar"),
    ("anticipar", "Anticipar"),
]

# Opciones del margen izquierdo y la barra de abajo de cada lugar.
OPCIONES = {
    "obra:portada": ["Resumen", "Tablero"],
    "obra:presupuestar": [
        "Partidas",
        "Componer un APU",
        "Tramos de la vía",
        "Plano o cómputo",
        "Precios de mercado",
    ],
    "obra:auditar": ["Problemas de la obra", "Dictamen", "Revisar un paquete"],
    "obra:anticipar": ["Control de obra", "Reajuste de precios", "Riesgo", "Escenarios"],
    "obra:versiones": ["Versiones", "Pedir aprobación", "Entregar al cliente"],
    "inicio": ["Resumen", "Obras", "Pendientes"],
    "auditar": ["Subir y auditar Excel", "Libro de la empresa", "Historial de auditorías"],
    "precios": [
        "Precios de la empresa",
        "Catálogo de partidas e insumos",
        "Índices del BCV",
        "Simulador de listas",
    ],
    "produccion": [
        "Resumen de arenera",
        "Existencias",
        "Costos del período",
        "Costo por tonelada",
        "Receta de la planta",
        "Producir mezcla",
    ],
    "nueva": ["Datos de la obra", "Cómo empezar", "Dónde se guarda"],
    "cuenta": [
        "Configuración",
        "Contraseña",
        "Cuentas y permisos",
        "Empresa y tema",
        "Carpetas",
        "Especialidades, IA e instalación",
        "Ayuda y acerca de Sílice",
    ],
}
NOMBRE_DEL_LUGAR = {
    "inicio": ("Inicio", "Lo que hay cargado en Sílice"),
    "auditar": ("Auditar un libro", "Espacio de la empresa"),
    "precios": ("Precios y catálogo", "Espacio de la empresa"),
    "produccion": ("Producción", "Espacio de la empresa"),
    "nueva": ("Nueva obra", "Se creará en la carpeta Obras 2026"),
    "cuenta": ("Su cuenta", "Eugenio Pérez · administrador"),
}


def barra_empresa(meta: dict) -> str:
    nueva_actual = ' aria-current="page"' if meta["area"] == "nueva" else ""
    yo_actual = ' aria-current="page"' if meta["area"] == "cuenta" else ""
    return (
        '<header class="emp"><a href="#" class="marca">Sílice</a><span style="flex-grow:1"></span>'
        f'<a href="#" class="btn-res"{nueva_actual}>{ICONO_MAS}Nueva obra</a>'
        f'<button type="button" class="buscar">{ICONO_LUPA}Buscar <kbd>Ctrl K</kbd></button>'
        f'<a href="#" class="yo" aria-label="Cuenta de Eugenio"{yo_actual}>EP</a></header>'
    )


def acciones(meta: dict) -> str:
    partes = []
    if meta.get("meta"):
        partes.append(f'<span class="meta">{meta["meta"]}</span>')
    if meta.get("accion2"):
        partes.append(f'<button type="button" class="btn2">{meta["accion2"]}</button>')
    if meta["area"] == "obra":
        partes.append(
            '<button type="button" class="btn2" aria-haspopup="menu">'
            f"V2 · en elaboración {ICONO_CHEVRON}</button>"
        )
    if meta.get("accion"):
        partes.append(f'<button type="button" class="btn1">{meta["accion"]}</button>')
    return f'<div class="acc">{"".join(partes)}</div>'


def clave_y_rotulo(meta: dict) -> tuple[str, str]:
    clave = f"obra:{meta['herramienta']}" if meta["area"] == "obra" else meta["area"]
    nombre = {"obra:portada": "Portada", "obra:versiones": "Versiones"}.get(clave)
    if nombre is None:
        nombre = (
            dict(HERRAMIENTAS).get(meta.get("herramienta", ""), "")
            if meta["area"] == "obra"
            else NOMBRE_DEL_LUGAR[meta["area"]][0]
        )
    return clave, nombre


def segunda_fila(meta: dict) -> str:
    clave, rotulo = clave_y_rotulo(meta)
    pestanas = "".join(
        f'<a href="#"{' aria-current="page"' if op == meta["opcion"] else ""}>{op}</a>'
        for op in OPCIONES[clave]
    )
    return f'<nav class="sub2" aria-label="Opciones de {rotulo}">{pestanas}</nav>'


def barra_del_lugar(meta: dict) -> str:
    if meta["area"] == "obra":
        herr = meta["herramienta"]
        portada = ' aria-current="page"' if herr == "portada" else ""
        pestanas = []
        for clave, texto in HERRAMIENTAS:
            actual = ' aria-current="page"' if clave == herr else ""
            extra = (
                ' <span class="cuenta" aria-label="3 problemas abiertos">3</span>'
                if clave == "auditar"
                else ""
            )
            pestanas.append(f'<a href="#"{actual}>{texto}{extra}</a>')
        fila1 = (
            f'<div class="sub"><a href="#" class="nombre"{portada}>'
            "<b>Vialidad Tramo 3</b><span>Portada de la obra</span></a>"
            f'<nav aria-label="Herramientas de la obra">{"".join(pestanas)}</nav>'
            f"{acciones(meta)}</div>"
        )
        return fila1 + segunda_fila(meta)
    titulo, subtitulo = NOMBRE_DEL_LUGAR[meta["area"]]
    fila1 = (
        f'<div class="sub"><div class="nombre"><b>{titulo}</b><span>{subtitulo}</span></div>'
        f"{acciones(meta)}</div>"
    )
    return fila1 + segunda_fila(meta)


def _fila(etiqueta: str, valor: str, extra: str = "") -> str:
    return (
        f'<a href="#" class="wf"><span class="we">{etiqueta}</span>'
        f'<span class="wv">{valor}</span>{extra}</a>'
    )


def widgets(meta: dict) -> str:
    area, herr = meta["area"], meta.get("herramienta")
    if area == "obra":
        if herr == "portada":
            return ""
        filas = {
            "presupuestar": _fila("Presupuesto V2", "1.284.560,00 Bs"),
            "auditar": _fila(
                "Problemas abiertos",
                '<span class="t-err">2 errores</span> · <span class="t-adv">1 advertencia</span>',
            ),
            "anticipar": _fila(
                "Avance al 15/11/2026",
                '38 % <span class="we">frente a 42 %</span>',
                '<div class="prog"><span style="width:38%"></span></div>',
            ),
        }
        cuerpo = "".join(v for k, v in filas.items() if k != herr)
        return (
            '<section class="wid" aria-label="La obra en cifras">'
            f'<span class="wt">La obra en cifras</span>{cuerpo}</section>'
        )
    datos = {
        "inicio": (
            "Esta semana",
            [
                ("Errores abiertos", '<span class="t-err">3 errores</span>'),
                ("Aprobaciones", "1 espera respuesta"),
                ("Precios", '<span class="t-adv">Advertencia</span> · 1 precio vencido'),
            ],
        ),
        "auditar": (
            "Último libro",
            [
                (
                    "Presupuesto cliente A.xlsx",
                    '<span class="t-err">3 errores</span> · '
                    '<span class="t-adv">3 advertencias</span>',
                ),
                ("Auditorías guardadas", "7"),
            ],
        ),
        "precios": (
            "Precios en uso",
            [
                ("Lista vigente", "Julio · vence 30/11/2026"),
                ("En el catálogo", "128 partidas · 42 insumos"),
            ],
        ),
        "produccion": (
            "Este mes",
            [
                ("Costo por tonelada", '258,40 Bs <span class="we">+3,7 % frente a octubre</span>'),
                ("Existencias", "1.320,0 t"),
            ],
        ),
        "cuenta": (
            "Su instalación",
            [
                ("Último respaldo", "14/11/2026"),
                ("Clave de firma", '<span class="estado ok">Vigente hasta 31/12/2026</span>'),
            ],
        ),
    }
    if area not in datos:
        return ""
    titulo, filas = datos[area]
    cuerpo = "".join(_fila(e, v) for e, v in filas)
    return (
        f'<section class="wid" aria-label="{titulo}">'
        f'<span class="wt">{titulo}</span>{cuerpo}</section>'
    )


# Trazos de los iconos (estilo lucide, trazo 1,5), en iconos.json.
TRAZOS = json.loads((RAIZ / "iconos.json").read_text(encoding="utf-8"))
ICONO_DE_OPCION = {
    "Resumen": "casa",
    "Tablero": "rejilla",
    "Partidas": "tabla",
    "Componer un APU": "calc",
    "Tramos de la vía": "ruta",
    "Plano o cómputo": "subir",
    "Precios de mercado": "linea",
    "Problemas de la obra": "alerta",
    "Dictamen": "firma",
    "Revisar un paquete": "caja",
    "Control de obra": "medidor",
    "Reajuste de precios": "ciclo",
    "Riesgo": "escudo",
    "Escenarios": "ramas",
    "Versiones": "reloj",
    "Pedir aprobación": "enviar",
    "Entregar al cliente": "caja",
    "Vista general": "rejilla",
    "Obras": "tabla",
    "Pendientes": "bandeja",
    "Subir y auditar Excel": "subir",
    "Libro de la empresa": "libro",
    "Historial de auditorías": "reloj",
    "Precios de la empresa": "etiqueta",
    "Catálogo de partidas e insumos": "lista",
    "Índices del BCV": "linea",
    "Simulador de listas": "mandos",
    "Resumen de arenera": "monte",
    "Existencias": "caja",
    "Costos del período": "recibo",
    "Costo por tonelada": "balanza",
    "Receta de la planta": "matraz",
    "Producir mezcla": "engrane",
    "Configuración": "engrane",
    "Contraseña": "llave",
    "Cuentas y permisos": "personas",
    "Empresa y tema": "paleta",
    "Carpetas": "carpeta",
    "Especialidades, IA e instalación": "chip",
    "Ayuda y acerca de Sílice": "ayuda",
    "Datos de la obra": "doc",
    "Cómo empezar": "inicio",
    "Dónde se guarda": "carpeta",
}
# Lo que la barra cuenta junto a una opcion (en el riel reducido va sobre el icono).
CUENTA_DE_OPCION = {"Problemas de la obra": "3", "Pendientes": "3"}


def icono(nombre: str) -> str:
    return f'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">{TRAZOS[nombre]}</svg>'


def opcion(texto: str, actual: bool) -> str:
    marca = ' aria-current="page"' if actual else ""
    cuenta = CUENTA_DE_OPCION.get(texto)
    extra = f'<span class="n">{cuenta}</span>' if cuenta else ""
    return f'<a href="#"{marca}>{icono(ICONO_DE_OPCION[texto])}<span>{texto}</span>{extra}</a>'


CARPETA = (
    f'<div class="carp">{icono("carpeta")}<span><span class="we">Carpeta abierta</span>'
    'Obras 2026</span><a href="#">Cambiar</a></div>'
)


ESPACIOS_LATERAL = [
    ("inicio", "Inicio", "casa"),
    ("auditar", "Auditar un libro", "libro"),
    ("precios", "Precios y catálogo", "etiqueta"),
    ("produccion", "Producción", "monte"),
]
# Obras de la demostración: problemas abiertos (cuenta, gravedad que manda, nombre accesible).
OBRAS_LATERAL = [
    ("Vialidad Tramo 3", "3", "err", "2 errores y 1 advertencia"),
    ("Rehabilitación Avenida Principal", "", "", ""),
    ("Puente Quebrada Seca", "1", "adv", "1 advertencia"),
    ("Drenaje Sector Norte", "1", "err", "1 error"),
]


def opciones(meta: dict) -> str:
    area = meta["area"]
    filas = ['<span class="grp">Espacios de la empresa</span>']
    for clave, texto, ic in ESPACIOS_LATERAL:
        actual = ' aria-current="page"' if clave == area else ""
        filas.append(f'<a href="#"{actual}>{icono(ic)}<span>{texto}</span></a>')
    filas.append('<span class="grp">Obras</span>')
    for nombre, cuenta, grav, dice in OBRAS_LATERAL:
        abierta = area == "obra" and nombre == "Vialidad Tramo 3"
        actual = ' aria-current="page"' if abierta else ""
        marca = (
            f'<span class="n {grav}" aria-label="{dice}" title="{dice}">{cuenta}</span>'
            if cuenta
            else ""
        )
        filas.append(f'<a href="#"{actual}>{icono("ruta")}<span>{nombre}</span>{marca}</a>')
        if abierta and meta.get("indice"):
            plantilla = (
                '<span class="ind-t">{}</span>'
                if meta["indice"].get("texto")
                else '<a href="#" class="ind">{}</a>'
            )
            filas.extend(plantilla.format(x) for x in meta["indice"]["items"])
    nav = f'<nav class="opc" aria-label="Lugares">{"".join(filas)}</nav>'
    cab = (
        '<div class="cabl"><span>Lugares</span>'
        f'<button type="button" aria-label="Reducir a iconos">{icono("plegar")}</button></div>'
    )
    return f'<aside class="lat" aria-label="Barra lateral">{cab}{nav}{widgets(meta)}</aside>'


ICONO_CAMPANA = (
    '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0"/></svg>'
)


def barra_de_estado(meta: dict) -> str:
    abierto = meta.get("notificaciones") == "panel"
    return (
        '<footer class="estado-barra" aria-label="Barra de estado">'
        f"{icono('carpeta')}<span>Carpeta Obras 2026</span>"
        '<span class="sep" aria-hidden="true">·</span><span>Guardado hace 2 min</span>'
        '<span style="flex-grow:1"></span>'
        f'<button type="button" class="campana" aria-expanded="{"true" if abierto else "false"}" '
        f'aria-controls="panel-notif" aria-label="Notificaciones, 3 sin leer">{ICONO_CAMPANA}'
        '<span class="n" aria-hidden="true">3</span></button></footer>'
    )


AVISOS = (RAIZ / "avisos.html").read_text(encoding="utf-8").strip()

PANEL = (RAIZ / "panel-notificaciones.html").read_text(encoding="utf-8").strip()


def pagina(meta: dict, principal: str, margen: str, modo: str) -> str:
    css = CSS.substitute(TOKENS[modo])
    principal = principal.replace("{{modo}}", modo)
    margen = margen.replace("{{modo}}", modo)
    ancho = "" if margen.strip() else " ancho"
    aside = (
        f'<aside class="margen" aria-label="Notas al margen">{margen}</aside>'
        if margen.strip()
        else ""
    )
    titulo = f"{meta['titulo']} · {'claro' if modo == 'claro' else 'oscuro'}"
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{titulo}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="{FUENTES}" rel="stylesheet">
<style>{css}</style>
</helmet>
<div class="hm">
{barra_empresa(meta)}
{barra_del_lugar(meta)}
<div class="cuerpo{ancho}">
{opciones(meta)}
<main class="doc">
{principal}
</main>
{aside}
</div>
{AVISOS if meta.get("notificaciones") else ""}
{PANEL if meta.get("notificaciones") == "panel" else ""}
{barra_de_estado(meta)}
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":1440,"height":960}}}}'>
class Component extends DCLogic {{
  renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>
"""


def leer(fragmento: Path) -> tuple[dict, str, str]:
    texto = fragmento.read_text(encoding="utf-8")
    cabecera, resto = texto.split("\n", 1)
    meta = json.loads(cabecera.strip()[4:-3])
    principal, _, margen = resto.partition("<!--MARGEN-->")
    if meta.get("base"):
        _, principal, margen = leer(fragmento.parent / f"{meta['base']}.html")
    return meta, principal, margen


def main() -> None:
    destino = Path(sys.argv[1])
    lienzo = destino / "canvas.json"
    datos = json.loads(lienzo.read_text(encoding="utf-8"))
    datos["boards"] = {k: v for k, v in datos["boards"].items() if not k.startswith("S-")}
    datos["order"] = [k for k in datos["order"] if not k.startswith("S-")]
    fragmentos = sorted(
        FRAGMENTOS.glob("*.html"),
        key=lambda p: json.loads(p.read_text(encoding="utf-8").split("\n", 1)[0].strip()[4:-3])[
            "orden"
        ],
    )
    por_fila, ancho, alto = 6, 1440, 960
    inicio_claro, separacion = 8860, 300
    filas = (len(fragmentos) + por_fila - 1) // por_fila
    inicio_oscuro = inicio_claro + filas * (alto + 140) + separacion
    datos["notes"]["vistas_claro"] = {
        "x": 880,
        "y": inicio_claro - 300,
        "text": "Sílice completo · Papel y resaltador · claro",
        "kind": "title1",
        "maxW": 8000,
    }
    datos["notes"]["vistas_oscuro"] = {
        "x": 880,
        "y": inicio_oscuro - 300,
        "text": "Sílice completo · Papel y resaltador · oscuro",
        "kind": "title1",
        "maxW": 8000,
    }
    for modo, y0 in (("claro", inicio_claro), ("oscuro", inicio_oscuro)):
        for i, fragmento in enumerate(fragmentos):
            meta, principal, margen = leer(fragmento)
            nombre = f"S-{fragmento.stem}-{modo}.dc.html"
            (destino / nombre).write_text(pagina(meta, principal, margen, modo), encoding="utf-8")
            datos["boards"][nombre] = {
                "x": 880 + (i % por_fila) * (ancho + 80),
                "y": y0 + (i // por_fila) * (alto + 140),
                "w": ancho,
                "h": alto,
                "title": f"{meta['orden']} · {meta['titulo']} · {modo}",
                "expand": "fill",
            }
            datos["order"].append(nombre)
    lienzo.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(len(fragmentos), "vistas x 2 modos")


if __name__ == "__main__":
    main()
