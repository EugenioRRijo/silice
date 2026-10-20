"""E6 a E11: el APU editable, el cambio de insumo, los cambios, retomar y reemplazar (T10, 3c-3).

Contrato: `docs/bitacora/2026-10-19-hoja-3c3-contrato-rutas.md` (diseno §3.2, §4.1, §4.4, §6.2).

* E6 `PUT .../apu/{partida}`: rendimiento y cantidad por linea de un APU (3c-B10).
* E7 `POST .../apu/{partida}/insumo`: cambiar el insumo de una linea (3c-B11, P21).
* E8 `GET .../insumos`: los candidatos de la lista de precios de la version.
* E9 `GET .../cambios`: la lista de `cambios_entre` para el modal de guardar.
* E10 `GET /v1/hoja/borradores` y E11 `POST /v1/hoja/borradores` con `reemplazar`: retomar tras
  recargar y cambiar de version sin perder nada (3c-B14, P23).
* 3c-B13 completa (dos hilos con el mismo `rev`: gana exactamente uno), 3c-B18 (medicion, solo
  registra) y 3c-B19 ampliada a E6 a E11.

Oraculos a mano (ninguno sale del codigo bajo prueba; los de AF-LLAVE estan deducidos en
`test_aplicacion_hoja_paridad_apu.py`): total de OF-001 2 703,86; AF-LLAVE vale 3 unidades en la
version; su CD es 10,433785 y su PU 13,198738025. Con 2 llaves por unidad: PU 23,000337525 (delta
del total 3 x 9,8015995 = 29,4047985); con rendimiento 10: PU 16,59587655 (delta 3 x 3,397138525 =
10,191415575); con el pegamento (34,5694) en lugar de la llave: PU 47,1274295250 (delta 3 x
33,9286915 = 101,7860745). Un cambio de APU del diseno §6.2 3c-B10: `materiales, fila 2: la
cantidad no puede ser negativa`.
"""

from __future__ import annotations

import copy
import shutil
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from aplicacion import hoja_borradores
from aplicacion.hoja import cambios_entre
from core.budget import crear_proyecto
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from scripts import medir_rnf11 as medir
from seguridad import sesiones
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    plantilla_of001,
    plantilla_ti001,
)
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
SOLO_CUENTA = "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."
FALTA = (
    "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). "
    "Lo que no guardó se perdió: abra la versión otra vez."
)
OTRO_CASO = "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual."
REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo."
EXCEDE = "El cuerpo de la peticion excede el maximo de 20 MiB."
FORMA_APU = (
    "El APU no tiene la forma esperada: envíe el rendimiento y las cantidades de materiales, "
    "equipos y mano de obra, cada una como texto de hasta 500 caracteres, con no más de 500 "
    "líneas por rubro."
)
FORMA_INSUMO = (
    "El cambio de insumo no tiene la forma esperada: envíe tipo, indice (entero), insumo "
    "(código) y rev."
)
FORMA_BUSQUEDA = (
    "La búsqueda de insumos no tiene la forma esperada: indique tipo (material, equipo o "
    "mano_obra), un texto de hasta 500 caracteres y un límite de 1 a 301."
)
PARTIDA_FALTA = "Esa partida no tiene APU en este borrador: vuelva a cargar la lista de partidas."
SIN_VERSION = "Abra una version guardada: los insumos se eligen de su lista de precios."
CENTINELA = "VALOR-CENTINELA"
ORIGEN = "http://127.0.0.1:8000"
ID_AJENO = "a" * 22
MIB = 1024 * 1024
LLAVE = "AF-LLAVE|esp_fuentes:F1;esp_fuentes:FC1;esp_puntos:P1;esp_puntos:P2;esp_puntos:PC1"
DESC_LLAVE = "Llave de paso de bola PVC 1/2 pulg [PLOG26]"
DESC_PEGAMENTO = "Pegamento para PVC 1/4 gl [MT539]"
APU_LLAVE = {"rendimiento": "20", "materiales": ["1"], "equipos": ["1"], "mano_obra": ["1", "1"]}
TOLERANCIA = D("0.001")


# --- los casos de la prueba ---


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_apu")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
        "ti001": plantilla_ti001(carpeta / "ti001.db"),
    }


