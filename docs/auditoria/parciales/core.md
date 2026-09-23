# Auditoría parcial — capa `core`

Commit auditado: `cc2243cd5a7efd3b20dc82fe586484a6ef01fea8`. `git diff --stat cc2243cd HEAD -- core/` está
vacío, así que los números de línea valen igual sobre el HEAD del worktree. Criterios: spec
`docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md` §4. Las decisiones D1–D9 de
`docs/dossier_g0.md` se toman como riesgo ya rastreado y no se reportan.

## 1. Archivos revisados (35 de 35 de `git ls-files core/`)

```
core/__init__.py
core/budget/__init__.py
core/budget/actualizacion.py
core/budget/curva.py
core/budget/escenarios.py
core/budget/excel.py
core/budget/persistencia.py
core/budget/presupuesto.py
core/catalog/__init__.py
core/catalog/errores.py
core/catalog/mapeo.py
core/catalog/precios.py
core/catalog/rendimientos.py
core/catalog/repositorio.py
core/catalog/sesion.py
core/contracts/__init__.py
core/contracts/adaptador.py
core/contracts/apu.py
core/contracts/dominio.py
core/contracts/item_computo.py
core/contracts/presupuesto.py
core/contracts/unidades.py
core/contracts/verificacion.py
core/costing/__init__.py
core/costing/motor.py
core/models/__init__.py
core/models/base.py
core/models/entidades.py
core/models/tipos.py
core/verification/__init__.py
core/verification/directivas.py
core/verification/expresiones.py
core/verification/informe.py
core/verification/reglas.py
core/verification/texto.py
```

## 2. Hallazgos

