"""Tanda 2026-11-19: `prod_movimiento.anula_id` y `prod_movimiento.motivo`, la anulacion de un conteo.

Un conteo fisico cierra el pasado de su material (prueba en vivo 2026-11-18) y uno mal hecho no
tenia vuelta. Se anula como en los ERP y como `prod_costo`: nada se borra; la anulacion es un
ajuste nuevo con la cantidad contraria, `anula_id` apuntando al conteo (unico: se anula una vez) y
el motivo. Columnas aditivas al final; los movimientos anteriores quedan sin anulacion (`anula_id`
nulo, `motivo` vacio). SQLite no agrega una clave foranea con `ALTER TABLE`, asi que la tabla se
recrea en lote (como `ins_0007`), conservando filas, `CHECK` y el ticket unico. Una base que ya
trae las columnas (creada con `create_all`) se adopta sin tocarla. Al bajar se quitan las
columnas; las filas de anulacion quedan como ajustes y la existencia no cambia (DA-S5-6: la
bajada nunca se ofrece al usuario).

El respaldo previo lo hace `operacion.base_datos` antes de cualquier revision.

`down_revision` es `ins_0011_receta_ligante`, la cabeza de la instalacion al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0012_conteo_anulado"
down_revision = "ins_0011_receta_ligante"
branch_labels = None
depends_on = None

TABLA = "prod_movimiento"
INDICE = "ix_prod_movimiento_anula_id"


def _tiene_columna() -> bool:
    return "anula_id" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLA)}


def upgrade() -> None:
    if _tiene_columna():
        return
    with op.batch_alter_table(TABLA, recreate="always") as lote:
        lote.add_column(
            sa.Column(
                "anula_id",
                sa.Integer,
                sa.ForeignKey(f"{TABLA}.id", name="fk_prod_movimiento_anula_id"),
                nullable=True,
            )
        )
        lote.add_column(
            sa.Column("motivo", sa.String(300), nullable=False, server_default=sa.text("''"))
        )
    op.create_index(INDICE, TABLA, ["anula_id"], unique=True)


def downgrade() -> None:
    if not _tiene_columna():
        return
    op.drop_index(INDICE, TABLA)
    with op.batch_alter_table(TABLA, recreate="always") as lote:
        lote.drop_column("motivo")
        lote.drop_column("anula_id")