@pytest.fixture(autouse=True)
def _entorno(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalacion con cuentas y OF-001 (version 001) como caso por defecto."""
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


def _poner(origen: Path) -> Path:
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    shutil.copyfile(origen, ruta)
    return ruta


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


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


def _abrir_con(navegador: TestClient, ficha: str, **cuerpo):
    cuerpo = {"proyecto": NOMBRE_OF001, "version": "001", **cuerpo}
    return navegador.post("/v1/hoja/borradores", json=cuerpo, headers=protegida(ficha))


def _vista(navegador: TestClient, id_: str, nombre: str, consulta: str = "") -> dict:
    return navegador.get(f"/v1/hoja/borradores/{id_}/vistas/{nombre}{consulta}").json()


def _resumen(navegador: TestClient, id_: str) -> dict:
    return navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]


def _total(resumen: dict) -> Decimal:
    return D(resumen["total"]["exacto"])


def _con_proyecto_nuevo(ruta: Path) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as sesion:
        crear_proyecto(sesion, "Proyecto nuevo")
        sesion.commit()
    motor.dispose()
    dependencias.cerrar_motores()


def _ruta_apu(id_: str, partida: str, resto: str = "") -> str:
    return f"/v1/hoja/borradores/{id_}/apu/{quote(partida, safe='')}{resto}"


def _apu(navegador, ficha, id_, rev, partida="AF-LLAVE", **cambios):
    return navegador.put(
        _ruta_apu(id_, partida),
        json={"rev": rev, **APU_LLAVE, **cambios},
        headers=protegida(ficha),
    )


def _insumo(navegador, ficha, id_, rev, partida="AF-LLAVE", **cuerpo):
    cuerpo = {"tipo": "material", "indice": 0, "insumo": "MAT-002", **cuerpo}
    return navegador.post(
        _ruta_apu(id_, partida, "/insumo"), json={"rev": rev, **cuerpo}, headers=protegida(ficha)
    )


def _insumos(navegador, id_, consulta: str):
    return navegador.get(f"/v1/hoja/borradores/{id_}/insumos{consulta}")


def _cambios(navegador, id_):
    return navegador.get(f"/v1/hoja/borradores/{id_}/cambios")


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


def _cantidades(navegador, ficha, id_, rev, filas):
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/cantidades",
        json={"rev": rev, "filas": filas},
        headers=protegida(ficha),
    )


def _espacio(navegador, ficha, id_, rev, alto: str):
    tablas = copy.deepcopy(_vista(navegador, id_, "espacio")["filas"])
    tablas["ambientes"][0]["alto"] = alto
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/espacio",
        json={"rev": rev, "tablas": tablas},
        headers=protegida(ficha),
    )


# --- E6: el APU editable (3c-B10, P21) ---


def test_e6_dos_llaves_por_unidad_suben_el_total_29_4047985_y_registran_un_solo_cambio() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _resumen(navegador, id_)
    assert abs(_total(antes) - D("2703.86")) <= D("0.01")
    respuesta = _apu(navegador, ficha, id_, 0, materiales=["2"])
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == cuerpo["resumen"]["rev"] == 1 and cuerpo["resumen"]["cambios"] == 1
    assert abs(_total(cuerpo["resumen"]) - _total(antes) - D("29.4047985")) <= TOLERANCIA
    detalle = cuerpo["apu"]["detalle"]
    assert cuerpo["apu"]["seleccionada"] == "AF-LLAVE" and detalle["codigo"] == "AF-LLAVE"
    materiales = next(g for g in detalle["grupos"] if g["clave"] == "materiales")
    assert materiales["filas"][0]["cantidad"] == "2"
    assert abs(D(detalle["metricas"]["precio_unitario"]["exacto"]) - D("23.000337525")) <= D(
        "0.0000001"
    )
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    cambios = cambios_entre(vivo.abierta.borrador, vivo.borrador)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("apu", f"AF-LLAVE|{DESC_LLAVE}", "cantidad", "1", "2")
    ]


def test_e6_la_respuesta_es_lo_mismo_que_piden_despues_r7_y_r3() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _apu(navegador, ficha, id_, 0, materiales=["2"]).json()
    assert _vista(navegador, id_, "apu", "?partida=AF-LLAVE") == respuesta["apu"]
    assert _resumen(navegador, id_) == respuesta["resumen"]


def test_e6_el_rendimiento_10_sube_el_total_10_191415575_y_registra_el_rendimiento() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _total(_resumen(navegador, id_))
    cuerpo = _apu(navegador, ficha, id_, 0, rendimiento="10").json()
    assert abs(_total(cuerpo["resumen"]) - antes - D("10.191415575")) <= TOLERANCIA
    assert cuerpo["apu"]["detalle"]["rendimiento"] == "10"
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    cambios = cambios_entre(vivo.abierta.borrador, vivo.borrador)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("apu", "AF-LLAVE", "rendimiento", "20", "10")
    ]


def test_e6_el_mismo_apu_no_es_un_cambio_ni_sube_el_rev() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    igual = _apu(navegador, ficha, id_, 0)  # lo mismo que tiene
    assert igual.status_code == 200 and igual.json()["rev"] == 0
    assert igual.json()["resumen"]["cambios"] == 0
    for texto in ("1.000", "1.0"):  # otra forma de escribir lo mismo
        assert _apu(navegador, ficha, id_, 0, materiales=[texto]).json()["rev"] == 0


def test_e6_volver_a_la_cantidad_original_deja_cero_cambios() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    assert _apu(navegador, ficha, id_, 0, materiales=["2"]).json()["resumen"]["cambios"] == 1
    vuelta = _apu(navegador, ficha, id_, 1, materiales=["1"]).json()
    assert vuelta["rev"] == 2 and vuelta["resumen"]["cambios"] == 0
    assert abs(_total(vuelta["resumen"]) - D("2703.86")) <= D("0.01")


def test_e6_una_partida_con_barra_en_el_codigo_viaja_en_la_ruta() -> None:
    """AF-TUB-PVC-1/2 tiene dos materiales: la fila 2 es el pegamento (0,01 por metro)."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    partida = "AF-TUB-PVC-1/2"
    cantidad = D(
        next(f for f in _vista(navegador, id_, "presupuesto")["filas"] if f["partida"] == partida)[
            "cantidad"
        ]
    )
    antes = _total(_resumen(navegador, id_))
    cuerpo = {"rendimiento": "30", "materiales": ["1", "0.02"], "equipos": ["1"]}
    cuerpo["mano_obra"] = ["1", "1"]
    respuesta = navegador.put(
        _ruta_apu(id_, partida), json={"rev": 0, **cuerpo}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 200, respuesta.text
    # 0,01 de pegamento mas por metro: 0,01 x 34,5694 x 1,15 x 1,10 por la cantidad del renglon
    esperado = D("0.01") * D("34.5694") * D("1.15") * D("1.10") * cantidad
    assert abs(_total(respuesta.json()["resumen"]) - antes - esperado) <= TOLERANCIA
    assert respuesta.json()["apu"]["seleccionada"] == partida
    errado = navegador.put(
        _ruta_apu(id_, partida),
        json={"rev": 1, **cuerpo, "materiales": ["1", "-1"]},
        headers=protegida(ficha),
    )
    assert errado.status_code == 422
    assert errado.json() == {"detalle": "materiales, fila 2: la cantidad no puede ser negativa"}


@pytest.mark.parametrize(
    ("cambios", "detalle"),
    [
        ({"materiales": ["-1"]}, "materiales, fila 1: la cantidad no puede ser negativa"),
        ({"mano_obra": ["1", "-2"]}, "mano de obra, fila 2: la cantidad no puede ser negativa"),
        (
            {"materiales": ["2,5"]},
            "materiales, fila 1: cantidad: '2,5' no es un numero decimal valido",
        ),
        ({"equipos": ["x"]}, "equipos, fila 1: cantidad: 'x' no es un numero decimal valido"),
        ({"rendimiento": "0,5"}, "rendimiento: '0,5' no es un numero decimal valido"),
        (
            {"materiales": ["1", "1"]},
            "materiales: la tabla tiene 2 lineas y el APU 1; en la hoja solo se edita la "
            "cantidad de cada linea (para agregar o quitar una, use Componer)",
        ),
        (
            {"mano_obra": []},
            "mano de obra: la tabla tiene 0 lineas y el APU 2; en la hoja solo se edita la "
            "cantidad de cada linea (para agregar o quitar una, use Componer)",
        ),
    ],
)
def test_e6_un_dato_invalido_es_422_con_el_texto_de_la_clasica_y_nada_cambia(
    cambios, detalle
) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _vista(navegador, id_, "apu", "?partida=AF-LLAVE")
    respuesta = _apu(navegador, ficha, id_, 0, **cambios)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": detalle}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _vista(navegador, id_, "apu", "?partida=AF-LLAVE") == antes
    assert _resumen(navegador, id_)["rev"] == 0
    assert _apu(navegador, ficha, id_, 0, materiales=["2"]).status_code == 200  # rev no gastado


def test_e6_un_rendimiento_cero_es_422_con_el_texto_del_modelo() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _apu(navegador, ficha, id_, 0, rendimiento="0")
    assert respuesta.status_code == 422 and respuesta.json()["detalle"]
    assert _resumen(navegador, id_)["rev"] == 0


def test_e6_una_partida_sin_apu_es_404_fijo_despues_de_rev_y_sin_eco() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _apu(navegador, ficha, id_, 0, partida="NO-EXISTE-" + CENTINELA)
    assert respuesta.status_code == 404 and respuesta.json() == {"detalle": PARTIDA_FALTA}
    assert respuesta.headers["cache-control"] == "no-store" and CENTINELA not in respuesta.text
    assert _parametros(navegador, ficha, id_, 0, utilidad="0.12").status_code == 200  # rev 1
    rezagada = _apu(navegador, ficha, id_, 0, partida="NO-EXISTE")
    assert rezagada.status_code == 409 and rezagada.json() == {"detalle": REV_VIEJO}


def test_e6_el_rev_se_comprueba_antes_que_el_contenido() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _parametros(navegador, ficha, id_, 0, utilidad="0.12")
    malo = _apu(navegador, ficha, id_, 0, materiales=["-1"])
    assert malo.status_code == 409 and malo.json() == {"detalle": REV_VIEJO}


def test_e6_el_cambio_se_ve_tambien_en_el_presupuesto_y_el_plan_ajusta_el_total() -> None:
    """Editar un APU no toca el plan: la curva sigue cerrando en el total nuevo."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    cuerpo = _apu(navegador, ficha, id_, 0, materiales=["2"]).json()
    plan = _vista(navegador, id_, "plan")
    assert D(plan["curva"][-1]["acumulado"]["exacto"]) == _total(cuerpo["resumen"])


def test_e6_en_ti001_una_partida_sin_espacio_tambien_se_edita(_casos) -> None:
    _poner(_casos["ti001"])
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha, NOMBRE_TI001, "TI-001")
    apu = _vista(navegador, id_, "apu", "?partida=TI-RACK")["detalle"]
    cuerpo = {
        "rendimiento": apu["rendimiento"],
        "materiales": [
            f["cantidad"] for g in apu["grupos"] if g["clave"] == "materiales" for f in g["filas"]
        ],
        "equipos": [
            f["cantidad"] for g in apu["grupos"] if g["clave"] == "equipos" for f in g["filas"]
        ],
        "mano_obra": [
            f["cantidad"] for g in apu["grupos"] if g["clave"] == "mano de obra" for f in g["filas"]
        ],
    }
    cuerpo["rendimiento"] = "2"
    respuesta = navegador.put(
        _ruta_apu(id_, "TI-RACK"), json={"rev": 0, **cuerpo}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["resumen"]["cambios"] == 1


# --- E6 y E7: la forma del cuerpo es 422 fijo, sin eco, antes del resto ---


@pytest.mark.parametrize(
    "cuerpo",
    [
        {**APU_LLAVE},  # sin rev
        {"rev": "0", **APU_LLAVE},
        {"rev": -1, **APU_LLAVE},
        {"rev": 0, "materiales": ["1"], "equipos": ["1"], "mano_obra": ["1", "1"]},
        {"rev": 0, **APU_LLAVE, "materiales": "1"},
        {"rev": 0, **APU_LLAVE, "materiales": [1]},
        {"rev": 0, **APU_LLAVE, "rendimiento": 20},
        {"rev": 0, **APU_LLAVE, "rendimiento": "2" * 501},
        {"rev": 0, **APU_LLAVE, "equipos": ["1" * 501]},
        {"rev": 0, **APU_LLAVE, "mano_obra": ["1"] * 501},
        {"rev": 0, **APU_LLAVE, "otro": CENTINELA},
        {"rev": 0, **APU_LLAVE, "materiales": [CENTINELA * 100]},
    ],
)
def test_e6_un_cuerpo_con_otra_forma_es_422_fijo_sin_eco_y_con_no_store(cuerpo) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = navegador.put(_ruta_apu(id_, "AF-LLAVE"), json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA_APU} and CENTINELA not in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert _resumen(navegador, id_)["rev"] == 0


def test_e6_exactamente_los_topes_de_forma_se_aceptan() -> None:
    """500 lineas de 500 caracteres no son error de forma: la ruta contesta el 422 de dominio."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _apu(navegador, ficha, id_, 0, materiales=["1" * 500] * 500)
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"].startswith("materiales: la tabla tiene 500 lineas")


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"tipo": "material", "indice": 0},  # sin insumo
        {"rev": 0, "indice": 0, "insumo": "MAT-002"},  # sin tipo
        {"rev": 0, "tipo": "material", "insumo": "MAT-002"},  # sin indice
        {"rev": 0, "tipo": "material", "indice": "0", "insumo": "MAT-002"},
        {"rev": 0, "tipo": "material", "indice": 0.5, "insumo": "MAT-002"},
        {"rev": 0, "tipo": "material", "indice": -1, "insumo": "MAT-002"},
        {"rev": 0, "tipo": "material", "indice": True, "insumo": "MAT-002"},
        {"rev": 0, "tipo": "material", "indice": 0, "insumo": 7},
        {"rev": 0, "tipo": "m" * 501, "indice": 0, "insumo": "MAT-002"},
        {"rev": 0, "tipo": "material", "indice": 0, "insumo": "X" * 501},
        {"rev": 0, "tipo": "material", "indice": 0, "insumo": "MAT-002", "otro": CENTINELA},
        {"rev": "0", "tipo": "material", "indice": 0, "insumo": "MAT-002"},
    ],
)
def test_e7_un_cuerpo_con_otra_forma_es_422_fijo_sin_eco_y_con_no_store(cuerpo) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = navegador.post(
        _ruta_apu(id_, "AF-LLAVE", "/insumo"), json=cuerpo, headers=protegida(ficha)
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA_INSUMO} and CENTINELA not in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert _resumen(navegador, id_)["rev"] == 0


