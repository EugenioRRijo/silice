"""P1 a P6: importar un plano a la hoja del proyecto (T10, 3e-2; pruebas 3e-B5 a 3e-B14).

Contrato: `docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md` (diseno §4.6 y §6.4, fila 3e-2; la
clasica `ui/paginas/hoja.py:1236-1374`).

* P1 `POST .../plano` (multipart `archivo` y `rev`): lee el plano y deja la importacion vigente.
* P2 `POST .../plano/unidad`, P3 `.../plano/alturas`, P4 `.../plano/circuitos`: la cambian.
* P5 `POST .../plano/fusionar`: la funde con el espacio del borrador (sube `rev`) y la descarta.
* P6 `DELETE .../plano`: la descarta.

La importacion NO es parte del borrador hasta fusionarla: P1 a P4 comprueban `rev` y no lo suben.
Sus archivos van a una carpeta temporal propia (`aplicacion.hoja_plano.DIRECTORIO_TEMPORAL`, que
aqui es una carpeta de la prueba) que se borra al descartar, vencer, expulsar, olvidar o fusionar.

Oraculos a mano (ninguno sale del codigo bajo prueba): los de `tests/fixtures/planos_de_la_hoja.py`
(memoria de OF-001: 33 importados, 6 alturas pendientes, circuitos C1 y C2); el total de la memoria
2 703,86 USD con los parametros de TI-001 (`test_aceptacion_sf.py:261-273`); los textos de la
clasica
(`ui/paginas/hoja.py:1285, 1304, 1330, 1350, 1367-1373` y `ui/hoja.py` H:2610-2842); el 413 de
`api/proteccion.py`.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adapters.espacio.planos import EstadoImportacion
from api import caso_web, dependencias
from api.rutas import hoja as ruta_hoja
from api.rutas import hoja_plano as ruta_plano
from aplicacion import hoja as copia
from aplicacion import hoja_borradores, hoja_plano
from core.budget import crear_proyecto
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from seguridad import sesiones
from tests.fixtures import caso_ti001
from tests.fixtures.app_de_prueba import app_con
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from tests.fixtures.planos_de_la_hoja import (
    AMBIENTES_OF001,
    CIRCUITOS_OF001,
    CORRUPTO,
    DXF_OF001,
    IMPORTADOS_OF001,
    altura_de_la_memoria,
    dxf_sin_unidad,
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
APP = app_con(ruta_hoja.router, ruta_plano.router)
SOLO_CUENTA = "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."
FALTA = (
    "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). "
    "Lo que no guardó se perdió: abra la versión otra vez."
)
OTRO_CASO = "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual."
REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo."
EXCEDE = "El cuerpo de la peticion excede el maximo de 20 MiB."
FORMA_PLANO = "Suba un archivo de plano (DXF o IFC) y envíe el rev del borrador."
SIN_IMPORTACION = "Vuelva a subir el plano: ya no está disponible."
UNIDAD = "Elija una unidad de la lista: m, cm, mm, dm, in o ft."
NO_ES_PLANO = (
    "El archivo «{}» no es un plano que se pueda importar. Suba un plano en formato DXF o IFC."
)
FALTA_LECTOR = (
    "Falta instalar el componente para leer planos DXF. Instale el extra «planos» con el comando "
    "«uv sync --extra planos» y vuelva a intentarlo."
)
AVISO = (
    "Si fusiona ahora, los ambientes sin altura entran con 2,5 m provisionales y los circuitos "
    "supuestos quedan marcados en la auditoría. Puede cargarlos antes o corregirlos después en las "
    "tablas."
)
TOTAL_MEMORIA = D("2703.86")
TOLERANCIA_M = D("0.001")
ORIGEN = "http://127.0.0.1:8000"
ID_AJENO = "a" * 22
MIB = 1024 * 1024
CENTINELA = "VALOR-CENTINELA"
CIRCUITO_BIEN = ["1", "1", "1", "6"]


# --- el entorno ---


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_plano")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
    }


@pytest.fixture(autouse=True)
def _entorno(
    _casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Path]:
    """La instalacion con cuentas, OF-001 como caso por defecto y la carpeta de los planos."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["of001"], ruta)
    planos = tmp_path / "planos_temporales"
    planos.mkdir()
    monkeypatch.setattr(hoja_plano, "DIRECTORIO_TEMPORAL", str(planos))
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def planos(tmp_path: Path) -> Path:
    return tmp_path / "planos_temporales"


def _carpetas(planos: Path) -> list[Path]:
    return sorted(p for p in planos.iterdir())


def _ana() -> tuple[TestClient, str]:
    return con_cuenta(APP, "ana")


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


def _rev(navegador: TestClient, id_: str) -> int:
    return navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]["rev"]


def _url(id_: str, resto: str = "") -> str:
    return f"/v1/hoja/borradores/{id_}/plano{resto}"


def _subir(navegador, ficha, id_, nombre="of001.dxf", contenido=None, rev=0, **extra):
    datos = DXF_OF001.read_bytes() if contenido is None else contenido
    return navegador.post(
        _url(id_),
        files={"archivo": (nombre, datos, "application/octet-stream")},
        data={"rev": str(rev)},
        headers=protegida(ficha),
        **extra,
    )


def _pedir(navegador, ficha, id_, resto, cuerpo):
    return navegador.post(_url(id_, resto), json=cuerpo, headers=protegida(ficha))


def _alturas(navegador, ficha, id_, alturas, rev=0):
    return _pedir(navegador, ficha, id_, "/alturas", {"rev": rev, "alturas": alturas})


def _circuitos(navegador, ficha, id_, circuitos, rev=0):
    return _pedir(navegador, ficha, id_, "/circuitos", {"rev": rev, "circuitos": circuitos})


def _fusionar(navegador, ficha, id_, rev=0):
    return _pedir(navegador, ficha, id_, "/fusionar", {"rev": rev})


def _todas_las_alturas() -> dict[str, str]:
    return {a: altura_de_la_memoria() for a in AMBIENTES_OF001}


def _listo(navegador, ficha, id_, rev=0) -> dict:
    """P1 + P3 (alturas de la memoria) + P4 (los dos circuitos)."""
    assert _subir(navegador, ficha, id_, rev=rev).status_code == 200
    assert _alturas(navegador, ficha, id_, _todas_las_alturas(), rev).status_code == 200
    respuesta = _circuitos(navegador, ficha, id_, {c: CIRCUITO_BIEN for c in CIRCUITOS_OF001}, rev)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _sin_floats(valor) -> None:
    assert not isinstance(valor, float), valor
    if isinstance(valor, dict):
        for v in valor.values():
            _sin_floats(v)
    elif isinstance(valor, list):
        for v in valor:
            _sin_floats(v)


