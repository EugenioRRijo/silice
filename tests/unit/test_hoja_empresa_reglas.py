"""Reglas del libro L1-L9 (Silice 1.5, RF-104; spec §3, causas raíz H1-H18, rulings RL-7 y RL-8).

Cada regla tiene su error SEMBRADO en un libro sintético (`tests/fixtures/libros_empresa.py`)
y, donde la regla tiene umbral, su frontera (el valor límite no es hallazgo y el siguiente sí).
Se compara siempre el CONJUNTO EXACTO de hallazgos (regla, severidad, celdas de origen,
impacto): un hallazgo de más es un falso positivo y uno de menos un error que se escapa.

Oráculo: la memoria de cálculo a mano del fixture. Las celdas de los APU generados (formas
distintas): APU-01 rinde en F19, su resumen va de G37 (MAT) a G45 (P.U.), escombro G31, flete G32,
subtotal de equipos G28; APU-02 rinde en F20, resumen G32 (MAT) … G36 (CD) … G40 (P.U.);
APU-03 rinde en F16, P.U. en G41. PRESUPUESTO: partidas en las filas 5, 6 y 7.

Cada impacto esperado se calcula aquí a mano con la cifra de la memoria (por ejemplo, el equipo
omitido del CD de APU-02: 1,59375 × 1,1 × 1,1 × 80 = 154,275 -> 154,28 ROUND_HALF_UP).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pytest

from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.reglas import REGLAS_LIBRO, reglas_del_libro
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    D,
    PartidaSinApu,
    Siembra,
    con,
    construir_libro,
    libro_limpio,
)

A1, A2, A3 = APUS_LIMPIOS
VINCULO = "file:///\\\\servidor-ficticio\\obras\\mediciones.xlsx"


def _c(x: Decimal) -> Decimal:
    """Céntimos ROUND_HALF_UP (la convención del impacto, oráculo aparte del código)."""
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _hallazgos(apus=APUS_LIMPIOS, **siembra):
    c = construir_libro(apus, Siembra(**siembra))
    return reglas_del_libro(leer_libro(c.datos, "sintetico.xlsx"))


def _firmas(hallazgos):
    return [(h.regla, h.severidad.name, h.origen_ids, h.impacto) for h in hallazgos]


def test_catalogo_de_reglas_del_libro():
    assert [codigo for codigo, _ in REGLAS_LIBRO] == [f"L{i}" for i in range(1, 10)]


def test_libro_limpio_no_da_ningun_hallazgo():
    c = libro_limpio()
    assert reglas_del_libro(leer_libro(c.datos, "limpio.xlsx")) == []


# --- L1 Referencia desalineada ------------------------------------------------------------------


def test_l1_columna_rend_lee_una_fila_fija():
    """H9: la columna REND. lee F19 en todos los APU; solo APU-01 rinde en F19."""
    hs = _hallazgos(rend_fila_fija=19)
    assert _firmas(hs) == [
        ("L1", "ERROR", ("PRESUPUESTO!F6", "APU-02!F19", "APU-02!F20"), None),
        ("L1", "ERROR", ("PRESUPUESTO!F7", "APU-03!F19", "APU-03!F16"), None),
    ]
    assert (hs[0].valor_observado, hs[0].valor_esperado) == (None, D("8"))
    assert "rendimiento" in hs[0].descripcion


def test_l1_acepta_la_celda_equivalente_del_rotulo():
    """Leer el subtotal de materiales (G12) en lugar de la línea del resumen (G37 = G12) es leer
    bien: sin falso positivo por forma."""
    hs = _hallazgos(parches={"PRESUPUESTO!H5": (D("3.25"), "='APU-01'!G12")})
    assert hs == []


def test_l1_cronograma_con_rendimiento_en_fila_fija_da_duracion_cero():
    """H6: CRONOGRAMA lee F19 por INDIRECT; en APU-02 y APU-03 esa celda está vacía."""
    hs = _hallazgos(cronograma_fila_rend=19)
    assert _firmas(hs) == [
        ("L1", "ERROR", ("CRONOGRAMA!D5", "APU-02!F19", "APU-02!F20"), None),
        ("L1", "ERROR", ("CRONOGRAMA!D6", "APU-03!F19", "APU-03!F16"), None),
    ]
    assert all("da 0 días" in h.descripcion for h in hs)


def test_l1_cronograma_con_otro_rendimiento_no_nulo():
    """F27 de APU-01 es el % de herramientas (0,05), no el rendimiento: la duración sale de otro
    número (efecto distinto del de la celda vacía de APU-02 y APU-03)."""
    hs = _hallazgos(cronograma_fila_rend=27)
    assert _firmas(hs) == [
        ("L1", "ERROR", ("CRONOGRAMA!D4", "APU-01!F27", "APU-01!F19"), None),
        ("L1", "ERROR", ("CRONOGRAMA!D5", "APU-02!F27", "APU-02!F20"), None),
        ("L1", "ERROR", ("CRONOGRAMA!D6", "APU-03!F27", "APU-03!F16"), None),
    ]
    assert (hs[0].valor_observado, hs[0].valor_esperado) == (D("0.05"), D("10"))
    assert "se calcula con otro rendimiento" in hs[0].descripcion
    assert "da 0 días" in hs[1].descripcion


def test_l1_aux_toma_el_flete_como_escombro():
    """H8: AUX lee el flete (G32 = 0,2) como escombro de APU-01 (G31 = 0,02)."""
    hs = _hallazgos(aux_escombro_celda={1: "G32"})
    assert _firmas(hs) == [("L1", "ERROR", ("AUX!B2", "APU-01!G32", "APU-01!G31"), None)]
    assert (hs[0].valor_observado, hs[0].valor_esperado) == (D("0.2"), D("0.02"))


def test_l1_partida_que_lee_el_pu_de_otra_hoja():
    """La fila de la partida 1 lee el P.U. de APU-02 (parche a la hoja equivocada, C2): L1, el
    riesgo del parche (L2 advertencia) y el desglose que no cuadra (L9)."""
    hs = _hallazgos(parches={"PRESUPUESTO!P5": (D("30.2121875"), "='APU-02'!G40")})
    # L2: la fórmula de la plantilla leería APU-01!G40 (transporte, 0,24) en vez de 30,2121875.
    riesgo = _c(D("120") * (D("0.24") - D("30.2121875")))
    # L9: N + O = 13,16975 + 1,316975 = 14,486725 frente a P = 30,2121875.
    dif = D("14.486725") - D("30.2121875")
    assert _firmas(hs) == [
        ("L1", "ERROR", ("PRESUPUESTO!P5", "APU-02!G40", "APU-01!G45"), None),
        ("L2", "ADVERTENCIA", ("PRESUPUESTO!P5", "APU-02!G40", "APU-01!G40"), None),
        (
            "L9",
            "ERROR",
            ("PRESUPUESTO!N5", "PRESUPUESTO!O5", "PRESUPUESTO!P5"),
            _c(dif * D("120")),
        ),
    ]
    assert "lee la hoja APU-02" in hs[0].descripcion
    assert hs[1].valor_esperado == D("0.24")
    assert f"{abs(riesgo):,.2f}".replace(",", " ").replace(".", ",") in hs[1].descripcion


# --- L2 Enlace partida ↔ APU roto ---------------------------------------------------------------


def test_l2_dos_apu_reclaman_la_misma_partida():
    """Caso C-1: APU-01 y APU-07 dicen ser la partida 1. APU-07 queda unido a la partida 2 por su
    P.U., pero su título apunta a la fila 5."""
    hs = _hallazgos((A1, con(A2, hoja="APU-07", fila_titulo=5)))
    assert _firmas(hs) == [
        ("L2", "ERROR", ("APU-01!A2", "APU-07!A2", "PRESUPUESTO!D5"), None),
        ("L2", "ERROR", ("APU-07!A2", "PRESUPUESTO!D6"), None),
    ]
    assert "Silice la unió a APU-01" in hs[0].descripcion


def test_l2_partida_sin_apu():
    """La partida 9 no tiene APU (L2). La composición de RESUMEN no la incluye (no tiene desglose)
    y el subtotal sí: la hoja no cuadra por su monto, 1 × 50 = 50,00 (L9)."""
    sin = PartidaSinApu(9, "S/C", "Limpieza final (ficticia)", "glb", D("1"), D("50"))
    hs = _hallazgos(partidas_sin_apu=(sin,))
    assert _firmas(hs) == [
        ("L2", "ERROR", ("PRESUPUESTO!B8",), None),
        ("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q11"), D("-50.00")),
    ]


def test_l2_hoja_de_plantilla_sin_partida_es_informativa():
    hs = _hallazgos((*APUS_LIMPIOS, con(A1, numero=9, hoja="APU-x", en_presupuesto=False)))
    assert _firmas(hs) == [("L2", "INFO", ("APU-x!A2",), None)]
    assert "no se copian a la devolución" in hs[0].descripcion


def test_l2_enlace_parcheado_a_mano_es_advertencia_sin_impacto_y_l8():
    """H4 + H5 (RL-7): el número 2 se repite; la fila 7 (cantidad 0) lee APU-07 por referencia
    directa. La fórmula de la plantilla leería APU-02!G40 (P.U. de APU-02 = 30,2121875)."""
    apus = (A1, A2, con(A2, hoja="APU-07", cantidad=D("0"), rendimiento=D("10")))
    hs = _hallazgos(apus)
    assert _firmas(hs) == [
        ("L2", "ADVERTENCIA", ("PRESUPUESTO!P7", "APU-07!G40", "APU-02!G40"), None),
        ("L8", "ADVERTENCIA", ("PRESUPUESTO!B6", "PRESUPUESTO!B7"), None),
    ]
    assert hs[0].valor_esperado == D("30.2121875")
    assert "cantidad 0" in hs[0].descripcion


def test_l2_parche_con_cantidad_cuantifica_el_riesgo_en_la_descripcion():
    """Con cantidad 10, el riesgo es 10 × (30,2121875 − P.U. de APU-07) y no es impacto (RL-7).

    P.U. de APU-07 (rendimiento 10): MO = 50 × 1,9 ÷ 10 = 9,5; EQ = 8 ÷ 10 + 0,05 × 9,5 = 1,275;
    CD = 11,5 + 9,5 + 1,275 = 22,275; P.U. = 22,275 × 1,21 = 26,95275.
    Riesgo = 10 × (30,2121875 − 26,95275) = 32,594375 -> 32,59.
    """
    apus = (A1, A2, con(A2, hoja="APU-07", cantidad=D("10"), rendimiento=D("10")))
    hs = [h for h in _hallazgos(apus) if h.regla == "L2"]
    assert len(hs) == 1 and hs[0].impacto is None
    assert hs[0].valor_observado == D("26.95275")
    assert "cambiaría en 32,59 USD" in hs[0].descripcion


# --- L3 Valor guardado ≠ fórmula ----------------------------------------------------------------


def test_l3_columna_que_no_mueve_monto_es_advertencia():
    hs = _hallazgos(rend_guardado={2: D("7.5")})
    assert _firmas(hs) == [("L3", "ADVERTENCIA", ("PRESUPUESTO!F6", "APU-02!F20"), None)]
    assert (hs[0].valor_observado, hs[0].valor_esperado) == (D("7.5"), D("8"))


def test_l3_pu_viejo_mueve_el_monto_y_descuadra_el_desglose():
    """P5 guarda 14,00 y su fórmula lee 14,486725: 120 × 0,486725 = 58,407 -> 58,41."""
    hs = _hallazgos(p_guardado={1: D("14")})
    assert _firmas(hs) == [
        ("L3", "ERROR", ("PRESUPUESTO!P5", "APU-01!G45"), D("58.41")),
        ("L9", "ERROR", ("PRESUPUESTO!N5", "PRESUPUESTO!O5", "PRESUPUESTO!P5"), D("58.41")),
        ("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q10"), D("58.41")),
    ]


@pytest.mark.parametrize(
    ("guardado", "hay_l3"),
    [
        # tolerancia relativa 1e-6: |Δ| ≤ máx(|a|, |b|) × 1e-6
        (D("14.4867394"), False),  # Δ = 0,0000144 ≤ 0,0000144867…
        (D("14.4867395"), True),  # Δ = 0,0000145 > 0,0000144867…
    ],
)
def test_l3_frontera_de_la_tolerancia_relativa(guardado, hay_l3):
    hs = _hallazgos(p_guardado={1: guardado})
    if hay_l3:
        # 120 × (14,486725 − 14,4867395) = −0,00174 -> −0,00 (céntimos)
        assert _firmas(hs) == [("L3", "ERROR", ("PRESUPUESTO!P5", "APU-01!G45"), D("0.00"))]
    else:
        assert hs == []


# --- L4 Componente fuera del total --------------------------------------------------------------


def test_l4_costo_directo_que_omite_los_equipos():
    """H1: CD = MAT + MO + TR deja fuera 1,59375 USD/u de equipos en APU-02 (cantidad 80)."""
    hs = _hallazgos((A1, con(A2, cd_sin_equipos=True), A3))
    assert _firmas(hs) == [
        ("L4", "ERROR", ("APU-02!G36", "APU-02!G34"), _c(D("1.59375") * D("1.21") * 80)),
        (
            "L9",
            "ERROR",
            tuple(f"PRESUPUESTO!{c}6" for c in "HIJKL"),
            _c(D("1.59375") * 80),
        ),
        ("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q10"), _c(D("1.59375") * 80)),
    ]
    assert _firmas(hs)[0][3] == D("154.28")
    assert (hs[0].valor_observado, hs[0].valor_esperado) == (D("23.375"), D("24.96875"))


@pytest.mark.parametrize(
    ("delta", "esperado"),
    [
        # CD guardado = suma + 0,005: dentro de medio céntimo. Solo RESUMEN, que multiplica por
        # la cantidad (120 × 0,005 = 0,60), ve la diferencia.
        (D("0.005"), [("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q10"), D("-0.60"))]),
        (
            D("0.0051"),
            [
                # L4: −0,0051 × 1,21 × 120 = −0,74052 -> −0,74
                ("L4", "ERROR", ("APU-01!G41",), D("-0.74")),
                # L9 desglose y RESUMEN: −0,0051 × 120 = −0,612 -> −0,61
                ("L9", "ERROR", tuple(f"PRESUPUESTO!{c}5" for c in "HIJKL"), D("-0.61")),
                ("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q10"), D("-0.61")),
            ],
        ),
    ],
)
def test_l4_frontera_del_medio_centimo(delta, esperado):
    hs = _hallazgos((con(A1, delta_cd_guardado=delta), A2, A3))
    assert _firmas(hs) == esperado


# --- L5 Referencia rota o externa ---------------------------------------------------------------


def test_l5_ref_en_resumen():
    hs = _hallazgos(resumen_ref_rota=True)
    assert _firmas(hs) == [("L5", "ERROR", ("RESUMEN!B13",), None)]


def test_l5_nombres_externos_y_rotos():
    hs = _hallazgos(nombres_externos=("MEDP2", "MEDP10", "MEDP1"), nombres_rotos=("VIEJO",))
    assert _firmas(hs) == [
        ("L5", "ERROR", ("nombre:VIEJO",), None),
        ("L5", "ADVERTENCIA", ("nombre:MEDP1", "nombre:MEDP2", "nombre:MEDP10"), None),
    ]


def test_l5_vinculo_a_otro_libro_sin_ruta_de_red_en_el_informe():
    hs = _hallazgos(vinculo_externo=VINCULO)
    assert _firmas(hs) == [("L5", "ADVERTENCIA", ("vinculo:mediciones.xlsx",), None)]
    assert "servidor-ficticio" not in hs[0].descripcion


def test_l5_formula_que_lee_otro_libro():
    hs = _hallazgos(formula_externa=True)
    assert _firmas(hs) == [("L5", "ADVERTENCIA", ("MEDICIONES!D5",), None)]


# --- L6 Parámetro global sobrescrito ------------------------------------------------------------


@pytest.mark.parametrize(
    ("literal", "esperado"),
    [
        (D("0.10"), []),  # escrita a mano pero igual a UTIL: no es hallazgo
        # (0,10 − 0,11) × SUB (13,16975) × 120 = −15,8037 -> −15,80
        (D("0.11"), [("L6", "ADVERTENCIA", ("APU-01!F44", "APU-01!G44"), D("-15.80"))]),
    ],
)
def test_l6_utilidad_escrita_a_mano(literal, esperado):
    hs = _hallazgos((con(A1, utilidad_literal=literal), A2, A3))
    assert _firmas(hs) == esperado
    if esperado:
        assert hs[0].descripcion.startswith("A confirmar")
        assert (hs[0].valor_observado, hs[0].valor_esperado) == (D("0.11"), D("0.10"))


@pytest.mark.parametrize(
    ("divisor", "severidad"),
    [(D("10"), "INFO"), (D("12"), "ADVERTENCIA")],
)
def test_l6_rendimiento_literal_en_la_formula_de_equipos(divisor, severidad):
    """H12 (`=G27/12`): igual al rendimiento del APU (10) es INFO; distinto, a confirmar."""
    hs = _hallazgos((con(A1, divisor_equipos=divisor), A2, A3))
    assert _firmas(hs) == [("L6", severidad, ("APU-01!G28", "APU-01!F19"), None)]
    assert (hs[0].valor_observado, hs[0].valor_esperado) == (divisor, D("10"))


# --- L7 Dato dentro de fórmula ------------------------------------------------------------------


def test_l7_medidas_y_factores_literales_en_mediciones():
    """`=9.73*2.75` y `=B4*0.28` son datos dentro de fórmulas; `=B4*2` y `=B4*C4` no."""
    hs = _hallazgos(mediciones_literales=("=9.73*2.75", "=B4*0.28", "=B4*2", "=B4*C4"))
    assert _firmas(hs) == [("L7", "INFO", ("MEDICIONES!D5", "MEDICIONES!D6"), None)]
    assert "«A · Frisos»" in hs[0].descripcion


# --- L8 Número de partida duplicado -------------------------------------------------------------


def test_l8_numero_repetido_con_cantidad_cero():
    hs = _hallazgos((A1, A2, con(A2, hoja="APU-07", cantidad=D("0"))))
    assert _firmas(hs) == [("L8", "ADVERTENCIA", ("PRESUPUESTO!B6", "PRESUPUESTO!B7"), None)]


# --- L9 Cuadre interno --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (D("0.0099"), []),
        (D("0.01"), [("L9", "ERROR", ("PRESUPUESTO!R5",), D("1.20"))]),  # 0,01 × 120
    ],
)
def test_l9_columna_de_verificacion(valor, esperado):
    assert _firmas(_hallazgos(verificacion={1: valor})) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (D("0.0099"), []),
        (D("0.01"), [("L9", "ERROR", ("PROCURA!B5",), D("0.01"))]),
    ],
)
def test_l9_procura_sin_doble_conteo(valor, esperado):
    """La fila «Dif. vs Costo Directo» repite la de materiales: no se cuenta dos veces."""
    assert _firmas(_hallazgos(procura_dif=valor)) == esperado


def test_l9_procura_solo_el_total_difiere():
    hs = _hallazgos(procura_dif_solo_total=D("0.01"))
    assert _firmas(hs) == [("L9", "ERROR", ("PROCURA!B6",), D("0.01"))]


def test_l9_plan_de_pagos():
    hs = _hallazgos(plan_dif=D("0.01"))
    assert _firmas(hs) == [("L9", "ERROR", ("PLAN DE PAGOS!B6",), D("0.01"))]


@pytest.mark.parametrize(
    ("delta", "esperado"),
    [
        # L guardado = CD + 0,005: L3 (lee el CD del APU) y nada más (medio céntimo).
        (D("0.005"), [("L3", "ADVERTENCIA", ("PRESUPUESTO!L5", "APU-01!G41"), None)]),
        (
            D("0.006"),
            [
                ("L3", "ADVERTENCIA", ("PRESUPUESTO!L5", "APU-01!G41"), None),
                # H+I+J+K − L = −0,006 × 120 = −0,72; L + M − N = +0,006 × 120 = 0,72
                ("L9", "ERROR", tuple(f"PRESUPUESTO!{c}5" for c in "HIJKL"), D("-0.72")),
                ("L9", "ERROR", ("PRESUPUESTO!L5", "PRESUPUESTO!M5", "PRESUPUESTO!N5"), D("0.72")),
            ],
        ),
    ],
)
def test_l9_desglose_frontera_del_medio_centimo(delta, esperado):
    assert _firmas(_hallazgos(desglose_delta={1: delta})) == esperado


# --- Conjunto exacto de un libro con varios errores ---------------------------------------------


def test_conjunto_exacto_con_varios_errores():
    """H1 + H2 en APU-02, `/12` en APU-03, H12 en MEDICIONES, H10 en RESUMEN, H11, H7, H6.

    Cifras a mano (APU-02 con CD sin equipos y utilidad 2 %): CD guardado 23,375; SUB = 25,7125.
    L4: 1,59375 × 1,1 × 1,02 × 80 = 143,055 -> 143,06. L6: (0,10 − 0,02) × 25,7125 × 80 = 164,56.
    L9: 1,59375 × 80 = 127,50 (desglose y RESUMEN); PROCURA 5,00.
    """
    apus = (
        A1,
        con(A2, cd_sin_equipos=True, utilidad_literal=D("0.02")),
        con(A3, divisor_equipos=D("12")),
    )
    hs = _hallazgos(
        apus,
        mediciones_literales=("=9.73*2.75",),
        resumen_ref_rota=True,
        nombres_externos=("MEDP1", "MEDP2"),
        procura_dif=D("5"),
        cronograma_fila_rend=23,
        vinculo_externo=VINCULO,
    )
    assert _firmas(hs) == [
        ("L1", "ERROR", ("CRONOGRAMA!D4", "APU-01!F23", "APU-01!F19"), None),
        ("L1", "ERROR", ("CRONOGRAMA!D5", "APU-02!F23", "APU-02!F20"), None),
        ("L1", "ERROR", ("CRONOGRAMA!D6", "APU-03!F23", "APU-03!F16"), None),
        ("L4", "ERROR", ("APU-02!G36", "APU-02!G34"), D("143.06")),
        ("L5", "ERROR", ("RESUMEN!B13",), None),
        ("L5", "ADVERTENCIA", ("nombre:MEDP1", "nombre:MEDP2"), None),
        ("L5", "ADVERTENCIA", ("vinculo:mediciones.xlsx",), None),
        ("L6", "ADVERTENCIA", ("APU-02!F39", "APU-02!G39"), D("164.56")),
        ("L6", "ADVERTENCIA", ("APU-03!G24", "APU-03!F16"), None),
        ("L7", "INFO", ("MEDICIONES!D5",), None),
        ("L9", "ERROR", tuple(f"PRESUPUESTO!{c}6" for c in "HIJKL"), D("127.50")),
        ("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q10"), D("127.50")),
        ("L9", "ERROR", ("PROCURA!B5",), D("5.00")),
    ]
    assert _c(D("1.59375") * D("1.1") * D("1.02") * 80) == D("143.06")
    assert _c((D("0.10") - D("0.02")) * D("25.7125") * 80) == D("164.56")


def test_reglas_deterministas():
    c = construir_libro((A1, con(A2, cd_sin_equipos=True), A3), Siembra(procura_dif=D("1")))
    primero = reglas_del_libro(leer_libro(c.datos, "a.xlsx"))
    segundo = reglas_del_libro(leer_libro(c.datos, "a.xlsx"))
    assert primero == segundo and primero
