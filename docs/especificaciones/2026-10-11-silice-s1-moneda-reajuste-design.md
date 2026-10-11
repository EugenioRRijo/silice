# Sílice S1 (0.6.0): moneda por proyecto, base de precios por empresa, datos del BCV y reajuste

| Campo | Valor |
|---|---|
| Estado | **propuesta**, pendiente de la aprobación de Eugenio y de la revisión por los cuatro encargos (requisitos, arquitectura, pruebas y calidad, verificador de hechos). Los tres expedientes de `core/` (§6) necesitan además el visto bueno del tutor |
| Versión que entrega | **0.6.0** (spec maestro §5); condición: 0.5.0 fusionada (sprint SF, PR #22–#29) |
| Fecha | 2026‑10‑11 |
| Rama del spec | `inc/silice` (worktree `.worktrees/silice`). Construcción en `inc/silice-s1-nucleo`, `inc/silice-s1-bcv` (adaptador) e `inc/silice-s1-ui` (§10) |
| Se apoya en | [spec maestro](2026-10-11-silice-1.0.0-design.md) (S‑D1…S‑D7, §3, §5), [horizonte](2026-10-08-horizonte-reorientacion-design.md) (H‑D1, H‑D3, H‑D8, §4), [antecedentes](../tesis/antecedentes-reorientacion-2026-10-08.md) §4 y §6, [spec SF](2026-10-04-sprint-final-prototipo-design.md) (SF‑E1, SF‑E4, SF‑E6, SF‑E7) |
| Documentos que enmienda | [ERS](../ERS.md), [modelo de datos](../modelo_datos.md) §2.5 nueva, [arquitectura](../arquitectura.md), [plan de pruebas](../plan_pruebas.md), [NORMAS.md](../../NORMAS.md) §6 (carpetas y conteo de entidades) |
| Naturaleza de los datos | [NORMAS.md §1](../../NORMAS.md): casos construidos; precios MaPreX de julio de 2026. Los índices de las memorias de cálculo son **ficticios y declarados**; los archivos del BCV son reales y se versionan con su fuente y su huella |

**Todo dato normativo de este spec está «a cotejar con la Gaceta Oficial».** La Ley de Contrataciones
Públicas se leyó en una **transcripción no oficial** (antecedentes §4); la fórmula escalatoria concreta es un
**INDICIO** de un documento de Scribd sin autor identificado. El sistema los implementa como **supuestos
declarados**, parametrizados y visibles, para que verificarlos cambie un parámetro o una función pura, no la
arquitectura.

---

## 1. Qué se quiere

1. **Moneda elegida por proyecto** (H‑D1): Bs o USD. Cada precio guarda su moneda original, su fecha y la
   tasa con que se convirtió (con su fecha y su fuente). Cambiar la moneda de un proyecto queda registrado y
   produce una versión nueva convertida. La **erosión** de un precio se muestra en las dos monedas.
2. **Base de precios por empresa** (H‑D8): cada empresa guarda sus precios con fecha, moneda y fuente. El
   auditor los compara con el mercado (MaPreX: «fuera de rango», regla **R11**) y con el tiempo («vencido»,
   con la erosión en Bs, regla **R12**).
3. **Datos del BCV desde archivos ya descargados**: la tasa diaria (.xls trimestral, una hoja por día
   hábil), el INPC mensual y el índice de precios de insumos de la construcción, con validación de formato,
   fuente y fecha, **sin conexión**.
4. **Reajuste** por fórmula escalatoria con índices y por comprobación directa (UC‑02), **lado a lado**
   (H‑D3), respetando el art. 134 según la transcripción: precios fijos el primer año, solo se ajusta lo
   ejecutado en el período, y estructura de costos, mecanismo, periodicidad e índices declarados.

**Criterio de éxito de la 0.6.0** (horizonte R1): un proyecto en Bs y otro en USD con su reajuste comparado
(escalatoria frente a comprobación directa) en las dos monedas; una empresa con su lista propia y sus precios
vencidos o fuera de rango marcados con el dinero que representan.

### 1.1 Lo que se encontró en el código (2026‑10‑11, rama `inc/silice`)

- `Presupuesto` (contrato) ya tiene `moneda: str`; la única moneda usada en el repositorio es `"USD"`
  (`core/budget/presupuesto.py:47`, `MONEDA_POR_DEFECTO`). `models.Proyecto` **no** guarda moneda.
- `ParametrosCosto.bono_alimentacion` es un **monto en la moneda del presupuesto** (`core/contracts/apu.py`):
  convertir una versión exige convertirlo; FCAS, administración y utilidad son fracciones y no se convierten.
- SF‑E7 ya guarda la tasa y su fecha **por lista** (`ListaPreciosOrigen`) y la referencia por precio
  (`ReferenciaPrecio`); no hay fecha ni moneda original **por precio**, ni fuente de la tasa.
- `Catalogo.lista_vigente` elige la lista global de mayor vigencia **sin mirar la moneda**: una lista de
  empresa cargada como global secuestraría la valoración de todos los proyectos.
- Ningún camino del núcleo, salvo la importación de UC‑05 (`core/budget/importacion.py:226`), impide valorar
  una versión en una moneda con una lista de otra.
- UC‑02 (`core/budget/actualizacion.py`) revalora una versión con una lista nueva y devuelve un `Comparativo`
  por partida (PU anterior y nuevo): es la base de la comprobación directa.
- `exportar_hoja(..., hojas_extra=...)` (SF‑E4) admite tablas genéricas: el reajuste y la erosión se exportan
  sin tocar el Excel del núcleo. `exportar_excel` conserva sus cuatro hojas.
- **Corrección al spec maestro §3:** `openpyxl` (ya instalado) **no lee** el formato `.xls` de Excel 97‑2003,
  que es el de los archivos de la tasa y del INPC (antecedentes §6). Hace falta un lector de `.xls`; se
  propone `xlrd` (≥ 2.0, que solo lee `.xls`) en un extra `bcv`, con su licencia confirmada en S1‑0
  (ruling S1‑R12).
- **Conflicto de numeración:** la ERS (notas de U0.1 y SF0) reserva **RF‑64** como el siguiente número libre
  para UC‑09 (asistente). El spec maestro asigna RF‑64 a RF‑71 a S1. Esta enmienda corre la nota de UC‑09 a
  «el siguiente al más alto asignado tras los specs de Sílice» (pregunta abierta 1).

### 1.2 Qué está verificado y qué no

| Dato | Estado | Fuente | Uso aquí |
|---|---|---|---|
| Arts. 133 y 134 de la LCP (Decreto 1.399, G.O. 6.154 Ext., 19‑11‑2014) | VERIFICADO en transcripción no oficial; **a cotejar con la Gaceta** | antecedentes §4 | restricciones de §8 |
| Reglamento (Decreto 6.708, G.O. 39.181, 2009), artículos de variaciones | **NO verificados** | antecedentes §4 | no se usan |
| Fórmula `Vpm = Vo(Km−1)(1−R)` | **INDICIO** (Scribd «ESCALATORIAS», autor no identificado) | antecedentes §4 | supuesto declarado S1‑R8 |
| Significado de `R` y composición de `Km` | **NO verificados**; interpretación de este spec | — | supuesto declarado S1‑R8 |
| Opinión de la Comisión de Contrataciones sobre variaciones > 10 % | **INDICIO** (número de artículo sin confirmar) | antecedentes §4 | solo una nota en el estudio (UC‑18 6a) |
| Tasa: .xls trimestral, una hoja por día hábil (3T‑2026: 64 hojas, 01‑07 a 30‑09), compra y venta, fecha valor del día hábil siguiente | VERIFICADO (2026‑10‑08) | antecedentes §6 | adaptador BCV |
| Ejemplo de tasa: USD 858,02 / 860,18 Bs, fecha valor 01‑10‑2026 | VERIFICADO | antecedentes §6 | memoria de erosión |
| Qué letra del nombre (`2_1_2{a,b,c,d}{AA}_smc.xls`) corresponde a qué trimestre; posición de las celdas en cada hoja | **NO verificado** | — | se fija en S1‑0 con los archivos reales |
| INPC: .xls con series mensuales (p. ej. `4_5_1.xls`), 2026 provisional «(*)», fuente BCV‑INE | VERIFICADO | antecedentes §6 | adaptador BCV |
| Índice de precios de insumos de la construcción (productor y mayorista; mensual, trimestral, anual) | enlaces VERIFICADOS; **contenido NO abierto** | antecedentes §6 | formato se fija en S1‑0; respaldo por CSV canónico |
| Tasa MaPreX 633,3644 Bs/USD al 01/07/2026 | VERIFICADO | [README MaPreX](../../data/precios/maprex_2026-07/README.md) | memoria de erosión, R11 |

---

## 2. Alcance

**Incluye:** moneda del proyecto y su cambio registrado; origen por precio; conversión con tasa fechada;
erosión en dos monedas; listas de empresa; R11 y R12; importación de archivos del BCV; cláusula de reajuste;
escalatoria y comprobación directa lado a lado; pantallas y exportación a Excel por `hojas_extra`.

**No incluye:**

- Descargar del BCV: el sistema **no se conecta**; el usuario trae los archivos (RNF‑14).
- Valuaciones por cantidades ejecutadas (S2, 0.7.0). S1 recibe lo ejecutado de cada período como dato
  declarado con su fuente en el estudio de reajuste; S2 lo alimentará desde sus valuaciones (pregunta 6).
- Variaciones de obra (aumentos, disminuciones, obras extra): S2.
- Monedas distintas de Bs y USD.
- Rutas nuevas de la API (la API se amplía en S3 y S5).
- Cuentas de usuario: el responsable sigue siendo un nombre declarado hasta S3 (S‑D4).
- Una entidad «empresa» con claves y firma: S3. S1 nombra la empresa con un texto (pregunta 5).
- Decidir si hubo ruptura del equilibrio económico: el sistema registra la excepción que el usuario declara,
  no la juzga.

---

## 3. Requisitos (enmienda a la ERS, IEEE 830)

**Numeración asignada:** UC‑17 y UC‑18; RF‑64 a RF‑71; RNF‑14; expedientes SL‑E1 a SL‑E3; reglas R11 y R12.
**Se usan todos; no queda ningún número vacante.** Conteos de la ERS tras S1: **70 RF** (62 + 8; RF‑32 sigue
vacante), **diecisiete UC** y catorce RNF. La meta `meta_s1.py` los comprueba.

### 3.1 Casos de uso

#### UC‑17 — Mantener la base de precios de la empresa y los índices del BCV

- **Actor principal:** administrador del catálogo. **Secundario:** proyectista.
- **Precondiciones:** catálogo con insumos; archivos del BCV ya descargados en el equipo; lista de referencia
  MaPreX cargada (S1‑0, tarea 0.4).
- **Flujo principal**
  1. El administrador elige uno o varios archivos del BCV y declara la **fuente** (dirección de la página del
     BCV de donde los bajó) y la **fecha de descarga**.
  2. El sistema lee cada archivo **sin conexión**, valida formato, fuente y fechas (§7.2) y muestra el
     informe de importación sin escribir nada: series, fechas, filas leídas, rechazadas y provisionales.
  3. El administrador confirma; el sistema guarda los valores con la huella SHA‑256 del archivo.
  4. El administrador carga la lista de su empresa (CSV o XLSX: las cuatro columnas de UC‑02 y, opcionales,
     `fecha`, `fuente` y `referencia` por fila), declara empresa, moneda, fecha y fuente de la lista y la
     **lista base** que completa los insumos que la empresa no cotiza.
  5. El sistema crea la lista de empresa (§6.2) y audita sus precios con R11 y R12 a la fecha de evaluación
     declarada; muestra cada hallazgo con el dinero que representa.
- **Flujos alternativos**
  - *2a. Formato no reconocido:* se rechaza el archivo con un mensaje que nombra la etiqueta o la hoja que
    faltó, sin *traceback* y sin escribir nada.
  - *2b. Fecha fuera del período del archivo, repetida o posterior a la fecha de descarga:* la fila se
    rechaza y se reporta; las demás se procesan.
  - *2c. Archivo ya importado (misma huella):* se informa y no se escribe nada.
  - *2d. Valor revisado (un INPC provisional que cambió):* se guarda como una importación nueva; los estudios
    de reajuste anteriores siguen citando la importación que usaron.
  - *2e. Nombre de archivo fuera de los patrones conocidos* (el BCV usa nombres irregulares algunos años): se
    importa si el formato valida, con ADVERTENCIA en el informe.
  - *2f. Índice de insumos de la construcción con formato aún no documentado:* se carga la serie desde el CSV
    canónico de §7.3, con su fuente declarada.
  - *4a. Insumos desconocidos o unidad no equivalente:* como UC‑02 2a y 2b.
  - *4b. Moneda distinta de Bs o USD:* se rechaza la lista.
  - *5a. Insumo sin referencia MaPreX:* R11 no lo contrasta y lo cuenta en su hallazgo INFO «no contrastable».
- **Postcondiciones:** series con su importación y huella; lista de empresa inmutable, fuera de
  `lista_vigente`, con origen por precio; informe de R11 y R12 a la fecha de evaluación.

#### UC‑18 — Reajustar los precios de la obra ejecutada

- **Actor principal:** proyectista (quien arma). **Secundario:** gerente / administrador que revisa.
- **Precondiciones:** versión del contrato guardada; cláusula de reajuste declarada (§8.1); índices
  importados (UC‑17); para la comprobación directa, una versión revalorada por UC‑02 por período.
- **Flujo principal**
  1. El usuario abre la versión del contrato y su cláusula de reajuste.
  2. Declara, por período, las cantidades ejecutadas por partida con su **fuente** (número y fecha del acta o
     de la valuación).
  3. El sistema calcula la **escalatoria** de cada período con las restricciones de §8.2.
  4. El usuario elige, por período, la versión revalorada por UC‑02 que sirve de **comprobación directa**.
  5. El sistema muestra, por período y en total, los dos montos lado a lado, su diferencia, y cada monto en
     las dos monedas con la tasa de la fecha de cierre del período.
  6. El usuario guarda el estudio (fuente y responsable obligatorios) y lo exporta a Excel.
- **Flujos alternativos**
  - *3a. Período dentro del primer año (contrato de más de un año):* reajuste cero, con la nota «precios
    fijos el primer año (art. 134, a cotejar)».
  - *3b. Período que cruza el aniversario:* se rechaza y se pide partirlo; el sistema no prorratea.
  - *3c. Falta el índice de un mes:* ese período no se calcula y se declara; no se extrapola.
  - *3d. Índice provisional:* se calcula y se marca «provisional».
  - *3e. Excepción del primer año por ruptura del equilibrio económico:* el usuario la declara con
    justificación y fuente; el período se calcula y se marca «excepción declarada».
  - *3f. Lo ejecutado acumulado supera lo presupuestado de una partida:* se rechaza; las variaciones de obra
    son de S2.
  - *4a. Sin versión revalorada para el período:* la comprobación directa queda «no disponible» y se muestra
    solo la escalatoria.
  - *5a. Proyecto en USD con índices en Bs:* ADVERTENCIA visible (§8.4).
  - *6a. La suma de reajustes supera el 10 % del monto original:* nota informativa sobre la opinión de la
    Comisión de Contrataciones, marcada INDICIO (artículo sin confirmar).
- **Postcondiciones:** estudio guardado con sus entradas, la importación de cada índice usado, sus
  resultados y su registro; la versión del contrato no cambia.

#### UC existentes que se enmiendan

| UC | Enmienda |
|---|---|
| UC‑01 | Paso 1: al crear el proyecto (RF‑63) se **elige** la moneda (Bs o USD), sin valor por defecto en la interfaz. La API y `elaborar` conservan `"USD"` por defecto (líneas base intactas) |
| UC‑02 | Sin cambios de flujo. Su versión revalorada es la entrada de la comprobación directa (UC‑18). Revalorar con una lista de otra moneda se rechaza (SL‑E1) |
| UC‑15 | La pestaña Parámetros muestra y cambia la moneda (RF‑64); la pestaña Precios agrega moneda original, fecha del precio, tasa con fecha y fuente, erosión en dos monedas y el Estado de R11 y R12 |

### 3.2 Requisitos funcionales

Prioridad: E = esencial, D = deseable. Fases: §10.

| RF | Requisito | UC | Pri. | Fase | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑64 | La moneda del proyecto (Bs o USD) se elige al crearlo; cambiarla crea una versión nueva **convertida** (motivo `conversion`), con la tasa fechada y su fuente, el bono de alimentación convertido, el plan conservado y un `RegistroCambio` (objeto `moneda`); la versión anterior no cambia | UC‑01, UC‑15 | E | S1‑1 | total convertido = total ÷ tasa (de Bs a USD) o × tasa (de USD a Bs) a ± 0,01 en la presentación, para la clínica y TI‑001; la versión de origen recarga idéntica; sin tasa, sin fecha o sin fuente se rechaza |
| RF‑65 | Cada precio tiene moneda original, precio original, fecha, y, si se convirtió, tasa con su fecha y su fuente (§5.1); una versión solo se valora con una lista de **su** moneda | UC‑15, UC‑17 | E | S1‑1 | la pestaña Precios muestra los seis datos por insumo; guardar una versión en Bs con una lista en USD se rechaza; las bases anteriores muestran el origen heredado de la lista |
| RF‑66 | La erosión de cada precio (§5.3) se muestra en Bs y en USD a una fecha de evaluación declarada, por insumo y por versión | UC‑15, UC‑17 | E | S1‑1 | la memoria `s1_conversion.md` (§9.1) se reproduce con 28 dígitos y a ± 0,01 en la presentación |
| RF‑67 | La lista de una empresa es una lista de alcance `empresa`: copia de una lista base declarada con los precios propios (fecha, moneda y fuente por precio), inmutable, fuera de `lista_vigente`, usable para valorar una versión | UC‑17 | E | S1‑3 | `lista_vigente` no la devuelve; un precio propio prevalece sobre el de la base; cada precio dice si es propio o heredado; la lista de una empresa no cambia la valoración de otra ni la de ningún proyecto que no la referencie |
| RF‑68 | Reglas **R11** (precio fuera de rango frente a MaPreX) y **R12** (precio vencido o sin trazabilidad de tasa) con la severidad de §6.3, el impacto en dinero y la fecha de evaluación en cada hallazgo | UC‑17, UC‑15 | E | S1‑3 | conjunto **exacto** de hallazgos de la memoria `s1_precios_empresa.md` (regla, severidad, insumo, impacto a ± 0,01) con sus fronteras |
| RF‑69 | Importación sin conexión de la tasa (.xls trimestral), el INPC (.xls mensual) y el índice de insumos de la construcción, con validación de formato, fuente y fecha, informe previo, huella SHA‑256 e importaciones idempotentes | UC‑17 | E | S1‑2 | el archivo real versionado de un trimestre da sus N hojas como N valores de compra y de venta del USD (N fijado en S1‑0 al abrirlo); cada caso negativo de la fila RF‑69 de §9.2 se rechaza con su mensaje; reimportar la misma huella no escribe nada |
| RF‑70 | Reajuste por **fórmula escalatoria** (§8.3) con las restricciones del art. 134 de §8.2 («a cotejar») y la cláusula declarada (§8.1) | UC‑18 | E | S1‑4 | la memoria `s1_reajuste.md` da 15 300,00 Bs en el período del ejemplo; cada frontera de §9.2 da su salida declarada |
| RF‑71 | **Comprobación directa** (con la versión revalorada por UC‑02) lado a lado con la escalatoria, por período y total, en las dos monedas; el estudio se guarda con fuente y responsable y se exporta por `hojas_extra` | UC‑18 | E | S1‑4 | la memoria da 16 000,00 Bs y una diferencia de −700,00 Bs; 18,00 y 18,82 USD a la tasa del ejemplo; el estudio recargado es idéntico al guardado |

### 3.3 Requisito no funcional

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑14 | Fiabilidad | **Reproducible y sin conexión:** importar, convertir, auditar con R11/R12 y reajustar no hacen ninguna llamada de red; el mismo estudio de reajuste, con las mismas importaciones citadas, da el mismo resultado aunque después se importe una revisión de los índices | pruebas con `socket.socket.connect` bloqueado (cualquier intento falla la prueba); recálculo del estudio de la memoria tras importar una revisión: diferencia 0 exacta |

---

## 4. Arquitectura

### 4.1 Principio que se conserva

NORMAS §2: lo genérico de cualquier presupuesto (moneda, tasa, origen de un precio, lista de empresa,
auditoría de precios, reajuste) va en `core/` con expediente; **leer un formato de archivo de un tercero** (el
BCV) va en un adaptador. Ningún expediente nombra una especialidad, y el reajuste de la ley vale para obras y
servicios de cualquier dominio. **Ningún contrato de `core/contracts/` cambia**: el adaptador entrega sus
propios tipos (biblioteca estándar) y la capa `ui/` los traduce a las funciones del núcleo, como hace
`ui.hoja` con `adapters.espacio`. Si al construir pareciera necesario un tipo nuevo en `core/contracts/`, se
**detiene** el trabajo y se registra (NORMAS §9).

### 4.2 Vista lógica

| Paquete | Qué contiene | Importa | Toca `core/` |
|---|---|---|---|
| `core/models/entidades.py` | tablas aditivas de §5.2; `MOTIVOS_VERSION` + `conversion`; alcance `empresa` | — | **SL‑E1, SL‑E2, SL‑E3** |
| `core/catalog/indices.py` (nuevo) | `DefinicionSerie`, `Observacion`, `registrar_importacion`, `valor_en`, `tasa_aplicable` | `core.models` | **SL‑E1** |
| `core/catalog/moneda.py` (nuevo) | `MONEDAS = ("Bs", "USD")`, `convertir` (pura), `erosion` (pura), `convertir_lista` | `core.catalog.indices` | **SL‑E1** |
| `core/budget/moneda.py` (nuevo) | `moneda_del_proyecto`, `convertir_version` | `core.budget.*` | **SL‑E1** |
| `core/budget/persistencia.py` | `guardar_presupuesto` rechaza lista y versión de monedas distintas | — | **SL‑E1** |
| `core/budget/edicion.py` | `OBJETOS` + `moneda` | — | **SL‑E1** |
| `core/catalog/empresa.py` (nuevo), `precios.py`, `repositorio.py` | `crear_lista_de_empresa`; lector con columnas opcionales `fecha`, `fuente`, `referencia`; `lista_vigente` excluye `empresa` | — | **SL‑E2** |
| `core/verification/precios.py` (nuevo) | `InstantaneaPrecios`, `PrecioFueraDeRango` (R11), `PrecioVencido` (R12); **no** entran en `REGLAS` | `core.contracts`, `core.costing` | **SL‑E2** |
| `core/catalog/origen.py` | `instantanea_precios(session, version, referencia, fecha_evaluacion)` y origen por precio en `OrigenPrecio` | — | **SL‑E2** |
| `core/budget/reajuste.py` (nuevo) | `coeficiente`, `reajuste_escalatorio`, `reajuste_por_comprobacion`, `comparar_reajustes` (puras); `guardar_estudio`, `cargar_estudio` | `core.catalog.indices` | **SL‑E3** |
| `adapters/bcv/` (nuevo) | `libro.py` (abre `.xls` con `xlrd` y `.xlsx` con `openpyxl` y devuelve una **cuadrícula neutra** por hoja), `tasa.py`, `inpc.py`, `insumos_construccion.py` (interpretan la cuadrícula), `informe.py`; tipos propios `SerieLeida`, `ValorLeido`, `InformeImportacion` | biblioteca estándar, `xlrd`, `openpyxl` | no |
| `ui/indices.py` (nuevo, sin Streamlit) | adaptador → informe previo → `core.catalog.indices` | `adapters.bcv`, `core` | no |
| `ui/reajuste.py` (nuevo, sin Streamlit) | arma el estudio, la tabla lado a lado y sus `TablaExportable` | `core` | no |
| `ui/hoja.py` | moneda en Parámetros; columnas de origen y erosión en Precios; R11 y R12 como reglas extra | — | no |
| `ui/paginas/indices.py`, `precios_empresa.py`, `reajuste.py` (nuevas) | pantallas de UC‑17 y UC‑18 | `ui.*` | no |

`adapters/bcv` **no** implementa `AdaptadorDominio`: no es un dominio ni produce `ItemComputo`. Es una fuente
de series, como `adapters/espacio` es una fuente de cantidades con interfaz propia.

### 4.3 Vista de procesos

```
importar (UC-17)                          reajustar (UC-18)
archivo .xls ──> adapters.bcv.libro       versión del contrato + cláusula (§8.1)
  (cuadrícula neutra, sin red)              + ejecutado por período (con fuente)
  ──> tasa / inpc / insumos: valida       ──> core.budget.reajuste.reajuste_escalatorio
  ──> InformeImportacion (sin escribir)        (índices de core.catalog.indices, importación citada)
  ──> ui.indices: confirma                ──> versión revalorada por UC-02 (comprobación)
  ──> core.catalog.indices.registrar_     ──> reajuste_por_comprobacion ──> comparar_reajustes
      importacion (huella, fuente)        ──> tasa_aplicable(fecha de cierre) ──> dos monedas
                                          ──> guardar_estudio (fuente, responsable)
```

**Auditoría de precios.** R11 y R12 se construyen con la instantánea de precios de la versión (lista, origen
por precio, referencia MaPreX, tasas) y una **fecha de evaluación explícita**, igual que R8–R10 con la
instantánea del espacio (DA‑SF‑8). Entran por `reglas=` (SF‑E1); sus hallazgos guardados se conservan al
recargar. Al abrir una versión, `ui.hoja` las vuelve a evaluar a la fecha de hoy y esa evaluación
**reemplaza** la guardada (no se suman), como R8–R10 (spec SF §8.4); el informe emitido conserva los
hallazgos a su fecha de emisión.

### 4.4 Vista de desarrollo y física

- Dependencias: `xlrd>=2.0` en un extra nuevo `bcv` (S1‑R12). `openpyxl` ya está. Ninguna dependencia de red.
- `tests/unit/test_arquitectura.py`: `TERCEROS_POR_ADAPTADOR["bcv"] = {"xlrd", "openpyxl"}`;
  `PROHIBIDOS_EN_UI` agrega `ui/indices.py` y `ui/reajuste.py` (`streamlit`, `pandas`, `ui.caso`).
- La CI instala el extra `bcv` en Linux y Windows: ninguna prueba se omite por falta de `xlrd`.
- Archivos del BCV de prueba en `tests/fixtures/bcv/` con un `FUENTE.md` (dirección, fecha de descarga,
  huella), límite de 20 MB y guardado seguro de subidas (A‑1, RNF‑12).

---

## 5. Moneda, origen por precio, conversión y erosión (SL‑E1)

### 5.1 Origen de un precio

| Dato | Dónde vive | Si falta |
|---|---|---|
| moneda original y precio original | `PrecioOrigen` (§5.2) | la moneda de la lista y el precio de la lista |
| fecha del precio | `PrecioOrigen.fecha_precio` | `ListaPrecios.fecha_vigencia` |
| tasa, fecha de la tasa y fuente de la tasa | `PrecioOrigen` (precio convertido) | `ListaPreciosOrigen.tasa` y `fecha_tasa` (SF‑E7), sin fuente: R12 da ADVERTENCIA (las listas de SF‑E7 no guardan la fuente de su tasa) |
| fuente del precio | `PrecioOrigen.fuente` | `ListaPrecios.origen` |

**Una sola regla de precedencia** (DRY): la fila por precio prevalece; la de la lista es el respaldo de las
listas anteriores a S1 y de las que declaran una sola tasa para todos (MaPreX). Así abren las bases
existentes (clínica, TI‑001, importadas): no tienen filas nuevas y todo cae a la lista.

### 5.2 Tablas aditivas (ruling SF3‑E0: tablas, no columnas)

| Tabla | Columnas | Expediente |
|---|---|---|
| `serie_indice` | `id`, `codigo` (único), `nombre`, `organismo`, `unidad`, `periodicidad` (diaria, mensual, trimestral, anual), `base` (texto tal como lo trae el archivo) | SL‑E1 |
| `importacion_indice` | `id`, `serie_id`, `archivo`, `huella` (SHA‑256), `fuente` (dirección declarada), `fecha_descarga`, `fecha_importacion`, `responsable`, `filas_leidas`, `filas_rechazadas`, `informe` (texto) | SL‑E1 |
| `valor_indice` | `id`, `serie_id`, `importacion_id`, `fecha` (fecha valor o primer día del período), `valor`, `provisional` | SL‑E1; única por (`serie_id`, `fecha`, `importacion_id`) |
| `moneda_proyecto` | `id`, `proyecto_id`, `moneda`, `desde` (fecha y hora), `version_id`, `responsable`, `fuente` | SL‑E1; historial: la vigente es la última; sin filas, la de su versión vigente |
| `precio_origen` | `precio_id` (PK → `precio_insumo`), `moneda_original`, `precio_original`, `fecha_precio`, `tasa`, `fecha_tasa`, `fuente_tasa` (id de importación o texto), `fuente` | SL‑E1 |
| `lista_empresa` | `lista_id` (PK), `empresa`, `lista_base_id`, `lista_referencia_id` (MaPreX), `plazo_vigencia_dias`, `rango_inferior`, `rango_superior` | SL‑E2 |
| `clausula_reajuste`, `componente_clausula` | §8.1 | SL‑E3 |
| `estudio_reajuste`, `periodo_reajuste`, `ejecutado_periodo` | §8.5 | SL‑E3 |

**Coordinación con S5 (Alembic).** La 0.6.0 sale antes que S5: sus tablas se crean con `crear_esquema`
(aditivas, sin `ALTER TABLE`). S5 incluye estas tablas en la revisión base de Alembic y marca (`stamp`) las
bases creadas por 0.5.0–0.9.0. Si S5 se adelanta, cada tabla de esta sección pasa a ser una revisión de
Alembic y la prueba de bases anteriores se mantiene.

### 5.3 Conversión y erosión (funciones puras)

Tasa `T` en Bs por USD. Toda división se hace con `decimal.localcontext(prec=28, rounding=ROUND_HALF_EVEN)`
fijado dentro de la función (el resultado no depende del contexto global); se redondea solo al presentar.

- `convertir(monto, de, a, tasa)`: Bs→USD = `monto / T`; USD→Bs = `monto × T`; misma moneda = `monto`.
- **Tasa aplicable** a una fecha `d` (`tasa_aplicable`): la de mayor fecha valor ≤ `d` del lado declarado
  (S1‑R1); si la más cercana tiene más de **7 días naturales** de antigüedad, se rechaza (S1‑R2). Nunca se
  extrapola.
- **Erosión** de un precio `P` de fecha `d0` (tasa `T0`) a la fecha de evaluación `d1` (tasa `T1`):

| Moneda original | Erosión en USD | Erosión en Bs |
|---|---|---|
| Bs | `P/T0 − P/T1` (valor en USD que perdió) | `P·T1/T0 − P` (Bs que faltan para reponerlo) |
| USD | 0 (no hay índice de inflación en USD en el alcance; se declara) | 0 |

  Con el índice de insumos de la construcción o el INPC cargados, se muestra además la **erosión por índice**
  `P·(I1/I0 − 1)` en Bs, con la serie y la importación citadas. Es una columna aparte, no se suma.

**Conversión de una versión** (`convertir_version`): crea una lista derivada de alcance `proyecto` (SF‑E7) con
cada precio convertido y su `PrecioOrigen`; toma las líneas de la instantánea (SF‑E6) con esa lista; convierte
el precio de las líneas sin insumo (precio manual) con la misma tasa; convierte `bono_alimentacion`; conserva
el plan (fracciones); elabora, guarda con `version_origen` (motivo `conversion`), agrega una fila a
`moneda_proyecto` y un `RegistroCambio` (objeto `moneda`, valores anterior y nuevo, fuente = importación de la
tasa). Como el PU es homogéneo de grado 1 en los montos (precios y bono; las fracciones no cambian), el total
convertido debe ser el total ÷ `T`: es el **oráculo independiente** de RF‑64.

---

## 6. Base de precios por empresa y auditoría de precios (SL‑E2)

### 6.1 Lista de empresa

`crear_lista_de_empresa(session, empresa, base, precios_propios, *, moneda, fecha, fuente, referencia)`
(firma exacta en S1‑3): copia de `base` (en la moneda de la lista; si `base` está en otra moneda se convierte
con `convertir_lista` y su `PrecioOrigen`) con los precios propios encima, cada uno con su `PrecioOrigen`
(fecha, fuente, moneda original). Registra `ListaPreciosOrigen.alcance = "empresa"` y una fila de
`lista_empresa`. `lista_vigente` excluye `empresa` como ya excluye `proyecto`. Una versión la usa
referenciándola explícitamente, como una lista de proyecto (DA‑SF‑9). Una cotización sobre una versión
valorada con lista de empresa toma esa lista como base (SF‑E7 sin cambios).

### 6.2 Lista de referencia MaPreX en Bs

Para R11 se carga en S1‑0 una lista **MaPreX julio 2026 en Bs** desde la columna `precio_bs` de los cuatro
`referencia_*.csv` (111 filas, verificadas a mano en M0.2), con su Ref (`ReferenciaPrecio`), fecha (09/07/2026;
mano de obra 01/07/2026) y tasa 633,3644 Bs/USD al 01/07/2026. Usar `precio_bs` evita reconstruir bolívares
desde `precio_usd`, que está redondeado a 4 decimales. **Límite declarado:** solo esos 111 insumos son
contrastables; los demás van al INFO de R11.

### 6.3 Reglas R11 y R12 (en `core/verification/precios.py`; implementan `ReglaVerificacion`)

| Regla | Comprueba | Severidad | Impacto |
|---|---|---|---|
| **R11** `PrecioFueraDeRango` | precio de la lista frente a su referencia MaPreX, ambos llevados a USD con la tasa que declara cada precio (§5.1) o, si no la declara, la aplicable a **su propia fecha**: desvío `p/p_ref − 1` fuera de [`rango_inferior`, `rango_superior`] (por defecto −20 % / +30 %, S1‑R5) | ADVERTENCIA por insumo fuera de rango; **un** INFO con el número de insumos no contrastables (sin referencia o sin tasa a su fecha) | diferencia del total de la versión si el insumo valiera su referencia, calculada con `calcular_apu` sobre las composiciones de la versión (no con una fórmula aparte) |
| **R12** `PrecioVencido` | antigüedad del precio a la fecha de evaluación mayor que `plazo_vigencia_dias` (por defecto 30, S1‑R6); precio convertido cuya tasa no tiene fecha o no tiene fuente | ADVERTENCIA si vencido o si la tasa no tiene fuente; **ERROR** si la tasa de un precio convertido no tiene fecha (el número no es trazable ni reproducible) | erosión en Bs del precio (§5.3) llevada al total de la versión con `calcular_apu` |

En la frontera, el desvío exactamente igual al límite **pasa** y la antigüedad exactamente igual al plazo
**pasa**. Cada hallazgo cita en `origen_ids` los códigos de las partidas que usan el insumo (precedente de
`ATIPICO`, expediente C6.5) y nombra el insumo, la referencia, las dos fechas y la fecha de evaluación en la
descripción. R11 y R12 **no** entran en `REGLAS`: la línea base sigue dando 7 de 7 y las dos huellas de
RNF‑04 no se mueven (S1‑R7). La correspondencia entre `origen_ids` y las filas de la pestaña Precios se
verifica en S1‑0 contra la columna Estado de `ui.hoja`.

---

## 7. Importación de archivos del BCV (adaptador `adapters/bcv`)

### 7.1 Principio

El adaptador **no adivina**: lee lo que el formato documentado dice y reporta lo demás. El formato exacto de
cada archivo (nombre de las hojas, etiquetas, posición de la fecha valor y de la compra y la venta del USD,
encabezados del INPC y del índice de la construcción, marca «(*)») **no se fija en este spec**: se documenta
en S1‑0 en `docs/fuentes/bcv_formatos.md` abriendo los archivos reales, **antes** del código del adaptador.
El lector se parte en dos: `libro.py` convierte el archivo en una cuadrícula neutra (`tuple` de filas de
`str | Decimal | date | None` por hoja) y los intérpretes trabajan sobre esa cuadrícula. Así las pruebas
negativas manipulan cuadrículas sin escribir `.xls`.

### 7.2 Validaciones

| Qué | Regla | Si falla |
|---|---|---|
| Archivo | extensión `.xls` o `.xlsx` que coincide con su contenido; ≤ 20 MB; abre sin error | rechazo con mensaje (RNF‑12) |
| Formato | las etiquetas documentadas en `bcv_formatos.md` están en su lugar | rechazo, nombrando la etiqueta faltante (UC‑17 2a) |
| Fuente | dirección declarada en el dominio `bcv.org.ve`; nombre del archivo contra los patrones conocidos (`2_1_2?{AA}_smc.xls` para la tasa; los del INPC y de la construcción, en S1‑0) | dominio ajeno: rechazo; nombre desconocido: ADVERTENCIA (2e) |
| Fecha | cada hoja o fila con fecha legible; dentro del trimestre o del rango del archivo (la letra del trimestre se verifica en S1‑0); sin repetidas; no posterior a la fecha de descarga; meses del INPC consecutivos | fila rechazada y reportada (2b) |
| Valor | `Decimal` > 0 leído del texto o del número de la celda sin pasar por `float` cuando el formato lo permita (si `xlrd` entrega `float`, se convierte con `Decimal(repr(x))` y se declara en el informe) | fila rechazada |
| Coherencia | compra ≤ venta | ADVERTENCIA (no se rechaza: es una expectativa, no una regla del BCV) |
| Provisional | la marca de provisional del archivo se guarda por valor | — |
| Repetición | misma huella ya importada | nada se escribe (2c) |

Solo se importa el **USD** de la tasa (H‑D1); las demás monedas del archivo van al informe como «no
importadas».

### 7.3 Respaldo por CSV canónico

Para el índice de la construcción mientras su formato no esté documentado (y para cualquier serie si el BCV
cambia el formato), la serie se carga desde un CSV `serie,fecha,valor,provisional,fuente` con las mismas
validaciones de fecha, valor y repetición. La fuente es obligatoria y queda en la importación. Es el plan B
del riesgo «el BCV cambia el formato» (spec maestro §8).

---

## 8. Reajuste (SL‑E3)

### 8.1 Cláusula de reajuste (lo que el art. 134 manda declarar, según la transcripción)

| Campo | Contenido | Art. 134 (transcripción, a cotejar) |
|---|---|---|
| `fecha_inicio`, `duracion_meses` | inicio del contrato y su duración; > 12 meses activa las restricciones de §8.2 | contratos de más de un año |
| `fecha_referencia_primer_anio` | fecha desde la que corre el primer año (por defecto `fecha_inicio`; **a cotejar**: firma, inicio o acta de inicio) | precios fijos el primer año |
| `periodicidad` | mensual, trimestral u otra declarada | num. 3, periodicidad |
| `mecanismo` | `escalatoria`, `comprobacion` o `ambos` (H‑D3: el sistema muestra los dos aunque el contrato elija uno) | num. 2, mecanismos de ajuste |
| `estructura` | `por_partida` (pesos de cada partida desde su `ResultadoAPU`: materiales, equipos y mano de obra sobre el costo directo) o `declarada` (pesos globales escritos en el contrato) | num. 1, estructura de costos por renglón o partida |
| `componente_clausula` | por componente: peso (si es declarada), **serie** con su organismo (p. ej. índice de insumos de la construcción, INPC) | num. 4, índices y órgano que los genera |
| `fecha_base_indices` | mes del índice base `I0` (obligatorio, sin valor por defecto) | — (S1‑R10) |
| `r` | fracción `R` de la fórmula, con su fuente (obligatoria; si el contrato no la tiene, el usuario escribe 0 y lo declara) | — (INDICIO, S1‑R8) |
| `fuente`, `responsable` | de dónde salen estos datos (contrato, número, fecha) | — |

Los pesos de cada estructura suman 1 exactamente (`Decimal`); si no, se rechaza.

### 8.2 Restricciones del art. 134 (según la transcripción; todas «a cotejar con la Gaceta»)

1. **Primer año fijo** (contrato > 12 meses): un período cuya fecha de cierre es anterior al aniversario de
   `fecha_referencia_primer_anio` tiene reajuste cero; uno que empieza en el aniversario o después se
   reajusta; uno que lo cruza se rechaza (UC‑18 3b). La excepción por ruptura del equilibrio económico se
   declara con justificación y fuente y queda marcada (3e).
2. **Solo lo ejecutado en el período:** el monto reajustable `Vo` de un período es Σ cantidad ejecutada en el
   período × PU del contrato; nunca el saldo por ejecutar ni lo ejecutado en otro período. Lo ejecutado
   acumulado no puede superar lo presupuestado (3f).
3. **Estructura, mecanismo, periodicidad e índices declarados:** sin cláusula completa no se calcula.
4. La escalatoria en **reconsideraciones** solo vale para obras y servicios (transcripción); el estudio lo
   recuerda como nota, no lo decide.

### 8.3 Fórmula escalatoria (supuesto declarado S1‑R8)

Forma tomada del INDICIO: `Vpm = Vo · (Km − 1) · (1 − R)`. Interpretación de **este spec** (no verificada):
`Vo` = valor de lo ejecutado en el período a precios del contrato; `Km` = coeficiente polinómico
`Σ pᵢ · Iᵢ,m / Iᵢ,0` (la ley de 2009 hablaba de «fórmulas polinómicas», antecedentes §4); `R` = fracción no
reajustable declarada en la cláusula. Con estructura `por_partida`, `Km` se calcula por partida y
`Vpm = Σⱼ Voⱼ · (Kⱼ,m − 1) · (1 − R)`. `Iᵢ,m` es el valor del índice del **mes en que cierra el período**
(S1‑R10) en la importación vigente al calcular, que el estudio cita. Las funciones son puras: reciben los
valores, no la sesión.

### 8.4 Comprobación directa y comparación

`reajuste_por_comprobacion` = Σⱼ q_ejecutadaⱼ,m · (PU_comprobadoⱼ − PU_contratoⱼ), con `PU_comprobado` de la
versión revalorada por UC‑02 que el usuario elige para el período (la lista de esa versión es la evidencia).
`R` no se aplica a la comprobación salvo que la cláusula lo diga (S1‑R14). `comparar_reajustes` da por período
y total: escalatoria, comprobación, diferencia y cada uno en la otra moneda con `tasa_aplicable(cierre del
período)`. El reajuste se calcula en la moneda en que está `Vo` (la del proyecto); si es USD y algún índice es
una serie en Bs, el estudio lleva una ADVERTENCIA: un índice de precios en bolívares aplicado a montos en
dólares cuenta dos veces la devaluación (S1‑R11).

### 8.5 Estudio guardado

`estudio_reajuste` (versión del contrato, cláusula, fecha de cálculo, fuente, responsable), `periodo_reajuste`
(desde, hasta, `Km`, escalatoria, comprobación, versión revalorada usada, importación de cada índice, marcas:
primer año, provisional, excepción) y `ejecutado_periodo` (partida, cantidad, fuente). Recargar un estudio lo
**recalcula** con las importaciones citadas y exige igualdad exacta con lo guardado (RNF‑14).

---

## 9. Pruebas (IEEE 829)

Pruebas antes que código con **rojo observado**: el commit de la prueba va antes que el de la implementación
en SL‑E1, SL‑E2, SL‑E3 y en cada intérprete del adaptador. **Cero pruebas omitidas** (sin `skipif` ni
`xfail`); el extra `bcv` se instala en la CI.

### 9.1 Oráculos independientes, versionados antes del código (S1‑0)

| Memoria | Contenido (a mano) | Valores que fija |
|---|---|---|
| `tests/fixtures/memorias/s1_conversion.md` | precio ficticio P = 1 000 Bs del 01/07/2026, tasa 633,3644 (MaPreX, verificada); evaluación al 01/10/2026 con 860,18 (BCV, verificada) | P/T0 = 1,578869920696521623255111907 USD; P/T1 = 1,162547373805482573414866656 USD; erosión 0,42 USD y 358,11 Bs (26,37 %) |
| `tests/fixtures/memorias/s1_reajuste.md` | una partida, PU contrato 100 Bs, pesos 0,5 / 0,2 / 0,3; índices **ficticios** 200→230, 150→165, 80→100; 1 000 unidades ejecutadas; R = 0,10; PU comprobado 116 Bs; tasa ficticia 850 Bs/USD | Km = 1,17; escalatoria 15 300,00 Bs (18,00 USD); comprobación 16 000,00 Bs (18,82 USD); diferencia −700,00 Bs |
| `tests/fixtures/memorias/s1_precios_empresa.md` | una lista de empresa con un insumo sembrado por condición de la fila RF‑68 de §9.2, más uno dentro de rango y vigente, frente a la referencia MaPreX en Bs | conjunto exacto de hallazgos de §9.2 |

Las pruebas comparan con estas memorias, no con la expresión que se prueba. La conversión de una versión se
verifica además con la **homogeneidad** del PU (§5.3), que no usa `convertir_version`.

### 9.2 Matriz

| RF / RNF | Prueba |
|---|---|
| RF‑64 | clínica y TI‑001 convertidas a Bs con 860,18: total = total × tasa a ± 0,01; bono convertido; plan y curva conservados (R2 cierra); versión de origen recarga idéntica; `RegistroCambio` y `moneda_proyecto` escritos; sin tasa, sin fecha o sin fuente se rechaza |
| RF‑65 | seis datos por insumo; lista de otra moneda rechazada al guardar y al revalorar; base anterior muestra el origen heredado |
| RF‑66 | memoria de conversión con 28 dígitos y a ± 0,01; precio en USD da erosión 0 declarada; erosión por índice como columna aparte |
| Tasa aplicable | precio de un sábado toma la tasa del viernes; 7 días naturales pasa, 8 se rechaza; lado compra y venta |
| RF‑67 | `lista_vigente` no devuelve la lista de empresa (ni la de proyecto); precio propio prevalece; heredado marcado; dos empresas aisladas |
| RF‑68 | conjunto **exacto** de la memoria: desvío −20,00 % pasa, −20,01 % ADVERTENCIA, +30,00 % pasa, +30,01 % ADVERTENCIA; 30 días pasa, 31 ADVERTENCIA; tasa sin fecha ERROR; tasa sin fuente ADVERTENCIA; sin referencia → un INFO con la cuenta; impacto a ± 0,01 recalculado a mano |
| RF‑69 | archivo real del trimestre: N hojas → N valores de compra y venta del USD con su fecha valor (N del `FUENTE.md`); cuadrículas negativas: falta la etiqueta, fecha repetida, fecha fuera del trimestre, fecha posterior a la descarga, valor no numérico, valor ≤ 0, hoja de otra moneda; `.xlsx` renombrado `.xls`; > 20 MB; dominio ajeno; misma huella dos veces; revisión del INPC como importación nueva |
| RF‑70 | memoria de reajuste; fronteras: cierre el día anterior al aniversario → 0; inicio en el aniversario → reajusta; período que lo cruza → rechazo; contrato de 12 meses exactos → sin congelamiento; pesos que suman 0,9999 → rechazo; índice faltante → período no calculado; provisional marcado; excepción declarada marcada |
| RF‑71 | memoria de reajuste (comprobación y diferencia, dos monedas); sin versión revalorada → «no disponible»; proyecto en USD con índice en Bs → ADVERTENCIA; > 10 % → nota INDICIO; estudio recargado = guardado; Excel por `hojas_extra` con sus totales |
| RNF‑14 | todas las pruebas de S1 con `socket.socket.connect` bloqueado por un *fixture*; estudio recalculado tras importar una revisión: diferencia 0 |
| Bases anteriores | una base con el esquema de 0.5.0 (clínica, TI‑001, importada) abre, gana las tablas de §5.2 sin perder filas, recarga y audita igual |
| Arquitectura | `adapters/bcv` solo importa biblioteca estándar, `xlrd` y `openpyxl`; `ui/indices.py` y `ui/reajuste.py` sin Streamlit; `core/` no importa `adapters/`; `git diff s1-base -- core/contracts/` vacío |

**Regresión en cada compuerta (no se editan):** cinco APU a ± 0,01; 7 de 7; R4 de 3/4 pulg; TI‑001 total, PU y
punto de equilibrio; las dos huellas de RNF‑04; cuatro hojas de `exportar_excel`. Si un cambio de S1 moviera
alguna, se registra un ruling de reanclaje; nunca se edita la prueba.

### 9.3 Datos de prueba del BCV

Archivos reales en `tests/fixtures/bcv/` (un trimestre de la tasa, el `.xls` del INPC y, si su formato se
documenta, uno del índice de la construcción), cada uno con dirección, fecha de descarga y huella en
`FUENTE.md`. No se editan: los casos negativos se construyen sobre la cuadrícula neutra.

---

## 10. Tareas por fase

Ramas (guardia M9): `inc/silice-s1-nucleo` (solo `core/`, `tests/`, `docs/`), `inc/silice-s1-bcv` (solo
`adapters/bcv/`, `tests/`, `docs/`, `pyproject.toml`, `uv.lock`), `inc/silice-s1-ui` (`ui/`, `tests/`, `docs/`).
Etiqueta base `s1-base` al abrir S1‑1.

| Fase | Tareas (archivos, interfaces, pruebas) | Funciona al cerrar | Compuerta |
|---|---|---|---|
| **S1‑0** | 0.1 enmiendas a ERS (UC‑17, UC‑18, RF‑64…71, RNF‑14, nota de UC‑09, conteos), modelo de datos §2.5, arquitectura, plan de pruebas §8 y §9. 0.2 descargar los archivos reales del BCV (curl en Windows entra; antecedentes §6), versionarlos con `FUENTE.md` y escribir `docs/fuentes/bcv_formatos.md` (hojas, etiquetas, celdas, letra del trimestre, marca de provisional). 0.3 licencia de `xlrd`. 0.4 lista MaPreX en Bs (§6.2) con `scripts/lista_maprex_bs.py`. 0.5 las tres memorias de §9.1. 0.6 `scripts/meta_s1.py`. 0.7 verificar la columna Estado de `ui.hoja` con `origen_ids` de partidas | documentos y memorias aprobados | GS1‑0 |
| **S1‑1** núcleo | SL‑E1: tablas de §5.2 (primeras cinco); `core/catalog/indices.py`, `core/catalog/moneda.py`, `core/budget/moneda.py`; `guardar_presupuesto` rechaza monedas distintas; `MOTIVOS_VERSION` + `conversion`; `OBJETOS` + `moneda`. Pruebas: `tests/unit/test_moneda.py`, `tests/integration/test_conversion_version.py`, `test_indices.py`, bases anteriores | convertir la clínica a Bs y ver la erosión | GS1‑1 |
| **S1‑2** adaptador | `adapters/bcv/`: `libro.py`, `tasa.py`, `inpc.py`, `insumos_construccion.py` (o CSV canónico), `informe.py`; extra `bcv`. Pruebas: `tests/unit/adapters/test_bcv_*.py` sobre el archivo real y sobre cuadrículas | importar el trimestre real y el INPC | GS1‑2 |
| **S1‑3** núcleo + interfaz | SL‑E2: `lista_empresa`, `core/catalog/empresa.py`, lector con columnas opcionales, `lista_vigente`, `core/verification/precios.py`, `instantanea_precios`. Interfaz: `ui/indices.py`, páginas Índices y Precios de la empresa, Parámetros y Precios de `ui.hoja`. Pruebas: memoria de precios de empresa, AppTest de las páginas | una empresa con su lista auditada | GS1‑3 |
| **S1‑4** núcleo + interfaz | SL‑E3: cláusula, `core/budget/reajuste.py`, estudio. Interfaz: `ui/reajuste.py`, página Reajuste, exportación. Pruebas: memoria de reajuste, fronteras, RNF‑14 | un proyecto en Bs y otro en USD con su reajuste lado a lado | GS1‑4 |
| **S1‑5** cierre | `pyproject.toml` 0.6.0, `CHANGELOG.md`, etiqueta `v0.6.0`; manuales; recorridos guiados con las páginas nuevas; meta en OK; CI verde en Linux y Windows; aprobación de los cuatro encargos | versión 0.6.0 | GS1 |

**Si el tiempo aprieta**, cae primero el intérprete del índice de la construcción (queda el CSV canónico,
§7.3), luego la erosión por índice (queda la cambiaria). La moneda, la lista de empresa con R11 y R12, la tasa
y el reajuste lado a lado no se recortan: son el criterio de éxito de la 0.6.0.

---

## 11. Expedientes de `core/` (resumen; el texto completo va en `docs/bitacora/2026-10-silice-s1-expedientes.md`)

| Exp. | Regla que lo motiva | Por qué es genérico | Prueba que lo demuestra | Impacto | Costo si es erróneo |
|---|---|---|---|---|---|
| **SL‑E1** moneda, tasa, origen por precio, conversión, erosión | H‑D1, RF‑64 a RF‑66; hoy un precio no dice su fecha ni su moneda original y nada impide mezclar monedas | todo presupuesto tiene moneda y todo precio una fecha, en cualquier dominio | memoria de conversión; homogeneidad del total convertido; rechazo de monedas mezcladas; bases anteriores abren | tablas aditivas; `guardar_presupuesto` gana una validación que ningún dato existente incumple (todo es USD); dos constantes ganan un valor | si se prefiere convertir solo al presentar, se retira `convertir_version` y la moneda del proyecto pasa a ser una preferencia de vista (H‑D1 queda a medias) |
| **SL‑E2** lista de empresa, R11, R12 | H‑D8, RF‑67, RF‑68; una lista global de empresa secuestraría `lista_vigente` | cualquier empresa de cualquier especialidad tiene precios propios que envejecen | memoria de precios de empresa con conjunto exacto y fronteras; `lista_vigente` | `lista_vigente` excluye un alcance más; lector acepta columnas opcionales; R11/R12 fuera de `REGLAS` | si R11/R12 debieran estar en `REGLAS`, se reanclan las huellas de RNF‑04 con ruling; si el rango o el plazo son malos, son parámetros por lista |
| **SL‑E3** reajuste | H‑D3, RF‑70, RF‑71; art. 133–134 (transcripción) | la ley aplica a obras y servicios de cualquier dominio; la estructura sale del `ResultadoAPU` | memoria de reajuste; fronteras del primer año; recálculo exacto del estudio | módulo nuevo y tablas aditivas; no toca el motor ni las versiones | si la Gaceta o un experto cambian la fórmula, se cambia una función pura y su memoria; si cambian el primer año, un parámetro de la cláusula |

---

## 12. Decisiones y rulings para ratificar

| # | Decisión | Alternativa descartada | Costo si es errónea |
|---|---|---|---|
| S1‑R1 | La tasa de conversión es la de **venta** del BCV por defecto; el proyecto puede declarar compra. SUPUESTO_DECLARADO | promedio de compra y venta | ≈ 0,25 % en cada conversión (858,02 frente a 860,18 en el ejemplo verificado) |
| S1‑R2 | Tasa aplicable = mayor fecha valor ≤ fecha; más de 7 días naturales sin tasa se rechaza | la más cercana, antes o después | convertir con una tasa vieja sin aviso |
| S1‑R3 | Cambiar la moneda crea una lista derivada y una versión nueva (`conversion`); nada se reescribe | convertir solo al presentar | la versión no estaría en la moneda elegida |
| S1‑R4 | Lista de empresa = alcance `empresa`, copia de una base declarada con los precios propios, fuera de `lista_vigente` | lista global por vigencia | una empresa cambiaría la valoración de todos los proyectos |
| S1‑R5 | R11: rango −20 % / +30 % por **analogía** con la clase 3 de AACE que el proyecto usa para estimaciones (no es una fuente de rango por insumo); ADVERTENCIA; configurable por lista | ERROR; sin rango por defecto | falsas alarmas u omisiones; se corrige un parámetro |
| S1‑R6 | R12: plazo de vigencia 30 días, SUPUESTO_DECLARADO sin fuente; configurable por lista | sin plazo | precios viejos sin marcar, o ruido |
| S1‑R7 | R11 y R12 son reglas externas (como R8–R10), no entran en `REGLAS` | agregarlas a las siete | reanclaje de las huellas de RNF‑04 y del 7 de 7 |
| S1‑R8 | Escalatoria `Vo(Km−1)(1−R)` con `Km` polinómico y `R` declarado: **INDICIO**, a verificar con el documento y con un experto | no implementar hasta verificar | cambiar una función pura y su memoria |
| S1‑R9 | Primer año: solo contratos > 12 meses; el período que cruza el aniversario se rechaza; la excepción por equilibrio económico se declara | prorratear por días | un reajuste del primer año mal calculado |
| S1‑R10 | Índice del período = mes en que cierra; `I0` = mes declarado, obligatorio | promedio del período; mes de la oferta por defecto | diferencias de un mes de inflación; parámetro |
| S1‑R11 | Reajuste en la moneda de `Vo`; USD con índice en Bs da ADVERTENCIA, no se bloquea | convertir `Vo` a Bs siempre | sobreestimar el reajuste de un contrato en USD |
| S1‑R12 | `.xls` con `xlrd` (corrige el spec maestro, que nombra `openpyxl`) en el extra `bcv` | `python-calamine`; pedir al usuario que convierta a `.xlsx` | cambiar `libro.py`; la cuadrícula neutra aísla el resto |
| S1‑R13 | Archivos reales del BCV versionados como datos de prueba con su fuente y huella | archivos sintéticos | si no se pueden redistribuir, se reemplazan por cuadrículas transcritas a mano y se pierde la prueba del lector real |
| S1‑R14 | `R` no se aplica a la comprobación directa salvo que la cláusula lo declare | aplicarla siempre | comparación lado a lado sesgada |
| S1‑R15 | Monedas guardadas como `"Bs"` y `"USD"` (las palabras de H‑D1), no códigos ISO | código ISO del bolívar | renombrar un valor en datos nuevos; ninguna base existente tiene `"Bs"` |

---

## 13. Riesgos

| Riesgo | Mitigación |
|---|---|
| La norma transcrita no coincide con la Gaceta | todo «a cotejar»; restricciones y fórmula como parámetros y funciones puras; R0 del horizonte coteja antes de citar |
| La fórmula del INDICIO no es la que se usa en la práctica | S1‑R8; revisión por un experto en contratación pública antes de la tesis |
| El formato real del BCV difiere de lo esperado o cambia | formato documentado con archivos reales en S1‑0; cuadrícula neutra; CSV canónico (§7.3) |
| El índice de la construcción no se puede leer | CSV canónico con fuente declarada; orden de caída de §10 |
| INPC 2026 provisional y revisado | valor marcado; importación nueva; el estudio cita la que usó |
| Tres expedientes más en `core/` | TDD con rojo visto, tablas aditivas, contratos intactos, aval del tutor |
| Solapamiento con S2 (ejecutado) y S3 (empresa) | §2; preguntas 5 y 6; S1 deja `ejecutado_periodo` con fuente textual que S2 podrá enlazar |
| Precisión de los cocientes en `DecimalExacto` (texto de 40 caracteres) | contexto de 28 dígitos fijo; prueba de ida y vuelta de almacenamiento con los valores más largos de las memorias |

---

## 14. Preguntas abiertas

1. **Numeración de UC‑09.** La ERS reserva RF‑64 como inicio de los requisitos de UC‑09 (asistente); el spec
   maestro dio RF‑64 a RF‑71 a S1. ¿Se acepta mover la nota de UC‑09 «al siguiente número libre tras los
   specs de Sílice», y que S4 la resuelva?
2. ¿Tasa de **compra o venta** para convertir (S1‑R1)?
3. ¿Desde qué fecha corre el **primer año** del art. 134: firma, inicio o acta de inicio (a cotejar)?
4. ¿Qué significan `R` y `Km` en la fórmula del INDICIO, y qué índice del BCV va con cada componente
   (productor o mayorista; general o por grupo)? Hace falta un experto o el documento con autor.
5. **Empresa:** S1 la nombra con un texto en `lista_empresa`; ¿S3 la reemplaza por su entidad con claves y
   firma, y quién migra el texto?
6. **Lo ejecutado del período:** S1 lo recibe declarado en el estudio; ¿S2 lo sustituye por sus valuaciones
   y el estudio pasa a citarlas?
7. ¿Se aceptan el rango de R11 (−20 % / +30 %) y el plazo de R12 (30 días) como supuestos por defecto, o
   Eugenio prefiere otros?
8. ¿Se pueden redistribuir en el repositorio los archivos del BCV (S1‑R13)?
9. ¿Se marca algo (más que una nota) cuando las variaciones superan el 10 % del monto original, una vez
   confirmado el artículo de la Comisión de Contrataciones?
