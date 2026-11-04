"""Agregar y quitar partidas en la Hoja, sus notas y el borrador en la moneda de la obra (Tarea 9).

Contrato (plan `docs/planes/PLAN_MONTAR_PRESUPUESTO.md`, Tarea 9 y su entrada en «Cambios por el
diseño de módulos»):

- `POST /v1/hoja/borradores/{id}/partidas` `{rev, codigo, cantidad, calculo, nota}` → 200
  `{rev, resumen, clave}`; 404 «La partida «X» no está en el catálogo: compóngala primero en
  Componer.»; 422 con la regla de las cifras o el texto del cálculo (Tarea 8); 409 `rev`.
- `POST /v1/hoja/borradores/{id}/partidas/quitar` `{rev, clave}` → 200 `{rev, resumen}`; una fila
  del espacio, 422 con el texto exacto.
- La nota (hasta 500 caracteres) se guarda con la versión y vuelve al abrirla; la fila del
  presupuesto trae `nota`, `calculo` y `quitable`; el resumen, `moneda` y `espacio_vacio`.
- Foco de revisión 1: una obra en USD dentro de una carpeta en Bs se valora con la lista de la
  carpeta convertida con la tasa del BCV (alcance proyecto, con su tasa); sin tasa de los últimos
  7 días, 409 con el texto de la tasa y nada guardado.
- La fuente «cantidades sin cálculo» de la mesa (`pendientes_sin_calculo`).

Datos FICTICIOS: la «Vivienda Demo 80 m2» con OBRA-01 a OBRA-06 de `tests/fixtures/
carpeta_aprobaciones.py` (OBRA-04 «Paredes de bloque de arcilla», m2; material 12,00 Bs), en la
carpeta «Contratista Demo, C.A.» que trabaja en Bs; la tasa ficticia es 40,00 Bs/USD. Oráculos a
mano: los textos del plan y de la Tarea 8, 12,00 / 40 = 0,3 USD, y los recuentos con `sqlite3`.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.rutas import hoja as rutas_hoja
from aplicacion import hoja_borradores
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from core import models
from core.budget import crear_proyecto
from core.budget.moneda import declarar_moneda
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts.dominio import Dominio
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import COMPOSICIONES
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from tests.fixtures.hoja_versiones_api import registrar_tasa
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
HOY = date(2026, 10, 25)
FECHA_LISTA = date(2026, 10, 1)
FECHA_TASA = date(2026, 10, 24)
VIVIENDA = "Vivienda Demo 80 m2"
CASA_USD = "Casa Demo en USD"
NOTA = "6 m × 35 m de muro"
FUENTE = "Medición en sitio del 24/10/2026"
ORIGEN = "http://127.0.0.1:8000"
ID_AJENO = "a" * 22
CENTINELA = "VALOR-CENTINELA"

CIFRA = "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56."
NO_COINCIDE = "El cálculo da 16 y la cantidad es 15: corrija uno de los dos."
FUERA_DEL_CATALOGO = "La partida «OBRA-99» no está en el catálogo: compóngala primero en Componer."
FILA_DEL_ESPACIO = "Esa fila sale del espacio: cámbiela en «Espacio y metrajes»."
FALTA = (
    "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). "
    "Lo que no guardó se perdió: abra la versión otra vez."
)
REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo."
SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar."
SOLO_CUENTA = "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."
TEXTO_LLANO = (
    "La cantidad de OBRA-04 (210 m2) se escribió a mano sin cálculo: escriba cómo se obtuvo si "
    "quiere que Sílice la pueda verificar."
)
FORMA_PARTIDA = (
    "La partida no tiene la forma esperada: envíe rev (entero), codigo, cantidad, calculo y nota "
    "como texto; la nota, de hasta 500 caracteres."
)
FORMA_QUITAR = "La petición no tiene la forma esperada: envíe rev (entero) y la clave de la fila."
SIN_LISTA_A_LA_FECHA = (
    "Esta carpeta de trabajo no tiene lista de precios para armar vigente al 01/09/2026: su "
    "primera lista rige desde el 01/10/2026."
)
FORMA_GUARDAR = (
    "El guardado no tiene la forma esperada: envíe rev (entero) y la fuente como texto de hasta "
    "300 caracteres."
)
CODIGO_SOLO_PRIMERA = (
    "El código se elige solo al guardar la primera versión; las siguientes siguen su numeración."
)
#: Una fila que deriva del espacio de OF-001 (la tubería de 3/4" de la fuente F1).
FILA_OF001 = "AF-CODO-3/4|esp_fuentes:F1"


# --- los casos de la prueba ---------------------------------------------------------------------


def _carpeta_en_bs(ruta: Path, *, con_tasa: bool) -> Path:
    """La carpeta ficticia en Bs: la lista «Lista Bs de prueba» con OBRA-01 a OBRA-06, la obra
    VIVIENDA en Bs y CASA_USD en USD, ambas sin versiones; con `con_tasa`, la tasa del BCV del
    24/10/2026 a 40,00 Bs/USD."""
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            lista = models.ListaPrecios(
                nombre="Lista Bs de prueba",
                moneda="Bs",
                fecha_vigencia=FECHA_LISTA,
                origen="prueba",
            )
            sesion.add(lista)
            sesion.flush()
            catalogo = Catalogo(sesion)
            for composicion in COMPOSICIONES.values():
                catalogo.cargar_composicion(
                    composicion, lista, Dominio.CIVIL, FECHA_LISTA, "prueba"
                )
            declarar_moneda_de_la_carpeta(
                sesion, "Bs", responsable="Ana <ana>", ahora=datetime(2026, 10, 1, 8, 0)
            )
            for nombre, moneda in ((VIVIENDA, "Bs"), (CASA_USD, "USD")):
                proyecto = crear_proyecto(sesion, nombre, dominio=Dominio.CIVIL)
                declarar_moneda(sesion, proyecto, moneda, responsable="Ana <ana>")
            sesion.commit()
    finally:
        motor.dispose()
    if con_tasa:
        registrar_tasa(ruta, FECHA_TASA, "40.00")
    return ruta


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_partidas")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "bs": _carpeta_en_bs(carpeta / "bs.db", con_tasa=False),
        "bs_con_tasa": _carpeta_en_bs(carpeta / "bs_con_tasa.db", con_tasa=True),
        "of001": plantilla_of001(carpeta / "of001.db"),
    }


@pytest.fixture(autouse=True)
def _entorno(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalación con cuentas y la carpeta en Bs (con tasa) como caso por defecto; hoy es el
    25/10/2026."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: HOY)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["bs_con_tasa"], ruta)
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    dependencias.cerrar_motores()


def _poner(origen: Path) -> Path:
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    shutil.copyfile(origen, ruta)
    return ruta


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def _consulta(ruta: Path, sql: str, *parametros) -> list[tuple]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        return bd.execute(sql, parametros).fetchall()


def _ana() -> tuple[TestClient, str]:
    return con_cuenta(app, "ana")


def _abrir(navegador: TestClient, ficha: str, proyecto: str = VIVIENDA, version=None):
    return navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": proyecto, "version": version},
        headers=protegida(ficha),
    )


def _abierto(navegador: TestClient, ficha: str, proyecto: str = VIVIENDA, version=None) -> str:
    respuesta = _abrir(navegador, ficha, proyecto, version)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _agregar(navegador: TestClient, ficha: str, id_: str, rev: int = 0, **campos):
    cuerpo = {"rev": rev, "codigo": "OBRA-04", "cantidad": "", "calculo": "", "nota": ""}
    cuerpo.update(campos)
    return navegador.post(
        f"/v1/hoja/borradores/{id_}/partidas", json=cuerpo, headers=protegida(ficha)
    )


def _quitar(navegador: TestClient, ficha: str, id_: str, rev: int, clave: str):
    return navegador.post(
        f"/v1/hoja/borradores/{id_}/partidas/quitar",
        json={"rev": rev, "clave": clave},
        headers=protegida(ficha),
    )


def _guardar(navegador: TestClient, ficha: str, id_: str, rev: int, **extra):
    return navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": rev, "fuente": FUENTE, **extra},
        headers=protegida(ficha),
    )


def _resumen(navegador: TestClient, id_: str) -> dict:
    respuesta = navegador.get(f"/v1/hoja/borradores/{id_}")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["resumen"]


def _filas(navegador: TestClient, id_: str) -> list[dict]:
    respuesta = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/presupuesto")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["filas"]


def _fila(navegador: TestClient, id_: str, clave: str) -> dict:
    return next(f for f in _filas(navegador, id_) if f["clave"] == clave)


def _sin_cache(respuesta) -> None:
    assert respuesta.headers["cache-control"] == "no-store"


# --- el borrador en blanco dice la moneda de la obra (O-7) --------------------------------------


def test_una_obra_nueva_en_bs_abre_en_bs_y_sin_espacio() -> None:
    navegador, ficha = _ana()
    respuesta = _abrir(navegador, ficha)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["resumen"]["moneda"] == "Bs"
    assert cuerpo["resumen"]["espacio_vacio"] is True
    assert cuerpo["base"]["moneda"] == "Bs"


def test_una_version_con_espacio_no_esta_vacia(_casos: dict[str, Path]) -> None:
    _poner(_casos["of001"])
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha, NOMBRE_OF001, "001")
    assert _resumen(navegador, id_)["espacio_vacio"] is False


# --- agregar ------------------------------------------------------------------------------------


def test_agregar_obra_04_con_su_nota_y_guardar_viv_001_conserva_la_nota(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)

    respuesta = _agregar(navegador, ficha, id_, cantidad="210", nota=NOTA)

    assert respuesta.status_code == 200, respuesta.text
    _sin_cache(respuesta)
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == 1 and cuerpo["clave"] == "OBRA-04|a-mano:1"
    assert cuerpo["resumen"]["rev"] == 1 and cuerpo["resumen"]["cambios"] == 1
    fila = _fila(navegador, id_, "OBRA-04|a-mano:1")
    assert (fila["cantidad"], fila["nota"], fila["quitable"], fila["calculo"]) == (
        "210",
        NOTA,
        True,
        None,
    )

    guardado = _guardar(navegador, ficha, id_, 1, codigo="VIV-001")
    assert guardado.status_code == 200, guardado.text
    assert (guardado.json()["codigo"], guardado.json()["primera"]) == ("VIV-001", True)
    assert _consulta(
        _entorno,
        "SELECT n.version, n.clave, n.nota FROM mp_nota_medicion n JOIN proyecto p "
        "ON p.id = n.proyecto_id WHERE p.nombre = ?",
        VIVIENDA,
    ) == [("VIV-001", "OBRA-04|a-mano:1", NOTA)]

    otra = _abierto(navegador, ficha, VIVIENDA, "VIV-001")
    reabierta = _fila(navegador, otra, "OBRA-04|a-mano:1")
    assert (reabierta["cantidad"], reabierta["nota"], reabierta["quitable"]) == ("210", NOTA, True)
    assert _resumen(navegador, otra)["cambios"] == 0


def test_la_nota_pasa_a_la_version_siguiente_y_el_codigo_solo_se_elige_en_la_primera(
    _entorno: Path,
) -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, cantidad="210", nota=NOTA).status_code == 200
    assert _guardar(navegador, ficha, id_, 1, codigo="VIV-001").status_code == 200
    otra = _abierto(navegador, ficha, VIVIENDA, "VIV-001")
    segunda = _agregar(navegador, ficha, otra, codigo="OBRA-06", cantidad="280", nota="Friso")
    assert segunda.json()["clave"] == "OBRA-06|a-mano:2"

    elegido = _guardar(navegador, ficha, otra, 1, codigo="VIV-777")
    assert elegido.status_code == 422
    assert elegido.json() == {"detalle": CODIGO_SOLO_PRIMERA}

    guardado = _guardar(navegador, ficha, otra, 1)
    assert guardado.status_code == 200, guardado.text
    assert guardado.json()["codigo"] == "VIV-002"
    assert _consulta(
        _entorno,
        "SELECT clave, nota FROM mp_nota_medicion WHERE version = 'VIV-002' ORDER BY clave",
    ) == [("OBRA-04|a-mano:1", NOTA), ("OBRA-06|a-mano:2", "Friso")]


def test_agregar_con_el_calculo_lo_muestra_con_coma_y_r1_no_avisa() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)

    respuesta = _agregar(navegador, ficha, id_, calculo="2,5*84")

    assert respuesta.status_code == 200, respuesta.text
    fila = _fila(navegador, id_, "OBRA-04|a-mano:1")
    assert (fila["cantidad"], fila["calculo"], fila["nota"]) == ("210", "2,5*84", None)
    auditoria = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/auditoria").json()
    assert [h for h in auditoria["hallazgos"] if h["regla"] == "R1"] == []


def test_la_auditoria_dice_en_lenguaje_llano_la_cantidad_sin_calculo() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, cantidad="210").status_code == 200

    auditoria = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/auditoria")

    assert auditoria.status_code == 200, auditoria.text
    r1 = [h["descripcion"] for h in auditoria.json()["hallazgos"] if h["regla"] == "R1"]
    assert r1 == [TEXTO_LLANO]


def test_una_cantidad_con_punto_decimal_es_422_con_la_regla_de_las_cifras() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)

    respuesta = _agregar(navegador, ficha, id_, cantidad="2.5")

    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": CIFRA}
    _sin_cache(respuesta)
    assert _resumen(navegador, id_)["rev"] == 0 and _filas(navegador, id_) == []


def test_un_calculo_que_no_coincide_con_la_cantidad_es_422_con_el_texto_de_la_tarea_8() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)

    respuesta = _agregar(navegador, ficha, id_, cantidad="15", calculo="6*3-2")

    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": NO_COINCIDE}
    assert _resumen(navegador, id_)["rev"] == 0


def test_una_partida_que_no_esta_en_el_catalogo_es_404_sin_repetir_otra_cosa() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)

    respuesta = _agregar(navegador, ficha, id_, codigo="OBRA-99", cantidad="1")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": FUERA_DEL_CATALOGO}
    _sin_cache(respuesta)
    assert _resumen(navegador, id_)["rev"] == 0


def test_agregar_con_un_rev_viejo_es_409_y_no_cambia_nada() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, cantidad="210").status_code == 200

    respuesta = _agregar(navegador, ficha, id_, rev=0, codigo="OBRA-06", cantidad="280")

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": REV_VIEJO}
    assert [f["clave"] for f in _filas(navegador, id_)] == ["OBRA-04|a-mano:1"]


def test_la_forma_mala_es_422_sin_eco() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    ruta = f"/v1/hoja/borradores/{id_}/partidas"
    malos = [
        {"rev": CENTINELA, "codigo": "OBRA-04", "cantidad": "1", "calculo": "", "nota": ""},
        {"rev": 0, "codigo": "OBRA-04", "cantidad": 1, "calculo": "", "nota": CENTINELA},
        {"rev": 0, "codigo": "OBRA-04", "cantidad": "1", "calculo": "", "nota": "n" * 501},
        {"rev": 0, "codigo": "", "cantidad": "1", "calculo": "", "nota": CENTINELA},
        {"rev": 0, "codigo": "OBRA-04", "cantidad": "1", "otro": CENTINELA},
    ]
    for cuerpo in malos:
        respuesta = navegador.post(ruta, json=cuerpo, headers=protegida(ficha))
        assert respuesta.status_code == 422, cuerpo
        assert respuesta.json() == {"detalle": FORMA_PARTIDA}
        assert CENTINELA not in respuesta.text
    quitar = navegador.post(
        f"{ruta}/quitar", json={"rev": 0, "clave": 7, "x": CENTINELA}, headers=protegida(ficha)
    )
    assert quitar.status_code == 422
    assert quitar.json() == {"detalle": FORMA_QUITAR}
    assert CENTINELA not in quitar.text
    assert _resumen(navegador, id_)["rev"] == 0


# --- quitar -------------------------------------------------------------------------------------


def test_quitar_la_partida_agregada_deja_cero_cambios() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, cantidad="210", nota=NOTA).status_code == 200

    respuesta = _quitar(navegador, ficha, id_, 1, "OBRA-04|a-mano:1")

    assert respuesta.status_code == 200, respuesta.text
    _sin_cache(respuesta)
    cuerpo = respuesta.json()
    assert cuerpo["rev"] == 2 and cuerpo["resumen"]["cambios"] == 0
    assert "clave" not in cuerpo
    assert _filas(navegador, id_) == []


def test_quitar_una_fila_del_espacio_es_422_con_el_texto_exacto(_casos: dict[str, Path]) -> None:
    _poner(_casos["of001"])
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha, NOMBRE_OF001, "001")
    assert _fila(navegador, id_, FILA_OF001)["quitable"] is False

    respuesta = _quitar(navegador, ficha, id_, 0, FILA_OF001)

    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FILA_DEL_ESPACIO}
    assert _resumen(navegador, id_)["rev"] == 0


def test_quitar_con_un_rev_viejo_es_409() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, cantidad="210").status_code == 200

    respuesta = _quitar(navegador, ficha, id_, 0, "OBRA-04|a-mano:1")

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": REV_VIEJO}
    assert len(_filas(navegador, id_)) == 1


# --- foco de revisión 1: obra en USD dentro de una carpeta en Bs --------------------------------


def test_una_obra_en_usd_en_carpeta_bs_se_guarda_en_usd_con_la_lista_convertida(
    _entorno: Path,
) -> None:
    navegador, ficha = _ana()
    abierta = _abrir(navegador, ficha, CASA_USD)
    assert abierta.status_code == 201, abierta.text
    assert abierta.json()["resumen"]["moneda"] == "USD"
    id_ = abierta.json()["id"]
    agregada = _agregar(navegador, ficha, id_, cantidad="210", nota=NOTA)
    assert agregada.status_code == 200, agregada.text
    assert agregada.json()["resumen"]["moneda"] == "USD"

    guardado = _guardar(navegador, ficha, id_, 1, codigo="CASA-001")

    assert guardado.status_code == 200, guardado.text
    filas = _consulta(
        _entorno,
        "SELECT pr.moneda, l.moneda, o.alcance, o.tasa, o.fecha_tasa, o.proyecto_id = p.id, l.id "
        "FROM presupuesto pr JOIN proyecto p ON p.id = pr.proyecto_id "
        "JOIN lista_precios l ON l.id = pr.lista_precios_id "
        "JOIN lista_precios_origen o ON o.lista_id = l.id "
        "WHERE p.nombre = ? AND pr.codigo = 'CASA-001'",
        CASA_USD,
    )
    assert len(filas) == 1
    moneda, moneda_lista, alcance, tasa, fecha_tasa, de_la_obra, lista_id = filas[0]
    assert (moneda, moneda_lista, alcance, D(str(tasa)), fecha_tasa, de_la_obra) == (
        "USD",
        "USD",
        "proyecto",
        D("40"),
        "2026-10-24",
        1,
    )
    precio = _consulta(
        _entorno,
        "SELECT pi.precio FROM precio_insumo pi JOIN insumo i ON i.id = pi.insumo_id "
        "WHERE pi.lista_id = ? AND i.descripcion = 'Material de OBRA-04'",
        lista_id,
    )
    assert [D(str(p[0])) for p in precio] == [D("0.3")]  # 12,00 Bs / 40,00 Bs por USD


def test_sin_tasa_agregar_en_una_obra_en_usd_es_409_y_no_escribe_nada(
    _casos: dict[str, Path],
) -> None:
    ruta = _poner(_casos["bs"])
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha, CASA_USD)
    antes = _volcado(ruta)

    respuesta = _agregar(navegador, ficha, id_, cantidad="210")

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": SIN_TASA}
    _sin_cache(respuesta)
    assert _resumen(navegador, id_)["rev"] == 0
    assert _volcado(ruta) == antes


def test_sin_tasa_al_guardar_es_409_y_no_queda_ni_la_version_ni_la_lista(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha, CASA_USD)
    antes = _volcado(_entorno)
    assert _agregar(navegador, ficha, id_, cantidad="210").status_code == 200
    assert _volcado(_entorno) == antes  # agregar tampoco escribe la lista convertida
    with closing(sqlite3.connect(_entorno)) as bd:  # se retiró la tasa del BCV
        bd.execute("DELETE FROM valor_indice")
        bd.commit()
    antes = _volcado(_entorno)

    respuesta = _guardar(navegador, ficha, id_, 1, codigo="CASA-001")

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": SIN_TASA}
    assert _volcado(_entorno) == antes


def test_si_llega_una_tasa_mas_nueva_la_version_declara_la_tasa_de_los_precios_de_sus_apu(
    _entorno: Path,
) -> None:
    """Ronda 2 (foco 1): tasa de 40,00 al 24/10 al agregar; antes de guardar llega la de 50,00
    del 25/10. La versión se valora con la lista que declara su tasa (la del día de guardar) y sus
    APU congelados usan esos mismos precios: 12,00 Bs / 50,00 = 0,24 USD."""
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha, CASA_USD)
    assert _agregar(navegador, ficha, id_, cantidad="210").status_code == 200
    registrar_tasa(_entorno, HOY, "50.00", huella="e" * 64)

    guardado = _guardar(navegador, ficha, id_, 1, codigo="CASA-001")

    assert guardado.status_code == 200, guardado.text
    ((presupuesto_id, lista_id, tasa, fecha_tasa),) = _consulta(
        _entorno,
        "SELECT pr.id, l.id, o.tasa, o.fecha_tasa FROM presupuesto pr "
        "JOIN proyecto p ON p.id = pr.proyecto_id "
        "JOIN lista_precios l ON l.id = pr.lista_precios_id "
        "JOIN lista_precios_origen o ON o.lista_id = l.id "
        "WHERE p.nombre = ? AND pr.codigo = 'CASA-001'",
        CASA_USD,
    )
    assert (D(str(tasa)), fecha_tasa) == (D("50"), "2026-10-25")
    en_la_lista = _consulta(
        _entorno,
        "SELECT pi.precio FROM precio_insumo pi JOIN insumo i ON i.id = pi.insumo_id "
        "WHERE pi.lista_id = ? AND i.descripcion = 'Material de OBRA-04'",
        lista_id,
    )
    en_el_apu = _consulta(
        _entorno,
        "SELECT l.precio FROM linea_composicion_version l "
        "JOIN composicion_version c ON c.id = l.composicion_id "
        "WHERE c.presupuesto_id = ? AND l.descripcion = 'Material de OBRA-04'",
        presupuesto_id,
    )
    assert [D(str(p[0])) for p in en_la_lista] == [D("0.24")]
    assert [D(str(p[0])) for p in en_el_apu] == [D("0.24")]


def test_sin_lista_vigente_a_la_fecha_del_borrador_lo_dice_con_la_fecha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ronda 2: la carpeta tiene lista, pero rige desde el 01/10/2026 y el borrador es del
    01/09/2026: no es que falte la lista, es que todavía no rige."""
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: date(2026, 9, 1))
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)

    respuesta = _agregar(navegador, ficha, id_, cantidad="210")

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": SIN_LISTA_A_LA_FECHA}
    assert _resumen(navegador, id_)["rev"] == 0


