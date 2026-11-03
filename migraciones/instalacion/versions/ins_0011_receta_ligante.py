"""Plan vial, Tarea 16c: `prod_receta_componente.es_ligante`, la marca del ligante en la receta.

Eugenio respondió (fila 109) que las recetas de la planta compran otros materiales por tonelada
(arena, filler), así que VR2 no puede suponer que el único comprado en t es el ligante. La receta
lleva una marca opcional por componente. Columna aditiva, `NOT NULL DEFAULT 0`: las recetas
anteriores quedan sin marca y se comportan como antes. Una base que ya trae la columna (creada con
`create_all`) se adopta sin tocarla. Al bajar se quita la columna (DA-S5-6: la bajada nunca se
ofrece al usuario).

`down_revision` es `ins_0010_modulo`, la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0011_receta_ligante"
down_revision = "ins_0010_modulo"
branch_labels = None
depends_on = None

TABLA = "prod_receta_componente"
COLUMNA = "es_ligante"


def _tiene_columna() -> bool:
    return COLUMNA in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLA)}


def upgrade() -> None:
    if _tiene_columna():
        return
    op.add_column(
        TABLA,
        sa.Column(COLUMNA, sa.Boolean, nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    if not _tiene_columna():
        return
    with op.batch_alter_table(TABLA) as lote:
        lote.drop_column(COLUMNA)
