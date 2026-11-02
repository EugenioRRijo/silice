"""MP-3 (Tarea 9): `mp_nota_medicion`, las notas de medición de los renglones de la Hoja.

Una fila por renglón agregado a mano que trae nota, por obra, versión y clave del renglón
(«OBRA-04|a-mano:1»); una sola nota por renglón de una versión. Tabla aditiva de
`aplicacion/tablas_medicion.py`, sin clave foránea a `core.models`; ninguna tabla existente cambia.
Una base que ya la trae (creada con `create_all` desde `crear_esquema_medicion`, o por el guardado
de una base sin migrar) se adopta sin recrearla.

El número no es el orden: `down_revision` es `caso_0014_mp_aprobacion`, la cabeza cuando se integró
(plan, «Cambios por el diseño de módulos», Migraciones: `caso_0010_mp_carpeta` →
`caso_0011_mod_ficha_obra` → `caso_0013_mp_mercado` → `caso_0014_mp_aprobacion` → esta).
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0012_mp_medicion"
down_revision = "caso_0014_mp_aprobacion"
branch_labels = None
depends_on = None

TABLA = "mp_nota_medicion"


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
            sa.Column("version", sa.String(40), nullable=False),
            sa.Column("clave", sa.String(200), nullable=False),
            sa.Column("nota", sa.String(500), nullable=False),
            sa.UniqueConstraint("proyecto_id", "version", "clave", name="uq_mp_nota_medicion"),
        )


def downgrade() -> None:
    if TABLA in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table(TABLA)
