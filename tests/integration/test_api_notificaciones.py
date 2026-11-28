"""`/v1/notificaciones`: notificaciones por persona con retención de 30 días (C11, servidor).

Contrato EXACTO (oráculos escritos a mano):
- `GET /v1/notificaciones` -> 200 `{notificaciones, sin_leer, retencion_dias, maximo}`, con cada
  notificación `{id, gravedad, titulo, detalle, enlace, creada, leida}` (`enlace` es `{texto, ruta}`
  o `null`). Las más nuevas primero, tope 200, descarta y borra las de más de 30 días.
- `POST /v1/notificaciones` `{gravedad, titulo, detalle?, enlace?}` -> 201 con la notificación.
- `POST /v1/notificaciones/leidas` `{ids}` o `{todas: true}` -> 200 `{marcadas, sin_leer}`.

Permisos y seguridad:
- 401 sin sesión; 403 con clave de API (no es una persona); 403 en POST sin CSRF o con `Origin`
  ajeno; toda respuesta lleva `Cache-Control: no-store`.
- Cada persona ve y marca solo las suyas (Ana no ve ni marca las de Rita).
- `enlace.ruta` insegura (`http://`, `//evil`, `javascript:`) -> 422 sin guardar.

También verifica la migración `ins_0014_notificacion` (subida desde `ins_0013`, columnas, índice
`(usuario_id, creada)`, `CHECK` de gravedad, FK a `usuario.id`, bajada y adopción). Datos ficticios.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from api import dependencias
from api.main import app
from operacion import config
from operacion.base_datos import (
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
)
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Notificacion, Usuario
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    ORIGEN,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

RUTA = "/v1/notificaciones"
RUTA_LEIDAS = "/v1/notificaciones/leidas"
CLAVES_LISTA = {"notificaciones", "sin_leer", "retencion_dias", "maximo"}
CLAVES_ITEM = {"id", "gravedad", "titulo", "detalle", "enlace", "creada", "leida"}
AJENO = {"Origin": "http://otro.sitio.example"}
MOMENTO = datetime(2026, 11, 26, 14, 0, 0)
MAXIMO_DEL_TOPE = 200  # el tope por cuenta (C11), escrito a mano


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("notificaciones_api"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    yield
    dependencias.cerrar_motores()


def _en_instalacion(hacer):
    motor = crear_motor(config.ruta_instalacion())
    sesion = abrir_sesion(motor)
    try:
        resultado = hacer(sesion)
        sesion.commit()
        return resultado
    finally:
        sesion.close()
        motor.dispose()


def _usuario_id(login: str) -> int:
    uid = _en_instalacion(lambda s: s.scalar(select(Usuario.id).where(Usuario.login == login)))
    assert uid is not None
    return uid


# --- contrato y flujo completo -------------------------------------------------------------------


def test_crear_listar_y_marcar_leidas_con_contrato_exacto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reloj = [MOMENTO - timedelta(minutes=5)]
    monkeypatch.setattr("api.rutas.notificaciones.ahora", lambda: reloj[0])
    ana, ficha = con_cuenta(app, "ana")

    r1 = ana.post(
        RUTA,
        json={
            "gravedad": "listo",
            "titulo": "Versión guardada",
            "detalle": "Se guardó VIV-002.",
            "enlace": {"texto": "Abrir versiones", "ruta": "/obras/1/versiones"},
        },
        headers=protegida(ficha),
    )
    assert r1.status_code == 201, r1.text
    assert r1.headers["cache-control"] == "no-store"
    item1 = r1.json()
    assert set(item1) == CLAVES_ITEM
    assert item1["gravedad"] == "listo"
    assert item1["titulo"] == "Versión guardada"
    assert item1["detalle"] == "Se guardó VIV-002."
    assert item1["enlace"] == {"texto": "Abrir versiones", "ruta": "/obras/1/versiones"}
    assert item1["creada"] == (MOMENTO - timedelta(minutes=5)).isoformat(timespec="seconds")
    assert item1["leida"] is False

    reloj[0] = MOMENTO
    r2 = ana.post(
        RUTA,
        json={"gravedad": "advertencia", "titulo": "Precio sin lista vigente"},
        headers=protegida(ficha),
    )
    assert r2.status_code == 201, r2.text
    item2 = r2.json()
    assert item2["detalle"] == ""
    assert item2["enlace"] is None

    lista = ana.get(RUTA)
    assert lista.status_code == 200, lista.text
    assert lista.headers["cache-control"] == "no-store"
    cuerpo = lista.json()
    assert set(cuerpo) == CLAVES_LISTA
    assert cuerpo["sin_leer"] == 2
    assert cuerpo["retencion_dias"] == 30
    assert cuerpo["maximo"] == 200
    # Más nueva primero.
    assert [n["id"] for n in cuerpo["notificaciones"]] == [item2["id"], item1["id"]]

    marcar_una = ana.post(
        RUTA_LEIDAS,
        json={"ids": [item1["id"]]},
        headers=protegida(ficha),
    )
    assert marcar_una.status_code == 200, marcar_una.text
    assert marcar_una.headers["cache-control"] == "no-store"
    assert marcar_una.json() == {"marcadas": 1, "sin_leer": 1}

    marcar_todas = ana.post(RUTA_LEIDAS, json={"todas": True}, headers=protegida(ficha))
    assert marcar_todas.status_code == 200, marcar_todas.text
    assert marcar_todas.json() == {"marcadas": 1, "sin_leer": 0}
    assert all(n["leida"] for n in ana.get(RUTA).json()["notificaciones"])


# --- aislamiento entre cuentas -------------------------------------------------------------------


def test_otra_cuenta_no_ve_ni_marca_mis_notificaciones() -> None:
    ana, ficha_ana = con_cuenta(app, "ana")
    rita, ficha_rita = con_cuenta(app, "rita")

    creada_ana = ana.post(
        RUTA,
        json={"gravedad": "info", "titulo": "Mensaje privado de Ana"},
        headers=protegida(ficha_ana),
    ).json()
    creada_rita = rita.post(
        RUTA,
        json={"gravedad": "error", "titulo": "Error privado de Rita"},
        headers=protegida(ficha_rita),
    ).json()

    de_ana = ana.get(RUTA).json()["notificaciones"]
    de_rita = rita.get(RUTA).json()["notificaciones"]
    assert [n["id"] for n in de_ana] == [creada_ana["id"]]
    assert [n["id"] for n in de_rita] == [creada_rita["id"]]

    # Ana intenta marcar la de Rita por id: 0 marcadas y la de Rita sigue sin leer.
    intento = ana.post(
        RUTA_LEIDAS,
        json={"ids": [creada_rita["id"]]},
        headers=protegida(ficha_ana),
    )
    assert intento.status_code == 200
    assert intento.json() == {"marcadas": 0, "sin_leer": 1}
    assert rita.get(RUTA).json()["notificaciones"][0]["leida"] is False

    # Ana marca todas las suyas: la de Rita sigue intacta.
    ana.post(RUTA_LEIDAS, json={"todas": True}, headers=protegida(ficha_ana))
    assert rita.get(RUTA).json()["notificaciones"][0]["leida"] is False


# --- retención de 30 días y tope por API ---------------------------------------------------------


def test_retencion_de_30_dias_exactos_y_borrado_en_get(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("api.rutas.notificaciones.ahora", lambda: MOMENTO)
    ana_id = _usuario_id("ana")
    _en_instalacion(
        lambda s: s.add_all(
            [
                Notificacion(
                    usuario_id=ana_id,
                    gravedad="info",
                    titulo="Vencida por un segundo",
                    detalle="",
                    enlace_texto="",
                    enlace_ruta="",
                    creada=MOMENTO - timedelta(days=30, seconds=1),
                    leida=False,
                ),
                Notificacion(
                    usuario_id=ana_id,
                    gravedad="listo",
                    titulo="Exactamente 30 dias",
                    detalle="",
                    enlace_texto="",
                    enlace_ruta="",
                    creada=MOMENTO - timedelta(days=30),
                    leida=False,
                ),
            ]
        )
    )

    ana, _ = con_cuenta(app, "ana")
    r = ana.get(RUTA)
    assert r.status_code == 200
    titulos = [n["titulo"] for n in r.json()["notificaciones"]]
    assert titulos == ["Exactamente 30 dias"]

    en_base = _en_instalacion(
        lambda s: list(
            s.scalars(select(Notificacion.titulo).where(Notificacion.usuario_id == ana_id))
        )
    )
    assert en_base == ["Exactamente 30 dias"]


def test_tope_de_200_al_listar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("api.rutas.notificaciones.ahora", lambda: MOMENTO)
    ana_id = _usuario_id("ana")
    _en_instalacion(
        lambda s: s.add_all(
            [
                Notificacion(
                    usuario_id=ana_id,
                    gravedad="info",
                    titulo=f"Aviso {i}",
                    detalle="",
                    enlace_texto="",
                    enlace_ruta="",
                    creada=MOMENTO - timedelta(seconds=205 - i),
                    leida=False,
                )
                for i in range(205)
            ]
        )
    )
    ana, _ = con_cuenta(app, "ana")
    cuerpo = ana.get(RUTA).json()
    assert len(cuerpo["notificaciones"]) == 200
    assert cuerpo["notificaciones"][0]["titulo"] == "Aviso 204"
    assert cuerpo["notificaciones"][-1]["titulo"] == "Aviso 5"


# --- validación de rutas inseguras y entradas malas ----------------------------------------------


@pytest.mark.parametrize(
    "ruta_insegura",
    [
        "http://ejemplo.com/x",
        "https://ejemplo.com/x",
        "//evil.example/x",
        "javascript:alert(1)",
        "/\\evil.example",
    ],
)
def test_enlace_con_ruta_insegura_da_422_sin_cache_y_no_guarda(ruta_insegura: str) -> None:
    ana, ficha = con_cuenta(app, "ana")
    r = ana.post(
        RUTA,
        json={
            "gravedad": "info",
            "titulo": "Enlace sospechoso",
            "enlace": {"texto": "Abrir", "ruta": ruta_insegura},
        },
        headers=protegida(ficha),
    )
    assert r.status_code == 422, r.text
    assert r.headers["cache-control"] == "no-store"
    assert "detalle" in r.json()
    assert ana.get(RUTA).json()["notificaciones"] == []


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"gravedad": "critico", "titulo": "X"},
        {"gravedad": "info", "titulo": "   "},
        {"gravedad": "info", "titulo": "x" * 201},
        {"gravedad": "info", "titulo": "OK", "detalle": "d" * 1001},
    ],
)
def test_entradas_invalidas_en_post_dan_422_sin_cache(cuerpo: dict) -> None:
    ana, ficha = con_cuenta(app, "ana")
    r = ana.post(RUTA, json=cuerpo, headers=protegida(ficha))
    assert r.status_code == 422
    assert r.headers["cache-control"] == "no-store"


def test_marcar_leidas_invalido_da_422_sin_cache() -> None:
    ana, ficha = con_cuenta(app, "ana")
    for cuerpo in ({}, {"ids": [1], "todas": True}, {"ids": [0]}):
        r = ana.post(RUTA_LEIDAS, json=cuerpo, headers=protegida(ficha))
        assert r.status_code == 422
        assert r.headers["cache-control"] == "no-store"
        assert "detalle" in r.json()


# --- permisos, clave de API, CSRF y Origin -------------------------------------------------------


def test_sin_sesion_da_401_y_con_clave_de_api_da_403() -> None:
    for metodo, ruta in (("GET", RUTA), ("POST", RUTA), ("POST", RUTA_LEIDAS)):
        sin_nada = cliente(app).request(metodo, ruta, json={}, headers={"Origin": ORIGEN})
        assert sin_nada.status_code == 401
        assert sin_nada.headers["cache-control"] == "no-store"

        con_clave = cliente(app).request(
            metodo,
            ruta,
            json={},
            headers={CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN},
        )
        assert con_clave.status_code == 403
        assert con_clave.headers["cache-control"] == "no-store"
        assert "cuenta" in con_clave.json()["detalle"]


def test_escrituras_exigen_csrf_y_origin_propio() -> None:
    ana, ficha = con_cuenta(app, "ana")
    cuerpo = {"gravedad": "info", "titulo": "Sin CSRF"}
    for ruta, payload in ((RUTA, cuerpo), (RUTA_LEIDAS, {"todas": True})):
        sin_csrf = ana.post(ruta, json=payload, headers={"Origin": ORIGEN})
        assert sin_csrf.status_code == 403
        assert sin_csrf.headers["cache-control"] == "no-store"

        cabeceras = protegida(ficha, origen=AJENO["Origin"])
        origen_ajeno = ana.post(ruta, json=payload, headers=cabeceras)
        assert origen_ajeno.status_code == 403
        assert origen_ajeno.headers["cache-control"] == "no-store"


# --- migración ins_0014_notificacion -------------------------------------------------------------


def test_migracion_ins_0014_subida_restricciones_indice_bajada_y_adopcion(
    tmp_path: Path,
) -> None:
    # Hasta `ins_0014` (desde C11b la cabeza es `ins_0015`, que agrega `clave_evento`: lo prueba
    # `test_migracion_notificacion_por_evento.py`).
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, "ins_0013_solicitud_cuenta")
    with closing(sqlite3.connect(base)) as c:
        c.execute(
            "INSERT INTO usuario (login, nombre, huella_clave, roles, activo, debe_cambiar_clave, "
            "restablecida_por_admin, creado, creado_por) VALUES ('ana', 'Ana', 'h', 'arma', 1, 0, "
            "0, '2026-11-20 08:00:00', 'admin')"
        )
        c.commit()

    aplicar_revisiones(base, Destino.INSTALACION, "ins_0014_notificacion")
    with closing(sqlite3.connect(base)) as c:
        c.execute("PRAGMA foreign_keys = ON")
        cols = [f[1] for f in c.execute("PRAGMA table_info(notificacion)")]
        assert cols == [
            "id",
            "usuario_id",
            "gravedad",
            "titulo",
            "detalle",
            "enlace_texto",
            "enlace_ruta",
            "creada",
            "leida",
        ]
        indices = {f[1] for f in c.execute("PRAGMA index_list(notificacion)")}
        assert "ix_notificacion_usuario_creada" in indices
        # CHECK de gravedad y FK a usuario.id.
        c.execute(
            "INSERT INTO notificacion (usuario_id, gravedad, titulo, detalle, enlace_texto, "
            "enlace_ruta, creada, leida) VALUES (1, 'listo', 'OK', '', '', '', "
            "'2026-11-26 10:00:00', 0)"
        )
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            c.execute(
                "INSERT INTO notificacion (usuario_id, gravedad, titulo, detalle, enlace_texto, "
                "enlace_ruta, creada, leida) VALUES (1, 'critico', 'Mala', '', '', '', "
                "'2026-11-26 10:00:00', 0)"
            )
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            c.execute(
                "INSERT INTO notificacion (usuario_id, gravedad, titulo, detalle, enlace_texto, "
                "enlace_ruta, creada, leida) VALUES (999, 'info', 'Ajena', '', '', '', "
                "'2026-11-26 10:00:00', 0)"
            )
        c.commit()

    deshacer_revisiones(base, Destino.INSTALACION, "ins_0013_solicitud_cuenta")
    with closing(sqlite3.connect(base)) as c:
        tablas = {n for (n,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "notificacion" not in tablas
        assert c.execute("SELECT login FROM usuario").fetchall() == [("ana",)]

    aplicar_revisiones(base, Destino.INSTALACION, "ins_0014_notificacion")
    with closing(sqlite3.connect(base)) as c:
        tablas = {n for (n,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "notificacion" in tablas


# --- revisión de seguridad T5 ---------------------------------------------------------------------


def test_un_id_que_no_cabe_en_el_integer_de_sqlite_da_422_sin_hablar_de_importes() -> None:
    """T5, hallazgo 3: `ids` enormes se rechazan al validar, no al desbordar en SQLite."""
    ana, ficha = con_cuenta(app, "ana")
    r = ana.post(RUTA_LEIDAS, json={"ids": [10**30]}, headers=protegida(ficha))
    assert r.status_code == 422, r.text
    assert "importe" not in r.text
    assert set(r.json()) == {"detalle"}


def test_el_422_de_forma_no_repite_lo_enviado() -> None:
    """T5, hallazgo 4: el router usa `RutaSinEco`; un título de 3000 caracteres da 422 con
    `detalle` y sin el texto enviado."""
    ana, ficha = con_cuenta(app, "ana")
    titulo = "secreto-" + "t" * 2992
    r = ana.post(RUTA, json={"gravedad": "info", "titulo": titulo}, headers=protegida(ficha))
    assert r.status_code == 422
    assert r.headers["cache-control"] == "no-store"
    assert "secreto-" not in r.text
    assert set(r.json()) == {"detalle"}


def test_las_del_front_no_empujan_fuera_un_aviso_del_servidor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T5, hallazgo 5: el tope de 200 poda primero las que crea el front (`clave_evento` nula);
    un aviso por evento del servidor (p. ej. `por_dictaminar`) sobrevive a 200 POST."""
    monkeypatch.setattr("api.rutas.notificaciones.ahora", lambda: MOMENTO)
    ana_id = _usuario_id("ana")
    _en_instalacion(
        lambda s: s.add(
            Notificacion(
                usuario_id=ana_id,
                gravedad="info",
                titulo="VIV-001 espera su dictamen",
                detalle="",
                enlace_texto="",
                enlace_ruta="",
                creada=MOMENTO - timedelta(hours=1),
                leida=False,
                clave_evento="aprobacion:vivienda.db:1:VIV-001:enviada",
            )
        )
    )
    ana, ficha = con_cuenta(app, "ana")
    for i in range(MAXIMO_DEL_TOPE):
        hecha = ana.post(
            RUTA, json={"gravedad": "listo", "titulo": f"Del front {i}"}, headers=protegida(ficha)
        )
        assert hecha.status_code == 201, hecha.text
    titulos = [n["titulo"] for n in ana.get(RUTA).json()["notificaciones"]]
    assert len(titulos) == MAXIMO_DEL_TOPE
    assert "VIV-001 espera su dictamen" in titulos
    assert "Del front 0" not in titulos and "Del front 199" in titulos
