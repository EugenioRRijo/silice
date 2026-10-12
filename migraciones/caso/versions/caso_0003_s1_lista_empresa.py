"""S1-3 (SL-E2): la lista de precios de una empresa."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0003_s1_lista_empresa"
down_revision = "caso_0002_s1_moneda"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aun no existen: una base sembrada con `create_all` del codigo 0.6.0 ya las
    trae (RP-4) y se adopta sin recrearlas; las que faltan se crean con `op.create_table`."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    if "lista_empresa" not in _faltan("lista_empresa"):
        return
    op.create_table(
        "lista_empresa",
        sa.Column(
            "lista_id",
            sa.Integer,
            sa.ForeignKey("lista_precios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("empresa_nombre", sa.String(200), nullable=False),
        sa.Column("empresa_rif", sa.String(20), nullable=False),
        sa.Column("lista_base_id", sa.Integer, sa.ForeignKey("lista_precios.id"), nullable=False),
        sa.Column(
            "lista_referencia_id", sa.Integer, sa.ForeignKey("lista_precios.id"), nullable=True
        ),
        sa.Column("plazo_vigencia_dias", sa.Integer, nullable=False),
        sa.Column("rango_inferior", DEC, nullable=False),
        sa.Column("rango_superior", DEC, nullable=False),
    )


def downgrade() -> None:
    if "lista_empresa" not in _faltan("lista_empresa"):
        op.drop_table("lista_empresa")
