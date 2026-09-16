# Integración continua (CI) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un pipeline de GitHub Actions que en cada PR y push a `main` garantiza suite + ruff en
Linux y Windows sin pruebas omitidas, la guardia del núcleo, cobertura de `core/` ≥ 80 % y
artefactos reproducibles.

**Architecture:** Un workflow (`.github/workflows/ci.yml`) con dos jobs: `calidad` (ruff +
guardia, sin extras pesados) y `pruebas` (matriz Linux + Windows con todos los extras). La lógica
nueva vive en dos scripts pequeños con funciones puras probadas en unidad, que reutilizan los
auxiliares de `scripts/meta_alpha.py` en vez de duplicarlos.

**Tech Stack:** GitHub Actions (`actions/checkout@v7`, `astral-sh/setup-uv@v10.1.0`,
`actions/cache@v6`), uv 0.11.9, Python 3.13, pytest + pytest-cov, ruff.

**Spec:** `docs/superpowers/specs/2026-09-14-ci-integracion-continua-design.md`

## Global Constraints

- `core/` no se toca: `git diff worktree-sprint-multidominio --stat -- core/` vacío al cerrar cada tarea.
- Todo con `--locked`: `uv.lock` y las dependencias de `pyproject.toml` no cambian.
- Vedados: `CLAUDE.md`, `README.md`, `docs/README.md`, `docs/linea_base.md`, `docs/tesis/**`.
- Prohibido modificar pruebas existentes para ponerlas en verde; nunca omitir una prueba por plataforma para obtener un verde.
- Código, docstrings y commits en español; identificadores y asuntos de commit sin tildes; Conventional Commits; salidas de consola en ASCII (consola cp1252).
- Cada tarea cierra con `uv run pytest -W error` verde y `uv run ruff check .` limpio. Entorno: `HF_HUB_DISABLE_SYMLINKS_WARNING=1`.
- Worktree `.claude/worktrees/ci-integracion`, rama `inc/CI-integracion-continua`; el PR #2 apunta a `worktree-sprint-multidominio`.

---

### Task 1: Guardia del núcleo (`scripts/guardia_nucleo.py`)

**Files:**
- Create: `scripts/guardia_nucleo.py`
- Test: `tests/unit/test_guardia_nucleo.py`

**Interfaces:**
- Consumes: de `scripts/meta_alpha.py`, `Estado` (StrEnum `OK`/`FALLA`/`PENDIENTE`), `estado_nucleo_intacto(commits, ramas) -> tuple[Estado, str]`, `_commits_nucleo_intacto(base) -> list[tuple[str, list[str]]]`, `_ramas_adaptador(base) -> list[tuple[str, list[str]]]` y `_git(*args) -> list[str]` (lista vacía si git falla).
- Produces: `veredicto(base: str, *, base_existe: bool, commits, ramas) -> tuple[int, str]`, y la CLI `python scripts/guardia_nucleo.py --base <ref>`, con salida 0 si cumple, 1 si viola y 2 si la base es inválida. La usa la Task 3.

- [ ] **Step 1: Write the failing test** — `tests/unit/test_guardia_nucleo.py`:

