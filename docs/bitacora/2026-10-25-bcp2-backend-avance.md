# BCP-2 backend · carpetas de trabajo · avance (2026-10-25)

Base `ab400fb1`. Diseño: `docs/especificaciones/2026-10-21-bienvenida-casos-proyectos-design.md` §4, §9 (C0 a C3),
§10 (B11 a B18, S5, S6, S8, S9), §16 9.1 y 9.2. Contrato para el front: `2026-10-25-bcp2-contrato-rutas.md`.

## Hecho

| Commit | Qué |
|---|---|
| `4d6ee280` | rojo: `tests/unit/test_aplicacion_casos.py` y `tests/fixtures/carpetas_trabajo.py` (colección fallaba: `aplicacion.casos` no existía) |
| `ded765d7` | `aplicacion/casos.py` (crear, `subir_seguro`, demostración, estado, ubicación, purga), `operacion/demostracion.py` (proceso hijo), `--salida` en la orden `demostracion`, `CasoYaExiste` y COM/LPT con superíndice en `operacion/base_datos.py` |
| `a36fcd50` | rojo: `tests/unit/test_api_casos_carpetas.py` y `test_api_casos_subida.py` (404/405 y la dependencia ausente) |
| `4cee3a2b` | `api/rutas/casos.py`: C0 a C3 con `no-store` y 422 sin eco |

Lo que BCP-1 dejó se reutiliza tal cual: el `lifespan` único (la purga de la cuarentena se le suma, texto en el informe
al orquestador), `aplicacion.equipo` y las dependencias de sesión. BCP-1 no tenía cerrojo ni cuarentena de casos: se
construyeron aquí.

## Rulings (opción conservadora ante ambigüedad)

1. **Cuarentena por petición en una subcarpeta**: `<datos>/cuarentena/<token>/<nombre>.db` en lugar de `<token>.sub`, para
   que el juego de respaldo de una subida migrada lleve el nombre real; la carpeta `cuarentena/` se quita si queda vacía
   (así B15 compara el árbol entero).
2. **Crear también nace en la cuarentena** y se publica con copia y `os.rename`: nunca hay un archivo a medias visible en `casos/`.
3. **Lo publicado queda en modo de diario `DELETE`** (no WAL): leerlo en solo lectura (C0) no deja `-wal`/`-shm`.
4. **Validación más estricta que el «o» del diseño**: las tablas núcleo se exigen siempre (`composicion_apu`, `insumo`,
   `lista_precios`, `partida`, `precio_insumo`, `presupuesto`, de la 0.5.0); una revisión desconocida con forma rara o de
   la base de la instalación es «no válida», no «más nueva». §15.2 queda resuelto así.
5. **«demostración» con tilde también está reservado** (además de mayúsculas).
6. **El `nombre` del formulario de la subida pasa por `_validar_forma`** como al crear (más estricto que solo sanear).
7. **Demostración**: el cerrojo se tiene durante el hijo (no hay dos hijos a la vez); salida inválida del hijo → 503;
   `demostracion.db` existente sin partidas → 409 y no se pisa.
8. **Subida**: comprobación de nombre libre y tope antes de trabajar (sin cerrojo) y otra vez bajo el cerrojo al publicar.
9. **Textos fijos en `estado`** (ilegible, bloqueada, por migrar) en lugar del texto de SQLite, que puede traer rutas.
10. **El 409 de «ya existe» nombra la carpeta que ya está** y dice «carpeta de trabajo» (D-1 pendiente, reversible).
11. **Proceso hijo** sin consola en Windows (`CREATE_NO_WINDOW`), entorno sin `PYTHON*`/`VIRTUAL_ENV`, salida capturada y no
    registrada (solo el código de salida).
12. **Fixture nueva** `tests/fixtures/carpetas_trabajo.py` (fuera de la lista de archivos del encargo, pero nueva: INV-052).

13. **Motivo propio para las subidas (corrección tras la revisión del árbitro).** Cada subida de una base anterior a `head`
    creaba un juego con motivo `migracion` y la poda conservaba solo 5: cinco subidas de bases viejas borraban el respaldo de
    la migración real de la instalación. Ahora `preparar_base(..., motivo=)` (por omisión `migracion`, sin cambio para los
    demás llamadores) recibe `MOTIVO_SUBIDA = "subida"` desde `aplicacion/casos.py::_preparar`; `podar_juegos(..., motivo=)`
    cuenta y borra solo juegos de ese motivo (se conservan 5 `subida` y 5 `migracion` por separado). Un juego `subida` jamás
    borra uno de migración, manual ni de antes de restaurar. `restaurar` y los listados (`aplicacion/instalacion.py`,
    `api/rutas/admin_instalacion.py`) no filtran por motivo: muestran el texto crudo de la ficha, así que un juego `subida`
    aparece y se restaura como cualquiera; la interfaz React no traduce motivos. Reversible: basta volver a pasar el motivo por omisión.
14. **MENOR C2**: `purgar_cuarentena` también quita `-journal`, `-wal` y `-shm` de los `casos/.subiendo-*.tmp` de más de una
    hora. Los `*.db.migrando-*` de `preparar_base` no se tocan (diferido).

## Desviaciones y diferidos

- **Sin plazo sobre `preparar_base`** (§16 9.1 lo pedía): Alembic no se puede interrumpir con seguridad desde otro hilo
  y un hilo vencido seguiría escribiendo en la cuarentena. El plazo existe sobre `quick_check`/`integrity_check`
  (`PLAZO_VALIDACION_S = 60`, manejador de progreso de SQLite). Diferido a BCP-10 (medir con 20 MiB).
- **Carrera tardía de la subida**: si otra creación publica el mismo nombre entre la migración y la publicación, la subida
  da 409 pero el juego de respaldo previo a la migración queda en `respaldos/` (nada queda en `casos/`).
- **La purga al arrancar** está en `aplicacion.casos.purgar_cuarentena` y probada directo; su llamada desde el `lifespan`
  la aplica el orquestador en `api/main.py` (compartido).
- **El 413 propio** («El archivo pasa de 20 MiB.») solo se alcanza con un tope menor que el del cuerpo: con los dos en
  20 MiB, el que responde es el tope de la API.
- `docs/api.json` debe regenerarse (`app.openapi()` ya no coincide: cuatro rutas nuevas).

## Ajuste declarado tras ver verde

- `test_una_base_vieja_esta_por_migrar`: el oráculo usaba `v1_0_0/s1.db`, que ya está en `head`; pasa a `v0_5_0/demo.db`
  (sin `alembic_version`). Error del oráculo, no del código.

## Observación fuera de alcance

- En `data/casos/` del árbol hay restos `*.db.migrando-shm`/`-wal` de octubre: `preparar_base` borra la copia de trabajo
  pero no sus `-shm`/`-wal`. No se tocó (`operacion/base_datos.py` solo se amplió con la subclase).

## Verificación

Ver el informe final de la sub-rebanada (salida real de `pytest -W error` y `ruff`). La prueba B17 corre el proceso hijo de
verdad una vez (~8 s en este equipo: 8 partidas, `DEMO-001`).
