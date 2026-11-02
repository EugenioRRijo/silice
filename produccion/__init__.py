"""Contexto de produccion de la arenera: materiales, movimientos y existencias (RT-7).

Dominio puro: importa solo la biblioteca estandar, `sqlalchemy`, `openpyxl` y
`core.contracts`; nunca `adapters`, `api`, `ui`, `operacion` ni `seguridad` (regla en
`tests/unit/test_arquitectura.py`).
Sus tablas viven en la base de la instalacion (RT-S4-1).
"""
