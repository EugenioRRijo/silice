# Auditoría parcial — capa adaptadores / ml / api

**Encargo:** Tarea de C0 (`docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md` §4).
**Commit auditado:** `cc2243cd5a7efd3b20dc82fe586484a6ef01fea8` (HEAD del worktree, `3b7645e`, solo difiere en
`docs/auditoria/2026-09-inventario.md`; el árbol de `adapters/`, `ml/` y `api/` es idéntico).
**Alcance:** todos los archivos de `git ls-files adapters/ ml/ api/` (32 de 32).
**Riesgo ya rastreado, no reportado aquí:** decisiones D1–D9 y salvedades de `docs/dossier_g0.md` §3–§4.

## 1. Archivos revisados (32/32)

adapters/__init__.py
adapters/civil/__init__.py
adapters/civil/evaluador.py
adapters/civil/ifc.py
adapters/civil/reglas.py
adapters/civil/tabular.py
adapters/industrial/__init__.py
adapters/industrial/adaptador.py
adapters/industrial/evaluador.py
adapters/sistemas/__init__.py
adapters/sistemas/adaptador.py
adapters/sistemas/evaluador.py
adapters/telecom/__init__.py
adapters/telecom/adaptador.py
adapters/telecom/evaluador.py
api/__init__.py
api/dependencias.py
api/esquemas.py
api/main.py
api/rutas/__init__.py
api/rutas/catalogo.py
api/rutas/computos.py
api/rutas/listas.py
api/rutas/presupuestos.py
api/rutas/rendimientos.py
ml/__init__.py
ml/anomaly/__init__.py
ml/anomaly/detector.py
ml/normalization/__init__.py
ml/normalization/normalizador.py
ml/prediction/__init__.py
ml/prediction/reglas.py

## 2. Hallazgos

| ID | Capa | Principio | Severidad | Evidencia | Hallazgo | Corrección propuesta | Fase destino |
|---|---|---|---|---|---|---|---|
| adaptadores-ml-api-01 | adapters (cruza: core) | DRY | Importante | `core/verification/expresiones.py:1-159`; `adapters/civil/evaluador.py:1-75`; `adapters/industrial/evaluador.py:1-80`; `adapters/sistemas/evaluador.py:1-61`; `adapters/telecom/evaluador.py:1-67`. `diff adapters/civil/evaluador.py adapters/industrial/evaluador.py` solo difiere en el docstring (líneas 1-13): el cuerpo ejecutable (líneas 17-75 de civil, 18-80 de industrial) es idéntico carácter por carácter. | El evaluador seguro de expresiones aritméticas trazables está reimplementado de forma independiente en cinco módulos (core y los cuatro adaptadores); civil e industrial son código clonado línea por línea, no solo "el mismo subconjunto aritmético". | Extraer un evaluador mínimo y parametrizable (conjunto de operadores permitidos como argumento) a `core/contracts` — el único paquete de `core` que los adaptadores pueden importar — y migrar los cuatro adaptadores y `core/verification/expresiones.py` a usarlo, preservando los subconjuntos reducidos que `sistemas` (sin resta/potencia/unario) y `telecom` (sin potencia/unario) restringen a propósito. | C1 (contrato compartido en `core.contracts`) → C2 (migración de los 4 adaptadores y de `core/verification`) |
| adaptadores-ml-api-02 | ml (cruza: core) | DRY | Menor | `ml/prediction/reglas.py:186-193` (`_a_dos_decimales`, `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`) vs. `core/verification/texto.py:76-89` (`formatear_decimal`, misma cuantización con `ROUND_HALF_UP`). El propio docstring de `_a_dos_decimales` (líneas 187-191) declara que "replica" a `formatear_decimal`. | `ml/prediction/reglas.py` reescribe a mano el redondeo de presentación a dos decimales que ya existe en `core.verification.texto.formatear_decimal`, porque `ml/` solo puede importar `core.contracts` y esa utilidad no vive ahí. | Mover `formatear_decimal` (o una versión mínima de presentación) a `core/contracts` como utilidad compartida, para que `ml/` y `core/verification` importen la misma implementación en vez de mantener dos. | C1 (si se traslada la utilidad a `core.contracts`) → C2 (ajustar `ml/prediction/reglas.py`) |
| adaptadores-ml-api-03 | adapters | DRY | Menor | `adapters/civil/tabular.py:30-43`; `adapters/industrial/adaptador.py:23-36`; `adapters/sistemas/adaptador.py:43-57`; `adapters/telecom/adaptador.py:25-38`. Las cuatro funciones `_parsear_especificaciones` tienen firma, docstring y cuerpo equivalentes (`"clave=valor;clave=valor" -> dict`). | `_parsear_especificaciones` está duplicada, idéntica en sustancia, en los cuatro adaptadores tabulares; a diferencia del evaluador, ninguna regla de `tests/unit/test_arquitectura.py` impide que un adaptador importe una función auxiliar de otro adaptador, así que la duplicación no tiene la misma justificación arquitectónica. | Extraer la función a un módulo compartido dentro de `adapters/` (p. ej. `adapters/_texto.py`) que los cuatro adaptadores importen; no exige tocar `core/`. | C2 (adapters) |

