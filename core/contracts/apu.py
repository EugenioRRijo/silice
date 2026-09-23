"""Entrada y salida del motor de costos, y registro de rendimientos (CLAUDE.md §4 y §5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from core.contracts.unidades import normalizar_unidad


def _exigir_decimal(nombre: str, valor: object) -> Decimal:
    if not isinstance(valor, Decimal):
        raise TypeError(f"{nombre} debe ser Decimal, no {type(valor).__name__}")
    return valor


def _no_negativo(nombre: str, valor: object) -> Decimal:
    decimal = _exigir_decimal(nombre, valor)
    if decimal < 0:
        raise ValueError(f"{nombre} no puede ser negativo: {decimal}")
    return decimal


@dataclass(frozen=True, slots=True)
class LineaMaterial:
    """Un material del APU.

    Su costo entra completo al precio unitario: NO se divide entre el rendimiento.
    """

    descripcion: str
    unidad: str
    cantidad: Decimal
    precio: Decimal

    def __post_init__(self) -> None:
        _no_negativo("cantidad", self.cantidad)
        _no_negativo("precio", self.precio)
        object.__setattr__(self, "unidad", normalizar_unidad(self.unidad))

    @property
    def total(self) -> Decimal:
        return self.cantidad * self.precio


@dataclass(frozen=True, slots=True)
class LineaEquipo:
    """Un equipo del APU. `depreciacion` es la fracción del precio imputable a un día de uso."""

    descripcion: str
    cantidad: Decimal
    precio: Decimal
    depreciacion: Decimal

    def __post_init__(self) -> None:
        _no_negativo("cantidad", self.cantidad)
        _no_negativo("precio", self.precio)
        _exigir_decimal("depreciacion", self.depreciacion)
        if not Decimal(0) < self.depreciacion <= Decimal(1):
            raise ValueError(f"depreciacion debe estar en (0, 1]: {self.depreciacion}")

    @property
    def total(self) -> Decimal:
        return self.cantidad * self.precio * self.depreciacion


class ModalidadManoObra(StrEnum):
    """Cómo se remunera una línea de mano de obra.

    JORNAL es el salario por unidad de tiempo: recibe el factor de costos asociados al salario y
    el bono de alimentación, y se divide entre el rendimiento.
    DESTAJO es el salario por unidad de obra del artículo 114 de la LOTTT: entra completo al
    precio unitario. Bajo esta modalidad, `sueldo` NO es un sueldo diario sino el precio por
    unidad de partida (decisión D9; ver docs/bitacora/2026-09-16-P0-hallazgo-destajo.md).
    """

    JORNAL = "jornal"
    DESTAJO = "destajo"


@dataclass(frozen=True, slots=True)
class LineaManoObra:
    """Una categoría de obrero del APU. `cantidad` = número de obreros.

    `sueldo` es el jornal diario bajo la modalidad JORNAL, o el precio por unidad de partida bajo
    la modalidad DESTAJO (artículo 114 de la LOTTT; ver `ModalidadManoObra`).
    """

    descripcion: str
    cantidad: Decimal
    sueldo: Decimal
    modalidad: ModalidadManoObra = ModalidadManoObra.JORNAL

    def __post_init__(self) -> None:
        _no_negativo("cantidad", self.cantidad)
        _no_negativo("sueldo", self.sueldo)
        object.__setattr__(self, "modalidad", ModalidadManoObra(self.modalidad))

    @property
    def total(self) -> Decimal:
        return self.cantidad * self.sueldo


@dataclass(frozen=True, slots=True)
class ComposicionAPU:
    """Desglose completo de una partida. `rendimiento` = unidades de partida ejecutadas por día."""

    codigo_partida: str
    descripcion: str
    unidad: str
    rendimiento: Decimal
    materiales: tuple[LineaMaterial, ...] = ()
    equipos: tuple[LineaEquipo, ...] = ()
    mano_obra: tuple[LineaManoObra, ...] = ()

    def __post_init__(self) -> None:
        if not self.codigo_partida.strip():
            raise ValueError("codigo_partida no puede estar vacío")
        _exigir_decimal("rendimiento", self.rendimiento)
        if self.rendimiento <= 0:
            raise ValueError(f"rendimiento debe ser mayor que cero: {self.rendimiento}")
        object.__setattr__(self, "unidad", normalizar_unidad(self.unidad))
        object.__setattr__(self, "materiales", tuple(self.materiales))
        object.__setattr__(self, "equipos", tuple(self.equipos))
        object.__setattr__(self, "mano_obra", tuple(self.mano_obra))

    @property
    def total_obreros(self) -> Decimal:
        """Obreros que devengan bono de alimentación: las líneas a destajo no cuentan."""
        return sum(
            (
                linea.cantidad
                for linea in self.mano_obra
                if linea.modalidad is ModalidadManoObra.JORNAL
            ),
            Decimal(0),
        )


@dataclass(frozen=True, slots=True)
class ParametrosCosto:
    """Factores de la estructura de costos. Por defecto, los de la línea base (CLAUDE.md §4).

    fcas: Factor de Costos Asociados al Salario, como fracción (6.00 = prestaciones del 600 %).
    bono_alimentacion: monto diario por obrero, en la moneda del presupuesto.
    administracion y utilidad: fracciones que se aplican EN CASCADA sobre el costo directo.
    """

    fcas: Decimal = Decimal("6.00")
    bono_alimentacion: Decimal = Decimal("1.00")
    administracion: Decimal = Decimal("0.15")
    utilidad: Decimal = Decimal("0.10")

    def __post_init__(self) -> None:
        for nombre in ("fcas", "bono_alimentacion", "administracion", "utilidad"):
            _no_negativo(nombre, getattr(self, nombre))


@dataclass(frozen=True, slots=True)
class ResultadoAPU:
    """Salida del motor de costos. Montos por unidad de partida, sin redondear."""

    materiales: Decimal
    equipos: Decimal
    mano_obra: Decimal
    costo_directo: Decimal
    con_administracion: Decimal
    precio_unitario: Decimal


class TipoRendimiento(StrEnum):
    ESTIMADO = "estimado"  # declarado por el proyectista
    MEDIDO = "medido"  # observado en obra ejecutada; exige referencia_ejecucion


@dataclass(frozen=True, slots=True)
class Rendimiento:
    """Rendimiento de una partida y su procedencia. Nunca se mezcla estimado con medido."""

    codigo_partida: str
    valor: Decimal
    tipo: TipoRendimiento
    fecha: date
    condiciones: str = ""
    referencia_ejecucion: str | None = None

    def __post_init__(self) -> None:
        _exigir_decimal("valor", self.valor)
        if self.valor <= 0:
            raise ValueError(f"valor debe ser mayor que cero: {self.valor}")
        if self.tipo is TipoRendimiento.MEDIDO and not self.referencia_ejecucion:
            raise ValueError(
                "un rendimiento MEDIDO debe referenciar la ejecución de la que proviene"
            )
