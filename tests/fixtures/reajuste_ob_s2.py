# tests/fixtures/reajuste_ob_s2.py
"""El escenario «con reajuste» de OB-S2 (spec S2 §7.1) sobre los estudios de S1.

La versión revalorada `OB-R01` (el material de B pasa de 3,00 a 4,00 y el de C de 12,00 a 14,10),
las series de índices (planas: `Km = 1`, porque el estudio de la memoria usa la comprobación
directa) y la cláusula ficticia de OB-S2: periodicidad mensual, mecanismo `comprobacion`. Con lo
ejecutado de noviembre (A 90 y B 60, de V-01 y V-02), el monto reconocido es
`Σ q_reajustable · (PU comprobado - PU del contrato)` = A 90 x 0,00 + B 60 x (7,59 - 6,325) = 75,90.
**Datos ficticios** (NORMAS.md §1).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from core import models
from core.budget import actualizar_precios
from core.budget.puente import PeriodoDelEstudio
from core.budget.reajuste import Clausula, Componente, Estructura, Mecanismo
from core.catalog.indices import DefinicionSerie, Observacion, registrar_importacion
from tests.fixtures import control_ob_s2 as ob

D = Decimal
REVALORADA = "OB-R01"
FECHA_REVALORACION = date(2026, 11, 13)
MATERIALES_DEL_CORTE = {
    "Material de Tuberia de drenaje": D("4.00"),
    "Material de Relleno compactado": D("14.10"),
}
SERIES = {"materiales": "OB-MAT", "equipos": "OB-EQU", "mano_obra": "OB-MO"}
PESOS = {"materiales": D("0.5"), "equipos": D("0.2"), "mano_obra": D("0.3")}
CLAUSULA = Clausula(
    fecha_inicio=date(2026, 11, 2),
    duracion_meses=6,
    fecha_referencia_primer_anio=date(2026, 11, 2),
    periodicidad="mensual",
    mecanismo=Mecanismo.COMPROBACION,
    estructura=Estructura.DECLARADA,
    componentes=tuple(Componente(c, SERIES[c], PESOS[c]) for c in SERIES),
    fecha_base_indices=date(2026, 10, 1),
    r=D("0"),
    fuente_r="memoria OB-S2: la clausula ficticia no declara R",
    fuente="contrato ficticio de OB-S2",
    responsable=ob.INSPECTOR,
)
NOVIEMBRE = PeriodoDelEstudio(date(2026, 11, 1), date(2026, 11, 30), REVALORADA)
DICIEMBRE = PeriodoDelEstudio(date(2026, 12, 1), date(2026, 12, 31), REVALORADA)
RECONOCIDO_DE_NOVIEMBRE = D("75.90")


def sembrar_revaloracion(sesion) -> models.Presupuesto:
    """Importa los índices planos y crea `OB-R01` revalorando OB-001 con una lista nueva."""
    for numero, codigo in enumerate(SERIES.values()):
        registrar_importacion(
            sesion,
            DefinicionSerie(codigo, codigo, "ficticio", "indice", "mensual"),
            [Observacion(date(2026, 10, 1), D(100)), Observacion(date(2026, 11, 1), D(100))],
            archivo="memoria",
            huella=str(numero) * 64,
            fuente="tests/fixtures/memorias/control_ob_s2.md",
            fecha_descarga=date(2026, 11, 13),
            responsable="Admin",
            filas_leidas=2,
            filas_rechazadas=0,
        )
    base = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == "OB-S2 USD")
    ).one()
    nueva = models.ListaPrecios(
        nombre="OB-S2 revalorada", moneda=ob.MONEDA, fecha_vigencia=FECHA_REVALORACION
    )
    sesion.add(nueva)
    sesion.flush()
    for precio in base.precios:
        descripcion = sesion.get(models.Insumo, precio.insumo_id).descripcion
        sesion.add(
            models.PrecioInsumo(
                lista_id=nueva.id,
                insumo_id=precio.insumo_id,
                precio=MATERIALES_DEL_CORTE.get(descripcion, precio.precio),
            )
        )
    sesion.flush()
    actualizar_precios(sesion, ob.NOMBRE, ob.CODIGO, nueva, REVALORADA, plan=ob.PLAN)
    return sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == REVALORADA)
    ).one()
