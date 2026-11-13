"""Las metas no se caen en una consola cp1252 (PowerShell con la salida capturada o redirigida).

Hallazgo 4 de la auditoria de Antigravity (`docs/bitacora/auditoria-agy-2026-11-04.md`):
`scripts/meta_datos.py` abortaba con `UnicodeEncodeError` al imprimir «→». Las demas metas
imprimen la misma tabla (`render_tabla` de `scripts/meta_alpha.py`), y su evidencia sale de los
datos (titulos de commits, nombres de pruebas, textos de los planes), asi que cualquiera puede
llevar un caracter que cp1252 no tiene.

Cada meta corre en un subproceso con `PYTHONIOENCODING=cp1252`, que reproduce la pagina de
codigos de esa consola. Su evaluacion real (que corre pytest, git y ruff, y en `meta_alpha` la
suite completa, que incluye esta prueba) se sustituye por una fila con «→», «≥» y «‑»: lo que se
prueba es el camino de impresion de `main`, no el veredicto de cada meta.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

#: Texto que cp1252 no puede codificar (flecha, mayor o igual, guion que no corta).
MARCA = "D1 → ≥ 80 % ‑ ok"

#: (modulo, funcion de evaluacion que `main` llama, argumentos de la linea de comandos).
METAS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("meta_alpha", "_evaluar", ()),
    ("meta_asistente", "_evaluar_metas", ()),
    ("meta_datos", "_evaluar_metas", ()),
    ("meta_i6", "_evaluar", ()),
    ("meta_multidominio", "_evaluar_metas", ()),
    ("meta_prototipo", "_evaluar_metas", ()),
    ("meta_redaccion", "_evaluar_metas", ()),
    ("meta_sf", "_evaluar_metas", ()),
    ("meta_silice", "evaluar", ("--version", "0.6.0", "--hasta", "S1-5")),
)

_PROGRAMA = """
import sys
sys.path.insert(0, {raiz!r})
import scripts.{modulo} as meta
from scripts.meta_alpha import Estado, Fila
meta.{funcion} = lambda *a, **k: [Fila("D1", {marca!r}, Estado.OK, {marca!r})]
raise SystemExit(meta.main({argv!r}))
"""


def _entorno_cp1252() -> dict[str, str]:
    entorno = {k: v for k, v in os.environ.items() if k not in {"PYTHONUTF8", "PYTHONIOENCODING"}}
    entorno["PYTHONIOENCODING"] = "cp1252"
    return entorno


def test_las_metas_listadas_son_todas_las_que_tienen_main():
    con_main = sorted(
        ruta.stem
        for ruta in (RAIZ / "scripts").glob("meta_*.py")
        if "def main(" in ruta.read_text(encoding="utf-8")
    )
    assert con_main == sorted(modulo for modulo, _, _ in METAS)


@pytest.mark.parametrize(("modulo", "funcion", "argv"), METAS, ids=[m for m, _, _ in METAS])
def test_la_meta_imprime_su_tabla_en_una_consola_cp1252(modulo, funcion, argv):
    programa = _PROGRAMA.format(
        raiz=str(RAIZ), modulo=modulo, funcion=funcion, marca=MARCA, argv=list(argv)
    )
    resultado = subprocess.run(
        [sys.executable, "-c", programa],
        cwd=RAIZ,
        env=_entorno_cp1252(),
        capture_output=True,
        timeout=120,
        check=False,
    )
    error = resultado.stderr.decode("utf-8", errors="replace")
    assert resultado.returncode == 0, error
    salida = resultado.stdout.decode("utf-8")
    assert f"D1 {MARCA}" in salida
    assert "RESULTADO: 1/1 metas OK" in salida


def _llamadas_print_con_tabla(arbol: ast.AST) -> list[int]:
    """Lineas de `print(...)` que reciben `render_tabla(...)` o `_filas_a_json(...)`."""
    lineas = []
    for nodo in ast.walk(arbol):
        es_print = isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
        if es_print and nodo.func.id == "print":
            for interno in ast.walk(nodo):
                if (
                    isinstance(interno, ast.Call)
                    and isinstance(interno.func, ast.Name)
                    and interno.func.id in {"render_tabla", "_filas_a_json"}
                ):
                    lineas.append(nodo.lineno)
                    break
    return lineas


def test_ningun_script_imprime_la_tabla_con_print_a_secas():
    """Quien imprime `render_tabla` lo hace por `imprimir_salida`, el unico camino que es UTF-8."""
    infractores = [
        f"{ruta.relative_to(RAIZ).as_posix()}:{linea}"
        for ruta in sorted((RAIZ / "scripts").glob("*.py"))
        for linea in _llamadas_print_con_tabla(ast.parse(ruta.read_text(encoding="utf-8")))
    ]
    assert infractores == []
