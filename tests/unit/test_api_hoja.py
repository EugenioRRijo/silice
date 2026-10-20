"""`/v1/hoja`: lectura y navegacion de la hoja del proyecto, rutas R1 a R4 (T10, 3b-1).

Contrato del diseno (`docs/especificaciones/2026-10-19-hoja-react-design.md`, §3.1, §4.1, §4.3):

- R1 `GET /v1/hoja/versiones?proyecto=` (clave de API o sesion `arma`): `{proyecto, moneda,
  por_omision, versiones: [{codigo, fecha, motivo, origen, vigente, descartada, cambios}]}`.
- R2 `POST /v1/hoja/borradores` `{proyecto, version|null}`: 201 `{id, base, resumen, instantanea}`.
  Solo cuenta (con `X-Silice-Clave`, 403). ESCRIBE la instantanea (UC-15e) y crea el borrador vivo.
- R3 `GET /v1/hoja/borradores/{id}` y R4 `DELETE ...` (204, idempotente): solo cuenta.
- Todo `no-store` (tambien en errores), 422 sin eco, montos `{texto, exacto}` sin `float`, un
  borrador de otra ficha no existe (404) y uno abierto en otro caso da 409 con mensaje fijo.

Oraculos a mano: los literales de la memoria de OF-001 (total 2 703,86 USD) y de la prueba de
aceptacion SF (historial 001 / 002 edicion / 003 restauracion), los textos de la pagina clasica
(`ui/paginas/hoja.py:346-351`, `ui/hoja.py:1572`) y los recuentos de filas con `sqlite3` directo.
Las pruebas de paridad pueden importar `ui` (aqui solo para sembrar con la clasica).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from aplicacion import entrega, hoja_borradores
from core import models
from core.budget import crear_proyecto
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.verification.texto import normalizar_texto
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import sesiones
from tests.fixtures import caso_of001, caso_ti001
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    borrar_instantanea,
    plantilla_of001,
    plantilla_ti001,
)
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)
from ui import hoja as clasica

D = Decimal
RAIZ = Path(__file__).resolve().parents[2]
SOLO_CUENTA = "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."
FALTA = (
    "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). "
    "Lo que no guardó se perdió: abra la versión otra vez."
)
OTRO_CASO = "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual."
CENTINELA = "VALOR-CENTINELA"
MENSAJE_FORMA = "Los datos de la hoja no tienen la forma esperada: escriba cada celda como texto."
ORIGEN = "http://127.0.0.1:8000"
ID_AJENO = "a" * 22


# --- los casos de la prueba -----------------------------------------------------------------


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    """Cada caso se siembra una vez por modulo; las pruebas copian el archivo que necesitan."""
    carpeta = tmp_path_factory.mktemp("api_hoja")
    casos = {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
        "ti001": plantilla_ti001(carpeta / "ti001.db"),
    }
    tres = Path(shutil.copyfile(casos["of001"], carpeta / "of001_tres.db"))
    casos["of001_tres"] = tres
    motor = crear_motor(f"sqlite:///{tres.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            entrega.con_anexos_de_cadena(sesion)
            catalogo = Catalogo(sesion)
            abierta = clasica.abrir_version(sesion, catalogo, NOMBRE_OF001, "001")
            clasica.guardar_version(
                sesion,
                catalogo,
                abierta,
                replace(
                    abierta.borrador,
                    parametros=replace(abierta.borrador.parametros, administracion=D("0.20")),
                ),
                fuente="criterio del residente, acta 12",
                responsable="Ing. Prueba",
            )
            clasica.restaurar(
                sesion, catalogo, NOMBRE_OF001, "001", fuente="volver a la 001", responsable="X"
            )
    finally:
        motor.dispose()
    return casos


@pytest.fixture(autouse=True)
def _entorno(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalacion con cuentas y OF-001 (version 001) como caso por defecto."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["of001"], ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _poner(origen: Path) -> Path:
    """Cambia el caso por defecto por una copia de `origen` (cierra el motor del anterior)."""
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    shutil.copyfile(origen, ruta)
    return ruta


def _filas(ruta: Path, tabla: str) -> int:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        return bd.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def _ana() -> tuple[TestClient, str]:
    return con_cuenta(app, "ana")


def _abrir(navegador: TestClient, ficha: str, proyecto: str = NOMBRE_OF001, version="001"):
    return navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": proyecto, "version": version},
        headers=protegida(ficha),
    )


def _versiones(navegador: TestClient, proyecto: str = NOMBRE_OF001):
    return navegador.get("/v1/hoja/versiones", params={"proyecto": proyecto})


def _con_proyecto_nuevo(ruta: Path) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as sesion:
        crear_proyecto(sesion, "Proyecto nuevo")
        sesion.commit()
    motor.dispose()
    dependencias.cerrar_motores()


def _huella(ficha: str) -> str:
    return sesiones.huella_de(ficha)


# --- R1: versiones -------------------------------------------------------------------------


def test_r1_lista_las_versiones_de_of001_con_su_historial() -> None:
    navegador, _ = _ana()
    respuesta = _versiones(navegador)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["proyecto"] == NOMBRE_OF001 and cuerpo["moneda"] == "USD"
    assert cuerpo["por_omision"] == "001"
    assert cuerpo["versiones"] == [
        {
            "codigo": "001",
            "fecha": caso_of001.FECHA.isoformat(),
            "motivo": "",
            "origen": "",
            "vigente": True,
            "descartada": False,
            "cambios": 0,
        }
    ]


def test_r1_con_tres_versiones_da_el_historial_de_la_aceptacion_sf(_casos) -> None:
    _poner(_casos["of001_tres"])
    navegador, _ = _ana()
    cuerpo = _versiones(navegador).json()
    assert [
        (v["codigo"], v["motivo"], v["origen"], v["vigente"], v["descartada"])
        for v in cuerpo["versiones"]
    ] == [
        ("001", "", "", False, False),
        ("002", "edicion", "001", False, False),
        ("003", "restauracion", "001", True, False),
    ]
    assert [v["cambios"] for v in cuerpo["versiones"]][:2] == [0, 1]
    assert cuerpo["por_omision"] == "003"


def _descartar(ruta: Path, *codigos: str) -> None:
    tabla = models.DescarteVersion.__tablename__
    with closing(sqlite3.connect(ruta)) as bd:
        ids = dict(bd.execute("SELECT codigo, id FROM presupuesto"))
        for codigo in codigos:
            bd.execute(
                f"INSERT INTO {tabla} (presupuesto_id, fecha) VALUES (?, ?)",
                (ids[codigo], "2026-10-06"),
            )
        bd.commit()
    dependencias.cerrar_motores()


def test_r1_con_la_vigente_descartada_se_ofrece_la_anterior_y_con_todas_la_ultima(_casos) -> None:
    ruta = _poner(_casos["of001_tres"])
    navegador, _ = _ana()
    _descartar(ruta, "003")
    cuerpo = _versiones(navegador).json()
    assert cuerpo["por_omision"] == "002"
    assert [v["descartada"] for v in cuerpo["versiones"]] == [False, False, True]
    _descartar(ruta, "001", "002")
    cuerpo = _versiones(navegador).json()
    assert cuerpo["por_omision"] == "003"
    assert all(v["descartada"] for v in cuerpo["versiones"])


def test_r1_acepta_el_codigo_del_proyecto_como_en_la_cabecera() -> None:
    navegador, _ = _ana()
    codigo = next(p["codigo"] for p in navegador.get("/v1/proyectos").json())
    cuerpo = _versiones(navegador, proyecto=codigo).json()
    assert cuerpo["proyecto"] == NOMBRE_OF001 and cuerpo["por_omision"] == "001"


def test_r1_de_un_proyecto_sin_versiones_no_tiene_version_por_omision(_entorno: Path) -> None:
    _con_proyecto_nuevo(_entorno)
    navegador, _ = _ana()
    cuerpo = _versiones(navegador, proyecto="Proyecto nuevo").json()
    assert cuerpo["versiones"] == [] and cuerpo["por_omision"] is None


def test_r1_la_clave_de_api_puede_leer_las_versiones() -> None:
    respuesta = cliente(app).get(
        "/v1/hoja/versiones",
        params={"proyecto": NOMBRE_OF001},
        headers={CABECERA: crear_clave_de_prueba()},
    )
    assert respuesta.status_code == 200 and respuesta.json()["por_omision"] == "001"


# --- R2: abrir un borrador ---------------------------------------------------------------------


def test_r2_abre_of001_v001_con_el_total_de_la_memoria() -> None:
    navegador, ficha = _ana()
    respuesta = _abrir(navegador, ficha)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert len(cuerpo["id"]) >= 16
    total = cuerpo["resumen"]["total"]
    assert D("2703.85") <= D(total["exacto"]) <= D("2703.87")
    assert total["texto"] == "2703.86"
    assert cuerpo["resumen"]["moneda"] == "USD" and cuerpo["base"]["moneda"] == "USD"
    assert cuerpo["base"]["solo_lectura"] is False
    assert cuerpo["resumen"]["cambios"] == 0 and cuerpo["resumen"]["rev"] == 0
    assert cuerpo["resumen"]["hay_plan"] is True
    assert (cuerpo["base"]["proyecto"], cuerpo["base"]["version"]) == (NOMBRE_OF001, "001")
    assert (cuerpo["base"]["vigente"], cuerpo["base"]["espacio_de"]) == ("001", "001")
    assert cuerpo["resumen"]["version_mas_nueva"] is None
    assert cuerpo["instantanea"] == {"creadas": 0, "mensaje": None}


def test_r2_sobre_ti001_no_tiene_espacio_y_no_escribe_versiones_ni_filas_esp(_casos) -> None:
    ruta = _poner(_casos["ti001"])
    preparar_base(ruta)  # la primera peticion la migra; lo que se compara es lo que ESCRIBE abrir
    antes = _volcado(ruta)
    navegador, ficha = _ana()
    respuesta = _abrir(navegador, ficha, NOMBRE_TI001, caso_ti001.CODIGO)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["base"]["espacio_de"] is None
    assert D(cuerpo["resumen"]["total"]["exacto"]) > 0
    assert cuerpo["resumen"]["cambios"] == 0
    despues = _volcado(ruta)
    assert despues == antes  # TI-001 ya traia su instantanea: abrir no escribe nada
    assert not [t for t in despues if t.startswith("esp_") and despues[t]]


def test_r2_crea_la_instantanea_si_falta_y_lo_informa_con_su_texto(_entorno: Path) -> None:
    motor = crear_motor(f"sqlite:///{_entorno.as_posix()}")
    with abrir_sesion(motor) as sesion:
        borrar_instantanea(sesion, NOMBRE_OF001)
    motor.dispose()
    dependencias.cerrar_motores()
    assert _filas(_entorno, "composicion_version") == 0
    navegador, ficha = _ana()
    cuerpo = _abrir(navegador, ficha).json()
    creadas = cuerpo["instantanea"]["creadas"]
    assert creadas == _filas(_entorno, "composicion_version") > 0
    clasico = (
        "Se creo y registro la instantanea de las composiciones de esta version "
        f"({creadas} partidas): sus APU ya no cambian si cambia el catalogo."
    )
    assert normalizar_texto(cuerpo["instantanea"]["mensaje"]) == normalizar_texto(clasico)
    otra = _abrir(navegador, ficha).json()
    assert otra["instantanea"] == {"creadas": 0, "mensaje": None}
    # el registro de la creacion lleva a la persona de la sesion (RF-82), no «sistema»
    with closing(sqlite3.connect(_entorno)) as bd:
        responsables = {r[0] for r in bd.execute("SELECT responsable FROM registro_cambio")}
    assert "Ana <ana>" in responsables and "sistema" not in responsables


CADENA_REGISTRO = (
    "Cadena rota en la versión 001: su registro de cambios no coincide con su huella; alguien "
    "cambió la base fuera del sistema. Revíselo con el administrador antes de entregar un paquete."
)
CADENA_SIN_ESLABON = (
    "Cadena rota en la versión 001: no tiene eslabón; alguien cambió la base fuera del sistema. "
    "Revíselo con el administrador antes de entregar un paquete."
)


def _sin_instantanea(ruta: Path, *, sellada: bool) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as sesion:
        borrar_instantanea(sesion, NOMBRE_OF001)
    motor.dispose()
    if not sellada:
        with closing(sqlite3.connect(ruta)) as bd:  # una version de antes de la cadena
            bd.execute("DELETE FROM eslabon_version")
            bd.commit()


def _cadena(ruta: Path) -> tuple[bool, str]:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            estado = entrega.estado_de_la_cadena(sesion, NOMBRE_OF001)
    finally:
        motor.dispose()
    assert estado is not None
    return estado.integra, estado.mensaje


@pytest.mark.parametrize(
    ("sellada", "mensaje"), [(True, CADENA_REGISTRO), (False, CADENA_SIN_ESLABON)]
)
def test_r2_sobre_una_version_sin_instantanea_deja_la_cadena_como_la_deja_la_clasica(
    sellada: bool, mensaje: str, _casos, _entorno: Path, tmp_path: Path
) -> None:
    """PRUEBA DE CARACTERIZACION (3b-B11, clausula de la cadena, inviable bajo Plan C).

    El diseno pedia que la cadena quedara integra tras abrir una version sin instantanea. No
    es asi, tampoco en la clasica: `abrir_version` escribe un `RegistroCambio` sobre una version ya
    sellada (o no sellada). Bajo el Plan C la copia es identica a `ui.hoja`, asi que R2, la copia y
    la clasica dejan EXACTAMENTE el mismo estado; los literales son lo observado (bitacora
    `2026-10-19-hoja-3b1-cadena-heredada.md`, decision para Eugenio)."""
    from aplicacion import hoja as copia

    resultados = {}
    for nombre, modulo in (("clasica", clasica), ("copia", copia)):
        ruta = tmp_path / f"{nombre}.db"
        shutil.copyfile(_casos["of001"], ruta)
        _sin_instantanea(ruta, sellada=sellada)
        motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
        with abrir_sesion(motor) as sesion:
            entrega.con_anexos_de_cadena(sesion)
            modulo.abrir_version(
                sesion, Catalogo(sesion), NOMBRE_OF001, "001", responsable="Ana <ana>"
            )
        motor.dispose()
        resultados[nombre] = _cadena(ruta)
    _sin_instantanea(_entorno, sellada=sellada)
    dependencias.cerrar_motores()
    navegador, ficha = _ana()
    assert _abrir(navegador, ficha).status_code == 201
    resultados["R2"] = _cadena(_entorno)
    assert resultados == {nombre: (False, mensaje) for nombre in ("clasica", "copia", "R2")}


def test_r2_de_un_proyecto_sin_versiones_abre_un_borrador_en_blanco(_entorno: Path) -> None:
    _con_proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": "Proyecto nuevo", "version": None},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["base"]["version"] is None and cuerpo["base"]["lista"] is None
    assert D(cuerpo["resumen"]["total"]["exacto"]) == 0 and cuerpo["resumen"]["cambios"] == 0
    assert cuerpo["resumen"]["hay_plan"] is False


def test_r2_sin_version_en_un_proyecto_que_ya_las_tiene_es_409() -> None:
    navegador, ficha = _ana()
    respuesta = navegador.post(
        "/v1/hoja/borradores", json={"proyecto": NOMBRE_OF001}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 409
    assert "ya tiene versiones" in respuesta.json()["detalle"]


def test_r2_proyecto_o_version_inexistente_es_404_con_los_textos_de_la_clasica() -> None:
    navegador, ficha = _ana()
    sin_proyecto = _abrir(navegador, ficha, "Z", "001")
    assert sin_proyecto.status_code == 404
    assert sin_proyecto.json() == {"detalle": "El proyecto «Z» no existe en este caso."}
    sin_version = _abrir(navegador, ficha, NOMBRE_OF001, "999")
    assert sin_version.status_code == 404
    assert sin_version.json() == {
        "detalle": (
            f"El proyecto {NOMBRE_OF001!r} no tiene una version '999': elija una de la lista."
        )
    }
    assert _versiones(navegador, "Z").status_code == 404
    assert _versiones(navegador, "Z").json() == {
        "detalle": "El proyecto «Z» no existe en este caso."
    }


# --- R3 y R4 -------------------------------------------------------------------------------


def test_r3_devuelve_lo_mismo_que_r2_sin_la_instantanea() -> None:
    navegador, ficha = _ana()
    abierto = _abrir(navegador, ficha).json()
    respuesta = navegador.get(f"/v1/hoja/borradores/{abierto['id']}")
    assert respuesta.status_code == 200
    assert respuesta.json() == {k: abierto[k] for k in ("id", "base", "resumen")}


def test_r4_descarta_es_idempotente_y_luego_r3_dice_que_ya_no_esta() -> None:
    navegador, ficha = _ana()
    id_ = _abrir(navegador, ficha).json()["id"]
    cabeceras = protegida(ficha)
    assert navegador.delete(f"/v1/hoja/borradores/{id_}", headers=cabeceras).status_code == 204
    assert navegador.delete(f"/v1/hoja/borradores/{id_}", headers=cabeceras).status_code == 204
    assert navegador.delete(f"/v1/hoja/borradores/{ID_AJENO}", headers=cabeceras).status_code == 204
    respuesta = navegador.get(f"/v1/hoja/borradores/{id_}")
    assert respuesta.status_code == 404 and respuesta.json() == {"detalle": FALTA}


def test_un_id_con_forma_invalida_es_422_sin_eco() -> None:
    navegador, _ = _ana()
    respuesta = navegador.get("/v1/hoja/borradores/corto")
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_FORMA}
    assert "corto" not in respuesta.text


def test_el_borrador_de_otra_ficha_no_existe_ni_en_get_ni_en_delete() -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()  # otra ficha de la misma cuenta: otra huella
    assert ficha_uno != ficha_otro
    id_ = _abrir(uno, ficha_uno).json()["id"]
    ajeno = otro.get(f"/v1/hoja/borradores/{id_}")
    assert ajeno.status_code == 404 and ajeno.json() == {"detalle": FALTA}
    assert id_ not in ajeno.text
    borrado = otro.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha_otro))
    assert borrado.status_code == 204
    assert uno.get(f"/v1/hoja/borradores/{id_}").status_code == 200  # no lo borro


# --- 3b-B12: acceso ---------------------------------------------------------------------------

_RUTAS = [
    ("GET", "/v1/hoja/versiones?proyecto=P", True),
    ("POST", "/v1/hoja/borradores", False),
    ("GET", "/v1/hoja/borradores/" + ID_AJENO, False),
    ("DELETE", "/v1/hoja/borradores/" + ID_AJENO, False),
]


def _pedir(navegador: TestClient, metodo: str, ruta: str, ficha: str | None, **extra):
    cabeceras = protegida(ficha) if ficha else {}
    cabeceras.update(extra.pop("headers", {}))
    cuerpo = {"json": {"proyecto": "P", "version": None}} if metodo == "POST" else {}
    return navegador.request(metodo, ruta, headers=cabeceras, **cuerpo)


@pytest.mark.parametrize(("metodo", "ruta", "acepta_clave"), _RUTAS)
def test_sin_sesion_ni_clave_es_401(metodo: str, ruta: str, acepta_clave: bool) -> None:
    respuesta = _pedir(cliente(app), metodo, ruta, None, headers={"Origin": ORIGEN})
    assert respuesta.status_code == 401 and "detalle" in respuesta.json()
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("metodo", "ruta", "acepta_clave"), _RUTAS)
def test_rita_que_revisa_no_puede_usar_la_hoja(metodo: str, ruta: str, acepta_clave: bool) -> None:
    navegador, ficha = con_cuenta(app, "rita")
    respuesta = _pedir(navegador, metodo, ruta, ficha)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("metodo", "ruta", "acepta_clave"), _RUTAS)
def test_tomas_con_contrasena_temporal_no_pasa(metodo: str, ruta: str, acepta_clave: bool) -> None:
    navegador, ficha = con_cuenta(app, "tomas")
    assert _pedir(navegador, metodo, ruta, ficha).status_code == 403


@pytest.mark.parametrize(("metodo", "ruta", "acepta_clave"), _RUTAS)
def test_la_clave_de_api_solo_sirve_para_leer_versiones(
    metodo: str, ruta: str, acepta_clave: bool
) -> None:
    respuesta = _pedir(
        cliente(app), metodo, ruta, None, headers={CABECERA: crear_clave_de_prueba()}
    )
    if acepta_clave:
        assert respuesta.status_code in (200, 404)
    else:
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detalle": SOLO_CUENTA}
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [("POST", "/v1/hoja/borradores"), ("DELETE", "/v1/hoja/borradores/" + ID_AJENO)],
)
def test_un_metodo_que_escribe_exige_csrf_y_origen_propio(metodo: str, ruta: str) -> None:
    navegador, ficha = _ana()
    sin_csrf = navegador.request(metodo, ruta, headers={"Origin": ORIGEN}, json={})
    assert sin_csrf.status_code == 403
    ajeno = navegador.request(
        metodo, ruta, headers=protegida(ficha, origen="http://evil.example"), json={}
    )
    assert ajeno.status_code == 403
    sin_origen = navegador.request(metodo, ruta, headers=protegida(ficha, origen=None), json={})
    assert sin_origen.status_code == 403


# --- 3b-B13: no-store y 422 sin eco ---------------------------------------------------------


def test_no_store_en_exito_404_y_422_de_cada_ruta() -> None:
    navegador, ficha = _ana()
    abierto = _abrir(navegador, ficha)
    id_ = abierto.json()["id"]
    respuestas = [
        abierto,
        _versiones(navegador),
        _versiones(navegador, "Z"),  # 404
        navegador.get("/v1/hoja/versiones"),  # 422
        navegador.get(f"/v1/hoja/borradores/{id_}"),
        navegador.get("/v1/hoja/borradores/" + ID_AJENO),  # 404
        navegador.post("/v1/hoja/borradores", json={}, headers=protegida(ficha)),  # 422
        navegador.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha)),
    ]
    assert [r.status_code for r in respuestas] == [201, 200, 404, 422, 200, 404, 422, 204]
    assert all(r.headers["cache-control"] == "no-store" for r in respuestas)


def test_el_422_no_repite_lo_enviado_y_combina_las_dos_clases_de_ruta() -> None:
    navegador, ficha = _ana()
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": {"x": CENTINELA}},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 422
    assert CENTINELA not in respuesta.text
    assert respuesta.json() == {"detalle": MENSAJE_FORMA}
    assert respuesta.headers["cache-control"] == "no-store"  # y la cabecera tambien


def test_una_celda_de_mas_de_500_caracteres_es_422_sin_eco() -> None:
    navegador, ficha = _ana()
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": CENTINELA * 60, "version": None},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 422 and CENTINELA not in respuesta.text


# --- 3b-B16: ningun float --------------------------------------------------------------------


def _sin_float(valor) -> None:
    if isinstance(valor, float):
        raise AssertionError(f"float en el JSON: {valor!r}")
    if isinstance(valor, dict):
        for v in valor.values():
            _sin_float(v)
    elif isinstance(valor, list):
        for v in valor:
            _sin_float(v)


def test_ningun_numero_del_json_es_float_y_todo_monto_es_texto() -> None:
    navegador, ficha = _ana()
    respuesta = _abrir(navegador, ficha)
    cuerpo = json.loads(respuesta.text, parse_float=lambda t: float("nan"))
    _sin_float(cuerpo)  # `parse_float` convertiria cualquier decimal sin comillas en float
    resumen = cuerpo["resumen"]
    assert isinstance(resumen["total"]["texto"], str)
    assert isinstance(resumen["total"]["exacto"], str)
    assert isinstance(resumen["cambios"], int) and isinstance(resumen["rev"], int)
    for hallazgo in resumen["hallazgos"]:
        assert isinstance(hallazgo["total"], int)
    _sin_float(json.loads(_versiones(navegador).text, parse_float=lambda t: float("nan")))


# --- 3b-B28: cambio de caso ------------------------------------------------------------------


def _otro_caso(origen: Path) -> Path:
    destino = config.carpeta_casos() / "Otro caso.db"
    shutil.copyfile(origen, destino)
    return destino


def test_cambiar_de_caso_olvida_los_borradores_y_ninguna_base_recibe_filas(
    _casos, _entorno
) -> None:
    navegador, ficha = _ana()
    otro = _otro_caso(_casos["ti001"])
    preparar_base(_entorno)
    preparar_base(otro)
    id_ = _abrir(navegador, ficha).json()["id"]
    antes_a, antes_b = _volcado(_entorno), _volcado(otro)
    cambio = navegador.post(
        "/v1/casos/actual", json={"nombre": otro.name}, headers=protegida(ficha)
    )
    assert cambio.status_code == 200, cambio.text
    assert hoja_borradores.listar(_huella(ficha)) == []  # `caso_web.fijar` los olvido
    assert navegador.get(f"/v1/hoja/borradores/{id_}").status_code == 404
    borrado = navegador.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha))
    assert borrado.status_code == 204
    assert _volcado(_entorno) == antes_a and _volcado(otro) == antes_b


def test_un_borrador_que_sobrevive_a_un_cambio_de_caso_da_409_fijo_y_no_toca_ninguna_base(
    _casos, _entorno
) -> None:
    """Defensa en profundidad: si el caso de la ficha difiere del de apertura, R3 y R4 dan 409."""
    navegador, ficha = _ana()
    otro = _otro_caso(_casos["ti001"])
    preparar_base(_entorno)
    preparar_base(otro)
    id_ = _abrir(navegador, ficha).json()["id"]
    antes_a, antes_b = _volcado(_entorno), _volcado(otro)
    caso_web._elegidos[_huella(ficha)] = otro.resolve()  # el cambio sin pasar por `fijar`
    leer = navegador.get(f"/v1/hoja/borradores/{id_}")
    borrar = navegador.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha))
    for respuesta in (leer, borrar):
        assert respuesta.status_code == 409
        assert respuesta.json() == {"detalle": OTRO_CASO}
        assert respuesta.headers["cache-control"] == "no-store"
    assert _volcado(_entorno) == antes_a and _volcado(otro) == antes_b
    assert hoja_borradores.obtener(_huella(ficha), id_) is not None  # el 409 no lo descarto


# --- memoria: el 5.o borrador de una ficha ---------------------------------------------------


def test_el_quinto_borrador_de_una_ficha_descarta_el_primero() -> None:
    navegador, ficha = _ana()
    ids = [_abrir(navegador, ficha).json()["id"] for _ in range(5)]
    assert navegador.get(f"/v1/hoja/borradores/{ids[0]}").status_code == 404
    assert all(navegador.get(f"/v1/hoja/borradores/{i}").status_code == 200 for i in ids[1:])


# --- 3b-B24 y 3b-B26 ----------------------------------------------------------------------


def test_docs_api_json_esta_al_dia() -> None:
    """3b-B24: `scripts/exportar_openapi.py` no deja diferencias pendientes."""
    guardado = json.loads((RAIZ / "docs" / "api.json").read_text(encoding="utf-8"))
    assert guardado == json.loads(json.dumps(app.openapi(), ensure_ascii=False))
    rutas = {r for r in guardado["paths"] if r.startswith("/v1/hoja")}
    assert rutas == {
        "/v1/hoja/versiones",
        "/v1/hoja/borradores",
        "/v1/hoja/borradores/{id}",
        "/v1/hoja/borradores/{id}/vistas/apu",
        "/v1/hoja/borradores/{id}/vistas/espacio",
        "/v1/hoja/borradores/{id}/vistas/presupuesto",
    }


def test_la_api_corre_en_un_solo_proceso_sin_workers_ni_reload() -> None:
    """3b-B26: el registro de borradores es de memoria del proceso."""
    from operacion.lanzador import orden_uvicorn

    orden = orden_uvicorn(Path("python"), "127.0.0.1", 8000)
    assert not [a for a in orden if a.startswith(("--workers", "--reload"))]


# --- R5 a R8: las vistas de las pestañas (3b-2) ----------------------------------------------


def _vista(navegador: TestClient, id_: str, nombre: str, **params):
    return navegador.get(f"/v1/hoja/borradores/{id_}/vistas/{nombre}", params=params)


def _abierta(navegador: TestClient, ficha: str, **kwargs) -> str:
    respuesta = _abrir(navegador, ficha, **kwargs)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def test_r5_of001_da_las_cantidades_derivadas_de_la_memoria() -> None:
    """3b-B7: AF-LLAVE 3; tubería de drenaje 2" 4,345 y de agua fría 1/2" 8,250 (memoria §2.4)."""
    navegador, ficha = _ana()
    respuesta = _vista(navegador, _abierta(navegador, ficha), "espacio")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    por_partida = {d["partida"]: d for d in cuerpo["derivadas"]}
    assert D(por_partida["AF-LLAVE"]["cantidad"]["exacto"]) == D("3")
    assert D(por_partida["DR-TUB-PVC-2"]["cantidad"]["exacto"]) == D("4.345")
    assert D(por_partida["AF-TUB-PVC-1/2"]["cantidad"]["exacto"]) == D("8.250")
    assert por_partida["AF-TUB-PVC-1/2"]["cantidad"]["texto"] == "8.25"
    assert D("2703.85") <= D(cuerpo["total"]["exacto"]) <= D("2703.87")
    assert (cuerpo["moneda"], cuerpo["pendientes"], cuerpo["vacio_mensaje"]) == ("USD", 0, None)


def test_r5_trae_las_cinco_tablas_con_sus_columnas_en_el_orden_de_la_clasica() -> None:
    navegador, ficha = _ana()
    cuerpo = _vista(navegador, _abierta(navegador, ficha), "espacio").json()
    assert [t["clave"] for t in cuerpo["tablas"]] == [
        "origenes",
        "ambientes",
        "fuentes",
        "puntos",
        "tramos",
    ]
    ambientes = cuerpo["tablas"][1]
    assert [c["clave"] for c in ambientes["columnas"]] == [
        "id",
        "nombre",
        "x0",
        "y0",
        "largo",
        "ancho",
        "alto",
        "origen_id",
    ]
    assert ambientes["con_estado"] is True and cuerpo["tablas"][0]["con_estado"] is False
    superficie = next(c for c in cuerpo["tablas"][3]["columnas"] if c["clave"] == "superficie")
    assert superficie["lista"] == [
        {"valor": "pared", "rotulo": "Pared"},
        {"valor": "techo", "rotulo": "Techo"},
        {"valor": "piso", "rotulo": "Piso"},
    ]
    assert ambientes["columnas"][1]["lista"] is None
    assert [f["id"] for f in cuerpo["filas"]["ambientes"]] == [
        "BAN-01",
        "COC-01",
        "CT-01",
        "REC-01",
        "ZA",
        "ZB",
    ]


def test_r5_el_estado_de_cada_fila_lleva_severidad_y_texto_de_la_clasica() -> None:
    navegador, ficha = _ana()
    cuerpo = _vista(navegador, _abierta(navegador, ficha), "espacio").json()
    estado = cuerpo["estado"]["esp_ambientes:BAN-01"]
    assert estado["severidad"] == "ADVERTENCIA"
    assert estado["texto"].startswith("ADVERTENCIA: ambiente BAN-01: la medida es un supuesto")


def test_r5_de_ti001_no_tiene_espacio_ni_cantidades_derivadas_y_lo_dice(_casos) -> None:
    _poner(_casos["ti001"])
    navegador, ficha = _ana()
    id_ = _abierta(navegador, ficha, proyecto=NOMBRE_TI001, version=caso_ti001.CODIGO)
    cuerpo = _vista(navegador, id_, "espacio").json()
    assert cuerpo["derivadas"] == [] and cuerpo["estado"] == {}
    assert cuerpo["vacio_mensaje"].startswith("El borrador todavía no deriva cantidades")
    assert all(filas == [] for filas in cuerpo["filas"].values())
    assert (
        D(cuerpo["total"]["exacto"]) > 0
    )  # los items de la version cuentan aunque no haya espacio


def test_las_vistas_no_escriben_nada_en_la_base(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abierta(navegador, ficha)
    antes = _volcado(_entorno)
    assert _vista(navegador, id_, "espacio").status_code == 200
    assert _volcado(_entorno) == antes


def test_r6_of001_lista_los_30_renglones_con_cantidad_texto_y_montos_exactos() -> None:
    navegador, ficha = _ana()
    respuesta = _vista(navegador, _abierta(navegador, ficha), "presupuesto")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert len(cuerpo["filas"]) == 30
    llave = next(f for f in cuerpo["filas"] if f["partida"] == "AF-LLAVE")
    # a mano: costo directo 10,433785 × 1,15 × 1,10 = 13,19874 (NORMAS.md §4)
    assert abs(D(llave["pu"]["exacto"]) - D("13.19874")) <= D("0.0001")
    assert llave["pu"]["texto"] == "13.20" and llave["total"]["texto"] == "39.60"
    assert (llave["cantidad"], llave["cantidad_calculada"], llave["escrita"]) == ("3", "3", False)
    assert llave["estado"] == {"severidad": None, "texto": "OK"}
    assert D("2703.85") <= D(cuerpo["total"]["exacto"]) <= D("2703.87")
    assert (cuerpo["moneda"], cuerpo["vacio_mensaje"]) == ("USD", None)


def test_r6_de_ti001_usa_los_renglones_de_la_version_y_el_total_del_caso(_casos) -> None:
    _poner(_casos["ti001"])
    navegador, ficha = _ana()
    id_ = _abierta(navegador, ficha, proyecto=NOMBRE_TI001, version=caso_ti001.CODIGO)
    cuerpo = _vista(navegador, id_, "presupuesto").json()
    assert {f["partida"] for f in cuerpo["filas"]} == set(caso_ti001.COMPOSICIONES)
    assert D(cuerpo["total"]["exacto"]) == caso_ti001.elaborar_caso().presupuesto.total


def test_r7_sin_parametros_selecciona_la_primera_partida_y_trae_su_cierre() -> None:
    navegador, ficha = _ana()
    respuesta = _vista(navegador, _abierta(navegador, ficha), "apu")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert len(cuerpo["partidas"]) == 30 and cuerpo["sin_coincidencias"] is False
    assert cuerpo["seleccionada"] == "AF-CODO-1/2"
    assert cuerpo["detalle"]["codigo"] == "AF-CODO-1/2" and cuerpo["vacio_mensaje"] is None
    assert [c["concepto"] for c in cuerpo["detalle"]["cierre"]][-1] == "= Precio unitario"


def test_r7_con_partida_da_la_cascada_a_mano_de_af_llave() -> None:
    navegador, ficha = _ana()
    cuerpo = _vista(navegador, _abierta(navegador, ficha), "apu", partida="AF-LLAVE").json()
    detalle = cuerpo["detalle"]
    assert cuerpo["seleccionada"] == "AF-LLAVE" and detalle["rendimiento"] == "20"
    assert [g["subtotal"]["exacto"] for g in detalle["grupos"]] == ["7.7483", "0.71523", "1.970255"]
    # costo directo 10,433785 × 1,15 × 1,10 = 13,198738025 (a mano; NORMAS.md §4)
    assert abs(D(detalle["metricas"]["precio_unitario"]["exacto"]) - D("13.198738025")) <= D(
        "0.000001"
    )
    assert detalle["metricas"]["precio_unitario"]["texto"] == "13.20"
    assert detalle["estados"] == [] and detalle["solo_lectura_insumos"] is False


def test_r7_buscar_filtra_y_sin_coincidencias_devuelve_todas() -> None:
    navegador, ficha = _ana()
    id_ = _abierta(navegador, ficha)
    picado = _vista(navegador, id_, "apu", buscar="picado").json()
    assert [p["codigo"] for p in picado["partidas"]] == [
        "AF-PICADO-PARED",
        "DR-PICADO-PARED",
        "DR-PICADO-PISO",
    ]
    assert picado["seleccionada"] == "AF-PICADO-PARED"
    ninguna = _vista(navegador, id_, "apu", buscar="zzz").json()
    assert ninguna["sin_coincidencias"] is True and len(ninguna["partidas"]) == 30


def test_r7_un_texto_de_mas_de_500_caracteres_es_422_sin_eco() -> None:
    navegador, ficha = _ana()
    id_ = _abierta(navegador, ficha)
    for parametro in ("partida", "buscar"):
        respuesta = _vista(navegador, id_, "apu", **{parametro: CENTINELA * 60})
        assert respuesta.status_code == 422 and CENTINELA not in respuesta.text
        assert respuesta.headers["cache-control"] == "no-store"


def test_r8_of001_trae_la_matriz_del_plan_y_la_curva_que_cierra_en_el_total() -> None:
    navegador, ficha = _ana()
    respuesta = _vista(navegador, _abierta(navegador, ficha), "plan")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["hay_plan"] is True and cuerpo["mensaje"] is None and cuerpo["moneda"] == "USD"
    assert cuerpo["etiquetas"][:3] == ["Dia 1", "Dia 2", "Dia 3"] and len(cuerpo["etiquetas"]) == 30
    assert cuerpo["filas"][0]["partida"] == "AF-CODO-1/2"
    assert cuerpo["filas"][0]["valores"]["Dia 1"] == "1"
    ultimo = cuerpo["curva"][-1]
    assert D("2703.85") <= D(ultimo["acumulado"]["exacto"]) <= D("2703.87")
    assert ultimo["porcentaje"]["texto"] == "100.00"
    assert cuerpo["curva"][22]["periodo"] == "Dia 23"  # el punto de equilibrio de la memoria


def test_r8_de_ti001_usa_su_propio_plan(_casos) -> None:
    _poner(_casos["ti001"])
    navegador, ficha = _ana()
    id_ = _abierta(navegador, ficha, proyecto=NOMBRE_TI001, version=caso_ti001.CODIGO)
    cuerpo = _vista(navegador, id_, "plan").json()
    assert cuerpo["hay_plan"] is True and len(cuerpo["etiquetas"]) == len(caso_ti001.PLAN)
    total = caso_ti001.elaborar_caso().presupuesto.total
    assert D(cuerpo["curva"][-1]["acumulado"]["exacto"]) == total


def test_r8_de_un_proyecto_sin_versiones_no_tiene_plan_y_lo_dice(_entorno: Path) -> None:
    _con_proyecto_nuevo(_entorno)
    navegador, ficha = _ana()
    id_ = _abierta(navegador, ficha, proyecto="Proyecto nuevo", version=None)
    cuerpo = _vista(navegador, id_, "plan").json()
    assert (cuerpo["hay_plan"], cuerpo["etiquetas"], cuerpo["filas"], cuerpo["curva"]) == (
        False,
        [],
        [],
        [],
    )
    assert cuerpo["mensaje"] == (
        "Esta versión no tiene plan de trabajo, así que no hay curva de inversión."
    )
    # el resto de las vistas de un borrador en blanco responde vacío y no falla
    assert _vista(navegador, id_, "presupuesto").json()["vacio_mensaje"] is not None
    assert _vista(navegador, id_, "apu").json()["detalle"] is None
    assert _vista(navegador, id_, "espacio").json()["derivadas"] == []
