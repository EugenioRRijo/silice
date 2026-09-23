# CLAUDE.md — Constitución del proyecto

Este archivo es la fuente de verdad sobre **qué** se construye y **cómo**. Cualquier sesión de trabajo
(humana o con Claude Code) empieza leyéndolo. Los demás documentos lo enlazan; no lo copian.

---

## 1. Qué es este proyecto

Sistema de generación y auditoría de Análisis de Precios Unitarios (APU) multidominio. Deriva las
cantidades de obra de una fuente trazable (modelo IFC, reglas paramétricas, tablas), las costea con
la estructura venezolana (prestaciones, bono de alimentación, depreciación de equipos, administración
y utilidad), produce presupuesto y curva de inversión, **verifica automáticamente su consistencia** y
contrasta los precios construidos con el mercado mediante aprendizaje automático.

Caso de estudio y línea base: obra civil del drenaje de una clínica (24 m de PVC 4", cuatro tanquillas
de 0,80 × 0,80 × 0,80 m con paredes de 0,10 m, cinco partidas, 1 586,61 USD), cuyo presupuesto manual
fue auditado y presenta **siete inconsistencias** que el sistema debe detectar (y hacer imposibles por
construcción). Detalle en [docs/linea_base.md](docs/linea_base.md).

**Naturaleza de los datos.** Todos los APU y presupuestos del repositorio son **ejercicios académicos
ficticios**. El de la clínica (línea base) y los dos de ARENAZA (telecom) provienen de ejercicios de
clase y no representan valores reales ni obras ejecutadas. `MNT-001` (industrial) y `SIS-001`
(sistemas) son casos construidos para el proyecto. Reproducen el contenido y el formato de la práctica
venezolana: por eso sirven como línea base normativa de las pruebas y como casos **didácticos** en la
tesis. Los listados MaPreX de julio de 2026 y el tabulador CIV son referencias publicadas aportadas por
el usuario. Cuando se suministren APU de casos reales, se incorporarán como evidencia adicional en
`data/` (con fixture propio en `tests/fixtures/`) sin sustituir la línea base, salvo decisión explícita
documentada en `docs/bitacora/`. Este párrafo es la **fuente única** de la naturaleza de los datos; los
demás documentos lo enlazan.

**Hipótesis central.** El núcleo (`core/`) no cambia cuando se agrega un dominio. Se demuestra con
`git diff --stat core/` vacío tras implementar los adaptadores telecom, industrial y sistemas
(Sesión I5) y con la prueba `tests/unit/test_arquitectura.py`, que falla si un adaptador importa algo
de `core` distinto de `core.contracts`.

**Los tres momentos del trabajo** (ver [PLAN_DESARROLLO.md](PLAN_DESARROLLO.md)): las cinco pruebas
del motor en verde (I0.3); la compuerta G1 de extracción IFC (I3.1); el `git diff --stat core/` vacío (I5).

---

## 2. Principios

