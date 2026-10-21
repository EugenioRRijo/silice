"""S2 a S5 `POST /v1/hoja/versiones/{restaurar,cotizar,retirar-cotizacion,convertir}` (T10, 3d-2).

Contrato: `docs/bitacora/2026-10-20-hoja-3d2-contrato-rutas.md` (diseno §4.5, §6.3 fila 3d-2 y §9
P24, P31 a P33, P35). Las cuatro crean una version nueva desde una GUARDADA (no usan borrador) y
son las rutas de la hoja que mas se parecen a S1: una sola transaccion que empieza con
`BEGIN IMMEDIATE`, la sesion envuelta en `con_anexos_de_cadena` (sin eso la cadena queda rota),
todo o nada, el responsable es siempre la persona de la sesion.

Oraculos a mano (ninguno sale del codigo bajo prueba): OF-001 vale 2 703,86 (memoria `of001.md`);
la historia de la aceptacion SF 001 / 002 (edicion) / 003 (restauracion) de
`test_aceptacion_sf.py:378-383`; el registro de una restauracion es (version, <restaurada>,
restauracion, <vigente de antes>, <nueva>); el de una cotizacion (precio, <insumo>, cotizacion,
<antes>, <despues>); la 002 con administracion 0,20 vale 2 137,44 x 1,20 x 1,10 = 2 821,4208.
"Nada escrito" se comprueba con el volcado completo de la base antes y despues; las versiones sembradas
las guarda la clasica (`ui.hoja`), no las rutas que se prueban.
"""

from __future__ import annotations

