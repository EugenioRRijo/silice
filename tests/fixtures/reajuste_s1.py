# tests/fixtures/reajuste_s1.py
"""Contrato de s1_reajuste.md en una base: versión 001 en Bs (PU 100) y la 002 revalorada (116)."""

from datetime import date
from decimal import Decimal as D  # noqa: N817

from core import models
from core.budget import actualizar_precios, crear_proyecto, elaborar, guardar_presupuesto
from core.budget.reajuste import (
    Clausula,
    Componente,
    Ejecutado,
    Estructura,
    Mecanismo,
    PeriodoDeclarado,
)
from core.catalog import Catalogo
from core.catalog.indices import (
    DefinicionSerie,
    Observacion,
    definicion_tasa,
    registrar_importacion,
)
from core.contracts import ComposicionAPU, Dominio, ItemComputo, LineaMaterial, ParametrosCosto
from core.contracts.item_computo import OrigenTipo

CERO = ParametrosCosto(D(0), D(0), D(0), D(0))
NOMBRE = "Contrato S1 (reajuste)"
INDICES = {"FIC-MAT": ("200", "230"), "FIC-EQU": ("150", "165"), "FIC-MO": ("80", "100")}
#: La cláusula y el período de `s1_reajuste.md` (los usan la prueba del estudio y la base 0.6.0).
PESOS = {
    "materiales": ("FIC-MAT", "0.5"),
    "equipos": ("FIC-EQU", "0.2"),
    "mano_obra": ("FIC-MO", "0.3"),
}
CLAUSULA = Clausula(
    date(2026, 1, 15),
    24,
    date(2026, 1, 15),
    "mensual",
    Mecanismo.AMBOS,
    Estructura.DECLARADA,
    tuple(Componente(c, s, D(p)) for c, (s, p) in PESOS.items()),
    date(2026, 1, 1),
    D("0.10"),
    "memoria",
    "contrato ficticio",
    "Ing.",
)
PERIODO = PeriodoDeclarado(
    date(2027, 2, 1),
    date(2027, 2, 28),
    (Ejecutado("S1-R01", D(1000), "AV-01 del 28/02/2027"),),
    "002",
)


def _importar(sesion, codigo, valores, huella):
    registrar_importacion(
        sesion,
        DefinicionSerie(codigo, codigo, "ficticio", "indice_bs", "mensual"),
        [Observacion(f, D(v)) for f, v in valores],
        archivo="memoria",
        huella=huella,
        fuente="tests/fixtures/memorias/s1_reajuste.md",
        fecha_descarga=date(2027, 3, 1),
        responsable="A",
        filas_leidas=len(valores),
        filas_rechazadas=0,
    )


def sembrar(sesion):
    lista = models.ListaPrecios(
        nombre="Contrato S1 Bs", moneda="Bs", fecha_vigencia=date(2026, 1, 15)
    )
    sesion.add(lista)
    sesion.flush()
    apu = ComposicionAPU(
        "S1-R01",
        "Partida ficticia del reajuste",
        "m3",
        D(1),
        (LineaMaterial("Insumo ficticio del reajuste", "m3", D(1), D(100)),),
    )
    Catalogo(sesion).cargar_composicion(apu, lista, Dominio.CIVIL, date(2026, 1, 15), "memoria S1")
    item = ItemComputo(
        "S1-R01", "Partida ficticia", "m3", D(1000), "memoria-s1", OrigenTipo.MANUAL, Dominio.CIVIL
    )
    hecho = elaborar(
        [item], {"S1-R01": apu}, CERO, codigo="001", fecha=date(2026, 1, 15), moneda="Bs"
    )
    proyecto = crear_proyecto(sesion, NOMBRE)
    guardar_presupuesto(
        sesion, hecho.presupuesto, hecho.informe, proyecto=proyecto, lista=lista, parametros=CERO
    )
    nueva = models.ListaPrecios(
        nombre="Revalorada 2027-02", moneda="Bs", fecha_vigencia=date(2027, 2, 1)
    )
    sesion.add(nueva)
    sesion.flush()
    insumo = sesion.query(models.Insumo).filter_by(descripcion="Insumo ficticio del reajuste").one()
    sesion.add(models.PrecioInsumo(lista_id=nueva.id, insumo_id=insumo.id, precio=D(116)))
    sesion.flush()
    actualizar_precios(sesion, NOMBRE, "001", nueva, "002")
    for n, (codigo, (i0, im)) in enumerate(INDICES.items()):
        _importar(sesion, codigo, [(date(2026, 1, 1), i0), (date(2027, 2, 1), im)], f"{n}" * 64)
    registrar_importacion(
        sesion,
        definicion_tasa("venta"),
        [Observacion(date(2027, 2, 26), D(850))],
        archivo="memoria",
        huella="9" * 64,
        fuente="https://www.bcv.org.ve/",
        fecha_descarga=date(2027, 3, 1),
        responsable="A",
        filas_leidas=1,
        filas_rechazadas=0,
    )  # tasa FICTICIA de la memoria
    sesion.flush()
