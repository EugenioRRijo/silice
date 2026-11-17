# Manual de orquestación de Sílice

**Fecha:** 2026-11-17 · **Estado:** vigente; sustituye a `manual_orquestador_optimizacion.md` (retirado: hablaba de
Tauri, de tuberías en la suite y de rutas que ya no existen).

Lo leen Eugenio y los agentes de IA que trabajan en el proyecto: Claude (orquestador) y Antigravity (`agy`, con los
modelos Hydrogen y Argon) como segunda opinión. Lo que aquí se marca **(propuesto)** todavía no existe en el
repositorio.

---

## 1. Para qué sirve y qué manda

Hay tres documentos que mandan, cada uno en lo suyo:

| Documento | Qué dice | Si choca con otro |
|---|---|---|
| [ESTADO.md](ESTADO.md) | Qué está en `main`, qué vive en ramas, qué falta y qué espera a Eugenio | Manda en todo lo que sea *estado* |
| [NORMAS.md](../NORMAS.md) | La constitución: principios, cálculo, contratos, reglas, compuertas | Manda en *qué* se construye |
| Este manual | El *cómo se trabaja*: ciclo de una tarea, herramientas, compuertas de cierre | Cede ante los dos anteriores |

[metodologia.md](metodologia.md) es el texto de la tesis sobre el proceso (Scrum-Cascada y DRY) y sus fuentes únicas
(§5.1). Este manual lo aplica al día a día; no lo repite. Los `PLAN_*.md`, `docs/planes/` y las bitácoras fechadas son
historia: explican por qué algo es así, no cómo es hoy ([AGENTS.md](../AGENTS.md)).

---

## 2. La metodología

### 2.1 Cascada: el orden de las etapas de una fase

Una fase pasa por cinco etapas en orden. No se salta a la siguiente sin cruzar su compuerta.

| Etapa | Documento que sale | Compuerta para seguir |
|---|---|---|
| 1. Requisitos | Los RF y RNF nuevos en [ERS.md](ERS.md), con su criterio de aceptación | Eugenio está de acuerdo con el *qué* |
| 2. Diseño | Una especificación fechada en [especificaciones/](especificaciones/) | Especificación revisada y **aprobada** por Eugenio |
| 3. Construcción | Un plan en `docs/planes/` y los commits rojo/verde en una rama `feature/*` | Cada tarea del plan cerrada con sus pruebas |
| 4. Pruebas | Suite verde, guardias en verde y, si hay pantalla, la pasada en navegador | §6 de este manual |
| 5. Entrega | Árbitro APROBADO, PR a `main`, ESTADO y CHANGELOG al día | Eugenio fusiona |

Lo que toca `core/` lleva además su expediente y el aval del tutor antes de la etapa 3 (NORMAS §9).

### 2.2 Scrum: cómo se construye dentro de la etapa 3

La construcción se hace en **olas** cortas (sprints). Cada ola tiene un objetivo y unas pocas tareas.

| Pieza de Scrum | En Sílice |
|---|---|
| Backlog | Las tareas del plan y los hallazgos abiertos de la bitácora y de ESTADO §5 |
| Planificación | La skill `writing-plans`: el plan con tareas pequeñas, cada una con su prueba |
| Daily | ESTADO §3 («Trabajo en curso»), que el orquestador actualiza al cerrar cada tarea grande |
| Revisión | La revisión de cada tarea y el arbitraje de la ola (§3) |
| Retrospectiva | Las lecciones van a la bitácora de la ola y a la memoria del orquestador; si cambian el proceso, a este manual y a NORMAS (§7) |

Roles:

| Rol | Quién | Qué hace |
|---|---|---|
| Dueño del producto | Eugenio | Decide requisitos y prioridades, aprueba especificaciones, **fusiona** en GitHub |
| Aval académico | El tutor | Aprueba cualquier cambio de `core/` y de la arquitectura, y las decisiones D-n |
| Orquestador | Claude | Hace de scrum master e integrador: planifica, reparte, revisa, integra, actualiza ESTADO |
| Equipo | Subagentes (`silice-*`, ECC) y Antigravity | Construyen o revisan una tarea acotada |

[metodologia.md §3.1](metodologia.md) todavía describe los roles como se redactaron para la tesis (tesista y Claude).
Ajustarlo a esta tabla es **(propuesto)** como enmienda en el mismo PR que este manual.

Cuando Eugenio está ausente, cada decisión se simula con datos ficticios, se elige la mejor y queda en un acta de la
bitácora y en ESTADO §4, siempre reversible.

