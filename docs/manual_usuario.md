# Manual de usuario — Sesión F.3

Guía de operación del sistema de generación y auditoría de Análisis de Precios Unitarios (APU)
para el proyectista. No hace falta saber programar: todo se opera desde la interfaz web local.
Qué es el sistema y por qué calcula como calcula está en [CLAUDE.md](../CLAUDE.md) y en la
[ERS](ERS.md); este manual solo explica **cómo usarlo**.

## 1. Requisitos e instalación

- Windows o Linux con **Python 3.12 o superior** y [uv](https://docs.astral.sh/uv/) instalados.
- Clonar o copiar la carpeta del proyecto y, dentro de ella, ejecutar:

```
uv sync --extra ui --extra api --extra civil --extra ml
```

No hay más pasos (RNF‑07). Notas:

- El extra `civil` instala `ifcopenshell` (modelos IFC); `ml` instala scikit‑learn y
  sentence‑transformers. Sin el extra correspondiente, esas funciones avisan que faltan en vez de
  fallar en silencio.
- La **primera** consulta de «Partidas similares» descarga el modelo de lenguaje y lo deja en
  caché local. Es la única conexión de red del sistema (RNF‑08); todo lo demás corre local.

## 2. Puesta en marcha

1. **Sembrar la base de datos** (una sola vez; crea `data/apu.db` con los cinco APU del caso de
   estudio):

   ```
   uv run python scripts/seed.py
   ```

   Los otros tres dominios tienen su propio catálogo, con precios publicados y fechados, cada uno en
   su base (opcional; cada comando imprime el presupuesto del dominio y su informe de auditoría):

   ```
   uv run python scripts/seed_telecom.py      # data/apu_telecom.db    presupuestos ARENAZA
   uv run python scripts/seed_industrial.py   # data/apu_industrial.db mantenimiento (precios MaPreX)
   uv run python scripts/seed_sistemas.py     # data/apu_sistemas.db   puntos de función (tabulador CIV)
   ```

   Para trabajar con uno de esos catálogos en la interfaz, escribir la ruta de su base en el
   campo **«Archivo SQLite»** de la barra lateral (todas las páginas que consultan la base lo
   tienen; por defecto dice `data/apu.db`). En la API, arrancar con la variable de entorno
   `APU_BASE` apuntando a esa base (por ejemplo `sqlite:///data/apu_telecom.db`). De dónde sale
   cada precio y con qué fecha: [manual técnico, sección 8.1](manual_tecnico.md#81-catálogos-por-dominio).

   **Dejar lista la aplicación para componer partidas (prototipo AREN.IA).** Una sola orden siembra
   la línea base de la clínica, tres partidas de demostración (`DEMO-01-INST`, `DEMO-02-VALV`,
   `DEMO-03-PRUEBA`) y el presupuesto de ejemplo `DEMO-001` con su informe de auditoría:

   ```
   uv run python scripts/seed_demo.py                                   # data/apu.db
   uv run python scripts/seed_demo.py --db data/prueba_arenia.db --reiniciar
   ```

   Es idempotente: repetirla no duplica nada. **`--reiniciar` borra la base antes de sembrarla**:
   úselo solo sobre una base de prueba, nunca sobre una con trabajo propio. Todo lo que siembra es
   un **caso didáctico** (ejercicio académico, no obra ejecutada ni precios cotizados; ver
   [CLAUDE.md §1](../CLAUDE.md)). Al terminar, la terminal muestra el total del presupuesto de
   ejemplo y la línea `Auditoria: 3 hallazgo(s), CUMPLE`.

2. **Abrir la interfaz** (se abre en el navegador, en el equipo local):

   ```
   uv run python -m streamlit run ui/app.py
   ```

   **Modo entrega.** Para mostrar solo las cinco pantallas que usa quien presupuesta
   (actualización de precios, catálogo, componer, elaborar e histórico) y ocultar las cuatro de
   investigación de la tesis (escenarios, partidas similares, simulador y visor 3D), se arranca con
   la variable `ARENIA_MODO_ENTREGA` en `1` (exactamente `1`; cualquier otro valor la deja apagada):

   ```
   ARENIA_MODO_ENTREGA=1 uv run python -m streamlit run ui/app.py                  # bash
   $env:ARENIA_MODO_ENTREGA = "1"; uv run python -m streamlit run ui/app.py        # PowerShell
   ```

3. **API HTTP** (opcional, para integrar con otro software):

   ```
   uv run uvicorn api.main:app
   ```

   La documentación interactiva queda en `http://127.0.0.1:8000/docs`. Todos los montos viajan
   como **texto** (`"1586.61"`), nunca como número JSON: así no se pierde precisión decimal.

## 3. Las pantallas

La interfaz tiene nueve páginas (menú lateral; cinco en modo entrega, sección 2). Todas presentan
los montos con dos decimales, pero **ningún cálculo interno redondea**: el redondeo es solo de
presentación.

| Página | Caso de uso | Qué hace |
|---|---|---|
| **Actualización de precios** | UC‑02 | Cargar una lista de precios nueva (CSV/XLSX) y revalorar un presupuesto guardado |
| **Catálogo** | consulta | Partidas e insumos con su precio vigente |
| **Componer partida** | UC‑10 / UC‑11 | Armar a mano una partida nueva o editar una existente, presupuestarla y exportarla (sección 3.7) |
| **Elaborar presupuesto** | UC‑01 | Extraer cantidades de una fuente por dominio y presupuestarlas |
| **Escenarios** | UC‑08 | Recalcular un presupuesto bajo supuestos («¿y si…?») sin alterarlo |
| **Histórico de precios** | UC‑02 | Cambios de precio registrados, con filtros |
| **Partidas similares** | UC‑03 | Buscar en texto libre partidas parecidas para reutilizar su desglose |
| **Simulador de listas** | apoyo | Generar listas de precios de prueba, deterministas |
| **Visor 3D** | apoyo a UC‑01 | Ver el modelo IFC junto a la tabla elemento ↔ partida |

### 3.1 Elaborar un presupuesto (UC‑01)

1. Elegir el **dominio** (civil, telecom, industrial o sistemas) y el **archivo fuente**. Hay
   muestras listas en `data/samples/` (sección 6).
2. El adaptador del dominio extrae el **cómputo**: una tabla de cantidades donde cada fila
   declara de dónde salió (`origen_id`) y, si vino de una regla paramétrica, la expresión que la
   produjo. En el dominio civil, un archivo `.ifc` trae sus códigos de partida en el propio
   modelo; un CSV pide asociar cada tipo de elemento a una partida del catálogo.
3. Al presupuestar, el sistema calcula cada precio unitario con la estructura venezolana
   (prestaciones, bono, administración y utilidad en cascada), arma el total y la curva de
   inversión **y audita el resultado siempre**: el informe aparece sin pedirlo.

### 3.2 Actualizar precios masivamente (UC‑02)

1. Preparar la lista nueva como CSV o XLSX con columnas `tipo,insumo,unidad,precio`
   (`tipo` ∈ material, equipo, mano_obra; ejemplo en `data/samples/precios/`).
2. Cargarla en la página: el sistema valida el archivo (si falta una columna o un precio no es
   un número, lo dice con archivo y fila), detecta qué insumos cambiaron y recalcula **todos**
   los APU afectados sin editar ninguna composición.
3. Revisar el **comparativo** (precio unitario antes/después por partida, incidencia en el
   total) y el informe de auditoría de la versión nueva; confirmar para guardarla o descartarla.
   Cada cambio queda en el histórico con precio anterior, nuevo, variación y fecha.

La decisión de guardar se toma con el número de **insumos afectados**, no con la variación del
total: una lista puede cambiar insumos que este presupuesto no usa (variación 0) y el cambio
sigue siendo real.

### 3.3 Reutilizar partidas (UC‑03)

Escribir la descripción en texto libre («excavación de zanja a mano», por ejemplo). El sistema
propone hasta **tres** partidas del catálogo con su puntaje de similitud (0 a 1; por debajo de
0,5 no propone). Al desplegar una propuesta se ven su desglose completo, su rendimiento y la
referencia a la partida de origen con el puntaje que la propuso.

### 3.4 Rendimientos reales de obra (UC‑06)

Se registran por la API (`POST /ejecuciones` y las rutas de rendimientos): un rendimiento
**medido** exige la referencia a la ejecución de obra de la que salió — sin referencia, se
rechaza. Al consultar una partida, el sistema devuelve su histórico con dispersión (número de
observaciones, media, mínimo, máximo) y propone el valor más defendible. Si el valor introducido
se aparta del comportamiento observado, el sistema **advierte pero no impide** el registro.

### 3.5 Contraste con el mercado (UC‑07)

`uv run python scripts/generar_resultados_ml.py` regenera [resultados_ml.md](resultados_ml.md):
la técnica de estimación que corresponde a los datos disponibles (hoy: sistema de reglas,
declarado como limitación), sus métricas (MAPE, RMSE, R²) y el contraste de cada precio
construido contra el estimado en el rango de la clase 3 de AACE.

### 3.6 Escenarios de sensibilidad (UC‑08)

En la página **Escenarios (UC‑08)**: elegir el presupuesto base, darle nombre al escenario y
declarar los supuestos — los cuatro parámetros de costo (precargados con los del base) y/o una
tabla de precios de ensayo por insumo (lo no mencionado conserva su precio vigente). Cada
escenario generado se suma a la tabla comparativa: el base en la primera fila y una fila por
escenario con su total y su variación absoluta y porcentual, descargable en CSV con los valores
exactos. El detalle por partida de cada escenario se despliega debajo, con los hallazgos de su
propia auditoría (que se genera siempre).

El presupuesto base **nunca** se altera y ningún escenario se guarda: al cambiar de presupuesto
la comparación se descarta. Para convertir un escenario en presupuesto vigente se usa la
actualización de precios (UC‑02) con la lista correspondiente. Por software, la misma operación
está en `POST /presupuestos/{codigo}/escenarios` (API) y en `core.budget.generar_escenario`
(Python).

### 3.7 Componer o editar una partida a mano (UC‑10 y UC‑11, prototipo AREN.IA)

La página **Componer partida (UC-10 / UC-11)** es el recorrido completo de quien presupuesta: arma
el análisis de precio de una partida, lo guarda en el catálogo, le asigna cantidades de obra y sale
con el presupuesto auditado y su Excel, sin cambiar de pantalla. Los casos de uso están en la
[ERS](ERS.md) (UC‑10 componer, UC‑11 editar; RF‑33 a RF‑35) y el diseño en la
[spec del prototipo](superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md). Para
practicarlo paso a paso con resultados esperados está el
[guion de prueba manual](guion_prueba_arenia.md).

1. **Cabecera.** Código, descripción y unidad de la partida, su dominio (civil por defecto) y la
   fecha, que decide qué lista de precios está vigente. Si el código ya existe en el catálogo, lo
   que se guarde **edita** esa partida (UC‑11); si no existe, la **crea** (UC‑10).
2. **Las tres tablas de insumos: materiales, equipos y mano de obra.** Se añaden filas al pie de
   cada tabla y se escribe en las celdas:
   - *Materiales:* descripción, unidad, **consumo por unidad** de partida (incluye el desperdicio:
     1,05 si se pierde el 5 %) y precio.
   - *Equipos:* descripción, cantidad, precio y **depreciación** (la fracción del precio imputable
     a un día de uso, entre 0 y 1).
   - *Mano de obra:* descripción, cantidad de obreros, sueldo y **modalidad**: `jornal` (sueldo
     diario; recibe prestaciones y bono de alimentación y se reparte entre el rendimiento) o
     `destajo` (pago por unidad de obra, art. 114 de la LOTTT: en esta modalidad el «sueldo» es el
     precio por unidad de partida y entra completo al precio unitario, sin prestaciones ni bono).
     Vacía equivale a jornal. Una misma partida puede mezclar las dos.

   Junto a cada tabla hay un **buscador de la referencia MaPreX** (julio 2026): se escribe parte del
   nombre del insumo, se elige un resultado y se pulsa **Usar esta fila**. La fila se **añade al
   final** de la tabla ya rellena (con la referencia MaPreX que respalda el precio, y en equipos
   con su factor de depreciación).
   El precio sugerido **se puede editar** (RF‑35): MaPreX es una referencia de mercado, no la
   verdad. En equipos, el precio de MaPreX es el **valor del activo**, no una tarifa diaria: lo que
   lo lleva a costo diario es la depreciación.
3. **Rendimiento, con sus condiciones.** El campo *Rendimiento — unidades por día* es la producción
   diaria de la cuadrilla (no confundir con el consumo de material, que va en la tabla). Si la
   partida ya tiene historial, el campo viene precargado con el rendimiento propuesto (el medido
   más reciente o, si no hay ninguno, el último registrado). Las
   **Condiciones del rendimiento** son **obligatorias** (RF‑33): un rendimiento sin decir en qué
   condiciones se obtuvo (tipo de suelo, cuadrilla, equipo…) no es verificable, y el botón de
   guardar permanece deshabilitado hasta que se escriban.
4. **Desglose en vivo.** Mientras se escribe, la página recalcula materiales, equipos, mano de
   obra, costo directo, costo con administración y **precio unitario**, con la misma fórmula del
   resto del sistema. Si una fila está incompleta o mal escrita, un aviso dice en qué tabla, qué
   fila y qué campo.
5. **Las cuatro ayudas.** Todas **sugieren y ninguna bloquea**: el guardado nunca depende de ellas.
   1. *Partidas similares del catálogo:* propuestas de solo lectura a partir de la descripción;
      lo útil se copia a mano.
   2. *Precio atípico:* avisa si un precio se aparta del histórico de cambios de ese insumo; sin
      histórico, se abstiene.
   3. *Rendimiento atípico:* avisa si el rendimiento escrito se sale del rango observado para la
      partida (hacen falta al menos dos observaciones) y, con historial suficiente, añade la
      lectura del bosque de aislamiento.
   4. *Contraste con la estimación por reglas (AACE):* solo para partidas que ya existen; compara
      el precio construido con el estimado y dice si cae en el rango de la clase 3 de AACE.
6. **Guardar y editar.** **Guardar composicion** crea o reemplaza el desglose de la partida. Al
   editar, el rendimiento anterior **no se pisa**: si el valor o las condiciones cambiaron, se
   registra uno nuevo y el anterior queda en el histórico; si no cambió nada, no se añade ruido.
   Si no hay ninguna lista de precios vigente a la fecha de la cabecera, la página lo dice y no
   guarda.
7. **Cantidades de obra, con su origen.** En la tabla *Cantidades de obra* se elige una partida
   ya guardada, su cantidad y su **origen** (de qué plano, cómputo o medición sale). El origen es
   obligatorio: una cantidad sin origen no es trazable.
8. **Elaborar.** Con al menos una cantidad válida aparece **Elaborar y auditar** (código, fecha y
   moneda del presupuesto). El sistema arma el presupuesto, su curva de inversión con un plan de
   una partida por día y el informe de auditoría.
9. **El informe de auditoría** se muestra siempre, tenga hallazgos o no (sección 4), con el total
   del presupuesto y el recuento por severidad.
10. **Descarga en Excel.** El botón **Exportar a Excel** entrega el libro del presupuesto; su hoja
    de APU muestra la columna *Modalidad* de cada línea de mano de obra, para que un destajo no se
    lea como sueldo diario.

## 4. El informe de auditoría

Se genera **siempre** — no existe forma de obtener un presupuesto sin él. Ejecuta las siete
reglas R1–R7 (trazabilidad de cantidades, cierre exacto de la curva, coherencia de unidades,
correspondencia de especificaciones, balance volumétrico, criterio único de depreciación y
conciliación con el plan; detalle en [CLAUDE.md §7](../CLAUDE.md)). Cada hallazgo trae:

- **severidad** (el informe se ordena de mayor a menor);
- **descripción e impacto cuantificado** (cuánto dinero o cuánta cantidad está en juego);
- **los `origen_id` involucrados**, para ir directo a la fila del cómputo o del plan que lo causó.

Una regla que no pueda evaluarse (por ejemplo, R2 sin curva) aparece como hallazgo informativo y
no interrumpe a las demás. Sobre el caso de estudio, el sistema detecta las **7 de 7**
inconsistencias del presupuesto original.

## 5. Exportar

- **Excel:** presupuesto y curva en un libro XLSX (desde la página de actualización, desde
  **Componer partida** tras elaborar, sección 3.7, o `GET /presupuestos/{codigo}/excel` en la API). Las celdas presentan dos decimales; los totales
  del libro cuadran con los del sistema porque el redondeo es solo de celda.
- **Informe:** `GET /presupuestos/{codigo}/informe`.
- **Tabla de escenarios:** botón de descarga CSV en la página de escenarios (valores exactos,
  sin redondeo de presentación).

## 6. Archivos de muestra

| Archivo | Dominio | Para probar |
|---|---|---|
| `data/samples/tanquilla.ifc` | civil (IFC) | UC‑01 y visor 3D; cantidades exactas al cálculo manual |
| `data/samples/civil/tanquillas_y_zanja.csv` | civil (tabular) | UC‑01 con mapeo de códigos |
| `data/samples/telecom/topologia_arenaza.csv` | telecom | nodos y enlaces con reserva de cable |
| `data/samples/industrial/activos_planta.csv` | industrial | activos con frecuencia de intervención |
| `data/samples/sistemas/alcance_funcional.csv` | sistemas | módulos y puntos de función |
| `data/samples/precios/lista_2026-06-01.csv` | — | UC‑02 (sube cemento y arena) |

Cada carpeta trae su `README.md` con el formato exacto de columnas.

## 7. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| «instala el extra civil» al cargar un `.ifc` | Falta `ifcopenshell`: `uv sync --extra civil` |
| Error 409 «catálogo incompleto» | Falta un precio o rendimiento vigente para una partida: revisar la lista de precios cargada o volver a sembrar (`scripts/seed.py`) |
| La UI no encuentra datos | La base no está sembrada: paso 1 de la sección 2 (`data/apu.db`) |
| «Partidas similares» tarda la primera vez | Descarga única del modelo de lenguaje; después queda en caché |
| Un rendimiento medido se rechaza | Falta la referencia a la ejecución: es una invariante, no un error |
| «Guardar composicion» no se puede pulsar | Faltan las condiciones del rendimiento (RF‑33): escribirlas |
| «no hay ninguna lista de precios vigente» al guardar | La base está vacía o la fecha es anterior a toda lista: sembrar con `scripts/seed_demo.py` o cambiar la fecha |
| El campo «Archivo SQLite» volvió a `data/apu.db` | Se reinicia al recargar la página (F5): volver a escribir la ruta de la base de prueba |
