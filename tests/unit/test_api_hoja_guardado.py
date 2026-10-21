"""S1 `POST /v1/hoja/borradores/{id}/guardar`: guardar el borrador como version (T10, 3d-1).

Contrato: `docs/bitacora/2026-10-20-hoja-3d1-contrato-rutas.md` (diseno §4.5, §6.3 y §9 P25 a P30,
P34). Es la primera ruta de la hoja que ESCRIBE versiones: todo ocurre en una sola transaccion que
empieza con `BEGIN IMMEDIATE`, con la sesion envuelta en `con_anexos_de_cadena` (sin eso la cadena
queda rota), todo o nada.

Oraculos a mano (ninguno sale del codigo bajo prueba): total de OF-001 2 703,86; con administracion
0,20 y utilidad 0,10 el total es CV 2 137,44 x 1,20 x 1,10 = 2 821,4208, el punto de equilibrio
0,825 x CV = 1 763,388 y 62,50 % de las ventas (diseno §9 P13, confirmados por el arbitro). Los
RegistroCambio, las versiones y la cadena se leen de la base con consultas propias; "nada escrito"
se comprueba con el volcado completo de la base antes y despues.

Diferencia deliberada con la clasica (D-5): la clasica guardaba aunque hubiera una version mas
nueva; S1 lo comprueba dentro de la transaccion y pide confirmar.
"""

from __future__ import annotations

import copy
import shutil
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.main import app
from aplicacion import hoja as copia
from aplicacion import hoja_borradores
from aplicacion.entrega import estado_de_la_cadena
from core import models
from core.budget import crear_proyecto
from core.budget.actualizacion import descartar_version
from core.budget.moneda import declarar_moneda
from core.catalog import CatalogoIncompleto, abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import sesiones
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
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
FALTA = (
    "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). "
    "Lo que no guardó se perdió: abra la versión otra vez."
)
OTRO_CASO = "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual."
REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo."
EXCEDE = "El cuerpo de la peticion excede el maximo de 20 MiB."
BASE = (
    "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro "
    "programa."
)
FORMA = (
    "El guardado no tiene la forma esperada: envíe rev (entero) y la fuente como texto de hasta "
    "300 caracteres."
)
SIN_FUENTE = "Escriba la fuente del cambio: por que se cambia y con que respaldo."
SIN_FUENTE_MEDIDA = "Escriba la fuente de la medida: de donde salen los datos (un plano, un acta)."
SIN_CAMBIOS = "No hay cambios para guardar: edite alguna celda primero."
HOJA_VACIA = (
    "La hoja esta vacia: describa o importe el espacio antes de guardar la primera version."
)
SOLO_LECTURA = (
    "Esta version esta en solo lectura: alguna de sus partidas ya no tiene composicion vigente "
    "en el catalogo, asi que recalcularla cambiaria sus precios."
)
CENTINELA = "VALOR-CENTINELA"
ORIGEN = "http://127.0.0.1:8000"
ID_AJENO = "a" * 22
MIB = 1024 * 1024
FUENTE = "acta de revision 7: el contrato fija la administracion en 20 %"
NUEVO = "Proyecto nuevo"
TOLERANCIA = D("0.01")
TOTAL_V002 = D("2821.4208")  # 2 137,44 x 1,20 x 1,10
PE_V002 = D("1763.388")  # 0,825 x 2 137,44
PORCENTAJE_V002 = D("62.50")
TOTAL_MEMORIA = D("2703.86")


# --- los casos de la prueba ---


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_guardado")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
    }


@pytest.fixture(autouse=True)
def _entorno(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalacion con cuentas y OF-001 (version 001) como caso por defecto, en la carpeta de
    datos temporal de la prueba (`tests/conftest.py`): nada toca `data/`."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["of001"], ruta)
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    dependencias.cerrar_motores()


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    """Todas las filas de todas las tablas, para comprobar que NO se escribio nada."""
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


@contextmanager
def _base(ruta: Path):
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            yield sesion
    finally:
        motor.dispose()


def _registros(ruta: Path, proyecto: str, codigo: str) -> list[tuple]:
    """Los RegistroCambio que dejo la version `codigo`, en orden."""
    registro = models.RegistroCambio
    with _base(ruta) as sesion:
        return [
            tuple(f)
            for f in sesion.execute(
                select(
                    registro.objeto,
                    registro.clave,
                    registro.campo,
                    registro.valor_anterior,
                    registro.valor_nuevo,
                    registro.fuente,
                    registro.responsable,
                )
                .join(models.Presupuesto, models.Presupuesto.id == registro.version_resultante_id)
                .join(models.Proyecto, models.Proyecto.id == models.Presupuesto.proyecto_id)
                .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
                .order_by(registro.id)
            )
        ]


def _cadena(ruta: Path, proyecto: str = NOMBRE_OF001):
    with _base(ruta) as sesion:
        return estado_de_la_cadena(sesion, proyecto)


def _codigos(navegador: TestClient, proyecto: str = NOMBRE_OF001) -> list[str]:
    respuesta = navegador.get("/v1/hoja/versiones", params={"proyecto": proyecto})
    assert respuesta.status_code == 200, respuesta.text
    return [v["codigo"] for v in respuesta.json()["versiones"]]


def _ana() -> tuple[TestClient, str]:
    return con_cuenta(app, "ana")


def _huella(ficha: str) -> str:
    return sesiones.huella_de(ficha)


def _abrir(navegador: TestClient, ficha: str, proyecto: str = NOMBRE_OF001, version="001") -> str:
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": proyecto, "version": version},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _vista(navegador: TestClient, id_: str, nombre: str) -> dict:
    return navegador.get(f"/v1/hoja/borradores/{id_}/vistas/{nombre}").json()


def _resumen(navegador: TestClient, id_: str) -> dict:
    return navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]


