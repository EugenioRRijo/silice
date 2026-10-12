"""S1-1 (SL-E1): series, importaciones, valores, moneda del proyecto y origen por precio."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0002_s1_moneda"
down_revision = "caso_0001_base_0_5_0"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aun no existen: una base sembrada con `create_all` del codigo 0.6.0 ya las
    trae (RP-4) y se adopta sin recrearlas; las que faltan se crean con `op.create_table`."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    faltan = _faltan("serie_indice", "importacion_indice", "valor_indice", "moneda_proyecto",
                     "precio_origen")
    if "serie_indice" in faltan:
        _serie_indice()
    if "importacion_indice" in faltan:
        _importacion_indice()
    if "valor_indice" in faltan:
        _valor_indice()
    if "moneda_proyecto" in faltan:
        _moneda_proyecto()
    if "precio_origen" in faltan:
        _precio_origen()


def _serie_indice() -> None:
    op.create_table(
        "serie_indice",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("codigo", sa.String(40), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("organismo", sa.String(120), nullable=False),
        sa.Column("unidad", sa.String(40), nullable=False),
        sa.Column("periodicidad", sa.String(12), nullable=False),
        sa.Column("base", sa.String(200), nullable=False),
        sa.UniqueConstraint("codigo", name="uq_serie_indice_codigo"),
    )


def _importacion_indice() -> None:
    op.create_table(
        "importacion_indice",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("serie_id", sa.Integer, sa.ForeignKey("serie_indice.id"), nullable=False),
        sa.Column("archivo", sa.String(255), nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("fuente", sa.String(500), nullable=False),
        sa.Column("fecha_descarga", sa.Date, nullable=False),
        sa.Column("fecha_importacion", sa.DateTime, nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("filas_leidas", sa.Integer, nullable=False),
        sa.Column("filas_rechazadas", sa.Integer, nullable=False),
        sa.Column("informe", sa.Text, nullable=False),
    )
    op.create_index("ix_importacion_indice_serie_huella", "importacion_indice",
                    ["serie_id", "huella"])


def _valor_indice() -> None:
    op.create_table(
        "valor_indice",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("serie_id", sa.Integer, sa.ForeignKey("serie_indice.id"), nullable=False),
        sa.Column("importacion_id", sa.Integer,
                  sa.ForeignKey("importacion_indice.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("valor", DEC, nullable=False),
        sa.Column("provisional", sa.Boolean, nullable=False),
        sa.UniqueConstraint("serie_id", "fecha", "importacion_id", name="uq_valor_indice"),
    )
    op.create_index("ix_valor_indice_serie_fecha", "valor_indice", ["serie_id", "fecha"])


def _moneda_proyecto() -> None:
    op.create_table(
        "moneda_proyecto",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("proyecto_id", sa.Integer, sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("moneda", sa.String(10), nullable=False),
        sa.Column("desde", sa.DateTime, nullable=False),
        sa.Column("version_id", sa.Integer,
                  sa.ForeignKey("presupuesto.id", ondelete="SET NULL"), nullable=True),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
    )


def _precio_origen() -> None:
    op.create_table(
        "precio_origen",
        sa.Column("precio_id", sa.Integer,
                  sa.ForeignKey("precio_insumo.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("moneda_original", sa.String(10), nullable=False),
        sa.Column("precio_original", DEC, nullable=False),
        sa.Column("fecha_precio", sa.Date, nullable=False),
        sa.Column("tasa", DEC, nullable=True),
        sa.Column("fecha_tasa", sa.Date, nullable=True),
        sa.Column("fuente_tasa", sa.String(300), nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
    )


def downgrade() -> None:
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    for tabla in ("precio_origen", "moneda_proyecto", "valor_indice", "importacion_indice",
                  "serie_indice"):
        if tabla in existentes:
            op.drop_table(tabla)
