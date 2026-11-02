"""MOD-0 (diseño de módulos §12.1): la elección y las preferencias de cada cuenta en la instalación.

`mp_eleccion` guarda por cuenta la carpeta de trabajo (`caso`, nula = la carpeta de la
instalación), la obra (`proyecto`), el último módulo abierto y si el sidebar queda fijado. Reemplaza
a la `ins_0004_mp_eleccion` del plan de montar un presupuesto (Tarea 5), que no llegó a existir.
Tabla aditiva de `aplicacion/tablas_eleccion.py`, sin clave foránea; una base que ya la trae
(creada con `create_all`) se adopta sin recrearla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0004_mod_eleccion"
down_revision = "ins_0003_auditoria_libro"
branch_labels = None
depends_on = None

TABLA = "mp_eleccion"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0009_s3_paquete`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    if TABLA in _faltan(TABLA):
        op.create_table(
            TABLA,
            sa.Column("usuario_id", sa.Integer, primary_key=True, autoincrement=False),
            sa.Column("caso", sa.String(255), nullable=True),
            sa.Column("proyecto", sa.String(120), nullable=True),
            sa.Column("modulo", sa.String(20), nullable=True),
            sa.Column("sidebar_fijado", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("fecha", sa.DateTime, nullable=False),
        )


def downgrade() -> None:
    op.drop_table(TABLA)
