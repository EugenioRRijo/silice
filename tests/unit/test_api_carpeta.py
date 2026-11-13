"""MP-1, Tarea 2: las rutas de la carpeta de trabajo (`api/rutas/carpeta.py`).

Contrato (plan de montar un presupuesto, T2; diseño §5.1 y §10, D-MP1: una moneda por carpeta):

- `GET /v1/carpeta` (cualquier rol) -> `{moneda, declarada, lista, aviso}`; `lista` es
  `{nombre, moneda, fecha, origen}` o `null`; `aviso` es el mensaje de «sin lista para armar».
- `PUT /v1/carpeta/moneda` (`EDITAR_HOJA`) `{moneda: "Bs"|"USD"}` -> 200 con la misma forma; 409 si
  la carpeta ya trabaja en otra moneda (declarada o la de su lista vigente).
- `POST /v1/carpeta/lista-para-armar` (`EDITAR_HOJA`) `{desde: "maprex"|"convertir"}` -> 201 con la
  misma forma; 409 con el mensaje de la regla que impide crearla. Desde el 2026-11-13 (prueba de
  punta a punta, D-7) también `{desde: "empresa", lista_id}`: copia la lista de la empresa en su
  moneda, sin tasa; `GET` dice en `empresa` las listas de empresa de la moneda de la carpeta.

Oráculos escritos a mano: los textos literales del plan y del diseño, el nombre de la lista
(«MaPreX julio 2026 en Bs al dd/mm/aaaa» con la fecha de hoy), 400 Bs ÷ 40 = 10 USD y las filas
leídas con `sqlite3` directo. Datos ficticios (insumo «Cemento gris»; tasa del BCV de 40,00 Bs/USD
inventada).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.main import app
from aplicacion.tablas_carpeta import CarpetaDeTrabajo
from core import models
from core.catalog import abrir_sesion, crear_motor
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
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

HOY = date.today()
JULIO = date(2026, 7, 1)
SIN_LISTA = (
    "Esta carpeta de trabajo no tiene lista de precios para armar. Créela a partir de MaPreX o "
    "convirtiendo la que tiene."
)
SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar."
YA_EN_BS = "La carpeta de trabajo ya trabaja en Bs: para trabajar en USD, cree otra carpeta."
YA_EN_USD = "La carpeta de trabajo ya trabaja en USD: para trabajar en Bs, cree otra carpeta."
CONVERTIR_AVISO = (
    "La lista vigente «Base» está en Bs y la carpeta trabaja en USD: conviértala antes de armar."
)
NADA_QUE_CONVERTIR = "La lista vigente «Base» ya está en Bs: no hay nada que convertir."
MENSAJE_422 = (
    "Indique la moneda (Bs o USD) o de dónde crear la lista (maprex, convertir o empresa, con "
    "el número de la lista de la empresa)."
)
PRIVADO = "valor-que-nunca-debe-volver"
NOMBRE_MAPREX_HOY = f"MaPreX julio 2026 en Bs al {HOY:%d/%m/%Y}"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("carpeta"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalación con cuentas y el caso por defecto vacío (sin lista ni moneda)."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _en_el_caso(ruta: Path, escribir) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            escribir(s)
            s.commit()
    finally:
        motor.dispose()


def _lista_base(ruta: Path, nombre: str = "Base", moneda: str = "Bs") -> None:
    def escribir(s) -> None:
        insumo = models.Insumo(
            codigo="MAT-001", tipo="material", descripcion="Cemento gris", unidad="saco"
        )
        lista = models.ListaPrecios(
            nombre=nombre, moneda=moneda, fecha_vigencia=JULIO, origen="prueba"
        )
        s.add_all([insumo, lista])
        s.flush()
        s.add(models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=Decimal("400")))

    _en_el_caso(ruta, escribir)


def _tasa(ruta: Path, fecha: date, valor: str = "40.00") -> None:
    _en_el_caso(
        ruta,
        lambda s: registrar_importacion(
            s,
            definicion_tasa("venta"),
            [Observacion(fecha, Decimal(valor))],
            archivo="tasa_ficticia.xls",
            huella=f"{fecha:%Y%m%d}".ljust(64, "0"),
            fuente="BCV (dato ficticio de prueba)",
            fecha_descarga=fecha,
            responsable="ana",
            filas_leidas=1,
            filas_rechazadas=0,
        ),
    )


def _declarar_usd_en_la_base(ruta: Path) -> None:
    _en_el_caso(
        ruta,
        lambda s: s.add(
            CarpetaDeTrabajo(
                id=1, moneda="USD", declarada_por="ana", declarada_el=datetime(2026, 10, 25, 9, 30)
            )
        ),
    )


def _filas(ruta: Path, consulta: str) -> list[tuple]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        return list(bd.execute(consulta))


def _poner(navegador, ficha: str, moneda):
    return navegador.put("/v1/carpeta/moneda", json={"moneda": moneda}, headers=protegida(ficha))


def _crear(navegador, ficha: str, desde):
    return navegador.post(
        "/v1/carpeta/lista-para-armar", json={"desde": desde}, headers=protegida(ficha)
    )


# --- GET ----------------------------------------------------------------------------------------


def test_carpeta_vacia_dice_que_no_hay_moneda_ni_lista() -> None:
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.get("/v1/carpeta")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "moneda": None,
        "declarada": False,
        "lista": None,
        "aviso": SIN_LISTA,
        "empresa": [],
    }


def test_con_lista_vigente_sin_declarar_la_moneda_es_la_de_la_lista(_entorno: Path) -> None:
    _lista_base(_entorno)
    navegador, _ = con_cuenta(app, "ana")
    assert navegador.get("/v1/carpeta").json() == {
        "moneda": "Bs",
        "declarada": False,
        "lista": {"nombre": "Base", "moneda": "Bs", "fecha": "2026-07-01", "origen": "prueba"},
        "aviso": None,
        "empresa": [],
    }


@pytest.mark.parametrize("login", ["ana", "rita", "admin"])
def test_cualquier_rol_con_sesion_consulta_la_carpeta(login: str) -> None:
    navegador, _ = con_cuenta(app, login)
    assert navegador.get("/v1/carpeta").status_code == 200


def test_sin_sesion_ni_clave_no_entra() -> None:
    assert cliente(app).get("/v1/carpeta").status_code == 401


def test_con_clave_de_api_consulta_y_declara(_entorno: Path) -> None:
    cabeceras = {CABECERA: crear_clave_de_prueba()}
    navegador = cliente(app)
    assert navegador.get("/v1/carpeta", headers=cabeceras).status_code == 200
    respuesta = navegador.put("/v1/carpeta/moneda", json={"moneda": "Bs"}, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert _filas(_entorno, "SELECT moneda, declarada_por FROM mp_carpeta") == [
        ("Bs", "api (clave de API)")
    ]


def test_carpeta_usd_con_lista_vigente_en_bs_avisa_y_la_muestra_para_convertir(
    _entorno: Path,
) -> None:
    # T4: `lista` es la vigente aunque esté en otra moneda (el `aviso` dice que no sirve para
    # armar), para que la pantalla ofrezca «Convertir la lista que tiene».
    _lista_base(_entorno)
    _declarar_usd_en_la_base(_entorno)
    navegador, _ = con_cuenta(app, "ana")
    assert navegador.get("/v1/carpeta").json() == {
        "moneda": "USD",
        "declarada": True,
        "lista": {"nombre": "Base", "moneda": "Bs", "fecha": "2026-07-01", "origen": "prueba"},
        "aviso": CONVERTIR_AVISO,
        "empresa": [],
    }


# --- PUT /moneda ---------------------------------------------------------------------------------


def test_ana_declara_bs_y_la_carpeta_lo_recuerda(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _poner(navegador, ficha, "Bs")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "moneda": "Bs",
        "declarada": True,
        "lista": None,
        "aviso": SIN_LISTA,
        "empresa": [],
    }
    assert navegador.get("/v1/carpeta").json()["moneda"] == "Bs"
    assert _filas(_entorno, "SELECT id, moneda, declarada_por FROM mp_carpeta") == [
        (1, "Bs", "Ana <ana>")
    ]


def test_declarar_la_misma_moneda_otra_vez_no_cambia_nada(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    _poner(navegador, ficha, "USD")
    antes = _filas(_entorno, "SELECT * FROM mp_carpeta")
    assert _poner(navegador, ficha, "USD").status_code == 200
    assert _filas(_entorno, "SELECT * FROM mp_carpeta") == antes


def test_declarar_otra_moneda_despues_es_409_con_el_texto_exacto(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    _poner(navegador, ficha, "Bs")
    respuesta = _poner(navegador, ficha, "USD")
    assert respuesta.status_code == 409
    assert respuesta.json()["detalle"] == YA_EN_BS
    assert _filas(_entorno, "SELECT moneda FROM mp_carpeta") == [("Bs",)]


def test_declarar_usd_con_lista_vigente_en_bs_es_409_y_no_escribe(_entorno: Path) -> None:
    _lista_base(_entorno)
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _poner(navegador, ficha, "USD")
    assert respuesta.status_code == 409
    assert respuesta.json()["detalle"] == YA_EN_BS
    assert _filas(_entorno, "SELECT * FROM mp_carpeta") == []


def test_declarar_bs_con_lista_vigente_en_usd_es_409(_entorno: Path) -> None:
    _lista_base(_entorno, moneda="USD")
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _poner(navegador, ficha, "Bs")
    assert respuesta.status_code == 409
    assert respuesta.json()["detalle"] == YA_EN_USD


def test_rita_no_declara_la_moneda(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "rita")
    respuesta = _poner(navegador, ficha, "Bs")
    assert respuesta.status_code == 403
    assert respuesta.json()["detalle"] == MENSAJE_PERMISO
    assert _filas(_entorno, "SELECT * FROM mp_carpeta") == []


def test_sin_csrf_no_declara(_entorno: Path) -> None:
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.put("/v1/carpeta/moneda", json={"moneda": "Bs"})
    assert respuesta.status_code == 403
    assert _filas(_entorno, "SELECT * FROM mp_carpeta") == []


def test_con_origen_ajeno_no_declara(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.put(
        "/v1/carpeta/moneda",
        json={"moneda": "Bs"},
        headers=protegida(ficha, origen="http://otro.example"),
    )
    assert respuesta.status_code == 403
    assert _filas(_entorno, "SELECT * FROM mp_carpeta") == []


@pytest.mark.parametrize("cuerpo", [{"moneda": PRIVADO}, {"moneda": 5}, {}, {"moneda": None}])
def test_un_422_de_la_moneda_no_repite_lo_enviado(cuerpo: dict) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.put("/v1/carpeta/moneda", json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_422}
    assert PRIVADO not in respuesta.text


def test_la_moneda_no_se_acepta_en_minusculas() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _poner(navegador, ficha, "usd").status_code == 422
    assert _poner(navegador, ficha, "Bs.").status_code == 422


# --- POST /lista-para-armar ---------------------------------------------------------------------


def test_crear_desde_maprex_da_201_con_la_lista_de_hoy(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, "maprex")
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["moneda"] == "Bs"
    assert cuerpo["aviso"] is None
    assert cuerpo["lista"]["nombre"] == NOMBRE_MAPREX_HOY
    assert cuerpo["lista"]["moneda"] == "Bs"
    assert cuerpo["lista"]["fecha"] == HOY.isoformat()
    assert "ana" in cuerpo["lista"]["origen"]
    assert navegador.get("/v1/carpeta").json() == cuerpo
    nombres = {n for (n,) in _filas(_entorno, "SELECT nombre FROM lista_precios")}
    assert NOMBRE_MAPREX_HOY in nombres


def test_crear_desde_maprex_en_carpeta_usd_convierte_con_la_tasa(_entorno: Path) -> None:
    _tasa(_entorno, HOY)
    navegador, ficha = con_cuenta(app, "ana")
    _poner(navegador, ficha, "USD")
    respuesta = _crear(navegador, ficha, "maprex")
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["moneda"] == "USD"
    assert cuerpo["lista"]["moneda"] == "USD"
    assert cuerpo["lista"]["nombre"] == f"MaPreX julio 2026 en USD al {HOY:%d/%m/%Y}"


def test_crear_desde_maprex_en_usd_sin_tasa_es_409_y_no_escribe_lista(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    _poner(navegador, ficha, "USD")
    respuesta = _crear(navegador, ficha, "maprex")
    assert respuesta.status_code == 409
    assert respuesta.json()["detalle"] == SIN_TASA
    assert _filas(_entorno, "SELECT * FROM lista_precios") == []


def test_crear_desde_maprex_si_ya_hay_lista_para_armar_es_409_y_no_crea_otra(
    _entorno: Path,
) -> None:
    # T4: un aviso viejo (otra pestaña) no debe crear «… (2)» encima de la lista que ya hay.
    navegador, ficha = con_cuenta(app, "ana")
    assert _crear(navegador, ficha, "maprex").status_code == 201
    respuesta = _crear(navegador, ficha, "maprex")
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": (
            f"La carpeta de trabajo ya tiene lista para armar («{NOMBRE_MAPREX_HOY}»): no se "
            "creó otra."
        )
    }
    nombres = [n for (n,) in _filas(_entorno, "SELECT nombre FROM lista_precios")]
    assert nombres.count(NOMBRE_MAPREX_HOY) == 1
    assert not any(n.endswith(")") for n in nombres)


def test_crear_desde_maprex_con_la_vigente_en_otra_moneda_si_crea(_entorno: Path) -> None:
    # Con la vigente en otra moneda no hay lista para armar: MaPreX sigue siendo una salida.
    _lista_base(_entorno)
    _tasa(_entorno, HOY)
    _declarar_usd_en_la_base(_entorno)
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, "maprex")
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["lista"]["nombre"] == f"MaPreX julio 2026 en USD al {HOY:%d/%m/%Y}"


def test_convertir_la_vigente_en_bs_a_la_carpeta_usd(_entorno: Path) -> None:
    _lista_base(_entorno)
    _tasa(_entorno, HOY)
    _declarar_usd_en_la_base(_entorno)
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, "convertir")
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["lista"]["moneda"] == "USD"
    assert cuerpo["lista"]["nombre"] == f"Base en USD al {HOY:%d/%m/%Y}"
    assert cuerpo["aviso"] is None
    precios = _filas(
        _entorno,
        "SELECT p.precio FROM precio_insumo p JOIN lista_precios l ON l.id = p.lista_id "
        "WHERE l.moneda = 'USD'",
    )
    assert [Decimal(str(p)) for (p,) in precios] == [Decimal("10")]  # 400 Bs / 40 = 10 USD


def test_convertir_sin_tasa_es_409(_entorno: Path) -> None:
    _lista_base(_entorno)
    _declarar_usd_en_la_base(_entorno)
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, "convertir")
    assert respuesta.status_code == 409
    assert respuesta.json()["detalle"] == SIN_TASA


def test_convertir_cuando_la_lista_ya_esta_en_la_moneda_es_409(_entorno: Path) -> None:
    _lista_base(_entorno)
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, "convertir")
    assert respuesta.status_code == 409
    assert respuesta.json()["detalle"] == NADA_QUE_CONVERTIR


def test_convertir_sin_ninguna_lista_es_409(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, "convertir")
    assert respuesta.status_code == 409
    assert respuesta.json()["detalle"] == SIN_LISTA


def test_rita_no_crea_la_lista(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "rita")
    respuesta = _crear(navegador, ficha, "maprex")
    assert respuesta.status_code == 403
    assert respuesta.json()["detalle"] == MENSAJE_PERMISO
    assert _filas(_entorno, "SELECT * FROM lista_precios") == []


def test_sin_csrf_no_crea_la_lista(_entorno: Path) -> None:
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.post("/v1/carpeta/lista-para-armar", json={"desde": "maprex"})
    assert respuesta.status_code == 403
    assert _filas(_entorno, "SELECT * FROM lista_precios") == []


@pytest.mark.parametrize("cuerpo", [{"desde": PRIVADO}, {"desde": 1}, {}, {"desde": None}])
def test_un_422_de_la_lista_no_repite_lo_enviado(cuerpo: dict, _entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.post(
        "/v1/carpeta/lista-para-armar", json=cuerpo, headers=protegida(ficha)
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_422}
    assert PRIVADO not in respuesta.text
    assert _filas(_entorno, "SELECT * FROM lista_precios") == []


def test_si_la_creacion_falla_tras_cargar_la_referencia_la_carpeta_queda_coherente(
    _entorno: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`cargar_referencia_maprex` confirma por su cuenta: queda la referencia (global, sin usar) y
    ninguna lista para armar a medias; la moneda declarada no cambia y reintentar funciona."""
    from aplicacion import listas_para_armar

    navegador, ficha = con_cuenta(app, "ana")
    _poner(navegador, ficha, "Bs")
    original = listas_para_armar._lista_global

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(listas_para_armar, "_lista_global", falla)
    assert _crear(navegador, ficha, "maprex").status_code == 500
    assert _filas(_entorno, "SELECT nombre, moneda FROM lista_precios") == [
        ("MaPreX julio 2026 en Bs", "Bs")
    ]
    assert _filas(_entorno, "SELECT moneda, declarada_por FROM mp_carpeta") == [("Bs", "Ana <ana>")]
    monkeypatch.setattr(listas_para_armar, "_lista_global", original)
    estado = navegador.get("/v1/carpeta").json()
    assert estado["moneda"] == "Bs"
    assert _crear(navegador, ficha, "maprex").status_code == 201
    nombres = sorted(n for (n,) in _filas(_entorno, "SELECT nombre FROM lista_precios"))
    assert nombres == sorted(["MaPreX julio 2026 en Bs", NOMBRE_MAPREX_HOY])


