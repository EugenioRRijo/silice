"""Mejora de la DS-81: `riesgo_mapa_guardado` y `riesgo_mapa_serie`, la serie que mueve cada insumo.

Tablas aditivas de `aplicacion/tablas_riesgo.py`, sin clave foránea a `core.models`; ninguna tabla
existente cambia. «Riesgo de la obra» guarda aquí el último mapa de series que se usó en cada
versión para precargar el selector al volver. Solo inserción: guardar otro mapa es otra fila del
guardado y al leer manda el último. Una base que ya trae alguna de las dos (creada con `create_all`
desde `crear_esquema_riesgo`, al guardar en una base sin migrar) se adopta sin recrearla.

Cuelga de `caso_0022_apu_desperdicio`, la cabeza cuando se escribió. Si otra línea creó su propia
`caso_0023`, se renumera según la cabeza real al integrar.

Cuidado al bajar (`downgrade`): borra las dos tablas y con ellas los mapas recordados (la proyección
no cambia: el mapa se vuelve a elegir en la pantalla). Quien baje debe tener el respaldo previo que
`preparar_base` deja antes de migrar.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0023_riesgo_mapa"
down_revision = "caso_0022_apu_desperdicio"
branch_labels = None
depends_on = None

GUARDADO = "riesgo_mapa_guardado"
SERIE = "riesgo_mapa_serie"


def _faltan(*tablas: str) -> set[str]:
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    faltan = _faltan(GUARDADO, SERIE)
    if GUARDADO in faltan:
        op.create_table(
            GUARDADO,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("version_id", sa.Integer, nullable=False),
            sa.Column("usuario", sa.String(200), nullable=False),
            sa.Column("fecha_hora", sa.DateTime, nullable=False),
        )
        op.create_index("ix_riesgo_mapa_guardado_version", GUARDADO, ["version_id"])
    if SERIE in faltan:
        op.create_table(
            SERIE,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("guardado_id", sa.Integer, nullable=False),
            sa.Column("insumo", sa.String(500), nullable=False),
            sa.Column("serie", sa.String(40), nullable=False),
        )
        op.create_index("ix_riesgo_mapa_serie_guardado", SERIE, ["guardado_id"])


def downgrade() -> None:
    for tabla in (SERIE, GUARDADO):
        if tabla not in _faltan(tabla):
            op.drop_table(tabla)
