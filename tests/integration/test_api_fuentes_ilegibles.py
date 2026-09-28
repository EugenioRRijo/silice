"""UC-01, flujo 2a (INV-089) por HTTP: `POST /computos/{dominio}` da 422 ante una fuente ilegible.

`api/main.py` traduce `ValueError` a 422 con el mensaje en `detalle`. Antes de C5 una fuente
ilegible no llegaba a esa traduccion: el IFC corrupto lanzaba `ifcopenshell.Error` (500), la celda
mal formada `decimal.InvalidOperation` (500) y la muestra de otro dominio un `KeyError`, que el
manejador de `LookupError` respondia como 404 («recurso no encontrado»). Cada caso sube una fuente
ilegible real y comprueba el 422 y que el `detalle` nombra el archivo y, si la hay, la fila.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MUESTRAS = RAIZ / "data" / "samples"


def _subir(cliente, dominio: str, nombre: str, contenido: bytes, tipo: str = "text/csv"):
    return cliente.post(f"/computos/{dominio}", files={"archivo": (nombre, contenido, tipo)})


def test_un_ifc_corrupto_responde_422_con_el_archivo(cliente):
    pytest.importorskip("ifcopenshell")

    r = _subir(cliente, "civil", "modelo_danado.ifc", b"\x00\xff no es STEP", "application/x-step")

    assert r.status_code == 422
    assert "modelo_danado.ifc" in r.json()["detalle"]


def test_una_celda_industrial_mal_formada_responde_422_con_archivo_y_fila(cliente):
    muestra = (MUESTRAS / "industrial" / "activos_planta.csv").read_text(encoding="utf-8")
    # IN-001 declara frecuencia_anual = 4 (data/samples/industrial/activos_planta.csv).
    assert "IN-001,Bomba centrifuga de agua potable,MNT-BOM-CEN,intervencion,4," in muestra
    alterada = muestra.replace(
        "IN-001,Bomba centrifuga de agua potable,MNT-BOM-CEN,intervencion,4,",
        "IN-001,Bomba centrifuga de agua potable,MNT-BOM-CEN,intervencion,cuatro,",
    )

    r = _subir(cliente, "industrial", "activos.csv", alterada.encode("utf-8"))

    assert r.status_code == 422
    detalle = r.json()["detalle"]
    assert "activos.csv" in detalle
    assert "IN-001" in detalle
    assert "frecuencia_anual" in detalle


def test_la_muestra_de_telecom_en_sistemas_responde_422_y_no_404(cliente):
    contenido = (MUESTRAS / "telecom" / "topologia_arenaza.csv").read_bytes()

    r = _subir(cliente, "sistemas", "topologia_arenaza.csv", contenido)

    assert r.status_code == 422
    detalle = r.json()["detalle"]
    assert "topologia_arenaza.csv" in detalle
    assert "sistemas" in detalle


def test_un_binario_en_telecom_responde_422_con_el_archivo(cliente):
    r = _subir(cliente, "telecom", "red.csv", b"%PDF-1.7\r\n%\xb5\xb5\xb5\xb5\r\n\xff\xfe")

    assert r.status_code == 422
    assert "red.csv" in r.json()["detalle"]


def _sin_rutas(detalle: str) -> bool:
    """El `detalle` nombra el archivo, no la ruta del directorio temporal del servidor (T-4)."""
    return "/" not in detalle and "\\" not in detalle


def test_la_muestra_de_telecom_en_civil_responde_422_sin_la_ruta_del_servidor(cliente):
    """Civil tambien lee `id` y `tipo`, que la topologia de telecom trae; antes la rechazaba por
    «tipo de fila no reconocido en WindowsPath('.../tmpXXXX/topologia_arenaza.csv')»."""
    from tests.fixtures.computo_civil import CODIGOS

    contenido = (MUESTRAS / "telecom" / "topologia_arenaza.csv").read_bytes()

    r = cliente.post(
        "/computos/civil",
        files={"archivo": ("topologia_arenaza.csv", contenido, "text/csv")},
        data={"codigos": json.dumps(CODIGOS)},
    )

    assert r.status_code == 422
    detalle = r.json()["detalle"]
    assert "topologia_arenaza.csv" in detalle
    assert "no es una fuente del dominio civil" in detalle
    assert _sin_rutas(detalle), detalle


def test_un_step_de_esquema_no_soportado_responde_422_sin_la_ruta_del_servidor(cliente):
    pytest.importorskip("ifcopenshell")
    muestra = (MUESTRAS / "tanquilla.ifc").read_bytes()
    assert b"FILE_SCHEMA(('IFC4'))" in muestra
    contenido = muestra.replace(b"FILE_SCHEMA(('IFC4'))", b"FILE_SCHEMA(('IFC9'))")

    r = _subir(cliente, "civil", "modelo_ifc9.ifc", contenido, "application/x-step")

    assert r.status_code == 422
    detalle = r.json()["detalle"]
    assert "modelo_ifc9.ifc" in detalle
    assert "esquema" in detalle
    assert _sin_rutas(detalle), detalle
