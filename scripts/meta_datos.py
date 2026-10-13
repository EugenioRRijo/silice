"""Meta de datos: la documentacion del repositorio no presenta sus datos como reales.

`NORMAS.md` seccion 1 declara que todos los APU y presupuestos del repositorio son ejercicios
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

Enmienda 1.5 (2026-10-13, NORMAS §1): ahora hay datos reales declarados (los PDF de ARENAZA,
autorizados como referencia, y los libros de la empresa, confidenciales y fuera del repositorio). D1
sigue vigilando que los casos CONSTRUIDOS no se presenten como reales; una oracion que nombra una de
las clases reales declaradas no es esa afirmacion. Las marcas de esas clases son FRASES («libros de
la empresa», «PDF de ARENAZA», «real-confidencial», «anonimizad...») y no palabras sueltas:
«empresa» o «ARENAZA» solas excusarian tambien «los APU de ARENAZA son reales», que es justo lo
que D1 caza (los APU de ARENAZA del repositorio siguen siendo ejercicios).

D4 vigila lo nuevo: ninguna ruta versionada cae donde viven los reales confidenciales
(`docs/auditoria/**` y `data/confidencial/**`, extension en cualquier capitalizacion), y ninguna
hoja de calculo (.xlsx, .xlsm, .xls, .xlsb) ni PDF esta versionado fuera de `LISTA_BLANCA`, que dice
por que cada uno puede estar en Git.

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
    "D2": "NORMAS.md declara la naturaleza de todos los datos (incluye ARENAZA)",
    "D3": "Los documentos historicos conservan su nota de errata",
    "D4": "Ningun libro real-confidencial esta versionado (enmienda 1.5)",
}

#: Donde viven los reales confidenciales (NORMAS §1, enmienda 1.5); ninguno puede estar en Git. En
#: cualquier subcarpeta de `docs/auditoria/` y con la extension en cualquier capitalizacion.
_CONFIDENCIALES = re.compile(
    r"^(docs/auditoria/.+\.(xlsx|xlsm|xlsb|xls|pdf)|data/confidencial/.+)$", re.I
)

#: Un libro de la empresa o su impreso llega como hoja de calculo o como PDF: fuera de la lista
#: blanca, ninguno puede estar versionado, este donde este.
_VIGILADOS_D4 = re.compile(r"\.(xlsx|xlsm|xlsb|xls|pdf)$", re.I)

#: Hojas de calculo y PDF que SI pueden estar en Git, cada uno con el porque. Rutas exactas, salvo
#: las que terminan en `/` (carpeta entera). Anadir una entrada es una decision, no un tramite.
LISTA_BLANCA: dict[str, str] = {
    # Hojas de calculo
    "tests/fixtures/control/ob_s2.xlsx": (
        "sintetico: XLSX de la memoria OB-S2 escrita a mano (spec S2 §7.2, commit 6dfd65e); "
        "partidas OB-A/OB-B, inspector 'Ing. Ficticio', fuente 'libro de obra ficticio'"
    ),
    "tests/fixtures/bcv/2_1_2c26_smc.xls": (
        "publico: tipo de cambio del BCV descargado de bcv.org.ve el 2026-10-11; direccion y "
        "SHA-256 en tests/fixtures/bcv/FUENTE.md (P6)"
    ),
    "tests/fixtures/bcv/4_5_7.xls": (
        "publico: INPC del BCV descargado de bcv.org.ve el 2026-10-11; direccion y SHA-256 en "
        "tests/fixtures/bcv/FUENTE.md (P6)"
    ),
    # PDF
    "data/samples/telecom/Presupuesto_1_ARENAZA.pdf": (
        "real AUTORIZADO como referencia (NORMAS §1, enmienda 1.5): PDF simple de ARENAZA"
    ),
    "data/samples/telecom/Presupuesto_2_ARENAZA.pdf": (
        "real AUTORIZADO como referencia (NORMAS §1, enmienda 1.5): PDF simple de ARENAZA"
    ),
    "data/linea_base/APUS_CLINICA.pdf": (
        "ejercicio academico ficticio: memoria de calculo de la linea base civil (NORMAS §1)"
    ),
    "data/precios/maprex_2026-07/": "publico: lista de precios MaPreX publicada (julio 2026)",
    "docs/fuentes/": "publico: fuentes normativas y bibliograficas citadas en la tesis",
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
    ".superpowers/",
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
    # Enmienda 1.5: las clases reales declaradas en NORMAS §1, como frases (ver el docstring).
    "libro de la empresa",
    "libros de la empresa",
    "presupuestos reales de arenaza",
    "pdf de arenaza",
    "real-confidencial",
    "anonimizad",
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


def _en_lista_blanca(ruta: str) -> bool:
    return any(
        ruta.startswith(permitida) if permitida.endswith("/") else ruta == permitida
        for permitida in LISTA_BLANCA
    )


def evaluar_confidenciales(versionados: list[str]) -> tuple[Estado, str]:
    """D4: ninguna ruta versionada cae donde viven los reales confidenciales, y ninguna hoja de
    calculo ni PDF versionado queda fuera de `LISTA_BLANCA`. Lo confidencial falla aunque alguien
    lo anada a la lista blanca."""
    rutas = [r.replace("\\", "/") for r in versionados]
    expuestos = sorted(r for r in rutas if _CONFIDENCIALES.match(r))
    sin_permiso = sorted(
        r
        for r in rutas
        if _VIGILADOS_D4.search(r) and not _CONFIDENCIALES.match(r) and not _en_lista_blanca(r)
    )
    problemas = []
    if expuestos:
        problemas.append("reales confidenciales versionados: " + ", ".join(expuestos))
    if sin_permiso:
        problemas.append(
            "hojas de calculo o PDF versionados fuera de la lista blanca: " + ", ".join(sin_permiso)
        )
    if problemas:
        return Estado.FALLA, "; ".join(problemas)
    vigilados = sum(1 for r in rutas if _VIGILADOS_D4.search(r))
    return Estado.OK, (
        f"{len(versionados)} archivo(s) versionados, ninguno confidencial; "
        f"{vigilados} hoja(s) de calculo o PDF, todos en la lista blanca"
    )


def _versionados(raiz: Path) -> list[str]:
    import subprocess

    salida = subprocess.run(
        ["git", "ls-files"], cwd=raiz, capture_output=True, text=True, check=False
    )
    return salida.stdout.splitlines() if salida.returncode == 0 else []


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
        "D2": lambda: evaluar_naturaleza_datos(_leer(RAIZ / "NORMAS.md")),
        "D3": lambda: evaluar_errata(historicos),
        "D4": lambda: evaluar_confidenciales(_versionados(RAIZ)),
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
