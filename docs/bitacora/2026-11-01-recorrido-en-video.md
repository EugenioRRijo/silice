# Recorrido en vivo grabado y auditado (1 de noviembre de 2026)

Rama `inc/vial-agregados` en 0329b0f6, servida con `uvicorn api.main:app` sobre una **copia** de la carpeta de
demostración vial ficticia («Vía Ficticia El Ensayo», cuentas ana/rita/admin). Ningún dato real.
Navegador Chromium visible a 1366×768, grabado con Playwright; en cada paso, captura y medidas
(desborde horizontal, elementos fuera de la ventana, textos de Carbon en inglés, números con punto decimal,
errores de consola y de red, botones sin nombre accesible).

- Toma definitiva: 73 pasos, 4 min 12 s, sin fallos del guion (Ana arma → Rita revisa → administrador).
- El video, las capturas y `pasos.json` quedan fuera del repositorio (Escritorio, carpeta
  «Recorrido Sílice 2026-11-01»).
- Ninguna de las 73 pantallas desplaza la página a lo ancho; ningún error de JavaScript (`pageerror`).

## Hallazgos

Severidad: **A** = conviene resolver o esquivar antes de mostrarlo; **M** = se nota en la demostración;
**m** = detalle.

| # | Sev. | Dónde | Qué se vio | Captura |
|---|------|-------|-----------|---------|
| 1 | A | Obra › Presupuesto con la cuenta que revisa | Rita (revisa) recibe «Sin permiso» y su barra solo ofrece Resumen y Aprobaciones: quien revisa no puede leer el presupuesto que dictamina. Ya resuelto en `inc/rediseno-f4` (T2b, lecturas de la Hoja con `leer_proyecto`), pero no en la candidata | 58_rita_hoja |
| 2 | A | Hoja de la obra, todas las pestañas | A 1366×768 la cabecera (barra de la obra, título, versión, aprobación, estado, Excel, pestañas) ocupa ~740 px: el contenido de cada pestaña empieza bajo el pliegue. En Presupuesto la descripción va en 3-4 líneas por fila y Total/Estado quedan fuera de la caja (desplazamiento interno) | 07, 08, 09, 13 |
| 3 | A | Precios y catálogo › Insumos | Precios con punto y sin miles: «0.50», «0.40», «2000»; unidades «m2»/«m3»; AGP-AR-01 sin precio vigente (celda vacía) | 46_catalogo_insumos |
| 4 | A | Precios de la empresa (admin) | Columna Impacto «0.00» con punto; «62 dias», «123 dias» sin tilde | 70, 71 |
| 5 | A | Riesgo de la obra | Con 2.000 trayectorias, P50 = P80 = 159.666,11 USD (dispersión nula); toda la reserva (20.387,84 USD, +14,6 %) sale de MZ-C. Los supuestos mostrados no lo explican: verificar antes de enseñarlo al tutor | 29, 30 |
| 6 | M | Obra › Resumen | Muestra «Inicio de presupuestos y obras» (h1, tabla de todas las obras, «Nueva obra»), no el resumen de esa obra | 03, 57 |
| 7 | M | Barra superior en pantallas de obra | El botón de la cuenta se sale del borde derecho (hasta 1.381 px en 1.366) y la miga se trunca: «Mis ob… / Vía Ficticia El En… / Tra…» | 05, 20, 59 |
| 8 | M | Hoja › Parámetros | Texto visible «FCAS (fracción: 6.00 = prestaciones del 600 %)» con punto. En Presupuesto/APU/Precios, «Valor exacto 2530.000000» (texto para lector de pantalla o tooltip) con punto | 13, 09, 12 |
| 9 | M | Riesgo › Proyectar sin fecha | El 422 «Indique la fecha de inicio…» aparece bajo el botón, lejos del campo, que no se marca como necesario. En Mejora, «Presupuesto original» llega vacío aunque Sílice conoce el total base (la estimación sí se rellena con el P50) | toma 1: 27; 32 |
| 10 | M | Salir estando en la Hoja | `DELETE /v1/hoja/borradores/…` sale después de cerrar la sesión → 401; el borrador podría quedar sin borrar | 55 (red) |
| 11 | M | Hoja › Presupuesto, «Cómo se midió» | «Sin cálculo» en filas que vienen de los tramos (C-000.000.006…), mientras Pendientes dice que solo hay 1 cantidad a mano: se contradicen a la vista | 07 |
| 12 | M | Costo por tonelada | «Calcular costo por tonelada» está inactivo hasta elegir la moneda y no dice por qué | 42 |
| 13 | M | Pendientes | Franja vacía de ~200 px entre el título y la lista | 02 |
| 14 | m | ~40 pantallas con pestañas o tablas anchas; Catálogo y APU | Textos de Carbon en inglés: «Scroll left/right», «Clear search input» | — |
| 15 | m | Receta de la planta | El autocompletado no ofrece nada con una letra («M») y sí con dos («MZ»); el aviso dice «No hay receta vigente de M el 2026-11-01» (fecha ISO) | toma 1: 37, 38; 39 |
| 16 | m | Costo por tonelada | «Fuente: Producción, período 2026-09» (ISO); autoría «… (ficticia) <ana>» con corchetes angulares | 43 |
| 17 | m | Auditoría de un libro | «curva de inversion» sin tilde (R2) | 50 |
| 18 | m | Producir mezcla | Dos 404 en consola al cargar (receta vigente de AR-01 y PC-19, agregados sin receta) | 41 |
| 19 | m | Visor de auditoría (3), Administración (2), Entrar (1) | Botones sin nombre accesible | 50, 63, 01 |
| 20 | m | Riesgo | «Trayectorias por corte (500)» va bajo «Proyectar» pero pertenece a «Comprobar hacia atrás» | 29 |

## Lo que funcionó en el recorrido

- Proyección de riesgo con 2.000 trayectorias en ~5 s; comprobación hacia atrás (7 cortes, 500 trayectorias)
  en ~7 s, cobertura 7 de 7.
- Auditoría de un libro ficticio de la empresa en ~5 s: totales «sin variación», 0 críticos, 2 de información.
- Costo por tonelada de septiembre 2026 (cálculo n.º 3: AR-01 y PC-19 a 7,00, MZ-C a 51,65 USD/t) con huella.
- Tramos con «Llevar al presupuesto» y los tres reportes en Excel; buscador Ctrl+K; letra «Muy grande» sin
  desborde; las tres cuentas entran y salen desde el menú de la cuenta.
- Coma decimal correcta en la Hoja, Riesgo, Costo por tonelada y la auditoría (arreglos del 31-10 confirmados).

## Para la demostración de hoy

1. No entrar como **revisa** (hallazgo 1) o unir antes la T2b de F4.
2. En la Hoja, desplazarse hasta la tabla al llegar (hallazgo 2); mostrar el Catálogo en Partidas, no en Insumos (3).
3. En Riesgo: escribir la fecha de inicio **antes** de Proyectar y el presupuesto original (139.278,27) antes de
   «Calcular la mejora»; tener a mano la explicación de P50 = P80 o no enseñar los percentiles (5).
4. En Costo por tonelada, elegir la moneda primero.
