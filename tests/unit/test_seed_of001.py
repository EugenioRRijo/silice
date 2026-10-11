"""`scripts/seed_of001.py`: la base propia de CP-08 a CP-11 del guion (`data/prueba_sf.db`).

La siembra nunca escribe en `data/apu.db` (la base de trabajo de la aplicacion) y deja la oficina
OF-001 lista para abrirla en la hoja: su proyecto, la version `001` con su espacio y 2 703,86 USD.
Todo ocurre en archivos temporales.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from core.catalog import Catalogo, abrir_sesion, crear_motor
from scripts import seed_of001
from scripts.seed import RUTA_POR_DEFECTO as RUTA_APU
from tests.fixtures.hoja_en_base import NOMBRE_OF001
from ui import hoja


def test_la_ruta_por_defecto_es_la_base_propia_de_la_prueba_y_no_la_de_trabajo():
    assert seed_of001.RUTA_POR_DEFECTO == "data/prueba_sf.db"
    assert Path(seed_of001.RUTA_POR_DEFECTO).resolve() != Path(RUTA_APU).resolve()


def test_sembrar_deja_el_proyecto_of001_con_su_version_001_y_el_total_de_la_memoria(tmp_path):
    ruta = tmp_path / "prueba_sf.db"
    assert seed_of001.main(["--db", str(ruta)]) == 0

    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            abierta = hoja.abrir_version(sesion, Catalogo(sesion), NOMBRE_OF001, "001")
    finally:
        motor.dispose()
    assert abs(abierta.guardada.presupuesto.total - Decimal("2703.86")) <= Decimal("0.01")
    assert len(abierta.borrador.espacio.ambientes) == 6


def test_el_resumen_impreso_dice_el_total_y_la_auditoria(tmp_path, capsys):
    seed_of001.main(["--db", str(tmp_path / "prueba_sf.db")])
    salida = capsys.readouterr().out
    assert NOMBRE_OF001 in salida
    assert "Total: 2703.86 USD" in salida
    assert "Auditoria: 33 hallazgo(s), CUMPLE" in salida


def test_sembrar_sobre_una_base_que_existe_exige_reiniciar(tmp_path, capsys):
    ruta = tmp_path / "prueba_sf.db"
    assert seed_of001.main(["--db", str(ruta)]) == 0
    assert seed_of001.main(["--db", str(ruta)]) == 2  # no pisa en silencio
    assert "--reiniciar" in capsys.readouterr().err
    assert seed_of001.main(["--db", str(ruta), "--reiniciar"]) == 0  # cada repeticion parte igual


def _base_centinela(monkeypatch, tmp_path) -> tuple[Path, bytes]:
    """Una `data/apu.db` falsa en una carpeta temporal que pasa a ser el cwd: si el guardia falla,
    el que se pisa es este archivo y no la base real del desarrollador."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    centinela = tmp_path / "data" / "apu.db"
    centinela.write_bytes(b"CENTINELA-NO-TOCAR")
    return centinela, b"CENTINELA-NO-TOCAR"


def test_nunca_siembra_sobre_la_base_de_trabajo(capsys, monkeypatch, tmp_path):
    centinela, contenido = _base_centinela(monkeypatch, tmp_path)
    assert seed_of001.main(["--db", RUTA_APU, "--reiniciar", "--confirmar"]) == 2
    assert "data/apu.db" in capsys.readouterr().err.replace("\\", "/")
    assert centinela.exists()
    assert centinela.read_bytes() == contenido


@pytest.mark.parametrize("ruta", ["data/../data/apu.db", "./data/apu.db"])
def test_tampoco_con_rutas_equivalentes_a_la_de_trabajo(ruta, monkeypatch, tmp_path):
    centinela, contenido = _base_centinela(monkeypatch, tmp_path)
    assert seed_of001.main(["--db", ruta]) == 2
    assert seed_of001.main(["--db", ruta, "--reiniciar", "--confirmar"]) == 2
    assert centinela.exists()
    assert centinela.read_bytes() == contenido
