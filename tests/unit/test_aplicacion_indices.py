"""`aplicacion.indices` (RM-1): UC-17 sin Streamlit, con los avisos que la API y la pantalla clásica
comparten. Oráculos escritos a mano: el mensaje de la falta de `xlrd`, el rango de una serie y las
definiciones que declara quien importa un CSV."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal

import pytest

from adapters.bcv.informe import InformeImportacion, Rechazo, SerieLeida, ValorLeido
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


def _con_rechazos(cuantos: int) -> InformeImportacion:
    rechazos = tuple(Rechazo(f"a.csv:{n}", "valor no numerico " + "x" * 40) for n in range(cuantos))
    return InformeImportacion(
        "a.csv",
        "0" * 64,
        "f",
        date(2026, 10, 11),
        (_serie("S", "2026-01-01"),),
        rechazos,
        ("una advertencia",),
    )


def test_un_informe_corto_se_guarda_tal_cual() -> None:
    informe = _con_rechazos(3)
    assert indices.texto_del_informe(informe) == informe.texto()
    assert indices.texto_del_informe(informe).count("rechazo ") == 3


def test_un_informe_enorme_se_acota_y_cuenta_los_rechazos_omitidos() -> None:
    """BAJO-5: el texto guardado en la base no crece sin limite con los rechazos."""
    informe = _con_rechazos(5000)  # ~ 80 B por linea: unos 400 000 caracteres enteros
    assert len(informe.texto()) > 300_000
    texto = indices.texto_del_informe(informe)
    lineas = texto.split("\n")
    guardados = sum(1 for linea in lineas if linea.startswith("rechazo "))
    assert 0 < guardados < 5000
    assert len(texto) <= indices.MAXIMO_TEXTO_INFORME + 100
    assert lineas[0] == "S: 1 valores" and "una advertencia" in lineas
    assert f"(+{5000 - guardados} rechazos omitidos)" in lineas


def test_confirmar_guarda_el_informe_acotado(monkeypatch) -> None:
    capturado = {}

    class Sesion:
        def commit(self) -> None: ...

        def rollback(self) -> None: ...

    def registrar(_sesion, _definicion, _obs, **datos):
        capturado.update(datos)

    monkeypatch.setattr(indices, "registrar_importacion", registrar)
    indices.confirmar(
        Sesion(),
        _con_rechazos(5000),
        responsable="Admin <admin>",
        definiciones_csv={"S": DefinicionSerie("S", "n", "o", "u", "mensual")},
    )
    assert capturado["informe"] == indices.texto_del_informe(_con_rechazos(5000))
    assert len(capturado["informe"]) <= indices.MAXIMO_TEXTO_INFORME + 100