# --- desde la lista de la empresa (prueba de punta a punta 2026-11-13, D-7) ---------------------


def _lista_de_empresa(ruta: Path, moneda: str = "USD") -> int:
    """Una lista de empresa «Empresa ficticia 2026-10-05» en `moneda` con el cemento a 11,25."""
    from core.catalog.empresa import PrecioPropio, crear_lista_de_empresa

    creada: list[int] = []

    def escribir(s) -> None:
        insumo = models.Insumo(
            codigo="MAT-001", tipo="material", descripcion="Cemento gris", unidad="saco"
        )
        base = models.ListaPrecios(nombre="Base", moneda=moneda, fecha_vigencia=JULIO, origen="x")
        s.add_all([insumo, base])
        s.flush()
        s.add(models.ListaPreciosOrigen(lista_id=base.id, alcance=models.ALCANCE_REFERENCIA))
        s.add(models.PrecioInsumo(lista_id=base.id, insumo_id=insumo.id, precio=Decimal("9")))
        s.flush()
        s.expire(base, ["precios"])
        lista = crear_lista_de_empresa(
            s,
            "Empresa ficticia",
            "J-00000000-0",
            base,
            [PrecioPropio(insumo.id, Decimal("11.25"), date(2026, 10, 5), "cotización ficticia")],
            moneda=moneda,
            fecha=date(2026, 10, 5),
            fuente="cotización ficticia",
            referencia=None,
        )
        creada.append(lista.id)

    _en_el_caso(ruta, escribir)
    return creada[0]


