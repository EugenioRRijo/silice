"""La pestaña APU de la Hoja muestra el desperdicio de cada material (F5 vial, punto 1).

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §4 (opción B) y §13,
«Lo que falta»: Componer ya guarda la cantidad con desperdicio y su traza (la neta y el
porcentaje); la Hoja la mostraba solo como la cantidad. `GET /v1/hoja/borradores/{id}/vistas/apu`
devuelve ahora, en `detalle.desperdicios`, la fila de Materiales y el texto «neta + porcentaje»
de cada línea cuya descripción, unidad y cantidad son las de la traza vigente de la partida.

Solo lectura: quien revisa también lo ve, y leerlo no escribe en la base del caso.

Datos FICTICIOS (la obra OF-001). Oráculo a mano: la llave de AF-LLAVE lleva 1 pieza; una traza
de 0,8 piezas con 25 % de desperdicio da 0,8 × 1,25 = 1, la misma cantidad.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.main import app
from aplicacion.desperdicio import TrazaDesperdicio, guardar_trazas, trazas_vigentes
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
LLAVE = "Llave de paso de bola PVC 1/2 pulg [PLOG26]"
#: Lo que la vista dice de la llave con la traza 0,8 + 25 % (= 1).
LLAVE_0_8 = {"fila": 1, "texto": "0,8 + 25 %", "neta": "0,8", "porcentaje": "25"}


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("hoja_desperdicio")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
    }


@pytest.fixture(autouse=True)
def _caso(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["of001"], ruta)
    preparar_base(ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _con_traza(ruta: Path, traza: TrazaDesperdicio) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            guardar_trazas(sesion, "AF-LLAVE", [traza], ahora=datetime(2026, 11, 13, 9))
            sesion.commit()
    finally:
        motor.dispose()


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def _detalle(login: str) -> dict:
    navegador, ficha = con_cuenta(app, login)
    abierto = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": "001"},
        headers=protegida(ficha),
    )
    assert abierto.status_code == 201, abierto.text
    vista = navegador.get(
        f"/v1/hoja/borradores/{abierto.json()['id']}/vistas/apu", params={"partida": "AF-LLAVE"}
    )
    assert vista.status_code == 200, vista.text
    return vista.json()["detalle"]


def test_sin_traza_no_hay_desperdicios(_caso: Path) -> None:
    assert _detalle("ana")["desperdicios"] == []


def test_la_linea_con_traza_trae_su_neta_y_su_porcentaje(_caso: Path) -> None:
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    detalle = _detalle("ana")
    assert detalle["desperdicios"] == [LLAVE_0_8]
    assert detalle["grupos"][0]["filas"][0]["cantidad"] == "1"


def test_una_traza_de_otra_cantidad_no_se_muestra(_caso: Path) -> None:
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("1"), D("4"), D("1.04")))
    assert _detalle("ana")["desperdicios"] == []


def test_quien_revisa_lo_ve_sin_escribir_en_la_base(_caso: Path) -> None:
    # quien arma abre la versión una vez (la prepara: UC-15e); después revisa solo lee
    _detalle("ana")
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    antes = _volcado(_caso)
    assert _detalle("rita")["desperdicios"] == [LLAVE_0_8]
    assert _volcado(_caso) == antes


def test_tras_editar_el_apu_la_respuesta_conserva_el_desperdicio(_caso: Path) -> None:
    """La respuesta de una edición (E6) trae la vista del APU recalculada: cambiar solo el
    rendimiento no toca la cantidad de la llave, así que su traza sigue valiendo; cambiar la
    cantidad de la llave sí la deja sin traza."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    abierto = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": "001"},
        headers=protegida(ficha),
    )
    assert abierto.status_code == 201, abierto.text
    id_ = abierto.json()["id"]
    detalle = navegador.get(
        f"/v1/hoja/borradores/{id_}/vistas/apu", params={"partida": "AF-LLAVE"}
    ).json()["detalle"]
    cantidades = {g["clave"]: [f["cantidad"] for f in g["filas"]] for g in detalle["grupos"]}

    def editar(rev: int, rendimiento: str, materiales: list[str]):
        return navegador.put(
            f"/v1/hoja/borradores/{id_}/apu/AF-LLAVE",
            json={
                "rev": rev,
                "rendimiento": rendimiento,
                "materiales": materiales,
                "equipos": cantidades["equipos"],
                "mano_obra": cantidades["mano de obra"],
            },
            headers=protegida(ficha),
        )

    primera = editar(0, "25", cantidades["materiales"])
    assert primera.status_code == 200, primera.text
    assert primera.json()["apu"]["detalle"]["desperdicios"] == [LLAVE_0_8]
    segunda = editar(primera.json()["rev"], "25", ["2"])
    assert segunda.status_code == 200, segunda.text
    assert segunda.json()["apu"]["detalle"]["desperdicios"] == []


# --- editar la neta y el porcentaje en la Hoja (2026-11-13, opción a de la bitácora) -------------


def _abrir(navegador, ficha) -> tuple[str, dict[str, list[str]]]:
    abierto = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": "001"},
        headers=protegida(ficha),
    )
    assert abierto.status_code == 201, abierto.text
    id_ = abierto.json()["id"]
    detalle = navegador.get(
        f"/v1/hoja/borradores/{id_}/vistas/apu", params={"partida": "AF-LLAVE"}
    ).json()["detalle"]
    return id_, {g["clave"]: [f["cantidad"] for f in g["filas"]] for g in detalle["grupos"]}


