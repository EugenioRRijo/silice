"""`GET /v1/obras/resumen/todas`: la cartera de todas las carpetas, por moneda (rediseño F6, T7).

Carpetas ficticias como en `test_api_obras_pendientes_todas.py`: la de la empresa (`silice.db`)
con «Edificio Central»; «Carpeta Norte» con «Galpón», «Clínica» y «Depósito»; «Carpeta Sur» con
«Vialidad». `mesa.obras_de_la_mesa` se reemplaza por una mesa falsa que lee la tabla `proyecto` y
le pone a cada obra la moneda, la etapa, el total y el EV, PV y BAC escritos a mano en `ESCENARIO`.

Oráculos a mano (nunca se suman Bs con USD; restricciones globales del plan F6):

- Bs: Galpón 1 000 000,10 + Clínica 2 000 000,20 = 3 000 000,30 (Depósito no tiene total: cuenta
  como obra, no suma); en ejecución, Galpón y Clínica (atrasada) = 2; obras = 3.
- USD: Edificio Central 500,00 + Vialidad 4 000,05 = 4 500,05; en ejecución, Vialidad = 1 (la
  aprobada no está en ejecución); obras = 2.
- La suma mezclada 3 000 000,30 + 4 500,05 = 3 004 500,35 no puede salir en ninguna parte.
- Avances (EV ÷ BAC × 100 y PV ÷ BAC × 100, a 0,1): Galpón 300 000,03 y 400 000,04 sobre
  1 000 000,10 = 30,0 y 40,0; Clínica 900 000,09 y 1 200 000,12 sobre 2 000 000,20 = 45,0 y 60,0;
  Vialidad 1 000 y 1 500 sobre 3 000 = 33,3 (33,333…) y 50,0.

Alcance por rol como en `/pendientes/todas`: «arma» y «revisa» (`ABRIR_CARPETA`; enmienda
2026-11-05, decisión de Eugenio) ven todas las carpetas; una cuenta sin él, solo la abierta (sin
abrir ninguna, la de la empresa); la clave de API, la carpeta del proceso. Una prueba sin mesa
falsa usa OB-S2 (`tests/fixtures/memorias/control_ob_s2.md`): total
5 060,00, avance real 30,0 y plan 37,5, atrasada. Hoy: miércoles 2026-11-04.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import app
from api.rutas import obras
from aplicacion import mesa
from aplicacion.mesa import ObraEnMesa
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import permisos, sesiones
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures.carpetas_trabajo import arbol
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)

RUTA = "/v1/obras/resumen/todas"
HOY = datetime(2026, 11, 4, 9, 0)
D = Decimal

NORTE, SUR, EMPRESA = "Carpeta Norte.db", "Carpeta Sur.db", "silice.db"
ESTE, OESTE = "Carpeta Este.db", "Carpeta Oeste.db"  # OB-S2 de verdad, solo en su prueba
OBRAS = {
    EMPRESA: ["Edificio Central"],
    NORTE: ["Galpón", "Clínica", "Depósito"],  # ids 1, 2 y 3
    SUR: ["Vialidad"],
}

_Datos = tuple[str, str, Decimal | None, Decimal | None, Decimal | None, Decimal | None]
#: nombre de la obra -> (moneda, etapa, total, EV, PV, BAC)
ESCENARIO: dict[str, _Datos] = {
    "Edificio Central": ("USD", "aprobada", D("500.00"), None, None, None),
    "Galpón": (
        "Bs", "en_ejecucion", D("1000000.10"), D("300000.03"), D("400000.04"), D("1000000.10"),
    ),
    "Clínica": (
        "Bs", "atrasada", D("2000000.20"), D("900000.09"), D("1200000.12"), D("2000000.20"),
    ),
    "Depósito": ("Bs", "en_elaboracion", None, None, None, None),
    "Vialidad": ("USD", "en_ejecucion", D("4000.05"), D("1000.00"), D("1500.00"), D("3000.00")),
}  # fmt: skip


def _mesa_falsa(sesion, catalogo, hoy) -> list[ObraEnMesa]:
    """Como `obras_de_la_mesa`: las obras de la carpeta por nombre, con los datos de `ESCENARIO`."""
    proyectos = sesion.scalars(select(models.Proyecto)).all()
    resultado = []
    for proyecto in sorted(proyectos, key=lambda p: p.nombre.casefold()):
        if proyecto.nombre not in ESCENARIO:
            continue
        moneda, etapa, total, ev, pv, bac = ESCENARIO[proyecto.nombre]
        resultado.append(
            ObraEnMesa(
                codigo=str(proyecto.id),
                nombre=proyecto.nombre,
                cliente="",
                moneda=moneda,
                etapa=etapa,
                version=None if total is None else "V1",
                total=total,
                corte=None,
                ev=ev,
                pv=pv,
                bac=bac,
                spi=None,
                retraso_dias=None,
                que_pasa=None,
                siguiente=None,
            )
        )
    return resultado


@pytest.fixture
def _mesa_falsa_puesta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mesa, "obras_de_la_mesa", _mesa_falsa)


def _ob_s2(ruta: Path, moneda: str, *, en_ejecucion: bool) -> Path:
    """OB-S2 con su versión OB-001 en `moneda`; con `en_ejecucion`, además su línea base y las
    valuaciones V-01 y V-02 (la fixture registra las valuaciones en USD: solo para la de USD)."""
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion, moneda)
            if en_ejecucion:
                ob.declarar_linea_base(sesion)
                ob.registrar_v01_y_v02(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_resumen_todas")
    plantillas = {"instalacion": plantilla_con_cuentas(carpeta)}
    for nombre, nombres_de_obras in OBRAS.items():
        ruta = carpeta / nombre
        preparar_base(ruta)
        with closing(sqlite3.connect(ruta)) as conexion:
            for n, obra in enumerate(nombres_de_obras, 1):
                conexion.execute(
                    "INSERT INTO proyecto (id, nombre, descripcion, dominio) VALUES (?, ?, '', '')",
                    (n, obra),
                )
            conexion.commit()
            conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        plantillas[nombre] = ruta
    plantillas[ESTE] = _ob_s2(carpeta / ESTE, "USD", en_ejecucion=True)
    plantillas[OESTE] = _ob_s2(carpeta / OESTE, "Bs", en_ejecucion=False)
    return plantillas


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    monkeypatch.setattr(obras, "ahora", lambda: HOY)
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


def _sin_cache(respuesta) -> None:
    assert respuesta.headers.get("cache-control") == "no-store", respuesta.headers


#: El texto de cada etapa, escrito a mano (el mismo que da el Resumen de la obra): la cartera
#: lo manda para que la interfaz no repita la tabla (F6, T8, menor 1 del revisor de diseño).
TEXTO_DE_ETAPA = {
    "en_elaboracion": "En elaboración",
    "en_aprobacion": "En aprobación",
    "aprobada": "Aprobada",
    "en_ejecucion": "En ejecución",
    "atrasada": "Atrasada",
}


def _obra(carpeta, titulo, obra_id, nombre, moneda, etapa, total, real, plan) -> dict:
    return {
        "carpeta": carpeta,
        "carpeta_titulo": titulo,
        "obra_id": obra_id,
        "nombre": nombre,
        "moneda": moneda,
        "etapa": etapa,
        "etapa_texto": TEXTO_DE_ETAPA[etapa],
        "total": total,
        "avance_real": real,
        "avance_plan": plan,
    }


def _moneda(moneda: str, cuantas: int, total: str, en_ejecucion: int) -> dict:
    return {"moneda": moneda, "obras": cuantas, "total": total, "en_ejecucion": en_ejecucion}


# Las filas que deben salir con la mesa falsa: la empresa primero, luego las carpetas por nombre y,
# dentro de cada una, las obras por nombre (C, D, G).
EMPRESA_TITULO = "Carpeta de la empresa"
CENTRAL = _obra(
    None, EMPRESA_TITULO, 1, "Edificio Central", "USD", "aprobada", "500.00", None, None
)
CLINICA = _obra(
    NORTE, "Carpeta Norte", 2, "Clínica", "Bs", "atrasada", "2000000.20", "45.0", "60.0"
)
DEPOSITO = _obra(NORTE, "Carpeta Norte", 3, "Depósito", "Bs", "en_elaboracion", None, None, None)
GALPON = _obra(
    NORTE, "Carpeta Norte", 1, "Galpón", "Bs", "en_ejecucion", "1000000.10", "30.0", "40.0"
)
VIALIDAD = _obra(
    SUR, "Carpeta Sur", 1, "Vialidad", "USD", "en_ejecucion", "4000.05", "33.3", "50.0"
)
TODAS = [CENTRAL, CLINICA, DEPOSITO, GALPON, VIALIDAD]

BS_TODAS = _moneda("Bs", 3, "3000000.30", 2)
USD_TODAS = _moneda("USD", 2, "4500.05", 1)
USD_SOLO_EMPRESA = _moneda("USD", 1, "500.00", 0)
MEZCLA_DE_TODAS = "3004500.35"  # Bs + USD: nunca debe aparecer


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_forma_de_la_respuesta() -> None:
    navegador, _ = con_cuenta(app, "ana")  # arma: LEER_PROYECTO y ABRIR_CARPETA
    respuesta = navegador.get(RUTA)
    assert respuesta.status_code == 200, respuesta.text
    _sin_cache(respuesta)
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"hoy", "por_moneda", "obras", "carpetas_omitidas"}
    assert cuerpo["hoy"] == "2026-11-04"
    assert cuerpo["carpetas_omitidas"] == 0
    # montos como texto decimal exacto (nunca número JSON): "500.00" != 500.0
    assert cuerpo["por_moneda"] == [BS_TODAS, USD_TODAS]
    assert cuerpo["obras"] == TODAS
    assert MEZCLA_DE_TODAS not in respuesta.text


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_dos_carpetas_una_en_bs_y_otra_en_usd_no_se_mezclan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Sin la obra de la empresa quedan dos carpetas: Norte, toda en Bs, y Sur, toda en USD.
    monkeypatch.delitem(ESCENARIO, "Edificio Central")
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.get(RUTA)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    # Bs: 1 000 000,10 + 2 000 000,20 = 3 000 000,30; USD: solo Vialidad, 4 000,05
    assert cuerpo["por_moneda"] == [BS_TODAS, _moneda("USD", 1, "4000.05", 1)]
    assert cuerpo["obras"] == [CLINICA, DEPOSITO, GALPON, VIALIDAD]
    assert "3004000.35" not in respuesta.text  # 3 000 000,30 + 4 000,05: la suma prohibida


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_una_sola_moneda_una_sola_fila_sin_fila_en_cero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        ESCENARIO, "Edificio Central", ("Bs", "aprobada", D("500.00"), None, None, None)
    )
    monkeypatch.setitem(
        ESCENARIO,
        "Vialidad",
        ("Bs", "en_ejecucion", D("4000.05"), D("1000.00"), D("1500.00"), D("3000.00")),
    )
    navegador, _ = con_cuenta(app, "ana")
    cuerpo = navegador.get(RUTA).json()
    # 1 000 000,10 + 2 000 000,20 + 4 000,05 + 500,00 = 3 004 500,35; en ejecución: Galpón,
    # Clínica y Vialidad. Ninguna fila «USD» con 0 obras.
    assert cuerpo["por_moneda"] == [_moneda("Bs", 5, "3004500.35", 3)]
    assert {o["moneda"] for o in cuerpo["obras"]} == {"Bs"}


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_carpeta_ilegible_da_200_y_se_cuenta(_entorno: Path) -> None:
    (_entorno / "Carpeta Rota.db").write_bytes(b"esto no es SQLite, es texto " * 40)
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.get(RUTA)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["carpetas_omitidas"] == 1
    assert cuerpo["por_moneda"] == [BS_TODAS, USD_TODAS]
    assert cuerpo["obras"] == TODAS


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_quien_revisa_ve_la_cartera_de_todas_las_carpetas() -> None:
    """Enmienda 2026-11-05 (decisión de Eugenio): con Norte abierta ve también la empresa y Sur."""
    navegador, ficha = con_cuenta(app, "rita")  # revisa: LEER_PROYECTO y ABRIR_CARPETA
    _abrir(ficha, NORTE)
    respuesta = navegador.get(RUTA)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["obras"] == TODAS
    assert cuerpo["por_moneda"] == [BS_TODAS, USD_TODAS]
    assert cuerpo["carpetas_omitidas"] == 0


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_quien_revisa_sin_carpeta_abierta_tambien_ve_todas() -> None:
    navegador, _ = con_cuenta(app, "rita")
    cuerpo = navegador.get(RUTA).json()
    assert cuerpo["obras"] == TODAS
    assert cuerpo["por_moneda"] == [BS_TODAS, USD_TODAS]


def _sin_abrir_carpeta_para_revisa(monkeypatch: pytest.MonkeyPatch) -> None:
    quitado = frozenset({permisos.Rol.ARMA, permisos.Rol.ADMINISTRADOR})
    monkeypatch.setitem(permisos.PERMISOS, "abrir_carpeta", quitado)


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_sin_abrir_carpeta_solo_la_carpeta_abierta(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_abrir_carpeta_para_revisa(monkeypatch)
    navegador, ficha = con_cuenta(app, "rita")
    _abrir(ficha, NORTE)
    respuesta = navegador.get(RUTA)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["obras"] == [CLINICA, DEPOSITO, GALPON]
    assert cuerpo["por_moneda"] == [BS_TODAS]
    assert cuerpo["carpetas_omitidas"] == 0


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_sin_abrir_carpeta_ni_carpeta_abierta_solo_la_de_la_empresa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sin_abrir_carpeta_para_revisa(monkeypatch)
    navegador, _ = con_cuenta(app, "rita")
    cuerpo = navegador.get(RUTA).json()
    assert cuerpo["obras"] == [CENTRAL]
    assert cuerpo["por_moneda"] == [USD_SOLO_EMPRESA]


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_con_la_clave_solo_la_carpeta_del_proceso() -> None:
    respuesta = cliente(app).get(RUTA, headers={CABECERA: crear_clave_de_prueba()})
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["obras"] == [CENTRAL]
    assert cuerpo["por_moneda"] == [USD_SOLO_EMPRESA]
    assert cuerpo["carpetas_omitidas"] == 0


def test_sin_leer_proyecto_es_403(monkeypatch: pytest.MonkeyPatch) -> None:
    navegador, _ = con_cuenta(app, "rita")
    quitado = permisos.PERMISOS[permisos.Accion.LEER_PROYECTO] - {permisos.Rol.REVISA}
    monkeypatch.setitem(permisos.PERMISOS, permisos.Accion.LEER_PROYECTO, quitado)
    respuesta = navegador.get(RUTA)
    assert respuesta.status_code == 403
    assert "detalle" in respuesta.json()
    _sin_cache(respuesta)


def test_el_administrador_no_tiene_leer() -> None:
    navegador, _ = con_cuenta(app, "admin")
    assert navegador.get(RUTA).status_code == 403


def test_sin_sesion_401() -> None:
    respuesta = cliente(app).get(RUTA)
    assert respuesta.status_code == 401
    assert "detalle" in respuesta.json()


def test_con_las_obras_reales_cada_moneda_va_en_su_fila(
    _plantillas: dict[str, Path], _entorno: Path
) -> None:
    """Sin mesa falsa: OB-S2 en ejecución en USD (Carpeta Este) y OB-S2 recién presupuestada en
    Bs (Carpeta Oeste), los mismos 5 060,00; la empresa con «Edificio Central» en blanco (USD por
    omisión, sin total). Bs: 1 obra, 5 060,00, 0 en ejecución; USD: 2 obras, 5 060,00, 1 en
    ejecución (OB-S2 atrasada). Nunca 10 120,00."""
    (_entorno / NORTE).unlink()
    (_entorno / SUR).unlink()
    for nombre in (ESTE, OESTE):
        (_entorno / nombre).write_bytes(_plantillas[nombre].read_bytes())
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.get(RUTA)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["carpetas_omitidas"] == 0
    assert cuerpo["por_moneda"] == [
        _moneda("Bs", 1, "5060.00", 0),
        _moneda("USD", 2, "5060.00", 1),
    ]
    central, este, oeste = cuerpo["obras"]
    assert central == _obra(
        None, EMPRESA_TITULO, 1, "Edificio Central", "USD", "en_elaboracion", None, None, None
    )
    assert isinstance(este["obra_id"], int)
    assert este == _obra(
        ESTE, "Carpeta Este", este["obra_id"], "OB-S2", "USD", "atrasada", "5060.00", "30.0", "37.5"
    )
    assert isinstance(oeste["obra_id"], int)
    assert oeste == _obra(
        OESTE, "Carpeta Oeste", oeste["obra_id"], "OB-S2", "Bs", "en_elaboracion", "5060.00",
        None, None,
    )  # fmt: skip
    assert "10120.00" not in respuesta.text


@pytest.mark.usefixtures("_mesa_falsa_puesta")
def test_no_escribe(_entorno: Path) -> None:
    antes = arbol(_entorno)
    fechas = {p.name: p.stat().st_mtime_ns for p in _entorno.glob("*.db")}
    navegador, _ = con_cuenta(app, "ana")
    assert navegador.get(RUTA).status_code == 200
    assert arbol(_entorno) == antes
    assert {p.name: p.stat().st_mtime_ns for p in _entorno.glob("*.db")} == fechas
