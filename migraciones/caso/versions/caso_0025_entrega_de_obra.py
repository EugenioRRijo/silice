"""Lote G5 (C11b, 2026-11-26): `entrega_de_obra`, la fecha de entrega al cliente de cada obra.

Tabla aditiva de `aplicacion/tablas_entrega.py`, sin clave foránea a `core.models`; ninguna tabla
existente cambia. Una fila por obra (`proyecto_codigo`) con `fecha_entrega` (`DATE`, anulable),
`actualizada` (`DATETIME`) y `actualizada_por` (`VARCHAR(200)`). Una base que ya la trae (creada con
`crear_esquema_entrega`) se adopta sin recrearla.

Cuelga de `caso_0024_desperdicio_responsable`.

Cuidado al bajar (`downgrade`): borra la tabla `entrega_de_obra` y con ella las fechas de entrega
al cliente registradas en la carpeta. Quien baje debe tener el respaldo previo que `preparar_base`
deja antes de migrar.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0025_entrega_de_obra"
down_revision = "caso_0024_desperdicio_responsable"
branch_labels = None
depends_on = None

TABLA = "entrega_de_obra"


def _existe() -> bool:
    return TABLA in set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if not _existe():
        op.create_table(
            TABLA,
            sa.Column("proyecto_codigo", sa.String(40), primary_key=True),
            sa.Column("fecha_entrega", sa.Date, nullable=True),
            sa.Column("actualizada", sa.DateTime, nullable=False),
            sa.Column("actualizada_por", sa.String(200), nullable=False),
        )


def downgrade() -> None:
    if _existe():
        op.drop_table(TABLA)
