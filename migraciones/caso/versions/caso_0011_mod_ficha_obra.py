"""MOD-3a: `ficha_obra`, el cliente y la ubicación de cada obra.

Una fila por obra (`proyecto_id`, sin clave foránea a `core.models`) con `cliente` y `ubicacion`
(hasta 200 caracteres, vacíos por omisión). Tabla aditiva de `aplicacion/tablas_obra.py`; ninguna
tabla existente cambia. Una base que ya la trae (creada con `create_all`) se adopta sin recrearla.
Las obras existentes no reciben fila: su ficha es la vacía hasta que alguien la escriba.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0011_mod_ficha_obra"
down_revision = "caso_0010_mp_carpeta"
branch_labels = None
depends_on = None

TABLA = "ficha_obra"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0010_mp_carpeta`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    if TABLA in _faltan(TABLA):
        op.create_table(
            TABLA,
            sa.Column("proyecto_id", sa.Integer, primary_key=True, autoincrement=False),
            sa.Column("cliente", sa.String(200), nullable=False, server_default=""),
            sa.Column("ubicacion", sa.String(200), nullable=False, server_default=""),
        )


def downgrade() -> None:
    if TABLA in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table(TABLA)
