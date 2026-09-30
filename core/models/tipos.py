"""Tipos de columna propios del modelo. Justificación en docs/modelo_datos.md §7.1."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Dialect, String
from sqlalchemy.types import TypeDecorator

LONGITUD_DECIMAL = 40


class DecimalExacto(TypeDecorator[Decimal]):
    """`Decimal` persistido como texto, sin pasar nunca por `float`.

    SQLite no tiene tipo decimal nativo: con `Numeric` el valor viaja como `REAL` y SQLAlchemy lo
    reconvierte a `Decimal` a través de `float`, lo que emite `SAWarning` y admite pérdida de
    precisión. El texto conserva exactamente los dígitos y la escala del original
    (`Decimal("0.415")` vuelve como `Decimal("0.415")`), que es lo que exige NORMAS.md §2.

    En PostgreSQL se sustituye por `Numeric(18, 6)` sin tocar los modelos.
    """

    impl = String(LONGITUD_DECIMAL)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if not isinstance(value, Decimal):
            raise TypeError(f"se esperaba Decimal, no {type(value).__name__}: {value!r}")
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))
