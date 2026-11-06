# F6 · T5 · Opus en Antigravity (2026-11-04): APROBADO con 4 menores (Claude Opus 5.5 High)

> Segundo arbitraje de T5 (cierre del bloque A), por separado del de Flash. Encargo de solo lectura y solo git.
> Respuesta literal; guardada por Claude.

VEREDICTO: **APROBADO**
Ronda: 1   Base: 6e021594   Cabeza: 5fa8f3fa

**Qué comprobé yo (solo git, sin pytest, npx, npm ni uv):**
- `git diff --stat 6e021594..5fa8f3fa`: los 22 archivos están en `frontend-desktop/`. `core/`, `api/`, `aplicacion/` y `docs/` no cambian.
- En el diff no se añade ningún `.skip`, `.only`, `xfail`, `eslint-disable`, `@ts-ignore` ni `parseFloat`/`Number(`.
- **Rojo (A1):** en c0edbfff, `espacios.test.ts` ya importa `vistaDeLaSeccion`, y esa función todavía no existe en `espacios.ts`. Las pruebas de la barra de la obra tampoco pueden pasar, porque la barra aún no está. Rojo real, en commit aparte.
- **Oráculos (A2):** `TABLA_2_4_OBRA` y `SUBVISTAS_DEL_CONTRATO` están escritas a mano desde el contrato.
- **Pruebas retiradas de `BarraLateral.test`:** las que salieron (sección sin permiso, «Tramos» con el módulo vial, sección actual marcada) tienen reemplazo en `Marco.test.tsx`, en el bloque «la barra de la obra y las subvistas».
- **C1:** `ofertaDe` solo amplía qué secciones se ofrecen, como pide el contrato §2.1. La pantalla sigue protegida por `PantallaDeRuta`: hay una prueba de «Sin permiso» al escribir a mano una subvista. A rita no se le abre nada nuevo: ya tenía `aprobar_version`.
- **D1/D2:** `BarraDeEspacio` no pone encabezados. El foco se queda en el enlace del conmutador al cambiar de subvista. La lista plana se recorre con Tab y las flechas no mueven el foco; hay pruebas de las dos cosas.

**Tus cinco puntos:**
1. **`BarraDeEspacio` pregunta por cambios sin guardar:** el cambio es correcto y era necesario. Las barras ahora están dentro de `<main>`, y `Marco.alClicAntes` deja pasar sin preguntar los clics en enlaces de ahí (`Marco.tsx:264-270`). Reutiliza `useNavegarSeguro` y `formulariosSucios(ruta)`, así que el borrador de la Hoja sigue sin contar al pasar de Partidas a Componer. No pregunta dos veces. Lo cubren dos pruebas: `ProveedorDeLaHoja.test` («de Componer a otra sección sí pregunta») y el bloque «Marco: salir de una sección o subvista». De paso corrige el mismo hueco en las barras de herramientas de T4.
2. **`busqueda.test.ts` cambiado en el verde:** es un ajuste aceptable. Solo se estrecha el escenario de la prueba, que es consecuencia directa del contrato §2.1. Las afirmaciones no se debilitan y el valor esperado sigue escrito a mano. Habría quedado más limpio en el commit rojo, donde también pasaba.
3. **Direcciones viejas de subvistas:** lo conecto con el hallazgo 1.
4. **`ZonaEmpresa` y `ABSORBIDAS`:** dejarlos para después tiene sentido, porque retirar `ZonaEmpresa` sin `/cuenta` quitaría Administración y Ayuda. Lo conecto con el hallazgo 2.
5. **Las dos «Partidas»:** ver la decisión para Eugenio, al final.

**HALLAZGOS (todos MENOR; no bloquean):**
1. **[MENOR] E2/A2 · `Marco.tsx:489`:** la regla «con consulta y sin obra en la sesión, se abre en su sitio» ahora vale también para las subvistas. El contrato §2.4 no la recoge; dice «sin obra, a Pendientes». La única prueba es `/aprobar?envio=12` (`Marco.test.tsx:157` y `:220`), que es una sección. Corrección: enmendar el §2.4 con esa excepción y añadir una prueba con una subvista (por ejemplo, `/reajuste?x=1`).
2. **[MENOR] F1 · `BarraLateral.tsx:17` y `:153`, `paginas/pendientes/logica.ts:9-12`:** el plan dice que T5 retira `ZonaEmpresa`, y el contrato §2.4 sustituye `ABSORBIDAS`. Ninguna de las dos cosas se hizo. Aplazarlas es razonable y no rompe nada respecto a la base, pero hoy tiene dos efectos:
   - un pendiente de «actualizar precios» abre Estudio de mercado en vez de Actualizar precios;
   - quien entrega paquetes sin `aprobar_version` ve ese pendiente sin acción, porque `Bandeja.tsx:153` comprueba la pantalla `aprobar`.

   Corrección: pasar las dos casillas en el plan a T6 o T8, con dueño.
3. **[MENOR] B2 · `BarraDeEspacio.tsx:33`:** repite la guarda de clic modificado de `Marco.tsx:264`. Corrección: sacarla a una sola función compartida, por ejemplo en `shell/navegarSeguro.ts`.
4. **[MENOR] Comentarios · `EspacioDeObra.tsx:142`, `ubicar.ts:50` y el mensaje del commit:** dicen que una subvista desconocida lleva a la pantalla principal. Lo que hace `vistaDeLaSeccion` (`espacios.ts:151`) es llevar a la primera usable, que es lo que pide el contrato §1. Corrección: ajustar los comentarios a lo que hace el código.
5. **[Sin verificar]** El plan pide medir cuánto alto le queda a la Hoja a 1366×768 con letra Muy grande. No pude medirlo, porque no tengo navegador ni permiso para ejecutar. Lo que reportó Claude no menciona Muy grande. Lo tiene que medir Claude, o quedar para la pasada de T9.

**APROBADO SI:** nada pendiente; los MENOR quedan para el implementador.

**Decisión para Eugenio (punto 5):** recomiendo que la opción del conmutador diga **«Presupuesto»** en lugar de «Partidas» (`espacios.ts:116`).
- Así coincide con el h1 de esa pantalla (`hoja/index.tsx:384`), igual que hace «Resumen» en su sección.
- Deja de chocar con la pestaña «Partidas» de abajo, que es solo una parte de la Hoja.
- El precio es que «Presupuesto» aparece en la barra de la obra y en el conmutador, igual que ya pasa con «Resumen».

La etiqueta «Partidas» venía de mi propio diseño (adenda A.1): si Eugenio lo acepta, enmiendo esa adenda. El cambio de código es una línea en `espacios.ts` más los textos de las pruebas.

No escribí en la bitácora porque el encargo era de solo lectura y solo con git.
