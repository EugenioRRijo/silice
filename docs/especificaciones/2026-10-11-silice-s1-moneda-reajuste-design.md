# Sílice S1 (0.6.0): moneda por proyecto, base de precios por empresa, datos del BCV y reajuste

| Campo | Valor |
|---|---|
| Estado | **propuesta, revisión 2**: revisada el 2026‑10‑11 por los cinco encargos (requisitos, arquitectura, pruebas y calidad, verificador de hechos, seguridad) y corregida según los rulings RV‑1…RV‑26 de esa revisión; pendiente de la aprobación de Eugenio. Los tres expedientes de `core/` (§11) necesitan además el visto bueno del tutor |
| Versión que entrega | **0.6.0** (spec maestro §5) = **S5‑1 adelantado** (Alembic, respaldo, `preparar_base`, casos en carpeta; spec S5) **+ S1** (RV‑1, RV‑3). La 0.5.0 ya está en `main` (8610053, etiqueta anotada `v0.5.0`) |
| Fecha | 2026‑10‑11 |
| Rama del spec | `inc/silice` (worktree `.worktrees/silice`, ya contiene `main`). Construcción en ramas cortas por fase desde `main`, con PR contra `main` (RV‑2, §10) |
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
- **Lector de `.xls`:** como fija el spec maestro §3, `openpyxl` (ya instalado) solo lee `.xlsx`, y los
  archivos de la tasa y del INPC son `.xls` de Excel 97‑2003 (antecedentes §6). Se usa `xlrd` (≥ 2.0, que solo
  lee `.xls`) en el extra `bcv`, con su licencia confirmada en S1‑0 (S1‑R12). El extra `bcv` entra en el
  instalador básico (RV‑24): sin él, UC‑17 no funciona en el producto.
- **Numeración de UC‑09:** la ERS (notas de U0.1 y SF0) reserva **RF‑64** como el siguiente número libre para
  UC‑09 (asistente). Lo resolvió el spec maestro §9: UC‑09 usa RF‑32 (vacante reservado) y RF‑90…95, y RF‑64
  pasa a S1. La enmienda de esa nota en la ERS la aplica **S4.0** (spec S4 §3), no S1 (pregunta 1, cerrada).

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
- Valuaciones por cantidades ejecutadas (S2, 0.7.0). En la 0.6.0, lo ejecutado de cada período se escribe
  **a mano** en el estudio de reajuste, con su fuente; desde la 0.7.0 el estudio **cita** las valuaciones
  registradas no anuladas de S2 (RV‑11, RV‑18; §8.6).
- Variaciones de obra (aumentos, disminuciones, obras extra): S2.
- Monedas distintas de Bs y USD.
- Rutas nuevas de la API (la API se amplía en S3 y S5).
- Cuentas de usuario: el responsable sigue siendo un nombre declarado hasta S3 (S‑D4).
- Una entidad «empresa» con claves y firma: S3. Hasta S3, la lista de empresa guarda `empresa_nombre` y
  `empresa_rif` como texto (instantánea, sin clave foránea entre bases); desde S3 se rellenan desde la empresa
  propia de la instalación (RV‑6, ratificada por Eugenio el 2026‑10‑11, pregunta P1 del spec maestro §10.3; §6.1).
- El paquete auditado: es de S3. S1 solo deja sus datos listos para viajar en él (§8.7, RV‑8).
- Decidir si hubo ruptura del equilibrio económico: el sistema registra la excepción que el usuario declara,
  no la juzga.

---

## 3. Requisitos (enmienda a la ERS, IEEE 830)

**Numeración asignada:** UC‑17 y UC‑18; RF‑64 a RF‑71; RNF‑14; expedientes SL‑E1 a SL‑E3; reglas R11 y R12.
**Se usan todos; no queda ningún número vacante.** La meta (`scripts/meta_silice.py --version 0.6.0`, §9.4)
comprueba la **presencia** de estos números en la ERS, no conteos absolutos (RV‑17, REQ‑19). Como dato
informativo: hoy la ERS tiene 62 RF (RF‑32 vacante), 15 UC (UC‑09 reservado, sin texto) y 13 RNF; tras S1,
70 RF, 17 UC y 14 RNF.

### 3.1 Casos de uso

#### UC‑17 — Mantener la base de precios de la empresa y los índices del BCV

- **Actor principal:** administrador del catálogo. **Secundario:** proyectista. Desde S3, rol
  *administrador* (valor por defecto de la pregunta P2 del spec maestro §10.3).
- **Precondiciones:** catálogo con insumos; archivos del BCV ya descargados en el equipo; lista de referencia
  MaPreX cargada (S1‑0, tarea 0.4).
- **Flujo principal**
  1. El administrador elige uno o varios archivos del BCV y declara la **fuente** (dirección de la página del
     BCV de donde los bajó) y la **fecha de descarga**.
  2. El sistema lee cada archivo **sin conexión**, valida formato, fuente y fechas (§7.2) y muestra el
     informe de importación sin escribir nada: series, fechas, filas leídas, rechazadas y provisionales.
  3. El administrador confirma; el sistema guarda los valores con la huella SHA‑256 del archivo.
  4. El administrador carga la lista de su empresa (CSV o XLSX: las cuatro columnas de UC‑02 y, opcionales,
     `fecha`, `fuente` y `referencia` por fila), declara la empresa (nombre y RIF, como texto hasta S3; RV‑6),
     moneda, fecha y fuente de la lista y la **lista base** que completa los insumos que la empresa no cotiza.
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

- **Actor principal:** proyectista (quien arma). **Secundario:** gerente / administrador que revisa. Desde
  S3, rol *arma* (pregunta P2 del spec maestro §10.3, ratificada por Eugenio el 2026‑10‑11).
- **Precondiciones:** versión del contrato guardada; cláusula de reajuste declarada (§8.1); índices
  importados (UC‑17); para la comprobación directa, una versión revalorada por UC‑02 por período.
- **Flujo principal**
  1. El usuario abre la versión del contrato y su cláusula de reajuste.
  2. Declara, por período, las cantidades ejecutadas por partida con su **fuente** (número y fecha del acta o
     de la valuación). En la 0.6.0 las escribe a mano; desde la 0.7.0 el sistema las toma de las valuaciones
     **registradas** y no anuladas de S2, asignando cada valuación al período de la cláusula que contiene su
     fecha *hasta*, y el estudio cita cada valuación (§8.6, RV‑11, RV‑18).
  3. El sistema calcula la **escalatoria** de cada período con las restricciones de §8.2.
  4. El usuario elige, por período, la versión revalorada por UC‑02 que sirve de **comprobación directa**.
  5. El sistema muestra, por período y en total, los dos montos lado a lado, su diferencia, y cada monto en
     las dos monedas con la tasa de la fecha de cierre del período.
  6. El usuario guarda el estudio (fuente y responsable obligatorios) y lo exporta a Excel. El estudio lleva su
     **monto reconocido** por período: el del mecanismo de la cláusula; con `ambos`, el del mecanismo que la
     cláusula declara **pagadero** (`mecanismo_pagadero`, §8.1) y, si no lo declara, la escalatoria, con la
     comprobación como referencia (S1‑R20).
