"""Tema de la empresa: colores y logo leídos de `<datos>/tema/` (rediseño del marco, Tarea 1).

El repositorio lleva un tema neutro; nombre, logo y paleta de la empresa viven fuera de él. Esta
lectura nunca falla: un `tema.json` ausente, ilegible o con otra forma, un color que no es
`#rrggbb`, un logo de más de 512 KB o en un formato no admitido (el SVG puede llevar scripts) se
descartan y quedan en `None` / `False`, que el front traduce al tema neutro.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

NOMBRE_CARPETA = "tema"
ARCHIVO_JSON = "tema.json"
TOPE_LOGO = 512 * 1024
TOPE_JSON = 64 * 1024
#: Nombre de archivo -> tipo de imagen. Nunca SVG.
LOGOS = {"logo.png": "image/png", "logo.jpg": "image/jpeg", "logo.webp": "image/webp"}
_FIRMAS = {
    "image/png": re.compile(rb"\x89PNG\r\n\x1a\n"),
    "image/jpeg": re.compile(rb"\xff\xd8\xff"),
    "image/webp": re.compile(rb"RIFF.{4}WEBP", re.DOTALL),
}
_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


#: Colores del tema neutro y de los textos y bordes del marco (frontend-desktop/src/estilos/
#: tokens.scss: --silice-* y --cds-* del tema Carbon g10). Es la ÚNICA copia en el servidor; los
#: avisos de contraste miden contra ella. Fuente: @carbon/colors (gray-80, gray-50, yellow-20,
#: warm-gray-10/-20) y @carbon/themes g10 (text-inverse, text-primary, background).
_NEUTRO = {
    "marco": "#393939",  # --silice-marco = --cds-background-inverse (gray-80)
    "acento": "#fddc69",  # --silice-acento (yellow-20)
    "lateral": "#f7f3f2",  # --silice-lateral (warm-gray-10)
    "lateral-activo": "#e5e0df",  # --silice-lateral-activo (warm-gray-20); el tema no lo cambia
    "texto-del-marco": "#ffffff",  # --cds-text-inverse
    "texto-del-boton": "#ffffff",  # --cds-text-on-color (g10): el texto del botón principal
    "texto": "#161616",  # --cds-text-primary
    "borde": "#8d8d8d",  # --cds-border-strong-01 (gray-50)
    "fondo": "#f4f4f4",  # --cds-background (g10): el fondo del contenido, no el blanco de las capas
    "blanco": "#ffffff",  # --cds-layer-01 (g10): las capas, los diálogos y los campos
}
#: Cuánto del complementario queda en el botón principal al oscurecerlo con negro, en porcentaje
#: (tokens.scss: $oscurecido-*; una prueba comprueba que las dos copias coinciden). En reposo el
#: botón es el complementario tal cual.
OSCURECIDO_DEL_BOTON = {"hover": 85, "pulsado": 70}
_TEXTO = 4.5  # WCAG 2.x 1.4.3, texto normal
_TEXTO_BOTON = 7.0  # decisión de Eugenio (2026-10-28): legibilidad para vista cansada
_GRAFICO = 3.0  # WCAG 2.x 1.4.11, bordes y rayas
#: (color delante, color de fondo, mínimo, frase del aviso). `marco`, `acento`, `lateral`,
#: `complementario`, `contador-numero` y `contador-fondo` los puede poner la empresa; uno ausente
#: mide con el del tema neutro (el complementario y el número del contador siguen al marco, y el
#: fondo del contador al lateral). `boton-*` son el complementario y sus dos oscurecidos
#: (OSCURECIDO_DEL_BOTON); el texto del botón es blanco. La raya del activo del
#: menú lateral es del color del marco (no del acento) y se mide sobre `lateral-activo`, que el
#: tema no cambia.
_PARES = (
    (
        "texto-del-marco",
        "marco",
        _TEXTO,
        "El texto de la barra superior no se lee bien sobre el color del marco",
    ),
    (
        "texto-del-boton",
        "boton-reposo",
        _TEXTO_BOTON,
        "El texto de los botones principales no se lee bien sobre su fondo",
    ),
    (
        "texto-del-boton",
        "boton-hover",
        _TEXTO_BOTON,
        "El texto de los botones principales no se lee bien al pasar el ratón",
    ),
    (
        "texto-del-boton",
        "boton-pulsado",
        _TEXTO_BOTON,
        "El texto de los botones principales no se lee bien al pulsarlos",
    ),
    (
        "marco",
        "acento",
        _TEXTO,
        "Las iniciales de la cuenta no se leen bien sobre el color de acento",
    ),
    (
        "complementario",
        "fondo",
        _TEXTO,
        "Los enlaces no se leen bien sobre el fondo de la página",
    ),
    (
        "complementario",
        "blanco",
        _TEXTO,
        "Los enlaces no se leen bien sobre las capas blancas",
    ),
    (
        "complementario",
        "lateral",
        _TEXTO,
        "Los enlaces no se leen bien sobre el color lateral",
    ),
    ("texto", "lateral", _TEXTO, "El texto del menú lateral no se lee bien sobre el color lateral"),
    (
        "texto",
        "lateral-activo",
        _TEXTO,
        "El texto de la opción activa del menú lateral no se lee bien sobre su fondo",
    ),
    (
        "borde",
        "marco",
        _GRAFICO,
        "Los bordes de la barra superior casi no se ven sobre el color del marco",
    ),
    (
        "borde",
        "lateral",
        _GRAFICO,
        "Las líneas del menú lateral casi no se ven sobre el color lateral",
    ),
    (
        "acento",
        "marco",
        _GRAFICO,
        "La raya de color de acento bajo la barra superior casi no se ve sobre el color del marco",
    ),
    (
        "marco",
        "lateral-activo",
        _GRAFICO,
        "La raya del elemento activo del menú lateral casi no se ve sobre su fondo",
    ),
    (
        "contador-numero",
        "contador-fondo",
        _TEXTO,
        "El número del contador no se lee bien sobre su fondo",
    ),
    (
        "contador-numero",
        "lateral",
        _GRAFICO,
        "El contorno del contador casi no se ve sobre el color lateral",
    ),
    (
        "contador-numero",
        "lateral-activo",
        _GRAFICO,
        "El contorno del contador casi no se ve sobre el fondo de la opción activa del menú"
        " lateral",
    ),
)


@dataclass(frozen=True)
class Tema:
    acento: str | None
    marco: str | None
    lateral: str | None
    complementario: str | None
    contador_numero: str | None
    contador_fondo: str | None
    tiene_logo: bool
    avisos: list[str]


def _luminancia(color: str) -> float:
    """Luminancia relativa de `#rrggbb` (WCAG 2.x, sRGB)."""
    canales = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    """Razón de contraste WCAG 2.x entre dos `#rrggbb`: de 1 (iguales) a 21 (negro y blanco)."""
    claro, oscuro = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def mezclar(delante: str, detras: str, porcentaje: int) -> str:
    """Mezcla sRGB canal a canal, como `color-mix(in srgb, delante P%, detras)` de CSS. Con enteros:
    la mitad se redondea hacia arriba, como pinta el navegador (`round()` de Python la manda al
    par y sesgaba hacia arriba el contraste medido)."""
    canales = (
        (
            int(delante[i : i + 2], 16) * porcentaje
            + int(detras[i : i + 2], 16) * (100 - porcentaje)
            + 50
        )
        // 100
        for i in (1, 3, 5)
    )
    return "#" + "".join(f"{c:02x}" for c in canales)


def _numero(valor: float) -> str:
    """Con coma decimal y un decimal, truncado (no redondeado): un 4,478 nunca se lee «4,5»."""
    return f"{int(valor * 10) / 10:.1f}".replace(".", ",")


def avisos_de_contraste(
    acento: str | None,
    marco: str | None,
    lateral: str | None,
    complementario: str | None = None,
    contador_numero: str | None = None,
    contador_fondo: str | None = None,
) -> list[str]:
    """Los pares del marco que no llegan a su mínimo, en español llano. El tema se aplica igual."""
    propios = {"acento": acento, "marco": marco, "lateral": lateral}
    colores = {**_NEUTRO, **{k: v for k, v in propios.items() if v}}
    colores["complementario"] = complementario or colores["marco"]
    colores["contador-numero"] = contador_numero or colores["marco"]
    colores["contador-fondo"] = contador_fondo or colores["lateral"]
    negro = "#000000"
    colores["boton-reposo"] = colores["complementario"]
    colores["boton-hover"] = mezclar(
        colores["complementario"], negro, OSCURECIDO_DEL_BOTON["hover"]
    )
    colores["boton-pulsado"] = mezclar(
        colores["complementario"], negro, OSCURECIDO_DEL_BOTON["pulsado"]
    )
    avisos = []
    for delante, fondo, minimo, frase in _PARES:
        razon = contraste(colores[delante], colores[fondo])
        if razon < minimo:
            hace_falta = f"{minimo:g}".replace(".", ",")
            avisos.append(f"{frase}: {_numero(razon)}:1, hace falta {hace_falta}:1")
    return avisos


def _color(valor: object) -> str | None:
    return valor if isinstance(valor, str) and _COLOR.fullmatch(valor) else None


def _colores(carpeta: Path) -> dict:
    archivo = carpeta / ARCHIVO_JSON
    try:
        if archivo.stat().st_size > TOPE_JSON:
            return {}
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):  # ausente, ilegible, roto o muy anidado
        return {}
    return datos if isinstance(datos, dict) else {}


def leer_logo(carpeta: Path) -> tuple[bytes, str] | None:
    """Los bytes del logo y su tipo, o `None` si no hay uno admitido, dentro del tope y con la
    firma de su formato. Lee a lo sumo `TOPE_LOGO + 1` bytes: un archivo que crece no se cuela."""
    for nombre, tipo in LOGOS.items():
        try:
            with (carpeta / nombre).open("rb") as f:
                contenido = f.read(TOPE_LOGO + 1)
        except OSError:  # ausente, carpeta o ilegible
            continue
        if len(contenido) <= TOPE_LOGO and _FIRMAS[tipo].match(contenido):
            return contenido, tipo
    return None


def leer_tema(carpeta: Path) -> Tema:
    colores = _colores(carpeta)
    claves = ("acento", "marco", "lateral", "complementario", "contador_numero", "contador_fondo")
    acento, marco, lateral, complementario, contador_numero, contador_fondo = (
        _color(colores.get(k)) for k in claves
    )
    return Tema(
        acento=acento,
        marco=marco,
        lateral=lateral,
        complementario=complementario,
        contador_numero=contador_numero,
        contador_fondo=contador_fondo,
        tiene_logo=leer_logo(carpeta) is not None,
        avisos=avisos_de_contraste(
            acento, marco, lateral, complementario, contador_numero, contador_fondo
        ),
    )
