# Fronts alternativos para Sílice: reemplazar o complementar Streamlit sobre FastAPI (estado a octubre de 2026)

Contexto del encargo: Sílice tiene un backend Python 3.12 con FastAPI (REST y clave de API) y una UI en Streamlit 1.62. Se instala en Windows sin internet (Inno Setup, Python empaquetado con uv) y puede correr en LAN. La UI necesita tablas editables tipo hoja de cálculo, tableros de KPI, gráficos, subida y descarga de xlsx y pdf, pantallas por rol y formato es-VE (coma decimal).

Nota de método: hice 17 llamadas de búsqueda y lectura. Varias páginas oficiales no contestaron lo que se les preguntó (la de despliegue de NiceGUI, la de dash-ag-grid y la de autoalojamiento de Reflex en lo tocante a Node). Lo que no pude verificar en una fuente lo marco como **[sin verificar, conocimiento previo]** o lo dejo en Gaps.

---

## P1. Frameworks de UI nativos de Python en 2026 (Reflex, NiceGUI, Panel, Dash, Flet, Shiny, Solara, Mesop, Gradio)

### Takeaway
NiceGUI y Dash (con dash-ag-grid) son las dos opciones nativas de Python que mejor encajan con el requisito de funcionar sin conexión y convivir con FastAPI. NiceGUI corre sobre FastAPI y tiene licencia MIT. Dash sirve sus recursos en local por defecto, aunque los CSS externos hay que copiarlos a mano. Reflex necesita Node en la compilación, pero se puede exportar a archivos estáticos. Panel tiene un problema documentado: su Tabulator sin conexión carga recursos de una CDN.