| ID provisional | capa | principio | severidad | evidencia archivo:línea | hallazgo | corrección propuesta | fase destino |
|---|---|---|---|---|---|---|---|
| core-01 | core | Invariantes de los contratos (§5) | importante | `core/contracts/apu.py:193`; `core/contracts/item_computo.py:54` (sin coerción en `:39-40`) | `Rendimiento` e `ItemComputo` comparan el enum con `is` sin convertir antes la entrada. Si reciben la cadena en vez del miembro del enum, se saltan sus invariantes: `Rendimiento('X', D('1'), 'medido', hoy)` se acepta sin `referencia_ejecucion`, y `ItemComputo(..., 'regla', 'civil')` se acepta sin `regla` (comprobado ejecutándolo). `LineaManoObra` sí convierte (`apu.py:99`). Ningún llamador de `adapters/`, `ml/`, `api/`, `ui/` ni `scripts/` pasa cadenas (grep) | En `__post_init__`, convertir con `TipoRendimiento(self.tipo)`, `OrigenTipo(self.origen_tipo)` y `Dominio(self.dominio)`, como hace `LineaManoObra` | C1. Cambia un contrato: necesita expediente en `docs/bitacora/` y aval del tutor |
| core-02 | core | Decimal en todo número (principio 3) / contratos §5 | importante | `core/contracts/item_computo.py:42,57` (no valida `parametros`); `core/contracts/apu.py:161-170` (`ResultadoAPU` sin `__post_init__`); `core/contracts/presupuesto.py:33-39` (`PuntoCurva` sin `__post_init__`); `core/contracts/verificacion.py:28-38` (`impacto` y `valor_*` sin validar) | Varios campos numéricos de los contratos no exigen `Decimal` y no tienen invariante de signo. Se comprobó que se aceptan `PuntoCurva('d', 1.5, -2.0)`, `Hallazgo(..., impacto=0.1)` e `ItemComputo(parametros={'a': 1.0})`. El problema es la validación que falta; no se detectó ningún uso real de `float` | Añadir `_exigir_decimal` o `_no_negativo` (`apu.py:13-23`) a esos campos: a cada valor de `parametros`, a los seis montos de `ResultadoAPU`, a `monto` y `acumulado` de `PuntoCurva`, y a los tres campos opcionales de `Hallazgo` | C1. Cambia contratos: expediente y aval del tutor |
| core-03 | core | El informe siempre se genera (principio 7) | importante | `core/verification/expresiones.py:125-138` (solo captura `ArithmeticError`); `core/verification/reglas.py:137` (solo captura `ExpresionInvalida` y `ParametroFaltante`); lo que prometen: `reglas.py:4-5` | Un valor que no es `Decimal` en `ItemComputo.parametros` lanza `TypeError` dentro de R1. Ese error sale de `auditar` y `elaborar` aborta sin presupuesto ni informe (comprobado: `TypeError: unsupported operand type(s) for *: 'float' and 'decimal.Decimal'`). Contradice el principio de que «ninguna [regla] lanza excepciones por datos» | Convertir `TypeError` en `ExpresionInvalida` en `_evaluar_binario` y `_evaluar_nodo`, para que R1 y R5 lo registren como hallazgo. Complementa a core-02 | C1 |
| core-04 | core | El informe siempre se genera (principio 7) | menor | `core/budget/presupuesto.py:39-64`; `core/budget/__init__.py:12-13,56` | `generar_presupuesto` es pública y devuelve un `Presupuesto` sin informe. Eso contradice «no existe forma de obtener el presupuesto sin su informe». Quienes la llaman la usan de borrador para armar el plan y después recalculan con `elaborar` (p. ej. `api/rutas/presupuestos.py:85-96`, `ui/paginas/elaborar.py:227`, `scripts/seed_industrial.py:201`). Cruza: api, ui, scripts | Que `elaborar` acepte un generador de plan (`Callable[[Presupuesto], plan]`, o una opción «secuencial»), para no exigir el borrador. Después, volver privada `generar_presupuesto` o documentarla como paso intermedio sin valor de entrega | C1 (los llamadores de api/ui/scripts, en commits separados) |
| core-05 | core | DRY | importante | `core/catalog/precios.py:115-118` frente a `core/budget/actualizacion.py:306-308` | La fórmula de variación de `docs/modelo_datos.md` §6 está escrita dos veces y se comporta distinto cuando el precio anterior es 0: una devuelve 0 y la otra lanza `DivisionByZero` (comprobado). El precio 0 es válido en la entrada (`precios.py:246`), así que `registrar_cambios` puede hacer fallar UC‑02 | Dejar una sola función de variación, con una política declarada para la base nula, e importarla desde los dos módulos | C1 |
| core-06 | core | DRY | importante | `core/catalog/rendimientos.py:100-146` frente a `core/catalog/repositorio.py:241-258`; `rendimientos.py:136-143` frente a `core/catalog/mapeo.py:231-244` | El registro de un rendimiento está implementado dos veces. Las dos versiones difieren en el error (`LookupError` frente a `CatalogoIncompleto`) y en lo que devuelven (contrato frente a modelo). Además, `rendimientos.py` construye `models.Rendimiento` a mano, fuera de `mapeo.py`, aunque `mapeo.py:3-9` y `models/entidades.py:6-8` declaran que la frontera modelo↔contrato vive solo en dos módulos (ADR 12) | Que `rendimientos.registrar_rendimiento` construya el contrato y delegue en `Catalogo.registrar_rendimiento` y `a_rendimiento`. Unificar la excepción | C1 |
| core-07 | core | DRY | importante | `core/verification/expresiones.py:6-8,52-159`. Cruza: adapters (`adapters/civil/evaluador.py`, `adapters/industrial/evaluador.py`, `adapters/sistemas/evaluador.py`, `adapters/telecom/evaluador.py`) | El evaluador de expresiones trazables existe en cinco copias. El núcleo reconoce la duplicación y la registró en la bitácora de I4 | En C1, subir un único evaluador a donde los adaptadores puedan importarlo (`core.contracts`). Eso es un cambio de contrato: expediente y aval, o «aceptado por decisión de arquitectura registrada». En C2, migrar los cuatro adaptadores | C1 (contrato) + C2 (adaptadores) |
| core-08 | core | DRY | menor | `core/budget/excel.py:35,53-54` frente a `core/verification/texto.py:83-85` (`texto.py:9-10` afirma que hay «una sola copia») | El redondeo de presentación (`quantize` con `ROUND_HALF_UP` a `DECIMALES_PRESENTACION`) está escrito dos veces dentro del núcleo | Exponer en `core/verification/texto.py` un `redondear(valor, decimales)` que devuelva `Decimal`; que `formatear_decimal` y `excel._redondear` lo usen | C1 |
| core-09 | core | S (responsabilidad única) | menor | `core/catalog/precios.py:3-20` (el docstring enumera «Tres responsabilidades»); `:41-44` (importa `openpyxl`, `pandas` y `sqlalchemy`) | Un solo módulo lee y analiza archivos CSV y XLSX, persiste la lista nueva y detecta y registra el historial de cambios. Son tres razones de cambio con nombre | Separar la lectura de archivos (p. ej. `core/catalog/lector_precios.py`) de la persistencia de la lista y del historial | C1 |
| core-10 | core | D (inversión de dependencias, estricta) | menor | `core/budget/actualizacion.py:25,87,275`; `core/budget/escenarios.py:30,108-128` | La API pública de `core.budget` devuelve `pandas.DataFrame` (`Comparativo.tabla`, `comparar_escenarios`), así que el núcleo depende de una implementación concreta de presentación tabular. No impide las pruebas | Devolver tuplas de dataclasses con celdas `Decimal` y construir el `DataFrame` en `ui/` o `api/` | C1 (los llamadores de ui/api, en commits separados) |

