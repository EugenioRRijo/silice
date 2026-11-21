"""Mejora de A.6 (acta DS-48g, opción A): quién guardó el desglose del desperdicio.

`apu_desperdicio_guardado` gana `responsable` (`Nombre <login>` de la sesión, RF-82; 120, como el
responsable del registro de cambios), con nulo: lo guardado antes de migrar no sabe quién lo hizo y
queda en nulo, igual que lo que se guarde con la clave de API (sin cuenta). Aditiva: ninguna otra
columna ni tabla cambia. Una base que ya trae la columna (creada con `crear_esquema_desperdicio`, al
guardar la primera traza en una base sin migrar) se adopta sin agregarla otra vez.

Cuelga de `ANTERIOR`, `caso_0023_riesgo_mapa`. Se escribió sobre `caso_0022_apu_desperdicio` y se
re-encadenó al unir las dos ramas del sprint 1120b (la constante y la de su prueba,
`tests/integration/test_migracion_desperdicio_responsable.py`).

Cuidado al bajar (`downgrade`): quita la columna y, con ella, quién guardó cada desglose; las trazas
y sus horas se conservan. Quien baje debe tener el respaldo previo que `preparar_base` deja antes de
migrar.
"""

import sqlalchemy as sa
from alembic import op

#: La revisión de la que cuelga esta (ver la cabecera).
ANTERIOR = "caso_0023_riesgo_mapa"

revision = "caso_0024_desperdicio_responsable"
down_revision = ANTERIOR
branch_labels = None
depends_on = None

TABLA = "apu_desperdicio_guardado"
COLUMNA = "responsable"


def _columnas() -> set[str]:
    """Las columnas que la tabla ya tiene (vacío si no existe)."""
    inspector = sa.inspect(op.get_bind())
    if TABLA not in inspector.get_table_names():
        return set()
    return {columna["name"] for columna in inspector.get_columns(TABLA)}


def upgrade() -> None:
    columnas = _columnas()
    if columnas and COLUMNA not in columnas:
        op.add_column(TABLA, sa.Column(COLUMNA, sa.String(120), nullable=True))


def downgrade() -> None:
    if COLUMNA in _columnas():
        with op.batch_alter_table(TABLA) as lote:
            lote.drop_column(COLUMNA)
