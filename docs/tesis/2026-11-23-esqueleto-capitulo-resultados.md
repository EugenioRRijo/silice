# Capítulo IV — Resultados (Esqueleto operativo del TEG)

> **Nota de estado y alcance:** Este esqueleto organiza la presentación de resultados de Sílice en tres capas —verificación técnica, validación con personas y precisión medida— en correspondencia con los objetivos específicos del Trabajo Especial de Grado (OE1–OE4). Al redactar este esqueleto ninguna celda de resultado contenía cifras medidas; desde el 2026‑11‑25 la Tabla 4.1 ya trae las de mantenibilidad (CRAP y dryer) y las de pruebas de mutación, con su fecha y su método. Donde corresponde un dato empírico figura `[pendiente: …]` con la indicación exacta de qué medir y de dónde extraerlo. La única cifra numérica que aparece corresponde a umbrales normativos o metas declaradas en las especificaciones del proyecto (expresadas con coma decimal). Conforme a [NORMAS.md](../../NORMAS.md) (§1), no se incluye ningún nombre de empresa real ni dato confidencial.

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
| Riesgo por función (CRAP = CC² × (1 − cobertura)³ + CC; mantenibilidad, ISO/IEC 25010) | `crapper --use-existing-coverage` (unclebob/crapper, `c757ec7`) sobre el lcov de la suite completa, paquetes `core`, `adapters`, `aplicacion`, `fusion`, `api`, `seguridad` y `operacion` | Sin umbral: se informa | 2026‑11‑25, `main` `f371c45c` (Windows): 3.796 funciones; 3.025 (79,7 %) con CRAP ≤ 5, 729 (19,2 %) entre 5 y 30 y 42 (1,1 %) sobre 30, de las que 33 están en el escritor de la devolución (`adapters/hoja_empresa/escritor/`); cobertura mediana por función 100 % | Informado |
| Código duplicado (mantenibilidad, ISO/IEC 25010) | `dryer` (unclebob/dryer, `66ff6d2`, umbral de similitud 0,82, formas de 4 líneas o más) sobre los mismos 7 paquetes | Sin umbral: se informa | 2026‑11‑25, `main` `f371c45c` (Windows): 124 pares candidatos, 98 con similitud 1,00 (estructura idéntica); se reducen después de la defensa (las reglas están congeladas) | Informado |
| Pruebas de mutación (mutator, unclebob, 0BSD; puntaje = detectados / (detectados + sobrevivientes)) | `mutator` (unclebob/mutator, `0136cf5`) en un contenedor Linux (Docker) sobre las reglas del libro de la empresa: `adapters/hoja_empresa/reglas_calculo.py`, `reglas.py` y `reglas_contexto.py` | Sin umbral: se informa | 2026‑11‑25, rama `feature/mutator-reglas` (Linux, Docker): en `reglas_calculo.py` las pruebas detectaron 32 de 35 mutantes (91,4 %) en la primera pasada; los 3 sobrevivientes eran huecos de prueba, no defectos de las reglas, y con 3 pruebas nuevas la segunda pasada detectó 35 de 35 (100 %), sin cambiar el código congelado. `reglas.py`: 144 de 190 (75,8 %) con las 22 pruebas que usan las reglas; con 30 casos nuevos, 192 de 196 (98,0 %), y 3 de los 4 sobrevivientes son equivalentes (no cambian ningún resultado). `reglas_contexto.py` (analizador de fórmulas): 123 de 198 (62,1 %); con 10 pruebas directas nuevas, 198 de 201 (98,5 %). Las pruebas nuevas no cambian el código congelado | Informado |