## 3. Principios sin hallazgos

- **Motor puro (principio 4): sin hallazgos.** `core/costing/motor.py:26-70` no tiene E/S ni estado, y solo importa `core.contracts.apu`. Aplica los materiales sin dividir entre el rendimiento y la administración y la utilidad en cascada.
- **`float` en los cálculos (principio 3, uso efectivo): sin hallazgos.** El grep de `float` en `core/` solo aparece en docstrings y en el filtro de constantes de `expresiones.py:150`, que convierte a partir del texto fuente. `DecimalExacto` (`models/tipos.py:14-38`) persiste como texto. Observación sin hallazgo: `precios.py:195-201` hace `str()` de la celda numérica que `openpyxl` entrega como `float`. Es una frontera de formato inevitable y está documentada en `precios.py:164-177`. Lo que falta en los contratos está en core-02.
- **Contratos inmutables (`frozen=True`): sin hallazgos.** Todas las dataclasses de `core/contracts/` son `frozen=True, slots=True`, y los `Mapping` se congelan con `MappingProxyType` (`item_computo.py:57-58`).
- **O, abierto/cerrado para dominios: sin hallazgos.** No hay ramas por dominio en `core/`: el grep de `Dominio.CIVIL|TELECOM|INDUSTRIAL|SISTEMAS` y de sus literales solo encuentra la definición de la enumeración (`contracts/dominio.py:7-10`). Una regla nueva solo exige añadirla a `REGLAS` (`reglas.py:689-697`), sin tocar las demás ni el motor.
- **L, sustitución: sin hallazgos.** Las siete subclases de `ReglaVerificacion` declaran `codigo` y `nombre`, devuelven `list[Hallazgo]`, no modifican el presupuesto y referencian `origen_id` o códigos de partida (`reglas.py`).
- **I, segregación de interfaces: sin hallazgos.** `AdaptadorDominio` y `ReglaVerificacion` exponen un único método abstracto cada uno.
- **D, regla de dependencia entre capas: sin hallazgos.** Ningún módulo de `core/` importa de `adapters`, `ml`, `ui`, `api` ni `scripts` (grep `^(from|import) (adapters|ml|ui|api|scripts)`). Lo que hay de inversión estricta está en core-10.
- **DRY frente a las fuentes únicas de `docs/metodologia.md` §5.1: sin hallazgos adicionales.** Los parámetros de costo solo están en `ParametrosCosto` (`apu.py:151-154`), los alias de unidades solo en `contracts/unidades.py`, y la fórmula del PU solo en `costing/motor.py`. No hay constantes de negocio repetidas en el núcleo.
