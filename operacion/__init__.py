"""Operación del producto Sílice, fuera del núcleo y sin Streamlit (spec S5 §5.2).

`config` (carpetas de datos), `base_datos` (`preparar_base`, lista de casos), `respaldo` (juegos de
respaldo y restauración) y la orden `python -m operacion`. Importa `core.catalog`, `migraciones`,
SQLAlchemy, Alembic y la biblioteca estándar; nunca `streamlit`, `ui` ni `api`
(`tests/unit/test_arquitectura_s5.py`).
"""
