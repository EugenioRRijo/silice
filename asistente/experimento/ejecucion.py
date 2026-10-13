"""Una corrida del experimento (S4 §9.4): una tarea, un modelo, una condicion, una repeticion.

Se acepta TODA propuesta valida tal cual (aceptacion automatica declarada: mide al modelo, no a la
persona), se elabora y audita el borrador resultante con las reglas del protocolo, y se compara con
la referencia. Las respuestas a las preguntas del modelo las da la regla automatica de la ficha
(§9.2): el experimentador no elige ni redacta. Nunca toca `data/apu.db`.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import replace
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
from asistente.experimento.metricas import Corrida
from asistente.experimento.modelo import Referencia
from asistente.orquestador import MotivoFin, Servicios, Topes, ejecutar
from asistente.propuestas import EstadoPropuesta, OrigenIA, aplicar
from asistente.proveedores.base import ProveedorIA, Tarifa
from core.contracts import Hallazgo
from core.verification.informe import InformeAuditoria
from ui import hoja
from ui.hoja import Borrador

Auditor = Callable[[Borrador], tuple[Hallazgo, ...]]


def auditor_de_la_hoja(borrador: Borrador) -> tuple[Hallazgo, ...]:
    """Los hallazgos de las reglas que corre la hoja: R1-R10 y R15 (plano), que son las de
    `protocolo.json::reglas_del_experimento` (maestro §3.3, columna «Experimento de S4»).
    S1 y S3 agregan R11 y R12 con la fecha FIJA del protocolo. La reevaluacion es en memoria."""
    return hoja.elaborar_borrador(borrador).elaboracion.informe.hallazgos


def reglas_del_auditor(borrador: Borrador) -> tuple[str, ...]:
    """Los codigos de las reglas que corre `auditor_de_la_hoja`, en su orden.

    El protocolo fija el conjunto exacto de reglas del experimento (`reglas_del_experimento`,
    maestro §3.3); una prueba exige que sean estas, sin filtro.
    """
    informe = hoja.elaborar_borrador(borrador).elaboracion.informe
    return tuple(codigo for codigo, _ in informe.reglas_evaluadas)


def correr(
    ficha: Ficha,
    proveedor: ProveedorIA,
    *,
    catalogo: CatalogoVista,
    tarifa: Tarifa,
    composiciones,
    condicion: str = "A",
    repeticion: int = 1,
    fecha: date = date(2026, 10, 31),
    topes: Topes = Topes(costo=Decimal(5)),  # noqa: B008
    auditor: Auditor = auditor_de_la_hoja,
) -> Corrida:
    partida = replace(borrador_de_partida(ficha, fecha), composiciones=composiciones)
    servicios = Servicios(
        catalogo=catalogo,
        tarifa=tarifa,
        auditar=lambda b: InformeAuditoria(hallazgos=auditor(b)),
        responder=lambda pregunta: respuesta_preparada(ficha, pregunta),
        informe_permitido=condicion == "B",
    )
    inicio = time.monotonic()
    sesion = ejecutar(proveedor, ficha.pedido, partida, servicios, topes, sesion_n=repeticion)
    segundos = time.monotonic() - inicio
    aceptadas = [
        replace(p, estado=EstadoPropuesta.ACEPTADA)
        for p in sesion.propuestas
        if p.estado is EstadoPropuesta.PENDIENTE
    ]
    origen = OrigenIA(proveedor.nombre, proveedor.modelo, repeticion)
    final = aplicar(partida, aceptadas, origen, catalogo)
    referencia = referencia_de(ficha)
    comparacion = comparar(referencia, final.espacio, final.items_base)
    veredicto = _veredicto(comparacion, final, referencia, partida, auditor)
    total = _elementos(referencia)
    presentes = total - sum(1 for e in comparacion.errores if e.tipo == "E6")
    return Corrida(
        tarea=ficha.id,
        modelo=proveedor.modelo,
        condicion=condicion,
        repeticion=repeticion,
        errores=comparacion.errores,
        veredicto=veredicto,
        llamadas_de_propuesta=sesion.llamadas_de_propuesta,
        validas_al_primer_intento=sesion.propuestas_validas,
        rechazos=dict(sesion.rechazos_por_causa),
        elementos_de_referencia=total,
        elementos_presentes=presentes,
        costo_usd=sesion.costo,
        segundos=segundos,
        rechazo_del_proveedor=sesion.motivo is MotivoFin.REHUSADO,
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
    fecha: date = date(2026, 10, 31),
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
