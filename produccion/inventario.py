"""Servicio de inventario de la arenera: materiales, movimientos, existencia y tablero.

Las cantidades estan como texto en la base, asi que toda suma se hace en Python con `Decimal`.
La validacion de entradas es de este servicio (la DDL no la hace). El servicio hace `flush`;
quien llama decide el `commit`. Un despacho nunca se bloquea por dejar la existencia negativa
(RT-S4-2): se registra y el tablero lo marca.

Un conteo fisico cierra el pasado de su material (prueba en vivo 2026-11-18): el ajuste guarda la
diferencia con la existencia del dia en que se registra, asi que un movimiento con fecha anterior o
igual registrado despues cambiaria la existencia posterior al conteo. Se niega, como en el cierre de
inventario de un ERP; un reconteo el mismo dia si se admite (ve todo lo de esa fecha).

Un conteo mal hecho se anula (tanda 2026-11-19) sin borrar nada: la anulacion es otro ajuste, con
la cantidad contraria, la fecha del conteo, `anula_id` y el motivo, asi que la existencia vuelve a
la de antes del conteo. El conteo anulado y su anulacion no cuentan como conteo: el pasado lo
cierra el anterior no anulado. Solo se anula el ultimo conteo vigente del material: el siguiente se
calculo sobre la existencia que el incluia y quedaria mal.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from produccion.costos import validar_periodo
from produccion.fuentes import CUANTO_T_A_M3
from produccion.modelo import Material, Movimiento

UNIDADES_VALIDAS = ("m3", "t")
CERO = Decimal(0)
LARGO_DEL_MOTIVO = 300  # el de prod_movimiento.motivo
YA_ANULADO = "Ese conteo físico ya fue anulado."


class ErrorDeInventario(ValueError):  # noqa: N818 - nombre fijado por el plan
    """Dato de inventario invalido; el mensaje esta escrito para el usuario."""


class Conflicto(ErrorDeInventario):
    """El dato choca con uno ya registrado (codigo o ticket repetido): la API lo responde 409."""


class ConteoInexistente(ErrorDeInventario):
    """No hay un conteo fisico con ese numero: la API lo responde 404."""


@dataclass(frozen=True, slots=True)
class FilaExistencia:
    material: Material
    existencia: Decimal
    minima: Decimal
    queda_poco: bool
    negativa: bool
    conteo: Movimiento | None = None  # el conteo vigente, el unico que se puede anular


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


def _exigir_positiva(cantidad: Decimal, de_que: str) -> None:
    """`de_que` es la frase que sigue a «La cantidad»: «de la entrada», «del consumo»."""
    if not isinstance(cantidad, Decimal) or not cantidad.is_finite() or cantidad <= CERO:
        raise ErrorDeInventario(f"La cantidad {de_que} debe ser un número mayor que cero.")


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


def _conteos_vigentes(material_id: int):
    """Los conteos (ajustes) del material que no son una anulacion ni estan anulados."""
    anulacion = aliased(Movimiento)
    return select(Movimiento).where(
        Movimiento.material_id == material_id,
        Movimiento.tipo == "ajuste",
        Movimiento.anula_id.is_(None),
        ~select(anulacion.id).where(anulacion.anula_id == Movimiento.id).exists(),
    )


def conteo_vigente(sesion: Session, material_id: int) -> Movimiento | None:
    """El ultimo conteo fisico no anulado del material (fecha mayor y, en la misma fecha, el
    registrado despues), o `None`."""
    return sesion.scalar(
        _conteos_vigentes(material_id)
        .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
        .limit(1)
    )


def abrir_transaccion(sesion: Session) -> None:
    """Deja abierta la transaccion de la conexion antes de un `begin_nested()`.

    `pysqlite` solo emite `BEGIN` antes de un `INSERT`/`UPDATE`/`DELETE`, no antes de un
    `SAVEPOINT`: con una sesion sin escrituras previas, el `RELEASE` del savepoint mas externo
    confirma todo y un `rollback` posterior del llamador no deshace nada. Con un `BEGIN` previo, el
    savepoint queda anidado y quien llama conserva la decision de confirmar o deshacer."""
    conexion = sesion.connection()
    crudo = conexion.connection.dbapi_connection
    if not getattr(crudo, "in_transaction", True):
        conexion.exec_driver_sql("BEGIN")


def ultimo_conteo(sesion: Session, material_id: int) -> date | None:
    """La fecha del ultimo conteo fisico no anulado del material, o `None` si no hay ninguno."""
    conteo = conteo_vigente(sesion, material_id)
    return None if conteo is None else conteo.fecha


def exigir_fecha_abierta(sesion: Session, material: Material, fecha: date) -> None:
    """`ErrorDeInventario` si `fecha` no pasa del ultimo conteo fisico de `material`: ese conteo
    cerro su pasado. Lo usan todos los movimientos menos el propio conteo."""
    exigir_fechas_abiertas(sesion, [material], fecha)


def exigir_fechas_abiertas(sesion: Session, materiales: Sequence[Material], fecha: date) -> None:
    """`exigir_fecha_abierta` para varios materiales a la vez (producir): si mas de uno esta
    cerrado en `fecha`, nombra el cierre mas tardio, que es el que obliga a mover la fecha
    (arbitraje 2026-11-18)."""
    cierres = [
        (cerrado, material)
        for material in materiales
        if (cerrado := ultimo_conteo(sesion, material.id)) is not None and fecha <= cerrado
    ]
    if cierres:
        cerrado, material = max(cierres, key=lambda par: par[0])
        raise ErrorDeInventario(
            f"El material {material.codigo} tiene un conteo físico del {cerrado:%d/%m/%Y}, que "
            f"cerró su existencia hasta ese día: registre el movimiento con una fecha posterior al "
            f"{cerrado:%d/%m/%Y} o, si el conteo estaba mal, anúlelo en «Existencias» con su "
            "motivo."
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
    anula_id: int | None = None,
    motivo: str = "",
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
        anula_id=anula_id,
        motivo=motivo,
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
    _exigir_positiva(cantidad, "de la entrada")
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
    _exigir_positiva(cantidad, "del consumo")
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
    _exigir_positiva(cantidad, "del despacho")
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
    hoy: date | None = None,
) -> Movimiento:
    """Guarda el conteo como un ajuste con la diferencia contra la existencia a `fecha`. Un conteo
    que coincide tambien se guarda (ajuste en 0, arbitraje 2026-11-18): es el que cierra el pasado
    del material. Un conteo con fecha posterior a `hoy` (la del equipo si no se da) se niega:
    cerraria el material hasta esa fecha sin salida."""
    if (
        not isinstance(conteo_fisico, Decimal)
        or not conteo_fisico.is_finite()
        or conteo_fisico < CERO
    ):
        raise ErrorDeInventario("El conteo físico debe ser un número de cero o más.")
    material = _material(sesion, material_id)
    hoy = date.today() if hoy is None else hoy
    if fecha > hoy:
        raise ErrorDeInventario(
            f"El conteo físico no puede tener fecha futura: el {fecha:%d/%m/%Y} es posterior a hoy "
            f"({hoy:%d/%m/%Y}). Registre el conteo el día en que se hizo."
        )
    anterior = ultimo_conteo(sesion, material_id)
    if anterior is not None and fecha < anterior:
        raise ErrorDeInventario(
            f"El material {material.codigo} ya tiene un conteo físico del {anterior:%d/%m/%Y}: un "
            f"conteo nuevo va en esa fecha o después."
        )
    diferencia = conteo_fisico - existencia(sesion, material_id, fecha)
    if diferencia == CERO:
        diferencia = CERO  # «0», no «0.0» ni «-0»
    return _registrar(sesion, material_id, fecha, "ajuste", diferencia, usuario=usuario, nota=nota)


def anular_conteo(
    sesion: Session, movimiento_id: int, *, motivo: str, usuario: str, ahora: datetime
) -> Movimiento:
    """Anula el conteo fisico `movimiento_id` con un ajuste nuevo que lo compensa (misma fecha,
    cantidad contraria, `anula_id` y `motivo`) y lo devuelve; el conteo no cambia. Lo que no es un
    conteo: `ConteoInexistente`. Ya anulado, una anulacion o no el ultimo conteo vigente del
    material: `Conflicto`. Sin motivo o con mas de `LARGO_DEL_MOTIVO` caracteres, el error lo
    dice."""
    motivo = motivo.strip()
    if not motivo:
        raise ErrorDeInventario("Escriba el motivo de la anulación del conteo.")
    if len(motivo) > LARGO_DEL_MOTIVO:
        raise ErrorDeInventario(
            f"El motivo de la anulación admite hasta {LARGO_DEL_MOTIVO} caracteres."
        )
    conteo = sesion.get(Movimiento, movimiento_id)
    if conteo is None or conteo.tipo != "ajuste":
        raise ConteoInexistente("No existe ese conteo físico. Actualice la existencia.")
    if conteo.anula_id is not None:
        raise Conflicto("Ese movimiento es la anulación de un conteo: no se anula.")
    if sesion.scalar(select(Movimiento.id).where(Movimiento.anula_id == conteo.id)) is not None:
        raise Conflicto(YA_ANULADO)
    vigente = conteo_vigente(sesion, conteo.material_id)
    if vigente is None or vigente.id != conteo.id:
        raise Conflicto(_no_es_el_ultimo(sesion, conteo, vigente))
    contraria = -conteo.cantidad
    if contraria == CERO:
        contraria = CERO  # «0», no «-0»
    # Otra anulacion del mismo conteo que gano la carrera despues de las comprobaciones: el indice
    # unico de `anula_id` frena esta; se deshace solo su savepoint (arbitraje 2026-11-19).
    abrir_transaccion(sesion)
    try:
        with sesion.begin_nested():
            return _registrar(
                sesion,
                conteo.material_id,
                conteo.fecha,
                "ajuste",
                contraria,
                usuario=usuario,
                ahora=ahora,
                anula_id=conteo.id,
                motivo=motivo,
            )
    except IntegrityError:
        raise Conflicto(YA_ANULADO) from None


def _no_es_el_ultimo(sesion: Session, conteo: Movimiento, vigente: Movimiento | None) -> str:
    """Por que `conteo` no se anula: no hay conteo vigente (otra anulacion lo dejo sin el) u otro
    lo sigue; si es del mismo dia, se dice a que hora se registro el que va despues."""
    if vigente is None:
        return YA_ANULADO
    codigo = _material(sesion, conteo.material_id).codigo
    if vigente.fecha == conteo.fecha:
        return (
            f"Solo se puede anular el último conteo vigente de {codigo}: el "
            f"{vigente.fecha:%d/%m/%Y} hay otro registrado después, a las "
            f"{vigente.registrado:%H:%M}. Anule primero ese."
        )
    return (
        f"Solo se puede anular el último conteo vigente de {codigo}, que es el del "
        f"{vigente.fecha:%d/%m/%Y}: anule primero ese."
    )


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
                conteo=conteo_vigente(sesion, material.id),
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
