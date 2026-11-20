"""El mapa de series que «Riesgo de la obra» recuerda por versión (mejora de la DS-81; DS-90 a
DS-93). Datos FICTICIOS (`tests/fixtures/riesgo_obra.py`: la obra «Vía Ficticia Riesgo», en USD,
con VR-001 y VR-002 y los insumos «Cemento asfáltico», «Gasoil» y «Señalización»).

Oráculos a mano:
- guardar y leer da lo mismo; guardar otra vez manda el último; guardar lo mismo que ya era el último
  de la versión no agrega un guardado (devuelve False);
- una versión sin mapa propio toma el último guardado de otra versión de la misma obra, y dice de
  cuál; con mapa propio (aunque esté vacío) manda el suyo;
- precargar deja fuera, y lo dice, el insumo que la versión ya no tiene y la serie que ya no se
  ofrece;
- una serie que la moneda no admite (la tasa en una obra en USD) no se guarda (ValueError);
- una base sin las tablas se lee como sin mapa.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from aplicacion.riesgo import mapa_guardado as mg
from aplicacion.riesgo import obra
from aplicacion.riesgo.proyeccion import SERIE_TASA
from aplicacion.tablas_riesgo import GuardadoDeMapa
from aplicacion.vial import VersionInexistente, version_de
from core import models
from core.catalog import abrir_sesion, crear_motor
from tests.fixtures import costo_propio as cp
from tests.fixtures.riesgo_obra import (
    ARCHIVO,
    ASFALTO,
    CON_LINEA_BASE,
    GASOIL,
    MAPA,
    OBRA,
    SENALES,
    SIN_LINEA_BASE,
    crear_via,
)

AHORA = datetime(2026, 11, 20, 9, 0)
LUEGO = datetime(2026, 11, 20, 10, 0)
PPI = MAPA[ASFALTO]
GASOIL_USD = MAPA[GASOIL]


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return crear_via(tmp_path_factory.mktemp("mapa_riesgo") / ARCHIVO)


@pytest.fixture
def caso(_plantilla: Path, tmp_path: Path) -> Iterator[Session]:
    ruta = tmp_path / ARCHIVO
    ruta.write_bytes(_plantilla.read_bytes())
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            yield sesion
    finally:
        motor.dispose()


def _guardar(caso: Session, version: str, mapa: dict[str, str], ahora: datetime = AHORA) -> bool:
    return obra.guardar_mapa_de_la_obra(caso, OBRA, version, mapa, usuario="Ana <ana>", ahora=ahora)


def _guardados(caso: Session) -> int:
    return caso.scalar(select(func.count()).select_from(GuardadoDeMapa))


def test_lo_guardado_se_lee_igual(caso: Session) -> None:
    assert _guardar(caso, CON_LINEA_BASE, MAPA) is True
    leido = mg.ultimo_mapa(caso, version_de(caso, OBRA, CON_LINEA_BASE))
    assert leido is not None
    assert leido.mapa == MAPA
    assert leido.version == CON_LINEA_BASE
    assert leido.usuario == "Ana <ana>"
    assert leido.fecha_hora == AHORA


def test_guardar_otra_vez_manda_el_ultimo_y_el_anterior_queda(caso: Session) -> None:
    _guardar(caso, CON_LINEA_BASE, MAPA)
    _guardar(caso, CON_LINEA_BASE, {GASOIL: GASOIL_USD}, LUEGO)
    leido = mg.ultimo_mapa(caso, version_de(caso, OBRA, CON_LINEA_BASE))
    assert leido is not None and leido.mapa == {GASOIL: GASOIL_USD}
    assert _guardados(caso) == 2


def test_guardar_lo_mismo_no_agrega_un_guardado(caso: Session) -> None:
    assert _guardar(caso, CON_LINEA_BASE, MAPA) is True
    assert _guardar(caso, CON_LINEA_BASE, dict(reversed(MAPA.items())), LUEGO) is False
    assert _guardados(caso) == 1


def test_la_version_sin_mapa_toma_el_ultimo_de_la_obra(caso: Session) -> None:
    _guardar(caso, CON_LINEA_BASE, MAPA)
    leido = mg.ultimo_mapa(caso, version_de(caso, OBRA, SIN_LINEA_BASE))
    assert leido is not None
    assert leido.mapa == MAPA
    assert leido.version == CON_LINEA_BASE


def test_con_mapa_propio_vacio_manda_el_suyo(caso: Session) -> None:
    _guardar(caso, CON_LINEA_BASE, MAPA)
    _guardar(caso, SIN_LINEA_BASE, {}, LUEGO)
    leido = mg.ultimo_mapa(caso, version_de(caso, OBRA, SIN_LINEA_BASE))
    assert leido is not None and leido.mapa == {} and leido.version == SIN_LINEA_BASE
    # y la otra versión sigue con el suyo
    otra = mg.ultimo_mapa(caso, version_de(caso, OBRA, CON_LINEA_BASE))
    assert otra is not None and otra.mapa == MAPA


def test_sin_nada_guardado_no_hay_mapa(caso: Session) -> None:
    assert mg.ultimo_mapa(caso, version_de(caso, OBRA, CON_LINEA_BASE)) is None


def test_precargar_deja_fuera_y_dice_lo_que_ya_no_vale() -> None:
    guardado = mg.MapaGuardado(
        mapa={ASFALTO: PPI, "Asfalto retirado": PPI, GASOIL: "SERIE_RETIRADA"},
        version=CON_LINEA_BASE,
        usuario="Ana <ana>",
        fecha_hora=AHORA,
    )
    precarga = mg.precargar(guardado, [ASFALTO, GASOIL, SENALES], [PPI, GASOIL_USD])
    assert precarga.mapa == {ASFALTO: PPI}
    assert precarga.de_version == CON_LINEA_BASE
    assert precarga.descartados == (
        mg.Descartado("Asfalto retirado", PPI, mg.SIN_INSUMO),
        mg.Descartado(GASOIL, "SERIE_RETIRADA", mg.SIN_SERIE),
    )


def test_la_serie_que_la_moneda_no_admite_no_se_guarda(caso: Session) -> None:
    with pytest.raises(ValueError, match="no se ofrece"):
        _guardar(caso, CON_LINEA_BASE, {ASFALTO: SERIE_TASA})
    assert _guardados(caso) == 0


def test_la_version_que_no_existe_no_se_guarda(caso: Session) -> None:
    with pytest.raises(VersionInexistente):
        _guardar(caso, "VR-999", MAPA)


def test_los_insumos_de_la_obra_traen_la_precarga(caso: Session) -> None:
    _guardar(caso, CON_LINEA_BASE, {**MAPA, "Insumo que no está": GASOIL_USD})
    with cp.instalacion_en_memoria() as ins:
        datos = obra.insumos_de_la_obra(caso, ins, OBRA, SIN_LINEA_BASE)
    assert datos.mapa_guardado is not None
    assert datos.mapa_guardado.mapa == MAPA
    assert datos.mapa_guardado.de_version == CON_LINEA_BASE
    assert datos.mapa_guardado.descartados == (
        mg.Descartado("Insumo que no está", GASOIL_USD, mg.SIN_INSUMO),
    )


def test_una_base_sin_las_tablas_se_lee_como_sin_mapa(tmp_path: Path) -> None:
    motor = create_engine(f"sqlite:///{(tmp_path / 'sin.db').as_posix()}")
    try:
        models.Base.metadata.create_all(motor)
        with Session(motor) as sesion:
            assert mg.ultimo_mapa(sesion, 1) is None
    finally:
        motor.dispose()
