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
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.main import app
from aplicacion import hoja_borradores
from aplicacion.desperdicio import TrazaDesperdicio, guardar_trazas, trazas_vigentes
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import sesiones
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


def _sin_trazas(volcado: dict[str, list[tuple]]) -> dict[str, list[tuple]]:
    """El volcado sin las tablas de las trazas del desperdicio (`apu_desperdicio*`)."""
    return {t: filas for t, filas in volcado.items() if not t.startswith("apu_desperdicio")}


def _detalle(login: str) -> dict:
    navegador, ficha = con_cuenta(app, login)
    abierto = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": "001"},
        headers=protegida(ficha),
    )
    assert abierto.status_code == 201, abierto.text
    return _detalle_de(navegador, abierto.json()["id"])


def _detalle_de(navegador, id_) -> dict:
    vista = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/apu", params={"partida": "AF-LLAVE"})
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


# --- Árbitro xhigh del 2026-11-13, M6: lo que comprobó con guiones, ahora en la suite ---


def test_si_falla_la_version_no_queda_ninguna_traza_y_el_reintento_la_guarda(
    _caso: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La traza va en la misma transacción que la versión: si el núcleo falla después de volcarla,
    la base queda igual byte a byte; con el núcleo sano, el reintento guarda las dos."""
    from aplicacion import hoja

    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    editado = _editar(navegador, ficha, id_, cantidades, 0, ["2"], ["5"])
    assert editado.status_code == 200, editado.text
    antes = _volcado(_caso)
    original = hoja.guardar_version

    def que_falla(sesion, *args, **kwargs):
        assert trazas_vigentes(sesion, "AF-LLAVE"), "la traza debía estar ya en la sesión"
        raise ValueError("fallo simulado del núcleo")

    monkeypatch.setattr(hoja, "guardar_version", que_falla)
    cuerpo = {"rev": editado.json()["rev"], "fuente": "Acta ficticia"}
    fallido = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar", json=cuerpo, headers=protegida(ficha)
    )
    assert fallido.status_code == 409, fallido.text
    assert _volcado(_caso) == antes
    assert _trazas(_caso) == []
    monkeypatch.setattr(hoja, "guardar_version", original)
    guardado = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar", json=cuerpo, headers=protegida(ficha)
    )
    assert guardado.status_code == 200, guardado.text
    assert _trazas(_caso) == [TrazaDesperdicio(LLAVE, "pieza", D("2"), D("5"), D("2.10"))]


@pytest.mark.parametrize(
    ("texto", "error"),
    [
        ("1.000", "debe ser de 0 a menos de 100"),  # mil por ciento, con punto de miles
        ("100", "debe ser de 0 a menos de 100"),
        ("4.5", "no se entiende como número"),  # el punto no es decimal
    ],
)
def test_un_porcentaje_fuera_de_rango_o_mal_escrito_es_422(
    _caso: Path, texto: str, error: str
) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    respuesta = _editar(navegador, ficha, id_, cantidades, 0, ["2"], [texto])
    assert respuesta.status_code == 422, respuesta.text
    assert error in respuesta.json()["detalle"]
    assert "materiales, fila 1" in respuesta.json()["detalle"]


@pytest.mark.parametrize(
    ("texto", "porcentaje"),
    [("99,99", "99,99"), (" 4 ", "4"), ("-0", None), ("0,0", None), ("\ufeff", None)],
)
def test_porcentajes_de_frontera_que_se_aceptan(
    _caso: Path, texto: str, porcentaje: str | None
) -> None:
    """«99,99» y « 4 » son desperdicio; «-0», «0,0» y un BOM solo, ninguno."""
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    respuesta = _editar(navegador, ficha, id_, cantidades, 0, ["2"], [texto])
    assert respuesta.status_code == 200, respuesta.text
    desperdicios = respuesta.json()["apu"]["detalle"]["desperdicios"]
    assert [d["porcentaje"] for d in desperdicios] == ([] if porcentaje is None else [porcentaje])


# --- Depuración del 2026-11-15, L2: borrar el porcentaje quita el desglose ----------------------


def test_al_guardar_sin_porcentaje_la_traza_vigente_de_esa_linea_deja_de_valer(
    _caso: Path,
) -> None:
    """Con otro cambio que guardar (el rendimiento), la línea que la Hoja dejó sin porcentaje no
    vuelve a mostrar «0,8 + 25 %» en la versión nueva: manda lo más nuevo (bitácora del
    2026-11-13, §3, riesgo 1), y la base registra un guardado sin trazas."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    editado = navegador.put(
        f"/v1/hoja/borradores/{id_}/apu/AF-LLAVE",
        json={
            "rev": 0,
            "rendimiento": "25",
            "materiales": ["1"],
            "desperdicios": [""],
            "equipos": cantidades["equipos"],
            "mano_obra": cantidades["mano de obra"],
        },
        headers=protegida(ficha),
    )
    assert editado.status_code == 200, editado.text
    guardado = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": editado.json()["rev"], "fuente": "Acta ficticia de obra"},
        headers=protegida(ficha),
    )
    assert guardado.status_code == 200, guardado.text
    assert _trazas(_caso) == []
    abierto = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": guardado.json()["codigo"]},
        headers=protegida(ficha),
    )
    assert abierto.status_code == 201, abierto.text
    detalle = navegador.get(
        f"/v1/hoja/borradores/{abierto.json()['id']}/vistas/apu", params={"partida": "AF-LLAVE"}
    ).json()["detalle"]
    assert detalle["desperdicios"] == []


