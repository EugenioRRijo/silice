"""Toda ruta de la API que el front nuevo pide existe en la API (V-18 de la auditoria visual).

Un front que pide `/v1/partidas` cuando la API sirve `/partidas` solo falla en el navegador (404
eterno): ninguna prueba de componente lo ve, porque el `fetch` es simulado. Esta prueba cruza los
literales de ruta de `frontend-desktop/src` (fuentes que no son pruebas) con el esquema OpenAPI real
de `api.main.app`.

Oraculo: el esquema que FastAPI genera hoy (`app.openapi()`), no el codigo del front. Los literales
con partes dinamicas (`${...}`) se comparan como patron contra las rutas con `{parametro}`; la
consulta (`?x=`) se ignora.
"""

from __future__ import annotations

import re
from pathlib import Path

from api.main import app

RAIZ = Path(__file__).resolve().parents[2]
FUENTES = RAIZ / "frontend-desktop" / "src"
#: Una cadena (comillas, apostrofes o plantilla) que empieza por una ruta de la API.
LITERAL = re.compile(
    r"""["'`](/(?:v1/[A-Za-z0-9_\-/${}.*]+|partidas|insumos|cambios-precio|listas-precios)"""
    r"""[^"'`\s]*)["'`]"""
)
#: V-4 de la auditoria visual: el Inicio pide rutas que solo existen en las ramas
#: inc/ruta-s4-arenera e inc/ruta-s4-existencias-react. Se quitan de aqui al integrarlas: la prueba
#: debe quedar sin excepciones.
PENDIENTES_V4 = ("/v1/produccion/existencias", "/v1/auditorias-libro")


def _a_patron(ruta: str) -> re.Pattern[str]:
    escapada = re.escape(ruta.rstrip("/"))
    return re.compile("^" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", escapada) + "$")


def test_cada_ruta_que_el_front_pide_existe_en_la_api() -> None:
    rutas = list(app.openapi()["paths"])
    patrones = [_a_patron(r) for r in rutas]
    faltan: list[tuple[str, str]] = []
    for archivo in sorted(FUENTES.rglob("*.ts*")):
        if ".test." in archivo.name or archivo.suffix not in {".ts", ".tsx"}:
            continue
        for literal in LITERAL.findall(archivo.read_text(encoding="utf-8")):
            ruta = literal.split("?", 1)[0].rstrip("/")
            if ruta in PENDIENTES_V4 or "*" in ruta:
                continue  # `/v1/control/*` es un comentario de prefijo, no una ruta
            if any(r.startswith(ruta + "/") for r in rutas):
                continue  # un prefijo que el front completa al concatenar
            ejemplo = re.sub(r"\$\{[^}]*\}", "x", ruta)
            if not any(p.match(ejemplo) for p in patrones):
                faltan.append((archivo.relative_to(RAIZ).as_posix(), literal))
    assert faltan == []


def test_la_prueba_ve_un_prefijo_que_no_existe() -> None:
    """El caso de V-18: `/v1/partidas` no esta en la API y la comparacion lo detecta."""
    patrones = [_a_patron(r) for r in app.openapi()["paths"]]
    assert not any(p.match("/v1/partidas") for p in patrones)
    assert any(p.match("/partidas") for p in patrones)
