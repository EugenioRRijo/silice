# «Auditar un presupuesto» (Fase 1 del pedido de la empresa): diseño

**Fecha:** 2026-10-25 · **Rama:** `inc/ruta-s2-mig-adm-empresa` (árbol `.worktrees/s2madm`) · **Estado:** PROPUESTO (por aprobar por Eugenio).
**Origen:** reunión con la empresa (2026-10-25), sesión de diseño con Eugenio el mismo día (maqueta del informe aprobada: «me gusta
como se ve»), recorrido con Playwright `docs/bitacora/2026-10-25-recorrido-ux-playwright.md`. Diseño hermano:
`2026-10-25-barra-superior-design.md` (va antes; esta pantalla vive bajo su área «Auditar»).

## 1. Intención

La empresa intentó **subir un Excel y no logró auditar**. El trabajo diario de la empresa es montar y revisar presupuestos; el
centro de Sílice es auditar. Sus cinco pedidos (reunión 2026-10-25):
1. aceptar **cualquier archivo** de presupuesto;
2. «Libro de la empresa» fuera del menú, como **contexto opcional** dentro de la auditoría;
3. **una sola vista** de trabajo;
4. auditar directo, con los APU en segundo plano, y un **informe accionable**;
5. elegir el **caso y el dominio automáticamente**.

Hoy el camino solo funciona con la plantilla ARENAZA: el lector toma columnas **por letra fija** del perfil
(`adapters/hoja_empresa/lector.py:497-505`, `perfiles/arenaza.json:74-75`) y exige la hoja PRESUPUESTO (`:731-736`). Hay un segundo
lector, distinto e incompatible («Revisar › Presupuesto en Excel», formato UC-05 con hoja `Datos`,
`core/budget/importacion.py:81-118`). Un `.xlsx` ajeno da 422; un `.csv` se rechaza por extensión; el libro limpio de prueba da
solo dos avisos «no aplicable», sin impacto en Bs ni nada que hacer con ellos.

## 2. Metas, no-metas y anti-metas

**Metas**
1. M1: **dos pasos**: soltar el archivo → leer el informe. Sin elegir antes carpeta, dominio, plantilla ni fecha.
2. M2: lee **Excel (`.xlsx`) y CSV de cualquier forma razonable** (cualquier hoja, títulos en cualquier fila, columnas en cualquier
   orden y con sus nombres habituales); la plantilla ARENAZA y el formato UC-05 siguen leyéndose con sus lectores ricos.
3. M3: si no reconoce las columnas, **un paso extra**: la persona señala qué columna es cuál y Sílice lo **recuerda** para los
   archivos de la misma forma.
4. M4: auditoría **determinista** (aritmética, subtotales, total, unidades, precio fuera de rango solo con referencia, cobertura).
5. M5: **informe accionable**: cuatro cifras, tabla ordenada por impacto en dinero, «cómo corregirlo» y dónde (fila y columna),
   descarga **PDF** y **Excel marcado**; contexto, controles que no aplicaron y auditorías anteriores plegados (maqueta aprobada).
6. M6: dominio y caso elegidos solos, **visibles y cambiables** en «Contexto».
7. M7: **ninguna pantalla se retira**: «Libro de la empresa» pasa a llamarse «Auditar un presupuesto» (misma ruta `#/libros`) y
   «Revisar › Presupuesto en Excel» usa el mismo despachador.

**No-metas (Fase 1):** IA de ningún tipo (decisión de Eugenio, 2026-10-25: «sin IA por ahora»); PDF, Word o imágenes como entrada
(Fase 3); emparejamiento de partidas compuestas con APU de referencia (Fase 2); `.xls` (ver §10 D-A5); tocar `core/`; guardar el
archivo de la empresa (se guarda la auditoría, nunca el Excel).

**Anti-metas:** que una cifra la invente una IA o una heurística opaca; marcar como **error** algo que solo «no tiene referencia»;
que el informe parezca completo cuando la cobertura es baja (la cobertura se muestra siempre); un `float` en dinero; perder la
auditoría rica de la plantilla ARENAZA; que un archivo malicioso salga del tope o ejecute algo; que el Excel marcado propague
fórmulas peligrosas (inyección CSV/fórmula).

## 3. Restricciones y hechos del código

