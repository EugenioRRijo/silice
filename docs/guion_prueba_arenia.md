# Guion de prueba manual de AREN.IA (IEEE 829) — Sesión P4.2

Especificación de casos de prueba manuales para la pantalla **Componer una partida** (UC‑10 / UC‑11)
del prototipo AREN.IA (`ui/paginas/componer.py`). Está escrita para una persona que **no programa**:
cada caso dice qué hacer, paso a paso, y qué debe ver en pantalla. Complementa el
[plan de pruebas](plan_pruebas.md), que cubre las pruebas automatizadas; los enunciados de los UC y
RF citados viven una sola vez en la [ERS](ERS.md) y aquí no se repiten.

## 1. Identificador y alcance

- **Identificador:** GP‑ARENIA‑001, versión de la Sesión P4.2 (2026‑09‑21), corregida en la fase C1
  del cierre (INV‑065: la prueba trabaja sobre su propia base, nunca sobre `data/apu.db`) y puesta
  al día en la fase C3 (U1: el caso se abre una vez, con `ARENIA_CASO`; nombres de pantalla nuevos;
  INV‑045: la pantalla presenta dos decimales).
- **Alcance:** el recorrido completo de la pantalla de componer: componer una partida desde cero con
  la referencia MaPreX, editarla, una línea de mano de obra a destajo, la advertencia de rendimiento
  fuera de rango, la exportación a Excel y la lectura del informe de auditoría.
- **Fuera de alcance:** las demás pantallas de la aplicación (salvo la consulta del *Catalogo* en
  CP‑02) y todo lo que ya prueban las pruebas automatizadas del [plan de pruebas](plan_pruebas.md).
- **Desde la integración final:** CP‑08 a CP‑11 recorren la **Hoja del proyecto** (levantar el espacio a
  mano, importar un plano, editar un APU y guardar con fuente, ver precios y cotizar, trazabilidad y
  Excel) con personas distintas de las de CP‑07 (RNF‑13).

CP‑07 (sprint de UI, [PLAN_UI.md](../PLAN_UI.md)) es de otra naturaleza: no lo ejecuta quien anota, sino una persona que nunca vio la aplicación, y mide RNF‑10.

**Puesta al día de la integración final del sprint SF (2026‑10‑05).** La navegación pasa a un menú
**superior** con una **barra de herramientas** debajo, y aparece la pantalla **Hoja del proyecto**
(UC‑13 a UC‑16). CP‑07 se actualiza a esa interfaz y se escriben **CP‑08 a CP‑11** como casos IEEE 829
completos, con persona y con RNF‑13 (sección 6.1). Es un cambio previo a la primera sesión de Med
(bitácora del sprint final). CP‑01 a CP‑06 no cambian de fondo: solo el nombre del menú.

## 2. Elementos a probar

| Elemento | Qué es |
|---|---|
| `ui/paginas/componer.py` | la pantalla que se prueba (UC‑10 componer, UC‑11 editar) |
| `ui/composicion.py` | el buscador de la referencia MaPreX y la lectura de las tablas |
| `core/budget/excel.py` | el libro de Excel con sus cuatro hojas |
| `scripts/seed_demo.py` | la siembra que deja la base lista para la prueba |
| `ui/paginas/hoja.py`, `ui/hoja.py` | la Hoja del proyecto (CP‑08 a CP‑11): tablas del espacio, APU, precios, versiones, plano y Excel |
| `ui/barra.py` | la barra de herramientas (Proyecto, Importar plano, Precios, Auditar, Guardar versión, Exportar Excel, Recorrido guiado) |
| `adapters/espacio/planos/` | la importación de planos DXF e IFC (CP‑09) |
| `scripts/seed_of001.py` | la siembra de OF‑001 en `data/prueba_sf.db` para CP‑08 a CP‑11 |

## 3. Naturaleza de los datos

