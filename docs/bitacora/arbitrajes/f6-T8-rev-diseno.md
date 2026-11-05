# F6 · T8 · Revisor de diseño de Claude (2026-11-05): APROBADO, 3 menores (`silice-rev-diseno`)

> Sustituye al arbitraje de Opus en Antigravity, que quedó sin cuota (`Individual quota reached`, ~141 h desde el
> 2026-11-05). Es un revisor de la misma familia que el constructor: veredicto **menos independiente**. Diff
> `da02b17b..534040e0`. Respuesta literal (sin las rutas absolutas del equipo); guardada por Claude.

VEREDICTO: APROBADO (sin bloqueantes ni mayores; 3 menores, ninguno impide cerrar T8)

**Verificado por mí:**
- `git diff da02b17b 534040e0` leído en lo relevante: paginas/inicio/{index,CarteraYAvance,LoQueBloquea,textos,inicio.scss}, indicadores/FranjaDeCifras.tsx, marco/{EspacioDeInicio,BarraLateral,Marco,espacios,secciones,ubicar,usePendientes,oferta}, shell/rutas.ts, api/tipos.ts.
- `npx vitest run src/paginas/inicio/VistaGeneral.test.tsx`: 35/35 verdes. No corrí la suite completa ni lint.
- Cruce contra PLAN T8, contrato de rutas §1/§4, diseño visual §3.1 y B.1/B.2, y DESIGN/skill.
- Búsqueda de hex/rgb sueltos en paginas/inicio/*.scss|tsx y FranjaDeCifras: ninguno. Colores solo por `--silice-*` y `--cds-*`.
- Cifras: no se recalcula nada. `centesimasEsVe` y `formatoEsVe` trabajan sobre texto y BigInt (formatoEsVe.ts:34-43). `Number()` solo sirve para el ancho de la barra (CarteraYAvance.tsx:36-40), y la cifra que se lee es el texto del servidor. Los totales por moneda llegan de `por_moneda` y nunca se suman (CarteraYAvance.tsx:83-101).
- Encabezados: un solo h1 en index.tsx:41, h2 por bloque con `aria-labelledby` (bloquea, cartera, obras, auditorías, arenera). La cabecera del espacio usa `<p>`, sin h1, como pide B.1.
- Estados por bloque: cargando con `role=status` y `aria-busy`, error con `AvisoError`, no_disponible, vacío con o sin permiso para crear, y aviso de carpetas omitidas. Un bloque que falla no tumba a los demás.
- Español llano: ni «dashboard» ni «KPI» en textos.ts.

**Juicio de las 7 decisiones:**
1. `centesimasEsVe`: correcto. Es la función existente para dinero, sin float, y coincide con el criterio del plan («334570.5» se ve «334.570,50»).
2. `FranjaDeCifras`: aceptable. Inventar meta y Δ para llenar `IndicadorFiori` sería una cifra que el servidor no dio. Reusa las clases `franja-indicadores` y `fiori-kpi` sin estilos aparte. Se aparta de la letra del plan (T8 decía `IndicadorFiori`/`FranjaIndicadores`); conviene dejarlo anotado al actualizar el plan o DESIGN en T9.
3. Ruta desconocida → Vista general: aceptable. Es coherente con contrato §1 («desconocida → primera usable de su nivel») y con la ruta índice. `/pendientes` redirige a `/inicio/pendientes` con replace y conserva la consulta.
4. «inicio» como pantalla 32: aceptable. Las pruebas de rutas dicen «31 del contrato + Vista general» y `oferta.ts` la excluye de las «sueltas». El contrato dice «Las 31 pantallas» (§2, línea 33 y 72), así que T9 debe anotar la 32.ª.
5. Carpeta homónima desde la cartera: aceptable. Reusa `obrasConMismoNombre`, con la misma regla de la barra y la bandeja.
6. Pasos con `destinoDelPendiente`/`paginaQueAbre` y `usable`: aceptable. Sin permiso se muestra «sin permiso» en lugar del enlace, sin 403. B.2 citaba `rutaCanonica`, pero estas funciones son las mismas que usa la bandeja, así que no divergen.
7. Sin `leer_proyecto`, no se piden cartera, avance ni auditorías: aceptable. `useCarga(null)` da `sin_permiso`, el bloque se omite y no se genera un 403 en la consola.

**IBCS en las barras:** real con relleno sólido (`--silice-texto`) y plan con contorno, según indicadores.scss:181-203. Los dos porcentajes se recortan a 0–100, así que todas las filas comparten la misma escala. Cada barra lleva su rótulo «Real X % · Plan Y %» y la barra es `aria-hidden`. No hay rojo ni verde: cero colores semánticos inventados, y la barra no va por signo. Aquí solo hay severidad en la urgencia, con ícono y texto, no solo color.

**Barra lateral contra §3.1 punto 1:** cumple. Texto «Vista general», `aria-label` `Vista general, {porHacer(total)}` solo con total > 0, `Pildora` a la derecha, y `aria-current` activo en `/inicio/general` y en `/inicio/pendientes` (BarraLateral.tsx:132-139). El destino es `/inicio/general`; §3.1 decía `RUTA_DE_PENDIENTES` o `RUTA_DE_INICIO` «en cuanto entre T6», y el plan y el contrato posteriores mandan la Vista general, así que el cambio es correcto.

**HALLAZGOS**
1. [MENOR] frontend-desktop/src/paginas/inicio/CarteraYAvance.tsx:17-23. `ETAPA_TEXTO` duplica en el cliente `ETAPA_TEXTO` de aplicacion/mesa.py:86. Hoy los textos coinciden. Se hace porque `ObraDeLaCartera` (api/rutas/obras.py:422) no trae `etapa_texto`. Corrección: añadir `etapa_texto` a `ObraDeLaCarteraRespuesta` (el servidor ya tiene el diccionario) y quitar la tabla del cliente. Si se quiere dejar así, anotar en el comentario que debe seguir a mesa.py. No bloquea.
2. [MENOR] frontend-desktop/src/paginas/inicio/inicio.scss:30-36 con tokens.scss:25 (`--silice-sev-advertencia`, yellow-30). El ícono de «Aviso» sobre fondo claro queda por debajo de 3:1 como gráfico. La palabra «Aviso» va en tinta normal, así que el color no es el único portador. La Bandeja usa el mismo token, así que no es nuevo de T8 y es una decisión de tokens (DESIGN), no de esta pantalla. No pude medirlo en navegador; el valor sale del color nominal, no de una medida. Anotarlo para T9 o DESIGN.
3. [MENOR] frontend-desktop/src/paginas/inicio/CarteraYAvance.tsx:46-52. Las barras miden 3 px por serie dentro de 6 px (indicadores.scss:181-203, heredadas). Con letra «Muy grande» o baja visión pueden costar de leer. Está mitigado porque el rótulo con las cifras va al lado. No lo pude comprobar en navegador. Opcional: dar la barra un alto mínimo propio en `.silice-inicio__avance`.

**No verificado (requiere navegador):** medidas de contraste reales, foco visible de los enlaces y de la tabla, el aspecto con letra «Muy grande» (1056 px) y el orden de tabulación. Por el código, `Link` con `cds--link` y `Table` de Carbon traen el foco propio, y h1 tiene `tabIndex={-1}`.
