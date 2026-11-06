# Autocompletado guiado · Ronda 2 · Árbitro de Claude, esfuerzo xhigh (2026-11-05): DEVUELTO (1 MAYOR)

> Arreglos `03db4797..43faa7c2`. Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: DEVUELTO.** Queda un solo MAYOR, y lo trajo el arreglo del bloqueante 2. Todo lo demás pasaría; según
MANUAL_ARBITRO §4, cualquier MAYOR devuelve la rama. El arreglo es pequeño.

**Verificado:** `core/` vacío en el diff y guardia sin queja; ruff, eslint y `tsc` limpios; pytest de los 7 archivos
cambiados (204), `test_openapi` y `test_api_acceso_por_ruta` en verde; vitest de 12 archivos 239/239; rojo comprobado
corriendo cada commit de prueba contra su propio código (361fe6ee: 19 fallos; f09c4467: todas las nuevas; 62858e9d: 15;
2328e795: 4; b2ce582f: 1).

## Ronda 1

| Hallazgo | Estado | Evidencia |
|---|---|---|
| BLOQ 1: precio de la lista de otra fecha | RESUELTO | `TablaInsumos.tsx:224` (`key={paraArmarAl}`); prueba `EleccionDeInsumos.test.tsx:115-171`. Reproducción: tras cambiar a 20/10 se pide de nuevo y al elegir sale «25,50» |
| BLOQ 2: segundo insumo con el precio del primero; lo escrito se pisaba | PARCIAL | `autocompletado.ts:85-121`, `TablaInsumos.tsx:93-152`. Resuelto entre dos insumos del catálogo («Cemento blanco ficticio», unidad y precio vacíos; precio escrito «7,5» conservado con aviso). Falla con una fila precargada o de MaPreX (nuevo 1) |
| MAYOR: Esc en el panel | RESUELTO | `ComponerEnPanel.tsx:87`, `CampoConBusqueda.tsx:494`; tras Esc la fila queda entera |
| MAYOR: la sugerencia sin precio, moneda ni fecha | RESUELTO | `consulta.ts:59-75`, `TablaInsumos.tsx:84` |
| Notación científica | RESUELTO | `api/rutas/consulta.py:195` |
| Control con lista recortada | RESUELTO | `corte` y `truncada` en `api/rutas/control.py:200-227`, `aplicacion/control.py:290-326` |
| Proveedores | RESUELTO | cotizaciones activas, `aplicacion/consulta.py:339-356`; desvío del permiso en la enmienda §1 |
| 404 y 503 fijos | RESUELTO | `control.py:219, 227`; `reajuste.py:229-251, 272` |
| Accesibilidad | RESUELTO | región viva en `CampoConBusqueda.tsx` y `SeleccionMultipleConBusqueda.tsx` |
| DRY y capas | PARCIAL | quedan `componer/unidades.ts:21-26` y `logicaBusqueda.ts:115`; importaciones entre páginas y MONEDAS en tres sitios |
| TDD | RESUELTO | sin oráculo circular |
| Documentación | PARCIAL | falta la enmienda del ERS (§12.4 del diseño) |
| Marcas por índice | RESUELTO | `marcaDe`, pruebas 6.1-6.3 |
| Escenarios y Simulador | RESUELTO | igual a la regla del núcleo; `list[str]` compatible con el texto de comas |

## Hallazgos nuevos

**[MAYOR] 1. Una fila precargada o de MaPreX se mezcla al elegir del catálogo.** `paginas/componer/autocompletado.ts:98-114`
con `TablaInsumos.tsx:137`. La precarga (`ComponerPartida.tsx:225-226`) y «Usar esta fila» de MaPreX (`:330`) crean filas
sin marca y `aplicarEleccion` trata todo lo que no llenó el catálogo como de la persona: la fila queda con la descripción
nueva y la unidad y el precio anteriores, con el aviso «se conserva el precio que escribió» (no lo escribió), y sin aviso
si el nuevo no trae precio. Regresión respecto de 03db4797. Contra el diseño §1.6.6. Salida por el panel real:
`R2-P3 TRAS ELEGIR CEMENTO: {"descripcion":"Cemento gris ficticio","unidad":"m3","precio":"5,00","ayudaPrecio":"El catálogo tiene 18,00 Bs; se conserva el precio que escribió.",…}`.
Corrección: solo es «de la persona» lo tecleado; lo que vino de fuera (precarga, MaPreX, catálogo) se reemplaza o se
vacía al elegir otro insumo y se dice. Pruebas de precarga y de MaPreX, con y sin precio; revisar el oráculo de
`EleccionDeInsumos.test.tsx:316-326`.

**[MENOR] 2.** El aviso «Precio de la lista del …; revise» aparece con cualquier cambio de «Fecha» (también vacía),
aunque la lista no cambie, y solo vive en la ayuda de la celda (WCAG 4.1.3). Anunciar una vez junto a «Fecha» cuántos
precios quedaron con otra fecha.

**[MENOR] 3. Simulador.** `","` o `" , "` antes daba un conjunto vacío (0 filas) y ahora `None` (todos), sin prueba; la
lista admite 20.000 elementos de 500 caracteres (antes 20.000 caracteres); `docs/api.json` pone `maxLength` sobre el
anyOf, que no limita un arreglo (falta `maxItems`).

**[MENOR] 4.** En Control, «No hay una línea base vigente a esa fecha de corte.» nunca se muestra
(`PestanaValuaciones.tsx:64-72`, `partidasDelContrato.ts:34`).

**[MENOR] 5.** El refactor b20c41da cambia la normalización (`\p{Diacritic}` en vez de `[̀-ͯ]`) sin prueba;
inocuo, pero no es un refactor puro.

**[MENOR] 6.** La fila AC3 de `PLAN_AUTOCOMPLETADO.md` dice «lo que se envía no cambia de forma», y el Simulador ahora
manda una lista.

**Sin defecto:** `alElegir` con texto no cambia a ningún uso viejo; `tipo` solo con `detalle`; Escenarios es el
complemento exacto de `_variados`; la región viva de la selección múltiple se monta con el foco.

**Sospechado:** R13 juzga por omisión con la línea base vigente al «hasta» de la última valuación
(`core/budget/valuaciones.py:468-482`): una valuación con fecha anterior podría no coincidir con la guía `corte=hasta`.
Fuera de esta rama: Esc en «Código» del panel restaura solo el código tras una precarga.
