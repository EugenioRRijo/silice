"""Servicio de inventario de la arenera: materiales, movimientos, existencia y tablero.

Las cantidades estan como texto en la base, asi que toda suma se hace en Python con `Decimal`.
La validacion de entradas es de este servicio (la DDL no la hace). El servicio hace `flush`;
quien llama decide el `commit`. Un despacho nunca se bloquea por dejar la existencia negativa
(RT-S4-2): se registra y el tablero lo marca.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from produccion.modelo import Material, Movimiento

UNIDADES_VALIDAS = ("m3", "t")
CERO = Decimal(0)


class ErrorDeInventario(ValueError):  # noqa: N818 - nombre fijado por el plan
    """Dato de inventario invalido; el mensaje esta escrito para el usuario."""


@dataclass(frozen=True, slots=True)
class FilaExistencia:
    material: Material
    existencia: Decimal
    minima: Decimal
    queda_poco: bool
    negativa: bool


def _ahora() -> datetime:
    return datetime.now().replace(microsecond=0)


def _material(sesion: Session, material_id: int) -> Material:
    material = sesion.get(Material, material_id)
    if material is None:
        raise ErrorDeInventario("No existe ese material. Elija uno de la lista de materiales.")
    return material


def _exigir_positiva(cantidad: Decimal, que: str) -> None:
    if not isinstance(cantidad, Decimal) or not cantidad.is_finite() or cantidad <= CERO:
        raise ErrorDeInventario(f"La cantidad de {que} debe ser un número mayor que cero.")


def crear_material(
    sesion: Session,
    *,
    codigo: str,
    nombre: str,
    unidad_venta: str,
    existencia_minima: Decimal,
    densidad_t_m3: Decimal | None = None,
) -> Material:
    codigo = codigo.strip()
    nombre = nombre.strip()
    if not codigo or not nombre:
        raise ErrorDeInventario("Indique el código y el nombre del material.")
    if unidad_venta not in UNIDADES_VALIDAS:
        raise ErrorDeInventario("La unidad de venta debe ser m3 o t.")
    if (
        not isinstance(existencia_minima, Decimal)
        or not existencia_minima.is_finite()
        or existencia_minima < CERO
    ):
        raise ErrorDeInventario("La existencia mínima debe ser un número de cero o más.")
    if densidad_t_m3 is not None and (
        not isinstance(densidad_t_m3, Decimal)
        or not densidad_t_m3.is_finite()
        or densidad_t_m3 <= CERO
    ):
        raise ErrorDeInventario("La densidad (t/m3) debe ser un número mayor que cero.")
    if sesion.scalar(select(Material.id).where(Material.codigo == codigo)) is not None:
        raise ErrorDeInventario(f"Ya existe un material con el código {codigo}.")
    material = Material(
        codigo=codigo,
        nombre=nombre,
        unidad_venta=unidad_venta,
        densidad_t_m3=densidad_t_m3,
        existencia_minima=existencia_minima,
        activo=True,
    )
    sesion.add(material)
    sesion.flush()
    return material


def _registrar(
    sesion: Session,
    material_id: int,
    fecha: date,
    tipo: str,
    cantidad: Decimal,
    *,
    usuario: str,
    ticket: str | None = None,
    placa: str = "",
    cliente: str = "",
    origen: str = "manual",
    nota: str = "",
) -> Movimiento:
    _material(sesion, material_id)
    movimiento = Movimiento(
        material_id=material_id,
        fecha=fecha,
        tipo=tipo,
        cantidad=cantidad,
        ticket=ticket,
        placa=placa,
        cliente=cliente,
        nota=nota,
        origen=origen,
        usuario=usuario,
        registrado=_ahora(),
    )
    sesion.add(movimiento)
    sesion.flush()
    return movimiento


def registrar_entrada(
    sesion: Session,
    material_id: int,
    fecha: date,
    cantidad: Decimal,
    *,
    usuario: str,
    nota: str = "",
) -> Movimiento:
    _exigir_positiva(cantidad, "la entrada")
    return _registrar(sesion, material_id, fecha, "entrada", cantidad, usuario=usuario, nota=nota)


def registrar_despacho(
    sesion: Session,
    material_id: int,
    fecha: date,
    cantidad: Decimal,
    *,
    usuario: str,
    ticket: str | None = None,
    placa: str = "",
    cliente: str = "",
    origen: str = "manual",
    nota: str = "",
) -> Movimiento:
    _exigir_positiva(cantidad, "el despacho")
    if ticket is not None and (
        sesion.scalar(select(Movimiento.id).where(Movimiento.ticket == ticket)) is not None
    ):
        raise ErrorDeInventario(f"El ticket {ticket} ya está registrado.")
    return _registrar(
        sesion,
        material_id,
        fecha,
        "despacho",
        cantidad,
        usuario=usuario,
        ticket=ticket,
        placa=placa,
        cliente=cliente,
        origen=origen,
        nota=nota,
    )


def registrar_ajuste_por_conteo(
    sesion: Session,
    material_id: int,
    fecha: date,
    conteo_fisico: Decimal,
    *,
    usuario: str,
    nota: str = "",
) -> Movimiento | None:
    if (
        not isinstance(conteo_fisico, Decimal)
        or not conteo_fisico.is_finite()
        or conteo_fisico < CERO
    ):
        raise ErrorDeInventario("El conteo físico debe ser un número de cero o más.")
    diferencia = conteo_fisico - existencia(sesion, material_id, fecha)
    if diferencia == CERO:
        return None
    return _registrar(sesion, material_id, fecha, "ajuste", diferencia, usuario=usuario, nota=nota)


def _neto(movimiento: Movimiento) -> Decimal:
    if movimiento.tipo == "entrada":
        return movimiento.cantidad
    if movimiento.tipo == "despacho":
        return -movimiento.cantidad
    return movimiento.cantidad  # ajuste: ya lleva su signo


def existencia(sesion: Session, material_id: int, a_fecha: date | None = None) -> Decimal:
    _material(sesion, material_id)
    consulta = select(Movimiento).where(Movimiento.material_id == material_id)
    if a_fecha is not None:
        consulta = consulta.where(Movimiento.fecha <= a_fecha)
    total = CERO
    for movimiento in sesion.scalars(consulta):
        total += _neto(movimiento)
    return total


def tablero(sesion: Session, a_fecha: date | None = None) -> list[FilaExistencia]:
    filas: list[FilaExistencia] = []
    materiales = sesion.scalars(
        select(Material).where(Material.activo.is_(True)).order_by(Material.codigo)
    )
    for material in materiales:
        actual = existencia(sesion, material.id, a_fecha)
        filas.append(
            FilaExistencia(
                material=material,
                existencia=actual,
                minima=material.existencia_minima,
                queda_poco=actual <= material.existencia_minima,
                negativa=actual < CERO,
            )
        )
    return filas
