"""G4 #5 (2026-11-27): `solicitud_cuenta.resuelta_por_id`, clave foránea a `usuario.id`.

Una aprobación no sobrevive a quien la dio: al aprobar o rechazar se guarda `resuelta_por_id` y al
canjear el código se exige que esa cuenta siga activa y con el rol de administrador. Columna
aditiva al final de `solicitud_cuenta`, nula en solicitudes pendientes o anteriores a esta
revisión. SQLite no agrega una clave foránea con `ALTER TABLE`, así que la tabla se recrea en lote
(como `ins_0012`), conservando filas y la unicidad de `login`. Una base que ya trae la columna
(creada con `create_all`) se adopta sin recrearla. Al bajar se quitan la columna y su clave
foránea (DA-S5-6: la bajada nunca se ofrece al usuario).

El respaldo previo lo hace `operacion.base_datos` antes de cualquier revisión.

`down_revision` es `ins_0015_notificacion_por_evento`, la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0016_solicitud_resuelta_por"
down_revision = "ins_0015_notificacion_por_evento"
branch_labels = None
depends_on = None

TABLA = "solicitud_cuenta"
COLUMNA = "resuelta_por_id"
FK = "fk_solicitud_cuenta_resuelta_por_id"


def _tiene_columna() -> bool:
    return COLUMNA in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(TABLA)}


def upgrade() -> None:
    if _tiene_columna():
        return
    with op.batch_alter_table(TABLA, recreate="always") as lote:
        lote.add_column(
            sa.Column(
                COLUMNA,
                sa.Integer,
                sa.ForeignKey("usuario.id", name=FK),
                nullable=True,
            )
        )


def downgrade() -> None:
    if not _tiene_columna():
        return
    with op.batch_alter_table(TABLA, recreate="always") as lote:
        lote.drop_column(COLUMNA)
