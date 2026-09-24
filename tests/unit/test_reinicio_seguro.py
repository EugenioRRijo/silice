"""INV-050: `--reiniciar` sobre la base por defecto se niega sin `--confirmar`.

`--reiniciar` hace `drop_all` sobre la base. Sobre la ruta por defecto (la base de trabajo) eso es
perdida de datos si se teclea por descuido, asi que ahi exige ademas `--confirmar`: sin el, `main`
devuelve 2, explica el motivo en `stderr` y no abre la base. Con `--db <otra ruta>` basta
`--reiniciar` (la preparacion del guion, `docs/guion_prueba_arenia.md`, no cambia).

**Estas pruebas ejecutan codigo destructivo** (antes del arreglo, `main(["--reiniciar"])` hace
`drop_all` sobre `RUTA_POR_DEFECTO`, que es relativa). Por eso cada caso, ANTES de llamar a `main`
(QA-9, Global Constraints del plan de C3):

1. `monkeypatch.chdir(tmp_path)`, para que ninguna ruta relativa alcance `data/` del repositorio;
2. parcha `RUTA_POR_DEFECTO` del modulo hacia `tmp_path/data/<nombre>`, donde siembra un centinela
   que es una base SQLite real (`crear_esquema` + `scripts.seed.sembrar`), y toma su huella;
3. afirma que la ruta parchada resuelve dentro de `tmp_path`; si no, la prueba se detiene sin haber
   llamado a `main`.
"""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import func, select

from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from scripts import seed

SEMBRADORES = (
    ("scripts.seed", "apu.db"),
    ("scripts.seed_demo", "apu.db"),
    ("scripts.seed_industrial", "apu_industrial.db"),
    ("scripts.seed_sistemas", "apu_sistemas.db"),
    ("scripts.seed_telecom", "apu_telecom.db"),
)
CON_CONFIRMAR = SEMBRADORES[:2]  # solo seed y seed_demo, por tiempo


def _huella(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _partidas(ruta: Path) -> int:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return sesion.scalar(select(func.count()).select_from(models.Partida))
    finally:
        motor.dispose()


def _centinela_en_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, nombre_modulo: str, nombre_base: str
) -> tuple[ModuleType, Path]:
    """Las tres precauciones, en orden, antes de que la prueba pueda llamar a `main`."""
    modulo = importlib.import_module(nombre_modulo)
    # 1. Ninguna ruta relativa sale de tmp_path.
    monkeypatch.chdir(tmp_path)
    # 2. La ruta por defecto apunta a un centinela sembrado dentro de tmp_path.
    centinela = tmp_path / "data" / nombre_base
    monkeypatch.setattr(modulo, "RUTA_POR_DEFECTO", str(centinela))
    centinela.parent.mkdir(parents=True)
    motor = crear_motor(f"sqlite:///{centinela.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            seed.sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    # 3. Si la ruta parchada no queda dentro de tmp_path, se detiene aqui, sin llamar a main.
    assert Path(modulo.RUTA_POR_DEFECTO).resolve().is_relative_to(tmp_path.resolve())
    return modulo, centinela


@pytest.mark.parametrize(("nombre_modulo", "nombre_base"), SEMBRADORES)
def test_reiniciar_la_base_por_defecto_sin_confirmar_se_niega(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    nombre_modulo: str,
    nombre_base: str,
) -> None:
    modulo, centinela = _centinela_en_tmp(monkeypatch, tmp_path, nombre_modulo, nombre_base)
    antes = _huella(centinela)

    codigo = modulo.main(["--reiniciar"])

    salida = capsys.readouterr()
    assert codigo == 2
    assert "--confirmar" in salida.err
    assert _huella(centinela) == antes


@pytest.mark.parametrize(("nombre_modulo", "nombre_base"), CON_CONFIRMAR)
def test_reiniciar_la_base_por_defecto_con_confirmar_procede(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    nombre_modulo: str,
    nombre_base: str,
) -> None:
    modulo, centinela = _centinela_en_tmp(monkeypatch, tmp_path, nombre_modulo, nombre_base)
    antes = _huella(centinela)

    codigo = modulo.main(["--reiniciar", "--confirmar"])

    assert codigo == 0
    assert _huella(centinela) != antes  # se reinicio
    assert _partidas(centinela) > 0  # y se volvio a sembrar


def test_reiniciar_otra_base_no_pide_confirmar(tmp_path: Path) -> None:
    otra = tmp_path / "prueba_arenia.db"
    assert seed.motivo_para_no_reiniciar(str(otra), True, False, "data/apu.db") is None


def test_sin_reiniciar_no_hay_motivo() -> None:
    assert seed.motivo_para_no_reiniciar("data/apu.db", False, False, "data/apu.db") is None
