"""`PUT .../cantidades`, `PUT .../parametros`, `PUT .../plan` y `POST .../plan/secuencial`
(E2 a E5): la edicion del presupuesto, los parametros y el plan de la hoja (T10, 3c-2).

Contrato (`docs/bitacora/2026-10-19-hoja-3c2-contrato-rutas.md`, del diseno §3.2, §4.1, §4.4, §6.2):
cada ruta recibe `{rev, ...}` con los valores como texto y responde `{rev, resumen, <vista>}` con el
borrador ya recalculado; 422 con el texto de la clasica (y el borrador intacto), 409 si `rev` no es
el vigente (se comprueba ANTES que el contenido), topes de filas y de celda, solo cuenta con
`EDITAR_HOJA`, nada se escribe en la base y todo `no-store`.

Oraculos a mano (ninguno sale del codigo bajo prueba):

* OF-001 (memoria): total 2 703,86 USD; CV 2 137,44; PE 1 530,49 en el «Dia 23» (56,60 %).
* P13: `administracion = 0.20` da total 2 821,42; PE 1 763,39; 62,50 %; un solo cambio
  `("parametro", "administracion", "valor", "0.15", "0.20")`.
* P15: AF-LLAVE de 3 a 5, Δtotal = 2 x CD x 1,15 x 1,10 con CD = 10,4338 (a mano, ver el diseno
  §6.2 3c-B3): 26,39748; se compara el valor EXACTO con tolerancia 0,001, no el texto a 2 decimales.
* P16/P19: los textos de H:861-863 y H:1202-1212 con la posicion de la fila a mano (AF-LLAVE es el
  renglon 3).
* P20: el plan secuencial de OF-001 tiene 30 periodos «Dia n» y la curva cierra en 2 703,86.
"""

from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

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
from seguridad import sesiones
from tests.fixtures import caso_ti001
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
FORMA_CANTIDADES = (
    "Las cantidades no tienen la forma esperada: envíe cada renglón como clave y cantidad en "
    "texto de hasta 500 caracteres, con no más de 20000 renglones."
)
FORMA_PARAMETROS = (
    "Los parámetros no tienen la forma esperada: envíe fcas, bono_alimentacion, administracion y "
    "utilidad, cada uno como texto de hasta 500 caracteres."
)
FORMA_PLAN = (
    "El plan no tiene la forma esperada: envíe periodos distintos (de 1 a 500) y cada fracción "
    "como texto de hasta 500 caracteres, con no más de 5000 partidas."
)
FORMA_REV = "La petición debe traer el rev del borrador, un número entero."
RENGLONES = (
    "Las cantidades enviadas no corresponden a los renglones del presupuesto: vuelva a cargarlo."
)
SIN_PLAN = "Esta versión no tiene plan de trabajo: cree primero el plan secuencial."
YA_TIENE_PLAN = "Esta versión ya tiene plan de trabajo: edítelo en la matriz del plan."
PARTIDA_REPETIDA = "plan: una partida aparece en más de una fila; deje una sola fila por partida."
MATRIZ_COMPLETA = (
    "plan: la matriz debe traer exactamente las partidas del presupuesto, una fila por cada una: "
    "vuelva a cargarla."
)
CENTINELA = "VALOR-CENTINELA"
ORIGEN = "http://127.0.0.1:8000"
ID_AJENO = "a" * 22
MIB = 1024 * 1024
LLAVE = "AF-LLAVE|esp_fuentes:F1;esp_fuentes:FC1;esp_puntos:P1;esp_puntos:P2;esp_puntos:PC1"
TEXTOS = {
    "fcas": "6.00",
    "bono_alimentacion": "5.8100",
    "administracion": "0.15",
    "utilidad": "0.10",
}


# --- los casos de la prueba ---


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_secciones")
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


def _vista(navegador: TestClient, id_: str, nombre: str) -> dict:
    return navegador.get(f"/v1/hoja/borradores/{id_}/vistas/{nombre}").json()


def _resumen(navegador: TestClient, id_: str) -> dict:
    return navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]


def _con_proyecto_nuevo(ruta: Path) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as sesion:
        crear_proyecto(sesion, "Proyecto nuevo")
        sesion.commit()
    motor.dispose()
    dependencias.cerrar_motores()


def _total(resumen: dict) -> Decimal:
    return D(resumen["total"]["exacto"])


def _cantidades(navegador, ficha, id_, rev, filas, **extra):
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/cantidades",
        json={"rev": rev, "filas": filas},
        headers=protegida(ficha),
        **extra,
    )


def _parametros(navegador, ficha, id_, rev, **cambios):
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/parametros",
        json={"rev": rev, **TEXTOS, **cambios},
        headers=protegida(ficha),
    )


def _plan(navegador, ficha, id_, rev, etiquetas, filas):
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/plan",
        json={"rev": rev, "etiquetas": etiquetas, "filas": filas},
        headers=protegida(ficha),
    )


def _secuencial(navegador, ficha, id_, rev):
    return navegador.post(
        f"/v1/hoja/borradores/{id_}/plan/secuencial", json={"rev": rev}, headers=protegida(ficha)
    )


def _matriz(navegador, id_, **cambios: dict[str, str]) -> tuple[list[str], list[dict]]:
    """La matriz del plan tal como la muestra R8, con los cambios por partida."""
    vista = _vista(navegador, id_, "plan")
    filas = copy.deepcopy(vista["filas"])
    for fila in filas:
        fila["valores"].update(cambios.get(fila["partida"], {}))
    return vista["etiquetas"], filas


def _sin_plan(ficha: str, id_: str) -> None:
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    vivo.borrador = replace(vivo.borrador, plan=None)
    vivo.calculo = None


def _por_dia(vista_plan: dict) -> dict[str, dict]:
    return {p["periodo"].split(" [")[0]: p for p in vista_plan["curva"]}


# --- E2: cantidades escritas a mano (3c-B3, 3c-B4, 3c-B5) ---