### 2.3 DRY: no te repitas

Cada regla vive en una sola función y los demás la llaman. La tabla de fuentes únicas es
[metodologia.md §5.1](metodologia.md). En el código de hoy:

1. **La lógica vive en `aplicacion/`.** Las rutas de `api/rutas/` solo traducen HTTP: leen la petición, llaman a
   `aplicacion/` y devuelven la respuesta. Una ruta que calcula, valida un negocio o arma un presupuesto está en la
   capa equivocada. Guardia automática de esto: **(propuesto)**; hoy lo vigila el revisor `silice-rev-arquitectura`.
2. **Antes de escribir una función, búscala.** Primero `graphify explain` o `graphify query` (§4.5), después `grep`.
   Si existe algo parecido, se reutiliza o se generaliza; no se escribe otra.
3. **Una sola función por regla.** Las que más se repiten:
   - Texto a `Decimal`: hoy hay dos copias de `decimal_desde_texto` (`aplicacion/composicion.py:92` y
     `api/esquemas.py:19`) y varios `_decimal` privados en `aplicacion/`, `api/rutas/` y `adapters/`. Unificarlas en
     una sola es **(propuesto)**. Mientras tanto, nada nuevo copia una tercera.
   - Montos para informes y mensajes: `formatear_decimal` de `core/verification/texto.py`. Devuelve texto con punto
     decimal; el front lo muestra con coma decimal y punto de miles con `frontend-desktop/src/indicadores/formatoEsVe.ts`.
   - Redondeo (decisión de Eugenio del 2026-11-17, pendiente de ratificar por el tutor): **al presentar**,
     `ROUND_HALF_UP` (el que ya usa `formatear_decimal`); **al calcular**, `ROUND_HALF_EVEN` con 28 dígitos, el
     contexto del motor (`core/budget/comparacion.py:54`, `core/budget/reajuste.py:71`).
4. **Nada se copia entre capas.** Si dos capas necesitan lo mismo, la función sube al paquete común más cercano
   (metodologia §5.2, regla 6). La interfaz no calcula: recibe texto exacto de la API.
5. **Módulos de tamaño razonable.** Un módulo que no cabe en una lectura es difícil de revisar. Hoy los más grandes son
   `aplicacion/hoja.py` (3.195 líneas, congelado por el experimento de la tesis), `aplicacion/control.py` (1.554) y
   `aplicacion/composicion.py` (1.471). Lo nuevo va en módulos aparte; un tope medido por una prueba es **(propuesto)**.

---

## 3. El ciclo de una tarea

| Paso | Qué se hace | Herramienta | Quién |
|---|---|---|---|
| 1. Idea | Se entiende el pedido, se buscan sistemas parecidos y estándares | `superpowers:brainstorming` o `/egm:egm-brainstorm` | Claude con Eugenio |
| 2. Especificación | Se escribe el diseño en `docs/especificaciones/AAAA-MM-DD-<tema>.md` | `/egm:egm-draft` o a mano | Claude |
| 3. Revisión de la especificación | Otra mirada busca huecos y contradicciones con NORMAS y el ERS | `/egm:egm-review` o `/egm:egm-review-loop`; `/egm:egm-resolve` para cerrar comentarios; `silice-rev-requisitos` | Revisores; Eugenio aprueba |
| 4. Plan | Tareas pequeñas, cada una con su prueba y sus archivos | `superpowers:writing-plans` | Claude |
| 5. Construcción | TDD en un worktree reutilizado: prueba en rojo, commit, código, commit | `superpowers:using-git-worktrees`, `superpowers:subagent-driven-development` o `superpowers:executing-plans`, `superpowers:test-driven-development`; constructores `silice-*` | Subagentes |
| 6. Revisión | Cada tarea se revisa antes de pasar a la siguiente | `superpowers:requesting-code-review`, revisores `silice-rev-*` y de ECC, `/code-review`, `/security-review` | Revisores |
| 7. Arbitraje | Un juez único dicta APROBADO o DEVUELTO sobre la rama entera | Claude xhigh con [MANUAL_ARBITRO.md](planes/MANUAL_ARBITRO.md); segunda opinión de `agy` si hace falta | Claude xhigh |
| 8. Cierre | Suite completa, PR a `main`, acta en la bitácora | `superpowers:verification-before-completion`, `superpowers:finishing-a-development-branch` | Claude |
| 9. Fusión | Se fusiona con merge commit | GitHub | **Eugenio** |
| 10. Después de fusionar | ESTADO y CHANGELOG al día **en `main`** | Una rama corta de documentación | Claude |

