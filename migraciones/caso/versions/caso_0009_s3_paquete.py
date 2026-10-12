"""S3-3 (T14): `paq_recibido` y `paq_dictamen`, lo que recibe y dictamina quien revisa (S3 §8.3).

Tablas aditivas de `paquete/modelo.py` en la base del caso, sin clave foránea a `core.models`: el
archivo recibido se guarda en la carpeta de paquetes y aquí quedan su SHA-256 (único), su estado de
verificación y la cadena que traía; el dictamen queda atado al SHA-256 del archivo y al estado de
ese momento. Ninguna tabla existente cambia. Escrita a mano como `caso_0008_s3_cadena`: una base
que ya las trae (creada con `create_all` desde `paquete.modelo.crear_esquema_paquete`) se adopta
sin recrearlas.

`down_revision` es la cabeza real del destino `caso` (`caso_0008_s3_cadena`); el plan la llamaba
`caso_0008_s3_paquete` colgada de `caso_0007_s3_cadena`, nombres que ya no existen.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0009_s3_paquete"
down_revision = "caso_0008_s3_cadena"
branch_labels = None
depends_on = None

TABLAS = ("paq_recibido", "paq_dictamen")


def _faltan(*tablas: str) -> set[str]:
    """Las tablas que aún no existen: una base sembrada con `create_all` del código 0.8.0 ya las
    trae y se adopta sin recrearlas; las que faltan se crean con `op.create_table`."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    return {tabla for tabla in tablas if tabla not in existentes}


def upgrade() -> None:
    faltan = _faltan(*TABLAS)
    if "paq_recibido" in faltan:
        op.create_table(
            "paq_recibido",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("archivo", sa.String(255), nullable=False),
            sa.Column("huella_archivo", sa.String(64), nullable=False, unique=True),
            sa.Column("paquete_id", sa.String(36), nullable=False),
            sa.Column("destinatario", sa.String(200), nullable=False),
            sa.Column("ruta", sa.String(500), nullable=False),
            sa.Column("empresa_declarada", sa.String(200), nullable=False),
            sa.Column("empresa_verificada", sa.String(200), nullable=False),
            sa.Column("huella_clave", sa.String(64), nullable=False),
            sa.Column("estado", sa.String(20), nullable=False),
            sa.Column("proyecto", sa.String(200), nullable=False),
            sa.Column("codigo", sa.String(40), nullable=False),
            sa.Column("emitido", sa.DateTime, nullable=False),
            sa.Column("cadena", sa.Text, nullable=False),
            sa.Column("huellas_anexos", sa.Text, nullable=False),
            sa.Column("recibido_por", sa.String(120), nullable=False),
            sa.Column("fecha", sa.DateTime, nullable=False),
        )
    if "paq_dictamen" in faltan:
        op.create_table(
            "paq_dictamen",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("paquete_id", sa.Integer, sa.ForeignKey("paq_recibido.id"), nullable=False),
            sa.Column("huella_archivo", sa.String(64), nullable=False),
            sa.Column("resultado", sa.String(20), nullable=False),
            sa.Column("notas", sa.Text, nullable=False),
            sa.Column("usuario", sa.String(120), nullable=False),
            sa.Column("fecha", sa.DateTime, nullable=False),
            sa.Column("estado_verificacion", sa.String(20), nullable=False),
            sa.Column("revisor_armo", sa.Boolean, nullable=False),
        )


def downgrade() -> None:
    presentes = set(sa.inspect(op.get_bind()).get_table_names())
    for tabla in reversed(TABLAS):  # primero el dictamen, que depende del recibido
        if tabla in presentes:
            op.drop_table(tabla)
