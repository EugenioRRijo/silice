"""C9a (2026-11-26): `solicitud_cuenta` y `usuario.correo`, el registro con código de 20 caracteres.

Una persona pide una cuenta con su nombre, su correo, su usuario y su contraseña; Sílice guarda una
**solicitud**, no una cuenta (spec `2026-11-26-registro-con-codigo` §2 y §3). El administrador la
aprueba con un papel y le da un código de un solo uso; al canjearlo nace el `usuario`, que ahora
guarda el correo. Tabla aditiva y columna aditiva al final de `usuario`, nula y con `''` por
omisión: las cuentas de hoy quedan con el correo vacío y nada existente cambia. Una base que ya las
trae (creada con `create_all`) se adopta sin tocarlas. Al bajar se borran la tabla y la columna
(DA-S5-6: la bajada nunca se ofrece al usuario); la columna se quita con `ALTER TABLE ... DROP
COLUMN` (SQLite 3.35 o más), sin recrear `usuario`, a la que apuntan `sesion` y `evento_acceso`.

El respaldo previo lo hace `operacion.base_datos` antes de cualquier revisión.

`down_revision` es `ins_0012_conteo_anulado`, la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0013_solicitud_cuenta"
down_revision = "ins_0012_conteo_anulado"
branch_labels = None
depends_on = None

TABLA = "solicitud_cuenta"
CUENTAS = "usuario"
COLUMNA = "correo"


def _tablas() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _tiene_correo() -> bool:
    return COLUMNA in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(CUENTAS)}


def upgrade() -> None:
    if not _tiene_correo():
        op.add_column(
            CUENTAS,
            sa.Column(COLUMNA, sa.String(254), nullable=True, server_default=sa.text("''")),
        )
    if TABLA in _tablas():
        return
    op.create_table(
        TABLA,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("login", sa.String(60), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("correo", sa.String(254), nullable=False),
        sa.Column("huella_clave", sa.String(200), nullable=False),
        sa.Column("creada", sa.DateTime, nullable=False),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("papel", sa.String(20), nullable=True),
        sa.Column("huella_codigo", sa.String(64), nullable=True),
        sa.Column("vence", sa.DateTime, nullable=True),
        sa.Column("resuelta_por", sa.String(120), nullable=False),
        sa.UniqueConstraint("login"),
    )


def downgrade() -> None:
    if TABLA in _tablas():
        op.drop_table(TABLA)
    if _tiene_correo():
        op.execute(f"ALTER TABLE {CUENTAS} DROP COLUMN {COLUMNA}")
