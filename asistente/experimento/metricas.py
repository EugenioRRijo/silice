"""Metricas del experimento (S4 §9.5): definiciones congeladas con el protocolo.

* Deteccion del auditor: errores (de los tipos que el protocolo declara detectables) con al menos un
  hallazgo NO esperado que cite su fila o su item, entre esos errores. Total y por tipo, con
  intervalo de BOOTSTRAP AGRUPADO POR TAREA (las 3 repeticiones de una tarea no son independientes).
* Falsas alarmas: hallazgos no esperados sin ninguna fila con error, entre los no esperados.
* Errores que escapan: los que quedaron sin hallazgo, por tipo; los «no detectables por diseno» se
  informan aparte con su numero.
* Propuestas validas: llamadas de propuesta que pasan las cuatro capas al primer intento.
* Medicion controlada con mutaciones: intervalo de WILSON al 95 % por tipo (ensayos separados).
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from decimal import Decimal

from asistente.experimento.comparador import Error, Veredicto

TIPOS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")
Z_95 = 1.959963984540054


@dataclass(frozen=True, slots=True)
class Corrida:
    tarea: str
    modelo: str
    condicion: str  # `A` (sin retroalimentacion) | `B` (con informe)
    repeticion: int
    errores: tuple[Error, ...]
    veredicto: Veredicto
    llamadas_de_propuesta: int = 0
    validas_al_primer_intento: int = 0
    rechazos: Mapping[str, int] = field(default_factory=dict)
    elementos_de_referencia: int = 0
    elementos_presentes: int = 0
    costo_usd: Decimal = Decimal(0)
    segundos: float = 0.0
    rechazo_del_proveedor: bool = False


def detectable(tipo: str, hipotesis: Mapping[str, Sequence[str] | None]) -> bool:
    return hipotesis.get(tipo) is not None


def percentil(ordenados: Sequence[float], p: float) -> float:
    """Percentil por rango mas cercano: el elemento ceil(p/100 * n), contando desde 1."""
    return ordenados[max(math.ceil(p / 100 * len(ordenados)) - 1, 0)]


def wilson(aciertos: int, ensayos: int, z: float = Z_95) -> tuple[float, float]:
    """Intervalo de Wilson para una proporcion; (0, 1) si no hay ensayos."""
    if ensayos == 0:
        return 0.0, 1.0
    p = aciertos / ensayos
    z2 = z * z
    centro = (p + z2 / (2 * ensayos)) / (1 + z2 / ensayos)
    mitad = z * math.sqrt(p * (1 - p) / ensayos + z2 / (4 * ensayos**2)) / (1 + z2 / ensayos)
    return max(centro - mitad, 0.0), min(centro + mitad, 1.0)


def bootstrap_agrupado(
    por_tarea: Mapping[str, tuple[int, int]], semilla: int, replicas: int = 10_000
) -> tuple[float, float]:
    """Percentiles 2,5 y 97,5 de la razon aciertos/total remuestreando TAREAS completas.

    `por_tarea` = {tarea: (aciertos, total)} con todas las repeticiones de la tarea ya sumadas.
    Semilla fija en el protocolo. Una replica sin total (todas las tareas sin errores) se omite.
    """
    tareas = sorted(por_tarea)
    if not tareas:
        return 0.0, 1.0
    azar = random.Random(semilla)
    razones: list[float] = []
    for _ in range(replicas):
        elegidas = azar.choices(tareas, k=len(tareas))
        aciertos = sum(por_tarea[t][0] for t in elegidas)
        total = sum(por_tarea[t][1] for t in elegidas)
        if total:
            razones.append(aciertos / total)
    razones.sort()
    return percentil(razones, 2.5), percentil(razones, 97.5)


@dataclass(frozen=True, slots=True)
class Resumen:
    modelo: str
    condicion: str
    corridas: int
    errores_detectables: int
    detectados: int
    deteccion: float | None
    intervalo_deteccion: tuple[float, float]
    por_tipo: Mapping[str, tuple[int, int]]  # tipo -> (detectados, errores)
    escapan_por_tipo: Mapping[str, int]
    no_detectables_por_diseno: Mapping[str, int]
    inesperados: int
    falsas_alarmas: int
    tasa_falsas_alarmas: float | None
    propuestas_validas: float | None
    rechazos_por_causa: Mapping[str, int]
    exhaustividad: float | None
    costo_usd: Decimal
    segundos: float
    rechazos_del_proveedor: int
    por_tarea: Mapping[str, tuple[int, int]]


def _razon(a: int, b: int) -> float | None:
    return a / b if b else None


def resumir(
    corridas: Sequence[Corrida],
    hipotesis: Mapping[str, Sequence[str] | None],
    semilla: int,
    replicas: int = 10_000,
) -> Resumen:
    """Las metricas de §9.5 para las corridas de UN modelo en UNA condicion."""
    det = defaultdict(lambda: [0, 0])
    no_det: Counter[str] = Counter()
    escapan: Counter[str] = Counter()
    por_tarea: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for c in corridas:
        detectados = set(c.veredicto.detectados)
        for e in c.errores:
            if not detectable(e.tipo, hipotesis):
                no_det[e.tipo] += 1
                continue
            det[e.tipo][1] += 1
            por_tarea[c.tarea][1] += 1
            if e in detectados:
                det[e.tipo][0] += 1
                por_tarea[c.tarea][0] += 1
            else:
                escapan[e.tipo] += 1
    detectables = sum(v[1] for v in det.values())
    acertados = sum(v[0] for v in det.values())
    inesperados = sum(c.veredicto.inesperados for c in corridas)
    falsas = sum(c.veredicto.falsas_alarmas for c in corridas)
    propuestas = sum(c.llamadas_de_propuesta for c in corridas)
    rechazos: Counter[str] = Counter()
    for c in corridas:
        rechazos.update(c.rechazos)
    tareas = {t: (v[0], v[1]) for t, v in por_tarea.items()}
    return Resumen(
        modelo=corridas[0].modelo if corridas else "",
        condicion=corridas[0].condicion if corridas else "",
        corridas=len(corridas),
        errores_detectables=detectables,
        detectados=acertados,
        deteccion=_razon(acertados, detectables),
        intervalo_deteccion=bootstrap_agrupado(tareas, semilla, replicas),
        por_tipo={t: (det[t][0], det[t][1]) for t in TIPOS if det[t][1]},
        escapan_por_tipo=dict(escapan),
        no_detectables_por_diseno=dict(no_det),
        inesperados=inesperados,
        falsas_alarmas=falsas,
        tasa_falsas_alarmas=_razon(falsas, inesperados),
        propuestas_validas=_razon(sum(c.validas_al_primer_intento for c in corridas), propuestas),
        rechazos_por_causa=dict(rechazos),
        exhaustividad=_razon(
            sum(c.elementos_presentes for c in corridas),
            sum(c.elementos_de_referencia for c in corridas),
        ),
        costo_usd=sum((c.costo_usd for c in corridas), Decimal(0)),
        segundos=sum(c.segundos for c in corridas),
        rechazos_del_proveedor=sum(c.rechazo_del_proveedor for c in corridas),
        por_tarea=tareas,
    )


def deteccion_controlada(
    resultados: Sequence[tuple[str, bool]],
) -> dict[str, tuple[int, int, tuple[float, float]]]:
    """Medicion con mutaciones: por tipo (detectados, ensayos, Wilson al 95 %)."""
    cuenta: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for tipo, detectado in resultados:
        cuenta[tipo][1] += 1
        cuenta[tipo][0] += int(detectado)
    return {t: (v[0], v[1], wilson(v[0], v[1])) for t, v in sorted(cuenta.items())}


def corrida_a_dict(c: Corrida) -> dict[str, object]:
    """La corrida como JSON (se informan TODAS las corridas, §9.5)."""
    return {
        "tarea": c.tarea,
        "modelo": c.modelo,
        "condicion": c.condicion,
        "repeticion": c.repeticion,
        "errores": [asdict(e) for e in c.errores],
        "detectados": [asdict(e) for e in c.veredicto.detectados],
        "escapan": [asdict(e) for e in c.veredicto.escapan],
        "inesperados": c.veredicto.inesperados,
        "falsas_alarmas": c.veredicto.falsas_alarmas,
        "llamadas_de_propuesta": c.llamadas_de_propuesta,
        "validas_al_primer_intento": c.validas_al_primer_intento,
        "rechazos": dict(c.rechazos),
        "elementos_de_referencia": c.elementos_de_referencia,
        "elementos_presentes": c.elementos_presentes,
        "costo_usd": str(c.costo_usd),
        "segundos": c.segundos,
        "rechazo_del_proveedor": c.rechazo_del_proveedor,
    }


def corrida_de_dict(d: Mapping[str, object]) -> Corrida:
    def errores(clave: str) -> tuple[Error, ...]:
        return tuple(Error(**e) for e in d[clave])  # type: ignore[union-attr]

    return Corrida(
        tarea=str(d["tarea"]),
        modelo=str(d["modelo"]),
        condicion=str(d["condicion"]),
        repeticion=int(d["repeticion"]),  # type: ignore[arg-type]
        errores=errores("errores"),
        veredicto=Veredicto(
            errores("detectados"),
            errores("escapan"),
            int(d["inesperados"]),  # type: ignore[arg-type]
            int(d["falsas_alarmas"]),  # type: ignore[arg-type]
        ),
        llamadas_de_propuesta=int(d["llamadas_de_propuesta"]),  # type: ignore[arg-type]
        validas_al_primer_intento=int(d["validas_al_primer_intento"]),  # type: ignore[arg-type]
        rechazos=dict(d["rechazos"]),  # type: ignore[arg-type]
        elementos_de_referencia=int(d["elementos_de_referencia"]),  # type: ignore[arg-type]
        elementos_presentes=int(d["elementos_presentes"]),  # type: ignore[arg-type]
        costo_usd=Decimal(str(d["costo_usd"])),
        segundos=float(d["segundos"]),  # type: ignore[arg-type]
        rechazo_del_proveedor=bool(d["rechazo_del_proveedor"]),
    )
