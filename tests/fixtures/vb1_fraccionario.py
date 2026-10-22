"""Siembra compartida de VB-1: un presupuesto con un equipo fraccionario (rendimiento 12,
equipos = 1/12). Lo usan `test_vb1_entregar_revisar` y `test_vb1_remedio_legado`."""

from __future__ import annotations

from decimal import Decimal

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
from tests.fixtures.canonico_minimo import FECHA, USUARIO

UN_DOCEAVO_28 = "0.0833333333333333333333333333"
UN_DOCEAVO_29 = "0.08333333333333333333333333333"

FRACCIONARIA = ComposicionAPU(
    codigo_partida="FRA-001",
    descripcion="Equipo fraccionario",
    unidad="m3",
    rendimiento=Decimal("12"),
    materiales=(LineaMaterial("Arena", "m3", Decimal("1.00"), Decimal("14.00")),),
    equipos=(LineaEquipo("Compactadora", Decimal("1"), Decimal("1.00"), Decimal("1")),),
    mano_obra=(LineaManoObra("Obrero", Decimal("2"), Decimal("10.25")),),
)


def sembrar_fraccionaria(caso: Session, **opciones):
    lista = models.ListaPrecios(nombre="Lista", moneda="USD", fecha_vigencia=FECHA, origen="prueba")
    caso.add(lista)
    caso.flush()
    Catalogo(caso).cargar_composicion(FRACCIONARIA, lista, Dominio.CIVIL, FECHA, "prueba")
    proyecto = crear_proyecto(caso, "FRA-001", dominio=Dominio.CIVIL)
    item = ItemComputo(
        codigo_partida="FRA-001",
        descripcion="Equipo fraccionario",
        unidad="m3",
        cantidad=Decimal("20"),
        origen_id="FILA-1",
        origen_tipo=OrigenTipo.TABULAR,
        dominio=Dominio.CIVIL,
    )
    r = elaborar(
        [item],
        {"FRA-001": FRACCIONARIA},
        ParametrosCosto(),
        codigo="001",
        fecha=FECHA,
        moneda="USD",
        plan=plan_secuencial,
    )
    version = guardar_presupuesto(
        caso,
        r.presupuesto,
        r.informe,
        proyecto=proyecto,
        lista=lista,
        parametros=ParametrosCosto(),
        pendientes=r.pendientes,
        usuario=USUARIO,
        **opciones,
    )
    caso.commit()
    return proyecto, version
