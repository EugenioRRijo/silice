"""Dos estados de una `instalacion.db` para probar lo que se pierde al restaurar (SEG-12).

Instalaciones mínimas, solo con las columnas que las pruebas necesitan; no dependen de las
migraciones de S3. Datos construidos (NORMAS.md §1): logins, huellas y nombres son ficticios.

Diferencia con el plan: `evento_acceso` lleva `fecha_hora`, que `operacion.respaldo` lee para
anotar en la ficha del juego el último evento (`_ultimo_evento`); sin ella, respaldar falla.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

ESQUEMA = """
CREATE TABLE usuario (id INTEGER PRIMARY KEY, login TEXT, activo INTEGER, roles TEXT,
                      huella_clave TEXT);
CREATE TABLE clave_empresa (id INTEGER PRIMARY KEY, huella TEXT, estado TEXT, privada_cifrada BLOB);
CREATE TABLE empresa_registrada (id INTEGER PRIMARY KEY, huella TEXT, estado TEXT);
CREATE TABLE clave_api (id INTEGER PRIMARY KEY, nombre TEXT, revocada INTEGER, huella_secreto TEXT);
CREATE TABLE evento_acceso (id INTEGER PRIMARY KEY, tipo TEXT, fecha_hora TEXT);
"""

COLUMNAS = {
    "usuario": "id, login, activo, roles, huella_clave",
    "clave_empresa": "id, huella, estado, privada_cifrada",
    "empresa_registrada": "id, huella, estado",
    "clave_api": "id, nombre, revocada, huella_secreto",
    "evento_acceso": "id, tipo, fecha_hora",
}


def base(ruta: Path, filas: dict[str, list[tuple]]) -> Path:
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.executescript(ESQUEMA)
        for tabla, registros in filas.items():
            marcas = ", ".join("?" * len(registros[0]))
            conexion.executemany(
                f"INSERT INTO {tabla} ({COLUMNAS[tabla]}) VALUES ({marcas})", registros
            )
        conexion.commit()
    return ruta


#: La instalación tal como quedó en el juego de respaldo.
COPIA = {
    "usuario": [(1, "ana", 1, "arma", "ARGON-A"), (2, "beto", 1, "arma,revisa", "ARGON-B")],
    "clave_empresa": [(1, "AAAA", "activa", b"cifrada")],
    "empresa_registrada": [(1, "BBBB", "activa")],
    "clave_api": [(1, "plugin", 0, "SHA-1")],
    "evento_acceso": [(1, "entrada", "2026-10-10 09:00:00")],
}
#: La instalación después del juego: desactivó a ana, quitó un rol a beto, creó a carla, revocó
#: las dos claves de firma y la de API, creó otra clave de API y registró una revocación.
ACTUAL = {
    "usuario": [
        (1, "ana", 0, "arma", "ARGON-A"),
        (2, "beto", 1, "revisa", "ARGON-B"),
        (3, "carla", 1, "arma", "ARGON-C"),
    ],
    "clave_empresa": [(1, "AAAA", "revocada", None)],
    "empresa_registrada": [(1, "BBBB", "revocada")],
    "clave_api": [(1, "plugin", 1, "SHA-1"), (2, "nuevo", 0, "SHA-2")],
    "evento_acceso": [(1, "entrada", "2026-10-10 09:00:00"), (2, "revocacion", "2026-10-11 10:00")],
}
