# Capítulo IV — Resultados (Esqueleto operativo del TEG)

> **Nota de estado y alcance:** Este esqueleto organiza la presentación de resultados de Sílice en tres capas —verificación técnica, validación con personas y precisión medida— en correspondencia con los objetivos específicos del Trabajo Especial de Grado (OE1–OE4). Ninguna celda de resultado contiene cifras medidas o ejecutadas al redactar este esqueleto: donde corresponde un dato empírico figura `[pendiente: …]` con la indicación exacta de qué medir y de dónde extraerlo. La única cifra numérica que aparece corresponde a umbrales normativos o metas declaradas en las especificaciones del proyecto (expresadas con coma decimal). Conforme a [NORMAS.md](../../NORMAS.md) (§1), no se incluye ningún nombre de empresa real ni dato confidencial.

---

## 4.1 Capa 1: Verificación del sistema

**Objetivo específico al que responde:** **OE2** (diseñar el modelo de costos y de verificación) y **OE3** (construir el sistema: auditoría determinista y proyección probabilística del riesgo de precios, con la IA limitada a proponer y explicar). Verifica que el software implementado cumple la especificación de [docs/ERS.md](../../docs/ERS.md), las invariantes de [NORMAS.md](../../NORMAS.md) y los criterios de calidad ISO/IEC 25010 de [docs/calidad_iso25010.md](../../docs/calidad_iso25010.md).

### 4.1.1 Ejecución de pruebas automatizadas, cobertura y guardias

**De dónde salen los datos:**
- Suite de Python, warnings como error y cero omitidas: `uv run pytest -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml --cov=core --cov=ml --cov=api --cov=adapters --cov=seguridad --cov=paquete --cov=asistente --cov=operacion --cov-report=term` y `uv run python scripts/verificar_omitidas.py reporte-pruebas.xml` (registrado en [.github/workflows/ci.yml](../../.github/workflows/ci.yml) y en [docs/plan_pruebas.md](../../docs/plan_pruebas.md) §10).
- Cobertura mínima (≥ 80 %): `uv run coverage report --include="core/*" --fail-under=80`, `--include="adapters/espacio/*" --fail-under=80` y `--include="seguridad/*,paquete/*" --fail-under=80` ([.github/workflows/ci.yml](../../.github/workflows/ci.yml)).
- Estilo y front-end: `uv run ruff check .` y, en `frontend-desktop/`, `npm run lint` y `npx vitest run`.
- Guardias arquitectónicas y de datos: [tests/unit/test_arquitectura.py](../../tests/unit/test_arquitectura.py), [scripts/guardia_nucleo.py](../../scripts/guardia_nucleo.py) (`--base main`) y [scripts/meta_datos.py](../../scripts/meta_datos.py) (reglas D1–D4).
- Tiempos de máquina reproducibles: [scripts/medir_rnf03.py](../../scripts/README.md), [scripts/medir_rnf11.py](../../scripts/README.md) y [scripts/medir_rnf15.py](../../scripts/README.md).

**Tabla 4.1. Resumen de verificación automatizada y guardias de integración continua**