- `core/` intacto (B1). Llamar funciones de `core/` está permitido; modificarlas no.
- Dinero y cantidades en `Decimal`, como texto en la API; la interfaz no calcula (B3).
- Subida segura: `adapters/hoja_empresa/guardia.py` (solo `.xlsx`, 25 MiB, topes de ZIP, celdas combinadas y declaradas) y
  `api/archivos.py`; 422 sin eco (`api/sin_eco.py`).
- Auditoría rica de ARENAZA: `POST /v1/libros/auditoria` → `fusion/proceso.py::procesar_libro` (F1 P.U. recalculado con impacto,
  R1-R7 del núcleo, L1-L9 del libro, L10/L11 PDF). Su impacto está en la moneda del libro.
- Hallazgo del núcleo: `core/contracts/verificacion.py:22` (regla, `Severidad`, descripción, `impacto: Decimal|None`, `origen_ids`
  `"HOJA!REF"`, observado, esperado); fila de tabla `FilaHallazgo` (`adapters/hoja_empresa/modelo.py:326`).
- Referencias MaPreX: `data/precios/maprex_2026-07/referencia_{civil,industrial,sistemas,telecom}.csv`, **111 filas de insumos**
  (37/13/43/18), no partidas; banda de R11 −20 %/+30 % (`core/catalog/empresa.py:34-35`); hoy **no existe** emparejamiento entre
  una partida de un libro y MaPreX (`fusion/proceso.py:110` `MOTIVO_R11`).
- `Dominio` (`core/contracts/dominio.py:6`): CIVIL, TELECOM, INDUSTRIAL, SISTEMAS. Hoy nada lo deduce (UC-05 lo lee; la fusión lo
  fija en CIVIL, `fusion/mapeo.py:456`).
- Salidas: no hay PDF de informes en la aplicación (`reportlab` es el extra `informes`, solo en `scripts/`); el Excel marcado de
  ARENAZA es `POST /v1/libros/devolucion` (XlsxWriter, depende del perfil).
- Historial: `GET /v1/auditorias-libro` y la pantalla `historial` (solo lectura).
- Front: `src/paginas/libros/index.tsx` monta `src/visor/Visor.tsx` (solo `.xlsx`, réplica Univer + halos + lista de hallazgos).

## 4. Lo que decidió Eugenio

- Sin IA por ahora; Fase 1 determinista con Excel y CSV.
- No retirar pantallas; adaptarlas.
- La maqueta del informe, tal como se vio (cuatro cifras, tabla por impacto, PDF y Excel marcado, contexto/controles/historial
  plegados).
- Pantalla bajo la barra superior opción C.

## 5. El flujo

```
 [Auditar un presupuesto]
   1. Suelta el archivo (.xlsx o .csv)  ──▶  despachador (§6.1)
        ├─ plantilla de la empresa (perfil ARENAZA)  → auditoría rica actual (fusion) + capas genéricas
        ├─ formato UC-05 (hoja «Datos»)              → lector UC-05 actual + auditoría del núcleo
        ├─ forma recordada (mapeo guardado)          → lector genérico con ese mapeo
        ├─ forma reconocida (confianza suficiente)   → lector genérico
        └─ no reconocida                              → paso extra: «Indique las columnas» (§6.3) → se recuerda
   2. Lee el informe (§7)
```

- La auditoría corre en el servidor al subir. Para archivos dentro de los topes se responde en una sola petición; la pantalla
  muestra «Leyendo… / Auditando…» con el esqueleto de Carbon. (Una cola de trabajos queda fuera: §10 D-A7.)
- Lo que Sílice entendió del archivo (hoja, fila de títulos, columna de cada campo, partidas leídas, moneda, dominio y su
  confianza) aparece en «Contexto usado», plegado, con «Corregir la lectura» que lleva al paso de columnas.

## 6. Lectura

### 6.1 Despachador (`aplicacion/auditar_presupuesto.py`)

Orden fijo y determinista; el primero que acepta gana y queda escrito en el informe («Leído como: plantilla de la empresa»):
1. **Plantilla de la empresa**: el perfil `arenaza` encuentra la hoja PRESUPUESTO y su fila de títulos (`_fila_encabezado`) → se usa
   el camino actual de `fusion/proceso.py` sin cambios, y además las comprobaciones genéricas que no dupliquen las suyas (§7.1).
2. **UC-05**: hay hoja `Datos` con las claves de `importacion.py` → `leer_presupuesto_tabular` + `auditar(...)` del núcleo.
3. **Forma recordada**: la firma de la forma (§6.3) coincide con un mapeo guardado.
4. **Lector genérico** (§6.2) con confianza suficiente.
5. Si nada alcanza: paso de columnas.

