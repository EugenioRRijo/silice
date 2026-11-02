"""MP-4 (Tarea 18): `mp_indice_aprobacion`, el índice de aprobaciones de todas las carpetas.

Una fila por envío a aprobación de cada carpeta de trabajo, reflejada desde su rastro (la carpeta
es la fuente de verdad); `UNIQUE(caso, envio_id)`. Tabla aditiva de
`aplicacion/tablas_indice_aprobacion.py`, sin clave foránea; el total es `DecimalExacto` (texto de
40). Ninguna tabla existente cambia. Una base que ya la trae (creada con `create_all`) se adopta
sin recrearla.

`down_revision` es `ins_0004_mod_eleccion` (MOD-0), la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0005_mp_indice_aprobacion"
down_revision = "ins_0004_mod_eleccion"
branch_labels = None
depends_on = None

TABLA = "mp_indice_aprobacion"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0009_s3_paquete`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    if TABLA in _faltan(TABLA):
        op.create_table(
            TABLA,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("caso", sa.String(255), nullable=False),
            sa.Column("envio_id", sa.Integer, nullable=False),
            sa.Column("proyecto", sa.String(120), nullable=False),
            sa.Column("obra", sa.String(200), nullable=False),
            sa.Column("version", sa.String(40), nullable=False),
            sa.Column("total", sa.String(40), nullable=False),
            sa.Column("moneda", sa.String(10), nullable=False),
            sa.Column("estado", sa.String(30), nullable=False),
            sa.Column("enviado_por", sa.String(200), nullable=False),
            sa.Column("enviado_el", sa.DateTime, nullable=False),
            sa.Column("dictamen_por", sa.String(200), nullable=True),
            sa.Column("dictamen_el", sa.DateTime, nullable=True),
            sa.Column("nota", sa.String(2000), nullable=False),
            sa.Column("notas", sa.String(2000), nullable=False),
            sa.Column("armo", sa.Boolean, nullable=False),
            sa.UniqueConstraint("caso", "envio_id", name="uq_mp_indice_aprobacion_envio"),
        )


def downgrade() -> None:
    if TABLA in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table(TABLA)
