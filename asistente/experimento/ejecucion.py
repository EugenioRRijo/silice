"""Una corrida del experimento (S4 §9.4): una tarea, un modelo, una condicion, una repeticion.

Se acepta TODA propuesta valida tal cual (aceptacion automatica declarada: mide al modelo, no a la
persona), se elabora y audita el borrador resultante con las reglas del protocolo, y se compara con
la referencia. Las respuestas a las preguntas del modelo las da la regla automatica de la ficha
(§9.2): el experimentador no elige ni redacta. Nunca toca `data/apu.db`.

Lo que se paga se guarda ANTES de puntuar (I3): `correr` entrega a `al_pagar` la corrida pagada
(`estado = sin_puntuar`) con el motivo de la sesion, el uso, el costo y las propuestas serializadas,
y solo despues puntua. `puntuar` reconstruye el borrador final desde esas propuestas y la ficha, sin
volver a llamar al modelo; si `aplicar`, `comparar` o el auditor fallan, devuelve la corrida con
`estado = fallo_al_puntuar` y el error, con su costo (nunca la pierde).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal

from asistente.catalogo import CatalogoVista
from asistente.experimento.banco import (
    Ficha,
    borrador_de_partida,
    referencia_de,
    respuesta_preparada,
)
from asistente.experimento.comparador import Veredicto, comparar, evaluar_hallazgos
from asistente.experimento.metricas import (
    FALLO_AL_PUNTUAR,
    PUNTUADA,
    SIN_PUNTUAR,
    Corrida,
)
from asistente.experimento.modelo import Referencia, protocolo
from asistente.orquestador import MotivoFin, Servicios, Topes, ejecutar
from asistente.propuestas import EstadoPropuesta, OrigenIA, Propuesta, TipoPropuesta, aplicar
from asistente.proveedores.base import ProveedorIA, Tarifa
from core.contracts import Hallazgo
from core.verification.informe import InformeAuditoria
from ui import hoja
from ui.hoja import Borrador

Auditor = Callable[[Borrador], tuple[Hallazgo, ...]]
#: R12 se evalua en la fecha FIJA del protocolo, no en la del dia de la corrida (§9.1, M2)
FECHA_R12 = date.fromisoformat(protocolo()["fecha_de_evaluacion_r12"])


def auditor_de_la_hoja(borrador: Borrador) -> tuple[Hallazgo, ...]:
    """Los hallazgos de las reglas que corre la hoja: R1-R10 y R15 (plano), que son las de
    `protocolo.json::reglas_del_experimento` (maestro §3.3, columna «Experimento de S4»), mas
    los `PENDIENTE` que declara la elaboracion (`protocolo.json::hallazgos_de_la_elaboracion`,
    M1). S1 y S3 agregan R11 y R12 con la fecha FIJA del protocolo. Reevaluacion en memoria."""
    return hoja.elaborar_borrador(borrador).elaboracion.informe.hallazgos


def reglas_del_auditor(borrador: Borrador) -> tuple[str, ...]:
    """Los codigos de las reglas que corre `auditor_de_la_hoja`, en su orden.

    El protocolo fija el conjunto exacto de reglas del experimento (`reglas_del_experimento`,
    maestro §3.3); `scripts/evaluar_asistente.py` lo exige antes de gastar en la evaluacion.
    """
    informe = hoja.elaborar_borrador(borrador).elaboracion.informe
    return tuple(codigo for codigo, _ in informe.reglas_evaluadas)


def propuesta_a_dict(p: Propuesta) -> dict[str, object]:
    """La propuesta como JSON: con la ficha basta para reconstruir el borrador final (I3)."""
    return {
        "id": p.id,
        "tipo": p.tipo.value,
        "filas": [dict(f) for f in p.filas],
        "citas": [list(c) for c in p.citas],
        "supuestos": [list(s) for s in p.supuestos],
        "estado": p.estado.value,
        "declarado": p.declarado,
    }


def propuesta_de_dict(d: Mapping[str, object]) -> Propuesta:
    return Propuesta(
        id=str(d["id"]),
        tipo=TipoPropuesta(d["tipo"]),
        filas=tuple(dict(f) for f in d["filas"]),  # type: ignore[union-attr]
        citas=tuple((str(a), str(b)) for a, b in d["citas"]),  # type: ignore[union-attr]
        supuestos=tuple((str(a), str(b)) for a, b in d["supuestos"]),  # type: ignore[union-attr]
        estado=EstadoPropuesta(d["estado"]),
        declarado=bool(d["declarado"]),
    )


def correr(
    ficha: Ficha,
    proveedor: ProveedorIA,
    *,
    catalogo: CatalogoVista,
    tarifa: Tarifa,
    composiciones,
    condicion: str = "A",
    repeticion: int = 1,
    fecha: date = FECHA_R12,
    topes: Topes = Topes(costo=Decimal(5)),  # noqa: B008
    auditor: Auditor = auditor_de_la_hoja,
    al_pagar: Callable[[Corrida], None] | None = None,
) -> Corrida:
    """La sesion con el modelo, guardada por `al_pagar` ANTES de puntuar, y luego puntuada."""
    partida = replace(borrador_de_partida(ficha, fecha), composiciones=composiciones)
    servicios = Servicios(
        catalogo=catalogo,
        tarifa=tarifa,
        auditar=lambda b: InformeAuditoria("HOJA", hallazgos=auditor(b)),
        responder=lambda pregunta: respuesta_preparada(ficha, pregunta),
        informe_permitido=condicion == "B",
    )
    inicio = time.monotonic()
    sesion = ejecutar(proveedor, ficha.pedido, partida, servicios, topes, sesion_n=repeticion)
    segundos = time.monotonic() - inicio
    pagada = Corrida(
        tarea=ficha.id,
        modelo=proveedor.modelo,
        condicion=condicion,
        repeticion=repeticion,
        errores=(),
        veredicto=Veredicto((), (), 0, 0),
        llamadas_de_propuesta=sesion.llamadas_de_propuesta,
        validas_al_primer_intento=sesion.propuestas_validas,
        rechazos=dict(sesion.rechazos_por_causa),
        costo_usd=sesion.costo,
        segundos=segundos,
        rechazo_del_proveedor=sesion.motivo is MotivoFin.REHUSADO,
        motivo=sesion.motivo.value,
        uso=asdict(sesion.uso),
        proveedor=proveedor.nombre,
        propuestas=tuple(propuesta_a_dict(p) for p in sesion.propuestas),
        estado=SIN_PUNTUAR,
    )
    if al_pagar is not None:
        al_pagar(pagada)  # lo pagado queda guardado aunque la puntuacion falle o se corte
    return puntuar(
        pagada, ficha, catalogo=catalogo, composiciones=composiciones, fecha=fecha, auditor=auditor
    )


def puntuar(
    pagada: Corrida,
    ficha: Ficha,
    *,
    catalogo: CatalogoVista,
    composiciones,
    fecha: date = FECHA_R12,
    auditor: Auditor = auditor_de_la_hoja,
) -> Corrida:
    """Puntua una corrida ya pagada SIN volver a llamar al modelo (tambien al reanudar).

    Acepta tal cual las propuestas que la sesion dejo pendientes, reconstruye el borrador final,
    lo compara con la referencia y lo audita. Nunca lanza por un fallo de la puntuacion: devuelve
    la corrida con `estado = fallo_al_puntuar` y el error, y con su costo.
    """
    try:
        partida = replace(borrador_de_partida(ficha, fecha), composiciones=composiciones)
        aceptadas = [
            replace(propuesta_de_dict(d), estado=EstadoPropuesta.ACEPTADA)
            for d in pagada.propuestas
            if d["estado"] == EstadoPropuesta.PENDIENTE.value
        ]
        origen = OrigenIA(pagada.proveedor, pagada.modelo, pagada.repeticion)
        final = aplicar(partida, aceptadas, origen, catalogo)
        referencia = referencia_de(ficha)
        comparacion = comparar(referencia, final.espacio, final.items_base)
        veredicto = _veredicto(comparacion, final, referencia, partida, auditor)
    except Exception as error:  # noqa: BLE001 - se guarda la corrida pagada con el fallo
        return replace(pagada, estado=FALLO_AL_PUNTUAR, fallo=f"{type(error).__name__}: {error}")
    total = _elementos(referencia)
    return replace(
        pagada,
        errores=comparacion.errores,
        veredicto=veredicto,
        elementos_de_referencia=total,
        elementos_presentes=total - sum(1 for e in comparacion.errores if e.tipo == "E6"),
        estado=PUNTUADA,
        fallo="",
    )


def _elementos(r: Referencia) -> int:
    e = r.espacio
    return len(e.ambientes) + len(e.fuentes) + len(e.puntos) + len(e.recorridos) + len(r.items)


def _veredicto(comparacion, final, referencia, partida, auditor) -> Veredicto:
    de_referencia = replace(partida, espacio=referencia.espacio, items_base=referencia.items)
    return evaluar_hallazgos(comparacion, auditor(final), auditor(de_referencia))


def medir_mutantes(
    mutantes,
    referencias: Mapping[str, Referencia],
    *,
    composiciones,
    fecha: date = FECHA_R12,
    auditor: Auditor = auditor_de_la_hoja,
) -> list[tuple[str, bool]]:
    """Medicion controlada (§9.5): por cada mutante, (tipo, si el auditor detecto ESE tipo).

    Cada mutante se elabora y audita igual que una corrida; los hallazgos que da la propia
    referencia no cuentan.
    """
    resultados: list[tuple[str, bool]] = []
    for m in mutantes:
        referencia = referencias[m.tarea]
        base = Borrador(fecha=fecha, composiciones=composiciones)
        comparacion = comparar(referencia, m.espacio, m.items)
        veredicto = evaluar_hallazgos(
            comparacion,
            auditor(replace(base, espacio=m.espacio, items_base=m.items)),
            auditor(replace(base, espacio=referencia.espacio, items_base=referencia.items)),
        )
        resultados.append((m.tipo, any(e.tipo == m.tipo for e in veredicto.detectados)))
    return resultados