# --- Anexo A.6 del desenredo (acta DS-3, opción B): solo el desglose es un cambio ---------------


@pytest.mark.parametrize(
    ("materiales", "desperdicios", "mostrado"),
    [  # 0,625 × 1,60 = 1 y 1 sin desperdicio (a mano): la misma cantidad que 0,8 + 25 %
        (
            ["0,625"],
            ["60"],
            [{"fila": 1, "texto": "0,625 + 60 %", "neta": "0,625", "porcentaje": "60"}],
        ),
        (["1"], [""], []),
    ],
)
def test_cambiar_solo_el_desglose_sube_el_rev_y_cuenta_un_cambio(
    _caso: Path, materiales: list[str], desperdicios: list[str], mostrado: list[dict]
) -> None:
    """Con 0,8 + 25 % (= 1) vigente, otro reparto de la misma cantidad o quitarle el porcentaje
    deja la composición igual pero cambia lo que la Hoja muestra: 200, el rev sube a 1 y el resumen
    cuenta un cambio (antes, acta DS-3 opción A, era 422). Editar no escribe en la base. Mandar lo
    mismo otra vez no sube el rev."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    antes = _volcado(_caso)
    editado = _editar(navegador, ficha, id_, cantidades, 0, materiales, desperdicios)
    assert editado.status_code == 200, editado.text
    assert editado.json()["rev"] == 1
    assert editado.json()["resumen"]["cambios"] == 1
    assert editado.json()["apu"]["detalle"]["desperdicios"] == mostrado
    assert _volcado(_caso) == antes
    igual = _editar(navegador, ficha, id_, cantidades, 1, materiales, desperdicios)
    assert igual.status_code == 200, igual.text
    assert igual.json()["rev"] == 1


LLAVE_0_625 = {"fila": 1, "texto": "0,625 + 60 %", "neta": "0,625", "porcentaje": "60"}
#: 0,625 × 1,60 = 1 (a mano): la misma cantidad que 0,8 + 25 %.
TRAZA_0_625 = TrazaDesperdicio(LLAVE, "pieza", D("0.625"), D("60"), D("1.000"))
SOLO_DESGLOSE_GUARDADO = (
    "Se guardó el desglose del desperdicio de 1 línea. La cantidad no cambió, así que la versión "
    "001 sigue siendo la misma."
)


def _codigos(navegador) -> list[str]:
    versiones = navegador.get("/v1/hoja/versiones", params={"proyecto": NOMBRE_OF001})
    assert versiones.status_code == 200, versiones.text
    return sorted(v["codigo"] for v in versiones.json()["versiones"])


def test_guardar_solo_el_desglose_escribe_las_trazas_sin_version_nueva(_caso: Path) -> None:
    """Con 0,8 + 25 % vigente, la Hoja deja 0,625 + 60 % (misma cantidad, rev 1, un cambio que es
    de desglose). Guardar responde 200 sin pedir fuente (no hay dónde guardarla): la traza nueva
    queda vigente en la base, no hay versión 002 y el borrador sigue abierto en el mismo rev, ya
    sin cambios. Otro borrador de la 001 muestra el desglose nuevo."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    editado = _editar(navegador, ficha, id_, cantidades, 0, ["0,625"], ["60"])
    assert editado.status_code == 200, editado.text
    resumen = editado.json()["resumen"]
    assert (resumen["rev"], resumen["cambios"]) == (1, 1)
    antes = _volcado(_caso)
    guardado = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": 1, "fuente": ""},
        headers=protegida(ficha),
    )
    assert guardado.status_code == 200, guardado.text
    # solo cambian las tablas de las trazas: ninguna versión, registro, sello ni fila esp_*
    despues = _volcado(_caso)
    assert _sin_trazas(despues) == _sin_trazas(antes)
    assert despues != antes
    assert resumen["desgloses"] == 1
    cuerpo = guardado.json()
    assert {
        k: cuerpo[k] for k in ("codigo", "cambios", "primera", "version_nueva", "desgloses")
    } == {
        "codigo": "001",
        "cambios": 0,
        "primera": False,
        "version_nueva": False,
        "desgloses": 1,
    }
    assert cuerpo["mensaje"] == SOLO_DESGLOSE_GUARDADO
    assert _trazas(_caso) == [TRAZA_0_625]
    assert _codigos(navegador) == ["001"]
    leido = navegador.get(f"/v1/hoja/borradores/{id_}")
    assert leido.status_code == 200, leido.text
    despues = leido.json()["resumen"]
    assert (despues["rev"], despues["cambios"], despues["desgloses"]) == (1, 0, 0)
    assert despues["guardado_como"] is None
    otra_vez = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": 1, "fuente": ""},
        headers=protegida(ficha),
    )
    assert otra_vez.status_code == 422, otra_vez.text
    abierto = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": "001"},
        headers=protegida(ficha),
    )
    assert abierto.status_code == 201, abierto.text
    detalle = navegador.get(
        f"/v1/hoja/borradores/{abierto.json()['id']}/vistas/apu", params={"partida": "AF-LLAVE"}
    ).json()["detalle"]
    assert detalle["desperdicios"] == [LLAVE_0_625]


