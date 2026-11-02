"""`GET /v1/tablero` (sesion 2b, ola 4): el tablero del proyecto para la interfaz nueva.

Contrato (el que lee `frontend-desktop/src/paginas/tablero/`): `?proyecto=<nombre>`, acceso
`LEER_PROYECTO` por clave de API o por sesion (arma y revisa; el administrador no). Los montos y
porcentajes que se leen viajan como texto ya presentado; `valor` es el numero exacto en texto, solo
para dibujar. Sin version vigente responde 200 con `version` nulo (la pantalla dice como armarla);
un proyecto que no existe, 404.

Oraculo: la obra ficticia OB-S2 (memoria a mano `tests/fixtures/memorias/control_ob_s2.md`), la
misma de `test_ui_tablero.py`: costo directo 4 000,00, administracion 600,00, utilidad 460,00, total
5 060,00 (materiales 1 800, equipos 210, mano de obra 1 990); al corte con V-01 y V-02, PV 1 500,
EV 1 200, AC 1 280, SPI 0,80, CPI 0,94 (0,9375) y EAC por indice 4 266,67; avance EV/BAC = 30,0 %.
Los valores esperados estan escritos a mano; ninguno sale del codigo bajo prueba. Datos ficticios.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)

SIN_LINEA_BASE = "Sin línea base de control: declárela en Control de obra."


def _base(ruta: Path, *, con_control: bool, con_version: bool = True) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            if con_version:
                ob.sembrar(sesion)
                if con_control:
                    ob.declarar_linea_base(sesion)
                    ob.registrar_v01_y_v02(sesion)
            else:
                from core.budget import crear_proyecto

                crear_proyecto(sesion, "Sin version")
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_tablero")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "con_control": _base(carpeta / "con_control.db", con_control=True),
        "sin_control": _base(carpeta / "sin_control.db", con_control=False),
        "sin_version": _base(carpeta / "sin_version.db", con_control=False, con_version=False),
    }


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv(
        dependencias.VARIABLE_BASE, f"sqlite:///{_plantillas['con_control'].as_posix()}"
    )
    copiar_instalacion(_plantillas["instalacion"])
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _con_clave() -> TestClient:
    navegador = cliente(app)
    navegador.headers[CABECERA] = crear_clave_de_prueba()
    return navegador


def _tablero(navegador: TestClient, proyecto: str = ob.NOMBRE):
    return navegador.get("/v1/tablero", params={"proyecto": proyecto})


def _usar(plantillas: dict[str, Path], nombre: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{plantillas[nombre].as_posix()}")


# --- acceso ----------------------------------------------------------------------------------


def test_sin_sesion_ni_clave_da_401() -> None:
    assert _tablero(cliente(app)).status_code == 401


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_arma_y_revisa_leen_el_tablero(login: str) -> None:
    navegador, _ = con_cuenta(app, login)
    assert _tablero(navegador).status_code == 200


def test_el_administrador_no_lee_proyectos() -> None:
    navegador, _ = con_cuenta(app, "admin")
    respuesta = _tablero(navegador)
    assert respuesta.status_code == 403
    assert respuesta.json()["detalle"] == MENSAJE_PERMISO


def test_con_clave_de_api_lee_el_tablero() -> None:
    assert _tablero(_con_clave()).status_code == 200


def test_sin_proyecto_da_422_y_uno_inexistente_404() -> None:
    navegador = _con_clave()
    assert navegador.get("/v1/tablero").status_code == 422
    respuesta = _tablero(navegador, "No existe")
    assert respuesta.status_code == 404
    assert "No existe" in respuesta.json()["detalle"]


# --- el contenido con control de obra --------------------------------------------------------


def test_el_encabezado_y_las_tarjetas_del_presupuesto() -> None:
    datos = _tablero(_con_clave()).json()
    assert (datos["proyecto"], datos["version"], datos["fecha"]) == (
        "OB-S2",
        "OB-001",
        "2026-11-02",
    )
    assert (datos["moneda"], datos["renglones"]) == ("USD", 3)
    tarjetas = {t["rotulo"]: t for t in datos["tarjetas"]}
    assert list(tarjetas) == [
        "Total del contrato",
        "Costo directo",
        "Punto de equilibrio",
        "Auditoría",
    ]
    assert tarjetas["Total del contrato"]["valor"] == "5060.00 USD"
    assert tarjetas["Costo directo"]["valor"] == "4000.00 USD"
    assert tarjetas["Punto de equilibrio"]["valor"] == "56.60 %"
    # VB-21: el exacto del total y del costo directo viaja aparte, para el title (5 060 y 4 000)
    assert Decimal(tarjetas["Total del contrato"]["exacto"]) == Decimal("5060")
    assert Decimal(tarjetas["Costo directo"]["exacto"]) == Decimal("4000")
    assert tarjetas["Punto de equilibrio"]["exacto"] == ""
    # VB-16: veredicto con mayúscula inicial y la cuenta de hallazgos en plural
    assert (tarjetas["Auditoría"]["valor"], tarjetas["Auditoría"]["detalle"]) == (
        "Cumple",
        "3 advertencias",
    )


def test_el_control_trae_los_tres_anillos_y_las_tarjetas_del_corte() -> None:
    control = _tablero(_con_clave()).json()["control"]
    assert control["disponible"] is True and control["motivo"] == ""
    anillos = {a["rotulo"]: a for a in control["anillos"]}
    assert list(anillos) == ["Avance fisico", "SPI (plazo)", "CPI (costo)"]
    assert (anillos["Avance fisico"]["texto"], anillos["Avance fisico"]["favorable"]) == (
        "30.0 %",
        None,
    )
    assert float(anillos["Avance fisico"]["fraccion"]) == pytest.approx(0.3)
    assert (anillos["SPI (plazo)"]["texto"], anillos["SPI (plazo)"]["favorable"]) == ("0.80", False)
    assert (anillos["CPI (costo)"]["texto"], anillos["CPI (costo)"]["favorable"]) == ("0.94", False)
    assert float(anillos["CPI (costo)"]["fraccion"]) == pytest.approx(0.9375)
    tarjetas = {t["rotulo"]: t["valor"] for t in control["tarjetas"]}
    assert tarjetas["Avance físico (EV/BAC)"] == "30.0 %"
    assert tarjetas["EAC (costo final estimado)"] == "4266.67 USD"


def test_la_curva_trae_pv_ev_y_ac_por_periodo() -> None:
    curvas = _tablero(_con_clave()).json()["curvas"]
    assert curvas["titulo"] == "Valor ganado (PV, EV, AC)"
    esperadas = {"PV": [500.0, 1500.0], "EV": [400.0, 1200.0], "AC": [0.0, 1280.0]}
    assert [s["serie"] for s in curvas["series"]] == ["PV", "EV", "AC"]
    for serie in curvas["series"]:
        assert [p["orden"] for p in serie["puntos"]] == [1, 2]
        assert [float(p["valor"]) for p in serie["puntos"]] == pytest.approx(
            esperadas[serie["serie"]], abs=0.005
        )
        assert all(isinstance(p["valor"], str) for p in serie["puntos"])  # exactos, en texto


def test_el_desglose_suma_el_total_del_contrato() -> None:
    desglose = _tablero(_con_clave()).json()["desglose"]
    montos = {f["rubro"]: f["monto"] for f in desglose}
    assert montos == {
        "Materiales": "1800.00 USD",
        "Equipos": "210.00 USD",
        "Mano de obra": "1990.00 USD",
        "Administración": "600.00 USD",
        "Utilidad": "460.00 USD",
    }
    assert sum(float(f["valor"]) for f in desglose) == pytest.approx(5060.0, abs=0.005)
    assert {f["rubro"]: f["peso"] for f in desglose}["Materiales"] == "35.6 %"


def test_el_pareto_ordena_por_total_con_peso_y_acumulado() -> None:
    pareto = _tablero(_con_clave()).json()["pareto"]
    assert sorted(f["partida"] for f in pareto) == ["OB-A", "OB-B", "OB-C"]
    acumulados = [f["acumulado"] for f in pareto]
    assert acumulados[-1] == "100.0 %"
    assert all(set(f) >= {"partida", "descripcion", "total", "peso", "acumulado", "valor"}
               for f in pareto)  # fmt: skip
    totales = [float(f["valor"]) for f in pareto]
    assert totales == sorted(totales, reverse=True)


def test_el_comparativo_marca_la_version_vigente() -> None:
    versiones = _tablero(_con_clave()).json()["versiones"]
    assert len(versiones) == 1
    fila = versiones[0]
    assert (fila["version"], fila["fecha"], fila["motivo"]) == ("OB-001", "2026-11-02", "elaborada")
    assert (fila["costo_directo"], fila["total"]) == ("4000.00 USD", "5060.00 USD")
    assert fila["vigente"] is True
    assert float(fila["valor"]) == pytest.approx(5060.0, abs=0.005)


# --- sin control, sin version ----------------------------------------------------------------


def test_sin_linea_base_el_control_no_esta_y_la_curva_es_el_plan(
    _plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "sin_control", monkeypatch)
    datos = _tablero(_con_clave()).json()
    assert datos["control"]["disponible"] is False
    assert datos["control"]["motivo"] == SIN_LINEA_BASE
    assert datos["control"]["anillos"] == [] and datos["control"]["tarjetas"] == []
    assert datos["curvas"]["titulo"] == "Plan acumulado"
    assert [s["serie"] for s in datos["curvas"]["series"]] == ["Plan"]


def test_un_proyecto_sin_version_responde_con_version_nula(
    _plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "sin_version", monkeypatch)
    respuesta = _tablero(_con_clave(), "Sin version")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["proyecto"] == "Sin version" and datos["version"] is None
    assert datos["tarjetas"] == [] and datos["versiones"] == []


def test_el_tablero_no_escribe_en_el_caso(_plantillas: dict[str, Path]) -> None:
    antes = _plantillas["con_control"].read_bytes()
    assert _tablero(_con_clave()).status_code == 200
    dependencias.cerrar_motores()
    assert config.ruta_instalacion().exists()
    assert _plantillas["con_control"].read_bytes() == antes


# --- V-11: el selector de la cabecera manda el `codigo` de GET /v1/proyectos ----------------


def _codigo_del_proyecto(navegador: TestClient) -> str:
    filas = navegador.get("/v1/proyectos").json()
    return next(f["codigo"] for f in filas if f["nombre"] == ob.NOMBRE)


def test_el_tablero_acepta_el_codigo_que_da_v1_proyectos_igual_que_el_nombre() -> None:
    navegador = _con_clave()
    por_codigo = _tablero(navegador, _codigo_del_proyecto(navegador))
    por_nombre = _tablero(navegador)
    assert por_codigo.status_code == 200
    assert por_codigo.json() == por_nombre.json()
    assert por_codigo.json()["proyecto"] == ob.NOMBRE  # el nombre, no el codigo


def test_un_codigo_que_no_existe_da_404_con_el_mensaje_de_siempre() -> None:
    respuesta = _tablero(_con_clave(), "987654")
    assert respuesta.status_code == 404
    assert respuesta.json()["detalle"] == "El proyecto «987654» no existe en este caso."
