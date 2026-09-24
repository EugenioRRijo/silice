"""Los CSV ARENAZA suman exactamente los totales de cada PDF y registran el 80/90."""
import csv
from decimal import Decimal
from pathlib import Path

from tests.fixtures.presupuestos_arenaza import (
    PRESUPUESTO_1,
    PRESUPUESTO_2,
    TOTAL_1,
    TOTAL_2,
    TUBO_CORRUGADO,
)

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "data" / "telecom" / "fuentes"


def _total_csv(nombre):
    with open(CARPETA / nombre, newline="", encoding="utf-8") as f:
        return sum(Decimal(fila["total"]) for fila in csv.DictReader(f))


def _filas_csv(nombre):
    with open(CARPETA / nombre, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fila_fixture_como_csv(renglon):
    """El mismo renglon del fixture, con sus 7 campos convertidos a texto exactamente como
    los escribe `scripts/extraer_arenaza.py` (cantidad/precio_unitario en None -> celda vacia),
    para compararlo campo a campo contra la fila leida del CSV."""
    return {
        "renglon": str(renglon.renglon),
        "descripcion": renglon.descripcion,
        "unidad": renglon.unidad,
        "cantidad": "" if renglon.cantidad is None else str(renglon.cantidad),
        "precio_unitario": "" if renglon.precio_unitario is None else str(renglon.precio_unitario),
        "total": str(renglon.total),
        "origen": renglon.origen,
    }


def test_totales_exactos():
    assert TOTAL_1 == Decimal("1109.29")
    assert TOTAL_2 == Decimal("5410.73")
    assert _total_csv("presupuesto_1_arenaza.csv") == TOTAL_1
    assert _total_csv("presupuesto_2_arenaza.csv") == TOTAL_2


def test_conteo_renglones():
    assert len(PRESUPUESTO_1) == 14
    assert len(PRESUPUESTO_2) == 26


def test_inconsistencia_80_90_registrada():
    assert TUBO_CORRUGADO["cantidad_computos"] == Decimal("80")
    assert TUBO_CORRUGADO["cantidad_presupuesto"] == Decimal("90")


def test_fixture_coincide_con_csv():
    for renglones, nombre in [(PRESUPUESTO_1, "presupuesto_1_arenaza.csv"),
                              (PRESUPUESTO_2, "presupuesto_2_arenaza.csv")]:
        assert sum(r.total for r in renglones) == _total_csv(nombre)
        # Reconciliacion campo a campo (las 7 columnas, las 40 filas): la unica copia
        # estructurada es el fixture (CLAUDE.md seccion 2, principio DRY); esta comparacion
        # detecta cualquier divergencia entre el fixture y el CSV que la suma de `total` por si
        # sola no vería (una descripcion, unidad, cantidad, precio_unitario u origen distintos).
        filas_csv = _filas_csv(nombre)
        assert len(filas_csv) == len(renglones)
        for renglon, fila_csv in zip(renglones, filas_csv, strict=True):
            assert _fila_fixture_como_csv(renglon) == fila_csv
