# Rediseño F6: espacios enrutados — plan unificado de construcción

> **Para quien ejecuta:** úsese superpowers:subagent-driven-development. Las casillas (`- [ ]`) son para el seguimiento.

**Objetivo:** que cada área de Sílice (Vista general, la obra, Producción, Auditoría, Precios y la Cuenta) sea una
ruta con su cabecera y su barra, que cada pantalla tenga **una sola ruta canónica**, y que la app abra en una Vista
general con los indicadores de la cartera separados por moneda.

**Arquitectura:** un registro único (`marco/espacios.ts`) dice dónde vive cada pantalla de `shell/rutas.ts`, y
`rutaCanonica` es la única fuente de rutas para el enrutador, el buscador, el recorrido guiado y los enlaces. Una sola
pieza, `BarraDeEspacio`, pinta todas las barras. Las pantallas no se reescriben (patrón estrangulador). El servidor gana
una sola ruta de lectura (`GET /v1/obras/resumen/todas`), sin tocar `core/`.

**Tecnología:** React 19 + TypeScript, `react-router` (HashRouter), `@carbon/react` g10, SCSS; FastAPI; Vitest + Testing
Library, pytest; Playwright para la pasada en navegador.

**Documentos que viajan con el plan:**
- [Especificación de Antigravity](../especificaciones/2026-11-04-rediseno-f6-espacios-design.md) y
  [su maqueta](../especificaciones/2026-11-04-rediseno-f6-maqueta.html), aprobadas por Eugenio.
- [Contrato de rutas](../especificaciones/2026-11-04-f6a-contrato-de-rutas.md) (Claude): **manda en rutas y
  permisos**.
- [Diseño visual](../especificaciones/2026-11-04-f6a-diseno-visual.md) (Antigravity): **manda en el aspecto**.

**Arbitraje:** Antigravity lo aprobó el 2026-11-04 con 3 observaciones menores, ya incorporadas en T5, T6 y T7.

**Origen:** une el plan de esta rama con el plan T0–T9 que otra sesión de Claude armó con Antigravity
(`~/.claude/plans/soy-antigravity-auditor-y-effervescent-spark.md`). Eugenio decidió el 2026-11-04 que orquesta esta
sesión.

**Rama:** `feature/f6-espacios`, desde `main` (`febf6673` o posterior). No se apila sobre ramas sin fusionar. Se trabaja
en el worktree `.worktrees/s2m3`, que ya existe.

## Reparto (acordado por Claude y Antigravity; Eugenio decide)

| Quién | Qué |
|---|---|
| **Claude** (orquestador) | Diseño técnico (contrato e interfaces); encarga cada tarea a un subagente constructor (`silice-frontend`, `silice-backend` en T7); corre la compuerta local; verifica cada hallazgo de Antigravity contra el código; integra, abre el PR y mantiene `docs/ESTADO.md` |
| **Antigravity** (árbitro y diseño visual) | Diseño visual de cada entrega; arbitra cada tarea en solo lectura (`arbitrar_rama`, skill `arbitro-independiente`) y deja sus hallazgos en `docs/bitacora/auditoria-agy-AAAA-MM-DD.md`; segunda pasada visual al cierre |
| **Eugenio** | Aprueba T0, decide las preguntas abiertas y fusiona. Si Claude y Antigravity discrepan, decide él |

Nadie construye lo que arbitra. Una tarea se cierra cuando no queda ningún hallazgo «confirmado» abierto (como máximo 3
rondas; después, a Eugenio).

## Decisiones de Eugenio (2026-11-04)

1. Vista general con los totales de la cartera **separados por moneda** (Bs y USD), servidos por el servidor.
2. Las pantallas atadas a una obra pasan a **subvistas de su sección** (contrato §2.1). Precios y catálogo queda con
   Precios de la empresa, Catálogo, Índices y Simulador.
3. **Español llano** en todo texto visible: «Vista general», «Secciones de la obra»; ni «Dashboard» ni «Top Bar».
4. El tamaño de letra pasa **solo a la Cuenta** (`/cuenta/preferencias`).
5. Se **enmienda** DESIGN.md y la especificación del 2026-10-26: la app abre en la Vista general, que pone primero lo que
   bloquea.