**Método de la prueba de mutación.** La prueba de mutación mide si las pruebas detectan cambios pequeños sembrados a propósito en el código, como invertir una comparación o sustituir un operador lógico; cada versión alterada se denomina mutante, y se considera detectada cuando al menos una prueba falla con ella (DeMillo et al., 1978; Jia y Harman, 2011). El puntaje informado es detectados / (detectados + sobrevivientes), es decir, la proporción de mutantes que las pruebas matan (Papadakis et al., 2019). La herramienta se ejecutó en un contenedor Linux (Docker) porque en Windows necesita crear enlaces simbólicos, y el equipo de medición no tiene los privilegios para ello. El total de mutantes de un mismo archivo cambia entre la primera y la segunda pasada (de 190 a 196 en `reglas.py` y de 198 a 201 en `reglas_contexto.py`; en `reglas_calculo.py` se mantiene en 35) porque la herramienta solo genera mutantes en las líneas que las pruebas ejecutan: las pruebas nuevas cubren líneas que antes no se ejecutaban y con ellas aparecen mutantes nuevos. Por eso los puntajes de las dos pasadas no comparten denominador y se informan con sus cuentas, no solo con el porcentaje. Su límite es que un mutante sobreviviente puede ser equivalente, esto es, sintácticamente distinto del original pero con su mismo comportamiento: ninguna prueba puede detectarlo y, por tanto, no constituye un hueco de prueba; como la equivalencia es indecidible en general, cada sobreviviente se revisa a mano (Jia y Harman, 2011). Dado que el denominador no descuenta los equivalentes, el puntaje informado es una cota inferior del que definen Jia y Harman (2011), que solo cuenta los mutantes no equivalentes.

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
- **Participantes:** cinco personas, por decisión de Eugenio del 2026-11-25 ([acta](../bitacora/2026-11-25-acta-kappa-sus-y-textos.md), punto 2). Son los 3 economistas de la población censal del v8 y 2 personas que presupuestan pero no conocen Sílice, con lo que se alcanza la referencia de Nielsen y Landauer (1993). Las tablas informan cada grupo por separado (`ECON-01…03` y `NUEVO-01…02`) y el conjunto.
- **Instrumentos:** Guía de observación con cronometraje (tiempo efectivo por tarea, ayudas solicitadas, interrupciones descontadas y completitud de entregables), **prueba de comprensión de las alertas** (6 alertas reales, A1 a A6, con las preguntas «¿Qué le está diciendo?», «¿Qué haría ahora?» y, al final, «¿Qué alerta le faltó?»; acta del consejo del 2026-11-24) y cuestionario estándar **SUS** (10 ítems en escala 1–5, puntaje convertido a escala 0–100), en ese orden.
- **Quién conduce cada parte:** las tareas T1 a T3 y la entrega del SUS las conduce Eugenio, autor del sistema, lo que se declara como límite; la prueba de comprensión de las alertas la conduce una persona que no construyó Sílice ni escribió sus reglas o textos de pantalla, y que tampoco es uno de los 3 expertos que validan los instrumentos ([guion](2026-11-23-guion-prueba-con-usuarios.md), «Prueba de comprensión de las alertas»). El SUS se responde sin ayuda.

**Tabla 4.3. Resultados individuales y consolidados de la prueba de uso (N = 3)**

| Participante | Perfil (años en presupuestos / rol) | Tareas completadas sin error (eficacia, n / total y %) | Tiempo total en tareas (eficiencia, min) | Preguntas al observador | Puntaje SUS (0–100) | Observaciones relevantes |
|---|---|---|---|---|---|---|
| `ECON-01` | `[pendiente: perfil]` | `[pendiente: n/N (%)]` | `[pendiente: min]` | `[pendiente: n]` | `[pendiente: puntaje SUS]` | `[pendiente: anotación de observación]` |
| `ECON-02` | `[pendiente: perfil]` | `[pendiente: n/N (%)]` | `[pendiente: min]` | `[pendiente: n]` | `[pendiente: puntaje SUS]` | `[pendiente: anotación de observación]` |
| `ECON-03` | `[pendiente: perfil]` | `[pendiente: n/N (%)]` | `[pendiente: min]` | `[pendiente: n]` | `[pendiente: puntaje SUS]` | `[pendiente: anotación de observación]` |
| **Resumen descriptivo** | **N = 3 (censal)** | **Mediana / rango: `[pendiente]`** | **Mediana / rango: `[pendiente]`** | **Total / mediana: `[pendiente]`** | **Media / mediana / rango: `[pendiente]`** | `[pendiente: versión/commit probado]` |

**Referencia del SUS:** el promedio publicado ronda 68 (Sauro y Lewis, citado en el guion; `[pendiente: verificar la obra y la página en docs/tesis/referencias.md antes de citarla]`). Un puntaje por encima de 68 se lee como mejor que el promedio publicado; no es un umbral de aprobación del sistema.

**Tabla 4.3b. Prueba de comprensión de las alertas (N = 3; conduce una persona que no construyó Sílice)**

| Alerta (texto real de pantalla, caso ficticio) | `ECON-01`: ¿la entendió? (sí / a medias / no) | `ECON-02` | `ECON-03` | Entendida «sí» (n de 3) | Acciones declaradas ante la alerta (agrupadas por tema, sin atribución) |
|---|---|---|---|---|---|
| A1 · Sin fuente | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: n de 3]` | `[pendiente: resumen de «¿Qué haría ahora?»]` |
| A2 · Base de la empresa | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: n de 3]` | `[pendiente]` |
| A3 · USD-Bs | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: n de 3]` | `[pendiente]` |
| A4 · Componente fuera del total (L4) | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: n de 3]` | `[pendiente]` |
| A5 · Referencia rota o externa (L5) | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: n de 3]` | `[pendiente]` |
| A6 · Causa raíz agrupada (L1, 6 casos) | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: n de 3]` | `[pendiente]` |
| **Resumen** | — | — | — | **`[pendiente: alertas entendidas «sí» por los 3; total de respuestas «sí» de 18]`** | **«¿Qué alerta le faltó?»: `[pendiente: citas textuales sin nombre, agrupadas por tema]`** |

