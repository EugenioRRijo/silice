"""Mejora de A.6 (acta DS-48g, opción A): la migración `caso_0024_desperdicio_responsable`.

`apu_desperdicio_guardado` gana la columna `responsable`: quién guardó el desglose del desperdicio
(`Nombre <login>`, el texto del responsable de RF-82, hasta 120). Oráculos a mano: la columna es
aditiva y admite nulos (un guardado de antes de migrar no sabe quién lo hizo: queda nulo y la Hoja
dice «sin dato»), bajar la quita sin tocar lo demás ni las filas, una base que ya la trae (creada
con `crear_esquema_desperdicio`, al guardar la primera traza sin migrar) se adopta y la migrada es
la del modelo.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

REVISION = "caso_0024_desperdicio_responsable"
#: La revisión de la que cuelga (la misma constante que `down_revision` en la migración). Si al unir
#: otra rama entra una revisión antes (`caso_0023_riesgo_mapa`), se cambia aquí y allí.
ANTERIOR = "caso_0023_riesgo_mapa"
TABLA = "apu_desperdicio_guardado"


def _columnas(ruta: Path) -> list[tuple[str, str, bool]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    return [(f[1], f[2], not f[3]) for f in filas]


def _filas(ruta: Path) -> list[tuple]:
    with closing(sqlite3.connect(ruta)) as conexion:
        return conexion.execute(
            f"SELECT id, partida_codigo, fecha_hora FROM {TABLA} ORDER BY id"
        ).fetchall()


def _con_un_guardado(ruta: Path) -> None:
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            f"INSERT INTO {TABLA} (partida_codigo, fecha_hora) VALUES "
            "('AF-LLAVE', '2026-11-13 09:00:00.000000')"
        )
        conexion.commit()


def test_la_revision_esta_en_la_unica_linea_del_caso() -> None:
    """Fue la cabeza hasta `caso_0025_entrega_de_obra` (Lote G5), que cuelga de ella."""
    from operacion.base_datos import _guion

    guion = _guion(Destino.CASO)
    assert len(guion.get_heads()) == 1
    assert guion.get_revision(REVISION).down_revision == ANTERIOR


def test_subir_agrega_la_columna_y_lo_guardado_antes_queda_sin_responsable(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    _con_un_guardado(ruta)
    antes = _filas(ruta)
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert _columnas(ruta)[-1] == ("responsable", "VARCHAR(120)", True)
    assert _filas(ruta) == antes
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT responsable FROM {TABLA}").fetchall() == [(None,)]


def test_bajar_quita_solo_la_columna_y_conserva_las_filas(tmp_path: Path) -> None:
    """Bajar deja el esquema completo de la base (tablas, columnas e índices) como estaba antes
    de subir, con las filas, también la de un guardado con responsable (revisión de Neon, 5)."""
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    columnas_antes = _columnas(ruta)
    esquema_antes = _instantanea(ruta)
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    _con_un_guardado(ruta)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            f"INSERT INTO {TABLA} (partida_codigo, fecha_hora, responsable) VALUES "
            "('AF-TUB', '2026-11-20 10:00:00.000000', 'Ana <ana>')"
        )
        conexion.commit()
    filas = _filas(ruta)
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert leer_estado(ruta).revision == ANTERIOR
    assert _columnas(ruta) == columnas_antes
    assert _instantanea(ruta) == esquema_antes
    assert _filas(ruta) == filas
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert "responsable" in {c[0] for c in _columnas(ruta)}


def test_una_base_que_ya_trae_la_columna_se_adopta(tmp_path: Path) -> None:
    from aplicacion.tablas_desperdicio import crear_esquema_desperdicio

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, "caso_0021_vial_transporte")
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema_desperdicio(motor)  # el primer guardado en una base sin migrar
    finally:
        motor.dispose()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert [c[0] for c in _columnas(ruta)].count("responsable") == 1


def _instantanea(ruta: Path) -> dict:
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        with motor.connect() as conexion:
            return instantanea_esquema(conexion)
    finally:
        motor.dispose()


def test_la_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    from aplicacion.tablas_desperdicio import crear_esquema_desperdicio

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(f"sqlite:///{creada.as_posix()}")
    try:
        crear_esquema_desperdicio(motor)
    finally:
        motor.dispose()
    assert _instantanea(migrada)[TABLA] == _instantanea(creada)[TABLA]
