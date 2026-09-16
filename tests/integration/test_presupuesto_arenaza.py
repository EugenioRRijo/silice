"""Los dos presupuestos ARENAZA reproducidos desde SQLite (Sesión M1.2).

Segunda línea base didáctica de la tesis, en otro dominio y con otra política de costeo: el catálogo
telecom se carga en SQLite con `scripts/seed_telecom.py`, se reconstruyen las `ComposicionAPU` de
las 40 partidas `TC-*` desde la base y el motor puro `core.costing.calcular_apu` las valora. El
total de cada presupuesto debe coincidir con el impreso en el PDF (1 109,29 y 5 410,73 USD) dentro
de ± 0,01, **sin haber tocado `core/`**.

Objetivo de la reproducción: **el PDF tal como está impreso** (criterio del sprint multidominio, el
mismo con el que la línea base civil conserva sus siete inconsistencias). Cuatro renglones no
cumplen
`cantidad x precio_unitario = total` en la fuente y cada uno se reproduce con un mecanismo
declarado en `scripts/seed_telecom.py`; esas pruebas están abajo, una por mecanismo:

- tubo corrugado (P1 renglón 3, P2 renglón 5): el precio impreso es por tubo de 30 m, no por metro;
- P2 renglones 14 y 18: el total impreso contradice `cantidad x precio_unitario` (1 446,65 vs
  1 445,00 y 303,93 vs 300,93); la contradicción se conserva y queda registrada para la Sesión M1.3;
- P1 renglón 14 ("Micelaneos"): partida global sin cantidad ni precio unitario en el PDF.

La política ARENAZA de mano de obra ("el precio de la mano de obra será el equivalente al 50 % del
presupuesto total") se representa con la OPCIÓN 1 del hallazgo 1 de
`docs/bitacora/2026-08-29-I5-telecom.md`: una `LineaManoObra` sintética que arma la capa de catálogo
ANTES de llamar al motor. El motor no cambia y la línea sintética no se persiste.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.catalog import Catalogo
from core.contracts.dominio import Dominio
from scripts.seed_telecom import (
    DEPRECIACION_HERRAMIENTA,
    FRACCION_MANO_OBRA,
    MARCA_AJUSTE,
    METROS_POR_TUBO,
    MONEDA,
    PARAMETROS_ARENAZA,
    UNIDAD_SUMA_GLOBAL,
    codigo_partida,
    composiciones_desde_catalogo,
    items_arenaza,
    presupuesto_arenaza,
    sembrar_telecom,
)
from tests.fixtures import presupuestos_arenaza as arenaza

TOLERANCIA = Decimal("0.01")

#: Los dos presupuestos del fixture, con su total impreso. Único origen de los números.
RENGLONES = {1: arenaza.PRESUPUESTO_1, 2: arenaza.PRESUPUESTO_2}
TOTALES = {1: arenaza.TOTAL_1, 2: arenaza.TOTAL_2}

#: Cuántos renglones de cada presupuesto NO cumplen `cantidad x precio_unitario = total` y se
#: reproducen con un mecanismo declarado (P1: tubo y Micelaneos; P2: tubo y renglones 14 y 18).
CON_MECANISMO = {1: 2, 2: 3}


@pytest.fixture
def sesion_telecom(sesion):
    """La sesión de integración (línea base civil ya sembrada) con el catálogo telecom cargado."""
    sembrar_telecom(sesion)
    return sesion


def _por_codigo(presupuesto):
    return {partida.apu.codigo_partida: partida for partida in presupuesto.partidas}


def _renglon(numero: int, indice: int):
    return next(fila for fila in RENGLONES[numero] if fila.renglon == indice)


# ---------------------------------------------------------------------------------------------
# Criterio de cierre de la sesión: los dos totales, ± 0,01
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("numero", (1, 2))
def test_el_total_reproduce_el_pdf(sesion_telecom, numero):
    presupuesto = presupuesto_arenaza(sesion_telecom, numero)

    assert abs(presupuesto.total - TOTALES[numero]) <= TOLERANCIA
    assert presupuesto.moneda == MONEDA
    assert len(presupuesto.partidas) == len(RENGLONES[numero])


@pytest.mark.parametrize("numero", (1, 2))
def test_el_total_reproduce_el_pdf_sin_diferencia_alguna(sesion_telecom, numero):
    """Más fuerte que el criterio de cierre: la reproducción es exacta, no solo tolerable."""
    presupuesto = presupuesto_arenaza(sesion_telecom, numero)

    assert presupuesto.total == TOTALES[numero]


@pytest.mark.parametrize("numero", (1, 2))
def test_cada_renglon_reproduce_su_total_impreso(sesion_telecom, numero):
    partidas = _por_codigo(presupuesto_arenaza(sesion_telecom, numero))

    for renglon in RENGLONES[numero]:
        partida = partidas[codigo_partida(numero, renglon.renglon)]
        assert abs(partida.total - renglon.total) <= TOLERANCIA, (
            f"renglon {renglon.renglon} ({renglon.descripcion}): "
            f"{partida.total} != {renglon.total}"
        )


@pytest.mark.parametrize("numero", (1, 2))
def test_cada_renglon_reproduce_su_precio_unitario_impreso(sesion_telecom, numero):
    """Los renglones sin mecanismo declarado valen exactamente el precio unitario del PDF."""
    partidas = _por_codigo(presupuesto_arenaza(sesion_telecom, numero))

    comparados = 0
    for renglon in RENGLONES[numero]:
        if renglon.cantidad is None or renglon.precio_unitario is None:
            continue
        if renglon.cantidad * renglon.precio_unitario != renglon.total:
            continue
        partida = partidas[codigo_partida(numero, renglon.renglon)]
        assert abs(partida.resultado.precio_unitario - renglon.precio_unitario) <= TOLERANCIA, (
            f"renglon {renglon.renglon} ({renglon.descripcion})"
        )
        comparados += 1

    assert comparados == len(RENGLONES[numero]) - CON_MECANISMO[numero]


# ---------------------------------------------------------------------------------------------
# Los mecanismos de los cuatro renglones que el PDF no cierra con cantidad x precio unitario
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("numero", "indice"), ((1, 3), (2, 5)))
def test_el_tubo_corrugado_conserva_metros_y_precio_por_tubo(sesion_telecom, numero, indice):
    """El precio impreso (99,75) es por tubo de 30 m: el APU compra 1/30 de tubo por metro."""
    renglon = _renglon(numero, indice)
    partida = _por_codigo(presupuesto_arenaza(sesion_telecom, numero))[
        codigo_partida(numero, indice)
    ]

    assert partida.item.cantidad == renglon.cantidad == Decimal("90")
    assert partida.item.unidad == "m"
    (tubo,) = partida.apu.materiales
    assert tubo.precio == renglon.precio_unitario == Decimal("99.75")
    assert tubo.cantidad == Decimal("1") / METROS_POR_TUBO
    assert abs(partida.total - renglon.total) <= TOLERANCIA


def test_el_tubo_del_presupuesto_2_registra_los_80_m_de_computos(sesion_telecom):
    """La inconsistencia 80/90 viaja con el ítem para que la Sesión M1.3 la audite."""
    partida = _por_codigo(presupuesto_arenaza(sesion_telecom, 2))[codigo_partida(2, 5)]

    assert partida.item.cantidad == arenaza.TUBO_CORRUGADO["cantidad_presupuesto"]
    assert partida.item.parametros["cantidad_computos"] == (
        arenaza.TUBO_CORRUGADO["cantidad_computos"]
    )
    assert partida.item.origen_id == arenaza.TUBO_CORRUGADO["origen_presupuesto"]


@pytest.mark.parametrize("indice", (14, 18))
def test_los_renglones_contradictorios_conservan_precio_y_total_impresos(sesion_telecom, indice):
    """P2 14 y 18: el total impreso no es `cantidad x precio`; se reproduce el total y se conserva
    el precio unitario del PDF, con la diferencia declarada en una línea de ajuste propia."""
    renglon = _renglon(2, indice)
    partida = _por_codigo(presupuesto_arenaza(sesion_telecom, 2))[codigo_partida(2, indice)]

    insumo, ajuste = partida.apu.materiales
    assert insumo.precio == renglon.precio_unitario
    assert insumo.cantidad == Decimal("1")
    assert ajuste.descripcion.startswith(MARCA_AJUSTE)
    assert renglon.origen in ajuste.descripcion
    assert ajuste.unidad == UNIDAD_SUMA_GLOBAL, "el ajuste no se disfraza de material por pieza"

    diferencia_impresa = renglon.total - renglon.cantidad * renglon.precio_unitario
    assert abs(ajuste.total * renglon.cantidad - diferencia_impresa) <= TOLERANCIA
    assert abs(partida.total - renglon.total) <= TOLERANCIA
    assert partida.total != renglon.cantidad * renglon.precio_unitario


def test_solo_hay_dos_lineas_de_ajuste_en_todo_el_catalogo(sesion_telecom):
    """Anti-enmascaramiento: los ajustes son exactamente los dos renglones que el PDF no cierra.

    Si algún mecanismo futuro empezara a tapar diferencias con líneas de ajuste, esta prueba lo
    delata. Fija además la obligación documentada para la Sesión M1.3: estas dos líneas son
    artefactos de reproducción (`unidad = "sg"`, importes que no son precio de nada) y quedan fuera
    de todo contraste de precios y de toda normalización de descripciones de insumo.
    """
    ajustes = [
        (codigo, linea)
        for numero in (1, 2)
        for codigo, composicion in composiciones_desde_catalogo(sesion_telecom, numero).items()
        for linea in composicion.materiales
        if linea.descripcion.startswith(MARCA_AJUSTE)
    ]

    assert [codigo for codigo, _ in ajustes] == [codigo_partida(2, 14), codigo_partida(2, 18)]
    assert all(linea.unidad == UNIDAD_SUMA_GLOBAL for _, linea in ajustes)

    insumos = Catalogo(sesion_telecom).insumos()
    assert sum(insumo.descripcion.startswith(MARCA_AJUSTE) for insumo in insumos) == 2


def test_la_marca_de_ajuste_no_colisiona_con_la_regla_de_verificacion_r6():
    """La marca se persiste como descripción de insumo y aparecerá en el informe de M1.3, donde
    "R6" significa `CriterioDepreciacion` (CLAUDE.md §7): no puede contener esa cadena."""
    assert "R6" not in MARCA_AJUSTE


def test_micelaneos_se_representa_como_suma_global(sesion_telecom):
    """El PDF solo declara un total (100,00): se representa como 1 suma global x 100,00."""
    renglon = _renglon(1, 14)
    partida = _por_codigo(presupuesto_arenaza(sesion_telecom, 1))[codigo_partida(1, 14)]

    assert renglon.cantidad is None and renglon.precio_unitario is None
    assert partida.item.unidad == partida.apu.unidad == UNIDAD_SUMA_GLOBAL
    assert partida.item.cantidad == Decimal("1")
    assert partida.resultado.precio_unitario == renglon.total == Decimal("100.00")


@pytest.mark.parametrize(("numero", "indice"), ((1, 12), (2, 26)))
def test_la_guaya_es_un_equipo_con_su_depreciacion_declarada(sesion_telecom, numero, indice):
    """La guaya guía es la única herramienta reutilizable del presupuesto: entra como equipo."""
    renglon = _renglon(numero, indice)
    partida = _por_codigo(presupuesto_arenaza(sesion_telecom, numero))[
        codigo_partida(numero, indice)
    ]

    assert partida.apu.materiales == ()
    (guaya,) = partida.apu.equipos
    assert guaya.precio == renglon.precio_unitario
    assert guaya.depreciacion == DEPRECIACION_HERRAMIENTA
    assert abs(partida.total - renglon.total) <= TOLERANCIA


# ---------------------------------------------------------------------------------------------
# La política de mano de obra del PDF (opción 1 del hallazgo 1 de la bitácora I5-telecom)
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("numero", (1, 2))
def test_la_mano_de_obra_sintetica_es_el_50_por_ciento_del_total(sesion_telecom, numero):
    con_mo = presupuesto_arenaza(sesion_telecom, numero, con_mano_obra_sintetica=True)

    esperado = TOTALES[numero] * (1 + FRACCION_MANO_OBRA)
    assert abs(con_mo.total - esperado) <= TOLERANCIA
    for partida in con_mo.partidas:
        (linea,) = partida.apu.mano_obra
        assert linea.cantidad == Decimal("1")
        materiales_y_equipos = partida.resultado.materiales + partida.resultado.equipos
        assert abs(partida.resultado.mano_obra - FRACCION_MANO_OBRA * materiales_y_equipos) <= (
            TOLERANCIA
        )


@pytest.mark.parametrize("numero", (1, 2))
def test_el_catalogo_no_persiste_la_mano_de_obra_sintetica(sesion_telecom, numero):
    """La política es de la capa de catálogo, no del PDF: SQLite guarda el presupuesto impreso."""
    composiciones = composiciones_desde_catalogo(sesion_telecom, numero)

    assert len(composiciones) == len(RENGLONES[numero])
    assert all(composicion.mano_obra == () for composicion in composiciones.values())


# ---------------------------------------------------------------------------------------------
# El catálogo multidominio
# ---------------------------------------------------------------------------------------------


def test_las_partidas_telecom_conviven_con_la_linea_base_civil(sesion_telecom):
    catalogo = Catalogo(sesion_telecom)

    telecom = [partida.codigo for partida in catalogo.partidas(Dominio.TELECOM)]
    civil = [partida.codigo for partida in catalogo.partidas(Dominio.CIVIL)]

    assert len(telecom) == len(RENGLONES[1]) + len(RENGLONES[2])
    assert all(codigo.startswith("TC-") for codigo in telecom)
    assert len(civil) == 5
    assert all(codigo.startswith("LB-") for codigo in civil)


@pytest.mark.parametrize("numero", (1, 2))
def test_los_items_son_trazables_a_la_fila_del_pdf(sesion_telecom, numero):
    for item, renglon in zip(items_arenaza(numero), RENGLONES[numero], strict=True):
        assert item.origen_id == renglon.origen
        assert item.dominio is Dominio.TELECOM
        assert item.codigo_partida == codigo_partida(numero, renglon.renglon)


def test_sembrar_telecom_es_idempotente(sesion_telecom):
    """Sembrar dos veces no duplica partidas ni lanza: el seed se puede volver a correr."""
    antes = len(Catalogo(sesion_telecom).partidas(Dominio.TELECOM))

    sembrar_telecom(sesion_telecom)

    assert len(Catalogo(sesion_telecom).partidas(Dominio.TELECOM)) == antes


def test_los_parametros_arenaza_no_llevan_estructura_venezolana():
    """El PDF no imprime FCAS, bono, administración ni utilidad: los cuatro factores van en cero."""
    assert PARAMETROS_ARENAZA.fcas == Decimal("0")
    assert PARAMETROS_ARENAZA.bono_alimentacion == Decimal("0")
    assert PARAMETROS_ARENAZA.administracion == Decimal("0")
    assert PARAMETROS_ARENAZA.utilidad == Decimal("0")
