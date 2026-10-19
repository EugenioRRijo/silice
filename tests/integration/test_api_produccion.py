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

Dos entradas (RT-9): la clave de API (`X-Silice-Clave`, integraciones; el `usuario` guardado es
`USUARIO_API`) y la sesión web (cookie `silice_sesion` más `X-Silice-CSRF` y `Origin` en lo que
escribe; el `usuario` guardado es el responsable de la cuenta, `Nombre <login>`, RF-82). Las cuentas
de la plantilla: `admin` (administrador), `ana` (arma) y `rita` (revisa). El CSRF se recalcula aquí
con `hashlib` (`sha256("csrf:" + ficha)`), no con el código bajo prueba.
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
from seguridad import cuentas
from seguridad.base import abrir_sesion, crear_motor
from tests.fixtures.bascula import construir
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona

REFERENCIA = "2026-10-18"
TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TIPO_CSV = "text/csv"
MENSAJE_SIN_UNIDAD = "Indique si los pesos están en kg o en t."
NUEVA = "otra contrasena larga de prueba"
COOKIE = "silice_sesion"
CABECERA_CSRF = "X-Silice-CSRF"
CONTRASENAS = {"admin": CONTRASENA, "ana": NUEVA, "rita": NUEVA}

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
    """Una `instalacion.db` ya migrada, una vez por módulo (patrón de `test_api_clave.py`), con tres
    cuentas por el camino real: admin (administrador), ana (arma) y rita (revisa)."""
    carpeta = tmp_path_factory.mktemp("plantilla_produccion")
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor(plantilla)
    sesion = abrir_sesion(motor)
    try:
        admin = administrador(sesion, carpeta)
        for login, roles in (("ana", ("arma",)), ("rita", ("revisa",))):
            usuario = persona(sesion, admin, login, roles)
            cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()  # cierra el WAL: la copia lleva todo
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_migrada, destino)
    cuentas.FRENO.reiniciar()  # el freno global es del proceso: ninguna prueba hereda fallos
    yield
    cuentas.FRENO.reiniciar()


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
        b"Ticket;Fecha;Placa;Cliente;Rubro;Bruto (kg);Tara (kg);Neto (kg)\n"
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

    original = rutas.importar

    def _importar_y_romper(sesion, lectura, *, usuario):
        resultado = original(sesion, lectura, usuario=usuario)
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


# --- Sesión web (RT-9): cookie, anti-CSRF y rol --------------------------------------------------


def _csrf(ficha: str) -> str:
    """Oráculo del anti-CSRF (RS2-4): `sha256("csrf:" + ficha)` en hexadecimal."""
    return hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()


class Web:
    """Un navegador ya dentro con una cuenta: la cookie queda en el tarro del cliente y las
    peticiones que escriben llevan `X-Silice-CSRF` y `Origin` (lo que haría la interfaz nueva)."""

    def __init__(self, login: str) -> None:
        self.cliente = TestClient(
            app, base_url=ANFITRION, client=IP_LOCAL, raise_server_exceptions=False
        )
        entrada = self.cliente.post(
            "/v1/sesion", json={"login": login, "contrasena": CONTRASENAS[login]}
        )
        assert entrada.status_code == 200, entrada.text
        self.ficha = entrada.cookies.get(COOKIE)
        assert self.ficha

    def cabeceras(self) -> dict[str, str]:
        return {CABECERA_CSRF: _csrf(self.ficha), "Origin": ANFITRION}

    def get(self, ruta: str, **kw):
        return self.cliente.get(ruta, **kw)

    def post(self, ruta: str, **kw):
        return self.cliente.post(ruta, headers=self.cabeceras(), **kw)


@pytest.fixture
def ana() -> Web:
    return Web("ana")


@pytest.fixture
def rita() -> Web:
    return Web("rita")


def _material_web(web, codigo="ARENA", unidad="m3", minima="20", densidad="1.60"):
    cuerpo = {
        "codigo": codigo,
        "nombre": f"Material {codigo}",
        "unidad_venta": unidad,
        "existencia_minima": minima,
    }
    if densidad is not None:
        cuerpo["densidad_t_m3"] = densidad
    return web.post("/v1/produccion/materiales", json=cuerpo)


