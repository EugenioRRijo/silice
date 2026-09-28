"""Catálogo de mantenimiento industrial: cuatro partidas `MNT-*` costeadas con la referencia
MaPreX de julio 2026 (Sesión M2.1 del PLAN_MULTIDOMINIO).

Única copia estructurada de las composiciones de mantenimiento en el sistema (CLAUDE.md §2,
principio DRY). **No transcribe ningún precio**: los lee de
`data/precios/maprex_2026-07/referencia_industrial.csv` (Sesión M0.2, cada fila verificada contra
el PDF y con `ref_maprex`) al importarse. Las descripciones de los insumos son las de MaPreX,
literales, para que la procedencia sea evidente en el catálogo, en el informe de auditoría y en
la lista canónica de UC‑02 (`data/industrial/fuentes/lista_maprex_2026-07.csv`, que
`filas_lista_canonica` deriva de este mismo módulo).

Degradación GM2 declarada
-------------------------
No llegaron cotizaciones de campo: los precios son el **proxy fechado** MaPreX jul‑2026
(PLAN_MULTIDOMINIO §2, degradación de GM2), no precios cotizados. La declaración completa, con la
correspondencia insumo ↔ Ref, está en `data/industrial/fuentes/README.md`.

Supuestos — SUPUESTO (pendiente validacion del autor)
-----------------------------------------------------
Ninguna orden de trabajo real respalda el alcance de las intervenciones. Se declaran como supuestos
del autor, a confirmar con la ronda de cotizaciones (`data/industrial/plantilla_precios.csv`):

- **Alcance de cada intervención** (qué repuestos, en qué cantidad; cantidades fraccionarias =
  consumo prorrateado entre intervenciones: 0,25 sello = un sello cada cuatro intervenciones).
- **`RENDIMIENTO_INTERVENCION = 1`**: una intervención por día de cuadrilla (la bitácora I5
  industrial anticipó que el rendimiento «unidades por día» civil no aplica a un evento de
  mantenimiento; se toma un día por evento).
- **El taladro industrial de banco (`EZ0453`) representa la herramienta de taller**: único
  equipo de taller estructurado para este dominio en M0.2, con su factor MaPreX (1,000000).
- **Repuestos proxy de categoría** cuando MaPreX no tiene el SKU exacto (`MZ0623`, «rodamientos
  de alternador», por rodamiento industrial genérico).
- **`PARAMETROS_INDUSTRIAL = ParametrosCosto()`** (FCAS 600 %, bono 1,00 USD/obrero‑día,
  administración 15 %, utilidad 10 %): el jornal es el del tabulador MaPreX, pero la estructura
  sobre él es la del contrato por defecto. MaPreX trae un bono propio por nivel (3 445,50 Bs para
  el mecánico N8, 3 679,85 Bs para el electricista N5) que no cabe en un único parámetro de
  presupuesto: discrepancia declarada para la decisión FCAS/bono del dossier G0, no resuelta aquí.

Consumidores: `tests/unit/test_mantenimiento_industrial.py` (M2.1) y `scripts/seed_industrial.py`
(M2.2), que es el único módulo fuera de `tests/` que lo importa. Sigue el patrón de
`scripts/seed.py` y `scripts/seed_telecom.py`, que importan a propósito la copia única de su
dominio, aunque esas copias tienen además otros importadores en `scripts/` (la lista completa está
en `docs/arquitectura.md` §4).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from core.contracts import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)

RAIZ = Path(__file__).resolve().parents[2]
RUTA_REFERENCIA = RAIZ / "data" / "precios" / "maprex_2026-07" / "referencia_industrial.csv"

#: Vigencia de la lista canónica: la de materiales y equipos (la de mano de obra es 01/07/2026).
FECHA_REFERENCIA = date(2026, 7, 9)
MONEDA = "USD"
UNIDAD_INTERVENCION = "intervencion"
#: SUPUESTO (pendiente validacion del autor): una intervención por día de cuadrilla.
RENDIMIENTO_INTERVENCION = Decimal("1")
#: Estructura de costos por defecto del contrato (ver «Supuestos» en el docstring del módulo).
PARAMETROS_INDUSTRIAL = ParametrosCosto()

#: Refs de la referencia MaPreX que usa este catálogo, en el orden de la lista canónica.
REFS_USADAS: tuple[str, ...] = (
    "MZ0471",  # MAT. P/INSTALACION SELLO MECANICO TIPO CARTUCHO
    "MZ0623",  # RODAMIENTOS DE ALTERNADOR
    "MZ0341",  # GRASA PARA RODAMIENTOS
    "COM032",  # ACEITE PARA MAQUINAS/MOTORES
    "MZ0294",  # FILTRO DE ACEITE DE MOTOR
    "MEC528",  # CORREA INDUSTRIAL A41 PARA MOTOR
    "EZ0453",  # TALADRO INDUSTRIAL BANCO 3/4" 750W (equipo)
    "24-6.7",  # MECANICO DE EQUIPO PESADO DE 1RA -N8 (mano de obra)
    "19-215",  # ELECTRICISTA DE 1RA -N5 (mano de obra)
)

#: Partida de mantenimiento -> `id_activo` de `data/samples/industrial/activos_planta.csv`.
ACTIVOS_COSTEADOS: dict[str, str] = {
    "MNT-BOM-CEN": "IN-001",  # Bomba centrifuga de agua potable, 15 HP
    "MNT-COM-REC": "IN-003",  # Compresor de aire reciprocante, 25 HP
    "MNT-MOT-TRI": "IN-006",  # Motor electrico trifasico de induccion, 50 HP
    "MNT-BOM-SUM": "IN-007",  # Bomba sumergible de aguas residuales, 10 HP
}


@dataclass(frozen=True)
class InsumoReferencia:
    """Una fila de `referencia_industrial.csv` ya tipada."""

    ref_maprex: str
    tipo: str
    descripcion: str
    unidad: str
    precio_usd: Decimal
    factor_depreciacion: Decimal | None
    archivo: str


def _leer_referencia() -> dict[str, InsumoReferencia]:
    with open(RUTA_REFERENCIA, newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    referencia: dict[str, InsumoReferencia] = {}
    for fila in filas:
        ref = fila["ref_maprex"]
        if ref in referencia:
            raise ValueError(f"{RUTA_REFERENCIA.name}: la Ref {ref} aparece dos veces")
        factor = fila["factor_depreciacion"]
        referencia[ref] = InsumoReferencia(
            ref_maprex=ref,
            tipo=fila["tipo"],
            descripcion=fila["insumo"],
            unidad=fila["unidad"],
            precio_usd=Decimal(fila["precio_usd"]),
            factor_depreciacion=Decimal(factor) if factor else None,
            archivo=fila["archivo"],
        )
    faltantes = [ref for ref in REFS_USADAS if ref not in referencia]
    if faltantes:
        raise ValueError(f"{RUTA_REFERENCIA.name} no trae las Refs {faltantes}")
    return referencia


REFERENCIA: dict[str, InsumoReferencia] = _leer_referencia()

#: Descripción de insumo (literal MaPreX) -> Ref, para trazar cada línea a su fila.
REF_POR_DESCRIPCION: dict[str, str] = {REFERENCIA[ref].descripcion: ref for ref in REFS_USADAS}


def _mat(ref: str, cantidad: str) -> LineaMaterial:
    insumo = REFERENCIA[ref]
    if insumo.tipo != "material":
        raise ValueError(f"{ref} no es material en la referencia: {insumo.tipo}")
    return LineaMaterial(insumo.descripcion, insumo.unidad, Decimal(cantidad), insumo.precio_usd)


def _eq(ref: str, cantidad: str) -> LineaEquipo:
    insumo = REFERENCIA[ref]
    if insumo.tipo != "equipo" or insumo.factor_depreciacion is None:
        raise ValueError(f"{ref} no es equipo con factor en la referencia: {insumo.tipo}")
    return LineaEquipo(
        insumo.descripcion, Decimal(cantidad), insumo.precio_usd, insumo.factor_depreciacion
    )


def _mo(ref: str, cantidad: str) -> LineaManoObra:
    insumo = REFERENCIA[ref]
    if insumo.tipo != "mano_obra":
        raise ValueError(f"{ref} no es mano de obra en la referencia: {insumo.tipo}")
    return LineaManoObra(insumo.descripcion, Decimal(cantidad), insumo.precio_usd)


# ---------------------------------------------------------------------------------------------
# Las cuatro intervenciones (alcance: SUPUESTO, ver docstring del módulo y README de la carpeta)
# ---------------------------------------------------------------------------------------------

APU_BOMBA_CENTRIFUGA = ComposicionAPU(
    codigo_partida="MNT-BOM-CEN",
    descripcion="Mantenimiento preventivo de bomba centrifuga de agua potable (IN-001)",
    unidad=UNIDAD_INTERVENCION,
    rendimiento=RENDIMIENTO_INTERVENCION,
    materiales=(
        _mat("MZ0471", "0.25"),  # un sello mecanico cada cuatro intervenciones
        _mat("MZ0623", "0.5"),  # un par de rodamientos al año
        _mat("MZ0341", "1"),  # un envase de grasa por intervencion
    ),
    equipos=(_eq("EZ0453", "1"),),  # un dia de herramienta de taller
    mano_obra=(_mo("24-6.7", "1"),),
)

APU_COMPRESOR_RECIPROCANTE = ComposicionAPU(
    codigo_partida="MNT-COM-REC",
    descripcion="Mantenimiento preventivo de compresor de aire reciprocante (IN-003)",
    unidad=UNIDAD_INTERVENCION,
    rendimiento=RENDIMIENTO_INTERVENCION,
    materiales=(
        _mat("COM032", "4"),  # cambio de aceite: 4 litros
        _mat("MZ0294", "1"),  # filtro de aceite
        _mat("MEC528", "0.5"),  # una correa cada dos intervenciones
    ),
    equipos=(_eq("EZ0453", "1"),),
    mano_obra=(_mo("24-6.7", "1"),),
)

APU_MOTOR_TRIFASICO = ComposicionAPU(
    codigo_partida="MNT-MOT-TRI",
    descripcion="Mantenimiento preventivo de motor electrico trifasico de induccion (IN-006)",
    unidad=UNIDAD_INTERVENCION,
    rendimiento=RENDIMIENTO_INTERVENCION,
    materiales=(
        _mat("MZ0623", "0.5"),
        _mat("MZ0341", "1"),
        _mat("MEC528", "0.5"),
    ),
    equipos=(_eq("EZ0453", "1"),),
    mano_obra=(_mo("24-6.7", "1"), _mo("19-215", "1")),
)

APU_BOMBA_SUMERGIBLE = ComposicionAPU(
    codigo_partida="MNT-BOM-SUM",
    descripcion="Mantenimiento preventivo de bomba sumergible de aguas residuales (IN-007)",
    unidad=UNIDAD_INTERVENCION,
    rendimiento=RENDIMIENTO_INTERVENCION,
    materiales=(
        _mat("MZ0471", "0.25"),
        _mat("MZ0623", "0.5"),
        _mat("MZ0341", "1"),
    ),
    # Sin equipo: el izaje de la bomba no tiene equivalente en la referencia MaPreX industrial.
    mano_obra=(_mo("24-6.7", "1"), _mo("19-215", "1")),
)

COMPOSICIONES_MNT: dict[str, ComposicionAPU] = {
    composicion.codigo_partida: composicion
    for composicion in (
        APU_BOMBA_CENTRIFUGA,
        APU_COMPRESOR_RECIPROCANTE,
        APU_MOTOR_TRIFASICO,
        APU_BOMBA_SUMERGIBLE,
    )
}

if set(COMPOSICIONES_MNT) != set(ACTIVOS_COSTEADOS):
    raise ValueError("cada composicion MNT-* debe tener su activo en ACTIVOS_COSTEADOS")


def filas_lista_canonica() -> list[dict[str, str]]:
    """Las filas de `data/industrial/fuentes/lista_maprex_2026-07.csv` (formato de UC‑02).

    Una por Ref usada, en el orden de `REFS_USADAS`; equipos y mano de obra sin unidad (no la
    llevan en el catálogo); el precio como texto exacto de la referencia.
    """
    filas: list[dict[str, str]] = []
    for ref in REFS_USADAS:
        insumo = REFERENCIA[ref]
        unidad = LineaMaterial(insumo.descripcion, insumo.unidad, Decimal(0), Decimal(0)).unidad
        filas.append(
            {
                "tipo": insumo.tipo,
                "insumo": insumo.descripcion,
                "unidad": unidad if insumo.tipo == "material" else "",
                "precio": f"{insumo.precio_usd:f}",
            }
        )
    return filas
