"""RM-6: `POST /v1/libros/auditoria` y `POST /v1/libros/pdf` dejan su resultado en el historial
(UC-25, UC-30; RF-142 a RF-144, RNF-28).

Oráculos, ninguno sale del código bajo prueba:

- Libro limpio: fecha de la PORTADA «Julio 2026» = 2026-07-31 (fin de mes), total general
  5055.52157 en el libro y en Sílice (memoria de cálculo a mano de
  `tests/fixtures/libros_empresa.py`),
  sin errores ni advertencias y dos hallazgos informativos (R2 y R7).
- El usuario: la cuenta de la sesión web (`Nombre <login>`, RF-82) o, con la clave de API,
  `api (clave de API)` (RT-S4-4, igual que `/v1/produccion`).
- El historial lo lee `GET /v1/auditorias-libro`, no la base: se comprueba el contrato público.
- Si guardar falla, la auditoría NO se tumba (RF-144): responde 200 con el mismo informe, el
  campo `aviso_historial` lleva el aviso y no queda fila alguna (todo o nada).
- Ni el libro ni el PDF se guardan (RNF-28): la base de la instalación solo trae sus nombres y su
  huella.

El PDF se prueba con un doble de `auditar_pdf_simple` (leer PDF necesita el extra `pdf`, que no
siempre está); lo que se ejerce aquí es la ruta, no el lector.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from adapters.hoja_empresa.modelo import FilaHallazgo
from api.main import app
from fusion.proceso import ResultadoPdf
from operacion import config
from operacion.base_datos import Destino, preparar_base
from seguridad import cuentas
from seguridad.base import abrir_sesion, crear_motor
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona
from tests.fixtures.libros_empresa import libro_limpio

FECHA_DEVOLUCION = "2026-10-13"
NUEVA = "otra contrasena larga de prueba"
COOKIE = "silice_sesion"
CABECERA_CSRF = "X-Silice-CSRF"
SHA_PDF = "ef" * 32
AVISO = "No se pudo guardar la auditoría en el historial."
HISTORIAL = "/v1/auditorias-libro"


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    carpeta = tmp_path_factory.mktemp("plantilla_libros_historial")
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor(plantilla)
    sesion = abrir_sesion(motor)
    try:
        admin = administrador(sesion, carpeta)
        usuario = persona(sesion, admin, "ana", ("arma",))
        cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_migrada, destino)
    cuentas.FRENO.reiniciar()
    yield
    cuentas.FRENO.reiniciar()


@pytest.fixture(scope="module")
def limpio():
    return libro_limpio()


@pytest.fixture
def historial() -> TestClient:
    """Un lector del historial independiente de la sesión de la prueba (otra conexión)."""
    return TestClient(
        app,
        base_url=ANFITRION,
        client=IP_LOCAL,
        headers={CABECERA: crear_clave_de_prueba()},
        raise_server_exceptions=False,
    )


def _auditar(cliente, datos: bytes, nombre: str = "libro.xlsx", **extra):
    return cliente.post(
        "/v1/libros/auditoria",
        files={"libro": (nombre, datos)},
        data={"fecha_devolucion": FECHA_DEVOLUCION},
        **extra,
    )


def _pdf(cliente, nombre: str = "presupuesto.pdf", **extra):
    return cliente.post("/v1/libros/pdf", files={"pdf": (nombre, b"%PDF-1.4 ficticio")}, **extra)


def _doble_de_pdf(monkeypatch, filas: tuple[FilaHallazgo, ...] = ()) -> None:
    leido = SimpleNamespace(
        numero="001",
        fecha="18/05/2026",
        computos=[],
        presupuesto=[],
        total_computos=None,
        total_impreso=None,
        notas=[],
    )
    resultado = ResultadoPdf(pdf=leido, hallazgos=(), hallazgos_tabla=filas, sha256=SHA_PDF)  # type: ignore[arg-type]
    monkeypatch.setattr("api.rutas.libros.auditar_pdf_simple", lambda datos, nombre: resultado)


def _filas_guardadas(historial) -> list[dict]:
    lista = historial.get(HISTORIAL, params={"limite": 100})
    assert lista.status_code == 200, lista.text
    return lista.json()


def _guardado_roto(*args, **kwargs):
    raise sqlite3.OperationalError("disco lleno")


# --- Éxito: la auditoría de un libro deja su fila ------------------------------------------------


def test_auditar_un_libro_deja_una_fila_con_su_resumen(cliente, historial, limpio) -> None:
    r = _auditar(cliente, limpio.datos, nombre=r"obras\libro.xlsx")
    assert r.status_code == 200, r.text
    assert r.json()["aviso_historial"] is None
    [fila] = _filas_guardadas(historial)
    assert (fila["archivo"], fila["tipo"], fila["errores"], fila["advertencias"]) == (
        "libro.xlsx",
        "libro",
        0,
        0,
    )
    d = historial.get(f"{HISTORIAL}/{fila['id']}").json()
    assert d["usuario"] == "api (clave de API)"
    assert d["sha256"] == hashlib.sha256(limpio.datos).hexdigest()
    assert d["fecha_libro"] == "2026-07-31"
    assert (Decimal(d["total_libro"]), Decimal(d["total_silice"])) == (Decimal("5055.52157"),) * 2
    assert d["informativos"] == 2 and d["atipicos"] == 0 and d["recortado"] is False
    assert sorted(h["regla"] for h in d["hallazgos"]) == ["R2", "R7"]


def test_el_historial_guarda_tantos_hallazgos_como_muestra_el_informe(
    cliente, historial, limpio
) -> None:
    informe = _auditar(cliente, limpio.datos).json()
    [fila] = _filas_guardadas(historial)
    d = historial.get(f"{HISTORIAL}/{fila['id']}").json()
    assert len(d["hallazgos"]) == len(informe["hallazgos"])
    assert [h["regla"] for h in d["hallazgos"]] == [h["codigo"] for h in informe["hallazgos"]]


def test_repetir_la_auditoria_deja_otra_fila_sin_deduplicar(cliente, historial, limpio) -> None:
    assert _auditar(cliente, limpio.datos).status_code == 200
    assert _auditar(cliente, limpio.datos).status_code == 200
    filas = _filas_guardadas(historial)
    assert len(filas) == 2 and filas[0]["id"] > filas[1]["id"]


def test_la_respuesta_solo_suma_el_aviso_al_contrato(cliente, limpio) -> None:
    r = _auditar(cliente, limpio.datos).json()
    assert set(r) == {
        "libro", "fecha_libro", "fecha_devolucion", "cumple", "por_severidad", "totales_libro",
        "totales_silice", "indicadores", "partidas_con_omision", "hallazgos", "alertas",
        "trazabilidad", "metadatos", "aviso_historial",
    }  # fmt: skip


def test_con_sesion_web_el_usuario_es_la_cuenta(cliente, historial, limpio) -> None:
    web = TestClient(app, base_url=ANFITRION, client=IP_LOCAL, raise_server_exceptions=False)
    entrada = web.post("/v1/sesion", json={"login": "ana", "contrasena": NUEVA})
    assert entrada.status_code == 200, entrada.text
    ficha = entrada.cookies.get(COOKIE)
    csrf = hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()
    r = _auditar(web, limpio.datos, headers={CABECERA_CSRF: csrf, "Origin": ANFITRION})
    assert r.status_code == 200, r.text
    [fila] = _filas_guardadas(historial)
    assert historial.get(f"{HISTORIAL}/{fila['id']}").json()["usuario"] == "Ana <ana>"


# --- Éxito: la revisión de un PDF simple ---------------------------------------------------------


def test_revisar_un_pdf_deja_una_fila_de_tipo_pdf(cliente, historial, monkeypatch) -> None:
    fila_l10 = FilaHallazgo("L10", "ERROR", "La fila 1 no cuadra", "F3", None, "informado")
    _doble_de_pdf(monkeypatch, (fila_l10,))
    r = _pdf(cliente, nombre="presupuesto.pdf")
    assert r.status_code == 200, r.text
    assert r.json()["aviso_historial"] is None
    [fila] = _filas_guardadas(historial)
    assert (fila["archivo"], fila["tipo"], fila["errores"], fila["advertencias"]) == (
        "presupuesto.pdf",
        "pdf",
        1,
        0,
    )
    d = historial.get(f"{HISTORIAL}/{fila['id']}").json()
    assert d["sha256"] == SHA_PDF and d["usuario"] == "api (clave de API)"
    assert (d["fecha_libro"], d["total_libro"], d["total_silice"]) == (None, None, None)
    assert d["hallazgos"] == [
        {
            "regla": "L10", "hoja": "", "celda": "F3", "severidad": "ERROR",
            "mensaje": "La fila 1 no cuadra",
        }
    ]  # fmt: skip


# --- Lo que no se guarda -------------------------------------------------------------------------


def test_devolver_o_replicar_no_registra_nada(cliente, historial, limpio) -> None:
    devolucion = cliente.post(
        "/v1/libros/devolucion",
        files={"libro": ("libro.xlsx", limpio.datos)},
        data={"fecha_devolucion": FECHA_DEVOLUCION},
    )
    replica = cliente.post("/v1/libros/replica", files={"libro": ("libro.xlsx", limpio.datos)})
    assert devolucion.status_code == 200 and replica.status_code == 200
    assert _filas_guardadas(historial) == []


def test_una_auditoria_rechazada_no_deja_fila(cliente, historial, limpio) -> None:
    assert _auditar(cliente, limpio.datos, nombre="libro.txt").status_code == 415
    assert _auditar(cliente, b"no es un xlsx").status_code == 422
    assert _filas_guardadas(historial) == []


def test_el_libro_no_se_guarda_solo_su_nombre_y_huella(cliente, limpio) -> None:
    assert _auditar(cliente, limpio.datos).status_code == 200
    with closing(sqlite3.connect(config.ruta_instalacion())) as con:
        columnas = {c[1]: c[2].upper() for c in con.execute("PRAGMA table_info(auditoria_libro)")}
        [(tamano,)] = con.execute("SELECT length(hallazgos) FROM auditoria_libro")
    assert "BLOB" not in columnas.values()
    assert tamano < len(limpio.datos)


# --- Si guardar falla: la auditoría sigue (RF-144) y no queda nada a medias ----------------------


def test_si_guardar_falla_el_libro_se_audita_igual_con_aviso(
    cliente, historial, limpio, monkeypatch, caplog
) -> None:
    esperado = _auditar(cliente, limpio.datos, nombre="secreto-ficticio.xlsx").json()
    monkeypatch.setattr("api.rutas.libros.registrar_resultado", _guardado_roto)
    caplog.set_level(logging.ERROR)
    r = _auditar(cliente, limpio.datos, nombre="secreto-ficticio.xlsx")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["aviso_historial"] == AVISO
    assert cuerpo == esperado | {"aviso_historial": AVISO}
    assert len(_filas_guardadas(historial)) == 1  # solo la primera, la sana
    registro = "\n".join(m.getMessage() for m in caplog.records if m.levelno >= logging.ERROR)
    assert "OperationalError" in registro  # el fallo queda en el registro del servidor
    assert "secreto-ficticio" not in registro and "disco lleno" not in registro


def test_si_guardar_falla_el_pdf_se_revisa_igual_con_aviso(cliente, historial, monkeypatch) -> None:
    _doble_de_pdf(monkeypatch)
    monkeypatch.setattr("api.rutas.libros.registrar_resultado_pdf", _guardado_roto)
    r = _pdf(cliente)
    assert r.status_code == 200, r.text
    assert r.json()["aviso_historial"] == AVISO and r.json()["pdf"]["sha256"] == SHA_PDF
    assert _filas_guardadas(historial) == []


def test_todo_o_nada_un_fallo_tras_insertar_no_deja_la_fila(
    cliente, historial, limpio, monkeypatch
) -> None:
    from fusion import historial as servicio

    def inserta_y_falla(sesion, resultado, *, usuario, ahora):
        servicio.registrar_resultado(sesion, resultado, usuario=usuario, ahora=ahora)
        raise sqlite3.OperationalError("falla despues de insertar")

    monkeypatch.setattr("api.rutas.libros.registrar_resultado", inserta_y_falla)
    r = _auditar(cliente, limpio.datos)
    assert r.status_code == 200 and r.json()["aviso_historial"] == AVISO
    assert _filas_guardadas(historial) == []


def test_si_la_base_de_la_instalacion_no_abre_la_auditoria_sigue(
    cliente, limpio, monkeypatch
) -> None:
    monkeypatch.setattr("api.rutas.libros.sesion_de_instalacion", _guardado_roto)
    r = _auditar(cliente, limpio.datos)
    assert r.status_code == 200 and r.json()["aviso_historial"] == AVISO


def test_la_puerta_de_los_libros_se_declara_una_sola_vez() -> None:
    """Una sola instancia de `exigir_clave_o_sesion(LEER_PROYECTO)` para el router (en `api.main`)
    y para saber quien audita: FastAPI no cachea instancias distintas y evaluaria la puerta dos
    veces por peticion."""
    from fastapi.dependencies.utils import get_dependant

    from api.rutas import libros

    incluido = next(
        r for r in app.router.routes if getattr(r, "original_router", None) is libros.router
    )
    en_main = [d.dependency for d in incluido.include_context.dependencies]
    en_usuario = [d.call for d in get_dependant(path="/", call=libros._usuario).dependencies]
    assert en_main == [libros.ACCESO_LIBROS]
    assert en_usuario == [libros.ACCESO_LIBROS]
