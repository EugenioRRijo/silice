"""`PUT /v1/hoja/borradores/{id}/espacio` (E1): la edicion del espacio de la hoja (T10, 3c-1).

Contrato (`docs/bitacora/2026-10-19-hoja-3c1-contrato-rutas.md`, del diseno §3.1, §4.1, §4.4, §6.2):
`{rev, tablas: {origenes, ambientes, fuentes, puntos, tramos}}` con las celdas como texto; 200
`{rev, resumen, espacio}` con el borrador ya recalculado; 422 con el texto de la clasica (y el
borrador intacto), 409 si `rev` no es el vigente, topes de filas y de celda, cuerpo de 20 MiB como
maximo, solo cuenta con `EDITAR_HOJA`, nada se escribe en la base y todo `no-store`.

Oraculos a mano: la memoria de OF-001 (total 2 703,86 USD; con la cocineta a 3,0 m la tuberia de
agua fria de 1/2" pasa de 8,25 a 9,35 y el picado de pared de agua fria de 9,8 a 10,8: sube 3,0 +
baja 2,1 en vez de 2,5 + 1,6), los textos de la clasica y del modelo `Espacio`, y los recuentos de
filas con `sqlite3` directo. Los tipos de ruta, los topes y los textos fijos salen del diseno.
"""

from __future__ import annotations

import copy
import json
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adapters.espacio import ModoRecorrido, Recorrido
from api import caso_web, dependencias
from api.main import app
from aplicacion import hoja_borradores
from aplicacion.hoja import cambios_entre, filas_desde_espacio
from core.budget import crear_proyecto
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import sesiones
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
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
FORMA = (
    "Los datos del espacio no tienen la forma esperada: escriba cada celda como texto de hasta "
    "500 caracteres y no pase de 5000 orígenes, 1000 ambientes, 1000 fuentes, 5000 puntos y "
    "20000 vértices."
)
EXCEDE = "El cuerpo de la peticion excede el maximo de 20 MiB."
CENTINELA = "VALOR-CENTINELA"
ORIGEN = "http://127.0.0.1:8000"
ID_AJENO = "a" * 22
MIB = 1024 * 1024


# --- los casos de la prueba ---


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_edicion")
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


def _vista(navegador: TestClient, id_: str, nombre: str):
    return navegador.get(f"/v1/hoja/borradores/{id_}/vistas/{nombre}")


def _tablas(navegador: TestClient, id_: str) -> dict[str, list[dict[str, str]]]:
    """Las cinco tablas tal como las muestra el editor (R5): la semilla de una edicion."""
    return copy.deepcopy(_vista(navegador, id_, "espacio").json()["filas"])


def _editar(navegador: TestClient, ficha: str, id_: str, rev, tablas, **extra):
    cuerpo = {"rev": rev, "tablas": tablas}
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/espacio", json=cuerpo, headers=protegida(ficha), **extra
    )


def _con_alto(tablas: dict, alto: str, ambiente: str = "COC-01") -> dict:
    nuevas = copy.deepcopy(tablas)
    next(f for f in nuevas["ambientes"] if f["id"] == ambiente)["alto"] = alto
    return nuevas


def _sin_circuitos() -> dict[str, list[dict[str, str]]]:
    """Las tablas de OF-001 sin circuitos: un borrador en blanco no los tiene (se declaran al
    importar un plano) y un punto no puede citar uno que no existe."""
    tablas = copy.deepcopy(filas_desde_espacio(espacio_of001()))
    for punto in tablas["puntos"]:
        punto["circuito_id"] = ""
    return tablas


def _derivadas(cuerpo: dict) -> dict[str, Decimal]:
    return {d["partida"]: D(d["cantidad"]["exacto"]) for d in cuerpo["derivadas"]}


def _resumen(navegador: TestClient, id_: str) -> dict:
    return navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]