def _movimiento_web(web, codigo, tipo, fecha, cantidad):
    return web.post(
        "/v1/produccion/movimientos",
        json={"material_codigo": codigo, "tipo": tipo, "fecha": fecha, "cantidad": cantidad},
    )


def _importar_web(web):
    return web.post(
        "/v1/produccion/bascula/importar",
        files={"archivo": ("reporte.xlsx", construir.xlsx_basico(), TIPO_XLSX)},
        data={"fecha_referencia": REFERENCIA},
    )


@pytest.mark.parametrize("quien", ["ana", "admin"])
def test_con_sesion_de_arma_o_administrador_se_opera_la_arenera(quien: str) -> None:
    web = Web(quien)
    assert web.get("/v1/produccion/materiales").status_code == 200
    assert _material_web(web).status_code == 201
    assert _material_web(web, "PIEDRA34", "t", "10", None).status_code == 201
    assert _movimiento_web(web, "ARENA", "entrada", "2026-10-01", "100").status_code == 201
    assert _movimiento_web(web, "ARENA", "despacho", "2026-10-02", "30").status_code == 201
    ajuste = _movimiento_web(web, "ARENA", "ajuste", "2026-10-03", "65")  # 70 -> 65: -5
    assert ajuste.status_code == 201 and Decimal(ajuste.json()["cantidad"]) == Decimal("-5")
    sin_diferencia = _movimiento_web(web, "ARENA", "ajuste", "2026-10-04", "65")
    assert (sin_diferencia.status_code, sin_diferencia.json()) == (200, None)
    existencias = web.get("/v1/produccion/existencias")
    assert existencias.status_code == 200
    por_codigo = {f["codigo"]: f for f in existencias.json()}
    assert Decimal(por_codigo["ARENA"]["existencia"]) == Decimal("65")
    por_fecha = web.get("/v1/produccion/existencias", params={"a_fecha": "2026-10-02"})
    assert por_fecha.status_code == 200
    assert web.get("/v1/produccion/pesajes-sospechosos").status_code == 200
    assert _contar(Movimiento) == 3


def test_con_sesion_se_importa_la_bascula_y_se_cierra_la_bandeja(ana) -> None:
    assert _material_web(ana).status_code == 201  # ARENA, m3, 1.60
    assert _material_web(ana, "PIEDRA34", "t", "10", None).status_code == 201
    r = _importar_web(ana)
    assert r.status_code == 200, r.text
    assert (r.json()["registrados"], r.json()["a_la_bandeja"]) == (2, 4)
    ruta = "/v1/produccion/pesajes-sospechosos"
    por_ticket = {f["ticket"]: f["id"] for f in ana.get(ruta).json()}
    resuelto = ana.post(
        f"{ruta}/{por_ticket['TCK-006']}/resolver",
        json={
            "material_codigo": "PIEDRA34",
            "fecha": "2026-10-17",
            "neto_t": "18.0",
            "ticket": "TCK-006",
            "ahora": "2026-10-18T09:30:00",
        },
    )
    assert resuelto.status_code == 201, resuelto.text
    descartado = ana.post(
        f"{ruta}/{por_ticket['TCK-003']}/descartar", json={"ahora": "2026-10-18T09:31:00"}
    )
    assert descartado.status_code == 204


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS, ids=[f"{m} {r}" for m, r in RUTAS])
def test_el_rol_revisa_recibe_403_en_toda_ruta_y_no_escribe_nada(rita, metodo: str, ruta: str):
    """`revisa` lee proyectos pero no opera la arenera (`Accion.OPERAR_ARENERA`: arma y admin)."""
    r = rita.cliente.request(metodo, ruta, json={}, headers=rita.cabeceras())
    assert r.status_code == 403, r.text
    assert r.json()["detalle"] == "Su cuenta no tiene permiso para esta acción."
    assert _contar(Movimiento) == 0 and _contar(PesajeSospechoso) == 0


