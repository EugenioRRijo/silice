# Ruta de construcción por sesiones: asistente, cambio visual, auditoría en el visor, arenera y escritorio

> **Fecha:** 2026-10-18 · **Base:** `main` en `5aa3da2` (Sílice 1.0.0, etiquetas `v1.0.0` y `v1.0-tesis`)
> **Implementa:** [PLAN_GESTOR_PRODUCCION_Y_AUDITORIA_VISUAL.md](./PLAN_GESTOR_PRODUCCION_Y_AUDITORIA_VISUAL.md) con las enmiendas de su §0
> **Fuentes de datos de cantera:** [PLAN_FUENTES_DATOS_CANTERA.md](./PLAN_FUENTES_DATOS_CANTERA.md)
> **Fichas de los subagentes:** [`.claude/agents/silice-*.md`](../../.claude/agents/) · **Skills:** [`.agents/skills/`](../../.agents/skills/)

Este documento es la **fuente única** del orden de trabajo, de quién hace cada tarea y con qué modelo y esfuerzo.
El plan del gestor dice *qué* se construye; esta ruta dice *en qué orden y con quién*.

---

## 1. Decisiones que fijan la ruta (Eugenio, 2026-10-18)

| # | Decisión | Origen |
|---|---|---|
| RS-1 | El plan de `docs/planes/` es lo que se construye. | Eugenio |
| RS-2 | **Las pruebas vuelven a ser obligatorias** (TDD, `-W error`, cero omitidas). La regla del 2026-10-12 («sin pruebas») queda derogada: era para ahorrar tokens hasta la 1.0.0. | Eugenio |
| RS-3 | El día a día de la empresa es **montar y revisar presupuestos y construir obra civil**: el centro es **auditar**. La arenera es secundaria y empieza por lo simple: **cuánto hay y cuánto queda** de cada material. | Eugenio |
| RS-4 | Orden: **primero el asistente**, luego **el cambio visual**, y un **plan de fuentes** para las cifras de cantera. | Eugenio |
| RS-5 | La tecnología la decide el orquestador (Eugenio: «te lo dejo a ti»). Ver §2. | Eugenio → ruling |
| RS-6 | Diseño obligatorio: **IBM Carbon** (densidad y severidad, morado para atípicos), **SAP Fiori** (valor, meta y desviación) e **IBCS** (favorable/desfavorable, no positivo/negativo). | Eugenio |
| RS-7 | Cada subagente tiene **modelo y esfuerzo** fijados en su ficha (§3); una tarea puede pedir otro en la tabla de su sesión. | Eugenio |
| RS-8 | **Modo local con Ollama en pausa**: el código existente no se retira ni recibe trabajo nuevo; RF-90 (b) queda diferido. | Eugenio (2026-10-18) |
| RS-9 | **E3 y E5 (opción A):** el protocolo del experimento sigue congelado; su 0/24 se informa como hipótesis previa falsada y límite del método. | Eugenio (2026-10-18) |
| RS-10 | **Sin gasto en la API de pago por ahora** («110 USD es muy caro»): la corrida real del experimento (RF-95) queda en pausa. | Eugenio (2026-10-18) |
| RS-11 | **Que el usuario sepa qué error hay y decida si lo corrige:** se agrega la regla R17 «Conexión de cada punto» (punto sin fuente o sin circuito), como mejora del producto que el experimento congelado no mide. | Eugenio (2026-10-18) |
| RS-12 | **La arenera (sesión 4) se instala como herramienta sin datos reales de la empresa**: datos construidos declarados como ficticios (NORMAS §1); la empresa carga los suyos cuando los tenga. El costo horario sigue esperando fuentes verificadas. | Eugenio (2026-10-18) |

## 2. Decisiones técnicas del orquestador (rulings, ratificables)