def test_cambiar_el_desglose_y_el_rendimiento_crea_la_version_con_las_trazas(_caso: Path) -> None:
    """La mezcla: el rendimiento pasa de 20 a 25 (una celda) y la llave pasa de 0,8 + 25 % a
    0,625 + 60 % (misma cantidad, un desglose). El resumen cuenta dos cambios, uno de desglose;
    guardar crea la 002 como siempre, registra la celda, escribe la traza y cierra el borrador."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    editado = navegador.put(
        f"/v1/hoja/borradores/{id_}/apu/AF-LLAVE",
        json={
            "rev": 0,
            "rendimiento": "25",
            "materiales": ["0,625"],
            "desperdicios": ["60"],
            "equipos": cantidades["equipos"],
            "mano_obra": cantidades["mano de obra"],
        },
        headers=protegida(ficha),
    )
    assert editado.status_code == 200, editado.text
    resumen = editado.json()["resumen"]
    assert (resumen["rev"], resumen["cambios"], resumen.get("desgloses")) == (1, 2, 1)
    guardado = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": 1, "fuente": "Acta ficticia de obra"},
        headers=protegida(ficha),
    )
    assert guardado.status_code == 200, guardado.text
    cuerpo = guardado.json()
    assert {k: cuerpo.get(k) for k in ("codigo", "cambios", "version_nueva", "desgloses")} == {
        "codigo": "002",
        "cambios": 1,
        "version_nueva": True,
        "desgloses": 1,
    }
    assert cuerpo["mensaje"] == "Se guardó la versión 002 con 1 cambio registrado."
    assert _trazas(_caso) == [TRAZA_0_625]
    assert _codigos(navegador) == ["001", "002"]
    assert navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]["guardado_como"] == "002"


# --- Arbitraje de la revisión de A.6 (acta DS-48h y DS-48i) -------------------------------------

DESGLOSE_YA_GUARDADO = "Ese desglose ya está guardado."


def _guardar(navegador, ficha, id_, rev, fuente="", **extra):
    return navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": rev, "fuente": fuente, **extra},
        headers=protegida(ficha),
    )


def _resumen(navegador, id_) -> dict:
    leido = navegador.get(f"/v1/hoja/borradores/{id_}")
    assert leido.status_code == 200, leido.text
    return leido.json()["resumen"]


def test_si_otro_ya_guardo_ese_mismo_desglose_es_422_propio_y_la_cuenta_se_vacia(
    _caso: Path,
) -> None:
    """La Hoja deja 0,625 + 60 % sobre 0,8 + 25 %; antes de guardar, otro (Componer) escribe en la
    base ese mismo desglose. Guardar no tiene nada que escribir: 422 con su texto, la base igual, y
    el borrador deja de contar el desglose (antes seguía con un cambio y cada Guardar repetía el
    422)."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    editado = _editar(navegador, ficha, id_, cantidades, 0, ["0,625"], ["60"])
    assert editado.status_code == 200, editado.text
    _con_traza(_caso, TRAZA_0_625)
    antes = _volcado(_caso)
    respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json()["detalle"] == DESGLOSE_YA_GUARDADO
    assert _volcado(_caso) == antes
    despues = _resumen(navegador, id_)
    assert (despues["rev"], despues["cambios"], despues["desgloses"]) == (1, 0, 0)


