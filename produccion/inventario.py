"""Servicio de inventario de la arenera: materiales, movimientos, existencia y tablero.

Las cantidades estan como texto en la base, asi que toda suma se hace en Python con `Decimal`.
La validacion de entradas es de este servicio (la DDL no la hace). El servicio hace `flush`;
quien llama decide el `commit`. Un despacho nunca se bloquea por dejar la existencia negativa
(RT-S4-2): se registra y el tablero lo marca.

Un conteo fisico cierra el pasado de su material (prueba en vivo 2026-11-18): el ajuste guarda la
diferencia con la existencia del dia en que se registra, asi que un movimiento con fecha anterior o
igual registrado despues cambiaria la existencia posterior al conteo. Se niega, como en el cierre de
inventario de un ERP; un reconteo el mismo dia si se admite (ve todo lo de esa fecha).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from produccion.costos import validar_periodo
from produccion.fuentes import CUANTO_T_A_M3
from produccion.modelo import Material, Movimiento

UNIDADES_VALIDAS = ("m3", "t")
CERO = Decimal(0)


class ErrorDeInventario(ValueError):  # noqa: N818 - nombre fijado por el plan
    """Dato de inventario invalido; el mensaje esta escrito para el usuario."""


class Conflicto(ErrorDeInventario):
    """El dato choca con uno ya registrado (codigo o ticket repetido): la API lo responde 409."""


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
    material = material_por_id(sesion, material_id)
    if material is None:
        raise ErrorDeInventario("No existe ese material. Elija uno de la lista de materiales.")
    return material


def material_por_id(sesion: Session, material_id: int) -> Material | None:
    """El material de ese `id`, o `None`."""
    return sesion.get(Material, material_id)


def material_por_codigo(sesion: Session, codigo: str) -> Material | None:
    """El material de ese codigo exacto (sin los blancos de los extremos), o `None`."""
    return sesion.scalar(select(Material).where(Material.codigo == codigo.strip()))


def materiales(sesion: Session) -> list[Material]:
    """Los materiales de la arenera, activos o no, por codigo."""
    return list(sesion.scalars(select(Material).order_by(Material.codigo)))


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
        raise Conflicto(f"Ya existe un material con el código {codigo}.")
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


def ultimo_conteo(sesion: Session, material_id: int) -> date | None:
    """La fecha del ultimo conteo fisico (ajuste) del material, o `None` si nunca se conto."""
    return sesion.scalar(
        select(func.max(Movimiento.fecha)).where(
            Movimiento.material_id == material_id, Movimiento.tipo == "ajuste"
        )
    )


def exigir_fecha_abierta(sesion: Session, material: Material, fecha: date) -> None:
    """`ErrorDeInventario` si `fecha` no pasa del ultimo conteo fisico de `material`: ese conteo
    cerro su pasado. Lo usan todos los movimientos menos el propio conteo."""
    cerrado = ultimo_conteo(sesion, material.id)
    if cerrado is not None and fecha <= cerrado:
        raise ErrorDeInventario(
            f"El material {material.codigo} tiene un conteo físico del {cerrado:%d/%m/%Y}, que "
            f"cerró su existencia hasta ese día: registre el movimiento con una fecha posterior al "
            f"{cerrado:%d/%m/%Y} o, si el conteo estaba mal, haga un conteo nuevo."
        )


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
    ahora: datetime | None = None,
) -> Movimiento:
    material = _material(sesion, material_id)
    if tipo != "ajuste":
        exigir_fecha_abierta(sesion, material, fecha)
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
        registrado=_ahora() if ahora is None else ahora,
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
    ahora: datetime | None = None,
) -> Movimiento:
    _exigir_positiva(cantidad, "la entrada")
    return _registrar(
        sesion, material_id, fecha, "entrada", cantidad, usuario=usuario, nota=nota, ahora=ahora
    )


def registrar_consumo(
    sesion: Session,
    material_id: int,
    fecha: date,
    cantidad: Decimal,
    *,
    usuario: str,
    ahora: datetime,
    nota: str = "",
) -> Movimiento:
    """Lo que la planta gasta de un material propio al producir (plan vial, Tarea 3). Se guarda en
    positivo, como el despacho, y resta de la existencia."""
    _exigir_positiva(cantidad, "el consumo")
    return _registrar(
        sesion, material_id, fecha, "consumo", cantidad, usuario=usuario, nota=nota, ahora=ahora
    )


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
        raise Conflicto(f"El ticket {ticket} ya está registrado.")
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
    material = _material(sesion, material_id)
    anterior = ultimo_conteo(sesion, material_id)
    if anterior is not None and fecha < anterior:
        raise ErrorDeInventario(
            f"El material {material.codigo} ya tiene un conteo físico del {anterior:%d/%m/%Y}: un "
            f"conteo nuevo va en esa fecha o después."
        )
    diferencia = conteo_fisico - existencia(sesion, material_id, fecha)
    if diferencia == CERO:
        return None
    return _registrar(sesion, material_id, fecha, "ajuste", diferencia, usuario=usuario, nota=nota)


def _neto(movimiento: Movimiento) -> Decimal:
    if movimiento.tipo == "entrada":
        return movimiento.cantidad
    if movimiento.tipo in ("despacho", "consumo"):
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


def a_toneladas(material: Material, cantidad: Decimal) -> Decimal:
    """`cantidad` en la unidad de venta del material, en toneladas (m3 x densidad). Un material en
    m3 sin densidad no se puede convertir: error que lo nombra."""
    if material.unidad_venta == "t":
        return cantidad
    if material.densidad_t_m3 is None:
        raise ErrorDeInventario(
            f"El material {material.codigo} está en m3 y no tiene densidad (t/m3): "
            "indíquela para pasarlo a toneladas."
        )
    return cantidad * material.densidad_t_m3


def de_toneladas(material: Material, toneladas: Decimal) -> Decimal:
    """Toneladas a la unidad de venta del material: la misma en t; en m3, t / densidad a cuatro
    decimales con redondeo de mitad al par. Es la UNICA regla de esta conversion (la usan la
    importacion de bascula y los consumos de la receta). Sin densidad (o no positiva): error."""
    if material.unidad_venta == "t":
        return toneladas
    if material.densidad_t_m3 is None or material.densidad_t_m3 <= CERO:
        raise ErrorDeInventario(
            f"El material {material.codigo} está en m3 y no tiene densidad (t/m3): "
            "indíquela para pasarlo desde toneladas."
        )
    return (toneladas / material.densidad_t_m3).quantize(CUANTO_T_A_M3, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class EntradaDelPeriodo:
    """Una entrada (produccion) del periodo: codigo del material, su fecha y sus toneladas."""

    codigo: str
    fecha: date
    toneladas: Decimal


def entradas_del_periodo(sesion: Session, periodo: str) -> list[EntradaDelPeriodo]:
    """Las entradas del periodo `AAAA-MM`, una por movimiento, en toneladas (m3 x densidad; un
    material en m3 sin densidad es error que lo nombra). Los despachos, ajustes y consumos no
    cuentan. Orden: codigo del material y luego orden de registro."""
    anio, mes = validar_periodo(periodo)
    desde = date(anio, mes, 1)
    hasta = date(anio + (mes == 12), mes % 12 + 1, 1)
    consulta = (
        select(Movimiento, Material)
        .join(Material, Material.id == Movimiento.material_id)
        .where(Movimiento.tipo == "entrada", Movimiento.fecha >= desde, Movimiento.fecha < hasta)
        .order_by(Material.codigo, Movimiento.id)
    )
    return [
        EntradaDelPeriodo(
            material.codigo, movimiento.fecha, a_toneladas(material, movimiento.cantidad)
        )
        for movimiento, material in sesion.execute(consulta)
    ]


def producido_en_periodo(sesion: Session, periodo: str) -> dict[str, Decimal]:
    """Toneladas producidas en el periodo `AAAA-MM` por código de material: la suma de sus
    entradas del mes (`entradas_del_periodo`). Ordenado por código; un material sin entradas en el
    mes no aparece."""
    sumas: dict[str, Decimal] = {}
    for entrada in entradas_del_periodo(sesion, periodo):
        sumas[entrada.codigo] = sumas.get(entrada.codigo, CERO) + entrada.toneladas
    return sumas