# --- E7: cambiar el insumo de una linea (3c-B11, P21) ---


def test_e7_el_pegamento_en_lugar_de_la_llave_conserva_la_cantidad_y_sube_101_7860745() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _total(_resumen(navegador, id_))
    candidatos = _insumos(navegador, id_, "?tipo=material&texto=pegamento").json()
    assert [i["codigo"] for i in candidatos["insumos"]] == ["MAT-002"]
    respuesta = _insumo(navegador, ficha, id_, 0, insumo="MAT-002")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == cuerpo["resumen"]["rev"] == 1 and cuerpo["resumen"]["cambios"] == 2
    assert abs(_total(cuerpo["resumen"]) - antes - D("101.7860745")) <= TOLERANCIA
    materiales = next(g for g in cuerpo["apu"]["detalle"]["grupos"] if g["clave"] == "materiales")
    fila = materiales["filas"][0]
    assert (fila["descripcion"], fila["unidad"], fila["cantidad"], fila["precio"]) == (
        DESC_PEGAMENTO,
        "env",
        "1",
        "34.5694",
    )
    precio = D(cuerpo["apu"]["detalle"]["metricas"]["precio_unitario"]["exacto"])
    assert abs(precio - D("47.127429525")) <= D("0.0000001")
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    cambios = cambios_entre(vivo.abierta.borrador, vivo.borrador)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("apu", f"AF-LLAVE|{DESC_LLAVE}", "insumo", DESC_LLAVE, DESC_PEGAMENTO),
        ("apu", f"AF-LLAVE|{DESC_LLAVE}", "precio", "7.7483", "34.5694"),
    ]
    assert _vista(navegador, id_, "apu", "?partida=AF-LLAVE") == cuerpo["apu"]
    assert _resumen(navegador, id_) == cuerpo["resumen"]


def test_e7_el_tecnico_en_lugar_del_plomero_cambia_el_sueldo_y_no_la_cantidad() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _total(_resumen(navegador, id_))
    tecnico = _insumos(navegador, id_, "?tipo=mano_obra&texto=tecnico").json()["insumos"][0]
    assert (tecnico["codigo"], tecnico["precio"]["exacto"]) == ("MO-005", "10.0000")
    respuesta = _insumo(navegador, ficha, id_, 0, tipo="mano_obra", indice=0, insumo="MO-005")
    assert respuesta.status_code == 200, respuesta.text
    # CD 10,433785 -> 13,168090 (+2,734305): el delta del total es 3 x 2,734305 x 1,15 x 1,10
    esperado = 3 * D("2.734305") * D("1.15") * D("1.10")
    assert abs(_total(respuesta.json()["resumen"]) - antes - esperado) <= TOLERANCIA
    obreros = next(
        g for g in respuesta.json()["apu"]["detalle"]["grupos"] if g["clave"] == "mano de obra"
    )
    assert obreros["filas"][0]["cantidad"] == "1" and obreros["filas"][0]["sueldo"] == "10.0000"


