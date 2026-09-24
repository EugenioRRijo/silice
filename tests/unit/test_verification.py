"""Pruebas unitarias del sistema de verificación (Sesión I4).

Cubren las tres piezas auxiliares del núcleo (evaluador de expresiones, normalización de texto y
convención de directivas), una prueba por regla sobre el presupuesto auditado y el informe.

Estas pruebas SÍ importan `adapters.civil`: comprueban que las expresiones y las claves de
directiva que escribe un adaptador son interpretables por el núcleo sin que el núcleo lo importe
(CLAUDE.md §2, hipótesis central).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

import pytest

from adapters.civil import reglas as reglas_civil
from adapters.civil.evaluador import evaluar_regla
from core.contracts import PuntoCurva, Severidad
from core.verification import (
    REGLAS,
    BalanceVolumetrico,
    CierreCurvaInversion,
    CoherenciaDimensional,
    ConciliacionPresupuestoPlan,
    CorrespondenciaEspecificaciones,
    CriterioDepreciacion,
    TrazabilidadGeometrica,
    auditar,
    directivas,
)
from core.verification.expresiones import (
    ExpresionInvalida,
    ParametroFaltante,
    evaluar,
    nombres_de,
    sustituir_codigos,
)
from core.verification.reglas import NO_APLICABLE, REGLA_NO_EVALUABLE
from core.verification.texto import es_numero, normalizar_texto, pares_numero_unidad, tokens
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import origen_de
from tests.fixtures.presupuesto_auditado import (
    BALANCE_RELLENO,
    presupuesto_con_siete_inconsistencias,
)

CENTIMO = Decimal("0.01")


def _redondeado(valor: Decimal) -> Decimal:
    return valor.quantize(CENTIMO, rounding=ROUND_HALF_UP)


@pytest.fixture(scope="module")
def presupuesto():
    return presupuesto_con_siete_inconsistencias()


def _errores(hallazgos):
    return [hallazgo for hallazgo in hallazgos if hallazgo.severidad >= Severidad.ERROR]


# ---------------------------------------------------------------------------------------------
# Evaluador de expresiones
# ---------------------------------------------------------------------------------------------


def test_el_evaluador_no_pierde_precision_decimal():
    assert evaluar("0.1 + 0.2", {}) == Decimal("0.3")


def test_el_evaluador_eleva_a_potencia_entera_de_forma_exacta():
    assert evaluar("a ** 2", {"a": Decimal("0.8")}) == Decimal("0.64")


@pytest.mark.parametrize(
    "expresion",
    [
        "__import__('os')",
        "a.b",
        "a[0]",
        "a if b else c",
        "'x'",
        "a and b",
        "a == b",
        "a % b",
        "~a",
        "a / 0",
        "2 +",
    ],
)
def test_el_evaluador_rechaza_todo_lo_que_no_sea_aritmetica(expresion):
    with pytest.raises(ExpresionInvalida):
        evaluar(expresion, {"a": Decimal("1"), "b": Decimal("2"), "c": Decimal("3")})


def test_el_evaluador_acepta_el_signo_unario_positivo():
    assert evaluar("+a - -a", {"a": Decimal("2")}) == Decimal("4")


def test_el_evaluador_indica_el_parametro_faltante():
    with pytest.raises(ParametroFaltante):
        evaluar("largo * ancho", {"largo": Decimal("2")})


@pytest.mark.parametrize(
    "expresion",
    [
        "1e999999 * 1e999999",
        "9e999999 + 9e999999",
        "9e999999 - -9e999999",
    ],
)
def test_el_evaluador_convierte_el_desbordamiento_en_expresion_invalida(expresion):
    """`decimal.Overflow` es un `ArithmeticError` como `DivisionByZero`: los tres operadores
    (Add, Sub, Mult) deben quedar tan protegidos como Div y Pow, no solo estos dos.
    """
    with pytest.raises(ExpresionInvalida):
        evaluar(expresion, {})


def test_nombres_de_devuelve_los_parametros_de_la_expresion():
    assert nombres_de("longitud * (1 + desperdicio)") == frozenset({"longitud", "desperdicio"})


def test_sustituir_codigos_reemplaza_cada_marcador_por_su_cantidad():
    expandida = sustituir_codigos("{A-1} - {B-2}", {"A-1": Decimal("9.74"), "B-2": Decimal("1.66")})
    assert expandida == "9.74 - 1.66"
    assert evaluar(expandida, {}) == Decimal("8.08")


def test_sustituir_codigos_falla_si_el_codigo_no_esta_en_el_presupuesto():
    with pytest.raises(ParametroFaltante):
        sustituir_codigos("{A-1} - {B-2}", {"A-1": Decimal("1")})


# ---------------------------------------------------------------------------------------------
# Normalización de texto
# ---------------------------------------------------------------------------------------------


def test_normalizar_texto_unifica_las_grafias_de_la_pulgada():
    assert normalizar_texto('Tubería PVC de 4"') == "tuberia pvc de 4 pulg"
    assert normalizar_texto("tuberia pvc de 4 pulgadas") == "tuberia pvc de 4 pulg"


def test_normalizar_texto_pasa_la_coma_decimal_a_punto():
    assert normalizar_texto("Espesor 0,10 m") == "espesor 0.10 m"


@pytest.mark.parametrize("token", ["3/4", "4", "0.10", "2"])
def test_es_numero_acepta_enteros_fracciones_y_decimales(token):
    assert es_numero(token)


@pytest.mark.parametrize("token", ["4ta", "pulg", "1/2/3", "m3", ""])
def test_es_numero_rechaza_lo_que_no_es_una_cantidad(token):
    assert not es_numero(token)


def test_pares_numero_unidad_asocia_cada_cantidad_con_lo_que_la_sigue():
    assert pares_numero_unidad(tokens('Clavos de acero 2 1/2 pulg y tuberia de 4"')) == [
        ("1/2", "pulg"),
        ("4", "pulg"),
    ]


# ---------------------------------------------------------------------------------------------
# Directivas
# ---------------------------------------------------------------------------------------------


def test_es_directiva_distingue_las_claves_del_nucleo():
    assert directivas.es_directiva(directivas.CLAVE_BALANCE)
    assert directivas.es_directiva(directivas.CLAVE_UNIDAD_ORIGINAL)
    assert not directivas.es_directiva("diametro")


def test_etiqueta_con_codigos_y_codigos_en_etiqueta_son_inversas():
    codigos = (
        linea_base.APU_EXCAVACION.codigo_partida,
        linea_base.APU_TUBERIA.codigo_partida,
    )
    etiqueta = directivas.etiqueta_con_codigos("Dia 1", codigos)
    assert etiqueta == "Dia 1 [LB-01-EXC, LB-02-TUB]"
    assert directivas.codigos_en_etiqueta(etiqueta) == codigos


def test_codigos_en_etiqueta_devuelve_vacio_si_no_hay_corchetes():
    assert directivas.codigos_en_etiqueta("Día 1 Excavación") == ()


def test_etiqueta_con_codigos_deja_la_etiqueta_intacta_si_no_hay_codigos():
    assert directivas.etiqueta_con_codigos(" Dia 1 ", ()) == "Dia 1"


def test_las_directivas_del_adaptador_civil_coinciden_con_el_nucleo():
    assert reglas_civil.CLAVE_BALANCE == directivas.CLAVE_BALANCE
    assert reglas_civil.CLAVE_TOLERANCIA == directivas.CLAVE_TOLERANCIA


def test_las_reglas_civiles_son_evaluables_por_el_nucleo():
    expresiones = {
        nombre: valor
        for nombre, valor in vars(reglas_civil).items()
        if nombre.startswith("REGLA_") and isinstance(valor, str)
    }
    assert expresiones, "el adaptador civil debe declarar al menos una regla paramétrica"
    for nombre, expresion in expresiones.items():
        valores = {
            parametro: Decimal(1 + indice) / 10
            for indice, parametro in enumerate(sorted(nombres_de(expresion)))
        }
        assert evaluar(expresion, valores) == evaluar_regla(expresion, valores), nombre


# ---------------------------------------------------------------------------------------------
# Una prueba por regla, sobre el presupuesto auditado
# ---------------------------------------------------------------------------------------------


def test_r1_encofrado_y_concreto_con_impacto(presupuesto):
    hallazgos = _errores(TrazabilidadGeometrica().evaluar(presupuesto))
    por_origen = {hallazgo.origen_ids[0]: hallazgo for hallazgo in hallazgos}
    assert len(hallazgos) == 2, [hallazgo.descripcion for hallazgo in hallazgos]

    encofrado = por_origen["computo:LB-03-ENC"]
    assert encofrado.valor_observado == linea_base.PRESUPUESTO_AUDITADO[2].cantidad
    assert encofrado.valor_esperado == linea_base.COMPUTO_CORREGIDO["LB-03-ENC"]
    assert _redondeado(encofrado.impacto) == Decimal("191.45")

    concreto = por_origen["computo:LB-04-CON"]
    assert concreto.valor_esperado == linea_base.COMPUTO_CORREGIDO["LB-04-CON"]
    assert _redondeado(concreto.impacto) == Decimal("185.38")


def test_r1_advierte_de_las_cantidades_manuales_sin_regla(presupuesto):
    hallazgos = TrazabilidadGeometrica().evaluar(presupuesto)
    advertencias = [h for h in hallazgos if h.severidad is Severidad.ADVERTENCIA]
    assert [h.origen_ids for h in advertencias] == [("computo:LB-05-REL",)]


def test_r2_brecha_11_11(presupuesto):
    hallazgos = CierreCurvaInversion().evaluar(presupuesto)
    criticos = [h for h in hallazgos if h.severidad is Severidad.CRITICO]
    assert len(criticos) == 1
    assert criticos[0].origen_ids == ()
    assert criticos[0].valor_observado == linea_base.TOTAL_CURVA_AUDITADA
    assert _redondeado(criticos[0].valor_esperado) == linea_base.TOTAL_PRESUPUESTO_AUDITADO
    assert _redondeado(criticos[0].impacto) == Decimal("11.11")


def test_r2_no_reporta_acumulados_rotos_en_una_curva_bien_sumada(presupuesto):
    hallazgos = CierreCurvaInversion().evaluar(presupuesto)
    assert [h for h in hallazgos if h.severidad is Severidad.ERROR] == []


def test_r2_informa_cuando_no_hay_curva(presupuesto):
    hallazgos = CierreCurvaInversion().evaluar(replace(presupuesto, curva=()))
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]
    assert NO_APLICABLE in hallazgos[0].descripcion


def test_r3_reporta_unidad_original_mts(presupuesto):
    hallazgos = _errores(CoherenciaDimensional().evaluar(presupuesto))
    origenes = [hallazgo.origen_ids[0] for hallazgo in hallazgos]
    assert origenes == ["computo:LB-02-TUB", "computo:LB-03-ENC"]

    tuberia = hallazgos[0]
    assert "mts" in tuberia.descripcion
    assert linea_base.APU_TUBERIA.unidad in tuberia.descripcion


def test_r4_marca_3_4_pulg_y_no_marca_pvc(presupuesto):
    hallazgos = CorrespondenciaEspecificaciones().evaluar(presupuesto)
    errores = _errores(hallazgos)
    assert len(errores) == 1
    assert errores[0].origen_ids == ("computo:LB-02-TUB",)
    assert normalizar_texto(linea_base.DIAMETRO_TUBERIA_MEMORIA) in errores[0].descripcion
    assert normalizar_texto(linea_base.DIAMETRO_TUBERIA_PROYECTO) in errores[0].descripcion
    assert all("pvc" not in hallazgo.descripcion.lower() for hallazgo in hallazgos)


def test_r5_relleno_vs_balance(presupuesto):
    hallazgos = _errores(BalanceVolumetrico().evaluar(presupuesto))
    assert len(hallazgos) == 1
    hallazgo = hallazgos[0]
    assert hallazgo.origen_ids[0] == "computo:LB-05-REL"
    assert set(hallazgo.origen_ids[1:]) == {
        "computo:LB-01-EXC",
        "computo:LB-02-TUB",
        "computo:LB-04-CON",
    }
    assert hallazgo.valor_observado == linea_base.PRESUPUESTO_AUDITADO[4].cantidad
    assert _redondeado(hallazgo.valor_esperado) == Decimal("7.89")
    assert hallazgo.impacto > 0


def test_r5_no_reporta_nada_si_el_balance_se_cumple(presupuesto):
    partidas = tuple(
        replace(partida, item=replace(partida.item, cantidad=Decimal("7.8856")))
        if partida.item.codigo_partida == linea_base.APU_RELLENO.codigo_partida
        else partida
        for partida in presupuesto.partidas
    )
    assert BalanceVolumetrico().evaluar(replace(presupuesto, partidas=partidas)) == []


def test_r6_vehiculo_0_03_vs_1_00(presupuesto):
    hallazgos = _errores(CriterioDepreciacion().evaluar(presupuesto))
    assert len(hallazgos) == 1
    hallazgo = hallazgos[0]
    assert hallazgo.origen_ids[0] == linea_base.APU_TUBERIA.codigo_partida
    assert set(hallazgo.origen_ids) == {apu.codigo_partida for apu in linea_base.APUS_LINEA_BASE}
    assert "0.03" in hallazgo.descripcion
    assert "1.00" in hallazgo.descripcion


def test_r7_dia_a_dia(presupuesto):
    hallazgos = _errores(ConciliacionPresupuestoPlan().evaluar(presupuesto))
    # Cinco componentes conexas: cuatro partidas con un período y el encofrado con dos (días 3 y 4).
    assert len(hallazgos) == 5
    por_partida = {hallazgo.origen_ids[0]: hallazgo for hallazgo in hallazgos}
    excavacion = por_partida["computo:LB-01-EXC"]
    assert excavacion.valor_observado == linea_base.CURVA_AUDITADA[0].monto
    assert _redondeado(excavacion.valor_esperado) == linea_base.PRESUPUESTO_AUDITADO[0].total

    encofrado = por_partida["computo:LB-03-ENC"]
    assert encofrado.valor_observado == (
        linea_base.CURVA_AUDITADA[2].monto + linea_base.CURVA_AUDITADA[3].monto
    )


def test_r7_concilia_una_curva_con_corchetes(presupuesto):
    puntos: list[PuntoCurva] = []
    acumulado = Decimal(0)
    for indice, partida in enumerate(presupuesto.partidas, start=1):
        acumulado += partida.total
        puntos.append(
            PuntoCurva(
                directivas.etiqueta_con_codigos(
                    f"Periodo {indice}", (partida.item.codigo_partida,)
                ),
                partida.total,
                acumulado,
            )
        )
    conciliado = replace(presupuesto, curva=tuple(puntos))
    assert ConciliacionPresupuestoPlan().evaluar(conciliado) == []


def test_r7_advierte_de_un_periodo_que_no_enlaza_con_ninguna_partida(presupuesto):
    curva = (*presupuesto.curva, PuntoCurva("Dia 7 [XX-99]", Decimal("0"), Decimal("1575.50")))
    hallazgos = ConciliacionPresupuestoPlan().evaluar(replace(presupuesto, curva=curva))
    advertencias = [h for h in hallazgos if h.severidad is Severidad.ADVERTENCIA]
    assert len(advertencias) == 1
    assert "XX-99" in advertencias[0].descripcion


def test_r7_advierte_de_una_partida_que_no_esta_en_el_plan(presupuesto):
    solo_un_periodo = replace(presupuesto, curva=presupuesto.curva[:1])
    hallazgos = ConciliacionPresupuestoPlan().evaluar(solo_un_periodo)
    advertencias = [h for h in hallazgos if h.severidad is Severidad.ADVERTENCIA]
    assert {h.origen_ids[0] for h in advertencias} == {
        "computo:LB-02-TUB",
        "computo:LB-03-ENC",
        "computo:LB-04-CON",
        "computo:LB-05-REL",
    }


def test_r7_se_declara_no_aplicable_si_el_presupuesto_no_declara_curva(presupuesto):
    """UC‑05, flujo 2a: sin plan de trabajo R7 se declara no aplicable en el informe (INV‑012)."""
    hallazgos = ConciliacionPresupuestoPlan().evaluar(replace(presupuesto, curva=()))
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]
    assert NO_APLICABLE in hallazgos[0].descripcion


# ---------------------------------------------------------------------------------------------
# Datos degradados: ninguna regla lanza excepciones, todas producen hallazgos
# ---------------------------------------------------------------------------------------------


def _con_item(presupuesto, codigo_partida, **cambios):
    """El mismo presupuesto con un solo ítem alterado."""
    partidas = tuple(
        replace(partida, item=replace(partida.item, **cambios))
        if partida.item.codigo_partida == codigo_partida
        else partida
        for partida in presupuesto.partidas
    )
    return replace(presupuesto, partidas=partidas)


def test_r1_reporta_la_regla_que_no_puede_evaluar(presupuesto):
    roto = _con_item(
        presupuesto,
        linea_base.APU_EXCAVACION.codigo_partida,
        regla="longitud * inexistente",
    )
    origen = origen_de(linea_base.APU_EXCAVACION.codigo_partida)
    hallazgos = [
        h for h in TrazabilidadGeometrica().evaluar(roto) if h.origen_ids == (origen,)
    ]
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]  # RF‑23, UC‑05 3a
    assert REGLA_NO_EVALUABLE in hallazgos[0].descripcion
    assert "no se puede evaluar" in hallazgos[0].descripcion


def test_r1_exige_igualdad_exacta_cuando_la_regla_da_cero(presupuesto):
    cero = _con_item(
        presupuesto,
        linea_base.APU_EXCAVACION.codigo_partida,
        regla="a - a",
        parametros={"a": Decimal("1")},
    )
    hallazgos = _errores(TrazabilidadGeometrica().evaluar(cero))
    assert [h.valor_esperado for h in hallazgos if h.origen_ids == ("computo:LB-01-EXC",)] == [
        Decimal("0")
    ]


def test_r2_detecta_un_acumulado_que_no_es_la_suma_corrida(presupuesto):
    curva = (PuntoCurva("Dia 1", Decimal("100"), Decimal("120")),)
    hallazgos = CierreCurvaInversion().evaluar(replace(presupuesto, curva=curva))
    errores = [h for h in hallazgos if h.severidad is Severidad.ERROR]
    assert len(errores) == 1
    assert errores[0].valor_observado == Decimal("120")
    assert errores[0].valor_esperado == Decimal("100")


def test_r4_informa_de_una_especificacion_que_no_puede_contrastar(presupuesto):
    con_extra = _con_item(
        presupuesto,
        linea_base.APU_RELLENO.codigo_partida,
        especificaciones={"acabado": "liso"},
    )
    hallazgos = CorrespondenciaEspecificaciones().evaluar(con_extra)
    informativos = [h for h in hallazgos if h.severidad is Severidad.INFO]
    assert len(informativos) == 1
    assert "no es contrastable" in informativos[0].descripcion


def test_r5_reporta_una_referencia_de_balance_no_resuelta(presupuesto):
    roto = _con_item(
        presupuesto,
        linea_base.APU_RELLENO.codigo_partida,
        especificaciones={directivas.CLAVE_BALANCE: "{XX-99} - 1"},
    )
    hallazgos = BalanceVolumetrico().evaluar(roto)
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]
    assert REGLA_NO_EVALUABLE in hallazgos[0].descripcion
    assert "referencia no resuelta" in hallazgos[0].descripcion


def test_r5_reporta_un_balance_que_no_puede_evaluar(presupuesto):
    roto = _con_item(
        presupuesto,
        linea_base.APU_RELLENO.codigo_partida,
        especificaciones={
            directivas.CLAVE_BALANCE: f"{{{linea_base.APU_EXCAVACION.codigo_partida}}} - falta"
        },
    )
    hallazgos = BalanceVolumetrico().evaluar(roto)
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]
    assert REGLA_NO_EVALUABLE in hallazgos[0].descripcion
    assert "no se puede evaluar" in hallazgos[0].descripcion


def test_r5_reporta_un_balance_sin_llaves_en_vez_de_lanzar(presupuesto):
    """Un balance como el que hoy escribe `adapters/civil/tabular.py` (códigos sin llaves) no es
    analizable: `LB-01-EXC` se leería como una resta. La regla lo reporta, no revienta.
    """
    sin_llaves = BALANCE_RELLENO.replace("{", "").replace("}", "")
    roto = _con_item(
        presupuesto,
        linea_base.APU_RELLENO.codigo_partida,
        especificaciones={directivas.CLAVE_BALANCE: sin_llaves},
    )
    hallazgos = _errores(BalanceVolumetrico().evaluar(roto))
    assert len(hallazgos) == 1
    assert "no se puede evaluar" in hallazgos[0].descripcion


def test_r5_cae_a_la_tolerancia_del_sistema_si_la_declarada_no_es_numerica(presupuesto):
    con_tolerancia_rota = _con_item(
        presupuesto,
        linea_base.APU_RELLENO.codigo_partida,
        especificaciones={
            directivas.CLAVE_BALANCE: BALANCE_RELLENO,
            directivas.CLAVE_TOLERANCIA: "cinco por ciento",
        },
    )
    hallazgos = BalanceVolumetrico().evaluar(con_tolerancia_rota)
    severidades = [h.severidad for h in hallazgos]
    assert Severidad.ADVERTENCIA in severidades
    assert Severidad.ERROR in severidades


@pytest.mark.parametrize("tolerancia_invalida", ["nan", "Infinity", "-0.05"])
def test_r5_cae_a_la_tolerancia_del_sistema_si_la_declarada_es_nan_infinita_o_negativa(
    presupuesto, tolerancia_invalida
):
    """`Decimal("nan")`, `Decimal("Infinity")` y `Decimal("-0.05")` construyen sin lanzar
    `InvalidOperation`: fallan (o mienten) recien al comparar en `_dentro_de_tolerancia`. La
    regla debe tratarlas igual que una tolerancia no numerica: advertir y usar la del sistema,
    sin lanzar y sin ocultar el error de balance detras de una tolerancia negativa siempre
    incumplida.
    """
    con_tolerancia_rota = _con_item(
        presupuesto,
        linea_base.APU_RELLENO.codigo_partida,
        especificaciones={
            directivas.CLAVE_BALANCE: BALANCE_RELLENO,
            directivas.CLAVE_TOLERANCIA: tolerancia_invalida,
        },
    )
    hallazgos = BalanceVolumetrico().evaluar(con_tolerancia_rota)
    severidades = [h.severidad for h in hallazgos]
    assert Severidad.ADVERTENCIA in severidades
    assert Severidad.ERROR in severidades
    advertencia = next(h for h in hallazgos if h.severidad is Severidad.ADVERTENCIA)
    assert "tolerancia de balance no numerica" in advertencia.descripcion


def test_r1_reporta_una_regla_que_desborda_en_vez_de_reventar_auditar(presupuesto):
    roto = _con_item(
        presupuesto,
        linea_base.APU_EXCAVACION.codigo_partida,
        regla="1e999999 * 1e999999",
    )
    informe = auditar(roto)
    hallazgos = [
        h for h in informe.hallazgos if h.regla == "R1" and h.origen_ids == ("computo:LB-01-EXC",)
    ]
    assert len(hallazgos) == 1
    assert hallazgos[0].severidad is Severidad.ERROR
    assert "no se puede evaluar" in hallazgos[0].descripcion


def test_r5_reporta_un_balance_que_desborda_en_vez_de_reventar_auditar(presupuesto):
    roto = _con_item(
        presupuesto,
        linea_base.APU_RELLENO.codigo_partida,
        especificaciones={directivas.CLAVE_BALANCE: "1e999999 * 1e999999"},
    )
    informe = auditar(roto)
    hallazgos = [h for h in informe.hallazgos if h.regla == "R5"]
    assert len(hallazgos) == 1
    assert hallazgos[0].severidad is Severidad.ERROR
    assert "no se puede evaluar" in hallazgos[0].descripcion


@pytest.mark.parametrize("regla", ["longitud * 2", "longitud"])
def test_r1_reporta_un_parametro_que_no_es_decimal_en_vez_de_reventar_auditar(presupuesto, regla):
    """Principio 7 (INV‑003): un `float` en `ItemComputo.parametros` no saca a `auditar` con
    `TypeError`. Con la expresión compuesta fallaba la aritmética; con el nombre solo, la
    comparación posterior contra la cantidad `Decimal`. En ambos casos R1 lo informa y sigue.
    """
    roto = _con_item(
        presupuesto,
        linea_base.APU_EXCAVACION.codigo_partida,
        regla=regla,
        parametros={"longitud": 1.5},
    )
    informe = auditar(roto)
    origen = origen_de(linea_base.APU_EXCAVACION.codigo_partida)
    hallazgos = [h for h in informe.hallazgos if h.regla == "R1" and h.origen_ids == (origen,)]
    assert len(hallazgos) == 1
    # Un dato erróneo, no ausente: sigue siendo ERROR también después de INV‑012 (Tarea 8).
    assert hallazgos[0].severidad >= Severidad.ERROR
    assert "'longitud'" in hallazgos[0].descripcion
    assert "float" in hallazgos[0].descripcion


def test_r5_reporta_un_parametro_que_no_es_decimal_en_vez_de_reventar_auditar(presupuesto):
    roto = _con_item(
        presupuesto,
        linea_base.APU_RELLENO.codigo_partida,
        especificaciones={
            directivas.CLAVE_BALANCE: f"{{{linea_base.APU_EXCAVACION.codigo_partida}}} - holgura"
        },
        parametros={"holgura": 0.5},
    )
    informe = auditar(roto)
    hallazgos = [h for h in informe.hallazgos if h.regla == "R5"]
    assert len(hallazgos) == 1
    assert hallazgos[0].severidad >= Severidad.ERROR
    assert "'holgura'" in hallazgos[0].descripcion


# ---------------------------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------------------------


def test_informe_markdown_contiene_resumen_y_partidas(presupuesto):
    informe = auditar(presupuesto)
    markdown = informe.a_markdown()

    assert linea_base.CODIGO_PRESUPUESTO in markdown
    assert "Resumen por severidad" in markdown
    assert not informe.cumple
    for regla in REGLAS:
        assert regla.codigo in markdown
    for apu in linea_base.APUS_LINEA_BASE:
        assert apu.codigo_partida in markdown
    assert sum(informe.por_severidad().values()) == len(informe.hallazgos)
    assert informe.por_regla()["R1"]


def test_el_informe_ordena_los_hallazgos_por_severidad_descendente(presupuesto):
    severidades = [hallazgo.severidad for hallazgo in auditar(presupuesto).hallazgos]
    assert severidades == sorted(severidades, reverse=True)


def test_partida_de_resuelve_el_origen_y_el_codigo_de_partida(presupuesto):
    informe = auditar(presupuesto)
    r6 = informe.por_regla()["R6"][0]
    assert informe.partida_de(r6) == linea_base.APU_TUBERIA.codigo_partida
    r2 = informe.por_regla()["R2"][0]
    assert informe.partida_de(r2) is None


def test_auditar_con_subconjunto_de_reglas(presupuesto):
    informe = auditar(presupuesto, reglas=(CoherenciaDimensional(),))
    assert {hallazgo.regla for hallazgo in informe.hallazgos} == {"R3"}
    assert len(informe.hallazgos) == 2
