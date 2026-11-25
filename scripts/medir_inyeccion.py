"""Mide la detección de fallas inyectadas tras recalcular con LibreOffice y trasplantar valores.

Herramienta LOCAL de la Fase 1: encadena `inyectar` -> `RecalculadorLibreOffice` ->
`trasplantar` -> `procesar_libro` -> `causas_de_hallazgos` -> `deteccion`, guarda un JSON fuera
del repositorio con el manifiesto de corrida y los resultados por inyección, e imprime el resumen
con coma decimal (sin descripciones de la empresa y compatible con cp1252).

La cifra OFICIAL de detección es la de TODAS LAS FALLAS A LA VEZ, la de este modo (decisión de
Eugenio, `docs/bitacora/2026-11-25-cifra-oficial-de-deteccion.md`). `--una-por-vez` da la cifra
secundaria y no decide el criterio de fracaso. En los dos modos un hallazgo que el libro base ya
tenía (misma regla y mismas celdas de origen) no se acredita a ninguna falla.

    uv run python scripts/medir_inyeccion.py LIBRO.xlsx --taxonomia T.toml \\
        --n 12 --semilla 7 --salida D:/medicion
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from adapters.hoja_empresa.guardia import ArchivoRechazado  # noqa: E402
from adapters.hoja_empresa.modelo import LibroNoInterpretable  # noqa: E402
from aplicacion.manifiesto_corrida import manifiesto  # noqa: E402
from aplicacion.oraculo_hoja import (  # noqa: E402
    LibreOfficeNoDisponibleError,
    Recalculador,
    RecalculadorLibreOffice,
)
from aplicacion.trasplante_valores import trasplantar  # noqa: E402
from asistente.experimento.metricas import wilson  # noqa: E402
from fusion.proceso import procesar_libro  # noqa: E402
from scripts.hallazgos_previos import hallazgos_nuevos  # noqa: E402
from scripts.inyector_fallas import (  # noqa: E402
    _CELDA_XML,
    Inyeccion,
    _attr,
    _mapa_hojas,
    cargar_taxonomia,
    inyectar,
)
from scripts.medir_auditoria_libro import (  # noqa: E402
    Sembrado,
    _destino_seguro,
    _no_aplica,
    causas_de_hallazgos,
    criterio_de_fracaso,
    deteccion,
    intervalo_wilson,
    porcentaje_de,
)


class MenosFallasQueLasPedidas(ValueError):  # noqa: N818 (nombre de dominio)
    """La taxonomía y el libro no dieron lugar para sembrar todas las fallas pedidas."""


def _comprobar_cantidad(pedidas: int, sembradas: int, permitir_menos: bool) -> None:
    if sembradas < pedidas and not permitir_menos:
        raise MenosFallasQueLasPedidas(
            f"Se pidieron {pedidas} fallas y solo se pudieron sembrar {sembradas}: la medición "
            "no sería la planeada. Amplíe la taxonomía o use --permitir-menos."
        )


def _auditar(
    datos: bytes, nombre: str, motor: Recalculador, fecha: date | None, perfil: str | None
) -> list:
    trasplantado = trasplantar(datos, motor.recalcular(datos, nombre))
    resultado = procesar_libro(trasplantado, nombre, fecha_devolucion=fecha, perfil=perfil)
    return list(resultado.informe.hallazgos)


# --- cifras: Wilson y criterio de fracaso ------------------------------------------------------


def _bloque_cifras(detectadas: int, total: int, *, oficial: bool, previos: int = 0) -> list[str]:
    lineas = [f"Intervalo de Wilson 95 %: {intervalo_wilson(detectadas, total)}"]
    if previos:
        lineas.append(f"Hallazgos previos del libro descontados: {previos}")
    lineas.append("Criterio de fracaso sellado:")
    lineas += [f"- {t}" for t in criterio_de_fracaso(deteccion=(detectadas, total))]
    if not oficial:
        lineas.append("Esta cifra (una por vez) es secundaria: no decide el fracaso.")
    return lineas


def resumen_pantalla(
    inyecciones: Sequence[Inyeccion],
    detectado_por: Mapping[int, int | None],
    *,
    destino: Path,
    previos: int = 0,
) -> str:
    """Resumen legible en español con coma decimal, solo en caracteres cp1252."""
    total = len(inyecciones)
    detectadas = sum(1 for inj in inyecciones if detectado_por.get(inj.numero) is not None)
    pct = porcentaje_de(detectadas, total)
    lineas = [f"Detectó {detectadas} de {total} fallas inyectadas ({pct})"]
    lineas += _bloque_cifras(detectadas, total, oficial=True, previos=previos)
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
    permitir_menos: bool = False,
) -> tuple[Path, str]:
    """Inyecta todas las fallas a la vez, recalcula, trasplanta, audita, mide detección y escribe
    el JSON. Es la cifra OFICIAL. Audita también el libro base por la misma cadena y no acredita
    a una falla un hallazgo que el base ya tenía."""
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
    _comprobar_cantidad(n, len(inyecciones), permitir_menos)
    base = _auditar(datos_base, origen.name, motor, fecha, perfil)
    auditados = _auditar(inyectado, origen.name, motor, fecha, perfil)
    nuevos = hallazgos_nuevos(base, auditados)
    previos = len([h for h in auditados if not _no_aplica(h)]) - len(nuevos)
    causas = causas_de_hallazgos(nuevos)
    sembrados = [
        Sembrado(numero=inj.numero, celda=f"{inj.hoja}!{inj.celda}", tipo=inj.categoria)
        for inj in inyecciones
    ]
    det = deteccion(sembrados, causas)

    carga = {
        "modo": "todas_a_la_vez",
        "cifra_oficial": True,
        "sha256_libro_base": hashlib.sha256(datos_base).hexdigest(),
        "manifiesto": manifiesto(
            version_libreoffice=ver_lo,
            semilla=semilla,
            configuracion_regional=configuracion_regional,
        ),
        "totales": {
            "pedidas": n,
            "inyectadas": det.total,
            "detectadas": det.detectados,
            "escapadas": det.total - det.detectados,
            "tasa_deteccion": det.valor,
            "intervalo_wilson_95": list(wilson(det.detectados, det.total)),
            "hallazgos_previos_descontados": previos,
            "causas_informadas": len(causas),
            "hallazgos_informados": sum(c.ocurrencias for c in causas),
        },
        "criterio_de_fracaso": criterio_de_fracaso(deteccion=(det.detectados, det.total)),
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
    texto = resumen_pantalla(inyecciones, det.por_sembrado, destino=destino, previos=previos)
    return destino, texto


# --- una falla por vez (pruebas de mutación; cifra secundaria) ---------------------------------


def reaccion(base: Sequence, mutado: Sequence) -> list[str]:
    """Reglas de los hallazgos del libro mutado que el libro limpio no daba (misma regla y mismas
    celdas de origen; un hallazgo previo que solo cambia una cifra de su descripción no cuenta).
    Los avisos «no aplicable» no cuentan."""
    return sorted({h.regla for h in hallazgos_nuevos(base, mutado)})


def _solo_una(datos_base: bytes, inyectado: bytes, inj: Inyeccion) -> bytes:
    """El libro base con SOLO la celda de `inj` tomada del libro con todas las fallas: así cada
    mutante es una de las mismas n inyecciones del modo de todas a la vez."""
    with zipfile.ZipFile(io.BytesIO(datos_base)) as zb:
        infos = zb.infolist()
        paquete = {i.filename: zb.read(i.filename) for i in infos}
    with zipfile.ZipFile(io.BytesIO(inyectado)) as zi:
        paquete_inyectado = {i.filename: zi.read(i.filename) for i in zi.infolist()}
    parte = _mapa_hojas(paquete)[inj.hoja]

    def buscar(xml: str):
        for m in _CELDA_XML.finditer(xml):
            if _attr(m.group("attrs"), "r") == inj.celda:
                return m
        raise RuntimeError(f"No se encontró la celda {inj.hoja}!{inj.celda} en el XML.")

    xml_base = paquete[parte].decode("utf-8")
    en_base = buscar(xml_base)
    nueva = buscar(paquete_inyectado[parte].decode("utf-8")).group(0)
    paquete[parte] = (xml_base[: en_base.start()] + nueva + xml_base[en_base.end() :]).encode()
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in infos:
            zout.writestr(info, paquete[info.filename])
    return salida.getvalue()


def ejecutar_mutantes(
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
    permitir_menos: bool = False,
) -> tuple[Path, str]:
    """Aplica las MISMAS `n` inyecciones del modo de todas a la vez, cada una sola sobre el libro
    limpio; recalcula, trasplanta y audita cada copia, y la compara con el libro limpio pasado
    por la misma cadena. Un libro que Sílice rechaza se cuenta aparte: no es detección."""
    origen = Path(ruta_libro)
    destino = _destino_seguro(
        Path(carpeta_salida) / f"mutantes_{origen.stem}_s{semilla}.json", Path(raiz_repo)
    )
    motor = recalculador or RecalculadorLibreOffice(configuracion_regional=configuracion_regional)
    datos_base = origen.read_bytes()
    taxonomia = cargar_taxonomia(Path(ruta_taxonomia))
    todo, inyecciones = inyectar(datos_base, taxonomia, n=n, semilla=semilla)
    _comprobar_cantidad(n, len(inyecciones), permitir_menos)
    base = _auditar(datos_base, origen.name, motor, fecha, perfil)

    mutantes: list[dict[str, object]] = []
    for inj in inyecciones:
        rechazado = False
        try:
            mutado = _solo_una(datos_base, todo, inj)
            nuevas = reaccion(base, _auditar(mutado, origen.name, motor, fecha, perfil))
        except (LibroNoInterpretable, ArchivoRechazado):
            nuevas, rechazado = [], True
        mutantes.append({
            "numero": inj.numero, "hoja": inj.hoja, "celda": inj.celda,
            "categoria": inj.categoria, "operacion": inj.operacion,
            "detectada": bool(nuevas), "reglas_nuevas": nuevas,
            "rechazado": rechazado,
        })  # fmt: skip

    detectadas = sum(1 for m in mutantes if m["detectada"])
    rechazados = sum(1 for m in mutantes if m["rechazado"])
    carga = {
        "modo": "una_por_vez",
        "cifra_oficial": False,
        "sha256_libro_base": hashlib.sha256(datos_base).hexdigest(),
        "manifiesto": manifiesto(
            version_libreoffice=motor.version() if hasattr(motor, "version") else None,
            semilla=semilla,
            configuracion_regional=configuracion_regional,
        ),
        "totales": {"pedidas": n, "inyectadas": len(mutantes), "detectadas": detectadas,
                    "rechazados": rechazados,
                    "intervalo_wilson_95": list(wilson(detectadas, len(mutantes))),
                    "hallazgos_libro_limpio": len([h for h in base if not _no_aplica(h)])},
        "criterio_de_fracaso": criterio_de_fracaso(deteccion=(detectadas, len(mutantes))),
        "mutantes": mutantes,
    }  # fmt: skip
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(carga, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lineas = [f"Detectó {detectadas} de {len(mutantes)} fallas inyectadas una por vez "
              f"({porcentaje_de(detectadas, len(mutantes))})"]  # fmt: skip
    if rechazados:
        lineas.append(f"Sílice rechazó {rechazados} libros mutantes: se cuentan aparte, no como "
                      "detectados.")  # fmt: skip
    lineas += _bloque_cifras(detectadas, len(mutantes), oficial=False)
    for m in mutantes:
        if not m["detectada"]:
            rotulo = "Rechazada" if m["rechazado"] else "Escapada"
            lineas.append(f"- {rotulo} #{m['numero']} ({m['categoria']}, {m['operacion']}): "
                          f"{m['hoja']}!{m['celda']}")  # fmt: skip
    lineas.append(f"Informe JSON: {destino}")
    return destino, "\n".join(lineas)


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
    analizador.add_argument(
        "--una-por-vez", action="store_true",
        help="cifra SECUNDARIA: inyecta cada falla sola y la compara con el libro limpio",
    )  # fmt: skip
    analizador.add_argument(
        "--permitir-menos", action="store_true",
        help="no es error que se siembren menos fallas que las pedidas con --n",
    )  # fmt: skip
    args = analizador.parse_args(argv)

    try:
        _, texto = (ejecutar_mutantes if args.una_por_vez else ejecutar)(
            Path(args.libro),
            Path(args.taxonomia),
            Path(args.salida),
            n=args.n,
            semilla=args.semilla,
            raiz_repo=Path(args.raiz_repo),
            configuracion_regional=args.configuracion_regional,
            fecha=args.fecha,
            perfil=args.perfil,
            permitir_menos=args.permitir_menos,
        )
    except LibreOfficeNoDisponibleError as error:
        print(error)
        return 2
    except MenosFallasQueLasPedidas as error:
        print(error)
        return 3
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