def test_e2_la_llave_de_3_a_5_suma_26_39748_marca_r8_y_registra_el_cambio() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _resumen(navegador, id_)
    assert abs(_total(antes) - D("2703.86")) <= D("0.01")
    respuesta = _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "5"}])
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert (
        cuerpo["rev"] == 1 and cuerpo["resumen"]["rev"] == 1 and cuerpo["resumen"]["cambios"] == 1
    )
    delta = _total(cuerpo["resumen"]) - _total(antes)
    assert abs(delta - D("26.39748")) <= D("0.001")  # exacto, no el texto a 2 decimales
    fila = next(f for f in cuerpo["presupuesto"]["filas"] if f["clave"] == LLAVE)
    assert (fila["cantidad"], fila["cantidad_calculada"], fila["escrita"]) == ("5", "3", True)
    assert fila["estado"]["severidad"] == "ADVERTENCIA"  # R8: cantidad escrita a mano
    assert cuerpo["presupuesto"]["total"] == cuerpo["resumen"]["total"]
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    cambios = cambios_entre(vivo.abierta.borrador, vivo.borrador)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("cantidad", LLAVE, "cantidad", "3", "5")
    ]


def test_e2_la_respuesta_es_lo_mismo_que_piden_despues_r6_y_r3() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "5"}]).json()
    assert _vista(navegador, id_, "presupuesto") == respuesta["presupuesto"]
    assert _resumen(navegador, id_) == respuesta["resumen"]


def test_e2_escribir_el_valor_calculado_no_es_una_cantidad_escrita() -> None:
    """3c-B4: «3» (o «3.000») no cambia nada; volver a 3 tras escribir 5 libera el renglon."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    for texto in ("3", "3.000"):
        igual = _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": texto}])
        assert igual.status_code == 200 and igual.json()["rev"] == 0
        assert igual.json()["resumen"]["cambios"] == 0
    assert _cantidades(navegador, ficha, id_, 0, []).json()["rev"] == 0  # ni filas ni cambio
    _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "5"}])
    vuelta = _cantidades(navegador, ficha, id_, 1, [{"clave": LLAVE, "cantidad": "3"}]).json()
    assert vuelta["rev"] == 2 and vuelta["resumen"]["cambios"] == 0
    fila = next(f for f in vuelta["presupuesto"]["filas"] if f["clave"] == LLAVE)
    assert (fila["cantidad"], fila["escrita"]) == ("3", False)
    assert abs(_total(vuelta["resumen"]) - D("2703.86")) <= D("0.01")


def test_e2_las_filas_que_no_se_mandan_conservan_su_cantidad_vigente() -> None:
    """El cliente manda solo lo tocado: una segunda edicion no borra la primera."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "5"}])
    salida = next(
        f["clave"]
        for f in _vista(navegador, id_, "presupuesto")["filas"]
        if f["partida"] == "AF-SALIDA"
    )
    dos = _cantidades(navegador, ficha, id_, 1, [{"clave": salida, "cantidad": "4"}]).json()
    por_clave = {f["clave"]: f for f in dos["presupuesto"]["filas"]}
    assert (por_clave[LLAVE]["cantidad"], por_clave[LLAVE]["escrita"]) == ("5", True)
    assert (por_clave[salida]["cantidad"], por_clave[salida]["escrita"]) == ("4", True)
    assert dos["resumen"]["cambios"] == 2


def test_e2_una_cantidad_negativa_dice_la_fila_de_la_tabla_completa_aunque_se_mande_una_sola() -> (
    None
):
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _vista(navegador, id_, "presupuesto")
    respuesta = _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "-1"}])
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": (
            "presupuesto, fila 3 (AF-LLAVE): la cantidad no puede ser negativa; "
            "escriba cero o una cantidad positiva"
        )
    }
    assert respuesta.headers["cache-control"] == "no-store"
    assert _vista(navegador, id_, "presupuesto") == antes and _resumen(navegador, id_)["rev"] == 0
    # el mismo rev sigue valido: la edicion rechazada no lo gasto
    assert (
        _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "0"}]).status_code
        == 200
    )


@pytest.mark.parametrize(
    ("texto", "detalle"),
    [
        ("2,5", "presupuesto, fila 3 (AF-LLAVE): cantidad: '2,5' no es un numero decimal valido"),
        (
            "mucho",
            "presupuesto, fila 3 (AF-LLAVE): cantidad: 'mucho' no es un numero decimal valido",
        ),
        ("", "presupuesto, fila 3 (AF-LLAVE): cantidad: '' no es un numero decimal valido"),
        ("Infinity", "presupuesto, fila 3 (AF-LLAVE): cantidad: 'Infinity' no es un monto finito"),
    ],
)
def test_e2_el_texto_que_no_es_un_decimal_es_422_con_el_mensaje_de_la_clasica(
    texto, detalle
) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": texto}])
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": detalle}
    assert _resumen(navegador, id_)["rev"] == 0


def test_e2_un_renglon_desconocido_o_repetido_es_422_y_no_se_ignora_en_silencio() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    desconocido = _cantidades(navegador, ficha, id_, 0, [{"clave": "NO-EXISTE|x", "cantidad": "9"}])
    assert desconocido.status_code == 422 and desconocido.json() == {"detalle": RENGLONES}
    repetido = _cantidades(
        navegador,
        ficha,
        id_,
        0,
        [{"clave": LLAVE, "cantidad": "5"}, {"clave": LLAVE, "cantidad": "6"}],
    )
    assert repetido.status_code == 422 and repetido.json() == {"detalle": RENGLONES}
    assert "NO-EXISTE" not in desconocido.text
    assert _resumen(navegador, id_)["rev"] == 0


