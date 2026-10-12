"""S3-1: las tablas de `seguridad` en la base de la instalación (RF-80, RF-84; spec S3 §7.4).

Revisión base del destino `instalacion` (`down_revision = None`): la base de la instalación no
existía antes de S3. Cuentas, intentos, fichas de sesión, registro de accesos, código de
instalación, empresa propia, clave de firma, empresas registradas y claves de API.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0001_seguridad"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("login", sa.String(60), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("huella_clave", sa.String(200), nullable=False),
        sa.Column("roles", sa.String(60), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False),
        sa.Column("debe_cambiar_clave", sa.Boolean, nullable=False),
        sa.Column("restablecida_por_admin", sa.Boolean, nullable=False),
        sa.Column("creado", sa.DateTime, nullable=False),
        sa.Column("creado_por", sa.String(120), nullable=False),
        sa.UniqueConstraint("login"),
    )
    op.create_table(
        "intento_acceso",
        sa.Column("login_normalizado", sa.String(60), primary_key=True),
        sa.Column("fallos_seguidos", sa.Integer, nullable=False),
        sa.Column("bloqueado_hasta", sa.DateTime, nullable=True),
        sa.Column("ultimo_fallo", sa.DateTime, nullable=True),
    )
    op.create_table(
        "sesion",
        sa.Column("huella_ficha", sa.String(64), primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("creada", sa.DateTime, nullable=False),
        sa.Column("ultima_actividad", sa.DateTime, nullable=False),
        sa.Column("cerrada", sa.Boolean, nullable=False),
        sa.Column("motivo_cierre", sa.String(40), nullable=False),
    )
    op.create_table(
        "evento_acceso",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
        sa.Column("login_intentado", sa.String(60), nullable=False),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("ip_cliente", sa.String(64), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("detalle", sa.Text, nullable=False),
    )
    op.create_table(
        "codigo_instalacion",
        sa.Column("huella", sa.String(64), primary_key=True),
        sa.Column("creado", sa.DateTime, nullable=False),
        sa.Column("usado", sa.DateTime, nullable=True),
        sa.Column("motivo", sa.String(20), nullable=False),
    )
    op.create_table(
        "empresa_propia",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("rif", sa.String(20), nullable=False),
        sa.Column("ciudad", sa.String(80), nullable=False),
        sa.Column("actualizada", sa.DateTime, nullable=False),
        sa.Column("actualizada_por", sa.String(120), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_empresa_propia_unica"),
    )
    op.create_table(
        "clave_empresa",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("publica", sa.LargeBinary, nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("privada_cifrada", sa.LargeBinary, nullable=True),
        sa.Column("kdf", sa.String(160), nullable=True),
        sa.Column("sal", sa.LargeBinary, nullable=True),
        sa.Column("nonce", sa.LargeBinary, nullable=True),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("creada", sa.DateTime, nullable=False),
        sa.Column("creada_por", sa.String(120), nullable=False),
        sa.Column("fecha_estado", sa.DateTime, nullable=True),
        sa.Column("motivo", sa.String(300), nullable=False),
    )
    op.create_table(
        "empresa_registrada",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa", sa.String(200), nullable=False),
        sa.Column("rif", sa.String(20), nullable=False),
        sa.Column("publica", sa.LargeBinary, nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("comprobada_con", sa.String(200), nullable=False),
        sa.Column("metodo", sa.String(20), nullable=False),
        sa.Column("fecha_comprobacion", sa.DateTime, nullable=False),
        sa.Column("registrada_por", sa.String(120), nullable=False),
        sa.Column("fecha_estado", sa.DateTime, nullable=True),
        sa.Column("motivo", sa.String(300), nullable=False),
    )
    op.create_table(
        "clave_api",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("identificador", sa.String(8), nullable=False),
        sa.Column("huella_secreto", sa.String(64), nullable=False),
        sa.Column("creada", sa.DateTime, nullable=False),
        sa.Column("creada_por", sa.String(120), nullable=False),
        sa.Column("ultimo_uso", sa.DateTime, nullable=True),
        sa.Column("revocada", sa.Boolean, nullable=False),
        sa.UniqueConstraint("identificador"),
    )


def downgrade() -> None:
    for tabla in (
        "clave_api", "empresa_registrada", "clave_empresa", "empresa_propia",
        "codigo_instalacion", "evento_acceso", "sesion", "intento_acceso", "usuario",
    ):
        op.drop_table(tabla)