1. **No te repitas (DRY).** Cada hecho del sistema vive en un solo lugar y los demás lo importan o lo
   enlazan. La tabla de fuentes únicas de verdad está en [docs/metodologia.md](docs/metodologia.md#5-dry).
   En código: constantes de cálculo solo en `core.contracts.apu.ParametrosCosto`; alias de unidades solo
   en `core.contracts.unidades`; la línea base solo en `tests/fixtures/apu_linea_base.py`.
2. **Núcleo cerrado, adaptadores abiertos.** `core/` no conoce a `adapters/`, `ml/`, `ui/` ni `api/`.
   Los adaptadores solo importan `core.contracts`. Si un adaptador "necesita" tocar `core/`, el hallazgo
   se documenta en `docs/bitacora/`, no se parchea (regla de la sección 9).
3. **`Decimal` para todo lo monetario y todo lo dimensional.** Nunca `float` en cantidades, precios,
   factores ni rendimientos. Se redondea a dos decimales únicamente al presentar.
4. **El motor de costos es una función pura.** Sin acceso a base de datos, sin estado. Recibe una
   `ComposicionAPU` y unos `ParametrosCosto`; devuelve un `ResultadoAPU`.
5. **Pruebas antes que implementación en el núcleo.** La línea base verificada existe antes que el
   motor; el motor se escribe para pasarla sin modificarla.
6. **Trazabilidad total.** Toda cantidad tiene `origen_id`, `origen_tipo` y, si viene de una regla,
   la expresión que la produjo. Todo hallazgo de verificación referencia los `origen_id` involucrados.
7. **El informe de auditoría se genera siempre**, sin que el usuario lo pida.

---

## 3. Metodología y convenciones

Se trabaja con un híbrido **Scrum‑Cascada** (detalle completo en [docs/metodologia.md](docs/metodologia.md)):

- **Cascada (macro):** las siete fases del PLAN se ejecutan en orden, cada una con entregables
  documentales normativos (IEEE 830, IEEE 829, ISO/IEC 25010, vistas 4+1) y **compuertas** que no se
  cruzan sin criterio cumplido (sección 8).
- **Scrum (micro):** cada incremento I0…I6 es un sprint; cada sesión del PLAN es un ítem del sprint
  backlog con su *Definition of Done*: criterio de cierre cumplido, pruebas verdes, commit convencional
  y, para adaptadores, `git diff --stat core/` vacío. La bitácora de cada sprint va en `docs/bitacora/`.

Convenciones operativas:

| Convención | Regla |
|---|---|
| Ramas | `main` para Fase 0 y esqueleto; desde I0.3 una rama por incremento: `inc/I1-actualizacion-precios` |
| Commits | Conventional Commits en español sin tildes en el asunto: `feat(core): …`, `test(core): …`, `docs(ers): …` |
| Sesiones | Una sesión por incremento, `/clear` entre ellas; modo plan antes de cambios grandes |
| Entorno | `uv sync` · `uv run pytest` · `uv run ruff check .` |
| Idioma | Código, docstrings, docs y commits en español; identificadores sin tildes |
| Worktrees | Uno por sprint en `.claude/worktrees/<nombre-corto>`; se borra al fusionar. Solo coexisten el checkout principal y el worktree del sprint vigente: varios worktrees vivos a la vez es lo que dejó `main` dos semanas desactualizado |
| Fusión | Un PR por incremento **contra `main`**, fusionado en cuanto la CI esté verde. No acumular pilas: `gh pr merge` fusiona en la base *actual* del PR, así que una pila hay que reorientarla con `gh pr edit <n> --base main` antes de fusionar, o se fusiona cada PR dentro de su padre y `main` no recibe nada |
| Etiquetas | Una por compuerta cruzada (`g0-docs`, `g1-ifc`, `g2-datos`…) y una **base por sprint** (`i6-base`, `m-base`, `a-base`, `r-base`, `p-base`) que sirve de referencia a `git diff <base> --stat -- core/` |
| Metas | `scripts/meta_<sprint>.py` audita las metas del sprint; una fase se cruza con `--hasta <fase>` en OK **y** la compuerta anotada en `docs/bitacora/` |

---

## 4. Especificación del cálculo y línea base

Todo APU se calcula así (`Decimal`, sin redondeos intermedios):

```
materiales         = Σ cantidad × precio                         ← NO se divide entre rendimiento
equipos            = Σ (cantidad × precio × depreciacion) / rendimiento
mano_obra          = ( Σ cantidad × sueldo × (1 + FCAS)  +  bono × Σ cantidad ) / rendimiento
costo_directo      = materiales + equipos + mano_obra
con_administracion = costo_directo × (1 + administracion)
precio_unitario    = con_administracion × (1 + utilidad)          ← en cascada, NO (1 + 0,15 + 0,10)
```

Parámetros de la línea base (`core.contracts.apu.ParametrosCosto`, valores por defecto):
FCAS = 6,00 (prestaciones 600 %) · bono de alimentación = 1,00 USD por obrero y día ·
administración = 0,15 · utilidad = 0,10. El rendimiento se expresa en unidades de partida por día.

Los dos errores más probables al implementar el motor, y que las pruebas vigilan explícitamente:
dividir los materiales entre el rendimiento; sumar administración y utilidad en vez de encadenarlas.

### Cinco APU de la línea base, verificados (USD, 28/04/2026)

| Partida | Unidad | Rend. | Materiales | Equipos Σ | MO Σsueldo / obreros | Costo directo | **PU** |
|---|---|---|---|---|---|---|---|
| Excavación | m3 | 80 | 0,00 | 402,40 | 19,50 / 5 | 6,79875 | **8,60** |
| Tubería PVC 4" | pieza | 100 | 7,19 | 3,30 | 11,50 / 3 | 8,058 | **10,19** |
| Encofrado de madera | m2 | 16 | 15,60 | 65,30 | 14,50 / 4 | 26,275 | **33,24** |
| Vaciado de concreto | m3 | 8 | 156,40 | 133,78 | 20,50 / 6 | 191,81 | **242,64** |
| Relleno compactado | m3 | 8 | 14,00 | 71,00 | 20,50 / 6 | 41,5625 | **52,58** |

El desglose línea por línea (cada material, equipo y obrero) está **una sola vez** en
`tests/fixtures/apu_linea_base.py`; la evidencia primaria es `data/linea_base/APUS_CLINICA.pdf`.
Tolerancia de las pruebas: ± 0,01 sobre el precio unitario.

---

## 5. Contratos de interfaz (`core/contracts/`)

Son los únicos tipos que cruzan fronteras entre paquetes. **Son estables**: no cambian en el resto del
proyecto. Si una sesión cree necesitar cambiarlos, se detiene y documenta el hallazgo.

| Módulo | Tipos | Papel |
|---|---|---|
| `unidades.py` | `normalizar_unidad()`, `unidades_equivalentes()` | Única tabla de alias (m³ ≡ m3, mts ≡ m, pza ≡ pieza). "pieza" y "m" siguen siendo distintas: la regla R3 depende de ello |
| `dominio.py` | `Dominio` (civil, telecom, industrial, sistemas) | Enumeración de dominios |
| `item_computo.py` | `OrigenTipo`, `ItemComputo` | Una cantidad de obra trazable: `codigo_partida`, `descripcion`, `unidad`, `cantidad`, `origen_id`, `origen_tipo`, `dominio`, `regla`, `parametros`, `especificaciones` |
| `adaptador.py` | `AdaptadorDominio` (ABC) | `dominio: ClassVar[Dominio]` y `extraer(fuente) -> list[ItemComputo]` |
| `apu.py` | `LineaMaterial`, `LineaEquipo`, `LineaManoObra`, `ComposicionAPU`, `ParametrosCosto`, `ResultadoAPU`, `TipoRendimiento`, `Rendimiento` | Entrada y salida del motor; rendimiento estimado vs medido |
| `presupuesto.py` | `PartidaPresupuestada`, `PuntoCurva`, `Presupuesto` | Forma en memoria del presupuesto y su curva; la entrada de toda regla de verificación |
| `verificacion.py` | `Severidad`, `Hallazgo`, `ReglaVerificacion` (ABC) | Contrato de las reglas: `evaluar(presupuesto) -> list[Hallazgo]` |

Reglas de los contratos: dataclasses inmutables (`frozen=True`); validan sus invariantes en
`__post_init__` (cantidades ≥ 0, rendimiento > 0, 0 < depreciación ≤ 1, unidades normalizadas);
`Decimal` en todo número; sin dependencias fuera de la biblioteca estándar.

Escribir un adaptador nuevo consiste en: crear `adapters/<dominio>/`, subclasificar `AdaptadorDominio`,
declarar `dominio`, implementar `extraer()` devolviendo `ItemComputo` con `origen_id` real, y no
importar nada de `core` salvo `core.contracts`. Guía ampliada en el manual técnico (Sesión F.3).

---

## 6. Estructura de carpetas

```
CLAUDE.md  PLAN_DESARROLLO.md  README.md  pyproject.toml
core/
  contracts/      estables (sección 5)                                   — I0.1 ✔
  costing/        motor: calcular_apu(composicion, parametros) -> ResultadoAPU — I0.3
  models/         SQLAlchemy según docs/modelo_datos.md                   — I0.4
  catalog/        consulta y carga de partidas, insumos, rendimientos     — I0.4
  budget/         presupuesto, curva de inversión, exportación Excel      — I0.5, I1
  verification/   las siete reglas (sección 7) y el informe de auditoría  — I4
adapters/
  civil/          IFC con ifcopenshell + reglas paramétricas trazables    — I3.1, I3.2
  telecom/        topología de red en CSV (nodos, enlaces, longitudes)     — I5
  industrial/     registro de activos con frecuencia de intervención      — I5
  sistemas/       alcance funcional (módulos, casos de uso, puntos de función) — I5
ml/
  normalization/  sentence-transformers, similitud del coseno             — I2
  anomaly/        Isolation Forest sobre precios y rendimientos           — I6.1
  prediction/     XGBoost / CBR / reglas según compuerta G2               — I6.3
ui/               Streamlit                                                — I1, F.1
api/              FastAPI, esquema OpenAPI exportado a docs/api.json       — F.1
scripts/          seed.py (carga la línea base en SQLite)                  — I0.4
data/
  linea_base/     APUS_CLINICA.pdf (evidencia primaria)
  samples/        tanquilla.ifc (antes de I3.1), telecom/*.pdf (muestras para I5)
tests/
  fixtures/       apu_linea_base.py — única copia de la línea base
  unit/           contratos, arquitectura, línea base, costing (rojo hasta I0.3)
  integration/    persistencia y flujos completos                          — I0.4+
docs/             metodologia, ERS, modelo_datos, arquitectura, linea_base, tesis/, bitacora/, fuentes/
```

---

## 7. Siete reglas de verificación (`core/verification/`, Sesión I4)

Cada regla es una clase `ReglaVerificacion` con `evaluar(presupuesto) -> list[Hallazgo]`; cada
hallazgo lleva severidad, descripción, cuantificación del impacto y los `origen_id` involucrados.

| Código | Regla | Qué comprueba | Hallazgo de la línea base que detecta |
|---|---|---|---|
| R1 | `TrazabilidadGeometrica` | Toda cantidad deriva de una regla declarada y coincide con su evaluación | 1 encofrado (5,92 vs 4,48 m2/tanquilla) · 2 concreto (0,415 vs 0,224 m3/tanquilla) |
| R2 | `CierreCurvaInversion` | El acumulado de la curva es exactamente el total del presupuesto | 3 curva cierra en 1 575,50 (99,30 %) vs 1 586,61 |
| R3 | `CoherenciaDimensional` | La unidad del cómputo equivale a la unidad del APU (vía `unidades_equivalentes`) | 4 tubería en "mts" vs APU en "Pieza" |
| R4 | `CorrespondenciaEspecificaciones` | Diámetros, materiales y espesores del cómputo coinciden con el modelo y el APU | 5 memoria dice 3/4" y el sistema es de 4" |
| R5 | `BalanceVolumetrico` | relleno = excavación − concreto − tubería (± tolerancia declarada) | 6 se excavan 9,74 m3 y se rellenan 1,30 m3 |
| R6 | `CriterioDepreciacion` | Un mismo insumo lleva el mismo factor en todos los APU y el criterio está declarado | 7 vehículo de transporte con 1,00 en cuatro APU y 0,03 en tubería |
| R7 | `ConciliacionPresupuestoPlan` | Cada monto del plan de trabajo coincide con el monto de su partida | raíz del hallazgo 3: día 1 = 82,98 vs partida = 83,77, etc. |

R7 es decisión de diseño de este proyecto (las Bases del anteproyecto listan cinco reglas); se valida
con el tutor en la Sesión I4. Prueba de aceptación crítica: un presupuesto de prueba que reproduzca
las siete inconsistencias y el sistema detecte **7 de 7** (indicador 1 de la tesis).

---

## 8. Compuertas y criterios de degradación

**8.1 Datos para el módulo predictivo (compuerta G2, antes de I6.3).** Contar los registros de APU
disponibles por dominio y aplicar:

| Registros por dominio | Técnica en `ml/prediction/` |
|---|---|
| > 200 | XGBoost, con bosques aleatorios como contraste |
| 50 – 200 | Razonamiento basado en casos con validación dejando uno fuera |
| < 50 | Sistema de reglas con análisis de sensibilidad, declarado como limitación |

Métricas obligatorias: MAPE, RMSE, R². Marco de contraste: clase 3 de AACE International.

**8.2 Extracción IFC (compuerta G1, Sesión I3.1).** Si las cantidades extraídas de
`data/samples/tanquilla.ifc` no coinciden con el cálculo manual, el adaptador civil se sustituye por
entrada tabular y se documenta la pérdida de independencia tecnológica. El resto del sistema no cambia.

**8.3 Documentación de Fase 0 (compuerta G0).** ERS, modelo de datos y arquitectura aprobados por el
tutor antes de I0.3. Los esqueletos ya existen; se completan en las Sesiones 0.1 – 0.3.

---

## 9. Cómo trabajar con Claude Code en este repositorio

- Leer este archivo y la sesión correspondiente de [PLAN_DESARROLLO.md](PLAN_DESARROLLO.md) antes de
  escribir código. Usar modo plan para cambios grandes.
- **Regla que evita el 80 % de los problemas:** si al trabajar en un adaptador o en `ml/` parece
  necesario modificar algo dentro de `core/`, **detenerse**. O el adaptador está mal diseñado, o el
  contrato es insuficiente. Ambas cosas son hallazgos de la investigación: se escriben en
  `docs/bitacora/`, no se parchean.
- No modificar `tests/unit/test_costing.py` para ponerlo en verde: se implementa `core/costing/`.
- Estado esperado de la suite hasta I0.3: todo verde salvo `test_costing.py`, que falla con
  `ImportError` (siete pruebas). Es correcto y deliberado.
- Al cerrar una sesión: verificar el criterio de cierre, ejecutar `uv run pytest` y
  `uv run ruff check .`, hacer el commit indicado en el PLAN y anotar la bitácora del sprint.
