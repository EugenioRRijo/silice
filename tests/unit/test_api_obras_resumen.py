"""`/v1/obras/resumen` y `/v1/obras/pendientes`: los datos de la mesa de control (MOD-4a).

Contrato (plan de módulos, MOD-4a): `GET /resumen` con `LEER_PROYECTO` (arma y revisa; el
administrador recibe 403) → `{moneda, hoy, cifras, conversiones, fuera_de_suma, obras}`, montos e
índices como texto; `GET /pendientes` con `EDITAR_HOJA` (arma) → `{grupos}`. `Cache-Control:
no-store` en toda respuesta; un fallo de la base → 503 con un mensaje fijo, sin SQL.

El router se monta en una aplicación propia (`tests/fixtures/app_de_prueba.py`) porque
`api/main.py` lo integra el orquestador; su fila de acceso la vigila
`tests/unit/test_api_acceso_por_ruta.py` cuando la gane.

Caso: la obra ficticia OB-S2 con línea base y las valuaciones V-01 y V-02, en una carpeta que
declara USD (la moneda de su lista: no hay conversión). Oráculos de la memoria
`tests/fixtures/memorias/control_ob_s2.md` (§1 y §3): EV 1 200,00, PV 1 500,00, BAC 4 000,00,
V = 5 060,00; SV −300,00 y −300 / 1 500 × 100 = −20,0 %; SPI 0,8000; avance real 1 200 / 4 000 ×
100 = 30,0 y plan 1 500 / 4 000 × 100 = 37,5. Hoy: domingo 2026-10-25.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.rutas import obras
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures.app_de_prueba import app_con
from tests.fixtures.hoja_versiones_api import registrar_tasa
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)

APLICACION = app_con(obras.router)
RESUMEN = "/v1/obras/resumen"
PENDIENTES = "/v1/obras/pendientes"
MENSAJE_BASE = "No se pudo leer la carpeta de trabajo. Intente de nuevo."
HOY = datetime(2026, 10, 25, 9, 0)


def _caso(ruta: Path, moneda: str = "USD") -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            ob.declarar_linea_base(sesion)
            ob.registrar_v01_y_v02(sesion)
            declarar_moneda_de_la_carpeta(
                sesion, moneda, responsable="Residente Ficticio", ahora=HOY
            )
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_obras_resumen")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "caso": _caso(carpeta / "caso.db"),
        "caso_bs": _caso(carpeta / "caso_bs.db", "Bs"),
    }


@pytest.fixture(autouse=True)
def _entorno(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    copiar_instalacion(_plantillas["instalacion"])
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    copia = tmp_path / "caso.db"
    copia.write_bytes(_plantillas["caso"].read_bytes())
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{copia.as_posix()}")
    monkeypatch.setattr(obras, "ahora", lambda: HOY)
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


def _usar_carpeta_en_bs(
    plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fecha_tasa: date
) -> None:
    """La carpeta declara Bs y OB-S2 sigue en USD; una tasa del BCV de 40,00 Bs/USD del
    `fecha_tasa`."""
    copia = tmp_path / "caso_bs.db"
    copia.write_bytes(plantillas["caso_bs"].read_bytes())
    registrar_tasa(copia, fecha_tasa, "40.00")
    dependencias.cerrar_motores()
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{copia.as_posix()}")


def _entrar(login: str) -> TestClient:
    return con_cuenta(APLICACION, login)[0]


def _sin_cache(respuesta) -> None:
    assert respuesta.headers.get("cache-control") == "no-store", respuesta.headers


def _numeros(valor) -> list:
    """Todos los números JSON (int o float, no bool) que haya en `valor`, en cualquier nivel."""
    if isinstance(valor, bool):
        return []
    if isinstance(valor, int | float):
        return [valor]
    if isinstance(valor, dict):
        return [n for v in valor.values() for n in _numeros(v)]
    if isinstance(valor, list):
        return [n for v in valor for n in _numeros(v)]
    return []


# --- resumen ------------------------------------------------------------------------------------


def test_resumen_de_ob_s2_en_una_carpeta_en_usd() -> None:
    respuesta = _entrar("ana").get(RESUMEN)

    assert respuesta.status_code == 200, respuesta.text
    _sin_cache(respuesta)
    cuerpo = respuesta.json()
    assert cuerpo["moneda"] == "USD"
    assert cuerpo["hoy"] == "2026-10-25"
    assert cuerpo["cifras"][0] == {
        "clave": "valor_ganado",
        "titulo": "Valor ganado",
        "actual": "1200.00",
        "meta": "1500.00",
        "delta": "-300.00",
        "delta_pct": "-20.0",
        "sentido": "rendimiento",
        "detalle": None,
    }
    # SPI 1 200 / 1 500 = 0,8000; desviación −0,2000; OB-S2 atrasada 3 días hábiles (memoria §4)
    assert cuerpo["cifras"][1] == {
        "clave": "avance",
        "titulo": "Avance contra el plan",
        "actual": "0.8000",
        "meta": "1.0000",
        "delta": "-0.2000",
        "delta_pct": None,
        "sentido": "rendimiento",
        "detalle": "1 obra atrasada; la más atrasada, OB-S2: 3 días hábiles",
    }
    assert len(cuerpo["cifras"]) == 2
    assert cuerpo["conversiones"] == []
    assert cuerpo["fuera_de_suma"] == []
    (obra,) = cuerpo["obras"]
    assert obra == {
        "codigo": obra["codigo"],
        "nombre": "OB-S2",
        "cliente": "",
        "etapa": "atrasada",
        "etapa_texto": "Atrasada",
        "version": "OB-001",
        "version_de_linea_base": True,
        "total": "5060.00",
        "moneda": "USD",
        "avance_real": "30.0",
        "avance_plan": "37.5",
        # T22: la primera partida atrasada (memoria §4: OB-A, día 11,11 contra 10: 2 días)
        "que_pasa": "OB-A atrasada 2 días: sin causa declarada",
        "siguiente": {"texto": "Ver las alertas", "pagina": "control"},
    }
    assert obra["codigo"].isdigit()
    assert _numeros(cuerpo) == []  # ningún monto ni índice viaja como número JSON


def test_ob_s2_en_usd_se_convierte_con_la_tasa_del_bcv_y_declara_su_fecha(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # corte de OB-S2: 2026-11-13; tasa del 2026-11-09 (4 días antes, dentro de los 7):
    # EV 1 200 × 40 = 48 000,00 Bs y PV 1 500 × 40 = 60 000,00 Bs
    _usar_carpeta_en_bs(_plantillas, tmp_path, monkeypatch, date(2026, 11, 9))

    cuerpo = _entrar("ana").get(RESUMEN).json()

    assert cuerpo["moneda"] == "Bs"
    assert cuerpo["conversiones"] == [
        {"obra": "OB-S2", "moneda": "USD", "tasa": "40.00", "fecha": "2026-11-13",
         "fecha_tasa": "2026-11-09"}
    ]  # fmt: skip
    assert cuerpo["fuera_de_suma"] == []
    assert (cuerpo["cifras"][0]["actual"], cuerpo["cifras"][0]["meta"]) == ("48000.00", "60000.00")
    assert cuerpo["cifras"][1]["actual"] == "0.8000"


def test_sin_tasa_de_los_ultimos_7_dias_ob_s2_queda_fuera_de_la_suma(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # tasa del 2026-11-05: 8 días antes del corte del 2026-11-13, más de 7 → no se convierte
    _usar_carpeta_en_bs(_plantillas, tmp_path, monkeypatch, date(2026, 11, 5))

    cuerpo = _entrar("ana").get(RESUMEN).json()

    assert cuerpo["moneda"] == "Bs"
    assert cuerpo["conversiones"] == []
    assert cuerpo["fuera_de_suma"] == ["OB-S2"]
    assert cuerpo["cifras"] == []


def test_resumen_de_rita_tambien() -> None:
    respuesta = _entrar("rita").get(RESUMEN)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["obras"][0]["nombre"] == "OB-S2"


def test_resumen_del_administrador_es_403() -> None:
    respuesta = _entrar("admin").get(RESUMEN)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}
    _sin_cache(respuesta)


def test_resumen_sin_sesion_es_401() -> None:
    respuesta = cliente(APLICACION).get(RESUMEN)
    assert respuesta.status_code == 401
    _sin_cache(respuesta)


def test_un_fallo_de_la_base_en_el_resumen_es_503_sin_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(*_args, **_kwargs):
        raise OperationalError("SELECT * FROM proyecto", {}, Exception("base bloqueada"))

    monkeypatch.setattr(obras, "obras_de_la_mesa", falla)
    respuesta = _entrar("ana").get(RESUMEN)
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detalle": MENSAJE_BASE}
    assert "SELECT" not in respuesta.text
    _sin_cache(respuesta)


# --- pendientes -----------------------------------------------------------------------------------


def test_pendientes_de_ana() -> None:
    respuesta = _entrar("ana").get(PENDIENTES)

    assert respuesta.status_code == 200, respuesta.text
    _sin_cache(respuesta)
    grupos = respuesta.json()["grupos"]
    assert [(g["clave"], g["titulo"]) for g in grupos] == [
        ("aprobar", "Aprobar"),
        ("compras", "Compras"),
        ("precios", "Precios"),
        ("calidad", "Calidad"),
    ]
    assert grupos[0]["items"] == []  # OB-S2 no tiene envíos a aprobación (T18)
    # Compras (T23): la tubería (OB-B) se necesita el lun 09/11 (semana 2: día hábil 6) y se pide a
    # más tardar el mié 04/11 (3 días hábiles antes); el aviso empieza el lun 02/11 (2 antes). El
    # relleno (OB-C), el 16/11 y el 11/11. Al 25/10 no hay nada que pedir todavía.
    assert grupos[1]["items"] == []
    # La lista «OB-S2 USD» es del 2026-11-02, posterior a hoy: no es vieja. Sus precios los cargó
    # el catálogo sin referencia ni origen: los ocho insumos de los tres APU (A: equipo y
    # cuadrilla; B y C: material, equipo y cuadrilla; 2 + 3 + 3) quedan sin referencia.
    precios = grupos[2]["items"]
    assert precios == [
        {
            "obra": precios[0]["obra"],
            "obra_nombre": "OB-S2",
            "texto": "8 precios sin referencia en OB-001",
            "accion": {"texto": "Ver el catálogo", "pagina": "catalogo"},
        }
    ]
    # Calidad: los hallazgos de OB-001 son tres R1 de ADVERTENCIA (cantidades a mano sin regla):
    # no son de error ni críticos, pero sí tres cantidades sin cálculo (T9); y al 2026-10-25 no hay
    # lista para armar con que compararla (la única lista, «OB-S2 USD», rige desde el 2026-11-02).
    assert grupos[3] == {
        "clave": "calidad",
        "titulo": "Calidad",
        "items": [
            {
                "obra": precios[0]["obra"],
                "obra_nombre": "OB-S2",
                "texto": "3 cantidades escritas a mano sin cálculo en OB-001",
                "accion": {"texto": "Abrir el presupuesto", "pagina": "hoja"},
            }
        ],
    }


def test_pendientes_de_compras_al_02_11(monkeypatch: pytest.MonkeyPatch) -> None:
    """La tubería (OB-B) se pide a más tardar el mié 04/11 y el aviso empieza el lun 02/11 (dos
    días hábiles antes); el relleno (OB-C), el 11/11, todavía no avisa. «Tuberia» va sin tilde
    porque así la escribe la fixture."""
    monkeypatch.setattr(obras, "ahora", lambda: datetime(2026, 11, 2, 9, 0))
    respuesta = _entrar("ana").get(PENDIENTES)
    assert respuesta.status_code == 200, respuesta.text
    (compras,) = [g for g in respuesta.json()["grupos"] if g["clave"] == "compras"]
    assert [item["texto"] for item in compras["items"]] == [
        "Pida Material de Tuberia de drenaje antes del 04/11/2026."
    ]
    assert compras["items"][0]["accion"] == {"texto": "Ver la procura", "pagina": "control"}


def test_pendientes_de_rita_es_403() -> None:
    respuesta = _entrar("rita").get(PENDIENTES)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}
    _sin_cache(respuesta)


def test_un_fallo_de_la_base_en_los_pendientes_es_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(*_args, **_kwargs):
        raise OperationalError("SELECT * FROM hallazgo", {}, Exception("base bloqueada"))

    monkeypatch.setattr(obras, "pendientes", falla)
    respuesta = _entrar("ana").get(PENDIENTES)
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detalle": MENSAJE_BASE}
    assert "SELECT" not in respuesta.text