| Componente / Guardia | Comando o fuente | Meta / Umbral | Resultado observado (Linux / Windows) | Estado |
|---|---|---|---|---|
| Suite Python (`pytest -W error`) | [.github/workflows/ci.yml](../../.github/workflows/ci.yml) · [docs/plan_pruebas.md](../../docs/plan_pruebas.md) §10 | 0 fallos, 0 errores, 0 omitidas | `[pendiente: total de pruebas pasadas, tiempo y SHA del commit en CI]` | `[pendiente: cumple / no cumple]` |
| Suite interfaz (`vitest` y `lint`) | `frontend-desktop/` (`npm run lint`, `npx vitest run`) | 0 errores de lint, 0 fallos | `[pendiente: total de pruebas Vitest pasadas y estado de lint]` | `[pendiente: cumple / no cumple]` |
| Cobertura de `core/` (RNF-06) | `coverage report --include="core/*"` | ≥ 80,00 % | `[pendiente: sentencias cubiertas / totales y % exacto]` | `[pendiente: cumple / no cumple]` |
| Cobertura de `adapters/espacio/`, `seguridad/`, `paquete/` | [.github/workflows/ci.yml](../../.github/workflows/ci.yml) | ≥ 80,00 % | `[pendiente: % exacto por paquete en corrida de CI]` | `[pendiente: cumple / no cumple]` |
| Invariabilidad y aislamiento de `core/` (RNF-05) | [tests/unit/test_arquitectura.py](../../tests/unit/test_arquitectura.py) · [scripts/guardia_nucleo.py](../../scripts/guardia_nucleo.py) | `diff --stat` vacío en ramas de adaptadores/ML | `[pendiente: casos en verde y salida de guardia_nucleo.py]` | `[pendiente: cumple / no cumple]` |
| Naturaleza y resguardo de datos (D1–D4) | [scripts/meta_datos.py](../../scripts/meta_datos.py) | 4/4 OK | `[pendiente: salida de meta_datos.py en corrida de cierre]` | `[pendiente: cumple / no cumple]` |
| Desempeño de cálculo (RNF-03, RNF-11, RNF-15) | `medir_rnf03.py`, `medir_rnf11.py`, `medir_rnf15.py` | < 5,00 s (RNF-03); ≤ 2,00 s (RNF-11 y RNF-15) | `[pendiente: mediana de 5 corridas en equipo de referencia]` | `[pendiente: cumple / no cumple]` |

### 4.1.2 Trazabilidad requisito → prueba

**De dónde salen los datos:**
- Matriz de requisitos funcionales y no funcionales en [docs/ERS.md](../../docs/ERS.md) (§3.2 y §3.3, más enmiendas hasta RF-214) cruzada con la fuente única de trazabilidad de [docs/plan_pruebas.md](../../docs/plan_pruebas.md) (§8 y §9).

**Tabla 4.2. Trazabilidad consolidada de requisitos funcionales y no funcionales**

| Bloque funcional (ERS) | Requisitos cubiertos | Evidencia de prueba / script | Total requisitos | En verde | Parcial / Pendiente |
|---|---|---|---|---|---|
| Núcleo de costos, presupuesto y curva (UC-01, UC-02, UC-05) | `RF-01`–`RF-14`, `RF-21`–`RF-24` | `test_costing.py`, `test_auditoria_7_de_7.py`, `test_importacion_tercero.py` | `[pendiente: n]` | `[pendiente: n]` | `[pendiente: n y motivo]` |
| Moneda, BCV y reajuste de precios (UC-17, UC-18) | `RF-64`–`RF-71`, `RF-214`, `RNF-14` | [docs/plan_pruebas.md](../../docs/plan_pruebas.md) §8.0b, `test_indices_usd.py` | `[pendiente: n]` | `[pendiente: n]` | `[pendiente: n y motivo]` |
| Control de obra y costo final (UC-19, UC-20) | `RF-72`–`RF-79`, `RF-196`–`RF-197`, `RNF-15` | [docs/plan_pruebas.md](../../docs/plan_pruebas.md) §8.0c | `[pendiente: n]` | `[pendiente: n]` | `[pendiente: n y motivo]` |
| Auditoría de libros de la empresa y visor (UC-25, UC-26, UC-30) | `RF-101`–`RF-118`, `RF-142`–`RF-146`, `RF-175`–`RF-179`, `RNF-21`–`RNF-23`, `RNF-28` | `test_visual_libro.py`, `test_fusion_apu_por_hoja.py`, `test_historial_auditorias.py` | `[pendiente: n]` | `[pendiente: n]` | `[pendiente: n y motivo]` |
| Especialidad vial y proyección probabilística P50/P80 | `RF-170`–`RF-174`, `RF-190`–`RF-192` + [PLAN_VIAL_AGREGADOS.md](../../docs/planes/PLAN_VIAL_AGREGADOS.md) | `test_vial_*.py`, `test_riesgo_proyeccion.py`, `test_riesgo_comprobacion.py`, `test_riesgo_mejora.py` | `[pendiente: n]` | `[pendiente: n]` | `[pendiente: n y motivo]` |
| Asistente de IA acotado a proponer y explicar (UC-09) | `RF-32`, `RF-90`–`RF-95`, `RNF-18` | `test_asistente_*.py`, `test_asistente_explicar_riesgo.py` | `[pendiente: n]` | `[pendiente: n]` | `[pendiente: n y motivo]` |