@pytest.mark.parametrize("cookie", [None, "ficha-que-no-existe"], ids=["sin cookie", "ficha falsa"])
@pytest.mark.parametrize(("metodo", "ruta"), RUTAS, ids=[f"{m} {r}" for m, r in RUTAS])
def test_sin_sesion_ni_clave_toda_ruta_responde_401(cookie, metodo: str, ruta: str) -> None:
    ajeno = TestClient(app, base_url=ANFITRION, client=IP_LOCAL)
    if cookie is not None:
        ajeno.cookies.set(COOKIE, cookie)
    r = ajeno.request(metodo, ruta, json={})
    assert r.status_code == 401, r.text
    assert r.json()["detalle"] == "Sesión ausente o vencida: entre de nuevo con su cuenta."


def test_una_clave_de_api_mala_no_cae_a_la_cookie(ana) -> None:
    """Con la cabecera de clave (aunque sea mala) manda la clave: una cookie buena no la salva."""
    r = ana.cliente.get("/v1/produccion/materiales", headers={CABECERA: "desconocida.secreto"})
    assert r.status_code == 401, r.text


@pytest.mark.parametrize("falta", ["sin csrf", "csrf ajeno", "sin origen", "origen ajeno"])
def test_un_post_con_sesion_sin_anti_csrf_se_rechaza_y_no_escribe(ana, falta: str) -> None:
    cabeceras = ana.cabeceras()
    if falta == "sin csrf":
        del cabeceras[CABECERA_CSRF]
    elif falta == "csrf ajeno":
        cabeceras[CABECERA_CSRF] = _csrf("otra-ficha")
    elif falta == "sin origen":
        del cabeceras["Origin"]
    else:
        cabeceras["Origin"] = "http://sitio-ajeno.example"
    r = ana.cliente.post(
        "/v1/produccion/materiales",
        headers=cabeceras,
        json={"codigo": "X", "nombre": "X", "unidad_venta": "t", "existencia_minima": "0"},
    )
    assert r.status_code == 403, (falta, r.text)
    assert ana.get("/v1/produccion/materiales").json() == []  # el GET no pide CSRF


def test_la_importacion_con_sesion_sin_csrf_se_rechaza(ana) -> None:
    r = ana.cliente.post(
        "/v1/produccion/bascula/importar",
        files={"archivo": ("reporte.xlsx", construir.xlsx_basico(), TIPO_XLSX)},
        data={"fecha_referencia": REFERENCIA},
    )
    assert r.status_code == 403, r.text
    assert _contar(Movimiento) == 0


# --- El usuario que queda escrito ----------------------------------------------------------------


def test_con_sesion_el_usuario_es_el_responsable_de_la_cuenta(ana) -> None:
    """RF-82: `Nombre <login>`, el mismo texto que deja la interfaz clásica. «Ana» es el nombre que
    `persona` le pone a `ana`."""
    _material_web(ana)
    entrada = _movimiento_web(ana, "ARENA", "entrada", "2026-10-01", "100")
    despacho = _movimiento_web(ana, "ARENA", "despacho", "2026-10-02", "30")
    ajuste = _movimiento_web(ana, "ARENA", "ajuste", "2026-10-03", "60")
    assert [r.json()["usuario"] for r in (entrada, despacho, ajuste)] == ["Ana <ana>"] * 3
    with sesion_de_instalacion() as sesion:
        assert set(sesion.scalars(select(Movimiento.usuario))) == {"Ana <ana>"}


def test_con_sesion_lo_importado_y_lo_resuelto_queda_a_nombre_de_la_cuenta(ana) -> None:
    _material_web(ana)
    _material_web(ana, "PIEDRA34", "t", "10", None)
    _importar_web(ana)
    ruta = "/v1/produccion/pesajes-sospechosos"
    por_ticket = {f["ticket"]: f["id"] for f in ana.get(ruta).json()}
    ana.post(
        f"{ruta}/{por_ticket['TCK-006']}/resolver",
        json={
            "material_codigo": "PIEDRA34",
            "fecha": "2026-10-17",
            "neto_t": "18.0",
            "ticket": "TCK-006",
            "ahora": "2026-10-18T09:30:00",
        },
    )
    ana.post(f"{ruta}/{por_ticket['TCK-003']}/descartar", json={"ahora": "2026-10-18T09:31:00"})
    assert _contar(Movimiento) == 3  # 2 de la importación + el resuelto
    with sesion_de_instalacion() as sesion:
        assert set(sesion.scalars(select(Movimiento.usuario))) == {"Ana <ana>"}
        cerrados = {
            s.ticket: s.resuelto_por
            for s in sesion.scalars(
                select(PesajeSospechoso).where(PesajeSospechoso.estado != "pendiente")
            )
        }
    assert cerrados == {"TCK-006": "Ana <ana>", "TCK-003": "Ana <ana>"}


