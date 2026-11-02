"""Precios de la empresa por la API (migracion de `ui/paginas/precios_empresa.py`; UC-17 4-5).

Contrato de `api/rutas/precios_empresa.py` (paridad con la pagina clasica; rol
`administrar_precios`, es decir, solo el administrador; la clave de API tambien pasa, como en
`exigir_clave_o_sesion`):

- `GET /v1/precios-empresa` -> `{bases: [{id, nombre, moneda}], listas: [{id, nombre}]}`.
- `POST /v1/precios-empresa/referencia` (sin cuerpo) -> `{mensaje}`; una referencia ya cargada no se
  duplica.
- `POST /v1/precios-empresa/listas` (multipart: empresa, rif, base_id, moneda, fecha, fuente,
  nombre, archivo) -> 201 `{nombre, propios, desconocidos, mensaje, aviso}`.
- `GET /v1/precios-empresa/listas/{id}/hallazgos?fecha=` -> `{columnas, filas, nota}`: R11 y R12 de
  la lista sola, con el impacto como texto.
- `GET /v1/precios-empresa/listas/{id}/atipicos` -> `{disponible, avisos, variaciones}`: el boton
  «Buscar variaciones atipicas de precio» (RF-100) sobre los insumos de la lista; solo lee.

Oraculos escritos a mano: las filas de la memoria `s1_precios_empresa.md` (impacto por unidad), el
nombre por defecto `<empresa> <fecha>`, las 111 filas de `lista_maprex_bs.csv` contadas con `csv`,
la serie de la memoria `atipicos_s3.md` (1, 2, 4 ... 256, 257: un solo atipico, de 256 a 257) y los
mensajes literales de la pagina clasica.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.admin_acceso import MENSAJE_SOLO_CUENTA
from api.main import app
from api.rutas import precios_empresa as ruta
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.catalog.empresa import crear_lista_de_empresa
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from operacion import config
from operacion.base_datos import preparar_base
from scripts.seed import sembrar
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)
from tests.fixtures.sin_extra import SinExtra

RAIZ = Path(__file__).resolve().parents[2]
CSV_EMPRESA = RAIZ / "tests" / "fixtures" / "precios_empresa_s1.csv"
CSV_REFERENCIA = RAIZ / "data" / "precios" / "maprex_2026-07" / "lista_maprex_bs.csv"
URL = "/v1/precios-empresa"
EVALUACION = "2026-10-01"
EMPRESA = "Contratista Demo, C.A."
RIF = "J-00000000-0"
FUENTE = "lista interna 2026-09"
MENSAJE_FALTA = "Elija la moneda de la lista y el archivo de precios: no tienen valor por defecto."
MENSAJE_INVALIDO = "Los datos enviados no son válidos."
NOMBRE_REFERENCIA = "MaPreX julio 2026 en Bs"
#: (regla, severidad, insumo) -> impacto por unidad (memoria s1_precios_empresa.md).
DE_LA_MEMORIA = {
    ("R11", "ADVERTENCIA", 'UNION PVC A.B. 4"'): "1057.53",
    ("R11", "ADVERTENCIA", "ARENA LAVADA"): "11328.78",
    ("R11", "INFO", "LIJA DE AGUA N 100"): "",
    ("R12", "ADVERTENCIA", 'CLAVO DE ACERO LISO L=2 1/2"'): "108.15",
    ("R12", "ADVERTENCIA", "MATERIAL GRANULAR INTEGRAL"): "1622.25",
    ("R12", "ERROR", "PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM"): "",
}


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("precios_empresa"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalacion con cuentas y el caso por defecto con la linea base y la tasa del BCV."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    ruta_caso = config.ruta_caso_por_defecto()
    ruta_caso.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta_caso)
    motor = crear_motor(f"sqlite:///{ruta_caso.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            Catalogo(sesion).dar_de_alta_insumo(
                models.TipoInsumo.MATERIAL, "LIJA DE AGUA N 100", "pza"
            )
            registrar_importacion(
                sesion,
                definicion_tasa("venta"),
                [Observacion(date(2026, 10, 1), Decimal("860.18"))],
                archivo="FUENTE.md",
                huella="e" * 64,
                fuente="https://www.bcv.org.ve/",
                fecha_descarga=date(2026, 10, 8),
                responsable="Admin",
                filas_leidas=1,
                filas_rechazadas=0,
            )
            sesion.commit()
    finally:
        motor.dispose()
    caso_web.olvidar_todo()
    yield ruta_caso
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _listas_de_la_base(caso: Path) -> list:
    motor = crear_motor(f"sqlite:///{caso.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return list(sesion.execute(select(models.ListaPrecios.id, models.ListaPrecios.nombre)))
    finally:
        motor.dispose()


def _cuantas_listas(caso: Path) -> int:
    motor = crear_motor(f"sqlite:///{caso.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return sesion.scalar(select(func.count()).select_from(models.ListaPrecios)) or 0
    finally:
        motor.dispose()


def _admin() -> tuple[TestClient, dict[str, str]]:
    navegador, ficha = con_cuenta(app, "admin")
    return navegador, protegida(ficha)


def _cargar_referencia(navegador: TestClient, cabeceras: dict[str, str]) -> None:
    r = navegador.post(f"{URL}/referencia", headers=cabeceras)
    assert r.status_code == 200, r.text


def _id_de_la_referencia(navegador: TestClient) -> int:
    bases = navegador.get(URL).json()["bases"]
    (referencia,) = [b for b in bases if b["nombre"] == NOMBRE_REFERENCIA]
    return referencia["id"]


def _datos(base_id: int, **cambios) -> dict[str, str]:
    datos = {
        "empresa": EMPRESA,
        "rif": RIF,
        "base_id": str(base_id),
        "moneda": "Bs",
        "fecha": "2026-09-20",
        "fuente": FUENTE,
        "nombre": "",
    }
    datos.update({k: str(v) for k, v in cambios.items()})
    return datos


def _archivo(contenido: bytes | None = None, nombre: str = "precios.csv") -> dict:
    return {"archivo": (nombre, CSV_EMPRESA.read_bytes() if contenido is None else contenido)}


def _crear(navegador, cabeceras, base_id: int, *, archivo: dict | None = None, **cambios):
    return navegador.post(
        f"{URL}/listas",
        data=_datos(base_id, **cambios),
        files=_archivo() if archivo is None else archivo,
        headers=cabeceras,
    )


def _con_empresa_creada() -> tuple[TestClient, dict[str, str], dict]:
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    r = _crear(navegador, cabeceras, _id_de_la_referencia(navegador))
    assert r.status_code == 201, r.text
    return navegador, cabeceras, r.json()


# --- el estado de la pagina -------------------------------------------------------------------


def test_el_estado_trae_las_bases_y_ninguna_lista_de_empresa(_entorno) -> None:
    navegador, _ = _admin()
    r = navegador.get(URL)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["listas"] == []
    esperadas = _listas_de_la_base(_entorno)
    assert [(b["id"], b["nombre"]) for b in cuerpo["bases"]] == [(i, n) for i, n in esperadas]
    assert cuerpo["bases"][0]["moneda"] == "USD"  # la linea base sembrada
    assert set(cuerpo["bases"][0]) == {"id", "nombre", "moneda"}


# --- la referencia MaPreX ---------------------------------------------------------------------


def test_carga_la_referencia_con_sus_111_precios_y_no_la_duplica(_entorno) -> None:
    navegador, cabeceras = _admin()
    with CSV_REFERENCIA.open(encoding="utf-8") as archivo:
        con_precio = sum(1 for _ in csv.DictReader(archivo))
    assert con_precio == 111
    r = navegador.post(f"{URL}/referencia", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json() == {"mensaje": f"Referencia «{NOMBRE_REFERENCIA}» cargada con 111 precios."}
    antes = _cuantas_listas(_entorno)
    r = navegador.post(f"{URL}/referencia", headers=cabeceras)
    assert r.json() == {
        "mensaje": f"La referencia «{NOMBRE_REFERENCIA}» ya estaba cargada: no se escribio nada."
    }
    assert _cuantas_listas(_entorno) == antes
    assert NOMBRE_REFERENCIA in [b["nombre"] for b in navegador.get(URL).json()["bases"]]


def test_una_referencia_ilegible_dice_el_motivo_sin_la_ruta_del_servidor(monkeypatch) -> None:
    navegador, cabeceras = _admin()
    monkeypatch.setattr(
        "aplicacion.precios_empresa.RUTA_REFERENCIA_MAPREX", Path("C:/secreto/servidor/no.csv")
    )
    r = navegador.post(f"{URL}/referencia", headers=cabeceras)
    assert r.status_code == 422, r.text
    assert r.json() == {
        "detalle": "No se cargó la referencia: no se pudo leer el archivo de la referencia."
    }
    assert "secreto" not in r.text


# --- la lista de la empresa -------------------------------------------------------------------


def test_crea_la_lista_de_la_empresa_con_diez_precios_propios(_entorno) -> None:
    navegador, _, cuerpo = _con_empresa_creada()
    assert cuerpo["nombre"] == f"{EMPRESA} 2026-09-20"
    assert cuerpo["propios"] == 10
    assert cuerpo["desconocidos"] == []
    assert cuerpo["aviso"] is None
    assert cuerpo["mensaje"] == f"Lista «{cuerpo['nombre']}» creada con 10 precios propios."
    estado = navegador.get(URL).json()
    assert [lista["nombre"] for lista in estado["listas"]] == [cuerpo["nombre"]]
    # la lista de la empresa ya no es base de otra (UC-17: solo las listas globales)
    assert cuerpo["nombre"] not in [b["nombre"] for b in estado["bases"]]


def test_el_nombre_opcional_manda_y_se_recorta(_entorno) -> None:
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    r = _crear(
        navegador, cabeceras, _id_de_la_referencia(navegador), nombre="  Lista Demo de la obra  "
    )
    assert r.status_code == 201, r.text
    assert r.json()["nombre"] == "Lista Demo de la obra"


def test_un_insumo_que_el_catalogo_no_conoce_se_informa_y_no_entra(_entorno) -> None:
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    archivo = (
        b"tipo,insumo,unidad,precio,fecha,fuente\n"
        b"material,ARENA LAVADA,m3,49078.775,2026-09-20,Cotizacion interna (ficticia)\n"
        b"material,INSUMO INEXISTENTE DEMO,pza,10.00,2026-09-20,Cotizacion interna (ficticia)\n"
    )
    r = _crear(
        navegador,
        cabeceras,
        _id_de_la_referencia(navegador),
        archivo={"archivo": ("precios.csv", archivo)},
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["propios"] == 1
    assert cuerpo["desconocidos"] == ["INSUMO INEXISTENTE DEMO"]
    assert (
        cuerpo["aviso"]
        == "Estos insumos no están en el catálogo y no entraron a la lista (UC-17 4a):"
    )


@pytest.mark.parametrize("campo", ["moneda", "archivo"])
def test_sin_moneda_o_sin_archivo_no_hay_valor_por_defecto(_entorno, campo) -> None:
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    base = _id_de_la_referencia(navegador)
    antes = _cuantas_listas(_entorno)
    if campo == "moneda":
        r = _crear(navegador, cabeceras, base, moneda="")
    else:
        r = navegador.post(f"{URL}/listas", data=_datos(base), headers=cabeceras)
    assert r.status_code == 422, r.text
    assert r.json() == {"detalle": MENSAJE_FALTA}
    assert _cuantas_listas(_entorno) == antes


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"moneda": "EUR"}, "No se creó la lista: "),
        ({"empresa": "  "}, "No se creó la lista: la empresa (nombre y RIF)"),
        ({"fuente": ""}, "No se creó la lista: la empresa (nombre y RIF)"),
        ({"base_id": 9999}, "No se creó la lista: la lista base 9999 no existe en este caso"),
    ],
)
def test_los_errores_del_nucleo_llegan_con_el_prefijo_de_la_pagina(
    _entorno, cambios, mensaje
) -> None:
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    base = _id_de_la_referencia(navegador)
    antes = _cuantas_listas(_entorno)
    r = _crear(navegador, cabeceras, cambios.pop("base_id", base), **cambios)
    assert r.status_code == 422, r.text
    assert r.json()["detalle"].startswith(mensaje)
    assert _cuantas_listas(_entorno) == antes  # todo o nada


def test_un_archivo_de_otro_formato_o_corrupto_o_enorme_se_rechaza(_entorno, monkeypatch) -> None:
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    base = _id_de_la_referencia(navegador)
    antes = _cuantas_listas(_entorno)
    r = _crear(navegador, cabeceras, base, archivo=_archivo(b"hola", "precios.txt"))
    assert r.status_code == 422, r.text
    assert r.json() == {"detalle": "No se creó la lista: el archivo debe ser CSV o XLSX."}
    r = _crear(navegador, cabeceras, base, archivo=_archivo(b"no es un zip", "precios.xlsx"))
    assert r.status_code == 422, r.text
    assert r.json()["detalle"].startswith("No se creó la lista: precios.xlsx: no se puede leer")
    monkeypatch.setattr(ruta, "TOPE_BYTES", 100)
    r = _crear(navegador, cabeceras, base)
    assert r.status_code == 422, r.text
    assert r.json() == {
        "detalle": "No se creó la lista: el archivo pesa más del máximo permitido (20 MiB)."
    }
    assert _cuantas_listas(_entorno) == antes


def test_el_nombre_del_archivo_no_saca_nada_del_directorio_temporal(_entorno) -> None:
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    r = _crear(
        navegador,
        cabeceras,
        _id_de_la_referencia(navegador),
        archivo=_archivo(nombre="../../fuera/precios.csv"),
    )
    assert r.status_code == 201, r.text
    assert not (_entorno.parent.parent / "fuera").exists()


def test_el_422_de_validacion_no_repite_lo_enviado(_entorno) -> None:
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    r = _crear(
        navegador,
        cabeceras,
        _id_de_la_referencia(navegador),
        fecha="no-es-una-fecha",
        rif="RIF-SECRETO-DEMO",
    )
    assert r.status_code == 422, r.text
    assert r.json() == {"detalle": MENSAJE_INVALIDO}
    assert "no-es-una-fecha" not in r.text
    assert "RIF-SECRETO-DEMO" not in r.text


# --- los hallazgos ----------------------------------------------------------------------------


def _id_de_la_lista(navegador: TestClient) -> int:
    return navegador.get(URL).json()["listas"][0]["id"]


def test_los_hallazgos_son_los_de_la_memoria_por_unidad(_entorno) -> None:
    navegador, _, _ = _con_empresa_creada()
    antes = _cuantas_listas(_entorno)
    lista = _id_de_la_lista(navegador)
    r = navegador.get(f"{URL}/listas/{lista}/hallazgos", params={"fecha": EVALUACION})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["columnas"] == ["Regla", "Severidad", "Descripción", "Impacto"]
    assert (
        cuerpo["nota"] == "Sin versión, el impacto es por unidad de insumo. Nada de esto se guarda."
    )
    assert all(list(fila) == cuerpo["columnas"] for fila in cuerpo["filas"])
    for (regla, severidad, insumo), impacto in DE_LA_MEMORIA.items():
        texto = insumo.casefold()
        (fila,) = [
            f
            for f in cuerpo["filas"]
            if (f["Regla"], f["Severidad"]) == (regla, severidad)
            and (
                texto in f["Descripción"].casefold()
                if severidad == "INFO"
                else f["Descripción"].casefold().startswith(f"{texto}:")
            )
        ]
        assert fila["Impacto"] == impacto, (regla, insumo)
    assert _cuantas_listas(_entorno) == antes  # nada se guarda


def test_la_fecha_de_evaluacion_es_hoy_si_no_se_envia() -> None:
    navegador, _, _ = _con_empresa_creada()
    r = navegador.get(f"{URL}/listas/{_id_de_la_lista(navegador)}/hallazgos")
    assert r.status_code == 200, r.text


def test_una_fecha_de_evaluacion_invalida_no_se_repite() -> None:
    navegador, _, _ = _con_empresa_creada()
    r = navegador.get(
        f"{URL}/listas/{_id_de_la_lista(navegador)}/hallazgos", params={"fecha": "ayer-secreto"}
    )
    assert r.status_code == 422, r.text
    assert r.json() == {"detalle": MENSAJE_INVALIDO}
    assert "ayer-secreto" not in r.text


def test_solo_las_listas_de_empresa_tienen_hallazgos(_entorno) -> None:
    navegador, _, _ = _con_empresa_creada()
    base = navegador.get(URL).json()["bases"][0]["id"]
    for lista in (base, 9999):
        r = navegador.get(f"{URL}/listas/{lista}/hallazgos", params={"fecha": EVALUACION})
        assert r.status_code == 404, r.text
        assert r.json() == {"detalle": f"la lista {lista} no es una lista de empresa de este caso"}


# --- el acceso --------------------------------------------------------------------------------


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_solo_el_administrador_administra_los_precios(login) -> None:
    navegador, ficha = con_cuenta(app, login)
    cabeceras = protegida(ficha)
    for r in (
        navegador.get(URL),
        navegador.post(f"{URL}/referencia", headers=cabeceras),
        navegador.post(f"{URL}/listas", data=_datos(1), files=_archivo(), headers=cabeceras),
        navegador.get(f"{URL}/listas/1/hallazgos"),
        navegador.get(f"{URL}/listas/1/atipicos"),
    ):
        assert r.status_code == 403, r.text
        assert r.json() == {"detalle": MENSAJE_PERMISO}


def test_sin_sesion_es_401_y_sin_csrf_u_origen_es_403() -> None:
    assert cliente(app).get(URL).status_code == 401
    navegador, ficha = con_cuenta(app, "admin")
    assert navegador.post(f"{URL}/referencia").status_code == 403  # sin CSRF ni Origin
    sin_origen = protegida(ficha, origen=None)
    assert navegador.post(f"{URL}/referencia", headers=sin_origen).status_code == 403
    ajeno = protegida(ficha, origen="http://sitio-ajeno.example")
    assert navegador.post(f"{URL}/referencia", headers=ajeno).status_code == 403


def _con_clave(clave: str) -> TestClient:
    return TestClient(
        app,
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 50000),
        raise_server_exceptions=False,
        headers={CABECERA: clave},
    )


def test_la_clave_de_api_lee_y_una_falsa_no() -> None:
    assert _con_clave(crear_clave_de_prueba()).get(URL).status_code == 200
    assert _con_clave("falsa.clave").get(URL).status_code == 401


def test_la_clave_de_api_no_escribe_es_403_en_cada_ruta_de_escritura(_entorno) -> None:
    """MEDIO-1: referencia y listas piden la sesion de una cuenta; la clave no basta."""
    con_clave = _con_clave(crear_clave_de_prueba())
    antes = _cuantas_listas(_entorno)
    pedidos = [
        con_clave.post(f"{URL}/referencia"),
        con_clave.post(f"{URL}/listas", data=_datos(1), files=_archivo()),
    ]
    for r in pedidos:
        assert (r.status_code, r.json()) == (403, {"detalle": MENSAJE_SOLO_CUENTA}), r.text
    assert _cuantas_listas(_entorno) == antes


def test_el_tope_de_la_ruta_es_el_real_de_20_mib_y_el_413_lo_dice(_entorno) -> None:
    """BAJO-1: el middleware corta el cuerpo en 20 MiB; la ruta y su mensaje dicen lo mismo."""
    assert ruta.TOPE_BYTES == 20 * 2**20
    assert "20 MiB" in ruta.MENSAJE_TAMANO and "25" not in ruta.MENSAJE_TAMANO
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    base = _id_de_la_referencia(navegador)
    antes = _cuantas_listas(_entorno)
    enorme = _archivo(b"x" * ruta.TOPE_BYTES, "precios.csv")  # con el multipart, pasa de 20 MiB
    r = _crear(navegador, cabeceras, base, archivo=enorme)
    assert r.status_code == 413, r.text
    assert "20 MiB" in r.json()["detalle"]
    assert _cuantas_listas(_entorno) == antes


def test_un_nombre_reservado_de_windows_se_salva_y_no_es_500(_entorno) -> None:
    """BAJO-2: CON/NUL/a:b se saneaban solo en Indices; la guardia es la misma en las dos rutas."""
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    base = _id_de_la_referencia(navegador)
    r = _crear(navegador, cabeceras, base, archivo=_archivo(nombre="CON.csv"))
    assert r.status_code == 201, r.text
    r = _crear(navegador, cabeceras, base, archivo=_archivo(b"no es un libro", "NUL.xlsx"))
    assert r.status_code == 422, r.text
    assert r.json()["detalle"].startswith("No se creó la lista: _NUL.xlsx: no se puede leer")
    r = _crear(navegador, cabeceras, base, archivo=_archivo(nombre="a:b.csv"))
    assert r.status_code == 422, r.text
    assert r.json() == {"detalle": "No se creó la lista: el archivo debe ser CSV o XLSX."}


@pytest.mark.parametrize(
    ("campo", "tope"), [("nombre", 200), ("empresa", 200), ("rif", 200), ("fuente", 500)]
)
def test_los_campos_de_texto_de_la_lista_tienen_tope(_entorno, campo: str, tope: int) -> None:
    """BAJO-4: un texto largo no llega al nucleo; el 422 no repite lo enviado."""
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    base = _id_de_la_referencia(navegador)
    antes = _cuantas_listas(_entorno)
    r = _crear(navegador, cabeceras, base, **{campo: "Z" * (tope + 1)})
    assert r.status_code == 422, r.text
    assert r.json() == {"detalle": MENSAJE_INVALIDO}
    assert _cuantas_listas(_entorno) == antes
    r = _crear(navegador, cabeceras, base, **{campo: "Z" * tope})
    assert r.status_code == 201, r.text


# --- huecos de la revision de seguridad -------------------------------------------------------

PISTAS_PROHIBIDAS = ("Traceback", "SELECT", "INSERT", "Temp", "tmp", ".py", "site-packages", "C:\\")


def _sin_pistas(r) -> None:
    for pista in PISTAS_PROHIBIDAS:
        assert pista not in r.text, (pista, r.text)


def _con_referencia() -> tuple[TestClient, dict[str, str], int]:
    navegador, cabeceras = _admin()
    _cargar_referencia(navegador, cabeceras)
    return navegador, cabeceras, _id_de_la_referencia(navegador)


def test_un_archivo_vacio_no_crea_la_lista_y_no_es_500(_entorno) -> None:
    navegador, cabeceras, base = _con_referencia()
    antes = _cuantas_listas(_entorno)
    for nombre in ("vacio.csv", "vacio.xlsx"):
        r = _crear(navegador, cabeceras, base, archivo=_archivo(b"", nombre))
        assert r.status_code == 422, r.text
        assert r.json()["detalle"].startswith("No se creó la lista: ")
        _sin_pistas(r)
    assert _cuantas_listas(_entorno) == antes


def test_el_tope_exacto_de_la_ruta_pasa_y_un_byte_mas_no(_entorno, monkeypatch) -> None:
    navegador, cabeceras, base = _con_referencia()
    contenido = CSV_EMPRESA.read_bytes()
    monkeypatch.setattr(ruta, "TOPE_BYTES", len(contenido))
    r = _crear(navegador, cabeceras, base, archivo=_archivo(contenido))
    assert r.status_code == 201, r.text
    antes = _cuantas_listas(_entorno)
    r = _crear(navegador, cabeceras, base, archivo=_archivo(contenido + b"\n"))
    assert (r.status_code, r.json()) == (422, {"detalle": ruta.MENSAJE_TAMANO})
    assert _cuantas_listas(_entorno) == antes


@pytest.mark.parametrize(
    ("nombre", "contenido"),
    [
        ("falso.xlsx", b"texto plano, no un libro"),
        ("falso.csv", b"\x00\x01\xff\xfe\x80\x81\x00" * 40),
        ("falso.csv", b"PK\x03\x04" + b"\x00" * 64),
    ],
)
def test_la_extension_que_no_coincide_con_el_contenido_es_422_sin_traza(
    _entorno, nombre: str, contenido: bytes
) -> None:
    navegador, cabeceras, base = _con_referencia()
    antes = _cuantas_listas(_entorno)
    r = _crear(navegador, cabeceras, base, archivo=_archivo(contenido, nombre))
    assert r.status_code == 422, r.text
    assert r.json()["detalle"].startswith("No se creó la lista: ")
    _sin_pistas(r)
    assert _cuantas_listas(_entorno) == antes


@pytest.mark.parametrize("fecha", ["2026-02-30", "11/10/2026", "", "manana-secreto", "2026-13-01"])
def test_una_fecha_de_la_lista_invalida_es_422_sin_eco(_entorno, fecha: str) -> None:
    navegador, cabeceras, base = _con_referencia()
    antes = _cuantas_listas(_entorno)
    r = _crear(navegador, cabeceras, base, fecha=fecha)
    assert (r.status_code, r.json()) == (422, {"detalle": MENSAJE_INVALIDO})
    if fecha:
        assert fecha not in r.text
    assert _cuantas_listas(_entorno) == antes


def test_ninguna_respuesta_de_error_trae_rutas_del_servidor_ni_sql(_entorno) -> None:
    navegador, cabeceras, base = _con_referencia()
    casos = [
        _archivo(b"hola", "precios.txt"),
        _archivo(b"no es un zip", "precios.xlsx"),
        _archivo(b"", "vacio.csv"),
        _archivo(b"a,b\n1,2\n", "ajeno.csv"),
        _archivo(nombre=".."),
    ]
    for archivo in casos:
        r = _crear(navegador, cabeceras, base, archivo=archivo)
        assert r.status_code == 422, (archivo, r.text)
        _sin_pistas(r)
    r = _crear(navegador, cabeceras, 987654)  # una base que no existe
    assert r.status_code in (404, 422), r.text
    _sin_pistas(r)
    r = navegador.get(f"{URL}/listas/987654/hallazgos")
    assert r.status_code == 404
    _sin_pistas(r)


# --- las variaciones atipicas de precio (RF-100, T4 de la migracion final) ----------------------

#: Memoria `atipicos_s3.md`: §1, una serie que se duplica y un paso final de 256 a 257 (+1/256 =
#: 0,390625 %), el unico atipico; §2, la serie que se duplica hasta 512, nada atipico; §3, ocho
#: precios (siete variaciones): el detector se abstiene.
SERIE_CON_ATIPICO = (1, 2, 4, 8, 16, 32, 64, 128, 256, 257)
SERIE_SIN_ATIPICO = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512)
SERIE_CORTA = (1, 2, 4, 8, 16, 32, 64, 128)
INSUMO = "ATIP-001"
LISTA_ATIPICOS = "Lista Demo de la serie"
DESCRIPCION_ATIPICA = (
    "ATIP-001: variación de 0.39 % entre 2026-09-01 y 2026-10-01 (en USD) se aparta del "
    "historial de variaciones del insumo"
)
NADA_ATIPICO = (
    "Ninguna variación atípica de precio (una serie de menos de 8 variaciones no se juzga)."
)
SIN_ML = (
    "La búsqueda de variaciones atípicas necesita el extra `ml` (scikit-learn), que no está "
    "instalado en este equipo. No se buscó nada y nada se bloquea."
)


def _sembrar_serie(caso: Path, precios=SERIE_CON_ATIPICO, sin_tasa: str | None = None) -> int:
    """Un insumo ficticio con un precio en USD por mes (listas globales, enero en adelante) y una
    lista de empresa sobre la ultima, sin precios propios: lo heredado no repite el punto de la
    base, asi la serie es exactamente `precios`. `sin_tasa` agrega una lista en Bs sin tasa."""
    motor = crear_motor(f"sqlite:///{caso.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            insumo = models.Insumo(
                codigo=INSUMO,
                tipo=models.TipoInsumo.MATERIAL,
                descripcion="Arena demo",
                unidad="m3",
            )
            sesion.add(insumo)
            sesion.flush()
            filas = [
                (f"Serie demo {mes:02d}", "USD", date(2026, mes, 1), precio)
                for mes, precio in enumerate(precios, start=1)
            ]
            if sin_tasa is not None:
                filas.append((sin_tasa, "Bs", date(2026, 11, 1), 720))
            listas = []
            for nombre, moneda, vigencia, precio in filas:
                lista = models.ListaPrecios(
                    nombre=nombre, moneda=moneda, fecha_vigencia=vigencia, origen="prueba"
                )
                sesion.add(lista)
                sesion.flush()
                sesion.add(
                    models.PrecioInsumo(
                        lista_id=lista.id, insumo_id=insumo.id, precio=Decimal(precio)
                    )
                )
                listas.append(lista)
            sesion.flush()
            empresa = crear_lista_de_empresa(
                sesion,
                EMPRESA,
                RIF,
                listas[len(precios) - 1],
                [],
                moneda="USD",
                fecha=date(2026, 10, 2),
                fuente=FUENTE,
                referencia=None,
                nombre=LISTA_ATIPICOS,
            )
            sesion.commit()
            return empresa.id
    finally:
        motor.dispose()


def test_la_serie_sembrada_da_su_unica_variacion_atipica_y_no_escribe_nada(_entorno) -> None:
    lista = _sembrar_serie(_entorno)
    navegador, _ = _admin()
    antes = _cuantas_listas(_entorno)
    r = navegador.get(f"{URL}/listas/{lista}/atipicos")
    assert r.status_code == 200, r.text
    assert r.json() == {
        "disponible": True,
        "avisos": [],
        "variaciones": [
            {
                "insumo": INSUMO,
                "porcentaje": "0.39",
                # el exacto a la vista (DESIGN.md): 1/256 = 0,390625 % (memoria §1)
                "porcentaje_exacto": "0.390625",
                "desde": "2026-09-01",
                "hasta": "2026-10-01",
                "severidad": "ADVERTENCIA",
                "descripcion": DESCRIPCION_ATIPICA,
            }
        ],
    }
    assert _cuantas_listas(_entorno) == antes  # solo lee


@pytest.mark.parametrize("serie", [SERIE_SIN_ATIPICO, SERIE_CORTA])
def test_sin_atipicos_o_con_serie_corta_lo_dice_como_la_pagina_clasica(_entorno, serie) -> None:
    lista = _sembrar_serie(_entorno, serie)
    navegador, _ = _admin()
    r = navegador.get(f"{URL}/listas/{lista}/atipicos")
    assert r.status_code == 200, r.text
    assert r.json() == {
        "disponible": True,
        "avisos": [{"nivel": "success", "texto": NADA_ATIPICO}],
        "variaciones": [],
    }


def test_un_precio_en_bs_sin_tasa_se_nombra_sin_escapar(_entorno) -> None:
    """El texto va tal cual: la interfaz nueva no pinta Markdown (la clasica lo escapa, RV-14)."""
    lista = _sembrar_serie(_entorno, sin_tasa="Lista-Bs demo [sin tasa]")
    navegador, _ = _admin()
    cuerpo = navegador.get(f"{URL}/listas/{lista}/atipicos").json()
    assert cuerpo["avisos"] == [
        {"nivel": "info", "texto": "Precio en Bs sin tasa, omitido: Lista-Bs demo [sin tasa]"}
    ]
    assert [v["descripcion"] for v in cuerpo["variaciones"]] == [DESCRIPCION_ATIPICA]


def test_sin_el_extra_ml_no_busca_y_lo_dice(_entorno, monkeypatch) -> None:
    lista = _sembrar_serie(_entorno)
    navegador, _ = _admin()
    relacionados = ("ml", "ml.anomaly", "ml.anomaly.series", "ml.anomaly.detector")
    with SinExtra(monkeypatch, ("ml",), relacionados):
        r = navegador.get(f"{URL}/listas/{lista}/atipicos")
    assert r.status_code == 200, r.text
    assert r.json() == {
        "disponible": False,
        "avisos": [{"nivel": "info", "texto": SIN_ML}],
        "variaciones": [],
    }


def test_solo_las_listas_de_empresa_se_revisan_y_el_404_no_trae_pistas(_entorno) -> None:
    _sembrar_serie(_entorno)
    navegador, _ = _admin()
    base = navegador.get(URL).json()["bases"][0]["id"]
    for lista in (base, 987654):
        r = navegador.get(f"{URL}/listas/{lista}/atipicos")
        assert r.status_code == 404, r.text
        assert r.json() == {"detalle": f"la lista {lista} no es una lista de empresa de este caso"}
        _sin_pistas(r)


def test_un_id_de_lista_invalido_no_se_repite() -> None:
    navegador, _ = _admin()
    r = navegador.get(f"{URL}/listas/id-secreto/atipicos")
    assert (r.status_code, r.json()) == (422, {"detalle": MENSAJE_INVALIDO})
    assert "id-secreto" not in r.text


def test_un_error_de_base_al_buscar_no_sale_con_su_sql(_entorno, monkeypatch) -> None:
    lista = _sembrar_serie(_entorno)
    navegador, _ = _admin()

    def rota(*_args, **_kwargs):
        raise OperationalError("SELECT secreto FROM precio_insumo", {}, Exception("rota"))

    monkeypatch.setattr("aplicacion.atipicos.codigos_de_la_lista", rota)
    r = navegador.get(f"{URL}/listas/{lista}/atipicos")
    assert (r.status_code, r.json()) == (
        503,
        {"detalle": "No se pudo leer o escribir el caso abierto."},
    )
    _sin_pistas(r)


def test_la_clave_de_api_lee_los_atipicos_y_sin_sesion_es_401(_entorno) -> None:
    """Solo lectura: cualquiera con acceso a la pagina (sesion del administrador o clave de API)."""
    lista = _sembrar_serie(_entorno)
    r = _con_clave(crear_clave_de_prueba()).get(f"{URL}/listas/{lista}/atipicos")
    assert r.status_code == 200, r.text
    assert [v["insumo"] for v in r.json()["variaciones"]] == [INSUMO]
    assert cliente(app).get(f"{URL}/listas/{lista}/atipicos").status_code == 401
