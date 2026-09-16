# Diseño — Integración continua con GitHub Actions (RNF‑06, RNF‑07 y guardia del núcleo)

**Fecha:** 2026‑09‑14 · **Estado:** aprobado en conversación (el usuario eligió las cuatro
garantías y aceptó las propuestas) · **Rama:** `inc/CI-integracion-continua`, apilada sobre
`worktree-sprint-multidominio` (PR #1) · **Autoridad:** [CLAUDE.md](../../../CLAUDE.md),
[docs/ERS.md](../../ERS.md) (RNF‑06, RNF‑07), [docs/plan_pruebas.md](../../plan_pruebas.md)

## 1. Contexto y alcance

Hoy toda la verificación del proyecto (suite con `-W error`, ruff, `core/` intacto, cobertura,
artefactos regenerables) se ejecuta a mano en un único equipo Windows. Tres consecuencias:

- **RNF‑07 portabilidad está en «parcial»**: «Windows ✔; Linux pendiente»
  ([calidad_iso25010.md](../../calidad_iso25010.md) §6). El usuario no quiere instalar Linux.
- **La hipótesis central se vigila con metas de sprint** (`meta_alpha.py`, `meta_multidominio.py`)
  cuyas bases están fijas (`sprint-0`, `m-base`): sirven para cerrar un sprint, no para vigilar cada
  cambio.
- **Los artefactos «reproducibles»** (`docs/api.json`, `docs/resultados_ml.md`) solo se comprueban
  si alguien se acuerda de regenerarlos.

**Alcance:** un pipeline de GitHub Actions (runners alojados por GitHub: nada que instalar en el
equipo) que en cada PR y en cada push a `main` garantice:

1. **Suite + ruff en Linux** con todos los extras, sin pruebas omitidas.
2. **Guardia del núcleo**: ningún commit mezcla `core/` con `adapters/` o `ml/`, y ninguna rama que
   incorpora un dominio cambia `core/` (la regla de `meta_alpha.estado_nucleo_intacto`).
3. **Cobertura y reproducibles**: `core/` ≥ 80 % (RNF‑06) y `docs/api.json` y
   `docs/resultados_ml.md` idénticos a lo que regeneran sus scripts.
4. **También Windows**: la suite corre en una matriz Linux + Windows.

**Fuera de alcance:**
- **Reproducibilidad de los extractores de PDF** (`extraer_maprex.py`, `extraer_arenaza.py`):
  necesitan PyMuPDF y sus salidas ya las verifican las pruebas de fixture.
- **Medición de RNF‑03 en CI:** el rendimiento de un runner compartido no es comparable con el
  umbral de la ERS.
- **Reglas de protección de rama:** son configuración del repositorio y decide el usuario;
  conviene activarlas tras el primer verde.
- **macOS**, porque la ERS no la declara.
- **Insignia en `README.md`:** el archivo está vedado, ver §8.

## 2. Enfoques considerados

| Enfoque | Veredicto |
|---|---|
| **A. Un workflow con dos jobs** (calidad rápida + pruebas en matriz) y dos scripts pequeños que reutilizan `meta_alpha.py` | **Elegido.** Cada garantía es un paso con nombre propio en el run; la lógica nueva es mínima y se prueba en unidad |
| B. Ejecutar las metas de sprint en CI | Descartado: bases fijas y metas propias de un sprint. M11 («`core/` intacto desde `m-base`») sería falsa en cualquier sesión de núcleo legítima |
| C. Una capa nueva (nox, tox o pre-commit) | Descartado: duplica lo que `uv` ya resuelve y añade una herramienta sin necesidad (YAGNI) |

## 3. El pipeline (`.github/workflows/ci.yml`)

**Disparadores:** `pull_request` (cualquier rama base, para que corra también en PR apilados),
`push` a `main` y `workflow_dispatch`. **Concurrencia:** grupo `ci-${{ github.ref }}` con
`cancel-in-progress` (un push nuevo cancela la corrida vieja del mismo PR). **Permisos:**
`contents: read`. **Entorno:** `HF_HUB_DISABLE_SYMLINKS_WARNING=1` (la misma variable que ya fijan
las pruebas). **Shell por defecto:** `bash` en los dos sistemas (Git Bash viene en los runners
Windows), para que cada comando se escriba una sola vez.

Acciones fijadas: `actions/checkout@v7` y `actions/cache@v6` por versión mayor, y
`astral-sh/setup-uv@v10.1.0` por versión exacta, porque ese repositorio no publica la etiqueta
flotante `v10` (la primera corrida falló al resolverla). `setup-uv` va con `version: "0.11.9"`, la
de desarrollo, y `enable-cache: true`.

### 3.1 Job `calidad` (ubuntu-latest, sin extras pesados)

| Paso | Comando | Garantía |
|---|---|---|
| Checkout con historia completa | `actions/checkout@v7`, `fetch-depth: 0` | la guardia necesita el rango |
| Entorno mínimo | `uv sync --locked --only-group dev` | — |
| Ruff | `uv run --no-sync ruff check .` | 1 |
| Guardia del núcleo | `uv run --no-sync python scripts/guardia_nucleo.py --base "$BASE"` | 2 |

`BASE` se resuelve en el paso: `origin/${{ github.base_ref }}` en un PR; `github.event.before` en
un push a `main` (si vale `000…0`, primer push de la rama, el paso lo anuncia y no evalúa);
`origin/main` en `workflow_dispatch`.

### 3.2 Job `pruebas` (matriz `ubuntu-latest`, `windows-latest`; `fail-fast: false`)

| Paso | Comando | Dónde | Garantía |
|---|---|---|---|
| Checkout | `actions/checkout@v7` | ambos | — |
| uv con caché | `astral-sh/setup-uv@v10` | ambos | — |
| Caché del modelo de similitud | `actions/cache@v6` sobre `~/.cache/huggingface`, clave con el SO y `paraphrase-multilingual-MiniLM-L12-v2` | ambos | — |
| Entorno completo | `uv sync --locked --all-extras` | ambos | — |
| Suite | `uv run --no-sync pytest -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml --cov=core --cov=ml --cov=api --cov=adapters --cov-report=term` | ambos | 1, 4 |
| Sin pruebas omitidas | `uv run --no-sync python scripts/verificar_omitidas.py reporte-pruebas.xml` | ambos | 1, 4 |
| Cobertura de `core/` | `uv run --no-sync coverage report --include="core/*" --fail-under=80` | Linux | 3 |
| Artefactos reproducibles | `exportar_openapi.py` y `generar_resultados_ml.py`, luego `git diff --exit-code -- docs/api.json docs/resultados_ml.md` | Linux | 3 |

Cobertura y reproducibles corren solo en Linux: el contenido es el mismo en los dos sistemas y
Windows escribe CRLF en modo texto, que `git` normaliza pero que duplicaría minutos sin aportar
evidencia nueva.

**Por qué «sin omitidas» es un paso:** siete archivos de prueba usan `pytest.importorskip` para
ifcopenshell, scikit‑learn y sentence‑transformers, y `test_normalizacion.py` se omite si el modelo
no se puede descargar. Si un extra faltara en CI, esas pruebas desaparecerían en silencio y el run
saldría verde. Hoy la suite local tiene **0 omitidas**; CI lo convierte en invariante.

## 4. Componentes nuevos

### 4.1 `scripts/guardia_nucleo.py`

- **Qué hace:** aplica la regla de la hipótesis central al rango `<base>..HEAD` y sale con 1 si se
  viola.
- **Qué reutiliza:** de `scripts/meta_alpha.py`, `_commits_nucleo_intacto`, `_ramas_adaptador`,
  `estado_nucleo_intacto` (pura, con cinco pruebas) y `Estado`. El precedente de importar los
  auxiliares privados de `meta_alpha` ya existe en `meta_multidominio.py`.
- **Lógica nueva, pura y probada:** `codigo_salida(estado) -> int`. FALLA da 1; OK y PENDIENTE
  dan 0. PENDIENTE significa que el rango no tiene commits de `adapters/` ni de `ml/`, así que no
  hay nada que violar.
- **Base inválida:** si `git rev-parse --verify <base>^{commit}` falla, sale con **2** y lo dice.
  `_commits_nucleo_intacto` devuelve una lista vacía ante un rango inválido, y eso se leería como
  PENDIENTE y pasaría en silencio; la validación explícita cierra ese hueco.
- **Interfaz:** `uv run python scripts/guardia_nucleo.py --base main` funciona igual en local.

### 4.2 `scripts/verificar_omitidas.py`

- **Qué hace:** lee el JUnit de pytest y sale con 1 si alguna prueba se omitió, listando cada una
  con su motivo.
- **Qué reutiliza:** de `meta_alpha.py`, `_testcases` y `_resultado_de`, que ya clasifican un
  `testcase` como pasadas, fallidas, errores u omitidas.
- **Lógica nueva, pura y probada:** `omitidas(xml_texto) -> list[str]`, con cada omitida como
  `classname::name — motivo`.
- **Ausencia de evidencia:** un archivo inexistente, un XML ilegible o cero pruebas sale con **2**,
  no con 0. Es el mismo principio de `meta_alpha.estado_pruebas`: la ausencia de datos nunca es
  un OK.

## 5. Documentación

- **`docs/plan_pruebas.md`:** §7 (entorno) describe el pipeline y cómo reproducir cada paso en
  local. §9, fila RNF‑07, pasa a «cumple» con el enlace al run verde en Linux, solo después de ver
  ese run.
- **`docs/calidad_iso25010.md`:** §6 Portabilidad y la fila de §9 cambian de veredicto con esa
  misma evidencia. Es un cambio de veredicto real, así que corresponde tocar el archivo.
- **`docs/manual_tecnico.md` §2:** qué vigila CI y el comando local equivalente de cada paso.
- **Bitácora `docs/bitacora/2026-09-14-CI-integracion-continua.md`:** qué se construyó, las
  pruebas negativas, el tiempo de cada job en la primera corrida y los hallazgos de portabilidad.

## 6. Pruebas y criterios de aceptación

1. **TDD** en los dos scripts: cada prueba en rojo antes de su implementación.
2. **Suite local verde** con `-W error`, ruff limpio y
   `git diff worktree-sprint-multidominio --stat -- core/` vacío (CI es infraestructura: no toca
   el núcleo).
3. **Pruebas negativas locales**, registradas en la bitácora, que demuestran que cada guardia
   muerde:
   - un `docs/api.json` alterado hace que `git diff --exit-code` salga con 1;
   - un JUnit con una omitida hace que `verificar_omitidas.py` salga con 1;
   - un commit desechable en una rama temporal, que toca `core/` y `adapters/`, hace que
     `guardia_nucleo.py` salga con 1; la rama se borra después;
   - una base inexistente hace que la guardia salga con 2.
4. **Remoto:** el PR #2 muestra `calidad`, `pruebas (ubuntu-latest)` y `pruebas (windows-latest)`
   en verde, con los pasos de §3 visibles por nombre.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| El lock resuelve torch con CUDA en Linux (15 paquetes `nvidia-*`): varios GB de descarga y disco | Caché de `setup-uv`; medir la primera corrida. Si el job falla por disco o tarda en exceso, se abre como decisión aparte el índice CPU de PyTorch para Linux (`[tool.uv.sources]`, cambia `uv.lock`); **no** se hace a ciegas en esta sesión |
| La descarga del modelo falla y la prueba se omite | Es el comportamiento buscado: el paso «sin omitidas» pone el run en rojo de forma visible; la caché lo hace improbable |
| Cupo de minutos del plan en un repo privado, con Windows a tarifa doble | Disparadores acotados (PR y push a `main`), cancelación de corridas obsoletas y cachés. El consumo real se consulta en Settings → Billing |
| Diferencias Linux/Windows que aparezcan en la primera corrida | Son hallazgos de RNF‑07: se corrigen si son defectos de portabilidad y se registran en la bitácora. Nunca se omite una prueba por plataforma para obtener un verde |
| PR apilado sobre el PR #1 | Al fusionar el PR #1, se reorienta el PR #2 a `main` |

## 8. Mecánica y restricciones

- **Worktree y rama:** worktree `.claude/worktrees/ci-integracion`, rama
  `inc/CI-integracion-continua`, PR #2 con base `worktree-sprint-multidominio`.
- **Plan:** `docs/superpowers/plans/2026-09-14-ci-integracion-continua.md`.
- **Commits:** Conventional Commits en español, sin tildes en el asunto; un commit por componente
  (spec, cada script, workflow y documentación).
- **Vedados**, igual que en el sprint multidominio: `CLAUDE.md`, `README.md`, `docs/README.md`,
  `docs/linea_base.md` y `docs/tesis/**` tienen cambios sin commitear del usuario. Quedan como
  pendientes en la bitácora: la convención de CI en `CLAUDE.md` §3 y la insignia del README.
- **Sin cambios de dependencias:** todo con `--locked`, y `uv.lock` no se toca en esta sesión.
