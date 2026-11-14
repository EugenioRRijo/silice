# Autocompletado guiado · Ronda 3 · Árbitro de Claude, esfuerzo xhigh (2026-11-05): DEVUELTO (1 MAYOR)

> Arreglos `43faa7c2..78615015`. Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: DEVUELTO** (un MAYOR, en un camino estrecho, que se arregla con pocas líneas). Sin BLOQUEANTE, así que no
corresponde ESCALADO.

**Verificado:** `core/` vacío en el diff y guardia sin queja; rojo visto ejecutando las pruebas contra el código anterior
(be3631d1 sobre 43faa7c2: 24 fallos; 6b91585a: 16 fallos, con la entrada aún devuelta en el 422; 7dc15231 corrige un
oráculo de forma legítima); verde en HEAD (vitest de 6 archivos, 99/99; pytest de test_api_simulador y test_openapi sin
fallos; ruff, eslint y `tsc` limpios).

## Ronda 2

| Hallazgo | Estado | Evidencia |
|---|---|---|
| MAYOR 1: fila precargada o de MaPreX mezclada | RESUELTO | `autocompletado.ts:103-155`, `TablaInsumos.tsx:105, 135-156`; `OrigenDeLaFila.test.tsx`, `EleccionDeInsumos.test.tsx:344`. Reproducción: «Se cambió el precio 5,00 por el del catálogo, 25,50 Bs.» y, con un insumo sin precio, «Se quitó el precio 5,00…» |
| MENOR 2: aviso de fecha | RESUELTO (deja el MENOR 3 de abajo) | `TablaInsumos.tsx:208-260`; `ComponerPartida.tsx` (`#componer-fecha-estado`) |
| MENOR 3: Simulador | RESUELTO | `aplicacion/simulador.py:98-118`, `api/rutas/simulador.py`; `maxItems` 200 |
| MENOR 4: aviso de Control | RESUELTO | `PestanaValuaciones.tsx:73, 163, 366` |
| MENOR 5: normalización | RESUELTO | `normalizar.ts:14` (`\p{M}`), 6 pruebas |
| MENOR 6: fila AC3 del plan | RESUELTO | `PLAN_AUTOCOMPLETADO.md:29` |

## Hallazgos nuevos

**[MAYOR] 1. Esc en el panel convierte en «tecleado» el precio que puso el catálogo y la fila vuelve a quedar mezclada.**
`paginas/componer/TablaInsumos.tsx:135-156` (`editar` toma cualquier `onChange` como tecleo) con
`paginas/hoja/ComponerEnPanel.tsx:88` (`restaurar` devuelve el valor con un evento `input`). Tras Esc, el precio del
insumo anterior se queda: sin aviso si el nuevo no tiene precio; con «se conserva el precio que escribió» (falso) si lo
tiene. Salida: `R3-N2 TRAS ELEGIR BLANCO: {…,"precio":"25,50","ayudaPrecio":null}` y
`R3-N2b TRAS ELEGIR ROJO: {…,"precio":"25,50","ayudaPrecio":"El catálogo tiene 9,00 Bs; se conserva el precio que escribió."}`.
No lo trajo esta ronda (el código de 43faa7c2 da lo mismo), pero es un hueco del modelo de origen. Corrección: el origen
va por valor, no por evento; si el valor vuelve a ser el que puso el catálogo, se repone como suyo. Pruebas en el panel.

**[MENOR] 2.** `tecleadas` va por índice y sobrevive a una precarga que reemplaza las tablas (`ComponerPartida.tsx:247-248`).

**[MENOR] 3.** Si la consulta del aviso de lista falla, el fallo queda guardado y no se reintenta (`TablaInsumos.tsx:243-256`).

**[MENOR] 4.** El Simulador no pone tope a lo elegido en la pantalla; con más de 200 el 422 se ve como «estado 422».

**[MENOR] 5.** Los números del ERS (RF-163, RF-164, RNF-30) chocan con el diseño de bienvenida, que por ruling usa RF-160
a RF-166 y RNF-30 y deja RNF-29 al autocompletado.

**[MENOR] 6.** DESIGN.md:250 cita un aviso de fecha que el código ya no produce.

**[MENOR] 7.** El aviso de Control no está en una región viva (WCAG 4.1.3).

**[MENOR] 8.** Asuntos de commit con tildes (be3631d1, 7dc15231, e34e92fe; E1 pide sin tildes); el CHANGELOG no recoge
las reglas nuevas del Simulador; `logicaBusqueda.ts:115` sigue con `\p{Diacritic}`.

**Sin defecto:** borrar una fila desplaza `tecleadas`; cada tabla tiene su estado; Componer no guarda borrador; la región
`#componer-fecha-estado` cumple 4.1.3; `[]` pasó a «ninguno» sin regresión en la pantalla; el 422 ya no devuelve lo
enviado.

**Sospechado:** la consulta del aviso busca por descripción con límite 20; si el código no sale entre esos 20, el aviso
queda en «puede regir otra lista».

**APROBADO SI:** se corrige el MAYOR 1 con sus pruebas; recomienda además los MENOR 2, 3 y 5. **Juicio de conjunto:** todo lo
demás está sano; con ese arreglo la rama queda para la prueba de Eugenio en el navegador y la fusión.
