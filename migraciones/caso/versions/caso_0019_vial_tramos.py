"""Plan vial, Tarea 8: `vial_tramos_guardado` y `vial_tramo`, los tramos viales de cada versión.

Tablas aditivas de `aplicacion/tablas_vial.py`, sin clave foránea a `core.models`; ninguna tabla
existente cambia. Solo inserción: guardar otra vez los tramos de una versión es otra fila de
`vial_tramos_guardado` y al leer manda el último. Las cifras son texto de 40 (`DecimalExacto`). Una
base que ya trae alguna de las dos (creada con `create_all` desde `crear_esquema_vial`, al guardar
los primeros tramos en una base sin migrar) se adopta sin recrearla.

Cuelga de `caso_0018_mp_corte_tasa`, la cabeza cuando se escribió.

Cuidado al bajar (`downgrade`): borra las dos tablas y, con ellas, todos los tramos guardados y su
rastro. Esos datos no se reconstruyen desde otra tabla; quien baje debe tener el respaldo previo
que `preparar_base` deja antes de migrar.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0019_vial_tramos"
down_revision = "caso_0018_mp_corte_tasa"
branch_labels = None
depends_on = None

GUARDADO = "vial_tramos_guardado"
TRAMO = "vial_tramo"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0017_mp_corte`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    faltan = _faltan(GUARDADO, TRAMO)
    if GUARDADO in faltan:
        op.create_table(
            GUARDADO,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("version_id", sa.Integer, nullable=False),
            sa.Column("usuario", sa.String(200), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
            sa.Column("fuente", sa.String(300), nullable=False),
        )
        op.create_index("ix_vial_tramos_guardado_version", GUARDADO, ["version_id"])
    if TRAMO in faltan:
        op.create_table(
            TRAMO,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("guardado_id", sa.Integer, nullable=False),
            sa.Column("orden", sa.Integer, nullable=False),
            sa.Column("tramo_id", sa.String(80), nullable=False),
            sa.Column("progresiva_ini_km", sa.String(40), nullable=False),
            sa.Column("progresiva_fin_km", sa.String(40), nullable=False),
            sa.Column("ancho_m", sa.String(40), nullable=False),
            sa.Column("distancia_planta_km", sa.String(40), nullable=True),
            sa.Column("capas", sa.Text, nullable=False),
            sa.Column("demarcacion", sa.Text, nullable=False),
        )
        op.create_index("ix_vial_tramo_guardado", TRAMO, ["guardado_id"])


def downgrade() -> None:
    faltan = _faltan(TRAMO, GUARDADO)
    for tabla in (TRAMO, GUARDADO):
        if tabla not in faltan:
            op.drop_table(tabla)