def _agregada_y_luego(ruta: Path, sql: str) -> tuple[TestClient, str, str]:
    """VIVIENDA en blanco con OBRA-04 agregada; después, `sql` cambia el catálogo (como si
    alguien lo hubiera tocado entre agregar y guardar)."""
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, cantidad="210").status_code == 200
    with closing(sqlite3.connect(ruta)) as bd:
        bd.execute(sql)
        bd.commit()
    return navegador, ficha, id_


@pytest.mark.parametrize(
    ("sql", "detalle"),
    [
        (
            "UPDATE partida SET codigo = 'OBRA-04-RETIRADA' WHERE codigo = 'OBRA-04'",
            "La partida «OBRA-04» ya no se puede valorar con la lista «Lista Bs de prueba»: ya "
            "no está en el catálogo. Quítela del presupuesto o vuelva a componerla en Componer.",
        ),
        (
            "DELETE FROM precio_insumo WHERE insumo_id = "
            "(SELECT id FROM insumo WHERE descripcion = 'Material de OBRA-04')",
            "La partida «OBRA-04» ya no se puede valorar con la lista «Lista Bs de prueba»: a "
            "uno de sus insumos le falta el precio en esa lista. Cárguelo o quite la partida del "
            "presupuesto.",
        ),
        (
            "UPDATE insumo SET descripcion = 'Material renovado de OBRA-04' "
            "WHERE descripcion = 'Material de OBRA-04'",
            "El APU de la partida «OBRA-04» cambió en el catálogo después de agregarla: quítela "
            "y vuelva a agregarla para valorarla con el APU de ahora.",
        ),
    ],
    ids=["salio_del_catalogo", "sin_precio", "apu_cambiado"],
)
def test_si_el_catalogo_cambio_entre_agregar_y_guardar_es_409_y_no_escribe(
    _entorno: Path, sql: str, detalle: str
) -> None:
    navegador, ficha, id_ = _agregada_y_luego(_entorno, sql)
    antes = _volcado(_entorno)

    respuesta = _guardar(navegador, ficha, id_, 1, codigo="VIV-001")

    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json() == {"detalle": detalle}
    assert _volcado(_entorno) == antes