def _parametros(navegador, ficha, id_, rev, **cambios):
    textos = {
        "fcas": "6.00",
        "bono_alimentacion": "5.8100",
        "administracion": "0.15",
        "utilidad": "0.10",
    }
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/parametros",
        json={"rev": rev, **textos, **cambios},
        headers=protegida(ficha),
    )


def _espacio(navegador, ficha, id_, rev, tablas):
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/espacio",
        json={"rev": rev, "tablas": tablas},
        headers=protegida(ficha),
    )


def _guardar(navegador, ficha, id_, rev, fuente=FUENTE, **extra):
    return navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": rev, "fuente": fuente, **extra},
        headers=protegida(ficha),
    )


def _con_administracion(navegador, ficha, valor="0.20", **abrir) -> str:
    """Un borrador de OF-001 v001 con la administracion cambiada: `rev` 1, un cambio."""
    id_ = _abrir(navegador, ficha, **abrir)
    assert _parametros(navegador, ficha, id_, 0, administracion=valor).status_code == 200
    return id_


def _cerca(texto: str, esperado: Decimal) -> bool:
    return abs(D(texto) - esperado) <= TOLERANCIA


def _sin_circuitos() -> dict[str, list[dict[str, str]]]:
    """El espacio de OF-001 sin circuitos: un borrador en blanco no los tiene (se declaran al
    importar un plano) y un punto no puede citar uno que no existe."""
    tablas = copy.deepcopy(clasica.filas_desde_espacio(espacio_of001()))
    for punto in tablas["puntos"]:
        punto["circuito_id"] = ""
    return tablas


def _proyecto_nuevo(ruta: Path, nombre: str = NUEVO, moneda: str | None = None) -> None:
    with _base(ruta) as sesion:
        proyecto = crear_proyecto(sesion, nombre)
        if moneda is not None:
            declarar_moneda(sesion, proyecto, moneda, responsable="Plantilla <plantilla>")
        sesion.commit()
    dependencias.cerrar_motores()


def _en_blanco_con_el_espacio(navegador, ficha, nombre: str = NUEVO) -> str:
    """Un borrador en blanco del proyecto nuevo con el espacio de OF-001 y sus parametros: lo que
    se guarda como primera version."""
    id_ = _abrir(navegador, ficha, nombre, None)
    editado = _espacio(navegador, ficha, id_, 0, _sin_circuitos())
    assert editado.status_code == 200, editado.text
    assert _parametros(navegador, ficha, id_, 1).status_code == 200
    return id_


def _a_la_vez(*peticiones) -> list:
    """Lanza las peticiones juntas (una barrera las suelta a la vez) y devuelve sus respuestas."""
    respuestas: list = [None] * len(peticiones)
    inicio = threading.Barrier(len(peticiones))

    def correr(n: int) -> None:
        inicio.wait()
        respuestas[n] = peticiones[n]()

    hilos = [threading.Thread(target=correr, args=(n,)) for n in range(len(peticiones))]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=120)
        assert not hilo.is_alive()
    return respuestas


# --- 3d-B1 / P25: sin fuente ---


@pytest.mark.parametrize("fuente", ["", "   ", "\t\n"])
def test_guardar_sin_fuente_es_422_con_el_texto_de_la_clasica_y_no_escribe_nada(
    fuente, _entorno
) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    antes = _volcado(_entorno)
    respuesta = _guardar(navegador, ficha, id_, 1, fuente)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": SIN_FUENTE}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes
    assert _codigos(navegador) == ["001"]  # ["001"] antes y despues
    assert _resumen(navegador, id_)["guardado_como"] is None  # el borrador sigue abierto


# --- 3d-B2 / P26: guardar con fuente ---


def test_guardar_con_fuente_crea_la_002_con_su_registro_exacto_y_los_literales_de_la_memoria(
    _entorno,
) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    antes = _resumen(navegador, id_)
    assert _cerca(antes["total"]["exacto"], TOTAL_V002)

    respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"codigo", "proyecto", "cambios", "total", "primera", "mensaje"}
    assert (cuerpo["codigo"], cuerpo["proyecto"], cuerpo["cambios"], cuerpo["primera"]) == (
        "002",
        NOMBRE_OF001,
        1,
        False,
    )
    assert cuerpo["mensaje"] == "Se guardó la versión 002 con 1 cambios registrados."
    assert _cerca(cuerpo["total"]["exacto"], TOTAL_V002)  # 2 821,42 (P13)
    assert cuerpo["total"]["texto"] == "2821.42"
    # el registro por celda: objeto, clave, campo, antes, despues, fuente y responsable de la sesion
    assert _registros(_entorno, NOMBRE_OF001, "002") == [
        ("parametro", "administracion", "valor", "0.15", "0.20", FUENTE, "Ana <ana>")
    ]
    assert _codigos(navegador) == ["001", "002"]
    versiones = navegador.get("/v1/hoja/versiones", params={"proyecto": NOMBRE_OF001}).json()
    assert versiones["por_omision"] == "002"
    assert [(v["codigo"], v["origen"], v["vigente"]) for v in versiones["versiones"]] == [
        ("001", "", False),
        ("002", "001", True),
    ]
    # el borrador queda cerrado, con la version en que entro
    assert _resumen(navegador, id_)["guardado_como"] == "002"
    # lo guardado es lo que se ve al reabrir: total, punto de equilibrio y su porcentaje (P13)
    reabierto = _abrir(navegador, ficha, version="002")
    assert _cerca(_resumen(navegador, reabierto)["total"]["exacto"], TOTAL_V002)
    assert _resumen(navegador, reabierto)["cambios"] == 0
    equilibrio = _vista(navegador, reabierto, "equilibrio")
    assert _cerca(equilibrio["punto"]["exacto"], PE_V002)  # 1 763,39
    assert _cerca(equilibrio["porcentaje"]["exacto"], PORCENTAJE_V002)  # 62,50 %


