"""F5 vial, tarea 3: `apu_desperdicio_guardado` y `apu_desperdicio`, la traza del desperdicio.

Tablas aditivas de `aplicacion/tablas_desperdicio.py`, sin clave foránea a `core.models`; ninguna
tabla existente cambia. El desperdicio va dentro de la cantidad de la línea del APU (el núcleo no
cambia); aquí quedan la cantidad neta y el porcentaje. Solo inserción: guardar otra vez la
composición de una partida es otra fila del guardado y al leer manda la última. Las cifras son
texto de 40 (`DecimalExacto`). Una base que ya trae alguna de las dos (creada con `create_all`
desde `crear_esquema_desperdicio`, al guardar en una base sin migrar) se adopta sin recrearla.

Cuelga de `caso_0021_vial_transporte`, la cabeza cuando se escribió. Si otra línea creó su propia
`caso_0022`, se renumera según la cabeza real al integrar.

Cuidado al bajar (`downgrade`): borra las dos tablas y con ellas la traza (la cantidad con
desperdicio sigue en las líneas del APU). Quien baje debe tener el respaldo previo que
`preparar_base` deja antes de migrar.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0022_apu_desperdicio"
down_revision = "caso_0021_vial_transporte"
branch_labels = None
depends_on = None

GUARDADO = "apu_desperdicio_guardado"
LINEA = "apu_desperdicio"


def _faltan(*tablas: str) -> set[str]:
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    faltan = _faltan(GUARDADO, LINEA)
    if GUARDADO in faltan:
        op.create_table(
            GUARDADO,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("partida_codigo", sa.String(64), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
        )
        op.create_index("ix_apu_desperdicio_guardado_partida", GUARDADO, ["partida_codigo"])
    if LINEA in faltan:
        op.create_table(
            LINEA,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("guardado_id", sa.Integer, nullable=False),
            sa.Column("orden", sa.Integer, nullable=False),
            sa.Column("descripcion", sa.String(300), nullable=False),
            sa.Column("unidad", sa.String(40), nullable=False),
            sa.Column("cantidad_neta", sa.String(40), nullable=False),
            sa.Column("desperdicio_pct", sa.String(40), nullable=False),
            sa.Column("cantidad", sa.String(40), nullable=False),
        )
        op.create_index("ix_apu_desperdicio_guardado", LINEA, ["guardado_id"])


def downgrade() -> None:
    for tabla in (LINEA, GUARDADO):
        if tabla not in _faltan(tabla):
            op.drop_table(tabla)
