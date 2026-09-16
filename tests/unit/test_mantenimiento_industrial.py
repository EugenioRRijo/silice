"""El catálogo de mantenimiento industrial (Sesión M2.1): al menos tres partidas `MNT-*` de
activos del inventario construido `activos_planta.csv`, costeadas con la referencia MaPreX
jul‑2026 como proxy declarado (degradación GM2, `data/industrial/fuentes/README.md`) y sin
transcribir ningún precio.

Los precios unitarios esperados se calcularon **a mano** con la fórmula de CLAUDE.md §4 antes de
correr el motor (rendimiento 1, parámetros por defecto del contrato) y se fijan aquí como regresión
exacta: materiales sin dividir entre el rendimiento; equipos cantidad × precio × factor; mano de
obra (Σ cantidad × jornal × (1 + 6,00) + 1,00 × obreros); administración 15 % y utilidad 10 % en
cascada.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from adapters.industrial import AdaptadorIndustrial
from core.catalog.precios import leer_lista_precios
from core.contracts import LineaManoObra, ParametrosCosto
from core.contracts.unidades import normalizar_unidad
from core.costing import calcular_apu
from tests.fixtures import mantenimiento_industrial as mnt

RAIZ = Path(__file__).resolve().parents[2]
RUTA_ACTIVOS = RAIZ / "data" / "samples" / "industrial" / "activos_planta.csv"
RUTA_LISTA = RAIZ / "data" / "industrial" / "fuentes" / "lista_maprex_2026-07.csv"
RUTA_README = RAIZ / "data" / "industrial" / "fuentes" / "README.md"

MARCA_SUPUESTO = "SUPUESTO (pendiente validacion del autor)"

#: Calculados a mano antes de correr el motor (ver docstring). Rendimiento 1 en las cuatro.
PRECIOS_UNITARIOS_ESPERADOS = {
    "MNT-BOM-CEN": Decimal("214.652631875"),
    "MNT-COM-REC": Decimal("154.33506"),
    "MNT-MOT-TRI": Decimal("147.82922825"),
    "MNT-BOM-SUM": Decimal("208.146863375"),
}


def _referencia() -> dict[str, dict[str, str]]:
    with open(mnt.RUTA_REFERENCIA, newline="", encoding="utf-8") as archivo:
        return {fila["ref_maprex"]: fila for fila in csv.DictReader(archivo)}


def _precio(linea) -> Decimal:
    return linea.sueldo if isinstance(linea, LineaManoObra) else linea.precio


def test_al_menos_tres_partidas_mnt_de_activos_reales():
    assert len(mnt.COMPOSICIONES_MNT) >= 3

    items = {item.codigo_partida: item for item in AdaptadorIndustrial().extraer(RUTA_ACTIVOS)}
    for codigo, composicion in mnt.COMPOSICIONES_MNT.items():
        assert codigo.startswith("MNT-")
        assert composicion.codigo_partida == codigo
        assert items[codigo].origen_id == mnt.ACTIVOS_COSTEADOS[codigo]
        assert composicion.unidad == items[codigo].unidad == mnt.UNIDAD_INTERVENCION


def test_toda_linea_tiene_precio_decimal_positivo():
    for composicion in mnt.COMPOSICIONES_MNT.values():
        assert composicion.materiales  # repuestos
        assert composicion.mano_obra  # tecnico
        for linea in (*composicion.materiales, *composicion.equipos, *composicion.mano_obra):
            assert isinstance(_precio(linea), Decimal)
            assert _precio(linea) > 0
            assert linea.cantidad > 0


def test_precio_unitario_positivo_y_fijado_por_regresion_manual():
    assert set(PRECIOS_UNITARIOS_ESPERADOS) == set(mnt.COMPOSICIONES_MNT)
    for codigo, esperado in PRECIOS_UNITARIOS_ESPERADOS.items():
        resultado = calcular_apu(mnt.COMPOSICIONES_MNT[codigo], ParametrosCosto())

        assert resultado.precio_unitario > 0
        assert resultado.precio_unitario == esperado, codigo


def test_los_parametros_del_fixture_son_los_del_contrato_por_defecto():
    """La discrepancia con el bono MaPreX por nivel queda declarada en el README, no resuelta."""
    assert mnt.PARAMETROS_INDUSTRIAL == ParametrosCosto()
    assert mnt.RENDIMIENTO_INTERVENCION == Decimal("1")


def test_cada_linea_proviene_de_una_fila_de_la_referencia_maprex():
    """DRY: el fixture lee la referencia; esta prueba lo comprueba fila a fila, incluido el factor
    de depreciación del equipo y el jornal de cada técnico."""
    referencia = _referencia()
    for composicion in mnt.COMPOSICIONES_MNT.values():
        for material in composicion.materiales:
            fila = referencia[mnt.REF_POR_DESCRIPCION[material.descripcion]]
            assert fila["tipo"] == "material"
            assert fila["insumo"] == material.descripcion
            assert normalizar_unidad(fila["unidad"]) == material.unidad
            assert Decimal(fila["precio_usd"]) == material.precio
        for equipo in composicion.equipos:
            fila = referencia[mnt.REF_POR_DESCRIPCION[equipo.descripcion]]
            assert fila["tipo"] == "equipo"
            assert Decimal(fila["precio_usd"]) == equipo.precio
            assert Decimal(fila["factor_depreciacion"]) == equipo.depreciacion
        for obrero in composicion.mano_obra:
            fila = referencia[mnt.REF_POR_DESCRIPCION[obrero.descripcion]]
            assert fila["tipo"] == "mano_obra"
            assert Decimal(fila["precio_usd"]) == obrero.sueldo


def test_lista_canonica_industrial_coincide_con_el_fixture():
    with open(RUTA_LISTA, newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))

    assert filas == mnt.filas_lista_canonica()
    assert len(leer_lista_precios(RUTA_LISTA)) == len(mnt.REFS_USADAS)


def test_degradacion_y_supuestos_declarados():
    readme = RUTA_README.read_text(encoding="utf-8")

    assert "Degradación GM2 declarada" in readme
    assert MARCA_SUPUESTO in readme
    assert MARCA_SUPUESTO in mnt.__doc__