def _editar_rendimiento(navegador, ficha, id_, cantidades, rev, rendimiento):
    """Una edición del APU de la llave sin `desperdicios`: solo el rendimiento."""
    return navegador.put(
        f"/v1/hoja/borradores/{id_}/apu/AF-LLAVE",
        json={
            "rev": rev,
            "rendimiento": rendimiento,
            "materiales": cantidades["materiales"],
            "equipos": cantidades["equipos"],
            "mano_obra": cantidades["mano de obra"],
        },
        headers=protegida(ficha),
    )


def test_el_desglose_guardado_sale_del_borrador_y_no_pisa_otro_guardado_despues(
    _caso: Path,
) -> None:
    """Tras guardar solo el desglose (0,625 + 60 %), Componer vuelve a guardar la partida con
    0,8 + 25 %. La Hoja muestra lo de la base, sin contar ningún cambio, y la versión que se guarda
    después por otra celda no reescribe la traza vieja del borrador sobre la de Componer."""
    componer = TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000"))
    _con_traza(_caso, componer)
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    assert _editar(navegador, ficha, id_, cantidades, 0, ["0,625"], ["60"]).status_code == 200
    guardado = _guardar(navegador, ficha, id_, 1)
    assert guardado.status_code == 200, guardado.text
    _con_traza(_caso, componer)  # Componer guarda otra vez la partida
    vista = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/apu", params={"partida": "AF-LLAVE"})
    assert vista.json()["detalle"]["desperdicios"] == [LLAVE_0_8]
    assert _resumen(navegador, id_)["cambios"] == 0
    editado = _editar_rendimiento(navegador, ficha, id_, cantidades, 1, "25")
    assert editado.status_code == 200, editado.text
    version = _guardar(navegador, ficha, id_, editado.json()["rev"], "Acta ficticia de obra")
    assert version.status_code == 200, version.text
    assert (version.json()["codigo"], version.json()["desgloses"]) == ("002", 0)
    assert _trazas(_caso) == [componer]


DESGLOSE_SOBRE_LA_002 = (
    "Otra persona guardó la versión 002 después de que usted abrió la 001. Si guarda, el desglose "
    "del desperdicio se guardará sobre lo de la 002: vale para la partida, no para una versión."
)


