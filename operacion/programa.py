"""El programa instalado contra su `manifiesto.json` (spec S5 §7.1, §10.4 y §11.2).

El instalador deja `{app}\\manifiesto.json` con ruta, tamaño y SHA-256 de cada archivo de
`codigo\\` y del `python.exe`. `verificar` dice qué cambió desde la instalación; en el
repositorio de desarrollo no hay manifiesto y no tiene sentido.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

NOMBRE = "manifiesto.json"
FORMATO = "silice-manifiesto"


def _sha256(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def entrada(raiz_app: Path, relativa: str) -> dict[str, object]:
    ruta = raiz_app / relativa
    return {"ruta": relativa, "tamano": ruta.stat().st_size, "sha256": _sha256(ruta)}


def escribir(raiz_app: Path, relativas: Iterable[str | Path], version: str) -> Path:
    rutas = sorted({Path(r).as_posix() for r in relativas})
    datos = {
        "formato": FORMATO,
        "version": version,
        "archivos": [entrada(raiz_app, r) for r in rutas],
    }
    destino = raiz_app / NOMBRE
    destino.write_text(json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return destino


def leer(raiz_app: Path) -> dict:
    datos = json.loads((raiz_app / NOMBRE).read_text(encoding="utf-8"))
    if datos.get("formato") != FORMATO:
        raise ValueError(f"{NOMBRE} no es un manifiesto de Sílice")
    return datos


def verificar(raiz_app: Path) -> list[str]:
    """Diferencias: `distinto X`, `falta X` y `sobra X` (solo bajo `codigo/`)."""
    esperado = {a["ruta"]: a for a in leer(raiz_app)["archivos"]}
    diferencias = []
    for ruta, datos in esperado.items():
        archivo = raiz_app / ruta
        if not archivo.is_file():
            diferencias.append(f"falta {ruta}")
        elif archivo.stat().st_size != datos["tamano"] or _sha256(archivo) != datos["sha256"]:
            diferencias.append(f"distinto {ruta}")
    codigo = raiz_app / "codigo"
    if codigo.is_dir():
        presentes = {p.relative_to(raiz_app).as_posix() for p in codigo.rglob("*") if p.is_file()}
        diferencias.extend(f"sobra {ruta}" for ruta in sorted(presentes - set(esperado)))
    return sorted(diferencias, key=lambda d: (d.split(" ", 1)[0] != "distinto", d))