def test_e7_un_insumo_que_la_lista_no_valora_o_de_otro_tipo_es_422_y_nada_cambia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    for insumo in ("MAT-999", "EQU-001", ""):  # inexistente, de otro tipo, vacio
        respuesta = _insumo(navegador, ficha, id_, 0, insumo=insumo)
        assert respuesta.status_code == 422, insumo
        assert respuesta.json() == {
            "detalle": f"El insumo {insumo!r} no esta en la lista de precios de la version 001 "
            "(o no es de tipo material): elijalo de la lista."
        }
    assert _resumen(navegador, id_)["rev"] == 0


@pytest.mark.parametrize(
    ("cuerpo", "detalle"),
    [
        (
            {"tipo": "xx"},
            "tipo de linea 'xx' desconocido; se espera uno de ('material', 'equipo', 'mano_obra')",
        ),
        ({"indice": 1}, "la linea 2 no existe: el grupo material tiene 1 lineas"),
        (
            {"tipo": "mano_obra", "indice": 5, "insumo": "MO-005"},
            "la linea 6 no existe: el grupo mano_obra tiene 2 lineas",
        ),
    ],
)
def test_e7_un_tipo_o_una_linea_que_no_existen_son_422_con_el_texto_de_la_clasica(
    cuerpo, detalle
) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _insumo(navegador, ficha, id_, 0, **cuerpo)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": detalle}
    assert _resumen(navegador, id_)["rev"] == 0


def test_e7_el_mismo_insumo_de_la_linea_no_es_un_cambio() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    llave = _insumos(navegador, id_, "?tipo=material&texto=llave").json()["insumos"][0]
    assert llave["codigo"] == "MAT-007"
    igual = _insumo(navegador, ficha, id_, 0, insumo="MAT-007")
    assert igual.status_code == 200 and igual.json()["rev"] == 0
    assert igual.json()["resumen"]["cambios"] == 0


def test_e7_sin_version_abierta_es_409_y_se_dice_antes_que_la_partida() -> None:
    navegador, ficha = _ana()
    _con_proyecto_nuevo(config.ruta_caso_por_defecto())
    id_ = _abrir(navegador, ficha, "Proyecto nuevo", None)
    for partida in ("AF-LLAVE", "NO-EXISTE"):
        respuesta = _insumo(navegador, ficha, id_, 0, partida=partida)
        assert respuesta.status_code == 409 and respuesta.json() == {"detalle": SIN_VERSION}
    rezagada = _insumo(navegador, ficha, id_, 7)
    assert rezagada.status_code == 409 and rezagada.json() == {"detalle": REV_VIEJO}  # rev primero


def test_e7_una_partida_sin_apu_es_404_fijo() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _insumo(navegador, ficha, id_, 0, partida="NO-EXISTE")
    assert respuesta.status_code == 404 and respuesta.json() == {"detalle": PARTIDA_FALTA}


def test_e7_el_rev_se_comprueba_antes_que_el_contenido() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _parametros(navegador, ficha, id_, 0, utilidad="0.12")
    malo = _insumo(navegador, ficha, id_, 0, insumo="MAT-999")
    assert malo.status_code == 409 and malo.json() == {"detalle": REV_VIEJO}


# --- E8: los candidatos ---


def test_e8_los_materiales_de_la_lista_vienen_ordenados_con_su_precio_exacto() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _insumos(navegador, id_, "?tipo=material")
    assert respuesta.status_code == 200 and respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert len(cuerpo["insumos"]) == 38 and cuerpo["hay_mas"] is False
    descripciones = [i["descripcion"] for i in cuerpo["insumos"]]
    assert descripciones == sorted(descripciones)
    assert cuerpo["insumos"][0] == {
        "codigo": "MAT-022",
        "descripcion": "Abrazadera sencilla conduit 3/4 pulg [TUB222]",
        "unidad": "pieza",
        "precio": {"texto": "0.83", "exacto": "0.8344"},
    }
    assert len(_insumos(navegador, id_, "?tipo=equipo").json()["insumos"]) == 6
    assert len(_insumos(navegador, id_, "?tipo=mano_obra").json()["insumos"]) == 5


def test_e8_el_limite_corta_y_dice_que_hay_mas() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    corto = _insumos(navegador, id_, "?tipo=material&limite=10").json()
    assert len(corto["insumos"]) == 10 and corto["hay_mas"] is True
    justo = _insumos(navegador, id_, "?tipo=material&limite=38").json()
    assert len(justo["insumos"]) == 38 and justo["hay_mas"] is False
    maximo = _insumos(navegador, id_, "?tipo=material&limite=301").json()  # 301 se trata como 300
    assert len(maximo["insumos"]) == 38 and maximo["hay_mas"] is False


def test_e8_el_texto_acota_y_sin_coincidencias_la_lista_es_vacia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    assert (
        _insumos(navegador, id_, "?tipo=material&texto=PEGAMENTO").json()["insumos"][0]["codigo"]
        == "MAT-002"
    )
    vacio = _insumos(navegador, id_, "?tipo=material&texto=no%20existe%20jamas").json()
    assert vacio == {"insumos": [], "hay_mas": False}


@pytest.mark.parametrize(
    "consulta",
    [
        "",
        "?tipo=",
        "?tipo=xx",
        "?tipo=material&limite=0",
        "?tipo=material&limite=302",
        "?tipo=material&limite=x",
        "?tipo=material&texto=" + "x" * 501,
    ],
)
def test_e8_una_consulta_con_otra_forma_es_422_fijo_sin_eco(consulta) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _insumos(navegador, id_, consulta)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": FORMA_BUSQUEDA}
    assert respuesta.headers["cache-control"] == "no-store"


def test_e8_sin_version_abierta_es_409() -> None:
    navegador, ficha = _ana()
    _con_proyecto_nuevo(config.ruta_caso_por_defecto())
    id_ = _abrir(navegador, ficha, "Proyecto nuevo", None)
    respuesta = _insumos(navegador, id_, "?tipo=material")
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": SIN_VERSION}


# --- E9: la lista de cambios ---


def test_e9_sin_ediciones_la_lista_esta_vacia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _cambios(navegador, id_)
    assert respuesta.status_code == 200 and respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {"rev": 0, "cambios": []}


