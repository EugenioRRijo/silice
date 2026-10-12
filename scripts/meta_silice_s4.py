"""Parte S4 de la meta unica de Silice (spec S4 §11; plan 0.9.0, tarea 1).

`scripts/meta_silice.py` la descubre por su nombre. Con `--version 0.9.0 --hasta S4-n` evalua,
ademas de las siete comprobaciones comunes (C1-C7):

* C1, los numeros de S4 (UC-09, RF-32, RF-90 a RF-95, RNF-18) DEFINIDOS en la ERS;
* C3, la prueba de cada modulo nuevo antes que su codigo;
* `S4-RNF08` (S4-0): la ERS declara la excepcion a RNF-08 por el asistente en modo nube;
* `S4-BANCO` (S4-0): el banco de tareas es el declarado y su huella esta en el protocolo;
* `S4-ARQ` (S4-1): la guardia de arquitectura del asistente existe y `asistente` esta fuera del
  nucleo;
* `S4-NUCLEO` (S4-1): ningun commit que toca `asistente/` toca `core/` (S4 no abre SL-E10);
* `S4-CONGELADO` (S4-4): desde el congelado, el banco, el protocolo y el auditor no cambiaron;
* `S4-RESULTADOS` (S4-4): `docs/resultados_asistente.md` es el que genera el script, sin editar.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_silice import Comprobacion, Contexto, ParTDD, Parte  # noqa: E402

REQUISITOS_S4: tuple[str, ...] = (
    "UC-09",
    "RF-32",
    *(f"RF-{numero}" for numero in range(90, 96)),
    "RNF-18",
)
RUTA_ERS = RAIZ / "docs" / "ERS.md"
RUTA_PROTOCOLO_MD = RAIZ / "docs" / "protocolo_asistente.md"
RUTA_RESULTADOS = RAIZ / "docs" / "resultados_asistente.md"
FICHAS_ESPERADAS = {"desarrollo": 4, "evaluacion": 12}
SEMBRADOS_ESPERADOS = 3

PARES_S4: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_meta_silice_s4.py", "scripts/meta_silice_s4.py", "S4-0"),
    ParTDD("tests/unit/test_experimento_banco.py", "asistente/experimento/banco.py", "S4-0"),
    ParTDD("tests/unit/test_asistente_herramientas.py", "asistente/herramientas.py", "S4-1"),
    ParTDD("tests/unit/test_asistente_validacion.py", "asistente/validacion.py", "S4-1"),
    ParTDD("tests/unit/test_asistente_propuestas.py", "asistente/propuestas.py", "S4-1"),
    ParTDD("tests/unit/test_asistente_privacidad.py", "asistente/privacidad.py", "S4-2"),
    ParTDD("tests/unit/test_asistente_registro.py", "asistente/registro.py", "S4-2"),
    ParTDD("tests/unit/test_asistente_orquestador.py", "asistente/orquestador.py", "S4-2"),
    ParTDD("tests/unit/test_asistente_claude.py", "asistente/proveedores/claude.py", "S4-2"),
    ParTDD("tests/unit/test_asistente_ollama.py", "asistente/proveedores/ollama_local.py", "S4-2"),
    ParTDD("tests/unit/test_asistente_clave.py", "asistente/clave.py", "S4-2"),
    ParTDD("tests/unit/test_asistente_servicio.py", "asistente/servicio.py", "S4-3"),
    ParTDD("tests/unit/test_asistente_administracion.py", "asistente/administracion.py", "S4-3"),
    ParTDD(
        "tests/unit/test_experimento_comparador.py", "asistente/experimento/comparador.py", "S4-4"
    ),
    ParTDD("tests/unit/test_experimento_metricas.py", "asistente/experimento/metricas.py", "S4-4"),
    ParTDD(
        "tests/unit/test_experimento_mutaciones.py", "asistente/experimento/mutaciones.py", "S4-4"
    ),
    ParTDD(
        "tests/unit/test_experimento_ejecucion.py", "asistente/experimento/ejecucion.py", "S4-4"
    ),
    ParTDD(
        "tests/unit/test_experimento_congelado.py", "asistente/experimento/congelado.py", "S4-4"
    ),
    ParTDD("tests/unit/test_evaluar_asistente.py", "scripts/evaluar_asistente.py", "S4-4"),
)


# ---------------------------------------------------------------------------------------------
# Evaluadores puros
# ---------------------------------------------------------------------------------------------


def evaluar_rnf08(texto_ers: str | None) -> tuple[Estado, str]:
    """S4-RNF08: la fila de RNF-08 declara la excepcion del asistente en modo nube."""
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    fila = re.search(r"^\|[^|\n]*\|\s*RNF.08\b.*(?:\n(?!\|).*)*", texto_ers, re.MULTILINE)
    if fila is None:
        return Estado.FALLA, "la ERS no define RNF-08"
    bloque = fila.group(0).casefold()
    falta = [palabra for palabra in ("asistente", "nube", "administrador") if palabra not in bloque]
    if falta:
        return Estado.FALLA, "RNF-08 no declara la excepcion del asistente (falta: " + ", ".join(
            falta
        ) + ")"
    return Estado.OK, "RNF-08 declara la excepcion del asistente en modo nube"


def evaluar_banco(
    conteo: dict[str, int], sembrados: int, huella: str | None, texto_protocolo: str | None
) -> tuple[Estado, str]:
    """S4-BANCO: 4 de desarrollo, 12 de evaluacion (3 con sembrados) y la huella en el protocolo."""
    if conteo != FICHAS_ESPERADAS:
        return Estado.FALLA, f"el banco trae {conteo}; se esperan {FICHAS_ESPERADAS}"
    if sembrados != SEMBRADOS_ESPERADOS:
        return Estado.FALLA, f"{sembrados} tareas con sembrados; se esperan {SEMBRADOS_ESPERADOS}"
    if texto_protocolo is None or huella is None:
        return Estado.PENDIENTE, "falta docs/protocolo_asistente.md"
    if huella not in texto_protocolo:
        return Estado.FALLA, "docs/protocolo_asistente.md no lleva la huella actual del banco"
    return Estado.OK, f"banco de 16 tareas con huella {huella[:12]} en el protocolo"


def evaluar_arquitectura(test_existe: bool, texto_arquitectura: str | None) -> tuple[Estado, str]:
    """S4-ARQ: la guardia propia existe y `asistente` esta en PAQUETES_FUERA_DEL_NUCLEO."""
    if not test_existe:
        return Estado.FALLA, "falta tests/unit/test_arquitectura_asistente.py"
    if texto_arquitectura is None or not re.search(
        r"PAQUETES_FUERA_DEL_NUCLEO\s*=\s*\([^)]*\"asistente\"", texto_arquitectura
    ):
        return Estado.FALLA, "`asistente` no esta en PAQUETES_FUERA_DEL_NUCLEO"
    return Estado.OK, "guardia de arquitectura del asistente y paquete fuera del nucleo"


def evaluar_nucleo(commits_que_tocan_core: Sequence[str] | None) -> tuple[Estado, str]:
    """S4-NUCLEO: ningun commit que toca `asistente/` toca `core/` (S4 no abre SL-E10)."""
    if commits_que_tocan_core is None:
        return Estado.PENDIENTE, "sin historial de git"
    if commits_que_tocan_core:
        return Estado.FALLA, "tocan asistente/ y core/: " + ", ".join(commits_que_tocan_core)
    return Estado.OK, "ningun commit de asistente/ toca core/"


def evaluar_congelado(diferencias: Sequence[str]) -> tuple[Estado, str]:
    """S4-CONGELADO: sin `congelado.json` aun es PENDIENTE; con el, cualquier cambio es FALLA."""
    if len(diferencias) == 1 and "aun no esta congelado" in diferencias[0]:
        return Estado.PENDIENTE, diferencias[0]
    if diferencias:
        return Estado.FALLA, "; ".join(diferencias)
    return Estado.OK, "banco, protocolo y auditor son los congelados"


def evaluar_resultados(actual: str | None, regenerado: str | None) -> tuple[Estado, str]:
    """S4-RESULTADOS: el archivo es EXACTAMENTE lo que genera el script."""
    if actual is None:
        return Estado.PENDIENTE, "falta docs/resultados_asistente.md"
    if regenerado is None:
        return Estado.PENDIENTE, "faltan las corridas o el congelado para regenerarlo"
    if actual != regenerado:
        return Estado.FALLA, "docs/resultados_asistente.md fue editado a mano"
    return Estado.OK, "resultados_asistente.md es el generado por el script"


# ---------------------------------------------------------------------------------------------
# Orquestacion: disco y git
# ---------------------------------------------------------------------------------------------


def _leer(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else None


def _git(*argumentos: str) -> str | None:
    try:
        salida = subprocess.run(
            ["git", *argumentos], cwd=RAIZ, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return salida.stdout


def commits_de_asistente_que_tocan_core() -> list[str] | None:
    commits = _git("log", "--format=%h", "--", "asistente")
    if commits is None:
        return None
    tocan = []
    for commit in commits.split():
        archivos = _git("diff-tree", "--no-commit-id", "--name-only", "-r", commit) or ""
        if any(linea.startswith("core/") for linea in archivos.splitlines()):
            tocan.append(commit)
    return tocan


def _banco(_ctx: Contexto) -> tuple[Estado, str]:
    from asistente.experimento.banco import cargar_banco, huella_del_banco

    banco = cargar_banco()
    conteo = {c: sum(f.conjunto == c for f in banco.values()) for c in FICHAS_ESPERADAS}
    sembrados = sum(bool(f.sembrados) for f in banco.values() if f.conjunto == "evaluacion")
    return evaluar_banco(conteo, sembrados, huella_del_banco(), _leer(RUTA_PROTOCOLO_MD))


def _congelado(_ctx: Contexto) -> tuple[Estado, str]:
    from asistente.experimento import congelado

    return evaluar_congelado(congelado.verificar())


def _resultados(_ctx: Contexto) -> tuple[Estado, str]:
    from asistente.experimento import congelado
    from scripts.evaluar_asistente import (
        CONTROLADO,
        CORRIDAS,
        PROTOCOLO,
        _cargar_corridas,
        generar_informe,
    )

    actual = _leer(RUTA_RESULTADOS)
    if not (CORRIDAS.is_file() and CONTROLADO.is_file() and congelado.CONGELADO.is_file()):
        return evaluar_resultados(actual, None)
    controlado = {
        tipo: (d, n, tuple(par))
        for tipo, (d, n, par) in json.loads(CONTROLADO.read_text(encoding="utf-8")).items()
    }
    regenerado = generar_informe(
        _cargar_corridas(CORRIDAS),
        json.loads(PROTOCOLO.read_text(encoding="utf-8")),
        controlado,
        json.loads(congelado.CONGELADO.read_text(encoding="utf-8")),
    )
    return evaluar_resultados(actual, regenerado)


PARTE = Parte(
    nombre="S4 asistente de IA verificada y su experimento",
    requisitos={"S4-0": REQUISITOS_S4},
    pares_tdd=PARES_S4,
    comprobaciones=(
        Comprobacion(
            "S4-RNF08",
            "RNF-08 con la excepcion del asistente",
            "S4-0",
            lambda _c: evaluar_rnf08(_leer(RUTA_ERS)),
        ),
        Comprobacion("S4-BANCO", "Banco de tareas con su huella", "S4-0", _banco),
        Comprobacion(
            "S4-ARQ",
            "Guardia de arquitectura del asistente",
            "S4-1",
            lambda _c: evaluar_arquitectura(
                (RAIZ / "tests/unit/test_arquitectura_asistente.py").is_file(),
                _leer(RAIZ / "tests/unit/test_arquitectura.py"),
            ),
        ),
        Comprobacion(
            "S4-NUCLEO",
            "S4 no toca core/",
            "S4-1",
            lambda _c: evaluar_nucleo(commits_de_asistente_que_tocan_core()),
        ),
        Comprobacion("S4-CONGELADO", "Protocolo y auditor congelados", "S4-4", _congelado),
        Comprobacion("S4-RESULTADOS", "Resultados generados, no editados", "S4-4", _resultados),
    ),
)
