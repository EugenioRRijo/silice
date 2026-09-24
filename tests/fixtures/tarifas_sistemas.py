"""Tarifas del dominio sistemas y el APU de un punto de función (Sesión M3.1 del PLAN_MULTIDOMINIO).

Única copia estructurada de las tarifas y de la composición por punto de función (CLAUDE.md §2,
principio DRY). **No transcribe ningún precio**: lee los jornales del tabulador CIV al 01/07/2026
de `data/precios/maprex_2026-07/referencia_sistemas.csv` (Sesión M0.2, 43 filas con `ref_maprex`)
al importarse. Las descripciones de los roles son las de MaPreX, literales (incluida la truncada
por el ancho de columna del reporte), para que la procedencia sea evidente en el catálogo, en el
informe de auditoría y en la lista canónica de UC‑02 (`data/sistemas/fuentes/
lista_tarifas_2026-07.csv`, que `filas_lista_canonica` deriva de este módulo).

Supuestos — SUPUESTO (pendiente validacion del autor)
-----------------------------------------------------
Declarados antes del código en `data/sistemas/fuentes/README.md`; ninguno bloquea GM3.

- **(a) Jornada de 8 h** para convertir jornal en tarifa horaria: `tarifa_hh = jornal_usd / 8`,
  cuantizada a 0,0001. El catálogo guarda el **jornal** (`LineaManoObra.sueldo` es un jornal por
  contrato); las horas por punto de función entran como fracción de obrero‑día
  (`cantidad = horas / 8`), de modo que `cantidad × jornal` es `horas × tarifa_hh` salvo el redondeo
  de la tarifa.
- **(b) Rol del APU ↔ fila del tabulador:** analista ↔ `DIS019` (INGENIERO P-5 CIV ANALISTA
  DIAGNOSTICO), desarrollador ↔ `DIS042` (INGENIERO COMPUTISTA P-9), líder ↔ `DIS036` (GERENTE DE
  PROYECTOS C/CERTIFICACION). QA y arquitecto no existen en el tabulador CIV: las horas de pruebas
  van al desarrollador; no se costea arquitecto.
- **(c) Productividad.** SUPUESTO (pendiente validacion del autor): 8 HH/PF, rango tipico
  reportado por benchmarks de la industria (ISBSG); la cita definitiva la fija el autor en el marco
  teorico.
- **Reparto de horas por PF:** analista 1,6 h (20 %), desarrollador 6,0 h (75 %), líder 0,4 h (5 %).
- **`PARAMETROS_SISTEMAS`: FCAS y bono en cero.** El tabulador CIV es de sueldos mínimos
  profesionales; el 600 % de prestaciones es la convención de la mano de obra de la construcción
  y el CIV no publica bono. Administración y utilidad quedan en sus valores por defecto. Pendiente
  de la decisión sobre la fuente del FCAS del dossier G0.

Consumidores: `tests/unit/test_tarifas_sistemas.py` (M3.1) y `scripts/seed_sistemas.py` (M3.2),
que es, como los otros seeds, el único módulo fuera de `tests/` que lo importa.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from core.contracts import ComposicionAPU, LineaManoObra, ParametrosCosto

RAIZ = Path(__file__).resolve().parents[2]
RUTA_REFERENCIA = RAIZ / "data" / "precios" / "maprex_2026-07" / "referencia_sistemas.csv"

#: Vigencia del tabulador CIV (columna `fecha_vigencia` de `mano_de_obra.pdf`).
FECHA_TABULADOR = date(2026, 7, 1)
MONEDA = "USD"
#: La unidad que emite `AdaptadorSistemas` (sin alias en `core.contracts.unidades`; ver I5).
UNIDAD_PF = "pf"
#: Un punto de función por día con las cantidades en obrero‑días por PF: la división es neutra.
RENDIMIENTO_PF = Decimal("1")
#: SUPUESTO (pendiente validacion del autor): jornada de 8 h.
HORAS_JORNADA = Decimal("8")
#: SUPUESTO (pendiente validacion del autor): 8 HH/PF (benchmark ISBSG, cita pendiente).
PRODUCTIVIDAD_HH_PF = Decimal("8")
CUANTO_TARIFA = Decimal("0.0001")

CODIGO_PLANTILLA = "SIS-PF"
DESCRIPCION_PLANTILLA = "Un punto de funcion no ajustado (IFPUG) de software a medida"

#: Honorarios profesionales: sin prestaciones ni bono (ver «Supuestos»).
PARAMETROS_SISTEMAS = ParametrosCosto(fcas=Decimal("0"), bono_alimentacion=Decimal("0"))

#: Precio unitario de un punto de función **calculado a mano** con la fórmula de CLAUDE.md §4 antes
#: de correr el motor (README de `data/sistemas/fuentes/`). Es un resultado esperado, no un precio
#: de entrada: única copia para las pruebas de M3.1 y M3.2 (INV‑009).
PRECIO_UNITARIO_PF_ESPERADO = Decimal("110.992365")

#: Rol del APU -> Ref del tabulador CIV (supuesto (b)); el orden es el de la lista canónica.
REF_POR_ROL: dict[str, str] = {
    "analista": "DIS019",
    "desarrollador": "DIS042",
    "lider": "DIS036",
}
#: Horas de cada rol por punto de función (reparto supuesto); suman `PRODUCTIVIDAD_HH_PF`.
HORAS_POR_PF: dict[str, Decimal] = {
    "analista": Decimal("1.6"),
    "desarrollador": Decimal("6.0"),
    "lider": Decimal("0.4"),
}


@dataclass(frozen=True)
class Tarifa:
    """La tarifa de un rol: su fila del tabulador CIV y la tarifa horaria derivada."""

    rol: str
    ref_maprex: str
    descripcion: str
    jornal_bs: Decimal
    jornal_usd: Decimal
    tarifa_hh: Decimal


def _leer_tarifas() -> dict[str, Tarifa]:
    with open(RUTA_REFERENCIA, newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    por_ref: dict[str, dict[str, str]] = {}
    for fila in filas:
        ref = fila["ref_maprex"]
        if ref in por_ref:
            raise ValueError(f"{RUTA_REFERENCIA.name}: la Ref {ref} aparece dos veces")
        por_ref[ref] = fila

    tarifas: dict[str, Tarifa] = {}
    for rol, ref in REF_POR_ROL.items():
        if ref not in por_ref:
            raise ValueError(f"{RUTA_REFERENCIA.name} no trae la Ref {ref} ({rol})")
        fila = por_ref[ref]
        if fila["tipo"] != "mano_obra":
            raise ValueError(f"{ref} no es mano de obra en la referencia: {fila['tipo']}")
        jornal_usd = Decimal(fila["precio_usd"])
        tarifas[rol] = Tarifa(
            rol=rol,
            ref_maprex=ref,
            descripcion=fila["insumo"],
            jornal_bs=Decimal(fila["precio_bs"]),
            jornal_usd=jornal_usd,
            tarifa_hh=(jornal_usd / HORAS_JORNADA).quantize(CUANTO_TARIFA, rounding=ROUND_HALF_UP),
        )
    return tarifas


TARIFAS: dict[str, Tarifa] = _leer_tarifas()
#: Descripción literal del tabulador -> rol del APU, para trazar cada línea a su tarifa.
ROL_POR_DESCRIPCION: dict[str, str] = {tarifa.descripcion: rol for rol, tarifa in TARIFAS.items()}

if set(HORAS_POR_PF) != set(REF_POR_ROL):
    raise ValueError("HORAS_POR_PF y REF_POR_ROL deben declarar los mismos roles")
if sum(HORAS_POR_PF.values()) != PRODUCTIVIDAD_HH_PF:
    raise ValueError(
        f"el reparto de horas por PF suma {sum(HORAS_POR_PF.values())} y la productividad "
        f"declarada es {PRODUCTIVIDAD_HH_PF} HH/PF"
    )


def _lineas_mano_obra() -> tuple[LineaManoObra, ...]:
    """Una línea por rol: `cantidad` en obrero‑días por PF (horas / 8), `sueldo` = jornal USD."""
    return tuple(
        LineaManoObra(
            TARIFAS[rol].descripcion, HORAS_POR_PF[rol] / HORAS_JORNADA, TARIFAS[rol].jornal_usd
        )
        for rol in REF_POR_ROL
    )


def composicion_para(codigo_partida: str, descripcion: str) -> ComposicionAPU:
    """El APU de un punto de función bajo el código de un caso de uso concreto.

    El alcance funcional (`data/samples/sistemas/alcance_funcional.csv`) no aporta datos para
    diferenciar la productividad por módulo sin inventarla: todas las partidas `SIS-*` comparten
    las mismas líneas (`scripts/seed_sistemas.py` las crea a partir de los ítems del adaptador).
    """
    return ComposicionAPU(
        codigo_partida=codigo_partida,
        descripcion=descripcion,
        unidad=UNIDAD_PF,
        rendimiento=RENDIMIENTO_PF,
        mano_obra=_lineas_mano_obra(),
    )


#: La plantilla: un punto de función (costo directo 87,741; precio unitario 110,992365 USD,
#: calculados a mano en `data/sistemas/fuentes/README.md`).
APU_PUNTO_FUNCION = composicion_para(CODIGO_PLANTILLA, DESCRIPCION_PLANTILLA)


def filas_lista_canonica() -> list[dict[str, str]]:
    """Las filas de `data/sistemas/fuentes/lista_tarifas_2026-07.csv` (formato de UC‑02).

    Una por rol, en el orden de `REF_POR_ROL`; sin unidad (la mano de obra no la lleva en el
    catálogo); el precio es el jornal USD como texto exacto de la referencia.
    """
    return [
        {
            "tipo": "mano_obra",
            "insumo": TARIFAS[rol].descripcion,
            "unidad": "",
            "precio": f"{TARIFAS[rol].jornal_usd:f}",
        }
        for rol in REF_POR_ROL
    ]
