"""Rutas de las líneas del APU de la versión y del antes y después (MP-7, Tarea 26).

- `POST /v1/hoja/borradores/{id}/apu/{partida}/lineas` `{rev, tipo, insumo, descripcion, unidad,
  cantidad, precio, depreciacion, modalidad}` y `POST …/lineas/quitar` `{rev, tipo, indice}` →
  `{rev, resumen, apu}` (como E6 y E7). Lo tecleado llega como texto y lo lee la regla de las
  cifras; 422 sin eco con el texto de la hoja; 409 por `rev` viejo o sin versión guardada; solo
  una cuenta con `editar_hoja`, con CSRF y `Origin` propio.
- `GET /v1/hoja/antes-y-despues?proyecto=&version=` → por partida cuyo APU cambió respecto de la
  línea base: costo directo unitario, duración, término y punto de equilibrio.

Datos FICTICIOS: la vivienda de `tests/fixtures/obra_vivienda.py`. Oráculos a mano: OBRA-02 tiene
costo directo 95 + 60 ÷ 6 + (2 × 45 × 7 + 2) ÷ 6 = 210,33; con «Concreto premezclado» (1,05 m³ a
95,00) los materiales pasan a 95 + 99,75 = 194,75 y el costo directo a 310,08; con rendimiento 4,
194,75 + (60 + 632) ÷ 4 = 367,75.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.rutas import hoja as rutas_hoja
from aplicacion import hoja, hoja_borradores
from aplicacion.control import declarar_linea_base
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from core.budget import crear_proyecto
from core.budget.moneda import declarar_moneda
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts.dominio import Dominio
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.obra_vivienda import FECHA, ITEMS, sembrar_catalogo
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    ORIGEN,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

OBRA = "Vivienda Demo 80 m2"
SIN_VERSIONES = "Obra sin versiones"
ANA = "Ana <ana>"
HOY = date(2026, 11, 2)
CENTINELA = "VALOR-CENTINELA"
ID_AJENO = "a" * 22
REGLA = "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56."
UNA_LINEA = "Un APU necesita al menos una línea."
REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo."
SOLO_CUENTA = "La hoja de la obra se edita y se guarda con una cuenta; la clave de API no sirve."
PARTIDA_FALTA = "Esa partida no tiene APU en este borrador: vuelva a cargar la lista de partidas."
SIN_VERSION = (
    "Las líneas del APU se agregan y se quitan en una versión guardada: guarde primero la versión."
)
FORMA_LINEA = (
    "La línea no tiene la forma esperada: envíe rev (entero), tipo (material, equipo o "
    "mano_obra), el código del insumo o la descripción, la unidad y el precio de uno nuevo, la "
    "cantidad, la depreciación de un equipo y la modalidad (jornal o destajo); cada texto de "
    "hasta 500 caracteres."
)
FORMA_QUITAR_LINEA = (
    "La petición no tiene la forma esperada: envíe rev (entero), tipo (material, equipo o "
    "mano_obra) e indice (entero)."
)
FORMA_ANTES = (
    "Indique la obra (código o nombre) y, si quiere, la versión; cada uno de hasta 500 caracteres."
)
SIN_LINEA_BASE = (
    "Esta obra no tiene línea base: declárela en Control de obra para comparar el antes y el "
    "después."
)
NUEVO = {
    "tipo": "material",
    "insumo": "",
    "descripcion": "Concreto premezclado",
    "unidad": "m3",
    "cantidad": "1,05",
    "precio": "95,00",
    "depreciacion": "",
    "modalidad": "jornal",
}


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    """La instalación con cuentas y la carpeta de la vivienda con «001» guardada (y una obra sin
    versiones); `con_linea_base`, además, con la línea base declarada sobre «001»."""
    carpeta = tmp_path_factory.mktemp("api_hoja_lineas_apu")
    caso = carpeta / "caso.db"
    preparar_base(caso)
    motor = crear_motor(f"sqlite:///{caso.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_catalogo(sesion)
            declarar_moneda_de_la_carpeta(
                sesion, "Bs", responsable=ANA, ahora=datetime(2026, 11, 2, 8, 0)
            )
            for nombre in (OBRA, SIN_VERSIONES):
                proyecto = crear_proyecto(sesion, nombre, dominio=Dominio.CIVIL)
                declarar_moneda(sesion, proyecto, "Bs", responsable=ANA)
            sesion.commit()
            hoja.crear_primera_version(
                sesion,
                Catalogo(sesion),
                OBRA,
                hoja.Borrador(fecha=FECHA, moneda="Bs", items_base=ITEMS),
                fuente="Medición en sitio",
                responsable=ANA,
            )
        con_linea_base = carpeta / "con_linea_base.db"
        motor.dispose()
        shutil.copyfile(caso, con_linea_base)
        motor = crear_motor(f"sqlite:///{con_linea_base.as_posix()}")
        with abrir_sesion(motor) as sesion:
            declarar_linea_base(
                sesion,
                OBRA,
                "001",
                desde="2026-11-02",
                perspectiva="costo",
                inicio="2026-11-02",
                dias_por_periodo="1",
                feriados="",
                fuente="Contrato firmado",
                responsable=ANA,
            )
    finally:
        motor.dispose()
    return {
        "instalacion": plantilla_con_cuentas(carpeta / "instalacion"),
        "caso": caso,
        "con_linea_base": con_linea_base,
    }


def _poner(origen: Path) -> Path:
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origen, ruta)
    return ruta


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: HOY)
    copiar_instalacion(_plantillas["instalacion"])
    ruta = _poner(_plantillas["caso"])
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    dependencias.cerrar_motores()


def _ana() -> tuple[TestClient, str]:
    return con_cuenta(app, "ana")


def _abierto(navegador: TestClient, ficha: str, proyecto: str = OBRA, version="001") -> str:
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": proyecto, "version": version},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _ruta(id_: str, partida: str = "OBRA-02") -> str:
    return f"/v1/hoja/borradores/{id_}/apu/{quote(partida, safe='')}/lineas"


def _agregar(navegador, ficha, id_, rev=0, partida="OBRA-02", **campos):
    return navegador.post(
        _ruta(id_, partida), json={"rev": rev, **NUEVO, **campos}, headers=protegida(ficha)
    )


def _quitar(navegador, ficha, id_, rev, tipo, indice, partida="OBRA-02"):
    return navegador.post(
        f"{_ruta(id_, partida)}/quitar",
        json={"rev": rev, "tipo": tipo, "indice": indice},
        headers=protegida(ficha),
    )


def _resumen(navegador: TestClient, id_: str) -> dict:
    respuesta = navegador.get(f"/v1/hoja/borradores/{id_}")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["resumen"]


def _consulta(ruta: Path, sql: str, *parametros) -> list[tuple]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        return bd.execute(sql, parametros).fetchall()


def _monto(detalle: dict, concepto: str) -> str:
    return next(c["monto"]["texto"] for c in detalle["cierre"] if c["concepto"] == concepto)


# --- agregar una línea ---------------------------------------------------------------------------


def test_agregar_concreto_premezclado_a_obra_02_sube_el_costo_directo_en_99_75() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    respuesta = _agregar(navegador, ficha, id_)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == 1 and cuerpo["resumen"]["cambios"] == 1
    detalle = cuerpo["apu"]["detalle"]
    assert detalle["codigo"] == "OBRA-02"
    materiales = next(g for g in detalle["grupos"] if g["clave"] == "materiales")
    assert materiales["filas"] == [
        {"descripcion": "Cemento gris", "unidad": "m3", "cantidad": "1", "precio": "95,00"},
        {
            "descripcion": "Concreto premezclado",
            "unidad": "m3",
            "cantidad": "1,05",
            "precio": "95,00",
        },
    ]
    assert detalle["metricas"]["materiales"]["texto"] == "194.75"  # 95 + 1,05 × 95
    assert _monto(detalle, "= Costo directo") == "310.08"  # 210,33 + 99,75
    cambios = navegador.get(f"/v1/hoja/borradores/{id_}/cambios").json()
    assert cambios == {
        "rev": 1,
        "cambios": [
            {
                "objeto": "apu",
                "clave": "OBRA-02|material|2",
                "campo": "alta",
                "antes": "",
                "despues": "Concreto premezclado",
            }
        ],
    }


def test_guardar_crea_la_version_nueva_con_la_linea_sin_insumo_del_catalogo(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_).status_code == 200
    guardado = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": 1, "fuente": "Crisis del cemento"},
        headers=protegida(ficha),
    )
    assert guardado.status_code == 200, guardado.text
    filas = _consulta(
        _entorno,
        "SELECT l.descripcion, l.insumo_id, l.cantidad, l.precio "
        "FROM linea_composicion_version l "
        "JOIN composicion_version c ON c.id = l.composicion_id "
        "JOIN presupuesto p ON p.id = c.presupuesto_id "
        "WHERE p.codigo = '002' AND c.codigo_partida = 'OBRA-02' AND l.tipo = 'material' "
        "ORDER BY l.orden",
    )
    assert [(d, i is None) for d, i, _, _ in filas] == [
        ("Cemento gris", False),
        ("Concreto premezclado", True),
    ]
    assert Decimal(str(filas[1][2])) == Decimal("1.05")


def test_un_insumo_del_catalogo_se_busca_y_se_agrega_con_el_precio_de_la_lista() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    hallados = navegador.get(
        f"/v1/hoja/borradores/{id_}/insumos", params={"tipo": "material", "texto": "mortero"}
    ).json()["insumos"]
    assert [(i["descripcion"], i["precio"]["texto"]) for i in hallados] == [
        ("Mortero premezclado", "4.00")
    ]
    respuesta = _agregar(
        navegador, ficha, id_, insumo=hallados[0]["codigo"], descripcion="", precio="", cantidad="2"
    )
    assert respuesta.status_code == 200, respuesta.text
    materiales = respuesta.json()["apu"]["detalle"]["grupos"][0]["filas"]
    assert materiales[-1] == {
        "descripcion": "Mortero premezclado",
        "unidad": "m2",
        "cantidad": "2",
        "precio": "4,00",
    }


def test_una_cifra_mal_escrita_es_422_con_la_regla_y_no_cambia_nada() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    respuesta = _agregar(navegador, ficha, id_, cantidad="1.05")
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": f"La cantidad no se entiende como número. {REGLA}"}
    assert _resumen(navegador, id_)["rev"] == 0


def test_con_un_rev_viejo_es_409_y_no_cambia_nada() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_).status_code == 200
    respuesta = _agregar(navegador, ficha, id_, rev=0, descripcion="Arena lavada")
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": REV_VIEJO}
    assert _quitar(navegador, ficha, id_, 0, "material", 0).status_code == 409
    assert _resumen(navegador, id_)["rev"] == 1


def test_una_partida_sin_apu_es_404() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    respuesta = _agregar(navegador, ficha, id_, partida="OBRA-99")
    assert respuesta.status_code == 404 and respuesta.json() == {"detalle": PARTIDA_FALTA}


def test_en_un_borrador_en_blanco_es_409_sin_version_guardada() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha, proyecto=SIN_VERSIONES, version=None)
    agregada = navegador.post(
        f"/v1/hoja/borradores/{id_}/partidas",
        json={"rev": 0, "codigo": "OBRA-02", "cantidad": "12", "calculo": "", "nota": ""},
        headers=protegida(ficha),
    )
    assert agregada.status_code == 200, agregada.text
    respuesta = _agregar(navegador, ficha, id_, rev=1)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": SIN_VERSION}
    quitar = _quitar(navegador, ficha, id_, 1, "material", 0)
    assert quitar.status_code == 409 and quitar.json() == {"detalle": SIN_VERSION}


@pytest.mark.parametrize(
    "cuerpo",
    [
        {**NUEVO, "rev": CENTINELA},
        {**NUEVO, "rev": 0, "tipo": CENTINELA},
        {**NUEVO, "rev": 0, "cantidad": 1.05, "descripcion": CENTINELA},
        {**NUEVO, "rev": 0, "modalidad": CENTINELA},
        {**NUEVO, "rev": 0, "otro": CENTINELA},
        {**NUEVO, "rev": 0, "descripcion": CENTINELA * 50},
    ],
)
def test_la_forma_mala_de_agregar_es_422_sin_eco(cuerpo: dict) -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    respuesta = navegador.post(_ruta(id_), json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA_LINEA}
    assert CENTINELA not in respuesta.text


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"rev": 0, "tipo": "material", "indice": CENTINELA},
        {"rev": 0, "tipo": CENTINELA, "indice": 0},
        {"rev": 0, "tipo": "material", "indice": -1},
        {"rev": 0, "tipo": "material", "indice": 0, "otro": CENTINELA},
    ],
)
def test_la_forma_mala_de_quitar_es_422_sin_eco(cuerpo: dict) -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    respuesta = navegador.post(f"{_ruta(id_)}/quitar", json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA_QUITAR_LINEA}
    assert CENTINELA not in respuesta.text


# --- quitar una línea -----------------------------------------------------------------------------


def test_quitar_la_ultima_linea_de_un_apu_es_422_con_el_texto() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    material = _quitar(navegador, ficha, id_, 0, "material", 0)
    assert material.status_code == 200, material.text
    detalle = material.json()["apu"]["detalle"]
    assert detalle["grupos"][0]["filas"] == []
    # sin el material: 210,33 − 95 = 115,33
    assert _monto(detalle, "= Costo directo") == "115.33"
    assert _quitar(navegador, ficha, id_, 1, "equipo", 0).status_code == 200
    ultima = _quitar(navegador, ficha, id_, 2, "mano_obra", 0)
    assert ultima.status_code == 422 and ultima.json() == {"detalle": UNA_LINEA}
    assert _resumen(navegador, id_)["rev"] == 2
    assert _resumen(navegador, id_)["cambios"] == 2


def test_quitar_una_linea_que_ya_no_esta_es_422() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    respuesta = _quitar(navegador, ficha, id_, 0, "material", 3)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "Esa línea ya no está en el APU: vuelva a cargarlo."}


# --- acceso: solo una cuenta con editar_hoja, CSRF y Origin ---------------------------------------

RUTAS = (
    (_ruta(ID_AJENO), {"rev": 0, **NUEVO}),
    (f"{_ruta(ID_AJENO)}/quitar", {"rev": 0, "tipo": "material", "indice": 0}),
)


@pytest.mark.parametrize(("ruta", "cuerpo"), RUTAS)
def test_sin_sesion_es_401_y_quien_revisa_no_puede(ruta: str, cuerpo: dict) -> None:
    anonimo = cliente(app).post(ruta, json=cuerpo, headers={"Origin": ORIGEN})
    assert anonimo.status_code == 401
    rita, ficha = con_cuenta(app, "rita")
    revisa = rita.post(ruta, json=cuerpo, headers=protegida(ficha))
    assert revisa.status_code == 403 and revisa.json() == {"detalle": MENSAJE_PERMISO}


@pytest.mark.parametrize(("ruta", "cuerpo"), RUTAS)
def test_la_clave_de_api_no_agrega_ni_quita_lineas(ruta: str, cuerpo: dict) -> None:
    respuesta = cliente(app).post(
        ruta, json=cuerpo, headers={CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN}
    )
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": SOLO_CUENTA}


def test_agregar_y_quitar_exigen_csrf_y_origen_propio() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    for ruta, cuerpo in (
        (_ruta(id_), {"rev": 0, **NUEVO}),
        (f"{_ruta(id_)}/quitar", {"rev": 0, "tipo": "material", "indice": 0}),
    ):
        assert navegador.post(ruta, json=cuerpo, headers={"Origin": ORIGEN}).status_code == 403
        ajeno = protegida(ficha, origen="http://evil.example")
        assert navegador.post(ruta, json=cuerpo, headers=ajeno).status_code == 403
        assert navegador.post(ruta, json=cuerpo, headers=protegida(ficha, None)).status_code == 403
    assert _resumen(navegador, id_)["rev"] == 0


# --- antes y después respecto de la línea base ----------------------------------------------------


def _version_con_la_crisis(navegador: TestClient, ficha: str) -> None:
    """«002»: OBRA-02 con el concreto premezclado y rendimiento 4."""
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_).status_code == 200
    apu = navegador.put(
        f"/v1/hoja/borradores/{id_}/apu/OBRA-02",
        json={
            "rev": 1,
            "rendimiento": "4",
            "materiales": ["1", "1,05"],
            "equipos": ["1"],
            "mano_obra": ["2"],
        },
        headers=protegida(ficha),
    )
    assert apu.status_code == 200, apu.text
    guardado = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": 2, "fuente": "Crisis del cemento"},
        headers=protegida(ficha),
    )
    assert guardado.status_code == 200, guardado.text


def test_antes_y_despues_de_obra_02_con_costo_duracion_y_termino(
    _plantillas: dict[str, Path],
) -> None:
    _poner(_plantillas["con_linea_base"])
    navegador, ficha = _ana()
    _version_con_la_crisis(navegador, ficha)
    respuesta = navegador.get("/v1/hoja/antes-y-despues", params={"proyecto": OBRA})
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["linea_base"], cuerpo["version"], cuerpo["moneda"], cuerpo["aviso"]) == (
        "001",
        "002",
        "Bs",
        None,
    )
    [fila] = cuerpo["filas"]
    assert (fila["partida"], fila["descripcion"], fila["unidad"], fila["cantidad"]) == (
        "OBRA-02",
        "Concreto para fundaciones",
        "m3",
        "12",
    )
    assert (fila["costo_antes"]["texto"], fila["costo_despues"]["texto"]) == ("210.33", "367.75")
    assert (fila["duracion_antes"], fila["duracion_despues"]) == ("2", "3")
    assert (fila["termino_antes"], fila["termino_despues"]) == (58, 59)
    antes, despues = fila["equilibrio_antes"], fila["equilibrio_despues"]
    assert antes is not None and despues is not None
    assert Decimal(despues["exacto"]) > Decimal(antes["exacto"])
    con_version = navegador.get(
        "/v1/hoja/antes-y-despues", params={"proyecto": OBRA, "version": "001"}
    ).json()
    assert con_version["filas"] == [] and con_version["aviso"] == (
        "Ninguna partida de la versión 001 cambió su APU respecto de la línea base 001."
    )


def test_una_version_en_otra_moneda_lo_dice_y_no_mezcla_filas(
    _plantillas: dict[str, Path],
) -> None:
    ruta = _poner(_plantillas["con_linea_base"])
    navegador, ficha = _ana()
    _version_con_la_crisis(navegador, ficha)
    dependencias.cerrar_motores()
    with closing(sqlite3.connect(ruta.as_posix())) as bd:
        bd.execute("UPDATE presupuesto SET moneda = 'USD' WHERE codigo = '002'")
        bd.commit()
    respuesta = navegador.get("/v1/hoja/antes-y-despues", params={"proyecto": OBRA})
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["linea_base"], cuerpo["version"], cuerpo["filas"]) == ("001", "002", [])
    assert cuerpo["aviso"] == (
        "La versión 002 está en USD y la línea base 001 en Bs: no se comparan montos en monedas "
        "distintas."
    )


def test_sin_linea_base_lo_dice_y_no_compara() -> None:
    navegador, _ = _ana()
    respuesta = navegador.get("/v1/hoja/antes-y-despues", params={"proyecto": OBRA})
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "linea_base": None,
        "version": "001",
        "moneda": "Bs",
        "filas": [],
        "aviso": SIN_LINEA_BASE,
    }


def test_antes_y_despues_lee_con_clave_y_con_quien_revisa() -> None:
    con_clave = cliente(app).get(
        "/v1/hoja/antes-y-despues",
        params={"proyecto": OBRA},
        headers={CABECERA: crear_clave_de_prueba()},
    )
    assert con_clave.status_code == 200
    rita, _ = con_cuenta(app, "rita")  # F4 2b: quien revisa lee (Eugenio, 2026-10-31)
    assert rita.get("/v1/hoja/antes-y-despues", params={"proyecto": OBRA}).status_code == 200
    admin, _ = con_cuenta(app, "admin")
    negada = admin.get("/v1/hoja/antes-y-despues", params={"proyecto": OBRA})
    assert negada.status_code == 403 and negada.json() == {"detalle": MENSAJE_PERMISO}


def test_antes_y_despues_de_una_obra_o_version_que_no_existe_es_404_y_la_forma_mala_422() -> None:
    navegador, _ = _ana()
    assert (
        navegador.get("/v1/hoja/antes-y-despues", params={"proyecto": "No existe"}).status_code
        == 404
    )
    assert (
        navegador.get(
            "/v1/hoja/antes-y-despues", params={"proyecto": OBRA, "version": "009"}
        ).status_code
        == 404
    )
    mala = navegador.get("/v1/hoja/antes-y-despues", params={"proyecto": CENTINELA * 50})
    assert mala.status_code == 422 and mala.json() == {"detalle": FORMA_ANTES}
    assert CENTINELA not in mala.text