6. La rama sale de `main`.

## Restricciones globales

- Carbon g10, esquinas rectas, densidad `sm`, **sin Tailwind**; morado solo para atípicos de ML; verde y rojo IBCS solo
  en las variaciones (DESIGN.md).
- Un solo `h1` por pantalla. Las cabeceras de espacio y las barras **no** llevan `h1` (diseño visual §2.4).
- Sin desplazamiento horizontal a 1056, 1366 y 1920 px con letra Normal, Grande y Muy grande.
- `src/paginas/sinJergaInterna.test.ts` en verde: dentro de `src/marco/` no puede aparecer «módulo», «área», «página»
  ni «carpeta de trabajo».
- La interfaz **no calcula**: cifras del servidor; contar elementos sí se permite. **Nunca se suman Bs con USD.**
- Coma decimal y punto de miles; `core/` intacto; solo datos ficticios.
- TDD con rojo visto y commit aparte para la prueba; asunto del commit en español y sin tildes.
- **No se borran pruebas de comportamiento sin poner su reemplazo** (en especial, las 62 del árbol de
  `BarraLateral.test.tsx`).

## Foco de revisión

1. **Enlaces viejos y favoritos** (contrato §2.4): redirigen conservando la consulta; nunca 404 ni página en blanco
   (T4, T5, T6).
2. **Sin permiso o con el módulo apagado:** la pestaña no aparece y la dirección escrita a mano muestra el aviso de
   siempre (T2, T4).
3. **Cambiar de obra con cambios sin guardar:** la barra lateral plana pregunta igual que hoy (`quedaEnLaHoja`) y no
   remonta `ProveedorDeLaHoja` al pasar entre secciones con Hoja (T5).
4. **Salir con un borrador de la Hoja abierto:** sin el 401 de `DELETE /v1/hoja/borradores/{id}` visto en vivo el
   2026-11-04 (T6).
5. **Botones fuera del marco** (pendientes, Resumen, recorridos guiados, los 11 enlaces escritos a mano): llevan a la
   ruta canónica de su pantalla (T1).
6. **Quien revisa** (solo la carpeta de la empresa): ni la Vista general ni la barra lateral le ofrecen obras que no
   puede abrir (T7, T8).

---

## T0: Expediente (sin código) — compuerta: aprobación de Eugenio

**Archivos:** `docs/especificaciones/2026-11-04-f6-enmienda.md` (nuevo), `frontend-desktop/DESIGN.md`, el contrato de
rutas, el diseño visual y `docs/ESTADO.md`.

- [ ] Claude redacta la enmienda fechada:
  - se modifica la tesis de DESIGN.md: «se rechaza el tablero de tarjetas con KPI» y «la navegación va por obras y
    pendientes»;
  - se modifica la especificación `2026-10-26-rediseno-marco-obras-design.md` (§2.2 Pendientes de entrada, §4
    antiobjetivo del menú de herramientas, §5 reparto y §7 fases);
  - se renumeran las fases: **F6 Espacios, F7 Ayuda, F8 Cierre** (la de Ayuda se llamaba F6).
- [x] Antigravity actualiza el diseño visual con:
  - la barra de **subvistas** dentro de una sección, distinta de la barra de la obra y de las pestañas Carbon;
  - la Vista general con lo que bloquea arriba y la cartera por moneda;
  - el tamaño de letra solo en la Cuenta.
- [x] Antigravity arbitra el expediente.
- [x] Eugenio aprueba.

## T1: Una ruta canónica por pantalla (sin cambio visible)

**Archivos:** `marco/espacios.ts` (nuevo, la tabla del contrato), `shell/recorrido.ts`, `shell/PanelRecorrido.tsx`,
`marco/busqueda.ts`, `paginas/pendientes/logica.ts` y los 11 enlaces escritos a mano:
- `inicio/PanelArenera.tsx:32,57`;
- `produccion/index.tsx:30,34`;
- `comun/EnlacesDeCostos.tsx:9,13`;
- `existencias/index.tsx:73,77`;
- `historial/index.tsx:60`;
- `auditoria/index.tsx:38`;
- `vial/Tramos.tsx:151`;
- `produccion/PublicarCosto.tsx:23`.

