"""UC-03 en «Partidas similares» (INV-091): la propuesta desplegada y el desglose incompleto.

`tests/unit/test_ui_similares.py` prueba la degradacion de la pagina (sin el extra, modelo roto);
estas pruebas fijan lo que la pagina hace cuando el modelo si propone:

- **Pasos 3 y 4:** al desplegar una propuesta, la pagina precarga su desglose (materiales, equipos
  y mano de obra) y su rendimiento, con la partida de origen y el puntaje que la propuso.
- **Flujo 4a:** si el desglose de una propuesta usa un insumo sin precio en la lista vigente, la
  pagina lo senala con un aviso que nombra el insumo y no muestra un desglose a medias; las demas
  propuestas siguen mostrando el suyo.

La propuesta del modelo se sustituye por un doble con puntajes fijos (el ranking real lo prueban
`tests/unit/test_normalizacion.py` y `tests/integration/test_api.py`; ninguna prueba de pantalla
recorre esta pagina con el modelo real en el camino de exito); asi el puntaje que se lee en
pantalla tiene un oraculo exacto. El doble comprueba lo que la pagina le pasa: el catalogo como
pares (codigo, descripcion) y la descripcion tecleada. El oraculo del desglose es la linea base
(`tests/fixtures/apu_linea_base.py`), que `scripts/seed.py` siembra en una base de `tmp_path`,
desviada por el objeto modulo `sys.modules["ui.caso"]`. El paso 5 (ajustar y recalcular) no lo hace
esta pagina, que es de solo lectura (UC-10, paso 6, en «Componer una partida»).
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from pandas import DataFrame
from sqlalchemy import delete, select
from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.contracts import ComposicionAPU
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from ml.normalization import PartidaSimilar, Propuesta
from scripts.seed import sembrar
from tests.conftest import RUTA_BASE_REAL, huella
from tests.fixtures.apu_linea_base import APU_CONCRETO, APU_EXCAVACION, APUS_LINEA_BASE

SCRIPT = "from ui.paginas.similares import render\nrender()\n"
ROTULO_DESCRIPCION = "Descripcion de la partida"

#: Puntajes del doble del modelo: el titulo del desplegable los presenta con dos decimales y el
#: pie con cuatro (`ui/paginas/similares.py`).
PUNTAJE_CONCRETO = 0.9137
PUNTAJE_EXCAVACION = 0.6402

#: El insumo que la prueba del flujo 4a deja sin precio: el primer material del concreto.
INSUMO_SIN_PRECIO = APU_CONCRETO.materiales[0].descripcion


@pytest.fixture
def base_sembrada(tmp_path: Path) -> Path:
    base = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return base


def _quitar_precio(base: Path, descripcion_insumo: str) -> None:
    """Borra el precio del insumo en todas las listas: ninguna lista vigente lo cotiza."""
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ids = sesion.scalars(
                select(models.Insumo.id).where(models.Insumo.descripcion == descripcion_insumo)
            ).all()
            assert ids, f"el insumo {descripcion_insumo!r} no esta sembrado"
            sesion.execute(
                delete(models.PrecioInsumo).where(models.PrecioInsumo.insumo_id.in_(ids))
            )
            sesion.commit()
    finally:
        motor.dispose()


DESCRIPCION_TECLEADA = "concreto para las paredes de una tanquilla"


def _consultar(monkeypatch, base: Path) -> AppTest:
    llamadas: list[tuple[dict[str, str], str]] = []

    def _propuesta(partidas, descripcion) -> Propuesta:
        """El doble del modelo: registra lo que recibe y propone el concreto y la excavacion."""
        llamadas.append((dict(partidas), descripcion))
        return Propuesta(
            (
                PartidaSimilar(
                    APU_CONCRETO.codigo_partida, APU_CONCRETO.descripcion, PUNTAJE_CONCRETO
                ),
                PartidaSimilar(
                    APU_EXCAVACION.codigo_partida, APU_EXCAVACION.descripcion, PUNTAJE_EXCAVACION
                ),
            )
        )

    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    pagina = importlib.import_module("ui.paginas.similares")
    monkeypatch.setattr(pagina, "sugerir_partidas_similares", _propuesta)
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert llamadas == [], "sin descripcion la pagina no debe consultar el modelo"
    next(t for t in at.text_input if t.label == ROTULO_DESCRIPCION).input(
        DESCRIPCION_TECLEADA
    ).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]

    # Lo que la pagina le paso al modelo: la descripcion tecleada y el catalogo sembrado, con la
    # descripcion de cada partida de la linea base (oraculo: el fixture, no la base).
    assert len(llamadas) == 1, llamadas
    partidas, descripcion = llamadas[0]
    assert descripcion == DESCRIPCION_TECLEADA
    for apu in APUS_LINEA_BASE:
        assert partidas.get(apu.codigo_partida) == apu.descripcion, apu.codigo_partida
    return at


def _desplegable(at: AppTest, codigo: str):
    candidatos = [expander for expander in at.expander if f" - {codigo} - " in expander.label]
    assert len(candidatos) == 1, [expander.label for expander in at.expander]
    return candidatos[0]


def _texto(valor) -> str:
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def _tablas_esperadas(apu: ComposicionAPU) -> list[DataFrame]:
    """Las tablas que la pagina debe mostrar para `apu`, en su orden, desde la linea base."""
    return [
        DataFrame(
            [
                {
                    "descripcion": linea.descripcion,
                    "unidad": linea.unidad,
                    "cantidad": _texto(linea.cantidad),
                    "precio": _texto(linea.precio),
                }
                for linea in apu.materiales
            ]
        ),
        DataFrame(
            [
                {
                    "descripcion": linea.descripcion,
                    "cantidad": _texto(linea.cantidad),
                    "precio": _texto(linea.precio),
                    "depreciacion": str(linea.depreciacion),
                }
                for linea in apu.equipos
            ]
        ),
        DataFrame(
            [
                {
                    "descripcion": linea.descripcion,
                    "cantidad": _texto(linea.cantidad),
                    "sueldo": _texto(linea.sueldo),
                }
                for linea in apu.mano_obra
            ]
        ),
    ]


def _comprobar_desglose(desplegable, apu: ComposicionAPU, puntaje: float) -> None:
    # Origen y puntaje (paso 4: la referencia a la partida de origen y el puntaje que la propuso).
    assert desplegable.label == f"{puntaje:.2f} - {apu.codigo_partida} - {apu.descripcion}"
    assert [c.value for c in desplegable.caption] == [
        f"Partida de origen: {apu.codigo_partida} | puntaje de similitud: {puntaje:.4f}"
    ]
    # Rendimiento, con su unidad.
    cabecera = desplegable.markdown[0].value
    assert f"**Unidad:** {apu.unidad}" in cabecera
    assert f"**Rendimiento:** {_texto(apu.rendimiento)} {apu.unidad}/dia" in cabecera
    # Desglose: las tablas no vacias de la linea base, en orden.
    esperadas = [tabla for tabla in _tablas_esperadas(apu) if not tabla.empty]
    obtenidas = [tabla.value.reset_index(drop=True) for tabla in desplegable.dataframe]
    assert len(obtenidas) == len(esperadas)
    for obtenida, esperada in zip(obtenidas, esperadas, strict=True):
        assert obtenida.astype(str).to_dict("records") == esperada.to_dict("records")


def test_desplegar_una_propuesta_precarga_su_desglose_rendimiento_origen_y_puntaje(
    monkeypatch, base_sembrada
):
    """UC-03, pasos 3 y 4: cada propuesta desplegada trae el desglose de su partida de origen."""
    antes = huella(RUTA_BASE_REAL)
    at = _consultar(monkeypatch, base_sembrada)

    assert len(at.expander) == 2
    concreto = _desplegable(at, APU_CONCRETO.codigo_partida)
    excavacion = _desplegable(at, APU_EXCAVACION.codigo_partida)
    _comprobar_desglose(concreto, APU_CONCRETO, PUNTAJE_CONCRETO)
    _comprobar_desglose(excavacion, APU_EXCAVACION, PUNTAJE_EXCAVACION)
    assert not at.warning
    assert huella(RUTA_BASE_REAL) == antes


def test_un_insumo_sin_precio_vigente_senala_el_desglose_incompleto(monkeypatch, base_sembrada):
    """UC-03, flujo 4a: la propuesta cuyo desglose usa un insumo sin precio se senala nombrandolo
    y no muestra tablas; la otra propuesta, completa, muestra su desglose sin aviso."""
    _quitar_precio(base_sembrada, INSUMO_SIN_PRECIO)

    at = _consultar(monkeypatch, base_sembrada)

    concreto = _desplegable(at, APU_CONCRETO.codigo_partida)
    avisos = [aviso.value for aviso in concreto.warning]
    assert len(avisos) == 1, avisos
    assert avisos[0].startswith("Desglose incompleto en la lista vigente")
    assert INSUMO_SIN_PRECIO in avisos[0]
    assert APU_CONCRETO.codigo_partida in avisos[0]
    assert len(concreto.dataframe) == 0

    excavacion = _desplegable(at, APU_EXCAVACION.codigo_partida)
    assert len(excavacion.warning) == 0
    _comprobar_desglose(excavacion, APU_EXCAVACION, PUNTAJE_EXCAVACION)
