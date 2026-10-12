"""S4 (0.9.0): el registro del asistente de IA, tablas `ia_*` (spec S4 §5.5, RF-93).

Tablas aditivas propias de `asistente.registro` en la base del caso, sin clave foranea a
`core/models`. Escrita a mano con la plantilla del destino `caso` (regla de S5-1); `down_revision`
es la `head` del destino antes de crearla.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0007_s4_asistente"
down_revision = "caso_0005_s2_valuaciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ia_sesiones",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("proyecto", sa.String(120), nullable=False),
        sa.Column("version_partida", sa.String(20), nullable=False),
        sa.Column("version_guardada", sa.String(20)),
        sa.Column("proveedor", sa.String(40), nullable=False),
        sa.Column("modelo_pedido", sa.String(80), nullable=False),
        sa.Column("pedido", sa.Text, nullable=False),
        sa.Column("topes", sa.Text, nullable=False),
        sa.Column("inicio", sa.DateTime, nullable=False),
        sa.Column("fin", sa.DateTime),
        sa.Column("motivo_fin", sa.String(40)),
    )
    op.create_table(
        "ia_turnos",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sesion_id", sa.Integer, sa.ForeignKey("ia_sesiones.id"), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False),
        sa.Column("modelo_respondio", sa.String(80), nullable=False),
        sa.Column("fin", sa.String(20), nullable=False),
        sa.Column("entrada", sa.Integer, nullable=False),
        sa.Column("salida", sa.Integer, nullable=False),
        sa.Column("cache_lectura", sa.Integer, nullable=False),
        sa.Column("cache_escritura", sa.Integer, nullable=False),
        sa.Column("costo", sa.String(40), nullable=False),
        sa.Column("texto", sa.Text, nullable=False),
    )
    op.create_table(
        "ia_llamadas",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sesion_id", sa.Integer, sa.ForeignKey("ia_sesiones.id"), nullable=False),
        sa.Column("turno", sa.Integer, nullable=False),
        sa.Column("herramienta", sa.String(40), nullable=False),
        sa.Column("argumentos", sa.Text, nullable=False),
        sa.Column("resultado", sa.String(40), nullable=False),
        sa.Column("motivo", sa.Text, nullable=False),
        sa.Column("respuesta", sa.Text),
    )
    op.create_table(
        "ia_propuestas",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sesion_id", sa.Integer, sa.ForeignKey("ia_sesiones.id"), nullable=False),
        sa.Column("propuesta", sa.String(20), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("citas", sa.Text, nullable=False),
        sa.Column("supuestos", sa.Text, nullable=False),
        sa.Column("filas", sa.Text, nullable=False),
        sa.Column("decidida_por", sa.String(80)),
        sa.Column("decidida_en", sa.DateTime),
    )


def downgrade() -> None:
    for tabla in ("ia_propuestas", "ia_llamadas", "ia_turnos", "ia_sesiones"):
        op.drop_table(tabla)
