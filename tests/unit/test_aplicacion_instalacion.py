"""Instalacion (`aplicacion/instalacion.py`): juegos de respaldo y su zip.

Movidas sin cambio de logica desde `tests/unit/test_ui_instalacion.py` (retiro de Streamlit, F3);
solo cambia el import (`ui.paginas.instalacion` reexportaba `juegos_de_respaldo` y `zip_del_juego`
de `aplicacion.instalacion`). Bases reales en `tmp_path`, sin datos reales (NORMAS.md §1).
"""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from aplicacion import instalacion
from operacion import config
from operacion.base_datos import Destino, preparar_base, respaldar_todo


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> tuple[Path, Path]:
    """La instalación y el caso migrados una vez por módulo; cada prueba copia los suyos (bases
    reales en `tmp_path`, sin pagar las migraciones en cada prueba)."""
    carpeta = tmp_path_factory.mktemp("plantillas")
    preparar_base(carpeta / "instalacion.db", Destino.INSTALACION)
    preparar_base(carpeta / "silice.db")
    return carpeta / "instalacion.db", carpeta / "silice.db"


@pytest.fixture
def bases(_plantillas: tuple[Path, Path]) -> None:
    for plantilla, destino in zip(
        _plantillas, (config.ruta_instalacion(), config.ruta_caso_por_defecto()), strict=True
    ):
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(plantilla, destino)


def test_los_juegos_van_del_mas_nuevo_al_mas_viejo_y_saltan_los_ilegibles(bases) -> None:
    carpeta = config.carpeta_respaldos()
    for nombre in ("20261010-100000-manual", "20261012-100000-manual"):
        (carpeta / nombre).mkdir(parents=True)
        (carpeta / nombre / "ficha.json").write_text(
            json.dumps({"motivo": "manual", "bases": [{}, {}, {}]}), encoding="utf-8"
        )
    (carpeta / "20261011-100000-roto").mkdir()
    (carpeta / "20261011-100000-roto" / "ficha.json").write_text("{no", encoding="utf-8")
    juegos = instalacion.juegos_de_respaldo()
    assert [(j.nombre, j.bases) for j in juegos] == [
        ("20261012-100000-manual", 3),
        ("20261010-100000-manual", 3),
    ]


def test_el_zip_del_juego_trae_las_bases_y_la_ficha(bases) -> None:
    carpeta = respaldar_todo()
    esperados = {p.relative_to(carpeta).as_posix() for p in carpeta.rglob("*") if p.is_file()}
    with zipfile.ZipFile(io.BytesIO(instalacion.zip_del_juego(carpeta))) as zip_:
        nombres = set(zip_.namelist())
        assert zip_.read("ficha.json") == (carpeta / "ficha.json").read_bytes()
    assert nombres == esperados
    assert "ficha.json" in nombres and "instalacion.db" in nombres
