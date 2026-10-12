# migraciones/caso/versions/caso_0005_s2_valuaciones.py
"""S2-1 (SL-E4): línea base de control, valuaciones, costos incurridos y cita de valuaciones."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0005_s2_valuaciones"
down_revision = "caso_0004_s1_reajuste"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aun no existen: una base sembrada con `create_all` del codigo 0.7.0 ya las
    trae (RP-4) y se adopta sin recrearlas; las que faltan se crean con `op.create_table`."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


TABLAS = (
    "linea_base_control",
    "calendario_obra",
    "parametros_control",
    "valuacion",
    "linea_valuacion",
    "anulacion_valuacion",
    "costo_real",
    "cita_valuacion",
)


def upgrade() -> None:
    faltan = _faltan(*TABLAS)
    if "linea_base_control" in faltan:
        op.create_table(
            "linea_base_control",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "proyecto_id",
                sa.Integer,
                sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "presupuesto_id",
                sa.Integer,
                sa.ForeignKey("presupuesto.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("desde", sa.Date, nullable=False),
            sa.Column("perspectiva", sa.String(10), nullable=False),
            sa.Column("fuente", sa.String(300), nullable=False),
            sa.Column("responsable", sa.String(120), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
        )
        op.create_index(
            "ix_linea_base_control_proyecto", "linea_base_control", ["proyecto_id", "desde"]
        )
    if "calendario_obra" in faltan:
        op.create_table(
            "calendario_obra",
            sa.Column(
                "linea_base_id",
                sa.Integer,
                sa.ForeignKey("linea_base_control.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("fecha_inicio", sa.Date, nullable=False),
            sa.Column("dias_por_periodo", sa.Integer, nullable=False),
            sa.Column("feriados", sa.Text, nullable=False),
        )
    if "parametros_control" in faltan:
        op.create_table(
            "parametros_control",
            sa.Column(
                "proyecto_id",
                sa.Integer,
                sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("spi_error", DEC, nullable=False),
            sa.Column("cpi_error", DEC, nullable=False),
            sa.Column("retraso_error", DEC, nullable=False),
            sa.Column("precio_info", DEC, nullable=False),
            sa.Column("equilibrio_puntos", DEC, nullable=False),
            sa.Column("eta_cuadrilla", DEC, nullable=False),
            sa.Column("cuadrillas_max", sa.Integer, nullable=False),
            sa.Column("eta_horas_extra", DEC, nullable=False),
            sa.Column("horas_extra_dia", DEC, nullable=False),
            sa.Column("recargo_horas_extra", DEC, nullable=False),
            sa.Column("fcas_en_horas_extra", sa.Boolean, nullable=False),
            sa.Column("penalizacion_diaria", DEC, nullable=False),
            sa.Column("fuente_penalizacion", sa.String(300), nullable=False),
        )
    if "valuacion" in faltan:
        op.create_table(
            "valuacion",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "proyecto_id",
                sa.Integer,
                sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("numero", sa.String(40), nullable=False),
            sa.Column("desde", sa.Date, nullable=False),
            sa.Column("hasta", sa.Date, nullable=False),
            sa.Column("fecha", sa.Date, nullable=True),
            sa.Column("inspector", sa.String(120), nullable=False),
            sa.Column("origen", sa.String(300), nullable=False),
            sa.Column("fuente", sa.String(300), nullable=False),
            sa.Column("responsable", sa.String(120), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
        )
        op.create_index("ix_valuacion_proyecto", "valuacion", ["proyecto_id"])
    if "linea_valuacion" in faltan:
        op.create_table(
            "linea_valuacion",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "valuacion_id",
                sa.Integer,
                sa.ForeignKey("valuacion.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("codigo_partida", sa.String(40), nullable=False),
            sa.Column("cantidad", DEC, nullable=False),
            sa.Column("fecha_medicion", sa.Date, nullable=True),
            sa.Column("observacion", sa.Text, nullable=False),
        )
        op.create_index("ix_linea_valuacion_valuacion", "linea_valuacion", ["valuacion_id"])
    if "anulacion_valuacion" in faltan:
        op.create_table(
            "anulacion_valuacion",
            sa.Column(
                "valuacion_id",
                sa.Integer,
                sa.ForeignKey("valuacion.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("motivo", sa.Text, nullable=False),
            sa.Column("responsable", sa.String(120), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
        )
    if "costo_real" in faltan:
        op.create_table(
            "costo_real",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "proyecto_id",
                sa.Integer,
                sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "valuacion_id",
                sa.Integer,
                sa.ForeignKey("valuacion.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("codigo_partida", sa.String(40), nullable=True),
            sa.Column("monto", DEC, nullable=False),
            sa.Column("moneda", sa.String(10), nullable=False),
            sa.Column("fecha", sa.Date, nullable=False),
            sa.Column("fuente", sa.String(300), nullable=False),
            sa.Column("responsable", sa.String(120), nullable=False),
        )
        op.create_index("ix_costo_real_proyecto", "costo_real", ["proyecto_id"])
    if "cita_valuacion" in faltan:
        op.create_table(
            "cita_valuacion",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "periodo_id",
                sa.Integer,
                sa.ForeignKey("periodo_reajuste.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "valuacion_id",
                sa.Integer,
                sa.ForeignKey("valuacion.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.UniqueConstraint("periodo_id", "valuacion_id", name="uq_cita_valuacion"),
        )


def downgrade() -> None:
    presentes = set(sa.inspect(op.get_bind()).get_table_names())
    for tabla in reversed(TABLAS):
        if tabla in presentes:
            op.drop_table(tabla)
