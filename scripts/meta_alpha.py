"""Meta del sprint alpha: evalua el cumplimiento de sus 12 metas.

Comando unico que el integrador ejecuta tras fusionar cada incremento del sprint alpha. Corre la
suite completa (con cobertura de `core/`), `ruff check`, `ruff format --check`, y revisa el
historial de git desde una referencia base, para decidir si cada meta esta en OK, FALLA o
PENDIENTE (su evidencia aun no existe en el repositorio). El codigo de salida es 0 solo si las
12 metas estan en OK.

Uso: `uv run python scripts/meta_alpha.py [--json] [--sin-cobertura] [--base REF]
[--umbral-cobertura N]`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Collection, Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BASE_POR_DEFECTO = "sprint-0"
UMBRAL_COBERTURA_POR_DEFECTO = 80


class Estado(StrEnum):
    """Resultado de evaluar una meta."""

    OK = "OK"
    FALLA = "FALLA"
    PENDIENTE = "PENDIENTE"


@dataclass(frozen=True, slots=True)
class ResumenArchivo:
    """Conteo de resultados de un archivo de pruebas, segun el reporte JUnit."""

    pasadas: int
    fallidas: int
    errores: int
    omitidas: int


@dataclass(frozen=True, slots=True)
class Meta:
    """Una de las 12 metas del sprint alpha."""

    codigo: str
    titulo: str
    tipo: str  # "pruebas" | "git" | "cobertura" | "ruff" | "suite"
    archivos: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Fila:
    """Resultado de evaluar una meta: una fila de la tabla o un objeto del JSON de salida."""

    codigo: str
    titulo: str
    estado: Estado
    evidencia: str


# Nota (hallazgo de la Task 1): el titulo de M10 usa ">=" en vez de "≥". La consola de
# Windows de esta maquina es cp1252 y no puede codificar ese caracter; imprimirlo abortaria
# render_tabla y --json con UnicodeEncodeError. Es la unica desviacion textual frente al brief.
METAS: tuple[Meta, ...] = (
    Meta(
        "M1",
        "Motor reproduce los 5 APU de la línea base",
        "pruebas",
        ("tests/unit/test_costing.py",),
    ),
    Meta(
        "M2",
        "SQLite reconstruye las 5 composiciones",
        "pruebas",
        ("tests/integration/test_persistencia.py",),
    ),
    Meta(
        "M3",
        "Presupuesto 1 586,61 y curva cierra al 100 %",
        "pruebas",
        ("tests/unit/test_budget.py", "tests/integration/test_presupuesto_linea_base.py"),
    ),
    Meta(
        "M4",
        "Reglas civiles: 0,224 m3 y 4,48 m2 por tanquilla",
        "pruebas",
        ("tests/unit/test_reglas_civil.py",),
    ),
    Meta(
        "M5",
        "Verificación detecta 7 de 7",
        "pruebas",
        ("tests/unit/test_verification.py", "tests/integration/test_auditoria_7_de_7.py"),
    ),
    Meta(
        "M6",
        "Tres adaptadores devuelven ItemComputo trazables",
        "pruebas",
        (
            "tests/unit/test_adapter_telecom.py",
            "tests/unit/test_adapter_industrial.py",
            "tests/unit/test_adapter_sistemas.py",
        ),
    ),
    Meta(
        "M7",
        "UC-02 actualiza precios con registro de cambios",
        "pruebas",
        ("tests/integration/test_actualizacion_precios.py",),
    ),
    Meta(
        "M8",
        "Arquitectura: dependencias del núcleo",
        "pruebas",
        ("tests/unit/test_arquitectura.py",),
    ),
    Meta("M9", "Núcleo intacto: ni un commit ni una rama de adaptador tocan core/", "git"),
    Meta("M10", "Cobertura de core/ >= umbral", "cobertura"),
    Meta("M11", "ruff check y ruff format --check limpios", "ruff"),
    Meta("M12", "Suite completa sin fallos ni errores", "suite"),
)


def _archivos_de_pruebas(metas: Sequence[Meta] = METAS) -> tuple[str, ...]:
    return tuple(archivo for meta in metas if meta.tipo == "pruebas" for archivo in meta.archivos)


# --------------------------------------------------------------------------------------
# Parseo de JUnit
# --------------------------------------------------------------------------------------


def parsear_junit(xml: str, archivos_conocidos: Collection[str]) -> dict[str, ResumenArchivo]:
    """Cuenta pasadas/fallidas/errores/omitidas por archivo, a partir de un reporte JUnit.

    El `classname` de cada `testcase` (p. ej. `tests.unit.test_contracts.TestUnidades`) se asigna
    al archivo conocido cuyo modulo punteado (`tests/unit/test_contracts.py` ->
    `tests.unit.test_contracts`) sea el prefijo mas largo que calce. Los archivos conocidos sin
    ningun `testcase` en el reporte quedan con conteos en cero.
    """
    modulos = {archivo: _modulo_de_archivo(archivo) for archivo in archivos_conocidos}
    conteos = {
        archivo: {"pasadas": 0, "fallidas": 0, "errores": 0, "omitidas": 0}
        for archivo in archivos_conocidos
    }

    raiz = ET.fromstring(xml)
    for testcase in _testcases(raiz):
        archivo = _archivo_de_classname(testcase.get("classname", ""), modulos)
        if archivo is None:
            continue
        conteos[archivo][_resultado_de(testcase)] += 1

    return {archivo: ResumenArchivo(**valores) for archivo, valores in conteos.items()}


def _testcases(elemento_raiz: ET.Element) -> Iterator[ET.Element]:
    if elemento_raiz.tag == "testsuites":
        for testsuite in elemento_raiz.findall("testsuite"):
            yield from testsuite.findall("testcase")
    else:
        yield from elemento_raiz.findall("testcase")


def _modulo_de_archivo(archivo: str) -> str:
    sin_extension = archivo.removesuffix(".py")
    return sin_extension.replace("\\", "/").replace("/", ".")


def _archivo_de_classname(classname: str, modulos: dict[str, str]) -> str | None:
    candidatos = [
        archivo
        for archivo, modulo in modulos.items()
        if classname == modulo or classname.startswith(f"{modulo}.")
    ]
    if not candidatos:
        return None
    return max(candidatos, key=lambda archivo: len(modulos[archivo]))


def _resultado_de(testcase: ET.Element) -> str:
    if testcase.find("failure") is not None:
        return "fallidas"
    if testcase.find("error") is not None:
        return "errores"
    if testcase.find("skipped") is not None:
        return "omitidas"
    return "pasadas"


def _totales_suite(xml_texto: str) -> tuple[int, int, int]:
    if not xml_texto:
        return 0, 0, 0
    raiz = ET.fromstring(xml_texto)
    testsuites = raiz.findall("testsuite") if raiz.tag == "testsuites" else [raiz]
    total = sum(int(ts.get("tests", 0)) for ts in testsuites)
    fallidas = sum(int(ts.get("failures", 0)) for ts in testsuites)
    errores = sum(int(ts.get("errors", 0)) for ts in testsuites)
    return total, fallidas, errores


# --------------------------------------------------------------------------------------
# Estado de cada tipo de meta
# --------------------------------------------------------------------------------------


def estado_pruebas(
    resumenes: dict[str, ResumenArchivo], archivos: Collection[str]
) -> tuple[Estado, str]:
    """PENDIENTE si falta algun archivo en disco. FALLA si alguno tiene fallidas + errores > 0,
    o si un archivo existente no tiene ningun resultado registrado en JUnit (0 pasadas / 0
    fallidas / 0 errores / 0 omitidas): eso nunca es un OK real, es ausencia de evidencia.
    """
    faltantes = sorted(archivo for archivo in archivos if not (RAIZ / archivo).exists())
    if faltantes:
        return Estado.PENDIENTE, f"falta {', '.join(faltantes)}"

    sin_resultados = ResumenArchivo(0, 0, 0, 0)
    detalles = []
    hay_fallo = False
    for archivo in archivos:
        resumen = resumenes.get(archivo, sin_resultados)
        if resumen == sin_resultados:
            hay_fallo = True
            detalles.append(f"{archivo}: sin resultados")
            continue
        if resumen.fallidas + resumen.errores > 0:
            hay_fallo = True
        detalles.append(f"{archivo}: {resumen.pasadas} pasadas / {resumen.fallidas} fallidas")
    estado = Estado.FALLA if hay_fallo else Estado.OK
    return estado, "; ".join(detalles)


def estado_ejecucion_pytest(codigo_retorno: int, xml_texto: str) -> tuple[Estado, str] | None:
    """Diagnostico de una corrida catastrofica de pytest: codigo de salida fuera de {0, 1}
    (INTERNALERROR, `conftest.py` roto, señal del SO) o sin JUnit para leer.

    Devuelve `None` cuando pytest corrio con normalidad: exito (0) o con pruebas en rojo, que
    sale con codigo 1 y sí escribe JUnit. En caso contrario devuelve el FALLA explicito que
    deben adoptar las metas de tipo "pruebas" y M12, en vez de interpretar la ausencia de datos
    como si todo hubiese pasado.
    """
    if codigo_retorno in (0, 1) and xml_texto:
        return None
    return Estado.FALLA, f"pytest no produjo resultados (codigo {codigo_retorno})"


def estado_nucleo_intacto(
    commits: Sequence[tuple[str, Sequence[str]]],
    ramas: Sequence[tuple[str, Sequence[str]]] = (),
) -> tuple[Estado, str]:
    """Las dos evidencias de la hipotesis central (NORMAS.md seccion 1), en una sola meta.

    1. **Por commit** (`commits`): FALLA si algun commit toca a la vez `adapters/`|`ml/` y `core/`.
    2. **Por rama** (`ramas`): FALLA si el `git diff core/` del rango completo de una rama que
       incorpora un dominio no esta vacio. Cierra el agujero de la regla por commit, que solo ve
       los commits listados por `git log -- adapters ml`: un commit de esa misma rama que tocara
       **solo** `core/` le seria invisible.

    Cada elemento de `ramas` es `(nombre legible de la rama, archivos de core/ que cambia)`.
    PENDIENTE si no hay ni commits ni ramas que evaluar.
    """
    if not commits and not ramas:
        return Estado.PENDIENTE, "sin commits que toquen adapters/ o ml/ desde la base"

    problemas = []
    conflictivos = [
        sha
        for sha, archivos in commits
        if any(archivo.startswith(("adapters/", "ml/")) for archivo in archivos)
        and any(archivo.startswith("core/") for archivo in archivos)
    ]
    if conflictivos:
        cortos = ", ".join(sha[:8] for sha in conflictivos)
        problemas.append(f"commits que tocan core/ junto a adapters/ o ml/: {cortos}")

    sucias = [(nombre, archivos) for nombre, archivos in ramas if archivos]
    if sucias:
        detalle = "; ".join(f"{nombre} cambia {', '.join(archivos)}" for nombre, archivos in sucias)
        problemas.append(f"ramas de adaptador con git diff core/ no vacio: {detalle}")

    if problemas:
        return Estado.FALLA, "; ".join(problemas)
    return (
        Estado.OK,
        f"{len(commits)} commits evaluados; {len(ramas)} ramas de adaptador "
        f"con git diff core/ vacio",
    )


def estado_cobertura(porcentaje: Decimal | float, umbral: Decimal | float) -> tuple[Estado, str]:
    """OK si `porcentaje >= umbral` (ambos se comparan como `Decimal`)."""
    porcentaje_decimal = Decimal(str(porcentaje))
    umbral_decimal = Decimal(str(umbral))
    estado = Estado.OK if porcentaje_decimal >= umbral_decimal else Estado.FALLA
    return estado, f"{porcentaje_decimal}% (umbral {umbral_decimal}%)"


def estado_ruff(codigo_check: int, codigo_format: int) -> tuple[Estado, str]:
    if codigo_check == 0 and codigo_format == 0:
        return Estado.OK, "ruff check y ruff format --check sin hallazgos"
    detalles = []
    if codigo_check != 0:
        detalles.append(f"ruff check codigo de salida {codigo_check}")
    if codigo_format != 0:
        detalles.append(f"ruff format --check codigo de salida {codigo_format}")
    return Estado.FALLA, "; ".join(detalles)


def estado_suite(total: int, fallidas: int, errores: int) -> tuple[Estado, str]:
    if total == 0:
        return Estado.PENDIENTE, "la suite no reporto pruebas ejecutadas"
    if fallidas + errores > 0:
        return Estado.FALLA, f"{fallidas} fallidas / {errores} errores de {total} pruebas"
    return Estado.OK, f"{total} pruebas, 0 fallidas, 0 errores"


# --------------------------------------------------------------------------------------
# Salida
# --------------------------------------------------------------------------------------


def render_tabla(filas: Sequence[Fila]) -> str:
    """Tabla ASCII (sin emojis ni caracteres de caja) con columnas Meta | Estado | Evidencia.

    Termina con `RESULTADO: k/n metas OK`.
    """
    encabezados = ("Meta", "Estado", "Evidencia")
    celdas_meta = [f"{fila.codigo} {fila.titulo}" for fila in filas]
    celdas_estado = [fila.estado.value for fila in filas]
    ancho_meta = max([len(encabezados[0]), *(len(celda) for celda in celdas_meta)])
    ancho_estado = max([len(encabezados[1]), *(len(celda) for celda in celdas_estado)])

    lineas = [
        f"{encabezados[0]:<{ancho_meta}} | {encabezados[1]:<{ancho_estado}} | {encabezados[2]}",
        f"{'-' * ancho_meta}-+-{'-' * ancho_estado}-+-{'-' * len(encabezados[2])}",
    ]
    for fila, celda_meta, celda_estado in zip(filas, celdas_meta, celdas_estado, strict=True):
        lineas.append(
            f"{celda_meta:<{ancho_meta}} | {celda_estado:<{ancho_estado}} | {fila.evidencia}"
        )

    ok = sum(1 for fila in filas if fila.estado is Estado.OK)
    lineas.append("")
    lineas.append(f"RESULTADO: {ok}/{len(filas)} metas OK")
    return "\n".join(lineas)


def _filas_a_json(filas: Sequence[Fila]) -> str:
    objetos = [
        {"codigo": f.codigo, "titulo": f.titulo, "estado": f.estado.value, "evidencia": f.evidencia}
        for f in filas
    ]
    return json.dumps(objetos, indent=2)


# --------------------------------------------------------------------------------------
# Orquestacion: subprocesos (pytest, ruff, git)
# --------------------------------------------------------------------------------------


def _ejecutar_pytest(
    directorio_salida: Path, con_cobertura: bool
) -> tuple[str, Decimal | None, int]:
    """Corre pytest una sola vez; devuelve el XML de JUnit, el % de cobertura de `core/` y el
    codigo de salida del proceso (para detectar una corrida catastrofica: ver
    `estado_ejecucion_pytest`).
    """
    junit_path = directorio_salida / "junit.xml"
    cov_path = directorio_salida / "cobertura.json"
    comando = [
        sys.executable,
        "-m",
        "pytest",
        "--junitxml",
        str(junit_path),
        "-p",
        "no:cacheprovider",
    ]
    if con_cobertura:
        comando += ["--cov=core", f"--cov-report=json:{cov_path}"]

    resultado = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True)

    xml_texto = junit_path.read_text(encoding="utf-8") if junit_path.exists() else ""
    cobertura = None
    if con_cobertura and cov_path.exists():
        datos = json.loads(cov_path.read_text(encoding="utf-8"))
        cobertura = Decimal(str(datos["totals"]["percent_covered"]))
    return xml_texto, cobertura, resultado.returncode


def _ejecutar_ruff() -> tuple[int, int]:
    resultado_check = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."], cwd=RAIZ, capture_output=True, text=True
    )
    resultado_format = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    return resultado_check.returncode, resultado_format.returncode


def _commits_nucleo_intacto(base: str) -> list[tuple[str, list[str]]]:
    resultado = subprocess.run(
        ["git", "log", "--no-merges", "--format=%H", f"{base}..HEAD", "--", "adapters", "ml"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    shas = [linea.strip() for linea in resultado.stdout.splitlines() if linea.strip()]

    commits: list[tuple[str, list[str]]] = []
    for sha in shas:
        archivos_resultado = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
            cwd=RAIZ,
            capture_output=True,
            text=True,
        )
        archivos = [
            linea.strip() for linea in archivos_resultado.stdout.splitlines() if linea.strip()
        ]
        commits.append((sha, archivos))
    return commits


def _git(*argumentos: str) -> list[str]:
    """Lineas no vacias de la salida de un comando git; lista vacia si el comando falla."""
    resultado = subprocess.run(
        ["git", *argumentos], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8"
    )
    if resultado.returncode != 0:
        return []
    return [linea.strip() for linea in resultado.stdout.splitlines() if linea.strip()]


def _ramas_adaptador(base: str) -> list[tuple[str, list[str]]]:
    """Ramas fusionadas que **incorporan** un dominio, con los archivos de `core/` que cambian.

    Una rama cuenta como incorporacion de un dominio si su rango (`primer_padre...tope`, es decir
    lo que la rama introdujo respecto de su punto de partida) **agrega** algun archivo bajo
    `adapters/` o `ml/`. Es la formulacion literal de la hipotesis de NORMAS.md seccion 1 ("el
    nucleo no cambia cuando se agrega un dominio") y la unidad de la que habla su evidencia:
    `git diff --stat core/` vacio tras implementar los adaptadores.

    Una rama que solo *modifica* un adaptador ya existente (una correccion, o una pasada
    transversal que ademas toca `core/` por razones ajenas al dominio) no es la incorporacion de
    un dominio: sus commits los cubre la regla por commit de `estado_nucleo_intacto`.

    Solo se miran las fusiones de la **linea principal** (las de `--first-parent`): una fusion de
    `main` *hacia dentro* de una rama en curso tiene los papeles invertidos (su segundo padre es la
    linea principal) y su rango no es lo que la rama introdujo. De una fusion se toman el primer y
    el segundo padre; una fusion de pulpo (tres o mas padres) no la produce este proyecto y se
    evalua solo por su segunda rama.
    """
    principales = set(_git("rev-list", "--first-parent", f"{base}..HEAD"))
    ramas: list[tuple[str, list[str]]] = []
    for linea in _git("log", "--merges", "--format=%H|%s", f"{base}..HEAD"):
        sha, _, asunto = linea.partition("|")
        if sha not in principales:
            continue
        padres = _git("rev-parse", f"{sha}^1", f"{sha}^2")
        if len(padres) != 2:
            continue
        rango = f"{padres[0]}...{padres[1]}"
        if not _git("diff", "--name-only", "--diff-filter=A", rango, "--", "adapters", "ml"):
            continue
        ramas.append((f"{sha[:8]} {asunto}", _git("diff", "--name-only", rango, "--", "core")))
    return ramas


def _evaluar(
    base: str, umbral_cobertura: int, con_cobertura: bool, metas: Sequence[Meta] = METAS
) -> list[Fila]:
    """Evalua `metas` (las del sprint alpha por defecto; `scripts/meta_i6.py` pasa las suyas:
    misma maquinaria, un solo lugar — DRY).
    """
    with tempfile.TemporaryDirectory(prefix="meta_alpha_") as directorio_temp:
        xml_texto, cobertura, codigo_pytest = _ejecutar_pytest(Path(directorio_temp), con_cobertura)
    corrida_rota = estado_ejecucion_pytest(codigo_pytest, xml_texto)

    codigo_check, codigo_format = _ejecutar_ruff()
    commits = _commits_nucleo_intacto(base)
    ramas = _ramas_adaptador(base)

    archivos_pruebas = _archivos_de_pruebas(metas)
    if xml_texto:
        resumenes = parsear_junit(xml_texto, archivos_pruebas)
    else:
        resumenes = {archivo: ResumenArchivo(0, 0, 0, 0) for archivo in archivos_pruebas}
    total, fallidas, errores = _totales_suite(xml_texto)

    filas: list[Fila] = []
    for meta in metas:
        if meta.tipo == "pruebas":
            estado, evidencia = estado_pruebas(resumenes, meta.archivos)
            # Un archivo faltante sigue siendo PENDIENTE aunque pytest se haya roto: la ausencia
            # del archivo es un hecho independiente de esta corrida. Solo se sobreescribe el
            # resultado de un archivo que sí existe (donde "sin resultados" ya dio FALLA) para
            # dejar un mensaje mas especifico sobre por que no hay evidencia.
            if corrida_rota is not None and estado is not Estado.PENDIENTE:
                estado, evidencia = corrida_rota
        elif meta.tipo == "git":
            estado, evidencia = estado_nucleo_intacto(commits, ramas)
        elif meta.tipo == "cobertura":
            if not con_cobertura:
                estado, evidencia = Estado.PENDIENTE, "cobertura omitida (--sin-cobertura)"
            elif cobertura is None:
                estado, evidencia = Estado.PENDIENTE, "sin datos de cobertura de core/"
            else:
                estado, evidencia = estado_cobertura(cobertura, Decimal(umbral_cobertura))
        elif meta.tipo == "ruff":
            estado, evidencia = estado_ruff(codigo_check, codigo_format)
        elif corrida_rota is not None:  # "suite", corrida catastrofica de pytest
            estado, evidencia = corrida_rota
        else:  # "suite"
            estado, evidencia = estado_suite(total, fallidas, errores)
        filas.append(Fila(meta.codigo, meta.titulo, estado, evidencia))
    return filas


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meta_alpha.py",
        description="Evalua el cumplimiento de las 12 metas del sprint alpha.",
    )
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    parser.add_argument(
        "--sin-cobertura",
        action="store_true",
        help="no mide cobertura de core/ al correr pytest (M10 queda PENDIENTE)",
    )
    parser.add_argument(
        "--base",
        default=BASE_POR_DEFECTO,
        help=f"referencia git para el nucleo intacto (por defecto {BASE_POR_DEFECTO})",
    )
    parser.add_argument(
        "--umbral-cobertura",
        type=int,
        default=UMBRAL_COBERTURA_POR_DEFECTO,
        help=f"umbral de cobertura de core/, en % (por defecto {UMBRAL_COBERTURA_POR_DEFECTO})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parsear_args(argv)
    filas = _evaluar(args.base, args.umbral_cobertura, con_cobertura=not args.sin_cobertura)

    if args.json:
        print(_filas_a_json(filas))
    else:
        print(render_tabla(filas))

    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