Los datos salen de la hoja de registro de la prueba de comprensión del guion, que se llena en papel o en una planilla local fuera del repositorio. Las tarjetas se copian de la pantalla real del caso de demostración con la versión congelada (`reglas-congeladas-2026-11-24`).

### 4.2.2 Juicio de expertos

**De dónde salen los datos:**
- **Quién valora (anteproyecto v8, §8):** los 3 economistas, como conocedores del oficio y después de usar el sistema, valoran la utilidad del asistente y del informe. Los 3 expertos que validan los instrumentos (costos, metodología y sistemas) no participan en esta valoración.
- **Instrumento:** Matriz de juicio de expertos (para el informe de auditoría, el bloque A de 8 afirmaciones en escala Likert 1–5 más campo abierto según [docs/protocolo_rnf04.md](../../docs/protocolo_rnf04.md), junto con la validación de contenido de los instrumentos de medición según la matriz de expertos del TEG). Se identifica el commit probado y las huellas SHA-256 de los artefactos evaluados.

**Tabla 4.4. Valoración de los 3 economistas (escala Likert 1–5, N = 3)**

> El protocolo anterior de RNF-04 ([docs/protocolo_rnf04.md](../protocolo_rnf04.md) §2) preveía un panel de 3 a 5 ingenieros ajenos al sistema, de donde venía una columna opcional para un cuarto y un quinto evaluador. El anteproyecto v8 (§8) asigna esta valoración a los 3 economistas, que son población censal; por eso la tabla tiene 3 columnas. Si se decidiera aplicar además el bloque A a un panel aparte, sus resultados irían en una tabla propia `[pendiente: confirmar con Eugenio]`.

| Ítem / Criterio evaluado | Forma evaluada | `ECON-01` | `ECON-02` | `ECON-03` | Promedio | Mín – Máx |
|---|---|---|---|---|---|---|
| 1. Comprensión sin formación previa | Ambas en conjunto | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 2. Severidad comprensible y bien asignada | Cualquiera | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 3. Impacto cuantificado | Pantalla (`.md` / visor) | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 4. Orígenes para ubicar la fila (`origen_id` / celda) | Hoja / Excel devuelto | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 5. Orden por severidad descendente | Pantalla | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 6. Lenguaje apropiado para obra | Cualquiera | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 7. Utilidad para decidir qué corregir | Ambas en conjunto | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| 8. Confianza como complemento manual | Ambas en conjunto | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |
| **Promedio por economista / Global (meta ≥ 4,00)** | — | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** |

**Cómo se analiza:** Análisis descriptivo puro sobre N = 3 participantes (prueba de uso) y el panel de expertos: frecuencias, porcentajes de eficacia, medianas, promedios y rangos (mínimo–máximo), sin pruebas de significancia estadística. Los campos abiertos se transcriben literalmente agrupados por tema sin atribución nominal.

**Si el resultado es negativo, se reporta así:** Si el puntaje SUS promedio queda por debajo de 68, la referencia publicada (Sauro y Lewis, por verificar), o el promedio global de la Tabla 4.4 resulta < 4,00 (o algún ítem < 3,00), se reporta explícitamente como veredicto `NO CUMPLE` (o hallazgo de usabilidad) identificando los ítems críticos y las dificultades observadas en pantalla. Una alerta que ninguno de los 3 entendió («no» en la Tabla 4.3b) se reporta como hallazgo de comprensión, con su cita textual.

---

## 4.3 Capa 3: Precisión medida

**Objetivo específico al que responde:** **OE1** (línea base diagnóstica del procedimiento tradicional) y **OE4** (evaluar el sistema frente al procedimiento tradicional en detección de errores, tiempo de preparación de reajustes, acierto de la proyección P50/P80 y estimación del costo final).

### 4.3.1 Detección de errores en presupuestos (fallas inyectadas, falsos positivos por causa, tiempo de revisión y kappa)

**Qué se afirma y cuándo fracasa (texto sellado).** El [plan de la evaluación no circular](../planes/2026-11-23-plan-auditoria-no-circular.md), sellado en la etiqueta `reglas-congeladas-2026-11-24`, fija antes de medir la afirmación que se defiende y su criterio de fracaso. La afirmación es, literalmente:

