# F6 · Ajuste de menores T5/T6 · Flash (2026-11-05): APROBADO, sin hallazgos (Gemini 3.8 Flash High)

> Encargo acotado a 4 puntos de riesgo (permisos de Pendientes, pruebas cambiadas, esClicSimple, enmiendas de
> documentos). Commits 1314ec18, f72e833e, 9ef7b79c y 694dccbf. Solo git. Respuesta literal; guardada por Claude.

**VEREDICTO: APROBADO**

**Verificado por mí:**
- `git log -n 6 --oneline 694dccbf`
- `git diff --stat 385383e1 694dccbf`
- `git diff 385383e1 f72e833e -- frontend-desktop/src/paginas/pendientes`
- `git diff 385383e1 f72e833e -- "*.test.ts" "*.test.tsx"`
- `git diff 385383e1 f72e833e -- frontend-desktop/src/shell/navegarSeguro.ts frontend-desktop/src/marco/BarraDeEspacio.tsx frontend-desktop/src/marco/Marco.tsx`
- `git diff 385383e1 1314ec18 -- docs`
- `git diff 385383e1 694dccbf -- api/rutas/produccion_planta.py tests/integration/test_api_produccion_publicar.py`

---

### Evaluación de los 4 puntos de riesgo

1. **A. Permisos en Pendientes:**
   - **No deja pasar a quien no deba:** Al eliminarse `ABSORBIDAS`, `paginaQueAbre(p)` devuelve directamente el `id` de la subvista (`actualizacion`, `entregar`, etc.). Por tanto, `usable` evalúa el permiso de esa subvista específica. Por ejemplo, «Actualizar precios» requiere `editar_hoja`; quien solo revisa no la tiene, `puede` resulta `false` y el botón no se muestra. A la par, quien tiene `entregar_paquete` pero no `aprobar_version` ahora sí ve «Entregar», corrigiendo el bloqueo anterior.
   - **Pantallas desconocidas seguras:** Ante un `id` inexistente, `destino()` resuelve a `seccionPorId("resumen")?.pagina` (`"obras"`), y `rutaOPendientes()` dirige a `/obra/:c/:o/resumen` (o `/inicio/pendientes` como salvaguarda ante nulo). No hay enlaces muertos.

2. **B. Pruebas existentes:**
   - **Ninguna prueba se debilitó:**
     - En [logica.test.ts](file:///C:/Users/euger/OneDrive/Escritorio/TESIS/frontend-desktop/src/paginas/pendientes/logica.test.ts): «tablero» salió de la lista de desconocidas porque pasó a ser formalmente una subvista de Resumen (`resumen/tablero`), con prueba propia. La lista de desconocidas reemplazó «tablero» por «no_existe», conservando `""`, `toString` y `constructor`.
     - En [EntregarDesdeAprobaciones.test.tsx](file:///C:/Users/euger/OneDrive/Escritorio/TESIS/frontend-desktop/src/paginas/aprobar/EntregarDesdeAprobaciones.test.tsx): La navegación desde el pendiente ahora prueba el arribo directo a la subvista `<h1>Entregar paquete</h1>`, mientras que el recorrido a través del enlace interno desde «Aprobar una versión» se preservó íntegro en una prueba separada.
     - En [CostoPorTonelada.test.tsx](file:///C:/Users/euger/OneDrive/Escritorio/TESIS/frontend-desktop/src/paginas/produccion/CostoPorTonelada.test.tsx): Los textos esperados se actualizaron al nuevo copy («de la Cuenta, «Empresa y tema»») conservando todas las aserciones funcionales y el `href === "/cuenta/empresa"`.

3. **C. `esClicSimple`:**
   - **Condición idéntica sin inversión de ramas:** La guarda original `if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;` equivale formalmente a `if (!esClicSimple(e)) return;` por doble negación (`esClicSimple` niega exactamente esa disyunción). Cubierto con suite unitaria exhaustiva en [navegarSeguro.test.tsx](file:///C:/Users/euger/OneDrive/Escritorio/TESIS/frontend-desktop/src/shell/navegarSeguro.test.tsx).

4. **D. Enmiendas de documentos:**
   - **Fieles al código y consistentes:** Reflejan fielmente el comportamiento de `Marco.tsx:RutaVieja` para rutas viejas con consulta sin obra en sesión (aplicable a secciones y subvistas), y la adenda A.1 documenta con precisión el renombramiento de la subvista a «Presupuesto» en congruencia con `SUBVISTAS` y el encabezado `<h1>`.

---

**HALLAZGOS:** ninguno.