## 3. Sin hallazgos, por principio

- **`Decimal` en todo lo monetario y dimensional, nunca `float` (bloqueante).** No se encontró `float(` en `adapters/` ni en `api/`. En `ml/` los únicos `float` son puntajes adimensionales (similitud del coseno en `ml/normalization/normalizador.py`, `decision_function` de Isolation Forest en `ml/anomaly/detector.py`) — declarados en sus docstrings como fuera del alcance de la regla 3 de CLAUDE.md por no ser monto ni cantidad de obra — y la conversión a `float` dentro de `ml/prediction/reglas.py` no existe (usa `Decimal.sqrt()` para RMSE). Sin hallazgos.
- **El motor de costos es una función pura.** `api/rutas/presupuestos.py` no reimplementa la fórmula del PU: delega en `core.budget.elaborar`/`generar_presupuesto`/`generar_escenario` y solo pasa `ParametrosCosto`. Sin hallazgos.
- **El informe de auditoría se genera siempre.** `api/rutas/presupuestos.py::crear_presupuesto` audita siempre antes de guardar (UC-05); `/presupuestos/{codigo}/informe` reutiliza `InformeAuditoria.a_markdown()` sin reinventarlo. Sin hallazgos.
- **Contratos de `core/contracts/` inmutables, invariantes en `__post_init__`.** No aplica directamente a esta capa (los contratos viven en `core/contracts/`), pero los adaptadores auditados no eluden esas invariantes: todo `ItemComputo` construido en `adapters/` pasa por `__post_init__` (valida `origen_id`, `cantidad: Decimal >= 0`, normaliza unidad). Sin hallazgos.
- **S — responsabilidad única.** Ningún archivo de `adapters/`, `ml/` o `api/` mezcla Streamlit con `sqlalchemy.orm` o con `core.costing`; `api/dependencias.py` combina `sqlalchemy.orm` con `core.catalog` porque esa es su única razón de cambio declarada (sesión de base de datos por petición). Sin hallazgos.
- **O — abierto/cerrado para dominios.** Los cuatro adaptadores de dominio se agregan sin modificar `core/` (verificado por `tests/unit/test_arquitectura.py`, fuera del alcance de esta auditoría de código pero consistente con lo leído). Sin hallazgos nuevos.
- **L — sustitución (`AdaptadorDominio`).** Las cuatro subclases (`AdaptadorCivilIFC`, `AdaptadorCivilTabular`, `AdaptadorIndustrial`, `AdaptadorSistemas`, `AdaptadorTelecom`) declaran `dominio: ClassVar[Dominio]`, implementan `extraer(fuente) -> list[ItemComputo]` y usan `origen_id` real y trazable (`GlobalId` IFC, `id` de fila CSV, o concatenación declarada de ids en el balance de relleno). Sin hallazgos.
- **I — segregación de interfaces.** `AdaptadorDominio` y `ReglaVerificacion` (esta última no vive en esta capa) no obligan a los adaptadores a depender de métodos que no usan. Sin hallazgos.
- **D — regla de dependencia entre capas.** Ningún archivo de `adapters/` o `ml/` importa de `core` algo distinto de `core.contracts` (verificado línea por línea con `grep` sobre los 22 archivos de ambos paquetes). `api/` importa libremente de `core` (permitido: la restricción de CLAUDE.md §5 es solo para adaptadores) y de `adapters/*` de forma perezosa (import dentro de función) en `api/rutas/computos.py` y `api/rutas/rendimientos.py`. Sin hallazgos.
- **`ml/` no usa datos del corpus simulado.** Los tres submódulos (`anomaly`, `normalization`, `prediction`) son funciones puras que reciben series, mapeos o catálogos como parámetros; ninguno abre un archivo de `data/`, importa un fixture de `tests/` ni referencia la línea base o ARENAZA por nombre. Sin hallazgos.
- **`api/` no duplica lógica que vive en `core`.** Las rutas delegan en `core.catalog`, `core.budget` y `core.verification`; `_buscar_modelo` (`api/rutas/presupuestos.py:348-379`) no reimplementa `core.budget.persistencia._buscar` (que exige `proyecto_nombre` obligatorio) sino que añade una conveniencia HTTP genuina (proyecto opcional, con 409 explícito si el código es ambiguo entre proyectos) que no existe en `core`. Sin hallazgos.
- **Coherencia documental.** Los docstrings revisados citan RF/UC/CLAUDE.md de forma consistente con el código que describen (incluida la autodeclaración de las duplicaciones DRY reportadas arriba). Sin hallazgos adicionales.
- **Trazabilidad (paso de caso de uso o RF sin prueba).** Dentro del conjunto de archivos auditado (sin cruzar a `tests/`), cada regla paramétrica y cada `ItemComputo` declara `origen_id`/`regla`/`parametros` según CLAUDE.md §5. Sin hallazgos.
- **Pruebas (aserciones vacías, aislamiento roto, orden o red).** No aplica: `git ls-files adapters/ ml/ api/` no incluye archivos de prueba. Sin hallazgos.
