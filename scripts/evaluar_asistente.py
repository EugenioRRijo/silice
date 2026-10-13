"""Corre el protocolo del experimento del asistente y GENERA docs/resultados_asistente.md (RF-95).

Nunca se edita a mano el resultado. Subcomandos:

* `informe` genera el Markdown desde las corridas ya guardadas; no gasta nada.
* `mutaciones` corre la medicion controlada del auditor (determinista, sin IA, sin costo).
* `corrida --proveedor claude|ollama --conjunto desarrollo|evaluacion --acepto-costo --tope-usd N`
  llama a la API REAL: exige `--acepto-costo`, que solo da una persona con la cifra del piloto
  (§9.4); la clave sale del almacen de credenciales, nunca de un argumento ni de una variable de
  entorno. Se guarda tras CADA corrida y se reanuda donde quedo.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from asistente.experimento.metricas import (  # noqa: E402
    TIPOS,
    Corrida,
    Resumen,
    corrida_a_dict,
    corrida_de_dict,
    deteccion_controlada,
    resumir,
    wilson,
)
from scripts._experimento import contexto_del_experimento, proveedor_real  # noqa: E402

PROTOCOLO = RAIZ / "asistente" / "experimento" / "protocolo.json"
CONGELADO = RAIZ / "asistente" / "experimento" / "congelado.json"
CORRIDAS = RAIZ / "docs" / "resultados_asistente_corridas.json"
CONTROLADO = RAIZ / "docs" / "resultados_asistente_controlado.json"
SALIDA = RAIZ / "docs" / "resultados_asistente.md"
CABECERA = (
    "<!-- GENERADO por scripts/evaluar_asistente.py: no se edita a mano (RF-95). -->\n"
    "# Resultados del experimento del asistente (OE-H2)\n"
)


def porcentaje(valor: float | None) -> str:
    return "n/d" if valor is None else f"{valor * 100:.1f} %".replace(".", ",")


def intervalo(par: tuple[float, float]) -> str:
    return f"[{porcentaje(par[0])}; {porcentaje(par[1])}]"


def cumple(valor: float | None, umbral: float, *, minimo: bool) -> str:
    if valor is None:
        return "sin datos"
    bien = valor >= umbral if minimo else valor <= umbral
    return "cumple" if bien else "NO cumple (se declara la brecha)"


def generar_informe(
    corridas: Sequence[Corrida],
    protocolo: Mapping[str, object],
    controlado: Mapping[str, tuple[int, int, tuple[float, float]]],
    huellas: Mapping[str, str],
) -> str:
    """El Markdown completo: deteccion, falsas alarmas, escapes, medicion controlada y corridas."""
    hipotesis = protocolo["hipotesis_de_deteccion"]
    grupos: dict[tuple[str, str], list[Corrida]] = {}
    for c in corridas:
        grupos.setdefault((c.modelo, c.condicion), []).append(c)
    resumenes: list[Resumen] = [
        resumir(lista, hipotesis, int(protocolo["semilla"]), int(protocolo["replicas_bootstrap"]))
        for _, lista in sorted(grupos.items())
    ]
    u = protocolo["umbrales"]
    lineas = [CABECERA, "## Huellas congeladas\n"]
    lineas += [f"- {nombre}: `{valor}`" for nombre, valor in sorted(huellas.items())]
    lineas += [
        "",
        "## Deteccion del auditor y falsas alarmas (por modelo y condicion)\n",
        "| Modelo | Cond. | Corridas | Detectables | Detectados | Deteccion | IC 95 % "
        "(bootstrap por tarea) | Veredicto | Falsas alarmas | Veredicto | Propuestas "
        "validas | Exhaustividad | USD | Segundos |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in resumenes:
        lineas.append(
            f"| {r.modelo} | {r.condicion} | {r.corridas} | {r.errores_detectables} | "
            f"{r.detectados} | {porcentaje(r.deteccion)} | {intervalo(r.intervalo_deteccion)} | "
            f"{cumple(r.deteccion, float(u['deteccion']), minimo=True)} | "
            f"{porcentaje(r.tasa_falsas_alarmas)} | "
            f"{cumple(r.tasa_falsas_alarmas, float(u['falsas_alarmas']), minimo=False)} | "
            f"{porcentaje(r.propuestas_validas)} | {porcentaje(r.exhaustividad)} | "
            f"{r.costo_usd:.2f} | {r.segundos:.0f} |"
        )
    lineas += [
        "",
        "## Por tipo de error: detectados / errores (los no detectables por diseno, aparte)\n",
        "| Modelo | Cond. | " + " | ".join(TIPOS) + " |",
        "|---|---|" + "---|" * len(TIPOS),
    ]
    for r in resumenes:
        celdas = []
        for t in TIPOS:
            if t in r.por_tipo:
                d, n = r.por_tipo[t]
                celdas.append(f"{d}/{n}")
            elif t in r.no_detectables_por_diseno:
                celdas.append(f"{r.no_detectables_por_diseno[t]} (no detectable)")
            else:
                celdas.append("0")
        lineas.append(f"| {r.modelo} | {r.condicion} | " + " | ".join(celdas) + " |")
    lineas += [
        "",
        "## Medicion controlada con mutaciones (Wilson 95 % sobre el n efectivo)\n",
        "El auditor es determinista: los mutantes repetidos se descartan, asi que el n efectivo "
        "por tipo (los ensayos) puede ser menor que el n pedido. Wilson usa el efectivo.\n",
        "| Tipo | Detectados | Ensayos (n efectivo) | Intervalo | n pedido |",
        "|---|---|---|---|---|",
    ]
    pedido = int(protocolo["n_por_tipo_de_mutacion"])
    for tipo, (d, n, par) in controlado.items():
        lineas.append(f"| {tipo} | {d} | {n} | {intervalo(par)} | {pedido} |")
    lineas += [
        "",
        "## Todas las corridas\n",
        "| Tarea | Modelo | Cond. | Rep. | Errores | Detectados | Falsas alarmas | USD |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in sorted(corridas, key=lambda c: (c.tarea, c.modelo, c.condicion, c.repeticion)):
        lineas.append(
            f"| {c.tarea} | {c.modelo} | {c.condicion} | {c.repeticion} | "
            f"{','.join(e.tipo for e in c.errores) or '-'} | {len(c.veredicto.detectados)} | "
            f"{c.veredicto.falsas_alarmas} | {c.costo_usd:.2f} |"
        )
    lineas += ["", f"Limites declarados: {protocolo['limites']}", ""]
    return "\n".join(lineas)


def _cargar_corridas(ruta: Path) -> list[Corrida]:
    if not ruta.is_file():
        return []
    return [corrida_de_dict(d) for d in json.loads(ruta.read_text(encoding="utf-8"))]


def _guardar_corridas(ruta: Path, corridas: Sequence[Corrida]) -> None:
    contenido = json.dumps([corrida_a_dict(c) for c in corridas], indent=1, sort_keys=True)
    ruta.write_text(contenido + "\n", encoding="utf-8")


def medicion_controlada(protocolo: Mapping[str, object]) -> dict[str, tuple]:
    """Determinista, sin IA y sin costo: los mutantes de cada tipo, elaborados y auditados.

    Devuelve por tipo (detectados, n efectivo, Wilson): el n efectivo es la longitud real de lo que
    da `generar` (puede ser menor que el n pedido); un tipo sin mutantes figura con 0 ensayos.
    """
    from asistente.experimento.ejecucion import medir_mutantes
    from asistente.experimento.mutaciones import generar

    banco, composiciones, _, catalogo, referencia_de = contexto_del_experimento()
    referencias = {f.id: referencia_de(f) for f in banco.values() if f.conjunto == "evaluacion"}
    resultados: list[tuple[str, bool]] = []
    for tipo in TIPOS:
        mutantes = generar(
            tipo,
            referencias,
            int(protocolo["semilla"]),
            int(protocolo["n_por_tipo_de_mutacion"]),
            catalogo,
        )
        resultados += medir_mutantes(mutantes, referencias, composiciones=composiciones)
    medido = deteccion_controlada(resultados)
    return {t: medido.get(t, (0, 0, wilson(0, 0))) for t in TIPOS}


def _correr_real(args: argparse.Namespace, protocolo: Mapping[str, object]) -> int:
    from asistente.experimento.ejecucion import correr
    from asistente.tarifas import tarifa_de

    if args.esfuerzo:  # el piloto compara esfuerzos antes de fijar el del protocolo (RS4-11)
        protocolo = {**protocolo, "esfuerzo": args.esfuerzo}
    banco, composiciones, catalogo, _, _ = contexto_del_experimento()
    proveedor = proveedor_real(args.proveedor, protocolo, args.empresa)
    disponibilidad = proveedor.disponible()
    if not disponibilidad.disponible:
        print(disponibilidad.motivo, file=sys.stderr)
        return 3
    tarifa = tarifa_de(proveedor.modelo, local=args.proveedor == "ollama")
    corridas = _cargar_corridas(args.corridas)
    hechas = {(c.tarea, c.modelo, c.condicion, c.repeticion) for c in corridas}
    gastado = sum((c.costo_usd for c in corridas), Decimal(0))
    fichas = sorted((f for f in banco.values() if f.conjunto == args.conjunto), key=lambda f: f.id)
    for ficha in fichas:
        for repeticion in range(1, int(protocolo["repeticiones"]) + 1):
            if (ficha.id, proveedor.modelo, args.condicion, repeticion) in hechas:
                continue
            if gastado > Decimal(str(args.tope_usd)):
                print(f"Tope de {args.tope_usd} USD alcanzado: se detiene.", file=sys.stderr)
                return 4
            corrida = correr(
                ficha,
                proveedor,
                catalogo=catalogo,
                tarifa=tarifa,
                composiciones=composiciones,
                condicion=args.condicion,
                repeticion=repeticion,
            )
            corridas.append(corrida)
            gastado += corrida.costo_usd
            _guardar_corridas(args.corridas, corridas)  # se guarda tras CADA corrida
            print(
                f"{ficha.id} rep {repeticion}: errores {[e.tipo for e in corrida.errores]}, "
                f"{corrida.costo_usd:.2f} USD (acumulado {gastado:.2f})"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="orden", required=True)
    informe = sub.add_parser("informe")
    informe.add_argument("--corridas", type=Path, default=CORRIDAS)
    informe.add_argument("--salida", type=Path, default=SALIDA)
    mutaciones = sub.add_parser("mutaciones")
    mutaciones.add_argument("--salida", type=Path, default=CONTROLADO)
    real = sub.add_parser("corrida")
    real.add_argument("--proveedor", choices=("claude", "ollama"), required=True)
    real.add_argument("--conjunto", choices=("desarrollo", "evaluacion"), required=True)
    real.add_argument("--condicion", choices=("A", "B"), default="A")
    real.add_argument("--esfuerzo", choices=("low", "medium", "high", "xhigh", "max"))
    real.add_argument("--empresa", default="EMPRESA-PROPIA")
    real.add_argument("--tope-usd", type=float, required=True)
    real.add_argument("--corridas", type=Path, default=CORRIDAS)
    real.add_argument("--acepto-costo", action="store_true")
    args = parser.parse_args(argv)
    if args.orden == "corrida" and not args.acepto_costo:
        print(
            "Falta --acepto-costo: la corrida real gasta dinero y la autoriza una persona.",
            file=sys.stderr,
        )
        return 2
    protocolo = json.loads(PROTOCOLO.read_text(encoding="utf-8"))
    if args.orden == "mutaciones":
        controlado = medicion_controlada(protocolo)
        args.salida.write_text(
            json.dumps(controlado, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        detalle = ", ".join(f"{t} {d}/{n}" for t, (d, n, _) in controlado.items())
        print(f"{args.salida} (detectados/n efectivo): {detalle}")
        return 0
    if args.orden == "corrida":
        return _correr_real(args, protocolo)
    corridas = _cargar_corridas(args.corridas)
    controlado = {
        t: (d, n, tuple(par))
        for t, (d, n, par) in json.loads(CONTROLADO.read_text(encoding="utf-8")).items()
    }
    huellas = json.loads(CONGELADO.read_text(encoding="utf-8"))
    args.salida.write_text(
        generar_informe(corridas, protocolo, controlado, huellas), encoding="utf-8"
    )
    print(f"{args.salida} generado con {len(corridas)} corridas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
