# tests/unit/test_memoria_ob_s2.py
"""El oráculo de S2 (`tests/fixtures/memorias/control_ob_s2.md`): trae sus cifras literales y sus
cuentas se rehacen **con aritmética de `fractions.Fraction`**, independiente de `Decimal` y de todo
código del sistema, a partir de los datos crudos de la memoria. Si la memoria se equivocara, esta
prueba lo diría antes de que ninguna función se compare con ella.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

F = Fraction
MEMORIA = Path(__file__).resolve().parents[1] / "fixtures" / "memorias" / "control_ob_s2.md"
LITERALES = [
    "1 500,00", "1 200,00", "0,8000", "0,9375", "4 480,00", "4 266,67", "−480,00", "−60,00",
    "−20,00", "−410,00", "−70,00", "11,11", "21,67", "22,5", "2026-12-02", "75,90", "5 135,90",
    "6 019,66", "5 402,91", "5 610,00", "4 887,68", "95,17 %", "6 860,09", "5 985,37", "115,3125",
    "110,00", "165,3125", "50,00", "OB-002", "siete", "2 864,15",
]  # fmt: skip

# Datos crudos de la memoria §1 y §2.
Q = {"A": F(100), "B": F(200), "C": F(100)}
U = {"A": F(10), "B": F(5), "C": F(20)}
U_CORTE = {"A": F(10), "B": F(6), "C": F("22.10")}
QE = {"A": F(90), "B": F(60), "C": F(0)}
PLAN = {"A": (F(1, 2), F(1, 2), 0, 0), "B": (0, F(1, 2), F(1, 2), 0), "C": (0, 0, F(1, 2), F(1, 2))}
AC = F(1280)
VENTA = sum(Q[p] * U[p] for p in Q) * F("1.265")
CF = sum(Q[p] * U[p] for p in Q) * F("0.15")


def test_la_memoria_existe_y_trae_sus_cifras_literales():
    texto = MEMORIA.read_text(encoding="utf-8")
    faltan = [cifra for cifra in LITERALES if cifra not in texto]
    assert not faltan, f"la memoria no trae {faltan}"


def test_el_valor_ganado_rehecho_con_fracciones():
    bac = sum(Q[p] * U[p] for p in Q)
    pv = sum(Q[p] * U[p] * sum(PLAN[p][:2]) for p in Q)  # corte en el dia 10: 2 periodos terminados
    ev = sum(QE[p] * U[p] for p in Q)
    en_corte = sum(QE[p] * U_CORTE[p] for p in Q)
    cpic = en_corte / AC
    eac = AC + sum((Q[p] - QE[p]) * U_CORTE[p] for p in Q) / cpic
    assert (bac, pv, ev) == (4000, 1500, 1200)
    assert (ev / pv, ev / AC, cpic) == (F(4, 5), F(15, 16), F(63, 64))
    assert eac == 4480 and round(bac / (ev / AC), 2) == F("4266.67")
    precio = sum(QE[p] * (U[p] - U_CORTE[p]) for p in Q)
    consumo = en_corte - AC
    assert (precio, consumo, ev - AC) == (-60, -20, -80) and precio + consumo == ev - AC
    vac_precio = -sum(Q[p] * (U_CORTE[p] - U[p]) for p in Q)
    assert (vac_precio, bac - eac - vac_precio) == (-410, -70)


def test_el_punto_de_equilibrio_base_y_los_proyectados_rehechos_con_fracciones():
    def pe(cv, cf, v):
        return cf * v / (v - cv)

    assert round(pe(F(4000), CF, VENTA), 2) == F("2864.15")
    reajuste = 60 * (F("7.59") - F("6.325"))
    assert reajuste == F("75.90") and VENTA + reajuste == F("5135.90")
    casos = {
        "aceptar": (F(4480), F(30) * 23, F("6019.66"), F("5402.91")),
        "cuadrillas": (F(4600), F(30) * 17, F("5610.00"), F("4887.68")),
        "horas": (F("4595.3125"), F(30) * 21, F("6860.09"), F("5985.37")),
    }
    for nombre, (cv, cf, sin, con) in casos.items():
        assert round(pe(cv, cf, VENTA), 2) == sin, nombre
        assert round(pe(cv, cf, VENTA + reajuste), 2) == con, nombre
        minimo = cv + cf - VENTA  # reajuste necesario para que PE' <= V'
        assert (minimo <= reajuste) is (nombre == "cuadrillas"), nombre
    assert round(pe(F(4600), F(510), VENTA + reajuste) / (VENTA + reajuste) * 100, 2) == F("95.17")


@pytest.mark.parametrize(
    ("nombre", "rendimiento", "salario", "cuadrilla", "restante", "costo_dia"),
    [("B", 20, 5, 2, 140, 40), ("C", 10, 10, 4, 100, 80)],
)
def test_los_costos_de_cuadrillas_y_horas_extra_rehechos_con_fracciones(
    nombre, rendimiento, salario, cuadrilla, restante, costo_dia
):
    e = 1 + F(4, 5)
    assert (
        F(restante * costo_dia) * (2 - e) / (rendimiento * e)
        == {
            "B": F(1120, 36),
            "C": F(1600, 18),
        }[nombre]
    )
    m = 1 + F(2, 8) * F(4, 5)
    ot = F(2, 8) * F(3, 2) * salario * 7
    adicional = restante * (costo_dia + ot - costo_dia * m) / (rendimiento * m)
    assert round(adicional, 4) == {"B": F("29.8958"), "C": F("85.4167")}[nombre]
    assert cuadrilla > 0


def test_la_suma_de_los_adicionales_es_la_de_la_memoria():
    cuadrillas = F(1120, 36) + F(1600, 18)
    assert cuadrillas == 120
    m = 1 + F(2, 8) * F(4, 5)
    horas = sum(
        r * (cd + F(2, 8) * F(3, 2) * s * 7 - cd * m) / (rend * m)
        for r, cd, s, rend in ((140, 40, 5, 20), (100, 80, 10, 10))
    )
    assert horas == F("115.3125")


def _numero(texto: str) -> Fraction:
    """«1 500,00», «−80,00» o «0,9375» como fracción exacta."""
    limpio = texto.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    limpio = limpio.replace("\u2212", "-").replace(",", ".").rstrip("%")
    return Fraction(limpio)


def _tabla_de_la_memoria(titulo: str) -> dict[str, list[str]]:
    """Etiqueta -> celdas sin negritas, de las filas de la tabla que sigue a `titulo`."""
    lineas = MEMORIA.read_text(encoding="utf-8").splitlines()
    inicio = next(i for i, linea in enumerate(lineas) if linea.startswith(titulo))
    filas: dict[str, list[str]] = {}
    for linea in lineas[inicio + 1 :]:
        if linea.startswith("#") and filas:
            break
        if linea.startswith("|") and "---" not in linea:
            celdas = [c.strip() for c in linea.strip("|").split("|")]
            filas[celdas[0]] = [c.replace("**", "") for c in celdas]
    return filas


def test_la_tabla_de_valor_ganado_de_la_memoria_coincide_con_el_recalculo_exacto():
    """No basta que las cifras aparezcan en el texto: cada fila de la tabla de la memoria debe
    ser el valor que sale de los datos crudos (con Fraction), a los decimales que la memoria da."""
    bac = sum(Q[p] * U[p] for p in Q)
    pv = sum(Q[p] * U[p] * sum(PLAN[p][:2]) for p in Q)
    ev = sum(QE[p] * U[p] for p in Q)
    en_corte = sum(QE[p] * U_CORTE[p] for p in Q)
    cpic = en_corte / AC
    eac = AC + sum((Q[p] - QE[p]) * U_CORTE[p] for p in Q) / cpic
    esperado = {
        "PV": (pv, 2),
        "EV": (ev, 2),
        "AC": (AC, 2),
        "SV": (ev - pv, 2),
        "SPI": (ev / pv, 4),
        "CV": (ev - AC, 2),
        "CPI": (ev / AC, 4),
        "CPIc": (cpic, 6),
        "VAC": (bac - eac, 2),
    }
    tabla = _tabla_de_la_memoria("| Resultado |")
    for etiqueta, (valor, decimales) in esperado.items():
        escrito = _numero(tabla[etiqueta][-1])
        assert round(valor, decimales) == escrito, (etiqueta, tabla[etiqueta])
    assert _numero(tabla["EAC (sistema)"][-1]) == round(eac, 2)
    assert _numero(tabla["EAC (índice)"][-1]) == round(bac / (ev / AC), 2)


def test_la_tabla_de_opciones_de_la_memoria_coincide_con_el_recalculo_exacto():
    def pe(cv, cf, v):
        return cf * v / (v - cv)

    reajuste = 60 * (F("7.59") - F("6.325"))
    v_sin, v_con = VENTA, VENTA + reajuste
    tabla = _tabla_de_la_memoria("| Opción |")
    filas = {
        "Aceptar el retraso": (F(4480), 23),
        "Más cuadrillas": (F(4600), 17),
        "Horas extra": (F("4595.3125"), 21),
    }
    for nombre, (cv, dias) in filas.items():
        cf = F(30) * dias
        escrito = " ".join(tabla[nombre]).replace(" ", "")
        for venta in (v_sin, v_con):
            cifra = f"{float(round(pe(cv, cf, venta), 2)):.2f}".replace(".", ",")
            assert cifra in escrito, (nombre, cifra)
