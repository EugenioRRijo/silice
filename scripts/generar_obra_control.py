# scripts/generar_obra_control.py
"""Generador determinista de una obra grande para el control (spec S2 §3.3, RNF-15).

Produce, con una semilla, una obra de `partidas` partidas, `periodos` períodos semanales de cinco
días hábiles y `valuaciones` valuaciones semanales: cantidades, APU (cuadrilla a jornal, equipo y
material), plan con fracciones exactas (1, 1/2, 1/4 o 1/5), valuaciones consecutivas que avanzan
entre el 70 % y el 110 % de lo planificado, un costo real por valuación y los unitarios del corte.
**Datos ficticios** (NORMAS.md §1). Sirve a `scripts/medir_rnf15.py` y a las pruebas de la
identidad `CV = precio + consumo` y de la pureza del control sobre una obra de tamaño real.

La obra se arma en memoria (`generar`); `sembrar` la guarda en una base (versión, plan, línea base
de control) para medir el camino completo. Mismas entradas, misma obra, byte a byte.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto
from core.budget.curva import PeriodoPlan
from core.budget.valor_ganado import PreciosDelCorte
from core.budget.valuaciones import (
    Calendario,
    CostoReal,
    registrar_costo,
    registrar_linea_base,
    registrar_valuacion,
)
from core.catalog import Catalogo
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import Presupuesto
from core.verification.valuaciones import LineaValuacion, Valuacion

D = Decimal
NOMBRE = "OBRA-GENERADA"
CODIGO = "GEN-001"
INICIO = date(2026, 11, 2)  # lunes
MONEDA = "USD"
PARAMETROS = ParametrosCosto(D("6.00"), D("1.00"), D("0.15"), D("0.10"))
FUENTE = "generador determinista (datos ficticios)"
RESPONSABLE = "Residente Ficticio"
#: Fracciones exactas: el plan de cada partida reparte 1 en tramos iguales de 1, 2, 4 o 5 períodos.
TRAMOS = (1, 2, 4, 5)


@dataclass(frozen=True)
class ObraGenerada:
    """La obra generada, sin base de datos."""

    presupuesto: Presupuesto
    plan: tuple[PeriodoPlan, ...]
    composiciones: dict[str, ComposicionAPU]
    items: list[ItemComputo]
    valuaciones: tuple[Valuacion, ...]
    costos: tuple[CostoReal, ...]
    precios: PreciosDelCorte
    calendario: Calendario
    corte: date


def _codigo(n: int) -> str:
    return f"G-{n:04d}"


def _composicion(rng: random.Random, codigo: str) -> ComposicionAPU:
    obreros = D(rng.randint(2, 6))
    return ComposicionAPU(
        codigo,
        f"Partida generada {codigo}",
        "m3",
        D(rng.choice((5, 10, 20, 40))),
        materiales=(
            LineaMaterial(f"Material {codigo}", "m3", D(1), D(rng.randint(2, 30)) + D("0.50")),
        ),
        equipos=(LineaEquipo(f"Equipo {codigo}", D(1), D(rng.randint(20, 200)), D("0.10")),),
        mano_obra=(LineaManoObra(f"Cuadrilla {codigo}", obreros, D(rng.randint(3, 8))),),
    )


def _plan(rng: random.Random, partidas: int, periodos: int) -> list[PeriodoPlan]:
    """Cada partida reparte 1 en `tramo` períodos consecutivos desde un inicio elegido."""
    reparto: list[list[tuple[str, Decimal]]] = [[] for _ in range(periodos)]
    for n in range(1, partidas + 1):
        tramo = rng.choice(TRAMOS)
        inicio = rng.randint(0, periodos - tramo)
        for k in range(tramo):
            reparto[inicio + k].append((_codigo(n), D(1) / D(tramo)))
    return [(f"Semana {n}", tuple(fila)) for n, fila in enumerate(reparto, start=1)]


def generar(
    partidas: int = 500, periodos: int = 52, valuaciones: int = 26, semilla: int = 0
) -> ObraGenerada:
    """La obra de `partidas` partidas con valuaciones semanales hasta la semana `valuaciones`.

    El corte es el viernes de la última semana valuada. Cada valuación cubre una semana exacta y
    avanza lo planificado de esa semana por un factor entre 0,70 y 1,10 (sin pasar de lo
    presupuestado)."""
    if not 1 <= valuaciones <= periodos:
        raise ValueError("las valuaciones semanales deben caber en el plan")
    rng = random.Random(semilla)
    composiciones = {_codigo(n): _composicion(rng, _codigo(n)) for n in range(1, partidas + 1)}
    cantidades = {codigo: D(rng.randint(50, 500)) for codigo in composiciones}
    items = [
        ItemComputo(
            codigo,
            composicion.descripcion,
            "m3",
            cantidades[codigo],
            f"generador:{codigo}",
            OrigenTipo.MANUAL,
            Dominio.CIVIL,
        )
        for codigo, composicion in composiciones.items()
    ]
    plan = _plan(rng, partidas, periodos)
    resultado = elaborar(
        items, composiciones, PARAMETROS, codigo=CODIGO, fecha=INICIO, moneda=MONEDA, plan=plan
    )
    fracciones = {(codigo, n): f for n, (_, reparto) in enumerate(plan) for codigo, f in reparto}
    ejecutadas: dict[str, Decimal] = {}
    lista: list[Valuacion] = []
    costos: list[CostoReal] = []
    unitario = {
        p.item.codigo_partida: p.resultado.costo_directo for p in resultado.presupuesto.partidas
    }
    for semana in range(valuaciones):
        desde = INICIO + timedelta(weeks=semana)
        hasta = desde + timedelta(days=4)
        lineas = []
        gastado = D(0)
        for codigo in composiciones:
            planificada = fracciones.get((codigo, semana))
            if planificada is None:
                continue
            factor = D(rng.randint(70, 110)) / D(100)
            cantidad = (cantidades[codigo] * planificada * factor).quantize(D("0.01"))
            cantidad = min(cantidad, cantidades[codigo] - ejecutadas.get(codigo, D(0)))
            if cantidad <= 0:
                continue
            ejecutadas[codigo] = ejecutadas.get(codigo, D(0)) + cantidad
            lineas.append(LineaValuacion(codigo, cantidad))
            gastado += cantidad * unitario[codigo]
        lista.append(
            Valuacion(
                id=semana + 1,
                numero=f"V-{semana + 1:02d}",
                desde=desde,
                hasta=hasta,
                fecha=hasta + timedelta(days=3),
                inspector="Ing. Ficticio",
                lineas=tuple(lineas),
            )
        )
        costos.append(
            CostoReal(
                semana + 1,
                (gastado * D(rng.randint(95, 115)) / D(100)).quantize(D("0.01")),
                MONEDA,
                hasta,
                FUENTE,
                RESPONSABLE,
            )
        )
    precios = PreciosDelCorte(
        "comprobacion",
        FUENTE,
        {c: u * (D(100) + D(rng.randint(0, 10))) / D(100) for c, u in unitario.items()},
    )
    return ObraGenerada(
        resultado.presupuesto,
        tuple(plan),
        composiciones,
        items,
        tuple(lista),
        tuple(costos),
        precios,
        Calendario(INICIO, 5),
        lista[-1].hasta,
    )


def sembrar(sesion, obra: ObraGenerada, *, con_valuaciones: bool = True) -> None:
    """Guarda la obra en la base: lista, catálogo, versión con su plan, línea base de control y,
    si `con_valuaciones`, sus valuaciones y costos salvo la última (la que se mide). No confirma."""
    lista = models.ListaPrecios(nombre="Generada USD", moneda=MONEDA, fecha_vigencia=INICIO)
    sesion.add(lista)
    sesion.flush()
    catalogo = Catalogo(sesion)
    for composicion in obra.composiciones.values():
        catalogo.cargar_composicion(composicion, lista, Dominio.CIVIL, INICIO, "generador")
    resultado = elaborar(
        obra.items,
        obra.composiciones,
        PARAMETROS,
        codigo=CODIGO,
        fecha=INICIO,
        moneda=MONEDA,
        plan=list(obra.plan),
    )
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=crear_proyecto(sesion, NOMBRE),
        lista=lista,
        parametros=PARAMETROS,
        plan=list(obra.plan),
        usuario="script:generar_obra_control",
    )
    registrar_linea_base(
        sesion, NOMBRE, CODIGO, desde=INICIO, perspectiva="costo", calendario=obra.calendario,
        fuente=FUENTE, responsable=RESPONSABLE,
    )  # fmt: skip
    if con_valuaciones:
        for valuacion in obra.valuaciones[:-1]:
            registrar_valuacion_de(sesion, valuacion)
        for costo in obra.costos[:-1]:
            registrar_costo_de(sesion, costo)


def registrar_valuacion_de(sesion, valuacion: Valuacion):
    """Registra una valuación generada (la que `medir_rnf15` mide es la última)."""
    return registrar_valuacion(
        sesion,
        NOMBRE,
        numero=valuacion.numero,
        desde=valuacion.desde,
        hasta=valuacion.hasta,
        fecha=valuacion.fecha,
        inspector=valuacion.inspector,
        lineas=valuacion.lineas,
        fuente=FUENTE,
        responsable=RESPONSABLE,
    )


def registrar_costo_de(sesion, costo: CostoReal):
    return registrar_costo(
        sesion,
        NOMBRE,
        monto=costo.monto,
        moneda=costo.moneda,
        fecha=costo.fecha,
        fuente=costo.fuente,
        responsable=RESPONSABLE,
    )
