"""Interfaz comun de proveedor de IA y tipos neutrales (S4 §5.3). Solo biblioteca estandar.

El historial es SOLO de agregar (append-only): cada `Mensaje` del asistente guarda en `crudo` los
bloques del modelo tal como llegaron, y el adaptador los devuelve sin editarlos (con los modelos
vigentes los bloques de razonamiento estan atados al modelo y a la conversacion). Un proveedor por
sesion (RS4-5): cambiar de proveedor abre otra sesion.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Protocol


class FinTurno(StrEnum):
    FIN = "fin"
    HERRAMIENTAS = "herramientas"
    LIMITE = "limite"  # respuesta cortada por el limite de salida (9j)
    RECHAZO = "rechazo"  # el proveedor rechazo el pedido (9e)


@dataclass(frozen=True, slots=True)
class Uso:
    entrada: int = 0
    salida: int = 0
    cache_lectura: int = 0
    cache_escritura: int = 0


@dataclass(frozen=True, slots=True)
class Tarifa:
    """USD por millon de fichas. El modelo local cuesta cero (se registra tiempo y equipo)."""

    entrada: Decimal
    salida: Decimal
    cache_lectura: Decimal = Decimal(0)
    cache_escritura: Decimal = Decimal(0)

    def costo(self, uso: Uso) -> Decimal:
        total = (
            uso.entrada * self.entrada
            + uso.salida * self.salida
            + uso.cache_lectura * self.cache_lectura
            + uso.cache_escritura * self.cache_escritura
        )
        return total / Decimal(1_000_000)


@dataclass(frozen=True, slots=True)
class LlamadaHerramienta:
    id: str
    nombre: str
    argumentos: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ResultadoHerramienta:
    llamada_id: str
    contenido: str
    es_error: bool = False


@dataclass(frozen=True, slots=True)
class Mensaje:
    rol: Literal["usuario", "asistente"]
    texto: str = ""
    llamadas: tuple[LlamadaHerramienta, ...] = ()
    resultados: tuple[ResultadoHerramienta, ...] = ()
    crudo: object | None = None


@dataclass(frozen=True, slots=True)
class Turno:
    texto: str
    llamadas: tuple[LlamadaHerramienta, ...]
    fin: FinTurno
    uso: Uso = field(default_factory=Uso)
    modelo_que_respondio: str = ""
    crudo: object | None = None
    motivo: str = ""  # categoria del rechazo, si el proveedor la da


@dataclass(frozen=True, slots=True)
class Disponibilidad:
    disponible: bool
    motivo: str = ""


#: El motivo de «no disponible» cuando falta el extra `ia` (anthropic, ollama o keyring).
FALTA_EL_COMPONENTE = "Falta el componente del asistente: uv sync --extra ia"


@dataclass(frozen=True, slots=True)
class EsquemaHerramienta:
    nombre: str
    descripcion: str
    esquema: Mapping[str, object]


class ErrorDeProveedor(Exception):  # noqa: N818
    """Falla del proveedor con una categoria que la interfaz sabe explicar (9a, 9b)."""

    def __init__(self, categoria: Literal["sin_conexion", "clave_invalida", "otro"], mensaje: str):
        super().__init__(mensaje)
        self.categoria = categoria


class ProveedorIA(Protocol):
    nombre: str
    modelo: str
    envia_fuera_del_equipo: bool

    def disponible(self) -> Disponibilidad: ...

    def turno(
        self,
        sistema: str,
        mensajes: Sequence[Mensaje],
        herramientas: Sequence[EsquemaHerramienta],
    ) -> Turno: ...
