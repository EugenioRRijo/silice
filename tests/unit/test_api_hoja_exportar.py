"""X1 `GET /v1/hoja/borradores/{id}/excel`: exportar el borrador vivo a Excel (T10, 3e-1).

Contrato: `docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md` (diseno §4.1, §6.4 filas 3e-B1 a B4,
B12 parte X1 y 3e-F4; la clasica es `ui/paginas/hoja.py:556-573`, `_preparar_excel`).

Oraculos a mano (ninguno sale del codigo bajo prueba): el total de OF-001 es 2 703,86 y con
administracion 0,20 es 2 821,42 (memoria de OF-001, aceptacion SF); las nueve hojas de pestanas
y su orden son los de `test_aceptacion_sf.py:419-429`; el nombre seguro de `a"<CR><LF>c/d\\eé;x` es
`hoja_a___c_d_e__x.xlsx` (cada caracter fuera de A-Z a-z 0-9 . _ - pasa a «_», uno por uno).
La PARIDAD se prueba contra `ui.hoja` y `ui.paginas.hoja` VIVOS (las pruebas si pueden importar
`ui`): se comparan las celdas con openpyxl, no los bytes, que llevan marcas de tiempo.

La ruta no esta montada en `api.main` (la monta el orquestador): aqui se arma con
`tests/fixtures/app_de_prueba.py`.
"""

from __future__ import annotations

import io
import shutil
import sqlite3
import tempfile
import time
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from openpyxl import load_workbook
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api import caso_web, dependencias
from api.rutas import hoja as hoja_ruta
from aplicacion import entrega, hoja_borradores
from core.budget import crear_proyecto
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from seguridad import sesiones
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures.app_de_prueba import app_con
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.evaluador_excel import _celda, evaluar
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
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

D = Decimal
SOLO_CUENTA = "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."
FALTA = (
    "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). "
    "Lo que no guardó se perdió: abra la versión otra vez."
)
OTRO_CASO = "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual."
BASE = (
    "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro "
    "programa."
)
FORMA = "Los datos de la hoja no tienen la forma esperada: escriba cada celda como texto."
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
NUEVE_HOJAS = [
    "Espacio y metrajes",
    "APU",
    "Presupuesto",
    "Plan y curva",
    "Punto de equilibrio",
    "Precios",
    "Parametros",
    "Auditoria",
    "Trazabilidad",
]
HOJAS_DEL_ESPACIO = ["Esp origenes", "Esp ambientes", "Esp fuentes", "Esp puntos", "Esp vertices"]
HOJAS_DE_CONTROL = ["Valuaciones", "Valor ganado", "Decisiones"]
PROYECTO_NUEVO = "PR-SIN-VERSION (caso de prueba)"
CODIGO_MALO = 'a"\r\nc/d\\eé;x'
CODIGO_SEGURO = "hoja_a___c_d_e__x.xlsx"


# --- los casos de la prueba ---


