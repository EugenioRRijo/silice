"""Verifica los CSV de referencia MaPreX: formato, conversion y procedencia."""

import csv
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "data" / "precios" / "maprex_2026-07"
ARCHIVOS = [
    "referencia_civil.csv",
    "referencia_telecom.csv",
    "referencia_industrial.csv",
    "referencia_sistemas.csv",
]
TASA = Decimal("633.3644")
CABECERA = [
    "tipo",
    "insumo",
    "unidad",
    "precio_bs",
    "bono_bs",
    "factor_depreciacion",
    "precio_usd",
    "fecha_vigencia",
    "archivo",
    "ref_maprex",
    "notas",
]


def _filas(nombre):
    with open(CARPETA / nombre, newline="", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        assert lector.fieldnames == CABECERA
        return list(lector)


def test_archivos_existen_y_no_vacios():
    for nombre in ARCHIVOS:
        assert len(_filas(nombre)) > 0


def test_conversion_usd_con_tasa_declarada():
    for nombre in ARCHIVOS:
        for fila in _filas(nombre):
            esperado = (Decimal(fila["precio_bs"]) / TASA).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            assert Decimal(fila["precio_usd"]) == esperado, f"{nombre}: {fila['insumo']}"


def test_procedencia_completa():
    for nombre in ARCHIVOS:
        for fila in _filas(nombre):
            assert fila["ref_maprex"], f"{nombre}: {fila['insumo']} sin ref"
            assert fila["archivo"] in {"materiales.pdf", "equipos.pdf", "mano_de_obra.pdf"}
            assert fila["fecha_vigencia"] in {"2026-07-09", "2026-07-01"}
            assert fila["tipo"] in {"material", "equipo", "mano_obra"}


def test_tabulador_civ_completo():
    assert len(_filas("referencia_sistemas.csv")) == 43


def test_equipos_llevan_factor_de_depreciacion():
    for nombre in ARCHIVOS:
        for fila in _filas(nombre):
            if fila["archivo"] == "equipos.pdf":
                factor = Decimal(fila["factor_depreciacion"])
                assert Decimal("0") < factor <= Decimal("1")
