"""Ejecuta el oráculo independiente (LibreOffice sin interfaz) sobre un libro `.xlsx`.

Herramienta LOCAL de la Fase 1 (evaluación no circular): recalcula las fórmulas con un motor
ajeno a Sílice, escribe fuera del repositorio un JSON con el manifiesto de corrida y las
discrepancias por celda (sin descripciones de la empresa), e imprime un resumen con coma
decimal.

    uv run python scripts/oraculo_libro.py LIBRO.xlsx --salida D:/medicion
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from aplicacion.cifras import texto_de_cifra  # noqa: E402
from aplicacion.manifiesto_corrida import manifiesto  # noqa: E402
from aplicacion.oraculo_hoja import (  # noqa: E402
    TOLERANCIA_ABSOLUTA,
    TOLERANCIA_RELATIVA,
    Discrepancia,
    RecalculadorLibreOffice,
    ValorCelda,
    contar_formulas,
    oraculo,
)
from scripts.medir_auditoria_libro import _destino_seguro, decimal_coma  # noqa: E402


def _valor_json(valor: ValorCelda) -> str | bool | None:
    if isinstance(valor, Decimal):
        return format(valor, "f")
    return valor


def _valor_pantalla(valor: ValorCelda) -> str:
    if valor is None:
        return "vacío"
    if isinstance(valor, bool):
        return "VERDADERO" if valor else "FALSO"
    if isinstance(valor, Decimal):
        return texto_de_cifra(valor)
    return valor


def resumen_pantalla(
    discrepancias: Sequence[Discrepancia],
    *,
    total_formulas: int,
    destino: Path,
    tolerancia_absoluta: Decimal = TOLERANCIA_ABSOLUTA,
) -> str:
    """Resumen legible en español con coma decimal, sin descripciones de la empresa."""
    n = len(discrepancias)
    etiqueta_disc = "1 discrepancia" if n == 1 else f"{n} discrepancias"
    etiqueta_form = (
        "1 celda con fórmula" if total_formulas == 1 else f"{total_formulas} celdas con fórmula"
    )
    tasa = (n / total_formulas * 100.0) if total_formulas else 0.0
    tol = texto_de_cifra(tolerancia_absoluta)
    lineas = [
        f"Oráculo independiente: {etiqueta_disc} en {etiqueta_form} "
        f"({decimal_coma(tasa, 1)} %; tolerancia absoluta {tol})."
    ]
    for d in discrepancias:
        guardado = _valor_pantalla(d.guardado)
        recalculado = _valor_pantalla(d.recalculado)
        lineas.append(f"- {d.hoja}!{d.celda}: guardado {guardado} ≠ recalculado {recalculado}")
    lineas.append(f"Informe JSON: {destino}")
    return "\n".join(lineas)


def ejecutar(
    ruta_libro: Path,
    carpeta_salida: Path,
    *,
    raiz_repo: Path = RAIZ,
    configuracion_regional: str = "es-VE",
    semilla: int | None = None,
) -> tuple[Path, str]:
    """Recalcula `ruta_libro`, guarda el JSON fuera del repositorio y devuelve el resumen."""
    origen = Path(ruta_libro)
    destino = _destino_seguro(
        Path(carpeta_salida) / f"oraculo_{origen.stem}.json", Path(raiz_repo)
    )
    datos = origen.read_bytes()
    recalculador = RecalculadorLibreOffice(configuracion_regional=configuracion_regional)
    ver_lo = recalculador.version()
    total_formulas = contar_formulas(datos, origen.name)
    discrepancias = oraculo(
        datos,
        origen.name,
        recalculador,
        tolerancia_relativa=TOLERANCIA_RELATIVA,
        tolerancia_absoluta=TOLERANCIA_ABSOLUTA,
    )
    carga = {
        "sha256_libro": hashlib.sha256(datos).hexdigest(),
        "manifiesto": manifiesto(
            version_libreoffice=ver_lo,
            semilla=semilla,
            configuracion_regional=configuracion_regional,
        ),
        "total_formulas": total_formulas,
        "total_discrepancias": len(discrepancias),
        "discrepancias": [
            {
                "hoja": d.hoja,
                "celda": d.celda,
                "formula": d.formula,
                "guardado": _valor_json(d.guardado),
                "recalculado": _valor_json(d.recalculado),
            }
            for d in discrepancias
        ],
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(carga, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    texto = resumen_pantalla(discrepancias, total_formulas=total_formulas, destino=destino)
    return destino, texto


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("libro", help="ruta del libro .xlsx a verificar")
    analizador.add_argument("--salida", required=True, help="carpeta fuera del repositorio")
    analizador.add_argument("--configuracion-regional", default="es-VE")
    analizador.add_argument("--semilla", type=int, default=None)
    analizador.add_argument("--raiz-repo", default=str(RAIZ))
    args = analizador.parse_args(argv)
    _, texto = ejecutar(
        Path(args.libro),
        Path(args.salida),
        raiz_repo=Path(args.raiz_repo),
        configuracion_regional=args.configuracion_regional,
        semilla=args.semilla,
    )
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