### 6.2 Lector genérico (`adapters/presupuesto_generico/`)

Paquete nuevo en `adapters/` (no importa `api`, `ui`, `scripts`; no modifica `core`). Entradas:
- `.xlsx`: tras `guardia.verificar_archivo`; openpyxl dos veces (valores guardados y fórmulas), como el lector actual.
- `.csv`: tope de 20 MiB y de 20 000 filas; codificación UTF-8 (con o sin BOM) y, si falla, Windows-1252; separador detectado
  entre `;`, `,` y tabulador (el que da columnas consistentes en las primeras 50 filas).

Detección (todo determinista y explicable):
- **Hoja**: la que tenga la fila de títulos de mayor puntaje; empate → la primera.
- **Fila de títulos**: entre las primeras 40 filas, la que más celdas de texto coincidan con el diccionario de sinónimos.
- **Diccionario de sinónimos** (archivo de datos versionado, sin tildes ni mayúsculas al comparar): `codigo` (código, cód., item,
  ítem, partida, renglón, nº, n°, no., part.), `descripcion` (descripción, concepto, designación, actividad, detalle), `unidad`
  (unidad, und, ud, u., u/m, unid.), `cantidad` (cantidad, cant., metrado, cómputo, computo), `precio_unitario` (precio unitario,
  p.u., pu, costo unitario, precio unit., p. unitario), `total` (total, monto, importe, precio total, parcial, subtotal de la
  partida). El implementador lo amplía con los libros ficticios; cada sinónimo nuevo con su prueba.
- **Confianza**: alta si se reconocen `descripcion` y al menos dos de `cantidad`, `precio_unitario`, `total`; si no, paso de
  columnas.
- **Filas**: una partida es una fila con descripción de texto y al menos un número entre cantidad, precio y total. Filas de
  **capítulo** (texto sin números, o código de un nivel), **subtotal** y **total** (texto «subtotal», «total», «sub-total»,
  «total general», «IVA», o fórmula `SUM(` sobre filas de partidas) se clasifican aparte.
- **Números**: celdas numéricas → `Decimal(str(v))`. Celdas de texto con número: formato es-VE (`1.234,56`) o anglosajón
  (`1,234.56`) decidido **por columna** según el patrón mayoritario; si la columna es ambigua, se informa («Números con formato
  dudoso») y se ofrece el paso de columnas.
- **Moneda**: de los títulos y celdas cercanas (`Bs`, `Bs.`, `VES`, `USD`, `US$`, `$`); si no se halla, **Bs por omisión** y se dice
  en «Contexto», cambiable.
- Cada valor conserva su **celda de origen** (hoja, fila, columna) para «Dónde» y para el Excel marcado.

Modelo de salida (`adapters/presupuesto_generico/modelo.py`, `dataclass(frozen=True)`): `PresupuestoLeido` (archivo, hoja, fila de
títulos, mapeo usado, moneda, partidas, capítulos, subtotales, totales, avisos de lectura) y `PartidaGenerica` (fila, código,
descripción, unidad, cantidad, precio unitario, total —cada uno `Decimal|str|None` con su `Celda`—, capítulo).

### 6.3 Paso de columnas y forma recordada

- Pantalla: las primeras 15 filas de la hoja elegida en una tabla densa; encima, un desplegable por campo (descripción, cantidad,
  precio unitario, total, y opcionales código y unidad) con las columnas reconocidas preseleccionadas; selector de hoja y de fila de
  títulos; **formato de los números** (`1.234,56` o `1,234.56`, preseleccionado el detectado) y **moneda** (Bs o USD).
  «Auditar con estas columnas».
- Firma de la forma: huella SHA-256 del nombre de la hoja y los textos normalizados de la fila de títulos. Lo recordado incluye el
  mapeo, el formato de los números y la moneda, así que un archivo con números dudosos (fixture (e)) no vuelve a pedir el paso.
- Se guarda en `instalacion.db` (tabla nueva `forma_de_presupuesto`: firma, mapeo JSON, quién y cuándo; migración `ins_000N` con
  su prueba), porque es saber de la instalación, no de una carpeta. Se puede borrar desde «Contexto» («Olvidar esta forma»).

## 7. Auditoría