| # | Ruling | Por qué | Costo si es erróneo |
|---|---|---|---|
| RT-1 | **Un solo backend de API:** el FastAPI de `api/` ya existente; ningún segundo servidor de API (Streamlit sigue siendo la interfaz vieja mientras dure RT-4). | DRY; la API ya tiene clave, protección de red y tope de cuerpo (`api/proteccion.py`). | Bajo. |
| RT-2 | **Interfaz nueva en `frontend-desktop/`** (Vite + React 19 + TypeScript + Univer), **servida primero por el propio FastAPI** en `/app`. CSP `default-src 'self'` (con `worker-src 'self' blob:` solo si Univer lo exige, justificado); **fuentes IBM Plex alojadas en el propio servidor** (nada de CDN: RNF-08); **prohibido `@univerjs-pro`** (licencia comercial), solo paquetes Apache-2.0. | Funciona en el navegador de otra PC de la red local (decisión S-D3 de la 1.0.0); Tauri no sirve a un segundo equipo. | Medio: si se exige escritorio puro desde el inicio, se adelanta la sesión 5. |
| RT-3 | **Tauri v2 como envoltorio** de esa misma interfaz, en la **sesión 5**, sobre el Python que ya instala Inno Setup. **No medido aún:** el instalador pesa 129,80 MB de 150 MB (RNF-19) y debe funcionar sin internet y sin administrador en Windows 10 22H2, donde WebView2 no está garantizado y su instalador sin conexión no cabe en el margen. La tarea 2.7 deja en la CI un **presupuesto de tamaño** del `dist`; la tarea 5.0 decide cómo se garantiza WebView2 o enmienda RNF-19; el job de Windows de la CI necesitará Rust. | Un sidecar empaquetado aparte (segundo Python) no cabe. | Medio-alto: si WebView2 no se resuelve, el escritorio queda solo para Windows 11. |
| RT-4 | **Streamlit convive** mientras las páginas se migran una a una; se retira cuando la nueva interfaz cubra lo mismo (decisión en la sesión 6). | La 1.0.0 entregada sigue funcionando entre sesiones. | Bajo. |
| RT-5 | **Transporte en el escritorio (sesión 5): bucle local `127.0.0.1` con puerto efímero y clave por sesión entregada por IPC de Tauri** (nunca en `localStorage`). En la red local sigue el puerto fijo de la configuración (`operacion/config.py`). Named Pipes queda como endurecimiento posterior. | uvicorn no sirve por Named Pipes de Windows sin un transporte propio; la API ya filtra por red (`api/proteccion.py`). | Bajo. |
| RT-6 | **La réplica visual extiende `adapters/hoja_empresa/`**; no se crea `adapters/excel_visual/` con un segundo parser. **Costo declarado:** `lector.py` abre en solo lectura a propósito (el modo normal cuesta ~7 s por libro) y en solo lectura no hay combinadas ni dimensiones, así que `visual.py` hace una **tercera apertura en modo normal**, solo para el aspecto, después de la guardia (`adapters/hoja_empresa/guardia.py`). | El lector ya hace las dos lecturas (`data_only`) y las reglas ya apuntan a `HOJA!CELDA` (DRY). | Bajo: ~7 s más por libro abierto en el visor. |
| RT-7 | **La arenera empieza como inventario** (entradas, despachos de báscula, ajustes por conteo). El costo horario de maquinaria espera a tener fuente verificada ([PLAN_FUENTES](./PLAN_FUENTES_DATOS_CANTERA.md)). `produccion/` entra en `PAQUETES_FUERA_DEL_NUCLEO` (`tests/unit/test_arquitectura.py`) con su propia regla de importaciones; `InsumoCanteraDTO` **vive en `produccion/`** (no en `core.contracts`) y el paso a la lista de precios de la empresa lo hace `api/` o un módulo de integración con permiso explícito de importar `core.catalog`. | RS-3; NORMAS §1 y §5. | Bajo. |
| RT-8 | Versiones: cada sesión que entrega código cierra con una versión SemVer menor (**1.1.0, 1.2.0…**) que **toma al fusionar** (la siguiente libre en `main`, por orden de llegada, no por número de sesión); no se reabre la 1.0.0. | La 1.0.0 está etiquetada; «Sílice 1.5» ya nombra el spec de la fusión con los libros (no es una versión). | Bajo. |
| RT-9 | **Acceso de la interfaz nueva:** `/app` es estático y público, **sin secretos**; la persona entra con su cuenta de la instalación (`seguridad/sesiones.py`, roles de S3) y recibe una cookie de sesión `HttpOnly` + `SameSite=Strict` con token anti-CSRF; las rutas que usa la interfaz se mapean a la matriz de roles. La clave de API `X-Silice-Clave` sigue siendo para integraciones, no para el navegador. La API viene apagada por defecto (`operacion/config.py`): la interfaz nueva la necesita encendida en el bucle local. | Una navegación no envía cabeceras y meter la clave en el HTML la expone a toda la red local; la API hoy no conoce usuarios ni roles. | Medio: es trabajo de seguridad propio de la sesión 2 (tarea 2.3). |

