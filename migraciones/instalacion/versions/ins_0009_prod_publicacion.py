"""Plan vial, Tarea 4b: `prod_publicacion`, una sola publicación por cálculo (pregunta 22).

`calculo_id` es único: publicar dos veces el mismo cálculo es imposible en la base, no solo en la
aplicación. `caso` es el nombre de la carpeta de trabajo y `lista_id` la lista de empresa creada en
ella (otra base: sin clave foránea). Tabla aditiva; nada existente cambia. Una base que ya trae la
tabla (creada con `create_all`) se adopta sin recrearla. Al bajar se borra la tabla (DA-S5-6: la
bajada nunca se ofrece al usuario).

`down_revision` es `ins_0008_prod_calculo`, la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0009_prod_publicacion"
down_revision = "ins_0008_prod_calculo"
branch_labels = None
depends_on = None

TABLA = "prod_publicacion"


def upgrade() -> None:
    if TABLA in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        TABLA,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "calculo_id", sa.Integer, sa.ForeignKey("prod_calculo.id"), nullable=False, unique=True
        ),
        sa.Column("caso", sa.String(255), nullable=False),
        sa.Column("lista_id", sa.Integer, nullable=False),
        sa.Column("usuario", sa.String(120), nullable=False),
        sa.Column("registrado", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    if TABLA not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.drop_table(TABLA)
