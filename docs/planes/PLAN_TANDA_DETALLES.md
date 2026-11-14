# Plan de lo que sigue en el front: tanda de detalles, F7 Ayuda y F8 Cierre

**Fecha:** 2026-11-05. **Decisión de Eugenio:** se construye con **Gemini Flash por `agy`** y Claude audita; el orden lo
recomendó el orquestador y Eugenio lo aceptó. **Estado del proyecto:** [ESTADO.md](../ESTADO.md). Cada fase sale de
`main` en su rama `feature/*`, una vez fusionados el PR #106 (F6) y el del autocompletado.

## Cómo se trabaja con Flash

1. **Encargo.** Claude escribe un encargo por tarea, en un archivo, con el contexto mínimo: qué está mal, los archivos y
   las líneas, la regla que aplica (NORMAS, DESIGN.md, contrato) y el criterio de aceptación. Se lanza desde la raíz de
   TESIS (en un worktree `agy` no ve git):
   `agy -p "$(cat encargo)" --model gemini-3.8-flash-high --sandbox </dev/null`.
   Flash es de solo lectura: lee el código con `git show <rama>:<ruta>` y no ejecuta pruebas, `npm` ni `uv`.
2. **Respuesta.** Flash devuelve el parche en `git diff` unificado contra la cabeza de la rama, en **dos bloques**: primero
   las pruebas (con oráculos escritos a mano) y después el código, más una línea por archivo con el porqué.
3. **Aplicación con TDD.** Claude aplica las pruebas, comprueba que fallan por la razón correcta y hace el commit del rojo.
   Después aplica el código, corre las pruebas de la zona, `npm run lint` o `ruff`, y hace el commit del verde. Cada
   commit dice «parche de Gemini Flash, auditado por Claude».
4. **Auditoría.** Claude revisa cada parche contra el código, no contra lo que Flash dice de él: que no debilite pruebas,
   que no calcule cifras en el cliente, coma decimal, español llano y accesibilidad.
5. **Si falla.** Si un parche no aplica o falla dos veces, la tarea pasa a un subagente de Claude. Lo que toque `core/`
   nunca va a Flash: necesita expediente y el aval del tutor.
6. **Paralelo.** Varios encargos a la vez, uno por tarea y con archivos que no se pisan.
7. **Compuerta de cada fase.** Suites completas (vitest, pytest `-W error`, ruff, build y `verificar_dist`, metas de
   datos, guardia del núcleo) y un árbitro de Claude con esfuerzo xhigh sobre la rama entera, sin las conclusiones del
   orquestador. Un MAYOR devuelve la rama.

## Fase 1 · Tanda de detalles

| ID | Qué | Dónde (punto de partida) | Origen |
|---|---|---|---|
| D1 | La cantidad sale con punto en la tabla de cambios de «Guardar versión» («24.5») | `paginas/hoja` (diálogo de guardar versión) | prueba en vivo 2026-11-04 |
| D2 | «del proyecto» → «de la obra» en los avisos | textos de `paginas/` y de `aplicacion/` | prueba en vivo 2026-11-04 |
| D3 | «Cadena íntegra: 1 versiones» (singular y plural) | `paginas/aprobar` o `paginas/versiones` | prueba en vivo 2026-11-04 |
| D4 | La hora del registro de cambios sale con microsegundos y nombres internos sin tilde | `paginas/versiones` y su API | prueba en vivo 2026-11-04 |
| D5 | Una obra nueva en una carpeta sin moneda dice «Carpeta sin moneda declarada» y no la moneda de la obra | `marco/CabeceraDeObra.tsx` | prueba en vivo 2026-11-04 |
| D6 | «m3» en Aprobaciones y «m³» en la Hoja: una sola forma | `paginas/aprobar`, formateador de unidades | prueba en vivo 2026-11-04 |
| D7 | 404 en consola al abrir «Producir mezcla» | `paginas/produccion/useMezclas.ts` | video 2026-11-01 |
| D8 | «Sin cálculo» en las filas de tramos | `aplicacion/hoja_vista.py` | video 2026-11-01 |
| D9 | «Trayectorias por corte» bajo «Proyectar» | `paginas/riesgo/RiesgoDeLaObra.tsx` | video 2026-11-01 |
| D10 | Botones sin nombre accesible: 3 en el Visor y 2 en Administración | `visor/`, `paginas/administracion/` | video 2026-11-01 · **falso positivo** (2026-11-06): eran los botones ocultos (`aria-hidden`) que Carbon pone en cada pestaña; el arreglo se revirtió (rompía la flecha izquierda) |
| D11 | «Versión vigente» del Resumen también es la de la línea base cuando existe | `paginas/obras/textos.ts:9`, `aplicacion/mesa.py:357-370` | árbitro final de F6 |
| D12 | La ayuda del «Total» de la cartera solo vive en la API: mostrarla | `paginas/inicio/CarteraYAvance.tsx` | árbitro final de F6 |
| D13 | La columna «Estado» del Presupuesto queda cortada a 1366 px | `paginas/hoja/hoja.scss:144-170` | árbitro final de F6 |
| D14 | La tabla apilada de la Vista general: rótulo y dato en una línea, rótulo en gris | `paginas/inicio/inicio.scss` | revisión del orquestador |
| D15 | Restos del autocompletado: dos normalizaciones duplicadas (`logicaBusqueda.ts:115`, `componer/unidades.ts`), importaciones entre páginas que deberían pasar por `comun/`, `MONEDAS` en tres sitios | `comun/`, `paginas/*` | árbitro del autocompletado |
| D16 | En el panel de Componer, Esc en «Código» restaura solo el código tras una precarga | `paginas/componer/CampoDelCodigo.tsx`, `paginas/hoja/ComponerEnPanel.tsx` | árbitro del autocompletado |
| D17 | En Componer, elegir una partida y luego otra dejaba la descripción y la unidad de la primera con el código y las tablas de la segunda | `paginas/componer/ComponerPartida.tsx:386-390` | árbitro de la tanda, ronda 2 (anterior a la tanda) |

