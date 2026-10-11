"""Lo compartido por los dos entornos de Alembic y sus revisiones (S5 §6.1; DA-S5-4, DA-S5-7)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import MetaData

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
