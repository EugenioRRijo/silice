# F6 · plan · ronda 1 (2026-11-04): DEVUELTO

> Respuesta literal de Antigravity (`agy -p --sandbox`), guardada por Claude. Solo se cambiaron los enlaces
> absolutos por relativos.

```
VEREDICTO: DEVUELTO
Ronda: 1   Base: b9f43cf8 (docs/plan-f6)   Cabeza: b9f43cf8 (árbol con PLAN_REDISENO_F6.md)
Verificado por mí:
- Lectura de AGENTS.md, docs/ESTADO.md y skills metodologia-silice, arbitro-independiente y colaboracion-con-claude desde docs/contexto-agentes (`git show docs/contexto-agentes:...`).
- Contraste de docs/planes/PLAN_REDISENO_F6.md contra docs/especificaciones/2026-11-04-rediseno-f6-espacios-design.md, frontend-desktop/src/shell/rutas.ts, frontend-desktop/src/marco/*, api/rutas/obras.py, aplicacion/mesa.py, api/rutas/sesion.py y api/caso_web.py.
- Ejecución de Vitest en sandbox (`npx vitest run src/marco src/shell src/paginas/sinJergaInterna.test.ts`): bloqueado por `EPERM` del sandbox de Windows al escribir `.vite-temp` en `node_modules`.
```

### Juicio sobre los 4 puntos del encargo

