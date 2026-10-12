"""Mide la tasa de detección y las falsas alarmas de la auditoría de planos (S3 §11.5, §13.5 b).

Para cada categoría del catálogo siembra el error (`scripts/sembrar_errores_planos.py`), audita el
plano sembrado y el limpio con las mismas reglas que la hoja (importación con su informe, R8 a R10
y R15; R16 contra el plano limpio como segunda fuente) y compara lo que la auditoría AGREGA:

* **detectado**: lo agregado cumple una de las detecciones del catálogo;
* **falsa alarma**: algo agregado que no está ni en la detección ni en las consecuencias admitidas;
* los controles **no detectables** se informan con su número y no entran en la tasa.

Meta del protocolo (`docs/protocolo_deteccion_planos.md`, ratificada por Eugenio el 2026-10-11):
100 % de lo detectable y cero falsas alarmas. La salida es una tabla Markdown o, con `--json`, el
mismo contenido para la bitácora.

    uv run python scripts/medir_deteccion_planos.py [--json]
    uv run python scripts/medir_deteccion_planos.py --limpio     # el conjunto exacto de OF-001
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.sembrar_errores_planos import (  # noqa: E402
    SEMILLA,
    SIEMBRAS,
    Sembrado,
    catalogo,
    limpio,
    sembrar,
)

RUTA_LIMPIO = RAIZ / "tests" / "fixtures" / "errores_planos" / "of001_limpio.py"


@dataclass(frozen=True, slots=True)
class Auditoria:
    """Lo que la hoja diría de un plano: estado, ítems del informe, hallazgos y su espacio."""

    estado: str
    items: tuple[tuple[str, str, str], ...]  # (tipo, tabla, mensaje), sin los «importado»
    hallazgos: tuple[tuple[str, str, str], ...]  # (regla, severidad, descripción)
    espacio: object = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class Agregado:
    """Lo que la auditoría del plano sembrado trae de más que la del limpio."""

    estado: str
    items: tuple[tuple[str, str, str], ...]
    hallazgos: tuple[tuple[str, str, str], ...]
    diferencias: tuple[tuple[str, str | None, str | None], ...]  # R16: (tipo, id plano, id ref)


def auditar(contenido: bytes, formato: str) -> Auditoria:
    from datetime import date as fecha

    from adapters.espacio.planos.geometria_plano import reglas_plano
    from adapters.espacio.reglas import reglas_espacio
    from core.contracts.presupuesto import Presupuesto

    if formato == "dxf":
        from adapters.espacio.planos.dxf import importar_dxf

        resultado = importar_dxf(contenido, nombre="plano.dxf")
    else:
        from adapters.espacio.planos.ifc import importar_ifc

        resultado = importar_ifc(contenido, nombre="plano.ifc")
    items = tuple(sorted(
        (i.tipo.value, i.tabla, i.mensaje) for i in resultado.informe if i.tipo.value != "importado"
    ))
    hallazgos: list[tuple[str, str, str]] = []
    espacio = None
    if resultado.estado.value == "importada":
        espacio = resultado.espacio()
        presupuesto = Presupuesto(codigo="X", fecha=fecha(2026, 11, 1), moneda="USD", partidas=())
        for regla in (*reglas_espacio(espacio), *reglas_plano(espacio)):
            hallazgos += [(h.regla, h.severidad.name, h.descripcion)
                          for h in regla.evaluar(presupuesto)]
    return Auditoria(resultado.estado.value, items, tuple(sorted(hallazgos)), espacio)


def agregado(sembrada: Auditoria, base: Auditoria, referencia: Auditoria | None) -> Agregado:
    from adapters.espacio.planos.contraste import contrastar

    diferencias: tuple[tuple[str, str | None, str | None], ...] = ()
    if referencia is not None and sembrada.espacio is not None and referencia.espacio is not None:
        diferencias = tuple(
            (d.tipo, d.id_plano, d.id_referencia)
            for d in contrastar(sembrada.espacio, referencia.espacio).diferencias
        )
    return Agregado(
        sembrada.estado if sembrada.estado != base.estado else "",
        tuple((Counter(sembrada.items) - Counter(base.items)).elements()),
        tuple((Counter(sembrada.hallazgos) - Counter(base.hallazgos)).elements()),
        diferencias,
    )


def cumple(etiqueta: str, agregados: Agregado) -> list[object]:
    """Lo agregado que satisface una etiqueta del catálogo (lista vacía si nada). Las
    alternativas `a|b` suman lo que cumple cada una."""
    if "|" in etiqueta:
        return [x for alternativa in etiqueta.split("|") for x in cumple(alternativa, agregados)]
    forma, _, resto = etiqueta.partition(":")
    if forma == "estado":
        return [agregados.estado] if agregados.estado == resto else []
    if forma == "item":
        tipo, _, texto = resto.partition(":")
        return [i for i in agregados.items if i[0] == tipo and texto in i[2]]
    if forma == "regla":
        regla, _, texto = resto.partition(":")
        return [h for h in agregados.hallazgos if h[0] == regla and texto in h[2]]
    if forma == "r16":
        return [d for d in agregados.diferencias if d[0] == resto]
    return []


@dataclass(frozen=True, slots=True)
class Resultado:
    id: str
    variante: int
    detalle: str
    detectable: bool
    detectado: bool
    falsas_alarmas: tuple[object, ...]


def evaluar(sembrado: Sembrado, base: dict[str, Auditoria], fila) -> Resultado:
    """Audita un plano sembrado y lo compara con el catálogo."""
    sembrada = auditar(sembrado.contenido, sembrado.formato)
    referencia = base["dxf"] if sembrado.referencia is not None else None
    nuevo = agregado(sembrada, base[sembrado.formato], referencia)
    explicados: list[object] = []
    detectado = bool(fila.deteccion) and all(cumple(e, nuevo) for e in fila.deteccion)
    for etiqueta in (*fila.deteccion, *fila.consecuencias):
        explicados += cumple(etiqueta, nuevo)
    pendientes = Counter([*nuevo.items, *nuevo.hallazgos, *nuevo.diferencias])
    pendientes.subtract(Counter(map(tuple, explicados)))
    alarmas = tuple((+pendientes).elements())
    if nuevo.estado and nuevo.estado not in {e.partition(":")[2] for e in fila.deteccion}:
        alarmas += (nuevo.estado,)
    return Resultado(sembrado.id, sembrado.variante, sembrado.detalle, fila.detectable,
                     detectado, alarmas)


def medir(semilla: int = SEMILLA) -> dict:
    """Siembra todo el catálogo y devuelve la medición por categoría."""
    base = {"dxf": auditar(limpio("dxf"), "dxf"), "ifc": auditar(limpio("ifc"), "ifc")}
    filas = catalogo()
    resultados = [
        evaluar(sembrar(id_, variante, semilla), base, filas[id_])
        for id_, siembra in SIEMBRAS.items() for variante in range(siembra.variantes)
    ]
    categorias = {}
    for id_ in SIEMBRAS:
        propios = [r for r in resultados if r.id == id_]
        categorias[id_] = {
            "sembrados": len(propios), "detectables": filas[id_].detectable,
            "detectados": sum(r.detectado for r in propios),
            "falsas_alarmas": sum(len(r.falsas_alarmas) for r in propios),
        }
    detectables = [r for r in resultados if r.detectable]
    return {
        "semilla": semilla, "categorias": categorias, "resultados": resultados,
        "tasa": sum(r.detectado for r in detectables) / len(detectables),
        "falsas_alarmas": sum(len(r.falsas_alarmas) for r in detectables),
        "no_detectables": sum(1 for r in resultados if not r.detectable),
        "no_detectados": sum(1 for r in resultados if not r.detectable and not r.detectado
                             and not r.falsas_alarmas),
        "limpio": {
            "dxf": {"items": [list(i) for i in base["dxf"].items],
                    "hallazgos": [list(h) for h in base["dxf"].hallazgos]},
            "ifc": {"items": [list(i) for i in base["ifc"].items],
                    "hallazgos": [list(h) for h in base["ifc"].hallazgos]},
        },
    }


ENCABEZADO_LIMPIO = """El conjunto EXACTO de los planos limpios (S3 §11.5 y §13.5 b; de S3-0).