**Los datos sembrados son didácticos, no de obra ejecutada.** Las cinco partidas `LB-*` de la
clínica y las tres partidas `DEMO-*` son ejercicios académicos ficticios; los precios de la
referencia MaPreX son una referencia publicada que se usa como sugerencia. La declaración completa
vive una sola vez en [NORMAS.md §1](../NORMAS.md#1-qué-es-este-proyecto). La partida `PRUEBA-01-TUB`
que se compone en este guion es, igualmente, un caso de prueba.

## 4. Entorno y preparación

**Requisitos:** la copia del repositorio, `uv` instalado y un navegador. Los resultados esperados se
obtuvieron en Windows 11 con Python 3.13 y Streamlit 1.62.0.

> **Esta prueba trabaja sobre su propia base, `data/prueba_arenia.db`, y nunca sobre
> `data/apu.db`**, la base de trabajo de la aplicación. La siembra con `--reiniciar` borra la base
> que se le indica antes de volver a sembrarla: por eso toda orden de este guion lleva
> `--db data/prueba_arenia.db`, y la aplicación se abre con `ARENIA_CASO=data/prueba_arenia.db`,
> que fija ese caso para todas las pantallas (sección 4, paso 3).

**Antes de empezar (protección de la base de trabajo).** Anote en la sección 8 si existe
`data/apu.db` **en esta copia de trabajo** (la carpeta del repositorio en la que está parado ahora,
no la copia desechable del paso 1) y, si existe, su fecha y hora de modificación. En PowerShell:
`Get-Item data/apu.db | Select-Object LastWriteTime`; en bash: `ls -l --time-style=full-iso data/apu.db`.
Si no existe, anote «no existe».

1. **Cree una copia desechable del repositorio y trabaje sobre ella, nunca sobre esta copia de
   trabajo.** Desde U1 (fase C3) la aplicación abre el caso que nombra `ARENIA_CASO` (`ui/caso.py`)
   en todas las pantallas, pero la copia desechable se conserva como segunda barrera: si la
   variable faltara o tuviera una errata, la aplicación abriría `data/apu.db` de la carpeta desde la
   que se ejecuta. Trabajar fuera de esta copia de trabajo evita tocar su `data/apu.db` en cualquier
   caso. Desde la raíz del repositorio:

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

3. Abra la aplicación con el caso de prueba. En bash:

   ```
   ARENIA_CASO=data/prueba_arenia.db uv run python -m streamlit run ui/app.py
   ```

   En PowerShell:

   ```
   $env:ARENIA_CASO = "data/prueba_arenia.db"; uv run python -m streamlit run ui/app.py
   ```

   Se abre el navegador en **Inicio**. Compruebe que la barra lateral, bajo **Caso abierto**, nombra
   `data/prueba_arenia.db` y que su resumen empieza por `8 partidas`. Si nombra otra base, cierre
   la aplicación y vuelva a arrancarla con la variable. Después, en el menú **superior** (sección
   **Trabajo**), elija **Componer una partida**. Recargar la página (F5) o abrir otra pestaña **no**
   cambia el caso abierto: la variable lo mantiene.

   Desde la integración final el menú de pantallas va **arriba** y, debajo de él, hay una **barra de
   herramientas** (Proyecto, Importar plano, Precios, Auditar, Guardar versión, Exportar Excel y
   Recorrido guiado); la barra lateral conserva el **Caso abierto** y el paso del recorrido. CP‑01 a
   CP‑06 no usan la barra de herramientas.

### 4.1 Base propia de CP‑08 a CP‑11 (`data/prueba_sf.db`)

CP‑08 a CP‑11 no usan `data/prueba_arenia.db`: trabajan sobre su propia base, **`data/prueba_sf.db`**, con
la oficina OF‑001 y la misma protección de `data/apu.db` (sección 4, «Antes de empezar» y «Al terminar la
prueba»). Dentro de la copia desechable del paso 1 (con `uv sync --extra ui --extra ml --extra planos`):

```
uv run python scripts/seed_of001.py --db data/prueba_sf.db --reiniciar
```

**Comprobación de la preparación.** La terminal debe mostrar, entre otras, estas líneas:
`Proyecto: OF-001: oficina con baño, cocineta y puestos (caso de prueba)`, `Version 001: 30 partidas`,
`Total: 2703.86 USD` y `Auditoria: 33 hallazgo(s), CUMPLE`. La orden se niega a escribir en `data/apu.db` y,
sobre una base que ya existe, exige `--reiniciar`: cada participante empieza de la misma base. Después, la
aplicación se abre con el caso de prueba (en bash `ARENIA_CASO=data/prueba_sf.db uv run python -m streamlit
run ui/app.py`; en PowerShell `$env:ARENIA_CASO = "data/prueba_sf.db"; uv run python -m streamlit run
ui/app.py`) y la barra lateral, bajo **Caso abierto**, nombra `prueba_sf.db` con `30 partidas · 49 insumos ·
lista vigente: Lista MaPreX jul-2026 (OF-001)`. Para CP‑09 el observador deja una copia de
`tests/fixtures/planos/of001.dxf` en el escritorio con el nombre `of001.dxf`.

**Orden de ejecución.** Los casos se ejecutan en orden, de CP‑01 a CP‑06, sobre una base recién
sembrada: CP‑02 y CP‑03 continúan donde terminó CP‑01. Si repite la prueba, vuelva al paso 2.

**Al terminar la prueba.** Vuelva a la copia de trabajo original (`cd` fuera de
`../tesis-prueba-manual`) y repita allí la comprobación de «Antes de empezar»; anótela en la sección
8: `data/apu.db` **de esta copia de trabajo** debe seguir igual que al empezar (o seguir sin
existir). Si cambió, la ejecución es **FALLA** aunque todos los casos hayan pasado: la prueba tocó la
base de trabajo. Por último, borre la copia desechable (paso 1).

## 5. Cómo leer los números y cómo anotar

- La pantalla muestra los importes con **dos decimales** (por ejemplo `20.11`): el sistema calcula
  con decimales exactos y solo redondea al presentar (INV‑045). Donde ayuda a entender un caso, el
  resultado esperado da entre paréntesis el valor exacto que calculó el sistema; compare en pantalla
  el de dos decimales.
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
- **Precondición:** base recién sembrada (sección 4) y la página *Componer una partida* abierta, con
  las tablas vacías y `data/prueba_arenia.db` bajo **Caso abierto** en la barra lateral (la
  aplicación arrancó con `ARENIA_CASO`, sección 4, paso 3).

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

  | Métrica | Valor esperado | Valor exacto del sistema |
  |---|---|---|
  | Materiales | `15.32` | 15.316943 |
  | Equipos | `0.15` | 0.1506512680 |
  | Mano de obra | `0.43` | 0.432563 |
  | Costo directo | `15.90` | 15.9001572680 |
  | Con administracion | `18.29` | 18.285180858200 |
  | **Precio unitario** | **`20.11`** | 20.11369894402000 |

  y **Guardar composicion está deshabilitado** (gris) porque faltan las condiciones (RF‑33).
- Paso 9: el botón **Guardar composicion** se habilita.
- Paso 10: aparece el mensaje verde
  `Composicion guardada para la partida PRUEBA-01-TUB: precio unitario 20.11.`

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑02 — Editar la partida de CP‑01 (UC‑11)

- **Objetivo:** guardar de nuevo la misma partida con otro rendimiento y comprobar que se edita, no
  se duplica, y que el historial de rendimientos gana una observación.
- **Trazabilidad:** UC‑11; RF‑26, RF‑27, RF‑33.
- **Precondición:** CP‑01 terminado con PASA, en la misma pestaña y sin recargar la página, con
  `data/prueba_arenia.db` bajo **Caso abierto** en la barra lateral.

**Pasos**

1. Observe el campo **Rendimiento — unidades por día**.
2. Cambie el rendimiento a `120` y pulse Enter.
3. Pulse **Guardar composicion**.
4. Para comprobar el historial, cambie el rendimiento a `150` y pulse Enter. **No guarde.**
5. Vuelva a escribir `120` en el rendimiento (así queda listo para CP‑03).
6. Abra una **segunda pestaña** del navegador con la misma dirección de la aplicación y, en ella,
   elija **Catalogo de partidas e insumos** en el menú superior. Compruebe que la barra lateral de
   esa pestaña también muestra `data/prueba_arenia.db` bajo **Caso abierto** (la variable
   `ARENIA_CASO` lo fija para toda pestaña nueva). Observe la tabla **Partidas**. Cierre esa pestaña
   y vuelva a la primera.

**Resultado esperado**

- Paso 1: el campo muestra `100`, el rendimiento guardado en CP‑01, precargado desde el historial.
- Paso 2: **Precio unitario** `19.99` (exacto: 19.99073793585). Aparece además el aviso
  azul de la ayuda 4 de AREN.IA: `El precio construido cae dentro del rango de la clase 3 de AACE
  International frente a la estimacion por reglas.`
- Paso 3: mensaje verde `Composicion guardada para la partida PRUEBA-01-TUB: precio unitario
  19.99.`
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
  rendimiento `120` y **Precio unitario** `19.99`, con `data/prueba_arenia.db` bajo **Caso abierto**
  en la barra lateral. Si el rendimiento no está en `120`, escríbalo.

**Pasos**

1. En la tabla **Mano de obra**, agregue una fila (el **+** bajo la tabla) y escriba: descripcion
   `Instalador a destajo`, cantidad `1`, sueldo `1.50`, y en modalidad elija `destajo`.
2. Observe **Mano de obra** y **Precio unitario** en el desglose en vivo.
3. En esa misma fila, cambie la modalidad a `jornal`.
4. Observe de nuevo el desglose.
5. **No guarde.** (El caso solo observa; la partida guardada en CP‑02 no cambia.)

**Resultado esperado**

| Estado | Mano de obra | Precio unitario | Valores exactos del sistema |
|---|---|---|---|
| Antes del paso 1 | `0.36` | `19.99` | 0.36046916… · 19.99073793585 |
| Paso 2 (la fila a **destajo**) | `1.86` | `21.89` | 1.86046916… · 21.88823793585 |
| Paso 4 (la misma fila a **jornal**) | `0.46` | `20.11` | 0.4563025 · 20.11196710251… |

**Por qué.** A destajo, `1.50` no es un jornal diario: es lo que se paga **por cada metro
instalado** (artículo 114 de la LOTTT, decisión D9). Por eso entra completo a la mano de obra, que
sube exactamente `1.50`: sin multiplicarse por (1 + FCAS), sin bono de alimentación y sin dividirse
entre el rendimiento. El precio unitario sube `1.8975` (1,50 con administración y utilidad en
cascada: 1,50 × 1,15 × 1,10; en pantalla, de `19.99` a `21.89`). La misma línea declarada a jornal
se trata como un obrero más de la cuadrilla: su sueldo lleva el FCAS y el bono, y todo se divide
entre los 120 m por día; la mano de obra sube solo `0.0958333…` (en pantalla, de `0.36` a `0.46`) y
el precio unitario `0.1212291…` (de `19.99` a `20.11`).

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑04 — Un rendimiento fuera de rango en `DEMO-01-INST` (RF‑27)

- **Objetivo:** comprobar que un rendimiento que se aparta de lo observado dispara la advertencia
  RF‑27 y que, aun así, guardar sigue habilitado.
- **Trazabilidad:** UC‑06, UC‑11; RF‑26, RF‑27, RF‑33.
- **Precondición:** base sembrada (la partida `DEMO-01-INST` trae dos observaciones de rendimiento:
  50 y 60 m por día). Recargue la página con **F5** para empezar con las tablas vacías y compruebe
  que sigue `data/prueba_arenia.db` bajo **Caso abierto** en la barra lateral (la recarga no cambia
  el caso: lo mantiene `ARENIA_CASO`).

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
  compruebe que sigue `data/prueba_arenia.db` bajo **Caso abierto** en la barra lateral. Excel o
  LibreOffice Calc para abrir el libro.

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
- **Precondición:** CP‑05 terminado, en la misma pestaña y con `data/prueba_arenia.db` bajo **Caso
  abierto** en la barra lateral.

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
parte de lo que se prueba (principio 7 de [NORMAS.md](../NORMAS.md)).

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑07 — Una persona nueva llega sola del Inicio al Excel auditado

> **CP‑07 es ejecutable desde U1 y se ejecuta en la fase Med (GU1b).** La fase C3 lo dejó listo:
> `ui/caso.py` lee `ARENIA_CASO` y la aplicación abre el caso de cada escenario en todas las
> pantallas. La medición con personas no es de C3: C3 cierra la compuerta GU1a (U1 completa sin
> CP‑07) y la medición cierra GU1b en Med. Con la misma protección de INV‑065 que los demás casos,
> se ejecuta **dentro de la copia desechable de la sección 4** (paso 1,
> `git worktree add ../tesis-prueba-manual HEAD`), nunca en la copia de trabajo, y se hacen las
> comprobaciones de `data/apu.db` de «Antes de empezar» y «Al terminar la prueba» de esa sección.

- **Objetivo:** medir si una persona que nunca vio la aplicación, sin explicación previa y sin que
  nadie la guíe, llega desde el Inicio hasta un presupuesto en Excel con su hoja de auditoría.
- **Trazabilidad:** UC‑12; RF‑36 a RF‑43; **RNF‑10**; compuerta GU1b de [PLAN_UI.md](../PLAN_UI.md)
  (fase Med; GU1a cierra U1 sin este caso).
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
5. Compruebe que el navegador abrió en **Inicio**, que el menú de pantallas está **arriba** (con la barra
   de herramientas debajo) y que la barra lateral, bajo **Caso abierto**, nombra la base del
   escenario. Cierre toda otra pestaña.
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
6. **La barra de herramientas** (Proyecto, Importar plano, Precios, Auditar, Guardar versión, Exportar
   Excel y Recorrido guiado) es parte de la aplicación que se mide: si el participante la usa, no cuenta
   como ayuda ni se le explica. **«Exportar Excel» de la barra produce el libro de la *Hoja del
   proyecto* (`hoja_<código>.xlsx`), no `presupuesto_<código>*.xlsx`:** el estado final de CP‑07 sigue
   siendo el de «Estado final observable» (el archivo de *Elaborar un presupuesto*). Si el participante
   termina con el libro de la barra, el observador lo anota como punto de detención y el escenario no
   alcanzó el estado final. (Ruling de la integración: no se amplía el criterio de CP‑07 al cambiar la
   interfaz; ver la bitácora.)
7. **Oferta única de ayuda:** si pasan 3 minutos sin avanzar —sin cambiar de pantalla ni producir
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

### CP‑08 — Levantar a mano el baño de OF‑001 y obtener su presupuesto auditado

> **CP‑08 a CP‑11 son casos con persona (RNF‑13) y se ejecutan en la fase Med.** Se preparan con la
> base de la sección 4.1 (`data/prueba_sf.db`), dentro de la copia desechable de la sección 4, y con las
> mismas comprobaciones de `data/apu.db` de «Antes de empezar» y «Al terminar la prueba». Su
> consigna literal, sus paradas y su criterio están en la sección 6.1.

- **Objetivo:** que una persona que no vio la aplicación describa un baño en las tablas de la hoja
  (un ambiente, una fuente, dos puntos de agua) y obtenga sus cantidades derivadas, su presupuesto y su
  informe de auditoría.
- **Trazabilidad:** UC‑13; RF‑44 a RF‑47, RF‑61; RNF‑13.
- **Precondición:** `data/prueba_sf.db` recién sembrada (sección 4.1); la aplicación abierta con
  `ARENIA_CASO=data/prueba_sf.db` en **Inicio**, con `prueba_sf.db` bajo **Caso abierto**; la pantalla
  **Hoja del proyecto** (menú superior, sección **Trabajo**) con **(borrador nuevo, sin guardar)** en
  el selector *Proyecto* y la pestaña **Espacio y metrajes**. (Desde la integración final el caso **termina
  guardando**: el proyecto se crea al final, en los pasos 7 y 8, y el borrador pasa a él. Los pasos 7 y 8 suman
  unos minutos al caso: ver la nota de RNF‑13 en 6.1.) La persona tiene en papel la **ficha del
  baño** (tabla siguiente).

**Ficha del baño** (se entrega impresa; metros; eje z hacia arriba desde el piso terminado; son supuestos
declarados de la memoria `tests/fixtures/memorias/bano_of001.md`, no un plano real)

| Tabla | id | Datos |
|---|---|---|
| Orígenes de medida | `O1` | tipo `supuesto`; referencia `motivo=ejemplo de memoria de calculo` |
| Ambientes | `BAN-01` | nombre `Bano`; x0 `0`; y0 `0`; largo `2`; ancho `1.5`; alto `2.5`; origen `O1` |
| Fuentes | `F1` | especialidad `agua`; tipo `montante_agua`; ambiente `BAN-01`; x `0`; y `0`; z `0`; origen `O1` |
| Puntos | `P1` | nombre `lavamanos`; especialidad `agua`; tipo `agua_fria`; ambiente `BAN-01`; superficie `pared`; x `1.5`; y `0`; z `0.6`; fuente `F1`; circuito vacío; especificaciones `diametro=1/2"; llave_de_paso=si`; origen `O1` |
| Puntos | `P2` | nombre `ducha`; especialidad `agua`; tipo `agua_fria`; ambiente `BAN-01`; superficie `pared`; x `1`; y `1.5`; z `1.2`; fuente `F1`; circuito vacío; especificaciones `diametro=3/4"; llave_de_paso=si`; origen `O1` |
| Vértices de recorridos | — | ninguna fila: el sistema propone el recorrido de cada punto |

**Pasos**

1. En la tabla **Origenes de medida**, agregue una fila (el **+** bajo la tabla) y escriba los datos de `O1`.
2. Repita para **Ambientes** (`BAN-01`), **Fuentes** (`F1`) y **Puntos** (`P1` y `P2`). Las columnas con lista
   (*tipo*, *especialidad*, *superficie*) se eligen de la lista. Deje **Vertices de recorridos** vacía.
3. Observe la columna **Estado** junto a cada tabla y la tabla **Cantidades derivadas**.
4. Observe el **Total del presupuesto** y baje a **Informe de auditoria**.
5. En la pestaña **Presupuesto**, observe el precio unitario y el total de cada renglón.
6. Abra el panel **Guardar version y exportar a Excel** y observe el botón **Guardar version**.
7. En la barra de herramientas abra **Proyecto**, escriba `Baño de prueba` en *Nombre del proyecto nuevo* y
   pulse **Crear proyecto**. Observe el aviso de la hoja y el panel de guardado.
8. En *Fuente de la medida* escriba `ficha del baño de la prueba` y, en *Responsable*, su nombre (`Ing.
   Participante`). Pulse **Guardar primera versión**. Observe el mensaje, los selectores *Proyecto* y
   *Version* y la pestaña **Trazabilidad**.

**Resultado esperado**

- Paso 3: cada fila trae el Estado `ADVERTENCIA: …la medida es un supuesto declarado (origen O1: ejemplo
  de memoria de calculo)` (el origen es un supuesto, no una medición). **Cantidades derivadas** tiene
  **ocho** filas, y sus cantidades son las de la memoria a mano (exactas):

  | Partida | Unidad | Cantidad |
  |---|---|---|
  | `AF-CODO-1/2` | unidad | `1.00` |
  | `AF-CODO-3/4` | unidad | `2.00` |
  | `AF-LLAVE` | unidad | `2.00` |
  | `AF-PICADO-PARED` | m | `5.70` |
  | `AF-SALIDA` | unidad | `2.00` |
  | `AF-TEE-3/4` | unidad | `1.00` |
  | `AF-TUB-PVC-1/2` | m | `2.64` |
  | `AF-TUB-PVC-3/4` | m | `6.93` |

- Paso 4: **Total del presupuesto `172.42 USD`** (los parámetros de un borrador nuevo son los de la
  aplicación: administración 15 %, utilidad 10 %, bono de alimentación 1,00). El informe dice
  `Hallazgos: 6 · Resultado: CUMPLE`: **cuatro ADVERTENCIA** de la regla R8 (ambiente `BAN-01`, fuente `F1`,
  punto `P1` y punto `P2`: «la medida es un supuesto declarado») y **dos INFO** (R2 y R7 «no aplicable»: el
  borrador no declara curva ni plan). R9 y R10 no dan hallazgos.
- Paso 5: precio unitario y total por renglón: `AF-CODO-1/2` 3.42 y 3.42; `AF-CODO-3/4` 4.63 y 9.26;
  `AF-LLAVE` 12.59 y 25.18; `AF-PICADO-PARED` 6.81 y 38.84; `AF-SALIDA` 6.59 y 13.19; `AF-TEE-3/4` 4.47 y
  4.47; `AF-TUB-PVC-1/2` 5.82 y 15.36; `AF-TUB-PVC-3/4` 9.05 y 62.71 (la suma de los renglones
  redondeados da 172.43; el total exacto es 172.42).
- Paso 6: **Guardar version** está deshabilitado y su ayuda dice `Elija o cree un proyecto (barra superior)
  para poder guardar.` (el borrador todavía no pertenece a ningún proyecto).
- Paso 7: mensaje de la barra `Proyecto «Baño de prueba» creado y abierto.`; la hoja pasa a ese proyecto **sin
  perder lo escrito** (las tablas y el total `172.42 USD` siguen igual) y muestra el aviso azul `Este proyecto
  aún no tiene versiones. Describa el espacio (o importe un plano) y guarde la primera version abajo, con su
  fuente y su responsable.` El botón del panel se llama ahora **Guardar primera versión** y, sin fuente, su
  ayuda dice `Escriba la fuente de la medida: de donde salen los datos (un plano, un acta).`
- Paso 8: mensaje verde `Se guardo la primera version 001 del proyecto Baño de prueba (total 172.42). Quedo
  registrada su creacion, con su fuente y su responsable.`; los selectores dicen `Baño de prueba` y `001`; ya
  no hay aviso de cambios sin guardar; el **Total del presupuesto** sigue en `172.42 USD`. El informe, ahora
  con el plan secuencial de la aplicación, dice `Hallazgos: 4 · Resultado: CUMPLE`: las **cuatro ADVERTENCIA**
  de R8 (la medida es un supuesto) y ninguna INFO de R2 y R7 (la versión guardada trae curva y plan).
  **Trazabilidad** muestra el historial (`001`, elaborada, 1 cambio, vigente) y **un** registro: objeto
  `version`, clave `001`, campo `creacion`, antes vacío, después `001`, la fuente, el responsable y la fecha y
  hora.

| Resultado obtenido | Veredicto |
|---|---|
| | |

### CP‑09 — Importar el DXF de OF‑001 y cargar lo que el informe marca como pendiente

- **Objetivo:** importar un plano, leer el informe de importación, cargar las alturas que el plano no
  trae, declarar los circuitos y fusionar el plano con el borrador de la hoja sin saltar la auditoría.
- **Trazabilidad:** UC‑14; RF‑50, RF‑51; RNF‑13.
- **Precondición:** la de CP‑08 (la persona de la medición no repite CP‑08 antes: recargue la página con
  **F5** para que el borrador quede nuevo). El archivo `of001.dxf` (copia de
  `tests/fixtures/planos/of001.dxf`) está en el escritorio.
- **Nota de alcance.** El DXF de OF‑001 trae **varias** marcas, no una sola «fila»: seis alturas
  pendientes, dos circuitos de valores supuestos y siete fuentes asignadas por cercanía. Este caso pide
  resolver lo **pendiente** (las seis alturas) y declarar los circuitos; las siete aproximaciones se leen
  y quedan en el informe. (Ruling de la integración; ver la bitácora.)

**Pasos**

1. En la barra de herramientas, pulse **Importar plano**. Se abre la pestaña **Espacio y metrajes** con el
   bloque **Importar plano (DXF o IFC)** abierto.
2. En el cuadro *Plano*, elija `of001.dxf` y pulse **Leer plano**.
3. Lea los cuatro contadores y la tabla del informe.
4. En **Alturas pendientes** escriba `2,50` en cada uno de los seis campos y pulse **Cargar alturas**.
5. En **Circuitos por declarar** revise `C1` y `C2` y pulse **Declarar circuitos** (confirma los valores
   que trae el plano).
6. Pulse **Fusionar con el espacio del borrador**.
7. Observe las tablas, **Cantidades derivadas**, el **Total del presupuesto** y el **Informe de auditoria**.
8. Observe el botón **Guardar version**.
9. En la barra de herramientas abra **Proyecto**, escriba `Oficina del plano` en *Nombre del proyecto nuevo* y
   pulse **Crear proyecto**. En *Fuente de la medida* escriba `plano of001.dxf y memoria de calculo` y, en
   *Responsable*, su nombre. Pulse **Guardar primera versión** y observe el mensaje y el **Total del
   presupuesto**.

**Resultado esperado**

- Paso 3: **Importado 33**, **No reconocido 0**, **Aproximado 9**, **Pendiente 6**; la tabla del informe
  tiene 48 filas (columnas *Tipo*, *En el plano*, *Fila de la hoja*, *Qué pasó*): seis ambientes con
  «altura pendiente; entra con 2.5 m provisionales hasta cargar la real», siete puntos con «fuente RK1
  asignada por cercania» y dos circuitos con «conductores 1-1-1 y 6 puntos maximos son supuestos
  declarados». Debajo aparecen **Alturas pendientes** (seis campos: BAN‑01, COC‑01, CT‑01, REC‑01, ZA y ZB)
  y **Circuitos por declarar** (C1 y C2, cada uno con 1, 1, 1 y 6), y un aviso azul que dice que, si se
  fusiona ahora, esas alturas entran con 2,5 m provisionales.
- Paso 4: **Pendiente 0** y desaparece el bloque *Alturas pendientes*.
- Paso 5: **Aproximado 7** y desaparece el bloque *Circuitos por declarar*.
- Paso 6: aparece el mensaje verde `Se fusionó «of001.dxf» con el borrador de la hoja: 6 ambientes, 6
  fuentes y 21 puntos. Revise las filas en las tablas de abajo; la auditoría las evalúa como a las demás.
  Todavía no se guardó ninguna versión: use Guardar versión cuando esté conforme.` y el bloque de importar
  pasa a mostrar **Informe de la última fusión**.
- Paso 7: las tablas tienen **6 ambientes** (alto `2.5`), **6 fuentes** y **21 puntos**; **Cantidades
  derivadas** tiene **30 filas**, las mismas partidas y cantidades que la hoja manual de OF‑001 a ±0,001 m
  (conteos exactos), entre ellas `AF-TUB-PVC-3/4` 6.93 m, `AF-TUB-PVC-1/2` 8.25 m, `DR-TUB-PVC-2` 4.35 m,
  `DT-UTP-CAT-6` 101.64 m, `EL-COND-12-AWG` 75.57 m y `EL-COND-14-AWG` 33.00 m. **Total del presupuesto
  `2577.59 USD`**, el mismo de la hoja manual de OF‑001 con los parámetros por defecto. El informe dice
  `Hallazgos: 2 · Resultado: CUMPLE`: dos INFO (R2 y R7, sin curva ni plan) y R8, R9 y R10 en cero (el plano
  es un origen de medida con archivo y las alturas están cargadas).
- Paso 8: **Guardar version** está deshabilitado y su ayuda dice `Elija o cree un proyecto (barra superior)
  para poder guardar.` (el borrador todavía no pertenece a ningún proyecto).
- Paso 9: la hoja pasa al proyecto nuevo sin perder las tablas ni el total; aparece el aviso `Este proyecto aún
  no tiene versiones…`; al guardar, mensaje verde `Se guardo la primera version 001 del proyecto Oficina del
  plano (total 2577.59).…`; el **Total del presupuesto** sigue en `2577.59 USD` (los parámetros por defecto
  se guardan con la versión) y las tablas conservan las 6 ambientes, 6 fuentes y 21 puntos al reabrirse.

| Resultado obtenido | Veredicto |
|---|---|

### CP‑10 — Cambiar la cantidad de una línea, ver el recálculo y el punto de equilibrio, guardar con fuente

- **Objetivo:** editar la cantidad de una línea de un APU en la copia de la versión, ver el recálculo y el
  punto de equilibrio, comprobar que guardar sin fuente se rechaza y guardar con fuente y responsable.
- **Trazabilidad:** UC‑15, UC‑16; RF‑52, RF‑53, RF‑55, RF‑58; RNF‑13.
- **Precondición:** `data/prueba_sf.db` recién sembrada (sección 4.1) y la aplicación recién arrancada
  sobre ella (**CP‑10 se ejecuta antes que CP‑11**, que parte de la versión que deja este caso). En
  **Hoja del proyecto**: *Proyecto* `OF-001: oficina con baño, cocineta y puestos (caso de prueba)` y
  *Version* `001 (vigente)` (se pueden elegir en la propia pantalla o abriendo el proyecto con la
  herramienta **Proyecto** de la barra).

**Pasos**

1. Elija el proyecto OF‑001 y la versión `001`. Observe el **Total del presupuesto** y la pestaña
   **Punto de equilibrio**.
2. Abra la pestaña **APU**, elija la partida `AF-TUB-PVC-3/4` y, en **Materiales**, cambie la cantidad de
   `Tubo PVC 3/4 pulg A.B. presion agua fria [MT2050]` de `1` a `1.05`.
3. Observe el aviso amarillo, el **Precio unitario** de la partida y, en **Punto de equilibrio**, las
   cifras nuevas.
4. Abra el panel **Guardar version y exportar a Excel** sin escribir nada y observe el botón **Guardar
   version**.
5. En *Fuente del cambio* escriba `ficha tecnica del fabricante: 5 % de desperdicio en el tubo` y, en
   *Responsable*, su nombre (`Ing. Participante`). Pulse **Guardar version**.
6. Observe el mensaje, el selector *Version* y la pestaña **Trazabilidad**.

**Resultado esperado**

- Paso 1: **Total del presupuesto `2703.86 USD`**. **Punto de equilibrio:** `Se alcanza en Dia 23, al 46 %
  de ese período.`; Ventas (contrato) `2703.86 USD`, Costo variable `2137.44 USD`, Costo fijo `320.62 USD`,
  Utilidad `245.81 USD`, Punto de equilibrio `1530.49 USD`, Como % de las ventas `56.60 %`.
- Paso 3: aviso amarillo `1 cambios sin guardar. Si cierra la hoja o abre otra version se pierden.`;
  **Precio unitario** de `AF-TUB-PVC-3/4` pasa de `9.45` a `9.78` (Materiales `5.68` → `5.94`); **Total
  `2706.12 USD`**; punto de equilibrio: `Se alcanza en Dia 23, al 45 % de ese período.`, Ventas `2706.12`,
  Costo variable `2139.23`, Costo fijo `320.88`, Utilidad `246.01`, Punto de equilibrio `1531.77 USD`,
  `56.60 %`. (El total sube 2,26 USD: 6,93 m × 0,05 × 5,1648 × 1,15 × 1,10.)
- Paso 4: el panel se abre solo; **Guardar version está deshabilitado** y su ayuda dice `Escriba la fuente
  del cambio: por que se cambia y con que respaldo.` (el rechazo de guardar sin fuente: no se escribe
  nada).
- Paso 5: mensaje verde `Se guardo la version 002 con 1 cambios registrados.`
- Paso 6: *Version* ofrece `001` y `002 (vigente)`. **Trazabilidad** muestra el historial (`001` elaborada;
  `002` edición, sale de `001`, 1 cambio, vigente) y el registro de la `002`: objeto `apu`, clave
  `AF-TUB-PVC-3/4|Tubo PVC 3/4 pulg A.B. presion agua fria [MT2050]`, campo `cantidad`, antes `1`, después
  `1.05`, la fuente, el responsable y la fecha y hora.

| Resultado obtenido | Veredicto |
|---|---|

### CP‑11 — Ver el origen de un precio, registrar una cotización, ver la trazabilidad y exportar el Excel

- **Objetivo:** ver de dónde sale el precio de un insumo, registrar una cotización, ver dónde queda el
  cambio y exportar el libro de Excel de la hoja.
- **Trazabilidad:** UC‑15; RF‑56, RF‑59; RNF‑13.
- **Precondición:** **CP‑10 terminado con PASA**, sin cerrar la aplicación: la versión `002` (vigente) de
  OF‑001 abierta en **Hoja del proyecto**. La carpeta de descargas vacía (o su contenido anotado).

**Pasos**

1. En la barra de herramientas pulse **Precios**. Busque en la tabla el insumo `MAT-003`, el tubo PVC de
   3/4 pulg, y lea su precio, su lista y su Estado.
2. En **Registrar una cotizacion** elija el insumo `MAT-003`; escriba *Precio cotizado* `5.50`, *Proveedor*
   `Ferreteria Los Andes`, *Numero de la cotizacion* `COT-2026-0412` y *Responsable* `Ing. Participante`;
   deje la fecha de hoy y pulse **Cotizar**.
3. Observe el mensaje y la fila de `MAT-003` en la tabla de precios.
4. Abra la pestaña **Trazabilidad**.
5. En la barra de herramientas pulse **Exportar Excel** y, en el panel *Guardar version y exportar a Excel*,
   **Descargar Excel**. Abra el archivo.

**Resultado esperado**

- Paso 1: se abre la pestaña **Precios** (la tabla de **49** insumos). `MAT-003`: `Tubo PVC 3/4 pulg A.B.
  presion agua fria [MT2050]`, **Precio** `5.16`, **Lista** `Lista MaPreX jul-2026 (OF-001)`, moneda `USD`,
  **Estado** `Sin referencia ni cotización: el precio no tiene fuente`.
- Paso 3: mensaje verde `Se guardo la version 003 con la cotizacion de MAT-003.`; la fila de `MAT-003`
  pasa a **Precio** `5.50`, **Cotizacion** `Ferreteria Los Andes, COT-2026-0412, <fecha de hoy>` y **Estado**
  `OK`.
- Paso 4: el historial tiene `001` (elaborada), `002` (edición, sale de `001`) y `003` (**cotizacion**, sale
  de `002`, 1 cambio, vigente); el registro de la `003`: objeto `precio`, clave `MAT-003`, campo
  `cotizacion`, antes `5.1648`, después `5.50`, fuente `Cotizacion COT-2026-0412 de Ferreteria Los Andes
  (<fecha de hoy>).` y su responsable.
- Paso 5: el archivo se llama `hoja_003.xlsx` y tiene **catorce hojas**, en este orden: *Espacio y
  metrajes*, *APU*, *Presupuesto*, *Plan y curva*, *Punto de equilibrio*, *Precios*, *Parametros*,
  *Auditoria*, *Trazabilidad*, *Esp origenes*, *Esp ambientes*, *Esp fuentes*, *Esp puntos* y *Esp
  vertices*. La hoja *Trazabilidad* tiene **una** fila de datos (`002`, `003`, `precio`, `MAT-003`,
  `cotizacion`, `5.1648`, `5.50`, la fuente, el responsable y la fecha y hora). Las fórmulas del libro
  (APU, Presupuesto, Punto de equilibrio) se calculan al abrirlo.

| Resultado obtenido | Veredicto |
|---|---|

### 6.1 RNF‑13 — Cómo se miden CP‑08 a CP‑11

RNF‑13 (ERS §9): en las condiciones de CP‑07, con el **mismo número y perfil** de participantes que CP‑07
pero **personas distintas**, cada caso de CP‑08 a CP‑11 se completa **sin ayuda** en **≤ 15 min** por todos
los participantes; el bloque B del anexo A de [dossier_g0.md](dossier_g0.md) da **≥ 4,0** y ningún ítem
queda por debajo de 3. El veredicto es **por caso**. Todo lo de esta sección se fija **antes de medir** y no
se cambia después de ver un resultado.

**Participantes (n y perfil declarados).** **n = 2**, igual que CP‑07 (dos personas, una por sesión), con el
perfil de CP‑07 (se anota profesión, años de experiencia con presupuestos de obra y si ha usado
aplicaciones web de datos; sin nombre). **Personas distintas** de las de CP‑07 y, con la misma regla de
exclusión cruzada de esos protocolos, de las que hayan hecho la medición del indicador 3 o la de RNF‑04
([protocolo_indicador3.md](protocolo_indicador3.md), [protocolo_rnf04.md](protocolo_rnf04.md)): nadie ya
expuesto a la tarea en otra medición. Ninguna vio antes la aplicación ni sus documentos; la segunda no
presenció la sesión de la primera. Cada participante hace los cuatro casos **en este orden: CP‑08, CP‑09,
CP‑10, CP‑11** (CP‑10 antes que CP‑11, que parte de su versión).

**Efecto de RI‑7 resuelto (integración final).** CP‑08 y CP‑09 ya **terminan guardando** su primera versión
(pasos 7 y 8 de CP‑08, paso 9 de CP‑09): suman unos minutos a cada caso, pero el umbral de ≤ 15 min **no se
cambia** (se fijó antes de medir y esta suma no lo cambia de forma material; si algún participante supera el
umbral solo por esos pasos, se anota en el registro como hallazgo de la medición, no como cambio del
umbral). **CP‑10 y CP‑11 siguen partiendo de OF‑001 `001` de `data/prueba_sf.db`, no de lo creado en CP‑08 y
CP‑09**: sus valores esperados (2703.86, Día 23, `MAT‑003`) son los de OF‑001 con el bono adoptado del caso y
los de lo creado en CP‑08 y CP‑09 serían otros (172.42 y 2577.59, con el bono por defecto); partir de lo
creado obligaría a reescribir y volver a ejecutar esos dos casos. Queda declarado.

**Condiciones.** Las de CP‑07: copia desechable (sección 4, paso 1), base propia
`data/prueba_sf.db` sembrada de nuevo antes de **cada participante** (sección 4.1), `ARENIA_MODO_ENTREGA`
sin definir, `data/apu.db` comprobada antes y después, observador distinto del participante, carpeta de
descargas vacía, y el mismo guion del observador de CP‑07 (puntos 1 a 7: no contestar preguntas, anotar
preguntas y puntos de detención, qué cuenta como ayuda, oferta única de ayuda) **con los umbrales de esta
sección**. El participante no recibe explicación previa de la aplicación.

**Consigna literal de cada caso** (se lee tal cual, una sola vez, al entregarle el material; el cronómetro
arranca al terminar de leerla):

- **CP‑08.** «Esta aplicación sirve para armar y auditar presupuestos de obra. Le entrego la ficha de un
  baño. Le pido que, sin ayuda, cargue esos datos en la aplicación y obtenga el presupuesto auditado de su
  instalación de agua fría y que, al terminar, me diga cuántas advertencias tiene la auditoría y cuál es el
  total. Puede pensar en voz alta. Yo solo voy a observar y a tomar notas.»
- **CP‑09.** «Le entrego el plano de una oficina, en el archivo `of001.dxf` del escritorio. Le pido que, sin
  ayuda, lo cargue en la aplicación, deje cargadas las alturas de los ambientes en 2,50 metros y lleve el
  plano a la hoja del proyecto y que, al terminar, me diga el total del presupuesto. Puede pensar en voz alta.
  Yo solo voy a observar y a tomar notas.»
- **CP‑10.** «El proyecto de esta oficina ya está en la aplicación. Le pido que, sin ayuda, cambie la
  cantidad de tubo de la partida AF‑TUB‑PVC‑3/4 de 1 a 1,05 metros por cada metro instalado; que intente
  guardar ese cambio sin escribir ninguna fuente y me diga qué pasa; que lo guarde después como versión
  nueva con la fuente y el responsable que usted escriba; y que me diga cuánto cambió el total y en qué día
  se alcanza el punto de equilibrio. Puede pensar en voz alta. Yo solo voy a observar y a tomar notas.»
- **CP‑11.** «Le pido que, sin ayuda, averigüe de dónde sale el precio del tubo PVC de 3/4 de pulgada
  (código MAT‑003); que registre una cotización de 5,50 dólares de la Ferretería Los Andes, número
  COT‑2026‑0412; que me diga dónde queda registrado ese cambio; y que obtenga el presupuesto en Excel.
  Puede pensar en voz alta. Yo solo voy a observar y a tomar notas.»

**Estado final observable** (el observador lo comprueba sobre la base y la carpeta de descargas, no sobre
lo que quede abierto en pantalla; tras detener el cronómetro):

| Caso | Se alcanza cuando… |
|---|---|
| CP‑08 | las tablas tienen 1 origen, 1 ambiente, 1 fuente y 2 puntos, **Cantidades derivadas** tiene las ocho filas de CP‑08, y el participante dice, de palabra, **cuatro** advertencias y un total de **172.42** (se acepta 172.42 ± 0,01) |
| CP‑09 | **Pendiente 0** en el informe de importación, el mensaje verde de fusión (`6 ambientes, 6 fuentes y 21 puntos`), los seis ambientes con alto `2.5` en la tabla, y el participante dice un total de **2577.59** (± 0,01) |
| CP‑10 | existe la versión `002` (vigente) de OF‑001 con **un** registro de cambio (`cantidad`, `1` → `1.05`) con una fuente y un responsable **no vacíos** (se lee en la base y en la pestaña Trazabilidad); el participante dice que el total sube **2.26** (± 0,01) y que el equilibrio se alcanza en el **Día 23**, y que sin fuente el sistema no deja guardar |
| CP‑11 | existe la versión `003` (cotización) con el registro de `MAT‑003`; `hoja_003.xlsx` está en la carpeta de descargas con la hoja *Trazabilidad*; el participante dice que el precio salía de la lista `Lista MaPreX jul-2026 (OF-001)` **sin referencia ni cotización** |

**Condiciones de parada** (la primera que ocurra; son decisiones de este caso, no medidas, y se revisan con
evidencia tras la primera ejecución dejando constancia en [docs/bitacora/](bitacora/))

1. El participante alcanza el estado final del caso (éxito).
2. Se cumplen **15 minutos** desde el fin de la consigna del caso.
3. Pasan **5 minutos sin una acción nueva** (abandono; la definición de acción nueva es la del punto 3 del
   guion del observador de CP‑07).
4. El participante declara que se rinde.
5. La aplicación muestra una traza de error o deja de responder: el caso es **FALLA**, se registra como
   defecto con la pantalla y el texto visible, y no se reinicia la aplicación.

**Oferta única de ayuda:** a los **3 minutos** sin avanzar, una sola vez: «¿Quiere que le ayude?». Si acepta, el
caso queda **asistido** (FALLA) y se sigue hasta una condición de parada. Si no acepta, no se vuelve a ofrecer.

**Bloque B.** Al terminar **cada caso**, con el cronómetro ya detenido, el participante contesta a solas el
bloque B del anexo A (B4 se marca «no aplica» si no hay estado vacío que evaluar); el observador no mira.
*(Ruling de la integración: un bloque B por caso, porque RNF‑13 pide el veredicto por caso; costo: unos dos
minutos más por caso y cuatro bloques por persona.)*

**Criterio de aceptación, declarado antes de ejecutar.** Un caso **PASA** si y solo si, para **los dos
participantes**: se alcanzó el estado final **sin ayuda**, **dentro de los 15 minutos**, y el promedio del
bloque B de ese caso es **≥ 4,0 sin ningún ítem por debajo de 3** (el promedio de cada participante, no el
promedio de los dos). **FALLA** en cualquier otro caso, sin negociar. RNF‑13 se cumple si y solo si pasan
los **cuatro** casos. Una FALLA no cancela el sprint: es el dato de la tesis y de la corrección de interfaz
que le sigue, y los puntos de detención dicen dónde.

**Hoja de registro** (una por participante; una columna por caso)

| Campo | CP‑08 | CP‑09 | CP‑10 | CP‑11 |
|---|---|---|---|---|
| Perfil del participante (sin nombre) | | | | |
| Fecha y hora de inicio · commit probado | | | | |
| Tiempo total (min; del fin de la consigna al estado final) | | | | |
| Preguntas al observador (minuto · cuál) | | | | |
| Oferta de ayuda: minuto · ¿aceptada? | | | | |
| Puntos de detención (minuto · pantalla · qué dijo) | | | | |
| Condición de parada (1–5) | | | | |
| Estado final comprobado (sí/no, con el detalle) | | | | |
| Bloque B: B1 · B2 · B3 · B4 · B5 · B6 · B7 · promedio | | | | |
| `data/apu.db` sin cambios al terminar (sí/no) | | | | |
| Veredicto del caso (para este participante) | | | | |

**Veredicto de cada caso:** CP‑08 ____ · CP‑09 ____ · CP‑10 ____ · CP‑11 ____ (PASA solo si los dos
participantes pasan). **Veredicto de RNF‑13:** ____ (PASA solo si pasan los cuatro casos).

## 7. Trazabilidad CP → UC / RF

| Caso | UC | RF | Otros |
|---|---|---|---|
| CP‑01 | UC‑10 | RF‑01, RF‑33, RF‑35 | referencia MaPreX |
| CP‑02 | UC‑11 | RF‑26, RF‑27, RF‑33 | ayuda 4 de AREN.IA (contraste AACE) |
| CP‑03 | UC‑10, UC‑11 | RF‑01, RF‑34 | decisión D9 ([dossier_g0.md](dossier_g0.md)) |
| CP‑04 | UC‑06, UC‑11 | RF‑26, RF‑27, RF‑33 | — |
| CP‑05 | UC‑01 | RF‑06, RF‑07, RF‑08, RF‑34 | hojas de `core/budget/excel.py` |
| CP‑06 | UC‑01, UC‑05 | RF‑02, RF‑21, RF‑23 | principio 7 de NORMAS.md §2 |
| CP‑07 | UC‑12 | RF‑36 a RF‑43 | RNF‑10; bloque B del anexo A de [dossier_g0.md](dossier_g0.md); compuerta GU1b (Med) |
| CP‑08 | UC‑13 | RF‑44 a RF‑47, RF‑61 | RNF‑13; memoria `bano_of001.md` |
| CP‑09 | UC‑14 | RF‑50, RF‑51 | RNF‑13; `tests/fixtures/planos/of001.dxf` |
| CP‑10 | UC‑15, UC‑16 | RF‑52, RF‑53, RF‑55, RF‑58 | RNF‑13; ejecutar **antes** que CP‑11 |
| CP‑11 | UC‑15 | RF‑56, RF‑59 | RNF‑13; parte de la versión que deja CP‑10 |

## 8. Registro de la ejecución

| Campo | Valor |
|---|---|
| Persona que prueba | |
| Fecha | |
| Commit probado (`git log -1 --oneline`) | |
| Sistema operativo y navegador | |
| Comprobación de la preparación (sección 4, paso 2; y 4.1 para CP‑08 a CP‑11) | |
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

**Puesta al día de la fase C3 (2026‑09‑24).** INV‑045 cambió solo la presentación: la pantalla de
componer pasa los importes por `formatear_decimal(valor, 2)`. Se volvió a ejecutar CP‑01 con
`AppTest` contra una base temporal sembrada con `scripts/seed_demo.py`: sus seis métricas y el
mensaje de guardado salen con dos decimales y coinciden con el redondeo de los valores exactos
anteriores. Los valores de dos decimales de CP‑02 y CP‑03 se obtuvieron aplicando esa misma
función a los valores exactos que el sistema produjo en `617861b`, que se conservan entre
paréntesis; el cálculo no cambió (la línea base sigue en 1 586,61 USD y 7 de 7).

**CP‑02 y CP‑03 no se volvieron a ejecutar en C3.** Es una **excepción declarada** a la regla del
párrafo anterior («se actualiza volviendo a ejecutar el recorrido, no a mano»). La causa: en esos
casos el rendimiento se vuelve a teclear después de guardar, y el `text_input` del rendimiento, que
no lleva clave, se vuelve a montar tras el guardado; `AppTest` no sigue ese campo y no toma el
valor retecleado. Sus números de dos decimales se comprobaron por otra ruta: se rehicieron las
composiciones con `core.costing.calcular_apu` y se redondearon con `formatear_decimal`, y coinciden.
Pero el **recorrido** que ejercitan cambió desde `617861b`: la precarga al editar (`b4f7321`), la
puerta única para registrar rendimientos, de donde salen las «2 observaciones» y el 100 precargado
(`3d9d4f0`), el guardado fuera de la página (`03c1ae0`) y la presentación (`934e835`). La
precarga, el historial de observaciones y los avisos de CP‑02 y CP‑03 quedan **a confirmar**: se
re‑ejecutan en la fase Med (GU1b). Si esa ejecución encuentra una diferencia, manda la ejecución.

**CP‑07 a CP‑11, integración final del sprint SF (2026‑10‑05).** Los resultados esperados de CP‑08 a CP‑11
se obtuvieron **ejecutando el sistema** sobre el commit `a8ec283` y los commits de documentos que le
siguen (no tocan el código), con `streamlit.testing.v1.AppTest` contra una base temporal sembrada con
`scripts/seed_of001.py` (nunca contra `data/apu.db`). `AppTest` no puede teclear en un `st.data_editor`:
las filas de CP‑08 y CP‑09 y la cantidad de CP‑10 se sembraron en `st.session_state` con las mismas filas que
produce la pantalla al leer el editor (el mismo recurso que usan `tests/unit/test_ui_hoja.py` y
`tests/unit/test_ui_hoja_planos.py`); **lo que solo se ve en un navegador** (teclear en las celdas, arrastrar
el archivo al cuadro *Plano*, descargar el libro, la apariencia de los contadores) **no se verificó** y se
confirma en la primera sesión de Med. Se cotejó con aritmética aparte: las ocho cantidades de CP‑08 con
`tests/fixtures/memorias/bano_of001.md` (exactas); las cantidades de CP‑09 con la hoja manual de OF‑001
(±0,001 m, prueba `tests/integration/test_aceptacion_sf.py`) y su total con la hoja manual con los mismos
parámetros (2577.59 USD, no 2703.86: esa cifra usa el bono adoptado del caso, 5.81, y un borrador nuevo
usa el de la aplicación, 1.00); los pasos 7 y 8 de CP‑08 y el paso 9 de CP‑09 (guardar la primera versión, RI‑7) se obtuvieron con `AppTest`
sobre una copia de `scripts/seed_of001.py` con un proyecto vacío (`tests/unit/test_ui_hoja_primera_version.py`
y el recorrido de CP‑08 con las filas de la ficha): el mensaje, el aviso, la ayuda del botón, los selectores y
la trazabilidad se leyeron de la pantalla; el total de CP‑09 tras guardar (2577.59) se comprobó a nivel de la
hoja (`tests/integration/test_primera_version.py`), **no** con el plano subido por la interfaz; el total de
CP‑10, 2703.86 + 6,93 × 0,05 × 5,1648 × 1,15 × 1,10 =
2706.12, y el 56,60 % del equilibrio como 0,15 / 0,265. El total de CP‑08 (172.42) se obtuvo ejecutando
el sistema: no tiene una memoria a mano propia (la suma de los renglones redondeados da 172.43).

**Puesta al día de CP‑07.** Solo cambia la interfaz que describe (menú superior, barra de herramientas,
y el aviso de que «Exportar Excel» de la barra no produce `presupuesto_<código>*.xlsx`); su consigna, sus
paradas y su criterio **no se tocaron**. Se verificó que el recorrido de CP‑07 sigue existiendo con las
pruebas `tests/unit/test_ui_recorridos.py` y `tests/unit/test_ui_app.py`; no se ejecutó con una persona.
