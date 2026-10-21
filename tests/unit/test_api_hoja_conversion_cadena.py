"""S5 (convertir la moneda) y S6 (`GET /v1/hoja/cadena`) de la hoja (T10, 3d-2).

Contrato: `docs/bitacora/2026-10-20-hoja-3d2-contrato-rutas.md` (diseno §4.5, §6.3, §9 P33).
Lo comun a S2 a S5 (BEGIN IMMEDIATE, todo o nada, acceso, forma del cuerpo, cambio de caso) esta en
`test_api_hoja_versiones.py`; aqui, lo propio de la conversion y de la lectura de la cadena.

Oraculos a mano (ninguno sale del codigo bajo prueba): OF-001 en USD vale 2 703,86; convertida a Bs
con la tasa del BCV T vale 2 703,86 x T en Bs (a +-0,01 USD al deshacer la tasa: memoria S1,
`s1_conversion.md`, tasa verificada 860,18 Bs/USD del 01/10/2026); sin tasa en los 7 dias
anteriores (S1-R2) no se convierte; el texto de la cadena sana es «Cadena integra: N versiones» y el
de la rota, el de S3 §6.4 (`mensaje_de_cadena`), escrito aqui a mano.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.main import app
from aplicacion import entrega
from core import models
from core.budget.cadena import sellar_historial
from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    plantilla_of001,
)
from tests.fixtures.hoja_versiones_api import (
    base,
    cadena,
    registrar_tasa,
    registros,
    volcado,
)
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)
from ui import hoja as clasica

D = Decimal
CONVERTIR = "/v1/hoja/versiones/convertir"
CADENA = "/v1/hoja/cadena"
HOY = date(2026, 10, 6)
TASA_VENTA = D("860.18")  # BCV venta del 01/10/2026 (memoria s1_conversion.md)
TASA_COMPRA = D("858.00")
FUENTE = "cambio de moneda del contrato"
SIN_FUENTE = "la fuente del cambio es obligatoria: diga por que y con que respaldo"
TOTAL_MEMORIA = D("2703.86")
TOLERANCIA = D("0.01")
BASE = (
    "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro "
    "programa."
)
FALTA_PROYECTO = "El proyecto «Z» no existe en este caso."
FORMA_CADENA = "Indique el proyecto (código o nombre) de hasta 500 caracteres."
ROTA_REGISTRO = (
    "Cadena rota en la versión 002: su registro de cambios no coincide con su huella; alguien "
    "cambió la base fuera del sistema. Revíselo con el administrador antes de entregar un paquete."
)
ROTA_ANEXO = (
    "Cadena rota en la versión 001: uno de sus anexos no coincide con su huella; alguien cambió "
    "la base fuera del sistema. Revíselo con el administrador antes de entregar un paquete."
)
SIN_ESLABON = (
    "Cadena rota en la versión 001: no tiene eslabón; alguien cambió la base fuera del sistema. "
    "Revíselo con el administrador antes de entregar un paquete."
)


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_conversion_cadena")
    casos = {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
    }
    con_tasa = Path(shutil.copyfile(casos["of001"], carpeta / "con_tasa.db"))
    registrar_tasa(con_tasa, date(2026, 10, 5), str(TASA_VENTA))
    registrar_tasa(con_tasa, date(2026, 10, 5), str(TASA_COMPRA), lado="compra", huella="e" * 64)
    casos["con_tasa"] = con_tasa
    dos = Path(shutil.copyfile(casos["of001"], carpeta / "dos.db"))
    motor = crear_motor(f"sqlite:///{dos.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            entrega.con_anexos_de_cadena(sesion)
            catalogo = Catalogo(sesion)
            abierta = clasica.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
            parametros = replace(abierta.borrador.parametros, administracion=D("0.20"))
            clasica.guardar_version(
                sesion,
                catalogo,
                abierta,
                replace(abierta.borrador, parametros=parametros),
                fuente="criterio del residente, acta 12",
                responsable="Ing. Prueba",
                ahora=datetime(2026, 10, 5, 16, 30),
            )
    finally:
        motor.dispose()
    casos["dos"] = dos
    return casos


@pytest.fixture(autouse=True)
def _entorno(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    monkeypatch.setattr("api.rutas.hoja._hoy", lambda: HOY)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["of001"], ruta)
    preparar_base(ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _poner(origen: Path) -> Path:
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    shutil.copyfile(origen, ruta)
    preparar_base(ruta)  # migrada ya: el volcado de «antes» es el de despues de abrir
    return ruta


def _ana() -> tuple[TestClient, str]:
    return con_cuenta(app, "ana")


def _convertir(navegador, ficha, **cambios):
    cuerpo = {
        "proyecto": NOMBRE_OF001,
        "version": "001",
        "moneda": "Bs",
        "lado": "venta",
        "fuente": FUENTE,
        **cambios,
    }
    return navegador.post(CONVERTIR, json=cuerpo, headers=protegida(ficha))


def _total_de(navegador, ficha, version: str) -> str:
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": version},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["resumen"]["total"]["exacto"]


def _versiones(navegador) -> dict:
    respuesta = navegador.get("/v1/hoja/versiones", params={"proyecto": NOMBRE_OF001})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# --- S5 / 3d-B13 / P33: convertir ---


def test_convertir_a_bs_crea_la_002_con_la_tasa_de_venta_y_el_total_de_la_memoria_por_la_tasa(
    _casos,
) -> None:
    ruta = _poner(_casos["con_tasa"])
    navegador, ficha = _ana()
    assert _versiones(navegador)["moneda"] == "USD"
    respuesta = _convertir(navegador, ficha)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "codigo": "002",
        "proyecto": NOMBRE_OF001,
        "mensaje": "Se guardó la versión 002, convertida a Bs.",
    }
    # el registro: objeto moneda, de USD a Bs, a nombre de la sesion (la fuente es la de la tasa)
    (registro,) = registros(ruta, NOMBRE_OF001, "002")
    assert registro[:5] == ("moneda", NOMBRE_OF001, "moneda", "USD", "Bs")
    assert registro[6] == "Ana <ana>" and registro[5] != ""
    with base(ruta) as sesion:
        fila = sesion.execute(
            select(
                models.MonedaProyecto.moneda,
                models.MonedaProyecto.responsable,
                models.MonedaProyecto.fuente,
            ).order_by(models.MonedaProyecto.id.desc())
        ).first()
    assert tuple(fila) == ("Bs", "Ana <ana>", FUENTE)
    estado = cadena(ruta, NOMBRE_OF001)  # antes de abrir nada: abrir tambien escribe
    assert estado.integra, estado.mensaje
    versiones = _versiones(navegador)
    assert versiones["moneda"] == "Bs" and versiones["por_omision"] == "002"
    assert [
        (v["codigo"], v["motivo"], v["origen"], v["vigente"]) for v in versiones["versiones"]
    ] == [
        ("001", "", "", False),
        ("002", "conversion", "001", True),
    ]
    # P33: el total en Bs / la tasa vuelve al de la memoria (a +-0,01 USD)
    total_bs = D(_total_de(navegador, ficha, "002"))
    assert abs(total_bs / TASA_VENTA - TOTAL_MEMORIA) <= TOLERANCIA
    assert _total_de(navegador, ficha, "001") != _total_de(
        navegador, ficha, "002"
    )  # la 001, en USD


def test_el_lado_compra_usa_la_tasa_de_compra(_casos) -> None:
    ruta = _poner(_casos["con_tasa"])
    navegador, ficha = _ana()
    assert _convertir(navegador, ficha, lado="compra").status_code == 200
    assert cadena(ruta, NOMBRE_OF001).integra
    total_bs = D(_total_de(navegador, ficha, "002"))
    assert abs(total_bs / TASA_COMPRA - TOTAL_MEMORIA) <= TOLERANCIA


def test_la_tasa_de_hace_7_dias_sirve_y_la_de_hace_8_no_s1_r2(
    _casos, monkeypatch: pytest.MonkeyPatch
) -> None:
    ruta = _poner(_casos["con_tasa"])  # la tasa es del 05/10/2026
    navegador, ficha = _ana()
    antes = volcado(ruta)
    monkeypatch.setattr("api.rutas.hoja._hoy", lambda: date(2026, 10, 13))  # 8 dias despues
    fuera = _convertir(navegador, ficha)
    assert fuera.status_code == 422
    assert fuera.json() == {
        "detalle": "No se convirtio nada: la tasa venta mas reciente es del 05/10/2026, 8 dias "
        "antes del 13/10/2026: con mas de 7 dias naturales sin tasa no se convierte (S1-R2)"
    }
    assert volcado(ruta) == antes
    monkeypatch.setattr("api.rutas.hoja._hoy", lambda: date(2026, 10, 12))  # 7 dias despues
    dentro = _convertir(navegador, ficha)
    assert dentro.status_code == 200 and dentro.json()["codigo"] == "002"


def test_sin_ninguna_tasa_no_se_convierte_nada_y_lo_dice(_entorno) -> None:
    navegador, ficha = _ana()  # OF-001 sin tasa importada
    antes = volcado(_entorno)
    respuesta = _convertir(navegador, ficha)
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": "No se convirtio nada: no hay tasa venta del BCV importada al 06/10/2026 o "
        "antes: importe el archivo trimestral (UC-17)"
    }
    assert respuesta.headers["cache-control"] == "no-store"
    assert volcado(_entorno) == antes


def test_el_lado_se_respeta_sin_serie_de_compra_no_se_convierte(_casos) -> None:
    ruta = _poner(_casos["of001"])
    registrar_tasa(ruta, date(2026, 10, 5), str(TASA_VENTA))  # solo venta
    navegador, ficha = _ana()
    antes = volcado(ruta)
    respuesta = _convertir(navegador, ficha, lado="compra")
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"] == (
        "No se convirtio nada: no hay tasa compra del BCV importada al 06/10/2026 o antes: "
        "importe el archivo trimestral (UC-17)"
    )
    assert volcado(ruta) == antes
    assert _convertir(navegador, ficha, lado="venta").status_code == 200


def test_los_datos_de_una_conversion_invalida_llevan_el_prefijo_de_la_clasica(_casos) -> None:
    ruta = _poner(_casos["con_tasa"])
    navegador, ficha = _ana()
    antes = volcado(ruta)
    casos = [
        ({"moneda": "USD"}, "No se convirtio nada: la version 001 ya esta en USD"),
        ({"moneda": "EUR"}, "No se convirtio nada: moneda 'EUR'; se espera Bs o USD (UC-17 4b)"),
        ({"fuente": ""}, f"No se convirtio nada: {SIN_FUENTE}"),
        ({"fuente": "   "}, f"No se convirtio nada: {SIN_FUENTE}"),
    ]
    fallos = []
    for cambios, texto in casos:
        respuesta = _convertir(navegador, ficha, **cambios)
        if (respuesta.status_code, respuesta.json()) != (422, {"detalle": texto}):
            fallos.append((cambios, respuesta.status_code, respuesta.text))
    assert fallos == []
    assert volcado(ruta) == antes
    # proyecto o version inexistente: 404 y antes que el dato
    assert _convertir(navegador, ficha, proyecto="Z", moneda="EUR").status_code == 404
    assert _convertir(navegador, ficha, version="009", moneda="EUR").status_code == 404
    assert volcado(ruta) == antes


def test_convertir_una_version_que_ya_esta_en_bs_a_bs_se_rechaza(_casos) -> None:
    ruta = _poner(_casos["con_tasa"])
    navegador, ficha = _ana()
    assert _convertir(navegador, ficha).json()["codigo"] == "002"
    antes = volcado(ruta)
    otra = _convertir(navegador, ficha, version="002")
    assert otra.status_code == 422
    assert otra.json() == {"detalle": "No se convirtio nada: la version 002 ya esta en Bs"}
    assert volcado(ruta) == antes


# --- S6 / 3d-B15: la cadena ---


def _cadena(navegador, proyecto=NOMBRE_OF001):
    return navegador.get(CADENA, params={"proyecto": proyecto})


def test_la_cadena_sana_esta_integra_y_lo_dice(_entorno) -> None:
    navegador, _ = _ana()
    respuesta = _cadena(navegador)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "integra": True,
        "mensaje": "Cadena íntegra: 1 versiones",
        "declaracion": None,
    }


def test_la_cadena_sigue_integra_tras_restaurar_cotizar_y_convertir(_casos) -> None:
    ruta = _poner(_casos["con_tasa"])
    navegador, ficha = _ana()
    cabeceras = protegida(ficha)
    cuerpo = {"proyecto": NOMBRE_OF001, "version": "001"}
    assert (
        navegador.post(
            "/v1/hoja/versiones/restaurar", json={**cuerpo, "fuente": "x"}, headers=cabeceras
        ).json()["codigo"]
        == "002"
    )
    assert (
        navegador.post(
            "/v1/hoja/versiones/cotizar",
            json={
                **cuerpo,
                "insumo": "EQU-001",
                "precio": "99.5",
                "proveedor": "Ferreteria Demo, C.A.",
                "numero": "C-1",
                "fecha": "2026-10-05",
            },
            headers=cabeceras,
        ).json()["codigo"]
        == "003"
    )
    assert _convertir(navegador, ficha, version="003").json()["codigo"] == "004"
    assert _cadena(navegador).json() == {
        "integra": True,
        "mensaje": "Cadena íntegra: 4 versiones",
        "declaracion": None,
    }
    assert cadena(ruta, NOMBRE_OF001).integra


def test_alterar_a_mano_el_registro_de_cambios_rompe_la_cadena_en_esa_version(_casos) -> None:
    ruta = _poner(_casos["dos"])
    navegador, _ = _ana()
    assert _cadena(navegador).json()["integra"] is True
    with closing(sqlite3.connect(ruta.as_posix())) as bd:
        bd.execute("UPDATE registro_cambio SET valor_nuevo = '0.99'")
        bd.commit()
    respuesta = _cadena(navegador)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"integra": False, "mensaje": ROTA_REGISTRO, "declaracion": None}


def test_alterar_a_mano_una_celda_del_espacio_rompe_el_anexo(_entorno) -> None:
    navegador, _ = _ana()
    assert _cadena(navegador).json()["integra"] is True
    with closing(sqlite3.connect(_entorno.as_posix())) as bd:
        bd.execute("UPDATE esp_ambientes SET alto = '9.9' WHERE id = 'BAN-01'")
        bd.commit()
    respuesta = _cadena(navegador)
    assert respuesta.json() == {"integra": False, "mensaje": ROTA_ANEXO, "declaracion": None}


def test_las_versiones_selladas_despues_se_declaran_retroactivas(_casos) -> None:
    ruta = _poner(_casos["dos"])
    with closing(sqlite3.connect(ruta.as_posix())) as bd:
        bd.execute("DELETE FROM eslabon_version")  # lo que habia antes de que existiera la cadena
        bd.commit()
    navegador, _ = _ana()
    sin = _cadena(navegador).json()
    assert sin == {"integra": False, "mensaje": SIN_ESLABON, "declaracion": None}
    with base(ruta) as sesion:
        entrega.con_anexos_de_cadena(sesion)
        sellar_historial(
            sesion,
            "Plantilla <plantilla>",
            anexos_de=entrega.anexos_de_cadena,
            ahora=datetime(2026, 10, 20, 9, 0),
        )
        sesion.commit()
    assert _cadena(navegador).json() == {
        "integra": True,
        "mensaje": "Cadena íntegra: 2 versiones",
        "declaracion": "Versiones 001 a 002 selladas el 2026-10-20: prueban que no cambiaron "
        "desde esa fecha; antes no hay garantía.",
    }


def test_un_proyecto_sin_versiones_tiene_la_cadena_vacia_integra(_entorno) -> None:
    from core.budget import crear_proyecto

    with base(_entorno) as sesion:
        crear_proyecto(sesion, "Proyecto nuevo")
        sesion.commit()
    navegador, _ = _ana()
    assert _cadena(navegador, "Proyecto nuevo").json() == {
        "integra": True,
        "mensaje": "Cadena íntegra: 0 versiones",
        "declaracion": None,
    }


def test_la_cadena_acepta_el_codigo_del_proyecto_y_dice_404_si_no_existe(_entorno) -> None:
    navegador, _ = _ana()
    codigo = next(
        p["codigo"] for p in navegador.get("/v1/proyectos").json() if p["nombre"] == NOMBRE_OF001
    )
    assert _cadena(navegador, codigo).json()["integra"] is True
    falta = _cadena(navegador, "Z")
    assert falta.status_code == 404 and falta.json() == {"detalle": FALTA_PROYECTO}
    assert falta.headers["cache-control"] == "no-store"


def test_la_cadena_solo_lee_y_la_clave_de_api_tambien_puede(_entorno) -> None:
    navegador, _ = _ana()
    assert _cadena(navegador).status_code == 200  # la primera lectura adopta el caso
    antes = volcado(_entorno)
    respuesta = cliente(app).get(
        CADENA,
        params={"proyecto": NOMBRE_OF001},
        headers={CABECERA: crear_clave_de_prueba()},
    )
    assert respuesta.status_code == 200 and respuesta.json()["integra"] is True
    assert respuesta.headers["cache-control"] == "no-store"
    assert volcado(_entorno) == antes


def test_la_cadena_sin_sesion_es_401_y_rita_o_tomas_no_pasan() -> None:
    sin = cliente(app).get(CADENA, params={"proyecto": "P"})
    assert sin.status_code == 401 and sin.headers["cache-control"] == "no-store"
    rita, _ = con_cuenta(app, "rita")
    respuesta = rita.get(CADENA, params={"proyecto": "P"})
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_PERMISO}
    tomas, _ = con_cuenta(app, "tomas")
    assert tomas.get(CADENA, params={"proyecto": "P"}).status_code == 403


def test_la_cadena_sin_proyecto_o_con_uno_enorme_es_422_fijo_sin_eco() -> None:
    navegador, _ = _ana()
    for params in ({}, {"proyecto": ""}, {"proyecto": "p" * 501}):
        respuesta = navegador.get(CADENA, params=params)
        assert respuesta.status_code == 422 and respuesta.json() == {"detalle": FORMA_CADENA}
        assert respuesta.headers["cache-control"] == "no-store"
        assert "ppp" not in respuesta.text


def test_un_error_de_base_al_verificar_la_cadena_es_503_fijo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    navegador, _ = _ana()

    def roto(*_args, **_kwargs):
        raise OperationalError(
            "SELECT * FROM eslabon_version",
            {},
            sqlite3.OperationalError("unable to open database file C:/datos/privados/apu.db"),
        )

    monkeypatch.setattr(entrega.cadena, "verificar_cadena", roto)
    respuesta = _cadena(navegador)
    assert respuesta.status_code == 503 and respuesta.json() == {"detalle": BASE}
    assert respuesta.headers["cache-control"] == "no-store"
    for prohibido in ("sqlite", "SELECT", "privados", "apu.db"):
        assert prohibido not in respuesta.text
