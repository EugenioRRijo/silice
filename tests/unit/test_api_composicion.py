"""`/v1/composicion/*`: «Componer una partida» por HTTP (ola 3, S2-B; plan §2, RB-2 a RB-5).

Contrato del plan (`docs/planes/PLAN_MIGRACION_OLA_3_B_COMPONER.md` §2): seis rutas, todas con
`EDITAR_HOJA` (arma), montos y decimales como texto. `evaluar` nunca responde 4xx por una tabla a
medias (`estado: "incompleto"`); `guardar` responde 422 sin escribir si faltan las condiciones
(RF-33), la composicion es invalida o la cabecera de una partida existente no coincide, y 409 sin
lista de precios vigente.

El caso es una base temporal en `tmp_path` (nunca `data/`), preparada con `preparar_base` y
sembrada con la linea base (`scripts.seed.sembrar`), que la API abre por `APU_BASE`. Oraculos: el
precio unitario de la tuberia es el del PDF de la linea base (10,19); su subtotal de materiales se
suma a mano en `tests/unit/test_aplicacion_composicion.py` (7,19); los mensajes son los literales
de la pagina clasica, copiados a mano.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from core.catalog import abrir_sesion, crear_motor, registrar_rendimiento
from core.contracts import TipoRendimiento
from operacion.base_datos import preparar_base
from scripts.seed import sembrar
from tests.fixtures.apu_linea_base import APU_TUBERIA, FECHA_LINEA_BASE
from tests.fixtures.claves_api import cliente_de_prueba
from tests.fixtures.filas_composicion import filas_equipos, filas_mano_obra, filas_materiales
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

TUBERIA = APU_TUBERIA.codigo_partida
NUEVA = "PRUEBA-01-NUEVA"
CONDICIONES = "condiciones de prueba de la ola 3: no provienen de una ejecucion medida"
JUSTIFICACION = "cuadrilla reforzada en la prueba de la ola 3; texto de prueba, no de obra"
CLAVES_DESGLOSE = {
    "materiales",
    "equipos",
    "mano_obra",
    "costo_directo",
    "con_administracion",
    "precio_unitario",
}


def _tablas() -> dict[str, list[dict[str, str]]]:
    return {
        "materiales": filas_materiales(APU_TUBERIA),
        "equipos": filas_equipos(APU_TUBERIA),
        "mano_obra": filas_mano_obra(APU_TUBERIA),
    }


def _cuerpo(codigo: str = NUEVA, descripcion: str = "Partida de prueba", **extra) -> dict:
    return {
        "codigo": codigo,
        "descripcion": descripcion,
        "unidad": APU_TUBERIA.unidad,
        "dominio": "civil",
        "rendimiento": "100",
        **_tablas(),
        **extra,
    }


def _guardar_cuerpo(**extra) -> dict:
    return _cuerpo(**{"fecha": "2026-05-01", "condiciones": CONDICIONES, **extra})


def _caso(ruta: Path, segundo_rendimiento: bool = False) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            if segundo_rendimiento:
                registrar_rendimiento(
                    sesion,
                    TUBERIA,
                    Decimal("110"),
                    TipoRendimiento.ESTIMADO,
                    FECHA_LINEA_BASE,
                    condiciones="segundo estimado de prueba (ola 3)",
                )
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("api_composicion"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    copiar_instalacion(_plantilla)
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


def _usar(ruta: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
    return ruta


@pytest.fixture
def caso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return _usar(_caso(tmp_path / "caso.db"), monkeypatch)


@pytest.fixture
def caso_con_rango(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return _usar(_caso(tmp_path / "caso.db", segundo_rendimiento=True), monkeypatch)


@pytest.fixture
def api(caso: Path) -> Iterator[TestClient]:
    with cliente_de_prueba() as cliente:
        yield cliente


# --- opciones ----------------------------------------------------------------------------------


def test_las_opciones_son_los_dominios_y_las_modalidades_del_contrato(api: TestClient) -> None:
    respuesta = api.get("/v1/composicion/opciones")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "dominios": ["civil", "telecom", "industrial", "sistemas"],
        "modalidades": ["jornal", "destajo"],
    }


# --- evaluar -----------------------------------------------------------------------------------


def test_evaluar_el_formulario_en_blanco_es_vacio_con_la_bienvenida(api: TestClient) -> None:
    respuesta = api.post(
        "/v1/composicion/evaluar",
        json={
            "codigo": "",
            "descripcion": "",
            "unidad": "",
            "dominio": "civil",
            "rendimiento": "",
            "materiales": [{}],
            "equipos": [],
            "mano_obra": [],
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "estado": "vacio",
        "aviso": (
            "Comience por la cabecera (codigo y descripcion) y declare al menos un insumo en "
            "alguna de las tres tablas de abajo, o busquelo en la referencia MaPreX: el desglose "
            "se calcula aqui automaticamente, sin necesidad de guardar."
        ),
        "desglose": None,
        "advertencias": [],
        "requiere_justificacion": False,
        "contraste": None,
    }


def test_evaluar_una_tabla_a_medias_es_200_incompleto_nunca_4xx(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/evaluar", json=_cuerpo(rendimiento="abc"))
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "incompleto"
    assert cuerpo["aviso"] == "rendimiento: 'abc' no es un numero decimal valido"
    assert cuerpo["desglose"] is None


def test_evaluar_una_composicion_valida_da_el_desglose_como_texto(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/evaluar", json=_cuerpo())
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "valido" and cuerpo["aviso"] is None
    desglose = cuerpo["desglose"]
    assert set(desglose) == CLAVES_DESGLOSE
    assert all(isinstance(valor, str) for valor in desglose.values())
    assert desglose["materiales"] == "7.19"
    assert desglose["precio_unitario"] == "10.19"
    assert cuerpo["advertencias"] == [
        {
            "tipo": "partida_nueva",
            "texto": (
                "Partida nueva: la estimacion por reglas parte del PU anterior de la partida, "
                "que no existe; el contraste no es posible (UC-07, flujo 3a)."
            ),
        }
    ]
    assert cuerpo["requiere_justificacion"] is False
    assert cuerpo["contraste"] is None


def test_evaluar_fuera_del_rango_pide_justificacion(caso_con_rango: Path) -> None:
    with cliente_de_prueba() as cliente:
        respuesta = cliente.post(
            "/v1/composicion/evaluar",
            json=_cuerpo(TUBERIA, APU_TUBERIA.descripcion, rendimiento="150"),
        )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["requiere_justificacion"] is True
    rendimiento = [a for a in cuerpo["advertencias"] if a["tipo"] == "rendimiento"]
    assert len(rendimiento) == 1
    assert rendimiento[0]["texto"].startswith("el rendimiento 150 se aparta")


def test_evaluar_con_la_sesion_de_quien_arma_responde_y_quien_revisa_no(caso: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.post("/v1/composicion/evaluar", json=_cuerpo(), headers=protegida(ficha))
    assert respuesta.status_code == 200
    assert respuesta.json()["desglose"]["precio_unitario"] == "10.19"

    revisor, ficha_revisor = con_cuenta(app, "rita")
    rechazo = revisor.post(
        "/v1/composicion/evaluar", json=_cuerpo(), headers=protegida(ficha_revisor)
    )
    assert (rechazo.status_code, rechazo.json()) == (403, {"detalle": MENSAJE_PERMISO})


# --- partidas/{codigo} -------------------------------------------------------------------------


def test_la_precarga_de_una_partida_existente_trae_sus_tablas_como_texto(api: TestClient) -> None:
    respuesta = api.get(f"/v1/composicion/partidas/{TUBERIA}")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["existe"] is True and cuerpo["hay_historial"] is True
    assert Decimal(cuerpo["rendimiento_propuesto"]) == APU_TUBERIA.rendimiento
    materiales = cuerpo["tablas"]["materiales"]
    assert [fila["descripcion"] for fila in materiales] == [
        linea.descripcion for linea in APU_TUBERIA.materiales
    ]
    assert all(isinstance(valor, str) for fila in materiales for valor in fila.values())
    assert [Decimal(fila["cantidad"]) for fila in materiales] == [
        linea.cantidad for linea in APU_TUBERIA.materiales
    ]
    assert len(cuerpo["tablas"]["equipos"]) == len(APU_TUBERIA.equipos)
    assert [f["modalidad"] for f in cuerpo["tablas"]["mano_obra"]] == ["jornal"] * len(
        APU_TUBERIA.mano_obra
    )


def test_la_precarga_de_un_codigo_nuevo_es_200_con_las_tablas_vacias(api: TestClient) -> None:
    respuesta = api.get(f"/v1/composicion/partidas/{NUEVA}")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "existe": False,
        "tablas": {"materiales": [], "equipos": [], "mano_obra": []},
        "rendimiento_propuesto": None,
        "hay_historial": False,
    }


# --- referencia --------------------------------------------------------------------------------


def test_la_referencia_sugiere_filas_completadas_desde_los_csv(
    api: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import aplicacion.composicion as composicion

    carpeta = tmp_path / "raiz" / "data" / "precios" / "maprex_2026-07"
    carpeta.mkdir(parents=True)
    cabecera = (
        "tipo,insumo,unidad,precio_bs,bono_bs,factor_depreciacion,precio_usd,fecha_vigencia,"
        "archivo,ref_maprex,notas\n"
    )
    for nombre in ("civil", "telecom", "industrial", "sistemas"):
        filas = "material,TUBO FICTICIO DE PRUEBA,m,,,,2.50,2026-07-01,prueba.pdf,FIC01,\n"
        contenido = cabecera + (filas if nombre == "civil" else "")
        (carpeta / f"referencia_{nombre}.csv").write_text(contenido, encoding="utf-8")
    monkeypatch.setattr(composicion, "_RAIZ_REPOSITORIO", tmp_path / "raiz")

    respuesta = api.get("/v1/composicion/referencia", params={"tipo": "material", "q": "tubo"})
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {
            "etiqueta": "TUBO FICTICIO DE PRUEBA — 2.50 USD/m · ref. FIC01",
            "ref_maprex": "FIC01",
            "fila": {
                "descripcion": "TUBO FICTICIO DE PRUEBA",
                "unidad": "m",
                "cantidad": "",
                "precio": "2.50",
            },
        }
    ]
    vacia = api.get("/v1/composicion/referencia", params={"tipo": "material", "q": ""})
    assert (vacia.status_code, vacia.json()) == (200, [])


def test_la_referencia_rechaza_un_tipo_desconocido_con_422(api: TestClient) -> None:
    respuesta = api.get("/v1/composicion/referencia", params={"tipo": "herramienta", "q": "x"})
    assert respuesta.status_code == 422


# --- similares ---------------------------------------------------------------------------------


def test_las_similares_traen_la_composicion_como_texto(
    api: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    import aplicacion.composicion as composicion
    from ml.normalization import PartidaSimilar, Propuesta

    normalizacion = SimpleNamespace(
        Propuesta=Propuesta,
        proponedor=lambda _partidas: (
            lambda _d: Propuesta((PartidaSimilar(TUBERIA, APU_TUBERIA.descripcion, 0.875),))
        ),
    )
    monkeypatch.setattr(composicion, "_importar_normalizacion", lambda: normalizacion)
    respuesta = api.get(
        "/v1/composicion/similares", params={"dominio": "civil", "descripcion": "tuberia"}
    )
    assert respuesta.status_code == 200
    [similar] = respuesta.json()
    assert similar["codigo"] == TUBERIA
    assert similar["descripcion"] == APU_TUBERIA.descripcion
    assert similar["puntaje"] == "0.88"  # dos decimales, como la pagina clasica (0.875 -> 0.88)
    assert Decimal(similar["rendimiento"]) == APU_TUBERIA.rendimiento
    assert similar["unidad"] == APU_TUBERIA.unidad
    assert similar["aviso"] is None
    assert len(similar["tablas"]["materiales"]) == len(APU_TUBERIA.materiales)


def test_las_similares_sin_descripcion_son_una_lista_vacia(api: TestClient) -> None:
    respuesta = api.get("/v1/composicion/similares", params={"dominio": "civil", "descripcion": ""})
    assert (respuesta.status_code, respuesta.json()) == (200, [])


# --- guardar -----------------------------------------------------------------------------------


def test_guardar_una_partida_nueva_confirma_y_responde_el_precio(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/guardar", json=_guardar_cuerpo())
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "precio_unitario": "10.19",
        "mensaje": (f"Composicion guardada para la partida {NUEVA}: precio unitario 10.19."),
        "justificada": False,
        "avisos": [],
    }
    precarga = api.get(f"/v1/composicion/partidas/{NUEVA}").json()
    assert precarga["existe"] is True  # confirmado: otra peticion (otra sesion) lo lee


def test_guardar_sin_condiciones_es_422_y_no_escribe(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/guardar", json=_guardar_cuerpo(condiciones="  "))
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"].startswith(
        "Las condiciones del rendimiento son obligatorias para guardar (RF-33)"
    )
    assert api.get(f"/v1/composicion/partidas/{NUEVA}").json()["existe"] is False


def test_guardar_una_composicion_invalida_es_422_con_el_mensaje(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/guardar", json=_guardar_cuerpo(rendimiento=""))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "rendimiento: '' no es un numero decimal valido"}
    assert api.get(f"/v1/composicion/partidas/{NUEVA}").json()["existe"] is False


def test_guardar_con_otra_cabecera_sobre_una_existente_es_422_con_el_motivo(
    api: TestClient,
) -> None:
    respuesta = api.post(
        "/v1/composicion/guardar",
        json=_guardar_cuerpo(codigo=TUBERIA, descripcion="Otra descripcion"),
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"].startswith(
        f"la partida {TUBERIA} ya existe con la descripcion"
    )


def test_guardar_sin_lista_de_precios_vigente_es_409_y_no_escribe(api: TestClient) -> None:
    respuesta = api.post("/v1/composicion/guardar", json=_guardar_cuerpo(fecha="2020-01-01"))
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "no hay ninguna lista de precios vigente al 2020-01-01"}
    assert api.get(f"/v1/composicion/partidas/{NUEVA}").json()["existe"] is False


def test_guardar_con_advertencia_y_justificacion_la_registra(caso_con_rango: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.post(
        "/v1/composicion/guardar",
        json=_guardar_cuerpo(
            codigo=TUBERIA,
            descripcion=APU_TUBERIA.descripcion,
            rendimiento="150",
            justificacion=JUSTIFICACION,
        ),
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["justificada"] is True
    assert cuerpo["avisos"] == []
    assert cuerpo["mensaje"].endswith(
        " Justificacion de la advertencia registrada junto al rendimiento 150 (UC-06, flujo 4a)."
    )


def test_guardar_sin_csrf_con_la_cookie_es_403(caso: Path) -> None:
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.post(
        "/v1/composicion/guardar",
        json=_guardar_cuerpo(),
        headers={"Origin": "http://127.0.0.1:8000"},
    )
    assert respuesta.status_code == 403