Módulo `aplicacion/auditar_presupuesto.py` (sin Streamlit, sin `api`), con reglas puras sobre `PresupuestoLeido` que emiten
`core.contracts.Hallazgo` (se reutiliza el contrato; el código de regla nuevo es `G1`…`G8`).

### 7.1 Comprobaciones (deterministas)

| Código | Qué comprueba | Severidad | Impacto (en la moneda del archivo) | «Cómo corregirlo» |
|---|---|---|---|---|
| G1 | cantidad × precio unitario = total de la fila, redondeando a céntimos (`ROUND_HALF_UP`) | ERROR si difiere más de 0,01 | total del archivo − cantidad × P.U. | «Revise la cantidad, el precio o el total: uno de los tres está mal.» |
| G2 | subtotal de capítulo = suma de los totales de sus partidas (tal como están escritos) | ERROR | subtotal escrito − suma | «Falta o sobra una partida en la fórmula del subtotal.» |
| G3 | total general = suma de subtotales (o de partidas si no hay capítulos), más IVA si se detecta | ERROR | total escrito − suma | ídem |
| G4 | unidad reconocida (normalizada: `m2`/`m²`/`M2` → `m²`, etc., con la tabla de unidades del núcleo si existe; si no, una propia en `adapters/`) | ADVERTENCIA si no se reconoce | — | «Escriba una unidad reconocible (m, m², m³, kg, u, …).» |
| G5 | cantidad o precio vacío, cero o negativo en una partida | ADVERTENCIA | — | «Complete la cantidad y el precio.» |
| G6 | número guardado como texto o con formato dudoso | INFORMACIÓN | — | «Convierta la celda a número.» |
| G7 | código de partida repetido | ADVERTENCIA | — | «Use un código distinto por partida.» |
| G8 | **precio fuera de rango frente a MaPreX**, solo a nivel de **insumo** (§7.2) | ADVERTENCIA si sale de −20 %/+30 % | (precio − referencia) × cantidad, **mostrado pero no sumado** a «Diferencia por corregir» | «Justifique el precio o ajústelo a la referencia (MaPreX <mes> <año>, <insumo>).» |
| G9 | **precio distinto al de la empresa** (§7.4), partida con partida | ADVERTENCIA si sale de −20 %/+30 % | (P.U. − P.U. de la empresa) × cantidad, mostrado y no sumado | «Justifique el precio o ajústelo al de la empresa (<archivo>, <fecha>).» |

- Severidades con los nombres del núcleo (`Severidad.INFO`, `ADVERTENCIA`, `ERROR`); «Cómo corregirlo» y la celda (hoja, fila,
  columna) van en un envoltorio propio fuera de `core/` (`HallazgoDePresupuesto`: el `Hallazgo` del núcleo + `como_corregir` +
  `celda`), porque el contrato del núcleo no tiene esos campos.
- **Qué se suma a «Diferencia por corregir»**: solo los errores aritméticos, que son ciertos (G1-G3; con la plantilla, F1/L4/L9;
  con UC-05, G1-G3). Las desviaciones de precio (G8) son **a justificar**, no errores: se muestran con su monto en la tabla y en una
  cifra aparte dentro de «Contexto usado» («Precios por justificar: Bs …»), pero no inflan la cifra principal.
- **Qué se suma a cada formato**: con la plantilla de la empresa se conservan **todas** sus reglas actuales y se agregan G4-G8
  (G1-G3 los cubren F1/L4/L9); con UC-05 se conservan sus reglas del núcleo y se agregan G1-G8 (las R1-R7 no aportan a la
  «Diferencia por corregir»: no son aritmética del archivo); con el lector genérico, G1-G8; G9 en los tres si hay referencia de la empresa. «Partidas con algo que corregir» =
  partidas distintas con al menos un ERROR o ADVERTENCIA.
- **Cobertura**: monto de las partidas con referencia ÷ monto total, siempre visible. Partida sin referencia = INFO «Sin
  referencia» con la frase «Nada que hacer si el precio está justificado». **Nunca** es error.

### 7.2 Emparejamiento con MaPreX (Fase 1, conservador)

Las 111 filas de MaPreX son **insumos**; el precio unitario de una partida compuesta (material + mano de obra + equipo +
administración y utilidad) no es comparable con el de un insumo y daría falsos positivos. Por eso, en Fase 1:
- **Plantilla de la empresa**: G8 corre sobre los **insumos de las hojas APU** (`InsumoLeido`), que sí son comparables. Es justo el
  mapeo que falta según `fusion/proceso.py:110` (`MOTIVO_R11`). El impacto de un insumo es (precio − referencia) × cantidad del
  insumo en el APU × cantidad de la partida.
