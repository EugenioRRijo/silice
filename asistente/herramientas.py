"""Las 13 herramientas que ve el modelo (S4 §6): modelos Pydantic estrictos y sus esquemas.

Reglas comunes: `extra="forbid"` (esquema con `additionalProperties: false`), todos los campos
requeridos (los opcionales admiten `null` pero no se omiten) y los numeros como TEXTO decimal
(`"2.40"` o `"2,40"`, hasta 3 decimales): nunca `float` (NORMAS §2.3). Ninguna herramienta tiene un
campo de precio, de total ni de cantidad derivada: el esquema lo hace imposible, no una instruccion
al modelo (RF-91). `proponer_partida` lleva `cantidad` porque su partida no deriva del espacio.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from adapters.espacio import (
    Especialidad,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoPunto,
)

#: `^-?\d{1,4}([.,]\d{1,3})?$` (S4 §6). Las dimensiones ademas deben ser positivas (validacion).
PATRON_NUMERO = r"^-?\d{1,4}([.,]\d{1,3})?$"
Numero = Annotated[str, StringConstraints(pattern=PATRON_NUMERO)]
Identificador = Annotated[str, StringConstraints(min_length=1, max_length=40)]
Texto = Annotated[str, StringConstraints(min_length=1, max_length=200)]

#: Lista cerrada de especificaciones de un punto: lo que leen agua, datos y electricidad.
ESPECIFICACIONES_ADMITIDAS: tuple[str, ...] = (
    "diametro",
    "llave_de_paso",
    "material",
    "canalizacion",
    "categoria",
)


class TipoHerramienta(StrEnum):
    LECTURA = "lectura"
    PROPUESTA = "propuesta"
    CONTROL = "control"


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Cita(_Estricto):
    """`texto` aparece literalmente en el pedido o en una respuesta del usuario (S4 §7.3)."""

    campo: Identificador
    texto: Texto


class Supuesto(_Estricto):
    campo: Identificador
    motivo: Texto


class Par(_Estricto):
    clave: Literal["diametro", "llave_de_paso", "material", "canalizacion", "categoria"]
    valor: Annotated[str, StringConstraints(min_length=1, max_length=40)]


class Vertice(_Estricto):
    x: Numero
    y: Numero
    z: Numero


class TramoDeclarado(_Estricto):
    orden: Annotated[int, Field(ge=1, le=99)]
    superficie: SuperficieTramo
    vertices: Annotated[list[Vertice], Field(min_length=2, max_length=20)]


class Sustento(_Estricto):
    """Citas y supuestos: todo numero de la llamada trae una cita o un supuesto."""

    citas: Annotated[list[Cita], Field(max_length=30)]
    supuestos: Annotated[list[Supuesto], Field(max_length=30)]


class ConsultarBorrador(_Estricto):
    pass


class BuscarPartidas(_Estricto):
    texto: Texto
    especialidad: Especialidad | None
    cuantos: Annotated[int, Field(ge=1, le=10)]


class ConsultarPartida(_Estricto):
    codigo: Identificador


class ProponerAmbiente(Sustento):
    id: Identificador
    nombre: Texto
    x0: Numero
    y0: Numero
    largo: Numero
    ancho: Numero
    alto: Numero


class ProponerFuente(Sustento):
    id: Identificador
    especialidad: Especialidad
    tipo: TipoFuente
    ambiente_id: Identificador
    x: Numero
    y: Numero
    z: Numero


class ProponerPunto(Sustento):
    id: Identificador
    nombre: Texto
    especialidad: Especialidad
    tipo: TipoPunto
    ambiente_id: Identificador
    superficie: SuperficiePunto
    x: Numero
    y: Numero
    z: Numero
    fuente_id: Identificador | None
    circuito_id: Identificador | None
    especificaciones: Annotated[list[Par], Field(max_length=8)]


class ProponerRecorrido(Sustento):
    punto_id: Identificador | None
    circuito_id: Identificador | None
    modo: Literal["propuesto", "declarado"]
    tramos: Annotated[list[TramoDeclarado], Field(max_length=30)] | None


class ProponerPartida(Sustento):
    codigo: Identificador
    unidad: Annotated[str, StringConstraints(min_length=1, max_length=20)]
    cantidad: Numero


class DeclararSinPartida(_Estricto):
    necesidad: Texto


class RetirarPropuesta(_Estricto):
    propuesta_id: Identificador


class PedirInformeAuditoria(_Estricto):
    pass


class PreguntarAlUsuario(_Estricto):
    pregunta: Texto


class Terminar(_Estricto):
    notas: Annotated[list[Texto], Field(max_length=10)]


@dataclass(frozen=True, slots=True)
class Herramienta:
    nombre: str
    tipo: TipoHerramienta
    modelo: type[BaseModel]
    descripcion: str

    def esquema(self) -> dict[str, object]:
        """El esquema JSON de la herramienta (generado del modelo Pydantic)."""
        return self.modelo.model_json_schema()


_L, _P, _C = TipoHerramienta.LECTURA, TipoHerramienta.PROPUESTA, TipoHerramienta.CONTROL

#: El orden de esta tupla es el que viaja al proveedor: no se reordena (S4 §6).
HERRAMIENTAS: tuple[Herramienta, ...] = (
    Herramienta(
        "consultar_borrador",
        _L,
        ConsultarBorrador,
        "Resumen del borrador: ambientes, fuentes, puntos, recorridos y partidas, sin precios.",
    ),
    Herramienta(
        "buscar_partidas",
        _L,
        BuscarPartidas,
        "Busca partidas del catalogo por texto. Devuelve codigo, descripcion y unidad.",
    ),
    Herramienta(
        "consultar_partida",
        _L,
        ConsultarPartida,
        "Descripcion, unidad y tipos de insumo de una partida, sin cantidades ni precios.",
    ),
    Herramienta(
        "proponer_ambiente",
        _P,
        ProponerAmbiente,
        "Propone un ambiente rectangular. Cada numero lleva una cita del pedido o un supuesto.",
    ),
    Herramienta(
        "proponer_fuente",
        _P,
        ProponerFuente,
        "Propone una fuente (acometida, montante, colector, rack, tablero).",
    ),
    Herramienta(
        "proponer_punto",
        _P,
        ProponerPunto,
        "Propone un punto de agua, drenaje, datos, tomacorriente o iluminacion.",
    ),
    Herramienta(
        "proponer_recorrido",
        _P,
        ProponerRecorrido,
        "Propone el recorrido de un punto: propuesto (lo calcula el sistema) o declarado.",
    ),
    Herramienta(
        "proponer_partida",
        _P,
        ProponerPartida,
        "Propone una partida que no deriva del espacio (equipos). La cantidad se cita.",
    ),
    Herramienta(
        "declarar_sin_partida",
        _P,
        DeclararSinPartida,
        "Declara una necesidad que el catalogo no cubre. No inventa una partida.",
    ),
    Herramienta(
        "retirar_propuesta", _P, RetirarPropuesta, "Retira una propuesta pendiente propia."
    ),
    Herramienta(
        "pedir_informe_auditoria",
        _L,
        PedirInformeAuditoria,
        "Informe del auditor sobre el borrador mas las propuestas pendientes.",
    ),
    Herramienta(
        "preguntar_al_usuario",
        _C,
        PreguntarAlUsuario,
        "Hace una pregunta a la persona. No pida claves, contrasenas ni precios.",
    ),
    Herramienta("terminar", _C, Terminar, "Termina la sesion con notas breves, sin montos."),
)

POR_NOMBRE: dict[str, Herramienta] = {h.nombre: h for h in HERRAMIENTAS}

#: Campos que NINGUNA herramienta puede tener (RF-91): se vigilan por nombre en el esquema.
CAMPOS_PROHIBIDOS: frozenset[str] = frozenset(
    {"precio", "monto", "total", "costo", "importe", "pu", "precio_unitario", "subtotal"}
)


def a_decimal(texto: str) -> Decimal:
    """`"2,40"` y `"2.40"` son 2.40. El patron ya garantizo la forma."""
    return Decimal(texto.replace(",", "."))
