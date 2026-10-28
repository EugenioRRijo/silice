"""`/v1/mercado`: las rutas del estudio de mercado y «Usar este precio» (MP-5, Tarea 14 del plan de
montar un presupuesto; diseño §5.1 y §10, D-MP2).

Contrato (todas con `EDITAR_HOJA`: arma o clave de API; revisa y administra reciben 403;
`Cache-Control: no-store` en toda respuesta; 422 de forma con un mensaje fijo que no repite lo
enviado; montos como texto con punto decimal; un fallo de la base es un 503 sin SQL ni rutas):

- `GET /v1/mercado/{lado}/{codigo}?dias=90&proyecto=` → `{lado, codigo, moneda, estadisticas,
  propuesta, piso, precio_unitario, observaciones}`.
- `POST /v1/mercado/observaciones` → 201 `{id}`; `POST /v1/mercado/observaciones/{id}/anular` → 200.
- `GET /v1/mercado/compra/{codigo}/afectados` → `{apus}`.
- `POST /v1/mercado/compra/{codigo}/usar` `{precio, observacion_id}` → 200 `{lista}`.
- `POST /v1/mercado/cobro/{codigo}/usar` `{precio, observaciones}` → 200 `{codigo, precio, moneda}`.
- `GET /v1/mercado/objetivos?partidas=A,B&pu=A:2074.44&moneda=Bs` → `{objetivos: [{codigo, precio,
  moneda, margen}]}` (Tarea 16: el margen lo calcula la API con los precios unitarios de la Hoja).

El router se monta en una aplicación propia con el de la sesión (para entrar) y los manejadores de
`api.main`, porque `api/main.py` es un archivo compartido que integra el orquestador.

Caso FICTICIO (carpeta «Contratista Demo» en Bs; nada es real): lista «Lista demo en Bs» del
01/07/2026 con Cemento gris (MAT-001) a 18,00, Arena lavada (MAT-002) a 25,00 y Albañil (MO-001) a
100,00; partidas OBRA-02 (1 saco de cemento y 0,5 m3 de arena), OBRA-03 (1 albañil, rendimiento 10)
y OBRA-04 (2 sacos de cemento); obra OBRA-01 con la versión VIV-001 (administración 0,25). Hoy es
25/10/2026 (`ahora` fijado). Oráculos a mano:

- Compra del cemento [19,00; 20,00; 22,50]: primer cuartil en (3 − 1)·0,25 = 0,5 → 19 + 0,5 × 1 =
  19,50; mediana en 1 → 20,00; promedio 61,50 / 3 = 20,50.
- OBRA-04 con los parámetros por omisión: costo directo 2 × 18 = 36,00; piso 36 × 1,15 = 41,40;
  precio con utilidad 41,40 × 1,10 = 45,54. Con la VIV-001 (administración 0,25): piso 45,00 y
  45 × 1,10 = 49,50. El mercado [40, 42, 44, 46, 48] tiene primer cuartil 42 (posición 1).
- Con el cemento a 20,00, OBRA-04 cuesta 40 → 46 → 50,60 con utilidad; a 22,00, 55,66.
- La lista de hoy derivada se llama «Lista demo en Bs al 25/10/2026», y la siguiente del mismo día
  «… (2)».
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import get_args

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.main import manejar_http_exception
from api.proteccion import proteger
from api.rutas import mercado as rutas_mercado
from api.rutas import sesion
from aplicacion.cifras import MENSAJE_CIFRA
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from aplicacion.mercado import FUENTES, LADOS, MENSAJE_SIN_MONEDA, CarpetaSinMoneda
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.contracts.apu import ComposicionAPU, LineaManoObra, LineaMaterial, ParametrosCosto
from core.contracts.dominio import Dominio
from core.costing import calcular_apu
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

HOY = date(2026, 10, 25)
AHORA = datetime(2026, 10, 25, 9, 30)
JULIO = date(2026, 7, 1)
LISTA = "Lista demo en Bs"
LISTA_DE_HOY = "Lista demo en Bs al 25/10/2026"
RUTA = "/v1/mercado"
MENSAJE_FORMA = (
    "Los datos del estudio de mercado no son válidos: el lado es compra o cobro; la fuente es "
    "proveedor, competidor, cotización, MaPreX o compra; la fecha va como aaaa-mm-dd; el precio "
    "va como texto; los códigos admiten hasta 40 caracteres y la ventana va de 1 a 3.650 días."
)
MENSAJE_BASE = "No se pudo leer ni guardar el estudio de mercado de la carpeta de trabajo."
PRIVADO = "valor-que-nunca-debe-volver"
#: El 422 de `pu` (los precios unitarios de la Hoja) tiene su propio mensaje fijo (árbitro de T16).
MENSAJE_PU = (
    "Los precios unitarios de la Hoja no son válidos: cada uno va como código:monto, separados "
    "por coma, con punto decimal y con la moneda de esos precios."
)
POR_ENCIMA = "Primer cuartil del mercado, igual o por encima de su costo."
POR_DEBAJO = "La competencia cobra menos que su costo: se propone su costo."

INSUMOS = (
    ("MAT-001", "material", "Cemento gris", "saco", Decimal("18.00")),
    ("MAT-002", "material", "Arena lavada", "m3", Decimal("25.00")),
    ("MO-001", "mano_obra", "Albañil", None, Decimal("100.00")),
)
PARED = ComposicionAPU(
    codigo_partida="OBRA-02",
    descripcion="Pared ficticia de bloques",
    unidad="m2",
    rendimiento=Decimal("1"),
    materiales=(
        LineaMaterial("Cemento gris", "saco", Decimal("1"), Decimal("18.00")),
        LineaMaterial("Arena lavada", "m3", Decimal("0.5"), Decimal("25.00")),
    ),
)
EXCAVACION = ComposicionAPU(
    codigo_partida="OBRA-03",
    descripcion="Excavación ficticia a mano",
    unidad="m3",
    rendimiento=Decimal("10"),
    mano_obra=(LineaManoObra("Albañil", Decimal("1"), Decimal("100.00")),),
)
CONCRETO = ComposicionAPU(
    codigo_partida="OBRA-04",
    descripcion="Concreto ficticio para losa",
    unidad="m3",
    rendimiento=Decimal("1"),
    materiales=(LineaMaterial("Cemento gris", "saco", Decimal("2"), Decimal("18.00")),),
)


def _aplicacion() -> FastAPI:
    aplicacion = FastAPI()
    aplicacion.add_exception_handler(HTTPException, manejar_http_exception)
    aplicacion.include_router(sesion.router)
    aplicacion.include_router(rutas_mercado.router)
    proteger(aplicacion)
    return aplicacion


APLICACION = _aplicacion()


def _sembrar(s) -> None:
    insumos = {}
    for codigo, tipo, descripcion, unidad, _ in INSUMOS:
        insumos[codigo] = models.Insumo(
            codigo=codigo, tipo=tipo, descripcion=descripcion, unidad=unidad
        )
        s.add(insumos[codigo])
    lista = models.ListaPrecios(nombre=LISTA, moneda="Bs", fecha_vigencia=JULIO, origen="")
    s.add(lista)
    s.flush()
    for codigo, *_, precio in INSUMOS:
        s.add(models.PrecioInsumo(lista_id=lista.id, insumo_id=insumos[codigo].id, precio=precio))
    s.flush()
    catalogo = Catalogo(s)
    for composicion in (PARED, EXCAVACION, CONCRETO):
        catalogo.cargar_composicion(
            composicion, lista, Dominio.CIVIL, JULIO, "rendimiento ficticio de prueba"
        )
    obra = models.Proyecto(nombre="OBRA-01", descripcion="Vivienda ficticia de 80 m²")
    s.add(obra)
    s.flush()
    s.add(
        models.Presupuesto(
            codigo="VIV-001",
            proyecto_id=obra.id,
            fecha=HOY,
            moneda="Bs",
            lista_precios_id=lista.id,
            fcas=Decimal("6.00"),
            bono_alimentacion=Decimal("1.00"),
            administracion=Decimal("0.25"),
            utilidad=Decimal("0.10"),
        )
    )
    declarar_moneda_de_la_carpeta(s, "Bs", responsable="Ana <ana>", ahora=AHORA)


def _caso(ruta: Path) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            _sembrar(s)
            s.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_mercado")
    return {"instalacion": plantilla_con_cuentas(carpeta), "caso": _caso(carpeta / "caso.db")}


@pytest.fixture(autouse=True)
def caso(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    copiar_instalacion(_plantillas["instalacion"])
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    copia = tmp_path / "caso.db"
    copia.write_bytes(_plantillas["caso"].read_bytes())
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{copia.as_posix()}")
    monkeypatch.setattr(rutas_mercado, "ahora", lambda: AHORA)
    yield copia
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


@pytest.fixture
def ana() -> tuple[TestClient, dict[str, str]]:
    navegador, ficha = con_cuenta(APLICACION, "ana")
    return navegador, protegida(ficha)


def _en_el_caso(ruta: Path, hacer):
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            resultado = hacer(s)
            s.commit()
            return resultado
    finally:
        motor.dispose()


def _precio(ruta: Path, lista: str, codigo: str) -> Decimal:
    return _en_el_caso(
        ruta,
        lambda s: s.scalars(
            select(models.PrecioInsumo.precio)
            .join(models.ListaPrecios)
            .join(models.Insumo)
            .where(models.ListaPrecios.nombre == lista, models.Insumo.codigo == codigo)
        ).one(),
    )


def _sin_cache(respuesta) -> None:
    assert respuesta.headers.get("cache-control") == "no-store", respuesta.headers


def _observar(ana, codigo: str, precios: list[str], *, lado: str = "compra") -> list[int]:
    navegador, cabeceras = ana
    ids = []
    for precio in precios:
        respuesta = navegador.post(
            f"{RUTA}/observaciones",
            json={
                "lado": lado,
                "codigo": codigo,
                "fuente_tipo": "proveedor" if lado == "compra" else "competidor",
                "fuente": "Ferretería Demo" if lado == "compra" else "Constructora Ejemplo",
                "fecha": "2026-10-20",
                "precio": precio,
                "nota": "",
            },
            headers=cabeceras,
        )
        assert respuesta.status_code == 201, respuesta.text
        _sin_cache(respuesta)
        ids.append(respuesta.json()["id"])
    return ids


# --- el esquema valida lado y fuente con los valores de la lógica --------------------------------


def test_el_esquema_admite_los_lados_y_las_fuentes_de_la_logica() -> None:
    assert get_args(rutas_mercado.Lado) == LADOS
    assert get_args(rutas_mercado.FuenteTipo) == FUENTES


# --- leer el estudio ----------------------------------------------------------------------------


def test_tres_observaciones_de_compra_dan_sus_cifras_como_texto(ana) -> None:
    ids = _observar(ana, "MAT-001", ["20,00", "19,00", "22,50"])
    respuesta = ana[0].get(f"{RUTA}/compra/MAT-001")
    assert respuesta.status_code == 200, respuesta.text
    _sin_cache(respuesta)
    cuerpo = respuesta.json()
    assert {k: v for k, v in cuerpo.items() if k != "observaciones"} == {
        "lado": "compra",
        "codigo": "MAT-001",
        "moneda": "Bs",
        "estadisticas": {
            "n": 3,
            "minimo": "19.00",
            "q1": "19.50",
            "mediana": "20.00",
            "promedio": "20.50",
            "maximo": "22.50",
            "ids": ids,
            "convertidas": 0,
            "sin_tasa": 0,
            "dias": 90,
        },
        "propuesta": {
            "precio": "20.00",
            "razon": "Mediana de 3 observaciones; la más barata vista: 19,00 Bs.",
        },
        "piso": None,
        "precio_unitario": None,
    }
    assert cuerpo["observaciones"][0] == {
        "id": ids[0],
        "fuente_tipo": "proveedor",
        "fuente": "Ferretería Demo",
        "fecha": "2026-10-20",
        "moneda": "Bs",
        "precio": "20.00",
        "nota": "",
        "responsable": "Ana <ana>",
        "cuenta": True,
        "equivalencia": None,
        "sin_tasa": None,
    }
    assert [o["id"] for o in cuerpo["observaciones"]] == ids


def test_una_observacion_en_usd_se_cita_convertida_con_la_tasa_de_su_dia(ana, caso: Path) -> None:
    """Oráculo a mano (D3): 20,00 y 22,50 Bs más 3,00 USD del 20/10 × 36,50 = 109,50 Bs; otra de
    4,00 USD del 21/10 no tiene tasa de ese día (solo la del 20/10): fuera y contada aparte.
    Ordenados [20,00; 22,50; 109,50]: mínimo 20,00, mediana 22,50, promedio 152,00 / 3 = 50,666…
    → 50,67, máximo 109,50."""
    from aplicacion.tablas_mercado import ObservacionDeMercado
    from tests.fixtures.hoja_versiones_api import registrar_tasa_en

    _observar(ana, "MAT-001", ["20,00", "22,50"])

    def sembrar(s) -> list[int]:
        registrar_tasa_en(s, date(2026, 10, 20), "36.50")
        ids = []
        for precio, dia in ((Decimal("3.00"), 20), (Decimal("4.00"), 21)):
            fila = ObservacionDeMercado(
                lado="compra",
                codigo="MAT-001",
                fuente_tipo="cotizacion",
                fuente="Proveedor Ejemplo",
                fecha=date(2026, 10, dia),
                moneda="USD",
                precio=precio,
                nota="",
                responsable="Ana <ana>",
                fecha_hora=AHORA,
            )
            s.add(fila)
            s.flush()
            ids.append(fila.id)
        return ids

    convertida, sin_tasa = _en_el_caso(caso, sembrar)
    cuerpo = ana[0].get(f"{RUTA}/compra/MAT-001").json()
    est = cuerpo["estadisticas"]
    assert (est["n"], est["convertidas"], est["sin_tasa"]) == (3, 1, 1)
    assert (est["minimo"], est["mediana"], est["promedio"], est["maximo"]) == (
        "20.00",
        "22.50",
        "50.67",
        "109.50",
    )
    por_id = {o["id"]: o for o in cuerpo["observaciones"]}
    assert (por_id[convertida]["precio"], por_id[convertida]["moneda"]) == ("3.00", "USD")
    assert por_id[convertida]["cuenta"] is True and por_id[convertida]["sin_tasa"] is None
    equivalencia = por_id[convertida]["equivalencia"]
    # El resultado es exacto (3,00 × 36,50 = 109,5000: los ceros finales de la multiplicación)
    assert Decimal(equivalencia.pop("convertido")) == Decimal("109.50")
    assert {k: v for k, v in equivalencia.items() if k != "fuente_tasa"} == {
        "precio_original": "3.00",
        "moneda_original": "USD",
        "tasa": "36.50",
        "fecha_tasa": "2026-10-20",
        "fuente_legible": "BCV, publicación del 20/10/2026",
        "moneda": "Bs",
        "operacion": "×",
    }
    assert equivalencia["fuente_tasa"].startswith("importacion:")
    assert por_id[sin_tasa]["cuenta"] is False and por_id[sin_tasa]["equivalencia"] is None
    assert por_id[sin_tasa]["sin_tasa"] == "sin tasa del BCV del 21/10/2026"


def test_la_ventana_se_cambia_con_dias(ana) -> None:
    _observar(ana, "MAT-001", ["20,00"])  # del 20/10: a 5 días
    cuerpo = ana[0].get(f"{RUTA}/compra/MAT-001", params={"dias": 4}).json()
    assert (cuerpo["estadisticas"]["n"], cuerpo["estadisticas"]["dias"]) == (0, 4)
    assert cuerpo["propuesta"] == {
        "precio": None,
        "razon": "Sin observaciones en los últimos 4 días.",
    }
    assert cuerpo["observaciones"] == []


def test_el_cobro_dice_su_piso_su_precio_con_utilidad_y_la_propuesta(ana) -> None:
    _observar(ana, "OBRA-04", ["40", "42", "44", "46", "48"], lado="cobro")
    cuerpo = ana[0].get(f"{RUTA}/cobro/OBRA-04").json()
    assert (cuerpo["piso"], cuerpo["precio_unitario"]) == ("41.40", "45.54")
    assert cuerpo["propuesta"] == {"precio": "42.00", "razon": POR_ENCIMA}


def test_el_piso_usa_los_parametros_de_la_obra_abierta(ana) -> None:
    _observar(ana, "OBRA-04", ["40", "42", "44", "46", "48"], lado="cobro")
    cuerpo = ana[0].get(f"{RUTA}/cobro/OBRA-04", params={"proyecto": "OBRA-01"}).json()
    assert (cuerpo["piso"], cuerpo["precio_unitario"]) == ("45.00", "49.50")
    assert cuerpo["propuesta"] == {"precio": "45.00", "razon": POR_DEBAJO}


def test_lo_que_no_existe_es_404(ana) -> None:
    navegador = ana[0]
    insumo = navegador.get(f"{RUTA}/compra/MAT-999")
    assert (insumo.status_code, insumo.json()) == (
        404,
        {"detalle": "No hay ningún insumo «MAT-999» en esta carpeta de trabajo."},
    )
    partida = navegador.get(f"{RUTA}/cobro/OBRA-99")
    assert (partida.status_code, partida.json()) == (
        404,
        {"detalle": "No hay ninguna partida «OBRA-99» en el catálogo de esta carpeta de trabajo."},
    )
    obra = navegador.get(f"{RUTA}/cobro/OBRA-04", params={"proyecto": "OBRA-77"})
    assert (obra.status_code, obra.json()) == (
        404,
        {"detalle": "No hay ninguna obra «OBRA-77» en esta carpeta de trabajo."},
    )
    _sin_cache(obra)


def test_sin_moneda_en_la_carpeta_es_409_con_su_mensaje(
    ana, monkeypatch: pytest.MonkeyPatch
) -> None:
    def sin_moneda(*_args, **_kwargs):
        raise CarpetaSinMoneda(MENSAJE_SIN_MONEDA)

    monkeypatch.setattr(rutas_mercado, "estadisticas", sin_moneda)
    respuesta = ana[0].get(f"{RUTA}/compra/MAT-001")
    assert (respuesta.status_code, respuesta.json()) == (409, {"detalle": MENSAJE_SIN_MONEDA})


# --- anular -------------------------------------------------------------------------------------


def test_una_observacion_anulada_sale_de_las_estadisticas(ana) -> None:
    navegador, cabeceras = ana
    ids = _observar(ana, "MAT-001", ["19,00", "22,00"])
    respuesta = navegador.post(f"{RUTA}/observaciones/{ids[0]}/anular", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    _sin_cache(respuesta)
    cuerpo = navegador.get(f"{RUTA}/compra/MAT-001").json()
    assert (cuerpo["estadisticas"]["n"], cuerpo["estadisticas"]["minimo"]) == (1, "22.00")
    assert [o["id"] for o in cuerpo["observaciones"]] == [ids[1]]
    otra_vez = navegador.post(f"{RUTA}/observaciones/{ids[0]}/anular", headers=cabeceras)
    assert (otra_vez.status_code, otra_vez.json()) == (
        409,
        {"detalle": f"La observación n.º {ids[0]} ya está anulada."},
    )
    nada = navegador.post(f"{RUTA}/observaciones/999/anular", headers=cabeceras)
    assert (nada.status_code, nada.json()) == (
        404,
        {"detalle": "No hay ninguna observación n.º 999 en esta carpeta de trabajo."},
    )


# --- usar un precio de compra -------------------------------------------------------------------


def test_los_apu_afectados_del_cemento(ana) -> None:
    respuesta = ana[0].get(f"{RUTA}/compra/MAT-001/afectados")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"apus": ["OBRA-02", "OBRA-04"]}
    _sin_cache(respuesta)
    assert ana[0].get(f"{RUTA}/compra/MAT-999/afectados").status_code == 404


def test_usar_un_precio_de_compra_lo_pone_en_la_lista_de_hoy(ana, caso: Path) -> None:
    navegador, cabeceras = ana
    ids = _observar(ana, "MAT-001", ["20,00"])
    respuesta = navegador.post(
        f"{RUTA}/compra/MAT-001/usar",
        json={"precio": "20,00", "observacion_id": ids[0]},
        headers=cabeceras,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"lista": LISTA_DE_HOY, "corte": None, "equivalencia": None}
    _sin_cache(respuesta)
    assert _precio(caso, LISTA_DE_HOY, "MAT-001") == Decimal("20.00")
    assert _precio(caso, LISTA, "MAT-001") == Decimal("18.00")


def test_con_una_version_sobre_la_lista_de_hoy_se_crea_otra_y_la_version_no_cambia(
    ana, caso: Path
) -> None:
    navegador, cabeceras = ana
    primera = navegador.post(
        f"{RUTA}/compra/MAT-001/usar",
        json={"precio": "20,00", "observacion_id": None},
        headers=cabeceras,
    )
    assert primera.json() == {"lista": LISTA_DE_HOY, "corte": None, "equivalencia": None}

    def version_sobre_la_lista_de_hoy(s) -> int:
        lista = s.scalars(
            select(models.ListaPrecios).where(models.ListaPrecios.nombre == LISTA_DE_HOY)
        ).one()
        obra = s.scalars(select(models.Proyecto).where(models.Proyecto.nombre == "OBRA-01")).one()
        nueva = models.Presupuesto(
            codigo="VIV-002",
            proyecto_id=obra.id,
            fecha=HOY,
            moneda="Bs",
            lista_precios_id=lista.id,
            fcas=Decimal("6.00"),
            bono_alimentacion=Decimal("1.00"),
            administracion=Decimal("0.15"),
            utilidad=Decimal("0.10"),
        )
        s.add(nueva)
        s.flush()
        return nueva.id

    version_id = _en_el_caso(caso, version_sobre_la_lista_de_hoy)
    segunda = navegador.post(
        f"{RUTA}/compra/MAT-001/usar",
        json={"precio": "22,00", "observacion_id": None},
        headers=cabeceras,
    )
    assert segunda.status_code == 200, segunda.text
    assert segunda.json() == {"lista": f"{LISTA_DE_HOY} (2)", "corte": None, "equivalencia": None}
    assert _precio(caso, f"{LISTA_DE_HOY} (2)", "MAT-001") == Decimal("22.00")
    assert _precio(caso, LISTA_DE_HOY, "MAT-001") == Decimal("20.00")

    def precio_de_la_version(s) -> Decimal:
        modelo = s.get(models.Presupuesto, version_id)
        apu = Catalogo(s).composicion("OBRA-04", fecha=HOY, lista=modelo.lista_precios)
        return calcular_apu(apu, ParametrosCosto()).precio_unitario

    assert _en_el_caso(caso, precio_de_la_version) == Decimal("50.60")


def test_un_precio_mal_escrito_es_422_con_la_regla(ana) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(
        f"{RUTA}/compra/MAT-001/usar",
        json={"precio": "2.5", "observacion_id": None},
        headers=cabeceras,
    )
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_CIFRA})
    _sin_cache(respuesta)


def test_una_observacion_ajena_es_422(ana) -> None:
    navegador, cabeceras = ana
    ajena = _observar(ana, "MAT-002", ["30"])[0]
    respuesta = navegador.post(
        f"{RUTA}/compra/MAT-001/usar",
        json={"precio": "20", "observacion_id": ajena},
        headers=cabeceras,
    )
    assert (respuesta.status_code, respuesta.json()) == (
        422,
        {"detalle": "La observación elegida no es un precio vigente de este insumo o partida."},
    )


# --- usar un precio de cobro y leer los objetivos -----------------------------------------------


def test_usar_un_precio_de_cobro_y_leerlo_como_objetivo(ana) -> None:
    navegador, cabeceras = ana
    ids = _observar(ana, "OBRA-04", ["1900", "2000"], lado="cobro")
    respuesta = navegador.post(
        f"{RUTA}/cobro/OBRA-04/usar",
        json={"precio": "1.980,00", "observaciones": ids},
        headers=cabeceras,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"codigo": "OBRA-04", "precio": "1980.00", "moneda": "Bs"}
    _sin_cache(respuesta)
    objetivos = navegador.get(f"{RUTA}/objetivos", params={"partidas": "OBRA-04,OBRA-02"})
    assert objetivos.status_code == 200, objetivos.text
    assert objetivos.json() == {
        "objetivos": [{"codigo": "OBRA-04", "precio": "1980.00", "moneda": "Bs", "margen": None}]
    }
    _sin_cache(objetivos)
    assert navegador.get(f"{RUTA}/objetivos").json() == {"objetivos": []}


# --- forma, permisos y fallos -------------------------------------------------------------------


@pytest.mark.parametrize(
    "cambio",
    [
        {"lado": PRIVADO},
        {"fuente_tipo": PRIVADO},
        {"fuente_tipo": "cotización"},  # el valor interno va sin tilde
        {"fecha": PRIVADO},
        {"codigo": PRIVADO * 2},
        {"precio": 20},
    ],
)
def test_una_observacion_mal_formada_es_422_fijo_sin_eco(ana, cambio: dict) -> None:
    navegador, cabeceras = ana
    cuerpo = {
        "lado": "compra",
        "codigo": "MAT-001",
        "fuente_tipo": "proveedor",
        "fuente": "Ferretería Demo",
        "fecha": "2026-10-20",
        "precio": "20,00",
        "nota": "",
    }
    cuerpo.update(cambio)
    respuesta = navegador.post(f"{RUTA}/observaciones", json=cuerpo, headers=cabeceras)
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_FORMA})
    assert PRIVADO not in respuesta.text
    _sin_cache(respuesta)


@pytest.mark.parametrize(
    "ruta",
    [f"{RUTA}/venta/MAT-001", f"{RUTA}/compra/MAT-001?dias=0", f"{RUTA}/compra/MAT-001?dias=3651"],
)
def test_un_lado_o_una_ventana_fuera_de_lo_admitido_es_422_fijo(ana, ruta: str) -> None:
    respuesta = ana[0].get(ruta)
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_FORMA})


def test_una_regla_de_la_observacion_es_422_con_su_mensaje(ana) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(
        f"{RUTA}/observaciones",
        json={
            "lado": "compra",
            "codigo": "MAT-001",
            "fuente_tipo": "cotizacion",
            "fuente": "Ferretería Demo",
            "fecha": "2026-10-26",
            "precio": "20,00",
        },
        headers=cabeceras,
    )
    assert (respuesta.status_code, respuesta.json()) == (
        422,
        {"detalle": "La fecha de la observación no puede ser posterior a hoy."},
    )


@pytest.mark.parametrize("login", ["rita", "admin"])
def test_quien_no_arma_recibe_403(login: str) -> None:
    navegador, ficha = con_cuenta(APLICACION, login)
    for respuesta in (
        navegador.get(f"{RUTA}/compra/MAT-001"),
        navegador.get(f"{RUTA}/objetivos"),
        navegador.post(
            f"{RUTA}/cobro/OBRA-04/usar",
            json={"precio": "1980", "observaciones": []},
            headers=protegida(ficha),
        ),
    ):
        assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": MENSAJE_PERMISO})
        _sin_cache(respuesta)


def test_escribir_sin_csrf_es_403(ana) -> None:
    respuesta = ana[0].post(
        f"{RUTA}/cobro/OBRA-04/usar",
        json={"precio": "1980", "observaciones": []},
        headers={"Origin": "http://127.0.0.1:8000"},
    )
    assert respuesta.status_code == 403


def test_con_la_clave_de_api_consta_el_usuario_de_la_api() -> None:
    navegador = cliente(APLICACION)
    respuesta = navegador.post(
        f"{RUTA}/observaciones",
        json={
            "lado": "compra",
            "codigo": "MAT-001",
            "fuente_tipo": "maprex",
            "fuente": "MaPreX ficticio",
            "fecha": "2026-10-20",
            "precio": "20,00",
        },
        headers={CABECERA: crear_clave_de_prueba()},
    )
    assert respuesta.status_code == 201, respuesta.text
    leido = navegador.get(f"{RUTA}/compra/MAT-001", headers={CABECERA: crear_clave_de_prueba()})
    assert leido.json()["observaciones"][0]["responsable"] == "api (clave de API)"


def test_un_fallo_de_la_base_es_un_503_sin_sql_ni_rutas(
    ana, monkeypatch: pytest.MonkeyPatch
) -> None:
    def falla(*_args, **_kwargs):
        raise OperationalError(
            "SELECT mp_observacion.precio FROM mp_observacion", {}, Exception("C:/datos/caso.db")
        )

    monkeypatch.setattr(rutas_mercado, "estadisticas", falla)
    monkeypatch.setattr(rutas_mercado, "usar_precio_de_cobro", falla)
    navegador, cabeceras = ana
    for respuesta in (
        navegador.get(f"{RUTA}/compra/MAT-001"),
        navegador.post(
            f"{RUTA}/cobro/OBRA-04/usar",
            json={"precio": "1980", "observaciones": []},
            headers=cabeceras,
        ),
    ):
        assert (respuesta.status_code, respuesta.json()) == (503, {"detalle": MENSAJE_BASE})
        assert "SELECT" not in respuesta.text and "caso.db" not in respuesta.text
        _sin_cache(respuesta)


# --- ronda 2 del árbitro ------------------------------------------------------------------------

MENSAJE_INESPERADO = "No se pudo procesar el estudio de mercado con esos datos."


def test_un_value_error_que_no_es_una_regla_no_sale_por_la_api(
    ana, monkeypatch: pytest.MonkeyPatch
) -> None:
    def falla(*_args, **_kwargs):
        raise ValueError("lado 'x'; detalle interno que no debe salir")

    monkeypatch.setattr(rutas_mercado, "apus_afectados", falla)
    respuesta = ana[0].get(f"{RUTA}/compra/MAT-001/afectados")
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_INESPERADO})
    assert "interno" not in respuesta.text
    _sin_cache(respuesta)


def test_un_precio_objetivo_con_mas_de_dos_decimales_es_422(ana) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(
        f"{RUTA}/cobro/OBRA-04/usar",
        json={"precio": "1.980,005", "observaciones": []},
        headers=cabeceras,
    )
    assert (respuesta.status_code, respuesta.json()) == (
        422,
        {"detalle": "El precio objetivo admite hasta 2 decimales (céntimos)."},
    )
    assert navegador.get(f"{RUTA}/objetivos", params={"partidas": "OBRA-04"}).json() == {
        "objetivos": []
    }


# --- Tarea 16: el margen con el precio unitario de la Hoja ---------------------------------------


def _objetivo(ana, codigo: str, precio: str) -> None:
    respuesta = ana[0].post(
        f"{RUTA}/cobro/{codigo}/usar",
        json={"precio": precio, "observaciones": []},
        headers=ana[1],
    )
    assert respuesta.status_code == 200, respuesta.text


def test_el_precio_objetivo_queda_con_el_responsable_de_la_sesion(ana, caso: Path) -> None:
    from aplicacion.tablas_mercado import PrecioObjetivo

    _objetivo(ana, "OBRA-03", "120")
    filas = _en_el_caso(
        caso,
        lambda s: [(f.codigo_partida, f.responsable) for f in s.scalars(select(PrecioObjetivo))],
    )
    assert filas == [("OBRA-03", "Ana <ana>")]


def _margenes(ana, **params: str) -> dict[str, tuple[str, str, str | None]]:
    respuesta = ana[0].get(f"{RUTA}/objetivos", params=params)
    assert respuesta.status_code == 200, respuesta.text
    _sin_cache(respuesta)
    return {
        o["codigo"]: (o["precio"], o["moneda"], o["margen"]) for o in respuesta.json()["objetivos"]
    }


@pytest.mark.parametrize(
    ("pu", "margen"),
    [
        # (1.980 − 2.074,44) / 2.074,44 × 100 = −94,44 / 20,7444 = −4,5526… → −4,6 (mitad arriba)
        ("2074.44", "-4.6"),
        # el exacto de la Hoja: −94,4449 / 20,744449 = −4,5528… → −4,6
        ("2074.4449", "-4.6"),
        # 180 / 18 = 10 → 10,0: el objetivo queda por encima del precio con utilidad
        ("1800", "10.0"),
        ("1980.00", "0.0"),
        # −0,50 / 19,805 = −0,0252… → −0,0 se dice 0,0 (sin un signo que no significa nada)
        ("1980.50", "0.0"),
        # −20 / 20 = −1 % exacto
        ("2000", "-1.0"),
    ],
)
def test_el_margen_lo_calcula_la_api_con_el_precio_unitario_de_la_hoja(
    ana, pu: str, margen: str
) -> None:
    _objetivo(ana, "OBRA-04", "1.980,00")
    assert _margenes(ana, partidas="OBRA-04", pu=f"OBRA-04:{pu}", moneda="Bs") == {
        "OBRA-04": ("1980.00", "Bs", margen)
    }


def test_sin_precio_unitario_en_otra_moneda_o_con_cero_no_hay_margen(ana, caso: Path) -> None:
    from aplicacion.tablas_mercado import PrecioObjetivo

    _objetivo(ana, "OBRA-04", "1.980,00")
    _objetivo(ana, "OBRA-03", "120")
    _en_el_caso(
        caso,
        lambda s: s.add(
            PrecioObjetivo(
                codigo_partida="OBRA-02",
                precio=Decimal("31.50"),
                moneda="USD",
                observaciones="[]",
                responsable="Ana <ana>",
                fecha_hora=AHORA,
            )
        ),
    )
    partidas = "OBRA-04,OBRA-03,OBRA-02"
    # sin `pu`: como antes de la Tarea 16, el margen va vacío
    assert _margenes(ana, partidas=partidas) == {
        "OBRA-04": ("1980.00", "Bs", None),
        "OBRA-03": ("120.00", "Bs", None),
        "OBRA-02": ("31.50", "USD", None),
    }
    # OBRA-04 sin su precio unitario; OBRA-03 con precio unitario 0 (no se divide entre cero);
    # OBRA-02 en USD y la Hoja en Bs: no se compara (ni se convierte); un `pu` de una partida no
    # pedida no agrega nada.
    assert _margenes(
        ana, partidas=partidas, pu="OBRA-03:0,OBRA-02:30.00,OBRA-09:10", moneda="Bs"
    ) == {
        "OBRA-04": ("1980.00", "Bs", None),
        "OBRA-03": ("120.00", "Bs", None),
        "OBRA-02": ("31.50", "USD", None),
    }
    # la misma partida en USD con la Hoja en USD sí se compara: (31,50 − 30) / 30 = 5 %
    assert _margenes(ana, partidas="OBRA-02", pu="OBRA-02:30.00", moneda="USD") == {
        "OBRA-02": ("31.50", "USD", "5.0")
    }


@pytest.mark.parametrize(
    "params",
    [
        {"pu": "OBRA-04:2.074,44", "moneda": "Bs"},  # la Hoja manda el decimal con punto
        {"pu": "OBRA-04", "moneda": "Bs"},
        {"pu": f"OBRA-04:{PRIVADO}", "moneda": "Bs"},
        {"pu": "OBRA-04:1e3", "moneda": "Bs"},
        {"pu": "OBRA-04:NaN", "moneda": "Bs"},
        {"pu": ":2074.44", "moneda": "Bs"},
        {"pu": "OBRA-04:2074.44,OBRA-04:2000", "moneda": "Bs"},  # la misma partida con dos precios
        {"pu": "OBRA-04:2074.44"},  # sin la moneda de esos precios
        {"pu": f"{PRIVADO * 2}:1", "moneda": "Bs"},  # código de más de 40 caracteres
    ],
)
def test_un_precio_unitario_mal_formado_es_422_fijo_sin_eco(ana, params: dict) -> None:
    respuesta = ana[0].get(f"{RUTA}/objetivos", params={"partidas": "OBRA-04", **params})
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_PU})
    assert PRIVADO not in respuesta.text
    _sin_cache(respuesta)


def test_la_misma_partida_repetida_con_el_mismo_precio_se_acepta(ana) -> None:
    _objetivo(ana, "OBRA-04", "1.980,00")
    assert _margenes(
        ana, partidas="OBRA-04", pu="OBRA-04:2074.44,OBRA-04:2074.44", moneda="Bs"
    ) == {"OBRA-04": ("1980.00", "Bs", "-4.6")}


def test_un_precio_unitario_absurdo_no_tumba_la_tanda(ana) -> None:
    """Un `pu` bien escrito pero diminuto (0,000…01) da un margen que no cabe en la precisión: esa
    partida queda sin margen y las demás siguen (antes, `InvalidOperation` y un 500)."""
    _objetivo(ana, "OBRA-04", "1.980,00")
    _objetivo(ana, "OBRA-03", "120")
    diminuto = "0." + "0" * 40 + "1"
    assert _margenes(
        ana, partidas="OBRA-04,OBRA-03", pu=f"OBRA-04:{diminuto},OBRA-03:100", moneda="Bs"
    ) == {
        "OBRA-04": ("1980.00", "Bs", None),
        # (120 − 100) / 100 = 20 %
        "OBRA-03": ("120.00", "Bs", "20.0"),
    }