def _con_proyecto_nuevo(ruta: Path) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as sesion:
        crear_proyecto(sesion, "Proyecto nuevo")
        sesion.commit()
    motor.dispose()
    dependencias.cerrar_motores()


# --- 3c-B6: editar el espacio ---


def test_e1_la_cocineta_a_3_metros_recalcula_las_cantidades_de_la_memoria() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _vista(navegador, id_, "espacio").json()
    assert _derivadas(antes)["AF-TUB-PVC-1/2"] == D("8.25")
    tablas = _tablas(navegador, id_)

    respuesta = _editar(navegador, ficha, id_, 0, _con_alto(tablas, "3"))
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == 1 and cuerpo["resumen"]["rev"] == 1
    assert cuerpo["resumen"]["cambios"] == 1  # una sola celda cambio respecto a la version abierta
    espacio = cuerpo["espacio"]
    derivadas = _derivadas(espacio)
    assert derivadas["AF-TUB-PVC-1/2"] == D("9.35")  # 2,4 + (3,0 + 1,0 + 2,1) = 8,5 x 1,10
    assert derivadas["AF-PICADO-PARED"] == D("10.8")  # 5,7 + (3,0 + 2,1)
    assert derivadas["AF-LLAVE"] == D("3") and derivadas["DR-TUB-PVC-2"] == D("4.345")
    coc = next(f for f in espacio["filas"]["ambientes"] if f["id"] == "COC-01")
    assert coc["alto"] == "3"
    assert D(espacio["total"]["exacto"]) > D(antes["total"]["exacto"])
    assert espacio["total"] == cuerpo["resumen"]["total"]


def test_e1_la_respuesta_es_lo_mismo_que_piden_despues_r5_r3_y_r6() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _editar(navegador, ficha, id_, 0, _con_alto(_tablas(navegador, id_), "3")).json()
    assert _vista(navegador, id_, "espacio").json() == respuesta["espacio"]
    assert _resumen(navegador, id_) == respuesta["resumen"]
    assert _vista(navegador, id_, "presupuesto").json()["total"] == respuesta["resumen"]["total"]


def test_e1_deja_en_el_borrador_exactamente_la_celda_cambiada() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _editar(navegador, ficha, id_, 0, _con_alto(_tablas(navegador, id_), "3"))
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    cambios = cambios_entre(vivo.abierta.borrador, vivo.borrador)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("metraje", "esp_ambientes:COC-01", "alto", "2.5", "3")
    ]


def test_e1_el_alto_con_coma_es_422_con_el_texto_escrito_y_el_borrador_no_cambia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    antes = _vista(navegador, id_, "espacio").json()
    respuesta = _editar(navegador, ficha, id_, 0, _con_alto(tablas, "2,5"))
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": "ambientes, fila 2: alto: '2,5' no es un numero decimal valido"
    }
    assert respuesta.headers["cache-control"] == "no-store"
    assert _vista(navegador, id_, "espacio").json() == antes
    assert _resumen(navegador, id_)["rev"] == 0  # el rev no subio
    # el mismo rev sigue valido: la edicion rechazada no lo gasto
    assert _editar(navegador, ficha, id_, 0, _con_alto(tablas, "3")).status_code == 200


def test_e1_el_rev_no_sube_si_el_espacio_no_cambia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    respuesta = _editar(navegador, ficha, id_, 0, tablas)
    assert respuesta.status_code == 200
    assert respuesta.json()["rev"] == 0 and respuesta.json()["resumen"]["cambios"] == 0
    assert _derivadas(respuesta.json()["espacio"])["AF-TUB-PVC-1/2"] == D("8.25")
    # escribir `2.500` donde estaba `2.5` es el mismo numero: tampoco hay cambio
    igual = _editar(navegador, ficha, id_, 0, _con_alto(tablas, "2.500", "BAN-01"))
    assert igual.status_code == 200 and igual.json()["rev"] == 0


# --- 3c-B7: filas en blanco y errores del modelo ---


