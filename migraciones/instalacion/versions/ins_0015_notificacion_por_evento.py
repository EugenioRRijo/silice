"""C11b (2026-11-26): notificaciones por evento y qué recibir, en `instalacion.db`.

- `notificacion.clave_evento` (255, nula): la clave del evento que creó la notificación en el
  servidor (por ejemplo `aprobacion:vivienda.db:3:VIV-002:enviada`), con el índice único
  `ux_notificacion_usuario_clave (usuario_id, clave_evento)`: un mismo evento no se repite para una
  persona. Las notificaciones del front van sin clave (SQLite admite varias nulas en un índice
  único), así que las filas de `ins_0014` quedan como estaban.
- `preferencia_notificacion (usuario_id, categoria, activa)`: lo que cada persona apagó o volvió a
  encender. Sin fila, la categoría está encendida. Clave primaria compuesta y FK a `usuario.id`.

Aditiva: una base que ya trae la columna, el índice o la tabla (creada con `create_all`) se adopta
sin duplicarlos. Al bajar se borran la tabla, el índice y la columna (DA-S5-6: la bajada nunca se
ofrece al usuario). El respaldo previo lo hace `operacion.base_datos` antes de cualquier revisión.

`down_revision` es `ins_0014_notificacion`, la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0015_notificacion_por_evento"
down_revision = "ins_0014_notificacion"
branch_labels = None
depends_on = None

NOTIFICACION = "notificacion"
COLUMNA = "clave_evento"
INDICE = "ux_notificacion_usuario_clave"
PREFERENCIA = "preferencia_notificacion"


def _inspector() -> sa.engine.reflection.Inspector:
    return sa.inspect(op.get_bind())


def _columnas() -> set[str]:
    return {c["name"] for c in _inspector().get_columns(NOTIFICACION)}


def _indices() -> set[str]:
    return {i["name"] for i in _inspector().get_indexes(NOTIFICACION) if i.get("name")}


def upgrade() -> None:
    if COLUMNA not in _columnas():
        op.add_column(NOTIFICACION, sa.Column(COLUMNA, sa.String(255), nullable=True))
    if INDICE not in _indices():
        op.create_index(INDICE, NOTIFICACION, ["usuario_id", COLUMNA], unique=True)
    if PREFERENCIA not in _inspector().get_table_names():
        op.create_table(
            PREFERENCIA,
            sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuario.id"), nullable=False),
            sa.Column("categoria", sa.String(40), nullable=False),
            sa.Column("activa", sa.Boolean, nullable=False),
            sa.PrimaryKeyConstraint("usuario_id", "categoria"),
        )


def downgrade() -> None:
    if PREFERENCIA in _inspector().get_table_names():
        op.drop_table(PREFERENCIA)
    if INDICE in _indices():
        op.drop_index(INDICE, table_name=NOTIFICACION)
    if COLUMNA in _columnas():
        # SQLite 3.35+ quita la columna sin recrear la tabla: el `CHECK` de la gravedad, la FK y
        # el índice `(usuario_id, creada)` quedan tal cual los dejó `ins_0014`.
        op.execute(f"ALTER TABLE {NOTIFICACION} DROP COLUMN {COLUMNA}")
