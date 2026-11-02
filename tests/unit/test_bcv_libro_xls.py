"""Guardia de tamano del lector `.xls` del BCV (MEDIO-2 de la revision de seguridad).

Se inyecta un modulo falso en `sys.modules` cuyas hojas
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
        self.pedidas: list[int] = []

    def sheets(self) -> list[_Hoja]:
        return list(self._hojas)

    def sheet_names(self) -> list[str]:
        return [h.name for h in self._hojas]

    def sheet_by_index(self, i: int) -> _Hoja:
        self.pedidas.append(i)
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
    hoja = _Hoja("01072026", 65_536, 256)  # 16 777 216 celdas declaradas
    llamadas = _xlrd_falso(monkeypatch, [hoja])
    with pytest.raises(FormatoNoReconocido) as error:
        modulo.abrir_libro(_xls(tmp_path))
    texto = str(error.value)
    assert "tasa.xls" in texto and "01072026" in texto
    assert "2000000" in texto
    assert hoja.leidas == 0
    assert llamadas["libro"].nsheets == 1


def test_una_celda_por_encima_del_tope_se_rechaza(monkeypatch, tmp_path):
    de_mas = _Hoja("01072026", 2_000_001, 1)
    _xlrd_falso(monkeypatch, [de_mas])
    with pytest.raises(FormatoNoReconocido):
        modulo.abrir_libro(_xls(tmp_path))
    assert de_mas.leidas == 0


def _dia(n: int) -> str:
    return f"{n % 28 + 1:02d}{n // 28 + 1:02d}2026"


def test_un_libro_de_64_hojas_con_las_necesarias_se_lee_y_no_se_piden_las_ajenas(
    monkeypatch, tmp_path
):
    hojas = [_Hoja(_dia(n), 2, 2) for n in range(60)]
    hojas[10:10] = [_Hoja(f"Notas{n}", 2, 2) for n in range(4)]
    llamadas = _xlrd_falso(monkeypatch, hojas)
    libro = modulo.abrir_libro(_xls(tmp_path))
    assert len(libro.hojas) == 60
    assert libro.hojas[0].filas == ((Decimal("1.5"),) * 2,) * 2
    assert llamadas["on_demand"] is True
    ajenas = {i for i, h in enumerate(hojas) if h.name.startswith("Notas")}
    assert ajenas and not ajenas & set(llamadas["libro"].pedidas)
    assert all(h.leidas == 0 for h in hojas if h.name.startswith("Notas"))
    assert any("hojas ajenas no leidas: 4" in a for a in libro.avisos)
    assert sorted(llamadas["libro"].descargadas) == sorted(llamadas["libro"].pedidas)


def test_el_tope_de_hojas_se_mide_sobre_las_leidas_no_sobre_el_total(monkeypatch, tmp_path):
    hojas = [_Hoja(_dia(n), 1, 1) for n in range(modulo.MAX_HOJAS_LEIDAS)]
    hojas += [_Hoja(f"Ajena{n}", 1, 1) for n in range(100)]  # total 200 <= 256
    _xlrd_falso(monkeypatch, hojas)
    assert len(modulo.abrir_libro(_xls(tmp_path)).hojas) == modulo.MAX_HOJAS_LEIDAS


def test_mas_hojas_necesarias_que_el_tope_se_rechaza_sin_leer_ninguna(monkeypatch, tmp_path):
    hojas = [_Hoja(_dia(n), 1, 1) for n in range(modulo.MAX_HOJAS_LEIDAS + 1)]
    llamadas = _xlrd_falso(monkeypatch, hojas)
    with pytest.raises(FormatoNoReconocido, match="hojas necesarias"):
        modulo.abrir_libro(_xls(tmp_path))
    assert llamadas["libro"].pedidas == []


def test_sin_hojas_necesarias_el_error_es_claro(monkeypatch, tmp_path):
    hojas = [_Hoja("Resumen", 1, 1), _Hoja("Notas", 1, 1)]
    llamadas = _xlrd_falso(monkeypatch, hojas)
    with pytest.raises(FormatoNoReconocido, match="ninguna hoja necesaria"):
        modulo.abrir_libro(_xls(tmp_path))
    assert llamadas["libro"].pedidas == []


def test_un_libro_hostil_con_miles_de_hojas_se_rechaza_sin_pedir_ninguna(monkeypatch, tmp_path):
    hojas = [_Hoja(_dia(n), 1, 1) for n in range(5000)]
    llamadas = _xlrd_falso(monkeypatch, hojas)
    with pytest.raises(FormatoNoReconocido, match="5000 hojas") as error:
        modulo.abrir_libro(_xls(tmp_path))
    assert str(modulo.MAX_HOJAS_DECLARADAS) in str(error.value)
    assert llamadas["libro"].pedidas == []


def test_el_inpc_se_lee_por_el_nombre_de_su_hoja(monkeypatch, tmp_path):
    hojas = [_Hoja("Otra", 1, 1), _Hoja("Base Diciembre 2007", 1, 1)]
    llamadas = _xlrd_falso(monkeypatch, hojas)
    libro = modulo.abrir_libro(_xls(tmp_path))
    assert [h.nombre for h in libro.hojas] == ["Base Diciembre 2007"]
    assert llamadas["libro"].pedidas == [1]


# --- MENOR-4 del arbitro: el informe dice QUE hojas se ignoraron ---


def test_el_aviso_de_hojas_ajenas_nombra_hasta_diez_y_cuenta_el_resto(monkeypatch, tmp_path):
    hojas = [_Hoja("01072026", 1, 1)] + [_Hoja(f"Notas{n:02d}", 1, 1) for n in range(13)]
    _xlrd_falso(monkeypatch, hojas)
    libro = modulo.abrir_libro(_xls(tmp_path))
    nombres = ", ".join(f"Notas{n:02d}" for n in range(10))
    assert libro.avisos[0] == f"hojas ajenas no leidas: 13 ({nombres} y 3 mas)"


def test_el_aviso_acota_cada_nombre_y_quita_los_caracteres_de_control(monkeypatch, tmp_path):
    hojas = [_Hoja("01072026", 1, 1), _Hoja("X" * 100, 1, 1), _Hoja("a\x00b\nc", 1, 1)]
    _xlrd_falso(monkeypatch, hojas)
    aviso = modulo.abrir_libro(_xls(tmp_path)).avisos[0]
    assert aviso == f"hojas ajenas no leidas: 2 ({'X' * 40}..., abc)"


def test_los_nombres_de_las_hojas_ajenas_llegan_al_informe_de_la_tasa(monkeypatch, tmp_path):
    from dataclasses import replace
    from datetime import date

    from adapters.bcv.tasa import leer_tasa
    from tests.fixtures.bcv_cuadriculas import hoja_tasa, libro

    _xlrd_falso(monkeypatch, [_Hoja("01072026", 1, 1), _Hoja("Resumen", 1, 1)])
    (aviso,) = modulo.abrir_libro(_xls(tmp_path)).avisos[:1]
    assert aviso == "hojas ajenas no leidas: 1 (Resumen)"
    informe = leer_tasa(
        replace(libro(hoja_tasa("01102026")), avisos=(aviso,)),
        fuente="https://www.bcv.org.ve/x",
        fecha_descarga=date(2026, 10, 15),
        trimestre_por_letra={"c": 3},
    )
    assert aviso in informe.advertencias
    assert aviso in informe.texto()


# --- MENOR-5 del arbitro: tope del TOTAL de celdas entre todas las hojas ---


def test_el_total_de_celdas_declaradas_entre_todas_las_hojas_tiene_tope(monkeypatch, tmp_path):
    assert modulo.MAX_CELDAS_TOTAL == 20_000_000
    monkeypatch.setattr(modulo, "MAX_CELDAS_TOTAL", 10)
    hojas = [_Hoja(_dia(n), 2, 2) for n in range(3)]  # 4 + 4 + 4 = 12 > 10
    _xlrd_falso(monkeypatch, hojas)
    with pytest.raises(FormatoNoReconocido, match="entre todas las hojas") as error:
        modulo.abrir_libro(_xls(tmp_path))
    assert "tasa.xls" in str(error.value) and "10" in str(error.value)
    assert hojas[2].leidas == 0  # la que no cabe ni se recorre


def test_un_total_justo_en_el_tope_se_lee(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo, "MAX_CELDAS_TOTAL", 12)
    _xlrd_falso(monkeypatch, [_Hoja(_dia(n), 2, 2) for n in range(3)])
    assert len(modulo.abrir_libro(_xls(tmp_path)).hojas) == 3