- **Lector genérico y UC-05**: G8 corre solo si la fila **empareja** con una referencia y la descripción no es la de una partida
  compuesta. Se considera compuesta si contiene alguno de los marcadores de una lista versionada («suministro y colocación»,
  «construcción de», «instalación de», «suministro, transporte», «incluye», …). Ante la duda, no se compara.
- **Emparejar**: la descripción normalizada (sin tildes, minúsculas, sin signos) **contiene todas las palabras significativas** de
  la referencia y la unidad normalizada es **la misma**. Más de una coincidencia = ambiguo = «sin referencia». El hallazgo muestra
  la referencia usada para que una persona lo verifique. Mejorarlo es la Fase 2.

### 7.3 Dominio y caso automáticos

- **Dominio**: puntaje por dominio = palabras de las descripciones del presupuesto que aparecen en un vocabulario por dominio
  (construido de los CSV de referencia de MaPreX y del catálogo del núcleo por dominio; archivo de datos versionado). Gana el mayor;
  si la diferencia con el segundo es menor que un umbral, se informa «Dominio: civil (poco seguro)». Se muestra en «Contexto» y se
  cambia con un desplegable, lo que vuelve a auditar.
- **Precedencia de dominio y moneda**: (1) lo que la persona elige en «Contexto»; (2) lo **declarado en el proyecto abierto**
  (`POST /v1/proyectos` guarda dominio y moneda, `aplicacion/proyectos.py:104`); (3) lo deducido del archivo; (4) por omisión, Bs y
  el dominio de mayor puntaje. Si lo deducido contradice al proyecto, se avisa en «Contexto» («El archivo parece de telecomunicaciones
  y el proyecto es civil») sin cambiar nada solo. Con la plantilla de la empresa el dominio sigue fijo como hoy
  (`fusion/mapeo.py:456`): en Fase 1 no se toca `fusion/`; el selector de dominio en «Contexto» solo afecta a G8 y se rotula así.
- **Caso**: la auditoría se hace sobre la **carpeta de trabajo y el proyecto abiertos** en la barra superior; no exige proyecto.
  El front envía el código del proyecto abierto en el cuerpo (`proyecto`, opcional); la carpeta llega como hoy por la cookie
  (`caso_web`). «Sin proyecto» se muestra tal cual. (Elegir la carpeta por el contenido del archivo queda fuera: §10 D-A6.)

### 7.4 El libro de la empresa como referencia (decisión de Eugenio: «las dos»)

Eugenio decidió que el libro de la empresa cumple **dos papeles**: (1) es el formato que la empresa suele auditar y debe leerse
bien (§6.1-1, sin cambios), y (2) es una **referencia de precios propia** con la que comparar otros presupuestos. Pidió además
recomendaciones; las que siguen son las aceptadas en este diseño.

- **Se carga una vez y se guarda**, no se sube en cada auditoría: «Agregar el libro de la empresa como referencia» lee el libro con
  el lector actual (`leer_libro`, perfil `arenaza`) y guarda en la **carpeta de trabajo abierta** (la base del caso, junto a
  «Precios de la empresa» de `aplicacion/precios_empresa.py`): (a) los **insumos** de sus hojas APU (tipo, descripción, unidad,
  precio) como una lista de precios de alcance empresa, y (b) las **partidas** de su hoja PRESUPUESTO (código, descripción, unidad,
  P.U.) como «partidas de referencia de la empresa» (tabla nueva en la base del caso, migración con su prueba). Se guarda la fecha
  del libro (o la de carga, si el libro no la dice) y el nombre del archivo; **no** el archivo. Es dato real de la empresa: queda
  solo en ese equipo y nunca en el repositorio (los fixtures de prueba son ficticios).
- **G9: precio distinto al de la empresa**, comparación **partida con partida** (la ventaja frente a MaPreX, que solo tiene
  insumos): primero por **código exacto** (normalizado: sin espacios, mayúsculas); si no, por descripción + misma unidad con la
  regla prudente de §7.2 (ambiguo = sin comparar). Banda: la misma de R11 (−20 %/+30 %). ADVERTENCIA «a justificar», con impacto
  (P.U. − P.U. de la empresa) × cantidad, mostrado y **no sumado** a «Diferencia por corregir», igual que G8. G8 (MaPreX) sigue
  corriendo para los insumos.