def test_e1_una_fila_en_blanco_no_es_un_error_ni_cambia_nada() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    tablas["ambientes"].append({})
    tablas["ambientes"].append({c: "" for c in tablas["ambientes"][0]})
    tablas["puntos"].insert(0, {"id": "", "nombre": ""})
    respuesta = _editar(navegador, ficha, id_, 0, tablas)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["rev"] == 0 and respuesta.json()["resumen"]["cambios"] == 0


def test_e1_un_id_duplicado_y_una_referencia_rota_dan_el_mensaje_del_modelo() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    duplicado = copy.deepcopy(tablas)
    duplicado["ambientes"].append(dict(duplicado["ambientes"][0]))
    respuesta = _editar(navegador, ficha, id_, 0, duplicado)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "ids repetidos en ambientes: ['BAN-01']"}
    rota = copy.deepcopy(tablas)
    next(f for f in rota["puntos"] if f["id"] == "P1")["fuente_id"] = "XX"
    respuesta = _editar(navegador, ficha, id_, 0, rota)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "el punto 'P1' cita una fuente inexistente: 'XX'"}
    assert _resumen(navegador, id_)["rev"] == 0


def test_e1_una_columna_desconocida_se_ignora_y_una_que_falta_cuenta_como_vacia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    tablas["origenes"][0]["columna_que_no_existe"] = "x"
    respuesta = _editar(navegador, ficha, id_, 0, tablas)
    assert respuesta.status_code == 200 and respuesta.json()["rev"] == 0
    sin_origen = _tablas(navegador, id_)
    del next(f for f in sin_origen["ambientes"] if f["id"] == "ZB")["origen_id"]
    respuesta = _editar(navegador, ficha, id_, 0, sin_origen)
    assert respuesta.status_code == 200 and respuesta.json()["rev"] == 1
    zb = next(f for f in respuesta.json()["espacio"]["filas"]["ambientes"] if f["id"] == "ZB")
    assert zb["origen_id"] == ""  # la clasica acepta la fila sin origen y R8 la marca


# --- 3c-B8: lo que el editor no muestra se conserva ---


def test_e1_conserva_los_circuitos_y_quita_el_recorrido_propuesto_de_un_punto_que_se_va() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    propuestos = (
        Recorrido(id="RP1", modo=ModoRecorrido.PROPUESTO, punto_id="P1"),
        Recorrido(id="RP2", modo=ModoRecorrido.PROPUESTO, punto_id="P2"),
    )
    vivo.borrador = replace(
        vivo.borrador, espacio=replace(vivo.borrador.espacio, recorridos=propuestos)
    )
    vivo.calculo = None
    tablas = _tablas(navegador, id_)
    tablas["puntos"] = [f for f in tablas["puntos"] if f["id"] != "P2"]
    respuesta = _editar(navegador, ficha, id_, 0, tablas)
    assert respuesta.status_code == 200, respuesta.text
    espacio = hoja_borradores.obtener(_huella(ficha), id_).borrador.espacio
    assert espacio.circuitos == espacio_of001().circuitos  # C1 con su orden y C2
    assert [r.id for r in espacio.recorridos] == ["RP1"]  # el de P2 se fue con el punto
    assert "P2" not in {p.id for p in espacio.puntos}


# --- 3c-B9: partida nueva toma su APU del catalogo ---


def test_e1_la_partida_que_la_version_no_tenia_toma_su_apu_del_catalogo_de_la_version() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    sin_salida = {k: v for k, v in vivo.borrador.composiciones.items() if k != "AF-SALIDA"}
    vivo.borrador = replace(vivo.borrador, composiciones=sin_salida)  # una version sin ese APU
    vivo.calculo = None
    assert _resumen(navegador, id_)["pendientes_catalogo"] == 1
    respuesta = _editar(navegador, ficha, id_, 0, _con_alto(_tablas(navegador, id_), "3"))
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["resumen"]["pendientes_catalogo"] == 0
    composiciones = hoja_borradores.obtener(_huella(ficha), id_).borrador.composiciones
    assert len(composiciones) == 30 and "AF-SALIDA" in composiciones