def test_crear_desde_la_lista_de_la_empresa_sin_tasa_da_201_en_usd(_entorno: Path) -> None:
    lista_id = _lista_de_empresa(_entorno)
    _declarar_usd_en_la_base(_entorno)
    navegador, ficha = con_cuenta(app, "ana")
    assert navegador.get("/v1/carpeta").json()["empresa"] == [
        {"id": lista_id, "nombre": "Empresa ficticia 2026-10-05", "moneda": "USD"}
    ]
    respuesta = navegador.post(
        "/v1/carpeta/lista-para-armar",
        json={"desde": "empresa", "lista_id": lista_id},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["aviso"] is None
    assert cuerpo["lista"]["nombre"] == f"Empresa ficticia 2026-10-05 al {HOY:%d/%m/%Y}"
    assert cuerpo["lista"]["moneda"] == "USD"
    precios = _filas(
        _entorno,
        "SELECT p.precio FROM precio_insumo p JOIN lista_precios l ON l.id = p.lista_id "
        f"WHERE l.nombre = 'Empresa ficticia 2026-10-05 al {HOY:%d/%m/%Y}'",
    )
    assert [Decimal(str(p)) for (p,) in precios] == [Decimal("11.25")]


def test_crear_desde_una_lista_que_no_es_de_empresa_es_409(_entorno: Path) -> None:
    _lista_base(_entorno, moneda="USD")
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.post(
        "/v1/carpeta/lista-para-armar",
        json={"desde": "empresa", "lista_id": 1},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 409
    assert (
        respuesta.json()["detalle"] == "La lista n.º 1 no es una lista de empresa de esta carpeta."
    )


def test_crear_desde_la_empresa_sin_decir_la_lista_es_422(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.post(
        "/v1/carpeta/lista-para-armar", json={"desde": "empresa"}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_422}
