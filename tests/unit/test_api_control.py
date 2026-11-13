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
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.main import app
from aplicacion import control as logica_control
from core import models
from core.budget import elaborar, guardar_presupuesto
from core.budget.valuaciones import registrar_linea_base
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
    assert datos["descripcion"].endswith("día(s) hábil(es) por período")  # VB-5
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


def test_un_parametro_desconocido_y_el_si_con_tilde() -> None:
    # VB-5: el mensaje acentuado; el «sí» que muestra la línea base se puede mandar de vuelta.
    navegador, cabeceras = _arma()
    cuerpo = {**P, "parametros": [{"parametro": "magia", "valor": "1"}], "fuente": "x"}
    respuesta = navegador.post("/v1/control/parametros", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"] == "parámetro desconocido: 'magia'"
    valores = {
        p["parametro"]: p["valor"]
        for p in navegador.get("/v1/control/linea-base", params=P).json()["parametros"]
    }
    assert valores["fcas_en_horas_extra"] == "sí"
    cuerpo = {
        **P,
        "parametros": [{"parametro": "fcas_en_horas_extra", "valor": "no"}],
        "fuente": "x",
    }
    assert navegador.post("/v1/control/parametros", json=cuerpo, headers=cabeceras).json() == {
        "cambiados": 1
    }


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
    assert datos["filas"][0]["Periodo"] == "02/11/2026 a 06/11/2026"  # VB-19: dd/mm/aaaa
    assert datos["filas"][0]["Fecha"] == "09/11/2026"
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


def test_un_numero_de_valuacion_con_forma_de_fecha_no_se_reescribe(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ronda 1 del árbitro, punto 1: la fecha se formatea solo en su ranura; el número lo escribió
    # el usuario y sale tal cual en la tabla y en el rótulo de «Anular».
    _usar(_plantillas, "solo_linea", tmp_path, monkeypatch)
    navegador, cabeceras = _arma()
    cuerpo = {
        **P,
        "numero": "2026-11-10",
        "desde": "2026-11-02",
        "hasta": "2026-11-06",
        "fecha": "2026-11-09",
        "lineas": [{"partida": "OB-A", "cantidad": "40"}],
        "fuente": ob.FUENTE,
    }
    respuesta = navegador.post("/v1/control/valuaciones", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    datos = navegador.get("/v1/control/valuaciones", params=P).json()
    assert datos["filas"][0]["Numero"] == "2026-11-10"
    assert datos["filas"][0]["Periodo"] == "02/11/2026 a 06/11/2026"
    assert [a["rotulo"] for a in datos["anulables"]] == ["2026-11-10 (02/11/2026 a 06/11/2026)"]
    calculo = navegador.get("/v1/control/calculo", params=P).json()
    assert re.fullmatch(r"día \d+ \(\d{2}/\d{2}/\d{4}\)", calculo["terminos"]["plan_base"])


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


#: El 422 de forma del router de control (`RutaSinEco`): fijo, sin repetir lo enviado.
MENSAJE_FORMA = (
    "Los datos del control de obra no son válidos: las cantidades, los montos, las fechas y las "
    "observaciones van como texto, y la causa del retraso es una clave de la lista de causas."
)
PRIVADO = "valor-que-nunca-debe-volver"


@pytest.mark.parametrize(
    "linea",
    [
        {"partida": "OB-A", "cantidad": "40", "causa": {"clave": PRIVADO}},
        {"partida": "OB-A", "cantidad": [PRIVADO]},
        {"partida": "OB-A", "cantidad": "40", "observacion": {"texto": PRIVADO}},
    ],
)
def test_una_linea_de_valuacion_mal_formada_es_422_fijo_sin_eco(linea: dict) -> None:
    navegador, cabeceras = _arma()
    cuerpo = {
        **P,
        "numero": "V-09",
        "desde": "2026-11-16",
        "hasta": "2026-11-20",
        "lineas": [linea],
        "fuente": "x",
    }
    respuesta = navegador.post("/v1/control/valuaciones", json=cuerpo, headers=cabeceras)
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_FORMA})
    assert PRIVADO not in respuesta.text and "input" not in respuesta.text
    assert respuesta.headers.get("cache-control") == "no-store"


def test_toda_respuesta_de_control_va_sin_cache() -> None:
    navegador = _con_clave()
    for ruta in ("/v1/control/linea-base", "/v1/control/valuaciones", "/v1/control/calculo"):
        respuesta = navegador.get(ruta, params=P)
        assert respuesta.status_code == 200, ruta
        assert respuesta.headers.get("cache-control") == "no-store", ruta
    # también el 404 de una obra que no existe
    respuesta = navegador.get("/v1/control/linea-base", params={"proyecto": "NO"})
    assert respuesta.status_code == 404
    assert respuesta.headers.get("cache-control") == "no-store"


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
    # La importación pasa ahora por la guardia, como toda subida de un .xlsx (F-D10): su aviso.
    assert respuesta.json()["detalle"] == (
        "El archivo «malo.xlsx» no es un libro .xlsx válido (está dañado o no es de Excel). No se "
        "importó nada."
    )


@pytest.mark.parametrize("ruta", ["/v1/control/importar/informe", "/v1/control/importar"])
def test_un_libro_de_valuaciones_con_una_celda_lejana_es_422_sin_importar_nada(
    ruta: str, tmp_path: Path
) -> None:
    """Acta del árbitro de los topes, NOTA 7: `leer_tabla` (núcleo) recorría la hoja sin tope y
    la importación ni siquiera pasaba por la guardia. Sin `<dimension>`, A1048576 eran un millón
    de filas; ahora se rechaza con el aviso del lector."""
    from tests.fixtures.libro_apu_por_hoja import con_celdas

    limpio = ob.escribir_xlsx(tmp_path / "ob_s2.xlsx").read_bytes()
    hostil = con_celdas(limpio, "Lineas", {"A1048576": "fin ficticio"}, sin_dimension=True)
    navegador, cabeceras = _arma()
    antes = navegador.get("/v1/control/valuaciones", params=P).json()["filas"]
    respuesta = navegador.post(
        ruta,
        data={**P, "fuente": ob.FUENTE},
        files={"archivo": ("valuaciones.xlsx", hostil, "application/octet-stream")},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json()["detalle"] == (
        "El libro «valuaciones.xlsx», hoja «Lineas»: tiene filas con datos o con formato más allá "
        "de la 20.000. Sílice lee de cada hoja hasta 20.000 filas y 100 columnas (de la A a la "
        "CV). Se rechaza por seguridad: borre lo que sobra al final de la hoja y guárdelo de "
        "nuevo. No se importó nada."
    )
    assert navegador.get("/v1/control/valuaciones", params=P).json()["filas"] == antes


# --- cálculo: valor ganado, alertas y reproyección -------------------------------------------


def test_el_calculo_trae_los_indicadores_de_la_memoria() -> None:
    datos = _con_clave().get("/v1/control/calculo", params=P).json()
    assert datos["estado"] == "listo"
    assert datos["corte"] == "2026-11-13" and datos["moneda"] == "USD"
    ind = {f["Indicador"]: f for f in datos["indicadores"]}
    assert ind["BAC (USD)"]["Valor"] == "4000.00"
    assert ind["SPI"]["Valor"] == "0.8000"
    assert ind["CPI"]["Valor"] == "0.9375"
    assert ind["EAC (índice BAC/CPI) (USD)"]["Valor"] == "4266.67"


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
    respuesta = _con_clave().get("/v1/control/calculo", params={**P, "metodo": "magia"})
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"].startswith("método de precios 'magia' desconocido")


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


@pytest.mark.parametrize("clave", ["cuadrillas", "horas_extra", "aceptar"])
def test_elegir_una_opcion_crea_la_version_y_deja_la_decision_con_el_responsable_de_la_sesion(
    clave: str,
) -> None:
    """Las tres opciones que aplican al corte de la memoria de OB-S2 (cuadrillas: dia 17, horas
    extra: dia 21, aceptar el retraso: dia 23; solo `paralelo` no aplica, `test_recuperacion`).
    Antes la prueba se omitia si ninguna aplicaba; el escenario lo garantiza y aqui se exige."""
    navegador, cabeceras = _arma()
    por_clave = {o["clave"]: o for o in _opciones(navegador, cabeceras).json()["opciones"]}
    elegida = por_clave[clave]
    assert elegida["aplica"] is True, elegida["motivo"]
    assert elegida["requiere_declaracion"] is False  # las que aplican aqui no la piden
    cuerpo = {
        **P,
        "objetivo": "",
        "horas_previas": "0",
        "opcion": clave,
        "fuente": "reunion de obra",
        "declaracion_independencia": "",
    }
    respuesta = navegador.post("/v1/control/recuperacion/elegir", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    codigo = respuesta.json()["version"]
    decisiones = navegador.get("/v1/control/calculo", params=P).json()["decisiones"]
    assert [(d["Version"], "<ana>" in d["Responsable"]) for d in decisiones] == [(codigo, True)]


def test_en_el_corte_de_la_memoria_solo_paralelo_no_aplica() -> None:
    """El escenario de la fixture garantiza que hay opciones que aplican (oraculo a mano, memoria
    de OB-S2 §1 y `tests/integration/test_contexto_de_recuperacion.py`)."""
    navegador, cabeceras = _arma()
    aplica = {o["clave"]: o["aplica"] for o in _opciones(navegador, cabeceras).json()["opciones"]}
    assert aplica == {"cuadrillas": True, "horas_extra": True, "aceptar": True, "paralelo": False}


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
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"].startswith("opción 'x' desconocida")


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
    assert respuesta.json()["detalle"] == "La obra «987654» no existe en esta carpeta."


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


# --- VD-1: los supuestos de cada opción, por ranura ------------------------------------------

#: La respuesta real de las opciones de OB-S2 que usa la prueba del front (`Control.test.tsx`).
OPCIONES_DEL_FRONT = FRONT_CONTROL / "opciones_ob_s2.json"


def test_las_opciones_traen_sus_supuestos_por_ranura_y_la_nota_se_arma_con_ellos() -> None:
    # VD-1: la «Nota» llega como un solo texto con los códigos de naturaleza y los nombres del
    # núcleo; el front no puede ponerla en español sin reescribir texto que trae códigos del
    # usuario. Cada supuesto viaja en sus tres ranuras. Oráculo: los valores por omisión de
    # `ParametrosControl` (η = 0.80, 3 cuadrillas, η_he = 0.80, 2 h, recargo 0.50, penalización
    # 0) y los nombres de `core/budget/recuperacion.py`, con las tildes de `con_tildes`.
    navegador, cabeceras = _arma()
    opciones = {o["clave"]: o for o in _opciones(navegador, cabeceras).json()["opciones"]}
    comunes = [
        {"nombre": "penalización diaria", "valor": "0", "naturaleza": "DATO_DEL_CONTRATO"},
        {
            "nombre": "costo diario de la cuadrilla",
            "valor": "composiciones de la línea base",
            "naturaleza": "SUPUESTO_DECLARADO",
        },
        {
            "nombre": "costo fijo en el tiempo",
            "valor": "CF' = CF · D'/D",
            "naturaleza": "SUPUESTO_DECLARADO",
        },
    ]
    assert opciones["cuadrillas"]["supuestos"] == [
        {"nombre": "eta de cuadrillas", "valor": "0.80", "naturaleza": "SUPUESTO_DECLARADO"},
        {"nombre": "cuadrillas máximas", "valor": "3", "naturaleza": "SUPUESTO_DECLARADO"},
        *comunes,
    ]
    assert opciones["horas_extra"]["supuestos"] == [
        {"nombre": "horas extra por día", "valor": "2", "naturaleza": "SUPUESTO_DECLARADO"},
        {"nombre": "eta de horas extra", "valor": "0.80", "naturaleza": "SUPUESTO_DECLARADO"},
        {"nombre": "recargo", "valor": "0.50", "naturaleza": "FUENTE_VERIFICADA"},
        {"nombre": "FCAS sobre las horas extra", "valor": "sí", "naturaleza": "SUPUESTO_DECLARADO"},
        {"nombre": "jornada ordinaria", "valor": "8 h", "naturaleza": "FUENTE_VERIFICADA"},
        {
            "nombre": "límites de horas extra",
            "valor": "10 h por semana, 100 h por año",
            "naturaleza": "FUENTE_VERIFICADA",
        },
        *comunes,
    ]
    assert opciones["aceptar"]["supuestos"] == comunes
    # La que no aplica no lista supuestos: su nota es el motivo.
    assert opciones["paralelo"]["supuestos"] == []
    # La nota de la clásica sigue igual y sale de las mismas ranuras.
    for o in opciones.values():
        if o["aplica"]:
            assert o["fila"]["Nota"] == "; ".join(
                f"{s['nombre']}: {s['valor']} ({s['naturaleza']})" for s in o["supuestos"]
            )


def test_la_respuesta_de_opciones_del_front_es_la_de_la_api_real() -> None:
    # La prueba del front monta la tabla con este JSON: si la API cambia, este archivo se
    # regenera con la respuesta real y la prueba del front se vuelve a mirar.
    import json

    navegador, cabeceras = _arma()
    real = _opciones(navegador, cabeceras).json()
    assert json.loads(OPCIONES_DEL_FRONT.read_text(encoding="utf-8")) == real


# --- IVA sobre las valuaciones (plan vial, Tarea 18) -----------------------------------------


def test_cada_valuacion_trae_subtotal_iva_y_total_con_iva() -> None:
    # Oraculo a mano, perspectiva costo: V-01 = 40 x 10,00 = 400,00 -> IVA 64,00 -> 464,00;
    # V-02 = 50 x 10,00 + 60 x 5,00 = 800,00 -> IVA 128,00 -> 928,00.
    filas = {
        f["Numero"]: f
        for f in _con_clave().get("/v1/control/valuaciones", params=P).json()["filas"]
    }
    v1, v2 = filas["V-01"], filas["V-02"]
    assert (v1["Subtotal"], v1["IVA"], v1["Total con IVA"]) == ("400.00", "64.00", "464.00")
    assert (v2["Subtotal"], v2["IVA"], v2["Total con IVA"]) == ("800.00", "128.00", "928.00")


def test_las_valuaciones_traen_el_acumulado_con_alicuota_y_fuente() -> None:
    imp = _con_clave().get("/v1/control/valuaciones", params=P).json()["impuestos"]
    assert (imp["subtotal"], imp["iva"], imp["total"]) == ("1200.00", "192.00", "1392.00")
    assert imp["alicuota"] == "0.16"
    assert "a cotejar con la Gaceta vigente" in imp["fuente_alicuota"]


def test_sin_valuaciones_el_acumulado_con_iva_es_cero(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "solo_linea", tmp_path, monkeypatch)
    datos = _con_clave().get("/v1/control/valuaciones", params=P).json()
    imp = datos["impuestos"]
    assert (imp["subtotal"], imp["iva"], imp["total"]) == ("0.00", "0.00", "0.00")
    assert imp["alicuota"] == "0.16"


def test_las_columnas_de_iva_del_front_existen_en_la_respuesta() -> None:
    # Los nombres de columna del front son claves de la fila (VB-3).
    columnas = _columnas_del_front("COLUMNAS_VALUACIONES")
    assert {"Subtotal", "IVA", "Total con IVA"} <= set(columnas)


def test_las_valuaciones_dicen_la_perspectiva_de_la_linea_base() -> None:
    # OB-S2 declara su línea base en costo: el IVA de lo medido no es facturable (T18-3).
    assert _con_clave().get("/v1/control/valuaciones", params=P).json()["perspectiva"] == "costo"


# --- las partidas del contrato (autocompletado AC2) ------------------------------------------

TRES_PARTIDAS = [
    {"codigo": "OB-A", "descripcion": "Excavacion de zanja", "unidad": "m3"},
    {"codigo": "OB-B", "descripcion": "Tuberia de drenaje", "unidad": "m"},
    {"codigo": "OB-C", "descripcion": "Relleno compactado", "unidad": "m3"},
]


def test_las_partidas_del_contrato_son_las_de_la_version_de_la_linea_base() -> None:
    """Oráculo a mano (`control_ob_s2.py`): la línea base presupuesta A, B y C. OB-D está valuada
    en la memoria pero no presupuestada, así que NO se ofrece: en una valuación solo se mide lo
    contratado."""
    r = _con_clave().get("/v1/control/partidas", params=P)
    assert r.status_code == 200
    assert r.json() == {
        "version": "OB-001",
        "aviso": "",
        "partidas": TRES_PARTIDAS,
        "truncada": False,
    }


def test_las_partidas_del_contrato_se_ofrecen_antes_de_la_primera_valuacion(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "solo_linea", tmp_path, monkeypatch)
    r = _con_clave().get("/v1/control/partidas", params=P)
    assert [p["codigo"] for p in r.json()["partidas"]] == ["OB-A", "OB-B", "OB-C"]


def test_sin_linea_base_las_partidas_vienen_vacias_con_su_aviso_y_no_es_error(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "vacia", tmp_path, monkeypatch)
    r = _con_clave().get("/v1/control/partidas", params=P)
    assert r.status_code == 200
    assert r.json() == {
        "version": "",
        "aviso": "Esta obra todavía no tiene línea base.",
        "partidas": [],
        "truncada": False,
    }


def test_las_partidas_del_contrato_exigen_proyecto_existente_y_van_sin_cache() -> None:
    navegador = _con_clave()
    assert navegador.get("/v1/control/partidas", params={"proyecto": "NO"}).status_code == 404
    assert navegador.get("/v1/control/partidas").status_code == 422
    respuesta = navegador.get("/v1/control/partidas", params=P)
    assert respuesta.headers.get("cache-control") == "no-store"


def _segunda_linea_base(tmp_path: Path) -> None:
    """Sobre la copia de la prueba: la versión OB-002 (solo OB-A y OB-B, con su plan) y una
    segunda línea base sobre ella desde el 2026-11-20. Hasta el 19 rige la de OB-001 (desde el
    2026-11-02, A, B y C); desde el 20, la de OB-002."""
    plan = [("Semana 1", (("OB-A", Decimal(1)),)), ("Semana 2", (("OB-B", Decimal(1)),))]
    dependencias.cerrar_motores()
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            primera = sesion.scalars(
                select(models.Presupuesto).where(models.Presupuesto.codigo == ob.CODIGO)
            ).one()
            resultado = elaborar(
                ob.items()[:2],
                ob.composiciones(),
                ob.PARAMETROS,
                codigo="OB-002",
                fecha=ob.FECHA,
                moneda=ob.MONEDA,
                plan=plan,
            )
            guardar_presupuesto(
                sesion,
                resultado.presupuesto,
                resultado.informe,
                proyecto=primera.proyecto,
                lista=primera.lista_precios,
                parametros=ob.PARAMETROS,
                plan=plan,
            )
            registrar_linea_base(
                sesion,
                ob.NOMBRE,
                "OB-002",
                desde=date(2026, 11, 20),
                perspectiva="costo",
                calendario=ob.CALENDARIO,
                fuente=ob.FUENTE,
                responsable=ob.RESPONSABLE,
            )
            sesion.commit()
    finally:
        motor.dispose()


def test_las_partidas_son_las_de_la_linea_base_vigente_al_corte(tmp_path: Path) -> None:
    """R13 juzga una valuación contra la línea base vigente a su corte (su *hasta*): la lista
    que guía el campo se pide para esa fecha. Sin corte, la más reciente (lo de antes)."""
    _segunda_linea_base(tmp_path)
    navegador = _con_clave()
    al_13 = navegador.get("/v1/control/partidas", params={**P, "corte": "2026-11-13"}).json()
    assert (al_13["version"], al_13["partidas"]) == ("OB-001", TRES_PARTIDAS)
    al_20 = navegador.get("/v1/control/partidas", params={**P, "corte": "2026-11-20"}).json()
    assert (al_20["version"], al_20["partidas"]) == ("OB-002", TRES_PARTIDAS[:2])
    sin_corte = navegador.get("/v1/control/partidas", params=P).json()
    assert sin_corte["version"] == "OB-002"


def test_antes_de_la_primera_linea_base_no_hay_lista_y_se_dice() -> None:
    r = _con_clave().get("/v1/control/partidas", params={**P, "corte": "2026-10-30"})
    assert r.status_code == 200
    assert r.json() == {
        "version": "",
        "aviso": "No hay una línea base vigente a esa fecha de corte.",
        "partidas": [],
        "truncada": False,
    }


def test_un_corte_que_no_es_fecha_es_422_sin_eco() -> None:
    r = _con_clave().get("/v1/control/partidas", params={**P, "corte": "ayer<b>"})
    assert r.status_code == 422
    assert "ayer" not in r.text


def test_la_lista_recortada_lo_dice(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con el tope en 2, de las tres partidas se ofrecen dos y `truncada` lo dice: la interfaz
    no puede juzgar con una lista incompleta y deja que decida el servidor."""
    monkeypatch.setattr(logica_control, "MAXIMO_DE_PARTIDAS_DEL_CONTRATO", 2)
    cuerpo = _con_clave().get("/v1/control/partidas", params=P).json()
    assert cuerpo["partidas"] == TRES_PARTIDAS[:2]
    assert cuerpo["truncada"] is True


def test_el_404_de_las_partidas_es_fijo_y_no_repite_lo_pedido() -> None:
    r = _con_clave().get("/v1/control/partidas", params={"proyecto": "Obra<b>inventada"})
    assert r.status_code == 404
    assert r.json()["detalle"] == "La obra no existe en esta carpeta."
    assert "inventada" not in r.text
    assert r.headers.get("cache-control") == "no-store"


def test_un_fallo_de_la_base_en_las_partidas_es_503_fijo(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(*_args, **_kwargs):
        raise OperationalError("SELECT secreto FROM item_computo", {}, Exception("disco"))

    monkeypatch.setattr(logica_control, "partidas_de_la_linea_base", falla)
    r = _con_clave().get("/v1/control/partidas", params=P)
    assert r.status_code == 503
    assert r.json()["detalle"] == (
        "No se pudieron leer las partidas del contrato de la carpeta de trabajo."
    )
    assert "SELECT" not in r.text and "secreto" not in r.text
    assert r.headers.get("cache-control") == "no-store"


# --- ola 2 del 2026-11-13: los días por período salen del plan de la versión ----------------------


def test_los_dias_por_periodo_se_leen_del_plan_de_la_version() -> None:
    navegador, _ = _arma()
    respuesta = navegador.get(
        "/v1/control/dias-por-periodo", params={**P, "version": "OB-001"}
    )
    assert respuesta.status_code == 200, respuesta.text
    # OB-S2 se planificó en cuatro «Semana n»
    assert respuesta.json() == {"dias": "5", "unidad": "semana", "aviso": ""}


def test_los_dias_de_una_version_que_no_existe_son_404() -> None:
    navegador, _ = _arma()
    respuesta = navegador.get("/v1/control/dias-por-periodo", params={**P, "version": "OB-999"})
    assert respuesta.status_code == 404
    assert "OB-999" in respuesta.json()["detalle"]


def test_sin_dias_por_periodo_la_linea_base_toma_los_del_plan(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _usar(_plantillas, "vacia", tmp_path, monkeypatch)
    navegador, cabeceras = _arma()
    cuerpo = {
        **P,
        "version": "OB-001",
        "desde": "2026-11-02",
        "perspectiva": "costo",
        "inicio": "2026-11-02",
        "dias_por_periodo": "",
        "feriados": "",
        "fuente": ob.FUENTE,
    }
    respuesta = navegador.post("/v1/control/linea-base", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert "5 día(s) hábil(es) por período" in respuesta.json()["descripcion"]
    del cuerpo["dias_por_periodo"]  # sin el campo, igual: del plan (antes era 5 fijo)
    _usar(_plantillas, "vacia", tmp_path, monkeypatch)
    otra = navegador.post("/v1/control/linea-base", json=cuerpo, headers=cabeceras)
    assert otra.status_code == 200, otra.text