**Figuras previstas en esta capa:**
- *Figura 4.1:* Cadena de trazabilidad `Objetivo específico → UC → RF/RNF → prueba automatizada → corrida de CI` (adaptada de [docs/metodologia.md](../../docs/metodologia.md) §7).
- *Figura 4.2:* Distribución de cobertura por paquete (`core/`, `adapters/`, `ml/`, `api/`, `seguridad/`, `paquete/`).

**Cómo se analiza:** Estadística descriptiva (conteos absolutos, porcentajes de requisitos en estado verde/parcial/pendiente y márgenes frente a los umbrales de cobertura y tiempo). Todas las cifras provienen de la misma corrida etiquetada en CI.

**Si el resultado es negativo, se reporta así:** Se declara la brecha exacta con nombre del requisito (`RF-*`/`RNF-*`), prueba fallida o cobertura inferior al 80,00 %, causa raíz y si permanece como limitación abierta o defecto corregido antes del cierre.

---

## 4.2 Capa 2: Validación con personas

**Objetivo específico al que responde:** **OE4** (evaluar el sistema frente al procedimiento tradicional) y verificación no automatizable de usabilidad y adecuación de **OE2** y **OE3** (correspondiente a `RNF-04` y `RNF-10` en [docs/calidad_iso25010.md](../../docs/calidad_iso25010.md) §4).

> El guion de la prueba de uso (consentimiento, 3 tareas, hoja de observación y SUS) está en [docs/tesis/2026-11-23-guion-prueba-con-usuarios.md](2026-11-23-guion-prueba-con-usuarios.md), que llega con el PR #140. Sus tareas y su hoja de observación las aprueban los 3 expertos antes de las sesiones.

### 4.2.1 Prueba de uso con usuarios (eficacia, eficiencia y cuestionario SUS)

**De dónde salen los datos:**
- **Población censal:** 3 economistas de la empresa objeto de estudio (`ECON-01`, `ECON-02`, `ECON-03`).
- **Instrumentos:** Guía de observación con cronometraje (tiempo efectivo por tarea, ayudas solicitadas, interrupciones descontadas y completitud de entregables) y cuestionario estándar **SUS** (10 ítems en escala 1–5, puntaje convertido a escala 0–100).

**Tabla 4.3. Resultados individuales y consolidados de la prueba de uso (N = 3)**

| Participante | Perfil (años en presupuestos / rol) | Tareas completadas sin error (eficacia, n / total y %) | Tiempo total en tareas (eficiencia, min) | Preguntas al observador | Puntaje SUS (0–100) | Observaciones relevantes |
|---|---|---|---|---|---|---|
| `ECON-01` | `[pendiente: perfil]` | `[pendiente: n/N (%)]` | `[pendiente: min]` | `[pendiente: n]` | `[pendiente: puntaje SUS]` | `[pendiente: anotación de observación]` |
| `ECON-02` | `[pendiente: perfil]` | `[pendiente: n/N (%)]` | `[pendiente: min]` | `[pendiente: n]` | `[pendiente: puntaje SUS]` | `[pendiente: anotación de observación]` |
| `ECON-03` | `[pendiente: perfil]` | `[pendiente: n/N (%)]` | `[pendiente: min]` | `[pendiente: n]` | `[pendiente: puntaje SUS]` | `[pendiente: anotación de observación]` |
| **Resumen descriptivo** | **N = 3 (censal)** | **Mediana / rango: `[pendiente]`** | **Mediana / rango: `[pendiente]`** | **Total / mediana: `[pendiente]`** | **Media / mediana / rango: `[pendiente]`** | `[pendiente: versión/commit probado]` |