def test_el_codigo_de_la_primera_version_solo_admite_letras_digitos_y_guiones() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, cantidad="210").status_code == 200
    for codigo in (f"VIV 001 {CENTINELA}", f"../{CENTINELA}", "VIV/001", "VIÑA-1", "x" * 41):
        respuesta = _guardar(navegador, ficha, id_, 1, codigo=codigo)
        assert respuesta.status_code == 422, codigo
        assert respuesta.json() == {"detalle": FORMA_GUARDAR}
        assert CENTINELA not in respuesta.text
    assert _guardar(navegador, ficha, id_, 1, codigo="VIV_2026.v-01").status_code == 200


# --- la fuente «cantidades sin cálculo» de la mesa ----------------------------------------------


def _guardar_viv_001(navegador, ficha, partidas: list[dict]) -> None:
    id_ = _abierto(navegador, ficha)
    for rev, partida in enumerate(partidas):
        assert _agregar(navegador, ficha, id_, rev=rev, **partida).status_code == 200
    guardado = _guardar(navegador, ficha, id_, len(partidas), codigo="VIV-001")
    assert guardado.status_code == 200, guardado.text


def _pendientes_sin_calculo(ruta: Path) -> list:
    from aplicacion.hoja_partidas import pendientes_sin_calculo

    dependencias.cerrar_motores()
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return pendientes_sin_calculo(sesion, HOY)
    finally:
        motor.dispose()