def test_el_responsable_es_la_sesion_y_el_cuerpo_no_puede_decir_otro_p34() -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    respuesta = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": 1, "fuente": FUENTE, "responsable": "Otra Persona <otra>"},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 422 and respuesta.json() == {
        "detalle": FORMA
    }  # extra prohibido
    assert "Otra" not in respuesta.text and _codigos(navegador) == ["001"]


def test_el_responsable_de_lo_guardado_es_quien_tiene_la_sesion(_entorno) -> None:
    """El mismo guardado, hecho por la otra cuenta que arma (tomas debe cambiar su clave y no
    puede): la unica cuenta que arma y entra es `ana`; el responsable sale de `activa.usuario`."""
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    assert _guardar(navegador, ficha, id_, 1).status_code == 200
    (registro,) = _registros(_entorno, NOMBRE_OF001, "002")
    assert registro[-1] == "Ana <ana>"


# --- 3d-B3 / P27: la cadena queda integra (rojo visto del diseno §1.2) ---


def test_la_cadena_queda_integra_tras_guardar_por_la_api(_entorno) -> None:
    antes = _cadena(_entorno)
    assert antes.integra, antes.mensaje  # la plantilla parte de una cadena sana
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    assert _guardar(navegador, ficha, id_, 1).status_code == 200
    despues = _cadena(_entorno)
    assert despues.integra, despues.mensaje
    assert "íntegra" in despues.mensaje or "integra" in despues.mensaje.lower()
    # y guardar otra encima (la 003, que copia el espacio con su anexo) tambien la deja sana
    otro = _abrir(navegador, ficha, version="002")
    assert _parametros(navegador, ficha, otro, 0, administracion="0.25").status_code == 200
    assert _guardar(navegador, ficha, otro, 1).json()["codigo"] == "003"
    assert _cadena(_entorno).integra


# --- 3d-B4 / P28: todo o nada ---


def _roto(excepcion: Exception):
    def roto(*_args, **_kwargs):
        raise excepcion

    return roto


FALLOS = [
    pytest.param(
        OperationalError(
            "INSERT INTO esp_ambientes VALUES (?)",
            {},
            sqlite3.OperationalError("disk I/O error en /home/secreto/apu.db"),
        ),
        503,
        {"detalle": BASE},
        id="error-de-base",
    ),
    pytest.param(
        ValueError("el espacio no se pudo copiar"),
        409,
        {"detalle": "No se guardó nada: el espacio no se pudo copiar"},
        id="valueerror",
    ),
    pytest.param(
        CatalogoIncompleto("falta la lista de precios"),
        409,
        {"detalle": "No se guardó nada: falta la lista de precios"},
        id="catalogo-incompleto",
    ),
]


@pytest.mark.parametrize(("fallo", "estado", "cuerpo"), FALLOS)
def test_si_la_copia_del_espacio_falla_no_queda_nada_y_se_puede_reintentar(
    fallo, estado, cuerpo, monkeypatch: pytest.MonkeyPatch, _entorno
) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    antes = _volcado(_entorno)
    with monkeypatch.context() as parche:
        parche.setattr(copia, "guardar_espacio", _roto(fallo))
        respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == estado and respuesta.json() == cuerpo
    assert respuesta.headers["cache-control"] == "no-store"
    for prohibido in ("sqlite", "SELECT", "INSERT", "secreto", ".db"):
        assert prohibido not in respuesta.text
    assert _volcado(_entorno) == antes  # ninguna version, registro, fila esp_* ni eslabon
    assert _cadena(_entorno).integra
    assert _resumen(navegador, id_)["guardado_como"] is None  # el borrador sigue abierto
    reintento = _guardar(navegador, ficha, id_, 1)  # sin el fallo, la misma peticion pasa
    assert reintento.status_code == 200 and reintento.json()["codigo"] == "002"


# --- 3d-B5 / P29: solo lectura (409) y 3d-B6: sin cambios (422) ---


def test_una_version_en_solo_lectura_no_se_guarda_y_dice_por_que(_entorno) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    vivo.abierta = replace(vivo.abierta, solo_lectura=True)
    antes = _volcado(_entorno)
    respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": SOLO_LECTURA}
    assert _volcado(_entorno) == antes
    # como en la clasica, lo primero que se dice es lo que falta en el formulario
    assert _guardar(navegador, ficha, id_, 1, "").json() == {"detalle": SIN_FUENTE}


