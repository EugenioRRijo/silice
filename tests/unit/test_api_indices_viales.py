"""Las series viales del riesgo se cargan desde la interfaz: `/v1/indices/series-viales`.

Contrato de `api/rutas/indices.py` (sección «series viales»):

- `GET /v1/indices/series-viales` -> las dos series de `aplicacion.riesgo.series.SERIES_VIALES`
  con su historia ya cargada (fecha ISO y valor exacto como texto de punto decimal; la coma y las
  fechas dd/mm/aaaa las pone el navegador).
- `POST /v1/indices/series-viales/importar` (multipart: serie, archivo .csv, fuente,
  fecha_descarga) -> importa SOLO esa serie del CSV canónico, todo o nada: una fila rechazada
  detiene la importación; el mismo archivo dos veces no escribe nada.

Acceso como `/v1/indices/*` (rol administrador; escribir solo con sesión de una cuenta, la clave de
API recibe 403) y, además, el módulo «Riesgo» encendido (D-V-4: 404 si está apagado).

Oráculos a mano: los valores del CSV de cada prueba; la huella no se recalcula (basta con que dos
envíos del mismo archivo coincidan). Datos ficticios, construidos aquí.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import app
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
PPI = "CEMENTO_ASFALTICO_PPI"
GASOIL = "GASOIL_USD"
FUENTE = "FRED/BLS, serie ficticia de la prueba"
FECHA = "2026-10-31"
ENCABEZADO = "serie,fecha,valor,provisional,fuente\n"
#: Tres meses del PPI (uno provisional) y dos del gasoil, en el mismo archivo.
BUENO = (
    ENCABEZADO
    + f"{PPI},2026-01-01,101.2,no,ficticia\n"
    + f"{PPI},2026-02-01,100.39,si,ficticia\n"
    + f"{PPI},2026-03-01,103,no,ficticia\n"
    + f"{GASOIL},2026-01-01,0.5,no,ficticia\n"
    + f"{GASOIL},2026-02-01,0.5,no,ficticia\n"
).encode()
#: El valor con coma decimal de la fila 3 es una fila rechazada (el CSV canónico exige punto).
CON_FILA_RECHAZADA = (
    ENCABEZADO
    + f"{PPI},2026-01-01,101.2,no,ficticia\n"
    + f"{PPI},2026-02-01,100.39,no,ficticia\n"
    + f'{PPI},2026-03-01,"103,5",no,ficticia\n'
).encode()
MENSAJE_YA = (
    "Ya estaba importado: este archivo ya se cargó antes para esta serie; no se escribió nada."
)


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("series_viales"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _admin():
    return con_cuenta(app, "admin")


def _importar(
    contenido: bytes = BUENO,
    serie: str = PPI,
    nombre: str = "series.csv",
    fuente: str = FUENTE,
    fecha: str = FECHA,
    cuenta=None,
):
    navegador, ficha = cuenta or _admin()
    return navegador.post(
        "/v1/indices/series-viales/importar",
        data={"serie": serie, "fuente": fuente, "fecha_descarga": fecha},
        files={"archivo": (nombre, contenido, "text/csv")},
        headers=protegida(ficha),
    )


def _valores(ruta: Path) -> dict[tuple[str, str], tuple[Decimal, bool]]:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            filas = sesion.execute(
                select(
                    models.SerieIndice.codigo,
                    models.ValorIndice.fecha,
                    models.ValorIndice.valor,
                    models.ValorIndice.provisional,
                ).join(models.SerieIndice, models.SerieIndice.id == models.ValorIndice.serie_id)
            ).all()
    finally:
        motor.dispose()
    return {(c, f.isoformat()): (v, p) for c, f, v, p in filas}


def _responsables(ruta: Path) -> set[str]:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return set(sesion.scalars(select(models.ImportacionIndice.responsable)))
    finally:
        motor.dispose()


# --- acceso ---------------------------------------------------------------------------------


def test_sin_sesion_es_401_y_la_clave_de_api_lee_pero_no_importa() -> None:
    sin = cliente(app)
    assert sin.get("/v1/indices/series-viales").status_code == 401
    clave = {CABECERA: crear_clave_de_prueba()}
    assert sin.get("/v1/indices/series-viales", headers=clave).status_code == 200
    r = sin.post(
        "/v1/indices/series-viales/importar",
        data={"serie": PPI, "fuente": FUENTE, "fecha_descarga": FECHA},
        files={"archivo": ("s.csv", BUENO)},
        headers=clave,
    )
    assert r.status_code == 403, r.text


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_solo_el_administrador_carga_las_series_viales(login: str) -> None:
    cuenta = con_cuenta(app, login)
    leer = cuenta[0].get("/v1/indices/series-viales")
    escribir = _importar(cuenta=cuenta)
    for r in (leer, escribir):
        assert (r.status_code, r.json()) == (403, {"detalle": MENSAJE_PERMISO})


def test_con_el_modulo_de_riesgo_apagado_las_dos_rutas_son_404() -> None:
    navegador, ficha = _admin()
    apagado = navegador.put("/v1/modulos/riesgo", json={"activo": False}, headers=protegida(ficha))
    assert apagado.status_code == 200, apagado.text
    esperado = {"detalle": "El módulo riesgo está apagado en esta instalación."}
    leer = navegador.get("/v1/indices/series-viales")
    escribir = _importar(cuenta=(navegador, ficha))
    for r in (leer, escribir):
        assert (r.status_code, r.json()) == (404, esperado)


# --- lo cargado -----------------------------------------------------------------------------


def test_sin_nada_cargado_trae_las_dos_series_viales_con_su_definicion() -> None:
    navegador, _ = _admin()
    r = navegador.get("/v1/indices/series-viales")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["responsable"] == "Admin de Prueba <admin>"
    assert [s["codigo"] for s in cuerpo["series"]] == [PPI, GASOIL]
    ppi, gasoil = cuerpo["series"]
    assert ppi["unidad"] == "indice" and ppi["organismo"] == "FRED/BLS"
    assert gasoil["unidad"] == "USD/l" and gasoil["periodicidad"] == "mensual"
    for serie in cuerpo["series"]:
        assert (serie["observaciones"], serie["desde"], serie["hasta"], serie["historia"]) == (
            0,
            "",
            "",
            [],
        )
        assert serie["omitidas"] == 0


# --- importar -------------------------------------------------------------------------------


def test_importar_un_csv_bueno_guarda_solo_esa_serie_y_dice_cuanto_y_el_rango(
    _entorno: Path,
) -> None:
    r = _importar()
    assert r.status_code == 200, r.text
    assert r.json() == {
        "serie": PPI,
        "importada": True,
        "observaciones": 3,
        "desde": "2026-01-01",
        "hasta": "2026-03-01",
        "mensaje": "Se importaron 3 valores del 01/01/2026 al 01/03/2026.",
    }
    # El gasoil, que venía en el mismo archivo, no se guardó: se importa por serie.
    assert _valores(_entorno) == {
        (PPI, "2026-01-01"): (D("101.2"), False),
        (PPI, "2026-02-01"): (D("100.39"), True),
        (PPI, "2026-03-01"): (D("103"), False),
    }
    # El responsable es la persona de la sesión, nunca el formulario (RF-82).
    assert _responsables(_entorno) == {"Admin de Prueba <admin>"}


def test_lo_importado_se_lee_despues_con_su_historia_en_orden() -> None:
    cuenta = _admin()
    assert _importar(cuenta=cuenta).status_code == 200
    r = cuenta[0].get("/v1/indices/series-viales")
    ppi, gasoil = r.json()["series"]
    assert (ppi["observaciones"], ppi["desde"], ppi["hasta"], ppi["omitidas"]) == (
        3,
        "2026-01-01",
        "2026-03-01",
        0,
    )
    assert ppi["historia"] == [
        {"fecha": "2026-01-01", "valor": "101.2", "provisional": False},
        {"fecha": "2026-02-01", "valor": "100.39", "provisional": True},
        {"fecha": "2026-03-01", "valor": "103", "provisional": False},
    ]
    assert gasoil["observaciones"] == 0 and gasoil["historia"] == []


def test_importar_dos_veces_el_mismo_archivo_dice_que_ya_estaba_y_no_escribe(
    _entorno: Path,
) -> None:
    cuenta = _admin()
    assert _importar(cuenta=cuenta).json()["importada"] is True
    antes = _valores(_entorno)
    otra = _importar(cuenta=cuenta)
    assert (otra.status_code, otra.json()) == (
        200,
        {
            "serie": PPI,
            "importada": False,
            "observaciones": None,
            "desde": None,
            "hasta": None,
            "mensaje": MENSAJE_YA,
        },
    )
    assert _valores(_entorno) == antes


def test_el_mismo_archivo_sirve_para_la_otra_serie() -> None:
    cuenta = _admin()
    assert _importar(cuenta=cuenta, serie=PPI).json()["importada"] is True
    r = _importar(cuenta=cuenta, serie=GASOIL)
    assert r.status_code == 200, r.text
    assert (r.json()["importada"], r.json()["observaciones"]) == (True, 2)


def test_una_fila_rechazada_detiene_todo_y_dice_cual_y_por_que(_entorno: Path) -> None:
    r = _importar(CON_FILA_RECHAZADA)
    assert r.status_code == 422, r.text
    detalle = r.json()["detalle"]
    assert detalle.startswith("No se importó nada: ")
    assert "series.csv:4" in detalle and "coma" in detalle
    assert set(r.json()) == {"detalle"}
    assert _valores(_entorno) == {}
    assert _responsables(_entorno) == set()


def test_una_serie_que_no_es_vial_se_rechaza_sin_repetir_lo_enviado(_entorno: Path) -> None:
    ajena = "texto-que-no-debe-volver-en-un-422"
    for serie in ("BCV-INPC-GENERAL", ajena):
        r = _importar(serie=serie)
        assert r.status_code == 422, r.text
        assert r.json() == {
            "detalle": "Esa no es una serie vial: elija CEMENTO_ASFALTICO_PPI o GASOIL_USD."
        }
        assert ajena not in r.text
    assert _valores(_entorno) == {}


def test_un_archivo_que_no_trae_la_serie_elegida_es_422(_entorno: Path) -> None:
    solo_ppi = (ENCABEZADO + f"{PPI},2026-01-01,101.2,no,ficticia\n").encode()
    r = _importar(solo_ppi, serie=GASOIL)
    assert r.status_code == 422, r.text
    assert r.json() == {
        "detalle": "No se importó nada: el archivo series.csv no trae la serie GASOIL_USD."
    }
    assert _valores(_entorno) == {}


@pytest.mark.parametrize("nombre", ["series.xlsx", "series.txt", "sin_extension"])
def test_solo_se_acepta_un_csv(nombre: str) -> None:
    r = _importar(nombre=nombre)
    assert (r.status_code, r.json()) == (422, {"detalle": "Solo se acepta un archivo .csv."})


def test_sin_fuente_es_422_con_su_mensaje(_entorno: Path) -> None:
    r = _importar(fuente="   ")
    assert (r.status_code, r.json()) == (
        422,
        {"detalle": "Escriba la fuente: de dónde bajó la serie."},
    )
    assert _valores(_entorno) == {}


def test_un_csv_con_otras_columnas_es_422_con_el_mensaje_del_lector() -> None:
    r = _importar(b"a,b\n1,2\n")
    assert r.status_code == 422
    assert r.json()["detalle"].startswith("No se importó nada: series.csv: las columnas deben ser")


def test_una_fecha_de_descarga_malformada_es_422_sin_eco() -> None:
    malo = "texto-que-no-debe-volver"
    r = _importar(fecha=malo)
    assert r.status_code == 422
    assert malo not in r.text
    assert set(r.json()) == {"detalle"}


def test_la_fecha_de_descarga_anterior_a_los_datos_se_rechaza(_entorno: Path) -> None:
    """El archivo trae datos de marzo de 2026: no pudo bajarse en enero (no hay fechas futuras)."""
    r = _importar(fecha=date(2026, 1, 15).isoformat())
    assert r.status_code == 422, r.text
    assert r.json()["detalle"].startswith("No se importó nada: ")
    assert _valores(_entorno) == {}