> «Sílice detecta de forma reproducible errores que un experto independiente confirma: X de N fallas inyectadas por un tercero, con intervalo de confianza del 95 % amplio. Su tasa de falsos positivos es Y por causa, con un costo de revisión de Z minutos por libro. No detecta errores de criterio de obra fuera de su taxonomía, y sus 8 umbrales viales son supuestos.»

X y N salen de la Tabla 4.5a; Y y Z, de la Tabla 4.5b. El criterio de fracaso, también literal:

> «Se fija y se sella con hash **antes** de medir el lote nuevo. Si se cumple cualquiera de estos tres, la tesis afirma solo «herramienta de apoyo con cobertura limitada», y lo reporta tal cual:
> - detecta menos del 50 % de las fallas que inyectó el tercero;
> - más del 40 % de las causas que informa en libros reales son falsos positivos según el experto;
> - el kappa entre el experto y Sílice queda por debajo de 0,4.»

**Aclaraciones fechadas, sin cambiar el criterio** ([acta del 2026-11-25](../bitacora/2026-11-25-cifra-oficial-de-deteccion.md), dos decisiones de Eugenio tomadas antes de medir los libros nuevos):
1. La cifra oficial de detección es la de **todas las fallas a la vez**. La de **una por vez** se informa al lado como cifra secundaria, con su propio intervalo de Wilson, y no decide el fracaso.
2. Para el criterio del 50 % cuenta como detectada solo la falla que Sílice señaló **y** el evaluador confirmó como verdadera; las señaladas sin confirmar se informan al lado. En la medición automática, sin evaluador, cuenta lo señalado, y se dice cuál de las dos se evaluó.

**Los dos kappa no son el mismo:**
- **Kappa del piloto, entre dos economistas.** Dos economistas marcan por separado 2 presupuestos que no entran en la evaluación. Mide si la planilla de hallazgos es un instrumento confiable. La referencia es 0,61, el inicio del acuerdo «sustancial» según Landis y Koch (1977), cuya escala sigue con verificación pendiente en [referencias.md](referencias.md). Un valor bajo obliga a revisar las instrucciones de la planilla antes de medir; **no** es un criterio de fracaso. En el plan B (sin ingeniero) se calcula de la misma forma entre los economistas que juzgan el lote.
- **Kappa entre el experto y Sílice.** Es el tercer criterio de fracaso sellado (umbral 0,4) y compara la marca a ciegas del ingeniero de costos externo con lo que señala Sílice. `[pendiente: definir, antes de abrir los libros nuevos y con acta fechada, cómo se calcula. Ningún script lo produce hoy: medir_auditoria_libro.py calcular --otra da el kappa entre dos planillas de evaluadores y es ese el que su salida compara con 0,4]`.

**De dónde salen los datos:**
- **Lote nuevo (Fase 3):** 1 o 2 libros reales que nadie ha visto, pedidos a la empresa (mejor si son viales), y el libro sintético del tercero: una copia con las fallas que inyecta un tercero con [scripts/inyector_fallas.py](../../scripts/inyector_fallas.py), con semilla fija, desde la taxonomía externa que Nicolaz o el tutor escriben a ciegas y que se sella en la etiqueta `taxonomia-tercero-sellada` ([guía del tercero](2026-11-25-guia-taxonomia-tercero.md)). Se audita con las reglas congeladas en `reglas-congeladas-2026-11-24`. Los 5 libros reales de desarrollo y el libro ficticio de 12 errores **no** entran: guiaron las reglas (límite 7).
- **Quién decide qué es verdadero:** el ingeniero de costos externo, que marca a ciegas, sin ver lo que dijeron las reglas («hallazgo verdadero» del plan: una diferencia que un presupuestista corregiría antes de entregar el presupuesto). Los 3 economistas también marcan a ciegas el lote nuevo. **Plan B sin ingeniero:** juzgan los 3 economistas, con kappa entre ellos; la afirmación baja a «concordancia con revisores del dominio» y se declara como límite.
- **Detección automática:** [scripts/medir_inyeccion.py](../../scripts/medir_inyeccion.py) encadena inyectar, recalcular con LibreOffice, trasplantar los valores y auditar, y descuenta los hallazgos que el libro base ya tenía. Sin opciones da la cifra oficial (todas a la vez); con `--una-por-vez`, la secundaria. Cada corrida escribe, fuera del repositorio, un JSON con el manifiesto de corrida, `totales.detectadas`, `totales.intervalo_wilson_95` y el criterio de fracaso evaluado.
- **Marca de los evaluadores:** [scripts/medir_auditoria_libro.py](../../scripts/medir_auditoria_libro.py) (`clave`, `exportar --recalcular`, `calcular`), según el [protocolo de medición](2026-11-23-protocolo-medicion-auditoria.md). `calcular` da la precisión, los falsos positivos, la detección señalada y la confirmada (cada una con su intervalo de Wilson al 95 %), la exhaustividad aproximada y el kappa entre dos planillas.
- **Tiempo de revisión (Z):** minutos de revisión por libro, cronometrados en la sesión de marca (plan, Fase 3: «Se cronometran los minutos de revisión por libro, que son el costo de los falsos positivos»). Ningún script lo produce: se anota en la planilla local.
- **Unidad de conteo:** **Causa raíz** (`causas_de_hallazgos`: misma regla y misma primera cláusula de descripción), excluyendo avisos de regla «no aplicable». Las ocurrencias repetidas por fórmulas copiadas se informan como razón de compactación (`hallazgos totales / causas raíz`).