### 4.2.2 Juicio de expertos

**De dónde salen los datos:**
- **Quién valora (anteproyecto v8, §8):** los 3 economistas, como conocedores del oficio y después de usar el sistema, valoran la utilidad del asistente y del informe. Los 3 expertos que validan los instrumentos (costos, metodología y sistemas) no participan en esta valoración.
- **Instrumento:** Matriz de juicio de expertos (para el informe de auditoría, el bloque A de 8 afirmaciones en escala Likert 1–5 más campo abierto según [docs/protocolo_rnf04.md](../../docs/protocolo_rnf04.md), junto con la validación de contenido de los instrumentos de medición según la matriz de expertos del TEG). Se identifica el commit probado y las huellas SHA-256 de los artefactos evaluados.

**Tabla 4.4. Valoración del panel de expertos (escala Likert 1–5)**

| Ítem / Criterio evaluado | Forma evaluada | Experto 1 | Experto 2 | Experto 3 | `[Opcional: E4–E5]` | Promedio | Mín – Máx |
|---|---|---|---|---|---|---|---|
| 1. Comprensión sin formación previa | Ambas en conjunto | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 2. Severidad comprensible y bien asignada | Cualquiera | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 3. Impacto cuantificado | Pantalla (`.md` / visor) | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 4. Orígenes para ubicar la fila (`origen_id` / celda) | Hoja / Excel devuelto | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 5. Orden por severidad descendente | Pantalla | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 6. Lenguaje apropiado para obra | Cualquiera | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 7. Utilidad para decidir qué corregir | Ambas en conjunto | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 8. Confianza como complemento manual | Ambas en conjunto | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| **Promedio por experto / Global (meta ≥ 4,00)** | — | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** |

**Cómo se analiza:** Análisis descriptivo puro sobre N = 3 participantes (prueba de uso) y el panel de expertos: frecuencias, porcentajes de eficacia, medianas, promedios y rangos (mínimo–máximo), sin pruebas de significancia estadística. Los campos abiertos se transcriben literalmente agrupados por tema sin atribución nominal.

**Si el resultado es negativo, se reporta así:** Si el puntaje SUS promedio cae por debajo del umbral aceptable declarado o el promedio global de expertos resulta < 4,00 (o algún ítem < 3,00), se reporta explícitamente como veredicto `NO CUMPLE` (o hallazgo de usabilidad) identificando los ítems críticos y las dificultades observadas en pantalla.

---

## 4.3 Capa 3: Precisión medida

**Objetivo específico al que responde:** **OE1** (línea base diagnóstica del procedimiento tradicional) y **OE4** (evaluar el sistema frente al procedimiento tradicional en detección de errores, tiempo de preparación de reajustes, acierto de la proyección P50/P80 y estimación del costo final).

### 4.3.1 Detección de errores en presupuestos (precisión, detección de sembrados, exhaustividad y kappa)

**De dónde salen los datos:**
- **Instrumentos y herramienta:** Matriz de registro de hallazgos, ejecutada localmente fuera del repositorio mediante [scripts/medir_auditoria_libro.py](../../scripts/medir_auditoria_libro.py) (`clave`, `exportar` con `procesar_libro`, `calcular`) siguiendo [docs/tesis/2026-11-23-protocolo-medicion-auditoria.md](../../docs/tesis/2026-11-23-protocolo-medicion-auditoria.md).
- **Unidad de conteo:** **Causa raíz** (`causas_de_hallazgos`: misma regla y misma primera cláusula de descripción), excluyendo avisos de regla «no aplicable». Las ocurrencias repetidas por fórmulas copiadas se informan como razón de compactación (`hallazgos totales / causas raíz`).
- **Piloto de confiabilidad:** Dos economistas marcan independientemente 2 presupuestos antes de la medición principal para calcular el **kappa de Cohen** ($\kappa$).

