"""Meta del sprint final del prototipo (SF): 10 metas agrupadas en seis fases (SF0-SF5).

Se define ANTES de las sesiones de `PLAN_SF.md`, igual que `meta_prototipo.py`: las metas existen
primero y cada fase se trabaja para ponerlas en OK (spec 2026-10-04, seccion 12.2). Reutiliza de
`scripts/meta_alpha.py` `Estado`, `Fila`, `_filas_a_json` y `render_tabla`.

Cada chequeo de contenido es una funcion pura sobre texto ya leido (`evaluar_*`). Las metas de
fases todavia no construidas dan PENDIENTE, nunca FALLA: es evidencia ausente, no un
incumplimiento. Hoy se evaluan de verdad S1 (requisitos en la ERS), S2 (memorias), S3 (agua),
S8 (regresion) y S10 (cobertura); la orquestacion lee disco, consulta git y ejecuta pytest, y
cada evaluador recibe solo el dato ya leido.

Nota: `FASES` agrupa cada meta en la fase donde ARRANCA su evaluacion. S3 («SF1-SF2» en la spec)
arranca en SF1 y S8 («todas») se conecta en SF1; por eso sus titulos llevan el alcance de la spec y
no la fase de agrupacion.

Uso: `uv run python scripts/meta_sf.py [--hasta SF0|SF1|SF2|SF3|SF4|SF5] [--json]`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado, Fila, _filas_a_json, render_tabla  # noqa: E402

#: Fases del sprint final, en orden. Cada una agrupa las metas que arrancan en ella (spec 12.2).
FASES: dict[str, tuple[str, ...]] = {
    "SF0": ("S1",),
    "SF1": ("S2", "S3", "S8", "S10"),
    "SF2": ("S4",),
    "SF3": ("S5", "S9"),
    "SF4": ("S6",),
    "SF5": ("S7",),
}

TITULOS: dict[str, str] = {
    "S1": "(SF0) UC-13 a UC-16, RF-44 a RF-63 y RNF-11 a RNF-13 estan en docs/ERS.md",
    "S2": "(SF1) Memorias de calculo versionadas antes del codigo de su fase",
    "S3": "(SF1-SF2) Pruebas de agua, datos y electricidad en verde",
    "S4": "(SF2) core/ intacto desde gsf1 (y desde gsf4 al cerrar SF5)",
    "S5": "(SF3) Pruebas de edicion, versiones, restauracion, PE y Excel en verde",
    "S6": "(SF4) AppTest de navegacion y herramientas de la barra",
    "S7": "(SF5) Pruebas de importacion de DXF e IFC",
    "S8": "(todas) Regresion: linea base, R4, TI-001, huellas de RNF-04, cuatro hojas",
    "S9": "(SF3) RNF-11: mediana registrada <= 2 s en el equipo de desarrollo",
    "S10": "(SF1) adapters/espacio con cobertura >= 80 %",
}

#: Guion ASCII o no separable (U+2011): la ERS usa el tipografico.
_GUION = "[-‑]"

RUTA_ERS = RAIZ / "docs" / "ERS.md"
#: Informe de cobertura (`coverage json`) que deja la corrida de la suite con `--cov`.
RUTA_COBERTURA = RAIZ / "coverage.json"
UMBRAL_COBERTURA_ESPACIO = 80.0

RUTA_MEMORIAS = RAIZ / "tests" / "fixtures" / "memorias"
RUTA_ESPACIO = RAIZ / "adapters" / "espacio"
RUTA_PRUEBAS_AGUA = "tests/unit/test_espacio_agua.py"

#: Memorias de calculo de SF1: nombre -> argumentos de `git log` que localizan el PRIMER commit del
#: codigo que ellas rigen. La del bano rige la geometria; la del drenaje, la derivacion de agua y
#: drenaje (`especialidades/agua.py`), que nace despues que la geometria.
MEMORIAS_SF1: dict[str, tuple[str, ...]] = {
    "bano_of001.md": ("--diff-filter=A", "--", "adapters/espacio/geometria.py"),
    "bano_drenaje_of001.md": ("--diff-filter=A", "--", "adapters/espacio/especialidades/agua.py"),
}
#: Memorias de fases posteriores: si faltan no hacen fallar la fase actual.
MEMORIAS_SF2: tuple[str, ...] = ("of001.md",)

#: Regresion de spec 11.2 que ya tiene prueba: grupo -> nodeids (archivo o archivo::prueba).
#: De TI-001 solo entran las pruebas que la spec 8.3 declara invariantes (total, PU, punto de
#: equilibrio); `test_auditoria_cumple_sin_errores` y `test_pruebas_de_control` cambian a proposito.
REGRESION: dict[str, tuple[str, ...]] = {
    "linea base": ("tests/unit/test_linea_base.py",),
    "7 de 7": ("tests/integration/test_auditoria_7_de_7.py",),
    "R4 de 3/4 pulg": ("tests/unit/test_verification.py::test_r4_marca_3_4_pulg_y_no_marca_pvc",),
    "TI-001": (
        "tests/unit/test_caso_ti001.py::test_total_y_cierre_de_la_curva",
        "tests/unit/test_caso_ti001.py::test_precios_unitarios",
        "tests/unit/test_caso_ti001.py::test_punto_de_equilibrio",
    ),
    "huellas RNF-04": ("tests/unit/test_huellas_rnf04.py",),
    "cuatro hojas": (
        "tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas",
        "tests/integration/test_composicion_extremo_a_extremo.py"
        "::test_exportar_excel_escribe_las_cuatro_hojas_con_la_modalidad",
    ),
}

#: Identificadores que la ERS enmendada debe declarar (spec 4): (prefijo, numeros).
REQUISITOS_SF: tuple[tuple[str, range], ...] = (
    ("UC", range(13, 17)),
    ("RF", range(44, 64)),
    ("RNF", range(11, 14)),
)


def metas_hasta(fase: str) -> list[str]:
    """Codigos de las metas de `fase` y de todas las fases anteriores, en orden SF0 -> SF5."""
    if fase not in FASES:
        raise ValueError(f"fase desconocida: {fase!r}; validas: {', '.join(FASES)}")
    codigos: list[str] = []
    for nombre_fase, metas in FASES.items():
        codigos.extend(metas)
        if nombre_fase == fase:
            break
    return codigos


# --------------------------------------------------------------------------------------
# Chequeos puros
# --------------------------------------------------------------------------------------


def _patron_definicion(prefijo: str, numero: int) -> str:
    """Linea que DEFINE el requisito: UC por encabezado, RF por fila de tabla, RNF por fila de la
    tabla de calidad (el identificador va en la 2.a celda)."""
    id_ = rf"{prefijo}{_GUION}{numero}(?!\d)"
    if prefijo == "UC":
        return rf"^#{{3,4}}\s+{id_}"
    if prefijo == "RF":
        return rf"^\|\s*{id_}\s*\|"
    return rf"^\|[^|\n]*\|\s*{id_}"


def evaluar_s1_requisitos(texto_ers: str | None) -> tuple[Estado, str]:
    """Cada UC-13..16, RF-44..63 y RNF-11..13 esta DEFINIDO en la ERS (no basta mencionarlo)."""
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    faltan = [
        f"{prefijo}-{numero}"
        for prefijo, numeros in REQUISITOS_SF
        for numero in numeros
        if not re.search(_patron_definicion(prefijo, numero), texto_ers, re.MULTILINE)
    ]
    if faltan:
        return Estado.FALLA, "la ERS no define: " + ", ".join(faltan)
    total = sum(len(numeros) for _, numeros in REQUISITOS_SF)
    return Estado.OK, f"los {total} requisitos del sprint final estan definidos en docs/ERS.md"


def porcentaje_espacio(texto_json: str) -> float | None:
    """Porcentaje de lineas cubiertas de `adapters/espacio` en un `coverage.json` (o None)."""
    try:
        archivos = json.loads(texto_json).get("files", {})
    except (ValueError, AttributeError):
        return None
    cubiertas = total = 0
    for ruta, datos in archivos.items():
        if "adapters/espacio/" in ruta.replace("\\", "/"):
            resumen = datos.get("summary", {})
            cubiertas += resumen.get("covered_lines", 0)
            total += resumen.get("num_statements", 0)
    return None if total == 0 else 100.0 * cubiertas / total


def evaluar_s10_cobertura(
    porcentaje: float | None, existe_adaptador: bool = True
) -> tuple[Estado, str]:
    """S10: cobertura de `adapters/espacio` >= 80 %. Pura: no ejecuta pytest, recibe el dato."""
    if not existe_adaptador:
        return Estado.PENDIENTE, "adapters/espacio aun no existe"
    if porcentaje is None:
        return Estado.PENDIENTE, "sin dato: corre la suite con --cov y `coverage json`"
    texto = f"{porcentaje:.2f}".replace(".", ",")
    if porcentaje >= UMBRAL_COBERTURA_ESPACIO:
        return Estado.OK, f"cobertura de adapters/espacio {texto} % (umbral 80 %)"
    return Estado.FALLA, f"cobertura de adapters/espacio {texto} % < 80 %"


def evaluar_s2_memorias(
    presentes: dict[str, bool],
    antes_del_codigo: dict[str, bool | None],
    codigo_existe: bool = True,
    posteriores: dict[str, bool] | None = None,
) -> tuple[Estado, str]:
    """S2: cada memoria de la fase existe y se versiono ANTES del codigo que rige.

    `antes_del_codigo[m]`: True si su commit precede al del codigo, False si lo sigue, None si no
    hay commit de la memoria (sin versionar). `posteriores` son memorias de fases siguientes: solo
    se mencionan, nunca cambian el estado.
    """
    faltan = [m for m, ok in presentes.items() if not ok]
    if faltan and not codigo_existe:
        return Estado.PENDIENTE, "memorias aun no escritas: " + ", ".join(faltan)
    if faltan:
        return Estado.FALLA, "faltan memorias: " + ", ".join(faltan)
    sin_versionar = [m for m in presentes if antes_del_codigo.get(m) is None]
    if sin_versionar:
        return Estado.FALLA, "memorias sin versionar: " + ", ".join(sin_versionar)
    despues = [m for m in presentes if antes_del_codigo[m] is False]
    if despues:
        return Estado.FALLA, "memorias versionadas despues del codigo: " + ", ".join(despues)
    detalle = "memorias antes del codigo: " + ", ".join(presentes)
    pendientes = [m for m, ok in (posteriores or {}).items() if not ok]
    if pendientes:
        detalle += "; llegan con SF2: " + ", ".join(pendientes)
    return Estado.OK, detalle


def evaluar_s3_especialidades(
    existe_agua: bool, resultado_agua: tuple[int, int] | None
) -> tuple[Estado, str]:
    """S3 hasta SF1: las pruebas de agua existen y pasan (`resultado_agua` = (pasan, total)).
    Datos y electricidad llegan en SF2 y no se exigen aqui."""
    if not existe_agua:
        return Estado.PENDIENTE, "faltan las pruebas de agua"
    if resultado_agua is None or resultado_agua[1] == 0:
        return Estado.PENDIENTE, "las pruebas de agua no recolectaron casos"
    pasan, total = resultado_agua
    if pasan < total:
        return Estado.FALLA, f"pruebas de agua: pasan {pasan} de {total}"
    return Estado.OK, f"pruebas de agua en verde ({pasan}/{total}); datos y electricidad: SF2"


def evaluar_s8_regresion(grupos: dict[str, tuple[int, int] | None]) -> tuple[Estado, str]:
    """S8: cada grupo de regresion es `(pasan, total)`; None si aun no tiene prueba (PENDIENTE).
    Un fallo pesa mas que una ausencia."""
    fallan = [f"{g} ({r[0]}/{r[1]})" for g, r in grupos.items() if r and r[1] > 0 and r[0] < r[1]]
    if fallan:
        return Estado.FALLA, "regresion rota en: " + ", ".join(fallan)
    pendientes = [g for g, r in grupos.items() if r is None or r[1] == 0]
    if pendientes:
        return Estado.PENDIENTE, "sin prueba que cubra: " + ", ".join(pendientes)
    total = sum(r[1] for r in grupos.values() if r)
    return Estado.OK, f"{len(grupos)} grupos de regresion en verde ({total} pruebas)"


def contar_resultados(
    salida: str, grupos: dict[str, tuple[str, ...]]
) -> dict[str, tuple[int, int]]:
    """Cuenta (pasan, total) por grupo a partir del resumen `-rA` de pytest (lineas «PASSED id»)."""
    cuenta = {g: [0, 0] for g in grupos}
    for linea in salida.splitlines():
        estado, _, resto = linea.partition(" ")
        if estado not in ("PASSED", "FAILED", "ERROR"):
            continue
        nodo = resto.split(" - ")[0].strip().replace("\\", "/")
        for grupo, prefijos in grupos.items():
            if nodo.startswith(prefijos):
                cuenta[grupo][1] += 1
                cuenta[grupo][0] += estado == "PASSED"
    return {g: (c[0], c[1]) for g, c in cuenta.items()}


def _s10() -> tuple[Estado, str]:
    existe = (RAIZ / "adapters" / "espacio").is_dir()
    texto = _leer(RUTA_COBERTURA)
    return evaluar_s10_cobertura(None if texto is None else porcentaje_espacio(texto), existe)


def _pendiente(motivo: str) -> Callable[[], tuple[Estado, str]]:
    return lambda: (Estado.PENDIENTE, motivo)


# --------------------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------------------


def _git(*args: str) -> list[str]:
    """Salida de `git <args>` separada por espacios; vacia si git falla."""
    try:
        r = subprocess.run(
            ["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", check=False
        )
    except OSError:
        return []
    return r.stdout.split() if r.returncode == 0 else []


def _ordenar_memoria(memoria: str, criterio_codigo: tuple[str, ...]) -> bool | None:
    """True si el primer commit de la memoria es ancestro del primer commit de su codigo."""
    ruta = f"tests/fixtures/memorias/{memoria}"
    de_memoria = _git("log", "--reverse", "--format=%H", "--diff-filter=A", "--", ruta)
    de_codigo = _git("log", "--reverse", "--format=%H", *criterio_codigo)
    if not de_memoria or not de_codigo:
        return None
    if de_memoria[0] == de_codigo[0]:
        return False
    ancestro = subprocess.run(
        ["git", "merge-base", "--is-ancestor", de_memoria[0], de_codigo[0]], cwd=RAIZ, check=False
    )
    return ancestro.returncode == 0


def _s2() -> tuple[Estado, str]:
    presentes = {m: (RUTA_MEMORIAS / m).is_file() for m in MEMORIAS_SF1}
    orden = {m: _ordenar_memoria(m, criterio) for m, criterio in MEMORIAS_SF1.items()}
    posteriores = {m: (RUTA_MEMORIAS / m).is_file() for m in MEMORIAS_SF2}
    return evaluar_s2_memorias(presentes, orden, RUTA_ESPACIO.is_dir(), posteriores)


def _correr_pytest(ids: list[str]) -> str:
    """Ejecuta pytest sobre `ids` y devuelve su salida (resumen -rA)."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-rA", "--no-header", "-p", "no:cacheprovider", *ids],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return r.stdout


