"""F4, Tarea 10: `hoja_importaciones`, el registro de importaciones de cada obra.

Tabla aditiva de `aplicacion/tablas_importaciones.py`, sin clave foránea a `core.models`; ninguna
tabla existente cambia. Guarda el nombre del archivo importado (plano o cómputo), quién, cuándo y
qué produjo, ligado a la versión que lo guardó; nunca una copia del archivo. Una base que ya la
trae (creada con `create_all` desde `crear_esquema_importaciones`, al guardar la primera versión
con importaciones en una base sin migrar) se adopta sin recrearla.

Cuelga de `caso_0019_vial_tramos`, la cabeza cuando se escribió. Si otra línea creó su propia
`caso_0020`, se renumera según la cabeza real al integrar (pregunta abierta 14 del plan).

Cuidado al bajar (`downgrade`): borra la tabla y, con ella, todo el registro. Esos datos no se
reconstruyen desde otra tabla; quien baje debe tener el respaldo previo que `preparar_base` deja
antes de migrar.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0020_hoja_importaciones"
down_revision = "caso_0019_vial_tramos"
branch_labels = None
depends_on = None

TABLA = "hoja_importaciones"


def _existe() -> bool:
    return TABLA in set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if _existe():
        return
    op.create_table(
        TABLA,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("version_id", sa.Integer, nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("archivo", sa.String(255), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
        sa.Column("usuario", sa.String(200), nullable=False),
        sa.Column("resumen", sa.String(300), nullable=False),
    )
    op.create_index("ix_hoja_importaciones_version", TABLA, ["version_id"])


def downgrade() -> None:
    if _existe():
        op.drop_table(TABLA)