def test_e9_lista_cada_celda_en_el_orden_apu_cantidad_parametro() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    assert _parametros(navegador, ficha, id_, 0, administracion="0.20").status_code == 200
    assert (
        _cantidades(navegador, ficha, id_, 1, [{"clave": LLAVE, "cantidad": "5"}]).status_code
        == 200
    )
    assert _apu(navegador, ficha, id_, 2, rendimiento="10").status_code == 200
    cuerpo = _cambios(navegador, id_).json()
    assert cuerpo["rev"] == 3
    assert cuerpo["cambios"] == [
        {
            "objeto": "apu",
            "clave": "AF-LLAVE",
            "campo": "rendimiento",
            "antes": "20",
            "despues": "10",
        },
        {"objeto": "cantidad", "clave": LLAVE, "campo": "cantidad", "antes": "3", "despues": "5"},
        {
            "objeto": "parametro",
            "clave": "administracion",
            "campo": "valor",
            "antes": "0.15",
            "despues": "0.20",
        },
    ]
    assert len(cuerpo["cambios"]) == _resumen(navegador, id_)["cambios"] == 3


def test_e9_en_un_borrador_en_blanco_todo_lo_escrito_cuenta() -> None:
    navegador, ficha = _ana()
    _con_proyecto_nuevo(config.ruta_caso_por_defecto())
    id_ = _abrir(navegador, ficha, "Proyecto nuevo", None)
    assert _cambios(navegador, id_).json() == {"rev": 0, "cambios": []}
    assert _parametros(navegador, ficha, id_, 0, administracion="0.20").status_code == 200
    cambios = _cambios(navegador, id_).json()["cambios"]
    # el borrador en blanco parte de los parametros por omision de `Borrador`, no de los de OF-001:
    # cada parametro que el cuerpo escribe distinto es una celda cambiada
    assert {c["objeto"] for c in cambios} == {"parametro"}
    administracion = next(c for c in cambios if c["clave"] == "administracion")
    assert administracion["despues"] == "0.20"
    assert len(cambios) == _resumen(navegador, id_)["cambios"]


# --- E10 y E11: retomar, reemplazar y cambiar de version (3c-B14, P23) ---


def _listar(navegador) -> list[dict]:
    respuesta = navegador.get("/v1/hoja/borradores")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["borradores"]


def test_e10_sin_borradores_la_lista_esta_vacia_y_es_no_store() -> None:
    navegador, ficha = _ana()
    respuesta = navegador.get("/v1/hoja/borradores")
    assert respuesta.status_code == 200 and respuesta.json() == {"borradores": []}
    assert respuesta.headers["cache-control"] == "no-store"


def test_e10_tras_dos_ediciones_se_puede_retomar_con_su_rev_y_sus_tablas() -> None:
    """3c-B14: la lista dice `cambios: 2`; con el id y el rev se reanuda tras recargar."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    assert _parametros(navegador, ficha, id_, 0, utilidad="0.12").status_code == 200
    assert _apu(navegador, ficha, id_, 1, materiales=["2"]).status_code == 200
    (fila,) = _listar(navegador)
    assert fila["id"] == id_ and fila["proyecto"] == NOMBRE_OF001 and fila["version"] == "001"
    assert fila["cambios"] == 2 and fila["rev"] == 2
    datetime.fromisoformat(fila["tocado"])
    # reanudar: el borrador vivo con su rev, su resumen y sus tablas
    vivo = navegador.get(f"/v1/hoja/borradores/{id_}").json()
    assert vivo["resumen"]["rev"] == 2 and vivo["resumen"]["cambios"] == 2
    assert (
        _vista(navegador, id_, "apu", "?partida=AF-LLAVE")["detalle"]["grupos"][0]["filas"][0][
            "cantidad"
        ]
        == "2"
    )
    siguiente = _parametros(navegador, ficha, id_, vivo["resumen"]["rev"], utilidad="0.13")
    assert siguiente.status_code == 200 and siguiente.json()["rev"] == 3


def test_e10_el_mas_reciente_va_primero_y_listar_no_renueva_el_plazo() -> None:
    navegador, ficha = _ana()
    _con_proyecto_nuevo(config.ruta_caso_por_defecto())
    uno = _abrir(navegador, ficha)
    dos = _abrir(navegador, ficha, "Proyecto nuevo", None)
    assert [b["id"] for b in _listar(navegador)] == [dos, uno]
    antes = {v.id: v.tocado for v in hoja_borradores.listar(_huella(ficha))}
    _listar(navegador)
    despues = {v.id: v.tocado for v in hoja_borradores.listar(_huella(ficha))}
    assert antes == despues


def test_e10_no_lista_los_guardados_ni_los_de_otro_caso_ni_los_de_otra_ficha() -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()  # otra ficha de la misma cuenta
    _con_proyecto_nuevo(config.ruta_caso_por_defecto())
    visible = _abrir(uno, ficha_uno)
    guardado = _abrir(uno, ficha_uno, "Proyecto nuevo", None)
    hoja_borradores.obtener(_huella(ficha_uno), guardado).guardado_como = "002"
    ajeno = _abrir(otro, ficha_otro)
    assert [b["id"] for b in _listar(uno)] == [visible]
    assert [b["id"] for b in _listar(otro)] == [ajeno]
    hoja_borradores.obtener(_huella(ficha_uno), visible).caso = "/otro/caso.db"
    assert _listar(uno) == []


def test_e11_reabrir_la_misma_version_con_cambios_es_409_con_el_id_y_no_abre_nada() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _parametros(navegador, ficha, id_, 0, utilidad="0.12")
    _apu(navegador, ficha, id_, 1, materiales=["2"])
    respuesta = _abrir_con(navegador, ficha)
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": "Ya tiene un borrador de esta versión con 2 cambios sin guardar: "
        "retómelo o reemplácelo.",
        "borrador_id": id_,
    }
    assert respuesta.headers["cache-control"] == "no-store"
    assert [b["id"] for b in _listar(navegador)] == [id_]  # no se abrio otro
    assert _resumen(navegador, id_)["cambios"] == 2  # nada se descarto


def test_e11_con_un_solo_cambio_el_aviso_va_en_singular() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _parametros(navegador, ficha, id_, 0, utilidad="0.12")
    detalle = _abrir_con(navegador, ficha).json()["detalle"]
    assert detalle == (
        "Ya tiene un borrador de esta versión con 1 cambio sin guardar: retómelo o reemplácelo."
    )


def test_e11_reemplazar_descarta_el_anterior_y_abre_uno_nuevo_sin_cambios() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _parametros(navegador, ficha, id_, 0, utilidad="0.12")
    respuesta = _abrir_con(navegador, ficha, reemplazar=True)
    assert respuesta.status_code == 201, respuesta.text
    nuevo = respuesta.json()["id"]
    assert nuevo != id_ and respuesta.json()["resumen"]["cambios"] == 0
    assert navegador.get(f"/v1/hoja/borradores/{id_}").status_code == 404
    assert [b["id"] for b in _listar(navegador)] == [nuevo]


def test_e11_sin_cambios_el_borrador_anterior_no_estorba_y_sigue_vivo() -> None:
    """Como siempre (el quinto descarta al primero, 3b-B15): abrir de nuevo no toca al anterior."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _abrir_con(navegador, ficha)  # reemplazar por omision: falso
    assert respuesta.status_code == 201
    assert navegador.get(f"/v1/hoja/borradores/{id_}").status_code == 200
    assert {b["id"] for b in _listar(navegador)} == {id_, respuesta.json()["id"]}


def test_e11_un_borrador_con_cambios_revertidos_tampoco_estorba() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _apu(navegador, ficha, id_, 0, materiales=["2"])
    _apu(navegador, ficha, id_, 1, materiales=["1"])  # de vuelta: cero cambios
    assert _abrir_con(navegador, ficha).status_code == 201


