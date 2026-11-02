"""S4-3: las tablas de la arenera en la base de la instalacion (RT-S4-1; RF-127 a RF-136).

Materiales, movimientos de inventario y bandeja de pesajes sospechosos de la bascula. La arenera
es de la empresa, no de un caso: por eso viven en `instalacion.db`, junto a las cuentas. Las
cantidades son texto exacto (`DEC`), nunca `float`.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0002_produccion"
down_revision = "ins_0001_seguridad"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de produccion.modelo.Cantidad


def upgrade() -> None:
    op.create_table(
        "prod_material",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("codigo", sa.String(40), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("unidad_venta", sa.String(2), nullable=False),
        sa.Column("densidad_t_m3", DEC, nullable=True),
        sa.Column("existencia_minima", DEC, nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False),
        sa.CheckConstraint("unidad_venta IN ('m3', 't')", name="ck_prod_material_unidad"),
        sa.UniqueConstraint("codigo"),
    )
    op.create_table(
        "prod_movimiento",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("material_id", sa.Integer, sa.ForeignKey("prod_material.id"), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("cantidad", DEC, nullable=False),
        sa.Column("ticket", sa.String(60), nullable=True),
        sa.Column("placa", sa.String(20), nullable=False),
        sa.Column("cliente", sa.String(120), nullable=False),
        sa.Column("nota", sa.String(300), nullable=False),
        sa.Column("origen", sa.String(10), nullable=False),
        sa.Column("usuario", sa.String(120), nullable=False),
        sa.Column("registrado", sa.DateTime, nullable=False),
        sa.UniqueConstraint("ticket", name="uq_prod_movimiento_ticket"),
        sa.CheckConstraint(
            "tipo IN ('entrada', 'despacho', 'ajuste')", name="ck_prod_movimiento_tipo"
        ),
        sa.CheckConstraint("origen IN ('manual', 'bascula')", name="ck_prod_movimiento_origen"),
        sa.CheckConstraint("length(cantidad) > 0", name="ck_prod_movimiento_cantidad"),
    )
    op.create_index("ix_prod_movimiento_material_id", "prod_movimiento", ["material_id"])
    op.create_table(
        "prod_pesaje_sospechoso",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("huella_archivo", sa.String(64), nullable=False),
        sa.Column("fila", sa.Integer, nullable=False),
        sa.Column("ticket", sa.String(60), nullable=False),
        sa.Column("fecha_texto", sa.String(60), nullable=False),
        sa.Column("placa", sa.String(20), nullable=False),
        sa.Column("material_texto", sa.String(120), nullable=False),
        sa.Column("bruto_texto", sa.String(60), nullable=False),
        sa.Column("tara_texto", sa.String(60), nullable=False),
        sa.Column("neto_texto", sa.String(60), nullable=False),
        sa.Column("motivo", sa.String(200), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False),
        sa.Column("resuelto_por", sa.String(120), nullable=True),
        sa.Column("resuelto_en", sa.DateTime, nullable=True),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'resuelto', 'descartado')",
            name="ck_prod_pesaje_sospechoso_estado",
        ),
    )
    op.create_index(
        "ix_prod_pesaje_sospechoso_huella_archivo", "prod_pesaje_sospechoso", ["huella_archivo"]
    )


def downgrade() -> None:
    op.drop_index("ix_prod_pesaje_sospechoso_huella_archivo", "prod_pesaje_sospechoso")
    op.drop_table("prod_pesaje_sospechoso")
    op.drop_index("ix_prod_movimiento_material_id", "prod_movimiento")
    op.drop_table("prod_movimiento")
    op.drop_table("prod_material")