Al recibir comentarios de una revisión se usa `superpowers:receiving-code-review`: cada comentario se comprueba
contra el código antes de aplicarlo. Ante un fallo, `superpowers:systematic-debugging` (una hipótesis a la vez).

---

## 4. Catálogo de herramientas

### 4.1 Skills de proceso (plugin superpowers)

Se invocan con la herramienta Skill (`superpowers:<nombre>`).

| Skill | Cuándo |
|---|---|
| `brainstorming` | Antes de cualquier cosa nueva: aclarar el pedido y las opciones |
| `writing-plans` | Con la especificación aprobada, antes de tocar código |
| `executing-plans` | Claude ejecuta el plan él mismo, sin subagentes |
| `subagent-driven-development` | Claude reparte las tareas del plan a subagentes y revisa cada una |
| `dispatching-parallel-agents` | Dos o más tareas sin archivos en común |
| `test-driven-development` | Siempre antes de escribir código |
| `systematic-debugging` | Ante una prueba roja o un comportamiento raro |
| `verification-before-completion` | Antes de decir «hecho», «pasa» o «arreglado» |
| `requesting-code-review` / `receiving-code-review` | Pedir revisión / atender sus comentarios con rigor |
| `finishing-a-development-branch` | Al terminar la rama: decidir PR, limpieza |
| `using-git-worktrees` | Al empezar una tarea aislada (ver §5 sobre reutilizar) |

### 4.2 EGM (plugin de Google)

Para el ciclo de especificaciones. Se invocan como órdenes:

- `/egm:egm-brainstorm`: explorar la idea.
- `/egm:egm-draft`: redactar la especificación.
- `/egm:egm-review` y `/egm:egm-review-loop`: revisarla, una vez o en bucle hasta que no queden hallazgos.
- `/egm:egm-resolve`: cerrar los comentarios de la revisión.
- `/egm:egm-drift-report`: comparar especificaciones y código y listar dónde se separaron (§7).

Cuidado: sus revisores **no leen AGENTS.md**. En el encargo se les pasan las reglas que importan (NORMAS §1 sobre
datos, `core/` cerrado, coma decimal, `aplicacion/` frente a `api/rutas/`) y se les pide responder en español.
**No usar `egm-bootstrap`**: crea un README en cada carpeta.

### 4.3 ECC (plugin)

Agentes revisores, cada uno con su área:

| Agente | Para qué |
|---|---|
| `silent-failure-hunter` | Errores tragados, `except` vacíos, valores por omisión que esconden fallos |
| `refactor-cleaner`, `code-simplifier` | Código muerto y simplificación, después de que las pruebas estén verdes |
| `fastapi-reviewer`, `python-reviewer` | `api/` y el Python en general |
| `react-reviewer`, `typescript-reviewer` | `frontend-desktop/` |
| `type-design-analyzer` | Diseño de tipos y contratos nuevos |
| `mle-reviewer` | `ml/` |
| `pr-test-analyzer` | Si las pruebas de un PR cubren lo que cambia |
| `e2e-runner` | Pruebas de punta a punta en el navegador |

Skills: `contract-first` (contrato de la API antes que el código), `change-impact` (qué rompe un cambio),
`production-audit`, `react-testing`, `frontend-a11y`, `e2e-testing`, `fastapi-patterns`.

**No usar** `doc-updater` (reescribe documentos sin respetar las fuentes únicas) ni `database-reviewer` (está pensado
para PostgreSQL; Sílice usa SQLite).

### 4.4 Agentes y skills propios

- `.claude/agents/silice-*`: los **constructores** (`silice-backend`, `silice-frontend`, `silice-base-datos`,
  `silice-pruebas`, `silice-asistente-ia`, `silice-auditoria-forense`, `silice-replica-excel`, `silice-arenera`,
  `silice-escriba` para tareas mecánicas) y el nuevo `silice-aplicacion` para la lógica de `aplicacion/` (llega en el
  mismo PR que este manual). Los **revisores** solo leen y dictaminan: `silice-rev-arquitectura`, `silice-rev-pruebas`,
  `silice-rev-seguridad`, `silice-rev-diseno`, `silice-rev-requisitos` y `silice-rev-hechos`. El puente con Antigravity
  es `silice-antigravity`.