**Tabla 4.5. Métricas de auditoría por causa raíz (piloto y muestra principal)**

| Conjunto evaluado | Causas raíz exportadas (hallazgos totales) | Precisión (`Verdadero / marcados`, % y pendientes) | Detección de errores sembrados (`detectados / sembrados`, %) | Exhaustividad aproximada (`Verdadero / (Verdadero + escapados)`, %) | Kappa de Cohen ($\kappa$) entre dos evaluadores |
|---|---|---|---|---|---|
| Piloto (2 presupuestos) | `[pendiente: causas (hallazgos)]` | `[pendiente: n/N (%)]` | `[pendiente: n/N (%) o no aplica]` | `[pendiente: n/N (%)]` | `[pendiente: κ y n comunes]` |
| Presupuestos evaluados (principal) | `[pendiente: causas (hallazgos)]` | `[pendiente: n/N (%)]` | `[pendiente: n/N (%)]` | `[pendiente: n/N (%)]` | `[pendiente: κ si hay doble marca]` |
| **Consolidado** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** |

**Cómo se analiza:** Cálculo determinista de proporciones por causa raíz y $\kappa$ de Cohen ((observado − esperado) / (1 − esperado)). La interpretación del $\kappa$ en el piloto verifica la consistencia de la matriz antes de medir (Landis y Koch, 1977: 0,61–0,80 «sustancial», sujeto a verificación bibliográfica previa a citar).

**Si el resultado es negativo, se reporta así:** Si $\kappa < 0,61$ en el piloto, se documenta la ambigüedad detectada y la revisión aplicada a las instrucciones antes de la medición principal; si la precisión, la detección de sembrados o la exhaustividad quedan por debajo de lo esperado, se desglosa por regla (`F1`, `L1`–`L11`, `R1`–`R7`, `VR1`–`VR8`, `AH1`–`AH12`) señalando qué tipos de error generaron falsos positivos o se escaparon.

### 4.3.2 Tiempo de preparación de reajustes (diseño cuasiexperimental cruzado)

**De dónde salen los datos:**
- **Diseño:** Cuasiexperimental con **orden cruzado por presupuesto** sobre la población censal de **3 economistas**. Cada participante prepara un reajuste bajo el procedimiento tradicional (hoja de cálculo habitual) y otro equivalente con Sílice (`UC-18`, [aplicacion/reajuste.py](../../aplicacion/reajuste.py)), alternando el orden y el presupuesto asignado para controlar el efecto de aprendizaje y la complejidad del libro.
- **Instrumento:** Guía de observación con cronometraje (minutos con dos decimales, interrupciones ajenas descontadas y verificación de exactitud del entregable resultante).

**Tabla 4.6. Comparación de tiempos de preparación de reajustes (diseño cruzado, N = 3)**

| Economista | Secuencia (orden × presupuesto) | `t_tradicional` (min) | `t_silice` (min) | Reducción absoluta (`t_tradicional − t_silice`, min) | Reducción relativa `r = 1 − t_silice / t_tradicional` (%) | Entregables correctos (Trad. / Sílice) |
|---|---|---|---|---|---|---|
| `ECON-01` | `[pendiente: ej. Trad(P1) → Sílice(P2)]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: Sí/No]` |
| `ECON-02` | `[pendiente: ej. Sílice(P1) → Trad(P2)]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: Sí/No]` |
| `ECON-03` | `[pendiente: secuencia asignada]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: Sí/No]` |
| **Resumen descriptivo** | **N = 3** | **Mediana / rango: `[pendiente]`** | **Mediana / rango: `[pendiente]`** | **Mediana / rango: `[pendiente]`** | **Mediana / rango: `[pendiente]`** | **Válidos: `[pendiente: n/3]`** |