## 3. Subagentes, modelo y esfuerzo

Ocho constructores (uno por skill), seis revisores y un escriba. Cada ficha vive en `.claude/agents/<nombre>.md` y
manda leer su skill de `.agents/skills/` antes de empezar (las skills tienen **una sola copia**: no se duplican en
`.claude/skills/`). Al despachar, el orquestador pasa además `model` y `effort` explícitos.

### 3.1 Constructores

| Ficha | Skill | Modelo | Esfuerzo | Área exclusiva | Por qué ese modelo |
|---|---|---|---|---|---|
| `silice-asistente-ia` | `asistente-ia` | **Opus** | high | `asistente/`, `ml/`, `ui/atipicos.py`, secciones del asistente y de atípicos en las páginas Streamlit (las nombra cada plan de sesión) | Aporte central de la tesis; privacidad; la IA nunca escribe el número final |
| `silice-auditoria-forense` | `auditoria-forense` | **Opus** | high | `adapters/hoja_empresa/reglas.py`, `auditoria/`, capa Delta | El dictamen es prueba documental: una regla mal hecha lo invalida |
| `silice-backend` | `back-clean-arch` | **Opus** | high | `api/`, `operacion/` salvo `base_datos.py`, `desktop/` (sesión 5) | Contratos que consumen todos, guardia de `core/`, transporte y seguridad |
| `silice-replica-excel` | `replicacion-excel` | Sonnet | high | `adapters/hoja_empresa/visual.py` (`lector.py` y `guardia.py` solo con permiso del plan) | Coordenadas exactas celda ↔ lienzo, sobre un lector que ya existe |
| `silice-frontend` | `front-carbon-fiori-ibcs` | Sonnet | high | `frontend-desktop/` | Muchos componentes, bien especificados por Carbon/Fiori/IBCS |
| `silice-pruebas` | `pruebas-cobertura` | Sonnet | high | `tests/fixtures/`, `tests/conftest.py` y pruebas transversales (cada constructor es dueño de las pruebas TDD de su tarea) | Oráculos independientes y conjuntos exactos de hallazgos |
| `silice-base-datos` | `base-datos-migraciones` | Sonnet | medium | `migraciones/`, `operacion/base_datos.py` | Alembic ya tiene su patrón; el riesgo lo cubre el respaldo previo |
| `silice-arenera` | `gestor-produccion-aridos` | Sonnet | medium | `produccion/` | Inventario: entra, sale, queda |

### 3.2 Revisores (la aprobación de todos es la compuerta de cada sesión)

| Ficha | Encargo | Modelo | Esfuerzo | Cuándo |
|---|---|---|---|---|
| `silice-rev-arquitectura` | Vistas 4+1, NORMAS §2, guardia de `core/`, DRY | **Opus** | high | todas las sesiones de código |
| `silice-rev-seguridad` | Secretos, red, entrada hostil (xlsx), OWASP | **Opus** | high | sesiones 1, 2, 3 y 5 |
| `silice-rev-requisitos` | IEEE 830, ERS, trazabilidad RF/RNF | Sonnet | high | todas |
| `silice-rev-pruebas` | IEEE 829, ISO/IEC 25010, oráculos no circulares | Sonnet | high | todas las de código |
| `silice-rev-diseno` | Carbon, Fiori, IBCS, accesibilidad | Sonnet | medium | sesiones 2, 3, 4 y 5 |
| `silice-rev-hechos` | Cada cita `archivo:línea`, cada cifra y cada fuente | Haiku | medium | todas |

### 3.3 Escriba (tareas mecánicas)