```python
"""Pruebas de `scripts/guardia_nucleo.py` (integracion continua).

La regla ya la prueba `test_meta_alpha.py` (`estado_nucleo_intacto`); aqui se prueba lo que la
guardia agrega: el codigo de salida y que una base inexistente nunca pase como rango vacio. Como en
`test_meta_alpha.py`, ninguna prueba ejecuta git: `veredicto` recibe los datos ya leidos.
"""

from scripts import guardia_nucleo


def test_base_inexistente_sale_con_2_aunque_no_haya_commits():
    """Sin la validacion, un rango invalido daria cero commits, PENDIENTE y un verde falso."""
    codigo, mensaje = guardia_nucleo.veredicto(
        "rama-inexistente", base_existe=False, commits=[], ramas=[]
    )

    assert codigo == 2
    assert "rama-inexistente" in mensaje


def test_commit_que_mezcla_core_y_adapters_sale_con_1():
    commits = [("a" * 40, ["core/costing/motor.py", "adapters/telecom/adaptador.py"])]

    codigo, mensaje = guardia_nucleo.veredicto("main", base_existe=True, commits=commits, ramas=[])

    assert codigo == 1
    assert "FALLA" in mensaje


def test_commits_que_solo_tocan_adapters_salen_con_0():
    commits = [("b" * 40, ["adapters/telecom/adaptador.py", "tests/unit/test_adapter_telecom.py"])]

    codigo, mensaje = guardia_nucleo.veredicto("main", base_existe=True, commits=commits, ramas=[])

    assert codigo == 0
    assert "OK" in mensaje


def test_rango_sin_commits_de_dominio_sale_con_0():
    """PENDIENTE: no hay commits de adapters/ ni ml/ que puedan violar la regla."""
    codigo, mensaje = guardia_nucleo.veredicto("main", base_existe=True, commits=[], ramas=[])

    assert codigo == 0
    assert "PENDIENTE" in mensaje
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -W error -p no:cacheprovider tests/unit/test_guardia_nucleo.py`
Expected: FAIL con `ImportError: cannot import name 'guardia_nucleo'`

- [ ] **Step 3: Write minimal implementation** — `scripts/guardia_nucleo.py`:

```python
"""Guardia del nucleo para CI: la hipotesis central aplicada a un rango de commits.

Aplica a `<base>..HEAD` la regla de `scripts/meta_alpha.py` (`estado_nucleo_intacto`): falla si un
commit toca `core/` junto a `adapters/` o `ml/`, o si una rama fusionada que incorpora un dominio
cambia `core/` (CLAUDE.md seccion 1). A diferencia de las metas de sprint, la base no esta fija: la
pone quien llama (el workflow de CI o el desarrollador en local).

Codigos de salida: 0 si la regla se cumple o el rango no tiene commits de dominio; 1 si se viola;
2 si la base no existe (una base invalida nunca se lee como rango vacio).

Uso: `uv run python scripts/guardia_nucleo.py --base main`.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import (  # noqa: E402
    Estado,
    _commits_nucleo_intacto,
    _git,
    _ramas_adaptador,
    estado_nucleo_intacto,
)

SALIDA_CUMPLE = 0
SALIDA_VIOLACION = 1
SALIDA_BASE_INVALIDA = 2


def veredicto(
    base: str,
    *,
    base_existe: bool,
    commits: Sequence[tuple[str, Sequence[str]]],
    ramas: Sequence[tuple[str, Sequence[str]]],
) -> tuple[int, str]:
    """Codigo de salida y mensaje para el rango `base..HEAD` ya leido de git.

    2 si la base no existe; 1 si `estado_nucleo_intacto` da FALLA; 0 con OK o con PENDIENTE (el
    rango no tiene commits de `adapters/` ni `ml/`, asi que no hay nada que violar).
    """
    if not base_existe:
        return SALIDA_BASE_INVALIDA, f"la base {base!r} no existe en este repositorio"
    estado, evidencia = estado_nucleo_intacto(commits, ramas)
    codigo = SALIDA_VIOLACION if estado is Estado.FALLA else SALIDA_CUMPLE
    return codigo, f"{estado.value}: {evidencia}"


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--base", required=True, help="referencia git desde la que se evalua el rango base..HEAD"
    )
    base = analizador.parse_args(argv).base

    base_existe = bool(_git("rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"))
    commits = _commits_nucleo_intacto(base) if base_existe else []
    ramas = _ramas_adaptador(base) if base_existe else []
    codigo, mensaje = veredicto(base, base_existe=base_existe, commits=commits, ramas=ramas)
    print(f"guardia del nucleo: {mensaje}")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -W error -p no:cacheprovider tests/unit/test_guardia_nucleo.py tests/unit/test_meta_alpha.py`
Expected: PASS (4 + 26)