**Cómo se analiza:** Análisis exclusivamente descriptivo (mediana, mínimo y máximo por condición, más comparación descriptiva por orden y por presupuesto), dado que con N = 3 no proceden pruebas de hipótesis inferenciales. Los casos con errores de cálculo en el reajuste se reportan en columna aparte y se analizan con y sin exclusión.

**Si el resultado es negativo, se reporta así:** Si `t_silice ≥ t_tradicional` o la mediana de reducción relativa es ≤ 0,00 %, se reporta el tiempo medido tal cual junto con los cuellos de botella observados en la interfaz o en la carga de índices, sin afirmar mejora de eficiencia.

### 4.3.3 Acierto de la proyección P50/P80 y estimación del costo final

**De dónde salen los datos:**
- **Proyección P50/P80 (comprobación hacia atrás):** Ficha de registro documental y técnico alimentada por [aplicacion/riesgo/comprobacion.py](../../aplicacion/riesgo/comprobacion.py) (`comprobar_hacia_atras`) sobre [aplicacion/riesgo/proyeccion.py](../../aplicacion/riesgo/proyeccion.py) (`proyectar`, remuestreo de meses históricos completos con semilla fija, ventana declarada y mínimo 12 meses completos). Mide por cada corte móvil mensual si el costo real revalorizado al horizonte cayó dentro de `P50` y dentro de `P80` (`real <= P80`), reportando la **cobertura empírica** y el número de cortes (`n_cortes`).
- **Estimación del costo final (si hay datos de obras culminadas):** Ficha de registro documental y técnico procesada con [aplicacion/riesgo/mejora.py](../../aplicacion/riesgo/mejora.py) (`mejora_de_estimacion`), contrastando el presupuesto original, la estimación con reserva P80 de Sílice y el costo final real de cierre de obra (`error = |estimado − real| / real × 100`, en puntos porcentuales `mejora_pp`).

**Tabla 4.7. Comprobación hacia atrás de la proyección probabilística P50/P80**

| Obra / Serie evaluada (código anónimo) | Horizonte (meses) | Ventana histórica (meses completos) | Semilla / Trayectorias | N.º de cortes móviles (`n_cortes`) | Cobertura P50 (`real ≤ P50`, %) | Cobertura P80 (`real ≤ P80`, %) | Insumos con mayor contribución |
|---|---|---|---|---|---|---|---|
| `[pendiente: Obra 1]` | `[pendiente: ej. 6]` | `[pendiente: ≥ 12]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| `[pendiente: Obra N]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |

**Tabla 4.8. Exactitud en la estimación del costo final frente al procedimiento tradicional *(condicional a disponibilidad de obras culminadas)***

