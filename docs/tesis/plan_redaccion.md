# Plan de redacción de los capítulos

Guión operativo para escribir el trabajo de grado. La **estructura** y la **matriz de
trazabilidad** viven en [esqueleto_tesis.md](esqueleto_tesis.md) y no se repiten aquí (DRY);
este documento añade lo que hace falta para sentarse a redactar: el guión de cada capítulo, las
cifras ya medidas listas para citar con su comando de regeneración, las dependencias con las
decisiones del [dossier de G0](../dossier_g0.md) y el tablero de avance.

**Dónde se escribe:** un archivo por capítulo en `docs/tesis/capitulos/`
(`01-el-problema.md`, `02-marco-teorico.md`, `03-marco-metodologico.md`, `04-desarrollo.md`,
`05-resultados.md`, `06-conclusiones.md`, `00-introduccion.md` — la introducción se escribe de
última). Cada archivo abre con la tabla `capítulo / estado / última revisión` y se registra en el
tablero de la sección 6.

---

## 1. Convenciones de redacción

- **Voz:** impersonal («se diseñó», «se verificó»), pasado para lo hecho, presente para lo que el
  sistema hace. Nada de primera persona.
- **Cifras:** coma decimal en el texto («12,46 %»); toda cifra citada debe aparecer en la tabla de
  la sección 5 con su comando de regeneración — una cifra irrepetible no entra al documento.
- **Citas:** norma institucional (Bases §12). Las bases normativas mínimas: COVENIN 2000,
  convención colectiva de la construcción (pendiente D4), AACE 18R‑97 (clase 3), IEEE 830,
  IEEE 829, ISO/IEC 25010.
- **Terminología:** BIM‑5D y «sombra digital»; jamás «gemelo digital» (decisión D8, pendiente de
  confirmación del tutor — si cambia, se corrige en un solo lugar: aquí).
- **Figuras:** cada capítulo lista las suyas en su guión; se generan desde las fuentes (diagramas
  de `docs/arquitectura.md`, ER de `docs/modelo_datos.md`, capturas de la UI, tablas de
  resultados) y se guardan en `docs/tesis/figuras/`.
- **DRY documental:** los capítulos citan y resumen; no copian páginas de la ERS ni de los
  manuales — esos van como anexos (esqueleto §1, fila «Anexos»).

## 2. Orden de escritura recomendado

No se escribe en el orden del índice sino del material más consolidado al menos:

| Orden | Capítulo | Por qué |
|---|---|---|
| 1.º | IV. Desarrollo | todo existe: código, docs, bitácoras; cero dependencias externas |
| 2.º | V. Resultados | los cinco indicadores están medidos; solo el juicio de expertos queda «pendiente» declarado |
| 3.º | III. Marco metodológico | `docs/metodologia.md` ya es el 80 % del capítulo |
| 4.º | II. Marco teórico | exige leer `docs/fuentes/Estado_del_Arte_BIM5D_ML_APU.pdf`; D4 puede esperar como nota |
| 5.º | I. El problema | los objetivos dependen de la decisión D3 (OE7 o complementario) |
| 6.º | Conclusiones | responden a lo ya escrito |
| 7.º | Introducción | se escribe cuando el resto existe |

La única dependencia dura con G0 es la **D3** (redacción de los objetivos): si la reunión se
atrasa, se escribe todo lo demás y el capítulo I queda con los objetivos en las dos variantes,
listas para elegir.

## 3. Guión por capítulo

### Capítulo I — El problema

Secciones: planteamiento · formulación (pregunta principal y secundarias, Bases §2.4) ·
objetivos (general + OE1–OE6, **más OE7 según D3**) · justificación · alcance y delimitación.

- **La evidencia va en dos planos**
  ([spec del Sprint R1](../superpowers/specs/2026-09-15-sprint-r1-capitulos-design.md) §3). La
  **literatura** sostiene, con citas verificadas, que el problema ocurre en la práctica. El
  **caso didáctico** de la clínica, un ejercicio académico ficticio de 1 586,61 USD
  ([CLAUDE.md §1](../../CLAUDE.md)), muestra el **mecanismo** con siete inconsistencias
  documentadas en [linea_base.md](../linea_base.md) (curva que cierra en 99,30 %, encofrado 5,92
  vs 4,48 m², concreto 0,415 vs 0,224 m³, «mts» vs «Pieza», 3/4" vs 4", 9,74 m³ excavados vs
  1,30 rellenados, depreciación 1,00 vs 0,03). El planteamiento no argumenta en abstracto, pero
  tampoco presenta el caso como obra real.
