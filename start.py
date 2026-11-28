"""Arranque de Sílice con un solo comando (como un `npm run dev`).

    uv run start.py              # prepara los casos de demostración la primera vez y abre la app
    uv run start.py --puerto 8600
    uv run start.py --sin-demo   # no siembra casos (usa los que ya haya en data/casos/)
    uv run start.py --reiniciar-demo   # vuelve a copiar los casos de demostración

Siembra en `data/casos/` (carpeta de datos de desarrollo, no versionada) cinco casos DIDÁCTICOS,
todos ficticios (NORMAS.md §1): `demo`, `of001`, `ti001`, `s1` (copias de las bases de prueba de
la 0.6.0) y `obra_control` (una obra generada con valuaciones y costos para Control de obra, y
con la tasa y las series viales didácticas, también ficticias, para Riesgo).
Nunca toca `data/apu.db`. Un solo proceso (Uvicorn, `api.main:app`) sirve la API y la interfaz
de React (`/app/`, compilada con `npm run build` en frontend-desktop) y escucha solo en 127.0.0.1.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

CASOS_COPIADOS = ("demo", "of001", "ti001", "s1")
BASES_PRUEBA = RAIZ / "tests" / "fixtures" / "bases" / "v0_6_0"
PUERTO_POR_OMISION = 8501
RUTA_INTERFAZ = "/app/"
RUTA_SALUD = "/salud"


def carpeta_casos() -> Path:
    from operacion.config import carpeta_casos as de_la_configuracion

    return de_la_configuracion()


#: Las valuaciones semanales de la obra de la demo de Control (`sembrar_obra_control`).
VALUACIONES_DE_LA_DEMO = 5


def inicio_de_la_demo(hoy: date) -> date:
    """El lunes en que empieza la obra de la demo: tantas semanas antes del lunes de esta semana
    como valuaciones lleva, así la última se firma este lunes y ninguna queda en el futuro (prueba
    en vivo del 2026-11-18: la demo sembraba valuaciones hasta el 04/12)."""
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes - timedelta(weeks=VALUACIONES_DE_LA_DEMO)


#: Meses de tasa ficticia que siembra la demo antes del inicio de la obra: con 24 variaciones Riesgo
#: tiene más que los 12 meses completos que pide (prueba en vivo del 2026-11-18, hallazgo 4).
MESES_DE_TASA_DE_LA_DEMO = 25
FUENTE_DE_LA_TASA_DE_LA_DEMO = (
    "tasa ficticia didáctica de la demo de Sílice: no es la publicada por el BCV (NORMAS.md §1)"
)


def sembrar_tasa_didactica(sesion, inicio: date, hoy: date) -> None:
    """Una tasa Bs/USD **ficticia**, un valor el día 15 de cada mes, desde
    `MESES_DE_TASA_DE_LA_DEMO` meses antes del mes de `inicio` hasta el mes anterior al de `hoy`:
    la historia mensual que Riesgo necesita para proyectar la obra de la demo. Sube 2 % por mes;
    su fuente dice que es didáctica. No confirma."""
    import hashlib
    from decimal import Decimal

    from core.catalog.indices import (
        LADO_POR_DEFECTO,
        Observacion,
        definicion_tasa,
        registrar_importacion,
    )

    indice = inicio.year * 12 + inicio.month - 1 - MESES_DE_TASA_DE_LA_DEMO
    ultimo = hoy.year * 12 + hoy.month - 2  # el mes anterior al de hoy
    valor = Decimal("36.50")
    observaciones = []
    while indice <= ultimo:
        observaciones.append(Observacion(date(indice // 12, indice % 12 + 1, 15), valor))
        valor = (valor * Decimal("1.02")).quantize(Decimal("0.01"))
        indice += 1
    huella = hashlib.sha256(
        "|".join(f"{o.fecha.isoformat()}:{o.valor}" for o in observaciones).encode()
    ).hexdigest()
    registrar_importacion(
        sesion,
        definicion_tasa(LADO_POR_DEFECTO),
        observaciones,
        # la pantalla «Índices del BCV» no lista las importaciones: el nombre lo dice también
        archivo="tasa_FICTICIA_didactica_de_la_demo_no_es_del_BCV.csv",
        huella=huella,
        fuente=FUENTE_DE_LA_TASA_DE_LA_DEMO,
        fecha_descarga=hoy,
        responsable="script:start",
        filas_leidas=len(observaciones),
        filas_rechazadas=0,
    )


#: La muestra versionada de las dos series viales, FICTICIA (`data/samples/vial/README.md`).
MUESTRA_DE_SERIES_VIALES = RAIZ / "data" / "samples" / "vial" / "series_ficticias.csv"
#: Con qué nombre se importa la muestra corrida: la importación guarda el nombre del archivo.
ARCHIVO_DE_LAS_SERIES_DE_LA_DEMO = "series_viales_FICTICIAS_didacticas_de_la_demo.csv"
FUENTE_DE_LAS_SERIES_DE_LA_DEMO = (
    "series viales ficticias didácticas de la demo de Sílice: no son el PPI de asfalto de FRED/BLS "
    "ni el precio del gasoil de la Gaceta (NORMAS.md §1)"
)


def _indice_de_mes(dia: date) -> int:
    return dia.year * 12 + dia.month - 1


def series_viales_corridas(hoy: date) -> str:
    """La muestra ficticia de las series viales, en CSV canónico, con cada fecha corrida los meses
    enteros que hagan falta para que su último mes sea el anterior al de `hoy` (como la tasa
    didáctica). Los valores no cambian: desde el día de la siembra, sus 36 meses cubren de sobra el
    mínimo de historia para proyectar, también cuando la muestra versionada (que termina en una
    fecha fija) se queda atrás o va por delante."""
    import csv
    import io

    filas = list(csv.DictReader(io.StringIO(MUESTRA_DE_SERIES_VIALES.read_text(encoding="utf-8"))))
    ultimo = max(_indice_de_mes(date.fromisoformat(f["fecha"])) for f in filas)
    corrimiento = _indice_de_mes(hoy) - 1 - ultimo
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=list(filas[0]), lineterminator="\n")
    escritor.writeheader()
    for fila in filas:
        indice = _indice_de_mes(date.fromisoformat(fila["fecha"])) + corrimiento
        escritor.writerow({**fila, "fecha": date(indice // 12, indice % 12 + 1, 1).isoformat()})
    return salida.getvalue()


def sembrar_series_viales_didacticas(sesion, hoy: date) -> list[int | None]:
    """Importa las dos series viales ficticias (`series_viales_corridas`) con
    `importar_serie_csv`, la misma importación de una serie real: devuelve el id de cada
    importación, o `None` si esa serie ya tenía el mismo archivo (misma huella). Sin ellas, la obra
    en USD de la demo no se mueve en Riesgo (prueba en vivo del 2026-11-18). No confirma.

    Idempotente dentro del mismo mes (el archivo corrido es el mismo y su huella también) o sobre
    una base limpia, que es lo que hace `--reiniciar-demo`. Otro mes sobre la misma base importaría
    otra revisión de la serie (otra huella), como una serie real revisada."""
    import tempfile

    from aplicacion.riesgo.series import SERIES_VIALES, importar_serie_csv

    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / ARCHIVO_DE_LAS_SERIES_DE_LA_DEMO
        ruta.write_text(series_viales_corridas(hoy), encoding="utf-8", newline="")
        return [
            importar_serie_csv(
                sesion,
                serie.codigo,
                ruta,
                fuente=FUENTE_DE_LAS_SERIES_DE_LA_DEMO,
                responsable="script:start",
                hoy=hoy,
            )
            for serie in SERIES_VIALES
        ]


def sembrar_obra_control(destino: Path, *, hoy: date | None = None) -> None:
    """Una obra pequeña con valuaciones y costos registrados, para la pantalla Control de obra.
    Sus fechas van hasta la semana de `hoy` (por defecto, el reloj, leído una sola vez), nunca
    después. Trae también lo que Riesgo necesita para que la obra (en USD) se mueva: la tasa y las
    dos series viales, ficticias, y el asfalto y el gasoil en dos partidas (manual, §10.6).

    Todo o nada, como `_sembrar_copia`: se siembra en un temporal de la misma carpeta y se publica
    con `_publicar` (`os.replace` tras borrar el `-wal`/`-shm` viejos del destino, con el servidor
    detenido). Si algo falla a medias, el temporal (y sus -wal/-shm/-journal) se borra y
    `destino` queda como estaba: sin crear o con la base anterior (arbitraje de
    feature/vivo-control: antes quedaba una base vacía que `preparar_demo` no volvía a sembrar)."""
    from core.catalog.sesion import abrir_sesion, crear_motor
    from operacion.base_datos import preparar_base
    from scripts.generar_obra_control import (
        generar,
        registrar_costo_de,
        registrar_valuacion_de,
        sembrar,
    )

    dia = hoy or date.today()
    temporal = destino.with_name(f".{destino.name}.tmp")
    restos = [temporal] + [
        temporal.with_name(temporal.name + s) for s in ("-wal", "-shm", "-journal")
    ]
    try:
        for resto in restos:
            resto.unlink(missing_ok=True)
        preparar_base(temporal)
        inicio = inicio_de_la_demo(dia)
        obra = generar(
            partidas=12,
            periodos=10,
            valuaciones=VALUACIONES_DE_LA_DEMO,
            semilla=7,
            inicio=inicio,
            insumos_viales=True,
        )
        motor = crear_motor(f"sqlite:///{temporal.resolve().as_posix()}")
        try:
            with abrir_sesion(motor) as sesion:
                sembrar(sesion, obra, con_valuaciones=True)
                registrar_valuacion_de(sesion, obra.valuaciones[-1])
                registrar_costo_de(sesion, obra.costos[-1])
                sembrar_tasa_didactica(sesion, inicio, dia)
                sembrar_series_viales_didacticas(sesion, dia)
                sesion.commit()
        finally:
            motor.dispose()
        for resto in restos[1:]:
            resto.unlink(missing_ok=True)
        _publicar(temporal, destino)
    finally:
        for resto in restos:
            resto.unlink(missing_ok=True)


def sellar_caso_copiado(destino: Path) -> None:
    """Lleva una base copiada de antes de la cadena a `head` y sella su historial (D3).

    Las bases de `tests/fixtures/bases/` son inmutables (su ficha lleva el hash) y nacen sin
    eslabones: sin esto, «Entregar paquete» dice «Cadena rota... no tiene eslabon». El sello es
    el declarado de siempre (`tipo = "retroactivo"`, que la Trazabilidad muestra) y usa la forma
    actual de las cifras (28 decimales, VB-1), asi que la version queda entregable.

    `preparar_base` puede migrar con respaldo en `SILICE_RESPALDOS` (el juego nombra el archivo
    que se le pasa, o sea el temporal de `preparar_demo`). Deja la base cerrada al volver."""
    from aplicacion.entrega import anexos_de_cadena
    from core.budget.cadena import sellar_historial
    from core.catalog.sesion import abrir_sesion, crear_motor
    from operacion.base_datos import preparar_base

    preparar_base(destino)
    motor = crear_motor(f"sqlite:///{destino.resolve().as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sellar_historial(sesion, "script:start", anexos_de=anexos_de_cadena)
            sesion.commit()
    finally:
        motor.dispose()


def _publicar(temporal: Path, destino: Path) -> None:
    """Publica la base `temporal` como `destino` con `os.replace`, borrando antes el `-wal`, el
    `-shm` y el `-journal` del destino: los de la corrida anterior quedan si el servidor se cerró
    sin checkpoint, y SQLite reaplicaría ese WAL viejo sobre la base nueva (la demo «resembrada»
    traía los datos de antes, con riesgo de corrupción; re-verificación en vivo del 2026-11-18).

    Se hace con el servidor detenido: `start.py` prepara la demo antes de servir, así que nadie
    tiene abierta la base del destino."""
    for sufijo in ("-wal", "-shm", "-journal"):
        destino.with_name(destino.name + sufijo).unlink(missing_ok=True)
    os.replace(temporal, destino)


def _sembrar_copia(origen: Path, destino: Path) -> None:
    """Todo o nada: copia, sella en un temporal de la misma carpeta y publica con `_publicar`
    (`os.replace` tras borrar el WAL viejo del destino). Si algo falla, el temporal (y sus
    -wal/-shm/-journal) se borra y `destino` no existe."""
    temporal = destino.with_name(f".{destino.name}.tmp")
    restos = [temporal] + [
        temporal.with_name(temporal.name + s) for s in ("-wal", "-shm", "-journal")
    ]
    try:
        for resto in restos:
            resto.unlink(missing_ok=True)
        shutil.copyfile(origen, temporal)
        sellar_caso_copiado(temporal)
        for resto in restos[1:]:
            resto.unlink(missing_ok=True)
        _publicar(temporal, destino)
    finally:
        for resto in restos:
            resto.unlink(missing_ok=True)


def preparar_empresa() -> None:
    """La carpeta de la empresa en `head`, como `operacion.lanzador` antes de servir. Uvicorn
    solo la crearía en su sitio con la primera petición, y la Vista general, que la lee en solo
    lectura a la vez, la vería a medio migrar («No se pudo leer 1 carpeta»; T6, 2026-11-28)."""
    from operacion import base_datos, config

    base_datos.preparar_base(config.ruta_caso_por_defecto())


def preparar_demo(*, reiniciar: bool = False) -> list[str]:
    """Deja los casos de demostración en la carpeta de casos; devuelve lo que sembró."""
    casos = carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    sembrados: list[str] = []
    for nombre in CASOS_COPIADOS:
        origen = BASES_PRUEBA / f"{nombre}.db"
        destino = casos / f"{nombre}.db"
        if not origen.exists():
            print(f"  (no está {origen.relative_to(RAIZ)}; se omite {nombre})")
            continue
        if reiniciar or not destino.exists():
            _sembrar_copia(origen, destino)
            sembrados.append(nombre)
    destino = casos / "obra_control.db"
    if reiniciar or not destino.exists():
        sembrar_obra_control(destino)
        sembrados.append("obra_control")
    return sembrados


def _abrir_navegador_cuando_responda(puerto: int) -> None:
    direccion = f"http://127.0.0.1:{puerto}"
    for _ in range(120):
        try:
            with urllib.request.urlopen(f"{direccion}{RUTA_SALUD}", timeout=1) as respuesta:
                if respuesta.status == 200:
                    webbrowser.open(f"{direccion}{RUTA_INTERFAZ}")
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--puerto", type=int, default=PUERTO_POR_OMISION)
    analizador.add_argument("--sin-demo", action="store_true", help="no siembra casos")
    analizador.add_argument("--reiniciar-demo", action="store_true", help="recopia los casos")
    analizador.add_argument("--sin-navegador", action="store_true")
    args = analizador.parse_args(argv)

    print("Sílice: arranque de demostración (datos ficticios, solo en este equipo)")
    preparar_empresa()
    if not args.sin_demo:
        sembrados = preparar_demo(reiniciar=args.reiniciar_demo)
        print(f"  casos sembrados: {', '.join(sembrados) if sembrados else 'ya estaban todos'}")
    print(f"  carpeta de casos: {carpeta_casos()}")
    print(f"  http://127.0.0.1:{args.puerto}{RUTA_INTERFAZ}   (Ctrl+C para detener)")

    if not args.sin_navegador:
        threading.Thread(
            target=_abrir_navegador_cuando_responda, args=(args.puerto,), daemon=True
        ).start()
    orden = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.puerto),
        "--no-access-log",
    ]
    try:
        return subprocess.call(orden, cwd=RAIZ, env=dict(os.environ))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
