"""UC‑04 de punta a punta, pasos 1 a 4 (RF‑19; INV‑011): cambiar el ancho de las tanquillas y
recalcular precios, curva y auditoría.

El paso 5 (RF‑20, el diferencial por partida contra la versión anterior) no tiene implementación:
está declarado «no implementado» en la ERS y en el plan de pruebas, y en las limitaciones
(decisión de Eugenio del 2026‑09‑23). Esta prueba compara los renglones de las dos versiones por su
cuenta, sin presentarlo como si fuera RF‑20.

Los ítems vienen de las reglas paramétricas del adaptador civil con los supuestos de la muestra
(`tests/fixtures/computo_civil.py`); los precios, de la línea base. Se usan tanquillas y tubería,
no la excavación de la zanja, para que ningún código de partida se repita (ver el hallazgo de
`plan_secuencial` registrado en la Tarea 11 del plan de C1).
"""

from __future__ import annotations

from decimal import Decimal

from adapters.civil.reglas import computar_tanquillas, computar_zanja
from core.budget import elaborar, plan_secuencial
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import composiciones_linea_base
from tests.fixtures.computo_civil import (
    CODIGOS,
    DESPERDICIO_TUBERIA,
    DIAMETRO_TUBERIA_M,
    ESPESOR_FONDO,
    SOBREANCHO,
)

GEOMETRIA = linea_base.GEOMETRIA_TANQUILLA
ANCHO_NUEVO = GEOMETRIA["a"] + Decimal("0.20")


def _items(ancho: Decimal):
    concreto, encofrado, excavacion = computar_tanquillas(
        origen_id="T-01",
        codigos=CODIGOS,
        a=ancho,
        h=GEOMETRIA["h"],
        e=GEOMETRIA["e"],
        n=linea_base.N_TANQUILLAS,
        sobreancho=SOBREANCHO,
        espesor_fondo=ESPESOR_FONDO,
    )
    _excavacion_zanja, tuberia = computar_zanja(
        origen_id="Z-01",
        codigos=CODIGOS,
        longitud=linea_base.LONGITUD_TUBERIA_M,
        ancho=linea_base.ZANJA["ancho"],
        profundidad=linea_base.ZANJA["profundidad"],
        diametro=DIAMETRO_TUBERIA_M,
        desperdicio=DESPERDICIO_TUBERIA,
    )
    return [concreto, encofrado, excavacion, tuberia]


def _elaborar(ancho: Decimal, codigo: str):
    return elaborar(
        _items(ancho),
        composiciones_linea_base(),
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=codigo,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
    )


def _por_codigo(presupuesto):
    """Un renglón por código: en este cómputo ningún código se repite."""
    return {partida.item.codigo_partida: partida for partida in presupuesto.partidas}


def test_uc04_recalcula_precios_curva_y_auditoria_al_cambiar_el_ancho():
    anterior = _elaborar(GEOMETRIA["a"], "UC04-1")
    nuevo = _elaborar(ANCHO_NUEVO, "UC04-2")
    antes = _por_codigo(anterior.presupuesto)
    despues = _por_codigo(nuevo.presupuesto)

    # Pasos 1 y 2: los ítems nuevos traen la expresión y el parámetro cambiado.
    assert antes.keys() == despues.keys()
    for clave in ("concreto", "encofrado", "excavacion"):
        item = despues[CODIGOS[clave]].item
        assert item.regla and item.parametros["a"] == ANCHO_NUEVO
    # Paso 3: se recalculan las partidas afectadas y ninguna otra; el precio unitario no cambia
    # porque el APU es el mismo.
    assert {codigo for codigo in antes if antes[codigo].total != despues[codigo].total} == {
        CODIGOS["concreto"],
        CODIGOS["encofrado"],
        CODIGOS["excavacion"],
    }
    assert all(
        antes[codigo].resultado.precio_unitario == despues[codigo].resultado.precio_unitario
        for codigo in antes
    )
    assert nuevo.presupuesto.total == sum(
        (partida.total for partida in nuevo.presupuesto.partidas), Decimal(0)
    )
    # Paso 4: curva regenerada que cierra en el total nuevo, y verificación ejecutada otra vez.
    # Ningún hallazgo de R1, de ninguna severidad: tras INV‑012 un parámetro ausente sería INFO y
    # un filtro por ERROR lo dejaría pasar.
    assert nuevo.presupuesto.total_curva == nuevo.presupuesto.total
    assert nuevo.informe.codigo_presupuesto == "UC04-2"
    assert not [h for h in nuevo.informe.hallazgos if h.regla == "R1"]
    assert nuevo.pendientes == ()