- [ ] **Step 5: Pruebas negativas de la CLI contra git real** (se anotan en la bitácora):

```bash
uv run --no-sync python scripts/guardia_nucleo.py --base no-existe; echo "salida=$?"                    # esperado 2
uv run --no-sync python scripts/guardia_nucleo.py --base worktree-sprint-multidominio; echo "salida=$?"  # esperado 0
git switch -c tmp/guardia-negativa
echo "# prueba negativa desechable" >> core/__init__.py
echo "# prueba negativa desechable" >> adapters/__init__.py
git commit -qam "tmp: commit desechable que mezcla core y adapters"
uv run --no-sync python scripts/guardia_nucleo.py --base HEAD~1; echo "salida=$?"                        # esperado 1
git switch inc/CI-integracion-continua
git branch -D tmp/guardia-negativa
git diff worktree-sprint-multidominio --stat -- core/ adapters/                                          # esperado vacio
```

- [ ] **Step 6: Commit**

```bash
git add scripts/guardia_nucleo.py tests/unit/test_guardia_nucleo.py
git commit -m "feat(scripts): guardia del nucleo para ci con base configurable"
```

---

### Task 2: Verificador de pruebas omitidas (`scripts/verificar_omitidas.py`)

**Files:**
- Create: `scripts/verificar_omitidas.py`
- Test: `tests/unit/test_verificar_omitidas.py`

**Interfaces:**
- Consumes: de `scripts/meta_alpha.py`, `_testcases(raiz) -> Iterator[ET.Element]` y `_resultado_de(testcase) -> str` (`"omitidas"` cuando hay `<skipped>`).
- Produces: `omitidas(xml_texto: str) -> list[str]`, la excepción `SinEvidenciaError(ValueError)` y la CLI `python scripts/verificar_omitidas.py <junit.xml>`, con salida 0 sin omitidas, 1 con alguna omitida y 2 sin evidencia. La usa la Task 3.

- [ ] **Step 1: Write the failing test** — `tests/unit/test_verificar_omitidas.py`:

```python
"""Pruebas de `scripts/verificar_omitidas.py` (integracion continua).

JUnit sintetico con la forma que escribe `pytest --junitxml`; ninguna prueba ejecuta pytest.
"""

import pytest

from scripts import verificar_omitidas

JUNIT_CON_UNA_OMITIDA = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" skipped="1" tests="2" time="0.10">
    <testcase classname="tests.unit.test_a" name="test_uno" time="0.01" />
    <testcase classname="tests.unit.test_ifc" name="test_dos" time="0.00">
      <skipped type="pytest.skip" message="could not import 'ifcopenshell'">omitida</skipped>
    </testcase>
  </testsuite>
</testsuites>
"""

JUNIT_SIN_OMITIDAS = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="0" tests="2" time="0.10">
    <testcase classname="tests.unit.test_a" name="test_uno" time="0.01" />
    <testcase classname="tests.unit.test_b" name="test_dos" time="0.01">
      <failure message="boom">AssertionError: boom</failure>
    </testcase>
  </testsuite>
</testsuites>
"""

JUNIT_SIN_PRUEBAS = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" errors="0" failures="0" skipped="0" tests="0" /></testsuites>
"""


def test_omitidas_lista_cada_omitida_con_su_motivo():
    assert verificar_omitidas.omitidas(JUNIT_CON_UNA_OMITIDA) == [
        "tests.unit.test_ifc::test_dos - could not import 'ifcopenshell'"
    ]


def test_una_fallida_no_cuenta_como_omitida():
    """Las fallidas ya ponen en rojo el paso de pytest; este verificador solo mira omisiones."""
    assert verificar_omitidas.omitidas(JUNIT_SIN_OMITIDAS) == []


def test_junit_sin_pruebas_es_ausencia_de_evidencia():
    with pytest.raises(verificar_omitidas.SinEvidenciaError, match="ninguna prueba"):
        verificar_omitidas.omitidas(JUNIT_SIN_PRUEBAS)


def test_xml_ilegible_es_ausencia_de_evidencia():
    with pytest.raises(verificar_omitidas.SinEvidenciaError, match="ilegible"):
        verificar_omitidas.omitidas("<testsuites><testsuite>")


def test_main_codigos_de_salida(tmp_path):
    con_omitida = tmp_path / "con_omitida.xml"
    con_omitida.write_text(JUNIT_CON_UNA_OMITIDA, encoding="utf-8")
    limpio = tmp_path / "limpio.xml"
    limpio.write_text(JUNIT_SIN_OMITIDAS, encoding="utf-8")

    assert verificar_omitidas.main([str(tmp_path / "no_existe.xml")]) == 2
    assert verificar_omitidas.main([str(con_omitida)]) == 1
    assert verificar_omitidas.main([str(limpio)]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -W error -p no:cacheprovider tests/unit/test_verificar_omitidas.py`
