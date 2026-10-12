# migraciones/caso/versions/caso_0006_s2_decision.py
"""S2-3 (SL-E6): la decisión de recuperación, con la foto de lo que el usuario vio."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0006_s2_decision"
down_revision = "caso_0005_s2_valuaciones"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aun no existen: una base sembrada con `create_all` del codigo 0.7.0 ya las
    trae (RP-4) y se adopta sin recrearlas; las que faltan se crean con `op.create_table`."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


TABLAS = ("decision_recuperacion",)


def upgrade() -> None:
    if not _faltan(*TABLAS):
        return
    op.create_table(
        "decision_recuperacion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "proyecto_id",
            sa.Integer,
            sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "linea_base_id",
            sa.Integer,
            sa.ForeignKey("linea_base_control.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_resultante_id",
            sa.Integer,
            sa.ForeignKey("presupuesto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fecha_corte", sa.Date, nullable=False),
        sa.Column("opcion", sa.String(20), nullable=False),
        sa.Column("detalle", sa.Text, nullable=False),
        sa.Column("costo_directo_adicional", DEC, nullable=False),
        sa.Column("costo_indirecto", DEC, nullable=False),
        sa.Column("penalizacion", DEC, nullable=False),
        sa.Column("termino", sa.Date, nullable=False),
        sa.Column("spi", DEC, nullable=True),
        sa.Column("cpi", DEC, nullable=True),
        sa.Column("eac", DEC, nullable=True),
        sa.Column("pe", DEC, nullable=True),
        sa.Column("supuestos", sa.Text, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
    )
    op.create_index("ix_decision_recuperacion_proyecto", "decision_recuperacion", ["proyecto_id"])


def downgrade() -> None:
    presentes = set(sa.inspect(op.get_bind()).get_table_names())
    for tabla in reversed(TABLAS):
        if tabla in presentes:
            op.drop_table(tabla)
