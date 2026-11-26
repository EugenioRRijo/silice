# Plan del front después de medir con personas (auditoría del 2026-11-25)

**Origen.** Cinco auditorías de solo lectura sobre `frontend-desktop/src` (unas 51.000 líneas): la Hoja; Componer,
Control, Producción y Mercado; Administración, Archivos, Existencias, Precios de la empresa, Índices, Reajuste y
Auditoría; el resto de las páginas; y la base común. Se auditó con los principios de ub-mode y la guía de Google
*modern-web-guidance*, leída desde el disco y sin telemetría. Salieron unos 170 hallazgos con archivo:línea; los
informes completos (A a E) están en [auditoria-front-2026-11-25/](auditoria-front-2026-11-25/).

> **Enmienda del 2026-11-25:** Eugenio decidió reestructurar el front **antes** de medir (Propuesta B, fases B0, B1,
> B4 y B2; fecha tope 2026-12-16). Lo que sigue dice lo que se planeaba antes de esa decisión. Manda el
> [acta](../bitacora/2026-11-25-acta-reestructuracion-front.md).

**Cuándo se aplica.** Después de la prueba con personas: SUS, comprensión de las 6 alertas y libros nuevos. El front
es parte de lo que se mide, y el congelamiento del consejo del 2026-11-24 lo incluye. Excepción: el punto 0.

## 0. Antes de la prueba con personas (verificar, no cambiar)

- **Filtros de Control** (`paginas/control/index.tsx:19-41,101-113`). Cada pestaña monta su propio `Resultados`, así
  que el corte y los valores de Km y R podrían volver a su valor inicial al cambiar de pestaña. Ninguna prueba lo
  fija. Hay que comprobarlo en el navegador: si pasa, puede confundir a quien hace la prueba.
- **Actualización** (`paginas/actualizacion/index.tsx:291`). Se puede enviar mientras la vista previa aún carga, y
  se pierden las altas de catálogo marcadas. Hay que comprobarlo y, si se confirma, avisarle a quien conduce la
  prueba.
- **Reglas del proyecto rotas a la vista**, que la guardia de la CI no detecta:
  - tuteo en `actualizacion/logica.ts:8`, `pendientes/textos.ts:33` y `precios_empresa/index.tsx:284`;
  - decimales con punto en el `title` de `comun/TablaDensa.tsx:75-86`, `PanelDesglose.tsx:51` y
    `tablero/index.tsx:41`;
  - enteros sin punto de miles en 4 sitios.

  Son correcciones de texto. Eugenio decide si se hacen antes de la prueba (con acta) o después.

**Resultado de la revisión en el navegador (2026-11-25, demo ficticia, rama `main` en `a28df67f`):**
- **Control: confirmado.** En Valor ganado se calculó al corte del 13/11/2026, con la escalatoria, Km = 1,15 y
  R = 0,1. Al pasar a «Alertas y reproyección» y volver, el formulario quedó en blanco y la tabla volvió al corte por
  omisión (20/11/2026). Se pierde lo escrito y también lo calculado.
- **Actualización: confirmado al leer el código.** El botón «Revalorar» solo exige un archivo
  (`actualizacion/index.tsx:291`). Mientras la vista previa carga, la lista de insumos desconocidos está vacía
  (`:124`), así que un envío temprano revalora sin que la persona haya podido marcar las altas de catálogo. En este
  equipo la vista previa responde casi al instante, así que la ventana es corta.
- **Ninguno afecta la prueba con personas:** sus tareas (leer el total, crear una partida y decir si el presupuesto
  tiene problemas) no pasan por Control ni por Actualización. Los dos se arreglan con el resto del plan, después de
  medir.

## 1. Arreglos de base (cada uno mejora todas las pantallas)

1. **Sesión vencida en un solo lugar.** `e instanceof ErrorDeApi && e.estado === 401` aparece en unos 110 sitios
   de 86 archivos. Se registra una vez en `api/cliente.ts` (`pedir`) y cada pantalla decide solo sus casos propios
   (422, 409). Guía: ub-mode, «una decisión en un lugar».
2. **Respuestas validadas en la frontera.** `pedir<T>` hace `as T` sin comprobar nada (184 usos). Parsear una vez en
   `api/` con validadores por recurso; dentro, confiar. Guía: ub-mode, «Boundary Discipline».
3. **Un solo diálogo modal sobre `<dialog>` y `showModal()`.** Hoy hay entre 11 y 12 diálogos hechos a mano con
   `role="dialog"`, trampas de foco y manejo de Esc propios, de tres implementaciones distintas. Antes del cambio, una
   prueba de contrato común fija el foco inicial, Esc, el bloqueo durante el envío y el retorno del foco. Guías:
   `ui-components/dialog.md`, `ui-behaviors/platform-controls-dismiss-dialog.md` y
   `ui-behaviors/prevent-page-scroll-under-modal-dialog.md`.
4. **Una sola carga de datos.** Siete o más variantes de «cargar y descartar la respuesta vieja», cuando ya existen
   `useCarga` y `useVista`. Basta un `useConsulta` con `AbortController`; `vial/useTramos.ts` es el modelo a copiar.