def test_e2_en_ti001_sin_espacio_se_escribe_la_cantidad_de_un_renglon_de_la_version(_casos) -> None:
    _poner(_casos["ti001"])
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha, NOMBRE_TI001, caso_ti001.CODIGO)
    filas = _vista(navegador, id_, "presupuesto")["filas"]
    rack = filas[0]
    assert rack["partida"] == "TI-RACK" and rack["cantidad"] == "1"
    antes = _total(_resumen(navegador, id_))
    respuesta = _cantidades(navegador, ficha, id_, 0, [{"clave": rack["clave"], "cantidad": "2"}])
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    nuevo = next(f for f in cuerpo["presupuesto"]["filas"] if f["clave"] == rack["clave"])
    assert (nuevo["cantidad"], nuevo["escrita"]) == ("2", True) and cuerpo["resumen"][
        "cambios"
    ] == 1
    # el total sube exactamente un precio unitario del rack (1 unidad mas)
    assert abs(_total(cuerpo["resumen"]) - antes - D(rack["pu"]["exacto"])) <= D("0.0001")


# --- E3: parametros del proyecto (3c-B1, 3c-B2) ---


def test_e3_administracion_020_da_los_literales_de_p13() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _parametros(navegador, ficha, id_, 0, administracion="0.20")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == 1 and cuerpo["resumen"]["cambios"] == 1
    assert abs(_total(cuerpo["resumen"]) - D("2821.42")) <= D("0.01")
    equilibrio = _vista(navegador, id_, "equilibrio")
    assert abs(D(equilibrio["punto"]["exacto"]) - D("1763.39")) <= D("0.01")
    assert abs(D(equilibrio["porcentaje"]["exacto"]) - D("62.50")) <= D("0.01")
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    cambios = cambios_entre(vivo.abierta.borrador, vivo.borrador)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("parametro", "administracion", "valor", "0.15", "0.20")
    ]
    campos = {c["clave"]: c["valor"] for c in cuerpo["parametros"]["campos"]}
    assert campos == {**TEXTOS, "administracion": "0.20"}
    assert cuerpo["parametros"]["total"] == cuerpo["resumen"]["total"]
    assert (cuerpo["parametros"]["moneda_proyecto"], cuerpo["parametros"]["puede_convertir"]) == (
        "USD",
        True,
    )


def test_e3_la_respuesta_es_lo_mismo_que_piden_despues_r10_y_r3() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _parametros(navegador, ficha, id_, 0, utilidad="0.12").json()
    assert _vista(navegador, id_, "parametros") == respuesta["parametros"]
    assert _resumen(navegador, id_) == respuesta["resumen"]