def test_con_una_version_posterior_guardar_el_desglose_pide_confirmar_como_la_version(
    _caso: Path,
) -> None:
    """Como el guardado de una versión (D-5, acta DS-48h): si otra persona guardó la 002 después
    de abrir la 001, guardar solo el desglose es 409 con `version_mas_nueva` y un texto que no
    habla de versión nueva; la base no cambia. Con la confirmación, guarda la traza y no crea
    otra versión."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    assert _editar(navegador, ficha, id_, cantidades, 0, ["0,625"], ["60"]).status_code == 200
    otro, ficha_otro = con_cuenta(app, "ana")  # otra ficha: otro borrador de la misma 001
    de_otro, _ = _abrir(otro, ficha_otro)
    assert _editar_rendimiento(otro, ficha_otro, de_otro, cantidades, 0, "25").status_code == 200
    assert _guardar(otro, ficha_otro, de_otro, 1, "Acta ficticia").json()["codigo"] == "002"
    antes = _volcado(_caso)
    respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json() == {"detalle": DESGLOSE_SOBRE_LA_002, "version_mas_nueva": "002"}
    assert _volcado(_caso) == antes
    confirmado = _guardar(navegador, ficha, id_, 1, confirmar_version_mas_nueva=True)
    assert confirmado.status_code == 200, confirmado.text
    assert (confirmado.json()["version_nueva"], confirmado.json()["codigo"]) == (False, "001")
    assert _trazas(_caso) == [TRAZA_0_625]
    assert _codigos(navegador) == ["001", "002"]


# --- Pruebas que faltaban (mutantes vivos de la revisión de A.6, acta DS-48i) -------------------

SOLO_LECTURA = (
    "Esta versión está en solo lectura: alguna de sus partidas ya no tiene composición vigente "
    "en el catálogo, así que recalcularla cambiaría sus precios."
)


def test_solo_el_desglose_de_una_version_en_solo_lectura_no_se_guarda(_caso: Path) -> None:
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    assert _editar(navegador, ficha, id_, cantidades, 0, ["0,625"], ["60"]).status_code == 200
    vivo = hoja_borradores.obtener(sesiones.huella_de(ficha), id_)
    vivo.abierta = replace(vivo.abierta, solo_lectura=True)
    antes = _volcado(_caso)
    respuesta = _guardar(navegador, ficha, id_, 1)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": SOLO_LECTURA}
    assert _volcado(_caso) == antes


def test_cambiar_la_cantidad_y_el_desglose_de_la_misma_linea_es_un_solo_cambio(
    _caso: Path,
) -> None:
    """De 0,8 + 25 % (= 1) a 2 + 5 % (= 2,10): cambia la celda de la cantidad, y su desglose viaja
    con ella; no cuenta aparte como desglose."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    editado = _editar(navegador, ficha, id_, cantidades, 0, ["2"], ["5"])
    assert editado.status_code == 200, editado.text
    resumen = editado.json()["resumen"]
    assert (resumen["cambios"], resumen["desgloses"]) == (1, 0)


def test_si_cambian_las_vigentes_entre_dos_ediciones_iguales_la_cuenta_se_rehace(
    _caso: Path,
) -> None:
    """La Hoja deja 0,625 + 60 % (un cambio); Componer guarda ese mismo desglose; mandar otra vez la
    misma edición no sube el rev, pero ya no hay nada que contar."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    primera = _editar(navegador, ficha, id_, cantidades, 0, ["0,625"], ["60"])
    assert primera.json()["resumen"]["cambios"] == 1
    _con_traza(_caso, TRAZA_0_625)
    segunda = _editar(navegador, ficha, id_, cantidades, 1, ["0,625"], ["60"])
    assert segunda.status_code == 200, segunda.text
    resumen = segunda.json()["resumen"]
    assert (resumen["rev"], resumen["cambios"], resumen["desgloses"]) == (1, 0, 0)


def test_dos_lineas_con_desglose_se_dicen_en_plural(_caso: Path) -> None:
    """EL-SALIDA-TOMA lleva dos materiales de 1 pieza; 0,8 + 25 % en cada uno da la misma cantidad
    (0,8 × 1,25 = 1, a mano): dos desgloses, sin versión nueva."""
    navegador, ficha = con_cuenta(app, "ana")
    id_, _ = _abrir(navegador, ficha)
    detalle = navegador.get(
        f"/v1/hoja/borradores/{id_}/vistas/apu", params={"partida": "EL-SALIDA-TOMA"}
    ).json()["detalle"]
    cantidades = {g["clave"]: [f["cantidad"] for f in g["filas"]] for g in detalle["grupos"]}
    assert cantidades["materiales"] == ["1", "1"]
    editado = navegador.put(
        f"/v1/hoja/borradores/{id_}/apu/EL-SALIDA-TOMA",
        json={
            "rev": 0,
            "rendimiento": "10",
            "materiales": ["0,8", "0,8"],
            "desperdicios": ["25", "25"],
            "equipos": cantidades["equipos"],
            "mano_obra": cantidades["mano de obra"],
        },
        headers=protegida(ficha),
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["resumen"]["desgloses"] == 2
    guardado = _guardar(navegador, ficha, id_, 1)
    assert guardado.status_code == 200, guardado.text
    assert guardado.json()["mensaje"] == (
        "Se guardó el desglose del desperdicio de 2 líneas. La cantidad no cambió, así que la "
        "versión 001 sigue siendo la misma."
    )


def test_guardar_el_desglose_quitado_deja_la_partida_sin_trazas(_caso: Path) -> None:
    """Con 0,8 + 25 % vigente, la Hoja le quita el porcentaje a la llave (la cantidad sigue en 1):
    guardar solo ese desglose registra un guardado sin trazas."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    assert _editar(navegador, ficha, id_, cantidades, 0, ["1"], [""]).status_code == 200
    guardado = _guardar(navegador, ficha, id_, 1)
    assert guardado.status_code == 200, guardado.text
    assert guardado.json()["version_nueva"] is False
    assert _trazas(_caso) == []


