"""Meta del plan del asistente de presupuestos (UC-09): 12 metas agrupadas por fase.

Se define ANTES de las sesiones de `PLAN_ASISTENTE.md`, como `meta_multidominio.py`: las metas
existen primero y cada fase se trabaja para ponerlas en OK. Dos diferencias aprendidas en aquel
sprint (spec `docs/superpowers/specs/2026-09-15-asistente-presupuestos-design.md`, seccion 7):

1. Cada chequeo de contenido es una funcion pura sobre el texto (`evaluar_*`), probada en
   `tests/unit/test_meta_asistente.py` sin tocar el disco; leer archivos es asunto de la
   orquestacion. La meta M8 multidominio contaba mal justamente por no tener pruebas.
2. `--hasta <fase>` evalua solo las metas de las fases alcanzadas (P, A0, A1, A2, A3) mas las
   transversales, para auditar una fase sin que las siguientes la muestren en PENDIENTE.

Reutiliza de `scripts/meta_alpha.py` las filas, la tabla y la corrida de pytest (`_evaluar`), y de
`scripts/meta_multidominio.py` los chequeos de nucleo intacto y ruff (DRY).

Uso: `uv run python scripts/meta_asistente.py [--hasta P|A0|A1|A2|A3] [--json] [--base REF]`.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import (  # noqa: E402
    Estado,
    Fila,
    Meta,
    _evaluar,
    _filas_a_json,
    render_tabla,
)
from scripts.meta_multidominio import (  # noqa: E402
    evaluar_m11_nucleo_intacto,
    evaluar_m12_ruff,
)

#: Etiqueta puesta al abrir el plan del asistente: punto de partida de la meta de nucleo intacto.
BASE_POR_DEFECTO = "a-base"

#: Fases que audita la meta, en orden. P es la planificacion; A4 no tiene meta propia.
FASES: tuple[str, ...] = ("P", "A0", "A1", "A2", "A3")
TRANSVERSAL = "todas"

#: Fase de cada meta; las transversales se evaluan siempre.
FASE_DE: dict[str, str] = {
    "M1": "P",
    "M2": "P",
    "M3": "A0",
    "M4": "A0",
    "M5": "A0",
    "M6": "A0",
    "M7": "A1",
    "M8": "A1",
    "M9": "A2",
    "M10": "A3",
    "M11": TRANSVERSAL,
    "M12": TRANSVERSAL,
}

TITULOS: dict[str, str] = {
    "M1": "(P) PLAN_ASISTENTE.md con fases, compuertas y sesiones completas",
    "M2": "(P) Spec de diseno del asistente",
    "M3": "(A0) ERS: UC-09 con al menos tres RF",
    "M4": "(A0) ERS: RNF-08 declara la excepcion del extra ia",
    "M5": "(A0) Arquitectura: seccion del asistente",
    "M6": "(A0) Protocolo de evaluacion con casos dorados y umbrales",
    "M7": "(A1) Guardia de arquitectura vigila asistente/",
    "M8": "(A1) Herramientas reconstruyen los casos dorados (GA1)",
    "M9": "(A2) Orquestacion en verde sin red (GA2)",
    "M10": "(A3) Resultados de evaluacion con recuento G2 (GA3, GA-datos)",
    "M11": "Nucleo intacto: git diff <base> --stat -- core/ vacio",
    "M12": "ruff check . limpio",
}

RUTA_PLAN = RAIZ / "PLAN_ASISTENTE.md"
RUTA_SPEC = RAIZ / "docs" / "superpowers" / "specs" / "2026-09-15-asistente-presupuestos-design.md"
RUTA_ERS = RAIZ / "docs" / "ERS.md"
RUTA_ARQUITECTURA = RAIZ / "docs" / "arquitectura.md"
RUTA_PROTOCOLO = RAIZ / "docs" / "evaluacion_asistente.md"
RUTA_PRUEBA_ARQUITECTURA = RAIZ / "tests" / "unit" / "test_arquitectura.py"
RUTA_RESULTADOS = RAIZ / "docs" / "resultados_asistente.md"

#: Archivos de prueba de las metas que son "una prueba de pytest debe pasar".
PRUEBAS: dict[str, str] = {
    "M8": "tests/integration/test_asistente_casos_dorados.py",
    "M9": "tests/unit/test_asistente_orquestacion.py",
}

#: Guion ASCII o no separable (U+2011): los documentos del proyecto usan los dos.
_GUION = "[-‑]"

FASES_DEL_PLAN: tuple[str, ...] = ("A0", "A1", "A2", "A3", "A4")
#: Cada compuerta debe estar DEFINIDA como fila de la tabla de compuertas (`| **GA0** ...`):
#: nombrarla en un prompt o en un parrafo no la declara.
COMPUERTAS: dict[str, str] = {
    "GA0": r"^\|\s*\*\*GA0\*\*",
    "GA1": r"^\|\s*\*\*GA1\*\*",
    "GA2": r"^\|\s*\*\*GA2\*\*",
    "GA3": r"^\|\s*\*\*GA3\*\*",
    "GA-datos": rf"^\|\s*\*\*GA{_GUION}datos\*\*",
}
#: La plantilla de sesion: DoD (Scrum), fuente unica (DRY) y commit convencional.
ELEMENTOS_DE_SESION: dict[str, str] = {
    "Cierre": r"\*\*Cierre\.\*\*",
    "Fuente unica": r"\*\*Fuente [uú]nica\.\*\*",
    "Commit": r"\*\*Commit\.\*\*",
}
CASOS_DORADOS: dict[str, str] = {
    "linea base": r"l[ií]nea base",
    "ARENAZA": r"ARENAZA",
    "MNT-001": rf"MNT{_GUION}001",
    "SIS-001": rf"SIS{_GUION}001",
}


def metas_hasta(fase: str) -> list[str]:
    """Codigos de las metas que se evaluan al alcanzar `fase`, con las transversales."""
    if fase not in FASES:
        raise ValueError(f"fase desconocida: {fase!r}; validas: {', '.join(FASES)}")
    alcanzadas = {*FASES[: FASES.index(fase) + 1], TRANSVERSAL}
    return [codigo for codigo, fase_meta in FASE_DE.items() if fase_meta in alcanzadas]


# --------------------------------------------------------------------------------------
# Chequeos puros sobre texto
# --------------------------------------------------------------------------------------


def evaluar_plan(texto: str | None) -> tuple[Estado, str]:
    """Fases A0-A4, compuertas GA0-GA3 y GA-datos, y la plantilla completa en cada sesion."""
    if texto is None:
        return Estado.PENDIENTE, "falta PLAN_ASISTENTE.md"

    problemas = [
        f"falta la Fase {fase}"
        for fase in FASES_DEL_PLAN
        if not re.search(rf"^## Fase {fase}\b", texto, re.MULTILINE)
    ]
    problemas += [
        f"falta la compuerta {nombre} en la tabla de compuertas"
        for nombre, patron in COMPUERTAS.items()
        if not re.search(patron, texto, re.MULTILINE)
    ]

    sesiones = re.split(r"^### Sesi[oó]n ", texto, flags=re.MULTILINE)[1:]
    if not sesiones:
        problemas.append("no hay sesiones")
    for bloque in sesiones:
        identificador = bloque.split(maxsplit=1)[0]
        # Cada sesion termina en el siguiente encabezado: un elemento de otra seccion no la cubre.
        cuerpo = re.split(r"^#{1,3} ", bloque, maxsplit=1, flags=re.MULTILINE)[0]
        faltan = [
            nombre
            for nombre, patron in ELEMENTOS_DE_SESION.items()
            if not re.search(patron, cuerpo)
        ]
        if faltan:
            problemas.append(f"sesion {identificador}: falta {', '.join(faltan)}")

    if problemas:
        return Estado.FALLA, "; ".join(problemas)
    return (
        Estado.OK,
        f"{len(FASES_DEL_PLAN)} fases, {len(COMPUERTAS)} compuertas y {len(sesiones)} sesiones "
        "con cierre, fuente unica y commit",
    )


def evaluar_spec(existe: bool) -> tuple[Estado, str]:
    if existe:
        return Estado.OK, "la spec del asistente existe"
    return Estado.PENDIENTE, f"falta {RUTA_SPEC.relative_to(RAIZ).as_posix()}"


def evaluar_uc09(texto_ers: str | None) -> tuple[Estado, str]:
    """UC-09 declarado en la ERS y al menos tres requisitos funcionales que lo citan."""
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    if not re.search(rf"^#{{2,4}} UC{_GUION}09\b", texto_ers, re.MULTILINE):
        return Estado.PENDIENTE, "la ERS todavia no declara UC-09"
    citas = re.findall(rf"^\| RF{_GUION}\d+ \|.*\bUC{_GUION}09\b", texto_ers, re.MULTILINE)
    if len(citas) < 3:
        return Estado.FALLA, f"UC-09 declarado, pero solo {len(citas)} RF lo citan (minimo 3)"
    return Estado.OK, f"UC-09 declarado; {len(citas)} RF citan UC-09"


def evaluar_rnf08(texto_ers: str | None) -> tuple[Estado, str]:
    """La fila RNF-08 declara la excepcion de red del extra `ia` (decision DA-2 de la spec)."""
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    fila = re.search(rf"^\|.*\bRNF{_GUION}08\b.*$", texto_ers, re.MULTILINE)
    if fila is None:
        return Estado.FALLA, "la ERS no tiene fila RNF-08"
    if "extra `ia`" not in fila.group(0):
        return Estado.PENDIENTE, "RNF-08 todavia no declara la excepcion del extra `ia`"
    return Estado.OK, "RNF-08 declara la excepcion del extra `ia`"


def evaluar_arquitectura(texto: str | None) -> tuple[Estado, str]:
    if texto is None:
        return Estado.PENDIENTE, "falta docs/arquitectura.md"
    if re.search(r"^#+ .*\b[Aa]sistente\b", texto, re.MULTILINE):
        return Estado.OK, "la arquitectura tiene una seccion del asistente"
    return Estado.PENDIENTE, "la arquitectura todavia no tiene seccion del asistente"


def evaluar_protocolo(texto: str | None) -> tuple[Estado, str]:
    """Los cuatro casos dorados nombrados y los umbrales declarados antes de medir."""
    if texto is None:
        return Estado.PENDIENTE, "falta docs/evaluacion_asistente.md"
    faltan = [
        nombre
        for nombre, patron in CASOS_DORADOS.items()
        if not re.search(patron, texto, re.IGNORECASE)
    ]
    if not re.search(r"\bumbral", texto, re.IGNORECASE):
        faltan.append("umbrales")
    if faltan:
        return Estado.FALLA, f"el protocolo no nombra: {', '.join(faltan)}"
    return Estado.OK, "los cuatro casos dorados y sus umbrales estan declarados"


def evaluar_guardia_arquitectura(texto: str | None) -> tuple[Estado, str]:
    """`tests/unit/test_arquitectura.py` vigila el paquete `asistente` como a `api` y `ui`."""
    if texto is None:
        return Estado.FALLA, "falta tests/unit/test_arquitectura.py"
    tupla = re.search(r"PAQUETES_FUERA_DEL_NUCLEO\s*=\s*\(([^)]*)\)", texto)
    if tupla is None:
        return Estado.FALLA, "no se encontro PAQUETES_FUERA_DEL_NUCLEO"
    if '"asistente"' in tupla.group(1):
        return Estado.OK, "PAQUETES_FUERA_DEL_NUCLEO incluye asistente"
    return Estado.PENDIENTE, "PAQUETES_FUERA_DEL_NUCLEO todavia no incluye asistente"


def evaluar_resultados(texto: str | None) -> tuple[Estado, str]:
    if texto is None:
        return Estado.PENDIENTE, "falta docs/resultados_asistente.md"
    faltan = []
    if not re.search(r"^\|[-:\s|]+\|\s*$", texto, re.MULTILINE):
        faltan.append("tabla de metricas")
    if "G2" not in texto:
        faltan.append("recuento G2")
    if faltan:
        return Estado.FALLA, f"no se encontro: {', '.join(faltan)}"
    return Estado.OK, "tabla de metricas y recuento G2 presentes"


# --------------------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------------------


def _leer(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.exists() else None


def _evaluar_metas(base: str, codigos: list[str]) -> list[Fila]:
    chequeos: dict[str, Callable[[], tuple[Estado, str]]] = {
        "M1": lambda: evaluar_plan(_leer(RUTA_PLAN)),
        "M2": lambda: evaluar_spec(RUTA_SPEC.exists()),
        "M3": lambda: evaluar_uc09(_leer(RUTA_ERS)),
        "M4": lambda: evaluar_rnf08(_leer(RUTA_ERS)),
        "M5": lambda: evaluar_arquitectura(_leer(RUTA_ARQUITECTURA)),
        "M6": lambda: evaluar_protocolo(_leer(RUTA_PROTOCOLO)),
        "M7": lambda: evaluar_guardia_arquitectura(_leer(RUTA_PRUEBA_ARQUITECTURA)),
        "M10": lambda: evaluar_resultados(_leer(RUTA_RESULTADOS)),
        "M11": lambda: evaluar_m11_nucleo_intacto(base),
        "M12": evaluar_m12_ruff,
    }

    metas_pytest = tuple(
        Meta(codigo, TITULOS[codigo], "pruebas", (PRUEBAS[codigo],))
        for codigo in codigos
        if codigo in PRUEBAS
    )
    filas_pytest = (
        {fila.codigo: fila for fila in _evaluar(base, 0, con_cobertura=False, metas=metas_pytest)}
        if metas_pytest
        else {}
    )

    filas = []
    for codigo in codigos:
        if codigo in PRUEBAS:
            estado, evidencia = filas_pytest[codigo].estado, filas_pytest[codigo].evidencia
        else:
            estado, evidencia = chequeos[codigo]()
        filas.append(Fila(codigo, TITULOS[codigo], estado, evidencia))
    return filas


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meta_asistente.py",
        description="Evalua las metas del plan del asistente de presupuestos (UC-09).",
    )
    parser.add_argument(
        "--hasta",
        choices=FASES,
        default=None,
        help="evalua solo las metas de las fases alcanzadas hasta esta (por defecto, todas)",
    )
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    parser.add_argument(
        "--base",
        default=BASE_POR_DEFECTO,
        help=f"referencia git de inicio del plan (por defecto {BASE_POR_DEFECTO})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parsear_args(argv)
    codigos = metas_hasta(args.hasta) if args.hasta else list(FASE_DE)
    filas = _evaluar_metas(args.base, codigos)
    print(_filas_a_json(filas) if args.json else render_tabla(filas))
    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
