"""Libros FICTICIOS con un APU por hoja y su libro de presupuesto (F5 vial, tareas 4 y 5).

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §7 (punto 4). La forma
es la que describe el diseño (un libro por frente con una hoja por partida, solo valores, tres
bloques con columnas distintas y un pie con porcentajes en cascada), escrita a mano desde esa
descripción: **ningún** nombre, código, cifra ni rótulo sale de un libro real (NORMAS §1). Los
rótulos son los del perfil del repositorio `adapters/hoja_empresa/perfiles/apu_por_hoja.json`, que
se escribió contra este libro.

Cada hoja «APU n» trae, de arriba abajo: el título; la cabecera («Partida N°:», «Código:»,
«Descripción:», «Unidad:», «Cantidad:», «Rendimiento:», cada valor en la celda de la derecha); el
bloque «MATERIALES» (N° | Descripción | Unidad | Cantidad | Desperdicio % | Precio | Total), el de
«EQUIPOS» (N° | Descripción | Cantidad | Precio | Coef. depreciación | Total) y el de «MANO DE OBRA»
(N° | Descripción | Cantidad | Jornal | Bono | Total), cada uno cerrado por su «Total …»; después
«Prestaciones sociales (%)», «Costo directo», «Administración (%)», «Utilidad e imprevistos (%)»,
«Financiamiento (%)», «Impuesto (%)» y «PRECIO UNITARIO». Hay renglones sin número correlativo. El
programa que exporta estos libros redondea cada renglón a dos decimales: los totales impresos de
aquí siguen esa regla (memoria abajo).

Memoria de cálculo (a mano; Sílice recalcula exacto y redondea solo al presentar):

    APU 1  Riego de adherencia ficticio (m2), cantidad 1.000, rendimiento 2.000
      MAT  = 0,50 × 1,04 × 2,00 + 0,002 × 10,00          = 1,04 + 0,02 = 1,06
      EQ   = (1 × 400 × 1 + 1 × 200 × 0,5) ÷ 2.000       = 0,25
      MO   = (2 × 50 + 3 × 30) × 3,5 ÷ 2.000             = 0,3325   (impreso 0,33)
      CD   = 1,6425 ; × 1,15 = 1,888875 ; × 1,10 = 2,0777625 → 2,08 (impreso 2,08)
    APU 2  Transporte de mezcla, mayor de 8 km y hasta 10 km (t-km, en t), cantidad 120, rend. 300
      EQ   = 2 × 350 ÷ 300 = 2,3333… ; MO = 2 × 40 × 3,5 ÷ 300 = 0,9333…
      CD   = 980 ÷ 300 = 3,2666… ; PU = 3,2666… × 1,265 = 4,1323… → 4,13 (impreso 4,50: ERROR)
    APU 3  Demarcación ficticia (m), cantidad 500, rendimiento 1.000
      MAT  = 6 × 0,001 × 4,50 = 0,027 (cada renglón impreso 0,00: total impreso 0,00)
      EQ   = 300 ÷ 1.000 = 0,30 ; MO = 2 × 45 × 3,5 ÷ 1.000 = 0,315 (impreso 0,32)
      CD   = 0,642 ; PU = 0,642 × 1,265 = 0,81213 → 0,81
      Con redondeo por renglón: CD 0,00 + 0,30 + 0,32 = 0,62; adm 0,093 → 0,09; 0,71; util
      0,071 → 0,07; PU 0,78 (impreso 0,78): la diferencia (0,03213) es solo redondeo → INFO.
    APU 4  Movilización ficticia (viaje), financiamiento 2 %: no evaluable (impreso 820,00).
    APU 5  Limpieza ficticia (m2), bono 5 por renglón e impuesto 16 %: no evaluable y
           ADVERTENCIA (impreso 0,20).

El libro de presupuesto (hoja «PRESUPUESTO»: N° | Código | Descripción | Unidad | Cantidad | P.U. |
Total) enlaza cada renglón con su APU por el número: el renglón 3 dice 450 m (el APU, 500), el 5
dice P.U. 0,25 (el APU, 0,20) y el 6 no tiene hoja de APU.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

D = Decimal
_CENT = D("0.01")


def _r(valor: Decimal) -> Decimal:
    return valor.quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Material:
    numero: int | None
    descripcion: str
    unidad: str
    cantidad: str
    desperdicio: str
    precio: str


@dataclass(frozen=True)
class Equipo:
    numero: int | None
    descripcion: str
    cantidad: str
    precio: str
    coeficiente: str


@dataclass(frozen=True)
class Obrero:
    numero: int | None
    descripcion: str
    cantidad: str
    jornal: str
    bono: str = "0"


@dataclass(frozen=True)
class ApuFicticio:
    numero: int
    codigo: str
    descripcion: str
    unidad: str
    cantidad: str
    rendimiento: str
    materiales: tuple[Material, ...] = ()
    equipos: tuple[Equipo, ...] = ()
    mano_obra: tuple[Obrero, ...] = ()
    prestaciones: str = "250"
    administracion: str = "15"
    utilidad: str = "10"
    financiamiento: str = "0"
    impuesto: str = "0"
    #: El P.U. que imprime la hoja; sin él, el que resulta del redondeo por renglón.
    impreso: str | None = None
    extra: dict[str, str] = field(default_factory=dict)


APUS: tuple[ApuFicticio, ...] = (
    ApuFicticio(
        1,
        "VF-001",
        "Riego de adherencia ficticio",
        "m2",
        "1000",
        "2000",
        materiales=(
            Material(1, "Emulsión asfáltica ficticia", "lt", "0.50", "4", "2.00"),
            Material(None, "Arena de secado ficticia", "m3", "0.002", "0", "10.00"),
        ),
        equipos=(
            Equipo(1, "Camión irrigador ficticio", "1", "400.00", "1"),
            Equipo(2, "Barredora ficticia", "1", "200.00", "0.5"),
        ),
        mano_obra=(
            Obrero(1, "Operador ficticio", "2", "50.00"),
            Obrero(None, "Ayudante ficticio", "3", "30.00"),
        ),
    ),
    ApuFicticio(
        2,
        "VF-002",
        "Transporte de mezcla asfáltica ficticia, mayor de 8 km y hasta 10 km",
        "t-km",
        "120",
        "300",
        equipos=(Equipo(1, "Volteo ficticio", "2", "350.00", "1"),),
        mano_obra=(Obrero(1, "Chofer ficticio", "2", "40.00"),),
        impreso="4.50",
    ),
    ApuFicticio(
        3,
        "VF-003",
        "Demarcación ficticia",
        "m",
        "500",
        "1000",
        materiales=tuple(
            Material(n, f"Microesfera ficticia {n}", "kg", "0.001", "0", "4.50")
            for n in range(1, 7)
        ),
        equipos=(Equipo(1, "Demarcadora ficticia", "1", "300.00", "1"),),
        mano_obra=(Obrero(1, "Pintor ficticio", "2", "45.00"),),
    ),
    ApuFicticio(
        4,
        "VF-004",
        "Movilización de equipos ficticia",
        "viaje",
        "2",
        "1",
        equipos=(Equipo(1, "Gandola ficticia", "1", "500.00", "1"),),
        mano_obra=(Obrero(1, "Chofer ficticio", "1", "40.00"),),
        financiamiento="2",
        impreso="820.00",
    ),
    ApuFicticio(
        5,
        "VF-005",
        "Limpieza de superficie ficticia",
        "m2",
        "1000",
        "4000",
        mano_obra=(Obrero(1, "Obrero ficticio", "4", "30.00", bono="5"),),
        impuesto="16",
        impreso="0.20",
    ),
)

#: Renglones del libro de presupuesto: (número, código, descripción, unidad, cantidad, P.U.).
RENGLONES: tuple[tuple[int, str, str, str, str, str], ...] = (
    (1, "VF-001", "Riego de adherencia ficticio", "m2", "1000", "2.08"),
    (
        2,
        "VF-002",
        "Transporte de mezcla asfáltica ficticia, mayor de 8 km y hasta 10 km",
        "t-km",
        "120",
        "4.50",
    ),
    (3, "VF-003", "Demarcación ficticia", "m", "450", "0.78"),
    (4, "VF-004", "Movilización de equipos ficticia", "viaje", "2", "820.00"),
    (5, "VF-005", "Limpieza de superficie ficticia", "m2", "1000", "0.25"),
    (6, "VF-006", "Señalización ficticia", "dia", "30", "15.00"),
)


def precio_impreso(apu: ApuFicticio) -> Decimal:
    """El P.U. de la hoja: el declarado o el del redondeo por renglón (la regla del exportador)."""
    if apu.impreso is not None:
        return D(apu.impreso)
    rend = D(apu.rendimiento)
    mat = sum(
        (_r(D(m.cantidad) * (1 + D(m.desperdicio) / 100) * D(m.precio)) for m in apu.materiales),
        D(0),
    )
    eq = _r(
        sum((_r(D(e.cantidad) * D(e.precio) * D(e.coeficiente)) for e in apu.equipos), D(0)) / rend
    )
    base = sum((_r(D(o.cantidad) * D(o.jornal)) for o in apu.mano_obra), D(0))
    mo = _r(_r(base * (1 + D(apu.prestaciones) / 100)) / rend)
    cd = mat + eq + mo
    sub = cd + _r(cd * D(apu.administracion) / 100)
    return sub + _r(sub * D(apu.utilidad) / 100)


def _hoja_apu(libro, apu: ApuFicticio) -> None:
    h = libro.create_sheet(f"APU {apu.numero}")
    filas: list[list[object]] = [
        ["ANÁLISIS DE PRECIO UNITARIO"],
        ["Obra:", "Vía ficticia de prueba"],
        ["Partida N°:", apu.numero, "Código:", apu.codigo],
        ["Descripción:", apu.descripcion],
        ["Unidad:", apu.unidad, "Cantidad:", D(apu.cantidad), "Rendimiento:", D(apu.rendimiento)],
        [],
        ["MATERIALES"],
        ["N°", "Descripción", "Unidad", "Cantidad", "Desperdicio %", "Precio", "Total"],
    ]
    total_mat = D(0)
    for m in apu.materiales:
        total = _r(D(m.cantidad) * (1 + D(m.desperdicio) / 100) * D(m.precio))
        total_mat += total
        filas.append(
            [m.numero, m.descripcion, m.unidad, D(m.cantidad), D(m.desperdicio), D(m.precio), total]
        )
    filas += [["Total materiales", None, None, None, None, None, total_mat], [], ["EQUIPOS"]]
    filas.append(["N°", "Descripción", "Cantidad", "Precio", "Coef. depreciación", "Total"])
    total_eq = D(0)
    for e in apu.equipos:
        total = _r(D(e.cantidad) * D(e.precio) * D(e.coeficiente))
        total_eq += total
        filas.append([e.numero, e.descripcion, D(e.cantidad), D(e.precio), D(e.coeficiente), total])
    rend = D(apu.rendimiento)
    filas += [
        ["Total equipos", None, None, None, None, total_eq],
        ["Equipos por unidad", None, None, None, None, _r(total_eq / rend)],
        [],
        ["MANO DE OBRA"],
        ["N°", "Descripción", "Cantidad", "Jornal", "Bono", "Total"],
    ]
    base = D(0)
    for o in apu.mano_obra:
        total = _r(D(o.cantidad) * D(o.jornal))
        base += total
        filas.append([o.numero, o.descripcion, D(o.cantidad), D(o.jornal), D(o.bono), total])
    con_prestaciones = _r(base * (1 + D(apu.prestaciones) / 100))
    filas += [
        ["Total mano de obra", None, None, None, None, base],
        ["Prestaciones sociales (%)", None, None, None, D(apu.prestaciones), con_prestaciones],
        ["Mano de obra por unidad", None, None, None, None, _r(con_prestaciones / rend)],
        [],
        ["Costo directo", None, None, None, None, None, None],
        ["Administración (%)", None, None, None, None, D(apu.administracion), None],
        ["Utilidad e imprevistos (%)", None, None, None, None, D(apu.utilidad), None],
        ["Financiamiento (%)", None, None, None, None, D(apu.financiamiento), None],
        ["Impuesto (%)", None, None, None, None, D(apu.impuesto), None],
        ["PRECIO UNITARIO", None, None, None, None, None, precio_impreso(apu)],
    ]
    for fila in filas:
        h.append([float(v) if isinstance(v, Decimal) else v for v in fila])


def libro_apu(apus: tuple[ApuFicticio, ...] = APUS) -> bytes:
    """El libro de APU (una hoja por partida, solo valores) como bytes de un .xlsx."""
    import openpyxl

    libro = openpyxl.Workbook()
    libro.remove(libro.active)
    for apu in apus:
        _hoja_apu(libro, apu)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def libro_presupuesto(renglones=RENGLONES) -> bytes:
    """El libro de presupuesto (P.U. tecleado; el número de renglón enlaza con la hoja del APU)."""
    import openpyxl

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "PRESUPUESTO"
    hoja.append(["PRESUPUESTO FICTICIO"])
    hoja.append([])
    hoja.append(["N°", "Código", "Descripción", "Unidad", "Cantidad", "P.U.", "Total"])
    for numero, codigo, descripcion, unidad, cantidad, pu in renglones:
        total = _r(D(cantidad) * D(pu))
        hoja.append([numero, codigo, descripcion, unidad, float(cantidad), float(pu), float(total)])
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()
