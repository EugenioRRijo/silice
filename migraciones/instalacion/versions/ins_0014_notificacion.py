"""C11 (2026-11-26): tabla `notificacion` en `instalacion.db`, retención de 30 días por persona.

Cada cuenta guarda sus propias notificaciones (gravedad, título, detalle, enlace interno opcional,
fecha de creación y marca de lectura) con clave foránea a `usuario.id` e índice compuesto por
`(usuario_id, creada)`. Tabla aditiva: nada existente cambia y una base que ya la trae (creada con
`create_all`) se adopta sin duplicarla. Al bajar se borran el índice y la tabla.

El respaldo previo lo hace `operacion.base_datos` antes de cualquier revisión.

`down_revision` es `ins_0013_solicitud_cuenta`, la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0014_notificacion"
down_revision = "ins_0013_solicitud_cuenta"
branch_labels = None
depends_on = None

TABLA = "notificacion"
INDICE = "ix_notificacion_usuario_creada"


def _tablas() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indices(tabla: str) -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(tabla) if i.get("name")}


def upgrade() -> None:
    if TABLA not in _tablas():
        op.create_table(
            TABLA,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuario.id"), nullable=False),
            sa.Column("gravedad", sa.String(12), nullable=False),
            sa.Column("titulo", sa.String(200), nullable=False),
            sa.Column("detalle", sa.String(1000), nullable=False),
            sa.Column("enlace_texto", sa.String(120), nullable=False),
            sa.Column("enlace_ruta", sa.String(300), nullable=False),
            sa.Column("creada", sa.DateTime, nullable=False),
            sa.Column("leida", sa.Boolean, nullable=False),
            sa.CheckConstraint(
                "gravedad IN ('listo', 'info', 'advertencia', 'error')",
                name="ck_notificacion_gravedad",
            ),
        )
    if INDICE not in _indices(TABLA):
        op.create_index(INDICE, TABLA, ["usuario_id", "creada"])


def downgrade() -> None:
    if TABLA in _tablas():
        if INDICE in _indices(TABLA):
            op.drop_index(INDICE, table_name=TABLA)
        op.drop_table(TABLA)