# --- 3e-B5: el plano de OF-001 ---


def test_p1_el_dxf_de_of001_da_el_informe_de_la_memoria_y_no_cambia_el_borrador(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    _sin_floats(cuerpo)
    assert (cuerpo["estado"], cuerpo["archivo"], cuerpo["pide_unidad"], cuerpo["unidades"]) == (
        "importada",
        "of001.dxf",
        False,
        [],
    )
    conteos = {c["rotulo"]: c["cantidad"] for c in cuerpo["conteos"]}
    assert (conteos["Importado"], conteos["No reconocido"], conteos["Pendiente"]) == (
        IMPORTADOS_OF001,
        0,
        6,
    )
    assert list(conteos) == ["Importado", "No reconocido", "Aproximado", "Pendiente"]
    assert sorted(a["id"] for a in cuerpo["alturas_pendientes"]) == sorted(AMBIENTES_OF001)
    assert [c["id"] for c in cuerpo["circuitos_supuestos"]] == list(CIRCUITOS_OF001)
    for circuito in cuerpo["circuitos_supuestos"]:
        assert set(circuito) == {"id", "fase", "neutro", "tierra", "puntos"}
        assert all(isinstance(v, str) for v in circuito.values())
    assert cuerpo["aviso_pendientes"] == AVISO
    assert len(cuerpo["informe"]) == sum(conteos.values())
    assert all(set(f) == {"tipo", "referencia", "fila", "mensaje"} for f in cuerpo["informe"])
    assert sum(f["tipo"] == "Importado" for f in cuerpo["informe"]) == IMPORTADOS_OF001
    assert cuerpo["mensaje"] == ""
    assert _rev(navegador, id_) == 0  # la importacion no es parte del borrador
    assert [p.name for p in _carpetas(planos)][0].startswith("silice_planos_")
    assert len(_carpetas(planos)) == 1
    assert [p.name for p in _carpetas(planos)[0].iterdir()] == ["of001.dxf"]


def test_p1_leer_otro_plano_reemplaza_la_importacion_y_su_carpeta(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    assert _subir(navegador, ficha, id_).status_code == 200
    primera = _carpetas(planos)
    respuesta = _subir(navegador, ficha, id_, nombre="corrupto.dxf", contenido=CORRUPTO)
    assert respuesta.status_code == 200 and respuesta.json()["estado"] == "rechazada"
    segunda = _carpetas(planos)
    assert len(segunda) == 1 and segunda != primera
    assert [p.name for p in segunda[0].iterdir()] == ["corrupto.dxf"]


# --- 3e-B6: alturas ---


def test_p3_las_seis_alturas_de_la_memoria_se_cargan_y_rev_no_sube() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    respuesta = _alturas(navegador, ficha, id_, _todas_las_alturas())
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["alturas_pendientes"] == []
    assert {c["rotulo"]: c["cantidad"] for c in cuerpo["conteos"]}["Pendiente"] == 0
    assert cuerpo["aviso_pendientes"] == AVISO  # los circuitos siguen supuestos
    assert _rev(navegador, id_) == 0


def test_p3_una_en_blanco_queda_pendiente() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    alturas = {**_todas_las_alturas(), "ZB": "  "}
    del alturas["ZA"]
    cuerpo = _alturas(navegador, ficha, id_, alturas).json()
    assert sorted(a["id"] for a in cuerpo["alturas_pendientes"]) == ["ZA", "ZB"]


@pytest.mark.parametrize("malo", ["250,5", "0", "abc"])
def test_p3_una_altura_invalida_es_422_con_el_texto_de_la_clasica_y_ninguna_se_carga(malo) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    respuesta = _alturas(navegador, ficha, id_, {**_todas_las_alturas(), "ZB": malo})
    assert respuesta.status_code == 422
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "detalle": f"Altura de «ZB»: «{malo}» no es una altura valida. Escriba un numero de "
        "metros mayor que 0 y hasta 250, por ejemplo 2,50. No se cargó ninguna altura."
    }
    sigue = _alturas(navegador, ficha, id_, {}).json()  # nada enviado: la de antes, sin cambio
    assert len(sigue["alturas_pendientes"]) == 6


def test_p3_un_ambiente_que_no_esta_pendiente_es_422_fijo_y_sin_eco() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    respuesta = _alturas(navegador, ficha, id_, {**_todas_las_alturas(), CENTINELA: "2,5"})
    assert respuesta.status_code == 422 and CENTINELA not in respuesta.text
    assert respuesta.json() == {"detalle": hoja_plano.MENSAJE_ALTURAS_AJENAS}
    assert len(_alturas(navegador, ficha, id_, {}).json()["alturas_pendientes"]) == 6


# --- 3e-B7: circuitos ---


def test_p4_declarar_los_dos_circuitos_y_ya_no_hay_aviso() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    cuerpo = _listo(navegador, ficha, id_)
    assert cuerpo["circuitos_supuestos"] == [] and cuerpo["alturas_pendientes"] == []
    assert cuerpo["aviso_pendientes"] is None
    assert _rev(navegador, id_) == 0


def test_p4_un_entero_invalido_es_422_con_el_texto_de_la_clasica_y_ninguno_se_declara() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    circuitos = {"C1": CIRCUITO_BIEN, "C2": ["1", "1", "1", "0"]}
    respuesta = _circuitos(navegador, ficha, id_, circuitos)
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": "Circuito «C2»: los puntos maximos debe ser un numero entero de 1 o mas "
        "(se escribio «0»). No se declaró ningún circuito."
    }
    sigue = _circuitos(navegador, ficha, id_, {}).json()
    assert [c["id"] for c in sigue["circuitos_supuestos"]] == ["C1", "C2"]


def test_p4_un_circuito_que_no_es_supuesto_es_422_fijo_y_sin_eco() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    respuesta = _circuitos(navegador, ficha, id_, {CENTINELA: CIRCUITO_BIEN})
    assert respuesta.status_code == 422 and CENTINELA not in respuesta.text
    assert respuesta.json() == {"detalle": hoja_plano.MENSAJE_CIRCUITOS_AJENOS}


