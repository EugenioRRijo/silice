"""F5 vial, tarea 2: la migración `caso_0021_vial_transporte` (columna `transporte` de `vial_tramo`).

Oráculos a mano: la columna es aditiva y nullable (texto de 10), un tramo guardado antes de migrar
se lee con la convención de siempre (nula, t·km), bajar la quita sin tocar lo demás y una base que
ya la trae (creada con `crear_esquema_vial`) se adopta.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

REVISION = "caso_0021_vial_transporte"
ANTERIOR = "caso_0020_hoja_importaciones"
TABLA = "vial_tramo"


def _columnas(ruta: Path) -> list[tuple[str, str, bool]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    return [(f[1], f[2], not f[3]) for f in filas]


def test_la_cabeza_del_caso_es_esta_revision() -> None:
    from operacion.base_datos import _guion

    assert _guion(Destino.CASO).get_heads() == [REVISION]


def test_subir_agrega_la_columna_y_lo_guardado_antes_queda_en_t_km(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO vial_tramo (guardado_id, orden, tramo_id, progresiva_ini_km, "
            "progresiva_fin_km, ancho_m, capas, demarcacion) VALUES (1, 1, 'T1', '0', '1', '7', "
            "'[]', '[]')"
        )
        conexion.commit()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert _columnas(ruta)[-1] == ("transporte", "VARCHAR(10)", True)
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT transporte FROM vial_tramo").fetchall() == [(None,)]


def test_bajar_quita_solo_la_columna(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    antes = _columnas(ruta)
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert _columnas(ruta) == antes
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert "transporte" in {c[0] for c in _columnas(ruta)}


def test_una_base_que_ya_trae_la_columna_se_adopta(tmp_path: Path) -> None:
    from aplicacion.tablas_vial import crear_esquema_vial

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, "caso_0018_mp_corte_tasa")
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema_vial(motor)  # las tablas creadas al guardar los primeros tramos, sin migrar
    finally:
        motor.dispose()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert [c[0] for c in _columnas(ruta)].count("transporte") == 1