import json
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
from sqlalchemy import event, select
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.main import app
from aplicacion import entrega
from aplicacion import hoja as copia
from core import models
from core.budget.actualizacion import descartar_version
from core.catalog import (
    Catalogo,
    CatalogoIncompleto,
    abrir_sesion,
    abrir_sesion_de_escritura,
    crear_motor,
)
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import permisos
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    plantilla_of001,
    plantilla_ti001,
)
from tests.fixtures.hoja_versiones_api import (
    a_la_vez,
    base,
    cadena,
    registrar_tasa,
    registros,
    sin_float,
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
SOLO_CUENTA = "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."
BASE = (
    "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro "
    "programa."
)
EXCEDE = "El cuerpo de la peticion excede el maximo de 20 MiB."
CENTINELA = "VALOR-CENTINELA"
ORIGEN = "http://127.0.0.1:8000"
MIB = 1024 * 1024
HOY = date(2026, 10, 6)
AHORA = datetime(2026, 10, 5, 16, 30, 0)
FUENTE = "acta de revision 7: se vuelve a la medida original"
MOTIVO = "el proveedor retiro la oferta"
PROVEEDOR = "Ferreteria Demo, C.A."
SIN_FUENTE = "la fuente del cambio es obligatoria: diga por que y con que respaldo"
TOLERANCIA = D("0.01")
TOTAL_MEMORIA = D("2703.86")  # OF-001 (memoria of001.md)
TOTAL_TI001 = D("50503.27")  # TI-001 (test_hoja_versiones.py: 50 503,27 USD)

RESTAURAR = "/v1/hoja/versiones/restaurar"
COTIZAR = "/v1/hoja/versiones/cotizar"
RETIRAR = "/v1/hoja/versiones/retirar-cotizacion"
CONVERTIR = "/v1/hoja/versiones/convertir"

FORMA_RESTAURAR = (
    "La restauración no tiene la forma esperada: envíe proyecto, version y la fuente como texto "
    "de hasta 300 caracteres."
)
FORMA_COTIZAR = (
    "La cotización no tiene la forma esperada: envíe proyecto, version, insumo, precio (texto), "
    "proveedor, numero, fecha (AAAA-MM-DD) y, si quiere, la evidencia; cada texto con su tope."
)
FORMA_RETIRAR = (
    "El retiro no tiene la forma esperada: envíe proyecto, version, insumo (código) y el motivo "
    "como texto de hasta 300 caracteres."
)
FORMA_CONVERTIR = (
    "La conversión no tiene la forma esperada: envíe proyecto, version, moneda, lado (venta o "
    "compra) y la fuente como texto de hasta 300 caracteres."
)

#: Para cada operacion: la ruta, un cuerpo valido SOBRE LA 002 de `completa`, la forma fija de su 422
#: y la funcion del nucleo (en `aplicacion.hoja`) que escribe la version.
CUERPOS = {
    "restaurar": (
        RESTAURAR,
        {"proyecto": NOMBRE_OF001, "version": "002", "fuente": FUENTE},
        FORMA_RESTAURAR,
        "restaurar_version",
    ),
    "cotizar": (
        COTIZAR,
        {
            "proyecto": NOMBRE_OF001,
            "version": "002",
            "insumo": "EQU-001",
            "precio": "999.5",
            "proveedor": PROVEEDOR,
            "numero": "COT-002",
            "fecha": "2026-10-05",
        },
        FORMA_COTIZAR,
        "cotizar_insumo",
    ),
    "retirar": (
        RETIRAR,
        {"proyecto": NOMBRE_OF001, "version": "002", "insumo": "EQU-001", "motivo": MOTIVO},
        FORMA_RETIRAR,
        "_retirar_cotizacion",
    ),
    "convertir": (
        CONVERTIR,
        {
            "proyecto": NOMBRE_OF001,
            "version": "002",
            "moneda": "Bs",
            "lado": "venta",
            "fuente": "cambio de moneda del contrato",
        },
        FORMA_CONVERTIR,
        "convertir_version",
    ),
}
OPERACIONES = list(CUERPOS)


# --- los casos de la prueba ---


def _sembrar(destino: Path, origen: Path, accion) -> Path:
    """Una copia de `origen` a la que la CLASICA le hace `accion(sesion, catalogo)`."""
    shutil.copyfile(origen, destino)
    motor = crear_motor(f"sqlite:///{destino.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            entrega.con_anexos_de_cadena(sesion)
            accion(sesion, Catalogo(sesion))
    finally:
        motor.dispose()
    return destino


def _con_002_de_administracion(sesion, catalogo) -> None:
    abierta = clasica.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
    parametros = replace(abierta.borrador.parametros, administracion=D("0.20"))
    clasica.guardar_version(
        sesion,
        catalogo,
        abierta,
        replace(abierta.borrador, parametros=parametros),
        fuente="criterio del residente, acta 12",
        responsable="Ing. Prueba",
        ahora=AHORA,
    )


def _con_002_cotizada(sesion, catalogo) -> None:
    clasica.cotizar(
        sesion,
        catalogo,
        NOMBRE_OF001,
        "001",
        insumo="EQU-001",
        precio=D("15.00"),
        proveedor=PROVEEDOR,
        numero="COT-001",
        fecha=date(2026, 10, 5),
        responsable="Ing. Prueba",
        fuente="cotizacion de prueba",
    )


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_versiones")
    casos = {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
        "ti001": plantilla_ti001(carpeta / "ti001.db"),
    }
    casos["dos"] = _sembrar(carpeta / "of001_dos.db", casos["of001"], _con_002_de_administracion)
    casos["completa"] = _sembrar(carpeta / "completa.db", casos["of001"], _con_002_cotizada)
    registrar_tasa(casos["completa"], date(2026, 10, 5), "860.18")  # la de «hoy» (HOY - 1 dia)
    return casos


@pytest.fixture(autouse=True)
def _entorno(
    _casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    """La instalacion con cuentas y OF-001 (version 001) como caso por defecto, en la carpeta de
    datos temporal de la prueba: nada toca `data/`. El «hoy» del servidor, fijo."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    monkeypatch.setattr("api.rutas.hoja._hoy", lambda: HOY)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["of001"], ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _poner(origen: Path) -> Path:
    """Cambia el caso por defecto por una copia de `origen` (cierra el motor del anterior)."""
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    shutil.copyfile(origen, ruta)
    return ruta


def _ana() -> tuple[TestClient, str]:
    return con_cuenta(app, "ana")


def _hacer(navegador, ficha, operacion: str, **cambios):
    ruta, cuerpo, _forma, _nucleo = CUERPOS[operacion]
    return navegador.post(ruta, json={**cuerpo, **cambios}, headers=protegida(ficha))


def _restaurar(navegador, ficha, version="001", fuente=FUENTE, proyecto=NOMBRE_OF001, **extra):
    cuerpo = {"proyecto": proyecto, "version": version, "fuente": fuente, **extra}
    return navegador.post(RESTAURAR, json=cuerpo, headers=protegida(ficha))


def _cotizar(navegador, ficha, **cambios):
    cuerpo = {
        "proyecto": NOMBRE_OF001,
        "version": "001",
        "insumo": "EQU-001",
        "precio": "999.5",
        "proveedor": PROVEEDOR,
        "numero": "COT-001",
        "fecha": "2026-10-05",
        **cambios,
    }
    return navegador.post(COTIZAR, json=cuerpo, headers=protegida(ficha))


def _retirar(navegador, ficha, **cambios):
    cuerpo = {
        "proyecto": NOMBRE_OF001,
        "version": "002",
        "insumo": "EQU-001",
        "motivo": MOTIVO,
        **cambios,
    }
    return navegador.post(RETIRAR, json=cuerpo, headers=protegida(ficha))


def _versiones(navegador, proyecto=NOMBRE_OF001) -> dict:
    respuesta = navegador.get("/v1/hoja/versiones", params={"proyecto": proyecto})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _codigos(navegador, proyecto=NOMBRE_OF001) -> list[str]:
    return [v["codigo"] for v in _versiones(navegador, proyecto)["versiones"]]


def _precios(navegador, version: str, proyecto=NOMBRE_OF001) -> list[dict]:
    respuesta = navegador.get(
        "/v1/hoja/precios", params={"proyecto": proyecto, "version": version}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["filas"]


def _fila(filas: list[dict], codigo: str) -> dict:
    return next(f for f in filas if f["codigo"] == codigo)


def _resumen_de(navegador, ficha, version: str, proyecto=NOMBRE_OF001) -> dict:
    """Abre la version como borrador (R2) y devuelve su resumen: lo que ve la pantalla."""
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": proyecto, "version": version},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["resumen"]


def _cerca(texto: str, esperado: Decimal) -> bool:
    return abs(D(texto) - esperado) <= TOLERANCIA


# --- S2 / 3d-B11 / P31: restaurar ---


def test_restaurar_la_001_crea_la_003_copia_de_la_001_y_la_deja_vigente(_casos) -> None:
    ruta = _poner(_casos["dos"])
    antes = cadena(ruta, NOMBRE_OF001)
    assert antes.integra, antes.mensaje  # la siembra de la clasica deja una cadena sana
    navegador, ficha = _ana()
    assert _codigos(navegador) == ["001", "002"]

    respuesta = _restaurar(navegador, ficha)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "codigo": "003",
        "proyecto": NOMBRE_OF001,
        "mensaje": "La versión 001 se restauró como la versión 003 (la vigente).",
    }
    # el registro por celda: la restaurada, la vigente de antes, la nueva, la fuente y la persona
    assert registros(ruta, NOMBRE_OF001, "003") == [
        ("version", "001", "restauracion", "002", "003", FUENTE, "Ana <ana>")
    ]
    # la historia de la aceptacion SF: nada se borra y la nueva es la vigente
    versiones = _versiones(navegador)
    assert [(v["codigo"], v["motivo"], v["origen"], v["vigente"]) for v in versiones["versiones"]] == [
        ("001", "", "", False),
        ("002", "edicion", "001", False),
        ("003", "restauracion", "001", True),
    ]
    assert versiones["por_omision"] == "003"
    despues = cadena(ruta, NOMBRE_OF001)
    assert despues.integra, despues.mensaje
    # la 003 es igual a la 001: el total de la memoria, sin cambios pendientes (y no el de la 002)
    resumen = _resumen_de(navegador, ficha, "003")
    assert _cerca(resumen["total"]["exacto"], TOTAL_MEMORIA) and resumen["cambios"] == 0
    assert _cerca(_resumen_de(navegador, ficha, "002")["total"]["exacto"], D("2821.4208"))


@pytest.mark.parametrize("fuente", ["", "   ", "\t\n"])
def test_restaurar_sin_fuente_es_422_con_el_texto_del_nucleo_y_no_escribe_nada(
    fuente, _casos
) -> None:
    ruta = _poner(_casos["dos"])
    navegador, ficha = _ana()
    antes = volcado(ruta)
    respuesta = _restaurar(navegador, ficha, fuente=fuente)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": SIN_FUENTE}
    assert respuesta.headers["cache-control"] == "no-store"
    assert volcado(ruta) == antes and _codigos(navegador) == ["001", "002"]  # igual antes y despues


def test_proyecto_o_version_inexistente_es_404_y_se_juzga_antes_que_el_dato(_entorno) -> None:
    navegador, ficha = _ana()
    antes = volcado(_entorno)
    sin_proyecto = _restaurar(navegador, ficha, proyecto="Z")
    assert sin_proyecto.status_code == 404
    assert sin_proyecto.json() == {"detalle": "El proyecto «Z» no existe en este caso."}
    sin_version = _restaurar(navegador, ficha, version="009")
    assert sin_version.status_code == 404
    assert sin_version.json() == {
        "detalle": f"El proyecto {NOMBRE_OF001!r} no tiene una version '009': "
        "elija una de la lista."
    }
    # el 404 va antes que el 422 del dato (la fuente en blanco)
    assert _restaurar(navegador, ficha, proyecto="Z", fuente="").status_code == 404
    assert _restaurar(navegador, ficha, version="009", fuente="").status_code == 404
    assert _restaurar(navegador, ficha, fuente="").status_code == 422
    # y la forma, antes que todo
    assert navegador.post(RESTAURAR, json={}, headers=protegida(ficha)).json() == {
        "detalle": FORMA_RESTAURAR
    }
    assert all(
        r.headers["cache-control"] == "no-store" for r in (sin_proyecto, sin_version)
    )
    assert volcado(_entorno) == antes


def test_el_proyecto_se_puede_dar_por_su_codigo_como_lo_ofrece_la_cabecera(_entorno) -> None:
    navegador, ficha = _ana()
    lista = navegador.get("/v1/proyectos").json()
    codigo = next(p["codigo"] for p in lista if p["nombre"] == NOMBRE_OF001)
    respuesta = _restaurar(navegador, ficha, proyecto=codigo)
    assert respuesta.status_code == 200 and respuesta.json()["proyecto"] == NOMBRE_OF001
    assert respuesta.json()["codigo"] == "002"


def test_restaurar_una_version_descartada_se_permite_como_en_la_clasica(_casos) -> None:
    ruta = _poner(_casos["dos"])
    with base(ruta) as sesion:
        descartar_version(sesion, NOMBRE_OF001, "002", date(2026, 10, 6))
        sesion.commit()
    navegador, ficha = _ana()
    respuesta = _restaurar(navegador, ficha, version="002")
    assert respuesta.status_code == 200 and respuesta.json()["codigo"] == "003"
    assert [v["descartada"] for v in _versiones(navegador)["versiones"]] == [False, True, False]
    assert cadena(ruta, NOMBRE_OF001).integra


def test_restaurar_ti001_sin_espacio_da_la_ti_002_con_el_total_del_caso(_casos) -> None:
    ruta = _poner(_casos["ti001"])
    navegador, ficha = _ana()
    assert _codigos(navegador, NOMBRE_TI001) == ["TI-001"]
    respuesta = _restaurar(navegador, ficha, "TI-001", proyecto=NOMBRE_TI001)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["codigo"] == "TI-002"
    assert registros(ruta, NOMBRE_TI001, "TI-002") == [
        ("version", "TI-001", "restauracion", "TI-001", "TI-002", FUENTE, "Ana <ana>")
    ]
    assert cadena(ruta, NOMBRE_TI001).integra
    assert _cerca(_resumen_de(navegador, ficha, "TI-002", NOMBRE_TI001)["total"]["exacto"], TOTAL_TI001)


# --- S3 / 3d-B12 / P32: cotizar ---

COTIZACION_001 = "Ferreteria Demo, C.A., COT-001, 2026-10-05"


def test_cotizar_crea_la_version_nueva_con_ese_insumo_y_conserva_el_plan(_entorno) -> None:
    navegador, ficha = _ana()
    antes_precios = _precios(navegador, "001")
    lista_antes = _fila(antes_precios, "EQU-001")
    total_antes = _resumen_de(navegador, ficha, "001")["total"]["exacto"]
    plan_antes = navegador.get(
        f"/v1/hoja/borradores/{_abierto(navegador, ficha, '001')}/vistas/plan"
    ).json()

    respuesta = _cotizar(navegador, ficha)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "codigo": "002",
        "proyecto": NOMBRE_OF001,
        "mensaje": "Se guardó la versión 002 con la cotización de EQU-001.",
    }
    estado = cadena(_entorno, NOMBRE_OF001)  # antes de abrir nada: abrir tambien escribe
    assert estado.integra, estado.mensaje
    # solo cambia ese insumo, en ese proyecto
    despues = _precios(navegador, "002")
    cotizada = _fila(despues, "EQU-001")
    assert cotizada["precio"]["exacto"] == "999.5" and cotizada["cotizacion"] == (
        "Ferreteria Demo, C.A., COT-001, 2026-10-05"
    )
    assert cotizada["estado"] == "OK"  # la cotizacion le da fuente
    for fila in despues:
        if fila["codigo"] != "EQU-001":
            assert fila == _fila(antes_precios, fila["codigo"])
    # la 001 sigue con su precio de lista; la nueva sale de ella
    assert _fila(_precios(navegador, "001"), "EQU-001") == lista_antes
    assert D(_resumen_de(navegador, ficha, "002")["total"]["exacto"]) > D(total_antes)
    # se conserva el plan: la misma matriz partida por periodo
    plan_despues = navegador.get(
        f"/v1/hoja/borradores/{_abierto(navegador, ficha, '002')}/vistas/plan"
    ).json()
    assert plan_despues["etiquetas"] == plan_antes["etiquetas"]
    assert plan_despues["filas"] == plan_antes["filas"]
    assert [v["origen"] for v in _versiones(navegador)["versiones"]] == ["", "001"]
    # el registro por celda y la cotizacion guardada, escritos a mano
    fuente = "Cotizacion COT-001 de Ferreteria Demo, C.A. (2026-10-05)."
    assert registros(_entorno, NOMBRE_OF001, "002") == [
        (
            "precio",
            "EQU-001",
            "cotizacion",
            lista_antes["precio"]["exacto"],
            "999.5",
            fuente,
            "Ana <ana>",
        )
    ]
    with base(_entorno) as sesion:
        fila = sesion.execute(
            select(
                models.Cotizacion.precio,
                models.Cotizacion.proveedor,
                models.Cotizacion.numero,
                models.Cotizacion.fecha,
            )
        ).one()
    assert tuple(fila) == (D("999.5"), PROVEEDOR, "COT-001", date(2026, 10, 5))


def _abierto(navegador, ficha, version: str) -> str:
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": version},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def test_la_evidencia_se_agrega_a_la_fuente_del_registro(_entorno) -> None:
    navegador, ficha = _ana()
    assert _cotizar(navegador, ficha, evidencia="factura 77 del proveedor").status_code == 200
    (registro,) = registros(_entorno, NOMBRE_OF001, "002")
    assert registro[5] == (
        "Cotizacion COT-001 de Ferreteria Demo, C.A. (2026-10-05). factura 77 del proveedor"
    )
    # null y ausente valen lo mismo
    assert _cotizar(navegador, ficha, version="002", precio="1000", evidencia=None).status_code == 200
    assert registros(_entorno, NOMBRE_OF001, "003")[0][5] == (
        "Cotizacion COT-001 de Ferreteria Demo, C.A. (2026-10-05)."
    )


def test_una_cotizacion_previa_del_mismo_insumo_se_reemplaza_y_las_otras_se_conservan(
    _casos,
) -> None:
    ruta = _poner(_casos["completa"])  # la 002 ya cotiza EQU-001 a 15.00
    navegador, ficha = _ana()
    assert _fila(_precios(navegador, "002"), "EQU-001")["cotizacion"] == COTIZACION_001
    segunda = _cotizar(navegador, ficha, version="002", insumo="MAT-001", precio="99.5")
    assert segunda.status_code == 200, segunda.text
    # otro insumo: se conserva la cotizacion de EQU-001
    filas = _precios(navegador, segunda.json()["codigo"])
    assert _fila(filas, "EQU-001")["cotizacion"] == COTIZACION_001
    assert _fila(filas, "MAT-001")["precio"]["exacto"] == "99.5"
    # el mismo insumo: se reemplaza
    tercera = _cotizar(navegador, ficha, version="002", precio="20", numero="COT-009")
    assert tercera.status_code == 200, tercera.text
    filas = _precios(navegador, tercera.json()["codigo"])
    assert _fila(filas, "EQU-001")["precio"]["exacto"] == "20"
    assert _fila(filas, "EQU-001")["cotizacion"].startswith("Ferreteria Demo, C.A., COT-009")
    assert cadena(ruta, NOMBRE_OF001).integra


def _precio_de_lista(navegador, version="001") -> str:
    return _fila(_precios(navegador, version), "EQU-001")["precio"]["exacto"]


def test_los_datos_de_una_cotizacion_invalida_dicen_cual_es_y_no_escriben_nada(_entorno) -> None:
    navegador, ficha = _ana()
    de_lista = _precio_de_lista(navegador)
    antes = volcado(_entorno)
    casos = [
        ({"precio": "abc"}, "precio: 'abc' no es un numero decimal valido"),
        ({"precio": "NaN"}, "precio: 'NaN' no es un monto finito"),
        ({"precio": "-1"}, "el precio cotizado debe ser un Decimal no negativo, no Decimal('-1')"),
        ({"proveedor": ""}, "el proveedor de la cotizacion es obligatorio"),
        ({"proveedor": "   "}, "el proveedor de la cotizacion es obligatorio"),
        ({"numero": ""}, "el numero de la cotizacion es obligatorio"),
        ({"insumo": "NO-EXISTE"}, "no hay ningun insumo con codigo 'NO-EXISTE'"),
        (
            {"precio": de_lista},
            f"el insumo EQU-001 ya vale {de_lista} en la lista de la version",
        ),
        # el orden del nucleo: el precio se juzga antes que el proveedor, y este antes que el numero
        ({"precio": "abc", "proveedor": ""}, "precio: 'abc' no es un numero decimal valido"),
        ({"proveedor": "", "numero": ""}, "el proveedor de la cotizacion es obligatorio"),
    ]
    fallos = []
    for cambios, texto in casos:
        respuesta = _cotizar(navegador, ficha, **cambios)
        if (respuesta.status_code, respuesta.json()) != (422, {"detalle": texto}):
            fallos.append((cambios, respuesta.status_code, respuesta.text))
        assert respuesta.headers["cache-control"] == "no-store"
    assert fallos == []
    assert volcado(_entorno) == antes and _codigos(navegador) == ["001"]


def test_cotizar_proyecto_o_version_inexistente_es_404_antes_que_el_precio(_entorno) -> None:
    navegador, ficha = _ana()
    antes = volcado(_entorno)
    sin_proyecto = _cotizar(navegador, ficha, proyecto="Z", precio="abc")
    assert sin_proyecto.status_code == 404
    assert sin_proyecto.json() == {"detalle": "El proyecto «Z» no existe en este caso."}
    sin_version = _cotizar(navegador, ficha, version="009", precio="abc")
    assert sin_version.status_code == 404 and "no tiene una version '009'" in sin_version.json()["detalle"]
    assert volcado(_entorno) == antes


def test_el_precio_con_espacios_se_acepta_y_la_fecha_es_la_que_dice_el_cuerpo(_entorno) -> None:
    navegador, ficha = _ana()
    respuesta = _cotizar(navegador, ficha, precio=" 999.5 ", fecha="2026-01-02")
    assert respuesta.status_code == 200, respuesta.text
    assert _fila(_precios(navegador, "002"), "EQU-001")["cotizacion"].endswith("2026-01-02")
    (registro,) = registros(_entorno, NOMBRE_OF001, "002")
    assert registro[4] == "999.5" and registro[5].endswith("(2026-01-02).")


# --- S4 / 3d-B12: retirar la cotizacion ---


def test_retirar_la_cotizacion_vuelve_al_precio_de_la_lista_base(_entorno) -> None:
    navegador, ficha = _ana()
    de_lista = _precio_de_lista(navegador)
    total_001 = _resumen_de(navegador, ficha, "001")["total"]["exacto"]
    assert _cotizar(navegador, ficha).json()["codigo"] == "002"

    respuesta = _retirar(navegador, ficha)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "codigo": "003",
        "proyecto": NOMBRE_OF001,
        "mensaje": "Se guardó la versión 003 sin la cotización.",
    }
    nueva = _fila(_precios(navegador, "003"), "EQU-001")
    assert nueva["precio"]["exacto"] == de_lista and nueva["cotizacion"] == ""
    assert registros(_entorno, NOMBRE_OF001, "003") == [
        ("precio", "EQU-001", "cotizacion", "999.5", de_lista, MOTIVO, "Ana <ana>")
    ]
    estado = cadena(_entorno, NOMBRE_OF001)  # antes de abrir nada: abrir tambien escribe
    assert estado.integra, estado.mensaje
    # volvio al total de la 001, exacto, y la 002 (cotizada) sigue ahi
    assert _resumen_de(navegador, ficha, "003")["total"]["exacto"] == total_001
    assert _fila(_precios(navegador, "002"), "EQU-001")["precio"]["exacto"] == "999.5"
    assert _codigos(navegador) == ["001", "002", "003"]


def test_los_errores_de_retirar_son_los_del_nucleo_y_no_escriben_nada(_casos) -> None:
    ruta = _poner(_casos["completa"])
    navegador, ficha = _ana()
    antes = volcado(ruta)
    casos = [
        ({"motivo": ""}, SIN_FUENTE),
        ({"motivo": "  "}, SIN_FUENTE),
        ({"insumo": "NO-EXISTE"}, "no hay ningun insumo con codigo 'NO-EXISTE'"),
        (
            {"version": "001"},
            "la version '001' no tiene cotizacion del insumo EQU-001",
        ),
    ]
    fallos = []
    for cambios, texto in casos:
        respuesta = _retirar(navegador, ficha, **cambios)
        if (respuesta.status_code, respuesta.json()) != (422, {"detalle": texto}):
            fallos.append((cambios, respuesta.status_code, respuesta.text))
    assert fallos == []
    assert _retirar(navegador, ficha, version="009").status_code == 404
    assert volcado(ruta) == antes


# --- las cuatro: una sola transaccion con BEGIN IMMEDIATE, carrera, todo o nada ---


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_el_bloqueo_de_escritura_es_la_primera_sentencia_y_va_antes_de_cualquier_select(
    operacion, _casos
) -> None:
    ruta = _poner(_casos["completa"])
    navegador, ficha = _ana()
    motor = dependencias.obtener_motor(dependencias.url_de_ruta(ruta))
    sentencias: list[str] = []

    def anotar(_conexion, _cursor, sentencia, *_resto) -> None:
        sentencias.append(sentencia.strip())

    event.listen(motor, "before_cursor_execute", anotar)
    try:
        respuesta = _hacer(navegador, ficha, operacion)
    finally:
        event.remove(motor, "before_cursor_execute", anotar)
    assert respuesta.status_code == 200, respuesta.text
    assert sentencias[0] == "BEGIN IMMEDIATE", sentencias[:3]
    assert next(n for n, s in enumerate(sentencias) if s.upper().startswith("SELECT")) > 0
    # una sola transaccion: despues de confirmar no se abre otra (que retendria el bloqueo)
    assert sentencias.count("BEGIN IMMEDIATE") == 1 and "BEGIN" not in sentencias


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_dos_peticiones_a_la_vez_obtienen_codigos_distintos_y_la_cadena_queda_sana(
    operacion, _casos
) -> None:
    ruta = _poner(_casos["completa"])
    navegador, ficha = _ana()
    respuestas = a_la_vez(
        lambda: _hacer(navegador, ficha, operacion), lambda: _hacer(navegador, ficha, operacion)
    )
    assert [r.status_code for r in respuestas] == [200, 200], [r.text for r in respuestas]
    assert sorted(r.json()["codigo"] for r in respuestas) == ["003", "004"]  # nunca dos «003»
    assert _codigos(navegador) == ["001", "002", "003", "004"]
    estado = cadena(ruta, NOMBRE_OF001)
    assert estado.integra, estado.mensaje


def _tras_escribir(real, fallo: Exception):
    """El nucleo escribe lo suyo en la transaccion y DESPUES falla: nada debe quedar."""

    def roto(*args, **kwargs):
        real(*args, **kwargs)
        raise fallo

    return roto


def _prefijo(operacion: str) -> str:
    return "No se convirtio nada: " if operacion == "convertir" else ""


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_si_el_nucleo_falla_despues_de_escribir_no_queda_nada_y_se_puede_reintentar(
    operacion, _casos, monkeypatch: pytest.MonkeyPatch
) -> None:
    ruta = _poner(_casos["completa"])
    navegador, ficha = _ana()
    nucleo = CUERPOS[operacion][3]
    real = getattr(copia, nucleo)
    antes = volcado(ruta)
    base_de_datos = OperationalError(
        "INSERT INTO presupuesto VALUES (?)",
        {},
        sqlite3.OperationalError("disk I/O error en /home/secreto/apu.db"),
    )
    casos = [
        (base_de_datos, 503, {"detalle": BASE}),
        (
            ValueError("el espacio no se pudo copiar"),
            422,
            {"detalle": _prefijo(operacion) + "el espacio no se pudo copiar"},
        ),
        (
            CatalogoIncompleto("falta la lista de precios"),
            409,
            {"detalle": "No se guardó nada: falta la lista de precios"},
        ),
        (RuntimeError("disco lleno"), 500, None),
    ]
    for fallo, estado, cuerpo in casos:
        with monkeypatch.context() as parche:
            parche.setattr(copia, nucleo, _tras_escribir(real, fallo))
            respuesta = _hacer(navegador, ficha, operacion)
        assert respuesta.status_code == estado, (fallo, respuesta.text)
        if cuerpo is not None:
            assert respuesta.json() == cuerpo and respuesta.headers["cache-control"] == "no-store"
        for prohibido in ("sqlite", "INSERT", "secreto", ".db", "disco"):
            assert prohibido not in respuesta.text
        assert volcado(ruta) == antes  # ninguna version, registro, lista ni eslabon
        assert cadena(ruta, NOMBRE_OF001).integra
    reintento = _hacer(navegador, ficha, operacion)  # sin el fallo, la misma peticion pasa
    assert reintento.status_code == 200 and reintento.json()["codigo"] == "003"


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_un_error_de_base_al_leer_el_codigo_es_503_fijo_sin_sql_ni_rutas(
    operacion, _casos, monkeypatch: pytest.MonkeyPatch
) -> None:
    ruta = _poner(_casos["completa"])
    navegador, ficha = _ana()
    antes = volcado(ruta)
    fallo = OperationalError(
        "SELECT presupuesto.id FROM presupuesto WHERE secreto = ?",
        {},
        sqlite3.OperationalError("unable to open database file C:/datos/privados/apu.db"),
    )

    def roto(*_args, **_kwargs):
        raise fallo

    with monkeypatch.context() as parche:
        parche.setattr(copia, "siguiente_codigo", roto)
        respuesta = _hacer(navegador, ficha, operacion)
    assert respuesta.status_code == 503 and respuesta.json() == {"detalle": BASE}
    assert respuesta.headers["cache-control"] == "no-store"
    for prohibido in ("sqlite", "SELECT", "presupuesto", "privados", "apu.db"):
        assert prohibido not in respuesta.text
    assert volcado(ruta) == antes and cadena(ruta, NOMBRE_OF001).integra


def test_un_rechazo_antes_de_escribir_suelta_el_bloqueo_de_escritura(_entorno) -> None:
    """Un 404, un dato mal escrito o una fuente en blanco se rechazan DESPUES de que la primera
    lectura abrio `BEGIN IMMEDIATE`: la funcion deshace esa transaccion ella misma (no espera a que
    alguien cierre la sesion) y otra conexion toma el bloqueo sin esperar."""
    from aplicacion import hoja_versiones

    motor = crear_motor(f"sqlite:///{_entorno.as_posix()}")
    llamadas = [
        lambda s: hoja_versiones.restaurar(s, "Z", "001", fuente=FUENTE, responsable="Ana <ana>"),
        lambda s: hoja_versiones.restaurar(
            s, NOMBRE_OF001, "009", fuente=FUENTE, responsable="Ana <ana>"
        ),
        lambda s: hoja_versiones.restaurar(
            s, NOMBRE_OF001, "001", fuente="", responsable="Ana <ana>"
        ),
        lambda s: hoja_versiones.cotizar(
            s,
            NOMBRE_OF001,
            "001",
            insumo="EQU-001",
            precio="abc",
            proveedor=PROVEEDOR,
            numero="C-1",
            fecha=date(2026, 10, 5),
            evidencia=None,
            responsable="Ana <ana>",
        ),
        lambda s: hoja_versiones.retirar_cotizacion(
            s, NOMBRE_OF001, "001", insumo="EQU-001", motivo=MOTIVO, responsable="Ana <ana>"
        ),
        lambda s: hoja_versiones.convertir(
            s,
            NOMBRE_OF001,
            "001",
            "Bs",
            lado="venta",
            fecha=HOY,
            fuente="x",
            responsable="Ana <ana>",
        ),
    ]
    try:
        with abrir_sesion_de_escritura(motor) as sesion:
            for llamada in llamadas:
                with pytest.raises(Exception):  # noqa: B017, PT011 (cada una falla por su motivo)
                    llamada(sesion)
                assert not sesion.in_transaction()
                with closing(sqlite3.connect(_entorno.as_posix(), timeout=0)) as otra:
                    otra.isolation_level = None
                    otra.execute("BEGIN IMMEDIATE")  # sin esperar: nadie retiene el bloqueo
                    otra.execute("ROLLBACK")
    finally:
        motor.dispose()


# --- el cambio de caso: las cuatro actuan sobre el caso de la ficha en ese momento ---


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_tras_cambiar_de_caso_la_operacion_escribe_solo_en_el_caso_nuevo(
    operacion, _casos
) -> None:
    viejo = _poner(_casos["completa"])
    nuevo = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["completa"], nuevo)
    preparar_base(viejo)
    preparar_base(nuevo)
    navegador, ficha = _ana()
    antes_viejo = volcado(viejo)
    cambio = navegador.post(
        "/v1/casos/actual", json={"nombre": nuevo.name}, headers=protegida(ficha)
    )
    assert cambio.status_code == 200, cambio.text
    respuesta = _hacer(navegador, ficha, operacion)
    assert respuesta.status_code == 200 and respuesta.json()["codigo"] == "003"
    assert volcado(viejo) == antes_viejo  # el caso de antes, intacto
    assert _codigos(navegador) == ["001", "002", "003"]  # en el nuevo
    assert cadena(nuevo, NOMBRE_OF001).integra


def test_si_el_proyecto_no_esta_en_el_caso_nuevo_es_404_y_ninguna_base_cambia(_casos) -> None:
    viejo = _poner(_casos["of001"])
    nuevo = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["ti001"], nuevo)  # otro caso: sin el proyecto de OF-001
    preparar_base(viejo)
    preparar_base(nuevo)
    navegador, ficha = _ana()
    assert navegador.post(
        "/v1/casos/actual", json={"nombre": nuevo.name}, headers=protegida(ficha)
    ).status_code == 200
    antes_viejo, antes_nuevo = volcado(viejo), volcado(nuevo)
    respuesta = _restaurar(navegador, ficha)  # el proyecto es el de OF-001
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": f"El proyecto «{NOMBRE_OF001}» no existe en este caso."}
    assert volcado(viejo) == antes_viejo and volcado(nuevo) == antes_nuevo


# --- la forma del cuerpo, antes de todo lo demas ---


def _cuerpos_malos(operacion: str) -> list[tuple[str, dict]]:
    """Variantes de un cuerpo valido que NO tienen la forma esperada."""
    _ruta, valido, _forma, _nucleo = CUERPOS[operacion]
    malos: list[tuple[str, dict]] = [("vacio", {})]
    for campo in valido:
        sin = {k: v for k, v in valido.items() if k != campo}
        malos.append((f"sin-{campo}", sin))
        malos.append((f"{campo}-objeto", {**valido, campo: {"x": CENTINELA}}))
        malos.append((f"{campo}-numero", {**valido, campo: 12.5}))
        malos.append((f"{campo}-booleano", {**valido, campo: True}))
        if campo not in ("lado", "fecha"):
            malos.append((f"{campo}-enorme", {**valido, campo: CENTINELA * 100}))
    malos.append(("campo-extra", {**valido, "responsable": CENTINELA}))
    malos.append(("proyecto-vacio", {**valido, "proyecto": ""}))
    malos.append(("version-vacia", {**valido, "version": ""}))
    if operacion == "convertir":
        malos.append(("lado-desconocido", {**valido, "lado": CENTINELA}))
        malos.append(("moneda-vacia", {**valido, "moneda": ""}))
    if operacion == "cotizar":
        for fecha in ("2026-02-30", "05/10/2026", "ayer", "", "2026-10-05T10:00:00", 20261005):
            malos.append((f"fecha-{fecha!r}", {**valido, "fecha": fecha}))
        malos.append(("evidencia-de-91", {**valido, "evidencia": "e" * 91}))
        malos.append(("proveedor-de-121", {**valido, "proveedor": "p" * 121}))
        malos.append(("numero-de-61", {**valido, "numero": "n" * 61}))
        malos.append(("precio-numero", {**valido, "precio": 999.5}))
        malos.append(("insumo-vacio", {**valido, "insumo": ""}))
    if operacion in ("restaurar", "convertir"):
        malos.append(("fuente-de-301", {**valido, "fuente": "f" * 301}))
    if operacion == "retirar":
        malos.append(("motivo-de-301", {**valido, "motivo": "f" * 301}))
    return malos


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_un_cuerpo_con_otra_forma_es_422_fijo_sin_eco_y_con_no_store(operacion, _casos) -> None:
    ruta = _poner(_casos["completa"])
    navegador, ficha = _ana()
    antes = volcado(ruta)
    ruta_http, _valido, forma, _nucleo = CUERPOS[operacion]
    fallos = []
    for nombre, cuerpo in _cuerpos_malos(operacion):
        respuesta = navegador.post(ruta_http, json=cuerpo, headers=protegida(ficha))
        correcto = (
            respuesta.status_code == 422
            and respuesta.json() == {"detalle": forma}
            and CENTINELA not in respuesta.text
            and respuesta.headers["cache-control"] == "no-store"
        )
        if not correcto:
            fallos.append((nombre, respuesta.status_code, respuesta.text[:120]))
    assert fallos == []
    assert volcado(ruta) == antes


def test_los_topes_exactos_se_aceptan(_entorno) -> None:
    """300 caracteres de fuente, 120 de proveedor, 60 de numero y 90 de evidencia son los topes."""
    navegador, ficha = _ana()
    assert _restaurar(navegador, ficha, fuente="f" * 300).status_code == 200
    (registro,) = registros(_entorno, NOMBRE_OF001, "002")
    assert registro[5] == "f" * 300
    respuesta = _cotizar(
        navegador,
        ficha,
        proveedor="p" * 120,
        numero="n" * 60,
        evidencia="e" * 90,
        version="002",
    )
    assert respuesta.status_code == 200, respuesta.text
    (registro,) = registros(_entorno, NOMBRE_OF001, "003")
    assert len(registro[5]) == 300  # 11 + 60 + 4 + 120 + 13 + 2 + 90: el ancho de la columna


def test_el_responsable_es_la_sesion_y_el_cuerpo_no_puede_decir_otro_p34(_entorno) -> None:
    navegador, ficha = _ana()
    respuesta = _restaurar(navegador, ficha, responsable="Otra Persona <otra>")
    assert respuesta.status_code == 422 and "Otra" not in respuesta.text
    assert _codigos(navegador) == ["001"]
    assert _restaurar(navegador, ficha).status_code == 200
    assert registros(_entorno, NOMBRE_OF001, "002")[0][-1] == "Ana <ana>"


# --- acceso: 3d-B14 para S2 a S5 ---


def test_sin_sesion_ni_clave_es_401_en_las_cuatro() -> None:
    fallos = []
    for operacion in OPERACIONES:
        ruta, cuerpo, _forma, _nucleo = CUERPOS[operacion]
        respuesta = cliente(app).post(ruta, json=cuerpo, headers={"Origin": ORIGEN})
        if respuesta.status_code != 401 or "detalle" not in respuesta.json():
            fallos.append((operacion, respuesta.status_code))
        assert respuesta.headers["cache-control"] == "no-store"
    assert fallos == []


@pytest.mark.parametrize("login", ["rita", "admin", "tomas"])
def test_quien_no_arma_no_puede_usar_ninguna_de_las_cuatro(login, _casos) -> None:
    ruta = _poner(_casos["completa"])
    navegador, ficha = con_cuenta(app, login)
    antes = volcado(ruta)
    for operacion in OPERACIONES:
        respuesta = _hacer(navegador, ficha, operacion)
        assert respuesta.status_code == 403, (login, operacion)
        if login != "tomas":  # tomas debe cambiar su clave: su 403 es otro
            assert respuesta.json() == {"detalle": MENSAJE_PERMISO}
        assert respuesta.headers["cache-control"] == "no-store"
    assert volcado(ruta) == antes


def test_la_clave_de_api_no_escribe_versiones(_casos) -> None:
    ruta = _poner(_casos["completa"])
    antes = volcado(ruta)
    cabeceras = {CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN}
    for operacion in OPERACIONES:
        ruta_http, cuerpo, _forma, _nucleo = CUERPOS[operacion]
        respuesta = cliente(app).post(ruta_http, json=cuerpo, headers=cabeceras)
        assert respuesta.status_code == 403 and respuesta.json() == {"detalle": SOLO_CUENTA}
        assert respuesta.headers["cache-control"] == "no-store"
    assert volcado(ruta) == antes


def test_exigen_csrf_y_origen_propio(_casos) -> None:
    ruta = _poner(_casos["completa"])
    navegador, ficha = _ana()
    antes = volcado(ruta)
    for operacion in OPERACIONES:
        ruta_http, cuerpo, _forma, _nucleo = CUERPOS[operacion]
        sin_csrf = navegador.post(ruta_http, json=cuerpo, headers={"Origin": ORIGEN})
        ajeno = navegador.post(
            ruta_http, json=cuerpo, headers=protegida(ficha, origen="http://evil.example")
        )
        sin_origen = navegador.post(ruta_http, json=cuerpo, headers=protegida(ficha, origen=None))
        assert [r.status_code for r in (sin_csrf, ajeno, sin_origen)] == [403, 403, 403], operacion
    assert volcado(ruta) == antes


def test_convertir_exige_convertir_y_reajustar_y_las_otras_tres_editar_la_hoja(
    _casos, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La matriz de permisos es la unica fuente (hallazgo 5 del diseno): hoy las dos acciones son
    solo de `arma`, asi que se separan a proposito para ver que cada ruta pide la suya."""
    _poner(_casos["completa"])
    navegador, ficha = _ana()
    sin_convertir = {**permisos.PERMISOS, permisos.Accion.CONVERTIR_Y_REAJUSTAR: frozenset({permisos.Rol.REVISA})}
    with monkeypatch.context() as parche:
        parche.setattr(permisos, "PERMISOS", sin_convertir)
        convertir = _hacer(navegador, ficha, "convertir")
        assert convertir.status_code == 403 and convertir.json() == {"detalle": MENSAJE_PERMISO}
        assert _hacer(navegador, ficha, "restaurar").status_code == 200
    sin_editar = {**permisos.PERMISOS, permisos.Accion.EDITAR_HOJA: frozenset({permisos.Rol.REVISA})}
    with monkeypatch.context() as parche:
        parche.setattr(permisos, "PERMISOS", sin_editar)
        for operacion in ("restaurar", "cotizar", "retirar"):
            assert _hacer(navegador, ficha, operacion).status_code == 403, operacion
        assert _hacer(navegador, ficha, "convertir").status_code == 200


# --- tamaños, float, no-store ---


def test_un_cuerpo_de_mas_de_20_mib_es_413_y_no_escribe(_entorno) -> None:
    navegador, ficha = _ana()
    antes = volcado(_entorno)
    cabeceras = {**protegida(ficha), "Content-Type": "application/json"}
    enorme = b'{"proyecto":"x","version":"001","fuente":"' + b"1" * (20 * MIB) + b'"}'
    respuesta = navegador.post(RESTAURAR, content=enorme, headers=cabeceras)
    assert respuesta.status_code == 413 and respuesta.json() == {"detalle": EXCEDE}
    assert volcado(_entorno) == antes


@pytest.mark.parametrize("operacion", OPERACIONES)
def test_ningun_numero_del_json_es_float_y_todo_es_texto(operacion, _casos) -> None:
    _poner(_casos["completa"])
    navegador, ficha = _ana()
    respuesta = _hacer(navegador, ficha, operacion)
    assert respuesta.status_code == 200
    sin_float(json.loads(respuesta.text, parse_float=lambda t: float("nan")))
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"codigo", "proyecto", "mensaje"}
    assert all(isinstance(v, str) for v in cuerpo.values())


# --- la guardia: la API no crea versiones con la sesion comun ---


def test_toda_funcion_de_la_api_que_crea_versiones_desde_una_guardada_usa_la_sesion_de_escritura() -> None:
    """Lo que cree una version sin `BEGIN IMMEDIATE` reabre la carrera por el codigo: se vigila
    leyendo el codigo de `api/` (AST), sin importar nada."""
    import ast

    raiz = Path(__file__).resolve().parents[2]
    nombres = {"restaurar", "cotizar", "retirar_cotizacion", "convertir"}
    encontradas = []
    for archivo in sorted((raiz / "api").rglob("*.py")):
        for definicion in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if not isinstance(definicion, ast.FunctionDef):
                continue
            llama = any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr in nombres
                and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "hoja_versiones"
                for n in ast.walk(definicion)
            )
            if llama:
                anotaciones = {
                    ast.unparse(a.annotation) for a in definicion.args.args if a.annotation
                }
                encontradas.append((archivo.name, definicion.name))
                assert "SesionDeEscrituraDep" in anotaciones, (archivo.name, definicion.name)
                assert "SesionDep" not in anotaciones, (archivo.name, definicion.name)
    assert sorted(n for _a, n in encontradas) == [
        "convertir_version",
        "cotizar_insumo",
        "restaurar_version",
        "retirar_cotizacion",
    ]
