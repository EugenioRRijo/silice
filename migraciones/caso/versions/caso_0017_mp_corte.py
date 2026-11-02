"""MP-7 (Tarea 25): `mp_precio_corte`, el precio declarado de un material como precio del corte.

Tabla aditiva de `aplicacion/tablas_corte.py`, sin clave foránea a `core.models`; ninguna tabla
existente cambia. El precio es `DecimalExacto` (texto de 40). Solo inserción: al leer manda el
último precio declarado hasta el corte. Una base que ya la trae (creada con `create_all` desde
`crear_esquema_corte`) se adopta sin recrearla.

Cuelga de `caso_0016_mp_procura` (T23), la cabeza cuando se escribió (la cadena real es
0010 → 0011_mod_ficha_obra → 0013_mp_mercado → 0014_mp_aprobacion → 0012_mp_medicion →
0015_mp_causas → 0016_mp_procura).

Cuidado al bajar (`downgrade`): borra la tabla y, con ella, todos los precios declarados como precio
del corte. Esos datos no se reconstruyen desde otra tabla; quien baje debe tener el respaldo previo
que `preparar_base` deja antes de migrar.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0017_mp_corte"
down_revision = "caso_0016_mp_procura"
branch_labels = None
depends_on = None

TABLA = "mp_precio_corte"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0009_s3_paquete`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    if TABLA not in _faltan(TABLA):
        return
    op.create_table(
        TABLA,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("proyecto_id", sa.Integer, nullable=False),
        sa.Column("descripcion_insumo", sa.String(300), nullable=False),
        sa.Column("unidad", sa.String(20), nullable=False),
        sa.Column("precio", sa.String(40), nullable=False),
        sa.Column("moneda", sa.String(10), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(200), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_mp_precio_corte_insumo", TABLA, ["proyecto_id", "descripcion_insumo", "unidad"]
    )


def downgrade() -> None:
    if not _faltan(TABLA):
        op.drop_table(TABLA)
