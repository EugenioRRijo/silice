"""MP-7 (Tarea 22): `mp_causa_retraso`, las causas de retraso por partida de cada valuación.

Una fila por línea de valuación a la que se le declaró una causa (solo inserción): la valuación, la
partida, la causa (`aplicacion.causas.CAUSAS`) y el momento del registro. Tabla aditiva de
`aplicacion/tablas_causas.py`, sin clave foránea a `core.models`; ninguna tabla existente cambia.
Una base que ya la trae (creada con `create_all` desde `crear_esquema_causas`, o por el registro de
una valuación en una base sin migrar) se adopta sin recrearla.

`down_revision` es `caso_0012_mp_medicion`, la cabeza al integrar (plan, «Cambios por el diseño de
módulos», Migraciones: … → `caso_0014_mp_aprobacion` → `caso_0012_mp_medicion` → esta). La procura
de la Tarea 23 (`caso_0016_mp_procura`) cuelga de esta.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0015_mp_causas"
down_revision = "caso_0012_mp_medicion"
branch_labels = None
depends_on = None

TABLA = "mp_causa_retraso"
INDICE = "ix_mp_causa_retraso_valuacion"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0009_s3_paquete`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    if TABLA in _faltan(TABLA):
        op.create_table(
            TABLA,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("valuacion_id", sa.Integer, nullable=False),
            sa.Column("codigo_partida", sa.String(40), nullable=False),
            sa.Column("causa", sa.String(40), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
        )
        op.create_index(INDICE, TABLA, ["valuacion_id"])


def downgrade() -> None:
    if TABLA in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_index(INDICE, table_name=TABLA)
        op.drop_table(TABLA)
