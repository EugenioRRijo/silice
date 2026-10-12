"""S1-4 (SL-E3): cláusula, componentes, estudio, períodos y ejecutado del reajuste."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0004_s1_reajuste"
down_revision = "caso_0003_s1_lista_empresa"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aun no existen: una base sembrada con `create_all` del codigo 0.6.0 ya las
    trae (RP-4) y se adopta sin recrearlas; las que faltan se crean con `op.create_table`."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


TABLAS = (
    "clausula_reajuste",
    "componente_clausula",
    "estudio_reajuste",
    "periodo_reajuste",
    "ejecutado_periodo",
)


def upgrade() -> None:
    faltan = _faltan(*TABLAS)
    if "clausula_reajuste" in faltan:
        _clausula_reajuste()
    if "componente_clausula" in faltan:
        _componente_clausula()
    if "estudio_reajuste" in faltan:
        _estudio_reajuste()
    if "periodo_reajuste" in faltan:
        _periodo_reajuste()
    if "ejecutado_periodo" in faltan:
        _ejecutado_periodo()


def _clausula_reajuste() -> None:
    op.create_table(
        "clausula_reajuste",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "presupuesto_id",
            sa.Integer,
            sa.ForeignKey("presupuesto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fecha_inicio", sa.Date, nullable=False),
        sa.Column("duracion_meses", sa.Integer, nullable=False),
        sa.Column("fecha_referencia_primer_anio", sa.Date, nullable=False),
        sa.Column("periodicidad", sa.String(20), nullable=False),
        sa.Column("mecanismo", sa.String(20), nullable=False),
        sa.Column("mecanismo_pagadero", sa.String(20), nullable=True),
        sa.Column("fuente_pagadero", sa.String(300), nullable=False),
        sa.Column("estructura", sa.String(20), nullable=False),
        sa.Column("fecha_base_indices", sa.Date, nullable=False),
        sa.Column("r", DEC, nullable=False),
        sa.Column("fuente_r", sa.String(300), nullable=False),
        sa.Column("r_en_comprobacion", sa.Boolean, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
    )


def _componente_clausula() -> None:
    op.create_table(
        "componente_clausula",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "clausula_id",
            sa.Integer,
            sa.ForeignKey("clausula_reajuste.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("orden", sa.Integer, nullable=False),
        sa.Column("componente", sa.String(20), nullable=False),
        sa.Column("serie_id", sa.Integer, sa.ForeignKey("serie_indice.id"), nullable=False),
        sa.Column("peso", DEC, nullable=True),
    )


def _estudio_reajuste() -> None:
    op.create_table(
        "estudio_reajuste",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "presupuesto_id",
            sa.Integer,
            sa.ForeignKey("presupuesto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "clausula_id",
            sa.Integer,
            sa.ForeignKey("clausula_reajuste.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fecha_calculo", sa.Date, nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("fecha_corte", sa.Date, nullable=True),
        sa.Column("reemplaza_a", sa.Integer, sa.ForeignKey("estudio_reajuste.id"), nullable=True),
        sa.Column("moneda", sa.String(10), nullable=False),
        sa.Column("lado", sa.String(10), nullable=False),
        sa.Column("monto_original", DEC, nullable=False),
        sa.Column("total_escalatoria", DEC, nullable=False),
        sa.Column("total_comprobacion", DEC, nullable=False),
        sa.Column("total_reconocido", DEC, nullable=False),
        sa.Column("avisos", sa.Text, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
        sa.UniqueConstraint("reemplaza_a", name="uq_estudio_reemplaza_a"),
    )


def _periodo_reajuste() -> None:
    op.create_table(
        "periodo_reajuste",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "estudio_id",
            sa.Integer,
            sa.ForeignKey("estudio_reajuste.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("orden", sa.Integer, nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=False),
        sa.Column("km", DEC, nullable=True),
        sa.Column("escalatoria", DEC, nullable=True),
        sa.Column("comprobacion", DEC, nullable=True),
        sa.Column("reconocido", DEC, nullable=True),
        sa.Column("mecanismo_reconocido", sa.String(20), nullable=False),
        sa.Column(
            "version_comprobacion_id",
            sa.Integer,
            sa.ForeignKey("presupuesto.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tasa", DEC, nullable=True),
        sa.Column("fecha_tasa", sa.Date, nullable=True),
        sa.Column("importaciones", sa.Text, nullable=False),
        sa.Column("marcas", sa.Text, nullable=False),
        sa.Column("excepcion", sa.String(300), nullable=False),
    )


def _ejecutado_periodo() -> None:
    op.create_table(
        "ejecutado_periodo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "periodo_id",
            sa.Integer,
            sa.ForeignKey("periodo_reajuste.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("orden", sa.Integer, nullable=False),
        sa.Column("codigo_partida", sa.String(40), nullable=False),
        sa.Column("cantidad", DEC, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
    )


def downgrade() -> None:
    presentes = set(sa.inspect(op.get_bind()).get_table_names())
    for tabla in reversed(TABLAS):
        if tabla in presentes:
            op.drop_table(tabla)
