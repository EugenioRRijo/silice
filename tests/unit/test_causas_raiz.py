"""Hallazgos agrupados por causa raíz y avisos de regla no aplicable (pantalla de auditoría).

Una fórmula copiada con una fila fija da un hallazgo por cada partida que la repite: la causa es
una sola. Los casos son textos construidos con la forma de los mensajes de L1, L9 y R2.
"""

from __future__ import annotations

from aplicacion import causas_raiz as c

_CRONO = ("CRONOGRAMA!D{n} (partida {n}) lee APU-0{n}!F23 (valor {v}) como rendimiento; el "
          "rendimiento de APU-0{n} está en APU-0{n}!F25 (valor 0,5). Efecto: la duración cambia")


def test_la_misma_formula_copiada_es_una_causa_con_sus_posiciones():
    filas = [
        ("L1", "ERROR", _CRONO.format(n=4, v="vacía")),
        ("L9", "ERROR", "PLAN DE PAGOS!B6 «Verificación» vale 40,00 USD"),
        ("L1", "CRITICO", _CRONO.format(n=5, v="«Costo/día (USD)»")),
    ]
    causas, no_aplicables = c.agrupar(filas)
    assert [(x.codigo, x.indices) for x in causas] == [("L1", (0, 2)), ("L9", (1,))]
    assert causas[0].severidad == "CRITICO"  # la más grave de sus casos
    assert causas[0].descripcion == filas[0][2]  # la del primer caso
    assert no_aplicables == []


def test_los_avisos_de_regla_no_aplicable_van_aparte():
    filas = [
        ("R2", "INFO", "R2 no aplicable: el presupuesto no declara curva de inversion"),
        ("L1", "ERROR", _CRONO.format(n=4, v="vacía")),
        ("R7", "INFO", "R7 no aplicable: el presupuesto no declara plan de trabajo"),
    ]
    causas, no_aplicables = c.agrupar(filas)
    assert [x.indices for x in causas] == [(1,)]
    assert no_aplicables == [0, 2]


def test_un_info_que_no_dice_no_aplicable_es_un_hallazgo():
    causas, no_aplicables = c.agrupar([("L7", "INFO", "MEDICIONES: 1 fórmula con medidas")])
    assert len(causas) == 1 and no_aplicables == []


def test_reglas_distintas_con_el_mismo_texto_no_se_juntan():
    causas, _ = c.agrupar([("L5", "ERROR", "texto"), ("L6", "ERROR", "texto")])
    assert [x.codigo for x in causas] == ["L5", "L6"]


def test_una_cifra_con_espacio_de_miles_es_una_sola_cifra():
    # Las reglas escriben los montos de mil o más con espacio de miles (`9 999,90`, a veces con
    # espacio fino o duro): la misma causa no se parte en dos por el tamaño del monto.
    # Hallazgo de Gemini Neon, 2026-11-23.
    base = c.patron("RESUMEN!B6 «Verificación» vale 999,99 USD")
    for monto in ("9 999,90", "9 999,90", "1 234 567,00"):
        assert c.patron(f"RESUMEN!B6 «Verificación» vale {monto} USD") == base


def test_el_patron_quita_celdas_numeros_y_el_valor_encontrado():
    assert c.patron(_CRONO.format(n=4, v="vacía")) == c.patron(_CRONO.format(n=9, v="0,75"))
    assert c.patron("AUX lee de APU-07 filas fijas; deja sin leer EQ-03") == \
        c.patron("AUX lee de APU-02 filas fijas; deja sin leer MO-01, MO-05")
