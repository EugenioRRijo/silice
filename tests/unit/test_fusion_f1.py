"""F1 «P.U. recalculado» (Silice 1.5, RF-103; spec §3, errata 5, arreglo V7 «F1 a céntimos»).

F1 compara el P.U. del motor del núcleo con el P guardado en PRESUPUESTO; impacto = (P.U. de
Silice − P guardado) × cantidad, en céntimos ROUND_HALF_UP; el umbral (≥ 0,01) se mide sobre el
valor SIN redondear. Se siembra un P guardado viejo (`Siembra.p_guardado`): la partida 3 (APU-03,
cantidad 50, P.U. de la memoria 4,056525) y la partida 1 (APU-01, cantidad 120, 14,486725).

Oráculo: aritmética a mano en cada caso (Δ × cantidad), nunca la función bajo prueba.
"""

from __future__ import annotations

from datetime import date

import pytest

from fusion.proceso import ACCION_CORREGIDO, REGLA_F1, UMBRAL_F1, procesar_libro
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    D,
    PartidaSinApu,
    Siembra,
    con,
    construir_libro,
)

A1, A2, A3 = APUS_LIMPIOS
PU3 = D("4.056525")
HOY = date(2026, 10, 13)


def _f1(apus=APUS_LIMPIOS, **siembra):
    c = construir_libro(apus, Siembra(**siembra))
    r = procesar_libro(c.datos, "f1.xlsx", fecha_devolucion=HOY)
    return [h for h in r.informe.hallazgos if h.regla == "F1"], r


def test_constantes():
    assert REGLA_F1 == ("F1", "P.U. recalculado")
    assert UMBRAL_F1 == D("0.01")


def test_libro_limpio_sin_f1():
    assert _f1()[0] == []


@pytest.mark.parametrize(
    ("guardado", "impacto"),
    [
        # Δ = 0,000199 × 50 = 0,00995 < 0,01: no es hallazgo
        (PU3 - D("0.000199"), None),
        # Δ = 0,0002 × 50 = 0,01 exacto: sí (≥)
        (PU3 - D("0.0002"), D("0.01")),
        # Δ = 0,0005 × 50 = 0,025 -> 0,03 (ROUND_HALF_UP; el redondeo bancario daría 0,02)
        (PU3 - D("0.0005"), D("0.03")),
        # P guardado mayor que el de Silice: −0,025 -> −0,03 (cobra de más)
        (PU3 + D("0.0005"), D("-0.03")),
        # −0,000199 × 50 = −0,00995: |bruto| < 0,01
        (PU3 + D("0.000199"), None),
    ],
)
def test_frontera_y_redondeo_del_impacto(guardado, impacto):
    f1, _ = _f1(p_guardado={3: guardado})
    if impacto is None:
        assert f1 == []
        return
    assert len(f1) == 1
    h = f1[0]
    assert (h.severidad.name, h.impacto) == ("ERROR", impacto)
    assert h.origen_ids == ("PRESUPUESTO!P7", "APU-03!G41")
    assert (h.valor_observado, h.valor_esperado) == (guardado, PU3)


def test_f1_del_equipo_omitido_h1():
    """H1 en APU-02: el P guardado es 23,375 × 1,21 = 28,28375 y el motor da 30,2121875;
    (30,2121875 − 28,28375) × 80 = 154,275 -> 154,28."""
    f1, r = _f1((A1, con(A2, cd_sin_equipos=True), A3))
    assert [(h.origen_ids, h.impacto, h.valor_observado, h.valor_esperado) for h in f1] == [
        (("PRESUPUESTO!P6", "APU-02!G40"), D("154.28"), D("28.28375"), D("30.2121875"))
    ]
    assert r.precios_unitarios[6] == D("30.2121875")
    acciones = {(f.codigo, f.celda): f.accion for f in r.hallazgos_tabla}
    assert acciones[("F1", "PRESUPUESTO!P6")] == ACCION_CORREGIDO
    assert r.informe.partida_por_hallazgo[f1[0]] == "E.321.000.002"


def test_partida_con_cantidad_cero_nunca_da_f1():
    apus = (A1, A2, con(A2, hoja="APU-07", cantidad=D("0"), rendimiento=D("10")))
    f1, _ = _f1(apus, p_guardado={2: D("1")})
    # Solo la partida 2 de la fila 6 (cantidad 80) tiene P viejo: 80 × (30,2121875 − 1).
    assert [(h.origen_ids[0], h.impacto) for h in f1] == [("PRESUPUESTO!P6", D("2336.98"))]


def test_partida_sin_apu_no_es_f1_sino_l2():
    sin = PartidaSinApu(9, "S/C", "Limpieza final (ficticia)", "glb", D("1"), D("50"))
    f1, r = _f1(partidas_sin_apu=(sin,))
    assert f1 == []
    assert ("L2", ("PRESUPUESTO!B8",)) in {(h.regla, h.origen_ids) for h in r.informe.hallazgos}
    # Sin APU, la partida entra a los totales con su monto guardado (50).
    assert r.totales_silice["SUBSINIVA"] == D("4358.20825") + D("50")


def test_utilidad_escrita_a_mano_no_da_f1():
    """F-D7: el 2 % escrito a mano se conserva; el motor usa la utilidad del APU y coincide."""
    f1, _ = _f1((A1, con(A2, utilidad_literal=D("0.02")), A3))
    assert f1 == []


def test_el_texto_de_f1_escribe_las_cifras_como_l9_y_nombra_a_silice_con_tilde():
    """VB-8: F1 escribía «28.28375 … 154.28» (punto decimal) junto a L9 «4 331,43 USD»; en es-VE
    «154.28» se lee ciento cincuenta y cuatro mil. Las cifras de F1 van con coma decimal y espacio
    de miles, como `_fmt` de las reglas L: P.U. con todos sus decimales, impacto en céntimos.
    Oráculo del caso H1 (arriba): 28,28375 guardado, 30,2121875 del motor, cantidad 80, 154,28."""
    f1, _ = _f1((A1, con(A2, cd_sin_equipos=True), A3))
    texto = f1[0].descripcion
    assert (
        "PRESUPUESTO guarda un P.U. de 28,28375 y el motor de Sílice lo recalcula en 30,2121875 "
        "con el APU APU-02; la diferencia por la cantidad (80) mueve el total sin IVA en 154,28"
    ) in texto
    assert "Silice" not in texto


def test_el_impacto_de_f1_con_miles_lleva_espacio_de_miles():
    """80 × (30,2121875 − 1) = 2 336,975 -> 2 336,98 (el caso de la partida con cantidad 0)."""
    apus = (A1, A2, con(A2, hoja="APU-07", cantidad=D("0"), rendimiento=D("10")))
    f1, _ = _f1(apus, p_guardado={2: D("1")})
    assert f1[0].descripcion.endswith("mueve el total sin IVA en 2 336,98")
    assert "P.U. de 1 y el motor de Sílice lo recalcula en 30,2121875" in f1[0].descripcion