- **La empresa manda sobre MaPreX** cuando ambas tienen referencia para la misma fila: el hallazgo muestra la de la empresa y la de
  MaPreX como dato. La **cobertura** cuenta una partida como «con referencia» si tiene cualquiera de las dos, y «Contexto usado»
  desglosa cuánto viene de cada fuente.
- **Vigencia**: si la referencia de la empresa tiene más de **90 días**, el informe lo dice en «Contexto usado» (misma idea que R12
  «precio vencido»).
- **Quitar o reemplazar**: «cambiar» carga un libro nuevo y reemplaza la referencia anterior (todo o nada); «quitar» la borra.
- Rutas: `POST /v1/referencia-empresa` (subir el libro; acción de editar precios de la empresa), `GET /v1/referencia-empresa`
  (resumen: fecha, archivo, n.º de insumos y partidas), `DELETE /v1/referencia-empresa`. Mismas guardias de subida que el libro.

## 8. Informe y salidas

### 8.1 Pantalla (la maqueta aprobada)

- Línea de archivo: nombre, hoja, partidas leídas, «Leído como …», hora.
- Cuatro cifras (montos como texto con el exacto accesible, formato es-VE): **Monto del presupuesto**, **Diferencia por corregir**
  (suma de |impacto| de G1-G3 y G8; con la plantilla, de F1/L4/L9 y G8), **Partidas con algo que corregir** (n de m), **Monto con
  precio de referencia** (%).
- Tabla «Qué corregir, de mayor a menor impacto»: Impacto, Partida (código y descripción), Qué pasa (etiqueta + frase con los
  números), Cómo corregirlo, Dónde (fila y columna). Orden: impacto absoluto descendente; sin impacto, por severidad y luego fila.
  Etiquetas de Carbon: rojo para ERROR, amarillo para ADVERTENCIA, gris para «Sin referencia»; **nunca solo color** (texto en la
  etiqueta). Sin morado.
- Plegados: **Contexto usado** (cómo se leyó, moneda, dominio, lista de referencia y fecha, libro de la empresa como contexto
  opcional, «Corregir la lectura», «Olvidar esta forma»), **Controles que no aplicaron** (los «no aplicable» y «no evaluados», que
  hoy ensucian la lista), **Auditorías anteriores de este proyecto**.
- Con la plantilla de la empresa se conserva además el visor actual (réplica Univer con halos) como «Ver la hoja con marcas»: no se
  retira nada.
- El «Libro de la empresa» como **contexto opcional** (§7.4): en «Contexto usado», «Referencia de la empresa: cargada el
  <fecha> · cambiar · quitar», o «Agregar el libro de la empresa como referencia» si aún no hay. Si no se agrega, la auditoría
  funciona igual.

### 8.2 PDF

`reportlab` (ya usado en `scripts/`; BSD; sin dependencias nativas). Pasa del extra `informes` a dependencia base **o** al perfil
del instalador (el implementador comprueba cuál y lo declara; prueba de que el instalador lo incluye). Contenido: portada mínima
(archivo, fecha, carpeta y proyecto, «Leído como»), las cuatro cifras, la tabla completa, cobertura y la nota de método («Auditoría
determinista; ninguna cifra fue generada por IA»). IBM Plex embebida si su licencia lo permite (OFL: sí).

### 8.3 Excel marcado

- `.xlsx` de entrada: copia con openpyxl del archivo **original** (se conserva el formato que openpyxl preserva; se declara que
  gráficos e imágenes pueden perderse), relleno de color suave en las celdas con hallazgo, un comentario por celda con «Qué pasa /
  Cómo corregirlo», y una hoja nueva **«AUDITORÍA»** con la tabla del informe.
- `.csv` de entrada: un `.xlsx` nuevo con la tabla leída, las mismas marcas y la hoja «AUDITORÍA».
- **Inyección de fórmulas**: todo texto escrito por Sílice que empiece por `=`, `+`, `-`, `@`, tabulador o retorno de carro se
  prefija con `'`.
- La plantilla de la empresa conserva su devolución actual (`/v1/libros/devolucion`).

### 8.4 Historial

