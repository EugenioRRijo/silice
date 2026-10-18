"""Capa de aplicación de Sílice (RM-1, plan de la sesión 2b).

Lo que la interfaz clásica (`ui/`, Streamlit) y la interfaz nueva (`api/`, FastAPI) comparten y no
pinta nada: las operaciones sobre el caso que hoy vivían en `ui/<x>.py` se **mueven** aquí cuando
su página se migra, y `ui/<x>.py` queda como reexportación explícita. Así la API no importa `ui/`
(`PROHIBIDOS_EN_API` de `tests/unit/test_arquitectura.py`) y la lógica no se duplica (NORMAS §2.1).

`aplicacion/` no importa `streamlit`, `ui`, `api`, `scripts` ni `tests`; lo vigila
`tests/unit/test_arquitectura.py` (por archivo y en un proceso limpio). Puede importar `core`,
`operacion` y `seguridad`.
"""
