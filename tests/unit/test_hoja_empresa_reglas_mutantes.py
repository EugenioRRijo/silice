"""Pruebas para matar mutantes sobrevivientes en `adapters/hoja_empresa/reglas.py`.

Cada prueba llama a `reglas_del_libro(leer_libro(...))` sobre libros sintéticos construidos con
`tests/fixtures/libros_empresa.py` y compara el conjunto exacto de hallazgos o una cifra/celda
exacta de la descripción. Cada docstring indica las líneas y operadores de mutator que mata.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pytest

from adapters.hoja_empresa.lector import leer_libro
from adapters.hoja_empresa.reglas import reglas_del_libro
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    ApuSint,
    D,
    Siembra,
    con,
    construir_libro,
)

A1, A2, A3 = APUS_LIMPIOS


def _c(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _hallazgos(apus=APUS_LIMPIOS, **siembra):
    c = construir_libro(apus, Siembra(**siembra))
    return reglas_del_libro(leer_libro(c.datos, "sintetico.xlsx"))


def _firmas(hallazgos):
    return [(h.regla, h.severidad.name, h.origen_ids, h.impacto) for h in hallazgos]


# --- L1 -----------------------------------------------------------------------------------------


def test_l1_aux_filas_variables_de_insumos_faltan_y_sobran():
    """Mata en `_l1_aux`: 226 (1 -> 0), 234 (1 -> 0), 240 (- -> +) y 243 (- -> +)."""
    hs = _hallazgos(
        parches={
            "AUX!A5": ("INSUMOS POR PARTIDA", None),
            "AUX!A6": (D("9"), None),
            "AUX!B6": ("Código", "=INDIRECT(\"'APU-01'!B\"&A6)"),
            "AUX!A7": (D("10"), None),
            "AUX!B7": ("MT-01", "=INDIRECT(\"'APU-01'!B\"&A7)"),
            "AUX!A8": (D("11"), None),
            "AUX!B8": ("MT-02", "=INDIRECT(\"'APU-01'!B\"&A8)"),
            "AUX!A9": (D("16"), None),
            "AUX!B9": ("MO-01", "=INDIRECT(\"'APU-01'!B\"&A9)"),
            "AUX!A10": (D("17"), None),
            "AUX!B10": ("MO-02", "=INDIRECT(\"'APU-01'!B\"&A10)"),
        }
    )
    assert _firmas(hs) == [("L1", "ERROR", ("AUX!B6", "APU-01!B25"), None)]
    assert "filas fijas 9-11, 16-17" in hs[0].descripcion
    assert "EQ-01 (fila 25)" in hs[0].descripcion
    assert "9 («Código»)" in hs[0].descripcion


def test_l1_aux_filas_variables_completas_no_dan_hallazgo():
    """Mata en `_l1_aux`: 226 (1 -> 0), 234 (1 -> 0), 240 (- -> +) y 243 (- -> +)."""
    hs = _hallazgos(
        parches={
            "AUX!A5": ("INSUMOS POR PARTIDA", None),
            "AUX!A6": (D("10"), None),
            "AUX!B6": ("MT-01", "=INDIRECT(\"'APU-01'!B\"&A6)"),
            "AUX!A7": (D("11"), None),
            "AUX!B7": ("MT-02", "=INDIRECT(\"'APU-01'!B\"&A7)"),
            "AUX!A8": (D("16"), None),
            "AUX!B8": ("MO-01", "=INDIRECT(\"'APU-01'!B\"&A8)"),
            "AUX!A9": (D("17"), None),
            "AUX!B9": ("MO-02", "=INDIRECT(\"'APU-01'!B\"&A9)"),
            "AUX!A10": (D("25"), None),
            "AUX!B10": ("EQ-01", "=INDIRECT(\"'APU-01'!B\"&A10)"),
        }
    )
    assert hs == []


def test_l1_aux_escombro_en_cero_en_apu_sin_transporte_no_avisa():
    """Mata en `_l1_aux`: 266 (and -> or)."""
    assert _hallazgos(aux_escombro_celda={2: "G35"}) == []


def test_l1_otra_hoja_juzga_escombro_y_rendimiento_por_rotulo():
    """Mata en `_l1_otras`: 317 (delete not)."""
    hs = _hallazgos(
        parches={
            "MEDICIONES!A5": ("Rendimiento de prueba", None),
            "MEDICIONES!D5": (D("0.05"), "='APU-01'!F27"),
            "MEDICIONES!A6": ("Referencia sin rótulo esperado", None),
            "MEDICIONES!D6": (D("0.05"), "='APU-01'!F27"),
        }
    )
    assert _firmas(hs) == [("L1", "ERROR", ("MEDICIONES!D5", "APU-01!F27", "APU-01!F19"), None)]


# --- L2 -----------------------------------------------------------------------------------------


def test_l2_plantilla_sin_partida_que_nombra_fila_del_presupuesto():
    """Mata en `_l2`: 397 (primer or -> and)."""
    apus = (*APUS_LIMPIOS, con(A1, numero=9, hoja="APU-x", en_presupuesto=False, fila_titulo=5))
    hs = _hallazgos(apus)
    assert _firmas(hs) == [
        ("L2", "ERROR", ("APU-01!A2", "APU-x!A2", "PRESUPUESTO!D5"), None),
        ("L2", "INFO", ("APU-x!A2",), None),
    ]


def test_l2_apu_unido_por_nombre_con_titulo_de_texto():
    """Mata en `_l2`: 397 (segundo or -> and)."""
    assert _hallazgos(parches={"APU-01!A2": ("Título manual", None)}) == []


def test_l2_titulo_ref_en_apu_usado():
    """Mata en `_l2`: 432 (or -> and)."""
    hs = _hallazgos(parches={"APU-01!A2": ("#REF!", "=#REF!")})
    assert _firmas(hs) == [
        ("L2", "ERROR", ("APU-01!A2",), None),
        ("L5", "ERROR", ("APU-01!A2",), None),
    ]


def test_l2_titulo_ref_en_plantilla_sin_partida():
    """Mata en `_l2`: 445 (or -> and)."""
    apus = (*APUS_LIMPIOS, con(A1, numero=9, hoja="APU-x", en_presupuesto=False))
    hs = _hallazgos(apus, parches={"APU-x!A2": ("#REF!", "=#REF!")})
    assert _firmas(hs) == [
        ("L2", "INFO", ("APU-x!A2",), None),
        ("L5", "ERROR", ("APU-x!A2",), None),
    ]
    assert "(título #REF! en APU-x)" in hs[0].descripcion


# --- L3 -----------------------------------------------------------------------------------------


def test_l3_lectura_pura_dentro_de_apu_con_valor_viejo():
    """Mata en `_l3`: 474 (and -> or) y 499 (and -> or)."""
    hs = _hallazgos(parches={"APU-01!E19": (D("1.5"), "=FCAS")})
    # FCAS es el nombre definido de INSUMOS!E16 en el libro sintético.
    assert _firmas(hs) == [("L3", "ERROR", ("APU-01!E19", "INSUMOS!E16"), None)]


def test_l3_pu_viejo_con_cantidad_uno_es_error_con_impacto():
    """Mata en `_l3`: 493 (0 -> 1)."""
    hs = _hallazgos((con(A1, cantidad=D("1")), A2, A3), p_guardado={1: D("14")})
    assert _firmas(hs) == [
        ("L3", "ERROR", ("PRESUPUESTO!P5", "APU-01!G45"), D("0.49")),
        ("L9", "ERROR", ("PRESUPUESTO!N5", "PRESUPUESTO!O5", "PRESUPUESTO!P5"), D("0.49")),
        ("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q10"), D("0.49")),
    ]


def test_l3_monto_de_presupuesto_con_valor_viejo_es_error_con_impacto():
    """Mata en `_l3`: 496 (== -> !=), 497 (- -> +) y 498 (True -> False)."""
    hs = _hallazgos(parches={"PRESUPUESTO!Q10": (D("4000"), "=Q8")})
    assert _firmas(hs) == [
        ("L3", "ERROR", ("PRESUPUESTO!Q10", "PRESUPUESTO!Q8"), D("358.21")),
        ("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q10"), D("358.21")),
        ("L9", "ERROR", ("RESUMEN!B15", "PRESUPUESTO!Q10"), D("358.21")),
    ]


def test_l3_indirect_a_otra_hoja_apu_no_dispara_parche_a_mano():
    """Mata en `_l3_plantilla`: 548 (or -> and)."""
    hs = _hallazgos(
        parches={
            "PRESUPUESTO!P5": (
                D("30.2121875"),
                '=INDIRECT("\'APU-"&TEXT($B6,"00")&"\'!G40")',
            )
        }
    )
    dif = D("14.486725") - D("30.2121875")
    assert _firmas(hs) == [
        ("L1", "ERROR", ("PRESUPUESTO!P5", "APU-02!G40", "APU-01!G45"), None),
        ("L9", "ERROR", ("PRESUPUESTO!N5", "PRESUPUESTO!O5", "PRESUPUESTO!P5"), _c(dif * 120)),
    ]


# --- L5 -----------------------------------------------------------------------------------------


def test_l5_descripcion_nombra_celda_en_ref():
    """Mata en `_l5`: 614 (1 -> 0)."""
    hs = _hallazgos(resumen_ref_rota=True)
    assert _firmas(hs) == [("L5", "ERROR", ("RESUMEN!B13",), None)]
    assert "se borró): B13. Efecto:" in hs[0].descripcion


def test_l5_descripcion_nombra_celda_en_formula_externa():
    """Mata en `_l5`: 628 (1 -> 0)."""
    hs = _hallazgos(formula_externa=True)
    assert _firmas(hs) == [("L5", "ADVERTENCIA", ("MEDICIONES!D5",), None)]
    assert "leen otro libro: D5. Efecto:" in hs[0].descripcion


# --- L6 -----------------------------------------------------------------------------------------


def test_l6_porcentaje_con_nombre_definido_y_valor_sin_recalcular():
    """Mata en `_usa_nombre`: 703 (True -> False) y en `_l6_porcentajes`: 732 (or -> and)."""
    hs = _hallazgos(parches={"APU-01!F42": (D("0.12"), "=ADMON")})
    # ADMON es el nombre definido de INSUMOS!E18 en el libro sintético.
    assert _firmas(hs) == [("L3", "ERROR", ("APU-01!F42", "INSUMOS!E18"), None)]


def test_l6_no_avisa_si_el_parametro_no_esta_definido_en_el_libro():
    """Mata en `_l6_porcentajes`: 722 (or -> and)."""
    hs = _hallazgos((con(A1, utilidad_literal=D("0.10")), A2, A3), sin_parametros=("UTIL",))
    assert hs == []


def test_l6_utilidad_escrita_como_literal_en_la_celda_del_monto():
    """Mata en `_l6_porcentajes`: 731 (and -> or), 741 (or -> and) y 742 (1 -> 0)."""
    hs = _hallazgos(parches={"APU-01!G44": (D("1.316975"), "=G43*0.12")})
    assert _firmas(hs) == [("L6", "ADVERTENCIA", ("APU-01!G44",), D("-31.61"))]
    assert (hs[0].valor_observado, hs[0].valor_esperado) == (D("0.12"), D("0.10"))


def test_l6_rendimiento_literal_no_avisa_si_el_apu_no_tiene_rendimiento_numerico():
    """Mata en `_l6_rendimiento`: 778 (primer or -> and)."""
    hs = _hallazgos(
        (con(A1, divisor_equipos=D("12")), A2, A3),
        parches={
            "APU-01!F19": (None, None),
            "PRESUPUESTO!F5": (None, None),
            "CRONOGRAMA!D4": (None, None),
        },
    )
    assert hs == []


def test_l6_rendimiento_no_falla_en_apu_solo_con_materiales():
    """Mata en `_l6_rendimiento`: 778 (segundo or -> and)."""
    solo_mat = ApuSint(
        numero=1,
        codigo="E.311.000.001",
        descripcion="Material directo (ficticio)",
        unidad="m2",
        cantidad=D("10"),
        rendimiento=D("10"),
        materiales=(("MT-01", D("1")),),
    )
    assert _hallazgos((solo_mat,)) == []


def test_l6_rendimiento_literal_en_primera_fila_de_mano_de_obra():
    """Mata en `_l6_rendimiento`: 784 (<= -> <) y 810 (1 -> 0)."""
    hs = _hallazgos((con(A1, factores={"MO-01": "/12"}), A2, A3))
    assert _firmas(hs) == [("L6", "ADVERTENCIA", ("APU-01!G16", "APU-01!F19"), None)]
    assert "G16 usan «/12»" in hs[0].descripcion


def test_l6_rendimiento_no_mira_el_resumen_del_apu():
    """Mata en `_l6_rendimiento`: 784 (< -> <=)."""
    assert _hallazgos(parches={"APU-01!G37": (D("3.25"), "=G12/1")}) == []


# --- L7 -----------------------------------------------------------------------------------------


def test_l7_seccion_en_primera_fila_de_mediciones():
    """Mata en `_l7`: 848 (0 -> 1)."""
    hs = _hallazgos(
        mediciones_literales=("=9.73*2.75",),
        parches={"MEDICIONES!A1": ("A · Preliminares", None), "MEDICIONES!A3": ("Frisos", None)},
    )
    assert _firmas(hs) == [("L7", "INFO", ("MEDICIONES!D5",), None)]
    assert "«A · Preliminares»" in hs[0].descripcion


def test_l7_cuatro_celdas_nombran_celda_y_sin_puntos_suspensivos():
    """Mata en `_l7`: 857 (1 -> 0) y 858 (> -> >=)."""
    hs = _hallazgos(mediciones_literales=("=9.73*2.75", "=B4*0.28", "=1.5*2.5", "=3.2*4.1"))
    celdas = ("MEDICIONES!D5", "MEDICIONES!D6", "MEDICIONES!D7", "MEDICIONES!D8")
    assert _firmas(hs) == [("L7", "INFO", celdas, None)]
    assert "D5 =9.73*2.75" in hs[0].descripcion
    assert "; …" not in hs[0].descripcion


# --- L8 -----------------------------------------------------------------------------------------


def test_l8_numero_repetido_informa_match_y_sumif_de_otras_hojas():
    """Mata en `_l8`: 891 (1 -> 0, 0 -> 1) y 892 (== -> !=, or -> and, delete not)."""
    apus = (A1, A2, con(A2, hoja="APU-07", cantidad=D("0")))
    hs = _hallazgos(
        apus,
        parches={
            "CRONOGRAMA!B4": (
                A1.descripcion,
                "=INDEX(PRESUPUESTO!$D$5:$D$7,MATCH(A4,PRESUPUESTO!$B$5:$B$7,0))",
            ),
            "AUX!C2": (D("80"), "=SUMIF(PRESUPUESTO!$B$5:$B$7,2,PRESUPUESTO!$G$5:$G$7)"),
            "PRESUPUESTO!T5": (
                D("80"),
                "=SUMIF(PRESUPUESTO!$B$5:$B$7,2,PRESUPUESTO!$G$5:$G$7)",
            ),
        },
    )
    assert _firmas(hs) == [
        ("L8", "ADVERTENCIA", ("PRESUPUESTO!B6", "PRESUPUESTO!B7"), None),
    ]
    esperado = (
        "CRONOGRAMA buscan la partida por número (MATCH) y toman siempre la primera fila; "
        "AUX suman por número (SUMIF) y mezclan las filas repetidas."
    )
    assert hs[0].descripcion.endswith(esperado)


def test_l8_lookup_simple_tambien_busca_por_numero():
    """Mata en `_l8`: 895 (el segundo or -> and). «VLOOKUP(» ya contiene «LOOKUP(», así que solo
    una fórmula con LOOKUP simple distingue el mutante."""
    apus = (A1, A2, con(A2, hoja="APU-07", cantidad=D("0")))
    hs = _hallazgos(
        apus,
        parches={
            "CRONOGRAMA!B4": (
                A1.descripcion,
                "=LOOKUP(A4,PRESUPUESTO!$B$5:$B$7,PRESUPUESTO!$D$5:$D$7)",
            ),
        },
    )
    assert _firmas(hs) == [("L8", "ADVERTENCIA", ("PRESUPUESTO!B6", "PRESUPUESTO!B7"), None)]
    assert "CRONOGRAMA buscan la partida por número" in hs[0].descripcion


# --- L9 -----------------------------------------------------------------------------------------


def test_l9_resumen_no_falla_si_falta_el_subtotal_del_presupuesto():
    """Mata en `_l9_resumen`: 1062 (or -> and)."""
    assert _hallazgos(parches={"PRESUPUESTO!Q10": (None, None)}) == []


def test_l9_resumen_costo_de_la_obra_descuadrado_en_rango_de_una_fila():
    """Mata en `_l9_resumen`: 1076 (+ -> - y 1 -> 0)."""
    hs = _hallazgos(parches={"RESUMEN!B15": (D("4000"), "=SUM(B12:B12)")})
    assert _firmas(hs) == [("L9", "ERROR", ("RESUMEN!B15", "PRESUPUESTO!Q10"), D("-358.21"))]


def test_l9_resumen_composicion_con_dos_sumaproductos():
    """Mata en `_l9_resumen`: 1078 (>= -> >)."""
    hs = _hallazgos(parches={"RESUMEN!B10": (D("1000"), "=SUM(B4:B5)")})
    assert _firmas(hs) == [("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q10"), D("-3358.21"))]


def test_l9_resumen_no_juzga_otra_suma_que_cita_presupuesto():
    """Mata en `_l9_resumen`: 1080 (and -> or)."""
    hs = _hallazgos(
        parches={
            "RESUMEN!A14": ("Subtotal de capítulo", None),
            "RESUMEN!B14": (D("1738.407"), "=SUM(B12:B12)"),
        }
    )
    assert hs == []


@pytest.mark.parametrize(
    ("delta", "esperado"),
    [
        (D("0.0099"), []),
        (D("0.01"), [("L9", "ERROR", ("RESUMEN!B10", "PRESUPUESTO!Q10"), D("0.01"))]),
    ],
)
def test_l9_resumen_frontera_del_centavo(delta, esperado):
    """Mata en `_l9_resumen`: 1086 (< -> <=)."""
    assert _firmas(_hallazgos(resumen_composicion_delta=delta)) == esperado