@pytest.mark.parametrize(
    "circuitos",
    [
        {"C1": ["1", "1", "1"]},
        {"C1": ["1", "1", "1", "1", "1"]},
        {"C1": "1,1,1,1"},
        {"C1": [1, 1, 1, 1]},
    ],
)
def test_p4_cada_circuito_es_de_cuatro_textos(circuitos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    respuesta = _circuitos(navegador, ficha, id_, circuitos)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": ruta_plano.FORMA_CIRCUITOS}


def test_p3_y_p4_topes_de_entradas_y_de_texto() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    muchas = {f"A{i}": "" for i in range(5001)}
    assert _alturas(navegador, ficha, id_, muchas).json() == {"detalle": ruta_plano.FORMA_ALTURAS}
    largo = {"ZB": "2" * 501}
    respuesta = _alturas(navegador, ficha, id_, largo)
    assert respuesta.status_code == 422 and "2" * 501 not in respuesta.text
    muchos = {f"C{i}": CIRCUITO_BIEN for i in range(5001)}
    respuesta = _circuitos(navegador, ficha, id_, muchos)
    assert respuesta.json() == {"detalle": ruta_plano.FORMA_CIRCUITOS}
    respuesta = _circuitos(navegador, ficha, id_, {"C1": ["1", "1", "1", CENTINELA * 60]})
    assert respuesta.status_code == 422 and CENTINELA not in respuesta.text
    # justo en el tope de texto: es el texto de la clasica (con eco, paridad aceptada)
    respuesta = _alturas(navegador, ficha, id_, {"ZB": "9" * 500})
    assert respuesta.status_code == 422 and "No se cargó ninguna altura." in respuesta.text


# --- 3e-B8 y 3e-B14: fusionar ---


def _con_proyecto_nuevo(ruta: Path) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as sesion:
        crear_proyecto(sesion, "Proyecto nuevo")
        sesion.commit()
    motor.dispose()
    dependencias.cerrar_motores()


def _parametros_de_ti001(navegador, ficha, id_) -> int:
    p = caso_ti001.PARAMETROS
    textos = {
        "fcas": str(p.fcas),
        "bono_alimentacion": str(p.bono_alimentacion),
        "administracion": str(p.administracion),
        "utilidad": str(p.utilidad),
    }
    respuesta = navegador.put(
        f"/v1/hoja/borradores/{id_}/parametros",
        json={"rev": 0, **textos},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["rev"]


def test_p5_sobre_un_borrador_en_blanco_da_el_total_y_las_cantidades_de_la_memoria(
    _entorno, planos
) -> None:
    _con_proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha, proyecto="Proyecto nuevo", version=None)
    rev = _parametros_de_ti001(navegador, ficha, id_)
    _listo(navegador, ficha, id_, rev)
    respuesta = _fusionar(navegador, ficha, id_, rev)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    _sin_floats(cuerpo)
    assert cuerpo["rev"] == cuerpo["resumen"]["rev"] == rev + 1
    assert abs(D(cuerpo["resumen"]["total"]["exacto"]) - TOTAL_MEMORIA) <= D("0.01")
    assert cuerpo["mensaje"] == (
        "Se fusionó «of001.dxf» con el borrador de la hoja: 6 ambientes, 6 fuentes y 21 puntos. "
        "Revise las filas en las tablas de abajo; la auditoría las evalúa como a las demás. "
        "Todavía no se guardó ninguna versión: use Guardar versión cuando esté conforme."
    )
    # 3e-B14: el resumen de la fusion cuenta una vez (33 importados, no 68)
    por_tipo = {f["rotulo"]: f["cantidad"] for f in cuerpo["fusion"]["por_tipo"]}
    assert por_tipo["Importado"] == IMPORTADOS_OF001 and por_tipo["Pendiente"] == 0
    por_tabla = {f["rotulo"]: f["cantidad"] for f in cuerpo["fusion"]["filas_por_tabla"]}
    assert (por_tabla["Ambientes"], por_tabla["Fuentes"], por_tabla["Puntos"]) == (6, 6, 21)
    assert isinstance(cuerpo["fusion"]["origenes"], int) and cuerpo["fusion"]["origenes"] > 0
    assert all(set(f) == {"tipo", "referencia", "fila", "mensaje"} for f in cuerpo["informe"])
    # las cantidades derivadas son las de la hoja manual a una milesima
    vista = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/espacio").json()
    del_plano = sorted((d["partida"], D(d["cantidad"]["exacto"])) for d in vista["derivadas"])
    manual = sorted(
        (i.codigo_partida, i.cantidad)
        for e in copia.TODAS
        for i in copia.items_del_borrador(espacio_of001(), e)
    )
    assert [p for p, _ in del_plano] == [p for p, _ in manual]
    for (partida, a), (_, b) in zip(del_plano, manual, strict=True):
        assert abs(a - b) <= TOLERANCIA_M, partida
    # la importacion se descarto: estado y carpeta
    assert _fusionar(navegador, ficha, id_, rev + 1).json() == {"detalle": SIN_IMPORTACION}
    assert _carpetas(planos) == []


def test_p5_sobre_of001_las_filas_ya_escritas_se_omiten_y_rev_no_sube(planos) -> None:
    """La hoja de OF-001 ya tiene los 33 ids del plano (escritos a mano, sin origen DXF): la fusion
    los OMITE (`adapters/espacio/planos/informe.py`, docstring) y el borrador no cambia, asi que
    `rev` no sube (como la clasica: `_poner_borrador` no hace nada si el borrador es el mismo).
    La importacion se descarta igual."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _listo(navegador, ficha, id_)
    respuesta = _fusionar(navegador, ficha, id_)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == 0 == _rev(navegador, id_) and cuerpo["resumen"]["cambios"] == 0
    por_tipo = {f["rotulo"]: f["cantidad"] for f in cuerpo["fusion"]["por_tipo"]}
    assert por_tipo["Omitido"] == IMPORTADOS_OF001 and cuerpo["fusion"]["filas_por_tabla"] == []
    assert _carpetas(planos) == []
    assert _fusionar(navegador, ficha, id_).json() == {"detalle": SIN_IMPORTACION}


def test_p5_con_un_rev_viejo_es_409_y_la_importacion_queda() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _listo(navegador, ficha, id_)
    respuesta = _fusionar(navegador, ficha, id_, rev=7)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": REV_VIEJO}
    assert _fusionar(navegador, ficha, id_).status_code == 200


def test_p5_sin_importacion_es_409() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _fusionar(navegador, ficha, id_)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": SIN_IMPORTACION}
    assert respuesta.headers["cache-control"] == "no-store"


def test_p5_un_borrador_ya_guardado_no_se_fusiona() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _listo(navegador, ficha, id_)
    hoja_borradores.obtener(_huella(ficha), id_).guardado_como = "002"
    respuesta = _fusionar(navegador, ficha, id_)
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": "Este borrador ya se guardó como la versión 002; abra esa versión para seguir."
    }


def test_p5_un_espacio_que_no_vale_es_422_y_el_borrador_no_cambia(monkeypatch) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _listo(navegador, ficha, id_)

    def invalido(_borrador, _resultado):
        raise ValueError("el punto 'P9' cita un ambiente inexistente: 'X'")

    monkeypatch.setattr(copia, "fusionar_plano", invalido)
    respuesta = _fusionar(navegador, ficha, id_)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "el punto 'P9' cita un ambiente inexistente: 'X'"}
    assert _rev(navegador, id_) == 0


# --- 3e-B9: detenida ---


def test_p1_un_dxf_sin_unidad_se_detiene_y_p2_con_metros_reanuda(tmp_path) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    sin_unidad = dxf_sin_unidad(tmp_path / "sin_unidad.dxf").read_bytes()
    cuerpo = _subir(navegador, ficha, id_, "sin_unidad.dxf", sin_unidad).json()
    assert (cuerpo["estado"], cuerpo["pide_unidad"]) == ("detenida", True)
    assert cuerpo["unidades"] == ["m", "cm", "mm", "dm", "in", "ft"]
    assert cuerpo["mensaje"].startswith("sin_unidad.dxf: el plano no declara sus unidades")
    assert cuerpo["alturas_pendientes"] == [] and cuerpo["aviso_pendientes"] is None
    malo = _pedir(navegador, ficha, id_, "/unidad", {"rev": 0, "unidades": CENTINELA})
    assert malo.status_code == 422 and malo.json() == {"detalle": UNIDAD}
    respuesta = _pedir(navegador, ficha, id_, "/unidad", {"rev": 0, "unidades": "m"})
    assert respuesta.status_code == 200, respuesta.text
    reanudado = respuesta.json()
    assert (reanudado["estado"], reanudado["pide_unidad"], reanudado["unidades"]) == (
        "importada",
        False,
        [],
    )
    assert len(reanudado["alturas_pendientes"]) == 6
    assert _rev(navegador, id_) == 0


def test_p2_p3_y_p4_sin_importacion_son_409() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    for resto, cuerpo in (
        ("/unidad", {"rev": 0, "unidades": "m"}),
        ("/alturas", {"rev": 0, "alturas": {}}),
        ("/circuitos", {"rev": 0, "circuitos": {}}),
    ):
        respuesta = _pedir(navegador, ficha, id_, resto, cuerpo)
        assert respuesta.status_code == 409, resto
        assert respuesta.json() == {"detalle": SIN_IMPORTACION}


def test_p2_si_el_archivo_guardado_ya_no_esta_es_409_sin_la_ruta_del_servidor(
    planos, tmp_path
) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    sin_unidad = dxf_sin_unidad(tmp_path / "sin_unidad.dxf").read_bytes()
    assert _subir(navegador, ficha, id_, "sin_unidad.dxf", sin_unidad).json()["pide_unidad"]
    for archivo in _carpetas(planos)[0].iterdir():
        archivo.unlink()
    respuesta = _pedir(navegador, ficha, id_, "/unidad", {"rev": 0, "unidades": "m"})
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": SIN_IMPORTACION}
    assert _carpetas(planos) == []


def test_un_mensaje_del_lector_con_la_ruta_del_servidor_no_la_devuelve(monkeypatch, planos) -> None:
    """Defensa: el lector repite el texto de su excepcion (un `OSError` trae la ruta)."""
    original = copia.leer_plano

    def con_ruta(ruta, *, unidades=None):
        resultado = original(ruta, unidades=unidades)
        mensaje = f"{Path(ruta).name}: no se pudo leer como DXF (OSError: '{Path(ruta)!s}')."
        return replace(resultado, estado=EstadoImportacion.RECHAZADA, mensaje=mensaje)

    monkeypatch.setattr(copia, "leer_plano", con_ruta)
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_)
    assert respuesta.status_code == 200
    assert str(planos) not in respuesta.text and str(planos).replace("\\", "\\\\") not in (
        respuesta.text
    )
    assert respuesta.json()["mensaje"] == hoja_plano.mensaje_sin_ruta("of001.dxf")


# --- ronda 1 del arbitro: la ruta recortada, P2 solo si esta detenida, heredar ---

NO_DETENIDA = "Esta importación no está detenida: no hace falta elegir una unidad."


def _errores_con_ruta():
    """Tres `OSError` como los que lanza el lector con la ruta del archivo en su texto."""
    return [
        lambda ruta: PermissionError(13, "Permission denied", str(ruta)),
        lambda ruta: FileNotFoundError(2, "No such file or directory", str(ruta)),
        lambda ruta: OSError(
            None, "El archivo esta siendo utilizado por otro proceso", str(ruta), 32
        ),
    ]


def _raiz_larga(tmp_path: Path, monkeypatch) -> Path:
    raiz = tmp_path / ("r" * 60) / ("s" * 60)
    raiz.mkdir(parents=True)
    assert len(str(raiz)) >= 120
    monkeypatch.setattr(hoja_plano, "DIRECTORIO_TEMPORAL", str(raiz))
    return raiz


def _lector_que_falla(monkeypatch, error) -> None:
    """El lector real de DXF ve `error` al abrir: el recorte a 120 caracteres es el REAL
    (`en_una_linea`), no uno inyectado."""
    from adapters.espacio.planos import auditoria_archivo

    def falla(ruta, *_a, **_k):
        raise error(ruta)

    monkeypatch.setattr(auditoria_archivo.ezdxf, "readfile", falla)
    monkeypatch.setattr(auditoria_archivo.recover, "readfile", falla)


def _sin_fragmentos_de(raiz: Path, texto: str) -> None:
    assert "Users" not in texto
    for parte in raiz.parts[1:]:
        assert parte[:6] not in texto, parte


@pytest.mark.parametrize("indice", [0, 1, 2], ids=["permiso", "no-existe", "winerror-32"])
def test_p1_un_error_del_lector_con_la_ruta_recortada_no_la_devuelve(
    indice, tmp_path, monkeypatch
) -> None:
    raiz = _raiz_larga(tmp_path, monkeypatch)
    _lector_que_falla(monkeypatch, _errores_con_ruta()[indice])
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_)
    assert respuesta.status_code == 200 and respuesta.json()["estado"] == "rechazada"
    _sin_fragmentos_de(raiz, respuesta.text)
    assert respuesta.json()["mensaje"] == hoja_plano.mensaje_sin_ruta("of001.dxf")


@pytest.mark.parametrize("indice", [0, 1, 2], ids=["permiso", "no-existe", "winerror-32"])
def test_p2_un_error_del_lector_con_la_ruta_recortada_no_la_devuelve(
    indice, tmp_path, monkeypatch
) -> None:
    raiz = _raiz_larga(tmp_path, monkeypatch)
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    sin_unidad = dxf_sin_unidad(tmp_path / "sin_unidad.dxf").read_bytes()
    assert _subir(navegador, ficha, id_, "sin_unidad.dxf", sin_unidad).json()["pide_unidad"]
    _lector_que_falla(monkeypatch, _errores_con_ruta()[indice])
    respuesta = _pedir(navegador, ficha, id_, "/unidad", {"rev": 0, "unidades": "m"})
    assert respuesta.status_code == 200 and respuesta.json()["estado"] == "rechazada"
    _sin_fragmentos_de(raiz, respuesta.text)
    assert respuesta.json()["mensaje"] == hoja_plano.mensaje_sin_ruta("sin_unidad.dxf")


def test_p2_sobre_una_importacion_que_no_esta_detenida_es_409_y_nada_cambia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    assert _alturas(navegador, ficha, id_, _todas_las_alturas()).status_code == 200
    respuesta = _pedir(navegador, ficha, id_, "/unidad", {"rev": 0, "unidades": "m"})
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": NO_DETENIDA}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _alturas(navegador, ficha, id_, {}).json()["alturas_pendientes"] == []  # siguen


def test_la_importacion_sigue_a_su_borrador_al_heredar_la_ficha(planos) -> None:
    """Cambio de contrasena: la ficha nueva hereda los borradores (`caso_web.heredar`) y con
    ellos su importacion; la ficha vieja ya no la alcanza."""
    vieja, ficha_vieja = _ana()
    nueva, ficha_nueva = _ana()
    id_ = _abrir(vieja, ficha_vieja)
    _listo(vieja, ficha_vieja, id_)
    caso_web.heredar(_huella(ficha_vieja), _huella(ficha_nueva))
    assert _fusionar(vieja, ficha_vieja, id_).json() == {"detalle": FALTA}
    respuesta = _fusionar(nueva, ficha_nueva, id_)
    assert respuesta.status_code == 200, respuesta.text
    assert _carpetas(planos) == []


# --- 3e-B10: rechazada ---


def test_p1_un_archivo_corrupto_es_rechazada_con_200_y_no_se_fusiona() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_, "corrupto.dxf", CORRUPTO)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "rechazada"
    assert cuerpo["mensaje"].startswith("corrupto.dxf: no se pudo leer como DXF (")
    assert cuerpo["conteos"] and all(c["cantidad"] == 0 for c in cuerpo["conteos"])
    fusion = _fusionar(navegador, ficha, id_)
    assert fusion.status_code == 409
    assert fusion.json() == {"detalle": f"No se puede fusionar «corrupto.dxf»: {cuerpo['mensaje']}"}
    assert _rev(navegador, id_) == 0


# --- 3e-B11: la subida ---


@pytest.mark.parametrize("nombre", ["virus.exe", "plano.DXF.txt", "sin_extension"])
def test_p1_otra_extension_es_422_antes_de_escribir_nada(nombre, planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_, nombre, b"MZ")
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": NO_ES_PLANO.format(nombre)}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _carpetas(planos) == []


def test_p1_la_extension_no_distingue_mayusculas(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_, "OF001.DXF")
    assert respuesta.status_code == 200 and respuesta.json()["estado"] == "importada"


@pytest.mark.parametrize(
    ("nombre", "guardado"),
    [("..\\..\\x.dxf", "x.dxf"), ("../../x.dxf", "x.dxf"), ("CON.dxf", "_CON.dxf")],
)
def test_p1_el_nombre_se_guarda_seguro_dentro_de_su_carpeta(nombre, guardado, planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_, nombre)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["archivo"] == guardado
    (carpeta,) = _carpetas(planos)
    assert [p.name for p in carpeta.iterdir()] == [guardado]
    assert not (planos.parent / "x.dxf").exists()


def test_p1_un_nombre_sin_nada_utilizable_es_422_con_el_texto_de_la_clasica(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_, ":.dxf")
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": "El archivo subido no trae un nombre utilizable. Renombre el archivo y vuelva "
        "a subirlo."
    }
    assert _carpetas(planos) == []


def test_p1_mas_de_20_mib_es_413_por_content_length_y_por_trozos_sin_eco(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    grande = CENTINELA.encode() * (21 * MIB // len(CENTINELA))
    respuesta = _subir(navegador, ficha, id_, f"{CENTINELA}.dxf", grande)
    assert respuesta.status_code == 413 and respuesta.json() == {"detalle": EXCEDE}
    assert CENTINELA not in respuesta.text

    frontera = "frontera-de-prueba"
    cabecera = (
        f'--{frontera}\r\nContent-Disposition: form-data; name="rev"\r\n\r\n0\r\n'
        f'--{frontera}\r\nContent-Disposition: form-data; name="archivo"; '
        f'filename="{CENTINELA}.dxf"\r\nContent-Type: application/octet-stream\r\n\r\n'
    ).encode()

    def trozos():
        yield cabecera
        for _ in range(21):
            yield b"0" * MIB
        yield f"\r\n--{frontera}--\r\n".encode()

    respuesta = navegador.post(
        _url(id_),
        content=trozos(),
        headers={**protegida(ficha), "Content-Type": f"multipart/form-data; boundary={frontera}"},
    )
    assert respuesta.status_code == 413 and respuesta.json() == {"detalle": EXCEDE}
    assert CENTINELA not in respuesta.text
    assert _carpetas(planos) == []


@pytest.mark.parametrize(
    "envio",
    [
        "sin_archivo",
        "sin_rev",
        "rev_texto",
        "rev_negativo",
        "dos_archivos",
        "archivo_texto",
        "json",
    ],
)
def test_p1_la_forma_es_422_fijo_sin_eco(envio, planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    archivo = ("of001.dxf", DXF_OF001.read_bytes(), "application/octet-stream")
    kwargs: dict = {"headers": protegida(ficha)}
    if envio == "sin_archivo":
        kwargs["data"] = {"rev": "0"}
    elif envio == "sin_rev":
        kwargs["files"] = {"archivo": archivo}
    elif envio == "rev_texto":
        kwargs.update(files={"archivo": archivo}, data={"rev": CENTINELA})
    elif envio == "rev_negativo":
        kwargs.update(files={"archivo": archivo}, data={"rev": "-1"})
    elif envio == "dos_archivos":
        kwargs.update(files=[("archivo", archivo), ("archivo", archivo)], data={"rev": "0"})
    elif envio == "archivo_texto":
        kwargs["data"] = {"rev": "0", "archivo": CENTINELA}
    else:
        kwargs["json"] = {"rev": 0, "archivo": CENTINELA}
    respuesta = navegador.post(_url(id_), **kwargs)
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json() == {"detalle": FORMA_PLANO}
    assert CENTINELA not in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert _carpetas(planos) == []


def test_p1_el_rev_se_comprueba_antes_que_la_extension(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_, "virus.exe", b"MZ", rev=3)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": REV_VIEJO}
    assert _carpetas(planos) == []


@pytest.mark.parametrize(
    ("resto", "cuerpo"),
    [
        ("/unidad", {"rev": 5, "unidades": "m"}),
        ("/alturas", {"rev": 5, "alturas": {}}),
        ("/circuitos", {"rev": 5, "circuitos": {}}),
    ],
)
def test_p2_p3_y_p4_con_rev_viejo_son_409_antes_que_el_contenido(resto, cuerpo) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    respuesta = _pedir(navegador, ficha, id_, resto, cuerpo)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": REV_VIEJO}


# --- 3e-B13: falta el lector ---


def test_p1_sin_el_lector_de_dxf_es_422_con_el_texto_de_la_clasica(monkeypatch, planos) -> None:
    monkeypatch.setitem(sys.modules, "adapters.espacio.planos.dxf", None)  # import -> ImportError
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FALTA_LECTOR}
    assert _carpetas(planos) == []


# --- 3e-B12: limpieza ---


def test_p6_descarta_la_importacion_y_su_carpeta_es_idempotente_y_no_toca_el_borrador(
    planos,
) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    respuesta = navegador.delete(_url(id_), headers=protegida(ficha))
    assert respuesta.status_code == 204 and respuesta.headers["cache-control"] == "no-store"
    assert _carpetas(planos) == []
    assert navegador.delete(_url(id_), headers=protegida(ficha)).status_code == 204
    assert _fusionar(navegador, ficha, id_).json() == {"detalle": SIN_IMPORTACION}
    assert _rev(navegador, id_) == 0


def test_descartar_el_borrador_borra_su_carpeta(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    assert (
        navegador.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha)).status_code == 204
    )
    assert _carpetas(planos) == []


def test_vencer_el_borrador_borra_su_carpeta(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    hoja_borradores.obtener(_huella(ficha), id_).tocado -= timedelta(hours=9)
    assert navegador.get(f"/v1/hoja/borradores/{id_}").status_code == 404
    assert _carpetas(planos) == []


def test_la_expulsion_por_el_tope_de_la_ficha_borra_su_carpeta(planos) -> None:
    navegador, ficha = _ana()
    primero = _abrir(navegador, ficha)
    _subir(navegador, ficha, primero)
    for _ in range(4):
        _abrir(navegador, ficha)
    assert navegador.get(f"/v1/hoja/borradores/{primero}").status_code == 404
    assert _carpetas(planos) == []


def test_olvidar_la_ficha_o_cambiar_de_caso_borra_su_carpeta(planos, _casos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    otro = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["of001"], otro)
    caso_web.fijar(_huella(ficha), otro.resolve())  # lo que hace `POST /v1/casos/actual`
    assert _carpetas(planos) == []
    uno = _abrir(navegador, ficha)
    _subir(navegador, ficha, uno)
    caso_web.olvidar(_huella(ficha))  # cerrar sesion
    assert _carpetas(planos) == []


# --- acceso ---

PEDIDOS = [
    ("post", "", "multipart"),
    ("post", "/unidad", {"rev": 0, "unidades": "m"}),
    ("post", "/alturas", {"rev": 0, "alturas": {}}),
    ("post", "/circuitos", {"rev": 0, "circuitos": {}}),
    ("post", "/fusionar", {"rev": 0}),
    ("delete", "", None),
]
IDS = ["p1", "p2", "p3", "p4", "p5", "p6"]


def _enviar(navegador, id_, metodo, resto, cuerpo, headers):
    kwargs: dict = {"headers": headers}
    if cuerpo == "multipart":
        kwargs.update(
            files={"archivo": ("of001.dxf", DXF_OF001.read_bytes(), "application/octet-stream")},
            data={"rev": "0"},
        )
    elif cuerpo is not None:
        kwargs["json"] = cuerpo
    return getattr(navegador, metodo)(_url(id_, resto), **kwargs)


@pytest.mark.parametrize(("metodo", "resto", "cuerpo"), PEDIDOS, ids=IDS)
def test_sin_sesion_ni_clave_es_401(metodo, resto, cuerpo, planos) -> None:
    respuesta = _enviar(cliente(APP), ID_AJENO, metodo, resto, cuerpo, {"Origin": ORIGEN})
    assert respuesta.status_code == 401 and "detalle" in respuesta.json()
    assert respuesta.headers["cache-control"] == "no-store"
    assert _carpetas(planos) == []


@pytest.mark.parametrize(("metodo", "resto", "cuerpo"), PEDIDOS, ids=IDS)
def test_rita_que_revisa_y_tomas_con_clave_temporal_no_pueden(metodo, resto, cuerpo) -> None:
    rita, ficha = con_cuenta(APP, "rita")
    respuesta = _enviar(rita, ID_AJENO, metodo, resto, cuerpo, protegida(ficha))
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert respuesta.headers["cache-control"] == "no-store"
    tomas, ficha_tomas = con_cuenta(APP, "tomas")
    assert (
        _enviar(tomas, ID_AJENO, metodo, resto, cuerpo, protegida(ficha_tomas)).status_code == 403
    )


@pytest.mark.parametrize(("metodo", "resto", "cuerpo"), PEDIDOS, ids=IDS)
def test_la_clave_de_api_no_sirve(metodo, resto, cuerpo, planos) -> None:
    cabeceras = {CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN}
    respuesta = _enviar(cliente(APP), ID_AJENO, metodo, resto, cuerpo, cabeceras)
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": SOLO_CUENTA}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _carpetas(planos) == []


@pytest.mark.parametrize(("metodo", "resto", "cuerpo"), PEDIDOS, ids=IDS)
def test_exige_csrf_y_origen_propio(metodo, resto, cuerpo, planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    for cabeceras in (
        {"Origin": ORIGEN},
        protegida(ficha, origen="http://evil.example"),
        protegida(ficha, origen=None),
    ):
        assert _enviar(navegador, id_, metodo, resto, cuerpo, cabeceras).status_code == 403
    assert _carpetas(planos) == [] and _rev(navegador, id_) == 0


@pytest.mark.parametrize(("metodo", "resto", "cuerpo"), PEDIDOS, ids=IDS)
def test_el_borrador_de_otra_ficha_no_existe(metodo, resto, cuerpo, planos) -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()  # otra ficha de la misma cuenta: otra huella
    id_ = _abrir(uno, ficha_uno)
    _subir(uno, ficha_uno, id_)
    antes = _carpetas(planos)
    ajeno = _enviar(otro, id_, metodo, resto, cuerpo, protegida(ficha_otro))
    inventado = _enviar(otro, ID_AJENO, metodo, resto, cuerpo, protegida(ficha_otro))
    assert ajeno.status_code == inventado.status_code == 404
    assert ajeno.json() == inventado.json() == {"detalle": FALTA}
    assert id_ not in ajeno.text
    assert _carpetas(planos) == antes  # la del dueno sigue y no se creo otra
    assert _fusionar(uno, ficha_uno, id_).status_code == 200  # el dueno no se entero


@pytest.mark.parametrize(("metodo", "resto", "cuerpo"), PEDIDOS, ids=IDS)
def test_tras_un_cambio_de_caso_forzado_es_409_fijo(metodo, resto, cuerpo, _casos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _subir(navegador, ficha, id_)
    otro = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["of001"], otro)
    caso_web._elegidos[_huella(ficha)] = otro.resolve()  # el cambio sin pasar por `fijar`
    respuesta = _enviar(navegador, id_, metodo, resto, cuerpo, protegida(ficha))
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": OTRO_CASO}
    assert respuesta.headers["cache-control"] == "no-store"


def test_la_importacion_de_una_ficha_no_se_ve_ni_se_fusiona_desde_otra() -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()
    del_uno = _abrir(uno, ficha_uno)
    del_otro = _abrir(otro, ficha_otro)
    _listo(uno, ficha_uno, del_uno)
    assert _fusionar(otro, ficha_otro, del_otro).json() == {"detalle": SIN_IMPORTACION}
    assert _fusionar(otro, ficha_otro, del_uno).json() == {"detalle": FALTA}
    assert _alturas(otro, ficha_otro, del_otro, {}).json() == {"detalle": SIN_IMPORTACION}
    assert _fusionar(uno, ficha_uno, del_uno).status_code == 200
    assert _rev(otro, del_otro) == 0


def test_cada_borrador_de_la_misma_ficha_tiene_su_importacion(planos) -> None:
    navegador, ficha = _ana()
    uno, dos = _abrir(navegador, ficha), _abrir(navegador, ficha)
    _subir(navegador, ficha, uno)
    _subir(navegador, ficha, dos, "corrupto.dxf", CORRUPTO)
    assert len(_carpetas(planos)) == 2
    assert _fusionar(navegador, ficha, dos).status_code == 409  # la suya esta rechazada
    navegador.delete(_url(dos), headers=protegida(ficha))
    assert len(_carpetas(planos)) == 1
    assert _fusionar(navegador, ficha, uno).status_code == 200


def test_un_id_mal_formado_es_422_sin_eco() -> None:
    navegador, ficha = _ana()
    for metodo, resto, cuerpo in PEDIDOS:
        respuesta = _enviar(navegador, "corto", metodo, resto, cuerpo, protegida(ficha))
        assert respuesta.status_code == 422, (metodo, resto)
        assert "corto" not in respuesta.text


# --- concurrencia ---


def test_dos_p5_con_el_mismo_rev_gana_exactamente_uno(_entorno) -> None:
    """Sobre un borrador en blanco (la fusion SI lo cambia): uno sube `rev` y el otro ve el 409."""
    _con_proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha, proyecto="Proyecto nuevo", version=None)
    _listo(navegador, ficha, id_)
    barrera = threading.Barrier(2)
    codigos: list[int] = []
    detalles: list[dict] = []

    def fusionar() -> None:
        barrera.wait()
        respuesta = _fusionar(navegador, ficha, id_)
        codigos.append(respuesta.status_code)
        detalles.append(respuesta.json())

    hilos = [threading.Thread(target=fusionar) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=60)
    assert sorted(codigos) == [200, 409]
    assert {"detalle": REV_VIEJO} in detalles
    assert _rev(navegador, id_) == 1


def test_dos_p1_a_la_vez_no_dejan_restos(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    barrera = threading.Barrier(2)
    codigos: list[int] = []

    def subir(nombre: str) -> None:
        barrera.wait()
        codigos.append(_subir(navegador, ficha, id_, nombre).status_code)

    hilos = [threading.Thread(target=subir, args=(n,)) for n in ("uno.dxf", "dos.dxf")]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=60)
    assert codigos == [200, 200]
    (carpeta,) = _carpetas(planos)
    (archivo,) = list(carpeta.iterdir())
    assert archivo.name in {"uno.dxf", "dos.dxf"}
    respuesta = _fusionar(navegador, ficha, id_)
    assert respuesta.status_code == 200 and f"«{archivo.name}»" in respuesta.json()["mensaje"]


def test_p1_durante_el_descarte_del_borrador_no_deja_restos(monkeypatch, planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    leyendo, seguir = threading.Event(), threading.Event()
    original = copia.leer_plano

    def lento(ruta, *, unidades=None):
        leyendo.set()
        assert seguir.wait(timeout=30)
        return original(ruta, unidades=unidades)

    monkeypatch.setattr(copia, "leer_plano", lento)
    respuestas = []
    hilo = threading.Thread(target=lambda: respuestas.append(_subir(navegador, ficha, id_)))
    hilo.start()
    assert leyendo.wait(timeout=30)
    assert (
        navegador.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha)).status_code == 204
    )
    seguir.set()
    hilo.join(timeout=60)
    assert respuestas[0].status_code == 404 and respuestas[0].json() == {"detalle": FALTA}
    assert _carpetas(planos) == []


def test_el_cerrojo_de_la_importacion_nunca_se_toma_antes_que_el_del_borrador(
    monkeypatch, tmp_path
) -> None:
    """Orden de bloqueos: borrador, importacion y registro; nunca al reves (sin abrazo mortal)."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tenidos = threading.local()
    violaciones: list[str] = []
    usos = {"borrador": 0, "plano": 0}

    class Espia:
        def __init__(self, real, nombre: str) -> None:
            self.real, self.nombre = real, nombre

        def acquire(self, *args, **kwargs):
            pila = getattr(tenidos, "pila", [])
            if self.nombre == "borrador" and "plano" in pila:
                violaciones.append("borrador despues de la importacion")
            obtenido = self.real.acquire(*args, **kwargs)
            pila.append(self.nombre)
            tenidos.pila = pila
            usos[self.nombre] += 1
            return obtenido

        def release(self) -> None:
            pila = tenidos.pila
            del pila[len(pila) - 1 - pila[::-1].index(self.nombre)]
            self.real.release()

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self, *_exc) -> None:
            self.release()

    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    vivo.cerrojo = Espia(vivo.cerrojo, "borrador")
    monkeypatch.setattr(hoja_plano.IMPORTACIONES, "_cerrojo", Espia(threading.RLock(), "plano"))
    _listo(navegador, ficha, id_)
    sin_unidad = dxf_sin_unidad(tmp_path / "sin_unidad.dxf").read_bytes()
    _subir(navegador, ficha, id_, "sin_unidad.dxf", sin_unidad)
    assert _pedir(navegador, ficha, id_, "/unidad", {"rev": 0, "unidades": "m"}).status_code == 200
    assert _fusionar(navegador, ficha, id_).status_code == 200  # con alturas provisionales
    assert navegador.delete(_url(id_), headers=protegida(ficha)).status_code == 204
    assert violaciones == []
    assert usos["borrador"] > 0 and usos["plano"] > 0