def test_con_clave_el_usuario_sigue_siendo_el_de_la_api_aunque_haya_cookie(ana) -> None:
    """La cabecera de clave manda: se escribe `USUARIO_API`, no la cuenta de la cookie."""
    clave = {CABECERA: crear_clave_de_prueba()}
    r = ana.cliente.post(
        "/v1/produccion/materiales",
        headers=clave,
        json={"codigo": "ARENA", "nombre": "A", "unidad_venta": "m3", "existencia_minima": "0"},
    )
    assert r.status_code == 201, r.text
    m = ana.cliente.post(
        "/v1/produccion/movimientos",
        headers=clave,
        json={
            "material_codigo": "ARENA",
            "tipo": "entrada",
            "fecha": "2026-10-01",
            "cantidad": "5",
        },
    )
    assert m.status_code == 201 and m.json()["usuario"] == USUARIO_API


# --- Contrato con la interfaz nueva (claves literales) -------------------------------------------


def test_contrato_de_existencias_claves_y_tipos_exactos(http) -> None:
    """Lo consumen Inicio y Existencias de la interfaz nueva: lista de objetos con ESTAS claves."""
    _material(http, "ARENA", "m3", "20", "1.60", "Arena lavada")
    _material(http, "PIEDRA34", "t", "10")
    _movimiento(http, "ARENA", "entrada", "2026-10-01", "100")
    _movimiento(http, "PIEDRA34", "despacho", "2026-10-02", "3")
    r = http.get("/v1/produccion/existencias")
    assert r.status_code == 200
    filas = r.json()
    assert isinstance(filas, list) and len(filas) == 2
    for fila in filas:
        assert set(fila) == {
            "codigo",
            "nombre",
            "unidad_venta",
            "existencia",
            "minima",
            "queda_poco",
            "negativa",
        }
        for clave in ("codigo", "nombre", "unidad_venta", "existencia", "minima"):
            assert isinstance(fila[clave], str), clave
        assert type(fila["queda_poco"]) is bool and type(fila["negativa"]) is bool
    assert filas == [  # por código; cantidades como texto
        {
            "codigo": "ARENA",
            "nombre": "Arena lavada",
            "unidad_venta": "m3",
            "existencia": "100",
            "minima": "20",
            "queda_poco": False,
            "negativa": False,
        },
        {
            "codigo": "PIEDRA34",
            "nombre": "Material PIEDRA34",
            "unidad_venta": "t",
            "existencia": "-3",
            "minima": "10",
            "queda_poco": True,
            "negativa": True,
        },
    ]


def test_contrato_de_materiales(http) -> None:
    _material(http, "ARENA", "m3", "20", "1.60", "Arena lavada")
    claves = {
        "id",
        "codigo",
        "nombre",
        "unidad_venta",
        "densidad_t_m3",
        "existencia_minima",
        "activo",
    }
    creado = _material(http, "GRAVA", "t", "1")
    assert creado.status_code == 201 and set(creado.json()) == claves
    listado = http.get("/v1/produccion/materiales").json()
    assert len(listado) == 2 and all(set(m) == claves for m in listado)
    arena = next(m for m in listado if m["codigo"] == "ARENA")
    assert type(arena["id"]) is int and type(arena["activo"]) is bool
    assert (arena["densidad_t_m3"], arena["existencia_minima"]) == ("1.60", "20")


