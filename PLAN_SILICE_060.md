# Plan de construcción de Sílice 0.6.0

> **Para quien ejecute (agentes):** SUB-SKILL REQUERIDA: `superpowers:subagent-driven-development` (un subagente
> por tarea con su ficha de rol `C:\Users\euger\.claude\agents\sf-*.md` y un revisor fresco por tarea). Los pasos
> usan casillas `- [ ]`. Cada tarea lleva su prueba primero, con el rojo observado (NORMAS §5).

**Objetivo:** entregar la 0.6.0 de Sílice. Un proyecto en Bs y otro en USD muestran su reajuste comparado, escalatoria
frente a comprobación directa, en las dos monedas. Una empresa tiene su lista de precios propia, y R11/R12 marcan los
precios fuera de rango o vencidos con el dinero que representan. Todo corre sobre bases migradas con Alembic, y cada
caso se abre desde la carpeta de datos.

**Arquitectura:** la construcción tiene tres secciones en orden estricto.
- **A (T0), transversal, sin núcleo:** el nombre pasa a Sílice; se versionan `.streamlit/config.toml` y `LICENSE`; entran las dependencias de la 0.6.0 a la 1.0.0; una guardia de red única; una meta única `scripts/meta_silice.py`.
- **B (S5‑1 adelantado), sin núcleo:** dos destinos de Alembic, `operacion.base_datos.preparar_base` y casos que se eligen de una lista; respaldo.
- **C (S1):** tres expedientes de núcleo (SL‑E1…E3) en carril único, el adaptador `adapters/bcv` en paralelo, y la interfaz.

**Tecnología:** Python 3.13, `uv`, SQLAlchemy 2.0, Alembic ≥ 1.20, Streamlit 1.62 (`AppTest`), FastAPI, `xlrd` ≥ 2.0 (extra `bcv`), `Decimal` (prec 28, ROUND_HALF_EVEN).

**Specs:** maestro `docs/especificaciones/2026-10-11-silice-1.0.0-design.md` (rulings RV‑1…RV‑26, §10), S1
`docs/especificaciones/2026-10-11-silice-s1-moneda-reajuste-design.md` y S5
`docs/especificaciones/2026-10-11-silice-s5-producto-instalador-design.md`. Todos fueron aprobados por Eugenio el
2026‑10‑11. El plan cita los specs por sección y no los repite; quien ejecute lee el plan y el spec.

## Restricciones globales

- `core/contracts/` no se toca: `git diff v0.5.0..HEAD -- core/contracts/` debe quedar vacío.
- `core/` solo cambia en las ramas `inc/060-s1-<n>-nucleo`. Cada una lleva primero su expediente en `docs/bitacora/2026-10-silice-expedientes.md` y requiere el visto bueno del tutor. Nunca hay dos ramas de núcleo abiertas a la vez (RV‑2).
- `main` es la única rama de integración. Las ramas son cortas, por fase, salen de `origin/main` del momento y abren su PR contra `main`. Se fusionan con `gh pr merge <n> --merge` al cruzar su compuerta. El `main` local está desactualizado: siempre se parte de `origin/main`.
- Montos en `Decimal`; las divisiones van dentro de `decimal.localcontext(prec=28, rounding=ROUND_HALF_EVEN)` y se redondea solo al presentar.
- Cero pruebas omitidas (`scripts/verificar_omitidas.py`), `pytest -W error`, ruff limpio solo sobre los archivos tocados (nunca `ruff format .` en todo el repositorio), y `scripts/guardia_nucleo.py --base origin/main`.
- La suite corre sin red: solo 127.0.0.1 y ::1, con `HF_HUB_OFFLINE=1` (A3).
- El bloque de regresión no cambia: `git diff v0.5.0..HEAD` vacío sobre `ARCHIVOS_REGRESION` (A4). Cubre:
  - cinco APU a ± 0,01;
  - 7 de 7;
  - R4 en 3/4 pulg;
  - TI‑001 con PE 28 586,76 USD en el Día 6;
  - dos huellas de RNF‑04;
  - cuatro hojas.
- Prohibido `pkill`, `taskkill` y matar procesos ajenos, porque hay sesiones en paralelo. Nadie toca `data/apu.db`.
- Las memorias a mano (oráculos) se escriben antes del código, con las cifras literales del spec.
- Licencia: propietaria, con todos los derechos reservados (P9).
- Las bitácoras y los specs anteriores al 2026‑10‑11 son historia y no se editan.

## Rulings del orquestador sobre el plan (2026‑10‑11)

El cotejo (`cotejo.md`, anexo) dejó siete decisiones con su valor por defecto. Seis son técnicas y se ratifican aquí
con ese valor; la séptima es de Eugenio.
- **RP‑1:** se etiqueta `v0.6.0` y después se genera su base de prueba desde la etiqueta (`inc/060-s1-5-base`). GS1 se cruza con esa fusión.
- **RP‑2:** una migración trabaja sobre una copia; el original nunca se toca y el respaldo queda para restaurar a mano. Así se cumple RF‑96 (c), que exige la misma huella.
- **RP‑3:** la API, ante una base vieja, migra con respaldo igual que la interfaz. Responde 503 solo si `preparar_base` falla.
- **RP‑4:** los scripts de siembra siguen con `create_all` y sus bases se adoptan al abrirse. El disparador para cambiarlos está en el manual técnico §10.5.
- **RP‑5:** la revisión base `caso_0001_base_0_5_0` es el DDL literal congelado de la base de prueba de `v0.5.0`, verificado contra las tres bases, en lugar de la autogeneración.
- **RP‑6:** `ifctester` va en un extra propio `ifc`, fuera de `civil` y del instalador, porque `bcf-client` declara GPLv3, incompatible con la licencia propietaria. S3‑0 resuelve la licencia antes de incluirlo.
- **Para Eugenio:** ratificar o no la enmienda de NORMAS §3 (A5). Mientras no la ratifique, queda PROPUESTA: NORMAS no cambia, se trabaja en un solo worktree `.worktrees/060` y las ramas son cortas.

## Orden y ramas

| Orden | Rama | Tareas | Condición |
|---|---|---|---|
| 1 | `inc/nombre-silice` | A1 | — |
| 2 | `inc/060-dependencias` | A2 | A1 fusionada |
| 3 | `inc/060-guardia-red` | A3 | A2 fusionada |
| 4 | `inc/060-meta` | A4 | A3 fusionada |
| libre | `inc/060-enmienda-normas` | A5 | — |
| 5 | `inc/060-s5-1-alembic` | B1–B7 (GS5‑1) | A1–A4 fusionadas |
| 6 | `inc/060-s1-0-docs` | C1–C3 (GS1‑0) | B fusionada |
| 7 | `inc/060-s1-1-nucleo` | C4–C5 (SL‑E1) | S1‑0 fusionada |
| 7′ | `inc/060-s1-2-bcv` (paralela, sin núcleo) | C6 | S1‑0 fusionada |
| 8 | `inc/060-s1-3-nucleo` | C7–C8 (SL‑E2) | S1‑1 fusionada |
| 9 | `inc/060-s1-3-ui` | C9–C10 | S1‑3 núcleo y S1‑2 fusionadas |
| 10 | `inc/060-s1-4-nucleo` | C11–C12 (SL‑E3) | S1‑3 ui fusionada |
| 11 | `inc/060-s1-4-ui` | C13 | S1‑4 núcleo fusionada |
| 12 | `inc/060-s1-5-cierre` | C14, pasos 1–4 → etiqueta `v0.6.0` | todo S1 fusionado |
| 13 | `inc/060-s1-5-base` | C14, paso 5 (cruza GS1) | etiqueta puesta |

Las tareas se numeran por sección (A1…A5, B1…B7 = «Tarea 1…7» de la sección B, C1…C14 = «Tarea 1…14» de la
sección C). El anexo «Cotejo» trae la tabla de interfaces unificadas, que **manda** sobre cualquier nombre de una sección.

## Foco de revisión (entradas que el spec implica y que ninguna prueba ejercitaba)

Cada sección cierra con su propio «Foco de revisión», y cada entrada tiene su prueba en la tarea dueña. Estas son las
cinco que más pueden morder a una persona real:
1. **La base real de Eugenio en OneDrive**, con espacios, acentos y bloqueo por sincronización: `preparar_base` debe fallar con un mensaje claro y nunca dejar una copia a medias (B).
2. **Un archivo del BCV con una hoja nueva o renombrada:** el adaptador lo rechaza con el nombre de la hoja y no lee cifras corridas (C6).
3. **Más de 7 días sin tasa del BCV:** la conversión se rechaza y se declara; nunca usa una tasa vieja en silencio (C4–C5).
4. **Cambiar la moneda de un proyecto con versiones previas:** se crea una versión nueva que pasa por el embudo, sin reescribir las anteriores (C5).
5. **Una lista de precios importada con coma decimal o con texto en celdas numéricas:** se rechaza por fila con su número, nunca se toma como cero (C7).

---

# A. Fase 0 transversal (T0): antes de cualquier núcleo

> **Para quien ejecute:** usar `superpowers:subagent-driven-development` (un subagente por tarea, con
> revisor nuevo). Los pasos usan casillas `- [ ]`. Esta sección **no toca `core/`**: en las cinco tareas,
> `uv run python scripts/guardia_nucleo.py --base origin/main` debe salir en 0 y
> `git diff --stat origin/main -- core/` debe quedar vacío.

**Meta de la fase:** dejar `main` listo para que S5‑1 y S1 construyan sin pisarse: el producto ya se llama
Sílice y escucha solo en el bucle local; todas las dependencias de la 0.6.0 a la 1.0.0 están en el candado
con sus licencias revisadas; la suite corre sin red y sin omisiones; una sola meta (`scripts/meta_silice.py`)
vigila el bloque de regresión; y la enmienda de NORMAS §3 queda escrita para que Eugenio la ratifique.

**Specs:** maestro `docs/especificaciones/2026-10-11-silice-1.0.0-design.md` §3, §5, §6 (RV‑2, RV‑17,
RV‑24), §10.3 P9; S5 `…-s5-producto-instalador-design.md` §1.2, §10.1, §11.1, §12, §13; S1 §4.4 y §9.4.

## Cómo se ejecuta

1. `git fetch origin --tags`. **El `main` local está desactualizado** (1a02530, PR #19): toda rama sale de
   `origin/main` (hoy ed597de, PR #30, que ya trae los specs de Sílice). Nunca `git pull` sobre `main` local.
2. Orden: **A1 → A2 → A3 → A4**, en serie (las cuatro tocan `pyproject.toml`/`uv.lock`, `tests/conftest.py`
   o `.github/workflows/ci.yml`). **A5** es solo documentos y puede ir en paralelo con cualquiera.
3. Worktrees (NORMAS §3 vigente: uno por sprint): A1 usa `.worktrees/nombre`, que ya existe. Al fusionar A1,
   `git worktree remove .worktrees/nombre` y luego
   `git worktree add .worktrees/060 -b inc/060-dependencias origin/main`. En ese mismo worktree, A3 y A4 se
   crean con `git switch -c inc/060-<algo> origin/main` cuando la tarea anterior ya está fusionada. A5 se hace
   ahí mismo al final, o antes en un segundo worktree solo si Eugenio ratifica la enmienda.
4. Cada tarea es **un PR contra `main`**. Se fusiona con la CI verde en Linux y Windows usando
   `gh pr merge <n> --merge` (**merge commit, nunca squash**): la comprobación C3 de la meta (A4) necesita que
   el commit de la prueba siga existiendo antes que el de su implementación.
5. En cada worktree, antes de pytest: `unset VIRTUAL_ENV; uv sync --all-extras`.
6. Commits: Conventional Commits en español, sin tildes en el asunto, terminados con la línea
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (segundo `-m`). Nunca `git add -A`, `ruff format .`,
   `pkill`/`taskkill`, ni nada contra `data/apu.db`.
7. El cuerpo de cada PR termina con la línea de atribución de Claude Code que fija el sistema.
8. **Después de T0** (orden cotejado en `cotejo.md`): la sección B (S5‑1, rama `inc/060-s5-1-alembic`) sale de
   `origin/main` con A1–A4 fusionadas —A2 ya trae `alembic` y `xlrd` en `pyproject.toml` y `uv.lock`—, y la sección C
   (S1, ramas `inc/060-s1-*`) no abre ninguna rama hasta que B esté fusionada. A5 no bloquea a nadie.

---

### Tarea A1: Renombre AREN.IA → Sílice, `.streamlit/config.toml` y licencia propietaria

**Rama:** `inc/nombre-silice` (ya existe, vacía, en 8610053; se adelanta a `origin/main` con fast‑forward; PR a `main`; RV‑2)   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/entorno.py`, `.streamlit/config.toml`, `LICENSE`, `docs/bitacora/2026-10-silice-060.md`
- Crear (pruebas): `tests/unit/test_entorno_silice.py`, `tests/unit/test_config_streamlit.py`, `tests/unit/test_nombre_silice.py`
- Modificar: `ui/caso.py:14,38-42,50-55`; `ui/app.py:36-54,82-83,130-138`; `ui/paginas/hoja.py:713`;
  `ui/composicion.py:579`; `ui/paginas/componer.py:271,307,335,516,537,628,672`; `api/main.py:18`;
  `docs/api.json:4` (regenerado); `tests/conftest.py:58-61`; `tests/unit/test_guion_prueba_arenia.py:10-15,37,124-129`;
  `tests/unit/test_guion_sf.py:76,84-85`; `pyproject.toml:2-6`; `uv.lock` (con `uv lock`); `README.md:1-6,25-30`;
  `NORMAS.md:171`; `scripts/seed_demo.py:111-118`; `scripts/meta_prototipo.py:1,370`; `scripts/README.md:19,89`;
  `docs/README.md:52`; `docs/ERS.md:151,886-893`; `docs/manual_usuario.md:46-60,78-82,120,383,657`;
  `docs/manual_tecnico.md:407,524`; `docs/guion_prueba_arenia.md` (36 líneas, inventario abajo);
  `docs/plan_pruebas.md:107`; `docs/protocolo_indicador3.md:275-278`
- No se tocan: `docs/bitacora/**`, `docs/auditoria/**`, specs anteriores al 2026‑10‑11, `PLAN_PROTOTIPO.md`.
  **No se renombran archivos** (`docs/guion_prueba_arenia.md`, `data/prueba_arenia.db`,
  `tests/unit/test_guion_prueba_arenia.py`) ni el identificador IEEE 829 `GP‑ARENIA‑001`: la bitácora y los
  specs, que no se editan, los enlazan por ese nombre.

**Inventario de partida** (`git grep -n -iE 'aren\.?ia'` sobre `origin/main`, 2026‑10‑11): 42 archivos. Fuera
de los históricos, quedan: interfaz (`ui/app.py`, `ui/caso.py`, `ui/composicion.py`, `ui/paginas/componer.py`,
`ui/paginas/hoja.py`, `ui/recorridos.py` solo nombra el archivo del guion), siembra (`scripts/seed_demo.py`),
metas (`scripts/meta_prototipo.py`), documentos vigentes (lista de arriba) y pruebas (`tests/conftest.py`,
dos pruebas del guion). **Variables:** se leen hoy solo en `ui/caso.py:38` (`ARENIA_CASO`) y
`ui/app.py:83` (`ARENIA_MODO_ENTREGA`); `tests/conftest.py:61` borra `ARENIA_CASO`. Ningún script lee
variables de entorno (`git grep -n 'environ\|getenv' -- scripts` vacío). **URLs del repositorio:** ningún
documento vigente enlaza `github.com/EugenioRRijo/<repo>` (`git grep -n -iE 'github\.com/'` sin resultados
fuera de acciones de la CI); el remoto ya es `https://github.com/EugenioRRijo/silice.git`. El paso 3.8 deja la
comprobación hecha.

**Regla de nombre** (la vigila `test_nombre_silice.py`): en los documentos vigentes y en `ui/`, «AREN.IA» solo
sobrevive como nombre histórico del prototipo con la forma exacta `AREN.IA (hoy Sílice)`; las variables
`ARENIA_*` solo se escriben en `ui/entorno.py` y en la nota de alias de los dos manuales.

**Interfaces:**
- Consume: `ui.caso.resolver_ruta(guardada: str | None, entorno: Mapping[str, str], por_defecto: str) -> Path`;
  `ui.app.modo_entrega_activo(entorno: Mapping[str, str] | None = None) -> bool`;
  `adapters.espacio.planos.comun.LIMITE_BYTES = 20 * 1024 * 1024`.
- Produce: `ui.entorno.VARIABLE_CASO = "SILICE_CASO"`; `ui.entorno.VARIABLE_MODO_ENTREGA = "SILICE_MODO_ENTREGA"`;
  `ui.entorno.ULTIMA_VERSION_CON_ALIAS = "0.6.0"`; `ui.entorno.ALIAS_ANTERIORES: dict[str, str]`;
  `ui.entorno.leer_variable(entorno: Mapping[str, str], nombre: str) -> str | None`;
  `ui.caso.VARIABLE_RUTA_CASO` (= `VARIABLE_CASO`, nombre que ya importan las pruebas);
  `ui.app.VARIABLE_MODO_ENTREGA` (reexportado); `ui.app.TITULO_APP = "Sílice"`; `.streamlit/config.toml`;
  `LICENSE`; `pyproject.toml` con `name = "silice"`.

- [ ] **Paso 0: Poner la rama al día y el entorno**
```bash
cd .worktrees/nombre
git fetch origin --tags
git merge --ff-only origin/main
unset VIRTUAL_ENV; uv sync --all-extras
```

- [ ] **Paso 1: Escribir las pruebas que fallan**

`tests/unit/test_entorno_silice.py`:
```python
"""Variables de entorno de Sílice con sus alias anteriores (plan 0.6.0, tarea A1).

Cuatro casos por variable: solo la nueva, solo la vieja, las dos (gana la nueva) y ninguna; más la nueva
en blanco, que cede al alias. El alias vive hasta la 0.6.0 inclusive: una prueba falla cuando
`pyproject.toml` pase de esa versión con el alias todavía declarado.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

import pytest
from packaging.version import Version

from ui.app import modo_entrega_activo
from ui.caso import resolver_ruta
from ui.entorno import (
    ALIAS_ANTERIORES,
    ULTIMA_VERSION_CON_ALIAS,
    VARIABLE_CASO,
    VARIABLE_MODO_ENTREGA,
    leer_variable,
)

RAIZ = Path(__file__).resolve().parents[2]
PARES = [(VARIABLE_CASO, "ARENIA_CASO"), (VARIABLE_MODO_ENTREGA, "ARENIA_MODO_ENTREGA")]


def test_los_alias_son_exactamente_los_de_arenia() -> None:
    assert VARIABLE_CASO == "SILICE_CASO"
    assert VARIABLE_MODO_ENTREGA == "SILICE_MODO_ENTREGA"
    assert ALIAS_ANTERIORES == dict(PARES)


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_solo_la_nueva(nueva: str, vieja: str) -> None:
    assert leer_variable({nueva: "a"}, nueva) == "a"


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_solo_la_vieja(nueva: str, vieja: str) -> None:
    assert leer_variable({vieja: "b"}, nueva) == "b"


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_las_dos_distintas_gana_la_nueva(nueva: str, vieja: str) -> None:
    assert leer_variable({nueva: "a", vieja: "b"}, nueva) == "a"


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_ninguna(nueva: str, vieja: str) -> None:
    assert leer_variable({}, nueva) is None


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_la_variable_nueva_en_blanco_cede_al_alias(nueva: str, vieja: str) -> None:
    assert leer_variable({nueva: "  ", vieja: "b"}, nueva) == "b"
    assert leer_variable({nueva: "  "}, nueva) is None


def test_el_caso_y_el_modo_entrega_leen_con_el_ayudante() -> None:
    assert resolver_ruta(None, {"ARENIA_CASO": "viejo.db"}, "d.db") == Path("viejo.db")
    entorno = {"SILICE_CASO": "nuevo.db", "ARENIA_CASO": "viejo.db"}
    assert resolver_ruta(None, entorno, "d.db") == Path("nuevo.db")
    assert modo_entrega_activo({"ARENIA_MODO_ENTREGA": "1"}) is True
    assert modo_entrega_activo({"SILICE_MODO_ENTREGA": "0", "ARENIA_MODO_ENTREGA": "1"}) is False
    assert modo_entrega_activo({"SILICE_MODO_ENTREGA": "1"}) is True


def _alias_permitidos(version: str) -> bool:
    return Version(version) <= Version(ULTIMA_VERSION_CON_ALIAS)


def test_el_alias_se_retira_despues_de_la_0_6_0() -> None:
    assert _alias_permitidos("0.6.0") and not _alias_permitidos("0.7.0")
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    version = tomllib.loads(texto)["project"]["version"]
    assert _alias_permitidos(version) or ALIAS_ANTERIORES == {}, (
        f"pyproject dice {version}: la 0.7.0 ya no acepta ARENIA_*; vacie ALIAS_ANTERIORES y "
        "retire la nota de alias de los dos manuales"
    )


def test_el_ayudante_solo_usa_la_biblioteca_estandar() -> None:
    arbol = ast.parse((RAIZ / "ui" / "entorno.py").read_text(encoding="utf-8"))
    importados = {
        alias.name.split(".")[0]
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Import)
        for alias in nodo.names
    } | {
        nodo.module.split(".")[0]
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom) and nodo.module
    }
    assert importados <= set(sys.stdlib_module_names) | {"__future__"}
```

`tests/unit/test_config_streamlit.py`:
```python
"""`.streamlit/config.toml` del repositorio (plan 0.6.0, tarea A1; maestro §4.7 y §8; S5 §1.2 y §10.1).

Streamlit 1.62.0 sin `server.address` escucha en todas las interfaces y envia estadisticas de uso
(S5 §1.2). Este archivo lo fija para el camino de desarrollo; S5-2 lo toma como base del archivo
oficial de `{app}\\codigo`.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from streamlit import config as config_streamlit

from adapters.espacio.planos.comun import LIMITE_BYTES

RAIZ = Path(__file__).resolve().parents[2]
CONFIG = RAIZ / ".streamlit" / "config.toml"


def _config() -> dict:
    with CONFIG.open("rb") as archivo:
        return tomllib.load(archivo)


def test_escucha_solo_en_el_bucle_local_y_sin_telemetria() -> None:
    config = _config()
    assert config["server"]["address"] == "127.0.0.1"
    assert config["browser"]["serverAddress"] == "127.0.0.1"
    assert config["browser"]["gatherUsageStats"] is False


def test_cors_y_xsrf_explicitos() -> None:
    config = _config()
    assert config["server"]["enableCORS"] is True
    assert config["server"]["enableXsrfProtection"] is True


def test_el_limite_de_subida_es_el_de_los_planos() -> None:
    """RNF-12: 20 MB, la misma cifra que `adapters/espacio/planos/comun.py:36`."""
    assert _config()["server"]["maxUploadSize"] * 1024 * 1024 == LIMITE_BYTES


def test_los_detalles_de_error_no_llegan_al_navegador() -> None:
    valor = _config()["client"]["showErrorDetails"]
    validos = {opcion.value for opcion in config_streamlit.ShowErrorDetailsConfigOptions}
    assert valor in validos
    assert valor == "none"


def test_streamlit_conoce_cada_opcion_del_archivo() -> None:
    opciones = config_streamlit.get_config_options()
    desconocidas = [
        f"{seccion}.{nombre}"
        for seccion, valores in _config().items()
        for nombre in valores
        if f"{seccion}.{nombre}" not in opciones
    ]
    assert desconocidas == []


def test_la_suite_conserva_el_detalle_de_los_errores_de_apptest() -> None:
    """AppTest lee el `config.toml` del directorio de trabajo; `tests/conftest.py` fija la variable
    `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS`, que manda sobre el archivo, para que un fallo de AppTest
    siga mostrando su mensaje real."""
    assert os.environ["STREAMLIT_CLIENT_SHOW_ERROR_DETAILS"] == "full"
```

`tests/unit/test_nombre_silice.py`:
```python
"""El producto se llama Sílice (plan 0.6.0, tarea A1; maestro S-D7 y P9).

En los documentos vigentes y en `ui/`, el nombre anterior solo sobrevive como nombre historico del
prototipo con la forma exacta de `NOMBRE_HISTORICO`; las variables viejas solo se nombran donde se
declaran como alias. La bitacora, la auditoria y los specs anteriores al 2026-10-11 no se tocan.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

VIGENTES: tuple[str, ...] = (
    "README.md",
    "docs/README.md",
    "docs/ERS.md",
    "docs/manual_usuario.md",
    "docs/manual_tecnico.md",
    "docs/guion_prueba_arenia.md",
    "docs/plan_pruebas.md",
    "docs/calidad_iso25010.md",
    "docs/protocolo_indicador3.md",
    "docs/protocolo_precios.md",
    "docs/protocolo_rnf04.md",
    "scripts/README.md",
    "scripts/seed_demo.py",
    "scripts/meta_prototipo.py",
    "api/main.py",
)
NOMBRE_HISTORICO = "AREN.IA (hoy Sílice)"
_NOMBRE_VIEJO = re.compile(r"AREN\.IA(?! \(hoy Sílice\))")
_VARIABLE_VIEJA = re.compile(r"ARENIA_(?:CASO|MODO_ENTREGA)")
PERMITEN_VARIABLE_VIEJA = frozenset(
    {"ui/entorno.py", "docs/manual_usuario.md", "docs/manual_tecnico.md"}
)
LICENCIA = "Copyright (c) 2026 Eugenio Rijo. Todos los derechos reservados.\n"


def _archivos() -> list[str]:
    de_ui = [ruta.relative_to(RAIZ).as_posix() for ruta in sorted((RAIZ / "ui").rglob("*.py"))]
    return [*VIGENTES, *de_ui]


def _texto(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8")


def test_ningun_archivo_vigente_usa_el_nombre_viejo() -> None:
    encontrados = [
        f"{ruta}:{numero}"
        for ruta in _archivos()
        for numero, linea in enumerate(_texto(ruta).splitlines(), start=1)
        if _NOMBRE_VIEJO.search(linea)
    ]
    assert encontrados == [], f"use «Sílice» o, si es historia, «{NOMBRE_HISTORICO}»"


def test_las_variables_viejas_solo_se_nombran_como_alias() -> None:
    encontrados = [
        ruta
        for ruta in _archivos()
        if ruta not in PERMITEN_VARIABLE_VIEJA and _VARIABLE_VIEJA.search(_texto(ruta))
    ]
    assert encontrados == []


def test_los_manuales_anuncian_el_alias_y_su_retiro() -> None:
    for ruta in ("docs/manual_usuario.md", "docs/manual_tecnico.md"):
        texto = _texto(ruta)
        assert "SILICE_CASO" in texto and "ARENIA_CASO" in texto, ruta
        assert "hasta la 0.6.0" in texto, ruta


def test_la_interfaz_la_api_y_el_readme_se_llaman_silice() -> None:
    from api.main import app
    from ui.app import TITULO_APP

    assert TITULO_APP == "Sílice"
    assert app.title == "Sílice"
    assert _texto("README.md").startswith("# Sílice\n")


def test_el_proyecto_se_llama_silice_y_es_propietario() -> None:
    proyecto = tomllib.loads(_texto("pyproject.toml"))["project"]
    assert proyecto["name"] == "silice"
    assert proyecto["license"] == "LicenseRef-Propietaria"
    assert proyecto["license-files"] == ["LICENSE"]
    assert _texto("LICENSE") == LICENCIA


def test_el_candado_lleva_el_nombre_nuevo() -> None:
    candado = _texto("uv.lock")
    assert 'name = "silice"' in candado
    assert 'name = "apu-system"' not in candado
```

Pruebas del guion (cambian porque cambia el comportamiento **especificado**, no porque fallen):
- `tests/unit/test_guion_prueba_arenia.py:37` → `CASO_ABIERTO = "SILICE_CASO"`; en el docstring (líneas 10,
  12, 15, 124 y 129) `ARENIA_CASO` → `SILICE_CASO`.
- `tests/unit/test_guion_sf.py:76` → `assert "SILICE_CASO=data/prueba_sf.db" in texto`; líneas 84‑85 →
  `if "uv run" in linea or "SILICE_CASO" in linea:` y
  `assert "SILICE_CASO=data/apu.db" not in linea and "--db data/apu.db" not in linea`.

- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_entorno_silice.py tests/unit/test_config_streamlit.py tests/unit/test_nombre_silice.py tests/unit/test_guion_prueba_arenia.py tests/unit/test_guion_sf.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'ui.entorno'`;
`FileNotFoundError: [Errno 2] No such file or directory: '…/.streamlit/config.toml'`;
`test_ningun_archivo_vigente_usa_el_nombre_viejo` FAIL con la lista de líneas;
`AssertionError: assert 'Sistema APU' == 'Sílice'`; `KeyError: 'license'`;
`test_la_preparacion_abre_el_caso_de_prueba` FAIL en `assert 'SILICE_CASO=data/prueba_arenia.db ' in preparacion`.
Commit del rojo (C3 de la meta lo exige anterior a `ui/entorno.py`, `.streamlit/config.toml` y `LICENSE`):
```bash
git add tests/unit/test_entorno_silice.py tests/unit/test_config_streamlit.py tests/unit/test_nombre_silice.py tests/unit/test_guion_prueba_arenia.py tests/unit/test_guion_sf.py
git commit -m "test(ui): nombre Silice, variables SILICE_* con alias y config de Streamlit" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

3.1 `ui/entorno.py` (nuevo):
```python
"""Variables de entorno de Sílice y sus alias anteriores (plan de la 0.6.0, tarea A1).

Durante el prototipo el producto se llamó AREN.IA (hoy Sílice) y sus variables llevaban ese prefijo.
Desde la 0.6.0 se llaman `SILICE_CASO` y `SILICE_MODO_ENTREGA`; `ARENIA_CASO` y
`ARENIA_MODO_ENTREGA` se aceptan como alias solo hasta la 0.6.0 inclusive
(`tests/unit/test_entorno_silice.py` falla cuando `pyproject.toml` pase de esa versión con el alias
todavía declarado).

Regla: manda la variable nueva si tiene texto; si falta o está en blanco, su alias; si ninguna, `None`.
Si las dos tienen valores distintos, gana la nueva. Sin Streamlit ni terceros: lo importan `ui.caso`,
`ui.app` y `tests/conftest.py`.
"""

from __future__ import annotations

from collections.abc import Mapping

VARIABLE_CASO = "SILICE_CASO"
VARIABLE_MODO_ENTREGA = "SILICE_MODO_ENTREGA"

#: Última versión que acepta los nombres anteriores.
ULTIMA_VERSION_CON_ALIAS = "0.6.0"

#: Nombre nuevo -> nombre anterior aceptado como alias hasta `ULTIMA_VERSION_CON_ALIAS`.
ALIAS_ANTERIORES: dict[str, str] = {
    VARIABLE_CASO: "ARENIA_CASO",
    VARIABLE_MODO_ENTREGA: "ARENIA_MODO_ENTREGA",
}


def leer_variable(entorno: Mapping[str, str], nombre: str) -> str | None:
    """El valor de `nombre` en `entorno` o, si falta o está en blanco, el de su alias anterior.

    `None` si ninguna de las dos tiene texto.
    """
    for candidato in (nombre, ALIAS_ANTERIORES.get(nombre)):
        if candidato is None:
            continue
        valor = entorno.get(candidato)
        if valor is not None and valor.strip():
            return valor
    return None
```

3.2 `ui/caso.py`: en el docstring (línea 14) «la variable de entorno `ARENIA_CASO` (el guion CP-07 la usa)» →
«la variable de entorno `SILICE_CASO` (el guion CP-07 la usa; la lee `ui.entorno.leer_variable`)». Agregar
`from ui.entorno import VARIABLE_CASO, leer_variable` debajo de `from core.catalog import …`. Líneas 38‑42:
```python
VARIABLE_RUTA_CASO = VARIABLE_CASO  # nombre que ya importan las pruebas (RF-38)
CLAVE_CASO = "silice_caso_ruta"
CLAVE_RECORRIDO = "silice_recorrido_activo"
CLAVE_PROYECTO = "silice_proyecto_abierto"
CLAVE_ACCION = "silice_accion_pedida"
```
Líneas 50‑55:
```python
def resolver_ruta(guardada: str | None, entorno: Mapping[str, str], por_defecto: str) -> Path:
    """La ruta del caso: la fijada en la sesion; si no, la del entorno; si no, la por defecto."""
    if guardada:
        return Path(guardada)
    del_entorno = (leer_variable(entorno, VARIABLE_RUTA_CASO) or "").strip()
    return Path(del_entorno or por_defecto)
```

3.3 `ui/app.py`: líneas 36‑54 del docstring, reemplazar el párrafo y los dos ejemplos por:
```text
Modo entrega (Sesion P5.1 del prototipo). Con `SILICE_MODO_ENTREGA=1` (exactamente `"1"`) el
menu **omite** la seccion Investigacion —escenarios, similares, simulador y visor 3D—; la seccion
Trabajo queda completa (RF-43). Se omite en vez de plegarse: la barra de herramientas y el resto
del marco no cambian. Las variables se leen con `ui.entorno.leer_variable`.

Uso (con `python -m`: `streamlit run` a secas pone en `sys.path` la carpeta `ui/` y no la raiz
del repositorio, y entonces `import ui` falla; `python -m` agrega el directorio actual)::

    uv sync --extra ui --extra api --extra civil
    uv run python -m streamlit run ui/app.py

Otro caso que `data/apu.db`, y modo entrega, en bash::

    SILICE_CASO=data/otro.db SILICE_MODO_ENTREGA=1 uv run python -m streamlit run ui/app.py

y en PowerShell::

    $env:SILICE_CASO = "data/otro.db"; $env:SILICE_MODO_ENTREGA = "1"
    uv run python -m streamlit run ui/app.py
```
Importar `from ui.entorno import VARIABLE_MODO_ENTREGA, leer_variable` (entre `ui.caso` y `ui.paginas`);
línea 82 → `TITULO_APP = "Sílice"`; borrar la línea 83; líneas 136‑138:
```python
    if entorno is None:
        entorno = os.environ
    return leer_variable(entorno, VARIABLE_MODO_ENTREGA) == VALOR_MODO_ENTREGA
```

3.4 Textos visibles de la interfaz: `ui/paginas/componer.py:537,628,672` («ayuda 1/2/4 de AREN.IA») y
`:335` («ayuda 3 de AREN.IA») → «… de Sílice»; los comentarios y docstrings `:271,307,516` y
`ui/composicion.py:579` igual. `ui/paginas/hoja.py:713` → `prefix="silice_planos_"`. `api/main.py:18` →
`title="Sílice"`; regenerar `docs/api.json` con `uv run python scripts/exportar_openapi.py` (el diff debe
ser solo la línea 4).

3.5 `tests/conftest.py` (líneas 1‑11 y 58‑61): agregar `import os` y
`from ui.entorno import ALIAS_ANTERIORES` (después de `from tests.fixtures …`), y debajo de las importaciones:
```python
#: AppTest lee el `.streamlit/config.toml` del directorio de trabajo, que oculta los detalles de los
#: errores (`client.showErrorDetails = "none"`, S5 §10.1). Las variables `STREAMLIT_*` mandan sobre
#: el archivo: la suite conserva el mensaje completo de cada excepcion de AppTest.
os.environ["STREAMLIT_CLIENT_SHOW_ERROR_DETAILS"] = "full"
```
y la fixture de las líneas 58‑61 pasa a:
```python
@pytest.fixture(autouse=True)
def _sin_variables_de_silice_del_entorno(monkeypatch):
    """Una `SILICE_*` (o su alias `ARENIA_*`) exportada en la terminal no debe desviar la suite."""
    for nombre in (*ALIAS_ANTERIORES, *ALIAS_ANTERIORES.values()):
        monkeypatch.delenv(nombre, raising=False)
```

3.6 `.streamlit/config.toml` (nuevo; valores verificados contra `streamlit/config.py` de Streamlit 1.62.0
en `.worktrees/sf5/.venv`: `ShowErrorDetailsConfigOptions` = `full | stacktrace | type | none`):
```toml
# Configuracion de Streamlit del repositorio (plan 0.6.0, tarea A1; S5 §1.2 y §10.1).
# Sin esto, Streamlit 1.62 escucha en todas las interfaces y envia estadisticas de uso.
# S5-2 lo toma como base del archivo oficial de {app}\codigo (instalador/streamlit_config.toml).

[server]
address = "127.0.0.1"
enableCORS = true
enableXsrfProtection = true
# MB; el mismo limite que los planos (RNF-12, adapters/espacio/planos/comun.py LIMITE_BYTES)
maxUploadSize = 20

[browser]
serverAddress = "127.0.0.1"
gatherUsageStats = false

[client]
showErrorDetails = "none"
```

3.7 Licencia y proyecto. `LICENSE` (nuevo, una línea con salto final):
```text
Copyright (c) 2026 Eugenio Rijo. Todos los derechos reservados.
```
`pyproject.toml` líneas 2‑6:
```toml
name = "silice"
version = "0.1.0"
description = "Sílice: generacion y auditoria de presupuestos con Analisis de Precios Unitarios multidominio"
license = "LicenseRef-Propietaria"
license-files = ["LICENSE"]
readme = "README.md"
requires-python = ">=3.12"
```
(`version` sigue en 0.1.0: la alinea S1‑5, maestro §5). Después: `uv lock` (nunca a mano). `NORMAS.md:171` →
`NORMAS.md  README.md  LICENSE  pyproject.toml  uv.lock  .streamlit/config.toml`.

3.8 Documentos. Primero, a mano, tres líneas donde la regla mecánica dejaría un doble paréntesis:
`docs/manual_usuario.md:54` → `**Dejar lista la aplicación para componer partidas.** Una sola orden siembra`;
`docs/manual_usuario.md:383` → `### 3.7 Componer o editar una partida a mano (UC‑10 y UC‑11)`;
`scripts/seed_demo.py:111-118` →
```python
NOMBRE_PROYECTO = "Sílice: caso de demostracion (linea de agua potable, didactico)"
DESCRIPCION_PROYECTO = (
    "Caso didactico sembrado para que Sílice no abra con el catalogo vacio: tres "
    "partidas ficticias de una linea de agua potable que, entre las tres, ejercitan mano de obra "
    "a jornal y a destajo en la misma partida (decision D9), materiales con desperdicio y equipos "
    "con depreciacion parcial. No representa obra ejecutada."
)
NOMBRE_LISTA = "Lista de referencia del caso de demostracion de Sílice"
```
Luego la regla mecánica sobre el resto (Git Bash, UTF‑8):
```bash
sed -i -E \
  -e 's/ARENIA_(CASO|MODO_ENTREGA)/SILICE_\1/g' \
  -e 's/prototipo (de entrega )?AREN\.IA/prototipo \1AREN.IA (hoy Sílice)/g' \
  -e 's/de AREN\.IA/de Sílice/g' \
  docs/README.md docs/ERS.md docs/manual_usuario.md docs/manual_tecnico.md docs/guion_prueba_arenia.md \
  docs/plan_pruebas.md docs/calidad_iso25010.md docs/protocolo_indicador3.md docs/protocolo_precios.md \
  docs/protocolo_rnf04.md scripts/README.md scripts/meta_prototipo.py ui/composicion.py ui/paginas/componer.py
git grep -n -E 'AREN\.IA' -- docs/README.md docs/ERS.md docs/manual_usuario.md docs/manual_tecnico.md docs/guion_prueba_arenia.md docs/plan_pruebas.md scripts ui api README.md
```
El último `git grep` solo debe mostrar la forma `AREN.IA (hoy Sílice)`. Título del guion (línea 1) →
`# Guion de prueba manual de Sílice (IEEE 829) — Sesión P4.2`. Después del `sed`, agregar la nota de alias
(única mención permitida de `ARENIA_*` en documentos) en `docs/manual_usuario.md`, justo después del párrafo
que termina en la línea 52, y en `docs/manual_tecnico.md`, después de la línea 527:
```markdown
> **Nombres de las variables.** Desde la 0.6.0 se llaman `SILICE_CASO` y `SILICE_MODO_ENTREGA`.
> Los nombres anteriores, `ARENIA_CASO` y `ARENIA_MODO_ENTREGA`, se aceptan como alias solo hasta la
> 0.6.0; si están las dos, manda la nueva (`ui/entorno.py`).
```
`README.md` líneas 1‑6:
```markdown
# Sílice

Sistema de generación y auditoría de Análisis de Precios Unitarios (APU) multidominio, asistido por
modelo BIM‑5D y aprendizaje automático. Nombre del producto desde la versión 0.6.0; el prototipo de
septiembre de 2026 se llamó AREN.IA (hoy Sílice). Trabajo de grado; caso de estudio: obra civil del
sistema de drenaje de una clínica (ejercicio académico ficticio con el contenido y el formato de un APU
venezolano, no una obra ejecutada; ver [docs/linea_base.md](docs/linea_base.md)).
```
y en «Arranque rápido», debajo del bloque de órdenes:
`La interfaz escucha solo en 127.0.0.1 y sin telemetría: lo fija `.streamlit/config.toml`, versionado.`
Comprobación de URLs: `git grep -n -iE 'github\.com/EugenioRRijo/' -- ':!docs/bitacora' ':!docs/auditoria'`
debe quedar vacío o mostrar solo `EugenioRRijo/silice`.

3.9 `docs/bitacora/2026-10-silice-060.md` (nuevo):
```markdown
# Bitácora de la 0.6.0 de Sílice

## T0 · A1 Renombre AREN.IA → Sílice (PR <n>)

- Interfaz y API se llaman «Sílice»; variables `SILICE_CASO` y `SILICE_MODO_ENTREGA`, con
  `ARENIA_*` como alias hasta la 0.6.0 (`ui/entorno.py`; gana la nueva si difieren).
- No se renombran archivos ni identificadores que la bitácora enlaza: `docs/guion_prueba_arenia.md`,
  `data/prueba_arenia.db`, `tests/unit/test_guion_prueba_arenia.py`, `GP‑ARENIA‑001`.
- `.streamlit/config.toml`: 127.0.0.1, sin telemetría, CORS y XSRF explícitos, 20 MB,
  `showErrorDetails = "none"` (valor válido verificado en Streamlit 1.62.0). La suite fija
  `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=full` para no perder el detalle de AppTest.
- Licencia propietaria (P9) adelantada a T0: `LICENSE` y `license` en `pyproject.toml`.
```

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite completa)
Run: `uv run pytest tests/unit/test_entorno_silice.py tests/unit/test_config_streamlit.py tests/unit/test_nombre_silice.py tests/unit/test_guion_prueba_arenia.py tests/unit/test_guion_sf.py tests/unit/test_ui_caso.py tests/unit/test_ui_app.py -v -W error`
Esperado: PASS. Luego `uv run pytest -q -W error`, `uv run ruff check ui tests scripts api`,
`uv run python scripts/meta_datos.py` y `uv run python scripts/guardia_nucleo.py --base origin/main` (los cuatro en 0).
Arranque a mano: `uv run python -m streamlit run ui/app.py` imprime solo la URL local `http://127.0.0.1:8501`
(sin «External URL»); el título de la pestaña es «Sílice».

- [ ] **Paso 5: Commit y PR**
```bash
git add ui/entorno.py ui/caso.py ui/app.py ui/composicion.py ui/paginas/componer.py ui/paginas/hoja.py tests/conftest.py
git commit -m "feat(ui): Silice y variables SILICE_* con alias ARENIA_* hasta la 0.6.0" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add .streamlit/config.toml LICENSE pyproject.toml uv.lock api/main.py docs/api.json NORMAS.md
git commit -m "chore: Streamlit en el bucle local, licencia propietaria y proyecto silice" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add README.md docs/README.md docs/ERS.md docs/manual_usuario.md docs/manual_tecnico.md docs/guion_prueba_arenia.md docs/plan_pruebas.md docs/calidad_iso25010.md docs/protocolo_indicador3.md docs/protocolo_precios.md docs/protocolo_rnf04.md scripts/README.md scripts/seed_demo.py scripts/meta_prototipo.py docs/bitacora/2026-10-silice-060.md
git commit -m "docs: renombre AREN.IA a Silice en los documentos vigentes" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin inc/nombre-silice
gh pr create --base main --head inc/nombre-silice --title "T0-A1: Silice, config de Streamlit y licencia" --body-file -
```
(cuerpo: inventario, regla de nombre, archivos que no se renombran y por qué; última línea, la atribución de
Claude Code). Fusionar con `gh pr merge <n> --merge` con la CI verde.

---

### Tarea A2: PR «dependencias Sílice» (maestro §3, RV‑2, RV‑24)

**Rama:** `inc/060-dependencias` (sale de `origin/main` con A1 fusionada; PR a `main`; RV‑2)   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear (prueba): `tests/unit/test_dependencias_silice.py`
- Modificar: `pyproject.toml:7-24` (con A1 ya aplicado), `uv.lock` (solo con `uv lock`), `README.md:27`,
  `docs/bitacora/2026-10-silice-060.md`

**Decisiones** (con la evidencia de PyPI consultada el 2026‑10‑11):
- Base: `alembic` (S5‑1), `argon2-cffi` y `cryptography` (S3 §4.4: «en el grupo principal»).
- Extras que ya existen y se respetan: `ui`, `api`, `civil`, `planos`, `ml`, `informes`. Se agregan: `bcv`
  (`xlrd`, S1‑R12; entra al instalador básico, RV‑24); `ifc` (`ifctester`); `ia` (`anthropic`, `ollama`,
  `keyring`; S4 §5.5); `anomalias` y `similitud` (S5 §5.2: los dos módulos de `ml` del instalador). `shapely`
  pasa a directa en `planos` (S3 §1.2).
- **`ifctester` va en un extra propio `ifc`, no en `civil`** (RV‑24 lo admite): `ifctester` 0.8.5 depende de
  `flask`, `odfpy`, `pystache`, `xmlschema` y `bcf-client`, y **`bcf-client` declara GPLv3** (clasificador
  «GNU General Public License v3»). Con `ifc` aparte, `civil` sigue liviano y el extra no entra al instalador
  hasta que S3‑0 resuelva la licencia (riesgo ya previsto en S3 §15: «si no, el IDS se reemplaza por
  comprobaciones propias con `ifcopenshell`»). Se fija `>=0.8.5,<0.9`, la serie de `ifcopenshell` 0.8.5 del
  candado (PyPI ya publica 0.9.0).

**Interfaces:**
- Consume: `pyproject.toml` de A1 (`name = "silice"`).
- Produce: extras `bcv`, `ifc`, `ia`, `anomalias`, `similitud`; base con `alembic`, `argon2-cffi`,
  `cryptography`; en la prueba, `DUENOS_DE_TERCEROS: dict[str, tuple[str, ...]]`, `DIFERIDOS: frozenset[str]`,
  `violaciones(ruta_relativa: str, texto: str) -> list[str]` (regla que cumplen S1‑2, S3, S4 y S5‑1).

- [ ] **Paso 1: Escribir la prueba que falla** — `tests/unit/test_dependencias_silice.py`:
```python
"""Dependencias de Sílice, una sola vez (maestro §3, RV-2, RV-24; plan 0.6.0, tarea A2).

Tres cosas: `pyproject.toml` declara lo que necesitan la 0.6.0 a la 1.0.0; todo esta instalado (la CI
corre con `--all-extras`: cero omitidas); y cada tercero nuevo solo lo importa su paquete dueño, con
importacion diferida (dentro de una funcion) si viene de un extra, para que importar el modulo no
falle sin el extra (INV-024, como `ml/normalization` con sentence-transformers). Complementa a
`TERCEROS_POR_ADAPTADOR` de `test_arquitectura.py`, que solo mira `adapters/`; las reglas de cada spec
van en su propio archivo (maestro §3.1).
"""

from __future__ import annotations

import ast
import importlib.util
import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

BASE_SILICE = ("alembic>=1.20", "argon2-cffi>=25.1", "cryptography>=44")
EXTRAS_SILICE: dict[str, tuple[str, ...]] = {
    "bcv": ("xlrd>=2.0",),
    "ifc": ("ifctester>=0.8.5,<0.9",),
    "planos": ("ezdxf>=1.3", "shapely>=2.1"),
    "anomalias": ("scikit-learn>=1.4",),
    "similitud": ("sentence-transformers>=3.0",),
    "ia": ("anthropic>=1.0", "ollama>=0.6", "keyring>=25"),
}

#: Tercero (nombre de importacion) -> carpetas que pueden importarlo. Fuera de ellas, ningun modulo.
DUENOS_DE_TERCEROS: dict[str, tuple[str, ...]] = {
    "xlrd": ("adapters/bcv/",),
    "ifctester": ("adapters/espacio/planos/",),
    "shapely": ("adapters/espacio/planos/",),
    "anthropic": ("asistente/",),
    "ollama": ("asistente/",),
    "keyring": ("asistente/",),
    "argon2": ("seguridad/",),
    "cryptography": ("seguridad/",),
    "alembic": ("migraciones/", "operacion/"),
}
#: Terceros de un extra: se importan dentro de una funcion, nunca al cargar el modulo.
DIFERIDOS = frozenset({"xlrd", "ifctester", "anthropic", "ollama", "keyring"})
#: Carpetas que no son codigo del producto (las pruebas pueden importar cualquier tercero).
_EXCLUIDAS = frozenset({"tests", "data", "docs"})


def _proyecto() -> dict:
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def importaciones(texto: str) -> list[tuple[str, bool]]:
    """(paquete de primer nivel, diferida) de cada importacion absoluta del modulo."""
    arbol = ast.parse(texto)
    en_funcion: set[int] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            en_funcion.update(id(hijo) for hijo in ast.walk(nodo) if hijo is not nodo)
    resultado: list[tuple[str, bool]] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            nombres = [nodo.module]
        else:
            continue
        resultado.extend((nombre.split(".")[0], id(nodo) in en_funcion) for nombre in nombres)
    return resultado


def violaciones(ruta_relativa: str, texto: str) -> list[str]:
    """Las importaciones de terceros de Sílice que `ruta_relativa` no puede hacer."""
    encontradas: list[str] = []
    for tercero, diferida in importaciones(texto):
        duenos = DUENOS_DE_TERCEROS.get(tercero)
        if duenos is None:
            continue
        if not ruta_relativa.startswith(duenos):
            encontradas.append(f"{ruta_relativa}: {tercero} fuera de {', '.join(duenos)}")
        elif tercero in DIFERIDOS and not diferida:
            encontradas.append(
                f"{ruta_relativa}: {tercero} se importa al cargar el modulo "
                "(debe ir dentro de una funcion)"
            )
    return encontradas


def _modulos_del_producto() -> list[Path]:
    return sorted(
        archivo
        for carpeta in RAIZ.iterdir()
        if carpeta.is_dir() and not carpeta.name.startswith(".") and carpeta.name not in _EXCLUIDAS
        for archivo in carpeta.rglob("*.py")
    )


def test_el_pyproject_declara_las_dependencias_de_silice() -> None:
    proyecto = _proyecto()
    assert set(BASE_SILICE) <= set(proyecto["dependencies"])
    extras = proyecto["optional-dependencies"]
    for extra, requisitos in EXTRAS_SILICE.items():
        assert set(requisitos) <= set(extras[extra]), extra


def test_ml_reune_anomalias_similitud_y_xgboost() -> None:
    extras = _proyecto()["optional-dependencies"]
    esperado = set(extras["anomalias"]) | set(extras["similitud"]) | {"xgboost>=2.0"}
    assert set(extras["ml"]) == esperado


def test_ifctester_no_entra_en_civil() -> None:
    """`bcf-client` (de ifctester) declara GPLv3: `civil` va al instalador basico y no lo arrastra."""
    assert not any(r.startswith("ifctester") for r in _proyecto()["optional-dependencies"]["civil"])


@pytest.mark.parametrize("modulo", sorted(DUENOS_DE_TERCEROS))
def test_cada_dependencia_nueva_esta_instalada(modulo: str) -> None:
    assert importlib.util.find_spec(modulo) is not None, (
        f"falta {modulo}: unset VIRTUAL_ENV; uv sync --all-extras"
    )


def test_ifctester_es_de_la_misma_serie_que_ifcopenshell() -> None:
    def serie(distribucion: str) -> list[str]:
        return version(distribucion).split(".")[:2]

    assert serie("ifctester") == serie("ifcopenshell")


def test_ningun_modulo_importa_un_tercero_de_silice_fuera_de_su_dueno() -> None:
    encontradas = [
        violacion
        for archivo in _modulos_del_producto()
        for violacion in violaciones(
            archivo.relative_to(RAIZ).as_posix(), archivo.read_text(encoding="utf-8")
        )
    ]
    assert encontradas == []


def test_la_guardia_de_terceros_ve_cada_caso() -> None:
    assert violaciones("ui/x.py", "import xlrd\n") == ["ui/x.py: xlrd fuera de adapters/bcv/"]
    assert violaciones("adapters/bcv/libro.py", "import xlrd\n") == [
        "adapters/bcv/libro.py: xlrd se importa al cargar el modulo (debe ir dentro de una funcion)"
    ]
    assert violaciones("adapters/bcv/libro.py", "def leer():\n    import xlrd\n") == []
    assert violaciones(
        "seguridad/firma.py", "from cryptography.hazmat.primitives.asymmetric import ed25519\n"
    ) == []
    assert violaciones("api/main.py", "from cryptography.fernet import Fernet\n") == [
        "api/main.py: cryptography fuera de seguridad/"
    ]
    assert violaciones("ui/x.py", "import pandas\n") == []
```

- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_dependencias_silice.py -v -W error`
Esperado: FAIL en `test_el_pyproject_declara_las_dependencias_de_silice` (`assert {...} <= {...}`), `KeyError: 'anomalias'`,
`KeyError: 'civil'` no (pasa), `test_cada_dependencia_nueva_esta_instalada[xlrd]` FAIL «falta xlrd»,
`PackageNotFoundError: ifctester`. Las dos de la guardia pasan ya (no hay código que las viole): son la regla
que heredan S1‑2, S3, S4 y S5‑1.
```bash
git add tests/unit/test_dependencias_silice.py
git commit -m "test(deps): dependencias de Silice y duenos de cada tercero" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima** — `pyproject.toml`, desde `dependencies` hasta el fin de los extras:
```toml
dependencies = [
    "sqlalchemy>=2.0",
    "pandas>=2.2",
    "pydantic>=2.0",
    "openpyxl>=3.1",
    "alembic>=1.20",      # S5-1 (0.6.0): migraciones del caso y de la instalacion (RV-3)
    "argon2-cffi>=25.1",  # S3 (0.8.0): contrasenas y secretos de seguridad/ (maestro 4.4)
    "cryptography>=44",   # S3 (0.8.0): firma Ed25519 y AES-GCM de seguridad/ (maestro 4.4)
]

# Extras por capa (uv sync --extra <x>; la CI instala todos con --all-extras: cero omitidas).
#   ui, api, civil (IFC), planos (DXF y geometria del plano), informes (PDF)
#   anomalias (scikit-learn) y similitud (sentence-transformers): los dos modulos de ml del
#     instalador (S5 7.2); ml = los dos + xgboost, para la CI y la investigacion
#   bcv  (S1: .xls del BCV; entra al instalador basico, RV-24)
#   ifc  (S3: IDS con ifctester; fuera del instalador mientras S3-0 no resuelva la GPLv3 de bcf-client)
#   ia   (S4: Claude, Ollama y el almacen de claves del sistema operativo)
[project.optional-dependencies]
ui = ["streamlit>=1.62"]
api = ["fastapi>=0.110", "uvicorn>=0.29"]
civil = ["ifcopenshell>=0.8"]
ifc = ["ifctester>=0.8.5,<0.9"]
planos = ["ezdxf>=1.3", "shapely>=2.1"]
anomalias = ["scikit-learn>=1.4"]
similitud = ["sentence-transformers>=3.0"]
ml = ["scikit-learn>=1.4", "sentence-transformers>=3.0", "xgboost>=2.0"]
informes = ["reportlab>=4.0", "matplotlib>=3.8"]
bcv = ["xlrd>=2.0"]
ia = ["anthropic>=1.0", "ollama>=0.6", "keyring>=25"]
```
(`ml` repite sus dos piezas: con `package = false` no se usa un extra que se cite a sí mismo, y
`test_ml_reune_anomalias_similitud_y_xgboost` impide que diverjan.) Luego:
```bash
uv lock
unset VIRTUAL_ENV; uv sync --all-extras
git diff origin/main -- uv.lock | grep -E '^\+name = '
```
Ante un conflicto del candado al recibir `main`: `git checkout --theirs uv.lock && uv lock`, nunca a mano.
`README.md:27` → comentario de `uv sync --all-extras`: `(ui, api, civil, ifc, planos, ml, anomalias, similitud, informes, bcv, ia)`.

Licencias: para cada paquete nuevo del candado (la lista del `grep` de arriba), correr
```bash
uv run python - <<'EOF'
import importlib.metadata as m, subprocess
nuevos = [l.split('"')[1] for l in subprocess.run(["git", "diff", "origin/main", "--", "uv.lock"], capture_output=True, text=True).stdout.splitlines() if l.startswith('+name = ')]
for d in nuevos:
    md = m.metadata(d)
    clasif = "; ".join(c.split(" :: ")[-1] for c in (md.get_all("Classifier") or []) if c.startswith("License"))
    print(f"| {d} | {m.version(d)} | {md.get('License-Expression') or md.get('License') or clasif} |")
EOF
```
y pegar su salida literal en la bitácora y en el cuerpo del PR, debajo de esta tabla de las directas (PyPI,
2026‑10‑11):
```markdown
## T0 · A2 Dependencias Sílice (PR <n>)

| Paquete | Requisito | Licencia | Extra |
|---|---|---|---|
| alembic | >=1.20 | MIT | base |
| argon2-cffi | >=25.1 | MIT | base |
| cryptography | >=44 | Apache-2.0 OR BSD-3-Clause | base |
| xlrd | >=2.0 | BSD (clasificador «BSD License») | bcv |
| shapely | >=2.1 | BSD-3-Clause (GEOS: LGPL-2.1) | planos |
| ifctester | >=0.8.5,<0.9 | LGPL-3.0-or-later (clasificador) | ifc |
| bcf-client (de ifctester) | transitiva | **GPL-3.0 (clasificador): bloquea `ifc` en el instalador hasta S3-0** | ifc |
| odfpy (de ifctester) | transitiva | Apache / GPL / LGPL (tres clasificadores) | ifc |
| pystache (de ifctester) | transitiva | MIT | ifc |
| anthropic | >=1.0 | MIT | ia |
| ollama | >=0.6 | MIT | ia |
| keyring | >=25 | MIT; guarda por usuario de Windows y no viaja en los respaldos (maestro §3) | ia |

Transitivas nuevas (salida literal del comando de licencias): …
```
(la línea «Transitivas nuevas» se sustituye por la salida del comando, sin editarla). Si `uv lock` no
resolviera `ifctester` con `ifcopenshell` 0.8.5, se quita el extra `ifc` de este PR, se anota aquí con el
mensaje de `uv` y pasa a S3‑0; el resto del PR sigue.

- [ ] **Paso 4: Correrla y ver el verde**
Run: `uv run pytest tests/unit/test_dependencias_silice.py tests/unit/test_arquitectura.py -v -W error` → PASS;
luego `uv run pytest -q -W error`, `uv run ruff check tests/unit/test_dependencias_silice.py`,
`uv run python scripts/guardia_nucleo.py --base origin/main`.

- [ ] **Paso 5: Commit y PR**
```bash
git add pyproject.toml uv.lock README.md docs/bitacora/2026-10-silice-060.md
git commit -m "build(deps): dependencias de Silice 0.6.0 a 1.0.0 con licencias verificadas" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin inc/060-dependencias
gh pr create --base main --head inc/060-dependencias --title "T0-A2: dependencias Silice" --body-file -
```
(cuerpo: la tabla de licencias completa y el aviso de `bcf-client`). Fusionar con `--merge`.

---

### Tarea A3: Guardia de red única y modelo de similitud sin red

**Rama:** `inc/060-guardia-red` (sale de `origin/main` con A2 fusionada; PR a `main`; RV‑2)   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `scripts/descargar_modelo.py`
- Crear (pruebas): `tests/unit/test_guardia_red.py`, `tests/unit/test_sin_omisiones.py`,
  `tests/unit/test_descargar_modelo.py`, `tests/unit/test_ci_silice.py`
- Modificar: `tests/conftest.py` (cabecera e importaciones; fixture nueva al final);
  `tests/unit/test_normalizacion.py:9-13,48-53`; `tests/integration/test_api.py:466-478`;
  `.github/workflows/ci.yml:76-109`; `scripts/verificar_omitidas.py:3-6`; `scripts/README.md` (fila nueva);
  `README.md:25-30`; `docs/bitacora/2026-10-silice-060.md`

**Cómo se omite hoy** (verificado): `tests/unit/test_normalizacion.py:53` hace `pytest.skip` si el modelo no
carga (`OSError`) y `tests/integration/test_api.py:478` copia el mismo criterio. La CI lo vuelve FALLA solo
después, con `scripts/verificar_omitidas.py`. Se eliminan las dos omisiones: sin el modelo en caché, la prueba
**falla** con la orden que lo arregla. Los `pytest.importorskip` de extras (14 archivos) siguen: con
`--all-extras` no omiten y `verificar_omitidas.py` vigila que así sea.

**Interfaces:**
- Consume: `ml.normalization.MODELO_POR_DEFECTO = "paraphrase-multilingual-MiniLM-L12-v2"`; `ui.entorno.ALIAS_ANTERIORES`.
- Produce: en `tests/conftest.py`: `DESTINOS_PERMITIDOS: frozenset[str]`,
  `class ConexionSalienteBloqueada(OSError)`, `INTENTOS_BLOQUEADOS: list[str]`,
  `destino_permitido(familia: int, direccion: object) -> bool`,
  `veredicto_de_la_guardia(intentos: Sequence[str]) -> str | None`, fixture `_guardia_de_red`
  (`scope="session"`, `autouse=True`; su nombre lo busca C7 de la meta); `scripts.descargar_modelo.descargar(nombre: str = MODELO_POR_DEFECTO, cargar: Callable[[str], object] | None = None) -> object`;
  `scripts.descargar_modelo.main(argv: list[str] | None = None) -> int`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

`tests/unit/test_guardia_red.py`:
```python
"""Guardia de red unica de la suite (maestro §6.3, RV-17; `tests/conftest.py`).

Solo admite conexiones a 127.0.0.1 y ::1. Una conexion afuera falla con un error que lo dice, y
queda registrada: si una prueba se traga el error con `except OSError`, la sesion falla igual al
cerrar. Limite declarado: no vigila los subprocesos ni la resolucion de nombres (`getaddrinfo`).
"""

from __future__ import annotations

import _socket
import socket

import pytest

from tests.conftest import (
    DESTINOS_PERMITIDOS,
    INTENTOS_BLOQUEADOS,
    ConexionSalienteBloqueada,
    destino_permitido,
    veredicto_de_la_guardia,
)


def test_la_guardia_esta_puesta_durante_toda_la_sesion() -> None:
    assert socket.socket.connect is not _socket.socket.connect
    assert socket.socket.connect_ex is not _socket.socket.connect_ex


def test_solo_se_admiten_el_bucle_local_ipv4_e_ipv6() -> None:
    assert DESTINOS_PERMITIDOS == frozenset({"127.0.0.1", "::1", "localhost"})


def test_una_conexion_fuera_del_equipo_falla_con_un_error_claro() -> None:
    antes = len(INTENTOS_BLOQUEADOS)
    try:
        with pytest.raises(
            ConexionSalienteBloqueada, match=r"203\.0\.113\.1.*solo admite 127\.0\.0\.1 y ::1"
        ):
            socket.create_connection(("203.0.113.1", 80), timeout=1)
        assert INTENTOS_BLOQUEADOS[antes:] == ["('203.0.113.1', 80)"]
    finally:
        del INTENTOS_BLOQUEADOS[antes:]


def test_una_conexion_al_bucle_local_pasa() -> None:
    with socket.create_server(("127.0.0.1", 0)) as servidor:
        puerto = servidor.getsockname()[1]
        with socket.create_connection(("127.0.0.1", puerto), timeout=5) as cliente:
            conexion, _ = servidor.accept()
            with conexion:
                cliente.sendall(b"ok")
                assert conexion.recv(2) == b"ok"


def test_un_intento_tragado_queda_registrado_y_falla_la_sesion() -> None:
    antes = len(INTENTOS_BLOQUEADOS)
    try:
        try:
            socket.create_connection(("198.51.100.7", 443), timeout=1)
        except OSError:
            pass  # una prueba descuidada que se traga el error
        assert INTENTOS_BLOQUEADOS[antes:] == ["('198.51.100.7', 443)"]
        mensaje = veredicto_de_la_guardia(INTENTOS_BLOQUEADOS[antes:])
        assert mensaje is not None and "198.51.100.7" in mensaje
    finally:
        del INTENTOS_BLOQUEADOS[antes:]
    assert veredicto_de_la_guardia([]) is None


@pytest.mark.parametrize(
    ("familia", "direccion", "permitido"),
    [
        (socket.AF_INET, ("127.0.0.1", 80), True),
        (socket.AF_INET6, ("::1", 80, 0, 0), True),
        (socket.AF_INET6, ("::1%1", 80, 0, 1), True),
        (socket.AF_INET, ("localhost", 80), True),
        (socket.AF_INET, ("203.0.113.1", 80), False),
        (socket.AF_INET, ("127.0.0.2", 80), False),
        (socket.AF_INET, ("ejemplo.com", 443), False),
        (socket.AF_INET6, ("2001:db8::1", 443, 0, 0), False),
        (socket.AF_INET6, ("fe80::1%eth0", 80, 0, 0), False),
        (socket.AF_INET6, ("::ffff:127.0.0.1", 80, 0, 0), False),
    ],
)
def test_destinos(familia: int, direccion: tuple, permitido: bool) -> None:
    assert destino_permitido(familia, direccion) is permitido
```

`tests/unit/test_sin_omisiones.py`:
```python
"""Ninguna prueba se omite por su cuenta (maestro §6.2 y §6.3; plan 0.6.0, tarea A3).

`pytest.skip`, `pytest.mark.skip` y `pytest.mark.skipif` quedan prohibidos en `tests/`: lo que falte
debe fallar con la orden que lo arregla. `pytest.importorskip` de un extra sigue permitido porque la
CI instala todos los extras y `scripts/verificar_omitidas.py` falla ante cualquier omitida.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
_FORMAS = frozenset({"pytest.skip", "pytest.mark.skip", "pytest.mark.skipif"})


def omisiones(archivo: Path) -> list[int]:
    """Lineas de `archivo` con una forma de omitir de `_FORMAS`."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    return sorted(
        {
            nodo.lineno
            for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.Attribute) and ast.unparse(nodo) in _FORMAS
        }
    )


def test_el_detector_ve_cada_forma_de_omitir(tmp_path: Path) -> None:
    archivo = tmp_path / "test_x.py"
    archivo.write_text(
        "import pytest\n"
        "@pytest.mark.skipif(True, reason='x')\n"
        "def test_a():\n"
        "    pytest.skip('y')\n"
        "@pytest.mark.skip\n"
        "def test_b():\n"
        "    pytest.importorskip('z')\n",
        encoding="utf-8",
    )
    assert omisiones(archivo) == [2, 4, 5]


def test_ninguna_prueba_se_omite_por_su_cuenta() -> None:
    encontradas = {
        archivo.relative_to(RAIZ).as_posix(): lineas
        for archivo in sorted((RAIZ / "tests").rglob("*.py"))
        if (lineas := omisiones(archivo))
    }
    assert encontradas == {}
```

`tests/unit/test_descargar_modelo.py`:
```python
"""`scripts/descargar_modelo.py` pide el modelo que usa la normalizacion (I2), y solo ese."""

from __future__ import annotations

from ml.normalization import MODELO_POR_DEFECTO
from scripts.descargar_modelo import descargar


def test_descarga_el_modelo_de_la_normalizacion() -> None:
    pedidos: list[str] = []
    descargar(cargar=pedidos.append)
    assert pedidos == [MODELO_POR_DEFECTO]
```

`tests/unit/test_ci_silice.py`:
```python
"""La CI corre la suite sin red y descarga el modelo antes (maestro §6.3, RV-17; S5 §11.1)."""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
FLUJO = RAIZ / ".github" / "workflows" / "ci.yml"


def _pruebas() -> dict:
    return yaml.safe_load(FLUJO.read_text(encoding="utf-8"))["jobs"]["pruebas"]


def _indice(trabajo: dict, fragmento: str) -> int:
    for indice, paso in enumerate(trabajo["steps"]):
        if fragmento in str(paso.get("run", "")):
            return indice
    raise AssertionError(f"ningun paso corre {fragmento!r}")


def test_la_suite_corre_sin_red() -> None:
    assert _pruebas()["env"]["HF_HUB_OFFLINE"] == "1"


def test_el_modelo_se_descarga_antes_de_pytest_y_con_cache() -> None:
    trabajo = _pruebas()
    descarga = _indice(trabajo, "scripts/descargar_modelo.py")
    assert descarga < _indice(trabajo, "pytest -W error")
    assert trabajo["steps"][descarga]["env"]["HF_HUB_OFFLINE"] == "0"
    cache = next(
        indice
        for indice, paso in enumerate(trabajo["steps"])
        if str(paso.get("uses", "")).startswith("actions/cache")
    )
    assert cache < descarga
```

- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_guardia_red.py tests/unit/test_sin_omisiones.py tests/unit/test_descargar_modelo.py tests/unit/test_ci_silice.py -v -W error`
Esperado: `ImportError: cannot import name 'DESTINOS_PERMITIDOS' from 'tests.conftest'`;
`ModuleNotFoundError: No module named 'scripts.descargar_modelo'`;
`test_ninguna_prueba_se_omite_por_su_cuenta` FAIL con
`{'tests/integration/test_api.py': [478], 'tests/unit/test_normalizacion.py': [53]}`;
`KeyError: 'env'` en `test_la_suite_corre_sin_red`.
```bash
git add tests/unit/test_guardia_red.py tests/unit/test_sin_omisiones.py tests/unit/test_descargar_modelo.py tests/unit/test_ci_silice.py
git commit -m "test(suite): guardia de red unica, cero omisiones y modelo antes de pytest" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

3.1 `tests/conftest.py`. Docstring del módulo: agregar el párrafo «Tres guardias de sesión: la base real
intacta, las variables de Sílice del entorno fuera y la guardia de red única (maestro §6.3, RV‑17): ninguna
prueba se conecta fuera de 127.0.0.1 y ::1.» Importaciones: `import os`, `import socket`,
`from collections.abc import Callable, Iterator, Sequence`. Debajo de la línea de `STREAMLIT_…` de A1:
```python
#: La suite corre sin red: Hugging Face lee esta variable al importarse y la guardia de red
#: bloquearia cualquier descarga. El modelo se baja antes, una vez, con `scripts/descargar_modelo.py`.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

#: Destinos a los que una prueba puede conectarse (maestro §6.3, RV-17): el bucle local.
DESTINOS_PERMITIDOS = frozenset({"127.0.0.1", "::1", "localhost"})

#: Cada conexion bloqueada en la sesion, como `repr` de su direccion. Si una prueba se traga el
#: error, la sesion falla igual al cerrar (`veredicto_de_la_guardia`).
INTENTOS_BLOQUEADOS: list[str] = []


class ConexionSalienteBloqueada(OSError):
    """Una prueba intento conectarse fuera del equipo. Es `OSError`, como la red ausente real."""


def destino_permitido(familia: int, direccion: object) -> bool:
    """True si el destino es el bucle local; las familias que no son IP no salen del equipo."""
    if familia not in (socket.AF_INET, socket.AF_INET6):
        return True
    anfitrion = direccion[0] if isinstance(direccion, tuple) and direccion else direccion
    return str(anfitrion).split("%", 1)[0] in DESTINOS_PERMITIDOS


def veredicto_de_la_guardia(intentos: Sequence[str]) -> str | None:
    """El mensaje de fallo de la sesion si hubo intentos bloqueados; `None` si no hubo ninguno."""
    if not intentos:
        return None
    return (
        f"guardia de red: la suite intento {len(intentos)} conexion(es) fuera del equipo: "
        + ", ".join(intentos[:5])
    )


def _vigilar(original: Callable) -> Callable:
    def conectar(sock: socket.socket, direccion: object):
        if not destino_permitido(sock.family, direccion):
            INTENTOS_BLOQUEADOS.append(repr(direccion))
            raise ConexionSalienteBloqueada(
                f"guardia de red (tests/conftest.py): conexion bloqueada hacia {direccion!r}; "
                "la suite solo admite 127.0.0.1 y ::1 (RV-17)"
            )
        return original(sock, direccion)

    return conectar
```
y al final del archivo:
```python
@pytest.fixture(scope="session", autouse=True)
def _guardia_de_red() -> Iterator[None]:
    """Guardia de red unica (RV-17): toda la sesion solo conecta con el bucle local."""
    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(socket.socket, "connect", _vigilar(socket.socket.connect))
        parche.setattr(socket.socket, "connect_ex", _vigilar(socket.socket.connect_ex))
        yield
    mensaje = veredicto_de_la_guardia(INTENTOS_BLOQUEADOS)
    if mensaje is not None:
        pytest.fail(mensaje, pytrace=False)
```

3.2 `tests/unit/test_normalizacion.py`: líneas 9‑13 del docstring → «… El modelo de similitud es una
precondición del UC‑03 («el modelo está disponible localmente», docs/ERS.md): la suite corre sin red
(`HF_HUB_OFFLINE=1`, guardia de `tests/conftest.py`) y, si el modelo no está en la caché, la prueba falla con la
orden que lo descarga; nunca se omite.» Líneas 48‑53:
```python
@pytest.fixture(scope="module")
def normalizador():
    from ml.normalization import NormalizadorPartidas

    try:
        return NormalizadorPartidas(CATALOGO)
    except OSError as exc:  # el modelo no esta en la cache local y la suite corre sin red
        pytest.fail(
            f"el modelo de similitud no esta en la cache local ({exc}); la suite corre sin red "
            "(HF_HUB_OFFLINE=1): descarguelo una vez con `uv run python scripts/descargar_modelo.py`",
            pytrace=False,
        )
```
`tests/integration/test_api.py:474-478`, mismo criterio:
```python
    try:
        NormalizadorPartidas({})
    except OSError as error:  # mismo criterio que tests/unit/test_normalizacion.py
        pytest.fail(
            f"el modelo de similitud no esta en la cache local ({error}): "
            "uv run python scripts/descargar_modelo.py",
            pytrace=False,
        )
```

3.3 `scripts/descargar_modelo.py` (nuevo):
```python
"""Descarga el modelo de similitud de partidas (I2) a la cache local de Hugging Face.

La suite corre sin red (`HF_HUB_OFFLINE=1` y la guardia de `tests/conftest.py`; maestro §6.3, RV-17):
este es el unico paso que descarga, una vez por equipo, antes de pytest. La CI lo corre en su propio
paso, con cache. En el producto, el instalador completo trae el modelo (S5 §10.2).

Uso: `uv run python scripts/descargar_modelo.py`.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from ml.normalization import MODELO_POR_DEFECTO  # noqa: E402


def descargar(
    nombre: str = MODELO_POR_DEFECTO, cargar: Callable[[str], object] | None = None
) -> object:
    """Carga (y, si falta, descarga) el modelo `nombre`. `cargar` reemplaza a SentenceTransformer."""
    if cargar is None:
        # Hugging Face lee la variable al importarse: se fija antes de importar.
        os.environ["HF_HUB_OFFLINE"] = "0"
        from sentence_transformers import SentenceTransformer

        cargar = SentenceTransformer
    return cargar(nombre)


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    descargar()
    print(f"modelo de similitud en la cache local: {MODELO_POR_DEFECTO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
Fila en `scripts/README.md`, sección «Guardias de la CI»:
`| `descargar_modelo.py` | descarga una vez el modelo de similitud a la caché de Hugging Face; la suite corre sin red (`HF_HUB_OFFLINE=1`) y la CI lo corre antes de pytest | CI · RV‑17 |`.
`scripts/verificar_omitidas.py:3-6` → «Varios archivos de prueba usan `pytest.importorskip` (ifcopenshell,
scikit‑learn, sentence‑transformers, reportlab). Si en la CI faltara un extra, esas pruebas desaparecerían en
silencio y la corrida saldría verde: este script convierte "0 omitidas" en una condición del pipeline.»
`README.md`, bloque «Arranque rápido», después de `uv sync --all-extras`:
`uv run python scripts/descargar_modelo.py      # una vez: modelo de similitud (la suite corre sin red)`.

3.4 `.github/workflows/ci.yml`, trabajo `pruebas` (líneas 76‑109): agregar debajo de `runs-on`
```yaml
    env:
      HF_HUB_OFFLINE: "1" # la suite corre sin red (maestro 6.3, RV-17); solo baja el paso del modelo
```
y, entre «Entorno completo (todos los extras)» y «Suite (pytest -W error)»:
```yaml
      - name: Modelo de similitud (antes de pytest; con la cache no baja nada)
        env:
          HF_HUB_OFFLINE: "0"
        run: uv run --no-sync python scripts/descargar_modelo.py
```

3.5 Bitácora, sección nueva `## T0 · A3 Guardia de red y modelo sin red (PR <n>)`: qué bloquea, el registro
de intentos tragados, los dos `pytest.skip` eliminados, y los **límites declarados**: no vigila subprocesos
(`tests/fixtures/subproceso.py`) ni `getaddrinfo`; la prueba de humo del instalador (S5 §11.2) cubre lo
primero con el cortafuegos de salida.

- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run python scripts/descargar_modelo.py` y luego
`uv run pytest tests/unit/test_guardia_red.py tests/unit/test_sin_omisiones.py tests/unit/test_descargar_modelo.py tests/unit/test_ci_silice.py tests/unit/test_normalizacion.py tests/integration/test_api.py -v -W error` → PASS.
Suite: `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml` y
`uv run python scripts/verificar_omitidas.py reporte-pruebas.xml` → «0 omitidas». Con la caché del modelo
renombrada, `test_normalizacion.py` debe FALLAR (no omitirse) con la orden de descarga. `uv run ruff check tests scripts`.

- [ ] **Paso 5: Commit y PR**
```bash
git add tests/conftest.py tests/unit/test_normalizacion.py tests/integration/test_api.py scripts/descargar_modelo.py scripts/verificar_omitidas.py scripts/README.md README.md .github/workflows/ci.yml docs/bitacora/2026-10-silice-060.md
git commit -m "test(suite): guardia de red unica y modelo de similitud descargado antes de pytest" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin inc/060-guardia-red
gh pr create --base main --head inc/060-guardia-red --title "T0-A3: guardia de red unica y suite sin red" --body-file -
```
Fusionar con `--merge`; la CI de este PR es la primera que corre con `HF_HUB_OFFLINE=1`.

---

### Tarea A4: Meta única `scripts/meta_silice.py --version X --hasta FASE`

**Rama:** `inc/060-meta` (sale de `origin/main` con A3 fusionada; PR a `main`; RV‑2)   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `scripts/meta_silice.py`
- Crear (prueba): `tests/unit/test_meta_silice.py`
- Modificar: `tests/unit/test_ci_silice.py` (una prueba nueva); `.github/workflows/ci.yml:84-85` (checkout con
  historia) y un paso nuevo tras «Medición de RNF‑11»; `scripts/README.md` (fila en «Metas de sprint»);
  `docs/bitacora/2026-10-silice-060.md`

**Bloque de regresión literal** (maestro §6.3; S5 §12; S1 §9.2), localizado con `grep` el 2026‑10‑11:

| Punto | Prueba (nodeid) |
|---|---|
| cinco APU a ± 0,01 | `tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base` (5 casos) y el oráculo `tests/unit/test_linea_base.py` |
| 7 de 7 | `tests/integration/test_auditoria_7_de_7.py` |
| R4 de 3/4 pulg | `tests/unit/test_verification.py::test_r4_marca_3_4_pulg_y_no_marca_pvc` |
| TI‑001 total, PU y PE 28 586,76 USD Día 6 | `tests/unit/test_caso_ti001.py::test_total_y_cierre_de_la_curva`, `::test_precios_unitarios`, `::test_punto_de_equilibrio` (líneas 82‑84: `28586.76`, `"Dia 6"`) |
| dos huellas de RNF‑04 | `tests/unit/test_huellas_rnf04.py` (`HUELLA_PANTALLA`, `HUELLA_CONTENIDO_LIBRO`) |
| cuatro hojas de `exportar_excel` | `tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas`, `tests/integration/test_composicion_extremo_a_extremo.py::test_exportar_excel_escribe_las_cuatro_hojas_con_la_modalidad` |

**Interfaces:**
- Consume: de `scripts.meta_alpha`: `Estado`, `Fila`, `_filas_a_json`, `render_tabla`; de `scripts.meta_sf`:
  `_correr_pytest(ids: list[str]) -> str`, `_existe(nodeid: str) -> bool`, `_patron_definicion(prefijo: str, numero: int) -> str`,
  `combinar_s4(resultados) -> tuple[Estado, str]`, `contar_resultados(salida, grupos)`, `evaluar_s8_regresion(grupos, ausentes)`;
  de `scripts.verificar_omitidas`: `omitidas(xml_texto: str) -> list[str]`, `SinEvidenciaError`; de A3: la
  fixture `_guardia_de_red` y `tests/unit/test_guardia_red.py`.
- Produce (lo que extienden S5‑1 y S1): `FASES: dict[str, tuple[str, ...]]`; `REGRESION: dict[str, tuple[str, ...]]`;
  `ARCHIVOS_REGRESION: tuple[str, ...]`; `BASE_REGRESION = "v0.5.0"`; dataclasses
  `ParTDD(prueba: str, implementacion: str, fase: str)`,
  `CifraDeTiempo(nombre: str, ruta: str, clave: str, orden: str, fase: str)`,
  `Contexto(version: str, fases: tuple[str, ...], junit: Path | None, partes: tuple[Parte, ...])`,
  `Comprobacion(codigo: str, titulo: str, fase: str, evaluar: Callable[[Contexto], tuple[Estado, str]])`,
  `Parte(nombre: str, requisitos: Mapping[str, tuple[str, ...]] = {}, pares_tdd: tuple[ParTDD, ...] = (), cifras: tuple[CifraDeTiempo, ...] = (), comprobaciones: tuple[Comprobacion, ...] = ())`;
  `PARTE_T0: Parte`; `fases_hasta(version: str, hasta: str) -> tuple[str, ...]`; `partes() -> tuple[Parte, ...]`
  (descubre `scripts/meta_silice_<parte>.py`, cada uno con `PARTE = Parte(...)`); `validar_partes(todas) -> None`;
  `requisitos_exigidos(partes_, fases) -> tuple[str, ...]`; `evaluar_requisitos`, `evaluar_omitidas`,
  `evaluar_orden_tdd`, `evaluar_diff_vacio`, `evaluar_regresion`, `evaluar_cifras`, `guardia_declarada`,
  `evaluar_guardia`, `orden_de_par(par: ParTDD) -> bool | None`, `evaluar(version, hasta, junit) -> list[Fila]`,
  `main(argv: list[str] | None = None) -> int`. **Cómo extiende cada parte** (sin editar este archivo; nombres
  cotejados con B y C): S5‑1 crea `scripts/meta_silice_s5.py` (B, Tarea 7) con
  `PARTE = Parte("S5-1 Alembic, preparar_base y respaldo", requisitos={"S5-1": ("RF-96", "RNF-20")}, pares_tdd=PARES_S5, comprobaciones=(Comprobacion("S5-M3", "Base de prueba 0.5.0 de su etiqueta, con ficha", "S5-1", _base_050),))`;
  S1‑0 crea `scripts/meta_silice_s1.py` (C, Tarea 1) con `requisitos={"S1-0": REQUISITOS_S1}` (UC‑17, UC‑18, RF‑64 a
  RF‑71 y RNF‑14), los `ParTDD` de SL‑E1, SL‑E2, SL‑E3 y de cada intérprete del BCV (fases `S1-0`…`S1-4`) y las
  comprobaciones `S1-MEM` y `S1-FUENTE` (`S1-0`) y `S1-BASE-060` (`S1-5`). S5‑M8 (regresión) es C5; S5‑M2 (núcleo
  intacto en S5‑1) no es acumulable y queda en `guardia_nucleo.py`. Cada fase posterior sube `--hasta` del paso
  «Meta de Silice» de la CI en el PR que cruza su compuerta.

- [ ] **Paso 1: Escribir la prueba que falla** — `tests/unit/test_meta_silice.py`:
```python
"""Meta unica de Silice (maestro §6.3, RV-17; plan 0.6.0, tarea A4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_silice import (
    ARCHIVOS_REGRESION,
    PARTE_T0,
    REGRESION,
    CifraDeTiempo,
    ParTDD,
    Parte,
    evaluar_cifras,
    evaluar_diff_vacio,
    evaluar_guardia,
    evaluar_omitidas,
    evaluar_orden_tdd,
    evaluar_regresion,
    evaluar_requisitos,
    fases_hasta,
    guardia_declarada,
    main,
    orden_de_par,
    partes,
    requisitos_exigidos,
    validar_partes,
)

RAIZ = Path(__file__).resolve().parents[2]
JUNIT_LIMPIO = '<testsuites><testsuite><testcase classname="a" name="b"/></testsuite></testsuites>'
JUNIT_OMITIDA = (
    '<testsuites><testsuite><testcase classname="a" name="b">'
    '<skipped message="sin modelo"/></testcase></testsuite></testsuites>'
)
CIFRA = CifraDeTiempo(
    "RNF-11", "scripts/_salida_rnf11.json", "mediana_s", "uv run python scripts/medir_rnf11.py", "T0"
)


def test_los_archivos_de_regresion_son_los_del_bloque_literal() -> None:
    assert ARCHIVOS_REGRESION == (
        "tests/integration/test_auditoria_7_de_7.py",
        "tests/integration/test_composicion_extremo_a_extremo.py",
        "tests/unit/test_budget.py",
        "tests/unit/test_caso_ti001.py",
        "tests/unit/test_costing.py",
        "tests/unit/test_huellas_rnf04.py",
        "tests/unit/test_linea_base.py",
        "tests/unit/test_verification.py",
    )
    assert set(REGRESION) == {
        "cinco APU a +-0,01",
        "7 de 7",
        "R4 de 3/4 pulg",
        "TI-001 total, PU y PE 28 586,76 USD Dia 6",
        "dos huellas de RNF-04",
        "cuatro hojas de exportar_excel",
    }


def test_cada_prueba_de_regresion_esta_definida() -> None:
    for nodos in REGRESION.values():
        for nodo in nodos:
            archivo, _, prueba = nodo.partition("::")
            texto = (RAIZ / archivo).read_text(encoding="utf-8")
            assert not prueba or f"def {prueba}(" in texto, nodo


def test_fases_hasta_acumula_en_orden() -> None:
    assert fases_hasta("0.6.0", "T0") == ("T0",)
    assert fases_hasta("0.6.0", "S1-0") == ("T0", "S5-1", "S1-0")
    with pytest.raises(ValueError, match="fase desconocida"):
        fases_hasta("0.6.0", "S2-1")
    with pytest.raises(ValueError, match="version desconocida"):
        fases_hasta("0.5.0", "T0")


def test_los_requisitos_se_exigen_por_presencia_y_por_fase() -> None:
    parte = Parte("S5", requisitos={"S5-1": ("RF-96", "RNF-20")})
    assert requisitos_exigidos((parte,), ("T0",)) == ()
    assert requisitos_exigidos((parte,), ("T0", "S5-1")) == ("RF-96", "RNF-20")
    ers = "| RF-96 | algo | E |\n| Calidad | RNF-20 deriva | x |\n"
    assert evaluar_requisitos(ers, ("RF-96", "RNF-20"))[0] is Estado.OK
    estado, detalle = evaluar_requisitos(ers, ("RF-96", "RF-97"))
    assert estado is Estado.FALLA and "RF-97" in detalle
    assert evaluar_requisitos(None, ("RF-96",))[0] is Estado.PENDIENTE
    assert evaluar_requisitos(None, ())[0] is Estado.OK


def test_omitidas() -> None:
    assert evaluar_omitidas(JUNIT_LIMPIO)[0] is Estado.OK
    estado, detalle = evaluar_omitidas(JUNIT_OMITIDA)
    assert estado is Estado.FALLA and "sin modelo" in detalle
    assert evaluar_omitidas(None)[0] is Estado.PENDIENTE
    assert evaluar_omitidas("<roto")[0] is Estado.PENDIENTE


def test_orden_tdd() -> None:
    par = ParTDD("tests/unit/test_x.py", "ui/x.py", "T0")
    assert evaluar_orden_tdd({})[0] is Estado.OK
    assert evaluar_orden_tdd({par: True})[0] is Estado.OK
    assert evaluar_orden_tdd({par: False})[0] is Estado.FALLA
    assert evaluar_orden_tdd({par: None})[0] is Estado.PENDIENTE


def test_el_orden_de_a1_se_lee_del_historial_real() -> None:
    assert orden_de_par(ParTDD("tests/unit/test_entorno_silice.py", "ui/entorno.py", "T0")) is True


def test_diff_vacio() -> None:
    assert evaluar_diff_vacio("core/contracts/", False, None)[0] is Estado.PENDIENTE
    assert evaluar_diff_vacio("core/contracts/", True, None)[0] is Estado.PENDIENTE
    cambio = " core/contracts/apu.py | 2 +-\n"
    assert evaluar_diff_vacio("core/contracts/", True, cambio)[0] is Estado.FALLA
    assert evaluar_diff_vacio("core/contracts/", True, "")[0] is Estado.OK


def test_una_prueba_de_regresion_borrada_es_falla() -> None:
    intacto = (Estado.OK, "intacto")
    grupos = {grupo: (1, 1) for grupo in REGRESION}
    assert evaluar_regresion(intacto, grupos, [])[0] is Estado.OK
    assert evaluar_regresion(intacto, {**grupos, "7 de 7": None}, ["7 de 7"])[0] is Estado.FALLA
    assert evaluar_regresion((Estado.FALLA, "cambio"), grupos, [])[0] is Estado.FALLA
    assert evaluar_regresion(intacto, {**grupos, "7 de 7": (3, 4)}, [])[0] is Estado.FALLA


def test_cifras_de_tiempo() -> None:
    assert evaluar_cifras({}, [])[0] is Estado.OK
    assert evaluar_cifras({CIFRA.ruta: None}, [CIFRA])[0] is Estado.PENDIENTE
    assert evaluar_cifras({CIFRA.ruta: {"mediana_s": "rapido"}}, [CIFRA])[0] is Estado.PENDIENTE
    estado, detalle = evaluar_cifras({CIFRA.ruta: {"mediana_s": 0.42}}, [CIFRA])
    assert estado is Estado.OK and "RNF-11" in detalle


def test_la_guardia_esta_declarada_en_el_conftest_real() -> None:
    assert guardia_declarada((RAIZ / "tests" / "conftest.py").read_text(encoding="utf-8"))


def test_una_guardia_sin_autouse_o_de_funcion_no_cuenta() -> None:
    sin_autouse = "import pytest\n@pytest.fixture(scope='session')\ndef _guardia_de_red():\n    yield\n"
    de_funcion = "import pytest\n@pytest.fixture(autouse=True)\ndef _guardia_de_red():\n    yield\n"
    assert not guardia_declarada(sin_autouse)
    assert not guardia_declarada(de_funcion)
    assert not guardia_declarada(None)


def test_evaluar_guardia() -> None:
    assert evaluar_guardia(False, None)[0] is Estado.FALLA
    assert evaluar_guardia(True, None)[0] is Estado.PENDIENTE
    assert evaluar_guardia(True, (5, 6))[0] is Estado.FALLA
    assert evaluar_guardia(True, (6, 6))[0] is Estado.OK


def test_las_partes_descubiertas_usan_fases_declaradas() -> None:
    validar_partes(partes())
    assert partes()[0] is PARTE_T0


def test_una_parte_con_una_fase_inexistente_se_rechaza() -> None:
    mala = Parte("X", pares_tdd=(ParTDD("a", "b", "S9-9"),))
    with pytest.raises(ValueError, match="S9-9"):
        validar_partes((mala,))


def test_los_pares_de_t0_nombran_archivos_del_repositorio() -> None:
    for par in PARTE_T0.pares_tdd:
        assert (RAIZ / par.prueba).is_file(), par.prueba
        assert (RAIZ / par.implementacion).is_file(), par.implementacion


def test_main_rechaza_una_fase_que_no_es_de_la_version(capsys) -> None:
    with pytest.raises(SystemExit) as salida:
        main(["--version", "0.6.0", "--hasta", "S2-1"])
    assert salida.value.code == 2
    assert "S2-1" in capsys.readouterr().err
```
En `tests/unit/test_ci_silice.py`, agregar:
```python
def test_la_meta_de_silice_corre_tras_la_suite_con_historia_completa() -> None:
    trabajo = _pruebas()
    checkout = next(
        paso for paso in trabajo["steps"] if str(paso.get("uses", "")).startswith("actions/checkout")
    )
    assert checkout["with"]["fetch-depth"] == 0
    meta = _indice(trabajo, "scripts/meta_silice.py")
    assert _indice(trabajo, "pytest -W error") < meta
    assert _indice(trabajo, "scripts/medir_rnf11.py") < meta
    assert "--junit reporte-pruebas.xml" in trabajo["steps"][meta]["run"]
```

- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_meta_silice.py tests/unit/test_ci_silice.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'scripts.meta_silice'` y
`AssertionError: ningun paso corre 'scripts/meta_silice.py'` (o `KeyError: 'with'` en el checkout).
```bash
git add tests/unit/test_meta_silice.py tests/unit/test_ci_silice.py
git commit -m "test(scripts): meta unica de Silice con regresion literal" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima** — `scripts/meta_silice.py`:
```python
"""Meta unica de Silice (spec maestro §6.3, RV-17): `--version X --hasta FASE`.

Una sola meta para la 0.6.0 a la 1.0.0 (no hay `meta_s1.py` ni `meta_s5.py`). Siete comprobaciones
comunes corren en toda version y fase:

C1 presencia en la ERS de los numeros que declaran las fases evaluadas (nunca un conteo absoluto);
C2 cero pruebas omitidas en el JUnit de la suite (`--junit`);
C3 el primer commit de cada prueba declarada es anterior al de su implementacion;
C4 `git diff v0.5.0..HEAD -- core/contracts/` vacio;
C5 bloque de regresion literal: sus archivos sin cambios desde v0.5.0 y sus pruebas en verde;
C6 las pruebas de tiempo de las fases evaluadas dejaron su cifra (la ausencia no es un OK);
C7 la guardia de red de `tests/conftest.py` esta declarada (autouse, de sesion) y su prueba pasa.

Cada parte de Silice extiende la meta sin editar este archivo: crea `scripts/meta_silice_<parte>.py`
con `PARTE = Parte(...)` (requisitos por fase, pares prueba-implementacion, cifras de tiempo y
comprobaciones propias, cada una con la fase en que arranca); `partes()` los descubre por nombre. Al
abrir una version solo se edita `FASES`. C3 exige fusionar con merge commit (`gh pr merge --merge`).

PENDIENTE es evidencia ausente y tambien impide el OK: el codigo de salida es 0 solo si todas las
filas estan en OK.

Uso: `uv run python scripts/meta_silice.py --version 0.6.0 --hasta T0 --junit reporte-pruebas.xml [--json]`.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado, Fila, _filas_a_json, render_tabla  # noqa: E402
from scripts.meta_sf import (  # noqa: E402
    _correr_pytest,
    _existe,
    _patron_definicion,
    combinar_s4,
    contar_resultados,
    evaluar_s8_regresion,
)
from scripts.verificar_omitidas import SinEvidenciaError, omitidas  # noqa: E402

BASE_REGRESION = "v0.5.0"
RUTA_ERS = RAIZ / "docs" / "ERS.md"
RUTA_CONFTEST = RAIZ / "tests" / "conftest.py"
PRUEBA_DE_LA_GUARDIA = "tests/unit/test_guardia_red.py"
NOMBRE_GUARDIA = "_guardia_de_red"

#: Fases de cada version, en orden de evaluacion (no de fusion). T0 es la fase transversal.
FASES: dict[str, tuple[str, ...]] = {
    "0.6.0": ("T0", "S5-1", "S1-0", "S1-1", "S1-2", "S1-3", "S1-4", "S1-5"),
}

#: Bloque de regresion literal (maestro §6.3): grupo -> nodeids. Estas pruebas no se editan; si un
#: cambio moviera alguna, se registra un ruling de reanclaje.
REGRESION: dict[str, tuple[str, ...]] = {
    "cinco APU a +-0,01": (
        "tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base",
        "tests/unit/test_linea_base.py",
    ),
    "7 de 7": ("tests/integration/test_auditoria_7_de_7.py",),
    "R4 de 3/4 pulg": ("tests/unit/test_verification.py::test_r4_marca_3_4_pulg_y_no_marca_pvc",),
    "TI-001 total, PU y PE 28 586,76 USD Dia 6": (
        "tests/unit/test_caso_ti001.py::test_total_y_cierre_de_la_curva",
        "tests/unit/test_caso_ti001.py::test_precios_unitarios",
        "tests/unit/test_caso_ti001.py::test_punto_de_equilibrio",
    ),
    "dos huellas de RNF-04": ("tests/unit/test_huellas_rnf04.py",),
    "cuatro hojas de exportar_excel": (
        "tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas",
        "tests/integration/test_composicion_extremo_a_extremo.py"
        "::test_exportar_excel_escribe_las_cuatro_hojas_con_la_modalidad",
    ),
}
#: Archivos cuyo `git diff v0.5.0..HEAD` debe quedar vacio (C5).
ARCHIVOS_REGRESION: tuple[str, ...] = tuple(
    sorted({nodo.partition("::")[0] for nodos in REGRESION.values() for nodo in nodos})
)


@dataclass(frozen=True, slots=True)
class ParTDD:
    """Una prueba y el archivo que ella hizo nacer: el primer commit de la prueba va antes."""

    prueba: str
    implementacion: str
    fase: str


@dataclass(frozen=True, slots=True)
class CifraDeTiempo:
    """Una medicion de tiempo que debe dejar su cifra (`clave` numerica en el JSON de `ruta`)."""

    nombre: str
    ruta: str
    clave: str
    orden: str
    fase: str


@dataclass(frozen=True)
class Parte:
    """Lo que una parte de Silice agrega a la meta, cada cosa con la fase en que arranca."""

    nombre: str
    requisitos: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    pares_tdd: tuple[ParTDD, ...] = ()
    cifras: tuple[CifraDeTiempo, ...] = ()
    comprobaciones: tuple[Comprobacion, ...] = ()


@dataclass(frozen=True)
class Contexto:
    version: str
    fases: tuple[str, ...]
    junit: Path | None
    partes: tuple[Parte, ...]


@dataclass(frozen=True)
class Comprobacion:
    codigo: str
    titulo: str
    fase: str
    evaluar: Callable[[Contexto], tuple[Estado, str]]


PARTE_T0 = Parte(
    nombre="T0 transversal",
    pares_tdd=(
        ParTDD("tests/unit/test_entorno_silice.py", "ui/entorno.py", "T0"),
        ParTDD("tests/unit/test_config_streamlit.py", ".streamlit/config.toml", "T0"),
        ParTDD("tests/unit/test_nombre_silice.py", "LICENSE", "T0"),
        ParTDD("tests/unit/test_descargar_modelo.py", "scripts/descargar_modelo.py", "T0"),
        ParTDD("tests/unit/test_meta_silice.py", "scripts/meta_silice.py", "T0"),
    ),
    cifras=(
        CifraDeTiempo(
            "RNF-11",
            "scripts/_salida_rnf11.json",
            "mediana_s",
            "uv run python scripts/medir_rnf11.py",
            "T0",
        ),
    ),
)


# --------------------------------------------------------------------------------------
# Fases y partes
# --------------------------------------------------------------------------------------


def fases_hasta(version: str, hasta: str) -> tuple[str, ...]:
    """Las fases de las versiones anteriores y las de `version` hasta `hasta` (incluida)."""
    if version not in FASES:
        raise ValueError(f"version desconocida: {version!r}; validas: {', '.join(FASES)}")
    if hasta not in FASES[version]:
        validas = ", ".join(FASES[version])
        raise ValueError(f"fase desconocida para la {version}: {hasta!r}; validas: {validas}")
    acumuladas: list[str] = []
    for nombre, fases in FASES.items():
        if nombre == version:
            return (*acumuladas, *fases[: fases.index(hasta) + 1])
        acumuladas.extend(fases)
    raise AssertionError("inalcanzable")


def partes() -> tuple[Parte, ...]:
    """`PARTE_T0` y la `PARTE` de cada `scripts/meta_silice_<parte>.py`, por nombre de archivo."""
    descubiertas = [PARTE_T0]
    for ruta in sorted((RAIZ / "scripts").glob("meta_silice_*.py")):
        descubiertas.append(importlib.import_module(f"scripts.{ruta.stem}").PARTE)
    return tuple(descubiertas)


def _fases_de(parte: Parte) -> set[str]:
    return {
        *parte.requisitos,
        *(par.fase for par in parte.pares_tdd),
        *(cifra.fase for cifra in parte.cifras),
        *(comprobacion.fase for comprobacion in parte.comprobaciones),
    }


def validar_partes(todas: Sequence[Parte]) -> None:
    """`ValueError` si alguna parte usa una fase que no esta en `FASES`."""
    conocidas = {fase for fases in FASES.values() for fase in fases}
    for parte in todas:
        desconocidas = sorted(_fases_de(parte) - conocidas)
        if desconocidas:
            raise ValueError(f"la parte {parte.nombre!r} usa fases fuera de FASES: {desconocidas}")


def requisitos_exigidos(partes_: Sequence[Parte], fases: Sequence[str]) -> tuple[str, ...]:
    return tuple(r for parte in partes_ for fase in fases for r in parte.requisitos.get(fase, ()))


# --------------------------------------------------------------------------------------
# Evaluadores puros
# --------------------------------------------------------------------------------------


def evaluar_requisitos(texto_ers: str | None, exigidos: Sequence[str]) -> tuple[Estado, str]:
    """C1: cada numero exigido esta DEFINIDO en la ERS (presencia; nunca un conteo)."""
    if not exigidos:
        return Estado.OK, "las fases evaluadas no declaran numeros de la ERS"
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    faltan = []
    for ident in exigidos:
        prefijo, _, numero = ident.partition("-")
        if not re.search(_patron_definicion(prefijo, int(numero)), texto_ers, re.MULTILINE):
            faltan.append(ident)
    if faltan:
        return Estado.FALLA, "la ERS no define: " + ", ".join(faltan)
    return Estado.OK, "definidos en docs/ERS.md: " + ", ".join(exigidos)


def evaluar_omitidas(xml_texto: str | None) -> tuple[Estado, str]:
    """C2: cero omitidas en el JUnit; sin JUnit legible no hay evidencia."""
    if xml_texto is None:
        return Estado.PENDIENTE, "sin JUnit: corra pytest con --junitxml=reporte-pruebas.xml y --junit"
    try:
        lista = omitidas(xml_texto)
    except SinEvidenciaError as error:
        return Estado.PENDIENTE, str(error)
    if lista:
        return Estado.FALLA, f"{len(lista)} omitida(s): " + "; ".join(lista[:5])
    return Estado.OK, "0 pruebas omitidas en el JUnit"


def evaluar_orden_tdd(orden: Mapping[ParTDD, bool | None]) -> tuple[Estado, str]:
    """C3: True si la prueba precede a su implementacion; False si no; None sin commits."""
    if not orden:
        return Estado.OK, "las fases evaluadas no declaran pares prueba-implementacion"
    despues = [f"{p.prueba} -> {p.implementacion}" for p, ok in orden.items() if ok is False]
    if despues:
        return Estado.FALLA, "prueba no anterior a su implementacion: " + "; ".join(despues)
    sin_commit = [f"{p.prueba} -> {p.implementacion}" for p, ok in orden.items() if ok is None]
    if sin_commit:
        return Estado.PENDIENTE, "sin commit de: " + "; ".join(sin_commit)
    return Estado.OK, f"{len(orden)} pruebas versionadas antes de su implementacion"


def evaluar_diff_vacio(que: str, base_existe: bool, diff: str | None) -> tuple[Estado, str]:
    """C4 y la mitad de C5: `git diff --stat v0.5.0..HEAD -- <que>` vacio."""
    if not base_existe:
        return Estado.PENDIENTE, f"no existe {BASE_REGRESION}: git fetch --tags"
    if diff is None:
        return Estado.PENDIENTE, f"git no respondio al comparar {que} con {BASE_REGRESION}"
    cambios = [linea.strip() for linea in diff.splitlines() if linea.strip()]
    if cambios:
        return Estado.FALLA, f"{que} cambio desde {BASE_REGRESION}: " + "; ".join(cambios[:5])
    return Estado.OK, f"{que} intacto desde {BASE_REGRESION} (git diff vacio)"


def evaluar_regresion(
    estado_diff: tuple[Estado, str],
    grupos: Mapping[str, tuple[int, int] | None],
    ausentes: Sequence[str],
) -> tuple[Estado, str]:
    """C5: archivos intactos y pruebas en verde; una prueba borrada es FALLA, no PENDIENTE."""
    return combinar_s4([estado_diff, evaluar_s8_regresion(dict(grupos), ausentes)])


def evaluar_cifras(
    registros: Mapping[str, Mapping | None], cifras: Sequence[CifraDeTiempo]
) -> tuple[Estado, str]:
    """C6: cada medicion de tiempo dejo un numero en su JSON."""
    if not cifras:
        return Estado.OK, "las fases evaluadas no declaran pruebas de tiempo"
    faltan, dejadas = [], []
    for cifra in cifras:
        registro = registros.get(cifra.ruta)
        valor = registro.get(cifra.clave) if isinstance(registro, Mapping) else None
        if isinstance(valor, bool) or not isinstance(valor, int | float):
            faltan.append(f"{cifra.nombre} (corra `{cifra.orden}`)")
        else:
            dejadas.append(f"{cifra.nombre} {cifra.clave}={valor}")
    if faltan:
        return Estado.PENDIENTE, "sin cifra: " + "; ".join(faltan)
    return Estado.OK, "cifras registradas: " + "; ".join(dejadas)


def guardia_declarada(texto_conftest: str | None) -> bool:
    """True si el conftest define `_guardia_de_red` como fixture autouse de sesion."""
    if texto_conftest is None:
        return False
    for nodo in ast.walk(ast.parse(texto_conftest)):
        if not (isinstance(nodo, ast.FunctionDef) and nodo.name == NOMBRE_GUARDIA):
            continue
        for decorador in nodo.decorator_list:
            if isinstance(decorador, ast.Call) and ast.unparse(decorador.func) == "pytest.fixture":
                claves = {
                    k.arg: ast.literal_eval(k.value)
                    for k in decorador.keywords
                    if k.arg in ("scope", "autouse")
                }
                if claves == {"scope": "session", "autouse": True}:
                    return True
    return False


def evaluar_guardia(declarada: bool, resultado: tuple[int, int] | None) -> tuple[Estado, str]:
    """C7: la guardia esta declarada y su prueba pasa (`resultado` = (pasan, total))."""
    if not declarada:
        return Estado.FALLA, f"tests/conftest.py no declara {NOMBRE_GUARDIA} autouse de sesion"
    if resultado is None or resultado[1] == 0:
        return Estado.PENDIENTE, f"{PRUEBA_DE_LA_GUARDIA} no recolecto casos"
    pasan, total = resultado
    if pasan < total:
        return Estado.FALLA, f"la prueba de la guardia falla ({pasan}/{total})"
    return Estado.OK, f"guardia de red activa; su prueba en verde ({pasan}/{total})"


# --------------------------------------------------------------------------------------
# Orquestacion: git, disco y pytest
# --------------------------------------------------------------------------------------


def _git(*argumentos: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *argumentos], cwd=RAIZ, capture_output=True, text=True,
            encoding="utf-8", check=False,
        )
    except OSError:
        return None


def _referencia_existe(ref: str) -> bool:
    r = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return r is not None and r.returncode == 0


def _diff_desde_base(rutas: Sequence[str]) -> tuple[bool, str | None]:
    if not _referencia_existe(BASE_REGRESION):
        return False, None
    r = _git("diff", "--stat", f"{BASE_REGRESION}..HEAD", "--", *rutas)
    return True, (r.stdout if r is not None and r.returncode == 0 else None)


def _primer_commit(ruta: str) -> str | None:
    r = _git("log", "--reverse", "--format=%H", "--diff-filter=A", "--", ruta)
    lineas = r.stdout.split() if r is not None and r.returncode == 0 else []
    return lineas[0] if lineas else None


def orden_de_par(par: ParTDD) -> bool | None:
    """True si el primer commit de la prueba es ancestro estricto del de su implementacion."""
    prueba, implementacion = _primer_commit(par.prueba), _primer_commit(par.implementacion)
    if prueba is None or implementacion is None:
        return None
    if prueba == implementacion:
        return False
    r = _git("merge-base", "--is-ancestor", prueba, implementacion)
    return r is not None and r.returncode == 0


def _leer_json(ruta: Path) -> Mapping | None:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def _c1(ctx: Contexto) -> tuple[Estado, str]:
    texto = RUTA_ERS.read_text(encoding="utf-8") if RUTA_ERS.is_file() else None
    return evaluar_requisitos(texto, requisitos_exigidos(ctx.partes, ctx.fases))


def _c2(ctx: Contexto) -> tuple[Estado, str]:
    junit = ctx.junit
    return evaluar_omitidas(junit.read_text(encoding="utf-8") if junit and junit.is_file() else None)


def _c3(ctx: Contexto) -> tuple[Estado, str]:
    pares = [p for parte in ctx.partes for p in parte.pares_tdd if p.fase in ctx.fases]
    return evaluar_orden_tdd({par: orden_de_par(par) for par in pares})


def _c4(ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_diff_vacio("core/contracts/", *_diff_desde_base(("core/contracts/",)))


def _c5(ctx: Contexto) -> tuple[Estado, str]:
    estado_diff = evaluar_diff_vacio(
        "archivos de regresion", *_diff_desde_base(ARCHIVOS_REGRESION)
    )
    presentes = {g: ids for g, ids in REGRESION.items() if all(_existe(i) for i in ids)}
    ausentes = [g for g in REGRESION if g not in presentes]
    ids = [i for grupo in presentes.values() for i in grupo]
    cuenta = contar_resultados(_correr_pytest(ids), presentes) if ids else {}
    return evaluar_regresion(estado_diff, {g: cuenta.get(g) for g in REGRESION}, ausentes)


def _c6(ctx: Contexto) -> tuple[Estado, str]:
    cifras = [c for parte in ctx.partes for c in parte.cifras if c.fase in ctx.fases]
    return evaluar_cifras({c.ruta: _leer_json(RAIZ / c.ruta) for c in cifras}, cifras)


def _c7(ctx: Contexto) -> tuple[Estado, str]:
    texto = RUTA_CONFTEST.read_text(encoding="utf-8") if RUTA_CONFTEST.is_file() else None
    if not guardia_declarada(texto):
        return evaluar_guardia(False, None)
    if not (RAIZ / PRUEBA_DE_LA_GUARDIA).is_file():
        return evaluar_guardia(True, None)
    salida = _correr_pytest([PRUEBA_DE_LA_GUARDIA])
    return evaluar_guardia(True, contar_resultados(salida, {"g": (PRUEBA_DE_LA_GUARDIA,)})["g"])


COMUNES: tuple[Comprobacion, ...] = (
    Comprobacion("C1", "Numeros de la ERS de las fases evaluadas (presencia)", "T0", _c1),
    Comprobacion("C2", "Cero pruebas omitidas", "T0", _c2),
    Comprobacion("C3", "Commit de la prueba anterior al de la implementacion", "T0", _c3),
    Comprobacion("C4", "core/contracts/ intacto desde v0.5.0", "T0", _c4),
    Comprobacion("C5", "Regresion literal intacta desde v0.5.0 y en verde", "T0", _c5),
    Comprobacion("C6", "Las pruebas de tiempo dejaron su cifra", "T0", _c6),
    Comprobacion("C7", "Guardia de red activa", "T0", _c7),
)


def evaluar(version: str, hasta: str, junit: Path | None) -> list[Fila]:
    fases = fases_hasta(version, hasta)
    todas = partes()
    validar_partes(todas)
    ctx = Contexto(version, fases, junit, todas)
    propias = [c for parte in todas for c in parte.comprobaciones if c.fase in fases]
    return [Fila(c.codigo, c.titulo, *c.evaluar(ctx)) for c in (*COMUNES, *propias)]


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meta_silice.py", description="Meta unica de Silice (maestro 6.3, RV-17)."
    )
    parser.add_argument("--version", required=True, choices=list(FASES))
    parser.add_argument("--hasta", required=True, help="fase hasta la que se evalua, incluida")
    parser.add_argument("--junit", type=Path, default=None, help="JUnit de pytest --junitxml")
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    args = parser.parse_args(argv)
    if args.hasta not in FASES[args.version]:
        parser.error(
            f"fase desconocida para la {args.version}: {args.hasta}; "
            f"validas: {', '.join(FASES[args.version])}"
        )
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parsear_args(argv)
    filas = evaluar(args.version, args.hasta, args.junit)
    print(_filas_a_json(filas) if args.json else render_tabla(filas))
    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```
(`Parte` cita `Comprobacion` y `Contexto` antes de definirlas: es válido por `from __future__ import annotations`.)

`.github/workflows/ci.yml`, trabajo `pruebas`: el paso «Checkout» lleva
```yaml
        with:
          fetch-depth: 0 # C3 y C5 de la meta leen el historial y la etiqueta v0.5.0
```
y, después de «Medición de RNF‑11»:
```yaml
      - name: Meta de Silice (maestro 6.3, RV-17)
        if: runner.os == 'Linux'
        run: >-
          uv run --no-sync python scripts/meta_silice.py
          --version 0.6.0 --hasta T0 --junit reporte-pruebas.xml
```
(cada compuerta posterior sube `--hasta` en este paso: S5‑1, S1‑0…). Fila en `scripts/README.md`, «Metas de
sprint»: `| `meta_silice.py` | meta única de Sílice: siete comprobaciones comunes (ERS por presencia, cero omitidas, prueba antes que código, contratos y regresión intactos desde v0.5.0, cifras de tiempo, guardia de red) más las de cada parte en `meta_silice_<parte>.py` | 0.6.0 a 1.0.0 |`.

- [ ] **Paso 4: Correrla y ver el verde**
Run: `uv run pytest tests/unit/test_meta_silice.py tests/unit/test_ci_silice.py -v -W error` → PASS. Luego:
```bash
uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml
uv run python scripts/medir_rnf11.py
uv run python scripts/meta_silice.py --version 0.6.0 --hasta T0 --junit reporte-pruebas.xml
```
Esperado en local: `RESULTADO: 6/7 metas OK` con **C3 en PENDIENTE** («sin commit de: tests/unit/test_meta_silice.py
-> scripts/meta_silice.py») hasta que exista el commit de implementación; tras el commit del paso 5, `7/7`.
`uv run ruff check scripts/meta_silice.py tests/unit/test_meta_silice.py`.

- [ ] **Paso 5: Commit y PR**
```bash
git add scripts/meta_silice.py scripts/README.md .github/workflows/ci.yml
git commit -m "feat(scripts): meta unica de Silice con siete comprobaciones comunes" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
uv run python scripts/meta_silice.py --version 0.6.0 --hasta T0 --junit reporte-pruebas.xml
git add docs/bitacora/2026-10-silice-060.md
git commit -m "docs(bitacora): compuerta T0 con la salida de la meta" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin inc/060-meta
gh pr create --base main --head inc/060-meta --title "T0-A4: meta unica de Silice" --body-file -
```
(la bitácora recibe `## T0 · A4 Meta única y compuerta T0` con la tabla impresa por la meta, literal).

---

### Tarea A5: Enmienda propuesta a NORMAS §3

**Rama:** `inc/060-enmienda-normas` (sale de `origin/main`; PR a `main`; puede ir en paralelo con A1…A4)   **Rol:** sf-lider-de-fase
**Archivos:**
- Crear: `docs/bitacora/2026-10-silice-enmienda-normas-3.md`
- Crear (prueba): `tests/unit/test_enmienda_normas.py`
- Modificar, **solo si Eugenio ratifica**: `NORMAS.md:79,84-87`

**Interfaces:**
- Consume: maestro §6.1 (RV‑2) y `git worktree list` del día.
- Produce: el texto exacto de las filas Ramas, Worktrees, Fusión, Etiquetas y Metas de NORMAS §3; el campo
  `**Estado:**` del documento (`PROPUESTA` o `RATIFICADA por Eugenio el AAAA-MM-DD`).

- [ ] **Paso 1: Escribir la prueba que falla** — `tests/unit/test_enmienda_normas.py`:
```python
"""NORMAS §3 y su enmienda concuerdan (maestro §6.1, RV-2; plan 0.6.0, tarea A5).

NORMAS cambia solo cuando el documento dice que Eugenio la ratifico.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ENMIENDA = RAIZ / "docs" / "bitacora" / "2026-10-silice-enmienda-normas-3.md"
REGLAS = (
    "Como máximo tres worktrees vivos",
    "ramas cortas por fase",
    "un solo carril de núcleo",
)
_ESTADO = re.compile(
    r"^\*\*Estado:\*\* (PROPUESTA|RATIFICADA por Eugenio el \d{4}-\d{2}-\d{2})$", re.MULTILINE
)


def test_la_enmienda_declara_las_tres_reglas_y_su_estado() -> None:
    texto = ENMIENDA.read_text(encoding="utf-8")
    for regla in REGLAS:
        assert regla in texto, regla
    assert _ESTADO.search(texto) is not None


def test_normas_aplica_la_enmienda_solo_si_esta_ratificada() -> None:
    estado = _ESTADO.search(ENMIENDA.read_text(encoding="utf-8")).group(1)
    normas = (RAIZ / "NORMAS.md").read_text(encoding="utf-8")
    assert (REGLAS[0] in normas) is estado.startswith("RATIFICADA")
```

- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_enmienda_normas.py -v -W error`
Esperado: FAIL con `FileNotFoundError: … 2026-10-silice-enmienda-normas-3.md`.
```bash
git add tests/unit/test_enmienda_normas.py
git commit -m "test(normas): la enmienda de NORMAS 3 y NORMAS concuerdan" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima** — `docs/bitacora/2026-10-silice-enmienda-normas-3.md`:
```markdown
# Enmienda propuesta a NORMAS.md §3: worktrees, ramas cortas por fase y un carril de núcleo

**Estado:** PROPUESTA

| Campo | Valor |
|---|---|
| Origen | spec maestro de Sílice 1.0.0, §6.1, ruling RV‑2; plan de la 0.6.0, sección A, tarea A5 |
| Redacción | 2026‑10‑11 |
| Quién ratifica | Eugenio. Al ratificar, se cambia la línea **Estado** a «RATIFICADA por Eugenio el AAAA-MM-DD» y, en el mismo PR, se aplica la sección 2 a NORMAS.md; `tests/unit/test_enmienda_normas.py` exige que ambas cosas vayan juntas |

## 1. Por qué

- NORMAS §3 dice hoy: «Uno por sprint en `.worktrees/<nombre-corto>` … Solo coexisten el checkout principal y
  el worktree del sprint vigente».
- Sílice construye con carriles en paralelo (maestro §5, RV‑1): S1‑2 (`adapters/bcv`), S3‑1 (`seguridad`),
  S3‑5 (planos) y S4.0–S4.2 (`asistente`) avanzan junto al carril de núcleo. Con un solo worktree, cada carril
  obliga a cambiar de rama en el mismo directorio (con su `.venv`) o a romper la norma.
- La norma ya no se cumple: el 2026‑10‑11, `git worktree list` muestra el checkout principal y nueve worktrees
  más (sección 5).
- El daño que motivó la norma (`main` dos semanas desactualizado) lo evitan mejor las otras dos reglas: ramas
  cortas por fase que salen del `main` del momento y se fusionan al cruzar su compuerta, y un solo carril de
  núcleo abierto a la vez.

## 2. Texto propuesto (sustituye estas filas de la tabla de NORMAS §3)

| Convención | Regla |
|---|---|
| Ramas | `main` es la única rama de integración. Desde Sílice (0.6.0), ramas cortas por fase: cada una sale del `main` del momento (`origin/main`), recibe `main` a menudo, corre la CI en cada *push* y se fusiona al cruzar la compuerta de su fase, no al final de la versión. Nada se apila. Hay un solo carril de núcleo abierto a la vez (orden del maestro §6.1: S1‑1 → S1‑3 → S1‑4 → S2‑1 … S2‑3 → S3‑2); una rama `-nucleo` toca solo `core/`, `migraciones/`, `tests/` y `docs/`. Una rama que agrega archivos bajo `adapters/` sale de `main` sin núcleo pendiente |
| Worktrees | Como máximo tres worktrees vivos además del checkout principal, en `.worktrees/<nombre-corto>`: el del carril de núcleo y hasta dos de carriles sin núcleo. Se borra con `git worktree remove` al fusionar su rama (nunca con `--force`; si se niega, se revisa qué quedó sin guardar) |
| Fusión | Un PR por fase **contra `main`**, fusionado en cuanto la CI esté verde y la compuerta cruzada, con *merge commit* (`gh pr merge <n> --merge`, nunca *squash*: la meta comprueba que el commit de cada prueba precede al de su implementación). No acumular pilas: `gh pr merge` fusiona en la base *actual* del PR |
| Etiquetas | Una por compuerta cruzada y, desde Sílice, `vX.Y.Z` anotada en `main`, en orden numérico (`v0.6.0` antes que `v0.7.0` aunque un carril llegue antes) |
| Metas | Desde la 0.6.0, una sola meta: `scripts/meta_silice.py --version X --hasta FASE`; una fase se cruza con la meta en OK **y** la compuerta anotada en `docs/bitacora/`. Las metas `meta_<sprint>.py` anteriores quedan como registro |

## 3. Qué no cambia

Commits, sesiones, entorno, idioma y el resto de NORMAS. La regla de la sección 9 (detenerse antes de tocar
`core/` desde un adaptador) sigue igual; los cambios de núcleo siguen con expediente.

## 4. Cómo se comprueba

- `git worktree list | wc -l` ≤ 4 (principal + tres) al abrir cada fase; se anota en la bitácora de la fase.
- La meta (`C3`) falla si una fusión con *squash* borra el orden prueba → implementación.
- `scripts/guardia_nucleo.py` en la CI sigue separando ramas de núcleo y de adaptadores (M9).

## 5. Limpieza propuesta de los worktrees actuales (no se ejecuta sin el visto bueno de Eugenio)

Todas las ramas de la tabla están contenidas en `origin/main` (`git merge-base --is-ancestor <rama> origin/main`,
2026‑10‑11):

| Worktree | Rama | Propuesta |
|---|---|---|
| `TESIS` (principal) | `inc/spec-horizonte` | se queda; volver a `main` cuando Eugenio lo decida |
| `.claude/worktrees/prototipo` | `inc/PLAN-prototipo` | borrar |
| `.claude/worktrees/ui` | `inc/PLAN-ui` | borrar |
| `.worktrees/integ` | `inc/sf-integracion` | borrar |
| `.worktrees/sf` | `inc/sf3-nucleo` | borrar |
| `.worktrees/sf3` | `inc/sf3` | borrar |
| `.worktrees/sf4` | `inc/sf4` | borrar |
| `.worktrees/sf5` | `inc/sf5` | borrar |
| `.worktrees/silice` | `inc/silice` | borrar al fusionar el plan de la 0.6.0 |
| `.worktrees/nombre` | `inc/nombre-silice` | se usa en A1; se borra al fusionarla |

Orden por worktree: `git -C <ruta> status --short` (debe estar vacío) y luego `git worktree remove <ruta>`.
```
Si Eugenio ratifica antes de fusionar este PR: cambiar la línea **Estado** a
`**Estado:** RATIFICADA por Eugenio el 2026-MM-DD` y sustituir en `NORMAS.md` las filas Ramas (línea 79),
Worktrees (84), Fusión (85), Etiquetas (86) y Metas (87) por las de la sección 2, literal.

- [ ] **Paso 4: Correrla y ver el verde**
Run: `uv run pytest tests/unit/test_enmienda_normas.py -v -W error` → PASS (en cualquiera de los dos estados);
`uv run python scripts/meta_datos.py` → 0.

- [ ] **Paso 5: Commit y PR**
```bash
git add docs/bitacora/2026-10-silice-enmienda-normas-3.md
git commit -m "docs(normas): enmienda propuesta a NORMAS 3, worktrees y ramas cortas" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin inc/060-enmienda-normas
gh pr create --base main --head inc/060-enmienda-normas --title "T0-A5: enmienda propuesta a NORMAS 3" --body-file -
```
(si se ratifica después de fusionar, un PR corto `inc/060-normas-ratificada` cambia el **Estado** y NORMAS juntos).

---

## Compuerta T0

- [ ] Las cinco PR fusionadas en `main` con *merge commit* y la CI verde en Linux y Windows (con
      `HF_HUB_OFFLINE=1` y el paso de la meta).
- [ ] En un checkout de `origin/main`: `unset VIRTUAL_ENV; uv sync --all-extras`;
      `uv run python scripts/descargar_modelo.py`;
      `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml`;
      `uv run python scripts/verificar_omitidas.py reporte-pruebas.xml` → «0 omitidas»;
      `uv run python scripts/medir_rnf11.py`;
      `uv run python scripts/meta_silice.py --version 0.6.0 --hasta T0 --junit reporte-pruebas.xml` →
      `RESULTADO: 7/7 metas OK`.
- [ ] `git diff --stat v0.5.0..origin/main -- core/` vacío; `uv run python scripts/guardia_nucleo.py --base v0.5.0` → 0;
      `uv run ruff check .` limpio.
- [ ] Arranque a mano: `uv run python -m streamlit run ui/app.py` escucha solo en `127.0.0.1` (`netstat -an | findstr 8501`
      sin `0.0.0.0` ni `[::]`) y el título es «Sílice».
- [ ] Encargos de revisión aprobados: requisitos, arquitectura, pruebas y calidad, verificador de hechos; y
      **seguridad** sobre A1 (`config.toml`) y A3 (guardia de red), por tocar red local y conexiones salientes.
- [ ] Compuerta anotada en `docs/bitacora/2026-10-silice-060.md` con la tabla literal de la meta, el estado de la
      enmienda (PROPUESTA o RATIFICADA) y la decisión pendiente sobre `ifctester`/`bcf-client` (para S3‑0).

## Foco de revisión

1. **Variable nueva en blanco o alias vencido** (A1): `SILICE_CASO="  "` con `ARENIA_CASO` lleno manda el alias,
   y al pasar `pyproject.toml` de 0.6.0 el alias debe desaparecer → `test_la_variable_nueva_en_blanco_cede_al_alias`
   y `test_el_alias_se_retira_despues_de_la_0_6_0`.
2. **AppTest bajo `showErrorDetails = "none"`** (A1): el `config.toml` del directorio de trabajo ocultaría el
   mensaje real de cada excepción en los fallos de AppTest → `test_la_suite_conserva_el_detalle_de_los_errores_de_apptest`
   (más la variable `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=full` de `tests/conftest.py`).
3. **Una prueba que se traga el bloqueo** con `except OSError` (A3): la sesión debe fallar igual →
   `test_un_intento_tragado_queda_registrado_y_falla_la_sesion`.
4. **IPv6 con zona o mapeada a IPv4** (`fe80::1%eth0`, `::ffff:127.0.0.1`) y `127.0.0.2` (A3): bloqueadas →
   casos de `test_destinos`.
5. **Una prueba de regresión borrada o renombrada** (A4): C5 en FALLA, nunca PENDIENTE →
   `test_una_prueba_de_regresion_borrada_es_falla`.

## Discrepancias encontradas

1. **`main` local desactualizado:** `main` = 1a02530 (PR #19); `origin/main` = ed597de (PR #30, con los specs). El
   encargo dice que `inc/nombre-silice` está «vacía sobre main»: está en 8610053 (`v0.5.0`), atrás de
   `origin/main`; A1 empieza con `git merge --ff-only origin/main`. Todas las ramas salen de `origin/main`. *Resuelta en el cotejo.* Toda rama sale de `origin/main`; B y C lo heredan.
2. **Límite de subida:** el encargo pide `maxUploadSize` coherente con `ui/subidas.py`, pero ese módulo no fija
   tamaño (solo nombres seguros). El límite de 20 MB vive en `adapters/espacio/planos/comun.py:36`
   (`LIMITE_BYTES`, RNF‑12); la prueba se ata a esa constante. *Resuelta en el cotejo.*
3. **`showErrorDetails`:** S5 §1.2 propone `"none"`; verificado válido en Streamlit 1.62.0
   (`.worktrees/sf5/.venv`, `ShowErrorDetailsConfigOptions`: full, stacktrace, type, none). Efecto no previsto
   por el spec: AppTest también lee ese archivo; se compensa con `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=full` en la suite. *Resuelta en el cotejo.* Verificado contra la versión de Streamlit del candado al ejecutar A1.
4. **`ifctester`:** RV‑24 y S5 §7.2 lo ponen en `civil` (instalador básico). PyPI (2026‑10‑11) muestra que
   `ifctester` 0.8.5 arrastra `bcf-client`, que declara **GPLv3**, además de `flask`. Se usa el extra aparte `ifc`
   (RV‑24 lo admite), fijado a `<0.9` (ya existe 0.9.0 y el candado tiene `ifcopenshell` 0.8.5). S3‑0 decide la
   licencia; S5‑3 decide si `ifc` entra al instalador. *Abierta (decisión 7 de `cotejo.md`; por defecto, extra `ifc` aparte y fuera del instalador hasta S3‑0).*
5. **Meta en la CI:** S5 §11.1 pone `meta_silice.py` en el trabajo `calidad`, pero ese trabajo no corre la suite
   (sin JUnit para C2) y clona con historia completa solo ahí. La meta va en `pruebas` (Linux), después de pytest
   y de `medir_rnf11.py`, con `fetch-depth: 0`. *Resuelta en el cotejo.* B (`--hasta S5-1`) y C (`--hasta S1-0`…`S1-5`) suben `--hasta` en ese mismo paso del trabajo `pruebas`.
6. **Licencia:** P9 la ubica en S5‑0; el encargo la adelanta a T0. S5‑0 la cita como existente (el instalador la
   muestra). *Resuelta en el cotejo.*
7. **`CHANGELOG.md`:** nace con S5‑1 (S5 §9.4), así que las cinco PR de T0 no tienen su línea. S5‑1 debe
   agregarlas bajo `[Sin publicar]` al crearlo. *Resuelta en el cotejo.* B, Tarea 7, crea `CHANGELOG.md` con las cinco líneas de T0 y la de S5‑1.
8. **Ratificación de la enmienda:** el maestro §6.1 dice que la enmienda se aplica «si Eugenio aprueba este
   maestro», y el maestro ya está aprobado (2026‑10‑11). El encargo pide un documento para ratificar: se escribe y
   NORMAS cambia solo con la ratificación registrada. Hoy hay nueve worktrees además del checkout principal. *Abierta (decisión 2 de `cotejo.md`; por defecto, la enmienda queda PROPUESTA y NORMAS no cambia).*
9. **`scripts/verificar_omitidas.py:3`** dice «Trece archivos» con `importorskip`; hoy son catorce. Se cambia el
   texto para que no dé un número. *Resuelta en el cotejo.*
10. **Regresión de `meta_sf.py`:** su grupo «linea base» solo corre `test_linea_base.py` (el oráculo de la
    fixture), no `test_costing.py`, que es la que verifica los cinco APU con el motor a ± 0,01. `REGRESION` de la
    meta única corre las dos. *Resuelta en el cotejo.*
11. **Alcance del renombre:** el encargo enumera los documentos vigentes; `docs/ERS.md` (líneas 151 y 886‑893) y
    `docs/README.md:52` también nombran el prototipo «AREN.IA». Se incluyen con la forma histórica
    `AREN.IA (hoy Sílice)`. *Resuelta en el cotejo.*
12. **`xlrd` con importación diferida:** S1 §4.4 no lo exige; esta sección lo impone en
    `tests/unit/test_dependencias_silice.py` (DIFERIDOS), siguiendo el patrón de los extras de `ml/`. S1‑2 importa
    `xlrd` dentro de la función de `adapters/bcv/libro.py` que abre el `.xls`. *Resuelta en el cotejo.* C, Tarea 6, importa `xlrd` dentro de `_xls` en `adapters/bcv/libro.py`.
13. **Interfaces que A produce y B y C consumen** (cotejo): `ui.entorno` (A1), la fixture `_guardia_de_red` (A3) y la API
    de `scripts/meta_silice.py` (A4: `Parte`, `ParTDD`, `Comprobacion`, `Contexto`, `partes()` que descubre
    `scripts/meta_silice_<parte>.py`). B se registra con `scripts/meta_silice_s5.py` y C con `scripts/meta_silice_s1.py`;
    ninguna edita `meta_silice.py`. `tests/fixtures/arquitectura.py` no es de A: lo crea B (Tarea 1). *Resuelta en el cotejo.*

---

# B. S5‑1 adelantado: Alembic en dos destinos, `preparar_base`, casos en la carpeta de datos y respaldo

> **Para quien ejecute:** usar `superpowers:subagent-driven-development` (un subagente por tarea y un revisor
> fresco). Los pasos usan casillas `- [ ]`. Esta sección es la **primera pieza de la 0.6.0** (maestro §5, RV‑1,
> RV‑3): sale de `main` con la sección A (T0: A1 → A2 → A3 → A4) fusionada, y ninguna rama de la sección C (S1) se
> abre hasta que GS5‑1 esté fusionada (S1 §13, tabla de fases). Nombres unificados con A y C en `cotejo.md`.

**Meta:** que toda base de Sílice (la de cada caso y la de la instalación) tenga su propio destino de migración
con Alembic; que una base de la 0.5.0 se adopte con respaldo previo y recargue con el mismo total, la misma
huella del informe y las mismas filas que su ficha; que el caso se elija de una lista, sin ruta libre; y que
ninguna pantalla ni la API emitan DDL para abrir un caso.

**Arquitectura:** dos paquetes nuevos fuera del núcleo: `migraciones/` (dos entornos de Alembic: `caso/` con la
revisión base congelada `caso_0001_base_0_5_0`, e `instalacion/` vacío) y `operacion/` (`config`, `base_datos`,
`respaldo`, `__main__`), sin Streamlit. `adapters/espacio/persistencia.py` publica `METADATA_ESPACIO`. La
interfaz y la API abren el caso solo con `operacion.base_datos.preparar_base`. **`core/` no cambia** (spec S5
§5.1): esta sección no lleva expediente y su rama es **sin núcleo**.

**Tecnología:** Python ≥ 3.12 (`requires-python`), `uv`, SQLAlchemy 2.0, **Alembic** (dependencia base que agrega
el PR «dependencias Sílice», tarea A2; maestro §3 y RV‑2), `sqlite3` de la biblioteca estándar (`Connection.backup`,
`PRAGMA integrity_check`), Streamlit ≥ 1.62 (`AppTest`).

**Fuentes:** [spec S5](docs/especificaciones/2026-10-11-silice-s5-producto-instalador-design.md) §1.2, §2, §5.2,
§5.3, §5.5 (DA‑S5‑4, DA‑S5‑6, DA‑S5‑7), §6.1–§6.6, §12 (RF‑96, RNF‑20), §13 (S5‑1); maestro §3.1, §4.2, §4.3, §5
(RV‑3, RV‑4, RV‑5). Esta sección no repite el spec: lo cita por sección.

## Restricciones globales de esta sección

- **Sin `core/`.** `git diff origin/main --stat -- core/` vacío en todo el rango; `core/contracts/` intocable.
  `crear_esquema` queda como está (spec S5 §5.1): lo siguen usando las pruebas en memoria y los `scripts/seed*.py`.
- **Una rama para la fase:** `inc/060-s5-1-alembic`, que sale de `origin/main` **después** de fusionar T0 completa:
  A2 «dependencias Sílice» (trae `alembic` en la base y `xlrd` en el extra `bcv`, en `pyproject.toml` y `uv.lock`),
  A3 (guardia de red `_guardia_de_red` en `tests/conftest.py`) y A4 (`scripts/meta_silice.py`, donde S5‑1 se registra
  con `scripts/meta_silice_s5.py`). PR único contra `main` al cruzar GS5‑1 (RV‑2), fusionado con
  `gh pr merge <n> --merge` (merge commit: C3 de la meta lee el orden prueba → implementación). Toca `adapters/espacio/persistencia.py` pero no `core/`: la guardia M9
  (`scripts/guardia_nucleo.py`) la acepta.
- **TDD con el rojo observado:** en cada tarea, un commit `test(...)` con la prueba en rojo y después el
  `feat(...)`/`fix(...)` que la pone en verde (maestro §6.3, comprobación común 3).
- Suite: `unset VIRTUAL_ENV; uv sync --all-extras` y luego `uv run pytest -q -W error`; 0 omitidas; ruff solo
  sobre los archivos tocados (`uv run ruff check <archivos>`; nunca `ruff format .`); nunca `pkill`/`taskkill`.
- **Nada contra `data/apu.db` ni contra la carpeta de datos real:** toda prueba usa `tmp_path` y la carpeta de
  datos temporal que fija `tests/conftest.py` (Tarea 1). La adopción de la base real la hace Eugenio a mano,
  después de la fusión (Compuerta).
- Commits en español, sin tildes en el asunto, con la línea final
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Bloque de regresión literal** (maestro §6.3) intacto: `git diff v0.5.0..HEAD` vacío sobre sus archivos.

## Decisión: dos entornos de Alembic programáticos (no `version_locations`, sin `alembic.ini`)

Se eligen **dos entornos** (`migraciones/caso/` y `migraciones/instalacion/`, cada uno con su `env.py`,
`script.py.mako` y `versions/`), configurados en código por `operacion.base_datos._configuracion`. Por qué:

1. **Cada base tiene una sola cabeza.** Con un solo entorno y dos `version_locations`, el mapa de revisiones
   tendría dos cabezas: `upgrade head` fallaría («Multiple heads») y habría que escribir `caso@head` o
   `instalacion@head` en cada llamada, con un `env.py` que elija la `MetaData` según la rama. Con dos entornos,
   `upgrade head` es siempre el mismo y la prueba de deriva compara cada destino contra **su** lista (RNF‑20).
2. **DA‑S5‑7:** cuentas y claves (S3) nunca pueden terminar en la base de un caso, que se copia y se envía.
   Dos entornos lo garantizan por construcción; dos ramas en un solo entorno, solo por disciplina.
3. **Sin `alembic.ini`:** no depende del directorio de trabajo (el repositorio en desarrollo, `{app}\codigo` en el
   producto), no hay un archivo más que copiar ni que el instalador pueda dejar desalineado, y no se ejecuta
   `fileConfig`, que reemplazaría la configuración del registro de Sílice (S5‑2). La orden `alembic` no se usa:
   todo pasa por `operacion`.

## Mapa de tareas

| Tarea | Entregable | Rol |
|---|---|---|
| 1 | `operacion.config`, paquetes `operacion` y `migraciones`, `METADATA_ESPACIO`, guardias, carpeta de datos temporal en las pruebas, `.gitignore` | sf-ingeniero-adaptadores |
| 2 | Bases de prueba de la 0.5.0 y su ficha, generadas desde `v0.5.0` (PRU‑H15, RV‑3) | sf-ingeniero-pruebas |
| 3 | Revisión base congelada, `crear_o_verificar`, capa Alembic de `operacion.base_datos`, RNF‑20 | sf-ingeniero-adaptadores |
| 4 | `operacion.respaldo`: juego con ficha, retención, restauración y eventos perdidos | sf-ingeniero-adaptadores |
| 5 | `preparar_base`, adopción, lista de casos, rutas rechazadas y `python -m operacion` | sf-ingeniero-adaptadores |
| 6 | Interfaz y API: lista de casos, `estado_caso` sin DDL, nueve páginas y la API vía `preparar_base` | sf-ingeniero-interfaz |
| 7 | ERS (RF‑96, RNF‑20), plan de pruebas, manual técnico §6 y §10.5, manual de usuario, README, `CHANGELOG.md` | sf-ingeniero-pruebas |

Orden: 1 → 2 → 3 → 4 → 5 → 6 → 7 (cada una consume firmas de la anterior).

---

### Tarea 1: andamiaje de `operacion` y `migraciones`, `METADATA_ESPACIO` y carpeta de datos

**Rama:** `inc/060-s5-1-alembic` (sale de `origin/main` con A1–A4 fusionadas; PR a `main` en GS5‑1; ver RV‑2)   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `operacion/__init__.py`, `operacion/config.py`, `migraciones/__init__.py`, `migraciones/metadatos.py`,
  `migraciones/comun.py`, `migraciones/caso/env.py`, `migraciones/caso/script.py.mako`,
  `migraciones/instalacion/env.py`, `migraciones/instalacion/script.py.mako`,
  `migraciones/instalacion/versions/.gitkeep`, `tests/fixtures/arquitectura.py`
- Modificar: `adapters/espacio/persistencia.py:45`, `:51`, `:150` (`_metadata` → `METADATA_ESPACIO`);
  `tests/unit/test_arquitectura.py:18` (`PAQUETES_FUERA_DEL_NUCLEO`); `pyproject.toml:48-55` (per-file-ignores y
  `known-first-party`); `tests/conftest.py` (tras `RUTA_BASE_REAL` y tras la fixture `_sin_variables_de_silice_del_entorno` de A1; líneas 20‑61 en `v0.5.0`, movidas por A1 y A3); `.gitignore` (al final)
- Prueba: `tests/unit/test_operacion_config.py`, `tests/unit/test_migraciones_metadatos.py`,
  `tests/unit/test_arquitectura_s5.py`

**Interfaces:**
- Consume: `alembic` instalado y con dueños `migraciones/` y `operacion/` (A2: `uv run python -c "import alembic"` sin
  error; `tests/unit/test_dependencias_silice.py::DUENOS_DE_TERCEROS`); de A1, la fixture autouse
  `_sin_variables_de_silice_del_entorno` y `ui.entorno`; de A3, la fixture de sesión `_guardia_de_red` (al final de
  `tests/conftest.py`).
- Produce:
  - `operacion.config`: `VARIABLE_DATOS = "SILICE_DATOS"`, `VARIABLE_INSTALACION = "SILICE_INSTALACION"`,
    `VARIABLE_RESPALDOS = "SILICE_RESPALDOS"`, `RAIZ: Path`, `DATOS_DESARROLLO: Path`, `BASE_ANTERIOR: Path`,
    `NOMBRE_INSTALACION = "instalacion.db"`, `CASO_POR_DEFECTO = "silice.db"`,
    `carpeta_datos(entorno: Mapping[str, str] | None = None) -> Path`, `carpeta_casos(entorno=None) -> Path`,
    `ruta_instalacion(entorno=None) -> Path`, `carpeta_respaldos(entorno=None) -> Path`,
    `ruta_caso_por_defecto(entorno=None) -> Path` (ninguna crea carpetas).
  - `adapters.espacio.persistencia.METADATA_ESPACIO: MetaData`.
  - `migraciones.metadatos.METADATAS_CASO: tuple[MetaData, ...]`, `METADATAS_INSTALACION: tuple[MetaData, ...]`.
  - `migraciones.comun`: `ErrorDeBase(ValueError)`, `BaseNoAdoptable(ErrorDeBase)` con `.diferencias`,
    `ejecutar_entorno(metadatas: Sequence[MetaData]) -> None`, `TABLA_VERSION = "alembic_version"`.
  - `tests.fixtures.arquitectura`: `RAIZ`, `archivos(paquete) -> list[Path]`, `ruta(archivo) -> str`,
    `importaciones(archivo) -> set[str]`, `llamadas(archivo, nombre) -> list[int]`.
  - Fixture autouse `_datos_de_silice_temporales` (todas las pruebas: `SILICE_DATOS` temporal).

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_operacion_config.py`:
```python
"""Carpetas de datos de Sílice (maestro §4.2; spec S5 §5.3). Ninguna función crea carpetas."""

from __future__ import annotations

from pathlib import Path

from operacion import config


def test_sin_variables_la_carpeta_de_datos_es_data_del_repositorio() -> None:
    raiz = Path(config.__file__).resolve().parents[1]
    assert config.carpeta_datos({}) == raiz / "data"
    assert config.carpeta_casos({}) == raiz / "data" / "casos"
    assert config.ruta_instalacion({}) == raiz / "data" / "instalacion.db"
    assert config.carpeta_respaldos({}) == raiz / "data" / "respaldos"
    assert config.ruta_caso_por_defecto({}) == raiz / "data" / "casos" / "silice.db"
    assert config.BASE_ANTERIOR == raiz / "data" / "apu.db"


def test_silice_datos_mueve_todo_y_no_crea_nada(tmp_path: Path) -> None:
    datos = tmp_path / "OneDrive - Personal" / "Tésis ñ" / "datos"
    entorno = {config.VARIABLE_DATOS: str(datos)}
    assert config.carpeta_casos(entorno) == datos.resolve() / "casos"
    assert config.ruta_instalacion(entorno) == datos.resolve() / "instalacion.db"
    assert config.carpeta_respaldos(entorno) == datos.resolve() / "respaldos"
    assert config.ruta_caso_por_defecto(entorno) == datos.resolve() / "casos" / "silice.db"
    assert not datos.exists()


def test_silice_instalacion_y_silice_respaldos_mandan_sobre_la_carpeta(tmp_path: Path) -> None:
    entorno = {
        config.VARIABLE_DATOS: str(tmp_path / "datos"),
        config.VARIABLE_INSTALACION: str(tmp_path / "otra" / "inst.db"),
        config.VARIABLE_RESPALDOS: str(tmp_path / "resp"),
    }
    assert config.ruta_instalacion(entorno) == (tmp_path / "otra" / "inst.db").resolve()
    assert config.carpeta_respaldos(entorno) == (tmp_path / "resp").resolve()


def test_una_variable_vacia_no_cuenta() -> None:
    assert config.carpeta_datos({config.VARIABLE_DATOS: "   "}) == config.DATOS_DESARROLLO


def test_sin_entorno_explicito_lee_os_environ(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(config.VARIABLE_DATOS, str(tmp_path))
    assert config.carpeta_datos() == tmp_path.resolve()


def test_las_pruebas_corren_con_una_carpeta_de_datos_temporal() -> None:
    """La fixture autouse de tests/conftest.py: nada llega a data/casos ni a data/respaldos."""
    assert config.carpeta_datos() != config.DATOS_DESARROLLO
```

`tests/unit/test_migraciones_metadatos.py`:
```python
"""Cada destino de migración declara su lista explícita de `MetaData` (maestro §4.2; RF-96)."""

from __future__ import annotations

from adapters.espacio import persistencia
from core.models import Base
from migraciones.metadatos import METADATAS_CASO, METADATAS_INSTALACION


def test_metadata_espacio_es_publica_y_es_la_de_las_tablas_esp() -> None:
    assert set(persistencia.METADATA_ESPACIO.tables) == {tabla.name for tabla in persistencia.TABLAS}
    assert all(tabla.metadata is persistencia.METADATA_ESPACIO for tabla in persistencia.TABLAS)


def test_el_caso_lleva_el_nucleo_y_el_espacio_y_la_instalacion_nace_vacia() -> None:
    assert len(METADATAS_CASO) == 2
    assert METADATAS_CASO[0] is Base.metadata
    assert METADATAS_CASO[1] is persistencia.METADATA_ESPACIO
    assert METADATAS_INSTALACION == ()
```

`tests/unit/test_arquitectura_s5.py`:
```python
"""Reglas de arquitectura de S5 (spec S5 §5.2; maestro §3.1 y §4.3; RV-5, RV-22).

Archivo propio de S5 (RV-2: cada spec escribe sus reglas en su archivo, con los ayudantes
compartidos de `tests/fixtures/arquitectura.py`).
"""

from __future__ import annotations

import pytest

from tests.fixtures.arquitectura import archivos, importaciones, ruta

#: Lo único de `operacion` que `ui` y `api` pueden importar (spec S5 §5.2).
PUBLICOS_DE_OPERACION = (
    "operacion.config",
    "operacion.version",
    "operacion.respaldo",
    "operacion.base_datos",
)


def _raiz(modulo: str) -> str:
    return modulo.split(".")[0]


def _infractores(paquetes: tuple[str, ...], prohibidos: set[str]) -> list[str]:
    return sorted(
        f"{ruta(archivo)}: {modulo}"
        for paquete in paquetes
        for archivo in archivos(paquete)
        for modulo in importaciones(archivo)
        if _raiz(modulo) in prohibidos
    )


@pytest.mark.parametrize("archivo", archivos("core"), ids=ruta)
def test_el_nucleo_no_importa_operacion_ni_migraciones(archivo) -> None:
    prohibidos = sorted(m for m in importaciones(archivo) if _raiz(m) in {"operacion", "migraciones"})
    assert prohibidos == []


def test_operacion_no_importa_streamlit_ui_ni_api() -> None:
    assert archivos("operacion"), "la guardia no ve operacion/"
    assert _infractores(("operacion",), {"streamlit", "ui", "api"}) == []


def test_migraciones_no_importa_streamlit_ui_api_ni_operacion() -> None:
    assert archivos("migraciones"), "la guardia no ve migraciones/"
    assert _infractores(("migraciones",), {"streamlit", "ui", "api", "operacion"}) == []


def test_ui_y_api_no_importan_migraciones() -> None:
    assert _infractores(("ui", "api"), {"migraciones"}) == []


def test_ui_y_api_solo_importan_los_modulos_publicos_de_operacion() -> None:
    infractores = sorted(
        f"{ruta(archivo)}: {modulo}"
        for paquete in ("ui", "api")
        for archivo in archivos(paquete)
        for modulo in importaciones(archivo)
        if _raiz(modulo) == "operacion"
        and modulo != "operacion"
        and not any(modulo == p or modulo.startswith(p + ".") for p in PUBLICOS_DE_OPERACION)
    )
    assert infractores == []
```

En `tests/unit/test_arquitectura.py:18`, reemplazar la línea por:
```python
PAQUETES_FUERA_DEL_NUCLEO = (
    "adapters", "ml", "ui", "api", "scripts", "tests", "operacion", "migraciones"
)
```

- [ ] **Paso 2: Correrla y ver el rojo; commit de la prueba**
Run: `unset VIRTUAL_ENV; uv sync --all-extras; uv run pytest tests/unit/test_operacion_config.py tests/unit/test_migraciones_metadatos.py tests/unit/test_arquitectura_s5.py "tests/unit/test_arquitectura.py::test_la_guardia_cubre_todo_paquete_de_primer_nivel_fuera_del_nucleo" -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'operacion'` (y `migraciones`, `tests.fixtures.arquitectura`)
y `assert {...} == {..., 'migraciones', 'operacion'}` en la guardia de paquetes.
```bash
git add tests/unit/test_operacion_config.py tests/unit/test_migraciones_metadatos.py tests/unit/test_arquitectura_s5.py tests/unit/test_arquitectura.py
git commit -m "test(operacion): carpeta de datos, destinos de migracion y guardias de S5 (rojo)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/__init__.py`:
```python
"""Operación del producto Sílice, fuera del núcleo y sin Streamlit (spec S5 §5.2).

`config` (carpetas de datos), `base_datos` (`preparar_base`, lista de casos), `respaldo` (juegos de
respaldo y restauración) y la orden `python -m operacion`. Importa `core.catalog`, `migraciones`,
SQLAlchemy, Alembic y la biblioteca estándar; nunca `streamlit`, `ui` ni `api`
(`tests/unit/test_arquitectura_s5.py`).
"""
```

`operacion/config.py`:
```python
"""Dónde viven los datos de Sílice (maestro §4.2; spec S5 §5.3).

En el producto, el lanzador (S5-2) fija `SILICE_DATOS` (`%LOCALAPPDATA%\\Silice\\datos`),
`SILICE_INSTALACION` y `SILICE_RESPALDOS` (`%LOCALAPPDATA%\\Silice\\respaldos`). En desarrollo,
`SILICE_DATOS` vale por defecto `data/` del repositorio, con la misma disposición: `instalacion.db`,
`casos/`, `paquetes/`, `codigo_instalacion.txt` y `respaldos/` (todos en `.gitignore`).

Las funciones reciben el entorno para que las pruebas no dependan de `os.environ`, y **ninguna crea
carpetas**: las crea quien escribe.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

VARIABLE_DATOS = "SILICE_DATOS"
VARIABLE_INSTALACION = "SILICE_INSTALACION"
VARIABLE_RESPALDOS = "SILICE_RESPALDOS"

RAIZ = Path(__file__).resolve().parents[1]
DATOS_DESARROLLO = RAIZ / "data"
NOMBRE_INSTALACION = "instalacion.db"
CARPETA_CASOS = "casos"
CARPETA_RESPALDOS = "respaldos"
CASO_POR_DEFECTO = "silice.db"
#: La base de trabajo de las versiones 0.1 a 0.5 (`scripts/seed.py`, `ui/caso.py`, `api`). No se abre
#: en su sitio: se adopta COPIÁNDOLA a la carpeta de casos con `python -m operacion adoptar`.
BASE_ANTERIOR = DATOS_DESARROLLO / "apu.db"


def _valor(nombre: str, entorno: Mapping[str, str] | None) -> str:
    fuente = os.environ if entorno is None else entorno
    return fuente.get(nombre, "").strip()


def _ruta(valor: str) -> Path:
    return Path(valor).expanduser().resolve()


def carpeta_datos(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_DATOS` si está; si no, `data/` del repositorio."""
    valor = _valor(VARIABLE_DATOS, entorno)
    return _ruta(valor) if valor else DATOS_DESARROLLO


def carpeta_casos(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_datos(entorno) / CARPETA_CASOS


def ruta_instalacion(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_INSTALACION` si está; si no, `instalacion.db` de la carpeta de datos."""
    valor = _valor(VARIABLE_INSTALACION, entorno)
    return _ruta(valor) if valor else carpeta_datos(entorno) / NOMBRE_INSTALACION


def carpeta_respaldos(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_RESPALDOS` si está; si no, `respaldos/` dentro de la carpeta de datos."""
    valor = _valor(VARIABLE_RESPALDOS, entorno)
    return _ruta(valor) if valor else carpeta_datos(entorno) / CARPETA_RESPALDOS


def ruta_caso_por_defecto(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_casos(entorno) / CASO_POR_DEFECTO
```

`migraciones/__init__.py`:
```python
"""Los dos destinos de migración de Sílice con Alembic (RF-96, RNF-20; maestro §4.2; spec S5 §6).

`caso/` migra la base de cada caso; `instalacion/` la base de la instalación (vacía hasta S3-1). Sin
`alembic.ini`: los corre solo `operacion.base_datos`, que arma la configuración y entrega la
conexión. Nunca importa `streamlit`, `ui`, `api` ni `operacion`.
"""
```

`migraciones/metadatos.py`:
```python
"""La lista explícita de `MetaData` de cada destino (maestro §4.2; RF-96, RNF-20).

`METADATAS_CASO` crece con `paquete` (S3) y `asistente` (S4); `METADATAS_INSTALACION` nace vacía y
la llena S3-1 con `seguridad.modelo`. Toda `MetaData` con tablas del repositorio está en una de las
dos: lo comprueba `tests/integration/test_migraciones.py`.
"""

from __future__ import annotations

from sqlalchemy import MetaData

from adapters.espacio.persistencia import METADATA_ESPACIO
from core.models import Base

METADATAS_CASO: tuple[MetaData, ...] = (Base.metadata, METADATA_ESPACIO)
METADATAS_INSTALACION: tuple[MetaData, ...] = ()
```

`migraciones/comun.py` (Tarea 3 le agrega el resto):
```python
"""Lo compartido por los dos entornos de Alembic y sus revisiones (spec S5 §6.1; DA-S5-4, DA-S5-7)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import MetaData

TABLA_VERSION = "alembic_version"


class ErrorDeBase(ValueError):  # noqa: N818
    """Una base que Sílice no puede abrir; el mensaje dice qué pasó y qué hacer.

    Es un `ValueError`: las pantallas que ya muestran `ValueError` como mensaje (no como traza) la
    muestran igual. `operacion.base_datos` la reexporta junto con sus subclases.
    """


class BaseNoAdoptable(ErrorDeBase):  # noqa: N818
    """La base tiene tablas del esquema con otra forma: no se adopta ni se toca (spec S5 §6.4)."""

    def __init__(self, diferencias: Sequence[str]) -> None:
        self.diferencias = tuple(diferencias)
        super().__init__(
            "Esta base no se puede adoptar: sus tablas no tienen la forma que Sílice espera ("
            + "; ".join(self.diferencias)
            + "). No se modificó. Vuelva a sembrarla o pida ayuda (manual técnico §10.5)."
        )


def ejecutar_entorno(metadatas: Sequence[MetaData]) -> None:
    """Cuerpo de cada `env.py`: solo en línea, con la conexión que pone `operacion.base_datos` en
    `config.attributes["connection"]`; modo batch porque SQLite casi no tiene `ALTER` (§6.1)."""
    from alembic import context

    conexion = context.config.attributes.get("connection")
    if conexion is None:
        raise RuntimeError(
            "Las migraciones de Sílice corren solo desde operacion.base_datos, con una conexión "
            "abierta; la orden `alembic` no se usa (DA-S5-7)."
        )
    context.configure(
        connection=conexion,
        target_metadata=list(metadatas),
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()
```

`migraciones/caso/env.py`:
```python
"""Entorno de Alembic de la base del caso (RF-96): `core.models` y `METADATA_ESPACIO`."""

from migraciones.comun import ejecutar_entorno
from migraciones.metadatos import METADATAS_CASO

ejecutar_entorno(METADATAS_CASO)
```

`migraciones/instalacion/env.py`:
```python
"""Entorno de Alembic de la base de la instalación (RF-96): vacío hasta S3-1 (`ins_0001_seguridad`)."""

from migraciones.comun import ejecutar_entorno
from migraciones.metadatos import METADATAS_INSTALACION

ejecutar_entorno(METADATAS_INSTALACION)
```

`migraciones/caso/script.py.mako` y `migraciones/instalacion/script.py.mako` (mismo contenido):
```mako
"""${message}

Revisión ${up_revision}; anterior: ${down_revision | comma,n}. Creada: ${create_date}.
"""

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

`migraciones/instalacion/versions/.gitkeep`: archivo vacío (Alembic necesita la carpeta; ignora lo que no es `.py`).

`adapters/espacio/persistencia.py`: en la línea 45 reemplazar `_metadata = MetaData()` por
```python
#: El esquema `esp_*` del adaptador: público porque es parte del destino de migración del caso
#: (`migraciones/metadatos.py`, maestro §4.2). Antes, `_metadata` privada.
METADATA_ESPACIO = MetaData()
```
y en las líneas 51 (`_metadata,` dentro de `_tabla`) y 150 (`_metadata.create_all(destino)`) cambiar
`_metadata` por `METADATA_ESPACIO`.

`tests/fixtures/arquitectura.py`:
```python
"""Ayudantes compartidos de las reglas de arquitectura de cada spec de Sílice (maestro §3.1, RV-2).

Cada spec escribe sus reglas en su propio archivo (`tests/unit/test_arquitectura_s5.py`, …) y lee las
importaciones con estas funciones. `tests/unit/test_arquitectura.py` conserva las suyas (archivo
caliente: no se reescribe).
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
_TIPADO = {"TYPE_CHECKING", "typing.TYPE_CHECKING"}


def archivos(paquete: str) -> list[Path]:
    carpeta = RAIZ / paquete
    return sorted(carpeta.rglob("*.py")) if carpeta.is_dir() else []


def ruta(archivo: Path) -> str:
    return archivo.relative_to(RAIZ).as_posix()


def importaciones(archivo: Path) -> set[str]:
    """Módulos que `archivo` importa en tiempo de ejecución (fuera de `if TYPE_CHECKING:`), también
    los perezosos; `from a import b` cuenta `a` y `a.b` (b puede ser un submódulo)."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    solo_tipado = {
        id(nodo)
        for bloque in ast.walk(arbol)
        if isinstance(bloque, ast.If) and ast.unparse(bloque.test) in _TIPADO
        for sentencia in bloque.body
        for nodo in ast.walk(sentencia)
    }
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if id(nodo) in solo_tipado:
            continue
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module)
            nombres.update(f"{nodo.module}.{alias.name}" for alias in nodo.names)
    return nombres


def llamadas(archivo: Path, nombre: str) -> list[int]:
    """Líneas donde `archivo` llama a `nombre(...)` o a `<algo>.nombre(...)`."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    lineas = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            funcion = nodo.func
            if (isinstance(funcion, ast.Name) and funcion.id == nombre) or (
                isinstance(funcion, ast.Attribute) and funcion.attr == nombre
            ):
                lineas.append(nodo.lineno)
    return sorted(lineas)
```

`tests/conftest.py`: después de `RUTA_BASE_REAL` (línea 20) agregar
```python
#: La base de la instalación de desarrollo (S5-1, maestro §4.2): ninguna prueba la crea ni la toca.
RUTA_INSTALACION_REAL = RUTA_BASE_REAL.parent / "instalacion.db"
```
y después de `_sin_variables_de_silice_del_entorno` (la fixture que A1 hizo de `_sin_caso_del_entorno`; antes de la
`_guardia_de_red` de A3, que queda al final del archivo) agregar
```python
@pytest.fixture(scope="session", autouse=True)
def _instalacion_real_intacta():
    """Falla la sesión si alguna prueba creó o modificó `data/instalacion.db`."""
    yield from vigilar_base(RUTA_INSTALACION_REAL)


@pytest.fixture(autouse=True)
def _datos_de_silice_temporales(monkeypatch, tmp_path_factory):
    """Toda prueba trabaja con una carpeta de datos temporal (`SILICE_DATOS`): nada llega a
    `data/casos/`, `data/respaldos/` ni `data/instalacion.db` (spec S5 §12)."""
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path_factory.mktemp("silice_datos")))
    monkeypatch.delenv("SILICE_INSTALACION", raising=False)
    monkeypatch.delenv("SILICE_RESPALDOS", raising=False)
```

`pyproject.toml`: en `[tool.ruff.lint.per-file-ignores]` (línea 48) agregar
```toml
# Revisiones de Alembic congeladas: el DDL literal de SQLite va tal cual (spec S5 §6.1).
"migraciones/*/versions/*.py" = ["E501"]
```
y la línea 55 queda
```toml
known-first-party = ["core", "adapters", "ml", "ui", "api", "tests", "scripts", "operacion", "migraciones"]
```

`.gitignore`, al final:
```gitignore
# Carpeta de datos de desarrollo de Silice: SILICE_DATOS por defecto (maestro §4.2; spec S5 §5.3)
data/instalacion.db
data/codigo_instalacion.txt
data/paquetes/
data/casos/
data/respaldos/
data/eventos_perdidos_*.json
# Copias de trabajo de una migracion interrumpida (operacion.base_datos)
*.migrando
```

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_operacion_config.py tests/unit/test_migraciones_metadatos.py tests/unit/test_arquitectura_s5.py tests/unit/test_arquitectura.py tests/integration/test_espacio_persistencia.py -v -W error`
Esperado: PASS. Luego `uv run pytest -q -W error` (toda la suite: la fixture autouse no cambia nada más) y
`uv run ruff check operacion migraciones adapters/espacio/persistencia.py tests/fixtures/arquitectura.py tests/conftest.py tests/unit/test_operacion_config.py tests/unit/test_migraciones_metadatos.py tests/unit/test_arquitectura_s5.py tests/unit/test_arquitectura.py`.

- [ ] **Paso 5: Commit**
```bash
git add operacion/__init__.py operacion/config.py migraciones/__init__.py migraciones/metadatos.py migraciones/comun.py migraciones/caso/env.py migraciones/caso/script.py.mako migraciones/instalacion/env.py migraciones/instalacion/script.py.mako migraciones/instalacion/versions/.gitkeep adapters/espacio/persistencia.py tests/fixtures/arquitectura.py tests/conftest.py pyproject.toml .gitignore
git commit -m "feat(operacion): carpeta de datos, destinos de migracion y METADATA_ESPACIO publica" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 2: bases de prueba de la 0.5.0 y su ficha, generadas desde `v0.5.0`

**Rama:** `inc/060-s5-1-alembic` (sale de `main`; PR a `main`; ver RV-2)   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `scripts/generar_base_prueba.py`, `tests/fixtures/bases_prueba.py`, `.gitattributes`,
  `tests/fixtures/bases/v0_5_0/demo.db`, `tests/fixtures/bases/v0_5_0/of001.db`,
  `tests/fixtures/bases/v0_5_0/ti001.db`, `tests/fixtures/bases/v0_5_0/ficha.json` (los cuatro **generados** con el
  código de `v0.5.0`, Paso 3)
- Modificar: `.gitignore` (al final), `scripts/README.md` (sección nueva al final)
- Prueba: `tests/unit/test_generar_base_prueba.py`, `tests/integration/test_base_prueba_v0_5_0.py`

**Interfaces:**
- Consume: `tests.fixtures.hoja_en_base.plantilla_of001(ruta) -> Path`, `plantilla_ti001(ruta) -> Path`,
  `scripts.seed_demo.main(argv) -> int`, `core.budget.cargar_elaboracion(session, proyecto_nombre, codigo, catalogo)`
  (las cuatro existen en `v0.5.0`).
- Produce:
  - `scripts.generar_base_prueba`: `NOMBRE_FICHA = "ficha.json"`, `TABLA_VERSION`, `CONSTRUCTORES: dict[str,
    Callable[[Path], object]]` (`demo.db`, `of001.db`, `ti001.db`), `filas_por_tabla(base) -> dict[str, int]`,
    `revision_alembic(base) -> str | None`, `presupuestos(base) -> list[dict[str, str]]`,
    `ficha_de(base) -> dict[str, Any]`, `main(argv=None) -> int`.
  - `tests.fixtures.bases_prueba`: `CARPETA`, `carpeta_version(version) -> Path`, `ficha(version) -> dict`,
    `nombres(version) -> list[str]`, `copiar_base(version, nombre, destino) -> Path`,
    `diferencias_con_ficha(ruta, esperado: dict) -> list[str]`,
    `crear_base_futura(ruta, revision="caso_9999_futura") -> Path`.
  - Ficha: `{"version", "etiqueta", "commit", "bases": {<nombre>: {"revision_alembic", "sha256_base",
    "filas_por_tabla", "presupuestos": [{"proyecto", "codigo", "total", "huella_informe"}]}}}`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_generar_base_prueba.py`:
```python
"""El generador de las bases de prueba de cada versión y de su ficha (RV-3, PRU-H15)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from scripts import generar_base_prueba as generador


def _base_minima(ruta: Path) -> Path:
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("CREATE TABLE a (id INTEGER PRIMARY KEY)")
        conexion.executemany("INSERT INTO a VALUES (?)", [(1,), (2,)])
        conexion.execute("CREATE TABLE b (x TEXT)")
        conexion.commit()
    return ruta


def test_filas_por_tabla_cuenta_todas_las_tablas(tmp_path: Path) -> None:
    assert generador.filas_por_tabla(_base_minima(tmp_path / "m.db")) == {"a": 2, "b": 0}


def test_la_revision_es_none_sin_alembic_y_la_fila_con_alembic(tmp_path: Path) -> None:
    base = _base_minima(tmp_path / "m.db")
    assert generador.revision_alembic(base) is None
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        conexion.execute("INSERT INTO alembic_version VALUES ('caso_0001_base_0_5_0')")
        conexion.commit()
    assert generador.revision_alembic(base) == "caso_0001_base_0_5_0"


def test_los_tres_casos_de_la_base_de_prueba() -> None:
    assert list(generador.CONSTRUCTORES) == ["demo.db", "of001.db", "ti001.db"]


def test_se_niega_a_reescribir_una_base_de_prueba(tmp_path: Path, capsys) -> None:
    (tmp_path / "demo.db").write_bytes(b"")
    codigo = generador.main(
        ["--salida", str(tmp_path), "--version", "0.5.0", "--etiqueta", "v0.5.0", "--commit", "x"]
    )
    assert codigo == 1
    assert "se genera una sola vez" in capsys.readouterr().err
```

`tests/integration/test_base_prueba_v0_5_0.py`:
```python
"""Las bases de prueba de la 0.5.0 y su ficha, generadas con el código de `v0.5.0` (RV-3, PRU-H15).

Fijan que los archivos versionados son los de la ficha. Las pruebas de adopción (Tarea 5) los llevan
a `head` y comparan contra esta ficha, nunca contra un recálculo con el código nuevo.
"""

from __future__ import annotations

import hashlib

import pytest

from tests.fixtures import bases_prueba

FICHA = bases_prueba.ficha("0.5.0")
NOMBRE_OF001 = "OF-001: oficina con baño, cocineta y puestos (caso de prueba)"
NOMBRE_TI001 = "TI-001: telecomunicaciones (caso de prueba)"


def test_la_ficha_es_de_la_etiqueta_v0_5_0() -> None:
    assert (FICHA["version"], FICHA["etiqueta"]) == ("0.5.0", "v0.5.0")
    assert FICHA["commit"].startswith("8610053")
    assert sorted(FICHA["bases"]) == ["demo.db", "of001.db", "ti001.db"]


@pytest.mark.parametrize("nombre", bases_prueba.nombres("0.5.0"))
def test_cada_base_versionada_es_la_de_su_ficha(nombre: str) -> None:
    base = bases_prueba.carpeta_version("0.5.0") / nombre
    datos = FICHA["bases"][nombre]
    assert hashlib.sha256(base.read_bytes()).hexdigest() == datos["sha256_base"]
    assert datos["revision_alembic"] is None
    assert "alembic_version" not in datos["filas_por_tabla"]
    assert datos["presupuestos"], f"{nombre} no trae ningún presupuesto"
    for presupuesto in datos["presupuestos"]:
        assert presupuesto["total"] and len(presupuesto["huella_informe"]) == 64


def test_las_bases_cubren_el_espacio_la_demostracion_y_ti001() -> None:
    of001 = FICHA["bases"]["of001.db"]
    assert of001["filas_por_tabla"]["esp_ambientes"] > 0
    assert len(of001["filas_por_tabla"]) == 33  # 25 tablas de core/models + 8 esp_* (spec S5 §6.1)
    assert (NOMBRE_OF001, "001") in {(p["proyecto"], p["codigo"]) for p in of001["presupuestos"]}
    assert "DEMO-001" in {p["codigo"] for p in FICHA["bases"]["demo.db"]["presupuestos"]}
    ti001 = {(p["proyecto"], p["codigo"]) for p in FICHA["bases"]["ti001.db"]["presupuestos"]}
    assert (NOMBRE_TI001, "001") in ti001
```

- [ ] **Paso 2: Correrla y ver el rojo; commit de la prueba**
Run: `uv run pytest tests/unit/test_generar_base_prueba.py tests/integration/test_base_prueba_v0_5_0.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'scripts.generar_base_prueba'` y
`No module named 'tests.fixtures.bases_prueba'`.
```bash
git add tests/unit/test_generar_base_prueba.py tests/integration/test_base_prueba_v0_5_0.py
git commit -m "test(migraciones): bases de prueba de la 0.5.0 con su ficha (rojo)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima y generación desde `v0.5.0`**

`scripts/generar_base_prueba.py`:
```python
"""Genera las bases de prueba de una versión y su ficha (RV-3, PRU-H15; spec S5 §2 y §12).

Se corre con el código DE LA ETIQUETA, nunca con el de la rama: la etiqueta se extrae con
`git archive` en una carpeta aparte, este script se copia a su `scripts/` y se corre allí
(procedimiento en docs/manual_tecnico.md §10.5). La ficha (total literal, huella del informe y filas
por tabla de cada base) queda escrita con ese código: las pruebas de adopción comparan contra ella,
nunca contra un recálculo con el código nuevo.

Tres bases, cada una en su archivo (casos construidos, NORMAS.md §1):

- `demo.db`: línea base de la clínica, la demostración y `DEMO-001` (`scripts.seed_demo`);
- `of001.db`: la oficina OF-001 con su espacio `esp_*` y la versión `001`
  (`tests.fixtures.hoja_en_base.plantilla_of001`);
- `ti001.db`: TI-001 con su versión `001` y su plan (`plantilla_ti001`).

Desde la 0.6.0 cada base nace por `operacion.base_datos.preparar_base` (en `head`); en la 0.5.0 ese
módulo no existe y la crea `create_all`, como la creaba la 0.5.0.

Uso, dentro del árbol de la etiqueta:
    uv run python scripts/generar_base_prueba.py --salida <repo>/tests/fixtures/bases/v0_5_0 \
        --version 0.5.0 --etiqueta v0.5.0 --commit <sha de la etiqueta>
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
import sys
from collections.abc import Callable, Sequence
from contextlib import closing
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import select  # noqa: E402

from core import models  # noqa: E402
from core.budget import cargar_elaboracion  # noqa: E402
from core.catalog import Catalogo, abrir_sesion, crear_motor  # noqa: E402
from scripts import seed_demo  # noqa: E402
from tests.fixtures.hoja_en_base import plantilla_of001, plantilla_ti001  # noqa: E402

NOMBRE_FICHA = "ficha.json"
TABLA_VERSION = "alembic_version"


def _demo(ruta: Path) -> None:
    if seed_demo.main(["--db", str(ruta)]) != 0:
        raise RuntimeError(f"scripts.seed_demo no pudo sembrar {ruta}")


CONSTRUCTORES: dict[str, Callable[[Path], object]] = {
    "demo.db": _demo,
    "of001.db": plantilla_of001,
    "ti001.db": plantilla_ti001,
}


def _solo_lectura(base: Path) -> sqlite3.Connection:
    return sqlite3.connect(base.resolve().as_uri() + "?mode=ro", uri=True)


def filas_por_tabla(base: Path) -> dict[str, int]:
    """Filas de cada tabla de la base (incluida `alembic_version` si la tiene)."""
    with closing(_solo_lectura(base)) as conexion:
        tablas = [
            nombre
            for (nombre,) in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            tabla: conexion.execute(f'SELECT count(*) FROM "{tabla}"').fetchone()[0]
            for tabla in tablas
        }


def revision_alembic(base: Path) -> str | None:
    with closing(_solo_lectura(base)) as conexion:
        existe = conexion.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (TABLA_VERSION,)
        ).fetchone()
        if existe is None:
            return None
        fila = conexion.execute(f"SELECT version_num FROM {TABLA_VERSION}").fetchone()
    return None if fila is None else str(fila[0])


def presupuestos(base: Path) -> list[dict[str, str]]:
    """Cada versión guardada, recargada con `cargar_elaboracion`: total literal y huella SHA-256 del
    informe en Markdown (el mismo texto que juzga RNF-04)."""
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            filas = sesion.execute(
                select(models.Proyecto.nombre, models.Presupuesto.codigo)
                .where(models.Presupuesto.proyecto_id == models.Proyecto.id)
                .order_by(models.Presupuesto.id)
            ).all()
            resultado = []
            for proyecto, codigo in filas:
                elaboracion = cargar_elaboracion(sesion, proyecto, codigo, Catalogo(sesion))
                informe = elaboracion.informe.a_markdown().encode("utf-8")
                resultado.append(
                    {
                        "proyecto": proyecto,
                        "codigo": codigo,
                        "total": str(elaboracion.presupuesto.total),
                        "huella_informe": hashlib.sha256(informe).hexdigest(),
                    }
                )
            return resultado
    finally:
        motor.dispose()


def ficha_de(base: Path) -> dict[str, Any]:
    """La ficha de una base, con el código que esté corriendo."""
    return {
        "revision_alembic": revision_alembic(base),
        "sha256_base": hashlib.sha256(base.read_bytes()).hexdigest(),
        "filas_por_tabla": filas_por_tabla(base),
        "presupuestos": presupuestos(base),
    }


def _preparar_si_existe(ruta: Path) -> None:
    """Desde la 0.6.0 la base nace en `head` por `preparar_base`; en la 0.5.0 no existe."""
    if importlib.util.find_spec("operacion") is not None:
        from operacion.base_datos import preparar_base

        preparar_base(ruta)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--salida", type=Path, required=True)
    analizador.add_argument("--version", required=True, help="p. ej. 0.5.0")
    analizador.add_argument("--etiqueta", required=True, help="p. ej. v0.5.0")
    analizador.add_argument("--commit", required=True, help="sha del commit de la etiqueta")
    argumentos = analizador.parse_args(argv)
    salida: Path = argumentos.salida
    ocupados = [n for n in (*CONSTRUCTORES, NOMBRE_FICHA) if (salida / n).exists()]
    if ocupados:
        print(
            f"{salida} ya tiene {ocupados}: la base de prueba de una versión se genera una sola "
            "vez, en su compuerta (RV-3).",
            file=sys.stderr,
        )
        return 1
    salida.mkdir(parents=True, exist_ok=True)
    bases: dict[str, Any] = {}
    for nombre, construir in CONSTRUCTORES.items():
        ruta = salida / nombre
        _preparar_si_existe(ruta)
        construir(ruta)
        bases[nombre] = ficha_de(ruta)
    ficha = {
        "version": argumentos.version,
        "etiqueta": argumentos.etiqueta,
        "commit": argumentos.commit,
        "bases": bases,
    }
    (salida / NOMBRE_FICHA).write_text(
        json.dumps(ficha, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Bases de prueba y ficha de {argumentos.etiqueta} en {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`tests/fixtures/bases_prueba.py`:
```python
"""Bases de prueba de cada versión con su ficha (RV-3, PRU-H15; spec S5 §2 y §12).

`tests/fixtures/bases/v<X_Y_Z>/` guarda las bases que generó `scripts/generar_base_prueba.py` con el
código de la etiqueta `vX.Y.Z`, y su `ficha.json`. Las pruebas COPIAN la base (nunca la abren en su
sitio) y comparan con `diferencias_con_ficha`, que recalcula con el código de hoy lo mismo que el
generador escribió con el de la etiqueta.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from scripts.generar_base_prueba import NOMBRE_FICHA, TABLA_VERSION, ficha_de

CARPETA = Path(__file__).resolve().parent / "bases"


def carpeta_version(version: str) -> Path:
    return CARPETA / ("v" + version.replace(".", "_"))


def ficha(version: str) -> dict[str, Any]:
    return json.loads((carpeta_version(version) / NOMBRE_FICHA).read_text(encoding="utf-8"))


def nombres(version: str) -> list[str]:
    return sorted(ficha(version)["bases"])


def copiar_base(version: str, nombre: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(carpeta_version(version) / nombre, destino)
    return destino


def diferencias_con_ficha(ruta: Path, esperado: dict[str, Any]) -> list[str]:
    """Lo que no cuadra entre la base (recargada con el código de hoy) y su ficha: filas de cada
    tabla de la ficha (salvo `alembic_version`), total literal y huella del informe."""
    actual = ficha_de(ruta)
    diferencias = [
        f"{tabla}: {actual['filas_por_tabla'].get(tabla)} filas; la ficha dice {filas}"
        for tabla, filas in sorted(esperado["filas_por_tabla"].items())
        if tabla != TABLA_VERSION and actual["filas_por_tabla"].get(tabla) != filas
    ]
    if actual["presupuestos"] != esperado["presupuestos"]:
        diferencias.append(f"presupuestos: {actual['presupuestos']} != {esperado['presupuestos']}")
    return diferencias


def crear_base_futura(ruta: Path, revision: str = "caso_9999_futura") -> Path:
    """Una base con una revisión que este código no conoce: la de un Sílice más nuevo (§6.4, 3d)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
        conexion.execute("INSERT INTO alembic_version VALUES (?)", (revision,))
        conexion.execute("CREATE TABLE partida (id INTEGER PRIMARY KEY)")
        conexion.commit()
    return ruta
```

`.gitignore`, al final:
```gitignore
# Bases de prueba de cada version, con su ficha (RV-3, PRU-H15): SI se versionan
!tests/fixtures/bases/*/*.db
```

`.gitattributes` (nuevo):
```gitattributes
# Bases de prueba de cada version: binarias, sin conversion de fin de linea (su SHA-256 esta en la ficha)
tests/fixtures/bases/*/*.db binary
```

`scripts/README.md`, al final:
```markdown
## Bases de prueba y migraciones (Sílice, desde la 0.6.0)

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `generar_base_prueba.py` | genera, **con el código de una etiqueta**, las bases de prueba `demo.db`, `of001.db` y `ti001.db` de esa versión y su `ficha.json` (filas por tabla, total literal y huella del informe) en `tests/fixtures/bases/v<X_Y_Z>/`; se niega a reescribirlas | S5‑1 · RV‑3 |
```

**Generación (una sola vez, con el código de `v0.5.0`)**, en Git Bash desde la raíz del worktree:
```bash
REPO="$(pwd)"
V050="${TMPDIR:-/tmp}/silice-v0.5.0"
rm -rf "$V050" && mkdir -p "$V050"
git archive v0.5.0 | tar -x -C "$V050"
cp scripts/generar_base_prueba.py "$V050/scripts/"
(
  cd "$V050" && unset VIRTUAL_ENV \
  && export UV_PROJECT_ENVIRONMENT="$V050/.venv" \
  && uv sync --frozen --all-extras \
  && uv run --frozen python scripts/generar_base_prueba.py \
       --salida "$REPO/tests/fixtures/bases/v0_5_0" --version 0.5.0 --etiqueta v0.5.0 \
       --commit "$(git -C "$REPO" rev-parse 'v0.5.0^{commit}')"
)
```
`UV_PROJECT_ENVIRONMENT` se fija a propósito: si el usuario lo tiene como variable global (README, nota de
OneDrive), `uv sync` en el árbol de la etiqueta pisaría el `.venv` del worktree. El commit esperado empieza
por `8610053`.

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_generar_base_prueba.py tests/integration/test_base_prueba_v0_5_0.py tests/unit/test_scripts_documentados.py tests/unit/test_arquitectura.py -v -W error`
Esperado: PASS. `git status --short tests/fixtures/bases` muestra los cuatro archivos (la negación del
`.gitignore` funciona). `uv run ruff check scripts/generar_base_prueba.py tests/fixtures/bases_prueba.py tests/unit/test_generar_base_prueba.py tests/integration/test_base_prueba_v0_5_0.py`.

- [ ] **Paso 5: Commit**
```bash
git add scripts/generar_base_prueba.py tests/fixtures/bases_prueba.py tests/fixtures/bases/v0_5_0/demo.db tests/fixtures/bases/v0_5_0/of001.db tests/fixtures/bases/v0_5_0/ti001.db tests/fixtures/bases/v0_5_0/ficha.json .gitignore .gitattributes scripts/README.md
git commit -m "test(migraciones): bases de prueba de v0.5.0 y su ficha generadas con el codigo de la etiqueta" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 3: revisión base congelada, `crear_o_verificar`, capa Alembic de `operacion.base_datos` y RNF‑20

**Rama:** `inc/060-s5-1-alembic` (sale de `main`; PR a `main`; ver RV-2)   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `scripts/congelar_esquema.py`, `migraciones/caso/versions/caso_0001_base_0_5_0.py` (**generado** por
  `scripts/congelar_esquema.py` en el Paso 3 y revisado a mano), `operacion/base_datos.py`
- Modificar: `migraciones/comun.py` (agregar al final), `scripts/README.md` (fila en la sección de la Tarea 2)
- Prueba: `tests/unit/test_congelar_esquema.py`, `tests/integration/test_migraciones.py`

**Interfaces:**
- Consume: `migraciones.comun.ErrorDeBase`, `BaseNoAdoptable`, `TABLA_VERSION`, `ejecutar_entorno`;
  `migraciones.metadatos.METADATAS_CASO`, `METADATAS_INSTALACION`; `tests.fixtures.bases_prueba.carpeta_version`,
  `nombres`, `copiar_base`.
- Produce:
  - `migraciones.comun`: `TablaCongelada(nombre: str, ddl: str, indices: tuple[str, ...] = ())`,
    `describir_tabla(inspector, nombre) -> dict[str, Any]`, `instantanea_esquema(conexion) -> dict[str, dict]`,
    `crear_o_verificar(conexion, tablas: Sequence[TablaCongelada]) -> None`,
    `borrar_tablas(conexion, tablas) -> None`, `metadata_unida(metadatas) -> MetaData`.
  - `scripts.congelar_esquema`: `leer_esquema(base) -> list[tuple[str, str, tuple[str, ...]]]`,
    `renderizar(esquema, *, revision, version, commit) -> str`, `main(argv=None) -> int`.
  - `operacion.base_datos`: `CARPETA_MIGRACIONES: Path`, `Destino(StrEnum)` (`CASO = "caso"`,
    `INSTALACION = "instalacion"`), `MigracionFallida(ErrorDeBase)`, `_configuracion(destino) -> Config`,
    `_guion(destino) -> ScriptDirectory` (con `functools.cache`), `revision_head(destino) -> str | None`,
    `revisiones_conocidas(destino) -> frozenset[str]`, `revisiones_en_orden(destino) -> list[str]`,
    `motor_de_migracion(ruta) -> Engine`, `aplicar_revisiones(ruta, destino, objetivo="head") -> None`,
    `deshacer_revisiones(ruta, destino, objetivo="base") -> None`.
  - Revisión `caso_0001_base_0_5_0` (`down_revision = None`) con `TABLAS: tuple[TablaCongelada, ...]` (33).

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_congelar_esquema.py`:
```python
"""El congelador de la revisión base: DDL literal de SQLite, en orden de creación (spec S5 §6.1)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from scripts import congelar_esquema as congelar


def _base(ruta: Path) -> Path:
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "CREATE TABLE padre (\n\tid INTEGER NOT NULL, \n\tnombre VARCHAR(40), \n"
            "\tPRIMARY KEY (id)\n)"
        )
        conexion.execute("CREATE INDEX ix_padre_nombre ON padre (nombre)")
        conexion.execute("CREATE TABLE hijo (padre_id INTEGER REFERENCES padre (id))")
        conexion.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        conexion.commit()
    return ruta


def test_leer_el_esquema_conserva_orden_ddl_e_indices_y_omite_alembic(tmp_path: Path) -> None:
    esquema = congelar.leer_esquema(_base(tmp_path / "m.db"))
    assert [tabla for tabla, _, _ in esquema] == ["padre", "hijo"]
    assert esquema[0][1].startswith("CREATE TABLE padre (\n\tid INTEGER NOT NULL")
    assert esquema[0][2] == ("CREATE INDEX ix_padre_nombre ON padre (nombre)",)
    assert esquema[1][2] == ()


def test_la_revision_renderizada_devuelve_el_mismo_ddl(tmp_path: Path) -> None:
    esquema = congelar.leer_esquema(_base(tmp_path / "m.db"))
    texto = congelar.renderizar(esquema, revision="prueba_0001", version="9.9.9", commit="abc1234")
    espacio: dict = {}
    exec(compile(texto, "prueba_0001.py", "exec"), espacio)
    assert espacio["revision"] == "prueba_0001" and espacio["down_revision"] is None
    assert [(t.nombre, t.ddl, t.indices) for t in espacio["TABLAS"]] == esquema


def test_no_pisa_una_revision_ya_congelada(tmp_path: Path, capsys) -> None:
    base = _base(tmp_path / "m.db")
    salida = tmp_path / "prueba_0001.py"
    salida.write_text("congelada\n", encoding="utf-8")
    argv = ["--base", str(base), "--revision", "prueba_0001", "--version", "9.9.9",
            "--commit", "abc1234", "--salida", str(salida)]
    assert congelar.main(argv) == 1
    assert salida.read_text(encoding="utf-8") == "congelada\n"
    assert "congelada" in capsys.readouterr().err
```

`tests/integration/test_migraciones.py`:
```python
"""Alembic en dos destinos: revisión base exacta de la 0.5.0, deriva cero (RNF-20) y vuelta atrás
de cada revisión (RF-96; spec S5 §6.1, §6.2 y §12; DA-S5-6)."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.orm import Session

from adapters.espacio import crear_esquema_espacio
from core import models
from core.catalog import crear_esquema, crear_motor
from migraciones.comun import BaseNoAdoptable, instantanea_esquema, metadata_unida
from migraciones.metadatos import METADATAS_CASO, METADATAS_INSTALACION
from operacion.base_datos import (
    CARPETA_MIGRACIONES,
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
    revision_head,
    revisiones_en_orden,
)
from scripts.congelar_esquema import leer_esquema
from tests.fixtures import bases_prueba

REVISION_BASE = "caso_0001_base_0_5_0"
RAIZ = Path(__file__).resolve().parents[2]
METADATAS = {Destino.CASO: METADATAS_CASO, Destino.INSTALACION: METADATAS_INSTALACION}
#: Paquetes donde puede vivir una `MetaData` con tablas (spec S5 §4.3, RNF-20).
PAQUETES_CON_TABLAS = ("core", "adapters", "ui", "seguridad", "paquete", "asistente")


def _url(ruta: Path) -> str:
    return f"sqlite:///{ruta.as_posix()}"


def _instantanea(ruta: Path) -> dict:
    motor = create_engine(_url(ruta))
    try:
        with motor.connect() as conexion:
            return instantanea_esquema(conexion)
    finally:
        motor.dispose()


def _ddl(ruta: Path) -> dict[str, str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        return dict(
            conexion.execute(
                "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL "
                "AND name NOT LIKE 'sqlite_%' AND tbl_name <> 'alembic_version'"
            )
        )


def _create_all(ruta: Path, destino: Destino) -> Path:
    motor = create_engine(_url(ruta))
    try:
        for metadata in METADATAS[destino]:
            metadata.create_all(motor)
    finally:
        motor.dispose()
    return ruta


def _revision_base():
    archivo = CARPETA_MIGRACIONES / "caso" / "versions" / f"{REVISION_BASE}.py"
    especificacion = importlib.util.spec_from_file_location(REVISION_BASE, archivo)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


# --- la revisión base es el esquema EXACTO de la 0.5.0 (RV-3) ------------------------------------


def test_la_revision_base_es_el_ddl_literal_de_las_bases_de_v0_5_0() -> None:
    congeladas = {t.nombre: (t.ddl, t.indices) for t in _revision_base().TABLAS}
    assert len(congeladas) == 33  # 25 tablas de core/models + 8 esp_* (spec S5 §6.1)
    for nombre in bases_prueba.nombres("0.5.0"):
        base = bases_prueba.carpeta_version("0.5.0") / nombre
        for tabla, ddl, indices in leer_esquema(base):
            assert congeladas[tabla] == (ddl, indices), f"{nombre}: {tabla}"


def test_subir_hasta_la_revision_base_da_el_esquema_de_la_0_5_0(tmp_path: Path) -> None:
    base = tmp_path / "vacia.db"
    aplicar_revisiones(base, Destino.CASO, REVISION_BASE)
    referencia = bases_prueba.copiar_base("0.5.0", "of001.db", tmp_path / "of001.db")
    assert _ddl(base) == _ddl(referencia)
    assert _instantanea(base) == _instantanea(referencia)


def test_la_revision_base_crea_solo_lo_que_falta_y_conserva_las_filas(tmp_path: Path) -> None:
    base = tmp_path / "solo_nucleo.db"
    motor = create_engine(_url(base))
    try:
        models.Base.metadata.create_all(motor)
        with Session(motor) as sesion:
            sesion.add(models.Proyecto(nombre="P", descripcion="", dominio="civil"))
            sesion.commit()
    finally:
        motor.dispose()
    aplicar_revisiones(base, Destino.CASO)
    assert _instantanea(base) == _instantanea(_create_all(tmp_path / "todo.db", Destino.CASO))
    with closing(sqlite3.connect(base)) as conexion:
        assert conexion.execute("SELECT nombre FROM proyecto").fetchall() == [("P",)]


@pytest.mark.parametrize(
    ("sentencia", "mensaje"),
    [
        ("ALTER TABLE composicion_apu DROP COLUMN modalidad", "composicion_apu: falta la columna modalidad"),
        ("ALTER TABLE partida ADD COLUMN extra TEXT", "partida: sobra la columna extra"),
    ],
)
def test_una_tabla_con_otra_forma_es_base_no_adoptable(tmp_path: Path, sentencia: str, mensaje: str) -> None:
    base = _create_all(tmp_path / "alterada.db", Destino.CASO)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute("DROP TABLE esp_origenes")  # una que falta: no debe crearse si hay diferencias
        conexion.execute(sentencia)
        conexion.commit()
    tablas_antes = set(_ddl(base))
    with pytest.raises(BaseNoAdoptable, match=re.escape(mensaje)):
        aplicar_revisiones(base, Destino.CASO)
    assert set(_ddl(base)) == tablas_antes


# --- RNF-20: deriva cero en cada destino ---------------------------------------------------------


@pytest.mark.parametrize("destino", list(Destino))
def test_head_en_vacio_es_igual_a_create_all(tmp_path: Path, destino: Destino) -> None:
    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, destino)
    creada = _create_all(tmp_path / "creada.db", destino)
    assert _instantanea(migrada) == _instantanea(creada)


@pytest.mark.parametrize("destino", list(Destino))
def test_la_autogeneracion_contra_head_no_propone_cambios(tmp_path: Path, destino: Destino) -> None:
    base = tmp_path / "head.db"
    aplicar_revisiones(base, destino)
    motor = create_engine(_url(base))
    try:
        with motor.connect() as conexion:
            contexto = MigrationContext.configure(conexion, opts={"compare_type": True})
            diferencias = compare_metadata(contexto, metadata_unida(METADATAS[destino]))
    finally:
        motor.dispose()
    assert diferencias == []


def test_crear_esquema_sobre_head_no_emite_ddl(tmp_path: Path) -> None:
    base = tmp_path / "head.db"
    aplicar_revisiones(base, Destino.CASO)
    antes = _instantanea(base)
    sentencias: list[str] = []
    motor = crear_motor(_url(base))

    def anotar(_conexion, _cursor, sentencia, *_resto) -> None:
        sentencias.append(sentencia)

    event.listen(motor, "before_cursor_execute", anotar)
    try:
        crear_esquema(motor)
        crear_esquema_espacio(motor)
    finally:
        motor.dispose()
    ddl = [s for s in sentencias if s.lstrip().split(" ", 1)[0].upper() in {"CREATE", "ALTER", "DROP"}]
    assert sentencias and ddl == []
    assert _instantanea(base) == antes


def _declara_tablas(nodo: ast.AST) -> bool:
    if isinstance(nodo, ast.Call):
        funcion = nodo.func
        return (isinstance(funcion, ast.Name) and funcion.id == "MetaData") or (
            isinstance(funcion, ast.Attribute) and funcion.attr == "MetaData"
        )
    if isinstance(nodo, ast.ClassDef):
        return any(
            (isinstance(b, ast.Name) and b.id == "DeclarativeBase")
            or (isinstance(b, ast.Attribute) and b.attr == "DeclarativeBase")
            for b in nodo.bases
        )
    return False


def _modulos_que_declaran_tablas() -> list[str]:
    modulos = []
    for paquete in PAQUETES_CON_TABLAS:
        carpeta = RAIZ / paquete
        if not carpeta.is_dir():
            continue
        for archivo in sorted(carpeta.rglob("*.py")):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            if any(_declara_tablas(nodo) for nodo in ast.walk(arbol)):
                partes = archivo.relative_to(RAIZ).with_suffix("").parts
                modulos.append(".".join(partes[:-1] if partes[-1] == "__init__" else partes))
    return modulos


def test_toda_metadata_con_tablas_esta_en_la_lista_de_su_destino() -> None:
    registradas = [*METADATAS_CASO, *METADATAS_INSTALACION]
    modulos = _modulos_que_declaran_tablas()
    assert {"core.models.base", "adapters.espacio.persistencia"} <= set(modulos), modulos
    sueltas = []
    for nombre in modulos:
        for valor in vars(importlib.import_module(nombre)).values():
            if isinstance(valor, MetaData):
                metadata = valor
            elif isinstance(valor, type):
                metadata = getattr(valor, "metadata", None)
            else:
                continue
            if isinstance(metadata, MetaData) and metadata.tables:
                if not any(metadata is registrada for registrada in registradas):
                    sueltas.append(f"{nombre}: {sorted(metadata.tables)}")
    assert sueltas == []


# --- cada revisión baja y vuelve a subir (DA-S5-6) -----------------------------------------------


@pytest.mark.parametrize("destino", list(Destino))
def test_cada_revision_baja_y_vuelve_a_subir(tmp_path: Path, destino: Destino) -> None:
    base = tmp_path / "ida_y_vuelta.db"
    for revision in revisiones_en_orden(destino):
        aplicar_revisiones(base, destino, revision)
        arriba = _instantanea(base)
        deshacer_revisiones(base, destino, "-1")
        aplicar_revisiones(base, destino, revision)
        assert _instantanea(base) == arriba, revision
    aplicar_revisiones(base, destino)
    deshacer_revisiones(base, destino, "base")
    assert _instantanea(base) == {}


def test_la_instalacion_nace_sin_tablas_y_con_su_alembic_version(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    assert revision_head(Destino.INSTALACION) is None
    with closing(sqlite3.connect(base)) as conexion:
        tablas = [n for (n,) in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        assert tablas == ["alembic_version"]
        assert conexion.execute("SELECT count(*) FROM alembic_version").fetchone()[0] == 0
```

- [ ] **Paso 2: Correrla y ver el rojo; commit de la prueba**
Run: `uv run pytest tests/unit/test_congelar_esquema.py tests/integration/test_migraciones.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'scripts.congelar_esquema'` y
`No module named 'operacion.base_datos'`.
```bash
git add tests/unit/test_congelar_esquema.py tests/integration/test_migraciones.py
git commit -m "test(migraciones): revision base exacta de v0.5.0, deriva cero y vuelta atras (rojo)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`migraciones/comun.py`, agregar a las importaciones `import functools`, `from dataclasses import dataclass`,
`from typing import Any` y cambiar `from sqlalchemy import MetaData` por
`from sqlalchemy import Connection, Inspector, MetaData, create_engine, inspect`; agregar al final:
```python
@dataclass(frozen=True, slots=True)
class TablaCongelada:
    """Una tabla tal como la creó la versión que congela la revisión: su DDL literal de SQLite."""

    nombre: str
    ddl: str
    indices: tuple[str, ...] = ()


def _tipo(tipo: Any) -> str:
    return " ".join(str(tipo).split()).upper()


def describir_tabla(inspector: Inspector, nombre: str) -> dict[str, Any]:
    """La forma reflejada de una tabla; las columnas, por nombre (su orden no importa)."""
    return {
        "columnas": sorted(
            (c["name"], _tipo(c["type"]), bool(c["nullable"])) for c in inspector.get_columns(nombre)
        ),
        "clave_primaria": tuple(inspector.get_pk_constraint(nombre)["constrained_columns"]),
        "indices": sorted(
            (i["name"], tuple(i["column_names"]), bool(i["unique"]))
            for i in inspector.get_indexes(nombre)
        ),
        "unicas": sorted(
            (u["name"] or "", tuple(u["column_names"]))
            for u in inspector.get_unique_constraints(nombre)
        ),
        "foraneas": sorted(
            (tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
            for f in inspector.get_foreign_keys(nombre)
        ),
        "checks": sorted(
            (c["name"] or "", " ".join(str(c["sqltext"]).split()))
            for c in inspector.get_check_constraints(nombre)
        ),
    }


def instantanea_esquema(conexion: Connection) -> dict[str, dict[str, Any]]:
    """Tablas, columnas, tipos, nulabilidad, clave primaria, índices, únicas, foráneas y `CHECK`
    de la base, sin `alembic_version` (RNF-20)."""
    inspector = inspect(conexion)
    return {
        nombre: describir_tabla(inspector, nombre)
        for nombre in sorted(inspector.get_table_names())
        if nombre != TABLA_VERSION
    }


@functools.cache
def _referencia(tablas: tuple[TablaCongelada, ...]) -> dict[str, dict[str, Any]]:
    """La forma de las tablas congeladas, reflejada de una base en memoria creada con su DDL."""
    motor = create_engine("sqlite://")
    try:
        with motor.begin() as conexion:
            for tabla in tablas:
                conexion.exec_driver_sql(tabla.ddl)
                for indice in tabla.indices:
                    conexion.exec_driver_sql(indice)
            return instantanea_esquema(conexion)
    finally:
        motor.dispose()


def _comparar(nombre: str, esperado: dict[str, Any], hallado: dict[str, Any]) -> list[str]:
    esperadas = {columna[0]: columna for columna in esperado["columnas"]}
    halladas = {columna[0]: columna for columna in hallado["columnas"]}
    diferencias = [f"{nombre}: falta la columna {c}" for c in sorted(esperadas.keys() - halladas.keys())]
    diferencias += [f"{nombre}: sobra la columna {c}" for c in sorted(halladas.keys() - esperadas.keys())]
    diferencias += [
        f"{nombre}.{c}: se esperaba {esperadas[c][1:]} y hay {halladas[c][1:]}"
        for c in sorted(esperadas.keys() & halladas.keys())
        if esperadas[c] != halladas[c]
    ]
    diferencias += [
        f"{nombre}: {clave} distintos"
        for clave in ("clave_primaria", "indices", "unicas", "foraneas", "checks")
        if esperado[clave] != hallado[clave]
    ]
    return diferencias


def crear_o_verificar(conexion: Connection, tablas: Sequence[TablaCongelada]) -> None:
    """Crea las tablas que faltan y verifica las existentes contra su definición congelada
    (DA-S5-4). Verifica TODAS antes de crear ninguna: una base no adoptable no gana tablas."""
    referencia = _referencia(tuple(tablas))
    inspector = inspect(conexion)
    existentes = set(inspector.get_table_names())
    diferencias: list[str] = []
    for tabla in tablas:
        if tabla.nombre in existentes:
            hallado = describir_tabla(inspector, tabla.nombre)
            diferencias += _comparar(tabla.nombre, referencia[tabla.nombre], hallado)
    if diferencias:
        raise BaseNoAdoptable(diferencias)
    for tabla in tablas:
        if tabla.nombre not in existentes:
            conexion.exec_driver_sql(tabla.ddl)
            for indice in tabla.indices:
                conexion.exec_driver_sql(indice)


def borrar_tablas(conexion: Connection, tablas: Sequence[TablaCongelada]) -> None:
    """`downgrade` de una revisión que solo crea tablas: las borra en orden inverso."""
    existentes = set(inspect(conexion).get_table_names())
    for tabla in reversed(tablas):
        if tabla.nombre in existentes:
            conexion.exec_driver_sql(f'DROP TABLE "{tabla.nombre}"')


def metadata_unida(metadatas: Sequence[MetaData]) -> MetaData:
    """Una sola `MetaData` con las tablas de varias, para `compare_metadata` (RNF-20)."""
    unida = MetaData()
    for metadata in metadatas:
        for tabla in metadata.sorted_tables:
            tabla.to_metadata(unida)
    return unida
```

`scripts/congelar_esquema.py`:
```python
"""Congela el esquema de una base de prueba como revisión base de Alembic (spec S5 §6.1).

Lee `sqlite_master` de una base de prueba (creada con el código de su etiqueta por
`scripts/generar_base_prueba.py`) y escribe la revisión con el DDL literal de cada tabla y de sus
índices, en el orden en que se crearon, como `TablaCongelada`. Se corre UNA vez por revisión base;
el archivo se revisa a mano y queda congelado: nunca se regenera desde los modelos.

Uso:
    uv run python scripts/congelar_esquema.py --base tests/fixtures/bases/v0_5_0/of001.db \
        --revision caso_0001_base_0_5_0 --version 0.5.0 --commit 8610053 \
        --salida migraciones/caso/versions/caso_0001_base_0_5_0.py
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path

CABECERA = '''"""Revisión base del caso: el esquema EXACTO de Sílice {version} (etiqueta v{version}, {commit}).

Generada una vez con `scripts/congelar_esquema.py` desde la base de prueba de esa versión
(`tests/fixtures/bases/`), creada con el código de su etiqueta; revisada a mano y CONGELADA: no se
deriva de los modelos (spec S5 §6.1). Idempotente (DA-S5-4): crea las tablas que faltan y verifica
las existentes; una diferencia es `BaseNoAdoptable`.
"""

from alembic import op

from migraciones.comun import TablaCongelada, borrar_tablas, crear_o_verificar

revision = "{revision}"
down_revision = None
branch_labels = None
depends_on = None

'''

PIE = '''

def upgrade() -> None:
    crear_o_verificar(op.get_bind(), TABLAS)


def downgrade() -> None:
    borrar_tablas(op.get_bind(), TABLAS)
'''


def leer_esquema(base: Path) -> list[tuple[str, str, tuple[str, ...]]]:
    """`(tabla, ddl, índices)` en orden de creación, sin `alembic_version` ni las internas."""
    uri = base.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conexion:
        filas = conexion.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql IS NOT NULL "
            "AND name NOT LIKE 'sqlite_%' AND tbl_name <> 'alembic_version' ORDER BY rowid"
        ).fetchall()
    indices: dict[str, list[str]] = {}
    for tipo, _nombre, tabla, sql in filas:
        if tipo == "index":
            indices.setdefault(tabla, []).append(sql)
    return [
        (nombre, sql, tuple(indices.get(nombre, ())))
        for tipo, nombre, _tabla, sql in filas
        if tipo == "table"
    ]


def _literal(texto: str) -> str:
    lineas = texto.splitlines(keepends=True) or [""]
    return "(\n" + "".join(f"            {linea!r}\n" for linea in lineas) + "        )"


def renderizar(
    esquema: Sequence[tuple[str, str, tuple[str, ...]]], *, revision: str, version: str, commit: str
) -> str:
    partes = [CABECERA.format(version=version, commit=commit, revision=revision), "TABLAS = (\n"]
    for nombre, ddl, indices in esquema:
        partes.append("    TablaCongelada(\n")
        partes.append(f"        nombre={nombre!r},\n")
        partes.append(f"        ddl={_literal(ddl)},\n")
        partes.append(
            "        indices=(\n" + "".join(f"            {i!r},\n" for i in indices) + "        ),\n"
        )
        partes.append("    ),\n")
    partes.append(")\n")
    partes.append(PIE)
    return "".join(partes)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--base", type=Path, required=True)
    analizador.add_argument("--revision", required=True)
    analizador.add_argument("--version", required=True)
    analizador.add_argument("--commit", required=True)
    analizador.add_argument("--salida", type=Path, required=True)
    argumentos = analizador.parse_args(argv)
    if argumentos.salida.exists():
        print(f"{argumentos.salida} ya existe: una revisión base está congelada.", file=sys.stderr)
        return 1
    texto = renderizar(
        leer_esquema(argumentos.base),
        revision=argumentos.revision,
        version=argumentos.version,
        commit=argumentos.commit,
    )
    argumentos.salida.write_text(texto, encoding="utf-8", newline="\n")
    print(f"Revisión {argumentos.revision} escrita en {argumentos.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`operacion/base_datos.py` (la Tarea 5 lo completa):
```python
"""Abrir una base de Sílice (RF-96; spec S5 §6). Capa de Alembic: destinos, revisiones y migrar.

Dos destinos (DA-S5-7): la base de cada caso y la de la instalación, cada una con su entorno en
`migraciones/<destino>/` y su `alembic_version`. Sin `alembic.ini`: la configuración se arma aquí
y la conexión se entrega en `config.attributes["connection"]`.
"""

from __future__ import annotations

import functools
from enum import StrEnum
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Engine, create_engine

import migraciones
from migraciones.comun import BaseNoAdoptable, ErrorDeBase

CARPETA_MIGRACIONES = Path(migraciones.__file__).resolve().parent

__all__ = ["BaseNoAdoptable", "ErrorDeBase"]


class Destino(StrEnum):
    CASO = "caso"
    INSTALACION = "instalacion"


class MigracionFallida(ErrorDeBase):  # noqa: N818
    """Una revisión falló o dejó la base inconsistente; la base original no se modificó."""


def _configuracion(destino: Destino) -> Config:
    configuracion = Config()
    ubicacion = str(CARPETA_MIGRACIONES / destino.value).replace("%", "%%")
    configuracion.set_main_option("script_location", ubicacion)
    configuracion.set_main_option("path_separator", "os")
    configuracion.set_main_option("version_path_separator", "os")
    return configuracion


@functools.cache
def _guion(destino: Destino) -> ScriptDirectory:
    return ScriptDirectory.from_config(_configuracion(destino))


def revision_head(destino: Destino) -> str | None:
    """La última revisión del destino; `None` mientras no tenga ninguna (la instalación en 0.6.0)."""
    return _guion(destino).get_current_head()


def revisiones_conocidas(destino: Destino) -> frozenset[str]:
    return frozenset(script.revision for script in _guion(destino).walk_revisions())


def revisiones_en_orden(destino: Destino) -> list[str]:
    """De la base a `head`."""
    return list(reversed([script.revision for script in _guion(destino).walk_revisions()]))


def motor_de_migracion(ruta: Path) -> Engine:
    """Motor SIN `PRAGMA foreign_keys`: el modo batch de Alembic recrea tablas y, con las claves
    activas, borrar la tabla vieja dispararía las foráneas. Se comprueban al terminar."""
    return create_engine(URL.create("sqlite", database=str(ruta)))


def aplicar_revisiones(ruta: Path, destino: Destino, objetivo: str = "head") -> None:
    """`upgrade` hasta `objetivo` y, después, `foreign_key_check` e `integrity_check`."""
    motor = motor_de_migracion(ruta)
    try:
        with motor.begin() as conexion:
            configuracion = _configuracion(destino)
            configuracion.attributes["connection"] = conexion
            command.upgrade(configuracion, objetivo)
        with motor.connect() as conexion:
            rotas = conexion.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            integridad = [str(f[0]) for f in conexion.exec_driver_sql("PRAGMA integrity_check")]
    finally:
        motor.dispose()
    if rotas:
        raise MigracionFallida(
            f"Tras migrar {ruta.name} quedaron {len(rotas)} filas con claves foráneas rotas."
        )
    if integridad != ["ok"]:
        raise MigracionFallida(f"Tras migrar {ruta.name}, integrity_check: {'; '.join(integridad[:5])}.")


def deshacer_revisiones(ruta: Path, destino: Destino, objetivo: str = "base") -> None:
    """`downgrade` (DA-S5-6): existe y se prueba en la CI; nunca se ofrece al usuario."""
    motor = motor_de_migracion(ruta)
    try:
        with motor.begin() as conexion:
            configuracion = _configuracion(destino)
            configuracion.attributes["connection"] = conexion
            command.downgrade(configuracion, objetivo)
    finally:
        motor.dispose()
```

**Congelar la revisión base** (una sola vez):
```bash
uv run python scripts/congelar_esquema.py --base tests/fixtures/bases/v0_5_0/of001.db \
  --revision caso_0001_base_0_5_0 --version 0.5.0 --commit 8610053 \
  --salida migraciones/caso/versions/caso_0001_base_0_5_0.py
```
**Revisión a mano** del archivo generado (anotar en el PR): 33 `TablaCongelada` (las 25 de `core/models` y las 8
`esp_*`); ninguna `alembic_version`; los índices de `entidades.py` (`ix_partida_descripcion`,
`ix_insumo_tipo_descripcion`, `ix_composicion_partida_orden`, `ix_rendimiento_partida_tipo_fecha`,
`ix_lista_precios_fecha_vigencia`, `ix_cambio_precio_lista_nueva`, `ix_registro_cambio_resultante`) junto a su
tabla; `ck_rendimiento_medido_exige_ejecucion` dentro del DDL de `rendimiento`. **No se edita** el DDL: si algo no
cuadra, se corrige la base de prueba, no la revisión.

`scripts/README.md`, en la tabla de la sección «Bases de prueba y migraciones», agregar:
```markdown
| `congelar_esquema.py` | escribe una revisión base de Alembic con el DDL literal (`sqlite_master`) de una base de prueba, en orden de creación; se niega a pisar una revisión existente (la revisión base queda congelada) | S5‑1 · RF‑96 |
```

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_congelar_esquema.py tests/integration/test_migraciones.py tests/unit/test_scripts_documentados.py -v -W error`
Esperado: PASS (incluida la autogeneración vacía en los dos destinos). Luego `uv run pytest -q -W error` y
`uv run ruff check migraciones operacion scripts/congelar_esquema.py tests/unit/test_congelar_esquema.py tests/integration/test_migraciones.py`.

- [ ] **Paso 5: Commit**
```bash
git add migraciones/comun.py migraciones/caso/versions/caso_0001_base_0_5_0.py operacion/base_datos.py scripts/congelar_esquema.py scripts/README.md
git commit -m "feat(migraciones): revision base caso_0001 congelada desde v0.5.0 y capa Alembic de operacion" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 4: `operacion.respaldo`: juego con ficha, retención y restauración

**Rama:** `inc/060-s5-1-alembic` (sale de `main`; PR a `main`; ver RV-2)   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `operacion/respaldo.py`
- Prueba: `tests/integration/test_respaldo.py`

**Interfaces:**
- Consume: `operacion.config` (`RAIZ`, `NOMBRE_INSTALACION`); `migraciones.comun.ErrorDeBase`;
  `operacion.base_datos.Destino`, `aplicar_revisiones`, `revision_head`, `revisiones_conocidas` (solo en las pruebas);
  `tests.fixtures.bases_prueba.copiar_base`, `ficha`, `crear_base_futura`.
- Produce (`operacion.respaldo`): `FORMATO_FICHA = 1`, `NOMBRE_FICHA`, `MOTIVO_MIGRACION = "migracion"`,
  `MOTIVO_MANUAL = "manual"`, `MOTIVO_ANTES_DE_RESTAURAR = "antes_de_restaurar"`, `CONSERVAR_MIGRACIONES = 5`,
  `TABLA_VERSION`, `TABLA_EVENTOS = "evento_acceso"`, `ESPERA_BLOQUEO_S = 5.0`, `RespaldoFallido(ErrorDeBase)`,
  `Restauracion(antes: Path, restauradas: tuple[Path, ...], eventos_perdidos: Path | None)`,
  `uri_solo_lectura(ruta) -> str`, `abrir_solo_lectura(ruta) -> sqlite3.Connection`, `huella(ruta) -> str`,
  `tablas_de(conexion) -> set[str]`, `revision_de(conexion) -> str | None`, `filas_por_tabla(conexion) -> dict`,
  `copiar_sqlite(origen, destino) -> None`, `verificar_integridad(ruta) -> None`,
  `ruta_en_juego(juego, ruta, destino: str) -> Path`,
  `respaldar(casos, motivo, *, ruta_instalacion, carpeta_respaldos, heads, ahora=None) -> Path`,
  `leer_ficha(juego) -> dict`, `listar_juegos(carpeta_respaldos) -> list[tuple[Path, dict]]`,
  `podar_juegos(carpeta_respaldos, conservar=CONSERVAR_MIGRACIONES) -> list[Path]`,
  `eventos_perdidos(actual, ultimo) -> list[dict]`,
  `restaurar(juego, *, ruta_instalacion, carpeta_casos, carpeta_datos, carpeta_respaldos, heads, conocidas, solo_caso=None, ahora=None) -> Restauracion`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/integration/test_respaldo.py`:
```python
"""Juegos de respaldo de las dos bases, en una ficha, y su restauración (RF-96 b y f; spec S5 §6.3
y §6.5). En la 0.6.0 la base de la instalación no tiene tablas: el juego ya la lleva y la lista de
eventos perdidos ya la lee."""

from __future__ import annotations

import json
import sqlite3
import tomllib
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from operacion import config, respaldo
from operacion.base_datos import Destino, aplicar_revisiones, revision_head, revisiones_conocidas
from tests.fixtures import bases_prueba


@dataclass(frozen=True)
class Datos:
    carpeta: Path
    casos: Path
    instalacion: Path
    respaldos: Path


@pytest.fixture
def datos(tmp_path: Path) -> Datos:
    carpeta = tmp_path / "datos"
    return Datos(carpeta, carpeta / "casos", carpeta / "instalacion.db", carpeta / "respaldos")


def _heads() -> dict[str, str | None]:
    return {d.value: revision_head(d) for d in Destino}


def _respaldar(datos: Datos, casos: list[Path], motivo: str = "migracion", ahora=None) -> Path:
    return respaldo.respaldar(
        casos, motivo, ruta_instalacion=datos.instalacion, carpeta_respaldos=datos.respaldos,
        heads=_heads(), ahora=ahora,
    )


def _restaurar(datos: Datos, juego: Path, solo_caso: str | None = None) -> respaldo.Restauracion:
    return respaldo.restaurar(
        juego, ruta_instalacion=datos.instalacion, carpeta_casos=datos.casos,
        carpeta_datos=datos.carpeta, carpeta_respaldos=datos.respaldos, heads=_heads(),
        conocidas={d.value: revisiones_conocidas(d) for d in Destino}, solo_caso=solo_caso,
    )


def _instalacion_vacia(datos: Datos) -> None:
    datos.carpeta.mkdir(parents=True, exist_ok=True)
    aplicar_revisiones(datos.instalacion, Destino.INSTALACION)


def _filas(ruta: Path) -> dict[str, int]:
    with closing(respaldo.abrir_solo_lectura(ruta)) as conexion:
        return respaldo.filas_por_tabla(conexion)


def test_el_juego_trae_la_copia_verificada_y_su_ficha(datos: Datos) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    juego = _respaldar(datos, [caso])
    ficha = respaldo.leer_ficha(juego)
    with (config.RAIZ / "pyproject.toml").open("rb") as archivo:
        assert ficha["version_silice"] == tomllib.load(archivo)["project"]["version"]
    assert ficha["motivo"] == "migracion" and ficha["ultimo_evento_acceso"] is None
    [base] = ficha["bases"]
    assert (base["archivo"], base["destino"]) == ("casos/demo.db", "caso")
    assert base["revision_origen"] is None
    assert base["revision_destino"] == revision_head(Destino.CASO)
    assert base["sha256"] == respaldo.huella(juego / "casos" / "demo.db")
    assert base["filas_por_tabla"] == bases_prueba.ficha("0.5.0")["bases"]["demo.db"]["filas_por_tabla"]
    respaldo.verificar_integridad(juego / "casos" / "demo.db")
    assert not (juego / "instalacion.db").exists()


def test_la_instalacion_va_siempre_en_el_juego_aunque_no_se_migre(datos: Datos) -> None:
    _instalacion_vacia(datos)
    juego = _respaldar(datos, [])
    [base] = respaldo.leer_ficha(juego)["bases"]
    assert (base["archivo"], base["destino"], base["revision_origen"]) == ("instalacion.db", "instalacion", None)
    assert base["filas_por_tabla"] == {"alembic_version": 0}


def test_se_respalda_con_la_base_abierta_y_una_escritura_sin_confirmar(datos: Datos) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    antes = _filas(caso)
    otro = sqlite3.connect(caso, isolation_level=None)
    try:
        otro.execute("BEGIN IMMEDIATE")
        otro.execute("INSERT INTO proyecto (nombre, descripcion, dominio) VALUES ('sin confirmar', '', 'civil')")
        juego = _respaldar(datos, [caso])
    finally:
        otro.execute("ROLLBACK")
        otro.close()
    assert _filas(juego / "casos" / "demo.db") == antes


def test_disco_lleno_no_deja_juego_ni_toca_la_base(datos: Datos, monkeypatch) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    antes = respaldo.huella(caso)

    def disco_lleno(_origen: Path, _destino: Path) -> None:
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(respaldo, "copiar_sqlite", disco_lleno)
    with pytest.raises(respaldo.RespaldoFallido, match="disk is full"):
        _respaldar(datos, [caso])
    assert list(datos.respaldos.iterdir()) == []
    assert respaldo.huella(caso) == antes


def test_una_copia_ilegible_no_deja_juego(datos: Datos, monkeypatch) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")

    def copia_rota(_origen: Path, destino: Path) -> None:
        destino.write_bytes(b"esto no es una base de datos" * 200)

    monkeypatch.setattr(respaldo, "copiar_sqlite", copia_rota)
    with pytest.raises(respaldo.RespaldoFallido, match="no es una base legible"):
        _respaldar(datos, [caso])
    assert list(datos.respaldos.iterdir()) == []


def test_juego_en_una_ruta_de_onedrive_con_espacios_y_acentos(tmp_path: Path) -> None:
    carpeta = tmp_path / "OneDrive - Personal" / "Escritorio" / "TÉSIS ñ" / "datos"
    datos = Datos(carpeta, carpeta / "casos", carpeta / "instalacion.db", carpeta / "respaldos")
    caso = bases_prueba.copiar_base("0.5.0", "of001.db", datos.casos / "Oficina Ñandú con espacios.db")
    juego = _respaldar(datos, [caso])
    [base] = respaldo.leer_ficha(juego)["bases"]
    assert base["archivo"] == "casos/Oficina Ñandú con espacios.db"
    respaldo.verificar_integridad(juego / base["archivo"])


def test_se_conservan_los_cinco_ultimos_de_migracion_y_todos_los_manuales(datos: Datos) -> None:
    inicio = datetime(2026, 10, 11, 8, 0, 0)
    de_migracion = [_respaldar(datos, [], ahora=inicio + timedelta(minutes=n)) for n in range(7)]
    manual = _respaldar(datos, [], motivo="manual", ahora=inicio - timedelta(days=1))
    borrados = respaldo.podar_juegos(datos.respaldos)
    assert borrados == de_migracion[:2]
    quedan = [c for c, _ in respaldo.listar_juegos(datos.respaldos)]
    assert quedan == [manual, *de_migracion[2:]]


def test_restaurar_devuelve_el_caso_y_guarda_antes_las_bases_actuales(datos: Datos) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    juego = _respaldar(datos, [caso])
    with closing(sqlite3.connect(caso)) as conexion:
        conexion.execute("INSERT INTO proyecto (nombre, descripcion, dominio) VALUES ('despues', '', 'civil')")
        conexion.commit()
    modificadas = _filas(caso)
    resultado = _restaurar(datos, juego)
    assert resultado.restauradas == (datos.casos / "demo.db",)
    assert resultado.eventos_perdidos is None
    assert _filas(caso) == _filas(juego / "casos" / "demo.db")
    assert respaldo.leer_ficha(resultado.antes)["motivo"] == "antes_de_restaurar"
    assert _filas(resultado.antes / "casos" / "demo.db") == modificadas


def test_restaurar_un_juego_con_la_instalacion_vacia_de_la_0_6_0(datos: Datos) -> None:
    _instalacion_vacia(datos)
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    juego = _respaldar(datos, [caso])
    resultado = _restaurar(datos, juego)
    assert sorted(r.name for r in resultado.restauradas) == ["demo.db", "instalacion.db"]
    perdidos = json.loads(resultado.eventos_perdidos.read_text(encoding="utf-8"))
    assert perdidos["revisado"] is False and perdidos["eventos"] == []
    assert resultado.eventos_perdidos.parent == datos.carpeta


def test_restaurar_la_instalacion_lista_los_eventos_posteriores_al_juego(datos: Datos) -> None:
    datos.carpeta.mkdir(parents=True)
    with closing(sqlite3.connect(datos.instalacion)) as conexion:
        # Las columnas que lee la lista son las de `evento_acceso` de S3 §12 (id, fecha_hora).
        conexion.execute("CREATE TABLE evento_acceso (id INTEGER PRIMARY KEY, fecha_hora TEXT NOT NULL, tipo TEXT NOT NULL)")
        conexion.executemany(
            "INSERT INTO evento_acceso VALUES (?, ?, ?)",
            [(1, "2026-10-01T08:00:00", "entrada"), (2, "2026-10-01T09:00:00", "revocación")],
        )
        conexion.commit()
    juego = _respaldar(datos, [])
    assert respaldo.leer_ficha(juego)["ultimo_evento_acceso"] == {"id": 2, "fecha_hora": "2026-10-01T09:00:00"}
    with closing(sqlite3.connect(datos.instalacion)) as conexion:
        conexion.execute("INSERT INTO evento_acceso VALUES (3, '2026-10-02T10:00:00', 'baja')")
        conexion.commit()
    resultado = _restaurar(datos, juego)
    perdidos = json.loads(resultado.eventos_perdidos.read_text(encoding="utf-8"))
    assert perdidos["eventos"] == [{"id": 3, "fecha_hora": "2026-10-02T10:00:00", "tipo": "baja"}]


def test_solo_caso_restaura_ese_caso_y_no_toca_la_instalacion(datos: Datos) -> None:
    _instalacion_vacia(datos)
    a = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "a.db")
    b = bases_prueba.copiar_base("0.5.0", "ti001.db", datos.casos / "b.db")
    juego = _respaldar(datos, [a, b])
    instalacion_antes = respaldo.huella(datos.instalacion)
    b_antes = respaldo.huella(b)
    resultado = _restaurar(datos, juego, solo_caso="a")
    assert resultado.restauradas == (datos.casos / "a.db",) and resultado.eventos_perdidos is None
    assert respaldo.huella(datos.instalacion) == instalacion_antes and respaldo.huella(b) == b_antes


def test_un_juego_alterado_no_se_restaura(datos: Datos) -> None:
    caso = bases_prueba.copiar_base("0.5.0", "demo.db", datos.casos / "demo.db")
    juego = _respaldar(datos, [caso])
    with (juego / "casos" / "demo.db").open("ab") as copia:
        copia.write(b"\0")
    antes = respaldo.huella(caso)
    with pytest.raises(respaldo.RespaldoFallido, match="alterada"):
        _restaurar(datos, juego)
    assert respaldo.huella(caso) == antes


def test_un_juego_de_una_version_mas_nueva_no_se_restaura(datos: Datos) -> None:
    futura = bases_prueba.crear_base_futura(datos.casos / "futura.db")
    juego = _respaldar(datos, [futura])
    with pytest.raises(respaldo.RespaldoFallido, match="versión más nueva"):
        _restaurar(datos, juego)
```

- [ ] **Paso 2: Correrla y ver el rojo; commit de la prueba**
Run: `uv run pytest tests/integration/test_respaldo.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'respaldo' from 'operacion'`.
```bash
git add tests/integration/test_respaldo.py
git commit -m "test(operacion): juego de respaldo con ficha, retencion y restauracion (rojo)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/respaldo.py`:
```python
"""Juegos de respaldo de las dos bases y su restauración (RF-96; spec S5 §6.3 y §6.5).

Un **juego** es la carpeta `<respaldos>/<AAAAMMDD-HHMMSS>_<motivo>/` con `instalacion.db` (si existe:
va siempre, aunque no se migre, para que la pareja restaurada sea coherente), los casos en `casos/`
y `ficha.json`: versión de Sílice, motivo, fecha y, por base, revisión de origen y de destino, filas
por tabla y SHA-256 de la copia; además, el último `evento_acceso` de la instalación. Cada copia sale
de la API de respaldo de `sqlite3` (segura con la base abierta) y pasa `PRAGMA integrity_check`:
sin juego verificado no se migra.

En la 0.6.0 la base de la instalación no tiene tablas (S3-1 las agrega): el juego y la restauración
ya la tratan, y la lista de eventos de seguridad perdidos lee `evento_acceso` (`id`, `fecha_hora`,
S3 §12) cuando existe. S3 agrega aquí las diferencias de cuentas, roles, claves y revocaciones.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tomllib
from collections.abc import Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from migraciones.comun import TABLA_VERSION, ErrorDeBase
from operacion import config

FORMATO_FICHA = 1
NOMBRE_FICHA = "ficha.json"
CARPETA_CASOS_DEL_JUEGO = "casos"
MOTIVO_MIGRACION = "migracion"
MOTIVO_MANUAL = "manual"
MOTIVO_ANTES_DE_RESTAURAR = "antes_de_restaurar"
CONSERVAR_MIGRACIONES = 5
TABLA_EVENTOS = "evento_acceso"
#: Segundos que se espera a otro proceso que tiene la base bloqueada antes de rendirse.
ESPERA_BLOQUEO_S = 5.0
_BLOQUE = 1 << 20

__all__ = ["TABLA_VERSION"]


class RespaldoFallido(ErrorDeBase):  # noqa: N818
    """No se pudo crear, verificar o restaurar un juego. Si era previo a una migración, no se migró
    nada: las bases quedan como estaban."""


@dataclass(frozen=True, slots=True)
class Restauracion:
    """Lo que hizo `restaurar`: el juego con las bases de antes, las restauradas y, si el juego
    traía la instalación, el archivo de eventos de seguridad perdidos (`revisado: false`)."""

    antes: Path
    restauradas: tuple[Path, ...]
    eventos_perdidos: Path | None


def uri_solo_lectura(ruta: Path) -> str:
    """URI `file:` de solo lectura; `as_uri` codifica espacios, tildes y `ñ` (rutas de OneDrive)."""
    return Path(ruta).resolve().as_uri() + "?mode=ro"


def abrir_solo_lectura(ruta: Path) -> sqlite3.Connection:
    return sqlite3.connect(uri_solo_lectura(ruta), uri=True, timeout=ESPERA_BLOQUEO_S)


def huella(ruta: Path) -> str:
    sha = hashlib.sha256()
    with Path(ruta).open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(_BLOQUE), b""):
            sha.update(bloque)
    return sha.hexdigest()


def tablas_de(conexion: sqlite3.Connection) -> set[str]:
    return {
        nombre
        for (nombre,) in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def revision_de(conexion: sqlite3.Connection) -> str | None:
    if TABLA_VERSION not in tablas_de(conexion):
        return None
    fila = conexion.execute(f"SELECT version_num FROM {TABLA_VERSION}").fetchone()
    return None if fila is None else str(fila[0])


def filas_por_tabla(conexion: sqlite3.Connection) -> dict[str, int]:
    return {
        tabla: conexion.execute(f'SELECT count(*) FROM "{tabla}"').fetchone()[0]
        for tabla in sorted(tablas_de(conexion))
    }


def copiar_sqlite(origen: Path, destino: Path) -> None:
    """Copia `origen` en `destino` con la API de respaldo de SQLite: segura con la base abierta por
    otro proceso y transaccional sobre el destino (un fallo no lo deja a medias)."""
    with (
        closing(abrir_solo_lectura(origen)) as fuente,
        closing(sqlite3.connect(destino, timeout=ESPERA_BLOQUEO_S)) as copia,
    ):
        fuente.backup(copia)


def verificar_integridad(ruta: Path) -> None:
    try:
        with closing(abrir_solo_lectura(ruta)) as conexion:
            resultado = [str(fila[0]) for fila in conexion.execute("PRAGMA integrity_check")]
    except sqlite3.DatabaseError as error:
        raise RespaldoFallido(f"La copia {ruta.name} no es una base legible: {error}.") from error
    if resultado != ["ok"]:
        raise RespaldoFallido(
            f"La copia {ruta.name} no pasó PRAGMA integrity_check: {'; '.join(resultado[:5])}."
        )


def ruta_en_juego(juego: Path, ruta: Path, destino: str) -> Path:
    if destino == "instalacion":
        return juego / config.NOMBRE_INSTALACION
    return juego / CARPETA_CASOS_DEL_JUEGO / Path(ruta).name


def _version_silice() -> str:
    """La versión de `pyproject.toml` (fuente única, RF-99); `operacion.version` la sustituye en S5-2."""
    with (config.RAIZ / "pyproject.toml").open("rb") as archivo:
        return str(tomllib.load(archivo)["project"]["version"])


def _escribir_json(ruta: Path, datos: Mapping[str, Any]) -> None:
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _carpeta_nueva(padre: Path, nombre: str) -> Path:
    padre.mkdir(parents=True, exist_ok=True)
    for numero in range(1, 1000):
        carpeta = padre / (nombre if numero == 1 else f"{nombre}_{numero}")
        try:
            carpeta.mkdir()
        except FileExistsError:
            continue
        return carpeta
    raise RespaldoFallido(f"Demasiados juegos llamados {nombre} en {padre}.")


def _ultimo_evento(ruta: Path) -> dict[str, Any] | None:
    if not ruta.exists():
        return None
    with closing(abrir_solo_lectura(ruta)) as conexion:
        if TABLA_EVENTOS not in tablas_de(conexion):
            return None
        fila = conexion.execute(
            f"SELECT id, fecha_hora FROM {TABLA_EVENTOS} ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return None if fila is None else {"id": fila[0], "fecha_hora": str(fila[1])}


def _copiar_y_describir(
    origen: Path, juego: Path, destino: str, heads: Mapping[str, str | None]
) -> dict[str, Any]:
    copia = ruta_en_juego(juego, origen, destino)
    copia.parent.mkdir(parents=True, exist_ok=True)
    copiar_sqlite(origen, copia)
    verificar_integridad(copia)
    with closing(abrir_solo_lectura(copia)) as conexion:
        revision = revision_de(conexion)
        filas = filas_por_tabla(conexion)
    return {
        "archivo": copia.relative_to(juego).as_posix(),
        "origen": str(Path(origen).resolve()),
        "destino": destino,
        "revision_origen": revision,
        "revision_destino": heads.get(destino),
        "filas_por_tabla": filas,
        "sha256": huella(copia),
    }


def respaldar(
    casos: Sequence[Path],
    motivo: str,
    *,
    ruta_instalacion: Path,
    carpeta_respaldos: Path,
    heads: Mapping[str, str | None],
    ahora: datetime | None = None,
) -> Path:
    """Crea y verifica un juego con la instalación (si existe) y `casos`. `RespaldoFallido` sin
    dejar carpeta a medias (disco lleno, copia ilegible, integridad, permisos)."""
    nombres = [Path(caso).name for caso in casos]
    if len(set(nombres)) != len(nombres):
        raise RespaldoFallido(f"Dos casos con el mismo nombre no caben en un juego: {sorted(nombres)}.")
    momento = ahora or datetime.now()
    try:
        juego = _carpeta_nueva(carpeta_respaldos, f"{momento:%Y%m%d-%H%M%S}_{motivo}")
    except OSError as error:
        raise RespaldoFallido(f"No se pudo crear el respaldo en {carpeta_respaldos}: {error}.") from error
    try:
        bases = []
        if ruta_instalacion.exists():
            bases.append(_copiar_y_describir(ruta_instalacion, juego, "instalacion", heads))
        for caso in casos:
            bases.append(_copiar_y_describir(Path(caso), juego, "caso", heads))
        _escribir_json(
            juego / NOMBRE_FICHA,
            {
                "formato": FORMATO_FICHA,
                "version_silice": _version_silice(),
                "motivo": motivo,
                "fecha": momento.isoformat(timespec="microseconds"),
                "bases": bases,
                "ultimo_evento_acceso": _ultimo_evento(juego / config.NOMBRE_INSTALACION),
            },
        )
    except RespaldoFallido:
        shutil.rmtree(juego, ignore_errors=True)
        raise
    except (OSError, sqlite3.Error) as error:
        shutil.rmtree(juego, ignore_errors=True)
        raise RespaldoFallido(
            f"No se pudo crear el respaldo en {carpeta_respaldos}: {error}. "
            "No se migró ni se cambió nada."
        ) from error
    return juego


def leer_ficha(juego: Path) -> dict[str, Any]:
    try:
        ficha = json.loads((Path(juego) / NOMBRE_FICHA).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RespaldoFallido(f"{juego} no es un juego de respaldo de Sílice: {error}.") from error
    if ficha.get("formato") != FORMATO_FICHA:
        raise RespaldoFallido(f"La ficha de {Path(juego).name} tiene un formato desconocido.")
    return ficha


def listar_juegos(carpeta_respaldos: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Los juegos legibles, del más viejo al más nuevo (por la fecha de su ficha)."""
    if not carpeta_respaldos.is_dir():
        return []
    juegos = []
    for carpeta in carpeta_respaldos.iterdir():
        if carpeta.is_dir() and (carpeta / NOMBRE_FICHA).is_file():
            try:
                juegos.append((carpeta, leer_ficha(carpeta)))
            except RespaldoFallido:
                continue
    return sorted(juegos, key=lambda par: par[1]["fecha"])


def podar_juegos(carpeta_respaldos: Path, conservar: int = CONSERVAR_MIGRACIONES) -> list[Path]:
    """Borra los juegos de migración más viejos y conserva los `conservar` últimos (al menos uno:
    nunca el más reciente). Los manuales y los de antes de restaurar no se borran (spec S5 §6.3)."""
    de_migracion = [
        carpeta
        for carpeta, ficha in listar_juegos(carpeta_respaldos)
        if ficha["motivo"] == MOTIVO_MIGRACION
    ]
    sobran = de_migracion[: -max(conservar, 1)]
    for carpeta in sobran:
        shutil.rmtree(carpeta)
    return sobran


def eventos_perdidos(actual: Path, ultimo: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Los `evento_acceso` de la instalación actual posteriores al último del juego (SEG-12)."""
    if not actual.exists():
        return []
    with closing(abrir_solo_lectura(actual)) as conexion:
        if TABLA_EVENTOS not in tablas_de(conexion):
            return []
        conexion.row_factory = sqlite3.Row
        desde = int(ultimo["id"]) if ultimo else 0
        filas = conexion.execute(
            f"SELECT * FROM {TABLA_EVENTOS} WHERE id > ? ORDER BY id", (desde,)
        ).fetchall()
    return [dict(fila) for fila in filas]


def _con_extension(nombre: str) -> str:
    return nombre if nombre.lower().endswith(".db") else f"{nombre}.db"


def restaurar(
    juego: Path,
    *,
    ruta_instalacion: Path,
    carpeta_casos: Path,
    carpeta_datos: Path,
    carpeta_respaldos: Path,
    heads: Mapping[str, str | None],
    conocidas: Mapping[str, frozenset[str]],
    solo_caso: str | None = None,
    ahora: datetime | None = None,
) -> Restauracion:
    """Restaura un juego (spec S5 §6.5). Rechaza, sin tocar nada, un juego alterado (huella distinta
    de la ficha), ilegible o de una versión más nueva. Antes guarda las bases actuales como juego
    `antes_de_restaurar`. Si el juego trae la instalación, escribe en la carpeta de datos
    `eventos_perdidos_<fecha>.json` con `revisado: false`. Exige Sílice detenido: hasta que el
    lanzador (S5-2) deje `estado/servidor.json`, lo comprueba quien ejecuta la orden."""
    juego = Path(juego)
    ficha = leer_ficha(juego)
    elegidas = [
        base
        for base in ficha["bases"]
        if solo_caso is None
        or (base["destino"] == "caso" and Path(base["archivo"]).name == _con_extension(solo_caso))
    ]
    if not elegidas:
        raise RespaldoFallido(f"El juego {juego.name} no trae {solo_caso or 'ninguna base'}.")
    for base in elegidas:
        copia = juego / base["archivo"]
        if not copia.is_file() or huella(copia) != base["sha256"]:
            raise RespaldoFallido(
                f"La copia {base['archivo']} del juego {juego.name} falta o fue alterada (su huella "
                "no es la de la ficha). No se restauró nada."
            )
        verificar_integridad(copia)
        origen = base["revision_origen"]
        if origen is not None and origen not in conocidas[base["destino"]]:
            raise RespaldoFallido(
                f"El juego {juego.name} es de una versión más nueva de Sílice (revisión {origen}). "
                "Instale esa versión para restaurarlo."
            )
    destinos = {
        base["archivo"]: ruta_instalacion
        if base["destino"] == "instalacion"
        else carpeta_casos / Path(base["archivo"]).name
        for base in elegidas
    }
    momento = ahora or datetime.now()
    actuales = [
        destinos[base["archivo"]]
        for base in elegidas
        if base["destino"] == "caso" and destinos[base["archivo"]].exists()
    ]
    antes = respaldar(
        actuales,
        MOTIVO_ANTES_DE_RESTAURAR,
        ruta_instalacion=ruta_instalacion,
        carpeta_respaldos=carpeta_respaldos,
        heads=heads,
        ahora=momento,
    )
    perdidos = None
    if any(base["destino"] == "instalacion" for base in elegidas):
        carpeta_datos.mkdir(parents=True, exist_ok=True)
        perdidos = carpeta_datos / f"eventos_perdidos_{momento:%Y%m%d-%H%M%S}.json"
        _escribir_json(
            perdidos,
            {
                "juego": str(juego),
                "fecha": momento.isoformat(timespec="seconds"),
                "revisado": False,
                "eventos": eventos_perdidos(ruta_instalacion, ficha.get("ultimo_evento_acceso")),
            },
        )
    restauradas = []
    for base in elegidas:
        destino = destinos[base["archivo"]]
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            copiar_sqlite(juego / base["archivo"], destino)
        except sqlite3.Error as error:
            raise RespaldoFallido(
                f"No se pudo restaurar {destino.name}: {error}. Cierre Sílice y vuelva a intentarlo; "
                f"las bases de antes están en {antes}."
            ) from error
        restauradas.append(destino)
    return Restauracion(antes=antes, restauradas=tuple(restauradas), eventos_perdidos=perdidos)
```

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/integration/test_respaldo.py tests/unit/test_arquitectura_s5.py -v -W error`
Esperado: PASS. `uv run ruff check operacion/respaldo.py tests/integration/test_respaldo.py`.

- [ ] **Paso 5: Commit**
```bash
git add operacion/respaldo.py
git commit -m "feat(operacion): juego de respaldo de las dos bases con ficha, retencion y restauracion" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 5: `preparar_base`, adopción, lista de casos, rutas rechazadas y `python -m operacion`

**Rama:** `inc/060-s5-1-alembic` (sale de `main`; PR a `main`; ver RV-2)   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `operacion/__main__.py`
- Modificar: `operacion/base_datos.py` (docstring del módulo, importaciones y agregar al final)
- Prueba: `tests/integration/test_preparar_base.py`, `tests/unit/test_casos.py`, `tests/integration/test_operacion_cli.py`

**Interfaces:**
- Consume: Tarea 3 (`Destino`, `aplicar_revisiones`, `revision_head`, `revisiones_conocidas`, `_configuracion`,
  `_guion`, `CARPETA_MIGRACIONES`, `MigracionFallida`); Tarea 4 (todo `operacion.respaldo`); `operacion.config`.
- Produce (`operacion.base_datos`): `SUFIJO_TRABAJO = ".migrando"`, `EXTENSION = ".db"`, `MENSAJE_MAS_NUEVA`,
  `RutaDeCasoRechazada`, `BaseIlegible`, `BaseBloqueada`, `BaseMasNueva` (todas `ErrorDeBase`), reexporta
  `ErrorDeBase`, `BaseNoAdoptable`, `RespaldoFallido`; `EstadoBase(existe, tablas, revision)` con `.sin_datos`;
  `ResultadoPreparacion(ruta, destino, revision_origen, revision_destino, juego, nueva)`;
  `leer_estado(ruta) -> EstadoBase`; `preparar_base(ruta, destino=Destino.CASO, *, entorno=None) -> ResultadoPreparacion`;
  `migrar_todo(entorno=None) -> list[ResultadoPreparacion]`; `respaldar_todo(entorno=None) -> Path`;
  `restaurar_juego(juego, *, solo_caso=None, entorno=None) -> Restauracion`;
  `motor_solo_lectura(ruta) -> Engine`; `listar_casos(carpeta=None, *, entorno=None) -> list[Path]`;
  `resolver_caso(nombre, carpeta=None, *, entorno=None) -> Path`; `sanear_nombre(nombre) -> str`;
  `crear_caso(nombre, carpeta=None, *, entorno=None)`, `subir_caso(nombre_original, contenido, carpeta=None, *, entorno=None)`,
  `adoptar_base(origen, nombre=None, *, entorno=None)` (las tres `-> ResultadoPreparacion`).
  `operacion.__main__.main(argv=None) -> int` con órdenes `casos | revision | migrar | respaldar | restaurar <juego> [--solo-caso N] | adoptar <origen> [--nombre N]`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/integration/test_preparar_base.py`:
```python
"""`preparar_base`: crear, adoptar y migrar con respaldo previo; rechazar sin tocar (RF-96 a, c, d;
spec S5 §6.3 y §6.4; RV-3). Las bases viven en `tmp_path`; los juegos, en la carpeta de datos
temporal de `tests/conftest.py`."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from operacion import base_datos, config, respaldo
from operacion.base_datos import (
    BaseBloqueada,
    BaseIlegible,
    BaseMasNueva,
    BaseNoAdoptable,
    Destino,
    MigracionFallida,
    RespaldoFallido,
    RutaDeCasoRechazada,
    leer_estado,
    migrar_todo,
    preparar_base,
    revision_head,
)
from tests.fixtures import bases_prueba

FICHA = bases_prueba.ficha("0.5.0")

REVISION_QUE_FALLA = '''"""Revisión de prueba: crea una tabla y falla a medias (RF-96 c)."""
import sqlalchemy as sa
from alembic import op

revision = "caso_9000_falla"
down_revision = "{abajo}"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("tabla_a_medias", sa.Column("id", sa.Integer, primary_key=True))
    raise RuntimeError("falla inyectada")


def downgrade() -> None:
    op.drop_table("tabla_a_medias")
'''


def _juegos() -> list:
    return respaldo.listar_juegos(config.carpeta_respaldos())


def _demo(tmp_path: Path) -> Path:
    return bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")


def test_una_base_que_no_existe_nace_en_head_sin_juego(tmp_path: Path) -> None:
    ruta = tmp_path / "nueva" / "caso.db"
    resultado = preparar_base(ruta)
    assert (resultado.nueva, resultado.juego) == (True, None)
    assert resultado.revision_destino == revision_head(Destino.CASO)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert _juegos() == []


def test_un_archivo_vacio_nace_en_head(tmp_path: Path) -> None:
    ruta = tmp_path / "vacia.db"
    ruta.touch()
    assert preparar_base(ruta).nueva
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)


@pytest.mark.parametrize("nombre", bases_prueba.nombres("0.5.0"))
def test_una_base_de_la_0_5_0_se_adopta_con_juego_y_recarga_igual_que_su_ficha(
    tmp_path: Path, nombre: str
) -> None:
    ruta = bases_prueba.copiar_base("0.5.0", nombre, tmp_path / nombre)
    resultado = preparar_base(ruta)
    assert resultado.revision_origen is None and resultado.juego is not None
    [base] = [b for b in respaldo.leer_ficha(resultado.juego)["bases"] if b["destino"] == "caso"]
    assert base["revision_origen"] is None
    assert base["revision_destino"] == revision_head(Destino.CASO)
    assert base["filas_por_tabla"] == FICHA["bases"][nombre]["filas_por_tabla"]
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert bases_prueba.diferencias_con_ficha(ruta, FICHA["bases"][nombre]) == []


def test_preparar_dos_veces_no_crea_otro_juego_ni_cambia_la_base(tmp_path: Path) -> None:
    ruta = _demo(tmp_path)
    preparar_base(ruta)
    antes, juegos = respaldo.huella(ruta), len(_juegos())
    segundo = preparar_base(ruta)
    assert segundo.juego is None and not segundo.nueva
    assert respaldo.huella(ruta) == antes and len(_juegos()) == juegos


def test_un_fallo_inyectado_en_una_revision_deja_la_base_como_estaba(tmp_path: Path, monkeypatch) -> None:
    versiones = tmp_path / "versiones de prueba"
    versiones.mkdir()
    (versiones / "caso_9000_falla.py").write_text(
        REVISION_QUE_FALLA.format(abajo=revision_head(Destino.CASO)), encoding="utf-8"
    )
    original = base_datos._configuracion

    def con_la_revision_que_falla(destino: Destino):
        configuracion = original(destino)
        if destino is Destino.CASO:
            propias = base_datos.CARPETA_MIGRACIONES / "caso" / "versions"
            ubicaciones = os.pathsep.join([str(propias), str(versiones)]).replace("%", "%%")
            configuracion.set_main_option("version_locations", ubicaciones)
        return configuracion

    monkeypatch.setattr(base_datos, "_configuracion", con_la_revision_que_falla)
    base_datos._guion.cache_clear()
    try:
        ruta = _demo(tmp_path)
        antes = respaldo.huella(ruta)
        with pytest.raises(MigracionFallida, match="falla inyectada"):
            preparar_base(ruta)
        assert respaldo.huella(ruta) == antes
        assert not ruta.with_name(ruta.name + base_datos.SUFIJO_TRABAJO).exists()
        assert len(_juegos()) == 1
    finally:
        base_datos._guion.cache_clear()


def test_una_base_sin_modalidad_no_es_adoptable_y_no_se_toca(tmp_path: Path) -> None:
    ruta = _demo(tmp_path)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("ALTER TABLE composicion_apu DROP COLUMN modalidad")
        conexion.commit()
    antes = respaldo.huella(ruta)
    with pytest.raises(BaseNoAdoptable, match="composicion_apu: falta la columna modalidad"):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes


def test_una_base_de_una_version_mas_nueva_no_se_toca(tmp_path: Path) -> None:
    ruta = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    antes = respaldo.huella(ruta)
    with pytest.raises(BaseMasNueva, match="versión más nueva de Sílice"):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes and _juegos() == []


def test_un_archivo_que_no_es_sqlite_es_ilegible_y_no_se_toca(tmp_path: Path) -> None:
    ruta = tmp_path / "notas.db"
    ruta.write_text("esto no es una base\n" * 50, encoding="utf-8")
    antes = respaldo.huella(ruta)
    with pytest.raises(BaseIlegible, match="file is not a database"):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes


def test_una_base_con_una_pagina_danada_no_se_migra(tmp_path: Path) -> None:
    ruta = _demo(tmp_path)
    with closing(sqlite3.connect(ruta)) as conexion:
        tamano = conexion.execute("PRAGMA page_size").fetchone()[0]
        raiz = conexion.execute("SELECT rootpage FROM sqlite_master WHERE name = 'partida'").fetchone()[0]
    datos = bytearray(ruta.read_bytes())
    inicio = (raiz - 1) * tamano
    datos[inicio : inicio + 64] = b"\xff" * 64
    ruta.write_bytes(bytes(datos))
    antes = respaldo.huella(ruta)
    with pytest.raises(RespaldoFallido):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes and _juegos() == []


def test_una_base_bloqueada_por_otro_proceso_se_rechaza_sin_tocarla(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(respaldo, "ESPERA_BLOQUEO_S", 0.2)
    ruta = _demo(tmp_path)
    antes = respaldo.huella(ruta)
    otro = sqlite3.connect(ruta, isolation_level=None)
    try:
        otro.execute("BEGIN EXCLUSIVE")
        with pytest.raises(BaseBloqueada, match="bloqueada"):
            preparar_base(ruta)
    finally:
        otro.execute("ROLLBACK")
        otro.close()
    assert respaldo.huella(ruta) == antes


def test_una_base_que_cambia_durante_la_migracion_no_se_pisa(tmp_path: Path, monkeypatch) -> None:
    ruta = _demo(tmp_path)
    original = base_datos.aplicar_revisiones

    def y_mientras_otra_ventana_escribe(trabajo: Path, destino: Destino, objetivo: str = "head") -> None:
        original(trabajo, destino, objetivo)
        with closing(sqlite3.connect(ruta)) as conexion:
            conexion.execute(
                "INSERT INTO proyecto (nombre, descripcion, dominio) "
                "VALUES ('escrito durante la migracion', '', 'civil')"
            )
            conexion.commit()

    monkeypatch.setattr(base_datos, "aplicar_revisiones", y_mientras_otra_ventana_escribe)
    with pytest.raises(BaseBloqueada, match="cambió mientras se migraba"):
        preparar_base(ruta)
    with closing(sqlite3.connect(ruta)) as conexion:
        escritos = conexion.execute(
            "SELECT count(*) FROM proyecto WHERE nombre = 'escrito durante la migracion'"
        ).fetchone()[0]
        tablas = {n for (n,) in conexion.execute("SELECT name FROM sqlite_master")}
    assert escritos == 1 and "alembic_version" not in tablas


def test_disco_lleno_al_respaldar_no_migra_ni_toca_la_base(tmp_path: Path, monkeypatch) -> None:
    ruta = _demo(tmp_path)
    antes = respaldo.huella(ruta)

    def disco_lleno(_origen: Path, _destino: Path) -> None:
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(respaldo, "copiar_sqlite", disco_lleno)
    with pytest.raises(RespaldoFallido, match="disk is full"):
        preparar_base(ruta)
    assert respaldo.huella(ruta) == antes and _juegos() == []
    assert leer_estado(ruta).revision is None
    assert not ruta.with_name(ruta.name + base_datos.SUFIJO_TRABAJO).exists()


def test_adopcion_en_una_carpeta_de_onedrive_con_espacios_y_acentos(tmp_path: Path, monkeypatch) -> None:
    datos = tmp_path / "OneDrive - Personal" / "Escritorio" / "TÉSIS ñ" / "datos"
    monkeypatch.setenv(config.VARIABLE_DATOS, str(datos))
    ruta = bases_prueba.copiar_base("0.5.0", "of001.db", datos / "casos" / "Oficina Ñandú.db")
    resultado = preparar_base(ruta)
    assert resultado.juego is not None and resultado.juego.is_relative_to(datos.resolve())
    assert bases_prueba.diferencias_con_ficha(ruta, FICHA["bases"]["of001.db"]) == []


def test_la_base_de_la_instalacion_nace_vacia_con_su_alembic_version() -> None:
    ruta = config.ruta_instalacion()
    primero = preparar_base(ruta, Destino.INSTALACION)
    assert primero.nueva and primero.revision_destino is None
    with closing(sqlite3.connect(ruta)) as conexion:
        tablas = [n for (n,) in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    assert tablas == ["alembic_version"]
    segundo = preparar_base(ruta, Destino.INSTALACION)
    assert segundo.juego is None and not segundo.nueva


def test_migrar_lleva_todo_a_head_con_un_solo_juego() -> None:
    casos = config.carpeta_casos()
    bases_prueba.copiar_base("0.5.0", "demo.db", casos / "demo.db")
    bases_prueba.copiar_base("0.5.0", "ti001.db", casos / "ti001.db")
    preparar_base(casos / "silice.db")
    resultados = migrar_todo()
    [(_, ficha)] = _juegos()
    assert sorted(b["archivo"] for b in ficha["bases"]) == ["casos/demo.db", "casos/ti001.db", "instalacion.db"]
    assert {r.ruta.name: r.juego is not None for r in resultados} == {
        "instalacion.db": False, "demo.db": True, "silice.db": False, "ti001.db": True,
    }
    assert all(leer_estado(r.ruta).revision == revision_head(r.destino) for r in resultados)


def test_adoptar_la_base_de_trabajo_anterior_la_copia_y_no_la_toca(tmp_path: Path) -> None:
    anterior = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "data" / "apu.db")
    antes = respaldo.huella(anterior)
    resultado = base_datos.adoptar_base(anterior, "silice")
    assert resultado.ruta == config.ruta_caso_por_defecto()
    assert respaldo.huella(anterior) == antes
    assert bases_prueba.diferencias_con_ficha(resultado.ruta, FICHA["bases"]["demo.db"]) == []
    with pytest.raises(RutaDeCasoRechazada, match="Ya existe"):
        base_datos.adoptar_base(anterior, "silice")
```

`tests/unit/test_casos.py`:
```python
"""Casos en la carpeta de datos (RV-5; spec S5 §6.6): lista, nombres seguros y rutas rechazadas sin
tocar el disco (RF-96 e)."""

from __future__ import annotations

from pathlib import Path

import pytest

from operacion.base_datos import (
    BaseIlegible,
    BaseMasNueva,
    Destino,
    RutaDeCasoRechazada,
    crear_caso,
    leer_estado,
    listar_casos,
    resolver_caso,
    revision_head,
    sanear_nombre,
    subir_caso,
)
from tests.fixtures import bases_prueba

RECHAZADAS = [
    r"\\equipo\x\a.db", "//equipo/x/a.db", r"C:\x.db", "C:x.db", "/etc/x.db", "../x.db",
    r"casos\..\x.db", "sub/x.db", "a:b.db", "nul.db", "CON", "", "   ",
]


def test_la_lista_trae_solo_los_db_de_la_carpeta_en_orden(tmp_path: Path) -> None:
    carpeta = tmp_path / "casos"
    carpeta.mkdir()
    for nombre in ("b.db", "A.db", "notas.txt", "c.db.migrando"):
        (carpeta / nombre).write_bytes(b"")
    (carpeta / "sub.db").mkdir()
    assert [ruta.name for ruta in listar_casos(carpeta)] == ["A.db", "b.db"]


def test_sin_carpeta_la_lista_es_vacia_y_no_la_crea(tmp_path: Path) -> None:
    carpeta = tmp_path / "no_existe"
    assert listar_casos(carpeta) == [] and not carpeta.exists()


@pytest.mark.parametrize("nombre", RECHAZADAS)
def test_unc_absolutas_puntos_y_carpetas_se_rechazan_sin_tocar_el_disco(tmp_path: Path, nombre: str) -> None:
    carpeta = tmp_path / "casos"
    with pytest.raises(RutaDeCasoRechazada):
        resolver_caso(nombre, carpeta)
    assert list(tmp_path.iterdir()) == []


def test_un_nombre_con_tildes_y_espacios_queda_dentro_de_la_carpeta(tmp_path: Path) -> None:
    assert resolver_caso("Obra Ñandú 2026", tmp_path) == tmp_path.resolve() / "Obra Ñandú 2026.db"


@pytest.mark.parametrize(
    ("original", "saneado"),
    [
        ("..\\..\\evil.db", "evil.db"),
        ("C:\\Users\\x\\Mi caso.db", "Mi caso.db"),
        ("presupuesto final?.db", "presupuesto final_.db"),
        ("Oficina Ñandú", "Oficina Ñandú.db"),
        ("informe: v2.db", "informe_ v2.db"),
    ],
)
def test_sanear_deja_solo_un_nombre_seguro(original: str, saneado: str) -> None:
    assert sanear_nombre(original) == saneado


@pytest.mark.parametrize("original", ["CON.db", "nul", " .db", ".."])
def test_sanear_rechaza_nombres_vacios_o_reservados(original: str) -> None:
    with pytest.raises(RutaDeCasoRechazada):
        sanear_nombre(original)


def test_crear_un_caso_lo_deja_en_head_y_no_lo_repite(tmp_path: Path) -> None:
    resultado = crear_caso("Obra nueva", tmp_path / "casos")
    assert resultado.nueva and resultado.ruta.name == "Obra nueva.db"
    assert leer_estado(resultado.ruta).revision == revision_head(Destino.CASO)
    with pytest.raises(RutaDeCasoRechazada, match="Ya existe"):
        crear_caso("Obra nueva", tmp_path / "casos")


def test_crear_con_una_ruta_se_rechaza_sin_crear_nada(tmp_path: Path) -> None:
    with pytest.raises(RutaDeCasoRechazada):
        crear_caso("..\\fuera", tmp_path / "casos")
    assert list(tmp_path.iterdir()) == []


def test_subir_un_caso_lo_copia_con_nombre_saneado_y_lo_migra(tmp_path: Path) -> None:
    contenido = (bases_prueba.carpeta_version("0.5.0") / "demo.db").read_bytes()
    resultado = subir_caso("C:\\Descargas\\Caso de Ana?.db", contenido, tmp_path / "casos")
    assert resultado.ruta.name == "Caso de Ana_.db" and resultado.juego is not None
    assert leer_estado(resultado.ruta).revision == revision_head(Destino.CASO)


def test_subir_algo_que_no_es_sqlite_no_deja_archivo(tmp_path: Path) -> None:
    with pytest.raises(BaseIlegible):
        subir_caso("notas.db", b"hola", tmp_path / "casos")
    assert not (tmp_path / "casos" / "notas.db").exists()


def test_subir_una_base_mas_nueva_no_la_deja_en_la_carpeta(tmp_path: Path) -> None:
    futura = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    with pytest.raises(BaseMasNueva):
        subir_caso("futura.db", futura.read_bytes(), tmp_path / "casos")
    assert not (tmp_path / "casos" / "futura.db").exists()
```

`tests/integration/test_operacion_cli.py`:
```python
"""`python -m operacion` (spec S5 §6.5): adoptar la base de trabajo anterior y las órdenes de consulta,
respaldo y restauración, con la carpeta de datos temporal de `tests/conftest.py`."""

from __future__ import annotations

from pathlib import Path

from operacion import config, respaldo
from operacion.__main__ import main
from operacion.base_datos import Destino, revision_head
from tests.fixtures import bases_prueba


def test_adoptar_y_las_demas_ordenes(tmp_path: Path, capsys) -> None:
    anterior = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "data" / "apu.db")
    antes = respaldo.huella(anterior)
    assert main(["adoptar", str(anterior), "--nombre", "silice"]) == 0
    assert respaldo.huella(anterior) == antes
    assert main(["casos"]) == 0
    assert "silice.db" in capsys.readouterr().out
    assert main(["revision"]) == 0
    assert f"silice.db: {revision_head(Destino.CASO)}" in capsys.readouterr().out
    assert main(["respaldar"]) == 0
    manuales = [c for c, f in respaldo.listar_juegos(config.carpeta_respaldos()) if f["motivo"] == "manual"]
    assert len(manuales) == 1
    assert main(["restaurar", str(manuales[0]), "--solo-caso", "silice"]) == 0
    assert main(["migrar"]) == 0


def test_un_error_de_base_sale_con_1_y_su_mensaje(tmp_path: Path, capsys) -> None:
    futura = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    assert main(["adoptar", str(futura)]) == 1
    assert "versión más nueva" in capsys.readouterr().err
    assert not (config.carpeta_casos() / "futura.db").exists()
```

- [ ] **Paso 2: Correrla y ver el rojo; commit de la prueba**
Run: `uv run pytest tests/integration/test_preparar_base.py tests/unit/test_casos.py tests/integration/test_operacion_cli.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'BaseBloqueada' from 'operacion.base_datos'` (y
`No module named 'operacion.__main__'`).
```bash
git add tests/integration/test_preparar_base.py tests/unit/test_casos.py tests/integration/test_operacion_cli.py
git commit -m "test(operacion): preparar_base, adopcion, casos y orden operacion (rojo)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/base_datos.py`: reemplazar el docstring del módulo por
```python
"""Abrir una base de Sílice: `preparar_base` y la lista de casos (RF-96; spec S5 §6.4 y §6.6).

Un caso se abre **solo** con `preparar_base` (RV-5). Una base nueva nace en `head` por las
revisiones. Una base anterior (sin `alembic_version`: la 0.5.0 o una de desarrollo creada con
`create_all`) o con una revisión vieja se **respalda** (juego con ficha, `operacion.respaldo`), se
migra sobre una **copia de trabajo** y, solo si llega entera a `head`, se devuelve a su archivo con
la API de respaldo de `sqlite3`, que es transaccional: si algo falla antes, el archivo original no
se tocó (su SHA-256 es el de antes). Una base de una versión más nueva, ilegible, bloqueada o no
adoptable se rechaza con un mensaje que dice qué hacer, sin modificarla.

Dos destinos (DA-S5-7): la base de cada caso y la de la instalación, cada una con su entorno en
`migraciones/<destino>/` y su `alembic_version`. Sin `alembic.ini`: la configuración se arma aquí.

Los casos viven en `<datos>/casos/` y se eligen de `listar_casos`; un nombre que llega del usuario
pasa por `resolver_caso` (`resolve` + `is_relative_to`): se rechazan rutas UNC, absolutas, con `..`
o con carpetas antes de tocar el disco. `SILICE_CASO` y `APU_BASE` son configuración de quien
arranca (el lanzador, las pruebas), no entrada del usuario: se preparan sin pasar por la lista.
"""
```
reemplazar las importaciones por
```python
from __future__ import annotations

import functools
import re
import shutil
import sqlite3
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.pool import NullPool

import migraciones
from migraciones.comun import BaseNoAdoptable, ErrorDeBase
from operacion import config, respaldo
from operacion.respaldo import RespaldoFallido, Restauracion
```
cambiar `__all__` por `__all__ = ["BaseNoAdoptable", "ErrorDeBase", "RespaldoFallido", "Restauracion"]` y agregar
al final:
```python
SUFIJO_TRABAJO = ".migrando"
EXTENSION = ".db"
LARGO_MAXIMO_NOMBRE = 80
CABECERA_SQLITE = b"SQLite format 3\x00"
MENSAJE_MAS_NUEVA = (
    "Esta base ({nombre}) es de una versión más nueva de Sílice (revisión {revision}). Instale esa "
    "versión o restaure el respaldo previo; no se modificó."
)
_RESERVADOS_WINDOWS = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(1, 10)), *(f"LPT{n}" for n in range(1, 10))}
)
_NO_PERMITIDO = re.compile(r"[^\w\- .]")  # `\w` es Unicode: conserva tildes y ñ


class RutaDeCasoRechazada(ErrorDeBase):  # noqa: N818
    """El nombre o la ruta de un caso sale de la carpeta de casos; se rechaza antes de tocar el disco."""


class BaseIlegible(ErrorDeBase):  # noqa: N818
    """El archivo no es una base SQLite legible (o es una carpeta)."""


class BaseBloqueada(ErrorDeBase):  # noqa: N818
    """Otro proceso tiene la base bloqueada o la cambió durante la migración; no se modificó."""


class BaseMasNueva(ErrorDeBase):  # noqa: N818
    """La base tiene una revisión que este código no conoce (bajó de versión, §6.4 3d)."""


@dataclass(frozen=True, slots=True)
class EstadoBase:
    """Lo que se lee de una base sin escribir nada."""

    existe: bool
    tablas: frozenset[str] = frozenset()
    revision: str | None = None

    @property
    def sin_datos(self) -> bool:
        return not (self.tablas - {respaldo.TABLA_VERSION})


@dataclass(frozen=True, slots=True)
class ResultadoPreparacion:
    ruta: Path
    destino: Destino
    revision_origen: str | None  # `None`: base sin `alembic_version` (adoptada) o nueva
    revision_destino: str | None  # `head` del destino; `None` mientras no tenga revisiones
    juego: Path | None  # el juego de respaldo previo, si hubo que migrar una base con datos
    nueva: bool  # la base no existía o no tenía tablas


def _es_bloqueo(error: sqlite3.Error) -> bool:
    texto = str(error).lower()
    return "locked" in texto or "busy" in texto


def leer_estado(ruta: Path) -> EstadoBase:
    """Existencia, tablas y revisión, con una conexión de solo lectura: nunca crea ni escribe."""
    ruta = Path(ruta)
    if not ruta.exists():
        return EstadoBase(existe=False)
    if ruta.is_dir():
        raise BaseIlegible(f"{ruta} es una carpeta, no una base de Sílice.")
    try:
        with closing(respaldo.abrir_solo_lectura(ruta)) as conexion:
            tablas = frozenset(respaldo.tablas_de(conexion))
            revision = respaldo.revision_de(conexion)
    except sqlite3.OperationalError as error:
        if _es_bloqueo(error):
            raise BaseBloqueada(
                f"La base {ruta.name} está bloqueada por otro programa ({error}). Ciérrelo y "
                "vuelva a intentarlo; no se modificó."
            ) from error
        raise BaseIlegible(
            f"{ruta.name} no es una base de Sílice legible ({error}). Restaure un respaldo o elija "
            "otro caso."
        ) from error
    except sqlite3.DatabaseError as error:
        raise BaseIlegible(
            f"{ruta.name} no es una base de Sílice legible ({error}). Restaure un respaldo o elija "
            "otro caso."
        ) from error
    return EstadoBase(existe=True, tablas=tablas, revision=revision)


def _heads() -> dict[str, str | None]:
    return {destino.value: revision_head(destino) for destino in Destino}


def _clasificar(ruta: Path, destino: Destino) -> tuple[str, EstadoBase]:
    """«al_dia», «nueva» o «pendiente»; `BaseMasNueva` si la revisión es desconocida."""
    estado = leer_estado(ruta)
    if estado.existe and respaldo.TABLA_VERSION in estado.tablas:
        if estado.revision == revision_head(destino):
            return "al_dia", estado
    if estado.revision is not None and estado.revision not in revisiones_conocidas(destino):
        raise BaseMasNueva(MENSAJE_MAS_NUEVA.format(nombre=ruta.name, revision=estado.revision))
    if not estado.existe or estado.sin_datos:
        return "nueva", estado
    return "pendiente", estado


def _crear(ruta: Path, destino: Destino) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        aplicar_revisiones(ruta, destino)
    except ErrorDeBase:
        raise
    except Exception as error:  # una revisión puede lanzar cualquier cosa
        raise MigracionFallida(f"No se pudo crear {ruta.name}: {error}.") from error


def _devolver(
    bases: Sequence[tuple[Path, Destino]],
    trabajos: Mapping[Path, Path],
    huellas: Mapping[Path, str],
    juego: Path,
) -> None:
    """Devuelve cada copia migrada a su archivo; si una no se puede, repone las ya devueltas."""
    devueltas: list[tuple[Path, Destino]] = []
    for ruta, destino in bases:
        try:
            if respaldo.huella(ruta) != huellas[ruta]:
                raise BaseBloqueada(
                    f"La base {ruta.name} cambió mientras se migraba (¿otra ventana de Sílice la "
                    "usa?). No se modificó: vuelva a abrirla."
                )
            respaldo.copiar_sqlite(trabajos[ruta], ruta)
        except (BaseBloqueada, OSError, sqlite3.Error) as error:
            for ya, su_destino in devueltas:
                respaldo.copiar_sqlite(respaldo.ruta_en_juego(juego, ya, su_destino.value), ya)
            if isinstance(error, BaseBloqueada):
                raise
            raise BaseBloqueada(
                f"No se pudo escribir {ruta.name} ({error}): otro programa la tiene abierta. No se "
                f"modificó; el respaldo previo está en {juego}."
            ) from error
        devueltas.append((ruta, destino))


def _migrar(bases: Sequence[tuple[Path, Destino]], entorno: Mapping[str, str] | None) -> Path:
    """Un juego para todas; cada una se migra en su copia de trabajo y se devuelve solo si todas
    llegaron a `head`. Un fallo antes de devolver deja los originales intactos (RF-96 c)."""
    huellas = {ruta: respaldo.huella(ruta) for ruta, _ in bases}
    ruta_instalacion = next(
        (ruta for ruta, destino in bases if destino is Destino.INSTALACION),
        config.ruta_instalacion(entorno),
    )
    juego = respaldo.respaldar(
        [ruta for ruta, destino in bases if destino is Destino.CASO],
        respaldo.MOTIVO_MIGRACION,
        ruta_instalacion=ruta_instalacion,
        carpeta_respaldos=config.carpeta_respaldos(entorno),
        heads=_heads(),
    )
    trabajos: dict[Path, Path] = {}
    try:
        for ruta, destino in bases:
            trabajo = ruta.with_name(ruta.name + SUFIJO_TRABAJO)
            trabajo.unlink(missing_ok=True)
            shutil.copyfile(respaldo.ruta_en_juego(juego, ruta, destino.value), trabajo)
            trabajos[ruta] = trabajo
            try:
                aplicar_revisiones(trabajo, destino)
            except ErrorDeBase:
                raise
            except Exception as error:  # una revisión puede lanzar cualquier cosa
                raise MigracionFallida(
                    f"La migración de {ruta.name} falló ({type(error).__name__}: {error}). La base "
                    f"no se modificó; el respaldo previo está en {juego}."
                ) from error
        _devolver(bases, trabajos, huellas, juego)
    finally:
        for trabajo in trabajos.values():
            trabajo.unlink(missing_ok=True)
    respaldo.podar_juegos(config.carpeta_respaldos(entorno))
    return juego


def preparar_base(
    ruta: Path, destino: Destino = Destino.CASO, *, entorno: Mapping[str, str] | None = None
) -> ResultadoPreparacion:
    """El único camino para abrir una base (RV-5): al día, la deja; nueva, la crea en `head`;
    anterior, la respalda y la migra (spec S5 §6.4). Idempotente."""
    ruta = Path(ruta)
    clase, estado = _clasificar(ruta, destino)
    head = revision_head(destino)
    if clase == "al_dia":
        return ResultadoPreparacion(ruta, destino, estado.revision, head, None, False)
    if clase == "nueva":
        _crear(ruta, destino)
        return ResultadoPreparacion(ruta, destino, None, head, None, True)
    juego = _migrar([(ruta, destino)], entorno)
    return ResultadoPreparacion(ruta, destino, estado.revision, head, juego, False)


def migrar_todo(entorno: Mapping[str, str] | None = None) -> list[ResultadoPreparacion]:
    """La instalación y todos los casos de la carpeta a `head`, con un solo juego (spec S5 §5.4)."""
    candidatos = [(config.ruta_instalacion(entorno), Destino.INSTALACION)]
    candidatos += [(caso, Destino.CASO) for caso in listar_casos(entorno=entorno)]
    resultados: list[ResultadoPreparacion] = []
    pendientes: list[tuple[Path, Destino, str | None]] = []
    for ruta, destino in candidatos:
        clase, estado = _clasificar(ruta, destino)
        head = revision_head(destino)
        if clase == "al_dia":
            resultados.append(ResultadoPreparacion(ruta, destino, estado.revision, head, None, False))
        elif clase == "nueva":
            _crear(ruta, destino)
            resultados.append(ResultadoPreparacion(ruta, destino, None, head, None, True))
        else:
            pendientes.append((ruta, destino, estado.revision))
    if pendientes:
        juego = _migrar([(ruta, destino) for ruta, destino, _ in pendientes], entorno)
        resultados += [
            ResultadoPreparacion(ruta, destino, origen, revision_head(destino), juego, False)
            for ruta, destino, origen in pendientes
        ]
    return resultados


def respaldar_todo(entorno: Mapping[str, str] | None = None) -> Path:
    """Juego manual de la instalación y de todos los casos (no se poda nunca)."""
    return respaldo.respaldar(
        listar_casos(entorno=entorno),
        respaldo.MOTIVO_MANUAL,
        ruta_instalacion=config.ruta_instalacion(entorno),
        carpeta_respaldos=config.carpeta_respaldos(entorno),
        heads=_heads(),
    )


def restaurar_juego(
    juego: Path, *, solo_caso: str | None = None, entorno: Mapping[str, str] | None = None
) -> Restauracion:
    return respaldo.restaurar(
        Path(juego),
        ruta_instalacion=config.ruta_instalacion(entorno),
        carpeta_casos=config.carpeta_casos(entorno),
        carpeta_datos=config.carpeta_datos(entorno),
        carpeta_respaldos=config.carpeta_respaldos(entorno),
        heads=_heads(),
        conocidas={destino.value: revisiones_conocidas(destino) for destino in Destino},
        solo_caso=solo_caso,
    )


def motor_solo_lectura(ruta: Path) -> Engine:
    """Motor que no puede escribir (URI `mode=ro`): leer el estado no emite DDL ni crea el archivo."""
    uri = respaldo.uri_solo_lectura(Path(ruta))
    return create_engine(
        "sqlite://",
        creator=lambda: sqlite3.connect(uri, uri=True, check_same_thread=False),
        poolclass=NullPool,
    )


# --- casos en la carpeta de datos (spec S5 §6.6) --------------------------------------------------


def _carpeta(carpeta: Path | None, entorno: Mapping[str, str] | None) -> Path:
    return config.carpeta_casos(entorno) if carpeta is None else Path(carpeta)


def _es_reservado(nombre: str) -> bool:
    return PureWindowsPath(nombre).name.split(".")[0].strip().upper() in _RESERVADOS_WINDOWS


def _validar_forma(texto: str) -> None:
    """Rechaza UNC, absolutas, `..`, carpetas, `:` (unidad o flujo alterno de NTFS) y nombres
    reservados de Windows, sin resolver nada en el disco."""
    if not texto:
        raise RutaDeCasoRechazada("Elija un caso: el nombre no puede quedar vacío.")
    if texto.startswith(("\\\\", "//")):
        raise RutaDeCasoRechazada(f"«{texto}» es una ruta de red (UNC): elija un caso de la lista.")
    ventanas, posix = PureWindowsPath(texto), PurePosixPath(texto)
    if ventanas.drive or ventanas.root or posix.is_absolute():
        raise RutaDeCasoRechazada(f"«{texto}» es una ruta absoluta: elija un caso de la lista.")
    if ".." in ventanas.parts or ".." in posix.parts:
        raise RutaDeCasoRechazada(f"«{texto}» sale de la carpeta de casos (..).")
    if len(ventanas.parts) != 1 or len(posix.parts) != 1:
        raise RutaDeCasoRechazada(f"«{texto}» lleva carpetas: escriba solo el nombre del caso.")
    if ":" in texto:
        raise RutaDeCasoRechazada(f"«{texto}» no puede llevar «:».")
    if _es_reservado(texto):
        raise RutaDeCasoRechazada(f"«{texto}» es un nombre reservado de Windows: elija otro.")


def listar_casos(
    carpeta: Path | None = None, *, entorno: Mapping[str, str] | None = None
) -> list[Path]:
    """Los `.db` de la carpeta de casos, por nombre; vacía (y sin crearla) si no existe."""
    carpeta = _carpeta(carpeta, entorno)
    if not carpeta.is_dir():
        return []
    return sorted(
        (ruta for ruta in carpeta.iterdir() if ruta.is_file() and ruta.suffix.lower() == EXTENSION),
        key=lambda ruta: ruta.name.casefold(),
    )


def resolver_caso(
    nombre: str, carpeta: Path | None = None, *, entorno: Mapping[str, str] | None = None
) -> Path:
    """La ruta del caso `nombre` dentro de la carpeta de casos (`resolve` + `is_relative_to`).
    `RutaDeCasoRechazada` antes de tocar el disco si sale de ella."""
    texto = nombre.strip()
    _validar_forma(texto)
    if not texto.lower().endswith(EXTENSION):
        texto += EXTENSION
    base = _carpeta(carpeta, entorno).resolve()
    ruta = (base / texto).resolve()
    if not ruta.is_relative_to(base) or ruta.parent != base:
        raise RutaDeCasoRechazada(f"«{nombre.strip()}» queda fuera de la carpeta de casos.")
    return ruta


def sanear_nombre(nombre: str) -> str:
    """Nombre de archivo seguro para un caso nuevo o subido: solo la última parte, sin caracteres
    raros (conserva tildes y ñ), con `.db`. `RutaDeCasoRechazada` si queda vacío o reservado."""
    ultimo = unicodedata.normalize("NFC", PureWindowsPath(nombre.replace("/", "\\")).name)
    if ultimo.lower().endswith(EXTENSION):
        ultimo = ultimo[: -len(EXTENSION)]
    limpio = _NO_PERMITIDO.sub("_", ultimo).strip(" .")[:LARGO_MAXIMO_NOMBRE].strip(" .")
    if not limpio or _es_reservado(limpio):
        raise RutaDeCasoRechazada(
            f"«{nombre}» no sirve como nombre de caso: use letras, números, espacios, guiones o puntos."
        )
    return limpio + EXTENSION


def crear_caso(
    nombre: str, carpeta: Path | None = None, *, entorno: Mapping[str, str] | None = None
) -> ResultadoPreparacion:
    _validar_forma(nombre.strip())
    ruta = resolver_caso(sanear_nombre(nombre), carpeta, entorno=entorno)
    if ruta.exists():
        raise RutaDeCasoRechazada(f"Ya existe el caso {ruta.name}: ábralo de la lista o elija otro nombre.")
    return preparar_base(ruta, entorno=entorno)


def subir_caso(
    nombre_original: str,
    contenido: bytes,
    carpeta: Path | None = None,
    *,
    entorno: Mapping[str, str] | None = None,
) -> ResultadoPreparacion:
    """Copia un `.db` subido a la carpeta de casos con nombre saneado y lo prepara; si no se puede
    preparar, no queda en la carpeta."""
    ruta = resolver_caso(sanear_nombre(nombre_original), carpeta, entorno=entorno)
    if ruta.exists():
        raise RutaDeCasoRechazada(
            f"Ya hay un caso llamado {ruta.name}: cambie el nombre del archivo antes de subirlo."
        )
    if not contenido.startswith(CABECERA_SQLITE):
        raise BaseIlegible(f"«{nombre_original}» no es una base de Sílice (SQLite): no se guardó.")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)
    try:
        return preparar_base(ruta, entorno=entorno)
    except ErrorDeBase:
        ruta.unlink(missing_ok=True)
        raise


def adoptar_base(
    origen: Path, nombre: str | None = None, *, entorno: Mapping[str, str] | None = None
) -> ResultadoPreparacion:
    """Adopta una base que vive fuera de la carpeta de casos (la `data/apu.db` de la 0.5.0, la de
    `SILICE_CASO` o la de `APU_BASE`): la COPIA con la API de respaldo a `<datos>/casos/` y prepara
    la copia. El original nunca se modifica (huella igual)."""
    origen = Path(origen)
    if not leer_estado(origen).existe:
        raise BaseIlegible(f"No existe {origen}.")
    ruta = resolver_caso(sanear_nombre(nombre or origen.name), entorno=entorno)
    if ruta.exists():
        raise RutaDeCasoRechazada(f"Ya existe el caso {ruta.name}: adopte con otro --nombre.")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        respaldo.copiar_sqlite(origen, ruta)
    except sqlite3.Error as error:
        ruta.unlink(missing_ok=True)
        raise BaseIlegible(f"No se pudo copiar {origen}: {error}.") from error
    try:
        return preparar_base(ruta, entorno=entorno)
    except ErrorDeBase:
        ruta.unlink(missing_ok=True)
        raise
```
(agregar `from contextlib import closing` a las importaciones).

`operacion/__main__.py`:
```python
"""`python -m operacion` (spec S5 §6.5): casos, revisión, migrar, respaldar, restaurar y adoptar.

En la 0.6.0 se corre a mano en desarrollo (`uv run python -m operacion …`); desde la 1.0.0 la llaman
el instalador y el lanzador. `restaurar` exige Sílice detenido: hasta que el lanzador (S5-2) deje
`estado/servidor.json`, lo comprueba quien la ejecuta.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from operacion import base_datos, config, respaldo


def _texto_revision(estado: base_datos.EstadoBase) -> str:
    if not estado.existe:
        return "no existe"
    if respaldo.TABLA_VERSION not in estado.tablas:
        return "sin alembic_version"
    return estado.revision or "sin revisiones"


def _casos(_argumentos: argparse.Namespace) -> int:
    casos = base_datos.listar_casos()
    print("\n".join(r.name for r in casos) if casos else f"(ningún caso en {config.carpeta_casos()})")
    return 0


def _revision(_argumentos: argparse.Namespace) -> int:
    bases = [(config.ruta_instalacion(), base_datos.Destino.INSTALACION)]
    bases += [(caso, base_datos.Destino.CASO) for caso in base_datos.listar_casos()]
    for ruta, destino in bases:
        head = base_datos.revision_head(destino) or "sin revisiones"
        print(f"{ruta.name}: {_texto_revision(base_datos.leer_estado(ruta))} (head {head})")
    return 0


def _migrar(_argumentos: argparse.Namespace) -> int:
    for resultado in base_datos.migrar_todo():
        if resultado.nueva:
            detalle = "creada"
        elif resultado.juego is not None:
            detalle = f"migrada (respaldo previo: {resultado.juego})"
        else:
            detalle = "al día"
        print(f"{resultado.ruta.name}: {detalle}")
    return 0


def _respaldar(_argumentos: argparse.Namespace) -> int:
    print(base_datos.respaldar_todo())
    return 0


def _restaurar(argumentos: argparse.Namespace) -> int:
    resultado = base_datos.restaurar_juego(argumentos.juego, solo_caso=argumentos.solo_caso)
    print("Restauradas: " + ", ".join(ruta.name for ruta in resultado.restauradas))
    print(f"Bases de antes de restaurar: {resultado.antes}")
    if resultado.eventos_perdidos is not None:
        print(f"Eventos de seguridad perdidos (revíselos): {resultado.eventos_perdidos}")
    return 0


def _adoptar(argumentos: argparse.Namespace) -> int:
    resultado = base_datos.adoptar_base(argumentos.origen, argumentos.nombre)
    print(
        f"Adoptada en {resultado.ruta} (revisión {resultado.revision_destino}); respaldo previo: "
        f"{resultado.juego}. El original no se modificó."
    )
    return 0


_ORDENES: dict[str, Callable[[argparse.Namespace], int]] = {
    "casos": _casos,
    "revision": _revision,
    "migrar": _migrar,
    "respaldar": _respaldar,
    "restaurar": _restaurar,
    "adoptar": _adoptar,
}


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(prog="python -m operacion", description=__doc__.splitlines()[0])
    ordenes = analizador.add_subparsers(dest="orden", required=True)
    ordenes.add_parser("casos", help="lista los casos de la carpeta de datos")
    ordenes.add_parser("revision", help="revisión de cada base y la head de su destino")
    ordenes.add_parser("migrar", help="lleva a head la instalación y todos los casos, con un solo juego")
    ordenes.add_parser("respaldar", help="juego manual de la instalación y de todos los casos")
    restaurar = ordenes.add_parser("restaurar", help="restaura un juego (con Sílice detenido)")
    restaurar.add_argument("juego", type=Path)
    restaurar.add_argument("--solo-caso", dest="solo_caso")
    adoptar = ordenes.add_parser("adoptar", help="copia una base anterior a la carpeta de casos y la migra")
    adoptar.add_argument("origen", type=Path)
    adoptar.add_argument("--nombre")
    argumentos = analizador.parse_args(argv)
    try:
        return _ORDENES[argumentos.orden](argumentos)
    except base_datos.ErrorDeBase as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/integration/test_preparar_base.py tests/unit/test_casos.py tests/integration/test_operacion_cli.py tests/integration/test_respaldo.py tests/integration/test_migraciones.py tests/unit/test_arquitectura_s5.py -v -W error`
Esperado: PASS. Luego `uv run pytest -q -W error` y `uv run ruff check operacion tests/integration/test_preparar_base.py tests/unit/test_casos.py tests/integration/test_operacion_cli.py`.

- [ ] **Paso 5: Commit**
```bash
git add operacion/base_datos.py operacion/__main__.py
git commit -m "feat(operacion): preparar_base con respaldo y copia de trabajo, casos en la carpeta y orden operacion" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 6: interfaz y API: lista de casos, `estado_caso` sin DDL, nueve páginas y la API vía `preparar_base`

**Rama:** `inc/060-s5-1-alembic` (sale de `main`; PR a `main`; ver RV-2)   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Modificar: `ui/caso.py` (completo), `ui/paginas/inicio.py` (completo), `api/dependencias.py` (completo),
  `ui/paginas/actualizacion.py:58-66,171-181,266`, `ui/paginas/catalogo.py:17,31,38`, `ui/paginas/componer.py:41-54,146`,
  `ui/paginas/elaborar.py:52,159,268`, `ui/paginas/escenarios.py:43,65`, `ui/paginas/historico.py:19,39,44`,
  `ui/paginas/hoja.py:58,123-136`, `ui/paginas/similares.py:32,63`, `ui/paginas/simulador.py:21,75`,
  `ui/elaboracion.py:13`, `tests/unit/test_ui_caso.py:12-23,57-58`, `tests/unit/test_ui_inicio.py:15-45,104-118`
- Prueba: `tests/unit/test_arquitectura_s5.py` (agregar), `tests/unit/test_ui_caso.py`, `tests/unit/test_ui_inicio.py`,
  `tests/unit/test_ui_paginas_preparan_el_caso.py`, `tests/integration/test_api_preparar_base.py`

**Interfaces:**
- Consume: `operacion.base_datos` (`preparar_base`, `ErrorDeBase`, `RutaDeCasoRechazada`, `MENSAJE_MAS_NUEVA`,
  `Destino`, `leer_estado`, `motor_solo_lectura`, `resolver_caso`, `revision_head`, `revisiones_conocidas`,
  `listar_casos`, `crear_caso`, `subir_caso`); `operacion.config` (`carpeta_casos`, `ruta_caso_por_defecto`,
  `BASE_ANTERIOR`); `tests.fixtures.bases_prueba`.
- Produce: `ui.caso.RUTA_BASE_POR_DEFECTO = None` (sigue siendo la que parchan las pruebas),
  `ui.caso.puede_cambiar_de_caso() -> bool` (gancho de S3), `ui.caso.abrir_caso(nombre, carpeta=None) -> Path`,
  `ui.caso.SIN_PERMISO_DE_CAMBIO: str`, `EstadoCaso.por_migrar: bool = False`; rótulos de
  `ui.paginas.inicio`: `ROTULO_CASO`, `ROTULO_ABRIR`, `ROTULO_NUEVO`, `ROTULO_CREAR`, `ROTULO_SUBIR`,
  `ROTULO_GUARDAR_SUBIDA`, `ROTULO_SEMBRAR`, `ROTULO_RECORRIDO`, `PREFIJO_CASO_ABIERTO`, `MENSAJE_BASE_ANTERIOR`
  (desaparece `ROTULO_ARCHIVO`); `api.dependencias.VARIABLE_BASE = "APU_BASE"`, `url_por_defecto() -> str`,
  `ruta_de_url(url) -> Path | None` (desaparece `URL_POR_DEFECTO`).

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_arquitectura_s5.py`, agregar a las importaciones `from tests.fixtures.arquitectura import RAIZ, llamadas`
y al final:
```python
#: Las nueve páginas que abren el caso con un motor propio (spec S5 §1.2): todas lo preparan.
PAGINAS_QUE_ABREN_EL_CASO = (
    "actualizacion", "catalogo", "componer", "elaborar", "escenarios", "historico", "hoja",
    "similares", "simulador",
)


def test_ni_la_interfaz_ni_la_api_crean_el_esquema() -> None:
    """RV-5: `crear_esquema` queda para las pruebas en memoria y los scripts de siembra."""
    infractores = sorted(
        f"{ruta(archivo)}:{linea}"
        for paquete in ("ui", "api")
        for archivo in archivos(paquete)
        for linea in llamadas(archivo, "crear_esquema")
    )
    assert infractores == []


def test_la_lista_de_paginas_que_abren_el_caso_esta_completa() -> None:
    con_motor = sorted(
        archivo.stem
        for archivo in (RAIZ / "ui" / "paginas").glob("*.py")
        if llamadas(archivo, "crear_motor")
    )
    assert con_motor == sorted(PAGINAS_QUE_ABREN_EL_CASO)


@pytest.mark.parametrize("pagina", PAGINAS_QUE_ABREN_EL_CASO)
def test_cada_pagina_que_abre_el_caso_lo_prepara(pagina: str) -> None:
    assert llamadas(RAIZ / "ui" / "paginas" / f"{pagina}.py", "preparar_base")
```

`tests/unit/test_ui_caso.py`: en las importaciones (líneas 12-23) quitar `RUTA_BASE_POR_DEFECTO` del bloque y agregar
```python
import hashlib

from sqlalchemy import Engine, event

from operacion.config import ruta_caso_por_defecto
from tests.fixtures.bases_prueba import crear_base_futura
from ui import caso as caso_ui
```
reemplazar el test de las líneas 57-58 por
```python
def test_sin_sesion_ni_entorno_queda_el_caso_por_defecto_de_la_carpeta_de_datos(tmp_path: Path) -> None:
    assert caso_ui.RUTA_BASE_POR_DEFECTO is None
    por_defecto = str(ruta_caso_por_defecto({"SILICE_DATOS": str(tmp_path)}))
    assert resolver_ruta(None, {}, por_defecto) == tmp_path.resolve() / "casos" / "silice.db"
```
y agregar al final:
```python
# --- estado sin DDL y bases que no están en head (RV-5) ---------------------------------------


def test_estado_caso_no_emite_ddl_ni_cambia_el_archivo(tmp_path: Path) -> None:
    ruta = _base_sembrada(tmp_path / "sembrada.db")
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    sentencias: list[str] = []

    def anotar(_conexion, _cursor, sentencia, *_resto) -> None:
        sentencias.append(sentencia)

    event.listen(Engine, "before_cursor_execute", anotar)
    try:
        estado = estado_caso(ruta)
    finally:
        event.remove(Engine, "before_cursor_execute", anotar)
    assert estado.partidas == len(APUS_LINEA_BASE) and estado.por_migrar
    primeras = {s.lstrip().split(" ", 1)[0].upper() for s in sentencias}
    assert sentencias and not primeras & {"CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE"}
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes


def test_estado_de_una_base_mas_nueva_es_un_error_con_mensaje(tmp_path: Path) -> None:
    estado = estado_caso(crear_base_futura(tmp_path / "futura.db"))
    assert estado.error and "versión más nueva" in estado.error


def test_el_resumen_avisa_que_el_caso_se_actualizara(tmp_path: Path) -> None:
    estado = EstadoCaso(tmp_path / "x.db", True, partidas=1, insumos=2, por_migrar=True)
    assert resumen_caso(estado).endswith("se actualizara al abrirlo")
```

`tests/unit/test_ui_inicio.py`: reemplazar las importaciones de las líneas 15-18 por
```python
from operacion.base_datos import Destino, leer_estado, preparar_base, resolver_caso, revision_head
from operacion.config import carpeta_casos
from ui.caso import CLAVE_CASO, CLAVE_RECORRIDO, SIN_PERMISO_DE_CAMBIO, estado_caso
from ui.paginas.inicio import (
    PREFIJO_CASO_ABIERTO,
    ROTULO_ABRIR,
    ROTULO_CASO,
    ROTULO_CREAR,
    ROTULO_NUEVO,
    ROTULO_RECORRIDO,
    ROTULO_SEMBRAR,
)
```
reemplazar `_inicio` (líneas 36-45) por
```python
def _inicio(monkeypatch, base: Path, *, tiempo: int = 60) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=tiempo)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any(c.value == f"{PREFIJO_CASO_ABIERTO}{base}" for c in at.caption), (
        "la desviacion de ui.caso.RUTA_BASE_POR_DEFECTO no surtio efecto"
    )
    return at


def _casos(*nombres: str) -> Path:
    carpeta = carpeta_casos()
    for nombre in nombres:
        preparar_base(carpeta / nombre)
    return carpeta
```
y reemplazar `test_abrir_otro_caso_lo_fija_en_la_clave_propia` y `test_abrir_un_caso_vacio_avisa_y_conserva_el_anterior`
(líneas 104-118) por
```python
def test_abrir_un_caso_de_la_lista_lo_fija_en_la_clave_propia(monkeypatch, tmp_path: Path) -> None:
    carpeta = _casos("a.db", "b.db")
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    selector = _por_rotulo(at.selectbox, ROTULO_CASO)
    assert list(selector.options) == ["a.db", "b.db"]
    selector.set_value("b.db")
    _por_rotulo(at.button, ROTULO_ABRIR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state[CLAVE_CASO] == str(resolver_caso("b.db", carpeta))


def test_el_inicio_no_ofrece_una_ruta_libre(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    assert [campo.label for campo in at.text_input] == [ROTULO_NUEVO]


def test_un_nombre_que_sale_de_la_carpeta_se_rechaza_sin_crear_nada(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    _por_rotulo(at.text_input, ROTULO_NUEVO).set_value("..\\fuera.db")
    _por_rotulo(at.button, ROTULO_CREAR).click().run()
    assert any("sale de la carpeta" in error.value for error in at.error)
    assert CLAVE_CASO not in at.session_state
    assert not (carpeta_casos().parent / "fuera.db").exists()


def test_crear_un_caso_nuevo_lo_deja_en_head_y_abierto(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    _por_rotulo(at.text_input, ROTULO_NUEVO).set_value("Obra Ñandú")
    _por_rotulo(at.button, ROTULO_CREAR).click().run()
    ruta = resolver_caso("Obra Ñandú", carpeta_casos())
    assert at.session_state[CLAVE_CASO] == str(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)


def test_sin_permiso_no_se_ofrece_cambiar_de_caso(monkeypatch, tmp_path: Path) -> None:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "puede_cambiar_de_caso", lambda: False)
    _casos("a.db")
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    assert any(SIN_PERMISO_DE_CAMBIO in info.value for info in at.info)
    assert ROTULO_ABRIR not in [boton.label for boton in at.button]
    assert len(at.selectbox) == 0
```

`tests/unit/test_ui_paginas_preparan_el_caso.py`:
```python
"""Las páginas abren el caso por `preparar_base` (RV-5): una base de la 0.5.0 se adopta una sola vez
con su juego; una de una versión más nueva se rechaza con mensaje y sin tocarla."""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

from operacion import config, respaldo
from operacion.base_datos import Destino, leer_estado, revision_head
from tests.fixtures import bases_prueba

SCRIPT = "from ui.paginas.catalogo import render\nrender()\n"


def _catalogo(monkeypatch, base: Path) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_el_catalogo_adopta_una_base_de_la_0_5_0_una_sola_vez(monkeypatch, tmp_path: Path) -> None:
    base = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")
    at = _catalogo(monkeypatch, base)
    assert not at.error
    assert leer_estado(base).revision == revision_head(Destino.CASO)
    assert len(respaldo.listar_juegos(config.carpeta_respaldos())) == 1
    at.run()
    assert len(respaldo.listar_juegos(config.carpeta_respaldos())) == 1


def test_una_base_mas_nueva_se_rechaza_con_mensaje_y_sin_tocarla(monkeypatch, tmp_path: Path) -> None:
    base = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    antes = respaldo.huella(base)
    at = _catalogo(monkeypatch, base)
    assert any("versión más nueva" in error.value for error in at.error)
    assert respaldo.huella(base) == antes
```

`tests/integration/test_api_preparar_base.py`:
```python
"""La API abre el caso por `preparar_base` (RV-5; spec S5 §5.2): adopta una base de la 0.5.0 y,
ante una que no se puede preparar, responde 503 con el mensaje y sin tocarla."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.dependencias as dependencias
from api.main import app
from operacion import respaldo
from operacion.base_datos import Destino, leer_estado, revision_head
from tests.fixtures import bases_prueba


@pytest.fixture
def cliente_sobre(monkeypatch):
    monkeypatch.setattr(dependencias, "_motor", None)

    def abrir(ruta: Path) -> TestClient:
        monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
        return TestClient(app)

    yield abrir
    if dependencias._motor is not None:
        dependencias._motor.dispose()


def test_la_api_adopta_una_base_de_la_0_5_0_y_responde(tmp_path: Path, cliente_sobre) -> None:
    ruta = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")
    with cliente_sobre(ruta) as cliente:
        respuesta = cliente.get("/partidas")
    assert respuesta.status_code == 200 and respuesta.json()
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)


def test_una_base_mas_nueva_responde_503_y_no_se_toca(tmp_path: Path, cliente_sobre) -> None:
    ruta = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    antes = respaldo.huella(ruta)
    with cliente_sobre(ruta) as cliente:
        respuesta = cliente.get("/partidas")
    assert respuesta.status_code == 503
    assert "versión más nueva" in respuesta.json()["detalle"]
    assert respaldo.huella(ruta) == antes
```

- [ ] **Paso 2: Correrla y ver el rojo; commit de la prueba**
Run: `uv run pytest tests/unit/test_arquitectura_s5.py tests/unit/test_ui_caso.py tests/unit/test_ui_inicio.py tests/unit/test_ui_paginas_preparan_el_caso.py tests/integration/test_api_preparar_base.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'SIN_PERMISO_DE_CAMBIO' from 'ui.caso'`, `cannot import name
'PREFIJO_CASO_ABIERTO'`, `AttributeError: module 'api.dependencias' has no attribute 'VARIABLE_BASE'` y las guardias
`test_ni_la_interfaz_ni_la_api_crean_el_esquema` (once llamadas) y `test_cada_pagina_que_abre_el_caso_lo_prepara` (nueve).
```bash
git add tests/unit/test_arquitectura_s5.py tests/unit/test_ui_caso.py tests/unit/test_ui_inicio.py tests/unit/test_ui_paginas_preparan_el_caso.py tests/integration/test_api_preparar_base.py
git commit -m "test(ui): casos desde la lista, estado sin DDL y paginas y API via preparar_base (rojo)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`ui/caso.py` (archivo completo):
```python
"""El caso abierto de la sesion y el recorrido activo (sprint de UI, RF-38 a RF-40; Silice 0.6.0, RV-5).

El archivo de la base se fija una vez por sesion y todas las pantallas operan sobre el: ninguna,
salvo el Inicio, vuelve a pedir el caso. Desde la 0.6.0 el Inicio lo elige de la lista de la carpeta
de casos (`abrir_caso`), y todo caso se abre con `operacion.base_datos.preparar_base` (spec S5 §6.6).

Tres invariantes (spec de UI, §3.2):

1. **Claves propias de `st.session_state`, nunca de widget.** Streamlit descarta las entradas de los
   widgets que no se vuelven a montar: `CLAVE_CASO` y `CLAVE_RECORRIDO` no son la `key` de ningun
   widget.
2. **Respaldo declarado.** Se puede entrar por URL a cualquier pantalla sin pasar por el Inicio. Sin
   caso fijado, manda la variable de entorno `SILICE_CASO` (el guion CP-07 la usa; la lee
   `ui.entorno.leer_variable`, con su alias anterior hasta la 0.6.0; en el producto la fija el
   lanzador) y, si no esta, el caso por defecto de la carpeta de datos (`<datos>/casos/silice.db`,
   `operacion.config`). `SILICE_CASO` es configuracion de quien arranca, no entrada del usuario: no
   pasa por la lista. `ruta_caso()` lee `RUTA_BASE_POR_DEFECTO` **al
   llamarse**: las pruebas la parchan en el objeto modulo de `sys.modules`.
3. **El motor de SQLAlchemy no va a la sesion.** Cada pantalla lo crea y lo cierra con
   `motor.dispose()`: en Windows no se puede borrar un archivo con un motor abierto.

`estado_caso` no crea el archivo ni emite DDL: lee con una conexion de solo lectura (RV-5). La
siembra desde la interfaz nunca construye el flag de reinicio de `scripts/seed_demo.py`, que borra la
base entera.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion
from operacion.base_datos import (
    MENSAJE_MAS_NUEVA,
    Destino,
    ErrorDeBase,
    RutaDeCasoRechazada,
    leer_estado,
    motor_solo_lectura,
    preparar_base,
    resolver_caso,
    revision_head,
    revisiones_conocidas,
)
from operacion.config import ruta_caso_por_defecto
from ui.entorno import VARIABLE_CASO, leer_variable

#: Sin caso fijado ni `SILICE_CASO`: `None` es el caso por defecto de la carpeta de datos. Las
#: pruebas lo desvian con una ruta de texto.
RUTA_BASE_POR_DEFECTO = None
VARIABLE_RUTA_CASO = VARIABLE_CASO  # nombre que ya importan las pruebas (RF-38; A1)
CLAVE_CASO = "silice_caso_ruta"
CLAVE_RECORRIDO = "silice_recorrido_activo"
CLAVE_PROYECTO = "silice_proyecto_abierto"
CLAVE_ACCION = "silice_accion_pedida"
#: Acciones que la barra superior le pide a la hoja del proyecto (`pedir_accion`).
ACCION_PRECIOS = "precios"
ACCION_IMPORTAR_PLANO = "importar_plano"
ACCION_GUARDAR_VERSION = "guardar_version"
ACCION_EXPORTAR_EXCEL = "exportar_excel"
SIN_PERMISO_DE_CAMBIO = "Su cuenta no puede cambiar de caso: pidaselo a quien arma o al administrador."


def resolver_ruta(guardada: str | None, entorno: Mapping[str, str], por_defecto: str) -> Path:
    """La ruta del caso: la fijada en la sesion; si no, la del entorno; si no, la por defecto."""
    if guardada:
        return Path(guardada)
    del_entorno = (leer_variable(entorno, VARIABLE_RUTA_CASO) or "").strip()
    return Path(del_entorno or por_defecto)


def ruta_caso() -> Path:
    """La ruta del caso abierto en esta sesion."""
    por_defecto = RUTA_BASE_POR_DEFECTO or str(ruta_caso_por_defecto())
    return resolver_ruta(st.session_state.get(CLAVE_CASO), os.environ, por_defecto)


def fijar_caso(ruta: Path | str) -> None:
    """Fija el caso abierto para toda la sesion. `ValueError` si la ruta queda vacia."""
    texto = str(ruta).strip()
    if not texto:
        raise ValueError("Elija un caso de la lista: no puede quedar vacio.")
    st.session_state[CLAVE_CASO] = texto


def puede_cambiar_de_caso() -> bool:
    """«Cambiar de caso»: solo *arma* y administrador (maestro §4.3). En la 0.6.0 no hay cuentas,
    asi que todos pueden; S3-1 reemplaza este cuerpo por la comprobacion del rol de la sesion."""
    return True


def abrir_caso(nombre: str, carpeta: Path | None = None) -> Path:
    """Abre un caso de la lista (RV-5): valida el nombre dentro de la carpeta de casos, lo prepara
    con `preparar_base` (lo migra con respaldo si hace falta) y lo fija para la sesion.
    `PermissionError` sin permiso de cambiar de caso; `ErrorDeBase` con el mensaje si no se puede."""
    if not puede_cambiar_de_caso():
        raise PermissionError(SIN_PERMISO_DE_CAMBIO)
    ruta = resolver_caso(nombre, carpeta)
    if not ruta.exists():
        raise RutaDeCasoRechazada(f"El caso {ruta.name} ya no esta en la carpeta de casos.")
    preparar_base(ruta)
    fijar_caso(ruta)
    return ruta


def recorrido_activo() -> str | None:
    """El nombre del recorrido elegido en el Inicio, o `None` si no se eligio ninguno."""
    return st.session_state.get(CLAVE_RECORRIDO)


def fijar_recorrido(nombre: str | None) -> None:
    """Fija (o, con `None`, suelta) el recorrido activo de la sesion."""
    st.session_state[CLAVE_RECORRIDO] = nombre


def proyecto_abierto() -> str | None:
    """El nombre del proyecto abierto en esta sesion (barra superior, RF-63), o `None`."""
    return st.session_state.get(CLAVE_PROYECTO)


def fijar_proyecto(nombre: str | None) -> None:
    """Fija (o, con `None`, suelta) el proyecto abierto de la sesion."""
    st.session_state[CLAVE_PROYECTO] = nombre


def pedir_accion(accion: str) -> None:
    """Deja una accion de la barra superior para la pantalla de destino (la hoja del proyecto)."""
    st.session_state[CLAVE_ACCION] = accion


def tomar_accion() -> str | None:
    """La accion pedida por la barra, que se consume: la segunda llamada devuelve `None`."""
    return st.session_state.pop(CLAVE_ACCION, None)


@dataclass(frozen=True, slots=True)
class EstadoCaso:
    """Lo que el marco muestra del caso abierto (RF-39)."""

    ruta: Path
    existe: bool
    partidas: int = 0
    insumos: int = 0
    lista_vigente: str | None = None
    error: str | None = None
    por_migrar: bool = False

    @property
    def vacio(self) -> bool:
        """Legible y sin partidas: incluye el archivo que todavia no existe (RF-40)."""
        return self.error is None and self.partidas == 0


def estado_caso(ruta: Path) -> EstadoCaso:
    """El estado del caso en `ruta`, sin crear el archivo y sin DDL (RV-5)."""
    if not ruta.exists():
        return EstadoCaso(ruta=ruta, existe=False)
    try:
        base = leer_estado(ruta)
    except ErrorDeBase as error:
        return EstadoCaso(ruta=ruta, existe=True, error=str(error))
    if base.revision is not None and base.revision not in revisiones_conocidas(Destino.CASO):
        texto = MENSAJE_MAS_NUEVA.format(nombre=ruta.name, revision=base.revision)
        return EstadoCaso(ruta=ruta, existe=True, error=texto)
    if base.sin_datos:
        return EstadoCaso(ruta=ruta, existe=True)
    motor = motor_solo_lectura(ruta)
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            try:
                lista: str | None = catalogo.lista_vigente().nombre
            except CatalogoIncompleto:
                lista = None
            return EstadoCaso(
                ruta=ruta,
                existe=True,
                partidas=len(catalogo.partidas()),
                insumos=len(catalogo.insumos()),
                lista_vigente=lista,
                por_migrar=base.revision != revision_head(Destino.CASO),
            )
    except SQLAlchemyError as error:
        # `orig` (el mensaje de SQLite, sin la sentencia SQL) solo existe en `DBAPIError`.
        return EstadoCaso(ruta=ruta, existe=True, error=str(getattr(error, "orig", None) or error))
    finally:
        motor.dispose()


def resumen_caso(estado: EstadoCaso) -> str:
    """Una linea con el estado del caso, para la barra lateral."""
    if estado.error is not None:
        return f"No se pudo leer: {estado.error}"
    if not estado.existe:
        return "El archivo no existe todavia."
    texto = (
        f"{estado.partidas} partidas · {estado.insumos} insumos · "
        f"lista vigente: {estado.lista_vigente or 'ninguna'}"
    )
    return texto + (" · se actualizara al abrirlo" if estado.por_migrar else "")


def argv_siembra(ruta: Path) -> list[str]:
    """Argumentos de `scripts.seed_demo.main` para sembrar el caso: nunca el flag de reinicio."""
    return ["--db", str(ruta)]
```

`ui/paginas/inicio.py` (archivo completo):
```python
"""Pantalla de Inicio (sprint de UI, UC-12; RF-36 a RF-40; Silice 0.6.0, RV-5).

La puerta de entrada: que caso esta abierto, que hacer si esta vacio y que recorridos hay. Desde la
0.6.0 el caso se elige de la **lista** de la carpeta de casos, se crea con un nombre o se sube un
`.db`; ya no hay campo de texto con la ruta (spec S5 §6.6). Todo caso se abre con `preparar_base`:
al entrar, el caso abierto se lleva a `head` (con respaldo previo si hace falta). «Cambiar de caso»
queda tras `ui.caso.puede_cambiar_de_caso` (gancho para los roles de S3).

El estado vacio ofrece cargar el caso de demostracion con `scripts.seed_demo.main`, siempre sin el
flag de reinicio, y solo cuando el caso no tiene partidas: nunca borra nada. Antes de sembrar, el
caso se crea en `head` por `preparar_base`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from operacion.base_datos import ErrorDeBase, crear_caso, listar_casos, preparar_base, subir_caso
from operacion.config import BASE_ANTERIOR, carpeta_casos
from scripts.seed_demo import main as sembrar_demostracion
from ui import caso
from ui.caso import (
    SIN_PERMISO_DE_CAMBIO,
    EstadoCaso,
    abrir_caso,
    argv_siembra,
    estado_caso,
    fijar_caso,
    fijar_recorrido,
    recorrido_activo,
    resumen_caso,
    ruta_caso,
)
from ui.recorridos import RECORRIDOS, recorrido_por_nombre

ROTULO_CASO = "Casos de la carpeta de datos"
ROTULO_ABRIR = "Abrir este caso"
ROTULO_NUEVO = "Nombre del caso nuevo"
ROTULO_CREAR = "Crear el caso"
ROTULO_SUBIR = "Subir un caso (.db)"
ROTULO_GUARDAR_SUBIDA = "Agregar el caso subido"
ROTULO_SEMBRAR = "Cargar el caso de demostracion"
ROTULO_RECORRIDO = "Que quiere hacer?"
PREFIJO_CASO_ABIERTO = "Caso abierto: "
MENSAJE_BASE_ANTERIOR = (
    "Hay una base de una version anterior en data/apu.db. Para seguir trabajando con ella, adoptela "
    "(se copia; el original no se toca): uv run python -m operacion adoptar data/apu.db --nombre silice"
)


def render() -> None:
    """El caso abierto, su estado vacio si lo tiene y los tres recorridos."""
    st.caption(
        "Esta aplicacion arma, costea y audita analisis de precios unitarios. Elija el caso con "
        "que va a trabajar y lo que quiere hacer: cada pantalla le indicara el paso siguiente."
    )
    _preparar_abierto()
    _elegir_caso()
    _estado(estado_caso(ruta_caso()))
    _elegir_recorrido()


def _preparar_abierto() -> None:
    """El caso abierto se lleva a `head` al entrar; uno que no existe no se crea."""
    ruta = ruta_caso()
    if not ruta.exists():
        return
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(str(error))


def _hacer(accion: Callable[[], object]) -> None:
    try:
        accion()
    except (ErrorDeBase, PermissionError) as error:
        st.error(str(error))
    else:
        st.rerun()


def _fijar(ruta: Path) -> Path:
    fijar_caso(ruta)
    return ruta


def _elegir_caso() -> None:
    st.subheader("1. El caso con que va a trabajar")
    st.caption(f"{PREFIJO_CASO_ABIERTO}{ruta_caso()}")
    if not caso.puede_cambiar_de_caso():
        st.info(SIN_PERMISO_DE_CAMBIO)
        return
    carpeta = carpeta_casos()
    nombres = [ruta.name for ruta in listar_casos(carpeta)]
    if nombres:
        eleccion = st.selectbox(ROTULO_CASO, nombres, index=None, placeholder="Elija un caso")
        if st.button(ROTULO_ABRIR) and eleccion is not None:
            _hacer(lambda: abrir_caso(str(eleccion), carpeta))
    else:
        st.info(f"Todavia no hay casos en {carpeta}. Cree uno o suba un archivo.")
        if BASE_ANTERIOR.exists():
            st.info(MENSAJE_BASE_ANTERIOR)
    with st.expander("Crear o subir un caso"):
        nombre = st.text_input(ROTULO_NUEVO, value="")
        if st.button(ROTULO_CREAR):
            _hacer(lambda: _fijar(crear_caso(nombre, carpeta).ruta))
        archivo = st.file_uploader(ROTULO_SUBIR, type=["db"])
        if archivo is not None and st.button(ROTULO_GUARDAR_SUBIDA):
            _hacer(lambda: _fijar(subir_caso(archivo.name, archivo.getvalue(), carpeta).ruta))


def _estado(estado: EstadoCaso) -> None:
    if estado.error is not None:
        st.error(f"{resumen_caso(estado)}. Revise el caso o abra otro.")
        return
    if not estado.vacio:
        st.success(f"Caso listo: {resumen_caso(estado)}.")
        return
    st.info(
        f"El caso {estado.ruta} no existe todavia o no tiene partidas. Puede cargar el caso de "
        "demostracion —la linea base de la clinica y una linea de agua potable didactica, con su "
        "presupuesto auditado— o abrir otro caso arriba."
    )
    if st.button(ROTULO_SEMBRAR, type="primary"):
        with st.spinner("Cargando la linea base, la demostracion y su presupuesto auditado..."):
            try:
                preparar_base(estado.ruta)
                sembrar_demostracion(argv_siembra(estado.ruta))
            except (LookupError, ValueError, ArithmeticError, OSError, SQLAlchemyError) as error:
                st.error(f"No se pudo cargar el caso de demostracion: {error}")
                return
        st.rerun()


def _elegir_recorrido() -> None:
    st.subheader("2. Que quiere hacer")
    nombres = [recorrido.nombre for recorrido in RECORRIDOS]
    activo = recorrido_activo()
    eleccion = st.radio(
        ROTULO_RECORRIDO,
        nombres,
        index=nombres.index(activo) if activo in nombres else None,
        captions=[recorrido.proposito for recorrido in RECORRIDOS],
    )
    if eleccion is not None and eleccion != activo:
        fijar_recorrido(eleccion)
        st.rerun()
    recorrido = recorrido_por_nombre(eleccion)
    if recorrido is None:
        return
    for numero, paso in enumerate(recorrido.pasos, start=1):
        st.markdown(f"**{numero}. {paso.titulo}.** {paso.que_hacer}")
    st.caption("Pulse «Siguiente» al pie de la pagina para ir al primer paso.")
```

`api/dependencias.py` (archivo completo):
```python
"""Sesion de base de datos por peticion. Lo unico de la API que sabe de configuracion.

El caso se abre por `operacion.base_datos.preparar_base` (RV-5, spec S5 §5.2): el de `APU_BASE` (que
en el producto fija el lanzador) o, sin ella, el caso por defecto de la carpeta de datos. Una base
que no se puede preparar (mas nueva, ilegible, bloqueada, no adoptable) responde 503 con el mensaje,
sin crear tablas.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from operacion.config import ruta_caso_por_defecto

VARIABLE_BASE = "APU_BASE"
_PREFIJO_ARCHIVO = "sqlite:///"
_motor = None


def url_por_defecto() -> str:
    return f"{_PREFIJO_ARCHIVO}{ruta_caso_por_defecto().as_posix()}"


def ruta_de_url(url: str) -> Path | None:
    """El archivo de una URL `sqlite:///...`; `None` si no es un archivo SQLite."""
    if not url.startswith(_PREFIJO_ARCHIVO):
        return None
    ruta = url[len(_PREFIJO_ARCHIVO) :]
    return Path(ruta) if ruta and ruta != ":memory:" else None


def _obtener_motor():
    global _motor
    if _motor is None:
        url = os.environ.get(VARIABLE_BASE, "").strip() or url_por_defecto()
        ruta = ruta_de_url(url)
        if ruta is not None:
            try:
                preparar_base(ruta)
            except ErrorDeBase as error:
                raise HTTPException(status_code=503, detail=str(error)) from error
        _motor = crear_motor(url)
    return _motor


def sesion_api() -> Iterator[Session]:
    with abrir_sesion(_obtener_motor()) as sesion:
        yield sesion


#: Alias de tipo para inyectar la sesion en las rutas sin disparar B008 (ruff): un `Depends(...)`
#: como valor por defecto es una llamada en la firma; dentro de `Annotated` no lo es.
SesionDep = Annotated[Session, Depends(sesion_api)]
```

**Las nueve páginas** (en todas: quitar `crear_esquema` del `from core.catalog import ...` y agregar, tras las
importaciones de `core`, `from operacion.base_datos import preparar_base`):
- `ui/paginas/actualizacion.py`: importar también `ErrorDeBase`; `_sembrar` (líneas 171-181) queda
  ```python
  def _sembrar(ruta: Path) -> None:
      """Prepara el caso (`preparar_base`, RV-5) y carga la linea base, si aun no esta."""
      motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
      try:
          preparar_base(ruta)
          with abrir_sesion(motor) as sesion:
              sembrar(sesion)
              partidas = len(Catalogo(sesion).partidas())
          st.sidebar.success(f"Base lista en {ruta} con {partidas} partidas.")
      except ErrorDeBase as error:
          st.sidebar.error(str(error))
      finally:
          motor.dispose()
  ```
  y la línea 266 `crear_esquema(motor)` → `preparar_base(parametros["ruta"])`.
- `ui/paginas/catalogo.py:31`, `componer.py:146`, `elaborar.py:159` y `:268`, `escenarios.py:65`, `historico.py:39`,
  `similares.py:63`: `crear_esquema(motor)` → `preparar_base(ruta)`.
- `ui/paginas/simulador.py:75`: `crear_esquema(motor)` → `preparar_base(Path(parametros["ruta"]))`.
- `ui/paginas/catalogo.py:38` y `historico.py:44`: en el comentario, «(`OperationalError` de `crear_esquema`)» →
  «(`ErrorDeBase` de `preparar_base`)».
- `ui/paginas/hoja.py`: importar también `ErrorDeBase`; `_sesion` (líneas 123-136) queda
  ```python
  @contextmanager
  def _sesion() -> Iterator[Any]:
      """Una sesion sobre el caso abierto, o `None` si el archivo no existe (no se crea nada) o no se
      puede preparar (el mensaje ya se mostro). El caso se abre por `preparar_base` (RV-5)."""
      ruta = ruta_caso()
      if not ruta.exists():
          yield None
          return
      try:
          preparar_base(ruta)
      except ErrorDeBase as error:
          st.error(str(error))
          yield None
          return
      motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
      try:
          with abrir_sesion(motor) as sesion:
              yield sesion
      finally:
          motor.dispose()
  ```
- `ui/elaboracion.py:13`: la frase pasa a «`ui.caso.estado_caso` no escribe: lee con una conexión de solo lectura
  (RV‑5).»

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_arquitectura_s5.py tests/unit/test_arquitectura.py tests/unit/test_ui_caso.py tests/unit/test_ui_inicio.py tests/unit/test_ui_paginas_preparan_el_caso.py tests/integration/test_api_preparar_base.py -v -W error`
Esperado: PASS. Luego **toda** la suite `uv run pytest -q -W error` (las pruebas de páginas con bases sembradas por
`create_all` ahora adoptan su base con un juego en la carpeta temporal; ninguna debe cambiar de resultado) y
`uv run python scripts/exportar_openapi.py && git diff --exit-code -- docs/api.json` (el esquema no cambia).
`uv run ruff check ui/caso.py ui/paginas api/dependencias.py ui/elaboracion.py tests/unit/test_arquitectura_s5.py tests/unit/test_ui_caso.py tests/unit/test_ui_inicio.py tests/unit/test_ui_paginas_preparan_el_caso.py tests/integration/test_api_preparar_base.py`.

- [ ] **Paso 5: Commit**
```bash
git add ui/caso.py ui/paginas/inicio.py ui/paginas/actualizacion.py ui/paginas/catalogo.py ui/paginas/componer.py ui/paginas/elaborar.py ui/paginas/escenarios.py ui/paginas/historico.py ui/paginas/hoja.py ui/paginas/similares.py ui/paginas/simulador.py ui/elaboracion.py api/dependencias.py
git commit -m "feat(ui): casos desde la carpeta de datos y paginas y API abren el caso con preparar_base" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 7: documentos de S5‑1 (ERS, plan de pruebas, manuales, README, `CHANGELOG.md`) y la parte S5 de la meta

**Rama:** `inc/060-s5-1-alembic` (sale de `main`; PR a `main`; ver RV-2)   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `CHANGELOG.md` (nace aquí: ninguna tarea de T0 lo crea; recoge también las cinco PR de T0, ver A §Discrepancias 7),
  `scripts/meta_silice_s5.py`
- Modificar: `docs/ERS.md` (enmienda antes de la tabla de versión, ~línea 72; fila RF‑96 tras RF‑63, ~línea 813; fila
  RNF‑20 al final de §3.3, ~línea 858), `docs/plan_pruebas.md` (§8.2 nueva antes de §9, ~línea 513; fila de §9),
  `docs/manual_tecnico.md:231-234` y `:501-517`, `docs/manual_usuario.md:47`, `:141-144`, `:657`, `README.md:31-33`,
  `.github/workflows/ci.yml` (paso «Meta de Silice» de A4: `--hasta T0` → `--hasta S5-1`), `scripts/README.md`
  (fila de `meta_silice_s5.py` en «Metas de sprint»)
- Prueba: `tests/unit/test_documentos_s5_1.py`, `tests/unit/test_meta_silice_s5.py`

**Interfaces:**
- Consume: nombres de prueba de las Tareas 3–6 (los que cita plan_pruebas §8.2); de `scripts.meta_silice` (A4):
  `Parte`, `ParTDD`, `Comprobacion`, `Contexto`, `partes()`, `validar_partes(todas)`; `scripts.meta_alpha.Estado`.
- Produce: RF‑96 y RNF‑20 presentes en la ERS (S5‑M1, parte de la 0.6.0); `CHANGELOG.md` con `## [Sin publicar]`
  (las líneas de T0 y la de S5‑1), donde cada PR siguiente agrega la suya; `scripts.meta_silice_s5.PARTE: Parte`
  (`requisitos={"S5-1": ("RF-96", "RNF-20")}`, ocho `ParTDD` de `S5-1`, comprobación `S5-M3`),
  `PARES_S5: tuple[ParTDD, ...]`, `BASES_050`, `evaluar_base_050(carpeta: Path) -> tuple[Estado, str]`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_documentos_s5_1.py`:
```python
"""Los documentos de S5-1 (spec S5 §13): la ERS trae RF-96 y RNF-20, el plan de pruebas cita sus
pruebas reales y los manuales ya no ofrecen la ruta libre del caso."""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _texto(relativa: str) -> str:
    return (RAIZ / relativa).read_text(encoding="utf-8")


def test_la_ers_trae_rf_96_y_rnf_20() -> None:
    ers = _texto("docs/ERS.md")
    assert re.search(r"^\| RF‑96 \|", ers, re.M)
    assert "RNF‑20" in ers


def test_el_plan_de_pruebas_cita_pruebas_que_existen() -> None:
    plan = _texto("docs/plan_pruebas.md")
    citadas = set(re.findall(r"`(tests/[\w/]+\.py)::(\w+)`", plan.split("### 8.2", 1)[1].split("## 9.", 1)[0]))
    assert citadas
    for archivo, prueba in citadas:
        assert f"def {prueba}(" in _texto(archivo), f"{archivo}::{prueba}"


def test_los_manuales_ya_no_ofrecen_la_ruta_libre_del_caso() -> None:
    for relativa in ("docs/manual_usuario.md", "README.md"):
        assert "Archivo del caso (SQLite)" not in _texto(relativa), relativa


def test_el_registro_de_cambios_trae_t0_y_s5_1() -> None:
    cambios = _texto("CHANGELOG.md")
    assert "## [Sin publicar]" in cambios and "caso_0001_base_0_5_0" in cambios
    for pieza in ("SILICE_CASO", "dependencias", "guardia de red", "meta_silice.py"):
        assert pieza in cambios, pieza
```

`tests/unit/test_meta_silice_s5.py`:
```python
"""Parte S5 de la meta unica de Silice (spec S5 §12 y §13; plan 0.6.0, seccion B, tarea 7)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.meta_alpha import Estado
from scripts.meta_silice import partes, validar_partes
from scripts.meta_silice_s5 import BASES_050, PARTE, evaluar_base_050

RAIZ = Path(__file__).resolve().parents[2]


def test_la_parte_s5_se_descubre_y_usa_solo_la_fase_s5_1() -> None:
    validar_partes((PARTE,))
    assert any(parte is PARTE for parte in partes())
    assert PARTE.requisitos == {"S5-1": ("RF-96", "RNF-20")}
    assert {par.fase for par in PARTE.pares_tdd} == {"S5-1"}
    assert [(c.codigo, c.fase) for c in PARTE.comprobaciones] == [("S5-M3", "S5-1")]


def test_los_pares_nombran_archivos_del_repositorio() -> None:
    for par in PARTE.pares_tdd:
        assert (RAIZ / par.prueba).is_file(), par.prueba
        assert (RAIZ / par.implementacion).is_file(), par.implementacion


def _carpeta(tmp_path: Path, commit: str = "8610053abcdef") -> Path:
    carpeta = tmp_path / "v0_5_0"
    carpeta.mkdir()
    bases = {}
    for nombre in BASES_050:
        (carpeta / nombre).write_bytes(nombre.encode())
        bases[nombre] = {"sha256_base": hashlib.sha256(nombre.encode()).hexdigest()}
    ficha = {"version": "0.5.0", "etiqueta": "v0.5.0", "commit": commit, "bases": bases}
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    return carpeta


def test_la_base_de_prueba_0_5_0_es_la_de_la_etiqueta(tmp_path: Path) -> None:
    assert evaluar_base_050(tmp_path / "no")[0] is Estado.FALLA
    carpeta = _carpeta(tmp_path)
    assert evaluar_base_050(carpeta)[0] is Estado.OK
    (carpeta / "of001.db").write_bytes(b"otra")
    estado, detalle = evaluar_base_050(carpeta)
    assert estado is Estado.FALLA and "of001.db" in detalle


def test_una_ficha_de_otro_commit_falla(tmp_path: Path) -> None:
    estado, detalle = evaluar_base_050(_carpeta(tmp_path, commit="1234567"))
    assert estado is Estado.FALLA and "8610053" in detalle


def test_la_base_versionada_del_repositorio_pasa() -> None:
    assert evaluar_base_050(RAIZ / "tests" / "fixtures" / "bases" / "v0_5_0")[0] is Estado.OK
```

- [ ] **Paso 2: Correrla y ver el rojo; commit de la prueba**
Run: `uv run pytest tests/unit/test_documentos_s5_1.py tests/unit/test_meta_silice_s5.py -v -W error`
Esperado: FAIL con `AssertionError` en RF‑96, en `split("### 8.2", 1)[1]` (`IndexError`), en «Archivo del caso
(SQLite)», `FileNotFoundError: CHANGELOG.md` y `ModuleNotFoundError: No module named 'scripts.meta_silice_s5'`.
```bash
git add tests/unit/test_documentos_s5_1.py tests/unit/test_meta_silice_s5.py
git commit -m "test(docs): RF-96, RNF-20 y documentos de S5-1 (rojo)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`docs/ERS.md`, enmienda (bloque citado, después de la enmienda del sprint final):
```markdown
> **Enmienda de Sílice 0.6.0 (S5‑1 adelantado; spec
> [S5](especificaciones/2026-10-11-silice-s5-producto-instalador-design.md) §4; maestro RV‑3, RV‑4, RV‑5):** se
> agregan **RF‑96** (migraciones con respaldo y vuelta atrás, en dos bases; abrir un caso solo con `preparar_base`
> y desde la carpeta de casos) y **RNF‑20** (cero deriva de esquema en cada destino). UC‑24, RF‑97 a RF‑99 y RNF‑19
> los agrega S5‑0 en la 1.0.0; hasta entonces RF‑96 cita UC‑24 por adelantado. En la 0.6.0 se cumplen de RF‑96 los
> criterios (a) para la base del caso, (b), (c), (d) y (e), y (f) con la base de la instalación sin tablas; el resto
> llega con S3 (`instalacion.db` con tablas) y S5‑2. Los conteos los calcula la meta (maestro §6.1).
```
fila tras RF‑63 (texto literal del spec S5 §4.2, con la columna «Incremento» de la ERS):
```markdown
| RF‑96 | **Migraciones con respaldo y vuelta atrás, en dos bases.** El esquema se versiona con Alembic en dos destinos, cada uno con su `alembic_version` y su lista `METADATAS` explícita: la **instalación** (`seguridad`) y el **caso** (`core.models`, `METADATA_ESPACIO`, `paquete`, `asistente`). La revisión base del caso es el esquema de la 0.5.0 y cada cambio posterior trae su revisión, desde la 0.6.0. Antes de aplicar cualquier revisión pendiente se respaldan **juntas** la instalación y los casos que se migran, en un juego con una sola ficha; si la migración falla, la base no queda modificada. Las bases de la 0.5.0 se adoptan. Un caso se abre solo con `preparar_base` y desde `datos\casos\` | Esencial | UC‑24 (S5‑0) | S5‑1 (0.6.0) | (a) una base vacía, una base de la 0.5.0 sin `alembic_version` y la base de prueba de cada versión 0.6.0…0.9.0 (generada en su compuerta con el código de su etiqueta) llegan a `head` y sus presupuestos recargan con el total literal, la huella del informe y las filas por tabla de su ficha; lo mismo para `instalacion.db` desde la 0.8.0; (b) cada base del juego de respaldo pasa `PRAGMA integrity_check` y su huella está en la ficha; (c) con un fallo inyectado en una revisión, la huella SHA‑256 de cada base tras el intento es igual a la de antes; (d) una base con revisión desconocida o no adoptable no se modifica (huella igual) y el mensaje dice qué hacer; (e) una ruta UNC, absoluta o con `..` se rechaza sin crear archivo, y `estado_caso` no emite DDL; (f) restaurar un juego con `instalacion.db` lista los eventos de seguridad perdidos y deja pendiente la revisión del administrador |
```
fila al final de §3.3:
```markdown
| Mantenibilidad | RNF‑20 cero deriva de esquema en cada destino: una base llevada a `head` por las migraciones es igual a la creada con `create_all` de sus `METADATAS`, la autogeneración de Alembic contra ella no propone cambios, toda `MetaData` con tablas está en la lista de su destino y cada revisión baja y vuelve a subir | `tests/integration/test_migraciones.py` en Linux y Windows en cada PR | deriva 0 en los dos destinos, desde la 0.6.0 |
```

`docs/plan_pruebas.md`, antes de `## 9.`:
```markdown
### 8.2 Filas de Sílice 0.6.0 (S5‑1): RF‑96

Fuente: [spec S5 §12](especificaciones/2026-10-11-silice-s5-producto-instalador-design.md). El commit de cada
prueba va antes que el de su implementación, con el rojo observado. Estas filas no entran en el resumen de §8.

| RF | Prueba(s) que lo demuestran | Estado |
|---|---|---|
| RF‑96 (a) | `tests/integration/test_preparar_base.py::test_una_base_que_no_existe_nace_en_head_sin_juego`, `tests/integration/test_preparar_base.py::test_una_base_de_la_0_5_0_se_adopta_con_juego_y_recarga_igual_que_su_ficha`, `tests/integration/test_preparar_base.py::test_migrar_lleva_todo_a_head_con_un_solo_juego`, `tests/integration/test_preparar_base.py::test_la_base_de_la_instalacion_nace_vacia_con_su_alembic_version` | parcial (bases de 0.6.0…0.9.0 e `instalacion.db` con tablas: en su versión) |
| RF‑96 (b) | `tests/integration/test_respaldo.py::test_el_juego_trae_la_copia_verificada_y_su_ficha`, `tests/integration/test_respaldo.py::test_la_instalacion_va_siempre_en_el_juego_aunque_no_se_migre`, `tests/integration/test_respaldo.py::test_se_conservan_los_cinco_ultimos_de_migracion_y_todos_los_manuales` | verde |
| RF‑96 (c) | `tests/integration/test_preparar_base.py::test_un_fallo_inyectado_en_una_revision_deja_la_base_como_estaba`, `tests/integration/test_preparar_base.py::test_disco_lleno_al_respaldar_no_migra_ni_toca_la_base` | verde |
| RF‑96 (d) | `tests/integration/test_preparar_base.py::test_una_base_sin_modalidad_no_es_adoptable_y_no_se_toca`, `tests/integration/test_preparar_base.py::test_una_base_de_una_version_mas_nueva_no_se_toca`, `tests/integration/test_api_preparar_base.py::test_una_base_mas_nueva_responde_503_y_no_se_toca` | verde |
| RF‑96 (e) | `tests/unit/test_casos.py::test_unc_absolutas_puntos_y_carpetas_se_rechazan_sin_tocar_el_disco`, `tests/unit/test_ui_caso.py::test_estado_caso_no_emite_ddl_ni_cambia_el_archivo`, `tests/unit/test_ui_inicio.py::test_el_inicio_no_ofrece_una_ruta_libre` | verde |
| RF‑96 (f) | `tests/integration/test_respaldo.py::test_restaurar_un_juego_con_la_instalacion_vacia_de_la_0_6_0`, `tests/integration/test_respaldo.py::test_restaurar_la_instalacion_lista_los_eventos_posteriores_al_juego` | parcial (el bloqueo de operaciones sensibles hasta la revisión llega con S3 y S5‑2) |
```
y en la tabla de §9, al final:
```markdown
| RNF‑20 deriva de esquema | `tests/integration/test_migraciones.py::test_head_en_vacio_es_igual_a_create_all`, `::test_la_autogeneracion_contra_head_no_propone_cambios`, `::test_toda_metadata_con_tablas_esta_en_la_lista_de_su_destino`, `::test_cada_revision_baja_y_vuelve_a_subir`, en los dos destinos | cumple (desde la 0.6.0) |
```

`docs/manual_tecnico.md:231-234` (el punto «No hay herramienta de migraciones»), reemplazar por:
```markdown
- **Migraciones con Alembic (desde la 0.6.0, S5‑1):** dos destinos, cada uno con su `alembic_version` en su propia
  base y su lista explícita de metadatos (`migraciones/metadatos.py`): la base del **caso** (`core.models` y
  `METADATA_ESPACIO`; después `paquete` y `asistente`) y la de la **instalación** (vacía hasta S3‑1). Un caso se
  abre solo con `operacion.base_datos.preparar_base`: crea la base nueva en `head`, y una anterior la respalda en
  un juego con ficha, la migra sobre una copia de trabajo y solo entonces la devuelve. `crear_esquema` queda para
  las bases en memoria de las pruebas y los scripts de siembra; sobre una base en `head` no emite DDL (RNF‑20).
  La regla completa, en §10.5.
```
`docs/manual_tecnico.md:501-517` (§10.5 hasta el párrafo de C3 exclusive), reemplazar por:
```markdown
### 10.5 La regla de las migraciones (Alembic desde la 0.6.0)

Desde la 0.6.0 el esquema se versiona con Alembic (RF‑96, RNF‑20; spec S5 §6). La regla anterior («toda sesión que
cambie una columna declara qué les pasa a las bases en disco») se cumple ahora con una **revisión**:

1. **Dónde.** `migraciones/caso/versions/` y `migraciones/instalacion/versions/`. No hay `alembic.ini` ni se usa la
   orden `alembic`: `operacion.base_datos` arma la configuración y entrega la conexión (dos entornos, decisión de
   la sección B del plan de la 0.6.0).
2. **La revisión base** `caso_0001_base_0_5_0` es el DDL literal de la 0.5.0, congelado con
   `scripts/congelar_esquema.py` desde la base de prueba de `v0.5.0`; nunca se regenera desde los modelos. Es
   idempotente: crea las tablas que faltan y verifica las demás; una diferencia es `BaseNoAdoptable` y la base no
   se toca. Una base anterior a P2 (sin `modalidad`) no se adopta: se vuelve a sembrar.
3. **Agregar una revisión** (cada spec la suya): cambiar el modelo; copiar `script.py.mako` del destino a
   `versions/<destino>_<NNNN>_<tema>.py` con `revision` igual al nombre del archivo y `down_revision` igual a la
   `head` actual (`uv run python -m operacion revision`); tablas nuevas con `crear_o_verificar` (si se quieren
   adoptar bases creadas con `create_all`) u `op.create_table`; columnas con `op.batch_alter_table`; nunca
   `stamp`; un `downgrade()` real. Después, `uv run pytest tests/integration/test_migraciones.py -W error`: la
   autogeneración contra `head` debe venir vacía y `head` debe ser igual a `create_all`.
4. **Base de prueba por versión** (RV‑3, PRU‑H15): en la compuerta de cada versión se generan sus bases y su ficha
   con el código de su etiqueta: `git archive vX.Y.Z | tar -x -C <carpeta>`, copiar
   `scripts/generar_base_prueba.py` a su `scripts/`, fijar `UV_PROJECT_ENVIRONMENT=<carpeta>/.venv`,
   `uv sync --frozen --all-extras` y correrlo con `--salida tests/fixtures/bases/vX_Y_Z`. Las pruebas de adopción
   comparan contra la ficha, nunca contra un recálculo con el código nuevo.
5. **Respaldos.** Antes de migrar una base con datos se crea un juego en `<datos>/respaldos/` (copias con la API de
   respaldo de SQLite, `integrity_check` y `ficha.json`); se conservan los cinco últimos de migración y todos los
   manuales. `uv run python -m operacion respaldar` crea uno manual; `restaurar <juego> [--solo-caso <nombre>]`
   lo restaura con Sílice detenido.
6. **La base de trabajo anterior.** `data/apu.db` ya no es el caso por defecto (lo es `data/casos/silice.db`):
   `uv run python -m operacion adoptar data/apu.db --nombre silice` la copia a la carpeta de casos y la migra; el
   original no se toca.
7. **Límite declarado.** Los `scripts/seed*.py` siguen creando con `create_all`; sus bases se adoptan (con un juego)
   la primera vez que se abren. Cuando una revisión altere columnas de una tabla existente, los scripts de siembra
   deben pasar a `preparar_base` en esa misma revisión (disparador anotado en la bitácora de la 0.6.0).
```

`docs/manual_usuario.md`: en la línea 47, «(campo *Archivo del caso (SQLite)* y botón *Abrir este caso*)» →
«(lista *Casos de la carpeta de datos* y botón *Abrir este caso*; la base se copia antes a `data/casos/` con
`uv run python -m operacion adoptar <ruta> --nombre <caso>`)» y «(por defecto, `data/apu.db`)» → «(por defecto,
`data/casos/silice.db`)»; el punto 1 de §3.0 (líneas 141-144) queda:
```markdown
1. **El caso.** La lista *Casos de la carpeta de datos* y el botón *Abrir este caso* fijan la base con que trabajan
   todas las pantallas durante la sesión. Los casos viven en la carpeta de datos (`data/casos/` en desarrollo): se
   elige uno de la lista, se crea con un nombre (*Crear o subir un caso*) o se sube un `.db`. No hay campo con la
   ruta: una ruta de red, absoluta o con `..` se rechaza sin crear nada. Si el caso es de una versión anterior,
   Sílice lo respalda y lo actualiza al abrirlo.
```
y la fila de la línea 657, en su segunda celda (ya con el nombre de A1), «Abrirlo en **Inicio** (*Archivo del caso
(SQLite)* y *Abrir este caso*) o arrancar con `SILICE_CASO=<ruta>`: recargar la página (F5) vuelve a la ruta de
`SILICE_CASO` o, sin ella, a `data/apu.db`» → «Abrirlo en **Inicio** (lista de casos y *Abrir este caso*) o arrancar
con `SILICE_CASO=<ruta>`: recargar la página (F5) vuelve a la ruta de `SILICE_CASO` o, sin ella, a
`data/casos/silice.db`».

`README.md:31-33`, reemplazar las tres líneas por:
```powershell
uv run python -m operacion adoptar data/apu.db --nombre silice   # una vez, si trae una base de la 0.5.0: la copia a data/casos/silice.db y la migra (el original no se toca)
uv run python scripts/seed_demo.py --db data/casos/silice.db     # o, sin base anterior: el caso de demostración en el caso por defecto
```

`CHANGELOG.md`:
```markdown
# Registro de cambios

Formato de [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) con secciones en español; versiones según
[SemVer](https://semver.org/lang/es/). Cada PR agrega una línea bajo «Sin publicar» (maestro §6.1, RV‑2); al
etiquetar, las líneas pasan a la sección de la versión. La historia anterior a la 0.5.0 está en `docs/bitacora/`.

## [Sin publicar]

### Agregado

- T0‑A1: el producto se llama Sílice; variables `SILICE_CASO` y `SILICE_MODO_ENTREGA` (alias `ARENIA_*` hasta la 0.6.0); `.streamlit/config.toml` en 127.0.0.1 sin telemetría; licencia propietaria (`LICENSE`).
- T0‑A2: dependencias de Sílice 0.6.0 a 1.0.0 (`alembic`, `argon2-cffi`, `cryptography`; extras `bcv`, `ifc`, `ia`, `anomalias`, `similitud`) con sus licencias en la bitácora.
- T0‑A3: guardia de red única de la suite y modelo de similitud descargado antes de pytest (`scripts/descargar_modelo.py`).
- T0‑A4: meta única `scripts/meta_silice.py --version X --hasta FASE` con el bloque de regresión literal.
- T0‑A5: enmienda propuesta a NORMAS §3 (worktrees, ramas cortas por fase, un carril de núcleo).
- Migraciones con Alembic en dos destinos (caso e instalación); revisión base `caso_0001_base_0_5_0` = esquema de la 0.5.0; `preparar_base` con respaldo previo, casos en la carpeta de datos y `python -m operacion` (RF‑96, RNF‑20; S5‑1).
```

`scripts/meta_silice_s5.py`:
```python
"""Parte S5 de la meta unica de Silice (spec S5 §12 y §13; plan 0.6.0, seccion B, tarea 7).

`scripts/meta_silice.py` (A4) la descubre por su nombre. Con `--hasta S5-1` o posterior evalua: C1,
RF-96 y RNF-20 por presencia en la ERS; C3, la prueba de cada pieza de S5-1 antes que su codigo; y
S5-M3, la base de prueba de la 0.5.0 con su ficha, generada con el codigo de `v0.5.0` (RV-3). El
nucleo intacto en la rama de S5-1 (S5-M2) no es acumulable a las fases de nucleo siguientes: lo
vigilan `scripts/guardia_nucleo.py` en la CI de esa rama y la compuerta GS5-1. La regresion (S5-M8)
es C5 de la meta.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_silice import Comprobacion, Contexto, ParTDD, Parte  # noqa: E402

CARPETA_BASE_050 = RAIZ / "tests" / "fixtures" / "bases" / "v0_5_0"
BASES_050 = ("demo.db", "of001.db", "ti001.db")
COMMIT_V050 = "8610053"

#: Prueba -> implementacion de S5-1 (C3 de la meta; el commit de la prueba va antes).
PARES_S5: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_operacion_config.py", "operacion/config.py", "S5-1"),
    ParTDD("tests/unit/test_migraciones_metadatos.py", "migraciones/metadatos.py", "S5-1"),
    ParTDD("tests/unit/test_generar_base_prueba.py", "scripts/generar_base_prueba.py", "S5-1"),
    ParTDD("tests/unit/test_congelar_esquema.py", "scripts/congelar_esquema.py", "S5-1"),
    ParTDD("tests/integration/test_migraciones.py", "operacion/base_datos.py", "S5-1"),
    ParTDD("tests/integration/test_respaldo.py", "operacion/respaldo.py", "S5-1"),
    ParTDD("tests/integration/test_operacion_cli.py", "operacion/__main__.py", "S5-1"),
    ParTDD("tests/unit/test_meta_silice_s5.py", "scripts/meta_silice_s5.py", "S5-1"),
)


def evaluar_base_050(carpeta: Path) -> tuple[Estado, str]:
    """S5-M3: la ficha es de `v0.5.0` (commit 8610053) y cada base tiene la huella de su ficha."""
    ruta_ficha = carpeta / "ficha.json"
    if not ruta_ficha.is_file():
        return Estado.FALLA, f"falta {ruta_ficha}"
    ficha = json.loads(ruta_ficha.read_text(encoding="utf-8"))
    de_la_etiqueta = (ficha.get("version"), ficha.get("etiqueta")) == ("0.5.0", "v0.5.0")
    if not de_la_etiqueta or not str(ficha.get("commit", "")).startswith(COMMIT_V050):
        return Estado.FALLA, f"la ficha no es de v0.5.0 ({COMMIT_V050}): {ficha.get('commit')!r}"
    bases = ficha.get("bases") or {}
    distintas = [
        nombre
        for nombre in BASES_050
        if nombre not in bases
        or not (carpeta / nombre).is_file()
        or hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest()
        != bases[nombre]["sha256_base"]
    ]
    if distintas:
        return Estado.FALLA, "bases ausentes o distintas de su ficha: " + ", ".join(distintas)
    return Estado.OK, "base de prueba 0.5.0 de v0.5.0: " + ", ".join(BASES_050)


def _base_050(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_base_050(CARPETA_BASE_050)


PARTE = Parte(
    nombre="S5-1 Alembic, preparar_base y respaldo",
    requisitos={"S5-1": ("RF-96", "RNF-20")},
    pares_tdd=PARES_S5,
    comprobaciones=(
        Comprobacion("S5-M3", "Base de prueba 0.5.0 de su etiqueta, con ficha", "S5-1", _base_050),
    ),
)
```
`.github/workflows/ci.yml`, paso «Meta de Silice»: `--hasta T0` → `--hasta S5-1`. `scripts/README.md`, «Metas de
sprint»: `| `meta_silice_s5.py` | parte S5 de la meta única: RF‑96 y RNF‑20, prueba antes que código de S5‑1 y base de prueba de v0.5.0 con su ficha (S5‑M3) | 0.6.0 |`.

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_documentos_s5_1.py tests/unit/test_meta_silice_s5.py tests/unit/test_meta_silice.py tests/unit/test_meta_datos.py -v -W error && uv run python scripts/meta_datos.py`
Esperado: PASS y la meta de datos en OK (ningún documento presenta como reales los datos construidos). Tras el commit del
paso 5: `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml`, `uv run python scripts/medir_rnf11.py`
y `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S5-1 --junit reporte-pruebas.xml` → todas las filas en OK.

- [ ] **Paso 5: Commit**
```bash
git add docs/ERS.md docs/plan_pruebas.md docs/manual_tecnico.md docs/manual_usuario.md README.md CHANGELOG.md scripts/meta_silice_s5.py scripts/README.md .github/workflows/ci.yml
git commit -m "docs(ers): RF-96 y RNF-20, migraciones con Alembic, casos en la carpeta de datos y parte S5 de la meta" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Compuerta GS5‑1

- [ ] **Suite y CI:** `unset VIRTUAL_ENV; uv sync --all-extras; uv run pytest -q -W error` en verde en local; CI verde en
  Linux y Windows, con `scripts/verificar_omitidas.py` en 0 omitidas.
- [ ] **RF‑96 (parte 0.6.0) y RNF‑20:** `uv run pytest -W error tests/integration/test_migraciones.py tests/integration/test_preparar_base.py tests/integration/test_respaldo.py tests/integration/test_operacion_cli.py tests/integration/test_api_preparar_base.py tests/unit/test_casos.py tests/unit/test_ui_caso.py tests/unit/test_ui_inicio.py tests/unit/test_ui_paginas_preparan_el_caso.py tests/unit/test_arquitectura_s5.py` en verde.
- [ ] **Núcleo intacto (S5‑M2):** `git diff origin/main --stat -- core/` vacío y
  `uv run python scripts/guardia_nucleo.py --base origin/main` con salida 0; `git diff origin/main -- core/contracts/` vacío.
- [ ] **Regresión literal (S5‑M8, maestro §6.3):** es C5 de la meta: el bloque `REGRESION` de `scripts/meta_silice.py`
  (A4) en verde y `git diff v0.5.0..HEAD --stat -- <ARCHIVOS_REGRESION>` vacío, es decir sobre
  `tests/integration/test_auditoria_7_de_7.py tests/integration/test_composicion_extremo_a_extremo.py tests/unit/test_budget.py tests/unit/test_caso_ti001.py tests/unit/test_costing.py tests/unit/test_huellas_rnf04.py tests/unit/test_linea_base.py tests/unit/test_verification.py`.
- [ ] **Base de prueba (S5‑M3, RV‑3):** `tests/fixtures/bases/v0_5_0/` con tres bases y `ficha.json` cuyo `commit`
  empieza por `8610053`; la revisión base no se editó a mano (sus 33 tablas son las de la base de prueba).
- [ ] **ERS (S5‑M1, parte 0.6.0):** `grep -n "| RF‑96 |" docs/ERS.md` y `grep -n "RNF‑20" docs/ERS.md` con resultado.
- [ ] **Prueba antes que código:** en `git log --reverse --format=%s origin/main..HEAD`, cada `test(...)... (rojo)`
  precede al `feat(...)`/`docs(...)` de su tarea (siete pares).
- [ ] **Meta única** (ya en `main` por A4): `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml`,
  `uv run python scripts/medir_rnf11.py` y `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S5-1 --junit reporte-pruebas.xml`
  → todas las filas en OK (C1 con RF‑96 y RNF‑20, C3 con los ocho `ParTDD` de `scripts/meta_silice_s5.py`, C5 y `S5-M3`);
  el paso de la CI queda en `--hasta S5-1`.
- [ ] **Encargos** (maestro §6.4): requisitos, arquitectura, pruebas y calidad, verificador de hechos y, por ser S5,
  usabilidad y **seguridad** (ruta del caso, UNC, respaldos con huellas), cada uno aprobado.
- [ ] **Bitácora:** la compuerta anotada en `docs/bitacora/2026-10-silice-060.md` con el disparador del límite de
  los seeds (§10.5, punto 7) y SL‑E11 declarado vacante.
- [ ] **Fusión:** PR de `inc/060-s5-1-alembic` contra `main` fusionado con `gh pr merge <n> --merge` y la CI verde; desde
  ese `main` abre la sección C (`inc/060-s1-0-docs`, luego `inc/060-s1-1-nucleo`).
- [ ] **Después de la fusión, a mano y por Eugenio (no un agente; NORMAS §6.2):**
  `uv run python -m operacion adoptar data/apu.db --nombre silice`; comprobar que `data/apu.db` conserva su huella y
  que la interfaz abre `data/casos/silice.db`.

## Foco de revisión

Condiciones que el spec implica y que ninguna prueba ejercitaba antes de esta sección; cada una tiene su prueba en
la tarea dueña.

1. **Base bloqueada por otro proceso** (otra ventana de Sílice, un visor de SQLite): no se migra ni se pisa lo que el
   otro escribió. → Tarea 5: `test_una_base_bloqueada_por_otro_proceso_se_rechaza_sin_tocarla`,
   `test_una_base_que_cambia_durante_la_migracion_no_se_pisa`; Tarea 4:
   `test_se_respalda_con_la_base_abierta_y_una_escritura_sin_confirmar`.
2. **Ruta con espacios, tildes y `ñ` en OneDrive** (URI `file:` codificada con `as_uri`, `URL.create`, `%` escapado
   en la configuración de Alembic). → Tarea 4: `test_juego_en_una_ruta_de_onedrive_con_espacios_y_acentos`; Tarea 5:
   `test_adopcion_en_una_carpeta_de_onedrive_con_espacios_y_acentos`; Tarea 1:
   `test_silice_datos_mueve_todo_y_no_crea_nada`.
3. **Disco lleno al respaldar:** sin juego verificado no se migra, y no queda carpeta a medias. → Tarea 4:
   `test_disco_lleno_no_deja_juego_ni_toca_la_base`; Tarea 5: `test_disco_lleno_al_respaldar_no_migra_ni_toca_la_base`.
4. **Base corrupta** (cabecera que no es SQLite y página interior dañada). → Tarea 5:
   `test_un_archivo_que_no_es_sqlite_es_ilegible_y_no_se_toca`, `test_una_base_con_una_pagina_danada_no_se_migra`;
   Tarea 4: `test_una_copia_ilegible_no_deja_juego`.
5. **Base más nueva que el código** (bajó de versión, §6.4 3d): no se toca en `preparar_base`, en la API, en las
   páginas, en `estado_caso` ni al restaurar. → Tarea 5: `test_una_base_de_una_version_mas_nueva_no_se_toca`,
   `test_un_error_de_base_sale_con_1_y_su_mensaje`; Tarea 6: `test_una_base_mas_nueva_responde_503_y_no_se_toca`,
   `test_una_base_mas_nueva_se_rechaza_con_mensaje_y_sin_tocarla`, `test_estado_de_una_base_mas_nueva_es_un_error_con_mensaje`;
   Tarea 4: `test_un_juego_de_una_version_mas_nueva_no_se_restaura`.

## Discrepancias encontradas

1. **Restaurar tras un fallo vs. no tocar el original.** El spec (§6.3, §6.4) dice que, si la migración falla, «se
   restaura el juego»; RF‑96 (c) exige que la huella SHA‑256 de la base tras el intento sea igual a la de antes. Una
   copia hecha con `Connection.backup` no garantiza una copia idéntica byte a byte (SQLite reescribe contadores de la
   cabecera del destino), así que restaurarla no daría la misma huella. El plan migra una **copia de trabajo** y solo
   la devuelve si llega entera a `head`: el original nunca se toca ante un fallo. El juego sigue siendo previo y sirve
   para la restauración manual. *Abierta (decisión 3 de `cotejo.md`; por defecto, copia de trabajo: el original nunca se toca).*
2. **`operacion.rutas` vs. `operacion.config`.** El spec §5.2 y §13 ponen las carpetas en `operacion/rutas.py` y la
   configuración (`silice.toml`) en `config.py`; el encargo pide las carpetas en `config.py`. Se sigue el encargo;
   S5‑2 agrega `silice.toml` al mismo `config.py`. *Resuelta en el cotejo.* A y C no consumen `operacion.rutas`; las carpetas son las funciones de `operacion.config`.
3. **`.gitignore` ya ignora `*.db`** (línea 14): las bases de prueba de `tests/fixtures/bases/` necesitan la negación
   `!tests/fixtures/bases/*/*.db` (y `.gitattributes` binario para que su SHA‑256 no cambie en Windows). El spec no lo
   menciona. *Resuelta en el cotejo.*
4. **Respaldos en desarrollo.** El spec §5.3 los pone fuera de la carpeta de datos (`%LOCALAPPDATA%\Silice\respaldos`) sin
   variable propia; en desarrollo `data/../respaldos` caería en la raíz del repositorio. El plan agrega
   `SILICE_RESPALDOS` (por defecto `<datos>/respaldos/`) y suma al `.gitignore` `data/respaldos/`,
   `data/eventos_perdidos_*.json` y `*.migrando`, además de los cuatro que pide el maestro §4.2. *Resuelta en el cotejo.* `SILICE_DATOS`, `SILICE_INSTALACION` y `SILICE_RESPALDOS` viven en `operacion.config` y no llevan alias; las de A1 (`SILICE_CASO`, `SILICE_MODO_ENTREGA`) siguen en `ui.entorno`.
5. **Seeds.** El spec §6.2 y §13 dicen que `scripts/seed*.py` llaman a `preparar_base` en S5‑1; el encargo no los
   incluye. Se dejan con `create_all` (sus bases se adoptan al abrirse) y el Inicio prepara el caso antes de sembrar; se
   declara el disparador (una revisión que altere columnas de una tabla existente) en el manual técnico §10.5. *Abierta (decisión 5 de `cotejo.md`; por defecto, los seeds siguen con `create_all`).*
6. **`SILICE_CASO` (antes `ARENIA_CASO`), `APU_BASE` y las pruebas.** El spec §6.6 dice «toda ruta pasa por `resolve` + `is_relative_to`». El
   plan lo aplica a todo nombre que llega del usuario (lista, crear, subir); `SILICE_CASO`, `APU_BASE` y las rutas que
   parchan las pruebas (`RUTA_BASE_POR_DEFECTO`, más de veinte archivos de prueba) son configuración de quien arranca y
   se preparan sin pasar por la lista, como prevé el spec §5.3 («siguen existiendo para las pruebas y el camino de
   desarrollo»). *Resuelta en el cotejo.* `ARENIA_CASO` pasó a `SILICE_CASO` (A1); `ui/caso.py` de la Tarea 6 conserva `ui.entorno.leer_variable` y las claves `silice_*`.
7. **La API.** El spec §5.2 dice que `api/dependencias.py` «si no está en `head`, responde 503 en vez de crear tablas»;
   el encargo pide que la API abra el caso vía `preparar_base`. El plan migra con respaldo (como la interfaz) y responde
   503 solo cuando `preparar_base` no puede (más nueva, ilegible, bloqueada, no adoptable). *Abierta (decisión 4 de `cotejo.md`; por defecto, la API migra con respaldo y responde 503 solo si no puede).*
8. **Nueve páginas, once llamadas.** El spec cuenta nueve páginas; `actualizacion.py` (`:175`, `:266`) y `elaborar.py`
   (`:159`, `:268`) llaman dos veces a `crear_esquema`: son once sustituciones, más `ui/caso.py:128` y
   `api/dependencias.py:22`. *Resuelta en el cotejo.* C agrega `indices`, `precios_empresa` y `reajuste` a `PAGINAS_QUE_ABREN_EL_CASO`.
9. **Caso por defecto.** `RUTA_BASE_POR_DEFECTO` pasa de `"data/apu.db"` a `None` (el caso por defecto de la carpeta de
   datos); `tests/unit/test_ui_caso.py:57-58` y cinco pruebas de `tests/unit/test_ui_inicio.py` se reescriben (no están en
   el bloque de regresión). `docs/manual_usuario.md` (líneas 47, 141, 657) también citaba el campo de ruta libre. *Resuelta en el cotejo.*
10. **Versión en la ficha.** El spec §6.3 pide «versión de Sílice» en la ficha; `operacion.version` es de S5‑2, así que
    `operacion.respaldo` la lee de `pyproject.toml` en privado (hoy `0.1.0`, que RF‑99 alinea) hasta que exista. *Resuelta en el cotejo.*
11. **Revisión base por DDL literal.** El spec §6.1 la genera «con la autogeneración de Alembic contra una base vacía
    creada con el código de `v0.5.0`»; el plan congela el DDL literal de `sqlite_master` de la base de prueba de
    `v0.5.0`, que es más exacto (mismo texto de `CREATE`), y lo verifica contra las tres bases de la etiqueta. *Abierta (decisión 6 de `cotejo.md`; por defecto, DDL literal congelado).*
12. **Base de prueba de la 0.5.0 en tres archivos** (`demo.db`, `of001.db`, `ti001.db`) en vez de una: sembrar los tres
    casos en un solo archivo arriesgaba choques de insumos entre catálogos. La ficha lleva una entrada por base. *Resuelta en el cotejo.* C agrega `s1.db` a `CONSTRUCTORES` para la base de la 0.6.0.
13. **Estado del repositorio.** INSTRUCCIONES dice `main` 8610053; la rama `inc/silice` está en 32a95c3 (8610053 más
    los commits de specs), sin diferencias de código respecto de `v0.5.0` (`git diff v0.5.0 HEAD --stat` solo toca
    `docs/`). *Resuelta en el cotejo.* La sección A fija la base real: toda rama sale de `origin/main` (ed597de o posterior), no de `main` local.
14. **Punto de partida.** La sección decía que la rama sale tras el PR «dependencias Sílice»; necesita además A3 (la
    guardia de red, que bloquea cualquier conexión de sus pruebas) y A4 (la meta en la que se registra). *Resuelta en el
    cotejo:* `inc/060-s5-1-alembic` sale de `origin/main` con A1–A4 fusionadas.
15. **Fixture renombrada por A1.** La Tarea 1 citaba `_sin_caso_del_entorno` (línea 61); A1 la reemplaza por
    `_sin_variables_de_silice_del_entorno` y A3 agrega `_guardia_de_red` al final. *Resuelta en el cotejo.*
16. **`ui/caso.py` completo pisaba A1.** La Tarea 6 reescribía el archivo con `VARIABLE_RUTA_CASO = "ARENIA_CASO"` y claves
    `arenia_*`, que `tests/unit/test_nombre_silice.py` (A1) prohíbe en `ui/`. *Resuelta en el cotejo:* el archivo conserva
    `from ui.entorno import VARIABLE_CASO, leer_variable`, `VARIABLE_RUTA_CASO = VARIABLE_CASO`, `silice_*` y
    `resolver_ruta` con `leer_variable`.
17. **Registro en la meta única.** La sección no se registraba en `scripts/meta_silice.py`. *Resuelta en el cotejo:* la
    Tarea 7 crea `scripts/meta_silice_s5.py` con `PARTE` (RF‑96 y RNF‑20, ocho `ParTDD`, `S5-M3`) y sube la CI a
    `--hasta S5-1`. S5‑M2 (núcleo intacto) no entra como comprobación acumulable porque S1 sí toca `core/`: queda en
    `guardia_nucleo.py` y en la compuerta.
18. **`CHANGELOG.md` y T0.** A §Discrepancias 7 pide que S5‑1 recoja las cinco PR de T0. *Resuelta en el cotejo:* la Tarea 7
    lo crea con esas líneas y la de S5‑1, y su prueba lo exige.
19. **Bloque de regresión de la compuerta.** La lista propia incluía `tests/unit/test_equilibrio.py` (fuera del bloque) y
    omitía `test_linea_base.py` y `test_composicion_extremo_a_extremo.py`. *Resuelta en el cotejo:* GS5‑1 usa C5 de la meta
    y los `ARCHIVOS_REGRESION` de A4.
20. **Bitácora.** `docs/bitacora/2026-10-silice-0.6.0.md` → `docs/bitacora/2026-10-silice-060.md` (la abre A1). *Resuelta en
    el cotejo.*

---

# C. S1 — Moneda por proyecto, precios de empresa, BCV y reajuste (fases S1‑0 … S1‑5)

> **Para quien ejecute:** `superpowers:subagent-driven-development`, un subagente por tarea y revisor fresco. Casillas `- [ ]`. Este plan **no repite** el spec: lo cita por sección (`S1 §n` = `docs/especificaciones/2026-10-11-silice-s1-moneda-reajuste-design.md`; `M §n` = spec maestro).

**Meta:** un proyecto en Bs y otro en USD con su reajuste comparado (escalatoria frente a comprobación directa) en las dos monedas; una empresa con su lista propia y sus precios vencidos o fuera de rango marcados con el dinero que representan (S1 §1, criterio de éxito de la 0.6.0).

**Arquitectura:** tres expedientes de núcleo (SL‑E1 moneda/tasa/origen/conversión/erosión; SL‑E2 lista de empresa, R11, R12; SL‑E3 reajuste) con tablas aditivas en `core/models/moneda.py` (reexportadas en `core/models/__init__.py`), una revisión de Alembic por fase de núcleo en `migraciones/caso/`; adaptador `adapters/bcv` (cuadrícula neutra, sin `core`); capa `ui/indices.py`, `ui/precios_empresa.py`, `ui/reajuste.py` sin Streamlit y tres páginas nuevas.

**Depende de** (nombres unificados en `cotejo.md`):
- Sección A (T0, fusionada antes que B): A2 «dependencias Sílice» (extra `bcv` con `xlrd>=2.0`; `xlrd` solo en `adapters/bcv/` y con importación diferida, `tests/unit/test_dependencias_silice.py`); A3 guardia de red única (`tests/conftest.py::_guardia_de_red`, `HF_HUB_OFFLINE=1`); A4 meta única `scripts/meta_silice.py` (`Parte`, `ParTDD`, `Comprobacion`, `Contexto`, `FASES["0.6.0"]` ya con `S1-0`…`S1-5`, bloque `REGRESION`/`ARCHIVOS_REGRESION`; cada parte se registra creando `scripts/meta_silice_<parte>.py` con `PARTE = Parte(...)`, sin editar `meta_silice.py`); A1 `ui.entorno` (`SILICE_CASO`, `SILICE_MODO_ENTREGA`).
- Sección B (S5‑1, fusionada antes de abrir cualquier rama de C): `tests/fixtures/arquitectura.py` (`RAIZ`, `archivos`, `ruta`, `importaciones`, `llamadas`); `tests/unit/test_arquitectura_s5.py::PAGINAS_QUE_ABREN_EL_CASO`; revisión base `caso_0001_base_0_5_0` en `migraciones/caso/versions/` y su plantilla `migraciones/caso/script.py.mako`; `operacion.base_datos.preparar_base(ruta, destino=Destino.CASO, *, entorno=None) -> ResultadoPreparacion`, `Destino`, `revision_head`; base de prueba 0.5.0 en `tests/fixtures/bases/v0_5_0/` (`demo.db`, `of001.db`, `ti001.db`, `ficha.json`) con los ayudantes de `tests/fixtures/bases_prueba.py` (`ficha`, `nombres`, `copiar_base`, `diferencias_con_ficha`); generador `scripts/generar_base_prueba.py`; prueba de deriva RNF‑20 `tests/integration/test_migraciones.py`; `CHANGELOG.md` con `[Sin publicar]`.

**S1 empieza después de fusionar S5‑1** (`inc/060-s5-1-alembic`). Orden de ramas de C: `inc/060-s1-0-docs` → `inc/060-s1-1-nucleo` → (`inc/060-s1-2-bcv` en paralelo, sin núcleo pendiente) → `inc/060-s1-3-nucleo` → `inc/060-s1-3-ui` → `inc/060-s1-4-nucleo` → `inc/060-s1-4-ui` → `inc/060-s1-5-cierre` → `inc/060-s1-5-base`.

## Restricciones globales

- `Decimal` en todo monto; divisiones con `decimal.localcontext(prec=28, rounding=ROUND_HALF_EVEN)` **dentro** de la función; se redondea solo al presentar (S1 §5.3).
- `core/contracts/` intocable (`git diff v0.5.0..HEAD -- core/contracts/` vacío). Si parece necesario un tipo nuevo ahí, se detiene y se registra (NORMAS §9).
- Pruebas antes que código con el **rojo visto**: el commit de la prueba precede al de la implementación (SL‑E1…E3 y cada intérprete del adaptador). Cero omitidas; `-W error`.
- Cada cambio en `core/` escribe primero su expediente en `docs/bitacora/2026-10-silice-expedientes.md`.
- Carril único de núcleo: `inc/060-s1-1-nucleo` → `inc/060-s1-3-nucleo` → `inc/060-s1-4-nucleo`; nunca dos abiertas. Una rama de núcleo toca solo `core/`, `migraciones/`, `tests/`, `docs/`; una de interfaz, `ui/`, `tests/`, `docs/`. `inc/060-s1-2-bcv` (solo `adapters/bcv/`, `tests/`, `docs/`) sale de `main` **sin núcleo pendiente** y puede ir en paralelo; se fusiona al cruzar GS1‑2.
- Comandos: `unset VIRTUAL_ENV; uv sync --all-extras` antes de pytest; `uv run pytest -q -W error`; `uv run ruff check <archivos>`; `uv run python scripts/guardia_nucleo.py --base origin/main`. Nunca `ruff format .`, `pkill`, `taskkill`, `git add -A`, ni nada contra `data/apu.db`.
- Commits convencionales en español, asunto sin tildes, con la línea final `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (en los bloques se escribe como segundo `-m`).
- Texto ajeno (hojas y etiquetas del BCV, descripciones de listas importadas) se muestra con `ui.texto_seguro.texto_seguro()` o en celdas; nunca `unsafe_allow_html` (RV‑14).
- Reglas externas R11/R12 según M §3.3: fecha de evaluación **explícita**; toda reevaluación en memoria, nunca reescribe filas guardadas.
- Cada PR se fusiona con `gh pr merge <n> --merge` (merge commit, nunca *squash*: C3 de la meta lee el orden prueba → implementación). Bitácora de la versión: `docs/bitacora/2026-10-silice-060.md` (la abre A1); expedientes: `docs/bitacora/2026-10-silice-expedientes.md` (lo crea la Tarea 4).
- **`--hasta` de la CI.** El paso «Meta de Silice» de `.github/workflows/ci.yml` (A4) lo sube, en el orden de `FASES`, el PR que cruza cada compuerta: S1‑0 → `--hasta S1-0`, S1‑1 → `S1-1`, … Si `inc/060-s1-2-bcv` se fusiona antes que `inc/060-s1-1-nucleo`, deja `--hasta` donde está y es el PR de S1‑1 el que lo sube a `S1-2`. La base de la 0.6.0 sube a `S1-5` (Tarea 14).
- Los números de línea de `ui/app.py`, `ui/caso.py`, `tests/conftest.py`, `tests/unit/test_arquitectura.py` y `tests/unit/test_ui_app.py` citados aquí son los de `v0.5.0`: A1 y B los mueven; se ubican por contenido.
- **Páginas nuevas que abren el caso** (`indices`, `precios_empresa`, `reajuste`): lo preparan con `preparar_base(ruta_caso())` antes de `crear_motor` y se agregan a `PAGINAS_QUE_ABREN_EL_CASO` de `tests/unit/test_arquitectura_s5.py` (B, Tarea 6), que exige ambas cosas a toda página con `crear_motor`.

## Mapa de tareas

| Fase | Tarea | Rama | Rol |
|---|---|---|---|
| S1‑0 | 1 ERS, documentos y comprobaciones S1 de la meta | `inc/060-s1-0-docs` | pruebas |
| S1‑0 | 2 Lista MaPreX en Bs y las cuatro memorias a mano | `inc/060-s1-0-docs` | pruebas |
| S1‑0 | 3 Archivos reales del BCV, `FUENTE.md`, `bcv_formatos.md`, licencia de `xlrd` | `inc/060-s1-0-docs` | adaptadores |
| S1‑1 | 4 SL‑E1a: tablas, revisión `caso_0002`, índices y tasa aplicable | `inc/060-s1-1-nucleo` | núcleo |
| S1‑1 | 5 SL‑E1b: conversión, erosión, origen por precio, `convertir_version` | `inc/060-s1-1-nucleo` | núcleo |
| S1‑2 | 6 Adaptador `adapters/bcv` | `inc/060-s1-2-bcv` | adaptadores |
| S1‑3 | 7 SL‑E2a: lista de empresa, referencia, lector, `lista_vigente`, revisión `caso_0003` | `inc/060-s1-3-nucleo` | núcleo |
| S1‑3 | 8 SL‑E2b: R11, R12 e instantánea de precios | `inc/060-s1-3-nucleo` | núcleo |
| S1‑3 | 9 Pantallas de UC‑17 (índices y precios de la empresa) | `inc/060-s1-3-ui` | interfaz |
| S1‑3 | 10 Hoja: moneda en Parámetros, origen/erosión/R11‑R12 en Precios | `inc/060-s1-3-ui` | interfaz |
| S1‑4 | 11 SL‑E3a: reajuste puro contra las memorias | `inc/060-s1-4-nucleo` | núcleo |
| S1‑4 | 12 SL‑E3b: tablas, revisión `caso_0004`, estudio guardado, RNF‑14 | `inc/060-s1-4-nucleo` | núcleo |
| S1‑4 | 13 Pantalla de UC‑18 y exportación por `hojas_extra` | `inc/060-s1-4-ui` | interfaz |
| S1‑5 | 14 Cierre: versión, manuales, recorridos, etiqueta; base de prueba 0.6.0 desde la etiqueta | `inc/060-s1-5-cierre` y luego `inc/060-s1-5-base` | pruebas |

---

# S1‑0 — Documentos, oráculos y archivos reales (rama `inc/060-s1-0-docs`)

### Tarea 1: ERS, documentos y la parte S1 de `meta_silice`

**Rama:** `inc/060-s1-0-docs` (sale de `main` tras fusionar S5‑1; PR a `main`; RV‑2)   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `scripts/meta_silice_s1.py`, `tests/unit/test_meta_silice_s1.py`
- Modificar: `.github/workflows/ci.yml` (paso «Meta de Silice» de A4: `--hasta S1-0`); `docs/ERS.md:642-663` (tras UC‑16: UC‑17, UC‑18), `docs/ERS.md:729-841` (§3.2, tras la fila RF‑63 y la RF‑96 de S5‑1: RF‑64…RF‑71), `docs/ERS.md:842-859` (§3.3: RNF‑14), tabla «UC existentes que se enmiendan» (UC‑01 paso 1, UC‑02, UC‑15) y matriz §4 (`:867-909`); `docs/modelo_datos.md:392` (nueva §2.5 antes de §3); `docs/arquitectura.md` (vista lógica: `adapters/bcv`, `core/models/moneda.py`); `docs/plan_pruebas.md:222` (nueva §8.0b RF‑64…71) y §9 (RNF‑14); `NORMAS.md:176-191` (§6: `core/models` con las tablas de S1, `adapters/bcv/`); `CHANGELOG.md` (una línea bajo `[Sin publicar]`, archivo que creó B en su Tarea 7)
- No se toca `scripts/meta_silice.py`: `FASES["0.6.0"]` ya trae `S1-0`…`S1-5` (A4) y `partes()` descubre `scripts/meta_silice_s1.py` por su nombre.

**Interfaces:**
- Consume: de `scripts.meta_silice` (A4): `Parte`, `ParTDD`, `Comprobacion`, `Contexto`, `orden_de_par(par) -> bool | None`, `_primer_commit(ruta) -> str | None`, `partes()`, `validar_partes(todas)`; de `scripts.meta_sf`: `_ordenar_memoria(memoria, criterio) -> bool | None`, `evaluar_s2_memorias(presentes, antes_del_codigo, codigo_existe=True)`; `scripts.meta_alpha.Estado`.
- Produce: `scripts.meta_silice_s1.PARTE: Parte` (requisitos de `S1-0`; pares de `S1-0`…`S1-4`; comprobaciones `S1-MEM` y `S1-FUENTE` en `S1-0` y `S1-BASE-060` en `S1-5`); `REQUISITOS_S1: tuple[str, ...]` (once); `MEMORIAS_S1: dict[str, tuple[str, ...]]`; `PARES_S1: tuple[ParTDD, ...]`; `evaluar_fuente_bcv(fuente_existe: bool, interprete_existe: bool, orden: bool | None) -> tuple[Estado, str]`; `evaluar_base_060(carpeta: Path) -> tuple[Estado, str]`.

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/unit/test_meta_silice_s1.py
"""Parte S1 de la meta unica de Silice (spec S1 §9.4; plan 0.6.0, seccion C, tarea 1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.meta_alpha import Estado
from scripts.meta_silice import partes, validar_partes
from scripts.meta_silice_s1 import (
    MEMORIAS_S1,
    PARTE,
    REQUISITOS_S1,
    evaluar_base_060,
    evaluar_fuente_bcv,
)


def test_la_parte_s1_se_descubre_y_usa_fases_de_la_0_6_0() -> None:
    validar_partes((PARTE,))
    assert any(parte is PARTE for parte in partes())
    assert PARTE.requisitos == {"S1-0": REQUISITOS_S1}
    assert {par.fase for par in PARTE.pares_tdd} == {"S1-0", "S1-1", "S1-2", "S1-3", "S1-4"}
    assert [(c.codigo, c.fase) for c in PARTE.comprobaciones] == [
        ("S1-MEM", "S1-0"),
        ("S1-FUENTE", "S1-0"),
        ("S1-BASE-060", "S1-5"),
    ]


def test_los_once_requisitos_y_las_cuatro_memorias() -> None:
    assert REQUISITOS_S1 == (
        "UC-17", "UC-18", "RF-64", "RF-65", "RF-66", "RF-67", "RF-68", "RF-69", "RF-70",
        "RF-71", "RNF-14",
    )
    assert sorted(MEMORIAS_S1) == [
        "s1_conversion.md",
        "s1_precios_empresa.md",
        "s1_reajuste.md",
        "s1_reajuste_por_partida.md",
    ]


def test_la_fuente_del_bcv_entra_antes_que_el_primer_interprete() -> None:
    assert evaluar_fuente_bcv(False, False, None)[0] is Estado.FALLA
    assert evaluar_fuente_bcv(True, False, None)[0] is Estado.OK
    assert evaluar_fuente_bcv(True, True, None)[0] is Estado.PENDIENTE
    assert evaluar_fuente_bcv(True, True, False)[0] is Estado.FALLA
    assert evaluar_fuente_bcv(True, True, True)[0] is Estado.OK


def test_la_base_0_6_0_exige_su_ficha_y_la_huella_de_cada_base(tmp_path: Path) -> None:
    assert evaluar_base_060(tmp_path / "v0_6_0")[0] is Estado.PENDIENTE
    carpeta = tmp_path / "v0_6_0"
    carpeta.mkdir()
    (carpeta / "s1.db").write_bytes(b"x")
    ficha = {
        "version": "0.6.0",
        "etiqueta": "v0.6.0",
        "commit": "abc1234",
        "bases": {"s1.db": {"sha256_base": hashlib.sha256(b"x").hexdigest()}},
    }
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    assert evaluar_base_060(carpeta)[0] is Estado.OK
    (carpeta / "s1.db").write_bytes(b"y")
    estado, detalle = evaluar_base_060(carpeta)
    assert estado is Estado.FALLA and "s1.db" in detalle
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_meta_silice_s1.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'scripts.meta_silice_s1'`
```bash
git add tests/unit/test_meta_silice_s1.py
git commit -m "test(scripts): parte S1 de la meta unica en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
```python
# scripts/meta_silice_s1.py
"""Parte S1 de la meta unica de Silice (spec S1 §9.4; plan 0.6.0, seccion C, tarea 1).

`scripts/meta_silice.py` (A4) la descubre por su nombre. Con `--hasta` en una fase de S1 evalua:
C1, los once requisitos de S1-0 por presencia en la ERS; C3, la prueba de cada expediente (SL-E1,
SL-E2, SL-E3) y de cada interprete del BCV antes que su codigo; y tres comprobaciones propias:
S1-MEM (memorias a mano antes del codigo que rigen), S1-FUENTE (archivos reales del BCV con su
`FUENTE.md` antes del primer interprete) y S1-BASE-060 (base de prueba de la 0.6.0 con su ficha).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_sf import _ordenar_memoria, evaluar_s2_memorias  # noqa: E402
from scripts.meta_silice import (  # noqa: E402
    Comprobacion,
    Contexto,
    ParTDD,
    Parte,
    _primer_commit,
    orden_de_par,
)

REQUISITOS_S1: tuple[str, ...] = (
    "UC-17",
    "UC-18",
    *(f"RF-{numero}" for numero in range(64, 72)),
    "RNF-14",
)

#: Memoria -> argumentos de `git log` que localizan el primer commit del codigo que rige.
MEMORIAS_S1: dict[str, tuple[str, ...]] = {
    "s1_conversion.md": ("--", "core/catalog/moneda.py"),
    "s1_precios_empresa.md": ("--", "core/verification/precios.py"),
    "s1_reajuste.md": ("--", "core/budget/reajuste.py"),
    "s1_reajuste_por_partida.md": ("--", "core/budget/reajuste.py"),
}
RUTA_MEMORIAS = RAIZ / "tests" / "fixtures" / "memorias"
RUTA_FUENTE_BCV = "tests/fixtures/bcv/FUENTE.md"
PRIMER_INTERPRETE_BCV = "adapters/bcv/tasa.py"
CARPETA_BASE_060 = RAIZ / "tests" / "fixtures" / "bases" / "v0_6_0"

#: Prueba -> implementacion, con la fase en que arranca cada par (C3 de la meta).
PARES_S1: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_meta_silice_s1.py", "scripts/meta_silice_s1.py", "S1-0"),
    ParTDD("tests/integration/test_indices.py", "core/catalog/indices.py", "S1-1"),
    ParTDD("tests/unit/test_moneda.py", "core/catalog/moneda.py", "S1-1"),
    ParTDD("tests/integration/test_conversion_version.py", "core/budget/moneda.py", "S1-1"),
    ParTDD("tests/unit/adapters/test_bcv_libro.py", "adapters/bcv/libro.py", "S1-2"),
    ParTDD("tests/unit/adapters/test_bcv_tasa.py", "adapters/bcv/tasa.py", "S1-2"),
    ParTDD("tests/unit/adapters/test_bcv_inpc.py", "adapters/bcv/inpc.py", "S1-2"),
    ParTDD("tests/unit/adapters/test_bcv_csv.py", "adapters/bcv/csv_canonico.py", "S1-2"),
    ParTDD("tests/integration/test_lista_empresa.py", "core/catalog/empresa.py", "S1-3"),
    ParTDD("tests/integration/test_precios_empresa.py", "core/verification/precios.py", "S1-3"),
    ParTDD("tests/unit/test_reajuste.py", "core/budget/reajuste.py", "S1-4"),
)


def evaluar_fuente_bcv(
    fuente_existe: bool, interprete_existe: bool, orden: bool | None
) -> tuple[Estado, str]:
    """S1-FUENTE: la transcripcion a mano existe y su commit precede al del primer interprete."""
    if not fuente_existe:
        return Estado.FALLA, f"falta {RUTA_FUENTE_BCV}"
    if not interprete_existe:
        return Estado.OK, f"{RUTA_FUENTE_BCV} presente; el interprete aun no existe"
    if orden is None:
        return Estado.PENDIENTE, f"sin commit de {RUTA_FUENTE_BCV} o de {PRIMER_INTERPRETE_BCV}"
    if not orden:
        return Estado.FALLA, f"{RUTA_FUENTE_BCV} no entro antes que {PRIMER_INTERPRETE_BCV}"
    return Estado.OK, f"{RUTA_FUENTE_BCV} versionado antes que {PRIMER_INTERPRETE_BCV}"


def evaluar_base_060(carpeta: Path) -> tuple[Estado, str]:
    """S1-BASE-060: `ficha.json` de la etiqueta v0.6.0 y la huella SHA-256 de cada base."""
    ruta_ficha = carpeta / "ficha.json"
    if not ruta_ficha.is_file():
        return Estado.PENDIENTE, "la base de prueba 0.6.0 se genera desde la etiqueta v0.6.0"
    ficha = json.loads(ruta_ficha.read_text(encoding="utf-8"))
    if (ficha.get("version"), ficha.get("etiqueta")) != ("0.6.0", "v0.6.0"):
        return Estado.FALLA, f"la ficha dice {ficha.get('version')!r} / {ficha.get('etiqueta')!r}"
    bases = ficha.get("bases") or {}
    distintas = [
        nombre
        for nombre, datos in sorted(bases.items())
        if not (carpeta / nombre).is_file()
        or hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest() != datos["sha256_base"]
    ]
    if not bases or distintas:
        detalle = ", ".join(distintas) or "la ficha no trae bases"
        return Estado.FALLA, "bases ausentes o distintas de su ficha: " + detalle
    return Estado.OK, "base de prueba 0.6.0 con ficha: " + ", ".join(sorted(bases))


def _orden_memoria(memoria: str, criterio: tuple[str, ...]) -> bool | None:
    """Antes de que exista el codigo, basta que la memoria este versionada."""
    if not (RAIZ / criterio[-1]).exists():
        return True if _primer_commit(f"tests/fixtures/memorias/{memoria}") else None
    return _ordenar_memoria(memoria, criterio)


def _memorias(_ctx: Contexto) -> tuple[Estado, str]:
    presentes = {m: (RUTA_MEMORIAS / m).is_file() for m in MEMORIAS_S1}
    antes = {m: _orden_memoria(m, criterio) for m, criterio in MEMORIAS_S1.items()}
    codigo = any((RAIZ / criterio[-1]).exists() for criterio in MEMORIAS_S1.values())
    return evaluar_s2_memorias(presentes, antes, codigo_existe=codigo)


def _fuente(_ctx: Contexto) -> tuple[Estado, str]:
    interprete = (RAIZ / PRIMER_INTERPRETE_BCV).is_file()
    par = ParTDD(RUTA_FUENTE_BCV, PRIMER_INTERPRETE_BCV, "S1-0")
    orden = orden_de_par(par) if interprete else None
    return evaluar_fuente_bcv((RAIZ / RUTA_FUENTE_BCV).is_file(), interprete, orden)


def _base_060(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_base_060(CARPETA_BASE_060)


PARTE = Parte(
    nombre="S1 moneda, precios de empresa, BCV y reajuste",
    requisitos={"S1-0": REQUISITOS_S1},
    pares_tdd=PARES_S1,
    comprobaciones=(
        Comprobacion("S1-MEM", "Memorias antes del codigo que rigen", "S1-0", _memorias),
        Comprobacion("S1-FUENTE", "FUENTE.md del BCV antes del interprete", "S1-0", _fuente),
        Comprobacion("S1-BASE-060", "Base de prueba 0.6.0 con su ficha", "S1-5", _base_060),
    ),
)
```
  `.github/workflows/ci.yml`, paso «Meta de Silice»: `--hasta S5-1` → `--hasta S1-0`.
- [ ] **Paso 4: Correrla y ver el verde**, y escribir los documentos: UC‑17, UC‑18, RF‑64…RF‑71 y RNF‑14 **copiados** de S1 §3.1–§3.3 con sus columnas (prioridad, fase, criterio), con la forma que `_patron_definicion` reconoce (UC por encabezado `###`/`####`, RF por fila `| RF‑nn |`, RNF en la 2.ª celda de la tabla de calidad); tabla de enmiendas de UC‑01/02/15; modelo de datos §2.5 con las tablas de S1 §5.2 (incluida la nota «empresa como texto, RV‑6»); plan de pruebas §8.0b con la matriz S1 §9.2; NORMAS §6. Luego `uv run pytest tests/unit/test_meta_silice_s1.py tests/unit/test_meta_silice.py -q -W error` (PASS), `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml` y `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S1-0 --junit reporte-pruebas.xml` → C1 OK (los once de S1 y los de S5‑1); `S1-MEM` en PENDIENTE y `S1-FUENTE` en FALLA hasta las tareas 2 y 3.
- [ ] **Paso 5: Commit**
```bash
git add scripts/meta_silice_s1.py .github/workflows/ci.yml docs/ERS.md docs/modelo_datos.md docs/arquitectura.md docs/plan_pruebas.md NORMAS.md CHANGELOG.md
git commit -m "docs(ers): S1 con UC-17, UC-18, RF-64 a RF-71 y RNF-14; parte S1 de la meta" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Tarea 2: Lista MaPreX en Bs y las cuatro memorias a mano

**Rama:** `inc/060-s1-0-docs`   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `scripts/lista_maprex_bs.py`, `data/precios/maprex_2026-07/lista_maprex_bs.csv` (salida del script), `tests/unit/test_lista_maprex_bs.py`, `tests/fixtures/memorias/s1_conversion.md`, `tests/fixtures/memorias/s1_reajuste.md`, `tests/fixtures/memorias/s1_reajuste_por_partida.md`, `tests/fixtures/memorias/s1_precios_empresa.md`, `tests/fixtures/precios_empresa_s1.csv`, `tests/unit/test_memorias_s1.py`
- Modificar: `scripts/README.md` (una fila)

**Interfaces:**
- Produce: `scripts.lista_maprex_bs.COLUMNAS_SALIDA = ("tipo","insumo","unidad","precio","fecha","fuente","referencia")`; `filas_canonicas() -> list[dict[str, str]]`; `RUTA_SALIDA`; `TASA_MAPREX = Decimal("633.3644")`; `FECHA_TASA_MAPREX = date(2026, 7, 1)`; `FUENTE_TASA_MAPREX: str`. Las memorias y `precios_empresa_s1.csv` son los oráculos de las tareas 5, 8, 11 y 12.

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/unit/test_lista_maprex_bs.py
from decimal import Decimal

from scripts.lista_maprex_bs import COLUMNAS_SALIDA, RUTA_SALIDA, filas_canonicas


def test_las_111_filas_llevan_precio_bs_fecha_y_ref_tal_cual():
    filas = filas_canonicas()
    assert len(filas) == 111  # verificadas a mano en M0.2 (S1 §6.2)
    assert all(tuple(f) == COLUMNAS_SALIDA for f in filas)
    tubo = next(f for f in filas if f["referencia"] == "PLOA38")
    assert (tubo["precio"], tubo["fecha"]) == ("8822.17", "2026-07-09")  # referencia_civil.csv
    assert next(f for f in filas if f["referencia"] == "1-1.2")["fecha"] == "2026-07-01"


def test_todo_precio_es_decimal_positivo_desde_texto_y_la_salida_existe():
    assert all(Decimal(f["precio"]) > 0 for f in filas_canonicas())
    assert RUTA_SALIDA.name == "lista_maprex_bs.csv"
```
```python
# tests/unit/test_memorias_s1.py
from pathlib import Path

import pytest

MEMORIAS = Path(__file__).resolve().parents[1] / "fixtures" / "memorias"
LITERALES = {
    "s1_conversion.md": ["1,578869920696521623255111907", "1,162547373805482573414866656",
                         "0,42 USD", "358,11 Bs", "26,37 %", "35,81 %"],
    "s1_reajuste.md": ["1,17", "15 300,00", "16 000,00", "−700,00", "18,00", "18,82", "−0,82"],
    "s1_reajuste_por_partida.md": ["1,175", "1,185", "10 298,34", "11 680,00", "−1 381,66",
                                   "12,12", "13,74", "−1,63", "9 785,88"],
    "s1_precios_empresa.md": ["2026-10-01", "13 377,74", "143 309,00", "1 368,10",
                              "20 521,45", "−20,01 %", "+30,01 %"],
}


@pytest.mark.parametrize("memoria", sorted(LITERALES))
def test_cada_memoria_existe_y_trae_sus_cifras_literales(memoria):
    texto = (MEMORIAS / memoria).read_text(encoding="utf-8")
    faltan = [cifra for cifra in LITERALES[memoria] if cifra not in texto]
    assert not faltan, f"{memoria} no trae {faltan}"
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_lista_maprex_bs.py tests/unit/test_memorias_s1.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'scripts.lista_maprex_bs'` y `FileNotFoundError` por cada memoria.
- [ ] **Paso 3: Implementación mínima**
```python
# scripts/lista_maprex_bs.py
"""Lista MaPreX julio 2026 en Bs (spec S1 §6.2): referencia de R11.

Copia como texto la columna `precio_bs` de los cuatro `referencia_*.csv` (111 filas verificadas a
mano en M0.2) con su fecha y su Ref; no reconstruye bolivares desde `precio_usd` (redondeado a 4
decimales). Mismo orden y deduplicacion que `scripts/lista_maprex_usd.py`. Columnas: las de UC‑02
mas las opcionales de UC‑17 (`fecha`, `fuente`, `referencia`).

Uso: `uv run python scripts/lista_maprex_bs.py`
"""

from __future__ import annotations

import csv
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.lista_maprex_usd import ARCHIVOS_ORIGEN, CARPETA  # noqa: E402

RUTA_SALIDA = CARPETA / "lista_maprex_bs.csv"
COLUMNAS_SALIDA = ("tipo", "insumo", "unidad", "precio", "fecha", "fuente", "referencia")
TASA_MAPREX = Decimal("633.3644")
FECHA_TASA_MAPREX = date(2026, 7, 1)
FUENTE_TASA_MAPREX = (
    "MaPreX v26.0.0.1, mano_de_obra.pdf: «01JUL @ 633,3644 BS/$» "
    "(data/precios/maprex_2026-07/README.md)"
)


def filas_canonicas() -> list[dict[str, str]]:
    vistos: dict[tuple[str, str, str], dict[str, str]] = {}
    for ruta in ARCHIVOS_ORIGEN:
        with ruta.open(newline="", encoding="utf-8") as archivo:
            for fila in csv.DictReader(archivo):
                clave = (fila["tipo"], fila["insumo"], fila["unidad"])
                if clave in vistos or not fila["precio_bs"].strip():
                    continue
                vistos[clave] = {
                    "tipo": fila["tipo"],
                    "insumo": fila["insumo"],
                    "unidad": fila["unidad"],
                    "precio": fila["precio_bs"].strip(),
                    "fecha": fila["fecha_vigencia"].strip(),
                    "fuente": f"{fila['archivo']} Ref {fila['ref_maprex']}",
                    "referencia": fila["ref_maprex"].strip(),
                }
    return [vistos[c] for c in sorted(vistos)]


def main() -> int:
    filas = filas_canonicas()
    with RUTA_SALIDA.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_SALIDA)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"{RUTA_SALIDA} generado con {len(filas)} filas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
  Correr `uv run python scripts/lista_maprex_bs.py`. Escribir las memorias **a mano** (rehaciendo cada cuenta en papel o calculadora, no con el código que se probará):

```markdown
<!-- tests/fixtures/memorias/s1_conversion.md -->
# Memoria S1: conversión y erosión (oráculo de RF‑66, spec S1 §9.1.1)
Precio ficticio P = 1 000 Bs del 01/07/2026; T0 = 633,3644 Bs/USD (MaPreX, verificada); evaluación al
01/10/2026 con T1 = 860,18 Bs/USD (BCV venta, fecha valor 01‑10‑2026, verificada). Decimal de 28 dígitos,
ROUND_HALF_EVEN.
| Cuenta | Valor exacto | Presentado |
|---|---|---|
| P/T0 | 1,578869920696521623255111907 USD | 1,58 USD |
| P/T1 | 1,162547373805482573414866656 USD | 1,16 USD |
| Erosión en USD = P/T0 − P/T1 | 0,416322546891039049840245251 | 0,42 USD |
| Erosión en Bs = P·T1/T0 − P | 358,112328384733969891582160 | 358,11 Bs |
| Porcentaje = 1 − T0/T1 | 0,2636838801181148131786370295 | 26,37 % |
| Contraste (NO es el de §5.3): 358,11 / 1 000 | — | 35,81 % |
Un precio en USD tiene erosión 0 en las dos monedas (declarado: no hay índice de inflación en USD).
```
```markdown
<!-- tests/fixtures/memorias/s1_reajuste.md -->
# Memoria S1: reajuste, estructura declarada (oráculo de RF‑70 y RF‑71, spec S1 §9.1)
Datos ficticios y declarados. Contrato: inicio 15/01/2026, 24 meses, primer año hasta el 15/01/2027;
partida S1‑R01, PU del contrato 100 Bs (un material de 100 Bs, FCAS, bono, administración y utilidad
en 0), presupuestado Q = 1 000. Cláusula: `declarada`, pesos materiales 0,5 / equipos 0,2 / mano de obra
0,3; series FIC‑MAT, FIC‑EQU, FIC‑MO (unidad «indice_bs»); I0 = enero 2026; R = 0,10 (fuente: memoria).
Período 01/02/2027–28/02/2027 (fuera del primer año); índices de febrero 2027: 200→230, 150→165, 80→100.
Ejecutado: 1 000 unidades (acta ficticia AV‑01). PU comprobado (versión revalorada, material a 116 Bs):
116 Bs. Tasa ficticia de cierre: 850 Bs/USD. Fecha de cálculo 05/03/2027 (estudio «cerrado»).
- Km = 0,5·230/200 + 0,2·165/150 + 0,3·100/80 = 0,575 + 0,22 + 0,375 = **1,17**
- Vo = 1 000 · 100 = 100 000 Bs; escalatoria = 100 000 · 0,17 · 0,9 = **15 300,00 Bs** (15 300 / 850 = **18,00 USD**)
- Comprobación = 1 000 · (116 − 100) = **16 000,00 Bs** (16 000 / 850 = 18,8235… → **18,82 USD**)
- Diferencia (escalatoria − comprobación) = **−700,00 Bs** (−700 / 850 = −0,8235… → **−0,82 USD**)
- Monto reconocido con `ambos`: `mecanismo_pagadero = comprobacion` → 16 000,00 Bs; sin declarar → 15 300,00 Bs.
- 15 300 / 100 000 = 15,3 % > 10 %: lleva la nota INDICIO de la Comisión.
- Fronteras: ejecutado acumulado = 1 000 pasa sin aviso; 1 000,001 se guarda con aviso y se reajusta 1 000.
```
```markdown
<!-- tests/fixtures/memorias/s1_reajuste_por_partida.md -->
# Memoria S1: reajuste por partida (PRU‑H12, spec S1 §9.1.2)
Mismas fechas, índices, R = 0,10 y tasa 850 que `s1_reajuste.md`; estructura `por_partida`. PU = CD × 1,30
(administración 0,30, utilidad 0; FCAS y bono 0; rendimiento 1).
| Partida | mat. / equipos / M.O. | CD | Pesos | PU contrato | Ejecutado | PU comprobado |
|---|---|---|---|---|---|---|
| A | 45,00 / 7,50 / 22,50 | 75,00 | 0,6 / 0,1 / 0,3 | 97,50 | 400 | 115,00 |
| B | 32,00 / 48,00 / 80,00 | 160,00 | 0,2 / 0,3 / 0,5 | 208,00 | 120 | 247,00 |
- K_A = (45·1,15 + 7,5·1,10 + 22,5·1,25)/75 = 88,125/75 = **1,175**; K_B = 189,60/160 = **1,185**
- Escalatoria A = 39 000·0,175·0,9 = 6 142,50; B = 24 960·0,185·0,9 = 4 155,84; total **10 298,34 Bs** (**12,12 USD**)
- Comprobación A = 400·17,50 = 7 000,00; B = 120·39,00 = 4 680,00; total **11 680,00 Bs** (**13,74 USD**)
- Diferencia **−1 381,66 Bs**; en USD −1 381,66/850 = −1,6254… → **−1,63** (una sola vez; no 12,12 − 13,74 = −1,62)
- Testigo: con `declarada` 0,5/0,2/0,3 daría 63 960·0,17·0,9 = **9 785,88 Bs**
```
```markdown
<!-- tests/fixtures/memorias/s1_precios_empresa.md -->
# Memoria S1: precios de empresa, R11 y R12 (oráculo de RF‑68, spec S1 §6.3 y §9.2)
Empresa ficticia «Constructora Ejemplo, C.A.», RIF J‑00000000‑0 (texto, RV‑6). Lista en Bs del 20/09/2026,
base y referencia = MaPreX julio 2026 en Bs (`lista_maprex_bs.csv`, tasa 633,3644 al 01/07/2026).
Precios propios en `tests/fixtures/precios_empresa_s1.csv`. **Fecha de evaluación fija: 2026-10-01**
(tasa venta 860,18, fecha valor 01‑10‑2026, BCV verificada). Rango −20 % / +30 %, plazo 30 días.
Versión ficticia en Bs: partida S1‑EMP‑01 con un material de cantidad 1 por cada insumo de la tabla,
cantidad de obra 10, administración 0,15, utilidad 0,10 (FCAS y bono 0): todo Δ de precio de un insumo
mueve el total en Δ · 1,15 · 1,10 · 10 = Δ · **12,65**.
Los precios en Bs declaran la tasa MaPreX para que el desvío sea exactamente p/p_ref − 1 (PRU‑H11).
| # | Insumo (MaPreX) | Ref | p_ref Bs | Precio en la lista (Bs) | Fecha | Condición |
|---|---|---|---|---|---|---|
| 1 | CEMENTO GRIS PORTLAND SACO 42.5 KG/93,7 LB | CEM019 | 12 080,00 | 13 288,00 (+10 %) | 2026‑09‑20 | dentro y vigente |
| 2 | CODO PVC 90 GRADOS A.N. D=4" | PLO035 | 4 530,00 | 3 624,00 = 0,8000·p_ref | 2026‑09‑20 | −20,00 % pasa |
| 3 | UNION PVC A.B. 4" | PLO560 | 5 285,00 | 4 227,4715 = 0,7999·p_ref | 2026‑09‑20 | −20,01 % |
| 4 | PIEDRA PICADA PARA CONCRETO | AGR081 | 37 750,00 | 49 075,00 = 1,3000·p_ref | 2026‑09‑20 | +30,00 % pasa |
| 5 | ARENA LAVADA | MZ0027 | 37 750,00 | 49 078,775 = 1,3001·p_ref | 2026‑09‑20 | +30,01 % |
| 6 | AGUA SUMINISTRADA EN CAMION CISTERNA O TANQUE | AGR003 | 7 550,00 | 7 550,00 | 2026‑09‑01 | 30 días pasa |
| 7 | CLAVO DE ACERO LISO L=2 1/2" | ACE076 | 302,00 | 302,00 | 2026‑08‑31 | 31 días |
| 8 | PEGAMENTO PARA PVC 1/4 GL TANGIT O SIM | MT539 | 21 895,00 | 30,00 USD × 700 = 21 000,00 | 2026‑09‑25 | tasa sin fecha |
| 9 | TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA | PLOA38 | 8 822,17 | 12,00 USD × 735,00 = 8 820,00 | 2026‑09‑26 | tasa sin fuente |
| 10 | LIJA DE AGUA N 100 (alta) | — | — | 150,00 | 2026‑09‑20 | sin referencia |
| 11 | MATERIAL GRANULAR INTEGRAL (heredado de la base) | BAS006 | 4 530,00 | 4 530,00 | 2026‑07‑09 | 84 días |
Desvíos de 8 y 9 (pasan): (21 000·633,3644)/(21 895·700) − 1 = −13,22 %; (8 820·633,3644)/(8 822,17·735) − 1 = −13,85 %.
Erosión en Bs por unidad (T1/T0 = 860,18/633,3644): clavo 302·0,358112328… = 108,1499231721896589072578124;
granular 4 530·0,358112328… = 1 622,248847582844883608867186. Precio original en USD: erosión 0 (declarada).
**Conjunto exacto de hallazgos a 2026‑10‑01 (versión):**
| Regla | Severidad | Insumo | Observado | Δ por unidad | Impacto en la versión (Bs) |
|---|---|---|---|---|---|
| R11 | ADVERTENCIA | UNION PVC A.B. 4" | −20,01 % | 1 057,53 | 13 377,74 |
| R11 | ADVERTENCIA | ARENA LAVADA | +30,01 % | 11 328,78 | 143 309,00 |
| R11 | INFO | 1 no contrastable (LIJA DE AGUA N 100, sin referencia) | 1 | — | — |
| R12 | ADVERTENCIA | CLAVO DE ACERO LISO L=2 1/2" | 31 días | 108,15 | 1 368,10 |
| R12 | ADVERTENCIA | MATERIAL GRANULAR INTEGRAL | 84 días | 1 622,25 | 20 521,45 |
| R12 | ERROR | PEGAMENTO PARA PVC 1/4 GL TANGIT O SIM | tasa 700 sin fecha | — | — |
| R12 | ADVERTENCIA | TUBO PVC A.N. D=4" … | tasa 735,00 sin fuente | 0,00 | 0,00 |
Reevaluada a 2026‑10‑06: se agrega R12 ADVERTENCIA del AGUA (35 días); las filas guardadas no cambian.
```
  `tests/fixtures/precios_empresa_s1.csv` (descripciones idénticas a MaPreX; la 11 no va: es heredada):
```text
tipo,insumo,unidad,precio,fecha,fuente,referencia,moneda,tasa,fecha_tasa,fuente_tasa
material,"CEMENTO GRIS PORTLAND SACO 42.5 KG/93,7 LB",sco,13288.00,2026-09-20,Cotizacion interna CI-001 (ficticia),CEM019,Bs,633.3644,2026-07-01,"MaPreX: 01JUL @ 633,3644 BS/$"
material,"CODO PVC 90 GRADOS A.N. D=4""",pza,3624.00,2026-09-20,Cotizacion interna CI-001 (ficticia),PLO035,Bs,633.3644,2026-07-01,"MaPreX: 01JUL @ 633,3644 BS/$"
material,"UNION PVC A.B. 4""",pza,4227.4715,2026-09-20,Cotizacion interna CI-001 (ficticia),PLO560,Bs,633.3644,2026-07-01,"MaPreX: 01JUL @ 633,3644 BS/$"
material,PIEDRA PICADA PARA CONCRETO,m3,49075.00,2026-09-20,Cotizacion interna CI-001 (ficticia),AGR081,Bs,633.3644,2026-07-01,"MaPreX: 01JUL @ 633,3644 BS/$"
material,ARENA LAVADA,m3,49078.775,2026-09-20,Cotizacion interna CI-001 (ficticia),MZ0027,Bs,633.3644,2026-07-01,"MaPreX: 01JUL @ 633,3644 BS/$"
material,AGUA SUMINISTRADA EN CAMION CISTERNA O TANQUE,m3,7550.00,2026-09-01,Cotizacion interna CI-001 (ficticia),AGR003,Bs,633.3644,2026-07-01,"MaPreX: 01JUL @ 633,3644 BS/$"
material,"CLAVO DE ACERO LISO L=2 1/2""",pza,302.00,2026-08-31,Cotizacion interna CI-001 (ficticia),ACE076,Bs,633.3644,2026-07-01,"MaPreX: 01JUL @ 633,3644 BS/$"
material,PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM,env,30.00,2026-09-25,Cotizacion proveedor PV-77 (ficticia),MT539,USD,700,,Tasa del proveedor (ficticia)
material,"TUBO PVC A.N. D=4"" / 110 MM E = 2,2 MM NORMA",m,12.00,2026-09-26,Cotizacion proveedor PV-78 (ficticia),PLOA38,USD,735.00,2026-09-26,
material,LIJA DE AGUA N 100,pza,150.00,2026-09-20,Cotizacion interna CI-002 (ficticia),,Bs,,,
```
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/unit/test_lista_maprex_bs.py tests/unit/test_memorias_s1.py tests/unit/test_lista_maprex_usd.py -q -W error`; tras el commit del paso 5, `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S1-0` → `S1-MEM OK` (memorias versionadas antes de todo código).
- [ ] **Paso 5: Commit**
```bash
git add scripts/lista_maprex_bs.py scripts/README.md data/precios/maprex_2026-07/lista_maprex_bs.csv tests/unit/test_lista_maprex_bs.py tests/unit/test_memorias_s1.py tests/fixtures/memorias/s1_*.md tests/fixtures/precios_empresa_s1.csv
git commit -m "test(memorias): oraculos de S1 y lista MaPreX en Bs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Tarea 3: Archivos reales del BCV, `FUENTE.md`, `bcv_formatos.md` y licencia de `xlrd`

**Rama:** `inc/060-s1-0-docs`   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `tests/fixtures/bcv/<archivo de la tasa 3T‑2026 tal como se descarga>`, `tests/fixtures/bcv/<archivo del INPC con niveles>`, `tests/fixtures/bcv/FUENTE.md`, `docs/fuentes/bcv_formatos.md`, `tests/unit/test_fuente_bcv.py`
- Modificar: `docs/fuentes/README.md` (si existe; si no, el índice de `docs/README.md`), `docs/bitacora/2026-10-silice-060.md` (licencia de `xlrd`: BSD, verificada en su `LICENSE` de PyPI; S1‑R12)

**Interfaces:**
- Produce: `FUENTE.md` con tablas **legibles por máquina** que las pruebas de la Tarea 6 leen: sección «Tasa» (`| Campo | Valor |` con `Archivo`, `Dirección`, `Página`, `Fecha de descarga`, `SHA-256`, `Hojas (N)`) y `| Hoja | Posición | Fecha valor | Compra | Venta |` (posiciones `primera`, `medio`, `última`); sección «INPC» igual con `| Mes | Posición | Valor | Provisional |` («Mes» en `AAAA-MM`, «Provisional» `sí` o `no`; cada tabla de transcripción bajo un `### Transcripción` de su sección, que es lo que lee `tests/fixtures/bcv_cuadriculas.py::transcripcion`). `bcv_formatos.md` con la sección `## Formatos para \`adapters/bcv/formatos.json\`` y su tabla `| Clave | Valor (JSON) |`, una fila por clave con la clave y el valor JSON entre comillas invertidas (p. ej. ``| `tasa.trimestre_por_letra` | `{"a": 1, "b": 2, "c": 3, "d": 4}` |``, con las letras **verificadas** en el archivo real): `tasa.trimestre_por_letra`, `inpc.hoja`, `inpc.etiqueta_periodo`, `inpc.etiqueta_valor`, `inpc.marca_provisional`, `inpc.base`. La Tarea 6 genera `adapters/bcv/formatos.json` de esa tabla y lo compara.

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/unit/test_fuente_bcv.py
import hashlib
import re
from pathlib import Path

CARPETA = Path(__file__).resolve().parents[1] / "fixtures" / "bcv"


def _campos(seccion: str) -> dict[str, str]:
    texto = (CARPETA / "FUENTE.md").read_text(encoding="utf-8").split(f"## {seccion}")[1]
    texto = texto.split("\n## ")[0]
    return dict(re.findall(r"^\| ([^|]+?) \| ([^|]+?) \|$", texto, re.MULTILINE))


def test_la_tasa_declara_archivo_bcv_huella_y_64_hojas():
    campos = _campos("Tasa")
    archivo = CARPETA / campos["Archivo"]
    assert campos["Dirección"].startswith("https://www.bcv.org.ve/")
    assert hashlib.sha256(archivo.read_bytes()).hexdigest() == campos["SHA-256"]
    assert campos["Hojas (N)"] == "64"  # antecedentes §6: 3T‑2026, 01‑07 a 30‑09
    assert archivo.stat().st_size <= 20 * 1024 * 1024


def test_la_transcripcion_trae_el_literal_verificado():
    texto = (CARPETA / "FUENTE.md").read_text(encoding="utf-8")
    assert re.search(r"\| 2026-10-01 \| 858\.02 \| 860\.18 \|", texto)


def test_el_inpc_declara_archivo_y_huella():
    campos = _campos("INPC")
    assert hashlib.sha256((CARPETA / campos["Archivo"]).read_bytes()).hexdigest() == campos["SHA-256"]
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_fuente_bcv.py -v -W error`
Esperado: FAIL con `FileNotFoundError: ...tests/fixtures/bcv/FUENTE.md`
- [ ] **Paso 3: Descarga y transcripción a mano** (sin `xlrd`; con Excel o LibreOffice; antecedentes §6)
  1. Tasa: desde `https://www.bcv.org.ve/estadisticas/tipo-cambio-de-referencia-smc`, el enlace del 3.er trimestre de 2026; el archivo vive en `https://www.bcv.org.ve/sites/default/files/EstadisticasGeneral/2_1_2?26_smc.xls`. En Windows: `curl.exe -L -o tests/fixtures/bcv/<nombre> <dirección>` (el certificado del BCV tiene la cadena incompleta; `curl` en Windows entra). Registrar el nombre **real** (la letra del trimestre queda verificada aquí).
  2. INPC: desde `https://www.bcv.org.ve/estadisticas/consumidor`. **Ojo:** `4_5_1.xls` publica *variaciones* por grupos (antecedentes §6); la escalatoria necesita **niveles** del índice. Elegir el archivo de niveles del índice general (base declarada en el propio archivo) y anotar en `bcv_formatos.md` por qué ese y no `4_5_1.xls`.
  3. `FUENTE.md`: dirección, página, fecha de descarga, SHA‑256 (`Get-FileHash -Algorithm SHA256`), N de hojas contado a mano, y la transcripción de la primera hoja, la del medio (n.º 32) y la última, con su fecha valor y compra/venta del USD en Bs; la fila con fecha valor 2026‑10‑01 debe decir 858.02 / 860.18. Del INPC: primer mes, último y uno del medio, con «(*)» si es provisional. Valores con punto decimal. **No se escribe ningún valor que no se haya leído del archivo.**
  4. `bcv_formatos.md`: por archivo, nombres de hoja, ubicación de «Fecha Valor» (misma celda tras «:» o celda siguiente), fila del código `USD` y orden de las columnas Compra/Venta (Bs por moneda); para el INPC, hoja, encabezados de período y de índice general, forma del período (fecha o texto «Ene‑2026»), marca de provisional y base. Cierra con la tabla de claves para `formatos.json`.
  5. Paso 0.7 del spec: comprobar en una versión abierta de OF‑001 que la columna Estado de la pestaña Precios es **por insumo** mientras los `origen_ids` de R11/R12 serán **códigos de partida**; dejar escrito en `bcv_formatos.md` §«Estado de Precios» que la Tarea 10 cruza por `insumo_id` interno, no por `origen_ids`.
  6. Índice de insumos de la construcción (`https://www.bcv.org.ve/estadisticas/insumos-de-la-construccion`): abrirlo y anotar si su formato es legible; si no, queda el CSV canónico (S1 §7.3; orden de caída de §10).
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/unit/test_fuente_bcv.py -q -W error`; tras el commit del paso 5, `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml` y `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S1-0 --junit reporte-pruebas.xml` → todas las filas en OK. **Compuerta GS1‑0:** documentos y memorias aprobados por los cuatro encargos.
- [ ] **Paso 5: Commit**
```bash
git add tests/fixtures/bcv tests/unit/test_fuente_bcv.py docs/fuentes/bcv_formatos.md docs/bitacora/2026-10-silice-060.md
git commit -m "docs(fuentes): archivos reales del BCV con transcripcion a mano y formatos" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

# S1‑1 — SL‑E1 (rama solo‑núcleo `inc/060-s1-1-nucleo`)

### Tarea 4: SL‑E1a — tablas, revisión `caso_0002`, series de índices y tasa aplicable

**Rama:** `inc/060-s1-1-nucleo` (solo `core/`, `migraciones/`, `tests/`, `docs/`; sale de `main` con S5‑1 y S1‑0 fusionados)   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/models/moneda.py`, `migraciones/caso/versions/caso_0002_s1_moneda.py`, `core/catalog/indices.py`, `tests/integration/test_indices.py`, `tests/integration/test_migracion_s1.py`
- Crear también: `docs/bitacora/2026-10-silice-expedientes.md` (nace con SL‑E1; SL‑E2 y SL‑E3 lo continúan)
- Modificar: `core/models/__init__.py:7-75` (reexportar)

**Interfaces:**
- Consume (sección B): `operacion.base_datos.preparar_base(ruta, destino=Destino.CASO, *, entorno=None)`, `leer_estado`, `revision_head`, `Destino`; `tests.fixtures.bases_prueba.copiar_base(version, nombre, destino)`, `ficha(version)`, `nombres(version)`, `diferencias_con_ficha(ruta, esperado)`; revisión base `caso_0001_base_0_5_0`.
- Produce: `models.SerieIndice`, `models.ImportacionIndice`, `models.ValorIndice`, `models.MonedaProyecto`, `models.PrecioOrigen`; `core.catalog.indices`: `PERIODICIDADES`, `SERIE_USD_COMPRA = "BCV-USD-COMPRA"`, `SERIE_USD_VENTA = "BCV-USD-VENTA"`, `LADO_POR_DEFECTO = "venta"`, `DIAS_MAXIMOS_SIN_TASA = 7`, `UNIDAD_TASA = "Bs/USD"`, `UNIDAD_INDICE_BS = "indice_bs"`, `TasaNoDisponible(ValueError)`, `DefinicionSerie`, `Observacion`, `ValorFechado(serie, fecha, valor, provisional, importacion_id)` con `.fuente -> "importacion:<id>"`, `definicion_tasa(lado) -> DefinicionSerie`, `registrar_importacion(session, definicion, observaciones, *, archivo, huella, fuente, fecha_descarga, responsable, filas_leidas, filas_rechazadas, informe="", ahora=None) -> models.ImportacionIndice | None`, `valor_en(session, codigo, fecha, *, importacion_id=None) -> ValorFechado | None`, `tasa_aplicable(session, fecha, *, lado=LADO_POR_DEFECTO) -> ValorFechado`.

- [ ] **Paso 0: Expediente SL‑E1** en `docs/bitacora/2026-10-silice-expedientes.md` (método de C5/C6): *regla que lo motiva* H‑D1, RF‑64…66 (hoy un precio no dice su fecha ni su moneda original y nada impide mezclar monedas, S1 §1.1); *por qué es genérico* (todo presupuesto tiene moneda y todo precio una fecha, en cualquier dominio); *diseño* (cinco tablas aditivas de S1 §5.2 en `core/models/moneda.py` con su revisión `caso_0002`; `indices.py`, `moneda.py`, `budget/moneda.py`; `guardar_presupuesto` rechaza monedas mezcladas; `MOTIVOS_VERSION` + `conversion`; `OBJETOS` + `moneda`); *prueba* (memoria de conversión, homogeneidad del total convertido, rechazo de monedas mezcladas, base 0.5.0 sube a `head`); *impacto*; *costo si es erróneo* (S1 §11). Commit `docs(bitacora): expediente SL-E1`.
- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/integration/test_indices.py
"""SL‑E1: series, importaciones idempotentes y tasa aplicable (S1 §5.3, S1‑R1, S1‑R2)."""
from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import func, select

from core import models
from core.catalog.indices import (
    Observacion,
    TasaNoDisponible,
    definicion_tasa,
    registrar_importacion,
    tasa_aplicable,
    valor_en,
)

HUELLA = "a" * 64
FUENTE = "https://www.bcv.org.ve/estadisticas/tipo-cambio-de-referencia-smc"


def _importar(sesion, lado, observaciones, huella=HUELLA):
    return registrar_importacion(
        sesion, definicion_tasa(lado), observaciones, archivo="2_1_2c26_smc.xls", huella=huella,
        fuente=FUENTE, fecha_descarga=date(2026, 10, 8), responsable="Admin",
        filas_leidas=len(observaciones), filas_rechazadas=0,
    )


@pytest.fixture
def con_tasas(sesion):
    # 01/10/2026 (jueves): literal verificado (antecedentes §6). 02/10 (viernes): 862,00 FICTICIO.
    _importar(sesion, "compra", [Observacion(date(2026, 10, 1), D("858.02"))])
    _importar(sesion, "venta", [Observacion(date(2026, 10, 1), D("860.18")),
                                Observacion(date(2026, 10, 2), D("862.00"))])
    return sesion


def test_el_sabado_toma_la_tasa_del_viernes_y_cada_lado_la_suya(con_tasas):
    assert tasa_aplicable(con_tasas, date(2026, 10, 3)).valor == D("862.00")
    assert tasa_aplicable(con_tasas, date(2026, 10, 1), lado="compra").valor == D("858.02")
    assert tasa_aplicable(con_tasas, date(2026, 10, 1)).fecha == date(2026, 10, 1)


def test_siete_dias_naturales_pasan_y_ocho_se_rechazan(con_tasas):
    assert tasa_aplicable(con_tasas, date(2026, 10, 9)).fecha == date(2026, 10, 2)
    with pytest.raises(TasaNoDisponible, match="8 dias"):
        tasa_aplicable(con_tasas, date(2026, 10, 10))
    with pytest.raises(TasaNoDisponible, match="no hay tasa"):
        tasa_aplicable(con_tasas, date(2026, 9, 30))


def test_la_misma_huella_no_escribe_nada(con_tasas):
    antes = con_tasas.scalar(select(func.count()).select_from(models.ValorIndice))
    assert _importar(con_tasas, "venta", [Observacion(date(2026, 10, 5), D("1"))]) is None
    assert con_tasas.scalar(select(func.count()).select_from(models.ValorIndice)) == antes


def test_una_revision_es_otra_importacion_y_la_citada_sigue_valiendo(con_tasas):
    primera = valor_en(con_tasas, "BCV-USD-VENTA", date(2026, 10, 1))
    _importar(con_tasas, "venta", [Observacion(date(2026, 10, 1), D("860.50"))], huella="b" * 64)
    assert valor_en(con_tasas, "BCV-USD-VENTA", date(2026, 10, 1)).valor == D("860.50")
    citada = valor_en(con_tasas, "BCV-USD-VENTA", date(2026, 10, 1),
                      importacion_id=primera.importacion_id)
    assert citada.valor == D("860.18")


def test_sin_fuente_sin_responsable_fecha_repetida_o_valor_no_positivo_se_rechaza(sesion):
    with pytest.raises(ValueError, match="fuente"):
        registrar_importacion(sesion, definicion_tasa("venta"), [], archivo="x", huella=HUELLA,
                              fuente=" ", fecha_descarga=date(2026, 10, 8), responsable="A",
                              filas_leidas=0, filas_rechazadas=0)
    with pytest.raises(ValueError, match="repetida"):
        _importar(sesion, "venta", [Observacion(date(2026, 10, 1), D("1")),
                                    Observacion(date(2026, 10, 1), D("2"))])
    with pytest.raises(ValueError, match="mayor que cero"):
        Observacion(date(2026, 10, 1), D("0"))
```
```python
# tests/integration/test_migracion_s1.py
"""Bases anteriores (S1 §9.2): cada base de prueba de la 0.5.0 sube a head por `preparar_base`,
gana las tablas de S1-1 y conserva filas, total y huella del informe de su ficha
(seccion B, RV-3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from tests.fixtures.bases_prueba import copiar_base, diferencias_con_ficha, ficha, nombres

TABLAS_S1_1 = {"serie_indice", "importacion_indice", "valor_indice", "moneda_proyecto",
               "precio_origen"}


@pytest.mark.parametrize("nombre", nombres("0.5.0"))
def test_la_base_0_5_0_gana_las_tablas_de_s1_1_sin_perder_filas(tmp_path: Path, nombre: str):
    ruta = copiar_base("0.5.0", nombre, tmp_path / nombre)
    preparar_base(ruta)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        assert TABLAS_S1_1 <= set(inspect(motor).get_table_names())
    finally:
        motor.dispose()
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert diferencias_con_ficha(ruta, ficha("0.5.0")["bases"][nombre]) == []
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/integration/test_indices.py tests/integration/test_migracion_s1.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.catalog.indices'` y, en las tres bases, `AssertionError` en el conjunto de tablas.
- [ ] **Paso 3: Implementación mínima**
```python
# core/models/moneda.py
"""Tablas aditivas de Sílice S1 (spec S1 §5.2). Módulo propio para no tocar `entidades.py` (M §3.2);
cada fase de núcleo agrega aquí las suyas con su revisión en `migraciones/caso/`. Ninguna altera
una tabla existente (ruling SF3‑E0)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base
from core.models.tipos import DecimalExacto


class SerieIndice(Base):
    """SL‑E1: una serie (tasa compra/venta, INPC, insumos de la construcción)."""

    __tablename__ = "serie_indice"
    __table_args__ = (UniqueConstraint("codigo", name="uq_serie_indice_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40))
    nombre: Mapped[str] = mapped_column(String(200))
    organismo: Mapped[str] = mapped_column(String(120))
    unidad: Mapped[str] = mapped_column(String(40))
    periodicidad: Mapped[str] = mapped_column(String(12))
    base: Mapped[str] = mapped_column(String(200), default="")


class ImportacionIndice(Base):
    """SL‑E1: un archivo importado para una serie, con su huella SHA‑256 y su fuente."""

    __tablename__ = "importacion_indice"
    __table_args__ = (Index("ix_importacion_indice_serie_huella", "serie_id", "huella"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serie_id: Mapped[int] = mapped_column(ForeignKey("serie_indice.id"))
    archivo: Mapped[str] = mapped_column(String(255))
    huella: Mapped[str] = mapped_column(String(64))
    fuente: Mapped[str] = mapped_column(String(500))
    fecha_descarga: Mapped[date] = mapped_column(Date)
    fecha_importacion: Mapped[datetime] = mapped_column(DateTime)
    responsable: Mapped[str] = mapped_column(String(120))
    filas_leidas: Mapped[int] = mapped_column(Integer)
    filas_rechazadas: Mapped[int] = mapped_column(Integer)
    informe: Mapped[str] = mapped_column(Text, default="")


class ValorIndice(Base):
    """SL‑E1: valor de una serie en una fecha (fecha valor o primer día del período)."""

    __tablename__ = "valor_indice"
    __table_args__ = (
        UniqueConstraint("serie_id", "fecha", "importacion_id", name="uq_valor_indice"),
        Index("ix_valor_indice_serie_fecha", "serie_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serie_id: Mapped[int] = mapped_column(ForeignKey("serie_indice.id"))
    importacion_id: Mapped[int] = mapped_column(
        ForeignKey("importacion_indice.id", ondelete="CASCADE")
    )
    fecha: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(DecimalExacto)
    provisional: Mapped[bool] = mapped_column(Boolean, default=False)


class MonedaProyecto(Base):
    """SL‑E1: historial de la moneda de un proyecto; la vigente es la última."""

    __tablename__ = "moneda_proyecto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    moneda: Mapped[str] = mapped_column(String(10))
    desde: Mapped[datetime] = mapped_column(DateTime)
    version_id: Mapped[int | None] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="SET NULL"), default=None
    )
    responsable: Mapped[str] = mapped_column(String(120))
    fuente: Mapped[str] = mapped_column(String(300))


class PrecioOrigen(Base):
    """SL‑E1: origen de un precio (S1 §5.1). Sin fila, manda la lista (regla única de precedencia)."""

    __tablename__ = "precio_origen"

    precio_id: Mapped[int] = mapped_column(
        ForeignKey("precio_insumo.id", ondelete="CASCADE"), primary_key=True
    )
    moneda_original: Mapped[str] = mapped_column(String(10))
    precio_original: Mapped[Decimal] = mapped_column(DecimalExacto)
    fecha_precio: Mapped[date] = mapped_column(Date)
    tasa: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    fecha_tasa: Mapped[date | None] = mapped_column(Date, default=None)
    fuente_tasa: Mapped[str] = mapped_column(String(300), default="")
    fuente: Mapped[str] = mapped_column(String(300), default="")
```
```python
# migraciones/caso/versions/caso_0002_s1_moneda.py
"""S1‑1 (SL‑E1): series, importaciones, valores, moneda del proyecto y origen por precio."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0002_s1_moneda"
down_revision = "caso_0001_base_0_5_0"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def upgrade() -> None:
    op.create_table(
        "serie_indice",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("codigo", sa.String(40), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("organismo", sa.String(120), nullable=False),
        sa.Column("unidad", sa.String(40), nullable=False),
        sa.Column("periodicidad", sa.String(12), nullable=False),
        sa.Column("base", sa.String(200), nullable=False),
        sa.UniqueConstraint("codigo", name="uq_serie_indice_codigo"),
    )
    op.create_table(
        "importacion_indice",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("serie_id", sa.Integer, sa.ForeignKey("serie_indice.id"), nullable=False),
        sa.Column("archivo", sa.String(255), nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("fuente", sa.String(500), nullable=False),
        sa.Column("fecha_descarga", sa.Date, nullable=False),
        sa.Column("fecha_importacion", sa.DateTime, nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("filas_leidas", sa.Integer, nullable=False),
        sa.Column("filas_rechazadas", sa.Integer, nullable=False),
        sa.Column("informe", sa.Text, nullable=False),
    )
    op.create_index("ix_importacion_indice_serie_huella", "importacion_indice",
                    ["serie_id", "huella"])
    op.create_table(
        "valor_indice",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("serie_id", sa.Integer, sa.ForeignKey("serie_indice.id"), nullable=False),
        sa.Column("importacion_id", sa.Integer,
                  sa.ForeignKey("importacion_indice.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("valor", DEC, nullable=False),
        sa.Column("provisional", sa.Boolean, nullable=False),
        sa.UniqueConstraint("serie_id", "fecha", "importacion_id", name="uq_valor_indice"),
    )
    op.create_index("ix_valor_indice_serie_fecha", "valor_indice", ["serie_id", "fecha"])
    op.create_table(
        "moneda_proyecto",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("proyecto_id", sa.Integer, sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("moneda", sa.String(10), nullable=False),
        sa.Column("desde", sa.DateTime, nullable=False),
        sa.Column("version_id", sa.Integer,
                  sa.ForeignKey("presupuesto.id", ondelete="SET NULL"), nullable=True),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
    )
    op.create_table(
        "precio_origen",
        sa.Column("precio_id", sa.Integer,
                  sa.ForeignKey("precio_insumo.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("moneda_original", sa.String(10), nullable=False),
        sa.Column("precio_original", DEC, nullable=False),
        sa.Column("fecha_precio", sa.Date, nullable=False),
        sa.Column("tasa", DEC, nullable=True),
        sa.Column("fecha_tasa", sa.Date, nullable=True),
        sa.Column("fuente_tasa", sa.String(300), nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
    )


def downgrade() -> None:
    for tabla in ("precio_origen", "moneda_proyecto", "valor_indice", "importacion_indice",
                  "serie_indice"):
        op.drop_table(tabla)
```
```python
# core/catalog/indices.py
"""SL‑E1: series de índices y tasa aplicable (spec S1 §5.3). Recibe definiciones y observaciones ya
validadas (las arma `ui.indices` con lo que entrega `adapters.bcv`); no conoce formatos de archivo.
Sin red (RNF‑14). No hace `commit`."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models

PERIODICIDADES = ("diaria", "mensual", "trimestral", "anual")
SERIE_USD_COMPRA = "BCV-USD-COMPRA"
SERIE_USD_VENTA = "BCV-USD-VENTA"
SERIES_DE_TASA = {"compra": SERIE_USD_COMPRA, "venta": SERIE_USD_VENTA}
LADO_POR_DEFECTO = "venta"  # S1‑R1, SUPUESTO_DECLARADO
DIAS_MAXIMOS_SIN_TASA = 7  # S1‑R2
UNIDAD_TASA = "Bs/USD"
UNIDAD_INDICE_BS = "indice_bs"


class TasaNoDisponible(ValueError):
    """No hay tasa a esa fecha, o la más cercana tiene más de 7 días naturales."""


@dataclass(frozen=True, slots=True)
class DefinicionSerie:
    codigo: str
    nombre: str
    organismo: str
    unidad: str
    periodicidad: str
    base: str = ""

    def __post_init__(self) -> None:
        if not self.codigo.strip():
            raise ValueError("el codigo de la serie no puede estar vacio")
        if self.periodicidad not in PERIODICIDADES:
            raise ValueError(f"periodicidad {self.periodicidad!r}; se espera una de {PERIODICIDADES}")


@dataclass(frozen=True, slots=True)
class Observacion:
    fecha: date
    valor: Decimal
    provisional: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.valor, Decimal) or not self.valor.is_finite() or self.valor <= 0:
            raise ValueError(f"el valor del {self.fecha} debe ser un Decimal mayor que cero")


@dataclass(frozen=True, slots=True)
class ValorFechado:
    serie: str
    fecha: date
    valor: Decimal
    provisional: bool
    importacion_id: int

    @property
    def fuente(self) -> str:
        return f"importacion:{self.importacion_id}"


def definicion_tasa(lado: str) -> DefinicionSerie:
    if lado not in SERIES_DE_TASA:
        raise ValueError(f"lado {lado!r}; se espera compra o venta")
    return DefinicionSerie(SERIES_DE_TASA[lado], f"Tasa de referencia USD ({lado})", "BCV",
                           UNIDAD_TASA, "diaria")


def _serie(session: Session, definicion: DefinicionSerie) -> models.SerieIndice:
    serie = session.scalars(
        select(models.SerieIndice).where(models.SerieIndice.codigo == definicion.codigo)
    ).one_or_none()
    if serie is None:
        serie = models.SerieIndice(codigo=definicion.codigo, nombre=definicion.nombre,
                                   organismo=definicion.organismo, unidad=definicion.unidad,
                                   periodicidad=definicion.periodicidad, base=definicion.base)
        session.add(serie)
        session.flush()
    elif (serie.unidad, serie.periodicidad) != (definicion.unidad, definicion.periodicidad):
        raise ValueError(f"la serie {definicion.codigo} ya existe con otra unidad o periodicidad")
    return serie


def registrar_importacion(
    session: Session,
    definicion: DefinicionSerie,
    observaciones: Sequence[Observacion],
    *,
    archivo: str,
    huella: str,
    fuente: str,
    fecha_descarga: date,
    responsable: str,
    filas_leidas: int,
    filas_rechazadas: int,
    informe: str = "",
    ahora: datetime | None = None,
) -> models.ImportacionIndice | None:
    """Guarda una importación nueva; `None` si la serie ya tiene esa huella (UC‑17 2c). Una
    revisión de valores es otra importación (2d): nunca se sobrescribe un valor guardado."""
    fuente, responsable = fuente.strip(), responsable.strip()
    if not fuente:
        raise ValueError("la fuente de la importacion es obligatoria (UC-17 paso 1)")
    if not responsable:
        raise ValueError("el responsable de la importacion es obligatorio")
    if len(huella) != 64:
        raise ValueError("la huella debe ser un SHA-256 en hexadecimal (64 caracteres)")
    repetidas = sorted(f for f, n in Counter(o.fecha for o in observaciones).items() if n > 1)
    if repetidas:
        raise ValueError("fecha repetida en la importacion: " + ", ".join(map(str, repetidas)))
    serie = _serie(session, definicion)
    ya = session.scalar(select(models.ImportacionIndice.id).where(
        models.ImportacionIndice.serie_id == serie.id, models.ImportacionIndice.huella == huella))
    if ya is not None:
        return None
    importacion = models.ImportacionIndice(
        serie_id=serie.id, archivo=archivo, huella=huella, fuente=fuente,
        fecha_descarga=fecha_descarga, fecha_importacion=ahora or datetime.now(),
        responsable=responsable, filas_leidas=filas_leidas, filas_rechazadas=filas_rechazadas,
        informe=informe)
    session.add(importacion)
    session.flush()
    session.add_all(
        models.ValorIndice(serie_id=serie.id, importacion_id=importacion.id, fecha=o.fecha,
                           valor=o.valor, provisional=o.provisional)
        for o in observaciones
    )
    session.flush()
    return importacion


def _consulta(codigo: str):
    return (select(models.ValorIndice, models.SerieIndice.codigo)
            .join(models.SerieIndice)
            .where(models.SerieIndice.codigo == codigo))


def _fechado(fila: models.ValorIndice, codigo: str) -> ValorFechado:
    return ValorFechado(codigo, fila.fecha, fila.valor, fila.provisional, fila.importacion_id)


def valor_en(
    session: Session, codigo: str, fecha: date, *, importacion_id: int | None = None
) -> ValorFechado | None:
    """El valor exacto de esa fecha: el de la importación citada o, sin cita, el de la más reciente."""
    consulta = _consulta(codigo).where(models.ValorIndice.fecha == fecha)
    if importacion_id is not None:
        consulta = consulta.where(models.ValorIndice.importacion_id == importacion_id)
    fila = session.execute(
        consulta.order_by(models.ValorIndice.importacion_id.desc()).limit(1)).first()
    return None if fila is None else _fechado(fila[0], codigo)


def tasa_aplicable(session: Session, fecha: date, *, lado: str = LADO_POR_DEFECTO) -> ValorFechado:
    """La de mayor fecha valor ≤ `fecha` (S1‑R1); más de 7 días naturales se rechaza (S1‑R2)."""
    codigo = definicion_tasa(lado).codigo
    fila = session.execute(
        _consulta(codigo).where(models.ValorIndice.fecha <= fecha)
        .order_by(models.ValorIndice.fecha.desc(), models.ValorIndice.importacion_id.desc())
        .limit(1)).first()
    if fila is None:
        raise TasaNoDisponible(
            f"no hay tasa {lado} del BCV importada al {fecha:%d/%m/%Y} o antes: importe el "
            "archivo trimestral (UC-17)")
    dias = (fecha - fila[0].fecha).days
    if dias > DIAS_MAXIMOS_SIN_TASA:
        raise TasaNoDisponible(
            f"la tasa {lado} mas reciente es del {fila[0].fecha:%d/%m/%Y}, {dias} dias antes del "
            f"{fecha:%d/%m/%Y}: con mas de 7 dias naturales sin tasa no se convierte (S1-R2)")
    return _fechado(fila[0], codigo)
```
  En `core/models/__init__.py`, tras la importación de `core.models.entidades`:
```python
from core.models.moneda import (
    ImportacionIndice,
    MonedaProyecto,
    PrecioOrigen,
    SerieIndice,
    ValorIndice,
)
```
  y en `__all__`, en orden alfabético: `"ImportacionIndice"`, `"MonedaProyecto"`, `"PrecioOrigen"`, `"SerieIndice"`, `"ValorIndice"`.
  **Cómo nace la revisión** (regla de B, manual técnico §10.5, y plantilla `migraciones/caso/script.py.mako` de B, Tarea 1): el archivo se escribe a mano en `migraciones/caso/versions/` con nombre igual a su `revision` (`caso_<NNNN>_<tema>.py`); `down_revision` es la `head` del destino antes de crearla, que da `uv run python -c "from operacion.base_datos import Destino, revision_head; print(revision_head(Destino.CASO))"` (aquí `caso_0001_base_0_5_0`; en la Tarea 7, `caso_0002_s1_moneda`; en la Tarea 12, `caso_0003_s1_lista_empresa`); tablas nuevas con `op.create_table`, nunca `stamp`, y un `downgrade()` real. La comprueban sin cambios las pruebas de B en `tests/integration/test_migraciones.py` (head = `create_all`, autogeneración vacía, cada revisión baja y vuelve a subir).
- [ ] **Paso 4: Correrla y ver el verde** (y la suite): `uv run pytest tests/integration/test_indices.py tests/integration/test_migracion_s1.py -q -W error`; la prueba de deriva de la sección B (RNF‑20) en verde; `uv run pytest -q -W error`; `uv run ruff check core/models core/catalog/indices.py migraciones tests/integration/test_indices.py tests/integration/test_migracion_s1.py`.
- [ ] **Paso 5: Commit** (prueba primero, luego código)
```bash
git add tests/integration/test_indices.py tests/integration/test_migracion_s1.py
git commit -m "test(core): SL-E1 indices, tasa aplicable y base 0.5.0 en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add core/models/moneda.py core/models/__init__.py core/catalog/indices.py migraciones/caso/versions/caso_0002_s1_moneda.py
git commit -m "feat(core): SL-E1 tablas de moneda e indices con su revision de Alembic" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Tarea 5: SL‑E1b — conversión, erosión, origen por precio y `convertir_version`

**Rama:** `inc/060-s1-1-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/catalog/moneda.py`, `core/budget/moneda.py`, `tests/unit/test_moneda.py`, `tests/integration/test_conversion_version.py`
- Modificar: `core/models/entidades.py:505` (`MOTIVOS_VERSION` + `"conversion"`), `core/budget/edicion.py:58` (`OBJETOS` + `"moneda"`), `core/budget/persistencia.py:144-153` (rechazos de moneda) y nueva `moneda_declarada`, `core/budget/actualizacion.py:174-187` (rechazo temprano), `core/budget/instantanea.py:164-197` (`precio_sin_insumo`), `core/catalog/origen.py:54-75,144-223,226-302` (`OrigenEfectivo`, `origenes_efectivos`, campos nuevos de `OrigenPrecio`, copia de `PrecioOrigen` en `crear_lista_de_proyecto`), `core/budget/__init__.py` (exportar)

**Interfaces:**
- Consume: Tarea 4.
- Produce: `core.catalog.moneda`: `MONEDAS = ("Bs", "USD")`, `exigir_moneda(m) -> str`, `convertir(monto, de, a, tasa) -> Decimal`, `TasaDeclarada(valor, fecha, fuente)` con `TasaDeclarada.de_importacion(v: ValorFechado)`, `Erosion(usd, bs, porcentaje, nota)`, `erosion(precio, moneda, tasa_precio, tasa_evaluacion) -> Erosion`, `erosion_por_indice(precio, indice_precio, indice_evaluacion) -> Decimal`, `copiar_precios(session, de, a_lista, tasa: TasaDeclarada | None, *, excluir=frozenset()) -> None`, `convertir_lista(session, lista, a, tasa, *, nombre, proyecto=None) -> models.ListaPrecios`. `core.catalog.origen`: `OrigenEfectivo(moneda_original, precio_original, fecha_precio, tasa, fecha_tasa, fuente_tasa, fuente)`, `origenes_efectivos(session, lista) -> dict[int, OrigenEfectivo]` (por `precio_id`); `OrigenPrecio` gana al final `moneda_original: str = ""`, `precio_original: Decimal | None = None`, `fecha_precio: date | None = None`, `fuente_tasa: str = ""`, `fuente: str = ""`. `core.budget.persistencia.moneda_declarada(session, proyecto_id) -> str | None`. `core.budget.moneda`: `moneda_del_proyecto(session, proyecto) -> str`, `declarar_moneda(session, proyecto, moneda, *, responsable, fuente, ahora=None) -> models.MonedaProyecto`, `convertir_version(session, proyecto_nombre, codigo, codigo_nuevo, moneda, tasa: TasaDeclarada, *, fuente, responsable, catalogo, reglas=REGLAS, ahora=None) -> models.Presupuesto`.

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/unit/test_moneda.py
"""Oráculo: tests/fixtures/memorias/s1_conversion.md (S1 §9.1.1)."""
from datetime import date
from decimal import Decimal as D, localcontext

import pytest

from core.catalog.moneda import TasaDeclarada, convertir, erosion, erosion_por_indice

T0, T1 = D("633.3644"), D("860.18")


def test_memoria_de_conversion_con_28_digitos():
    with localcontext(prec=6):  # el resultado no depende del contexto global
        e = erosion(D("1000"), "Bs", T0, T1)
        assert convertir(D("1000"), "Bs", "USD", T0) == D("1.578869920696521623255111907")
        assert convertir(D("1000"), "Bs", "USD", T1) == D("1.162547373805482573414866656")
    assert e.usd == D("0.416322546891039049840245251")
    assert e.bs == D("358.112328384733969891582160")
    assert e.porcentaje.quantize(D("0.0001")) == D("0.2637")
    assert e.porcentaje.quantize(D("0.0001")) != D("0.3581")  # no es 358,11 / 1 000


def test_usd_erosion_cero_declarada_y_misma_moneda_no_convierte():
    e = erosion(D("30"), "USD", T0, T1)
    assert (e.usd, e.bs) == (D(0), D(0)) and "USD" in e.nota
    assert convertir(D("7.5"), "USD", "USD", T1) == D("7.5")
    assert convertir(D("1"), "USD", "Bs", T1) == T1


def test_erosion_por_indice_es_columna_aparte():
    assert erosion_por_indice(D("1000"), D("200"), D("230")) == D("150")


@pytest.mark.parametrize("valor, fuente", [(D("0"), "importacion:1"), (D("860.18"), " ")])
def test_sin_tasa_o_sin_fuente_se_rechaza(valor, fuente):
    with pytest.raises(ValueError):
        TasaDeclarada(valor, date(2026, 10, 1), fuente)
```
```python
# tests/integration/test_conversion_version.py
"""RF‑64, RF‑65 (S1 §9.2). Oráculo independiente: homogeneidad del PU (total × T)."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import func, select

from core import models
from core.budget import actualizar_precios, cargar_presupuesto, plan_de_version, restaurar_version
from core.budget.moneda import convertir_version, moneda_del_proyecto
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.catalog.moneda import TasaDeclarada
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.base_con_pendiente import url_sqlite
from tests.fixtures.hoja_en_base import NOMBRE_TI001, plantilla_ti001
from tests.fixtures.versiones import elaborar_001, guardar_001

TASA = TasaDeclarada(D("860.18"), date(2026, 10, 1), "importacion:1")
CENT = D("0.01")


@pytest.fixture
def clinica(sesion):
    proyecto = sesion.scalars(select(models.Proyecto)).one()
    guardar_001(sesion, proyecto, elaborar_001(sesion))
    sesion.flush()
    return sesion, proyecto.nombre


def _convertir(sesion, nombre, codigo="001", nuevo="002", moneda="Bs", tasa=TASA):
    return convertir_version(sesion, nombre, codigo, nuevo, moneda, tasa, fuente="cambio pedido",
                             responsable="Ing. Prueba", catalogo=Catalogo(sesion))


def _total(sesion, nombre, codigo):
    return cargar_presupuesto(sesion, nombre, codigo, Catalogo(sesion)).total


def test_la_clinica_en_bs_es_el_total_por_la_tasa_y_el_origen_no_cambia(clinica):
    sesion, nombre = clinica
    antes = cargar_presupuesto(sesion, nombre, "001", Catalogo(sesion))
    nueva = _convertir(sesion, nombre)
    assert (_total(sesion, nombre, "002") - antes.total * TASA.valor).copy_abs() <= CENT
    assert nueva.moneda == "Bs" and nueva.bono_alimentacion == D("860.18")
    assert nueva.lista_precios.moneda == "Bs"
    assert plan_de_version(sesion, nueva) == plan_de_version(
        sesion, sesion.scalars(select(models.Presupuesto).where(models.Presupuesto.codigo == "001")).one())
    assert not [h for h in nueva.hallazgos if h.regla == "R2"]
    assert cargar_presupuesto(sesion, nombre, "001", Catalogo(sesion)) == antes


def test_registra_moneda_del_proyecto_y_registro_de_cambio(clinica):
    sesion, nombre = clinica
    nueva = _convertir(sesion, nombre)
    registro = sesion.scalars(select(models.RegistroCambio).where(
        models.RegistroCambio.version_resultante_id == nueva.id)).one()
    assert (registro.objeto, registro.valor_anterior, registro.valor_nuevo, registro.fuente) == (
        "moneda", "USD", "Bs", "importacion:1")
    assert moneda_del_proyecto(sesion, nueva.proyecto) == "Bs"
    assert sesion.get(models.VersionOrigen, nueva.id).motivo == "conversion"


def test_ida_y_vuelta_y_ti001(clinica, tmp_path):
    sesion, nombre = clinica
    original = _total(sesion, nombre, "001")
    _convertir(sesion, nombre)
    _convertir(sesion, nombre, "002", "003", "USD")
    assert (_total(sesion, nombre, "003") - original).copy_abs() <= CENT
    motor = crear_motor(url_sqlite(plantilla_ti001(tmp_path / "ti.db")))
    try:
        with abrir_sesion(motor) as otra:
            antes = _total(otra, NOMBRE_TI001, "001")
            _convertir(otra, NOMBRE_TI001, "001", "TI-002")
            assert (_total(otra, NOMBRE_TI001, "TI-002") - antes * TASA.valor).copy_abs() <= CENT
    finally:
        motor.dispose()


def test_lista_de_otra_moneda_se_rechaza_al_guardar_y_al_revalorar(clinica):
    sesion, nombre = clinica
    lista_bs = models.ListaPrecios(nombre="Bs", moneda="Bs", fecha_vigencia=date(2026, 5, 1))
    sesion.add(lista_bs)
    sesion.flush()
    with pytest.raises(ValueError, match="RF-65"):
        guardar_001(sesion, sesion.scalars(select(models.Proyecto)).one(),
                    replace(elaborar_001(sesion, codigo="009")), lista=lista_bs)
    antes = sesion.scalar(select(func.count()).select_from(models.CambioPrecio))
    with pytest.raises(ValueError, match="RF-65"):
        actualizar_precios(sesion, nombre, "001", lista_bs, "010")
    assert sesion.scalar(select(func.count()).select_from(models.CambioPrecio)) == antes


def test_moneda_cambiada_con_versiones_previas_no_se_restauran_en_la_vieja(clinica):
    """[Foco 3] tras convertir a Bs, restaurar o revalorar la 001 en USD se rechaza."""
    sesion, nombre = clinica
    _convertir(sesion, nombre)
    with pytest.raises(ValueError, match="convierta"):
        restaurar_version(sesion, nombre, "001", "004", Catalogo(sesion), fuente="x",
                          responsable="y")


def test_tasa_incompleta_se_rechaza_sin_escribir(clinica):
    sesion, nombre = clinica
    with pytest.raises(ValueError):
        _convertir(sesion, nombre, tasa=replace(TASA, fuente=""))
    assert sesion.scalar(select(func.count()).select_from(models.MonedaProyecto)) == 0
```
  `tests/fixtures/versiones.py:50-60` hoy pasa `lista=` fijo (la vigente) y un `lista=` en `**opciones` chocaría (`TypeError: got multiple values for keyword argument 'lista'`). En este mismo commit de prueba, `guardar_001` pasa a:
```python
def guardar_001(sesion, proyecto, resultado: ResultadoElaboracion, *, lista=None, **opciones):
    return guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=lista or Catalogo(sesion).lista_vigente(linea_base.FECHA_LINEA_BASE),
        parametros=linea_base.PARAMETROS_LINEA_BASE,
        pendientes=resultado.pendientes,
        **opciones,
    )
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_moneda.py tests/integration/test_conversion_version.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.catalog.moneda'`
- [ ] **Paso 3: Implementación mínima**
```python
# core/catalog/moneda.py
"""SL‑E1: monedas, conversión con tasa fechada y erosión (spec S1 §5.3). Toda división con 28 dígitos
y ROUND_HALF_EVEN fijados dentro de la función. No hace `commit`."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.catalog.indices import ValorFechado
from core.catalog.origen import origenes_efectivos

MONEDAS = ("Bs", "USD")  # S1‑R15
_CERO = Decimal(0)


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


def exigir_moneda(moneda: str) -> str:
    if moneda not in MONEDAS:
        raise ValueError(f"moneda {moneda!r}; se espera Bs o USD (UC-17 4b)")
    return moneda


@dataclass(frozen=True, slots=True)
class TasaDeclarada:
    """Tasa Bs por USD con su fecha y su fuente (importación o texto). Las tres obligatorias."""

    valor: Decimal
    fecha: date
    fuente: str

    def __post_init__(self) -> None:
        if not isinstance(self.valor, Decimal) or not self.valor.is_finite() or self.valor <= 0:
            raise ValueError("la tasa debe ser un Decimal mayor que cero")
        if not isinstance(self.fecha, date):
            raise ValueError("la tasa debe declarar su fecha")
        if not self.fuente.strip():
            raise ValueError("la tasa debe declarar su fuente")

    @classmethod
    def de_importacion(cls, valor: ValorFechado) -> TasaDeclarada:
        return cls(valor.valor, valor.fecha, valor.fuente)


def convertir(monto: Decimal, de: str, a: str, tasa: Decimal) -> Decimal:
    exigir_moneda(de), exigir_moneda(a)
    with _contexto():
        if de == a:
            return monto
        return monto / tasa if de == "Bs" else monto * tasa


@dataclass(frozen=True, slots=True)
class Erosion:
    usd: Decimal
    bs: Decimal
    porcentaje: Decimal
    nota: str = ""


def erosion(precio: Decimal, moneda: str, tasa_precio: Decimal, tasa_evaluacion: Decimal) -> Erosion:
    if exigir_moneda(moneda) == "USD":
        return Erosion(_CERO, _CERO, _CERO,
                       "precio en USD: no hay indice de inflacion en USD en el alcance (declarado)")
    with _contexto():
        return Erosion(precio / tasa_precio - precio / tasa_evaluacion,
                       precio * tasa_evaluacion / tasa_precio - precio,
                       1 - tasa_precio / tasa_evaluacion)


def erosion_por_indice(precio: Decimal, indice_precio: Decimal, indice_evaluacion: Decimal) -> Decimal:
    with _contexto():
        return precio * (indice_evaluacion / indice_precio - 1)


def copiar_precios(
    session: Session,
    de: models.ListaPrecios,
    a_lista: models.ListaPrecios,
    tasa: TasaDeclarada | None,
    *,
    excluir: Collection[int] = frozenset(),
) -> None:
    """Copia a `a_lista` cada precio de `de` (salvo los insumos de `excluir`), convertido con `tasa`
    si las monedas difieren, con su referencia y su origen efectivo (moneda y precio originales se
    conservan; la tasa pasa a ser la de esta conversión). Hace `flush`."""
    if de.moneda != a_lista.moneda and tasa is None:
        raise ValueError(f"la lista {de.nombre!r} esta en {de.moneda}: hace falta una tasa")
    origenes = origenes_efectivos(session, de)
    referencias = dict(session.execute(
        select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
        .join(models.PrecioInsumo, models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id)
        .where(models.PrecioInsumo.lista_id == de.id)).all())
    pares = []
    for precio in de.precios:
        if precio.insumo_id in excluir:
            continue
        valor = precio.precio if tasa is None else convertir(precio.precio, de.moneda,
                                                              a_lista.moneda, tasa.valor)
        copia = models.PrecioInsumo(lista_id=a_lista.id, insumo_id=precio.insumo_id, precio=valor)
        pares.append((precio, copia))
    session.add_all(c for _, c in pares)
    session.flush()
    for original, copia in pares:
        o = origenes[original.id]
        convertida = tasa is not None and de.moneda != a_lista.moneda
        session.add(models.PrecioOrigen(
            precio_id=copia.id, moneda_original=o.moneda_original,
            precio_original=o.precio_original, fecha_precio=o.fecha_precio,
            tasa=tasa.valor if convertida else o.tasa,
            fecha_tasa=tasa.fecha if convertida else o.fecha_tasa,
            fuente_tasa=tasa.fuente if convertida else o.fuente_tasa, fuente=o.fuente))
        if original.id in referencias:
            session.add(models.ReferenciaPrecio(precio_id=copia.id,
                                                referencia=referencias[original.id]))
    session.flush()


def convertir_lista(
    session: Session,
    lista: models.ListaPrecios,
    a: str,
    tasa: TasaDeclarada,
    *,
    nombre: str,
    proyecto: models.Proyecto | None = None,
) -> models.ListaPrecios:
    """Lista derivada de alcance `proyecto` (SF‑E7) con cada precio convertido. `lista_base_id` queda
    vacío a propósito: UC‑02 compara listas de la misma moneda (`lista_base` devuelve esta)."""
    nueva = models.ListaPrecios(
        nombre=nombre[:120], moneda=exigir_moneda(a), fecha_vigencia=lista.fecha_vigencia,
        origen=f"{lista.nombre} en {a} con {tasa.valor} Bs/USD del {tasa.fecha:%d/%m/%Y}"[:200])
    session.add(nueva)
    session.flush()
    session.add(models.ListaPreciosOrigen(
        lista_id=nueva.id, tasa=tasa.valor, fecha_tasa=tasa.fecha,
        alcance=models.ALCANCE_PROYECTO, proyecto_id=proyecto.id if proyecto else None))
    copiar_precios(session, lista, nueva, tasa)
    session.expire(nueva, ["precios"])
    return nueva
```
```python
# core/catalog/origen.py — agregados (la regla única de precedencia de S1 §5.1)
@dataclass(frozen=True, slots=True)
class OrigenEfectivo:
    moneda_original: str
    precio_original: Decimal
    fecha_precio: date
    tasa: Decimal | None
    fecha_tasa: date | None
    fuente_tasa: str
    fuente: str


def origenes_efectivos(session: Session, lista: models.ListaPrecios) -> dict[int, OrigenEfectivo]:
    """Por `precio_id`: la fila de `PrecioOrigen` y, si falta, la lista (moneda, vigencia, tasa de
    `ListaPreciosOrigen` sin fuente, `origen`). Así abren las bases anteriores."""
    de_lista = session.get(models.ListaPreciosOrigen, lista.id)
    filas = {f.precio_id: f for f in session.scalars(
        select(models.PrecioOrigen).join(
            models.PrecioInsumo, models.PrecioInsumo.id == models.PrecioOrigen.precio_id)
        .where(models.PrecioInsumo.lista_id == lista.id))}
    salida: dict[int, OrigenEfectivo] = {}
    for precio in lista.precios:
        f = filas.get(precio.id)
        salida[precio.id] = (
            OrigenEfectivo(f.moneda_original, f.precio_original, f.fecha_precio, f.tasa,
                           f.fecha_tasa, f.fuente_tasa, f.fuente)
            if f is not None else
            OrigenEfectivo(lista.moneda, precio.precio, lista.fecha_vigencia,
                           de_lista.tasa if de_lista else None,
                           de_lista.fecha_tasa if de_lista else None, "", lista.origen))
    return salida
```
```python
# core/catalog/origen.py — `OrigenPrecio` (:54-75) gana al final, con valor por defecto
    moneda_original: str = ""
    precio_original: Decimal | None = None
    fecha_precio: date | None = None
    fuente_tasa: str = ""
    fuente: str = ""
```
```python
# core/catalog/origen.py — `origen_de_precios` (:226-302): antes del bucle, junto a `cotizadas`
    efectivos = origenes_efectivos(session, lista)
# y el `filas.append(...)` del bucle (:282-300) queda (tasa y fecha de la tasa, del origen efectivo)
        efectivo = efectivos[precio.id]
        filas.append(
            OrigenPrecio(
                insumo_id=insumo.id,
                codigo=insumo.codigo,
                descripcion=insumo.descripcion,
                tipo=insumo.tipo,
                precio=precio.precio,
                lista=lista.nombre,
                fecha_vigencia=lista.fecha_vigencia,
                moneda=lista.moneda,
                tasa=efectivo.tasa,
                fecha_tasa=efectivo.fecha_tasa,
                referencia=referencias.get(precio.id, ""),
                alcance=origen.alcance if origen else models.ALCANCE_GLOBAL,
                cotizacion=(
                    f"{cotizacion.proveedor}, {cotizacion.numero}, {cotizacion.fecha.isoformat()}"
                    if cotizacion
                    else ""
                ),
                moneda_original=efectivo.moneda_original,
                precio_original=efectivo.precio_original,
                fecha_precio=efectivo.fecha_precio,
                fuente_tasa=efectivo.fuente_tasa,
                fuente=efectivo.fuente,
            )
        )
```
```python
# core/catalog/origen.py — `crear_lista_de_proyecto` (:144-223): tras el último `session.flush()`
# (el de las `ReferenciaPrecio`) y antes de `session.expire(lista, ["precios"])`. Importar además
# `from dataclasses import asdict, dataclass`.
    efectivos = origenes_efectivos(session, base)
    ids_base = {precio.insumo_id: precio.id for precio in base.precios}
    session.add_all(
        models.PrecioOrigen(precio_id=copia.id, **asdict(efectivos[ids_base[copia.insumo_id]]))
        for copia, _ in copias
        if copia.insumo_id in ids_base and copia.insumo_id not in cotizados
    )
    session.flush()
```
  Los nombres de `OrigenEfectivo` son los de las columnas de `PrecioOrigen` (sin `precio_id`): por eso `asdict` basta. Un precio cotizado no copia el origen de la base: su origen es la cotización.
```python
# core/budget/persistencia.py — dentro de guardar_presupuesto, tras validar `motivo` (:146-147)
    if lista.moneda != presupuesto.moneda:
        raise ValueError(
            f"la version {presupuesto.codigo} esta en {presupuesto.moneda} y la lista "
            f"{lista.nombre!r} en {lista.moneda}: una version solo se valora con una lista de su "
            "moneda (RF-65)")
    declarada = moneda_declarada(session, proyecto.id) if proyecto.id is not None else None
    if declarada is not None and declarada != presupuesto.moneda and motivo != "conversion":
        raise ValueError(
            f"el proyecto esta en {declarada} y la version {presupuesto.codigo} en "
            f"{presupuesto.moneda}: convierta la version (RF-64) antes de editarla, restaurarla o "
            "revalorarla")


def moneda_declarada(session: Session, proyecto_id: int) -> str | None:
    """La última moneda de `moneda_proyecto`; `None` si el proyecto nunca la declaró."""
    return session.scalar(
        select(models.MonedaProyecto.moneda)
        .where(models.MonedaProyecto.proyecto_id == proyecto_id)
        .order_by(models.MonedaProyecto.desde.desc(), models.MonedaProyecto.id.desc()).limit(1))
```
```python
# core/budget/actualizacion.py:175 — tras `modelo = _buscar(...)`, antes de crear listas ni
# `CambioPrecio` (la prueba cuenta que no se escribió ninguno)
    if lista_nueva.moneda != modelo.moneda:
        raise ValueError(
            f"la version {codigo_presupuesto} esta en {modelo.moneda} y la lista "
            f"{lista_nueva.nombre!r} en {lista_nueva.moneda}: una version solo se revalora con una "
            "lista de su moneda (RF-65)"
        )
```
```python
# core/budget/instantanea.py:164-197 — `composiciones_revaloradas` con el precio de la línea sin
# insumo convertible (lo usa `convertir_version`; UC-02 no lo pasa y conserva el precio)
def composiciones_revaloradas(
    session: Session,
    modelo: models.Presupuesto,
    catalogo: Catalogo,
    lista: models.ListaPrecios,
    codigos: Sequence[str],
    *,
    precio_sin_insumo: Callable[[Decimal], Decimal] | None = None,
) -> dict[str, ComposicionAPU]:
    """UC‑02: las líneas de la instantánea con los precios de `lista` (por insumo).

    Una línea sin insumo conserva su precio, o el que le da `precio_sin_insumo` (la conversión de
    moneda, SL‑E1); un insumo sin precio en `lista` es `CatalogoIncompleto`. Una partida sin
    instantánea se reconstruye del catálogo con `lista`.
    """
    filas = {fila.codigo_partida: fila for fila in _filas(session, modelo)}
    precios = {precio.insumo_id: precio.precio for precio in lista.precios}

    def precio_de(linea: models.LineaComposicionVersion) -> Decimal:
        if linea.insumo_id is None:
            return linea.precio if precio_sin_insumo is None else precio_sin_insumo(linea.precio)
        precio = precios.get(linea.insumo_id)
        if precio is None:
            raise CatalogoIncompleto(
                f"el insumo {linea.descripcion} no tiene precio en la lista '{lista.nombre}'; "
                f"no se puede valorar la partida {linea.composicion.codigo_partida}"
            )
        return precio

    return {
        codigo: (
            _a_composicion(filas[codigo], precio_de)
            if codigo in filas
            else catalogo.composicion(codigo, fecha=lista.fecha_vigencia, lista=lista)
        )
        for codigo in codigos
    }
```
```python
# core/models/entidades.py:505
MOTIVOS_VERSION = ("edicion", "restauracion", "cotizacion", "revaloracion", "conversion")
# core/budget/edicion.py:58
OBJETOS = ("metraje", "apu", "cantidad", "precio", "plan", "parametro", "version", "moneda")
```
```python
# core/budget/__init__.py — en su lugar alfabético (isort): tras `core.budget.instantanea`; el
# módulo importa sus submódulos por ruta (`core.budget.persistencia`...), nunca `core.budget`
from core.budget.moneda import convertir_version, declarar_moneda, moneda_del_proyecto
# y en `__all__`, en orden alfabético: "convertir_version", "declarar_moneda", "moneda_del_proyecto"
```
```python
# core/budget/moneda.py
"""SL‑E1: moneda del proyecto y conversión de una versión (RF‑64; spec S1 §5.3). La versión
convertida nace por `guardar_presupuesto`, el único embudo (M §3.2). No hace `commit`."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _buscar, _parametros_de
from core.budget.edicion import _exigir_codigo_libre, _exigir_respaldo, version_vigente
from core.budget.instantanea import composiciones_revaloradas, plan_de_version
from core.budget.persistencia import (
    _cargar_externos, _cargar_pendientes, cargar_presupuesto, guardar_presupuesto,
    moneda_declarada)
from core.budget.presupuesto import (
    CODIGO_ATIPICO, MONEDA_POR_DEFECTO, _declarar_externos, elaborar, exigir_composiciones)
from core.catalog import Catalogo
from core.catalog.moneda import TasaDeclarada, convertir, convertir_lista, exigir_moneda
from core.contracts.verificacion import ReglaVerificacion
from core.verification import REGLAS


def moneda_del_proyecto(session: Session, proyecto: models.Proyecto) -> str:
    declarada = moneda_declarada(session, proyecto.id)
    if declarada is not None:
        return declarada
    vigente = version_vigente(session, proyecto.nombre)
    return vigente.moneda if vigente is not None else MONEDA_POR_DEFECTO


def declarar_moneda(session, proyecto, moneda, *, responsable, fuente="al crear el proyecto "
                    "(UC-01 paso 1)", ahora=None) -> models.MonedaProyecto:
    """UC‑01 paso 1: la moneda elegida al crear el proyecto. Con versiones, es `convertir_version`."""
    if session.scalar(select(func.count()).select_from(models.Presupuesto)
                      .where(models.Presupuesto.proyecto_id == proyecto.id)):
        raise ValueError("el proyecto ya tiene versiones: cambiar su moneda es convertir_version")
    fila = models.MonedaProyecto(proyecto_id=proyecto.id, moneda=exigir_moneda(moneda),
                                 desde=ahora or datetime.now(), responsable=responsable.strip(),
                                 fuente=fuente)
    session.add(fila)
    session.flush()
    return fila


def convertir_version(
    session: Session, proyecto_nombre: str, codigo: str, codigo_nuevo: str, moneda: str,
    tasa: TasaDeclarada, *, fuente: str, responsable: str, catalogo: Catalogo,
    reglas: Sequence[ReglaVerificacion] = REGLAS, ahora: datetime | None = None,
) -> models.Presupuesto:
    """Versión nueva (motivo `conversion`) con lista derivada, líneas y bono convertidos y el plan
    conservado; fila de `moneda_proyecto` y `RegistroCambio` (objeto `moneda`, fuente = la tasa)."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    moneda = exigir_moneda(moneda)
    origen = _buscar(session, proyecto_nombre, codigo)
    if origen.moneda == moneda:
        raise ValueError(f"la version {codigo} ya esta en {moneda}")
    _exigir_codigo_libre(session, origen.proyecto_id, codigo_nuevo)
    anterior = cargar_presupuesto(session, proyecto_nombre, codigo, catalogo)
    lista = convertir_lista(session, origen.lista_precios, moneda, tasa,
                            nombre=f"{origen.lista_precios.nombre} en {moneda} ({codigo_nuevo})",
                            proyecto=origen.proyecto)
    items = [p.item for p in anterior.partidas]
    composiciones = composiciones_revaloradas(
        session, origen, catalogo, lista, list(dict.fromkeys(i.codigo_partida for i in items)),
        precio_sin_insumo=lambda p: convertir(p, origen.moneda, moneda, tasa.valor))
    exigir_composiciones(items, composiciones)
    parametros = replace(_parametros_de(origen), bono_alimentacion=convertir(
        origen.bono_alimentacion, origen.moneda, moneda, tasa.valor))
    plan = plan_de_version(session, origen)
    nuevo = elaborar([*items, *_cargar_pendientes(session, origen)], composiciones, parametros,
                     codigo=codigo_nuevo, fecha=origen.fecha, moneda=moneda, plan=plan,
                     reglas=tuple(reglas))
    externos = _cargar_externos(session, origen, tuple(reglas), sin=(CODIGO_ATIPICO,))
    nuevo = replace(nuevo, informe=_declarar_externos(nuevo.informe, externos))
    version = guardar_presupuesto(session, nuevo.presupuesto, nuevo.informe,
                                  proyecto=origen.proyecto, lista=lista, parametros=parametros,
                                  pendientes=nuevo.pendientes, plan=plan, version_origen=origen,
                                  motivo="conversion")
    momento = ahora or datetime.now()
    session.add(models.MonedaProyecto(proyecto_id=origen.proyecto_id, moneda=moneda, desde=momento,
                                      version_id=version.id, responsable=responsable,
                                      fuente=fuente))
    session.add(models.RegistroCambio(
        proyecto_id=origen.proyecto_id, version_origen_id=origen.id,
        version_resultante_id=version.id, objeto="moneda", clave=proyecto_nombre, campo="moneda",
        valor_anterior=origen.moneda, valor_nuevo=moneda, fuente=tasa.fuente,
        responsable=responsable, fecha_hora=momento))
    session.flush()
    return version
```
- [ ] **Paso 4: Correrla y ver el verde** (y la suite): `uv run pytest tests/unit/test_moneda.py tests/integration/test_conversion_version.py tests/integration/test_cotizacion_proyecto.py tests/integration/test_actualizacion_precios.py tests/integration/test_edicion_versiones.py -q -W error`; `uv run pytest -q -W error`; `uv run ruff check core tests/unit/test_moneda.py tests/integration/test_conversion_version.py`; `uv run python scripts/guardia_nucleo.py --base origin/main`.
- [ ] **Paso 5: Commit** (prueba, luego código)
```bash
git add tests/unit/test_moneda.py tests/integration/test_conversion_version.py tests/fixtures/versiones.py
git commit -m "test(core): SL-E1 conversion, erosion y monedas mezcladas en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add core/catalog/moneda.py core/catalog/origen.py core/budget/moneda.py core/budget/persistencia.py core/budget/actualizacion.py core/budget/instantanea.py core/budget/edicion.py core/budget/__init__.py core/models/entidades.py
git commit -m "feat(core): SL-E1 conversion de version, erosion y origen por precio" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
**Compuerta GS1‑1:** `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S1-1 --junit reporte-pruebas.xml` en OK (C3 con los tres `ParTDD` de `S1-1`; C5 regresión literal), el paso de la CI sube a `--hasta S1-1`, CI verde Linux/Windows, aval del tutor del expediente SL‑E1, PR `inc/060-s1-1-nucleo` fusionado con `gh pr merge <n> --merge`.

---

# S1‑2 — Adaptador del BCV (rama `inc/060-s1-2-bcv`, carril paralelo)

### Tarea 6: `adapters/bcv` — cuadrícula neutra, tasa, INPC, CSV canónico e informe

**Rama:** `inc/060-s1-2-bcv` (sale de `main` **sin núcleo pendiente**; nunca de una rama `-nucleo`; PR a `main`, se fusiona al cruzar GS1‑2)   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `adapters/bcv/__init__.py`, `adapters/bcv/informe.py`, `adapters/bcv/libro.py`, `adapters/bcv/tasa.py`, `adapters/bcv/inpc.py`, `adapters/bcv/csv_canonico.py`, `adapters/bcv/formatos.py`, `adapters/bcv/formatos.json`, `tests/unit/adapters/__init__.py`, `tests/unit/adapters/test_bcv_libro.py`, `tests/unit/adapters/test_bcv_tasa.py`, `tests/unit/adapters/test_bcv_inpc.py`, `tests/unit/adapters/test_bcv_csv.py`, `tests/fixtures/bcv_cuadriculas.py`
- Modificar: `tests/unit/test_arquitectura.py`, bloque `TERCEROS_POR_ADAPTADOR` (líneas 23‑29 en `v0.5.0`; B solo cambió la línea 18): agregar la línea `"bcv": frozenset({"xlrd", "openpyxl"}),`. `xlrd` cumple además la regla de A2 (`tests/unit/test_dependencias_silice.py`: dueño `adapters/bcv/`, importación diferida dentro de la función)

**Interfaces:**
- Produce (solo biblioteca estándar en los tipos): `Celda = str | Decimal | date | None`; `Hoja(nombre, filas)`; `Libro(archivo, huella, hojas, avisos)`; `FormatoNoReconocido(ValueError)`; `ValorLeido(fecha, valor, provisional=False, lugar="")`; `SerieLeida(clave, nombre, organismo, unidad, periodicidad, base, valores)`; `Rechazo(lugar, motivo)`; `InformeImportacion(archivo, huella, fuente, fecha_descarga, series, rechazos=(), advertencias=(), filas_leidas=0)` con `.filas_rechazadas`, `.provisionales`, `.texto()`; `validar_fuente(fuente) -> str`; `abrir_libro(ruta) -> Libro`; `leer_tasa(libro, *, fuente, fecha_descarga, trimestre_por_letra) -> InformeImportacion` (claves `usd_compra`, `usd_venta`); `FormatoMensual(hoja, etiqueta_periodo, etiqueta_valor, marca_provisional="(*)", base="")`; `leer_inpc(libro, *, fuente, fecha_descarga, formato) -> InformeImportacion` (clave `inpc_general`); `COLUMNAS_CSV = ("serie","fecha","valor","provisional","fuente")`; `leer_csv_canonico(ruta, *, fecha_descarga) -> InformeImportacion`; `Formatos(trimestre_por_letra, inpc)` y `cargar_formatos() -> Formatos`.

- [ ] **Paso 1: Escribir la prueba que falla** (una por intérprete; commit de cada prueba antes que su intérprete)
```python
# tests/fixtures/bcv_cuadriculas.py
"""Cuadrículas neutras para los casos negativos (S1 §7.1): sin escribir .xls."""
import re
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from adapters.bcv.libro import Hoja, Libro

CARPETA = Path(__file__).resolve().parent / "bcv"


def hoja_tasa(nombre, fecha="01/10/2026", compra=D("858.02"), venta=D("860.18"), codigo="USD",
              etiqueta="Fecha Valor:"):
    return Hoja(nombre, (
        ("BANCO CENTRAL DE VENEZUELA", None, None),
        (f"{etiqueta} {fecha}", None, None),
        ("EUR", D("1000.1"), D("1002.3")),
        (codigo, compra, venta),
    ))


def libro(*hojas, archivo="2_1_2c26_smc.xls"):
    return Libro(archivo, "0" * 64, tuple(hojas))


def transcripcion(seccion: str) -> list[dict[str, str]]:
    """Filas de la transcripción a mano de FUENTE.md (Tarea 3)."""
    texto = (CARPETA / "FUENTE.md").read_text(encoding="utf-8").split(f"## {seccion}")[1]
    tabla = texto.split("### Transcripción")[1].split("\n## ")[0]
    filas = [f.strip().strip("|").split("|") for f in tabla.splitlines() if f.startswith("| ")]
    encabezado = [c.strip() for c in filas[0]]
    return [dict(zip(encabezado, (c.strip() for c in f), strict=True)) for f in filas[2:]]


def campo(seccion: str, nombre: str) -> str:
    texto = (CARPETA / "FUENTE.md").read_text(encoding="utf-8").split(f"## {seccion}")[1]
    return re.search(rf"^\| {re.escape(nombre)} \| ([^|]+?) \|$", texto, re.MULTILINE).group(1)
```
```python
# tests/unit/adapters/test_bcv_tasa.py
from datetime import date
from decimal import Decimal as D

import pytest

from adapters.bcv.formatos import cargar_formatos
from adapters.bcv.informe import FormatoNoReconocido
from adapters.bcv.libro import abrir_libro
from adapters.bcv.tasa import leer_tasa
from tests.fixtures.bcv_cuadriculas import CARPETA, campo, hoja_tasa, libro, transcripcion

FUENTE = "https://www.bcv.org.ve/estadisticas/tipo-cambio-de-referencia-smc"
DESCARGA = date(2026, 10, 8)
LETRAS = {"a": 1, "b": 2, "c": 3, "d": 4}


def _leer(lib, fuente=FUENTE):
    return leer_tasa(lib, fuente=fuente, fecha_descarga=DESCARGA, trimestre_por_letra=LETRAS)


def test_el_archivo_real_da_n_hojas_y_coincide_con_la_transcripcion_a_mano():
    real = abrir_libro(CARPETA / campo("Tasa", "Archivo"))
    informe = leer_tasa(real, fuente=campo("Tasa", "Dirección"),
                        fecha_descarga=date.fromisoformat(campo("Tasa", "Fecha de descarga")),
                        trimestre_por_letra=cargar_formatos().trimestre_por_letra)
    compra, venta = informe.series
    assert len(venta.valores) == int(campo("Tasa", "Hojas (N)"))  # PRU‑H13: N transcrito
    por_hoja = {v.lugar.split("!")[0]: (c, v) for c, v in zip(compra.valores, venta.valores,
                                                               strict=True)}
    for fila in transcripcion("Tasa"):
        c, v = por_hoja[fila["Hoja"]]
        assert (v.fecha.isoformat(), c.valor, v.valor) == (
            fila["Fecha valor"], D(fila["Compra"]), D(fila["Venta"]))
    assert any(v.fecha == date(2026, 10, 1) and v.valor == D("860.18") for v in venta.valores)


def test_hoja_nueva_o_renombrada_no_tumba_el_archivo():
    """[Foco 1] una hoja sin la etiqueta se rechaza y se reporta; una renombrada vale por contenido."""
    resumen = libro(hoja_tasa("Resumen", etiqueta="Notas"), hoja_tasa("hoja renombrada"))
    informe = _leer(resumen)
    assert [r.lugar for r in informe.rechazos] == ["Resumen"]
    assert "Fecha Valor" in informe.rechazos[0].motivo
    assert informe.series[1].valores[0].valor == D("860.18")


@pytest.mark.parametrize("hojas, motivo", [
    ((hoja_tasa("a"), hoja_tasa("b")), "repetida"),
    ((hoja_tasa("a", fecha="15/05/2026"),), "fuera del trimestre"),
    ((hoja_tasa("a", fecha="09/10/2026"),), "posterior a la descarga"),
    ((hoja_tasa("a", venta="860,18"),), "no numerico"),
    ((hoja_tasa("a", compra=D("0")),), "mayor que cero"),
    ((hoja_tasa("a", codigo="EUR"),), "fila USD"),
])
def test_cuadriculas_negativas_se_rechazan_con_su_motivo(hojas, motivo):
    rechazos = _leer(libro(*hojas)).rechazos
    assert rechazos and motivo in rechazos[-1].motivo


def test_sin_ninguna_etiqueta_se_rechaza_el_archivo_y_dominio_ajeno_tambien():
    with pytest.raises(FormatoNoReconocido, match="Fecha Valor"):
        _leer(libro(hoja_tasa("x", etiqueta="Otra")))
    with pytest.raises(FormatoNoReconocido, match="bcv.org.ve"):
        _leer(libro(hoja_tasa("x")), fuente="https://bcv.org.ve.ejemplo.com/x.xls")


def test_nombre_fuera_de_patron_advierte_y_compra_mayor_que_venta_advierte():
    informe = _leer(libro(hoja_tasa("x", compra=D("861")), archivo="tasas.xls"))
    assert any("2e" in a for a in informe.advertencias)
    assert any("compra" in a for a in informe.advertencias)
```
```python
# tests/unit/adapters/test_bcv_libro.py
import openpyxl
import pytest

from adapters.bcv.informe import FormatoNoReconocido
from adapters.bcv.libro import FIRMA_OLE2, LIMITE_BYTES, abrir_libro
from tests.fixtures.bcv_cuadriculas import CARPETA, campo


def test_un_xlsx_renombrado_xls_se_rechaza(tmp_path):
    ruta = tmp_path / "x.xlsx"
    openpyxl.Workbook().save(ruta)
    falso = ruta.rename(tmp_path / "2_1_2c26_smc.xls")
    with pytest.raises(FormatoNoReconocido, match="renombrado"):
        abrir_libro(falso)


def test_mas_de_20_mb_se_rechaza(tmp_path):
    ruta = tmp_path / "grande.xls"
    ruta.write_bytes(FIRMA_OLE2 + b"\0" * LIMITE_BYTES)
    with pytest.raises(FormatoNoReconocido, match="20 MB"):
        abrir_libro(ruta)


def test_el_libro_real_abre_con_su_huella():
    libro = abrir_libro(CARPETA / campo("Tasa", "Archivo"))
    assert libro.huella == campo("Tasa", "SHA-256")
    assert len(libro.hojas) == int(campo("Tasa", "Hojas (N)"))
```
```python
# tests/unit/adapters/__init__.py
"""Pruebas del adaptador del BCV (spec S1 §7): archivo real contra `FUENTE.md` y cuadrículas."""
```
```python
# tests/unit/adapters/test_bcv_inpc.py
"""INPC mensual del BCV (S1 §7; UC-17 2a, 2b): el archivo real contra la transcripcion a mano de
FUENTE.md (PRU-H13) y cuadriculas negativas sin escribir .xls."""
import json
import re
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from adapters.bcv.formatos import RUTA_FORMATOS, FormatoMensual, cargar_formatos
from adapters.bcv.informe import FormatoNoReconocido
from adapters.bcv.inpc import leer_inpc
from adapters.bcv.libro import Hoja, abrir_libro
from tests.fixtures.bcv_cuadriculas import CARPETA, campo, libro, transcripcion

FUENTE = "https://www.bcv.org.ve/estadisticas/consumidor"
DESCARGA = date(2026, 10, 8)
#: Formato de las cuadriculas de esta prueba (no el del archivo real, que viene de formatos.json).
FORMATO = FormatoMensual("INPC", "Período", "Índice general", "(*)", "base ficticia")
BCV_FORMATOS = Path(__file__).resolve().parents[3] / "docs" / "fuentes" / "bcv_formatos.md"
TITULO_FORMATOS = "## Formatos para `adapters/bcv/formatos.json`"


def _hoja(*filas, nombre="INPC", encabezado=("Período", "Índice general")):
    return Hoja(nombre, (("BANCO CENTRAL DE VENEZUELA", None), encabezado, *filas))


def _leer(*hojas):
    return leer_inpc(libro(*hojas, archivo="inpc.xls"), fuente=FUENTE, fecha_descarga=DESCARGA,
                     formato=FORMATO)


def test_el_archivo_real_coincide_con_la_transcripcion_a_mano():
    real = abrir_libro(CARPETA / campo("INPC", "Archivo"))
    informe = leer_inpc(real, fuente=campo("INPC", "Dirección"),
                        fecha_descarga=date.fromisoformat(campo("INPC", "Fecha de descarga")),
                        formato=cargar_formatos().inpc)
    (serie,) = informe.series
    assert (serie.clave, serie.unidad, serie.periodicidad) == ("inpc_general", "indice_bs",
                                                               "mensual")
    por_mes = {v.fecha.strftime("%Y-%m"): v for v in serie.valores}
    for fila in transcripcion("INPC"):
        valor = por_mes[fila["Mes"]]
        assert (valor.valor, valor.provisional) == (D(fila["Valor"]), fila["Provisional"] == "sí")


@pytest.mark.parametrize(
    "periodo", ["Ene-2026", "enero 2026", "01/2026", "2026-01", date(2026, 1, 1)]
)
def test_cada_forma_del_periodo_da_el_primer_dia_del_mes(periodo):
    (valor,) = _leer(_hoja((periodo, D("100.5")))).series[0].valores
    assert (valor.fecha, valor.valor, valor.provisional) == (date(2026, 1, 1), D("100.5"), False)


def test_la_marca_de_provisional_se_guarda_por_valor():
    informe = _leer(_hoja(("Ene-2026", D("100.5")), ("Feb-2026 (*)", D("101.2"))))
    assert [v.provisional for v in informe.series[0].valores] == [False, True]
    assert informe.provisionales == 1


def test_sin_la_hoja_o_sin_un_encabezado_se_rechaza_el_archivo_nombrandolo():
    with pytest.raises(FormatoNoReconocido, match="INPC"):
        _leer(_hoja(("Ene-2026", D("100.5")), nombre="Otra"))
    with pytest.raises(FormatoNoReconocido, match="Índice general"):
        _leer(_hoja(("Ene-2026", D("100.5")), encabezado=("Período", "Variación")))
    with pytest.raises(FormatoNoReconocido, match="Período"):
        _leer(_hoja(("Ene-2026", D("100.5")), encabezado=("Mes", "Índice general")))


@pytest.mark.parametrize("filas, motivo", [
    ((("Ene-2026", D("100")), ("Ene-2026", D("101"))), "repetido"),
    ((("Ene-2026", D("100")), ("Mar-2026", D("102"))), "no consecutivo"),
    ((("Nov-2026", D("100")),), "posterior a la descarga"),
    ((("Ene-2026", "100,5"),), "no numerico"),
    ((("Ene-2026", D("0")),), "mayor que cero"),
    ((("Trimestre 1", D("100")),), "ilegible"),
])
def test_filas_negativas_se_rechazan_con_su_motivo_y_las_demas_siguen(filas, motivo):
    informe = _leer(_hoja(*filas))
    assert informe.rechazos and motivo in informe.rechazos[-1].motivo
    assert informe.filas_leidas == len(filas)
    assert len(informe.series[0].valores) == len(filas) - 1


def test_formatos_json_copia_bcv_formatos_md():
    seccion = BCV_FORMATOS.read_text(encoding="utf-8").split(TITULO_FORMATOS)[1]
    filas = re.findall(r"^\| `([a-z_.]+)` \| `(.+)` \|$", seccion.split("\n## ")[0], re.M)
    assert filas
    datos = json.loads(RUTA_FORMATOS.read_text(encoding="utf-8"))
    for clave, valor in filas:
        grupo, nombre = clave.split(".", 1)
        assert datos[grupo][nombre] == json.loads(valor), clave
    assert sum(len(grupo) for grupo in datos.values()) == len(filas)
```
```python
# tests/unit/adapters/test_bcv_csv.py
"""CSV canonico de series (S1 §7.3; UC-17 2f): las mismas validaciones de fecha, valor y repeticion
que los .xls, con la fuente obligatoria por fila."""
import hashlib
from datetime import date
from decimal import Decimal as D

import pytest

from adapters.bcv.csv_canonico import COLUMNAS_CSV, leer_csv_canonico
from adapters.bcv.informe import FormatoNoReconocido

DESCARGA = date(2026, 10, 8)
FUENTE = "https://www.bcv.org.ve/estadisticas/insumos-de-la-construccion"
BUENAS = (f"IIC-GENERAL,2026-01-01,100.5,no,{FUENTE}\n"
          f"IIC-GENERAL,2026-02-01,101.25,si,{FUENTE}\n")


def _csv(tmp_path, cuerpo, encabezado=",".join(COLUMNAS_CSV)):
    ruta = tmp_path / "serie.csv"
    ruta.write_text(f"{encabezado}\n{cuerpo}", encoding="utf-8")
    return ruta


def test_las_filas_buenas_dan_una_serie_con_su_huella_y_su_fuente(tmp_path):
    ruta = _csv(tmp_path, BUENAS)
    informe = leer_csv_canonico(ruta, fecha_descarga=DESCARGA)
    (serie,) = informe.series
    assert serie.clave == "IIC-GENERAL" and (serie.unidad, serie.periodicidad) == ("", "")
    assert [(v.fecha, v.valor, v.provisional) for v in serie.valores] == [
        (date(2026, 1, 1), D("100.5"), False), (date(2026, 2, 1), D("101.25"), True)]
    assert informe.huella == hashlib.sha256(ruta.read_bytes()).hexdigest()
    assert (informe.fuente, informe.filas_leidas, informe.rechazos) == (FUENTE, 2, ())


@pytest.mark.parametrize("fila, motivo", [
    (f"IIC-GENERAL,01/03/2026,100,no,{FUENTE}", "AAAA-MM-DD"),
    (f'IIC-GENERAL,2026-03-01,"1,5",no,{FUENTE}', "use punto"),
    (f"IIC-GENERAL,2026-03-01,0,no,{FUENTE}", "mayor que cero"),
    ("IIC-GENERAL,2026-03-01,100,no,", "fuente"),
    (f"IIC-GENERAL,2026-02-01,102,no,{FUENTE}", "repetido"),
    (f"IIC-GENERAL,2026-11-01,100,no,{FUENTE}", "posterior a la descarga"),
    (f"IIC-GENERAL,2026-03-01,100,quizas,{FUENTE}", "provisional"),
    (f",2026-03-01,100,no,{FUENTE}", "serie"),
])
def test_cada_fila_mala_se_rechaza_con_su_motivo_y_las_buenas_siguen(tmp_path, fila, motivo):
    informe = leer_csv_canonico(_csv(tmp_path, BUENAS + fila + "\n"), fecha_descarga=DESCARGA)
    assert len(informe.series[0].valores) == 2
    (rechazo,) = informe.rechazos
    assert rechazo.lugar == "serie.csv:4" and motivo in rechazo.motivo


def test_sin_las_cinco_columnas_se_rechaza_el_archivo(tmp_path):
    ruta = _csv(tmp_path, "IIC,2026-01-01,1,no\n", "serie,fecha,valor,provisional")
    with pytest.raises(FormatoNoReconocido, match="fuente"):
        leer_csv_canonico(ruta, fecha_descarga=DESCARGA)
```
```python
# tests/unit/test_arquitectura.py — bloque TERCEROS_POR_ADAPTADOR (líneas 23-29 en v0.5.0)
TERCEROS_POR_ADAPTADOR: dict[str, frozenset[str]] = {
    "bcv": frozenset({"xlrd", "openpyxl"}),
    "civil": frozenset({"ifcopenshell"}),
    "espacio": frozenset({"sqlalchemy", "ezdxf", "ifcopenshell"}),
    "industrial": frozenset(),
    "sistemas": frozenset(),
    "telecom": frozenset(),
}
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/adapters -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'adapters.bcv'`; `test_toda_carpeta_de_adapters_tiene_su_regla` en rojo hasta agregar la línea.
- [ ] **Paso 3: Implementación mínima**
```python
# adapters/bcv/informe.py
"""Tipos propios del adaptador del BCV (biblioteca estándar) y validación de la fuente."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from urllib.parse import urlsplit

DOMINIO_BCV = "bcv.org.ve"


class FormatoNoReconocido(ValueError):
    """El archivo no es lo que el formato documentado dice (UC‑17 2a); no se escribe nada."""


@dataclass(frozen=True, slots=True)
class ValorLeido:
    fecha: date
    valor: Decimal
    provisional: bool = False
    lugar: str = ""


@dataclass(frozen=True, slots=True)
class SerieLeida:
    clave: str
    nombre: str
    organismo: str
    unidad: str
    periodicidad: str
    base: str
    valores: tuple[ValorLeido, ...]


@dataclass(frozen=True, slots=True)
class Rechazo:
    lugar: str
    motivo: str


@dataclass(frozen=True, slots=True)
class InformeImportacion:
    archivo: str
    huella: str
    fuente: str
    fecha_descarga: date
    series: tuple[SerieLeida, ...]
    rechazos: tuple[Rechazo, ...] = ()
    advertencias: tuple[str, ...] = ()
    filas_leidas: int = 0

    @property
    def filas_rechazadas(self) -> int:
        return len(self.rechazos)

    @property
    def provisionales(self) -> int:
        return sum(v.provisional for s in self.series for v in s.valores)

    def texto(self) -> str:
        lineas = [f"{s.clave}: {len(s.valores)} valores" for s in self.series]
        lineas += [f"rechazo {r.lugar}: {r.motivo}" for r in self.rechazos]
        return "\n".join([*lineas, *self.advertencias])


def validar_fuente(fuente: str) -> str:
    partes = urlsplit(fuente.strip())
    host = (partes.hostname or "").lower()
    if partes.scheme not in ("http", "https") or not (
        host == DOMINIO_BCV or host.endswith("." + DOMINIO_BCV)
    ):
        raise FormatoNoReconocido(f"la fuente {fuente!r} no es una direccion de {DOMINIO_BCV}")
    return fuente.strip()
```
```python
# adapters/bcv/libro.py
"""Abre un libro del BCV (.xls con xlrd, .xlsx con openpyxl; ambos importados en la función) y lo
entrega como cuadrícula neutra. Un número que llega como float se lleva a Decimal con repr y se
declara en `Libro.avisos` (S1 §7.2)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from adapters.bcv.informe import FormatoNoReconocido

Celda = str | Decimal | date | None
LIMITE_BYTES = 20 * 1024 * 1024
FIRMA_OLE2 = bytes.fromhex("D0CF11E0A1B11AE1")
FIRMA_ZIP = b"PK\x03\x04"


@dataclass(frozen=True, slots=True)
class Hoja:
    nombre: str
    filas: tuple[tuple[Celda, ...], ...]


@dataclass(frozen=True, slots=True)
class Libro:
    archivo: str
    huella: str
    hojas: tuple[Hoja, ...]
    avisos: tuple[str, ...] = ()


def abrir_libro(ruta: Path) -> Libro:
    tamano = ruta.stat().st_size
    if tamano > LIMITE_BYTES:
        raise FormatoNoReconocido(f"{ruta.name}: pesa {tamano / 2**20:.1f} MB; el limite es 20 MB")
    contenido = ruta.read_bytes()
    sufijo = ruta.suffix.lower()
    if sufijo == ".xls":
        if not contenido.startswith(FIRMA_OLE2):
            extra = " (es un .xlsx renombrado)" if contenido.startswith(FIRMA_ZIP) else ""
            raise FormatoNoReconocido(f"{ruta.name}: la extension .xls no coincide con el contenido{extra}")
        hojas, floats = _xls(contenido, ruta.name)
    elif sufijo == ".xlsx":
        if not contenido.startswith(FIRMA_ZIP):
            raise FormatoNoReconocido(f"{ruta.name}: la extension .xlsx no coincide con el contenido")
        hojas, floats = _xlsx(ruta)
    else:
        raise FormatoNoReconocido(f"{ruta.name}: se leen .xls y .xlsx")
    avisos = (f"{floats} celdas numericas leidas como float y llevadas a Decimal con repr",) if floats else ()
    return Libro(ruta.name, hashlib.sha256(contenido).hexdigest(), hojas, avisos)


def _xls(contenido: bytes, nombre: str) -> tuple[tuple[Hoja, ...], int]:
    import xlrd  # extra `bcv` (RV‑24), importación diferida

    try:
        libro = xlrd.open_workbook(file_contents=contenido)
    except Exception as error:  # xlrd lanza varias clases ante un archivo dañado
        raise FormatoNoReconocido(f"{nombre}: no se pudo abrir ({error})") from None
    floats, hojas = 0, []
    for hoja in libro.sheets():
        filas = []
        for r in range(hoja.nrows):
            fila: list[Celda] = []
            for c in range(hoja.ncols):
                celda = hoja.cell(r, c)
                if celda.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    fila.append(None)
                elif celda.ctype == xlrd.XL_CELL_TEXT:
                    fila.append(celda.value.strip() or None)
                elif celda.ctype == xlrd.XL_CELL_NUMBER:
                    floats += 1
                    fila.append(Decimal(repr(celda.value)))
                elif celda.ctype == xlrd.XL_CELL_DATE:
                    fila.append(xlrd.xldate_as_datetime(celda.value, libro.datemode).date())
                else:
                    fila.append(str(celda.value))
            filas.append(tuple(fila))
        hojas.append(Hoja(hoja.name, tuple(filas)))
    return tuple(hojas), floats


def _xlsx(ruta: Path) -> tuple[tuple[Hoja, ...], int]:
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    floats, hojas = 0, []
    try:
        for hoja in libro.worksheets:
            filas = []
            for valores in hoja.iter_rows(values_only=True):
                fila: list[Celda] = []
                for v in valores:
                    if isinstance(v, float):
                        floats += 1
                        fila.append(Decimal(repr(v)))
                    elif isinstance(v, int) and not isinstance(v, bool):
                        fila.append(Decimal(v))
                    elif isinstance(v, datetime):
                        fila.append(v.date())
                    elif isinstance(v, str):
                        fila.append(v.strip() or None)
                    else:
                        fila.append(None if v is None else str(v))
                filas.append(tuple(fila))
            hojas.append(Hoja(hoja.title, tuple(filas)))
    finally:
        libro.close()
    return tuple(hojas), floats
```
```python
# adapters/bcv/tasa.py
"""Tasa de referencia del BCV: .xls trimestral, una hoja por día hábil (S1 §7). Solo el USD (H‑D1).
Las etiquetas «Fecha Valor» y el código USD están verificadas (antecedentes §6); la letra del
trimestre llega de `formatos.json` (Tarea 3). SUPUESTO_DECLARADO: la fecha valor puede caer hasta 7
días naturales después del fin del trimestre (la última hoja del 3T‑2026 vale el 01‑10‑2026)."""
from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal

from adapters.bcv.informe import (
    FormatoNoReconocido, InformeImportacion, Rechazo, SerieLeida, ValorLeido, validar_fuente)
from adapters.bcv.libro import Hoja, Libro

ETIQUETA_FECHA_VALOR = "fecha valor"
CODIGO_USD = "USD"
PATRON_NOMBRE = re.compile(r"^2_1_2([a-d])(\d{2})_smc\.xls$", re.IGNORECASE)
DIAS_DE_FECHA_VALOR = 7
_FECHA = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_SIN_ETIQUETA = object()


def _fecha_de(celda) -> date | None:
    if isinstance(celda, date):
        return celda
    m = _FECHA.search(celda) if isinstance(celda, str) else None
    if m is None:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _fecha_valor(hoja: Hoja):
    for fila in hoja.filas:
        for i, celda in enumerate(fila):
            if isinstance(celda, str) and ETIQUETA_FECHA_VALOR in celda.casefold():
                propia = _fecha_de(celda.split(":", 1)[1]) if ":" in celda else None
                siguiente = next((c for c in fila[i + 1:] if c is not None), None)
                return propia or _fecha_de(siguiente)
    return _SIN_ETIQUETA


def _rango(archivo: str, letras: Mapping[str, int]) -> tuple[date, date] | None:
    m = PATRON_NOMBRE.match(archivo)
    if m is None:
        return None
    trimestre, anio = letras[m.group(1).lower()], 2000 + int(m.group(2))
    inicio = date(anio, 3 * trimestre - 2, 1)
    fin = (date(anio + 1, 1, 1) if trimestre == 4 else date(anio, 3 * trimestre + 1, 1)) - timedelta(1)
    return inicio, fin + timedelta(days=DIAS_DE_FECHA_VALOR)


def leer_tasa(libro: Libro, *, fuente: str, fecha_descarga: date,
              trimestre_por_letra: Mapping[str, int]) -> InformeImportacion:
    fuente = validar_fuente(fuente)
    advertencias = list(libro.avisos)
    rango = _rango(libro.archivo, trimestre_por_letra)
    if rango is None:
        advertencias.append(f"el nombre {libro.archivo!r} no sigue 2_1_2<letra><AA>_smc.xls: se "
                            "importa porque el formato valida (UC-17 2e)")
    compra, venta, rechazos, vistas, con_etiqueta, otras = [], [], [], set(), 0, 0
    for hoja in libro.hojas:
        fecha = _fecha_valor(hoja)
        if fecha is _SIN_ETIQUETA:
            rechazos.append(Rechazo(hoja.nombre, "falta la etiqueta «Fecha Valor»"))
            continue
        con_etiqueta += 1
        motivo = (
            "fecha valor ilegible" if fecha is None
            else "fecha repetida" if fecha in vistas
            else "fecha fuera del trimestre del archivo" if rango and not rango[0] <= fecha <= rango[1]
            else "fecha posterior a la descarga" if fecha > fecha_descarga else "")
        if motivo:
            rechazos.append(Rechazo(hoja.nombre, motivo))
            continue
        fila_usd = next(((n, f) for n, f in enumerate(hoja.filas)
                         if any(isinstance(c, str) and c.strip().upper() == CODIGO_USD for c in f)),
                        None)
        if fila_usd is None:
            rechazos.append(Rechazo(hoja.nombre, "la hoja no trae la fila USD (hoja de otra moneda)"))
            continue
        n, fila = fila_usd
        despues = fila[[i for i, c in enumerate(fila) if isinstance(c, str) and c.strip().upper() == CODIGO_USD][0] + 1:]
        numeros = [c for c in despues if c is not None][:2]
        if len(numeros) < 2 or not all(isinstance(x, Decimal) for x in numeros):
            rechazos.append(Rechazo(f"{hoja.nombre}!{n + 1}", "valor no numerico en compra o venta"))
            continue
        c, v = numeros
        if c <= 0 or v <= 0:
            rechazos.append(Rechazo(f"{hoja.nombre}!{n + 1}", "el valor debe ser mayor que cero"))
            continue
        if c > v:
            advertencias.append(f"{hoja.nombre}: compra {c} mayor que venta {v} (expectativa, no regla)")
        vistas.add(fecha)
        compra.append(ValorLeido(fecha, c, lugar=f"{hoja.nombre}!{n + 1}"))
        venta.append(ValorLeido(fecha, v, lugar=f"{hoja.nombre}!{n + 1}"))
        otras += sum(1 for f in hoja.filas for x in f[:1] if isinstance(x, str)
                     and re.fullmatch(r"[A-Z]{3}", x.strip()) and x.strip() != CODIGO_USD)
    if con_etiqueta == 0:
        raise FormatoNoReconocido(f"{libro.archivo}: ninguna hoja trae la etiqueta «Fecha Valor»")
    if otras:
        advertencias.append(f"{otras} filas de otras monedas no importadas (solo USD, H-D1)")
    series = tuple(SerieLeida(clave, f"Tasa USD ({lado})", "BCV", "Bs/USD", "diaria", "", tuple(vals))
                   for clave, lado, vals in (("usd_compra", "compra", compra),
                                             ("usd_venta", "venta", venta)))
    return InformeImportacion(libro.archivo, libro.huella, fuente, fecha_descarga, series,
                              tuple(rechazos), tuple(advertencias), len(libro.hojas))
```
```python
# adapters/bcv/__init__.py
"""Lectura sin conexion de los archivos del BCV (spec S1 §7): `libro` da la cuadricula neutra;
`tasa`, `inpc` y `csv_canonico` la interpretan; `informe` tiene los tipos propios y `formatos` lo
que S1-0 verifico en los archivos reales. No implementa `AdaptadorDominio` ni importa `core`
(S1 §4.1). Este paquete no importa sus modulos: `xlrd` y `openpyxl` se cargan solo al leer."""
```
```python
# adapters/bcv/inpc.py
"""INPC mensual del BCV (spec S1 §7): una hoja con una columna de periodo y otra del indice
general. La hoja, los dos encabezados, la marca de provisional y la base llegan de `formatos.json`
(copia de `docs/fuentes/bcv_formatos.md`, Tarea 3): el lector no adivina ninguno. El periodo se lee
de una celda fecha o de un texto («Ene-2026», «enero 2026», «01/2026», «2026-01») y se guarda como
el primer dia del mes. Una fila mala se rechaza y se reporta; las demas siguen (UC-17 2b)."""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from adapters.bcv.formatos import FormatoMensual
from adapters.bcv.informe import (
    FormatoNoReconocido, InformeImportacion, Rechazo, SerieLeida, ValorLeido, validar_fuente)
from adapters.bcv.libro import Celda, Hoja, Libro

MESES = {
    "ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3, "abr": 4, "abril": 4,
    "may": 5, "mayo": 5, "jun": 6, "junio": 6, "jul": 7, "julio": 7, "ago": 8, "agosto": 8,
    "sep": 9, "sept": 9, "set": 9, "septiembre": 9, "setiembre": 9, "oct": 10, "octubre": 10,
    "nov": 11, "noviembre": 11, "dic": 12, "diciembre": 12,
}
_NOMBRE_Y_ANIO = re.compile(r"^([a-z]+)\.?[\s\-/]+(\d{4})$")
_MES_Y_ANIO = re.compile(r"^(\d{1,2})[/\-](\d{4})$")
_ANIO_Y_MES = re.compile(r"^(\d{4})[/\-](\d{1,2})$")
_NUMERO = re.compile(r"^\d+(\.\d+)?$")


def _sin_marca(texto: str, marca: str) -> str:
    return (texto.replace(marca, "") if marca else texto).strip()


def _mes(celda: Celda, marca: str) -> date | None:
    if isinstance(celda, date):
        return date(celda.year, celda.month, 1)
    if not isinstance(celda, str):
        return None
    texto = _sin_marca(celda, marca).casefold()
    if m := _NOMBRE_Y_ANIO.match(texto):
        mes, anio = MESES.get(m.group(1)), int(m.group(2))
    elif m := _MES_Y_ANIO.match(texto):
        mes, anio = int(m.group(1)), int(m.group(2))
    elif m := _ANIO_Y_MES.match(texto):
        anio, mes = int(m.group(1)), int(m.group(2))
    else:
        return None
    return date(anio, mes, 1) if mes is not None and 1 <= mes <= 12 else None


def _valor(celda: Celda, marca: str) -> Decimal | None:
    """`Decimal` de la celda: el de la cuadricula o el de un texto con punto decimal."""
    if isinstance(celda, Decimal):
        return celda
    if isinstance(celda, str) and _NUMERO.match(_sin_marca(celda, marca)):
        return Decimal(_sin_marca(celda, marca))
    return None


def _siguiente(mes: date) -> date:
    return date(mes.year + (mes.month == 12), mes.month % 12 + 1, 1)


def _hoja(libro: Libro, formato: FormatoMensual) -> Hoja:
    buscada = formato.hoja.strip().casefold()
    for hoja in libro.hojas:
        if hoja.nombre.strip().casefold() == buscada:
            return hoja
    raise FormatoNoReconocido(f"{libro.archivo}: falta la hoja «{formato.hoja}» del INPC")


def _columna(fila: tuple[Celda, ...], etiqueta: str) -> int | None:
    buscada = etiqueta.casefold()
    return next(
        (i for i, c in enumerate(fila) if isinstance(c, str) and buscada in c.casefold()), None
    )


def _encabezados(hoja: Hoja, formato: FormatoMensual, archivo: str) -> tuple[int, int, int]:
    """Fila de encabezados y columnas del periodo y del valor; el que falte se nombra."""
    for n, fila in enumerate(hoja.filas):
        periodo = _columna(fila, formato.etiqueta_periodo)
        if periodo is None:
            continue
        valor = _columna(fila, formato.etiqueta_valor)
        if valor is None:
            raise FormatoNoReconocido(
                f"{archivo}, hoja «{hoja.nombre}»: falta el encabezado «{formato.etiqueta_valor}»"
            )
        return n, periodo, valor
    raise FormatoNoReconocido(
        f"{archivo}, hoja «{hoja.nombre}»: falta el encabezado «{formato.etiqueta_periodo}»"
    )


def _celda(fila: tuple[Celda, ...], columna: int) -> Celda:
    return fila[columna] if columna < len(fila) else None


def leer_inpc(libro: Libro, *, fuente: str, fecha_descarga: date,
              formato: FormatoMensual) -> InformeImportacion:
    fuente = validar_fuente(fuente)
    hoja = _hoja(libro, formato)
    encabezado, col_periodo, col_valor = _encabezados(hoja, formato, libro.archivo)
    marca = formato.marca_provisional
    valores: list[ValorLeido] = []
    rechazos: list[Rechazo] = []
    leidas = 0
    for numero, fila in enumerate(hoja.filas[encabezado + 1:], start=encabezado + 2):
        celda_periodo, celda_valor = _celda(fila, col_periodo), _celda(fila, col_valor)
        if celda_periodo is None and celda_valor is None:
            continue
        leidas += 1
        lugar = f"{hoja.nombre}!{numero}"
        mes, valor = _mes(celda_periodo, marca), _valor(celda_valor, marca)
        anterior = valores[-1].fecha if valores else None
        motivo = (
            "mes ilegible" if mes is None
            else "mes repetido" if any(v.fecha == mes for v in valores)
            else "mes posterior a la descarga" if mes > fecha_descarga
            else "mes no consecutivo con el anterior" if anterior and mes != _siguiente(anterior)
            else "valor no numerico" if valor is None
            else "el valor debe ser mayor que cero" if valor <= 0
            else ""
        )
        if motivo:
            rechazos.append(Rechazo(lugar, motivo))
            continue
        provisional = bool(marca) and any(
            isinstance(c, str) and marca in c for c in (celda_periodo, celda_valor)
        )
        valores.append(ValorLeido(mes, valor, provisional, lugar))
    serie = SerieLeida("inpc_general", "INPC, indice general", "BCV-INE", "indice_bs", "mensual",
                       formato.base, tuple(valores))
    return InformeImportacion(libro.archivo, libro.huella, fuente, fecha_descarga, (serie,),
                              tuple(rechazos), tuple(libro.avisos), leidas)
```
```python
# adapters/bcv/csv_canonico.py
"""Respaldo por CSV canonico de series (spec S1 §7.3): `serie,fecha,valor,provisional,fuente`.

Para el indice de insumos de la construccion mientras su formato no este documentado, y para
cualquier serie si el BCV cambia el formato. Las mismas validaciones de fecha, valor y repeticion
que los lectores de .xls; la fuente es obligatoria por fila. Nombre, organismo, unidad y
periodicidad de cada serie los declara la interfaz al confirmar (`ui.indices.confirmar`,
`definiciones_csv`)."""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from adapters.bcv.informe import (
    FormatoNoReconocido, InformeImportacion, Rechazo, SerieLeida, ValorLeido)
from adapters.bcv.libro import LIMITE_BYTES

COLUMNAS_CSV = ("serie", "fecha", "valor", "provisional", "fuente")
_PROVISIONAL = {"si": True, "sí": True, "no": False, "": False}


def _valor(texto: str) -> Decimal | str:
    """El valor de la fila o, si no vale, el motivo del rechazo (nunca pasa por `float`)."""
    if "," in texto:
        return f"{texto!r} lleva coma; use punto como separador decimal"
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return f"valor {texto!r} no numerico"
    if not valor.is_finite():
        return f"valor {texto!r} no numerico"
    return valor if valor > 0 else "el valor debe ser mayor que cero"


def _fecha(texto: str) -> date | None:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


def leer_csv_canonico(ruta: Path, *, fecha_descarga: date) -> InformeImportacion:
    tamano = ruta.stat().st_size
    if tamano > LIMITE_BYTES:
        raise FormatoNoReconocido(f"{ruta.name}: pesa {tamano / 2**20:.1f} MB; el limite es 20 MB")
    contenido = ruta.read_bytes()
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise FormatoNoReconocido(f"{ruta.name}: el CSV debe estar en UTF-8") from None
    lector = csv.DictReader(io.StringIO(texto, newline=""))
    columnas = tuple((c or "").strip().lower() for c in lector.fieldnames or ())
    if columnas != COLUMNAS_CSV:
        faltan = [c for c in COLUMNAS_CSV if c not in columnas]
        raise FormatoNoReconocido(
            f"{ruta.name}: las columnas deben ser exactamente {', '.join(COLUMNAS_CSV)}"
            + (f"; faltan {', '.join(faltan)}" if faltan else "")
        )
    lector.fieldnames = list(COLUMNAS_CSV)
    valores: dict[str, list[ValorLeido]] = {}
    rechazos: list[Rechazo] = []
    vistas: set[tuple[str, date]] = set()
    fuentes: list[str] = []
    leidas = 0
    for numero, fila in enumerate(lector, start=2):
        leidas += 1
        lugar = f"{ruta.name}:{numero}"
        celda = {c: (fila.get(c) or "").strip() for c in COLUMNAS_CSV}
        fecha, valor = _fecha(celda["fecha"]), _valor(celda["valor"])
        provisional = _PROVISIONAL.get(celda["provisional"].casefold())
        motivo = (
            "la serie no puede estar vacia" if not celda["serie"]
            else f"fecha {celda['fecha']!r} no es AAAA-MM-DD" if fecha is None
            else "fecha posterior a la descarga" if fecha > fecha_descarga
            else valor if isinstance(valor, str)
            else "provisional debe ser si, no o vacio" if provisional is None
            else "la fuente es obligatoria por fila" if not celda["fuente"]
            else "(serie, fecha) repetido" if (celda["serie"], fecha) in vistas
            else ""
        )
        if motivo:
            rechazos.append(Rechazo(lugar, motivo))
            continue
        vistas.add((celda["serie"], fecha))
        fuentes.append(celda["fuente"])
        valores.setdefault(celda["serie"], []).append(
            ValorLeido(fecha, valor, provisional, lugar)
        )
    series = tuple(SerieLeida(clave, clave, "", "", "", "", tuple(lista))
                   for clave, lista in valores.items())
    return InformeImportacion(ruta.name, hashlib.sha256(contenido).hexdigest(),
                              "; ".join(dict.fromkeys(fuentes)), fecha_descarga, series,
                              tuple(rechazos), (), leidas)
```
```python
# adapters/bcv/formatos.py
"""Los formatos del BCV que S1-0 verifico abriendo los archivos reales (spec S1 §7.1): la letra de
cada trimestre en el nombre del archivo de la tasa y la hoja, los encabezados, la marca y la base
del INPC. `formatos.json` (junto a este modulo) es copia literal de la tabla «Formatos para
`adapters/bcv/formatos.json`» de `docs/fuentes/bcv_formatos.md`; lo comprueba
`tests/unit/adapters/test_bcv_inpc.py::test_formatos_json_copia_bcv_formatos_md`. Si el BCV cambia
un formato, se corrige la tabla, se regenera el JSON y se vuelve a transcribir `FUENTE.md`.

`FormatoMensual` vive aqui (y `inpc` lo importa) para que este modulo entre con el lector de la tasa
sin arrastrar el del INPC, que llega despues de su prueba (C3 de la meta)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from adapters.bcv.informe import FormatoNoReconocido

RUTA_FORMATOS = Path(__file__).with_name("formatos.json")


@dataclass(frozen=True, slots=True)
class FormatoMensual:
    """Donde estan, en el archivo mensual, el periodo y el valor (`bcv_formatos.md`)."""

    hoja: str
    etiqueta_periodo: str
    etiqueta_valor: str
    marca_provisional: str = "(*)"
    base: str = ""


@dataclass(frozen=True, slots=True)
class Formatos:
    trimestre_por_letra: dict[str, int]
    inpc: FormatoMensual


def cargar_formatos() -> Formatos:
    datos = json.loads(RUTA_FORMATOS.read_text(encoding="utf-8"))
    letras = {
        str(letra).lower(): int(n) for letra, n in datos["tasa"]["trimestre_por_letra"].items()
    }
    if sorted(letras.values()) != [1, 2, 3, 4]:
        raise FormatoNoReconocido(f"{RUTA_FORMATOS.name}: cada trimestre 1 a 4 necesita su letra")
    inpc = datos["inpc"]
    return Formatos(letras, FormatoMensual(inpc["hoja"], inpc["etiqueta_periodo"],
                                           inpc["etiqueta_valor"], inpc["marca_provisional"],
                                           inpc["base"]))
```
  `adapters/bcv/formatos.json` no se escribe a mano: se **genera** de la tabla de `docs/fuentes/bcv_formatos.md` (Tarea 3), así no puede cambiar una letra. Desde la raíz del worktree, en Git Bash:
```bash
uv run python - <<'EOF'
import json
import re
from pathlib import Path

texto = Path("docs/fuentes/bcv_formatos.md").read_text(encoding="utf-8")
seccion = texto.split("## Formatos para `adapters/bcv/formatos.json`")[1].split("\n## ")[0]
datos = {}
for clave, valor in re.findall(r"^\| `([a-z_.]+)` \| `(.+)` \|$", seccion, re.M):
    grupo, nombre = clave.split(".", 1)
    datos.setdefault(grupo, {})[nombre] = json.loads(valor)
Path("adapters/bcv/formatos.json").write_text(
    json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
EOF
```
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/unit/adapters tests/unit/test_arquitectura.py -q -W error`; `uv run ruff check adapters/bcv tests/unit/adapters tests/fixtures/bcv_cuadriculas.py`; `uv run python scripts/guardia_nucleo.py --base origin/main` (0: la rama no toca `core/`).
- [ ] **Paso 5: Commit** (por intérprete: prueba y luego código; ejemplo de la tasa)
```bash
git add tests/unit/adapters/__init__.py tests/unit/adapters/test_bcv_libro.py tests/unit/adapters/test_bcv_tasa.py tests/fixtures/bcv_cuadriculas.py
git commit -m "test(bcv): libro y tasa contra la transcripcion a mano en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add adapters/bcv/__init__.py adapters/bcv/informe.py adapters/bcv/libro.py adapters/bcv/tasa.py adapters/bcv/formatos.py adapters/bcv/formatos.json tests/unit/test_arquitectura.py
git commit -m "feat(bcv): cuadricula neutra y lector de la tasa trimestral" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add tests/unit/adapters/test_bcv_inpc.py
git commit -m "test(bcv): lector del INPC contra la transcripcion a mano en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add adapters/bcv/inpc.py
git commit -m "feat(bcv): lector del INPC mensual con marca de provisional" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add tests/unit/adapters/test_bcv_csv.py
git commit -m "test(bcv): CSV canonico de series en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add adapters/bcv/csv_canonico.py
git commit -m "feat(bcv): CSV canonico de series con fuente por fila" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin inc/060-s1-2-bcv
gh pr create --base main --head inc/060-s1-2-bcv --title "S1-2: adaptador del BCV" --body-file -
```
  (Cada par prueba → intérprete es un `ParTDD` de `S1-2` en `scripts/meta_silice_s1.py`: el commit de la prueba va siempre antes.)
**Compuerta GS1‑2:** `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S1-2 --junit reporte-pruebas.xml` en OK (C3 con los cuatro `ParTDD` del BCV; `S1-FUENTE` con el intérprete ya presente), CI verde, revisión de los encargos; fusionar `inc/060-s1-2-bcv` con `--merge` (si S1‑1 aún no está en `main`, la compuerta se mide con `--hasta S1-0` más `uv run pytest tests/unit/adapters -W error`, el paso de la CI se queda en `S1-0` y lo sube a `S1-2` el PR de S1‑1).

---

# S1‑3 — SL‑E2 (núcleo `inc/060-s1-3-nucleo`; luego interfaz `inc/060-s1-3-ui`)

### Tarea 7: SL‑E2a — lista de empresa, lista de referencia, lector y `lista_vigente`

**Rama:** `inc/060-s1-3-nucleo` (solo núcleo; sale de `main` con S1‑1 fusionado)   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/catalog/empresa.py`, `migraciones/caso/versions/caso_0003_s1_lista_empresa.py`, `tests/integration/test_lista_empresa.py`
- Modificar: `core/models/entidades.py:556-558` (`ALCANCE_EMPRESA = "empresa"`, `ALCANCE_REFERENCIA = "referencia"`, `ALCANCES_FUERA_DE_VIGENTE`), `core/models/moneda.py` (`ListaEmpresa`), `core/models/__init__.py`, `core/catalog/repositorio.py:101-120` (`lista_vigente`), `core/catalog/precios.py:92-100,246-304` (columnas opcionales y mensaje de coma decimal), `core/catalog/__init__.py`, `docs/bitacora/2026-10-silice-expedientes.md` (SL‑E2)

**Interfaces:**
- Produce: `models.ListaEmpresa(lista_id, empresa_nombre, empresa_rif, lista_base_id, lista_referencia_id, plazo_vigencia_dias, rango_inferior, rango_superior)`; `PrecioLeido` gana al final `fecha: date | None = None`, `fuente: str = ""`, `referencia: str = ""`, `moneda: str = ""`, `tasa: Decimal | None = None`, `fecha_tasa: date | None = None`, `fuente_tasa: str = ""`; `core.catalog.empresa`: `RANGO_INFERIOR = Decimal("-0.20")`, `RANGO_SUPERIOR = Decimal("0.30")` (S1‑R5), `PLAZO_VIGENCIA_DIAS = 30` (S1‑R6), `PrecioPropio(insumo_id, precio, fecha, fuente, referencia="", moneda_original="", tasa=None, fecha_tasa=None, fuente_tasa="")`, `precios_propios_desde(session, leidos) -> tuple[list[PrecioPropio], list[PrecioLeido]]`, `crear_lista_de_empresa(session, empresa_nombre, empresa_rif, base, precios_propios, *, moneda, fecha, fuente, referencia, nombre=None, tasa_base=None, plazo_vigencia_dias=PLAZO_VIGENCIA_DIAS, rango_inferior=RANGO_INFERIOR, rango_superior=RANGO_SUPERIOR) -> models.ListaPrecios`, `crear_lista_de_referencia(session, ruta, *, nombre, moneda, tasa: TasaDeclarada) -> models.ListaPrecios`, `lista_de_referencia(session) -> models.ListaPrecios | None`, `es_heredado(session, lista, precio) -> bool | None`.

- [ ] **Paso 0: Expediente SL‑E2** (S1 §11: H‑D8, RF‑67, RF‑68; una lista global de empresa secuestraría `lista_vigente`; genérico para cualquier especialidad; prueba = memoria de precios de empresa y `lista_vigente`; impacto: `lista_vigente` excluye dos alcances más —`empresa` y `referencia`, ver Discrepancias 4—, el lector acepta columnas opcionales, R11/R12 fuera de `REGLAS`; costo si es erróneo). Commit `docs(bitacora): expediente SL-E2`.
- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/integration/test_lista_empresa.py
"""RF‑67 y UC‑17 4 (S1 §6.1, §9.2)."""
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from core import models
from core.catalog import Catalogo, CatalogoIncompleto, leer_lista_precios
from core.catalog.empresa import (
    crear_lista_de_empresa, crear_lista_de_referencia, es_heredado, precios_propios_desde)
from core.catalog.moneda import TasaDeclarada
from scripts.lista_maprex_bs import FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX, RUTA_SALIDA, TASA_MAPREX
from tests.fixtures.apu_linea_base import APU_EXCAVACION

CSV_EMPRESA = Path(__file__).resolve().parents[1] / "fixtures" / "precios_empresa_s1.csv"


@pytest.fixture
def referencia(sesion):
    lista = crear_lista_de_referencia(
        sesion, RUTA_SALIDA, nombre="MaPreX julio 2026 en Bs", moneda="Bs",
        tasa=TasaDeclarada(TASA_MAPREX, FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX))
    Catalogo(sesion).dar_de_alta_insumo(models.TipoInsumo.MATERIAL, "LIJA DE AGUA N 100", "pza")
    return lista


def _empresa(sesion, referencia, nombre="Constructora Ejemplo, C.A.", rif="J-00000000-0"):
    propios, desconocidos = precios_propios_desde(sesion, leer_lista_precios(CSV_EMPRESA))
    assert not desconocidos
    return crear_lista_de_empresa(sesion, nombre, rif, referencia, propios, moneda="Bs",
                                  fecha=date(2026, 9, 20), fuente="lista interna 2026-09",
                                  referencia=referencia)


def test_ni_la_empresa_ni_la_referencia_entran_a_lista_vigente(sesion, referencia):
    _empresa(sesion, referencia)
    assert Catalogo(sesion).lista_vigente(date(2031, 1, 1)).moneda == "USD"  # la de la clínica


def test_propio_prevalece_heredado_marcado_y_empresa_como_texto(sesion, referencia):
    lista = _empresa(sesion, referencia)
    precios = {p.insumo.descripcion: p for p in lista.precios}
    assert precios["ARENA LAVADA"].precio == D("49078.775")
    assert es_heredado(sesion, lista, precios["MATERIAL GRANULAR INTEGRAL"]) is True
    assert es_heredado(sesion, lista, precios["ARENA LAVADA"]) is False
    fila = sesion.get(models.ListaEmpresa, lista.id)
    assert (fila.empresa_nombre, fila.empresa_rif, fila.rango_inferior) == (
        "Constructora Ejemplo, C.A.", "J-00000000-0", D("-0.20"))
    pegamento = precios["PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM"]
    origen = sesion.get(models.PrecioOrigen, pegamento.id)
    assert (pegamento.precio, origen.moneda_original, origen.fecha_tasa) == (D("21000.00"), "USD", None)


def test_dos_empresas_aisladas(sesion, referencia):
    una = _empresa(sesion, referencia)
    otra = _empresa(sesion, referencia, "Otra, S.A.", "J-11111111-1")
    assert {p.id for p in una.precios}.isdisjoint({p.id for p in otra.precios})


def test_coma_decimal_se_rechaza_con_fila_y_motivo(tmp_path):
    """[Foco 4] «13288,00» o «13.288,00» nunca se leen como otro número."""
    ruta = tmp_path / "coma.csv"
    ruta.write_text("tipo,insumo,unidad,precio\nmaterial,ARENA LAVADA,m3,\"13.288,00\"\n",
                    encoding="utf-8")
    with pytest.raises(ValueError, match=r"fila 2.*punto"):
        leer_lista_precios(ruta)


def test_moneda_ajena_se_rechaza(sesion, referencia):
    with pytest.raises(ValueError, match="4b"):
        crear_lista_de_empresa(sesion, "X", "J-1", referencia, [], moneda="EUR",
                               fecha=date(2026, 9, 20), fuente="x", referencia=referencia)


def test_insumo_sin_precio_en_la_moneda_de_la_lista_no_valora(sesion, referencia):
    """[Foco 5] una partida de la clínica valorada con la lista de empresa en Bs: el insumo que la
    base no trae da CatalogoIncompleto que lo nombra, sin escribir nada."""
    lista = _empresa(sesion, referencia)
    with pytest.raises(CatalogoIncompleto, match=lista.nombre):
        Catalogo(sesion).composicion(APU_EXCAVACION.codigo_partida, lista=lista)  # "LB-01-EXC"
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/integration/test_lista_empresa.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.catalog.empresa'`
- [ ] **Paso 3: Implementación mínima**
```python
# core/models/entidades.py:556-558 — tras ALCANCE_PROYECTO
ALCANCE_EMPRESA = "empresa"  # SL‑E2: la lista de una empresa (S1 §6.1)
ALCANCE_REFERENCIA = "referencia"  # SL‑E2: MaPreX en Bs, solo para contrastar con R11 (S1 §6.2)
#: Alcances que `Catalogo.lista_vigente` nunca resuelve: una versión los referencia explícitamente.
ALCANCES_FUERA_DE_VIGENTE = (ALCANCE_PROYECTO, ALCANCE_EMPRESA, ALCANCE_REFERENCIA)
```
```python
# core/catalog/repositorio.py:101-120 — lista_vigente
    def lista_vigente(self, fecha: date | None = None) -> models.ListaPrecios:
        """La lista global de mayor `fecha_vigencia` menor o igual a `fecha` (hoy, sin `fecha`).

        Las listas de proyecto (cotizaciones, SF‑E7), de empresa y de referencia (SL‑E2) no se
        resuelven aquí: una versión las referencia explícitamente (DA‑SF‑9).
        """
        limite = fecha if fecha is not None else date.today()
        fuera_de_vigente = exists().where(
            models.ListaPreciosOrigen.lista_id == models.ListaPrecios.id,
            models.ListaPreciosOrigen.alcance.in_(models.ALCANCES_FUERA_DE_VIGENTE),
        )
        lista = self._sesion.scalars(
            select(models.ListaPrecios)
            .where(models.ListaPrecios.fecha_vigencia <= limite, ~fuera_de_vigente)
            .order_by(models.ListaPrecios.fecha_vigencia.desc(), models.ListaPrecios.id.desc())
            .limit(1)
        ).one_or_none()
        if lista is None:
            raise CatalogoIncompleto(f"no hay ninguna lista de precios vigente al {limite}")
        return lista
```
```python
# core/models/moneda.py — al final (SL‑E2)
class ListaEmpresa(Base):
    """SL‑E2: la lista de una empresa (S1 §6.1). La empresa es texto (RV‑6): una instantánea sin
    clave foránea a `instalacion.db`; S3 la rellena desde la empresa propia."""

    __tablename__ = "lista_empresa"

    lista_id: Mapped[int] = mapped_column(
        ForeignKey("lista_precios.id", ondelete="CASCADE"), primary_key=True
    )
    empresa_nombre: Mapped[str] = mapped_column(String(200))
    empresa_rif: Mapped[str] = mapped_column(String(20))
    lista_base_id: Mapped[int] = mapped_column(ForeignKey("lista_precios.id"))
    lista_referencia_id: Mapped[int | None] = mapped_column(
        ForeignKey("lista_precios.id"), default=None
    )
    plazo_vigencia_dias: Mapped[int] = mapped_column(Integer)
    rango_inferior: Mapped[Decimal] = mapped_column(DecimalExacto)
    rango_superior: Mapped[Decimal] = mapped_column(DecimalExacto)
```
  En `core/models/__init__.py`: `ALCANCE_EMPRESA`, `ALCANCE_REFERENCIA` y `ALCANCES_FUERA_DE_VIGENTE` en la importación de `core.models.entidades`, `ListaEmpresa` en la de `core.models.moneda`, y los cuatro nombres en `__all__` (orden alfabético).
```python
# migraciones/caso/versions/caso_0003_s1_lista_empresa.py
"""S1‑3 (SL‑E2): la lista de precios de una empresa."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0003_s1_lista_empresa"
down_revision = "caso_0002_s1_moneda"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def upgrade() -> None:
    op.create_table(
        "lista_empresa",
        sa.Column("lista_id", sa.Integer,
                  sa.ForeignKey("lista_precios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("empresa_nombre", sa.String(200), nullable=False),
        sa.Column("empresa_rif", sa.String(20), nullable=False),
        sa.Column("lista_base_id", sa.Integer, sa.ForeignKey("lista_precios.id"), nullable=False),
        sa.Column("lista_referencia_id", sa.Integer, sa.ForeignKey("lista_precios.id"),
                  nullable=True),
        sa.Column("plazo_vigencia_dias", sa.Integer, nullable=False),
        sa.Column("rango_inferior", DEC, nullable=False),
        sa.Column("rango_superior", DEC, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lista_empresa")
```
```python
# core/catalog/precios.py — `PrecioLeido` (:92-100) gana al final, con valor por defecto
    fecha: date | None = None
    fuente: str = ""
    referencia: str = ""
    moneda: str = ""
    tasa: Decimal | None = None
    fecha_tasa: date | None = None
    fuente_tasa: str = ""
```
```python
# core/catalog/precios.py — tras COLUMNAS_ARCHIVO
#: Columnas opcionales de una lista de empresa (UC‑17 4; RF‑67): por precio, su fecha y su fuente,
#: el Ref de MaPreX y, si el precio se convirtió, su moneda original y la tasa con fecha y fuente.
COLUMNAS_OPCIONALES = ("fecha", "fuente", "referencia", "moneda", "tasa", "fecha_tasa",
                       "fuente_tasa")
```
```python
# core/catalog/precios.py:246-304 — `_a_precio_leido`, `_a_fecha` (nueva) y el inicio de `_a_precio`
def _a_precio_leido(fila: dict[str, object], numero: int, ruta: Path) -> PrecioLeido:
    descripcion = _texto(fila["insumo"])
    if not descripcion:
        raise ValueError(f"{ruta.name}, fila {numero}: la columna insumo está vacía")
    unidad = _texto(fila["unidad"])
    opcional = {columna: _texto(fila.get(columna, "")) for columna in COLUMNAS_OPCIONALES}
    return PrecioLeido(
        tipo=_a_tipo(_texto(fila["tipo"]), numero, ruta),
        descripcion=descripcion,
        unidad=normalizar_unidad(unidad) if unidad else None,
        precio=_a_precio(_texto(fila["precio"]), numero, ruta),
        fecha=_a_fecha(opcional["fecha"], "fecha", numero, ruta),
        fuente=opcional["fuente"],
        referencia=opcional["referencia"],
        moneda=opcional["moneda"],
        tasa=_a_precio(opcional["tasa"], numero, ruta) if opcional["tasa"] else None,
        fecha_tasa=_a_fecha(opcional["fecha_tasa"], "fecha_tasa", numero, ruta),
        fuente_tasa=opcional["fuente_tasa"],
    )


def _a_fecha(valor: str, campo: str, numero: int, ruta: Path) -> date | None:
    """Una fecha AAAA-MM-DD (una celda fecha del XLSX llega como `2026-09-20 00:00:00`)."""
    if not valor:
        return None
    try:
        return date.fromisoformat(valor.split(" ")[0].split("T")[0])
    except ValueError:
        raise ValueError(
            f"{ruta.name}, fila {numero}: {campo} {valor!r} no es una fecha AAAA-MM-DD"
        ) from None


def _a_precio(valor: str, numero: int, ruta: Path) -> Decimal:
    # [Foco 4] `13.288,00` o `1,5` nunca se leen como otro número: la coma se rechaza por su nombre.
    if "," in valor:
        raise ValueError(
            f"{ruta.name}, fila {numero}: {valor!r} lleva coma; use punto como separador "
            "decimal (1234.56)"
        )
    try:
        precio = Decimal(valor)
    except InvalidOperation as error:
        raise ValueError(
            f"{ruta.name}, fila {numero}: el precio {valor!r} no es un número decimal"
        ) from error
    # `is_finite()` va primero y en la misma condicion: `Decimal("nan") < 0` lanzaria
    # `InvalidOperation` (un `ArithmeticError`, no el `ValueError` que promete el docstring de
    # `leer_lista_precios`) y `Decimal("Infinity") < 0` es `False`, asi que un precio infinito
    # entraria a la lista en silencio.
    if not precio.is_finite() or precio < 0:
        raise ValueError(
            f"{ruta.name}, fila {numero}: el precio {valor} no es un numero no negativo"
        )
    return precio
```
```python
# core/catalog/empresa.py
"""SL‑E2: lista de precios de una empresa y lista de referencia (spec S1 §6). No hace `commit`."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.catalog.moneda import TasaDeclarada, convertir, copiar_precios, exigir_moneda
from core.catalog.origen import origenes_efectivos
from core.catalog.precios import PrecioLeido, _clave, _insumos_por_clave, leer_lista_precios
from core.catalog.repositorio import Catalogo

RANGO_INFERIOR = Decimal("-0.20")  # S1‑R5, por analogía con AACE clase 3
RANGO_SUPERIOR = Decimal("0.30")
PLAZO_VIGENCIA_DIAS = 30  # S1‑R6, SUPUESTO_DECLARADO


@dataclass(frozen=True, slots=True)
class PrecioPropio:
    insumo_id: int
    precio: Decimal
    fecha: date
    fuente: str
    referencia: str = ""
    moneda_original: str = ""
    tasa: Decimal | None = None
    fecha_tasa: date | None = None
    fuente_tasa: str = ""


def precios_propios_desde(session, leidos: Sequence[PrecioLeido]):
    """Las filas del archivo como precios propios (todas las variantes homónimas, como UC‑02)."""
    indice = _insumos_por_clave(session)
    propios, desconocidos = [], []
    for leido in leidos:
        variantes = indice.get(_clave(leido.tipo.value, leido.descripcion, leido.unidad))
        if not variantes:
            desconocidos.append(leido)
            continue
        if leido.fecha is None or not leido.fuente.strip():
            raise ValueError(f"{leido.descripcion}: el precio propio exige fecha y fuente (RF-67)")
        propios += [PrecioPropio(i.id, leido.precio, leido.fecha, leido.fuente, leido.referencia,
                                 leido.moneda, leido.tasa, leido.fecha_tasa, leido.fuente_tasa)
                    for i in variantes]
    return propios, desconocidos


def crear_lista_de_empresa(
    session: Session, empresa_nombre: str, empresa_rif: str, base: models.ListaPrecios,
    precios_propios: Sequence[PrecioPropio], *, moneda: str, fecha: date, fuente: str,
    referencia: models.ListaPrecios | None, nombre: str | None = None,
    tasa_base: TasaDeclarada | None = None, plazo_vigencia_dias: int = PLAZO_VIGENCIA_DIAS,
    rango_inferior: Decimal = RANGO_INFERIOR, rango_superior: Decimal = RANGO_SUPERIOR,
) -> models.ListaPrecios:
    """Copia de `base` (convertida con `tasa_base` si su moneda difiere) con los propios encima."""
    if moneda not in ("Bs", "USD"):
        raise ValueError(f"moneda {moneda!r}: la lista se rechaza (UC-17 4b)")
    if not empresa_nombre.strip() or not empresa_rif.strip() or not fuente.strip():
        raise ValueError("la empresa (nombre y RIF) y la fuente de la lista son obligatorias")
    lista = models.ListaPrecios(nombre=(nombre or f"{empresa_nombre} {fecha:%Y-%m-%d}")[:120],
                                moneda=moneda, fecha_vigencia=fecha, origen=fuente[:200])
    session.add(lista)
    session.flush()
    session.add(models.ListaPreciosOrigen(lista_id=lista.id, alcance=models.ALCANCE_EMPRESA,
                                          lista_base_id=base.id))
    copiar_precios(session, base, lista, tasa_base,
                   excluir={p.insumo_id for p in precios_propios})
    for p in precios_propios:
        original = exigir_moneda(p.moneda_original or moneda)
        if original != moneda and p.tasa is None:
            raise ValueError(f"insumo {p.insumo_id}: precio en {original} sin tasa a {moneda}")
        valor = p.precio if original == moneda else convertir(p.precio, original, moneda, p.tasa)
        fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=p.insumo_id, precio=valor)
        session.add(fila)
        session.flush()
        session.add(models.PrecioOrigen(
            precio_id=fila.id, moneda_original=original, precio_original=p.precio,
            fecha_precio=p.fecha, tasa=p.tasa, fecha_tasa=p.fecha_tasa,
            fuente_tasa=p.fuente_tasa, fuente=p.fuente))
        if p.referencia.strip():
            session.add(models.ReferenciaPrecio(precio_id=fila.id, referencia=p.referencia.strip()))
    session.add(models.ListaEmpresa(
        lista_id=lista.id, empresa_nombre=empresa_nombre.strip(), empresa_rif=empresa_rif.strip(),
        lista_base_id=base.id, lista_referencia_id=referencia.id if referencia else None,
        plazo_vigencia_dias=plazo_vigencia_dias, rango_inferior=rango_inferior,
        rango_superior=rango_superior))
    session.flush()
    session.expire(lista, ["precios"])
    return lista


def crear_lista_de_referencia(session, ruta: Path, *, nombre: str, moneda: str,
                              tasa: TasaDeclarada) -> models.ListaPrecios:
    """Lista de alcance `referencia` (p. ej. MaPreX en Bs): da de alta los insumos que falten
    (decisión explícita del administrador al cargarla) y guarda Ref, fecha y tasa por precio."""
    leidos = leer_lista_precios(ruta)
    catalogo = Catalogo(session)
    indice = _insumos_por_clave(session)
    lista = models.ListaPrecios(nombre=nombre[:120], moneda=exigir_moneda(moneda),
                                fecha_vigencia=max(l.fecha for l in leidos), origen=ruta.name)
    session.add(lista)
    session.flush()
    session.add(models.ListaPreciosOrigen(lista_id=lista.id, tasa=tasa.valor,
                                          fecha_tasa=tasa.fecha,
                                          alcance=models.ALCANCE_REFERENCIA))
    for leido in leidos:
        clave = _clave(leido.tipo.value, leido.descripcion, leido.unidad)
        insumo = (indice.get(clave) or [None])[0] or catalogo.dar_de_alta_insumo(
            leido.tipo, leido.descripcion, leido.unidad)
        indice[clave] = [insumo]
        fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=leido.precio)
        session.add(fila)
        session.flush()
        session.add(models.PrecioOrigen(precio_id=fila.id, moneda_original=moneda,
                                        precio_original=leido.precio, fecha_precio=leido.fecha,
                                        tasa=tasa.valor, fecha_tasa=tasa.fecha,
                                        fuente_tasa=tasa.fuente, fuente=leido.fuente))
        if leido.referencia:
            session.add(models.ReferenciaPrecio(precio_id=fila.id, referencia=leido.referencia))
    session.flush()
    session.expire(lista, ["precios"])
    return lista


def lista_de_referencia(session: Session) -> models.ListaPrecios | None:
    return session.scalars(
        select(models.ListaPrecios).join(
            models.ListaPreciosOrigen, models.ListaPreciosOrigen.lista_id == models.ListaPrecios.id)
        .where(models.ListaPreciosOrigen.alcance == models.ALCANCE_REFERENCIA)
        .order_by(models.ListaPrecios.id.desc()).limit(1)).one_or_none()


def es_heredado(session, lista: models.ListaPrecios, precio: models.PrecioInsumo) -> bool | None:
    """`None` si la lista no es de empresa. Heredado = mismo insumo en la base con igual moneda y
    precio originales, fecha y fuente (la tasa puede diferir si la base se convirtió)."""
    fila = session.get(models.ListaEmpresa, lista.id)
    if fila is None:
        return None
    base = session.get(models.ListaPrecios, fila.lista_base_id)
    en_base = {p.insumo_id: p for p in base.precios}
    if precio.insumo_id not in en_base:
        return False
    propio = origenes_efectivos(session, lista)[precio.id]
    de_base = origenes_efectivos(session, base)[en_base[precio.insumo_id].id]
    campos = ("moneda_original", "precio_original", "fecha_precio", "fuente")
    return all(getattr(propio, c) == getattr(de_base, c) for c in campos)
```
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/integration/test_lista_empresa.py tests/integration/test_actualizacion_precios.py tests/integration/test_cotizacion_proyecto.py tests/unit/test_lista_maprex_usd.py -q -W error`; `uv run pytest -q -W error`; `uv run ruff check core tests/integration/test_lista_empresa.py migraciones`.
- [ ] **Paso 5: Commit**
```bash
git add tests/integration/test_lista_empresa.py
git commit -m "test(core): SL-E2 lista de empresa y lector con columnas opcionales en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add core/catalog/empresa.py core/catalog/precios.py core/catalog/repositorio.py core/catalog/__init__.py core/models/entidades.py core/models/moneda.py core/models/__init__.py migraciones/caso/versions/caso_0003_s1_lista_empresa.py
git commit -m "feat(core): SL-E2 lista de empresa y de referencia fuera de lista_vigente" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Tarea 8: SL‑E2b — R11, R12 e instantánea de precios

**Rama:** `inc/060-s1-3-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/verification/precios.py`, `tests/integration/test_precios_empresa.py`, `tests/unit/test_reglas_precios.py`, `tests/fixtures/precios_empresa_s1.py`
- Modificar: `core/catalog/empresa.py` (`instantanea_de_lista`), `core/budget/instantanea.py` (`instantanea_precios`), `core/budget/__init__.py`

**Interfaces:**
- Consume: Tareas 4, 5, 7.
- Produce: `core.verification.precios`: `CODIGO_R11 = "R11"`, `CODIGO_R12 = "R12"`, `PrecioAuditado`, `PartidaPrecios(codigo, cantidad, composicion, insumos)`, `InstantaneaPrecios(fecha_evaluacion, moneda, precios, tasa_evaluacion, rango_inferior, rango_superior, plazo_vigencia_dias, partidas=(), parametros=ParametrosCosto())`, `PrecioFueraDeRango(instantanea)` (R11), `PrecioVencido(instantanea)` (R12), `reglas_precios(inst) -> tuple[ReglaVerificacion, ...]`, `estado_por_insumo(inst) -> dict[int, list[str]]`. `core.catalog.empresa.instantanea_de_lista(session, lista, referencia, fecha_evaluacion, *, insumos=None, lado=LADO_POR_DEFECTO) -> InstantaneaPrecios`. `core.budget.instantanea.instantanea_precios(session, version, referencia, fecha_evaluacion, *, lado=LADO_POR_DEFECTO) -> InstantaneaPrecios`.

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/fixtures/precios_empresa_s1.py
"""Caso de la memoria s1_precios_empresa.md: referencia, lista de empresa, tasa y versión en Bs."""
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto
from core.catalog import Catalogo, leer_lista_precios
from core.catalog.empresa import crear_lista_de_empresa, crear_lista_de_referencia, precios_propios_desde
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from core.catalog.moneda import TasaDeclarada
from core.contracts import ComposicionAPU, Dominio, ItemComputo, LineaMaterial, ParametrosCosto
from core.contracts.item_computo import OrigenTipo
from scripts.lista_maprex_bs import FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX, RUTA_SALIDA, TASA_MAPREX

CSV = Path(__file__).resolve().parent / "precios_empresa_s1.csv"
EVALUACION = date(2026, 10, 1)
PARAMETROS = ParametrosCosto(fcas=D(0), bono_alimentacion=D(0), administracion=D("0.15"),
                             utilidad=D("0.10"))
GRANULAR = "MATERIAL GRANULAR INTEGRAL"


def sembrar(sesion):
    referencia = crear_lista_de_referencia(
        sesion, RUTA_SALIDA, nombre="MaPreX julio 2026 en Bs", moneda="Bs",
        tasa=TasaDeclarada(TASA_MAPREX, FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX))
    Catalogo(sesion).dar_de_alta_insumo(models.TipoInsumo.MATERIAL, "LIJA DE AGUA N 100", "pza")
    propios, _ = precios_propios_desde(sesion, leer_lista_precios(CSV))
    lista = crear_lista_de_empresa(sesion, "Constructora Ejemplo, C.A.", "J-00000000-0",
                                   referencia, propios, moneda="Bs", fecha=date(2026, 9, 20),
                                   fuente="lista interna 2026-09", referencia=referencia)
    registrar_importacion(sesion, definicion_tasa("venta"),
                          [Observacion(EVALUACION, D("860.18"))], archivo="FUENTE.md",
                          huella="c" * 64, fuente="https://www.bcv.org.ve/", responsable="A",
                          fecha_descarga=date(2026, 10, 8), filas_leidas=1, filas_rechazadas=0)
    usados = {p.insumo.descripcion: p for p in lista.precios}
    descripciones = [l["insumo"] for l in _filas()] + [GRANULAR]
    lineas = tuple(LineaMaterial(d, usados[d].insumo.unidad, D(1), usados[d].precio)
                   for d in descripciones)
    sesion.add(models.Partida(codigo="S1-EMP-01", descripcion="Partida de prueba de precios",
                              unidad="m2", dominio="civil"))
    composicion = ComposicionAPU("S1-EMP-01", "Partida de prueba de precios", "m2", D(1), lineas)
    item = ItemComputo("S1-EMP-01", "Partida de prueba", "m2", D(10), "memoria-s1",
                       OrigenTipo.MANUAL, Dominio.CIVIL)
    resultado = elaborar([item], {"S1-EMP-01": composicion}, PARAMETROS, codigo="001",
                         fecha=date(2026, 9, 20), moneda="Bs")
    proyecto = crear_proyecto(sesion, "Precios de empresa S1")
    version = guardar_presupuesto(sesion, resultado.presupuesto, resultado.informe,
                                  proyecto=proyecto, lista=lista, parametros=PARAMETROS)
    return referencia, lista, version


def _filas():
    import csv
    with CSV.open(encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))
```
```python
# tests/integration/test_precios_empresa.py
"""RF‑68: conjunto EXACTO de tests/fixtures/memorias/s1_precios_empresa.md a 2026‑10‑01."""
from datetime import date
from decimal import Decimal as D

from sqlalchemy import select

from core import models
from core.budget.instantanea import instantanea_precios
from core.catalog.empresa import instantanea_de_lista
from core.contracts import Severidad
from core.verification.precios import reglas_precios
from tests.fixtures.precios_empresa_s1 import EVALUACION, sembrar

A, I, E = Severidad.ADVERTENCIA, Severidad.INFO, Severidad.ERROR
ESPERADO = {  # (regla, severidad, insumo) -> impacto en la versión a ± 0,01 (None: sin impacto)
    ("R11", A, "UNION PVC A.B. 4\""): D("13377.74"),
    ("R11", A, "ARENA LAVADA"): D("143309.00"),
    ("R11", I, "LIJA DE AGUA N 100"): None,
    ("R12", A, "CLAVO DE ACERO LISO L=2 1/2\""): D("1368.10"),
    ("R12", A, "MATERIAL GRANULAR INTEGRAL"): D("20521.45"),
    ("R12", E, "PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM"): None,
    ("R12", A, "TUBO PVC A.N. D=4\" / 110 MM E = 2,2 MM NORMA"): D("0.00"),
}


def _hallazgos(inst):
    return [h for regla in reglas_precios(inst) for h in regla.evaluar(None)]


def _clave(h):
    insumo = next(d for (_, _, d) in ESPERADO if d in h.descripcion)
    return (h.regla, h.severidad, insumo)


def test_conjunto_exacto_de_la_memoria(sesion):
    referencia, _, version = sembrar(sesion)
    hallazgos = _hallazgos(instantanea_precios(sesion, version, referencia, EVALUACION))
    assert len(hallazgos) == len(ESPERADO)
    for h in hallazgos:
        esperado = ESPERADO[_clave(h)]
        assert (h.impacto is None) == (esperado is None)
        if esperado is not None:
            assert (h.impacto - esperado).copy_abs() <= D("0.01")
        assert h.origen_ids in ((), ("S1-EMP-01",))
    assert next(h for h in hallazgos if "UNION" in h.descripcion).valor_observado == D("-0.2001")


def test_por_lista_el_impacto_es_por_unidad(sesion):
    referencia, lista, _ = sembrar(sesion)
    arena = next(h for h in _hallazgos(instantanea_de_lista(sesion, lista, referencia, EVALUACION))
                 if "ARENA" in h.descripcion)
    assert (arena.impacto - D("11328.78")).copy_abs() <= D("0.01")


def test_reevaluar_a_otra_fecha_cambia_lo_mostrado_y_no_las_filas(sesion):
    referencia, _, version = sembrar(sesion)
    guardadas = sesion.scalars(select(models.Hallazgo).where(
        models.Hallazgo.presupuesto_id == version.id)).all()
    antes = [(h.regla, h.descripcion, h.impacto) for h in guardadas]
    otra = _hallazgos(instantanea_precios(sesion, version, referencia, date(2026, 10, 6)))
    assert any("AGUA" in h.descripcion and h.regla == "R12" for h in otra)  # 35 días
    assert [(h.regla, h.descripcion, h.impacto) for h in sesion.scalars(select(models.Hallazgo)
            .where(models.Hallazgo.presupuesto_id == version.id))] == antes
```
```python
# tests/unit/test_reglas_precios.py
"""Fronteras de R11/R12 sin base (PRU‑H11) y el día sin tasa (Foco 2)."""
from datetime import date
from decimal import Decimal as D

from core.verification.precios import InstantaneaPrecios, PrecioAuditado, reglas_precios

T = D("633.3644")


def _p(precio, fecha=date(2026, 9, 20), referencia=D("4530.00"), tasa=T, tasa_a_su_fecha=None,
       erosion=D(0)):
    return PrecioAuditado(1, "MAT-1", "CODO", precio, "Bs", "Bs", precio, fecha, tasa,
                          date(2026, 7, 1) if tasa else None, "MaPreX" if tasa else "",
                          tasa_a_su_fecha, referencia, "Bs", T, "PLO035", erosion, None)


def _inst(*precios, tasa_evaluacion=D("860.18")):
    return InstantaneaPrecios(date(2026, 10, 1), "Bs", precios, tasa_evaluacion,
                              D("-0.20"), D("0.30"), 30)


def _r(inst, codigo):
    return [h for regla in reglas_precios(inst) for h in regla.evaluar(None) if h.regla == codigo]


def test_las_fronteras_exactas_pasan_y_un_diezmilesimo_mas_no():
    assert not _r(_inst(_p(D("0.8000") * D("4530.00")), _p(D("1.3000") * D("4530.00"))), "R11")
    assert len(_r(_inst(_p(D("0.7999") * D("4530.00")), _p(D("1.3001") * D("4530.00"))), "R11")) == 2


def test_30_dias_pasa_y_31_advierte():
    assert not _r(_inst(_p(D("4530"), fecha=date(2026, 9, 1))), "R12")
    assert len(_r(_inst(_p(D("4530"), fecha=date(2026, 8, 31))), "R12")) == 1


def test_dia_sin_tasa_no_revienta():
    """[Foco 2] sin tasa a la fecha del precio (> 7 días) R11 lo cuenta como no contrastable y R12
    vencido sale con impacto None, diciendo por qué."""
    sin = _p(D("4530"), fecha=date(2026, 8, 1), tasa=None, tasa_a_su_fecha=None, erosion=None)
    r11 = _r(_inst(sin, tasa_evaluacion=None), "R11")
    assert r11[0].severidad.name == "INFO" and "sin tasa" in r11[0].descripcion
    r12 = _r(_inst(sin, tasa_evaluacion=None), "R12")
    assert r12[0].impacto is None and "sin tasa" in r12[0].descripcion
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/integration/test_precios_empresa.py tests/unit/test_reglas_precios.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.verification.precios'`
- [ ] **Paso 3: Implementación mínima**
```python
# core/verification/precios.py
"""R11 (PrecioFueraDeRango) y R12 (PrecioVencido), reglas EXTERNAS (S1‑R7): no entran en `REGLAS`;
la línea base sigue 7 de 7 y las huellas de RNF‑04 no se mueven. Cada regla guarda su instantánea
con la fecha de evaluación EXPLÍCITA (M §3.3; nunca el reloj) y no lee el presupuesto que recibe.
Importa solo contratos y el motor: la erosión llega precalculada en `PrecioAuditado.erosion`."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad
from core.costing import calcular_apu

CODIGO_R11, CODIGO_R12 = "R11", "R12"


@dataclass(frozen=True, slots=True)
class PrecioAuditado:
    insumo_id: int
    codigo: str
    descripcion: str
    precio: Decimal  # en la moneda de la lista
    moneda: str
    moneda_original: str
    precio_original: Decimal
    fecha_precio: date
    tasa: Decimal | None  # declarada (por precio o por la lista)
    fecha_tasa: date | None
    fuente_tasa: str
    tasa_a_su_fecha: Decimal | None  # importada, si no declara
    referencia: Decimal | None  # precio MaPreX en su moneda
    moneda_referencia: str
    tasa_referencia: Decimal | None
    codigo_referencia: str
    erosion: Decimal | None  # Δ por unidad en la moneda de la lista (0 si USD; None sin tasa)
    heredado: bool | None


@dataclass(frozen=True, slots=True)
class PartidaPrecios:
    codigo: str
    cantidad: Decimal
    composicion: ComposicionAPU
    insumos: tuple[int | None, ...]  # alineados con (*materiales, *equipos, *mano_obra)


@dataclass(frozen=True, slots=True)
class InstantaneaPrecios:
    fecha_evaluacion: date
    moneda: str
    precios: tuple[PrecioAuditado, ...]
    tasa_evaluacion: Decimal | None
    rango_inferior: Decimal
    rango_superior: Decimal
    plazo_vigencia_dias: int
    partidas: tuple[PartidaPrecios, ...] = ()
    parametros: ParametrosCosto = field(default_factory=ParametrosCosto)


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


def _con_delta(p: PartidaPrecios, insumo_id: int, delta: Decimal) -> ComposicionAPU:
    c = p.composicion
    nm, ne = len(c.materiales), len(c.equipos)
    lineas = [*c.materiales, *c.equipos, *c.mano_obra]
    nuevas = []
    for i, (linea, insumo) in enumerate(zip(lineas, p.insumos, strict=True)):
        if insumo != insumo_id:
            nuevas.append(linea)
        elif i >= nm + ne:
            nuevas.append(replace(linea, sueldo=linea.sueldo + delta))
        else:
            nuevas.append(replace(linea, precio=linea.precio + delta))
    return replace(c, materiales=tuple(nuevas[:nm]), equipos=tuple(nuevas[nm:nm + ne]),
                   mano_obra=tuple(nuevas[nm + ne:]))


def _usan(inst, insumo_id) -> tuple[str, ...]:
    return tuple(p.codigo for p in inst.partidas if insumo_id in p.insumos)


def _impacto(inst: InstantaneaPrecios, insumo_id: int, delta: Decimal | None) -> Decimal | None:
    """Con versión, el Δ del total por `calcular_apu`; sin versión (lista sola), Δ por unidad."""
    if delta is None:
        return None
    if not inst.partidas:
        return abs(delta)
    total = Decimal(0)
    for p in inst.partidas:
        if insumo_id in p.insumos:
            antes = calcular_apu(p.composicion, inst.parametros).precio_unitario
            despues = calcular_apu(_con_delta(p, insumo_id, delta), inst.parametros).precio_unitario
            total += p.cantidad * (despues - antes)
    return abs(total)


def _pct(x: Decimal) -> str:
    return f"{x * 100:+.2f} %"


def _r11(inst: InstantaneaPrecios) -> list[tuple[int | None, Hallazgo]]:
    salida, sin_ref, sin_tasa = [], [], []
    for p in inst.precios:
        if p.referencia is None:
            sin_ref.append(p.descripcion)
            continue
        t_p = Decimal(1) if p.moneda == "USD" else (p.tasa or p.tasa_a_su_fecha)
        t_r = Decimal(1) if p.moneda_referencia == "USD" else p.tasa_referencia
        if t_p is None or t_r is None:
            sin_tasa.append(p.descripcion)
            continue
        with _contexto():
            desvio = (p.precio * t_r) / (p.referencia * t_p) - 1  # una división, sin cuantizar
            if inst.rango_inferior <= desvio <= inst.rango_superior:
                continue
            delta = p.referencia * t_p / t_r - p.precio
        salida.append((p.insumo_id, Hallazgo(
            CODIGO_R11, Severidad.ADVERTENCIA,
            f"{p.descripcion}: {_pct(desvio)} frente a MaPreX {p.codigo_referencia} "
            f"(precio del {p.fecha_precio:%d/%m/%Y}; evaluado al {inst.fecha_evaluacion:%d/%m/%Y})",
            impacto=_impacto(inst, p.insumo_id, delta), origen_ids=_usan(inst, p.insumo_id),
            valor_observado=desvio)))
    if sin_ref or sin_tasa:
        n = len(sin_ref) + len(sin_tasa)
        salida.append((None, Hallazgo(
            CODIGO_R11, Severidad.INFO,
            f"{n} insumos no contrastables: {len(sin_ref)} sin referencia MaPreX "
            f"({', '.join(sin_ref)}), {len(sin_tasa)} sin tasa a su fecha ({', '.join(sin_tasa)})",
            valor_observado=Decimal(n))))
    return salida


def _r12(inst: InstantaneaPrecios) -> list[tuple[int | None, Hallazgo]]:
    salida = []
    for p in inst.precios:
        dias = (inst.fecha_evaluacion - p.fecha_precio).days
        motivo = "" if p.erosion is not None else "; sin tasa a la fecha del precio o de evaluacion"
        if dias > inst.plazo_vigencia_dias:
            salida.append((p.insumo_id, Hallazgo(
                CODIGO_R12, Severidad.ADVERTENCIA,
                f"{p.descripcion}: precio del {p.fecha_precio:%d/%m/%Y} con {dias} dias al "
                f"{inst.fecha_evaluacion:%d/%m/%Y} (plazo {inst.plazo_vigencia_dias}){motivo}",
                impacto=_impacto(inst, p.insumo_id, p.erosion), origen_ids=_usan(inst, p.insumo_id),
                valor_observado=Decimal(dias), valor_esperado=Decimal(inst.plazo_vigencia_dias))))
        if p.tasa is not None and p.fecha_tasa is None:
            salida.append((p.insumo_id, Hallazgo(
                CODIGO_R12, Severidad.ERROR,
                f"{p.descripcion}: la tasa {p.tasa} no tiene fecha; el precio no es trazable",
                origen_ids=_usan(inst, p.insumo_id))))
        elif p.tasa is not None and not p.fuente_tasa.strip():
            salida.append((p.insumo_id, Hallazgo(
                CODIGO_R12, Severidad.ADVERTENCIA,
                f"{p.descripcion}: la tasa {p.tasa} del {p.fecha_tasa:%d/%m/%Y} no declara fuente"
                + (" (precio original en USD: erosion 0 declarada)" if p.moneda_original == "USD" else ""),
                impacto=_impacto(inst, p.insumo_id, p.erosion), origen_ids=_usan(inst, p.insumo_id))))
    return salida


class PrecioFueraDeRango(ReglaVerificacion):
    codigo = CODIGO_R11
    nombre = "Precio fuera de rango frente a MaPreX"

    def __init__(self, instantanea: InstantaneaPrecios) -> None:
        self.instantanea = instantanea

    def evaluar(self, presupuesto) -> list[Hallazgo]:
        return [h for _, h in _r11(self.instantanea)]


class PrecioVencido(ReglaVerificacion):
    codigo = CODIGO_R12
    nombre = "Precio vencido o sin trazabilidad de tasa"

    def __init__(self, instantanea: InstantaneaPrecios) -> None:
        self.instantanea = instantanea

    def evaluar(self, presupuesto) -> list[Hallazgo]:
        return [h for _, h in _r12(self.instantanea)]


def reglas_precios(instantanea: InstantaneaPrecios) -> tuple[ReglaVerificacion, ...]:
    return (PrecioFueraDeRango(instantanea), PrecioVencido(instantanea))


def estado_por_insumo(instantanea: InstantaneaPrecios) -> dict[int, list[str]]:
    """Textos de R11/R12 por insumo, de la MISMA evaluación (columna Estado de Precios)."""
    estado: dict[int, list[str]] = {}
    for insumo_id, h in [*_r11(instantanea), *_r12(instantanea)]:
        if insumo_id is not None:
            estado.setdefault(insumo_id, []).append(f"{h.regla} {h.severidad.name}: {h.descripcion}")
    return estado
```
```python
# core/catalog/empresa.py — agregados de SL‑E2b. Importar además: `from collections import Counter`,
# `from collections.abc import Collection` (junto a `Sequence`), `from core.catalog.indices import
# LADO_POR_DEFECTO, TasaNoDisponible, tasa_aplicable`, `erosion` en la importación de
# `core.catalog.moneda` y `from core.verification.precios import InstantaneaPrecios,
# PrecioAuditado`.


def _referencias(session: Session, lista: models.ListaPrecios) -> dict[int, str]:
    """`precio_id` -> Ref (`ReferenciaPrecio`) de los precios de `lista`."""
    return dict(session.execute(
        select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
        .join(models.PrecioInsumo, models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id)
        .where(models.PrecioInsumo.lista_id == lista.id)).all())


def _tasa_o_nada(session: Session, fecha: date, lado: str) -> Decimal | None:
    """La tasa aplicable a `fecha`; `None` si no la hay (Foco 2: un día sin tasa no revienta)."""
    try:
        return tasa_aplicable(session, fecha, lado=lado).valor
    except TasaNoDisponible:
        return None


def _erosion_en_lista(precio: Decimal, moneda_lista: str, moneda_original: str,
                      precio_original: Decimal, t0: Decimal | None,
                      t1: Decimal | None) -> Decimal | None:
    """Erosión por unidad en la moneda de la lista (S1 §5.3): 0 si el original es USD (declarado);
    `None` sin la tasa del precio o la de evaluación."""
    if moneda_original == "USD":
        return Decimal(0)
    if t0 is None or t1 is None:
        return None
    if moneda_lista == "Bs":
        return erosion(precio, "Bs", t0, t1).bs
    return erosion(precio_original, "Bs", t0, t1).usd


def instantanea_de_lista(
    session: Session,
    lista: models.ListaPrecios,
    referencia: models.ListaPrecios | None,
    fecha_evaluacion: date,
    *,
    insumos: Collection[int] | None = None,
    lado: str = LADO_POR_DEFECTO,
) -> InstantaneaPrecios:
    """R11 y R12 de una lista sola (S1 §6.3): un `PrecioAuditado` por precio de `lista` (o solo los
    de `insumos`) con su origen efectivo, su referencia MaPreX (por insumo y, si no, por Ref
    **única** en la referencia: una Ref repetida no contrasta) y las tasas a la fecha del precio y
    a `fecha_evaluacion`. Sin partidas: el impacto de cada hallazgo es por unidad. No escribe."""
    origenes = origenes_efectivos(session, lista)
    refs_lista = _referencias(session, lista)
    por_insumo: dict[int, models.PrecioInsumo] = {}
    por_ref: dict[str, models.PrecioInsumo] = {}
    refs_ref: dict[int, str] = {}
    origenes_ref = {}
    if referencia is not None:
        por_insumo = {p.insumo_id: p for p in referencia.precios}
        refs_ref = _referencias(session, referencia)
        veces = Counter(refs_ref.values())
        por_id = {p.id: p for p in referencia.precios}
        por_ref = {ref: por_id[pid] for pid, ref in refs_ref.items() if veces[ref] == 1}
        origenes_ref = origenes_efectivos(session, referencia)
    t1 = _tasa_o_nada(session, fecha_evaluacion, lado)
    auditados = []
    for precio in sorted(lista.precios, key=lambda p: p.insumo.codigo):
        if insumos is not None and precio.insumo_id not in insumos:
            continue
        o = origenes[precio.id]
        ref = por_insumo.get(precio.insumo_id) or por_ref.get(refs_lista.get(precio.id, ""))
        a_su_fecha = _tasa_o_nada(session, o.fecha_precio, lado) if o.tasa is None else None
        auditados.append(PrecioAuditado(
            precio.insumo_id, precio.insumo.codigo, precio.insumo.descripcion, precio.precio,
            lista.moneda, o.moneda_original, o.precio_original, o.fecha_precio, o.tasa,
            o.fecha_tasa, o.fuente_tasa, a_su_fecha,
            None if ref is None else ref.precio,
            "" if referencia is None else referencia.moneda,
            None if ref is None else origenes_ref[ref.id].tasa,
            "" if ref is None else refs_ref.get(ref.id, ""),
            _erosion_en_lista(precio.precio, lista.moneda, o.moneda_original, o.precio_original,
                              o.tasa or a_su_fecha, t1),
            es_heredado(session, lista, precio)))
    fila = session.get(models.ListaEmpresa, lista.id)
    return InstantaneaPrecios(
        fecha_evaluacion, lista.moneda, tuple(auditados), t1,
        fila.rango_inferior if fila else RANGO_INFERIOR,
        fila.rango_superior if fila else RANGO_SUPERIOR,
        fila.plazo_vigencia_dias if fila else PLAZO_VIGENCIA_DIAS)
```
```python
# core/budget/instantanea.py — agregado de SL‑E2b (y "instantanea_precios" en `__all__`). Importar
# además: `from dataclasses import dataclass, replace`, `from datetime import date, datetime`,
# `from core.catalog.empresa import instantanea_de_lista`, `from core.catalog.indices import
# LADO_POR_DEFECTO` y `from core.verification.precios import InstantaneaPrecios, PartidaPrecios`.

#: Orden de las líneas de un `ComposicionAPU`: (*materiales, *equipos, *mano_obra).
_ORDEN_TIPOS = (models.TipoInsumo.MATERIAL, models.TipoInsumo.EQUIPO, models.TipoInsumo.MANO_OBRA)


def _insumos_alineados(lineas: Sequence[tuple[str, int | None]]) -> tuple[int | None, ...]:
    """El insumo de cada línea (`(tipo, insumo_id)` ya en su `orden`) alineado con
    (*materiales, *equipos, *mano_obra) de la composición."""
    return tuple(insumo for tipo in _ORDEN_TIPOS for t, insumo in lineas if t == tipo)


def instantanea_precios(
    session: Session,
    version: models.Presupuesto,
    referencia: models.ListaPrecios | None,
    fecha_evaluacion: date,
    *,
    lado: str = LADO_POR_DEFECTO,
) -> InstantaneaPrecios:
    """R11 y R12 de una versión (S1 §4.3): los precios de su lista que usan sus partidas, con el
    impacto llevado al total por `calcular_apu` sobre sus composiciones (instantánea y, sin ella,
    catálogo) y sus parámetros. Con lista de empresa, la referencia es la que declara su
    `ListaEmpresa`. Una partida cuya composición ya no se puede reconstruir no entra (la hoja la
    abre en solo lectura). No escribe."""
    lista = version.lista_precios
    de_empresa = session.get(models.ListaEmpresa, lista.id)
    if de_empresa is not None and de_empresa.lista_referencia_id is not None:
        referencia = session.get(models.ListaPrecios, de_empresa.lista_referencia_id)
    cantidades: dict[str, Decimal] = {}
    for renglon in version.partidas:
        codigo = renglon.partida.codigo
        cantidades[codigo] = cantidades.get(codigo, Decimal(0)) + renglon.cantidad
    filas = {fila.codigo_partida: fila for fila in _filas(session, version)}
    catalogo = Catalogo(session)
    partidas: list[PartidaPrecios] = []
    for codigo, cantidad in cantidades.items():
        if codigo in filas:
            lineas = sorted(filas[codigo].lineas, key=lambda linea: linea.orden)
            composicion = _a_composicion(filas[codigo])
            insumos = _insumos_alineados([(linea.tipo, linea.insumo_id) for linea in lineas])
        else:
            try:
                composicion = catalogo.composicion(codigo, fecha=version.fecha, lista=lista)
            except (KeyError, CatalogoIncompleto):
                continue
            lineas = sorted(catalogo.partida(codigo).composicion, key=lambda linea: linea.orden)
            insumos = _insumos_alineados([(linea.insumo.tipo, linea.insumo_id) for linea in lineas])
        partidas.append(PartidaPrecios(codigo, cantidad, composicion, insumos))
    usados = {insumo for p in partidas for insumo in p.insumos if insumo is not None}
    de_lista = instantanea_de_lista(session, lista, referencia, fecha_evaluacion, insumos=usados,
                                    lado=lado)
    return replace(de_lista, moneda=version.moneda, partidas=tuple(partidas),
                   parametros=_parametros_de(version))
```
```python
# core/budget/__init__.py — `instantanea_precios` en la importación de `core.budget.instantanea` y
# en `__all__` (orden alfabético)
from core.budget.instantanea import (
    ResultadoInstantanea,
    asegurar_instantanea,
    composiciones_de_presupuesto,
    instantanea_precios,
    plan_de_version,
)
```
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/integration/test_precios_empresa.py tests/unit/test_reglas_precios.py tests/integration/test_auditoria_7_de_7.py tests/unit/test_huellas_rnf04.py -q -W error`; `uv run pytest -q -W error`; ruff.
- [ ] **Paso 5: Commit**
```bash
git add tests/integration/test_precios_empresa.py tests/unit/test_reglas_precios.py tests/fixtures/precios_empresa_s1.py
git commit -m "test(core): SL-E2 R11 y R12 contra la memoria de precios de empresa en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add core/verification/precios.py core/catalog/empresa.py core/budget/instantanea.py core/budget/__init__.py
git commit -m "feat(core): SL-E2 reglas R11 y R12 con instantanea de precios" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
  Fusionar `inc/060-s1-3-nucleo` tras su revisión y el aval del tutor de SL‑E2.

### Tarea 9: Pantallas de UC‑17 — índices del BCV y precios de la empresa

**Rama:** `inc/060-s1-3-ui` (sale de `main` con `inc/060-s1-3-nucleo` e `inc/060-s1-2-bcv` fusionados)   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/texto_seguro.py`, `ui/indices.py`, `ui/precios_empresa.py`, `ui/paginas/indices.py`, `ui/paginas/precios_empresa.py`, `tests/unit/test_texto_seguro.py`, `tests/unit/test_ui_indices.py`, `tests/unit/test_ui_precios_empresa.py`, `tests/unit/test_arquitectura_s1.py`
- Modificar: `ui/app.py:59-121` (dos `DefinicionPagina` en Trabajo, tras «Historico de cambios de precio»: «Precios de la empresa» `UC-17`, «Indices del BCV» `UC-17`), `tests/unit/test_ui_app.py:41-63,348` (`TITULOS_TRABAJO`, `CASOS_DE_USO` y el nombre/conteo de `test_son_once_pantallas...` → trece), `tests/unit/test_ui_importable.py:13-28` (`MODULOS_SIN_PAGINA` gana los tres módulos sin pantalla y el conteo pasa a trece páginas); `tests/unit/test_arquitectura_s5.py` (B, Tarea 6): `PAGINAS_QUE_ABREN_EL_CASO` gana `"indices"` y `"precios_empresa"` (las dos páginas abren el caso con `preparar_base(ruta_caso())` antes de `crear_motor`, como exige esa prueba)
- `ui/texto_seguro.py` lo crea esta tarea (ni A ni B lo crean); S1‑4 y las secciones siguientes lo importan.

**Interfaces:**
- Produce: `texto_seguro(texto: str) -> str` (escapa `\ ` `` ` `` `* _ { } [ ] ( ) # + - . ! | < > ~ $`); `ui.indices`: `TIPOS = ("tasa", "inpc", "csv")`, `leer(ruta, tipo, *, fuente, fecha_descarga) -> InformeImportacion`, `filas_del_informe(informe) -> list[dict[str, str]]`, `confirmar(sesion, informe, *, responsable, definiciones_csv=None, ahora=None) -> list[str]`; `ui.precios_empresa`: `ResumenEmpresa(nombre, propios, desconocidos)`, `COLUMNAS_HALLAZGOS`, `cargar_referencia_maprex(sesion) -> str`, `crear_lista(sesion, ruta, *, empresa_nombre, empresa_rif, base_id, moneda, fecha, fuente, nombre) -> ResumenEmpresa`, `hallazgos_de_lista(sesion, lista_id, fecha_evaluacion) -> list[dict[str, str]]`, y para los selectores de la pantalla `listas_base(sesion) -> list[tuple[int, str, str]]` y `listas_de_empresa(sesion) -> list[tuple[int, str]]`.

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/unit/test_texto_seguro.py
from ui.texto_seguro import texto_seguro


def test_una_imagen_markdown_ajena_no_se_interpreta():
    nombre = "![x](http://127.0.0.1:9/robo.png) **hoja**"
    seguro = texto_seguro(nombre)
    assert "![" not in seguro and "\\!\\[x\\]" in seguro and "\\*\\*hoja\\*\\*" in seguro
```
```python
# tests/unit/test_arquitectura_s1.py
"""Reglas de arquitectura de S1 en su propio archivo (RV‑2), con los ayudantes compartidos de
`tests/fixtures/arquitectura.py` (sección B, Tarea 1)."""
import pytest

from tests.fixtures.arquitectura import RAIZ, importaciones

SIN_PINTAR = ("ui/indices.py", "ui/precios_empresa.py", "ui/reajuste.py", "ui/texto_seguro.py")


@pytest.mark.parametrize("modulo", [m for m in SIN_PINTAR if (RAIZ / m).exists()])
def test_la_capa_de_s1_no_pinta(modulo):
    prohibidos = {
        m for m in importaciones(RAIZ / modulo)
        if m.split(".")[0] in {"streamlit", "pandas"} or m == "ui.caso"
    }
    assert prohibidos == set()


def test_ninguna_pagina_de_s1_importa_scripts_al_cargar():
    for pagina in ("indices", "precios_empresa", "reajuste"):
        ruta = RAIZ / "ui" / "paginas" / f"{pagina}.py"
        if ruta.exists():
            texto = ruta.read_text(encoding="utf-8")
            assert "\nfrom scripts" not in texto and "\nimport scripts" not in texto  # RV‑25
```
```python
# tests/unit/test_ui_indices.py
from datetime import date

from sqlalchemy import func, select

from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from tests.fixtures.bcv_cuadriculas import CARPETA, campo
from ui import indices


def test_leer_no_escribe_y_confirmar_es_idempotente(tmp_path):
    ruta = CARPETA / campo("Tasa", "Archivo")
    informe = indices.leer(ruta, "tasa", fuente=campo("Tasa", "Dirección"),
                           fecha_descarga=date.fromisoformat(campo("Tasa", "Fecha de descarga")))
    motor = crear_motor(f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        assert sesion.scalar(select(func.count()).select_from(models.ValorIndice)) == 0
        primero = indices.confirmar(sesion, informe, responsable="Admin")
        segundo = indices.confirmar(sesion, informe, responsable="Admin")
        assert all("importada" in m for m in primero) and all("ya importado" in m for m in segundo)
    motor.dispose()
```
```python
# tests/unit/test_ui_precios_empresa.py
"""UC-17 4-5 desde la capa sin Streamlit: referencia MaPreX, lista de empresa y R11/R12 de la lista
sola, sin version: el impacto es por unidad (memoria tests/fixtures/memorias/s1_precios_empresa.md,
columna «Δ por unidad»). La lista sola trae ademas los R12 de los precios heredados de la base: la
prueba exige las filas de la memoria, no el conjunto exacto (ese es de la version, Tarea 8)."""
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from core import models
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.catalog.empresa import lista_de_referencia
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from scripts.seed import sembrar
from tests.fixtures.subproceso import importar_en_limpio, modulos_cargados
from ui import precios_empresa

CSV = Path(__file__).resolve().parents[1] / "fixtures" / "precios_empresa_s1.csv"
EVALUACION = date(2026, 10, 1)
#: (regla, severidad, insumo) -> impacto por unidad tal como lo presenta la pantalla (memoria).
DE_LA_MEMORIA = {
    ("R11", "ADVERTENCIA", 'UNION PVC A.B. 4"'): "1057.53",
    ("R11", "ADVERTENCIA", "ARENA LAVADA"): "11328.78",
    ("R11", "INFO", "LIJA DE AGUA N 100"): "",
    ("R12", "ADVERTENCIA", 'CLAVO DE ACERO LISO L=2 1/2"'): "108.15",
    ("R12", "ADVERTENCIA", "MATERIAL GRANULAR INTEGRAL"): "1622.25",
    ("R12", "ERROR", "PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM"): "",
    ("R12", "ADVERTENCIA", 'TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA'): "0.00",
}


def _es(fila, regla, severidad, insumo):
    if (fila["Regla"], fila["Severidad"]) != (regla, severidad):
        return False
    texto = fila["Descripción"]
    return insumo in texto if severidad == "INFO" else texto.startswith(f"{insumo}:")


def test_referencia_lista_de_empresa_y_hallazgos_de_la_memoria(tmp_path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    try:
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
            assert "cargada" in precios_empresa.cargar_referencia_maprex(sesion)
            assert "ya estaba" in precios_empresa.cargar_referencia_maprex(sesion)
            Catalogo(sesion).dar_de_alta_insumo(
                models.TipoInsumo.MATERIAL, "LIJA DE AGUA N 100", "pza"
            )
            registrar_importacion(
                sesion, definicion_tasa("venta"), [Observacion(EVALUACION, D("860.18"))],
                archivo="FUENTE.md", huella="e" * 64, fuente="https://www.bcv.org.ve/",
                fecha_descarga=date(2026, 10, 8), responsable="Admin", filas_leidas=1,
                filas_rechazadas=0,
            )
            sesion.commit()
            resumen = precios_empresa.crear_lista(
                sesion, CSV, empresa_nombre="Constructora Ejemplo, C.A.",
                empresa_rif="J-00000000-0", base_id=lista_de_referencia(sesion).id, moneda="Bs",
                fecha=date(2026, 9, 20), fuente="lista interna 2026-09", nombre="",
            )
            assert (resumen.propios, resumen.desconocidos) == (10, ())
            ((lista_id, nombre),) = precios_empresa.listas_de_empresa(sesion)
            assert nombre == resumen.nombre
            filas = precios_empresa.hallazgos_de_lista(sesion, lista_id, EVALUACION)
    finally:
        motor.dispose()
    assert all(tuple(fila) == precios_empresa.COLUMNAS_HALLAZGOS for fila in filas)
    for (regla, severidad, insumo), impacto in DE_LA_MEMORIA.items():
        (fila,) = [f for f in filas if _es(f, regla, severidad, insumo)]
        assert fila["Impacto"] == impacto, (regla, insumo)


def test_la_pagina_no_importa_el_script_de_maprex_al_cargarse(tmp_path):
    """RV-25: el script de la lista MaPreX se importa dentro de la accion, no al cargar."""
    salida = importar_en_limpio(["ui.paginas.precios_empresa"], cwd=tmp_path)
    assert salida.returncode == 0, salida.stderr
    assert "scripts.lista_maprex_bs" not in modulos_cargados(salida)
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_texto_seguro.py tests/unit/test_arquitectura_s1.py tests/unit/test_ui_indices.py tests/unit/test_ui_precios_empresa.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'ui.texto_seguro'`
- [ ] **Paso 3: Implementación mínima**
```python
# ui/texto_seguro.py
"""Única función para mostrar texto ajeno en Markdown (M §4.6, RV‑14): escapa sus caracteres."""
import re

_ESPECIALES = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$])")


def texto_seguro(texto: str) -> str:
    return _ESPECIALES.sub(r"\\\1", texto)
```
```python
# ui/indices.py
"""UC‑17 1‑3 sin Streamlit: adaptador -> informe previo -> core.catalog.indices (S1 §4.3)."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from adapters.bcv.csv_canonico import leer_csv_canonico
from adapters.bcv.formatos import cargar_formatos
from adapters.bcv.informe import InformeImportacion
from adapters.bcv.inpc import leer_inpc
from adapters.bcv.libro import abrir_libro
from adapters.bcv.tasa import leer_tasa
from core.catalog.indices import (
    UNIDAD_INDICE_BS, DefinicionSerie, Observacion, definicion_tasa, registrar_importacion)

TIPOS = ("tasa", "inpc", "csv")


def leer(ruta: Path, tipo: str, *, fuente: str, fecha_descarga: date) -> InformeImportacion:
    if tipo == "csv":
        return leer_csv_canonico(ruta, fecha_descarga=fecha_descarga)
    libro, formatos = abrir_libro(ruta), cargar_formatos()
    if tipo == "tasa":
        return leer_tasa(libro, fuente=fuente, fecha_descarga=fecha_descarga,
                         trimestre_por_letra=formatos.trimestre_por_letra)
    if tipo == "inpc":
        return leer_inpc(libro, fuente=fuente, fecha_descarga=fecha_descarga, formato=formatos.inpc)
    raise ValueError(f"tipo {tipo!r}; se espera uno de {TIPOS}")


def _definicion(serie, definiciones_csv) -> DefinicionSerie:
    if serie.clave == "usd_compra":
        return definicion_tasa("compra")
    if serie.clave == "usd_venta":
        return definicion_tasa("venta")
    if serie.clave == "inpc_general":
        return DefinicionSerie("BCV-INPC-GENERAL", serie.nombre, serie.organismo,
                               UNIDAD_INDICE_BS, "mensual", serie.base)
    if serie.clave not in (definiciones_csv or {}):
        raise ValueError(f"declare nombre, organismo, unidad y periodicidad de la serie {serie.clave}")
    return definiciones_csv[serie.clave]


def filas_del_informe(informe: InformeImportacion) -> list[dict[str, str]]:
    return [{"Lugar": r.lugar, "Motivo": r.motivo} for r in informe.rechazos]


def confirmar(sesion, informe, *, responsable, definiciones_csv=None, ahora=None) -> list[str]:
    """UC‑17 3: guarda cada serie (una importación por serie, misma huella) y confirma."""
    mensajes = []
    try:
        for serie in informe.series:
            hecho = registrar_importacion(
                sesion, _definicion(serie, definiciones_csv),
                [Observacion(v.fecha, v.valor, v.provisional) for v in serie.valores],
                archivo=informe.archivo, huella=informe.huella, fuente=informe.fuente,
                fecha_descarga=informe.fecha_descarga, responsable=responsable,
                filas_leidas=informe.filas_leidas, filas_rechazadas=informe.filas_rechazadas,
                informe=informe.texto(), ahora=ahora or datetime.now())
            mensajes.append(f"{serie.clave}: " + ("ya importado; no se escribio nada" if hecho is None
                                                  else f"importada ({len(serie.valores)} valores)"))
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise
    return mensajes
```
```python
# ui/precios_empresa.py
"""UC-17 4-5 sin Streamlit: la referencia MaPreX en Bs, la lista de una empresa y sus hallazgos de
R11 y R12 a una fecha de evaluacion (spec S1 §6). La pantalla `ui/paginas/precios_empresa.py` solo
pinta. Cada accion que escribe confirma o deshace su transaccion entera. Sin Streamlit, sin pandas y
sin `ui.caso` (lo vigila `tests/unit/test_arquitectura_s1.py`)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select

from core import models
from core.catalog import leer_lista_precios
from core.catalog.empresa import (
    crear_lista_de_empresa,
    crear_lista_de_referencia,
    instantanea_de_lista,
    lista_de_referencia,
    precios_propios_desde,
)
from core.catalog.indices import tasa_aplicable
from core.catalog.moneda import TasaDeclarada, exigir_moneda
from core.verification.precios import reglas_precios
from core.verification.texto import formatear_decimal

COLUMNAS_HALLAZGOS = ("Regla", "Severidad", "Descripción", "Impacto")
NOMBRE_REFERENCIA = "MaPreX julio 2026 en Bs"


@dataclass(frozen=True, slots=True)
class ResumenEmpresa:
    """Lo que hizo `crear_lista`: el nombre de la lista, cuantos precios propios entraron y las
    descripciones que el catalogo no conoce (UC-17 4a: se informan, no se dan de alta)."""

    nombre: str
    propios: int
    desconocidos: tuple[str, ...]


def _confirmar[T](sesion, accion: Callable[[], T]) -> T:
    try:
        resultado = accion()
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise
    return resultado


def cargar_referencia_maprex(sesion) -> str:
    """Carga la lista MaPreX julio 2026 en Bs (S1 §6.2). El script se importa aqui, dentro de la
    accion, nunca al cargar la pagina (RV-25). Una referencia ya cargada no se duplica."""
    from scripts.lista_maprex_bs import (
        FECHA_TASA_MAPREX,
        FUENTE_TASA_MAPREX,
        RUTA_SALIDA,
        TASA_MAPREX,
    )

    existente = lista_de_referencia(sesion)
    if existente is not None:
        return f"La referencia «{existente.nombre}» ya estaba cargada: no se escribio nada."
    tasa = TasaDeclarada(TASA_MAPREX, FECHA_TASA_MAPREX, FUENTE_TASA_MAPREX)
    lista = _confirmar(sesion, lambda: crear_lista_de_referencia(
        sesion, RUTA_SALIDA, nombre=NOMBRE_REFERENCIA, moneda="Bs", tasa=tasa))
    return f"Referencia «{lista.nombre}» cargada con {len(lista.precios)} precios."


def crear_lista(
    sesion, ruta: Path, *, empresa_nombre: str, empresa_rif: str, base_id: int, moneda: str,
    fecha: date, fuente: str, nombre: str,
) -> ResumenEmpresa:
    """UC-17 4: lee el archivo, separa los precios propios de los insumos que el catalogo no
    conoce y crea la lista de empresa sobre la base elegida. Si la base esta en otra moneda, se
    convierte con la tasa del BCV aplicable a `fecha` (S1 §6.1). Confirma o deshace todo."""
    exigir_moneda(moneda)
    leidos = leer_lista_precios(ruta)

    def accion() -> ResumenEmpresa:
        base = sesion.get(models.ListaPrecios, base_id)
        if base is None:
            raise ValueError(f"la lista base {base_id} no existe en este caso")
        propios, desconocidos = precios_propios_desde(sesion, leidos)
        tasa_base = None
        if base.moneda != moneda:
            tasa_base = TasaDeclarada.de_importacion(tasa_aplicable(sesion, fecha))
        lista = crear_lista_de_empresa(
            sesion, empresa_nombre, empresa_rif, base, propios, moneda=moneda, fecha=fecha,
            fuente=fuente, referencia=lista_de_referencia(sesion), nombre=nombre.strip() or None,
            tasa_base=tasa_base,
        )
        return ResumenEmpresa(lista.nombre, len(propios),
                              tuple(leido.descripcion for leido in desconocidos))

    return _confirmar(sesion, accion)


def hallazgos_de_lista(sesion, lista_id: int, fecha_evaluacion: date) -> list[dict[str, str]]:
    """R11 y R12 de la lista sola a `fecha_evaluacion`, en memoria (no escribe nada): sin version
    no hay cantidades, asi que el impacto es por unidad de insumo."""
    lista = sesion.get(models.ListaPrecios, lista_id)
    if lista is None:
        raise ValueError(f"la lista {lista_id} no existe en este caso")
    instantanea = instantanea_de_lista(sesion, lista, lista_de_referencia(sesion),
                                       fecha_evaluacion)
    return [
        dict(zip(COLUMNAS_HALLAZGOS, (
            h.regla, h.severidad.name, h.descripcion,
            "" if h.impacto is None else formatear_decimal(h.impacto, 2),
        ), strict=True))
        for regla in reglas_precios(instantanea)
        for h in regla.evaluar(None)
    ]


def listas_base(sesion) -> list[tuple[int, str, str]]:
    """Las listas que pueden ser base de una lista de empresa (id, nombre, moneda): todas menos las
    de proyecto y las de empresa, de la mas reciente a la mas antigua."""
    fuera = select(models.ListaPreciosOrigen.lista_id).where(
        models.ListaPreciosOrigen.alcance.in_((models.ALCANCE_PROYECTO, models.ALCANCE_EMPRESA))
    )
    return [
        (lista.id, lista.nombre, lista.moneda)
        for lista in sesion.scalars(
            select(models.ListaPrecios)
            .where(models.ListaPrecios.id.not_in(fuera))
            .order_by(models.ListaPrecios.fecha_vigencia.desc(), models.ListaPrecios.id.desc())
        )
    ]


def listas_de_empresa(sesion) -> list[tuple[int, str]]:
    """Las listas de empresa del caso (id, nombre), en el orden en que se crearon."""
    return [
        (lista.id, lista.nombre)
        for lista in sesion.scalars(
            select(models.ListaPrecios)
            .join(models.ListaEmpresa, models.ListaEmpresa.lista_id == models.ListaPrecios.id)
            .order_by(models.ListaPrecios.id)
        )
    ]
```
  Las dos páginas (y `ui/paginas/reajuste.py` en la Tarea 13) abren el caso con el mismo patrón, que satisface `test_cada_pagina_que_abre_el_caso_lo_prepara` de B:
```python
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from ui.caso import ruta_caso


def _motor_del_caso():
    """El motor del caso abierto, ya en `head` (RV-5); `None` si no se puede preparar."""
    ruta = ruta_caso()
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(str(error))
        return None
    return crear_motor(f"sqlite:///{ruta.as_posix()}")
```
  y cada `render()` hace `motor = _motor_del_caso()`; `if motor is None: return`; `try: with abrir_sesion(motor) as sesion: ...` `finally: motor.dispose()`.
```python
# ui/paginas/indices.py
"""Pantalla «Indices del BCV» (UC-17 1-3): leer un archivo del BCV sin escribir nada, revisar el
informe previo y confirmar. La logica vive en `ui.indices` (sin Streamlit); aqui solo se pinta. Los
nombres de hoja, las etiquetas y los motivos vienen del archivo: son texto ajeno y van en celdas o
por `ui.texto_seguro`, nunca como Markdown interpretado (RV-14). Sin efectos al importarse."""
from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import abrir_sesion, crear_motor
from core.catalog.indices import PERIODICIDADES, UNIDAD_INDICE_BS, DefinicionSerie
from operacion.base_datos import ErrorDeBase, preparar_base
from ui import indices
from ui.caso import ruta_caso
from ui.subidas import guardar_subida
from ui.texto_seguro import texto_seguro

CLAVE_INFORME = "indices_informe"  # (tipo, InformeImportacion) leido: no es clave de ningun widget
ROTULOS_TIPO = {
    "tasa": "Tasa de referencia del USD (.xls trimestral)",
    "inpc": "INPC (.xls mensual)",
    "csv": "Una serie en CSV canonico (serie, fecha, valor, provisional, fuente)",
}


def _motor_del_caso():
    """El motor del caso abierto, ya en `head` (RV-5); `None` si no se puede preparar."""
    ruta = ruta_caso()
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(str(error))
        return None
    return crear_motor(f"sqlite:///{ruta.as_posix()}")


def render() -> None:
    st.caption(
        "Importe la tasa de referencia del BCV, el INPC o una serie en CSV. «Leer» no escribe "
        "nada: muestra lo que se importaria. «Confirmar» guarda los valores con la huella del "
        "archivo; el mismo archivo dos veces no escribe nada."
    )
    with st.form("indices_leer"):
        tipo = st.selectbox("Que archivo es", indices.TIPOS, format_func=ROTULOS_TIPO.get)
        archivo = st.file_uploader("Archivo", type=["xls", "xlsx", "csv"])
        fuente = st.text_input("Direccion de la pagina del BCV de donde lo bajo")
        descarga = st.date_input("Fecha de descarga", value=date.today())
        leer = st.form_submit_button("Leer")
    if leer:
        _leer(tipo, archivo, fuente, descarga)
    leido = st.session_state.get(CLAVE_INFORME)
    if leido is not None:
        _pintar(*leido)


def _leer(tipo: str, archivo, fuente: str, descarga: date) -> None:
    st.session_state.pop(CLAVE_INFORME, None)
    if archivo is None:
        st.error("Elija el archivo que bajo del BCV.")
        return
    try:
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = guardar_subida(carpeta, archivo)
            informe = indices.leer(Path(ruta), tipo, fuente=fuente, fecha_descarga=descarga)
    except ValueError as error:  # `FormatoNoReconocido` es `ValueError` (UC-17 2a)
        st.error(texto_seguro(f"No se importo nada: {error}"))
        return
    st.session_state[CLAVE_INFORME] = (tipo, informe)


def _rango(serie) -> tuple[str, str]:
    fechas = [valor.fecha for valor in serie.valores]
    return (min(fechas).isoformat(), max(fechas).isoformat()) if fechas else ("", "")


def _pintar(tipo: str, informe) -> None:
    st.subheader("Informe previo (todavia no se guardo nada)")
    a, b, c = st.columns(3)
    a.metric("Filas leidas", informe.filas_leidas)
    b.metric("Rechazadas", informe.filas_rechazadas)
    c.metric("Provisionales", informe.provisionales)
    st.dataframe(
        DataFrame(
            [
                {"Serie": serie.clave, "Valores": len(serie.valores),
                 "Desde": _rango(serie)[0], "Hasta": _rango(serie)[1]}
                for serie in informe.series
            ],
            columns=["Serie", "Valores", "Desde", "Hasta"],
        ),
        hide_index=True,
        width="stretch",
    )
    if informe.rechazos:
        st.dataframe(DataFrame(indices.filas_del_informe(informe)), hide_index=True,
                     width="stretch")
    for advertencia in informe.advertencias:
        st.text(advertencia)
    definiciones = _definiciones_csv(informe) if tipo == "csv" else None
    responsable = st.text_input("Responsable de la importacion")
    if st.button("Confirmar la importacion", type="primary"):
        _confirmar(informe, responsable, definiciones)


def _definiciones_csv(informe) -> dict[str, DefinicionSerie]:
    """Una serie del CSV canonico no trae nombre, organismo, unidad ni periodicidad: se declaran."""
    definiciones = {}
    for serie in informe.series:
        st.markdown(f"**Serie {texto_seguro(serie.clave)}**")
        a, b, c, d = st.columns(4)
        nombre = a.text_input("Nombre", value=serie.clave, key=f"indices_nombre_{serie.clave}")
        organismo = b.text_input("Organismo", key=f"indices_organismo_{serie.clave}")
        unidad = c.text_input("Unidad", value=UNIDAD_INDICE_BS,
                              key=f"indices_unidad_{serie.clave}")
        periodicidad = d.selectbox("Periodicidad", PERIODICIDADES, index=1,
                                   key=f"indices_periodicidad_{serie.clave}")
        if nombre.strip() and organismo.strip() and unidad.strip():
            definiciones[serie.clave] = DefinicionSerie(serie.clave, nombre.strip(),
                                                        organismo.strip(), unidad.strip(),
                                                        periodicidad)
    return definiciones


def _confirmar(informe, responsable: str, definiciones) -> None:
    motor = _motor_del_caso()
    if motor is None:
        return
    try:
        with abrir_sesion(motor) as sesion:
            mensajes = indices.confirmar(sesion, informe, responsable=responsable,
                                         definiciones_csv=definiciones)
    except ValueError as error:
        st.error(texto_seguro(f"No se guardo nada: {error}"))
        return
    except SQLAlchemyError as error:
        st.error(f"No se pudo escribir en el caso: {getattr(error, 'orig', None) or error}")
        return
    finally:
        motor.dispose()
    st.session_state.pop(CLAVE_INFORME, None)
    for mensaje in mensajes:
        st.success(texto_seguro(mensaje))
```
```python
# ui/paginas/precios_empresa.py
"""Pantalla «Precios de la empresa» (UC-17 4-5): cargar la referencia MaPreX en Bs, crear la lista
de una empresa sobre una lista base y ver sus hallazgos de R11 y R12 a una fecha de evaluacion. La
logica vive en `ui.precios_empresa` (sin Streamlit); aqui solo se pinta. Las descripciones de una
lista importada son texto ajeno: van en celdas (RV-14). El script de MaPreX se importa dentro de la
accion, no al cargar esta pagina (RV-25). Sin efectos al importarse."""
from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import abrir_sesion, crear_motor
from core.catalog.moneda import MONEDAS
from operacion.base_datos import ErrorDeBase, preparar_base
from ui import precios_empresa
from ui.caso import ruta_caso
from ui.subidas import guardar_subida
from ui.texto_seguro import texto_seguro


def _motor_del_caso():
    """El motor del caso abierto, ya en `head` (RV-5); `None` si no se puede preparar."""
    ruta = ruta_caso()
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(str(error))
        return None
    return crear_motor(f"sqlite:///{ruta.as_posix()}")


def render() -> None:
    st.caption(
        "La lista de su empresa: una copia de la lista base con sus precios encima, cada uno con "
        "su fecha y su fuente. No cambia la valoracion de ningun proyecto que no la use."
    )
    motor = _motor_del_caso()
    if motor is None:
        return
    try:
        _referencia(motor)
        _crear(motor)
        _hallazgos(motor)
    except SQLAlchemyError as error:
        st.error(f"No se pudo leer o escribir el caso: {getattr(error, 'orig', None) or error}")
    finally:
        motor.dispose()


def _referencia(motor) -> None:
    st.subheader("1. La referencia MaPreX en bolivares")
    if st.button("Cargar la referencia MaPreX en Bs"):
        try:
            with abrir_sesion(motor) as sesion:
                st.success(precios_empresa.cargar_referencia_maprex(sesion))
        except (ValueError, OSError) as error:
            st.error(texto_seguro(f"No se cargo la referencia: {error}"))


def _crear(motor) -> None:
    st.subheader("2. La lista de la empresa")
    with abrir_sesion(motor) as sesion:
        bases = precios_empresa.listas_base(sesion)
    if not bases:
        st.info("El caso no tiene listas de precios: cargue una en Actualizar precios.")
        return
    with st.form("precios_empresa_crear"):
        a, b = st.columns(2)
        empresa = a.text_input("Empresa (nombre)")
        rif = b.text_input("RIF")
        base = st.selectbox("Lista base", bases, format_func=lambda x: f"{x[1]} ({x[2]})")
        c, d = st.columns(2)
        moneda = c.selectbox("Moneda de la lista", MONEDAS, index=None,
                             placeholder="Elija Bs o USD")
        fecha = d.date_input("Fecha de la lista", value=date.today())
        fuente = st.text_input("Fuente de la lista (de donde salen estos precios)")
        nombre = st.text_input("Nombre de la lista (opcional)")
        archivo = st.file_uploader("Archivo de precios (CSV o XLSX)", type=["csv", "xlsx"])
        enviar = st.form_submit_button("Crear la lista de la empresa")
    if not enviar:
        return
    if moneda is None or archivo is None:
        st.error("Elija la moneda de la lista y el archivo de precios: no tienen valor "
                 "por defecto.")
        return
    try:
        with tempfile.TemporaryDirectory() as carpeta, abrir_sesion(motor) as sesion:
            ruta = guardar_subida(carpeta, archivo)
            resumen = precios_empresa.crear_lista(
                sesion, Path(ruta), empresa_nombre=empresa, empresa_rif=rif, base_id=base[0],
                moneda=moneda, fecha=fecha, fuente=fuente, nombre=nombre,
            )
    except ValueError as error:
        st.error(texto_seguro(f"No se creo la lista: {error}"))
        return
    st.success(texto_seguro(f"Lista «{resumen.nombre}» creada con {resumen.propios} precios "
                            "propios."))
    if resumen.desconocidos:
        st.warning("Estos insumos no estan en el catalogo y no entraron a la lista (UC-17 4a):")
        st.dataframe(DataFrame({"Insumo": list(resumen.desconocidos)}), hide_index=True)


def _hallazgos(motor) -> None:
    st.subheader("3. Precios vencidos o fuera de rango (R11 y R12)")
    with abrir_sesion(motor) as sesion:
        listas = precios_empresa.listas_de_empresa(sesion)
    if not listas:
        st.info("Todavia no hay listas de empresa en este caso.")
        return
    a, b = st.columns(2)
    lista = a.selectbox("Lista", listas, format_func=lambda x: x[1])
    evaluacion = b.date_input("Fecha de evaluacion", value=date.today())
    with abrir_sesion(motor) as sesion:
        filas = precios_empresa.hallazgos_de_lista(sesion, lista[0], evaluacion)
    st.caption("Sin version, el impacto es por unidad de insumo. Nada de esto se guarda.")
    st.dataframe(DataFrame(filas, columns=list(precios_empresa.COLUMNAS_HALLAZGOS)),
                 hide_index=True, width="stretch")
```
```python
# ui/app.py — importación de las páginas y las dos definiciones nuevas
from ui.paginas import (
    actualizacion,
    catalogo,
    componer,
    elaborar,
    escenarios,
    historico,
    hoja,
    indices,
    inicio,
    precios_empresa,
    similares,
    simulador,
    visor,
)
# en PAGINAS, tras «Historico de cambios de precio»:
    DefinicionPagina(precios_empresa.render, "Precios de la empresa", SECCION_TRABAJO, "UC-17"),
    DefinicionPagina(indices.render, "Indices del BCV", SECCION_TRABAJO, "UC-17"),
```
```python
# tests/unit/test_ui_app.py — TITULOS_TRABAJO (:41-49), CASOS_DE_USO (:57-63) y el conteo (:348)
TITULOS_TRABAJO = (
    "Inicio",
    "Catalogo de partidas e insumos",
    "Componer una partida",
    "Elaborar un presupuesto",
    "Hoja del proyecto",
    "Actualizar precios",
    "Historico de cambios de precio",
    "Precios de la empresa",
    "Indices del BCV",
)

CASOS_DE_USO = {
    "actualizacion": "UC-02",
    "componer": "UC-10 / UC-11",
    "elaborar": "UC-01",
    "escenarios": "UC-08",
    "indices": "UC-17",
    "precios_empresa": "UC-17",
    "similares": "UC-03",
}


def test_son_trece_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
    rutas = [p.ruta_url for p in PAGINAS]
    assert len(rutas) == 13
    assert rutas.index("hoja") == rutas.index("elaborar") + 1
    assert pagina_por_ruta("hoja").seccion == SECCION_TRABAJO
```
```python
# tests/unit/test_ui_importable.py:13-28 — los tres módulos sin pantalla de S1 y trece páginas
MODULOS_SIN_PAGINA = (
    "ui.app",
    "ui.caso",
    "ui.recorridos",
    "ui.composicion",
    "ui.elaboracion",
    "ui.hoja",
    "ui.resultado",
    "ui.texto_seguro",
    "ui.indices",
    "ui.precios_empresa",
)
# y en test_las_paginas_se_importan_sin_efectos:
    assert len(modulos) == len(MODULOS_SIN_PAGINA) + 13  # las trece paginas del marco
```
```python
# tests/unit/test_arquitectura_s5.py (B, Tarea 6) — las dos páginas nuevas abren el caso
PAGINAS_QUE_ABREN_EL_CASO = (
    "actualizacion", "catalogo", "componer", "elaborar", "escenarios", "historico", "hoja",
    "indices", "precios_empresa", "similares", "simulador",
)
```
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/unit/test_texto_seguro.py tests/unit/test_arquitectura_s1.py tests/unit/test_arquitectura_s5.py tests/unit/test_ui_indices.py tests/unit/test_ui_precios_empresa.py tests/unit/test_ui_app.py tests/unit/test_ui_importable.py tests/unit/test_arquitectura.py -q -W error`; ruff de los archivos.
- [ ] **Paso 5: Commit**
```bash
git add tests/unit/test_texto_seguro.py tests/unit/test_arquitectura_s1.py tests/unit/test_ui_indices.py tests/unit/test_ui_precios_empresa.py
git commit -m "test(ui): pantallas de UC-17 y texto seguro en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add ui/texto_seguro.py ui/indices.py ui/precios_empresa.py ui/paginas/indices.py ui/paginas/precios_empresa.py ui/app.py tests/unit/test_ui_app.py tests/unit/test_ui_importable.py tests/unit/test_arquitectura_s5.py
git commit -m "feat(ui): indices del BCV y precios de la empresa (UC-17)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Tarea 10: Hoja — moneda en Parámetros y origen, erosión y R11/R12 en Precios

**Rama:** `inc/060-s1-3-ui`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `tests/integration/test_hoja_moneda.py`
- Modificar: `ui/hoja.py:316-343` (`Borrador.reglas_extra`), `:664-729` (`elaborar_hoja(..., reglas_extra=())`), `:731-755` (`elaborar_borrador` pasa `borrador.reglas_extra`), `:1459` (`MOTIVOS_QUE_HEREDAN_EL_ESPACIO` + `"conversion"`), `:1588-1661` (`abrir_version(..., fecha_evaluacion=None)`), `:1805-1921` (`crear_primera_version(..., lista=None)` con rechazo de moneda), `:2121-2185` (`COLUMNAS_PRECIOS`, `FilaPrecio`, `precios_de_version`), nueva `convertir(...)`; `ui/paginas/hoja.py:1209-1241` (columnas nuevas), `:1334-1356` (moneda y conversión en Parámetros); `ui/proyectos.py:76-106` (`crear_proyecto_nuevo(ruta, nombre, moneda=None)`); `ui/barra.py:113-121,146-170` (selector de moneda sin valor por defecto)
- Pruebas que cambian con el comportamiento especificado (no son de regresión): `tests/unit/test_ui_proyectos.py` (una prueba nueva), `tests/unit/test_ui_barra.py:245-247` (`_crear` elige la moneda; una prueba nueva), `tests/unit/test_ui_hoja.py:279-283` (la Auditoría de la hoja abierta hoy suma R11/R12, S1 §4.3)

**Interfaces:**
- Produce: `Borrador.reglas_extra: tuple[ReglaVerificacion, ...] = ()`; `abrir_version(sesion, catalogo, proyecto, codigo, *, responsable="sistema", ahora=None, fecha_evaluacion: date | None = None)` (con fecha: reaudita además con `reglas_precios(instantanea_precios(..., fecha_evaluacion))` en memoria y deja esas reglas en `borrador.reglas_extra`; sin fecha, igual que hoy); `FilaPrecio` gana al final `moneda_original=""`, `precio_original=None`, `fuente_tasa=""`, `fuente=""`, `propio: bool | None = None`, `erosion_usd=None`, `erosion_bs=None`, `erosion_pct=None`, `erosion_indice=None` y `fecha` pasa a ser la del precio; `precios_de_version(sesion, proyecto, codigo, *, fecha_evaluacion=None, serie_indice=None, lado=LADO_POR_DEFECTO)`; `convertir(sesion, catalogo, proyecto, codigo, moneda, *, lado, fecha, fuente, responsable) -> str` (código nuevo; `HojaInvalida` con el mensaje de `TasaNoDisponible`); `crear_proyecto_nuevo(ruta, nombre, moneda: str | None = None)`.

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/integration/test_hoja_moneda.py
from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from core import models
from core.catalog import Catalogo
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from tests.fixtures.versiones import elaborar_001, guardar_001
from ui import hoja


@pytest.fixture
def clinica(sesion):
    proyecto = sesion.scalars(select(models.Proyecto)).one()
    guardar_001(sesion, proyecto, elaborar_001(sesion))
    registrar_importacion(sesion, definicion_tasa("venta"), [Observacion(date(2026, 10, 1),
                          D("860.18"))], archivo="FUENTE.md", huella="d" * 64,
                          fuente="https://www.bcv.org.ve/", fecha_descarga=date(2026, 10, 8),
                          responsable="A", filas_leidas=1, filas_rechazadas=0)
    sesion.commit()
    return sesion, proyecto.nombre


def test_convertir_desde_la_hoja_abre_la_version_en_bs_y_hereda_el_espacio(clinica):
    sesion, nombre = clinica
    nuevo = hoja.convertir(sesion, Catalogo(sesion), nombre, "001", "Bs", lado="venta",
                           fecha=date(2026, 10, 3), fuente="cambio", responsable="Ing.")
    abierta = hoja.abrir_version(sesion, Catalogo(sesion), nombre, nuevo)
    assert abierta.borrador.moneda == "Bs"
    assert "conversion" in hoja.MOTIVOS_QUE_HEREDAN_EL_ESPACIO


def test_sin_tasa_en_7_dias_la_hoja_lo_dice_y_no_escribe(clinica):
    sesion, nombre = clinica
    with pytest.raises(hoja.HojaInvalida, match="7 dias"):
        hoja.convertir(sesion, Catalogo(sesion), nombre, "001", "Bs", lado="venta",
                       fecha=date(2026, 10, 12), fuente="cambio", responsable="Ing.")


def test_precios_muestran_seis_datos_erosion_26_37_y_estado_r12(clinica):
    sesion, nombre = clinica
    filas = hoja.precios_de_version(sesion, nombre, "001", fecha_evaluacion=date(2026, 10, 1))
    assert all(f.moneda_original == "USD" and f.fuente for f in filas)
    assert all("R12 ADVERTENCIA" in f.estado for f in filas)  # precios del 28/04/2026, vencidos
    assert all(f.erosion_bs == D(0) for f in filas)  # originales en USD: erosión 0 declarada


def test_abrir_con_fecha_reaudita_en_memoria_sin_tocar_los_guardados(clinica):
    sesion, nombre = clinica
    sin = hoja.abrir_version(sesion, Catalogo(sesion), nombre, "001")
    con = hoja.abrir_version(sesion, Catalogo(sesion), nombre, "001",
                             fecha_evaluacion=date(2026, 10, 1))
    assert not [h for h in sin.guardada.informe.hallazgos if h.regla in ("R11", "R12")]
    assert [h for h in con.guardada.informe.hallazgos if h.regla == "R12"]
    assert not sesion.scalars(select(models.Hallazgo).where(models.Hallazgo.regla == "R12")).all()
```
```python
# tests/unit/test_ui_proyectos.py — importar además `from sqlalchemy import select`,
# `from core import models`, `from core.catalog import Catalogo, abrir_sesion, crear_motor` y
# `from ui import hoja`; al final:
def test_proyecto_nuevo_con_moneda_declara_moneda_proyecto(base):
    """UC-01 paso 1 (enmienda de S1): la moneda elegida queda en `moneda_proyecto`, y la primera
    version no se valora con una lista de otra moneda (RF-65)."""
    ruta, _ = base
    assert proyectos.crear_proyecto_nuevo(ruta, "Obra en Bs", "Bs") == "Obra en Bs"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            proyecto = sesion.scalars(
                select(models.Proyecto).where(models.Proyecto.nombre == "Obra en Bs")
            ).one()
            filas = sesion.scalars(
                select(models.MonedaProyecto)
                .where(models.MonedaProyecto.proyecto_id == proyecto.id)
            ).all()
            assert [fila.moneda for fila in filas] == ["Bs"]
            with pytest.raises(hoja.HojaInvalida, match="Bs"):
                hoja.crear_primera_version(
                    sesion, Catalogo(sesion), "Obra en Bs",
                    hoja.Borrador(fecha=linea_base.FECHA_LINEA_BASE),
                    fuente="plano A-01", responsable="Ing. Prueba",
                )
    finally:
        motor.dispose()


def test_sin_moneda_el_proyecto_no_declara_ninguna(base):
    ruta, _ = base
    proyectos.crear_proyecto_nuevo(ruta, "Obra sin moneda")
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            assert not sesion.scalars(select(models.MonedaProyecto)).all()
    finally:
        motor.dispose()
```
```python
# tests/unit/test_ui_barra.py:245-247 — `_crear` elige la moneda (UC-01 paso 1: sin valor por
# defecto); y una prueba nueva tras test_proyecto_nuevo_no_se_crea_dos_veces
def _crear(at: AppTest, nombre: str, moneda: str | None = "USD") -> AppTest:
    at.text_input(key=barra.CLAVE_NOMBRE_NUEVO).set_value(nombre)
    if moneda is not None:
        at.selectbox(key=barra.CLAVE_MONEDA_NUEVA).select(moneda)
    return _boton(at, barra.ROTULO_CREAR).click().run()


def test_proyecto_nuevo_sin_moneda_se_rechaza_con_mensaje(monkeypatch, caso):
    at = _crear(_barra(monkeypatch, caso), "Torre B", moneda=None)
    assert "Elija la moneda" in _textos(at)
    assert _abierto(at) is None
    assert "Torre B" not in at.selectbox(key=barra.CLAVE_ABRIR).options
```
```python
# tests/unit/test_ui_hoja.py:279-283 — la hoja abre la version a la fecha de hoy (S1 §4.3): R11 y
# R12 se suman a la auditoria del borrador; las 33 de R8 no cambian
def test_la_pestana_auditoria_lista_los_hallazgos_con_su_origen(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Auditoría"})

    detalle = next(d.value for d in at.dataframe if "Origen" in d.value.columns)
    assert set(detalle["Regla"]) - {"R11", "R12"} == {"R8"}
    assert (detalle["Regla"] == "R8").sum() == 33
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/integration/test_hoja_moneda.py tests/unit/test_ui_proyectos.py tests/unit/test_ui_barra.py -v -W error`
Esperado: FAIL con `AttributeError: module 'ui.hoja' has no attribute 'convertir'`, `TypeError: crear_proyecto_nuevo() takes 2 positional arguments but 3 were given` y `AttributeError: module 'ui.barra' has no attribute 'CLAVE_MONEDA_NUEVA'`
- [ ] **Paso 3: Implementación mínima**
```python
# ui/hoja.py — importaciones nuevas (en su lugar alfabético)
from core.budget.instantanea import composiciones_de_version, instantanea_precios
from core.budget.moneda import convertir_version, moneda_del_proyecto
from core.catalog.empresa import es_heredado, lista_de_referencia
from core.catalog.indices import LADO_POR_DEFECTO, tasa_aplicable, valor_en
from core.catalog.moneda import Erosion, TasaDeclarada, erosion, erosion_por_indice
from core.verification.precios import estado_por_insumo, reglas_precios
# y bajo `if TYPE_CHECKING:`
    from core.contracts.verificacion import ReglaVerificacion
    from core.verification.precios import PrecioAuditado
```
```python
# ui/hoja.py:316-343 — `Borrador` gana un campo al final (y una viñeta en su docstring:
# «`reglas_extra`: R11 y R12 evaluadas al abrir, a la fecha de hoy (S1 §4.3); no son un cambio»)
    cantidades: Mapping[str, Decimal] = field(default_factory=dict)
    reglas_extra: tuple[ReglaVerificacion, ...] = field(default=(), compare=False)
```
```python
# ui/hoja.py:664-729 — `elaborar_hoja`: un parámetro más al final de la firma y la tupla de reglas
    cantidades: Mapping[str, Decimal] | None = None,
    reglas_extra: Sequence[ReglaVerificacion] = (),
) -> ResultadoHoja:
# y en la llamada a `elaborar` (:706-715):
        reglas=(*REGLAS, *reglas_espacio(espacio, escritas), *reglas_extra),
```
```python
# ui/hoja.py:731-755 — `elaborar_borrador` pasa las reglas del borrador
    return elaborar_hoja(
        borrador.espacio,
        borrador.composiciones,
        codigo=codigo,
        fecha=borrador.fecha,
        especialidad=especialidad,
        items_base=borrador.items_base,
        parametros=borrador.parametros,
        moneda=borrador.moneda,
        plan=borrador.plan,
        cantidades=borrador.cantidades,
        reglas_extra=borrador.reglas_extra,
    )
```
```python
# ui/hoja.py:1459
MOTIVOS_QUE_HEREDAN_EL_ESPACIO = ("restauracion", "cotizacion", "revaloracion", "conversion")
```
```python
# ui/hoja.py:1588-1661 — `abrir_version`: firma, docstring (punto 5) y las dos líneas que cambian
def abrir_version(
    sesion: Session,
    catalogo: Catalogo,
    proyecto: str,
    codigo: str,
    *,
    responsable: str = "sistema",
    ahora: datetime | None = None,
    fecha_evaluacion: date | None = None,
) -> VersionAbierta:
    """Abre una version guardada como borrador editable (RF-52), sea de la hoja o no (FR-5).

    1. `asegurar_instantanea`: una version sin instantanea (clinica, TI-001, importadas) la
       crea desde el catalogo vigente si este todavia reproduce su precio, y lo **registra**
       (UC-15e). Es la unica escritura al abrir y se confirma aqui.
    2. Espacio por `espacio_de_version`; composiciones, parametros y plan de la version.
    3. Los items guardados se separan en los del espacio y los de la version, y las cantidades
       diferentes de la derivada son cantidades escritas a mano.
    4. La version se recarga con `REGLAS + reglas_espacio(espacio)`: R8 a R10 se recalculan
       sobre la instantanea del espacio y reemplazan las guardadas (§8.4).
    5. Con `fecha_evaluacion` (la pantalla pasa hoy, M §3.3), R11 y R12 se evaluan a esa fecha
       sobre la instantanea de precios de la version, **solo en memoria**: entran a la recarga y
       quedan en `borrador.reglas_extra`; ninguna fila guardada cambia (S1 §4.3).

    `HojaInvalida` si la version no existe o ya no se puede reconstruir.
    """
# dentro del `try`, justo antes de `guardada = cargar_elaboracion(...)`:
        extra: tuple[ReglaVerificacion, ...] = ()
        if fecha_evaluacion is not None:
            extra = reglas_precios(
                instantanea_precios(sesion, modelo, lista_de_referencia(sesion), fecha_evaluacion)
            )
        guardada = cargar_elaboracion(
            sesion,
            proyecto,
            codigo,
            catalogo,
            reglas=(*REGLAS, *reglas_espacio(espacio, cantidades), *extra),
        )
# y el `Borrador(...)` del final gana `reglas_extra=extra,` tras `cantidades=escritas,`
```
```python
# ui/hoja.py:1805-1921 — `crear_primera_version`: `lista` opcional y la moneda del proyecto.
# En la firma, tras `ahora`:
    lista: models.ListaPrecios | None = None,
# y el bloque desde `fecha = fecha or borrador.fecha` hasta `completar_composiciones` queda:
    fecha = fecha or borrador.fecha
    moneda = moneda_del_proyecto(sesion, modelo_proyecto)
    if lista is None:
        try:
            lista = catalogo.lista_vigente(fecha)
        except CatalogoIncompleto as error:
            raise HojaInvalida(
                f"No hay una lista de precios vigente al {fecha:%d/%m/%Y}: cargue una en "
                "Actualizar precios (o cambie la fecha del presupuesto) y vuelva a guardar."
            ) from error
    if lista.moneda != moneda:
        raise HojaInvalida(
            f"El proyecto {proyecto!r} esta en {moneda} y la lista {lista.nombre!r} en "
            f"{lista.moneda}: una version solo se valora con una lista de su moneda (RF-65). "
            "Elija una lista en la moneda del proyecto (Precios de la empresa) y vuelva a "
            "guardar."
        )
    borrador = completar_composiciones(
        catalogo, replace(borrador, fecha=fecha, moneda=moneda), lista=lista
    )
```
```python
# ui/hoja.py — nueva `convertir`, tras `retirar_cotizacion` (:1998-2020)
def convertir(
    sesion: Session,
    catalogo: Catalogo,
    proyecto: str,
    codigo: str,
    moneda: str,
    *,
    lado: str,
    fecha: date,
    fuente: str,
    responsable: str,
) -> str:
    """RF-64 desde Parametros: la version `codigo` convertida a `moneda` con la tasa del BCV
    aplicable a `fecha` (hoy, en pantalla; S1-R1, S1-R2). Devuelve el codigo de la version nueva.
    Sin tasa en los 7 dias anteriores, `HojaInvalida` con el motivo y nada escrito."""
    try:
        tasa = TasaDeclarada.de_importacion(tasa_aplicable(sesion, fecha, lado=lado))
        nuevo = siguiente_codigo(sesion, proyecto)
        convertir_version(sesion, proyecto, codigo, nuevo, moneda, tasa, fuente=fuente,
                          responsable=responsable, catalogo=catalogo)
        sesion.commit()
    except ValueError as error:  # TasaNoDisponible es ValueError
        sesion.rollback()
        raise HojaInvalida(f"No se convirtio nada: {error}") from error
    except BaseException:
        sesion.rollback()
        raise
    return nuevo
```
```python
# ui/hoja.py:2121-2185 — columnas, fila y lectura de los precios con su origen
COLUMNAS_PRECIOS = (
    "Insumo",
    "Código",
    "Tipo",
    "Precio",
    "Lista",
    "Moneda",
    "Fecha del precio",
    "Tasa",
    "Fecha de la tasa",
    "Referencia",
    "Cotización",
    "Moneda original",
    "Precio original",
    "Fuente de la tasa",
    "Fuente",
    "Propio/heredado",
    "Erosión USD",
    "Erosión Bs",
    "Erosión %",
    "Erosión por índice",
    "Estado",
)


@dataclass(frozen=True, slots=True)
class FilaPrecio:
    """El origen del precio de un insumo (pestana Precios, RF-56 y RF-65): lista, referencia,
    fecha **del precio**, moneda y precio originales, tasa con su fecha y su fuente, fuente del
    precio, propio o heredado (lista de empresa) y, con fecha de evaluacion, la erosion en las dos
    monedas, su porcentaje (S1 §5.3) y la erosion por indice; `estado` marca el que no tiene
    fuente o fecha y suma el texto de R11 y R12 de la misma evaluacion."""

    codigo: str
    descripcion: str
    tipo: str
    precio: Decimal
    lista: str
    moneda: str
    fecha: date
    tasa: Decimal | None
    fecha_tasa: date | None
    referencia: str
    cotizacion: str
    alcance: str
    estado: str
    moneda_original: str = ""
    precio_original: Decimal | None = None
    fuente_tasa: str = ""
    fuente: str = ""
    propio: bool | None = None
    erosion_usd: Decimal | None = None
    erosion_bs: Decimal | None = None
    erosion_pct: Decimal | None = None
    erosion_indice: Decimal | None = None


def texto_propio(propio: bool | None) -> str:
    """«propio», «heredado» o vacio (la lista no es de empresa)."""
    return "" if propio is None else ("propio" if propio else "heredado")


def _erosion_de(
    auditado: PrecioAuditado | None, tasa_evaluacion: Decimal | None
) -> Erosion | None:
    """La erosion del precio original con su T0 (declarada o la del BCV a su fecha) y T1 (S1 §5.3);
    `None` sin evaluacion o sin alguna de las dos tasas. Un original en USD da 0 (declarado)."""
    if auditado is None:
        return None
    t0 = auditado.tasa or auditado.tasa_a_su_fecha
    if auditado.moneda_original == "USD":
        return erosion(auditado.precio_original, "USD", t0 or Decimal(1),
                       tasa_evaluacion or Decimal(1))
    if t0 is None or tasa_evaluacion is None:
        return None
    return erosion(auditado.precio_original, "Bs", t0, tasa_evaluacion)


def _erosion_por_indice_de(
    sesion: Session, origen: OrigenPrecio, serie: str | None, fecha: date | None
) -> Decimal | None:
    """P·(I1/I0 − 1) en Bs con el indice del mes del precio y el del mes de evaluacion (columna
    aparte, no se suma); `None` sin serie, sin evaluacion, para un original en USD o sin indice."""
    if serie is None or fecha is None or origen.moneda_original != "Bs":
        return None
    desde = origen.fecha_precio or origen.fecha_vigencia
    inicial = valor_en(sesion, serie, date(desde.year, desde.month, 1))
    final = valor_en(sesion, serie, date(fecha.year, fecha.month, 1))
    if inicial is None or final is None or origen.precio_original is None:
        return None
    return erosion_por_indice(origen.precio_original, inicial.valor, final.valor)


def precios_de_version(
    sesion: Session,
    proyecto: str,
    codigo: str,
    *,
    fecha_evaluacion: date | None = None,
    serie_indice: str | None = None,
    lado: str = LADO_POR_DEFECTO,
) -> list[FilaPrecio]:
    """El origen de cada precio que usa la version, ordenado por codigo de insumo (§9.6).

    Sin `fecha_evaluacion`, el origen (S1 §5.1) sin erosion y el Estado de siempre. Con ella (la
    pantalla pasa hoy), la erosion y el texto de R11 y R12 de **esa** evaluacion, en memoria
    (M §3.3): nada se escribe. Con `serie_indice`, ademas la erosion por indice."""
    modelo = _modelo(sesion, proyecto, codigo)
    lista = modelo.lista_precios
    por_insumo = {precio.insumo_id: precio for precio in lista.precios}
    auditados: dict[int, PrecioAuditado] = {}
    textos: dict[int, list[str]] = {}
    tasa_evaluacion: Decimal | None = None
    if fecha_evaluacion is not None:
        instantanea = instantanea_precios(
            sesion, modelo, lista_de_referencia(sesion), fecha_evaluacion, lado=lado
        )
        auditados = {a.insumo_id: a for a in instantanea.precios}
        textos = estado_por_insumo(instantanea)
        tasa_evaluacion = instantanea.tasa_evaluacion
    filas = []
    for o in origen_de_precios(sesion, modelo):
        heredado = es_heredado(sesion, lista, por_insumo[o.insumo_id])
        perdida = _erosion_de(auditados.get(o.insumo_id), tasa_evaluacion)
        avisos = [aviso for aviso in (_estado_de_precio(o),) if aviso != TEXTO_OK]
        avisos += textos.get(o.insumo_id, [])
        filas.append(
            FilaPrecio(
                codigo=o.codigo,
                descripcion=o.descripcion,
                tipo=o.tipo,
                precio=o.precio,
                lista=o.lista,
                moneda=o.moneda,
                fecha=o.fecha_precio or o.fecha_vigencia,
                tasa=o.tasa,
                fecha_tasa=o.fecha_tasa,
                referencia=o.referencia,
                cotizacion=o.cotizacion,
                alcance=o.alcance,
                estado="; ".join(avisos) or TEXTO_OK,
                moneda_original=o.moneda_original,
                precio_original=o.precio_original,
                fuente_tasa=o.fuente_tasa,
                fuente=o.fuente,
                propio=None if heredado is None else not heredado,
                erosion_usd=None if perdida is None else perdida.usd,
                erosion_bs=None if perdida is None else perdida.bs,
                erosion_pct=None if perdida is None else perdida.porcentaje,
                erosion_indice=_erosion_por_indice_de(sesion, o, serie_indice, fecha_evaluacion),
            )
        )
    return filas
```
```python
# ui/hoja.py:2200-2222 — `tabla_de_precios`: las columnas nuevas, en el orden de COLUMNAS_PRECIOS
def tabla_de_precios(precios: Sequence[FilaPrecio]) -> TablaExportable:
    """La hoja Precios: una fila por insumo, con precios, tasas y erosiones como numeros (la
    erosion en porcentaje ya multiplicada por 100)."""
    return TablaExportable(
        "Precios",
        COLUMNAS_PRECIOS,
        tuple(
            (
                p.descripcion,
                p.codigo,
                p.tipo,
                p.precio,
                p.lista,
                p.moneda,
                p.fecha,
                p.tasa,
                p.fecha_tasa,
                p.referencia,
                p.cotizacion,
                p.moneda_original,
                p.precio_original,
                p.fuente_tasa,
                p.fuente,
                texto_propio(p.propio),
                p.erosion_usd,
                p.erosion_bs,
                None if p.erosion_pct is None else p.erosion_pct * 100,
                p.erosion_indice,
                p.estado,
            )  # fmt: skip
            for p in precios
        ),
    )
```
```python
# ui/paginas/hoja.py — importaciones nuevas
from core.budget.moneda import moneda_del_proyecto
from core.catalog.moneda import MONEDAS
```
```python
# ui/paginas/hoja.py:238 (`_abrir`) — la hoja en vivo evalua R11 y R12 a hoy (M §3.3)
                abierta = hoja.abrir_version(
                    sesion, Catalogo(sesion), proyecto, codigo, fecha_evaluacion=date.today()
                )
# ui/paginas/hoja.py:458 (`_preparar_excel`) — la hoja Precios del libro con la misma evaluacion
                precios = hoja.precios_de_version(
                    sesion, abierta.proyecto, abierta.codigo, fecha_evaluacion=date.today()
                )
```
```python
# ui/paginas/hoja.py:1209-1241 — `_pestana_precios`: la lectura y la tabla
def _monto(valor: Decimal | None) -> str:
    return "" if valor is None else formatear_decimal(valor, DECIMALES_PRESENTACION)


def _pestana_precios(cambios: Sequence) -> None:
    abierta = _abierta()
    if abierta is None:
        st.info("Abra una version guardada para ver el origen de sus precios.")
        return
    with _sesion() as sesion:
        precios = hoja.precios_de_version(
            sesion, abierta.proyecto, abierta.codigo, fecha_evaluacion=date.today()
        )
    st.caption(
        "Lista, referencia, fecha, moneda y tasa de cada insumo, su origen y cuanto valor perdio "
        "hasta hoy (erosion). Una cotizacion (con su proveedor, numero y fecha) vale solo para "
        "este proyecto y prevalece sobre la lista global hasta que se retire."
    )
    st.dataframe(
        DataFrame(
            {
                "Insumo": [p.descripcion for p in precios],
                "Codigo": [p.codigo for p in precios],
                "Precio": [formatear_decimal(p.precio, DECIMALES_PRESENTACION) for p in precios],
                "Lista": [p.lista for p in precios],
                "Moneda": [p.moneda for p in precios],
                "Fecha del precio": [p.fecha.isoformat() for p in precios],
                "Tasa": ["" if p.tasa is None else f"{p.tasa:f}" for p in precios],
                "Fecha de la tasa": [
                    "" if p.fecha_tasa is None else p.fecha_tasa.isoformat() for p in precios
                ],
                "Referencia": [p.referencia for p in precios],
                "Cotizacion": [p.cotizacion for p in precios],
                "Moneda original": [p.moneda_original for p in precios],
                "Precio original": [_monto(p.precio_original) for p in precios],
                "Fuente de la tasa": [p.fuente_tasa for p in precios],
                "Fuente": [p.fuente for p in precios],
                "Propio/heredado": [hoja.texto_propio(p.propio) for p in precios],
                "Erosion USD": [_monto(p.erosion_usd) for p in precios],
                "Erosion Bs": [_monto(p.erosion_bs) for p in precios],
                "Erosion %": [
                    _monto(None if p.erosion_pct is None else p.erosion_pct * 100) for p in precios
                ],
                "Erosion por indice": [_monto(p.erosion_indice) for p in precios],
                "Estado": [p.estado for p in precios],
            }
        ),
        hide_index=True,
        width="stretch",
    )
# Las lineas 1242-1321 de la funcion (cotizar y retirar una cotizacion) no cambian.
```
```python
# ui/paginas/hoja.py:1334-1356 — `_pestana_parametros` muestra la moneda y ofrece cambiarla
def _pestana_parametros() -> None:
    borrador, siembra = _borrador(), _partida()
    st.caption(
        "Los parametros de costo de esta version. Cambiarlos recalcula todos sus APU; el cambio "
        "queda en el registro con su fuente."
    )
    textos = {}
    columnas = st.columns(len(hoja.CAMPOS_PARAMETROS))
    for campo, columna in zip(hoja.CAMPOS_PARAMETROS, columnas, strict=True):
        textos[campo] = columna.text_input(
            _ROTULOS_PARAMETROS[campo],
            value=str(getattr(siembra.parametros, campo)),
            key=_clave("param", campo),
        )
    try:
        parametros = hoja.parametros_desde_texto(textos)
        if parametros != borrador.parametros:
            _poner_borrador(replace(borrador, parametros=parametros))
    except hoja.HojaInvalida as error:
        st.error(f"{error}. La hoja sigue con los ultimos parametros validos.")
    resultado, cambios = _calculo()
    presupuesto = resultado.elaboracion.presupuesto
    st.metric("Total del presupuesto", _dinero(presupuesto.total, presupuesto.moneda))
    _moneda(cambios)


def _moneda(cambios: Sequence) -> None:
    """RF-64: la moneda del proyecto y su cambio, que crea una version convertida (S1 §5.3)."""
    abierta = _abierta()
    if abierta is None:
        return
    with _sesion() as sesion:
        if sesion is None:
            return
        proyecto = sesion.scalars(
            select(models.Proyecto).where(models.Proyecto.nombre == abierta.proyecto)
        ).one()
        actual = moneda_del_proyecto(sesion, proyecto)
    st.markdown(f"**Moneda del proyecto:** {actual}")
    if cambios:
        st.warning(
            "Cambiar la moneda crea una version nueva desde la guardada: guarde o descarte primero "
            f"los {len(cambios)} cambios pendientes."
        )
        return
    with st.form("hoja_moneda"):
        st.markdown("**Cambiar la moneda** (crea una version convertida; la actual no cambia)")
        destino = st.selectbox("Moneda destino", [m for m in MONEDAS if m != actual])
        lado = st.selectbox("Tasa del BCV", ("venta", "compra"), help="Por defecto, venta (S1-R1).")
        fuente = st.text_input("Por que se cambia la moneda (fuente)")
        responsable = st.text_input("Responsable del cambio")
        enviar = st.form_submit_button("Convertir la version")
    if not enviar:
        return
    try:
        with _sesion() as sesion:
            nuevo = hoja.convertir(
                sesion, Catalogo(sesion), abierta.proyecto, abierta.codigo, destino, lado=lado,
                fecha=date.today(), fuente=fuente, responsable=responsable,
            )
    except hoja.HojaInvalida as error:
        st.error(str(error))
    except SQLAlchemyError as error:
        st.error(_error_de_base(error))
    else:
        _mensaje("success", f"Se guardo la version {nuevo}, convertida a {destino}.")
        _reabrir_nueva(nuevo)
        st.rerun()
```
```python
# ui/proyectos.py:76-106 — `crear_proyecto_nuevo` con la moneda elegida (UC-01 paso 1). Importar
# `from core.budget.moneda import declarar_moneda` y `from core.catalog.moneda import MONEDAS`.

#: Las monedas que ofrece la barra al crear un proyecto (sin valor por defecto en la interfaz).
MONEDAS_DEL_PROYECTO = MONEDAS
#: Quien declara la moneda al crear desde la barra: en la 0.6.0 no hay cuentas (S3 las trae).
RESPONSABLE_DE_LA_INTERFAZ = "interfaz (sin cuentas hasta S3)"


def crear_proyecto_nuevo(ruta: Path, nombre: str, moneda: str | None = None) -> str:
    """Crea el proyecto y devuelve su nombre limpio. Con `moneda`, la declara en `moneda_proyecto`
    (UC-01 paso 1, S1); sin ella el proyecto queda como antes (USD por defecto de `elaborar`).
    `ProyectoInvalido` si el nombre queda vacio, ya existe (sin distinguir mayusculas), la moneda
    no es Bs ni USD o el caso no existe."""
    limpio = " ".join(nombre.split())  # sin espacios sobrantes ni dobles
    if not limpio:
        raise ProyectoInvalido("Escriba un nombre para el proyecto: no puede quedar vacio.")
    if not ruta.exists():
        raise ProyectoInvalido(
            f"El caso {ruta} no existe todavia: abra o siembre un caso en el Inicio antes de "
            "crear un proyecto."
        )
    motor = crear_motor(_url(ruta))
    try:
        with abrir_sesion(motor) as sesion:
            # En Python: `lower()` de SQLite solo conoce el ASCII y «CLINICA» no es «clinica».
            existe = any(
                otro.casefold() == limpio.casefold()
                for otro in sesion.scalars(select(models.Proyecto.nombre))
            )
            if existe:
                raise ProyectoInvalido(
                    f"Ya existe un proyecto llamado «{limpio}»: elija otro nombre o abra ese."
                )
            try:
                proyecto = crear_proyecto(sesion, limpio)
                if moneda is not None:
                    declarar_moneda(
                        sesion, proyecto, moneda, responsable=RESPONSABLE_DE_LA_INTERFAZ
                    )
            except ValueError as error:  # el nucleo repite las reglas; por si cambian
                raise ProyectoInvalido(str(error)) from error
            sesion.commit()
    finally:
        motor.dispose()
    return limpio
```
```python
# ui/barra.py — la moneda del proyecto nuevo, sin valor por defecto (UC-01 paso 1)
from ui.proyectos import (
    MONEDAS_DEL_PROYECTO,
    ProyectoInvalido,
    crear_proyecto_nuevo,
    listar_proyectos,
    resumen_auditoria,
    version_vigente,
)

CLAVE_MONEDA_NUEVA = "barra_proyecto_moneda"
MENSAJE_SIN_MONEDA = "Elija la moneda del proyecto (Bs o USD): no tiene valor por defecto."


def _crear_proyecto() -> None:
    moneda = st.session_state.get(CLAVE_MONEDA_NUEVA)
    if moneda is None:
        st.session_state[CLAVE_MENSAJE] = ("error", MENSAJE_SIN_MONEDA)
        return
    try:
        nombre = crear_proyecto_nuevo(
            ruta_caso(), st.session_state.get(CLAVE_NOMBRE_NUEVO, ""), moneda
        )
    except ProyectoInvalido as error:
        st.session_state[CLAVE_MENSAJE] = ("error", str(error))
        return
    fijar_proyecto(nombre)
    st.session_state[CLAVE_NOMBRE_NUEVO] = ""
    st.session_state[CLAVE_MONEDA_NUEVA] = None
    st.session_state[CLAVE_MENSAJE] = (
        "exito", f"Proyecto «{nombre}» creado y abierto en {moneda}."
    )


# en `_pintar_proyecto`, entre el `st.text_input` del nombre y el boton Crear proyecto:
    st.selectbox(
        "Moneda del proyecto",
        MONEDAS_DEL_PROYECTO,
        index=None,
        placeholder="Elija Bs o USD",
        key=CLAVE_MONEDA_NUEVA,
    )
```
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/integration/test_hoja_moneda.py tests/unit/test_ui_proyectos.py tests/integration/test_hoja_versiones.py tests/unit/test_ui_hoja.py tests/unit/test_excel_hoja.py tests/unit/test_ui_barra.py -q -W error`; `uv run pytest -q -W error`. **Compuerta GS1‑3:** meta `--hasta S1-3` OK, CI verde, cuatro encargos; fusionar.
- [ ] **Paso 5: Commit**
```bash
git add tests/integration/test_hoja_moneda.py tests/unit/test_ui_proyectos.py tests/unit/test_ui_barra.py tests/unit/test_ui_hoja.py
git commit -m "test(ui): moneda del proyecto y precios con erosion en la hoja en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add ui/hoja.py ui/paginas/hoja.py ui/proyectos.py ui/barra.py
git commit -m "feat(ui): moneda en Parametros, origen, erosion y R11-R12 en Precios" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

# S1‑4 — SL‑E3 (núcleo `inc/060-s1-4-nucleo`; luego `inc/060-s1-4-ui`)

### Tarea 11: SL‑E3a — reajuste puro contra las memorias

**Rama:** `inc/060-s1-4-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/budget/reajuste.py`, `tests/unit/test_reajuste.py`
- Modificar: `docs/bitacora/2026-10-silice-expedientes.md` (SL‑E3), `core/budget/__init__.py`

**Interfaces:**
- Produce: `COMPONENTES = ("materiales", "equipos", "mano_obra")`; `Mecanismo`, `Estructura`, `EstadoEstudio` (`CERRADO = "cerrado"`, `PARCIAL = "parcial al corte"`); `Componente(componente, serie, peso=None)`; `Clausula(fecha_inicio, duracion_meses, fecha_referencia_primer_anio, periodicidad, mecanismo, estructura, componentes, fecha_base_indices, r, fuente_r, fuente, responsable, mecanismo_pagadero=None, fuente_pagadero="", r_en_comprobacion=False)`; `PartidaContrato(codigo, pu, resultado, presupuestado)`; `Ejecutado(codigo, cantidad, fuente)`; `PeriodoDeclarado(desde, hasta, ejecutado, version_comprobacion="", excepcion="")`; `Comparacion`; `ResultadoPeriodo`; `ResultadoEstudio`; `coeficiente(pesos, base, periodo)`, `coeficiente_de_partida(resultado, base, periodo)`, `reajuste_escalatorio(clausula, contrato, reajustables, base, periodo)`, `reajuste_por_comprobacion(reajustables, pu_contrato, pu_comprobado, r=0)`, `comparar_reajustes(escalatoria, comprobacion, *, moneda, tasa) -> Comparacion`, `calcular_estudio(clausula, contrato, periodos, indices, *, moneda, tasas, pu_comprobados, monto_original, fecha_calculo, series_en_bs=frozenset()) -> ResultadoEstudio`.

- [ ] **Paso 0: Expediente SL‑E3** (S1 §11: H‑D3, RF‑70, RF‑71, arts. 133–134 en transcripción; genérico para obras y servicios; prueba = las dos memorias, fronteras del primer año y de 3f, recálculo exacto; módulo nuevo y tablas aditivas; costo: cambiar una función pura y su memoria). Commit `docs(bitacora): expediente SL-E3`.
- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/unit/test_reajuste.py
"""Oráculos: memorias s1_reajuste.md y s1_reajuste_por_partida.md; fronteras de S1 §9.2."""
from datetime import date
from decimal import Decimal as D

import pytest

from core.budget.reajuste import (
    Clausula, Componente, Ejecutado, EstadoEstudio, Estructura, Mecanismo, PartidaContrato,
    PeriodoDeclarado, calcular_estudio, coeficiente_de_partida)
from core.catalog.indices import ValorFechado
from core.contracts.apu import ResultadoAPU

ENERO, FEBRERO = date(2026, 1, 1), date(2027, 2, 1)
SERIES = {"materiales": "FIC-MAT", "equipos": "FIC-EQU", "mano_obra": "FIC-MO"}
VALORES = {"FIC-MAT": ("200", "230"), "FIC-EQU": ("150", "165"), "FIC-MO": ("80", "100")}
C2 = D("0.01")


def _indices(provisional=False, sin=()):
    salida = {}
    for n, (serie, (i0, im)) in enumerate(VALORES.items()):
        salida[(serie, ENERO)] = ValorFechado(serie, ENERO, D(i0), False, n + 1)
        if serie not in sin:
            salida[(serie, FEBRERO)] = ValorFechado(serie, FEBRERO, D(im), provisional, n + 10)
    return salida


def _clausula(estructura=Estructura.DECLARADA, mecanismo=Mecanismo.AMBOS, pagadero=None,
              pesos=("0.5", "0.2", "0.3"), duracion=24, inicio=date(2026, 1, 15)):
    componentes = tuple(Componente(c, s, D(p) if estructura is Estructura.DECLARADA else None)
                        for (c, s), p in zip(SERIES.items(), pesos, strict=True))
    return Clausula(inicio, duracion, inicio, "mensual", mecanismo, estructura, componentes,
                    ENERO, D("0.10"), "memoria", "contrato ficticio", "Ing.",
                    mecanismo_pagadero=pagadero, fuente_pagadero="contrato" if pagadero else "")


def _r(m, e, o, factor=D(1)):
    cd = m + e + o
    return ResultadoAPU(m, e, o, cd, cd * factor, cd * factor)


DECLARADA = {"S1-R01": PartidaContrato("S1-R01", D(100), _r(D(100), D(0), D(0)), D(1000))}
POR_PARTIDA = {
    "A": PartidaContrato("A", D("97.50"), _r(D(45), D("7.50"), D("22.50"), D("1.30")), D(400)),
    "B": PartidaContrato("B", D("208.00"), _r(D(32), D(48), D(80), D("1.30")), D(120)),
}


def _periodo(ejecutado, desde=date(2027, 2, 1), hasta=date(2027, 2, 28), excepcion=""):
    return PeriodoDeclarado(desde, hasta, tuple(Ejecutado(c, D(q), "AV-01") for c, q in ejecutado),
                            "002", excepcion)


def _calcular(clausula, contrato, periodo, comprobado, *, indices=None, fecha=date(2027, 3, 5),
              moneda="Bs", monto=D(100000), en_bs=frozenset()):
    return calcular_estudio(clausula, contrato, [periodo], indices or _indices(), moneda=moneda,
                            tasas=[D(850)], pu_comprobados=[comprobado], monto_original=monto,
                            fecha_calculo=fecha, series_en_bs=en_bs)


def test_memoria_declarada():
    p = _calcular(_clausula(), DECLARADA, _periodo([("S1-R01", "1000")]), {"S1-R01": D(116)}).periodos[0]
    assert (p.km, p.escalatoria, p.comprobacion) == (D("1.17"), D("15300"), D("16000"))
    c = p.comparacion
    assert c.diferencia == D("-700")
    assert [x.quantize(C2) for x in (c.escalatoria_otra, c.comprobacion_otra, c.diferencia_otra)] == [
        D("18.00"), D("18.82"), D("-0.82")]


def test_memoria_por_partida():
    assert coeficiente_de_partida(POR_PARTIDA["A"].resultado, *_relativos()) == D("1.175")
    assert coeficiente_de_partida(POR_PARTIDA["B"].resultado, *_relativos()) == D("1.185")
    p = _calcular(_clausula(Estructura.POR_PARTIDA), POR_PARTIDA,
                  _periodo([("A", "400"), ("B", "120")]), {"A": D("115.00"), "B": D("247.00")},
                  monto=D("63960")).periodos[0]
    assert (p.escalatoria, p.comprobacion) == (D("10298.34"), D("11680.00"))
    assert p.comparacion.diferencia_otra.quantize(C2) == D("-1.63")  # una sola vez, no −1,62
    testigo = _calcular(_clausula(), {k: v for k, v in POR_PARTIDA.items()},
                        _periodo([("A", "400"), ("B", "120")]), None).periodos[0]
    assert testigo.escalatoria == D("9785.88")


def _relativos():
    return ({c: D(VALORES[s][0]) for c, s in SERIES.items()},
            {c: D(VALORES[s][1]) for c, s in SERIES.items()})


@pytest.mark.parametrize("pagadero, esperado", [(Mecanismo.COMPROBACION, D(16000)), (None, D(15300))])
def test_monto_reconocido_con_ambos(pagadero, esperado):
    p = _calcular(_clausula(pagadero=pagadero), DECLARADA, _periodo([("S1-R01", "1000")]),
                  {"S1-R01": D(116)}).periodos[0]
    assert p.reconocido == esperado


def test_comprobacion_no_disponible_con_pagadero_comprobacion_no_reconoce_nada():
    p = _calcular(_clausula(pagadero=Mecanismo.COMPROBACION), DECLARADA,
                  _periodo([("S1-R01", "1000")]), None).periodos[0]
    assert p.comprobacion is None and p.reconocido is None


def test_primer_anio_aniversario_y_doce_meses():
    cl = _clausula(inicio=date(2026, 3, 1))  # aniversario 01/03/2027
    antes = _calcular(cl, DECLARADA, _periodo([("S1-R01", "1")], date(2027, 2, 1), date(2027, 2, 28)),
                      {"S1-R01": D(116)}).periodos[0]
    assert antes.escalatoria == 0 and any("primer año" in m for m in antes.marcas)
    with pytest.raises(ValueError, match="3b"):
        _calcular(cl, DECLARADA, _periodo([("S1-R01", "1")], date(2027, 2, 15), date(2027, 3, 14)), None)
    doce = _calcular(_clausula(inicio=date(2026, 3, 1), duracion=12), DECLARADA,
                     _periodo([("S1-R01", "1")]), None).periodos[0]
    assert doce.escalatoria > 0
    excepcion = _calcular(cl, DECLARADA, _periodo([("S1-R01", "1")], excepcion="ruptura, acta 3"),
                          None).periodos[0]
    assert excepcion.escalatoria > 0 and any("excepción" in m for m in excepcion.marcas)


def test_pesos_que_no_suman_uno_indice_faltante_y_provisional():
    with pytest.raises(ValueError, match="0.9999"):
        _clausula(pesos=("0.5", "0.2", "0.2999"))
    falta = _calcular(_clausula(), DECLARADA, _periodo([("S1-R01", "1")]), None,
                      indices=_indices(sin=("FIC-MO",))).periodos[0]
    assert falta.escalatoria is None and any("faltante" in m for m in falta.marcas)
    prov = _calcular(_clausula(), DECLARADA, _periodo([("S1-R01", "1")]), None,
                     indices=_indices(provisional=True)).periodos[0]
    assert "provisional" in prov.marcas


def test_exceso_se_reajusta_hasta_q_con_aviso():
    exacto = _calcular(_clausula(), DECLARADA, _periodo([("S1-R01", "1000")]), None).periodos[0]
    assert not exacto.excesos
    exceso = _calcular(_clausula(), DECLARADA, _periodo([("S1-R01", "1000.001")]), None).periodos[0]
    assert exceso.excesos == ("S1-R01",) and exceso.escalatoria == D("15300")


def test_avisos_usd_con_indice_bs_nota_10_y_parcial_al_corte():
    r = _calcular(_clausula(), DECLARADA, _periodo([("S1-R01", "1000")]), None, moneda="USD",
                  en_bs=frozenset(SERIES.values()), fecha=date(2027, 2, 27))
    assert any("S1-R11" in a for a in r.avisos) and any("INDICIO" in a for a in r.avisos)
    assert r.estado is EstadoEstudio.PARCIAL
    assert _calcular(_clausula(), DECLARADA, _periodo([("S1-R01", "1")]), None,
                     fecha=date(2027, 2, 28)).estado is EstadoEstudio.CERRADO
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_reajuste.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.budget.reajuste'`
- [ ] **Paso 3: Implementación mínima**
```python
# core/budget/reajuste.py (parte pura; la Tarea 12 agrega guardar_estudio y cargar_estudio)
"""SL‑E3: reajuste por fórmula escalatoria y por comprobación directa (UC‑18; S1 §8). Supuestos
declarados, todo «a cotejar con la Gaceta»: Vpm = Vo·(Km−1)·(1−R) es INDICIO (S1‑R8); índice del mes
de cierre (S1‑R10); primer año solo en contratos > 12 meses (S1‑R9); R no se aplica a la
comprobación salvo declaración (S1‑R14); reconocido por `mecanismo_pagadero` (S1‑R20); mes en curso
«parcial al corte» (S1‑R21). Funciones puras, 28 dígitos y ROUND_HALF_EVEN."""
from __future__ import annotations

import calendar
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import StrEnum

from core.catalog.indices import ValorFechado
from core.catalog.moneda import convertir
from core.contracts.apu import ResultadoAPU

COMPONENTES = ("materiales", "equipos", "mano_obra")
CERO = Decimal(0)
MARCA_PRIMER_ANIO = "precios fijos el primer año (art. 134, a cotejar)"
MARCA_EXCEPCION = "excepción declarada"
MARCA_PROVISIONAL = "provisional"
MARCA_INDICE_FALTANTE = "índice faltante: período no calculado"
MARCA_SIN_COMPROBACION = "comprobación no disponible"
MARCA_SIN_RECONOCIDO = "sin monto reconocido: el mecanismo reconocido no está disponible"
AVISO_USD_BS = ("ADVERTENCIA: proyecto en USD con un índice en bolívares: cuenta dos veces la "
                "devaluación (S1-R11)")
NOTA_COMISION = ("INDICIO: los reajustes superan el 10 % del monto original; la Comisión de "
                 "Contrataciones opina sobre esas variaciones (artículo sin confirmar)")
NOTA_RECONSIDERACION = ("la escalatoria en reconsideraciones solo vale para obras y servicios "
                        "(art. 134, transcripción, a cotejar)")


class Mecanismo(StrEnum):
    ESCALATORIA = "escalatoria"
    COMPROBACION = "comprobacion"
    AMBOS = "ambos"


class Estructura(StrEnum):
    POR_PARTIDA = "por_partida"
    DECLARADA = "declarada"


class EstadoEstudio(StrEnum):
    CERRADO = "cerrado"
    PARCIAL = "parcial al corte"


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class Componente:
    componente: str
    serie: str
    peso: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Clausula:
    fecha_inicio: date
    duracion_meses: int
    fecha_referencia_primer_anio: date
    periodicidad: str
    mecanismo: Mecanismo
    estructura: Estructura
    componentes: tuple[Componente, ...]
    fecha_base_indices: date
    r: Decimal
    fuente_r: str
    fuente: str
    responsable: str
    mecanismo_pagadero: Mecanismo | None = None
    fuente_pagadero: str = ""
    r_en_comprobacion: bool = False

    def __post_init__(self) -> None:
        if self.duracion_meses <= 0:
            raise ValueError("la duracion del contrato debe ser positiva")
        if self.fecha_base_indices.day != 1:
            raise ValueError("el mes base de los indices se declara con su primer dia (S1-R10)")
        if not (CERO <= self.r < 1) or not self.fuente_r.strip():
            raise ValueError("R va en [0, 1) con su fuente (S1-R8)")
        if not self.fuente.strip() or not self.responsable.strip():
            raise ValueError("la clausula exige fuente y responsable")
        if self.mecanismo_pagadero is not None and (
                self.mecanismo is not Mecanismo.AMBOS
                or self.mecanismo_pagadero is Mecanismo.AMBOS or not self.fuente_pagadero.strip()):
            raise ValueError("mecanismo_pagadero solo con 'ambos', uno de los dos y con su fuente")
        nombres = [c.componente for c in self.componentes]
        if len(set(nombres)) != len(nombres):
            raise ValueError("componente repetido en la clausula")
        if self.estructura is Estructura.POR_PARTIDA:
            if sorted(nombres) != sorted(COMPONENTES):
                raise ValueError("por_partida exige materiales, equipos y mano_obra con su serie")
        else:
            if any(c.peso is None for c in self.componentes):
                raise ValueError("la estructura declarada exige el peso de cada componente")
            suma = sum((c.peso for c in self.componentes), CERO)
            if suma != 1:
                raise ValueError(f"los pesos de la estructura declarada suman {suma}, no 1 (§8.1)")


@dataclass(frozen=True, slots=True)
class PartidaContrato:
    codigo: str
    pu: Decimal
    resultado: ResultadoAPU
    presupuestado: Decimal


@dataclass(frozen=True, slots=True)
class Ejecutado:
    codigo: str
    cantidad: Decimal
    fuente: str


@dataclass(frozen=True, slots=True)
class PeriodoDeclarado:
    desde: date
    hasta: date
    ejecutado: tuple[Ejecutado, ...]
    version_comprobacion: str = ""
    excepcion: str = ""


@dataclass(frozen=True, slots=True)
class Comparacion:
    moneda: str
    otra: str
    tasa: Decimal | None
    escalatoria: Decimal | None
    comprobacion: Decimal | None
    diferencia: Decimal | None
    escalatoria_otra: Decimal | None
    comprobacion_otra: Decimal | None
    diferencia_otra: Decimal | None


@dataclass(frozen=True, slots=True)
class ResultadoPeriodo:
    desde: date
    hasta: date
    reajustables: Mapping[str, Decimal]
    excesos: tuple[str, ...]
    km: Decimal | None
    coeficientes: Mapping[str, Decimal]
    escalatoria: Decimal | None
    comprobacion: Decimal | None
    reconocido: Decimal | None
    mecanismo_reconocido: str
    importaciones: Mapping[str, int]
    marcas: tuple[str, ...]
    comparacion: Comparacion
    version_comprobacion: str


@dataclass(frozen=True, slots=True)
class ResultadoEstudio:
    moneda: str
    periodos: tuple[ResultadoPeriodo, ...]
    total_escalatoria: Decimal
    total_comprobacion: Decimal
    total_reconocido: Decimal
    estado: EstadoEstudio
    fecha_corte: date | None
    avisos: tuple[str, ...]


def coeficiente(pesos, base, periodo) -> Decimal:
    with _contexto():
        return sum((pesos[c] * periodo[c] / base[c] for c in pesos), CERO)


def coeficiente_de_partida(resultado: ResultadoAPU, base, periodo) -> Decimal:
    montos = dict(zip(COMPONENTES, (resultado.materiales, resultado.equipos, resultado.mano_obra),
                      strict=True))
    with _contexto():
        return sum((montos[c] * periodo[c] / base[c] for c in COMPONENTES), CERO) / resultado.costo_directo


def reajuste_escalatorio(clausula, contrato, reajustables, base, periodo) -> Decimal:
    with _contexto():
        if clausula.estructura is Estructura.DECLARADA:
            pesos = {c.componente: c.peso for c in clausula.componentes}
            vo = sum((q * contrato[c].pu for c, q in reajustables.items()), CERO)
            return vo * (coeficiente(pesos, base, periodo) - 1) * (1 - clausula.r)
        return sum((q * contrato[c].pu * (coeficiente_de_partida(contrato[c].resultado, base, periodo) - 1)
                    * (1 - clausula.r) for c, q in reajustables.items()), CERO)


def reajuste_por_comprobacion(reajustables, pu_contrato, pu_comprobado, r=CERO) -> Decimal:
    with _contexto():
        return sum((q * (pu_comprobado[c] - pu_contrato[c]) for c, q in reajustables.items()),
                   CERO) * (1 - r)


def comparar_reajustes(escalatoria, comprobacion, *, moneda, tasa) -> Comparacion:
    otra = "USD" if moneda == "Bs" else "Bs"
    diferencia = None if escalatoria is None or comprobacion is None else escalatoria - comprobacion

    def a_otra(x):
        return None if x is None or tasa is None else convertir(x, moneda, otra, tasa)

    return Comparacion(moneda, otra, tasa, escalatoria, comprobacion, diferencia,
                       a_otra(escalatoria), a_otra(comprobacion), a_otra(diferencia))


def _aniversario(d: date) -> date:
    try:
        return d.replace(year=d.year + 1)
    except ValueError:  # 29 de febrero
        return date(d.year + 1, 3, 1)


def _reajustables(contrato, periodos):
    acumulado = dict.fromkeys(contrato, CERO)
    for periodo in periodos:
        cantidades, excesos = {}, []
        for e in periodo.ejecutado:
            if e.codigo not in contrato:
                raise ValueError(f"la partida {e.codigo} no esta en la version del contrato")
            disponible = max(CERO, contrato[e.codigo].presupuestado - acumulado[e.codigo])
            if e.cantidad > disponible:
                excesos.append(e.codigo)
            cantidades[e.codigo] = cantidades.get(e.codigo, CERO) + min(e.cantidad, disponible)
            acumulado[e.codigo] += e.cantidad
        yield cantidades, tuple(excesos)


def calcular_estudio(clausula, contrato, periodos, indices, *, moneda, tasas, pu_comprobados,
                     monto_original, fecha_calculo, series_en_bs=frozenset()) -> ResultadoEstudio:
    periodos = list(periodos)
    if any(p.desde > p.hasta for p in periodos) or any(
            a.hasta >= b.desde for a, b in zip(periodos, periodos[1:])):
        raise ValueError("los periodos van en orden y sin solaparse")
    aniversario = _aniversario(clausula.fecha_referencia_primer_anio)
    resultados = []
    for periodo, (cantidades, excesos), tasa, comprobado in zip(
            periodos, _reajustables(contrato, periodos), tasas, pu_comprobados, strict=True):
        marcas: list[str] = []
        if excesos:
            marcas.append("ejecutado mayor que lo presupuestado: se reajusta hasta lo presupuestado")
        congelado = False
        if clausula.duracion_meses > 12:
            if periodo.desde < aniversario <= periodo.hasta:
                raise ValueError(f"el periodo {periodo.desde}–{periodo.hasta} cruza el aniversario "
                                 f"{aniversario}: partalo (UC-18 3b)")
            if periodo.hasta < aniversario:
                congelado = not periodo.excepcion.strip()
                marcas.append(MARCA_EXCEPCION if not congelado else MARCA_PRIMER_ANIO)
        mes = date(periodo.hasta.year, periodo.hasta.month, 1)
        base, actual, citas, provisional, km, coefs = {}, {}, {}, False, None, {}
        for comp in clausula.componentes:
            i0, im = indices.get((comp.serie, clausula.fecha_base_indices)), indices.get((comp.serie, mes))
            if i0 is None or im is None:
                base = None
                break
            base[comp.componente], actual[comp.componente] = i0.valor, im.valor
            citas[f"{comp.serie}@{i0.fecha.isoformat()}"] = i0.importacion_id
            citas[f"{comp.serie}@{im.fecha.isoformat()}"] = im.importacion_id
            provisional = provisional or i0.provisional or im.provisional
        if congelado:
            escalatoria = CERO
        elif base is None:
            escalatoria = None
            marcas.append(MARCA_INDICE_FALTANTE)
        else:
            escalatoria = reajuste_escalatorio(clausula, contrato, cantidades, base, actual)
            if clausula.estructura is Estructura.DECLARADA:
                km = coeficiente({c.componente: c.peso for c in clausula.componentes}, base, actual)
            else:
                coefs = {c: coeficiente_de_partida(contrato[c].resultado, base, actual) for c in cantidades}
        if provisional:
            marcas.append(MARCA_PROVISIONAL)
        if congelado:
            comprobacion = CERO
        elif comprobado is None:
            comprobacion = None
            marcas.append(MARCA_SIN_COMPROBACION)
        else:
            comprobacion = reajuste_por_comprobacion(
                cantidades, {c: p.pu for c, p in contrato.items()}, comprobado,
                clausula.r if clausula.r_en_comprobacion else CERO)
        elegido = (clausula.mecanismo if clausula.mecanismo is not Mecanismo.AMBOS
                   else clausula.mecanismo_pagadero or Mecanismo.ESCALATORIA)
        reconocido = escalatoria if elegido is Mecanismo.ESCALATORIA else comprobacion
        if reconocido is None:
            marcas.append(MARCA_SIN_RECONOCIDO)
        resultados.append(ResultadoPeriodo(
            periodo.desde, periodo.hasta, cantidades, excesos, km, coefs, escalatoria,
            comprobacion, reconocido, elegido.value, citas, tuple(marcas),
            comparar_reajustes(escalatoria, comprobacion, moneda=moneda, tasa=tasa),
            periodo.version_comprobacion))
    total = lambda campo: sum((getattr(r, campo) for r in resultados  # noqa: E731
                               if getattr(r, campo) is not None), CERO)
    avisos = [NOTA_RECONSIDERACION]
    if moneda == "USD" and any(c.serie in series_en_bs for c in clausula.componentes):
        avisos.append(AVISO_USD_BS)
    if monto_original and total("reconocido") / monto_original > Decimal("0.10"):
        avisos.append(NOTA_COMISION)
    ultimo = periodos[-1].hasta
    fin = date(ultimo.year, ultimo.month, calendar.monthrange(ultimo.year, ultimo.month)[1])
    estado = EstadoEstudio.PARCIAL if fecha_calculo < fin else EstadoEstudio.CERRADO
    return ResultadoEstudio(moneda, tuple(resultados), total("escalatoria"), total("comprobacion"),
                            total("reconocido"), estado,
                            fecha_calculo if estado is EstadoEstudio.PARCIAL else None, tuple(avisos))
```
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/unit/test_reajuste.py -q -W error`; ruff.
- [ ] **Paso 5: Commit**
```bash
git add tests/unit/test_reajuste.py
git commit -m "test(core): SL-E3 reajuste contra las dos memorias y sus fronteras en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add core/budget/reajuste.py core/budget/__init__.py
git commit -m "feat(core): SL-E3 escalatoria y comprobacion directa lado a lado" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Tarea 12: SL‑E3b — tablas, revisión `caso_0004`, estudio guardado y RNF‑14

**Rama:** `inc/060-s1-4-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `migraciones/caso/versions/caso_0004_s1_reajuste.py`, `tests/integration/test_estudio_reajuste.py`, `tests/fixtures/reajuste_s1.py`
- Modificar: `core/models/moneda.py` (cinco tablas), `core/models/__init__.py`, `core/budget/reajuste.py` (persistencia), `core/budget/__init__.py` (exportar)

**Interfaces:**
- Produce: `models.ClausulaReajuste`, `models.ComponenteClausula`, `models.EstudioReajuste` (con `UniqueConstraint("reemplaza_a", name="uq_estudio_reemplaza_a")`), `models.PeriodoReajuste`, `models.EjecutadoPeriodo` (columnas de S1 §8.5: `periodo_reajuste` con `km`, `escalatoria`, `comprobacion`, `reconocido`, `mecanismo_reconocido`, `version_comprobacion_id`, `tasa`, `fecha_tasa`, `importaciones` JSON‑texto, `marcas` JSON‑texto, `excepcion`); `contrato_de_version(version) -> dict[str, PartidaContrato]`; `guardar_estudio(session, version, clausula, periodos, *, fecha_calculo, fuente, responsable, reemplaza_a=None, lado=LADO_POR_DEFECTO, ahora=None) -> models.EstudioReajuste`; `cargar_estudio(session, estudio_id) -> EstudioCargado(id, version_id, estado, reemplaza_a, clausula, periodos, resultado)`.

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/fixtures/reajuste_s1.py
"""Contrato de s1_reajuste.md en una base: versión 001 en Bs (PU 100) y la 002 revalorada (116)."""
from datetime import date
from decimal import Decimal as D

from core import models
from core.budget import actualizar_precios, crear_proyecto, elaborar, guardar_presupuesto
from core.budget.reajuste import (
    Clausula, Componente, Ejecutado, Estructura, Mecanismo, PeriodoDeclarado)
from core.catalog import Catalogo
from core.catalog.indices import DefinicionSerie, Observacion, definicion_tasa, registrar_importacion
from core.contracts import ComposicionAPU, Dominio, ItemComputo, LineaMaterial, ParametrosCosto
from core.contracts.item_computo import OrigenTipo

CERO = ParametrosCosto(D(0), D(0), D(0), D(0))
NOMBRE = "Contrato S1 (reajuste)"
INDICES = {"FIC-MAT": ("200", "230"), "FIC-EQU": ("150", "165"), "FIC-MO": ("80", "100")}
#: La cláusula y el período de `s1_reajuste.md` (los usan la prueba del estudio y la base 0.6.0).
PESOS = {"materiales": ("FIC-MAT", "0.5"), "equipos": ("FIC-EQU", "0.2"), "mano_obra": ("FIC-MO", "0.3")}
CLAUSULA = Clausula(date(2026, 1, 15), 24, date(2026, 1, 15), "mensual", Mecanismo.AMBOS,
                    Estructura.DECLARADA,
                    tuple(Componente(c, s, D(p)) for c, (s, p) in PESOS.items()),
                    date(2026, 1, 1), D("0.10"), "memoria", "contrato ficticio", "Ing.")
PERIODO = PeriodoDeclarado(date(2027, 2, 1), date(2027, 2, 28),
                           (Ejecutado("S1-R01", D(1000), "AV-01 del 28/02/2027"),), "002")


def _importar(sesion, codigo, valores, huella):
    registrar_importacion(sesion, DefinicionSerie(codigo, codigo, "ficticio", "indice_bs", "mensual"),
                          [Observacion(f, D(v)) for f, v in valores], archivo="memoria",
                          huella=huella, fuente="tests/fixtures/memorias/s1_reajuste.md",
                          fecha_descarga=date(2027, 3, 1), responsable="A",
                          filas_leidas=len(valores), filas_rechazadas=0)


def sembrar(sesion):
    lista = models.ListaPrecios(nombre="Contrato S1 Bs", moneda="Bs", fecha_vigencia=date(2026, 1, 15))
    sesion.add(lista)
    sesion.flush()
    apu = ComposicionAPU("S1-R01", "Partida ficticia del reajuste", "m3", D(1),
                         (LineaMaterial("Insumo ficticio del reajuste", "m3", D(1), D(100)),))
    Catalogo(sesion).cargar_composicion(apu, lista, Dominio.CIVIL, date(2026, 1, 15), "memoria S1")
    item = ItemComputo("S1-R01", "Partida ficticia", "m3", D(1000), "memoria-s1", OrigenTipo.MANUAL,
                       Dominio.CIVIL)
    hecho = elaborar([item], {"S1-R01": apu}, CERO, codigo="001", fecha=date(2026, 1, 15), moneda="Bs")
    proyecto = crear_proyecto(sesion, NOMBRE)
    guardar_presupuesto(sesion, hecho.presupuesto, hecho.informe, proyecto=proyecto, lista=lista,
                        parametros=CERO)
    nueva = models.ListaPrecios(nombre="Revalorada 2027-02", moneda="Bs", fecha_vigencia=date(2027, 2, 1))
    sesion.add(nueva)
    sesion.flush()
    insumo = sesion.query(models.Insumo).filter_by(descripcion="Insumo ficticio del reajuste").one()
    sesion.add(models.PrecioInsumo(lista_id=nueva.id, insumo_id=insumo.id, precio=D(116)))
    sesion.flush()
    actualizar_precios(sesion, NOMBRE, "001", nueva, "002")
    for n, (codigo, (i0, im)) in enumerate(INDICES.items()):
        _importar(sesion, codigo, [(date(2026, 1, 1), i0), (date(2027, 2, 1), im)], f"{n}" * 64)
    registrar_importacion(sesion, definicion_tasa("venta"), [Observacion(date(2027, 2, 26), D(850))],
                          archivo="memoria", huella="9" * 64, fuente="https://www.bcv.org.ve/",
                          fecha_descarga=date(2027, 3, 1), responsable="A", filas_leidas=1,
                          filas_rechazadas=0)  # tasa FICTICIA de la memoria
    sesion.flush()
```
```python
# tests/integration/test_estudio_reajuste.py
from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from core import models
from core.budget.reajuste import EstadoEstudio, cargar_estudio, guardar_estudio
from tests.fixtures.reajuste_s1 import CLAUSULA, NOMBRE, PERIODO, _importar, sembrar


def _version(sesion, codigo="001"):
    return sesion.scalars(select(models.Presupuesto).join(models.Proyecto).where(
        models.Proyecto.nombre == NOMBRE, models.Presupuesto.codigo == codigo)).one()


def _guardar(sesion, fecha=date(2027, 3, 5), reemplaza_a=None):
    return guardar_estudio(sesion, _version(sesion), CLAUSULA, [PERIODO], fecha_calculo=fecha,
                           fuente="estudio de prueba", responsable="Ing.", reemplaza_a=reemplaza_a)


def test_recargado_es_identico_y_cita_lo_que_uso(sesion):
    sembrar(sesion)
    estudio = _guardar(sesion)
    cargado = cargar_estudio(sesion, estudio.id)
    p = cargado.resultado.periodos[0]
    assert (p.escalatoria, p.comprobacion, p.reconocido) == (D(15300), D(16000), D(15300))
    assert cargado.estado is EstadoEstudio.CERRADO and p.version_comprobacion == "002"


def test_rnf14_una_revision_posterior_no_cambia_el_estudio(sesion):
    sembrar(sesion)
    estudio = _guardar(sesion)
    _importar(sesion, "FIC-MAT", [(date(2027, 2, 1), "240")], "f" * 64)  # revisión del índice
    assert cargar_estudio(sesion, estudio.id).resultado.periodos[0].escalatoria - D(15300) == 0


def test_parcial_se_reemplaza_una_sola_vez_sin_borrarse(sesion):
    sembrar(sesion)
    parcial = _guardar(sesion, fecha=date(2027, 2, 27))
    assert parcial.estado == EstadoEstudio.PARCIAL.value
    cierre = _guardar(sesion, reemplaza_a=parcial.id)
    assert sesion.get(models.EstudioReajuste, parcial.id) is not None and cierre.reemplaza_a == parcial.id
    with pytest.raises(ValueError, match="una sola vez"):
        _guardar(sesion, reemplaza_a=parcial.id)


def test_sin_fuente_o_responsable_no_se_guarda(sesion):
    sembrar(sesion)
    with pytest.raises(ValueError):
        guardar_estudio(sesion, _version(sesion), CLAUSULA, [PERIODO], fecha_calculo=date(2027, 3, 5),
                        fuente=" ", responsable="Ing.")
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/integration/test_estudio_reajuste.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'guardar_estudio' from 'core.budget.reajuste'`
- [ ] **Paso 3: Implementación mínima**
```python
# core/models/moneda.py — al final (SL‑E3, S1 §8.1 y §8.5)
class ClausulaReajuste(Base):
    """SL‑E3: la cláusula de reajuste de un contrato (S1 §8.1), tal como se declaró al guardar un
    estudio. Inmutable: rehacerla es guardar otro estudio con otra cláusula."""

    __tablename__ = "clausula_reajuste"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id", ondelete="CASCADE"))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    duracion_meses: Mapped[int] = mapped_column(Integer)
    fecha_referencia_primer_anio: Mapped[date] = mapped_column(Date)
    periodicidad: Mapped[str] = mapped_column(String(20))
    mecanismo: Mapped[str] = mapped_column(String(20))
    mecanismo_pagadero: Mapped[str | None] = mapped_column(String(20), default=None)
    fuente_pagadero: Mapped[str] = mapped_column(String(300), default="")
    estructura: Mapped[str] = mapped_column(String(20))
    fecha_base_indices: Mapped[date] = mapped_column(Date)
    r: Mapped[Decimal] = mapped_column(DecimalExacto)
    fuente_r: Mapped[str] = mapped_column(String(300))
    r_en_comprobacion: Mapped[bool] = mapped_column(Boolean, default=False)
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))


class ComponenteClausula(Base):
    """SL‑E3: un componente de la cláusula con su serie y, con estructura declarada, su peso."""

    __tablename__ = "componente_clausula"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clausula_id: Mapped[int] = mapped_column(
        ForeignKey("clausula_reajuste.id", ondelete="CASCADE")
    )
    orden: Mapped[int] = mapped_column(Integer)
    componente: Mapped[str] = mapped_column(String(20))
    serie_id: Mapped[int] = mapped_column(ForeignKey("serie_indice.id"))
    peso: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)


class EstudioReajuste(Base):
    """SL‑E3: un estudio guardado (S1 §8.5). Solo‑agregar: un parcial al corte se reemplaza una
    sola vez por otro estudio que lo cita en `reemplaza_a` (S1‑R21)."""

    __tablename__ = "estudio_reajuste"
    __table_args__ = (UniqueConstraint("reemplaza_a", name="uq_estudio_reemplaza_a"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id", ondelete="CASCADE"))
    clausula_id: Mapped[int] = mapped_column(
        ForeignKey("clausula_reajuste.id", ondelete="CASCADE")
    )
    fecha_calculo: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20))
    fecha_corte: Mapped[date | None] = mapped_column(Date, default=None)
    reemplaza_a: Mapped[int | None] = mapped_column(
        ForeignKey("estudio_reajuste.id"), default=None
    )
    moneda: Mapped[str] = mapped_column(String(10))
    lado: Mapped[str] = mapped_column(String(10))
    monto_original: Mapped[Decimal] = mapped_column(DecimalExacto)
    total_escalatoria: Mapped[Decimal] = mapped_column(DecimalExacto)
    total_comprobacion: Mapped[Decimal] = mapped_column(DecimalExacto)
    total_reconocido: Mapped[Decimal] = mapped_column(DecimalExacto)
    avisos: Mapped[str] = mapped_column(Text, default="[]")
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


class PeriodoReajuste(Base):
    """SL‑E3: un período del estudio con sus resultados, la versión revalorada que usó, la tasa de
    su cierre y la importación de cada índice (`importaciones`: JSON `{"serie@AAAA-MM-DD": id}`)."""

    __tablename__ = "periodo_reajuste"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estudio_id: Mapped[int] = mapped_column(ForeignKey("estudio_reajuste.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(Integer)
    desde: Mapped[date] = mapped_column(Date)
    hasta: Mapped[date] = mapped_column(Date)
    km: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    escalatoria: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    comprobacion: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    reconocido: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    mecanismo_reconocido: Mapped[str] = mapped_column(String(20))
    version_comprobacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="SET NULL"), default=None
    )
    tasa: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    fecha_tasa: Mapped[date | None] = mapped_column(Date, default=None)
    importaciones: Mapped[str] = mapped_column(Text, default="{}")
    marcas: Mapped[str] = mapped_column(Text, default="[]")
    excepcion: Mapped[str] = mapped_column(String(300), default="")


class EjecutadoPeriodo(Base):
    """SL‑E3: lo ejecutado de una partida en un período, con su fuente (acta o valuación; S1 §8.6:
    escrito a mano en la 0.6.0; S2 agrega la cita a la valuación con su propia revisión)."""

    __tablename__ = "ejecutado_periodo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo_reajuste.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(Integer)
    codigo_partida: Mapped[str] = mapped_column(String(40))
    cantidad: Mapped[Decimal] = mapped_column(DecimalExacto)
    fuente: Mapped[str] = mapped_column(String(300))
```
  En `core/models/__init__.py`: `ClausulaReajuste`, `ComponenteClausula`, `EjecutadoPeriodo`, `EstudioReajuste` y `PeriodoReajuste` en la importación de `core.models.moneda` y en `__all__` (orden alfabético).
```python
# migraciones/caso/versions/caso_0004_s1_reajuste.py
"""S1‑4 (SL‑E3): cláusula, componentes, estudio, períodos y ejecutado del reajuste."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0004_s1_reajuste"
down_revision = "caso_0003_s1_lista_empresa"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def upgrade() -> None:
    op.create_table(
        "clausula_reajuste",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("presupuesto_id", sa.Integer,
                  sa.ForeignKey("presupuesto.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha_inicio", sa.Date, nullable=False),
        sa.Column("duracion_meses", sa.Integer, nullable=False),
        sa.Column("fecha_referencia_primer_anio", sa.Date, nullable=False),
        sa.Column("periodicidad", sa.String(20), nullable=False),
        sa.Column("mecanismo", sa.String(20), nullable=False),
        sa.Column("mecanismo_pagadero", sa.String(20), nullable=True),
        sa.Column("fuente_pagadero", sa.String(300), nullable=False),
        sa.Column("estructura", sa.String(20), nullable=False),
        sa.Column("fecha_base_indices", sa.Date, nullable=False),
        sa.Column("r", DEC, nullable=False),
        sa.Column("fuente_r", sa.String(300), nullable=False),
        sa.Column("r_en_comprobacion", sa.Boolean, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
    )
    op.create_table(
        "componente_clausula",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("clausula_id", sa.Integer,
                  sa.ForeignKey("clausula_reajuste.id", ondelete="CASCADE"), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False),
        sa.Column("componente", sa.String(20), nullable=False),
        sa.Column("serie_id", sa.Integer, sa.ForeignKey("serie_indice.id"), nullable=False),
        sa.Column("peso", DEC, nullable=True),
    )
    op.create_table(
        "estudio_reajuste",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("presupuesto_id", sa.Integer,
                  sa.ForeignKey("presupuesto.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clausula_id", sa.Integer,
                  sa.ForeignKey("clausula_reajuste.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha_calculo", sa.Date, nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("fecha_corte", sa.Date, nullable=True),
        sa.Column("reemplaza_a", sa.Integer, sa.ForeignKey("estudio_reajuste.id"), nullable=True),
        sa.Column("moneda", sa.String(10), nullable=False),
        sa.Column("lado", sa.String(10), nullable=False),
        sa.Column("monto_original", DEC, nullable=False),
        sa.Column("total_escalatoria", DEC, nullable=False),
        sa.Column("total_comprobacion", DEC, nullable=False),
        sa.Column("total_reconocido", DEC, nullable=False),
        sa.Column("avisos", sa.Text, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
        sa.UniqueConstraint("reemplaza_a", name="uq_estudio_reemplaza_a"),
    )
    op.create_table(
        "periodo_reajuste",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("estudio_id", sa.Integer,
                  sa.ForeignKey("estudio_reajuste.id", ondelete="CASCADE"), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=False),
        sa.Column("km", DEC, nullable=True),
        sa.Column("escalatoria", DEC, nullable=True),
        sa.Column("comprobacion", DEC, nullable=True),
        sa.Column("reconocido", DEC, nullable=True),
        sa.Column("mecanismo_reconocido", sa.String(20), nullable=False),
        sa.Column("version_comprobacion_id", sa.Integer,
                  sa.ForeignKey("presupuesto.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tasa", DEC, nullable=True),
        sa.Column("fecha_tasa", sa.Date, nullable=True),
        sa.Column("importaciones", sa.Text, nullable=False),
        sa.Column("marcas", sa.Text, nullable=False),
        sa.Column("excepcion", sa.String(300), nullable=False),
    )
    op.create_table(
        "ejecutado_periodo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("periodo_id", sa.Integer,
                  sa.ForeignKey("periodo_reajuste.id", ondelete="CASCADE"), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False),
        sa.Column("codigo_partida", sa.String(40), nullable=False),
        sa.Column("cantidad", DEC, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
    )


def downgrade() -> None:
    for tabla in ("ejecutado_periodo", "periodo_reajuste", "estudio_reajuste",
                  "componente_clausula", "clausula_reajuste"):
        op.drop_table(tabla)
```
```python
# core/budget/reajuste.py — persistencia (SL‑E3b), al final del módulo. Importar además:
# `import json`, `from datetime import date, datetime`, `from sqlalchemy import select`,
# `from sqlalchemy.orm import Session`, `from core import models` y, en la importación de
# `core.catalog.indices`, `LADO_POR_DEFECTO, UNIDAD_INDICE_BS, TasaNoDisponible, tasa_aplicable,
# valor_en`. Exportar `contrato_de_version`, `guardar_estudio`, `cargar_estudio` y `EstudioCargado`
# en `core/budget/__init__.py`, como las funciones puras de la Tarea 11.


@dataclass(frozen=True, slots=True)
class EstudioCargado:
    """Un estudio recargado: sus entradas reconstruidas y su resultado recalculado, que es igual al
    guardado (si no, `cargar_estudio` no lo devuelve)."""

    id: int
    version_id: int
    estado: EstadoEstudio
    reemplaza_a: int | None
    clausula: Clausula
    periodos: tuple[PeriodoDeclarado, ...]
    resultado: ResultadoEstudio


def contrato_de_version(version: models.Presupuesto) -> dict[str, PartidaContrato]:
    contrato: dict[str, PartidaContrato] = {}
    for r in version.partidas:
        codigo = r.partida.codigo
        resultado = ResultadoAPU(r.materiales, r.equipos, r.mano_obra, r.costo_directo,
                                 r.con_administracion, r.precio_unitario)
        previo = contrato.get(codigo)
        contrato[codigo] = PartidaContrato(codigo, r.precio_unitario, resultado,
                                           r.cantidad + (previo.presupuestado if previo else CERO))
    return contrato


def _series(session: Session, clausula: Clausula) -> dict[str, models.SerieIndice]:
    codigos = [c.serie for c in clausula.componentes]
    series = {s.codigo: s for s in session.scalars(
        select(models.SerieIndice).where(models.SerieIndice.codigo.in_(codigos)))}
    faltan = [codigo for codigo in codigos if codigo not in series]
    if faltan:
        raise ValueError(f"las series {', '.join(faltan)} no estan importadas (UC-17)")
    return series


def _mes_de_cierre(periodo: PeriodoDeclarado) -> date:
    return date(periodo.hasta.year, periodo.hasta.month, 1)


def _indices_vigentes(session: Session, clausula: Clausula,
                      periodos: Sequence[PeriodoDeclarado]) -> dict[tuple[str, date], ValorFechado]:
    """El valor de cada serie en el mes base y en el mes de cierre de cada período, de la
    importación vigente al calcular (S1‑R10). Lo que no está queda fuera: el período se declara
    sin calcular."""
    fechas = {clausula.fecha_base_indices, *(_mes_de_cierre(p) for p in periodos)}
    indices: dict[tuple[str, date], ValorFechado] = {}
    for componente in clausula.componentes:
        for fecha in fechas:
            valor = valor_en(session, componente.serie, fecha)
            if valor is not None:
                indices[(componente.serie, fecha)] = valor
    return indices


def _version_de_comprobacion(session: Session, version: models.Presupuesto,
                             codigo: str) -> models.Presupuesto | None:
    if not codigo.strip():
        return None
    otra = session.scalars(select(models.Presupuesto).where(
        models.Presupuesto.proyecto_id == version.proyecto_id,
        models.Presupuesto.codigo == codigo.strip())).one_or_none()
    if otra is None:
        raise ValueError(
            f"la version de comprobacion {codigo!r} no existe en el proyecto (UC-18 4)"
        )
    return otra


def _pu_de(version: models.Presupuesto | None,
           periodo: PeriodoDeclarado) -> dict[str, Decimal] | None:
    """El PU de cada partida ejecutada en la versión revalorada (comprobación directa, S1 §8.4)."""
    if version is None:
        return None
    pu = {r.partida.codigo: r.precio_unitario for r in version.partidas}
    faltan = sorted({e.codigo for e in periodo.ejecutado} - set(pu))
    if faltan:
        raise ValueError(f"la version {version.codigo} no valora {', '.join(faltan)}: no sirve de "
                         "comprobacion para ese periodo")
    return pu


def _tasa_o_nada(session: Session, fecha: date, lado: str) -> ValorFechado | None:
    try:
        return tasa_aplicable(session, fecha, lado=lado)
    except TasaNoDisponible:
        return None  # la otra moneda queda «no disponible» (S1 §8.4)


def _exigir_reemplazo(session: Session, version: models.Presupuesto, reemplaza_a: int,
                      resultado: ResultadoEstudio) -> None:
    parcial = session.get(models.EstudioReajuste, reemplaza_a)
    if parcial is None or parcial.presupuesto_id != version.id:
        raise ValueError(f"el estudio {reemplaza_a} no es de la version {version.codigo}")
    if parcial.estado != EstadoEstudio.PARCIAL:
        raise ValueError(f"el estudio {reemplaza_a} esta cerrado: solo un parcial se reemplaza")
    if session.scalar(select(models.EstudioReajuste.id).where(
            models.EstudioReajuste.reemplaza_a == reemplaza_a)) is not None:
        raise ValueError("un parcial se reemplaza una sola vez (S1-R21)")
    if resultado.estado is not EstadoEstudio.CERRADO:
        raise ValueError("el estudio que reemplaza a un parcial debe estar cerrado (S1-R21)")


def _guardar_clausula(session: Session, version: models.Presupuesto, clausula: Clausula,
                      series: Mapping[str, models.SerieIndice]) -> models.ClausulaReajuste:
    fila = models.ClausulaReajuste(
        presupuesto_id=version.id, fecha_inicio=clausula.fecha_inicio,
        duracion_meses=clausula.duracion_meses,
        fecha_referencia_primer_anio=clausula.fecha_referencia_primer_anio,
        periodicidad=clausula.periodicidad, mecanismo=clausula.mecanismo.value,
        mecanismo_pagadero=(None if clausula.mecanismo_pagadero is None
                            else clausula.mecanismo_pagadero.value),
        fuente_pagadero=clausula.fuente_pagadero, estructura=clausula.estructura.value,
        fecha_base_indices=clausula.fecha_base_indices, r=clausula.r, fuente_r=clausula.fuente_r,
        r_en_comprobacion=clausula.r_en_comprobacion, fuente=clausula.fuente,
        responsable=clausula.responsable)
    session.add(fila)
    session.flush()
    session.add_all(
        models.ComponenteClausula(clausula_id=fila.id, orden=n, componente=c.componente,
                                  serie_id=series[c.serie].id, peso=c.peso)
        for n, c in enumerate(clausula.componentes))
    session.flush()
    return fila


def guardar_estudio(
    session: Session,
    version: models.Presupuesto,
    clausula: Clausula,
    periodos: Sequence[PeriodoDeclarado],
    *,
    fecha_calculo: date,
    fuente: str,
    responsable: str,
    reemplaza_a: int | None = None,
    lado: str = LADO_POR_DEFECTO,
    ahora: datetime | None = None,
) -> models.EstudioReajuste:
    """UC‑18 6: calcula el estudio con los índices vigentes, la tasa de cada cierre y la versión
    revalorada de cada período, y lo guarda con todo lo que usó (S1 §8.5). Solo agrega filas; la
    versión del contrato no cambia. Hace `flush`, no `commit`."""
    fuente, responsable = fuente.strip(), responsable.strip()
    if not fuente or not responsable:
        raise ValueError("el estudio exige fuente y responsable (UC-18 6)")
    periodos = list(periodos)
    if not periodos:
        raise ValueError("el estudio necesita al menos un periodo")
    if any(not e.fuente.strip() for p in periodos for e in p.ejecutado):
        raise ValueError("cada cantidad ejecutada exige su fuente: acta o valuacion (UC-18 2)")
    contrato = contrato_de_version(version)
    series = _series(session, clausula)
    comprobaciones = [_version_de_comprobacion(session, version, p.version_comprobacion)
                      for p in periodos]
    tasas = [_tasa_o_nada(session, p.hasta, lado) for p in periodos]
    resultado = calcular_estudio(
        clausula, contrato, periodos, _indices_vigentes(session, clausula, periodos),
        moneda=version.moneda, tasas=[None if t is None else t.valor for t in tasas],
        pu_comprobados=[_pu_de(v, p) for v, p in zip(comprobaciones, periodos, strict=True)],
        monto_original=sum((r.total for r in version.partidas), CERO), fecha_calculo=fecha_calculo,
        series_en_bs=frozenset(c for c, s in series.items() if s.unidad == UNIDAD_INDICE_BS))
    if reemplaza_a is not None:
        _exigir_reemplazo(session, version, reemplaza_a, resultado)
    fila_clausula = _guardar_clausula(session, version, clausula, series)
    estudio = models.EstudioReajuste(
        presupuesto_id=version.id, clausula_id=fila_clausula.id, fecha_calculo=fecha_calculo,
        estado=resultado.estado.value, fecha_corte=resultado.fecha_corte, reemplaza_a=reemplaza_a,
        moneda=version.moneda, lado=lado,
        monto_original=sum((r.total for r in version.partidas), CERO),
        total_escalatoria=resultado.total_escalatoria,
        total_comprobacion=resultado.total_comprobacion,
        total_reconocido=resultado.total_reconocido,
        avisos=json.dumps(list(resultado.avisos), ensure_ascii=False), fuente=fuente,
        responsable=responsable, fecha_hora=ahora or datetime.now())
    session.add(estudio)
    session.flush()
    for orden, (periodo, calculado, comprobacion, tasa) in enumerate(
            zip(periodos, resultado.periodos, comprobaciones, tasas, strict=True)):
        fila = models.PeriodoReajuste(
            estudio_id=estudio.id, orden=orden, desde=periodo.desde, hasta=periodo.hasta,
            km=calculado.km, escalatoria=calculado.escalatoria,
            comprobacion=calculado.comprobacion, reconocido=calculado.reconocido,
            mecanismo_reconocido=calculado.mecanismo_reconocido,
            version_comprobacion_id=None if comprobacion is None else comprobacion.id,
            tasa=None if tasa is None else tasa.valor,
            fecha_tasa=None if tasa is None else tasa.fecha,
            importaciones=json.dumps(dict(calculado.importaciones), sort_keys=True),
            marcas=json.dumps(list(calculado.marcas), ensure_ascii=False),
            excepcion=periodo.excepcion)
        session.add(fila)
        session.flush()
        session.add_all(
            models.EjecutadoPeriodo(periodo_id=fila.id, orden=n, codigo_partida=e.codigo,
                                    cantidad=e.cantidad, fuente=e.fuente)
            for n, e in enumerate(periodo.ejecutado))
    session.flush()
    return estudio


def _clausula_de(session: Session, clausula_id: int) -> Clausula:
    fila = session.get(models.ClausulaReajuste, clausula_id)
    componentes = session.execute(
        select(models.ComponenteClausula, models.SerieIndice.codigo)
        .join(models.SerieIndice, models.SerieIndice.id == models.ComponenteClausula.serie_id)
        .where(models.ComponenteClausula.clausula_id == clausula_id)
        .order_by(models.ComponenteClausula.orden)).all()
    return Clausula(
        fila.fecha_inicio, fila.duracion_meses, fila.fecha_referencia_primer_anio,
        fila.periodicidad, Mecanismo(fila.mecanismo), Estructura(fila.estructura),
        tuple(Componente(c.componente, codigo, c.peso) for c, codigo in componentes),
        fila.fecha_base_indices, fila.r, fila.fuente_r, fila.fuente, fila.responsable,
        mecanismo_pagadero=(None if fila.mecanismo_pagadero is None
                            else Mecanismo(fila.mecanismo_pagadero)),
        fuente_pagadero=fila.fuente_pagadero, r_en_comprobacion=fila.r_en_comprobacion)


def cargar_estudio(session: Session, estudio_id: int) -> EstudioCargado:
    """Recalcula el estudio con las importaciones que **cita**, la tasa guardada de cada cierre y
    los PU de la versión de comprobación citada, con su fecha de cálculo, y exige igualdad exacta de
    escalatoria, comprobación y reconocido por período con lo guardado (RNF‑14). Una revisión de
    un índice importada después no lo cambia. No escribe."""
    estudio = session.get(models.EstudioReajuste, estudio_id)
    if estudio is None:
        raise ValueError(f"no hay ningun estudio de reajuste {estudio_id}")
    version = session.get(models.Presupuesto, estudio.presupuesto_id)
    clausula = _clausula_de(session, estudio.clausula_id)
    filas = list(session.scalars(
        select(models.PeriodoReajuste).where(models.PeriodoReajuste.estudio_id == estudio.id)
        .order_by(models.PeriodoReajuste.orden)))
    periodos: list[PeriodoDeclarado] = []
    indices: dict[tuple[str, date], ValorFechado] = {}
    pu_comprobados: list[dict[str, Decimal] | None] = []
    for fila in filas:
        ejecutado = tuple(
            Ejecutado(e.codigo_partida, e.cantidad, e.fuente)
            for e in session.scalars(
                select(models.EjecutadoPeriodo).where(models.EjecutadoPeriodo.periodo_id == fila.id)
                .order_by(models.EjecutadoPeriodo.orden)))
        comprobacion = (None if fila.version_comprobacion_id is None
                        else session.get(models.Presupuesto, fila.version_comprobacion_id))
        periodo = PeriodoDeclarado(fila.desde, fila.hasta, ejecutado,
                                   "" if comprobacion is None else comprobacion.codigo,
                                   fila.excepcion)
        periodos.append(periodo)
        pu_comprobados.append(_pu_de(comprobacion, periodo))
        for clave, importacion_id in json.loads(fila.importaciones).items():
            serie, texto = clave.rsplit("@", 1)
            fecha = date.fromisoformat(texto)
            citado = valor_en(session, serie, fecha, importacion_id=importacion_id)
            if citado is None:
                raise ValueError(f"el estudio {estudio.id} cita la importacion {importacion_id} de "
                                 f"{serie} al {fecha:%d/%m/%Y}, que ya no esta en la base")
            indices[(serie, fecha)] = citado
    series = _series(session, clausula)
    resultado = calcular_estudio(
        clausula, contrato_de_version(version), periodos, indices, moneda=estudio.moneda,
        tasas=[fila.tasa for fila in filas], pu_comprobados=pu_comprobados,
        monto_original=estudio.monto_original, fecha_calculo=estudio.fecha_calculo,
        series_en_bs=frozenset(c for c, s in series.items() if s.unidad == UNIDAD_INDICE_BS))
    for fila, calculado in zip(filas, resultado.periodos, strict=True):
        guardado = (fila.escalatoria, fila.comprobacion, fila.reconocido)
        if (calculado.escalatoria, calculado.comprobacion, calculado.reconocido) != guardado:
            raise ValueError(
                f"el periodo {fila.desde:%d/%m/%Y}-{fila.hasta:%d/%m/%Y} del estudio {estudio.id} "
                "no recalcula igual a lo guardado (RNF-14)")
    return EstudioCargado(estudio.id, version.id, EstadoEstudio(estudio.estado),
                          estudio.reemplaza_a, clausula, tuple(periodos), resultado)
```
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/integration/test_estudio_reajuste.py tests/unit/test_reajuste.py -q -W error`; prueba de deriva de la sección B; `uv run pytest -q -W error`; `uv run python scripts/guardia_nucleo.py --base origin/main`.
- [ ] **Paso 5: Commit**
```bash
git add tests/integration/test_estudio_reajuste.py tests/fixtures/reajuste_s1.py
git commit -m "test(core): SL-E3 estudio guardado, recalculo exacto y parcial al corte en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add core/models/moneda.py core/models/__init__.py core/budget/reajuste.py core/budget/__init__.py migraciones/caso/versions/caso_0004_s1_reajuste.py
git commit -m "feat(core): SL-E3 estudio de reajuste guardado con sus importaciones citadas" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Tarea 13: Pantalla de UC‑18 y exportación por `hojas_extra`

**Rama:** `inc/060-s1-4-ui` (sale de `main` con `inc/060-s1-4-nucleo` fusionado)   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/reajuste.py`, `ui/paginas/reajuste.py`, `tests/unit/test_ui_reajuste.py`
- Modificar: `ui/app.py` («Reajuste de precios», `UC-18`, en Trabajo tras «Indices del BCV»), `tests/unit/test_ui_app.py` (títulos, caso de uso y conteo: catorce), `tests/unit/test_ui_importable.py` (`ui.reajuste` y catorce páginas); `tests/unit/test_arquitectura_s5.py`: `PAGINAS_QUE_ABREN_EL_CASO` gana `"reajuste"` (la página abre el caso con `_motor_del_caso()`, patrón de la Tarea 9)

**Interfaces:**
- Produce: `ui.reajuste` (más `COLUMNAS_EJECUTADO`, `NO_DISPONIBLE` y `parciales_por_reemplazar(sesion, proyecto, codigo) -> list[tuple[int, date]]` para el selector de la pantalla): `COLUMNAS_REAJUSTE = ("Período", "Escalatoria", "Comprobación", "Diferencia", "Reconocido", "Mecanismo", "Moneda", "Escalatoria (otra)", "Comprobación (otra)", "Diferencia (otra)", "Tasa", "Marcas")`; `clausula_desde_textos(campos: Mapping[str, str], componentes: Sequence[Mapping[str, str]]) -> Clausula`; `periodos_desde_filas(periodos, ejecutado) -> list[PeriodoDeclarado]`; `calcular(sesion, proyecto, codigo, clausula, periodos, *, fecha_calculo) -> ResultadoEstudio` (en memoria: `guardar_estudio` dentro de una transacción deshecha); `filas_lado_a_lado(resultado) -> list[dict[str, str]]`; `tabla_reajuste(resultado) -> TablaExportable` («Reajuste») y `tabla_ejecutado(periodos) -> TablaExportable` («Ejecutado»); `guardar(sesion, ..., fuente, responsable, reemplaza_a=None) -> int` (confirma); `excel_en_bytes(sesion, proyecto, codigo, resultado, periodos) -> bytes` (`exportar_hoja(..., hojas_extra=[tabla_reajuste, tabla_ejecutado])`).

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/unit/test_ui_reajuste.py
from datetime import date
from decimal import Decimal as D
from io import BytesIO

import openpyxl

from core.catalog import abrir_sesion, crear_esquema, crear_motor
from tests.fixtures.reajuste_s1 import NOMBRE, sembrar
from ui import reajuste

CAMPOS = {"fecha_inicio": "2026-01-15", "duracion_meses": "24",
          "fecha_referencia_primer_anio": "2026-01-15", "periodicidad": "mensual",
          "mecanismo": "ambos", "estructura": "declarada", "fecha_base_indices": "2026-01-01",
          "r": "0.10", "fuente_r": "memoria", "fuente": "contrato ficticio", "responsable": "Ing."}
COMPONENTES = [{"componente": "materiales", "serie": "FIC-MAT", "peso": "0.5"},
               {"componente": "equipos", "serie": "FIC-EQU", "peso": "0.2"},
               {"componente": "mano_obra", "serie": "FIC-MO", "peso": "0.3"}]


def test_lado_a_lado_guardado_y_excel_con_sus_totales(tmp_path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'r.db').as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        sembrar(sesion)
        sesion.commit()
        clausula = reajuste.clausula_desde_textos(CAMPOS, COMPONENTES)
        periodos = reajuste.periodos_desde_filas(
            [{"desde": "2027-02-01", "hasta": "2027-02-28", "version_comprobacion": "002", "excepcion": ""}],
            [{"periodo": "1", "partida": "S1-R01", "cantidad": "1000", "fuente": "AV-01"}])
        resultado = reajuste.calcular(sesion, NOMBRE, "001", clausula, periodos,
                                      fecha_calculo=date(2027, 3, 5))
        fila = reajuste.filas_lado_a_lado(resultado)[0]
        assert (fila["Escalatoria"], fila["Comprobación"], fila["Diferencia (otra)"]) == (
            "15300.00", "16000.00", "-0.82")
        estudio_id = reajuste.guardar(sesion, NOMBRE, "001", clausula, periodos,
                                      fecha_calculo=date(2027, 3, 5), fuente="estudio",
                                      responsable="Ing.")
        libro = openpyxl.load_workbook(BytesIO(reajuste.excel_en_bytes(
            sesion, NOMBRE, "001", resultado, periodos)))
        hoja = libro["Reajuste"]
        assert [c.value for c in hoja[1]][:5] == list(reajuste.COLUMNAS_REAJUSTE[:5])
        assert D(str(hoja.cell(2, 2).value)) == D(15300) and estudio_id > 0
    motor.dispose()
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_ui_reajuste.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'reajuste' from 'ui'`
- [ ] **Paso 3: Implementación mínima**
```python
# ui/reajuste.py
"""UC-18 sin Streamlit: de los textos de la pantalla a la clausula y los periodos, el calculo en
memoria, la tabla lado a lado, el guardado y el Excel por `hojas_extra` (spec S1 §8). La pantalla
`ui/paginas/reajuste.py` solo pinta. Sin Streamlit, sin pandas y sin `ui.caso` (lo vigila
`tests/unit/test_arquitectura_s1.py`). Las celdas se leen con `ui.composicion.texto_de_celda`.

`calcular` usa el mismo `guardar_estudio` que guarda y el recalculo de `cargar_estudio`, dentro de
una transaccion que se deshace entera al terminar: lo que se ve antes de guardar es exactamente lo
que se guardaria, y nada queda escrito. Por eso se llama con una sesion sin cambios pendientes (la
pantalla abre una por accion)."""
from __future__ import annotations

import tempfile
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from sqlalchemy import select

from core import models
from core.budget import TablaExportable, cargar_elaboracion, exportar_hoja
from core.budget.reajuste import (
    Clausula,
    Componente,
    Ejecutado,
    EstadoEstudio,
    Estructura,
    Mecanismo,
    PeriodoDeclarado,
    ResultadoEstudio,
    cargar_estudio,
    guardar_estudio,
)
from core.catalog import Catalogo
from core.contracts import ParametrosCosto
from core.verification.texto import formatear_decimal
from ui.composicion import ComposicionInvalida, decimal_desde_texto, texto_de_celda
from ui.hoja import HojaInvalida

COLUMNAS_REAJUSTE = (
    "Período",
    "Escalatoria",
    "Comprobación",
    "Diferencia",
    "Reconocido",
    "Mecanismo",
    "Moneda",
    "Escalatoria (otra)",
    "Comprobación (otra)",
    "Diferencia (otra)",
    "Tasa",
    "Marcas",
)
COLUMNAS_EJECUTADO = ("Período", "Partida", "Cantidad", "Fuente")
NO_DISPONIBLE = "no disponible"
FUENTE_DEL_CALCULO = "calculo en pantalla, sin guardar"
_SI = {"si", "sí", "true", "1"}


# --- textos -> clausula y periodos ---------------------------------------------------------------


def _texto(fila: Mapping[str, object], campo: str, *, obligatorio: bool = True) -> str:
    texto = texto_de_celda(fila, campo)
    if obligatorio and not texto:
        raise HojaInvalida(f"Escriba «{campo}»: es obligatorio (UC-18).")
    return texto


def _fecha(texto: str, campo: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise HojaInvalida(f"{campo}: {texto!r} no es una fecha AAAA-MM-DD.") from None


def _decimal(texto: str, campo: str) -> Decimal:
    try:
        return decimal_desde_texto(texto, campo)
    except ComposicionInvalida as error:
        raise HojaInvalida(str(error)) from None


def _opcion[E: StrEnum](tipo: type[E], texto: str, campo: str) -> E:
    try:
        return tipo(texto)
    except ValueError:
        opciones = ", ".join(m.value for m in tipo)
        raise HojaInvalida(f"{campo}: {texto!r}; se espera uno de {opciones}.") from None


def _con_datos(fila: Mapping[str, object]) -> bool:
    return any(texto_de_celda(fila, clave) for clave in fila)


def clausula_desde_textos(
    campos: Mapping[str, str], componentes: Sequence[Mapping[str, str]]
) -> Clausula:
    """La clausula de S1 §8.1 desde el formulario y la tabla de componentes (filas en blanco se
    ignoran). `HojaInvalida` con el campo culpable, o con la regla de la clausula que no cumple."""
    try:
        duracion = int(_texto(campos, "duracion_meses"))
    except ValueError:
        raise HojaInvalida("duracion_meses: escriba un numero entero de meses.") from None
    lista = []
    for fila in (f for f in componentes if _con_datos(f)):
        componente = _texto(fila, "componente")
        peso = _texto(fila, "peso", obligatorio=False)
        lista.append(Componente(componente, _texto(fila, "serie"),
                                _decimal(peso, f"peso de {componente}") if peso else None))
    pagadero = _texto(campos, "mecanismo_pagadero", obligatorio=False)
    try:
        return Clausula(
            _fecha(_texto(campos, "fecha_inicio"), "fecha_inicio"),
            duracion,
            _fecha(_texto(campos, "fecha_referencia_primer_anio"), "fecha_referencia_primer_anio"),
            _texto(campos, "periodicidad"),
            _opcion(Mecanismo, _texto(campos, "mecanismo"), "mecanismo"),
            _opcion(Estructura, _texto(campos, "estructura"), "estructura"),
            tuple(lista),
            _fecha(_texto(campos, "fecha_base_indices"), "fecha_base_indices"),
            _decimal(_texto(campos, "r"), "r"),
            _texto(campos, "fuente_r"),
            _texto(campos, "fuente"),
            _texto(campos, "responsable"),
            mecanismo_pagadero=(_opcion(Mecanismo, pagadero, "mecanismo_pagadero")
                                if pagadero else None),
            fuente_pagadero=_texto(campos, "fuente_pagadero", obligatorio=False),
            r_en_comprobacion=(
                _texto(campos, "r_en_comprobacion", obligatorio=False).casefold() in _SI
            ),
        )
    except HojaInvalida:
        raise
    except ValueError as error:  # las reglas de la clausula (pesos que no suman 1, R, ...)
        raise HojaInvalida(f"La clausula no es valida: {error}") from None


def periodos_desde_filas(
    periodos: Sequence[Mapping[str, str]], ejecutado: Sequence[Mapping[str, str]]
) -> list[PeriodoDeclarado]:
    """Los periodos (desde, hasta, version de comprobacion, excepcion) y lo ejecutado de cada uno
    (`periodo` es el numero del periodo, desde 1; la fuente es obligatoria por fila, UC-18 2)."""
    filas = [f for f in periodos if _con_datos(f)]
    por_periodo: dict[int, list[Ejecutado]] = {n: [] for n in range(1, len(filas) + 1)}
    for fila in (f for f in ejecutado if _con_datos(f)):
        try:
            numero = int(_texto(fila, "periodo"))
        except ValueError:
            raise HojaInvalida("periodo: escriba el numero del periodo (1, 2, ...).") from None
        if numero not in por_periodo:
            raise HojaInvalida(f"periodo {numero}: no hay un periodo con ese numero.")
        partida = _texto(fila, "partida")
        por_periodo[numero].append(Ejecutado(
            partida, _decimal(_texto(fila, "cantidad"), f"cantidad de {partida}"),
            _texto(fila, "fuente")))
    return [
        PeriodoDeclarado(
            _fecha(_texto(fila, "desde"), "desde"), _fecha(_texto(fila, "hasta"), "hasta"),
            tuple(por_periodo[n]), _texto(fila, "version_comprobacion", obligatorio=False),
            _texto(fila, "excepcion", obligatorio=False))
        for n, fila in enumerate(filas, start=1)
    ]


# --- calcular, guardar y presentar ------------------------------------------------------------


def _version(sesion, proyecto: str, codigo: str) -> models.Presupuesto:
    version = sesion.scalars(
        select(models.Presupuesto).join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto, models.Presupuesto.codigo == codigo)
    ).one_or_none()
    if version is None:
        raise HojaInvalida(f"El proyecto {proyecto!r} no tiene una version {codigo!r}.")
    return version


def calcular(sesion, proyecto: str, codigo: str, clausula: Clausula,
             periodos: Sequence[PeriodoDeclarado], *, fecha_calculo: date) -> ResultadoEstudio:
    """UC-18 3-5 en memoria (ver el docstring del modulo): nada queda escrito."""
    try:
        estudio = guardar_estudio(
            sesion, _version(sesion, proyecto, codigo), clausula, periodos,
            fecha_calculo=fecha_calculo, fuente=FUENTE_DEL_CALCULO,
            responsable=clausula.responsable,
        )
        return cargar_estudio(sesion, estudio.id).resultado
    except HojaInvalida:
        raise
    except ValueError as error:
        raise HojaInvalida(f"No se pudo calcular: {error}") from error
    finally:
        sesion.rollback()


def guardar(sesion, proyecto: str, codigo: str, clausula: Clausula,
            periodos: Sequence[PeriodoDeclarado], *, fecha_calculo: date, fuente: str,
            responsable: str, reemplaza_a: int | None = None) -> int:
    """UC-18 6: guarda el estudio y confirma; devuelve su id. Si algo falla, deshace todo."""
    try:
        estudio = guardar_estudio(
            sesion, _version(sesion, proyecto, codigo), clausula, periodos,
            fecha_calculo=fecha_calculo, fuente=fuente, responsable=responsable,
            reemplaza_a=reemplaza_a,
        )
        sesion.commit()
    except HojaInvalida:
        sesion.rollback()
        raise
    except ValueError as error:
        sesion.rollback()
        raise HojaInvalida(f"No se guardo el estudio: {error}") from error
    except BaseException:
        sesion.rollback()
        raise
    return estudio.id


def parciales_por_reemplazar(sesion, proyecto: str, codigo: str) -> list[tuple[int, date]]:
    """Los estudios «parcial al corte» de la version que nadie reemplazo aun (id, fecha de
    calculo): los unicos que un estudio cerrado puede reemplazar (S1-R21)."""
    version = _version(sesion, proyecto, codigo)
    reemplazados = select(models.EstudioReajuste.reemplaza_a).where(
        models.EstudioReajuste.reemplaza_a.is_not(None))
    return [
        (estudio.id, estudio.fecha_calculo)
        for estudio in sesion.scalars(
            select(models.EstudioReajuste)
            .where(models.EstudioReajuste.presupuesto_id == version.id,
                   models.EstudioReajuste.estado == EstadoEstudio.PARCIAL.value,
                   models.EstudioReajuste.id.not_in(reemplazados))
            .order_by(models.EstudioReajuste.id)
        )
    ]


def _monto(valor: Decimal | None) -> str:
    return NO_DISPONIBLE if valor is None else formatear_decimal(valor, 2)


def _suma(valores) -> Decimal | None:
    presentes = [v for v in valores if v is not None]
    return sum(presentes, Decimal(0)) if presentes else None


def _periodo(desde: date, hasta: date) -> str:
    return f"{desde:%d/%m/%Y} a {hasta:%d/%m/%Y}"


def _valores(resultado: ResultadoEstudio) -> list[tuple]:
    """Una fila por periodo y la del total, con los montos como `Decimal` (o `None`)."""
    filas = []
    for p in resultado.periodos:
        c = p.comparacion
        filas.append((_periodo(p.desde, p.hasta), p.escalatoria, p.comprobacion, c.diferencia,
                      p.reconocido, p.mecanismo_reconocido, c.moneda, c.escalatoria_otra,
                      c.comprobacion_otra, c.diferencia_otra, c.tasa, "; ".join(p.marcas)))
    comparaciones = [p.comparacion for p in resultado.periodos]
    filas.append((
        "Total", resultado.total_escalatoria, resultado.total_comprobacion,
        _suma(c.diferencia for c in comparaciones), resultado.total_reconocido, "",
        resultado.moneda, _suma(c.escalatoria_otra for c in comparaciones),
        _suma(c.comprobacion_otra for c in comparaciones),
        _suma(c.diferencia_otra for c in comparaciones), None,
        "; ".join((f"estado: {resultado.estado.value}", *resultado.avisos)),
    ))
    return filas


def filas_lado_a_lado(resultado: ResultadoEstudio) -> list[dict[str, str]]:
    """La tabla lado a lado de UC-18 5 como texto: montos a dos decimales (redondeados una sola
    vez, S1 §8.4), «no disponible» donde no hay dato; la tasa exacta. Marcas y avisos van como
    texto en celdas (RV-14)."""
    salida = []
    for fila in _valores(resultado):
        textos = list(fila)
        for i in (1, 2, 3, 4, 7, 8, 9):
            textos[i] = _monto(fila[i])
        textos[10] = "" if fila[0] == "Total" else (
            NO_DISPONIBLE if fila[10] is None else formatear_decimal(fila[10]))
        salida.append(dict(zip(COLUMNAS_REAJUSTE, textos, strict=True)))
    return salida


def tabla_reajuste(resultado: ResultadoEstudio) -> TablaExportable:
    """La hoja «Reajuste» del Excel: los montos como numeros; lo que no hay, «no disponible»."""
    return TablaExportable(
        "Reajuste",
        COLUMNAS_REAJUSTE,
        tuple(tuple(NO_DISPONIBLE if v is None else v for v in fila)
              for fila in _valores(resultado)),
    )


def tabla_ejecutado(periodos: Sequence[PeriodoDeclarado]) -> TablaExportable:
    """La hoja «Ejecutado» del Excel: lo ejecutado de cada periodo con su fuente."""
    return TablaExportable(
        "Ejecutado",
        COLUMNAS_EJECUTADO,
        tuple((_periodo(p.desde, p.hasta), e.codigo, e.cantidad, e.fuente)
              for p in periodos for e in p.ejecutado),
    )


def excel_en_bytes(sesion, proyecto: str, codigo: str, resultado: ResultadoEstudio,
                   periodos: Sequence[PeriodoDeclarado]) -> bytes:
    """El libro de la version del contrato (`exportar_hoja`) con las hojas Reajuste y Ejecutado
    por `hojas_extra` (RF-71), como bytes para `st.download_button`."""
    version = _version(sesion, proyecto, codigo)
    elaboracion = cargar_elaboracion(sesion, proyecto, codigo, Catalogo(sesion))
    parametros = ParametrosCosto(fcas=version.fcas, bono_alimentacion=version.bono_alimentacion,
                                 administracion=version.administracion, utilidad=version.utilidad)
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = exportar_hoja(
            elaboracion.presupuesto, elaboracion.informe, Path(carpeta) / "reajuste.xlsx",
            parametros, hojas_extra=[tabla_reajuste(resultado), tabla_ejecutado(periodos)],
        )
        return ruta.read_bytes()
```
```python
# ui/paginas/reajuste.py
"""Pantalla «Reajuste de precios» (UC-18): la clausula, los periodos con lo ejecutado y su fuente,
la escalatoria y la comprobacion directa lado a lado en las dos monedas, el guardado del estudio y
su Excel. La logica vive en `ui.reajuste` (sin Streamlit); aqui solo se pinta. Avisos y marcas van
en celdas o por `ui.texto_seguro` (RV-14). Sin efectos al importarse."""
from __future__ import annotations

from datetime import date

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.budget.reajuste import COMPONENTES, EstadoEstudio, Estructura, Mecanismo
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from ui import reajuste
from ui.caso import proyecto_abierto, ruta_caso
from ui.hoja import HojaInvalida, historial_de_versiones
from ui.texto_seguro import texto_seguro

CLAVE_CALCULO = "reajuste_calculo"  # (contrato, clausula, periodos, resultado): no es de widget
CLAVE_EXCEL = "reajuste_excel"  # bytes del ultimo Excel preparado


def _motor_del_caso():
    """El motor del caso abierto, ya en `head` (RV-5); `None` si no se puede preparar."""
    ruta = ruta_caso()
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(str(error))
        return None
    return crear_motor(f"sqlite:///{ruta.as_posix()}")


def render() -> None:
    proyecto = proyecto_abierto()
    if proyecto is None:
        st.info("Abra un proyecto en la barra superior (Proyecto) para reajustar sus precios.")
        return
    motor = _motor_del_caso()
    if motor is None:
        return
    try:
        with abrir_sesion(motor) as sesion:
            versiones = historial_de_versiones(sesion, proyecto)
        if not versiones:
            st.info("El proyecto no tiene versiones guardadas: guarde la del contrato primero.")
            return
        _pintar(motor, proyecto, versiones)
    except SQLAlchemyError as error:
        st.error(f"No se pudo leer o escribir el caso: {getattr(error, 'orig', None) or error}")
    finally:
        motor.dispose()


def _clausula() -> tuple[dict[str, str], list[dict[str, str]]]:
    st.subheader("1. La clausula de reajuste (S1 §8.1, a cotejar con la Gaceta)")
    a, b, c = st.columns(3)
    inicio = a.date_input("Inicio del contrato", value=None)
    duracion = b.text_input("Duracion (meses)")
    primer_anio = c.date_input("El primer año corre desde", value=None,
                               help="Por defecto, el inicio del contrato (a cotejar).")
    d, e, f = st.columns(3)
    periodicidad = d.selectbox("Periodicidad", ("mensual", "trimestral"))
    mecanismo = e.selectbox("Mecanismo", [m.value for m in Mecanismo])
    pagadero = f.selectbox("Mecanismo pagadero (solo con «ambos»)",
                           ["", Mecanismo.ESCALATORIA.value, Mecanismo.COMPROBACION.value])
    fuente_pagadero = st.text_input("Fuente del mecanismo pagadero")
    g, h, i = st.columns(3)
    estructura = g.selectbox("Estructura", [x.value for x in Estructura])
    base = h.date_input("Mes base de los indices (I0)", value=None)
    r = i.text_input("R (fraccion no reajustable)")
    fuente_r = st.text_input("Fuente de R (si el contrato no la trae, escriba 0 y declarelo)")
    r_en_comprobacion = st.checkbox("La clausula aplica R tambien a la comprobacion (S1-R14)")
    fuente = st.text_input("Fuente de la clausula (contrato, numero, fecha)")
    responsable = st.text_input("Responsable")
    st.caption("Componentes: la serie de cada uno y, si la estructura es declarada, su peso.")
    componentes = st.data_editor(
        DataFrame({"componente": list(COMPONENTES), "serie": [""] * 3, "peso": [""] * 3}),
        hide_index=True, key="reajuste_componentes",
    )
    referencia = primer_anio or inicio
    campos = {
        "fecha_inicio": inicio.isoformat() if inicio else "",
        "duracion_meses": duracion,
        "fecha_referencia_primer_anio": referencia.isoformat() if referencia else "",
        "periodicidad": periodicidad,
        "mecanismo": mecanismo,
        "mecanismo_pagadero": pagadero,
        "fuente_pagadero": fuente_pagadero,
        "estructura": estructura,
        "fecha_base_indices": date(base.year, base.month, 1).isoformat() if base else "",
        "r": r,
        "fuente_r": fuente_r,
        "r_en_comprobacion": "si" if r_en_comprobacion else "no",
        "fuente": fuente,
        "responsable": responsable,
    }
    return campos, componentes.to_dict("records")


def _periodos(versiones) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    st.subheader("2. Periodos y lo ejecutado (con su fuente)")
    revaloradas = [v.codigo for v in versiones if v.motivo == "revaloracion"]
    st.caption("Versiones revaloradas para la comprobacion directa: "
               + (", ".join(revaloradas) or "ninguna (la comprobacion quedara «no disponible»)"))
    periodos = st.data_editor(
        DataFrame({"desde": [""], "hasta": [""], "version_comprobacion": [""], "excepcion": [""]}),
        num_rows="dynamic", hide_index=True, key="reajuste_periodos",
    )
    ejecutado = st.data_editor(
        DataFrame({"periodo": ["1"], "partida": [""], "cantidad": [""], "fuente": [""]}),
        num_rows="dynamic", hide_index=True, key="reajuste_ejecutado",
    )
    st.caption("Fechas en AAAA-MM-DD. «periodo» es el numero de la fila de periodos (1, 2, ...).")
    return periodos.to_dict("records"), ejecutado.to_dict("records")


def _pintar(motor, proyecto: str, versiones) -> None:
    contrato = st.selectbox("Version del contrato", [v.codigo for v in versiones])
    campos, componentes = _clausula()
    filas_periodos, filas_ejecutado = _periodos(versiones)
    if st.button("Calcular", type="primary"):
        try:
            clausula = reajuste.clausula_desde_textos(campos, componentes)
            periodos = reajuste.periodos_desde_filas(filas_periodos, filas_ejecutado)
            with abrir_sesion(motor) as sesion:
                resultado = reajuste.calcular(sesion, proyecto, contrato, clausula, periodos,
                                              fecha_calculo=date.today())
        except HojaInvalida as error:
            st.error(texto_seguro(str(error)))
        else:
            st.session_state[CLAVE_CALCULO] = (contrato, clausula, periodos, resultado)
            st.session_state.pop(CLAVE_EXCEL, None)
    calculo = st.session_state.get(CLAVE_CALCULO)
    if calculo is None or calculo[0] != contrato:
        return
    _, clausula, periodos, resultado = calculo
    st.subheader("3. Escalatoria y comprobacion, lado a lado")
    st.dataframe(DataFrame(reajuste.filas_lado_a_lado(resultado),
                           columns=list(reajuste.COLUMNAS_REAJUSTE)),
                 hide_index=True, width="stretch")
    for aviso in resultado.avisos:
        st.warning(texto_seguro(aviso))
    if resultado.estado is EstadoEstudio.PARCIAL:
        st.info(f"El ultimo periodo aun no cierra: el estudio se guardara «parcial al corte» al "
                f"{resultado.fecha_corte:%d/%m/%Y} y se reemplaza al cerrar el mes (S1-R21).")
    _guardar(motor, proyecto, contrato, clausula, periodos, resultado)
    _excel(motor, proyecto, contrato, resultado, periodos)


def _guardar(motor, proyecto, contrato, clausula, periodos, resultado) -> None:
    st.subheader("4. Guardar el estudio")
    with abrir_sesion(motor) as sesion:
        parciales = reajuste.parciales_por_reemplazar(sesion, proyecto, contrato)
    fuente = st.text_input("Fuente del estudio", key="reajuste_fuente")
    responsable = st.text_input("Responsable del estudio", key="reajuste_responsable")
    reemplaza = None
    if parciales and resultado.estado is EstadoEstudio.CERRADO:
        elegido = st.selectbox("Reemplaza al estudio parcial", [None, *parciales],
                               format_func=lambda x: "ninguno" if x is None
                               else f"{x[0]} (calculado el {x[1]:%d/%m/%Y})")
        reemplaza = None if elegido is None else elegido[0]
    if st.button("Guardar estudio"):
        try:
            with abrir_sesion(motor) as sesion:
                estudio = reajuste.guardar(sesion, proyecto, contrato, clausula, periodos,
                                           fecha_calculo=date.today(), fuente=fuente,
                                           responsable=responsable, reemplaza_a=reemplaza)
        except HojaInvalida as error:
            st.error(texto_seguro(str(error)))
        else:
            st.success(f"Estudio {estudio} guardado ({resultado.estado.value}).")


def _excel(motor, proyecto, contrato, resultado, periodos) -> None:
    if st.button("Preparar Excel"):
        try:
            with abrir_sesion(motor) as sesion:
                st.session_state[CLAVE_EXCEL] = reajuste.excel_en_bytes(
                    sesion, proyecto, contrato, resultado, periodos)
        except (HojaInvalida, ValueError) as error:
            st.error(texto_seguro(f"No se pudo preparar el Excel: {error}"))
    contenido = st.session_state.get(CLAVE_EXCEL)
    if contenido is not None:
        st.download_button("Descargar Excel", contenido, file_name=f"reajuste_{contrato}.xlsx")
```
```python
# ui/app.py — `reajuste` en la importación de `ui.paginas` (orden alfabético) y, en PAGINAS, tras
# «Indices del BCV»:
    DefinicionPagina(reajuste.render, "Reajuste de precios", SECCION_TRABAJO, "UC-18"),
```
```python
# tests/unit/test_ui_app.py — «Reajuste de precios» al final de TITULOS_TRABAJO, el caso de uso y
# catorce pantallas
TITULOS_TRABAJO = (
    "Inicio",
    "Catalogo de partidas e insumos",
    "Componer una partida",
    "Elaborar un presupuesto",
    "Hoja del proyecto",
    "Actualizar precios",
    "Historico de cambios de precio",
    "Precios de la empresa",
    "Indices del BCV",
    "Reajuste de precios",
)

CASOS_DE_USO = {
    "actualizacion": "UC-02",
    "componer": "UC-10 / UC-11",
    "elaborar": "UC-01",
    "escenarios": "UC-08",
    "indices": "UC-17",
    "precios_empresa": "UC-17",
    "reajuste": "UC-18",
    "similares": "UC-03",
}


def test_son_catorce_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
    rutas = [p.ruta_url for p in PAGINAS]
    assert len(rutas) == 14
    assert rutas.index("hoja") == rutas.index("elaborar") + 1
    assert pagina_por_ruta("hoja").seccion == SECCION_TRABAJO
```
```python
# tests/unit/test_ui_importable.py — `"ui.reajuste"` al final de MODULOS_SIN_PAGINA y catorce
MODULOS_SIN_PAGINA = (
    "ui.app",
    "ui.caso",
    "ui.recorridos",
    "ui.composicion",
    "ui.elaboracion",
    "ui.hoja",
    "ui.resultado",
    "ui.texto_seguro",
    "ui.indices",
    "ui.precios_empresa",
    "ui.reajuste",
)
# y en test_las_paginas_se_importan_sin_efectos:
    assert len(modulos) == len(MODULOS_SIN_PAGINA) + 14  # las catorce paginas del marco
```
```python
# tests/unit/test_arquitectura_s5.py — la pagina de reajuste abre el caso
PAGINAS_QUE_ABREN_EL_CASO = (
    "actualizacion", "catalogo", "componer", "elaborar", "escenarios", "historico", "hoja",
    "indices", "precios_empresa", "reajuste", "similares", "simulador",
)
```
- [ ] **Paso 4: Correrla y ver el verde**: `uv run pytest tests/unit/test_ui_reajuste.py tests/unit/test_ui_app.py tests/unit/test_arquitectura_s1.py tests/unit/test_arquitectura_s5.py tests/unit/test_ui_importable.py -q -W error`. **Compuerta GS1‑4:** meta `--hasta S1-4` OK, CI verde, cuatro encargos, aval del tutor de SL‑E3; fusionar.
- [ ] **Paso 5: Commit**
```bash
git add tests/unit/test_ui_reajuste.py
git commit -m "test(ui): reajuste lado a lado y Excel por hojas_extra en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add ui/reajuste.py ui/paginas/reajuste.py ui/app.py tests/unit/test_ui_app.py tests/unit/test_ui_importable.py tests/unit/test_arquitectura_s5.py
git commit -m "feat(ui): pantalla de reajuste de precios (UC-18)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

# S1‑5 — Cierre (ramas `inc/060-s1-5-cierre` y `inc/060-s1-5-base`)

### Tarea 14: Versión 0.6.0, manuales, recorrido, etiqueta y base de prueba de la 0.6.0

**Rama:** `inc/060-s1-5-cierre` (sale de `main` con todo S1 fusionado; PR a `main`) y, tras la etiqueta, `inc/060-s1-5-base` (sale de `origin/main` en `v0.6.0`; PR a `main`)   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear (cierre): `tests/fixtures/caso_s1.py`
- Modificar (cierre): `scripts/generar_base_prueba.py` (`CONSTRUCTORES` gana `"s1.db"`), `tests/unit/test_generar_base_prueba.py` (`test_los_casos_de_la_base_de_prueba`), `pyproject.toml:3` (`version = "0.6.0"`), `uv.lock` (con `uv lock`), `CHANGELOG.md` (`[Sin publicar]` → `[0.6.0] - <fecha>`), `ui/recorridos.py` (recorrido «Moneda, precios de empresa y reajuste»), `tests/unit/test_ui_recorridos.py`, `docs/manual_usuario.md`, `docs/manual_tecnico.md`, `.github/workflows/ci.yml` (`--hasta S1-4` si aún no lo estaba)
- Crear (base): `tests/integration/test_base_0_6_0.py`, `tests/fixtures/bases/v0_6_0/demo.db`, `of001.db`, `ti001.db`, `s1.db` y `ficha.json` (**generados** con el código de `v0.6.0`, procedimiento de B, Tarea 2)
- Modificar (base): `.github/workflows/ci.yml` (`--hasta S1-5`), `docs/bitacora/2026-10-silice-060.md` (compuerta GS1)

**Interfaces:**
- Consume (sección B): `scripts/generar_base_prueba.py` (`CONSTRUCTORES: dict[str, Callable[[Path], object]]`, `main(["--salida", …, "--version", …, "--etiqueta", …, "--commit", …])`, que llama a `preparar_base` antes de cada constructor); `tests.fixtures.bases_prueba` (`ficha`, `copiar_base`, `diferencias_con_ficha`); `operacion.base_datos` (`preparar_base`, `leer_estado`, `revision_head`, `Destino`). De C: `tests.fixtures.precios_empresa_s1.sembrar`, `tests.fixtures.reajuste_s1` (`sembrar`, `NOMBRE`, `CLAUSULA`, `PERIODO`), `convertir_version`, `guardar_estudio`, `cargar_estudio`, `tasa_aplicable`.
- Produce: `tests.fixtures.caso_s1.sembrar_caso_s1(sesion) -> None`, `plantilla_s1(ruta: Path) -> Path`; `ui.recorridos.NOMBRE_MONEDA = "Moneda, precios de empresa y reajuste"`; `tests/fixtures/bases/v0_6_0/` con su `ficha.json` (formato de B: `version`, `etiqueta`, `commit`, `bases`).

- [ ] **Paso 1: Escribir las pruebas que fallan (rama `inc/060-s1-5-cierre`)**
En `tests/unit/test_generar_base_prueba.py`, `test_los_tres_casos_de_la_base_de_prueba` pasa a:
```python
def test_los_casos_de_la_base_de_prueba() -> None:
    assert list(generador.CONSTRUCTORES) == ["demo.db", "of001.db", "ti001.db", "s1.db"]
```
En `tests/unit/test_ui_recorridos.py`, importar también `NOMBRE_MONEDA`; `test_hay_tres_recorridos_en_el_orden_declarado` pasa a `test_hay_cuatro_recorridos_en_el_orden_declarado` con `(NOMBRE_DEMOSTRACION, NOMBRE_PRESUPUESTO, NOMBRE_PRECIOS, NOMBRE_MONEDA)`, y se agrega:
```python
def test_el_recorrido_de_moneda_pasa_por_las_pantallas_de_s1() -> None:
    recorrido = recorrido_por_nombre(NOMBRE_MONEDA)
    assert [paso.pagina for paso in recorrido.pasos] == [
        "indices", "precios_empresa", "hoja", "reajuste",
    ]
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_generar_base_prueba.py tests/unit/test_ui_recorridos.py -v -W error`
Esperado: FAIL con `AssertionError` en la lista de `CONSTRUCTORES` y `ImportError: cannot import name 'NOMBRE_MONEDA' from 'ui.recorridos'`.
```bash
git add tests/unit/test_generar_base_prueba.py tests/unit/test_ui_recorridos.py
git commit -m "test(release): base de prueba con el caso S1 y recorrido de moneda en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima (cierre)**
```python
# tests/fixtures/caso_s1.py
"""El caso S1 de la base de prueba de la 0.6.0 (RV-3, PRU-H15; plan 0.6.0, seccion C, tarea 14).

Una base en `head` con lo que agrega S1: la clinica (linea base) con su 001 en USD convertida a Bs
(002), la lista de empresa de `s1_precios_empresa.md` y el estudio de `s1_reajuste.md` guardado.
`scripts/generar_base_prueba.py` la construye con el codigo de la etiqueta `v0.6.0`, despues de que
`preparar_base` la creo en `head`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import select

from core import models
from core.budget.moneda import convertir_version
from core.budget.reajuste import guardar_estudio
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.catalog.indices import tasa_aplicable
from core.catalog.moneda import TasaDeclarada
from scripts.seed import sembrar as sembrar_linea_base
from tests.fixtures import precios_empresa_s1, reajuste_s1
from tests.fixtures.versiones import elaborar_001, guardar_001

FECHA_CONVERSION = date(2026, 10, 1)  # tasa venta 860,18 (BCV, verificada; s1_conversion.md)


def sembrar_caso_s1(sesion) -> None:
    """Clinica convertida, lista de empresa y estudio de reajuste. No hace `commit`."""
    proyecto = sembrar_linea_base(sesion)
    guardar_001(sesion, proyecto, elaborar_001(sesion))
    precios_empresa_s1.sembrar(sesion)
    tasa = TasaDeclarada.de_importacion(tasa_aplicable(sesion, FECHA_CONVERSION))
    convertir_version(sesion, proyecto.nombre, "001", "002", "Bs", tasa,
                      fuente="base de prueba 0.6.0", responsable="Ing. Prueba",
                      catalogo=Catalogo(sesion))
    reajuste_s1.sembrar(sesion)
    contrato = sesion.scalars(
        select(models.Presupuesto).join(models.Proyecto).where(
            models.Proyecto.nombre == reajuste_s1.NOMBRE, models.Presupuesto.codigo == "001")
    ).one()
    guardar_estudio(sesion, contrato, reajuste_s1.CLAUSULA, [reajuste_s1.PERIODO],
                    fecha_calculo=date(2027, 3, 5), fuente="base de prueba 0.6.0",
                    responsable="Ing. Prueba")


def plantilla_s1(ruta: Path) -> Path:
    """Siembra el caso S1 en `ruta` (ya en `head`) y confirma."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_caso_s1(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta
```
```python
# scripts/generar_base_prueba.py — el caso S1 entra como cuarta base. En el docstring, «Tres bases»
# pasa a «Cuatro bases (la cuarta, desde la 0.6.0)» y se agrega, tras la viñeta de `ti001.db`:
#   - `s1.db` (desde la 0.6.0): el caso S1, la clinica convertida a Bs, la lista de empresa de la
#     memoria y el estudio de reajuste guardado (`tests.fixtures.caso_s1.plantilla_s1`).
from tests.fixtures.caso_s1 import plantilla_s1  # noqa: E402
from tests.fixtures.hoja_en_base import plantilla_of001, plantilla_ti001  # noqa: E402

CONSTRUCTORES: dict[str, Callable[[Path], object]] = {
    "demo.db": _demo,
    "of001.db": plantilla_of001,
    "ti001.db": plantilla_ti001,
    "s1.db": plantilla_s1,
}
```
  En `ui/recorridos.py`, junto a los otros nombres (tras `NOMBRE_PRECIOS`):
```python
NOMBRE_MONEDA = "Moneda, precios de empresa y reajuste"
```
  y, al final de `RECORRIDOS`:
```python
    Recorrido(
        NOMBRE_MONEDA,
        "Llevar un proyecto a su moneda, auditar los precios de la empresa y reajustarlos.",
        (
            Paso("Importar la tasa del BCV", "indices",
                 "Suba el archivo trimestral de la tasa, revise el informe previo y confirme.",
                 "La tasa queda importada con su fuente y su huella."),
            Paso("Crear la lista de la empresa", "precios_empresa",
                 "Cargue la referencia MaPreX en Bs y cree la lista de la empresa con su archivo.",
                 "Ve los hallazgos R11 y R12 a la fecha de evaluacion."),
            Paso("Revisar la moneda y los precios", "hoja",
                 "Abra la version, revise la moneda en Parametros y el origen y la erosion en "
                 "Precios.",
                 "Cada precio muestra su origen, su erosion y su estado."),
            Paso("Reajustar y exportar", "reajuste",
                 "Declare la clausula, los periodos y el ejecutado; calcule y exporte el Excel.",
                 "Ve la escalatoria y la comprobacion lado a lado y descarga el Excel."),
        ),
    ),
```
  Versión, candado y `CHANGELOG.md` (el alias `ARENIA_*` de A1 sigue aceptado en esta versión: `ULTIMA_VERSION_CON_ALIAS = "0.6.0"`), desde la raíz del worktree en Git Bash:
```bash
sed -i 's/^version = ".*"$/version = "0.6.0"/' pyproject.toml
grep -n '^version = "0.6.0"$' pyproject.toml
uv lock
uv run python - <<'EOF'
from datetime import date
from pathlib import Path

ruta = Path("CHANGELOG.md")
texto = ruta.read_text(encoding="utf-8")
assert texto.count("## [Sin publicar]") == 1
nueva = f"## [Sin publicar]\n\n## [0.6.0] - {date.today().isoformat()}"
ruta.write_text(texto.replace("## [Sin publicar]", nueva), encoding="utf-8")
EOF
```
  `docs/manual_usuario.md`: la sección nueva va **antes** de «## 4. El informe de auditoría» (tras la §3.8, Hoja del proyecto):
```markdown
### 3.9 Moneda, precios de la empresa, índices del BCV y reajuste (UC‑17 y UC‑18)

Desde la versión 0.6.0 cada proyecto tiene **su moneda** (Bs o USD), cada precio dice de dónde sale y
cuánto valor perdió, una empresa puede tener **su lista de precios**, el sistema lee los archivos del
**BCV** que usted descarga y calcula el **reajuste** de la obra ejecutada de dos maneras, lado a lado.
Nada de esto usa internet: el sistema lee lo que usted bajó.

**La moneda del proyecto.** Al crear un proyecto en la barra (**Proyecto**), elija la **Moneda del
proyecto**: Bs o USD. No tiene valor por defecto; sin elegirla, el proyecto no se crea. Una versión se
valora solo con una lista de su moneda: guardar o revalorar con una lista de otra moneda se rechaza y el
mensaje lo dice. En la pestaña **Parámetros** de la hoja verá la moneda del proyecto y el bloque
**Cambiar la moneda**: elija la moneda destino y la tasa del BCV (venta, por defecto, o compra), escriba
por qué se cambia y quién lo hace, y pulse **Convertir la version**. Se crea una **versión nueva**
convertida con la tasa del BCV de hoy (la de fecha valor más reciente que no pase de hoy); la versión
anterior no cambia. Si la última tasa importada tiene más de 7 días, no se convierte nada y el mensaje
lo dice: importe antes la tasa en **Indices del BCV**.

**De dónde sale cada precio.** La pestaña **Precios** de la hoja muestra, por insumo, la moneda y el
precio originales, la fecha del precio, la tasa con su fecha y su fuente, la fuente del precio, si es
**propio** o **heredado** de la lista base (en una lista de empresa) y la **erosión** a hoy: cuánto
valor perdió el precio, en USD, en Bs y en porcentaje. El porcentaje es la fracción del valor que se
perdió (1 − tasa del precio ÷ tasa de hoy), no la erosión en Bs dividida entre el precio. Ejemplo: un
precio de 1 000 Bs del 01/07/2026 (tasa 633,3644) evaluado al 01/10/2026 (tasa 860,18) perdió 0,42 USD,
que son 358,11 Bs, un **26,37 %** (no 35,81 %). Un precio en USD tiene erosión 0: el sistema no tiene un
índice de inflación en dólares y lo declara. Si hay una serie de índices cargada, la **erosión por
índice** va en su propia columna y no se suma a la otra. La columna **Estado** agrega los hallazgos de
R11 y R12 de hoy.

**Índices del BCV (UC‑17, pasos 1 a 3).** En la pantalla **Indices del BCV**:

1. Elija qué archivo es: la **tasa de referencia** (el `.xls` trimestral), el **INPC** (`.xls` mensual)
   o **una serie en CSV canónico**. Súbalo, escriba la dirección de la página del BCV de donde lo bajó
   (tiene que ser de `bcv.org.ve`) y la fecha de descarga, y pulse **Leer**.
2. Lea el **informe previo**: las series, cuántas filas se leyeron, cuántas se rechazaron y por qué
   (fecha repetida, fuera del trimestre, posterior a la descarga, valor no numérico…) y cuántas son
   provisionales. Todavía no se guardó nada.
3. Escriba el **responsable** y pulse **Confirmar la importacion**. El mismo archivo dos veces no
   escribe nada. Un INPC revisado por el BCV entra como una importación nueva: los estudios de reajuste
   ya guardados siguen usando la que citaron.

El **CSV canónico** sirve para el índice de insumos de la construcción (mientras su formato no esté
documentado) o para cualquier serie si el BCV cambia su formato: columnas
`serie,fecha,valor,provisional,fuente`, fechas `AAAA-MM-DD`, punto decimal, `si`/`no` en
`provisional` y la **fuente en cada fila**. Al confirmar, declare el nombre, el organismo, la unidad y la
periodicidad de cada serie.

**Precios de la empresa (UC‑17, pasos 4 y 5).** En la pantalla **Precios de la empresa**:

1. Pulse **Cargar la referencia MaPreX en Bs** (una vez por caso): los 111 precios de julio de 2026 en
   bolívares, con su Ref, contra los que se comparan los de la empresa.
2. Cree la lista: nombre y RIF de la empresa, **lista base** (la que completa los insumos que la empresa
   no cotiza), **moneda** (sin valor por defecto), fecha, fuente y el archivo (CSV o XLSX con las
   columnas `tipo`, `insumo`, `unidad`, `precio` y, opcionales, `fecha`, `fuente`, `referencia`,
   `moneda`, `tasa`, `fecha_tasa`, `fuente_tasa`). **Use punto decimal**: `13288.00`, nunca
   `13.288,00`; una cifra con coma se rechaza con su fila. Los insumos que el catálogo no conoce se
   listan y no entran. La lista de una empresa no es la lista vigente de nadie: solo la usa la versión
   que la elige, y no cambia la valoración de ningún otro proyecto.
3. Revise los **precios vencidos o fuera de rango** a la fecha de evaluación (hoy, por defecto). Sin
   versión, el impacto es por unidad de insumo; en la hoja de una versión es el dinero en su total.

| Regla | Qué marca | Severidad |
|---|---|---|
| **R11** Precio fuera de rango | el precio frente a su referencia MaPreX, los dos llevados a USD con la tasa de cada uno, fuera de −20 % / +30 %; exactamente −20 % o +30 % pasa | ADVERTENCIA por insumo, y **un** INFO que cuenta los insumos sin referencia o sin tasa a su fecha |
| **R12** Precio vencido o sin trazabilidad de tasa | un precio con más de 30 días a la fecha de evaluación (30 pasa), o convertido con una tasa sin fuente | ADVERTENCIA |
| **R12** | un precio convertido con una tasa **sin fecha**: no se puede reproducir | ERROR |

R11 y R12 no son parte de las siete reglas del informe de cada presupuesto (sección 4): se evalúan a una
fecha que usted ve, y volver a evaluar a otra fecha cambia lo que se muestra, nunca lo guardado.

**Reajuste de precios (UC‑18).** Abra el proyecto en la barra y vaya a **Reajuste de precios**:

1. Elija la **versión del contrato**.
2. Declare la **cláusula**: inicio y duración del contrato, desde cuándo corre el primer año,
   periodicidad, mecanismo (escalatoria, comprobación o ambos; con ambos, cuál es el **pagadero** y su
   fuente), estructura (**por partida**: los pesos salen del APU de cada partida; **declarada**: un peso
   por componente, que sumen exactamente 1), el **mes base** de los índices, **R** con su fuente (si el
   contrato no la trae, escriba 0 y dígalo), la fuente de la cláusula y el responsable. En la tabla de
   componentes escriba la serie importada de materiales, equipos y mano de obra.
3. Escriba los **períodos** (desde, hasta, la versión revalorada que sirve de comprobación y, si la hay,
   la excepción declarada) y lo **ejecutado** por período y partida, con su fuente (número y fecha del
   acta o de la valuación).
4. Pulse **Calcular**: ve por período y en total la **escalatoria**, la **comprobación directa**, su
   diferencia y el monto **reconocido**, en la moneda del proyecto y en la otra (con la tasa del cierre
   de cada período; la diferencia se convierte una sola vez). Nada se guarda todavía.
5. Escriba la fuente y el responsable y pulse **Guardar estudio**. Si el último período es un mes que
   aún no cierra, el estudio queda **«parcial al corte»**; al cerrar el mes, calcule otra vez y guárdelo
   eligiendo el parcial que **reemplaza** (una sola vez; el parcial no se borra).
6. **Preparar Excel** y **Descargar Excel**: el libro de la versión del contrato con las hojas
   **Reajuste** y **Ejecutado**.

Lo que el sistema decide solo, y le dice: un período anterior al aniversario de un contrato de más de un
año tiene reajuste 0 con la nota «precios fijos el primer año (art. 134, a cotejar)»; un período que
cruza el aniversario se rechaza (pártalo); si falta el índice de un mes, ese período no se calcula; un
índice provisional se marca; lo ejecutado por encima de lo presupuestado se guarda con aviso y se
reajusta solo hasta lo presupuestado; sin versión revalorada, la comprobación queda «no disponible»; un
proyecto en USD con índices en Bs lleva una ADVERTENCIA; si los reajustes superan el 10 % del monto
original sale una nota marcada INDICIO. Un estudio guardado no cambia aunque después se importe una
revisión de los índices: cita las importaciones que usó.

**Supuestos declarados, todos a cotejar con la Gaceta o con un experto.** El reajuste sigue una
transcripción de la ley, no la Gaceta Oficial; la fórmula `Vo · (Km − 1) · (1 − R)` es un INDICIO. Lo
que el sistema supone, para que usted lo vea y lo pueda discutir:

| # | Supuesto |
|---|---|
| S1‑R1 | La tasa para convertir es la de **venta** del BCV; se puede elegir compra |
| S1‑R2 | Tasa aplicable: la de fecha valor más reciente que no pase de la fecha; con más de 7 días sin tasa no se convierte |
| S1‑R3 | Cambiar la moneda crea una versión nueva convertida; nada se reescribe |
| S1‑R4 | La lista de una empresa no es la vigente de nadie: la usa la versión que la elige |
| S1‑R5 | R11: rango −20 % / +30 % por analogía con la clase 3 de AACE (no es una fuente de rango por insumo) |
| S1‑R6 | R12: un precio vence a los 30 días (supuesto sin fuente) |
| S1‑R7 | R11 y R12 no entran en las siete reglas del informe |
| S1‑R8 | La fórmula escalatoria `Vo · (Km − 1) · (1 − R)` es un INDICIO, a verificar |
| S1‑R9 | Primer año: solo en contratos de más de 12 meses; el período que cruza el aniversario se rechaza; la excepción por equilibrio económico se declara |
| S1‑R10 | El índice de un período es el del mes en que cierra; el mes base se declara |
| S1‑R11 | El reajuste se calcula en la moneda del contrato; USD con índice en Bs da ADVERTENCIA |
| S1‑R12 | Los `.xls` se leen con `xlrd` (extra `bcv`, incluido en la instalación básica) |
| S1‑R13 | Los archivos del BCV de prueba no vienen con el programa: cada empresa descarga los suyos |
| S1‑R14 | R no se aplica a la comprobación directa salvo que la cláusula lo diga |
| S1‑R15 | Las monedas se escriben `Bs` y `USD` |
| S1‑R16 | El desvío de R11 se calcula con una sola división y sin redondear antes de comparar |
| S1‑R17 | Lo ejecutado por encima de lo presupuestado se guarda con aviso y se reajusta hasta lo presupuestado |
| S1‑R18 | Desde la 0.7.0, cada valuación entra entera en el período que contiene su fecha *hasta* |
| S1‑R19 | El porcentaje de erosión es 1 − tasa del precio ÷ tasa de evaluación |
| S1‑R20 | Con «ambos», se reconoce el mecanismo pagadero de la cláusula; sin él, la escalatoria |
| S1‑R21 | El estudio de un mes en curso se guarda «parcial al corte» y se reemplaza una vez al cerrar el mes |

**Recorrido guiado.** En **Inicio**, «Moneda, precios de empresa y reajuste» lo lleva paso a paso por
**Indices del BCV**, **Precios de la empresa**, la **Hoja del proyecto** y **Reajuste de precios**.
```
  En la §4 («El informe de auditoría»), al final:
```markdown
**Reglas de precios (R11 y R12, desde la 0.6.0).** No son parte de las siete: se evalúan sobre la lista
de precios a una fecha de evaluación que se declara (en la hoja, hoy) y su impacto es dinero en el total
de la versión. Están en la sección 3.9.
```
  En la §7 («Problemas frecuentes»), filas nuevas al final de la tabla:
```markdown
| «… con mas de 7 dias naturales sin tasa no se convierte (S1-R2)» al convertir | No hay tasa del BCV importada en los 7 días anteriores: importe el archivo trimestral en **Indices del BCV** y vuelva a convertir |
| «… lleva coma; use punto como separador decimal» al cargar una lista o un CSV | El archivo usa coma decimal: escriba `13288.00`, no `13.288,00` ni `13288,00`. Nada se escribió |
| «… no es una direccion de bcv.org.ve» al leer un archivo del BCV | La dirección declarada no es del BCV: copie la de la página de donde bajó el archivo |
| «Elija la moneda del proyecto (Bs o USD)» al crear un proyecto | La moneda no tiene valor por defecto: elíjala en la barra y vuelva a pulsar **Crear proyecto** |
| «… una version solo se valora con una lista de su moneda (RF-65)» | La lista elegida (o la vigente) está en otra moneda que la versión: cree o elija una lista en la moneda del proyecto, o convierta la versión en **Parámetros** |
| «un parcial se reemplaza una sola vez (S1-R21)» | Ese estudio parcial ya tiene su estudio de cierre: no hace falta otro |
| Un período del reajuste dice «índice faltante: período no calculado» | Falta el índice del mes base o del mes de cierre de alguna serie: impórtelo en **Indices del BCV** y vuelva a calcular |
```
  `docs/manual_tecnico.md`: sección nueva al final del archivo:
```markdown
## 13. Moneda, precios de empresa, BCV y reajuste (Sílice 0.6.0, S1)

Spec: `docs/especificaciones/2026-10-11-silice-s1-moneda-reajuste-design.md`. Tres expedientes de núcleo
(SL‑E1 a SL‑E3, en `docs/bitacora/2026-10-silice-expedientes.md`); ningún contrato de `core/contracts/`
cambió.

**Capas.**

| Paquete | Qué hace |
|---|---|
| `core/models/moneda.py` | Las tablas aditivas de S1, reexportadas en `core.models`: series, importaciones y valores de índices, moneda del proyecto, origen por precio (SL‑E1); lista de empresa (SL‑E2); cláusula, estudio, períodos y ejecutado del reajuste (SL‑E3). Revisiones de Alembic `caso_0002_s1_moneda`, `caso_0003_s1_lista_empresa` y `caso_0004_s1_reajuste` |
| `core/catalog/indices.py` | `registrar_importacion` (idempotente por huella SHA‑256; una revisión es otra importación), `valor_en` (con la importación citada o la más reciente) y `tasa_aplicable` (S1‑R1, S1‑R2) |
| `core/catalog/moneda.py` | `convertir`, `erosion`, `erosion_por_indice` (puras, 28 dígitos y `ROUND_HALF_EVEN` fijados dentro), `TasaDeclarada`, `convertir_lista` |
| `core/catalog/origen.py` | `origenes_efectivos`: **una sola regla de precedencia**: la fila de `precio_origen` y, sin ella, la lista (así abren las bases anteriores) |
| `core/catalog/empresa.py` | `crear_lista_de_empresa`, `crear_lista_de_referencia`, `es_heredado` e `instantanea_de_lista` (R11/R12 de una lista sola) |
| `core/budget/moneda.py` | `moneda_del_proyecto`, `declarar_moneda`, `convertir_version` (versión nueva con motivo `conversion`, por `guardar_presupuesto`) |
| `core/verification/precios.py` | R11 `PrecioFueraDeRango` y R12 `PrecioVencido`: reglas **externas** (como R8–R10), fuera de `REGLAS`; reciben la instantánea con la fecha de evaluación explícita y nunca leen el reloj |
| `core/budget/reajuste.py` | Las funciones puras del reajuste (`calcular_estudio` y sus partes) y `guardar_estudio` / `cargar_estudio` |
| `adapters/bcv/` | `libro.py` convierte `.xls` (`xlrd`, importado dentro de la función) y `.xlsx` en una **cuadrícula neutra**; `tasa.py`, `inpc.py` y `csv_canonico.py` la interpretan; no importa `core` |
| `ui/indices.py`, `ui/precios_empresa.py`, `ui/reajuste.py`, `ui/texto_seguro.py` | Sin Streamlit, sin pandas y sin `ui.caso` (`tests/unit/test_arquitectura_s1.py`) |
| `ui/paginas/indices.py`, `precios_empresa.py`, `reajuste.py` | Abren el caso con `preparar_base` antes de `crear_motor` (están en `PAGINAS_QUE_ABREN_EL_CASO`) |

**Reglas que no se rompen.** Todo monto es `Decimal`; cada división fija su contexto dentro de la
función y se redondea solo al presentar. Una reevaluación de R11/R12 es siempre en memoria: la hoja abre
la versión con `abrir_version(..., fecha_evaluacion=hoy)` y no escribe hallazgos. El texto ajeno (hojas y
etiquetas del BCV, descripciones de una lista importada) se muestra en celdas o con
`ui.texto_seguro.texto_seguro`, nunca con `unsafe_allow_html`. Una página nueva no importa `scripts/` al
cargarse (la referencia MaPreX se importa dentro de la acción).

**Cuando el BCV cambia un formato.** Los formatos verificados viven en `docs/fuentes/bcv_formatos.md`; su
tabla «Formatos para `adapters/bcv/formatos.json`» se copia tal cual al JSON (una clave por fila, con
prefijo `tasa.` o `inpc.`, y su valor JSON) y `test_formatos_json_copia_bcv_formatos_md` compara los
dos. Pasos: abrir el archivo nuevo con Excel o LibreOffice, corregir la tabla, regenerar el JSON, volver a transcribir a mano en
`tests/fixtures/bcv/FUENTE.md` la primera, la última y una hoja del medio, y correr
`uv run pytest tests/unit/adapters -W error`. Mientras tanto, la serie entra por el CSV canónico.

**Reajuste reproducible (RNF‑14).** `guardar_estudio` guarda la cláusula, la tasa de cada cierre, la
versión revalorada usada y, en `periodo_reajuste.importaciones`, la importación de cada índice
(`{"serie@AAAA-MM-DD": id}`). `cargar_estudio` recalcula con esas citas y exige igualdad exacta: una
revisión importada después no lo cambia. Un parcial al corte se reemplaza una sola vez
(`uq_estudio_reemplaza_a`); el reemplazado no se borra.

**Dónde vive cada supuesto (S1‑R1 a S1‑R21, spec S1 §12).** Lado de la tasa: `LADO_POR_DEFECTO`; siete
días: `DIAS_MAXIMOS_SIN_TASA` (`core/catalog/indices.py`). Rango y plazo: `RANGO_INFERIOR`,
`RANGO_SUPERIOR`, `PLAZO_VIGENCIA_DIAS` (`core/catalog/empresa.py`), y por lista en `lista_empresa`.
Monedas: `MONEDAS` (`core/catalog/moneda.py`). Primer año, R, mecanismo pagadero y parcial al corte: la
cláusula y `calcular_estudio` (`core/budget/reajuste.py`), con sus notas en las constantes `MARCA_*`,
`AVISO_USD_BS`, `NOTA_COMISION` y `NOTA_RECONSIDERACION`. Cambiar uno es cambiar esa constante (o la
función pura) y su memoria en `tests/fixtures/memorias/`, con expediente si está en `core/`.

**Oráculos.** Las cuatro memorias a mano de `tests/fixtures/memorias/s1_*.md` y la transcripción a mano
de `tests/fixtures/bcv/FUENTE.md` se versionaron antes que el código que prueban (`S1-MEM`, `S1-FUENTE`
de `scripts/meta_silice.py`). La base de prueba de la 0.6.0 (`tests/fixtures/bases/v0_6_0/`, con
`s1.db`) se generó con el código de la etiqueta `v0.6.0` (`scripts/generar_base_prueba.py`).
```
- [ ] **Paso 4: Correrlas y ver el verde; PR, fusión y etiqueta**
Run: `uv run pytest tests/unit/test_generar_base_prueba.py tests/unit/test_ui_recorridos.py tests/unit/test_ui_app.py tests/unit/test_entorno_silice.py -v -W error` → PASS; `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml`; `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S1-4 --junit reporte-pruebas.xml` → todo OK.
```bash
git add tests/fixtures/caso_s1.py scripts/generar_base_prueba.py ui/recorridos.py pyproject.toml uv.lock CHANGELOG.md docs/manual_usuario.md docs/manual_tecnico.md .github/workflows/ci.yml
git commit -m "chore(release): Silice 0.6.0 con el caso S1 para su base de prueba y su recorrido" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin inc/060-s1-5-cierre
gh pr create --base main --head inc/060-s1-5-cierre --title "S1-5: Silice 0.6.0" --body-file -
gh pr merge <n> --merge
git fetch origin --tags
git tag -a v0.6.0 -m "Silice 0.6.0: S5-1 adelantado y S1 (moneda, precios de empresa, BCV, reajuste)" origin/main
git push origin v0.6.0
```
  (La etiqueta marca el código; la base de prueba se genera **de** ella en el paso siguiente, como la de la 0.5.0 en B. Ver la decisión abierta 1 de `cotejo.md`.)
- [ ] **Paso 5: Base de prueba de la 0.6.0 (rama `inc/060-s1-5-base`)**
```bash
git switch -c inc/060-s1-5-base origin/main
```
Prueba primero:
```python
# tests/integration/test_base_0_6_0.py
"""RV-3, PRU-H15: la base de prueba de la 0.6.0, generada con el codigo de la etiqueta v0.6.0,
abre por `preparar_base` y recarga igual que su ficha (seccion B, tests/fixtures/bases_prueba.py)."""

from __future__ import annotations

from decimal import Decimal as D
from pathlib import Path

import pytest
from sqlalchemy import select

from core import models
from core.budget.reajuste import cargar_estudio
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from tests.fixtures.bases_prueba import copiar_base, diferencias_con_ficha, ficha, nombres


def test_la_ficha_es_de_la_etiqueta_v0_6_0() -> None:
    datos = ficha("0.6.0")
    assert (datos["version"], datos["etiqueta"]) == ("0.6.0", "v0.6.0")
    assert sorted(datos["bases"]) == ["demo.db", "of001.db", "s1.db", "ti001.db"]
    assert {b["revision_alembic"] for b in datos["bases"].values()} == {"caso_0004_s1_reajuste"}


@pytest.mark.parametrize("nombre", nombres("0.6.0"))
def test_cada_base_0_6_0_abre_en_head_y_recarga_su_ficha(tmp_path: Path, nombre: str) -> None:
    ruta = copiar_base("0.6.0", nombre, tmp_path / nombre)
    preparar_base(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert diferencias_con_ficha(ruta, ficha("0.6.0")["bases"][nombre]) == []


def test_el_estudio_de_la_base_s1_recalcula_igual(tmp_path: Path) -> None:
    ruta = copiar_base("0.6.0", "s1.db", tmp_path / "s1.db")
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            estudio = sesion.scalars(select(models.EstudioReajuste)).one()
            assert cargar_estudio(sesion, estudio.id).resultado.total_escalatoria == D("15300")
    finally:
        motor.dispose()
```
Run: `uv run pytest tests/integration/test_base_0_6_0.py -v -W error` → error de colección `FileNotFoundError: …/tests/fixtures/bases/v0_6_0/ficha.json`.
```bash
git add tests/integration/test_base_0_6_0.py
git commit -m "test(migraciones): base de prueba de v0.6.0 contra su ficha en rojo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Generación (procedimiento de B, Tarea 2, con la etiqueta nueva), en Git Bash desde la raíz del worktree:
```bash
REPO="$(pwd)"
V060="${TMPDIR:-/tmp}/silice-v0.6.0"
rm -rf "$V060" && mkdir -p "$V060"
git archive v0.6.0 | tar -x -C "$V060"
(
  cd "$V060" && unset VIRTUAL_ENV \
  && export UV_PROJECT_ENVIRONMENT="$V060/.venv" \
  && uv sync --frozen --all-extras \
  && uv run --frozen python scripts/generar_base_prueba.py \
       --salida "$REPO/tests/fixtures/bases/v0_6_0" --version 0.6.0 --etiqueta v0.6.0 \
       --commit "$(git -C "$REPO" rev-parse 'v0.6.0^{commit}')"
)
```
(`scripts/generar_base_prueba.py` ya está en el árbol de la etiqueta: no se copia.) `.github/workflows/ci.yml`, paso «Meta de Silice»: `--hasta S1-5`.
Run: `uv run pytest tests/integration/test_base_0_6_0.py tests/integration/test_base_prueba_v0_5_0.py -v -W error` → PASS; `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml`; `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S1-5 --junit reporte-pruebas.xml` → todas las filas en OK (incluida `S1-BASE-060`).
```bash
git add tests/fixtures/bases/v0_6_0/demo.db tests/fixtures/bases/v0_6_0/of001.db tests/fixtures/bases/v0_6_0/ti001.db tests/fixtures/bases/v0_6_0/s1.db tests/fixtures/bases/v0_6_0/ficha.json .github/workflows/ci.yml docs/bitacora/2026-10-silice-060.md
git commit -m "test(migraciones): bases de prueba de v0.6.0 y su ficha generadas con el codigo de la etiqueta" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin inc/060-s1-5-base
gh pr create --base main --head inc/060-s1-5-base --title "S1-5: base de prueba de v0.6.0" --body-file -
```
Fusionar con `gh pr merge <n> --merge` con la CI verde: con esa fusión se cruza GS1.

---

## Compuerta GS1 (etiqueta `v0.6.0`; se cruza al fusionar `inc/060-s1-5-base`)

1. `uv run python scripts/meta_silice.py --version 0.6.0 --hasta S1-5 --junit reporte-pruebas.xml` → `RESULTADO` con todas las filas en OK: C1 (los requisitos de S5‑1 y los once de S1 por presencia), C2 (cero omitidas), C3 (cada `ParTDD` de T0, S5‑1 y S1: SL‑E1, SL‑E2, SL‑E3 y cada intérprete del BCV), C4 (`core/contracts/` intacto desde `v0.5.0`), C5 (bloque `REGRESION` de `scripts/meta_silice.py`: sus `ARCHIVOS_REGRESION` sin cambios desde `v0.5.0` y sus pruebas en verde), C6 (cifra de RNF‑11), C7 (guardia de red), `S1-MEM`, `S1-FUENTE` y `S1-BASE-060`.
2. CI verde en Linux y Windows con el extra `bcv` instalado (ninguna prueba omitida por `xlrd`), `HF_HUB_OFFLINE=1`, `-W error`, y el paso de la meta en `--hasta S1-5`.
3. **Bloque de regresión literal**: el de A4 (`REGRESION`), sin listas propias: cinco APU ± 0,01 (`tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base` y `tests/unit/test_linea_base.py`); 7 de 7 (`tests/integration/test_auditoria_7_de_7.py`); R4 de 3/4 pulg (`tests/unit/test_verification.py::test_r4_marca_3_4_pulg_y_no_marca_pvc`); TI‑001 total, PU y PE 28 586,76 USD Día 6 (`tests/unit/test_caso_ti001.py`: `::test_total_y_cierre_de_la_curva`, `::test_precios_unitarios`, `::test_punto_de_equilibrio`); dos huellas de RNF‑04 (`tests/unit/test_huellas_rnf04.py`); cuatro hojas (`tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas` y `tests/integration/test_composicion_extremo_a_extremo.py::test_exportar_excel_escribe_las_cuatro_hojas_con_la_modalidad`).
4. Prueba de deriva RNF‑20 de B en verde con las revisiones `caso_0002_s1_moneda`, `caso_0003_s1_lista_empresa` y `caso_0004_s1_reajuste`; las bases de `tests/fixtures/bases/v0_5_0/` y `v0_6_0/` abren por `preparar_base` y recargan igual que su ficha.
5. `uv run python scripts/guardia_nucleo.py --base v0.5.0` en 0; `uv run ruff check .`.
6. Aprobación de los cuatro encargos (requisitos, arquitectura, pruebas y calidad, verificador de hechos) y aval del tutor de SL‑E1, SL‑E2 y SL‑E3; compuerta anotada en `docs/bitacora/2026-10-silice-060.md` con la tabla literal de la meta.

## Foco de revisión

1. **Archivo BCV con una hoja nueva o renombrada:** una hoja sin «Fecha Valor» se rechaza y se reporta sin tumbar el archivo; una renombrada vale por su contenido → `tests/unit/adapters/test_bcv_tasa.py::test_hoja_nueva_o_renombrada_no_tumba_el_archivo` (Tarea 6).
2. **Día sin tasa > 7 días:** R11 cuenta el precio como no contrastable y R12 sale con impacto `None` explicándolo, sin excepción → `tests/unit/test_reglas_precios.py::test_dia_sin_tasa_no_revienta` (Tarea 8); la conversión desde la hoja lo dice sin escribir → `tests/integration/test_hoja_moneda.py::test_sin_tasa_en_7_dias_la_hoja_lo_dice_y_no_escribe` (Tarea 10).
3. **Moneda cambiada con versiones previas:** restaurar, editar o revalorar la versión vieja en la moneda anterior se rechaza → `tests/integration/test_conversion_version.py::test_moneda_cambiada_con_versiones_previas_no_se_restauran_en_la_vieja` (Tarea 5).
4. **Cifras con coma decimal en la lista importada:** `13.288,00` o `1,5` se rechazan con fila y «use punto» → `tests/integration/test_lista_empresa.py::test_coma_decimal_se_rechaza_con_fila_y_motivo` (Tarea 7).
5. **Insumo sin precio en una de las dos monedas:** valorar con la lista de empresa en Bs una partida cuyo insumo la base no trae da `CatalogoIncompleto` que nombra la lista → `tests/integration/test_lista_empresa.py::test_insumo_sin_precio_en_la_moneda_de_la_lista_no_valora` (Tarea 7).

## Discrepancias encontradas

1. **API de `meta_silice.py` (sección A) y helpers de las secciones A y B** — *resuelta en el cotejo.* La parte S1 es `scripts/meta_silice_s1.py` con `PARTE = Parte(...)` (requisitos, `ParTDD` y `Comprobacion` de A4; sin editar `meta_silice.py`); `imports_de_ejecucion` → `tests.fixtures.arquitectura.importaciones` (B); `tests.fixtures.bases` → `tests.fixtures.bases_prueba` con `copiar_base(version, nombre, destino)` y la ficha por base de B; `scripts/base_de_prueba.py --version` → `scripts/generar_base_prueba.py --salida … --version … --etiqueta … --commit …` (B) corrido desde `git archive v0.6.0`; `preparar_base(ruta)` es compatible con la firma de B. `down_revision = "caso_0001_base_0_5_0"` confirmado.
2. **Archivo de expedientes:** el spec (§11) dice `docs/bitacora/2026-10-silice-s1-expedientes.md`; INSTRUCCIONES fija `docs/bitacora/2026-10-silice-expedientes.md`. Se siguió INSTRUCCIONES — *resuelta en el cotejo* (lo crea la Tarea 4; la bitácora de la versión es `docs/bitacora/2026-10-silice-060.md`, de A1, en lugar de `2026-10-silice.md`).
3. **Nombres de rama:** el spec (§10) usa `inc/silice-s1-<fase>-nucleo`/`-ui`; el encargo fija `inc/060-s1-<n>-nucleo`. *Resuelta en el cotejo:* todas las ramas siguen `inc/060-<fase>-<algo>`; el adaptador pasa de `inc/silice-s1-bcv` a `inc/060-s1-2-bcv` y el cierre se parte en `inc/060-s1-5-cierre` e `inc/060-s1-5-base`.
4. **Alcance `referencia`:** S1 §6.2 carga la lista MaPreX en Bs como lista, pero solo excluye `empresa` de `lista_vigente`; cargada como global, una lista Bs del 09/07/2026 secuestraría la valoración de todo proyecto posterior (TI‑001 incluido). Se agrega `ALCANCE_REFERENCIA` y `ALCANCES_FUERA_DE_VIGENTE` (dentro de SL‑E2, declarado en su expediente). — *Resuelta en el cotejo:* no cruza secciones; la cubre el expediente o la prueba de su tarea.
5. **`instantanea_precios`:** el spec la ubica en `core/catalog/origen.py`, pero necesita las composiciones congeladas, que solo `core/budget/instantanea.py` lee, y `core/catalog` no importa `core/budget`. Se parte en `core.catalog.empresa.instantanea_de_lista` (lista sola, impacto por unidad) y `core.budget.instantanea.instantanea_precios` (misma firma del spec). La erosión llega precalculada en `PrecioAuditado` para que `core/verification/precios.py` importe solo contratos y motor (S1 §4.2). — *Resuelta en el cotejo:* no cruza secciones; la cubre el expediente o la prueba de su tarea.
6. **Moneda por precio en la lista de empresa:** RF‑67 pide «fecha, moneda y fuente por precio»; UC‑17 4 solo nombra `fecha`, `fuente`, `referencia`. El lector acepta además `moneda`, `tasa`, `fecha_tasa`, `fuente_tasa` (opcionales), que es el único camino real a los casos «tasa sin fecha/sin fuente» de R12. — *Resuelta en el cotejo:* no cruza secciones; la cubre el expediente o la prueba de su tarea.
7. **Propio/heredado** no tiene columna en S1 §5.2; se deduce comparando el origen efectivo con el de la base (`es_heredado`). — *Resuelta en el cotejo:* no cruza secciones; la cubre el expediente o la prueba de su tarea.
8. **Reevaluación al abrir:** para no mover pruebas existentes de `abrir_version`, R11/R12 entran solo con `fecha_evaluacion` explícita (la pantalla pasa hoy), coherente con M §3.3. — *Resuelta en el cotejo:* no cruza secciones; la cubre el expediente o la prueba de su tarea.
9. **INPC:** antecedentes §6 cita `4_5_1.xls`, que publica variaciones; la escalatoria necesita niveles. La Tarea 3 elige y documenta el archivo de niveles; los formatos no verificados (letra del trimestre, encabezados del INPC) viven en `adapters/bcv/formatos.json`, copiado de `bcv_formatos.md`, porque el spec los deja para S1‑0. Se declara como supuesto que la fecha valor puede caer hasta 7 días después del fin del trimestre (la última hoja del 3T‑2026 vale el 01‑10‑2026). — *Resuelta en el cotejo:* no cruza secciones; la cubre el expediente o la prueba de su tarea.
10. **Índice de insumos de la construcción:** entra por el CSV canónico (S1 §7.3, UC‑17 2f); `insumos_construccion.py` no se construye salvo que la Tarea 3 documente su formato (orden de caída de S1 §10). — *Resuelta en el cotejo:* no cruza secciones; la cubre el expediente o la prueba de su tarea.
11. **Pantallas:** el encargo dice «en la hoja»; el spec §4.2 fija páginas propias (`indices`, `precios_empresa`, `reajuste`). Se siguió el spec; la hoja gana moneda (Parámetros) y origen/erosión/R11‑R12 (Precios). `test_ui_app.py` cambia su conteo de pantallas (no es prueba de regresión). — *Resuelta en el cotejo:* manda el spec sobre el encargo.
12. **`huella_contenido`** (RV‑9) no existe hasta S3: la prueba de «reevaluar no reescribe» compara las filas de `hallazgo`; la parte de la huella la agrega S3. — *Resuelta en el cotejo:* no cruza secciones; la cubre el expediente o la prueba de su tarea.
13. **Bloque de regresión de la compuerta.** La lista propia de C omitía `test_composicion_extremo_a_extremo.py::test_exportar_excel_escribe_las_cuatro_hojas_con_la_modalidad` y no citaba nodeids. *Resuelta en el cotejo:* GS1 usa el `REGRESION`/`ARCHIVOS_REGRESION` de A4 (C5 de la meta).
14. **Páginas nuevas y la guardia de B.** `test_la_lista_de_paginas_que_abren_el_caso_esta_completa` (B, Tarea 6) falla con cualquier página que llame a `crear_motor` fuera de `PAGINAS_QUE_ABREN_EL_CASO`. *Resuelta en el cotejo:* las Tareas 9 y 13 agregan `indices`, `precios_empresa` y `reajuste` a esa tupla y abren el caso con `_motor_del_caso()` (`preparar_base` antes de `crear_motor`).
15. **Base de prueba de la 0.6.0 y la etiqueta.** RV‑3 pide la base «con el código de su etiqueta», pero GS1 exige la base antes de etiquetar. *Abierta (decisión 1 de `cotejo.md`):* por defecto se etiqueta `v0.6.0` al fusionar el cierre y la base se genera de la etiqueta en `inc/060-s1-5-base`, con cuya fusión se cruza GS1.
16. **`S1-MEM` antes del código.** `_ordenar_memoria` de `meta_sf` da `None` cuando el código aún no existe y `evaluar_s2_memorias` lo lee como «sin versionar» (FALLA en S1‑0). *Resuelta en el cotejo:* `_orden_memoria` de `meta_silice_s1.py` da `True` si la memoria está versionada y su código todavía no existe.
17. **Pasos en prosa sin código.** Quedan descritos en prosa, sin bloque de código: Tarea 6 (`adapters/bcv/inpc.py`, `csv_canonico.py`, `formatos.py` y las pruebas `test_bcv_inpc.py`, `test_bcv_csv.py`); Tarea 9 (`ui/precios_empresa.py`, las dos páginas y `test_ui_precios_empresa.py`); Tarea 10 (cambios de `abrir_version`, `precios_de_version`, páginas y la prueba nueva de `test_ui_proyectos.py`); Tarea 12 (modelos, `caso_0004_s1_reajuste.py`, `guardar_estudio`, `cargar_estudio`); Tarea 13 (`ui/reajuste.py` y su página); Tarea 14 (manuales). Cada uno tiene firmas e interfaces fijadas, pero el formato del plan pide código. *Resuelta (2026‑10‑11):* cada uno de esos pasos lleva ahora su bloque de código real, con las firmas de las Interfaces y de `cotejo.md`: Tarea 6 (`inpc.py`, `csv_canonico.py`, `formatos.py`, el generador de `formatos.json`, `__init__.py` y las pruebas `test_bcv_inpc.py` y `test_bcv_csv.py`), Tarea 9 (`ui/precios_empresa.py`, las dos páginas, `ui/app.py` y la prueba con los Δ por unidad de la memoria), Tarea 10 (cada cambio de `ui/hoja.py`, de `ui/paginas/hoja.py`, `ui/proyectos.py` y `ui/barra.py`, y sus pruebas), Tarea 12 (los cinco modelos, `caso_0004_s1_reajuste.py`, `guardar_estudio`, `cargar_estudio`), Tarea 13 (`ui/reajuste.py`, su página y el registro en el marco) y Tarea 14 (el texto de las secciones nuevas de los dos manuales, `CONSTRUCTORES`, versión y `CHANGELOG.md`). También se pasaron a código los restos en prosa de las Tareas 4, 5, 7 y 8 (ver 25). Las decisiones de detalle que pidió la redacción van en 18 a 27.
18. **Conteos de pantallas fuera de la lista de archivos.** `tests/unit/test_ui_importable.py` fija once páginas (`len(MODULOS_SIN_PAGINA) + 11`) y `tests/unit/test_ui_app.py::CASOS_DE_USO` exige el caso de uso de cada página que lo declara; ninguna de las dos estaba en las Tareas 9 y 13. *Resuelta:* las dos tareas los actualizan (13 y 14 páginas; `ui.texto_seguro`, `ui.indices`, `ui.precios_empresa` y `ui.reajuste` entran en `MODULOS_SIN_PAGINA`; `UC-17` y `UC-18` en `CASOS_DE_USO`).
19. **Moneda obligatoria al crear desde la barra.** La enmienda de UC‑01 pide elegir la moneda «sin valor por defecto en la interfaz». *Resuelta (Tarea 10):* la barra no crea el proyecto sin moneda (`MENSAJE_SIN_MONEDA`); `tests/unit/test_ui_barra.py::_crear` elige `USD` y se agrega la prueba del rechazo. `crear_proyecto_nuevo(ruta, nombre)` sin moneda (API, scripts, pruebas existentes) sigue sin declarar ninguna, y el proyecto vale USD como hoy. En la 0.6.0 no hay cuentas: la fila de `moneda_proyecto` lleva `RESPONSABLE_DE_LA_INTERFAZ`.
20. **R11/R12 en el borrador de la hoja.** Con `Borrador.reglas_extra` la hoja abierta hoy audita también R11 y R12 (S1 §4.3); `tests/unit/test_ui_hoja.py::test_la_pestana_auditoria_lista_los_hallazgos_con_su_origen` pasa de «solo R8, 33 filas» a «R8 más R11/R12, 33 de R8» (no es prueba de regresión). Dos efectos que se declaran: `reglas_extra` va con `compare=False` (no cuenta como cambio ni dispara «cambios sin guardar»), y una versión guardada desde la hoja emite con su informe los R11/R12 de esa evaluación, que luego se conservan al recargar como toda regla externa (SF‑E1, S1 §4.3); su instantánea de precios es la de la versión abierta hasta reabrir. *Resuelta;* si se prefiere que guardar no emita R11/R12, `guardar_version` pasa `replace(borrador, reglas_extra=())` a `elaborar_borrador` (una línea).
21. **`calcular` sin SAVEPOINT.** La prosa de la Tarea 13 decía `sesion.begin_nested()`. Con pysqlite, SAVEPOINT necesita los eventos `connect`/`begin` que `core.catalog.crear_motor` no instala (documentación de SQLAlchemy, «Serializable isolation / Savepoints»). *Resuelta:* `calcular` usa el mismo `guardar_estudio` y deshace la transacción **entera** en un `finally`; se llama con una sesión sin cambios pendientes (la página abre una por acción y la prueba confirma la siembra antes).
22. **Forma de `FUENTE.md` y de `bcv_formatos.md`.** La Tarea 3 no fijaba cómo se escribe el mes y la marca del INPC ni la forma de la tabla de formatos que leen las pruebas de la Tarea 6. *Resuelta:* sus Interfaces fijan «Mes» en `AAAA-MM`, «Provisional» `sí`/`no`, las transcripciones bajo `### Transcripción` y la tabla `| Clave | Valor (JSON) |`; `adapters/bcv/formatos.json` se **genera** de esa tabla (no se copia a mano).
23. **`FormatoMensual` en `formatos.py`.** El commit de la tasa lleva `formatos.py`; si `FormatoMensual` viviera en `inpc.py`, ese commit arrastraría el intérprete del INPC antes de su prueba (C3 de la meta) o quedaría roto. *Resuelta:* `FormatoMensual` vive en `adapters/bcv/formatos.py` e `inpc.py` lo importa; el nombre y los campos son los de las Interfaces.
24. **Funciones de apoyo de las pantallas.** Además de las firmas fijadas: `ui.precios_empresa.listas_base`, `listas_de_empresa` y `COLUMNAS_HALLAZGOS`; `ui.reajuste.parciales_por_reemplazar`, `COLUMNAS_EJECUTADO`, `NO_DISPONIBLE`; `ui.hoja.texto_propio`; `ui.proyectos.MONEDAS_DEL_PROYECTO` y `RESPONSABLE_DE_LA_INTERFAZ`; `ui.barra.CLAVE_MONEDA_NUEVA` y `MENSAJE_SIN_MONEDA`. Ninguna cambia una firma de `cotejo.md`. `cargar_referencia_maprex` no duplica una referencia ya cargada (lo dice y no escribe). *Resuelta.*
25. **Restos en prosa de las Tareas 4, 5, 7 y 8.** Pasados a código con las firmas fijadas: reexportaciones de `core/models/__init__.py`; en `origen.py`, los campos nuevos de `OrigenPrecio`, `origen_de_precios` con `origenes_efectivos` y la copia del origen efectivo de cada precio no cotizado en `crear_lista_de_proyecto` (incluido el de respaldo de la lista, para que la copia conserve la fuente de la base y no tome la de la lista de proyecto); `composiciones_revaloradas(..., precio_sin_insumo=None)`; el rechazo temprano de `actualizar_precios`; `MOTIVOS_VERSION`, `OBJETOS` y exportaciones; constantes de alcance, `lista_vigente`, `ListaEmpresa`, `caso_0003_s1_lista_empresa.py` y el lector con `COLUMNAS_OPCIONALES`; `instantanea_de_lista` e `instantanea_precios`. Esta última **omite** la partida cuya composición ya no se puede reconstruir del catálogo (la hoja la abre en solo lectura) en lugar de impedir abrir la versión. *Resuelta.*
26. **La lista sola no da el conjunto exacto de la memoria.** `s1_precios_empresa.md` fija el conjunto exacto **de la versión** (Tarea 8). La lista sola trae además un R12 por cada precio heredado de MaPreX con más de 30 días. *Resuelta:* `tests/unit/test_ui_precios_empresa.py` exige que estén, una vez cada una, las siete filas de la memoria con su «Δ por unidad» presentado (1057.53, 11328.78, 108.15, 1622.25, 0.00 y las dos sin impacto), no el conjunto exacto.
27. **Líneas de más de 100 caracteres en bloques que ya estaban** (unas cincuenta, en las Tareas 3 a 8 y 11 a 13: pruebas, `libro.py`, `tasa.py`, `precios.py`, `reajuste.py`, fixtures). `ruff check` las marca (E501, `line-length = 100`). Los bloques nuevos de esta redacción caben en 100. *Abierta (formato, no diseño):* al ejecutar cada tarea, partirlas a mano o con `uv run ruff format <archivo nuevo>` (nunca `ruff format .`) antes del commit.

---

# Anexo: cotejo de interfaces entre secciones


Revisión de coherencia del 2026‑10‑11 sobre `A-transversal.md` (T0, 5 tareas), `B-s5-1-alembic.md` (S5‑1, 7 tareas)
y `C-s1.md` (S1, 14 tareas). Regla aplicada: cuando dos secciones discrepaban, ganó la que **produce** (A antes que B
antes que C) y se ajustó a la que consume. Los tres archivos ya están editados; cada uno cierra con su sección
«Discrepancias encontradas», donde cada entrada dice si quedó resuelta en el cotejo o abierta.

## 1. Orden y ramas

| Orden | Rama | Sección y tarea | Sale de | Condición para abrirla |
|---|---|---|---|---|
| 1 | `inc/nombre-silice` (ya existe; worktree `.worktrees/nombre`) | A1 renombre, `config.toml`, `LICENSE` | `origin/main` (ff) | — |
| 2 | `inc/060-dependencias` | A2 dependencias (`alembic` en la base, `xlrd` en `bcv`) | `origin/main` | A1 fusionada |
| 3 | `inc/060-guardia-red` | A3 guardia de red y modelo sin red | `origin/main` | A2 fusionada |
| 4 | `inc/060-meta` | A4 `scripts/meta_silice.py` | `origin/main` | A3 fusionada |
| libre | `inc/060-enmienda-normas` | A5 enmienda de NORMAS §3 | `origin/main` | ninguna |
| 5 | `inc/060-s5-1-alembic` | B, tareas 1–7 (un solo PR, GS5‑1) | `origin/main` | A1–A4 fusionadas |
| 6 | `inc/060-s1-0-docs` | C, tareas 1–3 (GS1‑0) | `origin/main` | B fusionada |
| 7 | `inc/060-s1-1-nucleo` | C, tareas 4–5 (SL‑E1, GS1‑1) | `origin/main` | S1‑0 fusionada |
| 7′ | `inc/060-s1-2-bcv` (paralela) | C, tarea 6 (GS1‑2) | `origin/main` sin núcleo pendiente | S1‑0 fusionada |
| 8 | `inc/060-s1-3-nucleo` | C, tareas 7–8 (SL‑E2) | `origin/main` | S1‑1 fusionada |
| 9 | `inc/060-s1-3-ui` | C, tareas 9–10 (GS1‑3) | `origin/main` | S1‑3 núcleo y S1‑2 fusionadas |
| 10 | `inc/060-s1-4-nucleo` | C, tareas 11–12 (SL‑E3) | `origin/main` | S1‑3 ui fusionada |
| 11 | `inc/060-s1-4-ui` | C, tarea 13 (GS1‑4) | `origin/main` | S1‑4 núcleo fusionada |
| 12 | `inc/060-s1-5-cierre` | C, tarea 14, pasos 1–4 (versión 0.6.0) → etiqueta `v0.6.0` | `origin/main` | todo S1 fusionado |
| 13 | `inc/060-s1-5-base` | C, tarea 14, paso 5 (base de prueba desde `v0.6.0`; cruza GS1) | `origin/main` en `v0.6.0` | etiqueta puesta |

Todas las fusiones con `gh pr merge <n> --merge` (C3 de la meta lee el orden prueba → implementación). El paso «Meta de
Silice» de la CI sube `--hasta` en el PR que cruza cada compuerta: `T0` (A4) → `S5-1` (B) → `S1-0` … `S1-5` (C).

## 2. Interfaces unificadas

| Nombre final | Produce | Consumen |
|---|---|---|
| `ui.entorno`: `VARIABLE_CASO = "SILICE_CASO"`, `VARIABLE_MODO_ENTREGA = "SILICE_MODO_ENTREGA"`, `ALIAS_ANTERIORES` (`ARENIA_*`), `ULTIMA_VERSION_CON_ALIAS = "0.6.0"`, `leer_variable(entorno, nombre) -> str \| None`; `ui.caso.VARIABLE_RUTA_CASO = VARIABLE_CASO`; claves `silice_*` | A1 | B T6 (`ui/caso.py` reescrito conserva todo), B T7 (manual), C T14 (versión 0.6.0 = último alias) |
| Bitácora de la versión `docs/bitacora/2026-10-silice-060.md` | A1 | A2–A4, B (compuerta), C T3, T14 |
| `tests/conftest.py`: `_sin_variables_de_silice_del_entorno` (autouse) y `STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=full` | A1 | B T1 (inserta sus fixtures después) |
| `tests/conftest.py`: `_guardia_de_red` (sesión, autouse, al final), `DESTINOS_PERMITIDOS`, `ConexionSalienteBloqueada`, `INTENTOS_BLOQUEADOS`, `destino_permitido`, `veredicto_de_la_guardia`, `HF_HUB_OFFLINE=1` | A3 | A4 (C7), B, C (suite sin red) |
| `tests/conftest.py`: `RUTA_INSTALACION_REAL`, `_instalacion_real_intacta` (sesión), `_datos_de_silice_temporales` (autouse, `SILICE_DATOS` temporal) | B T1 | B T4–T6, C (toda prueba que prepare un caso) |
| Dependencias: base `alembic>=1.20`, `argon2-cffi>=25.1`, `cryptography>=44`; extra `bcv = ["xlrd>=2.0"]`; `DUENOS_DE_TERCEROS` (`alembic` → `migraciones/`, `operacion/`; `xlrd` → `adapters/bcv/`), `DIFERIDOS` (`xlrd` dentro de una función) | A2 | B (antes de abrir su rama), C T6 (`adapters/bcv/libro.py::_xls`) |
| `scripts/meta_silice.py`: `FASES["0.6.0"] = ("T0", "S5-1", "S1-0", …, "S1-5")`, `Parte(nombre, requisitos, pares_tdd, cifras, comprobaciones)`, `ParTDD(prueba, implementacion, fase)`, `Comprobacion(codigo, titulo, fase, evaluar: Callable[[Contexto], tuple[Estado, str]])`, `Contexto`, `partes()` (descubre `scripts/meta_silice_<parte>.py` con `PARTE`), `validar_partes`, `orden_de_par`, `_primer_commit` | A4 | B T7, C T1 (ninguno edita `meta_silice.py`) |
| `REGRESION`, `ARCHIVOS_REGRESION` (8 archivos), `BASE_REGRESION = "v0.5.0"` (C5) | A4 | compuertas GS5‑1 y GS1 (sin listas propias) |
| `scripts/meta_silice_s5.py`: `PARTE` (`requisitos={"S5-1": ("RF-96", "RNF-20")}`, `PARES_S5` ×8, comprobación `S5-M3`), `BASES_050`, `evaluar_base_050(carpeta)` | B T7 | meta (A4) |
| `scripts/meta_silice_s1.py`: `PARTE` (`requisitos={"S1-0": REQUISITOS_S1}`, `PARES_S1` ×11 en `S1-0`…`S1-4`, `S1-MEM`, `S1-FUENTE` en `S1-0`, `S1-BASE-060` en `S1-5`), `evaluar_fuente_bcv`, `evaluar_base_060` | C T1 | meta (A4) |
| `tests/fixtures/arquitectura.py`: `RAIZ`, `archivos(paquete)`, `ruta(archivo)`, `importaciones(archivo) -> set[str]`, `llamadas(archivo, nombre) -> list[int]` | B T1 | B T1/T6 (`test_arquitectura_s5.py`), C T9 (`test_arquitectura_s1.py`; antes `imports_de_ejecucion`) |
| `tests/unit/test_arquitectura_s5.py::PAGINAS_QUE_ABREN_EL_CASO` (toda página con `crear_motor` llama a `preparar_base`) | B T6 | C T9 (+`indices`, `precios_empresa`), C T13 (+`reajuste`) con `_motor_del_caso()` |
| `operacion.config`: `VARIABLE_DATOS = "SILICE_DATOS"`, `VARIABLE_INSTALACION = "SILICE_INSTALACION"`, `VARIABLE_RESPALDOS = "SILICE_RESPALDOS"`, `RAIZ`, `DATOS_DESARROLLO`, `BASE_ANTERIOR`, `NOMBRE_INSTALACION = "instalacion.db"`, `CASO_POR_DEFECTO = "silice.db"`, `carpeta_datos(entorno=None)`, `carpeta_casos(entorno=None)`, `ruta_instalacion(entorno=None)`, `carpeta_respaldos(entorno=None)`, `ruta_caso_por_defecto(entorno=None)` (ninguna crea carpetas) | B T1 | B T4–T6 (`ui/caso.py`, `api/dependencias.py`) |
| `operacion.base_datos.preparar_base(ruta, destino=Destino.CASO, *, entorno=None) -> ResultadoPreparacion(ruta, destino, revision_origen, revision_destino, juego, nueva)`; `Destino` (`CASO`, `INSTALACION`), `revision_head(destino)`, `leer_estado(ruta) -> EstadoBase`, `ErrorDeBase` y subclases | B T3/T5 | B T6, C T4 (`test_migracion_s1.py`), C T9/T13 (páginas), C T14 (`test_base_0_6_0.py`), `scripts/generar_base_prueba.py` |
| Destino `migraciones/caso/` con `script.py.mako`; revisión base `caso_0001_base_0_5_0` (`down_revision = None`) en `migraciones/caso/versions/caso_0001_base_0_5_0.py` | B T1/T3 | C T4, T7, T12 |
| Regla de una revisión nueva: archivo `migraciones/caso/versions/<revision>.py` escrito a mano con la plantilla; `down_revision` = salida de `uv run python -c "from operacion.base_datos import Destino, revision_head; print(revision_head(Destino.CASO))"`; `op.create_table`, nunca `stamp`, `downgrade()` real; la valida `tests/integration/test_migraciones.py` sin cambios | B T7 (manual técnico §10.5) | C: `caso_0002_s1_moneda` → `caso_0003_s1_lista_empresa` → `caso_0004_s1_reajuste` |
| Base de prueba 0.5.0: `tests/fixtures/bases/v0_5_0/{demo,of001,ti001}.db` + `ficha.json` (`version`, `etiqueta`, `commit`, `bases.<nombre>.{revision_alembic, sha256_base, filas_por_tabla, presupuestos}`) | B T2 | B T3–T6, C T4 |
| `tests/fixtures/bases_prueba.py`: `CARPETA`, `carpeta_version(version)`, `ficha(version)`, `nombres(version)`, `copiar_base(version, nombre, destino)`, `diferencias_con_ficha(ruta, esperado)`, `crear_base_futura(ruta)` | B T2 | B T3–T6, C T4, C T14 (antes `tests.fixtures.bases`) |
| `scripts/generar_base_prueba.py`: `CONSTRUCTORES` (+`"s1.db": plantilla_s1` desde la 0.6.0), `main(["--salida", "--version", "--etiqueta", "--commit"])`, corrido desde `git archive v<X>` | B T2 | C T14 (antes `scripts/base_de_prueba.py --version`) |
| Base de prueba 0.6.0: `tests/fixtures/bases/v0_6_0/{demo,of001,ti001,s1}.db` + `ficha.json` | C T14 | meta (`S1-BASE-060`), versiones siguientes |
| `CHANGELOG.md` con `## [Sin publicar]` (líneas de T0 y de S5‑1) | B T7 | C T1, C T14 (`[0.6.0]`) |
| `docs/bitacora/2026-10-silice-expedientes.md` | C T4 (SL‑E1) | C T7, T11 |
| `ui/texto_seguro.py::texto_seguro(texto: str) -> str` | C T9 (ni A ni B lo crean) | C T9, T10, T13 |

## 3. Decisiones abiertas para Eugenio (cada una con su valor por defecto)

1. **Etiqueta antes que la base de prueba de la 0.6.0.** RV‑3 pide generar la base con el código de la etiqueta, pero
   GS1 exige la base antes de etiquetar. *Por defecto:* se etiqueta `v0.6.0` al fusionar `inc/060-s1-5-cierre` y la base
   se genera de la etiqueta en `inc/060-s1-5-base`, con cuya fusión se cruza GS1 (C, Tarea 14).
2. **Enmienda de NORMAS §3** (A5). *Por defecto:* queda `PROPUESTA`; NORMAS no cambia y se siguen las ramas cortas
   `inc/060-*` en el worktree `.worktrees/060`. Si la ratifica, el PR aplica la sección 2 y limpia los nueve worktrees.
3. **Fallo de una migración** (B §Discrepancias 1). El spec dice «se restaura el juego»; RF‑96 (c) exige la misma huella.
   *Por defecto:* se migra una copia de trabajo y el original nunca se toca; el juego queda para restaurar a mano.
4. **La API ante una base vieja** (B §Discrepancias 7). El spec dice 503 si no está en `head`. *Por defecto:* la API
   migra con respaldo, como la interfaz, y responde 503 solo si `preparar_base` no puede.
5. **Scripts de siembra** (B §Discrepancias 5). El spec los pasa a `preparar_base` en S5‑1. *Por defecto:* siguen con
   `create_all` y sus bases se adoptan al abrirse; el disparador para cambiarlos queda en el manual técnico §10.5.
6. **Revisión base** (B §Discrepancias 11). El spec la genera con la autogeneración de Alembic. *Por defecto:* se
   congela el DDL literal de `sqlite_master` de la base de prueba de `v0.5.0`, verificado contra las tres bases.
7. **`ifctester` y la GPLv3 de `bcf-client`** (A §Discrepancias 4). *Por defecto:* extra propio `ifc`, fuera de `civil`
   y del instalador hasta que S3‑0 resuelva la licencia.

Tarea manual (no decisión): tras fusionar GS5‑1, Eugenio corre `uv run python -m operacion adoptar data/apu.db --nombre silice`
y comprueba que `data/apu.db` conserva su huella (ningún agente toca `data/apu.db`).

## 4. Pendiente de redacción (RESUELTO el 2026-10-11: C completada con código en todas sus tareas)

C conserva pasos descritos en prosa, con firmas fijadas pero sin bloque de código (C §Discrepancias 17): Tarea 6
(`inpc.py`, `csv_canonico.py`, `formatos.py` y sus pruebas), Tarea 9 (`ui/precios_empresa.py`, dos páginas y su prueba),
Tarea 10 (`abrir_version`, `precios_de_version`, páginas y prueba de `test_ui_proyectos.py`), Tarea 12 (modelos,
`caso_0004_s1_reajuste.py`, `guardar_estudio`, `cargar_estudio`), Tarea 13 (`ui/reajuste.py` y su página) y Tarea 14
(manuales). Las tareas de A y B llevan código en cada paso. No quedan «TBD», «TODO», «similar a la tarea N», «igual
para …» ni la línea muerta `if False` de la Tarea 11 de C.