- **Flujos alternativos**
  - *3a. Período dentro del primer año (contrato de más de un año):* reajuste cero, con la nota «precios
    fijos el primer año (art. 134, a cotejar)».
  - *3b. Período que cruza el aniversario:* se rechaza y se pide partirlo; el sistema no prorratea.
  - *3c. Falta el índice de un mes:* ese período no se calcula y se declara; no se extrapola.
  - *3d. Índice provisional:* se calcula y se marca «provisional».
  - *3e. Excepción del primer año por ruptura del equilibrio económico:* el usuario la declara con
    justificación y fuente; el período se calcula y se marca «excepción declarada».
  - *3f. Lo ejecutado acumulado supera lo presupuestado de una partida:* **se guarda**, con un aviso en el
    estudio, y el reajuste se calcula sobre `min(Q, q)` (la parte que no excede lo presupuestado, §8.2); desde
    la 0.7.0 la valuación que lo produce ya lleva el ERROR de R13 (S2). Se alinea con R13 y con S2‑R8 (RV‑11);
    las variaciones de obra son de S2.
  - *4a. Sin versión revalorada para el período:* la comprobación directa queda «no disponible» y se muestra
    solo la escalatoria.
  - *5a. Proyecto en USD con índices en Bs:* ADVERTENCIA visible (§8.4).
  - *6a. La suma de reajustes supera el 10 % del monto original:* nota informativa sobre la opinión de la
    Comisión de Contrataciones, marcada INDICIO (artículo sin confirmar).
  - *6b. El último período del estudio es un mes que aún no cierra:* se guarda con estado **«parcial al corte»**
    y su fecha de corte; al cerrar el mes se guarda un estudio nuevo que lo **reemplaza** (fila nueva que cita al
    parcial; el parcial se conserva, solo‑agregar) (S1‑R21).
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
| RF‑64 | La moneda del proyecto (Bs o USD) se elige al crearlo; cambiarla crea una versión nueva **convertida** (motivo `conversion`), con la tasa fechada y su fuente, el bono de alimentación convertido, el plan conservado y un `RegistroCambio` (objeto `moneda`); la versión anterior no cambia | UC‑01, UC‑15 | E | S1‑1 | total convertido = total ÷ tasa (de Bs a USD) o × tasa (de USD a Bs) a ± 0,01 en la presentación, para la clínica y TI‑001; la versión de origen recarga idéntica; sin tasa, sin fecha o sin fuente se rechaza. Desde la 0.7.0: si el proyecto tiene una línea base de control declarada (S2), la conversión la deja **invalidada** y hay que declararla de nuevo sobre la versión convertida (RV‑11; la prueba la escribe S2) |
| RF‑65 | Cada precio tiene moneda original, precio original, fecha, y, si se convirtió, tasa con su fecha y su fuente (§5.1); una versión solo se valora con una lista de **su** moneda | UC‑15, UC‑17 | E | S1‑1 | la pestaña Precios muestra los seis datos por insumo; guardar una versión en Bs con una lista en USD se rechaza; las bases anteriores muestran el origen heredado de la lista |
| RF‑66 | La erosión de cada precio (§5.3) se muestra en Bs y en USD a una fecha de evaluación declarada, por insumo y por versión | UC‑15, UC‑17 | E | S1‑1 | la memoria `s1_conversion.md` (§9.1) se reproduce con 28 dígitos y a ± 0,01 en la presentación |
| RF‑67 | La lista de una empresa es una lista de alcance `empresa`: copia de una lista base declarada con los precios propios (fecha, moneda y fuente por precio), inmutable, fuera de `lista_vigente`, usable para valorar una versión | UC‑17 | E | S1‑3 | `lista_vigente` no la devuelve; un precio propio prevalece sobre el de la base; cada precio dice si es propio o heredado; la lista de una empresa no cambia la valoración de otra ni la de ningún proyecto que no la referencie |
| RF‑68 | Reglas **R11** (precio fuera de rango frente a MaPreX) y **R12** (precio vencido o sin trazabilidad de tasa) con la severidad de §6.3, el impacto en dinero y la fecha de evaluación en cada hallazgo | UC‑17, UC‑15 | E | S1‑3 | conjunto **exacto** de hallazgos de la memoria `s1_precios_empresa.md` (regla, severidad, insumo, impacto a ± 0,01) a la fecha de evaluación que fija la memoria, con sus fronteras exactas (§9.1); reevaluar a otra fecha no reescribe ninguna fila guardada |
| RF‑69 | Importación sin conexión de la tasa (.xls trimestral), el INPC (.xls mensual) y el índice de insumos de la construcción, con validación de formato, fuente y fecha, informe previo, huella SHA‑256 e importaciones idempotentes | UC‑17 | E | S1‑2 | el archivo real versionado de un trimestre da sus N hojas como N valores de compra y de venta del USD, y la primera, la última y una del medio dan los valores **transcritos a mano** en `FUENTE.md` (§9.3; incluye 858,02 / 860,18 Bs con fecha valor 01‑10‑2026); cada caso negativo de la fila RF‑69 de §9.2 se rechaza con su mensaje; reimportar la misma huella no escribe nada |
| RF‑70 | Reajuste por **fórmula escalatoria** (§8.3) con las restricciones del art. 134 de §8.2 («a cotejar») y la cláusula declarada (§8.1) | UC‑18 | E | S1‑4 | la memoria `s1_reajuste.md` (estructura `declarada`) da 15 300,00 Bs en el período del ejemplo; la memoria `s1_reajuste_por_partida.md` (estructura `por_partida`, dos partidas) da K_A = 1,175, K_B = 1,185 y 10 298,34 Bs (§9.1.2); cada frontera de §9.2 da su salida declarada |
| RF‑71 | **Comprobación directa** (con la versión revalorada por UC‑02) lado a lado con la escalatoria, por período y total, en las dos monedas; el estudio se guarda con fuente y responsable y se exporta por `hojas_extra`. Con `ambos`, el monto reconocido es el del mecanismo pagadero de la cláusula, o la escalatoria si no lo declara; el estudio de un mes en curso se guarda «parcial al corte» y se reemplaza al cerrar el mes (§8.5). Desde la 0.7.0, lo ejecutado de cada período sale de las valuaciones registradas no anuladas de S2, citadas, asignadas por su fecha *hasta* (§8.6) | UC‑18 | E | S1‑4 (0.7.0 para el último criterio) | la memoria da 16 000,00 Bs y una diferencia de −700,00 Bs; 18,00 y 18,82 USD a la tasa del ejemplo; la memoria por partida da 11 680,00 Bs y −1 381,66 Bs; el estudio recargado es idéntico al guardado; con la memoria `s1_reajuste.md` y `mecanismo` = `ambos`, el reconocido es 16 000,00 Bs si `mecanismo_pagadero` = `comprobacion` y 15 300,00 Bs (la escalatoria) si la cláusula no lo declara; un estudio guardado antes del cierre de su mes queda «parcial al corte» y el del cierre lo reemplaza sin borrarlo; lo ejecutado por encima de lo presupuestado se guarda con aviso y se reajusta sobre `min(Q, q)` (3f). **Criterio del puente (0.7.0, lo entrega RF‑72 de S2):** una valuación registrada con *hasta* = último día del mes cae en ese período y una con *hasta* = primer día del mes siguiente cae en el siguiente; una anulada no cuenta; el estudio cita el número de cada valuación usada |

### 3.3 Requisito no funcional

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑14 | Fiabilidad | **Reproducible y sin conexión:** importar, convertir, auditar con R11/R12 y reajustar no hacen ninguna llamada de red; el mismo estudio de reajuste, con las mismas importaciones citadas, da el mismo resultado aunque después se importe una revisión de los índices | toda la suite corre bajo la **guardia de red única** de `tests/conftest.py`, que solo deja conectar a 127.0.0.1 y ::1 (cualquier otro intento falla la prueba; RV‑17, PRU‑H3), y la meta comprueba que la guardia está activa; recálculo del estudio de la memoria tras importar una revisión: diferencia 0 exacta |

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
| `core/models/moneda.py` (nuevo, reexportado en `core/models/__init__`) | tablas aditivas de §5.2 (módulo propio para no tocar el archivo caliente `entidades.py`, RV‑2) | — | **SL‑E1, SL‑E2, SL‑E3** |
| `core/models/entidades.py` | solo `MOTIVOS_VERSION` + `conversion` y el alcance `empresa` | — | **SL‑E1, SL‑E2** |
| `migraciones/` (de S5‑1, adelantado a la 0.6.0) | una revisión de Alembic de S1, en el entorno de la **base del caso** (RV‑4), sobre la revisión base (= esquema de la 0.5.0), con las tablas de §5.2 | — | (expediente de S5) |
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
recargar. Al abrir una versión, `ui.hoja` las vuelve a evaluar **solo en memoria** a la fecha de hoy y
**muestra** esa evaluación en lugar de la guardada (no se suman), como R8–R10 (spec SF §8.4). La reevaluación
**nunca reescribe** filas guardadas: no cambia `huella_contenido` ni el informe emitido, que conserva sus
hallazgos a su fecha de emisión (RV‑9).

**R11 y R12 en la tabla de reglas externas (RV‑9).** Qué contexto corre cada regla y con qué instantánea lo fija
**una sola tabla, la del spec maestro §3.3**; S1 la cita y no la repite. Lo que S1 aporta a esa fila:

