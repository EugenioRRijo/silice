"""Receta de la planta y consumos al producir mezcla (Tarea 3 del plan vial).

Dominio puro: solo biblioteca estandar, SQLAlchemy y `produccion.*`. Una receta dice que lleva una
tonelada de un producto (agregado propio, material comprado, combustible). Nada se sobrescribe: una
receta nueva es un registro nuevo y rige desde su `vigente_desde`; la de una fecha es la de
`vigente_desde` mas reciente que no pase de esa fecha (a igual fecha, la registrada despues). El
servicio hace `flush`; quien llama decide el `commit`.

Producir con receta registra la entrada del producto y un `consumo` por cada componente propio, en
la unidad de venta de ese material. Lo comprado no toca el inventario de la arenera.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from produccion.fuentes import TOLERANCIA_MASA
from produccion.inventario import (
    CERO,
    ErrorDeInventario,
    de_toneladas,
    producido_en_periodo,
    registrar_consumo,
    registrar_entrada,
)
from produccion.modelo import Material, RecetaComponente, RecetaRegistrada

__all__ = [
    "TOLERANCIA_MASA",
    "Componente",
    "ErrorDeReceta",
    "Receta",
    "producido_en_periodo",
    "producir_con_receta",
    "receta_vigente",
    "registrar_receta",
]

TIPOS = ("propio", "comprado")
UNIDADES = ("t", "l")
UNO = Decimal(1)


class ErrorDeReceta(ErrorDeInventario):
    """Dato de receta invalido, o producir sin receta: el mensaje esta escrito para el usuario."""


def _es_fecha(fecha: object) -> bool:
    return isinstance(fecha, date) and not isinstance(fecha, datetime)


@dataclass(frozen=True)
class Componente:
    codigo: str
    cantidad_por_t: Decimal
    unidad: str
    tipo: str

    def __post_init__(self) -> None:
        if not isinstance(self.codigo, str) or not self.codigo.strip():
            raise ErrorDeReceta("Indique el código del componente.")
        object.__setattr__(self, "codigo", self.codigo.strip())
        if self.unidad not in UNIDADES:
            raise ErrorDeReceta(f"La unidad de {self.codigo} debe ser t o l.")
        if self.tipo not in TIPOS:
            raise ErrorDeReceta(f"El tipo de {self.codigo} debe ser propio o comprado.")
        if (
            not isinstance(self.cantidad_por_t, Decimal)
            or not self.cantidad_por_t.is_finite()
            or self.cantidad_por_t <= CERO
        ):
            raise ErrorDeReceta(
                f"La cantidad por tonelada de {self.codigo} debe ser un número mayor que cero."
            )
        if self.tipo == "propio" and self.unidad != "t":
            raise ErrorDeReceta(
                f"El componente propio {self.codigo} sale del inventario y va en t, no en l."
            )


@dataclass(frozen=True)
class Receta:
    id: int
    producto: str
    componentes: tuple[Componente, ...]
    fuente: str
    vigente_desde: date


def _coma(valor: Decimal) -> str:
    return format(valor, "f").replace(".", ",")


def registrar_receta(
    sesion: Session,
    producto: str,
    componentes: Sequence[Componente],
    *,
    fuente: str,
    vigente_desde: date,
    usuario: str,
    ahora: datetime,
) -> int:
    """Inserta la receta y devuelve su numero. Las toneladas de componentes (`unidad` t) por
    tonelada de mezcla deben sumar 1 con la tolerancia `TOLERANCIA_MASA`; los litros no cuentan."""
    producto = producto.strip()
    if not producto:
        raise ErrorDeReceta("Indique el producto de la receta.")
    if not fuente.strip():
        raise ErrorDeReceta("Indique la fuente de la receta (por ejemplo, la dosificación).")
    if not usuario.strip():
        raise ErrorDeReceta("Falta el usuario que registra la receta.")
    if not _es_fecha(vigente_desde):
        raise ErrorDeReceta("La fecha desde la que rige la receta debe ser una fecha.")
    if not componentes:
        raise ErrorDeReceta("La receta necesita al menos un componente.")
    codigos = [c.codigo for c in componentes]
    repetidos = sorted(c for c, veces in Counter(codigos).items() if veces > 1)
    if repetidos:
        raise ErrorDeReceta(f"Componente repetido en la receta: {', '.join(repetidos)}.")
    masa = sum((c.cantidad_por_t for c in componentes if c.unidad == "t"), CERO)
    if abs(masa - UNO) > TOLERANCIA_MASA:
        raise ErrorDeReceta(
            f"Los componentes en toneladas deben sumar 1 t por t de mezcla "
            f"(con {_coma(TOLERANCIA_MASA)} de tolerancia); suman {_coma(masa)} t."
        )
    fila = RecetaRegistrada(
        producto=producto,
        fuente=fuente.strip(),
        vigente_desde=vigente_desde,
        usuario=usuario,
        registrado=ahora,
    )
    sesion.add(fila)
    sesion.flush()
    for orden, c in enumerate(componentes):
        sesion.add(
            RecetaComponente(
                receta_id=fila.id,
                orden=orden,
                codigo=c.codigo,
                cantidad_por_t=c.cantidad_por_t,
                unidad=c.unidad,
                tipo=c.tipo,
            )
        )
    sesion.flush()
    return fila.id


def receta_vigente(sesion: Session, producto: str, fecha: date) -> Receta | None:
    """La receta que rige para `producto` en `fecha`, o `None` si no hay ninguna."""
    fila = sesion.scalars(
        select(RecetaRegistrada)
        .where(
            RecetaRegistrada.producto == producto.strip(), RecetaRegistrada.vigente_desde <= fecha
        )
        .order_by(RecetaRegistrada.vigente_desde.desc(), RecetaRegistrada.id.desc())
        .limit(1)
    ).first()
    if fila is None:
        return None
    componentes = sesion.scalars(
        select(RecetaComponente)
        .where(RecetaComponente.receta_id == fila.id)
        .order_by(RecetaComponente.orden)
    )
    return Receta(
        id=fila.id,
        producto=fila.producto,
        componentes=tuple(
            Componente(c.codigo, c.cantidad_por_t, c.unidad, c.tipo) for c in componentes
        ),
        fuente=fila.fuente,
        vigente_desde=fila.vigente_desde,
    )


def _material(sesion: Session, codigo: str) -> Material:
    material = sesion.scalar(select(Material).where(Material.codigo == codigo))
    if material is None:
        raise ErrorDeReceta(
            f"No existe el material {codigo}. Créelo en la lista de materiales antes de producir."
        )
    return material


def producir_con_receta(
    sesion: Session,
    producto: str,
    toneladas: Decimal,
    fecha: date,
    *,
    usuario: str,
    ahora: datetime,
) -> list[int]:
    """Registra la produccion de `toneladas` del producto (una entrada) y un consumo por cada
    componente propio de la receta vigente en `fecha`. Devuelve los numeros de los movimientos: la
    entrada primero y luego los consumos en el orden de la receta. Todo se valida antes de
    escribir."""
    if not isinstance(toneladas, Decimal) or not toneladas.is_finite() or toneladas <= CERO:
        raise ErrorDeReceta("Las toneladas a producir deben ser un número mayor que cero.")
    producto = producto.strip()
    receta = receta_vigente(sesion, producto, fecha)
    if receta is None:
        raise ErrorDeReceta(
            f"No hay receta vigente de {producto} el {fecha.isoformat()}. "
            "Registre la receta antes de producir."
        )
    material_producto = _material(sesion, producto)
    consumos: list[tuple[Material, Decimal]] = []
    for c in receta.componentes:
        if c.tipo == "propio":
            material = _material(sesion, c.codigo)
            consumos.append((material, de_toneladas(material, c.cantidad_por_t * toneladas)))
    nota = f"receta {receta.id}"
    entrada = registrar_entrada(
        sesion,
        material_producto.id,
        fecha,
        de_toneladas(material_producto, toneladas),
        usuario=usuario,
        nota=nota,
        ahora=ahora,
    )
    ids = [entrada.id]
    for material, cantidad in consumos:
        consumo = registrar_consumo(
            sesion, material.id, fecha, cantidad, usuario=usuario, ahora=ahora, nota=nota
        )
        ids.append(consumo.id)
    return ids