1. **Cobertura de la especificación (`§1–§3`):**
   Casi completa en las 7 tareas, salvo dos omisiones respecto a la especificación:
   - La barra superior (`BarraSuperior.tsx`) en la especificación §1 ([`2026-11-04-rediseno-f6-espacios-design.md:18`](../../../docs/especificaciones/2026-11-04-rediseno-f6-espacios-design.md#L18)) convierte la marca «Sílice» en enlace a `#/inicio/general` y muestra la carpeta activa; la Tarea 5 ([`PLAN_REDISENO_F6.md:186-187`](../../../docs/planes/PLAN_REDISENO_F6.md#L186-L187)) solo pide quitar `TamanoLetra` y las migas y llevar el botón de la persona a `/cuenta/preferencias`.
   - En `#/cuenta/ayuda` ([`2026-11-04-rediseno-f6-espacios-design.md:124`](../../../docs/especificaciones/2026-11-04-rediseno-f6-espacios-design.md#L124)) la especificación incluye el inicio de recorridos guiados además de `PaginaAcerca`; la Tarea 5 ([`PLAN_REDISENO_F6.md:202`](../../../docs/planes/PLAN_REDISENO_F6.md#L202)) solo monta `Acerca de Sílice`.

2. **Verificación de las decisiones D1–D5 del orquestador:**
   - **D1 es exacta (son 18 pantallas sueltas, no 14):** en [`shell/rutas.ts:32-296`](../../../frontend-desktop/src/shell/rutas.ts#L32-L296) hay **31** pantallas en `PAGINAS`. En [`marco/secciones.ts:20-47`](../../../frontend-desktop/src/marco/secciones.ts#L20-L47), `SECCIONES_DE_OBRA` ubica **8** (`obras`, `hoja`, `tramos`, `archivos`, `versiones`, `aprobar`, `mercado`, `control`) y `ENTRADAS_DE_EMPRESA` ubica **5** (`catalogo`, `auditoria`, `existencias`, `administracion`, `acerca`). En [`marco/oferta.ts:27-31`](../../../frontend-desktop/src/marco/oferta.ts#L27-L31), `31 - 13 = 18` pantallas caen en `sueltas`: las 14 listadas en la especificación más **`tablero`**, **`riesgo`**, **`componer`**, **`actualizacion`**, **`entregar`** y **`escenarios`** (restando `catalogo`, `auditoria` y `existencias` que ya estaban en `ENTRADAS_DE_EMPRESA`). El reparto de D1 (`8 + 2 = 10` en obra, `6 + 4 + 7 = 17` en los 3 espacios, `2` en `SOLO_BUSCADOR` y `2` en Cuenta = **31**) particiona exactamente `PAGINAS`.
   - **D2 es exacta:** verificado en [`api/rutas/obras.py:86-126,202-223`](../../../api/rutas/obras.py#L86-L126) y [`aplicacion/mesa.py:417-476`](../../../aplicacion/mesa.py#L417-L476), `GET /v1/obras/resumen` devuelve únicamente `cifras` (`valor_ganado` $\Sigma\text{EV}$ vs $\Sigma\text{PV}$ de obras en ejecución y `avance` $\Sigma\text{EV}\div\Sigma\text{PV}$), `conversiones`, `fuera_de_suma` y `obras[]` (con `total`, `avance_real` y `avance_plan` por obra). **No trae** suma ni meta de cartera total, ni serie temporal para curva S de cartera, ni desglose de APU de cartera, y [`UltimasAuditorias.tsx:9-17`](../../../frontend-desktop/src/paginas/inicio/UltimasAuditorias.tsx#L9-L17) (`GET /v1/auditorias-libro`) solo trae conteos (`errores`, `advertencias`), no $\Delta$ en dinero. D2 respeta la regla B3 («la interfaz no calcula»).
   - **D3, D4 y D5 son coherentes** con el código actual, con una salvedad sobre el aviso en la Tarea 5: en [`api/rutas/sesion.py:420`](../../../api/rutas/sesion.py#L420) `DELETE /v1/sesion` llama a `caso_web.olvidar(sesiones.huella_de(ficha))`, que en [`api/caso_web.py:44-46`](../../../api/caso_web.py#L44-L46) **sí llama a `hoja_borradores.olvidar(huella)`** y descarta los borradores en memoria del servidor al cerrar sesión (la afirmación de [`PLAN_REDISENO_F6.md:212-214`](../../../docs/planes/PLAN_REDISENO_F6.md#L212-L214) de que `sesion.py` no los descarta es un falso positivo).

3. **Coherencia de interfaces entre tareas:** hay **4 huecos mayores** y **2 menores** detallados abajo.

4. **Riesgos que faltan en el Foco de revisión (`PLAN_REDISENO_F6.md:47-58`):**
   - **Recorridos guiados (`RECORRIDO_AUDITAR`):** que el panel lateral de recorrido reconozca el paso activo y enlace bien cuando las pantallas de auditoría vivan bajo `/auditoria/:herramienta`.
   - **Acciones de pendientes y del Resumen que apuntan a herramientas de empresa:** que `destinoDeLaAccion` (p. ej. `VER_EL_CATALOGO` → `pagina: "catalogo"` en [`aplicacion/mesa.py:127,537`](../../../aplicacion/mesa.py#L127)) lleve a `#/precios/catalogo` y no caiga en el fallback del Resumen de la obra cuando `precios` salga de `ENTRADAS_DE_EMPRESA`.
   - **Regreso automático a «Carpetas de trabajo» tras cambiar de carpeta:** hoy [`paginas/administracion/index.tsx:61-65`](../../../frontend-desktop/src/paginas/administracion/index.tsx#L61-L65) usa `tomarVueltaACarpetas()` para reabrir la pestaña; con rutas separadas (`#/cuenta/carpetas`), al cambiar `generacion` en `Marco.tsx:153` la URL ya conserva la pestaña, pero hay que verificar que no redirija ni pierda el foco.
   - **Guardia léxica `sinJergaInterna.test.ts`:** [`sinJergaInterna.test.ts:48-55`](../../../frontend-desktop/src/paginas/sinJergaInterna.test.ts#L48-L55) inspecciona **todos** los archivos de `src/marco/**/*.ts(x)` y falla si aparece `módulo`, `área`, `página`, `carpeta de trabajo` (en singular) o `streamlit` fuera de comentarios.

---

### HALLAZGOS (DEVUELTO)

1. **[MAYOR] F1 / Coherencia entre tareas · [`PLAN_REDISENO_F6.md:126-138`](../../../docs/planes/PLAN_REDISENO_F6.md#L126-L138), [`marco/oferta.ts:24-33`](../../../frontend-desktop/src/marco/oferta.ts#L24-L33) y [`paginas/pendientes/logica.ts:20-27`](../../../frontend-desktop/src/paginas/pendientes/logica.ts#L20-L27) · Al vaciar `ENTRADAS_DE_EMPRESA` en Tarea 3 se rompen `ofertaDe` y `destinoDeLaAccion` sin que esos archivos estén en la tarea.**
   - En [`oferta.ts:27-31`](../../../frontend-desktop/src/marco/oferta.ts#L27-L31), `conSitio` solo reúne `SECCIONES_DE_OBRA` y `ENTRADAS_DE_EMPRESA`; si `oferta.ts` no se actualiza con `ESPACIOS` y `SECCIONES_DE_CUENTA`, las herramientas seguirán saliendo en `oferta.sueltas`.
   - En [`paginas/pendientes/logica.ts:20-27`](../../../frontend-desktop/src/paginas/pendientes/logica.ts#L20-L27), `destino(carpeta, obraId, id)` busca `ENTRADAS_DE_EMPRESA.find((e) => e.pagina === id)` para acciones de pendientes que van a pantallas de empresa (como `VER_EL_CATALOGO` con `pagina: "catalogo"` en [`aplicacion/mesa.py:127,537`](../../../aplicacion/mesa.py#L127)). Si `precios` sale de `ENTRADAS_DE_EMPRESA` y `logica.ts` no consulta `espacioDeLaPagina(id)`, un pendiente de catálogo llevará por error al Resumen de la obra.
   - **Corrección exigida:** Incluir `marco/oferta.ts` y `paginas/pendientes/logica.ts` en la Tarea 3 para que `ofertaDe`, `resultadosDe` y `destinoDeLaAccion` resuelvan las herramientas por `espacioDeLaPagina` y `rutaDeHerramienta`.

2. **[MAYOR] F1 / Coherencia entre tareas · [`PLAN_REDISENO_F6.md:126-153`](../../../docs/planes/PLAN_REDISENO_F6.md#L126-L153), [`shell/recorrido.ts:46-49`](../../../frontend-desktop/src/shell/recorrido.ts#L46-L49) y [`shell/PanelRecorrido.tsx:37,58`](../../../frontend-desktop/src/shell/PanelRecorrido.tsx#L37) · Las nuevas rutas de Auditoría dejan ciego el recorrido guiado.**
   - `pasoDeRuta(recorrido, ruta)` compara `rutaDe({ id: p.pagina }) === ruta` (`"/auditoria"`, `"/libros"`, `"/historial"`). Cuando Tarea 3 redirija `/<paginaId>` a `/auditoria/subir`, `/auditoria/libros` y `/auditoria/historial`, `pathname` nunca coincidirá con `rutaDe` y `pasoDeRuta` devolverá siempre `null`.
   - **Corrección exigida:** Añadir `shell/recorrido.ts` (y `PanelRecorrido.tsx`) a la Tarea 3 para que `pasoDeRuta` y los `NavLink` del recorrido usen la ruta del espacio cuando la pantalla pertenezca a uno.

3. **[MAYOR] F1 / Coherencia entre tareas · [`PLAN_REDISENO_F6.md:126-203`](../../../docs/planes/PLAN_REDISENO_F6.md#L126-L203), [`marco/ubicar.ts:35-55`](../../../frontend-desktop/src/marco/ubicar.ts#L35-L55) y [`marco/Marco.tsx:279-280,328-339`](../../../frontend-desktop/src/marco/Marco.tsx#L279-L280) · Ninguna tarea actualiza `ubicar.ts` (que alimenta `document.title`) ni retira las entradas restantes de `ENTRADAS_DE_EMPRESA`.**
   - `Marco.tsx:279-280` usa `ubicar(ubicacion.pathname, ...)` para `useTituloDelDocumento(titulo)`. Sin actualizar `ubicar.ts`, las rutas `/inicio/:vista`, `/:espacio/:herramienta` y `/cuenta/:seccion` devuelven `titulo: null`.
   - En Tarea 3 `ENTRADAS_DE_EMPRESA` conserva `personas` (`administracion`) y `ayuda` (`acerca`), pero en Tarea 5 ambas pasan a `#/cuenta/:seccion` y en Tarea 4 `BarraLateral.tsx` reemplaza `ZonaEmpresa` por «Costos y producción». Falta declarar en Tarea 5 las redirecciones `#/empresa/personas` → `#/cuenta/cuentas` (o `preferencias`), `#/empresa/ayuda` → `#/cuenta/ayuda`, `#/administracion` y `#/acerca`, así como incluir `Marco.tsx` al cambiar las props de `BarraSuperior.tsx`.
   - **Corrección exigida:** Incluir `marco/ubicar.ts` en las Tareas 3, 5 y 6, y en la Tarea 5 incluir `marco/Marco.tsx` y las redirecciones de `personas`/`administracion` y `ayuda`/`acerca` hacia `#/cuenta/:seccion`.

4. **[MAYOR] F1 / Coherencia en Tarea 6 · [`PLAN_REDISENO_F6.md:218-246`](../../../docs/planes/PLAN_REDISENO_F6.md#L218-L246) y [`marco/usePendientes.ts:36-47`](../../../frontend-desktop/src/marco/usePendientes.ts#L36-L47) · `useCargaDePendientes` solo refresca al entrar en `RUTA_DE_PENDIENTES` (`"/pendientes"`).**
   - Si en la Tarea 6 la ruta índice va a `/inicio/general` y `/pendientes` redirige a `/inicio/pendientes`, `usePendientes.ts` (que no figura entre los archivos de la Tarea 6) debe actualizarse para refrescar al volver a `/inicio/general` o `/inicio/pendientes` (foco 4 de F3: que lo resuelto en una obra no quede viejo al volver a Inicio).
   - **Corrección exigida:** Añadir `marco/usePendientes.ts` (y `marco/EspacioDeObra.tsx:81`, que enlaza a `RUTA_DE_PENDIENTES`) a los archivos modificados de la Tarea 6.

5. **[MENOR] Especificación de segmentos en Tarea 1 y Tarea 3 · [`PLAN_REDISENO_F6.md:71-92,146-148`](../../../docs/planes/PLAN_REDISENO_F6.md#L71-L92).**
   - En Tarea 1 conviene dejar explícitos los `id` de ruta de las 17 herramientas (especialmente donde `id !== pagina`: `resumen`/`produccion`, `costo-tonelada`/`costo_tonelada`, `receta`/`receta_planta`, `mezcla`/`producir_mezcla`, `subir`/`auditoria`, `listas`/`precios_empresa`).
   - En Tarea 3 (`PLAN_REDISENO_F6.md:142,146-148`) y Tarea 4 (`BarraLateral`), alinear si `#/empresa/precios` y `#/empresa/produccion` (y los enlaces de la barra lateral) abren la primera pestaña del espacio (`/precios/listas`, `/produccion/resumen`, como en la especificación §1) o la que abrían en F4 (`/precios/catalogo`, `/produccion/existencias`).

6. **[MENOR] Nota de `api/rutas/sesion.py` en Tarea 5 · [`PLAN_REDISENO_F6.md:212-214`](../../../docs/planes/PLAN_REDISENO_F6.md#L212-L214) y [`api/caso_web.py:44-46`](../../../api/caso_web.py#L44-L46).**
   - Corregir la nota de la Tarea 5: `DELETE /v1/sesion` (`api/rutas/sesion.py:420`) sí descarta los borradores vivos de la ficha mediante `caso_web.olvidar` → `hoja_borradores.olvidar`. Además, recordar que si el usuario navega a `#/cuenta/preferencias` antes de pulsar «Salir», `useBorrador` se desmonta al salir de `#/obra/...` (con sesión aún activa); el 401 ocurre cuando se cierra sesión desde el atajo de la barra superior estando aún dentro de una sección con Hoja, por lo que la bandera en `useSesion.salir` antes de `DELETE /v1/sesion` sigue siendo la solución correcta.

---

**APROBADO SI:**
1. La Tarea 3 incluye `marco/oferta.ts`, `paginas/pendientes/logica.ts`, `shell/recorrido.ts` y `shell/PanelRecorrido.tsx` para que el buscador, los botones de pendientes y los recorridos guiados usen las rutas de `ESPACIOS`.
2. Las Tareas 3, 5 y 6 incluyen `marco/ubicar.ts` para mantener `useTituloDelDocumento`, y la Tarea 5 incluye `marco/Marco.tsx` y las redirecciones de `#/empresa/personas`, `#/empresa/ayuda`, `#/administracion` y `#/acerca` a `#/cuenta/:seccion`.
3. La Tarea 6 incluye `marco/usePendientes.ts` para que la recarga de pendientes funcione en `/inicio/general` y `/inicio/pendientes`.
