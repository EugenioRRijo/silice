"""F5 vial, tarea 2: la columna `transporte` de `vial_tramo`, la convención del transporte.

Aditiva y nullable: nula es t·km, la convención de siempre, así los tramos guardados antes se leen
igual. «banda» es el transporte medido en t con la distancia como banda en la descripción de la
partida (diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §5). Una base
cuya `vial_tramo` ya trae la columna (creada con `create_all` desde `crear_esquema_vial`, al
guardar los primeros tramos en una base sin migrar) se adopta sin tocarla; una sin la tabla no
cambia aquí (la crea el primer guardado, ya con la columna).

Cuelga de `caso_0020_hoja_importaciones`, la cabeza cuando se escribió. Si otra línea creó su
propia `caso_0021`, se renumera según la cabeza real al integrar.

Al bajar (`downgrade`) se pierde la convención de cada tramo guardado: vuelven a leerse en t·km.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0021_vial_transporte"
down_revision = "caso_0020_hoja_importaciones"
branch_labels = None
depends_on = None

TABLA = "vial_tramo"
COLUMNA = "transporte"


def _columnas() -> set[str] | None:
    """Las columnas de `vial_tramo`, o `None` si la tabla no existe."""
    inspector = sa.inspect(op.get_bind())
    if TABLA not in inspector.get_table_names():
        return None
    return {c["name"] for c in inspector.get_columns(TABLA)}


def upgrade() -> None:
    columnas = _columnas()
    if columnas is not None and COLUMNA not in columnas:
        with op.batch_alter_table(TABLA) as tabla:
            tabla.add_column(sa.Column(COLUMNA, sa.String(10), nullable=True))


def downgrade() -> None:
    columnas = _columnas()
    if columnas is not None and COLUMNA in columnas:
        with op.batch_alter_table(TABLA) as tabla:
            tabla.drop_column(COLUMNA)