Se guarda la auditoría (resumen, hallazgos, cobertura, «Leído como», firma de la forma), **nunca el archivo**, en el almacén
actual `auditoria_libro` de `instalacion.db` (`fusion/historial_modelo.py`), que sigue siendo **de la instalación entera** (no se
revierte RF-142/RNF-28). Migración de `instalacion.db`: `tipo` admite además `'presupuesto'` (hoy `CHECK tipo IN ('libro','pdf')`),
y dos columnas nuevas, opcionales: `carpeta` (el nombre de la carpeta de trabajo dentro de `casos/`, que la interfaz no deja
renombrar) y `proyecto` (código). «Auditorías anteriores de este proyecto» filtra por carpeta y proyecto; la pantalla «Historial de
auditorías» muestra todo, con un filtro por carpeta que arranca en la carpeta abierta.

## 9. API (nuevas; las actuales no cambian)

| Método y ruta | Acción | Hace |
|---|---|---|
| `POST /v1/auditar-presupuesto` | la de `POST /v1/libros/auditoria` | multipart `archivo` (+ `mapeo` JSON opcional, `dominio` opcional, `moneda` opcional); responde el informe o `409 {necesita_columnas: true, vista_previa}` |
| `POST /v1/auditar-presupuesto/pdf` | ídem | mismo cuerpo; devuelve el PDF |
| `POST /v1/auditar-presupuesto/excel` | ídem | mismo cuerpo; devuelve el Excel marcado |
| `DELETE /v1/formas-de-presupuesto/{firma}` | administrar o editar | olvida una forma recordada |

- Montos como texto; `no-store`; 422 sin eco; topes de `guardia`/CSV; acceso por la tabla `tests/unit/test_api_acceso_por_ruta.py`
  (compartido: orquestador); `docs/api.json` regenerado.
- «Revisar › Presupuesto en Excel» (`POST /v1/revision/excel-externo`, rol `REVISAR_PAQUETE`) pasa a llamar al despachador en
  **modo de solo lectura**: no escribe en el historial ni guarda formas (sigue «nada se guarda»), pero sí usa las formas ya
  recordadas. Responde con su forma actual (`total` = monto total leído del archivo; `hallazgos` en el formato del núcleo; el aviso
  «No verificado») más el campo aditivo `informe`. Si el archivo necesita el paso de columnas, responde el mismo 409 y la pestaña
  de Revisar muestra el mismo componente de columnas (AP-6), que en este modo no ofrece «recordar».
- Sin estado entre peticiones: PDF y Excel vuelven a leer y auditar el archivo (determinista, mismo resultado). Así no se guarda el
  archivo de la empresa.

## 10. Decisiones de ingeniería tomadas aquí (las ratifica Eugenio al leer)

- **D-A1** Lector genérico nuevo en `adapters/presupuesto_generico/`, en vez de forzar el perfil ARENAZA a ser flexible: el perfil
  sirve a una plantilla con APU y fórmulas que la auditoría rica necesita; lo genérico es otro problema.
- **D-A2** Despachador con orden fijo y el «Leído como» visible: determinista y explicable.
- **D-A3** Hallazgos sobre el contrato del núcleo (`Hallazgo`), reglas G1-G8 nuevas fuera de `core/`.
- **D-A4** Emparejamiento con MaPreX solo por todas las palabras + misma unidad, y ambiguo = sin referencia. Con 111 insumos, la
  mayoría de las partidas quedarán «sin referencia»; la cobertura lo dice. Es honesto; Fase 2 lo mejora.
- **D-A5** `.xls` fuera de la Fase 1: mensaje «Guárdelo como .xlsx (Archivo › Guardar como) y vuelva a subirlo». Motivo: no hay
  manera de construir fixtures ficticios `.xls` sin una librería de escritura sin mantenimiento; `xlrd` existe como extra (`bcv`) y
  puede sumarse en Fase 3.
- **D-A6** Caso = carpeta y proyecto abiertos (no se deduce del archivo).
- **D-A7** Una sola petición síncrona; sin cola de trabajos. Si el recorrido funcional mide más de 10 s con el archivo más grande
  dentro de los topes, se abre la cola como trabajo aparte.
- **D-A8** Moneda Bs por omisión si el archivo no la dice, visible y cambiable. Sin conversión Bs/USD en Fase 1 (el impacto va en la
  moneda del archivo).
- **D-A9** Formas recordadas en `instalacion.db`.
- **D-A10** PDF con `reportlab`; Excel marcado con openpyxl sobre la copia del original.
- **D-A11** Solo los errores aritméticos suman a «Diferencia por corregir»; las desviaciones de precio (G8, G9) son «a justificar»
  y van en su propia cifra.
