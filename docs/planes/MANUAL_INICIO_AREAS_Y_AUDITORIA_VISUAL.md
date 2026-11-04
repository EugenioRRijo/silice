# Manual: Inicio «panel del día», navegación por áreas e historial de auditorías, más la auditoría visual

> **Para:** la sesión que integra la migración del front (`inc/ruta-s2-mig`, hoy tesis-76 / tesis-bd).
> **De:** tesis-dd, 2026-10-19. **Eugenio no estará para aprobar**: lo que sigue está decidido con criterio de
> ingeniería senior. Todo es reversible y local; no hay push, PR ni fusión por mi parte. Lo que toque `core/`, datos
> reales o al tutor NO se hace y queda anotado.
> **Fuente de diseño:** `docs/especificaciones/2026-10-18-silice-ui-inicio-panel-del-dia-design.md` (está en la rama
> `inc/ruta-s4-ui-inicio`, worktree `.worktrees/s4u`) y `frontend-desktop/DESIGN.md`.

## 0. Hallazgos que cambian el orden (verificados 2026-10-19)

| # | Hallazgo | Consecuencia |
|---|---|---|
| H-1 | El Inicio en React **ya existe** en `inc/ruta-s2-mig` (`src/paginas/inicio/`: zona del Excel, `PanelArenera`, `UltimasAuditorias`, con pruebas). | No se reconstruye. Solo se completa lo que falta (§2). |
| H-2 | Ese Inicio llama a `/v1/produccion/existencias` y `/v1/auditorias-libro?limite=5`, pero **ninguna de las dos rutas existe en `api/` de `inc/ruta-s2-mig`**. Existen solo en `inc/ruta-s4-existencias-react` (`api/rutas/auditorias_libro.py`, migración `ins_0003_auditoria_libro`) y la de producción en `inc/ruta-s4-arenera`. | Integrar esas ramas ANTES de dar por buena la pantalla; si no, el Inicio muestra error de red en dos bloques. |
| H-3 | El menú actual (`src/shell/MenuLateral.tsx`, `rutas.ts`) tiene **4 secciones** (Trabajo, Revisión, Investigación, Administración). El spec pide **5 áreas** (Inicio, Auditar, Crear, Producción, Más) y un panel con 3 herramientas principales. | Es la brecha principal (§2.1). |
| H-4 | No hay página «Historial de auditorías» ni recorrido «Auditar un libro de la empresa» en React. | §2.2 y §2.3. |

## 1. Orden de integración (el que yo seguiría)

1. `inc/ruta-s4-arenera` (modelo, rutas `/v1/produccion/*`, migración `ins_0002_produccion`). Luego
   `inc/ruta-s4-existencias-react` (trae `ins_0003_auditoria_libro` y la ruta de auditorías). Verificar que la
   cadena de migraciones de `instalacion.db` quede `ins_0001 → ins_0002 → ins_0003` sin ramas.
2. Resolver conflictos de `api/main.py` conservando los dos routers; regenerar `docs/api.json` con
   `uv run --active python scripts/exportar_openapi.py` (nunca a mano).
3. Después las demás ramas pendientes (precios, índices, tablero-control, entregar, adm-empresa) según su plan.
4. Correr `npm test`, `npm run lint`, `npm run build`, `npm run dist` y las pruebas de Python tocadas con `-W error`.

Decisión sobre la arenera: **Eugenio la dejó como «herramienta sencilla para que sea atractiva»**
(Sesión 4 parada a propósito). Integrar lo ya commiteado con pruebas verdes; **no** abrir trabajo nuevo de S4
(4.10 extremo a extremo, versión 1.4.0) sin su pedido. Datos de la arenera: solo ficticios y declarados.

## 2. Qué construir (en este orden)

### 2.1 Navegación por áreas + panel de herramientas (la brecha principal)

- **Dónde:** `src/shell/MenuLateral.tsx` y `src/shell/rutas.ts`. Las **rutas URL no cambian** (RM del plan 2b).
- Agregar a `PaginaDef` un campo `area: "inicio" | "auditar" | "crear" | "produccion" | "mas"`; **no** quitar
  `seccion` hasta que la prueba de `rutas.test.ts` se actualice (ver regla RU-2: actualizar las enumeraciones de
  pruebas existentes es un cambio permitido pero se informa en la bitácora).
- Reparto (del spec §2.2): **Auditar** = `libros` (Auditor de APU), `revisar`, Historial de auditorías;
  **Crear** = `componer` (Creador de APU), `elaborar`, `hoja`, `catalogo`, `tablero`, `entregar`;
  **Producción** = `existencias`; **Más** = `actualizacion`, `historico`, `precios_empresa`, `indices`,
  `reajuste`, `control`, `escenarios`, `similares`, `simulador`, `visor`, `administracion`, `acerca`.
- Cada área con su descripción **siempre visible** bajo el nombre («Empiece aquí», «Revisar presupuestos y
  paquetes», «APU, presupuestos y entregas», «Arenera: existencias y báscula», «Precios, obra, análisis y
  ajustes»).
- **Panel de herramientas principales** arriba del menú, en este orden: Auditor de APU, Creador de APU, Gestor de
  producción, cada una con su línea corta («Suba un Excel y vea lo que no cuadra», «Componga una partida o arme un
  presupuesto», «Cuánto hay y cuánto queda de cada material»). «Más herramientas» plegado.
- Mantener lo que ya dicta `DESIGN.md`: las páginas no migradas van bajo «En la interfaz clásica»; no se pintan las
  que el rol no permite; un área sin páginas visibles no se pinta.
