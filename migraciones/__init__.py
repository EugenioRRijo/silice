"""Los dos destinos de migración de Sílice con Alembic (RF-96, RNF-20; maestro §4.2; spec S5 §6).

`caso/` migra la base de cada caso; `instalacion/` la base de la instalación (vacía hasta S3-1). Sin
`alembic.ini`: los corre solo `operacion.base_datos`, que arma la configuración y entrega la
conexión. Nunca importa `streamlit`, `ui`, `api` ni `operacion`.
"""