def test_e11_si_abrir_falla_el_anterior_queda_intacto() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _parametros(navegador, ficha, id_, 0, utilidad="0.12")
    respuesta = _abrir_con(navegador, ficha, version="999", reemplazar=True)
    assert respuesta.status_code == 404
    assert _resumen(navegador, id_)["cambios"] == 1 and [b["id"] for b in _listar(navegador)] == [
        id_
    ]


def test_e11_cambiar_de_version_no_descarta_nada_p23() -> None:
    """P23: abrir otra version (un proyecto sin versiones) deja vivo el borrador con cambios."""
    navegador, ficha = _ana()
    _con_proyecto_nuevo(config.ruta_caso_por_defecto())
    primero = _abrir(navegador, ficha)
    _parametros(navegador, ficha, primero, 0, utilidad="0.12")
    segundo = _abrir(navegador, ficha, "Proyecto nuevo", None)
    assert segundo != primero
    assert _resumen(navegador, primero)["cambios"] == 1  # nada se descarto solo
    assert {b["id"]: b["cambios"] for b in _listar(navegador)} == {primero: 1, segundo: 0}
    # y se sigue editando el primero con su rev
    assert _parametros(navegador, ficha, primero, 1, utilidad="0.13").status_code == 200


def test_e11_el_borrador_de_otra_ficha_no_estorba_ni_se_confirma() -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()
    id_ = _abrir(uno, ficha_uno)
    _parametros(uno, ficha_uno, id_, 0, utilidad="0.12")
    respuesta = _abrir_con(otro, ficha_otro)
    assert respuesta.status_code == 201 and id_ not in respuesta.text
    assert _resumen(uno, id_)["cambios"] == 1  # el dueno no se entero


@pytest.mark.parametrize("valor", ["si", 1, None, "true"])
def test_e11_reemplazar_debe_ser_booleano(valor) -> None:
    navegador, ficha = _ana()
    respuesta = _abrir_con(navegador, ficha, reemplazar=valor)
    assert respuesta.status_code == 422 and "detalle" in respuesta.json()
    assert respuesta.headers["cache-control"] == "no-store" and _listar(navegador) == []


# --- el rev completo: dos hilos con el mismo rev, exactamente uno gana (3c-B13) ---


def _carrera(navegador, ficha, id_, peticiones) -> list:
    """Lanza las peticiones a la vez: todas esperan al cerrojo del borrador y se sueltan juntas."""
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    respuestas: list = [None] * len(peticiones)
    inicio = threading.Barrier(len(peticiones) + 1)

    def correr(n: int) -> None:
        inicio.wait()
        respuestas[n] = peticiones[n]()

    hilos = [threading.Thread(target=correr, args=(n,)) for n in range(len(peticiones))]
    with vivo.cerrojo:
        for hilo in hilos:
            hilo.start()
        inicio.wait()
        time.sleep(0.5)  # todas llegan y esperan al cerrojo
    for hilo in hilos:
        hilo.join(timeout=60)
        assert not hilo.is_alive()
    return respuestas


def _evidencias(navegador, id_) -> list[bool]:
    """Para cada edicion de la carrera: si su efecto esta en el borrador."""
    return [
        _vista(navegador, id_, "parametros")["campos"][3]["valor"] == "0.12",
        any(f["escrita"] for f in _vista(navegador, id_, "presupuesto")["filas"]),
        next(g for g in _vista(navegador, id_, "apu", "?partida=AF-LLAVE")["detalle"]["grupos"])[
            "filas"
        ][0]["cantidad"]
        == "2",
        _vista(navegador, id_, "espacio")["filas"]["ambientes"][0]["alto"] == "3",
    ]


def test_cuatro_hilos_de_rutas_distintas_con_el_mismo_rev_gana_exactamente_uno() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    peticiones = [
        lambda: _parametros(navegador, ficha, id_, 0, utilidad="0.12"),
        lambda: _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "5"}]),
        lambda: _apu(navegador, ficha, id_, 0, materiales=["2"]),
        lambda: _espacio(navegador, ficha, id_, 0, "3"),
    ]
    respuestas = _carrera(navegador, ficha, id_, peticiones)
    codigos = sorted(r.status_code for r in respuestas)
    assert codigos == [200, 409, 409, 409], [r.text[:200] for r in respuestas]
    perdedoras = [r for r in respuestas if r.status_code == 409]
    assert all(r.json() == {"detalle": REV_VIEJO} for r in perdedoras)
    assert _resumen(navegador, id_)["rev"] == 1 and _resumen(navegador, id_)["cambios"] >= 1
    # se aplico la edicion ganadora y solo esa: ninguna de las otras dejo huella
    ganadora = next(n for n, r in enumerate(respuestas) if r.status_code == 200)
    assert _evidencias(navegador, id_) == [n == ganadora for n in range(4)]


def test_dos_hilos_a_la_misma_ruta_con_el_mismo_rev_no_pierden_ni_mezclan_una_edicion() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    peticiones = [
        lambda: _apu(navegador, ficha, id_, 0, materiales=["2"]),
        lambda: _apu(navegador, ficha, id_, 0, materiales=["3"]),
    ]
    respuestas = _carrera(navegador, ficha, id_, peticiones)
    assert sorted(r.status_code for r in respuestas) == [200, 409]
    ganadora = next(n for n, r in enumerate(respuestas) if r.status_code == 200)
    fila = _vista(navegador, id_, "apu", "?partida=AF-LLAVE")["detalle"]["grupos"][0]["filas"][0]
    assert fila["cantidad"] == str(ganadora + 2) and _resumen(navegador, id_)["rev"] == 1