def test_sin_cambios_es_422_con_el_texto_del_motivo_y_tambien_si_se_revirtieron(_entorno) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _volcado(_entorno)
    respuesta = _guardar(navegador, ficha, id_, 0)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": SIN_CAMBIOS}
    assert _parametros(navegador, ficha, id_, 0, administracion="0.20").status_code == 200
    assert _parametros(navegador, ficha, id_, 1).status_code == 200  # vuelve a 0.15
    assert _resumen(navegador, id_)["cambios"] == 0
    assert _guardar(navegador, ficha, id_, 2).json() == {"detalle": SIN_CAMBIOS}
    # la falta de cambios se dice antes que la falta de fuente (el orden del motivo, H:1801)
    assert _guardar(navegador, ficha, id_, 2, "").json() == {"detalle": SIN_CAMBIOS}
    assert _volcado(_entorno) == antes


# --- 3d-B7 / D-5: una version mas nueva ---


MAS_NUEVA = (
    "Otra persona guardó la versión 002 después de que usted abrió la 001. Si guarda, su versión "
    "saldrá de la 001 y quedará como vigente sin lo de la 002."
)


def test_una_version_mas_nueva_pide_confirmar_y_con_la_confirmacion_guarda(_entorno) -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()  # otra ficha de la misma cuenta: otro borrador de la misma 001
    mio = _con_administracion(uno, ficha_uno, "0.30")
    de_otro = _con_administracion(otro, ficha_otro, "0.20")
    assert _guardar(otro, ficha_otro, de_otro, 1).json()["codigo"] == "002"  # se me adelantan
    assert _resumen(uno, mio)["version_mas_nueva"] == "002"  # la pantalla ya lo sabia
    antes = _volcado(_entorno)

    respuesta = _guardar(uno, ficha_uno, mio, 1)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": MAS_NUEVA, "version_mas_nueva": "002"}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes  # ni una fila
    assert _resumen(uno, mio)["guardado_como"] is None
    # la confirmacion tiene que ser un booleano de verdad
    assert _guardar(uno, ficha_uno, mio, 1, confirmar_version_mas_nueva="si").status_code == 422
    assert _volcado(_entorno) == antes

    confirmada = _guardar(uno, ficha_uno, mio, 1, confirmar_version_mas_nueva=True)
    assert confirmada.status_code == 200 and confirmada.json()["codigo"] == "003"
    versiones = uno.get("/v1/hoja/versiones", params={"proyecto": NOMBRE_OF001}).json()
    assert [(v["codigo"], v["origen"], v["vigente"]) for v in versiones["versiones"]] == [
        ("001", "", False),
        ("002", "001", False),
        ("003", "001", True),  # sale de la 001 y queda vigente, sin lo de la 002
    ]
    assert _cadena(_entorno).integra


def test_una_version_descartada_se_abre_y_guardar_desde_ella_pide_confirmar(_entorno) -> None:
    """Limite declarado: la regla es la de `Resumen.version_mas_nueva` (la vigente es otra que la
    abierta). Abrir a proposito una version descartada tambien pide confirmar."""
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    assert _guardar(navegador, ficha, id_, 1).json()["codigo"] == "002"
    with _base(_entorno) as sesion:
        descartar_version(sesion, NOMBRE_OF001, "002", date.today())
        sesion.commit()
    versiones = navegador.get("/v1/hoja/versiones", params={"proyecto": NOMBRE_OF001}).json()
    assert [(v["codigo"], v["descartada"], v["vigente"]) for v in versiones["versiones"]] == [
        ("001", False, True),
        ("002", True, False),
    ]
    descartada = _abrir(navegador, ficha, version="002")
    assert _parametros(navegador, ficha, descartada, 0, administracion="0.30").status_code == 200
    pide = _guardar(navegador, ficha, descartada, 1)
    assert pide.status_code == 409 and pide.json()["version_mas_nueva"] == "001"
    ok = _guardar(navegador, ficha, descartada, 1, confirmar_version_mas_nueva=True)
    assert ok.status_code == 200 and ok.json()["codigo"] == "003"
    assert _cadena(_entorno).integra


# --- 3d-B7: la carrera ---


def test_dos_guardados_a_la_vez_del_mismo_borrador_uno_gana_y_el_otro_ya_esta_guardado(
    _entorno,
) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    respuestas = _a_la_vez(
        lambda: _guardar(navegador, ficha, id_, 1), lambda: _guardar(navegador, ficha, id_, 1)
    )
    assert sorted(r.status_code for r in respuestas) == [200, 409], [r.text for r in respuestas]
    ganadora = next(r for r in respuestas if r.status_code == 200)
    perdedora = next(r for r in respuestas if r.status_code == 409)
    assert ganadora.json()["codigo"] == "002"
    assert perdedora.json() == {
        "detalle": "Este borrador ya se guardó como la versión 002; abra esa versión para seguir."
    }
    assert _codigos(navegador) == ["001", "002"]  # una sola version nueva
    assert len(_registros(_entorno, NOMBRE_OF001, "002")) == 1
    assert _cadena(_entorno).integra


