"""Presupuesto de sistemas por puntos de función de extremo a extremo (Sesión M3.2, compuerta GM3).

`AdaptadorSistemas` extrae de `data/samples/sistemas/alcance_funcional.csv` un ítem por caso de uso
(PFNA con la regla IFPUG trazable, unidad `pf`) → `scripts/seed_sistemas.py` siembra el catálogo
(una partida `SIS-*` por caso de uso con el APU de un punto de función de
`tests/fixtures/tarifas_sistemas.py`, tarifas del tabulador CIV jul‑2026) → el presupuesto se arma
desde SQLite y lo valora el motor puro → las siete reglas lo auditan (R1 reevalúa la regla de
puntos de función; R3 acepta `pf`) → UC‑02 carga la lista canónica de tarifas. Nada toca `core/`.

Total esperado, calculado **a mano** antes de correr el flujo: 145 PF (27 + 19 + 18 + 14 + 20 + 4
+ 27 + 12 + 4, `data/samples/sistemas/README.md`) × 110,992365 USD/PF (README de
`data/sistemas/fuentes/`) = 16 093,892925 USD. Se fija como regresión exacta.

UC‑02 en este dominio: la única lista publicada es el tabulador con el que se sembró el catálogo;
cargar la lista canónica crea una lista nueva sin cambios de precio y la prueba lo afirma en vez
de fabricar un histórico. El histórico empieza con una encuesta salarial TI fechada.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from adapters.sistemas.adaptador import REGLA_PUNTOS_FUNCION
from core.catalog.precios import crear_lista_desde_archivo, registrar_cambios
from core.contracts import Severidad
from core.costing import calcular_apu
from core.verification import auditar
from scripts.seed_sistemas import (
    CODIGO_PRESUPUESTO,
    MONEDA,
    RUTA_LISTA_CANONICA,
    composiciones_desde_catalogo,
    items_sistemas,
    lista_sistemas,
    presupuesto_sistemas,
    sembrar_sistemas,
)
from tests.fixtures import tarifas_sistemas as sis

TOTAL_PF = Decimal("145")
PRECIO_UNITARIO_PF = Decimal("110.992365")
#: Calculado a mano (ver docstring del módulo).
TOTAL_ESPERADO = Decimal("16093.892925")
CASOS_DE_USO = 9


@pytest.fixture
def sesion_sistemas(sesion):
    """La sesión de integración (línea base civil sembrada) con el catálogo de sistemas cargado."""
    sembrar_sistemas(sesion)
    return sesion


def _hallazgos(informe, regla):
    return [h for h in informe.hallazgos if h.regla == regla]


# ---------------------------------------------------------------------------------------------
# Adaptador -> un item por caso de uso, con la regla IFPUG declarada
# ---------------------------------------------------------------------------------------------


def test_el_adaptador_produce_un_item_por_caso_de_uso_con_regla():
    items = items_sistemas()

    assert len(items) == CASOS_DE_USO
    assert sum(item.cantidad for item in items) == TOTAL_PF
    for item in items:
        assert item.codigo_partida.startswith("SIS-")
        assert item.origen_id.startswith("SI-")
        assert item.regla == REGLA_PUNTOS_FUNCION
        assert item.unidad == sis.UNIDAD_PF


# ---------------------------------------------------------------------------------------------
# (a) Total estable, verificado a mano; el catalogo reproduce el APU del fixture
# ---------------------------------------------------------------------------------------------


def test_total_estable_calculado_a_mano(sesion_sistemas):
    presupuesto = presupuesto_sistemas(sesion_sistemas)

    assert presupuesto.codigo == CODIGO_PRESUPUESTO
    assert presupuesto.moneda == MONEDA
    assert len(presupuesto.partidas) == CASOS_DE_USO
    assert presupuesto.total > 0
    assert presupuesto.total == TOTAL_ESPERADO
    for partida in presupuesto.partidas:
        assert partida.resultado.precio_unitario == PRECIO_UNITARIO_PF


def test_el_catalogo_reproduce_el_apu_por_punto_de_funcion(sesion_sistemas):
    esperado = calcular_apu(sis.APU_PUNTO_FUNCION, sis.PARAMETROS_SISTEMAS)
    composiciones = composiciones_desde_catalogo(sesion_sistemas)

    assert set(composiciones) == {item.codigo_partida for item in items_sistemas()}
    for composicion in composiciones.values():
        assert composicion.unidad == sis.UNIDAD_PF
        assert composicion.rendimiento == sis.RENDIMIENTO_PF
        assert not composicion.materiales and not composicion.equipos
        assert len(composicion.mano_obra) == len(sis.APU_PUNTO_FUNCION.mano_obra)
        resultado = calcular_apu(composicion, sis.PARAMETROS_SISTEMAS)
        assert resultado.costo_directo == esperado.costo_directo
        assert resultado.precio_unitario == esperado.precio_unitario


# ---------------------------------------------------------------------------------------------
# (b) Auditoria: R1 reevalua la regla IFPUG, R3 acepta la unidad pf, y R1 muerde si no cuadra
# ---------------------------------------------------------------------------------------------


def test_la_auditoria_no_reporta_errores_r1_acepta_ifpug_y_r3_acepta_pf(sesion_sistemas):
    informe = auditar(presupuesto_sistemas(sesion_sistemas))

    assert _hallazgos(informe, "R1") == []
    assert _hallazgos(informe, "R3") == []  # "pf" en el item y en el APU: coherente
    assert all(h.severidad not in (Severidad.ERROR, Severidad.CRITICO) for h in informe.hallazgos)
    assert informe.cumple
    assert [h.severidad for h in _hallazgos(informe, "R2")] == [Severidad.INFO]
    assert _hallazgos(informe, "R5") == []


def test_r1_detecta_puntos_de_funcion_que_no_salen_de_la_regla(sesion_sistemas):
    items = items_sistemas()
    alterado = replace(items[0], cantidad=items[0].cantidad + 1)

    informe = auditar(presupuesto_sistemas(sesion_sistemas, items=[alterado, *items[1:]]))

    (hallazgo,) = _hallazgos(informe, "R1")
    assert hallazgo.severidad == Severidad.ERROR
    assert hallazgo.origen_ids == (alterado.origen_id,)
    assert hallazgo.valor_observado == alterado.cantidad
    assert hallazgo.valor_esperado == items[0].cantidad
    assert not informe.cumple


# ---------------------------------------------------------------------------------------------
# (c) UC-02: la lista canonica de tarifas se carga completa y sin cambios fabricados
# ---------------------------------------------------------------------------------------------


def test_uc02_carga_la_lista_de_tarifas_sin_desconocidos_y_sin_cambios_fabricados(sesion_sistemas):
    anterior = lista_sistemas(sesion_sistemas)

    resumen = crear_lista_desde_archivo(
        sesion_sistemas,
        RUTA_LISTA_CANONICA,
        nombre="Tarifas tabulador CIV 2026-07 (UC-02)",
        moneda=MONEDA,
        fecha_vigencia=sis.FECHA_TABULADOR,
        origen=RUTA_LISTA_CANONICA.name,
    )

    assert resumen.desconocidos == ()  # los tres roles existen en el catalogo
    assert registrar_cambios(sesion_sistemas, anterior, resumen.lista) == []
    assert presupuesto_sistemas(sesion_sistemas, lista=resumen.lista).total == TOTAL_ESPERADO
