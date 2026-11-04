# F6 · plan · ronda 2 (2026-11-04): APROBADO

> Respuesta literal de Antigravity (`agy -p --sandbox`), guardada por Claude. Solo se cambiaron los enlaces
> absolutos por relativos.

**Veredicto:** APROBADO

**Resumen:** Los 6 hallazgos de la Ronda 1 (4 mayores y 2 menores) quedaron verificados y resueltos en [`PLAN_REDISENO_F6.md`](../../../docs/planes/PLAN_REDISENO_F6.md). No hay hallazgos bloqueantes ni mayores nuevos; el plan está listo para ejecutarse.

### Comprobación de hallazgos de Ronda 1
1. **M1 (`oferta.ts` y `busqueda.ts`):** **Resuelto** en Tarea 3 (`conSitio` suma `ESPACIOS`, `SECCIONES_DE_CUENTA` y `SOLO_BUSCADOR`; el buscador resuelve la ruta nueva de cada herramienta).
2. **M2 (`pendientes/logica.ts`, `recorrido.ts`, `PanelRecorrido.tsx`):** **Resuelto** en Foco 6 y Tarea 3 (`destino` consulta `espacioDeLaPagina`, y `pasoDeRuta` / enlaces del recorrido usan la ruta del espacio, con pruebas rojas explícitas).
3. **M3 (`ubicar.ts` y títulos del documento):** **Resuelto** en Tareas 3, 5 y 6 (títulos para `/:espacio/:herramienta`, `/cuenta/:seccion` y `/inicio/:vista`).
4. **M4 (`usePendientes.ts`, redirecciones de Cuenta y `tomarVueltaACarpetas`):** **Resuelto** en Tareas 5 y 6 (redirecciones de `#/empresa/personas`, `#/administracion`, `#/empresa/ayuda` y `#/acerca`; retiro de `ENTRADAS_DE_EMPRESA`/`ZonaEmpresa.tsx`; vuelta a `#/cuenta/carpetas`; recarga en [`usePendientes.ts`](../../../frontend-desktop/src/marco/usePendientes.ts#L36-L46) al entrar a `/inicio/general` o `/inicio/pendientes` y enlace en [`EspacioDeObra.tsx`](../../../frontend-desktop/src/marco/EspacioDeObra.tsx#L81)).
5. **m1 (Segmentos explícitos de ruta y marca «Sílice» en `BarraSuperior.tsx`):** **Resuelto** en Tarea 1 Paso 3 y Tarea 5.
6. **m2 (Descarte de borradores en `DELETE /v1/sesion`):** **Resuelto** en Tarea 5 Paso 3.

### Hallazgos nuevos

#### Bloqueantes
Ninguno.

#### Mayores
Ninguno.

#### Menores (notas para el constructor, no bloquean)
- **[m1] `tablero` no tiene `modulo` en `shell/rutas.ts`:** En [`PLAN_REDISENO_F6.md`](../../../docs/planes/PLAN_REDISENO_F6.md#L41) (D1 y [l. 188](../../../docs/planes/PLAN_REDISENO_F6.md#L188)) se menciona `Tablero` y `Riesgo` «solo si su módulo está encendido», pero en [`rutas.ts`](../../../frontend-desktop/src/shell/rutas.ts#L103-L109) `tablero` solo exige `accion: "leer_proyecto"` y no tiene `modulo` (los 4 módulos de [`modulos.py`](../../../aplicacion/modulos.py#L22) son `produccion`, `vial`, `edificacion`, `riesgo`). En la prueba de la Tarea 4 bastará comprobar el apagado de módulo con `tramos` (`vial`) y `riesgo` (`riesgo`), y el permiso de `tablero` con `leer_proyecto`.
- **[m2] Oráculo previo de `tablero` y `actualizacion` en `paginas/pendientes/logica.test.ts`:** En [`logica.test.ts`](../../../frontend-desktop/src/paginas/pendientes/logica.test.ts#L45-L62) `"tablero"` se usaba como ejemplo de pantalla sin sección de obra (que caía al Resumen) y en [`logica.ts`](../../../frontend-desktop/src/paginas/pendientes/logica.ts#L8-L11) `ABSORBIDAS` aún mapea `"actualizacion" -> "mercado"`. Al sumar `tablero` a `SECCIONES_DE_OBRA` (Tarea 1) y `actualizacion` al espacio de Precios (Tarea 3), el constructor deberá actualizar ese test en `logica.test.ts` y decidir si `actualizacion` sale de `ABSORBIDAS` hacia `/precios/actualizar`.