Expected: FAIL con `ImportError: cannot import name 'verificar_omitidas'`

- [ ] **Step 3: Write minimal implementation** — `scripts/verificar_omitidas.py`:

```python
"""Verificador de CI: ninguna prueba omitida en el JUnit de pytest.

Siete archivos de prueba usan `pytest.importorskip` (ifcopenshell, scikit-learn,
sentence-transformers) y `test_normalizacion.py` se omite si el modelo de similitud no se puede
descargar. Si en CI faltara un extra, esas pruebas desaparecerian en silencio y la corrida saldria
verde: este script convierte "0 omitidas" en una condicion del pipeline.

Codigos de salida: 0 sin omitidas; 1 con alguna omitida (se listan con su motivo); 2 sin evidencia
(archivo inexistente, XML ilegible o cero pruebas), porque la ausencia de datos nunca es un OK: el
mismo principio de `meta_alpha.estado_pruebas`.

Uso: `uv run python scripts/verificar_omitidas.py reporte-pruebas.xml`.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import _resultado_de, _testcases  # noqa: E402

SALIDA_SIN_OMITIDAS = 0
SALIDA_CON_OMITIDAS = 1
SALIDA_SIN_EVIDENCIA = 2


class SinEvidenciaError(ValueError):
    """El JUnit no permite afirmar nada: es ilegible o no registra pruebas."""


def omitidas(xml_texto: str) -> list[str]:
    """Cada prueba omitida como `classname::name - motivo`, en el orden del reporte.

    `SinEvidenciaError` si el XML no se puede leer o no registra ninguna prueba.
    """
    try:
        raiz = ET.fromstring(xml_texto)
    except ET.ParseError as error:
        raise SinEvidenciaError(f"JUnit ilegible: {error}") from error
    casos = list(_testcases(raiz))
    if not casos:
        raise SinEvidenciaError("el JUnit no registra ninguna prueba")
    return [_describir(caso) for caso in casos if _resultado_de(caso) == "omitidas"]


def _describir(caso: ET.Element) -> str:
    omision = caso.find("skipped")
    motivo = omision.get("message", "sin motivo") if omision is not None else "sin motivo"
    return f"{caso.get('classname')}::{caso.get('name')} - {motivo}"


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("reporte", type=Path, help="JUnit XML escrito por pytest --junitxml")
    reporte = analizador.parse_args(argv).reporte

    if not reporte.exists():
        print(f"verificar omitidas: no existe {reporte}")
        return SALIDA_SIN_EVIDENCIA
    try:
        lista = omitidas(reporte.read_text(encoding="utf-8"))
    except SinEvidenciaError as error:
        print(f"verificar omitidas: {error}")
        return SALIDA_SIN_EVIDENCIA
    if lista:
        print(f"verificar omitidas: {len(lista)} prueba(s) omitida(s)")
        for linea in lista:
            print(f"  {linea}")
        return SALIDA_CON_OMITIDAS
    print("verificar omitidas: 0 omitidas")
    return SALIDA_SIN_OMITIDAS


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -W error -p no:cacheprovider tests/unit/test_verificar_omitidas.py`
Expected: PASS (5)

