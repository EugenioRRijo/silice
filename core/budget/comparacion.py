"""SL-E9: la diferencia entre dos versiones y su costo, y la revaloración en memoria (spec S3 §9,
paso 4; maestro §9.1, RV-10).

Funciones puras: no leen la base ni escriben nada. **Diferencia entre versiones**, por partida:

    Δ total  = q2·PU2 − q1·PU1 = (q2 − q1)·PU1   [desvío por cantidad]
                               + (PU2 − PU1)·q2   [desvío por precio]

El término cruzado queda en el precio. Una partida que solo está en una versión es desvío por
cantidad entero: nueva (q1 = 0 y PU1 := PU2) o eliminada (q2 = 0 y PU2 := PU1). Las dos columnas
suman EXACTO el Δ total (`Decimal` sin redondeos). Es una descomposición **distinta** de la
«separación del desvío de control» de S2 (término cruzado en el consumo): S2 no la reutiliza.

**Revaloración**: el presupuesto de un paquete valorado con los precios de la lista de quien
revisa, emparejando cada línea por **referencia de precio** (Ref MaPreX) o, si no, por código de
insumo. Lo que no empareja es «no contrastable»: conserva su precio, se lista y no suma al Δ.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any

from core.budget.canonico import DocumentoLeido
from core.contracts.apu import ComposicionAPU
from core.costing import calcular_apu

__all__ = [
    "Diferencia",
    "DiferenciaPartida",
    "FilaPresupuesto",
    "NoContrastable",
    "PrecioDeLista",
    "Revaloracion",
    "diferencia_entre_versiones",
    "filas_de",
    "revalorar",
]

CERO = Decimal(0)
IGUAL, CAMBIADA, NUEVA, ELIMINADA = "igual", "cambiada", "nueva", "eliminada"


def _contexto_fijo[F: Callable[..., Any]](funcion: F) -> F:
    """Corre `funcion` con el contexto decimal del motor (prec 28, ROUND_HALF_EVEN), sin depender
    del contexto del hilo que llama (NORMAS §2; ninguna división aquí, pero sí productos y sumas
    que redondean a `prec`)."""

    @functools.wraps(funcion)
    def envuelta(*args: Any, **kwargs: Any) -> Any:
        with localcontext(prec=28, rounding=ROUND_HALF_EVEN):
            return funcion(*args, **kwargs)

    return envuelta  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class FilaPresupuesto:
    """Una partida de una versión: su cantidad total y su precio unitario recalculado."""

    codigo_partida: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    precio_unitario: Decimal


@dataclass(frozen=True, slots=True)
class DiferenciaPartida:
    codigo_partida: str
    descripcion: str
    estado: str  # igual | cambiada | nueva | eliminada
    cantidad_1: Decimal
    cantidad_2: Decimal
    precio_1: Decimal
    precio_2: Decimal
    desvio_cantidad: Decimal
    desvio_precio: Decimal

    @property
    def desvio_total(self) -> Decimal:
        return self.desvio_cantidad + self.desvio_precio


@dataclass(frozen=True, slots=True)
class Diferencia:
    partidas: tuple[DiferenciaPartida, ...]  # por |Δ total| descendente, luego por código
    total_1: Decimal
    total_2: Decimal
    desvio_cantidad: Decimal
    desvio_precio: Decimal

    @property
    def desvio_total(self) -> Decimal:
        return self.desvio_cantidad + self.desvio_precio


def _por_codigo(filas: Sequence[FilaPresupuesto]) -> dict[str, FilaPresupuesto]:
    """Junta las filas de una misma partida (cantidades suman); su precio debe ser único."""
    junto: dict[str, FilaPresupuesto] = {}
    for fila in filas:
        previa = junto.get(fila.codigo_partida)
        if previa is None:
            junto[fila.codigo_partida] = fila
        elif previa.precio_unitario != fila.precio_unitario:
            raise ValueError(
                f"la partida {fila.codigo_partida} aparece con dos precios unitarios distintos"
            )
        else:
            junto[fila.codigo_partida] = replace(previa, cantidad=previa.cantidad + fila.cantidad)
    return junto


@_contexto_fijo
def diferencia_entre_versiones(
    a: Sequence[FilaPresupuesto], b: Sequence[FilaPresupuesto]
) -> Diferencia:
    """La diferencia de `b` (la versión nueva) respecto de `a` (la anterior)."""
    uno, dos = _por_codigo(a), _por_codigo(b)
    partidas: list[DiferenciaPartida] = []
    for codigo in sorted(set(uno) | set(dos)):
        antes, despues = uno.get(codigo), dos.get(codigo)
        if antes is None:
            q1, p1, q2, p2, estado = (
                CERO,
                despues.precio_unitario,
                despues.cantidad,
                despues.precio_unitario,
                NUEVA,
            )
        elif despues is None:
            q1, p1, q2, p2, estado = (
                antes.cantidad,
                antes.precio_unitario,
                CERO,
                antes.precio_unitario,
                ELIMINADA,
            )
        else:
            q1, p1, q2, p2 = (
                antes.cantidad,
                antes.precio_unitario,
                despues.cantidad,
                despues.precio_unitario,
            )
            estado = IGUAL if (q1, p1) == (q2, p2) else CAMBIADA
        partidas.append(
            DiferenciaPartida(
                codigo_partida=codigo,
                descripcion=(despues or antes).descripcion,
                estado=estado,
                cantidad_1=q1,
                cantidad_2=q2,
                precio_1=p1,
                precio_2=p2,
                desvio_cantidad=(q2 - q1) * p1,
                desvio_precio=(p2 - p1) * q2,
            )
        )
    partidas.sort(key=lambda p: (-abs(p.desvio_total), p.codigo_partida))
    return Diferencia(
        partidas=tuple(partidas),
        total_1=sum((f.cantidad * f.precio_unitario for f in uno.values()), CERO),
        total_2=sum((f.cantidad * f.precio_unitario for f in dos.values()), CERO),
        desvio_cantidad=sum((p.desvio_cantidad for p in partidas), CERO),
        desvio_precio=sum((p.desvio_precio for p in partidas), CERO),
    )


@_contexto_fijo
def filas_de(documento: DocumentoLeido) -> tuple[FilaPresupuesto, ...]:
    """Las partidas de un documento con su precio unitario RECALCULADO por el motor desde las
    composiciones y los parámetros del propio documento (no se confía en lo declarado)."""
    filas: list[FilaPresupuesto] = []
    for item in documento.items:
        composicion = documento.composiciones[item.codigo_partida]
        filas.append(
            FilaPresupuesto(
                item.codigo_partida,
                item.descripcion,
                item.unidad,
                item.cantidad,
                calcular_apu(composicion, documento.parametros).precio_unitario,
            )
        )
    return tuple(filas)


# --- revaloración en memoria -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PrecioDeLista:
    """Un precio de la lista de quien revisa: por referencia de precio y por código de insumo."""

    codigo_insumo: str
    referencia: str
    precio: Decimal


@dataclass(frozen=True, slots=True)
class NoContrastable:
    codigo_partida: str
    descripcion: str
    insumo: str | None


@dataclass(frozen=True, slots=True)
class Revaloracion:
    filas: tuple[FilaPresupuesto, ...]
    no_contrastables: tuple[NoContrastable, ...]


def _revalorada(
    composicion: ComposicionAPU,
    extras: Sequence,
    por_referencia: Mapping[str, Decimal],
    por_codigo: Mapping[str, Decimal],
    sin_par: list[NoContrastable],
) -> ComposicionAPU:
    lineas = [*composicion.materiales, *composicion.equipos, *composicion.mano_obra]
    nuevas = []
    for linea, extra in zip(lineas, extras, strict=True):
        precio = por_referencia.get(extra.referencia) if extra.referencia else None
        if precio is None and extra.insumo is not None:
            precio = por_codigo.get(extra.insumo)
        if precio is None:
            sin_par.append(
                NoContrastable(composicion.codigo_partida, linea.descripcion, extra.insumo)
            )
            nuevas.append(linea)
        elif hasattr(linea, "sueldo"):
            nuevas.append(replace(linea, sueldo=precio))
        else:
            nuevas.append(replace(linea, precio=precio))
    nm, ne = len(composicion.materiales), len(composicion.equipos)
    return replace(
        composicion,
        materiales=tuple(nuevas[:nm]),
        equipos=tuple(nuevas[nm : nm + ne]),
        mano_obra=tuple(nuevas[nm + ne :]),
    )


@_contexto_fijo
def revalorar(documento: DocumentoLeido, precios: Sequence[PrecioDeLista]) -> Revaloracion:
    """El documento valorado con `precios`, en memoria. Las líneas sin pareja conservan su
    precio, se listan en `no_contrastables` (una vez por partida e insumo) y no suman al Δ."""
    por_referencia = {p.referencia: p.precio for p in precios if p.referencia}
    por_codigo = {p.codigo_insumo: p.precio for p in precios}
    sin_par: list[NoContrastable] = []
    nuevas = {
        codigo: _revalorada(
            composicion, documento.lineas[codigo], por_referencia, por_codigo, sin_par
        )
        for codigo, composicion in documento.composiciones.items()
    }
    filas = tuple(
        FilaPresupuesto(
            item.codigo_partida,
            item.descripcion,
            item.unidad,
            item.cantidad,
            calcular_apu(nuevas[item.codigo_partida], documento.parametros).precio_unitario,
        )
        for item in documento.items
    )
    unicas = tuple(dict.fromkeys(sin_par))
    return Revaloracion(filas=filas, no_contrastables=unicas)
