"""`aplicacion.indices` (RM-1): UC-17 sin Streamlit, con los avisos que la API y la pantalla clásica
comparten. Oráculos escritos a mano: el mensaje de la falta de `xlrd`, el rango de una serie y las
definiciones que declara quien importa un CSV."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal

import pytest

from adapters.bcv.informe import InformeImportacion, SerieLeida, ValorLeido
from aplicacion import indices
from core.catalog.indices import DefinicionSerie

FIRMA_OLE2 = bytes.fromhex("D0CF11E0A1B11AE1")
SIN_XLRD = (
    "No se puede leer un archivo .xls: falta el componente xlrd (extra «bcv» de la instalación). "
    "Instálelo, o use el .xlsx o el CSV canónico."
)


def _serie(clave: str, *fechas: str) -> SerieLeida:
    valores = tuple(ValorLeido(date.fromisoformat(f), Decimal("1.5")) for f in fechas)
    return SerieLeida(clave, clave, "", "", "", "", valores)


def _informe(*series: SerieLeida) -> InformeImportacion:
    return InformeImportacion("a.csv", "0" * 64, "f", date(2026, 10, 11), series)


def test_un_xls_sin_xlrd_dice_que_falta_el_componente_y_no_lanza_una_traza(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "xlrd", None)  # como si el extra «bcv» no estuviera
    ruta = tmp_path / "2_1_2c26_smc.xls"
    ruta.write_bytes(FIRMA_OLE2 + b"\x00" * 64)
    with pytest.raises(ValueError) as error:
        indices.leer(
            ruta, "tasa", fuente="https://www.bcv.org.ve/x", fecha_descarga=date(2026, 10, 11)
        )
    assert str(error.value) == SIN_XLRD


def test_un_xls_cuyo_contenido_no_es_ole2_se_rechaza_sin_necesitar_xlrd(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "xlrd", None)
    ruta = tmp_path / "4_5_7.xls"
    ruta.write_bytes(b"PK\x03\x04resto")
    with pytest.raises(ValueError) as error:
        indices.leer(
            ruta, "inpc", fuente="https://www.bcv.org.ve/x", fecha_descarga=date(2026, 10, 11)
        )
    assert str(error.value) == (
        "4_5_7.xls: la extension .xls no coincide con el contenido (es un .xlsx renombrado)"
    )


def test_el_rango_de_una_serie_son_su_primera_y_su_ultima_fecha_o_vacio():
    informe = _informe(_serie("A", "2026-03-01", "2026-01-15", "2026-02-01"), _serie("B"))
    assert indices.resumen_de_series(informe) == [
        {"serie": "A", "valores": 3, "desde": "2026-01-15", "hasta": "2026-03-01"},
        {"serie": "B", "valores": 0, "desde": "", "hasta": ""},
    ]


def test_las_definiciones_del_csv_recortan_y_omiten_las_series_incompletas():
    filas = [
        {
            "serie": "A",
            "nombre": " Indice A ",
            "organismo": " Ente ",
            "unidad": " u ",
            "periodicidad": "mensual",
        },
        {
            "serie": "B",
            "nombre": "Indice B",
            "organismo": "   ",
            "unidad": "u",
            "periodicidad": "mensual",
        },
    ]
    assert indices.definiciones_desde_filas(filas) == {
        "A": DefinicionSerie("A", "Indice A", "Ente", "u", "mensual")
    }


def test_una_periodicidad_ajena_es_el_error_del_nucleo():
    fila = {"serie": "A", "nombre": "n", "organismo": "o", "unidad": "u", "periodicidad": "x"}
    with pytest.raises(ValueError, match="periodicidad 'x'; se espera una de"):
        indices.definiciones_desde_filas([fila])


def test_ui_indices_reexporta_la_capa_de_aplicacion():
    from ui import indices as ui_indices

    for nombre in ("TIPOS", "leer", "confirmar", "filas_del_informe"):
        assert getattr(ui_indices, nombre) is getattr(indices, nombre)
