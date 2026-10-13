"""El congelado del protocolo (S4 §9.1): huellas del banco, del protocolo y del auditor.

Se congela DESPUES del piloto y ANTES de la primera corrida de evaluacion. Entre el congelado y la
ultima corrida, el banco, el protocolo y los archivos del auditor (`core/verification/` y
`adapters/espacio/reglas.py`, mas los modulos de las demas reglas externas que corran) deben tener
la misma huella: nadie ajusta reglas viendo los resultados. `verificar` devuelve lo que cambio.

`congelar` exige el arbol de git LIMPIO (M5): sin cambios ni archivos sin seguimiento, para que
el commit declarado sea exactamente lo que se congela. Un archivo del auditor que falta es error.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from asistente.experimento.banco import CARPETA_TAREAS, bytes_normalizados, huella_del_banco

RAIZ = Path(__file__).resolve().parents[2]
PROTOCOLO = Path(__file__).with_name("protocolo.json")
CONGELADO = Path(__file__).with_name("congelado.json")


def huella_de_archivos(rutas: list[str], raiz: Path = RAIZ) -> str:
    faltan = sorted(r for r in rutas if not (raiz / r).is_file())
    if faltan:
        raise FileNotFoundError(f"archivos del auditor que no existen: {faltan}")
    resumen = hashlib.sha256()
    for ruta in sorted(rutas):
        resumen.update(ruta.encode())
        resumen.update(b"\0")
        resumen.update(bytes_normalizados(raiz / ruta))
        resumen.update(b"\0")
    return resumen.hexdigest()


def calcular(
    protocolo: Path = PROTOCOLO, carpeta_tareas: Path = CARPETA_TAREAS, raiz: Path = RAIZ
) -> dict[str, str]:
    datos = json.loads(protocolo.read_text(encoding="utf-8"))
    return {
        "banco": huella_del_banco(carpeta_tareas),
        "protocolo": hashlib.sha256(bytes_normalizados(protocolo)).hexdigest(),
        "auditor": huella_de_archivos(datos["archivos_del_auditor"], raiz),
    }


def cambios_sin_commit(raiz: Path = RAIZ) -> list[str]:
    """Lo que `git status --porcelain` lista en `raiz`; `RuntimeError` si no es un repositorio."""
    try:
        salida = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=raiz,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"no se pudo leer el estado de git en {raiz}: {error}") from error
    return [linea for linea in salida.stdout.splitlines() if linea.strip()]


def congelar(commit: str, destino: Path = CONGELADO, **rutas) -> dict[str, str]:
    """Escribe `congelado.json`: las tres huellas y el commit en que se congelo.

    Exige el arbol limpio (M5): con cambios sin commit, `RuntimeError` y no escribe nada."""
    pendientes = cambios_sin_commit(rutas.get("raiz", RAIZ))
    if pendientes:
        raise RuntimeError(
            "el congelado exige el arbol limpio; hay cambios sin commit: " + "; ".join(pendientes)
        )
    huellas = {**calcular(**rutas), "commit": commit}
    destino.write_text(json.dumps(huellas, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return huellas


def verificar(congelado: Path = CONGELADO, **rutas) -> list[str]:
    """Que huellas ya no son las congeladas; vacio = nada cambio desde el congelado."""
    if not congelado.is_file():
        return ["el protocolo aun no esta congelado (falta congelado.json)"]
    guardado = json.loads(congelado.read_text(encoding="utf-8"))
    actual = calcular(**rutas)
    return [
        f"{nombre} cambio desde el congelado"
        for nombre in actual
        if actual[nombre] != guardado.get(nombre)
    ]