def test_e3_un_parametro_invalido_es_422_con_el_texto_de_la_clasica_y_conserva_los_previos() -> (
    None
):
    """3c-B2: «mucho» no es un numero; la hoja sigue con el ultimo valor valido."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    assert _parametros(navegador, ficha, id_, 0, fcas="5.00").status_code == 200  # fcas previo
    antes = _vista(navegador, id_, "parametros")
    respuesta = _parametros(navegador, ficha, id_, 1, fcas="5.00", utilidad="mucho")
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": "parametros: utilidad: 'mucho' no es un numero decimal valido"
    }
    assert respuesta.headers["cache-control"] == "no-store"
    despues = _vista(navegador, id_, "parametros")
    assert despues == antes and _resumen(navegador, id_)["rev"] == 1  # el rev no subio
    campos = {c["clave"]: c["valor"] for c in despues["campos"]}
    assert campos["fcas"] == "5.00" and campos["utilidad"] == "0.10"
    assert _parametros(navegador, ficha, id_, 1, fcas="5.00", utilidad="0.12").status_code == 200


@pytest.mark.parametrize(
    ("campo", "texto", "detalle"),
    [
        ("fcas", "6,00", "parametros: fcas: '6,00' no es un numero decimal valido"),
        ("administracion", "", "parametros: administracion: '' no es un numero decimal valido"),
        (
            "bono_alimentacion",
            "Infinity",
            "parametros: bono_alimentacion: 'Infinity' no es un monto finito",
        ),
        ("fcas", "-1", "parametros: fcas no puede ser negativo: -1"),
    ],
)
def test_e3_otros_textos_invalidos_con_el_mensaje_de_la_clasica(campo, texto, detalle) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _parametros(navegador, ficha, id_, 0, **{campo: texto})
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": detalle}
    assert _resumen(navegador, id_)["rev"] == 0


def test_e3_el_mismo_valor_escrito_de_otra_forma_no_cambia_nada() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    igual = _parametros(navegador, ficha, id_, 0, administracion="0.150", fcas="6")
    assert igual.status_code == 200
    assert igual.json()["rev"] == 0 and igual.json()["resumen"]["cambios"] == 0


# --- E4: la matriz del plan (3c-B12) ---


def test_e4_repartir_las_llaves_entre_el_dia_3_y_el_dia_30_mueve_la_mitad_y_la_curva_cierra() -> (
    None
):
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _por_dia(_vista(navegador, id_, "plan"))
    etiquetas, filas = _matriz(navegador, id_, **{"AF-LLAVE": {"Dia 3": "0.5", "Dia 30": "0.5"}})
    respuesta = _plan(navegador, ficha, id_, 0, etiquetas, filas)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == 1 and cuerpo["resumen"]["hay_plan"] is True
    plan = cuerpo["plan"]
    assert plan["hay_plan"] is True and plan["etiquetas"] == etiquetas
    fila = next(f for f in plan["filas"] if f["partida"] == "AF-LLAVE")
    assert (fila["valores"]["Dia 3"], fila["valores"]["Dia 30"]) == ("0.5", "0.5")
    despues = _por_dia(plan)
    mitad = D("19.798")  # a mano: PU 13,1989 x 3 llaves = 39,5967; la mitad cambia de periodo
    assert abs(
        D(despues["Dia 30"]["monto"]["exacto"]) - D(antes["Dia 30"]["monto"]["exacto"]) - mitad
    ) <= D("0.01")
    assert abs(
        D(despues["Dia 3"]["monto"]["exacto"]) - (D(antes["Dia 3"]["monto"]["exacto"]) - mitad)
    ) <= D("0.01")
    ultimo = plan["curva"][-1]
    assert abs(D(ultimo["acumulado"]["exacto"]) - D("2703.86")) <= D("0.01")
    assert abs(_total(cuerpo["resumen"]) - D("2703.86")) <= D("0.01")  # el total no cambia
    assert cuerpo["resumen"]["cambios"] == 2  # Dia 3: 1 -> 0.5 y Dia 30: 0 -> 0.5
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    cambios = cambios_entre(vivo.abierta.borrador, vivo.borrador)
    assert [(c.objeto, c.clave, c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("plan", "AF-LLAVE", "Dia 3", "1", "0.5"),
        ("plan", "AF-LLAVE", "Dia 30", "0", "0.5"),
    ]


def test_e4_la_respuesta_es_lo_mismo_que_piden_despues_r8_y_r3() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    etiquetas, filas = _matriz(navegador, id_, **{"AF-LLAVE": {"Dia 3": "0.5", "Dia 4": "0.5"}})
    respuesta = _plan(navegador, ficha, id_, 0, etiquetas, filas).json()
    assert _vista(navegador, id_, "plan") == respuesta["plan"]
    assert _resumen(navegador, id_) == respuesta["resumen"]


def test_e4_un_plan_que_no_suma_1_es_422_con_el_texto_de_la_clasica_y_el_plan_no_cambia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _vista(navegador, id_, "plan")
    etiquetas, filas = _matriz(navegador, id_, **{"AF-LLAVE": {"Dia 3": "0.5"}})
    respuesta = _plan(navegador, ficha, id_, 0, etiquetas, filas)
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": (
            "plan, partida AF-LLAVE: las fracciones suman 0.5 y deben sumar exactamente 1; "
            "repartala entre los periodos hasta completar 1"
        )
    }
    assert respuesta.headers["cache-control"] == "no-store"
    assert _vista(navegador, id_, "plan") == antes and _resumen(navegador, id_)["rev"] == 0


@pytest.mark.parametrize(
    ("celdas", "detalle"),
    [
        (
            {"Dia 3": "-1", "Dia 4": "2"},
            "plan, partida AF-LLAVE: la fraccion de Dia 3 no puede ser negativa",
        ),
        (
            {"Dia 3": "0,5", "Dia 4": "0.5"},
            "plan, partida AF-LLAVE: Dia 3: '0,5' no es un numero decimal valido",
        ),
    ],
)
def test_e4_fraccion_negativa_o_con_coma_son_422_con_el_texto_de_la_clasica(
    celdas, detalle
) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    etiquetas, filas = _matriz(navegador, id_, **{"AF-LLAVE": celdas})
    respuesta = _plan(navegador, ficha, id_, 0, etiquetas, filas)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": detalle}
    assert _resumen(navegador, id_)["rev"] == 0


def test_e4_una_celda_vacia_vale_cero() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    etiquetas, filas = _matriz(navegador, id_, **{"AF-LLAVE": {"Dia 3": "", "Dia 4": "1"}})
    respuesta = _plan(navegador, ficha, id_, 0, etiquetas, filas)
    assert respuesta.status_code == 200, respuesta.text
    fila = next(f for f in respuesta.json()["plan"]["filas"] if f["partida"] == "AF-LLAVE")
    assert (fila["valores"]["Dia 3"], fila["valores"]["Dia 4"]) == ("0", "1")


def test_e4_la_matriz_sin_tocar_no_cambia_nada_ni_siquiera_en_ti001(_casos) -> None:
    """TI-001 reparte varias partidas por periodo: reconstruir la matriz las ordena por partida,
    pero el plan es el mismo y `rev` no sube."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    etiquetas, filas = _matriz(navegador, id_)
    igual = _plan(navegador, ficha, id_, 0, etiquetas, filas)
    assert igual.status_code == 200 and igual.json()["rev"] == 0
    _poner(_casos["ti001"])
    otro, ficha_otro = _ana()
    id_ti = _abrir(otro, ficha_otro, NOMBRE_TI001, caso_ti001.CODIGO)
    etiquetas, filas = _matriz(otro, id_ti)
    assert etiquetas == [f"Dia {n}" for n in range(1, 11)]
    igual = _plan(otro, ficha_otro, id_ti, 0, etiquetas, filas)
    assert igual.status_code == 200 and igual.json()["rev"] == 0
    assert igual.json()["resumen"]["cambios"] == 0


def test_e4_dos_filas_de_la_misma_partida_son_422_y_no_duplican_la_ejecucion() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    etiquetas, filas = _matriz(navegador, id_)
    respuesta = _plan(navegador, ficha, id_, 0, etiquetas, [*filas, copy.deepcopy(filas[2])])
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": PARTIDA_REPETIDA}
    assert _resumen(navegador, id_)["rev"] == 0


