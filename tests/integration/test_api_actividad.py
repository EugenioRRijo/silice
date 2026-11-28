"""`GET /v1/actividad`: la actividad de una cuenta, como la página de actividad de GitHub (C10).

Contrato EXACTO (claves literales, escritas a mano): `{usuario, desde, hasta, dias, cifras,
eventos, recortado}`; `dias` es `[{fecha, cuantos}]`; `cifras`, `{versiones_guardadas,
versiones_enviadas, dictamenes, auditorias}`; cada evento, `{fecha, tipo, obra, archivo, texto}`.

Permisos: la ve la propia cuenta o quien administra las cuentas; otra cuenta, 403 (también si la
cuenta pedida no existe: no se dice quién existe); el administrador pidiendo una cuenta que no
existe, 404; sin sesión, 401; la clave de API no es una persona, 403.

Datos ficticios: Ana (arma), Rita (revisa), admin y «Vivienda Demo 80 m2». Los días y las cifras
se cuentan a mano sobre lo sembrado.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import update

from api import dependencias
from api.main import app
from aplicacion.tablas_indice_aprobacion import FilaIndiceAprobacion
from core.catalog import abrir_sesion
from core.models.cadena import EslabonVersion
from fusion.historial import HallazgoCompacto, registrar_auditoria
from operacion.instalacion import sesion_de_instalacion
from tests.fixtures.carpeta_aprobaciones import guardar_version, sembrar_vivienda
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)

RUTA = "/v1/actividad"
OBRA = "Vivienda Demo 80 m2"
ANA = "Ana Demo <ana>"
RITA = "Rita Demo <rita>"
SHA = "cd" * 32
LUNES = datetime(2026, 10, 19, 9, 0, 0)
MARTES = datetime(2026, 10, 20, 10, 30, 0)
RANGO = {"desde": "2026-10-01", "hasta": "2026-10-31"}
CLAVES = {"usuario", "desde", "hasta", "dias", "cifras", "eventos", "recortado"}
CLAVES_CIFRAS = {"versiones_guardadas", "versiones_enviadas", "dictamenes", "auditorias"}
CLAVES_EVENTO = {"fecha", "tipo", "obra", "archivo", "texto"}


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("actividad_api"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    yield
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


def _auditoria(por: str, el: datetime, archivo: str, errores: int) -> None:
    with sesion_de_instalacion() as sesion:
        registrar_auditoria(
            sesion,
            usuario=por,
            tipo="libro",
            nombre_archivo=archivo,
            sha256=SHA,
            fecha_libro=None,
            total_libro=None,
            total_silice=None,
            hallazgos=[
                HallazgoCompacto("L4", "APU-02", f"G{i}", "ERROR", "x") for i in range(errores)
            ],
            ahora=el,
        )
        sesion.commit()


def _envio(n: int, por: str, el: datetime, **extra) -> None:
    campos = {
        "caso": "caso.db",
        "envio_id": n,
        "proyecto": "1",
        "obra": OBRA,
        "version": "VIV-001",
        "total": Decimal("100.00"),
        "moneda": "Bs",
        "estado": "en_aprobacion",
        "enviado_por": por,
        "enviado_el": el,
        "dictamen_por": None,
        "dictamen_el": None,
        "nota": "",
        "notas": "",
        "armo": False,
    }
    with sesion_de_instalacion() as sesion:
        sesion.add(FilaIndiceAprobacion(**{**campos, **extra}))
        sesion.commit()


@pytest.fixture
def sembrado() -> None:
    """Lo de Ana: VIV-001 (lunes 19, 9:00), un envío (lunes 10:00) que Rita aprueba (martes
    10:30), y una auditoría de 3 errores (martes 15:00). Lo de Rita: VIV-002 (martes 10:30)."""
    motor = dependencias.obtener_motor(dependencias.url_del_proceso())
    with abrir_sesion(motor) as s:
        obra = sembrar_vivienda(s, usuario=ANA)
        guardar_version(s, obra, "VIV-002", usuario=RITA)
        for presupuesto, fecha in ((1, LUNES), (2, MARTES)):
            s.execute(
                update(EslabonVersion)
                .where(EslabonVersion.presupuesto_id == presupuesto)
                .values(fecha_hora=fecha)
            )
        s.commit()
    _envio(
        1,
        ANA,
        datetime(2026, 10, 19, 10, 0, 0),
        estado="aprobada",
        dictamen_por=RITA,
        dictamen_el=MARTES,
    )
    _auditoria(ANA, datetime(2026, 10, 20, 15, 0, 0), "Presupuesto cliente A.xlsx", 3)


# --- el contrato ---------------------------------------------------------------------------------


def test_la_propia_cuenta_ve_su_actividad_con_el_contrato_exacto(sembrado) -> None:
    ana, _ = con_cuenta(app, "ana")
    r = ana.get(RUTA, params={"usuario": "ana", **RANGO})
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    cuerpo = r.json()
    assert set(cuerpo) == CLAVES
    assert cuerpo["usuario"] == "ana"
    assert (cuerpo["desde"], cuerpo["hasta"], cuerpo["recortado"]) == (
        "2026-10-01",
        "2026-10-31",
        False,
    )
    assert set(cuerpo["cifras"]) == CLAVES_CIFRAS
    assert cuerpo["cifras"] == {
        "versiones_guardadas": 1,
        "versiones_enviadas": 1,
        "dictamenes": 0,
        "auditorias": 1,
    }
    assert cuerpo["dias"] == [
        {"fecha": "2026-10-19", "cuantos": 2},
        {"fecha": "2026-10-20", "cuantos": 1},
    ]
    assert all(set(e) == CLAVES_EVENTO for e in cuerpo["eventos"])


def test_los_eventos_van_del_mas_reciente_al_mas_antiguo_con_su_texto(sembrado) -> None:
    ana, _ = con_cuenta(app, "ana")
    eventos = ana.get(RUTA, params=RANGO).json()["eventos"]  # sin `usuario`: la propia cuenta
    assert eventos == [
        {
            "fecha": "2026-10-20T15:00:00",
            "tipo": "auditoria",
            "obra": "",
            "archivo": "Presupuesto cliente A.xlsx",
            "texto": "auditó Presupuesto cliente A.xlsx: 3 errores",
        },
        {
            "fecha": "2026-10-19T10:00:00",
            "tipo": "version_enviada",
            "obra": OBRA,
            "archivo": "",
            "texto": f"envió la versión VIV-001 de {OBRA} a aprobación",
        },
        {
            "fecha": "2026-10-19T09:00:00",
            "tipo": "version_guardada",
            "obra": OBRA,
            "archivo": "",
            "texto": f"guardó la versión VIV-001 de {OBRA}",
        },
    ]


def test_el_dictamen_es_de_quien_dictamina(sembrado) -> None:
    rita, _ = con_cuenta(app, "rita")
    cuerpo = rita.get(RUTA, params=RANGO).json()
    assert cuerpo["cifras"] == {
        "versiones_guardadas": 1,
        "versiones_enviadas": 0,
        "dictamenes": 1,
        "auditorias": 0,
    }
    assert [e["texto"] for e in cuerpo["eventos"]] == [
        f"aprobó la versión VIV-001 de {OBRA}",
        f"guardó la versión VIV-002 de {OBRA}",
    ]


def test_una_cuenta_sin_actividad_da_ceros_y_listas_vacias() -> None:
    admin, _ = con_cuenta(app, "admin")
    cuerpo = admin.get(RUTA, params={"usuario": "tomas", **RANGO}).json()
    assert cuerpo["dias"] == [] and cuerpo["eventos"] == []
    assert cuerpo["cifras"] == dict.fromkeys(CLAVES_CIFRAS, 0)


# --- el rango ------------------------------------------------------------------------------------


def test_el_rango_deja_fuera_lo_de_otros_dias(sembrado) -> None:
    ana, _ = con_cuenta(app, "ana")
    cuerpo = ana.get(RUTA, params={"desde": "2026-10-20", "hasta": "2026-10-20"}).json()
    assert cuerpo["dias"] == [{"fecha": "2026-10-20", "cuantos": 1}]
    assert [e["tipo"] for e in cuerpo["eventos"]] == ["auditoria"]


def test_por_omision_es_el_ultimo_ano_hasta_hoy() -> None:
    _auditoria(ANA, datetime.now() - timedelta(seconds=30), "de hoy.xlsx", 0)
    _auditoria(ANA, datetime.now() - timedelta(days=400), "de hace mucho.xlsx", 0)
    ana, _ = con_cuenta(app, "ana")
    cuerpo = ana.get(RUTA).json()
    hoy = date.today()
    assert cuerpo["hasta"] == hoy.isoformat()
    assert cuerpo["desde"] == (hoy - timedelta(days=364)).isoformat()
    assert [e["archivo"] for e in cuerpo["eventos"]] == ["de hoy.xlsx"]


def test_un_rango_al_reves_es_422_sin_cache() -> None:
    ana, _ = con_cuenta(app, "ana")
    r = ana.get(RUTA, params={"desde": "2026-10-31", "hasta": "2026-10-01"})
    assert r.status_code == 422
    assert r.headers["cache-control"] == "no-store"
    assert "desde" in r.json()["detalle"]


def test_una_fecha_que_no_es_fecha_es_422() -> None:
    ana, _ = con_cuenta(app, "ana")
    assert ana.get(RUTA, params={"desde": "ayer"}).status_code == 422


# --- los permisos --------------------------------------------------------------------------------


def test_el_administrador_ve_la_actividad_de_otra_cuenta(sembrado) -> None:
    admin, _ = con_cuenta(app, "admin")
    r = admin.get(RUTA, params={"usuario": "ana", **RANGO})
    assert r.status_code == 200
    assert r.json()["cifras"]["auditorias"] == 1


def test_el_login_se_reconoce_sin_importar_mayusculas(sembrado) -> None:
    admin, _ = con_cuenta(app, "admin")
    cuerpo = admin.get(RUTA, params={"usuario": "ANA", **RANGO}).json()
    assert cuerpo["usuario"] == "ana" and cuerpo["cifras"]["auditorias"] == 1


@pytest.mark.parametrize(("quien", "pedida"), [("ana", "rita"), ("rita", "ana"), ("ana", "admin")])
def test_otra_cuenta_sin_administrar_no_la_ve(quien: str, pedida: str, sembrado) -> None:
    navegador, _ = con_cuenta(app, quien)
    r = navegador.get(RUTA, params={"usuario": pedida, **RANGO})
    assert r.status_code == 403
    assert r.json()["detalle"] == (
        "Solo puede ver su propia actividad, o la de todos si administra las cuentas."
    )
    assert r.headers["cache-control"] == "no-store"
    assert "versiones_guardadas" not in r.text


def test_quien_no_administra_recibe_403_y_no_404_por_una_cuenta_que_no_existe() -> None:
    ana, _ = con_cuenta(app, "ana")
    assert ana.get(RUTA, params={"usuario": "nadie"}).status_code == 403


def test_el_administrador_recibe_404_por_una_cuenta_que_no_existe() -> None:
    admin, _ = con_cuenta(app, "admin")
    r = admin.get(RUTA, params={"usuario": "nadie"})
    assert r.status_code == 404
    assert r.json()["detalle"] == "No hay una cuenta con ese usuario."
    assert r.headers["cache-control"] == "no-store"


def test_la_propia_cuenta_sin_actividad_es_200_no_404() -> None:
    rita, _ = con_cuenta(app, "rita")
    assert rita.get(RUTA, params={"usuario": "rita", **RANGO}).status_code == 200


def test_sin_sesion_401() -> None:
    assert cliente(app).get(RUTA, params={"usuario": "ana"}).status_code == 401


def test_la_clave_de_api_no_es_una_persona_403() -> None:
    r = cliente(app).get(
        RUTA, params={"usuario": "ana"}, headers={CABECERA: crear_clave_de_prueba()}
    )
    assert r.status_code == 403
    assert "cuenta" in r.json()["detalle"]
