"""Importacion idempotente de pesajes de bascula y bandeja de sospechosos (Tarea 4.7).

Convierte una `LecturaBascula` (ya validada en su forma por el lector) en despachos del inventario
y en filas de la bandeja `prod_pesaje_sospechoso`. El lector no conoce el catalogo: aqui se decide
que un pesaje con material que no existe es «material desconocido», y que uno en m3 sin densidad es
«material sin densidad». Nunca se crea un despacho en cero.

Transacciones: este modulo hace `flush`, nunca `commit` (lo decide quien llama). La importacion y la
resolucion corren dentro de `Session.begin_nested()`: si algo falla, se deshace lo que se hizo en
esa llamada y la sesion sigue siendo util.

Idempotencia: un pesaje cuyo ticket ya existe como `Movimiento` cuenta en `ya_registrados` y no se
toca; un dudoso con la misma `(huella, fila)` ya en la bandeja no se vuelve a insertar (y no suma a
`a_la_bandeja`). Solo se consideran materiales activos.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from produccion.conectores.bascula import LecturaBascula, PesajeDudoso, PesajeLeido
from produccion.inventario import ErrorDeInventario, registrar_despacho
from produccion.modelo import Material, Movimiento, PesajeSospechoso

__all__ = [
    "ResultadoImportacion",
    "descartar",
    "importar",
    "pendientes",
    "resolver",
]

MOTIVO_MATERIAL_DESCONOCIDO = "material desconocido"
MOTIVO_SIN_DENSIDAD = "material sin densidad"
MOTIVO_CANTIDAD_EN_CERO = "peso neto en cero"

_CERO = Decimal(0)
_CUATRO_DECIMALES = Decimal("0.0001")
_LOTE_DE_TICKETS = 500


@dataclass(frozen=True, slots=True)
class ResultadoImportacion:
    registrados: int
    ya_registrados: int
    a_la_bandeja: int
    huella: str


# ------------------------------------------------------------------------------------ materiales


def _normalizar(texto: str) -> str:
    """Sin tildes, en minusculas y con los espacios colapsados («  Árena » -> «arena»)."""
    sin_marcas = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", sin_marcas).strip().lower()


class _Catalogo:
    """Materiales activos buscados por codigo o por nombre normalizado (el codigo manda)."""

    def __init__(self, sesion: Session) -> None:
        self._por_codigo: dict[str, Material] = {}
        self._por_nombre: dict[str, Material] = {}
        for material in sesion.scalars(
            select(Material).where(Material.activo.is_(True)).order_by(Material.id)
        ):
            self._por_codigo.setdefault(_normalizar(material.codigo), material)
            self._por_nombre.setdefault(_normalizar(material.nombre), material)

    def buscar(self, texto: str) -> Material | None:
        clave = _normalizar(texto)
        return self._por_codigo.get(clave) or self._por_nombre.get(clave)


def _cantidad_de_despacho(material: Material, neto_t: Decimal) -> tuple[Decimal | None, str]:
    """(cantidad en la unidad de venta del material, "") o (None, motivo de que no se puede)."""
    if material.unidad_venta == "t":
        cantidad = neto_t
    else:
        if material.densidad_t_m3 is None or material.densidad_t_m3 <= _CERO:
            return None, MOTIVO_SIN_DENSIDAD
        cantidad = (neto_t / material.densidad_t_m3).quantize(
            _CUATRO_DECIMALES, rounding=ROUND_HALF_EVEN
        )
    if cantidad <= _CERO:
        return None, MOTIVO_CANTIDAD_EN_CERO
    return cantidad, ""


# -------------------------------------------------------------------------------------- bandeja


def _corto(texto: str, largo: int) -> str:
    return texto[:largo]


def _decimal_legible(valor: Decimal) -> str:
    return format(valor, "f")


def _sospechoso_de_dudoso(huella: str, dudoso: PesajeDudoso) -> PesajeSospechoso:
    return PesajeSospechoso(
        huella_archivo=huella,
        fila=dudoso.fila,
        ticket=_corto(dudoso.ticket, 60),
        fecha_texto=_corto(dudoso.fecha_texto, 60),
        placa=_corto(dudoso.placa, 20),
        material_texto=_corto(dudoso.material, 120),
        bruto_texto=_corto(dudoso.bruto_texto, 60),
        tara_texto=_corto(dudoso.tara_texto, 60),
        neto_texto=_corto(dudoso.neto_texto, 60),
        motivo=_corto(dudoso.motivo, 200),
        estado="pendiente",
    )


def _sospechoso_de_pesaje(huella: str, pesaje: PesajeLeido, motivo: str) -> PesajeSospechoso:
    return PesajeSospechoso(
        huella_archivo=huella,
        fila=pesaje.fila,
        ticket=_corto(pesaje.ticket, 60),
        fecha_texto=pesaje.fecha.isoformat(),
        placa=_corto(pesaje.placa, 20),
        material_texto=_corto(pesaje.material, 120),
        bruto_texto=_decimal_legible(pesaje.bruto_t),
        tara_texto=_decimal_legible(pesaje.tara_t),
        neto_texto=_decimal_legible(pesaje.neto_t),
        motivo=motivo,
        estado="pendiente",
    )


def _tickets_existentes(sesion: Session, pesajes: tuple[PesajeLeido, ...]) -> set[str]:
    tickets = [p.ticket for p in pesajes]
    existentes: set[str] = set()
    for inicio in range(0, len(tickets), _LOTE_DE_TICKETS):
        lote = tickets[inicio : inicio + _LOTE_DE_TICKETS]
        existentes.update(
            sesion.scalars(select(Movimiento.ticket).where(Movimiento.ticket.in_(lote)))
        )
    return existentes


# --------------------------------------------------------------------------------------- API


def importar(sesion: Session, lectura: LecturaBascula, *, usuario: str) -> ResultadoImportacion:
    """Registra los despachos de la lectura y manda lo dudoso a la bandeja, todo o nada.

    No hace `commit`. Si un despacho falla, se deshace todo lo de esta llamada y se propaga el
    `ErrorDeInventario`.
    """
    registrados = 0
    ya_registrados = 0
    a_la_bandeja = 0
    with sesion.begin_nested():
        catalogo = _Catalogo(sesion)
        en_bandeja = set(
            sesion.scalars(
                select(PesajeSospechoso.fila).where(
                    PesajeSospechoso.huella_archivo == lectura.huella
                )
            )
        )
        tickets = _tickets_existentes(sesion, lectura.pesajes)

        def a_bandeja(fila: int, sospechoso: PesajeSospechoso) -> int:
            if fila in en_bandeja:
                return 0
            en_bandeja.add(fila)
            sesion.add(sospechoso)
            return 1

        for dudoso in lectura.dudosos:
            a_la_bandeja += a_bandeja(dudoso.fila, _sospechoso_de_dudoso(lectura.huella, dudoso))

        for pesaje in lectura.pesajes:
            if pesaje.ticket in tickets:
                ya_registrados += 1
                continue
            material = catalogo.buscar(pesaje.material)
            if material is None:
                cantidad, motivo = None, MOTIVO_MATERIAL_DESCONOCIDO
            else:
                cantidad, motivo = _cantidad_de_despacho(material, pesaje.neto_t)
            if material is None or cantidad is None:
                a_la_bandeja += a_bandeja(
                    pesaje.fila, _sospechoso_de_pesaje(lectura.huella, pesaje, motivo)
                )
                continue
            registrar_despacho(
                sesion,
                material.id,
                pesaje.fecha,
                cantidad,
                usuario=usuario,
                ticket=pesaje.ticket,
                placa=_corto(pesaje.placa, 20),
                cliente=_corto(pesaje.cliente, 120),
                origen="bascula",
            )
            tickets.add(pesaje.ticket)
            registrados += 1
        sesion.flush()
    return ResultadoImportacion(
        registrados=registrados,
        ya_registrados=ya_registrados,
        a_la_bandeja=a_la_bandeja,
        huella=lectura.huella,
    )


def pendientes(sesion: Session) -> list[PesajeSospechoso]:
    """Pesajes sospechosos por resolver, en el orden en que llegaron."""
    return list(
        sesion.scalars(
            select(PesajeSospechoso)
            .where(PesajeSospechoso.estado == "pendiente")
            .order_by(PesajeSospechoso.id)
        )
    )


def _sospechoso_pendiente(sesion: Session, id_sospechoso: int) -> PesajeSospechoso:
    sospechoso = sesion.get(PesajeSospechoso, id_sospechoso)
    if sospechoso is None:
        raise ErrorDeInventario("No existe ese pesaje sospechoso. Actualice la bandeja.")
    if sospechoso.estado != "pendiente":
        raise ErrorDeInventario("Ese pesaje sospechoso ya fue resuelto o descartado.")
    return sospechoso


def resolver(
    sesion: Session,
    id_sospechoso: int,
    *,
    material_codigo: str,
    fecha: date,
    neto_t: Decimal,
    ticket: str,
    usuario: str,
    ahora: datetime,
) -> Movimiento:
    """Crea el despacho con los valores corregidos y cierra el sospechoso como `resuelto`.

    `ahora` lo manda quien llama (este modulo no lee el reloj para el cierre). Todo o nada.
    """
    sospechoso = _sospechoso_pendiente(sesion, id_sospechoso)
    ticket = ticket.strip()
    if not ticket:
        raise ErrorDeInventario("Indique el ticket del pesaje.")
    if not isinstance(neto_t, Decimal) or not neto_t.is_finite() or neto_t <= _CERO:
        raise ErrorDeInventario("El peso neto debe ser un número mayor que cero.")
    material = _Catalogo(sesion).buscar(material_codigo)
    if material is None:
        raise ErrorDeInventario(
            f"No existe un material con el código o nombre «{material_codigo.strip()}». "
            "Elija uno de la lista de materiales."
        )
    cantidad, motivo = _cantidad_de_despacho(material, neto_t)
    if cantidad is None and motivo == MOTIVO_SIN_DENSIDAD:
        raise ErrorDeInventario(
            f"El material {material.codigo} se vende en m3 y no tiene densidad registrada; "
            "indíquela antes de resolver este pesaje."
        )
    if cantidad is None:
        raise ErrorDeInventario(
            "El peso neto es demasiado pequeño para la unidad del material; revise el valor."
        )
    with sesion.begin_nested():
        movimiento = registrar_despacho(
            sesion,
            material.id,
            fecha,
            cantidad,
            usuario=usuario,
            ticket=ticket,
            placa=sospechoso.placa,
            origen="bascula",
            nota=_corto(
                f"Resuelto desde la bandeja (archivo {sospechoso.huella_archivo[:8]}, "
                f"fila {sospechoso.fila}).",
                300,
            ),
        )
        sospechoso.estado = "resuelto"
        sospechoso.resuelto_por = usuario
        sospechoso.resuelto_en = ahora
        sesion.flush()
    return movimiento


def descartar(sesion: Session, id_sospechoso: int, *, usuario: str, ahora: datetime) -> None:
    """Cierra el sospechoso como `descartado` sin crear ningun despacho."""
    sospechoso = _sospechoso_pendiente(sesion, id_sospechoso)
    sospechoso.estado = "descartado"
    sospechoso.resuelto_por = usuario
    sospechoso.resuelto_en = ahora
    sesion.flush()
