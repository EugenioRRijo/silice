"""Metricas del experimento (S4 §9.5): definiciones congeladas con el protocolo.

* Deteccion del auditor: errores (de los tipos que el protocolo declara detectables) con al menos un
  hallazgo NO esperado que cite su fila o su item, entre esos errores. Total y por tipo, con
  intervalo de BOOTSTRAP AGRUPADO POR TAREA (las 3 repeticiones de una tarea no son independientes).
* Falsas alarmas: hallazgos no esperados sin ninguna fila con error, entre los no esperados.
* Errores que escapan: los que quedaron sin hallazgo, por tipo; los «no detectables por diseno» se
  informan aparte con su numero.
* Propuestas validas: llamadas de propuesta que pasan las cuatro capas al primer intento.
* Medicion controlada con mutaciones: intervalo de WILSON al 95 % por tipo (ensayos separados).
* Deteccion POR FILA (I1): ademas de por error, filas del borrador con algun error detectable y, de
  ellas, las que algun hallazgo cita (las cascadas no se colapsan: la cifra por fila lo compensa).

Solo cuentan las corridas NORMALES (`Corrida.normal`): puntuadas, no reemplazadas y sin
`error_de_proveedor`; las demas se informan aparte, con su costo (I3).
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
#: estado de una corrida guardada (I3): se paga, se guarda, y DESPUES se puntua
PUNTUADA = "puntuada"
SIN_PUNTUAR = "sin_puntuar"  # pagada y guardada; la puntuacion no llego a terminar
FALLO_AL_PUNTUAR = "fallo_al_puntuar"  # pagada; `aplicar`, `comparar` o el auditor fallaron
ERROR_DE_PROVEEDOR = "error_de_proveedor"  # `MotivoFin.ERROR_DE_PROVEEDOR`


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
    #: lo que se pago, para reauditar sin volver a pagar (I3)
    motivo: str = ""  # `MotivoFin` de la sesion
    uso: Mapping[str, int] = field(default_factory=dict)  # fichas: entrada, salida, cache...
    proveedor: str = ""  # `ProveedorIA.nombre` (va en el origen de las filas del modelo)
    #: las propuestas de la sesion, serializadas: con la ficha reconstruyen el borrador final
    propuestas: tuple[Mapping[str, object], ...] = ()
    estado: str = PUNTUADA
    fallo: str = ""  # el error al puntuar, si lo hubo

    @property
    def normal(self) -> bool:
        """Cuenta en las metricas: puntuada y sin error del proveedor (I3)."""
        return self.estado == PUNTUADA and self.motivo != ERROR_DE_PROVEEDOR


def fila_del_error(e: Error) -> str:
    """La fila del borrador que el error senala; la de la referencia si no hay (E6)."""
    return e.clave_borrador if e.clave_borrador else f"referencia:{e.clave_referencia}"


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
    bajo = 0.0 if aciertos == 0 else max(centro - mitad, 0.0)
    alto = 1.0 if aciertos == ensayos else min(centro + mitad, 1.0)
    return bajo, alto


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
    if not razones:  # ningun error detectable en ninguna tarea (I4): el informe lo dice
        return 0.0, 1.0
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
    #: I1: filas con algun error detectable y, de ellas, las citadas por algun hallazgo
    filas_con_error: int = 0
    filas_detectadas: int = 0
    #: corridas pagadas que no cuentan en las metricas (I3): error del proveedor o sin puntuar
    excluidas: int = 0


def _razon(a: int, b: int) -> float | None:
    return a / b if b else None


def resumir(
    corridas: Sequence[Corrida],
    hipotesis: Mapping[str, Sequence[str] | None],
    semilla: int,
    replicas: int = 10_000,
) -> Resumen:
    """Las metricas de §9.5 para las corridas NORMALES de UN modelo en UNA condicion.

    Las que no son normales (`Corrida.normal`) no cuentan en las metricas (se cuentan en
    `excluidas` y el informe las lista aparte), pero su costo y su tiempo SI suman: se pagaron."""
    todas = list(corridas)
    corridas = [c for c in todas if c.normal]
    det = defaultdict(lambda: [0, 0])
    filas = [0, 0]
    no_det: Counter[str] = Counter()
    escapan: Counter[str] = Counter()
    por_tarea: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for c in corridas:
        detectados = set(c.veredicto.detectados)
        # TODAS las tareas se remuestrean (§9.5), tengan o no errores detectables
        por_tarea.setdefault(c.tarea, [0, 0])
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
        con_error = {fila_del_error(e) for e in c.errores if detectable(e.tipo, hipotesis)}
        filas[0] += len(con_error)
        filas[1] += len(
            con_error & {fila_del_error(e) for e in detectados}
        )  # por fila: todo o nada
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
        modelo=todas[0].modelo if todas else "",
        condicion=todas[0].condicion if todas else "",
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
        costo_usd=sum((c.costo_usd for c in todas), Decimal(0)),
        segundos=sum(c.segundos for c in todas),
        rechazos_del_proveedor=sum(c.rechazo_del_proveedor for c in corridas),
        por_tarea=tareas,
        filas_con_error=filas[0],
        filas_detectadas=filas[1],
        excluidas=len(todas) - len(corridas),
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
        "motivo": c.motivo,
        "uso": dict(c.uso),
        "proveedor": c.proveedor,
        "propuestas": [dict(p) for p in c.propuestas],
        "estado": c.estado,
        "fallo": c.fallo,
    }


def corrida_de_dict(d: Mapping[str, object]) -> Corrida:
    """Inversa de `corrida_a_dict`; un archivo anterior, sin los campos de I3, se lee igual
    (esas corridas quedan `puntuada`, sin motivo, uso ni propuestas)."""

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
        motivo=str(d.get("motivo", "")),
        uso={str(k): int(v) for k, v in dict(d.get("uso") or {}).items()},  # type: ignore[arg-type]
        proveedor=str(d.get("proveedor", "")),
        propuestas=tuple(dict(p) for p in d.get("propuestas") or ()),  # type: ignore[union-attr]
        estado=str(d.get("estado", PUNTUADA)),
        fallo=str(d.get("fallo", "")),
    )
