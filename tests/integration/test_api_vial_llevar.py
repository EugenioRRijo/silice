"""`POST /v1/vial/tramos/llevar`: los tramos van al presupuesto (plan vial, Tarea 8b). FICTICIO.

De punta a punta por la API y **sin llamar a `derivar_tramos`**: se importa
`data/samples/vial/via_ficticia.csv` en VIV-002 de la «Vivienda Demo 80 m2», se lleva al borrador
de la Hoja, se escribe a mano una cantidad distinta de la derivada en la mezcla de la carpeta de T1
y la auditoría del borrador trae VR1 para esa capa. Oráculos a mano (memoria de cálculo del
README de la muestra): 18 renglones; la mezcla de T1 es 1200 × 7,30 × 0,05 × 2,35 = 1029,3 t.

`via.db` lleva las 14 partidas viales en «Lista Bs de prueba»; `sin_apu.db` es la misma carpeta
sin ninguna, y llevar da 404 con los 14 códigos. Mismo acceso que `POST /v1/hoja/llevar`: solo
una cuenta con `editar_hoja`, CSRF, `Origin` y `no-store`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import app
from api.rutas import hoja as rutas_hoja
from api.rutas import vial as rutas
from aplicacion import hoja_borradores
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts import Dominio
from core.contracts.apu import ComposicionAPU, LineaMaterial
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import FECHA, OBRA, guardar_version, sembrar_vivienda
from tests.fixtures.produccion_api import cliente_con_clave
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
ANA = "Ana <ana>"
MARTES = datetime(2026, 10, 20, 10, 30)
HOY = date(2026, 10, 31)
MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"
RUTA = "/v1/vial/tramos/llevar"
CENTINELA = "VALOR-CENTINELA"
MEZCLA_T1 = "C-000.000.009|tramo:T1:capa:3"
SOLO_CUENTA = "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."
SIN_OBRA = "Esa obra no está en esta carpeta de trabajo: elíjala de nuevo en el selector de obra."
FORMA = "Envíe la obra cuyos tramos se llevan al presupuesto."
CODIGOS = [f"C-000.000.{n:03d}" for n in range(1, 15)]
SIN_APU = (
    "Las partidas "
    + ", ".join(f"«{c}»" for c in CODIGOS[:-1])
    + f" y «{CODIGOS[-1]}» no están en el catálogo: compóngalas primero en Componer."
)
CABECERA = (
    "tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;"
    "espesor_m;densidad_t_m3;dosis_l_m2;lineas\n"
)


def _catalogar(sesion) -> None:
    """Las 14 partidas viales con un APU de una línea (precio inventado) en la lista de la obra."""
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == "Lista Bs de prueba")
    ).one()
    unidades = ["m3", "m3", "m3", "m2", "l", "m2", "l", "m2", "t", "m3", "t", "m", "m", "t·km"]
    for codigo, unidad in zip(CODIGOS, unidades, strict=True):
        linea = LineaMaterial(f"Material de {codigo}", unidad, D("1"), D("3"))
        apu = ComposicionAPU(codigo, f"Partida vial {codigo}", unidad, D("10"), materiales=(linea,))
        Catalogo(sesion).cargar_composicion(apu, lista, Dominio.CIVIL, FECHA, "prueba")
    sesion.commit()


def _carpeta(ruta: Path, *, viales: bool) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            obra = sembrar_vivienda(s, usuario=ANA)
            guardar_version(s, obra, "VIV-002", usuario=ANA)
            if viales:
                _catalogar(s)
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_vial_llevar")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "via.db": _carpeta(carpeta / "via.db", viales=True),
        "sin_apu.db": _carpeta(carpeta / "sin_apu.db", viales=False),
    }


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    for nombre in ("via.db", "sin_apu.db"):
        (casos / nombre).write_bytes(_plantillas[nombre].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    monkeypatch.setattr(rutas, "ahora", lambda: MARTES)
    monkeypatch.setattr(rutas, "_hoy", lambda: HOY)
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: HOY)
    yield
    hoja_borradores.olvidar_todo()
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _entrar(caso: str = "via.db", login: str = "ana") -> tuple[TestClient, str]:
    navegador, ficha = con_cuenta(app, login)
    elegida = navegador.post("/v1/casos/actual", json={"nombre": caso}, headers=protegida(ficha))
    assert elegida.status_code == 200, elegida.text
    return navegador, ficha


@pytest.fixture
def ana() -> tuple[TestClient, str]:
    return _entrar()


def _importar(cuenta, contenido: bytes, nombre: str = "via.csv"):
    navegador, ficha = cuenta
    return navegador.post(
        "/v1/vial/tramos/importar",
        params={"proyecto": OBRA, "version": "VIV-002"},
        files={"archivo": (nombre, contenido, "text/csv")},
        headers=protegida(ficha),
    )


def _llevar(cuenta, proyecto: str = OBRA):
    navegador, ficha = cuenta
    return navegador.post(RUTA, json={"proyecto": proyecto}, headers=protegida(ficha))


def _borradores(navegador: TestClient) -> list[dict]:
    respuesta = navegador.get("/v1/hoja/borradores")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["borradores"]


def _guardados(caso: str = "via.db") -> int:
    with closing(sqlite3.connect(config.carpeta_casos() / caso)) as conexion:
        tablas = {n for (n,) in conexion.execute("SELECT name FROM sqlite_master")}
        if "vial_tramos_guardado" not in tablas:
            return 0
        return conexion.execute("SELECT COUNT(*) FROM vial_tramos_guardado").fetchone()[0]


# --- de punta a punta ---------------------------------------------------------------------------


def test_importar_llevar_escribir_900_y_la_auditoria_muestra_vr1(ana) -> None:
    navegador, ficha = ana
    assert _importar(ana, MUESTRA.read_bytes()).status_code == 200

    llevado = _llevar(ana)

    assert llevado.status_code == 200, llevado.text
    assert llevado.headers["cache-control"] == "no-store"
    cuerpo = llevado.json()
    assert list(cuerpo) == ["borrador_id", "renglones"]
    assert cuerpo["renglones"] == 18
    id_ = cuerpo["borrador_id"]
    ((borrador,),) = [[b] for b in _borradores(navegador)]
    assert (borrador["id"], borrador["proyecto"], borrador["version"]) == (id_, OBRA, "VIV-002")

    filas = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/presupuesto").json()["filas"]
    claves = [f["clave"] for f in filas]
    assert len([c for c in claves if "|tramo:" in c]) == 18
    assert not [c for c in claves if "|a-mano:" in c]
    (mezcla,) = [f for f in filas if f["clave"] == MEZCLA_T1]
    assert mezcla["cantidad"] == "1.029,3"

    escrita = navegador.put(
        f"/v1/hoja/borradores/{id_}/cantidades",
        json={"rev": borrador["rev"], "filas": [{"clave": MEZCLA_T1, "cantidad": "900"}]},
        headers=protegida(ficha),
    )
    assert escrita.status_code == 200, escrita.text

    informe = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/auditoria")
    assert informe.status_code == 200, informe.text
    viales = [h for h in informe.json()["hallazgos"] if h["regla"].startswith("VR")]
    assert [(h["regla"], h["origen"]) for h in viales] == [("VR1", ["tramo:T1:capa:3"])]
    assert "900 t" in viales[0]["descripcion"] and "1.029,3 t" in viales[0]["descripcion"]


def test_llevar_otra_vez_usa_el_mismo_borrador_y_no_duplica(ana) -> None:
    navegador, _ = ana
    assert _importar(ana, MUESTRA.read_bytes()).status_code == 200
    primero = _llevar(ana).json()
    segundo = _llevar(ana).json()
    assert segundo == primero
    filas = navegador.get(f"/v1/hoja/borradores/{primero['borrador_id']}/vistas/presupuesto")
    assert len([f for f in filas.json()["filas"] if "|tramo:" in f["clave"]]) == 18


# --- errores ------------------------------------------------------------------------------------


def test_partidas_sin_apu_dan_404_con_todos_los_codigos_y_no_llevan_nada() -> None:
    cuenta = _entrar("sin_apu.db")
    assert _importar(cuenta, MUESTRA.read_bytes()).status_code == 200

    respuesta = _llevar(cuenta)

    assert respuesta.status_code == 404
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {"detalle": SIN_APU}
    assert _borradores(cuenta[0]) == []


def test_sin_tramos_es_409_y_no_abre_nada(ana) -> None:
    respuesta = _llevar(ana)
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": "La versión VIV-002 no tiene tramos: impórtelos en «Tramos de la vía» antes "
        "de llevarlos al presupuesto."
    }
    assert _borradores(ana[0]) == []


def test_csv_con_mas_de_2000_tramos_da_422_y_no_guarda(ana) -> None:
    filas = "".join(f"T{n};{n};{n + 1};7;;capa;fresado;0,05;;;\n" for n in range(2001))

    respuesta = _importar(ana, (CABECERA + filas).encode(), "grande.csv")

    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": "el archivo 'grande.csv' tiene 2.001 tramos: el máximo es 2.000. "
        "Divídalo en varios."
    }
    assert _guardados() == 0


def test_una_obra_que_no_existe_es_404_sin_eco(ana) -> None:
    respuesta = _llevar(ana, CENTINELA)
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": SIN_OBRA}
    assert CENTINELA not in respuesta.text


@pytest.mark.parametrize(
    "cuerpo",
    [{}, {"proyecto": ""}, {"proyecto": OBRA, "x": CENTINELA}, {"proyecto": 7}],
    ids=["vacio", "obra_vacia", "campo_de_mas", "numero"],
)
def test_la_forma_mala_es_422_sin_eco(ana, cuerpo: dict) -> None:
    navegador, ficha = ana
    respuesta = navegador.post(RUTA, json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA}
    assert CENTINELA not in respuesta.text


# --- acceso: el de POST /v1/hoja/llevar ----------------------------------------------------------


def test_la_clave_de_api_no_lleva_nada(ana) -> None:
    respuesta = cliente_con_clave().post(RUTA, json={"proyecto": OBRA})
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": SOLO_CUENTA}


def test_rita_no_lleva(ana) -> None:
    rita, ficha = con_cuenta(app, "rita")
    respuesta = rita.post(RUTA, json={"proyecto": OBRA}, headers=protegida(ficha))
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}


def test_llevar_exige_csrf_y_origen_propio(ana) -> None:
    navegador, ficha = ana
    assert _importar(ana, MUESTRA.read_bytes()).status_code == 200
    cuerpo = {"proyecto": OBRA}
    assert navegador.post(RUTA, json=cuerpo).status_code == 403
    ajeno = protegida(ficha, origen="http://evil.example")
    assert navegador.post(RUTA, json=cuerpo, headers=ajeno).status_code == 403
    assert navegador.post(RUTA, json=cuerpo, headers=protegida(ficha, None)).status_code == 403
    assert _borradores(navegador) == []
