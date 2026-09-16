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

2. **Abrir la interfaz** (se abre en el navegador, en el equipo local):

   ```
   uv run streamlit run ui/app.py
   ```

3. **API HTTP** (opcional, para integrar con otro software):

   ```
   uv run uvicorn api.main:app
   ```

   La documentación interactiva queda en `http://127.0.0.1:8000/docs`. Todos los montos viajan
   como **texto** (`"1586.61"`), nunca como número JSON: así no se pierde precisión decimal.

## 3. Las pantallas

La interfaz tiene ocho páginas (menú lateral). Todas presentan los montos con dos decimales,
pero **ningún cálculo interno redondea**: el redondeo es solo de presentación.

| Página | Caso de uso | Qué hace |
|---|---|---|
| **Actualización de precios** | UC‑02 | Cargar una lista de precios nueva (CSV/XLSX) y revalorar un presupuesto guardado |
| **Catálogo** | consulta | Partidas e insumos con su precio vigente |
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

- **Excel:** presupuesto y curva en un libro XLSX (desde la página de actualización o
  `GET /presupuestos/{codigo}/excel` en la API). Las celdas presentan dos decimales; los totales
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