5. **Utilidades únicas:**
   - «hoy en AAAA-MM-DD», hoy copiado en 12 archivos;
   - «monto con valor exacto», con 4 mecanismos distintos;
   - «mover el foco al resultado», en 9 efectos;
   - el permiso «¿puede abrir esta pantalla?», en 5 sitios;
   - el esqueleto de carga, en 8 sitios (ya existe `comun/EsqueletoPagina`).
6. **Códigos estables del servidor en vez de leer su prosa.** Hoy varias pantallas deciden con regex,
   `startsWith` o `includes` sobre el texto del servidor: `vial/AvisoDeLlevar.tsx`, `riesgo/logica.ts`,
   `escenarios/logica.ts`, `tablero/logica.ts`, `procura.ts`, `logicaPlanta.ts`, `reajuste/logica.ts` y otras.
   Además, `aprobar/logica.ts:78-105` arma en el front el veredicto «CUMPLE / NO CUMPLE», que debe llegar del
   servidor.

## 2. Pantallas grandes con estado frágil (después de la base)

| Pantalla | Problema | Dirección |
|---|---|---|
| `componer/ComponerPartida.tsx` (630 líneas, ~25 estados) y `TablaInsumos.tsx` | El origen de cada celda vive en tres mapas por número de fila, reindexados a mano | Tipo por fila con id estable y `useReducer` |
| `hoja/useEdicionDeSeccion.ts` | Objeto mutable con 6 banderas; el vaciado está copiado 3 veces | Unión discriminada y función pura `siguiente(estado, evento)` |
| `marco/Marco.tsx` (699 líneas) y `shell/contexto.tsx` | Contexto con campos opcionales «para las pruebas» | Partir el marco y hacer obligatorios esos campos |
| `escenarios/index.tsx` (360 líneas, 12 estados), `riesgo`, `actualizacion`, `vial/Tramos`, `tablero` | Máquinas de estado propias dentro de la vista | Hooks y `useReducer`; un `Bloque` común en tablero |
| `hoja/ProveedorDeLaHoja.tsx` | El contexto se recrea en cada render y mezcla datos, acciones y diálogos | Memoizar o partir en tres contextos |
| `precios_empresa/index` (564), `reajuste/index` (535), `AuditarApuPorHoja` (559), `ImportarPlano` (386), `Visor` (523) | Mezclan vista, red y reglas | Lógica pura en `logica.ts`, con pruebas directas |

## 3. Accesibilidad y formularios

- Al cambiar de pantalla con el menú, el foco no pasa al `h1` ni se anuncia la pantalla nueva
  (`Marco.tsx:687-699`). La navegación lateral desplegada no está dentro de `<nav>`.
- Los formularios con `noValidate` no llevan el foco al primer campo inválido. El modelo a copiar es
  `indices/SeriesViales.tsx`. Guía: `accessibility/accessible-error-announcement.md`.
- `inputMode="decimal"` en todas las cifras con coma; hoy solo lo tiene Cantidad en Agregar partida. Respetar
  `isComposing` al interceptar Enter. Guías: `forms/forms.md` y `forms/ime-safe-enter-submit.md`.
- El foco se pierde al revocar claves, al cerrar el detalle del Historial y en `fieldset disabled`.
- Regiones `aria-live` demasiado grandes (tablas enteras) o que cambian a cada tecla.
- El `listbox` de Pendientes no responde a Enter.
- Confirmaciones que faltan: anular una valuación, «Elegir y crear la versión» y «Descartar escenarios».

## 4. Rendimiento y seguridad

- Tablas grandes sin tope: la matriz del plan, `HistoricoDePrecios`, `TablaDensa` y el catálogo. Medir con datos
  reales antes de virtualizar; empezar por `content-visibility: auto` (guía
  `performance/defer-rendering-heavy-content.md`).
- El marco importa de forma estática la Hoja y la Bandeja, y `paginas/hoja` importa de `marco/`: hay que separarlos
  y cargar por demanda.
- `archivos/logicaComputo.ts:154-183` reescribe el cliente HTTP con su cabecera CSRF: unificarlo con `pedir`.
- `riesgo/logica.ts:86-98` manda el mapa en la URL de un GET: pasarlo a POST.
- `SubidaArchivo` no tiene tope de tamaño.

## 5. Lo que está bien y se conserva

- No hay `dangerouslySetInnerHTML`, `innerHTML` ni `href` dinámico.
- `localStorage` se usa solo para preferencias y con `try/catch`.
- La CSP es estricta y no hay peticiones a terceros.
- Las cifras se formatean en `indicadores/formatoEsVe.ts`.
- Las severidades llevan icono y palabra.
- Los gráficos de tablero tienen al lado una tabla con los montos exactos.
- `vial/useTramos.ts` y `indices/SeriesViales.tsx` son los modelos a copiar.
- Hay muchas pruebas de comportamiento (de 28 a 47 por página).

## Orden recomendado (método ub-mode)

1. Fijar el comportamiento actual con pruebas en los puntos a tocar, sobre todo la prueba de contrato del diálogo.
2. Aplicar la base, puntos 1.1 a 1.6, cada uno en su PR.
3. Pantallas grandes, de una en una, con crapper y mutator antes y después.
4. Accesibilidad, rendimiento y seguridad.
5. Repetir el cuestionario SUS si los cambios son grandes.
