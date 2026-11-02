"""Plan vial, Tarea 3: `prod_receta`, `prod_receta_componente` y el movimiento `consumo`.

La receta de la planta (qué lleva una tonelada de mezcla) se guarda como registros que no se
sobrescriben: una receta nueva es otra fila. Producir con receta registra, además de la entrada del
producto, un `consumo` por cada componente propio; por eso el `CHECK` de `prod_movimiento.tipo`
admite `consumo`. Tablas aditivas; lo único que cambia de lo existente es ese `CHECK`, y ninguna fila
se toca. Una base que ya trae las tablas o el `CHECK` nuevo (creada con `create_all`) se adopta sin
recrear nada. Al bajar se borran los movimientos `consumo` (con el `CHECK` viejo no caben) y las
dos tablas.

`down_revision` es `ins_0006_prod_costo`, la cabeza de la instalación al escribirla.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0007_prod_receta"
down_revision = "ins_0006_prod_costo"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de produccion.modelo.Cantidad
MOVIMIENTO = "prod_movimiento"
CK_TIPO = "ck_prod_movimiento_tipo"
TIPOS_ANTES = "tipo IN ('entrada', 'despacho', 'ajuste')"
TIPOS_AHORA = "tipo IN ('entrada', 'despacho', 'ajuste', 'consumo')"


def _admite_consumo() -> bool:
    for ck in sa.inspect(op.get_bind()).get_check_constraints(MOVIMIENTO):
        if ck.get("name") == CK_TIPO:
            return "consumo" in ck["sqltext"]
    return False


def _cambiar_tipos(nuevo: str) -> None:
    with op.batch_alter_table(MOVIMIENTO, recreate="always") as lote:
        lote.drop_constraint(CK_TIPO, type_="check")
        lote.create_check_constraint(CK_TIPO, nuevo)


def upgrade() -> None:
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    if "prod_receta" not in existentes:
        op.create_table(
            "prod_receta",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("producto", sa.String(40), nullable=False),
            sa.Column("fuente", sa.String(200), nullable=False),
            sa.Column("vigente_desde", sa.Date, nullable=False),
            sa.Column("usuario", sa.String(120), nullable=False),
            sa.Column("registrado", sa.DateTime, nullable=False),
        )
        op.create_index("ix_prod_receta_producto", "prod_receta", ["producto"])
    if "prod_receta_componente" not in existentes:
        op.create_table(
            "prod_receta_componente",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("receta_id", sa.Integer, sa.ForeignKey("prod_receta.id"), nullable=False),
            sa.Column("orden", sa.Integer, nullable=False),
            sa.Column("codigo", sa.String(40), nullable=False),
            sa.Column("cantidad_por_t", DEC, nullable=False),
            sa.Column("unidad", sa.String(1), nullable=False),
            sa.Column("tipo", sa.String(8), nullable=False),
            sa.CheckConstraint("unidad IN ('t', 'l')", name="ck_prod_receta_componente_unidad"),
            sa.CheckConstraint(
                "tipo IN ('propio', 'comprado')", name="ck_prod_receta_componente_tipo"
            ),
        )
        op.create_index(
            "ix_prod_receta_componente_receta_id", "prod_receta_componente", ["receta_id"]
        )
    if not _admite_consumo():
        _cambiar_tipos(TIPOS_AHORA)


def downgrade() -> None:
    if _admite_consumo():
        op.execute(sa.text(f"DELETE FROM {MOVIMIENTO} WHERE tipo = 'consumo'"))
        _cambiar_tipos(TIPOS_ANTES)
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    if "prod_receta_componente" in existentes:
        op.drop_index("ix_prod_receta_componente_receta_id", "prod_receta_componente")
        op.drop_table("prod_receta_componente")
    if "prod_receta" in existentes:
        op.drop_index("ix_prod_receta_producto", "prod_receta")
        op.drop_table("prod_receta")