- [ ] **Step 5: Commit**

```bash
git add scripts/verificar_omitidas.py tests/unit/test_verificar_omitidas.py
git commit -m "feat(scripts): verificador de pruebas omitidas para ci"
```

---

### Task 3: Workflow de CI y primera corrida remota

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `.gitignore` (añadir `reporte-pruebas.xml`)

**Interfaces:**
- Consumes: CLI de las Tasks 1 y 2; `scripts/exportar_openapi.py` (escribe `docs/api.json`); `scripts/generar_resultados_ml.py` (escribe `docs/resultados_ml.md`).
- Produces: los checks `calidad (ruff + guardia del nucleo)`, `pruebas (ubuntu-latest)` y `pruebas (windows-latest)` en el PR #2; la URL del run verde, que usa la Task 4.

- [ ] **Step 1: Escribir `.github/workflows/ci.yml`**

```yaml
# Integracion continua (spec: docs/superpowers/specs/2026-09-14-ci-integracion-continua-design.md).
# Cuatro garantias: suite + ruff en Linux sin omitidas, guardia del nucleo, cobertura de core/
# >= 80 % y artefactos reproducibles, y la suite tambien en Windows (RNF-06, RNF-07).
name: CI

on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

env:
  HF_HUB_DISABLE_SYMLINKS_WARNING: "1"

defaults:
  run:
    shell: bash

jobs:
  calidad:
    name: calidad (ruff + guardia del nucleo)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout con historia completa
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Instalar uv
        uses: astral-sh/setup-uv@v10.1.0
        with:
          version: "0.11.9"
          enable-cache: true

      - name: Entorno minimo (grupo dev)
        run: uv sync --locked --only-group dev

      - name: Ruff
        run: uv run --no-sync ruff check .

      - name: Guardia del nucleo
        env:
          EVENTO: ${{ github.event_name }}
          BASE_PR: ${{ github.base_ref }}
          ANTES: ${{ github.event.before }}
        run: |
          case "$EVENTO" in
            pull_request)
              base="origin/$BASE_PR"
              ;;
            push)
              if [ -z "$ANTES" ] || [ "$ANTES" = "0000000000000000000000000000000000000000" ]; then
                echo "::notice::primer push de la rama: no hay rango que evaluar"
                exit 0
              fi
              base="$ANTES"
              ;;
            *)
              base="origin/main"
              ;;
          esac
          uv run --no-sync python scripts/guardia_nucleo.py --base "$base"

  pruebas:
    name: pruebas (${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    steps:
      - name: Checkout
        uses: actions/checkout@v7

      - name: Instalar uv
        uses: astral-sh/setup-uv@v10.1.0
        with:
          version: "0.11.9"
          enable-cache: true

      - name: Cache del modelo de similitud
        uses: actions/cache@v6
        with:
          path: ~/.cache/huggingface
          key: hf-${{ runner.os }}-paraphrase-multilingual-MiniLM-L12-v2

      - name: Entorno completo (todos los extras)
        run: uv sync --locked --all-extras

      - name: Suite (pytest -W error)
        run: >-
          uv run --no-sync pytest -W error -p no:cacheprovider
          --junitxml=reporte-pruebas.xml
          --cov=core --cov=ml --cov=api --cov=adapters --cov-report=term

      - name: Sin pruebas omitidas
        run: uv run --no-sync python scripts/verificar_omitidas.py reporte-pruebas.xml

      - name: Cobertura de core >= 80 % (RNF-06)
        if: runner.os == 'Linux'
        run: uv run --no-sync coverage report --include="core/*" --fail-under=80

      - name: Artefactos reproducibles
        if: runner.os == 'Linux'
        run: |
          uv run --no-sync python scripts/exportar_openapi.py
          uv run --no-sync python scripts/generar_resultados_ml.py
          git diff --exit-code -- docs/api.json docs/resultados_ml.md
```