def test_e1_en_un_proyecto_sin_versiones_las_30_partidas_vienen_del_catalogo(
    _entorno: Path,
) -> None:
    _con_proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha, proyecto="Proyecto nuevo", version=None)
    en_blanco = _resumen(navegador, id_)
    assert (en_blanco["total"]["exacto"], en_blanco["pendientes_catalogo"]) == ("0", 0)
    respuesta = _editar(navegador, ficha, id_, 0, _sin_circuitos())
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == 1 and cuerpo["resumen"]["pendientes_catalogo"] == 0
    derivadas = _derivadas(cuerpo["espacio"])
    assert derivadas["AF-LLAVE"] == D("3") and derivadas["AF-TUB-PVC-1/2"] == D("8.25")
    assert D(cuerpo["resumen"]["total"]["exacto"]) > 0
    composiciones = hoja_borradores.obtener(_huella(ficha), id_).borrador.composiciones
    assert set(composiciones) == set(derivadas)  # cada partida derivada trajo su APU del catalogo
    assert len(composiciones) > 20
    assert len(_vista(navegador, id_, "presupuesto").json()["filas"]) == len(derivadas)


def test_e1_una_partida_sin_apu_en_el_catalogo_queda_pendiente_y_no_suma(_casos) -> None:
    """El catalogo de TI-001 no tiene ninguna de las 30 partidas de la oficina."""
    ruta = _poner(_casos["ti001"])
    _con_proyecto_nuevo(ruta)
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha, proyecto="Proyecto nuevo", version=None)
    respuesta = _editar(navegador, ficha, id_, 0, _sin_circuitos())
    assert respuesta.status_code == 200, respuesta.text
    resumen = respuesta.json()["resumen"]
    derivadas = _derivadas(respuesta.json()["espacio"])
    assert len(derivadas) > 20 and resumen["pendientes_catalogo"] == len(derivadas)
    assert resumen["total"]["exacto"] == "0"  # los pendientes no suman al total
    assert hoja_borradores.obtener(_huella(ficha), id_).borrador.composiciones == {}
    estados = [f["estado"] for f in _vista(navegador, id_, "presupuesto").json()["filas"]]
    assert estados and all(e["texto"].startswith("PENDIENTE: sin APU en el cat") for e in estados)


# --- 3c-B15: R17 en cada elaboracion ---


def _advertencias(resumen: dict) -> int:
    return next((h["total"] for h in resumen["hallazgos"] if h["severidad"] == "ADVERTENCIA"), 0)


def _r17(navegador: TestClient, id_: str) -> list[dict]:
    informe = _vista(navegador, id_, "auditoria").json()
    return [h for h in informe["hallazgos"] if h["regla"] == "R17"]


def test_e1_un_punto_de_agua_sin_fuente_da_r17_y_al_corregirlo_desaparece() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    base = _advertencias(_resumen(navegador, id_))
    assert _r17(navegador, id_) == []
    tablas = _tablas(navegador, id_)
    sin_fuente = copy.deepcopy(tablas)
    next(f for f in sin_fuente["puntos"] if f["id"] == "P1")["fuente_id"] = ""
    respuesta = _editar(navegador, ficha, id_, 0, sin_fuente)
    assert respuesta.status_code == 200, respuesta.text
    assert _advertencias(respuesta.json()["resumen"]) == base + 1  # R17 entra al resumen
    r17 = _r17(navegador, id_)
    assert [(h["severidad"], h["origen"]) for h in r17] == [("ADVERTENCIA", ["esp_puntos:P1"])]
    assert "El punto P1 (lavamanos) no tiene fuente" in r17[0]["descripcion"]
    estado = respuesta.json()["espacio"]["estado"]["esp_puntos:P1"]
    assert estado["severidad"] == "ADVERTENCIA" and "no tiene fuente" in estado["texto"]
    corregido = _editar(navegador, ficha, id_, 1, tablas)  # la fuente vuelve a ser F1
    assert corregido.status_code == 200
    assert _advertencias(corregido.json()["resumen"]) == base
    assert _r17(navegador, id_) == []  # no quedo ligada al espacio viejo


