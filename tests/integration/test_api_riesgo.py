"""`/v1/riesgo`: el informe de mejora de la estimación (Tarea 15 del plan vial) y la proyección, la
comprobación hacia atrás y los insumos de una obra (Tarea 16). Datos FICTICIOS.

`ver_riesgo` es de arma, revisa y administrador: las tres cuentas pasan. Las cifras viajan como
texto con punto decimal (como en el resto de la API; la coma es cosa del front). Sin sesión ni clave
401. Oráculo a mano de la mejora: real 130, original 100 y Sílice 125 dan 23,08 %, 3,85 % y 19,23
puntos.

Oráculo a mano de la obra (`tests/fixtures/riesgo_obra.py`): total base 1.000 USD, de los que 600
son cemento asfáltico; su serie sube exactamente 10 % cada mes, así que todas las trayectorias dan
lo mismo. Con gasto uniforme en 6 meses el factor es (1,1 + 1,21 + 1,331 + 1,4641 + 1,61051 +
1,771561) ÷ 6 = 8,487171 ÷ 6 = 1,4145285, y 600 × 1,4145285 = 848,7171: P50 = P80 = 1.248,7171 y la
reserva 248,7171, toda del asfalto. Hay 24 meses completos (febrero de 2025 a enero de 2027). En la
comprobación (25 meses de historia) entran los cortes de febrero a agosto de 2026: 7, cada uno con
12 meses completos antes y su plazo de 6 meses después, y en todos lo real es igual al P80:
cobertura 1 (100,00 %). Con el inicio en enero de 2026 solo hay 11 meses completos.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from operacion import config
from seguridad import cuentas
from tests.fixtures.produccion_api import Web, cliente_con_clave
from tests.fixtures.riesgo_obra import (
    ARCHIVO,
    ASFALTO,
    CON_LINEA_BASE,
    GASOIL,
    MAPA,
    OBRA,
    SENALES,
    SIN_LINEA_BASE,
    crear_via,
)
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

D = Decimal
RUTA = "/v1/riesgo/mejora"
PROYECCION = "/v1/riesgo/proyeccion"
COMPROBACION = "/v1/riesgo/comprobacion"
INSUMOS = "/v1/riesgo/insumos"
#: El oráculo a mano del encabezado.
P80 = D("1248.7171")
RESERVA = D("248.7171")


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantilla_riesgo")
    return {"instalacion": plantilla_con_cuentas(carpeta), "via": crear_via(carpeta / ARCHIVO)}


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / ARCHIVO).write_bytes(_plantillas["via"].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()
    cuentas.FRENO.reiniciar()


def _cuerpo(**cambios) -> dict:
    base = {"costo_final_real": "130", "presupuesto_original": "100", "estimacion_silice": "125"}
    return {**base, **cambios}


@pytest.mark.parametrize("quien", ["ana", "rita", "admin"])
def test_los_tres_roles_ven_el_informe(quien: str) -> None:
    r = Web(quien).post(RUTA, json=_cuerpo())
    assert r.status_code == 200, r.text
    assert r.json() == {
        "error_original_pct": "23.08",
        "error_silice_pct": "3.85",
        "mejora_pp": "19.23",
    }


def test_con_clave_de_api_tambien() -> None:
    http: TestClient = cliente_con_clave()
    r = http.post(RUTA, json=_cuerpo())
    assert r.status_code == 200, r.text
    assert r.json()["mejora_pp"] == "19.23"


def test_sin_credenciales_401() -> None:
    from api.main import app
    from tests.fixtures.sesion_web import cliente

    assert cliente(app).post(RUTA, json=_cuerpo()).status_code == 401


def test_sin_ver_riesgo_403(monkeypatch: pytest.MonkeyPatch) -> None:
    """Una cuenta cuyo rol no tiene `ver_riesgo` recibe 403 (se quita la acción a `revisa`)."""
    from seguridad import permisos

    monkeypatch.setitem(
        permisos.PERMISOS,
        permisos.Accion.VER_RIESGO,
        frozenset({permisos.Rol.ARMA, permisos.Rol.ADMINISTRADOR}),
    )
    r = Web("rita").post(RUTA, json=_cuerpo())
    assert r.status_code == 403, r.text


def test_la_mejora_negativa_se_informa() -> None:
    r = Web("ana").post(
        RUTA,
        json=_cuerpo(costo_final_real="100", presupuesto_original="120", estimacion_silice="70"),
    )
    assert r.status_code == 200, r.text
    assert r.json()["mejora_pp"] == "-10.00"


@pytest.mark.parametrize("campo", ["costo_final_real", "presupuesto_original", "estimacion_silice"])
@pytest.mark.parametrize("texto", ["abc", "1,5", "", "NaN", "Infinity", "1e3"])
def test_texto_no_decimal_422(campo: str, texto: str) -> None:
    r = Web("ana").post(RUTA, json=_cuerpo(**{campo: texto}))
    assert r.status_code == 422, r.text
    assert "detalle" in r.json()


def test_real_cero_422() -> None:
    r = Web("ana").post(RUTA, json=_cuerpo(costo_final_real="0"))
    assert r.status_code == 422, r.text
    assert "costo final real" in r.json()["detalle"]


def test_cuerpo_incompleto_o_con_numero_json_422() -> None:
    assert Web("ana").post(RUTA, json={"costo_final_real": "130"}).status_code == 422
    assert Web("ana").post(RUTA, json=_cuerpo(costo_final_real=130)).status_code == 422


# --- Tarea 16: proyección, comprobación hacia atrás e insumos de la obra -------------------------


def _en_la_via(login: str = "ana") -> Web:
    web = Web(login)
    elegida = web.post("/v1/casos/actual", json={"nombre": ARCHIVO})
    assert elegida.status_code == 200, elegida.text
    return web


def _proyeccion(**cambios) -> dict:
    base = {
        "proyecto": OBRA,
        "version": CON_LINEA_BASE,
        "inicio": None,
        "meses": 6,
        "trayectorias": 50,
        "semilla": 1,
        "ventana_meses": 36,
        "mapa": MAPA,
    }
    return {**base, **cambios}


def _comprobacion(**cambios) -> dict:
    base = {
        "proyecto": OBRA,
        "version": CON_LINEA_BASE,
        "meses": 6,
        "trayectorias_por_corte": 20,
        "semilla": 1,
        "ventana_meses": 36,
        "mapa": MAPA,
    }
    return {**base, **cambios}


def test_la_proyeccion_toma_el_inicio_de_la_linea_base_y_da_el_oraculo() -> None:
    r = _en_la_via().post(PROYECCION, json=_proyeccion())
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["inicio"], cuerpo["inicio_de"]) == ("2027-02-01", "linea_base")
    assert (cuerpo["moneda"], cuerpo["meses_usados"], cuerpo["semilla"]) == ("USD", 24, 1)
    assert D(cuerpo["total_base"]) == D(1000)
    assert D(cuerpo["p50"]) == P80
    assert D(cuerpo["p80"]) == P80
    assert D(cuerpo["reserva"]) == RESERVA
    assert [(c["insumo"], D(c["monto"])) for c in cuerpo["contribucion"]] == [(ASFALTO, RESERVA)]
    assert cuerpo["mezclas"] == []
    assert any("gasto uniforme" in s for s in cuerpo["supuestos"])
    assert all("E" not in cuerpo[k] for k in ("total_base", "p50", "p80", "reserva"))


def test_sin_linea_base_vale_el_inicio_declarado() -> None:
    r = _en_la_via("admin").post(
        PROYECCION, json=_proyeccion(version=SIN_LINEA_BASE, inicio="2027-02-01")
    )
    assert r.status_code == 200, r.text
    assert (r.json()["inicio"], r.json()["inicio_de"]) == ("2027-02-01", "declarado")
    assert D(r.json()["p80"]) == P80


def test_sin_linea_base_ni_inicio_declarado_422() -> None:
    r = _en_la_via().post(PROYECCION, json=_proyeccion(version=SIN_LINEA_BASE))
    assert r.status_code == 422, r.text
    assert "fecha de inicio" in r.json()["detalle"]


def test_el_error_de_pocos_meses_dice_el_numero() -> None:
    """Foco de revisión 4: con el inicio en enero de 2026 solo hay 11 meses completos."""
    r = _en_la_via().post(PROYECCION, json=_proyeccion(inicio="2026-01-01"))
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == "solo hay 11 meses completos; se necesitan 12"


def test_la_comprobacion_informa_cortes_y_cobertura() -> None:
    r = _en_la_via().post(COMPROBACION, json=_comprobacion())
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["n_cortes"], cuerpo["dentro"], cuerpo["trayectorias_por_corte"]) == (7, 7, 20)
    assert D(cuerpo["cobertura"]) == 1
    assert cuerpo["cobertura_pct"] == "100.00"
    assert [c["corte"] for c in cuerpo["cortes"]] == [f"2026-0{m}-01" for m in range(2, 9)]
    for corte in cuerpo["cortes"]:
        assert D(corte["p50"]) == D(corte["p80"]) == D(corte["real"]) == P80
        assert corte["dentro"] is True


def test_la_comprobacion_trae_500_trayectorias_por_corte_por_omision() -> None:
    from api.main import app

    esquema = app.openapi()["components"]["schemas"]["ComprobacionEntrada"]
    assert esquema["properties"]["trayectorias_por_corte"]["default"] == 500


def test_insumos_de_la_version_y_series_que_admite() -> None:
    r = _en_la_via().get(INSUMOS, params={"proyecto": OBRA, "version": CON_LINEA_BASE})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["moneda"] == "USD"
    assert cuerpo["insumos"] == sorted([ASFALTO, GASOIL, SENALES])
    assert cuerpo["componentes"] == []
    assert cuerpo["mezclas"] == []
    # en un presupuesto en USD ningún insumo puede seguir a la tasa (fila 78)
    assert [s["codigo"] for s in cuerpo["series"]] == ["CEMENTO_ASFALTICO_PPI", "GASOIL_USD"]
    assert cuerpo["inicio_linea_base"] == "2027-02-01"


def test_obra_o_version_que_no_existe_404() -> None:
    web = _en_la_via()
    assert web.post(PROYECCION, json=_proyeccion(version="NO-HAY")).status_code == 404
    r = web.get(INSUMOS, params={"proyecto": "Obra que no existe", "version": "VR-001"})
    assert r.status_code == 404


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("post", PROYECCION, _proyeccion()),
        ("post", COMPROBACION, _comprobacion()),
        ("get", INSUMOS, None),
    ],
)
def test_sin_ver_riesgo_403_tambien_en_la_obra(
    monkeypatch: pytest.MonkeyPatch, metodo: str, ruta: str, cuerpo: dict | None
) -> None:
    from seguridad import permisos

    web = Web("rita")  # revisa no cambia de carpeta: la puerta de `ver_riesgo` va antes
    monkeypatch.setitem(
        permisos.PERMISOS,
        permisos.Accion.VER_RIESGO,
        frozenset({permisos.Rol.ARMA, permisos.Rol.ADMINISTRADOR}),
    )
    if metodo == "post":
        r = web.post(ruta, json=cuerpo)
    else:
        r = web.get(ruta, params={"proyecto": OBRA, "version": CON_LINEA_BASE})
    assert r.status_code == 403, r.text


@pytest.mark.parametrize(
    "cambio",
    [
        {"meses": "seis"},
        {"meses": 0},
        {"meses": 61},
        {"trayectorias": 0},
        {"trayectorias": 20001},
        {"semilla": "1"},
        {"semilla": -1},
        {"ventana_meses": 11},
        {"inicio": "31/01/2027"},
        {"mapa": ["Gasoil"]},
        {"mapa": {"Gasoil": 7}},
        {"proyecto": ""},
        {"version": None},
        {"sobra": "algo"},
    ],
)
def test_proyeccion_con_forma_mala_422(cambio: dict) -> None:
    r = _en_la_via().post(PROYECCION, json=_proyeccion(**cambio))
    assert r.status_code == 422, r.text


@pytest.mark.parametrize(
    "cambio",
    [{"trayectorias_por_corte": 0}, {"trayectorias_por_corte": 2001}, {"inicio": "2027-02-01"}],
)
def test_comprobacion_con_forma_mala_422(cambio: dict) -> None:
    r = _en_la_via().post(COMPROBACION, json=_comprobacion(**cambio))
    assert r.status_code == 422, r.text


def test_una_serie_que_no_es_de_la_proyeccion_422() -> None:
    r = _en_la_via().post(PROYECCION, json=_proyeccion(mapa={ASFALTO: "SERIE_INVENTADA"}))
    assert r.status_code == 422, r.text
    assert "SERIE_INVENTADA" in r.json()["detalle"]
