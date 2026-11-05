"""`GET /v1/consulta/{tabla}`: autocompletado con tablas venezolanas (plan vial, Tarea 20).

Acceso `LEER_PROYECTO` como las rutas vecinas de solo lectura (`/v1/buscar/partidas`); el
administrador recibe 403. Tabla desconocida -> 404; `Cache-Control: no-store`.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import manejar_http_exception
from api.proteccion import proteger
from api.rutas import consulta, sesion
from aplicacion.consulta import Sugerencia
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from core import models
from core.catalog import abrir_sesion, crear_motor
from core.models import Insumo
from operacion.base_datos import preparar_base
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)


def _aplicacion() -> FastAPI:
    aplicacion = FastAPI()
    aplicacion.add_exception_handler(HTTPException, manejar_http_exception)
    aplicacion.include_router(sesion.router)
    aplicacion.include_router(consulta.router)
    proteger(aplicacion)
    return aplicacion


APLICACION = _aplicacion()


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("api_consulta"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    copiar_instalacion(_plantilla)
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            s.add(
                Insumo(
                    codigo="MAT-1",
                    tipo="material",
                    descripcion="Cemento gris ficticio",
                    unidad="saco",
                )
            )
            s.commit()
    finally:
        motor.dispose()
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def ana() -> TestClient:
    return con_cuenta(APLICACION, "ana")[0]


def test_carpeta_con_y_sin_mayusculas_ni_acentos_da_lo_mismo(ana: TestClient) -> None:
    a = ana.get("/v1/consulta/partidas_viales", params={"q": "carpeta"})
    b = ana.get("/v1/consulta/partidas_viales", params={"q": "CARPÉTA"})
    assert a.status_code == b.status_code == 200
    assert a.json()["resultados"][0] == b.json()["resultados"][0]
    assert a.json()["resultados"][0]["valor"] == "C-000.000.008"
    assert a.headers.get("cache-control") == "no-store"


def test_cada_sugerencia_trae_su_fuente(ana: TestClient) -> None:
    cuerpo = ana.get("/v1/consulta/insumos", params={"q": "cemento"}).json()
    assert cuerpo["tabla"] == "insumos" and cuerpo["hay_mas"] is False
    assert cuerpo["resultados"] == [
        {
            "valor": "MAT-1",
            "etiqueta": "Cemento gris ficticio (MAT-1, saco)",
            "fuente": "Catálogo de la carpeta de trabajo: material",
        }
    ]


def test_tabla_desconocida_es_404_sin_repetir_lo_enviado(ana: TestClient) -> None:
    r = ana.get("/v1/consulta/no_existe_xyz", params={"q": "algo"})
    assert r.status_code == 404
    assert "no_existe_xyz" not in r.text
    assert r.headers.get("cache-control") == "no-store"


def test_hay_mas_cuando_sobran_coincidencias(ana: TestClient) -> None:
    cuerpo = ana.get("/v1/consulta/partidas_viales", params={"q": "granular", "limite": 1}).json()
    assert len(cuerpo["resultados"]) == 1 and cuerpo["hay_mas"] is True


@pytest.mark.parametrize(
    "params", [{"q": "x" * 81}, {"q": "ab", "limite": 0}, {"q": "ab", "limite": 51}]
)
def test_forma_invalida_es_422(ana: TestClient, params: dict) -> None:
    r = ana.get("/v1/consulta/insumos", params=params)
    assert r.status_code == 422
    assert r.headers.get("cache-control") == "no-store"


def test_menos_de_dos_letras_responde_vacio(ana: TestClient) -> None:
    assert ana.get("/v1/consulta/insumos", params={"q": "c"}).json()["resultados"] == []


def test_el_administrador_recibe_403_y_sin_sesion_401() -> None:
    admin = con_cuenta(APLICACION, "admin")[0]
    r = admin.get("/v1/consulta/insumos", params={"q": "cemento"})
    assert r.status_code == 403 and MENSAJE_PERMISO in r.text
    assert (
        cliente(APLICACION).get("/v1/consulta/insumos", params={"q": "cemento"}).status_code == 401
    )


# --- AC1b: con `para_armar_al`, el precio de la lista para armar a esa fecha ------------------
#
# Dos listas en Bs con precios distintos (julio: 18,00; octubre: 25,50). Componer arma a su fecha:
# el precio que viaja es el de la lista para armar a esa fecha, no el de la vigente hoy. Montos
# como texto decimal con punto; la fecha del precio en ISO. Datos ficticios.


def _sembrar_listas(*, moneda: str = "Bs", declarada: str | None = None) -> None:
    motor = crear_motor(os.environ[dependencias.VARIABLE_BASE])
    try:
        with abrir_sesion(motor) as s:
            if declarada is not None:
                declarar_moneda_de_la_carpeta(
                    s, declarada, responsable="Ana Demo", ahora=datetime(2026, 6, 1, 8, 0)
                )
            cemento = s.scalars(select(Insumo).where(Insumo.codigo == "MAT-1")).one()
            for nombre, fecha, precio in (
                ("Julio ficticia", date(2026, 7, 1), "18.00"),
                ("Octubre ficticia", date(2026, 10, 1), "25.50"),
            ):
                lista = models.ListaPrecios(
                    nombre=nombre, moneda=moneda, fecha_vigencia=fecha, origen=""
                )
                s.add(lista)
                s.flush()
                s.add(
                    models.PrecioInsumo(
                        lista_id=lista.id, insumo_id=cemento.id, precio=Decimal(precio)
                    )
                )
            s.commit()
    finally:
        motor.dispose()


def _cemento(ana: TestClient, **params) -> dict:
    r = ana.get("/v1/consulta/insumos", params={"q": "cemento", **params})
    assert r.status_code == 200, r.text
    assert r.headers.get("cache-control") == "no-store"
    [sugerencia] = r.json()["resultados"]
    return sugerencia


def test_la_misma_moneda_trae_el_precio_de_la_lista_para_armar_con_su_moneda_y_fecha(
    ana: TestClient,
) -> None:
    _sembrar_listas()
    assert _cemento(ana, para_armar_al="2026-08-15") == {
        "valor": "MAT-1",
        "etiqueta": "Cemento gris ficticio (MAT-1, saco)",
        "fuente": "Catálogo de la carpeta de trabajo: material",
        "descripcion": "Cemento gris ficticio",
        "unidad": "saco",
        "precio": "18.00",
        "moneda": "Bs",
        "fecha_precio": "2026-07-01",
    }


def test_otra_moneda_no_trae_precio_y_si_el_aviso(ana: TestClient) -> None:
    _sembrar_listas(moneda="USD", declarada="Bs")
    sugerencia = _cemento(ana, para_armar_al="2026-08-15")
    assert "precio" not in sugerencia
    assert sugerencia["moneda"] == "USD"
    assert sugerencia["fecha_precio"] == "2026-07-01"
    assert sugerencia["aviso_precio"] == "El catálogo lo tiene en USD; escriba el precio en Bs."
    assert (sugerencia["descripcion"], sugerencia["unidad"]) == ("Cemento gris ficticio", "saco")


def test_sin_lista_de_precios_trae_descripcion_y_unidad_y_ningun_precio(ana: TestClient) -> None:
    sugerencia = _cemento(ana, para_armar_al="2026-08-15")
    assert {"descripcion": "Cemento gris ficticio", "unidad": "saco"}.items() <= sugerencia.items()
    assert not {"precio", "moneda", "fecha_precio", "aviso_precio"} & sugerencia.keys()


def test_con_detalle_y_sin_fecha_no_hay_precio(ana: TestClient) -> None:
    _sembrar_listas()
    sugerencia = _cemento(ana, detalle="true")
    assert (sugerencia["descripcion"], sugerencia["unidad"]) == ("Cemento gris ficticio", "saco")
    assert not {"precio", "moneda", "fecha_precio", "aviso_precio"} & sugerencia.keys()


def test_sin_los_parametros_nuevos_la_respuesta_es_la_de_siempre_aunque_haya_listas(
    ana: TestClient,
) -> None:
    _sembrar_listas()
    assert _cemento(ana) == {
        "valor": "MAT-1",
        "etiqueta": "Cemento gris ficticio (MAT-1, saco)",
        "fuente": "Catálogo de la carpeta de trabajo: material",
    }


def test_una_fecha_que_no_es_fecha_es_422_fijo(ana: TestClient) -> None:
    r = ana.get("/v1/consulta/insumos", params={"q": "cemento", "para_armar_al": "ayer<b>"})
    assert r.status_code == 422
    assert "ayer" not in r.text
    assert r.headers.get("cache-control") == "no-store"


def test_el_administrador_sigue_sin_acceso_con_la_fecha() -> None:
    admin = con_cuenta(APLICACION, "admin")[0]
    r = admin.get("/v1/consulta/insumos", params={"q": "cemento", "para_armar_al": "2026-08-15"})
    assert r.status_code == 403


@pytest.mark.parametrize(
    ("guardado", "viaja"), [("1E+2", "100"), ("0E+2", "0"), ("18.00", "18.00")]
)
def test_el_precio_viaja_en_decimal_con_punto_nunca_en_notacion_cientifica(
    ana: TestClient, monkeypatch: pytest.MonkeyPatch, guardado: str, viaja: str
) -> None:
    """`Decimal` puede llegar con exponente desde la base (`Decimal("1E+2")`): `str` lo dejaría en
    «1E+2», que el navegador no lee como cifra. Oráculo a mano: 1E+2 = 100 y 0E+2 = 0."""

    def una(*_args, **_kwargs) -> list[Sugerencia]:
        return [
            Sugerencia(
                valor="MAT-1",
                etiqueta="Cemento gris ficticio (MAT-1, saco)",
                fuente="Catálogo de la carpeta de trabajo: material",
                descripcion="Cemento gris ficticio",
                unidad="saco",
                precio=Decimal(guardado),
                moneda="Bs",
                fecha_precio=date(2026, 7, 1),
            )
        ]

    monkeypatch.setattr(consulta, "buscar", una)
    r = ana.get("/v1/consulta/insumos", params={"q": "cemento", "para_armar_al": "2026-08-15"})
    assert r.status_code == 200
    assert r.json()["resultados"][0]["precio"] == viaja