- Ruling senior: **un solo SideNav de Carbon**, no cabecera + panel + barra superior duplicados. El spec nació para
  Streamlit (barra superior); en Carbon el equivalente correcto es el SideNav con áreas. Costo si es erróneo: bajo.

### 2.2 Página «Historial de auditorías» (`src/paginas/historial/`)

- Lista (tabla densa `sm`, 32 px, `src/comun/TablaDensa.tsx`) con fecha, usuario, archivo, total del libro, total
  de Sílice, conteos por severidad. Al elegir una fila: resumen y hallazgos en solo lectura (`InformeAuditoria`
  de `src/comun`). Volver a trabajar el libro exige subirlo otra vez: **nunca se guarda el Excel ni el PDF**.
- Backend: usar `api/rutas/auditorias_libro.py` de la rama S4; si falta el detalle por id, agregarlo ahí con TDD.
- Registrar en `rutas.ts` con `cargar`, `accion: "leer_proyecto"`.

### 2.3 Recorrido «Auditar un libro de la empresa»

- Tres pasos, uno por pantalla (regla de `Recorrido`: no repetir pantalla): Inicio (subir el libro) → Libro de la
  empresa (leer resumen, revisar hallazgos por severidad, descargar el devuelto) → Historial (comprobar que quedó
  guardada). Cada paso con «qué hacer» y «sabrá que terminó cuando». Seguir la forma de los recorridos existentes
  (`ui/recorridos.py` en Python; en React, donde ya viva el motor de recorridos; si no existe, **diferirlo y anotarlo**
  en vez de inventar un motor).

### 2.4 Lo que NO se hace

- No construir nada en Streamlit (el spec quedó EN ESPERA por eso).
- No tocar `core/`; `git diff origin/main -- core/` vacío; guardia del núcleo en OK.
- No guardar libros reales, ni usarlos como ejemplos (`NORMAS.md`, regla de datos reales). El enlace «Probar con un
  ejemplo» usa un libro **construido y ficticio**.
- Los roles no se tocan (con el acceso apagado todo se ve).

## 3. Auditoría visual a 1366×768 (cómo hacerla sin molestar a nadie)

1. **Servidor:** solo `127.0.0.1`, puerto libre, datos en una carpeta temporal (nunca `data/`), con
   `APU_BASE` apuntando a un caso ficticio. Frontend: `npm run build` y servir el `dist/` desde FastAPI en `/app`.
2. **Navegador:** perfil propio (`--user-data-dir` en el scratchpad), viewport 1366×768; cerrar **solo el PID propio**.
   Prohibido cerrar Edge o Chrome por nombre: Eugenio usa el equipo.
3. **Por cada una de las páginas migradas** capturar: estado vacío, con datos, con error de API, con sesión
   expirada. Revisar:
   - sin scroll horizontal a 1366 px y a 1056 px (menú plegable);
   - esquinas rectas, sin sombras ni gradientes, separación por divisor de 1 px;
   - tablas densas en `sm` (32 px), cifras a la derecha con `tabular-nums`;
   - **dos semánticas de color que no se mezclan** (severidad vs. variación IBCS); morado solo en atípicos;
   - **montos exactos** disponibles (tooltip accesible) aunque se muestren en centésimas;
   - cada severidad con ícono y texto, nunca solo color (WCAG 2.1 AA);
   - sin animaciones decorativas; `prefers-reduced-motion` respetado;
   - textos: sin rayas (—), sin mayúsculas espaciadas, estados vacíos que enseñan qué hacer.
4. **Coherencia entre páginas:** buscar en `src/**/*.scss` valores sueltos (px, colores hex, `border-radius`
   distinto de 0, `box-shadow`) que no salgan de tokens de Carbon; unificar en `src/comun/comun.scss`.
5. **Revisores:** `silice-rev-diseno` con las capturas; `silice-rev-pruebas` para las pruebas nuevas;
   `silice-rev-seguridad` si se toca algo de sesión o archivos subidos (la subida de Excel lo es).
6. **Accesibilidad:** recorrer con teclado cada página (foco visible, orden de tabulación, `aria-label` en
   SideNav, `role="status"` en avisos). Pasar `axe` si ya está en las dependencias; **no agregar paquetes**
   (`package.json` solo lo cambia S2-orq).
7. Entregable: `docs/bitacora/2026-10-19-auditoria-visual-front.md` con hallazgos priorizados
   (bloqueante / importante / pulido), captura de cada uno y el arreglo propuesto o aplicado.

## 4. Reglas de oro (de la ruta y de Eugenio)

- TDD con rojo visto; `pytest -W error`; cero omitidas. **La suite completa la corre una sola sesión a la vez**.
- **Sin `git worktree add`** (TESIS pesa ~20 GB); reutilizar worktrees existentes; `.venv` común con `uv run --active`;
  `node_modules` por junction. Commit local al cerrar cada tarea; sin `git stash` simple; sin push a `main`.
- Si una decisión cambia lo que se construye: anotarla como ruling en la bitácora con su costo.
- Lo irreversible, outward (push, PR, fusión a main, gasto en API de pago, mensajes al tutor) queda **registrado y
  sin hacer**: Eugenio decide cuando vuelva.

## 5. Criterio de «terminado»

Inicio sin errores de red (H-2 resuelto); menú por áreas con descripciones y panel de 3 herramientas; Historial
funcionando con auditorías de prueba ficticias; recorrido nuevo o su diferimiento anotado; `npm test/lint/build/dist`
verdes; bitácora de auditoría visual con cero bloqueantes abiertos.
