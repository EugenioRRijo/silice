"""Meta del sprint del prototipo AREN.IA: 12 metas agrupadas en seis fases (P0-P5).

Se define ANTES de las sesiones de `PLAN_PROTOTIPO.md`, igual que `meta_asistente.py`: las metas
existen primero y cada fase se trabaja para ponerlas en OK. Reutiliza de `scripts/meta_alpha.py`
`Estado`, `Fila`, `_filas_a_json` y `render_tabla` (DRY); no declara una tabla nueva.

Cada chequeo de contenido es una funcion pura sobre texto u otros datos ya leidos (`evaluar_*`),
para poder probarla sin tocar el disco; leer archivos y correr codigo es asunto de la orquestacion
(`_evaluar_metas`). Las metas de fases todavia no construidas (P7 en adelante, y P11 mientras el
corpus simulado no exista) dan PENDIENTE, nunca FALLA: es evidencia ausente, no un incumplimiento.

Uso: `uv run python scripts/meta_prototipo.py [--hasta P0|P1|P2|P3|P4|P5] [--json]`.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable, Sequence
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado, Fila, _filas_a_json, render_tabla  # noqa: E402

#: Fases del sprint del prototipo, en orden. Cada una agrupa las metas que la cierran.
FASES: dict[str, tuple[str, ...]] = {
    "P0": ("P1", "P2", "P3"),
    "P1": ("P4", "P5", "P6"),
    "P2": ("P7", "P8"),
    "P3": ("P9",),
    "P4": ("P10", "P11"),
    "P5": ("P12",),
}

TITULOS: dict[str, str] = {
    "P1": "(P0) UC-10 y UC-11 estan en docs/ERS.md",
    "P2": "(P0) docs/fuentes/README.md ficha cada archivo de docs/fuentes/",
    "P3": "(P0) La decision D9 esta en docs/dossier_g0.md",
    "P4": "(P1) ModalidadManoObra existe en core.contracts.apu",
    "P5": "(P1) Los cinco APU de la linea base reproducen su precio unitario esperado",
    "P6": "(P1) Catalogo.reemplazar_composicion existe en core.catalog",
    "P7": "(P2) ui/composicion.py existe y no importa streamlit",
    "P8": "(P2) ui.paginas.componer esta listado en tests/unit/test_ui_importable.py",
    "P9": "(P3) Existe tests/integration/test_composicion_extremo_a_extremo.py",
    "P10": "(P4) Alguna prueba usa AppTest",
    "P11": "(P4) Ningun modulo de ml/ referencia el corpus simulado ni su generador",
    "P12": "(P5) Existe la bitacora del sprint en docs/bitacora/",
}

#: Guion ASCII o no separable (U+2011): los documentos del proyecto usan los dos, y la ERS del
#: prototipo (docs/ERS.md, UC-10 y UC-11) usa el tipografico.
_GUION = "[-‑]"

TOLERANCIA_PRECIO_UNITARIO = Decimal("0.01")

RUTA_ERS = RAIZ / "docs" / "ERS.md"
RUTA_FUENTES = RAIZ / "docs" / "fuentes"
RUTA_FUENTES_README = RUTA_FUENTES / "README.md"
RUTA_DOSSIER_G0 = RAIZ / "docs" / "dossier_g0.md"
RUTA_CONTRACTS_APU = RAIZ / "core" / "contracts" / "apu.py"
RUTA_CATALOGO_REPOSITORIO = RAIZ / "core" / "catalog" / "repositorio.py"
RUTA_UI_COMPOSICION = RAIZ / "ui" / "composicion.py"
RUTA_TEST_UI_IMPORTABLE = RAIZ / "tests" / "unit" / "test_ui_importable.py"
RUTA_PRUEBA_EXTREMO_A_EXTREMO = (
    RAIZ / "tests" / "integration" / "test_composicion_extremo_a_extremo.py"
)
RUTA_TESTS = RAIZ / "tests"
RUTA_ML = RAIZ / "ml"
RUTA_BITACORA = RAIZ / "docs" / "bitacora"

#: Carpetas que nunca contienen el generador del corpus simulado ni las pruebas que corren.
CARPETAS_EXCLUIDAS: tuple[str, ...] = (".git", ".venv", "__pycache__", "node_modules")

#: Los unicos `.md` de docs/fuentes/ que NO son "documentos archivados" con procedencia externa:
#: el propio indice y la transcripcion de una comunicacion personal (contenido propio del
#: proyecto, no una fuente que fichar). Se nombran explicitamente, no por extension: un `.md`
#: nuevo en docs/fuentes/ (p. ej. la captura de una pagina web archivada como procedencia) SI debe
#: ficharse, y P2 debe fallar si no aparece mencionado en el README (hallazgo de la ronda 1).
ARCHIVOS_FUENTES_SIN_FICHA: tuple[str, ...] = ("README.md", "2026-09-16-nota-practica-apu.md")

#: Ruta fija del generador del corpus simulado. El nombre lo fija el plan, no es una suposicion:
#: `PLAN_PROTOTIPO.md` (Sesion P4.3) y el spec de diseno
#: (docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md, linea 190) declaran
#: `scripts/simular_corpus.py`.
GENERADOR_CORPUS_SIMULADO: tuple[str, ...] = ("scripts", "simular_corpus.py")


def metas_hasta(fase: str) -> list[str]:
    """Codigos de las metas de `fase` y de todas las fases anteriores, en orden P0 -> P5."""
    if fase not in FASES:
        raise ValueError(f"fase desconocida: {fase!r}; validas: {', '.join(FASES)}")
    codigos: list[str] = []
    for nombre_fase, metas in FASES.items():
        codigos.extend(metas)
        if nombre_fase == fase:
            break
    return codigos


# --------------------------------------------------------------------------------------
# Chequeos puros (P0)
# --------------------------------------------------------------------------------------


def evaluar_p1_casos_uso(texto_ers: str | None) -> tuple[Estado, str]:
    """UC-10 y UC-11 declarados como encabezado en la ERS (Tarea 1, commit b3d2666)."""
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    faltan = [
        codigo
        for codigo in ("10", "11")
        if not re.search(rf"^#{{2,4}} UC{_GUION}{codigo}\b", texto_ers, re.MULTILINE)
    ]
    if faltan:
        return Estado.PENDIENTE, "la ERS todavia no declara UC-" + ", UC-".join(faltan)
    return Estado.OK, "UC-10 y UC-11 declarados en docs/ERS.md"


def evaluar_p2_fuentes_referenciadas(
    archivos: Sequence[str], texto_readme: str | None
) -> tuple[Estado, str]:
    """Cada documento archivado en docs/fuentes/ aparece mencionado en el README que lo ficha.

    Se compara por el nombre de archivo sin extension (su "stem"), no por conteo de filas: una
    fila del README cubre a la vez un `.pdf` y su `.txt` de texto extraido ("...pdf` y `.txt`"),
    asi que exigir el nombre completo con extension para el `.txt` daria un falso negativo.
    """
    if texto_readme is None:
        return Estado.PENDIENTE, "falta docs/fuentes/README.md"
    if not archivos:
        return Estado.PENDIENTE, "docs/fuentes/ no tiene archivos que fichar"
    faltan = [nombre for nombre in archivos if Path(nombre).stem not in texto_readme]
    if faltan:
        return Estado.FALLA, "README.md no menciona: " + ", ".join(faltan)
    return Estado.OK, f"README.md menciona los {len(archivos)} archivos de docs/fuentes/"


def evaluar_p3_decision_d9(texto_dossier: str | None) -> tuple[Estado, str]:
    """La decision D9 esta declarada como seccion en el dossier de la compuerta G0."""
    if texto_dossier is None:
        return Estado.PENDIENTE, "falta docs/dossier_g0.md"
    if re.search(r"^### D9\b", texto_dossier, re.MULTILINE):
        return Estado.OK, "la decision D9 esta en docs/dossier_g0.md"
    return Estado.PENDIENTE, "la decision D9 todavia no esta en docs/dossier_g0.md"


# --------------------------------------------------------------------------------------
# Chequeos puros (P1)
# --------------------------------------------------------------------------------------


def evaluar_p4_modalidad_mano_obra(texto_apu: str | None) -> tuple[Estado, str]:
    if texto_apu is None:
        return Estado.PENDIENTE, "falta core/contracts/apu.py"
    if re.search(r"^class ModalidadManoObra\b", texto_apu, re.MULTILINE):
        return Estado.OK, "ModalidadManoObra declarada en core/contracts/apu.py"
    return Estado.PENDIENTE, "ModalidadManoObra todavia no existe en core/contracts/apu.py"


def evaluar_p5_linea_base() -> tuple[Estado, str]:
    """Los cinco APU de la linea base reproducen su precio unitario esperado (tolerancia 0,01)."""
    try:
        from core.costing import calcular_apu
        from tests.fixtures import apu_linea_base as lb
    except ImportError as excepcion:
        return Estado.PENDIENTE, f"no se pudo importar el motor o la linea base: {excepcion}"

    try:
        discrepancias = []
        for apu in lb.APUS_LINEA_BASE:
            resultado = calcular_apu(apu, lb.PARAMETROS_LINEA_BASE)
            esperado = lb.PRECIO_UNITARIO_ESPERADO[apu.codigo_partida]
            if abs(resultado.precio_unitario - esperado) > TOLERANCIA_PRECIO_UNITARIO:
                discrepancias.append(
                    f"{apu.codigo_partida}: obtenido {resultado.precio_unitario} "
                    f"esperado {esperado}"
                )
    except Exception as excepcion:  # noqa: BLE001 - se reporta como FALLA, no se interrumpe la meta
        return Estado.FALLA, f"el motor fallo al calcular la linea base: {excepcion}"

    if discrepancias:
        return Estado.FALLA, "; ".join(discrepancias)
    return (
        Estado.OK,
        f"los {len(lb.APUS_LINEA_BASE)} APU de la linea base reproducen su precio unitario "
        f"esperado (tolerancia {TOLERANCIA_PRECIO_UNITARIO})",
    )


def evaluar_p6_reemplazar_composicion(texto_catalogo: str | None) -> tuple[Estado, str]:
    if texto_catalogo is None:
        return Estado.PENDIENTE, "falta core/catalog/repositorio.py"
    if re.search(r"\bdef reemplazar_composicion\b", texto_catalogo):
        return Estado.OK, "Catalogo.reemplazar_composicion existe en core/catalog/repositorio.py"
    return Estado.PENDIENTE, "Catalogo.reemplazar_composicion todavia no existe"


# --------------------------------------------------------------------------------------
# Chequeos puros (P2-P5): hoy inexistentes, dan PENDIENTE hasta que la fase los construya.
# --------------------------------------------------------------------------------------


def evaluar_p7_ui_composicion(texto: str | None) -> tuple[Estado, str]:
    if texto is None:
        return Estado.PENDIENTE, "falta ui/composicion.py"
    if re.search(r"^\s*(import\s+streamlit\b|from\s+streamlit\b)", texto, re.MULTILINE):
        return Estado.FALLA, "ui/composicion.py importa streamlit"
    return Estado.OK, "ui/composicion.py existe y no importa streamlit"


def evaluar_p8_ui_paginas_componer(texto_test: str | None) -> tuple[Estado, str]:
    if texto_test is None:
        return Estado.PENDIENTE, "falta tests/unit/test_ui_importable.py"
    if re.search(r"""["']ui\.paginas\.componer["']""", texto_test):
        return Estado.OK, "ui.paginas.componer esta listado en tests/unit/test_ui_importable.py"
    return (
        Estado.PENDIENTE,
        "ui.paginas.componer todavia no esta listado en tests/unit/test_ui_importable.py",
    )


def evaluar_p9_prueba_extremo_a_extremo(existe: bool) -> tuple[Estado, str]:
    ruta = "tests/integration/test_composicion_extremo_a_extremo.py"
    if existe:
        return Estado.OK, f"{ruta} existe"
    return Estado.PENDIENTE, f"falta {ruta}"


def evaluar_p10_apptest(encontrado: bool) -> tuple[Estado, str]:
    if encontrado:
        return Estado.OK, "alguna prueba usa AppTest"
    return Estado.PENDIENTE, "ninguna prueba usa AppTest todavia"


def evaluar_p11_ml_sin_corpus_simulado(
    generador: str | None, referencias: Sequence[str]
) -> tuple[Estado, str]:
    """Ni el corpus simulado ni el script que lo genera son referenciados desde ml/.

    Mientras el generador no exista en el repositorio (hoy es el caso: lo crea una fase
    posterior) no hay nada que revisar todavia: PENDIENTE, nunca FALLA ni OK.
    """
    if generador is None:
        return Estado.PENDIENTE, "el corpus simulado y su script generador todavia no existen"
    if referencias:
        detalle = ", ".join(referencias)
        return Estado.FALLA, f"ml/ referencia el corpus simulado ({generador}): {detalle}"
    return Estado.OK, f"ningun modulo de ml/ referencia el corpus simulado ({generador})"


def evaluar_p12_bitacora(bitacoras: Sequence[str]) -> tuple[Estado, str]:
    if bitacoras:
        return Estado.OK, "bitacora del sprint del prototipo: " + ", ".join(bitacoras)
    return Estado.PENDIENTE, "todavia no hay bitacora del sprint del prototipo en docs/bitacora/"


# --------------------------------------------------------------------------------------
# Orquestacion: lectura de disco y ejecucion
# --------------------------------------------------------------------------------------


def _leer(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.exists() else None


def _archivos_de_fuentes(raiz_fuentes: Path) -> tuple[str, ...]:
    """Documentos archivados a fichar: todo archivo de la carpeta salvo los de
    `ARCHIVOS_FUENTES_SIN_FICHA`, nombrados de forma explicita (no por extension `.md`): un `.md`
    nuevo que se archive como fuente (p. ej. una captura de pagina web) debe aparecer aqui y, si el
    README no lo menciona, P2 debe fallar en vez de quedar ciega ante el.
    """
    if not raiz_fuentes.is_dir():
        return ()
    return tuple(
        sorted(
            ruta.name
            for ruta in raiz_fuentes.iterdir()
            if ruta.is_file() and ruta.name not in ARCHIVOS_FUENTES_SIN_FICHA
        )
    )


def _alguna_prueba_usa_apptest(raiz_tests: Path) -> bool:
    if not raiz_tests.is_dir():
        return False
    return any(
        "AppTest" in ruta.read_text(encoding="utf-8")
        for ruta in raiz_tests.rglob("*.py")
        if not any(parte in CARPETAS_EXCLUIDAS for parte in ruta.parts)
    )


def _generador_corpus_simulado(raiz: Path) -> Path | None:
    """Ruta del script que genera el corpus simulado, si ya existe en el repositorio.

    Se comprueba la ruta fija `GENERADOR_CORPUS_SIMULADO` en vez de adivinar con un patron de
    nombre: la primera version de esta meta usaba `corpus.*simulado|simulado.*corpus`, que NUNCA
    casa con el nombre real (`scripts/simular_corpus.py`, con raiz "simul-", no "simulado-") que
    fijan `PLAN_PROTOTIPO.md` (Sesion P4.3) y el spec de diseno. Con ese patron, P11 se habria
    quedado en PENDIENTE para siempre incluso despues de que la Sesion P4.3 creara el generador
    (hallazgo de la ronda 1). Una ruta fija es menos adivinatoria y evita ese error.
    """
    ruta = raiz.joinpath(*GENERADOR_CORPUS_SIMULADO)
    return ruta if ruta.is_file() else None


def _referencias_ml_a_corpus(raiz_ml: Path, generador: Path) -> tuple[str, ...]:
    """Modulos de `raiz_ml` que mencionan el generador o el corpus simulado, como `ml/<archivo>`.

    La ruta se calcula respecto de `raiz_ml.parent` y no de `RAIZ`: con `RAIZ`, una carpeta `ml/`
    fuera del repositorio (la de una prueba) lanzaba `ValueError` y la rama FALLA de P11 no podia
    probarse. Sobre el repositorio el resultado es el mismo, porque `RUTA_ML.parent` es `RAIZ`.
    """
    nombre = generador.stem
    if not raiz_ml.is_dir():
        return ()
    referencias = []
    for ruta in sorted(raiz_ml.rglob("*.py")):
        texto = ruta.read_text(encoding="utf-8")
        if nombre in texto or "corpus_simulado" in texto or "corpus simulado" in texto.lower():
            referencias.append(ruta.relative_to(raiz_ml.parent).as_posix())
    return tuple(referencias)


def _bitacoras_del_sprint(raiz_bitacora: Path) -> tuple[str, ...]:
    if not raiz_bitacora.is_dir():
        return ()
    return tuple(
        sorted(ruta.name for ruta in raiz_bitacora.glob("*.md") if "prototipo" in ruta.name.lower())
    )


def _evaluar_metas(codigos: list[str]) -> list[Fila]:
    generador_corpus = _generador_corpus_simulado(RAIZ)
    chequeos: dict[str, Callable[[], tuple[Estado, str]]] = {
        "P1": lambda: evaluar_p1_casos_uso(_leer(RUTA_ERS)),
        "P2": lambda: evaluar_p2_fuentes_referenciadas(
            _archivos_de_fuentes(RUTA_FUENTES), _leer(RUTA_FUENTES_README)
        ),
        "P3": lambda: evaluar_p3_decision_d9(_leer(RUTA_DOSSIER_G0)),
        "P4": lambda: evaluar_p4_modalidad_mano_obra(_leer(RUTA_CONTRACTS_APU)),
        "P5": evaluar_p5_linea_base,
        "P6": lambda: evaluar_p6_reemplazar_composicion(_leer(RUTA_CATALOGO_REPOSITORIO)),
        "P7": lambda: evaluar_p7_ui_composicion(_leer(RUTA_UI_COMPOSICION)),
        "P8": lambda: evaluar_p8_ui_paginas_componer(_leer(RUTA_TEST_UI_IMPORTABLE)),
        "P9": lambda: evaluar_p9_prueba_extremo_a_extremo(RUTA_PRUEBA_EXTREMO_A_EXTREMO.exists()),
        "P10": lambda: evaluar_p10_apptest(_alguna_prueba_usa_apptest(RUTA_TESTS)),
        "P11": lambda: evaluar_p11_ml_sin_corpus_simulado(
            generador_corpus.relative_to(RAIZ).as_posix() if generador_corpus else None,
            _referencias_ml_a_corpus(RUTA_ML, generador_corpus) if generador_corpus else (),
        ),
        "P12": lambda: evaluar_p12_bitacora(_bitacoras_del_sprint(RUTA_BITACORA)),
    }
    return [Fila(codigo, TITULOS[codigo], *chequeos[codigo]()) for codigo in codigos]


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meta_prototipo.py",
        description="Evalua las 12 metas del sprint del prototipo AREN.IA, agrupadas en P0-P5.",
    )
    parser.add_argument(
        "--hasta",
        choices=list(FASES),
        default=None,
        help="evalua solo las metas de esta fase y las anteriores (por defecto, las doce)",
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
