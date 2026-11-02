"""MP-7 (Tarea 23): `mp_plazo_entrega` y `mp_compra`, la procura con fechas.

Tablas aditivas de `aplicacion/tablas_procura.py`, sin clave foránea a `core.models`; ninguna tabla
existente cambia. Las cantidades y los precios son `DecimalExacto` (texto de 40). `mp_compra` es
solo inserción; `mp_plazo_entrega` tiene una fila por (obra, descripción, unidad). Una base que ya
las trae (creada con `create_all` desde `crear_esquema_procura`) se adopta sin recrearlas.

Cuelga de `caso_0015_mp_causas` (T22), la cabeza cuando se integró (plan, «Cambios por el diseño de
módulos», Migraciones).
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0016_mp_procura"
down_revision = "caso_0015_mp_causas"
branch_labels = None
depends_on = None

PLAZO = "mp_plazo_entrega"
COMPRA = "mp_compra"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0009_s3_paquete`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    faltan = _faltan(PLAZO, COMPRA)
    if PLAZO in faltan:
        op.create_table(
            PLAZO,
            sa.Column("proyecto_id", sa.Integer, primary_key=True),
            sa.Column("descripcion_insumo", sa.String(300), primary_key=True),
            sa.Column("unidad", sa.String(20), primary_key=True),
            sa.Column("dias", sa.Integer, nullable=False),
        )
    if COMPRA in faltan:
        op.create_table(
            COMPRA,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("proyecto_id", sa.Integer, nullable=False),
            sa.Column("descripcion_insumo", sa.String(300), nullable=False),
            sa.Column("unidad", sa.String(20), nullable=False),
            sa.Column("evento", sa.String(10), nullable=False),
            sa.Column("fecha", sa.Date, nullable=False),
            sa.Column("cantidad", sa.String(40), nullable=True),
            sa.Column("precio", sa.String(40), nullable=True),
            sa.Column("moneda", sa.String(10), nullable=True),
            sa.Column("responsable", sa.String(200), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
        )
        op.create_index(
            "ix_mp_compra_insumo", COMPRA, ["proyecto_id", "descripcion_insumo", "unidad"]
        )


def downgrade() -> None:
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    for tabla in (COMPRA, PLAZO):
        if tabla in existentes:
            op.drop_table(tabla)