**Tabla 4.5a. Detección de las fallas inyectadas por el tercero (libro sintético del lote nuevo)**

| Modo de siembra | Papel de la cifra | Fallas inyectadas (N) | Señaladas por Sílice (n de N, %) | Wilson 95 % (señaladas) | Señaladas y confirmadas verdaderas por el evaluador (n de N, %) | Wilson 95 % (confirmadas) | Señaladas que el evaluador marcó «Falso» |
|---|---|---|---|---|---|---|---|
| Todas a la vez | **Oficial:** decide el criterio del 50 % con la cifra confirmada (sin evaluador, con la señalada, y se declara) | `[pendiente: medir_inyeccion.py, totales.inyectadas]` | `[pendiente: medir_inyeccion.py, totales.detectadas y tasa_deteccion]` | `[pendiente: medir_inyeccion.py, totales.intervalo_wilson_95]` | `[pendiente: medir_auditoria_libro.py calcular --clave, fila «Detección, señalado y confirmado verdadero»]` | `[pendiente: ídem, columna «Intervalo de Wilson 95 %»]` | `[pendiente: ídem, «señalados marcados Falso»]` |
| Una por vez | Secundaria: se informa al lado y no decide el fracaso | `[pendiente: medir_inyeccion.py --una-por-vez, totales.inyectadas]` | `[pendiente: ídem, totales.detectadas]` | `[pendiente: ídem, totales.intervalo_wilson_95]` | No aplica: los evaluadores marcan la planilla de todas a la vez | No aplica | No aplica |

Los libros mutantes que Sílice rechaza en el modo de una por vez se cuentan aparte (`totales.rechazados`), no como detectados: `[pendiente: n]`.

**Tabla 4.5b. Precisión, falsos positivos por causa y tiempo de revisión (lote nuevo, marca a ciegas)**

| Conjunto evaluado | Quién marca | Causas informadas (hallazgos; compactación) | Precisión (verdaderas / marcadas, %) y pendientes | Wilson 95 % (precisión) | Falsos positivos (falsas / marcadas, %) | Wilson 95 % (falsos positivos) | Exhaustividad aproximada (Verdadero / (Verdadero + escapados), %) | Minutos de revisión por libro (Z) |
|---|---|---|---|---|---|---|---|---|
| Piloto (2 presupuestos fuera de la evaluación) | 2 economistas, por separado | `[pendiente: medir_auditoria_libro.py calcular]` | `[pendiente: n de N (%); pendientes]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | No se informa: el piloto solo mide la confiabilidad de la planilla |
| Libro real nuevo 1 | Ingeniero de costos externo (plan B: economistas) | `[pendiente: medir_auditoria_libro.py calcular]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: cronómetro]` |
| Libro real nuevo 2 (si la empresa lo entrega) | Ingeniero de costos externo (plan B: economistas) | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: cronómetro]` |
| Libro sintético del tercero | Ingeniero de costos externo (plan B: economistas) | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: cronómetro]` |
| **Libros reales del lote nuevo (decide el criterio del 40 %)** | — | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente]`** | **`[pendiente: mediana y rango]`** |

**Tabla 4.5c. Acuerdo entre evaluadores y con Sílice (kappa de Cohen)**

| Kappa | Entre quiénes | Para qué sirve | Referencia o umbral | Lo produce | Resultado |
|---|---|---|---|---|---|
| Piloto | 2 economistas, sobre 2 presupuestos fuera de la evaluación | Confiabilidad de la planilla antes de medir | 0,61 (Landis y Koch, 1977; verificación pendiente); no es criterio de fracaso | `medir_auditoria_libro.py calcular --otra` | `[pendiente: κ y hallazgos marcados por los dos]` |
| Plan B (solo si no hay ingeniero) | Los economistas que juzgan el lote nuevo | Sustenta la afirmación rebajada a «concordancia con revisores del dominio» | Se informa; no está sellado como umbral | `medir_auditoria_libro.py calcular --otra` | `[pendiente: κ o «no aplica»]` |
| Experto–Sílice | Ingeniero de costos externo y Sílice | Tercer criterio de fracaso sellado | < 0,4: fracaso | `[pendiente: definir el cálculo; ningún script lo produce hoy]` | `[pendiente]` |