- **D-A12** G8 con MaPreX solo a nivel de insumo (APU de la plantilla; filas no compuestas del lector genérico).
- **D-A13** Precedencia de dominio y moneda: elección en «Contexto» > proyecto abierto > archivo > omisión; con aviso si el archivo
  contradice al proyecto. `fusion/` no se toca en Fase 1.
- **D-A14** Historial en `instalacion.db` como hoy, con `carpeta` y `proyecto` opcionales y `tipo = 'presupuesto'`.
- **D-A15** «Revisar › Presupuesto en Excel» usa el despachador en modo de solo lectura (sin historial ni formas nuevas).
- **D-A16** La referencia de la empresa se guarda en la carpeta de trabajo, se compara partida con partida (G9) y manda sobre MaPreX;
  aviso a los 90 días.

## 11. Pruebas y aceptación

- **Fixtures ficticios nuevos** (`tests/fixtures/presupuestos_genericos.py`, construidos en memoria con openpyxl/XlsxWriter y
  `csv`; «Contratista Demo, C.A.»): (a) títulos en la fila 1, orden habitual; (b) títulos en la fila 8 bajo un membrete con
  celdas combinadas; (c) columnas en otro orden y nombres sinónimos («Concepto», «Metrado», «P.U.», «Importe»); (d) capítulos con
  subtotales `SUM(` y total con IVA; (e) números como texto es-VE; (f) CSV `;` con coma decimal en Windows-1252; (g) CSV `,` con
  punto decimal en UTF-8 con BOM; (h) una forma irreconocible (títulos en inglés raros) que obliga al paso de columnas; (i) cada
  error de G1-G8 sembrado en una fila conocida, con su impacto calculado **a mano** en la prueba.
- Unitarias por regla (oráculos a mano), por detector (hoja, fila de títulos, sinónimos, números, moneda, dominio), del
  despachador (cada rama, y que ARENAZA y UC-05 siguen dando exactamente sus hallazgos actuales: prueba de no regresión con
  `tests/fixtures/libros_empresa.py` y `presupuesto_tabular.py`), de la forma recordada (guardar, reconocer, olvidar), de la
  inyección de fórmulas en el Excel marcado, de los topes de CSV.
- API: forma de respuesta, 409 de columnas, acceso por rol, CSRF, sin eco, `no-store`, PDF y Excel válidos (se abren con
  openpyxl/pypdf en la prueba).
- Front (Vitest): soltar → informe; paso de columnas; orden por impacto; plegados; descarga; montos tal como vienen.
- **Recorrido funcional** (`--funcional` del diseño hermano §8.3): con cada fixture (a)-(h), soltar y comprobar las cuatro cifras
  esperadas. Medida: de 6 pasos y 2 decisiones hoy a 2 pasos y 0 decisiones (1 extra en (h)).
- Cierre: árbitro (A1-F1), revisor de diseño, `CHANGELOG.md`, ERS (RF nuevos por el orquestador), manual de usuario.

## 12. Sub-rebanadas y orden

| Rebanada | Hace | Depende de |
|---|---|---|
| AP-1 | Lector genérico, sinónimos, números, moneda, modelo; fixtures (a)-(h) | — |
| AP-2 | Reglas G1-G8, cobertura, emparejamiento MaPreX, dominio automático | AP-1 |
| AP-3 | Despachador (ARENAZA, UC-05, recordada, genérico) y formas recordadas (migración) | AP-1, AP-2 |
| AP-4 | API (§9) + «Revisar › Presupuesto en Excel» por el despachador | AP-3 |
| AP-5 | PDF y Excel marcado | AP-2 |
| AP-6 | Front: pantalla «Auditar un presupuesto», paso de columnas, informe, contexto | AP-4, barra superior hecha |
| AP-8 | Referencia de la empresa (§7.4): carga, tablas, G9, rutas, «Contexto» | AP-2, AP-3 |
| AP-7 | Recorrido funcional, manual, ERS, CHANGELOG | todas |

AP-1 y AP-5 pueden ir en paralelo con la barra superior (no comparten archivos). Cada rebanada: implementador → árbitro.

## 13. Lo que queda al constructor

Los sinónimos exactos más allá de la lista base; el umbral numérico de confianza del dominio; los textos finales de «Cómo
corregirlo» (con revisión de vocabulario del árbitro); el color exacto de las marcas del Excel (de la paleta de Carbon, sin morado);
la maquetación interna del PDF.
