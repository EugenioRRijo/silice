"""«Índices del BCV» por la API (migración; UC-17 pasos 1-3; RM-3).

Contrato de `api/rutas/indices.py` (paridad con `ui/paginas/indices.py`, de la que salen los
mensajes). Todas con `ADMINISTRAR_PRECIOS` (rol administrador), sesión o clave de API:

- `GET /v1/indices/contexto` -> tipos de archivo, periodicidades, unidad por defecto, extensiones,
  si este equipo lee `.xls` (extra `bcv`) y el responsable de la sesión.
- `POST /v1/indices/leer` (multipart: tipo, archivo, fuente, fecha_descarga) -> informe previo; no
  escribe nada.
- `POST /v1/indices/confirmar` (lo mismo, más responsable, definiciones y huella) -> mensajes por
  serie; vuelve a leer el archivo y guarda todo o nada.

Oráculos a mano: los valores del CSV y de la hoja de tasa, la huella con `hashlib`, los mensajes
literales de la pantalla clásica. Datos ficticios.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from collections.abc import Iterator
from decimal import Decimal
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

import openpyxl
import pytest
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import app
from api.rutas import indices as ruta_indices
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

FUENTE = "https://www.bcv.org.ve/estadisticas/tipo-cambio-de-referencia-smc"
FECHA = "2026-10-11"
CSV = (
    b"serie,fecha,valor,provisional,fuente\n"
    b"INDICE-A,2026-01-01,100.10,no,https://www.bcv.org.ve/x\n"
    b"INDICE-A,2026-02-01,101.25,si,https://www.bcv.org.ve/x\n"
    b"INDICE-A,2026-02-01,102,no,https://www.bcv.org.ve/x\n"
    b"INDICE-B,2026-01-01,50,no,https://www.bcv.org.ve/x\n"
)
DEFINICIONES = [
    {
        "serie": "INDICE-A",
        "nombre": "Indice ficticio A",
        "organismo": "Ente Demo",
        "unidad": "indice_bs",
        "periodicidad": "mensual",
    },
    {
        "serie": "INDICE-B",
        "nombre": "Indice ficticio B",
        "organismo": "Ente Demo",
        "unidad": "indice_bs",
        "periodicidad": "mensual",
    },
]
SIN_XLRD = (
    "No se puede leer un archivo .xls: falta el componente xlrd (extra «bcv» de la instalación). "
    "Instálelo, o use el .xlsx o el CSV canónico."
)
FIRMA_OLE2 = bytes.fromhex("D0CF11E0A1B11AE1")
PRIVADO = "texto-que-no-debe-volver-en-un-422"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("indices"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _tasa_xlsx() -> bytes:
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "30092026"
    hoja.append(["BANCO CENTRAL DE VENEZUELA"])
    hoja.append(["Fecha Valor: 01/10/2026"])
    hoja.append(["EUR", None, 1.0, 1.0, 1000.1, 1002.3])
    hoja.append(["USD", None, 1.0, 1.0, 858.02, 860.18])
    flujo = io.BytesIO()
    libro.save(flujo)
    return flujo.getvalue()


def _campos(tipo="csv", **cambios) -> dict[str, str]:
    campos = {"tipo": tipo, "fuente": FUENTE, "fecha_descarga": FECHA}
    campos.update(cambios)
    return campos


def _enviar(navegador, ficha, ruta, contenido, nombre="indices.csv", **campos):
    archivo = {"archivo": (nombre, contenido, "application/octet-stream")}
    return navegador.post(
        f"/v1/indices/{ruta}", data=_campos(**campos), files=archivo, headers=protegida(ficha)
    )


def _admin():
    return con_cuenta(app, "admin")


def _leer(contenido=CSV, nombre="indices.csv", **campos):
    navegador, ficha = _admin()
    return _enviar(navegador, ficha, "leer", contenido, nombre, **campos)


def _confirmar(contenido=CSV, nombre="indices.csv", definiciones=DEFINICIONES, **campos):
    navegador, ficha = _admin()
    campos.setdefault("definiciones", json.dumps(definiciones))
    return _enviar(navegador, ficha, "confirmar", contenido, nombre, **campos)


def _valores(ruta: Path) -> dict[tuple[str, str], Decimal]:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            filas = sesion.execute(
                select(
                    models.SerieIndice.codigo, models.ValorIndice.fecha, models.ValorIndice.valor
                ).join(models.SerieIndice, models.SerieIndice.id == models.ValorIndice.serie_id)
            ).all()
    finally:
        motor.dispose()
    return {(codigo, fecha.isoformat()): valor for codigo, fecha, valor in filas}


def _responsables(ruta: Path) -> set[str]:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return set(sesion.scalars(select(models.ImportacionIndice.responsable)))
    finally:
        motor.dispose()


# --- acceso (RM-3) --------------------------------------------------------------------------


def test_sin_sesion_es_401_y_con_clave_de_api_pasa() -> None:
    sin = cliente(app)
    assert sin.get("/v1/indices/contexto").status_code == 401
    assert (
        sin.post("/v1/indices/leer", data=_campos(), files={"archivo": ("a.csv", CSV)}).status_code
        == 401
    )
    clave = {CABECERA: crear_clave_de_prueba()}
    assert sin.get("/v1/indices/contexto", headers=clave).status_code == 200
    r = sin.post(
        "/v1/indices/leer", data=_campos(), files={"archivo": ("a.csv", CSV)}, headers=clave
    )
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_solo_el_administrador_administra_los_indices(login: str) -> None:
    navegador, ficha = con_cuenta(app, login)
    pedidos = [
        navegador.get("/v1/indices/contexto"),
        _enviar(navegador, ficha, "leer", CSV),
        _enviar(navegador, ficha, "confirmar", CSV, definiciones="[]"),
    ]
    for r in pedidos:
        assert (r.status_code, r.json()) == (403, {"detalle": MENSAJE_PERMISO})


def test_un_post_sin_el_token_csrf_es_403_y_no_lee_nada() -> None:
    navegador, _ = _admin()
    r = navegador.post("/v1/indices/leer", data=_campos(), files={"archivo": ("a.csv", CSV)})
    assert r.status_code == 403


# --- contexto -------------------------------------------------------------------------------


def test_el_contexto_trae_las_opciones_de_la_pantalla_clasica() -> None:
    navegador, _ = _admin()
    r = navegador.get("/v1/indices/contexto")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["tipos"] == [
        {"id": "tasa", "rotulo": "Tasa de referencia del USD (.xls trimestral)"},
        {"id": "inpc", "rotulo": "INPC (.xls mensual)"},
        {
            "id": "csv",
            "rotulo": "Una serie en CSV canonico (serie, fecha, valor, provisional, fuente)",
        },
    ]
    assert cuerpo["periodicidades"] == ["diaria", "mensual", "trimestral", "anual"]
    assert cuerpo["unidad_por_defecto"] == "indice_bs"
    assert cuerpo["extensiones"] == [".xls", ".xlsx", ".csv"]
    assert cuerpo["responsable"] == "Admin de Prueba <admin>"


@pytest.mark.parametrize("hay_xlrd", [False, True])
def test_el_contexto_dice_si_este_equipo_lee_xls(monkeypatch, hay_xlrd: bool) -> None:
    falso = ModuleType("xlrd")
    falso.__spec__ = ModuleSpec("xlrd", None)
    monkeypatch.setitem(sys.modules, "xlrd", falso if hay_xlrd else None)
    navegador, _ = _admin()
    assert navegador.get("/v1/indices/contexto").json()["lee_xls"] is hay_xlrd


# --- leer (no escribe) ----------------------------------------------------------------------


def test_leer_un_csv_trae_el_informe_previo_y_no_escribe(_entorno: Path) -> None:
    r = _leer()
    assert r.status_code == 200, r.text
    assert r.json() == {
        "archivo": "indices.csv",
        "huella": hashlib.sha256(CSV).hexdigest(),
        "fuente": "https://www.bcv.org.ve/x",
        "fecha_descarga": FECHA,
        "filas_leidas": 4,
        "filas_rechazadas": 1,
        "provisionales": 1,
        "series": [
            {"clave": "INDICE-A", "valores": 2, "desde": "2026-01-01", "hasta": "2026-02-01"},
            {"clave": "INDICE-B", "valores": 1, "desde": "2026-01-01", "hasta": "2026-01-01"},
        ],
        "rechazos": [{"lugar": "indices.csv:4", "motivo": "(serie, fecha) repetido"}],
        "rechazos_omitidos": 0,
        "advertencias": [],
    }
    assert _valores(_entorno) == {}


def test_leer_la_tasa_de_un_xlsx_trae_compra_y_venta_exactas(_entorno: Path) -> None:
    contenido = _tasa_xlsx()
    r = _leer(contenido, "2_1_2c26_smc.xlsx", tipo="tasa")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["huella"] == hashlib.sha256(contenido).hexdigest()
    assert cuerpo["fuente"] == FUENTE
    assert cuerpo["series"] == [
        {"clave": "usd_compra", "valores": 1, "desde": "2026-10-01", "hasta": "2026-10-01"},
        {"clave": "usd_venta", "valores": 1, "desde": "2026-10-01", "hasta": "2026-10-01"},
    ]
    assert (
        "el nombre '2_1_2c26_smc.xlsx' no sigue 2_1_2<letra><AA>_smc.xls: se importa porque el "
        "formato valida (UC-17 2e)"
    ) in cuerpo["advertencias"]
    assert _valores(_entorno) == {}


def test_el_nombre_que_manda_el_cliente_se_queda_en_su_ultimo_componente() -> None:
    assert _leer(CSV, "../../carpeta/notas.csv").json()["archivo"] == "notas.csv"
    # Un nombre reservado de Windows se salva con un guion bajo delante en vez de fallar.
    assert _leer(CSV, "CON.csv").json()["archivo"] == "_CON.csv"


def test_los_rechazos_se_acotan_y_se_cuenta_los_omitidos(monkeypatch) -> None:
    monkeypatch.setattr(ruta_indices, "MAXIMO_RECHAZOS", 2)
    filas = "".join(f"S,2026-01-01,0,no,f{n}\n" for n in range(5))  # 5 rechazos: valor cero
    contenido = ("serie,fecha,valor,provisional,fuente\n" + filas).encode()
    cuerpo = _leer(contenido).json()
    assert cuerpo["filas_rechazadas"] == 5
    assert len(cuerpo["rechazos"]) == 2
    assert cuerpo["rechazos_omitidos"] == 3


def test_leer_con_una_fuente_que_no_es_del_bcv_es_el_mensaje_de_la_pantalla() -> None:
    r = _leer(_tasa_xlsx(), "2_1_2c26_smc.xlsx", tipo="tasa", fuente="https://ejemplo.com/x")
    assert (r.status_code, r.json()) == (
        422,
        {
            "detalle": "No se importo nada: la fuente 'https://ejemplo.com/x' no es una "
            "direccion de bcv.org.ve"
        },
    )


def test_un_csv_con_otras_columnas_es_422_con_el_mensaje_del_lector() -> None:
    r = _leer(b"a,b\n1,2\n")
    assert r.status_code == 422
    assert r.json()["detalle"].startswith(
        "No se importo nada: indices.csv: las columnas deben ser exactamente serie, fecha, valor,"
    )


def test_un_xls_sin_xlrd_es_un_mensaje_claro_y_no_una_traza(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "xlrd", None)
    r = _leer(FIRMA_OLE2 + b"\x00" * 32, "2_1_2c26_smc.xls", tipo="tasa")
    assert (r.status_code, r.json()) == (422, {"detalle": f"No se importo nada: {SIN_XLRD}"})


def test_un_xlsx_que_no_es_un_libro_lo_rechaza_la_guardia() -> None:
    r = _leer(b"PK\x03\x04no-es-un-zip-de-verdad", "falso.xlsx", tipo="tasa")
    assert r.status_code == 422
    assert r.json()["detalle"].startswith("No se importo nada: ")
    assert "falso.xlsx" in r.json()["detalle"]


def test_un_archivo_por_encima_del_tope_se_rechaza_sin_guardarlo(monkeypatch) -> None:
    monkeypatch.setattr(ruta_indices, "LIMITE_BYTES", 2 * 2**20)
    r = _leer(b"x" * (3 * 2**20))
    assert (r.status_code, r.json()) == (
        422,
        {"detalle": "No se importo nada: indices.csv: pesa 3.0 MB; el limite es 2 MB"},
    )


@pytest.mark.parametrize("nombre", ["notas.txt", "sin_extension", "libro.xlsm"])
def test_solo_se_aceptan_xls_xlsx_y_csv(nombre: str) -> None:
    r = _leer(CSV, nombre)
    assert (r.status_code, r.json()) == (
        422,
        {"detalle": "Solo se aceptan archivos .xls, .xlsx o .csv."},
    )


def test_un_archivo_sin_nombre_es_422() -> None:
    navegador, ficha = _admin()
    r = _enviar(navegador, ficha, "leer", CSV, nombre="..")
    assert r.status_code == 422


def test_un_tipo_ajeno_es_422() -> None:
    r = _leer(tipo="otro")
    assert (r.status_code, r.json()) == (
        422,
        {"detalle": "Tipo de archivo no reconocido; se espera tasa, inpc o csv."},
    )


def test_un_campo_malformado_es_422_sin_repetir_lo_enviado() -> None:
    r = _leer(fecha_descarga=PRIVADO)
    assert r.status_code == 422
    assert PRIVADO not in r.text
    assert set(r.json()) == {"detalle"}


def test_sin_archivo_es_422_sin_eco() -> None:
    navegador, ficha = _admin()
    r = navegador.post("/v1/indices/leer", data=_campos(), headers=protegida(ficha))
    assert r.status_code == 422
    assert set(r.json()) == {"detalle"}


# --- confirmar ------------------------------------------------------------------------------


def test_confirmar_un_csv_guarda_los_valores_exactos_y_repetirlo_no_escribe(_entorno: Path) -> None:
    r = _confirmar()
    assert (r.status_code, r.json()) == (
        200,
        {"mensajes": ["INDICE-A: importada (2 valores)", "INDICE-B: importada (1 valores)"]},
    )
    assert _valores(_entorno) == {
        ("INDICE-A", "2026-01-01"): Decimal("100.10"),
        ("INDICE-A", "2026-02-01"): Decimal("101.25"),
        ("INDICE-B", "2026-01-01"): Decimal("50"),
    }
    # El responsable es la persona de la sesión, diga lo que diga el formulario (RF-82).
    assert _responsables(_entorno) == {"Admin de Prueba <admin>"}
    otra = _confirmar(responsable="Otra Persona")
    assert otra.json() == {
        "mensajes": [
            "INDICE-A: ya importado; no se escribio nada",
            "INDICE-B: ya importado; no se escribio nada",
        ]
    }
    assert len(_valores(_entorno)) == 3
    assert _responsables(_entorno) == {"Admin de Prueba <admin>"}


def test_confirmar_la_tasa_guarda_compra_y_venta(_entorno: Path) -> None:
    r = _confirmar(_tasa_xlsx(), "2_1_2c26_smc.xlsx", tipo="tasa", definiciones=[])
    assert (r.status_code, r.json()) == (
        200,
        {"mensajes": ["usd_compra: importada (1 valores)", "usd_venta: importada (1 valores)"]},
    )
    assert _valores(_entorno) == {
        ("BCV-USD-COMPRA", "2026-10-01"): Decimal("858.02"),
        ("BCV-USD-VENTA", "2026-10-01"): Decimal("860.18"),
    }


def test_una_serie_sin_definir_no_guarda_ninguna(_entorno: Path) -> None:
    r = _confirmar(definiciones=DEFINICIONES[:1])
    assert (r.status_code, r.json()) == (
        422,
        {
            "detalle": "No se guardo nada: declare nombre, organismo, unidad y periodicidad de "
            "la serie INDICE-B"
        },
    )
    assert _valores(_entorno) == {}  # INDICE-A se deshizo con la transaccion


def test_una_definicion_con_el_organismo_en_blanco_cuenta_como_sin_definir(_entorno: Path) -> None:
    incompleta = [dict(DEFINICIONES[0], organismo="   "), DEFINICIONES[1]]
    r = _confirmar(definiciones=incompleta)
    assert r.status_code == 422
    assert r.json()["detalle"].endswith("de la serie INDICE-A")
    assert _valores(_entorno) == {}


def test_una_periodicidad_ajena_es_el_error_del_nucleo(_entorno: Path) -> None:
    ajena = [dict(DEFINICIONES[0], periodicidad="semanal"), DEFINICIONES[1]]
    r = _confirmar(definiciones=ajena)
    assert r.status_code == 422
    assert r.json()["detalle"].startswith("No se guardo nada: periodicidad 'semanal'; se espera")
    assert _valores(_entorno) == {}


@pytest.mark.parametrize(
    "mala",
    [
        PRIVADO,
        '{"serie": "A"}',
        '[{"serie": "A"}]',
        '[{"serie": 1, "nombre": "n", "organismo": "o", "unidad": "u", "periodicidad": "mensual"}]',
    ],
)
def test_unas_definiciones_malformadas_son_422_sin_eco(mala: str) -> None:
    r = _confirmar(definiciones=mala)
    assert (r.status_code, r.json()) == (
        422,
        {"detalle": "Las definiciones de las series no tienen la forma esperada."},
    )
    assert PRIVADO not in r.text


def test_confirmar_con_otra_huella_es_409_y_no_escribe(_entorno: Path) -> None:
    r = _confirmar(huella="0" * 64)
    assert (r.status_code, r.json()) == (
        409,
        {"detalle": "El archivo no es el que se leyó; léalo de nuevo antes de confirmar."},
    )
    assert _valores(_entorno) == {}


def test_confirmar_con_la_huella_leida_pasa() -> None:
    assert _confirmar(huella=hashlib.sha256(CSV).hexdigest()).status_code == 200


def test_con_clave_de_api_el_responsable_lo_dice_el_formulario(_entorno: Path) -> None:
    sin = cliente(app)
    clave = {CABECERA: crear_clave_de_prueba()}
    datos = _campos(definiciones=json.dumps(DEFINICIONES))
    archivo = {"archivo": ("indices.csv", CSV)}
    faltante = sin.post("/v1/indices/confirmar", data=datos, files=archivo, headers=clave)
    assert (faltante.status_code, faltante.json()) == (
        422,
        {"detalle": "No se guardo nada: el responsable de la importacion es obligatorio"},
    )
    assert _valores(_entorno) == {}
    datos["responsable"] = "Integracion Demo"
    r = sin.post("/v1/indices/confirmar", data=datos, files=archivo, headers=clave)
    assert r.status_code == 200, r.text
    assert _responsables(_entorno) == {"Integracion Demo"}


def test_un_fallo_de_la_base_no_devuelve_el_sql(monkeypatch, _entorno: Path) -> None:
    from sqlalchemy.exc import OperationalError

    def falla(*_args, **_kwargs):
        raise OperationalError(
            "INSERT INTO secreto VALUES (?)", (PRIVADO,), Exception("disk I/O error")
        )

    monkeypatch.setattr(ruta_indices.logica, "confirmar", falla)
    r = _confirmar()
    assert r.status_code == 503
    assert r.json() == {"detalle": "No se pudo escribir en el caso: disk I/O error"}
    assert PRIVADO not in r.text and "INSERT" not in r.text
