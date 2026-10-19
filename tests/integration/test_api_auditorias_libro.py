"""`/v1/auditorias-libro`: el historial de auditorias de «Libro de la empresa» (UC-30; RF-145/146).

Contrato EXACTO que consume el Inicio de la interfaz nueva (claves literales, escritas a mano):
`GET /v1/auditorias-libro?limite=5` es una lista de `{id, archivo, fecha, tipo, errores,
advertencias}`, las mas recientes primero; `fecha` es ISO con hora (`2026-10-18T14:03:05`). El
detalle suma el resumen completo y los hallazgos compactos. Los montos viajan como texto.

Acceso: clave de API, o cuenta que arma o revisa (`LEER_PROYECTO`); sin credenciales 401; el
administrador solo, 403. Es de solo lectura: ninguna escritura entra por aqui.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api.main import app
from fusion.historial import HallazgoCompacto, registrar_auditoria
from operacion import config
from operacion.base_datos import Destino, preparar_base
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, sesiones
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Usuario
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona

RUTA = "/v1/auditorias-libro"
NUEVA = "otra contrasena larga de prueba"
CUENTAS = {"admin": CONTRASENA, "ana": NUEVA, "rita": NUEVA}
COOKIE = "silice_sesion"
MENSAJE_SIN_SESION = "Sesión ausente o vencida: entre de nuevo con su cuenta."
MENSAJE_SIN_CLAVE = "Clave de API ausente, desconocida o revocada."
MENSAJE_PERMISO = "Su cuenta no tiene permiso para esta acción."
CLAVES_DE_LA_LISTA = {"id", "archivo", "fecha", "tipo", "errores", "advertencias"}
CLAVES_DEL_DETALLE = CLAVES_DE_LA_LISTA | {
    "usuario", "sha256", "fecha_libro", "total_libro", "total_silice", "informativos",
    "atipicos", "recortado", "hallazgos",
}
CLAVES_DEL_HALLAZGO = {"regla", "hoja", "celda", "severidad", "mensaje"}
SHA = "cd" * 32


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    """`instalacion.db` migrada con tres cuentas por el camino real (una vez por modulo)."""
    carpeta = tmp_path_factory.mktemp("plantilla_auditorias_libro")
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor(plantilla)
    sesion = abrir_sesion(motor)
    try:
        admin = administrador(sesion, carpeta)
        for login, roles in (("ana", ("arma",)), ("rita", ("revisa",))):
            usuario = persona(sesion, admin, login, roles)
            cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        for usuario in sesion.scalars(select(Usuario)):
            sesiones.cerrar_todas(sesion, usuario.id, "plantilla")
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path) -> Iterator[None]:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_plantilla, destino)
    cuentas.FRENO.reiniciar()
    yield
    cuentas.FRENO.reiniciar()


def _cliente(**extra) -> TestClient:
    return TestClient(
        app, base_url=ANFITRION, client=IP_LOCAL, raise_server_exceptions=False, **extra
    )


@pytest.fixture
def http() -> TestClient:
    return _cliente(headers={CABECERA: crear_clave_de_prueba()})


def _con_cuenta(login: str) -> TestClient:
    cliente = _cliente()
    r = cliente.post("/v1/sesion", json={"login": login, "contrasena": CUENTAS[login]})
    assert r.status_code == 200, r.text
    return cliente


def _sembrar(cuantas: int, *, tipo: str = "libro") -> None:
    """`cuantas` auditorias, una por minuto desde las 10:00 del 18-oct-2026 (la ultima, la mas
    reciente). La n-esima se llama `libro-n.xlsx`, tiene n errores y una advertencia."""
    with sesion_de_instalacion() as sesion:
        for n in range(1, cuantas + 1):
            hallazgos = [
                HallazgoCompacto("L4", "APU-02", f"G{i}", "ERROR", f"error {i}")
                for i in range(n)
            ] + [HallazgoCompacto("L2", "PRESUPUESTO", "P6", "ADVERTENCIA", "advertencia")]
            registrar_auditoria(
                sesion,
                usuario="Ana <ana>",
                tipo=tipo,
                nombre_archivo=f"libro-{n}.xlsx",
                sha256=SHA,
                fecha_libro=date(2026, 10, 1) if tipo == "libro" else None,
                total_libro=Decimal("1586.61") if tipo == "libro" else None,
                total_silice=Decimal("1500.00") if tipo == "libro" else None,
                hallazgos=hallazgos,
                ahora=datetime(2026, 10, 18, 10, 0, 0) + timedelta(minutes=n),
            )
        sesion.commit()


# --- contrato de la lista ------------------------------------------------------------------------


def test_la_lista_tiene_exactamente_las_claves_que_consume_el_inicio(http) -> None:
    _sembrar(3)
    r = http.get(RUTA, params={"limite": 5})
    assert r.status_code == 200, r.text
    assert r.json() == [
        {
            "id": 3, "archivo": "libro-3.xlsx", "fecha": "2026-10-18T10:03:00", "tipo": "libro",
            "errores": 3, "advertencias": 1,
        },
        {
            "id": 2, "archivo": "libro-2.xlsx", "fecha": "2026-10-18T10:02:00", "tipo": "libro",
            "errores": 2, "advertencias": 1,
        },
        {
            "id": 1, "archivo": "libro-1.xlsx", "fecha": "2026-10-18T10:01:00", "tipo": "libro",
            "errores": 1, "advertencias": 1,
        },
    ]
    for fila in r.json():
        assert set(fila) == CLAVES_DE_LA_LISTA
        assert isinstance(fila["id"], int) and isinstance(fila["errores"], int)


def test_la_lista_incluye_las_revisiones_de_pdf(http) -> None:
    _sembrar(1, tipo="pdf")
    [fila] = http.get(RUTA).json()
    assert fila["tipo"] == "pdf" and fila["archivo"] == "libro-1.xlsx"


def test_sin_auditorias_la_lista_es_vacia(http) -> None:
    r = http.get(RUTA)
    assert r.status_code == 200 and r.json() == []


def test_el_limite_por_omision_es_20_y_el_pedido_se_respeta(http) -> None:
    _sembrar(25)
    por_omision = http.get(RUTA).json()
    assert len(por_omision) == 20
    assert [f["id"] for f in por_omision][:3] == [25, 24, 23]
    assert [f["id"] for f in http.get(RUTA, params={"limite": 5}).json()] == [25, 24, 23, 22, 21]
    assert len(http.get(RUTA, params={"limite": 25}).json()) == 25


@pytest.mark.parametrize("limite", ["1", "100"])
def test_los_limites_extremos_se_aceptan(http, limite) -> None:
    assert http.get(RUTA, params={"limite": limite}).status_code == 200


@pytest.mark.parametrize("limite", ["0", "-1", "101", "diez", ""])
def test_un_limite_fuera_de_1_a_100_da_422(http, limite) -> None:
    assert http.get(RUTA, params={"limite": limite}).status_code == 422


# --- detalle -------------------------------------------------------------------------------------


def test_el_detalle_trae_el_resumen_y_los_hallazgos_compactos(http) -> None:
    _sembrar(2)
    r = http.get(f"{RUTA}/2")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert set(cuerpo) == CLAVES_DEL_DETALLE
    assert {k: v for k, v in cuerpo.items() if k != "hallazgos"} == {
        "id": 2, "archivo": "libro-2.xlsx", "fecha": "2026-10-18T10:02:00", "tipo": "libro",
        "errores": 2, "advertencias": 1, "informativos": 0, "atipicos": 0,
        "usuario": "Ana <ana>", "sha256": SHA, "fecha_libro": "2026-10-01",
        "total_libro": "1586.61", "total_silice": "1500.00", "recortado": False,
    }
    assert cuerpo["hallazgos"] == [
        {
            "regla": "L4", "hoja": "APU-02", "celda": "G0", "severidad": "ERROR",
            "mensaje": "error 0",
        },
        {
            "regla": "L4", "hoja": "APU-02", "celda": "G1", "severidad": "ERROR",
            "mensaje": "error 1",
        },
        {
            "regla": "L2", "hoja": "PRESUPUESTO", "celda": "P6", "severidad": "ADVERTENCIA",
            "mensaje": "advertencia",
        },
    ]
    assert all(set(h) == CLAVES_DEL_HALLAZGO for h in cuerpo["hallazgos"])


def test_el_detalle_de_un_pdf_lleva_nulos_los_totales_y_la_fecha_del_libro(http) -> None:
    _sembrar(1, tipo="pdf")
    cuerpo = http.get(f"{RUTA}/1").json()
    assert cuerpo["tipo"] == "pdf"
    assert (cuerpo["fecha_libro"], cuerpo["total_libro"], cuerpo["total_silice"]) == (
        None, None, None,
    )


def test_el_detalle_de_una_auditoria_que_no_existe_da_404(http) -> None:
    r = http.get(f"{RUTA}/99")
    assert r.status_code == 404
    assert set(r.json()) == {"detalle"} and r.json()["detalle"]


def test_un_id_que_no_es_entero_da_422(http) -> None:
    assert http.get(f"{RUTA}/abc").status_code == 422


def test_la_ruta_es_de_solo_lectura(http) -> None:
    _sembrar(1)
    assert http.post(RUTA, json={}).status_code == 405
    assert http.delete(f"{RUTA}/1").status_code == 405
    assert len(http.get(RUTA).json()) == 1


# --- acceso: clave de API o cuenta que arma o revisa ---------------------------------------------


@pytest.mark.parametrize("ruta", [RUTA, f"{RUTA}/1"])
def test_sin_credenciales_401_y_con_clave_mala_401(ruta) -> None:
    r = _cliente().get(ruta)
    assert r.status_code == 401 and r.json() == {"detalle": MENSAJE_SIN_SESION}
    mala = _cliente(headers={CABECERA: "AB12CD34.no-es-la-clave"}).get(ruta)
    assert mala.status_code == 401 and mala.json() == {"detalle": MENSAJE_SIN_CLAVE}


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_quien_arma_o_revisa_lee_el_historial(login) -> None:
    _sembrar(2)
    cliente = _con_cuenta(login)
    r = cliente.get(RUTA, params={"limite": 5})
    assert r.status_code == 200 and [f["id"] for f in r.json()] == [2, 1]
    assert cliente.get(f"{RUTA}/1").status_code == 200


def test_el_administrador_solo_no_lee_el_historial() -> None:
    _sembrar(1)
    cliente = _con_cuenta("admin")
    for ruta in (RUTA, f"{RUTA}/1"):
        r = cliente.get(ruta)
        assert r.status_code == 403 and r.json() == {"detalle": MENSAJE_PERMISO}
