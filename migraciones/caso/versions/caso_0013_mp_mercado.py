"""MP-5 (Tarea 13): `mp_observacion` y `mp_precio_objetivo`, el estudio de mercado.

Tablas aditivas de `aplicacion/tablas_mercado.py`, sin clave foránea a `core.models`; ninguna tabla
existente cambia. Los montos son `DecimalExacto` (texto de 40). Una base que ya las trae (creada
con `create_all` desde `crear_esquema_mercado`) se adopta sin recrearlas.

Cuelga de `caso_0011_mod_ficha_obra` (orden fijado por el orquestador: ficha de obra → mercado →
aprobación). Si `caso_0012_mp_medicion` (T9) entra después, el orquestador la intercala al integrar.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0013_mp_mercado"
down_revision = "caso_0011_mod_ficha_obra"
branch_labels = None
depends_on = None

OBSERVACION = "mp_observacion"
OBJETIVO = "mp_precio_objetivo"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0009_s3_paquete`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    faltan = _faltan(OBSERVACION, OBJETIVO)
    if OBSERVACION in faltan:
        op.create_table(
            OBSERVACION,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("lado", sa.String(10), nullable=False),
            sa.Column("codigo", sa.String(40), nullable=False),
            sa.Column("fuente_tipo", sa.String(20), nullable=False),
            sa.Column("fuente", sa.String(200), nullable=False),
            sa.Column("fecha", sa.Date, nullable=False),
            sa.Column("moneda", sa.String(10), nullable=False),
            sa.Column("precio", sa.String(40), nullable=False),
            sa.Column("nota", sa.String(500), nullable=False),
            sa.Column("responsable", sa.String(200), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
            sa.Column("anulada_por", sa.Integer, nullable=True),
        )
        op.create_index("ix_mp_observacion_lado_codigo", OBSERVACION, ["lado", "codigo"])
    if OBJETIVO in faltan:
        op.create_table(
            OBJETIVO,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("codigo_partida", sa.String(40), nullable=False),
            sa.Column("precio", sa.String(40), nullable=False),
            sa.Column("moneda", sa.String(10), nullable=False),
            sa.Column("observaciones", sa.String(400), nullable=False),
            sa.Column("responsable", sa.String(200), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
        )
        op.create_index("ix_mp_precio_objetivo_codigo_partida", OBJETIVO, ["codigo_partida"])


def downgrade() -> None:
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    for tabla in (OBJETIVO, OBSERVACION):
        if tabla in existentes:
            op.drop_table(tabla)
