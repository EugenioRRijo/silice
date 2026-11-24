"""Mide la detección de fallas inyectadas tras recalcular con LibreOffice y trasplantar valores.

Herramienta LOCAL de la Fase 1: encadena `inyectar` -> `RecalculadorLibreOffice` ->
`trasplantar` -> `procesar_libro` -> `causas_de_hallazgos` -> `deteccion`, guarda un JSON fuera
del repositorio con el manifiesto de corrida y los resultados por inyección, e imprime el resumen
con coma decimal (sin descripciones de la empresa y compatible con cp1252).

    uv run python scripts/medir_inyeccion.py LIBRO.xlsx --taxonomia T.toml \\
        --n 12 --semilla 7 --salida D:/medicion
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from aplicacion.manifiesto_corrida import manifiesto  # noqa: E402
from aplicacion.oraculo_hoja import (  # noqa: E402
    LibreOfficeNoDisponibleError,
    Recalculador,
    RecalculadorLibreOffice,
)
from aplicacion.trasplante_valores import trasplantar  # noqa: E402
from fusion.proceso import procesar_libro  # noqa: E402
from scripts.inyector_fallas import Inyeccion, cargar_taxonomia, inyectar  # noqa: E402
from scripts.medir_auditoria_libro import (  # noqa: E402
    Sembrado,
    _destino_seguro,
    causas_de_hallazgos,
    decimal_coma,
    deteccion,
)


def resumen_pantalla(
    inyecciones: Sequence[Inyeccion],
    detectado_por: Mapping[int, int | None],
    *,
    destino: Path,
) -> str:
    """Resumen legible en español con coma decimal, solo en caracteres cp1252."""
    total = len(inyecciones)
    detectadas = sum(1 for inj in inyecciones if detectado_por.get(inj.numero) is not None)
    tasa = (detectadas / total * 100.0) if total else 0.0
    pct = f"{decimal_coma(tasa, 1)} %"
    lineas = [f"Detectó {detectadas} de {total} fallas inyectadas ({pct})"]
    for inj in inyecciones:
        if detectado_por.get(inj.numero) is None:
            lineas.append(
                f"- Escapada #{inj.numero} ({inj.categoria}, {inj.operacion}): "
                f"{inj.hoja}!{inj.celda}"
            )
    lineas.append(f"Informe JSON: {destino}")
    return "\n".join(lineas)


def ejecutar(
    ruta_libro: Path,
    ruta_taxonomia: Path,
    carpeta_salida: Path,
    *,
    n: int = 12,
    semilla: int = 7,
    raiz_repo: Path = RAIZ,
    configuracion_regional: str = "es-VE",
    fecha: date | None = None,
    perfil: str | None = None,
    recalculador: Recalculador | None = None,
) -> tuple[Path, str]:
    """Inyecta fallas, recalcula, trasplanta, audita, mide detección y escribe el JSON."""
    origen = Path(ruta_libro)
    destino = _destino_seguro(
        Path(carpeta_salida) / f"medicion_{origen.stem}_s{semilla}.json",
        Path(raiz_repo),
    )
    motor = (
        recalculador
        if recalculador is not None
        else RecalculadorLibreOffice(configuracion_regional=configuracion_regional)
    )
    ver_lo = motor.version() if hasattr(motor, "version") else None

    datos_base = origen.read_bytes()
    taxonomia = cargar_taxonomia(Path(ruta_taxonomia))
    inyectado, inyecciones = inyectar(datos_base, taxonomia, n=n, semilla=semilla)
    recalculado = motor.recalcular(inyectado, origen.name)
    trasplantado = trasplantar(inyectado, recalculado)
    resultado = procesar_libro(
        trasplantado, origen.name, fecha_devolucion=fecha, perfil=perfil
    )
    causas = causas_de_hallazgos(resultado.informe.hallazgos)
    sembrados = [
        Sembrado(numero=inj.numero, celda=f"{inj.hoja}!{inj.celda}", tipo=inj.categoria)
        for inj in inyecciones
    ]
    det = deteccion(sembrados, causas)

    carga = {
        "sha256_libro_base": hashlib.sha256(datos_base).hexdigest(),
        "manifiesto": manifiesto(
            version_libreoffice=ver_lo,
            semilla=semilla,
            configuracion_regional=configuracion_regional,
        ),
        "totales": {
            "inyectadas": det.total,
            "detectadas": det.detectados,
            "escapadas": det.total - det.detectados,
            "tasa_deteccion": det.valor,
            "causas_informadas": len(causas),
            "hallazgos_informados": sum(c.ocurrencias for c in causas),
        },
        "inyecciones": [
            {
                "numero": inj.numero,
                "hoja": inj.hoja,
                "celda": inj.celda,
                "categoria": inj.categoria,
                "operacion": inj.operacion,
                "detectado_por": det.por_sembrado[inj.numero],
            }
            for inj in inyecciones
        ],
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(carga, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    texto = resumen_pantalla(inyecciones, det.por_sembrado, destino=destino)
    return destino, texto


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("libro", help="ruta del libro .xlsx base")
    analizador.add_argument("--taxonomia", required=True, help="archivo TOML de categorías")
    analizador.add_argument("--n", type=int, default=12, help="cantidad de fallas a inyectar")
    analizador.add_argument("--semilla", type=int, default=7, help="semilla determinista")
    analizador.add_argument("--salida", required=True, help="carpeta fuera del repositorio")
    analizador.add_argument("--configuracion-regional", default="es-VE")
    analizador.add_argument("--fecha", type=date.fromisoformat, default=None, help="AAAA-MM-DD")
    analizador.add_argument("--perfil", default=None, help="perfil de plantilla")
    analizador.add_argument("--raiz-repo", default=str(RAIZ))
    args = analizador.parse_args(argv)

    try:
        _, texto = ejecutar(
            Path(args.libro),
            Path(args.taxonomia),
            Path(args.salida),
            n=args.n,
            semilla=args.semilla,
            raiz_repo=Path(args.raiz_repo),
            configuracion_regional=args.configuracion_regional,
            fecha=args.fecha,
            perfil=args.perfil,
        )
    except LibreOfficeNoDisponibleError as error:
        print(error)
        return 2
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