def test_dos_personas_guardan_a_la_vez_desde_la_misma_version_uno_gana_y_el_otro_recibe_409(
    _entorno,
) -> None:
    """Dos borradores distintos de la misma 001: sin el bloqueo de escritura tomado ANTES de leer
    la vigente, los dos leerian "001" y uno fallaria con la base ocupada (503); con `BEGIN
    IMMEDIATE` el segundo espera, ve la 002 y recibe el 409 de "version mas nueva"."""
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()
    a = _con_administracion(uno, ficha_uno, "0.20")
    b = _con_administracion(otro, ficha_otro, "0.30")
    respuestas = _a_la_vez(
        lambda: _guardar(uno, ficha_uno, a, 1), lambda: _guardar(otro, ficha_otro, b, 1)
    )
    assert sorted(r.status_code for r in respuestas) == [200, 409], [r.text for r in respuestas]
    perdedora = next(r for r in respuestas if r.status_code == 409)
    assert perdedora.json()["version_mas_nueva"] == "002"
    assert _codigos(uno) == ["001", "002"]
    assert _cadena(_entorno).integra


def test_dos_personas_que_confirman_a_la_vez_obtienen_codigos_distintos(_entorno) -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()
    a = _con_administracion(uno, ficha_uno, "0.20")
    b = _con_administracion(otro, ficha_otro, "0.30")
    respuestas = _a_la_vez(
        lambda: _guardar(uno, ficha_uno, a, 1, confirmar_version_mas_nueva=True),
        lambda: _guardar(otro, ficha_otro, b, 1, confirmar_version_mas_nueva=True),
    )
    assert [r.status_code for r in respuestas] == [200, 200], [r.text for r in respuestas]
    assert sorted(r.json()["codigo"] for r in respuestas) == ["002", "003"]  # nunca dos "002"
    assert _codigos(uno) == ["001", "002", "003"]
    assert _cadena(_entorno).integra


def test_el_bloqueo_de_escritura_es_la_primera_sentencia_y_va_antes_de_cualquier_select(
    _entorno,
) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    motor = dependencias.obtener_motor(dependencias.url_de_ruta(_entorno))
    sentencias: list[str] = []

    def anotar(_conexion, _cursor, sentencia, *_resto) -> None:
        sentencias.append(sentencia.strip())

    event.listen(motor, "before_cursor_execute", anotar)
    try:
        respuesta = _guardar(navegador, ficha, id_, 1)
    finally:
        event.remove(motor, "before_cursor_execute", anotar)
    assert respuesta.status_code == 200, respuesta.text
    assert sentencias[0] == "BEGIN IMMEDIATE", sentencias[:3]
    primera_lectura = next(n for n, s in enumerate(sentencias) if s.upper().startswith("SELECT"))
    assert 0 < primera_lectura
    assert sentencias.count("BEGIN IMMEDIATE") == 1 and "BEGIN" not in sentencias
    assert "COMMIT" in sentencias


# --- 3d-B8: doble guardado ---


def test_el_borrador_guardado_queda_cerrado_y_no_se_guarda_ni_se_edita_otra_vez(_entorno) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    assert _guardar(navegador, ficha, id_, 1).status_code == 200
    despues = _volcado(_entorno)
    ya = {
        "detalle": "Este borrador ya se guardó como la versión 002; abra esa versión para seguir."
    }
    segundo = _guardar(navegador, ficha, id_, 1)
    assert segundo.status_code == 409 and segundo.json() == ya
    # ni siquiera con otro rev, con la confirmacion o con la fuente en blanco
    assert _guardar(navegador, ficha, id_, 9, "", confirmar_version_mas_nueva=True).json() == ya
    assert _parametros(navegador, ficha, id_, 1, utilidad="0.12").json() == ya
    assert _espacio(navegador, ficha, id_, 1, _sin_circuitos()).json() == ya
    assert _codigos(navegador) == ["001", "002"] and _volcado(_entorno) == despues


# --- la forma del cuerpo, antes de todo lo demas ---


CUERPOS_MALOS = [
    pytest.param({}, id="vacio"),
    pytest.param({"fuente": "x"}, id="sin-rev"),
    pytest.param({"rev": 1}, id="sin-fuente"),
    pytest.param({"rev": "uno", "fuente": "x"}, id="rev-texto"),
    pytest.param({"rev": True, "fuente": "x"}, id="rev-booleano"),
    pytest.param({"rev": -1, "fuente": "x"}, id="rev-negativo"),
    pytest.param({"rev": 1.0, "fuente": "x"}, id="rev-decimal"),
    pytest.param({"rev": 1, "fuente": {"a": CENTINELA}}, id="fuente-objeto"),
    pytest.param({"rev": 1, "fuente": CENTINELA * 40}, id="fuente-de-300-o-mas"),
    pytest.param({"rev": 1, "fuente": "x", "responsable": CENTINELA}, id="campo-extra"),
    pytest.param(
        {"rev": 1, "fuente": "x", "confirmar_version_mas_nueva": CENTINELA}, id="confirma"
    ),
]


@pytest.mark.parametrize("cuerpo", CUERPOS_MALOS)
def test_un_cuerpo_con_otra_forma_es_422_fijo_sin_eco_y_con_no_store(cuerpo, _entorno) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    antes = _volcado(_entorno)
    respuesta = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar", json=cuerpo, headers=protegida(ficha)
    )
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": FORMA}
    assert CENTINELA not in respuesta.text and respuesta.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes


def test_la_forma_se_juzga_antes_que_la_existencia_del_borrador() -> None:
    navegador, ficha = _ana()
    respuesta = navegador.post(
        f"/v1/hoja/borradores/{ID_AJENO}/guardar", json={"rev": "x"}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": FORMA}


def test_una_fuente_de_exactamente_300_caracteres_se_acepta_y_se_guarda_entera(_entorno) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    fuente = "f" * 300
    assert _guardar(navegador, ficha, id_, 1, fuente).status_code == 200
    assert _registros(_entorno, NOMBRE_OF001, "002")[0][5] == fuente


def test_el_rev_se_comprueba_antes_que_el_contenido_y_no_cambia_nada(_entorno) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    antes = _volcado(_entorno)
    for rev in (0, 2, 99):
        respuesta = _guardar(navegador, ficha, id_, rev, "")  # la fuente vacia no se llega a ver
        assert respuesta.status_code == 409 and respuesta.json() == {"detalle": REV_VIEJO}
    assert _volcado(_entorno) == antes


# --- 3d-B14 y B17 (acceso) para S1 ---


def test_sin_sesion_ni_clave_es_401() -> None:
    respuesta = cliente(app).post(
        f"/v1/hoja/borradores/{ID_AJENO}/guardar",
        json={"rev": 0, "fuente": "x"},
        headers={"Origin": ORIGEN},
    )
    assert respuesta.status_code == 401 and "detalle" in respuesta.json()
    assert respuesta.headers["cache-control"] == "no-store"


def test_rita_que_revisa_y_tomas_con_clave_temporal_no_pueden_guardar(_entorno) -> None:
    rita, ficha_rita = con_cuenta(app, "rita")
    respuesta = _guardar(rita, ficha_rita, ID_AJENO, 0)
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert respuesta.headers["cache-control"] == "no-store"
    tomas, ficha_tomas = con_cuenta(app, "tomas")
    assert _guardar(tomas, ficha_tomas, ID_AJENO, 0).status_code == 403


def test_la_clave_de_api_no_guarda(_entorno) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    antes = _volcado(_entorno)
    cabeceras = {CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN}
    respuesta = cliente(app).post(
        f"/v1/hoja/borradores/{id_}/guardar", json={"rev": 1, "fuente": FUENTE}, headers=cabeceras
    )
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": SOLO_CUENTA}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes and _resumen(navegador, id_)["guardado_como"] is None


def test_exige_csrf_y_origen_propio(_entorno) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    antes = _volcado(_entorno)
    ruta = f"/v1/hoja/borradores/{id_}/guardar"
    cuerpo = {"rev": 1, "fuente": FUENTE}
    assert navegador.post(ruta, json=cuerpo, headers={"Origin": ORIGEN}).status_code == 403
    ajeno = protegida(ficha, origen="http://evil.example")
    assert navegador.post(ruta, json=cuerpo, headers=ajeno).status_code == 403
    assert (
        navegador.post(ruta, json=cuerpo, headers=protegida(ficha, origen=None)).status_code == 403
    )
    assert _volcado(_entorno) == antes and _resumen(navegador, id_)["guardado_como"] is None


def test_el_borrador_de_otra_ficha_no_existe_y_no_se_guarda(_entorno) -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()  # otra ficha de la misma cuenta: otra huella
    id_ = _con_administracion(uno, ficha_uno)
    antes = _volcado(_entorno)
    ajeno = _guardar(otro, ficha_otro, id_, 1)
    inventado = _guardar(otro, ficha_otro, ID_AJENO, 1)
    assert ajeno.status_code == inventado.status_code == 404
    assert ajeno.json() == inventado.json() == {"detalle": FALTA}
    assert id_ not in ajeno.text and ajeno.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes and _resumen(uno, id_)["guardado_como"] is None


def test_un_id_con_forma_invalida_es_422_sin_eco() -> None:
    navegador, ficha = _ana()
    respuesta = _guardar(navegador, ficha, "corto", 0)
    assert respuesta.status_code == 422 and "corto" not in respuesta.text


def test_un_cuerpo_de_mas_de_20_mib_es_413_y_no_escribe(_entorno) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    antes = _volcado(_entorno)
    cabeceras = {**protegida(ficha), "Content-Type": "application/json"}
    enorme = b'{"rev":1,"fuente":"' + b"1" * (20 * MIB) + b'"}'
    respuesta = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar", content=enorme, headers=cabeceras
    )
    assert respuesta.status_code == 413 and respuesta.json() == {"detalle": EXCEDE}
    assert _volcado(_entorno) == antes


# --- 3d-B18: el cambio de caso ---


def test_tras_un_cambio_de_caso_forzado_guardar_es_409_y_ninguna_base_cambia(
    _casos, _entorno
) -> None:
    navegador, ficha = _ana()
    otro = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["of001"], otro)  # el mismo proyecto y la misma 001 en el caso nuevo
    preparar_base(_entorno)
    preparar_base(otro)
    id_ = _con_administracion(navegador, ficha)
    antes_a, antes_b = _volcado(_entorno), _volcado(otro)
    caso_web._elegidos[_huella(ficha)] = otro.resolve()  # el cambio sin pasar por `fijar`
    respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": OTRO_CASO}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes_a and _volcado(otro) == antes_b  # el caso nuevo, intacto
    assert hoja_borradores.obtener(_huella(ficha), id_).guardado_como is None