def _plantilla_ob_s2(ruta: Path) -> Path:
    """OB-S2 (control de obra) con linea base y dos valuaciones: las hojas de control del Excel."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            ob.declarar_linea_base(sesion)
            ob.registrar_v01_y_v02(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


def _con_tres_versiones(ruta: Path) -> Path:
    """OF-001 con la 002 (administracion 0,20, un cambio) y la 003 (restauracion de la 001):
    versiones con filas de trazabilidad. Mismo armado que `test_api_hoja.py`, sobre una copia."""
    from ui import hoja as clasica

    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
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
    return ruta


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_exportar")
    casos = {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
        "ti001": plantilla_ti001(carpeta / "ti001.db"),
        "ob": _plantilla_ob_s2(carpeta / "ob.db"),
    }
    casos["of001_tres"] = _con_tres_versiones(
        Path(shutil.copyfile(casos["of001"], carpeta / "of001_tres.db"))
    )
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
    hoja_borradores.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def app() -> FastAPI:
    from api.rutas import hoja_exportar  # se importa aqui: sin la ruta, cada prueba falla sola

    return app_con(hoja_ruta.router, hoja_exportar.router)


def _poner(origen: Path) -> Path:
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    shutil.copyfile(origen, ruta)
    return ruta


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def _ana(app: FastAPI):
    return con_cuenta(app, "ana")


def _huella(ficha: str) -> str:
    return sesiones.huella_de(ficha)


def _abrir(navegador, ficha: str, proyecto: str = NOMBRE_OF001, version: str | None = "001") -> str:
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": proyecto, "version": version},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _excel(navegador, id_: str):
    return navegador.get(f"/v1/hoja/borradores/{id_}/excel")


def _celdas(contenido: bytes) -> dict[str, list[list]]:
    """Todas las celdas del libro, hoja por hoja, en el orden de las hojas."""
    libro = load_workbook(io.BytesIO(contenido))
    return {h.title: [[c.value for c in fila] for fila in h.iter_rows()] for h in libro.worksheets}


def _con_proyecto_nuevo() -> None:
    """Agrega un proyecto sin versiones al caso por defecto."""
    dependencias.cerrar_motores()
    motor = crear_motor(f"sqlite:///{config.ruta_caso_por_defecto().as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            crear_proyecto(sesion, PROYECTO_NUEVO)
            sesion.commit()
    finally:
        motor.dispose()


def _renombrar_version(codigo_nuevo: str) -> None:
    """La version `001` de OF-001 pasa a llamarse `codigo_nuevo` (para el nombre seguro)."""
    dependencias.cerrar_motores()
    motor = crear_motor(f"sqlite:///{config.ruta_caso_por_defecto().as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sesion.execute(
                text("UPDATE presupuesto SET codigo = :nuevo WHERE codigo = '001'"),
                {"nuevo": codigo_nuevo},
            )
            sesion.commit()
    finally:
        motor.dispose()


# --- 3e-B1: el libro de OF-001 ---


def test_b1_el_libro_de_of001_tiene_las_nueve_hojas_y_el_total_del_sistema(
    app: FastAPI, tmp_path: Path
) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    total_del_sistema = D(
        navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]["total"]["exacto"]
    )
    respuesta = _excel(navegador, id_)
    assert respuesta.status_code == 200, respuesta.text[:200]
    assert respuesta.headers["content-type"] == XLSX
    assert respuesta.headers["content-disposition"] == 'attachment; filename="hoja_001.xlsx"'
    assert respuesta.headers["cache-control"] == "no-store"
    ruta = tmp_path / "libro.xlsx"
    ruta.write_bytes(respuesta.content)
    libro = load_workbook(ruta)
    assert libro.sheetnames[:9] == NUEVE_HOJAS
    total_xl = D(str(evaluar(ruta)[("PRESUPUESTO", _celda(libro, "Presupuesto", "TOTAL", "G"))]))
    assert abs(total_xl - total_del_sistema) <= D("0.005")
    assert abs(total_xl - D("2703.86")) <= D("0.01")  # la memoria de OF-001


def test_b1_exporta_el_borrador_vivo_no_la_version_guardada(app: FastAPI, tmp_path: Path) -> None:
    """Con la administracion en 0,20 el total es el de la memoria (2 821,42), no el guardado."""
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    editado = navegador.put(
        f"/v1/hoja/borradores/{id_}/parametros",
        json={
            "rev": 0,
            "fcas": "6.00",
            "bono_alimentacion": "5.8100",
            "administracion": "0.20",
            "utilidad": "0.10",
        },
        headers=protegida(ficha),
    )
    assert editado.status_code == 200, editado.text
    ruta = tmp_path / "libro.xlsx"
    ruta.write_bytes(_excel(navegador, id_).content)
    libro = load_workbook(ruta)
    total_xl = D(str(evaluar(ruta)[("PRESUPUESTO", _celda(libro, "Presupuesto", "TOTAL", "G"))]))
    assert abs(total_xl - D("2821.42")) <= D("0.01")


# --- 3e-B2: un borrador sin version ---


def test_b2_un_borrador_sin_version_se_llama_hoja_borrador(app: FastAPI) -> None:
    _con_proyecto_nuevo()
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha, proyecto=PROYECTO_NUEVO, version=None)
    respuesta = _excel(navegador, id_)
    assert respuesta.status_code == 200, respuesta.text[:200]
    assert respuesta.headers["content-disposition"] == 'attachment; filename="hoja_borrador.xlsx"'
    assert respuesta.headers["content-type"] == XLSX
    assert load_workbook(io.BytesIO(respuesta.content)).sheetnames[:9] == NUEVE_HOJAS


# --- 3e-B3: espacio, precios, trazabilidad y control ---


def test_b3_lleva_el_espacio_los_precios_y_el_estado_de_las_filas_de_la_vista(
    app: FastAPI,
) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    libro = load_workbook(io.BytesIO(_excel(navegador, id_).content))
    assert libro.sheetnames[9:] == HOJAS_DEL_ESPACIO
    assert "Precios" in libro.sheetnames
    vista = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/espacio").json()
    for hoja, prefijo in (
        ("Esp ambientes", "esp_ambientes"),
        ("Esp fuentes", "esp_fuentes"),
        ("Esp puntos", "esp_puntos"),
    ):
        filas = list(libro[hoja].iter_rows(values_only=True))
        encabezado = list(filas[0])
        assert encabezado[-1] == "Estado"
        colocados = {fila[0]: fila[-1] for fila in filas[1:]}
        assert colocados, hoja
        for identidad, estado in colocados.items():
            assert estado == vista["estado"][f"{prefijo}:{identidad}"]["texto"], (hoja, identidad)
    todos = {e["texto"] for e in vista["estado"].values()}
    assert len(todos) >= 2  # no todo es «OK»: la prueba distingue estados


def test_b3_la_trazabilidad_y_los_precios_son_los_de_la_version_abierta(app: FastAPI) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    libro = load_workbook(io.BytesIO(_excel(navegador, id_).content))
    precios = list(libro["Precios"].iter_rows(values_only=True))
    assert precios[0][0] == "Insumo" and len(precios) > 1
    trazabilidad = list(libro["Trazabilidad"].iter_rows(values_only=True))
    assert trazabilidad[0][:2] == ("Versión de origen", "Versión resultante")
    # la version 001 se guardo sin cambios previos: la hoja lleva solo su encabezado
    assert len(trazabilidad) == 1


def test_b3_con_linea_base_y_valuaciones_lleva_las_hojas_de_control(
    app: FastAPI, _casos: dict[str, Path]
) -> None:
    _poner(_casos["ob"])
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha, proyecto=ob.NOMBRE, version=ob.CODIGO)
    libro = load_workbook(io.BytesIO(_excel(navegador, id_).content))
    assert set(HOJAS_DE_CONTROL) <= set(libro.sheetnames)
    valuaciones = [c.value for c in libro["Valuaciones"][1]]
    assert valuaciones[:3] == ["Numero", "Desde", "Hasta"]
    assert libro["Valuaciones"].max_row == 4  # encabezado + A 40, A 50 y B 60 (V-01 y V-02)


def test_b3_sin_linea_base_no_hay_hojas_de_control(app: FastAPI) -> None:
    navegador, ficha = _ana(app)
    libro = load_workbook(io.BytesIO(_excel(navegador, _abrir(navegador, ficha)).content))
    assert not set(HOJAS_DE_CONTROL) & set(libro.sheetnames)


# --- 3e-B4: nombre seguro ---


def test_b4_un_codigo_con_comillas_saltos_y_barras_no_rompe_el_encabezado(app: FastAPI) -> None:
    _renombrar_version(CODIGO_MALO)
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha, version=CODIGO_MALO)
    respuesta = _excel(navegador, id_)
    assert respuesta.status_code == 200, respuesta.text[:200]
    assert respuesta.headers["content-disposition"] == f'attachment; filename="{CODIGO_SEGURO}"'


def test_b4_el_nombre_seguro_es_lineal_y_acotado() -> None:
    from aplicacion.hoja_exportar import nombre_de_archivo

    assert nombre_de_archivo(None) == "hoja_borrador.xlsx"
    assert nombre_de_archivo("001") == "hoja_001.xlsx"
    assert nombre_de_archivo("v1.2-b_3") == "hoja_v1.2-b_3.xlsx"
    assert nombre_de_archivo(CODIGO_MALO) == CODIGO_SEGURO
    assert nombre_de_archivo("..\\..\\x") == "hoja_.._.._x.xlsx"  # sin barras: no hay ruta
    assert nombre_de_archivo("") == "hoja_version.xlsx"
    largo = nombre_de_archivo("ab" * 50_000)
    assert largo.startswith("hoja_ab") and largo.endswith(".xlsx") and len(largo) <= 140
    for adversarial in ('"' * 100_000, "é\r\n" * 33_333, "/" * 100_000):
        inicio = time.perf_counter()
        nombre = nombre_de_archivo(adversarial)
        assert time.perf_counter() - inicio < 1
        assert len(nombre) <= 140
        assert all(c.isascii() and c not in '"\r\n/\\' for c in nombre)


# --- 3e-B12 (parte X1): acceso ---


def test_b12_sin_sesion_ni_clave_es_401(app: FastAPI) -> None:
    respuesta = cliente(app).get(f"/v1/hoja/borradores/{'a' * 22}/excel")
    assert respuesta.status_code == 401
    assert respuesta.headers["cache-control"] == "no-store"


def test_b12_la_clave_de_api_no_exporta_ni_confirma_el_id(app: FastAPI) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    anonimo = cliente(app)
    for id_probado in (id_, "b" * 22):
        respuesta = anonimo.get(
            f"/v1/hoja/borradores/{id_probado}/excel", headers={CABECERA: crear_clave_de_prueba()}
        )
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detalle": SOLO_CUENTA}
        assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("login", ["rita", "tomas"])
def test_b12_rita_que_revisa_y_tomas_con_clave_temporal_no_exportan(
    app: FastAPI, login: str
) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    otro, _ = con_cuenta(app, login)
    respuesta = _excel(otro, id_)
    assert respuesta.status_code == 403
    assert respuesta.headers["cache-control"] == "no-store"
    if login == "rita":
        assert respuesta.json() == {"detalle": MENSAJE_PERMISO}


def test_b12_el_borrador_de_otra_ficha_no_existe_es_404(app: FastAPI) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    segunda, _ = con_cuenta(app, "ana")  # otra sesion de la misma cuenta: otra ficha
    respuesta = _excel(segunda, id_)
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": FALTA}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _excel(navegador, id_).status_code == 200  # el dueno sigue exportando


def test_un_borrador_descartado_o_con_id_inventado_es_404_y_uno_mal_formado_422(
    app: FastAPI,
) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    assert (
        navegador.delete(f"/v1/hoja/borradores/{id_}", headers=protegida(ficha)).status_code == 204
    )
    assert _excel(navegador, id_).json() == {"detalle": FALTA}
    corto = _excel(navegador, "corto-<script>")
    assert corto.status_code == 422
    assert corto.json() == {"detalle": FORMA}  # mensaje fijo: no repite lo enviado
    assert "script" not in corto.text


def test_un_borrador_abierto_en_otro_caso_es_409_y_no_toca_ninguna_base(
    app: FastAPI, _casos: dict[str, Path], _entorno: Path, tmp_path: Path
) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    otro = tmp_path / "otro.db"
    shutil.copyfile(_casos["ti001"], otro)
    preparar_base(otro)  # migrada de antemano: abrirla por primera vez la modificaria
    antes = _volcado(_entorno), _volcado(otro)
    caso_web._elegidos[_huella(ficha)] = otro.resolve()
    respuesta = _excel(navegador, id_)
    assert respuesta.status_code == 409 and respuesta.json() == {"detalle": OTRO_CASO}
    assert respuesta.headers["cache-control"] == "no-store"
    assert (_volcado(_entorno), _volcado(otro)) == antes


# --- errores propios ---


def test_un_valueerror_del_libro_es_422_con_el_texto_de_la_clasica(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)

    def romper(*_args, **_kwargs):
        raise ValueError("la hoja «Precios» no cabe")

    monkeypatch.setattr("aplicacion.hoja.excel_de_hoja_en_bytes", romper)
    respuesta = _excel(navegador, id_)
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": "No se pudo preparar el Excel: la hoja «Precios» no cabe"
    }
    assert respuesta.headers["cache-control"] == "no-store"


def test_un_error_de_la_base_es_503_fijo_sin_el_orig_del_driver(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)

    def romper(*_args, **_kwargs):
        raise SQLAlchemyError("SECRETO-DEL-DRIVER C:\\ruta\\interna.db")

    monkeypatch.setattr("aplicacion.hoja.tabla_de_trazabilidad", romper)
    respuesta = _excel(navegador, id_)
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detalle": BASE}
    assert "SECRETO" not in respuesta.text and "interna" not in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"


# --- no escribe nada ---


def test_exportar_no_cambia_la_base_ni_el_borrador_ni_el_rev_ni_la_cache(
    app: FastAPI, _entorno: Path
) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    antes_resumen = navegador.get(f"/v1/hoja/borradores/{id_}").json()
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    borrador, rev, calculo = vivo.borrador, vivo.rev, vivo.calculo
    assert calculo is not None  # R3 ya lo calculo: exportar debe reutilizarlo tal cual
    volcado = _volcado(_entorno)
    for _ in range(2):
        assert _excel(navegador, id_).status_code == 200
    assert _volcado(_entorno) == volcado
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    assert (vivo.borrador is borrador, vivo.rev, vivo.calculo is calculo) == (True, rev, True)
    assert navegador.get(f"/v1/hoja/borradores/{id_}").json() == antes_resumen


def test_exportar_con_la_cache_fria_no_cambia_el_rev(app: FastAPI) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    vivo = hoja_borradores.obtener(_huella(ficha), id_)
    vivo.calculo = None
    assert _excel(navegador, id_).status_code == 200
    assert vivo.rev == 0 and vivo.guardado_como is None


def test_exportar_no_deja_archivos_temporales(
    app: FastAPI, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    propio = tmp_path / "temporales"
    propio.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(propio))
    assert _excel(navegador, id_).status_code == 200

    def romper(*_args, **_kwargs):
        raise ValueError("falla a medias")

    monkeypatch.setattr("aplicacion.hoja.exportar_excel", romper)
    assert _excel(navegador, id_).status_code == 422
    assert list(propio.iterdir()) == []


# --- paridad contra ui.hoja VIVO ---


def _libro_de_la_clasica(
    origen: Path, destino: Path, proyecto: str, version: str, hoy: date | None = None
) -> bytes:
    """Lo que hace `_preparar_excel` (P:556-573) sobre una COPIA del caso, con `ui.hoja` vivo."""
    from ui import control
    from ui import hoja as clasica
    from ui.paginas import hoja as pagina

    hoy = hoy or date.today()
    shutil.copyfile(origen, destino)
    motor = crear_motor(f"sqlite:///{destino.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            abierta = clasica.abrir_version(
                sesion,
                Catalogo(sesion),
                proyecto,
                version,
                fecha_evaluacion=hoy,
                responsable="ana",
            )
            resultado = pagina._elaborar(abierta.borrador)
            trazabilidad = clasica.tabla_de_trazabilidad(sesion, abierta.proyecto, abierta.codigo)
            precios = clasica.precios_de_version(
                sesion, abierta.proyecto, abierta.codigo, fecha_evaluacion=hoy
            )
            hojas = control.tablas_de_control(sesion, abierta.proyecto, Catalogo(sesion))
            return clasica.excel_de_hoja_en_bytes(
                resultado,
                abierta.borrador,
                trazabilidad=trazabilidad,
                precios=precios,
                control=hojas,
            )
    finally:
        motor.dispose()


@pytest.mark.parametrize(
    ("caso", "proyecto", "version"),
    [
        ("of001", NOMBRE_OF001, "001"),
        ("ti001", NOMBRE_TI001, "TI-001"),
        ("ob", ob.NOMBRE, ob.CODIGO),
        ("of001_tres", NOMBRE_OF001, "002"),
        ("of001_tres", NOMBRE_OF001, "003"),
    ],
)
def test_paridad_el_libro_es_celda_por_celda_el_de_la_clasica(
    app: FastAPI, _casos: dict[str, Path], tmp_path: Path, caso: str, proyecto: str, version: str
) -> None:
    esperado = _celdas(
        _libro_de_la_clasica(_casos[caso], tmp_path / "clasica.db", proyecto, version)
    )
    _poner(_casos[caso])
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha, proyecto=proyecto, version=version)
    obtenido = _celdas(_excel(navegador, id_).content)
    assert list(obtenido) == list(esperado)
    for hoja in esperado:
        assert obtenido[hoja] == esperado[hoja], hoja
    assert sum(len(f) for f in esperado.values()) > 50  # no se compararon libros vacios


# --- ronda 1 del arbitro: trazabilidad de la version abierta, fecha de los precios, caracteres ---

#: Lo que la 002 de OF-001 registro al subir la administracion de 0,15 a 0,20 (a mano, de la
#: edicion de `_con_tres_versiones`): version de origen, version resultante, objeto, clave, campo,
#: valor anterior y nuevo.
CAMBIO_DE_LA_002 = ("001", "002", "parametro", "administracion", "valor", "0.15", "0.20")


def test_la_trazabilidad_de_una_version_con_cambios_llega_al_libro(
    app: FastAPI, _casos: dict[str, Path], tmp_path: Path
) -> None:
    from ui import hoja as clasica

    _poner(_casos["of001_tres"])
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha, version="002")
    filas = list(load_workbook(io.BytesIO(_excel(navegador, id_).content))["Trazabilidad"].values)
    assert len(filas) >= 2, "la hoja Trazabilidad solo trae el encabezado"
    assert tuple(str(c) for c in filas[1][:7]) == CAMBIO_DE_LA_002
    # y es, celda por celda, la tabla de la clasica VIVA para esa version
    copia = tmp_path / "clasica.db"
    shutil.copyfile(_casos["of001_tres"], copia)
    motor = crear_motor(f"sqlite:///{copia.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            tabla = clasica.tabla_de_trazabilidad(sesion, NOMBRE_OF001, "002")
    finally:
        motor.dispose()

    esperado = [list(tabla.columnas)] + [list(f) for f in tabla.filas]
    assert len(filas) == len(esperado)
    for obtenida, buscada in zip(filas[1:], esperado[1:], strict=True):
        assert list(obtenida[:-1]) == buscada[:-1]
        # la marca de tiempo: Excel la guarda al milisegundo (redondea)
        assert abs((obtenida[-1] - buscada[-1]).total_seconds()) <= 0.001
    assert list(filas[0]) == esperado[0]


def test_la_trazabilidad_de_la_restauracion_tambien_llega_al_libro(
    app: FastAPI, _casos: dict[str, Path]
) -> None:
    _poner(_casos["of001_tres"])
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha, version="003")
    filas = list(load_workbook(io.BytesIO(_excel(navegador, id_).content))["Trazabilidad"].values)
    assert len(filas) >= 2
    assert all(str(f[1]) == "003" for f in filas[1:])  # cada fila es de la version resultante


def test_los_precios_se_evaluan_a_la_fecha_de_hoy_de_la_ruta(
    app: FastAPI, _casos: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lejana, pasada = date(2035, 1, 1), date(2000, 1, 1)
    monkeypatch.setattr(hoja_ruta, "_hoy", lambda: lejana)
    navegador, ficha = _ana(app)
    obtenido = _celdas(_excel(navegador, _abrir(navegador, ficha)).content)["Precios"]
    de_lejana = _celdas(
        _libro_de_la_clasica(_casos["of001"], tmp_path / "a.db", NOMBRE_OF001, "001", lejana)
    )["Precios"]
    de_pasada = _celdas(
        _libro_de_la_clasica(_casos["of001"], tmp_path / "b.db", NOMBRE_OF001, "001", pasada)
    )["Precios"]
    assert de_lejana != de_pasada, "la fecha no cambia la hoja Precios: la prueba no distingue"
    assert obtenido == de_lejana


@pytest.mark.parametrize(
    "caracter", ["\x01", chr(0xFFFE), chr(0xFFFF), "\x00", "\x1f"], ids=lambda c: f"U+{ord(c):04X}"
)
def test_un_caracter_que_un_xlsx_no_admite_se_sustituye_y_el_libro_abre(
    app: FastAPI, caracter: str
) -> None:
    """Ola de decisiones: E1 acepta el caracter al editar el espacio (como la clasica) y X1 lo
    sustituye por U+FFFD en el punto de salida. Antes: U+0001 daba 422 y U+FFFE/U+FFFF un libro que
    openpyxl no podia leer. El borrador vivo conserva lo escrito y `rev` no cambia."""
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    tablas = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/espacio").json()["filas"]
    tablas["ambientes"][0]["nombre"] = f"Ba{caracter}ño"
    editado = navegador.put(
        f"/v1/hoja/borradores/{id_}/espacio",
        json={"rev": 0, "tablas": tablas},
        headers=protegida(ficha),
    )
    assert editado.status_code == 200, editado.text
    respuesta = _excel(navegador, id_)
    assert respuesta.status_code == 200, respuesta.text[:200]
    assert respuesta.headers["cache-control"] == "no-store"
    celdas = [c for hoja in _celdas(respuesta.content).values() for fila in hoja for c in fila]
    assert (
        "Ba" + chr(0xFFFD) + "ño" in celdas
    )  # el libro abre y la celda lleva el sustituto en su sitio
    assert not any(isinstance(c, str) and caracter in c for c in celdas)
    # lo escrito sigue en el borrador (se sanea la salida, no la edicion) y nada cambio
    vista = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/espacio").json()
    assert vista["filas"]["ambientes"][0]["nombre"] == f"Ba{caracter}ño"
    assert navegador.get(f"/v1/hoja/borradores/{id_}").json()["resumen"]["rev"] == 1


def test_sin_caracteres_prohibidos_el_saneado_no_cambia_ni_una_celda(app: FastAPI) -> None:
    """La paridad celda por celda con la clasica (arriba) sigue valiendo: el saneado es identidad
    sobre un libro limpio. Aqui, ademas, con tildes, eñes, un tabulador y un emoji en el nombre."""
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    tablas = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/espacio").json()["filas"]
    tablas["ambientes"][0]["nombre"] = "Baño ñandú \U0001f600\t(2)"
    editado = navegador.put(
        f"/v1/hoja/borradores/{id_}/espacio",
        json={"rev": 0, "tablas": tablas},
        headers=protegida(ficha),
    )
    assert editado.status_code == 200, editado.text
    celdas = [c for h in _celdas(_excel(navegador, id_).content).values() for f in h for c in f]
    assert "Baño ñandú \U0001f600\t(2)" in celdas


def test_la_red_de_seguridad_un_caracter_ilegal_que_se_escape_sigue_siendo_422(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si algun texto se escapara del saneado (un tipo que no se recorre), openpyxl lo rechaza y la
    respuesta sigue siendo un 422 limpio con `no-store`, nunca un 500."""
    from openpyxl.utils.exceptions import IllegalCharacterError

    def romper(*_args, **_kwargs):
        raise IllegalCharacterError("texto con la celda adentro")

    monkeypatch.setattr("aplicacion.hoja.excel_de_hoja_en_bytes", romper)
    navegador, ficha = _ana(app)
    id_ = _abrir(navegador, ficha)
    respuesta = _excel(navegador, id_)
    assert respuesta.status_code == 422
    assert respuesta.headers["cache-control"] == "no-store"
    detalle = respuesta.json()["detalle"]
    assert detalle.startswith("No se pudo preparar el Excel: ")
    assert "celda adentro" not in detalle and "Traceback" not in detalle
