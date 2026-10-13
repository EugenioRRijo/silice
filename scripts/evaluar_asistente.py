"""Corre el protocolo del experimento del asistente y GENERA docs/resultados_asistente.md (RF-95).

Nunca se edita a mano el resultado. Subcomandos:

* `informe` genera el Markdown desde las corridas ya guardadas; no gasta nada.
* `mutaciones` corre la medicion controlada del auditor (determinista, sin IA, sin costo).
* `corrida --proveedor claude|ollama --conjunto desarrollo|evaluacion --acepto-costo --tope-usd N`
  llama a la API REAL: exige `--acepto-costo`, que solo da una persona con la cifra del piloto
  (§9.4); la clave sale del almacen de credenciales, nunca de un argumento ni de una variable de
  entorno. Se guarda tras CADA corrida y se reanuda donde quedo.

Piloto y evaluacion no se mezclan: `desarrollo` (el piloto) escribe por omision en
`docs/piloto_asistente_corridas.json`; solo `evaluacion` escribe en
`docs/resultados_asistente_corridas.json`, el que lee `informe` (que rechaza corridas de fichas que
no sean de evaluacion). Cada corrida guardada declara el esfuerzo con que se hizo y la reanudacion
no salta una corrida hecha con otro esfuerzo. La evaluacion y la medicion controlada exigen el
protocolo congelado (`congelado.verificar()` vacio) y la evaluacion usa el esfuerzo del protocolo.

Tope de gasto (`--tope-usd`, finito y mayor que cero): se compara con `>=` ANTES de cada corrida y
NO corta una sesion a medias (alteraria lo medido); el gasto puede superar el tope, como maximo, en
el costo de una sesion, que tiene su propio tope (`Topes.costo` de `correr`). El acumulado cuenta
TODAS las corridas del archivo, de cualquier modelo. Se corre un proceso a la vez por archivo.

Lo pagado se guarda ANTES de puntuar (I3): cada sesion se escribe con `estado = sin_puntuar`, su
`motivo`, `uso`, costo y propuestas; luego se puntua y se reescribe. Al reanudar:

* ninguna corrida guardada se vuelve a pagar, cualquiera sea su estado o motivo (una caida del
  proveedor queda como corrida con `motivo = error_de_proveedor`, no se reemplaza y el informe la
  lista aparte, fuera de las metricas);
* las que quedaron `sin_puntuar` o `fallo_al_puntuar` se puntuan de nuevo SIN pagar, desde sus
  propuestas guardadas (tambien con `repuntuar`); si alguna sigue fallando, se detiene con codigo
  5 ANTES de gastar mas;
* un fallo al puntuar durante la corrida guarda la corrida (con su costo) y detiene el proceso con
  codigo 5: el instrumento fallo y no se sigue pagando sin el.

La evaluacion y la medicion controlada exigen ademas que el auditor corra exactamente
`reglas_del_experimento` (I5) e `informe` exige el congelado vigente y las corridas completas (M4).
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from asistente.experimento.metricas import (  # noqa: E402
    ERROR_DE_PROVEEDOR,
    FALLO_AL_PUNTUAR,
    SIN_PUNTUAR,
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
#: El piloto (conjunto de desarrollo) NUNCA escribe en `CORRIDAS`: fuera de `resultados_asistente*`.
PILOTO = RAIZ / "docs" / "piloto_asistente_corridas.json"
CONTROLADO = RAIZ / "docs" / "resultados_asistente_controlado.json"
SALIDA = RAIZ / "docs" / "resultados_asistente.md"
Controlado = Mapping[str, tuple[int, int, tuple[float, float]]]
NO_DETECTABLE = "no detectable por diseno"
SIN_DETECTABLES = "sin errores detectables"
SIN_ESFUERZO = "-"  # el modelo local no tiene esfuerzo
POR_PUNTUAR = (SIN_PUNTUAR, FALLO_AL_PUNTUAR)
CABECERA = (
    "<!-- GENERADO por scripts/evaluar_asistente.py: no se edita a mano (RF-95). -->\n"
    "# Resultados del experimento del asistente (OE-H2)\n"
)


def porcentaje(valor: float | None) -> str:
    return "n/d" if valor is None else f"{valor * 100:.1f} %".replace(".", ",")


def intervalo(par: tuple[float, float]) -> str:
    return f"[{porcentaje(par[0])}; {porcentaje(par[1])}]"


def _ic_deteccion(r: Resumen) -> str:
    """El intervalo bootstrap, o «sin errores detectables» si no hubo ninguno (I4)."""
    return intervalo(r.intervalo_deteccion) if r.errores_detectables else SIN_DETECTABLES


def _estado(c: Corrida) -> str:
    return ERROR_DE_PROVEEDOR if c.motivo == ERROR_DE_PROVEEDOR else c.estado


def _orden_de_corrida(c: Corrida) -> tuple:
    return (c.tarea, c.modelo, c.condicion, c.repeticion)


def cumple(valor: float | None, umbral: float, *, minimo: bool) -> str:
    if valor is None:
        return "sin datos"
    bien = valor >= umbral if minimo else valor <= umbral
    return "cumple" if bien else "NO cumple (se declara la brecha)"


def generar_informe(
    corridas: Sequence[Corrida],
    protocolo: Mapping[str, object],
    controlado: Controlado,
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
    lineas.append(f"- esfuerzo del protocolo: `{protocolo.get('esfuerzo', 'n/d')}`")
    lineas += [
        "",
        "## Deteccion del auditor y falsas alarmas (por modelo y condicion)\n",
        "Solo cuentan las corridas normales; las excluidas (error del proveedor o sin puntuar) "
        "se listan aparte y su costo SI suma. Un error por par y tipo; las cascadas no se "
        "colapsan: la deteccion por fila (filas con algun error detectable y, de ellas, las "
        "citadas por algun hallazgo) lo compensa.\n",
        "| Modelo | Cond. | Corridas | Detectables | Detectados | Deteccion | IC 95 % "
        "(bootstrap por tarea) | Veredicto | Falsas alarmas | Veredicto | Propuestas "
        "validas | Exhaustividad | USD | Segundos | Filas con error | Filas detectadas | "
        "Deteccion por fila | Excluidas |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in resumenes:
        por_fila = r.filas_detectadas / r.filas_con_error if r.filas_con_error else None
        lineas.append(
            f"| {r.modelo} | {r.condicion} | {r.corridas} | {r.errores_detectables} | "
            f"{r.detectados} | {porcentaje(r.deteccion)} | {_ic_deteccion(r)} | "
            f"{cumple(r.deteccion, float(u['deteccion']), minimo=True)} | "
            f"{porcentaje(r.tasa_falsas_alarmas)} | "
            f"{cumple(r.tasa_falsas_alarmas, float(u['falsas_alarmas']), minimo=False)} | "
            f"{porcentaje(r.propuestas_validas)} | {porcentaje(r.exhaustividad)} | "
            f"{r.costo_usd:.2f} | {r.segundos:.0f} | {r.filas_con_error} | "
            f"{r.filas_detectadas} | {porcentaje(por_fila)} | {r.excluidas} |"
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
                celdas.append(f"{r.no_detectables_por_diseno[t]} ({NO_DETECTABLE})")
            else:
                celdas.append("-")
        lineas.append(f"| {r.modelo} | {r.condicion} | " + " | ".join(celdas) + " |")
    lineas += [
        "",
        "## Errores que escapan, rechazos y hallazgos inesperados\n",
        "| Modelo | Cond. | Escapan por tipo | Rechazos por causa | Rechazos del proveedor | "
        "Inesperados | Falsas alarmas |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in resumenes:
        lineas.append(
            f"| {r.modelo} | {r.condicion} | {_pares(r.escapan_por_tipo)} | "
            f"{_pares(r.rechazos_por_causa)} | {r.rechazos_del_proveedor} | "
            f"{r.inesperados} | {r.falsas_alarmas} |"
        )
    lineas += [
        "",
        "## Cifra por tarea: detectados / errores detectables\n",
        "| Modelo | Cond. | Tarea | Detectados | Errores |",
        "|---|---|---|---|---|",
    ]
    for r in resumenes:
        for tarea, (d, n) in sorted(r.por_tarea.items()):
            lineas.append(f"| {r.modelo} | {r.condicion} | {tarea} | {d} | {n} |")
    lineas += [
        "",
        "## Medicion controlada con mutaciones (Wilson 95 % sobre el n efectivo)\n",
        "El auditor es determinista: los mutantes repetidos se descartan, asi que el n efectivo "
        "por tipo (los ensayos) puede ser menor que el n pedido. Wilson usa el efectivo.\n",
        "| Tipo | Detectados | Ensayos (n efectivo) | Intervalo | n pedido | Nota |",
        "|---|---|---|---|---|---|",
    ]
    pedido = int(protocolo["n_por_tipo_de_mutacion"])
    for tipo, (d, n, par) in controlado.items():
        nota = NO_DETECTABLE if hipotesis.get(tipo, "?") is None else ""
        lineas.append(f"| {tipo} | {d} | {n} | {intervalo(par)} | {pedido} | {nota} |")
    excluidas = [c for c in corridas if not c.normal]
    lineas += [
        "",
        "## Corridas excluidas de las metricas (pagadas; se informan como estan)\n",
        "| Tarea | Modelo | Cond. | Rep. | Estado | Motivo de la sesion | Fallo | USD |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lineas += [
        f"| {c.tarea} | {c.modelo} | {c.condicion} | {c.repeticion} | {_estado(c)} | "
        f"{c.motivo or '-'} | {c.fallo or '-'} | {c.costo_usd:.2f} |"
        for c in sorted(excluidas, key=_orden_de_corrida)
    ] or ["| - | - | - | - | ninguna | - | - | - |"]
    lineas += [
        "",
        "## Todas las corridas\n",
        "| Tarea | Modelo | Cond. | Rep. | Estado | Errores | Detectados | Falsas alarmas | USD |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in sorted(corridas, key=_orden_de_corrida):
        lineas.append(
            f"| {c.tarea} | {c.modelo} | {c.condicion} | {c.repeticion} | {_estado(c)} | "
            f"{','.join(e.tipo for e in c.errores) or '-'} | {len(c.veredicto.detectados)} | "
            f"{c.veredicto.falsas_alarmas} | {c.costo_usd:.2f} |"
        )
    lineas += ["", f"Limites declarados: {protocolo['limites']}", ""]
    return "\n".join(lineas)


def _pares(cuenta: Mapping[str, int]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(cuenta.items())) or "-"


def _entradas(ruta: Path) -> list[dict]:
    """Las corridas guardadas tal cual (cada una con su `esfuerzo` si la hizo esta version)."""
    if not ruta.is_file():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


def _cargar_corridas(ruta: Path) -> list[Corrida]:
    return [corrida_de_dict(d) for d in _entradas(ruta)]


def corridas_de_evaluacion(ruta: Path, protocolo: Mapping[str, object]) -> list[Corrida]:
    """Las corridas del archivo si TODAS son de fichas de evaluacion y del esfuerzo del protocolo.

    `ValueError` con el motivo si el archivo mezcla el piloto (fichas de desarrollo) o corridas
    hechas con otro esfuerzo; un archivo sin esfuerzo declarado (anterior) no se rechaza por eso.
    """
    from asistente.experimento.banco import cargar_banco

    evaluacion = {f.id for f in cargar_banco().values() if f.conjunto == "evaluacion"}
    entradas = _entradas(ruta)
    ajenas = sorted({str(d["tarea"]) for d in entradas} - evaluacion)
    if ajenas:
        raise ValueError(f"{ruta.name} trae tareas que no son de evaluacion: {ajenas}")
    esfuerzo = str(protocolo.get("esfuerzo", ""))
    declarados = {str(d["esfuerzo"]) for d in entradas if "esfuerzo" in d}
    otros = sorted(declarados - {esfuerzo, SIN_ESFUERZO})
    if otros:
        raise ValueError(f"{ruta.name} trae corridas con otro esfuerzo ({otros}) que el protocolo")
    return [corrida_de_dict(d) for d in entradas]


def _guardar_corridas(ruta: Path, entradas: Sequence[Mapping[str, object]]) -> None:
    """Escritura atomica (`.tmp` y `os.replace`): una interrupcion no deja el archivo a medias."""
    contenido = json.dumps(list(entradas), indent=1, sort_keys=True) + "\n"
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(contenido, encoding="utf-8")
    os.replace(temporal, ruta)


def medicion_controlada(protocolo: Mapping[str, object]) -> Controlado:
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


@functools.cache
def _tope_de_sesion() -> Decimal:
    """El tope de costo por sesion que `correr` aplica por omision (`Topes.costo`)."""
    import inspect

    from asistente.experimento.ejecucion import correr

    return inspect.signature(correr).parameters["topes"].default.costo


def _gastado(entradas: Sequence[Mapping[str, object]]) -> Decimal:
    """Lo gastado segun el archivo: TODAS las corridas guardadas, de cualquier modelo y estado."""
    return sum((Decimal(str(d["costo_usd"])) for d in entradas), Decimal(0))


def _repuntuar_pendientes(entradas: list[dict], banco, catalogo, composiciones) -> list[str]:
    """Puntua SIN pagar las corridas `sin_puntuar` o `fallo_al_puntuar` (I3), desde sus propuestas
    guardadas; las reescribe en `entradas` (con su `esfuerzo`). Devuelve las que siguen fallando."""
    from asistente.experimento.ejecucion import puntuar

    siguen: list[str] = []
    for i, d in enumerate(entradas):
        if d.get("estado") not in POR_PUNTUAR:
            continue
        corrida = puntuar(
            corrida_de_dict(d), banco[d["tarea"]], catalogo=catalogo, composiciones=composiciones
        )
        entradas[i] = {**d, **corrida_a_dict(corrida)}
        if corrida.estado != "puntuada":
            siguen.append(f"{d['tarea']} rep {d['repeticion']}: {corrida.fallo}")
    return siguen


def _correr_real(
    args: argparse.Namespace, protocolo: Mapping[str, object], ruta: Path, esfuerzo: str
) -> int:
    from asistente.experimento.ejecucion import correr
    from asistente.tarifas import tarifa_de

    protocolo = {**protocolo, "esfuerzo": esfuerzo}
    banco, composiciones, catalogo, _, _ = contexto_del_experimento()
    entradas = _entradas(ruta)
    siguen = _repuntuar_pendientes(entradas, banco, catalogo, composiciones)
    if entradas:
        _guardar_corridas(ruta, entradas)
    if siguen:
        return _rechazo(
            "Corridas pagadas que siguen sin poder puntuarse; no se gasta mas:\n  "
            + "\n  ".join(siguen),
            5,
        )
    proveedor = proveedor_real(args.proveedor, protocolo, args.empresa)
    disponibilidad = proveedor.disponible()
    if not disponibilidad.disponible:
        print(disponibilidad.motivo, file=sys.stderr)
        return 3
    tarifa = tarifa_de(proveedor.modelo, local=args.proveedor == "ollama")
    usado = esfuerzo if args.proveedor == "claude" else SIN_ESFUERZO
    # ninguna corrida guardada se vuelve a pagar, sea cual sea su estado o motivo (I3)
    hechas = {
        (d["tarea"], d["modelo"], d["condicion"], d["repeticion"], d.get("esfuerzo"))
        for d in entradas
    }
    tope = Decimal(str(args.tope_usd))
    fichas = sorted((f for f in banco.values() if f.conjunto == args.conjunto), key=lambda f: f.id)
    for ficha in fichas:
        for repeticion in range(1, int(protocolo["repeticiones"]) + 1):
            if (ficha.id, proveedor.modelo, args.condicion, repeticion, usado) in hechas:
                continue
            gastado = _gastado(entradas)
            if gastado >= tope:
                print(
                    f"Tope de {tope} USD alcanzado (gastado {gastado:.2f} USD, todas las corridas "
                    f"del archivo): se detiene ANTES de la siguiente. El tope no corta una sesion "
                    f"a medias: el gasto pudo superarlo, como maximo, en el costo de una sesion "
                    f"(tope por sesion {_tope_de_sesion()} USD).",
                    file=sys.stderr,
                )
                return 4
            pagada: list[int] = []

            def al_pagar(c: Corrida, pagada: list[int] = pagada) -> None:
                entradas.append({**corrida_a_dict(c), "esfuerzo": usado})
                pagada.append(len(entradas) - 1)
                _guardar_corridas(ruta, entradas)  # el costo, ANTES de puntuar

            corrida = correr(
                ficha,
                proveedor,
                catalogo=catalogo,
                tarifa=tarifa,
                composiciones=composiciones,
                condicion=args.condicion,
                repeticion=repeticion,
                al_pagar=al_pagar,
            )
            entrada = {**corrida_a_dict(corrida), "esfuerzo": usado}
            if pagada:
                entradas[pagada[0]] = entrada
            else:
                entradas.append(entrada)
            _guardar_corridas(ruta, entradas)  # se guarda tras CADA corrida
            print(
                f"{ficha.id} rep {repeticion}: errores {[e.tipo for e in corrida.errores]}, "
                f"{corrida.costo_usd:.2f} USD (acumulado {_gastado(entradas):.2f}), "
                f"motivo {corrida.motivo or '-'}, {corrida.estado}"
            )
            if corrida.estado == FALLO_AL_PUNTUAR:
                return _rechazo(
                    f"Fallo al puntuar {ficha.id} rep {repeticion} ({corrida.fallo}): la corrida "
                    "quedo guardada con su costo; se detiene sin gastar mas. Al reanudar (o con "
                    "`repuntuar`) se puntua de nuevo sin pagar.",
                    5,
                )
            if corrida.motivo == ERROR_DE_PROVEEDOR:
                print(
                    f"{ficha.id} rep {repeticion}: error del proveedor; queda guardada como esta, "
                    "fuera de las metricas, y no se repite al reanudar.",
                    file=sys.stderr,
                )
    print(f"Fin: gastado {_gastado(entradas):.2f} USD en total en {ruta.name}.")
    return 0


def _rechazo(motivo: str, codigo: int) -> int:
    print(motivo, file=sys.stderr)
    return codigo


def faltantes_de_evaluacion(corridas: Sequence[Corrida], protocolo: Mapping[str, object]) -> list:
    """M4: lo que falta para que cada (modelo, condicion) presente tenga TODAS las tareas de
    evaluacion por `repeticiones`, y las corridas que siguen sin puntuar. Una corrida con error
    del proveedor cuenta como hecha (se informa como esta, fuera de las metricas)."""
    from asistente.experimento.banco import cargar_banco

    tareas = sorted(f.id for f in cargar_banco().values() if f.conjunto == "evaluacion")
    repeticiones = range(1, int(protocolo["repeticiones"]) + 1)
    hechas = {(c.modelo, c.condicion, c.tarea, c.repeticion) for c in corridas}
    grupos = sorted({(c.modelo, c.condicion) for c in corridas})
    faltan = [
        f"{m} {cond} {t} rep {r}"
        for m, cond in grupos
        for t in tareas
        for r in repeticiones
        if (m, cond, t, r) not in hechas
    ]
    faltan += [
        f"{c.modelo} {c.condicion} {c.tarea} rep {c.repeticion}: {c.estado} (use `repuntuar`)"
        for c in corridas
        if c.estado in POR_PUNTUAR
    ]
    return faltan


def _informe(args: argparse.Namespace, protocolo: Mapping[str, object]) -> int:
    from asistente.experimento import congelado

    faltan = []
    if not args.corridas.is_file():
        faltan.append(f"{args.corridas}: lo escribe `corrida --conjunto evaluacion` (T20)")
    if not CONTROLADO.is_file():
        faltan.append(f"{CONTROLADO}: lo escribe `mutaciones`, tras el congelado (T20)")
    if not CONGELADO.is_file():
        faltan.append(f"{CONGELADO}: lo escribe `asistente.experimento.congelado` (T20)")
    if faltan:
        return _rechazo("No se puede generar el informe; falta:\n  " + "\n  ".join(faltan), 3)
    cambios = congelado.verificar(CONGELADO)
    if cambios:
        return _rechazo("No se puede generar el informe: " + "; ".join(cambios), 3)
    try:
        corridas = corridas_de_evaluacion(args.corridas, protocolo)
    except ValueError as motivo:
        return _rechazo(f"No se puede generar el informe: {motivo}", 3)
    if not corridas:
        return _rechazo(f"No se puede generar el informe: {args.corridas} no trae corridas.", 3)
    incompletas = faltantes_de_evaluacion(corridas, protocolo)
    if incompletas:
        return _rechazo(
            "No se puede generar el informe: corridas incompletas:\n  " + "\n  ".join(incompletas),
            3,
        )
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


def reglas_desalineadas(protocolo: Mapping[str, object]) -> str | None:
    """I5: el auditor debe correr EXACTAMENTE `reglas_del_experimento`, en su orden, sobre cada
    referencia de evaluacion; `None` si es asi, o el motivo. No llama a ningun modelo."""
    from asistente.experimento.banco import borrador_de_partida
    from asistente.experimento.ejecucion import FECHA_R12, reglas_del_auditor

    banco, composiciones, _, _, referencia_de = contexto_del_experimento()
    esperadas = tuple(protocolo["reglas_del_experimento"])
    for ficha in sorted(
        (f for f in banco.values() if f.conjunto == "evaluacion"), key=lambda f: f.id
    ):
        referencia = referencia_de(ficha)
        borrador = replace(
            borrador_de_partida(ficha, FECHA_R12),
            composiciones=composiciones,
            espacio=referencia.espacio,
            items_base=referencia.items,
        )
        corren = reglas_del_auditor(borrador)
        if corren != esperadas:
            return (
                f"el auditor corre {list(corren)} en {ficha.id} y el protocolo fija "
                f"{list(esperadas)}"
            )
    return None


def _validar_corrida(args: argparse.Namespace, protocolo: Mapping[str, object]) -> int | None:
    """Los rechazos de la corrida real ANTES de pedir la clave o tocar la red; `None` si pasa."""
    from asistente.experimento import congelado

    if not math.isfinite(args.tope_usd) or args.tope_usd <= 0:
        return _rechazo("--tope-usd debe ser un numero finito mayor que cero.", 2)
    if args.conjunto == "evaluacion":
        if args.esfuerzo and args.esfuerzo != protocolo["esfuerzo"]:
            return _rechazo("La evaluacion usa el esfuerzo del protocolo congelado.", 2)
        cambios = congelado.verificar()
        if cambios:
            return _rechazo("La evaluacion exige el protocolo congelado: " + "; ".join(cambios), 2)
        desalineadas = reglas_desalineadas(protocolo)
        if desalineadas:
            return _rechazo(f"La evaluacion exige las reglas del protocolo: {desalineadas}", 2)
    elif args.corridas.resolve() == CORRIDAS.resolve():
        return _rechazo(f"El piloto no escribe en {CORRIDAS.name}: es el de la evaluacion.", 2)
    return None


def _repuntuar(args: argparse.Namespace, protocolo: Mapping[str, object]) -> int:
    """Puntua sin pagar las corridas guardadas sin puntuar o con fallo al puntuar (I3)."""
    from asistente.experimento import congelado

    entradas = _entradas(args.corridas)
    if not entradas:
        return _rechazo(f"{args.corridas} no trae corridas.", 3)
    banco, composiciones, catalogo, _, _ = contexto_del_experimento()
    evaluacion = {f.id for f in banco.values() if f.conjunto == "evaluacion"}
    if any(d["tarea"] in evaluacion for d in entradas):  # se puntua con el auditor congelado
        cambios = congelado.verificar()
        if cambios:
            return _rechazo("Puntuar la evaluacion exige el congelado: " + "; ".join(cambios), 2)
        desalineadas = reglas_desalineadas(protocolo)
        if desalineadas:
            return _rechazo(f"Puntuar la evaluacion exige sus reglas: {desalineadas}", 2)
    siguen = _repuntuar_pendientes(entradas, banco, catalogo, composiciones)
    _guardar_corridas(args.corridas, entradas)
    if siguen:
        return _rechazo("Siguen sin poder puntuarse:\n  " + "\n  ".join(siguen), 5)
    print(f"{args.corridas}: todas las corridas pagadas estan puntuadas (sin gastar nada).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="orden", required=True)
    informe = sub.add_parser("informe")
    informe.add_argument("--corridas", type=Path, default=CORRIDAS)
    informe.add_argument("--salida", type=Path, default=SALIDA)
    mutaciones = sub.add_parser("mutaciones")
    mutaciones.add_argument("--salida", type=Path, default=CONTROLADO)
    repuntuar = sub.add_parser("repuntuar")
    repuntuar.add_argument("--corridas", type=Path, required=True)
    real = sub.add_parser("corrida")
    real.add_argument("--proveedor", choices=("claude", "ollama"), required=True)
    real.add_argument("--conjunto", choices=("desarrollo", "evaluacion"), required=True)
    real.add_argument("--condicion", choices=("A", "B"), default="A")
    real.add_argument("--esfuerzo", choices=("low", "medium", "high", "xhigh", "max"))
    real.add_argument("--empresa", default="EMPRESA-PROPIA")
    real.add_argument(
        "--tope-usd",
        type=float,
        required=True,
        help="finito y mayor que cero (con Ollama, cuyo costo es 0, basta 1); se comprueba (>=) "
        "antes de cada corrida contra TODO lo gastado en el archivo y no corta una sesion a "
        "medias: el gasto puede superarlo, como maximo, en el costo de una sesion (tope por "
        f"sesion {_tope_de_sesion()} USD)",
    )
    real.add_argument(
        "--corridas",
        type=Path,
        default=None,
        help="archivo de corridas; por omision, el piloto (desarrollo) o el de la evaluacion",
    )
    real.add_argument("--acepto-costo", action="store_true")
    args = parser.parse_args(argv)
    if args.orden == "corrida" and not args.acepto_costo:
        return _rechazo(
            "Falta --acepto-costo: la corrida real gasta dinero y la autoriza una persona.", 2
        )
    protocolo = json.loads(PROTOCOLO.read_text(encoding="utf-8"))
    if args.orden == "mutaciones":
        from asistente.experimento import congelado

        cambios = congelado.verificar()
        if cambios:  # la medicion sobre evaluacion se hace con el protocolo ya congelado
            return _rechazo("La medicion controlada exige el congelado: " + "; ".join(cambios), 2)
        desalineadas = reglas_desalineadas(protocolo)
        if desalineadas:
            return _rechazo(f"La medicion controlada exige sus reglas: {desalineadas}", 2)
        controlado = medicion_controlada(protocolo)
        args.salida.write_text(
            json.dumps(controlado, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        detalle = ", ".join(f"{t} {d}/{n}" for t, (d, n, _) in controlado.items())
        print(f"{args.salida} (detectados/n efectivo): {detalle}")
        return 0
    if args.orden == "repuntuar":
        return _repuntuar(args, protocolo)
    if args.orden == "corrida":
        if args.corridas is None:
            args.corridas = CORRIDAS if args.conjunto == "evaluacion" else PILOTO
        rechazo = _validar_corrida(args, protocolo)
        if rechazo is not None:
            return rechazo
        esfuerzo = args.esfuerzo or str(protocolo["esfuerzo"])
        return _correr_real(args, protocolo, args.corridas, esfuerzo)
    return _informe(args, protocolo)


if __name__ == "__main__":
    sys.exit(main())