| Obra culminada (código anónimo) | Presupuesto original (moneda) | Estimación Sílice con P80 (moneda) | Costo final real (moneda) | Error presupuesto original (%) | Error estimación Sílice (%) | Mejora en puntos porcentuales (`pp`) |
|---|---|---|---|---|---|---|
| `[pendiente: Obra 1 o "sin obras culminadas disponibles"]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |

**Figuras previstas en esta capa:**
- *Figura 4.3:* Evolución de cortes móviles (`P50`, `P80` y valor real observado al horizonte) de la comprobación hacia atrás.
- *Figura 4.4:* Comparación gráfica de tiempos de reajuste (`t_tradicional` vs. `t_silice`) y de tasas de precisión/detección/exhaustividad por regla.

**Cómo se analiza:** Análisis descriptivo de cobertura empírica (`cortes_dentro / n_cortes`, expresado en porcentaje), error porcentual absoluto respecto al costo final real y diferencia en puntos porcentuales (`mejora_pp`). Se declara explícitamente que la cobertura histórica es un indicador descriptivo retrospectivo y no una garantía probabilística futura.

**Si el resultado es negativo, se reporta así:** Si la cobertura empírica de `P80` queda por debajo del 80,00 % (choques de precios o tasa fuera de la historia reciente) o `mejora_pp` resulta negativo (la estimación con P80 se desvía más del costo final que el presupuesto original), se reportan los valores literales y los cortes o insumos que causaron el desvío; si no existen obras culminadas con costo final real registrado al cierre de la medición, la Tabla 4.8 se sustituye por la declaración explícita de ausencia de dato real de cierre (evaluación acotada a la comprobación hacia atrás).

---

## 4.4 Límites del estudio

1. **Tamaño censal reducido (N = 3 economistas):** Al tratarse de un censo de 3 profesionales de la empresa objeto de estudio, no es procedente realizar inferencia estadística ni generalización poblacional; todos los resultados humanos se reportan de forma descriptiva.
2. **Exhaustividad aproximada y dependencia del catálogo de siembra:** En los libros reales no se conoce el universo absoluto de errores ocultos, por lo que la exhaustividad depende del esfuerzo de revisión de los evaluadores y la detección medida depende de los tipos de error incluidos en el catálogo de siembra previo ([docs/tesis/2026-11-23-protocolo-medicion-auditoria.md](../../docs/tesis/2026-11-23-protocolo-medicion-auditoria.md)).
3. **Condición de los datos históricos para P50/P80 y costo final:** La proyección probabilística requiere al menos 12 meses históricos completos coincidentes entre todas las series y la tasa BCV, bajo el supuesto de gasto uniforme en el plazo; la estimación del costo final solo es evaluable si se dispone de al menos una obra culminada con su costo real documentado.
4. **Restricciones del dominio y alcance de la IA:** El núcleo de cálculo (`core/`) permaneció inalterado; las reglas especializadas y la proyección operan en capas externas (`adapters/`, `aplicacion/`). Además, la IA se limita estrictamente a proponer o narrar cifras ya calculadas determinísticamente y su evaluación empírica completa con proveedor en la nube depende de la disponibilidad de ejecución autorizada.
5. **Instrumentos validados antes de medir:** las tareas y la hoja de observación del guion de uso, y la matriz de hallazgos, se aprueban por juicio de 3 expertos antes de llenar las Tablas 4.3 a 4.6; el cuestionario SUS es estandarizado y se usa en una versión en español publicada.
6. **El estudio de mercado depende de lo que la empresa anota (2026-11-24):** Sílice no trae precios de internet por diseño (funciona sin red y cada cifra tiene una fuente comprobable); su propuesta de precio sale de las cotizaciones, compras y precios de la competencia que la empresa anota, en una ventana de 90 días. Con menos de 3 observaciones por insumo, la mediana y los cuartiles no son representativos, y en bolívares la inflación hace poco comparables precios separados por semanas dentro de esa ventana; por eso el estudio se presenta como apoyo a la decisión, no como precio de mercado, y se reporta cuántos insumos críticos (clase A) tenían al menos 3 precios vigentes ([acta del consejo](../bitacora/2026-11-24-consejo-auditoria-alertas-mercado.md)). El mínimo de observaciones y la ventana son supuestos por confirmar con el ingeniero de costos.
7. **Reglas ajustadas sobre el libro de desarrollo (2026-11-24):** la medición una falla por vez en el libro de desarrollo pasó de 5 a 10 de 12 fallas detectadas después de cerrar tres huecos de reglas que esas mismas fallas revelaron; esas cifras miden lo aprendido y no la generalización, y se reportan solo como historia del desarrollo ([acta](../bitacora/2026-11-24-huecos-de-reglas-antes-del-congelamiento.md)). La cifra de la tesis es la de la Fase 3, sobre libros que nadie ha visto, con fallas de la taxonomía del tercero y con las reglas congeladas en la etiqueta `reglas-congeladas-2026-11-24`.
