"""Lo compartido por los dos entornos de Alembic y sus revisiones (S5 §6.1; DA-S5-4, DA-S5-7)."""

from __future__ import annotations

import functools
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, Inspector, MetaData, create_engine, inspect

TABLA_VERSION = "alembic_version"


class ErrorDeBase(ValueError):  # noqa: N818
    """Una base que Sílice no puede abrir; el mensaje dice qué pasó y qué hacer.

    Es un `ValueError`: las pantallas que ya muestran `ValueError` como mensaje (no como traza) la
    muestran igual. `operacion.base_datos` la reexporta junto con sus subclases.
    """


class BaseNoAdoptable(ErrorDeBase):  # noqa: N818
    """La base tiene tablas del esquema con otra forma: no se adopta ni se toca (spec S5 §6.4)."""

    def __init__(self, diferencias: Sequence[str]) -> None:
        self.diferencias = tuple(diferencias)
        super().__init__(
            "Esta base no se puede adoptar: sus tablas no tienen la forma que Sílice espera ("
            + "; ".join(self.diferencias)
            + "). No se modificó. Vuelva a sembrarla o pida ayuda (manual técnico §10.5)."
        )


def ejecutar_entorno(metadatas: Sequence[MetaData]) -> None:
    """Cuerpo de cada `env.py`: solo en línea, con la conexión que pone `operacion.base_datos` en
    `config.attributes["connection"]`; modo batch porque SQLite casi no tiene `ALTER` (§6.1)."""
    from alembic import context

    conexion = context.config.attributes.get("connection")
    if conexion is None:
        raise RuntimeError(
            "Las migraciones de Sílice corren solo desde operacion.base_datos, con una conexión "
            "abierta; la orden `alembic` no se usa (DA-S5-7)."
        )
    context.configure(
        connection=conexion,
        target_metadata=list(metadatas),
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


@dataclass(frozen=True, slots=True)
class TablaCongelada:
    """Una tabla tal como la creó la versión que congela la revisión: su DDL literal de SQLite."""

    nombre: str
    ddl: str
    indices: tuple[str, ...] = ()


def _tipo(tipo: Any) -> str:
    return " ".join(str(tipo).split()).upper()


def describir_tabla(inspector: Inspector, nombre: str) -> dict[str, Any]:
    """La forma reflejada de una tabla; las columnas, por nombre (su orden no importa)."""
    return {
        "columnas": sorted(
            (c["name"], _tipo(c["type"]), bool(c["nullable"]))
            for c in inspector.get_columns(nombre)
        ),
        "clave_primaria": tuple(inspector.get_pk_constraint(nombre)["constrained_columns"]),
        "indices": sorted(
            (i["name"], tuple(i["column_names"]), bool(i["unique"]))
            for i in inspector.get_indexes(nombre)
        ),
        "unicas": sorted(
            (u["name"] or "", tuple(u["column_names"]))
            for u in inspector.get_unique_constraints(nombre)
        ),
        "foraneas": sorted(
            (tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
            for f in inspector.get_foreign_keys(nombre)
        ),
        "checks": sorted(
            (c["name"] or "", " ".join(str(c["sqltext"]).split()))
            for c in inspector.get_check_constraints(nombre)
        ),
    }


def instantanea_esquema(conexion: Connection) -> dict[str, dict[str, Any]]:
    """Tablas, columnas, tipos, nulabilidad, clave primaria, índices, únicas, foráneas y `CHECK`
    de la base, sin `alembic_version` (RNF-20)."""
    inspector = inspect(conexion)
    return {
        nombre: describir_tabla(inspector, nombre)
        for nombre in sorted(inspector.get_table_names())
        if nombre != TABLA_VERSION
    }


@functools.cache
def _referencia(tablas: tuple[TablaCongelada, ...]) -> dict[str, dict[str, Any]]:
    """La forma de las tablas congeladas, reflejada de una base en memoria creada con su DDL."""
    motor = create_engine("sqlite://")
    try:
        with motor.begin() as conexion:
            for tabla in tablas:
                conexion.exec_driver_sql(tabla.ddl)
                for indice in tabla.indices:
                    conexion.exec_driver_sql(indice)
            return instantanea_esquema(conexion)
    finally:
        motor.dispose()


def _comparar(nombre: str, esperado: dict[str, Any], hallado: dict[str, Any]) -> list[str]:
    esperadas = {columna[0]: columna for columna in esperado["columnas"]}
    halladas = {columna[0]: columna for columna in hallado["columnas"]}
    diferencias = [
        f"{nombre}: falta la columna {c}" for c in sorted(esperadas.keys() - halladas.keys())
    ]
    diferencias += [
        f"{nombre}: sobra la columna {c}" for c in sorted(halladas.keys() - esperadas.keys())
    ]
    diferencias += [
        f"{nombre}.{c}: se esperaba {esperadas[c][1:]} y hay {halladas[c][1:]}"
        for c in sorted(esperadas.keys() & halladas.keys())
        if esperadas[c] != halladas[c]
    ]
    diferencias += [
        f"{nombre}: {clave} distintos"
        for clave in ("clave_primaria", "indices", "unicas", "foraneas", "checks")
        if esperado[clave] != hallado[clave]
    ]
    return diferencias


def crear_o_verificar(conexion: Connection, tablas: Sequence[TablaCongelada]) -> None:
    """Crea las tablas que faltan y verifica las existentes contra su definición congelada
    (DA-S5-4). Verifica TODAS antes de crear ninguna: una base no adoptable no gana tablas."""
    referencia = _referencia(tuple(tablas))
    inspector = inspect(conexion)
    existentes = set(inspector.get_table_names())
    diferencias: list[str] = []
    for tabla in tablas:
        if tabla.nombre in existentes:
            hallado = describir_tabla(inspector, tabla.nombre)
            diferencias += _comparar(tabla.nombre, referencia[tabla.nombre], hallado)
    if diferencias:
        raise BaseNoAdoptable(diferencias)
    for tabla in tablas:
        if tabla.nombre not in existentes:
            conexion.exec_driver_sql(tabla.ddl)
            for indice in tabla.indices:
                conexion.exec_driver_sql(indice)


def borrar_tablas(conexion: Connection, tablas: Sequence[TablaCongelada]) -> None:
    """`downgrade` de una revisión que solo crea tablas: las borra en orden inverso."""
    existentes = set(inspect(conexion).get_table_names())
    for tabla in reversed(tablas):
        if tabla.nombre in existentes:
            conexion.exec_driver_sql(f'DROP TABLE "{tabla.nombre}"')


def metadata_unida(metadatas: Sequence[MetaData]) -> MetaData:
    """Una sola `MetaData` con las tablas de varias, para `compare_metadata` (RNF-20)."""
    unida = MetaData()
    for metadata in metadatas:
        for tabla in metadata.sorted_tables:
            tabla.to_metadata(unida)
    return unida
