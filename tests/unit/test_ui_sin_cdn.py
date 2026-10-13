"""El visor 3D no pide nada fuera del equipo (RNF-08; spec S5 §10.2; RP10-5).

Desviación registrada (bitácora, Tarea 11): el plan pedía `"__THREE__" not in html`, pero three.js
r128 trae esa cadena en su propio código (`window.__THREE__`), así que la comprobación es otra:
que el marcador de la plantilla (`<script>__THREE__</script>`) ya no quede y que la biblioteca
aparezca incrustada una sola vez y entera.
"""

from __future__ import annotations

import hashlib
import json
import re

from ui.paginas import visor

MALLA = {"global_id": "g1", "vertices": [0, 0, 0, 1, 0, 0, 0, 1, 0], "caras": [0, 1, 2]}
#: Huella y tamaño publicados en la bitácora de la Tarea 11 (verificados contra RP10-5).
SHA256_R128 = "9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2"
TAMANO_R128 = 603_445


def test_el_archivo_de_three_es_el_r128_verificado() -> None:
    contenido = visor.RUTA_THREE_JS.read_bytes()
    assert len(contenido) == TAMANO_R128 == visor.TAMANO_THREE_JS
    assert hashlib.sha256(contenido).hexdigest() == SHA256_R128 == visor.SHA256_THREE_JS
    assert b"SPDX-License-Identifier: MIT" in contenido[:300]
    assert visor.VERSION_THREE_JS == "r128"


def test_la_licencia_de_three_acompana_al_archivo() -> None:
    texto = (visor.RUTA_THREE_JS.parent / "LICENSE-three.txt").read_text(encoding="utf-8")
    assert "MIT" in texto and "three.js authors" in texto and "r128" in texto


def test_git_trata_three_como_binario() -> None:
    """Sin conversión de fin de línea: la huella es la misma en Windows y en Linux."""
    atributos = (visor.RUTA_THREE_JS.parents[2] / ".gitattributes").read_text(encoding="utf-8")
    assert "ui/estaticos/three.min.js binary" in atributos.splitlines()


def test_el_visor_ya_no_cita_la_cdn() -> None:
    fuente = (visor.RUTA_THREE_JS.parents[1] / "paginas" / "visor.py").read_text(encoding="utf-8")
    # la prosa del docstring cuenta la historia de cdnjs; lo que no puede quedar es una URL
    assert re.search(r"https?://", fuente) is None and "URL_THREE_JS" not in fuente


def test_el_html_incrusta_three_y_no_menciona_hosts_externos() -> None:
    html = visor._html_visor([MALLA])
    assert "cdnjs" not in html and "<script src=" not in html and "<link" not in html
    hosts = set(re.findall(r"https?://([A-Za-z0-9.-]+)", html))
    # el espacio de nombres XHTML/SVG dentro de three.js, no una petición
    assert hosts <= {"www.w3.org"}


def test_three_queda_incrustado_una_vez_y_entero() -> None:
    html = visor._html_visor([MALLA])
    three = visor.RUTA_THREE_JS.read_text(encoding="utf-8")
    assert html.count(three) == 1
    assert "<script>__THREE__</script>" not in html  # el marcador de la plantilla se reemplazó
    assert html.index(three) < html.index("var datos =")  # la biblioteca antes de usarla


def test_el_script_incrustado_no_se_cierra_antes_de_tiempo() -> None:
    html = visor._html_visor([MALLA])
    assert html.count("</script") == 2  # los dos <script> de la plantilla, ninguno dentro de three
    assert "THREE.WebGLRenderer" in html and '"g1"' in html


def test_un_identificador_con_cierre_de_script_no_rompe_el_html() -> None:
    """Los datos van dentro de un `<script>`: un `GlobalId` con `</script>` (sale del `.ifc`
    subido) no puede cerrarlo. Hallazgo de la auditoría final, corregido en `_html_visor`."""
    rara = dict(MALLA, global_id="</script><script>alert(1)</script>")
    html = visor._html_visor([rara])
    assert html.count("</script") == 2
    datos = html.split("var datos = ", 1)[1].split(";\n", 1)[0]
    assert json.loads(datos) == [rara]  # el dato llega intacto al visor


def test_el_html_conserva_la_altura_y_los_datos() -> None:
    html = visor._html_visor([MALLA])
    assert f"height:{visor.ALTURA_VISOR}px" in html and "__DATOS__" not in html
    assert "__ALTURA__" not in html
    datos = html.split("var datos = ", 1)[1].split(";\n", 1)[0]
    assert json.loads(datos) == [MALLA]