# --- 3c-B16: los cambios se comparan con la version abierta ---


def test_e1_volver_al_valor_de_la_version_abierta_deja_cero_cambios() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    assert _resumen(navegador, id_)["cambios"] == 0  # R11 y R12 a la fecha de hoy no cuentan
    uno = _editar(navegador, ficha, id_, 0, _con_alto(tablas, "3")).json()
    assert uno["resumen"]["cambios"] == 1
    dos = _editar(navegador, ficha, id_, 1, tablas).json()  # vuelve a 2.5
    assert dos["rev"] == 2 and dos["resumen"]["cambios"] == 0
    assert _derivadas(dos["espacio"])["AF-TUB-PVC-1/2"] == D("8.25")


# --- 3c-B17: topes de filas, de celda y de cuerpo ---

TOPES = [
    ("origenes", 5000),
    ("ambientes", 1000),
    ("fuentes", 1000),
    ("puntos", 5000),
    ("tramos", 20000),
]


@pytest.mark.parametrize(("tabla", "tope"), TOPES)
def test_e1_una_fila_de_mas_que_el_tope_es_422_fijo_sin_eco(tabla: str, tope: int) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = {tabla: [{"id": CENTINELA}] * (tope + 1)}
    respuesta = _editar(navegador, ficha, id_, 0, tablas)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA} and CENTINELA not in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("tabla", "tope"), TOPES)
