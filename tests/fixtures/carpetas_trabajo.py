"""Bases y árboles para las pruebas de las carpetas de trabajo (BCP-2; diseño §4, §10.2 y §10.3).

Lo comparten `tests/unit/test_aplicacion_casos.py` y `tests/unit/test_api_casos_*.py` (INV-052: lo
compartido entre pruebas vive en `tests/fixtures/`). Todo es ficticio: las bases se crean aquí
mismo con `sqlite3` o con `preparar_base`, o se copian de las bases de prueba de cada versión
(`tests/fixtures/bases`).

Oráculos escritos a mano, ninguno sale de `aplicacion/casos.py`:

- `arbol` describe una carpeta (ruta relativa -> tamaño, `-1` para una carpeta) con `os.walk`; dos
  árboles iguales dicen que nada se creó, borró ni cambió de tamaño.
- `HOSTILES` son los archivos que una subida debe rechazar (B15), cada uno construido a mano.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from operacion.base_datos import preparar_base

CABECERA = b"SQLite format 3\x00"  # los 16 bytes de la firma de SQLite, copiados del formato


def arbol(carpeta: Path) -> dict[str, int]:
    """Cada archivo y carpeta bajo `carpeta` con su tamaño (`-1` las carpetas)."""
    vista: dict[str, int] = {}
    if not carpeta.exists():
        return vista
    for raiz, carpetas, archivos in os.walk(carpeta):
        for nombre in carpetas:
            vista[(Path(raiz) / nombre).relative_to(carpeta).as_posix()] = -1
        for nombre in archivos:
            ruta = Path(raiz) / nombre
            vista[ruta.relative_to(carpeta).as_posix()] = ruta.stat().st_size
    return vista


def base_minima(destino: Path) -> Path:
    """Un caso vacío en `head`, creado por el camino real (`preparar_base`)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(destino)
    return destino


def copiar(origen: Path, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origen, destino)
    return destino


def _ejecutar(ruta: Path, *sentencias: str) -> Path:
    with closing(sqlite3.connect(ruta)) as conexion:
        for sentencia in sentencias:
            conexion.execute(sentencia)
        conexion.commit()
    return ruta


def _texto(ruta: Path, _minima: Path) -> Path:
    ruta.write_bytes(b"Esto es una nota, no una base de datos.\n" * 10)
    return ruta


def _cabecera_falsa(ruta: Path, _minima: Path) -> Path:
    ruta.write_bytes(CABECERA + bytes(range(256)) * 32)
    return ruta


def _otra_aplicacion(ruta: Path, _minima: Path) -> Path:
    """Una base SQLite de otro programa (el historial de un navegador)."""
    return _ejecutar(
        ruta,
        "CREATE TABLE moz_places (id INTEGER PRIMARY KEY, url TEXT)",
        "INSERT INTO moz_places (url) VALUES ('http://ejemplo.invalid/')",
    )


def _con_disparador(ruta: Path, minima: Path) -> Path:
    return _ejecutar(
        copiar(minima, ruta),
        "CREATE TRIGGER t_partida AFTER INSERT ON partida BEGIN DELETE FROM insumo; END",
    )


def _con_vista(ruta: Path, minima: Path) -> Path:
    return _ejecutar(copiar(minima, ruta), "CREATE VIEW v_partida AS SELECT * FROM partida")


def _con_tabla_virtual(ruta: Path, minima: Path) -> Path:
    return _ejecutar(copiar(minima, ruta), "CREATE VIRTUAL TABLE buscar USING fts5(texto)")


def _con_tabla_virtual_en_minusculas(ruta: Path, minima: Path) -> Path:
    return _ejecutar(
        copiar(minima, ruta), "create   virtual\ttable   rtree_x using rtree(id, a, b)"
    )


def _integridad_rota(ruta: Path, minima: Path) -> Path:
    """Bytes del medio de cada página (salvo la primera) sobrescritos: la base abre, pero sus
    árboles están rotos."""
    datos = bytearray(minima.read_bytes())
    pagina = int.from_bytes(datos[16:18], "big")
    for numero in range(1, len(datos) // pagina):
        inicio = numero * pagina + pagina // 2
        datos[inicio : inicio + 64] = b"\xff" * 64
    ruta.write_bytes(bytes(datos))
    return ruta


def _revision_desconocida(ruta: Path, minima: Path) -> Path:
    return _ejecutar(copiar(minima, ruta), "UPDATE alembic_version SET version_num = 'zzz'")


def _sin_tablas(ruta: Path, _minima: Path) -> Path:
    """SQLite válido y vacío: ni `alembic_version` ni tablas de Sílice."""
    return _ejecutar(ruta, "PRAGMA user_version = 7")


def _instalacion(ruta: Path, _minima: Path) -> Path:
    """La base de la INSTALACIÓN (cuentas), no un caso: su revisión es de otro destino."""
    return _ejecutar(
        ruta,
        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)",
        "INSERT INTO alembic_version VALUES ('ins_0001_seguridad')",
        "CREATE TABLE usuario (id INTEGER PRIMARY KEY, login TEXT)",
    )


#: Nombre -> constructor `(ruta, base_minima) -> ruta` de un archivo que la subida rechaza.
HOSTILES: dict[str, Callable[[Path, Path], Path]] = {
    "texto": _texto,
    "cabecera_falsa": _cabecera_falsa,
    "otra_aplicacion": _otra_aplicacion,
    "disparador": _con_disparador,
    "vista": _con_vista,
    "tabla_virtual": _con_tabla_virtual,
    "tabla_virtual_minusculas": _con_tabla_virtual_en_minusculas,
    "integridad_rota": _integridad_rota,
    "revision_desconocida": _revision_desconocida,
    "sin_tablas": _sin_tablas,
    "instalacion": _instalacion,
}