- `.agents/skills/`: guías por área que leen todos los agentes, también Antigravity. Las de proceso son
  `metodologia-silice`, `arbitro-independiente` y `colaboracion-con-claude`; las de área, `back-clean-arch`,
  `front-carbon-fiori-ibcs`, `base-datos-migraciones`, `pruebas-cobertura`, `asistente-ia`, `auditoria-forense`,
  `replica-excel` y `gestor-produccion-aridos`.

### 4.5 Leer el código: graphify

El grafo del código vive fuera de OneDrive, en `C:\Users\euger\Silice-grafo`. Se lee antes de abrir archivos, para no
cargar módulos enteros.

```bash
bash /c/Users/euger/Silice-grafo/actualizar.sh            # rehace el grafo desde origin/main
graphify explain "aplicacion/composicion.py" --graph /c/Users/euger/Silice-grafo/src/graphify-out/graph.json
graphify query "donde se convierte texto a Decimal" --graph /c/Users/euger/Silice-grafo/src/graphify-out/graph.json --budget 3000
graphify path "A" "B" --graph /c/Users/euger/Silice-grafo/src/graphify-out/graph.json --undirected
```

Después se leen **solo las líneas que el grafo cita**. El grafo refleja la rama de `VERSION.txt`; para otra rama,
`bash /c/Users/euger/Silice-grafo/actualizar.sh feature/x`.

### 4.6 Antigravity (`agy`)

- **Hydrogen** (esfuerzo alto) construye o audita por áreas de 10.000 a 15.000 líneas, con un encargo de contexto
  cerrado: qué archivos, qué reglas, qué formato de respuesta.
- **Argon** solo para arbitrajes cortos, de pocos tokens.
- **Claude xhigh** es el árbitro final y único.
- Hydrogen exagera la gravedad. Cada hallazgo suyo lo verifica un subagente contra el código antes de corregir nada.
- Se llama con el subagente `silice-antigravity` o con el servidor MCP `antigravity` (`scripts/mcp_antigravity.py`,
  registrado en `.mcp.json`; herramientas `encargar_a_antigravity` y `arbitrar_rama`). Trabaja en solo lectura y
  nunca recibe libros ni cifras de la empresa: procesa en la nube de Google.
- Si audita por su cuenta, anota en `docs/bitacora/auditoria-agy-AAAA-MM-DD.md` y Claude escribe el veredicto al lado.
- Por línea de órdenes, desde la raíz del repositorio y con el encargo en un archivo:
  `timeout 30m agy -p "$(cat encargo.md)" --model gemini-4-hydrogen-high --sandbox --print-timeout 20m0s </dev/null`.
  Varios encargos por áreas pueden correr en paralelo (con `&`); un área de más de 25.000 líneas agota el tiempo.

### 4.7 Interfaz y textos

- `unslop-interfaz`: **solo** para auditar si una pantalla parece hecha por IA. Manda
  [frontend-desktop/DESIGN.md](../frontend-desktop/DESIGN.md); si la skill sugiere algo que lo contradice, gana
  DESIGN.md.
- `impeccable`: diseño y pulido de pantallas, dentro de lo que fija DESIGN.md.
- `frontend-a11y` (ECC): accesibilidad (WCAG 2.1 AA).
- Redacción: `humanizer` para quitar el tono de IA a un texto; `unslop` para textos en inglés.

### 4.8 Controles automáticos

- **Reglas Hookify locales**, en `.claude/hookify.*.local.md` del checkout principal (no se versionan: están en
  `.git/info/exclude`):
  - bloquean editar un `.py` de `core/`, escribir `import streamlit` y hacer `git add` de libros Excel, `.docx`,
    perfiles de libros o `docs/auditoria/`;
  - avisan al correr pytest o vitest con `| tail` (o `head`, `grep`, `sed`) sin `pipefail`, y al editar un plan
    cerrado o una bitácora fechada.
- **Hooks de ECC**: activos, con algunos apagados en `.claude/settings.local.json` (`ECC_DISABLED_HOOKS`).
- **Revisiones integradas**: `/code-review` (errores de corrección) y `/security-review`.
- **En la CI** (`.github/workflows/ci.yml`): `scripts/guardia_nucleo.py`, `scripts/meta_datos.py`, la suite, ruff y
  `npm run lint`.

---

## 5. Reglas de trabajo con subagentes

1. **Un worktree por tarea, reutilizado.** El repositorio pesa unos 20 GB: antes de crear uno nuevo se reutiliza uno de
   `.worktrees/` con su `.venv` y su `node_modules`. NORMAS §3 fija el tope de worktrees vivos.