def test_e1_exactamente_el_tope_de_filas_se_acepta(tabla: str, tope: int) -> None:
    """Las filas en blanco no se construyen: el espacio de la hoja queda como estaba."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    tablas[tabla] = tablas[tabla] + [{}] * (tope - len(tablas[tabla]))
    respuesta = _editar(navegador, ficha, id_, 0, tablas)
    assert respuesta.status_code == 200, respuesta.text[:300]
    assert respuesta.json()["rev"] == 0


def test_e1_una_celda_de_501_caracteres_es_422_sin_eco_y_una_de_500_se_acepta() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    larga = copy.deepcopy(tablas)
    next(f for f in larga["ambientes"] if f["id"] == "ZB")["nombre"] = CENTINELA * 40  # 600
    respuesta = _editar(navegador, ficha, id_, 0, larga)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA} and CENTINELA not in respuesta.text
    justa = copy.deepcopy(tablas)
    next(f for f in justa["ambientes"] if f["id"] == "ZB")["nombre"] = "n" * 500
    assert _editar(navegador, ficha, id_, 0, justa).status_code == 200
    mas = copy.deepcopy(tablas)
    next(f for f in mas["ambientes"] if f["id"] == "ZB")["nombre"] = "n" * 501
    assert _editar(navegador, ficha, id_, 1, mas).status_code == 422


def test_e1_una_fila_con_demasiadas_columnas_o_un_nombre_de_columna_largo_es_422() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    anchas = {"origenes": [{f"c{i}": "x" for i in range(41)}]}
    assert _editar(navegador, ficha, id_, 0, anchas).status_code == 422
    largas = {"origenes": [{"c" * 65: "x"}]}
    assert _editar(navegador, ficha, id_, 0, largas).status_code == 422


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"tablas": {}},  # sin rev
        {"rev": "0", "tablas": {}},  # rev como texto
        {"rev": 1.5, "tablas": {}},
        {"rev": -1, "tablas": {}},
        {"rev": True, "tablas": {}},
        {"rev": 0},  # sin tablas
        {"rev": 0, "tablas": {"otra": []}},  # una tabla que no existe
        {"rev": 0, "tablas": {"ambientes": [{"alto": 2.5}]}},  # una celda que no es texto
        {"rev": 0, "tablas": {"ambientes": {"id": "x"}}},  # una tabla que no es lista
        {"rev": 0, "tablas": {"ambientes": [["x"]]}},  # una fila que no es objeto
        {"rev": 0, "tablas": {"ambientes": [{"id": {"x": CENTINELA}}]}},
    ],
)
def test_e1_un_cuerpo_con_otra_forma_es_422_sin_eco(cuerpo: dict) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = navegador.put(
        f"/v1/hoja/borradores/{id_}/espacio", json=cuerpo, headers=protegida(ficha)
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA} and CENTINELA not in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"


def test_e1_un_id_con_forma_invalida_es_422_sin_eco() -> None:
    navegador, ficha = _ana()
    respuesta = _editar(navegador, ficha, "corto", 0, {})
    assert respuesta.status_code == 422 and "corto" not in respuesta.text


def test_e1_un_cuerpo_de_mas_de_20_mib_declarado_o_por_trozos_es_413() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    cabeceras = {**protegida(ficha), "Content-Type": "application/json"}
    ruta = f"/v1/hoja/borradores/{id_}/espacio"
    enorme = b'{"rev":0,"tablas":{"origenes":[{"id":"' + b"x" * (20 * MIB) + b'"}]}}'
    declarado = navegador.put(ruta, content=enorme, headers=cabeceras)
    assert declarado.status_code == 413 and declarado.json() == {"detalle": EXCEDE}

    def trozos() -> Iterator[bytes]:  # sin Content-Length: el middleware cuenta los bytes
        yield enorme[: 10 * MIB]
        yield enorme[10 * MIB :]

    chunked = navegador.put(ruta, content=trozos(), headers=cabeceras)
    assert chunked.status_code == 413 and chunked.json() == {"detalle": EXCEDE}
    assert _resumen(navegador, id_)["rev"] == 0  # y el borrador sigue como estaba


# --- 3c-B13 (minimo): el rev viejo da 409 y nada cambia ---


def test_e1_un_rev_viejo_es_409_y_nada_cambia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    assert _editar(navegador, ficha, id_, 0, _con_alto(tablas, "3")).status_code == 200
    despues = _vista(navegador, id_, "espacio").json()
    rezagada = _editar(navegador, ficha, id_, 0, _con_alto(tablas, "4"))  # la otra ventana vio el 0
    assert rezagada.status_code == 409
    assert rezagada.json() == {"detalle": REV_VIEJO}
    assert rezagada.headers["cache-control"] == "no-store"
    assert _vista(navegador, id_, "espacio").json() == despues
    assert _resumen(navegador, id_)["rev"] == 1
    adelantada = _editar(navegador, ficha, id_, 5, tablas)  # un rev que aun no existe tambien
    assert adelantada.status_code == 409 and adelantada.json() == {"detalle": REV_VIEJO}
    assert _editar(navegador, ficha, id_, 1, tablas).status_code == 200  # con el rev bueno, pasa


def test_e1_el_rev_se_comprueba_antes_que_el_contenido() -> None:
    """Una ventana rezagada con un dato malo recibe el 409 (recargar), no un 422 confuso."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    _editar(navegador, ficha, id_, 0, _con_alto(tablas, "3"))
    respuesta = _editar(navegador, ficha, id_, 0, _con_alto(tablas, "2,5"))
    assert respuesta.status_code == 409


def test_e1_un_borrador_ya_guardado_no_se_edita() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    hoja_borradores.obtener(_huella(ficha), id_).guardado_como = "002"  # lo hara 3d
    respuesta = _editar(navegador, ficha, id_, 0, _tablas(navegador, id_))
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": "Este borrador ya se guardó como la versión 002; abra esa versión para seguir."
    }


