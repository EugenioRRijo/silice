"""Plan vial, Tarea 19: `modulo_cambio`, el estado de los módulos activables de la instalación.

Una fila por cambio (clave, activo, usuario, registrado); nunca se sobrescribe. Sin filas todos los
módulos están activos, así que subir no cambia el comportamiento de ninguna instalación. Tabla
aditiva de `aplicacion/tablas_modulos.py`; nada existente cambia. Una base que ya la trae (creada
con `create_all`) se adopta sin recrearla. Al bajar se borra la tabla (DA-S5-6: la bajada nunca se
ofrece al usuario).

`down_revision` es `ins_0009_prod_publicacion`, la cabeza de la instalación al escribirla (el plan
decía `ins_0008_prod_calculo`: la Tarea 4b añadió la 0009 antes).
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0010_modulo"
down_revision = "ins_0009_prod_publicacion"
branch_labels = None
depends_on = None

TABLA = "modulo_cambio"


def upgrade() -> None:
    if TABLA in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        TABLA,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("clave", sa.String(40), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False),
        sa.Column("usuario", sa.String(200), nullable=False),
        sa.Column("registrado", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    if TABLA not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.drop_table(TABLA)
