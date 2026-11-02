"""La vivienda de la procura (MP-7, Tarea 23): la de `obra_vivienda` con sacos de cemento.

Datos FICTICIOS (ningún precio, consumo ni nombre real). Dos APU cambian solo para la procura, para
que haya un material contado en sacos y compartido por dos partidas:

- OBRA-02 (concreto, 12 m³): 7 sacos de «Cemento gris» y 0,55 m³ de «Arena lavada» por m³.
- OBRA-04 (paredes, 210 m²): 12,5 piezas de «Bloque de arcilla de 15 cm» y 0,2 sacos de «Cemento
  gris» (mortero de pega) por m².

Las demás partidas conservan su APU de `obra_vivienda`. `sembrar` guarda la obra con la versión
VIV-001 y el plan desde los rendimientos de la Tarea 21; `declarar_linea_base` la declara en días
hábiles (un día por período) desde el lunes 2026-11-02.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from aplicacion.plan_rendimientos import duraciones, plan_por_rendimientos
from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto
from core.budget.valuaciones import Calendario, registrar_linea_base
from core.catalog import Catalogo
from core.contracts.apu import ComposicionAPU, LineaMaterial, ParametrosCosto
from core.contracts.dominio import Dominio
from tests.fixtures import obra_vivienda as viv

D = Decimal
OBRA = "Vivienda Demo 80 m2"
VERSION = "VIV-001"
LUNES = date(2026, 11, 2)
PARAMETROS = ParametrosCosto(D("6.00"), D("1.00"), D("0.15"), D("0.10"))


def _con_materiales(codigo: str, *materiales: LineaMaterial) -> ComposicionAPU:
    base = viv.COMPOSICIONES[codigo]
    return ComposicionAPU(
        codigo_partida=base.codigo_partida,
        descripcion=base.descripcion,
        unidad=base.unidad,
        rendimiento=base.rendimiento,
        materiales=materiales,
        equipos=base.equipos,
        mano_obra=base.mano_obra,
    )


COMPOSICIONES: dict[str, ComposicionAPU] = {
    **viv.COMPOSICIONES,
    "OBRA-02": _con_materiales(
        "OBRA-02",
        LineaMaterial("Cemento gris", "saco", D("7"), D("95.00")),
        LineaMaterial("Arena lavada", "m3", D("0.55"), D("30.00")),
    ),
    "OBRA-04": _con_materiales(
        "OBRA-04",
        LineaMaterial("Bloque de arcilla de 15 cm", "pieza", D("12.5"), D("1.20")),
        LineaMaterial("Cemento gris", "saco", D("0.2"), D("95.00")),
    ),
}


def plan():
    """El plan desde los rendimientos de la Tarea 21 (entrada de las pruebas, no su oráculo)."""
    return plan_por_rendimientos(duraciones(viv.ITEMS, COMPOSICIONES, {}))


def sembrar(
    sesion: Session, *, nombre: str = OBRA, lista: models.ListaPrecios | None = None
) -> tuple[models.Proyecto, models.ListaPrecios]:
    """La obra con VIV-001 guardada (con su plan) sobre la lista en Bs; confirma."""
    if lista is None:
        lista = models.ListaPrecios(
            nombre=viv.LISTA, moneda="Bs", fecha_vigencia=viv.FECHA, origen="prueba"
        )
        sesion.add(lista)
        sesion.flush()
        catalogo = Catalogo(sesion)
        for composicion in COMPOSICIONES.values():
            catalogo.cargar_composicion(composicion, lista, Dominio.CIVIL, viv.FECHA, "prueba")
    elegido = plan()
    resultado = elaborar(
        list(viv.ITEMS),
        COMPOSICIONES,
        PARAMETROS,
        codigo=VERSION,
        fecha=viv.FECHA,
        moneda="Bs",
        plan=elegido,
    )
    obra = crear_proyecto(sesion, nombre, dominio=Dominio.CIVIL)
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=obra,
        lista=lista,
        parametros=PARAMETROS,
        plan=elegido,
        usuario="Ana <ana>",
    )
    sesion.commit()
    return obra, lista


def declarar_linea_base(
    sesion: Session, feriados: tuple[date, ...] = (), *, nombre: str = OBRA
) -> None:
    """La línea base sobre VIV-001, en días hábiles desde el lunes 2026-11-02; confirma."""
    registrar_linea_base(
        sesion,
        nombre,
        VERSION,
        desde=LUNES,
        perspectiva="costo",
        calendario=Calendario(LUNES, 1, feriados),
        fuente="acta ficticia de inicio",
        responsable="Residente Ficticio",
        ahora=datetime(2026, 10, 26, 9),
    )
    sesion.commit()
