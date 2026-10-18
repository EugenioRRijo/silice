"""`/v1/produccion/*`: materiales, movimientos, existencias, importación de la báscula y bandeja de
pesajes sospechosos por la API (Tarea 4.8; RF-134, RF-130 a RF-133, RNF-25, RT-S4-2, RT-S4-4).

Oráculos escritos a mano, ninguno sale de la función bajo prueba:

- Serie de «Arena lavada» (`ARENA`, m3, mínima 20; **ejemplo construido**): entrada 100 (1-oct),
  despacho 30 (2-oct), despacho 45,5 (3-oct), entrada 10 (4-oct), conteo 40 (5-oct). Existencia
  al 2-oct 100 − 30 = 70; al 3-oct 70 − 45,5 = 24,5; al 4-oct 24,5 + 10 = 34,5; el ajuste del
  5-oct es 40 − 34,5 = +5,5 y la existencia al 5-oct y sin fecha es 40.
- Reporte básico (`tests/fixtures/bascula/ORACULO.md` §1) con ARENA en m3, densidad 1,60 t/m³, y
  PIEDRA34 en t: registra 2 despachos (ARENA 28,300 t / 1,60 = 17,6875 m3; PIEDRA34 24,5 t) y manda
  4 filas a la bandeja (3 dudosas del lector y GRAVA9, material desconocido). Reimportarlo da
  ya_registrados = 2.
- Existencias tras importar el básico: ARENA 0 − 17,6875 = −17,6875 y PIEDRA34 0 − 24,5 = −24,5
  (un despacho nunca se bloquea, RT-S4-2: queda negativa y el tablero lo marca).

Cada petición es una transacción: lo que la ruta registra queda confirmado (se ve desde otra
sesión) y un error no deja nada a medias.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from api.dependencias import USUARIO_API
from api.main import app
from api.proteccion import LIMITE_CUERPO
from operacion import config
from operacion.base_datos import Destino, preparar_base
from operacion.instalacion import sesion_de_instalacion
from produccion.modelo import Movimiento, PesajeSospechoso
from tests.fixtures.bascula import construir
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba

REFERENCIA = "2026-10-18"
TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TIPO_CSV = "text/csv"
MENSAJE_SIN_UNIDAD = "Indique si los pesos están en kg o en t."

RUTAS = [
    ("GET", "/v1/produccion/materiales"),
    ("POST", "/v1/produccion/materiales"),
    ("POST", "/v1/produccion/movimientos"),
    ("GET", "/v1/produccion/existencias"),
    ("POST", "/v1/produccion/bascula/importar"),
    ("GET", "/v1/produccion/pesajes-sospechosos"),
    ("POST", "/v1/produccion/pesajes-sospechosos/1/resolver"),
    ("POST", "/v1/produccion/pesajes-sospechosos/1/descartar"),
]


# --- Ayudas --------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    """Una `instalacion.db` ya migrada, una vez por módulo (patrón de `test_api_clave.py`)."""
    plantilla = tmp_path_factory.mktemp("plantilla_produccion") / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path) -> None:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_migrada, destino)


@pytest.fixture
def http() -> TestClient:
    """Cliente desde 127.0.0.1 con una clave de API real de la instalación temporal."""
    return TestClient(
        app,
        base_url=ANFITRION,
        client=IP_LOCAL,
        headers={CABECERA: crear_clave_de_prueba()},
        raise_server_exceptions=False,
    )


def _material(http, codigo, unidad, minima="0", densidad=None, nombre=None):
    cuerpo = {
        "codigo": codigo,
        "nombre": nombre or f"Material {codigo}",
        "unidad_venta": unidad,
        "existencia_minima": minima,
    }
    if densidad is not None:
        cuerpo["densidad_t_m3"] = densidad
    return http.post("/v1/produccion/materiales", json=cuerpo)


def _movimiento(http, codigo, tipo, fecha, cantidad, **extra):
    cuerpo = {
        "material_codigo": codigo,
        "tipo": tipo,
        "fecha": fecha,
        "cantidad": cantidad,
        **extra,
    }
    return http.post("/v1/produccion/movimientos", json=cuerpo)


def _existencias(http, a_fecha=None) -> dict[str, dict]:
    params = {} if a_fecha is None else {"a_fecha": a_fecha}
    r = http.get("/v1/produccion/existencias", params=params)
    assert r.status_code == 200, r.text
    return {fila["codigo"]: fila for fila in r.json()}


def _importar(
    http, datos: bytes, nombre="reporte.xlsx", tipo=TIPO_XLSX, referencia=REFERENCIA, **c
):
    formulario = {"fecha_referencia": referencia, **c}
    formulario = {k: v for k, v in formulario.items() if v is not None}
    return http.post(
        "/v1/produccion/bascula/importar",
        files={"archivo": (nombre, datos, tipo)},
        data=formulario,
    )


def _catalogo_del_basico(http) -> None:
    assert _material(http, "ARENA", "m3", "20", "1.60", "Arena lavada").status_code == 201
    assert _material(http, "PIEDRA34", "t", "10").status_code == 201


def _contar(modelo) -> int:
    with sesion_de_instalacion() as sesion:
        return sesion.scalar(select(func.count()).select_from(modelo))


# --- Clave de API (RF-98, RF-134) ----------------------------------------------------------------


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS, ids=[f"{m} {r}" for m, r in RUTAS])
def test_sin_clave_toda_ruta_responde_401(metodo: str, ruta: str) -> None:
    ajeno = TestClient(app, base_url=ANFITRION, client=IP_LOCAL)
    for cabeceras in ({}, {CABECERA: ""}, {CABECERA: "desconocida.secreto"}):
        r = ajeno.request(metodo, ruta, json={}, headers=cabeceras)
        assert r.status_code == 401, (cabeceras, r.text)
        assert "detalle" in r.json()


def test_las_rutas_de_la_tabla_son_todas_las_de_produccion_en_la_aplicacion() -> None:
    """Si alguien agrega una ruta a `/v1/produccion` sin ponerla en `RUTAS`, esta prueba lo dice."""
    esquema = {
        (metodo.upper(), camino.replace("{id_sospechoso}", "1"))
        for camino, operaciones in app.openapi()["paths"].items()
        if camino.startswith("/v1/produccion")
        for metodo in operaciones
    }
    assert esquema == set(RUTAS)


# --- Materiales y movimientos (serie a mano de 4.4) ----------------------------------------------


def test_crear_material_y_registrar_el_flujo_de_la_serie_a_mano(http) -> None:
    r = _material(http, "ARENA", "m3", "20", "1.60", "Arena lavada")
    assert r.status_code == 201, r.text
    assert r.json()["codigo"] == "ARENA"

    assert _movimiento(http, "ARENA", "entrada", "2026-10-01", "100").status_code == 201
    assert _movimiento(http, "ARENA", "despacho", "2026-10-02", "30").status_code == 201
    assert _movimiento(http, "ARENA", "despacho", "2026-10-03", "45.5").status_code == 201
    assert _movimiento(http, "ARENA", "entrada", "2026-10-04", "10").status_code == 201

    assert Decimal(_existencias(http, "2026-10-02")["ARENA"]["existencia"]) == Decimal("70")
    assert Decimal(_existencias(http, "2026-10-03")["ARENA"]["existencia"]) == Decimal("24.5")
    assert Decimal(_existencias(http, "2026-10-04")["ARENA"]["existencia"]) == Decimal("34.5")

    ajuste = _movimiento(http, "ARENA", "ajuste", "2026-10-05", "40", nota="conteo de cierre")
    assert ajuste.status_code == 201, ajuste.text
    cuerpo = ajuste.json()
    assert cuerpo["tipo"] == "ajuste" and Decimal(cuerpo["cantidad"]) == Decimal("5.5")

    por_fecha = _existencias(http, "2026-10-05")["ARENA"]
    sin_fecha = _existencias(http)["ARENA"]
    assert Decimal(por_fecha["existencia"]) == Decimal("40") == Decimal(sin_fecha["existencia"])
    assert (sin_fecha["queda_poco"], sin_fecha["negativa"]) == (False, False)
    assert Decimal(sin_fecha["minima"]) == Decimal("20")


def test_un_ajuste_sin_diferencia_responde_200_con_null(http) -> None:
    _material(http, "ARENA", "m3", "20", "1.60")
    _movimiento(http, "ARENA", "entrada", "2026-10-01", "40")
    r = _movimiento(http, "ARENA", "ajuste", "2026-10-02", "40")
    assert (r.status_code, r.json()) == (200, None)
    assert _contar(Movimiento) == 1  # solo la entrada


def test_el_ajuste_negativo_guarda_la_diferencia_con_signo(http) -> None:
    _material(http, "ARENA", "m3", "20", "1.60")
    for fecha, cantidad in (("2026-10-01", "100"), ("2026-10-04", "10")):
        _movimiento(http, "ARENA", "entrada", fecha, cantidad)
    _movimiento(http, "ARENA", "despacho", "2026-10-02", "30")
    _movimiento(http, "ARENA", "despacho", "2026-10-03", "45.5")
    r = _movimiento(http, "ARENA", "ajuste", "2026-10-05", "20")  # 34,5 -> 20: -14,5
    assert r.status_code == 201 and Decimal(r.json()["cantidad"]) == Decimal("-14.5")
    fila = _existencias(http)["ARENA"]
    assert Decimal(fila["existencia"]) == Decimal("20")
    assert fila["queda_poco"] is True  # 20 <= mínima 20


def test_un_despacho_que_deja_negativo_se_registra_y_se_marca(http) -> None:
    """RT-S4-2: nunca se bloquea."""
    _material(http, "ARENA", "m3", "20", "1.60")
    r = _movimiento(http, "ARENA", "despacho", "2026-10-01", "3")
    assert r.status_code == 201
    fila = _existencias(http)["ARENA"]
    assert Decimal(fila["existencia"]) == Decimal("-3")
    assert (fila["negativa"], fila["queda_poco"]) == (True, True)


def test_los_movimientos_se_guardan_con_el_usuario_de_la_api(http) -> None:
    _material(http, "ARENA", "m3", "20", "1.60")
    r = _movimiento(http, "ARENA", "entrada", "2026-10-01", "100")
    assert USUARIO_API == "api (clave de API)"
    assert r.json()["usuario"] == USUARIO_API
    with sesion_de_instalacion() as sesion:
        assert sesion.scalar(select(Movimiento.usuario)) == USUARIO_API


def test_lo_que_registra_una_ruta_queda_confirmado(http) -> None:
    """Se ve desde otra sesión: la dependencia hace el `commit` al terminar bien."""
    _material(http, "ARENA", "m3", "20", "1.60")
    _movimiento(http, "ARENA", "entrada", "2026-10-01", "100")
    assert _contar(Movimiento) == 1


def test_el_listado_de_materiales_trae_los_datos_como_texto(http) -> None:
    _material(http, "PIEDRA34", "t", "10", nombre="Piedra 3/4")
    _material(http, "ARENA", "m3", "20", "1.60", "Arena lavada")
    r = http.get("/v1/produccion/materiales")
    assert r.status_code == 200
    por_codigo = {m["codigo"]: m for m in r.json()}
    assert set(por_codigo) == {"ARENA", "PIEDRA34"}
    assert por_codigo["ARENA"]["densidad_t_m3"] == "1.60"
    assert por_codigo["ARENA"]["existencia_minima"] == "20"
    assert por_codigo["PIEDRA34"]["densidad_t_m3"] is None
    assert (por_codigo["ARENA"]["unidad_venta"], por_codigo["ARENA"]["activo"]) == ("m3", True)


def test_codigo_repetido_responde_409_y_no_cambia_nada(http) -> None:
    assert _material(http, "ARENA", "m3", "20", "1.60").status_code == 201
    r = _material(http, "ARENA", "t", "5")
    assert r.status_code == 409 and "ARENA" in r.json()["detalle"]
    assert len(http.get("/v1/produccion/materiales").json()) == 1


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"codigo": "X", "nombre": "X", "unidad_venta": "kg", "existencia_minima": "0"},
        {"codigo": "X", "nombre": "X", "unidad_venta": "t", "existencia_minima": "-1"},
        {"codigo": "X", "nombre": "X", "unidad_venta": "t", "existencia_minima": "abc"},
        {
            "codigo": "X",
            "nombre": "X",
            "unidad_venta": "m3",
            "existencia_minima": "0",
            "densidad_t_m3": "0",
        },
        {
            "codigo": "X",
            "nombre": "X",
            "unidad_venta": "m3",
            "existencia_minima": "0",
            "densidad_t_m3": "mucha",
        },
        {"codigo": "  ", "nombre": "X", "unidad_venta": "t", "existencia_minima": "0"},
    ],
    ids=[
        "unidad",
        "minima negativa",
        "minima no decimal",
        "densidad cero",
        "densidad texto",
        "codigo vacio",
    ],
)
def test_material_con_datos_invalidos_responde_422_y_no_guarda(http, cuerpo) -> None:
    r = http.post("/v1/produccion/materiales", json=cuerpo)
    assert r.status_code == 422, r.text
    assert http.get("/v1/produccion/materiales").json() == []


@pytest.mark.parametrize(
    ("cuerpo", "que"),
    [
        ({"tipo": "entrada", "fecha": "2026-10-01", "cantidad": "0"}, "cantidad cero"),
        ({"tipo": "despacho", "fecha": "2026-10-01", "cantidad": "-2"}, "cantidad negativa"),
        ({"tipo": "entrada", "fecha": "2026-10-01", "cantidad": "diez"}, "cantidad no decimal"),
        ({"tipo": "entrada", "fecha": "01/10/2026", "cantidad": "1"}, "fecha no ISO"),
        ({"tipo": "venta", "fecha": "2026-10-01", "cantidad": "1"}, "tipo desconocido"),
        ({"tipo": "ajuste", "fecha": "2026-10-01", "cantidad": "-5"}, "conteo negativo"),
        (
            {
                "material_codigo": "NO-EXISTE",
                "tipo": "entrada",
                "fecha": "2026-10-01",
                "cantidad": "1",
            },
            "material inexistente",
        ),
    ],
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_movimiento_invalido_responde_422_y_no_guarda(http, cuerpo, que) -> None:
    _material(http, "ARENA", "m3", "20", "1.60")
    completo = {"material_codigo": "ARENA", **cuerpo}
    r = http.post("/v1/produccion/movimientos", json=completo)
    assert r.status_code == 422, (que, r.text)
    assert _contar(Movimiento) == 0


def test_una_cantidad_como_numero_json_se_rechaza(http) -> None:
    """Las cantidades entran como texto: un número JSON (float) es 422."""
    _material(http, "ARENA", "m3", "20", "1.60")
    r = http.post(
        "/v1/produccion/movimientos",
        json={
            "material_codigo": "ARENA",
            "tipo": "entrada",
            "fecha": "2026-10-01",
            "cantidad": 1.5,
        },
    )
    assert r.status_code == 422
    assert _contar(Movimiento) == 0


def test_existencias_con_fecha_mal_escrita_responde_422(http) -> None:
    r = http.get("/v1/produccion/existencias", params={"a_fecha": "ayer"})
    assert r.status_code == 422 and "a_fecha" in r.json()["detalle"]


def test_las_cantidades_viajan_como_texto(http) -> None:
    _material(http, "ARENA", "m3", "20", "1.60")
    movimiento = _movimiento(http, "ARENA", "entrada", "2026-10-01", "100.250").json()
    fila = _existencias(http)["ARENA"]
    material = http.get("/v1/produccion/materiales").json()[0]
    assert movimiento["cantidad"] == "100.250"
    for texto in (
        movimiento["cantidad"],
        fila["existencia"],
        fila["minima"],
        material["existencia_minima"],
        material["densidad_t_m3"],
    ):
        assert isinstance(texto, str)
    assert Decimal(fila["existencia"]) == Decimal("100.250")


# --- Importar el reporte de báscula --------------------------------------------------------------


def test_importar_el_reporte_basico_por_la_api(http) -> None:
    _catalogo_del_basico(http)
    datos = construir.xlsx_basico()
    r = _importar(http, datos)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "registrados": 2,
        "ya_registrados": 0,
        "a_la_bandeja": 4,
        "huella": hashlib.sha256(datos).hexdigest(),
    }
    existencias = _existencias(http)
    assert Decimal(existencias["ARENA"]["existencia"]) == Decimal("-17.6875")
    assert Decimal(existencias["PIEDRA34"]["existencia"]) == Decimal("-24.5")
    assert existencias["ARENA"]["negativa"] and existencias["PIEDRA34"]["negativa"]
    with sesion_de_instalacion() as sesion:
        usuarios = set(sesion.scalars(select(Movimiento.usuario)))
        origenes = set(sesion.scalars(select(Movimiento.origen)))
    assert usuarios == {USUARIO_API} and origenes == {"bascula"}


def test_importar_el_csv_da_lo_mismo_que_el_xlsx(http) -> None:
    _catalogo_del_basico(http)
    r = _importar(http, construir.csv_basico(), "reporte.csv", TIPO_CSV)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["registrados"], cuerpo["ya_registrados"], cuerpo["a_la_bandeja"]) == (2, 0, 4)


def test_reimportar_no_duplica(http) -> None:
    _catalogo_del_basico(http)
    datos = construir.xlsx_basico()
    assert _importar(http, datos).status_code == 200
    r = _importar(http, datos)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["registrados"], cuerpo["ya_registrados"]) == (0, 2)
    assert _contar(Movimiento) == 2
    assert len(http.get("/v1/produccion/pesajes-sospechosos").json()) == 4


def test_los_cuatro_sospechosos_del_basico_traen_su_motivo(http) -> None:
    _catalogo_del_basico(http)
    _importar(http, construir.xlsx_basico())
    r = http.get("/v1/produccion/pesajes-sospechosos")
    assert r.status_code == 200
    motivos = {fila["ticket"]: fila["motivo"] for fila in r.json()}
    assert motivos == {
        "TCK-003": "tara mayor o igual que el bruto",
        "TCK-004": "neto distinto de bruto − tara",
        "TCK-005": "fecha futura",
        "TCK-006": "material desconocido",
    }
    assert all(fila["estado"] == "pendiente" for fila in r.json())


def test_importar_sin_unidad_responde_422_con_el_mensaje(http) -> None:
    _catalogo_del_basico(http)
    r = _importar(http, construir.xlsx_sin_unidad())
    assert r.status_code == 422, r.text
    assert r.json() == {"detalle": MENSAJE_SIN_UNIDAD}
    assert _contar(Movimiento) == 0 and _contar(PesajeSospechoso) == 0
    # La unidad dicha por el usuario destraba el mismo archivo (ORACULO.md §2).
    con_unidad = _importar(http, construir.xlsx_sin_unidad(), unidad_peso="kg")
    assert con_unidad.status_code == 200, con_unidad.text
    assert (con_unidad.json()["registrados"], con_unidad.json()["a_la_bandeja"]) == (2, 4)


def test_una_unidad_de_peso_desconocida_responde_422(http) -> None:
    r = _importar(http, construir.xlsx_basico(), unidad_peso="lb")
    assert r.status_code == 422 and "unidad_peso" in r.json()["detalle"]


def test_archivo_con_macros_renombrado_responde_422(http) -> None:
    _catalogo_del_basico(http)
    r = _importar(http, construir.xlsx_con_macros_renombrado())
    assert r.status_code == 422, r.text
    assert "macros" in r.json()["detalle"]
    assert _contar(Movimiento) == 0 and _contar(PesajeSospechoso) == 0


def test_xlsx_que_no_es_un_zip_responde_422(http) -> None:
    r = _importar(http, b"esto no es un libro de excel")
    assert r.status_code == 422, r.text
    assert "detalle" in r.json()


def test_archivo_desmedido_responde_422_sin_tocar_la_base(http) -> None:
    _catalogo_del_basico(http)
    r = _importar(http, construir.csv_desmedido(100_001), "grande.csv", TIPO_CSV)
    assert r.status_code == 422, r.text
    assert "100000" in r.json()["detalle"]
    assert _contar(Movimiento) == 0 and _contar(PesajeSospechoso) == 0


@pytest.mark.parametrize("nombre", ["reporte.txt", "reporte.xls", "reporte.xlsm", "reporte"])
def test_extension_equivocada_responde_415(http, nombre: str) -> None:
    r = _importar(http, construir.csv_basico(), nombre)
    assert r.status_code == 415, r.text
    assert ".csv" in r.json()["detalle"] and ".xlsx" in r.json()["detalle"]


def test_un_cuerpo_de_mas_de_20_mib_responde_413(http) -> None:
    assert LIMITE_CUERPO == 20 * 1024 * 1024
    r = _importar(http, b"a;b\n" * ((LIMITE_CUERPO // 4) + 10), "enorme.csv", TIPO_CSV)
    assert r.status_code == 413
    assert _contar(Movimiento) == 0


def test_la_fecha_de_referencia_es_obligatoria(http) -> None:
    r = http.post(
        "/v1/produccion/bascula/importar",
        files={"archivo": ("reporte.csv", construir.csv_basico(), TIPO_CSV)},
    )
    assert r.status_code == 422


@pytest.mark.parametrize("referencia", ["", "   ", "18/10/2026", "mañana"])
def test_la_fecha_de_referencia_mal_escrita_responde_422(http, referencia: str) -> None:
    r = _importar(http, construir.csv_basico(), "reporte.csv", TIPO_CSV, referencia=referencia)
    assert r.status_code == 422
    assert "fecha_referencia" in json.dumps(r.json())


def test_la_referencia_manda_sobre_el_reloj(http) -> None:
    """Con referencia 2027-01-01, la fila del 2026-12-31 ya no es «fecha futura»: la API no usa el
    reloj para decidir (la bandeja baja de 4 a 3 y entra un despacho más)."""
    _catalogo_del_basico(http)
    r = _importar(http, construir.xlsx_basico(), referencia="2027-01-01")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["registrados"], cuerpo["a_la_bandeja"]) == (3, 3)


def test_mapeo_mal_formado_responde_422(http) -> None:
    for mapeo in ("{no es json", "[1, 2]", '{"material": "tres"}', '{"material": 1.5}', "null"):
        r = _importar(http, construir.csv_basico(), "reporte.csv", TIPO_CSV, mapeo=mapeo)
        assert r.status_code == 422, (mapeo, r.text)
        assert "mapeo" in r.json()["detalle"]


def test_faltan_columnas_pide_el_mapeo_con_la_lista(http) -> None:
    sin_material = (
        b"Ticket;Fecha;Placa;Cliente;Producto;Bruto (kg);Tara (kg);Neto (kg)\n"
        b"TCK-900;2026-10-15;EJ-900;Cliente Ejemplo A;ARENA;42500;14200;28300\n"
    )
    _catalogo_del_basico(http)
    r = _importar(http, sin_material, "sin_material.csv", TIPO_CSV)
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["detalle"] == "Indique en qué columna están: material."
    assert cuerpo["faltan"] == ["material"]
    # Con el mapeo explícito (columna 4, 0-based) el mismo archivo se importa.
    r = _importar(
        http, sin_material, "sin_material.csv", TIPO_CSV, mapeo=json.dumps({"material": 4})
    )
    assert r.status_code == 200, r.text
    assert r.json()["registrados"] == 1


def test_un_fallo_inesperado_responde_500_con_mensaje_fijo(http, monkeypatch, caplog) -> None:
    import api.rutas.produccion as rutas

    def _explota(*_a, **_k):
        raise RuntimeError("detalle interno SECRETO-123")

    monkeypatch.setattr(rutas, "leer", _explota)
    with caplog.at_level("ERROR"):
        r = _importar(http, construir.csv_basico(), "reporte.csv", TIPO_CSV)
    assert r.status_code == 500
    assert "SECRETO-123" not in r.text and "RuntimeError" not in r.text
    assert "SECRETO-123" in caplog.text  # el detalle va solo al registro


def test_si_la_importacion_falla_a_medias_no_queda_nada(http, monkeypatch) -> None:
    import api.rutas.produccion as rutas

    def _importar_y_romper(sesion, lectura, *, usuario):
        resultado = rutas.importar(sesion, lectura, usuario=usuario)
        raise RuntimeError(f"fallo después de importar {resultado.registrados}")

    _catalogo_del_basico(http)
    monkeypatch.setattr(rutas, "importar", _importar_y_romper)
    assert _importar(http, construir.xlsx_basico()).status_code == 500
    assert _contar(Movimiento) == 0 and _contar(PesajeSospechoso) == 0


# --- Bandeja: resolver y descartar ---------------------------------------------------------------


def _id_de(http, ticket: str) -> int:
    filas = http.get("/v1/produccion/pesajes-sospechosos").json()
    return next(f["id"] for f in filas if f["ticket"] == ticket)


def test_resolver_y_descartar(http) -> None:
    _catalogo_del_basico(http)
    _importar(http, construir.xlsx_basico())

    resolver = http.post(
        f"/v1/produccion/pesajes-sospechosos/{_id_de(http, 'TCK-006')}/resolver",
        json={
            "material_codigo": "PIEDRA34",
            "fecha": "2026-10-17",
            "neto_t": "18.0",
            "ticket": "TCK-006",
            "ahora": "2026-10-18T09:30:00",
        },
    )
    assert resolver.status_code == 201, resolver.text
    despacho = resolver.json()
    assert despacho["tipo"] == "despacho" and despacho["ticket"] == "TCK-006"
    assert Decimal(despacho["cantidad"]) == Decimal("18.0")
    assert despacho["usuario"] == USUARIO_API

    descartar = http.post(
        f"/v1/produccion/pesajes-sospechosos/{_id_de(http, 'TCK-003')}/descartar",
        json={"ahora": "2026-10-18T09:31:00"},
    )
    assert descartar.status_code == 204 and descartar.content == b""

    pendientes = http.get("/v1/produccion/pesajes-sospechosos").json()
    assert {f["ticket"] for f in pendientes} == {"TCK-004", "TCK-005"}
    # PIEDRA34: −24,5 (TCK-002) − 18,0 (resuelto) = −42,5; el descartado no crea despacho.
    assert Decimal(_existencias(http)["PIEDRA34"]["existencia"]) == Decimal("-42.5")
    assert _contar(Movimiento) == 3
    with sesion_de_instalacion() as sesion:
        cerrados = {
            s.ticket: (s.estado, s.resuelto_por, s.resuelto_en.isoformat())
            for s in sesion.scalars(
                select(PesajeSospechoso).where(PesajeSospechoso.estado != "pendiente")
            )
        }
    assert cerrados == {
        "TCK-006": ("resuelto", USUARIO_API, "2026-10-18T09:30:00"),
        "TCK-003": ("descartado", USUARIO_API, "2026-10-18T09:31:00"),
    }


def test_resolver_dos_veces_responde_409(http) -> None:
    _catalogo_del_basico(http)
    _importar(http, construir.xlsx_basico())
    ruta = f"/v1/produccion/pesajes-sospechosos/{_id_de(http, 'TCK-006')}"
    cuerpo = {
        "material_codigo": "PIEDRA34",
        "fecha": "2026-10-17",
        "neto_t": "18.0",
        "ticket": "TCK-006",
        "ahora": "2026-10-18T09:30:00",
    }
    assert http.post(f"{ruta}/resolver", json=cuerpo).status_code == 201
    de_nuevo = http.post(f"{ruta}/resolver", json=cuerpo)
    assert de_nuevo.status_code == 409, de_nuevo.text
    assert "resuelto" in de_nuevo.json()["detalle"]
    descartado = http.post(f"{ruta}/descartar", json={"ahora": "2026-10-18T10:00:00"})
    assert descartado.status_code == 409
    assert _contar(Movimiento) == 3  # los 2 de la importación + el resuelto


def test_descartar_dos_veces_responde_409(http) -> None:
    _catalogo_del_basico(http)
    _importar(http, construir.xlsx_basico())
    ruta = f"/v1/produccion/pesajes-sospechosos/{_id_de(http, 'TCK-003')}/descartar"
    assert http.post(ruta, json={"ahora": "2026-10-18T09:31:00"}).status_code == 204
    assert http.post(ruta, json={"ahora": "2026-10-18T09:32:00"}).status_code == 409


def test_resolver_con_un_ticket_ya_registrado_responde_409_y_deja_el_sospechoso_pendiente(
    http,
) -> None:
    _catalogo_del_basico(http)
    _importar(http, construir.xlsx_basico())
    id_sospechoso = _id_de(http, "TCK-006")
    r = http.post(
        f"/v1/produccion/pesajes-sospechosos/{id_sospechoso}/resolver",
        json={
            "material_codigo": "PIEDRA34",
            "fecha": "2026-10-17",
            "neto_t": "18.0",
            "ticket": "TCK-002",  # ya es un despacho de la importación
            "ahora": "2026-10-18T09:30:00",
        },
    )
    assert r.status_code == 409, r.text
    assert "TCK-002" in r.json()["detalle"]
    assert _contar(Movimiento) == 2
    assert id_sospechoso in {f["id"] for f in http.get("/v1/produccion/pesajes-sospechosos").json()}


def test_un_sospechoso_inexistente_responde_404(http) -> None:
    base = "/v1/produccion/pesajes-sospechosos/999"
    resolver = http.post(
        f"{base}/resolver",
        json={
            "material_codigo": "X",
            "fecha": "2026-10-17",
            "neto_t": "1",
            "ticket": "T",
            "ahora": "2026-10-18T09:30:00",
        },
    )
    descartar = http.post(f"{base}/descartar", json={"ahora": "2026-10-18T09:30:00"})
    assert (resolver.status_code, descartar.status_code) == (404, 404)


@pytest.mark.parametrize(
    "cambio",
    [
        {"material_codigo": "NO-EXISTE"},
        {"neto_t": "0"},
        {"neto_t": "mucho"},
        {"fecha": "17-10-2026"},
        {"ahora": "ayer"},
        {"ticket": "   "},
    ],
    ids=["material", "neto cero", "neto texto", "fecha", "ahora", "ticket vacio"],
)
def test_resolver_con_datos_invalidos_responde_422_y_no_cierra_el_sospechoso(
    http, cambio: dict
) -> None:
    _catalogo_del_basico(http)
    _importar(http, construir.xlsx_basico())
    id_sospechoso = _id_de(http, "TCK-006")
    cuerpo = {
        "material_codigo": "PIEDRA34",
        "fecha": "2026-10-17",
        "neto_t": "18.0",
        "ticket": "TCK-006",
        "ahora": "2026-10-18T09:30:00",
        **cambio,
    }
    r = http.post(f"/v1/produccion/pesajes-sospechosos/{id_sospechoso}/resolver", json=cuerpo)
    assert r.status_code == 422, r.text
    assert _contar(Movimiento) == 2
    assert id_sospechoso in {f["id"] for f in http.get("/v1/produccion/pesajes-sospechosos").json()}
