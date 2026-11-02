"""Plan vial, Tarea 4: `prod_calculo`, los cálculos del costo por tonelada del periodo.

Cada cálculo guarda sus entradas y su resultado en `instantanea` (JSON canónico) con la huella
SHA-256 de ese texto. Solo se inserta: recalcular es otra fila. Tabla aditiva; nada existente
cambia. Una base que ya trae la tabla (creada con `create_all`) se adopta sin recrearla. Al bajar se
borra la tabla (DA-S5-6: la bajada nunca se ofrece al usuario).

`down_revision` es `ins_0007_prod_receta`, la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0008_prod_calculo"
down_revision = "ins_0007_prod_receta"
branch_labels = None
depends_on = None

TABLA = "prod_calculo"


def upgrade() -> None:
    if TABLA in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        TABLA,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("periodo", sa.String(7), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("instantanea", sa.Text, nullable=False),
        sa.Column("usuario", sa.String(120), nullable=False),
        sa.Column("registrado", sa.DateTime, nullable=False),
        sa.CheckConstraint("moneda IN ('Bs', 'USD')", name="ck_prod_calculo_moneda"),
        sa.CheckConstraint("length(huella) = 64", name="ck_prod_calculo_huella"),
    )
    op.create_index("ix_prod_calculo_periodo", TABLA, ["periodo"])
    op.create_index("ix_prod_calculo_huella", TABLA, ["huella"])


def downgrade() -> None:
    if TABLA not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.drop_index("ix_prod_calculo_huella", TABLA)
    op.drop_index("ix_prod_calculo_periodo", TABLA)
    op.drop_table(TABLA)