def _existe(nodeid: str) -> bool:
    return (RAIZ / nodeid.split("::")[0]).is_file()


def _s3() -> tuple[Estado, str]:
    existe = _existe(RUTA_PRUEBAS_AGUA)
    resultado = None
    if existe:
        grupo = {"agua": (RUTA_PRUEBAS_AGUA,)}
        resultado = contar_resultados(_correr_pytest([RUTA_PRUEBAS_AGUA]), grupo)["agua"]
    return evaluar_s3_especialidades(existe, resultado)


def _s8() -> tuple[Estado, str]:
    presentes = {g: ids for g, ids in REGRESION.items() if all(_existe(i) for i in ids)}
    ids = [i for grupo in presentes.values() for i in grupo]
    cuenta = contar_resultados(_correr_pytest(ids), presentes) if ids else {}
    return evaluar_s8_regresion({g: cuenta.get(g) for g in REGRESION})


def _leer(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.exists() else None


def _evaluar_metas(codigos: list[str]) -> list[Fila]:
    chequeos: dict[str, Callable[[], tuple[Estado, str]]] = {
        "S1": lambda: evaluar_s1_requisitos(_leer(RUTA_ERS)),
        "S2": _s2,
        "S3": _s3,
        "S4": _pendiente("se evalua al cerrar SF2 (git diff gsf1..HEAD -- core/)"),
        "S5": _pendiente("la hoja del proyecto llega con SF3"),
        "S6": _pendiente("la barra superior llega con SF4"),
        "S7": _pendiente("la importacion de planos llega con SF5"),
        "S8": _s8,
        "S9": _pendiente("la medicion de RNF-11 llega con SF3"),
        "S10": _s10,
    }
    return [Fila(codigo, TITULOS[codigo], *chequeos[codigo]()) for codigo in codigos]


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meta_sf.py",
        description="Evalua las 10 metas del sprint final del prototipo, agrupadas en SF0-SF5.",
    )
    parser.add_argument(
        "--hasta",
        choices=list(FASES),
        default=None,
        help="evalua solo las metas de esta fase y las anteriores (por defecto, las diez)",
    )
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parsear_args(argv)
    if args.hasta:
        codigos = metas_hasta(args.hasta)
    else:
        codigos = [codigo for metas in FASES.values() for codigo in metas]
    filas = _evaluar_metas(codigos)
    print(_filas_a_json(filas) if args.json else render_tabla(filas))
    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