# --- Quién guardó el desglose (mejora de A.6, acta DS-48g, opción A) ----------------------------
#
# `apu_desperdicio_guardado.responsable` (migración `caso_0024`) guarda la cuenta que escribió la
# traza: la de la sesión (`Nombre <login>`, RF-82), como el registro de cambios de una versión.
# La pestaña APU lo dice en `detalle.desglose_guardado` cuando alguna línea muestra el desglose
# que está en la base; lo guardado antes de la columna sale con `responsable: null`.

ANA = "Ana <ana>"


def _responsables(ruta: Path) -> list[str | None]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        return [
            f[0] for f in bd.execute("SELECT responsable FROM apu_desperdicio_guardado ORDER BY id")
        ]


def test_sin_desglose_no_hay_quien_lo_guardo(_caso: Path) -> None:
    assert _detalle("ana")["desglose_guardado"] is None


def test_un_desglose_de_antes_de_la_columna_no_sabe_quien_lo_guardo(_caso: Path) -> None:
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    assert _detalle("ana")["desglose_guardado"] == {
        "responsable": None,
        "fecha_hora": "2026-11-13T09:00:00",
    }


def test_guardar_solo_el_desglose_anota_la_cuenta_de_la_sesion(_caso: Path) -> None:
    """Ana guarda solo el desglose (sin versión): la fila nueva lleva «Ana <ana>», su borrador y
    otro borrador de la 001 lo dicen, y la de antes sigue sin responsable."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    assert _editar(navegador, ficha, id_, cantidades, 0, ["0,625"], ["60"]).status_code == 200
    guardado = _guardar(navegador, ficha, id_, 1)
    assert guardado.status_code == 200, guardado.text
    assert _responsables(_caso) == [None, ANA]
    propio = _detalle_de(navegador, id_)["desglose_guardado"]
    assert propio["responsable"] == ANA
    assert datetime.fromisoformat(propio["fecha_hora"]) > datetime(2026, 11, 13, 9)
    otro, ficha_otro = con_cuenta(app, "rita")
    abierto = otro.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": "001"},
        headers=protegida(ficha_otro),
    )
    assert abierto.status_code == 201, abierto.text
    assert _detalle_de(otro, abierto.json()["id"])["desglose_guardado"] == propio


def test_guardar_la_version_con_el_desglose_tambien_anota_la_cuenta(_caso: Path) -> None:
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    editado = _editar(navegador, ficha, id_, cantidades, 0, ["2"], ["5"])
    assert editado.status_code == 200, editado.text
    version = _guardar(navegador, ficha, id_, 1, "Acta ficticia de obra")
    assert version.status_code == 200, version.text
    assert _responsables(_caso) == [None, ANA]


def test_un_desglose_sin_guardar_no_se_atribuye_al_de_la_base(_caso: Path) -> None:
    """La línea muestra el desglose del borrador (0,625 + 60 %), no el de la base: no hay
    responsable que decir de lo que todavía no se guardó."""
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    navegador, ficha = con_cuenta(app, "ana")
    id_, cantidades = _abrir(navegador, ficha)
    editado = _editar(navegador, ficha, id_, cantidades, 0, ["0,625"], ["60"])
    assert editado.status_code == 200, editado.text
    assert editado.json()["apu"]["detalle"]["desglose_guardado"] is None
    assert _detalle_de(navegador, id_)["desglose_guardado"] is None