def _id_de(ruta: Path, nombre: str) -> str:
    return str(_consulta(ruta, "SELECT id FROM proyecto WHERE nombre = ?", nombre)[0][0])


def test_la_mesa_cuenta_la_cantidad_sin_calculo_de_viv_001(_entorno: Path) -> None:
    from aplicacion.mesa import Pendiente, Siguiente

    navegador, ficha = _ana()
    _guardar_viv_001(navegador, ficha, [{"cantidad": "210", "nota": NOTA}])

    assert _pendientes_sin_calculo(_entorno) == [
        Pendiente(
            _id_de(_entorno, VIVIENDA),
            VIVIENDA,
            "1 cantidad escrita a mano sin cálculo en VIV-001",
            Siguiente("Abrir el presupuesto", "hoja"),
        )
    ]


def test_la_mesa_dice_el_plural_y_no_cuenta_las_que_traen_calculo(_entorno: Path) -> None:
    navegador, ficha = _ana()
    _guardar_viv_001(
        navegador,
        ficha,
        [
            {"cantidad": "210"},
            {"codigo": "OBRA-06", "cantidad": "280"},
            {"codigo": "OBRA-01", "calculo": "8*10"},
        ],
    )

    textos = [p.texto for p in _pendientes_sin_calculo(_entorno)]

    assert textos == ["2 cantidades escritas a mano sin cálculo en VIV-001"]


