"""Auditoría del presupuesto telecom ARENAZA + primer UC‑02 fuera de civil (Sesión M1.3).

Compuerta GM1: las siete reglas de verificación (CLAUDE.md §7) corren sobre el presupuesto
ARENAZA armado en la Sesión M1.2 (`scripts.seed_telecom.presupuesto_arenaza`) y el hallazgo 80/90
del tubo corrugado (presupuesto 2, renglón 5: 80 m en "Computos metricos" vs 90 m en
"Presupuesto", `data/telecom/fuentes/README.md`) sale del informe de auditoría con su `origen_id`,
en vez de vivir solo en la documentación. Además, dos listas de precios fechadas —
`data/telecom/fuentes/lista_arenaza.csv` (18/05/2026) y `lista_maprex_2026-07.csv` (09/07/2026,
derivada de `data/precios/maprex_2026-07/referencia_telecom.csv`) — se cargan por el flujo UC‑02
existente (`core.catalog.precios`, Sesión I1) y producen el primer histórico de `CambioPrecio`
fuera del dominio civil.

Qué regla detecta el 80/90 y por qué: la Sesión M1.2 dejó las dos cantidades del tubo en
`ItemComputo.parametros` pero sin `regla` ("la cantidad se transcribe, no se deriva",
`docs/bitacora/2026-09-02-M1.2-catalogo-telecom.md`), así que, tal como quedó wireado, NINGUNA
regla existente lo veía: R1 (`TrazabilidadGeometrica`) solo compara `regla` evaluada contra
`cantidad`, y sin `regla` no genera hallazgo para un ítem TABULAR; R7
(`ConciliacionPresupuestoPlan`) solo actúa si el presupuesto declara curva/plan de trabajo, y el
presupuesto ARENAZA no declara ninguno. Esta sesión cierra esa brecha por el lado de datos, no de
núcleo: `scripts/seed_telecom.py`
(`item_de`) ahora declara, solo para ese renglón, `regla = REGLA_TUBO_CORRUGADO =
"cantidad_computos"` — una referencia directa al parámetro que ya viajaba con el ítem, no una
fórmula geométrica nueva. R1 no exige que `regla` sea una fórmula: solo evalúa lo que se declare
contra los `parametros` declarados y lo compara con `cantidad`  (CLAUDE.md §7, R1;
`core/verification/reglas.py::TrazabilidadGeometrica`). Con eso, R1 compara la cantidad impresa en
"Presupuesto" (90, la que persiste como `cantidad`) contra la de "Computos metricos" (80, evaluando
la regla) y emite un hallazgo ERROR con `origen_id = "Presupuesto_2_ARENAZA.pdf:2:5"`. Ningún
archivo de `core/` cambió: la regla ya existía y ya hacía exactamente esta comparación para
cualquier otro dominio.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.catalog.precios import crear_lista_desde_archivo, leer_lista_precios, registrar_cambios
from core.contracts.verificacion import Severidad
from core.verification import InformeAuditoria, auditar
from scripts.derivar_listas_telecom import (
    FECHA_LISTA_MAPREX,
    RUTA_LISTA_ARENAZA,
    RUTA_LISTA_MAPREX,
)
from scripts.seed_telecom import (
    FECHA_ARENAZA,
    MARCA_AJUSTE,
    MONEDA,
    codigo_partida,
    presupuesto_arenaza,
    sembrar_telecom,
)
from tests.fixtures import presupuestos_arenaza as arenaza

#: El renglón del hallazgo: presupuesto 2, ítem 5 ("Tubo Corrugado Flexible 1 Pulgada 30 MTS").
CODIGO_TUBO = codigo_partida(2, 5)
ORIGEN_TUBO = arenaza.TUBO_CORRUGADO["origen_presupuesto"]


@pytest.fixture
def sesion_telecom(sesion):
    """La sesión de integración (línea base civil ya sembrada) con el catálogo telecom cargado."""
    sembrar_telecom(sesion)
    return sesion


def _hallazgos_de(regla: str, informe: InformeAuditoria) -> list:
    return [h for h in informe.hallazgos if h.regla == regla]


# ---------------------------------------------------------------------------------------------
# (a) La auditoría corre sobre el presupuesto telecom completo (los dos presupuestos ARENAZA)
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("numero", (1, 2))
def test_la_auditoria_corre_sobre_el_presupuesto_telecom_completo(sesion_telecom, numero):
    presupuesto = presupuesto_arenaza(sesion_telecom, numero)

    informe = auditar(presupuesto)

    assert isinstance(informe, InformeAuditoria)
    assert informe.codigo_presupuesto == presupuesto.codigo
    # El informe no altera el presupuesto auditado (RF‑23): mismas partidas, mismo total.
    assert presupuesto.total == presupuesto_arenaza(sesion_telecom, numero).total


# ---------------------------------------------------------------------------------------------
# (b) Exactamente un hallazgo del tubo corrugado 80/90, con origen_id no vacío
# ---------------------------------------------------------------------------------------------


def test_el_tubo_corrugado_produce_exactamente_un_hallazgo_80_90(sesion_telecom):
    informe = auditar(presupuesto_arenaza(sesion_telecom, 2))

    relacionados = [h for h in informe.hallazgos if ORIGEN_TUBO in h.origen_ids]

    assert len(relacionados) == 1
    (hallazgo,) = relacionados
    assert hallazgo.regla == "R1"
    assert hallazgo.severidad == Severidad.ERROR
    assert hallazgo.origen_ids  # trazable: no vacío (CLAUDE.md §2, principio 6)
    assert hallazgo.origen_ids == (ORIGEN_TUBO,)
    # 90 (impreso en "Presupuesto", el que vale como cantidad) vs 80 (impreso en "Computos
    # metricos", el que declara la regla): exactamente los dos valores del hallazgo de fuente.
    assert hallazgo.valor_observado == arenaza.TUBO_CORRUGADO["cantidad_presupuesto"] == Decimal(90)
    assert hallazgo.valor_esperado == arenaza.TUBO_CORRUGADO["cantidad_computos"] == Decimal(80)
    assert informe.partida_de(hallazgo) == CODIGO_TUBO


def test_el_presupuesto_1_no_tiene_el_hallazgo_80_90(sesion_telecom):
    """El presupuesto 1 no trae la inconsistencia: su tubo corrugado trae 90 m en las dos tablas
    del PDF (`data/telecom/fuentes/README.md`), así que no declara `regla` y R1 no dice nada de él.
    """
    informe = auditar(presupuesto_arenaza(sesion_telecom, 1))

    assert [h for h in informe.hallazgos if h.regla == "R1"] == []


# ---------------------------------------------------------------------------------------------
# (c) R5 (balance volumetrico, civil) no reporta error para un dominio que no declara balance
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("numero", (1, 2))
def test_r5_no_reporta_error_sin_balance_declarado(sesion_telecom, numero):
    """RF‑23 / `docs/bitacora/2026-08-31-plan-multidominio.md`: una regla sin datos que auditar se
    reporta sin abortar el informe y sin fingir un error. Ningún `ItemComputo` telecom declara la
    directiva `_balance` (M1.2: "las especificaciones del item se limitan a `_unidad_original`"),
    así que R5 no tiene nada que evaluar: su implementación realiza el "sin datos" como una lista
    vacía (mismo comportamiento que fija `tests/unit/test_verification.py::
    test_r5_no_reporta_nada_si_el_balance_se_cumple` para el caso civil sin balance a verificar),
    no como un `Hallazgo` INFO explícito. Lo que importa para RF‑23 y se fija aquí es la garantía
    de fondo: nunca ERROR ni CRITICO por falta de datos.
    """
    informe = auditar(presupuesto_arenaza(sesion_telecom, numero))

    hallazgos_r5 = _hallazgos_de("R5", informe)

    assert hallazgos_r5 == []
    assert all(h.severidad not in (Severidad.ERROR, Severidad.CRITICO) for h in hallazgos_r5)


# ---------------------------------------------------------------------------------------------
# Obligación de la Sesión M1.2: las líneas de ajuste quedan fuera de todo contraste de precios
# ---------------------------------------------------------------------------------------------


def test_las_listas_uc02_excluyen_las_lineas_de_ajuste():
    """`scripts/seed_telecom.py` (mecanismo 2) obliga a excluir de todo contraste de precios y de
    toda normalización semántica las líneas cuya descripción empieza por `MARCA_AJUSTE`: no son
    insumos de mercado, son artefactos de reproducción del total impreso. Ninguna de las dos listas
    de esta sesión las menciona.
    """
    for ruta in (RUTA_LISTA_ARENAZA, RUTA_LISTA_MAPREX):
        precios = leer_lista_precios(ruta)
        assert precios, f"{ruta.name} no debe estar vacia"
        assert not any(precio.descripcion.startswith(MARCA_AJUSTE) for precio in precios), ruta.name


# ---------------------------------------------------------------------------------------------
# (d) UC‑02: dos listas fechadas producen el primer historico de CambioPrecio en telecom
# ---------------------------------------------------------------------------------------------


def test_uc02_carga_arenaza_y_maprex_y_registra_cambios_de_precio(sesion_telecom):
    resumen_arenaza = crear_lista_desde_archivo(
        sesion_telecom,
        RUTA_LISTA_ARENAZA,
        nombre="Precios ARENAZA (UC-02) 18/05/2026",
        moneda=MONEDA,
        fecha_vigencia=FECHA_ARENAZA,
        origen=RUTA_LISTA_ARENAZA.name,
    )
    resumen_maprex = crear_lista_desde_archivo(
        sesion_telecom,
        RUTA_LISTA_MAPREX,
        nombre="Precios MaPreX 2026-07",
        moneda=MONEDA,
        fecha_vigencia=FECHA_LISTA_MAPREX,
        origen=RUTA_LISTA_MAPREX.name,
    )

    # Los insumos de las dos listas ya existen en el catalogo (mismas descripciones y unidades que
    # persistio scripts/seed_telecom.py): ninguna fila queda como "desconocida".
    assert resumen_arenaza.desconocidos == ()
    assert resumen_maprex.desconocidos == ()

    cambios = registrar_cambios(sesion_telecom, resumen_arenaza.lista, resumen_maprex.lista)

    # Exactamente la correspondencia defendible (`scripts/derivar_listas_telecom.py`,
    # `CORRESPONDENCIA`; README de la carpeta): tres insumos en la misma unidad de venta y el tubo
    # corrugado, que el catalogo guarda bajo las dos descripciones impresas (P1 y P2).
    assert len(cambios) == 5
    for cambio in cambios:
        assert cambio.lista_anterior.fecha_vigencia == FECHA_ARENAZA
        assert cambio.lista_nueva.fecha_vigencia == FECHA_LISTA_MAPREX
        assert cambio.fecha == FECHA_LISTA_MAPREX
        assert cambio.precio_nuevo != cambio.precio_anterior
        # La obligacion de M1.2 tambien se cumple en los efectos: ningun ajuste cambia de precio.
        assert not cambio.insumo.descripcion.startswith(MARCA_AJUSTE)

    descripciones_cambiadas = {cambio.insumo.descripcion for cambio in cambios}
    assert descripciones_cambiadas == {
        "Anillo E.m.t. 2",
        "Toma Doble Con Tierra 270 20a Con Placa Blanca",
        "Cajetin Plástico 4x2 Pvc Con Grapa Metálica.",
        "Tubo Corrugado Flexible 1 Pulgada (tubo de 30 m)",
        "Tubo Corrugado Flexible 1 Pulgada 30 MTS (tubo de 30 m)",
    }
    # El insumo del hallazgo 80/90 es tambien el del contraste de mercado: 99,75 USD por tubo de
    # 30 m en ARENAZA frente a la referencia MaPreX por metro convertida al mismo tubo.
    tubo = next(c for c in cambios if c.insumo.descripcion.startswith("Tubo Corrugado"))
    assert tubo.precio_anterior == Decimal("99.75")
    assert tubo.precio_nuevo < tubo.precio_anterior
