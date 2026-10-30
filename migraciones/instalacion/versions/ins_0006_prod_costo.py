"""Plan vial, Tarea 1: `prod_costo`, los costos del periodo de la cantera y la planta.

Una fila por costo registrado; anular es una fila nueva con `anula_id` (nada se sobrescribe). Tabla
aditiva: ninguna existente cambia. El monto es texto exacto (`String(40)`), igual que `ins_0002`.
Una base que ya la trae (creada con `create_all`) se adopta sin recrearla.

`down_revision` es `ins_0005_mp_indice_aprobacion`, la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0006_prod_costo"
down_revision = "ins_0005_mp_indice_aprobacion"
branch_labels = None
depends_on = None

TABLA = "prod_costo"
DEC = sa.String(40)  # impl de produccion.modelo.Cantidad


def upgrade() -> None:
    if TABLA in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        TABLA,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("periodo", sa.String(7), nullable=False),
        sa.Column("centro", sa.String(10), nullable=False),
        sa.Column("concepto", sa.String(20), nullable=False),
        sa.Column("monto", DEC, nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("fuente", sa.String(200), nullable=False),
        sa.Column("nota", sa.String(300), nullable=False),
        sa.Column("usuario", sa.String(120), nullable=False),
        sa.Column("registrado", sa.DateTime, nullable=False),
        sa.Column("anula_id", sa.Integer, sa.ForeignKey("prod_costo.id"), nullable=True),
        sa.Column("motivo", sa.String(300), nullable=False),
        sa.CheckConstraint("centro IN ('cantera', 'planta')", name="ck_prod_costo_centro"),
        sa.CheckConstraint(
            "concepto IN ('gasoil', 'equipo', 'nomina', 'mantenimiento', 'explosivos', "
            "'energia', 'otro')",
            name="ck_prod_costo_concepto",
        ),
        sa.CheckConstraint("moneda IN ('Bs', 'USD')", name="ck_prod_costo_moneda"),
        sa.CheckConstraint("length(monto) > 0", name="ck_prod_costo_monto"),
    )
    op.create_index("ix_prod_costo_periodo", TABLA, ["periodo"])
    op.create_index("ix_prod_costo_anula_id", TABLA, ["anula_id"])


def downgrade() -> None:
    if TABLA in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_index("ix_prod_costo_anula_id", TABLA)
        op.drop_index("ix_prod_costo_periodo", TABLA)
        op.drop_table(TABLA)
