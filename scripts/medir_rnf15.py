"""Mide RNF-15: el tiempo del control de obra en `aplicacion.control`, sin Streamlit (spec S2 §3.3).

La métrica de la spec de S2 pide, para una obra de 500 partidas, 52 períodos semanales y 26
valuaciones, una mediana de **2 s o menos** en dos trabajos:

1. desde registrar una valuación hasta tener el informe de control, los indicadores, las alertas y
   la reproyección (`aplicacion.control.registrar_y_controlar`), sobre una base con las 25
   valuaciones anteriores; y
2. calcular las cuatro opciones de recuperación (`aplicacion.control.calcular_las_opciones`).

Genera la obra con el generador determinista (`scripts/generar_obra_control.py`, semilla 0), la
guarda una vez en un archivo SQLite temporal y, para que cada corrida parta del mismo estado,
copia ese archivo antes de cada registro. Hace **una corrida de calentamiento** (no cuenta) y mide
**cinco**; la cifra de cada trabajo es la **mediana**.

Uso:
    uv run python scripts/medir_rnf15.py                  # el tamano de la spec (500/52/26)
    uv run python scripts/medir_rnf15.py --partidas 100   # otro tamaño
    uv run python scripts/medir_rnf15.py --estricto       # sale con 1 si una mediana supera 2 s

**Solo registra.** Sin `--estricto` sale siempre con 0, aunque supere los 2 s: el veredicto de
RNF-15 se toma en el equipo de desarrollo (como RNF-03 y RNF-11) y la CI solo anota la cifra en
Linux y Windows, porque una máquina compartida o cargada no debe romper la corrida. La cifra queda
en `scripts/_salida_rnf15.json` (ignorado por git), de donde la lee la meta de Sílice (C6: sin cifra
no es OK), y se anota en `docs/plan_pruebas.md` §10.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from aplicacion import control  # noqa: E402
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor  # noqa: E402
from scripts import generar_obra_control as generador  # noqa: E402
from scripts.medir_rnf11 import medir  # noqa: E402

PARTIDAS = 500
PERIODOS = 52
VALUACIONES = 26
CORRIDAS = 5
UMBRAL_SEGUNDOS = 2.0
SEMILLA = 0
RUTA_SALIDA = RAIZ / "scripts" / "_salida_rnf15.json"


def _url(ruta: Path) -> str:
    return f"sqlite:///{ruta.as_posix()}"


def preparar(carpeta: Path, partidas: int, periodos: int, valuaciones: int):
    """La base con la obra y sus `valuaciones - 1` primeras valuaciones, y la obra generada."""
    obra = generador.generar(partidas, periodos, valuaciones, SEMILLA)
    base = carpeta / "base.db"
    motor = crear_motor(_url(base))
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            generador.sembrar(sesion, obra)
            sesion.commit()
    finally:
        motor.dispose()
    return base, obra


def _filas_de(valuacion) -> list[dict[str, str]]:
    return [
        {
            "Partida": linea.codigo_partida,
            "Cantidad": format(linea.cantidad, "f"),
            "Fecha de medicion": "",
            "Observacion": "",
        }
        for linea in valuacion.lineas
    ]


def trabajo_de_registro(base: Path, obra, carpeta: Path) -> Callable[[int], object]:
    """Registrar la última valuación sobre una copia de la base y obtener el control completo."""
    ultima = obra.valuaciones[-1]

    def trabajo(i: int) -> object:
        copia = carpeta / f"corrida_{i}.db"
        shutil.copy(base, copia)
        motor = crear_motor(_url(copia))
        try:
            with abrir_sesion(motor) as sesion:
                return control.registrar_y_controlar(
                    sesion,
                    generador.NOMBRE,
                    Catalogo(sesion),
                    numero=ultima.numero,
                    desde=ultima.desde.isoformat(),
                    hasta=ultima.hasta.isoformat(),
                    fecha=ultima.fecha.isoformat(),
                    inspector=ultima.inspector,
                    filas=_filas_de(ultima),
                    fuente=generador.FUENTE,
                    responsable=generador.RESPONSABLE,
                    precios=obra.precios,
                )
        finally:
            motor.dispose()

    return trabajo


def trabajo_de_opciones(base: Path, obra, carpeta: Path) -> Callable[[int], object]:
    """Calcular las cuatro opciones de recuperación sobre el control al corte (ya calculado)."""
    copia = carpeta / "opciones.db"
    shutil.copy(base, copia)
    motor = crear_motor(_url(copia))
    try:
        with abrir_sesion(motor) as sesion:  # la última valuación no está en `base`
            generador.registrar_valuacion_de(sesion, obra.valuaciones[-1])
            generador.registrar_costo_de(sesion, obra.costos[-1])
            sesion.commit()
            resultado = control.calcular_el_control(
                sesion, generador.NOMBRE, Catalogo(sesion), precios=obra.precios
            )
    finally:
        motor.dispose()
    return lambda i: control.calcular_las_opciones(resultado)


def _coma(valor: float) -> str:
    return f"{valor:.3f}".replace(".", ",")


def _equipo() -> str:
    return f"{platform.platform()}; {platform.processor() or 'procesador sin nombre'}; " + (
        f"{os.cpu_count()} nucleos; Python {platform.python_version()}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--partidas", type=int, default=PARTIDAS)
    analizador.add_argument("--periodos", type=int, default=PERIODOS)
    analizador.add_argument("--valuaciones", type=int, default=VALUACIONES)
    analizador.add_argument("--corridas", type=int, default=CORRIDAS)
    analizador.add_argument("--umbral", type=float, default=UMBRAL_SEGUNDOS)
    analizador.add_argument("--salida", type=Path, default=RUTA_SALIDA)
    analizador.add_argument(
        "--estricto", action="store_true", help="sale con 1 si una mediana supera el umbral"
    )
    args = analizador.parse_args(argv)

    with tempfile.TemporaryDirectory() as nombre:
        carpeta = Path(nombre)
        base, obra = preparar(carpeta, args.partidas, args.periodos, args.valuaciones)
        registro = medir(trabajo_de_registro(base, obra, carpeta), args.corridas)
        opciones = medir(trabajo_de_opciones(base, obra, carpeta), args.corridas)
    cumple_registro = registro.mediana <= args.umbral
    cumple_opciones = opciones.mediana <= args.umbral
    datos = {
        "requisito": "RNF-15",
        "partidas": args.partidas,
        "periodos": args.periodos,
        "valuaciones": args.valuaciones,
        "corridas_registro_s": [round(c, 6) for c in registro.corridas],
        "mediana_registro_s": round(registro.mediana, 6),
        "corridas_opciones_s": [round(c, 6) for c in opciones.corridas],
        "mediana_opciones_s": round(opciones.mediana, 6),
        "mediana_texto": f"{_coma(registro.mediana)} / {_coma(opciones.mediana)}",
        "umbral_s": args.umbral,
        "cumple_registro": cumple_registro,
        "cumple_opciones": cumple_opciones,
        "equipo": _equipo(),
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    args.salida.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"RNF-15 ({args.partidas} partidas, {args.periodos} periodos, {args.valuaciones} "
        f"valuaciones): registro {_coma(registro.mediana)} s, opciones {_coma(opciones.mediana)} s "
        f"(umbral {_coma(args.umbral)} s)"
    )
    print(f"{'CUMPLE' if cumple_registro and cumple_opciones else 'NO CUMPLE'} (solo registra)")
    return 1 if args.estricto and not (cumple_registro and cumple_opciones) else 0


if __name__ == "__main__":
    raise SystemExit(main())
