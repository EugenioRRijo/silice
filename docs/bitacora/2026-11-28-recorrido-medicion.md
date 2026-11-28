# Recorrido de UX en modo medición (T2 del plan de cierre, 2026-11-28)

Plan: [2026-11-28-plan-cierre-rama-front.md](../planes/2026-11-28-plan-cierre-rama-front.md), tarea T2. Siembra ficticia
del propio guion (`sembrar_datos`): ningún libro ni dato de la empresa.

## Corrida completa

`scripts/recorrido_ux_playwright.py --medir-carga`, sin `--funcional`: los 3 roles (admin, ana, rita), los 3 anchos
(1056, 1366 y 1920 px) y los 3 tamaños de letra. 891 mediciones, 540 de pantallas que el rol tiene a la vista.

| Medida | Resultado |
|---|---|
| Un solo `h1` por pantalla | 522 de 540; las 18 restantes, el paso «con recorrido» de Libro (ver abajo) |
| Desplazamiento horizontal | ninguno |
| Errores de consola y de red | ninguno |
| Botones sin nombre | ninguno |
| Violaciones de axe fuera de `AXE_DE_REFERENCIA` | ninguna en las pantallas; una en Libro con el recorrido (ver abajo) |
| Textos recortados en la barra de arriba | sí, a 1056 y 1366 px con letra Normal y a 1920 px con Muy grande: pasa a T3 |

La corrida se hizo con la compilación del 2026-11-27 19:43 (`npm run dist` solo verifica la compilación, no la hace;
compilar es `npm run build`). Lo confirmado después solo tocó la cola de «Quitar», «Últimas auditorías» y la fila
«Aprobada» de Solicitudes.

## Lo que encontró y cómo se cerró

1. **El guion no llegaba a «Auditar con recorrido guiado».** Desde B2 el botón vive dentro del plegado «Más opciones»
   y Playwright esperaba a verlo. Las 18 mediciones con recorrido daban error. El guion ahora abre «Más opciones»
   antes de pulsarlo.
2. **Axe `scrollable-region-focusable` en `.lista-hallazgos__cuerpo`** (Libro de la empresa, con el recorrido y un
   libro sin hallazgos). La lista vacía se desplaza y no tenía nada enfocable, así que no se podía leer con el teclado
   (WCAG 2.1.1). Es nueva porque esa medición nunca había llegado a correr. Ahora el cuerpo es una región «Lista de
   hallazgos» en el orden de Tab, con su prueba (`visor/ListaHallazgos.test.tsx`).
3. **Repetición con la compilación nueva** (ana y rita, 1056 y 1366 px, letra Normal): Libro con el recorrido, un
   `h1` y axe vacío; el inicio de Auditoría conserva solo la violación de la referencia
   (`auditoria`, `scrollable-region-focusable`). La columna del recorrido se ve y no solapa.

## Para T3 (revisión visual)

- La barra de arriba: a 1366 px con letra Normal se lee «Carpeta activa: de…» y el buscador corta su atajo «(…».
  La regla escrita en `marco/BarraSuperior.scss` es que primero ceda el buscador hasta su icono y luego se recorte el
  contexto; hoy la carpeta se recorta antes que el contexto.
- Libro de la empresa con la columna del recorrido a 1366 px: el texto de ayuda de la fecha se monta sobre el texto
  del informe en PDF, y la lista de hallazgos queda muy baja.