def test_cambiar_de_caso_olvida_el_borrador_y_guardar_da_404(_casos, _entorno) -> None:
    navegador, ficha = _ana()
    otro = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["of001"], otro)
    preparar_base(_entorno)
    preparar_base(otro)
    id_ = _con_administracion(navegador, ficha)
    antes_b = _volcado(otro)
    cambio = navegador.post(
        "/v1/casos/actual", json={"nombre": otro.name}, headers=protegida(ficha)
    )
    assert cambio.status_code == 200, cambio.text
    respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == 404 and respuesta.json() == {"detalle": FALTA}
    assert _volcado(otro) == antes_b


# --- 3d-B9 / P30: la primera version de un proyecto nuevo ---


def test_la_primera_version_de_un_proyecto_nuevo_es_la_001_con_la_memoria(_entorno) -> None:
    _proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    id_ = _en_blanco_con_el_espacio(navegador, ficha)
    previo = _resumen(navegador, id_)
    assert _cerca(previo["total"]["exacto"], TOTAL_MEMORIA)

    respuesta = _guardar(navegador, ficha, id_, 2)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["codigo"], cuerpo["proyecto"], cuerpo["cambios"], cuerpo["primera"]) == (
        "001",
        NUEVO,
        1,
        True,
    )
    assert _cerca(cuerpo["total"]["exacto"], TOTAL_MEMORIA)  # 2 703,86 (memoria de OF-001)
    assert cuerpo["total"]["exacto"] == previo["total"]["exacto"]  # 3d-B17: el de la vista previa
    assert cuerpo["mensaje"] == (
        f"Se guardó la primera versión 001 del proyecto {NUEVO} "
        f"(total {cuerpo['total']['texto']}). "
        "Quedó registrada su creación, con su fuente y su responsable."
    )
    # un solo RegistroCambio: version / creacion, con la fuente y la persona de la sesion
    assert _registros(_entorno, NUEVO, "001") == [
        ("version", "001", "creacion", "", "001", FUENTE, "Ana <ana>")
    ]
    assert _codigos(navegador, NUEVO) == ["001"]
    assert _resumen(navegador, id_)["guardado_como"] == "001"
    assert _cadena(_entorno, NUEVO).integra
    assert _cadena(_entorno).integra  # y la del proyecto de al lado, intacta
    # al reabrirla: la misma hoja, con su plan secuencial y su espacio copiado
    reabierto = _abrir(navegador, ficha, NUEVO, "001")
    assert _cerca(_resumen(navegador, reabierto)["total"]["exacto"], TOTAL_MEMORIA)
    assert _resumen(navegador, reabierto)["hay_plan"] is True
    assert (
        _vista(navegador, reabierto, "espacio")["filas"]
        == _vista(navegador, id_, "espacio")["filas"]
    )


def test_la_primera_version_sin_fuente_o_con_la_hoja_vacia_se_dice_y_no_escribe(_entorno) -> None:
    _proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    vacio = _abrir(navegador, ficha, NUEVO, None)
    antes = _volcado(_entorno)
    respuesta = _guardar(navegador, ficha, vacio, 0)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": HOJA_VACIA}
    lleno = _en_blanco_con_el_espacio(navegador, ficha)
    sin_fuente = _guardar(navegador, ficha, lleno, 2, "  ")
    assert sin_fuente.status_code == 422 and sin_fuente.json() == {"detalle": SIN_FUENTE_MEDIDA}
    assert _volcado(_entorno) == antes and _codigos(navegador, NUEVO) == []


def test_la_primera_version_que_otra_persona_ya_creo_es_422_ya_tiene_versiones(_entorno) -> None:
    _proyecto_nuevo(_entorno)
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()
    a = _en_blanco_con_el_espacio(uno, ficha_uno)
    b = _en_blanco_con_el_espacio(otro, ficha_otro)
    assert _guardar(uno, ficha_uno, a, 2).json()["codigo"] == "001"
    despues = _volcado(_entorno)
    respuesta = _guardar(otro, ficha_otro, b, 2)
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": f"El proyecto {NUEVO!r} ya tiene versiones: abra una y use Guardar version."
    }
    assert _volcado(_entorno) == despues and _codigos(uno, NUEVO) == ["001"]


def test_la_primera_version_sin_lista_vigente_a_la_fecha_lo_dice_y_no_inventa_precios(
    _entorno,
) -> None:
    _proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    id_ = _en_blanco_con_el_espacio(navegador, ficha)
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    vivo.borrador = replace(vivo.borrador, fecha=date(2000, 1, 1))
    antes = _volcado(_entorno)
    respuesta = _guardar(navegador, ficha, id_, 2)
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"].startswith(
        "No hay una lista de precios vigente al 01/01/2000"
    )
    assert _volcado(_entorno) == antes


def test_la_primera_version_con_una_lista_de_otra_moneda_dice_cual_es_cada_una(_entorno) -> None:
    _proyecto_nuevo(_entorno, "Proyecto en bolivares", moneda="VES")
    navegador, ficha = _ana()
    id_ = _en_blanco_con_el_espacio(navegador, ficha, "Proyecto en bolivares")
    antes = _volcado(_entorno)
    respuesta = _guardar(navegador, ficha, id_, 2)
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"].startswith(
        "El proyecto 'Proyecto en bolivares' esta en VES y la lista "
        "'Lista MaPreX jul-2026 (OF-001)' en USD"
    )
    assert _volcado(_entorno) == antes