def test_e4_una_partida_desconocida_o_que_falta_es_422_y_el_plan_no_queda_parcial() -> None:
    """MENOR de 3c-2: la matriz debe cubrir EXACTAMENTE las partidas del presupuesto."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _vista(navegador, id_, "plan")
    etiquetas, filas = _matriz(navegador, id_)
    desconocida = [*filas, {"partida": "ZZ-NUEVA", "valores": {"Dia 1": "1"}}]
    falta_una = [f for f in filas if f["partida"] != "AF-LLAVE"]
    cambiada = [{**f, "partida": "ZZ-NUEVA"} if f["partida"] == "AF-LLAVE" else f for f in filas]
    for matriz in (desconocida, falta_una, cambiada, [], filas[:1]):
        respuesta = _plan(navegador, ficha, id_, 0, etiquetas, matriz)
        assert respuesta.status_code == 422 and respuesta.json() == {"detalle": MATRIZ_COMPLETA}
        assert respuesta.headers["cache-control"] == "no-store"
    assert _vista(navegador, id_, "plan") == antes and _resumen(navegador, id_)["rev"] == 0
    # el rev no se gasto: la matriz completa pasa con el mismo rev
    assert _plan(navegador, ficha, id_, 0, etiquetas, filas).status_code == 200


def test_e4_una_fila_con_la_partida_vacia_se_ignora_y_la_matriz_completa_pasa() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    etiquetas, filas = _matriz(navegador, id_, **{"AF-LLAVE": {"Dia 3": "0.5", "Dia 4": "0.5"}})
    respuesta = _plan(
        navegador, ficha, id_, 0, etiquetas, [*filas, {"partida": "", "valores": {"Dia 1": "7"}}]
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["rev"] == 1


def test_e4_la_cobertura_se_mira_despues_de_las_filas_repetidas_y_antes_de_las_fracciones() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    etiquetas, filas = _matriz(navegador, id_)
    # repetida Y sin otra partida: manda el mensaje de la repetida
    repetida = [filas[0], copy.deepcopy(filas[0])]
    assert _plan(navegador, ficha, id_, 0, etiquetas, repetida).json() == {
        "detalle": PARTIDA_REPETIDA
    }
    # incompleta Y con una suma mala: manda la cobertura
    mala = [{**filas[0], "valores": {**filas[0]["valores"], "Dia 1": "7"}}]
    assert _plan(navegador, ficha, id_, 0, etiquetas, mala).json() == {"detalle": MATRIZ_COMPLETA}


def test_e4_sin_plan_es_409_y_se_comprueba_despues_de_rev_y_antes_del_contenido() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    etiquetas, filas = _matriz(navegador, id_)
    _sin_plan(ficha, id_)
    respuesta = _plan(navegador, ficha, id_, 0, etiquetas, filas)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": SIN_PLAN}
    assert respuesta.headers["cache-control"] == "no-store"
    con_dato_malo = _plan(navegador, ficha, id_, 0, etiquetas, [{"partida": "X", "valores": {}}])
    assert con_dato_malo.status_code == 409  # el estado manda sobre el contenido
    assert _plan(navegador, ficha, id_, 7, etiquetas, filas).json() == {"detalle": REV_VIEJO}


# --- E5: el plan secuencial (3c-B12, P20) ---


def test_e5_el_plan_secuencial_de_of001_tiene_30_periodos_y_la_curva_cierra_en_el_total() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _sin_plan(ficha, id_)
    assert _vista(navegador, id_, "plan")["hay_plan"] is False
    respuesta = _secuencial(navegador, ficha, id_, 0)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == 1 and cuerpo["resumen"]["hay_plan"] is True
    plan = cuerpo["plan"]
    assert plan["hay_plan"] is True and plan["etiquetas"] == [f"Dia {n}" for n in range(1, 31)]
    primera = plan["filas"][0]
    assert primera["partida"] == "AF-CODO-1/2" and primera["valores"]["Dia 1"] == "1"
    assert plan["curva"][-1]["periodo"].split(" [")[0] == "Dia 30"
    assert abs(D(plan["curva"][-1]["acumulado"]["exacto"]) - D("2703.86")) <= D("0.01")
    assert _vista(navegador, id_, "plan") == plan
    assert cuerpo["resumen"]["cambios"] == 0  # la 001 ya tenia ese mismo plan secuencial


def test_e5_con_plan_es_409_y_nada_cambia() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = _secuencial(navegador, ficha, id_, 0)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": YA_TIENE_PLAN}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _resumen(navegador, id_)["rev"] == 0
    assert _secuencial(navegador, ficha, id_, 3).json() == {"detalle": REV_VIEJO}  # rev primero


def test_e5_en_un_proyecto_sin_versiones_no_revienta(_entorno: Path) -> None:
    """Sin renglones valorados el plan secuencial queda vacio, sin error."""
    _con_proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha, proyecto="Proyecto nuevo", version=None)
    respuesta = _secuencial(navegador, ficha, id_, 0)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["plan"]["curva"] == []
    assert _resumen(navegador, id_)["total"]["exacto"] == "0"


# --- la forma del cuerpo: 422 fijo, sin eco, antes del resto (3c-B17) ---


@pytest.mark.parametrize(
    ("ruta", "metodo", "cuerpo", "mensaje"),
    [
        ("cantidades", "put", {"filas": []}, FORMA_CANTIDADES),
        ("cantidades", "put", {"rev": "0", "filas": []}, FORMA_CANTIDADES),
        ("cantidades", "put", {"rev": 0}, FORMA_CANTIDADES),
        ("cantidades", "put", {"rev": 0, "filas": [{"clave": "x"}]}, FORMA_CANTIDADES),
        (
            "cantidades",
            "put",
            {"rev": 0, "filas": [{"clave": "x", "cantidad": 5}]},
            FORMA_CANTIDADES,
        ),
        (
            "cantidades",
            "put",
            {"rev": 0, "filas": [{"clave": CENTINELA, "cantidad": "1", "otra": "x"}]},
            FORMA_CANTIDADES,
        ),
        (
            "cantidades",
            "put",
            {"rev": 0, "filas": [{"clave": "x" * 501, "cantidad": "1"}]},
            FORMA_CANTIDADES,
        ),
        (
            "cantidades",
            "put",
            {"rev": 0, "filas": [{"clave": "x", "cantidad": "1" * 501}]},
            FORMA_CANTIDADES,
        ),
        (
            "cantidades",
            "put",
            {"rev": 0, "filas": [{"clave": "x", "cantidad": "1"}] * 20001},
            FORMA_CANTIDADES,
        ),
        ("cantidades", "put", {"rev": 0, "filas": [], "extra": CENTINELA}, FORMA_CANTIDADES),
        ("parametros", "put", {"rev": 0, **TEXTOS, "utilidad": 0.1}, FORMA_PARAMETROS),
        ("parametros", "put", {"rev": 0, "fcas": "6"}, FORMA_PARAMETROS),
        ("parametros", "put", {**TEXTOS}, FORMA_PARAMETROS),
        ("parametros", "put", {"rev": 0, **TEXTOS, "utilidad": "1" * 501}, FORMA_PARAMETROS),
        ("parametros", "put", {"rev": 0, **TEXTOS, "otro": CENTINELA}, FORMA_PARAMETROS),
        ("parametros", "put", {"rev": -1, **TEXTOS}, FORMA_PARAMETROS),
        ("plan", "put", {"rev": 0, "etiquetas": [], "filas": []}, FORMA_PLAN),
        ("plan", "put", {"rev": 0, "etiquetas": ["Dia 1", "Dia 1"], "filas": []}, FORMA_PLAN),
        ("plan", "put", {"rev": 0, "etiquetas": ["partida"], "filas": []}, FORMA_PLAN),
        (
            "plan",
            "put",
            {"rev": 0, "etiquetas": [f"D{n}" for n in range(501)], "filas": []},
            FORMA_PLAN,
        ),
        (
            "plan",
            "put",
            {"rev": 0, "etiquetas": ["Dia 1"], "filas": [{"partida": "A"}] * 5001},
            FORMA_PLAN,
        ),
        (
            "plan",
            "put",
            {
                "rev": 0,
                "etiquetas": ["Dia 1"],
                "filas": [{"partida": "A", "valores": {"Dia 1": 1}}],
            },
            FORMA_PLAN,
        ),
        ("plan", "put", {"rev": 0, "etiquetas": ["Dia 1"], "filas": [{"valores": {}}]}, FORMA_PLAN),
        ("plan", "put", {"rev": 0, "etiquetas": ["Dia 1"]}, FORMA_PLAN),
        (
            "plan",
            "put",
            {"rev": 0, "etiquetas": ["Dia 1"], "filas": [{"partida": "A", "valores": {}, "x": 1}]},
            FORMA_PLAN,
        ),
        ("plan", "put", {"etiquetas": ["Dia 1"], "filas": []}, FORMA_PLAN),
        ("plan/secuencial", "post", {}, FORMA_REV),
        ("plan/secuencial", "post", {"rev": "0"}, FORMA_REV),
        ("plan/secuencial", "post", {"rev": 1.5}, FORMA_REV),
        ("plan/secuencial", "post", {"rev": True}, FORMA_REV),
        ("plan/secuencial", "post", {"rev": 0, "otro": CENTINELA}, FORMA_REV),
    ],
)
def test_un_cuerpo_con_otra_forma_es_422_fijo_sin_eco_y_con_no_store(
    ruta, metodo, cuerpo, mensaje
) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuesta = getattr(navegador, metodo)(
        f"/v1/hoja/borradores/{id_}/{ruta}", json=cuerpo, headers=protegida(ficha)
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": mensaje} and CENTINELA not in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert _resumen(navegador, id_)["rev"] == 0


def test_exactamente_los_topes_de_forma_se_aceptan() -> None:
    """500 etiquetas, 5000 filas de plan y 20000 filas de cantidades no son error de forma."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    # 20000 renglones desconocidos: pasa la forma y la ruta contesta el 422 de dominio
    exacto = _cantidades(navegador, ficha, id_, 0, [{"clave": "x", "cantidad": "1"}] * 20000)
    assert exacto.status_code == 422 and exacto.json() == {"detalle": RENGLONES}
    etiquetas = [f"E{n}" for n in range(500)]
    plan = _plan(navegador, ficha, id_, 0, etiquetas, [{"partida": "", "valores": {}}] * 5000)
    # la FORMA es valida (500 periodos, 5000 filas); desde 3c-3 el dominio exige la matriz
    # completa, asi que las filas vacias (que se ignoran) no cubren las partidas: 422 de dominio
    assert plan.status_code == 422 and plan.json() == {"detalle": MATRIZ_COMPLETA}
    assert _resumen(navegador, id_)["rev"] == 0