# --- 3c-B19: acceso, CSRF, Origin, ficha ajena y caso ---

RUTA_E1 = f"/v1/hoja/borradores/{ID_AJENO}/espacio"
CUERPO_VACIO = {"rev": 0, "tablas": {}}


def test_e1_sin_sesion_ni_clave_es_401() -> None:
    respuesta = cliente(app).put(RUTA_E1, json=CUERPO_VACIO, headers={"Origin": ORIGEN})
    assert respuesta.status_code == 401 and "detalle" in respuesta.json()
    assert respuesta.headers["cache-control"] == "no-store"


def test_e1_rita_que_revisa_y_tomas_con_clave_temporal_no_pueden() -> None:
    rita, ficha = con_cuenta(app, "rita")
    respuesta = rita.put(RUTA_E1, json=CUERPO_VACIO, headers=protegida(ficha))
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert respuesta.headers["cache-control"] == "no-store"
    tomas, ficha_tomas = con_cuenta(app, "tomas")
    assert tomas.put(RUTA_E1, json=CUERPO_VACIO, headers=protegida(ficha_tomas)).status_code == 403


def test_e1_la_clave_de_api_no_edita_la_hoja() -> None:
    respuesta = cliente(app).put(
        RUTA_E1,
        json=CUERPO_VACIO,
        headers={CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN},
    )
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": SOLO_CUENTA}
    assert respuesta.headers["cache-control"] == "no-store"


def test_e1_exige_csrf_y_origen_propio() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    ruta = f"/v1/hoja/borradores/{id_}/espacio"
    tablas = _con_alto(_tablas(navegador, id_), "3")
    cuerpo = {"rev": 0, "tablas": tablas}
    assert navegador.put(ruta, json=cuerpo, headers={"Origin": ORIGEN}).status_code == 403
    ajeno = protegida(ficha, origen="http://evil.example")
    assert navegador.put(ruta, json=cuerpo, headers=ajeno).status_code == 403
    sin_origen = protegida(ficha, origen=None)
    assert navegador.put(ruta, json=cuerpo, headers=sin_origen).status_code == 403
    assert _resumen(navegador, id_)["rev"] == 0  # ninguno de los tres edito


def test_e1_el_borrador_de_otra_ficha_no_existe_y_no_se_edita() -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()  # otra ficha de la misma cuenta: otra huella
    id_ = _abrir(uno, ficha_uno)
    tablas = _con_alto(_tablas(uno, id_), "3")
    ajeno = _editar(otro, ficha_otro, id_, 0, tablas)
    inventado = _editar(otro, ficha_otro, ID_AJENO, 0, tablas)
    assert ajeno.status_code == inventado.status_code == 404
    assert ajeno.json() == inventado.json() == {"detalle": FALTA}
    assert id_ not in ajeno.text
    assert _resumen(uno, id_)["rev"] == 0  # el dueño no se enteró


def test_e1_tras_un_cambio_de_caso_forzado_es_409_fijo_y_ninguna_base_cambia(
    _casos, _entorno
) -> None:
    navegador, ficha = _ana()
    otro = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["ti001"], otro)
    preparar_base(_entorno)
    preparar_base(otro)
    id_ = _abrir(navegador, ficha)
    tablas = _con_alto(_tablas(navegador, id_), "3")
    antes_a, antes_b = _volcado(_entorno), _volcado(otro)
    caso_web._elegidos[_huella(ficha)] = otro.resolve()  # el cambio sin pasar por `fijar`
    respuesta = _editar(navegador, ficha, id_, 0, tablas)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": OTRO_CASO}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes_a and _volcado(otro) == antes_b
    assert hoja_borradores.obtener(_huella(ficha), id_).rev == 0