def test_si_la_copia_del_espacio_falla_la_primera_version_tampoco_queda(
    monkeypatch: pytest.MonkeyPatch, _entorno
) -> None:
    _proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    id_ = _en_blanco_con_el_espacio(navegador, ficha)
    antes = _volcado(_entorno)
    with monkeypatch.context() as parche:
        parche.setattr(copia, "guardar_espacio", _roto(RuntimeError("disco lleno")))
        # una excepcion inesperada es el 500 generico de la aplicacion (sin detalle), no un dato
        respuesta = _guardar(navegador, ficha, id_, 2)
    assert respuesta.status_code == 500 and "disco" not in respuesta.text
    assert _volcado(_entorno) == antes and _codigos(navegador, NUEVO) == []
    assert _guardar(navegador, ficha, id_, 2).json()["codigo"] == "001"  # y se puede reintentar


# --- 3d-B10: R17 en el guardado ---


def test_la_version_guardada_con_un_punto_sin_fuente_conserva_el_hallazgo_r17(_entorno) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = copy.deepcopy(_vista(navegador, id_, "espacio")["filas"])
    next(f for f in tablas["puntos"] if f["id"] == "P1")["fuente_id"] = ""
    assert _espacio(navegador, ficha, id_, 0, tablas).status_code == 200
    assert _guardar(navegador, ficha, id_, 1).json()["codigo"] == "002"
    with _base(_entorno) as sesion:
        hallazgos = sesion.execute(
            select(
                models.Hallazgo.severidad, models.Hallazgo.origen_ids, models.Hallazgo.descripcion
            )
            .join(models.Presupuesto, models.Presupuesto.id == models.Hallazgo.presupuesto_id)
            .join(models.Proyecto, models.Proyecto.id == models.Presupuesto.proyecto_id)
            .where(
                models.Proyecto.nombre == NOMBRE_OF001,
                models.Presupuesto.codigo == "002",
                models.Hallazgo.regla == "R17",
            )
        ).all()
        sin_r17 = sesion.scalar(
            select(models.Hallazgo.id)
            .join(models.Presupuesto, models.Presupuesto.id == models.Hallazgo.presupuesto_id)
            .join(models.Proyecto, models.Proyecto.id == models.Presupuesto.proyecto_id)
            .where(
                models.Proyecto.nombre == NOMBRE_OF001,
                models.Presupuesto.codigo == "001",
                models.Hallazgo.regla == "R17",
            )
        )
    assert len(hallazgos) == 1 and "esp_puntos:P1" in hallazgos[0][1]
    assert "El punto P1 (lavamanos) no tiene fuente" in hallazgos[0][2]
    assert sin_r17 is None  # la 001 no tenia ninguno


# --- 3d-B16: errores de base ---


def test_un_error_de_base_al_guardar_es_503_fijo_sin_sql_ni_rutas(
    monkeypatch: pytest.MonkeyPatch, _entorno
) -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    antes = _volcado(_entorno)
    fallo = OperationalError(
        "SELECT presupuesto.id FROM presupuesto WHERE secreto = ?",
        {},
        sqlite3.OperationalError("unable to open database file C:/datos/privados/apu.db"),
    )
    with monkeypatch.context() as parche:
        parche.setattr(copia, "siguiente_codigo", _roto(fallo))
        respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == 503 and respuesta.json() == {"detalle": BASE}
    assert respuesta.headers["cache-control"] == "no-store"
    for prohibido in ("sqlite", "SELECT", "presupuesto", "privados", "apu.db"):
        assert prohibido not in respuesta.text
    assert _volcado(_entorno) == antes and _cadena(_entorno).integra


# --- ningun float, no-store ---


def _sin_float(valor) -> None:
    if isinstance(valor, float):
        raise AssertionError(f"float en el JSON: {valor!r}")
    if isinstance(valor, dict):
        for v in valor.values():
            _sin_float(v)
    elif isinstance(valor, list):
        for v in valor:
            _sin_float(v)


def test_ningun_numero_del_json_es_float_y_el_total_es_texto() -> None:
    import json

    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == 200
    _sin_float(json.loads(respuesta.text, parse_float=lambda t: float("nan")))
    cuerpo = respuesta.json()
    assert isinstance(cuerpo["total"]["exacto"], str) and isinstance(cuerpo["cambios"], int)


def test_no_store_en_exito_404_409_y_422_de_guardar() -> None:
    navegador, ficha = _ana()
    id_ = _con_administracion(navegador, ficha)
    respuestas = [
        _guardar(navegador, ficha, id_, 1, ""),  # 422 dominio
        _guardar(navegador, ficha, ID_AJENO, 1),  # 404
        _guardar(navegador, ficha, id_, 0),  # 409 rev
        navegador.post(f"/v1/hoja/borradores/{id_}/guardar", json={}, headers=protegida(ficha)),
        _guardar(navegador, ficha, id_, 1),  # 200
        _guardar(navegador, ficha, id_, 1),  # 409 ya guardado
    ]
    assert [r.status_code for r in respuestas] == [422, 404, 409, 422, 200, 409]
    assert all(r.headers["cache-control"] == "no-store" for r in respuestas)