- **Delimitación honesta:** caso de estudio único y didáctico (drenaje de una clínica), dominio
  sanitario como línea base, extensión multidominio según D3, datos de mercado escasos (declarado
  en G2) y **validación con presupuestos reales como limitación** hasta que se suministren.
- Figuras: tabla de las siete inconsistencias con montos; foto/plano del caso si las Bases lo traen.

### Capítulo II — Marco teórico

Secciones: antecedentes (internacional → latinoamericano → nacional, desde el PDF de estado del
arte) · bases teóricas · bases normativas · definición de términos.

- **Bases teóricas, en este orden:** ciclo de vida del proyecto y estimación de costos; BIM y la
  dimensión 5D; sombra digital vs gemelo digital (D8: por qué este sistema es lo primero);
  estructura venezolana del APU (FCAS, bono, administración/utilidad en cascada); aprendizaje
  automático para costos (y por qué la escasez de datos degrada a reglas — prepara G2);
  NLP y similitud del coseno para normalización de partidas.
- **Bases normativas:** COVENIN 2000 (mediciones y codificación), convención colectiva (**D4:
  fuente del FCAS 600 %** — hasta la decisión, redactar con la nota «parámetro del caso de
  estudio»), AACE 18R‑97 (qué es clase 3 y por qué el rango −20 %/+30 %).
- Anclar cada antecedente a qué le aporta a ESTE trabajo (una línea), no resumir papers sueltos.

### Capítulo III — Marco metodológico

Secciones: tipo y diseño de la investigación (Bases §8) · fases I–VI · técnicas e instrumentos ·
fuentes de datos · criterios de validación · metodología de desarrollo.

- El corazón ya está escrito: [metodologia.md](../metodologia.md) (Scrum‑Cascada, DRY, sesiones,
  Definition of Done, indicadores §8, riesgos y compuertas §9). El capítulo lo **narra**, no lo
  duplica.
- **Instrumentos, con nombre y apellido:** pruebas automatizadas (pytest, 395 casos, `-W error`),
  metas de sprint automatizadas (`scripts/meta_alpha.py`, 12/12), observación estructurada
  (indicador 3), juicio de expertos (instrumento Likert del
  [dossier G0, anexo A](../dossier_g0.md)), medición reproducible de desempeño
  (`scripts/medir_rnf03.py`).
- **Las compuertas G0–G2 como decisión metodológica:** criterios de degradación declarados antes
  de conocer el resultado (G2 es el ejemplo estrella: la tabla de degradación existía desde la
  Fase 0 y se aplicó tal cual). Esto distingue el trabajo de un desarrollo ad hoc.
- Figura: el diagrama de trazabilidad objetivo → fase → sesión → UC → RF → prueba → commit →
  indicador (metodologia §7).

### Capítulo IV — Desarrollo de la propuesta

El más largo. Orden sugerido (el mismo del PLAN, que es el orden causal):

1. **Requerimientos** — ERS: 8 UC, 31 RF, 9 RNF; el criterio de aceptación medible por RF.
2. **Modelo de datos** — decisiones que valen la pena contar: versionado híbrido (congelar y
   recomputar), variantes de insumos homónimos (el octavo defecto → candidata R8, D2),
   rendimiento medido con clave foránea a la ejecución.
3. **Arquitectura** — núcleo cerrado / adaptadores abiertos; los contratos como única frontera;
   las dos guardias automáticas (65 pruebas de arquitectura + `git diff --stat core/`).
4. **Motor de costos** — la fórmula (CLAUDE.md §4) y los dos errores clásicos que las pruebas
   vigilan (materiales divididos por rendimiento; administración y utilidad sumadas). La línea
   base como oráculo: pruebas antes que implementación.
