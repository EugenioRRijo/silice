"""Dos obras ficticias con línea base y plan desde los rendimientos (MP-7, Tarea 22).

Datos FICTICIOS (ningún precio, rendimiento ni nombre real). Las dos usan el plan de la Tarea 21
(`aplicacion.plan_rendimientos`), en días hábiles (un día por período) desde el lunes 2026-11-02, y
la perspectiva *costo* (el unitario es el costo directo). Parámetros de costo: FCAS 0, bono 0,
administración 0,15 y utilidad 0,10, para que el costo directo salga a mano sin el factor de
prestaciones.

**Obra de dos partidas** («Obra de dos partidas», versión DOS-001):

| Partida | Cantidad | Rend. | Días | Material | Jornal (1 obrero) | Costo directo `u` |
|---------|----------|-------|------|----------|-------------------|-------------------|
| A       | 10 m3    | 2     | 5    | 50,00    | 20,00             | 20 / 2 + 50 = 60  |
| B       | 6 m2     | 3     | 2    | 10,00    | 30,00             | 30 / 3 + 10 = 20  |

Plan: A en «Dia 1» a «Dia 5» con 0,2 cada uno; B en «Dia 6» y «Dia 7» con 0,5.
BAC = 600 + 120 = 720.

**La vivienda** («Vivienda de 80 m2», versión VIV-001): los seis APU OBRA-01 a OBRA-06 de
`tests/fixtures/obra_vivienda.py` con su plan de 58 días (OBRA-01 días 1-4, OBRA-02 días 5-6, …).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from aplicacion.plan_rendimientos import duraciones, plan_por_rendimientos
from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto
from core.budget.valuaciones import Calendario, registrar_linea_base
from core.catalog import Catalogo
from core.contracts.apu import ComposicionAPU, LineaManoObra, LineaMaterial, ParametrosCosto
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from tests.fixtures import obra_vivienda

D = Decimal
INICIO = date(2026, 11, 2)  # lunes: día hábil 1
#: El día hábil 5 (viernes): el fin del plan de A.
DIA_5 = date(2026, 11, 6)
#: El día hábil 6 (lunes): el fin del plan de OBRA-02 en la vivienda.
DIA_6 = date(2026, 11, 9)
PARAMETROS = ParametrosCosto(D("0"), D("0"), D("0.15"), D("0.10"))
FUENTE = "acta ficticia de la obra atrasada"
RESPONSABLE = "Residente Ficticio"

NOMBRE = "Obra de dos partidas"
CODIGO = "DOS-001"
VIVIENDA = "Vivienda de 80 m2"
CODIGO_VIVIENDA = "VIV-001"

COMPOSICIONES = {
    "A": ComposicionAPU(
        "A",
        "Concreto ficticio",
        "m3",
        D("2"),
        materiales=(LineaMaterial("Concreto premezclado ficticio", "m3", D("1"), D("50.00")),),
        mano_obra=(LineaManoObra("Obrero", D("1"), D("20.00")),),
    ),
    "B": ComposicionAPU(
        "B",
        "Friso ficticio",
        "m2",
        D("3"),
        materiales=(LineaMaterial("Mortero ficticio", "m2", D("1"), D("10.00")),),
        mano_obra=(LineaManoObra("Obrero", D("1"), D("30.00")),),
    ),
}
CANTIDADES = {"A": D("10"), "B": D("6")}


def _items() -> list[ItemComputo]:
    return [
        ItemComputo(
            codigo,
            COMPOSICIONES[codigo].descripcion,
            COMPOSICIONES[codigo].unidad,
            cantidad,
            f"obra-atrasada:{codigo}",
            OrigenTipo.MANUAL,
            Dominio.CIVIL,
        )
        for codigo, cantidad in CANTIDADES.items()
    ]


def _sembrar(
    sesion: Session,
    nombre: str,
    codigo: str,
    items,
    composiciones,
    lista: models.ListaPrecios,
) -> models.Presupuesto:
    plan = plan_por_rendimientos(duraciones(items, composiciones, {}))
    resultado = elaborar(
        items, composiciones, PARAMETROS, codigo=codigo, fecha=INICIO, moneda="Bs", plan=plan
    )
    return guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=crear_proyecto(sesion, nombre),
        lista=lista,
        parametros=PARAMETROS,
        plan=plan,
        usuario=RESPONSABLE,
    )


def _declarar(sesion: Session, nombre: str, codigo: str) -> None:
    registrar_linea_base(
        sesion,
        nombre,
        codigo,
        desde=INICIO,
        perspectiva="costo",
        calendario=Calendario(INICIO, 1),
        fuente=FUENTE,
        responsable=RESPONSABLE,
    )


def sembrar_dos_partidas(sesion: Session) -> models.Presupuesto:
    """La obra de dos partidas con su versión DOS-001 y su línea base. No confirma."""
    lista = models.ListaPrecios(
        nombre="Lista Bs de dos partidas", moneda="Bs", fecha_vigencia=INICIO
    )
    sesion.add(lista)
    sesion.flush()
    catalogo = Catalogo(sesion)
    for composicion in COMPOSICIONES.values():
        catalogo.cargar_composicion(composicion, lista, Dominio.CIVIL, INICIO, "prueba")
    version = _sembrar(sesion, NOMBRE, CODIGO, _items(), COMPOSICIONES, lista)
    _declarar(sesion, NOMBRE, CODIGO)
    return version


def sembrar_vivienda(sesion: Session) -> models.Presupuesto:
    """La vivienda con su versión VIV-001 y su línea base. No confirma."""
    lista = obra_vivienda.sembrar_catalogo(sesion)
    version = _sembrar(
        sesion,
        VIVIENDA,
        CODIGO_VIVIENDA,
        list(obra_vivienda.ITEMS),
        obra_vivienda.COMPOSICIONES,
        lista,
    )
    _declarar(sesion, VIVIENDA, CODIGO_VIVIENDA)
    return version
