"""Meta unica de Silice (spec maestro §6.3, RV-17): `--version X --hasta FASE`.

Una sola meta para la 0.6.0 a la 1.0.0 (no hay `meta_s1.py` ni `meta_s5.py`). Siete comprobaciones
comunes corren en toda version y fase:

C1 presencia en la ERS de los numeros que declaran las fases evaluadas (nunca un conteo absoluto);
C2 cero pruebas omitidas en el JUnit de la suite (`--junit`);
C3 el primer commit de cada prueba declarada es anterior al de su implementacion;
C4 `git diff v0.5.0..HEAD -- core/contracts/` vacio;
C5 bloque de regresion literal: sus archivos sin cambios desde v0.5.0 y sus pruebas en verde;
C6 las pruebas de tiempo de las fases evaluadas dejaron su cifra (la ausencia no es un OK);
C7 la guardia de red de `tests/conftest.py` esta declarada (autouse, de sesion) y su prueba pasa.

Cada parte de Silice extiende la meta sin editar este archivo: crea `scripts/meta_silice_<parte>.py`
con `PARTE = Parte(...)` (requisitos por fase, pares prueba-implementacion, cifras de tiempo y
comprobaciones propias, cada una con la fase en que arranca); `partes()` los descubre por nombre. Al
abrir una version solo se edita `FASES`. C3 exige fusionar con merge commit (`gh pr merge --merge`).

PENDIENTE es evidencia ausente y tambien impide el OK: el codigo de salida es 0 solo si todas las
filas estan en OK.

Uso: `uv run python scripts/meta_silice.py --version 0.6.0 --hasta T0
--junit reporte-pruebas.xml [--json]`.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado, Fila, _filas_a_json, render_tabla  # noqa: E402
from scripts.meta_sf import (  # noqa: E402
    _correr_pytest,
    _existe,
    _patron_definicion,
    combinar_s4,
    contar_resultados,
    evaluar_s8_regresion,
)
from scripts.verificar_omitidas import SinEvidenciaError, omitidas  # noqa: E402

BASE_REGRESION = "v0.5.0"
RUTA_ERS = RAIZ / "docs" / "ERS.md"
RUTA_CONFTEST = RAIZ / "tests" / "conftest.py"
PRUEBA_DE_LA_GUARDIA = "tests/unit/test_guardia_red.py"
NOMBRE_GUARDIA = "_guardia_de_red"

#: Fases de cada version, en orden de evaluacion (no de fusion). T0 es la fase transversal.
FASES: dict[str, tuple[str, ...]] = {
    "0.6.0": ("T0", "S5-1", "S1-0", "S1-1", "S1-2", "S1-3", "S1-4", "S1-5"),
    "0.7.0": ("S2-0", "S2-1", "S2-2", "S2-3", "S2-4", "S2-5"),
}

#: Bloque de regresion literal (maestro §6.3): grupo -> nodeids. Estas pruebas no se editan; si un
#: cambio moviera alguna, se registra un ruling de reanclaje.
REGRESION: dict[str, tuple[str, ...]] = {
    "cinco APU a +-0,01": (
        "tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base",
        "tests/unit/test_linea_base.py",
    ),
    "7 de 7": ("tests/integration/test_auditoria_7_de_7.py",),
    "R4 de 3/4 pulg": ("tests/unit/test_verification.py::test_r4_marca_3_4_pulg_y_no_marca_pvc",),
    "TI-001 total, PU y PE 28 586,76 USD Dia 6": (
        "tests/unit/test_caso_ti001.py::test_total_y_cierre_de_la_curva",
        "tests/unit/test_caso_ti001.py::test_precios_unitarios",
        "tests/unit/test_caso_ti001.py::test_punto_de_equilibrio",
    ),
    "dos huellas de RNF-04": ("tests/unit/test_huellas_rnf04.py",),
    "cuatro hojas de exportar_excel": (
        "tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas",
        "tests/integration/test_composicion_extremo_a_extremo.py"
        "::test_exportar_excel_escribe_las_cuatro_hojas_con_la_modalidad",
    ),
}
#: Archivos cuyo `git diff v0.5.0..HEAD` debe quedar vacio (C5).
ARCHIVOS_REGRESION: tuple[str, ...] = tuple(
    sorted({nodo.partition("::")[0] for nodos in REGRESION.values() for nodo in nodos})
)


@dataclass(frozen=True, slots=True)
class ParTDD:
    """Una prueba y el archivo que ella hizo nacer: el primer commit de la prueba va antes."""

    prueba: str
    implementacion: str
    fase: str


@dataclass(frozen=True, slots=True)
class CifraDeTiempo:
    """Una medicion de tiempo que debe dejar su cifra (`clave` numerica en el JSON de `ruta`)."""

    nombre: str
    ruta: str
    clave: str
    orden: str
    fase: str


@dataclass(frozen=True)
class Parte:
    """Lo que una parte de Silice agrega a la meta, cada cosa con la fase en que arranca."""

    nombre: str
    requisitos: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    pares_tdd: tuple[ParTDD, ...] = ()
    cifras: tuple[CifraDeTiempo, ...] = ()
    comprobaciones: tuple[Comprobacion, ...] = ()


@dataclass(frozen=True)
class Contexto:
    version: str
    fases: tuple[str, ...]
    junit: Path | None
    partes: tuple[Parte, ...]


@dataclass(frozen=True)
class Comprobacion:
    codigo: str
    titulo: str
    fase: str
    evaluar: Callable[[Contexto], tuple[Estado, str]]


PARTE_T0 = Parte(
    nombre="T0 transversal",
    pares_tdd=(
        ParTDD("tests/unit/test_entorno_silice.py", "ui/entorno.py", "T0"),
        ParTDD("tests/unit/test_config_streamlit.py", ".streamlit/config.toml", "T0"),
        ParTDD("tests/unit/test_nombre_silice.py", "LICENSE", "T0"),
        ParTDD("tests/unit/test_descargar_modelo.py", "scripts/descargar_modelo.py", "T0"),
        ParTDD("tests/unit/test_meta_silice.py", "scripts/meta_silice.py", "T0"),
    ),
    cifras=(
        CifraDeTiempo(
            "RNF-11",
            "scripts/_salida_rnf11.json",
            "mediana_s",
            "uv run python scripts/medir_rnf11.py",
            "T0",
        ),
    ),
)


# --------------------------------------------------------------------------------------
# Fases y partes
# --------------------------------------------------------------------------------------


def fases_hasta(version: str, hasta: str) -> tuple[str, ...]:
    """Las fases de las versiones anteriores y las de `version` hasta `hasta` (incluida)."""
    if version not in FASES:
        raise ValueError(f"version desconocida: {version!r}; validas: {', '.join(FASES)}")
    if hasta not in FASES[version]:
        validas = ", ".join(FASES[version])
        raise ValueError(f"fase desconocida para la {version}: {hasta!r}; validas: {validas}")
    acumuladas: list[str] = []
    for nombre, fases in FASES.items():
        if nombre == version:
            return (*acumuladas, *fases[: fases.index(hasta) + 1])
        acumuladas.extend(fases)
    raise AssertionError("inalcanzable")


def partes() -> tuple[Parte, ...]:
    """`PARTE_T0` y la `PARTE` de cada `scripts/meta_silice_<parte>.py`, por nombre de archivo."""
    descubiertas = [PARTE_T0]
    for ruta in sorted((RAIZ / "scripts").glob("meta_silice_*.py")):
        descubiertas.append(importlib.import_module(f"scripts.{ruta.stem}").PARTE)
    return tuple(descubiertas)


def _fases_de(parte: Parte) -> set[str]:
    return {
        *parte.requisitos,
        *(par.fase for par in parte.pares_tdd),
        *(cifra.fase for cifra in parte.cifras),
        *(comprobacion.fase for comprobacion in parte.comprobaciones),
    }


def validar_partes(todas: Sequence[Parte]) -> None:
    """`ValueError` si alguna parte usa una fase que no esta en `FASES`."""
    conocidas = {fase for fases in FASES.values() for fase in fases}
    for parte in todas:
        desconocidas = sorted(_fases_de(parte) - conocidas)
        if desconocidas:
            raise ValueError(f"la parte {parte.nombre!r} usa fases fuera de FASES: {desconocidas}")


def requisitos_exigidos(partes_: Sequence[Parte], fases: Sequence[str]) -> tuple[str, ...]:
    return tuple(r for parte in partes_ for fase in fases for r in parte.requisitos.get(fase, ()))


# --------------------------------------------------------------------------------------
# Evaluadores puros
# --------------------------------------------------------------------------------------


def evaluar_requisitos(texto_ers: str | None, exigidos: Sequence[str]) -> tuple[Estado, str]:
    """C1: cada numero exigido esta DEFINIDO en la ERS (presencia; nunca un conteo)."""
    if not exigidos:
        return Estado.OK, "las fases evaluadas no declaran numeros de la ERS"
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    faltan = []
    for ident in exigidos:
        prefijo, _, numero = ident.partition("-")
        if not re.search(_patron_definicion(prefijo, int(numero)), texto_ers, re.MULTILINE):
            faltan.append(ident)
    if faltan:
        return Estado.FALLA, "la ERS no define: " + ", ".join(faltan)
    return Estado.OK, "definidos en docs/ERS.md: " + ", ".join(exigidos)


def evaluar_omitidas(xml_texto: str | None) -> tuple[Estado, str]:
    """C2: cero omitidas en el JUnit; sin JUnit legible no hay evidencia."""
    if xml_texto is None:
        return Estado.PENDIENTE, "sin JUnit: corra pytest --junitxml=reporte-pruebas.xml y --junit"
    try:
        lista = omitidas(xml_texto)
    except SinEvidenciaError as error:
        return Estado.PENDIENTE, str(error)
    if lista:
        return Estado.FALLA, f"{len(lista)} omitida(s): " + "; ".join(lista[:5])
    return Estado.OK, "0 pruebas omitidas en el JUnit"


def evaluar_orden_tdd(orden: Mapping[ParTDD, bool | None]) -> tuple[Estado, str]:
    """C3: True si la prueba precede a su implementacion; False si no; None sin commits."""
    if not orden:
        return Estado.OK, "las fases evaluadas no declaran pares prueba-implementacion"
    despues = [f"{p.prueba} -> {p.implementacion}" for p, ok in orden.items() if ok is False]
    if despues:
        return Estado.FALLA, "prueba no anterior a su implementacion: " + "; ".join(despues)
    sin_commit = [f"{p.prueba} -> {p.implementacion}" for p, ok in orden.items() if ok is None]
    if sin_commit:
        return Estado.PENDIENTE, "sin commit de: " + "; ".join(sin_commit)
    return Estado.OK, f"{len(orden)} pruebas versionadas antes de su implementacion"


def evaluar_diff_vacio(que: str, base_existe: bool, diff: str | None) -> tuple[Estado, str]:
    """C4 y la mitad de C5: `git diff --stat v0.5.0..HEAD -- <que>` vacio."""
    if not base_existe:
        return Estado.PENDIENTE, f"no existe {BASE_REGRESION}: git fetch --tags"
    if diff is None:
        return Estado.PENDIENTE, f"git no respondio al comparar {que} con {BASE_REGRESION}"
    cambios = [linea.strip() for linea in diff.splitlines() if linea.strip()]
    if cambios:
        return Estado.FALLA, f"{que} cambio desde {BASE_REGRESION}: " + "; ".join(cambios[:5])
    return Estado.OK, f"{que} intacto desde {BASE_REGRESION} (git diff vacio)"


def evaluar_regresion(
    estado_diff: tuple[Estado, str],
    grupos: Mapping[str, tuple[int, int] | None],
    ausentes: Sequence[str],
) -> tuple[Estado, str]:
    """C5: archivos intactos y pruebas en verde; una prueba borrada es FALLA, no PENDIENTE."""
    return combinar_s4([estado_diff, evaluar_s8_regresion(dict(grupos), ausentes)])


def evaluar_cifras(
    registros: Mapping[str, Mapping | None], cifras: Sequence[CifraDeTiempo]
) -> tuple[Estado, str]:
    """C6: cada medicion de tiempo dejo un numero en su JSON."""
    if not cifras:
        return Estado.OK, "las fases evaluadas no declaran pruebas de tiempo"
    faltan, dejadas = [], []
    for cifra in cifras:
        registro = registros.get(cifra.ruta)
        valor = registro.get(cifra.clave) if isinstance(registro, Mapping) else None
        if isinstance(valor, bool) or not isinstance(valor, int | float):
            faltan.append(f"{cifra.nombre} (corra `{cifra.orden}`)")
        else:
            dejadas.append(f"{cifra.nombre} {cifra.clave}={valor}")
    if faltan:
        return Estado.PENDIENTE, "sin cifra: " + "; ".join(faltan)
    return Estado.OK, "cifras registradas: " + "; ".join(dejadas)


def guardia_declarada(texto_conftest: str | None) -> bool:
    """True si el conftest define `_guardia_de_red` como fixture autouse de sesion."""
    if texto_conftest is None:
        return False
    for nodo in ast.walk(ast.parse(texto_conftest)):
        if not (isinstance(nodo, ast.FunctionDef) and nodo.name == NOMBRE_GUARDIA):
            continue
        for decorador in nodo.decorator_list:
            if isinstance(decorador, ast.Call) and ast.unparse(decorador.func) == "pytest.fixture":
                claves = {
                    k.arg: ast.literal_eval(k.value)
                    for k in decorador.keywords
                    if k.arg in ("scope", "autouse")
                }
                if claves == {"scope": "session", "autouse": True}:
                    return True
    return False


def evaluar_guardia(declarada: bool, resultado: tuple[int, int] | None) -> tuple[Estado, str]:
    """C7: la guardia esta declarada y su prueba pasa (`resultado` = (pasan, total))."""
    if not declarada:
        return Estado.FALLA, f"tests/conftest.py no declara {NOMBRE_GUARDIA} autouse de sesion"
    if resultado is None or resultado[1] == 0:
        return Estado.PENDIENTE, f"{PRUEBA_DE_LA_GUARDIA} no recolecto casos"
    pasan, total = resultado
    if pasan < total:
        return Estado.FALLA, f"la prueba de la guardia falla ({pasan}/{total})"
    return Estado.OK, f"guardia de red activa; su prueba en verde ({pasan}/{total})"


# --------------------------------------------------------------------------------------
# Orquestacion: git, disco y pytest
# --------------------------------------------------------------------------------------


def _git(*argumentos: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *argumentos],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return None


def _referencia_existe(ref: str) -> bool:
    r = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return r is not None and r.returncode == 0


def _diff_desde_base(rutas: Sequence[str]) -> tuple[bool, str | None]:
    if not _referencia_existe(BASE_REGRESION):
        return False, None
    r = _git("diff", "--stat", f"{BASE_REGRESION}..HEAD", "--", *rutas)
    return True, (r.stdout if r is not None and r.returncode == 0 else None)


def _primer_commit(ruta: str) -> str | None:
    r = _git("log", "--reverse", "--format=%H", "--diff-filter=A", "--", ruta)
    lineas = r.stdout.split() if r is not None and r.returncode == 0 else []
    return lineas[0] if lineas else None


def orden_de_par(par: ParTDD) -> bool | None:
    """True si el primer commit de la prueba es ancestro estricto del de su implementacion."""
    prueba, implementacion = _primer_commit(par.prueba), _primer_commit(par.implementacion)
    if prueba is None or implementacion is None:
        return None
    if prueba == implementacion:
        return False
    r = _git("merge-base", "--is-ancestor", prueba, implementacion)
    return r is not None and r.returncode == 0


def _leer_json(ruta: Path) -> Mapping | None:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def _c1(ctx: Contexto) -> tuple[Estado, str]:
    texto = RUTA_ERS.read_text(encoding="utf-8") if RUTA_ERS.is_file() else None
    return evaluar_requisitos(texto, requisitos_exigidos(ctx.partes, ctx.fases))


def _c2(ctx: Contexto) -> tuple[Estado, str]:
    junit = ctx.junit
    texto = junit.read_text(encoding="utf-8") if junit and junit.is_file() else None
    return evaluar_omitidas(texto)


def _c3(ctx: Contexto) -> tuple[Estado, str]:
    pares = [p for parte in ctx.partes for p in parte.pares_tdd if p.fase in ctx.fases]
    return evaluar_orden_tdd({par: orden_de_par(par) for par in pares})


def _c4(ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_diff_vacio("core/contracts/", *_diff_desde_base(("core/contracts/",)))


def _c5(ctx: Contexto) -> tuple[Estado, str]:
    estado_diff = evaluar_diff_vacio("archivos de regresion", *_diff_desde_base(ARCHIVOS_REGRESION))
    presentes = {g: ids for g, ids in REGRESION.items() if all(_existe(i) for i in ids)}
    ausentes = [g for g in REGRESION if g not in presentes]
    ids = [i for grupo in presentes.values() for i in grupo]
    cuenta = contar_resultados(_correr_pytest(ids), presentes) if ids else {}
    return evaluar_regresion(estado_diff, {g: cuenta.get(g) for g in REGRESION}, ausentes)


def _c6(ctx: Contexto) -> tuple[Estado, str]:
    cifras = [c for parte in ctx.partes for c in parte.cifras if c.fase in ctx.fases]
    return evaluar_cifras({c.ruta: _leer_json(RAIZ / c.ruta) for c in cifras}, cifras)


def _c7(ctx: Contexto) -> tuple[Estado, str]:
    texto = RUTA_CONFTEST.read_text(encoding="utf-8") if RUTA_CONFTEST.is_file() else None
    if not guardia_declarada(texto):
        return evaluar_guardia(False, None)
    if not (RAIZ / PRUEBA_DE_LA_GUARDIA).is_file():
        return evaluar_guardia(True, None)
    salida = _correr_pytest([PRUEBA_DE_LA_GUARDIA])
    return evaluar_guardia(True, contar_resultados(salida, {"g": (PRUEBA_DE_LA_GUARDIA,)})["g"])


COMUNES: tuple[Comprobacion, ...] = (
    Comprobacion("C1", "Numeros de la ERS de las fases evaluadas (presencia)", "T0", _c1),
    Comprobacion("C2", "Cero pruebas omitidas", "T0", _c2),
    Comprobacion("C3", "Commit de la prueba anterior al de la implementacion", "T0", _c3),
    Comprobacion("C4", "core/contracts/ intacto desde v0.5.0", "T0", _c4),
    Comprobacion("C5", "Regresion literal intacta desde v0.5.0 y en verde", "T0", _c5),
    Comprobacion("C6", "Las pruebas de tiempo dejaron su cifra", "T0", _c6),
    Comprobacion("C7", "Guardia de red activa", "T0", _c7),
)


def evaluar(version: str, hasta: str, junit: Path | None) -> list[Fila]:
    fases = fases_hasta(version, hasta)
    todas = partes()
    validar_partes(todas)
    ctx = Contexto(version, fases, junit, todas)
    propias = [c for parte in todas for c in parte.comprobaciones if c.fase in fases]
    return [Fila(c.codigo, c.titulo, *c.evaluar(ctx)) for c in (*COMUNES, *propias)]


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meta_silice.py", description="Meta unica de Silice (maestro 6.3, RV-17)."
    )
    parser.add_argument("--version", required=True, choices=list(FASES))
    parser.add_argument("--hasta", required=True, help="fase hasta la que se evalua, incluida")
    parser.add_argument("--junit", type=Path, default=None, help="JUnit de pytest --junitxml")
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    args = parser.parse_args(argv)
    if args.hasta not in FASES[args.version]:
        parser.error(
            f"fase desconocida para la {args.version}: {args.hasta}; "
            f"validas: {', '.join(FASES[args.version])}"
        )
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parsear_args(argv)
    filas = evaluar(args.version, args.hasta, args.junit)
    print(_filas_a_json(filas) if args.json else render_tabla(filas))
    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