- [ ] **Step 2: Añadir `reporte-pruebas.xml` a `.gitignore`**, en el bloque «Entornos y caches de Python», debajo de `htmlcov/`.

- [ ] **Step 3: Validar el YAML en local**

Run: `uv run --with pyyaml python -c "import yaml; d = yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); print(sorted(d['jobs']))"`
Expected: `['calidad', 'pruebas']`

- [ ] **Step 4: Ensayo local de los pasos del job `pruebas`** (el mismo orden que en CI)

```bash
uv run --no-sync pytest -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml --cov=core --cov=ml --cov=api --cov=adapters --cov-report=term | tail -3
uv run --no-sync python scripts/verificar_omitidas.py reporte-pruebas.xml     # esperado "0 omitidas", salida 0
uv run --no-sync coverage report --include="core/*" --fail-under=80 | tail -1  # esperado TOTAL ~98 %, salida 0
uv run --no-sync python scripts/exportar_openapi.py && uv run --no-sync python scripts/generar_resultados_ml.py
git diff --exit-code -- docs/api.json docs/resultados_ml.md; echo "salida=$?"  # esperado 0
```

Prueba negativa de reproducibles: `echo " " >> docs/api.json; git diff --exit-code --quiet -- docs/api.json; echo "salida=$?"` (esperado 1), y restaurar con `git checkout -- docs/api.json`. Prueba negativa de omitidas: `verificar_omitidas.py` sobre un JUnit con una omitida (esperado 1). Ya lo cubre `test_main_codigos_de_salida`; se repite por CLI y se anota en la bitácora.

- [ ] **Step 5: Suite + ruff + núcleo intacto, y commit**

```bash
uv run ruff check .
git diff worktree-sprint-multidominio --stat -- core/     # esperado vacio
git add .github/workflows/ci.yml .gitignore
git commit -m "ci: workflow con suite en linux y windows, guardia del nucleo y reproducibles"
```

- [ ] **Step 6: Push y PR #2**

```bash
git push -u origin inc/CI-integracion-continua
gh pr create --base worktree-sprint-multidominio --head inc/CI-integracion-continua \
  --title "Integracion continua: suite en Linux y Windows, guardia del nucleo y reproducibles" \
  --body-file <cuerpo del PR en el scratchpad: garantias, scripts nuevos, pruebas negativas, enlace a la spec, linea de atribucion>
```

- [ ] **Step 7: Observar la primera corrida**

Run: `gh pr checks <numero> --watch --interval 30`
Expected: los tres checks en verde. Registrar la duración de cada job con
`gh run view <id> --json jobs --jq '.jobs[] | [.name, .conclusion, .startedAt, .completedAt]'`.

Si un check falla: usar superpowers:systematic-debugging con el log
(`gh run view <id> --log-failed`). Un defecto de portabilidad se corrige en código, con prueba, en
un commit propio (`fix(<ambito>): …`). Nunca se relaja una garantía ni se omite una prueba para
obtener el verde. Si falla por disco o tiempo al instalar torch con CUDA, se detiene y se consulta
al usuario (spec §7).

---

### Task 4: Documentación y cierre del incremento

**Files:**
- Modify: `docs/plan_pruebas.md` (§7 entorno y §9 fila RNF‑07)
- Modify: `docs/calidad_iso25010.md` (§6 Portabilidad, fila de §9 y párrafo de resumen)
- Modify: `docs/manual_tecnico.md` (§2 entorno)
- Create: `docs/bitacora/2026-09-14-CI-integracion-continua.md`

**Interfaces:**
- Consumes: la URL del run verde de la Task 3, obtenida con `gh run list --branch inc/CI-integracion-continua --limit 1 --json url --jq '.[0].url'`, y las duraciones de sus jobs.
- Produces: RNF‑07 con veredicto «cumple» y evidencia enlazada; la bitácora del incremento.

- [ ] **Step 1: `docs/plan_pruebas.md` §7**: después del bloque de comandos, añadir el párrafo:

