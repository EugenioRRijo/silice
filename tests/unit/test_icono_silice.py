"""El ícono de Sílice y su identificador de aplicación (F5 ventana, V3; decisión provisional 5).

Una sola fuente, `frontend-desktop/public/silice.svg`: favicon de la interfaz, `.ico` de la ventana,
de los accesos directos y del instalador. El `.ico` se lee aquí byte a byte (formato ICO de
Windows: cabecera de 6 bytes y una entrada de 16 por imagen; ancho 0 = 256 px), sin Pillow.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

from defusedxml import ElementTree

from operacion import ventana

RAIZ = Path(__file__).resolve().parents[2]
SVG = RAIZ / "frontend-desktop" / "public" / "silice.svg"
ICO = RAIZ / "operacion" / "silice.ico"
ISS = RAIZ / "instalador" / "silice.iss"


def _tamanos_del_ico(datos: bytes) -> list[int]:
    reservado, tipo, cuantas = struct.unpack_from("<HHH", datos, 0)
    assert (reservado, tipo) == (0, 1), "no es un .ico"
    tamanos = []
    for i in range(cuantas):
        ancho, alto = struct.unpack_from("<BB", datos, 6 + 16 * i)
        assert ancho == alto, "cada imagen del ícono es cuadrada"
        tamanos.append(ancho or 256)
    return sorted(tamanos)


def test_el_svg_es_cuadrado_con_nombre_accesible_y_sin_recursos_de_fuera() -> None:
    raiz = ElementTree.fromstring(SVG.read_bytes())
    assert raiz.tag == "{http://www.w3.org/2000/svg}svg"
    assert raiz.get("viewBox") == "0 0 256 256"
    assert raiz.get("role") == "img" and raiz.get("aria-label") == "Sílice"
    texto = SVG.read_text(encoding="utf-8")
    # nada que descargar (RNF-22): ni href, ni fuentes, ni otra URL que el espacio de nombres
    assert "href" not in texto and "@import" not in texto and "<text" not in texto
    assert re.findall(r"https?://[^\s\"']+", texto) == ["http://www.w3.org/2000/svg"]


def test_los_colores_del_svg_son_los_de_carbon_del_marco() -> None:
    """Fondo = marco (gray-80), «S» blanca, raya = acento (yellow-20): DESIGN.md «Papeles del
    color». El acento nunca va solo: siempre junto al marco."""
    colores = set(re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{6})"', SVG.read_text("utf-8")))
    assert colores == {"#393939", "#ffffff", "#fddc69"}


def test_el_ico_trae_los_tamanos_de_windows_hasta_256() -> None:
    assert _tamanos_del_ico(ICO.read_bytes()) == [16, 24, 32, 48, 64, 128, 256]


def test_la_ventana_usa_el_ico_de_operacion() -> None:
    assert ventana.ICONO == ICO and ventana.ICONO.is_file()


def test_el_favicon_de_la_interfaz_es_el_svg_de_silice() -> None:
    html = (RAIZ / "frontend-desktop" / "index.html").read_text(encoding="utf-8")
    assert 'href="data:,"' not in html
    (enlace,) = re.findall(r"<link[^>]*rel=\"icon\"[^>]*>", html)
    assert 'href="/silice.svg"' in enlace and 'type="image/svg+xml"' in enlace


def _seccion(nombre: str) -> list[str]:
    """Las líneas de una sección del .iss con los atajos `#define` sustituidos (como ISPP)."""
    texto = ISS.read_text(encoding="utf-8-sig")
    for atajo, valor in re.findall(r'^#define (\w+) "(.*)"$', texto, re.M):
        texto = texto.replace("{#" + atajo + "}", valor)
    lineas = texto.splitlines()
    inicio = lineas.index(f"[{nombre}]") + 1
    fin = next((i for i in range(inicio, len(lineas)) if lineas[i].startswith("[")), len(lineas))
    return [linea for linea in lineas[inicio:fin] if linea and not linea.startswith(";")]


def test_el_instalador_lleva_el_icono_de_silice_y_no_el_de_python() -> None:
    texto = ISS.read_text(encoding="utf-8-sig")
    assert r"SetupIconFile={#Raiz}\operacion\silice.ico" in texto
    assert r"UninstallDisplayIcon={app}\codigo\operacion\silice.ico" in texto
    assert r"UninstallDisplayIcon={app}\python\python.exe" not in texto
    accesos = _seccion("Icons")
    assert len(accesos) == 5
    assert all(r"IconFilename: {app}\codigo\operacion\silice.ico;" in a for a in accesos)


def test_los_accesos_de_silice_llevan_el_identificador_de_la_ventana() -> None:
    """Mismo identificador en el acceso y en la ventana: la barra de tareas los agrupa como
    «Sílice» y no como Python. Los demás accesos (detener, red local, recuperar) no lo llevan:
    son otras órdenes de consola."""
    identificador = f"AppUserModelID: {ventana.IDENTIFICADOR_APLICACION}"
    accesos = _seccion("Icons")
    de_silice = [
        a
        for a in accesos
        if a.startswith((r'Name: "{autoprograms}\Sílice";', r'Name: "{autodesktop}\Sílice";'))
    ]
    assert len(de_silice) == 2
    assert all(identificador in a for a in de_silice)
    assert all("AppUserModelID" not in a for a in accesos if a not in de_silice)
