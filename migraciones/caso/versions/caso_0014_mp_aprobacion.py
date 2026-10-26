"""MP-4 (Tarea 17): `mp_aprobacion_evento`, el rastro de aprobaciones de la carpeta.

Una fila por envío, retiro o dictamen (solo inserción) con el sello del eslabón de su versión y su
propia huella encadenada a la anterior de la misma obra. Tabla aditiva de
`aplicacion/tablas_aprobacion.py`, sin clave foránea a `core.models`; ninguna tabla existente
cambia. Una base que ya la trae (creada con `create_all` desde `crear_esquema_aprobacion`) se adopta
sin recrearla.

`down_revision` es `caso_0013_mp_mercado`, por el orden fijo de integración que dio el orquestador
(`caso_0010_mp_carpeta` → `caso_0011_mod_ficha_obra` → `caso_0013_mp_mercado` → esta; plan,
«Cambios por el diseño de módulos», Migraciones). `caso_0012_mp_medicion` (T9) aún no existe: si
entra después, el orquestador ajusta la cadena al integrar.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0014_mp_aprobacion"
down_revision = "caso_0013_mp_mercado"
branch_labels = None
depends_on = None

TABLA = "mp_aprobacion_evento"


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen (como `caso_0009_s3_paquete`)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    if TABLA in _faltan(TABLA):
        op.create_table(
            TABLA,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("proyecto_id", sa.Integer, nullable=False),
            sa.Column("tipo", sa.String(10), nullable=False),
            sa.Column("version", sa.String(40), nullable=False),
            sa.Column("huella_version", sa.String(64), nullable=False),
            sa.Column("resultado", sa.String(30), nullable=True),
            sa.Column("notas", sa.String(2000), nullable=False),
            sa.Column("usuario", sa.String(200), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
            sa.Column("armo", sa.Boolean, nullable=False),
            sa.Column("cierre_de", sa.Integer, nullable=True),
            sa.Column("anterior", sa.String(64), nullable=False),
            sa.Column("huella", sa.String(64), nullable=False),
            sa.UniqueConstraint("cierre_de", name="uq_mp_aprobacion_cierre"),
            sa.UniqueConstraint("proyecto_id", "anterior", name="uq_mp_aprobacion_anterior"),
        )


def downgrade() -> None:
    if TABLA in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table(TABLA)
