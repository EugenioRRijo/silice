# Manual técnico — Sesión F.3

Guía para quien vaya a mantener o extender el sistema. El aporte central del trabajo es la
**extensibilidad sin tocar el núcleo**, así que el corazón de este manual es la sección 4: cómo
un tercero escribe un adaptador de dominio nuevo. La constitución del proyecto es
[NORMAS.md](../NORMAS.md); la arquitectura completa (vistas 4+1), [arquitectura.md](arquitectura.md);
el modelo de datos, [modelo_datos.md](modelo_datos.md). Este manual no los repite: los recorre.

## 1. La regla que gobierna todo

`core/` no conoce a `adapters/`, `ml/`, `ui/` ni `api/`. Los adaptadores importan de `core`
**únicamente `core.contracts`**. La regla no es una convención de estilo: es la hipótesis central
de la tesis, y está vigilada por dos guardias automáticas:

- `tests/unit/test_arquitectura.py` — parametrizada sobre los módulos existentes (un módulo nuevo
  genera su caso solo), falla si un adaptador importa otra cosa de `core`;
- `git diff --stat core/` vacío al cerrar cualquier sesión de adaptadores (indicador 4).

Si al trabajar en un adaptador o en `ml/` parece necesario modificar algo de `core/`:
**detenerse**. O el adaptador está mal planteado o el contrato es insuficiente; ambas cosas se
documentan en `docs/bitacora/`, no se parchean (NORMAS.md §9).

## 2. Entorno de desarrollo

```
uv sync --extra ui --extra api --extra civil --extra planos --extra ml   # todo
uv run pytest -W error                                    # la suite (advertencia = error)
uv run ruff check .                                       # estilo (E, F, W, I, B, UP, N)
```

**Integración continua.** `.github/workflows/ci.yml` repite en GitHub, en cada PR y en cada push a
`main`, lo que se verifica en local: el job `calidad` en Linux y el job `pruebas` en Linux y
Windows. Cada paso se reproduce así:

| Paso de CI | Comando local |
|---|---|
| Ruff | `uv run ruff check .` |
| Guardia del núcleo | `uv run python scripts/guardia_nucleo.py --base <rama base>` (0 cumple, 1 viola, 2 base inválida) |
| Suite sin omitidas | `uv run pytest -W error --junitxml=reporte-pruebas.xml` y luego `uv run python scripts/verificar_omitidas.py reporte-pruebas.xml` |
| Cobertura de `core/` ≥ 80 % | `uv run coverage report --include="core/*" --fail-under=80` (tras la suite con `--cov=core`) |
| Reproducibles | `uv run python scripts/exportar_openapi.py`, `uv run python scripts/generar_resultados_ml.py` y `git diff --exit-code -- docs/api.json docs/resultados_ml.md` |

Convenciones: código, docstrings y commits en español (identificadores sin tildes);
Conventional Commits (`feat(core): …`); `Decimal` en todo número monetario o dimensional —
nunca `float` — y redondeo solo al presentar; una rama por incremento y bitácora por sprint.
El estado de cada RF y la prueba que lo demuestra están en [plan_pruebas.md §8](plan_pruebas.md);
la suite y la cobertura vigentes, con la corrida de CI que las mide, en su §10.

## 3. Mapa del código

| Paquete | Papel | Piezas clave |
|---|---|---|
| `core/contracts` | los únicos tipos que cruzan fronteras (estables) | `ItemComputo`, `AdaptadorDominio`, `ComposicionAPU`, `ParametrosCosto`, `Presupuesto`, `ReglaVerificacion` |
| `core/costing` | motor de costos, función pura | `calcular_apu(composicion, parametros)` |
| `core/models` + `core/catalog` | SQLite (SQLAlchemy) y catálogo | `Catalogo`, `crear_lista_desde_archivo`, rendimientos con dispersión |
| `core/budget` | presupuesto, curva, exportación, UC‑02 y UC‑08 | `elaborar` (audita siempre), `actualizar_precios`, `generar_escenario` |
| `core/verification` | reglas R1–R7 e informe | `auditar`, `ReglaVerificacion.evaluar -> list[Hallazgo]`, `ReglaAtribuible.atribuir` (sección 5), `InformeAuditoria` |
| `adapters/{civil,telecom,industrial,sistemas}` | fuente de cada dominio → `ItemComputo` | sección 4 |
| `ml/` | normalización, anomalías, predicción | no conoce la base de datos: recibe datos planos |
| `api/` | FastAPI sobre el núcleo | montos como texto; OpenAPI exportado a `docs/api.json` |
| `ui/` | Streamlit multipágina | presentación; llama a `core` directo. La composición de APU a mano vive en la capa pura `ui/composicion.py` (sección 10.2). Tres páginas importan de `scripts/`: el Inicio siembra con `scripts.seed_demo`, la de actualización con `scripts.seed` y el simulador con `scripts.simular_lista` |
| `scripts/` | operaciones reproducibles | índice en [scripts/README.md](../scripts/README.md) (sección 8) |

El flujo completo de UC‑01: `AdaptadorDominio.extraer(fuente)` → `list[ItemComputo]` →
`core.budget.elaborar(items, composiciones, parametros, ..., plan=...)` → `ResultadoElaboracion`
(presupuesto + informe). El `plan` es el del proyectista (la tabla de la pantalla o el campo `plan`
de la API) o, sin él, `plan_secuencial` (sección 9). La fórmula del motor y sus dos errores clásicos (dividir materiales
entre rendimiento; sumar administración y utilidad en vez de encadenarlas) están en
[NORMAS.md §4](../NORMAS.md) y las vigila `tests/unit/test_costing.py`.

## 4. Escribir un adaptador de dominio nuevo

Un adaptador convierte la fuente propia de un dominio (un IFC, un CSV de topología, un registro
de activos…) en cantidades de obra **trazables**. Todo lo demás — costos, presupuesto, curva,
auditoría, exportación — lo hace el núcleo sin saber de dónde vinieron las cantidades.

### 4.1 El contrato

```python
# core/contracts/adaptador.py (completo; así de pequeño es)
class AdaptadorDominio(ABC):
    dominio: ClassVar[Dominio]

    @abstractmethod
    def extraer(self, fuente: Path | str) -> list[ItemComputo]: ...
```

