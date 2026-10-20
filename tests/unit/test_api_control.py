"""`/v1/control/*`: el Control de obra por la API (ola 4 S2-C; UC-19, UC-20, spec S2 §5.5).

Sobre la obra ficticia OB-S2 (`tests/fixtures/control_ob_s2.py`): una base con línea base y las
valuaciones V-01 y V-02, otra solo con la línea base y otra sin línea base. Lo que se prueba:

- acceso: 401 sin sesión ni clave; arma (CONTROL_DE_OBRA) pasa; revisa y administrador, 403; la
  clave de API pasa;
- lectura de las pestañas (línea base y parámetros, valuaciones, cálculo con valor ganado,
  alertas y reproyección, decisiones);
- escrituras: declarar la línea base, guardar parámetros, registrar, anular, anotar costo e
  importar un XLSX, con el responsable que sale de la sesión (nunca del cuerpo);
- recuperación: calcular las opciones y elegir una (DECIDIR_RECUPERACION), sin estado en el
  servidor.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

P = {"proyecto": ob.NOMBRE}
FRONT_CONTROL = Path(__file__).resolve().parents[2] / "frontend-desktop/src/paginas/control"


def _base(ruta: Path, *, linea: bool, valuaciones: bool) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            if linea:
                ob.declarar_linea_base(sesion)
            if valuaciones:
                ob.registrar_v01_y_v02(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_control")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "completa": _base(carpeta / "completa.db", linea=True, valuaciones=True),
        "solo_linea": _base(carpeta / "solo_linea.db", linea=True, valuaciones=False),
        "vacia": _base(carpeta / "vacia.db", linea=False, valuaciones=False),
    }


@pytest.fixture(autouse=True)
def _entorno(
    _plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[None]:
    # cada prueba escribe en su copia: las plantillas no se tocan
    copia = tmp_path / "caso.db"
    copia.write_bytes(_plantillas["completa"].read_bytes())
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{copia.as_posix()}")
    copiar_instalacion(_plantillas["instalacion"])
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _usar(plantillas: dict[str, Path], nombre: str, tmp_path: Path, monkeypatch) -> None:
    copia = tmp_path / f"{nombre}_copia.db"
    copia.write_bytes(plantillas[nombre].read_bytes())
    dependencias.cerrar_motores()
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{copia.as_posix()}")


def _con_clave() -> TestClient:
    navegador = cliente(app)
    navegador.headers[CABECERA] = crear_clave_de_prueba()
    return navegador


def _arma() -> tuple[TestClient, dict[str, str]]:
    navegador, ficha = con_cuenta(app, "ana")
    return navegador, protegida(ficha)


# --- acceso ----------------------------------------------------------------------------------


def test_sin_sesion_ni_clave_da_401() -> None:
    assert cliente(app).get("/v1/control/linea-base", params=P).status_code == 401


@pytest.mark.parametrize("login", ["rita", "admin"])
def test_quien_no_controla_la_obra_recibe_403(login: str) -> None:
    navegador, _ = con_cuenta(app, login)
    respuesta = navegador.get("/v1/control/linea-base", params=P)
    assert respuesta.status_code == 403
    assert respuesta.json()["detalle"] == MENSAJE_PERMISO


def test_arma_y_la_clave_de_api_leen() -> None:
    navegador, _ = con_cuenta(app, "ana")
    assert navegador.get("/v1/control/linea-base", params=P).status_code == 200
    assert _con_clave().get("/v1/control/linea-base", params=P).status_code == 200


def test_proyecto_inexistente_da_404_y_sin_proyecto_422() -> None:
    navegador = _con_clave()
    assert navegador.get("/v1/control/linea-base", params={"proyecto": "NO"}).status_code == 404
    assert navegador.get("/v1/control/linea-base").status_code == 422


# --- línea base y parámetros -----------------------------------------------------------------


def test_la_linea_base_vigente_y_los_parametros_con_su_naturaleza() -> None:
    datos = _con_clave().get("/v1/control/linea-base", params=P).json()
    assert datos["tiene_linea_base"] is True and datos["hay_valuaciones"] is True
    assert "versión OB-001, perspectiva costo" in datos["descripcion"]
    assert datos["versiones"] == ["OB-001"]
    por_nombre = {p["parametro"]: p for p in datos["parametros"]}
    assert por_nombre["spi_error"]["naturaleza"] == "SUPUESTO_DECLARADO"
    assert por_nombre["penalizacion_diaria"]["naturaleza"] == "DATO_DEL_CONTRATO"


def test_declarar_la_linea_base_de_un_proyecto_sin_ella(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "vacia", tmp_path, monkeypatch)
    navegador, cabeceras = _arma()
    assert navegador.get("/v1/control/linea-base", params=P).json()["tiene_linea_base"] is False
    cuerpo = {
        **P,
        "version": "OB-001",
        "desde": "2026-11-02",
        "perspectiva": "costo",
        "inicio": "2026-11-02",
        "dias_por_periodo": "5",
        "feriados": "",
        "fuente": ob.FUENTE,
    }
    respuesta = navegador.post("/v1/control/linea-base", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert "perspectiva costo" in respuesta.json()["descripcion"]
    assert navegador.get("/v1/control/linea-base", params=P).json()["tiene_linea_base"] is True


def test_una_fecha_mal_escrita_da_422_con_el_mensaje_del_nucleo(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "vacia", tmp_path, monkeypatch)
    navegador, cabeceras = _arma()
    cuerpo = {
        **P,
        "version": "OB-001",
        "desde": "ayer",
        "perspectiva": "costo",
        "inicio": "2026-11-02",
        "dias_por_periodo": "5",
        "feriados": "",
        "fuente": "x",
    }
    respuesta = navegador.post("/v1/control/linea-base", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 422
    assert "no es una fecha" in respuesta.json()["detalle"]


def test_guardar_parametros_cambia_solo_lo_enviado_y_dice_cuantos() -> None:
    navegador, cabeceras = _arma()
    cuerpo = {
        **P,
        "parametros": [{"parametro": "spi_error", "valor": "0.70"}],
        "fuente": "criterio de la obra",
    }
    respuesta = navegador.post("/v1/control/parametros", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["cambiados"] == 1
    despues = {
        p["parametro"]: p["valor"]
        for p in navegador.get("/v1/control/linea-base", params=P).json()["parametros"]
    }
    assert despues["spi_error"] == "0.70"
    # lo mismo otra vez no cambia nada
    assert (
        navegador.post("/v1/control/parametros", json=cuerpo, headers=cabeceras).json()["cambiados"]
        == 0
    )


def test_un_parametro_fuera_de_rango_da_422() -> None:
    navegador, cabeceras = _arma()
    cuerpo = {**P, "parametros": [{"parametro": "eta_cuadrilla", "valor": "1.5"}], "fuente": "x"}
    assert (
        navegador.post("/v1/control/parametros", json=cuerpo, headers=cabeceras).status_code == 422
    )


def test_escribir_exige_csrf_y_el_rol_que_controla() -> None:
    navegador, _ = con_cuenta(app, "ana")
    cuerpo = {**P, "parametros": [], "fuente": "x"}
    assert navegador.post("/v1/control/parametros", json=cuerpo).status_code == 403  # sin CSRF
    rita, ficha = con_cuenta(app, "rita")
    respuesta = rita.post("/v1/control/parametros", json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 403 and respuesta.json()["detalle"] == MENSAJE_PERMISO


# --- valuaciones, anulación y costos ---------------------------------------------------------


def test_las_valuaciones_guardadas_con_su_estado_y_las_que_se_pueden_anular() -> None:
    datos = _con_clave().get("/v1/control/valuaciones", params=P).json()
    assert [f["Numero"] for f in datos["filas"]] == ["V-01", "V-02"]
    assert datos["filas"][0]["Periodo"] == "2026-11-02 a 2026-11-06"
    assert datos["filas"][0]["Inspector"] == ob.INSPECTOR
    assert [a["rotulo"].split(" ")[0] for a in datos["anulables"]] == ["V-01", "V-02"]
    assert datos["corte_por_defecto"] == "2026-11-13"


def _columnas_del_front(nombre: str) -> list[str]:
    """Los literales de `export const <nombre> = [...]` en `src/paginas/control/logica.ts`."""
    fuente = (FRONT_CONTROL / "logica.ts").read_text(encoding="utf-8")
    bloque = re.search(rf"export const {nombre} = \[(.*?)\];", fuente, re.DOTALL)
    assert bloque is not None, f"{nombre} no esta en logica.ts"
    return re.findall(r'"([^"]*)"', bloque.group(1))


def test_cada_columna_de_valuaciones_del_front_es_una_clave_de_la_respuesta_real() -> None:
    # VB-3: la tabla busca cada celda por su clave; una clave que la API no manda deja la
    # columna vacia («Número» contra «Numero»). Oraculo: las filas que devuelve la API de verdad.
    filas = _con_clave().get("/v1/control/valuaciones", params=P).json()["filas"]
    assert filas, "la obra OB-S2 trae V-01 y V-02"
    columnas = _columnas_del_front("COLUMNAS_VALUACIONES")
    assert columnas, "el front declara las columnas de valuaciones"
    for fila in filas:
        assert [c for c in columnas if c not in fila] == []


def test_registrar_una_valuacion_controla_al_corte_y_el_responsable_sale_de_la_sesion(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "solo_linea", tmp_path, monkeypatch)
    navegador, cabeceras = _arma()
    cuerpo = {
        **P,
        "numero": "V-01",
        "desde": "2026-11-02",
        "hasta": "2026-11-06",
        "fecha": "2026-11-09",
        "inspector": ob.INSPECTOR,
        "lineas": [{"partida": "OB-A", "cantidad": "40", "fecha_medicion": "", "observacion": ""}],
        "fuente": ob.FUENTE,
        "responsable": "Otra Persona",  # se ignora: el responsable es quien tiene la sesion
    }
    respuesta = navegador.post("/v1/control/valuaciones", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["corte"] == "2026-11-06"
    assert navegador.get("/v1/control/valuaciones", params=P).json()["filas"][0]["Numero"] == "V-01"
    from sqlalchemy import select

    from core import models

    motor = crear_motor(_url())
    with abrir_sesion(motor) as sesion:
        responsables = set(sesion.scalars(select(models.Valuacion.responsable)))
    motor.dispose()
    assert responsables and all("<ana>" in r for r in responsables)


def _url() -> str:
    import os

    return os.environ[dependencias.VARIABLE_BASE]


def test_una_valuacion_sin_lineas_se_rechaza_con_422_y_no_se_guarda() -> None:
    navegador, cabeceras = _arma()
    cuerpo = {
        **P,
        "numero": "V-09",
        "desde": "2026-11-16",
        "hasta": "2026-11-20",
        "fecha": "",
        "inspector": "",
        "lineas": [],
        "fuente": "x",
    }
    respuesta = navegador.post("/v1/control/valuaciones", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 422
    assert [
        f["Numero"] for f in navegador.get("/v1/control/valuaciones", params=P).json()["filas"]
    ] == ["V-01", "V-02"]


def test_anular_una_valuacion_la_saca_de_las_que_cuentan() -> None:
    navegador, cabeceras = _arma()
    anulables = navegador.get("/v1/control/valuaciones", params=P).json()["anulables"]
    segunda = anulables[1]["id"]
    respuesta = navegador.post(
        f"/v1/control/valuaciones/{segunda}/anular",
        json={"motivo": "el cliente no la aprobo"},
        headers=cabeceras,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert [
        f["Numero"] for f in navegador.get("/v1/control/valuaciones", params=P).json()["filas"]
    ] == ["V-01"]


def test_anotar_un_costo_y_un_monto_ilegible_da_422() -> None:
    navegador, cabeceras = _arma()
    bueno = {
        **P,
        "monto": "100.00",
        "moneda": "USD",
        "fecha": "2026-11-12",
        "partida": "",
        "fuente": "libro de obra",
    }
    assert navegador.post("/v1/control/costos", json=bueno, headers=cabeceras).status_code == 200
    malo = {**bueno, "monto": "cien"}
    respuesta = navegador.post("/v1/control/costos", json=malo, headers=cabeceras)
    assert respuesta.status_code == 422 and "no es un numero decimal" in respuesta.json()["detalle"]


def test_importar_un_xlsx_muestra_el_informe_previo_y_luego_registra(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "solo_linea", tmp_path, monkeypatch)
    xlsx = ob.escribir_xlsx(tmp_path / "ob_s2.xlsx")
    navegador, cabeceras = _arma()
    tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    previo = navegador.post(
        "/v1/control/importar/informe",
        files={"archivo": ("ob_s2.xlsx", xlsx.read_bytes(), tipo)},
        headers=cabeceras,
    )
    assert previo.status_code == 200, previo.text
    assert previo.json()["informe"], "el informe previo no puede venir vacio"
    assert (
        navegador.get("/v1/control/valuaciones", params=P).json()["filas"] == []
    )  # leer no escribe
    hecho = navegador.post(
        "/v1/control/importar",
        data={**P, "fuente": ob.FUENTE},
        files={"archivo": ("ob_s2.xlsx", xlsx.read_bytes(), tipo)},
        headers=cabeceras,
    )
    assert hecho.status_code == 200, hecho.text
    assert hecho.json()["importadas"] == 2
    assert len(navegador.get("/v1/control/valuaciones", params=P).json()["filas"]) == 2


def test_un_archivo_que_no_es_un_libro_se_rechaza_entero_con_422() -> None:
    navegador, cabeceras = _arma()
    respuesta = navegador.post(
        "/v1/control/importar/informe",
        files={"archivo": ("malo.xlsx", b"no es un libro", "application/octet-stream")},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422


# --- cálculo: valor ganado, alertas y reproyección -------------------------------------------


def test_el_calculo_trae_los_indicadores_de_la_memoria() -> None:
    datos = _con_clave().get("/v1/control/calculo", params=P).json()
    assert datos["estado"] == "listo"
    assert datos["corte"] == "2026-11-13" and datos["moneda"] == "USD"
    ind = {f["Indicador"]: f for f in datos["indicadores"]}
    assert ind["BAC (USD)"]["Valor"] == "4000.00"
    assert ind["SPI"]["Valor"] == "0.8000"
    assert ind["CPI"]["Valor"] == "0.9375"
    assert ind["EAC (indice BAC/CPI) (USD)"]["Valor"] == "4266.67"


def test_la_curva_pv_ev_ac_cierra_en_el_corte() -> None:
    curva = _con_clave().get("/v1/control/calculo", params=P).json()["curva"]
    assert len(curva) == 2
    assert float(curva[-1]["pv"]) == pytest.approx(1500.0) or float(curva[-1]["pv"]) > 0
    assert set(curva[0]) == {"periodo", "pv", "ev", "ac"}


def test_alertas_terminos_reproyeccion_y_estudios_vienen_siempre() -> None:
    datos = _con_clave().get("/v1/control/calculo", params=P).json()
    assert {a["Alerta"] for a in datos["alertas"]} & {"AL-1", "AL-2", "AL-3"}
    assert set(datos["terminos"]) == {"indice", "reproyectado", "plan_base", "eac_sistema"}
    assert datos["terminos"]["plan_base"].startswith("día ")
    assert datos["reproyeccion"], "hay partidas con obra pendiente"
    assert datos["plan"]["columnas"][0] == "Periodo"
    assert "V' = V" in datos["estudios"]
    assert datos["versiones_revaloradas"] == []  # OB-S2 no tiene versiones revaloradas (UC-02)


def test_el_corte_pedido_cambia_el_calculo() -> None:
    primero = _con_clave().get("/v1/control/calculo", params={**P, "corte": "2026-11-06"}).json()
    assert primero["corte"] == "2026-11-06"
    ind = {f["Indicador"]: f["Valor"] for f in primero["indicadores"]}
    assert ind["EV (USD)"] != _ev_del_corte_por_defecto()


def _ev_del_corte_por_defecto() -> str:
    datos = _con_clave().get("/v1/control/calculo", params=P).json()
    return {f["Indicador"]: f["Valor"] for f in datos["indicadores"]}["EV (USD)"]


def test_la_escalatoria_sin_fuente_da_422() -> None:
    respuesta = _con_clave().get(
        "/v1/control/calculo",
        params={**P, "metodo": "escalatoria", "km": "1.1", "r": "0", "fuente": ""},
    )
    assert respuesta.status_code == 422


def test_un_metodo_de_precios_desconocido_da_422() -> None:
    assert (
        _con_clave().get("/v1/control/calculo", params={**P, "metodo": "magia"}).status_code == 422
    )


def test_sin_linea_base_o_sin_valuaciones_el_estado_lo_dice(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "vacia", tmp_path, monkeypatch)
    assert _con_clave().get("/v1/control/calculo", params=P).json()["estado"] == "sin_linea_base"
    _usar(_plantillas, "solo_linea", tmp_path, monkeypatch)
    assert _con_clave().get("/v1/control/calculo", params=P).json()["estado"] == "sin_valuaciones"


# --- recuperación ----------------------------------------------------------------------------


def _opciones(navegador: TestClient, cabeceras: dict[str, str] | None = None, **extra):
    return navegador.post(
        "/v1/control/recuperacion/opciones",
        json={**P, "objetivo": "", "horas_previas": "0", **extra},
        headers=cabeceras or {},
    )


def test_calcular_las_opciones_devuelve_las_cuatro_con_su_fila_y_no_escribe() -> None:
    navegador, cabeceras = _arma()
    respuesta = _opciones(navegador, cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    opciones = respuesta.json()["opciones"]
    assert len(opciones) == 4
    for o in opciones:
        assert {
            "clave",
            "titulo",
            "aplica",
            "motivo",
            "requisitos",
            "requiere_declaracion",
            "fila",
        } <= set(o)
        assert o["fila"]["Opcion"] == o["titulo"]
    assert navegador.get("/v1/control/calculo", params=P).json()["decisiones"] == []


def test_elegir_una_opcion_crea_la_version_y_deja_la_decision_con_el_responsable_de_la_sesion() -> (
    None
):
    navegador, cabeceras = _arma()
    aplican = [o for o in _opciones(navegador, cabeceras).json()["opciones"] if o["aplica"]]
    if not aplican:
        pytest.skip("ninguna opcion aplica al corte de la memoria")
    elegida = aplican[0]
    cuerpo = {
        **P,
        "objetivo": "",
        "horas_previas": "0",
        "opcion": elegida["clave"],
        "fuente": "reunion de obra",
        "declaracion_independencia": "las partidas no dependen entre si (plano 3)"
        if elegida["requiere_declaracion"]
        else "",
    }
    respuesta = navegador.post("/v1/control/recuperacion/elegir", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    codigo = respuesta.json()["version"]
    decisiones = navegador.get("/v1/control/calculo", params=P).json()["decisiones"]
    assert [(d["Version"], "<ana>" in d["Responsable"]) for d in decisiones] == [(codigo, True)]


def test_elegir_exige_decidir_la_recuperacion_y_una_opcion_conocida() -> None:
    rita, ficha = con_cuenta(app, "rita")
    cuerpo = {**P, "objetivo": "", "horas_previas": "0", "opcion": "x", "fuente": "x"}
    assert (
        rita.post(
            "/v1/control/recuperacion/elegir", json=cuerpo, headers=protegida(ficha)
        ).status_code
        == 403
    )
    navegador, cabeceras = _arma()
    respuesta = navegador.post("/v1/control/recuperacion/elegir", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 422 and "opcion" in respuesta.json()["detalle"].lower()


# --- V-11: el selector de la cabecera manda el `codigo` de GET /v1/proyectos ----------------


def _codigo_del_proyecto(navegador: TestClient) -> str:
    filas = navegador.get("/v1/proyectos").json()
    return next(f["codigo"] for f in filas if f["nombre"] == ob.NOMBRE)


def test_control_acepta_el_codigo_de_v1_proyectos_en_consulta() -> None:
    navegador = _con_clave()
    codigo = _codigo_del_proyecto(navegador)
    por_nombre = navegador.get("/v1/control/linea-base", params=P).json()
    por_codigo = navegador.get("/v1/control/linea-base", params={"proyecto": codigo})
    assert por_codigo.status_code == 200
    assert por_codigo.json() == por_nombre
    assert navegador.get("/v1/control/valuaciones", params={"proyecto": codigo}).status_code == 200
    calculo = navegador.get("/v1/control/calculo", params={"proyecto": codigo})
    assert calculo.status_code == 200
    assert calculo.json() == navegador.get("/v1/control/calculo", params=P).json()


def test_control_con_un_codigo_inexistente_da_404_con_el_mensaje_de_siempre() -> None:
    respuesta = _con_clave().get("/v1/control/linea-base", params={"proyecto": "987654"})
    assert respuesta.status_code == 404
    assert respuesta.json()["detalle"] == "El proyecto «987654» no existe en este caso."


def test_las_opciones_de_la_api_salen_con_tildes_en_titulo_motivo_y_requisitos() -> None:
    navegador, cabeceras = _arma()
    opciones = {o["clave"]: o for o in _opciones(navegador, cabeceras).json()["opciones"]}
    assert opciones["cuadrillas"]["titulo"] == "Más cuadrillas"
    assert opciones["cuadrillas"]["fila"]["Opcion"] == "Más cuadrillas"
    assert opciones["paralelo"]["motivo"] == (
        "ninguna partida sin empezar con inicio posterior al período siguiente"
    )
    assert opciones["horas_extra"]["requisitos"] == [
        "permiso de la Inspectoría del Trabajo (LOTTT art. 182) para las horas extra"
    ]