**Tabla 4.5d. Criterio de fracaso sellado y su resultado**

| Criterio sellado (cita literal del plan) | Cifra que lo decide | Resultado | ¿Se cumple? |
|---|---|---|---|
| «detecta menos del 50 % de las fallas que inyectó el tercero» | Tabla 4.5a, todas a la vez, confirmadas por el evaluador (sin evaluador, señaladas, y se declara) | `[pendiente: n de N (%) y Wilson 95 %]` | `[pendiente: sí / no]` |
| «más del 40 % de las causas que informa en libros reales son falsos positivos según el experto» | Tabla 4.5b, fila de libros reales del lote nuevo | `[pendiente: n de N (%) y Wilson 95 %]` | `[pendiente: sí / no]` |
| «el kappa entre el experto y Sílice queda por debajo de 0,4» | Tabla 4.5c, fila experto–Sílice (no el kappa del piloto) | `[pendiente: κ]` | `[pendiente: sí / no]` |
| **Afirmación que se sostiene** | Si se cumple cualquiera de los tres: «herramienta de apoyo con cobertura limitada»; si no, la afirmación sellada con X, N, Y y Z | — | `[pendiente]` |

**Cómo se analiza:** Cálculo determinista de proporciones por causa raíz, cada una con su intervalo de Wilson al 95 % (que con muestras pequeñas será amplio, como anticipa la afirmación sellada), y $\kappa$ de Cohen ((observado − esperado) / (1 − esperado)), calculado con fracciones exactas para que un 0,4 no quede por debajo del umbral por redondeo. El criterio de fracaso se evalúa con enteros, sin redondear, y se reporta tal cual. La comparación con la línea base humana del [protocolo](2026-11-23-protocolo-medicion-auditoria.md) es ilustrativa: con 3 economistas no hay potencia estadística.

**Si el resultado es negativo, se reporta así:** Si se cumple cualquiera de los tres criterios de la Tabla 4.5d, la tesis afirma solo «herramienta de apoyo con cobertura limitada» y lo reporta tal cual, sin cambiar reglas ni umbrales después de abrir los libros. Si el $\kappa$ del piloto queda por debajo de 0,61, se documenta la ambigüedad detectada y la revisión aplicada a las instrucciones antes de la medición principal (eso no es un fracaso del sistema). En todos los casos se desglosa por regla (`F1`, `L1`–`L11`, `R1`–`R7`, `VR1`–`VR8`, `AH1`–`AH12`) y por categoría de la taxonomía qué tipos de error generaron falsos positivos o se escaparon.

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

### 4.3.4 Oráculo independiente, sensibilidad de los umbrales y libros no interpretables

**Objetivo específico al que responde:** **OE4**. El plan no circular pide presentar los resultados en 3 capas (oráculo, inyección y juicio experto) y publicar, sin calibrar nada, la sensibilidad de los umbrales viales y la tasa de libros no interpretables («Aparece en el capítulo de resultados»). La inyección y el juicio experto están en §4.3.1; esta sección trae lo demás. Todo se corre sobre el lote nuevo con las reglas congeladas, salvo la sensibilidad, que usa el caso vial ficticio, y el banco de ensayo del oráculo (el libro ficticio de 12 errores).

**De dónde salen los datos:**
- **Oráculo:** [scripts/oraculo_libro.py](../../scripts/oraculo_libro.py) recalcula el libro con LibreOffice sin interfaz, un motor ajeno a Sílice, y escribe fuera del repositorio un JSON con el manifiesto de corrida (versión de LibreOffice, configuración regional y huellas) y las discrepancias por celda. Solo cubre F1: prueba que el valor guardado coincide con su fórmula, no que la fórmula sea correcta (plan, «Qué técnicas sirven»). Criterio de éxito del plan: en el libro ficticio de 12 errores, el oráculo y F1 coinciden en el 100 % de las fallas de cálculo y toda diferencia queda explicada.
- **Sensibilidad:** [scripts/sensibilidad_umbrales.py](../../scripts/sensibilidad_umbrales.py) barre en ±50 % cada umbral vial marcado como supuesto declarado en `adapters/vial/constantes.py` (el plan lo describe como «los umbrales VR1 a VR8») sobre la vía ficticia de `data/samples/vial/via_ficticia.csv` y cuenta cuántos hallazgos VR cambian. No se calibra con los mismos economistas que evalúan.
- **Libros no interpretables:** [scripts/tasa_no_interpretable.py](../../scripts/tasa_no_interpretable.py) audita cada libro de una carpeta fuera del repositorio y agrupa por motivo los rechazos de la guardia (`ArchivoRechazado`) y los fallos de interpretación (`LibroNoInterpretable`), sin nombres de archivo ni montos.