### Cited Findings
**NiceGUI**
- Licencia MIT, unas 16,3 mil estrellas y 960 forks en GitHub. — [GitHub zauberzeug/nicegui](https://github.com/zauberzeug/nicegui)
- El README dice: "We have built on top of FastAPI, which itself is based on the ASGI framework Starlette and the ASGI webserver Uvicorn". El frontend es Vue y Quasar, y la comunicación va por socket.io. — [GitHub zauberzeug/nicegui](https://github.com/zauberzeug/nicegui)
- La 3.0.0 salió el 3 oct 2025 con cambios incompatibles. Trajo el modo script, un parámetro de página raíz en `ui.run` para SPA y un sistema de eventos. — [Zenodo NiceGUI 3.0](https://zenodo.org/records/17259155); [Talk Python #525 "NiceGUI goes 3.0"](https://talkpython.fm/525)
- La v3.8.0 (24 feb 2026) corrige un fallo cuando se crean elementos antes de `ui.run_with()`, la API para montar NiceGUI sobre una app FastAPI existente. También expone la constante `ui.aggrid.VERSION`, así que AG Grid viene integrado. — [Zenodo NiceGUI v3.8.0](https://zenodo.org/records/18760618)
- El ritmo de versiones es alto: de la 3.0 (oct 2025) a la 3.8 (feb 2026), unas 8 menores en 5 meses. — [Zenodo 3.0](https://zenodo.org/records/17259155), [Zenodo 3.8](https://zenodo.org/records/18760618)
- Hay modo nativo (`native=True`), que en Windows exige .NET Framework. `nicegui-pack` empaqueta con PyInstaller ("distribute your app as a single file"). Hay que poner `reload=False` y, en modo nativo, llamar a `freeze_support()`. — [NiceGUI, configuración y despliegue](https://nicegui.io/documentation/section_configuration_deployment)
- La documentación solo dice que las bibliotecas (Vue, Quasar...) vienen de una CDN en el modo "On Air", el túnel remoto opcional. — [NiceGUI, configuración y despliegue](https://nicegui.io/documentation/section_configuration_deployment)
- Desde la 0.9.8, "libraries are now automatically served on demand", es decir, salen del paquete y no de una CDN. Las notas son antiguas. — [PyPI nicegui 0.9.8](https://pypi.org/project/nicegui/0.9.8/)

**Reflex**
- La v0.9.9a1 (preliminar) pasa a React Router 8.3.0 y exige Node ≥ 22.22.0. `pip install reflex` deja de instalar pydantic (hay extras `reflex[pydantic]` y `reflex[db]`). — [newreleases: reflex v0.9.9a1](https://newreleases.io/project/github/reflex-dev/reflex/release/v0.9.9a1); [v0.9.9](https://newreleases.io/project/github/reflex-dev/reflex/release/v0.9.9)
- En producción, `reflex run --env prod` "compiles the app, builds an optimized static frontend, and serves it together with the backend" en el puerto 3000. `reflex export` genera `frontend.zip` (HTML, JS y CSS minificados, más .gz y opcionalmente brotli o zstd) y `backend.zip`. Con `--no-zip` el frontend queda en `.web/build/client/`. — [Reflex, autoalojamiento](https://reflex.dev/docs/hosting/self-hosting/)
- El backend de Reflex expone sus propias rutas (`/_event`, `/ping`, `/_upload`, `/_health`) y necesita WebSocket (cabecera `Upgrade` en el proxy). — [Reflex, autoalojamiento](https://reflex.dev/docs/hosting/self-hosting/)
- "Instances of Reflex 0.9 and 0.10 cannot share a state store". Hay saltos de versión que rompen el almacén de estado. — [Reflex, autoalojamiento](https://reflex.dev/docs/hosting/self-hosting/)

**Panel (HoloViz)**
- Los mantenedores dicen en el foro que "We do not currently bundle Tabulator". Las rutas de Tabulator y de moment/luxon están fijadas a una CDN en el código, y `pn.config.inline = True` "appeared to make no difference". Las salidas propuestas son un servidor CDN local propio o parchear Panel. — [Foro HoloViz: Tabulator sin conexión](https://discourse.holoviz.org/t/using-panel-tabulator-offline/5175); [Desplegar Panel sin conexión](https://discourse.holoviz.org/t/deploy-panel-offline/2394); [Tabulator en HTML sin conexión](https://discourse.holoviz.org/t/panel-tabulator-in-offline-html-page/4698)
- Hay una incidencia #2284, "Tabulator should not be loaded by default". No pude confirmar si está resuelta. Los hilos son antiguos (2021-2023). — [Foro HoloViz](https://discourse.holoviz.org/t/serving-panel-with-plotly-extension-offline/124)

**Dash**
- dash-ag-grid es "a high-performance and highly customizable component that wraps AG Grid". Tiene edición de celdas, deshacer y rehacer, formateadores con d3-format, modelos de fila en cliente, infinito y en servidor, y una guía de rendimiento de desplazamiento. Las funciones Enterprise piden una clave de AG Grid. — [Dash AG Grid](https://dash.plotly.com/dash-ag-grid)
- Según un usuario del foro de Plotly, la carga por CDN viene "disabled by default", así que por defecto los recursos se sirven en local. Varios hilos cuentan pantallas en blanco ("Loading…") sin conexión hasta forzar `serve_locally = True`, y los CSS externos (Bootstrap y similares) hay que copiarlos a `assets/`. Son fuentes comunitarias y antiguas. — [Foro Plotly: Dash sin conexión](https://community.plotly.com/t/using-dash-in-an-offline-environment/29778); [Dash sin conexión con DBC](https://community.plotly.com/t/use-dash-offline-dash-bootstrap-components/61433); [Problema al cargar CSS/JS sin conexión](https://community.plotly.com/t/problem-to-load-css-and-js-offline/57020)

**Streamlit (la base actual, como referencia)**
- La 1.57 (29 abr 2026) cambió el servidor: "Streamlit now uses Starlette/Uvicorn instead of Tornado ... improved ASGI compatibility", con un objeto `st.App` "for advanced configuration". La 1.58 (28 may 2026) dio a `st.App` manejo propio de errores y restauró PKCE de OAuth en el flujo Starlette. La 1.59 (6 jul 2026) añadió `App.run()`, ButtonColumn y MarkdownColumn. La 1.61 (4 ago 2026) carga bajo demanda las filas de dataframes grandes y añade `server.allowedHosts`. La 1.62 (19 ago 2026) trae pesos de fuente en pasos de 50 en el tema. La 1.63 arregla las subidas con middleware ASGI. La 1.64 (15 sep 2026) admite async/await. — [Streamlit release notes 2026](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- La 1.65.0 salió el 2 oct 2026. Añade `theme.dataframeHeaderTextColor` y corrige que `st.data_editor` convertía `.07` en `7`. — [Streamlit release notes](https://docs.streamlit.io/develop/quick-reference/release-notes)
- Un hilo del foro dice que montar Streamlit en una subruta solo está documentado oficialmente para FastAPI. Un usuario que lo montó en `/dashboard` (Litestar) recibió 404 en los recursos, porque Streamlit genera URL relativas a `/`. — [Foro Streamlit: montar la app ASGI](https://discuss.streamlit.io/t/mounting-new-starlette-asgi-app-inside-litestar/120673)

### Inferences
- **NiceGUI** es el candidato nativo más natural. Ya es una app FastAPI, `ui.run_with(app)` se monta sobre la API existente de Sílice, es MIT, trae `ui.aggrid` (AG Grid Community) y ECharts **[sin verificar, conocimiento previo]**, y sirve sus bibliotecas desde el paquete. Le juegan en contra dos cosas: la estética por defecto es Quasar/Material, y conseguir un aspecto ejecutivo exige CSS o Tailwind propio; y las versiones salen muy seguido, con rupturas en la 3.0.
- **Reflex** no exige Node en ejecución si se usa `reflex export` y se sirve `.web/build/client/` como estático. Pero su backend es su propio servidor de estado por WebSocket, no un montaje limpio sobre la FastAPI de Sílice. Además hay que fijar Node ≥ 22 en la máquina de compilación y en la CI, y los saltos 0.x rompen el estado. Es el riesgo más alto entre los nativos.
- **Dash + dash-ag-grid + dash-mantine-components** es maduro y sirve en local. Dash es Flask/WSGI, así que convivir con FastAPI requiere `WSGIMiddleware` o un proceso aparte **[sin verificar en esta ronda]**. Las licencias de Dash, dash-ag-grid y DMC son MIT **[sin verificar, conocimiento previo]**.
- **Panel** queda descartado mientras no haya evidencia de que Tabulator se empaqueta en local. Sin conexión, los recursos de la CDN fallan y la tabla no se dibuja.
- **Streamlit** en 1.57+ ya corre sobre Starlette con `st.App`. Eso abre un patrón de estrangulamiento barato: un solo proceso Uvicorn con FastAPI como app principal, Streamlit montado en una subruta y la UI nueva en otra. Hay que vigilar el problema de las URL relativas a `/` en subrutas.
- Flet (Flutter, Apache-2.0), Shiny for Python (MIT, Posit), Solara (MIT, Widgetti), Mesop (Google, Apache-2.0, experimental) y Gradio (Apache-2.0, orientado a demos de ML) **[sin verificar, conocimiento previo]**: ninguno ofrece una ventaja clara en tablas tipo hoja de cálculo y aspecto ejecutivo frente a NiceGUI o Dash. Gradio y Mesop no son adecuados para un ERP de presupuestos.

### Gaps
- No verifiqué en una fuente primaria la fecha de la última versión de NiceGUI (posterior a la 3.8) ni de Reflex en octubre de 2026. Un listado de terceros fechaba la v0.9.7 en julio de 2026 y parecía desactualizado.
- No hay benchmarks con metodología declarada sobre tablas grandes en NiceGUI, Reflex o Dash. No encontré ninguno fiable.
- No verifiqué el estado de Flet, Shiny, Solara, Mesop y Gradio en 2026 (cadencia, licencia, componentes de rejilla).
- No confirmé si la incidencia #2284 de Panel se cerró ni si las versiones de Panel 1.x empaquetan Tabulator.
- No confirmé en la documentación oficial el valor por defecto de `serve_locally` en Dash 3.x.

---

## P2. SPA de JavaScript sobre FastAPI (React + shadcn/ui + Tremor o Recharts + TanStack Table o AG Grid; Vue + PrimeVue; Svelte) y rejillas tipo hoja de cálculo

### Takeaway
Una SPA compilada con Vite y servida como estático por FastAPI no necesita Node en ejecución, que es el requisito duro. Para la rejilla, AG Grid Community (MIT, uso comercial gratis) es la base segura, pero el rango, el portapapeles, la agrupación, la exportación a Excel y el pivote son de Enterprise (licencia comercial). Handsontable queda descartado para un producto propietario sin pagar licencia. RevoGrid, Univer (núcleo Apache-2.0) y jspreadsheet CE son las alternativas permisivas.

### Cited Findings
**AG Grid**
- "AG Grid Community is available under the MIT licence" y es "Free for everyone, including production use - no licence required". Enterprise "requires a commercial, EULA licence", se vende por desarrollador y por despliegue, es perpetua con un año de soporte y, sin clave, muestra marca de agua y un error en consola. — [AG Grid, licencias](https://www.ag-grid.com/javascript-data-grid/licensing/)
- Son solo de Enterprise: Server-Side Row Model, exportación a Excel, pivote y agregación, **selección de rangos**, gráficos integrados, agrupación de filas, **operaciones de portapapeles**, master/detail, paneles de herramientas y menús contextuales personalizados. — [AG Grid, licencias](https://www.ag-grid.com/javascript-data-grid/licensing/)

**Handsontable**
- Tiene licencia dual. El uso no comercial se activa con una palabra clave que no conecta con ningún servidor. El uso comercial pide una clave de pago y la licencia de evaluación prohíbe pasar a producción si el proyecto tiene actividad comercial. La última versión MIT fue la 6.2.2, del 19 dic 2018. — [Handsontable, licencia de software](https://handsontable.com/docs/software-license/); [clave de licencia](https://handsontable.com/docs/license-key/)
- Según una página escrita por un competidor (RevoGrid), el plan Standard cuesta desde 999 USD al año por desarrollador. Es fuente de un competidor y conviene verificarla. — [RevoGrid: alternativa a Handsontable](https://rv-grid.com/compare/handsontable-alternative)

**Alternativas tipo hoja de cálculo**
- RevoGrid tiene el núcleo MIT y un plan Pro (complementos avanzados) desde 199 USD al año por puesto, según su propio sitio. — [RevoGrid compare](https://rv-grid.com/compare/handsontable-alternative); [The Frontend Company: alternativas a Handsontable](https://www.thefrontendcompany.com/posts/handsontable-alternatives)
- Jspreadsheet: la Community Edition es MIT y los planes de pago empiezan en 499 USD al año, según un blog de terceros. No lo confirmé en el sitio de Jspreadsheet. — [The Frontend Company](https://www.thefrontendcompany.com/posts/handsontable-alternatives)
- Univer tiene el núcleo bajo Apache-2.0. Pivote, impresión, importación y exportación, colaboración y Live Share son Pro, con licencia comercial. Sin licencia, Pro pone marca de agua, imprime como máximo 3 páginas y permite una sola tabla dinámica por documento. Un agregador fecha la 1.0.0 el 24 sep 2026. — [Univer Pro features](https://docs.univer.ai/guides/sheets/pro-features/introduction); [Univer, pasar a Pro](https://docs.univer.ai/guides/sheets/getting-started/pro); [ai-tldr: Univer](https://ai-tldr.dev/tools/univer/)

**Gráficos y componentes**
- Vercel compró Tremor el 22 ene 2025. Tras la compra, "all Tremor components, including Blocks, are now free and open source", con licencia Apache-2.0. Son más de 20 componentes sobre Tailwind CSS, Recharts y Radix UI. — [Walder Wyss: venta de Tremor Labs a Vercel](https://www.walderwyss.com/fr/news/2025-01-22_walder-wyss-advises-on-exit-of-y-combinator-startup-tremor-labs-inc-to-vercel-inc); [tremor.so](https://tremor.so/); [bestofjs: tremor](https://bestofjs.org/projects/tremor)

### Inferences
- **Despliegue sin Node en ejecución:** `vite build` produce `dist/` (HTML, JS y CSS con hash). En FastAPI se sirve con `StaticFiles(directory="dist", html=True)` montado en `/`, después de las rutas `/api`, y con una ruta de reserva a `index.html` para el enrutado del cliente **[patrón estándar, sin fuente en esta ronda]**. Node solo hace falta en la máquina de desarrollo y en la CI. El instalador Inno Setup lleva `dist/` como datos. Es el mismo modelo que `reflex export`.
- **Fuentes e iconos sin conexión:** autoalojar las tipografías (paquetes `@fontsource/*` o archivos woff2 en `public/`) y usar iconos como componentes SVG (lucide-react, que shadcn/ui usa por defecto) en lugar de Google Fonts o CDN de iconos **[sin verificar, conocimiento previo]**. Lo mismo vale para NiceGUI y Dash: cualquier `<link>` a fonts.googleapis.com rompe el uso sin conexión.
- **Pila React recomendada:** shadcn/ui (MIT; el código se copia al repo, así que no hay dependencia de versión) más Tailwind, Tremor o Recharts para KPI y gráficos, TanStack Table (MIT, sin interfaz propia) para listados de solo lectura y AG Grid Community para las partidas y APU editables **[licencias de shadcn y TanStack sin verificar, conocimiento previo]**.
- **El hueco de Enterprise importa para Sílice:** pegar desde Excel (portapapeles), seleccionar rangos y exportar a xlsx desde la rejilla son de Enterprise. Hay dos salidas. Una es exportar xlsx desde el backend: Sílice ya genera xlsx y pdf en Python, así que la rejilla solo edita. La otra es una rejilla permisiva con portapapeles nativo: Glide Data Grid (MIT **[sin verificar]**), RevoGrid MIT o Univer Apache-2.0.
- **Vue + PrimeVue** (MIT **[sin verificar]**) trae una DataTable con edición de celdas y un tema empresarial completo. Es una alternativa razonable si el equipo prefiere Vue. Le da afinidad que NiceGUI ya use Vue y Quasar. **Svelte** tiene un ecosistema de rejillas y componentes más pequeño, y para un equipo de 1 o 2 personas eso aumenta el riesgo.
- **Coma decimal:** en cualquier SPA, `Intl.NumberFormat('es-VE')` sirve para mostrar. AG Grid permite `valueFormatter`, `valueParser` y `localeText` **[sin verificar en esta ronda]**. Hace falta un parser que acepte `1.234,56`. Para Sílice conviene que el backend siga mandando Decimal como cadena y que el front solo formatee.
- **Descartes por licencia:** Handsontable (comercial para producción), AG Grid Enterprise y Univer Pro (comerciales) y cualquier dependencia GPL o AGPL. Luckysheet está archivado y su sucesor es Univer; Fortune-sheet y x-spreadsheet son MIT pero con poca actividad **[sin verificar, conocimiento previo]**.

### Gaps
- No verifiqué los tamaños de paquete (KB gzip) de AG Grid Community, Glide, RevoGrid, Univer, Tremor ni PrimeVue, ni encontré mediciones con metodología declarada.
- No confirmé en fuente primaria las licencias de Glide Data Grid, TanStack Table, shadcn/ui, PrimeVue, Fortune-sheet, x-spreadsheet ni jspreadsheet CE.
- No verifiqué si el relleno de celdas (fill handle) de AG Grid es Community o Enterprise; la página de licencias no lo menciona.
- No verifiqué el estado de mantenimiento de Tremor en 2026 tras la compra.

---

## P3. Estrategias de migración (estrangulamiento, incrustación, sesión y autenticación compartidas, esfuerzo, pruebas)

### Takeaway
Streamlit ya corre sobre Starlette/Uvicorn desde la 1.57 y expone `st.App`, y montar en subruta está documentado para FastAPI. Por eso el estrangulamiento en un solo proceso es viable: FastAPI es la app raíz, sirve `/api`, la UI nueva en `/` o `/app` y Streamlit en `/legado`, y las pantallas se migran una a una.

### Cited Findings
- Streamlit 1.57 sustituyó Tornado por Starlette/Uvicorn ("improved ASGI compatibility") y expone `st.App`. Las versiones siguientes añadieron manejo de errores en `st.App` (1.58), `App.run()` (1.59), `server.allowedHosts` para limitar los handshakes de WebSocket (1.61) y la corrección de subidas con middleware ASGI que ya leyó el cuerpo (1.63). — [Streamlit release notes 2026](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- Montar Streamlit en subruta "only officially documented for FastAPI so far". En otro host ASGI, los recursos devolvieron 404 porque las URL se generan relativas a `/`. — [Foro Streamlit](https://discuss.streamlit.io/t/mounting-new-starlette-asgi-app-inside-litestar/120673)
- Una guía comunitaria recomienda correr Streamlit y FastAPI en un solo proceso Uvicorn mediante `streamlit.starlette.App`. Es de terceros, no documentación oficial. — [tomevault: streamlit-starlette-demo](https://tomevault.io/tome/andfanilo/streamlit-starlette-demo)
- NiceGUI se monta sobre una FastAPI existente con `ui.run_with()` (corrección relacionada en la v3.8.0). — [Zenodo NiceGUI v3.8.0](https://zenodo.org/records/18760618)
- Reflex en modo separado exige `REFLEX_API_URL` en compilación y un proxy que enrute `/_event` y `/_upload` con soporte de WebSocket. — [Reflex, autoalojamiento](https://reflex.dev/docs/hosting/self-hosting/)

### Inferences
- **Topología recomendada (una sola app ASGI, un solo puerto, apta para LAN):** `FastAPI()` raíz → `/api/*` (lo que ya existe) → `/legado` (Streamlit montado vía `st.App`) → `/` (la SPA en `dist/` o las páginas de NiceGUI). El instalador no cambia de forma: un solo `uvicorn` y un solo acceso directo.
- **Autenticación compartida:** hoy la API usa una clave. Para pantallas por rol conviene una sesión de navegador: cookie HttpOnly emitida por FastAPI tras el login, con el rol dentro. La SPA llama a `/api` con la cookie (mismo origen, sin CORS) y Streamlit en `/legado` lee la misma cookie desde la petición. La clave de API queda para integraciones. **[diseño propuesto, sin fuente]**
- **Orden de estrangulamiento:** primero las pantallas de solo lectura de alto valor visual (tablero ejecutivo con KPI y gráficos, que es poco riesgo y mucho efecto), luego descargas e informes, y al final la edición de partidas y APU (la rejilla), que es lo más arriesgado. Streamlit queda para la administración y las pantallas poco usadas.
- **Incrustar con iframe** (Streamlit dentro de la SPA o al revés) es posible al ser mismo origen, pero degrada la navegación y la coherencia visual. Solo sirve como puente temporal.
- **Esfuerzo y riesgo para 1 o 2 personas:** NiceGUI es lo que menos cuesta (todo Python, mismas pruebas con pytest y su `User` fixture **[sin verificar]**) y reutiliza la lógica de `ui/` que ya existe. Una SPA React cuesta más (un segundo lenguaje, toolchain de Node, un segundo conjunto de pruebas con Vitest o Playwright) pero da el aspecto ejecutivo más controlable y desacopla la UI del proceso Python. Reflex une los dos costes: aprender React por debajo y además su propio modelo de estado.
- **Pruebas:** con una SPA, las pruebas de contrato de la API (pytest sobre FastAPI) quedan como compuerta principal, y la UI se cubre con Playwright de punta a punta (Playwright tiene binding Python, así que encaja en la CI existente). La memoria del proyecto dice que no se escriben pruebas nuevas hasta la auditoría final, así que esto entraría en ese plan, no antes.

### Gaps
- No encontré documentación oficial de Streamlit con el ejemplo exacto de montaje en FastAPI (la URL `st.app` devolvió 404). Hay que verificar en la referencia de la API de la 1.62 instalada.
- No encontré estimaciones de esfuerzo publicadas ni casos de migración de Streamlit a otra pila con datos.

---

## P4. Qué opción da mejor un aspecto ejecutivo con bajo riesgo: pros, contras y lista corta

### Takeaway
La lista queda así: (1) SPA React (Vite + shadcn/ui + Tremor + AG Grid Community) servida como estático por FastAPI, con Streamlit montado como legado; (2) NiceGUI montado sobre la FastAPI existente; (3) Dash + dash-ag-grid + dash-mantine-components; (4) Reflex con exportación estática. Panel queda descartado por la CDN de Tabulator, y Handsontable por licencia.

### Cited Findings
- AG Grid Community MIT, con uso comercial en producción gratis; Enterprise comercial. — [AG Grid, licencias](https://www.ag-grid.com/javascript-data-grid/licensing/)
- Tremor: Apache-2.0, gratis tras la compra de Vercel (ene 2025), sobre Tailwind, Recharts y Radix. — [tremor.so](https://tremor.so/); [Walder Wyss](https://www.walderwyss.com/fr/news/2025-01-22_walder-wyss-advises-on-exit-of-y-combinator-startup-tremor-labs-inc-to-vercel-inc)
- NiceGUI: MIT, sobre FastAPI, `ui.run_with`, AG Grid integrado. — [GitHub](https://github.com/zauberzeug/nicegui); [Zenodo v3.8.0](https://zenodo.org/records/18760618)
- Reflex: Node ≥ 22.22 para compilar (v0.9.9a1); `reflex export` genera el frontend estático. — [newreleases](https://newreleases.io/project/github/reflex-dev/reflex/release/v0.9.9a1); [Reflex, autoalojamiento](https://reflex.dev/docs/hosting/self-hosting/)
- Panel: Tabulator no empaquetado y cargado desde CDN. — [Foro HoloViz](https://discourse.holoviz.org/t/using-panel-tabulator-offline/5175)
- Handsontable: comercial para producción desde la 7.0 (la última MIT es la 6.2.2 de 2018). — [Handsontable, licencia](https://handsontable.com/docs/software-license/)

### Inferences (lista corta razonada)
1. **SPA React + shadcn/ui + Tremor/Recharts + AG Grid Community, servida por FastAPI** (estrangulamiento con Streamlit en `/legado`)
   - A favor: el mejor techo visual "ejecutivo" (tipografía y tokens propios, densidad controlada). Todo MIT o Apache. Sin Node en ejecución. La API ya existe, así que la UI es un cliente puro. Es el ecosistema más grande y con más ayuda de IA y documentación.
   - En contra: un segundo lenguaje y toolchain (Node solo en desarrollo y CI). Más código de UI. La rejilla Community no tiene portapapeles ni rango (Sílice tendría que resolver la importación desde Excel por el backend, que ya existe, o usar Glide o RevoGrid). Hay que mantener dos suites de pruebas.
   - Riesgo: medio. El mayor riesgo es la capacidad de un equipo de 1 o 2 personas, no la técnica.
2. **NiceGUI con `ui.run_with(app)` sobre la FastAPI de Sílice**
   - A favor: todo Python. Mismo proceso y puerto. MIT. Bibliotecas servidas desde el paquete. Trae AG Grid y gráficos. La curva para quien ya hizo Streamlit es la más corta. Modelo de eventos con estado en el servidor, sin el rerun completo de Streamlit.
   - En contra: el aspecto Quasar/Material hay que reestilizarlo para que parezca ejecutivo. Cadencia alta con rupturas en mayores (3.0). Estado por conexión en el servidor, lo cual sirve en LAN pequeña. Hay que verificar que ninguna dependencia opcional tire de una CDN.
   - Riesgo: bajo a medio. **Es la mejor opción si se prioriza el bajo riesgo sobre el techo visual.**
3. **Dash + dash-ag-grid + dash-mantine-components**
   - A favor: maduro. AG Grid y Plotly de primera. Mantine da un aspecto más moderno que Bootstrap.
   - En contra: es WSGI (Flask), así que hay que montarlo con un adaptador o en otro proceso. Callbacks verbosos para flujos con mucho estado. Los CSS externos hay que copiarlos a `assets/` para que funcione sin conexión.
   - Riesgo: medio.
4. **Reflex**
   - A favor: Python que compila a React. Puede verse muy bien.
   - En contra: Node ≥ 22 en compilación. Backend de estado propio en lugar de la FastAPI actual. Versiones 0.x con rupturas de estado entre 0.9 y 0.10.
   - Riesgo: alto para este proyecto.
- **Descartados:** Panel (CDN de Tabulator sin conexión), Gradio y Mesop (orientados a demos), Handsontable (licencia comercial), AG Grid Enterprise y Univer Pro (salvo que se compren).
- **Complemento de bajo coste que no excluye nada:** subir Streamlit a 1.65, que ya trae tema con pesos de fuente, color de cabecera de dataframe y carga bajo demanda de filas, y aplicar un tema ejecutivo con fuentes autoalojadas. Eso puede cubrir la necesidad mientras se decide la migración.

### Gaps
- No hay comparativas 2025-2026 con metodología declarada entre estos frameworks. Las que aparecen son tutoriales o blogs de proveedores, y no las cité.
- No se midió rendimiento con tablas de presupuesto reales de Sílice (miles de partidas) en ninguna de las opciones. Antes de decidir haría falta una prueba de concepto de 1 o 2 días con la rejilla de partidas en NiceGUI y en React + AG Grid.
