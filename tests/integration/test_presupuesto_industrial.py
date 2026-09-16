"""Presupuesto de mantenimiento industrial de extremo a extremo (Sesión M2.2, compuerta GM2).

`AdaptadorIndustrial` extrae de `data/samples/industrial/activos_planta.csv` los ítems de cómputo
(intervenciones = `frecuencia_anual × horizonte_anios`, regla declarada) →
`scripts/seed_industrial.py` siembra el catálogo de mantenimiento
(`tests/fixtures/mantenimiento_industrial.py`, precios de la referencia MaPreX jul‑2026 como proxy
fechado: degradación GM2 declarada en `data/industrial/fuentes/README.md`) → el presupuesto se
arma desde SQLite y lo valora el motor puro → las siete reglas lo auditan (R1 reevalúa la regla de
intervenciones) → UC‑02 carga la lista canónica industrial. Nada de esto toca `core/`.

El total esperado se calculó **a mano** antes de correr el flujo: Σ (frecuencia × horizonte) ×
precio unitario manual de la Sesión M2.1 = 20 × 214,652631875 + 30 × 154,33506 +
20 × 147,82922825 + 30 × 208,146863375 = 18 124,094903750 USD. Se fija como regresión exacta.

Sobre UC‑02 en este dominio: la única lista publicada es la referencia MaPreX con la que se
sembró el catálogo; cargar la lista canónica por UC‑02 crea una lista nueva **sin cambios de
precio** (misma fuente), y así se afirma explícitamente: ningún `CambioPrecio` se fabrica con
datos que no existen. El histórico industrial empieza con la primera cotización de campo del
autor.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from adapters.industrial.adaptador import REGLA_INTERVENCIONES
from core.catalog.precios import crear_lista_desde_archivo, registrar_cambios
from core.contracts import Severidad
from core.costing import calcular_apu
from core.verification import auditar
from scripts.seed_industrial import (
    CODIGO_PRESUPUESTO,
    MONEDA,
    RUTA_LISTA_CANONICA,
    composiciones_desde_catalogo,
    items_industrial,
    items_sin_catalogo,
    lista_industrial,
    presupuesto_industrial,
    sembrar_industrial,
)
from tests.fixtures import mantenimiento_industrial as mnt

#: Calculado a mano (ver docstring del módulo) antes de correr el flujo.
TOTAL_ESPERADO = Decimal("18124.094903750")
#: Activos del registro sin partida en el catálogo (10 en el CSV, 4 costeados).
ACTIVOS_SIN_CATALOGO = 6


@pytest.fixture
def sesion_industrial(sesion):
    """La sesión de integración (línea base civil sembrada) con el catálogo industrial cargado."""
    sembrar_industrial(sesion)
    return sesion


def _hallazgos(informe, regla):
    return [h for h in informe.hallazgos if h.regla == regla]


# ---------------------------------------------------------------------------------------------
# Adaptador -> ítems con regla declarada
# ---------------------------------------------------------------------------------------------


def test_el_adaptador_alimenta_el_presupuesto_solo_con_los_activos_del_catalogo():
    items = items_industrial()

    assert [item.codigo_partida for item in items] == list(mnt.ACTIVOS_COSTEADOS)
    assert [item.origen_id for item in items] == list(mnt.ACTIVOS_COSTEADOS.values())
    for item in items:
        assert item.regla == REGLA_INTERVENCIONES
        parametros = item.parametros
        assert item.cantidad == parametros["frecuencia_anual"] * parametros["horizonte_anios"]
        assert item.unidad == mnt.UNIDAD_INTERVENCION
    # Los demas activos no se silencian: se declaran como pendientes de catalogo.
    assert len(items_sin_catalogo()) == ACTIVOS_SIN_CATALOGO
    assert {i.origen_id for i in items_sin_catalogo()}.isdisjoint({i.origen_id for i in items})


# ---------------------------------------------------------------------------------------------
# (a) Total > 0 y estable, verificado a mano; el catalogo reproduce el fixture
# ---------------------------------------------------------------------------------------------


def test_total_estable_calculado_a_mano(sesion_industrial):
    presupuesto = presupuesto_industrial(sesion_industrial)

    assert presupuesto.codigo == CODIGO_PRESUPUESTO
    assert presupuesto.moneda == MONEDA
    assert len(presupuesto.partidas) == len(mnt.COMPOSICIONES_MNT)
    assert presupuesto.total > 0
    assert presupuesto.total == TOTAL_ESPERADO


def test_el_catalogo_reproduce_los_precios_unitarios_del_fixture(sesion_industrial):
    presupuesto = presupuesto_industrial(sesion_industrial)

    for partida in presupuesto.partidas:
        esperado = calcular_apu(
            mnt.COMPOSICIONES_MNT[partida.item.codigo_partida], mnt.PARAMETROS_INDUSTRIAL
        )
        assert partida.resultado.precio_unitario == esperado.precio_unitario
        assert partida.resultado.costo_directo == esperado.costo_directo

    composiciones = composiciones_desde_catalogo(sesion_industrial)
    assert set(composiciones) == set(mnt.COMPOSICIONES_MNT)
    for codigo, composicion in composiciones.items():
        original = mnt.COMPOSICIONES_MNT[codigo]
        assert len(composicion.materiales) == len(original.materiales)
        assert len(composicion.equipos) == len(original.equipos)
        assert len(composicion.mano_obra) == len(original.mano_obra)
        assert composicion.rendimiento == original.rendimiento


# ---------------------------------------------------------------------------------------------
# (b) La auditoria corre; R1 reevalua frecuencia_anual x horizonte_anios y muerde si no cuadra
# ---------------------------------------------------------------------------------------------


def test_la_auditoria_no_reporta_errores_y_r1_acepta_la_regla_de_intervenciones(sesion_industrial):
    informe = auditar(presupuesto_industrial(sesion_industrial))

    assert _hallazgos(informe, "R1") == []
    assert all(h.severidad not in (Severidad.ERROR, Severidad.CRITICO) for h in informe.hallazgos)
    assert informe.cumple
    # R2 hace constar que no hay curva (INFO); R5 no tiene balance que verificar (lista vacia).
    assert [h.severidad for h in _hallazgos(informe, "R2")] == [Severidad.INFO]
    assert _hallazgos(informe, "R5") == []


def test_r1_detecta_una_cantidad_que_no_sale_de_la_regla(sesion_industrial):
    items = items_industrial()
    alterado = replace(items[0], cantidad=items[0].cantidad + 1)

    informe = auditar(presupuesto_industrial(sesion_industrial, items=[alterado, *items[1:]]))

    (hallazgo,) = _hallazgos(informe, "R1")
    assert hallazgo.severidad == Severidad.ERROR
    assert hallazgo.origen_ids == (alterado.origen_id,)
    assert hallazgo.valor_observado == alterado.cantidad
    assert hallazgo.valor_esperado == items[0].cantidad
    assert not informe.cumple


# ---------------------------------------------------------------------------------------------
# (c) UC-02: la lista canonica industrial se carga completa y sin cambios fabricados
# ---------------------------------------------------------------------------------------------


def test_uc02_carga_la_lista_canonica_sin_desconocidos_y_sin_cambios_fabricados(sesion_industrial):
    anterior = lista_industrial(sesion_industrial)

    resumen = crear_lista_desde_archivo(
        sesion_industrial,
        RUTA_LISTA_CANONICA,
        nombre="Precios MaPreX 2026-07 industrial (UC-02)",
        moneda=MONEDA,
        fecha_vigencia=mnt.FECHA_REFERENCIA,
        origen=RUTA_LISTA_CANONICA.name,
    )

    assert resumen.desconocidos == ()  # los 9 insumos existen en el catalogo
    cambios = registrar_cambios(sesion_industrial, anterior, resumen.lista)
    assert cambios == []  # misma fuente, ningun CambioPrecio inventado
    # La lista nueva valora el catalogo completo: el presupuesto se reconstruye igual con ella.
    assert presupuesto_industrial(sesion_industrial, lista=resumen.lista).total == TOTAL_ESPERADO