```markdown
**Integración continua** (desde 2026‑09‑15, `.github/workflows/ci.yml`): cada PR y cada push a
`main` ejecutan en runners de GitHub el job `calidad` (ruff y `scripts/guardia_nucleo.py`, que
aplica la regla de la hipótesis central al rango del cambio) y el job `pruebas` en Linux y
Windows (todos los extras, `pytest -W error` y `scripts/verificar_omitidas.py`, que exige 0
omitidas). En Linux, además, la cobertura de `core/` ≥ 80 % y la regeneración sin diferencias de
`docs/api.json` y `docs/resultados_ml.md`. Cada paso tiene su comando local equivalente en
[manual_tecnico.md](manual_tecnico.md) §2.
```

- [ ] **Step 2: `docs/plan_pruebas.md` §9**: la fila de RNF‑07 pasa a
`| RNF‑07 portabilidad | `uv sync --locked` sin pasos manuales y suite completa en verde en Windows 11 (local) y en Linux y Windows (CI, <URL del run>) | cumple |`, con la URL real del Step de Interfaces.

- [ ] **Step 3: `docs/calidad_iso25010.md`**: en §6 se reemplaza el texto «La verificación en Linux está **pendiente** …» por la evidencia del run (Linux y Windows en CI, URL, fecha), y el veredicto pasa a **cumple**. En la fila de §9, «Windows ✔; Linux pendiente | parcial» pasa a «Windows ✔ (local y CI); Linux ✔ (CI) | cumple». El párrafo de resumen que empieza «Cinco características cumplen…» se reescribe con seis que cumplen, una pendiente (usabilidad) y una parcial (compatibilidad IFC), leyendo antes el párrafo completo.

- [ ] **Step 4: `docs/manual_tecnico.md` §2**: después del bloque de comandos, añadir:

```markdown
**Integración continua.** `.github/workflows/ci.yml` repite en GitHub, en cada PR y push a `main`,
lo que se verifica en local, y los pasos se reproducen así:

| Paso de CI | Comando local |
|---|---|
| Ruff | `uv run ruff check .` |
| Guardia del núcleo | `uv run python scripts/guardia_nucleo.py --base <rama base>` (0 cumple, 1 viola, 2 base inválida) |
| Suite sin omitidas | `uv run pytest -W error --junitxml=reporte-pruebas.xml` y `uv run python scripts/verificar_omitidas.py reporte-pruebas.xml` |
| Cobertura de `core/` | `uv run coverage report --include="core/*" --fail-under=80` (tras la suite con `--cov=core`) |
| Reproducibles | `uv run python scripts/exportar_openapi.py`, `uv run python scripts/generar_resultados_ml.py` y `git diff --exit-code -- docs/api.json docs/resultados_ml.md` |
```

- [ ] **Step 5: Bitácora** `docs/bitacora/2026-09-14-CI-integracion-continua.md` con las secciones Objetivo, TDD (RED y GREEN de las Tasks 1 y 2), Qué se creó (tabla de archivos), Pruebas negativas (salida de cada comando de las Tasks 1 y 3), Primera corrida remota (URL, conclusión y duración de cada job), Hallazgos (incluidos los de portabilidad si aparecieron), Pendientes en archivos vedados («mencionar CI en CLAUDE.md §3» e «insignia de CI en README.md») y Estado final (suite, ruff, `core/` vacío, checks del PR).

- [ ] **Step 6: Suite + ruff + núcleo intacto, commit y push**

```bash
uv run pytest -W error -p no:cacheprovider | tail -2
uv run ruff check .
git diff worktree-sprint-multidominio --stat -- core/
git add docs/plan_pruebas.md docs/calidad_iso25010.md docs/manual_tecnico.md docs/bitacora/2026-09-14-CI-integracion-continua.md
git commit -m "docs(pruebas): rnf-07 cumple con evidencia de ci en linux y windows"
git push
```

Expected: el push dispara otra corrida del PR #2, también en verde (`gh pr checks <numero> --watch`).
