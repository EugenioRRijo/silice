"""`GET /v1/obras/pendientes/todas`: los pendientes de todas las carpetas (rediseño F3, T1).

Carpetas ficticias como en `test_api_obras_todas.py`: la de la empresa (`silice.db`) con «Edificio
Central»; «Carpeta Norte» con «Galpón» y «Clínica»; «Carpeta Sur» con «Vialidad». Las fuentes de
la mesa se reemplazan por fuentes falsas que leen la tabla `proyecto` (un texto por obra y grupo,
escrito a mano). Oráculos a mano: la forma del cuerpo, el orden (bloquea primero) y el alcance por
rol: «arma» (`EDITAR_HOJA`) ve todo; «revisa» (solo `APROBAR_VERSION`) ve únicamente lo que espera
su dictamen, nunca «devuelta», precios ni calidad (foco de revisión 1); sin ninguno de los dos
permisos, la lista va vacía. Con la clave de API, la carpeta del proceso con alcance «todo».
Las carpetas son las de `GET /v1/obras/todas`: con `ABRIR_CARPETA` (arma, revisa y administrador;
enmienda 2026-11-05, decisión de Eugenio) todas; sin él, solo la abierta.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import app
from aplicacion import mesa
from aplicacion.mesa import Pendiente, Siguiente
from core import models
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import permisos, sesiones
from tests.fixtures.carpetas_trabajo import arbol
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)

NORTE, SUR, EMPRESA = "Carpeta Norte.db", "Carpeta Sur.db", "silice.db"
OBRAS = {
    EMPRESA: ["Edificio Central"],
    NORTE: ["Galpón", "Clínica"],
    SUR: ["Vialidad"],
}
VER_EL_ENVIO = Siguiente("Ver el envío", "aprobar")
ABRIR_EL_PRESUPUESTO = Siguiente("Abrir el presupuesto", "hoja")
ACTUALIZAR = Siguiente("Actualizar precios", "actualizacion")
ESCENARIO: dict[tuple[str, str], tuple[str, Siguiente]] = {
    ("aprobar", "Vialidad"): ("V1 espera dictamen", VER_EL_ENVIO),
    ("aprobar", "Galpón"): ("V2 devuelta: falta acero", ABRIR_EL_PRESUPUESTO),
    ("precios", "Clínica"): ("Precios viejos", ACTUALIZAR),
    ("calidad", "Edificio Central"): ("Hallazgo grave", ABRIR_EL_PRESUPUESTO),
}


def _fuente_falsa(grupo: str):
    def fuente(sesion, hoy):
        obras = sesion.scalars(select(models.Proyecto).order_by(models.Proyecto.id)).all()
        return [
            Pendiente(str(o.id), o.nombre, *ESCENARIO[(grupo, o.nombre)])
            for o in obras
            if (grupo, o.nombre) in ESCENARIO
        ]

    return fuente


@pytest.fixture
def _fuentes_falsas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mesa, "FUENTES", {g: (_fuente_falsa(g),) for g, _ in mesa.GRUPOS})


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_pendientes_todas")
    plantillas = {"instalacion": plantilla_con_cuentas(carpeta)}
    for nombre, obras in OBRAS.items():
        ruta = carpeta / nombre
        preparar_base(ruta)
        with closing(sqlite3.connect(ruta)) as conexion:
            for n, obra in enumerate(obras, 1):
                conexion.execute(
                    "INSERT INTO proyecto (id, nombre, descripcion, dominio) VALUES (?, ?, '', '')",
                    (n, obra),
                )
            conexion.commit()
            conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        plantillas[nombre] = ruta
    return plantillas


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in OBRAS:
        (carpeta / nombre).write_bytes(_plantillas[nombre].read_bytes())
    caso_web.olvidar_todo()
    yield carpeta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _abrir(ficha: str, nombre: str) -> None:
    caso_web.fijar(sesiones.huella_de(ficha), config.carpeta_casos() / nombre)


def _filas(cuerpo: dict) -> list[tuple[str | None, str, str, str]]:
    return [(f["carpeta"], f["obra"], f["grupo"], f["urgencia"]) for f in cuerpo["pendientes"]]


# Lo que dicen las fuentes falsas, en el orden que manda la ruta (bloquea primero).
VIALIDAD = (SUR, "Vialidad", "aprobar", "bloquea")
GALPON = (NORTE, "Galpón", "aprobar", "bloquea")
CENTRAL = (None, "Edificio Central", "calidad", "aviso")
CLINICA = (NORTE, "Clínica", "precios", "aviso")


@pytest.mark.usefixtures("_fuentes_falsas")
def test_forma_de_la_respuesta() -> None:
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.get("/v1/obras/pendientes/todas")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"pendientes", "carpetas_omitidas"}
    assert cuerpo["carpetas_omitidas"] == 0
    assert cuerpo["pendientes"][0] == {
        "carpeta": NORTE,
        "obra_id": 1,
        "obra": "Galpón",
        "grupo": "aprobar",
        "urgencia": "bloquea",
        "texto": "V2 devuelta: falta acero",
        "accion": {"texto": "Abrir el presupuesto", "pagina": "hoja"},
    }
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.usefixtures("_fuentes_falsas")
def test_con_abrir_carpeta_ve_todas_las_carpetas() -> None:
    navegador, _ = con_cuenta(app, "ana")  # arma: EDITAR_HOJA y ABRIR_CARPETA
    cuerpo = navegador.get("/v1/obras/pendientes/todas").json()
    # bloquea: Norte antes que Sur; luego avisos: la empresa antes que Norte
    assert _filas(cuerpo) == [GALPON, VIALIDAD, CENTRAL, CLINICA]


@pytest.mark.usefixtures("_fuentes_falsas")
def test_quien_revisa_ve_lo_que_espera_dictamen_en_todas_las_carpetas() -> None:
    """Enmienda 2026-11-05 (decisión de Eugenio): con Norte abierta, el envío de Sur también."""
    navegador, ficha = con_cuenta(app, "rita")  # revisa: LEER, APROBAR_VERSION y ABRIR_CARPETA
    _abrir(ficha, NORTE)
    cuerpo = navegador.get("/v1/obras/pendientes/todas").json()
    assert _filas(cuerpo) == [VIALIDAD]
    otro, _ = con_cuenta(app, "rita")  # sin carpeta abierta: la de la empresa, y las demás
    assert _filas(otro.get("/v1/obras/pendientes/todas").json()) == [VIALIDAD]


@pytest.mark.usefixtures("_fuentes_falsas")
def test_sin_abrir_carpeta_solo_la_carpeta_abierta(monkeypatch: pytest.MonkeyPatch) -> None:
    quitado = frozenset({permisos.Rol.ARMA, permisos.Rol.ADMINISTRADOR})
    monkeypatch.setitem(permisos.PERMISOS, "abrir_carpeta", quitado)
    navegador, ficha = con_cuenta(app, "rita")
    _abrir(ficha, NORTE)  # Norte no tiene nada que espere dictamen
    assert navegador.get("/v1/obras/pendientes/todas").json()["pendientes"] == []
    _abrir(ficha, SUR)
    assert _filas(navegador.get("/v1/obras/pendientes/todas").json()) == [VIALIDAD]


@pytest.mark.usefixtures("_fuentes_falsas")
def test_revisa_no_ve_devueltas_precios_ni_calidad(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        ESCENARIO,
        ("aprobar", "Clínica"),
        ("V3 aprobada y sin entregar", Siguiente("Entregar", "entregar")),
    )
    monkeypatch.setitem(
        ESCENARIO,
        ("compras", "Galpón"),
        ("Falta registrar el avance", Siguiente("Control", "control")),
    )
    navegador, ficha = con_cuenta(app, "rita")
    _abrir(ficha, NORTE)  # Norte tiene una devuelta (Galpón) y precios (Clínica)
    cuerpo = navegador.get("/v1/obras/pendientes/todas").json()
    # de todas las carpetas, solo el envío de Sur espera dictamen: ni la devuelta, ni los precios,
    # ni la calidad de la empresa, ni «Entregar» ni compras
    assert _filas(cuerpo) == [VIALIDAD]
    assert cuerpo["carpetas_omitidas"] == 0


@pytest.mark.usefixtures("_fuentes_falsas")
def test_cuenta_sin_editar_ni_aprobar_recibe_lista_vacia(monkeypatch: pytest.MonkeyPatch) -> None:
    quitado = permisos.PERMISOS[permisos.Accion.APROBAR_VERSION] - {permisos.Rol.REVISA}
    monkeypatch.setitem(permisos.PERMISOS, permisos.Accion.APROBAR_VERSION, quitado)
    navegador, _ = con_cuenta(app, "rita")  # conserva LEER_PROYECTO
    respuesta = navegador.get("/v1/obras/pendientes/todas")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"pendientes": [], "carpetas_omitidas": 0}


@pytest.mark.usefixtures("_fuentes_falsas")
def test_con_la_clave_solo_la_carpeta_del_proceso_y_alcance_todo() -> None:
    respuesta = cliente(app).get(
        "/v1/obras/pendientes/todas", headers={CABECERA: crear_clave_de_prueba()}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert _filas(respuesta.json()) == [CENTRAL]


@pytest.mark.usefixtures("_fuentes_falsas")
def test_carpeta_ilegible_da_200_y_se_cuenta(_entorno: Path) -> None:
    (_entorno / "Carpeta Rota.db").write_bytes(b"esto no es SQLite, es texto " * 40)
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.get("/v1/obras/pendientes/todas")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["carpetas_omitidas"] == 1
    assert _filas(cuerpo) == [GALPON, VIALIDAD, CENTRAL, CLINICA]


def test_carpeta_sin_migrar_con_las_fuentes_reales_se_omite(_entorno: Path) -> None:
    """Una base vieja, sin las tablas de aprobaciones ni de compras: 200, no 503 ni lista en
    blanco; las demás carpetas siguen (foco de revisión 2)."""
    with closing(sqlite3.connect(_entorno / "Carpeta Vieja.db")) as conexion:
        conexion.execute("CREATE TABLE proyecto (id INTEGER PRIMARY KEY, nombre TEXT)")
        conexion.commit()
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.get("/v1/obras/pendientes/todas")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"pendientes": [], "carpetas_omitidas": 1}


@pytest.mark.usefixtures("_fuentes_falsas")
def test_no_escribe(_entorno: Path) -> None:
    antes = arbol(_entorno)
    fechas = {p.name: p.stat().st_mtime_ns for p in _entorno.glob("*.db")}
    navegador, _ = con_cuenta(app, "ana")
    assert navegador.get("/v1/obras/pendientes/todas").status_code == 200
    assert arbol(_entorno) == antes
    assert {p.name: p.stat().st_mtime_ns for p in _entorno.glob("*.db")} == fechas


def test_el_administrador_no_tiene_leer() -> None:
    navegador, _ = con_cuenta(app, "admin")
    assert navegador.get("/v1/obras/pendientes/todas").status_code == 403


def test_sin_sesion_401() -> None:
    respuesta = cliente(app).get("/v1/obras/pendientes/todas")
    assert respuesta.status_code == 401
    assert "detalle" in respuesta.json()


def test_carpeta_con_datos_raros_da_200_sin_el_texto_del_error(_entorno: Path) -> None:
    """Un `fecha_hora` no ISO hace lanzar `ValueError` a la fuente real: la carpeta se omite y el
    texto del error no sale en el cuerpo (los manejadores globales lo habrían puesto en un 422)."""
    with closing(sqlite3.connect(_entorno / NORTE)) as conexion:
        conexion.execute(
            "INSERT INTO mp_aprobacion_evento (proyecto_id, tipo, version, huella_version, notas,"
            " usuario, fecha_hora, armo, anterior, huella) VALUES (1, 'envio', 'V1', ?, '',"
            " 'Ana <ana>', '28/10/2026 9:00', 0, ?, ?)",
            ("a" * 64, "0" * 64, "b" * 64),
        )
        conexion.commit()
        conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.get("/v1/obras/pendientes/todas")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"pendientes": [], "carpetas_omitidas": 1}
    assert "28/10/2026" not in respuesta.text
    assert "isoformat" not in respuesta.text