def test_un_id_con_forma_invalida_es_422_sin_eco() -> None:
    navegador, ficha = _ana()
    for ruta, metodo, cuerpo in (
        ("cantidades", "put", {"rev": 0, "filas": []}),
        ("parametros", "put", {"rev": 0, **TEXTOS}),
        ("plan", "put", {"rev": 0, "etiquetas": ["Dia 1"], "filas": []}),
        ("plan/secuencial", "post", {"rev": 0}),
    ):
        respuesta = getattr(navegador, metodo)(
            f"/v1/hoja/borradores/corto/{ruta}", json=cuerpo, headers=protegida(ficha)
        )
        assert respuesta.status_code == 422 and "corto" not in respuesta.text


def test_un_cuerpo_de_mas_de_20_mib_declarado_o_por_trozos_es_413() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    cabeceras = {**protegida(ficha), "Content-Type": "application/json"}
    ruta = f"/v1/hoja/borradores/{id_}/cantidades"
    enorme = b'{"rev":0,"filas":[{"clave":"' + b"x" * (20 * MIB) + b'","cantidad":"1"}]}'
    declarado = navegador.put(ruta, content=enorme, headers=cabeceras)
    assert declarado.status_code == 413 and declarado.json() == {"detalle": EXCEDE}

    def trozos() -> Iterator[bytes]:
        yield enorme[: 10 * MIB]
        yield enorme[10 * MIB :]

    chunked = navegador.put(ruta, content=trozos(), headers=cabeceras)
    assert chunked.status_code == 413 and chunked.json() == {"detalle": EXCEDE}
    assert _resumen(navegador, id_)["rev"] == 0


# --- 3c-B13: el rev viejo da 409 y nada cambia, en E2 a E5 ---

PEDIDOS = [
    ("cantidades", lambda r: {"rev": r, "filas": [{"clave": LLAVE, "cantidad": "5"}]}, "put"),
    ("parametros", lambda r: {"rev": r, **TEXTOS, "administracion": "0.20"}, "put"),
    ("plan", lambda r: {"rev": r, "etiquetas": ["Dia 1"], "filas": []}, "put"),
    ("plan/secuencial", lambda r: {"rev": r}, "post"),
]
IDS = [p[0] for p in PEDIDOS]


