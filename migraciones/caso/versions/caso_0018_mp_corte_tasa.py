"""MP-7 (Tarea D2): el rastro de la conversión de un precio del corte en `mp_precio_corte`.

Un precio declarado en otra moneda que la obra se convierte con la tasa del BCV de su fecha
(decisión de Eugenio del 2026-10-27). La fila sigue llevando en `precio` y `moneda` lo que el
control usa (el resultado, en la moneda de la obra) y gana cinco columnas, todas con nulo, para que
quien revise reconstruya la cuenta: `moneda_original`, `precio_original`, `tasa` (Bs por USD),
`fecha_tasa` y `fuente_tasa`. Un precio que ya estaba en la moneda de la obra las deja en nulo, y
las filas que ya existían también (nunca se convirtió ninguna). Aditiva: ninguna columna ni tabla
existente cambia. Una base que ya trae las columnas (creada con `crear_esquema_corte`) se adopta sin
agregarlas otra vez.

Cuelga de `caso_0017_mp_corte`, la cabeza cuando se escribió.

Cuidado al bajar (`downgrade`): quita las cinco columnas y, con ellas, el rastro de toda conversión
(precio original, moneda original, tasa, su fecha y su fuente). Los precios convertidos en `precio`
y `moneda` se conservan y siguen siendo los que usa el control, pero ya no se puede reconstruir de
dónde salieron. Quien baje debe tener el respaldo previo que `preparar_base` deja antes de migrar.
"""

import sqlalchemy as sa
from alembic import op

revision = "caso_0018_mp_corte_tasa"
down_revision = "caso_0017_mp_corte"
branch_labels = None
depends_on = None

TABLA = "mp_precio_corte"
#: Las columnas del rastro, en orden (como `PrecioDelCorte`).
COLUMNAS = (
    ("moneda_original", sa.String(10)),
    ("precio_original", sa.String(40)),
    ("tasa", sa.String(40)),
    ("fecha_tasa", sa.Date),
    ("fuente_tasa", sa.String(300)),
)


def _existentes() -> set[str]:
    """Las columnas que `mp_precio_corte` ya tiene (vacío si la tabla no existe)."""
    inspector = sa.inspect(op.get_bind())
    if TABLA not in inspector.get_table_names():
        return set()
    return {columna["name"] for columna in inspector.get_columns(TABLA)}


def upgrade() -> None:
    existentes = _existentes()
    if not existentes:
        return
    for nombre, tipo in COLUMNAS:
        if nombre not in existentes:
            op.add_column(TABLA, sa.Column(nombre, tipo, nullable=True))


def downgrade() -> None:
    existentes = _existentes()
    sobran = [nombre for nombre, _ in COLUMNAS if nombre in existentes]
    if not sobran:
        return
    with op.batch_alter_table(TABLA) as lote:
        for nombre in sobran:
            lote.drop_column(nombre)
