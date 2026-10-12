# Plan de construcción de Sílice 0.7.0

> **Para quien ejecute (agentes):** SUB-SKILL REQUERIDA: `superpowers:subagent-driven-development` (un subagente
> por tarea con su ficha de rol `C:\Users\euger\.claude\agents\sf-*.md` y un revisor fresco por tarea). Los pasos
> usan casillas `- [ ]`. Cada tarea lleva su prueba primero, con el rojo observado (NORMAS §5).

**Objetivo:** entregar la 0.7.0 de Sílice, que es **S2: el presupuesto vivo**. Una obra en marcha registra valuaciones
por cantidades ejecutadas (a mano o por Excel) y costos reales; el sistema calcula el **valor ganado** (PV, EV, AC, SV,
CV, SPI, CPI, EAC, VAC) en la moneda del proyecto, **separa el desvío de control** en plazo, precio y consumo, evalúa
las **alertas** AL-1 a AL-6 y **reproyecta** plan, término, costo final y punto de equilibrio sin que nadie lo pida.
A pedido calcula cuatro **opciones de recuperación** (más cuadrillas, horas extra, partidas en paralelo, aceptar el
retraso) con su costo, y la que el usuario elige se guarda como una **versión nueva** del presupuesto (motivo
`recuperacion`) con su registro de cambios. Lo ejecutado de las valuaciones alimenta además el reajuste de S1 (UC-18).
Todo corre sobre las bases migradas con Alembic de la 0.6.0, que ganan 9 tablas aditivas.

**Arquitectura:** seis fases en orden estricto, sobre la base de las secciones A, B y C del plan de la 0.6.0.
- **S2-0 (docs, sin núcleo):** la parte S2 de la meta única (`scripts/meta_silice_s2.py`), la ERS (UC-19, UC-20, RF-72
  a RF-79, RNF-15, R13 y R14), la memoria a mano **OB-S2** y su XLSX antes de todo código, y los tres expedientes
  SL-E4, SL-E5 y SL-E6 escritos antes del núcleo que cubren.
- **S2-1 (núcleo, SL-E4):** las tablas de `core/models/control.py`, la revisión `caso_0005_s2_valuaciones`, el
  calendario hábil, R13 y R14 (`core/verification/valuaciones.py`), el registro y la anulación de valuaciones, la
  importación de Excel y el puente con S1 (`ejecutado_por_periodo`, estudio con valuaciones citadas).
- **S2-2 (núcleo, SL-E5):** el equilibrio extraído sin cambiar su resultado, el valor ganado y la separación del
  desvío, la reproyección, las alertas, el PE proyectado y el **reajuste reconocido** que lo alimenta.
- **S2-3 (núcleo, SL-E6):** las opciones de recuperación (funciones puras) y la decisión que crea la versión
  (`guardar_edicion(motivo=...)`), con la revisión `caso_0006_s2_decision`.
- **S2-4 (interfaz):** `ui/control.py` (sin Streamlit), la pantalla «Control de obra» con cinco pestañas, la casilla
  de la pantalla de reajuste de S1, la hoja del proyecto con sus tablas de control en Excel y la medición de RNF-15.
- **S2-5 (cierre):** versión 0.7.0, CHANGELOG, manuales, etiqueta `v0.7.0` y la base de prueba de la 0.7.0.

**Tecnología:** Python 3.13, `uv`, SQLAlchemy 2.0, Alembic ≥ 1.20, Streamlit 1.62 (`AppTest`), `openpyxl` (ya
presente), `Decimal` (prec 28, ROUND_HALF_EVEN). S2 no agrega dependencias.

**Specs:** maestro `docs/especificaciones/2026-10-11-silice-1.0.0-design.md` (rulings RV-1…RV-26, §10), S2
`docs/especificaciones/2026-10-11-silice-s2-presupuesto-vivo-design.md` (revisión 2), horizonte
`docs/especificaciones/2026-10-08-horizonte-reorientacion-design.md` (H-D2, H-D5, §4 y §6, fase R2) y los
antecedentes. Todos fueron aprobados por Eugenio el 2026-10-11. El plan cita los specs por sección y no los repite;
quien ejecute lee el plan y el spec. La parte numérica es la memoria `control_ob_s2.md` (S2 §7.1), que el plan copia
literal.

## Restricciones globales

- **Condición de entrada:** la 0.6.0 está fusionada y etiquetada (`v0.6.0`) con su base de prueba, y `main` local es
  `origin/main`. Las firmas que S2 consume de ella están en la última sección («Supuestos sobre 0.6.0»); si una no
  existe tal cual, la tarea que la consume se detiene y se registra, no se improvisa otra.
- `core/contracts/` no se toca: `git diff v0.6.0..HEAD -- core/contracts/` debe quedar vacío.
- `core/` solo cambia en las ramas `inc/070-s2-<n>-nucleo` (S2-1, S2-2, S2-3 y la corrección de rendimiento de S2-4). Cada una toca solo `core/`, `migraciones/`, `tests/`, `docs/` y, para el generador y la medición de RNF-15, `scripts/`; nunca `ui/`, `adapters/` ni `ml/`. Cada una requiere, antes de abrirse, el expediente de su
  SL-E (escrito en la tarea 3, commiteado antes del código) y el visto bueno del tutor. Nunca hay dos ramas de núcleo
  abiertas: el carril es único (S2-1 → S2-2 → S2-3 → S2-4-nucleo).
- Las tablas nuevas viven en **un solo módulo**, `core/models/control.py`; los modelos ya existentes no ganan
  columnas. Las revisiones `caso_0005_s2_valuaciones` y `caso_0006_s2_decision` se encadenan tras
  `caso_0004_s1_reajuste` y son aditivas: crean tablas y no tocan filas.
- `main` es la única rama de integración. Las ramas son cortas, por fase, salen de `origin/main` del momento y abren su
  PR contra `main`. Se fusionan con `gh pr merge <n> --merge` (merge commit, nunca *squash*: C3 de la meta lee el orden
  prueba → implementación) al cruzar su compuerta.
- Montos en `Decimal`; las divisiones van dentro de `decimal.localcontext(prec=28, rounding=ROUND_HALF_EVEN)` y se
  multiplica antes de dividir; se redondea solo al presentar. Los días se `quantize` a `1e-12` antes del techo.
- Una valuación registrada y no anulada **cuenta desde su registro** (RV-18): no hay estado «aprobada». Las valuaciones
  y los costos reales son solo-agregar; se corrigen anulando con fuente y registrando otra.
- Se guardan **entradas y decisiones**; indicadores, alertas y hallazgos de R13 y R14 se **recalculan** (S2-R13). R13 y
  R14 no entran a `REGLAS` ni al informe guardado de ninguna versión.
- Cero pruebas omitidas (`scripts/verificar_omitidas.py`), `pytest -W error`, ruff limpio solo sobre los archivos
  tocados (nunca `ruff format .` en todo el repositorio; líneas de 100 columnas como máximo) y
  `scripts/guardia_nucleo.py --base origin/main`.
- La suite corre sin red: solo 127.0.0.1 y ::1, con `HF_HUB_OFFLINE=1` (guardia de red de la 0.6.0). Ninguna prueba de
  S2 abre un socket.
- El bloque de regresión no cambia: `git diff v0.6.0..HEAD` vacío sobre `ARCHIVOS_REGRESION`, y las memorias de S1 no
  se editan (`S2-REG-S1`). Ver «Bloque de regresión» al final.
- Prohibido `pkill`, `taskkill`, `git add -A` y matar procesos ajenos, porque hay sesiones en paralelo. **Nadie toca
  `data/apu.db`**; las pruebas usan SQLite en memoria o bases en `tmp_path`.
- Las memorias a mano (oráculos) se escriben antes del código, con las cifras literales del spec; la memoria OB-S2 se
  rehace además con `fractions.Fraction` (oráculo independiente de `Decimal`).
- Texto ajeno (nombres de hoja y celdas de un XLSX de valuaciones, fuentes, observaciones) se muestra por celdas o por
  `ui.texto_seguro.texto_seguro()`; nunca `unsafe_allow_html` (RV-14).
- Commits convencionales en español, asunto sin tildes, con el trailer final
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` (en los bloques se escribe como segundo `-m`).
- Todos los datos de OB-S2 y de las bases de prueba son **ficticios** (NORMAS §1): la obra, el inspector, las actas y
  los costos reales los inventa la memoria. Lo real son la LOTTT (arts. 118, 173, 178 y 182, citados a cotejar) y los
  índices del BCV que importa S1.
- Las bitácoras y los specs anteriores al 2026-10-11 son historia y no se editan.

## Rulings propios del plan (RP7-n, 2026-10-11)

Al llevar el spec al código aparecieron decisiones que el spec no fija. Se ratifican aquí con el valor que el código
ya prueba; cada una tiene su prueba en la tarea dueña. Las de más peso para Eugenio o el tutor van marcadas.
- **RP7-1:** la instantánea de control lleva **todas** las valuaciones no anuladas, también las posteriores al corte.
  EV cuenta solo las que tienen `hasta ≤ corte`; R14(b) marca como hallazgo a las posteriores (T5, T7).
- **RP7-2:** `core/budget/calendario.py` entra con el expediente SL-E4 y la rama S2-1 (el spec lo nombraba en SL-E5):
  R14 necesita contar días hábiles y R14 está en SL-E4. Como `core/verification` no importa `core/budget`, la
  instantánea inyecta `habiles_entre` (T4, T5).
- **RP7-3:** módulos que el spec §5.2 no nombraba y el código necesita: `core/budget/puente.py` (S1↔S2),
  `core/budget/control.py` (orquesta la instantánea, el estado y los indicadores), `core/budget/decision.py` (para
  que `recuperacion.py` quede **pura**) y los tipos de valuación en `core/verification/valuaciones.py` (rompen el
  ciclo budget ↔ verification) (T5, T9, T11).
- **RP7-4:** la cita de un estudio de reajuste a sus valuaciones es una tabla propia, `cita_valuacion`, en
  `caso_0005`; no se agrega columna a `ejecutado_periodo` de S1 (S1 no se enmienda). Son 9 tablas en
  total, no las 7 que decía el expediente del spec (T4, T6).
- **RP7-5:** horas extra: `h = horas_extra_dia` (por defecto 2) en **todas** las partidas determinantes de la ruta;
  el límite anual de 100 horas (art. 178 LOTTT, a cotejar) usa las `horas_previas` declaradas (T10).
- **RP7-6:** R13 emite **un hallazgo por partida** (el primer cruce de lo presupuestado, con el impacto total);
  R14(c) emite uno por pareja de valuaciones que se solapan (T5).
- **RP7-7:** la decisión sale de la **versión vigente** y compara contra su propio plan; en la primera decisión ese
  plan coincide con la línea base. Cada decisión registra sus propios cambios (T11).
- **RP7-8:** las partidas que la línea base no tiene (OB-D en la memoria) **no se entregan a S1**, que las rechaza por
  no tener su PU del contrato; R13 las marca (T6).
- **RP7-9:** `cargar_presupuesto` se precarga con `selectinload` (`_precargar`). Sin eso RNF-15 se mide en 2,96 s y
  no pasa; con eso, 0,65 s (registro) y 0,36 s (opciones). Se añade como corrección **tras** la prueba roja (T14).
- **RP7-10:** la opción «partidas en paralelo» se calcula siempre y se presenta; la **declaración de independencia**
  se exige al elegirla, no al verla (T10, T11).
- **RP7-11:** precios del corte en la pantalla: ninguno, comprobación (versión revalorada de S1) o escalatoria con un
  Km único. Sin precios, la separación dice «no disponible» y el resto funciona (T12).
- **RP7-12:** `FASES["0.7.0"] = ("S2-0", …, "S2-5")` se agrega en `scripts/meta_silice.py`; la parte S2 se descubre
  por su nombre (T1).
- **RP7-13:** el generador determinista de RNF-15 (`scripts/generar_obra_control.py`) llega en S2-2 y su medición en
  S2-4, no en S2-0 como sugiere el spec: necesita el núcleo de las dos fases anteriores (T9, T14).
- **RP7-14:** sin recorrido guiado nuevo en la 0.7.0; la pantalla se prueba con `AppTest`. Se evalúa con la 0.8.0.
- **RP7-15:** las reglas de arquitectura de S2 **copian** la tupla de prohibiciones de `ui/hoja.py` en
  `tests/unit/test_arquitectura_s2.py`: una prueba no importa a otra (T12).
- **RP7-16:** las ramas se llaman `inc/070-s2-<n>-…` (patrón de la 0.6.0), no `inc/silice-s2-…` como decía el spec.
- **RP7-17:** R13 y R14 y los expedientes SL-E no pasan por `evaluar_requisitos` de la meta; tienen comprobaciones
  propias (`S2-REGLAS`, `S2-EXPEDIENTES`) que leen el texto de la ERS y de la bitácora (T1).
- **RP7-18:** las memorias de S1 se comparan contra la etiqueta `v0.6.0`, no `v0.5.0` (T1).
- **RP7-19:** la pantalla de reajuste de S1 gana una casilla «Tomar lo ejecutado de las valuaciones registradas»; es
  el único archivo de S1 que S2 enmienda, por UC-18 (T12, T13).
- **RP7-20:** el alias `ARENIA_*` de A1 vence con la 0.7.0: al subir `pyproject.toml` a 0.7.0 el plan lo retira
  (`ALIAS_ANTERIORES = {}`, cuatro pruebas de A1 y la nota de los dos manuales), en la tarea 15.
- **RP7-21:** la corrección de rendimiento de RNF-15 (`_precargar`) es de `core/`, así que va en su propia rama de
  núcleo, `inc/070-s2-4-nucleo`, tras la de interfaz; y se ata a una prueba que cuenta sentencias SQL, no a segundos (T14).
- **Para Eugenio:** (a) las fórmulas de valor ganado y el EAC del sistema son **definiciones del sistema** hasta que el
  verificador de hechos confirme una fuente (S2-R11); (b) los umbrales de las alertas son **SUPUESTO_DECLARADO**
  (parámetros editables, nunca valores quemados); (c) los límites de la LOTTT (arts. 118, 173, 178, 182) se citan «a
  cotejar» hasta tener el texto oficial; (d) las valuaciones cuentan sin conformación del cliente (RV-18, riesgo
  aceptado). Nada de esto bloquea la 0.7.0; todo queda declarado en pantalla y en el informe.

## Orden y ramas

| Orden | Rama | Tareas | Condición |
|---|---|---|---|
| 1 | `inc/070-s2-0-docs` | 1–3 (GS2-0) | 0.6.0 fusionada y etiquetada |
| 2 | `inc/070-s2-1-nucleo` | 4–6 (SL-E4) | S2-0 fusionada |
| 3 | `inc/070-s2-2-nucleo` | 7–9 (SL-E5) | S2-1 fusionada |
| 4 | `inc/070-s2-3-nucleo` | 10–11 (SL-E6) | S2-2 fusionada |
| 5 | `inc/070-s2-4-ui` | 12–13 | S2-3 fusionada |
| 6 | `inc/070-s2-4-nucleo` | 14 (precarga y medición de RNF-15; cruza GS2-4) | S2-4 ui fusionada |
| 7 | `inc/070-s2-5-cierre` | 15, pasos 1–4 → etiqueta `v0.7.0` | todo S2 fusionado |
| 8 | `inc/070-s2-5-base` | 15, paso 5 (cruza GS2) | etiqueta puesta |

Las tareas se numeran del 1 al 15 de corrido. Las cuatro ramas de núcleo no se solapan nunca (carril único). Cada PR
sube `--hasta` en el paso «Meta de Silice» de `.github/workflows/ci.yml` (con `--version 0.7.0`) a la fase que cruza:
S2-0 → `--hasta S2-0`, S2-1 → `S2-1`, y así hasta `S2-5`.

## Mapa de tareas

| Fase | Tarea | Rama | Rol |
|---|---|---|---|
| S2-0 | 1 Parte S2 de la meta, ERS y documentos | `inc/070-s2-0-docs` | pruebas |
| S2-0 | 2 Memoria OB-S2 a mano, su XLSX y las fronteras | `inc/070-s2-0-docs` | pruebas |
| S2-0 | 3 Expedientes SL-E4, SL-E5, SL-E6 y fuentes | `inc/070-s2-0-docs` | núcleo (solo documentos) |
| S2-1 | 4 SL-E4a: tablas, revisión `caso_0005` y calendario | `inc/070-s2-1-nucleo` | núcleo |
| S2-1 | 5 SL-E4b: R13, R14, registro, anulación e instantánea | `inc/070-s2-1-nucleo` | núcleo |
| S2-1 | 6 SL-E4c: ejecutado por período, Excel y estudio con citas | `inc/070-s2-1-nucleo` | núcleo |
| S2-2 | 7 SL-E5a: equilibrio extraído y valor ganado | `inc/070-s2-2-nucleo` | núcleo |
| S2-2 | 8 SL-E5b: reproyección, alertas y PE proyectado | `inc/070-s2-2-nucleo` | núcleo |
| S2-2 | 9 SL-E5c: control, reajuste reconocido y generador | `inc/070-s2-2-nucleo` | núcleo |
| S2-3 | 10 SL-E6a: opciones de recuperación (puras) | `inc/070-s2-3-nucleo` | núcleo |
| S2-3 | 11 SL-E6b: decisión, versión `recuperacion` y `caso_0006` | `inc/070-s2-3-nucleo` | núcleo |
| S2-4 | 12 `ui/control.py` y la casilla de reajuste | `inc/070-s2-4-ui` | interfaz |
| S2-4 | 13 Pantalla «Control de obra», barra, app y hoja | `inc/070-s2-4-ui` | interfaz |
| S2-4 | 14 RNF-15: medición y precarga | `inc/070-s2-4-nucleo` | núcleo |
| S2-5 | 15 Cierre: versión, manuales, etiqueta y base de prueba | `inc/070-s2-5-cierre`, luego `inc/070-s2-5-base` | pruebas |

La tabla de interfaces de cada tarea (Consume/Produce) **manda** sobre cualquier nombre que aparezca en prosa.

---

# S2-0 — Documentos, oráculo y expedientes (rama `inc/070-s2-0-docs`)

Esta fase no toca `core/`, `ui/` ni `adapters/`: deja escrito, antes de cualquier código, qué se promete (ERS), contra
qué se compara (memoria a mano y su XLSX) y por qué cada cambio de núcleo es genérico (expedientes). Su compuerta es
GS2-0.

### Tarea 1: Parte S2 de la meta única, ERS y documentos

**Rama:** `inc/070-s2-0-docs` (sale de `origin/main` con la 0.6.0 etiquetada; PR a `main`)   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `scripts/meta_silice_s2.py`, `tests/unit/test_meta_silice_s2.py`
- Modificar: `scripts/meta_silice.py` (`FASES`, tras la entrada `"0.6.0"`: la entrada `"0.7.0"`; ubicar por contenido), `scripts/README.md` (fila de `meta_silice_s2.py`, junto a `meta_sf.py`), `.github/workflows/ci.yml` (paso «Meta de Silice»: `--version 0.7.0 --hasta S2-0` como segundo paso, tras el de la 0.6.0)
- Modificar (documentos, ubicados por contenido porque S1 y S5-1 mueven las líneas): `docs/ERS.md` (tras UC-18: UC-19 y UC-20; en §3.2, tras RF-71: RF-72 a RF-79; en §3.3, tras RNF-14 y RNF-20: RNF-15; en §3.4, R13 y R14), `docs/modelo_datos.md` (§2.6 nuevo: «Control de obra (S2)»), `docs/arquitectura.md` (vista de desarrollo: módulos de S2), `docs/plan_pruebas.md` (matriz de UC-19 y UC-20), `NORMAS.md` (§6, estructura de carpetas: los módulos nuevos), `CHANGELOG.md` (bajo `[Sin publicar]`)
- Crear: `docs/bitacora/2026-10-silice-070.md` (la bitácora de la versión; GS2 se anota ahí)

**Interfaces:**
- Consume: de `scripts.meta_silice` (0.6.0, sección A): `Parte`, `ParTDD`, `Comprobacion`, `Contexto`, `CifraDeTiempo`, `FASES`, `partes() -> list[Parte]`, `validar_partes(todas) -> None`, `_git(*args)`, `_primer_commit(ruta) -> str | None`, `_referencia_existe(ref) -> bool`; de `scripts.meta_sf`: `_ordenar_memoria(memoria, criterio) -> bool | None`, `evaluar_s2_memorias(presentes, antes, *, codigo_existe) -> tuple[Estado, str]`; `scripts.meta_alpha.Estado`.
- Produce:
- `scripts/meta_silice_s2.py`:
  - `RAIZ = Path(__file__).resolve().parents[1]`
  - `XLSX_OB_S2 = 'tests/fixtures/control/ob_s2.xlsx'`
  - `RUTA_MEMORIAS = RAIZ / 'tests' / 'fixtures' / 'memorias'`
  - `RUTA_EXPEDIENTES = RAIZ / 'docs' / 'bitacora' / '2026-10-silice-s2-expedientes.md'`
  - `CARPETA_BASE_070 = RAIZ / 'tests' / 'fixtures' / 'bases' / 'v0_7_0'`
  - `ETIQUETA_S1 = 'v0.6.0'`
  - `MEMORIAS_DE_S1 = ('tests/fixtures/memorias/s1_conversion.md', 'tests/fixtures/memorias/s1_precios_empresa.m`
  - `EXPEDIENTES = ('SL-E4', 'SL-E5', 'SL-E6')`
  - `GUION = '[-‑]'`
  - `def evaluar_reglas_en_ers(texto_ers: str | None) -> tuple[Estado, str]`
  - `def evaluar_expedientes(texto: str | None) -> tuple[Estado, str]`
  - `def evaluar_memorias_de_s1(existe_etiqueta: bool, diff: str | None) -> tuple[Estado, str]`
  - `def evaluar_base_070(carpeta: Path) -> tuple[Estado, str]`
  - `PARTE = Parte(nombre='S2 presupuesto vivo: valuaciones, valor ganado, alertas y recuperacion', req`
  y `FASES["0.7.0"] = ("S2-0", "S2-1", "S2-2", "S2-3", "S2-4", "S2-5")`; `PARTE: Parte` con los diez requisitos en `S2-0`, los pares TDD de `S2-0`…`S2-4`, las dos cifras de RNF-15 en `S2-4` y las comprobaciones `S2-MEM`, `S2-REGLAS`, `S2-EXPEDIENTES`, `S2-REG-S1` (todas en `S2-0`) y `S2-BASE-070` (en `S2-5`).

- [ ] **Paso 1: Escribir la prueba que falla**
```python
# tests/unit/test_meta_silice_s2.py
"""Parte S2 de la meta única de Sílice (spec S2 §8; plan 0.7.0, tarea 1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_silice import FASES, fases_hasta, partes, requisitos_exigidos, validar_partes
from scripts.meta_silice_s2 import (
    CIFRAS_S2,
    EXPEDIENTES,
    MEMORIAS_S2,
    PARES_S2,
    PARTE,
    REQUISITOS_S2,
    evaluar_base_070,
    evaluar_expedientes,
    evaluar_memorias_de_s1,
    evaluar_reglas_en_ers,
)

FASES_S2 = ("S2-0", "S2-1", "S2-2", "S2-3", "S2-4", "S2-5")


def test_la_0_7_0_abre_sus_seis_fases_despues_de_las_de_la_0_6_0():
    assert FASES["0.7.0"] == FASES_S2
    acumuladas = fases_hasta("0.7.0", "S2-1")
    assert acumuladas[: len(FASES["0.6.0"])] == FASES["0.6.0"]
    assert acumuladas[len(FASES["0.6.0"]) :] == ("S2-0", "S2-1")


def test_la_parte_s2_se_descubre_y_usa_fases_de_la_0_7_0():
    validar_partes((PARTE,))
    assert any(parte is PARTE for parte in partes())
    assert PARTE.requisitos == {"S2-0": REQUISITOS_S2}
    assert {par.fase for par in PARTE.pares_tdd} == set(FASES_S2[:5])
    assert [(c.codigo, c.fase) for c in PARTE.comprobaciones] == [
        ("S2-MEM", "S2-0"),
        ("S2-REGLAS", "S2-0"),
        ("S2-EXPEDIENTES", "S2-0"),
        ("S2-REG-S1", "S2-0"),
        ("S2-BASE-070", "S2-5"),
    ]


def test_los_requisitos_de_s2_son_los_diez_de_la_ers_y_se_exigen_desde_s2_0():
    assert REQUISITOS_S2 == (
        "UC-19", "UC-20", "RF-72", "RF-73", "RF-74", "RF-75", "RF-76", "RF-77", "RF-78", "RF-79",
        "RNF-15",
    )  # fmt: skip
    assert set(REQUISITOS_S2) <= set(requisitos_exigidos(partes(), fases_hasta("0.7.0", "S2-0")))
    assert not set(REQUISITOS_S2) & set(requisitos_exigidos(partes(), fases_hasta("0.6.0", "S1-5")))


def test_cada_par_nombra_una_prueba_y_un_modulo_distintos_en_su_fase():
    assert len({(p.prueba, p.implementacion) for p in PARES_S2}) == len(PARES_S2)
    assert all(p.prueba != p.implementacion for p in PARES_S2)
    nuevos = {p.implementacion for p in PARES_S2}
    assert {
        "core/models/control.py",
        "core/budget/valuaciones.py",
        "core/budget/valor_ganado.py",
        "core/budget/recuperacion.py",
        "core/budget/decision.py",
        "ui/control.py",
    } <= nuevos


def test_rnf_15_deja_dos_cifras_en_la_fase_s2_4():
    assert {(c.ruta, c.clave, c.fase) for c in CIFRAS_S2} == {
        ("scripts/_salida_rnf15.json", "mediana_registro_s", "S2-4"),
        ("scripts/_salida_rnf15.json", "mediana_opciones_s", "S2-4"),
    }


def test_las_memorias_de_s2_se_ligan_al_primer_modulo_del_valor_ganado():
    assert MEMORIAS_S2 == {"control_ob_s2.md": ("--", "core/budget/valor_ganado.py")}


def test_r13_y_r14_deben_estar_en_la_fila_de_rf_74():
    ers = "| RF‑74 | El sistema ejecutará **R13 y R14** sobre las valuaciones | UC-19 |\n"
    assert evaluar_reglas_en_ers(ers)[0] is Estado.OK
    assert evaluar_reglas_en_ers(ers.replace("R14", "R15"))[0] is Estado.FALLA
    assert evaluar_reglas_en_ers("| RF-73 | otra |\n")[0] is Estado.FALLA
    assert evaluar_reglas_en_ers(None)[0] is Estado.PENDIENTE


def test_los_tres_expedientes_se_exigen_como_encabezados():
    texto = "\n".join(f"## {e} Titulo\ntexto" for e in EXPEDIENTES)
    assert evaluar_expedientes(texto)[0] is Estado.OK
    assert evaluar_expedientes(texto.replace("## SL-E6", "texto SL-E6"))[0] is Estado.FALLA
    assert "SL-E6" in evaluar_expedientes(texto.replace("## SL-E6", "texto"))[1]
    assert evaluar_expedientes(None)[0] is Estado.PENDIENTE


@pytest.mark.parametrize(
    ("existe", "diff", "estado"),
    [
        (False, None, Estado.PENDIENTE),
        (True, None, Estado.PENDIENTE),
        (True, "", Estado.OK),
        (True, " \n", Estado.OK),
        (True, " tests/fixtures/memorias/s1_reajuste.md | 2 +-", Estado.FALLA),
    ],
)
def test_las_memorias_de_s1_no_se_editan_desde_v0_6_0(existe, diff, estado):
    assert evaluar_memorias_de_s1(existe, diff)[0] is estado


def test_la_base_070_exige_su_ficha_s2_db_y_la_huella_de_cada_base(tmp_path: Path):
    carpeta = tmp_path / "v0_7_0"
    assert evaluar_base_070(carpeta)[0] is Estado.PENDIENTE
    carpeta.mkdir()
    (carpeta / "s2.db").write_bytes(b"x")
    ficha = {
        "version": "0.7.0",
        "etiqueta": "v0.7.0",
        "commit": "abc1234",
        "bases": {"s2.db": {"sha256_base": hashlib.sha256(b"x").hexdigest()}},
    }
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    assert evaluar_base_070(carpeta)[0] is Estado.OK
    (carpeta / "s2.db").write_bytes(b"y")
    estado, detalle = evaluar_base_070(carpeta)
    assert estado is Estado.FALLA and "s2.db" in detalle
    ficha["bases"] = {}
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    assert "no trae la base s2.db" in evaluar_base_070(carpeta)[1]
    ficha["version"] = "0.6.0"
    (carpeta / "ficha.json").write_text(json.dumps(ficha), encoding="utf-8")
    assert evaluar_base_070(carpeta)[0] is Estado.FALLA
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_meta_silice_s2.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'scripts.meta_silice_s2'`
```bash
git add tests/unit/test_meta_silice_s2.py
git commit -m "test(scripts): parte S2 de la meta unica en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
En `scripts/meta_silice.py`, la entrada nueva de `FASES` (RP7-12):
```diff
 FASES: dict[str, tuple[str, ...]] = {
     "0.6.0": ("T0", "S5-1", "S1-0", "S1-1", "S1-2", "S1-3", "S1-4", "S1-5"),
+    "0.7.0": ("S2-0", "S2-1", "S2-2", "S2-3", "S2-4", "S2-5"),
 }
```
```python
# scripts/meta_silice_s2.py
"""Parte S2 de la meta única de Sílice (spec S2 §8; plan 0.7.0, tarea 1).

`scripts/meta_silice.py` la descubre por su nombre. Con `--version 0.7.0 --hasta FASE` evalúa,
además de las siete comprobaciones comunes: C1, la presencia en la ERS de UC-19, UC-20, RF-72 a
RF-79 y RNF-15 (nunca un conteo, REQ-19); C3, el commit de la prueba de cada módulo nuevo de S2
anterior al de su código y el del expediente anterior al de las tablas; C6, que `medir_rnf15.py`
dejó su cifra (sin cifra no es OK: PRU-H21); y las comprobaciones propias:

* `S2-MEM`: la memoria OB-S2 y su XLSX existen y la memoria se versionó antes que
  `core/budget/valor_ganado.py`;
* `S2-REGLAS`: la ERS define R13 y R14 (en la fila de RF-74);
* `S2-EXPEDIENTES`: la bitácora trae SL-E4, SL-E5 y SL-E6;
* `S2-REG-S1`: las memorias de S1 no cambiaron desde `v0.6.0`;
* `S2-BASE-070`: la base de prueba de la 0.7.0 con su ficha (fase S2-5).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_sf import _ordenar_memoria, evaluar_s2_memorias  # noqa: E402
from scripts.meta_silice import (  # noqa: E402
    CifraDeTiempo,
    Comprobacion,
    Contexto,
    ParTDD,
    Parte,
    _git,
    _primer_commit,
    _referencia_existe,
)

REQUISITOS_S2: tuple[str, ...] = (
    "UC-19",
    "UC-20",
    *(f"RF-{numero}" for numero in range(72, 80)),
    "RNF-15",
)
MEMORIAS_S2: dict[str, tuple[str, ...]] = {
    "control_ob_s2.md": ("--", "core/budget/valor_ganado.py"),
}
XLSX_OB_S2 = "tests/fixtures/control/ob_s2.xlsx"
RUTA_MEMORIAS = RAIZ / "tests" / "fixtures" / "memorias"
RUTA_EXPEDIENTES = RAIZ / "docs" / "bitacora" / "2026-10-silice-s2-expedientes.md"
CARPETA_BASE_070 = RAIZ / "tests" / "fixtures" / "bases" / "v0_7_0"
ETIQUETA_S1 = "v0.6.0"
MEMORIAS_DE_S1 = (
    "tests/fixtures/memorias/s1_conversion.md",
    "tests/fixtures/memorias/s1_precios_empresa.md",
    "tests/fixtures/memorias/s1_reajuste.md",
    "tests/fixtures/memorias/s1_reajuste_por_partida.md",
)
EXPEDIENTES = ("SL-E4", "SL-E5", "SL-E6")
GUION = "[-‑]"

#: Prueba -> implementación, con la fase en que arranca cada par (C3 de la meta).
PARES_S2: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_meta_silice_s2.py", "scripts/meta_silice_s2.py", "S2-0"),
    ParTDD("docs/bitacora/2026-10-silice-s2-expedientes.md", "core/models/control.py", "S2-1"),
    ParTDD(
        "tests/integration/test_migracion_s2.py",
        "migraciones/caso/versions/caso_0005_s2_valuaciones.py",
        "S2-1",
    ),
    ParTDD("tests/unit/test_calendario.py", "core/budget/calendario.py", "S2-1"),
    ParTDD("tests/unit/test_r13_r14.py", "core/verification/valuaciones.py", "S2-1"),
    ParTDD("tests/integration/test_valuaciones.py", "core/budget/valuaciones.py", "S2-1"),
    ParTDD("tests/integration/test_importar_valuaciones.py", "core/budget/valuaciones.py", "S2-1"),
    ParTDD("tests/integration/test_ejecutado_por_periodo.py", "core/budget/puente.py", "S2-1"),
    ParTDD("tests/unit/test_valor_ganado.py", "core/budget/valor_ganado.py", "S2-2"),
    ParTDD("tests/unit/test_reproyeccion.py", "core/budget/valor_ganado.py", "S2-2"),
    ParTDD("tests/unit/test_alertas.py", "core/budget/valor_ganado.py", "S2-2"),
    ParTDD("tests/unit/test_pe_proyectado.py", "core/budget/valor_ganado.py", "S2-2"),
    ParTDD("tests/integration/test_control.py", "core/budget/control.py", "S2-2"),
    ParTDD("tests/unit/test_generar_obra_control.py", "scripts/generar_obra_control.py", "S2-2"),
    ParTDD("tests/integration/test_reajuste_reconocido.py", "core/budget/control.py", "S2-2"),
    ParTDD("tests/unit/test_recuperacion.py", "core/budget/recuperacion.py", "S2-3"),
    ParTDD("tests/integration/test_decision_crea_version.py", "core/budget/decision.py", "S2-3"),
    ParTDD(
        "tests/integration/test_migracion_s2.py",
        "migraciones/caso/versions/caso_0006_s2_decision.py",
        "S2-3",
    ),
    ParTDD("tests/integration/test_ui_control.py", "ui/control.py", "S2-4"),
    ParTDD("tests/unit/test_ui_pagina_control.py", "ui/paginas/control.py", "S2-4"),
    ParTDD("tests/unit/test_medir_rnf15.py", "scripts/medir_rnf15.py", "S2-4"),
)
CIFRAS_S2: tuple[CifraDeTiempo, ...] = (
    CifraDeTiempo(
        "RNF-15 (valuacion a reproyeccion)",
        "scripts/_salida_rnf15.json",
        "mediana_registro_s",
        "uv run python scripts/medir_rnf15.py",
        "S2-4",
    ),
    CifraDeTiempo(
        "RNF-15 (cuatro opciones)",
        "scripts/_salida_rnf15.json",
        "mediana_opciones_s",
        "uv run python scripts/medir_rnf15.py",
        "S2-4",
    ),
)


def evaluar_reglas_en_ers(texto_ers: str | None) -> tuple[Estado, str]:
    """S2-REGLAS: la fila de RF-74 de la ERS nombra R13 y R14 (las reglas externas de S2)."""
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    fila = re.search(rf"^\|\s*RF{GUION}74\s*\|[^\n]*", texto_ers, re.MULTILINE)
    if fila is None:
        return Estado.FALLA, "la ERS no define RF-74"
    faltan = [regla for regla in ("R13", "R14") if regla not in fila.group(0)]
    if faltan:
        return Estado.FALLA, "la fila de RF-74 no nombra " + ", ".join(faltan)
    return Estado.OK, "RF-74 define R13 y R14 en la ERS"


def evaluar_expedientes(texto: str | None) -> tuple[Estado, str]:
    """S2-EXPEDIENTES: la bitácora tiene un encabezado por expediente de `core/` de S2."""
    if texto is None:
        return Estado.PENDIENTE, "falta docs/bitacora/2026-10-silice-s2-expedientes.md"
    faltan = [
        e
        for e in EXPEDIENTES
        if not re.search(rf"^#{{2,4}}\s+{e.replace('-', GUION)}\b", texto, re.MULTILINE)
    ]
    if faltan:
        return Estado.FALLA, "la bitacora no trae el expediente " + ", ".join(faltan)
    return Estado.OK, "expedientes escritos: " + ", ".join(EXPEDIENTES)


def evaluar_memorias_de_s1(existe_etiqueta: bool, diff: str | None) -> tuple[Estado, str]:
    """S2-REG-S1: `git diff v0.6.0..HEAD` vacío sobre las cuatro memorias de S1 (no se editan)."""
    if not existe_etiqueta:
        return Estado.PENDIENTE, f"falta la etiqueta {ETIQUETA_S1}: S1 aun no se cerro"
    if diff is None:
        return Estado.PENDIENTE, "git diff no devolvio evidencia"
    if diff.strip():
        return Estado.FALLA, "las memorias de S1 cambiaron desde v0.6.0:\n" + diff.strip()
    return Estado.OK, f"las memorias de S1 no cambiaron desde {ETIQUETA_S1}"


def evaluar_base_070(carpeta: Path) -> tuple[Estado, str]:
    """S2-BASE-070: `ficha.json` de la etiqueta v0.7.0 y la huella SHA-256 de cada base."""
    ruta_ficha = carpeta / "ficha.json"
    if not ruta_ficha.is_file():
        return Estado.PENDIENTE, "la base de prueba 0.7.0 se genera desde la etiqueta v0.7.0"
    ficha = json.loads(ruta_ficha.read_text(encoding="utf-8"))
    if (ficha.get("version"), ficha.get("etiqueta")) != ("0.7.0", "v0.7.0"):
        return Estado.FALLA, f"la ficha dice {ficha.get('version')!r} / {ficha.get('etiqueta')!r}"
    bases = ficha.get("bases") or {}
    if "s2.db" not in bases:
        return Estado.FALLA, "la ficha no trae la base s2.db (OB-S2 con su decision)"
    distintas = [
        nombre
        for nombre, datos in sorted(bases.items())
        if not (carpeta / nombre).is_file()
        or hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest() != datos["sha256_base"]
    ]
    if distintas:
        return Estado.FALLA, "bases ausentes o distintas de su ficha: " + ", ".join(distintas)
    return Estado.OK, "base de prueba 0.7.0 con ficha: " + ", ".join(sorted(bases))


def _orden_memoria(memoria: str, criterio: tuple[str, ...]) -> bool | None:
    """Antes de que exista el código, basta que la memoria esté versionada."""
    if not (RAIZ / criterio[-1]).exists():
        return True if _primer_commit(f"tests/fixtures/memorias/{memoria}") else None
    return _ordenar_memoria(memoria, criterio)


def _memorias(_ctx: Contexto) -> tuple[Estado, str]:
    presentes = {m: (RUTA_MEMORIAS / m).is_file() for m in MEMORIAS_S2}
    presentes[Path(XLSX_OB_S2).name] = (RAIZ / XLSX_OB_S2).is_file()
    antes = {m: _orden_memoria(m, c) for m, c in MEMORIAS_S2.items()}
    antes[Path(XLSX_OB_S2).name] = True if presentes[Path(XLSX_OB_S2).name] else None
    codigo = any((RAIZ / c[-1]).exists() for c in MEMORIAS_S2.values())
    return evaluar_s2_memorias(presentes, antes, codigo_existe=codigo)


def _reglas(_ctx: Contexto) -> tuple[Estado, str]:
    ers = RAIZ / "docs" / "ERS.md"
    return evaluar_reglas_en_ers(ers.read_text(encoding="utf-8") if ers.is_file() else None)


def _expedientes(_ctx: Contexto) -> tuple[Estado, str]:
    existe = RUTA_EXPEDIENTES.is_file()
    return evaluar_expedientes(RUTA_EXPEDIENTES.read_text(encoding="utf-8") if existe else None)


def _memorias_de_s1(_ctx: Contexto) -> tuple[Estado, str]:
    if not _referencia_existe(ETIQUETA_S1):
        return evaluar_memorias_de_s1(False, None)
    resultado = _git("diff", "--stat", f"{ETIQUETA_S1}..HEAD", "--", *MEMORIAS_DE_S1)
    diff = resultado.stdout if resultado is not None and resultado.returncode == 0 else None
    return evaluar_memorias_de_s1(True, diff)


def _base_070(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_base_070(CARPETA_BASE_070)


PARTE = Parte(
    nombre="S2 presupuesto vivo: valuaciones, valor ganado, alertas y recuperacion",
    requisitos={"S2-0": REQUISITOS_S2},
    pares_tdd=PARES_S2,
    cifras=CIFRAS_S2,
    comprobaciones=(
        Comprobacion("S2-MEM", "Memoria OB-S2 y su XLSX antes del codigo", "S2-0", _memorias),
        Comprobacion("S2-REGLAS", "La ERS define R13 y R14", "S2-0", _reglas),
        Comprobacion("S2-EXPEDIENTES", "Expedientes SL-E4 a SL-E6 escritos", "S2-0", _expedientes),
        Comprobacion("S2-REG-S1", "Memorias de S1 intactas desde v0.6.0", "S2-0", _memorias_de_s1),
        Comprobacion("S2-BASE-070", "Base de prueba 0.7.0 con su ficha", "S2-5", _base_070),
    ),
)
```
  `scripts/README.md`, una fila nueva tras la de `meta_sf.py`:
```markdown
| `meta_silice_s2.py` | las comprobaciones y requisitos de S2 (0.7.0): memoria OB‑S2, reglas R13/R14, expedientes SL‑E4 a SL‑E6, regresión de S1 y base de prueba | Sílice 0.7.0 |
```
  `.github/workflows/ci.yml`: junto al paso «Meta de Silice» de la 0.6.0 se agrega el de la 0.7.0 (en el orden de `FASES`; cada PR de S2 sube su `--hasta`):
```yaml
      - name: Meta de Silice 0.7.0
        run: uv run --no-sync python scripts/meta_silice.py --version 0.7.0 --hasta S2-0 --junit reporte-pruebas.xml
```
- [ ] **Paso 4: Correrla y ver el verde, y escribir los documentos**
Run: `uv run pytest tests/unit/test_meta_silice_s2.py tests/unit/test_scripts_documentados.py -v -W error` → todo verde (14 pruebas de la meta; la fila del README satisface `test_cada_script_tiene_su_fila_en_el_readme`).
  Documentos (se **copian** del spec S2, no se parafrasean; cada fila lleva sus columnas de prioridad, fase y criterio):
  1. `docs/ERS.md`, tras UC-18: **UC-19 — Registrar una valuación de obra** (spec S2 §3.1, líneas 98-121) y **UC-20 — Controlar el avance y recuperar un retraso** (§3.1, líneas 123-148), con el encabezado `#### UC‑19 — …` que reconoce la meta, y las enmiendas de UC-15 (variación de obra = edición de cantidad), UC-16 (PE de la versión + PE proyectado) y UC-18 (lo ejecutado viene de las valuaciones desde la 0.7.0; el paso 3f marca el exceso como R13 en lugar de rechazarlo).
  2. `docs/ERS.md` §3.2: **RF-72 a RF-79** (spec §3.2, líneas 156-163). La fila de **RF-74** nombra **R13 y R14** en su texto (`S2-REGLAS` lo lee); no se deja ninguna fila vacante.
  3. `docs/ERS.md` §3.3: **RNF-15** (spec §3.3, línea 169: 500 partidas, 52 períodos, 26 valuaciones; mediana ≤ 2 s en cada trabajo) y §3.4: **R13** (valuación dentro del presupuesto) y **R14** (fuente y fechas de la valuación), spec §3.4, líneas 171-202, como reglas externas que no entran a `REGLAS`.
  4. `docs/modelo_datos.md`: la sección **§2.6 Control de obra (S2)** con las nueve tablas (`linea_base_control`, `calendario_obra`, `parametros_control`, `valuacion`, `linea_valuacion`, `anulacion_valuacion`, `costo_real`, `cita_valuacion` y `decision_recuperacion`), copiada de spec §6.1 con `cita_valuacion` añadida (RP7-4).
  5. `docs/arquitectura.md`, vista de desarrollo: los módulos `core/models/control.py`, `core/budget/{calendario,valuaciones,puente,valor_ganado,control,recuperacion,decision}.py`, `core/verification/valuaciones.py`, `ui/control.py`, `ui/paginas/control.py`, y la flecha nueva «`core/budget` no importa `core/verification` para los tipos de valuación» (RP7-3). `NORMAS.md` §6 recibe los mismos nombres en el árbol de carpetas.
  6. `docs/plan_pruebas.md`: dos filas nuevas de matriz por paso, UC-19 y UC-20, con las pruebas de este plan (se completan en la tarea 15).
  7. `CHANGELOG.md`, bajo `## [Sin publicar]`: `- S2 (0.7.0 en construcción): especificación de valuaciones, valor ganado, alertas y recuperación; parte S2 de la meta.`
  8. `docs/bitacora/2026-10-silice-070.md`: encabezado de la versión, el plan (este archivo) y la lista de rulings RP7-1…RP7-21.
- [ ] **Paso 5: Commit**
```bash
git add scripts/meta_silice_s2.py scripts/meta_silice.py scripts/README.md .github/workflows/ci.yml docs/ERS.md docs/modelo_datos.md docs/arquitectura.md docs/plan_pruebas.md NORMAS.md CHANGELOG.md docs/bitacora/2026-10-silice-070.md
git commit -m "docs(ers): S2 con UC-19, UC-20, RF-72 a RF-79, RNF-15, R13 y R14; parte S2 de la meta" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 2: Memoria OB-S2 a mano, su XLSX y las fronteras

**Rama:** `inc/070-s2-0-docs`   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `tests/fixtures/memorias/control_ob_s2.md`, `tests/unit/test_memoria_ob_s2.py`, `tests/fixtures/control/ob_s2.xlsx` (binario, generado por el procedimiento del paso 3), `tests/fixtures/control_fronteras.py`
- Prueba: `tests/unit/test_memoria_ob_s2.py`

**Interfaces:**
- Consume: `core.contracts.apu` (`ComposicionAPU`, `LineaManoObra`, `ModalidadManoObra`), `tests.fixtures.caso_ti001` (la composición real de TI-001, de la 0.5.0), `tests.fixtures.memorias` (carpeta de oráculos).
- Produce: la memoria `control_ob_s2.md` (los números de S2 §7.1, a mano); `tests/fixtures/control/ob_s2.xlsx` (hojas `Valuaciones`, `Lineas`, `Costos`); en `control_fronteras.py` las variantes declaradas de otros dominios (TI-001 con el técnico a destajo; SIS-001 sin mano de obra), que usan T10 y T11.

- [ ] **Paso 1: Escribir la prueba que falla**
La prueba **rehace con `fractions.Fraction`** cada cifra de la memoria a partir de los datos crudos (independiente de `Decimal` y de todo el sistema): si la memoria se equivocara, esto lo dice antes de que ninguna función se compare con ella.
```python
# tests/unit/test_memoria_ob_s2.py
"""El oráculo de S2 (`tests/fixtures/memorias/control_ob_s2.md`): trae sus cifras literales y sus
cuentas se rehacen **con aritmética de `fractions.Fraction`**, independiente de `Decimal` y de todo
código del sistema, a partir de los datos crudos de la memoria. Si la memoria se equivocara, esta
prueba lo diría antes de que ninguna función se compare con ella.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

F = Fraction
MEMORIA = Path(__file__).resolve().parents[1] / "fixtures" / "memorias" / "control_ob_s2.md"
LITERALES = [
    "1 500,00", "1 200,00", "0,8000", "0,9375", "4 480,00", "4 266,67", "−480,00", "−60,00",
    "−20,00", "−410,00", "−70,00", "11,11", "21,67", "22,5", "2026-12-02", "75,90", "5 135,90",
    "6 019,66", "5 402,91", "5 610,00", "4 887,68", "95,17 %", "6 860,09", "5 985,37", "115,3125",
    "110,00", "165,3125", "50,00", "OB-002", "siete", "2 864,15",
]  # fmt: skip

# Datos crudos de la memoria §1 y §2.
Q = {"A": F(100), "B": F(200), "C": F(100)}
U = {"A": F(10), "B": F(5), "C": F(20)}
U_CORTE = {"A": F(10), "B": F(6), "C": F("22.10")}
QE = {"A": F(90), "B": F(60), "C": F(0)}
PLAN = {"A": (F(1, 2), F(1, 2), 0, 0), "B": (0, F(1, 2), F(1, 2), 0), "C": (0, 0, F(1, 2), F(1, 2))}
AC = F(1280)
VENTA = sum(Q[p] * U[p] for p in Q) * F("1.265")
CF = sum(Q[p] * U[p] for p in Q) * F("0.15")


def test_la_memoria_existe_y_trae_sus_cifras_literales():
    texto = MEMORIA.read_text(encoding="utf-8")
    faltan = [cifra for cifra in LITERALES if cifra not in texto]
    assert not faltan, f"la memoria no trae {faltan}"


def test_el_valor_ganado_rehecho_con_fracciones():
    bac = sum(Q[p] * U[p] for p in Q)
    pv = sum(Q[p] * U[p] * sum(PLAN[p][:2]) for p in Q)  # corte en el dia 10: 2 periodos terminados
    ev = sum(QE[p] * U[p] for p in Q)
    en_corte = sum(QE[p] * U_CORTE[p] for p in Q)
    cpic = en_corte / AC
    eac = AC + sum((Q[p] - QE[p]) * U_CORTE[p] for p in Q) / cpic
    assert (bac, pv, ev) == (4000, 1500, 1200)
    assert (ev / pv, ev / AC, cpic) == (F(4, 5), F(15, 16), F(63, 64))
    assert eac == 4480 and round(bac / (ev / AC), 2) == F("4266.67")
    precio = sum(QE[p] * (U[p] - U_CORTE[p]) for p in Q)
    consumo = en_corte - AC
    assert (precio, consumo, ev - AC) == (-60, -20, -80) and precio + consumo == ev - AC
    vac_precio = -sum(Q[p] * (U_CORTE[p] - U[p]) for p in Q)
    assert (vac_precio, bac - eac - vac_precio) == (-410, -70)


def test_el_punto_de_equilibrio_base_y_los_proyectados_rehechos_con_fracciones():
    def pe(cv, cf, v):
        return cf * v / (v - cv)

    assert round(pe(F(4000), CF, VENTA), 2) == F("2864.15")
    reajuste = 60 * (F("7.59") - F("6.325"))
    assert reajuste == F("75.90") and VENTA + reajuste == F("5135.90")
    casos = {
        "aceptar": (F(4480), F(30) * 23, F("6019.66"), F("5402.91")),
        "cuadrillas": (F(4600), F(30) * 17, F("5610.00"), F("4887.68")),
        "horas": (F("4595.3125"), F(30) * 21, F("6860.09"), F("5985.37")),
    }
    for nombre, (cv, cf, sin, con) in casos.items():
        assert round(pe(cv, cf, VENTA), 2) == sin, nombre
        assert round(pe(cv, cf, VENTA + reajuste), 2) == con, nombre
        minimo = cv + cf - VENTA  # reajuste necesario para que PE' <= V'
        assert (minimo <= reajuste) is (nombre == "cuadrillas"), nombre
    assert round(pe(F(4600), F(510), VENTA + reajuste) / (VENTA + reajuste) * 100, 2) == F("95.17")


@pytest.mark.parametrize(
    ("nombre", "rendimiento", "salario", "cuadrilla", "restante", "costo_dia"),
    [("B", 20, 5, 2, 140, 40), ("C", 10, 10, 4, 100, 80)],
)
def test_los_costos_de_cuadrillas_y_horas_extra_rehechos_con_fracciones(
    nombre, rendimiento, salario, cuadrilla, restante, costo_dia
):
    e = 1 + F(4, 5)
    assert (
        F(restante * costo_dia) * (2 - e) / (rendimiento * e)
        == {
            "B": F(1120, 36),
            "C": F(1600, 18),
        }[nombre]
    )
    m = 1 + F(2, 8) * F(4, 5)
    ot = F(2, 8) * F(3, 2) * salario * 7
    adicional = restante * (costo_dia + ot - costo_dia * m) / (rendimiento * m)
    assert round(adicional, 4) == {"B": F("29.8958"), "C": F("85.4167")}[nombre]
    assert cuadrilla > 0


def test_la_suma_de_los_adicionales_es_la_de_la_memoria():
    cuadrillas = F(1120, 36) + F(1600, 18)
    assert cuadrillas == 120
    m = 1 + F(2, 8) * F(4, 5)
    horas = sum(
        r * (cd + F(2, 8) * F(3, 2) * s * 7 - cd * m) / (rend * m)
        for r, cd, s, rend in ((140, 40, 5, 20), (100, 80, 10, 10))
    )
    assert horas == F("115.3125")
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_memoria_ob_s2.py -v -W error`
Esperado: FAIL con `FileNotFoundError` (la memoria `control_ob_s2.md` no existe todavía).
```bash
git add tests/unit/test_memoria_ob_s2.py
git commit -m "test(fixtures): oraculo de OB-S2 con fracciones, en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima (la memoria a mano, el XLSX y las fronteras)**
La memoria se escribe **antes** de que exista `core/budget/valor_ganado.py` (la meta `S2-MEM` lee el orden de los commits):
```markdown
# Memoria S2: la obra OB-S2 (oráculo de RF-72 a RF-79, spec S2 §7.1)

Escrita a mano **antes del código**, con cada paso intermedio; las pruebas comparan con esta memoria,
nunca con la salida de otra función del sistema. Todo es **ficticio y declarado** (NORMAS.md §1): la obra,
el inspector «Ing. Ficticio», las actas, los costos reales y el reajuste. Cuentas en `Decimal`, 28 dígitos,
`ROUND_HALF_EVEN`; se redondea solo al presentar.

## 1. Datos

Proyecto OB-S2, versión de contrato y línea base `OB-001`, perspectiva **costo**, moneda USD. Parámetros de
costo: FCAS 6,00, bono de alimentación 1,00, administración 0,15, utilidad 0,10 (PU = costo directo × 1,15 ×
1,10 = costo directo × 1,265). Calendario: inicio **lunes 2026-11-02**, períodos semanales de 5 días hábiles,
sin feriados: *D* = 20 días hábiles (4 semanas), término del plan base **viernes 2026-11-27**.

| Partida | Cantidad | Rend. *R* | Cuadrilla (obreros × sueldo) | Equipo (cant. × precio × dep.) | Material | Costo directo `u` |
|---|---|---|---|---|---|---|
| OB-A excavación (m3) | 100 | 10 m3/d | 4 × 3,00 = 12 | 1 × 120 × 0,10 = 12 | — | 10,00 |
| OB-B tubería (m) | 200 | 20 m/d | 2 × 2,50 = 5 | 1 × 30 × 0,10 = 3 | 3,00 | 5,00 |
| OB-C relleno (m3) | 100 | 10 m3/d | 4 × 2,50 = 10 | 1 × 60 × 0,10 = 6 | 12,00 | 20,00 |

`C_d` (costo diario de la cuadrilla y el equipo) = `S` × (1 + FCAS 6,00) + bono 1,00 × obreros + equipo:
A = 12 × 7 + 4 + 12 = **100**; B = 5 × 7 + 2 + 3 = **40**; C = 10 × 7 + 4 + 6 = **80**. Con `u = C_d / R + material`:
A = 100/10 = 10; B = 40/20 + 3 = 5; C = 80/10 + 12 = 20. `S`: A 12, B 5, C 10.

BAC = 100 × 10 + 200 × 5 + 100 × 20 = **4 000,00**; V = 4 000 × 1,265 = **5 060,00**; CV = 4 000; CF = CV × 0,15 =
**600,00**; PE base = CF × V / (V − CV) = 600 × 5 060 / 1 060 = **2 864,15** USD (56,60 %).

Plan de la línea base (fracción de cada partida por semana): A S1 0,5 · S2 0,5; B S2 0,5 · S3 0,5; C S3 0,5 · S4 0,5.
Precios del corte `u'` (el material de B pasa de 3,00 a 4,00 y el de C de 12,00 a 14,10): A 10,00; B 6,00; C 22,10.

## 2. Valuaciones y costos

V-01: 2026-11-02 a 11-06, fecha 11-09: A 40. V-02: 2026-11-09 a 11-13, fecha 11-16: A 50, B 60. Inspector «Ing. Ficticio».
Las dos **cuentan desde su registro** (RV-18, sin conformación). Costos reales: **1 280,00 USD**.
**Corte: viernes 2026-11-13** (día hábil 10, *c* = 2 períodos terminados).

## 3. Valor ganado al corte (§4.2)

| Resultado | Cuenta | Valor |
|---|---|---|
| PV | A 100 × 10 × 1 + B 200 × 5 × 0,5 + C 0 | **1 500,00** |
| EV | A 90 × 10 + B 60 × 5 | **1 200,00** |
| AC | costo real declarado | **1 280,00** |
| SV | 1 200 − 1 500 | **−300,00** |
| SPI | 1 200 / 1 500 | **0,8000** |
| CV | 1 200 − 1 280 | **−80,00** |
| CPI | 1 200 / 1 280 | **0,9375** |
| CPIc | (90 × 10 + 60 × 6) / 1 280 = 1 260 / 1 280 | **0,984375** |
| EAC (sistema) | 1 280 + (10 × 10 + 140 × 6 + 100 × 22,10) / 0,984375 = 1 280 + 3 150 / 0,984375 | **4 480,00** |
| EAC (índice) | 4 000 / 0,9375 | **4 266,67** |
| VAC | 4 000 − 4 480 | **−480,00** |
| Término (índice) | ⌈20 / 0,8⌉ = día hábil 25 | **2026-12-04** |

### Separación del desvío de control (§4.3)

Precio ΔP = Σ qe·(u − u') = 90 × (10 − 10) + 60 × (5 − 6) = **−60,00**. Consumo ΔC = Σ qe·u' − AC = 1 260 − 1 280 =
**−20,00**. CV = −60 − 20 = **−80,00** (la identidad es exacta). Al término: VAC_precio = −Σ q·(u' − u) = −(0 + 200 × 1 + 100 × 2,10) =
**−410,00**; VAC_consumo = −480 − (−410) = **−70,00**.

## 4. Reproyección al ritmo real (§4.4)

Índices por partida: A = 900 / 1 000 = **0,9**; B = 300 / 500 = **0,6**; C no tiene evidencia propia (PV = 0): el SPI global
**0,8**. Ritmo `r = s / n` con *n* = 2 períodos por partida: A 0,45; B 0,30; C 0,40. Pendiente: A 0,1; B 0,7; C 1.

**Plan reproyectado:** S1 A 0,4 · S2 A 0,5, B 0,3 · S3 A 0,1, B 0,3, C 0,4 · S4 B 0,3, C 0,4 · S5 B 0,1, C 0,2.

Fines (días hábiles): A (3 − 1) × 5 + (0,1 / 0,45) × 5 = **11,11**; B 4 × 5 + (0,1 / 0,3) × 5 = **21,67**; C 4 × 5 + (0,2 / 0,4) × 5 =
**22,5**. Término por el plan: ⌈22,5⌉ = día hábil 23 = **2026-12-02** (3 días hábiles tarde).

## 5. Lo ejecutado que S2 entrega a S1 (RF-72)

Cláusula ficticia: periodicidad mensual, mecanismo `comprobacion`. V-01 (*hasta* 11-06) y V-02 (*hasta* 11-13) caen en noviembre de 2026:
**A 90 y B 60**, C 0; la cantidad reajustable es la misma (ningún acumulado supera lo presupuestado). Con la valuación sembrada V-S
(B 150 más) B entrega cantidad 210 y reajustable 200, con aviso, y R13 da ERROR.

## 6. Reajuste reconocido (RV-12; §4.7)

Escenario **con reajuste**: un estudio de S1 guardado al corte (fecha de cálculo 2026-11-13), período noviembre, «parcial al corte» porque
noviembre no cierra (S1-R21), comprobación directa contra la versión revalorada: PU del contrato = `u` × 1,265: A 12,65; B 6,325. PU
comprobado = `u'` × 1,265: A 12,65; B 7,59. `Σ q_reajustable · (PU comprobado − PU contrato)` = 90 × 0,00 + 60 × 1,265 = **75,90**.
V' = 5 060,00 + 75,90 = **5 135,90**. La comprobación de toda la obra (410 × 1,265) **no** entra: incluye obra no ejecutada.
Escenario **sin reajuste**: ningún estudio guardado, V' = V = 5 060,00.

## 7. Alertas (iguales en los dos escenarios)

AL-1 ERROR (SPI 0,80 < 0,90); AL-2 ADVERTENCIA (CPI 0,9375 ≥ 0,90); AL-3 ERROR (3 días = 15 % de *D* > 10 %); AL-4 ERROR (el PE' de la
reproyección no se alcanza, con y sin el reajuste); AL-5 INFO (|ΔP| = 60 = 5 % de 1 200, frontera exacta).

## 8. Opciones de recuperación (§4.6)

`T*` = día 20; CF/D = 600 / 20 = 30 por día; `CV'` = 4 480 + ΔCD; `PE' = CF'·V' / (V' − CV')`.

| Opción | Detalle | Término | ΔCD | `CV'` | `CF'` | PE' sin reajuste (V' = 5 060,00) | PE' con reajuste (V' = 5 135,90) |
|---|---|---|---|---|---|---|---|
| Aceptar el retraso | — | día 23, 2026-12-02 | 0,00 | 4 480,00 | 690,00 | 6 019,66: no se alcanza | 5 402,91: no se alcanza |
| Más cuadrillas | B y C con *k* = 2, `E` = 1,8 | día 17, 2026-11-24 | 120,00 | 4 600,00 | 510,00 | 5 610,00: no se alcanza | **4 887,68 (95,17 %), se alcanza en S4** |
| Horas extra | `h` = 2 en B y C; B llega (19,72), C no (20,42) | día 21, 2026-11-30 | 115,3125 | 4 595,3125 | 630,00 | 6 860,09: no se alcanza | 5 985,37: no se alcanza |
| Partidas en paralelo | ninguna sin empezar con inicio > S3 | — | — | — | — | no aplica | no aplica |

Cuentas. Más cuadrillas: `E(2)` = 1 + 0,8 = 1,8; B: q_rest 140 × 40 × (2 − 1,8) / (20 × 1,8) = 31,11; C: 100 × 80 × 0,2 / (10 × 1,8) = 88,89; ΔCD = 120,00. Plan:
S3 B 0,54, C 0,72; S4 B 0,16, C 0,28 (B termina en 16,48 y C en 16,94 → día 17). Horas extra: `m` = 1 + (2/8) × 0,8 = 1,2; OT = (2/8) × 1,5 × S × 7:
B 13,125; C 26,25; ΔCD_B = 140 × (40 + 13,125 − 40 × 1,2) / (20 × 1,2) = 29,8958; ΔCD_C = 100 × (80 + 26,25 − 96) / (10 × 1,2) = 85,4167; total 115,3125. Con reajuste:
`V' − CV'` = 5 135,90 − 4 600,00 = 535,90 y PE' = 510 × 5 135,90 / 535,90 = 4 887,68 (95,17 % de V'); en la curva de `OB-002` el acumulado llega a 82 % en S3 y a 100 % en S4: se
ubica en **S4**. Horas extra: 540,5875 y 630 × 5 135,90 / 540,5875 = 5 985,37. Sin reajuste: 460,00 y 510 × 5 060 / 460 = 5 610,00; 464,6875 y 630 × 5 060 / 464,6875 = 6 860,09.
**Comprobación cruzada:** PE' ≤ V' equivale a V' ≥ CV' + CF', así que cada opción necesita un reajuste reconocido de al menos CV' + CF' − V: aceptar **110,00**; más cuadrillas **50,00**; horas extra
**165,3125**. Con 75,90 solo «más cuadrillas» lo supera; sin reajuste, ninguna.

## 9. Decisión «más cuadrillas»

Versión **`OB-002`** con motivo `recuperacion` y el plan S1 A 0,4 · S2 A 0,5, B 0,3 · S3 A 0,1, B 0,54, C 0,72 · S4 B 0,16, C 0,28. Un `RegistroCambio` (objeto `plan`) por cada
(período, partida) que cambió respecto del plan de la versión de origen: (S1, A) 0,5 → 0,4; (S2, B) 0,5 → 0,3; (S3, A) 0 → 0,1; (S3, B) 0,5 → 0,54; (S3, C) 0,5 → 0,72; (S4, B) 0 → 0,16; (S4, C) 0,5 →
0,28 (**siete**). R2 y R7 sin hallazgos; la línea base sigue en `OB-001`; el SPI al mismo corte sigue en 0,80.

## 10. Valuación sembrada V-S (para R13 y R14)

Número `V-03`, 2026-11-12 a 11-20, fecha 11-19, **sin inspector**; líneas: B 150 (acumulado 210 > 200), D 5 (no presupuestada), C 10 con fecha de medición 11-23. El corte de la prueba es 2026-11-20.
Conjunto **exacto** de seis hallazgos: R13 ERROR B (impacto **50,00** = 10 × 5,00); R13 ERROR D; R14 ERROR sin inspector; R14 ERROR fecha anterior a *hasta*; R14 ERROR solape con V-02; R14 ERROR medición
fuera del período.
```
  Las fronteras de otros dominios (spec §4.6, ARQ-H3). Ninguna partida de TI-001 ni de SIS-001 es de solo destajo o sin mano de obra tal cual, así que se siembra una **variante declarada** de una partida real, sin tocar la composición del caso:
```python
# tests/fixtures/control_fronteras.py
"""Partidas de otros dominios sin mano de obra a jornal (spec S2 §4.6, ARQ-H3).

Las opciones «más cuadrillas» y «horas extra» dividen por el rendimiento y escalan el jornal de la
cuadrilla: una partida solo a destajo o sin mano de obra no tiene nada que escalar y debe dar «no
aplica» sin dividir. Ninguna partida de TI-001 ni de SIS-001 lo es tal cual (todas pagan jornal),
así que cada una se siembra como **variante declarada** de una partida real del caso:

* TI-001: `TI-LAP` (laptop HP configurada) con el técnico pagado a destajo, 50 USD por unidad;
* SIS-001: el APU de un punto de función sin mano de obra (todo el costo sería de terceros).

Son datos ficticios y declarados (NORMAS.md §1): la composición real de esas partidas no se toca.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from core.contracts.apu import ComposicionAPU, LineaManoObra, ModalidadManoObra
from tests.fixtures import caso_ti001
from tests.fixtures import tarifas_sistemas as sis

D = Decimal
PARTIDA_TI001 = "TI-LAP"
PARTIDA_SIS001 = "SIS-FRONTERA-01"


def ti001_a_destajo() -> ComposicionAPU:
    """`TI-LAP` con la mano de obra a destajo: no hay jornal que escalar."""
    original = caso_ti001.COMPOSICIONES[PARTIDA_TI001]
    return replace(
        original,
        mano_obra=(
            LineaManoObra(
                "Tecnico a destajo (variante declarada)", D(1), D(50), ModalidadManoObra.DESTAJO
            ),
        ),
    )


def sis001_sin_mano_de_obra() -> ComposicionAPU:
    """El APU de un punto de función de SIS-001 sin mano de obra."""
    return replace(
        sis.composicion_para(PARTIDA_SIS001, "Punto de funcion sin mano de obra (variante)"),
        mano_obra=(),
    )
```
  El XLSX de §6.2 se genera una vez con este procedimiento y se versiona; T6 comprueba que `escribir_xlsx` lo regenera igual celda por celda:
```bash
uv run python - <<'EOF'
from pathlib import Path
import openpyxl

libro = openpyxl.Workbook()
hoja = libro.active
hoja.title = "Valuaciones"
for fila in [
    ["numero", "desde", "hasta", "fecha", "inspector"],
    ["V-01", "2026-11-02", "2026-11-06", "2026-11-09", "Ing. Ficticio"],
    ["V-02", "2026-11-09", "2026-11-13", "2026-11-16", "Ing. Ficticio"],
]:
    hoja.append(fila)
lineas = libro.create_sheet("Lineas")
for fila in [
    ["numero", "codigo_partida", "cantidad", "fecha_medicion", "observacion"],
    ["V-01", "OB-A", "40", "", ""],
    ["V-02", "OB-A", "50", "", ""],
    ["V-02", "OB-B", "60", "", ""],
]:
    lineas.append(fila)
costos = libro.create_sheet("Costos")
costos.append(["numero", "codigo_partida", "monto", "moneda", "fecha", "fuente"])
costos.append(["", "", "1280.00", "USD", "2026-11-13", "libro de obra ficticio"])
destino = Path("tests/fixtures/control/ob_s2.xlsx")
destino.parent.mkdir(parents=True, exist_ok=True)
libro.save(destino)
EOF
```
- [ ] **Paso 4: Correrla y ver el verde** (y la parte S2 de la meta)
Run: `uv run pytest tests/unit/test_memoria_ob_s2.py tests/unit/test_meta_silice_s2.py -v -W error` → verde.
Run: `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-0` → `S2-MEM` en OK (memoria y XLSX versionados, el código que rigen aún no existe).
- [ ] **Paso 5: Commit**
```bash
git add tests/fixtures/memorias/control_ob_s2.md tests/fixtures/control/ob_s2.xlsx tests/fixtures/control_fronteras.py
git commit -m "test(fixtures): memoria OB-S2 a mano, su XLSX y las fronteras de otros dominios" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 3: Expedientes SL-E4, SL-E5, SL-E6 y verificación de fuentes

**Rama:** `inc/070-s2-0-docs`   **Rol:** sf-ingeniero-nucleo (solo documentos)
**Archivos:**
- Crear: `docs/bitacora/2026-10-silice-s2-expedientes.md` (nace con los tres expedientes; cada rama de núcleo cita el suyo)
- Modificar: `docs/bitacora/2026-10-silice-070.md` (sección «Fuentes por verificar»)
- Prueba: `tests/unit/test_meta_silice_s2.py::test_los_tres_expedientes_se_exigen_como_encabezados` (ya escrita en T1) y el chequeo `S2-EXPEDIENTES` de la meta

**Interfaces:**
- Consume: `scripts.meta_silice_s2.evaluar_expedientes(texto: str | None) -> tuple[Estado, str]` (T1).
- Produce: tres encabezados `## SL‑E4`, `## SL‑E5` y `## SL‑E6` con su texto; la lista de fuentes por verificar.

- [ ] **Paso 1: La prueba que ya existe y debe fallar sobre el repositorio**
No hay prueba nueva: la fija T1 (`test_los_tres_expedientes_se_exigen_como_encabezados`), y la comprobación `S2-EXPEDIENTES` de la meta lee el archivo real.
- [ ] **Paso 2: Correr la meta y ver el rojo**
Run: `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-0`
Esperado: `S2-EXPEDIENTES` en PENDIENTE con `falta docs/bitacora/2026-10-silice-s2-expedientes.md`.
- [ ] **Paso 3: Escribir los expedientes** en `docs/bitacora/2026-10-silice-s2-expedientes.md`, con el método de C3/C5/C6 (problema, diseño, por qué es genérico, qué no toca, pruebas que lo fijan, impacto y costo si es erróneo). Las citas de pruebas son las de este plan:
````markdown
# Expedientes de la 0.7.0 (S2, presupuesto vivo): núcleo

**Fecha:** 2026-10-11 · **Plan:** `PLAN_SILICE_070.md` · **Spec:** `docs/especificaciones/2026-10-11-silice-s2-presupuesto-vivo-design.md` §5.4 · **Bitácora de la versión:** [2026-10-silice-070.md](2026-10-silice-070.md)

Tres expedientes, uno por rama de núcleo (`inc/070-s2-1-nucleo`, `inc/070-s2-2-nucleo`, `inc/070-s2-3-nucleo`), cada uno commiteado antes de su código y aprobado por el tutor antes de abrir la rama. `core/contracts/` no se toca. El método es el de los expedientes de la 0.6.0.

## SL‑E4 Valuaciones, línea base de control y su auditoría

**Problema.** Un presupuesto no dice qué se ejecutó de él: no hay dónde registrar cantidades ejecutadas por período, con fuente, ni nada que impida que lo ejecutado supere lo presupuestado sin una variación registrada (H‑D5, RF‑72 a RF‑74, principio 7).
**Diseño.** Nueve tablas aditivas en `core/models/control.py` (revisión `caso_0005_s2_valuaciones`); el calendario hábil (`core/budget/calendario.py`); los tipos y las reglas R13 y R14 en `core/verification/valuaciones.py`, **fuera de `REGLAS`** (reciben una instantánea de control con `habiles_entre` inyectado); el registro, la anulación, la instantánea y la importación de Excel en `core/budget/valuaciones.py`; el puente a S1 en `core/budget/puente.py` (`ejecutado_por_periodo`, `estudio_con_valuaciones`, tabla `cita_valuacion`). Las valuaciones y los costos reales son solo-agregar; una valuación registrada y no anulada cuenta desde su registro (RV‑18). La lectura de la instantánea trae la versión con cuatro consultas (`selectinload`) y no con unas tres por renglón (RP7‑9); se agrega al final de S2‑4, en su propia rama de núcleo, tras medir RNF‑15, con una prueba que cuenta sentencias; no cambia ningún resultado.
**Por qué es genérico.** Toda obra se valúa por cantidades de sus partidas, sea del dominio que sea; nada de lo anterior nombra una especialidad.
**Qué no toca.** Ninguna tabla existente gana columnas; ninguna lectura anterior cambia; R13 y R14 no entran a `REGLAS` ni al informe guardado (S2‑R13).
**Pruebas que lo fijan.** `tests/unit/test_calendario.py`; `tests/unit/test_r13_r14.py` (conjunto exacto de hallazgos de V‑S, SIS‑001 y fronteras); `tests/integration/test_valuaciones.py` (OB‑S2 a mano y por Excel; inmutabilidad; anulación); `tests/integration/test_importar_valuaciones.py` (Excel malformado se rechaza entero); `tests/integration/test_ejecutado_por_periodo.py` y `test_estudio_cita_valuaciones.py` (asignación por *hasta*, registradas no anuladas, reajustable con `min`, línea base invalidada por cambio de moneda); `tests/integration/test_migracion_s2.py` (una base de la 0.6.0 abre con las tablas de control).
**Impacto.** 8 tablas en `caso_0005` (las 7 del spec más `cita_valuacion`, RP7‑4); `calendario.py` entra aquí y no en SL‑E5 (RP7‑2). **Costo si es erróneo.** Una revisión de Alembic más (RV‑3); las severidades de R13 y R14 son parámetros.

## SL‑E5 Valor ganado, separación del desvío de control y reproyección

**Problema.** El presupuesto no dice cómo va la obra contra su plan ni cuánto del desvío es de plazo, de precio o de consumo (H‑D2, RF‑75 a RF‑77, aporte central del horizonte §5).
**Diseño.** `core/budget/valor_ganado.py` (funciones puras sobre `Presupuesto`, plan y valuaciones: PV, EV, AC, SV, CV, SPI, CPI, BAC, EAC por índice y por sistema, VAC; separación `CV = precio + consumo` exacta; reproyección por partida con el ritmo `r = s/n·mult`; alertas AL‑1 a AL‑6 con umbrales SUPUESTO_DECLARADO; `equilibrio_proyectado`); `core/budget/control.py` (orquesta instantánea, estado y precios del corte); `core/budget/puente.py` gana `reajuste_reconocido`; `core/budget/equilibrio.py` se refactoriza extrayendo `equilibrio(venta, costo_variable, costo_fijo, curva)` sin cambiar `punto_equilibrio`.
**Por qué es genérico.** Se calcula sobre `Presupuesto`, plan y valuaciones, sin conocer dominios.
**Qué no toca.** El resultado de `punto_equilibrio` (TI‑001 sigue en 28 586,76 USD, Día 6); ninguna tabla.
**Pruebas que lo fijan.** `tests/unit/test_valor_ganado.py` (OB‑S2, §7.1; la identidad de la separación); `tests/unit/test_equilibrio_extraido.py` (TI‑001 literal sin editar); `tests/unit/test_reproyeccion.py`, `test_alertas.py`, `test_pe_proyectado.py` (los dos escenarios, sin reajuste y con el reconocido; la obra «según el plan» da el PE de SF‑E3 con su misma ubicación); `tests/integration/test_control.py`, `test_reajuste_reconocido.py`.
**Impacto.** `equilibrio.py` se refactoriza sin cambiar su resultado; funciones puras nuevas. **Costo si es erróneo.** Si el tutor prefiere otra separación u otro EAC, cambian dos funciones puras y su memoria (S2‑R1, S2‑R11).

## SL‑E6 Opciones de recuperación y decisión

**Problema.** Ante un retraso, el sistema no dice qué cuesta recuperarlo ni deja decidir con el costo a la vista (H‑D2, RF‑78, RF‑79; horizonte §4).
**Diseño.** `core/budget/recuperacion.py` (puro): costo diario de la ruta, `E(k) = Σ η^(j−1)`, límites de la LOTTT (arts. 118, 173, 178, 182, a cotejar), las cuatro opciones; `core/budget/decision.py`: `aplicar_decision` crea la versión por `guardar_edicion(motivo="recuperacion")`, que pasa por el embudo único `guardar_presupuesto`, y guarda la decisión con la foto de lo que el usuario vio (`caso_0006_s2_decision`, tabla `decision_recuperacion`).
**Por qué es genérico.** El costo sale del rendimiento y la cuadrilla de cualquier APU; una partida sin jornal da «no aplica» sin dividir.
**Qué no toca.** `guardar_edicion` gana un parámetro con valor por defecto (`motivo: str = "edicion"`); `MOTIVOS_VERSION` gana un valor (`"recuperacion"`); no hay otro camino que cree versiones.
**Pruebas que lo fijan.** `tests/unit/test_recuperacion.py` (cuatro opciones de OB‑S2, límites de la LOTTT, monotonía, «no aplica» en TI‑001 y SIS‑001); `tests/integration/test_decision_crea_version.py` (siete registros de cambio, curva, línea base intacta, un solo paso por el embudo, `test_guardar_edicion_sin_motivo_sigue_siendo_edicion_y_rechaza_un_motivo_desconocido`).
**Impacto.** Un parámetro con defecto, un motivo más, una tabla. **Costo si es erróneo.** Cambiar `η`, `k_máx` o `a` es un parámetro; cambiar el modelo `E(k)` es una función pura (S2‑R5).
````
  En `docs/bitacora/2026-10-silice-070.md`, la sección «Fuentes por verificar» (la lista que recibe el verificador de hechos antes del cierre; hasta entonces las fórmulas son **definiciones del sistema**, S2‑R11): (1) las fórmulas de PV, EV, AC, SPI, CPI y EAC de la práctica de valor ganado (PMI, norma ANSI/EIA‑748 y la Guía de los fundamentos); (2) Lee (2022), sobre modelos de aceleración con rendimiento decreciente por cuadrillas; (3) LOTTT arts. 118, 173, 178 y 182 (jornada, horas extra, límites diarios y anuales); (4) LCP art. 134, ya verificado por S1. Cada una se anota «verificada»/«no verificada» con el hecho exacto que la sostiene.
- [ ] **Paso 4: Correr la meta y ver el verde**
Run: `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-0 --junit reporte-pruebas.xml` → `S2-EXPEDIENTES` en OK; `S2-MEM`, `S2-REGLAS` y `S2-REG-S1` en OK (`S2-REG-S1` queda PENDIENTE solo si la etiqueta `v0.6.0` aún no existe).
- [ ] **Paso 5: Commit**
```bash
git add docs/bitacora/2026-10-silice-s2-expedientes.md docs/bitacora/2026-10-silice-070.md
git commit -m "docs(bitacora): expedientes SL-E4, SL-E5 y SL-E6 de S2 antes del nucleo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS2-0 y foco de revisión de la fase

**Compuerta GS2-0** (se cruza al fusionar `inc/070-s2-0-docs`):
1. `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-0 --junit reporte-pruebas.xml` → todas las filas en OK, salvo `S2-REG-S1` si la etiqueta `v0.6.0` aún no existe (entonces PENDIENTE, nunca FALLA).
2. CI verde en Linux y Windows, `-W error`, cero omitidas.
3. `uv run pytest tests/unit/test_scripts_documentados.py tests/unit/test_meta_silice_s2.py tests/unit/test_memoria_ob_s2.py -v -W error` en verde.
4. Revisión de los encargos (requisitos: UC‑19/20, RF‑72 a RF‑79, RNF‑15, R13/R14 presentes y copiados; pruebas: la memoria se rehace con fracciones; arquitectura: los módulos nombrados) y **aval del tutor de SL‑E4, SL‑E5 y SL‑E6 antes de abrir `inc/070-s2-1-nucleo`**.
5. Compuerta anotada en `docs/bitacora/2026-10-silice-070.md` con la tabla literal de la meta.

**Foco de revisión de S2-0** (lo que el spec implica y ninguna prueba ejercita todavía; cada entrada con su prueba, añadida a la tarea dueña):
1. **La memoria de un valor ganado equivocada** no se detectaría si el sistema la reprodujera: `test_el_valor_ganado_rehecho_con_fracciones` recalcula cada cifra de la memoria con `Fraction` desde los datos crudos (Tarea 2).
2. **Una regla externa fuera de la ERS** no cuenta: `test_r13_y_r14_deben_estar_en_la_fila_de_rf_74` falla si la fila de RF‑74 no nombra R13 y R14 (Tarea 1).
3. **Un expediente tardío:** `test_los_tres_expedientes_se_exigen_como_encabezados` exige `SL‑E4`, `SL‑E5` y `SL‑E6` como encabezados antes de la fase de núcleo (Tarea 1 y 3).
4. **Una memoria de S1 editada** para que una cifra de S2 cuadre: `test_las_memorias_de_s1_no_se_editan_desde_v0_6_0` (Tarea 1).

---

# S2-1 — Valuaciones, línea base de control y su auditoría (rama `inc/070-s2-1-nucleo`, SL-E4)

Solo `core/`, `migraciones/`, `tests/` y `docs/`. Sale de `origin/main` con S2-0 fusionada y el aval del tutor de SL-E4.
Al terminar, un residente registra valuaciones (a mano o por Excel), R13 y R14 las auditan, el sistema entrega lo
ejecutado por período a S1 y el estudio de reajuste cita las valuaciones que usó.

### Tarea 4: SL-E4a — tablas, revisión `caso_0005` y calendario hábil

**Rama:** `inc/070-s2-1-nucleo` (solo `core/`, `migraciones/`, `tests/`, `docs/`; sale de `main` con S2-0 fusionada)   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/models/control.py`, `migraciones/caso/versions/caso_0005_s2_valuaciones.py`, `core/budget/calendario.py`, `tests/unit/test_calendario.py`, `tests/integration/test_migracion_s2.py`
- Modificar: `core/models/__init__.py:7-75` (importar de `core.models.control` y reexportar; ubicar por contenido)

**Interfaces:**
- Consume: `core.models.base.Base`, `core.models.tipos.DecimalExacto`; las tablas `proyecto` y `presupuesto` (FK); el head de Alembic `caso_0004_s1_reajuste`; de la sección B: `operacion.base_datos.preparar_base(ruta, destino=Destino.CASO, *, entorno=None)`, `leer_estado(ruta)`, `revision_head(Destino.CASO)`, `Destino`; `tests.fixtures.bases_prueba.copiar_base(version, nombre, destino)`, `ficha(version)`, `nombres(version)`, `diferencias_con_ficha(ruta, esperado)`.
- Produce:
- `core/models/control.py`:
  - `PERSPECTIVAS = ('costo', 'precio')`
  - `class LineaBaseControl [id: Mapped[int]; proyecto_id: Mapped[int]; presupuesto_id: Mapped[int]; desde: Mapped[date]; perspectiva: Mapped[str]; fuente: Mapped[str]; responsable: Mapped[str]; fecha_hora: Mapped[datetime]; calendario: Mapped[CalendarioObra]]`
  - `class CalendarioObra [linea_base_id: Mapped[int]; fecha_inicio: Mapped[date]; dias_por_periodo: Mapped[int]; feriados: Mapped[str]; linea_base: Mapped[LineaBaseControl]]`
  - `class ParametrosControl [proyecto_id: Mapped[int]; spi_error: Mapped[Decimal]; cpi_error: Mapped[Decimal]; retraso_error: Mapped[Decimal]; precio_info: Mapped[Decimal]; equilibrio_puntos: Mapped[Decimal]; eta_cuadrilla: Mapped[Decimal]; cuadrillas_max: Mapped[int]; eta_horas_extra: Mapped[Decimal]; horas_extra_dia: Mapped[Decimal]; recargo_horas_extra: Mapped[Decimal]; fcas_en_horas_extra: Mapped[bool]; penalizacion_diaria: Mapped[Decimal]; fuente_penalizacion: Mapped[str]]`
  - `class Valuacion [id: Mapped[int]; proyecto_id: Mapped[int]; numero: Mapped[str]; desde: Mapped[date]; hasta: Mapped[date]; fecha: Mapped[date | None]; inspector: Mapped[str]; origen: Mapped[str]; fuente: Mapped[str]; responsable: Mapped[str]; fecha_hora: Mapped[datetime]; lineas: Mapped[list[LineaValuacion]]; anulacion: Mapped[AnulacionValuacion | None]]`
  - `class LineaValuacion [id: Mapped[int]; valuacion_id: Mapped[int]; codigo_partida: Mapped[str]; cantidad: Mapped[Decimal]; fecha_medicion: Mapped[date | None]; observacion: Mapped[str]; valuacion: Mapped[Valuacion]]`
  - `class AnulacionValuacion [valuacion_id: Mapped[int]; motivo: Mapped[str]; responsable: Mapped[str]; fecha_hora: Mapped[datetime]; valuacion: Mapped[Valuacion]]`
  - `class CostoReal [id: Mapped[int]; proyecto_id: Mapped[int]; valuacion_id: Mapped[int | None]; codigo_partida: Mapped[str | None]; monto: Mapped[Decimal]; moneda: Mapped[str]; fecha: Mapped[date]; fuente: Mapped[str]; responsable: Mapped[str]]`
  - `class CitaValuacion [id: Mapped[int]; periodo_id: Mapped[int]; valuacion_id: Mapped[int]]`
- `core/budget/calendario.py`:
  - `DIAS_DE_LA_SEMANA_HABILES = 5`
  - `def es_habil(dia: date, feriados: Collection[date]=()) -> bool`
  - `def dias_habiles(desde: date, hasta: date, feriados: Collection[date]=()) -> int`
  - `def numero_de_dia(inicio: date, fecha: date, feriados: Collection[date]=()) -> int`
  - `def dia_habil(inicio: date, numero: int, feriados: Collection[date]=()) -> date`
  - `def periodo_de(inicio: date, dias_por_periodo: int, fecha: date, feriados: Collection[date]=()) -> int`
  y la revisión `caso_0005_s2_valuaciones` (`down_revision = "caso_0004_s1_reajuste"`) con ocho tablas: `linea_base_control`, `calendario_obra`, `parametros_control`, `valuacion`, `linea_valuacion`, `anulacion_valuacion`, `costo_real`, `cita_valuacion`. `DecisionRecuperacion` (tabla `decision_recuperacion`) llega en la tarea 11 con `caso_0006`.

- [ ] **Paso 0: Expediente SL-E4** ya escrito y aprobado (tarea 3, `docs/bitacora/2026-10-silice-s2-expedientes.md`, encabezado `SL‑E4`). Antes de abrir la rama: `git log --oneline -- docs/bitacora/2026-10-silice-s2-expedientes.md` muestra su commit en `main`, y el visto bueno del tutor está anotado en `docs/bitacora/2026-10-silice-070.md`. Sin ambos, la tarea no empieza.
- [ ] **Paso 1: Escribir las pruebas que fallan**
  El calendario hábil (spec S2 §4.1; lunes a viernes menos feriados declarados, S2-R9; el **día hábil 1** es el primer hábil en o después del inicio; el período *n* abarca los días `(n−1)·L+1 … n·L`):
```python
# tests/unit/test_calendario.py
"""SL-E4: el calendario de la obra (spec S2 §4.1, S2-R9): lunes a viernes menos feriados."""

from datetime import date

import pytest

from core.budget.calendario import dia_habil, dias_habiles, es_habil, numero_de_dia, periodo_de

LUNES = date(2026, 11, 2)  # inicio de OB-S2
FERIADOS = frozenset({date(2026, 11, 4)})  # un miercoles ficticio


def test_el_fin_de_semana_y_el_feriado_no_son_habiles():
    assert es_habil(date(2026, 11, 6))  # viernes
    assert not es_habil(date(2026, 11, 7))  # sabado
    assert not es_habil(date(2026, 11, 8))  # domingo
    assert es_habil(date(2026, 11, 4))
    assert not es_habil(date(2026, 11, 4), FERIADOS)


def test_cuatro_semanas_de_cinco_dias_son_veinte_dias_habiles():
    assert dias_habiles(LUNES, date(2026, 11, 27)) == 20
    assert dias_habiles(LUNES, date(2026, 11, 1)) == 0  # desde > hasta


def test_el_dia_habil_veinte_es_el_viernes_27_y_el_veintitres_el_2_de_diciembre():
    assert dia_habil(LUNES, 1) == LUNES
    assert dia_habil(LUNES, 20) == date(2026, 11, 27)
    assert dia_habil(LUNES, 23) == date(2026, 12, 2)
    assert dia_habil(LUNES, 25) == date(2026, 12, 4)


def test_un_feriado_corre_el_calendario_un_dia():
    assert dia_habil(LUNES, 3, FERIADOS) == date(2026, 11, 5)  # el 4 no cuenta
    assert numero_de_dia(LUNES, date(2026, 11, 5), FERIADOS) == 3


def test_el_fin_de_semana_pertenece_al_ultimo_dia_habil_anterior():
    assert numero_de_dia(LUNES, date(2026, 11, 7)) == 5
    assert numero_de_dia(LUNES, date(2026, 11, 8)) == 5
    assert numero_de_dia(LUNES, date(2026, 11, 9)) == 6


def test_el_inicio_en_sabado_arranca_el_lunes():
    sabado = date(2026, 10, 31)
    assert dia_habil(sabado, 1) == LUNES
    assert numero_de_dia(sabado, sabado) == 0


@pytest.mark.parametrize(
    ("fecha", "periodo"),
    [
        (date(2026, 11, 1), 0),  # antes del inicio
        (date(2026, 11, 2), 1),
        (date(2026, 11, 6), 1),  # ultimo dia del periodo 1
        (date(2026, 11, 9), 2),  # primer dia del periodo 2
        (date(2026, 11, 13), 2),
        (date(2026, 11, 27), 4),
        (date(2026, 12, 2), 5),  # pasa del plan
    ],
)
def test_periodo_de_con_semanas_de_cinco_dias(fecha, periodo):
    assert periodo_de(LUNES, 5, fecha) == periodo


def test_numeros_invalidos_se_rechazan():
    with pytest.raises(ValueError, match="1 o mayor"):
        dia_habil(LUNES, 0)
    with pytest.raises(ValueError, match="1 o mas"):
        periodo_de(LUNES, 0, LUNES)
```
  Las bases anteriores suben a `head` y ganan las tablas sin perder filas (S2 §6.1, SL-E4; RV-3). Esta prueba usa la API de la sección B y las bases de la 0.5.0 y la 0.6.0 versionadas; `TABLAS_DE_S2_3` queda vacío hasta la tarea 11:
```python
# tests/integration/test_migracion_s2.py
"""Bases anteriores (S2 §6.1, SL-E4): cada base de prueba de la 0.6.0 sube a `head` por
`preparar_base`, gana las tablas de control sin perder filas y recarga con el total y la huella del
informe de su ficha (sección B, RV-3). La prueba de deriva (RNF-20, `test_migraciones.py`) recorre
las revisiones `caso_0005_s2_valuaciones` y `caso_0006_s2_decision` sin cambios."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from tests.fixtures.bases_prueba import copiar_base, diferencias_con_ficha, ficha, nombres

TABLAS_DE_S2_1 = {
    "linea_base_control",
    "calendario_obra",
    "parametros_control",
    "valuacion",
    "linea_valuacion",
    "anulacion_valuacion",
    "costo_real",
    "cita_valuacion",
}
TABLAS_DE_S2_3: set[str] = set()


def _tablas(ruta: Path) -> set[str]:
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        return set(inspect(motor).get_table_names())
    finally:
        motor.dispose()


@pytest.mark.parametrize("nombre", nombres("0.6.0"))
def test_base_anterior_abre_con_tablas_de_control(tmp_path: Path, nombre: str) -> None:
    ruta = copiar_base("0.6.0", nombre, tmp_path / nombre)
    antes = _tablas(ruta)
    assert not antes & TABLAS_DE_S2_1  # una base de la 0.6.0 no las tiene
    preparar_base(ruta)
    assert (TABLAS_DE_S2_1 | TABLAS_DE_S2_3) <= _tablas(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert diferencias_con_ficha(ruta, ficha("0.6.0")["bases"][nombre]) == []


@pytest.mark.parametrize("nombre", nombres("0.5.0"))
def test_base_de_la_0_5_0_sube_hasta_las_tablas_de_control(tmp_path: Path, nombre: str) -> None:
    ruta = copiar_base("0.5.0", nombre, tmp_path / nombre)
    preparar_base(ruta)
    assert (TABLAS_DE_S2_1 | TABLAS_DE_S2_3) <= _tablas(ruta)
    assert diferencias_con_ficha(ruta, ficha("0.5.0")["bases"][nombre]) == []


def test_las_tablas_de_control_nacen_vacias(tmp_path: Path) -> None:
    ruta = copiar_base("0.6.0", "ti001.db", tmp_path / "ti001.db")
    preparar_base(ruta)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        with motor.connect() as conexion:
            for tabla in sorted(TABLAS_DE_S2_1 | TABLAS_DE_S2_3):
                filas = conexion.exec_driver_sql(f"SELECT COUNT(*) FROM {tabla}").scalar()
                assert filas == 0, tabla
    finally:
        motor.dispose()
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_calendario.py tests/integration/test_migracion_s2.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.budget.calendario'` (el calendario) y, en la migración, `assert not antes & TABLAS_DE_S2_1` en verde pero `assert (TABLAS_DE_S2_1 | TABLAS_DE_S2_3) <= _tablas(ruta)` en rojo (las tablas aún no existen).
```bash
git add tests/unit/test_calendario.py tests/integration/test_migracion_s2.py
git commit -m "test(core): calendario habil y migracion de las tablas de control en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
```python
# core/budget/calendario.py
"""SL-E4: el calendario de la obra (spec S2 §4.1). Funciones puras, sin base de datos.

Los días hábiles son lunes a viernes menos los feriados declarados (S2-R9, SUPUESTO_DECLARADO: la
LOTTT, art. 173, limita la jornada del trabajador a cinco días por semana, no la de la obra). El
**día hábil 1** es el primer día hábil que cae en la fecha de inicio o después. El período *n*
abarca los días hábiles `(n-1)·L + 1 ... n·L` desde el inicio, con `L` los días por período.
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import date, timedelta

__all__ = ["dia_habil", "dias_habiles", "es_habil", "numero_de_dia", "periodo_de"]

DIAS_DE_LA_SEMANA_HABILES = 5  # lunes (0) a viernes (4)


def es_habil(dia: date, feriados: Collection[date] = ()) -> bool:
    """True si `dia` es de lunes a viernes y no es feriado."""
    return dia.weekday() < DIAS_DE_LA_SEMANA_HABILES and dia not in feriados


def dias_habiles(desde: date, hasta: date, feriados: Collection[date] = ()) -> int:
    """Cuántos días hábiles hay en [desde, hasta], ambos incluidos; 0 si `desde` > `hasta`."""
    cuenta = 0
    dia = desde
    while dia <= hasta:
        if es_habil(dia, feriados):
            cuenta += 1
        dia += timedelta(days=1)
    return cuenta


def numero_de_dia(inicio: date, fecha: date, feriados: Collection[date] = ()) -> int:
    """El número de día hábil de `fecha`: los días hábiles de [inicio, fecha]. Antes de que
    empiece la obra (o de su primer día hábil) es 0; un sábado cuenta lo ya transcurrido."""
    return dias_habiles(inicio, fecha, feriados)


def dia_habil(inicio: date, numero: int, feriados: Collection[date] = ()) -> date:
    """La fecha del día hábil número `numero` (1 es el primer día hábil desde `inicio`).
    `ValueError` si `numero` es menor que 1."""
    if numero < 1:
        raise ValueError(f"el numero de dia habil debe ser 1 o mayor, no {numero}")
    dia = inicio
    cuenta = 0
    while True:
        if es_habil(dia, feriados):
            cuenta += 1
            if cuenta == numero:
                return dia
        dia += timedelta(days=1)


def periodo_de(
    inicio: date, dias_por_periodo: int, fecha: date, feriados: Collection[date] = ()
) -> int:
    """El período (1, 2, ...) que contiene `fecha`; 0 si la obra aún no empieza. Un fin de semana
    o un feriado pertenece al período del último día hábil que lo precede."""
    if dias_por_periodo < 1:
        raise ValueError(f"los dias por periodo deben ser 1 o mas, no {dias_por_periodo}")
    numero = numero_de_dia(inicio, fecha, feriados)
    return -(-numero // dias_por_periodo)
```
```python
# core/models/control.py
"""Tablas aditivas de Sílice S2 (spec S2 §6.1). Módulo propio, reexportado por `core.models`, para
no tocar `entidades.py` (M §3.2); cada fase de núcleo agrega aquí las suyas con su revisión de
Alembic en `migraciones/caso/versions/`. Ninguna altera una tabla existente (ruling SF3-E0).

`valuacion`, `linea_valuacion` y `anulacion_valuacion` son solo-agregar: ninguna función de `core`
emite `UPDATE` ni `DELETE` sobre ellas (S2-R10); la única tabla que se actualiza es
`parametros_control`, y cada cambio deja su `RegistroCambio` (objeto `parametro`).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base
from core.models.tipos import DecimalExacto

PERSPECTIVAS = ("costo", "precio")


class LineaBaseControl(Base):
    """SL-E4: la línea base de control (S2 §6.1). La vigente al corte es la de mayor `desde`
    menor o igual al corte; declarar otra es agregar una fila. Queda invalidada si la moneda de su
    versión ya no es la del proyecto: se calcula, no se escribe (RV-11)."""

    __tablename__ = "linea_base_control"
    __table_args__ = (Index("ix_linea_base_control_proyecto", "proyecto_id", "desde"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id", ondelete="CASCADE"))
    desde: Mapped[date] = mapped_column(Date)
    perspectiva: Mapped[str] = mapped_column(String(10))
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)

    calendario: Mapped[CalendarioObra] = relationship(
        back_populates="linea_base", uselist=False, cascade="all, delete-orphan"
    )


class CalendarioObra(Base):
    """SL-E4: fecha de inicio, días hábiles por período y feriados de una línea base."""

    __tablename__ = "calendario_obra"

    linea_base_id: Mapped[int] = mapped_column(
        ForeignKey("linea_base_control.id", ondelete="CASCADE"), primary_key=True
    )
    fecha_inicio: Mapped[date] = mapped_column(Date)
    dias_por_periodo: Mapped[int] = mapped_column(Integer)
    feriados: Mapped[str] = mapped_column(Text, default="[]")

    linea_base: Mapped[LineaBaseControl] = relationship(back_populates="calendario")


class ParametrosControl(Base):
    """SL-E4: umbrales de las alertas y supuestos de las opciones de un proyecto (S2 §4.5, §4.6).
    Sin fila rigen los valores por defecto de `core.budget.valor_ganado`. Todos son
    SUPUESTO_DECLARADO salvo `penalizacion_diaria`, que es un dato del contrato."""

    __tablename__ = "parametros_control"

    proyecto_id: Mapped[int] = mapped_column(
        ForeignKey("proyecto.id", ondelete="CASCADE"), primary_key=True
    )
    spi_error: Mapped[Decimal] = mapped_column(DecimalExacto)
    cpi_error: Mapped[Decimal] = mapped_column(DecimalExacto)
    retraso_error: Mapped[Decimal] = mapped_column(DecimalExacto)
    precio_info: Mapped[Decimal] = mapped_column(DecimalExacto)
    equilibrio_puntos: Mapped[Decimal] = mapped_column(DecimalExacto)
    eta_cuadrilla: Mapped[Decimal] = mapped_column(DecimalExacto)
    cuadrillas_max: Mapped[int] = mapped_column(Integer)
    eta_horas_extra: Mapped[Decimal] = mapped_column(DecimalExacto)
    horas_extra_dia: Mapped[Decimal] = mapped_column(DecimalExacto)
    recargo_horas_extra: Mapped[Decimal] = mapped_column(DecimalExacto)
    fcas_en_horas_extra: Mapped[bool] = mapped_column(Boolean)
    penalizacion_diaria: Mapped[Decimal] = mapped_column(DecimalExacto)
    fuente_penalizacion: Mapped[str] = mapped_column(String(300), default="")


class Valuacion(Base):
    """SL-E4: una valuación por cantidades ejecutadas. Cuenta desde su registro (`fecha_hora`)
    hasta que se anula (RV-18, S2-R14). El número y otros campos pueden faltar: R14 los marca."""

    __tablename__ = "valuacion"
    __table_args__ = (Index("ix_valuacion_proyecto", "proyecto_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    numero: Mapped[str] = mapped_column(String(40), default="")
    desde: Mapped[date] = mapped_column(Date)
    hasta: Mapped[date] = mapped_column(Date)
    fecha: Mapped[date | None] = mapped_column(Date, default=None)
    inspector: Mapped[str] = mapped_column(String(120), default="")
    origen: Mapped[str] = mapped_column(String(300))
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)

    lineas: Mapped[list[LineaValuacion]] = relationship(
        back_populates="valuacion", order_by="LineaValuacion.id", cascade="all, delete-orphan"
    )
    anulacion: Mapped[AnulacionValuacion | None] = relationship(
        back_populates="valuacion", uselist=False
    )


class LineaValuacion(Base):
    """SL-E4: la cantidad ejecutada de una partida en una valuación (del período, no acumulada)."""

    __tablename__ = "linea_valuacion"
    __table_args__ = (Index("ix_linea_valuacion_valuacion", "valuacion_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    valuacion_id: Mapped[int] = mapped_column(ForeignKey("valuacion.id", ondelete="CASCADE"))
    codigo_partida: Mapped[str] = mapped_column(String(40))
    cantidad: Mapped[Decimal] = mapped_column(DecimalExacto)
    fecha_medicion: Mapped[date | None] = mapped_column(Date, default=None)
    observacion: Mapped[str] = mapped_column(Text, default="")

    valuacion: Mapped[Valuacion] = relationship(back_populates="lineas")


class AnulacionValuacion(Base):
    """SL-E4: la anulación de una valuación. La anulada se conserva y deja de contar."""

    __tablename__ = "anulacion_valuacion"

    valuacion_id: Mapped[int] = mapped_column(
        ForeignKey("valuacion.id", ondelete="CASCADE"), primary_key=True
    )
    motivo: Mapped[str] = mapped_column(Text)
    responsable: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)

    valuacion: Mapped[Valuacion] = relationship(back_populates="anulacion")


class CostoReal(Base):
    """SL-E4: un costo real declarado. Se convierte con `tasa_aplicable(fecha)` de S1 al calcular;
    no se guarda el convertido."""

    __tablename__ = "costo_real"
    __table_args__ = (Index("ix_costo_real_proyecto", "proyecto_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    valuacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("valuacion.id", ondelete="SET NULL"), default=None
    )
    codigo_partida: Mapped[str | None] = mapped_column(String(40), default=None)
    monto: Mapped[Decimal] = mapped_column(DecimalExacto)
    moneda: Mapped[str] = mapped_column(String(10))
    fecha: Mapped[date] = mapped_column(Date)
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))


class CitaValuacion(Base):
    """SL-E4, puente a S1 (RV-11, S1 §8.6): las valuaciones que un período de un estudio de
    reajuste usó para su ejecutado. Es la revisión de `ejecutado_periodo` que S1 deja a S2, como
    tabla aparte (ruling RP7-4): una valuación entra entera en un solo período."""

    __tablename__ = "cita_valuacion"
    __table_args__ = (UniqueConstraint("periodo_id", "valuacion_id", name="uq_cita_valuacion"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo_reajuste.id", ondelete="CASCADE"))
    valuacion_id: Mapped[int] = mapped_column(ForeignKey("valuacion.id", ondelete="CASCADE"))
```
  `core/models/__init__.py` (importar y reexportar; `DecisionRecuperacion` entra con la tarea 11):
```diff
--- a/core/models/__init__.py
+++ b/core/models/__init__.py
@@ -5,6 +5,16 @@
 """
 
 from core.models.base import Base
+from core.models.control import (
+    AnulacionValuacion,
+    CalendarioObra,
+    CitaValuacion,
+    CostoReal,
+    LineaBaseControl,
+    LineaValuacion,
+    ParametrosControl,
+    Valuacion,
+)
 from core.models.entidades import (
     ALCANCE_GLOBAL,
     ALCANCE_PROYECTO,
@@ -56,12 +66,16 @@
     "ALCANCE_PROYECTO",
     "MOTIVOS_VERSION",
     "PREFIJO_CODIGO_INSUMO",
+    "AnulacionValuacion",
     "Base",
+    "CalendarioObra",
     "CambioPrecio",
+    "CitaValuacion",
     "ClausulaReajuste",
     "ComponenteClausula",
     "ComposicionAPU",
     "ComposicionVersion",
+    "CostoReal",
     "Cotizacion",
     "DecimalExacto",
     "DescarteVersion",
@@ -74,10 +88,13 @@
     "Insumo",
     "ItemComputo",
     "JustificacionRendimiento",
+    "LineaBaseControl",
     "LineaComposicionVersion",
+    "LineaValuacion",
     "ListaPrecios",
     "ListaPreciosOrigen",
     "MonedaProyecto",
+    "ParametrosControl",
     "Partida",
     "PartidaPresupuestada",
     "PeriodoReajuste",
@@ -93,5 +110,6 @@
     "SerieIndice",
     "TipoInsumo",
     "ValorIndice",
+    "Valuacion",
     "VersionOrigen",
 ]
```
  La revisión de Alembic, escrita a mano (no autogenerada) con el mismo DDL que el modelo:
```python
# migraciones/caso/versions/caso_0005_s2_valuaciones.py
"""S2-1 (SL-E4): línea base de control, valuaciones, costos incurridos y cita de valuaciones."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0005_s2_valuaciones"
down_revision = "caso_0004_s1_reajuste"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def upgrade() -> None:
    op.create_table(
        "linea_base_control",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "proyecto_id",
            sa.Integer,
            sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "presupuesto_id",
            sa.Integer,
            sa.ForeignKey("presupuesto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("perspectiva", sa.String(10), nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_linea_base_control_proyecto", "linea_base_control", ["proyecto_id", "desde"]
    )
    op.create_table(
        "calendario_obra",
        sa.Column(
            "linea_base_id",
            sa.Integer,
            sa.ForeignKey("linea_base_control.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("fecha_inicio", sa.Date, nullable=False),
        sa.Column("dias_por_periodo", sa.Integer, nullable=False),
        sa.Column("feriados", sa.Text, nullable=False),
    )
    op.create_table(
        "parametros_control",
        sa.Column(
            "proyecto_id",
            sa.Integer,
            sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("spi_error", DEC, nullable=False),
        sa.Column("cpi_error", DEC, nullable=False),
        sa.Column("retraso_error", DEC, nullable=False),
        sa.Column("precio_info", DEC, nullable=False),
        sa.Column("equilibrio_puntos", DEC, nullable=False),
        sa.Column("eta_cuadrilla", DEC, nullable=False),
        sa.Column("cuadrillas_max", sa.Integer, nullable=False),
        sa.Column("eta_horas_extra", DEC, nullable=False),
        sa.Column("horas_extra_dia", DEC, nullable=False),
        sa.Column("recargo_horas_extra", DEC, nullable=False),
        sa.Column("fcas_en_horas_extra", sa.Boolean, nullable=False),
        sa.Column("penalizacion_diaria", DEC, nullable=False),
        sa.Column("fuente_penalizacion", sa.String(300), nullable=False),
    )
    op.create_table(
        "valuacion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "proyecto_id",
            sa.Integer,
            sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("numero", sa.String(40), nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=False),
        sa.Column("fecha", sa.Date, nullable=True),
        sa.Column("inspector", sa.String(120), nullable=False),
        sa.Column("origen", sa.String(300), nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
    )
    op.create_index("ix_valuacion_proyecto", "valuacion", ["proyecto_id"])
    op.create_table(
        "linea_valuacion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "valuacion_id",
            sa.Integer,
            sa.ForeignKey("valuacion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("codigo_partida", sa.String(40), nullable=False),
        sa.Column("cantidad", DEC, nullable=False),
        sa.Column("fecha_medicion", sa.Date, nullable=True),
        sa.Column("observacion", sa.Text, nullable=False),
    )
    op.create_index("ix_linea_valuacion_valuacion", "linea_valuacion", ["valuacion_id"])
    op.create_table(
        "anulacion_valuacion",
        sa.Column(
            "valuacion_id",
            sa.Integer,
            sa.ForeignKey("valuacion.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("motivo", sa.Text, nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
    )
    op.create_table(
        "costo_real",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "proyecto_id",
            sa.Integer,
            sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "valuacion_id",
            sa.Integer,
            sa.ForeignKey("valuacion.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("codigo_partida", sa.String(40), nullable=True),
        sa.Column("monto", DEC, nullable=False),
        sa.Column("moneda", sa.String(10), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
    )
    op.create_index("ix_costo_real_proyecto", "costo_real", ["proyecto_id"])
    op.create_table(
        "cita_valuacion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "periodo_id",
            sa.Integer,
            sa.ForeignKey("periodo_reajuste.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "valuacion_id",
            sa.Integer,
            sa.ForeignKey("valuacion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("periodo_id", "valuacion_id", name="uq_cita_valuacion"),
    )


def downgrade() -> None:
    for tabla in (
        "cita_valuacion",
        "costo_real",
        "anulacion_valuacion",
        "linea_valuacion",
        "valuacion",
        "parametros_control",
        "calendario_obra",
        "linea_base_control",
    ):
        op.drop_table(tabla)
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_calendario.py tests/integration/test_migracion_s2.py -v -W error` → 14 pruebas del calendario en verde y las de migración en verde sobre las bases de la 0.5.0 y la 0.6.0.
Run: `uv run pytest tests/integration/test_migraciones.py tests/unit/test_arquitectura.py -q -W error` → verde: la prueba de deriva de la sección B no encuentra diferencia entre los modelos y la revisión `caso_0005_s2_valuaciones` (RNF-20).
Run: `uv run ruff check core/models/control.py core/models/__init__.py core/budget/calendario.py migraciones/caso/versions/caso_0005_s2_valuaciones.py tests/unit/test_calendario.py tests/integration/test_migracion_s2.py` y `uv run python scripts/guardia_nucleo.py --base origin/main`.
- [ ] **Paso 5: Commit**
```bash
git add core/models/control.py core/models/__init__.py core/budget/calendario.py migraciones/caso/versions/caso_0005_s2_valuaciones.py
git commit -m "feat(core): tablas de control de obra, revision caso_0005 y calendario habil" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 5: SL-E4b — R13, R14, registro, anulación e instantánea de control

**Rama:** `inc/070-s2-1-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/verification/valuaciones.py`, `core/budget/valuaciones.py`, `tests/fixtures/control_ob_s2.py`, `tests/unit/test_r13_r14.py`, `tests/integration/test_valuaciones.py`
- Modificar: `tests/integration/conftest.py` (después de la fixture `sesion`: `obra_sin_linea_base` y `obra`; ubicar por contenido)

**Interfaces:**
- Consume: de la tarea 4: `models.LineaBaseControl`, `models.CalendarioObra`, `models.ParametrosControl`, `models.Valuacion`, `models.LineaValuacion`, `models.AnulacionValuacion`, `models.CostoReal`, `core.budget.calendario.{dias_habiles, numero_de_dia, periodo_de}`; del núcleo existente: `core.budget.{crear_proyecto, elaborar, guardar_presupuesto}`, `core.budget.curva.PeriodoPlan`, `core.budget.moneda.moneda_del_proyecto(session, proyecto)`, `core.catalog.Catalogo`, `core.contracts.ParametrosCosto`, `core.verification.ReglaVerificacion`/`Hallazgo`, `core.budget.persistencia.cargar_presupuesto`.
- Produce:
- `core/verification/valuaciones.py`:
  - `CODIGO_R13 = 'R13'`
  - `CODIGO_R14 = 'R14'`
  - `class LineaValuacion [codigo_partida: str; cantidad: Decimal; fecha_medicion: date | None; observacion: str]`
  - `class Valuacion [id: int; numero: str; desde: date; hasta: date; fecha: date | None; inspector: str; lineas: tuple[LineaValuacion, ...]; origen: str; fuente: str; responsable: str; fecha_hora: datetime | None]`
  - `class PartidaBase [codigo: str; cantidad: Decimal; unitario: Decimal; origen_id: str; programada: bool]`
  - `class InstantaneaDeControl [corte: date; inicio: date; partidas: tuple[PartidaBase, ...]; valuaciones: tuple[Valuacion, ...]; habiles_entre: Callable[[date, date], int]]`
  - `class ValuacionDentroDelPresupuesto`
  - `class FuenteYFechasDeValuacion`
  - `def reglas_de_control(instantanea: InstantaneaDeControl) -> tuple[ReglaVerificacion, ...]`
- `core/budget/valuaciones.py`:
  - `ORIGEN_MANUAL = 'manual'`
  - `MENSAJE_INVALIDADA = 'linea base invalidada: declarela de nuevo'`
  - `class LineaBaseInvalidada`
  - `class Calendario [fecha_inicio: date; dias_por_periodo: int; feriados: tuple[date, ...]]`
  - `class LineaBase [id: int; proyecto: str; version: str; desde: date; perspectiva: str; fuente: str; responsable: str; calendario: Calendario; fecha_hora: datetime | None]`
  - `class CostoReal [id: int; monto: Decimal; moneda: str; fecha: date; fuente: str; responsable: str; codigo_partida: str | None; valuacion_id: int | None]`
  - `class InstantaneaControl [proyecto: str; corte: date; linea_base: LineaBase; presupuesto: Presupuesto; plan: tuple[PeriodoPlan, ...]; parametros_costo: ParametrosCosto; moneda: str; valuaciones: tuple[Valuacion, ...]; costos: tuple[CostoReal, ...]]`
  - `def registrar_linea_base(session: Session, proyecto_nombre: str, codigo_version: str, *, desde: date, perspectiva: str, calendario: Calendario, fuente: str, responsable: str, ahora: datetime | None=None) -> models.LineaBaseControl`
  - `def registrar_valuacion(session: Session, proyecto_nombre: str, *, numero: str, desde: date, hasta: date, fecha: date | None, inspector: str, lineas: Sequence[LineaValuacion | tuple], fuente: str, responsable: str, origen: str=ORIGEN_MANUAL, ahora: datetime | None=None) -> models.Valuacion`
  - `def anular_valuacion(session: Session, valuacion_id: int, *, motivo: str, responsable: str, ahora: datetime | None=None) -> models.AnulacionValuacion`
  - `def registrar_costo(session: Session, proyecto_nombre: str, *, monto: Decimal, moneda: str, fecha: date, fuente: str, responsable: str, codigo_partida: str | None=None, valuacion_id: int | None=None) -> models.CostoReal`
  - `def valuaciones_registradas(session: Session, proyecto_nombre: str, *, con_anuladas: bool=False) -> list[Valuacion]`
  - `def instantanea_control(session: Session, proyecto_nombre: str, *, catalogo: Catalogo, corte: date | None=None) -> InstantaneaControl`
  - `def dia_del_corte(instantanea: InstantaneaControl) -> int`
  - `TITULO_VALUACIONES = 'Valuaciones'`
  - `COLUMNAS_TABLA_VALUACIONES = ('Numero', 'Desde', 'Hasta', 'Fecha', 'Inspector', 'Partida', 'Cantidad', 'Fecha de medici`
  - `def tabla_valuaciones(valuaciones: Sequence[Valuacion], *, anuladas: Sequence[Valuacion]=(), estados: Mapping[str, str] | None=None) -> TablaExportable`
  - `def anexo_control(session: Session, proyecto_nombre: str) -> dict[str, object]`
  - `def linea_base_vigente(session: Session, proyecto_nombre: str, corte: date) -> models.LineaBaseControl | None`

- [ ] **Paso 0: Expediente SL-E4** (ver tarea 4, paso 0); la rama ya está abierta.
- [ ] **Paso 1: Escribir las pruebas que fallan**
  La obra OB-S2 de la memoria en código (la única copia de los datos, usada también por las tareas 7 a 14):
```python
# tests/fixtures/control_ob_s2.py
"""La obra OB-S2 (spec S2 §7.1): los datos de `tests/fixtures/memorias/control_ob_s2.md` en código.

Una excavación (A), una tubería (B) y un relleno (C) en USD, con administración 0,15, utilidad 0,10,
FCAS 6,00 y bono 1,00: el PU es el costo directo por 1,265. El plan son cuatro semanas de cinco días
hábiles desde el lunes 2026-11-02. **Datos ficticios** (NORMAS.md §1): el inspector, las actas y los
costos reales los inventa la memoria.

Los códigos de partida son `OB-A`, `OB-B`, `OB-C` y `OB-D` (esta última, para la valuación sembrada,
no está presupuestada). Este módulo es la única copia de los datos: lo usan las pruebas de
valuaciones, valor ganado, recuperación y la interfaz de control.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto
from core.budget.curva import PeriodoPlan
from core.budget.valuaciones import (
    Calendario,
    CostoReal,
    InstantaneaControl,
    LineaBase,
    registrar_costo,
    registrar_linea_base,
    registrar_valuacion,
)
from core.catalog import Catalogo
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.verification.valuaciones import LineaValuacion, Valuacion

D = Decimal
NOMBRE = "OB-S2"
CODIGO = "OB-001"
FECHA = date(2026, 11, 2)
MONEDA = "USD"
PARAMETROS = ParametrosCosto(D("6.00"), D("1.00"), D("0.15"), D("0.10"))
INICIO = date(2026, 11, 2)
CALENDARIO = Calendario(INICIO, 5)
CORTE = date(2026, 11, 13)
INSPECTOR = "Ing. Ficticio"
RESPONSABLE = "Residente Ficticio"
FUENTE = "acta ficticia de OB-S2 (NORMAS.md seccion 1)"
CARPETA = Path(__file__).resolve().parent / "control"
RUTA_XLSX = CARPETA / "ob_s2.xlsx"

#: (código, descripción, unidad, rendimiento, obreros, sueldo por obrero, equipo, material)
_DATOS = {
    "OB-A": ("Excavacion de zanja", "m3", D(10), (D(4), D("3.00")), (D(120), D("0.10")), None),
    "OB-B": ("Tuberia de drenaje", "m", D(20), (D(2), D("2.50")), (D(30), D("0.10")), D("3.00")),
    "OB-C": ("Relleno compactado", "m3", D(10), (D(4), D("2.50")), (D(60), D("0.10")), D("12.00")),
}
CANTIDADES = {"OB-A": D(100), "OB-B": D(200), "OB-C": D(100)}
#: Plan de la línea base: fracción de cada partida por semana (S2 §7.1).
PLAN: list[PeriodoPlan] = [
    ("Semana 1", (("OB-A", D("0.5")),)),
    ("Semana 2", (("OB-A", D("0.5")), ("OB-B", D("0.5")))),
    ("Semana 3", (("OB-B", D("0.5")), ("OB-C", D("0.5")))),
    ("Semana 4", (("OB-C", D("0.5")),)),
]
#: Unitarios del corte `u'` (costo directo): el material de B pasa de 3,00 a 4,00 y el de C de 12,00
#: a 14,10.
UNITARIOS_BASE = {"OB-A": D("10.00"), "OB-B": D("5.00"), "OB-C": D("20.00")}
UNITARIOS_DEL_CORTE = {"OB-A": D("10.00"), "OB-B": D("6.00"), "OB-C": D("22.10")}
COSTO_REAL = D("1280.00")


def precios_del_corte():
    """Los precios del corte de la memoria, por comprobación directa (importa S2-2 al llamarse)."""
    from core.budget.valor_ganado import PreciosDelCorte

    return PreciosDelCorte("comprobacion", "version revalorada ficticia", UNITARIOS_DEL_CORTE)


def composiciones(materiales: dict[str, D] | None = None) -> dict[str, ComposicionAPU]:
    """Los tres APU. `materiales` cambia el precio del material de una partida (la revaloración)."""
    precios = {"OB-B": D("3.00"), "OB-C": D("12.00"), **(materiales or {})}
    apus: dict[str, ComposicionAPU] = {}
    for codigo, (descripcion, unidad, rendimiento, obreros, equipo, material) in _DATOS.items():
        apus[codigo] = ComposicionAPU(
            codigo,
            descripcion,
            unidad,
            rendimiento,
            materiales=()
            if material is None
            else (LineaMaterial(f"Material de {descripcion}", unidad, D(1), precios[codigo]),),
            equipos=(LineaEquipo(f"Equipo de {descripcion}", D(1), equipo[0], equipo[1]),),
            mano_obra=(LineaManoObra(f"Cuadrilla de {descripcion}", obreros[0], obreros[1]),),
        )
    return apus


def items() -> list[ItemComputo]:
    return [
        ItemComputo(
            codigo,
            _DATOS[codigo][0],
            _DATOS[codigo][1],
            cantidad,
            f"memoria-ob-s2:{codigo}",
            OrigenTipo.MANUAL,
            Dominio.CIVIL,
        )
        for codigo, cantidad in CANTIDADES.items()
    ]


def elaborar_ob_s2(codigo: str = CODIGO, plan=PLAN):
    """El presupuesto OB-001 con su curva y su informe (puro: no toca la base)."""
    return elaborar(
        items(), composiciones(), PARAMETROS, codigo=codigo, fecha=FECHA, moneda=MONEDA, plan=plan
    )


def sembrar(sesion) -> models.Presupuesto:
    """El proyecto OB-S2 con la versión OB-001 guardada y su plan. No confirma."""
    lista = models.ListaPrecios(nombre="OB-S2 USD", moneda=MONEDA, fecha_vigencia=FECHA)
    sesion.add(lista)
    sesion.flush()
    catalogo = Catalogo(sesion)
    for apu in composiciones().values():
        catalogo.cargar_composicion(apu, lista, Dominio.CIVIL, FECHA, "memoria OB-S2")
    resultado = elaborar_ob_s2()
    proyecto = crear_proyecto(sesion, NOMBRE)
    return guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=proyecto,
        lista=lista,
        parametros=PARAMETROS,
        plan=PLAN,
    )


def declarar_linea_base(sesion, perspectiva: str = "costo", desde: date = INICIO):
    return registrar_linea_base(
        sesion,
        NOMBRE,
        CODIGO,
        desde=desde,
        perspectiva=perspectiva,
        calendario=CALENDARIO,
        fuente=FUENTE,
        responsable=RESPONSABLE,
    )


#: Las valuaciones de la memoria: V-01 y V-02 (registradas) y la sembrada V-S.
V01 = dict(
    numero="V-01",
    desde=date(2026, 11, 2),
    hasta=date(2026, 11, 6),
    fecha=date(2026, 11, 9),
    inspector=INSPECTOR,
    lineas=[LineaValuacion("OB-A", D(40))],
)
V02 = dict(
    numero="V-02",
    desde=date(2026, 11, 9),
    hasta=date(2026, 11, 13),
    fecha=date(2026, 11, 16),
    inspector=INSPECTOR,
    lineas=[LineaValuacion("OB-A", D(50)), LineaValuacion("OB-B", D(60))],
)
VS = dict(
    numero="V-03",
    desde=date(2026, 11, 12),
    hasta=date(2026, 11, 20),
    fecha=date(2026, 11, 19),
    inspector="",
    lineas=[
        LineaValuacion("OB-B", D(150)),
        LineaValuacion("OB-D", D(5)),
        LineaValuacion("OB-C", D(10), date(2026, 11, 23)),
    ],
)
CORTE_DE_VS = date(2026, 11, 20)


def registrar(sesion, datos: dict, **extra):
    return registrar_valuacion(
        sesion, NOMBRE, fuente=FUENTE, responsable=RESPONSABLE, **datos, **extra
    )


def registrar_v01_y_v02(sesion):
    """V-01 y V-02, registradas, y el costo real de la memoria (1 280,00 USD)."""
    primera = registrar(sesion, V01, ahora=datetime(2026, 11, 9, 9, 0))
    segunda = registrar(sesion, V02, ahora=datetime(2026, 11, 16, 9, 0))
    registrar_costo(
        sesion,
        NOMBRE,
        monto=COSTO_REAL,
        moneda=MONEDA,
        fecha=date(2026, 11, 13),
        fuente="libro de obra ficticio",
        responsable=RESPONSABLE,
    )
    return primera, segunda


def valuacion(datos: dict, id: int) -> Valuacion:
    """Una valuación de la memoria como objeto puro (sin base)."""
    return Valuacion(id=id, **datos)


def instantanea(
    valuaciones, *, corte: date = CORTE, perspectiva: str = "costo", costos=None
) -> InstantaneaControl:
    """La instantánea de control de OB-S2 sin base de datos (para las pruebas puras)."""
    resultado = elaborar_ob_s2()
    return InstantaneaControl(
        proyecto=NOMBRE,
        corte=corte,
        linea_base=LineaBase(
            1, NOMBRE, CODIGO, INICIO, perspectiva, FUENTE, RESPONSABLE, CALENDARIO
        ),
        presupuesto=resultado.presupuesto,
        plan=tuple(PLAN),
        parametros_costo=PARAMETROS,
        moneda=MONEDA,
        valuaciones=tuple(valuaciones),
        costos=tuple(
            costos
            if costos is not None
            else [CostoReal(1, COSTO_REAL, MONEDA, date(2026, 11, 13), "libro de obra ficticio")]
        ),
    )


def v01_v02() -> list[Valuacion]:
    return [valuacion(V01, 1), valuacion(V02, 2)]


def escribir_xlsx(ruta: Path, *, valuaciones=None, costos=True) -> Path:
    """Escribe el XLSX de valuaciones de §6.2 con V-01, V-02 (y el costo real de la memoria).

    Los números van como texto, que es lo exacto por construcción (`leer_tabla`); las fechas, en
    ISO. `valuaciones` permite escribir otras (por ejemplo V-S)."""
    import openpyxl

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Valuaciones"
    hoja.append(["numero", "desde", "hasta", "fecha", "inspector"])
    lineas = libro.create_sheet("Lineas")
    lineas.append(["numero", "codigo_partida", "cantidad", "fecha_medicion", "observacion"])
    for datos in valuaciones or (V01, V02):
        hoja.append(
            [
                datos["numero"],
                datos["desde"].isoformat(),
                datos["hasta"].isoformat(),
                "" if datos["fecha"] is None else datos["fecha"].isoformat(),
                datos["inspector"],
            ]
        )
        for linea in datos["lineas"]:
            medicion = linea.fecha_medicion
            lineas.append(
                [
                    datos["numero"],
                    linea.codigo_partida,
                    str(linea.cantidad),
                    "" if medicion is None else medicion.isoformat(),
                    linea.observacion,
                ]
            )
    if costos:
        hoja_costos = libro.create_sheet("Costos")
        hoja_costos.append(["numero", "codigo_partida", "monto", "moneda", "fecha", "fuente"])
        hoja_costos.append(
            ["", "", str(COSTO_REAL), MONEDA, "2026-11-13", "libro de obra ficticio"]
        )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta)
    return ruta
```
  Las fixtures de integración (`obra` hace `commit()` para que el `rollback` de `_escribir` no borre la siembra):
```diff
--- a/tests/integration/conftest.py
+++ b/tests/integration/conftest.py
@@ -127,2 +127,25 @@
         for item in items_auditados()
     ]
+
+
+@pytest.fixture
+def obra_sin_linea_base(motor):
+    """OB-S2 (S2 §7.1) en una base vacía: la versión OB-001 con su plan, sin línea base de control.
+
+    Datos ficticios (NORMAS.md §1). No confirma: la sesión se cierra con el motor."""
+    from tests.fixtures import control_ob_s2 as ob
+
+    with abrir_sesion(motor) as sesion:
+        ob.sembrar(sesion)
+        sesion.commit()  # un caso guardado: un `rollback` de la pantalla no lo deshace
+        yield sesion
+
+
+@pytest.fixture
+def obra(obra_sin_linea_base):
+    """OB-S2 con su línea base de control declarada (perspectiva costo, desde el 2026-11-02)."""
+    from tests.fixtures import control_ob_s2 as ob
+
+    ob.declarar_linea_base(obra_sin_linea_base)
+    obra_sin_linea_base.commit()
+    return obra_sin_linea_base
```
  R13 y R14 (spec S2 §3.4; conjunto exacto de hallazgos de la valuación sembrada V-S; SIS-001 y fronteras):
```python
# tests/unit/test_r13_r14.py
"""SL-E4: R13 y R14 (spec S2 §3.4, RF-74). Conjunto exacto de la valuación sembrada V-S de la
memoria `control_ob_s2.md`, cada frontera de §7.3 y R13 sobre SIS-001 (ARQ-H3). Puras: sin base."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.contracts.verificacion import Severidad
from core.verification import auditar
from core.verification.valuaciones import (
    InstantaneaDeControl,
    LineaValuacion,
    PartidaBase,
    Valuacion,
    reglas_de_control,
)
from tests.fixtures import control_ob_s2 as ob

D = Decimal
INICIO = date(2026, 11, 2)  # lunes
CORTE = date(2026, 11, 20)


def _habiles(a: date, b: date) -> int:
    dias = (a + timedelta(days=n) for n in range((b - a).days + 1))
    return sum(1 for dia in dias if dia.weekday() < 5)


def _hallazgos(valuaciones, *, corte=CORTE, partidas=None):
    instantanea = InstantaneaDeControl(
        corte=corte,
        inicio=INICIO,
        partidas=partidas or _partidas_de_ob_s2(),
        valuaciones=tuple(valuaciones),
        habiles_entre=_habiles,
    )
    informe = auditar(ob.elaborar_ob_s2().presupuesto, reglas_de_control(instantanea))
    return informe.hallazgos


def _partidas_de_ob_s2():
    presupuesto = ob.elaborar_ob_s2().presupuesto
    return tuple(
        PartidaBase(
            p.item.codigo_partida,
            p.item.cantidad,
            p.resultado.costo_directo,
            p.item.origen_id,
            True,
        )
        for p in presupuesto.partidas
    )


def _v(numero, desde, hasta, *, fecha=None, inspector="Ing. Ficticio", lineas=None, id=1):
    return Valuacion(
        id=id,
        numero=numero,
        desde=desde,
        hasta=hasta,
        fecha=hasta if fecha is None else fecha,
        inspector=inspector,
        lineas=tuple(lineas or [LineaValuacion("OB-A", D(1))]),
    )


def _de(regla, hallazgos):
    return [h for h in hallazgos if h.regla == regla]


def test_la_valuacion_sembrada_da_exactamente_los_seis_hallazgos_de_la_memoria():
    valuaciones = [ob.valuacion(ob.V01, 1), ob.valuacion(ob.V02, 2), ob.valuacion(ob.VS, 3)]
    hallazgos = _hallazgos(valuaciones)
    resumen = sorted((h.regla, h.severidad.name, h.origen_ids[0], h.impacto) for h in hallazgos)
    assert resumen == [
        ("R13", "ERROR", "valuacion:V-03:OB-B", D("50.00")),
        ("R13", "ERROR", "valuacion:V-03:OB-D", None),
        ("R14", "ERROR", "valuacion:V-03", None),
        ("R14", "ERROR", "valuacion:V-03", None),
        ("R14", "ERROR", "valuacion:V-03", None),
        ("R14", "ERROR", "valuacion:V-03:OB-C", None),
    ]
    textos = " | ".join(h.descripcion for h in _de("R14", hallazgos))
    for fragmento in (
        "no tiene inspector",
        "anterior a su fin",
        "se solapa",
        "fuera de su periodo",
    ):
        assert fragmento in textos
    exceso = _de("R13", hallazgos)[0]
    assert (exceso.valor_observado, exceso.valor_esperado) == (D(210), D(200))
    assert "memoria-ob-s2:OB-B" in exceso.origen_ids  # atribuye la partida (C5.1)


def test_las_dos_valuaciones_de_la_memoria_no_dan_hallazgos():
    assert _hallazgos(ob.v01_v02(), corte=ob.CORTE) == ()


def test_r13_el_acumulado_igual_a_lo_presupuestado_pasa_y_un_milesimo_mas_falla():
    pasa = _v("V-01", INICIO, date(2026, 11, 6), lineas=[LineaValuacion("OB-A", D(100))])
    falla = _v("V-01", INICIO, date(2026, 11, 6), lineas=[LineaValuacion("OB-A", D("100.001"))])
    assert _de("R13", _hallazgos([pasa])) == []
    (hallazgo,) = _de("R13", _hallazgos([falla]))
    assert hallazgo.impacto == D("0.001") * D(10)


def test_r13_el_exceso_se_suma_entre_valuaciones_y_el_impacto_es_el_total():
    primera = _v("V-01", INICIO, date(2026, 11, 6), lineas=[LineaValuacion("OB-A", D(80))])
    segunda = _v(
        "V-02", date(2026, 11, 9), date(2026, 11, 13), lineas=[LineaValuacion("OB-A", D(30))], id=2
    )
    tercera = _v(
        "V-03", date(2026, 11, 16), date(2026, 11, 20), lineas=[LineaValuacion("OB-A", D(5))], id=3
    )
    (hallazgo,) = _de("R13", _hallazgos([primera, segunda, tercera]))
    assert hallazgo.impacto == D(15) * D(10)  # 115 - 100, a 10,00 de costo directo
    assert hallazgo.origen_ids[0] == "valuacion:V-02:OB-A"  # la que cruza el limite


def test_r13_una_partida_presupuestada_que_el_plan_no_programa_es_advertencia():
    partidas = tuple(
        PartidaBase(p.codigo, p.cantidad, p.unitario, p.origen_id, p.codigo != "OB-C")
        for p in _partidas_de_ob_s2()
    )
    (hallazgo,) = _de("R13", _hallazgos([], partidas=partidas))
    assert hallazgo.severidad is Severidad.ADVERTENCIA
    assert "no la programa" in hallazgo.descripcion


@pytest.mark.parametrize(
    ("fecha", "falla"),
    [(date(2026, 11, 6), False), (date(2026, 11, 5), True)],
    ids=["fecha igual a hasta pasa", "un dia antes falla"],
)
def test_r14_la_fecha_de_la_valuacion_no_es_anterior_a_su_fin(fecha, falla):
    valuacion = _v("V-01", INICIO, date(2026, 11, 6), fecha=fecha)
    hallazgos = [h for h in _de("R14", _hallazgos([valuacion])) if "anterior" in h.descripcion]
    assert bool(hallazgos) is falla


@pytest.mark.parametrize(
    ("campo", "texto"),
    [("numero", "no tiene numero"), ("inspector", "no tiene inspector")],
)
def test_r14_sin_numero_o_sin_inspector_es_error(campo, texto):
    valuacion = _v("" if campo == "numero" else "V-01", INICIO, date(2026, 11, 6))
    if campo == "inspector":
        valuacion = _v("V-01", INICIO, date(2026, 11, 6), inspector="  ")
    (hallazgo,) = _de("R14", _hallazgos([valuacion]))
    assert hallazgo.severidad is Severidad.ERROR and texto in hallazgo.descripcion


def test_r14_sin_fecha_es_error_y_sin_numero_la_clave_es_el_id():
    sin_fecha = Valuacion(7, "", INICIO, date(2026, 11, 6), None, "Ing. Ficticio",
                          (LineaValuacion("OB-A", D(1)),))  # fmt: skip
    hallazgos = _de("R14", _hallazgos([sin_fecha]))
    assert sorted(h.descripcion.split(" no tiene ")[1] for h in hallazgos) == ["fecha", "numero"]
    assert all(h.origen_ids == ("valuacion:#7",) for h in hallazgos)


@pytest.mark.parametrize(
    ("hasta", "falla"),
    [(CORTE, False), (CORTE + timedelta(days=1), True)],
    ids=["hasta igual al corte pasa", "corte mas un dia falla"],
)
def test_r14_la_valuacion_no_termina_despues_del_corte(hasta, falla):
    valuacion = _v("V-01", date(2026, 11, 16), hasta)
    hallazgos = [
        h for h in _de("R14", _hallazgos([valuacion])) if "despues del corte" in h.descripcion
    ]
    assert bool(hallazgos) is falla


@pytest.mark.parametrize(
    ("desde", "falla"),
    [(INICIO, False), (INICIO - timedelta(days=1), True)],
    ids=["desde igual al inicio pasa", "inicio menos un dia falla"],
)
def test_r14_la_valuacion_no_empieza_antes_del_calendario(desde, falla):
    valuacion = _v("V-01", desde, date(2026, 11, 6))
    hallazgos = [
        h for h in _de("R14", _hallazgos([valuacion])) if "antes del inicio" in h.descripcion
    ]
    assert bool(hallazgos) is falla


def test_r14_desde_posterior_a_hasta_es_error():
    (hallazgo,) = [
        h
        for h in _de("R14", _hallazgos([_v("V-01", date(2026, 11, 9), date(2026, 11, 6))]))
        if "despues de su fin" in h.descripcion
    ]
    assert hallazgo.severidad is Severidad.ERROR


@pytest.mark.parametrize(
    ("desde_de_la_segunda", "solapa"),
    [(date(2026, 11, 7), False), (date(2026, 11, 6), True)],
    ids=["periodos contiguos pasan", "un dia de solape falla"],
)
def test_r14_periodos_solapados(desde_de_la_segunda, solapa):
    primera = _v("V-01", INICIO, date(2026, 11, 6))
    segunda = _v("V-02", desde_de_la_segunda, date(2026, 11, 13), id=2)
    hallazgos = [h for h in _de("R14", _hallazgos([primera, segunda])) if "solapa" in h.descripcion]
    assert bool(hallazgos) is solapa


def test_r14_numero_repetido_es_error():
    primera = _v("V-01", INICIO, date(2026, 11, 6))
    segunda = _v("V-01", date(2026, 11, 9), date(2026, 11, 13), id=2)
    (hallazgo,) = [
        h for h in _de("R14", _hallazgos([primera, segunda])) if "repetido" in h.descripcion
    ]
    assert hallazgo.severidad is Severidad.ERROR


@pytest.mark.parametrize(
    ("fecha_de_medicion", "falla"),
    [(date(2026, 11, 6), False), (date(2026, 11, 2), False), (date(2026, 11, 7), True)],
    ids=["en hasta pasa", "en desde pasa", "un dia despues falla"],
)
def test_r14_la_medicion_cae_dentro_del_periodo(fecha_de_medicion, falla):
    valuacion = _v(
        "V-01", INICIO, date(2026, 11, 6), lineas=[LineaValuacion("OB-A", D(1), fecha_de_medicion)]
    )
    hallazgos = [h for h in _de("R14", _hallazgos([valuacion])) if "medicion" in h.descripcion]
    assert bool(hallazgos) is falla


@pytest.mark.parametrize(
    ("segundo_numero", "advierte"),
    [("V-02", False), ("V-03", True)],
    ids=["V-01 y V-02 pasa", "V-01 y V-03 advierte"],
)
def test_r14_numeros_consecutivos_con_prefijo(segundo_numero, advierte):
    primera = _v("V-01", INICIO, date(2026, 11, 6))
    segunda = _v(segundo_numero, date(2026, 11, 9), date(2026, 11, 13), id=2)
    hallazgos = [
        h for h in _de("R14", _hallazgos([primera, segunda])) if "consecutivas" in h.descripcion
    ]
    assert bool(hallazgos) is advierte
    assert all(h.severidad is Severidad.ADVERTENCIA for h in hallazgos)


@pytest.mark.parametrize(
    ("desde_de_la_segunda", "hueco"),
    [(date(2026, 11, 9), False), (date(2026, 11, 10), True)],
    ids=["viernes a lunes no hay hueco", "martes deja un dia habil sin cubrir"],
)
def test_r14_hueco_de_dias_habiles_entre_valuaciones_consecutivas(desde_de_la_segunda, hueco):
    primera = _v("V-01", INICIO, date(2026, 11, 6))
    segunda = _v("V-02", desde_de_la_segunda, date(2026, 11, 13), id=2)
    hallazgos = [
        h for h in _de("R14", _hallazgos([primera, segunda])) if "sin cubrir" in h.descripcion
    ]
    assert bool(hallazgos) is hueco
    assert all(h.severidad is Severidad.INFO for h in hallazgos)


def test_r13_sirve_a_un_presupuesto_de_otro_dominio_sis_001():
    """ARQ-H3: R13 no conoce dominios; sobre SIS-001 da su conjunto exacto."""
    from core.budget import generar_presupuesto
    from scripts import seed_sistemas as sis

    presupuesto = generar_presupuesto(
        sis.items_sistemas(),
        sis.composiciones_sistemas(),
        sis.sis.PARAMETROS_SISTEMAS,
        codigo="SIS-001",
        fecha=sis.FECHA_TABULADOR,
        moneda="USD",
    )
    partidas = tuple(
        PartidaBase(
            p.item.codigo_partida, p.item.cantidad, p.resultado.costo_directo, p.item.origen_id
        )
        for p in presupuesto.partidas
    )
    primera = presupuesto.partidas[0]
    codigo, cantidad = primera.item.codigo_partida, primera.item.cantidad
    valuacion = _v(
        "V-01",
        INICIO,
        date(2026, 11, 6),
        lineas=[LineaValuacion(codigo, cantidad + D(1)), LineaValuacion("SIS-NO-EXISTE", D(1))],
    )
    instantanea = InstantaneaDeControl(CORTE, INICIO, partidas, (valuacion,), _habiles)
    hallazgos = auditar(presupuesto, reglas_de_control(instantanea)).hallazgos
    por_origen = {h.origen_ids[0]: h for h in hallazgos}
    assert sorted(por_origen) == sorted(
        [f"valuacion:V-01:{codigo}", "valuacion:V-01:SIS-NO-EXISTE"]
    )
    assert {(h.regla, h.severidad.name) for h in hallazgos} == {("R13", "ERROR")}
    assert por_origen[f"valuacion:V-01:{codigo}"].impacto == primera.resultado.costo_directo
    assert por_origen["valuacion:V-01:SIS-NO-EXISTE"].impacto is None
```
  Registro, inmutabilidad, anulación e instantánea:
```python
# tests/integration/test_valuaciones.py
"""SL-E4: valuaciones registradas, anuladas y la instantánea de control (spec S2 §3, RF-72).

OB-S2 a mano (memoria `control_ob_s2.md`): V-01 y V-02 cuentan desde su registro, la anulada se
conserva y deja de contar, nada se edita ni se borra, y un cambio de moneda invalida la línea base.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import event, func, select

from core import models
from core.budget import elaborar, guardar_edicion
from core.budget.edicion import CambioEditado
from core.budget.valuaciones import (
    Calendario,
    LineaBaseInvalidada,
    anexo_control,
    anular_valuacion,
    instantanea_control,
    registrar_costo,
    registrar_linea_base,
    registrar_valuacion,
    valuaciones_registradas,
)
from core.catalog import Catalogo
from core.verification.valuaciones import LineaValuacion
from tests.fixtures import control_ob_s2 as ob

D = Decimal
TABLAS_SOLO_AGREGAR = ("valuacion", "linea_valuacion", "anulacion_valuacion")


def _instantanea(sesion, corte=None):
    return instantanea_control(sesion, ob.NOMBRE, catalogo=Catalogo(sesion), corte=corte)


def test_v01_y_v02_cuentan_desde_su_registro_con_su_fecha_hora(obra):
    primera, segunda = ob.registrar_v01_y_v02(obra)
    assert (primera.fecha_hora, segunda.fecha_hora) == (
        datetime(2026, 11, 9, 9, 0),
        datetime(2026, 11, 16, 9, 0),
    )
    instantanea = _instantanea(obra)
    assert instantanea.corte == date(2026, 11, 13)  # el hasta de la ultima valuacion
    assert [v.numero for v in instantanea.valuaciones] == ["V-01", "V-02"]
    assert instantanea.linea_base.version == "OB-001"
    assert instantanea.moneda == "USD" and len(instantanea.costos) == 1
    assert [v.fecha_hora for v in instantanea.valuaciones] == [
        primera.fecha_hora,
        segunda.fecha_hora,
    ]


def test_una_valuacion_anulada_se_conserva_y_deja_de_contar(obra):
    _, segunda = ob.registrar_v01_y_v02(obra)
    anulacion = anular_valuacion(
        obra, segunda.id, motivo="el cliente no la aprobo", responsable=ob.RESPONSABLE
    )
    assert anulacion.valuacion_id == segunda.id
    assert [v.numero for v in valuaciones_registradas(obra, ob.NOMBRE)] == ["V-01"]
    todas = valuaciones_registradas(obra, ob.NOMBRE, con_anuladas=True)
    assert [v.numero for v in todas] == ["V-01", "V-02"]
    assert obra.scalar(select(func.count()).select_from(models.Valuacion)) == 2
    with pytest.raises(ValueError, match="ya esta anulada"):
        anular_valuacion(obra, segunda.id, motivo="otra vez", responsable=ob.RESPONSABLE)


def test_anular_exige_motivo_y_responsable_y_una_valuacion_que_exista(obra):
    _, segunda = ob.registrar_v01_y_v02(obra)
    with pytest.raises(ValueError, match="obligatoria"):
        anular_valuacion(obra, segunda.id, motivo=" ", responsable=ob.RESPONSABLE)
    with pytest.raises(ValueError, match="responsable"):
        anular_valuacion(obra, segunda.id, motivo="x", responsable="")
    with pytest.raises(KeyError):
        anular_valuacion(obra, 999, motivo="x", responsable="Ing.")


def test_registrar_rechaza_cantidad_negativa_sin_fuente_y_sin_lineas(obra):
    base = dict(numero="V-09", desde=ob.INICIO, hasta=date(2026, 11, 6), fecha=None, inspector="")
    with pytest.raises(ValueError, match="no puede ser negativa"):
        registrar_valuacion(
            obra, ob.NOMBRE, lineas=[("OB-A", D("-1"))], fuente="acta", responsable="Ing.", **base
        )
    with pytest.raises(ValueError, match="obligatoria"):
        registrar_valuacion(
            obra, ob.NOMBRE, lineas=[("OB-A", D(1))], fuente="", responsable="Ing.", **base
        )
    with pytest.raises(ValueError, match="al menos una linea"):
        registrar_valuacion(obra, ob.NOMBRE, lineas=[], fuente="acta", responsable="Ing.", **base)
    assert obra.scalar(select(func.count()).select_from(models.Valuacion)) == 0


def test_sin_linea_base_no_se_registra_ninguna_valuacion(obra_sin_linea_base):
    with pytest.raises(ValueError, match="linea base de control"):
        ob.registrar(obra_sin_linea_base, ob.V01)


def test_sin_numero_ni_inspector_se_guarda_y_r14_la_marca(obra):
    registrar_valuacion(
        obra,
        ob.NOMBRE,
        numero="",
        desde=ob.INICIO,
        hasta=date(2026, 11, 6),
        fecha=None,
        inspector="",
        lineas=[LineaValuacion("OB-A", D(1))],
        fuente="acta",
        responsable="Ing.",
    )
    informe = _instantanea(obra, corte=date(2026, 11, 6)).informe()
    assert sorted(h.descripcion.split(" no tiene ")[1] for h in informe.hallazgos) == [
        "fecha",
        "inspector",
        "numero",
    ]


def test_la_linea_base_vigente_al_corte_es_la_de_mayor_desde(obra):
    ob.registrar_v01_y_v02(obra)
    registrar_linea_base(
        obra,
        ob.NOMBRE,
        ob.CODIGO,
        desde=date(2026, 11, 10),
        perspectiva="precio",
        calendario=Calendario(date(2026, 11, 2), 5),
        fuente="nueva linea base",
        responsable="Ing.",
    )
    assert _instantanea(obra, corte=date(2026, 11, 9)).linea_base.perspectiva == "costo"
    assert _instantanea(obra, corte=date(2026, 11, 10)).linea_base.perspectiva == "precio"
    with pytest.raises(ValueError, match="no hay linea base"):
        _instantanea(obra, corte=date(2026, 11, 1))


def test_la_linea_base_exige_perspectiva_valida_fuente_y_version_existente(obra_sin_linea_base):
    sesion = obra_sin_linea_base
    base = dict(desde=ob.INICIO, calendario=ob.CALENDARIO, responsable="Ing.")
    with pytest.raises(ValueError, match="perspectiva"):
        registrar_linea_base(sesion, ob.NOMBRE, ob.CODIGO, perspectiva="otra", fuente="x", **base)
    with pytest.raises(ValueError, match="obligatoria"):
        registrar_linea_base(sesion, ob.NOMBRE, ob.CODIGO, perspectiva="costo", fuente="", **base)
    with pytest.raises(KeyError):
        registrar_linea_base(sesion, ob.NOMBRE, "NO-HAY", perspectiva="costo", fuente="x", **base)
    with pytest.raises(ValueError, match="1 o mas"):
        Calendario(ob.INICIO, 0)


def test_sin_valuaciones_y_sin_corte_pide_la_fecha(obra):
    with pytest.raises(ValueError, match="elija la fecha de corte"):
        _instantanea(obra)
    assert _instantanea(obra, corte=ob.CORTE).valuaciones == ()


def test_un_cambio_de_moneda_invalida_la_linea_base(obra):
    """RV-11: con el proyecto en Bs, la línea base sobre OB-001 (USD) queda invalidada."""
    ob.registrar_v01_y_v02(obra)
    proyecto = obra.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == ob.NOMBRE)
    ).one()
    obra.add(
        models.MonedaProyecto(
            proyecto_id=proyecto.id,
            moneda="Bs",
            desde=datetime(2026, 11, 14),
            version_id=None,
            responsable="Ing.",
            fuente="conversion ficticia",
        )
    )
    obra.flush()
    with pytest.raises(LineaBaseInvalidada, match="linea base invalidada: declarela de nuevo"):
        _instantanea(obra)


def test_costo_real_con_moneda_y_monto_validos(obra):
    registrar_costo(
        obra,
        ob.NOMBRE,
        monto=D("10.50"),
        moneda="Bs",
        fecha=ob.CORTE,
        fuente="factura 1",
        responsable="Ing.",
        codigo_partida="OB-A",
    )
    base = dict(fecha=ob.CORTE, fuente="f", responsable="I")
    with pytest.raises(ValueError, match="no negativo"):
        registrar_costo(obra, ob.NOMBRE, monto=D("-1"), moneda="USD", **base)
    with pytest.raises(ValueError, match="moneda"):
        registrar_costo(obra, ob.NOMBRE, monto=D(1), moneda="EUR", **base)


def test_el_anexo_de_control_trae_todo_con_las_anuladas_marcadas(obra):
    primera, _ = ob.registrar_v01_y_v02(obra)
    anular_valuacion(obra, primera.id, motivo="error de medicion", responsable="Ing.")
    anexo = anexo_control(obra, ob.NOMBRE)
    assert [v["numero"] for v in anexo["valuaciones"]] == ["V-01", "V-02"]
    assert anexo["valuaciones"][0]["anulada"]["motivo"] == "error de medicion"
    assert anexo["valuaciones"][1]["anulada"] is None
    assert anexo["valuaciones"][1]["fecha_hora"] == "2026-11-16T09:00:00"
    assert anexo["valuaciones"][1]["lineas"][1] == {
        "partida": "OB-B",
        "cantidad": "60",
        "fecha_medicion": None,
        "observacion": "",
    }
    assert anexo["lineas_base"][0]["version"] == "OB-001"
    assert anexo["costos"][0]["monto"] == "1280.00"
    assert anexo == anexo_control(obra, ob.NOMBRE)  # determinista


def test_ninguna_funcion_emite_update_ni_delete_sobre_las_tablas_solo_agregar(motor, obra):
    """S2-R10: se ejercen las operaciones de escritura y lectura y se miran los SQL emitidos."""
    emitidos: list[str] = []

    @event.listens_for(motor, "before_cursor_execute")
    def _guardar(conexion, cursor, sentencia, parametros, contexto, varias):
        emitidos.append(sentencia)

    primera, _ = ob.registrar_v01_y_v02(obra)
    anular_valuacion(obra, primera.id, motivo="prueba", responsable="Ing.")
    _instantanea(obra, corte=ob.CORTE)
    anexo_control(obra, ob.NOMBRE)
    obra.flush()
    patron = re.compile(rf"^\s*(UPDATE|DELETE FROM)\s+({'|'.join(TABLAS_SOLO_AGREGAR)})\b", re.I)
    assert [sentencia for sentencia in emitidos if patron.match(sentencia)] == []
    assert any(s.lstrip().upper().startswith("INSERT INTO VALUACION") for s in emitidos)


def test_una_variacion_de_obra_declarada_como_linea_base_hace_pasar_r13(obra):
    """UC-19 4b: lo valuado sobre lo presupuestado se guarda con R13 ERROR; registrar la variación
    por la hoja (versión nueva con la cantidad) y declararla línea base lo resuelve."""
    ob.registrar_v01_y_v02(obra)
    ob.registrar(obra, ob.VS)
    antes = _instantanea(obra, corte=ob.CORTE_DE_VS).informe()
    assert [h.origen_ids[0] for h in antes.hallazgos if h.regla == "R13"] == [
        "valuacion:V-03:OB-B",
        "valuacion:V-03:OB-D",
    ]
    mayor = [replace(i, cantidad=D(210)) if i.codigo_partida == "OB-B" else i for i in ob.items()]
    variacion = elaborar(
        mayor, ob.composiciones(), ob.PARAMETROS, codigo="OB-002", fecha=ob.FECHA,
        moneda=ob.MONEDA, plan=ob.PLAN,
    )  # fmt: skip
    guardar_edicion(
        obra, ob.NOMBRE, ob.CODIGO, variacion, ob.PARAMETROS,
        [CambioEditado("cantidad", "OB-B", "cantidad", "200", "210")],
        fuente="acta de variacion ficticia", responsable=ob.RESPONSABLE, plan=ob.PLAN,
    )  # fmt: skip
    registrar_linea_base(
        obra, ob.NOMBRE, "OB-002", desde=date(2026, 11, 12), perspectiva="costo",
        calendario=ob.CALENDARIO, fuente="la variacion pasa a ser la linea base",
        responsable=ob.RESPONSABLE,
    )  # fmt: skip
    despues = _instantanea(obra, corte=ob.CORTE_DE_VS)
    assert despues.linea_base.version == "OB-002"
    assert [h.origen_ids[0] for h in despues.informe().hallazgos if h.regla == "R13"] == [
        "valuacion:V-03:OB-D"
    ]  # B ya cabe; D sigue sin estar presupuestada
    # Al corte anterior a la variacion rige la linea base anterior.
    assert _instantanea(obra, corte=date(2026, 11, 11)).linea_base.version == "OB-001"
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_r13_r14.py tests/integration/test_valuaciones.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.verification.valuaciones'`
```bash
git add tests/fixtures/control_ob_s2.py tests/integration/conftest.py tests/unit/test_r13_r14.py tests/integration/test_valuaciones.py
git commit -m "test(core): R13, R14 y el registro de valuaciones de OB-S2 en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  Los tipos y las reglas viven en `core/verification/valuaciones.py` (RP7-3: así `core/budget` los importa sin ciclo). Reciben la `InstantaneaDeControl` con `habiles_entre` inyectado, porque `core/verification` no importa `core/budget` (RP7-2):
```python
# core/verification/valuaciones.py
"""SL-E4: reglas R13 y R14 de las valuaciones de obra (spec S2 §3.4; RF-74).

Son `ReglaVerificacion` del contrato, sin cambios, y se construyen con la **instantánea de
control** (`InstantaneaDeControl`): la línea base (partidas, cantidades y unitarios), su
calendario y las valuaciones registradas y no anuladas. Entran por `reglas=` como R8-R12; **no**
entran en `REGLAS`, así que el 7 de 7 y las huellas de RNF-04 no se mueven. El `Presupuesto` que
reciben `evaluar` no se lee: la regla habla de las valuaciones, no de las partidas.

**R13 Valuación dentro del presupuesto**: (a) el acumulado no anulado de una partida supera su
cantidad de la línea base (ERROR, impacto = exceso x unitario base; la igualdad pasa); (b) partida
valuada que la línea base no tiene (ERROR, sin impacto: no hay unitario); (c) partida presupuestada
que el plan no programa en ningún período (ADVERTENCIA).

**R14 Fuente y fechas de la valuación**: (a) falta número, inspector o fecha (ERROR); (b) *desde*
posterior a *hasta*, fecha anterior a *hasta*, *hasta* posterior al corte o *desde* anterior al
inicio del calendario (ERROR); (c) períodos solapados o número repetido (ERROR); (d) fecha de
medición de una línea fuera de [*desde*, *hasta*] (ERROR); (e) números no consecutivos con el patrón
prefijo + número (ADVERTENCIA); (f) hueco de al menos un día hábil entre dos valuaciones
consecutivas (INFO).

Cada hallazgo cita en `origen_ids` la clave de la línea (`valuacion:<número>:<código>`) y, si la
línea base tiene la partida, el `origen_id` de su ítem, para que el informe atribuya la partida
(C5.1). Los hallazgos salen en un orden estable: por valuación en el orden recibido y, dentro de
ella, por línea. Este módulo no importa `core.budget`: el calendario llega como función
(`habiles_entre`), que arma quien construye la instantánea.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "CODIGO_R13",
    "CODIGO_R14",
    "FuenteYFechasDeValuacion",
    "InstantaneaDeControl",
    "LineaValuacion",
    "PartidaBase",
    "Valuacion",
    "ValuacionDentroDelPresupuesto",
    "reglas_de_control",
]

CODIGO_R13 = "R13"
CODIGO_R14 = "R14"
CERO = Decimal(0)
_NUMERO = re.compile(r"^(.*?)(\d+)$")


@dataclass(frozen=True, slots=True)
class LineaValuacion:
    """La cantidad ejecutada de una partida en una valuación (del período, no acumulada)."""

    codigo_partida: str
    cantidad: Decimal
    fecha_medicion: date | None = None
    observacion: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.cantidad, Decimal) or not self.cantidad.is_finite():
            raise ValueError(f"la cantidad de {self.codigo_partida!r} debe ser un Decimal finito")
        if self.cantidad < CERO:
            raise ValueError(
                f"la cantidad de {self.codigo_partida!r} no puede ser negativa ({self.cantidad}): "
                "una correccion es una anulacion"
            )


@dataclass(frozen=True, slots=True)
class Valuacion:
    """Una valuación registrada. `numero`, `inspector` y `fecha` pueden faltar: R14 los marca.

    `id` es 0 mientras no está guardada. `origen` dice si se escribió a mano o de qué archivo
    salió; `fecha_hora` es el momento del registro, desde el cual cuenta (S2-R14).
    """

    id: int
    numero: str
    desde: date
    hasta: date
    fecha: date | None
    inspector: str
    lineas: tuple[LineaValuacion, ...]
    origen: str = "manual"
    fuente: str = ""
    responsable: str = ""
    fecha_hora: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "lineas", tuple(self.lineas))

    @property
    def clave(self) -> str:
        """El número, o `#<id>` si falta: la clave que citan los hallazgos."""
        return self.numero.strip() or f"#{self.id}"


@dataclass(frozen=True, slots=True)
class PartidaBase:
    """Una partida de la línea base: su cantidad, su unitario según la perspectiva, el
    `origen_id` de su ítem de cómputo y si el plan la programa en algún período."""

    codigo: str
    cantidad: Decimal
    unitario: Decimal
    origen_id: str
    programada: bool = True


@dataclass(frozen=True)
class InstantaneaDeControl:
    """Lo que R13 y R14 miran (S2 §3.4): las valuaciones registradas y no anuladas, la línea base
    y el calendario, al `corte`. `habiles_entre(a, b)` cuenta los días hábiles de [a, b]."""

    corte: date
    inicio: date
    partidas: tuple[PartidaBase, ...]
    valuaciones: tuple[Valuacion, ...]
    habiles_entre: Callable[[date, date], int] = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "partidas", tuple(self.partidas))
        object.__setattr__(self, "valuaciones", tuple(self.valuaciones))


def _n(valor: Decimal) -> str:
    """Un decimal tal cual, sin ceros de relleno ni notación científica (mensajes deterministas)."""
    return format(valor.normalize(), "f")


def _dia(valor: date) -> str:
    return valor.isoformat()


def _origenes(
    instantanea: InstantaneaDeControl, valuacion: Valuacion, codigo: str | None = None
) -> tuple[str, ...]:
    clave = f"valuacion:{valuacion.clave}" + (f":{codigo}" if codigo else "")
    partida = next((p for p in instantanea.partidas if p.codigo == codigo), None)
    return (clave,) if partida is None else (clave, partida.origen_id)


def _hallazgo(
    regla: str,
    severidad: Severidad,
    descripcion: str,
    origenes: tuple[str, ...],
    *,
    impacto: Decimal | None = None,
    observado: Decimal | None = None,
    esperado: Decimal | None = None,
) -> Hallazgo:
    return Hallazgo(
        regla=regla,
        severidad=severidad,
        descripcion=descripcion,
        impacto=impacto,
        origen_ids=origenes,
        valor_observado=observado,
        valor_esperado=esperado,
    )


class ValuacionDentroDelPresupuesto(ReglaVerificacion):
    """R13: lo valuado no supera lo presupuestado ni sale de la línea base."""

    codigo = CODIGO_R13
    nombre = "Valuacion dentro del presupuesto"

    def __init__(self, instantanea: InstantaneaDeControl) -> None:
        self._instantanea = instantanea

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        instantanea = self._instantanea
        base = {p.codigo: p for p in instantanea.partidas}
        acumulado: dict[str, Decimal] = defaultdict(lambda: CERO)
        # Un evento por partida: la primera valuacion que la cita sin base o que la excede.
        eventos: list[tuple[str, Valuacion]] = []
        vistas: set[str] = set()
        for valuacion in instantanea.valuaciones:
            for linea in valuacion.lineas:
                codigo = linea.codigo_partida
                partida = base.get(codigo)
                antes = acumulado[codigo]
                acumulado[codigo] += linea.cantidad
                excede = partida is not None and antes <= partida.cantidad < acumulado[codigo]
                if codigo not in vistas and (partida is None or excede):
                    vistas.add(codigo)
                    eventos.append((codigo, valuacion))
        hallazgos = [
            self._sin_base(valuacion, codigo)
            if codigo not in base
            else self._exceso(valuacion, base[codigo], acumulado[codigo])
            for codigo, valuacion in eventos
        ]
        hallazgos.extend(
            _hallazgo(
                CODIGO_R13,
                Severidad.ADVERTENCIA,
                f"la partida {partida.codigo} esta presupuestada y el plan de la linea base no "
                "la programa en ningun periodo",
                (partida.origen_id,),
            )
            for partida in instantanea.partidas
            if not partida.programada
        )
        return hallazgos

    def _sin_base(self, valuacion: Valuacion, codigo: str) -> Hallazgo:
        return _hallazgo(
            CODIGO_R13,
            Severidad.ERROR,
            f"la valuacion {valuacion.clave} valua la partida {codigo}, que la linea base no "
            "tiene: sin unitario, no se cuantifica",
            _origenes(self._instantanea, valuacion, codigo),
        )

    def _exceso(self, valuacion: Valuacion, partida: PartidaBase, total: Decimal) -> Hallazgo:
        exceso = total - partida.cantidad
        return _hallazgo(
            CODIGO_R13,
            Severidad.ERROR,
            f"la partida {partida.codigo} lleva {_n(total)} valuados y la linea base "
            f"presupuesta {_n(partida.cantidad)}: exceso de {_n(exceso)} desde la valuacion "
            f"{valuacion.clave}",
            _origenes(self._instantanea, valuacion, partida.codigo),
            impacto=exceso * partida.unitario,
            observado=total,
            esperado=partida.cantidad,
        )


class FuenteYFechasDeValuacion(ReglaVerificacion):
    """R14: cada valuación declara su fuente y sus fechas son coherentes entre sí y con el
    calendario."""

    codigo = CODIGO_R14
    nombre = "Fuente y fechas de la valuacion"

    def __init__(self, instantanea: InstantaneaDeControl) -> None:
        self._instantanea = instantanea

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        instantanea = self._instantanea
        hallazgos: list[Hallazgo] = []
        for valuacion in instantanea.valuaciones:
            hallazgos.extend(self._de_la_valuacion(valuacion))
        hallazgos.extend(self._solapes_y_repetidos())
        hallazgos.extend(self._numeracion())
        hallazgos.extend(self._huecos())
        return hallazgos

    def _error(
        self, valuacion: Valuacion, descripcion: str, severidad: Severidad = Severidad.ERROR
    ) -> Hallazgo:
        return _hallazgo(CODIGO_R14, severidad, descripcion, (f"valuacion:{valuacion.clave}",))

    def _de_la_valuacion(self, valuacion: Valuacion) -> list[Hallazgo]:
        instantanea = self._instantanea
        clave = valuacion.clave
        hallazgos: list[Hallazgo] = []
        if not valuacion.numero.strip():
            hallazgos.append(self._error(valuacion, f"la valuacion {clave} no tiene numero"))
        if not valuacion.inspector.strip():
            hallazgos.append(self._error(valuacion, f"la valuacion {clave} no tiene inspector"))
        if valuacion.fecha is None:
            hallazgos.append(self._error(valuacion, f"la valuacion {clave} no tiene fecha"))
        if valuacion.desde > valuacion.hasta:
            hallazgos.append(
                self._error(
                    valuacion,
                    f"la valuacion {clave} empieza el {_dia(valuacion.desde)}, despues de su "
                    f"fin ({_dia(valuacion.hasta)})",
                )
            )
        if valuacion.fecha is not None and valuacion.fecha < valuacion.hasta:
            hallazgos.append(
                self._error(
                    valuacion,
                    f"la valuacion {clave} tiene fecha {_dia(valuacion.fecha)}, anterior a su "
                    f"fin ({_dia(valuacion.hasta)})",
                )
            )
        if valuacion.hasta > instantanea.corte:
            hallazgos.append(
                self._error(
                    valuacion,
                    f"la valuacion {clave} termina el {_dia(valuacion.hasta)}, despues del corte "
                    f"({_dia(instantanea.corte)})",
                )
            )
        if valuacion.desde < instantanea.inicio:
            hallazgos.append(
                self._error(
                    valuacion,
                    f"la valuacion {clave} empieza el {_dia(valuacion.desde)}, antes del inicio "
                    f"del calendario ({_dia(instantanea.inicio)})",
                )
            )
        for linea in valuacion.lineas:
            medida = linea.fecha_medicion
            if medida is not None and not valuacion.desde <= medida <= valuacion.hasta:
                hallazgos.append(
                    _hallazgo(
                        CODIGO_R14,
                        Severidad.ERROR,
                        f"la medicion de {linea.codigo_partida} en la valuacion {clave} es del "
                        f"{_dia(medida)}, fuera de su periodo "
                        f"{_dia(valuacion.desde)} a {_dia(valuacion.hasta)}",
                        _origenes(instantanea, valuacion, linea.codigo_partida),
                    )
                )
        return hallazgos

    def _solapes_y_repetidos(self) -> list[Hallazgo]:
        validas = [v for v in self._instantanea.valuaciones if v.desde <= v.hasta]
        hallazgos: list[Hallazgo] = []
        for i, primera in enumerate(self._instantanea.valuaciones):
            for segunda in self._instantanea.valuaciones[i + 1 :]:
                if primera.numero.strip() and primera.numero.strip() == segunda.numero.strip():
                    hallazgos.append(
                        self._error(segunda, f"el numero {segunda.clave} esta repetido")
                    )
                if (
                    primera in validas
                    and segunda in validas
                    and segunda.desde <= primera.hasta
                    and primera.desde <= segunda.hasta
                ):
                    hallazgos.append(
                        self._error(
                            segunda,
                            f"el periodo de la valuacion {segunda.clave} "
                            f"({_dia(segunda.desde)} a {_dia(segunda.hasta)}) se solapa con el "
                            f"de la {primera.clave} "
                            f"({_dia(primera.desde)} a {_dia(primera.hasta)})",
                        )
                    )
        return hallazgos

    def _numeracion(self) -> list[Hallazgo]:
        por_prefijo: dict[str, list[tuple[int, Valuacion]]] = defaultdict(list)
        for valuacion in self._instantanea.valuaciones:
            encontrado = _NUMERO.match(valuacion.numero.strip())
            if encontrado:
                por_prefijo[encontrado.group(1)].append((int(encontrado.group(2)), valuacion))
        hallazgos: list[Hallazgo] = []
        for numeradas in por_prefijo.values():
            numeradas.sort(key=lambda par: par[0])
            for (antes, anterior), (despues, siguiente) in zip(
                numeradas, numeradas[1:], strict=False
            ):
                if despues - antes > 1:
                    hallazgos.append(
                        self._error(
                            siguiente,
                            f"las valuaciones {anterior.clave} y {siguiente.clave} no son "
                            "consecutivas: falta al menos un numero",
                            Severidad.ADVERTENCIA,
                        )
                    )
        return hallazgos

    def _huecos(self) -> list[Hallazgo]:
        validas = sorted(
            (v for v in self._instantanea.valuaciones if v.desde <= v.hasta),
            key=lambda v: (v.desde, v.hasta),
        )
        hallazgos: list[Hallazgo] = []
        for anterior, siguiente in zip(validas, validas[1:], strict=False):
            primero = anterior.hasta + timedelta(days=1)
            ultimo = siguiente.desde - timedelta(days=1)
            if primero > ultimo:
                continue
            dias = self._instantanea.habiles_entre(primero, ultimo)
            if dias >= 1:
                hallazgos.append(
                    self._error(
                        siguiente,
                        f"entre las valuaciones {anterior.clave} y {siguiente.clave} hay "
                        f"{dias} dia(s) habil(es) sin cubrir ({_dia(primero)} a {_dia(ultimo)})",
                        Severidad.INFO,
                    )
                )
        return hallazgos


def reglas_de_control(instantanea: InstantaneaDeControl) -> tuple[ReglaVerificacion, ...]:
    """R13 y R14 sobre la instantánea: lo que se pasa a `elaborar`/`auditar` por `reglas=`."""
    return (ValuacionDentroDelPresupuesto(instantanea), FuenteYFechasDeValuacion(instantanea))
```
  El registro, la anulación y la instantánea (a esta altura sin Excel ni `ejecutado_por_periodo`, que llegan en la tarea 6):
```python
# core/budget/valuaciones.py
"""SL-E4: línea base de control, valuaciones, costos incurridos y su entrega a S1 (spec S2 §3, §6).

Una **valuación** es la cantidad ejecutada por partida y período, con su fuente (número, inspector,
fecha). Se guarda **sin modificar ninguna anterior** y **cuenta desde su registro**, sin
conformación (RV-18, S2-R14); la única forma de sacarla del cálculo es anularla, y la anulada se
conserva. Ninguna función de este módulo emite `UPDATE` ni `DELETE` sobre `valuacion`,
`linea_valuacion` ni `anulacion_valuacion` (S2-R10).

La **línea base de control** (versión, perspectiva, calendario) fija contra qué se mide el avance;
una decisión de recuperación **no** la cambia (S2-R3). Un cambio de moneda del proyecto después de
declararla la **invalida**: `instantanea_control` lo rechaza y hay que declararla de nuevo sobre la
versión convertida (RV-11).

`ejecutado_por_periodo` entrega a S1 lo ejecutado de cada período de su cláusula: las valuaciones
registradas y no anuladas, cada una entera en el período que contiene su fecha *hasta* (S2-R16).
`leer_valuaciones_excel` es la fuente única del formato del XLSX (§6.2). Todo monto y cantidad es
`Decimal`; las divisiones, si las hubiera, irían en un contexto local de 28 dígitos.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import partial

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _buscar, _parametros_de
from core.budget.calendario import dias_habiles, numero_de_dia
from core.budget.curva import PeriodoPlan
from core.budget.edicion import _exigir_respaldo
from core.budget.excel import TablaExportable
from core.budget.instantanea import plan_de_version
from core.budget.moneda import moneda_del_proyecto
from core.budget.persistencia import cargar_presupuesto
from core.catalog import Catalogo
from core.catalog.moneda import exigir_moneda
from core.contracts.apu import ParametrosCosto
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import ReglaVerificacion
from core.models.control import PERSPECTIVAS
from core.verification import auditar
from core.verification.informe import InformeAuditoria
from core.verification.valuaciones import (
    InstantaneaDeControl,
    LineaValuacion,
    PartidaBase,
    Valuacion,
    reglas_de_control,
)

__all__ = [
    "Calendario",
    "CostoReal",
    "InstantaneaControl",
    "LineaBase",
    "LineaBaseInvalidada",
    "anexo_control",
    "anular_valuacion",
    "instantanea_control",
    "registrar_costo",
    "registrar_linea_base",
    "registrar_valuacion",
    "tabla_valuaciones",
]

CERO = Decimal(0)
ORIGEN_MANUAL = "manual"
MENSAJE_INVALIDADA = "linea base invalidada: declarela de nuevo"


class LineaBaseInvalidada(ValueError):  # noqa: N818
    """La moneda del proyecto cambió después de declarar la línea base de control (RV-11)."""


@dataclass(frozen=True, slots=True)
class Calendario:
    """Fecha de inicio, días hábiles por período y feriados de la obra (S2 §4.1)."""

    fecha_inicio: date
    dias_por_periodo: int
    feriados: tuple[date, ...] = ()

    def __post_init__(self) -> None:
        if self.dias_por_periodo < 1:
            raise ValueError(f"los dias por periodo deben ser 1 o mas: {self.dias_por_periodo}")
        object.__setattr__(self, "feriados", tuple(sorted(set(self.feriados))))


@dataclass(frozen=True, slots=True)
class LineaBase:
    """Una línea base de control ya guardada, con su calendario y el código de su versión."""

    id: int
    proyecto: str
    version: str
    desde: date
    perspectiva: str
    fuente: str
    responsable: str
    calendario: Calendario
    fecha_hora: datetime | None = None


@dataclass(frozen=True, slots=True)
class CostoReal:
    """Un costo real declarado (S2 §6.1): se convierte con la tasa de su fecha al calcular."""

    id: int
    monto: Decimal
    moneda: str
    fecha: date
    fuente: str
    responsable: str = ""
    codigo_partida: str | None = None
    valuacion_id: int | None = None


@dataclass(frozen=True)
class InstantaneaControl:
    """Lo que el control necesita al corte (S2 §3.4): la línea base con su presupuesto, su plan y
    su calendario; las valuaciones registradas y no anuladas y los costos reales declarados.

    Las valuaciones son **todas** las no anuladas; el valor ganado usa las de *hasta* menor o
    igual al corte y R14 marca las que terminan después (RP7-2).
    """

    proyecto: str
    corte: date
    linea_base: LineaBase
    presupuesto: Presupuesto
    plan: tuple[PeriodoPlan, ...]
    parametros_costo: ParametrosCosto
    moneda: str
    valuaciones: tuple[Valuacion, ...] = ()
    costos: tuple[CostoReal, ...] = ()

    @property
    def calendario(self) -> Calendario:
        return self.linea_base.calendario

    def para_el_valor_ganado(self) -> tuple[Valuacion, ...]:
        """Las valuaciones que cuentan al corte: registradas, no anuladas y con *hasta* <= corte."""
        return tuple(v for v in self.valuaciones if v.hasta <= self.corte)

    def auditada(self) -> InstantaneaDeControl:
        """La entrada de R13 y R14 (`core.verification.valuaciones`)."""
        programadas = {codigo for _, reparto in self.plan for codigo, f in reparto if f > CERO}
        partidas: dict[str, PartidaBase] = {}
        for renglon in self.presupuesto.partidas:
            codigo = renglon.item.codigo_partida
            unitario = (
                renglon.resultado.costo_directo
                if self.linea_base.perspectiva == "costo"
                else renglon.resultado.precio_unitario
            )
            previa = partidas.get(codigo)
            partidas[codigo] = PartidaBase(
                codigo,
                renglon.item.cantidad + (previa.cantidad if previa else CERO),
                unitario,
                previa.origen_id if previa else renglon.item.origen_id,
                codigo in programadas,
            )
        return InstantaneaDeControl(
            corte=self.corte,
            inicio=self.calendario.fecha_inicio,
            partidas=tuple(partidas.values()),
            valuaciones=self.valuaciones,
            habiles_entre=partial(dias_habiles, feriados=frozenset(self.calendario.feriados)),
        )

    def reglas(self) -> tuple[ReglaVerificacion, ...]:
        return reglas_de_control(self.auditada())

    def informe(self) -> InformeAuditoria:
        """El informe de control (principio 7): R13 y R14 sobre las valuaciones al corte."""
        return auditar(self.presupuesto, self.reglas())


# ---------------------------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------------------------


def _proyecto(session: Session, nombre: str) -> models.Proyecto:
    proyecto = session.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == nombre)
    ).one_or_none()
    if proyecto is None:
        raise KeyError(f"no hay ningun proyecto {nombre!r}")
    return proyecto


def registrar_linea_base(
    session: Session,
    proyecto_nombre: str,
    codigo_version: str,
    *,
    desde: date,
    perspectiva: str,
    calendario: Calendario,
    fuente: str,
    responsable: str,
    ahora: datetime | None = None,
) -> models.LineaBaseControl:
    """Declara la línea base de control sobre una versión guardada (RF-72). Cambiarla es declarar
    otra fila: la vigente al corte es la de mayor `desde` menor o igual al corte. La versión debe
    tener plan de trabajo y estar en la moneda del proyecto (`ValueError`). No confirma."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    if perspectiva not in PERSPECTIVAS:
        raise ValueError(f"perspectiva {perspectiva!r}: se espera costo o precio")
    version = _buscar(session, proyecto_nombre, codigo_version)
    if plan_de_version(session, version) is None:
        raise ValueError(
            f"la version {codigo_version!r} no tiene plan de trabajo: no hay con que medir"
        )
    if moneda_del_proyecto(session, version.proyecto) != version.moneda:
        raise ValueError(
            f"la version {codigo_version!r} esta en {version.moneda}, no en la moneda del "
            "proyecto: declare la linea base sobre la version convertida"
        )
    fila = models.LineaBaseControl(
        proyecto_id=version.proyecto_id,
        presupuesto_id=version.id,
        desde=desde,
        perspectiva=perspectiva,
        fuente=fuente,
        responsable=responsable,
        fecha_hora=ahora or datetime.now(),
    )
    fila.calendario = models.CalendarioObra(
        fecha_inicio=calendario.fecha_inicio,
        dias_por_periodo=calendario.dias_por_periodo,
        feriados=json.dumps([dia.isoformat() for dia in calendario.feriados]),
    )
    session.add(fila)
    session.flush()
    return fila


def _lineas(lineas: Sequence[LineaValuacion | tuple]) -> list[LineaValuacion]:
    return [
        linea if isinstance(linea, LineaValuacion) else LineaValuacion(*linea) for linea in lineas
    ]


def registrar_valuacion(
    session: Session,
    proyecto_nombre: str,
    *,
    numero: str,
    desde: date,
    hasta: date,
    fecha: date | None,
    inspector: str,
    lineas: Sequence[LineaValuacion | tuple],
    fuente: str,
    responsable: str,
    origen: str = ORIGEN_MANUAL,
    ahora: datetime | None = None,
) -> models.Valuacion:
    """Registra una valuación (UC-19 4): no modifica ninguna anterior y cuenta desde ahora.

    El número, el inspector y la fecha pueden faltar: se guarda y R14 la marca (UC-19 4a). Una
    cantidad negativa o no decimal se rechaza (`ValueError`, 2b): corregir es anular. Exige una
    línea base de control declarada, fuente y responsable. No confirma."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    proyecto = _proyecto(session, proyecto_nombre)
    if _lineas_base(session, proyecto.id) == []:
        raise ValueError("declare la linea base de control antes de registrar valuaciones")
    validadas = _lineas(lineas)
    if not validadas:
        raise ValueError("una valuacion necesita al menos una linea")
    fila = models.Valuacion(
        proyecto_id=proyecto.id,
        numero=numero.strip(),
        desde=desde,
        hasta=hasta,
        fecha=fecha,
        inspector=inspector.strip(),
        origen=origen,
        fuente=fuente,
        responsable=responsable,
        fecha_hora=ahora or datetime.now(),
    )
    fila.lineas = [
        models.LineaValuacion(
            codigo_partida=linea.codigo_partida,
            cantidad=linea.cantidad,
            fecha_medicion=linea.fecha_medicion,
            observacion=linea.observacion,
        )
        for linea in validadas
    ]
    session.add(fila)
    session.flush()
    return fila


def anular_valuacion(
    session: Session,
    valuacion_id: int,
    *,
    motivo: str,
    responsable: str,
    ahora: datetime | None = None,
) -> models.AnulacionValuacion:
    """Anula una valuación (UC-19 4c): fila de anulación con motivo y responsable. La anulada se
    conserva y deja de contar; se anula una sola vez. No confirma."""
    motivo, responsable = _exigir_respaldo(motivo, responsable)
    valuacion = session.get(models.Valuacion, valuacion_id)
    if valuacion is None:
        raise KeyError(f"no hay ninguna valuacion {valuacion_id}")
    if session.get(models.AnulacionValuacion, valuacion_id) is not None:
        raise ValueError(f"la valuacion {valuacion.numero or valuacion_id} ya esta anulada")
    anulacion = models.AnulacionValuacion(
        valuacion_id=valuacion_id,
        motivo=motivo,
        responsable=responsable,
        fecha_hora=ahora or datetime.now(),
    )
    session.add(anulacion)
    session.flush()
    return anulacion


def registrar_costo(
    session: Session,
    proyecto_nombre: str,
    *,
    monto: Decimal,
    moneda: str,
    fecha: date,
    fuente: str,
    responsable: str,
    codigo_partida: str | None = None,
    valuacion_id: int | None = None,
) -> models.CostoReal:
    """Registra un costo real (RF-75): monto, moneda, fecha y fuente. No se guarda convertido:
    se convierte con `tasa_aplicable(fecha)` al calcular. `ValueError` si el monto es negativo."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    if not isinstance(monto, Decimal) or not monto.is_finite() or monto < CERO:
        raise ValueError(f"el monto de un costo real debe ser un Decimal no negativo: {monto!r}")
    proyecto = _proyecto(session, proyecto_nombre)
    fila = models.CostoReal(
        proyecto_id=proyecto.id,
        valuacion_id=valuacion_id,
        codigo_partida=codigo_partida,
        monto=monto,
        moneda=exigir_moneda(moneda),
        fecha=fecha,
        fuente=fuente,
        responsable=responsable,
    )
    session.add(fila)
    session.flush()
    return fila


# ---------------------------------------------------------------------------------------------
# Lectura: la instantánea de control
# ---------------------------------------------------------------------------------------------


def _lineas_base(session: Session, proyecto_id: int) -> list[models.LineaBaseControl]:
    return list(
        session.scalars(
            select(models.LineaBaseControl)
            .where(models.LineaBaseControl.proyecto_id == proyecto_id)
            .order_by(models.LineaBaseControl.desde, models.LineaBaseControl.id)
        )
    )


def _a_linea_base(fila: models.LineaBaseControl, proyecto: str, version: str) -> LineaBase:
    calendario = fila.calendario
    return LineaBase(
        id=fila.id,
        proyecto=proyecto,
        version=version,
        desde=fila.desde,
        perspectiva=fila.perspectiva,
        fuente=fila.fuente,
        responsable=fila.responsable,
        calendario=Calendario(
            calendario.fecha_inicio,
            calendario.dias_por_periodo,
            tuple(date.fromisoformat(dia) for dia in json.loads(calendario.feriados)),
        ),
        fecha_hora=fila.fecha_hora,
    )


def _a_valuacion(fila: models.Valuacion) -> Valuacion:
    return Valuacion(
        id=fila.id,
        numero=fila.numero,
        desde=fila.desde,
        hasta=fila.hasta,
        fecha=fila.fecha,
        inspector=fila.inspector,
        lineas=tuple(
            LineaValuacion(
                linea.codigo_partida, linea.cantidad, linea.fecha_medicion, linea.observacion
            )
            for linea in fila.lineas
        ),
        origen=fila.origen,
        fuente=fila.fuente,
        responsable=fila.responsable,
        fecha_hora=fila.fecha_hora,
    )


def valuaciones_registradas(
    session: Session, proyecto_nombre: str, *, con_anuladas: bool = False
) -> list[Valuacion]:
    """Las valuaciones del proyecto en el orden en que se registraron. Por defecto, solo las no
    anuladas (las que cuentan)."""
    proyecto = _proyecto(session, proyecto_nombre)
    filas = session.scalars(
        select(models.Valuacion)
        .where(models.Valuacion.proyecto_id == proyecto.id)
        .order_by(models.Valuacion.id)
    )
    return [_a_valuacion(fila) for fila in filas if con_anuladas or fila.anulacion is None]


def instantanea_control(
    session: Session,
    proyecto_nombre: str,
    *,
    catalogo: Catalogo,
    corte: date | None = None,
) -> InstantaneaControl:
    """La instantánea de control al `corte` (por defecto, el *hasta* de la última valuación no
    anulada). Usa la línea base vigente al corte: la de mayor `desde` menor o igual a él.

    `LineaBaseInvalidada` si la moneda del proyecto ya no es la de la versión de esa línea base
    (RV-11): hay que declararla de nuevo sobre la versión convertida. `ValueError` si no hay línea
    base a esa fecha o, sin `corte`, ninguna valuación."""
    proyecto = _proyecto(session, proyecto_nombre)
    cuentan = valuaciones_registradas(session, proyecto_nombre)
    if corte is None:
        if not cuentan:
            raise ValueError("no hay valuaciones registradas: elija la fecha de corte")
        corte = max(v.hasta for v in cuentan)
    candidatas = [fila for fila in _lineas_base(session, proyecto.id) if fila.desde <= corte]
    if not candidatas:
        raise ValueError(f"no hay linea base de control declarada al {corte.isoformat()}")
    fila = candidatas[-1]
    version = session.get(models.Presupuesto, fila.presupuesto_id)
    moneda = moneda_del_proyecto(session, proyecto)
    if version.moneda != moneda:
        raise LineaBaseInvalidada(f"{MENSAJE_INVALIDADA} sobre la version en {moneda}")
    plan = plan_de_version(session, version)
    if plan is None:
        raise ValueError(f"la version {version.codigo!r} no tiene plan de trabajo")
    presupuesto = cargar_presupuesto(session, proyecto_nombre, version.codigo, catalogo)
    costos = tuple(
        CostoReal(
            c.id,
            c.monto,
            c.moneda,
            c.fecha,
            c.fuente,
            c.responsable,
            c.codigo_partida,
            c.valuacion_id,
        )
        for c in session.scalars(
            select(models.CostoReal)
            .where(models.CostoReal.proyecto_id == proyecto.id)
            .order_by(models.CostoReal.id)
        )
    )
    return InstantaneaControl(
        proyecto=proyecto_nombre,
        corte=corte,
        linea_base=_a_linea_base(fila, proyecto_nombre, version.codigo),
        presupuesto=presupuesto,
        plan=tuple((etiqueta, tuple(reparto)) for etiqueta, reparto in plan),
        parametros_costo=_parametros_de(version),
        moneda=moneda,
        valuaciones=tuple(cuentan),
        costos=costos,
    )


def dia_del_corte(instantanea: InstantaneaControl) -> int:
    """El número de día hábil del corte en el calendario de la línea base."""
    calendario = instantanea.calendario
    return numero_de_dia(calendario.fecha_inicio, instantanea.corte, frozenset(calendario.feriados))


# ---------------------------------------------------------------------------------------------
# Lo que se entrega a S1: lo ejecutado por período (RF-72, S2-R16)
# ---------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------
# Importación de Excel (RF-73, §6.2)
# ---------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------
# Tablas para el Excel y el paquete
# ---------------------------------------------------------------------------------------------

TITULO_VALUACIONES = "Valuaciones"
COLUMNAS_TABLA_VALUACIONES = (
    "Numero",
    "Desde",
    "Hasta",
    "Fecha",
    "Inspector",
    "Partida",
    "Cantidad",
    "Fecha de medicion",
    "Observacion",
    "Origen",
    "Registrada",
    "Estado",
)


def tabla_valuaciones(
    valuaciones: Sequence[Valuacion],
    *,
    anuladas: Sequence[Valuacion] = (),
    estados: Mapping[str, str] | None = None,
) -> TablaExportable:
    """Las valuaciones como la hoja «Valuaciones» del Excel (una fila por línea), con su fecha de
    registro y, si se pasa, el peor hallazgo de R13-R14 de cada una (`estados`, por su clave)."""
    estados = estados or {}
    filas = []
    for valuacion, estado_base in [(v, None) for v in valuaciones] + [
        (v, "ANULADA") for v in anuladas
    ]:
        for linea in valuacion.lineas:
            filas.append(
                (
                    valuacion.numero,
                    valuacion.desde,
                    valuacion.hasta,
                    valuacion.fecha,
                    valuacion.inspector,
                    linea.codigo_partida,
                    linea.cantidad,
                    linea.fecha_medicion,
                    linea.observacion,
                    valuacion.origen,
                    valuacion.fecha_hora,
                    estado_base or estados.get(valuacion.clave, ""),
                )
            )
    return TablaExportable(TITULO_VALUACIONES, COLUMNAS_TABLA_VALUACIONES, tuple(filas))


def anexo_control(session: Session, proyecto_nombre: str) -> dict[str, object]:
    """Todas las filas de control del proyecto como datos planos (textos y listas), para
    `anexos/control.json` del paquete de S3 (RV-8): líneas base con su calendario, parámetros,
    valuaciones con sus líneas y anulaciones, costos reales y citas. Las anuladas se incluyen,
    marcadas, con su fecha de registro. Es de solo lectura y determinista."""
    proyecto = _proyecto(session, proyecto_nombre)
    codigos = {
        fila.id: fila.codigo
        for fila in session.scalars(
            select(models.Presupuesto).where(models.Presupuesto.proyecto_id == proyecto.id)
        )
    }
    return {
        "lineas_base": [
            {
                "id": f.id,
                "version": codigos[f.presupuesto_id],
                "desde": f.desde.isoformat(),
                "perspectiva": f.perspectiva,
                "fuente": f.fuente,
                "responsable": f.responsable,
                "fecha_hora": f.fecha_hora.isoformat(),
                "inicio": f.calendario.fecha_inicio.isoformat(),
                "dias_por_periodo": f.calendario.dias_por_periodo,
                "feriados": json.loads(f.calendario.feriados),
            }
            for f in _lineas_base(session, proyecto.id)
        ],
        "valuaciones": [
            {
                "id": v.id,
                "numero": v.numero,
                "desde": v.desde.isoformat(),
                "hasta": v.hasta.isoformat(),
                "fecha": None if v.fecha is None else v.fecha.isoformat(),
                "inspector": v.inspector,
                "origen": v.origen,
                "fuente": v.fuente,
                "responsable": v.responsable,
                "fecha_hora": v.fecha_hora.isoformat(),
                "anulada": None
                if v.anulacion is None
                else {
                    "motivo": v.anulacion.motivo,
                    "responsable": v.anulacion.responsable,
                    "fecha_hora": v.anulacion.fecha_hora.isoformat(),
                },
                "lineas": [
                    {
                        "partida": linea.codigo_partida,
                        "cantidad": str(linea.cantidad),
                        "fecha_medicion": None
                        if linea.fecha_medicion is None
                        else linea.fecha_medicion.isoformat(),
                        "observacion": linea.observacion,
                    }
                    for linea in v.lineas
                ],
            }
            for v in session.scalars(
                select(models.Valuacion)
                .where(models.Valuacion.proyecto_id == proyecto.id)
                .order_by(models.Valuacion.id)
            )
        ],
        "costos": [
            {
                "id": c.id,
                "valuacion_id": c.valuacion_id,
                "partida": c.codigo_partida,
                "monto": str(c.monto),
                "moneda": c.moneda,
                "fecha": c.fecha.isoformat(),
                "fuente": c.fuente,
                "responsable": c.responsable,
            }
            for c in session.scalars(
                select(models.CostoReal)
                .where(models.CostoReal.proyecto_id == proyecto.id)
                .order_by(models.CostoReal.id)
            )
        ],
    }


def linea_base_vigente(
    session: Session, proyecto_nombre: str, corte: date
) -> models.LineaBaseControl | None:
    """La línea base de control vigente al `corte`, o `None` si no hay."""
    proyecto = _proyecto(session, proyecto_nombre)
    candidatas = [f for f in _lineas_base(session, proyecto.id) if f.desde <= corte]
    return candidatas[-1] if candidatas else None
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_r13_r14.py tests/integration/test_valuaciones.py -v -W error` → 40 pruebas en verde (26 de R13/R14 y 14 de valuaciones).
Run: `uv run pytest tests/unit/test_verification.py tests/integration/test_auditoria_7_de_7.py tests/unit/test_calendario.py -q -W error` → verde (R13 y R14 no entran a `REGLAS`; las siete reglas siguen en 7 de 7).
Run: `uv run ruff check core/verification/valuaciones.py core/budget/valuaciones.py tests/fixtures/control_ob_s2.py tests/unit/test_r13_r14.py tests/integration/test_valuaciones.py tests/integration/conftest.py` y la guardia del núcleo.
- [ ] **Paso 5: Commit**
```bash
git add core/verification/valuaciones.py core/budget/valuaciones.py
git commit -m "feat(core): R13, R14, registro y anulacion de valuaciones e instantanea de control" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 6: SL-E4c — ejecutado por período, importación de Excel y estudio con valuaciones citadas

**Rama:** `inc/070-s2-1-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/budget/puente.py`, `tests/fixtures/reajuste_ob_s2.py`, `tests/integration/test_ejecutado_por_periodo.py`, `tests/integration/test_importar_valuaciones.py`, `tests/integration/test_estudio_cita_valuaciones.py`
- Modificar: `core/budget/valuaciones.py` (agrega `ejecutado_por_periodo`, el lector de Excel y `registrar_lectura`; ver el parche del paso 3)

**Interfaces:**
- Consume: de la tarea 5: `registrar_valuacion`, `valuaciones_registradas`, `linea_base_vigente`, `Calendario`, `LineaBase`; de S1 (0.6.0): `core.budget.reajuste.{Clausula, Ejecutado, PeriodoDeclarado, guardar_estudio}`, `core.catalog.indices.LADO_POR_DEFECTO`, `models.PeriodoReajuste`, `models.EstudioReajuste`, `core.budget.moneda.moneda_del_proyecto`.
- Produce:
- `core/budget/valuaciones.py`:
  - `LIMITE_BYTES = 20 * 1024 * 1024`
  - `HOJA_VALUACIONES = 'Valuaciones'`
  - `HOJA_LINEAS = 'Lineas'`
  - `HOJA_COSTOS = 'Costos'`
  - `COLUMNAS_VALUACIONES = ('numero', 'desde', 'hasta', 'fecha', 'inspector')`
  - `COLUMNAS_LINEAS = ('numero', 'codigo_partida', 'cantidad', 'fecha_medicion', 'observacion')`
  - `COLUMNAS_COSTOS = ('numero', 'codigo_partida', 'monto', 'moneda', 'fecha', 'fuente')`
  - `PREFIJO_ORIGEN_EXCEL = 'excel:'`
  - `class LineaEjecutada [codigo: str; cantidad: Decimal; reajustable: Decimal; valuaciones: tuple[str, ...]; en_linea_base: bool]`
  - `class EjecutadoDelPeriodo [desde: date; hasta: date; valuaciones: tuple[Valuacion, ...]; lineas: tuple[LineaEjecutada, ...]; avisos: tuple[str, ...]]`
  - `def ejecutado_por_periodo(session: Session, proyecto_nombre: str, periodos: Sequence[tuple[date, date]]) -> tuple[EjecutadoDelPeriodo, ...]`
  - `class CostoLeido [numero: str; codigo_partida: str | None; monto: Decimal; moneda: str; fecha: date; fuente: str]`
  - `class LecturaControl [valuaciones: tuple[Valuacion, ...]; costos: tuple[CostoLeido, ...]; informe: tuple[str, ...]]`
  - `def leer_valuaciones_excel(ruta: Path) -> LecturaControl`
  - `def registrar_lectura(session: Session, proyecto_nombre: str, lectura: LecturaControl, *, fuente: str, responsable: str, ahora: datetime | None=None) -> tuple[list[models.Valuacion], list[models.CostoReal]]`
- `core/budget/puente.py`:
  - `class PeriodoDelEstudio [desde: date; hasta: date; version_comprobacion: str; excepcion: str]`
  - `def periodos_declarados(session: Session, proyecto_nombre: str, periodos: Sequence[PeriodoDelEstudio]) -> list[PeriodoDeclarado]`
  - `def estudio_con_valuaciones(session: Session, proyecto_nombre: str, codigo_contrato: str, clausula: Clausula, periodos: Sequence[PeriodoDelEstudio], *, fecha_calculo: date, fuente: str, responsable: str, reemplaza_a: int | None=None, lado: str=LADO_POR_DEFECTO, ahora: datetime | None=None) -> models.EstudioReajuste`
  - `def valuaciones_citadas(session: Session, estudio_id: int) -> dict[int, list[str]]`

- [ ] **Paso 0: Expediente SL-E4** (ver tarea 4, paso 0).
- [ ] **Paso 1: Escribir las pruebas que fallan**
  El estudio de reajuste de S1 que las pruebas de esta tarea y de la 9 comparten (revaloración `OB-R01`, cláusula y períodos de noviembre y diciembre; reconocido de noviembre 75,90):
```python
# tests/fixtures/reajuste_ob_s2.py
"""El escenario «con reajuste» de OB-S2 (spec S2 §7.1) sobre los estudios de S1.

La versión revalorada `OB-R01` (el material de B pasa de 3,00 a 4,00 y el de C de 12,00 a 14,10),
las series de índices (planas: `Km = 1`, porque el estudio de la memoria usa la comprobación
directa) y la cláusula ficticia de OB-S2: periodicidad mensual, mecanismo `comprobacion`. Con lo
ejecutado de noviembre (A 90 y B 60, de V-01 y V-02), el monto reconocido es
`Σ q_reajustable · (PU comprobado - PU del contrato)` = A 90 x 0,00 + B 60 x (7,59 - 6,325) = 75,90.
**Datos ficticios** (NORMAS.md §1).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from core import models
from core.budget import actualizar_precios
from core.budget.puente import PeriodoDelEstudio
from core.budget.reajuste import Clausula, Componente, Estructura, Mecanismo
from core.catalog.indices import DefinicionSerie, Observacion, registrar_importacion
from tests.fixtures import control_ob_s2 as ob

D = Decimal
REVALORADA = "OB-R01"
FECHA_REVALORACION = date(2026, 11, 13)
MATERIALES_DEL_CORTE = {
    "Material de Tuberia de drenaje": D("4.00"),
    "Material de Relleno compactado": D("14.10"),
}
SERIES = {"materiales": "OB-MAT", "equipos": "OB-EQU", "mano_obra": "OB-MO"}
PESOS = {"materiales": D("0.5"), "equipos": D("0.2"), "mano_obra": D("0.3")}
CLAUSULA = Clausula(
    fecha_inicio=date(2026, 11, 2),
    duracion_meses=6,
    fecha_referencia_primer_anio=date(2026, 11, 2),
    periodicidad="mensual",
    mecanismo=Mecanismo.COMPROBACION,
    estructura=Estructura.DECLARADA,
    componentes=tuple(Componente(c, SERIES[c], PESOS[c]) for c in SERIES),
    fecha_base_indices=date(2026, 10, 1),
    r=D("0"),
    fuente_r="memoria OB-S2: la clausula ficticia no declara R",
    fuente="contrato ficticio de OB-S2",
    responsable=ob.INSPECTOR,
)
NOVIEMBRE = PeriodoDelEstudio(date(2026, 11, 1), date(2026, 11, 30), REVALORADA)
DICIEMBRE = PeriodoDelEstudio(date(2026, 12, 1), date(2026, 12, 31), REVALORADA)
RECONOCIDO_DE_NOVIEMBRE = D("75.90")


def sembrar_revaloracion(sesion) -> models.Presupuesto:
    """Importa los índices planos y crea `OB-R01` revalorando OB-001 con una lista nueva."""
    for numero, codigo in enumerate(SERIES.values()):
        registrar_importacion(
            sesion,
            DefinicionSerie(codigo, codigo, "ficticio", "indice", "mensual"),
            [Observacion(date(2026, 10, 1), D(100)), Observacion(date(2026, 11, 1), D(100))],
            archivo="memoria",
            huella=str(numero) * 64,
            fuente="tests/fixtures/memorias/control_ob_s2.md",
            fecha_descarga=date(2026, 11, 13),
            responsable="Admin",
            filas_leidas=2,
            filas_rechazadas=0,
        )
    base = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == "OB-S2 USD")
    ).one()
    nueva = models.ListaPrecios(
        nombre="OB-S2 revalorada", moneda=ob.MONEDA, fecha_vigencia=FECHA_REVALORACION
    )
    sesion.add(nueva)
    sesion.flush()
    for precio in base.precios:
        descripcion = sesion.get(models.Insumo, precio.insumo_id).descripcion
        sesion.add(
            models.PrecioInsumo(
                lista_id=nueva.id,
                insumo_id=precio.insumo_id,
                precio=MATERIALES_DEL_CORTE.get(descripcion, precio.precio),
            )
        )
    sesion.flush()
    actualizar_precios(sesion, ob.NOMBRE, ob.CODIGO, nueva, REVALORADA, plan=ob.PLAN)
    return sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == REVALORADA)
    ).one()
```
  RF-72, el criterio del puente: lo ejecutado por período viene de las valuaciones **registradas y no anuladas**, cada una al período que contiene su *hasta*; `min(Q, q)` para lo reajustable; línea base invalidada por cambio de moneda:
```python
# tests/integration/test_ejecutado_por_periodo.py
"""SL-E4: lo ejecutado por período que S2 entrega a S1 (spec S2 RF-72, S2-R16; S1 §8.6).

Las valuaciones registradas y no anuladas, cada una entera en el período mensual que contiene su
fecha *hasta*, con la cantidad del período y la cantidad reajustable `min(Q al cierre, q) -
min(Q al cierre anterior, q)`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from core import models
from core.budget.valuaciones import (
    LineaBaseInvalidada,
    anular_valuacion,
    ejecutado_por_periodo,
)
from core.verification.valuaciones import LineaValuacion
from tests.fixtures import control_ob_s2 as ob

D = Decimal
NOVIEMBRE = (date(2026, 11, 1), date(2026, 11, 30))
DICIEMBRE = (date(2026, 12, 1), date(2026, 12, 31))


def _lineas(periodo):
    return {linea.codigo: (linea.cantidad, linea.reajustable) for linea in periodo.lineas}


def _valuar(sesion, numero, desde, hasta, **cantidades):
    """Una valuación breve (la fecha es el hasta, como exige R14) con las partidas dadas."""
    return ob.registrar(
        sesion,
        dict(
            numero=numero,
            desde=desde,
            hasta=hasta,
            fecha=hasta,
            inspector=ob.INSPECTOR,
            lineas=[LineaValuacion(codigo, D(c)) for codigo, c in cantidades.items()],
        ),
    )


def test_ob_s2_entrega_a_noviembre_a_90_y_b_60(obra):
    ob.registrar_v01_y_v02(obra)
    (noviembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert _lineas(noviembre) == {"OB-A": (D(90), D(90)), "OB-B": (D(60), D(60))}
    assert [v.numero for v in noviembre.valuaciones] == ["V-01", "V-02"]
    assert noviembre.avisos == ()
    assert [linea.valuaciones for linea in noviembre.lineas] == [("V-01", "V-02"), ("V-02",)]


def test_una_valuacion_anulada_no_entra(obra):
    _, segunda = ob.registrar_v01_y_v02(obra)
    anular_valuacion(obra, segunda.id, motivo="no aprobada", responsable="Ing.")
    (noviembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert _lineas(noviembre) == {"OB-A": (D(40), D(40))}


def test_lo_valuado_sobre_lo_presupuestado_entrega_el_total_y_reajusta_el_tope_con_aviso(obra):
    ob.registrar_v01_y_v02(obra)
    ob.registrar(obra, ob.VS)  # B 150 mas: acumulado 210 contra 200 presupuestados
    (noviembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    lineas = _lineas(noviembre)
    assert lineas["OB-B"] == (D(210), D(200))
    assert lineas["OB-D"] == (D(5), D(0))  # no presupuestada: nada reajustable
    assert lineas["OB-C"] == (D(10), D(10))
    avisos = " | ".join(noviembre.avisos)
    assert (
        "OB-B: ejecutado 210 en el periodo y solo 200 es reajustable (presupuestado 200" in avisos
    )
    assert "OB-D" in avisos


def test_una_valuacion_que_cruza_el_mes_va_entera_al_periodo_de_su_hasta(obra):
    _valuar(obra, "V-01", date(2026, 11, 30), date(2026, 12, 4), **{"OB-A": "25"})
    noviembre, diciembre = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE, DICIEMBRE])
    assert noviembre.lineas == ()
    assert _lineas(diciembre) == {"OB-A": (D(25), D(25))}


@pytest.mark.parametrize(
    ("hasta", "periodo"),
    [(date(2026, 11, 30), "noviembre"), (date(2026, 12, 1), "diciembre")],
    ids=[
        "hasta el ultimo dia del mes va a ese mes",
        "hasta el primero del siguiente va al siguiente",
    ],
)
def test_frontera_del_mes(obra, hasta, periodo):
    _valuar(obra, "V-01", date(2026, 11, 23), hasta, **{"OB-A": "10"})
    resultado = dict(
        zip(
            ("noviembre", "diciembre"),
            ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE, DICIEMBRE]),
            strict=True,
        )
    )
    assert _lineas(resultado[periodo]) == {"OB-A": (D(10), D(10))}
    otro = "diciembre" if periodo == "noviembre" else "noviembre"
    assert resultado[otro].lineas == ()


def test_lo_acumulado_de_periodos_anteriores_cuenta_para_el_tope(obra):
    _valuar(obra, "V-01", date(2026, 11, 2), date(2026, 11, 27), **{"OB-A": "95"})
    _valuar(obra, "V-02", date(2026, 12, 1), date(2026, 12, 4), **{"OB-A": "20"})
    noviembre, diciembre = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE, DICIEMBRE])
    assert _lineas(noviembre) == {"OB-A": (D(95), D(95))}
    assert _lineas(diciembre) == {"OB-A": (D(20), D(5))}  # 95 + 20 = 115: solo 5 caben en 100
    # Pedir solo diciembre cuenta igual lo de noviembre como ya ejecutado.
    (solo_diciembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [DICIEMBRE])
    assert _lineas(solo_diciembre) == {"OB-A": (D(20), D(5))}


def test_el_acumulado_igual_al_presupuestado_no_avisa_y_un_milesimo_mas_si(obra):
    _valuar(obra, "V-01", date(2026, 11, 2), date(2026, 11, 6), **{"OB-A": "100"})
    (justo,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert justo.avisos == ()
    _valuar(obra, "V-02", date(2026, 11, 9), date(2026, 11, 13), **{"OB-A": "0.001"})
    (pasado,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert _lineas(pasado)["OB-A"] == (D("100.001"), D(100))
    assert pasado.avisos


def test_lo_ejecutado_fuera_de_los_periodos_pedidos_no_se_entrega(obra):
    _valuar(obra, "V-01", date(2026, 10, 5), date(2026, 10, 9), **{"OB-A": "5"})
    (noviembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert noviembre.lineas == () and noviembre.valuaciones == ()


def test_pide_al_menos_un_periodo_y_necesita_linea_base(obra, obra_sin_linea_base):
    with pytest.raises(ValueError, match="al menos un periodo"):
        ejecutado_por_periodo(obra, ob.NOMBRE, [])


def test_tras_un_cambio_de_moneda_la_linea_base_invalidada_se_rechaza(obra):
    ob.registrar_v01_y_v02(obra)
    proyecto = obra.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == ob.NOMBRE)
    ).one()
    obra.add(
        models.MonedaProyecto(
            proyecto_id=proyecto.id,
            moneda="Bs",
            desde=datetime(2026, 11, 14),
            version_id=None,
            responsable="Ing.",
            fuente="conversion ficticia",
        )
    )
    obra.flush()
    with pytest.raises(LineaBaseInvalidada, match="declarela de nuevo"):
        ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
```
  La importación de Excel (§6.2): informe previo, rechazo entero de un archivo malformado, idempotencia, límite de tamaño, texto seguro:
```python
# tests/integration/test_importar_valuaciones.py
"""SL-E4: importación de valuaciones y costos desde XLSX (spec S2 §6.2, RF-73).

El XLSX versionado de OB-S2 da las mismas valuaciones que la entrada a mano; cada malformación de
§7.2 (fila RF-73) da su mensaje, sin *traceback* y sin escribir nada.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import openpyxl
import pytest
from sqlalchemy import func, select

from core import models
from core.budget.valuaciones import (
    LIMITE_BYTES,
    anular_valuacion,
    leer_valuaciones_excel,
    registrar_lectura,
    valuaciones_registradas,
)
from tests.fixtures import control_ob_s2 as ob

D = Decimal


def _cuenta(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


def _libro(tmp_path, cambiar):
    """El XLSX de OB-S2 con una malformación aplicada por `cambiar(libro)`."""
    ruta = ob.escribir_xlsx(tmp_path / "malo.xlsx")
    libro = openpyxl.load_workbook(ruta)
    cambiar(libro)
    libro.save(ruta)
    return ruta


def test_el_xlsx_versionado_de_la_memoria_existe_y_se_regenera_igual(tmp_path):
    regenerado = ob.escribir_xlsx(tmp_path / "otro.xlsx")

    def celdas(ruta):
        libro = openpyxl.load_workbook(ruta)
        return {h.title: [[c.value for c in fila] for fila in h.iter_rows()] for h in libro}

    assert celdas(ob.RUTA_XLSX) == celdas(regenerado)


def test_el_xlsx_de_ob_s2_da_las_mismas_valuaciones_que_la_entrada_a_mano(obra):
    lectura = leer_valuaciones_excel(ob.RUTA_XLSX)
    assert lectura.informe == (
        "Valuaciones: 2 valuacion(es)",
        "Lineas: 3 linea(s)",
        "Costos: 1 costo(s)",
    )
    registrar_lectura(obra, ob.NOMBRE, lectura, fuente="XLSX ficticio", responsable="Ing.")
    del_excel = valuaciones_registradas(obra, ob.NOMBRE)
    a_mano = ob.v01_v02()
    assert [(v.numero, v.desde, v.hasta, v.fecha, v.inspector, v.lineas) for v in del_excel] == [
        (v.numero, v.desde, v.hasta, v.fecha, v.inspector, v.lineas) for v in a_mano
    ]
    assert all(v.origen == "excel:ob_s2.xlsx" for v in del_excel)
    costo = obra.scalars(select(models.CostoReal)).one()
    assert (costo.monto, costo.moneda, costo.fecha) == (D("1280.00"), "USD", date(2026, 11, 13))


def test_un_numero_ya_registrado_se_rechaza_entero_y_no_escribe(obra):
    ob.registrar(obra, ob.V01)
    antes = (_cuenta(obra, models.Valuacion), _cuenta(obra, models.CostoReal))
    with pytest.raises(ValueError, match="V-01 ya estan registradas"):
        registrar_lectura(
            obra, ob.NOMBRE, leer_valuaciones_excel(ob.RUTA_XLSX), fuente="x", responsable="I"
        )
    assert (_cuenta(obra, models.Valuacion), _cuenta(obra, models.CostoReal)) == antes


def test_el_archivo_no_corrige_se_anula_y_se_vuelve_a_registrar(obra):
    primera = ob.registrar(obra, ob.V01)
    anular_valuacion(obra, primera.id, motivo="error de medicion", responsable="Ing.")
    registrar_lectura(
        obra, ob.NOMBRE, leer_valuaciones_excel(ob.RUTA_XLSX), fuente="x", responsable="I"
    )
    assert [v.numero for v in valuaciones_registradas(obra, ob.NOMBRE)] == ["V-01", "V-02"]


def _quitar_hoja(nombre):
    return lambda libro: libro.remove(libro[nombre])


def _quitar_columna(hoja, columna):
    def cambiar(libro):
        fila = libro[hoja][1]
        celda = next(c for c in fila if c.value == columna)
        libro[hoja].delete_cols(celda.column)

    return cambiar


def _escribir(hoja, fila, columna, valor):
    def cambiar(libro):
        libro[hoja].cell(row=fila, column=columna, value=valor)

    return cambiar


def _repetir_numero(libro):
    libro["Valuaciones"].append(["V-01", "2026-11-16", "2026-11-20", "", "Ing. Ficticio"])


@pytest.mark.parametrize(
    ("cambiar", "mensaje"),
    [
        (_quitar_hoja("Valuaciones"), "malo.xlsx: falta la hoja 'Valuaciones'"),
        (_quitar_hoja("Lineas"), "malo.xlsx: falta la hoja 'Lineas'"),
        (_quitar_columna("Lineas", "cantidad"), "hoja Lineas: faltan las columnas cantidad"),
        (_quitar_columna("Valuaciones", "hasta"), "hoja Valuaciones: faltan las columnas hasta"),
        (_escribir("Valuaciones", 2, 2, "02/11/2026"), "hoja Valuaciones, fila 2: desde"),
        (_escribir("Lineas", 3, 3, "-5"), "hoja Lineas, fila 3: la cantidad de 'OB-A' no puede"),
        (_escribir("Lineas", 2, 3, "cuarenta"), "hoja Lineas, fila 2: cantidad 'cuarenta'"),
        (_escribir("Lineas", 2, 1, "V-77"), "hoja Lineas, fila 2: la valuacion 'V-77' no esta"),
        (_repetir_numero, "hoja Valuaciones, fila 4: el numero V-01 esta repetido"),
        (_escribir("Valuaciones", 2, 1, ""), "hoja Valuaciones, fila 2: falta el numero"),
        (_escribir("Costos", 2, 4, "EUR"), "hoja Costos, fila 2: moneda 'EUR'"),
        (_escribir("Costos", 2, 6, ""), "hoja Costos, fila 2: falta la fuente"),
        (_escribir("Costos", 2, 3, "-1"), "hoja Costos, fila 2: el monto no puede ser negativo"),
    ],
)
def test_cada_malformacion_da_su_mensaje_sin_traceback_y_sin_escribir(
    obra, tmp_path, cambiar, mensaje
):
    ruta = _libro(tmp_path, cambiar)
    with pytest.raises(ValueError) as error:
        registrar_lectura(
            obra, ob.NOMBRE, leer_valuaciones_excel(ruta), fuente="x", responsable="I"
        )
    assert mensaje in str(error.value)
    assert "Traceback" not in str(error.value)
    assert _cuenta(obra, models.Valuacion) == _cuenta(obra, models.CostoReal) == 0


def test_una_valuacion_sin_lineas_se_rechaza(tmp_path):
    ruta = _libro(tmp_path, lambda libro: libro["Lineas"].delete_rows(3, 2))
    with pytest.raises(ValueError, match="V-02 no tienen lineas"):
        leer_valuaciones_excel(ruta)


def test_un_archivo_que_no_es_xlsx_o_pesa_mas_de_20_mb_se_rechaza(tmp_path):
    csv = tmp_path / "valuaciones.csv"
    csv.write_text("numero\n", encoding="utf-8")
    with pytest.raises(ValueError, match="libro .xlsx"):
        leer_valuaciones_excel(csv)
    grande = tmp_path / "grande.xlsx"
    with grande.open("wb") as archivo:
        archivo.truncate(LIMITE_BYTES + 1)
    with pytest.raises(ValueError, match="pesa mas de 20 MB"):
        leer_valuaciones_excel(grande)


def test_las_cantidades_decimales_se_leen_exactas_como_texto(tmp_path):
    ruta = _libro(tmp_path, _escribir("Lineas", 2, 3, "40.125"))
    primera = leer_valuaciones_excel(ruta).valuaciones[0]
    assert primera.lineas[0].cantidad == D("40.125")
```
  La prueba que S1 deja a S2 (`test_estudio_cita_valuaciones_por_fecha_hasta`): el estudio cita el número de cada valuación usada y su monto reconocido de noviembre es 75,90:
```python
# tests/integration/test_estudio_cita_valuaciones.py
"""SL-E4, puente a S1 (RV-11; S1 §8.6, criterio de RF-71): el estudio de reajuste cita las
valuaciones registradas y no anuladas por su fecha *hasta*.

Es la prueba que S1 deja a S2 (`test_estudio_cita_valuaciones_por_fecha_hasta`): se escribe en la
fase que entrega `ejecutado_por_periodo`. Usa la revaloración `OB-R01` y la cláusula de
`tests/fixtures/reajuste_ob_s2.py`; el monto reconocido de noviembre es 75,90 (memoria OB-S2).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from core import models
from core.budget.puente import estudio_con_valuaciones, valuaciones_citadas
from core.budget.reajuste import cargar_estudio
from core.budget.valuaciones import anular_valuacion
from core.verification.valuaciones import LineaValuacion
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz

D = Decimal


@pytest.fixture
def con_revaloracion(obra):
    rz.sembrar_revaloracion(obra)
    return obra


def _estudio(sesion, periodos, fecha_calculo=date(2026, 11, 13), **extra):
    return estudio_con_valuaciones(
        sesion,
        ob.NOMBRE,
        ob.CODIGO,
        rz.CLAUSULA,
        periodos,
        fecha_calculo=fecha_calculo,
        fuente="estudio ficticio",
        responsable="Ing.",
        **extra,
    )


def _valuar(sesion, numero, desde, hasta, **cantidades):
    return ob.registrar(
        sesion,
        dict(
            numero=numero,
            desde=desde,
            hasta=hasta,
            fecha=hasta,
            inspector=ob.INSPECTOR,
            lineas=[LineaValuacion(codigo, D(c)) for codigo, c in cantidades.items()],
        ),
    )


def test_el_estudio_usa_lo_ejecutado_de_las_valuaciones_y_cita_cada_una(con_revaloracion):
    ob.registrar_v01_y_v02(con_revaloracion)
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE])
    cargado = cargar_estudio(con_revaloracion, estudio.id)
    periodo = cargado.resultado.periodos[0]
    assert dict(periodo.reajustables) == {"OB-A": D(90), "OB-B": D(60)}
    assert periodo.reconocido == D("75.90")  # A 90 x 0,00 + B 60 x (7,59 - 6,325)
    assert [e.fuente for e in cargado.periodos[0].ejecutado] == [
        "valuaciones V-01, V-02",
        "valuaciones V-02",
    ]
    assert valuaciones_citadas(con_revaloracion, estudio.id) == {0: ["V-01", "V-02"]}


def test_estudio_cita_valuaciones_por_fecha_hasta(con_revaloracion):
    """El criterio del puente: *hasta* = último día del mes cae en ese período y *hasta* = primer
    día del siguiente cae en el siguiente; una anulada no cuenta; una registrada cuenta sin otro
    paso; el estudio cita el número de cada valuación usada."""
    _valuar(con_revaloracion, "V-01", date(2026, 11, 23), date(2026, 11, 30), **{"OB-A": "10"})
    _valuar(con_revaloracion, "V-02", date(2026, 12, 1), date(2026, 12, 4), **{"OB-A": "7"})
    anulada = _valuar(
        con_revaloracion, "V-03", date(2026, 12, 7), date(2026, 12, 11), **{"OB-A": "50"}
    )
    anular_valuacion(con_revaloracion, anulada.id, motivo="no aprobada", responsable="Ing.")
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE, rz.DICIEMBRE], date(2026, 12, 31))
    cargado = cargar_estudio(con_revaloracion, estudio.id)
    assert [dict(p.reajustables) for p in cargado.resultado.periodos] == [
        {"OB-A": D(10)},
        {"OB-A": D(7)},
    ]
    assert valuaciones_citadas(con_revaloracion, estudio.id) == {0: ["V-01"], 1: ["V-02"]}


def test_lo_ejecutado_sobre_lo_presupuestado_se_guarda_y_se_reajusta_hasta_el_tope(
    con_revaloracion,
):
    ob.registrar_v01_y_v02(con_revaloracion)
    ob.registrar(con_revaloracion, ob.VS)  # B 150 mas: 210 contra 200
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE], date(2026, 11, 30))
    cargado = cargar_estudio(con_revaloracion, estudio.id)
    periodo = cargado.resultado.periodos[0]
    assert dict(periodo.reajustables)["OB-B"] == D(200)
    assert periodo.excesos  # S1 lo declara: no se reajusta lo que excede lo presupuestado
    assert "OB-D" not in dict(periodo.reajustables)  # no presupuestada: no se entrega a S1
    assert cargado.estado.value == "cerrado"


def test_el_estudio_recargado_es_identico_aunque_se_anule_una_valuacion_despues(
    con_revaloracion,
):
    primera, _ = ob.registrar_v01_y_v02(con_revaloracion)
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE])
    antes = cargar_estudio(con_revaloracion, estudio.id).resultado.periodos[0]
    anular_valuacion(con_revaloracion, primera.id, motivo="error", responsable="Ing.")
    despues = cargar_estudio(con_revaloracion, estudio.id).resultado.periodos[0]
    assert (despues.reconocido, dict(despues.reajustables)) == (
        antes.reconocido,
        dict(antes.reajustables),
    )


def test_un_periodo_sin_valuaciones_queda_con_cero_y_sin_citas(con_revaloracion):
    ob.registrar_v01_y_v02(con_revaloracion)
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE, rz.DICIEMBRE], date(2026, 12, 31))
    assert valuaciones_citadas(con_revaloracion, estudio.id) == {0: ["V-01", "V-02"]}
    filas = con_revaloracion.scalars(
        select(models.CitaValuacion).join(
            models.PeriodoReajuste, models.PeriodoReajuste.id == models.CitaValuacion.periodo_id
        )
    ).all()
    assert len(filas) == 2
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/integration/test_ejecutado_por_periodo.py tests/integration/test_importar_valuaciones.py tests/integration/test_estudio_cita_valuaciones.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'ejecutado_por_periodo' from 'core.budget.valuaciones'`
```bash
git add tests/fixtures/reajuste_ob_s2.py tests/integration/test_ejecutado_por_periodo.py tests/integration/test_importar_valuaciones.py tests/integration/test_estudio_cita_valuaciones.py
git commit -m "test(core): ejecutado por periodo, Excel de valuaciones y estudio con citas en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  `core/budget/valuaciones.py` gana (RP7-8: las partidas fuera de la línea base se marcan `en_linea_base=False` y no se entregan a S1):
```diff
--- a/core/budget/valuaciones.py
+++ b/core/budget/valuaciones.py
@@ -20,11 +20,13 @@
 from __future__ import annotations
 
 import json
+from collections import defaultdict
 from collections.abc import Mapping, Sequence
-from dataclasses import dataclass
+from dataclasses import dataclass, field
 from datetime import date, datetime
-from decimal import Decimal
+from decimal import Decimal, InvalidOperation
 from functools import partial
+from pathlib import Path
 
 from sqlalchemy import select
 from sqlalchemy.orm import Session
@@ -40,6 +42,7 @@
 from core.budget.persistencia import cargar_presupuesto
 from core.catalog import Catalogo
 from core.catalog.moneda import exigir_moneda
+from core.catalog.precios import PRIMERA_FILA_DE_DATOS, leer_tabla
 from core.contracts.apu import ParametrosCosto
 from core.contracts.presupuesto import Presupuesto
 from core.contracts.verificacion import ReglaVerificacion
@@ -55,22 +58,44 @@
 )
 
 __all__ = [
+    "COLUMNAS_COSTOS",
+    "COLUMNAS_LINEAS",
+    "COLUMNAS_VALUACIONES",
+    "HOJA_COSTOS",
+    "HOJA_LINEAS",
+    "HOJA_VALUACIONES",
+    "LIMITE_BYTES",
     "Calendario",
+    "CostoLeido",
     "CostoReal",
+    "EjecutadoDelPeriodo",
     "InstantaneaControl",
+    "LecturaControl",
     "LineaBase",
+    "LineaEjecutada",
     "LineaBaseInvalidada",
     "anexo_control",
     "anular_valuacion",
+    "ejecutado_por_periodo",
     "instantanea_control",
+    "leer_valuaciones_excel",
     "registrar_costo",
+    "registrar_lectura",
     "registrar_linea_base",
     "registrar_valuacion",
     "tabla_valuaciones",
 ]
 
 CERO = Decimal(0)
+LIMITE_BYTES = 20 * 1024 * 1024  # RNF-12: el mismo límite que los planos
+HOJA_VALUACIONES = "Valuaciones"
+HOJA_LINEAS = "Lineas"
+HOJA_COSTOS = "Costos"
+COLUMNAS_VALUACIONES = ("numero", "desde", "hasta", "fecha", "inspector")
+COLUMNAS_LINEAS = ("numero", "codigo_partida", "cantidad", "fecha_medicion", "observacion")
+COLUMNAS_COSTOS = ("numero", "codigo_partida", "monto", "moneda", "fecha", "fuente")
 ORIGEN_MANUAL = "manual"
+PREFIJO_ORIGEN_EXCEL = "excel:"
 MENSAJE_INVALIDADA = "linea base invalidada: declarela de nuevo"
 
 
@@ -504,9 +529,326 @@
 # ---------------------------------------------------------------------------------------------
 
 
+@dataclass(frozen=True, slots=True)
+class LineaEjecutada:
+    """Lo ejecutado de una partida en un período: `cantidad` es la del período y `reajustable`
+    `min(Q al cierre, q) - min(Q al cierre anterior, q)`; `valuaciones` son las que la aportan.
+    Una partida que la línea base no tiene (`en_linea_base` falso) no tiene reajustable: R13 la
+    marca y no se entrega a S1, que no tiene PU del contrato para ella."""
+
+    codigo: str
+    cantidad: Decimal
+    reajustable: Decimal
+    valuaciones: tuple[str, ...]
+    en_linea_base: bool = True
+
+
+@dataclass(frozen=True, slots=True)
+class EjecutadoDelPeriodo:
+    """Lo ejecutado de un período de la cláusula: las valuaciones citadas, las partidas y los
+    avisos (por ejemplo, lo ejecutado por encima de lo presupuestado, que R13 marca)."""
+
+    desde: date
+    hasta: date
+    valuaciones: tuple[Valuacion, ...]
+    lineas: tuple[LineaEjecutada, ...]
+    avisos: tuple[str, ...] = field(default=())
+
+
+def _cantidades_de_la_linea_base(version: models.Presupuesto) -> dict[str, Decimal]:
+    cantidades: dict[str, Decimal] = defaultdict(lambda: CERO)
+    for renglon in version.partidas:
+        cantidades[renglon.partida.codigo] += renglon.cantidad
+    return cantidades
+
+
+def ejecutado_por_periodo(
+    session: Session,
+    proyecto_nombre: str,
+    periodos: Sequence[tuple[date, date]],
+) -> tuple[EjecutadoDelPeriodo, ...]:
+    """Lo ejecutado de cada período `(desde, hasta)` de la cláusula, con las valuaciones
+    registradas y no anuladas, cada una entera en el período que contiene su *hasta* (S2-R16).
+
+    La cantidad reajustable usa lo acumulado desde el inicio de la obra (incluidas las valuaciones
+    de períodos anteriores al primero que se pide) contra lo presupuestado de la línea base
+    vigente al último cierre. `LineaBaseInvalidada` si un cambio de moneda la invalidó."""
+    if not periodos:
+        raise ValueError("pida al menos un periodo")
+    ordenados = sorted(periodos)
+    proyecto = _proyecto(session, proyecto_nombre)
+    cierre = ordenados[-1][1]
+    candidatas = [f for f in _lineas_base(session, proyecto.id) if f.desde <= cierre]
+    if not candidatas:
+        raise ValueError(f"no hay linea base de control declarada al {cierre.isoformat()}")
+    version = session.get(models.Presupuesto, candidatas[-1].presupuesto_id)
+    if version.moneda != moneda_del_proyecto(session, proyecto):
+        raise LineaBaseInvalidada(MENSAJE_INVALIDADA)
+    presupuestado = _cantidades_de_la_linea_base(version)
+    cuentan = valuaciones_registradas(session, proyecto_nombre)
+    acumulado: dict[str, Decimal] = defaultdict(lambda: CERO)
+    for valuacion in cuentan:
+        if valuacion.hasta < ordenados[0][0]:
+            for linea in valuacion.lineas:
+                acumulado[linea.codigo_partida] += linea.cantidad
+    salida: list[EjecutadoDelPeriodo] = []
+    for desde, hasta in ordenados:
+        del_periodo = [v for v in cuentan if desde <= v.hasta <= hasta]
+        cantidades: dict[str, Decimal] = defaultdict(lambda: CERO)
+        citas: dict[str, list[str]] = defaultdict(list)
+        for valuacion in del_periodo:
+            for linea in valuacion.lineas:
+                cantidades[linea.codigo_partida] += linea.cantidad
+                if valuacion.clave not in citas[linea.codigo_partida]:
+                    citas[linea.codigo_partida].append(valuacion.clave)
+        lineas: list[LineaEjecutada] = []
+        avisos: list[str] = []
+        for codigo, cantidad in cantidades.items():
+            q = presupuestado.get(codigo, CERO)
+            antes = acumulado[codigo]
+            despues = antes + cantidad
+            reajustable = min(despues, q) - min(antes, q)
+            acumulado[codigo] = despues
+            lineas.append(
+                LineaEjecutada(
+                    codigo, cantidad, reajustable, tuple(citas[codigo]), codigo in presupuestado
+                )
+            )
+            if reajustable != cantidad:
+                avisos.append(
+                    f"{codigo}: ejecutado {cantidad} en el periodo y solo {reajustable} es "
+                    f"reajustable (presupuestado {q}; lo que excede lo marca R13)"
+                )
+        salida.append(
+            EjecutadoDelPeriodo(desde, hasta, tuple(del_periodo), tuple(lineas), tuple(avisos))
+        )
+    return tuple(salida)
+
+
 # ---------------------------------------------------------------------------------------------
 # Importación de Excel (RF-73, §6.2)
 # ---------------------------------------------------------------------------------------------
+
+
+@dataclass(frozen=True, slots=True)
+class CostoLeido:
+    """Una fila de la hoja `Costos`: el costo, y el número de la valuación que lo cita si lo hay."""
+
+    numero: str
+    codigo_partida: str | None
+    monto: Decimal
+    moneda: str
+    fecha: date
+    fuente: str
+
+
+@dataclass(frozen=True, slots=True)
+class LecturaControl:
+    """Lo que se lee del XLSX antes de escribir nada: las valuaciones (sin registrar), los costos
+    y el informe previo (una línea por hoja)."""
+
+    valuaciones: tuple[Valuacion, ...]
+    costos: tuple[CostoLeido, ...]
+    informe: tuple[str, ...]
+
+
+def _donde(ruta: Path, hoja: str, fila: int | None = None) -> str:
+    return f"{ruta.name}, hoja {hoja}" + (f", fila {fila}" if fila is not None else "")
+
+
+def _decimal(texto: str, donde: str, columna: str) -> Decimal:
+    try:
+        valor = Decimal(texto)
+    except InvalidOperation:
+        raise ValueError(f"{donde}: {columna} {texto!r} no es un numero decimal") from None
+    if not valor.is_finite():
+        raise ValueError(f"{donde}: {columna} {texto!r} no es un numero finito")
+    return valor
+
+
+def _fecha(texto: str, donde: str, columna: str, *, opcional: bool = False) -> date | None:
+    if not texto and opcional:
+        return None
+    try:
+        return date.fromisoformat(texto[:10])
+    except ValueError:
+        raise ValueError(f"{donde}: {columna} {texto!r} no es una fecha ISO (AAAA-MM-DD)") from None
+
+
+def _filas(ruta: Path, hoja: str, columnas: tuple[str, ...]) -> list[tuple[int, dict[str, str]]]:
+    tabla = leer_tabla(ruta, hoja)
+    faltan = [c for c in columnas if c not in tabla.columns]
+    if faltan:
+        raise ValueError(
+            f"{_donde(ruta, hoja)}: faltan las columnas {', '.join(faltan)}; "
+            f"se esperan {', '.join(columnas)}"
+        )
+    return [
+        (numero, {c: str(fila[c]).strip() for c in columnas})
+        for numero, fila in enumerate(tabla.to_dict("records"), start=PRIMERA_FILA_DE_DATOS)
+    ]
+
+
+def leer_valuaciones_excel(ruta: Path) -> LecturaControl:
+    """Lee un XLSX de valuaciones (y costos) con las hojas y columnas de §6.2. No toca la base.
+
+    Todo error de forma es `ValueError` con el archivo, la hoja y la fila, sin *traceback* útil
+    para el usuario: archivo de más de 20 MB, formato que no es XLSX, hoja o columna ausente,
+    número repetido, número de `Lineas` sin su valuación, fecha o número ilegibles, cantidad
+    negativa. Un archivo malformado se rechaza entero."""
+    if ruta.suffix.lower() not in (".xlsx", ".xlsm"):
+        raise ValueError(f"{ruta.name}: las valuaciones se importan de un libro .xlsx")
+    if ruta.stat().st_size > LIMITE_BYTES:
+        raise ValueError(f"{ruta.name}: pesa mas de {LIMITE_BYTES // (1024 * 1024)} MB")
+    cabeceras: dict[str, dict[str, str]] = {}
+    for numero, fila in _filas(ruta, HOJA_VALUACIONES, COLUMNAS_VALUACIONES):
+        donde = _donde(ruta, HOJA_VALUACIONES, numero)
+        if not fila["numero"]:
+            raise ValueError(f"{donde}: falta el numero de la valuacion")
+        if fila["numero"] in cabeceras:
+            raise ValueError(f"{donde}: el numero {fila['numero']} esta repetido en el archivo")
+        _fecha(fila["desde"], donde, "desde")
+        _fecha(fila["hasta"], donde, "hasta")
+        _fecha(fila["fecha"], donde, "fecha", opcional=True)
+        cabeceras[fila["numero"]] = fila
+    lineas: dict[str, list[LineaValuacion]] = defaultdict(list)
+    for numero, fila in _filas(ruta, HOJA_LINEAS, COLUMNAS_LINEAS):
+        donde = _donde(ruta, HOJA_LINEAS, numero)
+        if fila["numero"] not in cabeceras:
+            raise ValueError(
+                f"{donde}: la valuacion {fila['numero']!r} no esta en la hoja {HOJA_VALUACIONES}"
+            )
+        cantidad = _decimal(fila["cantidad"], donde, "cantidad")
+        try:
+            lineas[fila["numero"]].append(
+                LineaValuacion(
+                    fila["codigo_partida"],
+                    cantidad,
+                    _fecha(fila["fecha_medicion"], donde, "fecha_medicion", opcional=True),
+                    fila["observacion"],
+                )
+            )
+        except ValueError as error:
+            raise ValueError(f"{donde}: {error}") from None
+    sin_lineas = [n for n in cabeceras if not lineas[n]]
+    if sin_lineas:
+        raise ValueError(
+            f"{_donde(ruta, HOJA_LINEAS)}: las valuaciones {', '.join(sin_lineas)} no tienen lineas"
+        )
+    valuaciones = tuple(
+        Valuacion(
+            id=0,
+            numero=n,
+            desde=_fecha(c["desde"], "", "desde"),
+            hasta=_fecha(c["hasta"], "", "hasta"),
+            fecha=_fecha(c["fecha"], "", "fecha", opcional=True),
+            inspector=c["inspector"],
+            lineas=tuple(lineas[n]),
+            origen=f"{PREFIJO_ORIGEN_EXCEL}{ruta.name}",
+        )
+        for n, c in cabeceras.items()
+    )
+    costos = _leer_costos(ruta, cabeceras)
+    informe = (
+        f"{HOJA_VALUACIONES}: {len(valuaciones)} valuacion(es)",
+        f"{HOJA_LINEAS}: {sum(len(v.lineas) for v in valuaciones)} linea(s)",
+        f"{HOJA_COSTOS}: {len(costos)} costo(s)",
+    )
+    return LecturaControl(valuaciones, costos, informe)
+
+
+def _leer_costos(ruta: Path, cabeceras: Mapping[str, object]) -> tuple[CostoLeido, ...]:
+    if HOJA_COSTOS not in _hojas(ruta):
+        return ()
+    costos: list[CostoLeido] = []
+    for numero, fila in _filas(ruta, HOJA_COSTOS, COLUMNAS_COSTOS):
+        donde = _donde(ruta, HOJA_COSTOS, numero)
+        if fila["numero"] and fila["numero"] not in cabeceras:
+            raise ValueError(f"{donde}: la valuacion {fila['numero']!r} no esta en el archivo")
+        if not fila["fuente"]:
+            raise ValueError(f"{donde}: falta la fuente del costo")
+        monto = _decimal(fila["monto"], donde, "monto")
+        if monto < CERO:
+            raise ValueError(f"{donde}: el monto no puede ser negativo ({monto})")
+        try:
+            moneda = exigir_moneda(fila["moneda"])
+        except ValueError as error:
+            raise ValueError(f"{donde}: {error}") from None
+        costos.append(
+            CostoLeido(
+                fila["numero"],
+                fila["codigo_partida"] or None,
+                monto,
+                moneda,
+                _fecha(fila["fecha"], donde, "fecha"),
+                fila["fuente"],
+            )
+        )
+    return tuple(costos)
+
+
+def _hojas(ruta: Path) -> list[str]:
+    import openpyxl
+
+    libro = openpyxl.load_workbook(ruta, read_only=True)
+    try:
+        return list(libro.sheetnames)
+    finally:
+        libro.close()
+
+
+def registrar_lectura(
+    session: Session,
+    proyecto_nombre: str,
+    lectura: LecturaControl,
+    *,
+    fuente: str,
+    responsable: str,
+    ahora: datetime | None = None,
+) -> tuple[list[models.Valuacion], list[models.CostoReal]]:
+    """Registra todo lo leído, o nada: una valuación del archivo con el mismo número que una
+    guardada y no anulada se rechaza (el archivo no corrige: se anula y se vuelve a registrar)."""
+    fuente, responsable = _exigir_respaldo(fuente, responsable)
+    guardadas = {v.numero for v in valuaciones_registradas(session, proyecto_nombre)}
+    repetidas = sorted(v.numero for v in lectura.valuaciones if v.numero in guardadas)
+    if repetidas:
+        raise ValueError(
+            f"las valuaciones {', '.join(repetidas)} ya estan registradas: anule la anterior y "
+            "vuelva a importar"
+        )
+    registradas = [
+        registrar_valuacion(
+            session,
+            proyecto_nombre,
+            numero=v.numero,
+            desde=v.desde,
+            hasta=v.hasta,
+            fecha=v.fecha,
+            inspector=v.inspector,
+            lineas=v.lineas,
+            fuente=fuente,
+            responsable=responsable,
+            origen=v.origen,
+            ahora=ahora,
+        )
+        for v in lectura.valuaciones
+    ]
+    por_numero = {fila.numero: fila.id for fila in registradas}
+    costos = [
+        registrar_costo(
+            session,
+            proyecto_nombre,
+            monto=c.monto,
+            moneda=c.moneda,
+            fecha=c.fecha,
+            fuente=c.fuente,
+            responsable=responsable,
+            codigo_partida=c.codigo_partida,
+            valuacion_id=por_numero.get(c.numero),
+        )
+        for c in lectura.costos
+    ]
+    return registradas, costos
 
 
 # ---------------------------------------------------------------------------------------------
```
  El puente con S1 (el estudio se guarda con `guardar_estudio` de S1 y se cita en `cita_valuacion`; `periodos_declarados` es lo que la pantalla de reajuste calcula en memoria, tarea 12):
```python
# core/budget/puente.py
"""Puente entre S1 (reajuste) y S2 (valuaciones), en los dos sentidos (spec S2 §4.7, S1 §8.6).

* `estudio_con_valuaciones` (SL-E4, RF-72): guarda un estudio de reajuste de S1 cuyo ejecutado sale
  de las valuaciones registradas y no anuladas (`ejecutado_por_periodo`) y **cita** cada una en
  `cita_valuacion`. S1 sigue calculando y guardando el estudio con `guardar_estudio`.
* `reajuste_reconocido` (SL-E5, RF-77): la suma de los montos reconocidos de los estudios de S1
  **guardados** con fecha de cálculo menor o igual al corte, sin los reemplazados (S1-R21), en la
  moneda del proyecto. Nunca suma un reajuste proyectado sobre la obra pendiente (S2-R15, RV-12).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _buscar
from core.budget.reajuste import Clausula, Ejecutado, PeriodoDeclarado, guardar_estudio
from core.budget.valuaciones import EjecutadoDelPeriodo, ejecutado_por_periodo
from core.catalog.indices import LADO_POR_DEFECTO

__all__ = [
    "PeriodoDelEstudio",
    "estudio_con_valuaciones",
    "periodos_declarados",
]

CERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class PeriodoDelEstudio:
    """Un período del estudio: sus fechas y, opcionales, la versión revalorada para la comprobación
    directa y la excepción declarada (S1 §8.2)."""

    desde: date
    hasta: date
    version_comprobacion: str = ""
    excepcion: str = ""


def _declarar(
    session: Session, proyecto_nombre: str, periodos: Sequence[PeriodoDelEstudio]
) -> tuple[list[PeriodoDelEstudio], list[PeriodoDeclarado], list[EjecutadoDelPeriodo]]:
    ordenados = sorted(periodos, key=lambda p: (p.desde, p.hasta))
    ejecutados = ejecutado_por_periodo(
        session, proyecto_nombre, [(p.desde, p.hasta) for p in ordenados]
    )
    declarados = [
        PeriodoDeclarado(
            periodo.desde,
            periodo.hasta,
            tuple(
                Ejecutado(
                    linea.codigo, linea.cantidad, "valuaciones " + ", ".join(linea.valuaciones)
                )
                for linea in ejecutado.lineas
                if linea.en_linea_base
            ),
            periodo.version_comprobacion,
            periodo.excepcion,
        )
        for periodo, ejecutado in zip(ordenados, ejecutados, strict=True)
    ]
    return ordenados, declarados, ejecutados


def periodos_declarados(
    session: Session, proyecto_nombre: str, periodos: Sequence[PeriodoDelEstudio]
) -> list[PeriodoDeclarado]:
    """Los períodos de S1 con lo ejecutado de las valuaciones registradas y no anuladas, sin
    guardar nada: es lo que la pantalla de reajuste calcula en memoria (UC-18 paso 3)."""
    return _declarar(session, proyecto_nombre, periodos)[1]


def estudio_con_valuaciones(
    session: Session,
    proyecto_nombre: str,
    codigo_contrato: str,
    clausula: Clausula,
    periodos: Sequence[PeriodoDelEstudio],
    *,
    fecha_calculo: date,
    fuente: str,
    responsable: str,
    reemplaza_a: int | None = None,
    lado: str = LADO_POR_DEFECTO,
    ahora: datetime | None = None,
) -> models.EstudioReajuste:
    """Guarda el estudio de reajuste de la versión `codigo_contrato` con lo ejecutado de las
    valuaciones registradas y no anuladas, asignadas por su *hasta* al período que lo contiene.

    Cada cantidad ejecutada lleva como fuente el número de las valuaciones que la aportan, y cada
    período cita sus valuaciones en `cita_valuacion`. Lo ejecutado por encima de lo presupuestado
    se entrega completo: S1 lo guarda con aviso y reajusta solo `min(Q, q)` (S1-R17). Las partidas
    que la línea base no tiene no se entregan (S1 no tiene su PU del contrato; R13 las marca).
    Hace `flush`, no `commit`."""
    ordenados, declarados, ejecutados = _declarar(session, proyecto_nombre, periodos)
    estudio = guardar_estudio(
        session,
        _buscar(session, proyecto_nombre, codigo_contrato),
        clausula,
        declarados,
        fecha_calculo=fecha_calculo,
        fuente=fuente,
        responsable=responsable,
        reemplaza_a=reemplaza_a,
        lado=lado,
        ahora=ahora,
    )
    filas = session.scalars(
        select(models.PeriodoReajuste)
        .where(models.PeriodoReajuste.estudio_id == estudio.id)
        .order_by(models.PeriodoReajuste.orden)
    ).all()
    for fila, ejecutado in zip(filas, ejecutados, strict=True):
        session.add_all(
            models.CitaValuacion(periodo_id=fila.id, valuacion_id=valuacion.id)
            for valuacion in ejecutado.valuaciones
        )
    session.flush()
    return estudio


def valuaciones_citadas(session: Session, estudio_id: int) -> dict[int, list[str]]:
    """Por orden de período, el número de las valuaciones que el estudio citó."""
    filas = session.execute(
        select(models.PeriodoReajuste.orden, models.Valuacion.numero, models.Valuacion.id)
        .join(models.CitaValuacion, models.CitaValuacion.periodo_id == models.PeriodoReajuste.id)
        .join(models.Valuacion, models.Valuacion.id == models.CitaValuacion.valuacion_id)
        .where(models.PeriodoReajuste.estudio_id == estudio_id)
        .order_by(models.PeriodoReajuste.orden, models.Valuacion.id)
    )
    citadas: dict[int, list[str]] = {}
    for orden, numero, _ in filas:
        citadas.setdefault(orden, []).append(numero)
    return citadas
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/integration/test_ejecutado_por_periodo.py tests/integration/test_importar_valuaciones.py tests/integration/test_estudio_cita_valuaciones.py tests/integration/test_valuaciones.py tests/unit/test_r13_r14.py tests/unit/test_calendario.py tests/unit/test_reajuste.py tests/integration/test_estudio_reajuste.py -q -W error` → verde (36 pruebas nuevas; las de S1 no cambian).
Run: `uv run ruff check core/budget/valuaciones.py core/budget/puente.py tests/fixtures/reajuste_ob_s2.py tests/integration/test_ejecutado_por_periodo.py tests/integration/test_importar_valuaciones.py tests/integration/test_estudio_cita_valuaciones.py` y la guardia del núcleo.
- [ ] **Paso 5: Commit**
```bash
git add core/budget/valuaciones.py core/budget/puente.py
git commit -m "feat(core): ejecutado por periodo, lector de Excel y estudio de reajuste con valuaciones citadas" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS2-1 y foco de revisión de la fase

**Compuerta GS2-1** (se cruza al fusionar `inc/070-s2-1-nucleo`):
1. `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-1 --junit reporte-pruebas.xml` → todas las filas en OK: C1 (los diez requisitos por presencia), C2 (cero omitidas), C3 (cada `ParTDD` de `S2-0` y `S2-1`: la prueba de calendario, R13/R14, valuaciones, importación, ejecutado por período y migración precede a su código), C4 (`core/contracts/` intacto desde `v0.6.0`), C5 (bloque de regresión), C7 (guardia de red), `S2-MEM`, `S2-REGLAS`, `S2-EXPEDIENTES`, `S2-REG-S1`.
2. CI verde en Linux y Windows, `-W error`, y el paso de la meta en `--hasta S2-1`.
3. Bloque de regresión literal (sección final) en verde y `git diff v0.6.0..HEAD -- <ARCHIVOS_REGRESION>` vacío.
4. Prueba de deriva RNF-20 en verde con `caso_0005_s2_valuaciones`; `test_migracion_s2.py` en verde sobre las bases de la 0.5.0 y la 0.6.0.
5. `uv run python scripts/guardia_nucleo.py --base origin/main` en 0; `uv run ruff check` sobre los archivos tocados.
6. Aprobación de los encargos (requisitos, arquitectura, pruebas y calidad) y aval del tutor de SL-E4; compuerta anotada en `docs/bitacora/2026-10-silice-070.md`.

**Foco de revisión de S2-1** (entradas que el spec implica y que ninguna prueba ejercitaba; cada una con la prueba que la fija):
1. **Una valuación anulada deja de contar, pero queda:** nada la borra ni la edita (S2-R10) → `tests/integration/test_valuaciones.py` (`test_una_valuacion_anulada_se_conserva_y_deja_de_contar` y `test_ninguna_funcion_emite_update_ni_delete_sobre_las_tablas_solo_agregar`) (Tarea 5).
2. **Una valuación con fecha de corte posterior:** R14(b) marca como ERROR la valuación cuyo *hasta* es posterior al corte, sin que EV la cuente → `tests/unit/test_r13_r14.py::test_r14_la_valuacion_no_termina_despues_del_corte` (Tarea 5).
3. **Excel con una hoja que falta o un número con coma:** el archivo se rechaza **entero**, con la hoja o la fila, sin escribir nada → `tests/integration/test_importar_valuaciones.py::test_cada_malformacion_da_su_mensaje_sin_traceback_y_sin_escribir` (Tarea 6).
4. **Lo ejecutado por encima de lo presupuestado:** S1 reajusta solo `min(Q, q)` y R13 marca el exceso con su impacto → `tests/integration/test_ejecutado_por_periodo.py::test_lo_valuado_sobre_lo_presupuestado_entrega_el_total_y_reajusta_el_tope_con_aviso` (Tarea 6).
5. **Cambiar la moneda del proyecto después de declarar la línea base:** la línea base queda invalidada (`LineaBaseInvalidada`), nunca se convierte en silencio → `tests/integration/test_ejecutado_por_periodo.py::test_tras_un_cambio_de_moneda_la_linea_base_invalidada_se_rechaza` (Tarea 6).

### Discrepancias encontradas (S2-1)

1. **Siete tablas del spec contra nueve del código.** El expediente del spec (§5.4, SL-E4) dice «7 tablas»; con `cita_valuacion` (RP7-4) son 8 en `caso_0005`, y `decision_recuperacion` (SL-E6) hace 9. *Resuelta:* el plan sigue al código y lo anota en el expediente.
2. **`calendario.py` en SL-E5 o SL-E4.** El spec lo nombra en SL-E5 (§5.2), pero R14 necesita contar días hábiles. *Resuelta (RP7-2):* entra con SL-E4.
3. **Las reglas importan «solo contratos».** El spec dice que R13 y R14 importan solo contratos; el código necesita los tipos de valuación y un contador de días. *Resuelta (RP7-3):* los tipos viven en `core/verification/valuaciones.py` y los días hábiles se inyectan.
4. **Partidas no presupuestadas hacia S1.** `reajuste._pu_de` de S1 rechaza una partida que el contrato no tiene. *Resuelta (RP7-8):* el puente no las entrega; R13 las marca.
5. **Líneas de más de 100 columnas en bloques de la 0.6.0** (E501, N817, B905 en código de S1 que el plan de la 0.6.0 dejó abierto): no se tocan; S2 no los hereda.

---

# S2-2 — Valor ganado, separación del desvío y reproyección (rama `inc/070-s2-2-nucleo`, SL-E5)

Solo `core/`, `migraciones/`, `tests/`, `scripts/` (el generador) y `docs/`. Sale de `origin/main` con S2-1 fusionada y el
aval del tutor de SL-E5. Al terminar, el sistema calcula al corte PV, EV, AC, SV, CV, SPI, CPI, EAC y VAC, separa el
desvío en plazo, precio y consumo, evalúa AL-1 a AL-6, reproyecta plan, término, costo final y PE, y suma el reajuste
reconocido de los estudios de S1. Nada de esto toca la base de datos: se calcula sobre lo guardado (S2-R13).

### Tarea 7: SL-E5a — equilibrio extraído y valor ganado con su separación

**Rama:** `inc/070-s2-2-nucleo` (solo `core/`, `migraciones/`, `tests/`, `scripts/`, `docs/`; sale de `main` con S2-1 fusionada)   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/budget/valor_ganado.py`, `core/budget/control.py`, `tests/unit/test_valor_ganado.py`, `tests/unit/test_equilibrio_extraido.py`
- Modificar: `core/budget/equilibrio.py` (extrae `equilibrio(venta, costo_variable, costo_fijo, curva)` de `punto_equilibrio`; `_ubicar(curva, punto)`; ver el parche del paso 3)

**Interfaces:**
- Consume: de S2-1: `core.budget.valuaciones.{InstantaneaControl, CostoReal, instantanea_control, linea_base_vigente, dia_del_corte}`, `core.budget.calendario`; del núcleo: `core.budget.equilibrio.{punto_equilibrio, EstadoEquilibrio, ResultadoEquilibrio}`, `core.budget.curva.{PeriodoPlan, curva_de_costos}`, `core.contracts.{Presupuesto, ParametrosCosto}`, `core.catalog.moneda.{convertir}`, `core.catalog.indices.tasa_aplicable` (S1).
- Produce:
- `core/budget/valor_ganado.py`:
  - `PERSPECTIVA_COSTO = 'costo'`
  - `PERSPECTIVA_PRECIO = 'precio'`
  - `NATURALEZA_DECLARADA = 'SUPUESTO_DECLARADO'`
  - `UNO = Decimal(1)`
  - `CIEN = Decimal(100)`
  - `PRECISION_DE_DIAS = Decimal('1e-12')`
  - `def techo_de_dias(dias: Decimal) -> int`
  - `class ParametrosControl [spi_error: Decimal; cpi_error: Decimal; retraso_error: Decimal; precio_info: Decimal; equilibrio_puntos: Decimal; eta_cuadrilla: Decimal; cuadrillas_max: int; eta_horas_extra: Decimal; horas_extra_dia: Decimal; recargo_horas_extra: Decimal; fcas_en_horas_extra: bool; penalizacion_diaria: Decimal; fuente_penalizacion: str]`
  - `class PartidaControl [codigo: str; cantidad: Decimal; unitario: Decimal; plan: tuple[Decimal, ...]]`
  - `class PreciosDelCorte [metodo: str; fuente: str; unitarios: Mapping[str, Decimal]]`
  - `class EstadoObra [partidas: tuple[PartidaControl, ...]; etiquetas: tuple[str, ...]; dias_por_periodo: int; dia: int; ejecutado: Mapping[str, Decimal]; por_periodo: Mapping[tuple[str, int], Decimal]; perspectiva: str; costo_real: Decimal | None; motivo_costo: str; precios: PreciosDelCorte | None; dia_ultima_valuacion: int]`
  - `def partidas_de_plan(presupuesto: Presupuesto, plan: Sequence[PeriodoPlan], perspectiva: str) -> tuple[PartidaControl, ...]`
  - `def precios_por_escalatoria(unitarios: Mapping[str, Decimal], coeficientes: Mapping[str, Decimal], r: Decimal, fuente: str) -> PreciosDelCorte`
  - `class Indicadores [bac: Decimal; pv: Decimal; ev: Decimal; ac: Decimal | None; sv: Decimal; cv: Decimal | None; spi: Decimal | None; cpi: Decimal | None; cpi_corte: Decimal | None; eac_indice: Decimal | None; eac_sistema: Decimal | None; vac: Decimal | None; termino_indice: int | None; no_disponible: Mapping[str, str]]`
  - `def indicadores(estado: EstadoObra) -> Indicadores`
  - `class Separacion [plazo: Decimal; precio: Decimal | None; consumo: Decimal | None; vac_precio: Decimal | None; vac_consumo: Decimal | None; metodo: str; fuente: str; no_disponible: Mapping[str, str]]`
  - `def separar_desvio(estado: EstadoObra, calculados: Indicadores | None=None) -> Separacion`
- `core/budget/control.py`:
  - `def construir_estado(instantanea: InstantaneaControl, *, costo_real: Decimal | None, motivo_costo: str='', precios: PreciosDelCorte | None=None) -> EstadoObra`
- `core/budget/equilibrio.py`:
  - `def equilibrio(venta: Decimal, costo_variable: Decimal, costo_fijo: Decimal, curva: Sequence[PuntoCurva]) -> PuntoEquilibrio`

- [ ] **Paso 0: Expediente SL-E5** escrito y aprobado (tarea 3, encabezado `SL‑E5`) y visto bueno del tutor anotado en `docs/bitacora/2026-10-silice-070.md`. Sin ambos la rama no se abre. Recordatorio del expediente: `equilibrio.py` se refactoriza **sin cambiar su resultado** (TI-001 sigue en 28 586,76 USD, Día 6).
- [ ] **Paso 1: Escribir las pruebas que fallan**
  Primero se fija que la extracción no mueve el PE de TI-001 y que `equilibrio` da los mismos estados tipados de SF-E3 (literal de `tests/unit/test_caso_ti001.py`, que no se edita):
```python
# tests/unit/test_equilibrio_extraido.py
"""SL-E5: extraer `equilibrio` de `punto_equilibrio` no mueve ningún resultado (spec S2 §5.2).

`punto_equilibrio(presupuesto, parametros)` llama ahora a `equilibrio(venta, costo_variable,
costo_fijo, curva)` con los mismos argumentos que antes calculaba en su cuerpo; TI-001 sigue en
28 586,76 USD en el Día 6 (regresión literal, sin editar).
"""

from __future__ import annotations

from decimal import Decimal

from core.budget import punto_equilibrio
from core.budget.equilibrio import EstadoEquilibrio, equilibrio
from tests.fixtures import caso_ti001

D = Decimal
MONTOS = D("0.01")


def test_la_extraccion_de_equilibrio_no_mueve_el_pe_de_ti_001():
    """TI-001 sigue en 28 586,76 USD en el Día 6 (regresión literal); `equilibrio` da lo mismo."""
    resultado = caso_ti001.elaborar_caso()
    presupuesto = resultado.presupuesto
    esperado = punto_equilibrio(presupuesto, caso_ti001.PARAMETROS)
    assert abs(esperado.punto - D("28586.76")) <= MONTOS
    assert esperado.periodo.startswith("Dia 6")
    costo_variable = sum(
        (p.item.cantidad * p.resultado.costo_directo for p in presupuesto.partidas), D(0)
    )
    directo = equilibrio(
        presupuesto.total,
        costo_variable,
        costo_variable * caso_ti001.PARAMETROS.administracion,
        presupuesto.curva,
    )
    assert directo == esperado


def test_equilibrio_da_los_estados_tipados_de_sf_e3():
    curva = ()
    assert equilibrio(D(0), D(0), D(0), curva).estado is EstadoEquilibrio.NO_APLICABLE
    assert equilibrio(D(100), D(100), D(10), curva).estado is EstadoEquilibrio.NO_EXISTE
    assert equilibrio(D(100), D(50), D(100), curva).estado is EstadoEquilibrio.NO_SE_ALCANZA
    sin_curva = equilibrio(D(100), D(50), D(25), curva)
    assert sin_curva.estado is EstadoEquilibrio.CALCULADO and sin_curva.periodo is None
    assert sin_curva.punto == D(50)  # CF x V / (V - CV) = 25 x 100 / 50
```
  El valor ganado contra la memoria OB-S2 (PV 1 500, EV 1 200, SPI 0,80, CPI 0,9375, EAC 4 480, EAC por índice 4 266,67, VAC −480; separación: plazo −300, precio −60, consumo −20; CV = precio + consumo exacta):
```python
# tests/unit/test_valor_ganado.py
"""SL-E5: valor ganado y separación del desvío de control (spec S2 §4.2, §4.3; RF-75, RF-76).

El oráculo es la memoria `control_ob_s2.md` (§7.1), a ± 0,01 en montos y ± 0,0001 en índices;
la identidad `CV = precio + consumo` se exige exacta, con `Decimal`, también sobre la obra grande
del generador de RNF-15. Puras: sin base de datos.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from core.budget.control import construir_estado
from core.budget.valor_ganado import (
    PERSPECTIVA_PRECIO,
    indicadores,
    precios_por_escalatoria,
    separar_desvio,
)
from tests.fixtures import control_ob_s2 as ob

D = Decimal
MONTOS = D("0.01")
INDICES = D("0.0001")


PRECIOS = ob.precios_del_corte()


def _estado(valuaciones=None, *, corte=ob.CORTE, costo_real=ob.COSTO_REAL, precios=PRECIOS):
    instantanea = ob.instantanea(ob.v01_v02() if valuaciones is None else valuaciones, corte=corte)
    return construir_estado(instantanea, costo_real=costo_real, precios=precios)


def test_la_tabla_de_la_memoria_ob_s2():
    ind = indicadores(_estado())
    assert (ind.bac, ind.pv, ind.ev, ind.ac) == (D(4000), D(1500), D(1200), D(1280))
    assert (ind.sv, ind.cv) == (D(-300), D(-80))
    assert abs(ind.spi - D("0.8000")) <= INDICES
    assert abs(ind.cpi - D("0.9375")) <= INDICES
    assert abs(ind.cpi_corte - D("0.984375")) <= INDICES
    assert abs(ind.eac_sistema - D("4480.00")) <= MONTOS
    assert abs(ind.eac_indice - D("4266.67")) <= MONTOS
    assert abs(ind.vac - D("-480.00")) <= MONTOS
    assert ind.termino_indice == 25  # techo de 20 / 0,80 = dia habil 25 = 2026-12-04
    assert ind.no_disponible == {}


def test_la_separacion_del_desvio_de_la_memoria_y_su_identidad_exacta():
    estado = _estado()
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert (sep.plazo, sep.precio, sep.consumo) == (D(-300), D(-60), D(-20))
    assert sep.precio + sep.consumo == ind.cv  # exacta, no a +- 0,01
    assert (sep.vac_precio, sep.vac_consumo) == (D(-410), D(-70))
    assert sep.vac_precio + sep.vac_consumo == ind.vac
    assert (sep.metodo, sep.fuente) == ("comprobacion", "version revalorada ficticia")


def test_una_valuacion_registrada_cuenta_en_ev_sin_otro_paso():
    assert indicadores(_estado()).ev == D(1200)
    assert indicadores(_estado(ob.v01_v02()[:1])).ev == D(400)  # solo V-01: A 40 x 10


def test_lo_valuado_sobre_lo_presupuestado_no_gana_valor_s2_r8():
    exceso = ob.valuacion(ob.VS, 3)
    estado = _estado([*ob.v01_v02(), exceso], corte=ob.CORTE_DE_VS)
    assert estado.ejecutado["OB-B"] == D(210)
    assert estado.cantidad_ejecutada(next(p for p in estado.partidas if p.codigo == "OB-B")) == D(
        200
    )
    # EV de B: min(210, 200) x 5; A 90 x 10; C 10 x 20; D no presupuestada: nada.
    assert indicadores(estado).ev == D(900) + D(1000) + D(200)


def test_corte_a_mitad_de_periodo_prorratea_el_plan_por_dias_habiles():
    estado = _estado(corte=date(2026, 11, 11))  # dia habil 8: 3 de 5 dias de la semana 2
    assert estado.dia == 8
    ind = indicadores(estado)
    # A: 0,5 + 0,5 x 3/5 = 0,8 -> 800; B: 0,5 x 3/5 = 0,3 -> 300; C: aun no.
    assert ind.pv == D(1100)


def test_antes_de_todo_trabajo_planificado_pv_es_cero_y_spi_no_aplica():
    ind = indicadores(_estado([], corte=date(2026, 11, 1)))
    assert (ind.pv, ind.ev, ind.spi, ind.termino_indice) == (0, 0, None, None)
    assert "PV = 0" in ind.no_disponible["SPI"]


def test_sin_costos_reales_cpi_no_aplica():
    ind = indicadores(_estado(costo_real=D(0)))
    assert ind.ac == 0 and ind.cpi is None and ind.eac_indice is None and ind.eac_sistema is None
    assert "AC = 0" in ind.no_disponible["CPI"]


def test_un_costo_real_sin_tasa_deja_el_ac_y_lo_que_depende_de_el_no_disponible():
    estado = replace(
        _estado(costo_real=None), motivo_costo="sin tasa aplicable para: 500 Bs del 2026-11-13"
    )
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert (ind.ac, ind.cv, ind.cpi, ind.eac_indice, ind.eac_sistema, ind.vac) == (None,) * 6
    assert "sin tasa aplicable" in ind.no_disponible["AC"]
    assert (sep.consumo, sep.vac_consumo) == (None, None)
    assert sep.precio == D(-60) and sep.vac_precio == D(-410)  # solo dependen de los precios
    assert (ind.pv, ind.ev, ind.sv) == (D(1500), D(1200), D(-300))  # PV, EV, SPI intactos
    assert abs(ind.spi - D("0.8")) <= INDICES


def test_sin_precios_del_corte_la_separacion_no_esta_disponible_y_lo_demas_funciona():
    estado = _estado(precios=None)
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert (ind.eac_sistema, ind.vac) == (None, None)
    assert (sep.precio, sep.consumo, sep.vac_precio) == (None, None, None)
    assert "sin precios del corte" in sep.no_disponible["precio"]
    assert ind.cpi == D("0.9375") and ind.spi == D("0.8")


def test_una_partida_ejecutada_sin_precio_del_corte_deja_la_separacion_no_disponible():
    sin_b = replace(
        PRECIOS,
        unitarios={k: v for k, v in PRECIOS.unitarios.items() if k != "OB-B"},
    )
    sep = separar_desvio(_estado(precios=sin_b))
    assert (sep.precio, sep.consumo) == (None, None)
    assert "OB-B" in sep.no_disponible["precio"]


def test_perspectiva_precio_el_consumo_es_cero_por_construccion():
    pu = {codigo: u * D("1.265") for codigo, u in ob.UNITARIOS_DEL_CORTE.items()}
    precios = replace(PRECIOS, unitarios=pu)
    instantanea = ob.instantanea(ob.v01_v02(), perspectiva=PERSPECTIVA_PRECIO)
    estado = construir_estado(instantanea, costo_real=None, precios=precios)
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert ind.ev == D(1200) * D("1.265")
    assert sep.consumo == 0
    assert sep.precio + sep.consumo == ind.cv


def test_los_precios_por_escalatoria_aplican_k_y_r_por_partida():
    unitarios = {"OB-A": D(10), "OB-B": D(5)}
    corte = precios_por_escalatoria(
        unitarios, {"OB-A": D("1.10"), "OB-B": D("1.00")}, D("0.10"), "S1"
    )
    assert corte.metodo == "escalatoria"
    assert corte.unitarios == {"OB-A": D(10) * (1 + D("0.10") * D("0.90")), "OB-B": D(5)}
    with pytest.raises(ValueError, match="falta el coeficiente K de las partidas OB-B"):
        precios_por_escalatoria(unitarios, {"OB-A": D(1)}, D(0), "S1")
    with pytest.raises(ValueError, match="R va en"):
        precios_por_escalatoria(unitarios, {"OB-A": D(1), "OB-B": D(1)}, D(1), "S1")


def test_un_estado_rechaza_perspectiva_y_dias_invalidos():
    base = _estado()
    with pytest.raises(ValueError, match="costo o precio"):
        replace(base, perspectiva="otra")
    with pytest.raises(ValueError, match="1 o mas"):
        replace(base, dias_por_periodo=0)
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_valor_ganado.py tests/unit/test_equilibrio_extraido.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.budget.control'`
```bash
git add tests/unit/test_valor_ganado.py tests/unit/test_equilibrio_extraido.py
git commit -m "test(core): valor ganado de OB-S2 y equilibrio extraido en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  `equilibrio.py`: se extrae el cálculo puro; `punto_equilibrio` lo llama con sus datos y devuelve lo mismo:
```diff
--- a/core/budget/equilibrio.py
+++ b/core/budget/equilibrio.py
@@ -16,14 +16,15 @@
 
 from __future__ import annotations
 
+from collections.abc import Sequence
 from dataclasses import dataclass
 from decimal import Decimal
 from enum import StrEnum
 
 from core.contracts.apu import ParametrosCosto
-from core.contracts.presupuesto import Presupuesto
+from core.contracts.presupuesto import Presupuesto, PuntoCurva
 
-__all__ = ["EstadoEquilibrio", "PuntoEquilibrio", "punto_equilibrio"]
+__all__ = ["EstadoEquilibrio", "PuntoEquilibrio", "equilibrio", "punto_equilibrio"]
 
 CERO = Decimal(0)
 CIEN = Decimal(100)
@@ -65,7 +66,15 @@
         (p.item.cantidad * p.resultado.costo_directo for p in presupuesto.partidas), CERO
     )
     costo_fijo = costo_variable * parametros.administracion
-    venta = presupuesto.total
+    return equilibrio(presupuesto.total, costo_variable, costo_fijo, presupuesto.curva)
+
+
+def equilibrio(
+    venta: Decimal, costo_variable: Decimal, costo_fijo: Decimal, curva: Sequence[PuntoCurva]
+) -> PuntoEquilibrio:
+    """El punto de equilibrio de unas ventas, un costo variable y un costo fijo dados, ubicado en
+    `curva` (SL-E5: se extrae de `punto_equilibrio` sin cambiar su resultado, para que el punto de
+    equilibrio proyectado de S2 use la misma definición con otros montos)."""
     utilidad = venta - costo_variable - costo_fijo
 
     def resultado(
@@ -107,7 +116,7 @@
             punto=punto,
             porcentaje=porcentaje,
         )
-    ubicacion = _ubicar(presupuesto, punto)
+    ubicacion = _ubicar(curva, punto)
     mensaje = (
         f"se alcanza en {ubicacion[0]}"
         if ubicacion[0] is not None
@@ -123,10 +132,10 @@
     )
 
 
-def _ubicar(presupuesto: Presupuesto, punto: Decimal) -> tuple[str | None, Decimal | None]:
+def _ubicar(curva: Sequence[PuntoCurva], punto: Decimal) -> tuple[str | None, Decimal | None]:
     """El primer período cuyo acumulado alcanza `punto` y la fracción de su monto en que ocurre."""
     anterior = CERO
-    for periodo in presupuesto.curva:
+    for periodo in curva:
         if periodo.acumulado >= punto:
             fraccion = (punto - anterior) / periodo.monto if periodo.monto else CERO
             return periodo.periodo, fraccion
```
  El valor ganado (funciones puras; `Decimal` con multiplicar antes de dividir; EV usa `qe = min(Q, q)`, S2-R8; umbrales y precios del corte como entradas, nunca valores quemados):
```python
# core/budget/valor_ganado.py
"""SL-E5: valor ganado, separación del desvío de control, reproyección y alertas (spec S2 §4).

Funciones **puras** con `Decimal` (sin base de datos ni `sqlalchemy`): reciben el `EstadoObra` al
corte y devuelven resultados tipados. Las divisiones van en un contexto local de 28 dígitos con
`ROUND_HALF_EVEN`, fijado dentro de cada función (S1 §5.3); se multiplica antes de dividir y se
redondea solo al presentar. Un número de días se redondea a 12 decimales antes de tomarle el techo
(S2-R9): un resto de 28 dígitos no debe adelantar un día.

Las fórmulas de PV, EV, AC, SV, CV, SPI, CPI y EAC = BAC/CPI son **definiciones del sistema**
(S2-R11): ninguna fuente que las contenga está verificada. El EAC del sistema y la separación del
desvío son propios de este trabajo y se declaran así. Los umbrales de las alertas son
SUPUESTO_DECLARADO (`ParametrosControl`).

**Separación del desvío de control** (S2 §4.3, RV-10): plazo = SV; precio = Σ qe·(u − u');
consumo = Σ qe·u' − AC; la identidad CV = precio + consumo es exacta. Es distinta de la «diferencia
entre versiones» de S3 (el término cruzado queda aquí en el consumo, allá en el precio).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_EVEN, Decimal, localcontext

from core.budget.curva import PeriodoPlan
from core.contracts.presupuesto import Presupuesto

__all__ = [
    "NATURALEZA_DECLARADA",
    "PERSPECTIVA_COSTO",
    "PERSPECTIVA_PRECIO",
    "EstadoObra",
    "Indicadores",
    "ParametrosControl",
    "PartidaControl",
    "PreciosDelCorte",
    "Separacion",
    "indicadores",
    "partidas_de_plan",
    "precios_por_escalatoria",
    "separar_desvio",
    "techo_de_dias",
]

PERSPECTIVA_COSTO = "costo"
PERSPECTIVA_PRECIO = "precio"
NATURALEZA_DECLARADA = "SUPUESTO_DECLARADO"
CERO = Decimal(0)
UNO = Decimal(1)
CIEN = Decimal(100)
PRECISION_DE_DIAS = Decimal("1e-12")


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


def techo_de_dias(dias: Decimal) -> int:
    """El techo de un número de días hábiles, tras redondearlo a 12 decimales (S2-R9)."""
    with _contexto():
        return int(dias.quantize(PRECISION_DE_DIAS).to_integral_value(rounding=ROUND_CEILING))


@dataclass(frozen=True, slots=True)
class ParametrosControl:
    """Umbrales de las alertas (§4.5) y supuestos de las opciones (§4.6). Los valores por defecto
    son SUPUESTO_DECLARADO sin fuente, editables por proyecto con su `RegistroCambio`;
    `penalizacion_diaria` es un dato del contrato (ninguna norma verificada la fija)."""

    spi_error: Decimal = Decimal("0.90")
    cpi_error: Decimal = Decimal("0.90")
    retraso_error: Decimal = Decimal("0.10")
    precio_info: Decimal = Decimal("0.05")
    equilibrio_puntos: Decimal = Decimal("10")
    eta_cuadrilla: Decimal = Decimal("0.80")
    cuadrillas_max: int = 3
    eta_horas_extra: Decimal = Decimal("0.80")
    horas_extra_dia: Decimal = Decimal("2")
    recargo_horas_extra: Decimal = Decimal("0.50")
    fcas_en_horas_extra: bool = True
    penalizacion_diaria: Decimal = CERO
    fuente_penalizacion: str = ""

    def __post_init__(self) -> None:
        for nombre in ("eta_cuadrilla", "eta_horas_extra"):
            if not CERO < getattr(self, nombre) <= UNO:
                raise ValueError(f"{nombre} debe estar en (0, 1]: {getattr(self, nombre)}")
        if self.cuadrillas_max < 2:
            raise ValueError(f"cuadrillas_max debe ser 2 o mas: {self.cuadrillas_max}")
        for nombre in (
            "spi_error",
            "cpi_error",
            "retraso_error",
            "precio_info",
            "equilibrio_puntos",
            "horas_extra_dia",
            "recargo_horas_extra",
            "penalizacion_diaria",
        ):
            if getattr(self, nombre) < CERO:
                raise ValueError(f"{nombre} no puede ser negativo: {getattr(self, nombre)}")


@dataclass(frozen=True, slots=True)
class PartidaControl:
    """Una partida de la línea base: cantidad `q`, unitario `u` según la perspectiva y la fracción
    del plan en cada período (`plan[n-1]` es la del período `n`)."""

    codigo: str
    cantidad: Decimal
    unitario: Decimal
    plan: tuple[Decimal, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan", tuple(self.plan))

    @property
    def periodos_activos(self) -> int:
        """`n_p`: períodos con fracción mayor que cero."""
        return sum(1 for fraccion in self.plan if fraccion > CERO)

    @property
    def inicio(self) -> int:
        """`inicio_p`: el primer período con fracción mayor que cero (0 si no tiene)."""
        return next((n for n, fraccion in enumerate(self.plan, start=1) if fraccion > CERO), 0)


@dataclass(frozen=True, slots=True)
class PreciosDelCorte:
    """Los unitarios `u'` al corte por partida, con el método y la fuente que los produjo (S1):
    `comprobacion` (PU de la versión revalorada por UC-02) o `escalatoria` (S1 §8.3)."""

    metodo: str
    fuente: str
    unitarios: Mapping[str, Decimal]


@dataclass(frozen=True, slots=True)
class EstadoObra:
    """Todo lo que los cálculos puros necesitan al corte.

    `dia` es el número de día hábil del corte; `ejecutado` es `Q_p` (acumulado de las valuaciones
    registradas y no anuladas con *hasta* menor o igual al corte) y `por_periodo`, esa misma
    cantidad por (partida, período del *hasta*). `costo_real` es el AC de la perspectiva *costo*
    ya convertido a la moneda del proyecto (`None` si algún costo no tiene tasa aplicable, con su
    `motivo_costo`). `etiquetas` son las del plan base; `dia_ultima_valuacion` es el día hábil de
    la última valuación (0 si no hay).
    """

    partidas: tuple[PartidaControl, ...]
    etiquetas: tuple[str, ...]
    dias_por_periodo: int
    dia: int
    ejecutado: Mapping[str, Decimal]
    por_periodo: Mapping[tuple[str, int], Decimal]
    perspectiva: str = PERSPECTIVA_COSTO
    costo_real: Decimal | None = None
    motivo_costo: str = ""
    precios: PreciosDelCorte | None = None
    dia_ultima_valuacion: int = 0

    def __post_init__(self) -> None:
        if self.perspectiva not in (PERSPECTIVA_COSTO, PERSPECTIVA_PRECIO):
            raise ValueError(f"perspectiva {self.perspectiva!r}: se espera costo o precio")
        if self.dias_por_periodo < 1:
            raise ValueError("los dias por periodo deben ser 1 o mas")
        object.__setattr__(self, "partidas", tuple(self.partidas))
        object.__setattr__(self, "etiquetas", tuple(self.etiquetas))

    @property
    def periodos(self) -> int:
        """`N`: períodos del plan base."""
        return len(self.etiquetas)

    @property
    def dias_plan(self) -> int:
        """`D = N · L`: días hábiles del plan base."""
        return self.periodos * self.dias_por_periodo

    def cantidad_ejecutada(self, partida: PartidaControl) -> Decimal:
        """`qe_p = min(Q_p, q_p)` (S2-R8): la obra no presupuestada no gana valor."""
        return min(self.ejecutado.get(partida.codigo, CERO), partida.cantidad)

    def fraccion_planificada(self, partida: PartidaControl) -> Decimal:
        """`F_p(t)`: las fracciones de los períodos terminados más la parte proporcional, por días
        hábiles, del período que contiene al corte."""
        completos, transcurridos = divmod(self.dia, self.dias_por_periodo)
        hasta = min(completos, len(partida.plan))
        total = sum(partida.plan[:hasta], CERO)
        if transcurridos and completos < len(partida.plan):
            with _contexto():
                total += partida.plan[completos] * transcurridos / self.dias_por_periodo
        return min(total, UNO)


def partidas_de_plan(
    presupuesto: Presupuesto, plan: Sequence[PeriodoPlan], perspectiva: str
) -> tuple[PartidaControl, ...]:
    """Las partidas del presupuesto con su plan por período. Varios renglones del mismo código se
    suman (la cantidad) y comparten el unitario del primero, como `generar_curva`."""
    if perspectiva not in (PERSPECTIVA_COSTO, PERSPECTIVA_PRECIO):
        raise ValueError(f"perspectiva {perspectiva!r}: se espera costo o precio")
    cantidades: dict[str, Decimal] = defaultdict(lambda: CERO)
    unitarios: dict[str, Decimal] = {}
    for partida in presupuesto.partidas:
        codigo = partida.item.codigo_partida
        cantidades[codigo] += partida.item.cantidad
        unitarios.setdefault(
            codigo,
            partida.resultado.costo_directo
            if perspectiva == PERSPECTIVA_COSTO
            else partida.resultado.precio_unitario,
        )
    fracciones: dict[str, list[Decimal]] = {codigo: [CERO] * len(plan) for codigo in cantidades}
    for n, (_, reparto) in enumerate(plan):
        for codigo, fraccion in reparto:
            if codigo in fracciones:
                fracciones[codigo][n] += fraccion
    return tuple(
        PartidaControl(codigo, cantidades[codigo], unitarios[codigo], tuple(fracciones[codigo]))
        for codigo in cantidades
    )


def precios_por_escalatoria(
    unitarios: Mapping[str, Decimal],
    coeficientes: Mapping[str, Decimal],
    r: Decimal,
    fuente: str,
) -> PreciosDelCorte:
    """`u' = u · (1 + (K - 1)(1 - R))` por partida (S2 §4.3, S1 §8.3; INDICIO declarado en S1).
    `ValueError` si falta el coeficiente de alguna partida: no se supone `K = 1`."""
    faltan = sorted(set(unitarios) - set(coeficientes))
    if faltan:
        raise ValueError(f"falta el coeficiente K de las partidas {', '.join(faltan)}")
    if not CERO <= r < UNO:
        raise ValueError(f"R va en [0, 1): {r}")
    with _contexto():
        corte = {
            codigo: u * (UNO + (coeficientes[codigo] - UNO) * (UNO - r))
            for codigo, u in unitarios.items()
        }
    return PreciosDelCorte("escalatoria", fuente, corte)


# ---------------------------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Indicadores:
    """PV, EV, AC y sus índices al corte (§4.2). Un indicador que no se puede calcular es `None` y
    su motivo está en `no_disponible` (UC-20 1a-1d)."""

    bac: Decimal
    pv: Decimal
    ev: Decimal
    ac: Decimal | None
    sv: Decimal
    cv: Decimal | None
    spi: Decimal | None
    cpi: Decimal | None
    cpi_corte: Decimal | None
    eac_indice: Decimal | None
    eac_sistema: Decimal | None
    vac: Decimal | None
    termino_indice: int | None
    no_disponible: Mapping[str, str]


def _unitario_de_corte(estado: EstadoObra, codigo: str) -> Decimal | None:
    if estado.precios is None:
        return None
    return estado.precios.unitarios.get(codigo)


def _ac(estado: EstadoObra, motivos: dict[str, str]) -> Decimal | None:
    """AC de la perspectiva: el costo real declarado (*costo*) o `Σ qe·u'` (*precio*)."""
    if estado.perspectiva == PERSPECTIVA_COSTO:
        if estado.costo_real is None:
            motivos["AC"] = estado.motivo_costo or "sin costos reales declarados"
        return estado.costo_real
    total = CERO
    for partida in estado.partidas:
        qe = estado.cantidad_ejecutada(partida)
        if qe == CERO:
            continue
        precio = _unitario_de_corte(estado, partida.codigo)
        if precio is None:
            motivos["AC"] = f"sin precio del corte para la partida {partida.codigo}"
            return None
        total += qe * precio
    return total


def indicadores(estado: EstadoObra) -> Indicadores:
    """Los indicadores de valor ganado al corte (§4.2), en la moneda del proyecto."""
    motivos: dict[str, str] = {}
    with _contexto():
        bac = sum((p.cantidad * p.unitario for p in estado.partidas), CERO)
        pv = sum(
            (p.cantidad * p.unitario * estado.fraccion_planificada(p) for p in estado.partidas),
            CERO,
        )
        ev = sum(
            (estado.cantidad_ejecutada(p) * p.unitario for p in estado.partidas),
            CERO,
        )
        ac = _ac(estado, motivos)
        spi = ev / pv if pv > CERO else None
        if spi is None:
            motivos["SPI"] = "PV = 0: el corte es anterior a todo trabajo planificado"
        cpi = ev / ac if ac is not None and ac > CERO else None
        if ac == CERO:
            motivos["CPI"] = "AC = 0: aun no hay costos reales"
        cv = None if ac is None else ev - ac
        eac_indice = bac / cpi if cpi else None
        cpi_corte, eac_sistema = _eac_del_sistema(estado, ac, motivos)
        vac = None if eac_sistema is None else bac - eac_sistema
        termino = None
        if spi:
            termino = techo_de_dias(Decimal(estado.dias_plan) * pv / ev)
    for nombre in ("CV", "CPI", "EAC", "VAC"):
        if ac is None:
            motivos.setdefault(nombre, motivos.get("AC", "AC no disponible"))
    return Indicadores(
        bac=bac,
        pv=pv,
        ev=ev,
        ac=ac,
        sv=ev - pv,
        cv=cv,
        spi=spi,
        cpi=cpi,
        cpi_corte=cpi_corte,
        eac_indice=eac_indice,
        eac_sistema=eac_sistema,
        vac=vac,
        termino_indice=termino,
        no_disponible=dict(motivos),
    )


def _eac_del_sistema(
    estado: EstadoObra, ac: Decimal | None, motivos: dict[str, str]
) -> tuple[Decimal | None, Decimal | None]:
    """`CPIc = Σ qe·u' / AC` y `EAC = AC + Σ (q - qe)·u' / CPIc` (§4.2, propio de este trabajo)."""
    if ac is None or estado.precios is None:
        if ac is not None:
            motivos["EAC"] = "sin precios del corte"
        return None, None
    ejecutado_a_corte = CERO
    pendiente_a_corte = CERO
    for partida in estado.partidas:
        precio = _unitario_de_corte(estado, partida.codigo)
        if precio is None:
            motivos["EAC"] = f"sin precio del corte para la partida {partida.codigo}"
            return None, None
        qe = estado.cantidad_ejecutada(partida)
        ejecutado_a_corte += qe * precio
        pendiente_a_corte += (partida.cantidad - qe) * precio
    if ac == CERO or ejecutado_a_corte == CERO:
        motivos["EAC"] = "sin avance o sin costos reales: el rendimiento del consumo no existe"
        return None, None
    cpi_corte = ejecutado_a_corte / ac
    return cpi_corte, ac + pendiente_a_corte * ac / ejecutado_a_corte


# ---------------------------------------------------------------------------------------------
# Separación del desvío de control
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Separacion:
    """`CV = precio + consumo` (exacta) y, al término, `VAC = vac_precio + vac_consumo`.

    `plazo` es SV (cantidad y tiempo a precios de la línea base). Sin precios del corte, o sin AC,
    los componentes que dependen de ellos son `None` y `no_disponible` dice por qué (§4.3)."""

    plazo: Decimal
    precio: Decimal | None
    consumo: Decimal | None
    vac_precio: Decimal | None
    vac_consumo: Decimal | None
    metodo: str
    fuente: str
    no_disponible: Mapping[str, str]


def separar_desvio(estado: EstadoObra, calculados: Indicadores | None = None) -> Separacion:
    """Separa el desvío de control en plazo, precio y consumo (§4.3, S2-R1)."""
    ind = calculados or indicadores(estado)
    motivos: dict[str, str] = {}
    metodo = "" if estado.precios is None else estado.precios.metodo
    fuente = "" if estado.precios is None else estado.precios.fuente
    precio = consumo = vac_precio = vac_consumo = None
    sin_precio = sorted(
        p.codigo for p in estado.partidas if _unitario_de_corte(estado, p.codigo) is None
    )
    ejecutadas_sin_precio = [
        p.codigo
        for p in estado.partidas
        if p.codigo in sin_precio and estado.cantidad_ejecutada(p) > CERO
    ]
    with _contexto():
        if ejecutadas_sin_precio or estado.precios is None:
            motivos["precio"] = _motivo_sin_precios(estado, ejecutadas_sin_precio)
        else:
            precio = sum(
                (
                    estado.cantidad_ejecutada(p) * (p.unitario - estado.precios.unitarios[p.codigo])
                    for p in estado.partidas
                    if estado.cantidad_ejecutada(p) > CERO
                ),
                CERO,
            )
            if ind.ac is None:
                motivos["consumo"] = ind.no_disponible.get("AC", "AC no disponible")
            else:
                a_corte = sum(
                    (
                        estado.cantidad_ejecutada(p) * estado.precios.unitarios[p.codigo]
                        for p in estado.partidas
                        if estado.cantidad_ejecutada(p) > CERO
                    ),
                    CERO,
                )
                consumo = a_corte - ind.ac
        if sin_precio or estado.precios is None:
            motivos["vac_precio"] = _motivo_sin_precios(estado, sin_precio)
        else:
            vac_precio = -sum(
                (
                    p.cantidad * (estado.precios.unitarios[p.codigo] - p.unitario)
                    for p in estado.partidas
                ),
                CERO,
            )
            if ind.vac is not None:
                vac_consumo = ind.vac - vac_precio
            else:
                motivos["vac_consumo"] = ind.no_disponible.get("EAC", "EAC no disponible")
    return Separacion(ind.sv, precio, consumo, vac_precio, vac_consumo, metodo, fuente, motivos)


def _motivo_sin_precios(estado: EstadoObra, partidas: Sequence[str]) -> str:
    if estado.precios is None:
        return "sin precios del corte (S1): la separacion no esta disponible"
    return "sin precio del corte para " + ", ".join(partidas)


# ---------------------------------------------------------------------------------------------
# Reproyección al ritmo real
# ---------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------
# Punto de equilibrio proyectado y alertas
# ---------------------------------------------------------------------------------------------
```
  La orquestación: de la instantánea de la base al `EstadoObra` y los indicadores (el costo real convertido con `tasa_aplicable(fecha)` de cada costo, S2-R17):
```python
# core/budget/control.py
"""SL-E5: el control de la obra al corte, de la base de datos al resultado (spec S2 §4, §5.3).

`calcular_control` lee la instantánea de control (`core.budget.valuaciones`), convierte los costos
reales con la tasa de su fecha (S1), toma los precios del corte y el reajuste ya reconocido y
llama a las funciones puras de `core.budget.valor_ganado`. **Nada derivado se guarda**: los
indicadores, las alertas, los hallazgos de R13-R14 y la reproyección se recalculan cada vez, sin
reescribir filas (S2-R13, RV-9). Los parámetros de control sí se guardan, con su `RegistroCambio`.

Un costo real sin tasa aplicable (más de 7 días sin tasa, S1-R2) deja el AC «no disponible» con la
lista de esos costos; PV, EV, SPI, el precio y el término se calculan igual (S2-R17, REQ-25).
"""

from __future__ import annotations

from decimal import Decimal

from core.budget.calendario import numero_de_dia, periodo_de
from core.budget.valor_ganado import (
    EstadoObra,
    PreciosDelCorte,
    partidas_de_plan,
)
from core.budget.valuaciones import InstantaneaControl

__all__ = [
    "construir_estado",
]

CERO = Decimal(0)


def construir_estado(
    instantanea: InstantaneaControl,
    *,
    costo_real: Decimal | None,
    motivo_costo: str = "",
    precios: PreciosDelCorte | None = None,
) -> EstadoObra:
    """El `EstadoObra` puro al corte: partidas con su plan, el día hábil del corte y lo ejecutado
    por partida y por período del *hasta* (valuaciones con *hasta* menor o igual al corte)."""
    calendario = instantanea.calendario
    feriados = frozenset(calendario.feriados)
    largo = calendario.dias_por_periodo
    ejecutado: dict[str, Decimal] = {}
    por_periodo: dict[tuple[str, int], Decimal] = {}
    ultima = 0
    for valuacion in instantanea.para_el_valor_ganado():
        # Una valuacion que termina antes del primer dia habil cae en el periodo 1.
        periodo = max(1, periodo_de(calendario.fecha_inicio, largo, valuacion.hasta, feriados))
        ultima = max(ultima, numero_de_dia(calendario.fecha_inicio, valuacion.hasta, feriados))
        for linea in valuacion.lineas:
            ejecutado[linea.codigo_partida] = (
                ejecutado.get(linea.codigo_partida, CERO) + linea.cantidad
            )
            clave = (linea.codigo_partida, periodo)
            por_periodo[clave] = por_periodo.get(clave, CERO) + linea.cantidad
    return EstadoObra(
        partidas=partidas_de_plan(
            instantanea.presupuesto, instantanea.plan, instantanea.linea_base.perspectiva
        ),
        etiquetas=tuple(etiqueta for etiqueta, _ in instantanea.plan),
        dias_por_periodo=largo,
        dia=numero_de_dia(calendario.fecha_inicio, instantanea.corte, feriados),
        ejecutado=ejecutado,
        por_periodo=por_periodo,
        perspectiva=instantanea.linea_base.perspectiva,
        costo_real=costo_real,
        motivo_costo=motivo_costo,
        precios=precios,
        dia_ultima_valuacion=ultima,
    )


# ---------------------------------------------------------------------------------------------
# Parámetros de control (S2 §4.5, §4.6)
# ---------------------------------------------------------------------------------------------
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_valor_ganado.py tests/unit/test_equilibrio_extraido.py -v -W error` → 15 pruebas en verde.
Run: `uv run pytest tests/unit/test_caso_ti001.py tests/unit/test_equilibrio.py tests/unit/test_budget.py -q -W error` → verde **sin editar esas pruebas**: TI-001 sigue en 28 586,76 USD, Día 6.
Run: `uv run ruff check core/budget/equilibrio.py core/budget/valor_ganado.py core/budget/control.py tests/unit/test_valor_ganado.py tests/unit/test_equilibrio_extraido.py` y la guardia del núcleo.
- [ ] **Paso 5: Commit**
```bash
git add core/budget/equilibrio.py core/budget/valor_ganado.py core/budget/control.py
git commit -m "feat(core): valor ganado, separacion del desvio y equilibrio extraido" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 8: SL-E5b — reproyección, alertas y punto de equilibrio proyectado

**Rama:** `inc/070-s2-2-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `tests/unit/test_reproyeccion.py`, `tests/unit/test_alertas.py`, `tests/unit/test_pe_proyectado.py`
- Modificar: `core/budget/valor_ganado.py` (agrega la reproyección, las alertas y `equilibrio_proyectado`; ver el parche del paso 3)

**Interfaces:**
- Consume: de la tarea 7: `ParametrosControl`, `PartidaControl`, `EstadoObra`, `Indicadores`, `indicadores`, `separar_desvio`, `techo_de_dias`, `core.budget.equilibrio.equilibrio`, `core.budget.curva.PeriodoPlan`.
- Produce:
- `core/budget/valor_ganado.py`:
  - `LIMITE_DE_PERIODOS = 10000`
  - `class ProyeccionPartida [codigo: str; indice: Decimal | None; ritmo: Decimal | None; pendiente: Decimal; fin: Decimal | None; detenida: bool; sin_evidencia: bool; motivo: str]`
  - `class Reproyeccion [plan: tuple[PeriodoPlan, ...]; partidas: tuple[ProyeccionPartida, ...]; termino: int | None; motivo_termino: str]`
  - `def reproyectar(estado: EstadoObra, *, multiplicador: Mapping[str, Decimal] | None=None, adelantar: Collection[str]=()) -> Reproyeccion`
  - `def proyectar_partida(estado: EstadoObra, codigo: str, *, multiplicador: Decimal=UNO, adelantada: bool=False, spi_global: Decimal | None=None) -> ProyeccionPartida`
  - `def fin_excede(fin: Decimal, objetivo: int) -> bool`
  - `def equilibrio_proyectado(*, venta: Decimal, costo_variable: Decimal, costo_fijo: Decimal, dias_plan: int, dias_proyectados: int, reajuste_reconocido: Decimal, curva: Sequence[PuntoCurva]) -> PuntoEquilibrio`
  - `class Alerta [codigo: str; severidad: Severidad; descripcion: str; valor_observado: Decimal | None; umbral: Decimal | None; naturaleza_umbral: str]`
  - `class Alertas [alertas: tuple[Alerta, ...]; no_evaluadas: Mapping[str, str]]`
  - `def alertas(ind: Indicadores, sep: Separacion, reproyeccion: Reproyeccion, *, dias_plan: int, equilibrio_base: PuntoEquilibrio | None, equilibrio_proyectado: PuntoEquilibrio | None, parametros: ParametrosControl) -> Alertas`

- [ ] **Paso 0: Expediente SL-E5** (ver tarea 7, paso 0).
- [ ] **Paso 1: Escribir las pruebas que fallan**
  La reproyección por partida (índice `s = EV_p/PV_p` o SPI global, ritmo `r = s/n·mult`, período en curso parcial; plan válido para la curva y cerrado en el total; término 2026-12-02 = día 23 en OB-S2):
```python
# tests/unit/test_reproyeccion.py
"""SL-E5: reproyección al ritmo real (spec S2 §4.4; RF-77).

El plan reproyectado, los fines por partida y el término de OB-S2 salen de la memoria
`control_ob_s2.md` (§7.1). Casos de frontera: partida detenida (AL-6), SPI global 0, corte a mitad
de período, obra terminada, partida sin plan y plan que cierra exacto en el total.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from core.budget.control import construir_estado
from core.budget.curva import generar_curva
from core.budget.valor_ganado import reproyectar
from tests.fixtures import control_ob_s2 as ob

D = Decimal
PLAN_REPROYECTADO = [
    ("Semana 1", [("OB-A", D("0.4"))]),
    ("Semana 2", [("OB-A", D("0.5")), ("OB-B", D("0.3"))]),
    ("Semana 3", [("OB-A", D("0.1")), ("OB-B", D("0.3")), ("OB-C", D("0.4"))]),
    ("Semana 4", [("OB-B", D("0.3")), ("OB-C", D("0.4"))]),
    ("Semana 5", [("OB-B", D("0.1")), ("OB-C", D("0.2"))]),
]


def _estado(valuaciones=None, *, corte=ob.CORTE):
    instantanea = ob.instantanea(ob.v01_v02() if valuaciones is None else valuaciones, corte=corte)
    return construir_estado(instantanea, costo_real=ob.COSTO_REAL, precios=ob.precios_del_corte())


def _plan(reproyeccion):
    return [(etiqueta, list(reparto)) for etiqueta, reparto in reproyeccion.plan]


def test_el_plan_reproyectado_de_la_memoria():
    reproyeccion = reproyectar(_estado())
    assert _plan(reproyeccion) == PLAN_REPROYECTADO
    assert reproyeccion.termino == 23  # dia habil 23 = 2026-12-02
    assert reproyeccion.motivo_termino == ""


def test_los_fines_ritmos_e_indices_por_partida():
    reproyeccion = reproyectar(_estado())
    a, b, c = (reproyeccion.de(codigo) for codigo in ("OB-A", "OB-B", "OB-C"))
    assert [p.indice for p in (a, b, c)] == [D("0.9"), D("0.6"), D("0.8")]
    assert [p.ritmo for p in (a, b, c)] == [D("0.45"), D("0.3"), D("0.4")]
    assert [round(p.fin, 2) for p in (a, b, c)] == [D("11.11"), D("21.67"), D("22.50")]
    assert (a.sin_evidencia, b.sin_evidencia, c.sin_evidencia) == (False, False, True)
    assert reproyeccion.detenidas == () and reproyeccion.no_proyectables == ()


def test_el_plan_reproyectado_es_valido_para_la_curva_y_cierra_en_el_total():
    estado = _estado()
    reproyeccion = reproyectar(estado)
    presupuesto = ob.elaborar_ob_s2().presupuesto
    curva = generar_curva(presupuesto, reproyeccion.plan)
    assert curva[-1].acumulado == presupuesto.total
    sumas = {}
    for _, reparto in reproyeccion.plan:
        for codigo, fraccion in reparto:
            sumas[codigo] = sumas.get(codigo, D(0)) + fraccion
    assert sumas == {"OB-A": 1, "OB-B": 1, "OB-C": 1}  # exacto, no a +- epsilon


def test_una_partida_detenida_se_reproyecta_al_ritmo_global_y_se_marca():
    """A tiene PV > 0 y EV = 0 (AL-6) y sigue al SPI global: EV 300 / PV 1500 = 0,2, o sea 0,2 / 2
    periodos = 0,1 por periodo; con 1 por ejecutar termina en el dia habil 60."""
    solo_b = ob.valuacion({**ob.V02, "lineas": ob.V02["lineas"][1:]}, 2)  # solo B 60
    reproyeccion = reproyectar(_estado([solo_b]))
    assert reproyeccion.detenidas == ("OB-A",)
    detenida = reproyeccion.de("OB-A")
    assert (detenida.detenida, detenida.indice, detenida.ritmo) == (True, D("0.2"), D("0.1"))
    assert detenida.fin == D(60) and reproyeccion.termino == 60


def test_un_spi_global_cero_hace_el_termino_no_proyectable():
    estado = _estado([], corte=date(2026, 11, 13))  # PV > 0 y nada ejecutado: SPI = 0
    reproyeccion = reproyectar(estado)
    assert reproyeccion.termino is None
    assert "no proyectable" in reproyeccion.motivo_termino
    assert set(reproyeccion.no_proyectables) == {"OB-A", "OB-B", "OB-C"}
    assert reproyeccion.de("OB-A").motivo.startswith("el SPI global es 0")


def test_antes_de_empezar_sin_spi_cada_partida_va_a_su_ritmo_planificado():
    estado = _estado([], corte=date(2026, 11, 1))  # PV = 0: el SPI no aplica, indice 1
    reproyeccion = reproyectar(estado)
    assert reproyeccion.termino == 20  # el plan base, intacto
    assert _plan(reproyeccion) == [
        ("Semana 1", [("OB-A", D("0.5"))]),
        ("Semana 2", [("OB-A", D("0.5")), ("OB-B", D("0.5"))]),
        ("Semana 3", [("OB-B", D("0.5")), ("OB-C", D("0.5"))]),
        ("Semana 4", [("OB-C", D("0.5"))]),
    ]


def test_corte_a_mitad_de_periodo_el_periodo_en_curso_aporta_solo_lo_que_le_queda():
    """Dia 8 (3 de 5 dias de la semana 2): lo pendiente arranca en la semana 2 con 2/5 de ritmo."""
    valuacion = ob.valuacion({**ob.V01, "lineas": ob.V01["lineas"]}, 1)
    estado = _estado([valuacion], corte=date(2026, 11, 11))
    assert estado.dia == 8
    reproyeccion = reproyectar(estado)
    a = reproyeccion.de("OB-A")
    # A: planificado 0,8, ejecutado 0,4 -> s = 0,5; ritmo 0,25; la semana 2 aporta 0,25 x 2/5.
    assert a.indice == D("0.5") and a.ritmo == D("0.25")
    semana_2 = dict(reproyeccion.plan[1][1])
    assert semana_2["OB-A"] == D("0.25") * D(2) / D(5)
    assert round(a.fin, 4) > D(8)  # termina despues del corte


def test_la_obra_terminada_termina_en_la_fecha_de_la_ultima_valuacion():
    completa = [
        ob.valuacion(
            dict(
                numero="V-01", desde=ob.INICIO, hasta=date(2026, 11, 27), fecha=date(2026, 11, 30),
                inspector=ob.INSPECTOR,
                lineas=[
                    ob.LineaValuacion("OB-A", D(100)),
                    ob.LineaValuacion("OB-B", D(200)),
                    ob.LineaValuacion("OB-C", D(100)),
                ],
            ),
            1,
        )
    ]  # fmt: skip
    reproyeccion = reproyectar(_estado(completa, corte=date(2026, 11, 27)))
    assert reproyeccion.termino == 20
    assert "nada queda pendiente" in reproyeccion.motivo_termino
    assert all(p.fin is None and p.pendiente == 0 for p in reproyeccion.partidas)


def test_adelantar_lleva_una_partida_sin_empezar_al_periodo_siguiente_al_corte():
    estado = _estado()
    adelantada = reproyectar(estado, adelantar=["OB-C"])
    # C ya empieza en la semana 3 (= c + 1): adelantar no cambia nada en OB-S2.
    assert _plan(adelantada) == PLAN_REPROYECTADO
    atrasada = replace(
        estado,
        partidas=tuple(
            replace(p, plan=(D(0), D(0), D(0), D(0), D("0.5"), D("0.5")))
            if p.codigo == "OB-C"
            else p
            for p in estado.partidas
        ),
        etiquetas=(*estado.etiquetas, "Semana 5", "Semana 6"),
    )
    assert _plan(reproyectar(atrasada))[2][1] == [("OB-A", D("0.1")), ("OB-B", D("0.3"))]
    assert dict(_plan(reproyectar(atrasada, adelantar=["OB-C"]))[2][1])["OB-C"] == D("0.4")


def test_las_etiquetas_del_plan_continuan_la_numeracion_y_si_no_hay_numero_usan_periodo():
    estado = _estado()
    assert reproyectar(estado).plan[4][0] == "Semana 5"
    sin_numero = replace(estado, etiquetas=("Inicio", "Medio", "Fin", "Cierre"))
    assert reproyectar(sin_numero).plan[4][0] == "Periodo 5"


def test_un_multiplicador_acelera_solo_esa_partida():
    estado = _estado()
    rapido = reproyectar(estado, multiplicador={"OB-B": D("1.8"), "OB-C": D("1.8")})
    assert rapido.termino == 17
    assert rapido.de("OB-A").fin == reproyectar(estado).de("OB-A").fin
    assert dict(rapido.plan[2][1]) == {"OB-A": D("0.1"), "OB-B": D("0.54"), "OB-C": D("0.72")}
```
  Las alertas AL-1 a AL-6 con umbrales SUPUESTO_DECLARADO y editables por proyecto, y sus fronteras:
```python
# tests/unit/test_alertas.py
"""SL-E5: alertas AL-1 a AL-6 con umbrales declarados (spec S2 §4.5; RF-77).

Las cinco alertas de OB-S2 (iguales con y sin el reajuste reconocido) y cada frontera de §7.3:
SPI y CPI en 1,0000 / 0,9999 / 0,9000 / 0,8999, retraso de 2 días (10 %) y de 3, `|ΔP|` de 5 %
exacto y de 4,99 %, y el punto de equilibrio que sube 10,00 y 10,01 puntos. Un indicador no
disponible no se evalúa y la pantalla lo dice.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from core.budget.control import construir_estado
from core.budget.equilibrio import EstadoEquilibrio, PuntoEquilibrio
from core.budget.valor_ganado import (
    ParametrosControl,
    alertas,
    indicadores,
    reproyectar,
    separar_desvio,
)
from core.contracts.verificacion import Severidad
from tests.fixtures import control_ob_s2 as ob

D = Decimal
PARAMETROS = ParametrosControl()


def _insumos(costo_real=ob.COSTO_REAL):
    estado = construir_estado(
        ob.instantanea(ob.v01_v02()), costo_real=costo_real, precios=ob.precios_del_corte()
    )
    ind = indicadores(estado)
    return estado, ind, separar_desvio(estado, ind), reproyectar(estado)


def _pe(porcentaje: str, estado=EstadoEquilibrio.CALCULADO) -> PuntoEquilibrio:
    return PuntoEquilibrio(
        estado, D(5060), D(4000), D(600), D(460), D("0.2095"), D(100), D(porcentaje),
        "Semana 4", D("0.5"), "se alcanza",
    )  # fmt: skip


def _alertas(*, ind=None, sep=None, rep=None, base="56.60", proyectado="56.60", **parametros):
    estado, i, s, r = _insumos()
    return alertas(
        ind or i,
        sep or s,
        rep or r,
        dias_plan=20,
        equilibrio_base=_pe(base),
        equilibrio_proyectado=None if proyectado is None else _pe(proyectado),
        parametros=replace(PARAMETROS, **parametros),
    )


def _por_codigo(resultado):
    return {a.codigo: a for a in resultado.alertas}


def test_las_alertas_de_ob_s2_sin_el_equilibrio_proyectado_alcanzable():
    estado, ind, sep, rep = _insumos()
    resultado = alertas(
        ind, sep, rep, dias_plan=20, equilibrio_base=_pe("56.60"),
        equilibrio_proyectado=_pe("119.00", EstadoEquilibrio.NO_SE_ALCANZA), parametros=PARAMETROS,
    )  # fmt: skip
    por_codigo = _por_codigo(resultado)
    assert {c: a.severidad for c, a in por_codigo.items()} == {
        "AL-1": Severidad.ERROR,
        "AL-2": Severidad.ADVERTENCIA,
        "AL-3": Severidad.ERROR,
        "AL-4": Severidad.ERROR,
        "AL-5": Severidad.INFO,
    }
    assert por_codigo["AL-1"].valor_observado == D("0.8") and por_codigo["AL-1"].umbral == D("0.9")
    assert por_codigo["AL-3"].valor_observado == 3 and por_codigo["AL-3"].umbral == D(2)
    assert "LCP art. 133, a cotejar" in por_codigo["AL-5"].descripcion
    assert all(a.naturaleza_umbral == "SUPUESTO_DECLARADO" for a in resultado.alertas)
    assert resultado.no_evaluadas == {}


@pytest.mark.parametrize(
    ("spi", "severidad"),
    [
        ("1.0000", None),
        ("1.2000", None),
        ("0.9999", Severidad.ADVERTENCIA),
        ("0.9000", Severidad.ADVERTENCIA),
        ("0.8999", Severidad.ERROR),
    ],
)
def test_fronteras_del_spi_y_del_cpi(spi, severidad):
    _, ind, _, _ = _insumos()
    en_spi = _por_codigo(_alertas(ind=replace(ind, spi=D(spi), cpi=D(1)))).get("AL-1")
    en_cpi = _por_codigo(_alertas(ind=replace(ind, cpi=D(spi), spi=D(1)))).get("AL-2")
    assert (None if en_spi is None else en_spi.severidad) == severidad
    assert (None if en_cpi is None else en_cpi.severidad) == severidad


@pytest.mark.parametrize(
    ("termino", "severidad"),
    [(20, None), (19, None), (22, Severidad.ADVERTENCIA), (23, Severidad.ERROR)],
    ids=["en plazo", "antes", "2 dias = 10 % advierte", "3 dias = 15 % es error"],
)
def test_fronteras_del_retraso_del_termino(termino, severidad):
    _, _, _, rep = _insumos()
    alerta = _por_codigo(_alertas(rep=replace(rep, termino=termino))).get("AL-3")
    assert (None if alerta is None else alerta.severidad) == severidad


@pytest.mark.parametrize(
    ("precio", "salta"),
    [(D("-60.00"), True), (D("-59.88"), False), (D("60.00"), True), (D("-59.99"), False)],
    ids=["5 % exacto", "4,99 %", "5 % favorable", "casi 5 %"],
)
def test_fronteras_de_la_desviacion_de_precio(precio, salta):
    _, _, sep, _ = _insumos()
    alerta = _por_codigo(_alertas(sep=replace(sep, precio=precio, consumo=D(0)))).get("AL-5")
    assert (alerta is not None) is salta
    assert alerta is None or alerta.severidad is Severidad.INFO


@pytest.mark.parametrize(
    ("proyectado", "severidad"),
    [("66.60", None), ("66.61", Severidad.ADVERTENCIA), ("50.00", None)],
    ids=["sube 10,00 puntos: sin alerta", "sube 10,01: advierte", "baja: sin alerta"],
)
def test_fronteras_del_equilibrio_proyectado(proyectado, severidad):
    alerta = _por_codigo(_alertas(proyectado=proyectado)).get("AL-4")
    assert (None if alerta is None else alerta.severidad) == severidad


def test_un_equilibrio_que_no_existe_o_no_se_alcanza_es_error():
    for estado in (EstadoEquilibrio.NO_EXISTE, EstadoEquilibrio.NO_SE_ALCANZA):
        _, ind, sep, rep = _insumos()
        resultado = alertas(
            ind, sep, rep, dias_plan=20, equilibrio_base=_pe("56.60"),
            equilibrio_proyectado=_pe("200", estado), parametros=PARAMETROS,
        )  # fmt: skip
        assert _por_codigo(resultado)["AL-4"].severidad is Severidad.ERROR


def test_una_partida_detenida_da_su_advertencia_al_6():
    solo_b = ob.valuacion({**ob.V02, "lineas": ob.V02["lineas"][1:]}, 2)
    estado = construir_estado(
        ob.instantanea([solo_b]), costo_real=ob.COSTO_REAL, precios=ob.precios_del_corte()
    )
    ind = indicadores(estado)
    resultado = alertas(
        ind, separar_desvio(estado, ind), reproyectar(estado), dias_plan=20,
        equilibrio_base=_pe("56.60"), equilibrio_proyectado=_pe("56.60"), parametros=PARAMETROS,
    )  # fmt: skip
    detenida = [a for a in resultado.alertas if a.codigo == "AL-6"]
    assert len(detenida) == 1 and detenida[0].severidad is Severidad.ADVERTENCIA
    assert "OB-A" in detenida[0].descripcion


def test_lo_que_no_esta_disponible_no_se_evalua_y_se_declara():
    estado = construir_estado(
        ob.instantanea(ob.v01_v02()), costo_real=None, precios=ob.precios_del_corte()
    )
    ind = replace(indicadores(estado), spi=None)
    estado_sin_precios = construir_estado(ob.instantanea(ob.v01_v02()), costo_real=D(1280))
    sep = separar_desvio(estado_sin_precios)
    resultado = alertas(
        ind, sep, reproyectar(estado), dias_plan=20, equilibrio_base=None,
        equilibrio_proyectado=None, parametros=PARAMETROS,
    )  # fmt: skip
    assert set(resultado.no_evaluadas) == {"AL-1", "AL-2", "AL-4", "AL-5"}
    assert "AL-3" not in resultado.no_evaluadas  # el termino por plan si se calcula
    assert resultado.no_evaluadas["AL-1"] == "SPI no aplica"


def test_un_termino_no_proyectable_no_evalua_al_3():
    _, _, _, rep = _insumos()
    resultado = _alertas(rep=replace(rep, termino=None, motivo_termino="no proyectable: OB-A"))
    assert resultado.no_evaluadas == {"AL-3": "no proyectable: OB-A"}


def test_los_umbrales_son_editables_por_proyecto():
    _, ind, _, _ = _insumos()
    resultado = _alertas(ind=replace(ind, spi=D("0.85"), cpi=D(1)), spi_error=D("0.80"))
    assert _por_codigo(resultado)["AL-1"].severidad is Severidad.ADVERTENCIA


def test_los_parametros_de_control_validan_sus_rangos():
    with pytest.raises(ValueError, match="eta_cuadrilla"):
        ParametrosControl(eta_cuadrilla=D(0))
    with pytest.raises(ValueError, match="eta_horas_extra"):
        ParametrosControl(eta_horas_extra=D("1.1"))
    with pytest.raises(ValueError, match="cuadrillas_max"):
        ParametrosControl(cuadrillas_max=1)
    with pytest.raises(ValueError, match="penalizacion_diaria"):
        ParametrosControl(penalizacion_diaria=D(-1))
```
  El PE proyectado: `V' = V + reajuste reconocido`, `CF' = CF·D'/D`, curva reescalada a `V'` (OB-S2: 6 019,66 sin reajuste, 5 402,91 con él, 4 887,68 con más cuadrillas, 6 860,09 y 5 985,37 en los otros dos), y la obra que va «según el plan» da el PE de SF-E3 con su misma ubicación:
```python
# tests/unit/test_pe_proyectado.py
"""SL-E5: punto de equilibrio proyectado (spec S2 §4.7; RF-77) y `equilibrio` extraído (SL-E5).

Los dos escenarios de la memoria `control_ob_s2.md` (sin reajuste y con el reajuste reconocido de
75,90), la frontera `PE' = V'` exacta, la coherencia con SF-E3 (una obra que va según el plan da el
mismo PE y la misma ubicación) y que la extracción de `equilibrio` no movió TI-001.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from core.budget import punto_equilibrio
from core.budget.control import construir_estado
from core.budget.curva import generar_curva
from core.budget.equilibrio import EstadoEquilibrio
from core.budget.valor_ganado import equilibrio_proyectado, indicadores, reproyectar
from tests.fixtures import control_ob_s2 as ob

D = Decimal
MONTOS = D("0.01")
CF = D(600)
VENTA = D(5060)
EAC = D(4480)
SIN_REAJUSTE, CON_REAJUSTE = D(0), D("75.90")


def _pe(*, cv, dias, reajuste, plan=ob.PLAN):
    presupuesto = ob.elaborar_ob_s2().presupuesto
    return equilibrio_proyectado(
        venta=VENTA,
        costo_variable=cv,
        costo_fijo=CF,
        dias_plan=20,
        dias_proyectados=dias,
        reajuste_reconocido=reajuste,
        curva=generar_curva(presupuesto, plan),
    )


def _reproyectado():
    return reproyectar(
        construir_estado(
            ob.instantanea(ob.v01_v02()), costo_real=ob.COSTO_REAL, precios=ob.precios_del_corte()
        )
    )


def test_aceptar_el_retraso_sin_reajuste_no_se_alcanza_en_6_019_66():
    pe = _pe(cv=EAC, dias=23, reajuste=SIN_REAJUSTE, plan=_reproyectado().plan)
    assert pe.estado is EstadoEquilibrio.NO_SE_ALCANZA
    assert abs(pe.punto - D("6019.66")) <= MONTOS
    assert (pe.venta, pe.costo_fijo) == (VENTA, D(690))


def test_aceptar_el_retraso_con_el_reajuste_reconocido_no_se_alcanza_en_5_402_91():
    pe = _pe(cv=EAC, dias=23, reajuste=CON_REAJUSTE, plan=_reproyectado().plan)
    assert pe.estado is EstadoEquilibrio.NO_SE_ALCANZA
    assert abs(pe.punto - D("5402.91")) <= MONTOS
    assert pe.venta == D("5135.90")


PLAN_DE_CUADRILLAS = [
    ("Semana 1", [("OB-A", D("0.4"))]),
    ("Semana 2", [("OB-A", D("0.5")), ("OB-B", D("0.3"))]),
    ("Semana 3", [("OB-A", D("0.1")), ("OB-B", D("0.54")), ("OB-C", D("0.72"))]),
    ("Semana 4", [("OB-B", D("0.16")), ("OB-C", D("0.28"))]),
]


def test_mas_cuadrillas_sin_reajuste_no_se_alcanza_con_cv_4600_y_cf_510():
    pe = _pe(cv=D(4600), dias=17, reajuste=SIN_REAJUSTE, plan=PLAN_DE_CUADRILLAS)
    assert pe.estado is EstadoEquilibrio.NO_SE_ALCANZA
    assert pe.costo_fijo == D(510) and abs(pe.punto - D("5610.00")) <= MONTOS


def test_mas_cuadrillas_con_el_reajuste_se_alcanza_en_4_887_68_y_se_ubica_en_s4():
    pe = _pe(cv=D(4600), dias=17, reajuste=CON_REAJUSTE, plan=PLAN_DE_CUADRILLAS)
    assert pe.estado is EstadoEquilibrio.CALCULADO
    assert abs(pe.punto - D("4887.68")) <= MONTOS
    assert abs(pe.porcentaje - D("95.17")) <= MONTOS
    assert pe.periodo.startswith("Semana 4")  # el acumulado llega a 82 % en S3 y a 100 % en S4


def test_pe_igual_a_v_exacto_se_alcanza_con_un_reajuste_de_50():
    """V' = 5110 = CV' + CF' = 4600 + 510: PE' = 5110 = V' exacto, se alcanza (frontera)."""
    pe = _pe(cv=D(4600), dias=17, reajuste=D(50), plan=PLAN_DE_CUADRILLAS)
    assert (pe.estado, pe.punto, pe.venta) == (EstadoEquilibrio.CALCULADO, D(5110), D(5110))
    assert pe.periodo.startswith("Semana 4")
    sin_un_centavo = _pe(cv=D(4600), dias=17, reajuste=D("49.99"), plan=PLAN_DE_CUADRILLAS)
    assert sin_un_centavo.estado is EstadoEquilibrio.NO_SE_ALCANZA


def test_cada_opcion_necesita_un_reajuste_minimo_igual_a_cv_mas_cf_menos_v():
    """Comprobación cruzada de la memoria: aceptar 110,00; cuadrillas 50,00; horas 165,3125."""
    minimos = {"aceptar": (EAC, 690), "cuadrillas": (D(4600), 510), "horas": (D("4595.3125"), 630)}
    esperados = {"aceptar": D("110.00"), "cuadrillas": D("50.00"), "horas": D("165.3125")}
    for nombre, (cv, cf) in minimos.items():
        assert cv + cf - VENTA == esperados[nombre]


def test_el_costo_fijo_se_causa_en_el_tiempo_cf_prima_es_cf_por_d_prima_sobre_d():
    assert _pe(cv=EAC, dias=20, reajuste=SIN_REAJUSTE).costo_fijo == CF
    assert _pe(cv=EAC, dias=10, reajuste=SIN_REAJUSTE).costo_fijo == D(300)


def test_sin_margen_el_pe_proyectado_no_existe():
    pe = _pe(cv=D(5060), dias=20, reajuste=SIN_REAJUSTE)
    assert pe.estado is EstadoEquilibrio.NO_EXISTE


def test_dias_del_plan_invalidos_se_rechazan():
    with pytest.raises(ValueError, match="1 o mas"):
        equilibrio_proyectado(
            venta=VENTA, costo_variable=EAC, costo_fijo=CF, dias_plan=0, dias_proyectados=1,
            reajuste_reconocido=SIN_REAJUSTE, curva=(),
        )  # fmt: skip


def test_una_obra_que_va_segun_el_plan_da_el_pe_de_sf_e3_con_su_misma_ubicacion():
    """EAC = BAC, D' = D, curva reproyectada = plan, sin reajuste: PE' = PE de SF-E3."""
    segun_el_plan = [
        ob.valuacion(
            dict(
                numero=f"V-0{n}", desde=desde, hasta=hasta, fecha=hasta, inspector=ob.INSPECTOR,
                lineas=lineas,
            ),
            n,
        )
        for n, (desde, hasta, lineas) in enumerate(
            [
                (date(2026, 11, 2), date(2026, 11, 6), [ob.LineaValuacion("OB-A", D(50))]),
                (
                    date(2026, 11, 9),
                    date(2026, 11, 13),
                    [ob.LineaValuacion("OB-A", D(50)), ob.LineaValuacion("OB-B", D(100))],
                ),
            ],
            start=1,
        )
    ]  # fmt: skip
    precios_base = ob.precios_del_corte().__class__("comprobacion", "base", ob.UNITARIOS_BASE)
    estado = construir_estado(
        ob.instantanea(segun_el_plan), costo_real=D(1500), precios=precios_base
    )
    ind = indicadores(estado)
    reproyeccion = reproyectar(estado)
    assert (ind.spi, ind.cpi, ind.eac_sistema, ind.ev == ind.pv) == (D(1), D(1), D(4000), True)
    assert reproyeccion.termino == 20
    presupuesto = ob.elaborar_ob_s2().presupuesto
    curva = generar_curva(presupuesto, reproyeccion.plan)
    assert curva == presupuesto.curva
    proyectado = equilibrio_proyectado(
        venta=presupuesto.total,
        costo_variable=ind.eac_sistema,
        costo_fijo=CF,
        dias_plan=20,
        dias_proyectados=reproyeccion.termino,
        reajuste_reconocido=D(0),
        curva=curva,
    )
    base = punto_equilibrio(presupuesto, ob.PARAMETROS)
    assert (proyectado.estado, proyectado.punto, proyectado.porcentaje) == (
        base.estado,
        base.punto,
        base.porcentaje,
    )
    assert (proyectado.periodo, proyectado.fraccion_periodo) == (
        base.periodo,
        base.fraccion_periodo,
    )
    assert abs(base.punto - D("2864.15")) <= MONTOS  # el PE base de OB-S2 (S3 §7.1)
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_reproyeccion.py tests/unit/test_alertas.py tests/unit/test_pe_proyectado.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'reproyectar' from 'core.budget.valor_ganado'`
```bash
git add tests/unit/test_reproyeccion.py tests/unit/test_alertas.py tests/unit/test_pe_proyectado.py
git commit -m "test(core): reproyeccion, alertas y PE proyectado de OB-S2 en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
```diff
--- a/core/budget/valor_ganado.py
+++ b/core/budget/valor_ganado.py
@@ -18,27 +18,39 @@
 
 from __future__ import annotations
 
+import re
 from collections import defaultdict
-from collections.abc import Mapping, Sequence
+from collections.abc import Collection, Mapping, Sequence
 from dataclasses import dataclass
 from decimal import ROUND_CEILING, ROUND_HALF_EVEN, Decimal, localcontext
 
 from core.budget.curva import PeriodoPlan
-from core.contracts.presupuesto import Presupuesto
+from core.budget.equilibrio import EstadoEquilibrio, PuntoEquilibrio, equilibrio
+from core.contracts.presupuesto import Presupuesto, PuntoCurva
+from core.contracts.verificacion import Severidad
 
 __all__ = [
     "NATURALEZA_DECLARADA",
     "PERSPECTIVA_COSTO",
     "PERSPECTIVA_PRECIO",
+    "Alerta",
+    "Alertas",
     "EstadoObra",
     "Indicadores",
     "ParametrosControl",
     "PartidaControl",
     "PreciosDelCorte",
+    "ProyeccionPartida",
+    "Reproyeccion",
     "Separacion",
+    "alertas",
+    "equilibrio_proyectado",
+    "fin_excede",
     "indicadores",
     "partidas_de_plan",
     "precios_por_escalatoria",
+    "proyectar_partida",
+    "reproyectar",
     "separar_desvio",
     "techo_de_dias",
 ]
@@ -50,6 +62,8 @@
 UNO = Decimal(1)
 CIEN = Decimal(100)
 PRECISION_DE_DIAS = Decimal("1e-12")
+LIMITE_DE_PERIODOS = 10_000
+_ETIQUETA = re.compile(r"^(.*?)(\d+)$")
 
 
 def _contexto():
@@ -457,6 +471,425 @@
 # ---------------------------------------------------------------------------------------------
 
 
+@dataclass(frozen=True, slots=True)
+class ProyeccionPartida:
+    """Lo proyectado de una partida (§4.4). `fin` es el día hábil (con decimales) en que termina
+    su obra pendiente; `None` si no le queda obra o no es proyectable (`motivo`)."""
+
+    codigo: str
+    indice: Decimal | None
+    ritmo: Decimal | None
+    pendiente: Decimal
+    fin: Decimal | None
+    detenida: bool = False
+    sin_evidencia: bool = False
+    motivo: str = ""
+
+
+@dataclass(frozen=True, slots=True)
+class Reproyeccion:
+    """El plan reproyectado (lo ejecutado más lo proyectado, un `PeriodoPlan` válido para
+    `generar_curva`), la proyección de cada partida y el término en días hábiles (`None` si alguna
+    partida con obra pendiente no es proyectable)."""
+
+    plan: tuple[PeriodoPlan, ...]
+    partidas: tuple[ProyeccionPartida, ...]
+    termino: int | None
+    motivo_termino: str
+
+    @property
+    def detenidas(self) -> tuple[str, ...]:
+        return tuple(p.codigo for p in self.partidas if p.detenida)
+
+    @property
+    def no_proyectables(self) -> tuple[str, ...]:
+        return tuple(p.codigo for p in self.partidas if p.motivo)
+
+    def de(self, codigo: str) -> ProyeccionPartida:
+        return next(p for p in self.partidas if p.codigo == codigo)
+
+
+def _etiqueta_siguiente(etiquetas: Sequence[str], numero: int) -> str:
+    """La etiqueta del período `numero` si pasa del plan: «Semana 4» continúa «Semana 5»."""
+    if etiquetas:
+        encontrada = _ETIQUETA.match(etiquetas[-1])
+        if encontrada:
+            avance = numero - len(etiquetas)
+            return f"{encontrada.group(1)}{int(encontrada.group(2)) + avance}"
+    return f"Periodo {numero}"
+
+
+def _ejecutado_por_periodo(
+    estado: EstadoObra, partida: PartidaControl
+) -> tuple[dict[int, Decimal], Decimal]:
+    """Las fracciones ya ejecutadas de la partida por período (con tope en 1, S2-R8) y su suma."""
+    fracciones: dict[int, Decimal] = {}
+    acumulado = CERO
+    periodos = sorted(n for (codigo, n) in estado.por_periodo if codigo == partida.codigo)
+    with _contexto():
+        for n in periodos:
+            fraccion = min(
+                estado.por_periodo[(partida.codigo, n)] / partida.cantidad, UNO - acumulado
+            )
+            if fraccion > CERO:
+                fracciones[n] = fracciones.get(n, CERO) + fraccion
+                acumulado += fraccion
+    if estado.cantidad_ejecutada(partida) == partida.cantidad and fracciones:
+        ultimo = max(fracciones)
+        fracciones[ultimo] += UNO - acumulado
+        acumulado = UNO
+    return fracciones, acumulado
+
+
+def reproyectar(
+    estado: EstadoObra,
+    *,
+    multiplicador: Mapping[str, Decimal] | None = None,
+    adelantar: Collection[str] = (),
+) -> Reproyeccion:
+    """Reproyecta el plan al ritmo real (§4.4).
+
+    `multiplicador` escala el ritmo de una partida (más cuadrillas, horas extra) y `adelantar`
+    lleva su inicio al período siguiente al corte (partidas en paralelo). Cada partida con obra
+    pendiente avanza a `r = s / n · multiplicador` por período, con `s` el índice de la partida
+    (`EV_p / PV_p`) o, sin evidencia propia, el SPI global."""
+    multiplicador = multiplicador or {}
+    cantidad_de_periodos = estado.periodos
+    siguiente, restantes = _corte(estado)
+    ind = indicadores(estado)
+    ritmos: dict[str, tuple[dict[int, Decimal], ProyeccionPartida]] = {}
+    for partida in estado.partidas:
+        ritmos[partida.codigo] = _proyectar_partida(
+            estado,
+            partida,
+            ind.spi,
+            multiplicador.get(partida.codigo, UNO),
+            partida.codigo in adelantar,
+            (siguiente, restantes),
+        )
+    ultimo = max(
+        [cantidad_de_periodos] + [max(fracciones, default=0) for fracciones, _ in ritmos.values()]
+    )
+    plan: list[PeriodoPlan] = []
+    for n in range(1, ultimo + 1):
+        etiqueta = (
+            estado.etiquetas[n - 1]
+            if n <= cantidad_de_periodos
+            else _etiqueta_siguiente(estado.etiquetas, n)
+        )
+        reparto = tuple(
+            (partida.codigo, ritmos[partida.codigo][0][n])
+            for partida in estado.partidas
+            if ritmos[partida.codigo][0].get(n, CERO) > CERO
+        )
+        plan.append((etiqueta, reparto))
+    while len(plan) > 1 and not plan[-1][1]:
+        plan.pop()
+    proyecciones = tuple(proyeccion for _, proyeccion in ritmos.values())
+    termino, motivo = _termino(estado, proyecciones)
+    return Reproyeccion(tuple(plan), proyecciones, termino, motivo)
+
+
+def proyectar_partida(
+    estado: EstadoObra,
+    codigo: str,
+    *,
+    multiplicador: Decimal = UNO,
+    adelantada: bool = False,
+    spi_global: Decimal | None = None,
+) -> ProyeccionPartida:
+    """La proyección de una sola partida: lo mismo que `reproyectar` hace con cada una, sin
+    recorrer las demás. `spi_global` es el de `indicadores(estado).spi`."""
+    partida = next(p for p in estado.partidas if p.codigo == codigo)
+    siguiente, restantes = _corte(estado)
+    return _proyectar_partida(
+        estado, partida, spi_global, multiplicador, adelantada, (siguiente, restantes)
+    )[1]
+
+
+def fin_excede(fin: Decimal, objetivo: int) -> bool:
+    """True si el día hábil `fin` (con decimales) pasa del día `objetivo`: la igualdad exacta
+    cuenta como recuperado (§7.3)."""
+    return fin.quantize(PRECISION_DE_DIAS) > objetivo
+
+
+def _corte(estado: EstadoObra) -> tuple[int, int]:
+    """El período siguiente al corte y los días hábiles que le quedan."""
+    completos, transcurridos = divmod(estado.dia, estado.dias_por_periodo)
+    return completos + 1, estado.dias_por_periodo - transcurridos
+
+
+def _proyectar_partida(
+    estado: EstadoObra,
+    partida: PartidaControl,
+    spi_global: Decimal | None,
+    multiplicador: Decimal,
+    adelantada: bool,
+    corte: tuple[int, int],
+) -> tuple[dict[int, Decimal], ProyeccionPartida]:
+    siguiente, restantes = corte
+    largo = estado.dias_por_periodo
+    if partida.cantidad == CERO:
+        base = {n: f for n, f in enumerate(partida.plan, start=1) if f > CERO}
+        return base, ProyeccionPartida(partida.codigo, None, None, CERO, None)
+    hechas, hecho = _ejecutado_por_periodo(estado, partida)
+    pendiente = UNO - hecho
+    fracciones = dict(hechas)
+    if pendiente <= CERO:
+        return fracciones, ProyeccionPartida(partida.codigo, None, None, CERO, None)
+    qe = estado.cantidad_ejecutada(partida)
+    planificada = estado.fraccion_planificada(partida)
+    detenida = planificada > CERO and qe == CERO
+    with _contexto():
+        if planificada > CERO and qe > CERO:
+            indice: Decimal | None = qe / (partida.cantidad * planificada)
+            sin_evidencia = False
+        else:
+            indice = UNO if spi_global is None else spi_global
+            sin_evidencia = not detenida
+    if partida.periodos_activos == 0:
+        return fracciones, ProyeccionPartida(
+            partida.codigo, indice, None, pendiente, None, motivo="la partida no esta en el plan"
+        )
+    if not indice:
+        return fracciones, ProyeccionPartida(
+            partida.codigo,
+            indice,
+            None,
+            pendiente,
+            None,
+            detenida=detenida,
+            motivo="el SPI global es 0: sin ritmo no se proyecta",
+        )
+    with _contexto():
+        ritmo = indice / partida.periodos_activos * multiplicador
+    empezada = qe > CERO or partida.inicio <= siguiente
+    inicio = siguiente if (empezada or adelantada) else partida.inicio
+    restante = pendiente
+    n = inicio
+    ultimo_n, ultima = inicio, CERO
+    while restante > CERO:
+        if n - inicio > LIMITE_DE_PERIODOS:
+            raise ValueError("la reproyeccion no termina: el ritmo es demasiado bajo")
+        with _contexto():
+            tope = ritmo * restantes / largo if n == siguiente else ritmo
+        tomado = min(tope, restante)
+        fracciones[n] = fracciones.get(n, CERO) + tomado
+        restante -= tomado
+        ultimo_n, ultima = n, tomado
+        n += 1
+    with _contexto():
+        base = estado.dia if ultimo_n == siguiente else (ultimo_n - 1) * largo
+        fin = Decimal(base) + ultima * largo / ritmo
+    return fracciones, ProyeccionPartida(
+        partida.codigo,
+        indice,
+        ritmo,
+        pendiente,
+        fin,
+        detenida=detenida,
+        sin_evidencia=sin_evidencia,
+    )
+
+
+def _termino(
+    estado: EstadoObra, proyecciones: Sequence[ProyeccionPartida]
+) -> tuple[int | None, str]:
+    sin_ritmo = [p.codigo for p in proyecciones if p.motivo]
+    if sin_ritmo:
+        return None, "no proyectable: " + ", ".join(sin_ritmo)
+    fines = [p.fin for p in proyecciones if p.fin is not None]
+    if not fines:
+        return estado.dia_ultima_valuacion, "nada queda pendiente: la fecha de la ultima valuacion"
+    return techo_de_dias(max(fines)), ""
+
+
 # ---------------------------------------------------------------------------------------------
 # Punto de equilibrio proyectado y alertas
 # ---------------------------------------------------------------------------------------------
+
+
+def equilibrio_proyectado(
+    *,
+    venta: Decimal,
+    costo_variable: Decimal,
+    costo_fijo: Decimal,
+    dias_plan: int,
+    dias_proyectados: int,
+    reajuste_reconocido: Decimal,
+    curva: Sequence[PuntoCurva],
+) -> PuntoEquilibrio:
+    """El punto de equilibrio con `V' = V + reajuste reconocido`, `CV'` dado y `CF' = CF · D'/D`
+    (S2-R7), ubicado en la curva reproyectada (§4.7). No suma ningún reajuste proyectado: recibe
+    el ya reconocido como dato (S2-R15). `curva` es la del plan reproyectado sobre la venta `V`:
+    se reescala a `V'` para ubicar el punto por su fracción del total."""
+    if dias_plan < 1:
+        raise ValueError("los dias del plan base deben ser 1 o mas")
+    with _contexto():
+        venta_proyectada = venta + reajuste_reconocido
+        fijo = costo_fijo * dias_proyectados / dias_plan
+        if reajuste_reconocido != CERO and venta != CERO:
+            curva = tuple(
+                PuntoCurva(
+                    p.periodo,
+                    p.monto * venta_proyectada / venta,
+                    p.acumulado * venta_proyectada / venta,
+                )
+                for p in curva
+            )
+        return equilibrio(venta_proyectada, costo_variable, fijo, curva)
+
+
+@dataclass(frozen=True, slots=True)
+class Alerta:
+    """Una alerta con su umbral y la naturaleza de este (§4.5)."""
+
+    codigo: str
+    severidad: Severidad
+    descripcion: str
+    valor_observado: Decimal | None
+    umbral: Decimal | None
+    naturaleza_umbral: str = NATURALEZA_DECLARADA
+
+
+@dataclass(frozen=True, slots=True)
+class Alertas:
+    """Las alertas que saltaron y las que no se pudieron evaluar, con el motivo (UC-20 1a-1d)."""
+
+    alertas: tuple[Alerta, ...]
+    no_evaluadas: Mapping[str, str]
+
+
+def alertas(
+    ind: Indicadores,
+    sep: Separacion,
+    reproyeccion: Reproyeccion,
+    *,
+    dias_plan: int,
+    equilibrio_base: PuntoEquilibrio | None,
+    equilibrio_proyectado: PuntoEquilibrio | None,
+    parametros: ParametrosControl,
+) -> Alertas:
+    """Evalúa AL-1 a AL-6 (§4.5). Si el indicador de una alerta no está disponible, no se evalúa."""
+    salidas: list[Alerta] = []
+    no_evaluadas: dict[str, str] = {}
+    if ind.spi is None:
+        no_evaluadas["AL-1"] = ind.no_disponible.get("SPI", "SPI no aplica")
+    elif ind.spi < UNO:
+        error = ind.spi < parametros.spi_error
+        salidas.append(
+            Alerta(
+                "AL-1",
+                Severidad.ERROR if error else Severidad.ADVERTENCIA,
+                f"retraso: SPI {_cuatro(ind.spi)}",
+                ind.spi,
+                parametros.spi_error,
+            )
+        )
+    if ind.cpi is None:
+        no_evaluadas["AL-2"] = ind.no_disponible.get("CPI", "CPI no disponible")
+    elif ind.cpi < UNO:
+        error = ind.cpi < parametros.cpi_error
+        salidas.append(
+            Alerta(
+                "AL-2",
+                Severidad.ERROR if error else Severidad.ADVERTENCIA,
+                f"sobrecosto: CPI {_cuatro(ind.cpi)}",
+                ind.cpi,
+                parametros.cpi_error,
+            )
+        )
+    salidas.extend(_alerta_de_termino(reproyeccion, dias_plan, parametros, no_evaluadas))
+    salidas.extend(
+        _alerta_de_equilibrio(equilibrio_base, equilibrio_proyectado, parametros, no_evaluadas)
+    )
+    if sep.precio is None or ind.ev <= CERO:
+        no_evaluadas["AL-5"] = sep.no_disponible.get("precio", "sin avance ejecutado")
+    elif abs(sep.precio) >= parametros.precio_info * ind.ev:
+        salidas.append(
+            Alerta(
+                "AL-5",
+                Severidad.INFO,
+                "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvia "
+                f"{sep.precio} sobre un valor ganado de {ind.ev}",
+                abs(sep.precio),
+                parametros.precio_info * ind.ev,
+            )
+        )
+    salidas.extend(
+        Alerta(
+            "AL-6",
+            Severidad.ADVERTENCIA,
+            f"la partida {codigo} tiene trabajo planificado y ningun avance (detenida)",
+            None,
+            None,
+        )
+        for codigo in reproyeccion.detenidas
+    )
+    return Alertas(tuple(salidas), no_evaluadas)
+
+
+def _cuatro(valor: Decimal) -> str:
+    return format(valor.quantize(Decimal("0.0001")), "f")
+
+
+def _alerta_de_termino(
+    reproyeccion: Reproyeccion,
+    dias_plan: int,
+    parametros: ParametrosControl,
+    no_evaluadas: dict[str, str],
+) -> list[Alerta]:
+    if reproyeccion.termino is None:
+        no_evaluadas["AL-3"] = reproyeccion.motivo_termino
+        return []
+    retraso = reproyeccion.termino - dias_plan
+    if retraso <= 0:
+        return []
+    error = Decimal(retraso) > parametros.retraso_error * dias_plan
+    return [
+        Alerta(
+            "AL-3",
+            Severidad.ERROR if error else Severidad.ADVERTENCIA,
+            f"el termino proyectado (dia {reproyeccion.termino}) pasa {retraso} dia(s) habil(es) "
+            f"del plan base (dia {dias_plan})",
+            Decimal(retraso),
+            parametros.retraso_error * dias_plan,
+        )
+    ]
+
+
+def _alerta_de_equilibrio(
+    base: PuntoEquilibrio | None,
+    proyectado: PuntoEquilibrio | None,
+    parametros: ParametrosControl,
+    no_evaluadas: dict[str, str],
+) -> list[Alerta]:
+    if proyectado is None or base is None:
+        no_evaluadas["AL-4"] = "el punto de equilibrio no aplica o AC no esta disponible"
+        return []
+    if proyectado.estado in (EstadoEquilibrio.NO_SE_ALCANZA, EstadoEquilibrio.NO_EXISTE):
+        return [
+            Alerta(
+                "AL-4",
+                Severidad.ERROR,
+                f"el punto de equilibrio proyectado: {proyectado.mensaje}",
+                proyectado.porcentaje,
+                base.porcentaje,
+            )
+        ]
+    if (
+        proyectado.porcentaje is not None
+        and base.porcentaje is not None
+        and proyectado.porcentaje - base.porcentaje > parametros.equilibrio_puntos
+    ):
+        return [
+            Alerta(
+                "AL-4",
+                Severidad.ADVERTENCIA,
+                "el punto de equilibrio proyectado sube mas de "
+                f"{parametros.equilibrio_puntos} puntos porcentuales sobre el de la linea base",
+                proyectado.porcentaje - base.porcentaje,
+                parametros.equilibrio_puntos,
+            )
+        ]
+    return []
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_reproyeccion.py tests/unit/test_alertas.py tests/unit/test_pe_proyectado.py tests/unit/test_valor_ganado.py tests/unit/test_equilibrio_extraido.py -q -W error` → 44 pruebas nuevas en verde y las de la tarea 7 sin cambio.
Run: `uv run ruff check core/budget/valor_ganado.py tests/unit/test_reproyeccion.py tests/unit/test_alertas.py tests/unit/test_pe_proyectado.py` y la guardia del núcleo.
- [ ] **Paso 5: Commit**
```bash
git add core/budget/valor_ganado.py
git commit -m "feat(core): reproyeccion por partida, alertas AL-1 a AL-6 y PE proyectado" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 9: SL-E5c — control al corte, reajuste reconocido y generador de obras

**Rama:** `inc/070-s2-2-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `scripts/generar_obra_control.py`, `tests/integration/test_control.py`, `tests/integration/test_reajuste_reconocido.py`, `tests/unit/test_generar_obra_control.py`
- Modificar: `core/budget/control.py` (agrega `calcular_control`, `costo_real_al_corte`, `precios_del_corte_de_version`, `contexto_de_recuperacion`, los parámetros de control y `ResultadoControl`), `core/budget/puente.py` (agrega `reajuste_reconocido`), `scripts/README.md` (fila de `generar_obra_control.py`)

**Interfaces:**
- Consume: de las tareas 7 y 8: todo `core.budget.valor_ganado`; de la tarea 6: `core.budget.puente`, `tests.fixtures.reajuste_ob_s2`; de S1: `cargar_estudio(session, id).resultado.periodos[].reconocido`, `EstudioReajuste.estado`.
- Produce:
- `core/budget/control.py`:
  - `OBJETO_PARAMETRO = 'parametro'`
  - `class ResultadoControl [instantanea: InstantaneaControl; estado: EstadoObra; indicadores: Indicadores; separacion: Separacion; reproyeccion: Reproyeccion; equilibrio_base: PuntoEquilibrio | None; equilibrio_proyectado: PuntoEquilibrio | None; reajuste: ReajusteReconocido; alertas: Alertas; informe: InformeAuditoria; costos_sin_tasa: tuple[CostoReal, ...]; parametros: ParametrosControl; venta: Decimal; costo_fijo: Decimal]`
  - `def precios_del_corte_de_version(session: Session, proyecto_nombre: str, codigo_version: str, perspectiva: str, catalogo: Catalogo) -> PreciosDelCorte`
  - `def costo_real_al_corte(session: Session, instantanea: InstantaneaControl, *, lado: str=LADO_POR_DEFECTO) -> tuple[Decimal | None, tuple[CostoReal, ...]]`
  - `def calcular_control(session: Session, proyecto_nombre: str, *, catalogo: Catalogo, corte: date | None=None, precios: PreciosDelCorte | None=None, parametros: ParametrosControl | None=None, lado: str=LADO_POR_DEFECTO) -> ResultadoControl`
  - `def parametros_de_control(session: Session, proyecto_nombre: str) -> ParametrosControl`
  - `def guardar_parametros(session: Session, proyecto_nombre: str, parametros: ParametrosControl, *, fuente: str, responsable: str, ahora: datetime | None=None) -> list[CambioEditado]`
  - `def composiciones_de_la_linea_base(resultado: ResultadoControl) -> dict[str, ComposicionAPU]`
- `core/budget/puente.py`:
  - `class EstudioSumado [id: int; version_id: int; fecha_calculo: date; estado: str; monto: Decimal; moneda: str]`
  - `class ReajusteReconocido [monto: Decimal; moneda: str; estudios: tuple[EstudioSumado, ...]; omitidos: tuple[EstudioSumado, ...]]`
  - `def reajuste_reconocido(session: Session, proyecto_nombre: str, corte: date) -> ReajusteReconocido`
- `scripts/generar_obra_control.py`:
  - `D = Decimal`
  - `NOMBRE = 'OBRA-GENERADA'`
  - `CODIGO = 'GEN-001'`
  - `INICIO = date(2026, 11, 2)`
  - `MONEDA = 'USD'`
  - `PARAMETROS = ParametrosCosto(D('6.00'), D('1.00'), D('0.15'), D('0.10'))`
  - `FUENTE = 'generador determinista (datos ficticios)'`
  - `RESPONSABLE = 'Residente Ficticio'`
  - `TRAMOS = (1, 2, 4, 5)`
  - `class ObraGenerada [presupuesto: Presupuesto; plan: tuple[PeriodoPlan, ...]; composiciones: dict[str, ComposicionAPU]; items: list[ItemComputo]; valuaciones: tuple[Valuacion, ...]; costos: tuple[CostoReal, ...]; precios: PreciosDelCorte; calendario: Calendario; corte: date]`
  - `def generar(partidas: int=500, periodos: int=52, valuaciones: int=26, semilla: int=0) -> ObraGenerada`
  - `def sembrar(sesion, obra: ObraGenerada, *, con_valuaciones: bool=True) -> None`
  - `def registrar_valuacion_de(sesion, valuacion: Valuacion)`
  - `def registrar_costo_de(sesion, costo: CostoReal)`

- [ ] **Paso 0: Expediente SL-E5** (ver tarea 7, paso 0).
- [ ] **Paso 1: Escribir las pruebas que fallan**
  El control al corte de punta a punta con la base (la memoria completa; la perspectiva *precio*; costos en Bs con la tasa de su fecha y sin tasa; parámetros que gobiernan las alertas con su `RegistroCambio`):
```python
# tests/integration/test_control.py
"""SL-E5: el control de OB-S2 de la base al resultado (spec S2 §4, §5.3; RF-75 a RF-77).

`calcular_control` lee la base, convierte los costos con la tasa de su fecha (S1) y devuelve
indicadores, separación, reproyección, punto de equilibrio y alertas, sin escribir nada.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core import models
from core.budget.control import (
    calcular_control,
    guardar_parametros,
    parametros_de_control,
    precios_del_corte_de_version,
)
from core.budget.puente import estudio_con_valuaciones
from core.budget.valor_ganado import ParametrosControl
from core.budget.valuaciones import anular_valuacion, registrar_costo
from core.catalog import Catalogo
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz

D = Decimal
MONTOS = D("0.01")


def _control(sesion, **extra):
    extra.setdefault("precios", ob.precios_del_corte())
    return calcular_control(sesion, ob.NOMBRE, catalogo=Catalogo(sesion), **extra)


def _tasa(sesion, fecha: date, valor: str = "850"):
    registrar_importacion(
        sesion, definicion_tasa("venta"), [Observacion(fecha, D(valor))], archivo="tasa.xls",
        huella=f"{fecha.day:02d}" * 32, fuente="https://www.bcv.org.ve/",
        fecha_descarga=date(2026, 11, 20), responsable="Admin", filas_leidas=1, filas_rechazadas=0,
    )  # fmt: skip


def _sin_costos(sesion):
    sesion.query(models.CostoReal).delete()
    sesion.flush()


def test_ob_s2_de_punta_a_punta_da_la_memoria(obra):
    ob.registrar_v01_y_v02(obra)
    r = _control(obra)
    assert r.instantanea.corte == ob.CORTE
    ind = r.indicadores
    assert (ind.pv, ind.ev, ind.ac) == (D(1500), D(1200), D(1280))
    assert abs(ind.eac_sistema - D(4480)) <= MONTOS and r.reproyeccion.termino == 23
    assert (r.separacion.precio, r.separacion.consumo) == (D(-60), D(-20))
    assert {a.codigo for a in r.alertas.alertas} == {"AL-1", "AL-2", "AL-3", "AL-4", "AL-5"}
    assert abs(r.equilibrio_base.punto - D("2864.15")) <= MONTOS
    assert abs(r.equilibrio_proyectado.punto - D("6019.66")) <= MONTOS  # sin reajuste reconocido
    assert r.reajuste.monto == 0 and r.reajuste.estudios == ()
    assert r.informe.hallazgos == () and r.informe.cumple
    assert (r.venta, r.costo_fijo) == (D(5060), D(600))


def test_una_valuacion_anulada_deja_de_contar_y_al_registrarla_de_nuevo_ev_vuelve(obra):
    _, segunda = ob.registrar_v01_y_v02(obra)
    anular_valuacion(obra, segunda.id, motivo="no aprobada", responsable="Ing.")
    anulada = _control(obra, corte=ob.CORTE)
    assert anulada.indicadores.ev == D(400)  # solo V-01: A 40 x 10
    ob.registrar(obra, ob.V02, ahora=None)
    assert _control(obra, corte=ob.CORTE).indicadores.ev == D(1200)  # el EV de la memoria


def test_calcular_el_control_no_escribe_nada(obra):
    ob.registrar_v01_y_v02(obra)
    tablas = (models.Valuacion, models.LineaValuacion, models.RegistroCambio, models.Presupuesto)

    def cuentas():
        return [obra.scalar(select(func.count()).select_from(t)) for t in tablas]

    antes = cuentas()
    _control(obra)
    assert cuentas() == antes


def test_un_costo_en_bs_se_convierte_con_la_tasa_de_su_fecha(obra):
    ob.registrar_v01_y_v02(obra)
    _sin_costos(obra)
    _tasa(obra, date(2026, 11, 13), "850")
    registrar_costo(
        obra, ob.NOMBRE, monto=D("1088000"), moneda="Bs", fecha=date(2026, 11, 13),
        fuente="factura ficticia", responsable="Ing.",
    )  # fmt: skip
    r = _control(obra)
    assert r.indicadores.ac == D(1280)  # 1 088 000 Bs / 850
    assert r.indicadores.cpi == D("0.9375") and r.costos_sin_tasa == ()


def test_un_costo_en_bs_sin_tasa_aplicable_deja_el_ac_no_disponible_y_lo_declara(obra):
    ob.registrar_v01_y_v02(obra)
    _tasa(obra, date(2026, 11, 4), "850")  # 9 dias antes del 13: mas de 7, se rechaza (S1-R2)
    registrar_costo(
        obra, ob.NOMBRE, monto=D("1000"), moneda="Bs", fecha=date(2026, 11, 13),
        fuente="factura ficticia", responsable="Ing.",
    )  # fmt: skip
    r = _control(obra)
    ind = r.indicadores
    assert (ind.ac, ind.cv, ind.cpi, ind.eac_sistema, ind.vac) == (None,) * 5
    assert (r.separacion.consumo, r.equilibrio_proyectado) == (None, None)
    assert [c.monto for c in r.costos_sin_tasa] == [D(1000)]
    assert "sin tasa aplicable para: 1000 Bs del 2026-11-13" in ind.no_disponible["AC"]
    assert (ind.pv, ind.ev) == (D(1500), D(1200)) and abs(ind.spi - D("0.8")) <= D("0.0001")
    assert r.reproyeccion.termino == 23 and r.separacion.precio == D(-60)
    assert "AL-2" in r.alertas.no_evaluadas and "AL-4" in r.alertas.no_evaluadas


def test_un_costo_posterior_al_corte_no_cuenta(obra):
    ob.registrar_v01_y_v02(obra)
    registrar_costo(
        obra, ob.NOMBRE, monto=D(999), moneda="USD", fecha=date(2026, 11, 14),
        fuente="factura ficticia", responsable="Ing.",
    )  # fmt: skip
    assert _control(obra).indicadores.ac == D(1280)


def test_los_precios_del_corte_por_comprobacion_directa_salen_de_una_version_revalorada(obra):
    ob.registrar_v01_y_v02(obra)
    rz.sembrar_revaloracion(obra)
    precios = precios_del_corte_de_version(obra, ob.NOMBRE, rz.REVALORADA, "costo", Catalogo(obra))
    assert precios.metodo == "comprobacion"
    assert precios.unitarios == ob.UNITARIOS_DEL_CORTE
    assert "OB-R01" in precios.fuente and "OB-S2 revalorada" in precios.fuente
    r = _control(obra, precios=precios)
    assert (r.separacion.precio, r.separacion.consumo) == (D(-60), D(-20))
    pu = precios_del_corte_de_version(obra, ob.NOMBRE, rz.REVALORADA, "precio", Catalogo(obra))
    assert pu.unitarios["OB-B"] == D("7.59")  # 6,00 x 1,265


def test_con_el_estudio_guardado_el_reajuste_reconocido_entra_al_pe_proyectado(obra):
    ob.registrar_v01_y_v02(obra)
    rz.sembrar_revaloracion(obra)
    estudio_con_valuaciones(
        obra, ob.NOMBRE, ob.CODIGO, rz.CLAUSULA, [rz.NOVIEMBRE], fecha_calculo=date(2026, 11, 13),
        fuente="estudio ficticio", responsable="Ing.",
    )  # fmt: skip
    r = _control(obra)
    assert r.reajuste.monto == D("75.90") and len(r.reajuste.estudios) == 1
    assert r.equilibrio_proyectado.venta == D("5135.90")
    assert abs(r.equilibrio_proyectado.punto - D("5402.91")) <= MONTOS
    assert {a.codigo for a in r.alertas.alertas} == {"AL-1", "AL-2", "AL-3", "AL-4", "AL-5"}


def test_la_perspectiva_precio_no_tiene_punto_de_equilibrio_y_el_consumo_es_cero(obra):
    ob.registrar_v01_y_v02(obra)
    ob.declarar_linea_base(obra, perspectiva="precio", desde=date(2026, 11, 10))
    pu = {c: u * D("1.265") for c, u in ob.UNITARIOS_DEL_CORTE.items()}
    r = _control(obra, precios=replace(ob.precios_del_corte(), unitarios=pu))
    assert r.instantanea.linea_base.perspectiva == "precio"
    assert (r.equilibrio_base, r.equilibrio_proyectado) == (None, None)
    assert r.separacion.consumo == 0
    assert "AL-4" in r.alertas.no_evaluadas


def test_los_parametros_de_control_se_guardan_con_su_registro_de_cambio(obra):
    assert parametros_de_control(obra, ob.NOMBRE) == ParametrosControl()  # sin fila: por defecto
    nuevos = replace(ParametrosControl(), spi_error=D("0.85"), horas_extra_dia=D("1.5"))
    cambios = guardar_parametros(
        obra, ob.NOMBRE, nuevos, fuente="criterio de la empresa", responsable="Ing.",
    )  # fmt: skip
    assert [(c.campo, c.valor_anterior, c.valor_nuevo) for c in cambios] == [
        ("spi_error", "0.90", "0.85"),
        ("horas_extra_dia", "2", "1.5"),
    ]
    assert parametros_de_control(obra, ob.NOMBRE) == nuevos
    registros = obra.scalars(
        select(models.RegistroCambio).where(models.RegistroCambio.objeto == "parametro")
    ).all()
    assert [r.clave for r in registros] == ["control|spi_error", "control|horas_extra_dia"]
    assert {r.fuente for r in registros} == {"criterio de la empresa"}
    assert guardar_parametros(obra, ob.NOMBRE, nuevos, fuente="x", responsable="y") == []
    with pytest.raises(ValueError, match="obligatoria"):
        guardar_parametros(obra, ob.NOMBRE, ParametrosControl(), fuente="", responsable="Ing.")


def test_los_parametros_guardados_gobiernan_las_alertas(obra):
    ob.registrar_v01_y_v02(obra)
    guardar_parametros(
        obra, ob.NOMBRE, replace(ParametrosControl(), spi_error=D("0.70")), fuente="f",
        responsable="Ing.",
    )  # fmt: skip
    alertas = {a.codigo: a for a in _control(obra).alertas.alertas}
    assert alertas["AL-1"].severidad.name == "ADVERTENCIA"  # SPI 0,80 >= 0,70
```
  El reajuste reconocido (RV-12, S2-R15): suma los montos reconocidos de los estudios de S1 guardados con fecha de cálculo ≤ corte, el más reciente de cada pareja parcial/cierre, en la moneda del proyecto; nunca un reajuste proyectado:
```python
# tests/integration/test_reajuste_reconocido.py
"""SL-E5: el reajuste ya reconocido que entra al punto de equilibrio proyectado (spec S2 §4.7,
S2-R15; RV-12; S1-R20 y S1-R21).

Es la suma de los montos reconocidos de los estudios de S1 **guardados** con fecha de cálculo menor
o igual al corte, sin los reemplazados: nunca un reajuste proyectado. El escenario «con reajuste»
de la memoria `control_ob_s2.md` es un estudio de noviembre «parcial al corte» de 75,90.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from core.budget.puente import estudio_con_valuaciones, reajuste_reconocido
from core.budget.reajuste import Mecanismo
from core.verification.valuaciones import LineaValuacion
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz

D = Decimal
CORTE = date(2026, 11, 13)


@pytest.fixture
def con_revaloracion(obra):
    ob.registrar_v01_y_v02(obra)
    rz.sembrar_revaloracion(obra)
    return obra


def _guardar(sesion, fecha_calculo, clausula=rz.CLAUSULA, **extra):
    return estudio_con_valuaciones(
        sesion, ob.NOMBRE, ob.CODIGO, clausula, [rz.NOVIEMBRE], fecha_calculo=fecha_calculo,
        fuente="estudio ficticio", responsable="Ing.", **extra,
    )  # fmt: skip


def test_sin_estudios_guardados_el_reajuste_reconocido_es_cero(con_revaloracion):
    reconocido = reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE)
    assert (reconocido.monto, reconocido.estudios, reconocido.moneda) == (D(0), (), "USD")


def test_el_estudio_parcial_de_la_memoria_suma_75_90(con_revaloracion):
    estudio = _guardar(con_revaloracion, CORTE)
    reconocido = reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE)
    assert reconocido.monto == D("75.90")
    (sumado,) = reconocido.estudios
    assert (sumado.id, sumado.estado, sumado.monto) == (estudio.id, "parcial al corte", D("75.90"))


def test_un_estudio_guardado_despues_del_corte_no_cuenta(con_revaloracion):
    _guardar(con_revaloracion, date(2026, 11, 14))
    assert reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE).monto == 0
    assert reajuste_reconocido(con_revaloracion, ob.NOMBRE, date(2026, 11, 14)).monto == D("75.90")


def test_de_un_parcial_y_su_cierre_cuenta_solo_el_mas_reciente(con_revaloracion):
    parcial = _guardar(con_revaloracion, CORTE)
    ob.registrar(
        con_revaloracion,
        dict(
            numero="V-03",
            desde=date(2026, 11, 23),
            hasta=date(2026, 11, 27),
            fecha=date(2026, 11, 30),
            inspector=ob.INSPECTOR,
            lineas=[LineaValuacion("OB-B", D(20))],
        ),
    )
    cierre = _guardar(con_revaloracion, date(2026, 11, 30), reemplaza_a=parcial.id)
    assert cierre.estado == "cerrado"
    entre = reajuste_reconocido(con_revaloracion, ob.NOMBRE, date(2026, 11, 20))
    assert entre.monto == D("75.90")  # el cierre se guarda despues: el parcial aun suma
    al_cierre = reajuste_reconocido(con_revaloracion, ob.NOMBRE, date(2026, 11, 30))
    assert al_cierre.monto == D("101.20")  # B 80 x (7,59 - 6,325): no 177,10
    assert [e.id for e in al_cierre.estudios] == [cierre.id]


def test_con_ambos_suma_el_monto_del_mecanismo_pagadero(con_revaloracion):
    ambos = replace(
        rz.CLAUSULA,
        mecanismo=Mecanismo.AMBOS,
        mecanismo_pagadero=Mecanismo.COMPROBACION,
        fuente_pagadero="clausula 12 del contrato ficticio",
    )
    _guardar(con_revaloracion, CORTE, clausula=ambos)
    assert reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE).monto == D("75.90")


def test_con_ambos_y_la_escalatoria_pagadera_los_indices_planos_dan_cero(con_revaloracion):
    escalatoria = replace(
        rz.CLAUSULA,
        mecanismo=Mecanismo.AMBOS,
        mecanismo_pagadero=Mecanismo.ESCALATORIA,
        fuente_pagadero="clausula 12 del contrato ficticio",
    )
    _guardar(con_revaloracion, CORTE, clausula=escalatoria)
    assert reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE).monto == 0


def test_un_estudio_en_otra_moneda_no_se_suma_en_silencio_se_declara_omitido(con_revaloracion):
    estudio = _guardar(con_revaloracion, CORTE)
    estudio.moneda = "Bs"  # lo que quedaria tras un cambio de moneda del proyecto
    con_revaloracion.flush()
    reconocido = reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE)
    assert reconocido.monto == 0 and reconocido.estudios == ()
    assert [e.id for e in reconocido.omitidos] == [estudio.id]
```
  El generador determinista (500 partidas, 52 períodos semanales, 26 valuaciones; sin excesos ni solapes; la misma semilla da la misma obra) y la identidad `CV = precio + consumo` sobre su obra:
```python
# tests/unit/test_generar_obra_control.py
"""El generador determinista de la obra grande del control (spec S2 §3.3, RNF-15)."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from core.budget.control import construir_estado
from core.budget.curva import generar_curva
from core.budget.valor_ganado import indicadores, reproyectar, separar_desvio
from core.verification import auditar
from core.verification.valuaciones import InstantaneaDeControl, PartidaBase, reglas_de_control
from scripts import generar_obra_control as generador
from tests.fixtures import control_ob_s2 as ob

D = Decimal


def test_la_misma_semilla_da_la_misma_obra_y_otra_semilla_otra():
    primera = generador.generar(40, 12, 6, semilla=3)
    repetida = generador.generar(40, 12, 6, semilla=3)
    otra = generador.generar(40, 12, 6, semilla=4)
    assert primera.plan == repetida.plan and primera.valuaciones == repetida.valuaciones
    assert primera.presupuesto.total == repetida.presupuesto.total
    assert primera.presupuesto.total != otra.presupuesto.total


def test_el_tamano_de_la_spec_son_500_partidas_52_periodos_y_26_valuaciones_semanales():
    obra = generador.generar()
    assert len(obra.presupuesto.partidas) == 500 and len(obra.plan) == 52
    assert len(obra.valuaciones) == len(obra.costos) == 26
    assert obra.valuaciones[0].desde == generador.INICIO
    assert (
        obra.corte == obra.valuaciones[-1].hasta == generador.INICIO + timedelta(weeks=25, days=4)
    )


def test_el_plan_de_cada_partida_suma_exactamente_uno_y_la_curva_cierra_en_el_total():
    obra = generador.generar(60, 20, 10, semilla=1)
    curva = generar_curva(obra.presupuesto, obra.plan)
    assert curva[-1].acumulado == obra.presupuesto.total


def test_las_valuaciones_son_consecutivas_sin_huecos_ni_solapes_y_sin_excesos():
    obra = generador.generar(80, 20, 10, semilla=2)
    for anterior, siguiente in zip(obra.valuaciones, obra.valuaciones[1:], strict=False):
        assert siguiente.desde == anterior.desde + timedelta(weeks=1)
    partidas = tuple(
        PartidaBase(
            p.item.codigo_partida, p.item.cantidad, p.resultado.costo_directo, p.item.origen_id
        )
        for p in obra.presupuesto.partidas
    )
    instantanea = InstantaneaDeControl(
        obra.corte, generador.INICIO, partidas, obra.valuaciones, lambda a, b: 0
    )
    informe = auditar(obra.presupuesto, reglas_de_control(instantanea))
    graves = [h for h in informe.hallazgos if h.severidad.name == "ERROR"]
    assert graves == []  # R13 y R14 no encuentran errores en lo generado


def test_la_obra_generada_se_puede_controlar_y_reproyectar():
    obra = generador.generar(60, 20, 10, semilla=5)
    instantanea = ob.instantanea(obra.valuaciones, corte=obra.corte, costos=obra.costos)
    instantanea = replace(
        instantanea,
        presupuesto=obra.presupuesto,
        plan=obra.plan,
        linea_base=replace(instantanea.linea_base, calendario=obra.calendario),
    )
    costo = sum((c.monto for c in obra.costos), D(0))
    estado = construir_estado(instantanea, costo_real=costo, precios=obra.precios)
    ind = indicadores(estado)
    reproyeccion = reproyectar(estado)
    assert ind.spi is not None and ind.cpi is not None and ind.eac_sistema is not None
    assert reproyeccion.termino is not None and reproyeccion.termino >= estado.dia
    curva = generar_curva(obra.presupuesto, reproyeccion.plan)
    assert curva[-1].acumulado == obra.presupuesto.total  # el plan reproyectado es valido


def test_la_identidad_cv_igual_precio_mas_consumo_se_cumple_en_la_obra_del_generador():
    obra = generador.generar(partidas=60, periodos=20, valuaciones=10, semilla=7)
    instantanea = ob.instantanea(obra.valuaciones, corte=obra.corte, costos=[])
    instantanea = replace(
        instantanea,
        presupuesto=obra.presupuesto,
        plan=obra.plan,
        linea_base=replace(instantanea.linea_base, calendario=obra.calendario),
        costos=obra.costos,
    )
    costo = sum((c.monto for c in obra.costos), D(0))
    estado = construir_estado(instantanea, costo_real=costo, precios=obra.precios)
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert ind.spi is not None and 0 < ind.spi
    assert sep.precio + sep.consumo == ind.cv
    assert sep.vac_precio + sep.vac_consumo == ind.vac
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/integration/test_control.py tests/integration/test_reajuste_reconocido.py tests/unit/test_generar_obra_control.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'calcular_control' from 'core.budget.control'`
```bash
git add tests/integration/test_control.py tests/integration/test_reajuste_reconocido.py tests/unit/test_generar_obra_control.py
git commit -m "test(core): control al corte, reajuste reconocido y generador de obras en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  `control.py` completo (el cálculo no escribe; `calcular_control` devuelve `ResultadoControl` con la instantánea, el estado, los indicadores, la separación, la reproyección, las alertas y el PE proyectado):
```diff
--- a/core/budget/control.py
+++ b/core/budget/control.py
@@ -12,21 +12,136 @@
 
 from __future__ import annotations
 
+from dataclasses import dataclass, fields
+from datetime import date, datetime
 from decimal import Decimal
 
+from sqlalchemy import select
+from sqlalchemy.orm import Session
+
+from core import models
 from core.budget.calendario import numero_de_dia, periodo_de
+from core.budget.curva import generar_curva
+from core.budget.edicion import CambioEditado, _exigir_respaldo, version_vigente
+from core.budget.equilibrio import PuntoEquilibrio, punto_equilibrio
+from core.budget.persistencia import cargar_presupuesto
+from core.budget.puente import ReajusteReconocido, reajuste_reconocido
 from core.budget.valor_ganado import (
+    PERSPECTIVA_COSTO,
+    Alertas,
     EstadoObra,
+    Indicadores,
+    ParametrosControl,
     PreciosDelCorte,
+    Reproyeccion,
+    Separacion,
+    alertas,
+    equilibrio_proyectado,
+    indicadores,
     partidas_de_plan,
+    reproyectar,
+    separar_desvio,
 )
-from core.budget.valuaciones import InstantaneaControl
+from core.budget.valuaciones import CostoReal, InstantaneaControl, instantanea_control
+from core.catalog import Catalogo
+from core.catalog.indices import LADO_POR_DEFECTO, TasaNoDisponible, tasa_aplicable
+from core.catalog.moneda import convertir
+from core.contracts.apu import ComposicionAPU
+from core.verification.informe import InformeAuditoria
 
 __all__ = [
+    "ResultadoControl",
+    "calcular_control",
     "construir_estado",
+    "composiciones_de_la_linea_base",
+    "costo_real_al_corte",
+    "guardar_parametros",
+    "parametros_de_control",
+    "precios_del_corte_de_version",
 ]
 
 CERO = Decimal(0)
+OBJETO_PARAMETRO = "parametro"
+
+
+@dataclass(frozen=True)
+class ResultadoControl:
+    """Todo lo que la pantalla «Control de obra» muestra al corte (S2 §5.5)."""
+
+    instantanea: InstantaneaControl
+    estado: EstadoObra
+    indicadores: Indicadores
+    separacion: Separacion
+    reproyeccion: Reproyeccion
+    equilibrio_base: PuntoEquilibrio | None
+    equilibrio_proyectado: PuntoEquilibrio | None
+    reajuste: ReajusteReconocido
+    alertas: Alertas
+    informe: InformeAuditoria
+    costos_sin_tasa: tuple[CostoReal, ...]
+    parametros: ParametrosControl
+    venta: Decimal
+    costo_fijo: Decimal
+
+
+def precios_del_corte_de_version(
+    session: Session,
+    proyecto_nombre: str,
+    codigo_version: str,
+    perspectiva: str,
+    catalogo: Catalogo,
+) -> PreciosDelCorte:
+    """Los unitarios del corte por **comprobación directa** (S2 §4.3): los de una versión
+    revalorada por UC-02 (costo directo o precio unitario según la perspectiva). La fuente cita
+    la versión y su lista de precios."""
+    modelo = session.scalars(
+        select(models.Presupuesto)
+        .join(models.Proyecto)
+        .where(
+            models.Proyecto.nombre == proyecto_nombre, models.Presupuesto.codigo == codigo_version
+        )
+    ).one_or_none()
+    if modelo is None:
+        raise KeyError(
+            f"no hay ninguna version {codigo_version!r} en el proyecto {proyecto_nombre!r}"
+        )
+    presupuesto = cargar_presupuesto(session, proyecto_nombre, codigo_version, catalogo)
+    unitarios: dict[str, Decimal] = {}
+    for renglon in presupuesto.partidas:
+        unitarios.setdefault(
+            renglon.item.codigo_partida,
+            renglon.resultado.costo_directo
+            if perspectiva == PERSPECTIVA_COSTO
+            else renglon.resultado.precio_unitario,
+        )
+    fuente = (
+        f"version {codigo_version} del {modelo.fecha.isoformat()} "
+        f"(lista {modelo.lista_precios.nombre})"
+    )
+    return PreciosDelCorte("comprobacion", fuente, unitarios)
+
+
+def costo_real_al_corte(
+    session: Session, instantanea: InstantaneaControl, *, lado: str = LADO_POR_DEFECTO
+) -> tuple[Decimal | None, tuple[CostoReal, ...]]:
+    """El AC de la perspectiva *costo*: los costos reales con fecha menor o igual al corte,
+    convertidos a la moneda del proyecto con `tasa_aplicable(fecha)` (S1). Si alguno no tiene tasa
+    aplicable, el AC es `None` y se devuelven esos costos (S2-R17): ninguno se estima."""
+    total = CERO
+    sin_tasa: list[CostoReal] = []
+    for costo in instantanea.costos:
+        if costo.fecha > instantanea.corte:
+            continue
+        if costo.moneda == instantanea.moneda:
+            total += costo.monto
+            continue
+        try:
+            tasa = tasa_aplicable(session, costo.fecha, lado=lado)
+        except TasaNoDisponible:
+            sin_tasa.append(costo)
+            continue
+        total += convertir(costo.monto, costo.moneda, instantanea.moneda, tasa.valor)
+    return (None if sin_tasa else total), tuple(sin_tasa)
 
 
 def construir_estado(
@@ -71,6 +186,159 @@
     )
 
 
+def calcular_control(
+    session: Session,
+    proyecto_nombre: str,
+    *,
+    catalogo: Catalogo,
+    corte: date | None = None,
+    precios: PreciosDelCorte | None = None,
+    parametros: ParametrosControl | None = None,
+    lado: str = LADO_POR_DEFECTO,
+) -> ResultadoControl:
+    """Indicadores, separación del desvío, reproyección, punto de equilibrio proyectado, alertas e
+    informe de control al `corte` (por defecto el *hasta* de la última valuación). Sin escribir.
+
+    `precios` son los del corte (S1): sin ellos la separación y el EAC quedan «no disponible»."""
+    instantanea = instantanea_control(session, proyecto_nombre, catalogo=catalogo, corte=corte)
+    parametros = parametros or parametros_de_control(session, proyecto_nombre)
+    perspectiva = instantanea.linea_base.perspectiva
+    costo_real, sin_tasa = (None, ())
+    motivo = ""
+    if perspectiva == PERSPECTIVA_COSTO:
+        costo_real, sin_tasa = costo_real_al_corte(session, instantanea, lado=lado)
+        if sin_tasa:
+            motivo = "sin tasa aplicable para: " + "; ".join(
+                f"{c.monto} {c.moneda} del {c.fecha.isoformat()}" for c in sin_tasa
+            )
+    estado = construir_estado(
+        instantanea, costo_real=costo_real, motivo_costo=motivo, precios=precios
+    )
+    calculados = indicadores(estado)
+    separacion = separar_desvio(estado, calculados)
+    reproyeccion = reproyectar(estado)
+    reconocido = reajuste_reconocido(session, proyecto_nombre, instantanea.corte)
+    venta = instantanea.presupuesto.total
+    base = None
+    proyectado = None
+    costo_fijo = CERO
+    if perspectiva == PERSPECTIVA_COSTO:
+        base = punto_equilibrio(instantanea.presupuesto, instantanea.parametros_costo)
+        costo_fijo = base.costo_fijo
+        if calculados.eac_sistema is not None and reproyeccion.termino is not None:
+            proyectado = equilibrio_proyectado(
+                venta=venta,
+                costo_variable=calculados.eac_sistema,
+                costo_fijo=costo_fijo,
+                dias_plan=estado.dias_plan,
+                dias_proyectados=reproyeccion.termino,
+                reajuste_reconocido=reconocido.monto,
+                curva=generar_curva(instantanea.presupuesto, reproyeccion.plan),
+            )
+    return ResultadoControl(
+        instantanea=instantanea,
+        estado=estado,
+        indicadores=calculados,
+        separacion=separacion,
+        reproyeccion=reproyeccion,
+        equilibrio_base=base,
+        equilibrio_proyectado=proyectado,
+        reajuste=reconocido,
+        alertas=alertas(
+            calculados,
+            separacion,
+            reproyeccion,
+            dias_plan=estado.dias_plan,
+            equilibrio_base=base,
+            equilibrio_proyectado=proyectado,
+            parametros=parametros,
+        ),
+        informe=instantanea.informe(),
+        costos_sin_tasa=sin_tasa,
+        parametros=parametros,
+        venta=venta,
+        costo_fijo=costo_fijo,
+    )
+
+
 # ---------------------------------------------------------------------------------------------
 # Parámetros de control (S2 §4.5, §4.6)
 # ---------------------------------------------------------------------------------------------
+
+_CAMPOS = tuple(campo.name for campo in fields(ParametrosControl))
+
+
+def parametros_de_control(session: Session, proyecto_nombre: str) -> ParametrosControl:
+    """Los parámetros del proyecto; sin fila, los valores por defecto (§4.5 y §4.6)."""
+    proyecto = session.scalars(
+        select(models.Proyecto).where(models.Proyecto.nombre == proyecto_nombre)
+    ).one()
+    fila = session.get(models.ParametrosControl, proyecto.id)
+    if fila is None:
+        return ParametrosControl()
+    return ParametrosControl(**{nombre: getattr(fila, nombre) for nombre in _CAMPOS})
+
+
+def guardar_parametros(
+    session: Session,
+    proyecto_nombre: str,
+    parametros: ParametrosControl,
+    *,
+    fuente: str,
+    responsable: str,
+    ahora: datetime | None = None,
+) -> list[CambioEditado]:
+    """Cambia los parámetros de control del proyecto con un `RegistroCambio` (objeto `parametro`)
+    por cada valor que cambió, sobre la versión vigente. Exige fuente y responsable. No confirma.
+    Devuelve los cambios; sin ninguno no escribe nada."""
+    fuente, responsable = _exigir_respaldo(fuente, responsable)
+    proyecto = session.scalars(
+        select(models.Proyecto).where(models.Proyecto.nombre == proyecto_nombre)
+    ).one()
+    vigente = version_vigente(session, proyecto_nombre)
+    if vigente is None:
+        raise ValueError("el proyecto no tiene version guardada: no hay donde registrar el cambio")
+    anterior = parametros_de_control(session, proyecto_nombre)
+    cambios = [
+        CambioEditado(
+            OBJETO_PARAMETRO,
+            f"control|{nombre}",
+            nombre,
+            str(getattr(anterior, nombre)),
+            str(getattr(parametros, nombre)),
+        )
+        for nombre in _CAMPOS
+        if getattr(anterior, nombre) != getattr(parametros, nombre)
+    ]
+    if not cambios:
+        return []
+    fila = session.get(models.ParametrosControl, proyecto.id)
+    if fila is None:
+        fila = models.ParametrosControl(proyecto_id=proyecto.id)
+        session.add(fila)
+    for nombre in _CAMPOS:
+        setattr(fila, nombre, getattr(parametros, nombre))
+    momento = ahora or datetime.now()
+    session.add_all(
+        models.RegistroCambio(
+            proyecto_id=proyecto.id,
+            version_origen_id=vigente.id,
+            version_resultante_id=vigente.id,
+            objeto=cambio.objeto,
+            clave=cambio.clave,
+            campo=cambio.campo,
+            valor_anterior=cambio.valor_anterior,
+            valor_nuevo=cambio.valor_nuevo,
+            fuente=fuente,
+            responsable=responsable,
+            fecha_hora=momento,
+        )
+        for cambio in cambios
+    )
+    session.flush()
+    return cambios
+
+
+def composiciones_de_la_linea_base(resultado: ResultadoControl) -> dict[str, ComposicionAPU]:
+    """Los APU congelados de la línea base por código (SF-E6): `Presupuesto.partidas[i].apu`."""
+    return {p.item.codigo_partida: p.apu for p in resultado.instantanea.presupuesto.partidas}
```
  El reajuste reconocido (`reajuste_reconocido` suma por pareja el estudio más reciente y declara los omitidos, p. ej. en otra moneda):
```diff
--- a/core/budget/puente.py
+++ b/core/budget/puente.py
@@ -20,14 +20,18 @@
 
 from core import models
 from core.budget._modelo import _buscar
+from core.budget.moneda import moneda_del_proyecto
 from core.budget.reajuste import Clausula, Ejecutado, PeriodoDeclarado, guardar_estudio
 from core.budget.valuaciones import EjecutadoDelPeriodo, ejecutado_por_periodo
 from core.catalog.indices import LADO_POR_DEFECTO
 
 __all__ = [
+    "EstudioSumado",
     "PeriodoDelEstudio",
+    "ReajusteReconocido",
     "estudio_con_valuaciones",
     "periodos_declarados",
+    "reajuste_reconocido",
 ]
 
 CERO = Decimal(0)
@@ -140,3 +144,69 @@
     for orden, numero, _ in filas:
         citadas.setdefault(orden, []).append(numero)
     return citadas
+
+
+@dataclass(frozen=True, slots=True)
+class EstudioSumado:
+    """Un estudio de S1 y lo que aporta al reajuste reconocido."""
+
+    id: int
+    version_id: int
+    fecha_calculo: date
+    estado: str
+    monto: Decimal
+    moneda: str
+
+
+@dataclass(frozen=True, slots=True)
+class ReajusteReconocido:
+    """La suma de los montos reconocidos de los estudios guardados hasta el corte (S2-R15).
+    `estudios` son los que suman; `omitidos` son los guardados en otra moneda que la del proyecto,
+    que no se convierten ni se suman en silencio."""
+
+    monto: Decimal
+    moneda: str
+    estudios: tuple[EstudioSumado, ...]
+    omitidos: tuple[EstudioSumado, ...] = ()
+
+
+def reajuste_reconocido(session: Session, proyecto_nombre: str, corte: date) -> ReajusteReconocido:
+    """El reajuste ya reconocido al `corte` (RV-12): los estudios de S1 guardados con fecha de
+    cálculo menor o igual al corte. De un parcial y su reemplazo (`reemplaza_a`), ambos con fecha
+    menor o igual al corte, cuenta solo el más reciente; el reemplazo guardado después del corte
+    no quita al parcial. Sin estudios, 0."""
+    modelo = session.scalars(
+        select(models.Proyecto).where(models.Proyecto.nombre == proyecto_nombre)
+    ).one()
+    moneda = moneda_del_proyecto(session, modelo)
+    filas = list(
+        session.scalars(
+            select(models.EstudioReajuste)
+            .join(
+                models.Presupuesto, models.Presupuesto.id == models.EstudioReajuste.presupuesto_id
+            )
+            .where(
+                models.Presupuesto.proyecto_id == modelo.id,
+                models.EstudioReajuste.fecha_calculo <= corte,
+            )
+            .order_by(models.EstudioReajuste.id)
+        )
+    )
+    reemplazados = {fila.reemplaza_a for fila in filas if fila.reemplaza_a is not None}
+    suman: list[EstudioSumado] = []
+    omitidos: list[EstudioSumado] = []
+    for fila in filas:
+        if fila.id in reemplazados:
+            continue
+        estudio = EstudioSumado(
+            fila.id,
+            fila.presupuesto_id,
+            fila.fecha_calculo,
+            fila.estado,
+            fila.total_reconocido,
+            fila.moneda,
+        )
+        (suman if fila.moneda == moneda else omitidos).append(estudio)
+    return ReajusteReconocido(
+        sum((e.monto for e in suman), CERO), moneda, tuple(suman), tuple(omitidos)
+    )
```
  El generador (RP7-13: llega aquí porque necesita el núcleo de S2-1 y S2-2; su medición es la tarea 14):
```python
# scripts/generar_obra_control.py
"""Generador determinista de una obra grande para el control (spec S2 §3.3, RNF-15).

Produce, con una semilla, una obra de `partidas` partidas, `periodos` períodos semanales de cinco
días hábiles y `valuaciones` valuaciones semanales: cantidades, APU (cuadrilla a jornal, equipo y
material), plan con fracciones exactas (1, 1/2, 1/4 o 1/5), valuaciones consecutivas que avanzan
entre el 70 % y el 110 % de lo planificado, un costo real por valuación y los unitarios del corte.
**Datos ficticios** (NORMAS.md §1). Sirve a `scripts/medir_rnf15.py` y a las pruebas de la
identidad `CV = precio + consumo` y de la pureza del control sobre una obra de tamaño real.

La obra se arma en memoria (`generar`); `sembrar` la guarda en una base (versión, plan, línea base
de control) para medir el camino completo. Mismas entradas, misma obra, byte a byte.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto
from core.budget.curva import PeriodoPlan
from core.budget.valor_ganado import PreciosDelCorte
from core.budget.valuaciones import (
    Calendario,
    CostoReal,
    registrar_costo,
    registrar_linea_base,
    registrar_valuacion,
)
from core.catalog import Catalogo
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import Presupuesto
from core.verification.valuaciones import LineaValuacion, Valuacion

D = Decimal
NOMBRE = "OBRA-GENERADA"
CODIGO = "GEN-001"
INICIO = date(2026, 11, 2)  # lunes
MONEDA = "USD"
PARAMETROS = ParametrosCosto(D("6.00"), D("1.00"), D("0.15"), D("0.10"))
FUENTE = "generador determinista (datos ficticios)"
RESPONSABLE = "Residente Ficticio"
#: Fracciones exactas: el plan de cada partida reparte 1 en tramos iguales de 1, 2, 4 o 5 períodos.
TRAMOS = (1, 2, 4, 5)


@dataclass(frozen=True)
class ObraGenerada:
    """La obra generada, sin base de datos."""

    presupuesto: Presupuesto
    plan: tuple[PeriodoPlan, ...]
    composiciones: dict[str, ComposicionAPU]
    items: list[ItemComputo]
    valuaciones: tuple[Valuacion, ...]
    costos: tuple[CostoReal, ...]
    precios: PreciosDelCorte
    calendario: Calendario
    corte: date


def _codigo(n: int) -> str:
    return f"G-{n:04d}"


def _composicion(rng: random.Random, codigo: str) -> ComposicionAPU:
    obreros = D(rng.randint(2, 6))
    return ComposicionAPU(
        codigo,
        f"Partida generada {codigo}",
        "m3",
        D(rng.choice((5, 10, 20, 40))),
        materiales=(
            LineaMaterial(f"Material {codigo}", "m3", D(1), D(rng.randint(2, 30)) + D("0.50")),
        ),
        equipos=(LineaEquipo(f"Equipo {codigo}", D(1), D(rng.randint(20, 200)), D("0.10")),),
        mano_obra=(LineaManoObra(f"Cuadrilla {codigo}", obreros, D(rng.randint(3, 8))),),
    )


def _plan(rng: random.Random, partidas: int, periodos: int) -> list[PeriodoPlan]:
    """Cada partida reparte 1 en `tramo` períodos consecutivos desde un inicio elegido."""
    reparto: list[list[tuple[str, Decimal]]] = [[] for _ in range(periodos)]
    for n in range(1, partidas + 1):
        tramo = rng.choice(TRAMOS)
        inicio = rng.randint(0, periodos - tramo)
        for k in range(tramo):
            reparto[inicio + k].append((_codigo(n), D(1) / D(tramo)))
    return [(f"Semana {n}", tuple(fila)) for n, fila in enumerate(reparto, start=1)]


def generar(
    partidas: int = 500, periodos: int = 52, valuaciones: int = 26, semilla: int = 0
) -> ObraGenerada:
    """La obra de `partidas` partidas con valuaciones semanales hasta la semana `valuaciones`.

    El corte es el viernes de la última semana valuada. Cada valuación cubre una semana exacta y
    avanza lo planificado de esa semana por un factor entre 0,70 y 1,10 (sin pasar de lo
    presupuestado)."""
    if not 1 <= valuaciones <= periodos:
        raise ValueError("las valuaciones semanales deben caber en el plan")
    rng = random.Random(semilla)
    composiciones = {_codigo(n): _composicion(rng, _codigo(n)) for n in range(1, partidas + 1)}
    cantidades = {codigo: D(rng.randint(50, 500)) for codigo in composiciones}
    items = [
        ItemComputo(
            codigo,
            composicion.descripcion,
            "m3",
            cantidades[codigo],
            f"generador:{codigo}",
            OrigenTipo.MANUAL,
            Dominio.CIVIL,
        )
        for codigo, composicion in composiciones.items()
    ]
    plan = _plan(rng, partidas, periodos)
    resultado = elaborar(
        items, composiciones, PARAMETROS, codigo=CODIGO, fecha=INICIO, moneda=MONEDA, plan=plan
    )
    fracciones = {(codigo, n): f for n, (_, reparto) in enumerate(plan) for codigo, f in reparto}
    ejecutadas: dict[str, Decimal] = {}
    lista: list[Valuacion] = []
    costos: list[CostoReal] = []
    unitario = {
        p.item.codigo_partida: p.resultado.costo_directo for p in resultado.presupuesto.partidas
    }
    for semana in range(valuaciones):
        desde = INICIO + timedelta(weeks=semana)
        hasta = desde + timedelta(days=4)
        lineas = []
        gastado = D(0)
        for codigo in composiciones:
            planificada = fracciones.get((codigo, semana))
            if planificada is None:
                continue
            factor = D(rng.randint(70, 110)) / D(100)
            cantidad = (cantidades[codigo] * planificada * factor).quantize(D("0.01"))
            cantidad = min(cantidad, cantidades[codigo] - ejecutadas.get(codigo, D(0)))
            if cantidad <= 0:
                continue
            ejecutadas[codigo] = ejecutadas.get(codigo, D(0)) + cantidad
            lineas.append(LineaValuacion(codigo, cantidad))
            gastado += cantidad * unitario[codigo]
        lista.append(
            Valuacion(
                id=semana + 1,
                numero=f"V-{semana + 1:02d}",
                desde=desde,
                hasta=hasta,
                fecha=hasta + timedelta(days=3),
                inspector="Ing. Ficticio",
                lineas=tuple(lineas),
            )
        )
        costos.append(
            CostoReal(
                semana + 1,
                (gastado * D(rng.randint(95, 115)) / D(100)).quantize(D("0.01")),
                MONEDA,
                hasta,
                FUENTE,
                RESPONSABLE,
            )
        )
    precios = PreciosDelCorte(
        "comprobacion",
        FUENTE,
        {c: u * (D(100) + D(rng.randint(0, 10))) / D(100) for c, u in unitario.items()},
    )
    return ObraGenerada(
        resultado.presupuesto,
        tuple(plan),
        composiciones,
        items,
        tuple(lista),
        tuple(costos),
        precios,
        Calendario(INICIO, 5),
        lista[-1].hasta,
    )


def sembrar(sesion, obra: ObraGenerada, *, con_valuaciones: bool = True) -> None:
    """Guarda la obra en la base: lista, catálogo, versión con su plan, línea base de control y,
    si `con_valuaciones`, sus valuaciones y costos salvo la última (la que se mide). No confirma."""
    lista = models.ListaPrecios(nombre="Generada USD", moneda=MONEDA, fecha_vigencia=INICIO)
    sesion.add(lista)
    sesion.flush()
    catalogo = Catalogo(sesion)
    for composicion in obra.composiciones.values():
        catalogo.cargar_composicion(composicion, lista, Dominio.CIVIL, INICIO, "generador")
    resultado = elaborar(
        obra.items,
        obra.composiciones,
        PARAMETROS,
        codigo=CODIGO,
        fecha=INICIO,
        moneda=MONEDA,
        plan=list(obra.plan),
    )
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=crear_proyecto(sesion, NOMBRE),
        lista=lista,
        parametros=PARAMETROS,
        plan=list(obra.plan),
    )
    registrar_linea_base(
        sesion, NOMBRE, CODIGO, desde=INICIO, perspectiva="costo", calendario=obra.calendario,
        fuente=FUENTE, responsable=RESPONSABLE,
    )  # fmt: skip
    if con_valuaciones:
        for valuacion in obra.valuaciones[:-1]:
            registrar_valuacion_de(sesion, valuacion)
        for costo in obra.costos[:-1]:
            registrar_costo_de(sesion, costo)


def registrar_valuacion_de(sesion, valuacion: Valuacion):
    """Registra una valuación generada (la que `medir_rnf15` mide es la última)."""
    return registrar_valuacion(
        sesion,
        NOMBRE,
        numero=valuacion.numero,
        desde=valuacion.desde,
        hasta=valuacion.hasta,
        fecha=valuacion.fecha,
        inspector=valuacion.inspector,
        lineas=valuacion.lineas,
        fuente=FUENTE,
        responsable=RESPONSABLE,
    )


def registrar_costo_de(sesion, costo: CostoReal):
    return registrar_costo(
        sesion,
        NOMBRE,
        monto=costo.monto,
        moneda=costo.moneda,
        fecha=costo.fecha,
        fuente=costo.fuente,
        responsable=RESPONSABLE,
    )
```
  `scripts/README.md`, una fila nueva junto a las de las otras mediciones:
```markdown
| `generar_obra_control.py` | obra determinista de control (partidas, plan, línea base y valuaciones por período) para medir RNF‑15 (500 partidas, 52 períodos, 26 valuaciones) | RNF‑15 · Sílice 0.7.0 |
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/integration/test_control.py tests/integration/test_reajuste_reconocido.py tests/unit/test_generar_obra_control.py -v -W error` → 24 pruebas en verde.
Run: `uv run pytest tests/unit tests/integration -q -W error -x` → verde en lo que S2 toca (valuaciones, puente, valor ganado, equilibrio, scripts documentados).
Run: `uv run ruff check core/budget/control.py core/budget/puente.py scripts/generar_obra_control.py tests/integration/test_control.py tests/integration/test_reajuste_reconocido.py tests/unit/test_generar_obra_control.py` y la guardia del núcleo.
- [ ] **Paso 5: Commit**
```bash
git add core/budget/control.py core/budget/puente.py scripts/generar_obra_control.py scripts/README.md
git commit -m "feat(core): control al corte, reajuste reconocido y generador determinista de obras" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS2-2 y foco de revisión de la fase

**Compuerta GS2-2** (se cruza al fusionar `inc/070-s2-2-nucleo`):
1. `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-2 --junit reporte-pruebas.xml` → todas las filas en OK, con C3 sobre los pares de `S2-2` (valor ganado, reproyección, alertas, PE proyectado, control, reajuste reconocido y generador).
2. CI verde en Linux y Windows, `-W error`, cero omitidas; el paso de la meta en `--hasta S2-2`.
3. **TI-001 sigue en 28 586,76 USD, Día 6** (`tests/unit/test_caso_ti001.py` sin editar) y `tests/unit/test_equilibrio_extraido.py` en verde.
4. La identidad `CV = precio + consumo` exacta en OB-S2 y en la obra del generador.
5. `uv run python scripts/guardia_nucleo.py --base origin/main` en 0; `uv run ruff check` sobre los archivos tocados.
6. Aprobación de los encargos y aval del tutor de SL-E5 (fórmulas y separación); compuerta anotada en `docs/bitacora/2026-10-silice-070.md`.

**Foco de revisión de S2-2:**
1. **Un costo en Bs sin tasa aplicable** deja AC «no disponible» y lo que depende de él, y lo declara; nunca usa una tasa vieja en silencio → `tests/integration/test_control.py::test_un_costo_en_bs_sin_tasa_aplicable_deja_el_ac_no_disponible_y_lo_declara` (Tarea 9).
2. **Una partida ejecutada sin precio del corte** deja la separación «no disponible» y el resto funciona → `tests/unit/test_valor_ganado.py::test_una_partida_ejecutada_sin_precio_del_corte_deja_la_separacion_no_disponible` (Tarea 7).
3. **Obra detenida o con SPI cero:** el término es «no proyectable» y AL-3 no se evalúa; la partida detenida da su advertencia → `tests/unit/test_reproyeccion.py::test_un_spi_global_cero_hace_el_termino_no_proyectable` y `tests/unit/test_alertas.py::test_una_partida_detenida_da_su_advertencia_al_6` (Tarea 8).
4. **El PE proyectado no suma un reajuste que nadie reconoció:** sin estudio guardado, `V' = V`; un estudio en otra moneda se declara omitido → `tests/integration/test_reajuste_reconocido.py::test_un_estudio_en_otra_moneda_no_se_suma_en_silencio_se_declara_omitido` (Tarea 9).
5. **La perspectiva *precio* no tiene punto de equilibrio y su consumo es cero por construcción** → `tests/integration/test_control.py::test_la_perspectiva_precio_no_tiene_punto_de_equilibrio_y_el_consumo_es_cero` (Tarea 9).

### Discrepancias encontradas (S2-2)

1. **Nombres de pruebas del spec.** El expediente SL-E5 del spec cita `test_identidad_separacion`, `test_pe_proyectado_coincide_con_sf_e3_segun_plan` y `test_pe_proyectado_dos_escenarios`. *Resuelta:* los nombres reales son `test_la_separacion_del_desvio_de_la_memoria_y_su_identidad_exacta` y `test_la_identidad_cv_igual_precio_mas_consumo_se_cumple_en_la_obra_del_generador` (identidad), `test_una_obra_que_va_segun_el_plan_da_el_pe_de_sf_e3_con_su_misma_ubicacion` (según el plan) y los cuatro `test_aceptar_el_retraso_…`/`test_mas_cuadrillas_…` (dos escenarios por opción).
2. **`equilibrio_proyectado` pura.** El spec la deja recibir el reajuste como dato (§4.7); el código lo hace así y es `ui.control` quien lo arma desde `reajuste_reconocido`. Sin diferencia de comportamiento.
3. **Módulo `control.py` no previsto en §5.2.** *Resuelta (RP7-3):* orquesta la instantánea, el estado y los precios del corte para que `valor_ganado.py` quede puro.
4. **Generador en S2-0.** El spec sugiere el generador junto a la memoria; necesita el núcleo. *Resuelta (RP7-13):* entra en la tarea 9.

---

# S2-3 — Opciones de recuperación y decisión (rama `inc/070-s2-3-nucleo`, SL-E6)

Solo `core/`, `migraciones/`, `tests/` y `docs/`. Sale de `origin/main` con S2-2 fusionada y el aval del tutor de SL-E6.
Al terminar, a pedido, el sistema calcula las cuatro opciones de recuperación con su costo y supuestos; la que se elige
crea una versión nueva del presupuesto (`recuperacion`) con su registro de cambios y su decisión guardada.

### Tarea 10: SL-E6a — opciones de recuperación (funciones puras)

**Rama:** `inc/070-s2-3-nucleo` (solo `core/`, `migraciones/`, `tests/`, `docs/`; sale de `main` con S2-2 fusionada)   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/budget/recuperacion.py`, `tests/unit/test_recuperacion.py`

**Interfaces:**
- Consume: de S2-2: `core.budget.valor_ganado.{PartidaControl, EstadoObra, Reproyeccion, reproyectar, equilibrio_proyectado, techo_de_dias}`, `core.budget.control.contexto_de_recuperacion(resultado, composiciones) -> ContextoRecuperacion` (la función de la tarea 9 que arma el contexto desde `ResultadoControl`), `core.budget.equilibrio.{equilibrio, PuntoEquilibrio}`, `core.budget.curva.{PeriodoPlan, generar_curva}`; de la tarea 2: `tests.fixtures.control_fronteras` (TI-001 a destajo, SIS-001 sin mano de obra), `tests.fixtures.control_ob_s2`.
- Produce:
- `core/budget/recuperacion.py`:
  - `OPCIONES = ('cuadrillas', 'horas_extra', 'paralelo', 'aceptar')`
  - `TITULOS = {'cuadrillas': 'Mas cuadrillas', 'horas_extra': 'Horas extra', 'paralelo': 'Partidas en pa`
  - `HORAS_JORNADA = Decimal(8)`
  - `HORAS_EXTRA_DIA_MAX = Decimal(2)`
  - `HORAS_EXTRA_SEMANA_MAX = Decimal(10)`
  - `HORAS_EXTRA_ANIO_MAX = Decimal(100)`
  - `DIAS_POR_SEMANA = 5`
  - `FUENTE_LOTTT = 'LOTTT G.O. 6.076 Ext. 07-05-2012 (docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt)'`
  - `NATURALEZA_FUENTE = 'FUENTE_VERIFICADA'`
  - `NATURALEZA_DATO = 'DATO_DEL_CONTRATO'`
  - `NATURALEZA_SUPUESTO = 'SUPUESTO_DECLARADO'`
  - `PERMISO_ART_182 = 'permiso de la Inspectoria del Trabajo (LOTTT art. 182) para las horas extra'`
  - `class LimiteLegal`
  - `class Supuesto [nombre: str; valor: str; naturaleza: str; fuente: str]`
  - `class CostoDiario [codigo: str; costo_dia: Decimal; salario: Decimal; rendimiento: Decimal; motivo: str]`
  - `def costo_diario(composicion: ComposicionAPU, parametros: ParametrosCosto) -> CostoDiario`
  - `def eficiencia_de_cuadrillas(cuadrillas: int, eta: Decimal) -> Decimal`
  - `def exigir_horas_extra_legales(horas_por_dia: Decimal, dias_con_extra: int, previas: Decimal) -> None`
  - `class ContextoRecuperacion [estado: EstadoObra; base: Reproyeccion; indicadores: Indicadores; composiciones: Mapping[str, ComposicionAPU]; parametros_costo: ParametrosCosto; parametros: ParametrosControl; presupuesto: Presupuesto; venta: Decimal; costo_fijo: Decimal; reajuste: Decimal; objetivo: int | None; origen_costo_diario: str; horas_previas: Decimal; independientes: frozenset[str]]`
  - `class Opcion [nombre: str; aplica: bool; motivo: str; plan: tuple[PeriodoPlan, ...]; termino: int | None; retraso: int | None; costo_directo_adicional: Decimal; costo_indirecto: Decimal; penalizacion: Decimal; eac: Decimal | None; equilibrio: PuntoEquilibrio | None; detalle: Mapping[str, object]; supuestos: tuple[Supuesto, ...]; requisitos: tuple[str, ...]; requiere_declaracion: bool]`
  - `def opcion_cuadrillas(contexto: ContextoRecuperacion) -> Opcion`
  - `def opcion_horas_extra(contexto: ContextoRecuperacion) -> Opcion`
  - `def opcion_paralelo(contexto: ContextoRecuperacion) -> Opcion`
  - `def opcion_aceptar(contexto: ContextoRecuperacion) -> Opcion`
  - `def opciones(contexto: ContextoRecuperacion) -> tuple[Opcion, ...]`

- [ ] **Paso 0: Expediente SL-E6** escrito y aprobado (tarea 3, encabezado `SL‑E6`) y visto bueno del tutor anotado en `docs/bitacora/2026-10-silice-070.md`. Sin ambos la rama no se abre.
- [ ] **Paso 1: Escribir la prueba que falla**
  Las cuatro opciones de OB-S2 contra la memoria §8 (aceptar el retraso: día 23, 2026-12-02, ΔCD 0,00, CF' 690,00; más cuadrillas: `E(2)` = 1,8 en B y C, día 17, 2026-11-24, ΔCD 120,00, CV' 4 600,00, CF' 510,00; horas extra con `h` = 2: día 21, 2026-11-30, ΔCD 115,3125, CV' 4 595,3125, CF' 630,00; partidas en paralelo: no aplica), los límites de la LOTTT (2 horas por día y 100 al año pasan; 101 se rechaza), la monotonía (más *k* nunca alarga) y las fronteras de otros dominios («no aplica» sin dividir):
```python
# tests/unit/test_recuperacion.py
"""SL-E6: opciones de recuperación (spec S2 §4.6; RF-78).

Las cuatro opciones de OB-S2 con su término, su costo directo adicional, su `CF'` y su `PE'` en los
dos escenarios (memoria `control_ob_s2.md`, §7.1); los límites de la LOTTT; la monotonía en `k`;
«no aplica» tipado, sin dividir, para partidas sin mano de obra a jornal de TI-001 y SIS-001.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from core.budget.control import construir_estado
from core.budget.equilibrio import EstadoEquilibrio
from core.budget.recuperacion import (
    HORAS_EXTRA_ANIO_MAX,
    ContextoRecuperacion,
    LimiteLegal,
    costo_diario,
    eficiencia_de_cuadrillas,
    exigir_horas_extra_legales,
    opcion_aceptar,
    opcion_cuadrillas,
    opcion_horas_extra,
    opcion_paralelo,
    opciones,
)
from core.budget.valor_ganado import (
    ParametrosControl,
    indicadores,
    proyectar_partida,
    reproyectar,
)
from core.contracts.apu import ModalidadManoObra
from tests.fixtures import control_fronteras as fronteras
from tests.fixtures import control_ob_s2 as ob

D = Decimal
MONTOS = D("0.01")
SIN_REAJUSTE = D(0)


def _contexto(
    *, reajuste=SIN_REAJUSTE, valuaciones=None, corte=ob.CORTE, composiciones=None, **extra
):
    instantanea = ob.instantanea(ob.v01_v02() if valuaciones is None else valuaciones, corte=corte)
    estado = construir_estado(instantanea, costo_real=ob.COSTO_REAL, precios=ob.precios_del_corte())
    presupuesto = instantanea.presupuesto
    parametros = extra.pop("parametros", ParametrosControl())
    return ContextoRecuperacion(
        estado=estado,
        base=reproyectar(estado),
        indicadores=indicadores(estado),
        composiciones=composiciones or {p.item.codigo_partida: p.apu for p in presupuesto.partidas},
        parametros_costo=ob.PARAMETROS,
        parametros=parametros,
        presupuesto=presupuesto,
        venta=presupuesto.total,
        costo_fijo=D(600),
        reajuste=reajuste,
        **extra,
    )


def _resumen(opcion):
    return (
        opcion.termino,
        round(opcion.costo_directo_adicional, 4),
        opcion.eac,
        opcion.costo_indirecto,
    )


@pytest.mark.parametrize(
    ("nombre", "termino", "adicional", "cv", "cf"),
    [
        ("aceptar", 23, D(0), D(4480), D(690)),
        ("cuadrillas", 17, D(120), D(4600), D(510)),
        ("horas_extra", 21, D("115.3125"), D("4595.3125"), D(630)),
    ],
)
def test_los_resultados_de_la_memoria_ob_s2(nombre, termino, adicional, cv, cf):
    opcion = {o.nombre: o for o in opciones(_contexto())}[nombre]
    assert opcion.aplica and opcion.termino == termino
    assert abs(opcion.costo_directo_adicional - adicional) <= D("0.0001")
    assert abs(opcion.eac - cv) <= D("0.0001")
    assert opcion.costo_indirecto == cf - 600  # CF' - CF
    assert opcion.retraso == max(0, termino - 20)


def test_los_pe_de_cada_opcion_en_los_dos_escenarios_de_la_memoria():
    sin = {o.nombre: o for o in opciones(_contexto())}
    con = {o.nombre: o for o in opciones(_contexto(reajuste=D("75.90")))}
    esperado = {
        "aceptar": (D("6019.66"), D("5402.91")),
        "cuadrillas": (D("5610.00"), D("4887.68")),
        "horas_extra": (D("6860.09"), D("5985.37")),
    }
    for nombre, (punto_sin, punto_con) in esperado.items():
        assert abs(sin[nombre].equilibrio.punto - punto_sin) <= MONTOS, nombre
        assert abs(con[nombre].equilibrio.punto - punto_con) <= MONTOS, nombre
        assert sin[nombre].equilibrio.estado is EstadoEquilibrio.NO_SE_ALCANZA
    # Con el reajuste reconocido solo «mas cuadrillas» alcanza el equilibrio, y en la semana 4.
    alcanzan = [
        n
        for n, o in con.items()
        if o.equilibrio and o.equilibrio.estado is EstadoEquilibrio.CALCULADO
    ]
    assert alcanzan == ["cuadrillas"]
    assert con["cuadrillas"].equilibrio.periodo.startswith("Semana 4")
    assert abs(con["cuadrillas"].equilibrio.porcentaje - D("95.17")) <= MONTOS


def test_partidas_en_paralelo_no_aplica_si_ninguna_empieza_despues_del_periodo_siguiente():
    paralelo = opcion_paralelo(_contexto())
    assert not paralelo.aplica and "ninguna partida sin empezar" in paralelo.motivo


def test_mas_cuadrillas_usa_k_2_con_e_igual_a_1_8_en_b_y_c():
    opcion = opcion_cuadrillas(_contexto())
    assert opcion.detalle["partidas"]["OB-B"]["k"] == 2
    assert opcion.detalle["partidas"]["OB-C"]["k"] == 2
    assert opcion.detalle["partidas"]["OB-B"]["eficiencia"] == "1.80"
    assert "OB-A" not in opcion.detalle["partidas"]  # A termina en 11,11: no determina el termino
    assert dict(opcion.plan[2][1]) == {"OB-A": D("0.1"), "OB-B": D("0.54"), "OB-C": D("0.72")}


def test_cada_opcion_lista_sus_supuestos_con_su_naturaleza():
    por_opcion = {o.nombre: o for o in opciones(_contexto())}
    cuadrillas = {s.nombre: s for s in por_opcion["cuadrillas"].supuestos}
    assert cuadrillas["eta de cuadrillas"].naturaleza == "SUPUESTO_DECLARADO"
    assert cuadrillas["eta de cuadrillas"].valor == "0.80"
    assert "Lee (2022)" in cuadrillas["eta de cuadrillas"].fuente
    assert cuadrillas["penalizacion diaria"].naturaleza == "DATO_DEL_CONTRATO"
    horas = {s.nombre: s for s in por_opcion["horas_extra"].supuestos}
    assert (
        horas["recargo"].naturaleza == "FUENTE_VERIFICADA" and "art. 118" in horas["recargo"].fuente
    )
    assert horas["limites de horas extra"].fuente == "LOTTT art. 178"
    assert any("art. 182" in requisito for requisito in por_opcion["horas_extra"].requisitos)


def test_aceptar_el_retraso_suma_la_penalizacion_del_contrato_por_dia_de_retraso():
    contexto = _contexto(parametros=ParametrosControl(penalizacion_diaria=D(100)))
    assert opcion_aceptar(contexto).penalizacion == D(300)  # 3 dias sobre el dia 20
    assert opcion_cuadrillas(contexto).penalizacion == 0  # llega antes del plan base


def test_el_termino_objetivo_declarado_cambia_que_partidas_lo_determinan():
    sin_objetivo = opcion_cuadrillas(_contexto())
    amplio = opcion_cuadrillas(_contexto(objetivo=25))
    assert sin_objetivo.aplica and not amplio.aplica
    assert "ninguna partida pasa del objetivo" in amplio.motivo
    estricto = opcion_cuadrillas(_contexto(objetivo=10))
    assert estricto.aplica and estricto.retraso > 0  # ni k_max alcanza: devuelve lo que queda (4a)
    assert estricto.detalle["partidas"]["OB-B"]["k"] == 3


def test_un_fin_igual_al_objetivo_cuenta_como_recuperado():
    """Antes de empezar (indice 1) A termina exacto en el dia 10: con objetivo 10 no determina."""
    contexto = _contexto(valuaciones=[], corte=date(2026, 11, 1), objetivo=10)
    assert contexto.base.de("OB-A").fin == D(10)
    assert set(opcion_cuadrillas(contexto).detalle["partidas"]) == {"OB-B", "OB-C"}
    contexto_9 = _contexto(valuaciones=[], corte=date(2026, 11, 1), objetivo=9)
    assert set(opcion_cuadrillas(contexto_9).detalle["partidas"]) == {"OB-A", "OB-B", "OB-C"}


def test_mas_cuadrillas_nunca_alargan_el_termino_de_una_partida():
    contexto = _contexto()
    fines = [
        proyectar_partida(
            contexto.estado,
            "OB-B",
            multiplicador=eficiencia_de_cuadrillas(k, D("0.80")),
            spi_global=contexto.indicadores.spi,
        ).fin
        for k in range(1, 6)
    ]
    assert fines == sorted(fines, reverse=True) and len(set(fines)) == 5  # estrictamente menor
    assert eficiencia_de_cuadrillas(1, D("0.80")) == 1
    assert eficiencia_de_cuadrillas(3, D("0.80")) == D("2.44")


@pytest.mark.parametrize("horas", [D("2.2"), D(3)])
def test_las_horas_extra_por_dia_sobre_el_limite_se_rechazan(horas):
    with pytest.raises(LimiteLegal):
        opcion_horas_extra(_contexto(parametros=ParametrosControl(horas_extra_dia=horas)))
    with pytest.raises(LimiteLegal, match="negativas"):
        exigir_horas_extra_legales(D("-1"), 0, D(0))


def test_dos_horas_por_dia_son_el_limite_y_pasan_y_se_citan_los_articulos():
    exigir_horas_extra_legales(D(2), 0, D(0))  # 10 h extra en la semana de cinco dias: pasa
    with pytest.raises(LimiteLegal, match="art. 178"):
        exigir_horas_extra_legales(D("2.2"), 0, D(0))  # 11 h por semana
    assert opcion_horas_extra(_contexto()).aplica


def test_cien_horas_extra_en_el_anio_pasan_y_ciento_una_se_rechazan():
    # B termina en el dia 20 y C en el 21: C trabaja 11 dias con 2 h extra = 22 h.
    pasa = opcion_horas_extra(_contexto(horas_previas=HORAS_EXTRA_ANIO_MAX - 22))
    assert pasa.aplica
    assert pasa.detalle["partidas"]["OB-C"]["horas_extra_del_obrero"] == "22"
    falla = opcion_horas_extra(_contexto(horas_previas=HORAS_EXTRA_ANIO_MAX - 21))
    assert not falla.aplica and "101" in falla.motivo and "art. 178" in falla.motivo
    exigir_horas_extra_legales(D(1), 100, D(0))
    with pytest.raises(LimiteLegal, match="101"):
        exigir_horas_extra_legales(D(1), 101, D(0))


def test_las_horas_extra_de_la_memoria_ninguna_supera_los_limites():
    opcion = opcion_horas_extra(_contexto())
    for datos in opcion.detalle["partidas"].values():
        assert D(datos["horas_extra_del_obrero"]) <= HORAS_EXTRA_ANIO_MAX


def test_fcas_en_horas_extra_es_un_parametro_que_cambia_el_costo():
    con = opcion_horas_extra(_contexto())
    sin = opcion_horas_extra(_contexto(parametros=ParametrosControl(fcas_en_horas_extra=False)))
    assert sin.costo_directo_adicional < con.costo_directo_adicional


def test_una_partida_de_ti_001_a_destajo_no_aplica_en_cuadrillas_ni_horas_extra():
    costo = costo_diario(fronteras.ti001_a_destajo(), fronteras.caso_ti001.PARAMETROS)
    assert (costo.aplica, costo.motivo, costo.salario) == (False, "sin mano de obra a jornal", 0)
    assert fronteras.ti001_a_destajo().mano_obra[0].modalidad is ModalidadManoObra.DESTAJO


def test_una_partida_de_sis_001_sin_mano_de_obra_no_aplica_sin_dividir():
    costo = costo_diario(fronteras.sis001_sin_mano_de_obra(), fronteras.sis.PARAMETROS_SISTEMAS)
    assert (costo.aplica, costo.motivo) == (False, "sin mano de obra a jornal")


def test_si_las_partidas_que_determinan_el_termino_no_tienen_jornal_la_opcion_no_aplica():
    ti, sis = fronteras.ti001_a_destajo(), fronteras.sis001_sin_mano_de_obra()
    base = {p.item.codigo_partida: p.apu for p in ob.elaborar_ob_s2().presupuesto.partidas}
    # OB-B y OB-C, las que determinan el termino, toman las variantes de otros dominios.
    cambiadas = {
        **base,
        "OB-B": replace(ti, codigo_partida="OB-B"),
        "OB-C": replace(sis, codigo_partida="OB-C"),
    }
    contexto = _contexto(composiciones=cambiadas)
    for opcion in (opcion_cuadrillas(contexto), opcion_horas_extra(contexto)):
        assert not opcion.aplica
        assert "OB-B: sin mano de obra a jornal" in opcion.motivo
        assert "OB-C: sin mano de obra a jornal" in opcion.motivo
    # «Aceptar el retraso» no depende de la cuadrilla y se calcula igual.
    assert opcion_aceptar(contexto).aplica and opcion_aceptar(contexto).termino == 23


def test_si_solo_una_partida_no_tiene_jornal_la_otra_se_calcula_y_la_primera_se_declara():
    base = {p.item.codigo_partida: p.apu for p in ob.elaborar_ob_s2().presupuesto.partidas}
    cambiadas = {**base, "OB-B": replace(fronteras.ti001_a_destajo(), codigo_partida="OB-B")}
    opcion = opcion_cuadrillas(_contexto(composiciones=cambiadas))
    assert opcion.aplica
    assert set(opcion.detalle["partidas"]) == {"OB-C"}
    assert opcion.detalle["sin_cuadrilla"] == {"OB-B": "sin mano de obra a jornal"}


def test_el_costo_diario_de_los_apu_de_ob_s2_es_el_de_la_memoria():
    apus = {p.item.codigo_partida: p.apu for p in ob.elaborar_ob_s2().presupuesto.partidas}
    esperados = {"OB-A": (100, 12, 10), "OB-B": (40, 5, 20), "OB-C": (80, 10, 10)}
    for codigo, (cd, s, r) in esperados.items():
        costo = costo_diario(apus[codigo], ob.PARAMETROS)
        assert (costo.costo_dia, costo.salario, costo.rendimiento) == (D(cd), D(s), D(r))


def test_partidas_en_paralelo_cuando_una_partida_empieza_mas_tarde_se_adelanta():
    contexto = _contexto()
    estado = contexto.estado
    atrasada = replace(
        estado,
        partidas=tuple(
            replace(p, plan=(D(0), D(0), D(0), D(0), D("0.5"), D("0.5")))
            if p.codigo == "OB-C"
            else p
            for p in estado.partidas
        ),
        etiquetas=(*estado.etiquetas, "Semana 5", "Semana 6"),
    )
    contexto = replace(contexto, estado=atrasada, base=reproyectar(atrasada))
    opcion = opcion_paralelo(contexto)
    assert opcion.aplica and opcion.requiere_declaracion
    assert opcion.detalle["adelantadas"] == ["OB-C"]
    assert opcion.detalle["partidas_simultaneas_maximas"] == 3
    assert opcion.costo_directo_adicional == 0
    assert opcion.termino < contexto.base.termino
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_recuperacion.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.budget.recuperacion'`
```bash
git add tests/unit/test_recuperacion.py
git commit -m "test(core): opciones de recuperacion de OB-S2 y sus limites en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  Todo el cálculo es puro (sin `sqlalchemy`, sin `core.models`, sin `core.catalog`; lo vigila `tests/unit/test_arquitectura_s2.py` en la tarea 12). El costo sale del rendimiento y la cuadrilla del APU de cada partida; una partida sin jornal da «no aplica» antes de dividir; cada resultado lista sus supuestos con su naturaleza (RP7-5: `h = horas_extra_dia`, por defecto 2, en todas las partidas determinantes; el límite anual usa `horas_previas`; RP7-10: el paralelo se calcula siempre y su declaración se exige al elegirlo):
```python
# core/budget/recuperacion.py
"""SL-E6: opciones de recuperación de un retraso (spec S2 §4.6). Funciones **puras**, sin base de
datos ni `sqlalchemy`; la decisión que crea la versión vive en `core.budget.decision`.

Cuatro opciones, cada una calculada sola (sin combinar) desde el rendimiento y la cuadrilla del APU
de cada partida y un factor de eficiencia declarado por rendimientos decrecientes (horizonte §4;
Lee, 2022 es la base del método, **no** de las cifras):

* **más cuadrillas**: con `k` cuadrillas iguales a la del APU el ritmo se multiplica por
  `E(k) = Σ η^(j-1)`, `η = 0,80`, `k` hasta `cuadrillas_max = 3`;
* **horas extra**: `h` horas por día dentro de los límites verificados de la LOTTT (arts. 118, 173,
  178 y 182), con ritmo `1 + (h/8)·η_he`;
* **partidas en paralelo**: partidas sin empezar se adelantan al período siguiente al corte; exige
  la declaración del usuario de que no dependen de las que están en curso (S2-R4);
* **aceptar el retraso**: el plan reproyectado, con su costo indirecto y la penalización del
  contrato.

Una partida sin mano de obra a jornal (solo destajo o sin mano de obra) no tiene cuadrilla que
escalar: «más cuadrillas» y «horas extra» devuelven «no aplica» para ella **antes** de dividir. Los
supuestos de cada resultado se listan con su naturaleza.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from core.budget.curva import PeriodoPlan, generar_curva
from core.budget.equilibrio import PuntoEquilibrio
from core.budget.valor_ganado import (
    CERO,
    PERSPECTIVA_COSTO,
    UNO,
    EstadoObra,
    Indicadores,
    ParametrosControl,
    Reproyeccion,
    equilibrio_proyectado,
    fin_excede,
    proyectar_partida,
    reproyectar,
    techo_de_dias,
)
from core.contracts.apu import ComposicionAPU, ModalidadManoObra, ParametrosCosto
from core.contracts.presupuesto import Presupuesto

__all__ = [
    "HORAS_EXTRA_ANIO_MAX",
    "HORAS_EXTRA_DIA_MAX",
    "HORAS_EXTRA_SEMANA_MAX",
    "HORAS_JORNADA",
    "OPCIONES",
    "ContextoRecuperacion",
    "CostoDiario",
    "LimiteLegal",
    "Opcion",
    "Supuesto",
    "costo_diario",
    "eficiencia_de_cuadrillas",
    "exigir_horas_extra_legales",
    "opcion_aceptar",
    "opcion_cuadrillas",
    "opcion_horas_extra",
    "opcion_paralelo",
    "opciones",
]

OPCIONES = ("cuadrillas", "horas_extra", "paralelo", "aceptar")
TITULOS = {
    "cuadrillas": "Mas cuadrillas",
    "horas_extra": "Horas extra",
    "paralelo": "Partidas en paralelo",
    "aceptar": "Aceptar el retraso",
}
#: Límites de la LOTTT (G.O. 6.076 Ext., 07-05-2012), verificados en la copia del repositorio.
HORAS_JORNADA = Decimal(8)  # art. 173: jornada diurna
HORAS_EXTRA_DIA_MAX = Decimal(2)  # art. 178: duración efectiva con extras <= 10 h diarias
HORAS_EXTRA_SEMANA_MAX = Decimal(10)  # art. 178
HORAS_EXTRA_ANIO_MAX = Decimal(100)  # art. 178
DIAS_POR_SEMANA = 5  # art. 173: cinco días a la semana
FUENTE_LOTTT = "LOTTT G.O. 6.076 Ext. 07-05-2012 (docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt)"
NATURALEZA_FUENTE = "FUENTE_VERIFICADA"
NATURALEZA_DATO = "DATO_DEL_CONTRATO"
NATURALEZA_SUPUESTO = "SUPUESTO_DECLARADO"
PERMISO_ART_182 = "permiso de la Inspectoria del Trabajo (LOTTT art. 182) para las horas extra"


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


class LimiteLegal(ValueError):  # noqa: N818
    """Una opción de horas extra que supera un límite de la LOTTT."""


@dataclass(frozen=True, slots=True)
class Supuesto:
    """Un dato con que se calculó una opción, con su naturaleza (fuente o supuesto declarado)."""

    nombre: str
    valor: str
    naturaleza: str
    fuente: str = ""


@dataclass(frozen=True, slots=True)
class CostoDiario:
    """El componente dependiente del tiempo del APU (§4.6): `costo_dia = C_d` (cuadrilla a jornal
    con FCAS y bono, más equipos), `salario = S` (jornales sin FCAS) y `rendimiento = R`. Si la
    partida no tiene mano de obra a jornal o no tiene rendimiento, `motivo` dice por qué «no
    aplica»."""

    codigo: str
    costo_dia: Decimal
    salario: Decimal
    rendimiento: Decimal
    motivo: str = ""

    @property
    def aplica(self) -> bool:
        return not self.motivo


def costo_diario(composicion: ComposicionAPU, parametros: ParametrosCosto) -> CostoDiario:
    """`C_d = Σ_jornal cantidad·sueldo·(1 + FCAS) + bono·obreros_a_jornal + Σ cantidad·precio·dep`;
    `S = Σ_jornal cantidad·sueldo`. Las líneas a destajo se pagan por unidad y los materiales no
    dependen del tiempo: ninguna opción los cambia."""
    jornal = [m for m in composicion.mano_obra if m.modalidad is ModalidadManoObra.JORNAL]
    salario = sum((m.cantidad * m.sueldo for m in jornal), CERO)
    equipos = sum((e.cantidad * e.precio * e.depreciacion for e in composicion.equipos), CERO)
    costo_dia = (
        salario * (UNO + parametros.fcas) + parametros.bono_alimentacion * composicion.total_obreros
    ) + equipos
    motivo = ""
    if composicion.rendimiento <= CERO:
        motivo = "sin rendimiento"
    elif salario == CERO:
        motivo = "sin mano de obra a jornal"
    return CostoDiario(
        composicion.codigo_partida, costo_dia, salario, composicion.rendimiento, motivo
    )


def eficiencia_de_cuadrillas(cuadrillas: int, eta: Decimal) -> Decimal:
    """`E(k) = Σ_{j=1..k} η^(j-1)`: lo que rinden `k` cuadrillas respecto de una (§4.6.1)."""
    with _contexto():
        return sum((eta ** (j - 1) for j in range(1, cuadrillas + 1)), CERO)


def exigir_horas_extra_legales(
    horas_por_dia: Decimal, dias_con_extra: int, previas: Decimal
) -> None:
    """`LimiteLegal` si `h` horas extra por día durante `dias_con_extra` días llevan a un obrero
    más allá de 2 h por día (10 h de duración efectiva, art. 178), 10 h extra por semana o 100 h
    extra por año (con las `previas` del año). El límite exacto pasa."""
    if horas_por_dia < CERO:
        raise LimiteLegal(f"las horas extra por dia no pueden ser negativas: {horas_por_dia}")
    if horas_por_dia > HORAS_EXTRA_DIA_MAX:
        raise LimiteLegal(
            f"{horas_por_dia} h extra por dia superan las {HORAS_EXTRA_DIA_MAX} h que dejan la "
            f"duracion efectiva en 10 h (LOTTT art. 178; {FUENTE_LOTTT})"
        )
    if horas_por_dia * DIAS_POR_SEMANA > HORAS_EXTRA_SEMANA_MAX:
        raise LimiteLegal(
            f"{horas_por_dia} h extra por dia son {horas_por_dia * DIAS_POR_SEMANA} h por semana, "
            f"mas de las {HORAS_EXTRA_SEMANA_MAX} h del art. 178"
        )
    anuales = previas + horas_por_dia * dias_con_extra
    if anuales > HORAS_EXTRA_ANIO_MAX:
        raise LimiteLegal(
            f"un obrero llegaria a {anuales} h extra en el año, mas de las "
            f"{HORAS_EXTRA_ANIO_MAX} h del art. 178"
        )


@dataclass(frozen=True)
class ContextoRecuperacion:
    """Todo lo que las opciones necesitan: el estado al corte, la reproyección base, los
    indicadores, los APU de la línea base (o los revalorados, `origen_costo_diario`), los
    parámetros y los montos del punto de equilibrio. `objetivo` es el término objetivo en días
    hábiles (por defecto el fin del plan base). `horas_previas` son las horas extra que el obrero
    ya acumula en el año (dato declarado, por defecto 0)."""

    estado: EstadoObra
    base: Reproyeccion
    indicadores: Indicadores
    composiciones: Mapping[str, ComposicionAPU]
    parametros_costo: ParametrosCosto
    parametros: ParametrosControl
    presupuesto: Presupuesto
    venta: Decimal
    costo_fijo: Decimal
    reajuste: Decimal = CERO
    objetivo: int | None = None
    origen_costo_diario: str = "composiciones de la linea base"
    horas_previas: Decimal = CERO
    independientes: frozenset[str] = field(default_factory=frozenset)

    @property
    def meta(self) -> int:
        return self.estado.dias_plan if self.objetivo is None else self.objetivo


@dataclass(frozen=True)
class Opcion:
    """El resultado de una opción (§4.6). `eac` es el costo directo final proyectado de la opción
    (`CV'` del punto de equilibrio); `costo_indirecto = CF' - CF`; `retraso` son los días hábiles
    que quedan sobre el objetivo; `detalle` es serializable a JSON (textos y números)."""

    nombre: str
    aplica: bool
    motivo: str
    plan: tuple[PeriodoPlan, ...] = ()
    termino: int | None = None
    retraso: int | None = None
    costo_directo_adicional: Decimal = CERO
    costo_indirecto: Decimal = CERO
    penalizacion: Decimal = CERO
    eac: Decimal | None = None
    equilibrio: PuntoEquilibrio | None = None
    detalle: Mapping[str, object] = field(default_factory=dict)
    supuestos: tuple[Supuesto, ...] = ()
    requisitos: tuple[str, ...] = ()
    requiere_declaracion: bool = False

    @property
    def titulo(self) -> str:
        return TITULOS[self.nombre]


def _no_aplica(nombre: str, motivo: str, supuestos: tuple[Supuesto, ...] = ()) -> Opcion:
    return Opcion(nombre, False, motivo, supuestos=supuestos)


def _supuestos_comunes(contexto: ContextoRecuperacion) -> tuple[Supuesto, ...]:
    parametros = contexto.parametros
    return (
        Supuesto(
            "penalizacion diaria",
            str(parametros.penalizacion_diaria),
            NATURALEZA_DATO,
            parametros.fuente_penalizacion or "sin fuente: ninguna norma verificada la fija",
        ),
        Supuesto("costo diario de la cuadrilla", contexto.origen_costo_diario, NATURALEZA_SUPUESTO),
        Supuesto("costo fijo en el tiempo", "CF' = CF · D'/D", NATURALEZA_SUPUESTO),
    )


def _cerrar(
    contexto: ContextoRecuperacion,
    nombre: str,
    reproyeccion: Reproyeccion,
    adicional: Decimal,
    supuestos: tuple[Supuesto, ...],
    detalle: Mapping[str, object],
    *,
    requisitos: tuple[str, ...] = (),
    requiere_declaracion: bool = False,
) -> Opcion:
    """Completa una opción con su término, sus costos indirectos y su punto de equilibrio."""
    termino = reproyeccion.termino
    if termino is None:
        return _no_aplica(nombre, reproyeccion.motivo_termino, supuestos)
    retraso = max(0, termino - contexto.meta)
    with _contexto():
        fijo = contexto.costo_fijo * termino / contexto.estado.dias_plan
        indirecto = fijo - contexto.costo_fijo
        penalizacion = contexto.parametros.penalizacion_diaria * retraso
    eac = None
    punto = None
    if contexto.indicadores.eac_sistema is not None:
        eac = contexto.indicadores.eac_sistema + adicional
        if contexto.estado.perspectiva == PERSPECTIVA_COSTO:
            punto = equilibrio_proyectado(
                venta=contexto.venta,
                costo_variable=eac,
                costo_fijo=contexto.costo_fijo,
                dias_plan=contexto.estado.dias_plan,
                dias_proyectados=termino,
                reajuste_reconocido=contexto.reajuste,
                curva=generar_curva(contexto.presupuesto, reproyeccion.plan),
            )
    return Opcion(
        nombre,
        True,
        "",
        reproyeccion.plan,
        termino,
        retraso,
        adicional,
        indirecto,
        penalizacion,
        eac,
        punto,
        detalle,
        (*supuestos, *_supuestos_comunes(contexto)),
        requisitos,
        requiere_declaracion,
    )


def _determinantes(contexto: ContextoRecuperacion) -> list[str]:
    """Las partidas que determinan el término: las de `fin > objetivo` en la reproyección base."""
    return [
        p.codigo
        for p in contexto.base.partidas
        if p.fin is not None and fin_excede(p.fin, contexto.meta)
    ]


def _cantidad_restante(contexto: ContextoRecuperacion, codigo: str) -> Decimal:
    partida = next(p for p in contexto.estado.partidas if p.codigo == codigo)
    return partida.cantidad - contexto.estado.cantidad_ejecutada(partida)


def _costos_diarios(
    contexto: ContextoRecuperacion, codigos: list[str]
) -> tuple[dict[str, CostoDiario], dict[str, str]]:
    aplican: dict[str, CostoDiario] = {}
    no_aplican: dict[str, str] = {}
    for codigo in codigos:
        composicion = contexto.composiciones.get(codigo)
        if composicion is None:
            no_aplican[codigo] = "sin composicion de APU"
            continue
        costo = costo_diario(composicion, contexto.parametros_costo)
        if costo.aplica:
            aplican[codigo] = costo
        else:
            no_aplican[codigo] = costo.motivo
    return aplican, no_aplican


# ---------------------------------------------------------------------------------------------
# Más cuadrillas
# ---------------------------------------------------------------------------------------------


def opcion_cuadrillas(contexto: ContextoRecuperacion) -> Opcion:
    """Más cuadrillas (§4.6.1). Para cada partida que determina el término, el menor `k` en
    `2 .. cuadrillas_max` con `fin <= objetivo` (o `cuadrillas_max` si ninguno alcanza); costo
    adicional `ΔCD = q_rest · C_d · (k - E(k)) / (R · E(k))`."""
    parametros = contexto.parametros
    supuestos = (
        Supuesto(
            "eta de cuadrillas",
            str(parametros.eta_cuadrilla),
            NATURALEZA_SUPUESTO,
            "Lee (2022) es la base del metodo, no del valor",
        ),
        Supuesto("cuadrillas maximas", str(parametros.cuadrillas_max), NATURALEZA_SUPUESTO),
    )
    determinantes = _determinantes(contexto)
    if not determinantes:
        return _no_aplica("cuadrillas", "ninguna partida pasa del objetivo", supuestos)
    aplican, no_aplican = _costos_diarios(contexto, determinantes)
    if not aplican:
        motivos = "; ".join(f"{c}: {m}" for c, m in no_aplican.items())
        return _no_aplica("cuadrillas", f"no aplica ({motivos})", supuestos)
    multiplicadores: dict[str, Decimal] = {}
    elegidas: dict[str, object] = {}
    adicional = CERO
    for codigo, costo in aplican.items():
        elegido = parametros.cuadrillas_max
        for k in range(2, parametros.cuadrillas_max + 1):
            eficiencia = eficiencia_de_cuadrillas(k, parametros.eta_cuadrilla)
            fin = proyectar_partida(
                contexto.estado,
                codigo,
                multiplicador=eficiencia,
                spi_global=contexto.indicadores.spi,
            ).fin
            if fin is not None and not fin_excede(fin, contexto.meta):
                elegido = k
                break
        eficiencia = eficiencia_de_cuadrillas(elegido, parametros.eta_cuadrilla)
        multiplicadores[codigo] = eficiencia
        with _contexto():
            delta = (
                _cantidad_restante(contexto, codigo)
                * costo.costo_dia
                * (elegido - eficiencia)
                / (costo.rendimiento * eficiencia)
            )
        adicional += delta
        elegidas[codigo] = {"k": elegido, "eficiencia": str(eficiencia), "adicional": str(delta)}
    reproyeccion = reproyectar(contexto.estado, multiplicador=multiplicadores)
    return _cerrar(
        contexto,
        "cuadrillas",
        reproyeccion,
        adicional,
        supuestos,
        {"partidas": elegidas, "sin_cuadrilla": no_aplican},
    )


# ---------------------------------------------------------------------------------------------
# Horas extra
# ---------------------------------------------------------------------------------------------


def opcion_horas_extra(contexto: ContextoRecuperacion) -> Opcion:
    """Horas extra (§4.6.2): `h = horas_extra_dia` en cada partida que determina el término, con
    ritmo `r · (1 + (h/8)·η_he)` y costo de un día de cuadrilla `C_d + OT`,
    `OT = (h/8)(1 + recargo)·S·(1 + FCAS·a)`; `ΔCD = q_rest · (C_d + OT - C_d·m) / (R·m)`, con
    `m = 1 + h·η_he/8`. `ValueError` (`LimiteLegal`) si `h` supera los límites diarios o semanales;
    la opción no aplica si un obrero pasaría de 100 h extra en el año."""
    parametros = contexto.parametros
    horas = parametros.horas_extra_dia
    exigir_horas_extra_legales(horas, 0, CERO)
    supuestos = (
        Supuesto("horas extra por dia", str(horas), NATURALEZA_SUPUESTO, "tope legal 2 h"),
        Supuesto("eta de horas extra", str(parametros.eta_horas_extra), NATURALEZA_SUPUESTO),
        Supuesto(
            "recargo",
            str(parametros.recargo_horas_extra),
            NATURALEZA_FUENTE,
            "LOTTT art. 118: por lo menos 50 %",
        ),
        Supuesto(
            "FCAS sobre las horas extra",
            "si" if parametros.fcas_en_horas_extra else "no",
            NATURALEZA_SUPUESTO,
            "interpretacion de los arts. 104 y 178; decide el tutor",
        ),
        Supuesto("jornada ordinaria", f"{HORAS_JORNADA} h", NATURALEZA_FUENTE, "LOTTT art. 173"),
        Supuesto(
            "limites de horas extra",
            "10 h por semana, 100 h por año",
            NATURALEZA_FUENTE,
            "LOTTT art. 178",
        ),
    )
    determinantes = _determinantes(contexto)
    if not determinantes:
        return _no_aplica("horas_extra", "ninguna partida pasa del objetivo", supuestos)
    aplican, no_aplican = _costos_diarios(contexto, determinantes)
    if not aplican:
        motivos = "; ".join(f"{c}: {m}" for c, m in no_aplican.items())
        return _no_aplica("horas_extra", f"no aplica ({motivos})", supuestos)
    with _contexto():
        multiplicador = UNO + horas * parametros.eta_horas_extra / HORAS_JORNADA
        incluye_fcas = parametros.fcas_en_horas_extra
        factor_fcas = UNO + (contexto.parametros_costo.fcas if incluye_fcas else CERO)
    reproyeccion = reproyectar(contexto.estado, multiplicador=dict.fromkeys(aplican, multiplicador))
    adicional = CERO
    por_partida: dict[str, object] = {}
    peor = 0
    for codigo, costo in aplican.items():
        with _contexto():
            extra = (
                horas
                / HORAS_JORNADA
                * (UNO + parametros.recargo_horas_extra)
                * costo.salario
                * factor_fcas
            )
            delta = (
                _cantidad_restante(contexto, codigo)
                * (costo.costo_dia + extra - costo.costo_dia * multiplicador)
                / (costo.rendimiento * multiplicador)
            )
        fin = reproyeccion.de(codigo).fin
        dias = max(0, techo_de_dias(fin) - contexto.estado.dia) if fin is not None else 0
        peor = max(peor, dias)
        adicional += delta
        por_partida[codigo] = {
            "dias": dias,
            "horas_extra_del_obrero": str(horas * dias),
            "adicional": str(delta),
        }
    try:
        exigir_horas_extra_legales(horas, peor, contexto.horas_previas)
    except LimiteLegal as error:
        return _no_aplica("horas_extra", str(error), supuestos)
    return _cerrar(
        contexto,
        "horas_extra",
        reproyeccion,
        adicional,
        supuestos,
        {"partidas": por_partida, "sin_cuadrilla": no_aplican, "horas_por_dia": str(horas)},
        requisitos=(PERMISO_ART_182,),
    )


# ---------------------------------------------------------------------------------------------
# Partidas en paralelo y aceptar el retraso
# ---------------------------------------------------------------------------------------------


def opcion_paralelo(contexto: ContextoRecuperacion) -> Opcion:
    """Partidas en paralelo (§4.6.3): las partidas sin empezar con `inicio > c + 1` se adelantan al
    período siguiente al corte. Costo directo adicional 0 según el APU. Exige la declaración del
    usuario de que no dependen de las que están en curso (`requiere_declaracion`)."""
    estado = contexto.estado
    siguiente = estado.dia // estado.dias_por_periodo + 1
    candidatas = [
        p.codigo
        for p in estado.partidas
        if estado.cantidad_ejecutada(p) == CERO
        and estado.fraccion_planificada(p) == CERO
        and p.inicio > siguiente
    ]
    if not candidatas:
        return _no_aplica(
            "paralelo", "ninguna partida sin empezar con inicio posterior al periodo siguiente"
        )
    reproyeccion = reproyectar(estado, adelantar=candidatas)
    simultaneas = max(
        (len(reparto) for _, reparto in reproyeccion.plan),
        default=0,
    )
    return _cerrar(
        contexto,
        "paralelo",
        reproyeccion,
        CERO,
        (
            Supuesto(
                "independencia de las partidas",
                ", ".join(candidatas),
                NATURALEZA_SUPUESTO,
                "el plan no tiene dependencias: el usuario lo declara con su fuente (S2-R4)",
            ),
        ),
        {"adelantadas": candidatas, "partidas_simultaneas_maximas": simultaneas},
        requiere_declaracion=True,
    )


def opcion_aceptar(contexto: ContextoRecuperacion) -> Opcion:
    """Aceptar el retraso (§4.6.4): el plan es la reproyección; el costo es el indirecto
    `CF' - CF` más `penalizacion diaria × días de retraso`."""
    return _cerrar(contexto, "aceptar", contexto.base, CERO, (), {})


def opciones(contexto: ContextoRecuperacion) -> tuple[Opcion, ...]:
    """Las cuatro opciones, en el orden de `OPCIONES`."""
    return (
        opcion_cuadrillas(contexto),
        opcion_horas_extra(contexto),
        opcion_paralelo(contexto),
        opcion_aceptar(contexto),
    )
```
- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_recuperacion.py -v -W error` → 23 pruebas en verde.
Run: `uv run pytest tests/unit/test_valor_ganado.py tests/unit/test_reproyeccion.py tests/unit/test_pe_proyectado.py tests/integration/test_control.py -q -W error` → verde (la tarea 9 consume la misma firma).
Run: `uv run ruff check core/budget/recuperacion.py tests/unit/test_recuperacion.py` y la guardia del núcleo.
- [ ] **Paso 5: Commit**
```bash
git add core/budget/recuperacion.py
git commit -m "feat(core): cuatro opciones de recuperacion con su costo, limites de la LOTTT y supuestos" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 11: SL-E6b — decisión, versión `recuperacion` y revisión `caso_0006`

**Rama:** `inc/070-s2-3-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/budget/decision.py`, `migraciones/caso/versions/caso_0006_s2_decision.py`, `tests/integration/test_decision_crea_version.py`
- Modificar: `core/models/control.py` (agrega `DecisionRecuperacion`), `core/models/__init__.py` (reexporta `DecisionRecuperacion`), `core/models/entidades.py` (`MOTIVOS_VERSION` gana `"recuperacion"`; ubicar por contenido), `core/budget/edicion.py` (`guardar_edicion(..., motivo: str = "edicion")`), `tests/integration/test_migracion_s2.py` (`TABLAS_DE_S2_3 = {"decision_recuperacion"}`)

**Interfaces:**
- Consume: de la tarea 10: `Opcion`, `opciones`; de S2-2: `ResultadoControl`, `calcular_control`, `contexto_de_recuperacion`, `composiciones_de_la_linea_base`; del núcleo: `core.budget.edicion.{CambioEditado, guardar_edicion, siguiente_codigo, version_vigente}`, `core.budget.persistencia.guardar_presupuesto` (el embudo único, RV-7), `core.budget.instantanea.plan_de_version`, `core.budget.curva.{PeriodoPlan, con_curva, generar_curva}`, `core.verification.{REGLAS, auditar}`.
- Produce:
- `core/budget/decision.py`:
  - `OBJETO_PLAN = 'plan'`
  - `def cambios_de_plan(anterior: list[PeriodoPlan] | tuple[PeriodoPlan, ...] | None, nuevo: list[PeriodoPlan] | tuple[PeriodoPlan, ...]) -> list[CambioEditado]`
  - `def aplicar_decision(session: Session, resultado: ResultadoControl, opcion: Opcion, *, catalogo: Catalogo, fuente: str, responsable: str, declaracion_independencia: str='', ahora: datetime | None=None) -> models.DecisionRecuperacion`
  - `class Decision [id: int; version: str; fecha_corte: date; opcion: str; detalle: dict; costo_directo_adicional: Decimal; costo_indirecto: Decimal; penalizacion: Decimal; termino: date; spi: Decimal | None; cpi: Decimal | None; eac: Decimal | None; pe: Decimal | None; supuestos: tuple[dict, ...]; fuente: str; responsable: str; fecha_hora: datetime]`
  - `def decisiones(session: Session, proyecto_nombre: str) -> list[Decision]`
- `core/models/control.py`:
  - `class DecisionRecuperacion [id: Mapped[int]; proyecto_id: Mapped[int]; linea_base_id: Mapped[int]; version_resultante_id: Mapped[int]; fecha_corte: Mapped[date]; opcion: Mapped[str]; detalle: Mapped[str]; costo_directo_adicional: Mapped[Decimal]; costo_indirecto: Mapped[Decimal]; penalizacion: Mapped[Decimal]; termino: Mapped[date]; spi: Mapped[Decimal | None]; cpi: Mapped[Decimal | None]; eac: Mapped[Decimal | None]; pe: Mapped[Decimal | None]; supuestos: Mapped[str]; fuente: Mapped[str]; responsable: Mapped[str]; fecha_hora: Mapped[datetime]]`
  y `guardar_edicion(session, ..., motivo: str = "edicion")` (valor por defecto: SF-E2 no cambia), `MOTIVOS_VERSION` con `"recuperacion"`, la revisión `caso_0006_s2_decision` (`down_revision = "caso_0005_s2_valuaciones"`) con la tabla `decision_recuperacion`.

- [ ] **Paso 0: Expediente SL-E6** (ver tarea 10, paso 0); la rama ya está abierta.
- [ ] **Paso 1: Escribir las pruebas que fallan**
  La decisión «más cuadrillas» de OB-S2 crea la versión `OB-002` con motivo `recuperacion` y siete `RegistroCambio` (uno por fracción del plan que cambió); el informe no tiene hallazgos de R2 ni de R7 y la curva cierra en el total; la línea base no cambia y el SPI al mismo corte sigue en 0,80; la decisión recarga con la foto de lo que el usuario vio; sin fuente o sin responsable no se escribe nada; el paralelo exige la declaración; la versión nace una sola vez por el embudo único; `guardar_edicion` sin motivo sigue siendo `edicion`:
```python
# tests/integration/test_decision_crea_version.py
"""SL-E6: elegir una opción crea una versión nueva con su plan, su curva, su informe y su registro
(spec S2 §5.3, RF-79), y la línea base no cambia (S2-R3).

Decisión «más cuadrillas» de OB-S2: versión `OB-002` de motivo `recuperacion`, un `RegistroCambio`
(objeto `plan`) por cada fracción que cambió, R2 y R7 sin hallazgos, la curva que cierra en el total
y el SPI al mismo corte en 0,80.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core import models
from core.budget import edicion, guardar_edicion
from core.budget.control import (
    calcular_control,
    composiciones_de_la_linea_base,
    contexto_de_recuperacion,
)
from core.budget.decision import aplicar_decision, cambios_de_plan, decisiones
from core.budget.edicion import CambioEditado, registros_de_version, version_vigente
from core.budget.instantanea import plan_de_version
from core.budget.persistencia import cargar_elaboracion
from core.budget.recuperacion import opciones
from core.catalog import Catalogo
from core.verification import REGLAS
from tests.fixtures import control_ob_s2 as ob

D = Decimal
PLAN_DE_LA_DECISION = [
    ("Semana 1", [("OB-A", "0.4")]),
    ("Semana 2", [("OB-A", "0.5"), ("OB-B", "0.3")]),
    ("Semana 3", [("OB-A", "0.1"), ("OB-B", "0.54"), ("OB-C", "0.72")]),
    ("Semana 4", [("OB-B", "0.16"), ("OB-C", "0.28")]),
]
REGISTROS_DEL_PLAN = [
    ("Semana 1|OB-A", "0.5", "0.4"),
    ("Semana 2|OB-B", "0.5", "0.3"),
    ("Semana 3|OB-A", "0", "0.1"),
    ("Semana 3|OB-B", "0.5", "0.54"),
    ("Semana 3|OB-C", "0.5", "0.72"),
    ("Semana 4|OB-B", "0", "0.16"),
    ("Semana 4|OB-C", "0.5", "0.28"),
]


@pytest.fixture
def decidida(obra):
    """OB-S2 con V-01 y V-02 y el control al corte, listo para elegir una opción."""
    ob.registrar_v01_y_v02(obra)
    catalogo = Catalogo(obra)
    resultado = calcular_control(obra, ob.NOMBRE, catalogo=catalogo, precios=ob.precios_del_corte())
    contexto = contexto_de_recuperacion(resultado, composiciones_de_la_linea_base(resultado))
    return obra, catalogo, resultado, {o.nombre: o for o in opciones(contexto)}


def _decidir(decidida, nombre="cuadrillas", **extra):
    sesion, catalogo, resultado, por_nombre = decidida
    extra.setdefault("fuente", "decision ficticia del residente")
    extra.setdefault("responsable", "Residente Ficticio")
    return aplicar_decision(sesion, resultado, por_nombre[nombre], catalogo=catalogo, **extra)


def test_mas_cuadrillas_crea_la_version_ob_002_con_motivo_recuperacion(decidida):
    sesion = decidida[0]
    decision = _decidir(decidida)
    version = sesion.get(models.Presupuesto, decision.version_resultante_id)
    assert version.codigo == "OB-002" and version_vigente(sesion, ob.NOMBRE).codigo == "OB-002"
    origen = sesion.get(models.VersionOrigen, version.id)
    assert (origen.motivo, sesion.get(models.Presupuesto, origen.origen_id).codigo) == (
        "recuperacion",
        "OB-001",
    )


def test_un_registro_de_cambio_por_cada_fraccion_del_plan_que_cambio(decidida):
    sesion = decidida[0]
    decision = _decidir(decidida)
    version = sesion.get(models.Presupuesto, decision.version_resultante_id)
    registros = registros_de_version(sesion, version)
    assert [(r.clave, r.valor_anterior, r.valor_nuevo) for r in registros] == REGISTROS_DEL_PLAN
    assert {(r.objeto, r.campo) for r in registros} == {("plan", "fraccion")}
    assert {(r.fuente, r.responsable) for r in registros} == {
        ("decision ficticia del residente", "Residente Ficticio")
    }


def test_el_informe_de_la_version_nueva_no_tiene_hallazgos_de_r2_ni_de_r7_y_la_curva_cierra(
    decidida,
):
    sesion, catalogo, *_ = decidida
    _decidir(decidida)
    nueva = cargar_elaboracion(sesion, ob.NOMBRE, "OB-002", catalogo)
    assert [h for h in nueva.informe.hallazgos if h.regla in ("R2", "R7")] == []
    assert nueva.presupuesto.total_curva == nueva.presupuesto.total
    assert [p.periodo.split(" [")[0] for p in nueva.presupuesto.curva] == [
        "Semana 1", "Semana 2", "Semana 3", "Semana 4",
    ]  # fmt: skip
    # El plan se guardo con la version: el reparto se recupera tal cual.
    version = sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == "OB-002")
    ).one()
    plan = plan_de_version(sesion, version)
    assert [(e, list(r)) for e, r in plan] == [
        (e, [(c, D(f)) for c, f in r]) for e, r in PLAN_DE_LA_DECISION
    ]


def test_la_linea_base_no_cambia_y_el_spi_al_mismo_corte_sigue_en_0_80(decidida):
    sesion, catalogo, *_ = decidida
    _decidir(decidida)
    despues = calcular_control(
        sesion, ob.NOMBRE, catalogo=catalogo, precios=ob.precios_del_corte(), corte=ob.CORTE
    )
    assert despues.instantanea.linea_base.version == "OB-001"
    assert abs(despues.indicadores.spi - D("0.8")) <= D("0.0001")
    assert despues.reproyeccion.termino == 23  # el retraso no desaparece del control (S2-R3)
    assert sesion.scalar(select(func.count()).select_from(models.LineaBaseControl)) == 1


def test_la_decision_recarga_identica_con_la_foto_de_lo_que_el_usuario_vio(decidida):
    sesion, _, resultado, por_nombre = decidida
    opcion = por_nombre["cuadrillas"]
    _decidir(decidida)
    (cargada,) = decisiones(sesion, ob.NOMBRE)
    assert (cargada.version, cargada.opcion, cargada.fecha_corte) == (
        "OB-002",
        "cuadrillas",
        ob.CORTE,
    )
    assert cargada.termino == date(2026, 11, 24)  # dia habil 17
    assert (cargada.costo_directo_adicional, cargada.costo_indirecto) == (
        opcion.costo_directo_adicional,
        opcion.costo_indirecto,
    )
    assert (cargada.spi, cargada.cpi, cargada.eac) == (
        resultado.indicadores.spi,
        resultado.indicadores.cpi,
        opcion.eac,
    )
    assert cargada.pe == opcion.equilibrio.punto
    assert cargada.detalle["detalle"]["partidas"]["OB-B"]["k"] == 2
    assert cargada.detalle["plan"][2] == [
        "Semana 3",
        [["OB-A", "0.1"], ["OB-B", "0.54"], ["OB-C", "0.72"]],
    ]
    nombres = {s["nombre"]: s for s in cargada.supuestos}
    assert nombres["eta de cuadrillas"] == {
        "nombre": "eta de cuadrillas",
        "valor": "0.80",
        "naturaleza": "SUPUESTO_DECLARADO",
        "fuente": "Lee (2022) es la base del metodo, no del valor",
    }
    assert (cargada.fuente, cargada.responsable) == (
        "decision ficticia del residente",
        "Residente Ficticio",
    )
    assert cargada == decisiones(sesion, ob.NOMBRE)[0]  # recargar da lo mismo


@pytest.mark.parametrize(("fuente", "responsable"), [("", "Ing."), ("acta", " "), (" ", " ")])
def test_sin_fuente_o_sin_responsable_se_rechaza_y_no_se_escribe_nada(
    decidida, fuente, responsable
):
    sesion = decidida[0]
    versiones = sesion.scalar(select(func.count()).select_from(models.Presupuesto))
    with pytest.raises(ValueError, match="obligatori"):
        _decidir(decidida, fuente=fuente, responsable=responsable)
    assert sesion.scalar(select(func.count()).select_from(models.Presupuesto)) == versiones
    assert decisiones(sesion, ob.NOMBRE) == []


def test_una_opcion_que_no_aplica_no_se_puede_elegir(decidida):
    with pytest.raises(ValueError, match="la opcion 'paralelo' no aplica"):
        _decidir(decidida, "paralelo")


def test_las_partidas_en_paralelo_exigen_la_declaracion_de_independencia(decidida):
    sesion, catalogo, resultado, por_nombre = decidida
    adelantada = replace(
        por_nombre["cuadrillas"], nombre="paralelo", requiere_declaracion=True, detalle={}
    )
    with pytest.raises(ValueError, match="no dependen"):
        aplicar_decision(
            sesion, resultado, adelantada, catalogo=catalogo, fuente="acta", responsable="Ing."
        )
    decision = aplicar_decision(
        sesion, resultado, adelantada, catalogo=catalogo, fuente="acta", responsable="Ing.",
        declaracion_independencia="el residente declara que C no depende de A ni de B",
    )  # fmt: skip
    (cargada,) = decisiones(sesion, ob.NOMBRE)
    assert cargada.id == decision.id
    assert "no depende" in cargada.detalle["declaracion_independencia"]


def test_aceptar_el_retraso_tambien_deja_su_version_y_su_decision(decidida):
    decision = _decidir(decidida, "aceptar")
    assert decision.opcion == "aceptar" and decision.termino == date(2026, 12, 2)
    assert (decision.costo_directo_adicional, decision.costo_indirecto) == (0, D(90))


def test_la_segunda_decision_sale_de_la_version_vigente_y_registra_sus_propios_cambios(decidida):
    sesion = decidida[0]
    _decidir(decidida)
    segunda = _decidir(decidida, "aceptar")
    version = sesion.get(models.Presupuesto, segunda.version_resultante_id)
    assert version.codigo == "OB-003"
    origen = sesion.get(models.VersionOrigen, version.id)
    assert sesion.get(models.Presupuesto, origen.origen_id).codigo == "OB-002"
    assert [d.version for d in decisiones(sesion, ob.NOMBRE)] == ["OB-002", "OB-003"]


def test_la_version_nace_en_el_unico_embudo_una_sola_vez(decidida, monkeypatch):
    llamadas = []
    original = edicion.guardar_presupuesto

    def contar(*args, **kwargs):
        llamadas.append(kwargs.get("motivo"))
        return original(*args, **kwargs)

    monkeypatch.setattr(edicion, "guardar_presupuesto", contar)
    _decidir(decidida)
    assert llamadas == ["recuperacion"]


def test_una_opcion_sin_cambios_en_el_plan_no_crea_version(decidida):
    sesion, catalogo, resultado, por_nombre = decidida
    igual = replace(por_nombre["cuadrillas"], plan=tuple(ob.PLAN))
    with pytest.raises(ValueError, match="no cambia el plan"):
        aplicar_decision(
            sesion, resultado, igual, catalogo=catalogo, fuente="acta", responsable="Ing."
        )
    assert version_vigente(sesion, ob.NOMBRE).codigo == "OB-001"


def test_guardar_edicion_sin_motivo_sigue_siendo_edicion_y_rechaza_un_motivo_desconocido(obra):
    assert "recuperacion" in models.MOTIVOS_VERSION
    resultado = ob.elaborar_ob_s2("OB-002")
    cambio = [CambioEditado("cantidad", "OB-A", "cantidad", "100", "101")]
    nueva = guardar_edicion(
        obra, ob.NOMBRE, ob.CODIGO, resultado, ob.PARAMETROS, cambio, fuente="acta",
        responsable="Ing.", plan=ob.PLAN,
    )  # fmt: skip
    assert obra.get(models.VersionOrigen, nueva.id).motivo == "edicion"
    with pytest.raises(ValueError, match="motivo 'otra' desconocido"):
        guardar_edicion(
            obra, ob.NOMBRE, ob.CODIGO, ob.elaborar_ob_s2("OB-003"), ob.PARAMETROS, cambio,
            fuente="acta", responsable="Ing.", plan=ob.PLAN, motivo="otra",
        )  # fmt: skip


def test_cambios_de_plan_compara_por_celda_y_por_etiqueta():
    anterior = [("S1", (("A", D("0.5")),)), ("S2", (("A", D("0.5")), ("B", D(1))))]
    nuevo = [
        ("S1", (("A", D("0.50")),)),
        ("S2", (("A", D("0.25")), ("B", D(1)))),
        ("S3", (("A", D("0.25")),)),
    ]
    assert [
        (c.clave, c.valor_anterior, c.valor_nuevo) for c in cambios_de_plan(anterior, nuevo)
    ] == [
        ("S2|A", "0.5", "0.25"),
        ("S3|A", "0", "0.25"),
    ]
    assert cambios_de_plan(anterior, anterior) == []
    assert cambios_de_plan(None, [("S1", (("A", D(1)),))])[0].valor_anterior == "0"


def test_r13_y_r14_no_entran_a_regla_ni_al_informe_guardado_de_ninguna_version(decidida):
    """RF-62 y RV-9: son reglas externas que se recalculan en memoria; el 7 de 7 no se mueve."""
    sesion, catalogo, *_ = decidida
    ob.registrar(sesion, ob.VS)  # V-S da seis hallazgos de R13 y R14 en la instantanea
    _decidir(decidida)
    guardados = {
        h.regla for h in cargar_elaboracion(sesion, ob.NOMBRE, "OB-002", catalogo).informe.hallazgos
    }
    guardados |= set(sesion.scalars(select(models.Hallazgo.regla)))
    assert not guardados & {"R13", "R14"}
    assert [r.codigo for r in REGLAS] == ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
```
  `test_migracion_s2.py` pasa a exigir también la tabla de la decisión (S2 §6.1, SL-E6):
```diff
--- a/tests/integration/test_migracion_s2.py
+++ b/tests/integration/test_migracion_s2.py
@@ -23,7 +23,7 @@
     "costo_real",
     "cita_valuacion",
 }
-TABLAS_DE_S2_3: set[str] = set()
+TABLAS_DE_S2_3 = {"decision_recuperacion"}
 
 
 def _tablas(ruta: Path) -> set[str]:
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/integration/test_decision_crea_version.py tests/integration/test_migracion_s2.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'core.budget.decision'` (y, en la migración, `decision_recuperacion` ausente de las tablas).
```bash
git add tests/integration/test_decision_crea_version.py tests/integration/test_migracion_s2.py
git commit -m "test(core): la decision de recuperacion crea la version OB-002 en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  El motivo nuevo y el parámetro con valor por defecto (`guardar_edicion` sigue pasando por el único embudo `guardar_presupuesto`; S2 no agrega otro camino que cree versiones):
```diff
--- a/core/models/entidades.py
+++ b/core/models/entidades.py
@@ -502,7 +502,14 @@
 
 
 #: Motivos con que una versión nueva declara su `VersionOrigen`.
-MOTIVOS_VERSION = ("edicion", "restauracion", "cotizacion", "revaloracion", "conversion")
+MOTIVOS_VERSION = (
+    "edicion",
+    "restauracion",
+    "cotizacion",
+    "revaloracion",
+    "conversion",
+    "recuperacion",
+)
 
 
 class VersionOrigen(Base):
```
```diff
--- a/core/budget/edicion.py
+++ b/core/budget/edicion.py
@@ -106,6 +106,7 @@
     lista: models.ListaPrecios | None = None,
     ahora: datetime | None = None,
     gancho: Gancho | None = None,
+    motivo: str = "edicion",
 ) -> models.Presupuesto | None:
     """Guarda `resultado` (la elaboración ya editada) como versión nueva de `codigo_origen`.
 
@@ -113,7 +114,9 @@
     `cambios` son las celdas que cambiaron: las de valor anterior igual al nuevo no cuentan, y si no
     queda ninguna no se crea nada y se devuelve `None` (FR‑4). Crea un `RegistroCambio` por celda.
     `lista` es la de la versión de origen salvo que se diga otra; `plan` se guarda con la versión.
-    `gancho(session, version)` corre tras crearla, en la misma sesión. No confirma.
+    `gancho(session, version)` corre tras crearla, en la misma sesión. `motivo` es uno de
+    `MOTIVOS_VERSION` (por defecto `edicion`; `recuperacion` lo pasa `core.budget.decision`). No
+    confirma.
     """
     fuente, responsable = _exigir_respaldo(fuente, responsable)
     for cambio in cambios:
@@ -134,7 +137,7 @@
         pendientes=resultado.pendientes,
         plan=plan,
         version_origen=origen,
-        motivo="edicion",
+        motivo=motivo,
         heredar_insumos=True,
     )
     momento = ahora or datetime.now()
```
  La tabla de la decisión y su reexportación:
```diff
--- a/core/models/control.py
+++ b/core/models/control.py
@@ -182,3 +182,34 @@
     id: Mapped[int] = mapped_column(Integer, primary_key=True)
     periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo_reajuste.id", ondelete="CASCADE"))
     valuacion_id: Mapped[int] = mapped_column(ForeignKey("valuacion.id", ondelete="CASCADE"))
+
+
+class DecisionRecuperacion(Base):
+    """SL-E6: la decisión de recuperación, con la foto de lo que el usuario vio (S2 §6.1)."""
+
+    __tablename__ = "decision_recuperacion"
+    __table_args__ = (Index("ix_decision_recuperacion_proyecto", "proyecto_id"),)
+
+    id: Mapped[int] = mapped_column(Integer, primary_key=True)
+    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
+    linea_base_id: Mapped[int] = mapped_column(
+        ForeignKey("linea_base_control.id", ondelete="CASCADE")
+    )
+    version_resultante_id: Mapped[int] = mapped_column(
+        ForeignKey("presupuesto.id", ondelete="CASCADE")
+    )
+    fecha_corte: Mapped[date] = mapped_column(Date)
+    opcion: Mapped[str] = mapped_column(String(20))
+    detalle: Mapped[str] = mapped_column(Text, default="{}")
+    costo_directo_adicional: Mapped[Decimal] = mapped_column(DecimalExacto)
+    costo_indirecto: Mapped[Decimal] = mapped_column(DecimalExacto)
+    penalizacion: Mapped[Decimal] = mapped_column(DecimalExacto)
+    termino: Mapped[date] = mapped_column(Date)
+    spi: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
+    cpi: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
+    eac: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
+    pe: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
+    supuestos: Mapped[str] = mapped_column(Text, default="[]")
+    fuente: Mapped[str] = mapped_column(String(300))
+    responsable: Mapped[str] = mapped_column(String(120))
+    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
```
```diff
--- a/core/models/__init__.py
+++ b/core/models/__init__.py
@@ -10,6 +10,7 @@
     CalendarioObra,
     CitaValuacion,
     CostoReal,
+    DecisionRecuperacion,
     LineaBaseControl,
     LineaValuacion,
     ParametrosControl,
@@ -78,6 +79,7 @@
     "CostoReal",
     "Cotizacion",
     "DecimalExacto",
+    "DecisionRecuperacion",
     "DescarteVersion",
     "Ejecucion",
     "EjecutadoPeriodo",
```
  La revisión de Alembic:
```python
# migraciones/caso/versions/caso_0006_s2_decision.py
"""S2-3 (SL-E6): la decisión de recuperación, con la foto de lo que el usuario vio."""

import sqlalchemy as sa
from alembic import op

revision = "caso_0006_s2_decision"
down_revision = "caso_0005_s2_valuaciones"
branch_labels = None
depends_on = None

DEC = sa.String(40)  # impl de core.models.tipos.DecimalExacto


def upgrade() -> None:
    op.create_table(
        "decision_recuperacion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "proyecto_id",
            sa.Integer,
            sa.ForeignKey("proyecto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "linea_base_id",
            sa.Integer,
            sa.ForeignKey("linea_base_control.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_resultante_id",
            sa.Integer,
            sa.ForeignKey("presupuesto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fecha_corte", sa.Date, nullable=False),
        sa.Column("opcion", sa.String(20), nullable=False),
        sa.Column("detalle", sa.Text, nullable=False),
        sa.Column("costo_directo_adicional", DEC, nullable=False),
        sa.Column("costo_indirecto", DEC, nullable=False),
        sa.Column("penalizacion", DEC, nullable=False),
        sa.Column("termino", sa.Date, nullable=False),
        sa.Column("spi", DEC, nullable=True),
        sa.Column("cpi", DEC, nullable=True),
        sa.Column("eac", DEC, nullable=True),
        sa.Column("pe", DEC, nullable=True),
        sa.Column("supuestos", sa.Text, nullable=False),
        sa.Column("fuente", sa.String(300), nullable=False),
        sa.Column("responsable", sa.String(120), nullable=False),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
    )
    op.create_index("ix_decision_recuperacion_proyecto", "decision_recuperacion", ["proyecto_id"])


def downgrade() -> None:
    op.drop_table("decision_recuperacion")
```
  La decisión (una transacción; no confirma; compara contra el plan de la **versión vigente**, RP7-7; la línea base de control no cambia):
```python
# core/budget/decision.py
"""SL-E6: la decisión de recuperación crea una versión nueva (spec S2 §5.3, RF-79).

Elegir una opción (`core.budget.recuperacion`) crea, en **una transacción**, una versión nueva de
motivo `recuperacion` con el plan de la opción, su curva y su informe (R1-R7 de nuevo sobre la curva
nueva), un `RegistroCambio` por cada fracción del plan que cambió y una `DecisionRecuperacion` con
la foto de lo que el usuario vio. La versión nace en el embudo `guardar_presupuesto` (RV-7) por
`guardar_edicion(motivo="recuperacion")`: este módulo no agrega otro camino que cree versiones.

La **línea base de control no cambia** (S2-R3): el SPI al mismo corte sigue siendo el mismo después
de decidir. Sin fuente o sin responsable se rechaza. No confirma la transacción.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _parametros_de
from core.budget.calendario import dia_habil
from core.budget.control import ResultadoControl
from core.budget.curva import PeriodoPlan, con_curva, generar_curva
from core.budget.edicion import (
    CambioEditado,
    _exigir_respaldo,
    guardar_edicion,
    siguiente_codigo,
    version_vigente,
)
from core.budget.instantanea import plan_de_version
from core.budget.persistencia import (
    _cargar_externos,
    cargar_elaboracion,
)
from core.budget.presupuesto import ResultadoElaboracion, _declarar_externos, _declarar_pendientes
from core.budget.recuperacion import Opcion
from core.catalog import Catalogo
from core.verification import REGLAS, auditar

__all__ = ["Decision", "aplicar_decision", "cambios_de_plan", "decisiones"]

CERO = Decimal(0)
OBJETO_PLAN = "plan"


def _texto(valor: Decimal) -> str:
    """Una fracción como texto estable (sin ceros de relleno ni notación científica)."""
    return format(valor.normalize(), "f")


def cambios_de_plan(
    anterior: list[PeriodoPlan] | tuple[PeriodoPlan, ...] | None,
    nuevo: list[PeriodoPlan] | tuple[PeriodoPlan, ...],
) -> list[CambioEditado]:
    """Un cambio (objeto `plan`) por cada (período, partida) cuya fracción cambió: la fracción
    anterior (0 si la celda no existía) y la nueva. La clave es `<período>|<partida>`, con el
    período por su etiqueta: primero los del plan nuevo y luego los que solo tenía el anterior."""

    def celdas(plan) -> dict[tuple[str, str], Decimal]:
        valores: dict[tuple[str, str], Decimal] = {}
        for etiqueta, reparto in plan or ():
            for codigo, fraccion in reparto:
                clave = (etiqueta, codigo)
                valores[clave] = valores.get(clave, CERO) + fraccion
        return valores

    antes, despues = celdas(anterior), celdas(nuevo)
    claves = [*despues, *(clave for clave in antes if clave not in despues)]
    return [
        CambioEditado(
            OBJETO_PLAN,
            f"{etiqueta}|{codigo}",
            "fraccion",
            _texto(antes.get((etiqueta, codigo), CERO)),
            _texto(despues.get((etiqueta, codigo), CERO)),
        )
        for etiqueta, codigo in claves
        if antes.get((etiqueta, codigo), CERO) != despues.get((etiqueta, codigo), CERO)
    ]


def aplicar_decision(
    session: Session,
    resultado: ResultadoControl,
    opcion: Opcion,
    *,
    catalogo: Catalogo,
    fuente: str,
    responsable: str,
    declaracion_independencia: str = "",
    ahora: datetime | None = None,
) -> models.DecisionRecuperacion:
    """Crea la versión de la opción elegida y guarda la decisión (RF-79).

    `ValueError` si falta la fuente o el responsable, si la opción no aplica, si es «partidas en
    paralelo» sin la declaración de independencia o si el plan de la opción no cambia nada."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    if not opcion.aplica:
        raise ValueError(f"la opcion {opcion.nombre!r} no aplica: {opcion.motivo}")
    if opcion.requiere_declaracion and not declaracion_independencia.strip():
        raise ValueError(
            "las partidas en paralelo exigen declarar, con su fuente, que no dependen de las "
            "que estan en curso (S2-R4)"
        )
    instantanea = resultado.instantanea
    proyecto = instantanea.proyecto
    origen = version_vigente(session, proyecto)
    if origen is None:
        raise ValueError("el proyecto no tiene version guardada")
    guardada = cargar_elaboracion(session, proyecto, origen.codigo, catalogo)
    codigo = siguiente_codigo(session, proyecto)
    presupuesto = replace(guardada.presupuesto, codigo=codigo)
    presupuesto = con_curva(presupuesto, generar_curva(presupuesto, opcion.plan))
    informe = _declarar_pendientes(auditar(presupuesto, REGLAS), guardada.pendientes)
    informe = _declarar_externos(informe, _cargar_externos(session, origen, REGLAS))
    cambios = cambios_de_plan(plan_de_version(session, origen), opcion.plan)
    calendario = instantanea.calendario
    termino: date = dia_habil(
        calendario.fecha_inicio, opcion.termino, frozenset(calendario.feriados)
    )
    indicadores = resultado.indicadores
    guardadas: list[models.DecisionRecuperacion] = []

    def registrar(sesion: Session, version: models.Presupuesto) -> None:
        fila = models.DecisionRecuperacion(
            proyecto_id=version.proyecto_id,
            linea_base_id=instantanea.linea_base.id,
            version_resultante_id=version.id,
            fecha_corte=instantanea.corte,
            opcion=opcion.nombre,
            detalle=json.dumps(
                {
                    "detalle": opcion.detalle,
                    "declaracion_independencia": declaracion_independencia.strip(),
                    "requisitos": list(opcion.requisitos),
                    "plan": [
                        [etiqueta, [[c, _texto(f)] for c, f in reparto]]
                        for etiqueta, reparto in opcion.plan
                    ],
                },
                ensure_ascii=False,
                default=str,
            ),
            costo_directo_adicional=opcion.costo_directo_adicional,
            costo_indirecto=opcion.costo_indirecto,
            penalizacion=opcion.penalizacion,
            termino=termino,
            spi=indicadores.spi,
            cpi=indicadores.cpi,
            eac=opcion.eac,
            pe=None if opcion.equilibrio is None else opcion.equilibrio.punto,
            supuestos=json.dumps(
                [
                    {
                        "nombre": s.nombre,
                        "valor": s.valor,
                        "naturaleza": s.naturaleza,
                        "fuente": s.fuente,
                    }
                    for s in opcion.supuestos
                ],
                ensure_ascii=False,
            ),
            fuente=fuente,
            responsable=responsable,
            fecha_hora=ahora or datetime.now(),
        )
        sesion.add(fila)
        sesion.flush()
        guardadas.append(fila)

    nueva = guardar_edicion(
        session,
        proyecto,
        origen.codigo,
        ResultadoElaboracion(presupuesto, informe, guardada.pendientes),
        _parametros_de(origen),
        cambios,
        fuente=fuente,
        responsable=responsable,
        plan=list(opcion.plan),
        ahora=ahora,
        gancho=registrar,
        motivo="recuperacion",
    )
    if nueva is None:
        raise ValueError("la opcion no cambia el plan de la version vigente: no hay nada que crear")
    return guardadas[0]


@dataclass(frozen=True, slots=True)
class Decision:
    """Una decisión recargada: lo que el usuario vio al elegir y la versión que resultó."""

    id: int
    version: str
    fecha_corte: date
    opcion: str
    detalle: dict
    costo_directo_adicional: Decimal
    costo_indirecto: Decimal
    penalizacion: Decimal
    termino: date
    spi: Decimal | None
    cpi: Decimal | None
    eac: Decimal | None
    pe: Decimal | None
    supuestos: tuple[dict, ...]
    fuente: str
    responsable: str
    fecha_hora: datetime


def decisiones(session: Session, proyecto_nombre: str) -> list[Decision]:
    """Las decisiones de recuperación del proyecto, de la más antigua a la más reciente."""
    filas = session.execute(
        select(models.DecisionRecuperacion, models.Presupuesto.codigo)
        .join(
            models.Presupuesto,
            models.Presupuesto.id == models.DecisionRecuperacion.version_resultante_id,
        )
        .join(models.Proyecto, models.Proyecto.id == models.DecisionRecuperacion.proyecto_id)
        .where(models.Proyecto.nombre == proyecto_nombre)
        .order_by(models.DecisionRecuperacion.id)
    )
    return [
        Decision(
            id=fila.id,
            version=codigo,
            fecha_corte=fila.fecha_corte,
            opcion=fila.opcion,
            detalle=json.loads(fila.detalle),
            costo_directo_adicional=fila.costo_directo_adicional,
            costo_indirecto=fila.costo_indirecto,
            penalizacion=fila.penalizacion,
            termino=fila.termino,
            spi=fila.spi,
            cpi=fila.cpi,
            eac=fila.eac,
            pe=fila.pe,
            supuestos=tuple(json.loads(fila.supuestos)),
            fuente=fila.fuente,
            responsable=fila.responsable,
            fecha_hora=fila.fecha_hora,
        )
        for fila, codigo in filas
    ]
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/integration/test_decision_crea_version.py tests/integration/test_migracion_s2.py tests/unit/test_recuperacion.py -v -W error` → 17 pruebas de la decisión en verde y las de migración en verde sobre las bases de la 0.5.0 y la 0.6.0.
Run: `uv run pytest tests/integration/test_edicion_versiones.py tests/integration/test_hoja_versiones.py tests/integration/test_migraciones.py -q -W error` → verde: las ediciones de SF-E2 no cambian y la deriva de RNF-20 recorre `caso_0006_s2_decision` sin diferencia.
Run: `uv run ruff check core/budget/decision.py core/budget/edicion.py core/models/control.py core/models/entidades.py core/models/__init__.py migraciones/caso/versions/caso_0006_s2_decision.py tests/integration/test_decision_crea_version.py` y la guardia del núcleo.
- [ ] **Paso 5: Commit**
```bash
git add core/budget/decision.py core/budget/edicion.py core/models/control.py core/models/entidades.py core/models/__init__.py migraciones/caso/versions/caso_0006_s2_decision.py
git commit -m "feat(core): la decision de recuperacion crea la version con motivo recuperacion y su registro" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS2-3 y foco de revisión de la fase

**Compuerta GS2-3** (se cruza al fusionar `inc/070-s2-3-nucleo`):
1. `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-3 --junit reporte-pruebas.xml` → todas las filas en OK, con C3 sobre los pares de `S2-3` (opciones, decisión, `caso_0006`).
2. CI verde en Linux y Windows, `-W error`, cero omitidas; el paso de la meta en `--hasta S2-3`.
3. Las ediciones de SF-E2 sin cambio: `tests/integration/test_edicion_versiones.py` y `test_guardar_edicion_sin_motivo_sigue_siendo_edicion_y_rechaza_un_motivo_desconocido` en verde.
4. La prueba de deriva RNF-20 recorre `caso_0005` y `caso_0006` sin diferencia; `test_migracion_s2.py` exige las nueve tablas.
5. `uv run python scripts/guardia_nucleo.py --base origin/main` en 0; `uv run ruff check` sobre los archivos tocados; `core/contracts/` intacto desde `v0.6.0`.
6. Aprobación de los encargos y aval del tutor de SL-E6 (modelo `E(k)`, límites legales, decisión); compuerta anotada en `docs/bitacora/2026-10-silice-070.md`.

**Foco de revisión de S2-3:**
1. **Horas extra por encima de la ley:** 3 horas por día o 101 horas en el año se rechazan citando el artículo, y no hay valor por defecto que las salte → `tests/unit/test_recuperacion.py::test_las_horas_extra_por_dia_sobre_el_limite_se_rechazan` y `::test_cien_horas_extra_en_el_anio_pasan_y_ciento_una_se_rechazan` (Tarea 10).
2. **Una partida sin jornal (destajo o sin mano de obra):** «no aplica» sin dividir por cero, y la otra partida se calcula y la primera se declara → `tests/unit/test_recuperacion.py::test_si_solo_una_partida_no_tiene_jornal_la_otra_se_calcula_y_la_primera_se_declara` (Tarea 10).
3. **Elegir sin fuente o sin responsable:** no escribe nada, ni versión ni decisión → `tests/integration/test_decision_crea_version.py::test_sin_fuente_o_sin_responsable_se_rechaza_y_no_se_escribe_nada` (Tarea 11).
4. **Una opción que no cambia el plan** no crea una versión vacía → `tests/integration/test_decision_crea_version.py::test_una_opcion_sin_cambios_en_el_plan_no_crea_version` (Tarea 11).
5. **Dos caminos que crean versiones:** la decisión nace en el embudo una sola vez → `tests/integration/test_decision_crea_version.py::test_la_version_nace_en_el_unico_embudo_una_sola_vez` (Tarea 11).

### Discrepancias encontradas (S2-3)

1. **Módulo `decision.py` no previsto en §5.2.** *Resuelta (RP7-3):* para que `recuperacion.py` quede puro (sin `sqlalchemy`) y la decisión, que escribe, viva aparte.
2. **Horas extra «en las partidas determinantes».** El spec no fija cuántas horas por partida. *Resuelta (RP7-5):* `h = horas_extra_dia` (por defecto 2) en todas las determinantes y límite anual con `horas_previas` declarado.
3. **Paralelo sin declaración.** El spec exige la declaración del usuario; no dice cuándo. *Resuelta (RP7-10):* la opción se calcula y se muestra siempre; elegirla sin declarar se rechaza (`test_las_partidas_en_paralelo_exigen_la_declaracion_de_independencia`).
4. **La segunda decisión.** *Resuelta (RP7-7):* sale de la versión vigente y registra sus propios cambios (`test_la_segunda_decision_sale_de_la_version_vigente_y_registra_sus_propios_cambios`).

---

# S2-4 — Interfaz: «Control de obra», la casilla de reajuste y RNF-15 (ramas `inc/070-s2-4-ui` e `inc/070-s2-4-nucleo`)

Dos ramas en serie. `inc/070-s2-4-ui` (tareas 12 y 13) solo toca `ui/` y `tests/`; sale de `origin/main` con S2-3
fusionada y consume el núcleo ya cerrado. `inc/070-s2-4-nucleo` (tarea 14) mide RNF-15 y agrega la precarga que lo hace
cumplir; es la última rama de núcleo de S2.

### Tarea 12: `ui/control.py` (sin Streamlit) y la casilla «Tomar lo ejecutado de las valuaciones»

**Rama:** `inc/070-s2-4-ui` (solo `ui/`, `tests/`; sale de `main` con S2-3 fusionada)   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/control.py`, `tests/integration/test_ui_control.py`, `tests/unit/test_arquitectura_s2.py`, `tests/integration/test_ui_reajuste_valuaciones.py`
- Modificar: `ui/reajuste.py` (S1, T13 de la 0.6.0: importa `core.budget.puente` y agrega `periodos_desde_valuaciones` y `guardar_con_valuaciones`; ubicar por contenido: la sección nueva va justo antes de `parciales_por_reemplazar`)

**Interfaces:**
- Consume: de S2-1 a S2-3: `core.budget.valuaciones.{registrar_linea_base, registrar_valuacion, anular_valuacion, registrar_costo, leer_valuaciones_excel, registrar_lectura, tabla_valuaciones, anexo_control, linea_base_vigente, valuaciones_registradas, Calendario}`, `core.budget.control.{calcular_control, ResultadoControl, parametros_de_control, guardar_parametros, contexto_de_recuperacion, composiciones_de_la_linea_base, precios_por_escalatoria}`, `core.budget.recuperacion.{opciones, Opcion}`, `core.budget.decision.{aplicar_decision, decisiones}`, `core.budget.puente.{PeriodoDelEstudio, periodos_declarados, estudio_con_valuaciones}`, `core.budget.excel.TablaExportable`; de S1: `ui.reajuste.{_texto, _fecha, _con_datos, calcular, guardar}`, `ui.hoja.HojaInvalida`, `ui.texto_seguro` (no se importa aquí: la pantalla lo usa).
- Produce:
- `ui/control.py`:
  - `METODO_NINGUNO = 'Sin precios del corte'`
  - `METODO_COMPROBACION = 'Comprobacion directa (version revalorada)'`
  - `METODO_ESCALATORIA = 'Escalatoria (un Km declarado)'`
  - `METODOS_DE_PRECIOS = (METODO_NINGUNO, METODO_COMPROBACION, METODO_ESCALATORIA)`
  - `COLUMNAS_LINEAS = ('Partida', 'Cantidad', 'Fecha de medicion', 'Observacion')`
  - `COLUMNAS_VALUACIONES = ('Numero', 'Periodo', 'Fecha', 'Inspector', 'Registrada', 'Estado')`
  - `COLUMNAS_INDICADORES = ('Indicador', 'Valor', 'En la otra moneda', 'Nota')`
  - `COLUMNAS_ALERTAS = ('Alerta', 'Severidad', 'Descripcion', 'Observado', 'Umbral')`
  - `COLUMNAS_REPROYECCION = ('Partida', 'Indice', 'Fin (dia habil)', 'Nota')`
  - `COLUMNAS_OPCIONES = ('Opcion', 'Termino', 'Retraso (dias)', 'Costo directo adicional', 'Costo indirecto', 'Pen`
  - `COLUMNAS_DECISIONES = ('Version', 'Opcion', 'Corte', 'Termino', 'Fuente', 'Responsable')`
  - `NO_DISPONIBLE = 'no disponible'`
  - `NO_APLICA = 'no aplica'`
  - `NATURALEZA_SUPUESTO = 'SUPUESTO_DECLARADO'`
  - `NATURALEZA_DATO = 'DATO_DEL_CONTRATO'`
  - `class ControlInvalido`
  - `def versiones_para_la_linea_base(sesion: Session, proyecto: str) -> list[str]`
  - `def versiones_revaloradas(sesion: Session, proyecto: str) -> list[str]`
  - `def declarar_linea_base(sesion: Session, proyecto: str, version: str, *, desde: str, perspectiva: str, inicio: str, dias_por_periodo: str, feriados: str, fuente: str, responsable: str) -> None`
  - `def lineas_desde_filas(filas: Sequence[Mapping[str, object]]) -> list[LineaValuacion]`
  - `def registrar_y_controlar(sesion: Session, proyecto: str, catalogo: Catalogo, *, numero: str, desde: str, hasta: str, fecha: str, inspector: str, filas: Sequence[Mapping[str, object]], fuente: str, responsable: str, precios: PreciosDelCorte | None=None) -> ResultadoControl`
  - `def anular(sesion: Session, valuacion_id: int, *, motivo: str, responsable: str) -> None`
  - `def registrar_costo_real(sesion: Session, proyecto: str, *, monto: str, moneda: str, fecha: str, fuente: str, responsable: str, partida: str='') -> None`
  - `def leer_excel(ruta: Path) -> LecturaControl`
  - `def importar_excel(sesion: Session, proyecto: str, lectura: LecturaControl, *, fuente: str, responsable: str) -> int`
  - `class PrecioElegido [metodo: str; version: str; km: str; r: str; fuente: str]`
  - `def precios_del_corte(sesion: Session, proyecto: str, catalogo: Catalogo, elegido: PrecioElegido, perspectiva: str) -> PreciosDelCorte | None`
  - `def calcular_el_control(sesion: Session, proyecto: str, catalogo: Catalogo, *, corte: date | None=None, precios: PreciosDelCorte | None=None) -> ResultadoControl`
  - `def calcular_las_opciones(resultado: ResultadoControl, *, objetivo: str='', horas_previas: str='0', independientes: str='') -> tuple[Opcion, ...]`
  - `def elegir_opcion(sesion: Session, resultado: ResultadoControl, opcion: Opcion, catalogo: Catalogo, *, fuente: str, responsable: str, declaracion_independencia: str='') -> str`
  - `def estado_de_valuaciones(resultado: ResultadoControl) -> dict[str, str]`
  - `def filas_de_valuaciones(resultado: ResultadoControl) -> list[dict[str, str]]`
  - `def filas_de_indicadores(sesion: Session, resultado: ResultadoControl) -> list[dict[str, str]]`
  - `def alertas_en_filas(resultado: ResultadoControl) -> list[dict[str, str]]`
  - `def filas_de_reproyeccion(resultado: ResultadoControl) -> list[dict[str, str]]`
  - `def filas_de_opciones(todas: Sequence[Opcion]) -> list[dict[str, str]]`
  - `def filas_de_decisiones(sesion: Session, proyecto: str) -> list[dict[str, str]]`
  - `def tablas_de_control(sesion: Session, proyecto: str, catalogo: Catalogo, *, precios: PreciosDelCorte | None=None) -> list[TablaExportable]`
  - `PARAMETROS_EDITABLES = (('spi_error', 'SPI por debajo del cual el retraso es ERROR (AL-1)', NATURALEZA_SUPUESTO),`
  - `COLUMNAS_PARAMETROS = ('Parametro', 'Que es', 'Valor', 'Naturaleza')`
  - `def filas_de_parametros(parametros: ParametrosControl) -> list[dict[str, str]]`
  - `def parametros_desde_filas(filas: Sequence[Mapping[str, object]]) -> ParametrosControl`
  - `def guardar_los_parametros(sesion: Session, proyecto: str, filas: Sequence[Mapping[str, object]], *, fuente: str, responsable: str) -> int`
  - `def curva_pv_ev_ac(sesion: Session, resultado: ResultadoControl) -> list[dict[str, object]]`
  - `def texto_monto(valor: Decimal | None) -> str`
  - `def tiene_linea_base(sesion: Session, proyecto: str) -> bool`
  - `def describir_linea_base(sesion: Session, proyecto: str) -> str | None`
  - `def hay_valuaciones(sesion: Session, proyecto: str) -> bool`
  - `def corte_por_defecto(sesion: Session, proyecto: str) -> date`
  - `def valuaciones_para_anular(sesion: Session, proyecto: str) -> list[tuple[int, str]]`
  - `def parametros_actuales(sesion: Session, proyecto: str) -> ParametrosControl`
  - `def dia_con_fecha(resultado: ResultadoControl, dia: int | None) -> str`
  - `def filas_del_plan_reproyectado(resultado: ResultadoControl) -> tuple[tuple[str, ...], list[dict[str, str]]]`
  - `def estudios_que_suma(resultado: ResultadoControl) -> str`
- `ui/reajuste.py`:
  - `def periodos_desde_valuaciones(sesion, proyecto: str, periodos: Sequence[Mapping[str, str]]) -> list[PeriodoDeclarado]`
  - `def guardar_con_valuaciones(sesion, proyecto: str, codigo: str, clausula: Clausula, periodos: Sequence[Mapping[str, str]], *, fecha_calculo: date, fuente: str, responsable: str, reemplaza_a: int | None=None) -> int`

- [ ] **Paso 1: Escribir las pruebas que fallan**
  `ui.control` es lo que la pantalla necesita del núcleo, sin pintar: declarar la línea base desde textos, registrar a mano o por XLSX con informe previo, anular, costos reales, calcular siempre el control (indicadores en las dos monedas con la tasa del corte, alertas, reproyección), las opciones a pedido y elegir una, los precios del corte según el método (ninguno, comprobación o escalatoria con un Km único; RP7-11) y las tres hojas del Excel de la hoja. Cada función que escribe confirma o deshace y levanta `ControlInvalido` con mensaje en español, sin *traceback*:
```python
# tests/integration/test_ui_control.py
"""UC-19 y UC-20 desde la capa sin Streamlit (`ui.control`, spec S2 §5.5).

Registrar una valuación a mano o por XLSX, ver el control al corte, pedir las opciones y elegir una,
y las hojas del Excel; todo sobre OB-S2 y con los mismos números de la memoria.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import openpyxl
import pytest
from sqlalchemy import func, select

from core import models
from core.budget import exportar_hoja
from core.budget.excel import (
    HOJA_APU,
    HOJA_AUDITORIA,
    HOJA_PRESUPUESTO,
    PESTANA_EQUILIBRIO,
    PESTANA_PLAN,
)
from core.catalog import Catalogo
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz
from ui import control

D = Decimal
FILAS_V01 = [
    {"Partida": "OB-A", "Cantidad": "40", "Fecha de medicion": "", "Observacion": ""},
    {"Partida": "", "Cantidad": "", "Fecha de medicion": "", "Observacion": ""},
]


def _registrar_v01(sesion, **extra):
    datos = dict(
        numero="V-01", desde="2026-11-02", hasta="2026-11-06", fecha="2026-11-09",
        inspector=ob.INSPECTOR, filas=FILAS_V01, fuente=ob.FUENTE, responsable=ob.RESPONSABLE,
    )  # fmt: skip
    datos.update(extra)
    return control.registrar_y_controlar(sesion, ob.NOMBRE, Catalogo(sesion), **datos)


def test_declarar_la_linea_base_desde_los_textos_de_la_pantalla(obra_sin_linea_base):
    sesion = obra_sin_linea_base
    control.declarar_linea_base(
        sesion, ob.NOMBRE, ob.CODIGO, desde="2026-11-02", perspectiva="costo", inicio="2026-11-02",
        dias_por_periodo="5", feriados="2026-11-04, 2026-11-05\n2026-11-06", fuente=ob.FUENTE,
        responsable=ob.RESPONSABLE,
    )  # fmt: skip
    fila = sesion.scalars(select(models.CalendarioObra)).one()
    assert (fila.dias_por_periodo, fila.feriados) == (
        5,
        '["2026-11-04", "2026-11-05", "2026-11-06"]',
    )


@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("desde", "02/11/2026", "desde: '02/11/2026' no es una fecha"),
        ("dias_por_periodo", "cinco", "dias por periodo: 'cinco' no es un numero"),
        ("dias_por_periodo", "2.5", "debe ser un entero"),
        ("dias_por_periodo", "0", "1 o mas"),
        ("perspectiva", "otra", "perspectiva"),
        ("feriados", "2026-13-40", "feriado: '2026-13-40' no es una fecha"),
        ("fuente", "", "obligatoria"),
    ],
)
def test_una_linea_base_mal_declarada_se_rechaza_con_su_mensaje_y_sin_escribir(
    obra_sin_linea_base, campo, valor, mensaje
):
    datos = dict(
        desde="2026-11-02", perspectiva="costo", inicio="2026-11-02", dias_por_periodo="5",
        feriados="", fuente=ob.FUENTE, responsable=ob.RESPONSABLE,
    )  # fmt: skip
    datos[campo] = valor
    with pytest.raises(control.ControlInvalido, match=mensaje):
        control.declarar_linea_base(obra_sin_linea_base, ob.NOMBRE, ob.CODIGO, **datos)
    assert (
        obra_sin_linea_base.scalar(select(func.count()).select_from(models.LineaBaseControl)) == 0
    )


def test_registrar_una_valuacion_devuelve_el_control_al_corte_de_su_hasta(obra):
    resultado = _registrar_v01(obra)
    assert resultado.instantanea.corte == date(2026, 11, 6)
    assert resultado.indicadores.ev == D(400)
    assert resultado.reproyeccion.termino is not None
    assert resultado.informe.hallazgos == ()
    assert obra.scalar(select(func.count()).select_from(models.Valuacion)) == 1  # confirmada


def test_una_cantidad_ilegible_o_negativa_se_rechaza_con_su_fila_y_no_se_escribe(obra):
    for cantidad, mensaje in (("cuarenta", "fila 1, cantidad"), ("-3", "no puede ser negativa")):
        filas = [{**FILAS_V01[0], "Cantidad": cantidad}]
        with pytest.raises(control.ControlInvalido, match=mensaje):
            _registrar_v01(obra, filas=filas)
    with pytest.raises(control.ControlInvalido, match="fila 1: falta la partida"):
        control.lineas_desde_filas([{"Partida": "", "Cantidad": "5"}])
    assert obra.scalar(select(func.count()).select_from(models.Valuacion)) == 0


def test_una_valuacion_sin_fuente_se_rechaza_y_se_deshace(obra):
    with pytest.raises(control.ControlInvalido, match="obligatoria"):
        _registrar_v01(obra, fuente=" ")
    assert obra.scalar(select(func.count()).select_from(models.Valuacion)) == 0


def test_sin_linea_base_el_control_dice_que_hay_que_declararla(obra_sin_linea_base):
    with pytest.raises(control.ControlInvalido, match="linea base de control"):
        control.calcular_el_control(
            obra_sin_linea_base, ob.NOMBRE, Catalogo(obra_sin_linea_base), corte=ob.CORTE
        )


def test_la_tabla_de_valuaciones_muestra_la_fecha_de_registro_y_el_peor_hallazgo(obra):
    ob.registrar_v01_y_v02(obra)
    ob.registrar(obra, ob.VS)
    resultado = control.calcular_el_control(obra, ob.NOMBRE, Catalogo(obra), corte=ob.CORTE_DE_VS)
    filas = control.filas_de_valuaciones(resultado)
    assert [f["Numero"] for f in filas] == ["V-01", "V-02", "V-03"]
    assert filas[0]["Registrada"] == "2026-11-09 09:00" and filas[0]["Estado"] == "sin hallazgos"
    assert filas[2]["Estado"] == "ERROR: R13" or filas[2]["Estado"].startswith("ERROR")
    assert tuple(filas[0]) == control.COLUMNAS_VALUACIONES


def test_los_indicadores_salen_en_las_dos_monedas_con_la_tasa_del_corte(obra):
    ob.registrar_v01_y_v02(obra)
    registrar_importacion(
        obra, definicion_tasa("venta"), [Observacion(ob.CORTE, D("850"))], archivo="t.xls",
        huella="a" * 64, fuente="https://www.bcv.org.ve/", fecha_descarga=date(2026, 11, 20),
        responsable="Admin", filas_leidas=1, filas_rechazadas=0,
    )  # fmt: skip
    resultado = control.calcular_el_control(
        obra, ob.NOMBRE, Catalogo(obra), precios=ob.precios_del_corte()
    )
    filas = {f["Indicador"]: f for f in control.filas_de_indicadores(obra, resultado)}
    assert filas["PV (USD)"]["Valor"] == "1500.00"
    assert filas["PV (USD)"]["En la otra moneda"] == "1275000.00 Bs"
    assert filas["SPI"]["Valor"] == "0.8000" and filas["CPI"]["Valor"] == "0.9375"
    assert filas["EAC (sistema) (USD)"]["Valor"] == "4480.00"
    assert filas["Desvio de precio (USD)"]["Valor"] == "-60.00"
    assert filas["Desvio de consumo (USD)"]["Valor"] == "-20.00"
    assert filas["Metodo y fuente del precio del corte"]["Valor"] == "comprobacion"


def test_sin_tasa_del_corte_la_otra_moneda_dice_no_disponible(obra):
    ob.registrar_v01_y_v02(obra)
    resultado = control.calcular_el_control(obra, ob.NOMBRE, Catalogo(obra))
    filas = {f["Indicador"]: f for f in control.filas_de_indicadores(obra, resultado)}
    assert filas["PV (USD)"]["En la otra moneda"] == "no disponible"
    assert filas["Tasa del corte"]["Valor"] == "no disponible"
    assert filas["Desvio de precio (USD)"]["Valor"] == "no disponible"  # sin precios del corte
    assert "sin precios del corte" in filas["Desvio de precio (USD)"]["Nota"]


def test_las_alertas_y_la_reproyeccion_se_muestran_siempre(obra):
    ob.registrar_v01_y_v02(obra)
    resultado = control.calcular_el_control(
        obra, ob.NOMBRE, Catalogo(obra), precios=ob.precios_del_corte()
    )
    alertas = {f["Alerta"]: f for f in control.alertas_en_filas(resultado)}
    assert {c: alertas[c]["Severidad"] for c in ("AL-1", "AL-2", "AL-3", "AL-4", "AL-5")} == {
        "AL-1": "ERROR", "AL-2": "ADVERTENCIA", "AL-3": "ERROR", "AL-4": "ERROR", "AL-5": "INFO",
    }  # fmt: skip
    assert "SUPUESTO_DECLARADO" in alertas["AL-1"]["Umbral"]
    filas = {f["Partida"]: f for f in control.filas_de_reproyeccion(resultado)}
    assert filas["OB-A"]["Indice"] == "0.9000" and filas["OB-C"]["Nota"].startswith("sin evidencia")
    assert filas["OB-C"]["Fin (dia habil)"] == "22.50"


def test_las_opciones_se_calculan_a_pedido_y_elegir_una_crea_la_version(obra):
    ob.registrar_v01_y_v02(obra)
    catalogo = Catalogo(obra)
    resultado = control.calcular_el_control(
        obra, ob.NOMBRE, catalogo, precios=ob.precios_del_corte()
    )
    todas = control.calcular_las_opciones(resultado)
    filas = {f["Opcion"]: f for f in control.filas_de_opciones(todas)}
    assert filas["Mas cuadrillas"]["Termino"] == "dia 17"
    assert filas["Mas cuadrillas"]["Costo directo adicional"] == "120.00"
    assert filas["Horas extra"]["Termino"] == "dia 21"
    assert filas["Partidas en paralelo"]["Nota"].startswith("ninguna partida sin empezar")
    assert filas["Aceptar el retraso"]["Costo indirecto"] == "90.00"
    assert "eta de cuadrillas: 0.80 (SUPUESTO_DECLARADO)" in filas["Mas cuadrillas"]["Nota"]
    version = control.elegir_opcion(
        obra, resultado, todas[0], catalogo, fuente="decision ficticia", responsable="Ing."
    )
    assert version == "OB-002"
    (decision,) = control.filas_de_decisiones(obra, ob.NOMBRE)
    assert (decision["Version"], decision["Opcion"], decision["Termino"]) == (
        "OB-002", "cuadrillas", "2026-11-24",
    )  # fmt: skip


def test_elegir_sin_fuente_se_rechaza_y_no_deja_version(obra):
    ob.registrar_v01_y_v02(obra)
    catalogo = Catalogo(obra)
    resultado = control.calcular_el_control(
        obra, ob.NOMBRE, catalogo, precios=ob.precios_del_corte()
    )
    todas = control.calcular_las_opciones(resultado)
    with pytest.raises(control.ControlInvalido, match="obligatoria"):
        control.elegir_opcion(obra, resultado, todas[0], catalogo, fuente="", responsable="Ing.")
    assert obra.scalar(select(func.count()).select_from(models.Presupuesto)) == 1


def test_un_limite_legal_o_un_numero_ilegible_en_las_opciones_se_rechaza(obra):
    ob.registrar_v01_y_v02(obra)
    resultado = control.calcular_el_control(
        obra, ob.NOMBRE, Catalogo(obra), precios=ob.precios_del_corte()
    )
    with pytest.raises(control.ControlInvalido, match="objetivo"):
        control.calcular_las_opciones(resultado, objetivo="veinte")
    with pytest.raises(control.ControlInvalido, match="horas extra previas"):
        control.calcular_las_opciones(resultado, horas_previas="muchas")
    assert control.calcular_las_opciones(resultado, objetivo="25")[0].aplica is False


def test_anular_y_el_costo_real_desde_los_textos(obra):
    primera, _ = ob.registrar_v01_y_v02(obra)
    control.anular(obra, primera.id, motivo="error de medicion", responsable="Ing.")
    assert obra.scalar(select(func.count()).select_from(models.AnulacionValuacion)) == 1
    with pytest.raises(control.ControlInvalido, match="ya esta anulada"):
        control.anular(obra, primera.id, motivo="otra vez", responsable="Ing.")
    control.registrar_costo_real(
        obra, ob.NOMBRE, monto="12.50", moneda="USD", fecha="2026-11-13", fuente="factura",
        responsable="Ing.", partida="OB-A",
    )  # fmt: skip
    with pytest.raises(control.ControlInvalido, match="monto"):
        control.registrar_costo_real(
            obra,
            ob.NOMBRE,
            monto="mucho",
            moneda="USD",
            fecha="2026-11-13",
            fuente="f",
            responsable="I",
        )


def test_importar_el_xlsx_de_ob_s2_con_informe_previo(obra):
    lectura = control.leer_excel(ob.RUTA_XLSX)
    assert lectura.informe[0] == "Valuaciones: 2 valuacion(es)"
    assert control.importar_excel(obra, ob.NOMBRE, lectura, fuente="XLSX", responsable="Ing.") == 2
    with pytest.raises(control.ControlInvalido, match="ya estan registradas"):
        control.importar_excel(obra, ob.NOMBRE, lectura, fuente="XLSX", responsable="Ing.")


def test_un_archivo_malo_se_rechaza_con_control_invalido(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text("a\n", encoding="utf-8")
    with pytest.raises(control.ControlInvalido, match="libro .xlsx"):
        control.leer_excel(csv)


def test_los_precios_del_corte_segun_el_metodo_elegido(obra):
    ob.registrar_v01_y_v02(obra)
    rz.sembrar_revaloracion(obra)
    catalogo = Catalogo(obra)
    assert control.versiones_revaloradas(obra, ob.NOMBRE) == ["OB-R01"]
    assert control.versiones_para_la_linea_base(obra, ob.NOMBRE)[-1] == "OB-001"
    ninguno = control.precios_del_corte(obra, ob.NOMBRE, catalogo, control.PrecioElegido(), "costo")
    assert ninguno is None
    comprobacion = control.precios_del_corte(
        obra, ob.NOMBRE, catalogo,
        control.PrecioElegido(control.METODOS_DE_PRECIOS[1], version="OB-R01"), "costo",
    )  # fmt: skip
    assert comprobacion.unitarios["OB-C"] == D("22.10")
    declarada = control.PrecioElegido(
        control.METODOS_DE_PRECIOS[2], km="1.10", r="0.10", fuente="S1"
    )
    escalatoria = control.precios_del_corte(obra, ob.NOMBRE, catalogo, declarada, "costo")
    assert escalatoria.unitarios["OB-A"] == D(10) * (1 + D("0.10") * D("0.90"))
    for elegido, mensaje in (
        (control.PrecioElegido(control.METODOS_DE_PRECIOS[1]), "elija la version"),
        (control.PrecioElegido(control.METODOS_DE_PRECIOS[1], version="NO-HAY"), "NO-HAY"),
        (control.PrecioElegido(control.METODOS_DE_PRECIOS[2], km="1.1"), "fuente"),
        (control.PrecioElegido(control.METODOS_DE_PRECIOS[2], km="x", fuente="S1"), "Km"),
    ):
        with pytest.raises(control.ControlInvalido, match=mensaje):
            control.precios_del_corte(obra, ob.NOMBRE, catalogo, elegido, "costo")


def test_las_tres_hojas_del_excel_de_la_hoja_conservan_las_propias(obra, tmp_path):
    ob.registrar_v01_y_v02(obra)
    resultado = ob.elaborar_ob_s2()
    # Sin decisiones ni valuaciones raras: las tres hojas, con sus encabezados.
    tablas = control.tablas_de_control(
        obra, ob.NOMBRE, Catalogo(obra), precios=ob.precios_del_corte()
    )
    assert [t.titulo for t in tablas] == ["Valuaciones", "Valor ganado", "Decisiones"]
    ruta = exportar_hoja(
        resultado.presupuesto, resultado.informe, tmp_path / "hoja.xlsx", ob.PARAMETROS,
        hojas_extra=tablas,
    )  # fmt: skip
    libro = openpyxl.load_workbook(ruta)
    propias = {HOJA_PRESUPUESTO, HOJA_APU, PESTANA_PLAN, PESTANA_EQUILIBRIO, HOJA_AUDITORIA}
    assert propias <= set(libro.sheetnames)
    assert {"Valuaciones", "Valor ganado", "Decisiones"} <= set(libro.sheetnames)
    assert [c.value for c in libro["Valuaciones"][1]][:3] == ["Numero", "Desde", "Hasta"]
    assert libro["Valuaciones"].max_row == 4  # encabezado + A 40, A 50, B 60


def test_sin_linea_base_o_sin_valuaciones_no_hay_hojas_extra(obra_sin_linea_base, obra):
    assert control.tablas_de_control(obra, ob.NOMBRE, Catalogo(obra)) == []


def test_un_inspector_con_formula_viaja_como_texto_al_excel(obra, tmp_path):
    ob.registrar(obra, {**ob.V01, "inspector": '=HYPERLINK("http://127.0.0.1:9/robo")'})
    tablas = control.tablas_de_control(obra, ob.NOMBRE, Catalogo(obra))
    resultado = ob.elaborar_ob_s2()
    ruta = exportar_hoja(
        resultado.presupuesto, resultado.informe, tmp_path / "hoja.xlsx", ob.PARAMETROS,
        hojas_extra=tablas,
    )  # fmt: skip
    celda = openpyxl.load_workbook(ruta)["Valuaciones"]["E2"]
    assert celda.data_type == "s" and celda.value.startswith("=HYPERLINK")
```
  Las reglas de arquitectura de S2 en su propio archivo (RV-2). Copian la tupla de prohibiciones de `ui/hoja.py` y una segunda prueba ata la copia a la regla original por su contenido (RP7-15: un módulo de prueba no importa a otro). En esta tarea la lista de pantallas solo trae `ui/control.py`; la página llega en la tarea 13:
```python
# tests/unit/test_arquitectura_s2.py
"""Reglas de arquitectura de S2 en su propio archivo (RV-2), con los ayudantes compartidos de
`tests/fixtures/arquitectura.py` (sección B, Tarea 1).

* `ui/control.py` no pinta: ni Streamlit, ni `pandas`, ni `ui.caso` (la misma regla que
  `PROHIBIDOS_EN_UI["ui/hoja.py"]` de `test_arquitectura.py`; un módulo de prueba no importa de
  otro, así que aquí se declara y la prueba lo ata a la regla de `ui/hoja.py` por su contenido);
* `valor_ganado`, `calendario` y las opciones de recuperación son puras: sin `sqlalchemy` ni
  `core.models`; la decisión, que escribe, vive en `decision.py`;
* `core/verification/valuaciones.py` no importa `core.budget` (la capa de reglas queda debajo);
* ningún módulo de S2 emite `UPDATE` ni `DELETE` sobre las tablas solo-agregar (S2-R10);
* ninguna pantalla de S2 importa `scripts` ni `tests` al cargar (RV-25) ni usa HTML sin escapar
  (RV-14).
"""

from __future__ import annotations

import re

import pytest

from tests.fixtures.arquitectura import RAIZ, importaciones

PROHIBIDOS_EN_UI_CONTROL = ("streamlit", "pandas", "ui.caso")
PUROS = (
    "core/budget/valor_ganado.py",
    "core/budget/calendario.py",
    "core/budget/recuperacion.py",
)
SOLO_AGREGAR = (
    "core/budget/valuaciones.py",
    "core/budget/puente.py",
    "core/budget/decision.py",
)
PAGINAS_DE_S2 = ("ui/control.py", "ui/paginas/control.py")


def _coincide(modulo: str, prefijo: str) -> bool:
    return modulo == prefijo or modulo.startswith(prefijo + ".")


def test_ui_control_no_pinta_ni_lee_la_sesion_de_streamlit():
    prohibidos = {
        modulo
        for modulo in importaciones(RAIZ / "ui" / "control.py")
        for prefijo in PROHIBIDOS_EN_UI_CONTROL
        if _coincide(modulo, prefijo)
    }
    assert prohibidos == set()


def test_la_regla_de_ui_control_es_la_misma_que_la_de_ui_hoja():
    """Si la regla de `ui/hoja.py` cambia, la de `ui/control.py` se revisa junto con ella."""
    texto = (RAIZ / "tests" / "unit" / "test_arquitectura.py").read_text(encoding="utf-8")
    regla = re.search(r'"ui/hoja\.py": \(([^)]*)\)', texto)
    assert regla is not None
    assert tuple(re.findall(r'"([^"]+)"', regla.group(1))) == PROHIBIDOS_EN_UI_CONTROL


@pytest.mark.parametrize("modulo", PUROS)
def test_los_calculos_de_s2_son_puros_sin_base_de_datos(modulo):
    prohibidos = {
        m
        for m in importaciones(RAIZ / modulo)
        if _coincide(m, "sqlalchemy") or _coincide(m, "core.models") or _coincide(m, "core.catalog")
    }
    assert prohibidos == set()


def test_las_reglas_r13_y_r14_no_dependen_de_la_capa_de_presupuesto():
    importados = importaciones(RAIZ / "core" / "verification" / "valuaciones.py")
    assert {m for m in importados if _coincide(m, "core.budget")} == set()
    assert {m for m in importados if _coincide(m, "sqlalchemy")} == set()


@pytest.mark.parametrize("modulo", SOLO_AGREGAR)
def test_ningun_modulo_de_s2_borra_ni_actualiza_las_tablas_solo_agregar(modulo):
    texto = (RAIZ / modulo).read_text(encoding="utf-8")
    assert not re.search(r"\.delete\(|\bdelete\(|\bupdate\(|\.update\(", texto)
    assert "from sqlalchemy import" not in texto or not re.search(
        r"from sqlalchemy import[^\n]*\b(delete|update)\b", texto
    )


@pytest.mark.parametrize("modulo", PAGINAS_DE_S2)
def test_las_pantallas_de_s2_no_importan_scripts_ni_tests_ni_usan_html_sin_escapar(modulo):
    texto = (RAIZ / modulo).read_text(encoding="utf-8")
    assert "unsafe_allow_html" not in texto
    assert not {m for m in importaciones(RAIZ / modulo) if m.split(".")[0] in ("scripts", "tests")}


def test_ningun_contrato_importa_nada_de_s2():
    for archivo in sorted((RAIZ / "core" / "contracts").glob("*.py")):
        assert not {
            m for m in importaciones(archivo) if _coincide(m, "core.budget") or "valuaciones" in m
        }, archivo.name
```
  UC-18 enmendado (RF-72): la pantalla de reajuste calcula en memoria y guarda con lo ejecutado de las valuaciones, que el estudio cita (reconocido de noviembre 75,90):
```python
# tests/integration/test_ui_reajuste_valuaciones.py
"""UC-18 enmendado por S2 (RF-72): la pantalla de reajuste toma lo ejecutado de las valuaciones.

`ui.reajuste.periodos_desde_valuaciones` calcula en memoria y `guardar_con_valuaciones` guarda el
estudio citando cada valuación. El monto reconocido de noviembre es 75,90 (memoria OB-S2).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core import models
from core.budget.puente import valuaciones_citadas
from core.budget.reajuste import cargar_estudio
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz
from ui import reajuste
from ui.hoja import HojaInvalida

D = Decimal
FILAS = [
    {"desde": "2026-11-01", "hasta": "2026-11-30", "version_comprobacion": rz.REVALORADA,
     "excepcion": ""},
    {"desde": "", "hasta": "", "version_comprobacion": "", "excepcion": ""},
]  # fmt: skip


@pytest.fixture
def con_valuaciones(obra):
    rz.sembrar_revaloracion(obra)
    ob.registrar_v01_y_v02(obra)
    return obra


def test_los_periodos_salen_de_las_valuaciones_sin_escribir_nada(con_valuaciones):
    antes = con_valuaciones.scalar(select(func.count()).select_from(models.CitaValuacion))
    periodos = reajuste.periodos_desde_valuaciones(con_valuaciones, ob.NOMBRE, FILAS)
    assert len(periodos) == 1
    ejecutado = periodos[0].ejecutado
    assert {e.codigo: e.cantidad for e in ejecutado} == {"OB-A": D(90), "OB-B": D(60)}
    assert [e.fuente for e in ejecutado] == ["valuaciones V-01, V-02", "valuaciones V-02"]
    despues = con_valuaciones.scalar(select(func.count()).select_from(models.CitaValuacion))
    assert antes == despues == 0


def test_el_calculo_en_memoria_da_el_reconocido_de_la_memoria(con_valuaciones):
    periodos = reajuste.periodos_desde_valuaciones(con_valuaciones, ob.NOMBRE, FILAS)
    resultado = reajuste.calcular(
        con_valuaciones, ob.NOMBRE, ob.CODIGO, rz.CLAUSULA, periodos,
        fecha_calculo=date(2026, 11, 13),
    )  # fmt: skip
    assert resultado.periodos[0].reconocido == rz.RECONOCIDO_DE_NOVIEMBRE


def test_guardar_con_valuaciones_cita_cada_una_y_confirma(con_valuaciones):
    id_estudio = reajuste.guardar_con_valuaciones(
        con_valuaciones, ob.NOMBRE, ob.CODIGO, rz.CLAUSULA, FILAS,
        fecha_calculo=date(2026, 11, 13), fuente="estudio ficticio", responsable="Ing.",
    )  # fmt: skip
    periodo = cargar_estudio(con_valuaciones, id_estudio).resultado.periodos[0]
    assert periodo.reconocido == D("75.90")
    assert valuaciones_citadas(con_valuaciones, id_estudio) == {0: ["V-01", "V-02"]}


def test_guardar_sin_fuente_se_rechaza_y_no_deja_estudio(con_valuaciones):
    with pytest.raises(HojaInvalida, match="No se guardo el estudio"):
        reajuste.guardar_con_valuaciones(
            con_valuaciones, ob.NOMBRE, ob.CODIGO, rz.CLAUSULA, FILAS,
            fecha_calculo=date(2026, 11, 13), fuente="", responsable="Ing.",
        )  # fmt: skip
    assert con_valuaciones.scalar(select(func.count()).select_from(models.EstudioReajuste)) == 0
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/integration/test_ui_control.py tests/unit/test_arquitectura_s2.py tests/integration/test_ui_reajuste_valuaciones.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'control' from 'ui'`
```bash
git add tests/integration/test_ui_control.py tests/unit/test_arquitectura_s2.py tests/integration/test_ui_reajuste_valuaciones.py
git commit -m "test(ui): ui.control, reglas de arquitectura de S2 y reajuste con valuaciones en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
```python
# ui/control.py
"""Control de obra sin Streamlit (UC-19 y UC-20; spec S2 §5.5).

Lo que la pantalla «Control de obra» necesita del núcleo: declarar la línea base de control,
registrar una valuación a mano o desde un XLSX, anularla, anotar costos reales, calcular al corte el
valor ganado, la separación del desvío, las alertas y la reproyección **siempre**, calcular las
opciones de recuperación **a pedido** y elegir una, y armar las hojas «Valuaciones», «Valor ganado»
y «Decisiones» del Excel de la hoja (`hojas_extra`).

Cada función que escribe confirma su transacción o la deshace (`rollback`) y levanta
`ControlInvalido` con un mensaje en español, sin *traceback*. Los textos que vienen de fuera
(inspector, observación y fuente de un XLSX) los muestra la página con `ui.texto_seguro` o en
celdas (RV-14). Los montos se presentan a dos decimales y los índices a cuatro, que es donde se
redondea. Sin Streamlit, sin `pandas` y sin `ui.caso`; lo vigila
`tests/unit/test_arquitectura_s2.py`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core import models
from core.budget.calendario import dia_habil
from core.budget.control import (
    ResultadoControl,
    calcular_control,
    composiciones_de_la_linea_base,
    construir_estado,
    contexto_de_recuperacion,
    costo_real_al_corte,
    guardar_parametros,
    parametros_de_control,
    precios_del_corte_de_version,
)
from core.budget.decision import aplicar_decision, decisiones
from core.budget.excel import TablaExportable
from core.budget.recuperacion import Opcion, opciones
from core.budget.valor_ganado import (
    ParametrosControl,
    PreciosDelCorte,
    indicadores,
    precios_por_escalatoria,
)
from core.budget.valuaciones import (
    Calendario,
    LecturaControl,
    LineaBaseInvalidada,
    anular_valuacion,
    instantanea_control,
    leer_valuaciones_excel,
    linea_base_vigente,
    registrar_costo,
    registrar_lectura,
    registrar_linea_base,
    registrar_valuacion,
    tabla_valuaciones,
    valuaciones_registradas,
)
from core.catalog import Catalogo
from core.catalog.indices import TasaNoDisponible, tasa_aplicable
from core.catalog.moneda import convertir
from core.verification.texto import formatear_decimal
from core.verification.valuaciones import LineaValuacion

__all__ = [
    "COLUMNAS_ALERTAS",
    "COLUMNAS_DECISIONES",
    "COLUMNAS_INDICADORES",
    "COLUMNAS_LINEAS",
    "COLUMNAS_OPCIONES",
    "COLUMNAS_PARAMETROS",
    "COLUMNAS_REPROYECCION",
    "COLUMNAS_VALUACIONES",
    "METODOS_DE_PRECIOS",
    "PARAMETROS_EDITABLES",
    "ControlInvalido",
    "PrecioElegido",
    "alertas_en_filas",
    "corte_por_defecto",
    "describir_linea_base",
    "dia_con_fecha",
    "estudios_que_suma",
    "filas_del_plan_reproyectado",
    "hay_valuaciones",
    "parametros_actuales",
    "texto_monto",
    "tiene_linea_base",
    "valuaciones_para_anular",
    "anular",
    "calcular_el_control",
    "calcular_las_opciones",
    "curva_pv_ev_ac",
    "declarar_linea_base",
    "elegir_opcion",
    "estado_de_valuaciones",
    "filas_de_decisiones",
    "filas_de_parametros",
    "filas_de_indicadores",
    "filas_de_opciones",
    "filas_de_reproyeccion",
    "filas_de_valuaciones",
    "guardar_los_parametros",
    "importar_excel",
    "leer_excel",
    "lineas_desde_filas",
    "parametros_desde_filas",
    "precios_del_corte",
    "registrar_costo_real",
    "registrar_y_controlar",
    "tablas_de_control",
    "versiones_para_la_linea_base",
    "versiones_revaloradas",
]

METODO_NINGUNO = "Sin precios del corte"
METODO_COMPROBACION = "Comprobacion directa (version revalorada)"
METODO_ESCALATORIA = "Escalatoria (un Km declarado)"
METODOS_DE_PRECIOS = (METODO_NINGUNO, METODO_COMPROBACION, METODO_ESCALATORIA)
COLUMNAS_LINEAS = ("Partida", "Cantidad", "Fecha de medicion", "Observacion")
COLUMNAS_VALUACIONES = ("Numero", "Periodo", "Fecha", "Inspector", "Registrada", "Estado")
COLUMNAS_INDICADORES = ("Indicador", "Valor", "En la otra moneda", "Nota")
COLUMNAS_ALERTAS = ("Alerta", "Severidad", "Descripcion", "Observado", "Umbral")
COLUMNAS_REPROYECCION = ("Partida", "Indice", "Fin (dia habil)", "Nota")
COLUMNAS_OPCIONES = (
    "Opcion",
    "Termino",
    "Retraso (dias)",
    "Costo directo adicional",
    "Costo indirecto",
    "Penalizacion",
    "Punto de equilibrio",
    "Nota",
)
COLUMNAS_DECISIONES = ("Version", "Opcion", "Corte", "Termino", "Fuente", "Responsable")
NO_DISPONIBLE = "no disponible"
NO_APLICA = "no aplica"
NATURALEZA_SUPUESTO = "SUPUESTO_DECLARADO"
NATURALEZA_DATO = "DATO_DEL_CONTRATO"


class ControlInvalido(ValueError):  # noqa: N818
    """Algo del control no se pudo hacer; el mensaje dice qué pasó y cómo arreglarlo."""


def _monto(valor: Decimal | None) -> str:
    return NO_DISPONIBLE if valor is None else formatear_decimal(valor, 2)


def _indice(valor: Decimal | None) -> str:
    return NO_APLICA if valor is None else formatear_decimal(valor, 4)


def _fecha(texto: str, que: str) -> date:
    try:
        return date.fromisoformat(texto.strip()[:10])
    except ValueError:
        raise ControlInvalido(f"{que}: {texto!r} no es una fecha (AAAA-MM-DD)") from None


def _decimal(texto: str, que: str) -> Decimal:
    try:
        valor = Decimal(str(texto).strip())
    except InvalidOperation:
        raise ControlInvalido(f"{que}: {texto!r} no es un numero decimal") from None
    if not valor.is_finite():
        raise ControlInvalido(f"{que}: {texto!r} no es un numero finito")
    return valor


def _escribir(sesion: Session, accion):
    """Corre `accion`, confirma si sale bien y deshace si no; todo error sale como
    `ControlInvalido`."""
    try:
        resultado = accion()
        sesion.commit()
        return resultado
    except ControlInvalido:
        sesion.rollback()
        raise
    except LineaBaseInvalidada as error:
        sesion.rollback()
        raise ControlInvalido(str(error)) from error
    except (ValueError, KeyError) as error:
        sesion.rollback()
        raise ControlInvalido(
            str(error.args[0] if isinstance(error, KeyError) else error)
        ) from error
    except SQLAlchemyError as error:
        sesion.rollback()
        raise ControlInvalido(
            f"No se pudo escribir en el caso: {getattr(error, 'orig', error)}"
        ) from error


# ---------------------------------------------------------------------------------------------
# Línea base, valuaciones, anulación y costos (UC-19)
# ---------------------------------------------------------------------------------------------


def versiones_para_la_linea_base(sesion: Session, proyecto: str) -> list[str]:
    """Los códigos de las versiones guardadas del proyecto, de la más reciente a la más antigua."""
    return list(
        sesion.scalars(
            select(models.Presupuesto.codigo)
            .join(models.Proyecto)
            .where(models.Proyecto.nombre == proyecto)
            .order_by(models.Presupuesto.id.desc())
        )
    )


def versiones_revaloradas(sesion: Session, proyecto: str) -> list[str]:
    """Las versiones revaloradas por UC-02: las que sirven para los precios del corte."""
    return list(
        sesion.scalars(
            select(models.Presupuesto.codigo)
            .join(models.Proyecto)
            .join(
                models.VersionOrigen, models.VersionOrigen.presupuesto_id == models.Presupuesto.id
            )
            .where(
                models.Proyecto.nombre == proyecto, models.VersionOrigen.motivo == "revaloracion"
            )
            .order_by(models.Presupuesto.id.desc())
        )
    )


def declarar_linea_base(
    sesion: Session,
    proyecto: str,
    version: str,
    *,
    desde: str,
    perspectiva: str,
    inicio: str,
    dias_por_periodo: str,
    feriados: str,
    fuente: str,
    responsable: str,
) -> None:
    """Declara la línea base de control (RF-72) desde los textos de la pantalla. Los feriados van
    separados por comas o saltos de línea, en AAAA-MM-DD."""
    dias = _decimal(dias_por_periodo, "dias por periodo")
    if dias != dias.to_integral_value():
        raise ControlInvalido(f"dias por periodo: {dias_por_periodo!r} debe ser un entero")
    lista = [parte for parte in feriados.replace("\n", ",").split(",") if parte.strip()]

    def accion():
        return registrar_linea_base(
            sesion,
            proyecto,
            version,
            desde=_fecha(desde, "desde"),
            perspectiva=perspectiva,
            calendario=Calendario(
                _fecha(inicio, "fecha de inicio"),
                int(dias),
                tuple(_fecha(dia, "feriado") for dia in lista),
            ),
            fuente=fuente,
            responsable=responsable,
        )

    _escribir(sesion, accion)


def lineas_desde_filas(filas: Sequence[Mapping[str, object]]) -> list[LineaValuacion]:
    """Las líneas de la tabla de la pantalla (`COLUMNAS_LINEAS`) como líneas de valuación. Una fila
    sin partida y sin cantidad se ignora; una cantidad ilegible o negativa se rechaza con su
    fila."""
    lineas: list[LineaValuacion] = []
    for numero, fila in enumerate(filas, start=1):
        partida = str(fila.get("Partida") or "").strip()
        cantidad = str(fila.get("Cantidad") or "").strip()
        if not partida and not cantidad:
            continue
        if not partida:
            raise ControlInvalido(f"fila {numero}: falta la partida")
        medicion = str(fila.get("Fecha de medicion") or "").strip()
        try:
            lineas.append(
                LineaValuacion(
                    partida,
                    _decimal(cantidad, f"fila {numero}, cantidad"),
                    _fecha(medicion, f"fila {numero}, fecha de medicion") if medicion else None,
                    str(fila.get("Observacion") or "").strip(),
                )
            )
        except ValueError as error:
            raise ControlInvalido(f"fila {numero}: {error}") from None
    return lineas


def registrar_y_controlar(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    *,
    numero: str,
    desde: str,
    hasta: str,
    fecha: str,
    inspector: str,
    filas: Sequence[Mapping[str, object]],
    fuente: str,
    responsable: str,
    precios: PreciosDelCorte | None = None,
) -> ResultadoControl:
    """UC-19 4 y 5: registra la valuación y calcula al corte (su fecha *hasta*) el informe de
    control, los indicadores, las alertas y la reproyección. Es lo que mide RNF-15."""
    fin = _fecha(hasta, "hasta")

    def accion():
        registrar_valuacion(
            sesion,
            proyecto,
            numero=numero,
            desde=_fecha(desde, "desde"),
            hasta=fin,
            fecha=_fecha(fecha, "fecha") if fecha.strip() else None,
            inspector=inspector,
            lineas=lineas_desde_filas(filas),
            fuente=fuente,
            responsable=responsable,
        )

    _escribir(sesion, accion)
    return calcular_el_control(sesion, proyecto, catalogo, corte=fin, precios=precios)


def anular(sesion: Session, valuacion_id: int, *, motivo: str, responsable: str) -> None:
    """Anula una valuación (UC-19 4c): se conserva y deja de contar."""
    _escribir(
        sesion,
        lambda: anular_valuacion(sesion, valuacion_id, motivo=motivo, responsable=responsable),
    )


def registrar_costo_real(
    sesion: Session,
    proyecto: str,
    *,
    monto: str,
    moneda: str,
    fecha: str,
    fuente: str,
    responsable: str,
    partida: str = "",
) -> None:
    """Anota un costo real (monto, moneda, fecha y fuente); se convierte al calcular."""
    _escribir(
        sesion,
        lambda: registrar_costo(
            sesion,
            proyecto,
            monto=_decimal(monto, "monto"),
            moneda=moneda,
            fecha=_fecha(fecha, "fecha"),
            fuente=fuente,
            responsable=responsable,
            codigo_partida=partida.strip() or None,
        ),
    )


def leer_excel(ruta: Path) -> LecturaControl:
    """Lee un XLSX de valuaciones sin escribir nada (informe previo). `ControlInvalido` si se
    rechaza: el archivo se rechaza entero."""
    try:
        return leer_valuaciones_excel(ruta)
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def importar_excel(
    sesion: Session, proyecto: str, lectura: LecturaControl, *, fuente: str, responsable: str
) -> int:
    """Registra lo leído (todas las valuaciones y costos, o ninguno) y devuelve cuántas son."""
    registradas, _ = _escribir(
        sesion,
        lambda: registrar_lectura(
            sesion, proyecto, lectura, fuente=fuente, responsable=responsable
        ),
    )
    return len(registradas)


# ---------------------------------------------------------------------------------------------
# Cálculo (UC-20 1 a 3, siempre) y opciones (UC-20 4 a 6, a pedido)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PrecioElegido:
    """Cómo se toman los precios del corte (S2 §4.3): ninguno, una versión revalorada
    (comprobación directa) o la escalatoria con un solo `Km` y `R` declarados. Son textos de la
    pantalla."""

    metodo: str = METODO_NINGUNO
    version: str = ""
    km: str = ""
    r: str = "0"
    fuente: str = ""


def precios_del_corte(
    sesion: Session, proyecto: str, catalogo: Catalogo, elegido: PrecioElegido, perspectiva: str
) -> PreciosDelCorte | None:
    """Los `PreciosDelCorte` que corresponden a la elección, o `None` si no se eligió ninguno."""
    if elegido.metodo == METODO_COMPROBACION:
        if not elegido.version:
            raise ControlInvalido("elija la version revalorada para la comprobacion directa")
        try:
            return precios_del_corte_de_version(
                sesion, proyecto, elegido.version, perspectiva, catalogo
            )
        except (KeyError, ValueError) as error:
            raise ControlInvalido(str(error.args[0])) from None
    if elegido.metodo == METODO_ESCALATORIA:
        if not elegido.fuente.strip():
            raise ControlInvalido("la escalatoria necesita la fuente de Km y R")
        base = instantanea_control(sesion, proyecto, catalogo=catalogo).presupuesto
        unitarios = {
            p.item.codigo_partida: (
                p.resultado.costo_directo if perspectiva == "costo" else p.resultado.precio_unitario
            )
            for p in base.partidas
        }
        km = _decimal(elegido.km, "Km")
        try:
            return precios_por_escalatoria(
                unitarios, dict.fromkeys(unitarios, km), _decimal(elegido.r, "R"), elegido.fuente
            )
        except ValueError as error:
            raise ControlInvalido(str(error)) from None
    return None


def calcular_el_control(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    *,
    corte: date | None = None,
    precios: PreciosDelCorte | None = None,
) -> ResultadoControl:
    """El control al corte (sin escribir). `ControlInvalido` si no hay línea base, si está
    invalidada por un cambio de moneda o si no hay valuaciones ni corte."""
    try:
        return calcular_control(sesion, proyecto, catalogo=catalogo, corte=corte, precios=precios)
    except LineaBaseInvalidada as error:
        raise ControlInvalido(str(error)) from error
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def calcular_las_opciones(
    resultado: ResultadoControl,
    *,
    objetivo: str = "",
    horas_previas: str = "0",
    independientes: str = "",
) -> tuple[Opcion, ...]:
    """Las cuatro opciones de recuperación a pedido (UC-20 4). `objetivo` es el día hábil objetivo
    (vacío = el fin del plan base). `ControlInvalido` si un límite legal se rompe."""
    try:
        contexto = contexto_de_recuperacion(
            resultado,
            composiciones_de_la_linea_base(resultado),
            objetivo=int(_decimal(objetivo, "objetivo")) if objetivo.strip() else None,
            horas_previas=_decimal(horas_previas or "0", "horas extra previas"),
        )
        return opciones(contexto)
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def elegir_opcion(
    sesion: Session,
    resultado: ResultadoControl,
    opcion: Opcion,
    catalogo: Catalogo,
    *,
    fuente: str,
    responsable: str,
    declaracion_independencia: str = "",
) -> str:
    """UC-20 5 y 6: crea la versión de la opción elegida y guarda la decisión. Devuelve el código de
    la versión nueva."""
    decision = _escribir(
        sesion,
        lambda: aplicar_decision(
            sesion,
            resultado,
            opcion,
            catalogo=catalogo,
            fuente=fuente,
            responsable=responsable,
            declaracion_independencia=declaracion_independencia,
        ),
    )
    return sesion.get(models.Presupuesto, decision.version_resultante_id).codigo


# ---------------------------------------------------------------------------------------------
# Tablas para la pantalla y para el Excel
# ---------------------------------------------------------------------------------------------

_ORDEN = {"ERROR": 3, "ADVERTENCIA": 2, "INFO": 1}


def estado_de_valuaciones(resultado: ResultadoControl) -> dict[str, str]:
    """Por clave de valuación, el peor hallazgo de R13-R14 (columna Estado, como RF-55)."""
    peores: dict[str, tuple[int, str]] = {}
    for hallazgo in resultado.informe.hallazgos:
        clave = hallazgo.origen_ids[0].split(":")[1]
        rango = _ORDEN.get(hallazgo.severidad.name, 0)
        texto = f"{hallazgo.severidad.name}: {hallazgo.regla}"
        if clave not in peores or rango > peores[clave][0]:
            peores[clave] = (rango, texto)
    return {clave: texto for clave, (_, texto) in peores.items()}


def filas_de_valuaciones(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Las valuaciones guardadas, en solo lectura, con su fecha de registro y su Estado."""
    estados = estado_de_valuaciones(resultado)
    return [
        {
            "Numero": v.numero or f"#{v.id}",
            "Periodo": f"{v.desde.isoformat()} a {v.hasta.isoformat()}",
            "Fecha": "" if v.fecha is None else v.fecha.isoformat(),
            "Inspector": v.inspector,
            "Registrada": "" if v.fecha_hora is None else v.fecha_hora.strftime("%Y-%m-%d %H:%M"),
            "Estado": estados.get(v.clave, "sin hallazgos"),
        }
        for v in resultado.instantanea.valuaciones
    ]


def _otra_moneda(sesion: Session, resultado: ResultadoControl) -> tuple[str, Decimal | None]:
    """La moneda que no es la del proyecto y la tasa aplicable a la fecha del corte (S1)."""
    moneda = resultado.instantanea.moneda
    otra = "USD" if moneda == "Bs" else "Bs"
    try:
        return otra, tasa_aplicable(sesion, resultado.instantanea.corte).valor
    except TasaNoDisponible:
        return otra, None


def filas_de_indicadores(sesion: Session, resultado: ResultadoControl) -> list[dict[str, str]]:
    """La tabla de §4.2 y la separación de §4.3, cada monto en las dos monedas con la tasa del
    corte (S1); lo que no se puede calcular dice «no disponible» y por qué."""
    ind, sep = resultado.indicadores, resultado.separacion
    moneda = resultado.instantanea.moneda
    otra, tasa = _otra_moneda(sesion, resultado)

    def en_otra(valor: Decimal | None) -> str:
        if valor is None or tasa is None:
            return NO_DISPONIBLE
        return formatear_decimal(convertir(valor, moneda, otra, tasa), 2)

    def monto(nombre: str, valor: Decimal | None, nota: str = "") -> dict[str, str]:
        return {
            "Indicador": f"{nombre} ({moneda})",
            "Valor": _monto(valor),
            "En la otra moneda": f"{en_otra(valor)} {otra}" if tasa is not None else NO_DISPONIBLE,
            "Nota": nota,
        }

    def indice(nombre: str, valor: Decimal | None, nota: str = "") -> dict[str, str]:
        return {"Indicador": nombre, "Valor": _indice(valor), "En la otra moneda": "", "Nota": nota}

    no = ind.no_disponible
    filas = [
        monto("BAC", ind.bac),
        monto("PV", ind.pv),
        monto("EV", ind.ev),
        monto("AC", ind.ac, no.get("AC", "")),
        monto("SV (plazo)", ind.sv),
        monto("CV", ind.cv, no.get("CV", "")),
        indice("SPI", ind.spi, no.get("SPI", "")),
        indice("CPI", ind.cpi, no.get("CPI", "")),
        monto("EAC (indice BAC/CPI)", ind.eac_indice, no.get("EAC", "")),
        monto("EAC (sistema)", ind.eac_sistema, no.get("EAC", "")),
        monto("VAC", ind.vac, no.get("VAC", "")),
        {
            "Indicador": "Termino por el indice (dia habil)",
            "Valor": NO_APLICA if ind.termino_indice is None else str(ind.termino_indice),
            "En la otra moneda": "",
            "Nota": "",
        },
        monto("Desvio de precio", sep.precio, sep.no_disponible.get("precio", "")),
        monto("Desvio de consumo", sep.consumo, sep.no_disponible.get("consumo", "")),
    ]
    if sep.metodo:
        filas.append(
            {
                "Indicador": "Metodo y fuente del precio del corte",
                "Valor": sep.metodo,
                "En la otra moneda": "",
                "Nota": sep.fuente,
            }
        )
    if tasa is None:
        filas.append(
            {
                "Indicador": "Tasa del corte",
                "Valor": NO_DISPONIBLE,
                "En la otra moneda": "",
                "Nota": "sin tasa aplicable a la fecha del corte (S1-R2)",
            }
        )
    return filas


def alertas_en_filas(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Las alertas que saltaron y, aparte, las que no se pudieron evaluar con su motivo."""
    filas = [
        {
            "Alerta": a.codigo,
            "Severidad": a.severidad.name,
            "Descripcion": a.descripcion,
            "Observado": ""
            if a.valor_observado is None
            else formatear_decimal(a.valor_observado, 4),
            "Umbral": ("" if a.umbral is None else formatear_decimal(a.umbral, 4))
            + f" ({a.naturaleza_umbral})",
        }
        for a in resultado.alertas.alertas
    ]
    filas.extend(
        {
            "Alerta": codigo,
            "Severidad": "sin evaluar",
            "Descripcion": motivo,
            "Observado": "",
            "Umbral": "",
        }
        for codigo, motivo in resultado.alertas.no_evaluadas.items()
    )
    return filas


def filas_de_reproyeccion(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Por partida con obra pendiente: su índice, el día hábil en que termina y su nota."""
    filas = []
    for p in resultado.reproyeccion.partidas:
        if p.pendiente == 0:
            continue
        nota = p.motivo or (
            "detenida"
            if p.detenida
            else "sin evidencia propia: SPI global"
            if p.sin_evidencia
            else ""
        )
        filas.append(
            {
                "Partida": p.codigo,
                "Indice": _indice(p.indice),
                "Fin (dia habil)": NO_DISPONIBLE if p.fin is None else formatear_decimal(p.fin, 2),
                "Nota": nota,
            }
        )
    return filas


def filas_de_opciones(todas: Sequence[Opcion]) -> list[dict[str, str]]:
    """Una fila por opción con su término, sus costos, su punto de equilibrio y sus supuestos."""
    filas = []
    for o in todas:
        if not o.aplica:
            filas.append(
                {"Opcion": o.titulo, "Nota": o.motivo}
                | dict.fromkeys(COLUMNAS_OPCIONES[1:-1], NO_APLICA)
            )
            continue
        pe = NO_APLICA
        if o.equilibrio is not None:
            pe = _monto(o.equilibrio.punto) + f" ({o.equilibrio.mensaje})"
        filas.append(
            {
                "Opcion": o.titulo,
                "Termino": f"dia {o.termino}",
                "Retraso (dias)": str(o.retraso),
                "Costo directo adicional": _monto(o.costo_directo_adicional),
                "Costo indirecto": _monto(o.costo_indirecto),
                "Penalizacion": _monto(o.penalizacion),
                "Punto de equilibrio": pe,
                "Nota": "; ".join(f"{s.nombre}: {s.valor} ({s.naturaleza})" for s in o.supuestos),
            }
        )
    return filas


def filas_de_decisiones(sesion: Session, proyecto: str) -> list[dict[str, str]]:
    """Las decisiones de recuperación del proyecto."""
    return [
        {
            "Version": d.version,
            "Opcion": d.opcion,
            "Corte": d.fecha_corte.isoformat(),
            "Termino": d.termino.isoformat(),
            "Fuente": d.fuente,
            "Responsable": d.responsable,
        }
        for d in decisiones(sesion, proyecto)
    ]


def tablas_de_control(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    *,
    precios: PreciosDelCorte | None = None,
) -> list[TablaExportable]:
    """Las hojas «Valuaciones», «Valor ganado» y «Decisiones» del Excel de la hoja (`hojas_extra`,
    SF-E4). Sin línea base de control (o sin valuaciones) no agrega ninguna: el Excel de la hoja
    conserva sus hojas y sale igual que antes."""
    try:
        resultado = calcular_control(sesion, proyecto, catalogo=catalogo, precios=precios)
    except (ValueError, LineaBaseInvalidada):
        return []
    anuladas = [
        v
        for v in valuaciones_registradas(sesion, proyecto, con_anuladas=True)
        if v.id not in {x.id for x in resultado.instantanea.valuaciones}
    ]
    valuaciones = tabla_valuaciones(
        resultado.instantanea.valuaciones,
        anuladas=anuladas,
        estados=estado_de_valuaciones(resultado),
    )
    filas = filas_de_indicadores(sesion, resultado) + alertas_en_filas(resultado)
    columnas = ("Indicador", "Valor", "En la otra moneda", "Nota")
    valor_ganado = TablaExportable(
        "Valor ganado",
        columnas,
        tuple(
            (
                f.get("Indicador") or f"{f['Alerta']} ({f['Severidad']})",
                f.get("Valor") or f.get("Observado", ""),
                f.get("En la otra moneda", ""),
                f.get("Nota") or f.get("Descripcion", ""),
            )
            for f in filas
        ),
    )
    decisiones_tabla = TablaExportable(
        "Decisiones",
        COLUMNAS_DECISIONES,
        tuple(
            tuple(f[c] for c in COLUMNAS_DECISIONES) for f in filas_de_decisiones(sesion, proyecto)
        ),
    )
    return [valuaciones, valor_ganado, decisiones_tabla]


# ---------------------------------------------------------------------------------------------
# Parámetros de control y la curva PV/EV/AC
# ---------------------------------------------------------------------------------------------

#: (campo, qué es, naturaleza): lo que la pestaña «Línea base» muestra de `ParametrosControl`.
PARAMETROS_EDITABLES = (
    ("spi_error", "SPI por debajo del cual el retraso es ERROR (AL-1)", NATURALEZA_SUPUESTO),
    ("cpi_error", "CPI por debajo del cual el sobrecosto es ERROR (AL-2)", NATURALEZA_SUPUESTO),
    (
        "retraso_error",
        "Retraso del termino, fraccion de D, que pasa a ERROR (AL-3)",
        NATURALEZA_SUPUESTO,
    ),
    ("precio_info", "Desvio de precio, fraccion del EV, que avisa (AL-5)", NATURALEZA_SUPUESTO),
    (
        "equilibrio_puntos",
        "Puntos porcentuales de subida del PE que advierten (AL-4)",
        NATURALEZA_SUPUESTO,
    ),
    ("eta_cuadrilla", "Eficiencia de cada cuadrilla adicional (eta)", NATURALEZA_SUPUESTO),
    ("cuadrillas_max", "Cuadrillas maximas por frente", NATURALEZA_SUPUESTO),
    ("eta_horas_extra", "Eficiencia de la hora extra (eta_he)", NATURALEZA_SUPUESTO),
    ("horas_extra_dia", "Horas extra por dia (tope legal 2)", NATURALEZA_SUPUESTO),
    ("recargo_horas_extra", "Recargo de las horas extra (minimo legal 0,50)", NATURALEZA_SUPUESTO),
    ("fcas_en_horas_extra", "FCAS sobre las horas extra (si o no)", NATURALEZA_SUPUESTO),
    ("penalizacion_diaria", "Penalizacion por dia de retraso del contrato", NATURALEZA_DATO),
    ("fuente_penalizacion", "Fuente de la penalizacion", NATURALEZA_DATO),
)
COLUMNAS_PARAMETROS = ("Parametro", "Que es", "Valor", "Naturaleza")


def filas_de_parametros(parametros: ParametrosControl) -> list[dict[str, str]]:
    """Los parámetros de control como filas de la pantalla; la columna `Valor` es la editable."""
    filas = []
    for campo, que_es, naturaleza in PARAMETROS_EDITABLES:
        valor = getattr(parametros, campo)
        texto = (
            ("si" if valor else "no")
            if isinstance(valor, bool)
            else format(valor, "f")
            if (isinstance(valor, Decimal))
            else str(valor)
        )
        filas.append(
            {"Parametro": campo, "Que es": que_es, "Valor": texto, "Naturaleza": naturaleza}
        )
    return filas


def parametros_desde_filas(filas: Sequence[Mapping[str, object]]) -> ParametrosControl:
    """Los `ParametrosControl` que describen las filas editadas. `ControlInvalido` si un valor
    no se lee o está fuera de rango (por ejemplo, `eta` fuera de (0, 1])."""
    valores = {str(f.get("Parametro")): str(f.get("Valor") or "").strip() for f in filas}
    muestra = ParametrosControl()
    leidos: dict[str, object] = {}
    for campo, _, _ in PARAMETROS_EDITABLES:
        if campo not in valores:
            raise ControlInvalido(f"falta el parametro {campo}")
        base = getattr(muestra, campo)
        texto = valores[campo]
        if isinstance(base, bool):
            if texto.lower() not in ("si", "no"):
                raise ControlInvalido(f"{campo}: escriba si o no")
            leidos[campo] = texto.lower() == "si"
        elif isinstance(base, int):
            numero = _decimal(texto, campo)
            if numero != numero.to_integral_value():
                raise ControlInvalido(f"{campo}: {texto!r} debe ser un entero")
            leidos[campo] = int(numero)
        elif isinstance(base, Decimal):
            leidos[campo] = _decimal(texto, campo)
        else:
            leidos[campo] = texto
    try:
        return ParametrosControl(**leidos)
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def guardar_los_parametros(
    sesion: Session,
    proyecto: str,
    filas: Sequence[Mapping[str, object]],
    *,
    fuente: str,
    responsable: str,
) -> int:
    """Guarda los parámetros editados con un `RegistroCambio` por valor que cambió; devuelve
    cuántos cambiaron."""
    nuevos = parametros_desde_filas(filas)
    return len(
        _escribir(
            sesion,
            lambda: guardar_parametros(
                sesion, proyecto, nuevos, fuente=fuente, responsable=responsable
            ),
        )
    )


def curva_pv_ev_ac(sesion: Session, resultado: ResultadoControl) -> list[dict[str, object]]:
    """PV, EV y AC al cierre de cada período hasta el corte (el último punto es el corte mismo),
    para la curva de la pestaña «Valor ganado». El AC es `None` donde algún costo no tiene tasa."""
    instantanea = resultado.instantanea
    calendario = instantanea.calendario
    feriados = frozenset(calendario.feriados)
    largo = calendario.dias_por_periodo
    etiquetas = resultado.estado.etiquetas
    hasta = -(-resultado.estado.dia // largo)
    puntos: list[dict[str, object]] = []
    for n in range(1, hasta + 1):
        cierre = dia_habil(calendario.fecha_inicio, n * largo, feriados)
        parcial = replace(instantanea, corte=min(cierre, instantanea.corte))
        costo, _ = costo_real_al_corte(sesion, parcial)
        estado = construir_estado(parcial, costo_real=costo, precios=resultado.estado.precios)
        calculados = indicadores(estado)
        puntos.append(
            {
                "Periodo": etiquetas[n - 1] if n <= len(etiquetas) else f"Periodo {n}",
                "PV": calculados.pv,
                "EV": calculados.ev,
                "AC": calculados.ac,
            }
        )
    return puntos


# ---------------------------------------------------------------------------------------------
# Consultas cortas para la pantalla
# ---------------------------------------------------------------------------------------------


def texto_monto(valor: Decimal | None) -> str:
    """Un monto a dos decimales para mostrar; `None` es «no disponible»."""
    return _monto(valor)


def tiene_linea_base(sesion: Session, proyecto: str) -> bool:
    """True si el proyecto tiene alguna línea base de control declarada."""
    return linea_base_vigente(sesion, proyecto, date.max) is not None


def describir_linea_base(sesion: Session, proyecto: str) -> str | None:
    """La línea base vigente hoy en una frase (versión, perspectiva, calendario), o `None`.
    La fuente es texto ajeno: la pantalla la escapa con `ui.texto_seguro`."""
    fila = linea_base_vigente(sesion, proyecto, date.max)
    if fila is None:
        return None
    version = sesion.get(models.Presupuesto, fila.presupuesto_id)
    calendario = fila.calendario
    return (
        f"version {version.codigo}, perspectiva {fila.perspectiva}, vigente desde "
        f"{fila.desde.isoformat()}; inicio de obra {calendario.fecha_inicio.isoformat()} con "
        f"{calendario.dias_por_periodo} dia(s) habil(es) por periodo"
    )


def hay_valuaciones(sesion: Session, proyecto: str) -> bool:
    """True si el proyecto tiene alguna valuación registrada (anulada o no)."""
    return bool(valuaciones_registradas(sesion, proyecto, con_anuladas=True))


def corte_por_defecto(sesion: Session, proyecto: str) -> date:
    """El *hasta* de la última valuación no anulada; hoy si no hay ninguna."""
    return max((v.hasta for v in valuaciones_registradas(sesion, proyecto)), default=date.today())


def valuaciones_para_anular(sesion: Session, proyecto: str) -> list[tuple[int, str]]:
    """`(id, rótulo)` de las valuaciones que cuentan y se pueden anular."""
    return [
        (v.id, f"{v.numero or '#' + str(v.id)} ({v.desde.isoformat()} a {v.hasta.isoformat()})")
        for v in valuaciones_registradas(sesion, proyecto)
    ]


def parametros_actuales(sesion: Session, proyecto: str) -> ParametrosControl:
    """Los parámetros de control del proyecto (los por defecto si no tiene fila)."""
    return parametros_de_control(sesion, proyecto)


def dia_con_fecha(resultado: ResultadoControl, dia: int | None) -> str:
    """«día N (AAAA-MM-DD)» en el calendario de la línea base; «no proyectable» si no hay día."""
    if dia is None:
        return "no proyectable"
    calendario = resultado.instantanea.calendario
    fecha = dia_habil(calendario.fecha_inicio, dia, frozenset(calendario.feriados))
    return f"dia {dia} ({fecha.isoformat()})"


def filas_del_plan_reproyectado(
    resultado: ResultadoControl,
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    """Las columnas (período y una por partida) y las filas del plan reproyectado."""
    codigos = [p.codigo for p in resultado.estado.partidas]
    filas = []
    for etiqueta, reparto in resultado.reproyeccion.plan:
        fila = {"Periodo": etiqueta, **dict.fromkeys(codigos, "")}
        fila.update({codigo: format(fraccion, ".4f") for codigo, fraccion in reparto})
        filas.append(fila)
    return ("Periodo", *codigos), filas


def estudios_que_suma(resultado: ResultadoControl) -> str:
    """Una frase con los estudios de reajuste de S1 que suma V' (S2-R15), o que no suma ninguno."""
    reajuste = resultado.reajuste
    if not reajuste.estudios:
        return "Sin estudio de reajuste guardado: V' = V. Nunca se proyecta un reajuste."
    detalle = ", ".join(
        f"#{e.id} ({e.fecha_calculo.isoformat()}, {_monto(e.monto)})" for e in reajuste.estudios
    )
    return (
        f"V' suma el reajuste reconocido de {len(reajuste.estudios)} estudio(s) de S1 guardado(s): "
        f"{detalle}; total {_monto(reajuste.monto)} {reajuste.moneda}."
    )
```
  La pantalla de reajuste de S1 calcula en memoria con `periodos_desde_valuaciones` y guarda con `guardar_con_valuaciones` (el estudio cita cada valuación en `cita_valuacion`):
```diff
--- a/ui/reajuste.py
+++ b/ui/reajuste.py
@@ -22,4 +22,5 @@
 from core import models
 from core.budget import TablaExportable, cargar_elaboracion, exportar_hoja
+from core.budget.puente import PeriodoDelEstudio, estudio_con_valuaciones, periodos_declarados
 from core.budget.reajuste import (
     Clausula,
@@ -220,4 +221,66 @@
 
 
+# --- lo ejecutado desde las valuaciones (S2, UC-18 enmendado) ------------------------------------
+
+
+def _periodos_del_estudio(periodos: Sequence[Mapping[str, str]]) -> list[PeriodoDelEstudio]:
+    return [
+        PeriodoDelEstudio(
+            _fecha(_texto(fila, "desde"), "desde"),
+            _fecha(_texto(fila, "hasta"), "hasta"),
+            _texto(fila, "version_comprobacion", obligatorio=False),
+            _texto(fila, "excepcion", obligatorio=False),
+        )
+        for fila in periodos
+        if _con_datos(fila)
+    ]
+
+
+def periodos_desde_valuaciones(
+    sesion, proyecto: str, periodos: Sequence[Mapping[str, str]]
+) -> list[PeriodoDeclarado]:
+    """Los periodos de la pantalla con lo ejecutado de las valuaciones registradas y no anuladas
+    (cada una al periodo que contiene su *hasta*; UC-18 enmendado, RF-72). No escribe nada."""
+    return periodos_declarados(sesion, proyecto, _periodos_del_estudio(periodos))
+
+
+def guardar_con_valuaciones(
+    sesion,
+    proyecto: str,
+    codigo: str,
+    clausula: Clausula,
+    periodos: Sequence[Mapping[str, str]],
+    *,
+    fecha_calculo: date,
+    fuente: str,
+    responsable: str,
+    reemplaza_a: int | None = None,
+) -> int:
+    """Como `guardar`, pero con lo ejecutado de las valuaciones, que el estudio cita. Confirma."""
+    try:
+        estudio = estudio_con_valuaciones(
+            sesion,
+            proyecto,
+            codigo,
+            clausula,
+            _periodos_del_estudio(periodos),
+            fecha_calculo=fecha_calculo,
+            fuente=fuente,
+            responsable=responsable,
+            reemplaza_a=reemplaza_a,
+        )
+        sesion.commit()
+    except HojaInvalida:
+        sesion.rollback()
+        raise
+    except ValueError as error:
+        sesion.rollback()
+        raise HojaInvalida(f"No se guardo el estudio: {error}") from error
+    except BaseException:
+        sesion.rollback()
+        raise
+    return estudio.id
+
+
 def parciales_por_reemplazar(sesion, proyecto: str, codigo: str) -> list[tuple[int, date]]:
     """Los estudios «parcial al corte» de la version que nadie reemplazo aun (id, fecha de
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/integration/test_ui_control.py tests/unit/test_arquitectura_s2.py tests/integration/test_ui_reajuste_valuaciones.py -v -W error` → 41 pruebas en verde.
Run: `uv run pytest tests/unit/test_arquitectura.py tests/unit/test_arquitectura_s5.py tests/unit/test_ui_reajuste.py -q -W error` → verde: las pruebas de S1 de la pantalla de reajuste no cambian (la casilla es opcional).
Run: `uv run ruff check ui/control.py ui/reajuste.py tests/integration/test_ui_control.py tests/unit/test_arquitectura_s2.py tests/integration/test_ui_reajuste_valuaciones.py`.
- [ ] **Paso 5: Commit**
```bash
git add ui/control.py ui/reajuste.py
git commit -m "feat(ui): control de obra sin Streamlit y reajuste con lo ejecutado de las valuaciones" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 13: pantalla «Control de obra», barra, app, hoja y casilla de la pantalla de reajuste

**Rama:** `inc/070-s2-4-ui`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/paginas/control.py`, `tests/unit/test_ui_pagina_control.py`, `tests/unit/test_ui_pagina_reajuste_valuaciones.py`
- Modificar: `ui/paginas/reajuste.py` (casilla y llamadas; S1), `ui/app.py:59-121` (importar `control` y una `DefinicionPagina` en Trabajo), `ui/barra.py` (rótulo, ruta y columnas), `ui/caso.py:47-50` (`ACCION_REGISTRAR_VALUACION`), `ui/hoja.py:2270-2310` (`control` en `exportar_excel` y `excel_de_hoja_en_bytes`), `ui/paginas/hoja.py:58,450-470` (`_preparar_excel` pasa `control.tablas_de_control`), `tests/unit/test_ui_app.py`, `tests/unit/test_ui_barra.py`, `tests/unit/test_ui_importable.py`, `tests/unit/test_arquitectura_s2.py` (la pantalla entra a la regla), `tests/unit/test_arquitectura_s5.py` (`"control"` en `PAGINAS_QUE_ABREN_EL_CASO`, entre `"componer"` y `"elaborar"`)

**Interfaces:**
- Consume: de la tarea 12: `ui.control.*` completo; de S1: `ui.texto_seguro.texto_seguro`, `ui.subidas.guardar_subida`, `ui.caso.{proyecto_abierto, ruta_caso, tomar_accion, pedir_accion}`, `operacion.base_datos.{preparar_base, ErrorDeBase}`.
- Produce:
- `ui/paginas/control.py`:
  - `PESTANAS = ('Línea base', 'Valuaciones', 'Valor ganado', 'Alertas y reproyección', 'Recuperación')`
  - `CLAVE_PESTANA = 'control_pestana'`
  - `CLAVE_OPCIONES = 'control_opciones'`
  - `CLAVE_MENSAJE = 'control_mensaje'`
  - `CLAVE_LECTURA = 'control_lectura'`
  - `PERSPECTIVAS = ('costo', 'precio')`
  - `def render() -> None`
  `ui.caso.ACCION_REGISTRAR_VALUACION = "registrar_valuacion"`, `ui.barra.ROTULO_VALUACION = "Registrar valuacion"`, `ui.barra.RUTA_CONTROL = "control"`, `ui.paginas.reajuste.CLAVE_VALUACIONES = "reajuste_con_valuaciones"`.

- [ ] **Paso 1: Escribir las pruebas que fallan**
  La pantalla con `AppTest`: cinco pestañas (`st.segmented_control`), alertas y reproyección visibles al abrir sin pedirlas, opciones a pedido, elegir crea la versión, lo de afuera por celdas (RV-14), la base real intacta. `st.data_editor` no se teclea desde `AppTest`, así que el registro con líneas se prueba en la tarea 12 y aquí solo su rechazo sin líneas:
```python
# tests/unit/test_ui_pagina_control.py
"""Pantalla «Control de obra» (UC-19 y UC-20; spec S2 §5.5) con `AppTest`.

Una base de OB-S2 en `tmp_path`, abierta con `preparar_base` (RV-5); el caso se desvía parchando el
objeto módulo de `ui.caso`. `st.data_editor` no se teclea desde `AppTest`, así que el registro con
líneas se prueba en `tests/integration/test_ui_control.py` y aquí solo su rechazo sin líneas.
"""

from __future__ import annotations

import importlib
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz
from ui.caso import ACCION_REGISTRAR_VALUACION, CLAVE_ACCION, CLAVE_PROYECTO
from ui.paginas.control import CLAVE_PESTANA, PESTANAS
from ui.texto_seguro import texto_seguro

SCRIPT = "from ui.paginas.control import render\n\nrender()\n"


def _caso(tmp_path: Path, *, linea_base=True, valuaciones=True, revaloracion=False) -> Path:
    ruta = tmp_path / "obra.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            if linea_base:
                ob.declarar_linea_base(sesion)
            if valuaciones:
                ob.registrar_v01_y_v02(sesion)
            if revaloracion:
                rz.sembrar_revaloracion(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


def _contar(ruta: Path, modelo) -> int:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return sesion.scalar(select(func.count()).select_from(modelo))
    finally:
        motor.dispose()


def _pantalla(monkeypatch, ruta: Path, estado=None, *, proyecto=ob.NOMBRE) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(ruta))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    if proyecto is not None:
        at.session_state[CLAVE_PROYECTO] = proyecto
    for clave, valor in (estado or {}).items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _pestana(at: AppTest, nombre: str) -> AppTest:
    at.session_state[CLAVE_PESTANA] = nombre
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _texto(at: AppTest) -> str:
    return " ".join(
        [m.value for m in at.markdown]
        + [c.value for c in at.caption]
        + [e.value for e in at.error]
        + [s.value for s in at.success]
        + [i.value for i in at.info]
        + [w.value for w in at.warning]
    )


def _tabla(at: AppTest, titulo_columna: str) -> list[dict]:
    for df in at.dataframe:
        if titulo_columna in df.value.columns:
            return df.value.to_dict("records")
    raise AssertionError(f"ninguna tabla trae la columna {titulo_columna!r}")


def test_sin_proyecto_abierto_pide_abrir_uno(monkeypatch, tmp_path):
    at = _pantalla(monkeypatch, _caso(tmp_path), proyecto=None)
    assert any("Abra un proyecto" in i.value for i in at.info)


def test_sin_linea_base_solo_ofrece_declararla_y_las_demas_pestanas_lo_dicen(monkeypatch, tmp_path):
    at = _pantalla(monkeypatch, _caso(tmp_path, linea_base=False, valuaciones=False))
    assert any("no tiene linea base de control" in i.value for i in at.info)
    for pestana in PESTANAS[1:]:
        _pestana(at, pestana)
        assert any("Declare primero la linea base" in i.value for i in at.info), pestana


def test_declarar_la_linea_base_desde_la_pantalla(monkeypatch, tmp_path):
    ruta = _caso(tmp_path, linea_base=False, valuaciones=False)
    at = _pantalla(monkeypatch, ruta)
    at.text_input(key="control_lb_desde").input("2026-11-02")
    at.text_input(key="control_lb_inicio").input("2026-11-02")
    at.text_input(key="control_lb_fuente").input(ob.FUENTE)
    at.text_input(key="control_lb_responsable").input(ob.RESPONSABLE)
    at.button(key="control_lb_declarar").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Linea base declarada." in s.value for s in at.success)
    assert _contar(ruta, models.LineaBaseControl) == 1
    vigente = next(m.value for m in at.markdown if "Linea base vigente" in m.value)
    assert "perspectiva costo" in vigente and texto_seguro("version OB-001") in vigente


def test_una_linea_base_mal_declarada_se_muestra_como_error_y_no_escribe(monkeypatch, tmp_path):
    ruta = _caso(tmp_path, linea_base=False, valuaciones=False)
    at = _pantalla(monkeypatch, ruta)
    at.text_input(key="control_lb_desde").input("02/11/2026")
    at.button(key="control_lb_declarar").click().run()
    assert any("no es una fecha" in e.value for e in at.error)
    assert _contar(ruta, models.LineaBaseControl) == 0


def test_la_pestana_linea_base_muestra_la_vigente_y_los_parametros_con_su_naturaleza(
    monkeypatch, tmp_path
):
    at = _pantalla(monkeypatch, _caso(tmp_path))
    assert any("Linea base vigente" in m.value for m in at.markdown)
    filas = {f["Parametro"]: f for f in _tabla(at, "Naturaleza")}
    assert filas["spi_error"]["Valor"] == "0.90"
    assert filas["spi_error"]["Naturaleza"] == "SUPUESTO_DECLARADO"
    assert filas["penalizacion_diaria"]["Naturaleza"] == "DATO_DEL_CONTRATO"


def test_las_valuaciones_se_listan_con_su_fecha_de_registro_y_su_estado(monkeypatch, tmp_path):
    at = _pestana(_pantalla(monkeypatch, _caso(tmp_path)), "Valuaciones")
    filas = _tabla(at, "Registrada")
    assert [f["Numero"] for f in filas] == ["V-01", "V-02"]
    assert filas[0]["Registrada"] == "2026-11-09 09:00" and filas[0]["Estado"] == "sin hallazgos"
    assert "solo anularla la saca del calculo" in _texto(at)


def test_registrar_sin_lineas_se_rechaza_con_su_mensaje(monkeypatch, tmp_path):
    ruta = _caso(tmp_path)
    at = _pestana(_pantalla(monkeypatch, ruta), "Valuaciones")
    at.text_input(key="control_v_numero").input("V-03")
    at.text_input(key="control_v_desde").input("2026-11-16")
    at.text_input(key="control_v_hasta").input("2026-11-20")
    at.text_input(key="control_v_fuente").input("acta")
    at.text_input(key="control_v_responsable").input("Ing.")
    at.button(key="control_v_registrar").click().run()
    assert any("al menos una linea" in e.value for e in at.error)
    assert _contar(ruta, models.Valuacion) == 2


def test_anular_una_valuacion_la_saca_de_la_lista_de_las_que_cuentan(monkeypatch, tmp_path):
    ruta = _caso(tmp_path)
    at = _pestana(_pantalla(monkeypatch, ruta), "Valuaciones")
    at.selectbox(key="control_a_valuacion").select_index(1)
    at.text_input(key="control_a_motivo").input("no aprobada")
    at.text_input(key="control_a_responsable").input("Ing.")
    at.button(key="control_a_anular").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Valuacion anulada" in s.value for s in at.success)
    assert _contar(ruta, models.AnulacionValuacion) == 1
    assert [f["Numero"] for f in _tabla(at, "Registrada")] == ["V-01"]


def test_el_boton_de_la_barra_abre_la_pestana_valuaciones(monkeypatch, tmp_path):
    at = _pantalla(monkeypatch, _caso(tmp_path), {CLAVE_ACCION: ACCION_REGISTRAR_VALUACION})
    assert at.session_state[CLAVE_PESTANA] == "Valuaciones"
    assert any("Registrar una valuacion" in e.label for e in at.expander)


def test_valor_ganado_muestra_la_tabla_y_la_curva(monkeypatch, tmp_path):
    at = _pestana(_pantalla(monkeypatch, _caso(tmp_path)), "Valor ganado")
    filas = {f["Indicador"]: f for f in _tabla(at, "Indicador")}
    assert filas["PV (USD)"]["Valor"] == "1500.00" and filas["EV (USD)"]["Valor"] == "1200.00"
    assert filas["SPI"]["Valor"] == "0.8000" and filas["CPI"]["Valor"] == "0.9375"
    assert filas["Desvio de precio (USD)"]["Valor"] == "no disponible"  # sin precios del corte
    assert "definiciones del sistema (S2-R11)" in _texto(at)
    assert len(at.get("vega_lite_chart")) == 1


def test_con_la_comprobacion_directa_la_separacion_aparece(monkeypatch, tmp_path):
    at = _pestana(_pantalla(monkeypatch, _caso(tmp_path, revaloracion=True)), "Valor ganado")
    at.selectbox(key="control_metodo").select("Comprobacion directa (version revalorada)").run()
    at.selectbox(key="control_pc_version").select("OB-R01").run()
    assert not at.exception, [e.value for e in at.exception]
    filas = {f["Indicador"]: f for f in _tabla(at, "Indicador")}
    assert filas["Desvio de precio (USD)"]["Valor"] == "-60.00"
    assert filas["Desvio de consumo (USD)"]["Valor"] == "-20.00"


def test_alertas_y_reproyeccion_se_ven_al_abrir_sin_pedirlas(monkeypatch, tmp_path):
    at = _pestana(_pantalla(monkeypatch, _caso(tmp_path)), "Alertas y reproyección")
    alertas = {f["Alerta"]: f for f in _tabla(at, "Alerta")}
    assert alertas["AL-1"]["Severidad"] == "ERROR" and alertas["AL-3"]["Severidad"] == "ERROR"
    texto = _texto(at)
    assert "Termino por el plan reproyectado: dia 23 (2026-12-02)" in texto
    assert "Termino por el indice: dia 25 (2026-12-04)" in texto
    assert "Sin estudio de reajuste guardado: V' = V" in texto
    plan = _tabla(at, "OB-C")
    assert plan[2]["OB-C"] == "0.4000" and len(plan) == 5


def test_un_corte_con_un_costo_en_bs_sin_tasa_avisa_que_el_ac_no_esta_disponible(
    monkeypatch, tmp_path
):
    ruta = _caso(tmp_path)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as sesion:
        from core.budget.valuaciones import registrar_costo

        registrar_costo(
            sesion, ob.NOMBRE, monto=ob.COSTO_REAL, moneda="Bs", fecha=date(2026, 11, 13),
            fuente="factura", responsable="Ing.",
        )  # fmt: skip
        sesion.commit()
    motor.dispose()
    at = _pestana(_pantalla(monkeypatch, ruta), "Valor ganado")
    assert any("no tiene tasa aplicable" in w.value for w in at.warning)
    filas = {f["Indicador"]: f for f in _tabla(at, "Indicador")}
    assert filas["AC (USD)"]["Valor"] == "no disponible"


def test_recuperacion_calcula_a_pedido_y_elegir_crea_la_version(monkeypatch, tmp_path):
    ruta = _caso(tmp_path)
    at = _pestana(_pantalla(monkeypatch, ruta), "Recuperación")
    assert not at.dataframe  # nada se calcula hasta que se pide
    at.button(key="control_r_calcular").click().run()
    assert not at.exception, [e.value for e in at.exception]
    filas = {f["Opcion"]: f for f in _tabla(at, "Opcion")}
    assert filas["Mas cuadrillas"]["Termino"] == "dia 17"
    assert filas["Partidas en paralelo"]["Nota"].startswith("ninguna partida sin empezar")
    assert any("art. 182" in c.value for c in at.caption)
    at.radio(key="control_r_elegida").set_value(
        next(o for o in at.radio(key="control_r_elegida").options if "cuadrillas" in o.lower())
    )
    at.text_input(key="control_r_fuente").input("decision ficticia")
    at.text_input(key="control_r_responsable").input("Ing.")
    at.button(key="control_r_elegir").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Version OB-002 creada" in s.value for s in at.success)
    assert _contar(ruta, models.DecisionRecuperacion) == 1
    assert [f["Version"] for f in _tabla(at, "Corte")] == ["OB-002"]


def test_elegir_sin_fuente_se_rechaza(monkeypatch, tmp_path):
    ruta = _caso(tmp_path)
    at = _pestana(_pantalla(monkeypatch, ruta), "Recuperación")
    at.button(key="control_r_calcular").click().run()
    at.button(key="control_r_elegir").click().run()
    assert any("obligatoria" in e.value for e in at.error)
    assert _contar(ruta, models.DecisionRecuperacion) == 0


def test_la_pantalla_no_escribe_en_la_base_real(monkeypatch, tmp_path):
    ruta = _caso(tmp_path)
    antes = ruta.stat().st_size
    _pestana(_pestana(_pantalla(monkeypatch, ruta), "Valor ganado"), "Alertas y reproyección")
    assert ruta.stat().st_size == antes
```
  La casilla de la pantalla de reajuste: marcada, la tabla de lo ejecutado a mano desaparece y la pantalla dice de dónde sale lo ejecutado:
```python
# tests/unit/test_ui_pagina_reajuste_valuaciones.py
"""La casilla «Tomar lo ejecutado de las valuaciones» de la pantalla de reajuste (UC-18 enmendado
por S2, RF-72): marcada, la tabla de lo ejecutado a mano desaparece y la pantalla avisa de dónde
sale lo ejecutado. `st.data_editor` no se teclea desde `AppTest`; el cálculo y el guardado con
valuaciones se prueban en `tests/integration/test_ui_reajuste_valuaciones.py`."""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from ui.caso import CLAVE_PROYECTO
from ui.paginas.reajuste import CLAVE_VALUACIONES

SCRIPT = "from ui.paginas.reajuste import render\n\nrender()\n"


def _pantalla(monkeypatch, tmp_path: Path, *, con_valuaciones: bool) -> AppTest:
    tmp_path.mkdir(exist_ok=True)
    ruta = tmp_path / "obra.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(ruta))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_PROYECTO] = ob.NOMBRE
    at.session_state[CLAVE_VALUACIONES] = con_valuaciones
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_sin_marcar_la_pantalla_pide_lo_ejecutado_a_mano(monkeypatch, tmp_path):
    at = _pantalla(monkeypatch, tmp_path, con_valuaciones=False)
    assert len(at.dataframe) == 3  # componentes, periodos y ejecutado
    assert any("valuaciones" in c.label for c in at.checkbox)


def test_marcada_la_tabla_de_lo_ejecutado_no_se_pide(monkeypatch, tmp_path):
    a_mano = len(_pantalla(monkeypatch, tmp_path / "a", con_valuaciones=False).dataframe)
    marcada = _pantalla(monkeypatch, tmp_path / "b", con_valuaciones=True)
    assert len(marcada.dataframe) == a_mano - 1
    assert any("valuaciones no anuladas" in c.value for c in marcada.caption)
```
  Los conteos de pantallas, el caso de uso de la página y el botón de la barra (parches sobre pruebas existentes que no son de regresión; la 0.6.0 deja catorce pantallas y S2 agrega la quince):
```diff
--- a/tests/unit/test_ui_app.py
+++ b/tests/unit/test_ui_app.py
@@ TITULOS_TRABAJO @@
     "Indices del BCV",
     "Reajuste de precios",
+    "Control de obra",
 )
@@ CASOS_DE_USO @@
     "componer": "UC-10 / UC-11",
+    "control": "UC-19 / UC-20",
     "elaborar": "UC-01",
@@ el conteo de pantallas @@
-def test_son_catorce_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
+def test_son_quince_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
     rutas = [p.ruta_url for p in PAGINAS]
-    assert len(rutas) == 14
+    assert len(rutas) == 15
--- a/tests/unit/test_ui_importable.py
+++ b/tests/unit/test_ui_importable.py
@@ MODULOS_SIN_PAGINA @@
     "ui.reajuste",
+    "ui.control",
 )
@@ test_las_paginas_se_importan_sin_efectos @@
-    assert len(modulos) == len(MODULOS_SIN_PAGINA) + 14  # las catorce paginas del marco
+    assert len(modulos) == len(MODULOS_SIN_PAGINA) + 15  # las quince paginas del marco
```
```diff
--- a/tests/unit/test_ui_barra.py
+++ b/tests/unit/test_ui_barra.py
@@ -24,4 +24,5 @@
     ACCION_IMPORTAR_PLANO,
     ACCION_PRECIOS,
+    ACCION_REGISTRAR_VALUACION,
     CLAVE_ACCION,
     CLAVE_PROYECTO,
@@ -145,4 +146,5 @@
     assert _rotulos(at) == [
         barra.ROTULO_PRECIOS,
+        barra.ROTULO_VALUACION,
         barra.ROTULO_GUARDAR,
         barra.ROTULO_EXPORTAR,
@@ -162,4 +164,11 @@
     assert at.session_state["destino"] == "hoja"
     assert at.session_state[CLAVE_ACCION] == ACCION_IMPORTAR_PLANO
+
+
+def test_registrar_valuacion_lleva_a_control_de_obra_con_su_accion(monkeypatch, caso_con_version):
+    at = _barra(monkeypatch, caso_con_version[0])
+    _boton(at, barra.ROTULO_VALUACION).click().run()
+    assert at.session_state["destino"] == "control"
+    assert at.session_state[CLAVE_ACCION] == ACCION_REGISTRAR_VALUACION
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_ui_pagina_control.py tests/unit/test_ui_pagina_reajuste_valuaciones.py tests/unit/test_ui_app.py tests/unit/test_ui_barra.py tests/unit/test_ui_importable.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'ACCION_REGISTRAR_VALUACION' from 'ui.caso'`
```bash
git add tests/unit/test_ui_pagina_control.py tests/unit/test_ui_pagina_reajuste_valuaciones.py tests/unit/test_ui_app.py tests/unit/test_ui_barra.py tests/unit/test_ui_importable.py
git commit -m "test(ui): pantalla Control de obra, boton de la barra y casilla de reajuste en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  La página (abre el caso con `preparar_base`, RV-5; muestra todo texto ajeno por `texto_seguro` o en celdas):
```python
# ui/paginas/control.py
"""Pantalla «Control de obra» (UC-19 y UC-20; spec S2 §5.5).

Cinco pestañas sobre la línea base de control del proyecto abierto:

* **Línea base**: la vigente (versión, perspectiva, calendario), su declaración y los parámetros
  de control con su naturaleza visible (SUPUESTO_DECLARADO, salvo la penalización del contrato);
* **Valuaciones**: las guardadas en solo lectura con su fecha de registro y su Estado (el peor
  hallazgo de R13-R14); registrar una a mano, importar un XLSX con informe previo, anular con
  fuente y anotar costos reales;
* **Valor ganado**: la tabla de §4.2 y la separación del desvío en plazo, precio y consumo, cada
  monto en las dos monedas con la tasa del corte (S1), y la curva PV/EV/AC;
* **Alertas y reproyección**: AL-1 a AL-6, el término por los dos métodos, el EAC, el punto de
  equilibrio proyectado con los estudios de reajuste que suma y el plan reproyectado. Se calculan
  **siempre**, sin que se pidan;
* **Recuperación**: «Calcular opciones» (a pedido) y elegir una, con fuente y responsable.

Toda la lógica vive en `ui.control` (sin Streamlit); aquí solo se pinta. Los textos que vienen de
fuera (inspector, observación, fuente de un XLSX) van en celdas o por `ui.texto_seguro`, nunca como
Markdown interpretado (RV-14). El caso se abre con `preparar_base` (RV-5). Sin efectos al
importarse.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st
from pandas import DataFrame
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from ui import control
from ui.caso import ACCION_REGISTRAR_VALUACION, proyecto_abierto, ruta_caso, tomar_accion
from ui.subidas import guardar_subida
from ui.texto_seguro import texto_seguro

PESTANAS = ("Línea base", "Valuaciones", "Valor ganado", "Alertas y reproyección", "Recuperación")
CLAVE_PESTANA = "control_pestana"
CLAVE_OPCIONES = "control_opciones"  # (proyecto, corte, opciones): no es clave de ningún widget
CLAVE_MENSAJE = "control_mensaje"  # (tipo, texto) del último intento de escribir
CLAVE_LECTURA = "control_lectura"  # (nombre, LecturaControl) del XLSX leído
PERSPECTIVAS = ("costo", "precio")


def _motor_del_caso():
    """El motor del caso abierto, ya en `head` (RV-5); `None` si no se puede preparar."""
    ruta = ruta_caso()
    try:
        preparar_base(ruta)
    except ErrorDeBase as error:
        st.error(texto_seguro(str(error)))
        return None
    return crear_motor(f"sqlite:///{ruta.as_posix()}")


def _mensaje(tipo: str, texto: str) -> None:
    st.session_state[CLAVE_MENSAJE] = (tipo, texto)


def _mostrar_mensaje() -> None:
    pendiente = st.session_state.pop(CLAVE_MENSAJE, None)
    if pendiente is not None:
        tipo, texto = pendiente
        {"error": st.error, "success": st.success}.get(tipo, st.info)(texto)


def _intentar(accion, exito: str) -> bool:
    """Corre `accion`; deja el resultado en el mensaje de la pantalla. True si salió bien."""
    try:
        accion()
    except control.ControlInvalido as error:
        _mensaje("error", texto_seguro(str(error)))
        return False
    _mensaje("success", exito)
    return True


def _tabla(filas: list[dict[str, str]], columnas: tuple[str, ...]) -> None:
    st.dataframe(DataFrame(filas, columns=list(columnas)), hide_index=True, width="stretch")


def render() -> None:
    proyecto = proyecto_abierto()
    if proyecto is None:
        st.info("Abra un proyecto en la barra superior (Proyecto) para controlar su obra.")
        return
    motor = _motor_del_caso()
    if motor is None:
        return
    try:
        with abrir_sesion(motor) as sesion:
            _pintar(sesion, proyecto)
    except SQLAlchemyError as error:
        detalle = getattr(error, "orig", error)
        st.error(texto_seguro(f"No se pudo leer o escribir el caso: {detalle}"))
    finally:
        motor.dispose()


def _pintar(sesion, proyecto: str) -> None:
    catalogo = Catalogo(sesion)
    if tomar_accion() == ACCION_REGISTRAR_VALUACION:
        st.session_state[CLAVE_PESTANA] = PESTANAS[1]
    _mostrar_mensaje()
    pestana = st.segmented_control(
        "Seccion", PESTANAS, default=PESTANAS[0], key=CLAVE_PESTANA, label_visibility="collapsed"
    )
    pestana = pestana or PESTANAS[0]
    if pestana == PESTANAS[0]:
        _linea_base(sesion, proyecto)
    elif pestana == PESTANAS[1]:
        _valuaciones(sesion, proyecto, catalogo)
    elif not control.tiene_linea_base(sesion, proyecto):
        st.info("Declare primero la linea base de control (pestana Línea base).")
    elif not control.hay_valuaciones(sesion, proyecto):
        st.info("Registre la primera valuacion (pestana Valuaciones) para ver el control.")
    else:
        resultado = _calcular(sesion, proyecto, catalogo)
        if resultado is None:
            return
        if pestana == PESTANAS[2]:
            _valor_ganado(sesion, resultado)
        elif pestana == PESTANAS[3]:
            _alertas_y_reproyeccion(resultado)
        else:
            _recuperacion(sesion, proyecto, catalogo, resultado)


# --- pestaña Línea base ---------------------------------------------------------------------------


def _linea_base(sesion, proyecto: str) -> None:
    descripcion = control.describir_linea_base(sesion, proyecto)
    if descripcion is None:
        st.info("El proyecto no tiene linea base de control. Declarela abajo.")
    else:
        st.markdown(f"**Linea base vigente**: {texto_seguro(descripcion)}.")
    with st.expander("Declarar una linea base", expanded=descripcion is None):
        versiones = control.versiones_para_la_linea_base(sesion, proyecto)
        version = st.selectbox("Version del contrato", versiones, key="control_lb_version")
        a, b, c = st.columns(3)
        desde = a.text_input("Vigente desde (AAAA-MM-DD)", key="control_lb_desde")
        perspectiva = b.selectbox(
            "Perspectiva",
            PERSPECTIVAS,
            key="control_lb_perspectiva",
            help="costo: quien arma (contratista); precio: quien revisa (contratante).",
        )
        inicio = c.text_input("Inicio de obra (AAAA-MM-DD)", key="control_lb_inicio")
        d, e = st.columns(2)
        dias = d.text_input("Dias habiles por periodo", value="5", key="control_lb_dias")
        feriados = e.text_area("Feriados (AAAA-MM-DD, separados por comas)", key="control_lb_fer")
        fuente = st.text_input("Fuente de la linea base", key="control_lb_fuente")
        responsable = st.text_input("Responsable", key="control_lb_responsable")
        if st.button("Declarar linea base", key="control_lb_declarar") and _intentar(
            lambda: control.declarar_linea_base(
                sesion,
                proyecto,
                version,
                desde=desde,
                perspectiva=perspectiva,
                inicio=inicio,
                dias_por_periodo=dias,
                feriados=feriados,
                fuente=fuente,
                responsable=responsable,
            ),
            "Linea base declarada.",
        ):
            st.rerun()
        _mostrar_mensaje()
    _parametros(sesion, proyecto)


def _parametros(sesion, proyecto: str) -> None:
    st.subheader("Parametros de control")
    st.caption(
        "Umbrales de las alertas y supuestos de las opciones. Son SUPUESTO_DECLARADO, sin fuente "
        "normativa, salvo la penalizacion (dato del contrato). Cambiarlos deja su registro."
    )
    filas = control.filas_de_parametros(control.parametros_actuales(sesion, proyecto))
    editadas = st.data_editor(
        DataFrame(filas, columns=list(control.COLUMNAS_PARAMETROS)),
        hide_index=True,
        disabled=["Parametro", "Que es", "Naturaleza"],
        key="control_parametros",
        width="stretch",
    )
    fuente = st.text_input("Fuente del cambio de parametros", key="control_par_fuente")
    responsable = st.text_input("Responsable del cambio", key="control_par_responsable")
    if st.button("Guardar parametros", key="control_par_guardar"):
        try:
            cambiados = control.guardar_los_parametros(
                sesion,
                proyecto,
                editadas.to_dict("records"),
                fuente=fuente,
                responsable=responsable,
            )
        except control.ControlInvalido as error:
            st.error(texto_seguro(str(error)))
        else:
            st.success(f"{cambiados} parametro(s) cambiado(s).")


# --- pestaña Valuaciones --------------------------------------------------------------------------


def _valuaciones(sesion, proyecto: str, catalogo: Catalogo) -> None:
    if not control.tiene_linea_base(sesion, proyecto):
        st.info("Declare primero la linea base de control (pestana Línea base).")
        return
    if control.hay_valuaciones(sesion, proyecto):
        try:
            resultado = control.calcular_el_control(sesion, proyecto, catalogo)
        except control.ControlInvalido as error:
            st.error(texto_seguro(str(error)))
        else:
            st.subheader("Valuaciones registradas (cuentan desde su registro)")
            _tabla(control.filas_de_valuaciones(resultado), control.COLUMNAS_VALUACIONES)
            st.caption(
                "Una valuacion registrada cuenta desde su registro; solo anularla la saca del "
                "calculo (S2-R14). Si el cliente no la aprueba, anulela."
            )
    else:
        st.info("Aun no hay valuaciones registradas.")
    _registrar(sesion, proyecto, catalogo)
    _importar(sesion, proyecto)
    _anular(sesion, proyecto)
    _costo(sesion, proyecto)


def _registrar(sesion, proyecto: str, catalogo: Catalogo) -> None:
    with st.expander("Registrar una valuacion", expanded=True):
        a, b, c = st.columns(3)
        numero = a.text_input("Numero", key="control_v_numero")
        desde = b.text_input("Periodo desde (AAAA-MM-DD)", key="control_v_desde")
        hasta = c.text_input("Periodo hasta (AAAA-MM-DD)", key="control_v_hasta")
        d, e = st.columns(2)
        fecha = d.text_input("Fecha de la valuacion (AAAA-MM-DD)", key="control_v_fecha")
        inspector = e.text_input("Inspector", key="control_v_inspector")
        editadas = st.data_editor(
            DataFrame({c: [""] for c in control.COLUMNAS_LINEAS}),
            num_rows="dynamic",
            hide_index=True,
            key="control_v_lineas",
            width="stretch",
        )
        fuente = st.text_input("Fuente (acta, oficio)", key="control_v_fuente")
        responsable = st.text_input("Responsable", key="control_v_responsable")
        if st.button("Registrar y controlar", type="primary", key="control_v_registrar"):
            try:
                resultado = control.registrar_y_controlar(
                    sesion,
                    proyecto,
                    catalogo,
                    numero=numero,
                    desde=desde,
                    hasta=hasta,
                    fecha=fecha,
                    inspector=inspector,
                    filas=editadas.to_dict("records"),
                    fuente=fuente,
                    responsable=responsable,
                )
            except control.ControlInvalido as error:
                st.error(texto_seguro(str(error)))
            else:
                graves = sum(1 for h in resultado.informe.hallazgos if h.severidad.name == "ERROR")
                _mensaje(
                    "success",
                    f"Valuacion registrada: corte {resultado.instantanea.corte.isoformat()}, "
                    f"{len(resultado.informe.hallazgos)} hallazgo(s) de R13-R14 ({graves} ERROR).",
                )
                st.rerun()


def _importar(sesion, proyecto: str) -> None:
    with st.expander("Importar valuaciones de un XLSX"):
        st.caption(
            "Hojas Valuaciones (numero, desde, hasta, fecha, inspector), Lineas (numero, "
            "codigo_partida, cantidad, fecha_medicion, observacion) y Costos (opcional). Un "
            "archivo malformado se rechaza entero."
        )
        subida = st.file_uploader("Archivo .xlsx", type=["xlsx"], key="control_x_archivo")
        if subida is not None:
            with tempfile.TemporaryDirectory() as carpeta:
                ruta = guardar_subida(subida, Path(carpeta))
                try:
                    st.session_state[CLAVE_LECTURA] = (subida.name, control.leer_excel(ruta))
                except control.ControlInvalido as error:
                    st.session_state.pop(CLAVE_LECTURA, None)
                    st.error(texto_seguro(str(error)))
        leida = st.session_state.get(CLAVE_LECTURA)
        if leida is None:
            return
        nombre, lectura = leida
        st.markdown(f"Informe previo de **{texto_seguro(nombre)}**:")
        for linea in lectura.informe:
            st.markdown(f"- {texto_seguro(linea)}")
        fuente = st.text_input("Fuente de la importacion", key="control_x_fuente")
        responsable = st.text_input("Responsable de la importacion", key="control_x_responsable")
        if st.button("Importar", key="control_x_importar"):
            try:
                cuantas = control.importar_excel(
                    sesion, proyecto, lectura, fuente=fuente, responsable=responsable
                )
            except control.ControlInvalido as error:
                st.error(texto_seguro(str(error)))
            else:
                st.session_state.pop(CLAVE_LECTURA, None)
                _mensaje("success", f"{cuantas} valuacion(es) importada(s).")
                st.rerun()


def _anular(sesion, proyecto: str) -> None:
    opciones = control.valuaciones_para_anular(sesion, proyecto)
    if not opciones:
        return
    with st.expander("Anular una valuacion"):
        rotulos = {rotulo: id_ for id_, rotulo in opciones}
        elegida = st.selectbox("Valuacion", list(rotulos), key="control_a_valuacion")
        motivo = st.text_input("Motivo", key="control_a_motivo")
        responsable = st.text_input("Responsable de la anulacion", key="control_a_responsable")
        if st.button("Anular", key="control_a_anular") and _intentar(
            lambda: control.anular(
                sesion, rotulos[elegida], motivo=motivo, responsable=responsable
            ),
            "Valuacion anulada: se conserva y ya no cuenta.",
        ):
            st.rerun()
        _mostrar_mensaje()


def _costo(sesion, proyecto: str) -> None:
    with st.expander("Anotar un costo real"):
        a, b, c = st.columns(3)
        monto = a.text_input("Monto", key="control_c_monto")
        moneda = b.selectbox("Moneda", ("USD", "Bs"), key="control_c_moneda")
        fecha = c.text_input("Fecha (AAAA-MM-DD)", key="control_c_fecha")
        partida = st.text_input("Partida (opcional)", key="control_c_partida")
        fuente = st.text_input("Fuente del costo", key="control_c_fuente")
        responsable = st.text_input("Responsable", key="control_c_responsable")
        if st.button("Anotar costo", key="control_c_anotar") and _intentar(
            lambda: control.registrar_costo_real(
                sesion,
                proyecto,
                monto=monto,
                moneda=moneda,
                fecha=fecha,
                fuente=fuente,
                responsable=responsable,
                partida=partida,
            ),
            "Costo anotado: se convierte con la tasa de su fecha al calcular.",
        ):
            st.rerun()
        _mostrar_mensaje()


# --- pestañas de resultados -----------------------------------------------------------------------


def _calcular(sesion, proyecto: str, catalogo: Catalogo):
    """Corte y precios del corte elegidos arriba; el control se recalcula en cada ejecución."""
    a, b = st.columns(2)
    corte = a.date_input(
        "Fecha de corte", value=control.corte_por_defecto(sesion, proyecto), key="control_corte"
    )
    metodo = b.selectbox("Precios del corte (S1)", control.METODOS_DE_PRECIOS, key="control_metodo")
    version = km = r = fuente = ""
    if metodo == control.METODO_COMPROBACION:
        revaloradas = control.versiones_revaloradas(sesion, proyecto)
        version = st.selectbox("Version revalorada", revaloradas, key="control_pc_version") or ""
        if not revaloradas:
            st.caption("El proyecto no tiene versiones revaloradas (UC-02): no hay comprobacion.")
    elif metodo == control.METODO_ESCALATORIA:
        c, d, e = st.columns(3)
        km = c.text_input("Km declarado", key="control_pc_km")
        r = d.text_input("R declarado", value="0", key="control_pc_r")
        fuente = e.text_input("Fuente de Km y R", key="control_pc_fuente")
    try:
        precios = None
        if metodo != control.METODO_NINGUNO:
            elegido = control.PrecioElegido(metodo, version, km, r, fuente)
            precios = control.precios_del_corte(sesion, proyecto, catalogo, elegido, "costo")
        return control.calcular_el_control(sesion, proyecto, catalogo, corte=corte, precios=precios)
    except control.ControlInvalido as error:
        st.error(texto_seguro(str(error)))
        return None


def _valor_ganado(sesion, resultado) -> None:
    st.caption(
        f"Corte {resultado.instantanea.corte.isoformat()} (dia habil {resultado.estado.dia}). "
        "Las formulas de valor ganado son definiciones del sistema (S2-R11); el EAC del sistema y "
        "la separacion del desvio son propios de este trabajo. Sin proyectar inflacion futura "
        "(S2-R12)."
    )
    for costo in resultado.costos_sin_tasa:
        st.warning(
            f"El costo de {costo.monto} {costo.moneda} del {costo.fecha.isoformat()} no tiene "
            "tasa aplicable (mas de 7 dias sin tasa): el AC y lo que depende de el no estan "
            "disponibles; nada se estima."
        )
    _tabla(control.filas_de_indicadores(sesion, resultado), control.COLUMNAS_INDICADORES)
    curva = control.curva_pv_ev_ac(sesion, resultado)
    if curva:
        st.subheader("PV, EV y AC al cierre de cada periodo")
        st.line_chart(
            DataFrame(
                {
                    "PV": [float(p["PV"]) for p in curva],
                    "EV": [float(p["EV"]) for p in curva],
                    "AC": [None if p["AC"] is None else float(p["AC"]) for p in curva],
                },
                index=[p["Periodo"] for p in curva],
            )
        )
    if resultado.indicadores.pv == 0:
        st.caption("El corte es anterior a todo trabajo planificado: el SPI no aplica.")


def _alertas_y_reproyeccion(resultado) -> None:
    ind, rep = resultado.indicadores, resultado.reproyeccion
    st.subheader("Alertas")
    _tabla(control.alertas_en_filas(resultado), control.COLUMNAS_ALERTAS)
    st.subheader("Termino, costo final y punto de equilibrio")
    st.markdown(
        f"- Termino por el indice: {control.dia_con_fecha(resultado, ind.termino_indice)}\n"
        f"- Termino por el plan reproyectado: {control.dia_con_fecha(resultado, rep.termino)}\n"
        f"- Termino del plan base: {control.dia_con_fecha(resultado, resultado.estado.dias_plan)}\n"
        f"- EAC (sistema): {control.texto_monto(ind.eac_sistema)} {resultado.instantanea.moneda}"
    )
    if rep.termino is None:
        st.caption(rep.motivo_termino)
    equilibrio = resultado.equilibrio_proyectado
    if equilibrio is None:
        st.caption("Punto de equilibrio proyectado: no disponible (perspectiva precio o AC/EAC).")
    else:
        st.markdown(
            f"- Punto de equilibrio proyectado: {control.texto_monto(equilibrio.punto)} "
            f"({equilibrio.mensaje})"
        )
    st.caption(control.estudios_que_suma(resultado))
    st.subheader("Reproyeccion por partida")
    _tabla(control.filas_de_reproyeccion(resultado), control.COLUMNAS_REPROYECCION)
    st.subheader("Plan reproyectado")
    columnas, filas = control.filas_del_plan_reproyectado(resultado)
    _tabla(filas, columnas)


def _recuperacion(sesion, proyecto: str, catalogo: Catalogo, resultado) -> None:
    st.caption(
        "Las opciones se calculan a pedido, cada una sola, con el rendimiento y la cuadrilla de "
        "cada APU y un factor de eficiencia declarado (supuesto, no dato). Elegir una crea una "
        "version nueva; la linea base no cambia."
    )
    a, b = st.columns(2)
    objetivo = a.text_input(
        "Dia habil objetivo (vacio: el fin del plan base)", key="control_r_objetivo"
    )
    previas = b.text_input(
        "Horas extra que el obrero ya acumula en el año", value="0", key="control_r_previas"
    )
    corte = resultado.instantanea.corte
    if st.button("Calcular opciones", key="control_r_calcular"):
        try:
            st.session_state[CLAVE_OPCIONES] = (
                proyecto,
                corte,
                control.calcular_las_opciones(resultado, objetivo=objetivo, horas_previas=previas),
            )
        except control.ControlInvalido as error:
            st.session_state.pop(CLAVE_OPCIONES, None)
            st.error(texto_seguro(str(error)))
    guardadas = st.session_state.get(CLAVE_OPCIONES)
    if guardadas is not None and guardadas[:2] == (proyecto, corte):
        _elegir(sesion, catalogo, resultado, guardadas[2])
    decisiones = control.filas_de_decisiones(sesion, proyecto)
    if decisiones:
        st.subheader("Decisiones tomadas")
        _tabla(decisiones, control.COLUMNAS_DECISIONES)


def _elegir(sesion, catalogo: Catalogo, resultado, todas) -> None:
    _tabla(control.filas_de_opciones(todas), control.COLUMNAS_OPCIONES)
    for opcion in todas:
        if opcion.requisitos:
            st.caption(f"{opcion.titulo}: requiere " + "; ".join(opcion.requisitos))
    aplican = [o for o in todas if o.aplica]
    if not aplican:
        st.info("Ninguna opcion aplica a este corte.")
        return
    elegida = st.radio(
        "Opcion a aplicar", aplican, format_func=lambda o: o.titulo, key="control_r_elegida"
    )
    declaracion = ""
    if elegida.requiere_declaracion:
        declaracion = st.text_input(
            "Declaro que estas partidas no dependen de las que estan en curso (con su fuente)",
            key="control_r_independencia",
        )
    fuente = st.text_input("Fuente de la decision", key="control_r_fuente")
    responsable = st.text_input("Responsable de la decision", key="control_r_responsable")
    if st.button("Elegir y crear la version", type="primary", key="control_r_elegir"):
        try:
            codigo = control.elegir_opcion(
                sesion,
                resultado,
                elegida,
                catalogo,
                fuente=fuente,
                responsable=responsable,
                declaracion_independencia=declaracion,
            )
        except control.ControlInvalido as error:
            st.error(texto_seguro(str(error)))
        else:
            st.session_state.pop(CLAVE_OPCIONES, None)
            _mensaje("success", f"Version {codigo} creada con el plan de la opcion elegida.")
            st.rerun()
```
  Registro en la aplicación (`control` se importa de `ui.paginas` en orden alfabético, tras `componer`; la `DefinicionPagina` va al final de Trabajo, tras «Reajuste de precios» de S1), la barra y el estado del caso:
```diff
--- a/ui/app.py
+++ b/ui/app.py
@@ from ui.paginas import ( @@
     componer,
+    control,
     elaborar,
@@ PAGINAS @@
     DefinicionPagina(reajuste.render, "Reajuste de precios", SECCION_TRABAJO, "UC-18"),
+    DefinicionPagina(control.render, "Control de obra", SECCION_TRABAJO, "UC-19 / UC-20"),
```
```diff
--- a/ui/caso.py
+++ b/ui/caso.py
@@ -48,4 +48,5 @@
 ACCION_GUARDAR_VERSION = "guardar_version"
 ACCION_EXPORTAR_EXCEL = "exportar_excel"
+ACCION_REGISTRAR_VALUACION = "registrar_valuacion"  # S2: lleva a «Control de obra»
```
```diff
--- a/ui/barra.py
+++ b/ui/barra.py
@@ -12,4 +12,5 @@
 | Precios | la pestana Precios de la hoja si existe; si no, la pantalla Actualizar precios |
 | Auditar | resume el informe de la version vigente (se audita siempre; el boton lo muestra) |
+| Registrar valuacion | lleva a «Control de obra», pestana Valuaciones (UC-19, S2) |
 | Guardar version, Exportar Excel | dependen de SF3: deshabilitados hasta que `ui.hoja` exista |
 | Recorrido guiado | abre o retoma el recorrido de UC-12 |
@@ -40,4 +41,5 @@
     ACCION_IMPORTAR_PLANO,
     ACCION_PRECIOS,
+    ACCION_REGISTRAR_VALUACION,
     estado_caso,
     fijar_proyecto,
@@ -60,4 +62,5 @@
 ROTULO_PRECIOS = "Precios"
 ROTULO_AUDITAR = "Auditar"
+ROTULO_VALUACION = "Registrar valuacion"
 ROTULO_GUARDAR = "Guardar version"
 ROTULO_EXPORTAR = "Exportar Excel"
@@ -82,4 +85,5 @@
 RUTA_HOJA = "hoja"
 RUTA_ACTUALIZACION = "actualizacion"
+RUTA_CONTROL = "control"
 PESTANA_PRECIOS = "Precios"
 
@@ -211,5 +215,5 @@
 
     with st.container(key="barra_herramientas"):
-        columnas = st.columns(7 if con_planos else 6, vertical_alignment="bottom")
+        columnas = st.columns(8 if con_planos else 7, vertical_alignment="bottom")
         celdas = iter(columnas)
         with next(celdas), st.popover(ROTULO_PROYECTO, width="stretch"):
@@ -227,4 +231,7 @@
         with next(celdas), st.popover(ROTULO_AUDITAR, width="stretch"):
             _pintar_auditoria(abierto)
+        with next(celdas):
+            if st.button(ROTULO_VALUACION, width="stretch", key="barra_valuacion"):
+                _ir_con_accion(ir_a, RUTA_CONTROL, ACCION_REGISTRAR_VALUACION)
         for rotulo, accion, clave in (
             (ROTULO_GUARDAR, ACCION_GUARDAR_VERSION, "barra_guardar"),
```
  La hoja del proyecto exporta las tres hojas de control en su Excel (`control` por omisión vacío: las cuatro hojas de la línea base no cambian):
```diff
--- a/ui/hoja.py
+++ b/ui/hoja.py
@@ -2271,11 +2271,14 @@
     trazabilidad: TablaExportable | None = None,
     precios: Sequence[FilaPrecio] = (),
+    control: Sequence[TablaExportable] = (),
 ) -> Path:
     """Escribe el libro de la hoja (spec §9.5) con lo que muestra `resultado`: una hoja por
     pestana, mas Trazabilidad y Auditoria, con formulas vivas. Solo se llama al pulsar Exportar.
+    `control` son las hojas «Valuaciones», «Valor ganado» y «Decisiones» de S2 (`ui.control`).
     """
     extras = [
         *tablas_de_espacio(borrador.espacio, resultado.items, resultado.estado),
         tabla_de_precios(precios),
+        *control,
     ]
     return exportar_hoja(
@@ -2295,4 +2298,5 @@
     trazabilidad: TablaExportable | None = None,
     precios: Sequence[FilaPrecio] = (),
+    control: Sequence[TablaExportable] = (),
 ) -> bytes:
     """El libro de `exportar_excel` como bytes, para `st.download_button`."""
@@ -2304,4 +2308,5 @@
             trazabilidad=trazabilidad,
             precios=precios,
+            control=control,
         )
         return ruta.read_bytes()
```
```diff
--- a/ui/paginas/hoja.py
+++ b/ui/paginas/hoja.py
@@ -59,5 +59,5 @@
 from core.verification.informe import DECIMALES_PRESENTACION
 from core.verification.texto import formatear_decimal
-from ui import caso, hoja
+from ui import caso, control, hoja
 from ui.caso import ACCION_IMPORTAR_PLANO, ACCION_PRECIOS, ruta_caso
 
@@ -451,5 +451,5 @@
     resultado, _ = _calculo()
     abierta = _abierta()
-    trazabilidad, precios = None, ()
+    trazabilidad, precios, hojas_de_control = None, (), []
     try:
         if abierta is not None:
@@ -457,6 +457,13 @@
                 trazabilidad = hoja.tabla_de_trazabilidad(sesion, abierta.proyecto, abierta.codigo)
                 precios = hoja.precios_de_version(sesion, abierta.proyecto, abierta.codigo)
+                hojas_de_control = control.tablas_de_control(
+                    sesion, abierta.proyecto, Catalogo(sesion)
+                )
         contenido = hoja.excel_de_hoja_en_bytes(
-            resultado, borrador, trazabilidad=trazabilidad, precios=precios
+            resultado,
+            borrador,
+            trazabilidad=trazabilidad,
+            precios=precios,
+            control=hojas_de_control,
         )
     except (SQLAlchemyError, ValueError) as error:
```
  La casilla de la pantalla de reajuste:
```diff
--- a/ui/paginas/reajuste.py
+++ b/ui/paginas/reajuste.py
@@ -22,4 +22,5 @@
 CLAVE_CALCULO = "reajuste_calculo"  # (contrato, clausula, periodos, resultado): no es de widget
 CLAVE_EXCEL = "reajuste_excel"  # bytes del ultimo Excel preparado
+CLAVE_VALUACIONES = "reajuste_con_valuaciones"  # casilla de la 0.7.0
 
 
@@ -111,4 +112,11 @@
         num_rows="dynamic", hide_index=True, key="reajuste_periodos",
     )
+    st.checkbox(
+        "Tomar lo ejecutado de las valuaciones registradas (cada una al periodo de su fecha hasta)",
+        key=CLAVE_VALUACIONES,
+    )
+    if st.session_state.get(CLAVE_VALUACIONES):
+        st.caption("Lo ejecutado sale de las valuaciones no anuladas y el estudio las cita.")
+        return periodos.to_dict("records"), []
     ejecutado = st.data_editor(
         DataFrame({"periodo": ["1"], "partida": [""], "cantidad": [""], "fuente": [""]}),
@@ -126,6 +134,9 @@
         try:
             clausula = reajuste.clausula_desde_textos(campos, componentes)
-            periodos = reajuste.periodos_desde_filas(filas_periodos, filas_ejecutado)
             with abrir_sesion(motor) as sesion:
+                if st.session_state.get(CLAVE_VALUACIONES):
+                    periodos = reajuste.periodos_desde_valuaciones(sesion, proyecto, filas_periodos)
+                else:
+                    periodos = reajuste.periodos_desde_filas(filas_periodos, filas_ejecutado)
                 resultado = reajuste.calcular(sesion, proyecto, contrato, clausula, periodos,
                                               fecha_calculo=date.today())
@@ -148,9 +159,9 @@
         st.info(f"El ultimo periodo aun no cierra: el estudio se guardara «parcial al corte» al "
                 f"{resultado.fecha_corte:%d/%m/%Y} y se reemplaza al cerrar el mes (S1-R21).")
-    _guardar(motor, proyecto, contrato, clausula, periodos, resultado)
+    _guardar(motor, proyecto, contrato, clausula, periodos, resultado, filas_periodos)
     _excel(motor, proyecto, contrato, resultado, periodos)
 
 
-def _guardar(motor, proyecto, contrato, clausula, periodos, resultado) -> None:
+def _guardar(motor, proyecto, contrato, clausula, periodos, resultado, filas_periodos) -> None:
     st.subheader("4. Guardar el estudio")
     with abrir_sesion(motor) as sesion:
@@ -167,7 +178,13 @@
         try:
             with abrir_sesion(motor) as sesion:
-                estudio = reajuste.guardar(sesion, proyecto, contrato, clausula, periodos,
-                                           fecha_calculo=date.today(), fuente=fuente,
-                                           responsable=responsable, reemplaza_a=reemplaza)
+                if st.session_state.get(CLAVE_VALUACIONES):
+                    estudio = reajuste.guardar_con_valuaciones(
+                        sesion, proyecto, contrato, clausula, filas_periodos,
+                        fecha_calculo=date.today(), fuente=fuente, responsable=responsable,
+                        reemplaza_a=reemplaza)
+                else:
+                    estudio = reajuste.guardar(sesion, proyecto, contrato, clausula, periodos,
+                                               fecha_calculo=date.today(), fuente=fuente,
+                                               responsable=responsable, reemplaza_a=reemplaza)
         except HojaInvalida as error:
             st.error(texto_seguro(str(error)))
```
  Las reglas de arquitectura incluyen la pantalla, y la lista de páginas que abren el caso gana `control`:
```diff
--- a/tests/unit/test_arquitectura_s2.py
+++ b/tests/unit/test_arquitectura_s2.py
@@ -31,7 +31,7 @@
     "core/budget/puente.py",
     "core/budget/decision.py",
 )
-PAGINAS_DE_S2 = ("ui/control.py",)
+PAGINAS_DE_S2 = ("ui/control.py", "ui/paginas/control.py")
 
 
 def _coincide(modulo: str, prefijo: str) -> bool:
```
  En `tests/unit/test_arquitectura_s5.py`, la tupla `PAGINAS_QUE_ABREN_EL_CASO` gana el elemento `"control"` entre `"componer"` y `"elaborar"` (una línea; el resto de la tupla, con las páginas de S1, no cambia): la página abre el caso con `preparar_base` antes de `crear_motor`.
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_ui_pagina_control.py tests/unit/test_ui_pagina_reajuste_valuaciones.py tests/unit/test_arquitectura_s2.py -v -W error` → 18 pruebas nuevas en verde.
Run: `uv run pytest tests/unit/test_ui_app.py tests/unit/test_ui_barra.py tests/unit/test_ui_importable.py tests/unit/test_arquitectura_s5.py tests/unit/test_ui_hoja.py tests/unit/test_excel_hoja.py -q -W error` → verde. `test_exportar_excel_escribe_cuatro_hojas` (regresión) no cambia: `control` es opcional.
Run: `uv run ruff check ui/paginas/control.py ui/app.py ui/barra.py ui/caso.py ui/paginas/reajuste.py tests/unit/test_ui_pagina_control.py tests/unit/test_ui_pagina_reajuste_valuaciones.py`. Las líneas modificadas de `ui/hoja.py` y `ui/paginas/hoja.py` se revisan con `git diff`; `ruff format` solo sobre archivos nuevos.
- [ ] **Paso 5: Commit**
```bash
git add ui/paginas/control.py ui/paginas/reajuste.py ui/app.py ui/barra.py ui/caso.py ui/hoja.py ui/paginas/hoja.py tests/unit/test_arquitectura_s2.py tests/unit/test_arquitectura_s5.py
git commit -m "feat(ui): pantalla Control de obra, boton de la barra, Excel con hojas de control y casilla de reajuste" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta de la rama `inc/070-s2-4-ui` y foco de revisión

**Compuerta** (se cruza al fusionar `inc/070-s2-4-ui`; la compuerta GS2-4 completa se cruza con la tarea 14):
1. `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-4 --junit reporte-pruebas.xml` → todas las filas en OK salvo la cifra de RNF-15 (C6), que queda PENDIENTE hasta la tarea 14 (sin cifra no es OK: PRU-H21).
2. CI verde en Linux y Windows, `-W error`, cero omitidas.
3. El recorrido a mano de Eugenio por «Control de obra» con la base de OB-S2 (registrar V-01 y V-02, ver alertas, calcular opciones, elegir «más cuadrillas» y abrir la versión `OB-002`) anotado en `docs/bitacora/2026-10-silice-070.md`. No hay recorrido guiado nuevo (RP7-14).
4. `tests/unit/test_arquitectura_s2.py` en verde: `ui/control.py` sin Streamlit, `pandas` ni `ui.caso`; ninguna pantalla de S2 importa `scripts` ni `tests` ni usa `unsafe_allow_html`.

**Foco de revisión de la interfaz:**
1. **Un inspector con una fórmula (`=1+1`) o con Markdown** en una valuación importada: viaja como texto a la celda del Excel y se muestra por `texto_seguro` → `tests/integration/test_ui_control.py::test_un_inspector_con_formula_viaja_como_texto_al_excel` (Tarea 12).
2. **Abrir la pantalla sin línea base:** solo ofrece declararla y las demás pestañas lo dicen, sin excepción → `tests/unit/test_ui_pagina_control.py::test_sin_linea_base_solo_ofrece_declararla_y_las_demas_pestanas_lo_dicen` (Tarea 13).
3. **Un corte con un costo en Bs sin tasa del BCV:** la pantalla avisa que el AC no está disponible en lugar de mostrar un cero → `tests/unit/test_ui_pagina_control.py::test_un_corte_con_un_costo_en_bs_sin_tasa_avisa_que_el_ac_no_esta_disponible` (Tarea 13).
4. **Elegir una opción sin fuente:** se rechaza y no deja versión → `tests/unit/test_ui_pagina_control.py::test_elegir_sin_fuente_se_rechaza` (Tarea 13).
5. **La pantalla nunca escribe en la base real:** `data/apu.db` no se toca → `tests/unit/test_ui_pagina_control.py::test_la_pantalla_no_escribe_en_la_base_real` (Tarea 13).

---

### Tarea 14: RNF-15 — medición y precarga de la lectura de la obra

**Rama:** `inc/070-s2-4-nucleo` (solo `core/`, `tests/`, `scripts/`, `docs/`, `.github/`; sale de `main` con `inc/070-s2-4-ui` fusionada)   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `scripts/medir_rnf15.py`, `tests/unit/test_medir_rnf15.py`, `tests/integration/test_rnf15_consultas.py`
- Modificar: `core/budget/valuaciones.py` (`_precargar` y su llamada en `instantanea_control`), `.gitignore` (`scripts/_salida_rnf15.json`), `scripts/README.md` (fila de `medir_rnf15.py`), `.github/workflows/ci.yml` (paso «Medición de RNF-15» antes de la meta de la 0.7.0)

**Interfaces:**
- Consume: de la tarea 9: `scripts.generar_obra_control.{generar, sembrar, registrar_valuacion_de, registrar_costo_de, NOMBRE, FUENTE, RESPONSABLE}`; de la tarea 12: `ui.control.{registrar_y_controlar, calcular_el_control, calcular_las_opciones}`; de S1/A: `scripts.medir_rnf11` (el patrón de la medición que solo registra), `core.catalog.{Catalogo, abrir_sesion, crear_motor, crear_esquema}`.
- Produce:
- `scripts/medir_rnf15.py`:
  - `RAIZ = Path(__file__).resolve().parents[1]`
  - `PARTIDAS = 500`
  - `PERIODOS = 52`
  - `VALUACIONES = 26`
  - `CORRIDAS = 5`
  - `UMBRAL_SEGUNDOS = 2.0`
  - `SEMILLA = 0`
  - `RUTA_SALIDA = RAIZ / 'scripts' / '_salida_rnf15.json'`
  - `def preparar(carpeta: Path, partidas: int, periodos: int, valuaciones: int)`
  - `def trabajo_de_registro(base: Path, obra, carpeta: Path) -> Callable[[int], object]`
  - `def trabajo_de_opciones(base: Path, obra, carpeta: Path) -> Callable[[int], object]`
  - `def main(argv: Sequence[str] | None=None) -> int`
  y `core.budget.valuaciones._precargar(session, version) -> list[object]`.

- [ ] **Paso 0: Expediente SL-E4** (tarea 3): su «Diseño» ya declara la precarga (RP7-9) como el último cambio de S2-4, sin efecto sobre ningún resultado, con una prueba que cuenta sentencias. Visto bueno del tutor anotado en la bitácora.
- [ ] **Paso 1: Escribir las pruebas que fallan**
  La medición (spec S2 §3.3: 500 partidas, 52 períodos semanales, 26 valuaciones; mediana de cinco corridas; límite de 2 s en cada trabajo; solo registra salvo `--estricto`, como RNF-11):
```python
# tests/unit/test_medir_rnf15.py
"""La medición de RNF-15 (spec S2 §3.3): corre, deja su cifra y solo registra (PRU-H21)."""

from __future__ import annotations

import json

from scripts import medir_rnf15


def test_mide_los_dos_trabajos_y_deja_la_cifra_en_su_json(tmp_path):
    salida = tmp_path / "rnf15.json"
    codigo = medir_rnf15.main(
        ["--partidas", "30", "--periodos", "10", "--valuaciones", "5", "--corridas", "2",
         "--salida", str(salida)]
    )  # fmt: skip
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert codigo == 0 and datos["requisito"] == "RNF-15"
    assert (datos["partidas"], datos["periodos"], datos["valuaciones"]) == (30, 10, 5)
    assert len(datos["corridas_registro_s"]) == len(datos["corridas_opciones_s"]) == 2
    assert isinstance(datos["mediana_registro_s"], float) and datos["mediana_registro_s"] > 0
    assert isinstance(datos["mediana_opciones_s"], float) and datos["mediana_opciones_s"] > 0
    assert datos["umbral_s"] == 2.0 and "equipo" in datos


def test_sin_estricto_solo_registra_aunque_supere_el_umbral(tmp_path):
    salida = tmp_path / "rnf15.json"
    argumentos = ["--partidas", "20", "--periodos", "8", "--valuaciones", "4", "--corridas", "1",
                  "--umbral", "0.000001", "--salida", str(salida)]  # fmt: skip
    assert medir_rnf15.main(argumentos) == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["cumple_registro"] is False and datos["cumple_opciones"] is False
    assert medir_rnf15.main([*argumentos, "--estricto"]) == 1


def test_la_ultima_valuacion_se_registra_sobre_una_copia_para_que_cada_corrida_parta_igual(
    tmp_path,
):
    base, obra = medir_rnf15.preparar(tmp_path, 20, 8, 4)
    trabajo = medir_rnf15.trabajo_de_registro(base, obra, tmp_path)
    primera, segunda = trabajo(0), trabajo(1)
    assert primera.indicadores.ev == segunda.indicadores.ev
    assert len(primera.instantanea.valuaciones) == 4  # tres sembradas + la que se mide
    assert (tmp_path / "base.db").stat().st_size > 0
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_medir_rnf15.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'medir_rnf15' from 'scripts'`
```bash
git add tests/unit/test_medir_rnf15.py
git commit -m "test(scripts): medicion de RNF-15 en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima de la medición**
```python
# scripts/medir_rnf15.py
"""Mide RNF-15: el tiempo del control de obra en `ui.control`, sin Streamlit (spec S2 §3.3).

La métrica de la spec de S2 pide, para una obra de 500 partidas, 52 períodos semanales y 26
valuaciones, una mediana de **2 s o menos** en dos trabajos:

1. desde registrar una valuación hasta tener el informe de control, los indicadores, las alertas y
   la reproyección (`ui.control.registrar_y_controlar`), sobre una base con las 25 valuaciones
   anteriores; y
2. calcular las cuatro opciones de recuperación (`ui.control.calcular_las_opciones`).

Genera la obra con el generador determinista (`scripts/generar_obra_control.py`, semilla 0), la
guarda una vez en un archivo SQLite temporal y, para que cada corrida parta del mismo estado,
copia ese archivo antes de cada registro. Hace **una corrida de calentamiento** (no cuenta) y mide
**cinco**; la cifra de cada trabajo es la **mediana**.

Uso:
    uv run python scripts/medir_rnf15.py                  # el tamano de la spec (500/52/26)
    uv run python scripts/medir_rnf15.py --partidas 100   # otro tamaño
    uv run python scripts/medir_rnf15.py --estricto       # sale con 1 si una mediana supera 2 s

**Solo registra.** Sin `--estricto` sale siempre con 0, aunque supere los 2 s: el veredicto de
RNF-15 se toma en el equipo de desarrollo (como RNF-03 y RNF-11) y la CI solo anota la cifra en
Linux y Windows, porque una máquina compartida o cargada no debe romper la corrida. La cifra queda
en `scripts/_salida_rnf15.json` (ignorado por git), de donde la lee la meta de Sílice (C6: sin cifra
no es OK), y se anota en `docs/plan_pruebas.md` §10.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor  # noqa: E402
from scripts import generar_obra_control as generador  # noqa: E402
from scripts.medir_rnf11 import medir  # noqa: E402
from ui import control  # noqa: E402

PARTIDAS = 500
PERIODOS = 52
VALUACIONES = 26
CORRIDAS = 5
UMBRAL_SEGUNDOS = 2.0
SEMILLA = 0
RUTA_SALIDA = RAIZ / "scripts" / "_salida_rnf15.json"


def _url(ruta: Path) -> str:
    return f"sqlite:///{ruta.as_posix()}"


def preparar(carpeta: Path, partidas: int, periodos: int, valuaciones: int):
    """La base con la obra y sus `valuaciones - 1` primeras valuaciones, y la obra generada."""
    obra = generador.generar(partidas, periodos, valuaciones, SEMILLA)
    base = carpeta / "base.db"
    motor = crear_motor(_url(base))
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            generador.sembrar(sesion, obra)
            sesion.commit()
    finally:
        motor.dispose()
    return base, obra


def _filas_de(valuacion) -> list[dict[str, str]]:
    return [
        {
            "Partida": linea.codigo_partida,
            "Cantidad": format(linea.cantidad, "f"),
            "Fecha de medicion": "",
            "Observacion": "",
        }
        for linea in valuacion.lineas
    ]


def trabajo_de_registro(base: Path, obra, carpeta: Path) -> Callable[[int], object]:
    """Registrar la última valuación sobre una copia de la base y obtener el control completo."""
    ultima = obra.valuaciones[-1]

    def trabajo(i: int) -> object:
        copia = carpeta / f"corrida_{i}.db"
        shutil.copy(base, copia)
        motor = crear_motor(_url(copia))
        try:
            with abrir_sesion(motor) as sesion:
                return control.registrar_y_controlar(
                    sesion,
                    generador.NOMBRE,
                    Catalogo(sesion),
                    numero=ultima.numero,
                    desde=ultima.desde.isoformat(),
                    hasta=ultima.hasta.isoformat(),
                    fecha=ultima.fecha.isoformat(),
                    inspector=ultima.inspector,
                    filas=_filas_de(ultima),
                    fuente=generador.FUENTE,
                    responsable=generador.RESPONSABLE,
                    precios=obra.precios,
                )
        finally:
            motor.dispose()

    return trabajo


def trabajo_de_opciones(base: Path, obra, carpeta: Path) -> Callable[[int], object]:
    """Calcular las cuatro opciones de recuperación sobre el control al corte (ya calculado)."""
    copia = carpeta / "opciones.db"
    shutil.copy(base, copia)
    motor = crear_motor(_url(copia))
    try:
        with abrir_sesion(motor) as sesion:  # la última valuación no está en `base`
            generador.registrar_valuacion_de(sesion, obra.valuaciones[-1])
            generador.registrar_costo_de(sesion, obra.costos[-1])
            sesion.commit()
            resultado = control.calcular_el_control(
                sesion, generador.NOMBRE, Catalogo(sesion), precios=obra.precios
            )
    finally:
        motor.dispose()
    return lambda i: control.calcular_las_opciones(resultado)


def _coma(valor: float) -> str:
    return f"{valor:.3f}".replace(".", ",")


def _equipo() -> str:
    return f"{platform.platform()}; {platform.processor() or 'procesador sin nombre'}; " + (
        f"{os.cpu_count()} nucleos; Python {platform.python_version()}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--partidas", type=int, default=PARTIDAS)
    analizador.add_argument("--periodos", type=int, default=PERIODOS)
    analizador.add_argument("--valuaciones", type=int, default=VALUACIONES)
    analizador.add_argument("--corridas", type=int, default=CORRIDAS)
    analizador.add_argument("--umbral", type=float, default=UMBRAL_SEGUNDOS)
    analizador.add_argument("--salida", type=Path, default=RUTA_SALIDA)
    analizador.add_argument(
        "--estricto", action="store_true", help="sale con 1 si una mediana supera el umbral"
    )
    args = analizador.parse_args(argv)

    with tempfile.TemporaryDirectory() as nombre:
        carpeta = Path(nombre)
        base, obra = preparar(carpeta, args.partidas, args.periodos, args.valuaciones)
        registro = medir(trabajo_de_registro(base, obra, carpeta), args.corridas)
        opciones = medir(trabajo_de_opciones(base, obra, carpeta), args.corridas)
    cumple_registro = registro.mediana <= args.umbral
    cumple_opciones = opciones.mediana <= args.umbral
    datos = {
        "requisito": "RNF-15",
        "partidas": args.partidas,
        "periodos": args.periodos,
        "valuaciones": args.valuaciones,
        "corridas_registro_s": [round(c, 6) for c in registro.corridas],
        "mediana_registro_s": round(registro.mediana, 6),
        "corridas_opciones_s": [round(c, 6) for c in opciones.corridas],
        "mediana_opciones_s": round(opciones.mediana, 6),
        "mediana_texto": f"{_coma(registro.mediana)} / {_coma(opciones.mediana)}",
        "umbral_s": args.umbral,
        "cumple_registro": cumple_registro,
        "cumple_opciones": cumple_opciones,
        "equipo": _equipo(),
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    args.salida.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"RNF-15 ({args.partidas} partidas, {args.periodos} periodos, {args.valuaciones} "
        f"valuaciones): registro {_coma(registro.mediana)} s, opciones {_coma(opciones.mediana)} s "
        f"(umbral {_coma(args.umbral)} s)"
    )
    print(f"{'CUMPLE' if cumple_registro and cumple_opciones else 'NO CUMPLE'} (solo registra)")
    return 1 if args.estricto and not (cumple_registro and cumple_opciones) else 0


if __name__ == "__main__":
    raise SystemExit(main())
```
  Y el ignorado de su salida, la fila del README y el paso de la CI:
```gitignore
# Cifra de la medicion de RNF-15 (la lee la meta de la 0.7.0)
scripts/_salida_rnf15.json
```
```markdown
| `medir_rnf15.py` | mide RNF‑15: registrar una valuación y calcular el control, y calcular las opciones de recuperación, sobre la obra de 500 partidas, 52 períodos y 26 valuaciones del generador (mediana de 5 corridas, límite de 2 s en cada trabajo) | RNF‑15 · Sílice 0.7.0 |
```
```yaml
      - name: Medicion de RNF-15
        run: uv run --no-sync python scripts/medir_rnf15.py
```
  (el paso va en el trabajo `pruebas`, después de pytest y antes del paso «Meta de Silice 0.7.0».)
- [ ] **Paso 4: Correrla y ver el verde, y medir**
Run: `uv run pytest tests/unit/test_medir_rnf15.py -v -W error` → 3 pruebas en verde.
Run: `uv run python scripts/medir_rnf15.py` → imprime las dos medianas y deja `scripts/_salida_rnf15.json`. **En esta máquina, sin la precarga, el registro mide unos 2,9 s (sobre el límite) y las opciones unos 0,4 s.** La causa es que `cargar_presupuesto` carga de forma perezosa unas tres filas por renglón (≈ 1 500 consultas para 500 partidas). Como el tiempo varía con la máquina, la corrección se ata a una prueba que cuenta sentencias, no a un número de segundos.
```bash
git add scripts/medir_rnf15.py tests/unit/test_medir_rnf15.py .gitignore scripts/README.md .github/workflows/ci.yml
git commit -m "feat(scripts): medicion de RNF-15 con el generador de obras" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 5: La prueba que cuenta sentencias, el rojo y la corrección**
  La prueba (no mide tiempo: cuenta las sentencias SQL de `instantanea_control` y exige que no crezcan con el número de partidas):
```python
# tests/integration/test_rnf15_consultas.py
"""RNF-15, la causa y no el síntoma: leer una obra para controlarla no hace una consulta por
partida. `cargar_presupuesto` carga de forma perezosa (unas tres consultas por renglón), y para 500
partidas eso es lo que lleva el control sobre los 2 s de RNF-15. La prueba no mide tiempo (varía
con la máquina): cuenta las sentencias SQL de `instantanea_control` y exige que no crezcan con el
número de partidas.
"""

from __future__ import annotations

from sqlalchemy import event

from core.budget.valuaciones import instantanea_control
from core.catalog import Catalogo, abrir_sesion, crear_motor
from scripts import generar_obra_control as generador
from scripts import medir_rnf15

MAXIMO_DE_SENTENCIAS = 40  # medido: 25 con 20 y con 120 partidas; sin precarga, 20 + 3 por partida


def _sentencias(tmp_path, partidas: int) -> int:
    base, _obra = medir_rnf15.preparar(tmp_path, partidas, 8, 4)
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    cuenta = []
    event.listen(motor, "before_cursor_execute", lambda *args: cuenta.append(1))
    try:
        with abrir_sesion(motor) as sesion:
            instantanea_control(sesion, generador.NOMBRE, catalogo=Catalogo(sesion))
    finally:
        motor.dispose()
    return len(cuenta)


def test_leer_la_obra_no_hace_una_consulta_por_partida(tmp_path):
    chica = _sentencias(tmp_path / "a", 20)
    grande = _sentencias(tmp_path / "b", 120)
    assert grande <= MAXIMO_DE_SENTENCIAS, grande
    assert grande - chica <= 2, (chica, grande)  # no crece con las partidas
```
Run: `uv run pytest tests/integration/test_rnf15_consultas.py -v -W error`
Esperado: FAIL con `AssertionError: 380` (`assert 380 <= 40`: sin precarga son 20 sentencias fijas más 3 por partida; 80 con 20 partidas, 200 con 60 y 380 con 120).
```bash
git add tests/integration/test_rnf15_consultas.py
git commit -m "test(core): leer la obra no hace una consulta por partida, en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
  La corrección (RP7-9; trae la versión, sus renglones, ítems, composiciones congeladas y curva en cuatro consultas y conserva las filas mientras `cargar_presupuesto` las lee, porque la sesión las guarda con referencias débiles):
```diff
--- a/core/budget/valuaciones.py
+++ b/core/budget/valuaciones.py
@@ -29,7 +29,7 @@
 from pathlib import Path
 
 from sqlalchemy import select
-from sqlalchemy.orm import Session
+from sqlalchemy.orm import Session, selectinload
 
 from core import models
 from core.budget._modelo import _buscar, _parametros_de
@@ -487,7 +487,9 @@
     plan = plan_de_version(session, version)
     if plan is None:
         raise ValueError(f"la version {version.codigo!r} no tiene plan de trabajo")
+    cargadas = _precargar(session, version)
     presupuesto = cargar_presupuesto(session, proyecto_nombre, version.codigo, catalogo)
+    del cargadas  # el Presupuesto del contrato ya no necesita las filas
     costos = tuple(
         CostoReal(
             c.id,
@@ -516,6 +518,33 @@
         valuaciones=tuple(cuentan),
         costos=costos,
     )
+
+
+def _precargar(session: Session, version: models.Presupuesto) -> list[object]:
+    """Trae de una vez los renglones, sus ítems, las composiciones congeladas y la curva de la
+    versión (cuatro consultas en vez de unas 1 500 cargas perezosas de `cargar_presupuesto`): para
+    una obra de 500 partidas es lo que mantiene el control dentro de RNF-15. Devuelve las filas
+    cargadas: la sesión las guarda con referencias débiles, así que quien llama las conserva
+    mientras lee la versión."""
+    versiones = session.scalars(
+        select(models.Presupuesto)
+        .where(models.Presupuesto.id == version.id)
+        .options(
+            selectinload(models.Presupuesto.partidas).selectinload(
+                models.PartidaPresupuestada.partida
+            ),
+            selectinload(models.Presupuesto.partidas).selectinload(
+                models.PartidaPresupuestada.item_computo
+            ),
+            selectinload(models.Presupuesto.curva),
+        )
+    ).all()
+    composiciones = session.scalars(
+        select(models.ComposicionVersion)
+        .where(models.ComposicionVersion.presupuesto_id == version.id)
+        .options(selectinload(models.ComposicionVersion.lineas))
+    ).all()
+    return [versiones, composiciones]
 
 
 def dia_del_corte(instantanea: InstantaneaControl) -> int:
```
Run: `uv run pytest tests/integration/test_rnf15_consultas.py tests/integration/test_valuaciones.py tests/integration/test_control.py tests/integration/test_decision_crea_version.py -q -W error` → verde: 25 sentencias con 20 y con 120 partidas; ningún resultado cambia.
Run: `uv run python scripts/medir_rnf15.py` → registro ≈ 0,65 s y opciones ≈ 0,36 s (mediana de 5 corridas; 500 partidas, 52 períodos, 26 valuaciones).
Run: `uv run ruff check core/budget/valuaciones.py scripts/medir_rnf15.py tests/unit/test_medir_rnf15.py tests/integration/test_rnf15_consultas.py` y `uv run python scripts/guardia_nucleo.py --base origin/main`.
```bash
git add core/budget/valuaciones.py
git commit -m "perf(core): precargar la version con cuatro consultas para cumplir RNF-15" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS2-4 y foco de revisión de la fase

**Compuerta GS2-4** (se cruza al fusionar `inc/070-s2-4-nucleo`):
1. `uv run python scripts/medir_rnf15.py` y luego `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-4 --junit reporte-pruebas.xml` → todas las filas en OK, incluida C6 con las **dos** cifras de RNF-15 (registro y opciones) leídas de `scripts/_salida_rnf15.json`.
2. CI verde en Linux y Windows, `-W error`, cero omitidas; los pasos «Medicion de RNF-15» y «Meta de Silice 0.7.0 --hasta S2-4».
3. RNF-15 **registra, no rompe** (como RNF-11): si la medición de la CI superara 2 s se anota en la bitácora, no tumba la CI; la prueba que sí es estricta es la de sentencias.
4. Aprobación de los encargos (interfaz, pruebas y calidad) y recorrido a mano de Eugenio; compuerta anotada en `docs/bitacora/2026-10-silice-070.md`.

**Foco de revisión de la medición:**
1. **La medición sin la cifra no es OK:** si el JSON no existe o no trae la clave, C6 queda PENDIENTE y nunca OK → `tests/unit/test_meta_silice_s2.py::test_rnf_15_deja_dos_cifras_en_la_fase_s2_4` (Tarea 1) y `tests/unit/test_medir_rnf15.py::test_mide_los_dos_trabajos_y_deja_la_cifra_en_su_json` (Tarea 14).
2. **Cada corrida parte de la misma base:** la última valuación se registra sobre una copia → `tests/unit/test_medir_rnf15.py::test_la_ultima_valuacion_se_registra_sobre_una_copia_para_que_cada_corrida_parta_igual` (Tarea 14).
3. **La precarga no cambia un resultado:** el control de OB-S2 da la memoria con y sin ella → `tests/integration/test_control.py::test_ob_s2_de_punta_a_punta_da_la_memoria` (Tarea 9, vuelve a correr en la 14).

### Discrepancias encontradas (S2-4)

1. **`ui/reajuste.py` es de S1.** UC-18 enmendado exige que lo ejecutado venga de las valuaciones; el spec de S2 no nombra la pantalla de S1. *Resuelta (RP7-19):* S2 agrega una casilla opcional y dos funciones; nada de S1 cambia si la casilla no se marca.
2. **El spec pone la medición en S2-0.** *Resuelta (RP7-13):* necesita el núcleo, entra en S2-4.
3. **Una corrección de núcleo dentro de la fase de interfaz.** La precarga es `core/`; por eso va en su propia rama de núcleo, `inc/070-s2-4-nucleo`, tras la de interfaz, con el carril único respetado.
4. **«Importar la lista `PROHIBIDOS_EN_UI`».** El spec lo pide; una prueba no importa a otra. *Resuelta (RP7-15):* se copia la tupla y una prueba ata la copia a la original por su contenido.
5. **`test_ui_importable.py` y `test_ui_app.py`.** Fijan el número de páginas y el caso de uso de cada una; la tarea 13 los actualiza (no son pruebas de regresión).

---

# S2-5 — Cierre: versión 0.7.0, manuales, etiqueta y base de prueba (ramas `inc/070-s2-5-cierre` e `inc/070-s2-5-base`)

### Tarea 15: Versión 0.7.0, retiro del alias `ARENIA_*`, manuales, etiqueta y base de prueba de la 0.7.0

**Rama:** `inc/070-s2-5-cierre` (sale de `main` con todo S2 fusionado; PR a `main`) y, tras la etiqueta, `inc/070-s2-5-base` (sale de `origin/main` en `v0.7.0`; PR a `main`)   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear (cierre): `tests/fixtures/caso_s2.py`, `tests/integration/test_caso_s2.py`
- Modificar (cierre): `scripts/generar_base_prueba.py` (`CONSTRUCTORES` gana `"s2.db"`), `tests/unit/test_generar_base_prueba.py` (`test_los_casos_de_la_base_de_prueba`), `pyproject.toml:3` (`version = "0.7.0"`), `uv.lock` (con `uv lock`), `CHANGELOG.md`, `docs/manual_usuario.md` (§3.10, antes de «## 4. El informe de auditoría»; y se retira la nota de los nombres anteriores de las variables), `docs/manual_tecnico.md` (§14 nuevo al final; y se retira la misma nota), `docs/plan_pruebas.md` (matriz de UC-19 y UC-20 completa), `ui/entorno.py` (`ALIAS_ANTERIORES = {}`), `tests/unit/test_entorno_silice.py`, `tests/unit/test_nombre_silice.py`, `.github/workflows/ci.yml` (`--hasta S2-5`)
- Crear (base): `tests/integration/test_base_0_7_0.py`, `tests/fixtures/bases/v0_7_0/demo.db`, `of001.db`, `ti001.db`, `s1.db`, `s2.db` y `ficha.json` (**generados** con el código de `v0.7.0`, procedimiento de la sección B)
- Modificar (base): `.github/workflows/ci.yml` (el paso de la meta ya dice `--hasta S2-5`), `docs/bitacora/2026-10-silice-070.md` (compuerta GS2)

**Interfaces:**
- Consume: de la sección B: `scripts/generar_base_prueba.py` (`CONSTRUCTORES: dict[str, Callable[[Path], object]]`, `main(["--salida", …, "--version", …, "--etiqueta", …, "--commit", …])`, que llama a `preparar_base` antes de cada constructor), `tests.fixtures.bases_prueba.{copiar_base, diferencias_con_ficha, ficha, nombres}`, `operacion.base_datos.{preparar_base, leer_estado, revision_head, Destino}`; de las tareas 5 a 11: `tests.fixtures.control_ob_s2`, `core.budget.control.{calcular_control, composiciones_de_la_linea_base, contexto_de_recuperacion}`, `core.budget.recuperacion.opciones`, `core.budget.decision.{aplicar_decision, decisiones}`; de A1: `ui.entorno.{ALIAS_ANTERIORES, ULTIMA_VERSION_CON_ALIAS, leer_variable}`.
- Produce:
- `tests/fixtures/caso_s2.py`:
  - `MOMENTO_DE_LA_DECISION = datetime(2026, 11, 16, 10, 0)`
  - `def sembrar_caso_s2(sesion) -> None`
  - `def plantilla_s2(ruta: Path) -> Path`
  y `tests/fixtures/bases/v0_7_0/` con su `ficha.json` (formato de la sección B: `version`, `etiqueta`, `commit`, `bases` con `revision_alembic`, `sha256_base`, total e huella del informe), con cinco bases en `caso_0006_s2_decision`.

- [ ] **Paso 1: Escribir las pruebas que fallan (rama `inc/070-s2-5-cierre`)**
En `tests/unit/test_generar_base_prueba.py`, `test_los_casos_de_la_base_de_prueba` pasa a:
```python
def test_los_casos_de_la_base_de_prueba() -> None:
    assert list(generador.CONSTRUCTORES) == ["demo.db", "of001.db", "ti001.db", "s1.db", "s2.db"]
```
Y el caso S2 se siembra en una base nueva en `head` y da lo que dice la memoria:
```python
# tests/integration/test_caso_s2.py
"""El caso S2 que alimenta la base de prueba de la 0.7.0: se siembra en una base nueva en `head` y
da lo que dice la memoria `control_ob_s2.md` (PRU-H15)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from core import models
from core.budget.decision import decisiones
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures.caso_s2 import plantilla_s2

D = Decimal


def test_la_plantilla_s2_siembra_la_obra_sus_valuaciones_y_su_decision(tmp_path: Path) -> None:
    ruta = tmp_path / "s2.db"
    preparar_base(ruta)
    plantilla_s2(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            numeros = sesion.scalars(select(models.Valuacion.numero).order_by(models.Valuacion.id))
            assert list(numeros) == ["V-01", "V-02"]
            codigos = sesion.scalars(
                select(models.Presupuesto.codigo).order_by(models.Presupuesto.id)
            )
            assert list(codigos) == ["OB-001", "OB-002"]
            (decision,) = decisiones(sesion, "OB-S2")
            assert (decision.opcion, decision.termino.isoformat()) == ("cuadrillas", "2026-11-24")
            assert decision.costo_directo_adicional == D(120)
            registros = sesion.scalars(
                select(models.RegistroCambio).where(models.RegistroCambio.objeto == "plan")
            ).all()
            assert len(registros) == 7
    finally:
        motor.dispose()
```
  El alias `ARENIA_*` de A1 vence con la 0.6.0: `test_el_alias_se_retira_despues_de_la_0_6_0` falla en cuanto `pyproject.toml` dice 0.7.0 con el alias todavía declarado. Las pruebas que ejercen el alias pasan a ejercer su retiro (cuatro cambios en `tests/unit/test_entorno_silice.py` y dos en `tests/unit/test_nombre_silice.py`; el resto de los dos archivos no cambia):
```diff
--- a/tests/unit/test_entorno_silice.py
+++ b/tests/unit/test_entorno_silice.py
@@ test_los_alias_son_exactamente_los_de_arenia @@
-def test_los_alias_son_exactamente_los_de_arenia() -> None:
+def test_los_alias_estan_retirados_desde_la_0_7_0() -> None:
     assert VARIABLE_CASO == "SILICE_CASO"
     assert VARIABLE_MODO_ENTREGA == "SILICE_MODO_ENTREGA"
-    assert ALIAS_ANTERIORES == dict(PARES)
+    assert ALIAS_ANTERIORES == {}
@@ test_solo_la_vieja @@
 @pytest.mark.parametrize(("nueva", "vieja"), PARES)
-def test_solo_la_vieja(nueva: str, vieja: str) -> None:
-    assert leer_variable({vieja: "b"}, nueva) == "b"
+def test_solo_la_vieja_ya_no_se_lee(nueva: str, vieja: str) -> None:
+    assert leer_variable({vieja: "b"}, nueva) is None
@@ test_la_variable_nueva_en_blanco_cede_al_alias @@
 @pytest.mark.parametrize(("nueva", "vieja"), PARES)
-def test_la_variable_nueva_en_blanco_cede_al_alias(nueva: str, vieja: str) -> None:
-    assert leer_variable({nueva: "  ", vieja: "b"}, nueva) == "b"
+def test_la_variable_nueva_en_blanco_ya_no_cede_a_ningun_alias(nueva: str, vieja: str) -> None:
+    assert leer_variable({nueva: "  ", vieja: "b"}, nueva) is None
     assert leer_variable({nueva: "  "}, nueva) is None
@@ test_el_caso_y_el_modo_entrega_leen_con_el_ayudante @@
-def test_el_caso_y_el_modo_entrega_leen_con_el_ayudante() -> None:
-    assert resolver_ruta(None, {"ARENIA_CASO": "viejo.db"}, "d.db") == Path("viejo.db")
+def test_el_caso_y_el_modo_entrega_ignoran_los_nombres_anteriores() -> None:
+    assert resolver_ruta(None, {"ARENIA_CASO": "viejo.db"}, "d.db") == Path("d.db")
     entorno = {"SILICE_CASO": "nuevo.db", "ARENIA_CASO": "viejo.db"}
     assert resolver_ruta(None, entorno, "d.db") == Path("nuevo.db")
-    assert modo_entrega_activo({"ARENIA_MODO_ENTREGA": "1"}) is True
-    assert modo_entrega_activo({"SILICE_MODO_ENTREGA": "0", "ARENIA_MODO_ENTREGA": "1"}) is False
+    assert modo_entrega_activo({"ARENIA_MODO_ENTREGA": "1"}) is False
+    assert modo_entrega_activo({"SILICE_MODO_ENTREGA": "0", "ARENIA_MODO_ENTREGA": "1"}) is False
     assert modo_entrega_activo({"SILICE_MODO_ENTREGA": "1"}) is True
--- a/tests/unit/test_nombre_silice.py
+++ b/tests/unit/test_nombre_silice.py
@@ PERMITEN_VARIABLE_VIEJA @@
-PERMITEN_VARIABLE_VIEJA = frozenset(
-    {"ui/entorno.py", "docs/manual_usuario.md", "docs/manual_tecnico.md"}
-)
+PERMITEN_VARIABLE_VIEJA = frozenset({"ui/entorno.py"})
@@ test_los_manuales_anuncian_el_alias_y_su_retiro @@
-def test_los_manuales_anuncian_el_alias_y_su_retiro() -> None:
+def test_los_manuales_ya_no_anuncian_el_alias() -> None:
     for ruta in ("docs/manual_usuario.md", "docs/manual_tecnico.md"):
         texto = _texto(ruta)
-        assert "SILICE_CASO" in texto and "ARENIA_CASO" in texto, ruta
-        assert "hasta la 0.6.0" in texto, ruta
+        assert "SILICE_CASO" in texto and "ARENIA_CASO" not in texto, ruta
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_generar_base_prueba.py tests/integration/test_caso_s2.py -v -W error`
Esperado: FAIL con `AssertionError` en la lista de `CONSTRUCTORES` (no trae `"s2.db"`) y `ModuleNotFoundError: No module named 'tests.fixtures.caso_s2'`.
Run: `sed -i 's/^version = ".*"$/version = "0.7.0"/' pyproject.toml && uv run pytest tests/unit/test_entorno_silice.py::test_el_alias_se_retira_despues_de_la_0_6_0 -v -W error`
Esperado: FAIL con `AssertionError: pyproject dice 0.7.0: la 0.7.0 ya no acepta ARENIA_*; vacie ALIAS_ANTERIORES y retire la nota de alias de los dos manuales`.
```bash
git add tests/unit/test_generar_base_prueba.py tests/integration/test_caso_s2.py tests/unit/test_entorno_silice.py tests/unit/test_nombre_silice.py
git commit -m "test(release): caso S2 para la base de prueba y retiro del alias ARENIA en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima (cierre)**
```python
# tests/fixtures/caso_s2.py
"""El caso S2 de la base de prueba de la 0.7.0 (RV-3, PRU-H15; plan 0.7.0, tarea 15).

Una base en `head` con lo que agrega S2: la obra OB-S2 de la memoria `control_ob_s2.md` con su
línea base de control, V-01 y V-02 registradas, el costo incurrido de 1 280,00 USD y la decisión «más
cuadrillas» tomada al corte (versión `OB-002`, motivo `recuperacion`, siete cambios de plan). Las
fechas de registro son fijas, así que la base se reconstruye igual.
`scripts/generar_base_prueba.py` la construye con el código de la etiqueta `v0.7.0`, después de
que `preparar_base` la creó en `head`. Datos ficticios (NORMAS.md §1).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.budget.control import (
    calcular_control,
    composiciones_de_la_linea_base,
    contexto_de_recuperacion,
)
from core.budget.decision import aplicar_decision
from core.budget.recuperacion import opciones
from core.catalog import Catalogo, abrir_sesion, crear_motor
from tests.fixtures import control_ob_s2 as ob

MOMENTO_DE_LA_DECISION = datetime(2026, 11, 16, 10, 0)


def sembrar_caso_s2(sesion) -> None:
    """OB-S2 con sus dos valuaciones, su costo y la decisión «más cuadrillas». No confirma."""
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion)
    ob.registrar_v01_y_v02(sesion)
    catalogo = Catalogo(sesion)
    resultado = calcular_control(
        sesion, ob.NOMBRE, catalogo=catalogo, precios=ob.precios_del_corte()
    )
    contexto = contexto_de_recuperacion(resultado, composiciones_de_la_linea_base(resultado))
    cuadrillas = next(o for o in opciones(contexto) if o.nombre == "cuadrillas")
    aplicar_decision(
        sesion,
        resultado,
        cuadrillas,
        catalogo=catalogo,
        fuente="base de prueba 0.7.0",
        responsable=ob.RESPONSABLE,
        ahora=MOMENTO_DE_LA_DECISION,
    )


def plantilla_s2(ruta: Path) -> Path:
    """Siembra el caso S2 en `ruta` (ya en `head`) y confirma."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_caso_s2(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta
```
  `scripts/generar_base_prueba.py`: el caso S2 entra como quinta base. En el docstring, «Cuatro bases» pasa a «Cinco bases (la quinta, desde la 0.7.0)» y se agrega, tras la viñeta de `s1.db`: «`s2.db` (desde la 0.7.0): el caso S2, la obra OB-S2 con su línea base de control, V-01 y V-02, el costo real y la decisión «más cuadrillas» (`tests.fixtures.caso_s2.plantilla_s2`)».
```python
from tests.fixtures.caso_s2 import plantilla_s2  # noqa: E402

CONSTRUCTORES: dict[str, Callable[[Path], object]] = {
    "demo.db": _demo,
    "of001.db": plantilla_of001,
    "ti001.db": plantilla_ti001,
    "s1.db": plantilla_s1,
    "s2.db": plantilla_s2,
}
```
  Retiro del alias en `ui/entorno.py` (la función `leer_variable` no cambia: su bucle ya salta a un alias `None`). El texto del módulo cuenta la historia; la tabla queda vacía:
```diff
--- a/ui/entorno.py
+++ b/ui/entorno.py
@@ docstring @@
-Desde la 0.6.0 se llaman `SILICE_CASO` y `SILICE_MODO_ENTREGA`; `ARENIA_CASO` y
-`ARENIA_MODO_ENTREGA` se aceptan como alias solo hasta la 0.6.0 inclusive
-(`tests/unit/test_entorno_silice.py` falla cuando `pyproject.toml` pase de esa versión con el alias
-todavía declarado).
+Desde la 0.6.0 se llaman `SILICE_CASO` y `SILICE_MODO_ENTREGA`; `ARENIA_CASO` y
+`ARENIA_MODO_ENTREGA` se aceptaron como alias hasta la 0.6.0 inclusive y desde la 0.7.0 ya no se
+leen (`tests/unit/test_entorno_silice.py` falla si `pyproject.toml` pasa de esa versión con el alias
+declarado).
@@ ALIAS_ANTERIORES @@
-ALIAS_ANTERIORES: dict[str, str] = {
-    VARIABLE_CASO: "ARENIA_CASO",
-    VARIABLE_MODO_ENTREGA: "ARENIA_MODO_ENTREGA",
-}
+ALIAS_ANTERIORES: dict[str, str] = {}
```
  Versión, candado y `CHANGELOG.md`, desde la raíz del worktree en Git Bash:
```bash
sed -i 's/^version = ".*"$/version = "0.7.0"/' pyproject.toml
grep -n '^version = "0.7.0"$' pyproject.toml
uv lock
uv run python - <<'EOF'
from datetime import date
from pathlib import Path

ruta = Path("CHANGELOG.md")
texto = ruta.read_text(encoding="utf-8")
assert texto.count("## [Sin publicar]") == 1
nueva = f"## [Sin publicar]\n\n## [0.7.0] - {date.today().isoformat()}"
ruta.write_text(texto.replace("## [Sin publicar]", nueva), encoding="utf-8")
EOF
```
  Bajo `## [0.7.0]` del `CHANGELOG.md` quedan estas líneas (las de S2-0 ya estaban bajo `[Sin publicar]`; se agregan las demás):
```markdown
- Control de obra (S2): valuaciones por cantidades ejecutadas (a mano o por Excel), línea base de control y calendario, valor ganado con separación del desvío en plazo, precio y consumo, alertas AL-1 a AL-6, reproyección de plan, término, costo final y punto de equilibrio, y opciones de recuperación con su decisión (versión `recuperacion`).
- Reglas externas R13 y R14 (valuación dentro del presupuesto; fuente y fechas de la valuación), fuera de `REGLAS`.
- El estudio de reajuste de S1 puede tomar lo ejecutado de las valuaciones y las cita; el punto de equilibrio proyectado suma el reajuste ya reconocido.
- Dos revisiones de Alembic aditivas: `caso_0005_s2_valuaciones` y `caso_0006_s2_decision` (nueve tablas).
- Retirado: los nombres de variable `ARENIA_CASO` y `ARENIA_MODO_ENTREGA` ya no se leen; use `SILICE_CASO` y `SILICE_MODO_ENTREGA`.
- Medición de RNF-15 (`scripts/medir_rnf15.py`) y base de prueba de la 0.7.0.
```
  `docs/manual_usuario.md` (se retira la nota «Nombres de las variables» de la 0.6.0, que ya no corresponde) y la sección nueva, **antes** de «## 4. El informe de auditoría», tras la §3.9:
````markdown
### 3.10 Control de obra: valuaciones, valor ganado, alertas y recuperación (UC‑19 y UC‑20)

Desde la versión 0.7.0, cuando la obra está en marcha, usted registra lo **ejecutado** y el sistema le dice cómo va
contra el plan, cuánto de la desviación es de **plazo**, de **precio** o de **consumo**, y qué cuesta recuperar un
retraso. Todo vive en la pantalla **Control de obra** (sección Trabajo; también la abre el botón **Registrar valuacion**
de la barra). Las cifras de los ejemplos son ficticias.

**1. Línea base.** En la pestaña **Línea base** elija la versión del contrato, la perspectiva (**costo** o **precio**), la
fecha de inicio, los días hábiles por período y los feriados; escriba la fuente y el responsable y pulse **Declarar linea
base**. Si después cambia la moneda del proyecto, la línea base queda invalidada y el sistema le pide declararla de nuevo.
Más abajo están los **parámetros de control** (umbrales de las alertas, eficiencia de las cuadrillas, horas extra,
penalización del contrato); cada uno dice si es un supuesto declarado o un dato del contrato, y cada cambio deja su
registro.

**2. Valuaciones.** En **Valuaciones** escriba la nueva (número, período desde/hasta, fecha, inspector) con sus líneas
(partida y cantidad **del período**), la fuente y el responsable, y pulse **Registrar y controlar**; o suba un `.xlsx`
con las hojas `Valuaciones`, `Lineas` y `Costos` (el sistema le muestra un informe antes de guardar; un archivo con un
error se rechaza **entero**). Una valuación registrada **cuenta desde ese momento**: no hay estado «aprobada». No se
edita: si se equivocó, **anúlela** con su motivo y registre otra. La tabla muestra la **fecha de registro** de cada una
y su **Estado** (el peor hallazgo de R13, «lo ejecutado no supera lo presupuestado», y R14, «fuente y fechas en orden»).
En la misma pestaña anota los **costos reales** (monto, moneda, fecha y fuente); uno en bolívares se convierte con la
tasa del BCV de su fecha, y si no hay tasa de esa fecha el sistema lo dice y deja el costo real «no disponible».

**3. Valor ganado.** Con la línea base y al menos una valuación, **Valor ganado** muestra, al corte, el valor planificado
(PV), el ganado (EV), el costo real (AC), los índices SPI y CPI, el costo final estimado (EAC) y la variación al término
(VAC), cada monto en las dos monedas con la tasa del corte. La **separación del desvío** parte la variación de costo
en **precio** (lo que la obra ejecutada cuesta de más por los precios de hoy) y **consumo** (el resto); para ver el
precio elija en **Precios del corte** el método: ninguno, **comprobación directa** (una versión revalorada) o
**escalatoria**. Sin precios la separación dice «no disponible» y el resto sigue funcionando. Las fórmulas son
**definiciones del sistema** mientras no se verifique su fuente (se indica en pantalla).

**4. Alertas y reproyección.** Se ven al abrir, sin pedirlas: AL‑1 (SPI), AL‑2 (CPI), AL‑3 (retraso del término), AL‑4
(el punto de equilibrio proyectado ya no se alcanza), AL‑5 (desviación de precio) y AL‑6 (partidas detenidas), cada una
con su severidad y el umbral que la disparó. Debajo, el **término** por los dos métodos, el EAC, el **punto de
equilibrio proyectado** (con el reajuste ya reconocido por los estudios guardados de **Reajuste de precios**, que se
citan) y el **plan reproyectado** por partida.

**5. Recuperación.** Pulse **Calcular opciones** (a pedido): **más cuadrillas**, **horas extra** (dentro de los límites de
la LOTTT que se citan), **partidas en paralelo** (exige declarar que no dependen de las que están en curso) y **aceptar el
retraso**. Cada una muestra su término, su costo adicional, su costo indirecto, su punto de equilibrio y los **supuestos**
con su naturaleza. Elija una, escriba la fuente y el responsable y pulse **Elegir y crear la version**: se crea una
**versión nueva** del presupuesto (motivo `recuperacion`) con su plan, su curva y un registro por cada cambio del plan; la
línea base **no cambia**. Una partida sin mano de obra a jornal da «no aplica» en las dos primeras opciones.

**Reajuste desde las valuaciones.** En **Reajuste de precios** marque **Tomar lo ejecutado de las valuaciones
registradas**: cada valuación va entera al período de su fecha *hasta*, y el estudio guardado cita cuáles usó.

| Si ve… | Haga… |
|---|---|
| «linea base invalidada: declarela de nuevo» | Cambió la moneda del proyecto: declare la línea base otra vez en **Línea base** |
| Estado ERROR en una valuación (R13) | Lo ejecutado supera lo presupuestado o la partida no existe: registre la variación de obra en la hoja y declare una nueva línea base |
| Estado ERROR en una valuación (R14) | Falta el inspector o el número, o las fechas no cuadran: anule y registre de nuevo con los datos correctos |
| «AC no disponible» | Un costo en bolívares no tiene tasa del BCV de su fecha: impórtela en **Indices del BCV** |
| «no aplica» en una opción | La partida determinante no tiene mano de obra a jornal: elija otra opción |
| «Separación no disponible» | Elija el método de **Precios del corte** |
````
  `docs/manual_tecnico.md` (se retira la misma nota de variables) y la sección nueva al final:
````markdown
## 14. Control de obra: valuaciones, valor ganado y recuperación (Sílice 0.7.0, S2)

Spec: `docs/especificaciones/2026-10-11-silice-s2-presupuesto-vivo-design.md`. Tres expedientes de núcleo (SL‑E4 a
SL‑E6, en `docs/bitacora/2026-10-silice-s2-expedientes.md`); ningún contrato de `core/contracts/` cambió.

| Paquete | Qué hace |
|---|---|
| `core/models/control.py` | Las nueve tablas aditivas de S2 (línea base, calendario, parámetros, valuación, línea de valuación, anulación, costo real, cita de valuación, decisión), reexportadas en `core.models`. Revisiones `caso_0005_s2_valuaciones` y `caso_0006_s2_decision` |
| `core/budget/calendario.py` | Funciones puras de días hábiles (lunes a viernes menos feriados declarados) |
| `core/verification/valuaciones.py` | Tipos de valuación y las reglas **externas** R13 y R14, fuera de `REGLAS`; reciben una instantánea con `habiles_entre` inyectado |
| `core/budget/valuaciones.py` | Registro, anulación, instantánea de control, lector de Excel, `ejecutado_por_periodo`; solo-agregar |
| `core/budget/puente.py` | `estudio_con_valuaciones` (S1 ← S2) y `reajuste_reconocido` (S2 ← S1) |
| `core/budget/valor_ganado.py` | Funciones puras: indicadores, separación del desvío, reproyección, alertas, `equilibrio_proyectado` |
| `core/budget/control.py` | Orquesta la instantánea, el estado y los precios del corte; `calcular_control` no escribe |
| `core/budget/recuperacion.py` | Las cuatro opciones (puras): `E(k) = Σ η^(j‑1)`, límites de la LOTTT, supuestos con naturaleza |
| `core/budget/decision.py` | `aplicar_decision`: versión `recuperacion` por `guardar_edicion(motivo=...)` y el embudo único |
| `ui/control.py`, `ui/paginas/control.py` | La lógica sin Streamlit y la pantalla de cinco pestañas; la página abre el caso con `preparar_base` |

**Reglas que no se rompen.** Se guardan **entradas y decisiones**; indicadores, alertas y hallazgos se **recalculan** (S2‑R13).
Valuaciones y costos son solo‑agregar (`tests/unit/test_arquitectura_s2.py` vigila que ningún módulo emita `UPDATE` ni
`DELETE` sobre ellas). `valor_ganado.py`, `calendario.py` y `recuperacion.py` son puros: sin `sqlalchemy` ni `core.models`.
Toda versión nueva nace en `guardar_presupuesto`. Los umbrales de las alertas, `η`, `k_máx` y el multiplicador de horas
extra son **parámetros** (`parametros_control`), nunca constantes del código.

**Dónde vive cada supuesto (S2‑R1 a S2‑R17, spec S2 §12).** Separación y EAC: `separar_desvio` e `indicadores`
(`valor_ganado.py`). Umbrales: `ParametrosControl`. Calendario hábil: `calendario.py` (S2‑R9). Reajuste reconocido:
`puente.reajuste_reconocido` (S2‑R15). Modelo de cuadrillas y límites legales: `recuperacion.py`. Cambiar uno es cambiar esa
función pura y su memoria `tests/fixtures/memorias/control_ob_s2.md`, con expediente.

**Rendimiento (RNF‑15).** `instantanea_control` precarga la versión con cuatro consultas (`_precargar`); sin ella cada
renglón costaba unas tres cargas perezosas. Se vigila con `tests/integration/test_rnf15_consultas.py` (cuenta
sentencias) y se mide con `scripts/medir_rnf15.py` sobre `scripts/generar_obra_control.py`.

**Oráculos.** La memoria a mano `control_ob_s2.md` y su XLSX se versionaron antes que el código (`S2‑MEM`); sus cuentas se
rehacen con `fractions.Fraction` en `tests/unit/test_memoria_ob_s2.py`. La base de prueba de la 0.7.0
(`tests/fixtures/bases/v0_7_0/`, con `s2.db`) se generó con el código de la etiqueta `v0.7.0`.
````
  `docs/plan_pruebas.md`: la matriz por paso de UC‑19 y UC‑20 (las dos filas que abrió la tarea 1) se completa nombrando, por flujo y por alternativo, las pruebas de las tareas 5 a 13 (p. ej. 4a ⇒ `test_sin_numero_ni_inspector_se_guarda_y_r14_la_marca`; 4b ⇒ `test_la_valuacion_sembrada_da_exactamente_los_seis_hallazgos_de_la_memoria`; 4c ⇒ `test_una_valuacion_anulada_se_conserva_y_deja_de_contar`; 4d ⇒ `test_r14_periodos_solapados`; paso 4 de UC‑20 ⇒ `test_las_opciones_se_calculan_a_pedido_y_elegir_una_crea_la_version`).
  `.github/workflows/ci.yml`, paso «Meta de Silice 0.7.0»: `--hasta S2-5`.
- [ ] **Paso 4: Correrlas y ver el verde; PR, fusión y etiqueta**
Run: `uv run pytest tests/unit/test_generar_base_prueba.py tests/integration/test_caso_s2.py tests/unit/test_entorno_silice.py tests/unit/test_nombre_silice.py tests/unit/test_ui_app.py -v -W error` → verde; `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml`; `uv run python scripts/medir_rnf15.py`; `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-4 --junit reporte-pruebas.xml` → todas las filas en OK salvo `S2-BASE-070` (fase `S2-5`, PENDIENTE hasta el paso 5); `uv run ruff check` sobre los archivos tocados; `uv run python scripts/guardia_nucleo.py --base v0.6.0`.
```bash
git add tests/fixtures/caso_s2.py scripts/generar_base_prueba.py ui/entorno.py pyproject.toml uv.lock CHANGELOG.md docs/manual_usuario.md docs/manual_tecnico.md docs/plan_pruebas.md .github/workflows/ci.yml
git commit -m "chore(release): Silice 0.7.0 con el caso S2 para su base de prueba y sin el alias ARENIA" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push -u origin inc/070-s2-5-cierre
gh pr create --base main --head inc/070-s2-5-cierre --title "S2-5: Silice 0.7.0" --body-file -
gh pr merge <n> --merge
git fetch origin --tags
git tag -a v0.7.0 -m "Silice 0.7.0: S2 (valuaciones, valor ganado, alertas y recuperacion)" origin/main
git push origin v0.7.0
```
  (La etiqueta marca el código; la base de prueba se genera **de** ella en el paso siguiente, como la de la 0.5.0 y la 0.6.0.)
- [ ] **Paso 5: Base de prueba de la 0.7.0 (rama `inc/070-s2-5-base`)**
```bash
git switch -c inc/070-s2-5-base origin/main
```
Prueba primero (la ficha es de la etiqueta; la base `s2.db` conserva la decisión y el control recalcula igual):
```python
# tests/integration/test_base_0_7_0.py
"""RV-3, PRU-H15: la base de prueba de la 0.7.0, generada con el código de la etiqueta v0.7.0, abre
por `preparar_base` y recarga igual que su ficha (sección B, `tests/fixtures/bases_prueba.py`)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from core import models
from core.budget.decision import decisiones
from core.budget.valuaciones import instantanea_control
from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from tests.fixtures.bases_prueba import copiar_base, diferencias_con_ficha, ficha, nombres

D = Decimal


def test_la_ficha_es_de_la_etiqueta_v0_7_0() -> None:
    datos = ficha("0.7.0")
    assert (datos["version"], datos["etiqueta"]) == ("0.7.0", "v0.7.0")
    assert sorted(datos["bases"]) == ["demo.db", "of001.db", "s1.db", "s2.db", "ti001.db"]
    assert {b["revision_alembic"] for b in datos["bases"].values()} == {"caso_0006_s2_decision"}


@pytest.mark.parametrize("nombre", nombres("0.7.0"))
def test_cada_base_0_7_0_abre_en_head_y_recarga_su_ficha(tmp_path: Path, nombre: str) -> None:
    ruta = copiar_base("0.7.0", nombre, tmp_path / nombre)
    preparar_base(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert diferencias_con_ficha(ruta, ficha("0.7.0")["bases"][nombre]) == []


def test_la_base_s2_conserva_la_decision_y_el_control_recalcula_igual(tmp_path: Path) -> None:
    ruta = copiar_base("0.7.0", "s2.db", tmp_path / "s2.db")
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            (decision,) = decisiones(sesion, "OB-S2")
            assert (decision.version, decision.opcion) == ("OB-002", "cuadrillas")
            assert len(sesion.scalars(select(models.Valuacion)).all()) == 2
            instantanea = instantanea_control(sesion, "OB-S2", catalogo=Catalogo(sesion))
            assert instantanea.linea_base.version == "OB-001"
            assert [v.numero for v in instantanea.valuaciones] == ["V-01", "V-02"]
    finally:
        motor.dispose()
```
Run: `uv run pytest tests/integration/test_base_0_7_0.py -v -W error` → error de colección `FileNotFoundError: …/tests/fixtures/bases/v0_7_0/ficha.json`.
```bash
git add tests/integration/test_base_0_7_0.py
git commit -m "test(migraciones): base de prueba de v0.7.0 contra su ficha en rojo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
Generación (procedimiento de la sección B con la etiqueta nueva), en Git Bash desde la raíz del worktree:
```bash
REPO="$(pwd)"
V070="${TMPDIR:-/tmp}/silice-v0.7.0"
rm -rf "$V070" && mkdir -p "$V070"
git archive v0.7.0 | tar -x -C "$V070"
(
  cd "$V070" && unset VIRTUAL_ENV \
  && export UV_PROJECT_ENVIRONMENT="$V070/.venv" \
  && uv sync --frozen --all-extras \
  && uv run --frozen python scripts/generar_base_prueba.py \
       --salida "$REPO/tests/fixtures/bases/v0_7_0" --version 0.7.0 --etiqueta v0.7.0 \
       --commit "$(git -C "$REPO" rev-parse 'v0.7.0^{commit}')"
)
```
(`scripts/generar_base_prueba.py` ya está en el árbol de la etiqueta: no se copia.) El paso de la meta en `.github/workflows/ci.yml` ya dice `--hasta S2-5`.
Run: `uv run pytest tests/integration/test_base_0_7_0.py tests/integration/test_base_0_6_0.py tests/integration/test_base_prueba_v0_5_0.py -v -W error` → verde; `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml`; `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-5 --junit reporte-pruebas.xml` → todas las filas en OK (incluida `S2-BASE-070`).
```bash
git add tests/fixtures/bases/v0_7_0/demo.db tests/fixtures/bases/v0_7_0/of001.db tests/fixtures/bases/v0_7_0/ti001.db tests/fixtures/bases/v0_7_0/s1.db tests/fixtures/bases/v0_7_0/s2.db tests/fixtures/bases/v0_7_0/ficha.json docs/bitacora/2026-10-silice-070.md
git commit -m "test(migraciones): bases de prueba de v0.7.0 y su ficha generadas con el codigo de la etiqueta" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push -u origin inc/070-s2-5-base
gh pr create --base main --head inc/070-s2-5-base --title "S2-5: base de prueba de v0.7.0" --body-file -
```
Fusionar con `gh pr merge <n> --merge` con la CI verde: con esa fusión se cruza GS2.

---

## Compuerta GS2 (etiqueta `v0.7.0`; se cruza al fusionar `inc/070-s2-5-base`)

1. `uv run python scripts/meta_silice.py --version 0.7.0 --hasta S2-5 --junit reporte-pruebas.xml` → `RESULTADO` con todas las filas en OK: C1 (los requisitos de la 0.6.0 y los diez de S2 por presencia), C2 (cero omitidas), C3 (cada `ParTDD` de `S2-0` a `S2-4`: la prueba precede a su código; el expediente precede a sus tablas), C4 (`core/contracts/` intacto desde `v0.6.0`), C5 (bloque `REGRESION`: sus `ARCHIVOS_REGRESION` sin cambios desde `v0.6.0` y sus pruebas en verde), C6 (las cifras de RNF‑11 y las dos de RNF‑15), C7 (guardia de red), `S2-MEM`, `S2-REGLAS`, `S2-EXPEDIENTES`, `S2-REG-S1` y `S2-BASE-070`.
2. CI verde en Linux y Windows, `HF_HUB_OFFLINE=1`, `-W error`, y el paso de la meta en `--hasta S2-5`.
3. **Bloque de regresión literal** (sección siguiente) en verde sin editar una sola de esas pruebas.
4. Prueba de deriva RNF‑20 de la sección B en verde con las revisiones `caso_0005_s2_valuaciones` y `caso_0006_s2_decision`; las bases de `tests/fixtures/bases/v0_5_0/`, `v0_6_0/` y `v0_7_0/` abren por `preparar_base` y recargan igual que su ficha.
5. `uv run python scripts/guardia_nucleo.py --base v0.6.0` en 0; `uv run ruff check` sobre los archivos tocados.
6. Aprobación de los encargos (requisitos, arquitectura, pruebas y calidad, verificador de hechos: fórmulas de valor ganado, Lee 2022 y LOTTT, con su resultado anotado) y aval del tutor de SL‑E4, SL‑E5 y SL‑E6; compuerta anotada en `docs/bitacora/2026-10-silice-070.md` con la tabla literal de la meta.
7. Recorrido a mano de Eugenio con la base `s2.db` (registrar, ver las alertas, calcular las opciones, abrir la versión `OB-002`) y la prueba del Excel exportado desde la hoja con las tres hojas de control.

---

# Cierre del plan

## Bloque de regresión (literal)

El de la sección A de la 0.6.0 (`REGRESION` y `ARCHIVOS_REGRESION` de `scripts/meta_silice.py`), sin listas propias. Ninguna
de estas pruebas se edita en la 0.7.0; si un cambio moviera alguna, se registra un ruling de reanclaje y se detiene la fase:
- cinco APU a ± 0,01: `tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base` y `tests/unit/test_linea_base.py`;
- 7 de 7: `tests/integration/test_auditoria_7_de_7.py`;
- R4 de 3/4 pulg: `tests/unit/test_verification.py::test_r4_marca_3_4_pulg_y_no_marca_pvc`;
- TI-001 total, PU y PE 28 586,76 USD en el Día 6: `tests/unit/test_caso_ti001.py` (`::test_total_y_cierre_de_la_curva`, `::test_precios_unitarios`, `::test_punto_de_equilibrio`) y `tests/unit/test_equilibrio.py`, que la extracción de `equilibrio` (tarea 7) debe dejar en verde;
- dos huellas de RNF-04: `tests/unit/test_huellas_rnf04.py`;
- cuatro hojas: `tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas` y `tests/integration/test_composicion_extremo_a_extremo.py::test_exportar_excel_escribe_las_cuatro_hojas_con_la_modalidad`. La tarea 13 agrega `control` a `exportar_excel` con valor por defecto vacío, de modo que esas dos pruebas no se tocan;
- las cuatro memorias de S1 (`tests/fixtures/memorias/s1_*.md`) sin cambios desde `v0.6.0` (`S2-REG-S1`);
- las ediciones de SF-E2: `tests/integration/test_edicion_versiones.py` y `tests/integration/test_hoja_versiones.py` sin editar (`guardar_edicion` gana un parámetro con valor por defecto).

## Foco de revisión (entradas que ninguna prueba ejercitaba y que más pueden morder a una persona real)

Cada fase tiene el suyo; estas son las cinco globales, cada una con la prueba que la fija en su tarea:
1. **La misma valuación pegada dos veces o con un número repetido:** se rechaza entera y no escribe nada; la corrección es anular y registrar otra → `tests/integration/test_importar_valuaciones.py::test_un_numero_ya_registrado_se_rechaza_entero_y_no_escribe` (Tarea 6).
2. **Un costo real en bolívares sin tasa del BCV de su fecha:** el AC sale «no disponible», se declara y no se usa una tasa vieja en silencio → `tests/integration/test_control.py::test_un_costo_en_bs_sin_tasa_aplicable_deja_el_ac_no_disponible_y_lo_declara` (Tarea 9).
3. **Cambiar la moneda del proyecto con la línea base declarada:** la línea base queda invalidada y no se convierte en silencio → `tests/integration/test_ejecutado_por_periodo.py::test_tras_un_cambio_de_moneda_la_linea_base_invalidada_se_rechaza` (Tarea 6).
4. **Horas extra por encima de la LOTTT o una partida sin jornal:** se rechazan citando el artículo o dan «no aplica» sin dividir → `tests/unit/test_recuperacion.py::test_las_horas_extra_por_dia_sobre_el_limite_se_rechazan` y `::test_una_partida_de_sis_001_sin_mano_de_obra_no_aplica_sin_dividir` (Tarea 10).
5. **Abrir «Control de obra» sobre la base real de Eugenio** (con espacios, acentos y OneDrive): la página abre el caso con `preparar_base`, nunca crea el esquema ni toca `data/apu.db` → `tests/unit/test_ui_pagina_control.py::test_la_pantalla_no_escribe_en_la_base_real` (Tarea 13) y `tests/unit/test_arquitectura_s5.py::test_la_lista_de_paginas_que_abren_el_caso_esta_completa` (Tarea 13).

## Supuestos sobre 0.6.0 (cada firma que S2 consume de A, B y S1)

El plan se escribió contra el código del plan de la 0.6.0 (`PLAN_SILICE_060.md`, secciones A, B y C). Si al ejecutar una firma
no existe tal cual, la tarea que la consume se detiene y se registra el ruling; no se improvisa otra.

**S1 — moneda, tasa, reajuste (sección C), consumidas por el núcleo de S2:**
- `core/budget/moneda.py`:
  - `def moneda_del_proyecto(session: Session, proyecto: models.Proyecto) -> str`
- `core/catalog/moneda.py`:
  - `def exigir_moneda(moneda: str) -> str`
  - `def convertir(monto: Decimal, de: str, a: str, tasa: Decimal) -> Decimal`
- `core/catalog/indices.py`:
  - `LADO_POR_DEFECTO = 'venta'`
  - `class TasaNoDisponible`
  - `class DefinicionSerie [codigo: str; nombre: str; organismo: str; unidad: str; periodicidad: str; base: str]`
  - `class Observacion [fecha: date; valor: Decimal; provisional: bool]`
  - `class ValorFechado [serie: str; fecha: date; valor: Decimal; provisional: bool; importacion_id: int]`
  - `def definicion_tasa(lado: str) -> DefinicionSerie`
  - `def registrar_importacion(session: Session, definicion: DefinicionSerie, observaciones: Sequence[Observacion], *, archivo: str, huella: str, fuente: str, fecha_descarga: date, responsable: str, filas_leidas: int, filas_rechazadas: int, informe: str='', ahora: datetime | None=None) -> models.ImportacionIndice | None`
  - `def tasa_aplicable(session: Session, fecha: date, *, lado: str=LADO_POR_DEFECTO) -> ValorFechado`
- `core/budget/reajuste.py`:
  - `class Mecanismo`
  - `class Estructura`
  - `class EstadoEstudio`
  - `class Componente [componente: str; serie: str; peso: Decimal | None]`
  - `class Clausula [fecha_inicio: date; duracion_meses: int; fecha_referencia_primer_anio: date; periodicidad: str; mecanismo: Mecanismo; estructura: Estructura; componentes: tuple[Componente, ...]; fecha_base_indices: date; r: Decimal; fuente_r: str; fuente: str; responsable: str; mecanismo_pagadero: Mecanismo | None; fuente_pagadero: str; r_en_comprobacion: bool]`
  - `class Ejecutado [codigo: str; cantidad: Decimal; fuente: str]`
  - `class PeriodoDeclarado [desde: date; hasta: date; ejecutado: tuple[Ejecutado, ...]; version_comprobacion: str; excepcion: str]`
  - `class EstudioCargado [id: int; version_id: int; estado: EstadoEstudio; reemplaza_a: int | None; clausula: Clausula; periodos: tuple[PeriodoDeclarado, ...]; resultado: ResultadoEstudio]`
  - `def guardar_estudio(session: Session, version: models.Presupuesto, clausula: Clausula, periodos: Sequence[PeriodoDeclarado], *, fecha_calculo: date, fuente: str, responsable: str, reemplaza_a: int | None=None, lado: str=LADO_POR_DEFECTO, ahora: datetime | None=None) -> models.EstudioReajuste`
  - `def cargar_estudio(session: Session, estudio_id: int) -> EstudioCargado`
- Tablas de S1: `models.EstudioReajuste` (con `estado`, `fecha_calculo`, `reemplaza_a`, `version_id`), `models.PeriodoReajuste` (`id`, `estudio_id`, `orden`; `cita_valuacion.periodo_id` la referencia por clave foránea), `models.EjecutadoPeriodo`, `models.MonedaProyecto`; `cargar_estudio(session, id).resultado.periodos[].{reajustables, excesos, reconocido}` y `.resultado.total_escalatoria`.
- Regla de S1 que S2 respeta: `reajuste._pu_de` rechaza una partida que el contrato no tiene (por eso RP7-8).

**S1 — interfaz (sección C), consumida por la de S2:** `ui.reajuste` y `ui.paginas.reajuste` (tarea 13 de S1: `periodos_desde_filas`, `calcular`, `guardar`, `parciales_por_reemplazar`, `CLAVE_CALCULO`, `CLAVE_EXCEL`, `_texto`, `_fecha`, `_con_datos`, `_clausula`, `_periodos`, `_pintar`, `_guardar`); `ui.texto_seguro.texto_seguro(texto: str) -> str` (tarea 9); `ui.subidas.guardar_subida`; `ui.hoja.HojaInvalida`; `ui.hoja.exportar_excel` y `excel_de_hoja_en_bytes` (la tarea 13 les agrega `control=()`); `ui.entorno.{ALIAS_ANTERIORES, ULTIMA_VERSION_CON_ALIAS, leer_variable}` (A1).

**B — Alembic, `preparar_base` y bases de prueba:**
- `operacion.base_datos.preparar_base(ruta: Path, destino: Destino = Destino.CASO, *, entorno: Mapping[str, str] | None = None) -> ResultadoPreparacion`, `leer_estado(ruta: Path) -> EstadoBase` (con `.revision`), `revision_head(destino: Destino) -> str | None`, `Destino` (`CASO`, `INSTALACION`), `ErrorDeBase`.
- `tests.fixtures.bases_prueba`: `ficha(version: str) -> dict`, `nombres(version: str) -> list[str]`, `copiar_base(version: str, nombre: str, destino: Path) -> Path`, `diferencias_con_ficha(ruta: Path, esperado: dict) -> list[str]`.
- `tests.fixtures.arquitectura`: `RAIZ: Path`, `importaciones(archivo: Path) -> set[str]`.
- `scripts/generar_base_prueba.py::CONSTRUCTORES: dict[str, Callable[[Path], object]]` con `demo.db`, `of001.db`, `ti001.db` y `s1.db`; `main([...])` con `--salida`, `--version`, `--etiqueta` y `--commit`.
- Revisión head de la 0.6.0: `caso_0004_s1_reajuste`; la prueba de deriva `tests/integration/test_migraciones.py` (RNF-20) recorre toda revisión nueva; `PAGINAS_QUE_ABREN_EL_CASO` en `tests/unit/test_arquitectura_s5.py`.
- Bases versionadas: `tests/fixtures/bases/v0_5_0/` y `v0_6_0/` con sus `ficha.json`.

**A — meta única, guardia de red, nombre:**
- `scripts/meta_silice.py`:
  - `FASES: dict[str, tuple[str, ...]] = {'0.6.0': ('T0', 'S5-1', 'S1-0', 'S1-1', 'S1-2', 'S1-3', 'S1`
  - `class ParTDD [prueba: str; implementacion: str; fase: str]`
  - `class CifraDeTiempo [nombre: str; ruta: str; clave: str; orden: str; fase: str]`
  - `class Parte [nombre: str; requisitos: Mapping[str, tuple[str, ...]]; pares_tdd: tuple[ParTDD, ...]; cifras: tuple[CifraDeTiempo, ...]; comprobaciones: tuple[Comprobacion, ...]]`
  - `class Contexto [version: str; fases: tuple[str, ...]; junit: Path | None; partes: tuple[Parte, ...]]`
  - `class Comprobacion [codigo: str; titulo: str; fase: str; evaluar: Callable[[Contexto], tuple[Estado, str]]]`
  - `def fases_hasta(version: str, hasta: str) -> tuple[str, ...]`
  - `def partes() -> tuple[Parte, ...]`
  - `def validar_partes(todas: Sequence[Parte]) -> None`
  - `def requisitos_exigidos(partes_: Sequence[Parte], fases: Sequence[str]) -> tuple[str, ...]`
  - `_git`
  - `_referencia_existe`
  - `_primer_commit`
- `scripts/meta_sf.py`:
  - `def evaluar_s2_memorias(presentes: dict[str, bool], antes_del_codigo: dict[str, bool | None], codigo_existe: bool=True, posteriores: dict[str, bool] | None=None) -> tuple[Estado, str]`
  - `_ordenar_memoria`
- `scripts.medir_rnf11.medir` (el patrón de la medición que solo registra), la guardia de red de `tests/conftest.py` (A3), `scripts/guardia_nucleo.py`, `scripts/verificar_omitidas.py`, `CHANGELOG.md` con `## [Sin publicar]` (B, tarea 7).

## Discrepancias encontradas (spec contra código) en todo el plan

1. **`calendario.py` en SL-E5 o SL-E4.** El spec lo nombra en SL-E5 (§5.2); R14 necesita contar días hábiles y está en SL-E4. *Resuelta (RP7-2):* entra con SL-E4 en S2-1.
2. **Siete tablas, ocho, nueve.** El expediente SL-E4 del spec dice «7 tablas»; el §6.1 lista 8 (con `decision_recuperacion`); el código necesita además `cita_valuacion` (RP7-4). Son 8 en `caso_0005` y 1 en `caso_0006`, 9 en total.
3. **R13 y R14 «importan solo contratos».** Necesitan los tipos de valuación y un contador de días hábiles. *Resuelta (RP7-3, RP7-2):* los tipos viven en `core/verification/valuaciones.py` (así `core/budget` los importa sin ciclo) y `habiles_entre` se inyecta.
4. **Módulos que el spec §5.2 no nombra:** `core/budget/puente.py`, `core/budget/control.py` y `core/budget/decision.py` (RP7-3). `decision.py` existe para que `recuperacion.py` quede pura; `control.py` para que `valor_ganado.py` no toque la base.
5. **Generador y medición de RNF-15 en S2-0.** El spec los sugiere junto a la memoria; necesitan el núcleo de S2-1 y S2-2. *Resuelta (RP7-13):* el generador entra en la tarea 9 y la medición en la 14.
6. **«Importar la lista `PROHIBIDOS_EN_UI`».** Una prueba no importa a otra. *Resuelta (RP7-15):* se copia la tupla y una segunda prueba la ata a la original por su contenido.
7. **Partidas fuera de la línea base hacia S1.** `reajuste._pu_de` de S1 rechaza una partida que el contrato no tiene. *Resuelta (RP7-8):* el puente no las entrega; R13 las marca.
8. **Ramas.** El spec usa `inc/silice-s2-<fase>-…`; el plan sigue el patrón de la 0.6.0, `inc/070-s2-<n>-…` (RP7-16), y agrega `inc/070-s2-4-nucleo` para la corrección de rendimiento, que es de `core/`.
9. **Nombres de pruebas del spec.** `test_identidad_separacion`, `test_pe_proyectado_coincide_con_sf_e3_segun_plan`, `test_pe_proyectado_dos_escenarios` y `test_guardar_edicion_motivo_por_defecto` del expediente SL-E5/SL-E6 tienen otro nombre en el código (ver la discrepancia 1 de S2-2 y `test_guardar_edicion_sin_motivo_sigue_siendo_edicion_y_rechaza_un_motivo_desconocido`); el plan cita los reales.
10. **UC-18 de S1 y su pantalla.** El spec de S2 enmienda UC-18 pero no nombra `ui/reajuste.py` ni su página. *Resuelta (RP7-19):* una casilla opcional y dos funciones; nada de S1 cambia si no se marca.
11. **El alias `ARENIA_*` vence con la 0.7.0 (A1).** El spec de S2 no lo menciona; subir `pyproject.toml` a 0.7.0 hace fallar `test_el_alias_se_retira_despues_de_la_0_6_0`. *Resuelta:* la tarea 15 lo retira (vacía `ALIAS_ANTERIORES`, ajusta cuatro pruebas de A1 y quita la nota de los dos manuales).
12. **RNF-15 «registra, no rompe».** Se respeta (la medición no tumba la CI), pero la causa se ata a una prueba determinista que cuenta sentencias SQL (tarea 14), porque un número de segundos no se puede fijar entre máquinas.
13. **Código de S1 que el plan de la 0.6.0 deja con E501, N817 y B905.** Se reprodujo en el sandbox al extraerlo; S2 no los hereda ni los toca (`ruff check` solo sobre los archivos tocados).
14. **Líneas de `ui/app.py`, `ui/hoja.py`, `ui/paginas/hoja.py`, `tests/conftest.py` y `tests/unit/test_arquitectura_s5.py`** citadas aquí son de `v0.5.0` y la 0.6.0 las mueve: se ubican por contenido.
15. **Recorrido guiado.** El spec de S2 no pide uno; el de moneda y reajuste de S1 queda como está (RP7-14).
