"""`POST /v1/hoja/libro`: llevar a la Hoja el libro auditado (ola 2, línea 3, 2026-11-13). FICTICIO.

De punta a punta por la API: el libro con un APU por hoja de `tests/fixtures/libro_apu_por_hoja.py`
y su presupuesto de dos frentes (FRENTE A con el 60 % de cada cantidad, FRENTE B con el 40 %) van
al borrador de la Hoja de una obra sin versiones, sin teclear nada:

- cada APU entra al catálogo con sus materiales, equipos y mano de obra, su rendimiento y su precio
  en la lista para armar de la carpeta (la misma en que escribe Componer), y cada precio que puso
  el libro lleva su referencia (el libro y la celda);
- cada renglón del presupuesto es un renglón de la Hoja con su cantidad, su origen (la celda de la
  cantidad) y su frente (la hoja del presupuesto); el renglón 6 no tiene APU y no se lleva;
- los porcentajes del libro (prestaciones, administración y utilidad) son los del borrador;
- la respuesta dice, por partida, el P.U. impreso y el de la Hoja, y si casan (un centavo).

Oráculos a mano (memoria de cálculo del libro ficticio): VF-001 2,0777625 → 2,08 (impreso 2,08,
casa); VF-002 4,1323… → 4,13 (impreso 4,50); VF-003 0,81213 → 0,81 (impreso 0,78, solo redondeo);
VF-004 sin el financiamiento: (500 + 40 × 3,5) × 1,15 × 1,10 = 809,6 (impreso 820,00); VF-005 sin el
bono: 4 × 30 × 3,5 ÷ 4.000 × 1,265 = 0,132825 → 0,13 (impreso 0,20).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.rutas import hoja as rutas_hoja
from aplicacion import hoja_borradores, libro_a_la_hoja
from core.budget.moneda import declarar_moneda
from core.budget.persistencia import crear_proyecto
from core.catalog import abrir_sesion, crear_motor
from core.contracts import Dominio
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import OBRA, sembrar_vivienda
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.hoja_versiones_api import registrar_tasa_en
from tests.fixtures.libro_apu_por_hoja import (
    APUS,
    Material,
    libro_apu,
    libro_presupuesto_por_hojas,
)
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

HOY = date(2026, 10, 31)
RUTA = "/v1/hoja/libro"
VIA = "Vía ficticia por frentes"
FRENTES = ["FRENTE A", "FRENTE B"]


def _carpeta(ruta: Path) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            sembrar_vivienda(s)  # la lista «Lista Bs de prueba» y una obra con versiones
            via = crear_proyecto(s, VIA, dominio=Dominio.CIVIL)  # la obra sin versiones
            declarar_moneda(s, via, "Bs", responsable="Ana <ana>")  # la de la carpeta
            s.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_hoja_libro")
    return {"instalacion": plantilla_con_cuentas(carpeta), "via.db": _carpeta(carpeta / "via.db")}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / "via.db").write_bytes(_plantillas["via.db"].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: HOY)  # el «hoy» de toda la Hoja, también este
    yield
    hoja_borradores.olvidar_todo()
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _entrar(login: str = "ana") -> tuple[TestClient, str]:
    navegador, ficha = con_cuenta(app, login)
    elegida = navegador.post(
        "/v1/casos/actual", json={"nombre": "via.db"}, headers=protegida(ficha)
    )
    assert elegida.status_code == 200, elegida.text
    return navegador, ficha


@pytest.fixture
def ana() -> tuple[TestClient, str]:
    return _entrar()


def _llevar(cuenta, *, libro: bytes | None = None, presupuesto: bool = True, **datos):
    navegador, ficha = cuenta
    archivos = {"libro": ("obra_a.xlsx", libro or libro_apu())}
    if presupuesto:
        archivos["presupuesto"] = ("frentes.xlsx", libro_presupuesto_por_hojas())
    formulario = {"proyecto": VIA, "moneda": "Bs", "hoja_presupuesto": FRENTES, **datos}
    return navegador.post(RUTA, files=archivos, data=formulario, headers=protegida(ficha))


def _filas(navegador: TestClient, id_: str) -> list[dict]:
    r = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/presupuesto")
    assert r.status_code == 200, r.text
    return r.json()["filas"]


def _referencias() -> dict[str, str]:
    with closing(sqlite3.connect(config.carpeta_casos() / "via.db")) as conexion:
        return dict(
            conexion.execute(
                "SELECT i.descripcion, r.referencia FROM referencia_precio r "
                "JOIN precio_insumo p ON p.id = r.precio_id JOIN insumo i ON i.id = p.insumo_id"
            ).fetchall()
        )


# --- de punta a punta -------------------------------------------------------------------------


def test_el_libro_auditado_llega_a_la_hoja_sin_teclear(ana) -> None:
    navegador, _ficha = ana
    r = _llevar(ana)
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    cuerpo = r.json()
    assert cuerpo["renglones"] == 10
    assert cuerpo["sin_apu"] == ["FRENTE A, renglón 6", "FRENTE B, renglón 6"]
    assert cuerpo["moneda"] == "Bs"
    assert [
        (p["codigo"], p["codigo_libro"], p["hoja"], p["nueva"], p["precio_impreso"])
        for p in cuerpo["partidas"]
    ] == [
        ("VF-001", "VF-001", "APU 1", True, "2.08"),
        ("VF-002", "VF-002", "APU 2", True, "4.50"),
        ("VF-003", "VF-003", "APU 3", True, "0.78"),
        ("VF-004", "VF-004", "APU 4", True, "820.00"),
        ("VF-005", "VF-005", "APU 5", True, "0.20"),
    ]
    assert [(p["precio_hoja"], p["casa"]) for p in cuerpo["partidas"]] == [
        ("2.08", True),
        ("4.13", False),
        ("0.81", False),
        ("809.60", False),
        ("0.13", False),
    ]

    filas = _filas(navegador, cuerpo["borrador_id"])
    assert [(f["clave"], f["cantidad"]) for f in filas[:3]] == [
        ("VF-001|libro:FRENTE A!E4", "600"),
        ("VF-002|libro:FRENTE A!E5", "72"),
        ("VF-003|libro:FRENTE A!E6", "270"),
    ]
    assert len(filas) == 10
    assert filas[5]["clave"] == "VF-001|libro:FRENTE B!E4"
    assert filas[0]["pu"]["texto"] == "2.08"


def test_cada_precio_del_libro_lleva_su_referencia(ana) -> None:
    assert _llevar(ana).status_code == 200
    referencias = _referencias()
    assert referencias["Emulsión asfáltica ficticia"] == "obra_a.xlsx, APU 1!F9"
    assert referencias["Volteo ficticio"] == "obra_a.xlsx, APU 2!D13"
    assert referencias["Chofer ficticio"] == "obra_a.xlsx, APU 2!D19"


def test_llevar_otra_vez_no_duplica_ni_el_catalogo_ni_los_renglones(ana) -> None:
    navegador, _ = ana
    primero = _llevar(ana).json()
    segundo = _llevar(ana)
    assert segundo.status_code == 200, segundo.text
    cuerpo = segundo.json()
    assert cuerpo["borrador_id"] == primero["borrador_id"]
    assert [p["nueva"] for p in cuerpo["partidas"]] == [False] * 5
    assert len(_filas(navegador, cuerpo["borrador_id"])) == 10


def test_otro_libro_con_un_apu_distinto_entra_como_variante(ana) -> None:
    """El APU 1 de la obra B cuesta otro precio: entra como VF-001-B; los demás se reutilizan."""
    _llevar(ana)
    primero = replace(
        APUS[0],
        materiales=(Material(1, "Emulsión asfáltica ficticia", "lt", "0.50", "4", "2.50"),),
    )
    r = _llevar(ana, libro=libro_apu((primero, *APUS[1:])))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert [(p["codigo"], p["nueva"]) for p in cuerpo["partidas"]] == [
        ("VF-001-B", True),
        ("VF-002", False),
        ("VF-003", False),
        ("VF-004", False),
        ("VF-005", False),
    ]


def test_sin_presupuesto_la_cantidad_es_la_de_cada_apu_y_el_frente_el_dicho(ana) -> None:
    navegador, _ = ana
    r = _llevar(ana, presupuesto=False, frente="Frente único", hoja_presupuesto=[])
    assert r.status_code == 200, r.text
    filas = _filas(navegador, r.json()["borrador_id"])
    assert [(f["clave"], f["cantidad"]) for f in filas] == [
        ("VF-001|libro:APU 1!D5", "1.000"),
        ("VF-002|libro:APU 2!D5", "120"),
        ("VF-003|libro:APU 3!D5", "500"),
        ("VF-004|libro:APU 4!D5", "2"),
        ("VF-005|libro:APU 5!D5", "1.000"),
    ]


# --- lo que no se lleva -----------------------------------------------------------------------


def test_un_libro_en_otra_moneda_que_la_carpeta_no_se_lleva(ana) -> None:
    r = _llevar(ana, moneda="USD")
    assert r.status_code == 409
    assert r.json()["detalle"] == (
        "El libro está en USD y esta carpeta arma en Bs (lista «Lista Bs de prueba»): Sílice no "
        "cambia la moneda de sus precios. Lleve el libro a una carpeta que arme en USD."
    )


VIA_USD = "Vía ficticia en dólares"


def _obra_en_dolares() -> None:
    """Una obra sin versiones declarada en USD (choque 16: la carpeta arma en Bs) y una tasa
    ficticia del BCV del día anterior, con la que la Hoja la valoraría convirtiendo."""
    motor = crear_motor(f"sqlite:///{(config.carpeta_casos() / 'via.db').as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            via = crear_proyecto(s, VIA_USD, dominio=Dominio.CIVIL)
            declarar_moneda(s, via, "USD", responsable="Ana <ana>")
            registrar_tasa_en(s, date(2026, 10, 30), "40")
            s.commit()
    finally:
        motor.dispose()


def _partidas_del_libro() -> list[str]:
    with closing(sqlite3.connect(config.carpeta_casos() / "via.db")) as conexion:
        filas = conexion.execute("SELECT codigo FROM partida WHERE codigo LIKE 'VF-%'")
        return [codigo for (codigo,) in filas.fetchall()]


def test_un_libro_en_otra_moneda_que_la_obra_no_se_lleva(ana) -> None:
    """La carpeta arma en Bs y el libro está en Bs, pero la obra está en USD: la Hoja convertiría
    cada precio del libro con la tasa del BCV del día del borrador, una tasa que el libro no dice
    (D6). No se lleva, y ni el catálogo ni los borradores cambian."""
    navegador, _ = ana
    _obra_en_dolares()
    r = _llevar(ana, proyecto=VIA_USD)
    assert r.status_code == 409, r.text
    assert r.json()["detalle"] == (
        f"La obra «{VIA_USD}» está en USD y el libro en Bs: Sílice no convierte los precios del "
        "libro. Lleve el libro a una obra en Bs."
    )
    assert _partidas_del_libro() == []
    assert _borradores(navegador) == []


# --- todo o nada (hallazgo 3 de la ronda 1 del árbitro de la ola 2) ----------------------------
#
# La falla se fuerza en `importaciones.anotar`, el último paso antes de confirmar: el catálogo ya
# tiene las partidas del libro (con `flush`) y el borrador ya tiene sus renglones.


def _que_falle(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(*_a, **_k):
        raise RuntimeError("falla forzada después de escribir el catálogo")

    monkeypatch.setattr(libro_a_la_hoja.importaciones, "anotar", falla)


def test_si_falla_al_final_no_queda_nada_y_el_borrador_nuevo_se_descarta(
    ana, monkeypatch: pytest.MonkeyPatch
) -> None:
    navegador, _ = ana
    with monkeypatch.context() as m:
        _que_falle(m)
        r = _llevar(ana)
    assert r.status_code == 500
    assert _partidas_del_libro() == []
    assert _borradores(navegador) == []
    # Sin la falla entra entero, con los códigos del libro: nada quedó a medias que pida «-B».
    otra = _llevar(ana)
    assert otra.status_code == 200, otra.text
    assert [(p["codigo"], p["nueva"]) for p in otra.json()["partidas"]] == [
        (f"VF-00{n}", True) for n in range(1, 6)
    ]


def test_si_falla_al_final_el_borrador_que_ya_estaba_queda_como_estaba(
    ana, monkeypatch: pytest.MonkeyPatch
) -> None:
    navegador, _ = ana
    id_ = _llevar(ana).json()["borrador_id"]
    antes = [(f["clave"], f["cantidad"]) for f in _filas(navegador, id_)]
    rev = _rev(navegador, id_)
    primero = replace(
        APUS[0],
        materiales=(Material(1, "Emulsión asfáltica ficticia", "lt", "0.50", "4", "2.50"),),
    )
    with monkeypatch.context() as m:
        _que_falle(m)
        r = _llevar(ana, libro=libro_apu((primero, *APUS[1:])))  # crearía «VF-001-B»
    assert r.status_code == 500
    assert [(f["clave"], f["cantidad"]) for f in _filas(navegador, id_)] == antes
    assert len(antes) == 10
    assert _rev(navegador, id_) == rev
    assert sorted(_partidas_del_libro()) == [f"VF-00{n}" for n in range(1, 6)]


def test_una_obra_con_versiones_no_recibe_el_libro(ana) -> None:
    r = _llevar(ana, proyecto=OBRA)
    assert r.status_code == 409
    assert r.json()["detalle"] == (
        f"La obra «{OBRA}» ya tiene la versión VIV-001: el libro se lleva a una obra sin "
        "versiones, para que sus precios sean los del libro. Cree una obra nueva para el libro."
    )


def test_apus_con_porcentajes_distintos_no_se_llevan_juntos(ana) -> None:
    tercero = replace(APUS[2], utilidad="12")
    r = _llevar(ana, libro=libro_apu((*APUS[:2], tercero, *APUS[3:])))
    assert r.status_code == 422
    assert r.json()["detalle"] == (
        "Las hojas del libro no usan los mismos porcentajes y la Hoja lleva uno solo por obra: "
        "APU 3 usa una utilidad del 12 % y las demás del 10 %."
    )


def test_quien_revisa_no_lleva_el_libro() -> None:
    r = _llevar(_entrar("rita"))
    assert r.status_code == 403
    assert r.json()["detalle"] == MENSAJE_PERMISO


def test_con_la_clave_de_api_no_se_lleva() -> None:
    navegador = cliente(app)
    navegador.headers[CABECERA] = crear_clave_de_prueba()
    r = navegador.post(
        RUTA,
        files={"libro": ("obra_a.xlsx", libro_apu())},
        data={"proyecto": VIA, "moneda": "Bs"},
    )
    assert r.status_code == 403


# --- el presupuesto agrupado por frente (paso 3) -----------------------------------------------
#
# `GET /v1/hoja/borradores/{id}/vistas/frentes`: el subtotal de cada frente y el total general,
# calculados por el servidor con los totales de cada renglón (cantidad × P.U.). Oráculos a mano, con
# los P.U. exactos de la memoria: FRENTE A = 600 × 2,0777625 + 72 × 4,1323… (= 297,528) + 270 ×
# 0,81213 + 1,2 × 809,6 + 600 × 0,132825 = 2.814,6756; FRENTE B (el 40 %) = 1.876,4504; total
# 4.691,126. `PUT /v1/hoja/borradores/{id}/frentes` pone el frente de un renglón a mano.


def _frentes(navegador: TestClient, id_: str) -> dict:
    r = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/frentes")
    assert r.status_code == 200, r.text
    return r.json()


def _resumen_frentes(cuerpo: dict) -> list[tuple]:
    return [
        (f["frente"], f["renglones"], f["pendientes"], f["total"]["texto"])
        for f in cuerpo["frentes"]
    ]


def _rev(navegador: TestClient, id_: str) -> int:
    return next(b["rev"] for b in _borradores(navegador) if b["id"] == id_)


def _borradores(navegador: TestClient) -> list[dict]:
    r = navegador.get("/v1/hoja/borradores")
    assert r.status_code == 200, r.text
    return r.json()["borradores"]


def test_el_presupuesto_del_libro_sale_agrupado_por_frente(ana) -> None:
    navegador, _ = ana
    id_ = _llevar(ana).json()["borrador_id"]
    cuerpo = _frentes(navegador, id_)
    assert cuerpo["con_frentes"] is True
    assert _resumen_frentes(cuerpo) == [
        ("FRENTE A", 5, 0, "2814.68"),
        ("FRENTE B", 5, 0, "1876.45"),
    ]
    assert cuerpo["total"]["texto"] == "4691.13"
    presupuesto = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/presupuesto").json()
    assert presupuesto["total"]["texto"] == cuerpo["total"]["texto"]


def test_el_frente_de_un_renglon_se_pone_a_mano(ana) -> None:
    navegador, ficha = ana
    id_ = _llevar(ana).json()["borrador_id"]
    r = navegador.put(
        f"/v1/hoja/borradores/{id_}/frentes",
        json={
            "rev": _rev(navegador, id_),
            "filas": [{"clave": "VF-001|libro:FRENTE A!E4", "frente": "  Estación norte "}],
        },
        headers=protegida(ficha),
    )
    assert r.status_code == 200, r.text
    assert _resumen_frentes(r.json()["frentes"]) == [
        ("Estación norte", 1, 0, "1246.66"),
        ("FRENTE A", 4, 0, "1568.02"),
        ("FRENTE B", 5, 0, "1876.45"),
    ]
    quitado = navegador.put(
        f"/v1/hoja/borradores/{id_}/frentes",
        json={
            "rev": r.json()["rev"],
            "filas": [{"clave": "VF-001|libro:FRENTE A!E4", "frente": ""}],
        },
        headers=protegida(ficha),
    )
    assert quitado.status_code == 200, quitado.text
    assert _resumen_frentes(quitado.json()["frentes"])[-1] == (None, 1, 0, "1246.66")


def test_un_renglon_que_no_esta_o_un_rev_viejo_no_cambian_nada(ana) -> None:
    navegador, ficha = ana
    id_ = _llevar(ana).json()["borrador_id"]
    rev = _rev(navegador, id_)
    otro = navegador.put(
        f"/v1/hoja/borradores/{id_}/frentes",
        json={"rev": rev, "filas": [{"clave": "NO-EXISTE|x", "frente": "A"}]},
        headers=protegida(ficha),
    )
    assert otro.status_code == 422
    assert otro.json()["detalle"] == (
        "Ese renglón no está en el presupuesto o sale del espacio: vuelva a cargarlo."
    )
    viejo = navegador.put(
        f"/v1/hoja/borradores/{id_}/frentes",
        json={"rev": rev - 1, "filas": [{"clave": "VF-001|libro:FRENTE A!E4", "frente": "A"}]},
        headers=protegida(ficha),
    )
    assert viejo.status_code == 409
    assert _resumen_frentes(_frentes(navegador, id_))[0][0] == "FRENTE A"


def test_los_frentes_se_guardan_con_la_version_y_vuelven_al_abrirla(ana) -> None:
    navegador, ficha = ana
    id_ = _llevar(ana).json()["borrador_id"]
    guardado = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={
            "rev": _rev(navegador, id_),
            "fuente": "Libro ficticio auditado",
            "codigo": "VIA-001",
        },
        headers=protegida(ficha),
    )
    assert guardado.status_code == 200, guardado.text
    abierto = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": VIA, "version": "VIA-001"},
        headers=protegida(ficha),
    )
    assert abierto.status_code == 201, abierto.text
    cuerpo = _frentes(navegador, abierto.json()["id"])
    assert _resumen_frentes(cuerpo) == [
        ("FRENTE A", 5, 0, "2814.68"),
        ("FRENTE B", 5, 0, "1876.45"),
    ]


def test_una_obra_sin_frentes_sale_en_un_solo_grupo(ana) -> None:
    navegador, ficha = ana
    abierto = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": OBRA, "version": "VIV-001"},
        headers=protegida(ficha),
    )
    assert abierto.status_code == 201, abierto.text
    cuerpo = _frentes(navegador, abierto.json()["id"])
    assert cuerpo["con_frentes"] is False
    assert [f["frente"] for f in cuerpo["frentes"]] == [None]
    assert cuerpo["frentes"][0]["total"] == cuerpo["total"]


def test_quien_revisa_ve_los_frentes_pero_no_los_cambia(ana) -> None:
    navegador, ficha = ana
    _llevar(ana)
    rita, ficha_rita = _entrar("rita")
    abierto = rita.post(
        "/v1/hoja/borradores",
        json={"proyecto": OBRA, "version": "VIV-001"},
        headers=protegida(ficha_rita),
    )
    assert abierto.status_code == 201, abierto.text
    id_rita = abierto.json()["id"]
    assert rita.get(f"/v1/hoja/borradores/{id_rita}/vistas/frentes").status_code == 200
    r = rita.put(
        f"/v1/hoja/borradores/{id_rita}/frentes",
        json={"rev": 0, "filas": []},
        headers=protegida(ficha_rita),
    )
    assert r.status_code == 403