def test_e1_cambiar_de_caso_olvida_el_borrador_y_editarlo_da_404(_casos, _entorno) -> None:
    navegador, ficha = _ana()
    otro = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["ti001"], otro)
    preparar_base(_entorno)
    preparar_base(otro)
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    cambio = navegador.post(
        "/v1/casos/actual", json={"nombre": otro.name}, headers=protegida(ficha)
    )
    assert cambio.status_code == 200, cambio.text
    respuesta = _editar(navegador, ficha, id_, 0, tablas)
    assert respuesta.status_code == 404 and respuesta.json() == {"detalle": FALTA}


# --- nada a la base, ningun float, no-store ---


def test_e1_no_escribe_nada_en_la_base_ni_con_exito_ni_con_error(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    antes = _volcado(_entorno)
    assert _editar(navegador, ficha, id_, 0, _con_alto(tablas, "3")).status_code == 200
    assert _editar(navegador, ficha, id_, 1, _con_alto(tablas, "2,5")).status_code == 422
    assert _editar(navegador, ficha, id_, 0, tablas).status_code == 409
    nueva = copy.deepcopy(tablas)
    nueva["puntos"].append({"id": "PX", "especialidad": "agua", "tipo": "agua_fria"})
    assert _editar(navegador, ficha, id_, 1, nueva).status_code == 422  # le faltan datos al punto
    assert _volcado(_entorno) == antes


def _sin_float(valor) -> None:
    if isinstance(valor, float):
        raise AssertionError(f"float en el JSON: {valor!r}")
    if isinstance(valor, dict):
        for v in valor.values():
            _sin_float(v)
    elif isinstance(valor, list):
        for v in valor:
            _sin_float(v)


def test_e1_ningun_numero_del_json_es_float_y_todo_monto_es_texto() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _editar(navegador, ficha, id_, 0, _con_alto(_tablas(navegador, id_), "3"))
    cuerpo = json.loads(respuesta.text, parse_float=lambda t: float("nan"))
    _sin_float(cuerpo)
    assert isinstance(cuerpo["rev"], int) and isinstance(cuerpo["resumen"]["cambios"], int)
    for monto in (cuerpo["resumen"]["total"], cuerpo["espacio"]["total"]):
        assert isinstance(monto["texto"], str) and isinstance(monto["exacto"], str)
    for derivada in cuerpo["espacio"]["derivadas"]:
        assert isinstance(derivada["cantidad"]["exacto"], str)


def test_e1_no_store_en_exito_404_409_y_422() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    tablas = _tablas(navegador, id_)
    respuestas = [
        _editar(navegador, ficha, id_, 0, _con_alto(tablas, "3")),  # 200
        _editar(navegador, ficha, ID_AJENO, 0, tablas),  # 404
        _editar(navegador, ficha, id_, 0, tablas),  # 409
        _editar(navegador, ficha, id_, 1, _con_alto(tablas, "2,5")),  # 422 de dominio
        _editar(navegador, ficha, id_, "x", tablas),  # 422 de forma
    ]
    assert [r.status_code for r in respuestas] == [200, 404, 409, 422, 422]
    assert all(r.headers["cache-control"] == "no-store" for r in respuestas)


# --- la re-estimacion del tamano llega hasta la ruta (M5) ---


def test_e1_el_registro_vuelve_a_medir_el_borrador_en_los_cambios_que_toca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    medidas: list[int] = []
    medir_real = hoja_borradores.REGISTRO._medir

    def medir(borrador) -> int:
        medidas.append(1)
        return medir_real(borrador)

    monkeypatch.setattr(hoja_borradores.REGISTRO, "_medir", medir)
    monkeypatch.setattr(hoja_borradores.REGISTRO, "_re_estimar_cada", 3)
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    assert len(medidas) == 1  # al crear
    tablas = _tablas(navegador, id_)
    for rev, alto in enumerate(["3", "2.5", "3"]):
        assert _editar(navegador, ficha, id_, rev, _con_alto(tablas, alto)).status_code == 200
        assert len(medidas) == (1 if rev < 2 else 2)  # y en el cambio 3