**Tabla 4.9. Oráculo independiente (LibreOffice) frente a los valores guardados**

| Libro | Fórmulas recalculadas | Discrepancias por celda | Discrepancias que también señala F1 | Discrepancias sin explicar | Versión de LibreOffice y configuración regional |
|---|---|---|---|---|---|
| Libro ficticio de 12 errores (banco de ensayo del criterio del plan) | `[pendiente: oraculo_libro.py]` | `[pendiente]` | `[pendiente]` | `[pendiente: debe ser 0]` | `[pendiente: manifiesto]` |
| Libros del lote nuevo | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: manifiesto]` |

**Tabla 4.10. Sensibilidad ±50 % de los umbrales viales supuestos (caso ficticio)**

| Umbral (regla) | Valor supuesto | Hallazgos VR con −50 % | Hallazgos VR con el valor supuesto | Hallazgos VR con +50 % | ¿Cambia el veredicto? |
|---|---|---|---|---|---|
| `[pendiente: una fila por cada umbral supuesto que informe sensibilidad_umbrales.py]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente: sí / no]` |

**Tabla 4.11. Libros no interpretables (lote nuevo)**

| Libros recibidos | Auditados | Rechazados por la guardia (por motivo) | No interpretables (por motivo) | Tasa de no interpretables (%) |
|---|---|---|---|---|
| `[pendiente: tasa_no_interpretable.py]` | `[pendiente]` | `[pendiente]` | `[pendiente]` | `[pendiente]` |

**Cómo se analiza:** Conteos y porcentajes descriptivos. La sensibilidad se publica tal cual y no se usa para mover ningún umbral; un umbral que cambia el veredicto se declara como supuesto crítico.

**Si el resultado es negativo, se reporta así:** Una discrepancia del oráculo sin explicar se informa con su celda anonimizada y su causa probable; un umbral que cambia el veredicto con ±50 % se marca como supuesto que la tesis no puede sostener sin dato; los libros no interpretables se reportan con su motivo, sin forzar su lectura.

---

## 4.4 Límites del estudio

1. **Tamaño reducido (N = 3 economistas más 2 personas nuevas en el SUS):** Al tratarse de un censo de 3 profesionales de la empresa objeto de estudio, más 2 personas ajenas en la prueba de uso, no es procedente realizar inferencia estadística ni generalización poblacional; todos los resultados humanos se reportan de forma descriptiva.
2. **Exhaustividad aproximada y dependencia de la taxonomía externa:** En los libros reales no se conoce el universo absoluto de errores ocultos, por lo que la exhaustividad depende del esfuerzo de revisión de los evaluadores. La detección medida depende de las categorías de la taxonomía que escribe un tercero (Nicolaz o el tutor) **a ciegas**, sin abrir las reglas de auditoría ni los resultados del libro de desarrollo, y que se sella con su huella en la etiqueta `taxonomia-tercero-sellada` antes de abrir los libros nuevos; las fallas las inyecta ese tercero con `scripts/inyector_fallas.py` y semilla fija ([guía del tercero](2026-11-25-guia-taxonomia-tercero.md)). Las familias que el inyector no puede producir (hoy, la duplicación, los errores de razonamiento o de dominio y los cualitativos) se anotan en la lista `[[sin_operacion]]` y Sílice no se midió contra ellas. Además, un libro inyectado no es un libro real, y un libro de edificación no es vial (plan, «Puntos ciegos»).
3. **Condición de los datos históricos para P50/P80 y costo final:** La proyección probabilística requiere al menos 12 meses históricos completos coincidentes entre todas las series y la tasa BCV, bajo el supuesto de gasto uniforme en el plazo; la estimación del costo final solo es evaluable si se dispone de al menos una obra culminada con su costo real documentado.
4. **Restricciones del dominio y alcance de la IA:** El núcleo de cálculo (`core/`) permaneció inalterado; las reglas especializadas y la proyección operan en capas externas (`adapters/`, `aplicacion/`). Además, la IA se limita estrictamente a proponer o narrar cifras ya calculadas determinísticamente y su evaluación empírica completa con proveedor en la nube depende de la disponibilidad de ejecución autorizada.
5. **Instrumentos validados antes de medir:** las tareas y la hoja de observación del guion de uso, y la matriz de hallazgos, se aprueban por juicio de 3 expertos antes de llenar las Tablas 4.3 a 4.6 (con sus subtablas); el cuestionario SUS es estandarizado y se usa en una versión en español publicada (Sevilla-Gonzalez et al., 2020). Las tareas T1 a T3 las conduce el autor del sistema; solo la prueba de comprensión de las alertas la conduce un tercero.
6. **El estudio de mercado depende de lo que la empresa anota (2026-11-24):** Sílice no trae precios de internet por diseño (funciona sin red y cada cifra tiene una fuente comprobable); su propuesta de precio sale de las cotizaciones, compras y precios de la competencia que la empresa anota, en una ventana de 90 días. Con menos de 3 observaciones por insumo, la mediana y los cuartiles no son representativos, y en bolívares la inflación hace poco comparables precios separados por semanas dentro de esa ventana; por eso el estudio se presenta como apoyo a la decisión, no como precio de mercado, y se reporta cuántos insumos críticos (clase A) tenían al menos 3 precios vigentes ([acta del consejo](../bitacora/2026-11-24-consejo-auditoria-alertas-mercado.md)). El mínimo de observaciones y la ventana son supuestos por confirmar con el ingeniero de costos.
7. **Reglas ajustadas sobre el libro de desarrollo (2026-11-24):** la medición una falla por vez en el libro de desarrollo pasó de 5 a 10 de 12 fallas detectadas después de cerrar tres huecos de reglas que esas mismas fallas revelaron; esas cifras miden lo aprendido y no la generalización, y se reportan solo como historia del desarrollo ([acta](../bitacora/2026-11-24-huecos-de-reglas-antes-del-congelamiento.md)). La cifra de la tesis es la de la Fase 3, sobre libros que nadie ha visto, con fallas de la taxonomía del tercero y con las reglas congeladas en la etiqueta `reglas-congeladas-2026-11-24`. El criterio sellado no decía cómo se siembran las fallas ni qué cuenta como detectada, y en un ensayo con un libro ficticio (no es resultado de la tesis) las dos formas de sembrar dieron, con las herramientas de medición del commit `06ba7491`, 3 de 12 (todas a la vez) y 11 de 12 (una por vez); la primera medición del ensayo (4 y 10 de 12) usó el inyector anterior a su corrección ([enmienda del 2026-11-27](../bitacora/2026-11-25-cifra-oficial-de-deteccion.md)). Los dos modos no miden lo mismo: todas a la vez pide el hallazgo en la celda exacta de la falla (localización) y una por vez cuenta cualquier hallazgo nuevo (reacción). Por eso Eugenio tomó dos decisiones el 2026-11-25, antes de medir los libros nuevos ([acta](../bitacora/2026-11-25-cifra-oficial-de-deteccion.md)): la cifra oficial es la de todas las fallas a la vez y la de una por vez se informa al lado, con su propio intervalo de Wilson, sin decidir el fracaso; y para el criterio del 50 % cuenta como detectada solo la falla que el evaluador confirma como verdadera, con las señaladas sin confirmar al lado (sin evaluador cuenta lo señalado, y se dice). El acta aclara el criterio sin cambiar sus umbrales; después de abrir los libros nuevos no se revierte.
8. **Agrupación de hallazgos en causas (2026-11-25):** la precisión y los falsos positivos se cuentan por causa, y las causas las arma `aplicacion/causas_raiz.py`, que está sellado en la etiqueta del congelamiento. Una auditoría independiente (Argon, Gemini) observó que separa en causas distintas dos hallazgos de la misma regla cuando su texto cita códigos de insumo o descripciones de partida diferentes, en lugar de unirlos. Eso puede aumentar el número de causas y mover la precisión por causa. Como el archivo está sellado, no se corrigió antes de medir: el efecto se informa con la cifra, y la corrección queda para después de la defensa.
9. **Umbrales viales supuestos y errores fuera de la taxonomía:** la afirmación sellada lo dice así: «No detecta errores de criterio de obra fuera de su taxonomía, y sus 8 umbrales viales son supuestos». De los 17 umbrales viales, 8 se fijaron sin datos; su efecto se mide solo como sensibilidad ±50 % (Tabla 4.10) y no se calibran. Los errores de criterio de obra (rendimientos, depreciación, toneladas) no los ven ni las taxonomías de hojas de cálculo ni el oráculo de LibreOffice, solo el experto; y los falsos negativos fuera de la taxonomía no se miden: nadie mide lo que las reglas no pueden ver (plan, «Puntos ciegos»).
