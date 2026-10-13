"""Modelo en memoria del libro que se devuelve (spec 1.5, F-D3 a F-D5).

El escritor no escribe celda por celda directamente en XlsxWriter: primero arma el libro completo en
este modelo (celdas con su literal o su fórmula, su estilo y su valor sembrado), después calcula el
valor guardado de cada fórmula (`calculos`) y al final lo vuelca a XlsxWriter (`salida`). Así cada
fórmula sale con su valor y el orden de escritura no importa.

Una celda puede tener:

- `valor`: el literal (Decimal, str, bool, datetime o None).
- `formula`: el texto de la fórmula (con '='). Si la hay, `valor` no se usa.
- `fijo`: el valor sembrado de una fórmula (lo que calculó Silice). Si está, el calculador no evalúa
  la fórmula: la celda vale eso. Así P.U., componentes y totales salen iguales a los de Silice.
- `respaldo`: el valor guardado en el libro recibido, para cuando el calculador no soporta una
  fórmula (se informa en TRAZABILIDAD).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adapters.hoja_empresa.escritor.estilos import Estilo

__all__ = ["NADA", "CeldaSalida", "HojaSalida", "Imagen", "LibroSalida", "Nota"]


class _Nada:
    """Centinela de 'sin valor sembrado' (None es un valor válido: celda vacía)."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "NADA"


NADA: Any = _Nada()


@dataclass(slots=True)
class CeldaSalida:
    valor: object = None
    formula: str | None = None
    estilo: Estilo | None = None
    fijo: object = NADA
    respaldo: object = None
    comentario: str | None = None
    calculado: object = NADA


@dataclass(slots=True)
class Imagen:
    fila: int
    col: int
    datos: bytes
    opciones: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Nota:
    """Una transformación hecha por el escritor (va a TRAZABILIDAD): qué, dónde y por qué."""

    dato: str
    valor: str
    origen: str
    nota: str


@dataclass(slots=True)
class HojaSalida:
    nombre: str
    celdas: dict[tuple[int, int], CeldaSalida] = field(default_factory=dict)
    anchos: dict[int, tuple[float | None, bool]] = field(default_factory=dict)
    altos: dict[int, tuple[float | None, bool]] = field(default_factory=dict)
    combinadas: list[tuple[int, int, int, int]] = field(default_factory=list)
    validaciones: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    condicionales: list[tuple[str, dict[str, Any], Estilo | None]] = field(default_factory=list)
    impresion: dict[str, Any] = field(default_factory=dict)
    paneles: tuple[int, int] | None = None
    oculta: bool = False
    color_pestana: str | None = None
    zoom: int | None = None
    sin_cuadricula: bool = False
    imagenes: list[Imagen] = field(default_factory=list)
    graficos: list[Any] = field(default_factory=list)
    alto_defecto: float | None = None

    def celda(self, fila: int, col: int) -> CeldaSalida:
        """La celda (fila, col), creándola vacía si no existe."""
        c = self.celdas.get((fila, col))
        if c is None:
            c = CeldaSalida()
            self.celdas[(fila, col)] = c
        return c

    def poner(
        self,
        fila: int,
        col: int,
        valor: object = None,
        *,
        formula: str | None = None,
        estilo: Estilo | None = None,
        fijo: object = NADA,
    ) -> CeldaSalida:
        """Escribe un literal o una fórmula; conserva el estilo existente si no se da otro."""
        c = self.celda(fila, col)
        c.valor = None if formula else valor
        c.formula = formula
        c.fijo = fijo
        c.calculado = NADA
        if estilo is not None:
            c.estilo = estilo
        return c

    @property
    def max_fila(self) -> int:
        return max((f for f, _ in self.celdas), default=0)

    @property
    def max_col(self) -> int:
        return max((c for _, c in self.celdas), default=0)


@dataclass(slots=True)
class LibroSalida:
    hojas: dict[str, HojaSalida] = field(default_factory=dict)
    orden: list[str] = field(default_factory=list)
    nombres: dict[str, str] = field(default_factory=dict)
    notas: list[Nota] = field(default_factory=list)
    propiedades: dict[str, str] = field(default_factory=dict)
    propiedades_extra: dict[str, str] = field(default_factory=dict)

    def agregar(self, hoja: HojaSalida) -> HojaSalida:
        self.hojas[hoja.nombre] = hoja
        self.orden.append(hoja.nombre)
        return hoja

    def anotar(self, dato: str, valor: object, origen: str, nota: str) -> None:
        self.notas.append(Nota(dato, "" if valor is None else str(valor), origen, nota))
