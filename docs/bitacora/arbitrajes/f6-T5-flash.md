# F6 · T5 · Flash (2026-11-04): APROBADO, sin hallazgos (Gemini 3.8 Flash High)

> Encargo acotado a los 4 puntos de riesgo (quedaEnLaHoja, pregunta de cambios sin guardar en BarraDeEspacio, rutas de
> subvistas sin bucles, pruebas de la barra lateral). Respuesta literal; guardada por Claude.

**VEREDICTO: APROBADO**

**Verificado por mí:**
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/secciones.ts`
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/secciones.test.ts`
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/BarraDeEspacio.tsx`
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/BarraDeEspacio.test.tsx`
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/Marco.tsx`
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/Marco.test.tsx`
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/espacios.ts`
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/espacios.test.ts`
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/EspacioDeObra.tsx`
- `git diff 6e021594 5fa8f3fa -- frontend-desktop/src/marco/BarraLateral.test.tsx`

---

### Evaluación de los 4 puntos de riesgo:

1. **`secciones.ts` (`quedaEnLaHoja`):**
   - **No hay falsos positivos**: `camino.startsWith(`${seccion}/`)` exige la barra final `/` tras el ID de la sección (`/presupuesto/`). Un prefijo como `presupuestos` o `versiones2` no coincide ni por igualdad ni por prefijo (probado en [secciones.test.ts](file:///frontend-desktop/src/marco/secciones.test.ts#L165-L168)).
   - **No omite advertencias indebidas**: Solo devuelve `true` si el destino coincide con `SECCIONES_CON_HOJA` (`presupuesto`, `archivos`, `versiones` o sus subvistas) para la **misma** carpeta y obra. Navegar a otra sección (`control`, `tramos`, etc.), otra obra o fuera de la obra devuelve `false` y pregunta como antes.

2. **`BarraDeEspacio.tsx` (`alPulsar`, `formulariosSucios`, `useNavegarSeguro`):**
   - **Correcto y seguro**: `alPulsar` solo deja pasar sin interceptar clics con modificadores (Ctrl/Cmd/Shift/Alt/botón central, que abren otra pestaña sin perder el formulario actual) o cuando `formulariosSucios(ruta).length === 0`.
   - Con cambios sucios, cancela el evento nativo con `e.preventDefault()` y delega en `navegarSeguro(ruta)`. Si el usuario pulsa «Quedarme», la navegación se detiene. Al pulsar con teclado (`Enter` sobre el enlace), el evento `click` se dispara y pasa por la misma guarda. No hay fuga de navegación no vigilada.

3. **`Marco.tsx` / `EspacioDeObra.tsx` / `vistaDeLaSeccion`:**
   - **Subvista conocida no usable**: `vistaDeLaSeccion` encuentra la subvista, retorna `redirigeA: null` y monta su página; [Marco.tsx](file:///frontend-desktop/src/marco/Marco.tsx) (`PantallaDeRuta`) muestra el estado vacío «Sin permiso» (o «Apagada») en el cuerpo sin redirigir ni dejar pantalla en blanco.
   - **Sección sin raíz usable**: Redirige con `replace` a su primera subvista usable (ej. Aprobaciones → `/aprobaciones/revisar`). En el siguiente renderizado, al ser conocida, `redirigeA` es `null`, resolviendo en un solo salto.
   - **Subvista desconocida**: Redirige con `replace` a la raíz de la sección (o primera usable). En el siguiente renderizado, `redirigeA` es `null`.
   - **Sin bucles ni pantallas en blanco**: Toda redirección termina en máximo un salto hacia una ruta con `redirigeA === null`; el contenido está cubierto por `Suspense` y `LimiteDeError`.

4. **`BarraLateral.test.tsx` (pruebas conservadas, eliminadas y reemplazadas):**
   - **Comprobado con el diff**: Las únicas 2 pruebas eliminadas sin reemplazo en este archivo corresponden a la interacción de árbol colapsable WAI-ARIA (`flecha derecha despliega...` y `flecha izquierda en una sección vuelve a su obra`), las cuales ya no aplican al convertirse la barra lateral en una lista plana de enlaces.
   - El comportamiento de secciones de la obra, permisos de sección y conmutación según módulos encendidos/apagados (ej. `Tramos`) fue trasladado a [Marco.test.tsx](file:///frontend-desktop/src/marco/Marco.test.tsx#L450-L515) para probar la nueva `BarraDeEspacio`. En `BarraLateral.test.tsx`, la accesibilidad por teclado plana se verifica con `Tab`, `Enter` y la confirmación de que las flechas ya no mueven el foco.

---

**HALLAZGOS:** ninguno
