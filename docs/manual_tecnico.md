# Manual técnico — Sesión F.3

Guía para quien vaya a mantener o extender el sistema. El aporte central del trabajo es la
**extensibilidad sin tocar el núcleo**, así que el corazón de este manual es la sección 4: cómo
un tercero escribe un adaptador de dominio nuevo. La constitución del proyecto es
[CLAUDE.md](../CLAUDE.md); la arquitectura completa (vistas 4+1), [arquitectura.md](arquitectura.md);
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
documentan en `docs/bitacora/`, no se parchean (CLAUDE.md §9).

## 2. Entorno de desarrollo

```
uv sync --extra ui --extra api --extra civil --extra ml   # todo
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
El estado de las pruebas y la cobertura vigente están en [plan_pruebas.md](plan_pruebas.md).

## 3. Mapa del código

| Paquete | Papel | Piezas clave |
|---|---|---|
| `core/contracts` | los únicos tipos que cruzan fronteras (estables) | `ItemComputo`, `AdaptadorDominio`, `ComposicionAPU`, `ParametrosCosto`, `Presupuesto`, `ReglaVerificacion` |
| `core/costing` | motor de costos, función pura | `calcular_apu(composicion, parametros)` |
| `core/models` + `core/catalog` | SQLite (SQLAlchemy) y catálogo | `Catalogo`, `crear_lista_desde_archivo`, rendimientos con dispersión |
| `core/budget` | presupuesto, curva, exportación, UC‑02 y UC‑08 | `elaborar` (audita siempre), `actualizar_precios`, `generar_escenario` |
| `core/verification` | reglas R1–R7 e informe | `auditar`, `ReglaVerificacion.evaluar -> list[Hallazgo]` |
| `adapters/{civil,telecom,industrial,sistemas}` | fuente de cada dominio → `ItemComputo` | sección 4 |
| `ml/` | normalización, anomalías, predicción | no conoce la base de datos: recibe datos planos |
| `api/` | FastAPI sobre el núcleo | montos como texto; OpenAPI exportado a `docs/api.json` |
| `ui/` | Streamlit multipágina | solo presentación; llama a `core` directo. La composición de APU a mano vive en la capa pura `ui/composicion.py` (sección 10.2) |
| `scripts/` | operaciones reproducibles | tabla en la sección 8 |

El flujo completo de UC‑01: `AdaptadorDominio.extraer(fuente)` → `list[ItemComputo]` →
`core.budget.elaborar(items, composiciones, parametros, ...)` → `ResultadoElaboracion`
(presupuesto + informe). La fórmula del motor y sus dos errores clásicos (dividir materiales
entre rendimiento; sumar administración y utilidad en vez de encadenarlas) están en
[CLAUDE.md §4](../CLAUDE.md) y las vigila `tests/unit/test_costing.py`.

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

1. **Crear el paquete** `adapters/<dominio>/` con su `adaptador.py` (y un `evaluador.py` si hay
   reglas paramétricas: véase `adapters/telecom/`, el ejemplo más pequeño).
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
   malformada (se rechaza citando la fila, no se adivina).
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
  gobernanza del proyecto y se registra en `docs/bitacora/` (CLAUDE.md §5).
- Los `codigo_partida` que emite el adaptador deben existir en el catálogo al presupuestar; si
  la fuente no los trae (caso del civil tabular), el adaptador recibe el mapeo del llamador en
  su constructor — los códigos son del catálogo, no del adaptador.

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

## 6. Persistencia

Modelo en [modelo_datos.md](modelo_datos.md); entidades SQLAlchemy en `core/models/entidades.py`.
Los dos puntos que más preguntas generan:

- **Versionado híbrido:** el renglón guardado congela su `ResultadoAPU`; al cargar, el sistema
  recomputa desde el catálogo y comprueba que sigue reproduciéndolo. Reconstruir un presupuesto
  «a su fecha» usa la lista de precios vigente en esa fecha (RNF‑02, 100 % exacto).
- **Rendimiento medido ≠ estimado:** el medido exige clave foránea a una `Ejecucion` real; la
  invariante vive en el contrato y en el esquema.
- **No hay herramienta de migraciones:** `create_all` crea tablas ausentes pero nunca altera una
  existente. Cambiar una columna exige la regla de la sección 10.5.

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

| Script | Produce |
|---|---|
| `scripts/seed.py` | `data/apu.db` con la línea base (idempotente) |
| `scripts/seed_telecom.py`, `scripts/seed_industrial.py`, `scripts/seed_sistemas.py` | catálogo, presupuesto auditado y lista de precios de cada dominio en su propia base (sección 8.1) |
| `scripts/extraer_maprex.py` | `data/precios/maprex_2026-07/referencia_<dominio>.csv` desde los tres listados MaPreX |
| `scripts/extraer_arenaza.py` | `data/telecom/fuentes/presupuesto_{1,2}_arenaza.csv` desde los PDF ARENAZA |
| `scripts/derivar_listas_telecom.py` | las dos listas UC‑02 de telecom (ARENAZA y MaPreX); `--verificar` las compara con las de disco |
| `scripts/simular_lista.py` | listas de precios de prueba, deterministas por semilla |
| `scripts/generar_tanquilla_ifc.py` | `data/samples/tanquilla.ifc` (la muestra de G1) |
| `scripts/exportar_openapi.py` | `docs/api.json` |
| `scripts/generar_resultados_ml.py` | `docs/resultados_ml.md` (conteo G2 y métricas RF‑28 por dominio) |
| `scripts/medir_rnf03.py` | evidencia de RNF‑03 (100 partidas, umbral 5 s) |
| `scripts/seed_demo.py` | en una sola orden: línea base, las tres partidas `DEMO-*` (caso didáctico de AREN.IA) con su lista heredando los precios de la vigente, y el presupuesto `DEMO-001` guardado con su informe (idempotente; `--db`, `--reiniciar`) |
| `scripts/lista_maprex_usd.py` | `data/precios/maprex_2026-07/lista_maprex_usd.csv`, la referencia MaPreX en el formato canónico `tipo,insumo,unidad,precio` (en equipos, `precio` es el valor del activo, no una tarifa diaria) |
| `scripts/simular_corpus.py` | corpus **simulado** de partidas `SIM-*` para pruebas de volumen de la interfaz, siempre en una base nueva (sección 10.4) |
| `scripts/meta_alpha.py`, `scripts/meta_i6.py`, `scripts/meta_multidominio.py`, `scripts/meta_prototipo.py` | evaluación automática de metas de sprint (`meta_prototipo.py --hasta P<n>` evalúa por fases) |

PyMuPDF no es dependencia del proyecto: los dos extractores se ejecutan con
`uv run --with pymupdf python scripts/<extractor>.py` y ninguna prueba lo importa. Sus salidas
están versionadas, así que regenerarlas solo hace falta si cambia el PDF de origen.

### 8.1 Catálogos por dominio

Los cuatro dominios siguen el patrón de la línea base: evidencia de precios fechada en `data/`,
**una sola copia** estructurada en `tests/fixtures/` y un seed que es el único módulo fuera de
`tests/` que importa ese fixture. Ningún seed escribe un precio: todos los leen.

| Dominio | Fuente de precios | Copia única | Seed → base por defecto |
|---|---|---|---|
| civil | `data/linea_base/APUS_CLINICA.pdf` (caso de ejemplo, 28/04/2026) | `apu_linea_base.py` | `seed.py` → `data/apu.db` |
| telecom | presupuestos ARENAZA de `data/samples/telecom/`, estructurados en `data/telecom/fuentes/` (18/05/2026) | `presupuestos_arenaza.py` | `seed_telecom.py` → `data/apu_telecom.db` |
| industrial | referencia MaPreX jul‑2026 como proxy declarado (degradación GM2): `data/precios/maprex_2026-07/referencia_industrial.csv` | `mantenimiento_industrial.py` | `seed_industrial.py` → `data/apu_industrial.db` |
| sistemas | tabulador CIV al 01/07/2026: `data/precios/maprex_2026-07/referencia_sistemas.csv` (la productividad HH/PF es un supuesto declarado) | `tarifas_sistemas.py` | `seed_sistemas.py` → `data/apu_sistemas.db` |

Los cuatro seeds aceptan `--db <ruta>` y `--reiniciar`. Cada carpeta `data/<dominio>/fuentes/`
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
- **`tests/fixtures/apu_linea_base.py` es la única copia de la línea base.** `seed.py` y
  `medir_rnf03.py` la importan a propósito; duplicarla en cualquier otro lado viola DRY.
- **No modificar `tests/unit/test_costing.py`** para poner nada en verde: se corrige la
  implementación.
- **UC‑08 no persiste nada.** `core/budget/escenarios.py` es la lógica; la ruta
  `POST /presupuestos/{codigo}/escenarios` y la página «Escenarios (UC‑08)» solo componen y
  presentan. Promover un escenario a presupuesto es UC‑02 con la lista nueva, a propósito.
- Los hallazgos abiertos del proyecto (flujo de creación de partidas para RF‑16, IFC real para
  G1, Linux para RNF‑07) están en las bitácoras de [bitacora/](bitacora/) — leerlas antes de
  «arreglar» algo que en realidad es una limitación declarada.

## 10. El prototipo AREN.IA: composición de APU a mano (sprint P0–P5)

El sprint del prototipo añadió la pantalla que compone y edita una partida a mano (UC‑10 y UC‑11
de la [ERS](ERS.md), RF‑33 a RF‑35). El diseño y su porqué están en la
[spec](superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md); la vista lógica de la
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
`ALTER TABLE … ADD COLUMN` aditivo o volver a sembrar con `--reiniciar`). **Regla:** toda sesión que
añada o cambie una columna de `core/models/entidades.py` declara en su plan, antes de escribir el
código, qué les pasa a las bases que ya existen en disco.