Cada fila se confirma en el código antes del encargo: si ya no pasa, se anota y no se toca.

## Fase 2 · F7 Ayuda

| ID | Qué |
|---|---|
| A1 | «¿Qué es esto?» en cada sección de la obra y de los espacios, con el componente de las pestañas del Presupuesto (`paginas/hoja/AyudaDePestana.tsx`) |
| A2 | Guías por tarea, en español llano: montar un presupuesto, enviarlo a aprobación, actualizar precios, auditar un libro |
| A3 | Glosario de términos (APU, FCAS, valor ganado, reajuste, línea base, lista para armar), enlazado desde la ayuda |
| A4 | «Empieza aquí» para la primera vez, que incluye la entrada del primer administrador desde la interfaz (pedido de Eugenio del 2026-10-21) |

Flash redacta los textos de A2 y A3 a partir del manual de usuario y del código. Claude los coteja con el código (cada
afirmación contra `archivo:línea`) antes de aplicarlos.

## Fase 3 · F8 Cierre del rediseño

| ID | Qué |
|---|---|
| C1 | Retirar las redirecciones viejas del contrato §2.4, con aviso en el CHANGELOG |
| C2 | Rehacer `scripts/recorrido_ux_playwright.py`, que aún navega por el menú de módulos retirado (modos de pantallas, `--funcional` y `--umbrales`); si se le añade un detector de botones sin nombre, que salte lo `aria-hidden`, como axe (D10) |
| C3 | Pasada única en navegador a 1056, 1366 y 1920 px, con las tres letras |
| C4 | Comparación de líneas contra la línea base del rediseño y tamaño del front (14,4 MB de 15): partir el paquete si hace falta |
| C5 | Restos del árbitro de la tanda (rondas 3 y 4): el presentador de cambios elige la primera coincidencia de columna (N1: un nombre «Toma; x=3» engaña); el aviso de Componer compara sin `trim()` ni grafías equivalentes de unidad (N4); 14 mensajes del servidor dicen «no existe en este caso»; «Esta version esta en solo lectura…» (`aplicacion/hoja.py:2134`, `hoja_guardado.py:77`) y `motivo_para_no_reemplazar` (`aplicacion/composicion.py:460-469`) sin tildes. `hoja.py` y `composicion.py` están congelados por el experimento: tocarlos exige re-congelar con acta y aval de Eugenio |

## Después · Diseños de F5

Lecciones del presupuesto vial revisado en local y ventana de escritorio: esperan las respuestas de Eugenio. Diseño del
vial revisado en local: §10 de [su especificación](../especificaciones/2026-11-03-presupuesto-vial-real-design.md);
la ventana, en su propia especificación. La ventana exige enmendar RT-3 y RT-5, que todavía dicen Tauri.