def _editar(navegador, ficha, id_, cantidades, rev, materiales, desperdicios):
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/apu/AF-LLAVE",
        json={
            "rev": rev,
            "rendimiento": "20",
            "materiales": materiales,
            "desperdicios": desperdicios,
            "equipos": cantidades["equipos"],
            "mano_obra": cantidades["mano de obra"],
        },
        headers=protegida(ficha),
    )


def _trazas(ruta: Path) -> list[TrazaDesperdicio]:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return trazas_vigentes(sesion, "AF-LLAVE")
    finally:
        motor.dispose()


LLAVE_2_5 = {"fila": 1, "texto": "2 + 5 %", "neta": "2", "porcentaje": "5"}


def test_la_hoja_edita_la_neta_y_el_porcentaje_y_el_servidor_calcula_la_cantidad(
    _caso: Path,
) -> None:
    """2 piezas netas con 5 % dan 2 × 1,05 = 2,10 (a mano). Editar no escribe en la base: la
    traza viaja en el borrador hasta guardar la versión."""
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    antes = _volcado(_caso)
    respuesta = _editar(navegador, ficha, id_, cantidades, 0, ["2"], ["5"])
    assert respuesta.status_code == 200, respuesta.text
    detalle = respuesta.json()["apu"]["detalle"]
    assert D(detalle["grupos"][0]["filas"][0]["cantidad"].replace(",", ".")) == D("2.10")
    assert detalle["desperdicios"] == [LLAVE_2_5]
    assert _volcado(_caso) == antes
    # la lectura de la vista dice lo mismo que la respuesta
    leida = navegador.get(
        f"/v1/hoja/borradores/{id_}/vistas/apu", params={"partida": "AF-LLAVE"}
    ).json()["detalle"]
    assert leida["desperdicios"] == [LLAVE_2_5]


def test_al_guardar_la_version_se_escribe_la_traza_unida_a_la_vigente(_caso: Path) -> None:
    """La traza de Componer (0,8 + 25 % = 1) sigue valiendo para el catálogo y para la versión
    001; la de la Hoja (2 + 5 % = 2,10) se suma, y la versión 002 la muestra al abrirla."""
    componer = TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000"))
    _con_traza(_caso, componer)
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    editado = _editar(navegador, ficha, id_, cantidades, 0, ["2"], ["5"])
    assert editado.status_code == 200, editado.text
    guardado = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": editado.json()["rev"], "fuente": "Acta ficticia de obra"},
        headers=protegida(ficha),
    )
    assert guardado.status_code == 200, guardado.text
    assert guardado.json()["codigo"] == "002"
    assert _trazas(_caso) == [
        TrazaDesperdicio(LLAVE, "pieza", D("2"), D("5"), D("2.10")),
        componer,
    ]
    for version, esperado in (("002", LLAVE_2_5), ("001", LLAVE_0_8)):
        abierto = navegador.post(
            "/v1/hoja/borradores",
            json={"proyecto": NOMBRE_OF001, "version": version},
            headers=protegida(ficha),
        )
        assert abierto.status_code == 201, abierto.text
        detalle = navegador.get(
            f"/v1/hoja/borradores/{abierto.json()['id']}/vistas/apu",
            params={"partida": "AF-LLAVE"},
        ).json()["detalle"]
        assert detalle["desperdicios"] == [esperado], version


def test_descartar_el_borrador_no_deja_ninguna_traza(_caso: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    antes = _volcado(_caso)
    assert _editar(navegador, ficha, id_, cantidades, 0, ["2"], ["5"]).status_code == 200
    descartado = navegador.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha))
    assert descartado.status_code == 204, descartado.text
    assert _volcado(_caso) == antes


def test_un_porcentaje_mal_escrito_es_422_y_el_borrador_no_cambia(_caso: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    malo = _editar(navegador, ficha, id_, cantidades, 0, ["2"], ["cinco"])
    assert malo.status_code == 422, malo.text
    assert malo.json()["detalle"].startswith(
        "materiales, fila 1: el desperdicio «cinco» no se entiende como número."
    )
    # rev sigue en 0: la misma edición bien escrita se acepta con él
    assert _editar(navegador, ficha, id_, cantidades, 0, ["2"], ["5"]).status_code == 200


def test_un_porcentaje_de_mas_o_de_menos_es_422(_caso: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    for desperdicios in ([], ["5", ""]):
        respuesta = _editar(navegador, ficha, id_, cantidades, 0, ["2"], desperdicios)
        assert respuesta.status_code == 422, respuesta.text
        assert "desperdicio" in respuesta.json()["detalle"]


def test_quien_revisa_no_edita_el_desperdicio(_caso: Path) -> None:
    _detalle("ana")  # la versión ya preparada
    navegador, ficha = con_cuenta(app, "rita")
    id_, cantidades = _abrir(navegador, ficha)
    antes = _volcado(_caso)
    respuesta = _editar(navegador, ficha, id_, cantidades, 0, ["2"], ["5"])
    assert respuesta.status_code == 403, respuesta.text
    assert _volcado(_caso) == antes
