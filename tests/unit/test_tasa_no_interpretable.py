"""Pruebas de `scripts/tasa_no_interpretable.py` sobre libros sintéticos y corruptos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from scripts import tasa_no_interpretable as t
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    PARAMETROS,
    Siembra,
    construir_libro,
    libro_limpio,
)

FECHA = date(2026, 11, 23)


def _escribir_libro_sin_plantilla(ruta: Path) -> None:
    wb = openpyxl.Workbook()
    try:
        wb.save(ruta)
    finally:
        wb.close()


def test_tasa_con_libro_bueno_corrupto_y_sin_hojas_de_plantilla(tmp_path: Path) -> None:
    carpeta = tmp_path / "lote_libros"
    carpeta.mkdir()
    (carpeta / "obra_buena_confidencial.xlsx").write_bytes(libro_limpio().datos)
    (carpeta / "archivo_corrupto_secreto.xlsx").write_bytes(b"\x00\xffno es un xlsx valido")
    _escribir_libro_sin_plantilla(carpeta / "sin_hojas_plantilla_privado.xlsx")

    resumen = t.medir_carpeta(carpeta, fecha=FECHA)
    assert resumen.total == 3
    assert resumen.auditados == 1
    assert resumen.rechazados == 2
    assert resumen.no_interpretables == 0
    assert sum(resumen.motivos_rechazo.values()) == 2
    assert len(resumen.motivos_rechazo) == 2

    tabla = t.formatear_tabla(resumen)
    assert "33,3 %" in tabla
    assert "66,7 %" in tabla
    assert "100,0 %" in tabla
    for nombre in (
        "obra_buena_confidencial",
        "archivo_corrupto_secreto",
        "sin_hojas_plantilla_privado",
    ):
        assert nombre not in tabla


def test_tasa_cuenta_libro_no_interpretable_sin_filtrar_nombres_ni_montos(tmp_path: Path) -> None:
    carpeta = tmp_path / "lote_no_interpretable"
    carpeta.mkdir()
    datos = construir_libro(
        APUS_LIMPIOS,
        Siembra(parametros={**PARAMETROS, "FCAS": Decimal("0.5")}),
    ).datos
    (carpeta / "cliente_privado_999.xlsx").write_bytes(datos)

    resumen = t.medir_carpeta(carpeta, fecha=FECHA)
    assert (resumen.total, resumen.auditados, resumen.rechazados, resumen.no_interpretables) == (
        1,
        0,
        0,
        1,
    )
    tabla = t.formatear_tabla(resumen)
    assert "cliente_privado_999" not in tabla
    assert "0.5000" not in tabla and "0,5000" not in tabla
    assert "100,0 %" in tabla


def test_tasa_rechaza_carpeta_dentro_del_repositorio(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    carpeta = repo / "libros"
    carpeta.mkdir(parents=True)
    with pytest.raises(ValueError, match="repositorio"):
        t.medir_carpeta(carpeta, raiz_repo=repo)


def test_tasa_cli_imprime_tabla_con_porcentajes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    carpeta = tmp_path / "lote_cli"
    carpeta.mkdir()
    (carpeta / "bueno.xlsx").write_bytes(libro_limpio().datos)
    (carpeta / "roto.xlsx").write_bytes(b"corrupto")
    assert t.main([str(carpeta), "--fecha", "2026-11-23"]) == 0
    salida = capsys.readouterr().out
    assert "| Estado | Libros | Porcentaje |" in salida
    assert "50,0 %" in salida
