"""`PUT /v1/riesgo/mapa` y la precarga de `GET /v1/riesgo/insumos` (mejora de la DS-81; DS-90 a
DS-93). Datos FICTICIOS (`tests/fixtures/riesgo_obra.py`: «Vía Ficticia Riesgo», en USD, con VR-001
y VR-002 y los mismos tres insumos).

Oráculos a mano:
- lo que se guarda para VR-001 vuelve en `mapa_guardado` de VR-001 (`de_version` VR-001) y, sin mapa
  propio, también en el de VR-002 (`de_version` VR-001);
- guardar lo mismo otra vez responde `guardado: false`;
- un insumo que la versión no tiene no se precarga y vuelve en `descartados` con motivo «insumo»;
- la tasa del BCV no se ofrece en una obra en USD: 422 y no queda nada;
- obra o versión que no existe: 404; la clave de API: 403 (el mapa lo recuerda una cuenta), también
  con el módulo apagado (la cuenta se decide antes que el módulo, como en vial); sin `ver_riesgo`:
  403; forma mala: 422 sin eco, con el mensaje propio del mapa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from api.rutas import riesgo as rutas
from aplicacion.riesgo.proyeccion import SERIE_TASA
from tests.fixtures.produccion_api import Web, cliente_con_clave
from tests.fixtures.riesgo_obra import (
    ASFALTO,
    CON_LINEA_BASE,
    GASOIL,
    MAPA,
    OBRA,
    SIN_LINEA_BASE,
)
from tests.fixtures.riesgo_web import en_la_via, instalacion_con_la_via, plantillas_de_la_via

MAPA_RUTA = "/v1/riesgo/mapa"
INSUMOS = "/v1/riesgo/insumos"


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    return plantillas_de_la_via(tmp_path_factory.mktemp("plantilla_riesgo_mapa"))


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch):
    with instalacion_con_la_via(_plantillas, monkeypatch):
        yield


def _guardar(web: Web, mapa: dict, version: str = CON_LINEA_BASE, **otros):
    cuerpo = {"proyecto": OBRA, "version": version, "mapa": mapa, **otros}
    return web.cliente.put(MAPA_RUTA, headers=web.cabeceras(), json=cuerpo)


def _precarga(web: Web, version: str) -> dict | None:
    r = web.get(INSUMOS, params={"proyecto": OBRA, "version": version})
    assert r.status_code == 200, r.text
    return r.json()["mapa_guardado"]


def test_sin_nada_guardado_no_hay_precarga() -> None:
    assert _precarga(en_la_via(), CON_LINEA_BASE) is None


def test_lo_guardado_vuelve_en_los_insumos_de_la_version() -> None:
    web = en_la_via()
    r = _guardar(web, MAPA)
    assert r.status_code == 200, r.text
    assert r.json() == {"guardado": True}
    assert _precarga(web, CON_LINEA_BASE) == {
        "mapa": MAPA,
        "de_version": CON_LINEA_BASE,
        "descartados": [],
    }


def test_la_version_sin_mapa_propio_toma_el_de_la_obra() -> None:
    web = en_la_via()
    assert _guardar(web, {ASFALTO: MAPA[ASFALTO]}).status_code == 200
    assert _precarga(web, SIN_LINEA_BASE) == {
        "mapa": {ASFALTO: MAPA[ASFALTO]},
        "de_version": CON_LINEA_BASE,
        "descartados": [],
    }


def test_guardar_lo_mismo_no_guarda_otra_vez() -> None:
    web = en_la_via()
    assert _guardar(web, MAPA).json() == {"guardado": True}
    assert _guardar(web, MAPA).json() == {"guardado": False}


def test_el_insumo_que_no_esta_se_descarta_y_se_dice() -> None:
    web = en_la_via()
    assert _guardar(web, {**MAPA, "Insumo retirado": MAPA[GASOIL]}).status_code == 200
    assert _precarga(web, CON_LINEA_BASE) == {
        "mapa": MAPA,
        "de_version": CON_LINEA_BASE,
        "descartados": [{"insumo": "Insumo retirado", "serie": MAPA[GASOIL], "motivo": "insumo"}],
    }


def test_la_serie_que_la_moneda_no_admite_422_y_no_guarda() -> None:
    web = en_la_via()
    r = _guardar(web, {ASFALTO: SERIE_TASA})
    assert r.status_code == 422, r.text
    assert "no se ofrece" in r.json()["detalle"]
    assert _precarga(web, CON_LINEA_BASE) is None


def test_obra_o_version_que_no_existe_404() -> None:
    web = en_la_via()
    assert _guardar(web, MAPA, version="NO-HAY").status_code == 404
    r = web.cliente.put(
        MAPA_RUTA,
        headers=web.cabeceras(),
        json={"proyecto": "Obra que no existe", "version": CON_LINEA_BASE, "mapa": MAPA},
    )
    assert r.status_code == 404


def test_con_la_clave_de_api_403() -> None:
    r = cliente_con_clave().put(
        MAPA_RUTA, json={"proyecto": OBRA, "version": CON_LINEA_BASE, "mapa": MAPA}
    )
    assert r.status_code == 403, r.text
    assert r.json()["detalle"] == rutas.MENSAJE_MAPA_SOLO_CUENTA


def test_con_la_clave_y_el_modulo_apagado_403_antes_que_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api import acceso_modulos

    monkeypatch.setattr(acceso_modulos, "modulos_activos", lambda _instalacion: frozenset())
    r = cliente_con_clave().put(
        MAPA_RUTA, json={"proyecto": OBRA, "version": CON_LINEA_BASE, "mapa": MAPA}
    )
    assert r.status_code == 403, r.text
    assert r.json()["detalle"] == rutas.MENSAJE_MAPA_SOLO_CUENTA


def test_sin_ver_riesgo_403(monkeypatch: pytest.MonkeyPatch) -> None:
    from seguridad import permisos

    web = en_la_via("ana")
    monkeypatch.setitem(
        permisos.PERMISOS,
        permisos.Accion.VER_RIESGO,
        frozenset({permisos.Rol.REVISA, permisos.Rol.ADMINISTRADOR}),
    )
    assert _guardar(web, MAPA).status_code == 403


@pytest.mark.parametrize(
    "cambio",
    [
        {"mapa": {ASFALTO: 7}},
        {"mapa": "no es un mapa"},
        {"version": ""},
        {"sobra": 1},
        {"mapa": {f"insumo {i}": MAPA[ASFALTO] for i in range(501)}},
    ],
)
def test_forma_mala_422_sin_eco(cambio: dict) -> None:
    web = en_la_via()
    cuerpo = {"proyecto": OBRA, "version": CON_LINEA_BASE, "mapa": MAPA, **cambio}
    r = web.cliente.put(MAPA_RUTA, headers=web.cabeceras(), json=cuerpo)
    assert r.status_code == 422, r.text
    assert r.json() == {"detalle": rutas.MENSAJE_MAPA_FORMA}
    assert rutas.MENSAJE_MAPA_FORMA != rutas.MENSAJE_FORMA
