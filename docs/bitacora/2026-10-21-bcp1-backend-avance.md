# BCP-1 backend · avance (2026-10-21)

Base `82c0bab6`. Contrato: `2026-10-21-bcp1-contrato-rutas.md`. Expediente: `2026-10-21-bcp1-expediente-seguridad.md`.

## Hecho
- S3 en rojo (`1518ca8e`, 5/5 rojas 3 corridas) -> bloqueo de escritura (`d86c3404`, 4 verdes, defensa roja) -> defensa `UPDATE` y ciclo de vida del codigo (`950a51d2` rojo, `f4206bfc` verde).
- `operacion/primer_arranque.py`, gancho del lanzador, orden `restablecer-administrador` (`14093612` rojo, `804d3c2c`).
- Rutas P0 y P1, `lifespan` unico (`8529bb64` rojo, `5010b6af` pruebas, `945abf7d`).
- Servidor Uvicorn real: no imprime codigo ni contrasena (`tests/integration/test_primer_arranque_servidor.py`).

## Ajustes declarados tras ver verde
- `tests/unit/test_ordenes_100.py`: el conjunto de ordenes gana `restablecer-administrador`.
- `tests/unit/test_lanzador.py`: `Escenario.correr` inyecta un `asegurar` falso por omision (las bases no se migran en esas pruebas).
- `tests/integration/test_api_auditorias.py` y `test_api_clave.py`: las dos rutas publicas salen de la lista que exige clave.
- La implementacion del lifespan precedio a su prueba; rojo retroactivo por mutacion (se anulo la llamada: 5 pruebas fallan).
- Puerta (Origin/equipo) como paso de la clase de ruta y no dependencia: un JSON roto daba 422 antes de ella.
- Formateo `ruff format` de las pruebas nuevas tras su commit rojo.

## Verificacion
Corrida combinada (51 archivos): 1719 pasadas, 2 fallos (`test_api_clave`, ya corregidos y repetidos en verde). `app.openapi() == docs/api.json`: True. `ruff check` limpio en lo tocado. `git diff 82c0bab6..HEAD -- core asistente/experimento aplicacion/hoja.py` vacio.
