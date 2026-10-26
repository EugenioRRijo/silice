"""Datos FICTICIOS del estudio de mercado (MP-5, Tarea 13).

Todo es inventado: la carpeta «Contratista Demo, C.A.» trabaja en Bs; sus insumos («Cemento gris»,
«Arena lavada», «Albañil») y sus partidas (`OBRA-04`, `OBRA-05`) son de la vivienda ficticia de
80 m²; los proveedores y competidores («Ferretería Demo», «Constructora Ejemplo») no existen.
Nunca hay aquí precios, nombres ni libros reales de la empresa ni de la competencia.

Los APU están pensados para que su costo se calcule a mano:

- `OBRA-04` (concreto ficticio, m3): 2 sacos de cemento a 500,00 → costo directo 1.000,00.
- `OBRA-05` (friso ficticio, m2): 1 albañil a jornal de 100,00 con rendimiento 10 m2/día, sin
  materiales → costo directo (100 × (1 + fcas) + bono × 1) / 10.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from aplicacion.mercado import registrar_observacion
from aplicacion.tablas_carpeta import crear_esquema_carpeta
from aplicacion.tablas_mercado import ObservacionDeMercado, crear_esquema_mercado
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.contracts.apu import ComposicionAPU, LineaManoObra, LineaMaterial
from core.contracts.dominio import Dominio

HOY = date(2026, 10, 25)
JULIO = date(2026, 7, 1)
AHORA = datetime(2026, 10, 25, 9, 30)
LISTA = "Lista demo en Bs"
RESPONSABLE = "ana"

#: (código, tipo, descripción, unidad, precio en Bs) de la lista ficticia.
INSUMOS = (
    ("MAT-001", "material", "Cemento gris", "saco", Decimal("500.00")),
    ("MAT-002", "material", "Arena lavada", "m3", Decimal("1250.50")),
    ("MO-001", "mano_obra", "Albañil", None, Decimal("100.00")),
)

CONCRETO = ComposicionAPU(
    codigo_partida="OBRA-04",
    descripcion="Concreto ficticio para losa",
    unidad="m3",
    rendimiento=Decimal("1"),
    materiales=(LineaMaterial("Cemento gris", "saco", Decimal("2"), Decimal("500.00")),),
)
FRISO = ComposicionAPU(
    codigo_partida="OBRA-05",
    descripcion="Friso ficticio de pared",
    unidad="m2",
    rendimiento=Decimal("10"),
    mano_obra=(LineaManoObra("Albañil", Decimal("1"), Decimal("100.00")),),
)


def nueva_sesion(*, moneda: str | None = "Bs", con_lista: bool = True) -> Iterator[Session]:
    """Base en memoria con el catálogo ficticio; la carpeta declarada en `moneda` (sin declarar
    con `None`). Sin `con_lista` no hay lista de precios ni partidas, solo los insumos."""
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    crear_esquema_carpeta(motor)
    crear_esquema_mercado(motor)
    try:
        with abrir_sesion(motor) as s:
            _sembrar(s, con_lista=con_lista)
            if moneda is not None:
                declarar_moneda_de_la_carpeta(s, moneda, responsable=RESPONSABLE, ahora=AHORA)
            yield s
    finally:
        motor.dispose()


def _sembrar(s: Session, *, con_lista: bool) -> None:
    insumos = {}
    for codigo, tipo, descripcion, unidad, _ in INSUMOS:
        insumo = models.Insumo(codigo=codigo, tipo=tipo, descripcion=descripcion, unidad=unidad)
        s.add(insumo)
        insumos[codigo] = insumo
    s.flush()
    if not con_lista:
        return
    lista = models.ListaPrecios(nombre=LISTA, moneda="Bs", fecha_vigencia=JULIO, origen="")
    s.add(lista)
    s.flush()
    for codigo, *_, precio in INSUMOS:
        s.add(models.PrecioInsumo(lista_id=lista.id, insumo_id=insumos[codigo].id, precio=precio))
    s.flush()
    catalogo = Catalogo(s)
    for composicion in (CONCRETO, FRISO):
        catalogo.cargar_composicion(
            composicion, lista, Dominio.CIVIL, JULIO, "rendimiento ficticio de prueba"
        )


def observar(
    s: Session,
    codigo: str,
    precios: Sequence[str],
    *,
    lado: str = "compra",
    fecha: date = HOY,
    fuente_tipo: str = "proveedor",
) -> list[int]:
    """Registra una observación por precio (escritos como los teclea la persona)."""
    return [
        registrar_observacion(
            s,
            lado=lado,
            codigo=codigo,
            fuente_tipo=fuente_tipo,
            fuente="Ferretería Demo" if lado == "compra" else "Constructora Ejemplo",
            fecha=fecha,
            precio=precio,
            nota="",
            responsable=RESPONSABLE,
            ahora=AHORA,
        )
        for precio in precios
    ]


def observacion_cruda(
    s: Session,
    codigo: str,
    precio: Decimal,
    *,
    moneda: str,
    lado: str = "compra",
    fecha: date = HOY,
    anulada_por: int | None = None,
) -> int:
    """Una fila escrita directo en la tabla (otra moneda o anulada), sin pasar por las reglas."""
    fila = ObservacionDeMercado(
        lado=lado,
        codigo=codigo,
        fuente_tipo="cotizacion",
        fuente="Proveedor Ejemplo",
        fecha=fecha,
        moneda=moneda,
        precio=precio,
        nota="",
        responsable=RESPONSABLE,
        fecha_hora=AHORA,
        anulada_por=anulada_por,
    )
    s.add(fila)
    s.flush()
    return fila.id


def version(
    s: Session,
    proyecto: str,
    codigo: str,
    *,
    moneda: str = "Bs",
    fcas: str = "6.00",
    bono: str = "1.00",
    administracion: str = "0.15",
    utilidad: str = "0.10",
) -> models.Presupuesto:
    """Una versión mínima de la obra `proyecto` (la crea si falta) con esos parámetros."""
    obra = s.scalars(select(models.Proyecto).where(models.Proyecto.nombre == proyecto)).first()
    if obra is None:
        obra = models.Proyecto(nombre=proyecto, descripcion="Vivienda ficticia de 80 m²")
        s.add(obra)
        s.flush()
    lista = s.scalars(select(models.ListaPrecios).where(models.ListaPrecios.nombre == LISTA)).one()
    presupuesto = models.Presupuesto(
        codigo=codigo,
        proyecto_id=obra.id,
        fecha=HOY,
        moneda=moneda,
        lista_precios_id=lista.id,
        fcas=Decimal(fcas),
        bono_alimentacion=Decimal(bono),
        administracion=Decimal(administracion),
        utilidad=Decimal(utilidad),
    )
    s.add(presupuesto)
    s.flush()
    return presupuesto
