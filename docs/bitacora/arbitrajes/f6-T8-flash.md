# F6 · T8 · Flash (2026-11-05): APROBADO, sin hallazgos (Gemini 3.8 Flash High)

> Encargo acotado a 5 puntos de riesgo (cifras, robustez, rutas y permisos, pruebas cambiadas y las 7 decisiones del
> constructor). Diff da02b17b..534040e0. Solo git. Respuesta literal; guardada por Claude.

**VEREDICTO: APROBADO**

**Verificado por mí:**
- `git log --oneline da02b17b..534040e0`
- `git diff da02b17b 534040e0 -- frontend-desktop/src/paginas/inicio frontend-desktop/src/indicadores`
- `git diff da02b17b 534040e0 -- frontend-desktop/src/marco frontend-desktop/src/shell`
- `git diff da02b17b 534040e0 -- '*.test.ts' '*.test.tsx'`
- `git show 534040e0:frontend-desktop/src/paginas/inicio/CarteraYAvance.tsx`
- `git show 534040e0:frontend-desktop/src/paginas/inicio/LoQueBloquea.tsx`
- `git show 534040e0:frontend-desktop/src/paginas/inicio/index.tsx`
- `git show 534040e0:frontend-desktop/src/marco/BarraLateral.tsx`
- `git show 534040e0:frontend-desktop/src/marco/EspacioDeInicio.tsx`
- `git show 534040e0:frontend-desktop/src/marco/usePendientes.ts`

---

### Juicio de los puntos de riesgo

**A. Cifras (`paginas/inicio`, `indicadores`):**
- **Sin recalcular ni inventar:** En [`CarteraYAvance.tsx`](frontend-desktop/src/paginas/inicio/CarteraYAvance.tsx) y [`FranjaDeCifras.tsx`](frontend-desktop/src/indicadores/FranjaDeCifras.tsx) las cifras vienen directo del servidor y solo pasan por formateo de texto (`centesimasEsVe` y `formatoEsVe`). Las barras solo derivan su ancho visual con límites 0–100 % (`Math.min(100, Math.max(0, n))%`).
- **Monedas separadas:** `por_moneda.map` renderiza una tarjeta independiente por moneda; en ningún camino se suman, promedian o combinan montos en Bs y USD.
- **Estados condicionales:** «Sin avance» se emite estrictamente si `real === null || plan === null` ([`CarteraYAvance.tsx:47`](frontend-desktop/src/paginas/inicio/CarteraYAvance.tsx#L47)); «Sin versión» se emite si `obra.total === null` ([`CarteraYAvance.tsx:69`](frontend-desktop/src/paginas/inicio/CarteraYAvance.tsx#L69)).

**B. Robustez:**
- **Aislamiento de fallos:** Cada bloque gestiona su propio estado (`useCarga` y `usePendientes`). Si la cartera, las auditorías o los pendientes devuelven 500 o fallan, muestran su respectivo componente de error (`AvisoError`/`EstadoVacio`) sin propagar excepciones ni romper los demás bloques ni el espacio. Adicionalmente, [`EspacioDeInicio.tsx:32`](frontend-desktop/src/marco/EspacioDeInicio.tsx#L32) envuelve cada vista en su propio `<LimiteDeError>`.
- **Carga de pendientes en arranque y retorno:** En [`usePendientes.ts:39-49`](frontend-desktop/src/marco/usePendientes.ts#L39-L49), `esEntradaDeInicio` reconoce `/`, `/inicio` y `/pendientes` durante la carga inicial evitando pedir dos veces al redirigir; al navegar a una obra `leyendoEnInicio` pasa a `false`, por lo que al regresar a cualquier vista de Inicio se invalida el estado y se recargan los pendientes una sola vez.

**C. Rutas y permisos (`marco`, `shell`):**
- **Sin bucles de redirección:** `/` y `path="*"` redirigen con `replace` a `/inicio/general`; `/pendientes` redirige con `replace` a `/inicio/pendientes` conservando `search`. Vistas inexistentes de inicio (`/inicio/xyz`) caen a `/inicio/general`.
- **Permisos estrictos:** Sin `leer_proyecto`, `useCarga` recibe `null` ([`paginas/inicio/index.tsx:33-34`](frontend-desktop/src/paginas/inicio/index.tsx#L33-L34)), devolviendo `sin_permiso` sin disparar llamadas de red; la cartera, el avance y las auditorías no se piden ni se muestran. Sin `operar_arenera` o con el módulo apagado, la arenera no se pide ni se monta. Quien solo revisa ve el estado vacío sin el botón «Nueva obra».
- **Barra lateral:** Cumple exactamente la especificación visual §3.1 punto 1: la primera fila es `<Link to="/inicio/general">` con clases `.silice-marco-lateral__fila.silice-marco-lateral__pendientes`, texto visible «Vista general», activa en cualquier ruta de Inicio (`esRutaDeInicio`), y con `<Pildora valor={total} />` y `aria-label` condicionales cuando `total > 0`.

**D. Pruebas existentes cambiadas:**
- Ninguna prueba fue debilitada ni se eliminaron casos sin reemplazo.
- Las aserciones actualizadas en [`App.test.tsx`](frontend-desktop/src/App.test.tsx), [`BarraLateral.test.tsx`](frontend-desktop/src/marco/BarraLateral.test.tsx), [`Marco.test.tsx`](frontend-desktop/src/marco/Marco.test.tsx) y [`Bandeja.test.tsx`](frontend-desktop/src/paginas/pendientes/Bandeja.test.tsx) responden a las rutas canónicas del contrato (`/inicio/general` y `/inicio/pendientes`).
- Los dos ciclos TDD son limpios: el commit rojo `878e17a7` falló legítimamente por ausencia de la funcionalidad antes de `ce42995e`, y `8677d365` falló por el enlace de la barra lateral antes de `534040e0`.

**E. Juicio de las 7 decisiones del constructor:**
1. **`centesimasEsVe` en montos:** APROBADA. Asegura los dos decimales exigidos por el plan y el estándar financiero es-VE (`334.570,50`), operando sobre cadenas y `BigInt` sin pérdida por floats.
2. **`FranjaDeCifras.tsx`:** APROBADA. Reutiliza los estilos y clases de Fiori sin forzar `meta` y `variación`, evitando inventar cifras.
3. **`path="*"` a `/inicio/general`:** APROBADA. Coherente con que la Vista general es la pantalla de inicio principal de la aplicación.
4. **`inicio` como pantalla 32 en `shell/rutas.ts`:** APROBADA. Permite la resolución declarativa de títulos, rutas canónicas y carga diferida respetando el aislamiento de las 31 pantallas funcionales del contrato en las pruebas.
5. **Homónimas desde la cartera:** APROBADA. Reutiliza los datos ya entregados por `GET /v1/obras/resumen/todas`, evitando peticiones redundantes.
6. **Pasos de pendientes con `destinoDelPendiente`/`paginaQueAbre`:** APROBADA. Garantiza paridad total con la Bandeja de pendientes y no ofrece pasos que la API rechazaría.
7. **Sin `leer_proyecto` no se piden cartera ni auditorías:** APROBADA. Cumple el principio de no llamar a endpoints que devuelven 403.

---

**HALLAZGOS:** ninguno.
