"""Tarifas del dominio sistemas (Sesión M3.1): jornales del tabulador CIV jul‑2026 por rol, con Ref,
y el APU de un punto de función cuyo precio unitario se fijó **a mano** con la fórmula de
CLAUDE.md §4 antes de correr el motor (`data/sistemas/fuentes/README.md`).

Ningún precio se transcribe aquí: cada valor esperado se lee de `referencia_sistemas.csv` (M0.2)
o se deriva del fixture. Las regresiones exactas son las del cálculo manual: costo directo 87,741 y
precio unitario 110,992365 USD/PF (sin prestaciones ni bono; administración y utilidad en cascada).
"""

from __future__ import annotations

import csv
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from core.catalog.precios import leer_lista_precios
from core.contracts import ParametrosCosto
from core.costing import calcular_apu
from tests.fixtures import tarifas_sistemas as sis

RAIZ = Path(__file__).resolve().parents[2]
RUTA_LISTA = RAIZ / "data" / "sistemas" / "fuentes" / "lista_tarifas_2026-07.csv"
RUTA_README = RAIZ / "data" / "sistemas" / "fuentes" / "README.md"

MARCA_SUPUESTO = "SUPUESTO (pendiente validacion del autor)"
FRASE_BENCHMARK = "rango tipico reportado por benchmarks de la industria (ISBSG)"
CUANTO = Decimal("0.0001")

#: Calculados a mano antes de correr el motor (README, «El APU de un punto de función»).
COSTO_DIRECTO_ESPERADO = Decimal("87.741")


def _referencia() -> dict[str, dict[str, str]]:
    with open(sis.RUTA_REFERENCIA, newline="", encoding="utf-8") as archivo:
        return {fila["ref_maprex"]: fila for fila in csv.DictReader(archivo)}


def test_tarifas_por_rol_con_ref_del_tabulador_civ():
    referencia = _referencia()

    assert len(sis.TARIFAS) >= 3
    for tarifa in sis.TARIFAS.values():
        fila = referencia[tarifa.ref_maprex]
        assert fila["tipo"] == "mano_obra"
        assert fila["archivo"] == "mano_de_obra.pdf"
        assert "TAB CIV" in fila["notas"].upper() or "tabulador CIV" in fila["notas"]
        assert tarifa.descripcion == fila["insumo"]
        assert tarifa.jornal_bs == Decimal(fila["precio_bs"])
        assert tarifa.jornal_usd == Decimal(fila["precio_usd"])
        assert isinstance(tarifa.jornal_usd, Decimal) and tarifa.jornal_usd > 0
        assert isinstance(tarifa.tarifa_hh, Decimal) and tarifa.tarifa_hh > 0
        # (a) jornal -> HH con jornada de 8 h (supuesto declarado), cuantizado a 0,0001
        esperada = (tarifa.jornal_usd / sis.HORAS_JORNADA).quantize(CUANTO, rounding=ROUND_HALF_UP)
        assert tarifa.tarifa_hh == esperada


def test_productividad_y_reparto_declarados_como_supuestos():
    assert sis.HORAS_JORNADA == Decimal("8")
    assert Decimal("6") <= sis.PRODUCTIVIDAD_HH_PF <= Decimal("12")
    assert sum(sis.HORAS_POR_PF.values()) == sis.PRODUCTIVIDAD_HH_PF
    assert set(sis.HORAS_POR_PF) == set(sis.TARIFAS)

    # La frase literal del PLAN puede quedar partida en varias lineas: se compara sin saltos.
    docstring = " ".join(sis.__doc__.split())
    readme = " ".join(RUTA_README.read_text(encoding="utf-8").split())
    assert MARCA_SUPUESTO in docstring
    assert FRASE_BENCHMARK in docstring
    assert MARCA_SUPUESTO in readme
    assert FRASE_BENCHMARK in readme


def test_el_apu_de_un_punto_de_funcion_fijado_por_regresion_manual():
    apu = sis.APU_PUNTO_FUNCION

    assert apu.codigo_partida.startswith("SIS-")
    assert apu.unidad == sis.UNIDAD_PF == "pf"
    assert apu.rendimiento == sis.RENDIMIENTO_PF == Decimal("1")
    assert not apu.materiales and not apu.equipos  # solo horas de personas
    assert apu.total_obreros == sis.PRODUCTIVIDAD_HH_PF / sis.HORAS_JORNADA  # 1 obrero-dia/PF

    resultado = calcular_apu(apu, sis.PARAMETROS_SISTEMAS)

    assert resultado.precio_unitario > 0
    assert resultado.costo_directo == COSTO_DIRECTO_ESPERADO
    assert resultado.precio_unitario == sis.PRECIO_UNITARIO_PF_ESPERADO


def test_cantidad_por_jornal_equivale_a_horas_por_tarifa_horaria():
    """`cantidad = horas / 8` y `sueldo = jornal`: lo que el contrato guarda es lo mismo que
    horas × tarifa_hh, salvo el redondeo a 0,0001 de la tarifa."""
    for linea in sis.APU_PUNTO_FUNCION.mano_obra:
        rol = sis.ROL_POR_DESCRIPCION[linea.descripcion]
        tarifa = sis.TARIFAS[rol]
        horas = sis.HORAS_POR_PF[rol]

        assert linea.cantidad == horas / sis.HORAS_JORNADA
        assert linea.sueldo == tarifa.jornal_usd
        assert abs(linea.cantidad * linea.sueldo - horas * tarifa.tarifa_hh) < Decimal("0.001")


def test_parametros_sistemas_sin_prestaciones_ni_bono():
    """Honorarios profesionales del tabulador CIV: FCAS y bono en cero (supuesto declarado);
    administración y utilidad, las del contrato."""
    por_defecto = ParametrosCosto()

    assert sis.PARAMETROS_SISTEMAS.fcas == Decimal("0")
    assert sis.PARAMETROS_SISTEMAS.bono_alimentacion == Decimal("0")
    assert sis.PARAMETROS_SISTEMAS.administracion == por_defecto.administracion
    assert sis.PARAMETROS_SISTEMAS.utilidad == por_defecto.utilidad


def test_composicion_para_un_caso_de_uso_conserva_las_lineas():
    composicion = sis.composicion_para("SIS-PRES-01", "Presupuestos: Crear presupuesto")

    assert composicion.codigo_partida == "SIS-PRES-01"
    assert composicion.descripcion == "Presupuestos: Crear presupuesto"
    assert composicion.unidad == sis.UNIDAD_PF
    assert composicion.rendimiento == sis.RENDIMIENTO_PF
    assert composicion.mano_obra == sis.APU_PUNTO_FUNCION.mano_obra
    resultado = calcular_apu(composicion, sis.PARAMETROS_SISTEMAS)
    assert resultado.precio_unitario == sis.PRECIO_UNITARIO_PF_ESPERADO


def test_lista_canonica_de_tarifas_coincide_con_el_fixture():
    with open(RUTA_LISTA, newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))

    assert filas == sis.filas_lista_canonica()
    assert len(leer_lista_precios(RUTA_LISTA)) == len(sis.TARIFAS)
    for fila in filas:
        assert fila["tipo"] == "mano_obra"
        assert fila["unidad"] == ""  # la mano de obra no lleva unidad en el catalogo
        assert Decimal(fila["precio"]) > 0
