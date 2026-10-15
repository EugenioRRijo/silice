"""Reúne las licencias de Python y de cada paquete instalado en `LICENCIAS\\` (spec S5 §7.1 paso 5).

    python instalador/licencias.py --salida build/app/LICENCIAS [--solo-ruta CARPETA]

Sale con 1 si un paquete no declara licencia y no trae ningún texto de licencia, o si falta la de
Python: esos casos se resuelven a mano con un ruling, no se omiten.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from importlib import metadata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PATRON = re.compile(r"(?i)^(licen[cs]e|copying|notice|authors)([-_. ].*)?$")
RESPALDO_LICENCIAS: dict[str, str] = {
    "ifcopenshell": "GNU Lesser General Public License v3 or later (LGPLv3+)",
}


def _declarada(meta) -> str:
    expresion = meta.get("License-Expression") or meta.get("License") or ""
    if not expresion or expresion.upper() == "UNKNOWN":
        clases = [
            c.split("::")[-1].strip() for c in meta.get_all("Classifier", []) if "License ::" in c
        ]
        expresion = "; ".join(clases)
    return " ".join(expresion.split("\n")[0].split())[:90]


def _de_licencias_pep639(archivo) -> bool:
    """Todo lo que la rueda deja en `*.dist-info/licenses/` (PEP 639) es texto de licencia, se
    llame como se llame: pypdfium2 (extra `pdf`, 1.5) guarda ahí `Apache-2.0.txt` y las licencias
    de lo que trae compilado PDFium (freetype, ICU, libjpeg...), que deben viajar con el binario."""
    partes = archivo.parts
    return len(partes) > 2 and partes[0].endswith(".dist-info") and partes[1] == "licenses"


def _textos(dist) -> list[Path]:
    halladas = []
    for archivo in dist.files or []:
        if _de_licencias_pep639(archivo) or (
            PATRON.match(archivo.name)
            and (
                "licenses" in archivo.parts
                or len(archivo.parts) <= 2
                or archivo.parts[0].endswith(".dist-info")
            )
        ):
            ruta = Path(str(dist.locate_file(archivo)))
            if ruta.is_file():
                halladas.append(ruta)
    return halladas


def _textos_respaldo(nombre: str) -> list[Path]:
    """Textos de respaldo para paquetes conocidos sin archivo de licencia en dist-info (ARQ-2)."""
    if nombre.lower() == "ifcopenshell":
        candidatos = [RAIZ / "docs" / "licencias_ifc.md"]
        return [c for c in candidatos if c.is_file()]
    return []


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--salida", required=True, type=Path)
    analizador.add_argument("--solo-ruta", action="append", type=Path, help="buscar solo aquí")
    analizador.add_argument(
        "--python-licencia", type=Path, default=Path(sys.base_prefix) / "LICENSE.txt"
    )
    argumentos = analizador.parse_args(argv)
    problemas: list[str] = []
    argumentos.salida.mkdir(parents=True, exist_ok=True)
    if argumentos.python_licencia.is_file():
        (argumentos.salida / "Python").mkdir(exist_ok=True)
        shutil.copyfile(argumentos.python_licencia, argumentos.salida / "Python" / "LICENSE.txt")
    else:
        problemas.append(f"falta la licencia de Python en {argumentos.python_licencia}")
    # `distributions(path=None)` falla en 3.13: sin --solo-ruta no se pasa el argumento.
    filtro = {"path": [str(p) for p in argumentos.solo_ruta]} if argumentos.solo_ruta else {}
    filas = []
    for dist in sorted(metadata.distributions(**filtro), key=lambda d: d.metadata["Name"].lower()):
        nombre, version = dist.metadata["Name"], dist.version
        declarada, textos = _declarada(dist.metadata), _textos(dist)
        if not declarada:
            declarada = RESPALDO_LICENCIAS.get(nombre.lower(), "")
        if not textos:
            textos = _textos_respaldo(nombre)
        if not declarada and not textos:
            problemas.append(f"{nombre} {version}: sin licencia declarada ni texto de licencia")
        carpeta = argumentos.salida / f"{nombre}-{version}"
        for numero, texto in enumerate(textos):
            carpeta.mkdir(exist_ok=True)
            destino = carpeta / texto.name
            shutil.copyfile(
                texto, destino if not destino.exists() else carpeta / f"{numero}-{texto.name}"
            )
        filas.append(f"| {nombre} | {version} | {declarada or 'ver texto'} |")
    (argumentos.salida / "INDICE.md").write_text(
        "# Licencias de terceros\n\n| Paquete | Versión | Licencia |\n|---|---|---|\n"
        + "\n".join(filas)
        + "\n\nPython: carpeta `Python\\`. Sílice: `LICENSE` (propietaria).\n",
        encoding="utf-8",
    )
    for problema in problemas:
        print(problema, file=sys.stderr)
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