- La instantánea es `instantanea_precios(session, version, referencia, fecha_evaluacion)` (§4.2): lista de la
  versión, origen por precio (§5.1), referencia MaPreX en Bs (§6.2), tasas importadas, y el rango y el plazo de
  `lista_empresa`. En el paquete, la misma información sale de `precio_origen` en `presupuesto.json` y de
  `anexos/reajuste.json` (§8.7).
- **R12 recibe la fecha de evaluación explícita**, nunca la toma del reloj dentro de la regla: hoja en vivo =
  hoy; reauditoría del paquete = fecha de emisión del paquete; experimento de S4 = fecha fija de su protocolo;
  en la API, la fija S3‑0 y la respuesta la declara. R11 no depende de esa fecha (cada precio se lleva a USD
  con su propia tasa).
- En ningún contexto escriben filas (párrafo anterior).

### 4.4 Vista de desarrollo y física

- Dependencias: `xlrd>=2.0` en un extra nuevo `bcv` (S1‑R12), que entra en el **instalador básico** (RV‑24).
  Se agrega en el PR temprano «dependencias Sílice» (`pyproject.toml` + `uv.lock`, licencias verificadas; ante
  un conflicto del candado, `uv lock`, nunca a mano; RV‑2), no en la rama del adaptador. `openpyxl` ya está.
  Ninguna dependencia de red.
- Pruebas de arquitectura: en `tests/unit/test_arquitectura.py` solo la línea
  `TERCEROS_POR_ADAPTADOR["bcv"] = {"xlrd", "openpyxl"}` (la exige `test_toda_carpeta_de_adapters_tiene_su_regla`);
  las reglas propias de S1 (`ui/indices.py` y `ui/reajuste.py` sin `streamlit`, `pandas` ni `ui.caso`) van en
  su propio archivo, `tests/unit/test_arquitectura_s1.py` (RV‑2), con ayudantes compartidos fuera de los
  módulos de prueba (la guardia prohíbe que un módulo de prueba importe otro).
- La CI instala el extra `bcv` en Linux y Windows: ninguna prueba se omite por falta de `xlrd`.
- Las tablas de S1 viven en la **base del caso** (`datos\casos\*.db`; RV‑4), no en `instalacion.db`.
- Archivos del BCV de prueba en `tests/fixtures/bcv/` con un `FUENTE.md` (dirección, fecha de descarga,
  huella y la transcripción a mano de §9.3), límite de 20 MB y guardado seguro de subidas (A‑1, RNF‑12).

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
| `lista_empresa` | `lista_id` (PK), `empresa_nombre`, `empresa_rif` (texto, instantánea sin clave foránea a `instalacion.db`; RV‑6, ratificada por Eugenio el 2026‑10‑11, P1), `lista_base_id`, `lista_referencia_id` (MaPreX), `plazo_vigencia_dias`, `rango_inferior`, `rango_superior` | SL‑E2 |
| `clausula_reajuste`, `componente_clausula` | §8.1 | SL‑E3 |
| `estudio_reajuste`, `periodo_reajuste`, `ejecutado_periodo` | §8.5 | SL‑E3 |