def test_con_el_rev_nuevo_de_la_respuesta_la_segunda_edicion_si_pasa() -> None:
    """El perdedor recarga (R3) y reintenta con el rev vigente: la secuencia no pierde nada."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    peticiones = [
        lambda: _parametros(navegador, ficha, id_, 0, utilidad="0.12"),
        lambda: _apu(navegador, ficha, id_, 0, materiales=["2"]),
    ]
    respuestas = _carrera(navegador, ficha, id_, peticiones)
    perdedora = next(n for n, r in enumerate(respuestas) if r.status_code == 409)
    rev = _resumen(navegador, id_)["rev"]
    if perdedora == 0:
        assert _parametros(navegador, ficha, id_, rev, utilidad="0.12").status_code == 200
    else:
        assert _apu(navegador, ficha, id_, rev, materiales=["2"]).status_code == 200
    assert _resumen(navegador, id_)["cambios"] == 2 and _resumen(navegador, id_)["rev"] == 2


# --- 3c-B19: acceso, CSRF, Origin, ficha ajena y caso en E6 a E11 ---

# (metodo, ruta con {id}, cuerpo, escribe)
PEDIDOS = [
    ("put", "/v1/hoja/borradores/{id}/apu/AF-LLAVE", {"rev": 0, **APU_LLAVE}, True),
    (
        "post",
        "/v1/hoja/borradores/{id}/apu/AF-LLAVE/insumo",
        {"rev": 0, "tipo": "material", "indice": 0, "insumo": "MAT-002"},
        True,
    ),
    ("get", "/v1/hoja/borradores/{id}/insumos?tipo=material", None, False),
    ("get", "/v1/hoja/borradores/{id}/cambios", None, False),
]
IDS = ["e6", "e7", "e8", "e9"]
GENERALES = PEDIDOS + [
    ("get", "/v1/hoja/borradores", None, False),
    (
        "post",
        "/v1/hoja/borradores",
        {"proyecto": NOMBRE_OF001, "version": "001", "reemplazar": True},
        True,
    ),
]
IDS_GENERALES = [*IDS, "e10", "e11"]


def _enviar(navegador, ficha, id_, metodo, ruta, cuerpo):
    kwargs = {"headers": protegida(ficha)}
    if cuerpo is not None:
        kwargs["json"] = cuerpo
    return getattr(navegador, metodo)(ruta.format(id=id_), **kwargs)


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "escribe"), GENERALES, ids=IDS_GENERALES)
def test_sin_sesion_ni_clave_es_401(metodo, ruta, cuerpo, escribe) -> None:
    kwargs = {"headers": {"Origin": ORIGEN}}
    if cuerpo is not None:
        kwargs["json"] = cuerpo
    respuesta = getattr(cliente(app), metodo)(ruta.format(id=ID_AJENO), **kwargs)
    assert respuesta.status_code == 401 and "detalle" in respuesta.json()
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "escribe"), GENERALES, ids=IDS_GENERALES)
def test_rita_que_revisa_y_tomas_con_clave_temporal_no_pueden(
    metodo, ruta, cuerpo, escribe
) -> None:
    rita, ficha = con_cuenta(app, "rita")
    respuesta = _enviar(rita, ficha, ID_AJENO, metodo, ruta, cuerpo)
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert respuesta.headers["cache-control"] == "no-store"
    tomas, ficha_tomas = con_cuenta(app, "tomas")
    assert _enviar(tomas, ficha_tomas, ID_AJENO, metodo, ruta, cuerpo).status_code == 403


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "escribe"), GENERALES, ids=IDS_GENERALES)
def test_la_clave_de_api_no_edita_ni_lee_la_hoja(metodo, ruta, cuerpo, escribe) -> None:
    kwargs = {"headers": {CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN}}
    if cuerpo is not None:
        kwargs["json"] = cuerpo
    respuesta = getattr(cliente(app), metodo)(ruta.format(id=ID_AJENO), **kwargs)
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": SOLO_CUENTA}
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo", "escribe"),
    [p for p in GENERALES if p[3]],
    ids=[i for i, p in zip(IDS_GENERALES, GENERALES, strict=True) if p[3]],
)
def test_exige_csrf_y_origen_propio(metodo, ruta, cuerpo, escribe) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    url = ruta.format(id=id_)
    llamar = getattr(navegador, metodo)
    assert llamar(url, json=cuerpo, headers={"Origin": ORIGEN}).status_code == 403  # sin CSRF
    ajeno = protegida(ficha, origen="http://evil.example")
    assert llamar(url, json=cuerpo, headers=ajeno).status_code == 403
    assert llamar(url, json=cuerpo, headers=protegida(ficha, origen=None)).status_code == 403
    assert _resumen(navegador, id_)["rev"] == 0 and len(_listar(navegador)) == 1


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "escribe"), PEDIDOS, ids=IDS)
def test_el_borrador_de_otra_ficha_no_existe_y_no_se_edita(metodo, ruta, cuerpo, escribe) -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()  # otra ficha de la misma cuenta: otra huella
    id_ = _abrir(uno, ficha_uno)
    ajeno = _enviar(otro, ficha_otro, id_, metodo, ruta, cuerpo)
    inventado = _enviar(otro, ficha_otro, ID_AJENO, metodo, ruta, cuerpo)
    assert ajeno.status_code == inventado.status_code == 404
    assert ajeno.json() == inventado.json() == {"detalle": FALTA}
    assert id_ not in ajeno.text
    assert _resumen(uno, id_)["rev"] == 0  # el dueno no se entero


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "escribe"), PEDIDOS, ids=IDS)
def test_tras_un_cambio_de_caso_forzado_es_409_fijo_y_ninguna_base_cambia(
    metodo, ruta, cuerpo, escribe, _casos, _entorno
) -> None:
    navegador, ficha = _ana()
    otro = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["ti001"], otro)
    preparar_base(_entorno)
    preparar_base(otro)
    id_ = _abrir(navegador, ficha)
    antes_a, antes_b = _volcado(_entorno), _volcado(otro)
    caso_web._elegidos[_huella(ficha)] = otro.resolve()  # el cambio sin pasar por `fijar`
    respuesta = _enviar(navegador, ficha, id_, metodo, ruta, cuerpo)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": OTRO_CASO}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes_a and _volcado(otro) == antes_b
    assert hoja_borradores.obtener(_huella(ficha), id_).rev == 0


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "escribe"), PEDIDOS, ids=IDS)
def test_cambiar_de_caso_olvida_el_borrador_y_pedirlo_da_404(
    metodo, ruta, cuerpo, escribe, _casos, _entorno
) -> None:
    navegador, ficha = _ana()
    otro = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["ti001"], otro)
    preparar_base(_entorno)
    preparar_base(otro)
    id_ = _abrir(navegador, ficha)
    cambio = navegador.post(
        "/v1/casos/actual", json={"nombre": otro.name}, headers=protegida(ficha)
    )
    assert cambio.status_code == 200, cambio.text
    respuesta = _enviar(navegador, ficha, id_, metodo, ruta, cuerpo)
    assert respuesta.status_code == 404 and respuesta.json() == {"detalle": FALTA}
    assert _listar(navegador) == []


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "escribe"), PEDIDOS[:2], ids=IDS[:2])
def test_un_borrador_ya_guardado_no_se_edita_con_e6_ni_e7(metodo, ruta, cuerpo, escribe) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    hoja_borradores.obtener(_huella(ficha), id_).guardado_como = "002"
    respuesta = _enviar(navegador, ficha, id_, metodo, ruta, cuerpo)
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": "Este borrador ya se guardó como la versión 002; abra esa versión para seguir."
    }


def test_un_id_con_forma_invalida_es_422_sin_eco() -> None:
    navegador, ficha = _ana()
    for metodo, ruta, cuerpo in (
        ("put", "/v1/hoja/borradores/corto/apu/AF-LLAVE", {"rev": 0, **APU_LLAVE}),
        (
            "post",
            "/v1/hoja/borradores/corto/apu/AF-LLAVE/insumo",
            {"rev": 0, "tipo": "material", "indice": 0, "insumo": "MAT-002"},
        ),
        ("get", "/v1/hoja/borradores/corto/insumos?tipo=material", None),
        ("get", "/v1/hoja/borradores/corto/cambios", None),
    ):
        kwargs = {"json": cuerpo} if cuerpo is not None else {}
        respuesta = getattr(navegador, metodo)(ruta, headers=protegida(ficha), **kwargs)
        assert respuesta.status_code == 422 and "corto" not in respuesta.text, ruta


def test_un_codigo_de_partida_de_mas_de_500_caracteres_es_422_sin_eco() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _apu(navegador, ficha, id_, 0, partida="P" * 501)
    assert respuesta.status_code == 422 and "P" * 20 not in respuesta.text


def test_un_cuerpo_de_mas_de_20_mib_en_e6_declarado_o_por_trozos_es_413() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    cabeceras = {**protegida(ficha), "Content-Type": "application/json"}
    ruta = _ruta_apu(id_, "AF-LLAVE")
    enorme = b'{"rev":0,"rendimiento":"' + b"1" * (20 * MIB) + b'","materiales":[]}'
    declarado = navegador.put(ruta, content=enorme, headers=cabeceras)
    assert declarado.status_code == 413 and declarado.json() == {"detalle": EXCEDE}

    def trozos() -> Iterator[bytes]:
        yield enorme[: 10 * MIB]
        yield enorme[10 * MIB :]

    chunked = navegador.put(ruta, content=trozos(), headers=cabeceras)
    assert chunked.status_code == 413 and chunked.json() == {"detalle": EXCEDE}
    assert _resumen(navegador, id_)["rev"] == 0


# --- nada a la base, ningun float, no-store ---


def _sin_float(valor) -> None:
    if isinstance(valor, float):
        raise AssertionError(f"float en el JSON: {valor!r}")
    if isinstance(valor, dict):
        for v in valor.values():
            _sin_float(v)
    elif isinstance(valor, list):
        for v in valor:
            _sin_float(v)


def test_e6_a_e10_no_escriben_en_la_base_ni_con_exito_ni_con_error(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _volcado(_entorno)
    assert _apu(navegador, ficha, id_, 0, materiales=["2"]).status_code == 200
    assert _insumo(navegador, ficha, id_, 1, insumo="MAT-002").status_code == 200
    assert _apu(navegador, ficha, id_, 2, materiales=["-1"]).status_code == 422
    assert _insumo(navegador, ficha, id_, 0).status_code == 409
    assert _insumos(navegador, id_, "?tipo=material").status_code == 200
    assert _cambios(navegador, id_).status_code == 200
    assert len(_listar(navegador)) == 1
    assert _volcado(_entorno) == antes


def test_ningun_numero_del_json_es_float_y_todo_monto_es_texto() -> None:
    import json

    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuestas = [
        _apu(navegador, ficha, id_, 0, materiales=["2"]),
        _insumo(navegador, ficha, id_, 1, insumo="MAT-002"),
        _insumos(navegador, id_, "?tipo=material"),
        _cambios(navegador, id_),
        navegador.get("/v1/hoja/borradores"),
    ]
    for respuesta in respuestas:
        assert respuesta.status_code == 200, respuesta.text
        _sin_float(json.loads(respuesta.text, parse_float=lambda t: float("nan")))
    assert isinstance(respuestas[0].json()["resumen"]["total"]["exacto"], str)
    assert isinstance(respuestas[2].json()["insumos"][0]["precio"]["exacto"], str)


def test_no_store_en_exito_404_409_y_422_de_e6_a_e11() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuestas = [
        _apu(navegador, ficha, id_, 0, materiales=["2"]),  # 200
        _apu(navegador, ficha, ID_AJENO, 0),  # 404 borrador
        _apu(navegador, ficha, id_, 0),  # 409 rev
        _apu(navegador, ficha, id_, 1, materiales=["-1"]),  # 422 dominio
        _apu(navegador, ficha, id_, "x"),  # 422 forma
        _insumos(navegador, id_, "?tipo=xx"),  # 422 forma
        _insumos(navegador, ID_AJENO, "?tipo=material"),  # 404
        _cambios(navegador, id_),  # 200
        _abrir_con(navegador, ficha),  # 409 con cambios
    ]
    assert [r.status_code for r in respuestas] == [200, 404, 409, 422, 422, 422, 404, 200, 409]
    assert all(r.headers["cache-control"] == "no-store" for r in respuestas)


# --- orden de bloqueos (borrador -> registro, nunca al reves) en E6 y E7 ---


class _Espia:
    """Un cerrojo que anota, por hilo, que otros tenia tomados al adquirirse."""

    historia: list[tuple[str, tuple[str, ...]]] = []
    tomados = threading.local()

    def __init__(self, nombre: str, real) -> None:
        self.nombre, self.real = nombre, real

    def __enter__(self):
        previos = tuple(getattr(self.tomados, "pila", ()))
        self.real.acquire()
        self.historia.append((self.nombre, previos))
        self.tomados.pila = (*previos, self.nombre)
        return self

    def __exit__(self, *_):
        pila = list(self.tomados.pila)
        pila.remove(self.nombre)
        self.tomados.pila = tuple(pila)
        self.real.release()

    def acquire(self, *a, **k):
        return self.real.acquire(*a, **k)

    def release(self):
        self.real.release()


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "escribe"), PEDIDOS[:2], ids=IDS[:2])
def test_el_registro_nunca_se_toma_antes_que_el_borrador(
    metodo, ruta, cuerpo, escribe, monkeypatch: pytest.MonkeyPatch
) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _Espia.historia = []
    registro = hoja_borradores.REGISTRO
    monkeypatch.setattr(registro, "_cerrojo", _Espia("registro", registro._cerrojo))
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    monkeypatch.setattr(vivo, "cerrojo", _Espia("borrador", vivo.cerrojo))
    respuesta = _enviar(navegador, ficha, id_, metodo, ruta, cuerpo)
    assert respuesta.status_code in (200, 409, 422), respuesta.text
    assert {nombre for nombre, _ in _Espia.historia} == {"registro", "borrador"}
    assert [(n, p) for n, p in _Espia.historia if n == "borrador" and "registro" in p] == []


# --- 3c-B18: PUT espacio + vista de resumen con 500 puntos (solo se registra) ---


def test_put_espacio_con_500_puntos_y_resumen_la_mediana_se_registra() -> None:
    """Como RNF-11, solo REGISTRA: ninguna afirmacion sobre el tiempo (seria fragil con la carga
    de la maquina). Comprueba el procedimiento y que los 500 puntos entran de verdad."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = copy.deepcopy(_vista(navegador, id_, "espacio")["filas"])
    modelo = next(p for p in tablas["puntos"] if p["tipo"] == "agua_fria")
    adicionales = [{**modelo, "id": f"X{n:03d}"} for n in range(500)]
    tablas["puntos"] = [*tablas["puntos"], *adicionales]
    estado = {"rev": 0}

    def edicion(i: int) -> None:
        tablas["puntos"][-1]["x"] = str(i)  # cada corrida cambia algo: el borrador cambia
        respuesta = navegador.put(
            f"/v1/hoja/borradores/{id_}/espacio",
            json={"rev": estado["rev"], "tablas": tablas},
            headers=protegida(ficha),
        )
        assert respuesta.status_code == 200, respuesta.text[:300]
        estado["rev"] = respuesta.json()["rev"]
        assert navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]["rev"] == estado["rev"]

    medicion = medir.medir(edicion)
    assert len(medicion.corridas) == medir.CORRIDAS == 5
    assert medicion.mediana >= 0  # solo se registra: ningun umbral
    assert estado["rev"] == 6  # calentamiento + cinco corridas, todas cambiaron el borrador
    assert len(_vista(navegador, id_, "espacio")["filas"]["puntos"]) == 21 + 500
    print(f"3c-B18 PUT espacio + resumen con 500 puntos: mediana {medicion.mediana:.3f} s")
