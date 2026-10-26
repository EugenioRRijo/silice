"""La vivienda ficticia de 80 m2 con sus seis APU OBRA-01 a OBRA-06 (MP-7, Tarea 21).

Datos FICTICIOS (ningún precio, rendimiento ni nombre real): seis partidas de una vivienda
unifamiliar con el rendimiento de su APU (unidades por día de una cuadrilla) y la cantidad de
obra que el plan por rendimientos reparte:

| Partida | Descripción                  | Unidad | Rend. | Cant. | Días (cantidad ÷ rendimiento) |
|---------|------------------------------|--------|-------|-------|-------------------------------|
| OBRA-01 | Excavación para fundaciones  | m3     | 4,5   | 18    | 18 ÷ 4,5 = 4                  |
| OBRA-02 | Concreto para fundaciones    | m3     | 6     | 12    | 12 ÷ 6 = 2                    |
| OBRA-03 | Acero de refuerzo            | kg     | 250   | 950   | 3,8 → 4 (al medio día)        |
| OBRA-04 | Paredes de bloque de arcilla | m2     | 12    | 210   | 17,5                          |
| OBRA-05 | Friso liso en paredes        | m2     | 18    | 420   | 23,33… → 23,5                 |
| OBRA-06 | Pintura de caucho            | m2     | 60    | 420   | 7                             |

Cada APU tiene una línea de material, una de equipo y una de mano de obra (el concreto lleva el
«Cemento gris» de la procura de MP-7). `ITEMS` son los renglones del presupuesto en ese orden;
`sembrar_catalogo` carga los seis APU en una lista «Lista Bs de la vivienda» para las pruebas que
necesitan una base del caso.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from core import models
from core.catalog import Catalogo
from core.contracts.apu import ComposicionAPU, LineaEquipo, LineaManoObra, LineaMaterial
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo

FECHA = date(2026, 11, 2)
LISTA = "Lista Bs de la vivienda"

#: (código, descripción, unidad, rendimiento, cantidad, material, precio, equipo, precio, jornal)
# fmt: off
PARTIDAS = (
    ("OBRA-01", "Excavación para fundaciones", "m3", "4.5", "18",
     "Agua", "2.00", "Pala y pico", "3.00", "40.00"),
    ("OBRA-02", "Concreto para fundaciones", "m3", "6", "12",
     "Cemento gris", "95.00", "Mezcladora de concreto", "60.00", "45.00"),
    ("OBRA-03", "Acero de refuerzo", "kg", "250", "950",
     "Cabilla de 1/2 pulgada", "1.80", "Cizalla", "5.00", "45.00"),
    ("OBRA-04", "Paredes de bloque de arcilla", "m2", "12", "210",
     "Bloque de arcilla de 15 cm", "12.00", "Andamio", "8.00", "42.00"),
    ("OBRA-05", "Friso liso en paredes", "m2", "18", "420",
     "Mortero premezclado", "4.00", "Andamio", "8.00", "42.00"),
    ("OBRA-06", "Pintura de caucho en paredes", "m2", "60", "420",
     "Pintura de caucho", "3.50", "Rodillo y bandeja", "2.00", "40.00"),
)
# fmt: on


def _composicion(fila: tuple[str, ...]) -> ComposicionAPU:
    codigo, descripcion, unidad, rendimiento, _, material, precio, equipo, tarifa, jornal = fila
    return ComposicionAPU(
        codigo_partida=codigo,
        descripcion=descripcion,
        unidad=unidad,
        rendimiento=Decimal(rendimiento),
        materiales=(LineaMaterial(material, unidad, Decimal("1"), Decimal(precio)),),
        equipos=(LineaEquipo(equipo, Decimal("1"), Decimal(tarifa), Decimal("1")),),
        mano_obra=(LineaManoObra("Obrero", Decimal("2"), Decimal(jornal)),),
    )


COMPOSICIONES: dict[str, ComposicionAPU] = {fila[0]: _composicion(fila) for fila in PARTIDAS}


def item(codigo: str, cantidad: str, n: int = 1) -> ItemComputo:
    """Un renglón de la partida `codigo` de la vivienda con `cantidad` (texto exacto)."""
    fila = next(f for f in PARTIDAS if f[0] == codigo)
    return ItemComputo(
        codigo_partida=codigo,
        descripcion=fila[1],
        unidad=fila[2],
        cantidad=Decimal(cantidad),
        origen_id=f"FILA-{n}",
        origen_tipo=OrigenTipo.TABULAR,
        dominio=Dominio.CIVIL,
    )


#: Los seis renglones del presupuesto, en su orden.
ITEMS: tuple[ItemComputo, ...] = tuple(
    item(fila[0], fila[4], n) for n, fila in enumerate(PARTIDAS, 1)
)


def sembrar_catalogo(sesion: Session) -> models.ListaPrecios:
    """La lista en Bs con los seis APU en el catálogo del caso (sin confirmar)."""
    lista = models.ListaPrecios(nombre=LISTA, moneda="Bs", fecha_vigencia=FECHA, origen="prueba")
    sesion.add(lista)
    sesion.flush()
    catalogo = Catalogo(sesion)
    for composicion in COMPOSICIONES.values():
        catalogo.cargar_composicion(composicion, lista, Dominio.CIVIL, FECHA, "prueba")
    return lista