Cada `ItemComputo` exige: `codigo_partida` (del catálogo, no inventado), `descripcion`, `unidad`
(se normaliza sola: `m³` ≡ `m3`, `pza` ≡ `pieza`), `cantidad` (`Decimal`, ≥ 0), **`origen_id`
real** (GlobalId del elemento IFC, clave de la fila CSV…), `origen_tipo` y `dominio`. Si la
cantidad la produjo una regla paramétrica, `regla` lleva la expresión y `parametros` los valores
(la regla R1 los reevalúa al auditar); `especificaciones` guarda atributos comparables
(diámetro, material) para la regla R4.

### 4.2 Pasos

1. **Crear el paquete** `adapters/<dominio>/` con su `adaptador.py`. Si el dominio tiene reglas
   paramétricas necesita un evaluador de expresiones, y hoy no hay uno que un adaptador pueda
   importar: el del núcleo (`core/verification/expresiones.py`) está fuera de `core.contracts`.
   Por eso el evaluador existe en **cinco copias**, la del núcleo y una por adaptador
   (`adapters/{civil,industrial,sistemas,telecom}/evaluador.py`): es deuda declarada (INV‑006,
   aceptada por decisión de arquitectura registrada y pendiente del aval del tutor; ADR 8 de
   [arquitectura.md](arquitectura.md)). Su cierre previsto es un evaluador parametrizable en
   `core.contracts` ([expediente §A.3](bitacora/2026-09-23-C1-expedientes.md)). Mientras no
   exista, un adaptador nuevo con reglas agrega una **sexta** copia: partir de la de telecom
   (`adapters/telecom/evaluador.py`, suma, resta, producto y cociente) o de la de sistemas
   (solo suma y producto), reducir los operadores a los que sus reglas usan, llevar sus pruebas y
   declarar la copia en la bitácora de la sesión. La copia tiene que dar el mismo `Decimal` que el
   evaluador del núcleo, porque la regla R1 reevalúa con este último las expresiones de todo
   dominio al auditar; el patrón de esa comprobación es
   `tests/unit/test_verification.py::test_las_reglas_civiles_son_evaluables_por_el_nucleo`. Un
   adaptador sin reglas no la necesita.
2. **Subclasificar** `AdaptadorDominio`, declarar `dominio` e implementar `extraer()`:

   ```python
   from decimal import Decimal
   from pathlib import Path

   from core.contracts import AdaptadorDominio, Dominio, ItemComputo, OrigenTipo


   class AdaptadorRiego(AdaptadorDominio):
       """Lee el plano de riego en CSV y devuelve las cantidades que declara."""

       dominio = Dominio.CIVIL  # o el dominio que corresponda

       def extraer(self, fuente: Path | str) -> list[ItemComputo]:
           items = []
           for fila in _leer(Path(fuente)):          # el formato es asunto del adaptador
               items.append(
                   ItemComputo(
                       codigo_partida=fila.codigo,
                       descripcion=fila.descripcion,
                       unidad=fila.unidad,
                       cantidad=Decimal(fila.cantidad),   # Decimal desde texto, nunca float
                       origen_id=fila.clave,              # identificador REAL de la fuente
                       origen_tipo=OrigenTipo.CSV,
                       dominio=self.dominio,
                   )
               )
           return items
   ```

3. **Importar de `core` solo `core.contracts`.** Nada de `core.models`, `core.catalog` ni
   `core.costing`: el adaptador no consulta la base de datos ni calcula precios.
