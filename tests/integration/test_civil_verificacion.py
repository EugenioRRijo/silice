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


# ---------------------------------------------------------------------------------------------
# INV-096 (C5): las especificaciones de cada objeto civil llegan solo a la partida a la que se
# refieren. La columna `especificaciones` de la muestra describe el elemento construido de cada
# objeto: `material=concreto` en T-01 son las paredes de concreto de la tanquilla, y
# `diametro=4 pulg;material=PVC` en Z-01 es la tuberia. La excavacion (de las dos filas) y el
# encofrado (de madera) no son de concreto ni de PVC: si reciben esas claves, R4 emite cuatro INFO
# «no es contrastable» de ruido (reproduccion de GC4, bitacora del cierre, INV-095 e INV-096).
# ---------------------------------------------------------------------------------------------

#: Lo que declara `data/samples/civil/tanquillas_y_zanja.csv`, transcrito a mano de su columna
#: `especificaciones` (oraculo independiente del parser del adaptador), por la partida que lo lleva.
_ESPECIFICACIONES_POR_PARTIDA = {
    ("T-01", CODIGOS["concreto"]): {"material": "concreto"},
    ("Z-01", CODIGOS["tuberia"]): {"diametro": "4 pulg", "material": "PVC"},
}


def test_la_muestra_civil_no_da_hallazgos_r4_de_ruido():
    informe = auditar(_presupuesto_de(_extraer_muestra()))

    # Las dos especificaciones que llegan a su partida aparecen en el texto de su APU (el concreto
    # en el de LB-04-CON; «4 pulg» y «PVC» en el de LB-02-TUB): R4 no tiene nada que decir.
    assert [h.descripcion for h in informe.hallazgos if h.regla == "R4"] == []


def test_la_excavacion_y_el_encofrado_no_reciben_las_especificaciones_del_objeto():
    items = _extraer_muestra()
    auxiliares = [
        item
        for item in items
        if item.codigo_partida in (CODIGOS["excavacion"], CODIGOS["encofrado"])
    ]

    # Tres ítems auxiliares: la excavación de T-01, la de Z-01 y el encofrado de T-01.
    assert sorted((item.origen_id, item.codigo_partida) for item in auxiliares) == sorted(
        [
            ("T-01", CODIGOS["encofrado"]),
            ("T-01", CODIGOS["excavacion"]),
            ("Z-01", CODIGOS["excavacion"]),
        ]
    )
    assert all(item.especificaciones == {} for item in auxiliares)


def test_cada_especificacion_llega_a_la_partida_a_la_que_se_refiere():
    items = _extraer_muestra()
    con_especificaciones = {
        (item.origen_id, item.codigo_partida): dict(item.especificaciones)
        for item in items
        if item.especificaciones and item.codigo_partida != CODIGOS["relleno"]
    }

    assert con_especificaciones == _ESPECIFICACIONES_POR_PARTIDA


def test_r4_sigue_viendo_el_diametro_contradicho_de_la_tuberia(tmp_path):
    """La otra dirección: quitar el ruido no puede apagar R4 sobre la partida a la que se refiere.

    Con la muestra alterada a `diametro=3/4 pulg` (el hallazgo 5 de la línea base), la tubería
    recibe la especificación y R4 da un ERROR sobre LB-02-TUB con el origen Z-01.
    """
    alterada = tmp_path / "tanquillas_y_zanja_3_4.csv"
    texto = RUTA_MUESTRA.read_text(encoding="utf-8")
    assert "diametro=4 pulg" in texto
    alterada.write_text(texto.replace("diametro=4 pulg", "diametro=3/4 pulg"), encoding="utf-8")

    items = tuple(AdaptadorCivilTabular(codigos=CODIGOS).extraer(alterada))
    informe = auditar(_presupuesto_de(items))

    errores_r4 = [
        h for h in informe.hallazgos if h.regla == "R4" and h.severidad == Severidad.ERROR
    ]
    assert len(errores_r4) == 1
    assert errores_r4[0].origen_ids == ("Z-01",)
    assert CODIGOS["tuberia"] in errores_r4[0].descripcion
    assert "3/4 pulg" in errores_r4[0].descripcion


def test_r4_sigue_viendo_el_material_declarado_del_concreto(tmp_path):
    """La otra dirección para la tanquilla (T-6 de la revisión de la pista P de C5).

    Con `material=acero` en T-01, el concreto recibe la especificación y R4 la señala sobre
    LB-04-CON con el origen T-01, y solo ahí: ni el encofrado ni la excavación la reciben. Es INFO
    y no ERROR porque R4 solo declara contradicción entre pares número-unidad (`3/4 pulg` frente a
    `4 pulg`), y un material no lo es: «acero» no aparece en el texto del APU de concreto y queda
    como no contrastable (`core/verification/reglas.py`, `CorrespondenciaEspecificaciones`).
    """
    alterada = tmp_path / "tanquillas_y_zanja_acero.csv"
    texto = RUTA_MUESTRA.read_text(encoding="utf-8")
    assert texto.count("material=concreto") == 1
    alterada.write_text(texto.replace("material=concreto", "material=acero"), encoding="utf-8")

    items = tuple(AdaptadorCivilTabular(codigos=CODIGOS).extraer(alterada))
    informe = auditar(_presupuesto_de(items))

    hallazgos_r4 = [h for h in informe.hallazgos if h.regla == "R4"]
    assert len(hallazgos_r4) == 1, [h.descripcion for h in hallazgos_r4]
    (hallazgo,) = hallazgos_r4
    assert hallazgo.severidad == Severidad.INFO
    assert hallazgo.origen_ids == ("T-01",)
    assert CODIGOS["concreto"] in hallazgo.descripcion
    assert "'acero'" in hallazgo.descripcion
