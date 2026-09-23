# Guion de prueba manual de AREN.IA (IEEE 829) — Sesión P4.2

Especificación de casos de prueba manuales para la pantalla **Componer partida (UC‑10 / UC‑11)**
del prototipo AREN.IA (`ui/paginas/componer.py`). Está escrita para una persona que **no programa**:
cada caso dice qué hacer, paso a paso, y qué debe ver en pantalla. Complementa el
[plan de pruebas](plan_pruebas.md), que cubre las pruebas automatizadas; los enunciados de los UC y
RF citados viven una sola vez en la [ERS](ERS.md) y aquí no se repiten.

## 1. Identificador y alcance

- **Identificador:** GP‑ARENIA‑001, versión de la Sesión P4.2 (2026‑09‑21), corregida en la fase C1
  del cierre (INV‑065: la prueba trabaja sobre su propia base, nunca sobre `data/apu.db`).
- **Alcance:** el recorrido completo de la pantalla de componer: componer una partida desde cero con
  la referencia MaPreX, editarla, una línea de mano de obra a destajo, la advertencia de rendimiento
  fuera de rango, la exportación a Excel y la lectura del informe de auditoría.
- **Fuera de alcance:** las demás pantallas de la aplicación (salvo la consulta del *Catalogo* en
  CP‑02) y todo lo que ya prueban las pruebas automatizadas del [plan de pruebas](plan_pruebas.md).

CP‑07 (sprint de UI, [PLAN_UI.md](../PLAN_UI.md)) es de otra naturaleza: no lo ejecuta quien anota, sino una persona que nunca vio la aplicación, y mide RNF‑10.

## 2. Elementos a probar

| Elemento | Qué es |
|---|---|
| `ui/paginas/componer.py` | la pantalla que se prueba (UC‑10 componer, UC‑11 editar) |
| `ui/composicion.py` | el buscador de la referencia MaPreX y la lectura de las tablas |
| `core/budget/excel.py` | el libro de Excel con sus cuatro hojas |
| `scripts/seed_demo.py` | la siembra que deja la base lista para la prueba |

## 3. Naturaleza de los datos

