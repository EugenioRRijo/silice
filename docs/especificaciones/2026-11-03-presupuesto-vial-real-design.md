# Lecciones de un presupuesto vial real revisado en local: diseño

**Fecha:** 2026-11-03 · **Rama:** `feature/disenos-f5` (árbol `.worktrees/s2m5`) · **Estado:** PROPUESTO (por aprobar por
Eugenio; lo que toca `core/`, además, por el tutor). **2026-11-06:** tareas 1 a 6 de §11 construidas en `feature/f5-vial`
con las decisiones provisionales de §13, a la espera de que Eugenio las ratifique; la tarea 0 (PR #100) sigue con el tutor.
**Origen:** un presupuesto vial de repavimentación con sus APU, entregado a Eugenio y revisado **solo en local** (el análisis
vive fuera del repositorio). Diseños de los que depende: `2026-10-30-vial-agregados-design.md` (especialidad vial) y
`2026-10-25-auditar-un-presupuesto-design.md` (auditar cualquier archivo). Plan vigente de lo vial:
`docs/planes/PLAN_VIAL_AGREGADOS.md`.

**Regla de datos (NORMAS §1).** Ningún nombre, cifra, código ni texto de aquel material entra al repositorio, tampoco
anonimizado ni derivado. Este documento describe **formas** («el transporte se mide en toneladas con la distancia en la
descripción»), nunca valores. Todo número que aparece aquí es un **ejemplo ficticio** escrito para este diseño, salvo los
que ya están en el código del repositorio y se citan con su archivo.

## 1. Intención

Lo vial de Sílice (tramos, VR1 a VR7, conciliación CV1 a CV3, costo propio de la mezcla) se construyó y se probó con una
vía ficticia (`data/samples/vial/via_ficticia.csv`). El primer presupuesto vial real que llegó, revisado en local, muestra
cinco lugares donde Sílice no lo leería o lo juzgaría mal. Este diseño propone qué hacer con cada uno, dónde viviría el
cambio y si toca el núcleo. Es un diseño: no se escribe código hasta que Eugenio lo apruebe.

Los cinco puntos:

1. **Desperdicio por material.** El APU real lo trae en cada renglón de material; Sílice no lo modela.
2. **VR4 con transporte por tramo de distancia.** El transporte se expresa en toneladas con la distancia como banda en la
   descripción; VR4 y CV2 esperan t·km y darían un falso ERROR.
3. **Partidas que faltan en el catálogo vial:** movilización de equipos, limpieza de la superficie, transporte del
   fresado, señalización y control de tránsito por día, ojos de gato y demarcación medida en m².
4. **Perfil de importación de un libro con un APU por hoja.**
5. **Alias de unidades** (tonelada y litro), ya preparados en la rama `feature/nucleo-alias-ton-litro` (PR #100),
   pendientes del tutor.

## 2. Metas, no-metas y anti-metas

**Metas**
- M1: que un libro con la forma del real (un APU por hoja, solo valores, desperdicio por renglón) se lea y cada precio
  unitario se recalcule y se compare con el impreso.
- M2: que una partida de transporte medida por banda de distancia no dé un ERROR falso, y que una banda que no cuadra con
  la distancia del tramo sí dé un hallazgo.
- M3: que las seis partidas que faltan existan en el catálogo vial, con código provisional, y las que salen de la
  geometría del tramo se deriven con su regla.
- M4: que cada punto diga si toca `core/` y, si lo toca, cuál es la alternativa fuera del núcleo.

**No-metas** (recomendaciones del análisis local que quedan para otro diseño): el FCAS de la empresa frente a la
calculadora de la Tarea 17; reglas de coherencia nuevas (descripciones que se contradicen, un equipo cobrado en dos
partidas); agrupar el presupuesto por frente de obra y parte; comparar dos revisiones del mismo presupuesto; riego y
pintura «con suministro» dentro del APU (VR3 y VR5 leyendo la dosis del insumo).

**Anti-metas** (fracasos aunque funcione)
- Un nombre, una cifra o un código del material real en el repositorio, en una prueba, una captura o un PR.
- Tocar `core/` sin el aval del tutor, o tocarlo cuando hay una alternativa fuera del núcleo que basta.
- «Arreglar» el libro de la empresa: el archivo original es prueba documental y nunca se modifica; Sílice lee, recalcula
  e informa.
- Un segundo lector de Excel que duplique la guardia y el modelo de `adapters/hoja_empresa/` (ruling RT-6 de
  `docs/planes/RUTA_SESIONES.md`).

## 3. Hechos del código que condicionan el diseño (leídos el 2026-11-03)

- `core/contracts/apu.py`: `LineaMaterial` tiene `descripcion`, `unidad`, `cantidad` y `precio`; su total es
  `cantidad × precio`. No hay desperdicio. NORMAS §5 declara estables los contratos: cambiarlos exige detenerse y
  documentarlo.
- `adapters/civil/reglas.py` ya modela el desperdicio **dentro de la cantidad**: `REGLA_TUBERIA = "longitud * (1 +
  desperdicio)"`. Igual `adapters/espacio/especialidades/agua.py` (constantes D-1 y D-2). Es el precedente: el desperdicio
  vive fuera del núcleo, en la regla que produce la cantidad.
- `adapters/vial/reglas.py`: VR4 es `_contra_derivado("VR4", "transporte_mezcla", …)`; compara la suma del presupuesto
  con `longitud × ancho × espesor × densidad × distancia` del tramo, por `origen_id` del renglón, con tolerancia
  relativa V-10 (0,005). VR7 marca ERROR si la unidad no es la de la partida derivada. Solo evalúan renglones con origen
  de tramo («tramo:T1:capa:3»).
- `aplicacion/conciliacion.py`: CV2 suma por **código de partida**, sin convertir unidades, la cantidad del presupuesto
  y la de los tramos.
- `adapters/vial/constantes.py`: `PARTIDAS_VIALES` tiene 15 claves con códigos provisionales y correlativos
  `C-000.000.001` a `C-000.000.015` (V-2: «a cotejar con el texto de la norma»).
- `adapters/hoja_empresa/perfil.py`: un perfil exige las 12 hojas lógicas de la plantilla conocida (`PORTADA` … `AUX`),
  identifica las hojas de APU por un prefijo y lee las líneas de un solo bloque con cinco columnas. El único perfil del
  paquete es `perfiles/arenaza.json`. Un libro con un APU por hoja y nada más no carga.
- `core/contracts/unidades.py` no conoce `ton`, `lt` ni `kgf`; una unidad desconocida se devuelve sin traducir (R3 la
  ve distinta). La rama `feature/nucleo-alias-ton-litro` (expediente NUC-E1) agrega `t` ← `ton`, `tn`, `tonelada(s)` y
  `l` ← `lt`, `lts`, `litro(s)`.

## 4. Punto 1: desperdicio por material

### 4.1 El problema

En el APU revisado en local cada material lleva un porcentaje de desperdicio y el costo del renglón es
`cantidad × (1 + desperdicio) × precio`. Sílice no tiene dónde ponerlo: si el importador copia la cantidad tal cual, el
precio unitario recalculado sale por debajo del impreso y CV1 marca una diferencia que no es error de la empresa.

Ejemplo ficticio: un riego con 0,50 l/m² de ligante y 4 % de desperdicio consume 0,52 l/m²; a un precio de 2,00 por
litro, el renglón vale 1,04 y no 1,00.

### 4.2 Opciones

| Opción | Pros | Contras |
|---|---|---|
| **A. Campo `desperdicio` en `LineaMaterial`** (contrato del núcleo, el motor lo aplica) | El concepto queda nombrado en el contrato; el APU guardado distingue cantidad neta y desperdicio; el motor es la única fuente del cálculo | **Toca `core/`**: contrato, motor, modelos persistidos (`LineaComposicionVersion`) y su migración. Cambia un contrato que NORMAS §5 declara estable. Exige aval del tutor, rama solo-core, TDD con rojo visto y expediente |
| **B. Desperdicio dentro de la cantidad, con traza** (el importador y Componer guardan `cantidad × (1 + desperdicio)`; la cantidad neta y el porcentaje van a una tabla aditiva de la base del caso) | **No toca `core/`**. Sigue el precedente de `adapters/civil` y `adapters/espacio`. El precio unitario recalculado cuadra con el impreso. La traza permite mostrar «0,50 + 4 %» | Dos datos (neta y porcentaje) viven fuera del APU del núcleo; quien edite la cantidad en la Hoja debe ver que ya incluye desperdicio. Una tabla y una migración nuevas en la base del caso |
| **C. Desperdicio en la descripción** («Ligante (incluye 4 % de desperdicio)») | Trivial | Frágil: R4 compara especificaciones, una edición de texto lo pierde; no se puede leer de vuelta con garantías |

### 4.3 Recomendación

**B ahora; A solo si el tutor quiere el concepto en el contrato.** Con B:

- `adapters/hoja_empresa/` lee el porcentaje del renglón; `fusion/mapeo.py` arma la `LineaMaterial` con la cantidad ya
  multiplicada (en `Decimal`, sin redondear) y devuelve, aparte, la traza `(línea, cantidad neta, desperdicio)`.
- `aplicacion/` guarda la traza en una tabla aditiva del caso (migración `caso_00NN`, regla SF3-E0 de tablas aditivas) y
  la ofrece a la Hoja y a Componer, que la muestran como «0,52 (0,50 + 4 %)».
- Componer acepta un desperdicio opcional por material; el backend calcula la cantidad (la interfaz no calcula montos).
- Si después se adopta A, la traza de B es exactamente lo que habría que migrar al campo nuevo: B no se tira.

**Toca `core/`:** B no; A sí (expediente propuesto NUC-E2, con el método de NUC-E1: la regla que lo motiva, por qué es
genérico, la prueba en rojo antes que la implementación, el impacto y el costo si es erróneo).

## 5. Punto 2: VR4 con transporte por tramo de distancia

### 5.1 El problema

El presupuesto revisado en local mide el transporte de mezcla **en toneladas** y escribe la distancia como una banda en la descripción
(«… distancia mayor de X km y hasta Y km»); la unidad escrita parece de t·km, pero la cantidad son toneladas. Sílice
espera t·km = toneladas × distancia. Cuando esa partida se casa con un tramo (porque se llevó desde los tramos o porque su
código es el de `transporte_mezcla`, que es como la encuentra CV2), VR4 y CV2 marcan ERROR por un factor igual a la
distancia, y VR7 marca la unidad si no es literalmente `t·km`.

Ejemplo ficticio: 120 t de mezcla, partida «transporte de mezcla, mayor de 8 km y hasta 10 km», cantidad 120. VR4 espera
120 × 9 = 1.080 t·km con un tramo a 9 km de la planta y marca ERROR; la partida está bien medida según su convención.

### 5.2 Opciones

| Opción | Pros | Contras |
|---|---|---|
| **A. Convertir al importar** (cantidad × distancia, unidad t·km) | VR4 queda igual | Cambia la cifra que escribió la empresa; el informe ya no cita lo que dice su libro; el precio unitario por tonelada deja de compararse |
| **B. Segunda convención en VR4**: la partida declara la banda (directiva `_tramo_km` con «mín-máx», puesta por el importador al leer la descripción o escrita por la persona) y VR4 compara toneladas, no t·km | Respeta el libro; reutiliza la derivación; el hallazgo dice qué convención usó | Leer la banda de la descripción necesita un patrón; una descripción que no lo siga queda sin banda (y se dice) |
| **C. Partida propia** `transporte_mezcla_banda` en `t`, con la banda como parámetro del tramo | VR7 y CV2 la tratan como cualquier partida en `t`; nada ambiguo | Una clave más; el tramo debe declarar qué convención usa la obra |

### 5.3 Recomendación

**B y C juntas**, todo en `adapters/vial/` y sin tocar el núcleo:

- `PARTIDAS_VIALES` gana `transporte_mezcla_banda` en `t` (código provisional correlativo).
- El tramo declara la convención de su obra (`t·km`, la de hoy y por defecto, o `banda`). Con `banda`, `derivar_tramos`
  produce la partida en `t` (= toneladas de la mezcla de la capa) en vez de la de t·km; VR7 y CV2 la tratan sin cambios.
- VR4 en modo banda: ERROR si las toneladas no cuadran (misma tolerancia V-10); **ADVERTENCIA** si la distancia del
  tramo (`distancia_planta_km`) cae fuera de la banda de la partida, con los dos números en el mensaje; INFO si la
  partida no declara banda («no evaluable: la descripción no dice la banda»).
- La banda se lee de la descripción con un patrón declarado en el perfil del importador (punto 4); si no coincide, no
  se adivina.
- Una unidad escrita de t·km con cantidad en toneladas no se «corrige»: el perfil la traduce a `t` y lo deja en la
  traza, y el informe lo dice (INFO).

**Toca `core/`:** no.

## 6. Punto 3: partidas que faltan en el catálogo vial

### 6.1 El problema

El presupuesto real tiene seis partidas que `PARTIDAS_VIALES` no conoce o conoce en otra unidad: movilización de equipos
(viaje), limpieza de la superficie antes del riego (m²), transporte del material fresado medido suelto (m³),
señalización y control de tránsito (día), ojos de gato (unidad) y demarcación de superficies como pasos peatonales y
líneas de pare (m², hoy solo existe la demarcación lineal en m). Sin clave, CV2 no puede conciliarlas y la Hoja no las
reconoce como viales.

### 6.2 Opciones

| Opción | Pros | Contras |
|---|---|---|
| **A. Solo catálogo**: seis claves nuevas en `PARTIDAS_VIALES`, sin derivación | Pequeño; la Hoja y la búsqueda las encuentran | CV2 no las concilia con nada; la cantidad va a mano |
| **B. Catálogo + derivación de las geométricas**: limpieza = área de la capa sobre la que se riega; transporte del fresado = volumen fresado × esponjamiento; demarcación de superficie = área declarada × número | VR7 y CV2 las cubren; cada cantidad tiene su regla (R1) | Hay que declarar datos nuevos en el tramo (esponjamiento, áreas) y cada constante necesita fuente |
| **C. Esperar a los códigos de la norma** | Nada provisional | Bloquea sin necesidad: los 15 códigos actuales ya son provisionales (V-2) |

### 6.3 Recomendación

**B para las tres geométricas, A para las otras tres**, con códigos provisionales correlativos desde
`C-000.000.016` (como V-2 hasta que el tutor coteje la norma):

| Clave propuesta | Unidad | Cantidad |
|---|---|---|
| `movilizacion_equipos` | viaje | a mano (no sale de la geometría) |
| `limpieza_superficie` | m2 | área de la capa de riego o imprimación (`longitud*ancho`) |
| `transporte_fresado` | m3 | volumen fresado × `esponjamiento` |
| `senalizacion_transito` | dia | a mano (sale del plazo, no del tramo) |
| `captafaros` | unidad | a mano, o el número que declare la línea de demarcación (ver abajo) |
| `demarcacion_superficie` | m2 | área declarada de cada elemento × número |

- **Esponjamiento sin valor por defecto.** Es un dato de la capa de fresado, obligatorio solo si se quiere la partida de
  transporte del fresado. Un valor por defecto necesitaría fuente; mientras no la haya, no se inventa.
- **Ojos de gato desde la separación:** sacar el número de la longitud y la separación pide dividir y redondear hacia
  arriba, y `derivar_tramos` hoy solo multiplica parámetros con nombre (así R1 compara la expresión con la cantidad). Por
  eso la primera versión toma el número que declara la línea; derivarlo de la separación es una extensión aparte (§10).
- **Variantes de medición** que el material real también muestra (fresado en m² con espesor declarado, colocación de la
  carpeta en t): quedan como pregunta (§10), no se agregan sin respuesta.

Dónde: `adapters/vial/constantes.py`, `modelo.py` (campos opcionales de `Capa` y un tipo de demarcación de superficie),
`derivacion.py`, `tabular.py` (columnas nuevas del CSV, opcionales: un CSV de hoy sigue leyéndose igual),
`aplicacion/consulta.py` (la lista de partidas viales sale de `PARTIDAS_VIALES` y crece sola), la pantalla de tramos
(`frontend-desktop/src/paginas/vial/`) y la vía ficticia de `data/samples/vial/`. Los APU de estas partidas los compone
la persona; si la demostración los quiere, con cifras ficticias declaradas.

**Toca `core/`:** no.

## 7. Punto 4: perfil de importación de un libro con un APU por hoja

### 7.1 El problema

El material real es la exportación de un programa de APU: **un libro por frente de obra con una hoja por partida**, sin
fórmulas (solo valores), y el presupuesto en otro libro, con el precio unitario tecleado y el número de renglón como
único enlace con la hoja de su APU. Cada hoja de APU tiene cabecera (descripción, unidad, cantidad, rendimiento) y tres
bloques con columnas distintas: materiales (con desperdicio), equipos (con coeficiente de depreciación o de uso) y mano de
obra (jornal y bono por separado); al pie, prestaciones como porcentaje, administración, utilidad e imprevistos en
cascada, financiamiento e impuestos. Hay renglones sin número correlativo: un lector que filtre por esa columna los pierde
y el precio unitario no cuadra.

El perfil de hoy (`perfiles/arenaza.json`) describe otra plantilla y exige sus 12 hojas: no sirve.

### 7.2 Opciones

| Opción | Pros | Contras |
|---|---|---|
| **A. Estirar el esquema del perfil actual** | Un solo tipo de perfil | El esquema actual es de una plantilla con 12 hojas y un bloque de líneas; meterle tres bloques con columnas distintas lo vuelve opcional en todo y debilita su validación |
| **B. Un tipo de perfil hermano en `adapters/hoja_empresa/`** (`apu_por_hoja`) con su lector, que produce el mismo `LibroLeido` / `ApuLeido` de `modelo.py` y usa la misma guardia | Una guardia, un modelo, las mismas celdas citables y el mismo camino a `fusion/`; respeta RT-6 | Un lector más que mantener; `ParametrosLibro` y `ApuLeido` necesitan campos opcionales nuevos (desperdicio por línea, bono, financiamiento) |
| **C. Un adaptador nuevo** (`adapters/apu_por_hoja/`) | Aislado | Duplica la guardia, el modelo y la lectura doble; contradice RT-6 |

### 7.3 Recomendación

**B.** Lo que hace el lector:

- Busca por **rótulos**, nunca por fila fija (causa C1 de `lector.py`), y lee los tres bloques por sus encabezados.
- **Lee todos los renglones de cada bloque**, tengan o no número correlativo.
- Prestaciones como porcentaje → `fcas = valor / 100`; bono del renglón → si es cero en todos, `bono_alimentacion = 0`
  (sin doble cuenta con las prestaciones); si no lo es, el APU es «no evaluable» y se dice (el bono de Sílice es un monto
  por obrero y día, no por renglón).
- Administración y utilidad en cascada → los parámetros de siempre. Financiamiento distinto de cero → «no evaluable»:
  Sílice no tiene ese parámetro y reproducirlo exigiría tocar el núcleo. Impuesto dentro del APU distinto de cero →
  ADVERTENCIA (el IVA va sobre el total, Tarea 18; contarlo dos veces sería un error).
- Desperdicio por renglón → punto 1, opción B.
- Enlace presupuesto ↔ APU por número de renglón y hoja, y por libro de frente; cada diferencia de precio unitario o de
  cantidad entre presupuesto y APU es un hallazgo con su `HOJA!CELDA`.
- Unidades del libro: el perfil declara su tabla de traducción («lo que el libro escribe → la unidad de Sílice»), para lo
  que no es un alias general (punto 5). Cada traducción usada queda en la traza.
- **Perfiles locales.** Los rótulos exactos de un libro real son texto de ese libro: el perfil del repositorio se escribe
  contra un **libro ficticio** con la misma forma (en `tests/fixtures/`, con sus propios rótulos); si un libro real usa
  otras variantes, su perfil vive en la carpeta de datos de la instalación, fuera del repositorio. `cargar_perfil` buscaría
  primero ahí.
- **Redondeo por renglón.** El programa que exporta estos libros redondea cada renglón a dos decimales; el motor de Sílice
  redondea al final (NORMAS §2.3). Las diferencias de céntimos no deben pasar por errores de la empresa: la comparación
  usa la tolerancia de un centavo de CV1 (V-15) y, si se pasa solo por redondeo, el hallazgo es INFO y lo dice (§10).

Dónde: `adapters/hoja_empresa/` (perfil hermano, lector, campos opcionales del modelo), `fusion/mapeo.py`, `aplicacion/`
(despachador de «Auditar un presupuesto», que elige el perfil), `api/` (subir el libro de APU y, si viene, el de
presupuesto) y la pantalla de auditar (`frontend-desktop/src/paginas/auditoria/`). Prueba de aceptación: el libro ficticio
con un APU por hoja, renglones sin número, un desperdicio, un financiamiento en cero y uno distinto de cero, y una banda de
transporte.

**Toca `core/`:** no. El financiamiento distinto de cero se declara no evaluable en vez de tocarlo.

## 8. Punto 5: alias de unidades

### 8.1 El problema

El material real escribe tonelada y litro con grafías que la tabla del núcleo no conoce (`ton`, `lt`), además de `kgf`
para el acero, una unidad de t·km en dos grafías y el cuñete para la pintura. R3 marcaría `ton` distinto de `t`.

### 8.2 Opciones

| Opción | Pros | Contras |
|---|---|---|
| **A. Fusionar NUC-E1** (PR #100): `t` y `l` con sus grafías | Ya está hecho, con prueba en rojo, implementación y expediente; resuelve también la pregunta 17 de `docs/bitacora/2026-10-30-preguntas-para-eugenio.md` | **Toca `core/`** (`core/contracts/unidades.py`): espera al tutor |
| **B. Ampliar el núcleo con `kgf` → `kg` y las grafías de t·km** (expediente NUC-E2) | Una sola tabla de alias | `kgf` es kilogramo-fuerza: no es una grafía de la misma unidad, y la tabla solo admite grafías de la misma unidad (docstring de `unidades.py`). En este libro, además, la «unidad de t·km» acompaña cantidades en toneladas (punto 2): un alias la volvería más engañosa |
| **C. Traducción declarada en el perfil del importador** para lo que no es alias general | No toca el núcleo; cada traducción queda en la traza y en el informe | Una tabla por perfil, distinta de la general (no es duplicación: traduce un formato, no define unidades) |

### 8.3 Recomendación

**A para `t` y `l`, cuando el tutor lo apruebe; C para lo demás; B no.** El cuñete nunca equivale a litros sin su tamaño:
el perfil o la persona declara cuántos litros trae, y sin ese dato la pintura de ese APU queda sin comparar (VR5 «no
evaluable»), no se adivina. Mientras el PR #100 espera, el perfil también traduce `ton` y `lt` (declarado) y deja de
hacerlo cuando el alias esté en el núcleo.

**Toca `core/`:** A sí (ya preparado con su expediente NUC-E1, en rama solo-core, sin fusionar); C no.

## 9. Resumen: qué toca el núcleo

| Punto | Recomendación | Vive en | Toca `core/` |
|---|---|---|---|
| 1. Desperdicio | B: dentro de la cantidad, con traza | `adapters/hoja_empresa`, `fusion`, `aplicacion` (tabla aditiva del caso), Componer y Hoja | No (A, el campo en el contrato, sí: NUC-E2 si el tutor lo pide) |
| 2. VR4 por banda | B + C: convención por obra y clave en `t` | `adapters/vial` | No |
| 3. Partidas | B para las geométricas, A para las otras dos | `adapters/vial`, `aplicacion/consulta.py`, pantalla de tramos | No |
| 4. Perfil APU por hoja | B: perfil hermano en `hoja_empresa` | `adapters/hoja_empresa`, `fusion`, `aplicacion`, `api`, pantalla de auditar | No |
| 5. Alias | A (`t`, `l`) + C (el resto) | `core/contracts/unidades.py` (A); perfil (C) | Sí, solo A, ya preparado |

Todo lo que no es A del punto 5 se construye con `git diff --stat <base> -- core/` vacío, como pide el plan vial.

## 10. Preguntas

**Para Eugenio**
1. ¿Aprueba que el desperdicio vaya dentro de la cantidad con su traza (punto 1, B), sin esperar al tutor?
2. Transporte por banda (punto 2): si la distancia del tramo cae fuera de la banda de la partida, ¿ADVERTENCIA (lo
   propuesto) o ERROR?
3. Esponjamiento del fresado: ¿dato obligatorio de la capa, sin valor por defecto (lo propuesto), o una constante con
   fuente que usted aporte? Y los ojos de gato: ¿basta el número declarado o quiere que salga de la separación?
4. Variantes de medición del material real: ¿Sílice debe aceptar el fresado en m² (con espesor) y la colocación de la
   carpeta en toneladas, además de las unidades de hoy?
5. ¿De acuerdo con que los perfiles de libros reales vivan en la carpeta de datos de la instalación, fuera del
   repositorio, y que el del repositorio se escriba contra un libro ficticio?
6. Diferencias de céntimos por redondeo por renglón: ¿INFO que lo explica (lo propuesto) o no mostrarlas?
7. ¿Quien le dio el material autoriza citar en la tesis la **forma** de su APU (sin nombres ni cifras)?

**Para el tutor**
1. NUC-E1 (PR #100): alias de tonelada y litro en el núcleo.
2. ¿Quiere el desperdicio como concepto del contrato (`LineaMaterial`, NUC-E2) o basta dentro de la cantidad con traza,
   como ya hacen los adaptadores civil y de espacio?
3. Códigos de las partidas viales: siguen provisionales (V-2); las seis nuevas también. ¿Qué parte de la norma se coteja?
4. `kgf` en los APU de acero: ¿se acepta traducirlo a `kg` en el perfil, declarado, o debe tratarse como unidad propia?

## 11. Orden de construcción sugerido

Tamaños: **S** = una tarea de una sesión; **M** = dos o tres tareas; **L** = cuatro o más. Cada tarea con TDD (rojo visto),
su árbitro y commit; suite completa al cerrar.

| # | Qué | Tamaño | Depende de |
|---|---|---|---|
| 0 | Tutor: decidir PR #100 (NUC-E1). Sin código nuevo | — | — |
| 1 | Partidas nuevas: catálogo y derivación de las tres geométricas, CSV y pantalla de tramos | M | — |
| 2 | VR4 por banda: clave en `t`, convención del tramo, modo banda de VR4 | S | 1 (comparte constantes y CSV) |
| 3 | Desperdicio dentro de la cantidad: traza, tabla aditiva, Componer y Hoja | M | — |
| 4 | Libro ficticio con un APU por hoja (fixture) y perfil hermano: lector, campos opcionales del modelo, mapeo | L | 3 |
| 5 | Enlace con el libro de presupuesto, hallazgos de precio y cantidad, traducción de unidades, perfiles locales | M | 4 |
| 6 | Pantalla de auditar: subir los dos libros, informe | S | 5 |

1-2 y 3-6 son carriles independientes. Lo que toque el núcleo (solo NUC-E1 y, si el tutor lo pide, NUC-E2) va en su rama
solo-core, nunca mezclado con estas tareas.

## 12. Riesgos

- **El patrón de la banda de distancia no es universal.** Otro libro puede escribirla de otra forma: el patrón es del
  perfil, y una descripción que no lo sigue queda sin banda e informada.
- **La traza del desperdicio se desincroniza** si alguien edita la cantidad en la Hoja sin pasar por el campo de
  desperdicio. Mitigación: la Hoja edita neta y porcentaje, nunca el producto.
- **Libros de solo valores.** Las reglas L del libro conocido que comparan fórmula contra valor no aplican: la evidencia
  es el recálculo de Sílice, y el informe lo dice.
- **Datos reales cerca del código.** El libro ficticio de prueba se escribe a mano desde la forma, nunca a partir de una
  copia del real; antes de cada commit se busca en lo añadido cualquier nombre, código o cifra del material.

## 13. Decisiones provisionales y lo construido (2026-11-06)

**Decisiones provisionales** (recomendaciones del orquestador a las preguntas para Eugenio de §10, del 2026-11-06,
**pendientes de que Eugenio las ratifique**). Se construyó así, de modo que cambiar cada una sea local:

| Pregunta (§10) | Decisión provisional | Dónde se cambia si Eugenio dice otra cosa |
|---|---|---|
| 1. Desperdicio | Dentro de la cantidad, con su traza (punto 1, B), sin esperar al tutor | `fusion/desperdicio.py` (la fórmula), `aplicacion/desperdicio.py` (la traza) |
| 2. Distancia fuera de la banda | ADVERTENCIA, no ERROR | `adapters/vial/reglas.py`, `_vr4_banda` |
| 3. Esponjamiento y ojos de gato | Esponjamiento: dato obligatorio de la capa para derivar el transporte del fresado, sin valor por defecto (factor ≥ 1). Ojos de gato: basta el número declarado por la línea | `adapters/vial/modelo.py` (`Capa`, `Demarcacion`) |
| 4. Variantes de medición | Sí: fresado en m² (con espesor) y colocación de la carpeta en t, cada una con su código (`fresado_area` C-000.000.022, `carpeta_colocacion_masa` C-000.000.023) | `adapters/vial/modelo.py` (`MEDICIONES`), `derivacion.py` (`_VARIANTES`) |
| 5. Perfiles de libros reales | Fuera del repositorio, en la carpeta de datos de la instalación (`SILICE_PERFILES_LIBROS`); el del repositorio se escribe contra un libro ficticio (`tests/fixtures/libro_apu_por_hoja.py`) | `adapters/hoja_empresa/perfil_apu_por_hoja.py`, `carpetas_locales` |
| 6. Céntimos por redondeo por renglón | INFO que los explica | `fusion/apu_por_hoja.py`, AH1 |

**Decisiones de construcción** (tomadas al construir, prudentes y reversibles):

- La limpieza de la superficie se deriva solo si la capa de riego la declara (columna `limpieza` = `sí`): derivarla siempre
  habría cambiado las cantidades de las obras de hoy («un CSV de hoy sigue leyéndose igual», §6.3).
- La convención del transporte es del tramo (columna `transporte` del CSV, vacía = t·km, la de siempre; `banda`), guardada
  en una columna nueva y nullable de `vial_tramo` (migración aditiva `caso_0021_vial_transporte`). Con banda, la partida en
  t se deriva aunque el tramo no declare la distancia; VR4 la usa para comparar la banda.
- La banda de una partida se lee de la directiva `_tramo_km` («mínimo-máximo», coma o punto decimal) y se entiende como «más
  del mínimo y hasta el máximo», que es como la escribe la descripción.
- La demarcación de superficie es un tipo de demarcación (`superficie`: `lineas` es el número de elementos y `area_m2` el
  área de cada uno); no deriva pintura (VR5 mide líneas).
- La traza del desperdicio va en dos tablas aditivas del caso (`caso_0022_apu_desperdicio`), solo inserción, por partida.
  Solo se muestra en la línea cuya cantidad guardada sigue siendo la que resultó (riesgo de §12).
- El libro con un APU por hoja se audita por su propia ruta (`POST /v1/libros/apu-por-hoja`) y su propio bloque de la
  pantalla de auditar; no pasa por el visor ni por el historial de UC-30 (que son del libro de la plantilla conocida).
- Hallazgos del libro con un APU por hoja: AH1 precio impreso frente al recalculado; AH2 bono por renglón y AH3
  financiamiento (no evaluable); AH4 impuesto dentro del APU (ADVERTENCIA, y esa hoja no se compara); AH5 precio y AH6
  cantidad del presupuesto frente a su APU; AH7 renglón u hoja sin pareja; AH8 unidad traducida por el perfil; AH9 banda
  leída de la descripción (`fusion/apu_por_hoja.py`).

**Lo que falta:** la Hoja todavía no muestra ni edita la neta y el porcentaje del desperdicio (punto 1, «la Hoja edita neta
y porcentaje, nunca el producto»): Componer sí, y la traza no se muestra si la cantidad cambió por otro camino. Mostrarla en
la pestaña APU de la Hoja es la tarea siguiente; editarla allí puede exigir tocar `aplicacion/hoja.py`, congelado por el
experimento de la tesis (re-congelar exige acta y aval de Eugenio).

