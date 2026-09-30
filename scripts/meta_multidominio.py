"""Meta del sprint multidominio: evalua el cumplimiento de sus 12 metas (Fases M0-M4).

Se define ANTES de ejecutar las once sesiones del PLAN_MULTIDOMINIO (mismo principio que
`meta_alpha.py` y `meta_i6.py`): las metas existen primero y el sprint se escribe para
ponerlas en OK. Al arrancar el sprint casi todas estan en PENDIENTE porque los archivos que
verifican todavia no existen; eso es correcto y esperado.

Reutiliza la maquinaria de `scripts/meta_alpha.py` (`Estado`, `Fila`, `Meta`, `render_tabla`,
`_filas_a_json`) para las cuatro metas que son "una prueba de pytest debe pasar" (M6, M7 y las
mitades de integracion de M8 y M9): se invoca `_evaluar(metas=...)` con un tuple propio de
`Meta` de tipo "pruebas", exactamente como hace `meta_i6.py` (un solo lugar para el parseo de
JUnit y la corrida de pytest, DRY).

Las otras ocho metas (y las mitades de fixture de M8 y M9) no encajan en los tipos que ya
resuelve `_evaluar` ("pruebas", "git", "cobertura", "ruff", "suite"): piden contenido concreto
de un archivo (columnas de un CSV no vacias, un fixture que menciona 80 y 90, una tabla en un
markdown) o un chequeo mas simple que el que ya implementan `estado_nucleo_intacto`/
`estado_ruff` (M11 solo pide que `git diff <base> --stat -- core/` este vacio; M12 solo pide
`ruff check .`, no tambien `ruff format --check`). Para esas se escriben funciones propias en
este archivo, sin tocar `scripts/meta_alpha.py`: cada una devuelve `(Estado, evidencia)` y se
combinan en un `Fila` por meta con el mismo contrato de salida.

Uso: `uv run python scripts/meta_multidominio.py [--json] [--base REF]`.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from decimal import Decimal, InvalidOperation
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

#: Etiqueta puesta al arrancar el sprint multidominio, el punto de partida de sus metas de git.
BASE_POR_DEFECTO = "m-base"

#: Los cuatro dominios del proyecto (NORMAS.md seccion 1), en el orden en que aparecen ahi.
DOMINIOS: tuple[str, ...] = ("civil", "telecom", "industrial", "sistemas")

#: Cabecera exacta de los CSV de referencia MaPreX (Task 3 del plan de sesiones); solo
#: importan aqui las dos columnas que la meta 3 exige no vacias.
ARCHIVOS_REFERENCIA_MAPREX: tuple[str, ...] = tuple(
    f"referencia_{dominio}.csv" for dominio in DOMINIOS
)

#: Titulo de cada meta, en el orden en que las lista el plan de sesiones.
TITULOS: dict[str, str] = {
    "M1": "docs/protocolo_precios.md con las cuatro secciones de dominio",
    "M2": "Las cuatro plantillas data/<dominio>/plantilla_precios.csv existen",
    "M3": "Referencia MaPreX por dominio con ref_maprex y archivo en toda fila",
    "M4": "Fuentes ARENAZA: los dos presupuestos suman sus totales exactos",
    "M5": "Fixture ARENAZA registra la discrepancia 80/90 del tubo corrugado",
    "M6": "Presupuesto ARENAZA reproducido desde el catalogo (+/- 0.01)",
    "M7": "Auditoria telecom detecta el hallazgo 80/90",
    "M8": "Presupuesto industrial: fixture con >= 3 partidas MNT-* y prueba verde",
    "M9": "Presupuesto sistemas: fixture de tarifas y prueba de integracion verde",
    "M10": "docs/resultados_ml.md con conteos por dominio regenerados",
    "M11": "Nucleo intacto: git diff <base> --stat -- core/ vacio",
    "M12": "ruff check . limpio",
}


def _leer_texto(ruta: Path) -> str | None:
    """Contenido de `ruta` si existe, o `None`. Nunca lanza por archivo ausente."""
    if not ruta.exists():
        return None
    return ruta.read_text(encoding="utf-8")


def _combinar(*pares: tuple[Estado, str]) -> tuple[Estado, str]:
    """Combina los sub-chequeos de una meta compuesta (M8, M9: fixture + prueba).

    PENDIENTE si algun sub-chequeo lo esta (su evidencia todavia no existe: es mas
    fundamental que una falla sobre evidencia que si existe). Si no, FALLA si alguno fallo.
    Si no, OK. Las evidencias se concatenan en el orden recibido.
    """
    estados = [estado for estado, _ in pares]
    evidencia = "; ".join(texto for _, texto in pares)
    if any(estado is Estado.PENDIENTE for estado in estados):
        return Estado.PENDIENTE, evidencia
    if any(estado is Estado.FALLA for estado in estados):
        return Estado.FALLA, evidencia
    return Estado.OK, evidencia


# --------------------------------------------------------------------------------------
# M1-M5, M8 (fixture), M9 (fixture), M10: chequeos de contenido de archivo
# --------------------------------------------------------------------------------------


def evaluar_m1_protocolo_precios() -> tuple[Estado, str]:
    ruta = RAIZ / "docs" / "protocolo_precios.md"
    texto = _leer_texto(ruta)
    if texto is None:
        return Estado.PENDIENTE, "falta docs/protocolo_precios.md"
    faltantes = [
        dominio for dominio in DOMINIOS if not re.search(rf"\b{dominio}\b", texto, re.IGNORECASE)
    ]
    if faltantes:
        return Estado.FALLA, f"no se menciona la seccion de: {', '.join(faltantes)}"
    return Estado.OK, "las cuatro secciones de dominio (civil, telecom, industrial, sistemas) estan"


def evaluar_m2_plantillas_precios() -> tuple[Estado, str]:
    rutas = [Path("data") / dominio / "plantilla_precios.csv" for dominio in DOMINIOS]
    faltantes = sorted(ruta.as_posix() for ruta in rutas if not (RAIZ / ruta).exists())
    if faltantes:
        return Estado.PENDIENTE, f"falta {', '.join(faltantes)}"
    return Estado.OK, "las cuatro plantillas de precios existen"


def evaluar_m3_referencia_maprex() -> tuple[Estado, str]:
    carpeta = RAIZ / "data" / "precios" / "maprex_2026-07"
    faltantes = sorted(
        nombre for nombre in ARCHIVOS_REFERENCIA_MAPREX if not (carpeta / nombre).exists()
    )
    if faltantes:
        return Estado.PENDIENTE, f"falta {', '.join(faltantes)}"

    problemas: list[str] = []
    for nombre in ARCHIVOS_REFERENCIA_MAPREX:
        try:
            with open(carpeta / nombre, newline="", encoding="utf-8") as archivo:
                filas = list(csv.DictReader(archivo))
        except (OSError, csv.Error, UnicodeDecodeError) as error:
            problemas.append(f"{nombre}: no se pudo leer ({error})")
            continue
        if not filas:
            problemas.append(f"{nombre}: sin filas")
            continue
        for indice, fila in enumerate(filas, start=2):  # la fila 1 es la cabecera
            if not fila.get("ref_maprex", "").strip():
                problemas.append(f"{nombre} fila {indice}: ref_maprex vacio")
            if not fila.get("archivo", "").strip():
                problemas.append(f"{nombre} fila {indice}: archivo vacio")
    if problemas:
        detalle = "; ".join(problemas[:5])
        if len(problemas) > 5:
            detalle += f"; y {len(problemas) - 5} problema(s) mas"
        return Estado.FALLA, detalle
    return Estado.OK, "los cuatro CSV existen y toda fila tiene ref_maprex y archivo"


def _suma_columna_total(ruta: Path) -> Decimal:
    with open(ruta, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        return sum((Decimal(fila["total"]) for fila in lector), Decimal("0"))


def evaluar_m4_presupuestos_arenaza() -> tuple[Estado, str]:
    carpeta = RAIZ / "data" / "telecom" / "fuentes"
    totales_esperados = {
        "presupuesto_1_arenaza.csv": Decimal("1109.29"),
        "presupuesto_2_arenaza.csv": Decimal("5410.73"),
    }
    faltantes = sorted(nombre for nombre in totales_esperados if not (carpeta / nombre).exists())
    if faltantes:
        return Estado.PENDIENTE, f"falta {', '.join(faltantes)}"

    detalles: list[str] = []
    hay_fallo = False
    for nombre, esperado in totales_esperados.items():
        try:
            total = _suma_columna_total(carpeta / nombre)
        except (KeyError, InvalidOperation, OSError, csv.Error, UnicodeDecodeError) as error:
            hay_fallo = True
            detalles.append(f"{nombre}: columna 'total' invalida ({error})")
            continue
        if total != esperado:
            hay_fallo = True
        detalles.append(f"{nombre}: suma {total} (esperado {esperado})")
    return (Estado.FALLA if hay_fallo else Estado.OK), "; ".join(detalles)


def evaluar_m5_fixture_arenaza() -> tuple[Estado, str]:
    ruta = RAIZ / "tests" / "fixtures" / "presupuestos_arenaza.py"
    texto = _leer_texto(ruta)
    if texto is None:
        return Estado.PENDIENTE, "falta tests/fixtures/presupuestos_arenaza.py"
    chequeos = {
        "80": re.search(r"\b80\b", texto) is not None,
        "90": re.search(r"\b90\b", texto) is not None,
        "corrugado": re.search(r"corrugad", texto, re.IGNORECASE) is not None,
    }
    if all(chequeos.values()):
        return Estado.OK, "el fixture menciona 80, 90 y el tubo corrugado"
    faltan = [etiqueta for etiqueta, ok in chequeos.items() if not ok]
    return Estado.FALLA, f"no se encontro: {', '.join(faltan)}"


#: Codigo de partida industrial: `MNT-<activo>-<variante>` (p. ej. `MNT-BOM-CEN`). Exige los dos
#: segmentos, asi no confunde partidas del mismo activo ni cuenta `MNT-001` (el presupuesto).
PATRON_PARTIDA_INDUSTRIAL = re.compile(r"\bMNT-[A-Z]+-[A-Z]+\b")


def codigos_partida_industrial(texto: str) -> list[str]:
    """Los codigos de partida industrial distintos que aparecen en `texto`, ordenados."""
    return sorted(set(PATRON_PARTIDA_INDUSTRIAL.findall(texto)))


def evaluar_m8_fixture_industrial() -> tuple[Estado, str]:
    ruta = RAIZ / "tests" / "fixtures" / "mantenimiento_industrial.py"
    texto = _leer_texto(ruta)
    if texto is None:
        return Estado.PENDIENTE, "falta tests/fixtures/mantenimiento_industrial.py"
    codigos = codigos_partida_industrial(texto)
    if len(codigos) >= 3:
        return Estado.OK, f"fixture: {len(codigos)} partidas MNT-* ({', '.join(codigos)})"
    return Estado.FALLA, f"fixture: solo {len(codigos)} partida(s) MNT-* ({', '.join(codigos)})"


def evaluar_m9_fixture_sistemas() -> tuple[Estado, str]:
    ruta = RAIZ / "tests" / "fixtures" / "tarifas_sistemas.py"
    if not ruta.exists():
        return Estado.PENDIENTE, "falta tests/fixtures/tarifas_sistemas.py"
    return Estado.OK, "fixture: tests/fixtures/tarifas_sistemas.py existe"


def evaluar_m10_resultados_ml() -> tuple[Estado, str]:
    ruta = RAIZ / "docs" / "resultados_ml.md"
    texto = _leer_texto(ruta)
    if texto is None:
        return Estado.PENDIENTE, "falta docs/resultados_ml.md"
    tiene_telecom = "telecom" in texto
    tiene_tabla = re.search(r"^\|[-:\s|]+\|\s*$", texto, re.MULTILINE) is not None
    if tiene_telecom and tiene_tabla:
        return Estado.OK, "contiene la cadena 'telecom' y una tabla de conteos"
    faltan = [
        etiqueta
        for etiqueta, ok in (("cadena 'telecom'", tiene_telecom), ("tabla de conteos", tiene_tabla))
        if not ok
    ]
    return Estado.FALLA, f"no se encontro: {', '.join(faltan)}"


# --------------------------------------------------------------------------------------
# M11, M12: git y ruff (chequeos mas simples que los tipos "git"/"ruff" de meta_alpha)
# --------------------------------------------------------------------------------------


def evaluar_m11_nucleo_intacto(base: str) -> tuple[Estado, str]:
    """La hipotesis central de NORMAS.md seccion 1, literal: `git diff <base> --stat --
    core/` vacio. A diferencia de `estado_nucleo_intacto` de `meta_alpha.py` (que audita
    commit por commit y rama por rama), esta meta pide solo el diff acumulado del sprint.
    """
    resultado = subprocess.run(
        ["git", "diff", base, "--stat", "--", "core/"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        detalle = resultado.stderr.strip() or f"codigo {resultado.returncode}"
        return Estado.FALLA, f"git diff {base} --stat -- core/ fallo: {detalle}"
    salida = resultado.stdout.strip()
    if salida:
        return Estado.FALLA, f"git diff {base} --stat -- core/ no vacio:\n{salida}"
    return Estado.OK, f"git diff {base} --stat -- core/ vacio"


def evaluar_m12_ruff() -> tuple[Estado, str]:
    """Solo `ruff check .`: la meta 12 no pide tambien `ruff format --check` (eso es M11 del
    sprint alpha/I6, no esta meta)."""
    resultado = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."], cwd=RAIZ, capture_output=True, text=True
    )
    if resultado.returncode == 0:
        return Estado.OK, "ruff check . sin hallazgos"
    return Estado.FALLA, f"ruff check . codigo de salida {resultado.returncode}"


# --------------------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------------------


def _evaluar_metas(base: str) -> list[Fila]:
    """Arma las 12 filas: M6, M7 y las mitades de integracion de M8/M9 via `_evaluar`
    (mecanica exacta de `meta_i6.py`); el resto con las funciones de este archivo.
    """
    metas_pytest: tuple[Meta, ...] = (
        Meta("M6", TITULOS["M6"], "pruebas", ("tests/integration/test_presupuesto_arenaza.py",)),
        Meta("M7", TITULOS["M7"], "pruebas", ("tests/integration/test_auditoria_arenaza.py",)),
        Meta(
            "M8t",
            "prueba de integracion industrial",
            "pruebas",
            ("tests/integration/test_presupuesto_industrial.py",),
        ),
        Meta(
            "M9t",
            "prueba de integracion sistemas",
            "pruebas",
            ("tests/integration/test_presupuesto_sistemas.py",),
        ),
    )
    filas_pytest = {
        fila.codigo: fila for fila in _evaluar(base, 0, con_cobertura=False, metas=metas_pytest)
    }

    resultados: dict[str, tuple[Estado, str]] = {
        "M1": evaluar_m1_protocolo_precios(),
        "M2": evaluar_m2_plantillas_precios(),
        "M3": evaluar_m3_referencia_maprex(),
        "M4": evaluar_m4_presupuestos_arenaza(),
        "M5": evaluar_m5_fixture_arenaza(),
        "M6": (filas_pytest["M6"].estado, filas_pytest["M6"].evidencia),
        "M7": (filas_pytest["M7"].estado, filas_pytest["M7"].evidencia),
        "M8": _combinar(
            evaluar_m8_fixture_industrial(),
            (filas_pytest["M8t"].estado, filas_pytest["M8t"].evidencia),
        ),
        "M9": _combinar(
            evaluar_m9_fixture_sistemas(),
            (filas_pytest["M9t"].estado, filas_pytest["M9t"].evidencia),
        ),
        "M10": evaluar_m10_resultados_ml(),
        "M11": evaluar_m11_nucleo_intacto(base),
        "M12": evaluar_m12_ruff(),
    }

    return [
        Fila(codigo, TITULOS[codigo], estado, evidencia)
        for codigo, (estado, evidencia) in resultados.items()
    ]


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meta_multidominio.py",
        description="Evalua el cumplimiento de las 12 metas del sprint multidominio.",
    )
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    parser.add_argument(
        "--base",
        default=BASE_POR_DEFECTO,
        help=f"referencia git de inicio del sprint (por defecto {BASE_POR_DEFECTO})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parsear_args(argv)
    filas = _evaluar_metas(args.base)

    if args.json:
        print(_filas_a_json(filas))
    else:
        print(render_tabla(filas))

    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