| Ficha | Modelo | Esfuerzo | Qué hace |
|---|---|---|---|
| `silice-escriba` | Haiku | low | Índices, CHANGELOG, bitácora a partir de lo que le dicta el orquestador, copiar archivos, correr `ruff` y las guardias y devolver la salida |

**El orquestador** (la sesión principal) corre en **Opus**: escribe el plan detallado de cada sesión, reparte,
integra, corre los cierres y registra los rulings.

## 4. Protocolo de cada sesión (sin interrupciones)

Cada sesión se abre en una sesión nueva de Claude Code con esta orden:

> «Lee `docs/planes/RUTA_SESIONES.md` y ejecuta la **Sesión N** con sus subagentes.»

1. **Arranque.** `git fetch`; worktree nuevo desde `origin/main` (`.worktrees/s<N>`, rama `inc/ruta-s<N>-<tema>`).
2. **Plan detallado.** Si la sesión no lo tiene, el orquestador lo escribe en `docs/planes/PLAN_SESION_<N>_<TEMA>.md`
   (skill `superpowers:writing-plans`: archivos, firmas, pruebas con sus valores, comandos) y lo commitea. Antes de
   inventar archivos o firmas, **busca si un plan anterior ya los especificó** (`PLAN_SILICE_0x0.md`) y si la meta
   (`scripts/meta_silice*.py`, pares `ParTDD`) ya exige nombres: se adoptan esos (DRY).
3. **Enmienda de requisitos.** El plan detallado incluye una tarea que enmienda `docs/ERS.md` (UC, RF, RNF nuevos con
   su criterio de aceptación), `docs/modelo_datos.md` si cambia una tabla y la meta de la versión. Numeración libre
   al 2026-10-18: **UC-26, RF-111 y RNF-22 en adelante**, repartida por sesión en §8 para que las sesiones en
   paralelo no choquen.
4. **Construcción.** Una tarea por subagente, con su ficha, modelo y esfuerzo de la tabla; TDD (rojo visto → verde);
   tareas sin archivos compartidos van en paralelo, las demás en orden. Cuando la tabla pide un modelo distinto del
   de la ficha, la fila lo marca «(excepción RS-7)».
5. **Revisión por tarea.** `silice-rev-pruebas` + el revisor del área; con hallazgos bloqueantes se corrige y se
   vuelve a pasar.
6. **Cierre de la sesión (compuerta).** Suite completa una vez
   (`uv run pytest -W error --junitxml=reporte-pruebas.xml` + `uv run python scripts/verificar_omitidas.py
   reporte-pruebas.xml`), `uv run ruff check .`, `uv run python scripts/guardia_nucleo.py --base origin/main`;
   los revisores de §3.2 que tocan a la sesión **aprueban**; PR con CI verde (Linux, Windows, calidad); fusión con
   merge commit; bitácora `docs/bitacora/2026-10-ruta-s<N>.md`.
7. **Encadenar.** Se abre la sesión siguiente sin esperar confirmación (regla de autonomía vigente). Lo que exige a
   Eugenio (gasto, instalar algo, una decisión que cambia lo que se construye) se anota como **bloqueo** en la
   bitácora y se sigue con lo demás.

**Nunca:** tocar `core/` (`git diff origin/main -- core/` vacío), versionar libros reales
(`docs/auditoria/*.xlsx|pdf`, `data/confidencial/`), gastar en la API de pago sin autorización expresa, abrir la red
en una prueba, ni usar `COMPARTIR_ONLINE.bat`.

## 5. Las sesiones

### Sesión 0 — Fundación (esta) · sin versión (solo documentos)

| Tarea | Quién | Modelo | Esfuerzo |
|---|---|---|---|
| 0.1 Fichas `.claude/agents/silice-*.md` y skills versionadas (con sus correcciones) | orquestador | Opus | high |
| 0.2 Esta ruta, enmiendas §0 al plan del gestor, README e índice del manual | orquestador | Opus | high |
| 0.3 [PLAN_FUENTES_DATOS_CANTERA.md](./PLAN_FUENTES_DATOS_CANTERA.md) | orquestador | Opus | high |
| 0.4 Plan detallado de la sesión 1 | orquestador | Opus | high |
| 0.5 Revisión: requisitos, arquitectura, hechos | revisores | §3.2 | §3.2 |

