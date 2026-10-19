"""Guardia de tamano del lector `.xls` del BCV (MEDIO-2 de la revision de seguridad).

`xlrd` no esta instalado en este equipo: se inyecta un modulo falso en `sys.modules` cuyas hojas
declaran dimensiones enormes (un `.xls` de pocos KB puede declarar 65 536 x 256 celdas por hoja, y
un libro puede traer cientos de hojas). El lector debe rechazarlo ANTES del doble bucle, con un
mensaje claro (`FormatoNoReconocido`), sin recorrer celdas.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

from adapters.bcv import libro as modulo
from adapters.bcv.informe import FormatoNoReconocido

FIRMA_OLE2 = bytes.fromhex("D0CF11E0A1B11AE1")


class _Celda:
    def __init__(self, ctype: int, value) -> None:
        self.ctype, self.value = ctype, value


class _Hoja:
    def __init__(self, nombre: str, nrows: int, ncols: int, celdas: int = 0) -> None:
        self.name, self.nrows, self.ncols = nombre, nrows, ncols
        self.leidas = 0
        self._celdas = celdas

    def cell(self, r: int, c: int) -> _Celda:
        self.leidas += 1
        return _Celda(2, 1.5)  # XL_CELL_NUMBER


class _Libro:
    datemode = 0

    def __init__(self, hojas: list[_Hoja]) -> None:
        self._hojas = hojas
        self.nsheets = len(hojas)
        self.descargadas: list[int] = []

    def sheets(self) -> list[_Hoja]:
        return list(self._hojas)

    def sheet_by_index(self, i: int) -> _Hoja:
        return self._hojas[i]

    def release_resources(self) -> None:
        pass

    def unload_sheet(self, i: int) -> None:
        self.descargadas.append(i)


def _xlrd_falso(monkeypatch, hojas: list[_Hoja]) -> dict:
    llamadas: dict = {}
    libro = _Libro(hojas)

    def open_workbook(*args, **kwargs):
        llamadas.update(kwargs)
        return libro

    falso = ModuleType("xlrd")
    falso.open_workbook = open_workbook
    falso.XL_CELL_EMPTY, falso.XL_CELL_TEXT, falso.XL_CELL_NUMBER = 0, 1, 2
    falso.XL_CELL_DATE, falso.XL_CELL_BLANK = 3, 6
    monkeypatch.setitem(sys.modules, "xlrd", falso)
    llamadas["libro"] = libro
    return llamadas


def _xls(tmp_path: Path) -> Path:
    ruta = tmp_path / "tasa.xls"
    ruta.write_bytes(FIRMA_OLE2 + b"\x00" * 64)
    return ruta


def test_una_hoja_con_dimensiones_enormes_se_rechaza_sin_recorrerla(monkeypatch, tmp_path):
    hoja = _Hoja("H", 65_536, 256)  # 16 777 216 celdas declaradas
    llamadas = _xlrd_falso(monkeypatch, [hoja])
    with pytest.raises(FormatoNoReconocido) as error:
        modulo.abrir_libro(_xls(tmp_path))
    texto = str(error.value)
    assert "tasa.xls" in texto and "H" in texto
    assert "2000000" in texto
    assert hoja.leidas == 0
    assert llamadas["libro"].nsheets == 1


def test_mas_de_50_hojas_se_rechaza_antes_de_cargar_ninguna(monkeypatch, tmp_path):
    hojas = [_Hoja(f"H{n}", 1, 1) for n in range(51)]
    _xlrd_falso(monkeypatch, hojas)
    with pytest.raises(FormatoNoReconocido) as error:
        modulo.abrir_libro(_xls(tmp_path))
    assert "51 hojas" in str(error.value) and "50" in str(error.value)
    assert all(h.leidas == 0 for h in hojas)


def test_una_celda_por_encima_del_tope_se_rechaza(monkeypatch, tmp_path):
    de_mas = _Hoja("M", 2_000_001, 1)
    _xlrd_falso(monkeypatch, [de_mas])
    with pytest.raises(FormatoNoReconocido):
        modulo.abrir_libro(_xls(tmp_path))
    assert de_mas.leidas == 0


def test_50_hojas_pequenas_se_leen_y_se_abre_bajo_demanda(monkeypatch, tmp_path):
    hojas = [_Hoja(f"H{n}", 2, 2) for n in range(50)]
    llamadas = _xlrd_falso(monkeypatch, hojas)
    libro = modulo.abrir_libro(_xls(tmp_path))
    assert len(libro.hojas) == 50
    assert libro.hojas[0].filas == ((Decimal("1.5"),) * 2,) * 2
    assert llamadas["on_demand"] is True
    assert llamadas["libro"].descargadas == list(range(50))