**Interfaces:** produce `rutaCanonica(paginaId: string, obra?: { carpeta: string | null; obraId: number }): string | null`.
En T1 devuelve la ruta de **hoy**: las de obra con `rutaDeObra` y las de empresa con `/empresa/<entrada>` o
`/<id>`. T4 y T5 la cambian a la del contrato sin tocar a quien la llama.

- [x] Rojo: `PanelRecorrido en /empresa/auditoria marca «Paso 1 de 3»` (hoy falla; riesgo R5 de la revisión) y
  `ningún enlace interno escribe una ruta a mano` (un `grep` en la prueba: cero `to="/` y cero `navegar("/` fuera de
  `marco/`).
- [x] Verde: implementar. Correr `npx vitest run src/shell src/marco src/paginas`. Esperado: PASA.
- [x] Antigravity arbitra.

## T2: Tabla de espacios y `primeraUsable`

**Archivos:** `marco/espacios.ts`, `marco/oferta.ts` y sus pruebas.

**Interfaces:**
- `ESPACIOS` y `SUBVISTAS`, que dan, para cada sección de obra, `{ id; titulo; pagina }[]`.
- `SECCIONES_DE_CUENTA`.
- `primeraUsable(nivel, acciones, modoEntrega, apagados)`, que devuelve `string | null`.
- `ofertaDe` deja de producir `sueltas` (el contrato no deja ninguna).

- [x] Rojo: la tabla del contrato §2 escrita a mano (31 ids, con `accion` y `modulo`) contra `PAGINAS`, con
  **conjuntos exactos**. Además, `primeraUsable` por rol: quien arma entra al Catálogo y no a Precios de la empresa, y
  con modo entrega no aparece el Simulador. Y la guardia de jerga sobre los títulos.
- [x] Verde. Antigravity arbitra.

## T3: `BarraDeEspacio`

**Archivos:** `marco/BarraDeEspacio.tsx`, su SCSS y su prueba.

**Interfaces:**
- `BarraDeEspacio({ etiqueta, pestanas, activa, nivel })`, con `nivel: "espacio" | "subvista"`.
- `pestanasUsables(...)`, que devuelve `{ id; titulo; ruta }[]`.

Medidas y estados: diseño visual §1.

- [x] Rojo: `nav` con `aria-label`, `aria-current="page"`, que no use `role="tablist"`, sin ancho fijo
  (`estilosMarco.test`), lo no usable no aparece y Tab recorre en orden.
- [x] Verde. Antigravity arbitra el contraste WCAG 2.1 AA y que se distinga de las pestañas Carbon.

## T4: Espacios Producción, Auditoría y Precios

**Archivos:** `marco/EspacioDeHerramientas.tsx` (sigue el molde de `EspacioDeObra.tsx:140-188`), `marco/Marco.tsx`,
`marco/ubicar.ts`, `marco/BarraLateral.tsx` (zona «Costos y producción»), `marco/secciones.ts` (`ENTRADAS_DE_EMPRESA`
pierde `precios`, `auditoria` y `produccion`) y `rutaCanonica` (las rutas del contrato §2.2).

- [x] Rojo:
  - la tabla de redirecciones del contrato §2.4 (empresa), reescrita en `Marco.test.tsx`;
  - un solo `h1`;
  - «Sin permiso» y «Apagada» escritas a mano;
  - se entra a la primera usable;
  - el foco se queda en el enlace al cambiar de herramienta;
  - `document.title`;
  - `/aprobar?envio=12` sigue andando.
- [ ] Verde. Antigravity arbitra: ninguna URL vieja da 404 y `scripts/recorrido_ux_playwright.py:763,1749` sigue al día.

## T5: Obra con su barra, subvistas y barra lateral plana — cierre del bloque A

**Archivos:** `marco/CabeceraDeObra.tsx`, `marco/EspacioDeObra.tsx`, `marco/Marco.tsx` (patrón con `:subvista`),
`marco/BarraLateral.tsx` y su SCSS, `marco/ZonaEmpresa.tsx` (se retira) y `rutaCanonica` (contrato §2.1).

