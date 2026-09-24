"""Integración: el balance de relleno del adaptador civil tabular es resoluble por la regla R5.

Corrección 4b (Sesión I3.2, hallazgo de la Task 7). `AdaptadorCivilTabular` construía el balance de
relleno interpolando los códigos de partida sin llaves
(`"LB-01-EXC - LB-04-CON - LB-02-TUB * 0.008107338624"`); `core.verification.expresiones.
sustituir_codigos` solo reconoce referencias entre llaves (`{codigo}`), así que sin ellas los
nombres no se sustituían y `evaluar` lanzaba `ParametroFaltante`: la regla R5 reportaba "referencia
no resuelta" para todo presupuesto civil que usara este adaptador, en vez de verificar el balance.

Estas pruebas comprueban comportamiento real, no solo la forma del texto: el balance se evalúa y
coincide con la cantidad de relleno que emite el propio adaptador (primera prueba); un presupuesto
armado con la muestra civil no produce ningún hallazgo grave de R5 (segunda); y un relleno alterado
sí produce un hallazgo R5 de severidad ERROR (tercera).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from adapters.civil.tabular import AdaptadorCivilTabular
from core.contracts import ItemComputo, PartidaPresupuestada, Presupuesto, Severidad
from core.costing import calcular_apu
from core.verification import auditar
from core.verification.directivas import CLAVE_BALANCE
from core.verification.expresiones import evaluar, sustituir_codigos
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import composiciones_linea_base
from tests.fixtures.computo_civil import CODIGOS

RUTA_MUESTRA = (
    Path(__file__).resolve().parents[2] / "data" / "samples" / "civil" / "tanquillas_y_zanja.csv"
)


def _extraer_muestra() -> tuple[ItemComputo, ...]:
    return tuple(AdaptadorCivilTabular(codigos=CODIGOS).extraer(RUTA_MUESTRA))


def _cantidades_por_codigo(items: tuple[ItemComputo, ...]) -> dict[str, Decimal]:
    """Cantidad total de cada partida: la excavación viene de dos filas (tanquilla y zanja)."""
    totales: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for item in items:
        totales[item.codigo_partida] += item.cantidad
    return dict(totales)


def _presupuesto_de(items: tuple[ItemComputo, ...]) -> Presupuesto:
    """Un renglón por item, con el APU y el resultado de costeo de la línea base. Sin curva."""
    composiciones = composiciones_linea_base()
    partidas = tuple(
        PartidaPresupuestada(
            item=item,
            apu=composiciones[item.codigo_partida],
            resultado=calcular_apu(
                composiciones[item.codigo_partida], linea_base.PARAMETROS_LINEA_BASE
            ),
        )
        for item in items
    )
    return Presupuesto(
        codigo=linea_base.CODIGO_PRESUPUESTO,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        partidas=partidas,
    )


def test_el_balance_del_adaptador_es_resoluble_por_r5():
    items = _extraer_muestra()
    relleno = next(item for item in items if item.codigo_partida == CODIGOS["relleno"])
    cantidades = _cantidades_por_codigo(items)

    # No debe lanzar ParametroFaltante: las llaves permiten resolver cada código de partida.
    expandido = sustituir_codigos(relleno.especificaciones[CLAVE_BALANCE], cantidades)
    esperado = evaluar(expandido, {})

    # excavacion - concreto - volumen_tuberia: exactamente la misma cuenta que produjo la cantidad
    # de relleno que emitió el propio adaptador (adapters/civil/reglas.py:REGLA_RELLENO).
    assert esperado == relleno.cantidad


def test_auditoria_de_la_muestra_civil_no_reporta_balance():
    informe = auditar(_presupuesto_de(_extraer_muestra()))

    hallazgos_r5 = [h for h in informe.hallazgos if h.regla == "R5"]
    graves = [h for h in hallazgos_r5 if h.severidad >= Severidad.ERROR]
    assert graves == []
    assert not any("referencia no resuelta" in h.descripcion for h in hallazgos_r5)


def test_auditoria_detecta_relleno_alterado():
    items = _extraer_muestra()
    items_alterados = tuple(
        replace(item, cantidad=item.cantidad * Decimal("4"))
        if item.codigo_partida == CODIGOS["relleno"]
        else item
        for item in items
    )

    informe = auditar(_presupuesto_de(items_alterados))

    relleno_alterado = next(
        item for item in items_alterados if item.codigo_partida == CODIGOS["relleno"]
    )
    hallazgos_r5_error = [
        h
        for h in informe.hallazgos
        if h.regla == "R5"
        and h.severidad == Severidad.ERROR
        and relleno_alterado.origen_id in h.origen_ids
    ]
    assert len(hallazgos_r5_error) == 1
