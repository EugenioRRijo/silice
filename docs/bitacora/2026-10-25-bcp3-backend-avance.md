# BCP-3 backend: crear proyectos (avance y rulings)

> **Fecha:** 2026-10-25 · **Quién:** subagente `silice-backend` · **Diseño:**
> `docs/especificaciones/2026-10-21-bienvenida-casos-proyectos-design.md` §5, §9.3, §10 (B19, B20, J1 de S8), P-13.

## Qué se hizo

- `aplicacion/proyectos.py`: `crear_proyecto_en_sesion(sesion, nombre, moneda, dominio, descripcion, responsable)`
  normaliza el nombre, compara con `casefold` en Python, valida moneda y tipo de obra con texto propio, crea el
  proyecto y declara la moneda y confirma en una sola transacción (si algo falla, `rollback`: no queda el
  proyecto). `crear_proyecto_nuevo(ruta, ...)` abre su motor y delega en ella. Nueva `ProyectoRepetido`
  (subclase de `ProyectoInvalido`) para el 409.
- `api/rutas/proyectos.py`: `POST /v1/proyectos` con `EDITAR_HOJA` sobre la sesión de escritura
  (`SesionDeEscrituraDep`, `BEGIN IMMEDIATE`), con `RutaSinEco`. 201 con la forma de un elemento de la lista.
- `tests/unit/test_api_proyectos_crear.py`: B19, B20, J1 de S8 y P-13 (rojo visto: 405 en todas).

## Rulings (opción conservadora)

1. **Cerrojo (§9.3):** se usa la sesión de escritura existente (`BEGIN IMMEDIATE`) en lugar de un cerrojo nuevo:
   serializa comparación y alta entre procesos y hilos. Respaldo: un `IntegrityError` por la restricción única
   también da 409. La prueba de dos peticiones simultáneas da 201 y 409.
2. **Texto del 409:** B19 pide «Torre B» en el mensaje también para «  torre   b ». El texto nombra al proyecto
   que **ya existe** («abra ese» lo apunta), no al intento. Para el nombre idéntico coincide con la clásica.
3. **Forma de los errores:** la API del repositorio contesta `{"detalle": ...}` (no `detail`); los 409/422 de
   dominio y el 422 de forma siguen esa convención.
4. **Responsable en las pruebas:** la cuenta `ana` de `tests/fixtures/sesion_web.py` se llama «Ana», así que el
   responsable esperado es «Ana <ana>» (el «Ana Pérez» del diseño es un ejemplo).
5. **Mensajes de `crear_proyecto_nuevo`:** al delegar, también salen con tilde (DV-BCP-3) y la moneda/tipo de obra
   con el texto propio del §9.3. Cambió una línea de `tests/unit/test_aplicacion_proyectos.py` (el `match` de
   «vacío»).
6. **S8, IP remota:** `POST /v1/proyectos` no filtra por IP (solo las rutas P0/P1 y las de equipo propio lo hacen);
   no se prueba el 403 remoto aquí.
7. `dominio` ausente equivale a `""`; `moneda` ausente o `null` no declara moneda.

## Pendiente para el orquestador (archivos compartidos)

Ver el informe final del subagente: `api/main.py` no necesita cambios (el router ya está incluido);
`test_api_acceso_por_ruta.py`, `CHANGELOG.md`, `docs/api.json` y `docs/ERS.md` (P-13) llevan las líneas allí indicadas.