- [x] Rojo:
  - la barra de la obra va bajo su cabecera;
  - las subvistas abren dentro de su sección (por ejemplo, `/obra/demo.db/1/control/reajuste` monta Reajuste con la
    barra de la obra en «Control de obra»);
  - una sección sin pantalla principal usable abre su subvista usable;
  - las 62 pruebas del árbol de `BarraLateral.test.tsx` se **reemplazan** una a una por las de lista plana: píldoras,
    homónimas, «Nueva obra», sin permiso, carga y error;
  - pasar de Presupuesto a Versiones no remonta `ProveedorDeLaHoja`, y pasar de Partidas a Componer
    (`/presupuesto/componer`) tampoco pregunta por cambios sin guardar: `quedaEnLaHoja` compara el segmento `:seccion` y no
    la ruta entera (`secciones.ts:61`; nota H-F6-1 de Antigravity);
  - al cambiar de obra se abre su **Resumen**, como hoy (decisión de Eugenio, 2026-11-04).
- [x] Verde.
- [ ] Antigravity arbitra. Se mide el alto que le queda a la Hoja (Univer) a 1366×768 con letra Muy grande.
- [ ] Revisores internos `silice-rev-diseno` y `silice-rev-pruebas`.
- [x] Suite completa.

## T6: Cuenta `/cuenta/:seccion`

**Archivos:**
- `marco/EspacioDeCuenta.tsx`;
- `paginas/administracion/index.tsx` y `logica.ts` (secciones por ruta, reutilizando `PESTANAS`);
- `marco/BarraSuperior.tsx`: sin migas ni `TamanoLetra`; «Sílice» lleva a la Vista general; se ve la carpeta activa; el
  botón de la persona es un enlace a `/cuenta/preferencias`;
- `shell/MenuCuenta.tsx` (solo antes de entrar);
- `marco/ubicar.ts`, `sesion/useSesion.ts` y `paginas/hoja/useBorrador.ts`.

- [x] Rojo:
  - permisos por sección (contrato §3), en particular que Carpetas exige `administrar_cuentas` y `cambiar_caso`;
  - redirecciones de `/administracion`, `/empresa/personas`, `/acerca` y `/empresa/ayuda`;
  - el tamaño de letra está en `preferencias` para toda cuenta y ya no en la barra de arriba;
  - tras cambiar de carpeta se vuelve a `/cuenta/carpetas`;
  - salir con un borrador abierto no pide `DELETE` del borrador después de `DELETE /v1/sesion` (el servidor ya los
    descarta: `api/caso_web.py:43-46`).
- [x] Verde. Antigravity arbitra: un administrador no pierde nada y quien no administra no ve nada que no deba.

## T7: Servidor, cartera por moneda (puede ir en paralelo con T3 a T5)

**Archivos:** `api/rutas/obras.py` (siguiendo el molde de `GET /v1/obras/pendientes/todas`, `obras.py:371`),
`aplicacion/mesa.py` y pruebas en `tests/unit/test_api_obras_resumen_todas.py`.

**Interfaces:** `GET /v1/obras/resumen/todas` con `LEER_PROYECTO`. Devuelve:
- `{ hoy: str; por_moneda: [{ moneda: "Bs" | "USD"; obras: int; total: str; en_ejecucion: int }]; obras:
  [{ carpeta: str | null; obra_id: int; nombre: str; moneda: str; etapa: str; total: str | null; avance_real: str | null;
  avance_plan: str | null; carpeta_titulo: str }]; carpetas_omitidas: int }`, como `GET /v1/obras/pendientes/todas`
  (`obras.py:356` y `:271`; nota H-F6-3 de Antigravity);
- montos como texto exacto (`format(x, "f")`).

Quien no puede cambiar de carpeta solo ve la abierta (`_carpetas_visibles`).

- [x] Rojo (pytest, casos construidos):
  - dos carpetas, una en Bs y otra en USD: `por_moneda` trae dos filas y nunca una suma mezclada;
  - una carpeta ilegible va a `carpetas_omitidas`;
  - sin permiso, 403;
  - quien revisa solo ve la carpeta de la empresa.
- [ ] Verde. `scripts/guardia_nucleo.py` limpio y `docs/api.json` regenerado.
- [x] Antigravity arbitra.

## T8: Vista general `/inicio/:vista`