def test_registrada_en_calidad_la_fuente_sale_una_vez_en_ese_grupo(_entorno: Path) -> None:
    from aplicacion import mesa
    from aplicacion.hoja_partidas import pendientes_sin_calculo

    assert mesa.FUENTES["calidad"].count(pendientes_sin_calculo) == 1
    navegador, ficha = _ana()
    _guardar_viv_001(navegador, ficha, [{"cantidad": "210"}])
    dependencias.cerrar_motores()
    motor = crear_motor(f"sqlite:///{_entorno.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            grupos = mesa.pendientes(sesion, HOY)
    finally:
        motor.dispose()

    calidad = next(g for g in grupos if g.clave == "calidad")
    assert [p.texto for p in calidad.items] == ["1 cantidad escrita a mano sin cálculo en VIV-001"]


# --- acceso: solo una cuenta con editar_hoja, CSRF y Origin -------------------------------------

RUTAS = (
    (f"/v1/hoja/borradores/{ID_AJENO}/partidas", {"rev": 0, "codigo": "OBRA-04"}),
    (f"/v1/hoja/borradores/{ID_AJENO}/partidas/quitar", {"rev": 0, "clave": "X"}),
)


@pytest.mark.parametrize(("ruta", "cuerpo"), RUTAS)
def test_sin_sesion_es_401_y_quien_revisa_no_puede(ruta: str, cuerpo: dict) -> None:
    anonimo = cliente(app).post(ruta, json=cuerpo, headers={"Origin": ORIGEN})
    assert anonimo.status_code == 401
    _sin_cache(anonimo)
    rita, ficha = con_cuenta(app, "rita")
    revisa = rita.post(ruta, json=cuerpo, headers=protegida(ficha))
    assert revisa.status_code == 403 and revisa.json() == {"detalle": MENSAJE_PERMISO}


@pytest.mark.parametrize(("ruta", "cuerpo"), RUTAS)
def test_la_clave_de_api_no_agrega_ni_quita(ruta: str, cuerpo: dict) -> None:
    respuesta = cliente(app).post(
        ruta, json=cuerpo, headers={CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN}
    )
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": SOLO_CUENTA}


def test_agregar_exige_csrf_y_origen_propio() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    ruta = f"/v1/hoja/borradores/{id_}/partidas"
    cuerpo = {"rev": 0, "codigo": "OBRA-04", "cantidad": "210", "calculo": "", "nota": ""}
    assert navegador.post(ruta, json=cuerpo, headers={"Origin": ORIGEN}).status_code == 403
    ajeno = protegida(ficha, origen="http://evil.example")
    assert navegador.post(ruta, json=cuerpo, headers=ajeno).status_code == 403
    assert navegador.post(ruta, json=cuerpo, headers=protegida(ficha, None)).status_code == 403
    assert _resumen(navegador, id_)["rev"] == 0


def test_el_borrador_de_otra_ficha_no_existe() -> None:
    uno, ficha_uno = _ana()
    otro, ficha_otro = _ana()
    id_ = _abierto(uno, ficha_uno)
    respuesta = _agregar(otro, ficha_otro, id_, cantidad="210")
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": FALTA}
    assert _resumen(uno, id_)["rev"] == 0


# --- las notas en una base sin la tabla (creada con `crear_esquema`, sin migrar) ----------------


def test_abrir_y_guardar_en_una_base_sin_la_tabla_de_notas(tmp_path: Path) -> None:
    from aplicacion import hoja
    from aplicacion.entrega import con_anexos_de_cadena
    from aplicacion.hoja_partidas import PartidaElegida, agregar_partida
    from core.catalog import crear_esquema

    motor = crear_motor(f"sqlite:///{(tmp_path / 'sin_tabla.db').as_posix()}")
    crear_esquema(motor)
    try:
        with abrir_sesion(motor) as sesion:
            con_anexos_de_cadena(sesion)
            lista = models.ListaPrecios(
                nombre="Lista USD", moneda="USD", fecha_vigencia=FECHA_LISTA, origen="prueba"
            )
            sesion.add(lista)
            sesion.flush()
            obra_04 = COMPOSICIONES["OBRA-04"]
            Catalogo(sesion).cargar_composicion(
                obra_04, lista, Dominio.CIVIL, FECHA_LISTA, "prueba"
            )
            crear_proyecto(sesion, "Obra sin notas", dominio=Dominio.CIVIL)
            sesion.commit()
            partida = PartidaElegida("OBRA-04", obra_04.descripcion, "m2", Dominio.CIVIL)
            sin_nota, _ = agregar_partida(
                hoja.Borrador(fecha=HOY), partida, cantidad="5", calculo="", nota=""
            )
            hoja.crear_primera_version(
                sesion,
                Catalogo(sesion),
                "Obra sin notas",
                sin_nota,
                fuente=FUENTE,
                responsable="Ana <ana>",
                codigo="A-001",
            )
            sin_tabla = (
                sesion.connection()
                .exec_driver_sql("SELECT name FROM sqlite_master WHERE name = 'mp_nota_medicion'")
                .all()
            )
            assert sin_tabla == []  # sin notas no se crea la tabla
            abierta = hoja.abrir_version(sesion, Catalogo(sesion), "Obra sin notas", "A-001")
            assert abierta.borrador.notas == {}

            con_nota, clave = agregar_partida(
                abierta.borrador, partida, cantidad="7", calculo="", nota="Muro del patio"
            )
            hoja.guardar_version(
                sesion, Catalogo(sesion), abierta, con_nota, fuente=FUENTE, responsable="Ana <ana>"
            )
            segunda = hoja.abrir_version(sesion, Catalogo(sesion), "Obra sin notas", "A-002")
            assert segunda.borrador.notas == {clave: "Muro del patio"}
    finally:
        motor.dispose()