# --- ola de decisiones: los topes del lector (bytes, lecturas a la vez, barrido) ---

PLANO_GRANDE = (
    "El plano DXF pesa más de 8 MiB, el máximo que Sílice lee en un tiempo razonable. Purgue las "
    "capas y bloques que no use, o divida el dibujo por plantas, y vuelva a subirlo."
)
LECTURAS_OCUPADAS = (
    "Sílice está leyendo otros planos en este momento: espere unos segundos y vuelva a subirlo."
)


def test_p1_un_dxf_de_mas_de_8_mib_es_413_de_texto_fijo_y_no_toca_la_importacion(planos) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    assert _subir(navegador, ficha, id_).status_code == 200
    antes = _carpetas(planos)
    grande = CENTINELA.encode() * ((8 * MIB + 1) // len(CENTINELA) + 1)
    respuesta = _subir(navegador, ficha, id_, f"{CENTINELA}.dxf", grande[: 8 * MIB + 1])
    assert respuesta.status_code == 413 and respuesta.json() == {"detalle": PLANO_GRANDE}
    assert respuesta.headers["cache-control"] == "no-store"
    assert CENTINELA not in respuesta.text
    assert _carpetas(planos) == antes  # la importacion anterior sigue y no hay carpeta nueva
    # la importacion anterior sigue vigente (si se hubiera perdido, P3 daria 409 sin importacion)
    assert _pedir(navegador, ficha, id_, "/alturas", {"rev": 0, "alturas": {}}).status_code == 200


def test_p1_la_lectura_de_mas_es_503_de_texto_fijo_sin_esperar(monkeypatch, planos) -> None:
    monkeypatch.setattr(hoja_plano, "_CUPOS", threading.BoundedSemaphore(0))
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _subir(navegador, ficha, id_)
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detalle": LECTURAS_OCUPADAS}
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["retry-after"] == "10"
    assert _carpetas(planos) == []


def test_p2_la_lectura_de_mas_es_503_y_la_importacion_detenida_queda(
    monkeypatch, planos, tmp_path
) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    sin_unidad = dxf_sin_unidad(tmp_path / "sin_unidad.dxf").read_bytes()
    assert _subir(navegador, ficha, id_, "sin_unidad.dxf", sin_unidad).json()["pide_unidad"]
    monkeypatch.setattr(hoja_plano, "_CUPOS", threading.BoundedSemaphore(0))
    respuesta = _pedir(navegador, ficha, id_, "/unidad", {"rev": 0, "unidades": "m"})
    assert respuesta.status_code == 503 and respuesta.json() == {"detalle": LECTURAS_OCUPADAS}
    monkeypatch.setattr(hoja_plano, "_CUPOS", threading.BoundedSemaphore(1))
    assert _pedir(navegador, ficha, id_, "/unidad", {"rev": 0, "unidades": "m"}).status_code == 200


def test_cuatro_planos_a_la_vez_con_dos_cupos_dos_leen_y_dos_reciben_503_enseguida(
    monkeypatch, planos
) -> None:
    """El fallo medido era que 40 lecturas agotaban el grupo de hilos: con el tope, las de mas
    vuelven al instante aunque las dos primeras sigan leyendo, y al terminar quedan los cupos."""
    assert hoja_plano.LECTURAS_SIMULTANEAS == 2
    monkeypatch.setattr(hoja_plano, "_CUPOS", threading.BoundedSemaphore(2))
    leyendo, soltar = threading.Semaphore(0), threading.Event()
    real = copia.subir_plano

    def lenta(subida, carpeta, **kwargs):
        leyendo.release()
        assert soltar.wait(timeout=120)
        return real(subida, carpeta, **kwargs)

    monkeypatch.setattr(copia, "subir_plano", lenta)
    navegador, ficha = _ana()
    ids = [_abrir(navegador, ficha) for _ in range(4)]
    respuestas: dict[int, object] = {}

    def subir(n: int) -> None:
        respuestas[n] = _subir(navegador, ficha, ids[n])

    primeras = [threading.Thread(target=subir, args=(n,)) for n in (0, 1)]
    for hilo in primeras:
        hilo.start()
    assert leyendo.acquire(timeout=60) and leyendo.acquire(timeout=60)  # las dos estan leyendo

    inicio = time.perf_counter()
    subir(2)
    subir(3)
    assert time.perf_counter() - inicio < 30  # sin esperar a las que leen
    assert [respuestas[n].status_code for n in (2, 3)] == [503, 503]
    assert all(respuestas[n].json() == {"detalle": LECTURAS_OCUPADAS} for n in (2, 3))

    soltar.set()
    for hilo in primeras:
        hilo.join(timeout=120)
        assert not hilo.is_alive()
    assert [respuestas[n].status_code for n in (0, 1)] == [200, 200]
    monkeypatch.setattr(copia, "subir_plano", real)
    assert _subir(navegador, ficha, ids[2]).status_code == 200  # el cupo volvio
    assert len(_carpetas(planos)) == 3


def test_al_arrancar_el_servidor_barre_las_carpetas_huerfanas(monkeypatch, planos) -> None:
    monkeypatch.setattr(hoja_plano, "_ultimo_barrido", None)
    vieja = planos / "silice_planos_de_una_caida"
    vieja.mkdir()
    (vieja / "plano.dxf").write_bytes(b"0")
    hace_dos_horas = time.time() - 7200
    os.utime(vieja, (hace_dos_horas, hace_dos_horas))
    reciente = planos / "silice_planos_reciente"
    reciente.mkdir()
    with TestClient(APP):  # el `startup` del router de los planos
        assert not vieja.exists()
        assert reciente.exists()
