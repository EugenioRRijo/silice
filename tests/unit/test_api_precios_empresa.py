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

Oraculos escritos a mano: las filas de la memoria `s1_precios_empresa.md` (impacto por unidad), el
nombre por defecto `<empresa> <fecha>`, las 111 filas de `lista_maprex_bs.csv` contadas con `csv`
y los mensajes literales de la pagina clasica.
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

from api import caso_web, dependencias
from api.admin_acceso import MENSAJE_SOLO_CUENTA
from api.main import app
from api.rutas import precios_empresa as ruta
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_motor
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
        "detalle": "No se cargo la referencia: no se pudo leer el archivo de la referencia."
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
        == "Estos insumos no estan en el catalogo y no entraron a la lista (UC-17 4a):"
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
        ({"moneda": "EUR"}, "No se creo la lista: "),
        ({"empresa": "  "}, "No se creo la lista: la empresa (nombre y RIF)"),
        ({"fuente": ""}, "No se creo la lista: la empresa (nombre y RIF)"),
        ({"base_id": 9999}, "No se creo la lista: la lista base 9999 no existe en este caso"),
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
    assert r.json() == {"detalle": "No se creo la lista: el archivo debe ser CSV o XLSX."}
    r = _crear(navegador, cabeceras, base, archivo=_archivo(b"no es un zip", "precios.xlsx"))
    assert r.status_code == 422, r.text
    assert r.json()["detalle"].startswith("No se creo la lista: precios.xlsx: no se puede leer")
    monkeypatch.setattr(ruta, "TOPE_BYTES", 100)
    r = _crear(navegador, cabeceras, base)
    assert r.status_code == 422, r.text
    assert r.json() == {
        "detalle": "No se creo la lista: el archivo pesa mas del maximo permitido (20 MiB)."
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
        cuerpo["nota"] == "Sin version, el impacto es por unidad de insumo. Nada de esto se guarda."
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
    assert r.json()["detalle"].startswith("No se creo la lista: _NUL.xlsx: no se puede leer")
    r = _crear(navegador, cabeceras, base, archivo=_archivo(nombre="a:b.csv"))
    assert r.status_code == 422, r.text
    assert r.json() == {"detalle": "No se creo la lista: el archivo debe ser CSV o XLSX."}