**Compuerta S0:** los tres revisores aprueban; PR de documentos fusionado.

### Sesión 1 — Asistente de IA: cerrar sus deudas · **1.1.0** · plan: [PLAN_SESION_1_ASISTENTE.md](./PLAN_SESION_1_ASISTENTE.md)

| Tarea | Quién | Modelo | Esfuerzo |
|---|---|---|---|
| 1.1 RF-100: variaciones atípicas en la serie fechada de precios (USD) de un insumo, ADVERTENCIA `CODIGO_ATIPICO` (Tarea 22 de `PLAN_SILICE_080.md`) | `silice-asistente-ia` | Sonnet (excepción RS-7) | high |
| 1.2 Reactivar la clave de IA desde el respaldo cifrado (pantalla del administrador) | `silice-asistente-ia` | Opus | high |
| 1.3 Las seis pruebas y el fixture del experimento que faltan (Tareas 17–19 de `PLAN_SILICE_090.md`) | `silice-pruebas` | Sonnet | high |
| 1.4 Experimento RF-95: informe `docs/resultados_asistente.md` con lo que no gasta (medición controlada) | `silice-asistente-ia` | Sonnet (excepción RS-7) | medium |
| 1.5 Enmienda de la ERS (RF-100 → 1.1.0, estado de RF-95, deroga la regla «pruebas en la auditoría final») | orquestador | Opus | high |
| 1.6 Cierre 1.1.0: versión, CHANGELOG, bitácora | `silice-escriba` | Haiku | low |
| 1.7 Regla R17 «Conexión de cada punto» (RS-11, RF-141), fuera de los archivos congelados del experimento | `silice-auditoria-forense` | Opus | high |

Revisores: arquitectura, seguridad, requisitos, pruebas, hechos.
**Bloqueos conocidos (de Eugenio):** la corrida real del experimento queda en pausa (RS-10, sin gasto) y el modo
local también (RS-8).

### Sesión 2 — Cambio visual: base y visor de solo lectura · **1.2.0**

| Tarea | Quién | Modelo | Esfuerzo |
|---|---|---|---|
| 2.0 Plan detallado; versiones exactas (≥ 2 semanas) y licencias de React, Vite, Univer y `@carbon/*` | orquestador | Opus | high |
| 2.1 Andamiaje `frontend-desktop/` (Vite + React 19 + TS + Vitest), tokens Carbon como variables CSS, job de CI | `silice-frontend` | Sonnet | high |
| 2.2 `adapters/hoja_empresa/visual.py`: estilos, combinadas, anchos y altos → instantánea de libro para Univer | `silice-replica-excel` | Sonnet | high |
| 2.3 `POST /v1/libros/replica`, servir `/app` estático con CSP, y acceso por cuenta + cookie de sesión + anti-CSRF (RT-9) | `silice-backend` | Opus | high |
| 2.4 Visor `UniverGrid` + capa de halos (severidad **con ícono**) desde `POST /v1/libros/auditoria` | `silice-frontend` | Sonnet | high |
| 2.5 Tarjeta `IndicadorFiori` (valor, meta, Δ, Δ%) con semántica IBCS | `silice-frontend` | Sonnet | medium |
| 2.6 Pruebas de coordenadas (backend = posición en pantalla) con un libro anonimizado y oráculo a mano | `silice-pruebas` | Sonnet | high |
| 2.7 El instalador lleva la interfaz compilada; presupuesto de tamaño del `dist` en la CI; total ≤ 150 MB | `silice-backend` | Sonnet (excepción RS-7) | medium |

Revisores: arquitectura, seguridad, requisitos, pruebas, diseño, hechos.

### Sesión 3 — Auditoría forense en el visor (Capa Delta) · **1.3.0**

