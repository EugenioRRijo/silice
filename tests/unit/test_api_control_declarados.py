"""`/v1/control/calculo` con los precios declarados y la casilla «Declararlo precio del corte» del
estudio de mercado (MP-7, Tarea 25; diseño §11, meta 4).

Sobre la obra ficticia OB-S2 (`tests/fixtures/control_ob_s2.py`) con V-01 y V-02 y su costo real.
Lo que se prueba:

- `metodo=declarados` usa los precios declarados hasta el corte: la separación ya no dice «sin
  precios del corte» y el método y la fuente lo cuentan; sin ninguno declarado, un 422 que lo dice;
- **la perspectiva sale de la línea base** (prueba del defecto: antes la ruta pasaba siempre
  «costo»): con la línea base en la perspectiva precio, la escalatoria con Km = 1 no da desvío y los
  declarados se comparan con el precio unitario;
- `POST /v1/mercado/compra/{codigo}/usar` con `declarar_en` (la obra) declara el precio usado como
  precio del corte, en la misma transacción que la lista (todo o nada).

Oráculos de la memoria de OB-S2 (`tests/fixtures/memorias/control_ob_s2.md`, §1, §3 y §6), a mano:
el material de B pasa de 3,00 a 4,00 y el de C de 12,00 a 14,10 → ΔP = 90 × 0 + 60 × (5 − 6) =
−60,00; ΔC = 1 260 − 1 280 = −20,00. En la perspectiva precio (PU = u × 1,265) con solo B:
ΔP = 60 × (6,325 − 7,59) = −75,90. Con la perspectiva mal tomada («costo» sobre una línea base en
«precio»), la escalatoria con Km = 1 daba 90 × (12,65 − 10) + 60 × (6,325 − 5) = 318,00 en lugar
de 0,00.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import app
from api.rutas import mercado as rutas_mercado
from aplicacion.precios_declarados import declarar_precio_del_corte
from aplicacion.tablas_corte import PrecioDelCorte
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
P = {"proyecto": ob.NOMBRE}
TUBO = "Material de Tuberia de drenaje"
RELLENO = "Material de Relleno compactado"
AHORA = datetime(2026, 11, 10, 9, 0)
SIN_DECLARADOS = (
    "No hay precios declarados de insumos hasta el corte: declárelos desde Estudio de mercado o "
    "al recibir una compra en Procura."
)


def _base(ruta: Path, perspectiva: str) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            ob.declarar_linea_base(sesion, perspectiva)
            ob.registrar_v01_y_v02(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_declarados")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "costo": _base(carpeta / "costo.db", "costo"),
        "precio": _base(carpeta / "precio.db", "precio"),
    }


def _entrar(plantillas: dict[str, Path], nombre: str, tmp_path: Path, monkeypatch) -> Path:
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    copia = tmp_path / f"{nombre}.db"
    copia.write_bytes(plantillas[nombre].read_bytes())
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{copia.as_posix()}")
    return copia


@pytest.fixture(autouse=True)
def caso(
    _plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Path]:
    copiar_instalacion(_plantillas["instalacion"])
    copia = _entrar(_plantillas, "costo", tmp_path, monkeypatch)
    monkeypatch.setattr(rutas_mercado, "ahora", lambda: AHORA)
    yield copia
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _en_el_caso(ruta: Path, hacer):
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            resultado = hacer(sesion)
            sesion.commit()
            return resultado
    finally:
        motor.dispose()


def _declarar(ruta: Path, descripcion: str, unidad: str, precio: str, fecha: date) -> None:
    _en_el_caso(
        ruta,
        lambda s: declarar_precio_del_corte(
            s,
            ob.NOMBRE,
            descripcion=descripcion,
            unidad=unidad,
            precio=D(precio),
            fecha=fecha,
            fuente="cotización ficticia",
            responsable="Ana <ana>",
            ahora=datetime(2026, 11, 20, 17, 0),
        ),
    )


def _arma():
    navegador, ficha = con_cuenta(app, "ana")
    return navegador, protegida(ficha)


def _indicadores(navegador, **params: str) -> dict[str, dict[str, str]]:
    respuesta = navegador.get("/v1/control/calculo", params={**P, **params})
    assert respuesta.status_code == 200, respuesta.text
    return {f["Indicador"]: f for f in respuesta.json()["indicadores"]}


# --- el método «declarados» ----------------------------------------------------------------------


def test_con_los_declarados_la_separacion_ya_no_dice_sin_precios_del_corte(caso: Path) -> None:
    navegador, _ = _arma()
    sin = _indicadores(navegador)
    assert sin["Desvío de precio (USD)"]["Valor"] == "no disponible"
    assert "sin precios del corte" in sin["Desvío de precio (USD)"]["Nota"]

    _declarar(caso, TUBO, "m", "4.00", date(2026, 11, 10))
    _declarar(caso, RELLENO, "m3", "14.10", date(2026, 11, 12))
    ind = _indicadores(navegador, metodo="declarados")
    assert ind["Desvío de precio (USD)"]["Valor"] == "-60.00"
    assert ind["Desvío de precio (USD)"]["Nota"] == ""
    assert ind["Desvío de consumo (USD)"]["Valor"] == "-20.00"
    metodo = ind["Método y fuente del precio del corte"]
    assert (metodo["Valor"], metodo["Nota"]) == (
        "declarados",
        "Precios declarados al 13/11/2026: 2 insumos",
    )


def test_un_declarado_posterior_al_corte_no_cuenta_en_la_api(caso: Path) -> None:
    navegador, _ = _arma()
    _declarar(caso, TUBO, "m", "4.00", date(2026, 11, 16))
    _declarar(caso, RELLENO, "m3", "14.10", date(2026, 11, 12))
    ind = _indicadores(navegador, metodo="declarados")
    # solo C (sin avance al corte): 60 × (5 − 5) + 0 = 0,00
    assert ind["Desvío de precio (USD)"]["Valor"] == "0.00"
    assert ind["Método y fuente del precio del corte"]["Nota"] == (
        "Precios declarados al 13/11/2026: 1 insumo"
    )


def test_sin_precios_declarados_el_metodo_lo_dice_con_422(caso: Path) -> None:
    navegador, _ = _arma()
    respuesta = navegador.get("/v1/control/calculo", params={**P, "metodo": "declarados"})
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": SIN_DECLARADOS})


# --- la perspectiva sale de la línea base (prueba del defecto) ---------------------------------


def test_la_escalatoria_usa_la_perspectiva_de_la_linea_base(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _entrar(_plantillas, "precio", tmp_path, monkeypatch)
    navegador, _ = _arma()
    ind = _indicadores(navegador, metodo="escalatoria", km="1", r="0", fuente="Km ficticio")
    # Km = 1: u' = u, sin desvío (antes, 318,00 por comparar costo con precio unitario)
    assert ind["Desvío de precio (USD)"]["Valor"] == "0.00"


def test_los_declarados_en_la_perspectiva_precio_usan_el_precio_unitario(
    _plantillas: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copia = _entrar(_plantillas, "precio", tmp_path, monkeypatch)
    _declarar(copia, TUBO, "m", "4.00", date(2026, 11, 10))
    navegador, _ = _arma()
    ind = _indicadores(navegador, metodo="declarados")
    assert ind["Desvío de precio (USD)"]["Valor"] == "-75.90"


# --- la casilla del estudio de mercado ----------------------------------------------------------


def _codigo(ruta: Path, descripcion: str) -> str:
    return _en_el_caso(
        ruta,
        lambda s: s.scalars(
            select(models.Insumo.codigo).where(models.Insumo.descripcion == descripcion)
        ).one(),
    )


def _declarados(ruta: Path) -> list[tuple[str, str, Decimal, str, date, str, str]]:
    return _en_el_caso(
        ruta,
        lambda s: [
            (f.descripcion_insumo, f.unidad, f.precio, f.moneda, f.fecha, f.fuente, f.responsable)
            for f in s.scalars(select(PrecioDelCorte).order_by(PrecioDelCorte.id))
        ],
    )


def test_desde_el_estudio_de_mercado_la_casilla_declara_el_precio_del_corte(caso: Path) -> None:
    navegador, cabeceras = _arma()
    codigo = _codigo(caso, TUBO)
    respuesta = navegador.post(
        f"/v1/mercado/compra/{codigo}/usar",
        json={"precio": "4,00", "observacion_id": None, "declarar_en": ob.NOMBRE},
        headers=cabeceras,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["corte"] == (
        "Declarado precio del corte de la obra «OB-S2» desde el 10/11/2026."
    )
    [declarado] = _declarados(caso)
    assert declarado[:6] == (
        TUBO,
        "m",
        D("4.00"),
        "USD",
        date(2026, 11, 10),
        "Estudio de mercado: precio propio",
    )
    assert "<ana>" in declarado[6]  # quien consta es la cuenta de la sesión
    ind = _indicadores(navegador, metodo="declarados")
    assert ind["Desvío de precio (USD)"]["Valor"] == "-60.00"


def test_sin_la_casilla_no_se_declara_nada(caso: Path) -> None:
    navegador, cabeceras = _arma()
    respuesta = navegador.post(
        f"/v1/mercado/compra/{_codigo(caso, TUBO)}/usar",
        json={"precio": "4,00", "observacion_id": None},
        headers=cabeceras,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["corte"] is None
    assert _declarados(caso) == []


def test_si_no_se_puede_declarar_tampoco_cambia_la_lista(caso: Path) -> None:
    navegador, cabeceras = _arma()

    def listas(s) -> list[str]:
        return list(s.scalars(select(models.ListaPrecios.nombre).order_by(models.ListaPrecios.id)))

    antes = _en_el_caso(caso, listas)
    # un equipo no es un material de la línea base: 404 y ni la lista de hoy ni el declarado
    respuesta = navegador.post(
        f"/v1/mercado/compra/{_codigo(caso, 'Equipo de Excavacion de zanja')}/usar",
        json={"precio": "1,00", "observacion_id": None, "declarar_en": ob.NOMBRE},
        headers=cabeceras,
    )
    assert respuesta.status_code == 404, respuesta.text
    assert respuesta.json() == {
        "detalle": "«Equipo de Excavacion de zanja» no es un material de la línea base de la "
        "obra «OB-S2»."
    }
    assert _en_el_caso(caso, listas) == antes
    assert _declarados(caso) == []


def test_la_obra_de_la_casilla_que_no_existe_es_404(caso: Path) -> None:
    navegador, cabeceras = _arma()
    respuesta = navegador.post(
        f"/v1/mercado/compra/{_codigo(caso, TUBO)}/usar",
        json={"precio": "4,00", "observacion_id": None, "declarar_en": "NO-HAY"},
        headers=cabeceras,
    )
    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detalle": "No hay ninguna obra «NO-HAY» en esta carpeta de trabajo."
    }
    assert _declarados(caso) == []
