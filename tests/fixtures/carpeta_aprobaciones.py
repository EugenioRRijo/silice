"""Una carpeta de trabajo ficticia para el ciclo de aprobación (MP-4, Tarea 18).

La «Vivienda Demo 80 m2» con seis partidas OBRA-01 a OBRA-06 (una línea de material, una de equipo
y una de mano de obra cada una, números inventados), en Bs, sobre la lista «Lista Bs de prueba».
`sembrar_vivienda` guarda VIV-001 por el embudo del núcleo a nombre de quien se indique (por
omisión «Ana <ana>», la cuenta `ana` de `tests/fixtures/sesion_web.py`); `guardar_version` guarda
otra versión de la misma obra. Datos ficticios: ningún precio ni nombre real.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import Catalogo
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo

OBRA = "Vivienda Demo 80 m2"
ANA = "Ana <ana>"
FECHA = date(2026, 10, 1)
PARAMETROS = ParametrosCosto()

#: (código, descripción, unidad, cantidad de VIV-001, precio del material, del equipo, jornal)
PARTIDAS = (
    ("OBRA-01", "Limpieza y replanteo del terreno", "m2", "80", "2.00", "10.00", "8.00"),
    ("OBRA-02", "Excavación para fundaciones", "m3", "12", "0.00", "40.00", "8.00"),
    ("OBRA-03", "Concreto para fundaciones", "m3", "6", "90.00", "30.00", "9.00"),
    ("OBRA-04", "Paredes de bloque de arcilla", "m2", "140", "12.00", "5.00", "9.00"),
    ("OBRA-05", "Losa de techo nervada", "m2", "80", "35.00", "20.00", "10.00"),
    ("OBRA-06", "Friso liso en paredes", "m2", "280", "4.00", "2.00", "8.00"),
)


def _composicion(codigo, descripcion, unidad, _cantidad, material, equipo, jornal):
    return ComposicionAPU(
        codigo_partida=codigo,
        descripcion=descripcion,
        unidad=unidad,
        rendimiento=Decimal("10"),
        materiales=(
            LineaMaterial(f"Material de {codigo}", unidad, Decimal("1"), Decimal(material)),
        ),
        equipos=(LineaEquipo(f"Equipo de {codigo}", Decimal("1"), Decimal(equipo), Decimal("1")),),
        mano_obra=(LineaManoObra("Obrero", Decimal("2"), Decimal(jornal)),),
    )


COMPOSICIONES = {fila[0]: _composicion(*fila) for fila in PARTIDAS}


def _items(cantidades: dict[str, str]) -> list[ItemComputo]:
    return [
        ItemComputo(
            codigo_partida=codigo,
            descripcion=descripcion,
            unidad=unidad,
            cantidad=Decimal(cantidades.get(codigo, cantidad)),
            origen_id=f"FILA-{n}",
            origen_tipo=OrigenTipo.TABULAR,
            dominio=Dominio.CIVIL,
        )
        for n, (codigo, descripcion, unidad, cantidad, *_precios) in enumerate(PARTIDAS, 1)
    ]


def guardar_version(
    sesion: Session,
    proyecto: models.Proyecto,
    codigo: str,
    *,
    usuario: str = ANA,
    cantidades: dict[str, str] | None = None,
    version_origen: models.Presupuesto | None = None,
) -> models.Presupuesto:
    """Guarda otra versión de la vivienda (las seis partidas; `cantidades` cambia alguna) y
    confirma."""
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == "Lista Bs de prueba")
    ).one()
    resultado = elaborar(
        _items(cantidades or {}),
        COMPOSICIONES,
        PARAMETROS,
        codigo=codigo,
        fecha=FECHA,
        moneda="Bs",
        plan=plan_secuencial,
    )
    opciones = {} if version_origen is None else {"version_origen": version_origen}
    if version_origen is not None:
        opciones["motivo"] = "edicion"
    version = guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=lista,
        parametros=PARAMETROS,
        pendientes=resultado.pendientes,
        usuario=usuario,
        **opciones,
    )
    sesion.commit()
    return version


def sembrar_vivienda(sesion: Session, *, usuario: str = ANA) -> models.Proyecto:
    """La lista, las seis partidas en el catálogo, la obra y su VIV-001 (confirmado)."""
    lista = models.ListaPrecios(
        nombre="Lista Bs de prueba", moneda="Bs", fecha_vigencia=FECHA, origen="prueba"
    )
    sesion.add(lista)
    sesion.flush()
    catalogo = Catalogo(sesion)
    for composicion in COMPOSICIONES.values():
        catalogo.cargar_composicion(composicion, lista, Dominio.CIVIL, FECHA, "prueba")
    proyecto = crear_proyecto(sesion, OBRA, dominio=Dominio.CIVIL)
    sesion.commit()
    guardar_version(sesion, proyecto, "VIV-001", usuario=usuario)
    return proyecto
