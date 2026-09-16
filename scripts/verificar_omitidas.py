"""Verificador de CI: ninguna prueba omitida en el JUnit de pytest.

Siete archivos de prueba usan `pytest.importorskip` (ifcopenshell, scikit-learn,
sentence-transformers) y `test_normalizacion.py` se omite si el modelo de similitud no se puede
descargar. Si en CI faltara un extra, esas pruebas desaparecerian en silencio y la corrida saldria
verde: este script convierte "0 omitidas" en una condicion del pipeline.

Codigos de salida: 0 sin omitidas; 1 con alguna omitida (se listan con su motivo); 2 sin evidencia
(archivo inexistente, XML ilegible o cero pruebas), porque la ausencia de datos nunca es un OK: el
mismo principio de `meta_alpha.estado_pruebas`.

Uso: `uv run python scripts/verificar_omitidas.py reporte-pruebas.xml`.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import _resultado_de, _testcases  # noqa: E402

SALIDA_SIN_OMITIDAS = 0
SALIDA_CON_OMITIDAS = 1
SALIDA_SIN_EVIDENCIA = 2


class SinEvidenciaError(ValueError):
    """El JUnit no permite afirmar nada: es ilegible o no registra pruebas."""


def omitidas(xml_texto: str) -> list[str]:
    """Cada prueba omitida como `classname::name - motivo`, en el orden del reporte.

    `SinEvidenciaError` si el XML no se puede leer o no registra ninguna prueba.
    """
    try:
        raiz = ET.fromstring(xml_texto)
    except ET.ParseError as error:
        raise SinEvidenciaError(f"JUnit ilegible: {error}") from error
    casos = list(_testcases(raiz))
    if not casos:
        raise SinEvidenciaError("el JUnit no registra ninguna prueba")
    return [_describir(caso) for caso in casos if _resultado_de(caso) == "omitidas"]


def _describir(caso: ET.Element) -> str:
    omision = caso.find("skipped")
    motivo = omision.get("message", "sin motivo") if omision is not None else "sin motivo"
    return f"{caso.get('classname')}::{caso.get('name')} - {motivo}"


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("reporte", type=Path, help="JUnit XML escrito por pytest --junitxml")
    reporte = analizador.parse_args(argv).reporte

    if not reporte.exists():
        print(f"verificar omitidas: no existe {reporte}")
        return SALIDA_SIN_EVIDENCIA
    try:
        lista = omitidas(reporte.read_text(encoding="utf-8"))
    except SinEvidenciaError as error:
        print(f"verificar omitidas: {error}")
        return SALIDA_SIN_EVIDENCIA
    if lista:
        print(f"verificar omitidas: {len(lista)} prueba(s) omitida(s)")
        for linea in lista:
            print(f"  {linea}")
        return SALIDA_CON_OMITIDAS
    print("verificar omitidas: 0 omitidas")
    return SALIDA_SIN_OMITIDAS


if __name__ == "__main__":
    sys.exit(main())
