"""Sesion 4 (historial): la tabla de auditorias de «Libro de la empresa» en la instalacion.

Cada auditoria de UC-25 (libro o PDF simple) deja una fila con su resumen y sus hallazgos
compactos (RF-142, RF-143). El libro y el PDF no se guardan nunca (RNF-28): solo la huella SHA-256.
Los totales son texto decimal exacto (`DEC`), nunca `float`.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0003_auditoria_libro"
down_revision = "ins_0002_produccion"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de fusion.historial_modelo.Total


def upgrade() -> None:
    op.create_table(
        "auditoria_libro",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
        sa.Column("usuario", sa.String(120), nullable=False),
        sa.Column("tipo", sa.String(5), nullable=False),
        sa.Column("nombre_archivo", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("fecha_libro", sa.Date, nullable=True),
        sa.Column("total_libro", DEC, nullable=True),
        sa.Column("total_silice", DEC, nullable=True),
        sa.Column("errores", sa.Integer, nullable=False),
        sa.Column("advertencias", sa.Integer, nullable=False),
        sa.Column("informativos", sa.Integer, nullable=False),
        sa.Column("atipicos", sa.Integer, nullable=False),
        sa.Column("recortado", sa.Boolean, nullable=False),
        sa.Column("hallazgos", sa.Text, nullable=False),
        sa.CheckConstraint("tipo IN ('libro', 'pdf')", name="ck_auditoria_libro_tipo"),
    )
    op.create_index("ix_auditoria_libro_fecha_hora", "auditoria_libro", ["fecha_hora"])


def downgrade() -> None:
    op.drop_index("ix_auditoria_libro_fecha_hora", "auditoria_libro")
    op.drop_table("auditoria_libro")
