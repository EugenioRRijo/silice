"""`--reiniciar-demo` no puede revivir los datos de antes (re-verificación en vivo, 2026-11-18).

`_sembrar_copia` y `sembrar_obra_control` publicaban la base nueva con `os.replace`, pero dejaban el
`<destino>-wal` y el `-shm` de la corrida anterior (quedan si el servidor se cerró sin checkpoint).
Al abrir la base, SQLite reaplicaba ese WAL viejo sobre la nueva: la demo «resembrada» traía los
datos de antes, con riesgo de corrupción. La prueba arma un WAL viejo de verdad (una tabla con
filas que nunca pasó a la base) y comprueba que, tras sembrar, no queda y la base no la tiene.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import date
from pathlib import Path

import start

SUFIJOS = ("-wal", "-shm", "-journal")


def _con_wal_viejo(destino: Path) -> None:
    """Deja en `destino` una base WAL y, al lado, el `-wal`/`-shm` de una escritura que nunca se
    llevó a la base: la tabla `viejo` con dos filas, como tras un cierre sin checkpoint."""
    conexion = sqlite3.connect(destino)
    conexion.execute("PRAGMA journal_mode=WAL")
    conexion.execute("PRAGMA wal_autocheckpoint=0")
    conexion.execute("CREATE TABLE base_vieja (x INTEGER)")
    conexion.commit()
    conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conexion.execute("CREATE TABLE viejo (dato TEXT)")
    conexion.executemany("INSERT INTO viejo VALUES (?)", [("antes 1",), ("antes 2",)])
    conexion.commit()
    copias = {}
    for sufijo in ("-wal", "-shm"):
        archivo = destino.with_name(destino.name + sufijo)
        copias[sufijo] = archivo.read_bytes()
    conexion.close()  # el cierre limpio vacía el WAL: se restituye el de antes del cierre
    for sufijo, contenido in copias.items():
        destino.with_name(destino.name + sufijo).write_bytes(contenido)
    assert len(copias["-wal"]) > 0


def _restos(destino: Path) -> list[str]:
    return [s for s in SUFIJOS if destino.with_name(destino.name + s).exists()]


def _tablas(destino: Path) -> set[str]:
    conexion = sqlite3.connect(destino)
    try:
        return {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master")}
    finally:
        conexion.close()


def test_resembrar_la_obra_de_control_borra_el_wal_viejo(tmp_path: Path) -> None:
    destino = tmp_path / "obra_control.db"
    _con_wal_viejo(destino)
    assert "viejo" in _tablas_sin_tocar(destino, tmp_path)  # el WAL viejo revive la tabla
    start.sembrar_obra_control(destino, hoy=date(2026, 11, 18))
    assert _restos(destino) == []
    assert "viejo" not in _tablas(destino) and "base_vieja" not in _tablas(destino)


def test_resembrar_un_caso_copiado_borra_el_wal_viejo(tmp_path: Path) -> None:
    origen = start.BASES_PRUEBA / f"{start.CASOS_COPIADOS[0]}.db"
    assert origen.exists(), f"falta la base versionada {origen}"
    destino = tmp_path / origen.name
    _con_wal_viejo(destino)
    assert "viejo" in _tablas_sin_tocar(destino, tmp_path)  # el WAL viejo revive la tabla
    start._sembrar_copia(origen, destino)
    assert _restos(destino) == []
    assert "viejo" not in _tablas(destino) and "base_vieja" not in _tablas(destino)


def _tablas_sin_tocar(destino: Path, carpeta: Path) -> set[str]:
    """Las tablas que vería quien abre `destino` con su WAL, sobre una copia."""
    copia = carpeta / "control" / destino.name
    copia.parent.mkdir()
    for sufijo in ("", "-wal", "-shm"):
        shutil.copyfile(
            destino.with_name(destino.name + sufijo), copia.with_name(copia.name + sufijo)
        )
    return _tablas(copia)