**Migraciones (RV‑1, RV‑3).** La 0.6.0 **empieza** con S5‑1 adelantado: Alembic con su revisión base = esquema
de la 0.5.0, respaldo, `operacion.base_datos.preparar_base` y casos en `datos\casos\`. S5 conserva la propiedad
del spec de Alembic; S1 solo agrega **su** revisión con las tablas de esta sección (todas aditivas, sin
`ALTER TABLE` sobre tablas existentes). Las bases anteriores (clínica, TI‑001, importadas, de la 0.5.0) entran
por la **revisión base** de Alembic y suben a `head` con la revisión de S1 al abrirse por `preparar_base`; S1
no usa `stamp`. La prueba de deriva (RNF‑20, de S5) está activa desde S1: una base llevada a `head` es igual a
la creada desde los metadatos. Como Alembic ya está, un cambio posterior de columnas (p. ej. la cita a la
valuación que agrega S2 en `ejecutado_periodo`, §8.6) es una revisión más, no una tabla rehecha.

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

  **Porcentaje de erosión** (uno solo, igual en las dos monedas): `1 − T0/T1` = erosión en USD ÷ `P/T0` =
  erosión en Bs ÷ `P·T1/T0`. Es la fracción del valor que el precio perdió; no se expresa sobre `P`.

  Con el índice de insumos de la construcción o el INPC cargados, se muestra además la **erosión por índice**
  `P·(I1/I0 − 1)` en Bs, con la serie y la importación citadas. Es una columna aparte, no se suma.

**Conversión de una versión** (`convertir_version`): crea una lista derivada de alcance `proyecto` (SF‑E7) con
cada precio convertido y su `PrecioOrigen`; toma las líneas de la instantánea (SF‑E6) con esa lista; convierte
el precio de las líneas sin insumo (precio manual) con la misma tasa; convierte `bono_alimentacion`; conserva
el plan (fracciones); elabora, guarda con `version_origen` (motivo `conversion`) **por
`core/budget/persistencia.guardar_presupuesto`**, el único embudo que crea versiones (desde S3 la versión se sella al confirmar la
transacción que la crea, con `usuario` exigido al confirmar; RV‑7), agrega una fila a `moneda_proyecto` y un `RegistroCambio` (objeto `moneda`,
valores anterior y nuevo, fuente = importación de la tasa). Desde la 0.7.0, si el proyecto tiene una línea
base de control declarada (S2), la conversión la deja **invalidada** y hay que declararla de nuevo sobre la
versión convertida (RV‑11). Como el PU es homogéneo de grado 1 en los montos (precios y bono; las fracciones no cambian), el total
convertido debe ser el total ÷ `T`: es el **oráculo independiente** de RF‑64.

---

## 6. Base de precios por empresa y auditoría de precios (SL‑E2)

### 6.1 Lista de empresa

`crear_lista_de_empresa(session, empresa_nombre, empresa_rif, base, precios_propios, *, moneda, fecha, fuente,
referencia)` (firma exacta en S1‑3): copia de `base` (en la moneda de la lista; si `base` está en otra moneda se convierte
con `convertir_lista` y su `PrecioOrigen`) con los precios propios encima, cada uno con su `PrecioOrigen`
(fecha, fuente, moneda original). Registra `ListaPreciosOrigen.alcance = "empresa"` y una fila de
`lista_empresa`. `lista_vigente` excluye `empresa` como ya excluye `proyecto`. Una versión la usa
referenciándola explícitamente, como una lista de proyecto (DA‑SF‑9). Una cotización sobre una versión
valorada con lista de empresa toma esa lista como base (SF‑E7 sin cambios).

**Empresa (RV‑6, ratificada por Eugenio el 2026‑10‑11, pregunta P1 del spec maestro §10.3).** Una
instalación tiene **una sola empresa propia** (tabla de S3 en `instalacion.db`: nombre, RIF, ciudad opcional) y las empresas **ajenas**
registradas que llegan en los paquetes. Antes de S3 (0.6.0 y 0.7.0) la empresa de una lista es el texto
`empresa_nombre` + `empresa_rif` que declara el administrador del catálogo; desde S3 la interfaz los
**rellena** desde la empresa propia. Siguen siendo texto en la base del caso (una instantánea: no hay clave
foránea entre bases), así que S3 no migra nada.

### 6.2 Lista de referencia MaPreX en Bs

Para R11 se carga en S1‑0 una lista **MaPreX julio 2026 en Bs** desde la columna `precio_bs` de los cuatro
`referencia_*.csv` (111 filas, verificadas a mano en M0.2), con su Ref (`ReferenciaPrecio`), fecha (09/07/2026;
mano de obra 01/07/2026) y tasa 633,3644 Bs/USD al 01/07/2026. Usar `precio_bs` evita reconstruir bolívares
desde `precio_usd`, que está redondeado a 4 decimales. **Límite declarado:** solo esos 111 insumos son
contrastables; los demás van al INFO de R11. Si la interfaz ofrece cargar esta lista, importa el script
**dentro de la acción** (importación diferida), no al cargar la página (RV‑25).

### 6.3 Reglas R11 y R12 (en `core/verification/precios.py`; implementan `ReglaVerificacion`)

| Regla | Comprueba | Severidad | Impacto |
|---|---|---|---|
| **R11** `PrecioFueraDeRango` | precio de la lista frente a su referencia MaPreX, ambos llevados a USD con la tasa que declara cada precio (§5.1) o, si no la declara, la aplicable a **su propia fecha**: desvío `p/p_ref − 1` fuera de [`rango_inferior`, `rango_superior`] (por defecto −20 % / +30 %, S1‑R5) | ADVERTENCIA por insumo fuera de rango; **un** INFO con el número de insumos no contrastables (sin referencia o sin tasa a su fecha) | diferencia del total de la versión si el insumo valiera su referencia, calculada con `calcular_apu` sobre las composiciones de la versión (no con una fórmula aparte) |
| **R12** `PrecioVencido` | antigüedad del precio a la fecha de evaluación mayor que `plazo_vigencia_dias` (por defecto 30, S1‑R6); precio convertido cuya tasa no tiene fecha o no tiene fuente | ADVERTENCIA si vencido o si la tasa no tiene fuente; **ERROR** si la tasa de un precio convertido no tiene fecha (el número no es trazable ni reproducible) | erosión en Bs del precio (§5.3) llevada al total de la versión con `calcular_apu` |

En la frontera, el desvío exactamente igual al límite **pasa** y la antigüedad exactamente igual al plazo
**pasa**. **Cálculo del desvío** (PRU‑H11): con `p` y `p_ref` en sus monedas originales y `T_p`, `T_ref` sus
tasas (Bs por USD; para un precio que ya está en USD se toma 1), el desvío en USD es
`(p · T_ref) / (p_ref · T_p) − 1`: se multiplica antes de dividir y se divide **una sola vez**, y el resultado
**no se cuantiza** antes de comparar con el rango (solo se redondea a 0,01 % al presentarlo). Si los dos precios están en la misma moneda con la misma tasa, el desvío
es exactamente `p/p_ref − 1`; así se construyen las fronteras de la memoria (§9.1), para que −20 % y +30 % sean
exactos y no dependan de un cociente de 28 dígitos. Cada hallazgo cita en `origen_ids` los códigos de las partidas que usan el insumo (precedente de
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

Los nombres de hojas, las etiquetas y las celdas rechazadas que el informe repite, y las descripciones de una
lista de empresa importada, son **texto ajeno**: la interfaz los muestra con `ui/texto_seguro()` o en celdas,
nunca como Markdown interpretado (RV‑14).

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
| `mecanismo_pagadero` | solo con `ambos`: `escalatoria` o `comprobacion`, el que el contrato declara pagadero (opcional, con su fuente). Fija el **monto reconocido**; si falta, se reconoce la escalatoria y la comprobación queda como referencia (S1‑R20) | num. 2 |
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
2. **Solo lo ejecutado en el período:** el monto reajustable `Vo` de un período es Σ cantidad reajustable del
   período × PU del contrato; nunca el saldo por ejecutar ni lo ejecutado en otro período. La cantidad
   reajustable de una partida en el período `m` es `min(q_m, máx(0, Q − Σ q de los períodos anteriores))`: lo
   acumulado se reajusta hasta `min(Q, q)`. Lo que excede lo presupuestado **se guarda** con aviso y no se
   reajusta (3f; RV‑11, alineado con R13 y S2‑R8).
3. **Estructura, mecanismo, periodicidad e índices declarados:** sin cláusula completa no se calcula.
4. La escalatoria en **reconsideraciones** solo vale para obras y servicios (transcripción); el estudio lo
   recuerda como nota, no lo decide.

### 8.3 Fórmula escalatoria (supuesto declarado S1‑R8)

Forma tomada del INDICIO: `Vpm = Vo · (Km − 1) · (1 − R)`. Interpretación de **este spec** (no verificada):
`Vo` = valor de lo ejecutado en el período a precios del contrato; `Km` = coeficiente polinómico
`Σ pᵢ · Iᵢ,m / Iᵢ,0` (la ley de 2009 hablaba de «fórmulas polinómicas», antecedentes §4); `R` = fracción no
reajustable declarada en la cláusula. Con estructura `por_partida`, `Km` se calcula por partida y
`Vpm = Σⱼ Voⱼ · (Kⱼ,m − 1) · (1 − R)`, con los montos por componente del `ResultadoAPU` de la partida en la
versión del contrato (materiales `cₘ`, equipos `cₑ`, mano de obra `cₒ`; su suma es el costo directo `CDⱼ`,
`core/costing/motor.py`): `Kⱼ,m = (Σᵢ cᵢ,ⱼ · Iᵢ,m / Iᵢ,0) / CDⱼ`. Los pesos `cᵢ,ⱼ / CDⱼ` suman 1 por
construcción, así que el chequeo «los pesos suman 1» de §8.1 solo aplica a la estructura `declarada`. `Iᵢ,m` es el valor del índice del **mes en que cierra el período**
(S1‑R10) en la importación vigente al calcular, que el estudio cita. Las funciones son puras: reciben los
valores, no la sesión.

### 8.4 Comprobación directa y comparación

`reajuste_por_comprobacion` = Σⱼ q_reajustableⱼ,m · (PU_comprobadoⱼ − PU_contratoⱼ) (la cantidad reajustable
de §8.2), con `PU_comprobado` de la
versión revalorada por UC‑02 que el usuario elige para el período (la lista de esa versión es la evidencia).
`R` no se aplica a la comprobación salvo que la cláusula lo diga (S1‑R14). `comparar_reajustes` da por período
y total: escalatoria, comprobación, diferencia y cada uno en la otra moneda con `tasa_aplicable(cierre del
período)`. La diferencia en la otra moneda se calcula como (diferencia en la moneda de `Vo`) convertida y se
redondea **una vez** al presentar; no es la resta de los dos montos ya redondeados (en la memoria por partida,
−1 381,66 / 850 = −1,63 USD, mientras que 12,12 − 13,74 = −1,62). El reajuste se calcula en la moneda en que está `Vo` (la del proyecto); si es USD y algún índice es
una serie en Bs, el estudio lleva una ADVERTENCIA: un índice de precios en bolívares aplicado a montos en
dólares cuenta dos veces la devaluación (S1‑R11).

### 8.5 Estudio guardado

`estudio_reajuste` (versión del contrato, cláusula, fecha de cálculo, **estado** (`cerrado` o `parcial al
corte`), fecha de corte si es parcial, `reemplaza_a` (el estudio parcial que reemplaza, anulable), fuente,
responsable), `periodo_reajuste` (desde, hasta, `Km`, escalatoria, comprobación, **monto reconocido** y su
mecanismo, versión revalorada usada, importación de cada índice, marcas: primer año, provisional, excepción, exceso
sobre lo presupuestado) y `ejecutado_periodo` (partida, cantidad, fuente). Recargar un estudio lo **recalcula** con
las importaciones citadas y exige igualdad exacta con lo guardado (RNF‑14). Un estudio guardado es inmutable;
rehacerlo es guardar otro.

- **Monto reconocido (S1‑R20).** Con mecanismo `escalatoria` o `comprobacion`, el de ese mecanismo. Con `ambos`,
  el del `mecanismo_pagadero` de la cláusula (§8.1); si la cláusula no lo declara, la **escalatoria**, y la
  comprobación se muestra como referencia. Si el mecanismo reconocido quedó «no disponible» en un período (3c,
  4a), ese período no tiene monto reconocido y se declara; no se toma el otro.
- **Mes en curso (S1‑R21).** Un estudio cuyo último período es un mes que aún no cierra a la fecha de cálculo se
  guarda con estado **«parcial al corte»** (lo ejecutado y los índices disponibles a esa fecha). Al cerrar el mes
  se guarda un estudio **nuevo**, `cerrado`, con `reemplaza_a` = el parcial: solo‑agregar, el parcial se conserva
  y deja de sumar desde la fecha de cálculo del que lo reemplaza. Un parcial se reemplaza una sola vez.

### 8.6 Puente con S2: lo ejecutado del período (RV‑11, RV‑18, RV‑12)

| Versión | De dónde sale lo ejecutado | Qué cita el estudio |
|---|---|---|
| **0.6.0** | escrito a mano por período y partida en `ejecutado_periodo`, con su fuente textual (número y fecha del acta o de la valuación) | la fuente textual |
| **0.7.0** | `ejecutado_por_periodo` de S2: las valuaciones **registradas** y no anuladas (RV‑18, decidida por Eugenio el 2026‑10‑11: sin conformación; cuentan desde su registro y solo la anulación las saca); cada valuación entra entera en el período de la cláusula (mensual en el caso común; §8.1 `periodicidad`) que contiene su fecha *hasta*; una valuación semanal que cruza el cierre del mes no se prorratea | cada valuación usada (S2 agrega la cita en su revisión de Alembic de `ejecutado_periodo`) |

- **Ejecutado mayor que lo presupuestado:** se guarda; R13 lo marca ERROR en la valuación (S2) y el estudio lo
  reajusta solo hasta `min(Q, q)` con aviso (§8.2, UC‑18 3f).
- **Cambio de moneda después de declarar la línea base de control:** la conversión crea versión nueva (§5.3) y
  la línea base queda **invalidada**; hay que declararla de nuevo (RV‑11). Un estudio de reajuste guardado no
  cambia: sigue citando la versión del contrato que usó.
- **Reajuste reconocido (RV‑12):** el punto de equilibrio proyectado de S2 suma solo el reajuste **ya
  reconocido**, es decir, el de los estudios de S1 guardados hasta la fecha, nunca uno proyectado. S1 entrega
  los estudios guardados con su **monto reconocido** por período (§8.5, S1‑R20), su estado y `reemplaza_a`; un
  estudio reemplazado por otro guardado hasta esa fecha no suma (S1‑R21). Qué suma S2 lo fija S2 (§4.7).
- **Criterio y prueba:** el criterio del puente está en RF‑71 (§3.2). Su prueba
  (`test_estudio_cita_valuaciones_por_fecha_hasta`) la escribe S2 en la fase que entrega `ejecutado_por_periodo`
  (RF‑72), con el rojo observado antes de la implementación, y queda en la matriz de S1 (§9.2).

### 8.7 Lo que S1 deja listo para el paquete auditado (S3, RV‑8)

S3 es dueño del formato. S1 garantiza que sus datos se pueden serializar sin pérdida: la moneda del proyecto y
el `precio_origen` de cada precio van en `presupuesto.json` (documento canónico); los índices usados (con su
fuente y la huella SHA‑256 del archivo del BCV) y los estudios de reajuste van en `anexos/reajuste.json`,
cubierto por `huella_anexos` del manifiesto firmado, con huella pero sin cadena propia. La reauditoría de S3
recomputa R11 y R12 con esos datos, R12 a la fecha de emisión del paquete (§4.3).

---

## 9. Pruebas (IEEE 829)

Pruebas antes que código con **rojo observado**: el commit de la prueba va antes que el de la implementación
en SL‑E1, SL‑E2, SL‑E3 y en cada intérprete del adaptador. **Cero pruebas omitidas** (sin `skipif` ni
`xfail`); el extra `bcv` se instala en la CI.

### 9.1 Oráculos independientes, versionados antes del código (S1‑0)

| Memoria | Contenido (a mano) | Valores que fija |
|---|---|---|
| `tests/fixtures/memorias/s1_conversion.md` | precio ficticio P = 1 000 Bs del 01/07/2026, tasa 633,3644 (MaPreX, verificada); evaluación al 01/10/2026 con 860,18 (BCV, verificada) | P/T0 = 1,578869920696521623255111907 USD; P/T1 = 1,162547373805482573414866656 USD; erosión 0,42 USD y 358,11 Bs; **26,37 % es la erosión en USD sobre el valor en USD a la fecha del precio** (0,4163 / 1,5789 = 358,11 / 1 358,11); sobre P en Bs serían 35,81 % (358,11 / 1 000), que **no** es el porcentaje que define §5.3 (§9.1.1) |
| `tests/fixtures/memorias/s1_reajuste.md` | estructura `declarada`: una partida, PU contrato 100 Bs, pesos 0,5 / 0,2 / 0,3; índices **ficticios** 200→230, 150→165, 80→100; 1 000 unidades ejecutadas; R = 0,10; PU comprobado 116 Bs; tasa ficticia 850 Bs/USD | Km = 1,17; escalatoria 15 300,00 Bs (18,00 USD); comprobación 16 000,00 Bs (18,82 USD); diferencia −700,00 Bs (−0,82 USD) |
| `tests/fixtures/memorias/s1_reajuste_por_partida.md` | estructura `por_partida` (PRU‑H12): dos partidas de composiciones distintas, pesos desde su `ResultadoAPU`; los mismos índices, R y tasa (§9.1.2) | K_A = 1,175; K_B = 1,185; escalatoria 10 298,34 Bs (12,12 USD); comprobación 11 680,00 Bs (13,74 USD); diferencia −1 381,66 Bs (−1,63 USD); con estructura declarada 0,5 / 0,2 / 0,3 daría 9 785,88 Bs |
| `tests/fixtures/memorias/s1_precios_empresa.md` | una lista de empresa con un insumo sembrado por condición de la fila RF‑68 de §9.2, más uno dentro de rango y vigente, frente a la referencia MaPreX en Bs; **fecha de evaluación fija** escrita en la memoria (RV‑9); los insumos de frontera de R11 en Bs con la **misma tasa** que su referencia (PRU‑H11): `p = 0,8000 · p_ref` (−20,00 %, pasa), `0,7999 · p_ref` (−20,01 %), `1,3000 · p_ref` (+30,00 %, pasa), `1,3001 · p_ref` (+30,01 %) | conjunto exacto de hallazgos de §9.2 |

Las pruebas comparan con estas memorias, no con la expresión que se prueba. La conversión de una versión se
verifica además con la **homogeneidad** del PU (§5.3), que no usa `convertir_version`.

#### 9.1.1 Memoria de conversión: base del porcentaje

P = 1 000 Bs; T0 = 633,3644; T1 = 860,18 (Bs por USD).

- P/T0 = 1,578869920696521623255111907 USD; P/T1 = 1,162547373805482573414866656 USD.
- Erosión en USD = P/T0 − P/T1 = 0,416322546891039049840245251 → **0,42 USD**.
- Erosión en Bs = P·T1/T0 − P = 1 358,112328… − 1 000 = 358,112328384733969891582160 → **358,11 Bs**.
- Porcentaje (§5.3) = 1 − T0/T1 = 0,4163 / 1,5789 = 358,11 / 1 358,11 = 0,2636838801… → **26,37 %**.
- Contraste (no es el porcentaje de §5.3): 358,11 / 1 000 = **35,81 %**. La prueba comprueba que la pantalla
  muestra 26,37 % y no 35,81 %.

#### 9.1.2 Memoria de reajuste por partida (`s1_reajuste_por_partida.md`, PRU‑H12)

Datos **ficticios y declarados**. Un período, ya fuera del primer año; R = 0,10; tasa 850 Bs/USD; índices
como en `s1_reajuste.md`: materiales 200→230 (relativo 1,15), equipos 150→165 (1,10), mano de obra 80→100
(1,25). El PU del contrato es un dato de la versión (aquí, CD × 1,30 por un factor ficticio de administración
y utilidad).

| Partida | `ResultadoAPU` (Bs/unidad): mat. / equipos / M.O. | CD | Pesos (c/CD) | PU contrato | Ejecutado | PU comprobado |
|---|---|---|---|---|---|---|
| A | 45,00 / 7,50 / 22,50 | 75,00 | 0,6 / 0,1 / 0,3 | 97,50 | 400 | 115,00 |
| B | 32,00 / 48,00 / 80,00 | 160,00 | 0,2 / 0,3 / 0,5 | 208,00 | 120 | 247,00 |

Cuentas a mano:

- K_A = (45 · 1,15 + 7,5 · 1,10 + 22,5 · 1,25) / 75 = (51,75 + 8,25 + 28,125) / 75 = 88,125 / 75 = **1,175**.
- K_B = (32 · 1,15 + 48 · 1,10 + 80 · 1,25) / 160 = (36,80 + 52,80 + 100,00) / 160 = 189,60 / 160 = **1,185**.
- Vo_A = 400 · 97,50 = 39 000,00 Bs; Vo_B = 120 · 208,00 = 24 960,00 Bs; Vo = 63 960,00 Bs.
- Escalatoria A = 39 000 · 0,175 · 0,9 = **6 142,50 Bs**; B = 24 960 · 0,185 · 0,9 = **4 155,84 Bs**;
  total **10 298,34 Bs**.
- Comprobación A = 400 · (115,00 − 97,50) = 400 · 17,50 = **7 000,00 Bs**; B = 120 · (247,00 − 208,00) =
  120 · 39,00 = **4 680,00 Bs**; total **11 680,00 Bs**.
- Diferencia (escalatoria − comprobación) = 10 298,34 − 11 680,00 = **−1 381,66 Bs**.
- En USD a 850: 10 298,34 / 850 = 12,1156941… → **12,12**; 11 680 / 850 = 13,7411764… → **13,74**;
  diferencia −1 381,66 / 850 = −1,6254823… → **−1,63** (redondeada una vez, §8.4; no 12,12 − 13,74 = −1,62).
- Testigo de que el camino `por_partida` se ejerce: con estructura `declarada` 0,5 / 0,2 / 0,3 (Km = 1,17) los
  mismos datos darían 63 960 · 0,17 · 0,9 = 9 785,88 Bs, distinto de 10 298,34.

Verificado con `Decimal` (28 dígitos, `ROUND_HALF_EVEN`) el 2026‑10‑11 al escribir este spec; S1‑0 copia estas
cuentas a la memoria y las rehace a mano antes del código.

### 9.2 Matriz

| RF / RNF | Prueba |
|---|---|
| RF‑64 | clínica y TI‑001 convertidas a Bs con 860,18: total = total × tasa a ± 0,01; bono convertido; plan y curva conservados (R2 cierra); versión de origen recarga idéntica; `RegistroCambio` y `moneda_proyecto` escritos; sin tasa, sin fecha o sin fuente se rechaza |
| RF‑65 | seis datos por insumo; lista de otra moneda rechazada al guardar y al revalorar; base anterior muestra el origen heredado |
| RF‑66 | memoria de conversión con 28 dígitos y a ± 0,01; precio en USD da erosión 0 declarada; erosión por índice como columna aparte |
| Tasa aplicable | precio de un sábado toma la tasa del viernes; 7 días naturales pasa, 8 se rechaza; lado compra y venta |
| RF‑67 | `lista_vigente` no devuelve la lista de empresa (ni la de proyecto); precio propio prevalece; heredado marcado; dos empresas aisladas |
| RF‑68 | conjunto **exacto** de la memoria a su fecha de evaluación fija: desvío −20,00 % pasa, −20,01 % ADVERTENCIA, +30,00 % pasa, +30,01 % ADVERTENCIA (fronteras en Bs contra Bs con la misma tasa, desvío exacto; PRU‑H11); 30 días pasa, 31 ADVERTENCIA; tasa sin fecha ERROR; tasa sin fuente ADVERTENCIA; sin referencia → un INFO con la cuenta; impacto a ± 0,01 recalculado a mano; reevaluar R12 a otra fecha cambia lo mostrado y deja intactas las filas guardadas y `huella_contenido` (RV‑9) |
| RF‑69 | archivo real del trimestre: N hojas → N valores de compra y venta del USD con su fecha valor; N y los valores de la primera hoja, la última y una del medio se comparan con la **transcripción a mano** de `FUENTE.md` (§9.3), no con un conteo hecho con `xlrd` (PRU‑H13); cuadrículas negativas: falta la etiqueta, fecha repetida, fecha fuera del trimestre, fecha posterior a la descarga, valor no numérico, valor ≤ 0, hoja de otra moneda; `.xlsx` renombrado `.xls`; > 20 MB; dominio ajeno; misma huella dos veces; revisión del INPC como importación nueva |
| RF‑70 | las dos memorias de reajuste (`declarada` y `por_partida`); fronteras: cierre el día anterior al aniversario → 0; inicio en el aniversario → reajusta; período que lo cruza → rechazo; contrato de 12 meses exactos → sin congelamiento; pesos que suman 0,9999 → rechazo; índice faltante → período no calculado; provisional marcado; excepción declarada marcada |
| RF‑71 | las dos memorias de reajuste (comprobación y diferencia, dos monedas; diferencia en USD redondeada una vez); sin versión revalorada → «no disponible»; proyecto en USD con índice en Bs → ADVERTENCIA; > 10 % → nota INDICIO; ejecutado acumulado = Q pasa sin aviso, Q + 0,001 se guarda con aviso y reajusta solo Q (3f); estudio recargado = guardado; Excel por `hojas_extra` con sus totales. **0.7.0** (la escribe S2, §8.6): `test_estudio_cita_valuaciones_por_fecha_hasta` (*hasta* = último día del mes → ese período; primer día del mes siguiente → el siguiente; una registrada cuenta sin otro paso y una anulada no cuenta; cita de cada valuación). Monto reconocido con la memoria `s1_reajuste.md` y `ambos`: `mecanismo_pagadero` = `comprobacion` → 16 000,00 Bs; sin `mecanismo_pagadero` → 15 300,00 Bs (escalatoria); comprobación «no disponible» con `mecanismo_pagadero` = `comprobacion` → período sin monto reconocido, declarado. Mes en curso: fecha de cálculo = último día del mes → `cerrado`; un día antes → «parcial al corte»; el estudio de cierre con `reemplaza_a` deja el parcial en la base; reemplazar dos veces el mismo parcial se rechaza |
| RNF‑14 | la suite corre bajo la guardia de red única de `tests/conftest.py` (solo 127.0.0.1 y ::1; RV‑17), sin guardias propias por *fixture*; la meta comprueba que está activa; estudio recalculado tras importar una revisión: diferencia 0 |
| Bases anteriores | una base de la 0.5.0 (clínica, TI‑001, importada) abre por `preparar_base`: entra por la revisión base de Alembic, sube a `head` con la revisión de S1 (con respaldo previo), gana las tablas de §5.2 sin perder filas, recarga y audita igual que su ficha (total literal, huella del informe, filas por tabla, escrita con el código de `v0.5.0`; RV‑3, PRU‑H15); deriva de esquema 0 (RNF‑20) |
| Arquitectura | `adapters/bcv` solo importa biblioteca estándar, `xlrd` y `openpyxl`; `ui/indices.py` y `ui/reajuste.py` sin Streamlit (`tests/unit/test_arquitectura_s1.py`); `core/` no importa `adapters/`; `git diff v0.5.0..HEAD -- core/contracts/` vacío |

**Regresión en cada compuerta (bloque literal, común a todos los specs de Sílice; RV‑17):**

- cinco APU ± 0,01;
- 7 de 7;
- R4 3/4 pulg y `test_r4_marca_3_4_pulg_y_no_marca_pvc`;
- TI‑001 total, PU y PE 28 586,76 USD Día 6;
- dos huellas de RNF‑04;
- cuatro hojas (`exportar_excel`).

Estas pruebas **no se editan**: la meta comprueba que `git diff v0.5.0..HEAD` está vacío sobre sus archivos. Si
un cambio de S1 moviera alguna, se registra un ruling de reanclaje; nunca se edita la prueba.

### 9.3 Datos de prueba del BCV

Archivos reales en `tests/fixtures/bcv/` (un trimestre de la tasa, el `.xls` del INPC y, si su formato se
documenta, uno del índice de la construcción), cada uno con dirección, fecha de descarga y huella en
`FUENTE.md`. No se editan: los casos negativos se construyen sobre la cuadrícula neutra.

**Oráculo del archivo real (PRU‑H13).** `FUENTE.md` registra, **transcritos a mano** por quien abre el archivo
en S1‑0 (con Excel o LibreOffice, no con `xlrd`): el número N de hojas; la primera, la última y una del medio,
cada una con su fecha valor y sus valores de compra y venta del USD; y el literal ya verificado de la tasa con
fecha valor 01‑10‑2026: **858,02 / 860,18 Bs** (antecedentes §6). Del INPC, la misma transcripción para el
primer mes, el último y uno del medio, con su marca de provisional. La prueba compara lo que entrega el
adaptador con esa transcripción; así el oráculo no sale de la biblioteca que se prueba. Los `.xls` se versionan
en el repositorio privado como *fixtures* de prueba y no van en el instalador: cada empresa descarga los suyos
(S1‑R13; pregunta 8 = P6 del spec maestro §10.3, ratificada por Eugenio el 2026‑10‑11).

### 9.4 Meta de la versión (RV‑17)

Una sola meta para toda Sílice: `scripts/meta_silice.py --version 0.6.0 --hasta S1‑n` (no hay `meta_s1.py`).
Para S1 comprueba, hasta la fase `n`:

- **presencia** en la ERS de UC‑17, UC‑18, RF‑64…RF‑71 y RNF‑14 (no conteos absolutos, REQ‑19);
- cero pruebas omitidas;
- en SL‑E1, SL‑E2, SL‑E3 y cada intérprete del adaptador, el commit de la prueba es anterior al de la
  implementación;
- `git diff v0.5.0..HEAD -- core/contracts/` vacío;
- `git diff v0.5.0..HEAD` vacío sobre los archivos de las pruebas de regresión (§9.2);
- la guardia de red de `tests/conftest.py` está activa;
- desde S1‑0, las cuatro memorias de §9.1 y `FUENTE.md` existen y su commit es anterior al del código que
  prueban.

---

## 10. Tareas por fase

**Integración (RV‑2).** `main` es la única rama de integración. Cada fase se construye en una **rama corta**
que sale del `main` del momento, abre un PR contra `main` y se fusiona al cruzar **su** compuerta de fase, no
al final de la versión; lo inconcluso queda fuera de la navegación, para que `main` siempre se pueda publicar.
Separación de la guardia M9: una rama de núcleo toca solo `core/`, `migraciones/`, `tests/` y `docs/`; una de
interfaz, `ui/`, `tests/` y `docs/`. Nombres: `inc/silice-s1-<fase>-nucleo` e `inc/silice-s1-<fase>-ui`.

- **Primero, S5‑1 adelantado** (Alembic, respaldo, `preparar_base`, casos en carpeta; spec S5) y el PR temprano
  «dependencias Sílice» (`pyproject.toml` + `uv.lock`, con `xlrd` en el extra `bcv`).
- **Un solo carril de núcleo abierto a la vez:** S1‑1 → S1‑3 → S1‑4 (después siguen S2‑1…S2‑3 y S3‑2). Nunca
  dos ramas de núcleo abiertas; la de interfaz de una fase sale de `main` después de fusionar su núcleo.
- **Carril paralelo sin núcleo:** S1‑2 en `inc/silice-s1-bcv` (solo `adapters/bcv/`, `tests/`, `docs/`). Sale
  de `main` **sin commits de núcleo pendientes**, nunca de una rama de núcleo: `_ramas_adaptador`
  (`scripts/meta_alpha.py`) trata toda rama fusionada que agrega archivos bajo `adapters/` como un dominio
  nuevo y falla si su rango cambia `core/` (ARQ‑H5). Puede adelantarse, pero se fusiona al cruzar GS1‑2.
- Como mucho **tres worktrees vivos** (enmienda propuesta a NORMAS §3, RV‑2). `CHANGELOG.md` con
  `[Sin publicar]` y una línea por PR. Las etiquetas (`v0.6.0`) se ponen en `main`.

| Fase | Tareas (archivos, interfaces, pruebas) | Funciona al cerrar | Compuerta |
|---|---|---|---|
| **S1‑0** (rama de documentos desde `main`) | 0.1 enmiendas a ERS (UC‑17, UC‑18, RF‑64…71 citando la numeración del maestro §9, RNF‑14; la nota de UC‑09 la enmienda S4.0), modelo de datos §2.5, arquitectura, plan de pruebas §8 y §9. 0.2 descargar los archivos reales del BCV (curl en Windows entra; antecedentes §6), versionarlos con `FUENTE.md` **con la transcripción a mano de §9.3** y escribir `docs/fuentes/bcv_formatos.md` (hojas, etiquetas, celdas, letra del trimestre, marca de provisional). 0.3 licencia de `xlrd`. 0.4 lista MaPreX en Bs (§6.2) con `scripts/lista_maprex_bs.py`. 0.5 las **cuatro** memorias de §9.1 (con `s1_reajuste_por_partida.md`). 0.6 la parte de S1 de `scripts/meta_silice.py` (§9.4). 0.7 verificar la columna Estado de `ui.hoja` con `origen_ids` de partidas | documentos y memorias aprobados | GS1‑0 |
| **S1‑1** núcleo (`inc/silice-s1-1-nucleo`, después de fusionar S5‑1) | SL‑E1: revisión de Alembic de S1 y tablas de §5.2 (primeras cinco) en `core/models/moneda.py`; `core/catalog/indices.py`, `core/catalog/moneda.py`, `core/budget/moneda.py`; `guardar_presupuesto` rechaza monedas distintas; `MOTIVOS_VERSION` + `conversion`; `OBJETOS` + `moneda`. Pruebas: `tests/unit/test_moneda.py`, `tests/integration/test_conversion_version.py`, `test_indices.py`, bases anteriores | convertir la clínica a Bs y ver la erosión | GS1‑1 |
| **S1‑2** adaptador (`inc/silice-s1-bcv`, carril paralelo) | `adapters/bcv/`: `libro.py`, `tasa.py`, `inpc.py`, `insumos_construccion.py` (o CSV canónico), `informe.py`; el extra `bcv` ya llegó con el PR de dependencias. Pruebas: `tests/unit/adapters/test_bcv_*.py` sobre el archivo real y sobre cuadrículas | importar el trimestre real y el INPC | GS1‑2 |
| **S1‑3** núcleo + interfaz (`inc/silice-s1-3-nucleo`; luego `inc/silice-s1-3-ui` desde `main`, con S1‑2 ya fusionado) | SL‑E2: `lista_empresa` (con `empresa_nombre` y `empresa_rif`), `core/catalog/empresa.py`, lector con columnas opcionales, `lista_vigente`, `core/verification/precios.py`, `instantanea_precios`. Interfaz: `ui/indices.py`, páginas Índices y Precios de la empresa, Parámetros y Precios de `ui.hoja`. Pruebas: memoria de precios de empresa, AppTest de las páginas | una empresa con su lista auditada | GS1‑3 |
| **S1‑4** núcleo + interfaz (`inc/silice-s1-4-nucleo`; luego `inc/silice-s1-4-ui`) | SL‑E3: cláusula, `core/budget/reajuste.py`, estudio (lo ejecutado a mano, §8.6). Interfaz: `ui/reajuste.py`, página Reajuste, exportación. Pruebas: las dos memorias de reajuste, fronteras (con 3f), RNF‑14 | un proyecto en Bs y otro en USD con su reajuste lado a lado | GS1‑4 |
| **S1‑5** cierre (rama corta desde `main`) | `pyproject.toml` 0.6.0; `CHANGELOG.md` pasa `[Sin publicar]` a `[0.6.0]`; etiqueta `v0.6.0` en `main`; **base de prueba de la 0.6.0** generada en esta compuerta con su ficha (total literal, huella del informe, filas por tabla, escrita con el código de la etiqueta; RV‑3, PRU‑H15); manuales; recorridos guiados con las páginas nuevas; `meta_silice.py --version 0.6.0 --hasta S1‑5` en OK; CI verde en Linux y Windows; aprobación de los cuatro encargos | versión 0.6.0 | GS1 |

**Si el tiempo aprieta**, cae primero el intérprete del índice de la construcción (queda el CSV canónico,
§7.3), luego la erosión por índice (queda la cambiaria). La moneda, la lista de empresa con R11 y R12, la tasa
y el reajuste lado a lado no se recortan: son el criterio de éxito de la 0.6.0.

---

## 11. Expedientes de `core/` (resumen; el texto completo va en `docs/bitacora/2026-10-silice-s1-expedientes.md`)

| Exp. | Regla que lo motiva | Por qué es genérico | Prueba que lo demuestra | Impacto | Costo si es erróneo |
|---|---|---|---|---|---|
| **SL‑E1** moneda, tasa, origen por precio, conversión, erosión | H‑D1, RF‑64 a RF‑66; hoy un precio no dice su fecha ni su moneda original y nada impide mezclar monedas | todo presupuesto tiene moneda y todo precio una fecha, en cualquier dominio | memoria de conversión; homogeneidad del total convertido; rechazo de monedas mezcladas; bases anteriores abren | tablas aditivas en `core/models/moneda.py` con su revisión de Alembic; `guardar_presupuesto` gana una validación que ningún dato existente incumple (todo es USD); dos constantes ganan un valor | si se prefiere convertir solo al presentar, se retira `convertir_version` y la moneda del proyecto pasa a ser una preferencia de vista (H‑D1 queda a medias) |
| **SL‑E2** lista de empresa, R11, R12 | H‑D8, RF‑67, RF‑68; una lista global de empresa secuestraría `lista_vigente` | cualquier empresa de cualquier especialidad tiene precios propios que envejecen | memoria de precios de empresa con conjunto exacto y fronteras; `lista_vigente` | `lista_vigente` excluye un alcance más; lector acepta columnas opcionales; R11/R12 fuera de `REGLAS` | si R11/R12 debieran estar en `REGLAS`, se reanclan las huellas de RNF‑04 con ruling; si el rango o el plazo son malos, son parámetros por lista |
| **SL‑E3** reajuste | H‑D3, RF‑70, RF‑71; art. 133–134 (transcripción) | la ley aplica a obras y servicios de cualquier dominio; la estructura sale del `ResultadoAPU` | las dos memorias de reajuste (`declarada` y `por_partida`); fronteras del primer año y de 3f; recálculo exacto del estudio | módulo nuevo y tablas aditivas; no toca el motor ni las versiones | si la Gaceta o un experto cambian la fórmula, se cambia una función pura y su memoria; si cambian el primer año, un parámetro de la cláusula |

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
| S1‑R12 | `.xls` con `xlrd` (como el spec maestro §3) en el extra `bcv`, que entra en el instalador básico (RV‑24) | `python-calamine`; pedir al usuario que convierta a `.xlsx` | cambiar `libro.py`; la cuadrícula neutra aísla el resto |
| S1‑R13 | Archivos reales del BCV versionados en el repositorio privado como datos de prueba (`tests/fixtures/bcv/`) con su fuente, huella y `FUENTE.md` transcrito a mano; no van en el instalador (ratificada por Eugenio el 2026‑10‑11, P6) | archivos sintéticos | sin el archivo real se pierde la prueba del lector real |
| S1‑R14 | `R` no se aplica a la comprobación directa salvo que la cláusula lo declare | aplicarla siempre | comparación lado a lado sesgada |
| S1‑R15 | Monedas guardadas como `"Bs"` y `"USD"` (las palabras de H‑D1), no códigos ISO | código ISO del bolívar | renombrar un valor en datos nuevos; ninguna base existente tiene `"Bs"` |
| S1‑R16 | Desvío de R11 con una sola división y **sin cuantizar** antes de comparar; fronteras de la memoria construidas en la misma moneda y tasa (PRU‑H11) | cuantizar el desvío a 0,01 % antes de comparar | una frontera que pasa o falla por el dígito 28 de un cociente |
| S1‑R17 | Ejecutado por encima de lo presupuestado: se guarda con aviso y se reajusta sobre `min(Q, q)` (RV‑11, alineado con R13 y S2‑R8) | rechazarlo (versión 1 de este spec) | reajuste reclamado sobre obra no aprobada, o un estudio imposible de guardar con datos reales |
| S1‑R18 | Desde la 0.7.0, cada valuación registrada no anulada entra entera en el período que contiene su *hasta* (RV‑11, RV‑18) | prorratear por días | hasta un mes de desfase en lo ejecutado de una valuación que cruza el cierre |
| S1‑R19 | Porcentaje de erosión = `1 − T0/T1` (sobre el valor a la fecha del precio), el mismo en las dos monedas | erosión en Bs sobre `P` | mostrar 35,81 % donde la pérdida de valor es 26,37 % |
| S1‑R20 | Con `ambos`, el monto reconocido es el del `mecanismo_pagadero` que declara la cláusula; si no lo declara, la escalatoria, y la comprobación queda como referencia (cierra la pregunta 10 de S2) | reconocer el mayor o el menor de los dos | un reajuste reconocido que el contrato no paga; se corrige un campo de la cláusula |
| S1‑R21 | El estudio de un mes en curso se guarda «parcial al corte» y se reemplaza al cerrar el mes con una fila nueva (`reemplaza_a`), solo‑agregar (cierra la pregunta 10 de S2) | prohibir guardar antes del cierre | sin él, el PE proyectado de S2 no vería el reajuste del mes en curso; con él, dos estudios del mismo mes que hay que no sumar dos veces |

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
| Solapamiento con S2 (ejecutado) y S3 (empresa) | resuelto por RV‑11 y RV‑6: puente de §8.6 (a mano en 0.6.0, valuaciones registradas no anuladas citadas en 0.7.0) y empresa como texto que S3 rellena (§6.1); con Alembic desde la 0.6.0, la cita a la valuación es una revisión más |
| Conflictos al integrar con S2 y S3 (mismos archivos de núcleo) | carril único de núcleo, ramas cortas por fase contra `main`, tablas en `core/models/moneda.py` y reglas de arquitectura en su propio archivo (§10, RV‑2) |
| Precisión de los cocientes en `DecimalExacto` (texto de 40 caracteres) | contexto de 28 dígitos fijo; prueba de ida y vuelta de almacenamiento con los valores más largos de las memorias |

---

## 14. Preguntas abiertas

Las preguntas que dependen de Eugenio, del tutor o de un experto se llevan a la lista única del **spec maestro
§10** (preguntas P1…P9 en §10.3; parámetros que pueden decidirse después en §10.4) y se responden allí; aquí
quedan para la trazabilidad. Mientras no haya respuesta, rige el valor por defecto.

1. ~~Numeración de UC‑09.~~ **Cerrada:** la resolvió el spec maestro §9 (UC‑09 usa RF‑32 y RF‑90…95; RF‑64
   pasa a S1); la enmienda de la nota en la ERS la aplica S4.0 (RV‑26, REQ‑16, HEC‑7).
2. ¿Tasa de **compra o venta** para convertir (S1‑R1)? → parámetro con valor por defecto (venta), spec maestro §10.4.
3. ¿Desde qué fecha corre el **primer año** del art. 134: firma, inicio o acta de inicio (a cotejar)? →
   normativa a cotejar, spec maestro §10.4.
4. ¿Qué significan `R` y `Km` en la fórmula del INDICIO, y qué índice del BCV va con cada componente
   (productor o mayorista; general o por grupo)? Hace falta un experto o el documento con autor. →
   normativa a cotejar, spec maestro §10.4.
5. ~~Empresa.~~ **Cerrada por RV‑6** (ratificada por Eugenio el 2026‑10‑11, pregunta P1 del spec
   maestro §10.3): una empresa propia por instalación; la lista guarda `empresa_nombre` y `empresa_rif` como
   texto, que S3 rellena desde la empresa propia; no hay texto que migrar (§6.1).
6. ~~Lo ejecutado del período.~~ **Cerrada por RV‑11** (y RV‑18, decidida por Eugenio el 2026‑10‑11 en la
   pregunta P3 del spec maestro §10.3: todas las registradas, sin conformación): a mano en la 0.6.0; desde la
   0.7.0 el estudio cita las valuaciones registradas no anuladas, asignadas
   por su fecha *hasta*; criterio en RF‑71 y entrega en RF‑72 de S2 (§8.6).
7. ¿Se aceptan el rango de R11 (−20 % / +30 %) y el plazo de R12 (30 días) como supuestos por defecto, o
   Eugenio prefiere otros? → parámetros con valor por defecto, spec maestro §10.4.
8. ~~Redistribución de los archivos del BCV.~~ **Cerrada:** ratificada por Eugenio el 2026‑10‑11 (pregunta P6
   del spec maestro §10.3): los `.xls` se versionan en el repositorio privado como *fixtures* de prueba
   (`tests/fixtures/bcv/`) con `FUENTE.md` transcrito a mano, que sigue siendo el oráculo (§9.3); no van en el
   instalador, cada empresa descarga los suyos (S1‑R13).
9. ¿Se marca algo (más que una nota) cuando las variaciones superan el 10 % del monto original, una vez
   confirmado el artículo de la Comisión de Contrataciones? → normativa a cotejar, spec maestro §10.4.