`DXF_*` es lo que la hoja diría del DXF de OF-001 (`tests/fixtures/planos/of001.dxf`): los ítems
del informe de importación que no son «importado» y los hallazgos de R8 a R10 y R15 (R9, R10 y
R15 no dan ninguno). `IFC_*` es lo mismo del IFC de oficina de `planos_ifc_ids`. Lo regenera
`uv run python scripts/medir_deteccion_planos.py --limpio`; cambiarlo a mano es cambiar el
oráculo de la medición. Las constantes son tuplas de `(tipo, tabla, mensaje)` y de
`(regla, severidad, descripción)`.
"""
ANCHO = 96


def _literal(texto: str) -> str:
    return json.dumps(texto, ensure_ascii=False)


def _trozos(mensaje: str, sangria: int) -> list[str]:
    """El mensaje partido en literales de una línea cada uno (≤ 100 columnas)."""
    trozos, actual = [], ""
    for palabra in mensaje.split(" "):
        candidato = palabra if not actual else actual + " " + palabra
        if actual and sangria + len(_literal(candidato + " ")) > ANCHO:
            trozos.append(actual + " ")
            actual = palabra
        else:
            actual = candidato
    trozos.append(actual)
    return trozos


def modulo_limpio(limpio: dict) -> str:
    """El texto de `tests/fixtures/errores_planos/of001_limpio.py`."""
    salida = ['"""' + ENCABEZADO_LIMPIO + '"""', ""]
    for formato in ("dxf", "ifc"):
        for clave, nombre in (("items", "ITEMS"), ("hallazgos", "HALLAZGOS")):
            salida.append(f"{formato.upper()}_{nombre} = (")
            for *cortos, largo in limpio[formato][clave]:
                salida.append("    (" + ", ".join(_literal(c) for c in cortos) + ",")
                partes = _trozos(largo, 5)
                salida += [("     " + _literal(p)) for p in partes]
                salida[-1] += "),"
            salida += [")", ""]
    salida.append("LIMPIO = {")
    for formato in ("dxf", "ifc"):
        f = formato.upper()
        salida.append(f'    "{formato}": {{"items": {f}_ITEMS, "hallazgos": {f}_HALLAZGOS}},')
    salida.append("}")
    return "\n".join(salida) + "\n"


def tabla(medicion: dict) -> str:
    filas = ["| Categoría | Sembrados | Detectados | Falsas alarmas | Detectable |",
             "|---|---|---|---|---|"]
    for id_, c in medicion["categorias"].items():
        filas.append(f"| {id_} | {c['sembrados']} | {c['detectados']} | {c['falsas_alarmas']} | "
                     f"{'sí' if c['detectables'] else 'no (control)'} |")
    filas.append("")
    filas.append(f"Tasa de detección: {medicion['tasa']:.0%}. Falsas alarmas: "
                 f"{medicion['falsas_alarmas']}. Controles no detectables: "
                 f"{medicion['no_detectables']} ({medicion['no_detectados']} sin detectar, como "
                 "se espera).")
    return "\n".join(filas)


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--json", action="store_true")
    analizador.add_argument("--limpio", action="store_true",
                            help="escribe el conjunto exacto del plano limpio")
    args = analizador.parse_args(argv)
    medicion = medir()
    if args.limpio:
        print(modulo_limpio(medicion["limpio"]), end="")
        return 0
    if args.json:
        medicion = {k: v for k, v in medicion.items() if k != "resultados"}
        print(json.dumps(medicion, ensure_ascii=False, indent=2, default=str))
    else:
        print(tabla(medicion))
    return 0 if medicion["tasa"] == 1 and medicion["falsas_alarmas"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
