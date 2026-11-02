"""Tarea 12 del plan vial: series viales (PPI de asfalto y gasoil) y su mapa a insumos.

Oráculos escritos a mano. Los datos son ficticios (ninguna cifra real)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from aplicacion.riesgo.series import (
    CEMENTO_ASFALTICO_PPI,
    GASOIL_USD,
    SERIES_VIALES,
    MapaSeries,
    historia_mensual,
    importar_serie_csv,
)
from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion

D = Decimal
RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "vial" / "series_ficticias.csv"
HOY = date(2026, 10, 31)
CABECERA = "serie,fecha,valor,provisional,fuente\n"


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'series.db').as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        yield sesion
    motor.dispose()


def _csv(tmp_path: Path, nombre: str, filas: list[str]) -> Path:
    ruta = tmp_path / nombre
    ruta.write_text(CABECERA + "".join(f + "\n" for f in filas), encoding="utf-8")
    return ruta


def _importar(sesion, codigo, ruta):
    return importar_serie_csv(
        sesion, codigo, ruta, fuente="prueba ficticia", responsable="Prueba", hoy=HOY
    )


def _cuantos_valores(sesion) -> int:
    return sesion.scalar(select(func.count()).select_from(models.ValorIndice))


def test_las_series_viales_declaran_unidad_y_periodicidad():
    assert [s.codigo for s in SERIES_VIALES] == ["CEMENTO_ASFALTICO_PPI", "GASOIL_USD"]
    assert (CEMENTO_ASFALTICO_PPI.unidad, CEMENTO_ASFALTICO_PPI.periodicidad) == (
        "indice",
        "mensual",
    )
    assert (GASOIL_USD.unidad, GASOIL_USD.periodicidad) == ("USD/l", "mensual")
    assert "proxy internacional" in CEMENTO_ASFALTICO_PPI.nombre
    assert "WPU05810212" in CEMENTO_ASFALTICO_PPI.nombre
    assert "a cotejar" in GASOIL_USD.nombre


def test_importar_dos_veces_misma_huella_no_duplica(sesion, tmp_path):
    ruta = _csv(
        tmp_path, "g.csv", ["GASOIL_USD,2026-01-01,0.32,no,f", "GASOIL_USD,2026-02-01,0.32,no,f"]
    )
    primera = _importar(sesion, "GASOIL_USD", ruta)
    segunda = _importar(sesion, "GASOIL_USD", ruta)
    assert isinstance(primera, int)
    assert segunda is None
    assert _cuantos_valores(sesion) == 2


def test_unidad_distinta_rechazada(sesion, tmp_path):
    from core.catalog.indices import DefinicionSerie

    registrar_importacion(
        sesion,
        DefinicionSerie("GASOIL_USD", "otra", "x", "Bs/l", "mensual"),
        [Observacion(date(2026, 1, 1), D("1"))],
        archivo="a.csv",
        huella="b" * 64,
        fuente="f",
        fecha_descarga=HOY,
        responsable="r",
        filas_leidas=1,
        filas_rechazadas=0,
    )
    ruta = _csv(tmp_path, "g.csv", ["GASOIL_USD,2026-02-01,0.32,no,f"])
    with pytest.raises(ValueError, match="ya existe con otra unidad o periodicidad"):
        _importar(sesion, "GASOIL_USD", ruta)


def test_historia_por_mes(sesion, tmp_path):
    ruta = _csv(
        tmp_path,
        "p.csv",
        [
            "CEMENTO_ASFALTICO_PPI,2026-01-01,100.5,no,f",
            "CEMENTO_ASFALTICO_PPI,2026-02-01,101.5,no,f",
            "CEMENTO_ASFALTICO_PPI,2026-03-01,103,si,f",
            "CEMENTO_ASFALTICO_PPI,2026-04-01,104,no,f",
            "GASOIL_USD,2026-02-01,0.32,no,f",
        ],
    )
    _importar(sesion, "CEMENTO_ASFALTICO_PPI", ruta)
    _importar(sesion, "GASOIL_USD", ruta)
    historia = historia_mensual(
        sesion, ["CEMENTO_ASFALTICO_PPI", "GASOIL_USD"], date(2026, 2, 1), date(2026, 3, 31)
    )
    assert historia == {
        "CEMENTO_ASFALTICO_PPI": {date(2026, 2, 1): D("101.5"), date(2026, 3, 1): D("103")},
        "GASOIL_USD": {date(2026, 2, 1): D("0.32")},
    }


def test_una_serie_diaria_aporta_su_ultimo_valor_del_mes(sesion):
    registrar_importacion(
        sesion,
        definicion_tasa("venta"),
        [
            Observacion(date(2026, 1, 5), D("40")),
            Observacion(date(2026, 1, 30), D("42")),
            Observacion(date(2026, 2, 2), D("43")),
        ],
        archivo="t.csv",
        huella="c" * 64,
        fuente="f",
        fecha_descarga=HOY,
        responsable="r",
        filas_leidas=3,
        filas_rechazadas=0,
    )
    historia = historia_mensual(sesion, ["BCV-USD-VENTA"], date(2026, 1, 1), date(2026, 2, 28))
    assert historia == {"BCV-USD-VENTA": {date(2026, 1, 1): D("42"), date(2026, 2, 1): D("43")}}


def test_una_revision_posterior_manda_sobre_la_anterior(sesion, tmp_path):
    uno = _csv(tmp_path, "uno.csv", ["GASOIL_USD,2026-01-01,0.32,no,f"])
    dos = _csv(tmp_path, "dos.csv", ["GASOIL_USD,2026-01-01,0.35,no,f"])
    _importar(sesion, "GASOIL_USD", uno)
    _importar(sesion, "GASOIL_USD", dos)
    historia = historia_mensual(sesion, ["GASOIL_USD"], date(2026, 1, 1), date(2026, 1, 31))
    assert historia == {"GASOIL_USD": {date(2026, 1, 1): D("0.35")}}


def test_una_serie_sin_datos_en_el_rango_da_historia_vacia(sesion):
    assert historia_mensual(sesion, ["GASOIL_USD"], date(2026, 1, 1), date(2026, 3, 1)) == {
        "GASOIL_USD": {}
    }


def test_codigo_desconocido_se_rechaza(sesion, tmp_path):
    ruta = _csv(tmp_path, "x.csv", ["ARENA,2026-01-01,1,no,f"])
    with pytest.raises(ValueError, match="ARENA"):
        _importar(sesion, "ARENA", ruta)


def test_el_archivo_sin_la_serie_pedida_se_rechaza(sesion, tmp_path):
    ruta = _csv(tmp_path, "x.csv", ["CEMENTO_ASFALTICO_PPI,2026-01-01,100,no,f"])
    with pytest.raises(ValueError, match="no trae la serie GASOIL_USD"):
        _importar(sesion, "GASOIL_USD", ruta)
    assert _cuantos_valores(sesion) == 0


def test_una_fila_rechazada_no_se_calla(sesion, tmp_path):
    ruta = _csv(
        tmp_path, "x.csv", ["GASOIL_USD,2026-01-01,0.32,no,f", "GASOIL_USD,2026-02-01,0,no,f"]
    )
    with pytest.raises(ValueError, match="x.csv:3"):
        _importar(sesion, "GASOIL_USD", ruta)
    assert _cuantos_valores(sesion) == 0


def test_la_muestra_ficticia_trae_36_meses_por_serie_y_se_declara_ficticia(sesion):
    assert "FICTICIO" in MUESTRA.read_text(encoding="utf-8").splitlines()[1]
    for codigo in ("CEMENTO_ASFALTICO_PPI", "GASOIL_USD"):
        assert isinstance(_importar(sesion, codigo, MUESTRA), int)
    historia = historia_mensual(
        sesion, ["CEMENTO_ASFALTICO_PPI", "GASOIL_USD"], date(2023, 10, 1), date(2026, 9, 30)
    )
    assert len(historia["CEMENTO_ASFALTICO_PPI"]) == 36
    assert len(historia["GASOIL_USD"]) == 36
    assert historia["GASOIL_USD"][date(2023, 10, 1)] == D("0.300")
    assert historia["CEMENTO_ASFALTICO_PPI"][date(2023, 10, 1)] == D("101.200")


def test_el_mapa_es_inmutable_y_se_indexa_por_descripcion():
    mapa = MapaSeries({"Gasoil": "GASOIL_USD"})
    assert mapa.serie_por_insumo["Gasoil"] == "GASOIL_USD"
    with pytest.raises(FrozenInstanceError):
        mapa.serie_por_insumo = {}  # type: ignore[misc]
    with pytest.raises(TypeError):
        mapa.serie_por_insumo["Otro"] = "X"  # type: ignore[index]