2. **Archivos que no se cruzan.** Dos subagentes en paralelo nunca editan el mismo archivo. El plan dice qué archivos
   toca cada tarea.
3. **Commits rojo/verde.** Primero `test(<area>): ... (rojo)` con la prueba sola, después `feat|fix(<area>): ...`.
   Conventional Commits en español, asunto sin tildes.
4. **Sin push hasta el arbitraje.** La rama se sube cuando el árbitro la aprueba.
5. **La suite sin tuberías.** Un `| tail` cambia el código de salida. Se corre sin tubería, o con `set -o pipefail;`
   delante y la salida completa guardada en un archivo.
6. **Entorno idéntico a la CI**: `uv sync --locked --all-extras`.
7. **El checkout principal puede estar en una rama vieja.** Para leer `main`, se lee en un worktree al día o con
   `git show main:<ruta>`. Nunca se cambia de rama en el checkout principal si hay agentes trabajando en él.
8. **Datos reales nunca al repositorio** (NORMAS §1): ni libros, ni lo anonimizado, ni lo derivado, ni en commits,
   pruebas, capturas, PR o encargos a Antigravity. Las pruebas usan casos construidos de `tests/fixtures/`.
9. **`core/` solo con expediente y aval del tutor.** Si una tarea parece necesitar el núcleo, se detiene y se anota el
   hallazgo (NORMAS §9).
10. **Cada encargo es autosuficiente.** El subagente solo sabe lo que dice el encargo: objetivo, archivos, reglas, qué
    ya se descartó y el formato de la respuesta.
11. **Lo que dice un subagente se comprueba.** Su informe es una pista; la prueba es el comando y su salida.

---

## 6. Compuertas y definición de «hecho»

Una tarea está **hecha** cuando todo esto está en verde y la salida se vio (no se supone):

```powershell
uv run pytest -W error -q                 # suite de Python, completa al cerrar una fase
uv run ruff check .                       # estilo
uv run python scripts/meta_datos.py       # naturaleza de los datos (D1-D4)
cd frontend-desktop; npm run lint; npx vitest run --maxWorkers=3
```

Además:

- `scripts/guardia_nucleo.py` en verde: `core/` no cambió o tiene expediente.
- Si hay pantalla nueva: pasada en navegador con la siembra ficticia.
- Árbitro Claude xhigh: **APROBADO** (o aprobado con cambios ya corregidos con prueba en rojo primero).
- Ningún RF, matriz ni documento contradice el código (metodologia §3.4).

Qué se actualiza al cerrar:

| Cuándo | Qué | Dónde |
|---|---|---|
| Al cerrar la ola | Acta del arbitraje y lecciones | `docs/bitacora/` (y `docs/bitacora/arbitrajes/`) |
| En el PR | Entrada en «Sin publicar» | `CHANGELOG.md` |
| **Después** de que Eugenio fusiona | §1, §2 y §3 al día | `docs/ESTADO.md` **en `main`** |

---

## 7. Cómo evitar que la documentación se desincronice

Lecciones del 2026-11-17: el PR #109 entró a `main` y ESTADO.md seguía diciendo que `feature/ola2` estaba abierta;
fichas de agentes y el manual anterior nombraban Tauri y rutas que ya no existen.

1. **ESTADO se actualiza en `main` después de cada fusión.** No en la rama de la feature: ahí queda viejo en cuanto se
   fusiona. Una rama corta de documentación lo pone al día.
2. **Cada cambio de proceso lleva su enmienda en NORMAS en el mismo PR.** Si cambia cómo se trabaja, se toca este
   manual y el registro de enmiendas de NORMAS juntos.
3. **Cada especificación declara su estado** de una lista cerrada (borrador, aprobada, construida, sustituida) y, si se
   sustituye, enlaza a la que la reemplaza («sustituido por …»). Una guardia que lo compruebe es **(propuesto)**.
4. **Al cerrar cada ola, `/egm:egm-drift-report`**: compara especificaciones y código y lista las diferencias. Cada
   diferencia se corrige o se anota en ESTADO §5.
5. **Las fichas de agentes se revisan con el código.** Si una ficha nombra una carpeta o tecnología, debe existir.
   Una prueba que lo verifique es **(propuesto)**.
6. **No se reescribe la historia.** Los planes cerrados y las bitácoras fechadas no se editan (la regla Hookify avisa);
   lo nuevo va en una entrada nueva o en una enmienda fechada.