| Tarea | Quién | Modelo | Esfuerzo |
|---|---|---|---|
| 3.0 Plan detallado | orquestador | Opus | high |
| 3.1 Tabla de parches Delta en `casos/*.db` (migración Alembic con respaldo previo) | `silice-base-datos` | Sonnet | medium |
| 3.2 Servicio de parches: crear, revertir, huella SHA-256 del original, libro corregido derivado (reusa `escritor/devolucion`) | `silice-auditoria-forense` | Opus | high |
| 3.3 Acciones de 1 clic: adoptar precio de la lista de la empresa, ajustar a MaPreX, recalcular fórmula, justificar | `silice-auditoria-forense` | Opus | high |
| 3.4 Rutas de parches y dictamen | `silice-backend` | Opus | high |
| 3.5 `AuditPopover`, `DeltaHistory`, filtros y halo morado de RF-100 | `silice-frontend` | Sonnet | high |
| 3.6 «Explicar con IA» en el popover (la IA explica; los valores los pone el sistema) | `silice-asistente-ia` | Opus | high |
| 3.7 Panel del asistente en la interfaz nueva con diff del borrador e informe completo (hueco S4 §3.1 paso 5) | `silice-frontend` | Sonnet | high |

Revisores: todos.

### Sesión 4 — Arenera: inventario y báscula · **1.4.0**

| Tarea | Quién | Modelo | Esfuerzo |
|---|---|---|---|
| 4.0 Plan detallado y verificación de las fuentes de [PLAN_FUENTES](./PLAN_FUENTES_DATOS_CANTERA.md) | orquestador + `silice-rev-hechos` | Opus / Haiku | high / medium |
| 4.1 `produccion/`: materiales, movimientos (producción, despacho, ajuste por conteo), existencia y mínimo | `silice-arenera` | Sonnet | medium |
| 4.2 `produccion.db` con Alembic | `silice-base-datos` | Sonnet | medium |
| 4.3 Importador de báscula con detección de columnas y bandeja de pesajes sospechosos | `silice-arenera` | Sonnet | high |
| 4.4 Rutas `/v1/produccion/*` | `silice-backend` | Sonnet | high |
| 4.5 Tablero de existencias (Fiori) y `DropzoneBascula` | `silice-frontend` | Sonnet | high |
| 4.6 Partes diarios de maquinaria (horómetro, diésel, incidencias: `Maquinaria`, `ParteDiario`, `TarjetaMaquinaria` de 48 px), costo horario e `InsumoCanteraDTO` → lista de precios de la empresa (**solo con fuentes verificadas**) | `silice-arenera` + `silice-frontend` | Opus (excepción RS-7) / Sonnet | high |

Revisores: arquitectura, requisitos, pruebas, diseño, hechos.

### Sesión 5 — Escritorio con Tauri v2 · **1.5.0**

| Tarea | Quién | Modelo | Esfuerzo |
|---|---|---|---|
| 5.0 Plan detallado | orquestador | Opus | high |
| 5.0b Decidir cómo se garantiza WebView2 sin internet ni administrador en Windows 10 22H2, o enmendar RNF-19 (RT-3) | orquestador + `silice-rev-seguridad` | Opus | high |
| 5.1 `desktop/src-tauri/`: ventana, arranque del Python instalado, puerto efímero + clave por IPC, watchdog | `silice-backend` | Opus | high |
| 5.2 Inno Setup lleva el ejecutable de Tauri; tamaño ≤ 150 MB; prueba de humo; Rust en el job de Windows de la CI | `silice-backend` | Sonnet (excepción RS-7) | high |
| 5.3 Pruebas del ciclo de vida (caída y relanzamiento del backend) | `silice-pruebas` | Sonnet | high |

Revisores: arquitectura, seguridad, pruebas, diseño, hechos.
**Bloqueo conocido (de Eugenio):** instalar Rust (`rustup`) en su equipo.

### Sesión 6 — Auditoría de la ruta y release

| Tarea | Quién | Modelo | Esfuerzo |
|---|---|---|---|
| 6.1 Auditoría con los seis revisores sobre `main` completo | revisores | §3.2 | §3.2 |
| 6.2 Suite completa, metas, cobertura por capa, instalador medido | `silice-pruebas` | Sonnet | high |
| 6.3 Decisión sobre el retiro de Streamlit (RT-4) y release | orquestador | Opus | high |

## 6. Bloqueos que dependen de Eugenio

