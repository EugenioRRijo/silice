# Hoja 3e: Excel (X1) e importar un plano (P1 a P6), avance

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-hoja-e` (desde `dfc8719`) · Contrato: `2026-10-20-hoja-3e-contrato-rutas.md`.
Plan C: no se tocó `ui/hoja.py`, `ui/composicion.py`, `ui/paginas/hoja.py`, `core/`, `asistente/` ni `aplicacion/hoja.py`.
Implementadores y árbitros independientes por rebanada; sin push ni PR.

## Ciclos

| Rebanada | Implementador | Árbitro | Rondas | Veredicto |
|---|---|---|---|---|
| 3e-1 Excel (backend y botón) | agentes propios | independiente | 2 | APROBADO (cabeza `d50b304a`) |
| 3e-2 backend (P1 a P6) | agente propio | independiente | 2 | APROBADO (cabeza `b16800d0`) |
| 3e-2 front (importar plano) | agente propio | independiente | ver estado al pie | |

Hallazgos que obligaron a devolver: 3e-1, la trazabilidad de la versión abierta no estaba probada (T1, T2, T4 a T7 sobrevivían; ahora mueren) y un
carácter de control en una celda daba 500 (ahora 422 con texto fijo). 3e-2 backend, la ruta del servidor salía en el mensaje del lector cuando
el recorte a 120 caracteres la cortaba (ahora `_sin_rutas` sustituye el mensaje entero por marca de `OSError` o rastro de la raíz temporal).
3e-2 front, una carrera entre fusionar y editar el espacio (el `PUT` salía con el `rev` nuevo y las tablas viejas y las filas fusionadas
desaparecían), foco perdido tras el 409 de `rev` y una regla de estilo en el archivo equivocado.

## Archivos compartidos (míos)

`api/main.py` (dos routers), filas de acceso (X1 y P1 a P6, `EDITAR`, solo con sesión), conjunto de rutas de `test_api_hoja.py`,
`docs/api.json` regenerado, `Shell.tsx` (`olvidarImportaciones()` al salir y al vencer la sesión) y CHANGELOG.
Comprobado: `test_api_hoja`, `test_api_acceso_por_ruta`, `test_openapi`, `test_front_rutas_api`: 346 verdes.

## Cambios al contrato respecto del texto de `460f04f`

- P2 (`POST …/plano/unidad`) sobre una importación que no está detenida responde **409** «Esta importación no está detenida: no hace falta elegir
  una unidad.» sin volver a leer el plano. Orden de comprobaciones: `rev`, unidad válida, que haya importación, que esté detenida, que el archivo exista.
- `heredar` conserva la importación (va por el `id` del borrador).

## Riesgos con números (decisiones para Eugenio)

1. **Lector de planos sin tope de tiempo ni de tamaño.** DXF de 13,6 MiB y 99 mil líneas: 26,5 s; 140 mil líneas: 36,7 s y se rechaza
   después de leerlo entero; 15 mil puntos (16 MiB): 43 s. El árbitro con 4,4 MiB tardó 11,3 s.
2. **Hilos agotados.** El grupo de 40 hilos de anyio se agota con 40 lecturas (P1) de una sola cuenta: las rutas síncronas quedan paradas
   entre 17 y 29 minutos. Hay que decidir un tope de tiempo o de tamaño.
3. **Carpetas `silice_planos_*` tras una caída.** Si el proceso muere, el plano del usuario queda en `%TEMP%` y nada lo barre al arrancar. Un barrido al iniciar es tarea aparte.
4. Memoria del lector no medida (no hay `psutil`).
5. `filas_del_informe` de la clásica es cuadrática en una expresión regular; se dejó en la copia congelada. La copia de `aplicacion/hoja_plano.py` es lineal.
6. `hoja_edicion._cambiar` es privada y P5 la reutiliza; conviene hacerla pública (`cambiar_borrador`) cuando se pueda tocar ese módulo.
7. Con U+FFFE o U+FFFF en el nombre de un ambiente, E1 lo acepta y X1 entrega un libro que openpyxl no puede leer (la clásica entrega el mismo libro roto). La raíz está en E1.
8. Ningún caso de prueba tiene una versión con 2 o más filas de trazabilidad: «solo la 1.ª fila» no se distingue.
9. X1 usa la trazabilidad de la versión abierta; tras «guardar» (3d) puede diferir de `vivo.abierta` hasta releer.
10. `DescargaArchivo` (en `src/comun`) pierde el foco tras descargar; `SubidaArchivo` es cuadrático con el nombre (1,3 s con 20 mil caracteres, unos 29 s con 100 mil; regex sin escapar el punto). Ambos son del dueño de `src/comun`; el sistema de archivos limita el nombre a 255, así que no es riesgo real.
11. La página Espacio mide unos 52 000 px de alto y la columna Estado se rompe (3c-1, T11); 7 `role=alert` vacíos de `TablaEditable`.
12. Pruebas que usan `ezdxf` fallan sin él (decisión de proyecto, como `xlrd`); usar `.worktrees\s2m4\.venv`.
13. Dos P5 simultáneos sobre un borrador que no cambia: la perdedora recibe 409 «sin importación», no de `rev`. Sin prueba.
14. Con el backend real, fusionar OF-001 sobre OF-001 deja `rev` 0 y «ninguna» fila entrada, con 33 orígenes.

## Pendiente fuera de esta rebanada

VB-1 (el patrón de cifras de `core/` rechaza 29 decimales y deja sin revisar paquetes firmados con 1/12), poda de 49 worktrees, PR en borrador y retiro de Streamlit: de Eugenio.
