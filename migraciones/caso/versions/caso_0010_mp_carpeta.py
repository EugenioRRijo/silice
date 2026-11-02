"""MP-1 (Tarea 1; D-MP1): `mp_carpeta`, la moneda de la carpeta de trabajo.

Una sola fila (`id = 1`) con la moneda declarada, quién la declaró y cuándo. Tabla aditiva de
`aplicacion/tablas_carpeta.py`, sin clave foránea a `core.models`; ninguna tabla existente cambia.
Una base que ya la trae (creada con `create_all` desde `crear_esquema_carpeta`) se adopta sin
recrearla. Las carpetas existentes no reciben fila: su moneda es la de su lista vigente hasta que
alguien la declare.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0010_mp_carpeta"
down_revision = "caso_0009_s3_paquete"
branch_labels = None
depends_on = None

TABLA = "mp_carpeta"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0009_s3_paquete`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    if TABLA in _faltan(TABLA):
        op.create_table(
            TABLA,
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
            sa.Column("moneda", sa.String(10), nullable=False),
            sa.Column("declarada_por", sa.String(200), nullable=False),
            sa.Column("declarada_el", sa.DateTime, nullable=False),
        )


def downgrade() -> None:
    if TABLA in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table(TABLA)