5. **Presupuesto y curva** — cierre al 100 % por construcción (el caso didáctico cerraba al 99,30 %).
6. **Actualización masiva de precios (UC‑02)** — recalcular sin editar composiciones; histórico
   de cambios e incidencias (el dato que luego alimenta ML).
7. **Adaptador civil** — IFC (G1, con su salvedad) y reglas paramétricas con expresión y
   parámetros registrados en cada cantidad (lo que hace posible R1).
8. **Verificación R1–R7 y el informe** — una regla por inconsistencia del caso; el informe se
   genera siempre; hallazgos con severidad, impacto y `origen_id`.
9. **Extensibilidad (I5)** — tres adaptadores nuevos con el núcleo intacto; guía para terceros
   en el manual técnico.
10. **Módulos ML** — normalización (umbral 0,5; RF‑17 5/5), anomalías (Isolation Forest,
    semilla 42, abstención con n < 8), predicción (G2 → reglas con sensibilidad, limitación).
11. **Interfaz y API** — ocho pantallas, ocho UC; montos como texto en la frontera JSON;
    escenarios UC‑08 sin persistencia (D6).

Cada sección: el problema → la decisión → la evidencia (prueba o bitácora). Las bitácoras de
`docs/bitacora/` son la memoria de las decisiones: citarlas como anexo H.

### Capítulo V — Resultados y evaluación

Un apartado por indicador, con su cifra y su procedencia (tabla de la sección 5):

| Indicador | Resultado a redactar |
|---|---|
| 1. Inconsistencias | **7 de 7** detectadas, una por regla; más los hallazgos adicionales 8 (precio no uniforme, D2) y 9 (las cinco discrepancias diarias que explican la brecha de 11,11 USD, sustento de R7/D1) |
| 2. Exactitud | desviación **0,00 %** frente a la línea base corregida; muy dentro de clase 3 AACE (−20 %/+30 %) |
| 3. Tiempo | recálculo de 100 partidas en **1,17 s** (meta < 5 s); el cronometraje manual vs automatizado queda como medición de la defensa (observación estructurada) |
| 4. Extensibilidad | `git diff --stat core/` **vacío** tras telecom, industrial y sistemas; 65 pruebas de arquitectura lo re‑verifican en cada corrida |
| 5. Desempeño predictivo | MAPE **12,46 %** · RMSE **5,10 USD** · R² **0,9974** — presentados como resultado de la **degradación declarada** (reglas), no como logro de ML |

Además: la evaluación ISO/IEC 25010 (tabla de veredictos de
[calidad_iso25010.md](../calidad_iso25010.md): 5 cumplen, 1 pendiente, 2 parciales — contarlo
así, con las brechas a la vista, es más fuerte que esconderlas), el plan IEEE 829 (395 pruebas,
cobertura núcleo 98,05 %) y el juicio de expertos cuando se aplique (anexo A del dossier).

### Conclusiones y recomendaciones

- Responder la pregunta principal y las cinco secundarias **una por una** (la tabla del
  esqueleto §4 dice dónde está cada respuesta; conclusión sin pregunta es relleno).
- **Limitaciones = las salvedades del dossier §4**, con nombre: G1 (IFC programático), G2
  (degradación por datos), RNF‑04 y RNF‑07 pendientes, RF‑16 acotado (según D5).
- **Recomendaciones que ya tienen semilla en el repo:** regla R8 (D2), flujo de creación de
  partidas (D5), IFC de modeladores reales, conectores de listas de precios (cada conector
  produce una lista que entra por UC‑02), evolución hacia sombra digital con rendimientos
  medidos (UC‑06 ya registra la realimentación de obra).

### Introducción

Una página de contexto, el problema en un párrafo (con el caso y su monto), el aporte en un
párrafo (verificación imposible-por-construcción + extensibilidad), y la estructura del
documento. Se escribe al final, cuando ya se sabe qué se está introduciendo.

## 4. Dependencias con G0 (qué bloquea qué)