**Los datos sembrados son didácticos, no de obra ejecutada.** Las cinco partidas `LB-*` de la
clínica y las tres partidas `DEMO-*` son ejercicios académicos ficticios; los precios de la
referencia MaPreX son una referencia publicada que se usa como sugerencia. La declaración completa
vive una sola vez en [CLAUDE.md §1](../CLAUDE.md#1-qué-es-este-proyecto). La partida `PRUEBA-01-TUB`
que se compone en este guion es, igualmente, un caso de prueba.

## 4. Entorno y preparación

**Requisitos:** la copia del repositorio, `uv` instalado y un navegador. Los resultados esperados se
obtuvieron en Windows 11 con Python 3.13 y Streamlit 1.62.0.

> **Esta prueba trabaja sobre su propia base, `data/prueba_arenia.db`, y nunca sobre
> `data/apu.db`**, la base de trabajo de la aplicación. La siembra con `--reiniciar` borra la base
> que se le indica antes de volver a sembrarla: por eso toda orden de este guion lleva
> `--db data/prueba_arenia.db`, y cada caso le recuerda escribir esa base en la barra lateral.

**Antes de empezar (protección de la base de trabajo).** Anote en la sección 8 si existe
`data/apu.db` **en esta copia de trabajo** (la carpeta del repositorio en la que está parado ahora,
no la copia desechable del paso 1) y, si existe, su fecha y hora de modificación. En PowerShell:
`Get-Item data/apu.db | Select-Object LastWriteTime`; en bash: `ls -l --time-style=full-iso data/apu.db`.
Si no existe, anote «no existe».

1. **Cree una copia desechable del repositorio y trabaje sobre ella, nunca sobre esta copia de
   trabajo.** Hasta que la Tarea 12 de U1 (fase C3, con `ARENIA_CASO` leído por `ui/caso.py`)
   reemplace esta barrera, la aplicación abre `data/apu.db` de la carpeta desde la que se ejecuta en
   el primer renderizado de cada página —antes de que se pueda escribir ninguna otra ruta—, así que
   solo ejecutar la prueba fuera de esta copia de trabajo evita tocar su `data/apu.db`. Desde la raíz
   del repositorio:

   ```
   git worktree add ../tesis-prueba-manual HEAD
   cd ../tesis-prueba-manual
   uv sync --extra ui --extra ml
   ```

   Ejecute el resto de esta sección y los casos CP‑01…CP‑06 **dentro de `../tesis-prueba-manual`**.
   Al terminar toda la prueba (después del paso «Al terminar la prueba», más abajo), vuelva a la
   copia de trabajo original y borre la copia desechable:

   ```
   git worktree remove ../tesis-prueba-manual
   ```

2. Siembre la base de prueba (línea base de la clínica, las tres partidas de demostración y el
   presupuesto de ejemplo `DEMO-001`) en su propio archivo:

   ```
   uv run python scripts/seed_demo.py --db data/prueba_arenia.db --reiniciar
   ```

   `--reiniciar` borra `data/prueba_arenia.db` antes de sembrarla, de modo que cada repetición
   empieza de la misma base. **No ejecute nunca la orden sin `--db`:** sin esa opción apunta a
   `data/apu.db`.

   **Comprobación de la preparación.** Al terminar, la terminal debe mostrar, entre otras, estas
   líneas: `Partida: 8`, `Total: 4131.10 USD` y `Auditoria: 3 hallazgo(s), CUMPLE`. Si no aparecen,
   detenga la prueba y anótelo en la sección 8.

3. Abra la aplicación:

   ```
   uv run python -m streamlit run ui/app.py
   ```

   Se abre el navegador. En el menú lateral, elija **Componer partida (UC-10 / UC-11)**.

   En la barra lateral, escriba `data/prueba_arenia.db` en el campo **Archivo SQLite** y pulse
   Enter. **El campo vuelve a `data/apu.db` cada vez que se recarga la página (F5) o se abre otra
   pestaña**: cada caso le indica cuándo escribirlo de nuevo.

**Orden de ejecución.** Los casos se ejecutan en orden, de CP‑01 a CP‑06, sobre una base recién
sembrada: CP‑02 y CP‑03 continúan donde terminó CP‑01. Si repite la prueba, vuelva al paso 2.

**Al terminar la prueba.** Vuelva a la copia de trabajo original (`cd` fuera de
`../tesis-prueba-manual`) y repita allí la comprobación de «Antes de empezar»; anótela en la sección
8: `data/apu.db` **de esta copia de trabajo** debe seguir igual que al empezar (o seguir sin
existir). Si cambió, la ejecución es **FALLA** aunque todos los casos hayan pasado: la prueba tocó la
base de trabajo. Por último, borre la copia desechable (paso 1).

## 5. Cómo leer los números y cómo anotar

- La pantalla muestra los importes **sin redondear** (por ejemplo `20.11369894402000`): el sistema
  calcula con decimales exactos y solo redondea al presentar un informe. Compare **todas las cifras
  que da el resultado esperado**; los ceros finales de más o de menos no cuentan. Entre paréntesis
  se da el valor redondeado a dos decimales como ayuda de lectura.
- El separador decimal en pantalla es el **punto**.
- **Veredicto:** escriba **PASA** si todo lo que dice el resultado esperado se observó, y **FALLA**
  si algo no coincide; en ese caso copie en *Resultado obtenido* lo que vio (una captura de pantalla
  ayuda).
- Los recuadros de **sugerencia** de AREN.IA (por ejemplo, «Partidas similares del catalogo» al
  escribir una descripción) pueden aparecer; son de solo lectura y no forman parte del veredicto
  salvo que el caso los mencione.

## 6. Casos de prueba

### CP‑01 — Componer una partida desde cero con el buscador MaPreX

- **Objetivo:** componer una partida nueva tomando sus seis insumos de la referencia MaPreX y ver su
  precio unitario en vivo, antes de guardar.
- **Trazabilidad:** UC‑10; RF‑01, RF‑33, RF‑35.
- **Precondición:** base recién sembrada (sección 4) y la página *Componer partida* abierta, con las
  tablas vacías y `data/prueba_arenia.db` escrita en el campo **Archivo SQLite** de la barra lateral.

**Pasos**

1. En **Materiales**, en el campo *Buscar en la referencia MaPreX (materiales)*, escriba
   `tubo pvc` y pulse Enter. En *Resultado* deje elegida la primera opción,
   `TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA — 13.9291 USD/m · ref. PLOA38`, y pulse
   **Usar esta fila**.
2. Repita el paso 1 con `pegamento` (una sola opción: `PEGAMENTO PARA PVC  1/4 GL TANGIT  O SIM —
   34.5694 USD/env · ref. MT539`).
3. En **Equipos**, con su propio buscador, repita con `segueta` y después con `herramientas`.
4. En **Mano de obra**, con su propio buscador, repita con `albanil` y después con `ayudante`.
5. Complete la cantidad de cada fila (doble clic en la celda), sin tocar ninguna otra columna:

   | Tabla | Fila | Columna | Valor |
   |---|---|---|---|
   | Materiales | TUBO PVC A.N. D=4"… | Consumo por unidad | `1.05` |
   | Materiales | PEGAMENTO PARA PVC… | Consumo por unidad | `0.02` |
   | Equipos | SEGUETA AJUSTABLE (ARCO) | cantidad | `1` |
   | Equipos | HERRAMIENTAS MENORES | cantidad | `1` |
   | Mano de obra | ALBAÑIL DE 1RA -N5 | cantidad | `1` |
   | Mano de obra | AYUDANTE - TABULADOR CONSTRUCCION -N2 | cantidad | `2` |

6. En **Cabecera de la partida** escriba: Codigo `PRUEBA-01-TUB`, Descripcion
   `Colocacion de tuberia PVC de 4 pulgadas`, Unidad `m`. Deje Dominio en `civil` y la Fecha de hoy.
7. En **Rendimiento — unidades por día** escriba `100`.
8. Observe el **Desglose en vivo** y el botón **Guardar composicion**.
9. En **Condiciones del rendimiento** escriba `cuadrilla de un albanil y dos ayudantes; condiciones
   de prueba del guion, no proviene de una ejecucion medida` y pulse fuera del campo.
10. Pulse **Guardar composicion**.

**Resultado esperado**

- Pasos 1 a 4: cada búsqueda encuentra resultados; bajo el selector aparece la procedencia
  (`Referencia MaPreX: PLOA38` para la tubería) y cada **Usar esta fila** agrega una fila con
  descripción, unidad y precio ya llenos y la cantidad **en blanco**. `tubo pvc` ofrece dos opciones
  (la segunda es un tubo de electricidad de 1"); las demás búsquedas, una. Los precios y los factores
  de depreciación que se agregan son: tubería `13.9291`, pegamento `34.5694`, segueta `34.5694` con
  depreciación `0.022000`, herramientas menores `14.3046` con depreciación `1.000000`, albañil
  `2.1877` y ayudante `1.7816`. Todas las celdas de precio se pueden editar (RF‑35), aunque en este
  caso no se editan.
- Paso 8: el desglose muestra

  | Métrica | Valor esperado |
  |---|---|
  | Materiales | `15.316943` |
  | Equipos | `0.1506512680` |
  | Mano de obra | `0.432563` |
  | Costo directo | `15.9001572680` |
  | Con administracion | `18.285180858200` |
  | **Precio unitario** | **`20.11369894402000`** (≈ 20,11) |

  y **Guardar composicion está deshabilitado** (gris) porque faltan las condiciones (RF‑33).
- Paso 9: el botón **Guardar composicion** se habilita.
- Paso 10: aparece el mensaje verde
  `Composicion guardada para la partida PRUEBA-01-TUB: precio unitario 20.11369894402000.`

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑02 — Editar la partida de CP‑01 (UC‑11)

- **Objetivo:** guardar de nuevo la misma partida con otro rendimiento y comprobar que se edita, no
  se duplica, y que el historial de rendimientos gana una observación.
- **Trazabilidad:** UC‑11; RF‑26, RF‑27, RF‑33.
- **Precondición:** CP‑01 terminado con PASA, en la misma pestaña y sin recargar la página: el campo
  **Archivo SQLite** sigue diciendo `data/prueba_arenia.db`.

**Pasos**

1. Observe el campo **Rendimiento — unidades por día**.
2. Cambie el rendimiento a `120` y pulse Enter.
3. Pulse **Guardar composicion**.
4. Para comprobar el historial, cambie el rendimiento a `150` y pulse Enter. **No guarde.**
5. Vuelva a escribir `120` en el rendimiento (así queda listo para CP‑03).
6. Abra una **segunda pestaña** del navegador con la misma dirección de la aplicación y, en ella,
   elija **Catalogo** en el menú lateral. En la barra lateral de esa pestaña escriba
   `data/prueba_arenia.db` en el campo **Archivo SQLite** y pulse Enter (la pestaña nueva empieza en
   `data/apu.db`). Observe la tabla **Partidas**. Cierre esa pestaña y vuelva a la primera.

**Resultado esperado**

- Paso 1: el campo muestra `100`, el rendimiento guardado en CP‑01, precargado desde el historial.
- Paso 2: **Precio unitario** `19.99073793585000000000000000` (≈ 19,99). Aparece además el aviso
  azul de la ayuda 4 de AREN.IA: `El precio construido cae dentro del rango de la clase 3 de AACE
  International frente a la estimacion por reglas.`
- Paso 3: mensaje verde `Composicion guardada para la partida PRUEBA-01-TUB: precio unitario
  19.99073793585000000000000000.`
- Paso 4: aparece el aviso amarillo `el rendimiento 150 se aparta del comportamiento observado de la
  partida: rango [100, 120] en 2 observaciones (0 medidas); el registro se completa igualmente`.
  **«2 observaciones»** es la prueba de que el historial ganó un rendimiento (100 y 120).
- Paso 6: la tabla **Partidas** tiene **9** filas (las 8 sembradas más `PRUEBA-01-TUB`) y
  `PRUEBA-01-TUB` aparece **una sola vez**: guardar dos veces editó la partida, no la duplicó.

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑03 — Una línea a destajo junto a otra a jornal

- **Objetivo:** ver cuánto sube el precio unitario al agregar una línea de mano de obra a destajo,
  y por qué no lleva FCAS ni bono de alimentación (decisión D9 del [dossier G0](dossier_g0.md)).
- **Trazabilidad:** UC‑10 / UC‑11; RF‑01, RF‑34.
- **Precondición:** CP‑02 terminado, en la misma pestaña: la partida `PRUEBA-01-TUB` en pantalla con
  rendimiento `120` y **Precio unitario** `19.99073793585000000000000000`, y el campo **Archivo
  SQLite** en `data/prueba_arenia.db`. Si el rendimiento no está en `120`, escríbalo.

**Pasos**

1. En la tabla **Mano de obra**, agregue una fila (el **+** bajo la tabla) y escriba: descripcion
   `Instalador a destajo`, cantidad `1`, sueldo `1.50`, y en modalidad elija `destajo`.
2. Observe **Mano de obra** y **Precio unitario** en el desglose en vivo.
3. En esa misma fila, cambie la modalidad a `jornal`.
4. Observe de nuevo el desglose.
5. **No guarde.** (El caso solo observa; la partida guardada en CP‑02 no cambia.)

**Resultado esperado**

| Estado | Mano de obra | Precio unitario |
|---|---|---|
| Antes del paso 1 | `0.3604691666666666666666666667` | `19.99073793585000000000000000` (≈ 19,99) |
| Paso 2 (la fila a **destajo**) | `1.860469166666666666666666667` | `21.88823793585000000000000000` (≈ 21,89) |
| Paso 4 (la misma fila a **jornal**) | `0.4563025` | `20.11196710251666666666666666` (≈ 20,11) |

**Por qué.** A destajo, `1.50` no es un jornal diario: es lo que se paga **por cada metro
instalado** (artículo 114 de la LOTTT, decisión D9). Por eso entra completo a la mano de obra, que
sube exactamente `1.50`: sin multiplicarse por (1 + FCAS), sin bono de alimentación y sin dividirse
entre el rendimiento. El precio unitario sube `1.8975` (1,50 con administración y utilidad en
cascada: 1,50 × 1,15 × 1,10). La misma línea declarada a jornal se trata como un obrero más de la
cuadrilla: su sueldo lleva el FCAS y el bono, y todo se divide entre los 120 m por día; la mano de
obra sube solo `0.0958333…` y el precio unitario `0.1212291…`.

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑04 — Un rendimiento fuera de rango en `DEMO-01-INST` (RF‑27)

- **Objetivo:** comprobar que un rendimiento que se aparta de lo observado dispara la advertencia
  RF‑27 y que, aun así, guardar sigue habilitado.
- **Trazabilidad:** UC‑06, UC‑11; RF‑26, RF‑27, RF‑33.
- **Precondición:** base sembrada (la partida `DEMO-01-INST` trae dos observaciones de rendimiento:
  50 y 60 m por día). Recargue la página con **F5** para empezar con las tablas vacías y escriba de
  nuevo `data/prueba_arenia.db` en el campo **Archivo SQLite** (la recarga lo devolvió a
  `data/apu.db`).

**Pasos**

1. En Codigo escriba `DEMO-01-INST` y pulse Enter. Observe el campo de rendimiento.
2. Cambie el rendimiento a `80` y pulse Enter.
3. En **Condiciones del rendimiento** escriba `condiciones de prueba del guion` y pulse fuera del
   campo. Observe el botón **Guardar composicion**. **No lo pulse:** el caso solo observa la
   advertencia. (Con la cabecera en blanco no se guardaría nada; con la cabecera completa, guardar
   registraría el rendimiento `80` en la partida de demostración que usan CP‑05 y CP‑06. Guardar
   sobre una partida existente con las tres tablas vacías, o con otra unidad u otra descripción que
   las registradas, muestra un error rojo y no escribe nada.)
4. Cambie el rendimiento a `55` y pulse Enter.

**Resultado esperado**

- Paso 1: el rendimiento aparece precargado con `60` (la observación más reciente) y **no** hay
  advertencia. Las tres tablas de insumos aparecen **precargadas** con la composición guardada de
  la partida (UC‑11, paso 1): 3 materiales, 2 equipos y 2 líneas de mano de obra, una a `jornal` y
  otra a `destajo`.
- Paso 2: aparece el aviso amarillo `el rendimiento 80 se aparta del comportamiento observado de la
  partida: rango [50, 60] en 2 observaciones (0 medidas); el registro se completa igualmente`.
  (En el desglose aparece también el aviso azul `La unidad no puede estar vacía`, porque en este
  caso no se compone la partida: es esperado y no forma parte del veredicto.)
- Paso 3: el aviso amarillo sigue visible y **Guardar composicion está habilitado**: la advertencia
  informa, no bloquea (RF‑27).
- Paso 4: el aviso amarillo **desaparece** (55 está dentro del rango [50, 60]).

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑05 — Exportar a Excel

- **Objetivo:** elaborar un presupuesto con las tres partidas de demostración, descargarlo en Excel
  y comprobar sus cuatro hojas y la columna *Modalidad*.
- **Trazabilidad:** UC‑01; RF‑06, RF‑07, RF‑08, RF‑34.
- **Precondición:** base sembrada y CP‑04 terminado **sin guardar**. Recargue la página con **F5** y
  escriba de nuevo `data/prueba_arenia.db` en el campo **Archivo SQLite**. Excel o LibreOffice Calc
  para abrir el libro.

**Pasos**

1. Baje a **Cantidades de obra**. Agregue tres filas (el **+** bajo la tabla) con estos valores
   (la columna codigo_partida se elige de una lista):

   | codigo_partida | cantidad | origen_id |
   |---|---|---|
   | `DEMO-01-INST` | `180` | `DEMO-TRAMO-01` |
   | `DEMO-02-VALV` | `4` | `DEMO-VALVULAS-01` |
   | `DEMO-03-PRUEBA` | `180` | `DEMO-PRUEBA-01` |

2. En **Elaborar presupuesto** deje los valores por defecto: Codigo del presupuesto `P-001`, Fecha
   del presupuesto la de hoy y Moneda `USD`.
3. Pulse **Elaborar y auditar**.
4. Pulse **Exportar a Excel** y abra el archivo descargado.
5. En el libro, recorra las pestañas de las hojas y, en la hoja **APU**, busque la tabla de mano de
   obra de `DEMO-01-INST`.

**Resultado esperado**

- Paso 3: aparece **Presupuesto elaborado** con **Total del presupuesto** `4131.10 USD` (el mismo
  total que la siembra imprimió para `DEMO-001`) y el botón **Exportar a Excel**.
- Paso 4: el archivo se llama `presupuesto_P-001.xlsx`.
- Paso 5: el libro tiene **cuatro hojas**, en este orden: **Presupuesto**, **APU**, **Curva** y
  **Auditoria**. En la hoja **APU**, la tabla de mano de obra de cada partida tiene los encabezados
  `Mano de obra | Obreros | Sueldo | Modalidad | Total`. Para `DEMO-01-INST`:

  | Mano de obra | Obreros | Sueldo | Modalidad | Total |
  |---|---|---|---|---|
  | Supervisor de cuadrilla | 1 | 8 | jornal | 8 |
  | Cuadrilla instaladora a destajo | 1 | 3.5 | destajo | 3.5 |

  (según el programa y su configuración, los números pueden verse con otro separador decimal o con
  ceros de más, por ejemplo `8,00`; el valor es el mismo). Los precios unitarios de las tres partidas son `18.85` (DEMO-01-INST), `129.35` (DEMO-02-VALV)
  y `1.23` (DEMO-03-PRUEBA).

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑06 — Leer el informe de auditoría

- **Objetivo:** comprobar que el informe de auditoría aparece siempre, sin pedirlo, y leer cuántos
  hallazgos tiene y de qué severidad.
- **Trazabilidad:** UC‑01, UC‑05; RF‑02, RF‑21, RF‑23.
- **Precondición:** CP‑05 terminado, en la misma pestaña y con `data/prueba_arenia.db` en el campo
  **Archivo SQLite**.

**Pasos**

1. Bajo **Presupuesto elaborado**, observe el resumen por severidad.
2. Baje a **Informe de auditoria** y léalo completo.

**Resultado esperado**

- Paso 1: una sola métrica, **ADVERTENCIA** con valor **3**. No hay hallazgos de otra severidad.
- Paso 2: el informe se titula `Informe de auditoria del presupuesto P-001` y dice
  `Hallazgos: 3 · Resultado: CUMPLE`. La tabla de hallazgos tiene **tres filas**, todas de la regla
  **R1** con severidad **ADVERTENCIA**, una por partida, en este orden:

  | # | Partida | Observado | Qué dice |
  |---|---|---|---|
  | 1 | DEMO-03-PRUEBA | 180.00 | `la cantidad de DEMO-03-PRUEBA (180 m) es manual y no declara la regla que la produjo: no es derivable ni reproducible` |
  | 2 | DEMO-01-INST | 180.00 | `la cantidad de DEMO-01-INST (180 m) es manual y no declara la regla que la produjo: no es derivable ni reproducible` |
  | 3 | DEMO-02-VALV | 4.00 | `la cantidad de DEMO-02-VALV (4 unidad) es manual y no declara la regla que la produjo: no es derivable ni reproducible` |

**Cómo se lee.** Las tres cantidades se escribieron a mano en CP‑05; ninguna viene de una regla
paramétrica ni de un modelo IFC. La regla R1 (trazabilidad geométrica) lo hace constar como
advertencia, no como error: el presupuesto **cumple**. Que el informe aparezca sin haberlo pedido es
parte de lo que se prueba (principio 7 de [CLAUDE.md](../CLAUDE.md)).

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑07 — Una persona nueva llega sola del Inicio al Excel auditado

- **Objetivo:** medir si una persona que nunca vio la aplicación, sin explicación previa y sin que
  nadie la guíe, llega desde el Inicio hasta un presupuesto en Excel con su hoja de auditoría.
- **Trazabilidad:** UC‑12; RF‑36 a RF‑43; **RNF‑10**; compuerta GU1 de [PLAN_UI.md](../PLAN_UI.md).
- **Naturaleza:** caso con persona. Hay dos papeles: el **participante**, que usa la aplicación, y
  el **observador**, que prepara, lee la consigna, cronometra y anota. El observador no es
  participante.
- **Participantes:** dos personas distintas, una por escenario. Ninguna vio antes la aplicación ni
  sus documentos; la persona del escenario B tampoco debe haber presenciado la sesión del escenario
  A. Se anota su perfil, no su nombre: profesión, años de experiencia con presupuestos de obra, si
  ha usado aplicaciones web de datos.
- **Escenarios:**
  - **A — base sembrada:** mide el recorrido.
  - **B — base vacía:** mide además el estado vacío y la siembra desde la interfaz.

**Preparación (el observador, antes de que llegue el participante)**

1. Instale las dependencias si no lo ha hecho ya (sección 4, paso 1, en la raíz del repositorio):
   `uv sync --extra ui --extra ml`.
2. Base **exclusiva** de la prueba, nunca `data/apu.db`. Anote si `data/apu.db` existe y su fecha de
   modificación: es la protección para confirmar, al terminar, que la prueba no lo tocó. Escenario
   A: borre `data/cp07/escenario_a.db` si existe (de una corrida anterior) y siembre:
   `uv run python scripts/seed_demo.py --db data/cp07/escenario_a.db`; compruebe en la terminal la
   misma salida que el paso 2 de la sección 4: `Partida: 8`, `Total: 4131.10 USD` y
   `Auditoria: 3 hallazgo(s), CUMPLE`. Escenario B: compruebe que `data/cp07/escenario_b.db` **no**
   existe (bórrelo si quedó de una corrida anterior). Los `*.db` están ignorados por git.
3. Antes de arrancar, limpie el modo entrega: CP‑07 se ejecuta en modo normal. En bash,
   `unset ARENIA_MODO_ENTREGA`; en PowerShell,
   `Remove-Item Env:ARENIA_MODO_ENTREGA -ErrorAction SilentlyContinue`.
4. Arranque la aplicación apuntando a esa base. En bash:
   `ARENIA_CASO=data/cp07/escenario_a.db uv run python -m streamlit run ui/app.py`;
   en PowerShell: `$env:ARENIA_CASO = "data/cp07/escenario_a.db"; uv run python -m streamlit run ui/app.py`
   (en el escenario B, `escenario_b.db`).
5. Compruebe que el navegador abrió en **Inicio** y que la barra lateral, bajo **Caso abierto**,
   nombra la base del escenario. Cierre toda otra pestaña.
6. Vacíe la carpeta de descargas del navegador, o anote su contenido para distinguir después el
   archivo nuevo.
7. Tenga a mano el cronómetro, esta hoja de registro y el bloque B del anexo A de
   [dossier_g0.md](dossier_g0.md), impreso.

**Consigna literal** — se lee tal cual, una sola vez, sin agregar nada:

> «Esta aplicación sirve para armar y auditar presupuestos de obra. Le pido que, sin ayuda,
> obtenga un presupuesto en Excel que incluya su auditoría y que, al terminar, me diga cuántos
> hallazgos tiene esa auditoría. Puede pensar en voz alta. Yo solo voy a observar y a tomar notas.»

**Guion del observador**

1. Ponga en marcha el cronómetro al terminar de leer la consigna.
2. **No conteste preguntas sobre la aplicación.** Respuesta fija a cualquier pregunta: «Haga lo que
   haría si yo no estuviera». Anote cada pregunta con su minuto: cuentan para el registro.
3. Anote cada **punto de detención**: 30 s o más sin una **acción nueva** —clic, escritura o cambio
   de pantalla; mover el ratón o desplazarse por la página no cuenta—, o una frase del tipo «no sé
   qué hacer». Registre minuto, pantalla y lo que dijo la persona. Son la entrada de U2 si el caso
   resulta FALLA.
4. **Qué cuenta como ayuda:** cualquier indicación sobre qué pulsar, adónde ir o qué significa un
   término, y cualquier gesto que confirme o niegue que va bien. Repetir la consigna literal **no**
   cuenta como ayuda.
5. **Si el participante sale del caso abierto** (cambia el archivo en la barra lateral o abre otro
   caso): eso tampoco cuenta como ayuda; anote el minuto y la ruta que abrió. El estado final se
   comprueba siempre sobre la base del escenario (`escenario_a.db` o `escenario_b.db`), nunca sobre
   la que haya quedado abierta al final.
6. **Oferta única de ayuda:** si pasan 3 minutos sin avanzar —sin cambiar de pantalla ni producir
   un resultado nuevo—, diga una sola vez: «¿Quiere que le ayude?». Si acepta, la sesión queda
   **asistida** y el veredicto ya es FALLA; se continúa hasta una condición de parada para registrar
   el resto. Si no acepta, no se vuelve a ofrecer.

**Condiciones de parada** (la primera que ocurra)

1. El participante alcanza el estado final (éxito).
2. Se cumplen **20 minutos** desde el fin de la consigna (el cronómetro corre hasta el estado final;
   ver «Estado final observable», más abajo).
3. Pasan **5 minutos sin una acción nueva** (abandono; definición del punto 3 del guion del
   observador).
4. El participante declara que se rinde.
5. La aplicación muestra una traza de error o deja de responder: el escenario es **FALLA**, se
   registra como defecto con la pantalla y el texto visible, y no se reinicia la aplicación.

**Estado final observable.** El cronómetro corre desde el fin de la consigna hasta que se cumplen
estos dos puntos; abrir el archivo y contestar el bloque B ocurren después y no cuentan para el
tiempo:

- En la carpeta de descargas existe `presupuesto_<codigo>*.xlsx` (el navegador agrega « (1)» si ya
  había un archivo con ese nombre).
- El participante dice, de palabra, un número de hallazgos.

Con el cronómetro ya detenido, el observador abre el archivo y comprueba sus **cuatro hojas**, en
este orden: *Presupuesto*, *APU*, *Curva* y *Auditoria*, y compara el número que dijo el
participante contra la hoja *Auditoria* de **ese mismo archivo** — la referencia es esa hoja, no el
informe en pantalla, que es solo apoyo (en el escenario A la base sembrada ya trae el presupuesto
`DEMO-001`: no lo confunda con el que acaba de producir el participante). Solo en el escenario B: la
barra lateral, bajo **Caso abierto**, informa más de cero partidas. Repita también la comprobación
de la preparación sobre `data/apu.db` (existencia y fecha de modificación) y compárela con la
anotada al inicio.

**Al terminar:** el participante contesta a solas el **bloque B** del anexo A (en el escenario A,
B4 se marca «no aplica»). El observador no mira mientras lo contesta.

**Criterio de aceptación, declarado antes de ejecutar.** Un escenario **PASA** si y solo si: se
alcanzó el estado final **sin ayuda**; **dentro de los 20 minutos**; y el promedio del bloque B es
**≥ 4,0 sin ningún ítem por debajo de 3**. **FALLA** en cualquier otro caso, sin negociar. **CP‑07
PASA si y solo si pasan los dos escenarios.** Una FALLA no cancela el sprint: es el dato de la
tesis y la entrada de la fase U2, cuyo alcance lo fijan los puntos de detención.

Los umbrales de 20, 5 y 3 minutos **son decisiones de este caso, no medidas**: se declaran para que
el veredicto no dependa del criterio del observador, y se revisan con evidencia tras la primera
ejecución, dejando constancia en [docs/bitacora/](bitacora/).

**Hoja de registro** (una hoja, una columna por escenario)

| Campo | Escenario A | Escenario B |
|---|---|---|
| Perfil del participante (sin nombre) | | |
| Fecha y hora de inicio | | |
| Commit probado (`git log -1 --oneline`) | | |
| Sistema operativo y navegador | | |
| Tiempo total (min; desde el fin de la consigna hasta el estado final) | | |
| Número de preguntas al observador | | |
| Oferta de ayuda: minuto · ¿aceptada? | | |
| Puntos de detención (minuto · pantalla · qué dijo) | | |
| Condición de parada (1–5) | | |
| Archivo obtenido y sus hojas | | |
| Hallazgos que dijo · hallazgos de la hoja Auditoria | | |
| `data/apu.db` sin cambios al terminar (sí/no) | | |
| Partidas al terminar (solo B) | — | |
| Bloque B: B1 · B2 · B3 · B4 · B5 · B6 · B7 · promedio | | |
| Campo abierto | | |
| Veredicto del escenario | | |

**Veredicto de CP‑07:** ____ (PASA solo si ambos escenarios PASAN)

## 7. Trazabilidad CP → UC / RF

| Caso | UC | RF | Otros |
|---|---|---|---|
| CP‑01 | UC‑10 | RF‑01, RF‑33, RF‑35 | referencia MaPreX |
| CP‑02 | UC‑11 | RF‑26, RF‑27, RF‑33 | ayuda 4 de AREN.IA (contraste AACE) |
| CP‑03 | UC‑10, UC‑11 | RF‑01, RF‑34 | decisión D9 ([dossier_g0.md](dossier_g0.md)) |
| CP‑04 | UC‑06, UC‑11 | RF‑26, RF‑27, RF‑33 | — |
| CP‑05 | UC‑01 | RF‑06, RF‑07, RF‑08, RF‑34 | hojas de `core/budget/excel.py` |
| CP‑06 | UC‑01, UC‑05 | RF‑02, RF‑21, RF‑23 | principio 7 de CLAUDE.md §2 |
| CP‑07 | UC‑12 | RF‑36 a RF‑43 | RNF‑10; bloque B del anexo A de [dossier_g0.md](dossier_g0.md); compuerta GU1 |

## 8. Registro de la ejecución

| Campo | Valor |
|---|---|
| Persona que prueba | |
| Fecha | |
| Commit probado (`git log -1 --oneline`) | |
| Sistema operativo y navegador | |
| Comprobación de la preparación (sección 4, paso 2) | |
| `data/apu.db` al empezar (existe · fecha de modificación) | |
| `data/apu.db` sin cambios al terminar (sí/no) | |
| Casos PASA / FALLA | |
| Observaciones | |

## 9. Procedencia de los resultados esperados

Todos los resultados esperados de la sección 6 se obtuvieron **ejecutando el sistema** el
2026‑09‑21 sobre el commit `617861b`, contra una base temporal sembrada con
`scripts/seed_demo.py` (nunca contra `data/apu.db`), recorriendo la pantalla con
`streamlit.testing.v1.AppTest` como en `tests/unit/test_ui_componer.py`: las búsquedas de CP‑01 se
hicieron en la propia pantalla (buscador, *Resultado* y *Usar esta fila*), y las cantidades de las
tablas, que `AppTest` no puede teclear, se sembraron con las mismas filas que produce el buscador.
Los guiones auxiliares no forman parte del repositorio. Si una versión posterior del sistema cambia
un valor, este guion se actualiza volviendo a ejecutar el recorrido, no a mano.
