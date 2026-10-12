"""S3-2 (SL-E7): `eslabon_version`, el registro encadenado con huellas (spec S3 §6.2 y §7.4).

Tabla aditiva de `core/models/cadena.py`: una fila por versión con la huella de su contenido, de
sus `RegistroCambio`, de sus anexos y del eslabón anterior **del mismo proyecto**. El índice
único (`proyecto_id`, `anterior`) es la salvaguarda de la concurrencia (S3 §6.3). Ninguna tabla
existente cambia. Escrita a mano como `caso_0002` a `caso_0007`: las bases que los sembradores y
las pruebas crean con `create_all` ya la traen y se adoptan sin recrearla. Las versiones que ya
existían se sellan después, una vez y de forma retroactiva y declarada
(`core.budget.cadena.sellar_historial`), no aquí: una migración no inventa quién las guardó.

`down_revision` es la cabeza del destino `caso` antes de crearla (`caso_0007_s4_asistente`; el
plan la llamaba `caso_0007_s3_cadena` colgada de `caso_0006_s2_decision`, pero S4 llegó antes).
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0008_s3_cadena"
down_revision = "caso_0007_s4_asistente"
branch_labels = None
depends_on = None

TABLAS = ("eslabon_version",)


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen: una base sembrada con `create_all` del código 0.8.0 ya las
    trae y se adopta sin recrearlas; las que faltan se crean con `op.create_table`."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    if not _faltan(*TABLAS):
        return
    op.create_table(
        "eslabon_version",
        sa.Column(
            "presupuesto_id",
            sa.Integer,
            sa.ForeignKey("presupuesto.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "proyecto_id",
            sa.Integer,
            sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("anterior", sa.String(64), nullable=False),
        sa.Column("huella_contenido", sa.String(64), nullable=False),
        sa.Column("huella_cambios", sa.String(64), nullable=False),
        sa.Column("huella_anexos", sa.String(64), nullable=False),
        sa.Column("huella_eslabon", sa.String(64), nullable=False),
        sa.Column("usuario", sa.String(120), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("version_formato", sa.Integer, nullable=False),
    )
    op.create_index(
        "uq_eslabon_proyecto_anterior", "eslabon_version", ["proyecto_id", "anterior"], unique=True
    )


def downgrade() -> None:
    presentes = set(sa.inspect(op.get_bind()).get_table_names())
    for tabla in reversed(TABLAS):
        if tabla in presentes:
            op.drop_table(tabla)