| Decisión | Capítulo que la espera | Mientras tanto |
|---|---|---|
| D3 (OE7 vs complementario) | I (objetivos), título | redactar ambas variantes de los objetivos |
| D4 (fuente FCAS) | II (bases normativas) | nota «parámetro del caso de estudio» |
| D8 (BIM‑5D / sombra digital) | II, título, resumen | usar la terminología actual (ya declarada) |
| D1, D2 (R7, R8) | V (indicador 1 y hallazgos 8–9) | redactar con R7 dentro y R8 como candidata |
| D5, D6 (RF‑16, UC‑08) | IV §11 y conclusiones | describir lo implementado + la decisión documentada |

Nada de esto impide empezar: el orden de la sección 2 existe precisamente para eso.

## 5. Cifras citables y cómo regenerarlas

Toda cifra del texto sale de aquí. Si una medición se repite y cambia, se actualiza esta tabla
y se buscan sus usos en los capítulos.

| Cifra | Valor (31/08/2026) | Comando / fuente |
|---|---|---|
| Inconsistencias detectadas | 7 de 7 | `uv run pytest tests/integration/test_auditoria_7_de_7.py` |
| Desviación vs línea base | 0,00 % (± 0,01 por PU) | `uv run pytest tests/unit/test_costing.py tests/integration/test_presupuesto_linea_base.py` |
| Núcleo intacto | diff vacío | `git diff --stat <rama-adaptador> -- core/` · `tests/unit/test_arquitectura.py` (65 casos) |
| MAPE · RMSE · R² | 12,46 % · 5,10 USD · 0,9974 | `uv run python scripts/generar_resultados_ml.py` → [resultados_ml.md](../resultados_ml.md) |
| Recálculo masivo | 1,17 s / 100 partidas | `uv run python scripts/medir_rnf03.py` |
| Suite y cobertura | 395 pruebas · núcleo 98,05 % | `uv run pytest -W error --cov=core` → [plan_pruebas.md §10](../plan_pruebas.md) |
| Total del caso | 1 586,61 USD · curva 99,30 % | [linea_base.md](../linea_base.md) · `data/linea_base/APUS_CLINICA.pdf` |
| Siete inconsistencias del caso didáctico (magnitudes) | encofrado 5,92 vs 4,48 m² (+32 %) · concreto 0,415 vs 0,224 m³ (+85 %) · curva 1 575,50 USD, 11,11 USD sin conciliar · relleno 1,30 vs ≈ 8,6 m³ · depreciación 0,03 vs 1,00 | [linea_base.md §5](../linea_base.md) · `tests/fixtures/apu_linea_base.py` |
| Dimensiones del caso didáctico | 24 m de PVC de 4" · cuatro tanquillas de 0,80 × 0,80 × 0,80 m con paredes de 0,10 m · cinco partidas | [linea_base.md §1](../linea_base.md) · `tests/fixtures/apu_linea_base.py` |
| Parámetros de costo del caso didáctico | FCAS 6,00 (600 %) · bono de alimentación 1,00 USD por obrero y día · administración 15 % · utilidad 10 %, en cascada | `core/contracts/apu.py` (`ParametrosCosto`) · [CLAUDE.md §4](../../CLAUDE.md) |
| Umbrales de la compuerta G2 (técnica según datos) | más de 200 registros por dominio: XGBoost con bosques aleatorios como contraste · de 50 a 200: razonamiento basado en casos · menos de 50: sistema de reglas con análisis de sensibilidad | [CLAUDE.md §8.1](../../CLAUDE.md) · `ml/prediction/reglas.py` (`tecnica_para`) |
| Inconsistencia del ejercicio ARENAZA | tubo corrugado 80 m (cómputo) vs 90 m (presupuesto) | [data/telecom/fuentes/README.md](../../data/telecom/fuentes/README.md) · `uv run pytest tests/integration/test_auditoria_arenaza.py` |
| Metas de sprint | 12/12 | `uv run python scripts/meta_i6.py` |
| Conteo G2 | civil 5 · resto 0 (< 50) | [resultados_ml.md](../resultados_ml.md) |
| Predicciones del caso | tabla PU base/estimado/rango | [resultados_ml.md](../resultados_ml.md) |

## 6. Tablero de avance

El tablero vive en un solo lugar: [capitulos/README.md](capitulos/README.md) (índice y estado de
los capítulos, con el resumen del proyecto para quien llega de nuevo). Se actualiza al cerrar
cada sesión de redacción, como la bitácora de un sprint.
