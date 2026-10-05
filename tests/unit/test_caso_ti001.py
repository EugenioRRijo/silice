"""Caso TI-001 (laptops HP, cableado Cat 6, EMT y servidor en rack) de punta a punta.

Oráculos: el total y los precios unitarios del informe publicado el 30/09/2026
(`docs/bitacora/2026-09-30-caso-ti001.md`), la identidad de cierre de la curva y el recálculo
independiente de `scripts/analisis_ti001.py`. Caso construido (NORMAS.md §1).
"""

from __future__ import annotations

import subprocess
import sys
from decimal import Decimal

import pytest

from core.contracts import Severidad
from scripts import analisis_ti001 as an
from tests.fixtures import caso_ti001 as caso

TOLERANCIA = Decimal("0.01")


@pytest.fixture(scope="module")
def resultado():
    return caso.elaborar_caso()


def test_total_y_cierre_de_la_curva(resultado):
    presupuesto = resultado.presupuesto
    assert abs(presupuesto.total - Decimal("50503.27")) <= TOLERANCIA
    assert presupuesto.total_curva == presupuesto.total
    assert len(presupuesto.curva) == len(caso.PLAN)


@pytest.mark.parametrize(
    ("codigo", "precio_unitario"),
    [
        ("TI-EMT1", "18.72"),
        ("TI-EMT34", "14.75"),
        ("TI-PTO", "19.19"),
        ("TI-UTP", "3.55"),
        ("TI-CERT", "15.55"),
        ("TI-RACK", "1845.50"),
        ("TI-UPS", "2030.48"),
        ("TI-SW", "1820.68"),
        ("TI-SRV", "4801.77"),
        ("TI-LAP", "3039.65"),
    ],
)
def test_precios_unitarios(resultado, codigo, precio_unitario):
    grupo = an.por_partida(resultado.presupuesto)[codigo]
    assert abs(grupo["resultado"].precio_unitario - Decimal(precio_unitario)) <= TOLERANCIA


def test_auditoria_cumple_sin_errores(resultado):
    """Las siete reglas corren y no queda ningún hallazgo. Hasta SF‑2 quedaban 40 INFO de R4 (M‑3: el
    adaptador telecom emitía `origen` y `destino` como especificaciones y R4 no los reconocía en el
    APU); cambia a propósito, con el ruling SF2‑M3 de `docs/bitacora/2026-10-sf.md` (spec §8.3)."""
    informe = resultado.informe
    assert informe.cumple
    assert len(informe.reglas_evaluadas) == 7
    assert not informe.hallazgos
    assert not [h for h in informe.hallazgos if h.regla == "R4"]


def test_el_motor_coincide_con_el_recalculo_independiente(resultado):
    for codigo, motor, manual, diferencia in an.verificaciones_motor(resultado.presupuesto):
        assert diferencia == 0, (codigo, motor, manual)


def test_pruebas_de_control():
    """Siete de siete errores sembrados se detectan. Hasta SF‑E5 el de 1/2 pulg se escapaba (A‑2: R4
    comparaba por subcadena y el APU cita la «Dobladora de tubo EMT 1/2 a 1 1/2 pulg»); cambia a
    propósito, con el ruling SF‑E5‑1 de `docs/bitacora/2026-10-sf.md` (spec §8.3)."""
    controles = {c["nombre"]: c["ok"] for c in an.pruebas_de_control()}
    assert len(controles) == 7
    no_detectados = [nombre for nombre, ok in controles.items() if not ok]
    assert no_detectados == []


def test_punto_de_equilibrio(resultado):
    equilibrio = an.punto_equilibrio(resultado.presupuesto)
    assert abs(equilibrio["PE"] - Decimal("28586.76")) <= TOLERANCIA
    assert abs(equilibrio["PE_pct"] - Decimal("56.60")) <= TOLERANCIA
    assert equilibrio["periodo"].startswith("Dia 6")
    # Identidad: en el PE el margen de contribución cubre el costo fijo (salvo la precisión finita
    # de Decimal al dividir y volver a multiplicar).
    assert abs(equilibrio["PE"] * equilibrio["m"] - equilibrio["CF"]) < Decimal("1e-20")


def test_sensibilidad_del_bono_y_de_la_cascada(resultado):
    filas = {
        nombre: variacion for nombre, _, variacion, _ in an.sensibilidad(resultado.presupuesto)
    }
    assert filas["Caso base (parametros del informe)"] == 0
    assert (
        abs(filas["Bono exacto por oficio (MaPreX) en vez de bono unico"] + Decimal("23.04"))
        <= TOLERANCIA
    )
    assert filas["Error tipico: sumar adm. + util. (1,25) en vez de encadenar (1,265)"] < 0


@pytest.mark.parametrize("script", ["informe_ti001.py", "glosario_presupuestos.py"])
def test_los_pdf_se_generan(tmp_path, script):
    pytest.importorskip("reportlab")
    pytest.importorskip("matplotlib")
    salida = tmp_path / "salida.pdf"
    subprocess.run(
        [sys.executable, f"scripts/{script}", "--salida", str(salida)],
        check=True,
        cwd=caso.RAIZ,
        capture_output=True,
    )
    assert salida.read_bytes().startswith(b"%PDF")