def _enviar(navegador, ficha, id_, ruta, metodo, cuerpo):
    return getattr(navegador, metodo)(
        f"/v1/hoja/borradores/{id_}/{ruta}", json=cuerpo, headers=protegida(ficha)
    )


@pytest.mark.parametrize(("ruta", "cuerpo", "metodo"), PEDIDOS, ids=IDS)
def test_un_rev_viejo_o_adelantado_es_409_y_nada_cambia(ruta, cuerpo, metodo) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    assert _parametros(navegador, ficha, id_, 0, utilidad="0.12").status_code == 200  # rev 1
    antes = (_vista(navegador, id_, "presupuesto"), _vista(navegador, id_, "plan"))
    estado = _resumen(navegador, id_)
    for rev in (0, 5):
        respuesta = _enviar(navegador, ficha, id_, ruta, metodo, cuerpo(rev))
        assert respuesta.status_code == 409 and respuesta.json() == {"detalle": REV_VIEJO}
        assert respuesta.headers["cache-control"] == "no-store"
    assert (_vista(navegador, id_, "presupuesto"), _vista(navegador, id_, "plan")) == antes
    assert _resumen(navegador, id_) == estado


def test_el_rev_se_comprueba_antes_que_el_contenido_en_e2_e3_y_e4() -> None:
    """Una ventana rezagada con un dato malo recibe el 409 (recargar), no un 422 confuso."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    _parametros(navegador, ficha, id_, 0, utilidad="0.12")
    malos = [
        _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "-1"}]),
        _parametros(navegador, ficha, id_, 0, utilidad="mucho"),
        _plan(
            navegador,
            ficha,
            id_,
            0,
            ["Dia 1"],
            [{"partida": "AF-LLAVE", "valores": {"Dia 1": "7"}}],
        ),
    ]
    assert [r.status_code for r in malos] == [409, 409, 409]


def test_un_borrador_ya_guardado_no_se_edita_en_ninguna_de_las_cuatro() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    hoja_borradores.obtener(_huella(ficha), id_).guardado_como = "002"
    esperado = {
        "detalle": "Este borrador ya se guardó como la versión 002; abra esa versión para seguir."
    }
    for ruta, cuerpo, metodo in PEDIDOS:
        respuesta = _enviar(navegador, ficha, id_, ruta, metodo, cuerpo(0))
        assert respuesta.status_code == 409 and respuesta.json() == esperado, ruta


# --- 3c-B19: acceso, CSRF, Origin, ficha ajena y caso en E2 a E5 ---


@pytest.mark.parametrize(("ruta", "cuerpo", "metodo"), PEDIDOS, ids=IDS)
def test_sin_sesion_ni_clave_es_401(ruta, cuerpo, metodo) -> None:
    respuesta = getattr(cliente(app), metodo)(
        f"/v1/hoja/borradores/{ID_AJENO}/{ruta}", json=cuerpo(0), headers={"Origin": ORIGEN}
    )
    assert respuesta.status_code == 401 and "detalle" in respuesta.json()
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("ruta", "cuerpo", "metodo"), PEDIDOS, ids=IDS)
def test_rita_que_revisa_y_tomas_con_clave_temporal_no_pueden(ruta, cuerpo, metodo) -> None:
    rita, ficha = con_cuenta(app, "rita")
    respuesta = _enviar(rita, ficha, ID_AJENO, ruta, metodo, cuerpo(0))
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert respuesta.headers["cache-control"] == "no-store"
    tomas, ficha_tomas = con_cuenta(app, "tomas")
    assert _enviar(tomas, ficha_tomas, ID_AJENO, ruta, metodo, cuerpo(0)).status_code == 403


@pytest.mark.parametrize(("ruta", "cuerpo", "metodo"), PEDIDOS, ids=IDS)
def test_la_clave_de_api_no_edita_la_hoja(ruta, cuerpo, metodo) -> None:
    respuesta = getattr(cliente(app), metodo)(
        f"/v1/hoja/borradores/{ID_AJENO}/{ruta}",
        json=cuerpo(0),
        headers={CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN},
    )
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": SOLO_CUENTA}
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("ruta", "cuerpo", "metodo"), PEDIDOS, ids=IDS)
def test_exige_csrf_y_origen_propio(ruta, cuerpo, metodo) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    url = f"/v1/hoja/borradores/{id_}/{ruta}"
    llamar = getattr(navegador, metodo)
    assert llamar(url, json=cuerpo(0), headers={"Origin": ORIGEN}).status_code == 403  # sin CSRF
    ajeno = protegida(ficha, origen="http://evil.example")
    assert llamar(url, json=cuerpo(0), headers=ajeno).status_code == 403
    sin_origen = protegida(ficha, origen=None)
    assert llamar(url, json=cuerpo(0), headers=sin_origen).status_code == 403
    assert _resumen(navegador, id_)["rev"] == 0  # ninguno edito


@pytest.mark.parametrize(("ruta", "cuerpo", "metodo"), PEDIDOS, ids=IDS)
def test_el_borrador_de_otra_ficha_no_existe_y_no_se_edita(ruta, cuerpo, metodo) -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()  # otra ficha de la misma cuenta: otra huella
    id_ = _abrir(uno, ficha_uno)
    ajeno = _enviar(otro, ficha_otro, id_, ruta, metodo, cuerpo(0))
    inventado = _enviar(otro, ficha_otro, ID_AJENO, ruta, metodo, cuerpo(0))
    assert ajeno.status_code == inventado.status_code == 404
    assert ajeno.json() == inventado.json() == {"detalle": FALTA}
    assert id_ not in ajeno.text
    assert _resumen(uno, id_)["rev"] == 0  # el dueño no se enteró


@pytest.mark.parametrize(("ruta", "cuerpo", "metodo"), PEDIDOS, ids=IDS)
def test_tras_un_cambio_de_caso_forzado_es_409_fijo_y_ninguna_base_cambia(
    ruta, cuerpo, metodo, _casos, _entorno
) -> None:
    navegador, ficha = _ana()
    otro = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(_casos["ti001"], otro)
    preparar_base(_entorno)
    preparar_base(otro)
    id_ = _abrir(navegador, ficha)
    antes_a, antes_b = _volcado(_entorno), _volcado(otro)
    caso_web._elegidos[_huella(ficha)] = otro.resolve()  # el cambio sin pasar por `fijar`
    respuesta = _enviar(navegador, ficha, id_, ruta, metodo, cuerpo(0))
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": OTRO_CASO}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes_a and _volcado(otro) == antes_b
    assert hoja_borradores.obtener(_huella(ficha), id_).rev == 0


@pytest.mark.parametrize(("ruta", "cuerpo", "metodo"), PEDIDOS, ids=IDS)
def test_cambiar_de_caso_olvida_el_borrador_y_editarlo_da_404(
    ruta, cuerpo, metodo, _casos, _entorno
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
    respuesta = _enviar(navegador, ficha, id_, ruta, metodo, cuerpo(0))
    assert respuesta.status_code == 404 and respuesta.json() == {"detalle": FALTA}


# --- nada a la base, ningun float, no-store ---


def test_ninguna_de_las_cuatro_escribe_en_la_base_ni_con_exito_ni_con_error(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    antes = _volcado(_entorno)
    assert (
        _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "5"}]).status_code
        == 200
    )
    assert _parametros(navegador, ficha, id_, 1, administracion="0.20").status_code == 200
    etiquetas, filas = _matriz(navegador, id_, **{"AF-LLAVE": {"Dia 3": "0.5", "Dia 4": "0.5"}})
    assert _plan(navegador, ficha, id_, 2, etiquetas, filas).status_code == 200
    assert (
        _cantidades(navegador, ficha, id_, 3, [{"clave": LLAVE, "cantidad": "-1"}]).status_code
        == 422
    )
    assert _parametros(navegador, ficha, id_, 0).status_code == 409
    assert _secuencial(navegador, ficha, id_, 3).status_code == 409  # ya tiene plan
    _sin_plan(ficha, id_)
    assert _secuencial(navegador, ficha, id_, 3).status_code == 200
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


def test_ningun_numero_del_json_es_float_y_todo_monto_es_texto() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    etiquetas, filas = _matriz(navegador, id_, **{"AF-LLAVE": {"Dia 3": "0.5", "Dia 4": "0.5"}})
    respuestas = [
        _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "5"}]),
        _parametros(navegador, ficha, id_, 1, administracion="0.20"),
        _plan(navegador, ficha, id_, 2, etiquetas, filas),
    ]
    _sin_plan(ficha, id_)
    respuestas.append(_secuencial(navegador, ficha, id_, 3))
    for respuesta in respuestas:
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = json.loads(respuesta.text, parse_float=lambda t: float("nan"))
        _sin_float(cuerpo)
        assert isinstance(cuerpo["rev"], int) and isinstance(cuerpo["resumen"]["cambios"], int)
        assert isinstance(cuerpo["resumen"]["total"]["exacto"], str)


def test_no_store_en_exito_404_409_y_422_de_las_cuatro() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    respuestas = [
        _cantidades(navegador, ficha, id_, 0, [{"clave": LLAVE, "cantidad": "5"}]),  # 200
        _parametros(navegador, ficha, ID_AJENO, 0),  # 404
        _plan(navegador, ficha, id_, 0, ["Dia 1"], []),  # 409 de rev
        _secuencial(navegador, ficha, id_, 1),  # 409 ya tiene plan
        _parametros(navegador, ficha, id_, 1, utilidad="mucho"),  # 422 de dominio
        _cantidades(navegador, ficha, id_, "x", []),  # 422 de forma
    ]
    assert [r.status_code for r in respuestas] == [200, 404, 409, 409, 422, 422]
    assert all(r.headers["cache-control"] == "no-store" for r in respuestas)


# --- concurrencia y orden de bloqueos (borrador -> registro, nunca al reves) ---


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

    def acquire(self, *a, **k):  # por si algo lo llama sin `with`
        return self.real.acquire(*a, **k)

    def release(self):
        self.real.release()


@pytest.mark.parametrize(("ruta", "cuerpo", "metodo"), PEDIDOS, ids=IDS)
def test_el_registro_nunca_se_toma_antes_que_el_borrador(
    ruta, cuerpo, metodo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Orden de bloqueos como E1: borrador -> registro. Ningun cerrojo de borrador se adquiere
    teniendo ya el del registro (una inversion permitiria un abrazo mortal entre dos peticiones)."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    if ruta == "plan/secuencial":
        _sin_plan(ficha, id_)
    _Espia.historia = []
    registro = hoja_borradores.REGISTRO
    monkeypatch.setattr(registro, "_cerrojo", _Espia("registro", registro._cerrojo))
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    monkeypatch.setattr(vivo, "cerrojo", _Espia("borrador", vivo.cerrojo))
    respuesta = _enviar(navegador, ficha, id_, ruta, metodo, cuerpo(0))
    assert respuesta.status_code in (200, 409, 422), respuesta.text
    nombres = {nombre for nombre, _ in _Espia.historia}
    assert nombres == {"registro", "borrador"}  # los dos se usaron
    inversiones = [(n, p) for n, p in _Espia.historia if n == "borrador" and "registro" in p]
    assert inversiones == []


def test_una_edicion_espera_al_cerrojo_del_borrador() -> None:
    """Una peticion a la vez por borrador: mientras alguien lo tiene tomado, la edicion espera."""
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha)
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    resultado: list = []

    def editar() -> None:
        resultado.append(_parametros(navegador, ficha, id_, 0, utilidad="0.12"))

    with vivo.cerrojo:
        hilo = threading.Thread(target=editar)
        hilo.start()
        hilo.join(timeout=1.0)
        assert hilo.is_alive() and resultado == []  # espera: no se colo
        assert vivo.rev == 0
    hilo.join(timeout=30)
    assert not hilo.is_alive() and resultado[0].status_code == 200
    assert vivo.rev == 1
