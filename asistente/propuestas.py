"""Propuestas pendientes y su aplicacion al borrador (S4 §3.1 pasos 4-6, §5.4).

Una propuesta valida queda PENDIENTE; el borrador no cambia hasta que la persona la acepta
(RF-32). Aplicar es construir otro `Borrador` con `dataclasses.replace` por la MISMA puerta que una
edicion a mano (`espacio_desde_filas`), asi que pasa por el mismo auditor (RF-92). Cada propuesta
aceptada cita su origen «propuesta de IA»: un `OrigenMedida` de tipo `ia` para las filas del espacio
y un `ItemComputo` MANUAL con `origen_id = "ia:<sesion>:<propuesta>"` para las partidas (§5.4).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum

from adapters.espacio import ModoRecorrido, Recorrido
from asistente.catalogo import CatalogoVista
from core.contracts.item_computo import ItemComputo, OrigenTipo
from ui.hoja import (
    PREFIJO_ORIGEN_IA,
    Borrador,
    HojaInvalida,
    espacio_desde_filas,
    filas_desde_espacio,
)


class TipoPropuesta(StrEnum):
    AMBIENTE = "ambiente"
    FUENTE = "fuente"
    PUNTO = "punto"
    RECORRIDO = "recorrido"
    PARTIDA = "partida"
    SIN_PARTIDA = "sin_partida"


class EstadoPropuesta(StrEnum):
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    EDITADA = "editada"
    RECHAZADA = "rechazada"


#: Tabla del editor de la hoja donde cae cada tipo (`ui.hoja.COLUMNAS`).
TABLA_DE = {
    TipoPropuesta.AMBIENTE: "ambientes",
    TipoPropuesta.FUENTE: "fuentes",
    TipoPropuesta.PUNTO: "puntos",
}


@dataclass(frozen=True, slots=True)
class Propuesta:
    """`filas`: celdas de texto como las del editor (sin `origen_id`; lo pone `aplicar`).

    Para un recorrido declarado son las filas de la tabla `tramos`; para uno propuesto, una sola
    con `punto_id` y `circuito_id`; para una partida, `codigo`, `unidad` y `cantidad`.
    """

    id: str
    tipo: TipoPropuesta
    filas: tuple[Mapping[str, str], ...]
    citas: tuple[tuple[str, str], ...] = ()
    supuestos: tuple[tuple[str, str], ...] = ()
    estado: EstadoPropuesta = EstadoPropuesta.PENDIENTE
    declarado: bool = False

    @property
    def clave(self) -> str:
        """El id de la fila que crea (`BAN-01`, `P1`, `R-P1`) o el codigo de la partida."""
        fila = self.filas[0]
        if self.tipo is TipoPropuesta.RECORRIDO:
            return (
                fila.get("recorrido_id") or f"R-{fila.get('punto_id') or fila.get('circuito_id')}"
            )
        if self.tipo is TipoPropuesta.PARTIDA:
            return fila["codigo"]
        return fila.get("id") or fila.get("necesidad", "")


@dataclass(frozen=True, slots=True)
class OrigenIA:
    proveedor: str
    modelo: str
    sesion: int


def id_de_origen(origen: OrigenIA, propuesta: Propuesta) -> str:
    return f"IA-{origen.sesion}-{propuesta.id}"


def id_de_item(origen: OrigenIA, propuesta: Propuesta) -> str:
    return f"{PREFIJO_ORIGEN_IA}{origen.sesion}:{propuesta.id}"


def _limpio(texto: str) -> str:
    """La referencia de un origen se escribe `k=v; k=v`: ni «;» ni «=» pueden venir en el valor."""
    return texto.replace(";", ",").replace("=", ":").strip()


def referencia_de(origen: OrigenIA, propuesta: Propuesta) -> dict[str, str]:
    referencia = {
        "proveedor": _limpio(origen.proveedor),
        "modelo": _limpio(origen.modelo),
        "sesion": str(origen.sesion),
        "propuesta": propuesta.id,
    }
    for campo, motivo in propuesta.supuestos:
        referencia[f"supuesto.{campo}"] = _limpio(motivo)
    return referencia


def _texto_de(referencia: Mapping[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in sorted(referencia.items()))


def aplicar(
    borrador: Borrador,
    propuestas: Sequence[Propuesta],
    origen: OrigenIA,
    catalogo: CatalogoVista,
) -> Borrador:
    """El borrador con `propuestas` aplicadas, o `HojaInvalida` si la hoja no las construye.

    No toca el `borrador` recibido (es inmutable). Las `SIN_PARTIDA` no cambian el borrador.
    """
    filas = filas_desde_espacio(borrador.espacio)
    propuestos: list[Recorrido] = []
    items = list(borrador.items_base)
    for propuesta in propuestas:
        if propuesta.tipo is TipoPropuesta.SIN_PARTIDA:
            continue
        if propuesta.tipo is TipoPropuesta.PARTIDA:
            items.append(_item(propuesta, origen, catalogo))
            continue
        if propuesta.tipo is TipoPropuesta.RECORRIDO:  # un recorrido no tiene origen de medida
            if propuesta.declarado:
                filas["tramos"].extend(dict(f) for f in propuesta.filas)
            else:
                fila = propuesta.filas[0]
                propuestos.append(
                    Recorrido(
                        id=propuesta.clave,
                        modo=ModoRecorrido.PROPUESTO,
                        punto_id=fila.get("punto_id") or None,
                        circuito_id=fila.get("circuito_id") or None,
                    )
                )
            continue
        oid = id_de_origen(origen, propuesta)
        filas["origenes"].append(
            {"id": oid, "tipo": "ia", "referencia": _texto_de(referencia_de(origen, propuesta))}
        )
        filas[TABLA_DE[propuesta.tipo]].append({**propuesta.filas[0], "origen_id": oid})
    espacio = espacio_desde_filas(filas, base=borrador.espacio)
    if propuestos:
        try:
            espacio = replace(espacio, recorridos=(*espacio.recorridos, *propuestos))
        except ValueError as error:
            raise HojaInvalida(str(error)) from error
    return replace(borrador, espacio=espacio, items_base=tuple(items))


def _item(propuesta: Propuesta, origen: OrigenIA, catalogo: CatalogoVista) -> ItemComputo:
    fila = propuesta.filas[0]
    partida = catalogo.partida(fila["codigo"])
    if partida is None:
        raise HojaInvalida(f"la partida {fila['codigo']!r} no esta en el catalogo")
    return ItemComputo(
        codigo_partida=partida.codigo,
        descripcion=partida.descripcion,
        unidad=fila["unidad"],
        cantidad=Decimal(fila["cantidad"]),
        origen_id=id_de_item(origen, propuesta),
        origen_tipo=OrigenTipo.MANUAL,
        dominio=partida.dominio,
    )


@dataclass(slots=True)
class Pendientes:
    """La lista mutable de propuestas de UNA sesion: agregar, retirar, decidir."""

    propuestas: list[Propuesta]

    @classmethod
    def vacia(cls) -> Pendientes:
        return cls([])

    def siguiente_id(self) -> str:
        return f"P{len(self.propuestas) + 1}"

    def agregar(self, propuesta: Propuesta) -> None:
        self.propuestas.append(propuesta)

    def vigentes(self) -> tuple[Propuesta, ...]:
        return tuple(p for p in self.propuestas if p.estado is EstadoPropuesta.PENDIENTE)

    def buscar(self, propuesta_id: str) -> Propuesta | None:
        return next((p for p in self.propuestas if p.id == propuesta_id), None)

    def retirar(self, propuesta_id: str) -> bool:
        """True si habia una pendiente con ese id: la marca RECHAZADA."""
        return self.marcar(propuesta_id, EstadoPropuesta.RECHAZADA)

    def marcar(self, propuesta_id: str, estado: EstadoPropuesta) -> bool:
        for i, propuesta in enumerate(self.propuestas):
            if propuesta.id == propuesta_id and propuesta.estado is EstadoPropuesta.PENDIENTE:
                self.propuestas[i] = replace(propuesta, estado=estado)
                return True
        return False

    def aceptadas(self) -> tuple[Propuesta, ...]:
        return tuple(
            p
            for p in self.propuestas
            if p.estado in (EstadoPropuesta.ACEPTADA, EstadoPropuesta.EDITADA)
        )