| # | Qué | Sesión que lo necesita |
|---|---|---|
| B-1 | ~~Autorizar el gasto de la corrida real con Claude (~110 USD)~~ **No autorizado por ahora (RS-10)** | 1 (no bloquea el resto) |
| B-2 | ~~Instalar Ollama y el modelo local~~ **En pausa (RS-8)** | — |
| B-3 | Un libro de la empresa **anonimizado** con `scripts/anonimizar_libro.py` para las pruebas del visor | 2 |
| B-4 | ~~Muestras reales de báscula e inventario~~ **No aplica (RS-12)**: se construye con datos ficticios declarados | — |
| B-5 | Instalar Rust | 5 |

## 7. Diferido (fuera de esta ruta, con motivo)

| Qué (del plan del gestor) | Motivo | Cuándo se reconsidera |
|---|---|---|
| Extracción, voladura y acarreo (§3) | RS-3: la arenera empieza por existencias; sin fuentes ni datos de la empresa | tras la sesión 4, con datos de la empresa |
| Balance de masa en trituración (`balance_planta`, §3.1) y reparto de costos conjuntos | Depende de F-3/F-4 de PLAN_FUENTES y del costo horario (4.6) | sesión 4.6 o posterior |
| Desgaste de piezas (muelas, conos, mallas, llantas) y ensayos de acopio | Sin fuente verificada ni datos de la empresa | tras la sesión 4 |
| Réplica visual desde PDF | El lector PDF actual solo verifica (L10/L11); la réplica en lienzo se hace sobre `.xlsx` | sesión 6 |
| Named Pipes de Windows | RT-5: solo si una prueba real muestra un antivirus bloqueando el bucle local | sesión 5 |

## 8. Sesiones en paralelo (Eugenio abre cada ventana)

Cada sesión corre en **su propia conversación de Claude Code**, abierta por Eugenio. Dependencias:

| Sesión | Puede empezar | Depende de |
|---|---|---|
| 1 Asistente | en curso | — |
| 2 Cambio visual | **ya** | — |
| 4 Arenera | **ya**, tareas 4.0–4.4 y la parte de backend de 4.6 | la tarea 4.5 (pantallas) espera a que la sesión 2 fusione `frontend-desktop/`; 4.6 espera fuentes verificadas |
| 3 Auditoría en el visor | cuando la sesión 2 esté en `main` | 2 |
| 5 Escritorio Tauri | cuando la sesión 2 esté en `main` y haya Rust (B-5) | 2 |
| 6 Auditoría y release | al final | todas |

**Reglas para no chocar:**

| Recurso | Regla |
|---|---|
| Carpetas | cada sesión usa solo `.worktrees/s<N>*` y ramas `inc/ruta-s<N>-*`; nunca toca las de otra |
| `git stash` | prohibido el `stash` simple (la pila es común a todas): `git stash push -u -m "<etiqueta única>"` y `apply` por SHA, o un commit WIP |
| Numeración de la ERS | S1: **RF-141** (R17, RS-11; cierra además RF-100 y RF-95 en parte) · S2: **UC-26, RF-111–RF-118, RNF-22–RNF-23** · S3: **UC-27, RF-119–RF-126, RNF-24** · S4: **UC-28–UC-29, RF-127–RF-136, RNF-25** · S5: **RF-137–RF-140, RNF-26–RNF-27** |
| Versión | la toma al fusionar (RT-8): `pyproject.toml` se cambia en el último commit, justo antes del PR, tras traer `main` |
| `CHANGELOG.md` | solo líneas nuevas bajo «Sin publicar»; al chocar se conservan las dos |
| `api/main.py`, `tests/unit/test_arquitectura.py` | solo agregar líneas; `docs/api.json` se **regenera** después de traer `main`, nunca se fusiona a mano |
| Migraciones Alembic | una sola cabeza por base: antes del PR, `git merge origin/main` y re-apuntar la revisión nueva a la cabeza vigente |
| Archivos congelados del experimento | ningún archivo de `archivos_del_auditor` (`asistente/experimento/protocolo.json`) se toca; `tests/unit/test_experimento_congelado_vigente.py` lo vigila (RS-9) |
| Antes de cada PR | `git fetch && git merge origin/main`, suite completa, metas; la CI verde manda |
| Carga del equipo | como máximo **tres** sesiones a la vez (cada una con sus subagentes); la suite completa no se corre en dos sesiones al mismo tiempo |