def test_contrato_de_movimientos(http) -> None:
    _material(http, "ARENA", "m3", "20", "1.60")
    r = _movimiento(http, "ARENA", "entrada", "2026-10-01", "100", nota="primera")
    assert r.status_code == 201
    cuerpo = r.json()
    assert set(cuerpo) == {
        "id",
        "material_codigo",
        "fecha",
        "tipo",
        "cantidad",
        "ticket",
        "placa",
        "cliente",
        "nota",
        "origen",
        "usuario",
        "registrado",
    }
    assert (cuerpo["material_codigo"], cuerpo["fecha"], cuerpo["cantidad"]) == (
        "ARENA",
        "2026-10-01",
        "100",
    )
    assert cuerpo["ticket"] is None and cuerpo["nota"] == "primera"


def test_contrato_de_la_importacion_y_de_la_bandeja(http) -> None:
    _catalogo_del_basico(http)
    r = _importar(http, construir.xlsx_basico())
    assert r.status_code == 200
    assert set(r.json()) == {"registrados", "ya_registrados", "a_la_bandeja", "huella"}
    assert all(type(r.json()[k]) is int for k in ("registrados", "ya_registrados", "a_la_bandeja"))
    bandeja = http.get("/v1/produccion/pesajes-sospechosos").json()
    assert len(bandeja) == 4
    for fila in bandeja:
        assert set(fila) == {
            "id",
            "huella_archivo",
            "fila",
            "ticket",
            "fecha_texto",
            "placa",
            "material_texto",
            "bruto_texto",
            "tara_texto",
            "neto_texto",
            "motivo",
            "estado",
        }
        assert type(fila["id"]) is int and type(fila["fila"]) is int
        assert fila["estado"] == "pendiente"


# --- Cache-Control: no-store en lo que se lee (existencias, pesajes y materiales no se guardan) ---


@pytest.mark.parametrize(
    "ruta",
    [
        "/v1/produccion/materiales",
        "/v1/produccion/existencias",
        "/v1/produccion/existencias?a_fecha=2026-10-02",
        "/v1/produccion/pesajes-sospechosos",
    ],
)
def test_las_lecturas_de_la_arenera_no_se_guardan_en_el_navegador(http, ruta) -> None:
    r = http.get(ruta)
    assert r.status_code == 200, r.text
    assert r.headers["Cache-Control"] == "no-store"


def test_tambien_los_rechazos_de_la_arenera_van_sin_cache(rita) -> None:
    r = rita.get("/v1/produccion/materiales")  # revisa: sin permiso de operar la arenera
    assert r.status_code == 403
    assert r.headers["Cache-Control"] == "no-store"
    sin_credenciales = TestClient(app, base_url=ANFITRION, client=IP_LOCAL)
    r = sin_credenciales.get("/v1/produccion/existencias")
    assert r.status_code == 401
    assert r.headers["Cache-Control"] == "no-store"


def test_una_fecha_mala_en_existencias_tambien_va_sin_cache(http) -> None:
    r = http.get("/v1/produccion/existencias", params={"a_fecha": "no-es-fecha"})
    assert r.status_code == 422
    assert r.headers["Cache-Control"] == "no-store"


def test_un_4xx_tras_una_escritura_parcial_no_deja_nada_y_va_sin_cache(http, monkeypatch) -> None:
    """Un conflicto (409) o un archivo rechazado (422) despues de escribir deshacen la peticion
    entera: `RutaSinCache` relanza la HTTPException para que la sesion con `yield` haga rollback."""
    import api.rutas.produccion as rutas
    from produccion.inventario import Conflicto

    original = rutas.importar
    errores = {409: Conflicto("ticket repetido (ficticio)"), 422: rutas.ArchivoRechazado("malo")}
    _catalogo_del_basico(http)
    for estado, error in errores.items():

        def _escribe_y_falla(sesion, lectura, *, usuario, _error=error):
            original(sesion, lectura, usuario=usuario)
            raise _error

        monkeypatch.setattr(rutas, "importar", _escribe_y_falla)
        r = _importar(http, construir.xlsx_basico())
        assert r.status_code == estado, r.text
        assert r.headers["Cache-Control"] == "no-store"
        assert _contar(Movimiento) == 0 and _contar(PesajeSospechoso) == 0
