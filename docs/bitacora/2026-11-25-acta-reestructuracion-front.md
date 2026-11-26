# Acta: reestructuración del front antes de medir con personas

**Fecha:** 2026-11-25. **Decide:** Eugenio. **Redacta:** el orquestador (Claude).

## Contexto

- El consejo del 2026-11-23 congeló el código: «nada de código nuevo antes de defender»
  ([plan](../planes/2026-11-23-plan-auditoria-no-circular.md)).
- El 2026-11-25 se auditó el front ([informes A a E](../planes/auditoria-front-2026-11-25/)) y se redactó una propuesta de
  UX y UI según la guía *modern-web-guidance* de Google ([propuesta](../planes/2026-11-25-propuesta-ux-ui.md)).
  - **A:** diez cambios incrementales.
  - **B:** navegación por tareas, con tres superficies por obra.
- Un consejo de cinco asesores revisó la propuesta, con revisión cruzada a ciegas y un presidente. Recomendó no tocar el
  front antes de defender. También dejó un hecho que cambia el cálculo: **todavía no se ha medido nada con personas**, así
  que reestructurar ahora no rompe ninguna comparación. Lo que invalida una medición es cambiar el programa entre una
  sesión y otra.

## Decisión

Eugenio decide reestructurar el front **antes** de la prueba con personas y medir sobre la versión nueva:

| Fase de B | Qué | ¿Antes de medir? |
|---|---|---|
| B0 | Base común: el cliente de la API con el 401 en un solo lugar y analizadores, `Dialogo`, `Anunciador`, el foco y el título al navegar, `MontoExacto` y `CampoDeCifra` | Sí |
| B1 | Superficie Presupuesto: la tabla, el total fijo, la columna «Problemas» y el inspector lateral (T1, T2 y T3) | Sí |
| B4 | Inicio unificado y Versiones y entregas | Sí, el Inicio. Versiones, si alcanza |
| B2 | Auditar un libro en un solo flujo (lo usa la prueba de las 6 alertas) | Sí |
| B3 | Ejecución al corte en una página | No: después de defender |
| B5 | Rutas viejas, manual, guías y guardias | Solo lo necesario para que nada quede roto |

**Fecha tope: 2026-12-16.** Ese día se congela la versión nueva con la etiqueta `medicion-v1`. Lo que no esté terminado
queda para después de defender. Desde la primera sesión con personas hasta la última **no cambia nada**.

## Límites (no se negocian)

- `core/` no cambia (NORMAS; `scripts/guardia_nucleo.py`).
- No cambia ningún archivo sellado por la etiqueta `reglas-congeladas-2026-11-24`: las reglas, los umbrales,
  `aplicacion/causas_raiz.py`, el plan no circular y la taxonomía de plantilla. Si B2 necesita códigos estables en los
  hallazgos, se agregan en una capa de presentación fuera de esos archivos, y una prueba compara las huellas con la
  etiqueta.
- `aplicacion/hoja.py` (experimento de la tesis) solo cambia con una nueva acta de re-congelado.
- Ningún libro real ni nada derivado de él entra al repositorio (NORMAS §1).

## Cómo se trabaja

- **Antes de cada pantalla:**
  - se escribe su ficha de 10 partes (skills `disenar-desde-la-tarea` e `interfaz-silice`);
  - se consulta la guía de Google, y cada cambio cita la guía que sigue.
- **TDD:** prueba en rojo antes del código. Al cerrar cada fase, la suite completa y un árbitro.
- **Antes de la primera sesión:**
  - un piloto cronometrado de T1 a T3 con una persona ajena;
  - una prueba de instalación de la versión etiquetada en cada equipo donde haya sesión.

## Lo que sigue en paralelo (no espera al front)

Viene del veredicto del consejo:
- Buscar a las 5 personas, con fecha. Si al 2026-12-10 no hay día y hora, se activa el plan B de participantes:
  estudiantes de ingeniería civil o presupuestistas externos.
- Contactar al experto y resolver dónde revisa los libros, que no salen del equipo de Eugenio.
- Enviar al tutor un correo con los instrumentos (4 instrumentos y 16 ítems) y los criterios de éxito fijados antes de
  medir: umbral del SUS, acierto y tiempo máximo en T1 a T3, y cuántas alertas deben entenderse. El correo pide la
  ventana de defensa.
- La revisión del experto y la medición de detección de la Fase 3 no dependen del front.

## Consecuencias para la tesis

- El capítulo IV describe la versión `medicion-v1`.
- La auditoría del front y la propuesta entran como antecedente del diseño. Lo que quede fuera (B3, la Propuesta A
  restante) va a trabajo futuro.
- El congelamiento del 2026-11-23 sigue vigente para todo lo que no sea el front: auditoría, alertas, reglas y mercado
  (lista cerrada del consejo del 2026-11-24).

## Enmienda: lo que se decidió al construir B0 (2026-11-25)

- **Foco al navegar.** Cuando la persona cambia de espacio (de la Vista general a una obra, o a Producción, Precios o
  Cuenta), el foco va al título de la pantalla. Dentro del mismo espacio, el foco se queda en el enlace, como en unas
  pestañas. Es un punto medio entre la guía de Google («Update single-page application (SPA) titles during page
  transitions») y la decisión de F6, ya arbitrada (`docs/planes/PLAN_REDISENO_F6.md:167`).
  - Si la pantalla nueva ya enfocó un campo propio, se respeta.
  - Al crear una obra, el foco va al título de la obra nueva.
- **Título de la ventana.** Lo pone solo el marco y conserva el nombre de la obra.
- **Diálogos.** El título sigue siendo un `h2`, como pide DESIGN.md. La guía de Google pide `h1`, y esa decisión
  queda para Eugenio. La franja lateral de 4 px se quitó, porque era adorno.
- **Error de un campo de cifras.** Se anuncia medio segundo después de salir del campo. Eugenio no lo objetó.
- **Quién construye.** Gemini se quedó sin créditos y Eugenio decidió no contar con él hasta nuevo aviso. Construye
  Sonnet y audita Opus.
- **Skills, al pie de la letra.** Por pedido de Eugenio, ui-ux-pro-max, la guía de Google y ub-mode se aplican tal
  cual. Del sistema de diseño de ui-ux-pro-max se toma el estilo «Data-Dense Dashboard» y su lista previa a entregar.
  Sus colores y su tipografía no se toman, porque chocan con DESIGN.md y con el uso sin conexión.
- **Auditorías.** Opus hizo tres:
  - devolvió 5 hallazgos mayores y todos se corrigieron, con la prueba en rojo primero y una mutación por punto;
  - los menores también se corrigieron;
  - ninguna pantalla usa todavía las piezas: B1 será la primera.
