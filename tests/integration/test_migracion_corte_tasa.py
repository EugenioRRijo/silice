"""`caso_0018_mp_corte_tasa`: el rastro de la conversión de un precio del corte (Tarea D2).

Oráculo, escrito a mano: a las diez columnas de `mp_precio_corte` (`caso_0017_mp_corte`) se suman
cinco que admiten nulo: `moneda_original String(10)`, `precio_original String(40)`,
`tasa String(40)`, `fecha_tasa Date` y `fuente_tasa String(300)`. Las filas que ya existían
quedan con ellas en nulo. Bajar quita las cinco columnas y deja las diez de siempre con sus datos.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

TABLA = "mp_precio_corte"
REVISION = "caso_0018_mp_corte_tasa"
ANTERIOR = "caso_0017_mp_corte"
NUEVAS = [
    ("moneda_original", "VARCHAR(10)", True),
    ("precio_original", "VARCHAR(40)", True),
    ("tasa", "VARCHAR(40)", True),
    ("fecha_tasa", "DATE", True),
    ("fuente_tasa", "VARCHAR(300)", True),
]
ANTIGUAS = [
    "id",
    "proyecto_id",
    "descripcion_insumo",
    "unidad",
    "precio",
    "moneda",
    "fecha",
    "fuente",
    "responsable",
    "fecha_hora",
]
FILA = (
    f"INSERT INTO {TABLA} (proyecto_id, descripcion_insumo, unidad, precio, moneda, fecha, fuente, "
    "responsable, fecha_hora) VALUES (1, 'Cemento gris', 'saco', '20.00', 'Bs', '2026-11-10', "
    "'cotización ficticia', 'Ana <ana>', '2026-11-10 09:00:00')"
)


def _columnas(ruta: Path) -> list[tuple[str, str, bool]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    return [(f[1], f[2], not f[3]) for f in filas]


def _instantanea(ruta: Path) -> dict:
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        with motor.connect() as conexion:
            return instantanea_esquema(conexion)[TABLA]
    finally:
        motor.dispose()


def test_cuelga_de_la_del_corte() -> None:
    from migraciones.caso.versions import caso_0018_mp_corte_tasa as revision

    assert revision.revision == REVISION
    assert revision.down_revision == ANTERIOR


def test_subir_agrega_las_cinco_columnas_con_nulo_y_deja_las_filas_viejas_en_nulo(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(FILA)
        conexion.commit()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    columnas = _columnas(ruta)
    assert [c[0] for c in columnas[:10]] == ANTIGUAS
    assert columnas[10:] == NUEVAS
    with closing(sqlite3.connect(ruta)) as conexion:
        fila = conexion.execute(
            f"SELECT precio, moneda_original, precio_original, tasa, fecha_tasa, fuente_tasa "
            f"FROM {TABLA}"
        ).fetchall()
    assert fila == [("20.00", None, None, None, None, None)]


def test_la_tabla_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    from aplicacion.tablas_corte import crear_esquema_corte

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(f"sqlite:///{creada.as_posix()}")
    try:
        crear_esquema_corte(motor)
    finally:
        motor.dispose()
    assert _instantanea(migrada) == _instantanea(creada)


def test_bajar_quita_solo_las_cinco_columnas_y_conserva_los_datos(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(FILA)
        conexion.execute(
            f"UPDATE {TABLA} SET moneda_original='Bs', precio_original='146.00', tasa='36.50', "
            "fecha_tasa='2026-11-10', fuente_tasa='importacion:1'"
        )
        conexion.commit()
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert leer_estado(ruta).revision == ANTERIOR
    assert [c[0] for c in _columnas(ruta)] == ANTIGUAS
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT precio, moneda FROM {TABLA}").fetchall() == [
            ("20.00", "Bs")
        ]
    aplicar_revisiones(ruta, Destino.CASO, REVISION)  # y se puede volver a subir
    assert [c[0] for c in _columnas(ruta)][10:] == [n for n, _, _ in NUEVAS]


def test_una_base_que_ya_trae_las_columnas_se_adopta_sin_agregarlas_otra_vez(
    tmp_path: Path,
) -> None:
    from aplicacion.tablas_corte import crear_esquema_corte

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, "caso_0016_mp_procura")
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema_corte(motor)  # la tabla ya con el esquema nuevo
    finally:
        motor.dispose()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert [c[0] for c in _columnas(ruta)][10:] == [n for n, _, _ in NUEVAS]
