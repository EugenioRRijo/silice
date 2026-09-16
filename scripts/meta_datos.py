"""Meta de datos: la documentacion del repositorio no presenta sus datos como reales.

`CLAUDE.md` seccion 1 declara que todos los APU y presupuestos del repositorio son ejercicios
academicos ficticios. La sesion de limpieza (2026-09-15) corrigio las afirmaciones que decian lo
contrario; esta meta existe para que no vuelvan.

Por que no basta con `scripts/meta_redaccion.py`: su meta R7 solo mira los capitulos de la tesis,
y la contradiccion estaba fuera de ellos (planes, manuales, dossier, README y docstrings).

Por que la regla es distinta de la de R7: alli «obra ejecutada» delata una afirmacion sobre los
datos, porque un capitulo que la usa esta hablando del caso de estudio. Aqui es vocabulario del
dominio — UC-06 registra rendimientos de obra ejecutada — asi que solo se vigila la pareja
«presupuesto / APU / caso / datos / linea base» con «real», que es la afirmacion que contradice
la fuente unica.

Que NO se vigila, y por que:
- `docs/bitacora/` y `docs/superpowers/`: registran lo que se sabia en su fecha; la errata va en la
  bitacora de la sesion que la descubre, no reescribiendo el registro.
- `docs/tesis/`: lo vigila `meta_redaccion.py` (R7), con su regla mas estricta.

Uso: `uv run python scripts/meta_datos.py [--json]`.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado, Fila, _filas_a_json, render_tabla  # noqa: E402
from scripts.meta_redaccion import evaluar_naturaleza_datos  # noqa: E402

TITULOS: dict[str, str] = {
    "D1": "La documentacion no presenta los datos del repositorio como reales",
    "D2": "CLAUDE.md declara la naturaleza de todos los datos (incluye ARENAZA)",
    "D3": "Los documentos historicos conservan su nota de errata",
}

#: Documentos escritos antes de la aclaracion del 2026-09-15. No se reescriben sin dejar la nota.
DOCUMENTOS_HISTORICOS: tuple[str, ...] = (
    "PLAN_DESARROLLO.md",
    "PLAN_MULTIDOMINIO.md",
    "data/telecom/fuentes/README.md",
)

CARPETAS_EXCLUIDAS: tuple[str, ...] = (
    ".claude/",
    ".git/",
    ".venv/",
    "docs/bitacora/",
    "docs/superpowers/",
    "docs/tesis/",
    "node_modules/",
)

_DATOS = r"(presupuestos?|apus?|casos?|datos|lineas? base)"
_REAL = r"(real(?:es)?)"
_AFIRMACION = re.compile(rf"\b{_DATOS}\b[^.\n]{{0,60}}?\b{_REAL}\b")

#: Citar no es afirmar. Entre comillas invertidas van los mensajes de commit ya hechos, que
#: `PLAN_MULTIDOMINIO.md` reproduce porque son historia; entre comillas angulares, la redaccion
#: antigua que las notas de errata citan justamente para declararla corregida.
_CITADO = re.compile(r"`[^`]*`|«[^»]*»|“[^”]*”")

#: Una oracion con estas marcas no afirma que los datos sean reales: los niega, los declara
#: didacticos o habla de datos que todavia no existen.
_MARCAS: tuple[str, ...] = (
    "academic",
    "didactic",
    "ejercicio",
    "ficticio",
    "futur",
    "ilustrativ",
    "limitacion",
    "ni ",
    "no ",
    "pendiente",
    "sin ",
    "suministr",
)


def _normalizar(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower()


def _oraciones(texto: str) -> Iterator[str]:
    # Corta solo donde el punto va seguido de espacio: asi "M1.1-M4.2" o "2026-09-15).**" siguen
    # en su oracion, y la marca que la desmiente no queda en un trozo distinto del que la necesita.
    for linea in texto.splitlines():
        for trozo in re.split(r"(?<=\.)\s+", linea):
            oracion = trozo.strip()
            if oracion:
                yield oracion


def oraciones_como_reales(texto: str) -> list[str]:
    """Oraciones que presentan los datos del repositorio como reales, sin marca que lo desmienta.

    La afirmacion se busca fuera de lo citado; la marca que la desmiente, en toda la oracion.
    """
    hallazgos = []
    for oracion in _oraciones(texto):
        normalizada = _normalizar(oracion)
        afirmado = _CITADO.sub(" ", normalizada)
        if _AFIRMACION.search(afirmado) and not any(marca in normalizada for marca in _MARCAS):
            hallazgos.append(oracion)
    return hallazgos


def evaluar_documentos(textos: Mapping[str, str]) -> tuple[Estado, str]:
    if not textos:
        return Estado.PENDIENTE, "sin documentos que revisar"
    hallazgos = [
        f"{nombre}: {oracion}"
        for nombre, texto in sorted(textos.items())
        for oracion in oraciones_como_reales(texto)
    ]
    if hallazgos:
        return Estado.FALLA, "datos presentados como reales: " + "; ".join(hallazgos)
    return Estado.OK, f"{len(textos)} documento(s) sin datos presentados como reales"


def evaluar_errata(textos: Mapping[str, str]) -> tuple[Estado, str]:
    if not textos:
        return Estado.PENDIENTE, "sin documentos historicos que revisar"
    faltan = [
        nombre for nombre, texto in sorted(textos.items()) if "errata" not in _normalizar(texto)
    ]
    if faltan:
        return Estado.FALLA, "sin nota de errata: " + ", ".join(faltan)
    return Estado.OK, f"los {len(textos)} documentos historicos conservan su nota de errata"


def es_vigilado(relativo: str) -> bool:
    """Solo documentacion (`.md`) del proyecto, fuera de los registros fechados y de la tesis."""
    ruta = relativo.replace("\\", "/")
    if not ruta.endswith(".md"):
        return False
    return not any(ruta.startswith(carpeta) for carpeta in CARPETAS_EXCLUIDAS)


# --------------------------------------------------------------------------------------
# Orquestacion y CLI
# --------------------------------------------------------------------------------------


def _documentos(raiz: Path) -> dict[str, str]:
    documentos: dict[str, str] = {}
    for ruta in sorted(raiz.rglob("*.md")):
        relativo = ruta.relative_to(raiz).as_posix()
        if es_vigilado(relativo):
            documentos[relativo] = ruta.read_text(encoding="utf-8")
    return documentos


def _leer(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.exists() else None


def _evaluar_metas() -> list[Fila]:
    documentos = _documentos(RAIZ)
    historicos = {
        nombre: texto
        for nombre in DOCUMENTOS_HISTORICOS
        if (texto := _leer(RAIZ / nombre)) is not None
    }
    chequeos: dict[str, Callable[[], tuple[Estado, str]]] = {
        "D1": lambda: evaluar_documentos(documentos),
        "D2": lambda: evaluar_naturaleza_datos(_leer(RAIZ / "CLAUDE.md")),
        "D3": lambda: evaluar_errata(historicos),
    }
    return [Fila(codigo, TITULOS[codigo], *chequeo()) for codigo, chequeo in chequeos.items()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="meta_datos.py",
        description=(
            "Comprueba que la documentacion no presente los datos del repositorio como reales."
        ),
    )
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    args = parser.parse_args(argv)
    filas = _evaluar_metas()
    print(_filas_a_json(filas) if args.json else render_tabla(filas))
    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