4. **Muestra y pruebas.** Dejar una fuente pequeña en `data/samples/<dominio>/` con su
   `README.md`, y escribir `tests/unit/test_adapter_<dominio>.py` **antes** de implementar
   (TDD; el patrón está en `tests/unit/test_adapter_telecom.py`): cantidades exactas en
   `Decimal`, `origen_id` presente en cada ítem, unidad normalizada, y el caso de fuente
   malformada (se rechaza citando la fila, no se adivina). Desde C5 (INV‑089) los cuatro
   adaptadores siguen la misma convención, que la API traduce a 422 y la pantalla muestra tal cual:
   toda fuente ilegible es un **`ValueError`** (nunca un `KeyError`, un `InvalidOperation` ni un
   `UnicodeDecodeError`) cuyo mensaje nombra el archivo **por su nombre, sin la ruta** del servidor
   (`Path(fuente).name`) y, si es de una fila, la fila y la columna. La cabecera se comprueba antes
   de leer: si faltan columnas del formato, «no es una fuente del dominio X», así una muestra de
   otro dominio no se confunde con una propia (el civil exige sus 13 columnas). El patrón está en
   `_leer_filas` y `_decimal` de cualquier adaptador tabular; son copias, porque ningún adaptador
   importa de otro (deuda declarada en [arquitectura §6.1](arquitectura.md#61-deuda-arquitectónica-declarada)),
   y su equivalencia la vigila `tests/unit/test_fuentes_ilegibles.py`, donde conviene agregar el
   dominio nuevo.
5. **Verificar las guardias.** `uv run pytest -W error` (la prueba de arquitectura ya incluye el
   módulo nuevo sin registrarlo en ningún lado) y `git diff --stat core/` → vacío.
6. **Cablear la entrada (opcional).** Para que la fuente se pueda subir por la interfaz:
   añadir el caso en `api/rutas/computos.py::_adaptador` y en la página
   `ui/paginas/elaborar.py`. Son las dos únicas listas de despacho; el núcleo no se toca.

### 4.3 Los límites, dichos honestamente

- La enumeración `Dominio` tiene cuatro valores (civil, telecom, industrial, sistemas). Un
  adaptador para una **variante** de esos dominios (otro formato de fuente, otra disciplina
  dentro de civil) no toca nada. Un **quinto dominio** exigiría añadir un miembro a esa
  enumeración, que es un contrato estable: la línea es trivial, pero la decisión es de
  gobernanza del proyecto y se registra en `docs/bitacora/` (NORMAS.md §5).
- Los `codigo_partida` que emite el adaptador deben existir en el catálogo al presupuestar; si
  la fuente no los trae (caso del civil tabular), el adaptador recibe el mapeo del llamador en
  su constructor — los códigos son del catálogo, no del adaptador.
- **El límite de `ifcopenshell`.** `adapters/civil/ifc.py::_abrir_modelo` rechaza con `ValueError`
  un archivo que no es STEP (sin la cabecera `ISO-10303-21`) y un STEP que `ifcopenshell` no puede
  abrir (cabecera dañada, esquema no soportado), comprobando el estado de
  `ifcopenshell_wrapper.open` **antes** de construir el `ifcopenshell.file`: con
  `ifcopenshell.open`, la versión 0.8.5 deja una excepción no atrapable en `file.__del__`, que con
  `-W error` rompe otra prueba al azar. El analizador, en cambio, **tolera el cuerpo**: un `.ifc`
  truncado o con basura tras una cabecera válida se abre sin error y da un cómputo vacío (o con los
  elementos que alcanzó a leer), sin rechazo. Está verificado contra `ifcopenshell` 0.8.5, la
  versión de `uv.lock` (`pyproject.toml` pide `>=0.8`, sin cota superior); si otra versión cambia
  esa API de bajo nivel, fallan las pruebas del IFC, no en silencio.
- Las especificaciones de un objeto civil (`especificaciones` del CSV) llegan solo a la partida
  del elemento que describen: el concreto en la tanquilla y la tubería en la zanja, no la
  excavación ni el encofrado (INV‑096). Una especificación de la excavación o del encofrado (tipo
  de suelo, madera) no se puede dirigir hoy desde esa columna.

## 5. Añadir una regla de verificación

Subclasificar `core.contracts.verificacion.ReglaVerificacion` en `core/verification/reglas.py`
(esto **sí** es núcleo: sesión de núcleo, no de adaptador), implementar
`evaluar(presupuesto) -> list[Hallazgo]` — cada hallazgo con severidad, descripción, impacto
cuantificado y los `origen_id` involucrados — y sumarla a la tupla `REGLAS` de ese módulo (el
valor por defecto que `auditar` recorre). Regla
de oro heredada de R1–R7: una regla que no puede evaluarse devuelve un hallazgo INFO, jamás
lanza; el informe nunca se cae a medias. Las pruebas van por regla en
`tests/unit/test_verification.py` y el caso integrado en
`tests/integration/test_auditoria_7_de_7.py` (que debe seguir en 7 de 7).

Lo que la regla nueva recibe sin hacer nada: el informe la enumera en **Reglas evaluadas** (su
`codigo` y su `nombre`, con su cuenta de hallazgos, en pantalla y en las columnas G a I de la hoja
*Auditoria*), porque `auditar` registra toda regla que corre (INV‑092). Lo que tiene que decidir:

- **La columna *Partida*.** Si sus hallazgos nacen de una partida concreta, que implemente también
  `atribuir(presupuesto) -> list[tuple[Hallazgo, str | None]]` (el protocolo `ReglaAtribuible` de
  `core/verification/reglas.py`, no un contrato): cada hallazgo con el código de la partida que lo
  produjo, o `None`. `auditar` usa entonces `atribuir` en lugar de `evaluar`, así que los dos
  tienen que dar exactamente los mismos hallazgos, en el mismo orden (la forma sencilla, la de
  R1, R3, R4, R5 y R7: `evaluar` devuelve los de `atribuir` sin la partida), y quien redefine uno
  redefine el otro. Si no lo implementa, el informe atribuye cada hallazgo por su primer
  `origen_id`, salvo que ese origen lo compartan varias partidas: entonces pinta «-», porque no
  adivina (INV‑095).
- **`InformeAuditoria` crece solo añadiendo campos al final, con valor por defecto**: no es un
  contrato de `core/contracts/`, pero `api/`, `ui/`, `scripts/` y `core.budget` lo consumen.
  Quien lo copie con cambios usa `dataclasses.replace`, como `_declarar_pendientes`
  ([arquitectura §2.2](arquitectura.md#22-clases-y-funciones-del-núcleo), «Verificación»).

## 6. Persistencia

Modelo en [modelo_datos.md](modelo_datos.md); entidades SQLAlchemy en `core/models/entidades.py`.
Los dos puntos que más preguntas generan:

- **Versionado híbrido:** el renglón guardado congela su `ResultadoAPU`; al cargar, el sistema
  recomputa desde el catálogo y comprueba que sigue reproduciéndolo. Reconstruir un presupuesto
  «a su fecha» usa la lista de precios vigente en esa fecha (RNF‑02, 100 % exacto).
- **Rendimiento medido ≠ estimado:** el medido exige clave foránea a una `Ejecucion` real; la
  invariante vive en el contrato y en el esquema.
- **No hay herramienta de migraciones:** `create_all` crea tablas ausentes pero nunca altera una
  existente. Cambiar una columna exige la regla de la sección 10.5. Las **tablas aditivas**
  (`descarte_version`, C3; `justificacion_rendimiento`, C6) no son migraciones: una base anterior
  las gana al abrirse con `crear_esquema`, sin `ALTER TABLE` y conservando sus filas.

## 7. `ml/` y sus compuertas

`ml/` recibe datos planos y devuelve datos planos; la capa de composición (quién consulta la
base y le pasa los pares) es la página o la ruta que lo usa. De `core`, `ml/` importa
**únicamente `core.contracts`** (el `Hallazgo` del contraste AACE de `prediction`): la misma
frontera que los adaptadores, vigilada por `tests/unit/test_arquitectura.py`. Los tres módulos:
`normalization` (similitud del coseno, umbral 0,5), `anomaly` (Isolation Forest, semilla 42, se
**abstiene** con menos de 8 observaciones) y `prediction` (técnica según el conteo de registros
del dominio — compuerta G2, hoy reglas con sensibilidad en los cuatro dominios, declarado
limitación). Conteo G2 y métricas por dominio, reproducibles:
`uv run python scripts/generar_resultados_ml.py` → [resultados_ml.md](resultados_ml.md).

## 8. Scripts reproducibles

El índice de los scripts —qué hace cada uno, agrupados en siembra, datos derivados, simulación y
medición, artefactos reproducibles, guardias de la CI y metas de sprint— vive en un solo lugar,
[scripts/README.md](../scripts/README.md): una fila por script, y
`tests/unit/test_scripts_documentados.py` falla si alguno no la tiene (INV‑051). Esta sección no
lo repite (INV‑056); solo agrega lo que quien mantiene el código necesita saber de algunos:

- Las opciones de siembra (`--db`, `--reiniciar` y `--confirmar`) y la procedencia de los precios
  de cada dominio están en la sección 8.1; el corpus simulado de `simular_corpus.py` tiene su
  cuarentena (sección 10.4).
- `guardia_nucleo.py` y `verificar_omitidas.py` son pasos de la CI; su comando local está en la
  sección 2.

`probar_precios_maprex.py` (C6) revalora los casos didácticos con los listados MaPreX de julio de
2026 y el tabulador CIV, siempre sobre bases temporales (no tiene `--db`, no toca `data/apu.db` ni
la línea base). Se ejecuta con `uv run --all-extras python scripts/probar_precios_maprex.py
[--salida resultado.md]`: `--all-extras` deja el entorno como lo sincronizan la CI y el README; sin
el extra `ml` corre igual, sin detector de atípicos, y el informe lo declara. Su resultado
registrado está en `docs/bitacora/2026-09-29-C6-precios-maprex.md`.

PyMuPDF no es dependencia del proyecto: los dos extractores se ejecutan con
`uv run --with pymupdf python scripts/<extractor>.py` y ninguna prueba lo importa. Sus salidas
están versionadas, así que regenerarlas solo hace falta si cambia el PDF de origen.

### 8.1 Catálogos por dominio

Los cuatro dominios siguen el patrón de la línea base: evidencia de precios fechada en `data/`,
**una sola copia** estructurada en `tests/fixtures/` y un seed que importa ese fixture en vez de
copiarlo (no es el único script que lo importa: §9). Ningún seed escribe un precio: todos los leen.

| Dominio | Fuente de precios | Copia única | Seed → base por defecto |
|---|---|---|---|
| civil | `data/linea_base/APUS_CLINICA.pdf` (caso de ejemplo, 28/04/2026) | `apu_linea_base.py` | `seed.py` → `data/apu.db` |
| telecom | presupuestos ARENAZA de `data/samples/telecom/`, estructurados en `data/telecom/fuentes/` (18/05/2026) | `presupuestos_arenaza.py` | `seed_telecom.py` → `data/apu_telecom.db` |
| industrial | referencia MaPreX jul‑2026 como proxy declarado (degradación GM2): `data/precios/maprex_2026-07/referencia_industrial.csv` | `mantenimiento_industrial.py` | `seed_industrial.py` → `data/apu_industrial.db` |
| sistemas | tabulador CIV al 01/07/2026: `data/precios/maprex_2026-07/referencia_sistemas.csv` (la productividad HH/PF es un supuesto declarado) | `tarifas_sistemas.py` | `seed_sistemas.py` → `data/apu_sistemas.db` |

Los cuatro seeds aceptan `--db <ruta>` y `--reiniciar`. Sobre la ruta por defecto, `--reiniciar`
exige además `--confirmar` (sin él la orden se niega con código 2 y no toca la base), también
si esa misma ruta se escribe con `--db`; con `--db` hacia otra ruta basta `--reiniciar`.
Cada carpeta `data/<dominio>/fuentes/`
trae un `README.md` con origen, vigencia y supuestos de sus precios; las reglas de uso de MaPreX
(referencia, no ronda vigente; tasa única 633,3644 Bs/USD del 01/07/2026) están en
`data/precios/maprex_2026-07/README.md`. Una cotización de campo nueva no se edita en ningún
fixture: se registra según [protocolo_precios.md](protocolo_precios.md) y entra por UC‑02 como
lista fechada, lo que abre el histórico de `CambioPrecio` del dominio. La API sirve el
catálogo de otro dominio apuntando `APU_BASE` a su base (`sqlite:///data/apu_telecom.db`).

## 9. Decisiones que conviene conocer antes de tocar nada

- **La UI no consume la API por HTTP** (decisión registrada en la spec de F.1): ambas llaman a
  `core` directo. Si se añade una función, se expone en las dos capas por separado.
- **La API serializa montos como texto** — al añadir rutas, construir `Decimal` desde el texto
  en la frontera y devolverlo como `str`.
- **El plan de trabajo (UC‑01, paso 6; INV‑087).** `POST /presupuestos` acepta un campo opcional
  `plan`: una lista de `{"periodo": "Semana 1", "reparto": {"LB-01-EXC": "0.5", ...}}`, con las
  fracciones como texto decimal (esquema `PeriodoPlanPeticion`). Sin el campo, `plan_secuencial`
  (una partida por día), que es lo que deja la línea base como estaba. Un plan en que alguna
  partida no sume exactamente 1, que nombre una partida que el presupuesto no tiene o con una
  fracción que no es un decimal responde **422 sin guardar** (las dos primeras son `PlanInvalido`,
  un `ValueError`: la regla del plan vive una sola vez, en `core.budget.curva`). La pantalla hace lo mismo con la tabla
  «Plan de trabajo» (`ui.elaboracion.plan_desde_filas` y `plan_de`). Fracciones negativas o
  mayores que 1 pasan si la partida suma 1: es la regla de `core.budget.curva`, y ni la pantalla ni
  la API añaden otra (INV‑101, a limitaciones; lo fija
  `tests/integration/test_api_plan_y_rendimiento.py::test_fracciones_fuera_de_0_1_pasan_si_la_partida_suma_1`).
  Un `plan` vacío no es la ausencia del campo: cada partida suma 0 y responde 422
  (`::test_un_plan_vacio_responde_422_sin_guardar`).
- **El 409 del flujo 3b (UC‑01; INV‑088).** Si a una partida le falta un rendimiento **estimado**
  vigente (de fecha no posterior a la del presupuesto), `POST /presupuestos` responde **409 sin
  guardar** con el esquema `RendimientosPorDeclararRespuesta`: `detalle` y, por partida,
  `rendimientos_por_declarar[].propuesta` (el rendimiento de `core.catalog.proponer_rendimiento`
  con su dispersión, o `null` si la partida no tiene histórico). El cliente declara el tipo
  registrando el rendimiento con `POST /partidas/{codigo}/rendimientos` (tipo `estimado`, fecha no
  posterior a la del presupuesto) y reenvía el presupuesto; un medido registrado **no** lo
  desbloquea, porque la elaboración usa solo el estimado (`Catalogo._rendimiento_estimado`). Si lo
  que falta es la lista de precios vigente o un precio, el 409 es el de siempre, solo con
  `detalle`. El criterio «estimado vigente» está escrito en `api.rutas.presupuestos` y en
  `ui.elaboracion` porque la API no puede importar `ui/` y C5 no tocó `core.catalog`: si cambia la
  política, hay que cambiar los dos y `core` (deuda U‑5, [arquitectura §6.1](arquitectura.md#61-deuda-arquitectónica-declarada)).
- **`tests/fixtures/apu_linea_base.py` es la única copia de la línea base.** `seed.py`,
  `generar_resultados_ml.py`, `medir_rnf03.py`, `meta_prototipo.py` y `probar_precios_maprex.py` la
  importan a propósito; duplicarla en cualquier otro lado viola DRY. En total, nueve scripts
  dependen de `tests/fixtures/`
  ([arquitectura §4](arquitectura.md#4-vista-de-desarrollo-definitivo)): esos cinco,
  `seed_telecom.py`, `seed_industrial.py`, `seed_sistemas.py` y `extraer_arenaza.py`. Como la
  interfaz importa `scripts.seed`, la aplicación Streamlit no arranca sin `tests/fixtures/`.
- **Las rutas de C6** (dos nuevas y tres campos; esquema en `docs/api.json`):
  - `POST /proyectos` (UC‑01 1): cuerpo `{nombre, descripcion?, dominio?}`. 201 con el proyecto; 422 si
    el nombre está vacío o repetido o el dominio no es de `Dominio`. La interfaz no crea proyectos.
  - `POST /presupuestos/importar` (RF‑24, UC‑05 1 y 2): multipart con `archivo` (XLSX) y `proyecto`.
    201 con `PresupuestoCreadoRespuesta` (`pendientes` vacío); 404 si el proyecto no existe; 422, sin
    dejar nada escrito, si el archivo no es un libro legible o está mal formado (con archivo, hoja y
    fila), si un código de partida ya está en el catálogo, si el código de presupuesto se repite en
    el proyecto o si la moneda no es la de la lista vigente a su fecha (comparación exacta, sin
    normalizar: «usd» no es «USD»). El informe y el libro salen por `GET /presupuestos/{codigo}/informe`
    y `…/excel`. Se declara antes de las rutas con `{codigo}`.
  - `POST /listas-precios` gana el campo repetible `dar_de_alta` (descripciones del archivo, que
    elige por identidad normalizada, con `normalizar_texto`) y la respuesta gana `dados_de_alta`,
    `ignorados` (2a) y `rechazados` (2b); `desconocidos` sigue trayendo los dos últimos juntos. Un alta
    de lo que no es desconocido, o dos filas elegidas del mismo insumo con precios distintos, es 422
    sin escribir. **Por API no hay vista previa del flujo 2a**: el cliente elige en la misma carga a
    partir de su archivo y de `GET /insumos`; cargar el mismo archivo dos veces para ver los
    desconocidos deja dos listas, y **el nombre de la lista debe ser único**, porque
    `POST /presupuestos/{codigo}/actualizacion` la busca por nombre y con dos iguales responde 500
    (`MultipleResultsFound`, defecto anterior a C6, a limitaciones).
  - `POST /partidas/{codigo}/rendimientos` gana `justificacion` (UC‑06 4a): se registra solo si hay
    advertencia, ligada al rendimiento de esa misma petición; sin advertencia se ignora y la
    respuesta trae `justificacion: null`; con advertencia y en blanco, 422 sin registrar nada. Ninguna
    ruta la lee después.
  - `POST /presupuestos/{codigo}/actualizacion` pasa el detector `ml.anomaly.precios_atipicos` (UC‑07
    5): los atípicos de la lista nueva salen como `ATIPICO` (ADVERTENCIA) en el informe de la versión
    nueva. Requiere `scikit-learn` (la guarda es `importlib.util.find_spec("sklearn")`, no el import
    de `ml.anomaly`) y al menos `MINIMO_OBSERVACIONES` = 8 variaciones en el histórico; con menos, o
    sin el extra, no hay atípicos y el informe no lo dice.
  Las rutas de escritura hacen un `commit`; las que pueden fallar tras escribir (`importar`,
  `rendimientos`) hacen `rollback` ante `ValueError`, así que la petición es una sola operación.
- **El formato del XLSX de importación** (`core/budget/importacion.py`, fuente única de hojas y
  columnas: `HOJA_*`, `COLUMNAS_*`, `CLAVES_DATOS`). Un solo libro `.xlsx` o `.xlsm`; todo número se
  lee como texto y se convierte a `Decimal`. **Límite:** una celda numérica de Excel llega por `str()`
  del valor que guardó el libro (`data_only=True`): exacto si se tecleó, pero una celda de fórmula puede
  traer artefactos binarios (0,30000000000000004); conviene escribir los importes como texto.

  | Hoja | Columnas | Notas |
  |---|---|---|
  | `Datos` | `clave`, `valor` | claves obligatorias: `codigo`, `fecha` (ISO), `moneda`, `dominio`, `fcas`, `bono_alimentacion`, `administracion`, `utilidad` |
  | `Presupuesto` | `codigo_partida`, `descripcion`, `unidad`, `cantidad`, `origen_id`, `regla`, `parametros`, `especificaciones` | `parametros` y `especificaciones` son objetos JSON; con `regla` el origen es `REGLA`, sin ella `MANUAL` (R1 advierte); sin `origen_id`, `<archivo>:Presupuesto:<fila>`; la unidad del autor se conserva en `especificaciones[_unidad_original]` y llega a R3 |
  | `APU` | `codigo_partida`, `descripcion`, `unidad`, `rendimiento` | una fila por partida, sin repetir |
  | `Insumos` | `codigo_partida`, `tipo`, `insumo`, `unidad`, `cantidad`, `precio`, `depreciacion`, `modalidad` | `tipo` con las grafías de UC‑02; `unidad` solo en materiales; `depreciacion` solo en equipos; `modalidad` solo en mano de obra (jornal por defecto; en la mano de obra `precio` es el sueldo) |
  | `Curva` (opcional) | `periodo`, `monto`, `acumulado` | la curva del autor, tal cual; sin ella R2 y R7 no aplican |

  El presupuesto se **valora con el motor** sobre los APU y los parámetros del archivo: el formato
  no trae los precios unitarios ni los totales del autor. La importación crea la lista
  «Importada: <archivo>», con la moneda y la fecha del presupuesto, que **copia la lista vigente a esa
  fecha**, y carga los APU con las condiciones «importado de <archivo> (presupuesto de un tercero,
  UC-05)». Desde ese momento **la lista «Importada» es la vigente desde su fecha** para todo el caso
  (la muestra el marco de las pantallas, valora lo que se elabore o componga después y la copia la
  próxima lista que se cargue), y los APU del tercero cuentan en «Elaborar», en UC‑03 y en el recuento
  de la compuerta G2. Los importes no cambian; la procedencia sí (limitación, [arquitectura §6.1](arquitectura.md#61-deuda-arquitectónica-declarada)).
  Hay un fixture que escribe el libro desde el presupuesto de las siete inconsistencias:
  `tests/fixtures/presupuesto_tabular.py`.
- **No modificar `tests/unit/test_costing.py`** para poner nada en verde: se corrige la
  implementación.
- **UC‑08 no persiste nada.** `core/budget/escenarios.py` es la lógica; la ruta
  `POST /presupuestos/{codigo}/escenarios` y la página «Escenarios de sensibilidad» solo componen
  y presentan. Promover un escenario a presupuesto es UC‑02 con la lista nueva, a propósito. Si el
  base tiene ítems pendientes (UC‑01 3a), la página los declara al abrirlo y la API los devuelve en
  `pendientes_base` (esquema `PendienteRespuesta`: `codigo_partida`, `descripcion`, `unidad`,
  `cantidad` como texto decimal exacto y `origen_id`, sin propuestas); ningún escenario los
  recalcula ni los suma. El informe de auditoría del propio escenario no los declara, porque hacerlo exigiría cambiar `generar_escenario` en
  `core/` y va a limitaciones (ruling C4‑3 de la [bitácora del cierre](bitacora/2026-09-23-cierre.md)).
- Las limitaciones y los hallazgos abiertos están en dos lugares: el estado de cada RF en
  [plan_pruebas.md §8](plan_pruebas.md) y el [inventario de la auditoría](auditoria/2026-09-inventario.md),
  una fila por hallazgo con su fase y su estado (por ejemplo, el IFC exportado desde un modelador BIM
  para G1). Leerlos antes de «arreglar»
  algo que en realidad es una limitación declarada. RNF‑07 ya no figura entre ellos: la CI lo
  verifica en Linux y Windows en cada cambio.

## 10. El prototipo AREN.IA (hoy Sílice): composición de APU a mano (sprint P0–P5)

El sprint del prototipo añadió la pantalla que compone y edita una partida a mano (UC‑10 y UC‑11
de la [ERS](ERS.md), RF‑33 a RF‑35). El diseño y su porqué están en la
spec; la vista lógica de la
capa nueva, en [arquitectura.md §2.4](arquitectura.md#24-composición-de-partidas-en-la-ui-uicomposicionpy-sesión-p21);
el recorrido del sprint, en la [bitácora de cierre](bitacora/2026-09-16-sprint-prototipo.md).
Esta sección solo recoge lo que quien mantenga el código necesita saber.

### 10.1 La modalidad de mano de obra (decisión D9)

`LineaManoObra` lleva un campo `modalidad: ModalidadManoObra` (`StrEnum` con `JORNAL` y
`DESTAJO`), con `JORNAL` por defecto. `__post_init__` coacciona el texto (`"destajo"` →
`DESTAJO`) y rechaza cualquier otro valor con `ValueError`. El motor separa la suma:

```
mano_obra_jornal  = ( Σ cantidad × sueldo × (1 + FCAS) + bono × Σ cantidad ) / rendimiento   ← solo JORNAL
mano_obra_destajo =   Σ cantidad × sueldo                                                   ← solo DESTAJO, completo
mano_obra         = mano_obra_jornal + mano_obra_destajo
```

Bajo `DESTAJO`, `sueldo` no es un jornal diario sino el **precio por unidad de partida** del
artículo 114 de la LOTTT: no recibe FCAS ni bono ni se divide entre el rendimiento, y
`ComposicionAPU.total_obreros` (la base del bono) cuenta solo las líneas a jornal. El fundamento
normativo y las cuatro opciones evaluadas están en la [decisión D9 del dossier](dossier_g0.md) y en
la [bitácora del hallazgo](bitacora/2026-09-16-P0-hallazgo-destajo.md); no se repiten aquí.

**Por qué no afecta a la hipótesis central.** La hipótesis dice que `core/` no cambia al añadir un
**dominio**; D9 es un vacío de la estructura de costos venezolana, no un dominio, y ningún
adaptador cambió. El cambio es aditivo y retrocompatible: con todo a `JORNAL` el motor da los
mismos `Decimal` que antes, y `tests/unit/test_costing.py` y `tests/fixtures/apu_linea_base.py`
no se tocaron. Siguen vigentes las dos guardias de la sección 1: la prueba de arquitectura y
`scripts/guardia_nucleo.py`, que falla si un commit toca `core/` junto con `adapters/` o `ml/`.

La modalidad se persiste en la columna `composicion_apu.modalidad` (anulable: `NULL` se lee como
`jornal`, `core/catalog/mapeo.py`) y aparece como columna *Modalidad* en la hoja APU del Excel
(`core/budget/excel.py`).

### 10.2 Contratos y funciones nuevos

| Pieza | Dónde | Qué hace |
|---|---|---|
| `ModalidadManoObra` | `core.contracts` (reexportado en su `__all__`) | la enumeración de la sección 10.1 |
| `Catalogo.reemplazar_composicion(composicion, lista, dominio, fecha_rendimiento, condiciones) -> ResumenCarga` | `core/catalog/repositorio.py` | UC‑11: sustituye el desglose de una partida existente; registra un rendimiento ESTIMADO nuevo **solo si** cambia el valor o las condiciones respecto del último estimado, sin pisar el histórico |
| `Catalogo.cargar_composicion(..., condiciones)` | ídem | UC‑10: `condiciones` pasó a ser obligatorio (RF‑33); vacío lanza `ValueError` **antes** de crear la partida, así que no deja partida huérfana |
| `ui/composicion.py` | capa pura de la interfaz | `composicion_desde_tablas`, `formulario_vacio`, `item_desde_cantidad` (origen `MANUAL`), `buscar_referencia` y `FilaReferencia` (los cuatro CSV de la referencia MaPreX), `fila_*_desde_referencia`, y las cuatro ayudas (`sugerir_partidas_similares`, `advertencia_precio_atipico`, `veredicto_ml_rendimiento`, `contrastar_precio_con_reglas`) con `ml` importado de forma perezosa |

`ui/composicion.py` recibe filas de texto (`dict[str, str]`) y devuelve tipos del contrato; los
errores (`ComposicionInvalida`) dicen tabla, fila y campo. **No importa `streamlit` ni `pandas`**,
ni siquiera dentro de una función: lo vigila la meta P7 de `scripts/meta_prototipo.py`. La página
`ui/paginas/componer.py` solo pinta y decide entre `cargar_composicion` y `reemplazar_composicion`.

### 10.3 Probar la interfaz con `AppTest`

`tests/unit/test_ui_componer.py` son las primeras pruebas del repositorio que ejecutan una pantalla
(`streamlit.testing.v1.AppTest`, Streamlit 1.62). Corren dentro de la CI normal con `-W error`,
sin `filterwarnings` ni marcador. Lo que hay que saber para escribir otra:

- **El guion es de dos líneas:** `AppTest.from_string("from ui.paginas.componer import render\nrender()\n")`.
  `AppTest.from_function(render)` no sirve: serializa el cuerpo y pierde los globales del módulo.
- **`AppTest` no puede teclear en `st.data_editor`.** Las tablas se siembran en
  `st.session_state[f"{clave}__filas"]` (`componer_materiales__filas`, `componer_equipos__filas`,
  `componer_mano_obra__filas`, `componer_cantidades__filas`) **antes del primer `at.run()`**; sembrar
  después no surte efecto porque el editor conserva su estado.
- **Desvío de la base.** Se parcha `RUTA_BASE_POR_DEFECTO` sobre el **objeto módulo** que devuelve
  `importlib.import_module("ui.paginas.componer")` (el de `sys.modules`, que es el que ejecuta
  `AppTest`), no con una ruta de texto, y se afirma `base.exists()` tras el primer `run()`: si el
  desvío fallara, la prueba falla ruidosamente en vez de escribir en `data/apu.db`. La ruta de texto
  se abandonó porque un aislamiento defectuoso de otra prueba dejaba el atributo del paquete
  `ui.paginas` desincronizado de `sys.modules` (hallazgo en la [bitácora de
  cierre](bitacora/2026-09-16-sprint-prototipo.md)).
- **El doble de la ayuda 1.** Con catálogo no vacío y descripción tecleada, `sugerir_partidas_similares`
  carga `sentence-transformers`; las pruebas la sustituyen por `lambda *_: []` en el mismo objeto
  módulo.
- Los widgets se localizan por su rótulo (`"Codigo"`, `"Descripcion"`, `"Unidad"`,
  `componer.RENDIMIENTO_ETIQUETA`); las pruebas que guardan siembran antes la base temporal con
  `scripts.seed_demo.main(["--db", ...])`, y todo motor que abre una prueba se cierra con
  `motor.dispose()` (en Windows un archivo abierto no se puede borrar).

Lo que `AppTest` no cubre (teclear en las celdas, la experiencia de uso) lo cubre el
[guion de prueba manual](guion_prueba_arenia.md), con resultados esperados obtenidos por ejecución.

### 10.4 El corpus simulado y su cuarentena

`scripts/simular_corpus.py --db <ruta nueva> [--n 200] [--semilla 42]` genera partidas `SIM-*`
**simuladas** para probar la interfaz con volumen: combina filas de la referencia MaPreX con
cantidades y rendimientos sorteados desde enteros (`Decimal(entero) / Decimal(100)`, nunca
`float`), con la misma capa pura que usa la pantalla. No es dato de mercado ni de obra y no cuenta
para ninguna compuerta, en particular para G2. La cuarentena tiene dos capas: `main` se niega si
el archivo de `--db` ya existe (el corpus nunca se mezcla con una base de trabajo) y la meta P11
falla si algún módulo de `ml/` menciona el generador o el corpus. Todas las partidas se cargan como
`Dominio.CIVIL` aunque sus insumos vengan de las cuatro referencias MaPreX: el dominio del corpus
no describe su origen.

### 10.5 La regla de las migraciones

El proyecto no tiene Alembic: `Base.metadata.create_all` crea las tablas ausentes y **no altera**
las existentes, así que una columna nueva no llega a las bases ya sembradas y la interfaz falla
con `OperationalError`. Pasó con `modalidad` en la fase P2
([bitácora del hallazgo](bitacora/2026-09-20-P2-hallazgo-migraciones.md), con las dos salidas:
`ALTER TABLE … ADD COLUMN` aditivo o volver a sembrar con `--reiniciar`, que sobre la ruta por
defecto exige `--confirmar` y con `--db` hacia otra ruta no). **Regla:** toda sesión que
añada o cambie una columna de `core/models/entidades.py` declara en su plan, antes de escribir el
código, qué les pasa a las bases que ya existen en disco.

La fase C3 dejó un caso de esa regla sin migración, declarado: desde `04ca90d` (INV‑080) un
presupuesto se guarda con sus ítems pendientes (UC‑01 3a), y su recarga devuelve el informe
emitido. Una base guardada **antes** de ese commit no tiene los pendientes persistidos: la recarga
no los inventa y el informe recargado es la reauditoría de los renglones valorados, que puede decir
CUMPLE sobre un documento que se emitió NO CUMPLE (no conformidad residual con RF‑02, dictamen
C3‑3). Para que su informe recargado declare los pendientes, esa base se vuelve a sembrar.

## 11. Interfaz del sprint final: menú superior, barra de herramientas y subidas (SF4)

**Menú y marco.** `ui/app.py` llama a `st.navigation(secciones, position="top")` (Streamlit ≥ 1.62,
fijado en el extra `ui` de `pyproject.toml`; `tests/unit/test_ui_app.py` falla con una versión sin
`position="top"`). Son once pantallas en dos grupos, Trabajo e Investigación; la «Hoja del
proyecto» va en Trabajo, justo después de Elaborar; `SILICE_MODO_ENTREGA=1` sigue omitiendo
Investigación. `marco()` pinta, en este orden: la barra de herramientas, el título, el subtítulo
del caso de uso, el caso abierto (barra lateral), el paso del recorrido, la pantalla y el botón
«Siguiente».

> **Nombres de las variables.** Desde la 0.6.0 se llaman `SILICE_CASO` y `SILICE_MODO_ENTREGA`.
> Los nombres anteriores, `ARENIA_CASO` y `ARENIA_MODO_ENTREGA`, se aceptan como alias solo
> hasta la 0.6.0; si están las dos, manda la nueva (`ui/entorno.py`).

**Barra de herramientas (`ui/barra.py`).** La importa **solo** `ui/app.py` (lo vigila
`test_solo_ui_app_importa_la_barra_de_herramientas`); ninguna página importa el marco. No conoce
las claves de la hoja: cuando una herramienta pide trabajo a la hoja, deja una *acción pedida* con
`ui.caso.pedir_accion(...)` y navega; la pantalla la consume con `ui.caso.tomar_accion()` al
renderizar. Desde la integración final `ui/paginas/hoja.py` atiende las cuatro acciones
(`ACCION_PRECIOS`, `ACCION_IMPORTAR_PLANO`, `ACCION_GUARDAR_VERSION` y `ACCION_EXPORTAR_EXCEL`).
Tres ganchos de detección, hoy **todos conectados**:

| Gancho | Detección | Estado hoy |
|---|---|---|
| Importar plano (SF5) | `hay_importacion_de_planos()`: `importlib.util.find_spec("adapters.espacio.planos")` | disponible: abre el flujo de importar de la pestaña *Espacio y metrajes*; se oculta si el paquete no existe |
| Guardar versión y Exportar Excel (SF3) | `hay_guardado_y_exportacion()`: `ui.hoja` expone las funciones de `FUNCIONES_DE_SF3` (`guardar_version`, `exportar_excel`) | disponibles (la hoja las expone): llevan al panel de guardado y preparan el Excel; si faltaran, se deshabilitan con la ayuda y el aviso visible |
| Precios (SF3) | `"Precios" in ui.paginas.hoja.PESTANAS` | la pestaña existe: lleva a *Precios* de la hoja (sin ella, a Actualizar precios) |

El guardado exige fuente y responsable (RF‑53) y el Excel se genera solo al pulsar, así que ambos
viven en la pantalla de la hoja, no en la barra. Si alguien renombra las funciones de `ui/hoja.py`,
hay que cambiar `FUNCIONES_DE_SF3` en un solo lugar. La acción pedida pasa por `CLAVE_ACCION_PENDIENTE`
de la pantalla, porque abrir una versión reinicia la ejecución y la acción no puede perderse.
`tests/unit/test_ui_barra_con_la_hoja.py` corre la barra y la hoja **reales** en el mismo guion
(sin parchar nada) y prueba los dos caminos: con las funciones y borrándolas.

**La hoja sigue al proyecto de la barra.** `_seguir_al_proyecto_de_la_barra` (en la pantalla de la
hoja) compara el proyecto que abrió la barra (`ui.caso.proyecto_abierto()`) con el último que la hoja
vio; solo cuando cambia, fija el selector *Proyecto* de la hoja. Así lo que el usuario elige después en
la hoja no se pisa en cada ejecución.

**Proyectos (`ui/proyectos.py`, sin Streamlit).** `crear_proyecto_nuevo` valida (nombre no vacío,
único sin distinguir mayúsculas ni espacios sobrantes, caso existente) antes de llamar a
`core.budget.crear_proyecto`, que repite las dos reglas; `version_vigente` y `resumen_auditoria`
leen el último presupuesto no descartado del proyecto. Ninguna función crea el archivo de la base.
`ui.proyectos._vigente` (último presupuesto no descartado) es la versión vigente de la barra; la hoja
usa la suya (`ui.hoja.codigo_vigente`, la que marca el historial). Coinciden mientras no se restaure una
versión anterior.

**Subidas (`ui/subidas.py`, A‑1).** `guardar_subida(directorio, archivo)` es la única forma de
escribir una subida de Streamlit: conserva solo el último componente del nombre (separadores `/` y
`\`), reemplaza los caracteres prohibidos en Windows, quita espacios y puntos finales, renombra con
`_` los nombres reservados (`CON`, `NUL`, `COM1`…), acota a 100 caracteres conservando la extensión
y rechaza con `ValueError` el nombre sin componente utilizable. `actualizacion`, `elaborar` y
`visor` la usan; un test impide volver a unir `archivo.name` a una carpeta. Imita las reglas de
`api/archivos.py` sin importarlo (`ui` no importa `api`).

**Probar la barra con `AppTest`.** `tests/unit/test_ui_barra.py` corre `pintar_barra(ruta, ir_a)` en
un guion de cuatro líneas, con un `ir_a` que solo anota el destino en `st.session_state`; los
popovers se localizan con `at.get("popover")` (`.proto.popover.label`) y sus widgets con su `key`.
Los estados sin la hoja se simulan quitando los atributos del objeto módulo
(`monkeypatch.delattr(ui.hoja, ...)`).

## 12. Importar planos en la hoja (integración de SF3, SF4 y SF5)

**Capas.** `adapters/espacio/planos/` lee el plano (`dxf.importar_dxf`, `ifc.importar_ifc`) y deja un
`ResultadoImportacion` con las filas por tabla y el informe; su `__init__` solo reexporta el informe,
así que importar `adapters.espacio` (que carga la interfaz) no carga `ezdxf` ni `ifcopenshell`
(extras perezosos). `ui/hoja.py` (sin Streamlit) orquesta: `leer_plano` (importa el lector al leer y
traduce la falta del extra a `HojaInvalida`), `subir_plano` (`ui.subidas.guardar_subida`, A‑1, y rechaza
un formato ajeno antes de escribir), `resumen_del_informe`, `filas_del_informe` (quita las
referencias internas entre paréntesis), `alturas_pendientes` y `cargar_alturas_desde_texto` (acepta coma
decimal, hasta 250 m, todo o nada), `circuitos_supuestos` y `declarar_circuitos_desde_texto`, y
`fusionar_plano` (devuelve un `Borrador` nuevo y el informe de la fusión; una importación detenida o
rechazada es `HojaInvalida`). La pantalla solo pinta (`_importar_plano` en `ui/paginas/hoja.py`): el
resultado vive en `st.session_state[CLAVE_IMPORTACION]`, que no es de ningún widget.

**Garantías (DA‑SF‑6).** El plano nunca salta la hoja ni la auditoría: `fusionar_plano` solo cambia el
`espacio` del borrador; `elaborar_borrador` audita con `REGLAS + reglas_espacio`, y R8 marca las filas
que siguen siendo supuestos (circuitos sin declarar). `tests/unit/test_hoja_planos.py` (lógica),
`tests/unit/test_ui_hoja_planos.py` (pintado con la importación precargada: `AppTest` no sube
archivos) y `tests/integration/test_aceptacion_sf.py` (del DXF de OF‑001 al Excel evaluado con
`formulas`) lo comprueban.

**Límites conocidos.** (1) La primera versión de un proyecto nuevo se guarda con `ui.hoja.crear_primera_version` (RI‑7):
lista vigente a la fecha del borrador, parámetros del borrador, plan secuencial si no hay plan, un
`RegistroCambio` de creación y sin `VersionOrigen` (el núcleo no tiene motivo `creacion`; propuesta en la
bitácora, RI‑17). (2) El Excel de la hoja no se reimporta (RS‑3). (3) Un
borrador nuevo usa los parámetros por defecto de la aplicación (bono 1,00), no los del caso: por eso
su total puede diferir del de una versión guardada con otros parámetros.

**Base de CP‑08 a CP‑11.** `scripts/seed_of001.py` siembra OF‑001 (catálogo, lista, proyecto, versión
`001` con su espacio) en `data/prueba_sf.db`; se niega a escribir en `data/apu.db` y exige `--reiniciar`
si el archivo existe (`tests/unit/test_seed_of001.py`).