**Archivos:** `paginas/inicio/index.tsx` (`Panorama`), `marco/EspacioDeInicio.tsx`, `marco/Marco.tsx` (índice →
`/inicio/general`; `/pendientes` → `/inicio/pendientes`), `marco/usePendientes.ts`, `marco/EspacioDeObra.tsx:81`,
`marco/ubicar.ts`, `shell/rutas.ts` y `shell/rutas.test.ts:54-55` («inicio» deja de no existir).

Contenido: **primero lo que bloquea** (de la Bandeja), después la cartera por moneda (T7) con `IndicadorFiori` y
`FranjaIndicadores`, el avance ejecutado contra el plan por obra (barras IBCS), las últimas auditorías (`UltimasAuditorias`)
y la arenera (`PanelArenera`, solo con `operar_arenera` y su módulo encendido).

- [x] Rojo:
  - cada cifra sale del `fetch` simulado de T7 sin recalcular (`"334570.5"` se ve como `334.570,50`);
  - no aparece ninguna suma de Bs con USD;
  - sin avance, «Sin avance»;
  - quien revisa sin obras ve el estado vacío;
  - volver de una obra recarga los pendientes;
  - un bloque que falla no tumba los demás.
- [ ] Verde. Antigravity arbitra: nada de lo que DESIGN prohíbe, ninguna cifra inventada y español llano.

## T9: Cierre — cierre del bloque B

- [ ] DESIGN.md (Marco, Espacios y Vista general), CHANGELOG, `docs/ESTADO.md`, `recorrido_ux_playwright.py` y
  `recorrido_funcional.toml` con las rutas nuevas, el manual de usuario y la bitácora del cierre.
- [ ] Suite completa:
  - `uv run --active pytest -W error -q` y `uv run ruff check .`;
  - `uv run python scripts/meta_datos.py` y `scripts/guardia_nucleo.py`;
  - `npm run lint`, `npx vitest run --maxWorkers=3` y `knip`;
  - `node scripts/verificar_dist.mjs`;
  - las líneas de producto contra la base.
- [ ] Pasada en Chromium visible (Claude) y segunda pasada visual (Antigravity) a 1056, 1366 y 1920 px con las 3 letras,
  como ana, rita y admin: un `h1`, sin desplazamiento horizontal y sin errores de consola de la app.
- [ ] PR a `main`. Eugenio prueba y fusiona.

**Dependencias:** T0 → T1 → T2 → T3 → (T4 ∥ T7) → T5 → T6 → T8 (necesita T7) → T9.

## Desvíos aprobados

Lo que la construcción cambió respecto del plan, con su razón. T9 no los reabre.

- **(a) `FranjaDeCifras` en lugar de `IndicadorFiori` y `FranjaIndicadores`.** La cartera por moneda (T8) trae total, obras y en ejecución, sin meta ni variación; `IndicadorFiori` las exige. `FranjaDeCifras` (`indicadores/FranjaDeCifras.tsx`) reusa las clases de `FranjaIndicadores`. Lo acordó el arbitraje de T8 (`docs/bitacora/arbitrajes/f6-T8-flash.md`).
- **(b) «inicio» es la pantalla 32 del registro.** El contrato cuenta 31 pantallas en §2 sin «inicio», que es la Vista general (§4). La enmienda del 2026-11-05 está en el contrato de rutas.
- **(c) Una dirección desconocida lleva a la Vista general**, no a Pendientes: el comodín de `Marco.tsx` (línea 423) va a `/inicio/general`.
- **(d) «Presupuesto» en el conmutador de la obra.** Dice «Presupuesto | Componer», no «Partidas» (decisión de Eugenio, 2026-11-04). Se aplicó en T5 y se ajustó en los menores de T5 y T6.

## Respuestas de Eugenio (2026-11-04)

T0 **aprobado**. «Riesgo de la obra» queda como sección propia. Quien revisa sigue viendo solo la carpeta abierta (sin
cambio de permisos). **Enmienda 2026-11-05 (Eugenio):** quien revisa ve y abre las obras de todas las carpetas; la
acción nueva `abrir_carpeta` (abrir y listar) se separa de `cambiar_caso` (crear y subir carpetas), que sigue sin revisa. Al cambiar de obra se abre su Resumen, como hoy: el diseño visual §3.1 («conserva la sección»)
queda corregido por esta respuesta.
