# Capítulos de la tesis — índice y estado de redacción

Este archivo es la **fuente única del estado de los capítulos**: se actualiza al cerrar cada
sesión de redacción, en el momento en que un capítulo avanza. El guión detallado de cada
capítulo, las cifras citables y las convenciones de redacción están en
[plan_redaccion.md](../plan_redaccion.md); la estructura y la matriz de trazabilidad, en
[esqueleto_tesis.md](../esqueleto_tesis.md). Aquí solo vive el tablero.

---

## 1. El proyecto en una página (para quien llega de nuevo)

Trabajo de grado: **sistema de generación y auditoría de Análisis de Precios Unitarios (APU)
multidominio**, asistido por modelo BIM‑5D y aprendizaje automático.

- **El problema.** Los presupuestos de obra se elaboran a mano (croquis → cómputo en hoja de
  cálculo → APU → presupuesto → plan de trabajo) y acumulan errores sin que nadie los detecte:
  cantidades sin respaldo geométrico, unidades incompatibles, curvas que no cierran, criterios
  inconsistentes entre partidas.
- **La evidencia.** Un presupuesto de drenaje de una clínica (5 partidas, 1 586,61 USD) con
  **siete inconsistencias** documentadas una a una en [linea_base.md](../../linea_base.md).
  Es un **ejercicio académico ficticio**, igual que los presupuestos ARENAZA: casos
  **didácticos** con el contenido y el formato de la práctica, no obras ejecutadas ni valores
  reales ([CLAUDE.md §1](../../../CLAUDE.md#1-qué-es-este-proyecto)). La validación con
  presupuestos reales es una limitación declarada hasta que el usuario los suministre.
- **La solución.** El sistema deriva las cantidades de una fuente trazable (IFC, reglas
  paramétricas, tablas), las costea con la estructura venezolana (FCAS, bono, administración y
  utilidad en cascada, todo en `Decimal`), produce presupuesto y curva de inversión, **verifica
  automáticamente** con siete reglas (R1–R7) generando siempre el informe de auditoría, y
  contrasta los precios con el mercado mediante ML.
- **La hipótesis arquitectónica.** El núcleo (`core/`) no cambia al agregar dominios (civil,
  telecom, industrial, sistemas): se demuestra con `git diff --stat core/` vacío y 65 pruebas
  de arquitectura ([CLAUDE.md](../../../CLAUDE.md) — hipótesis central).
- **Los resultados ya medidos** (procedencia y regeneración en
  [plan_redaccion.md §5](../plan_redaccion.md#5-cifras-citables-y-cómo-regenerarlas)):
  7 de 7 inconsistencias detectadas · desviación 0,00 % vs línea base corregida · recálculo de
  100 partidas en 1,17 s · núcleo intacto tras tres adaptadores · MAPE 12,46 % por reglas
  (degradación G2 declarada).
- **Metodología.** Híbrido Scrum‑Cascada con compuertas G0–G2 y criterios de degradación
  declarados a priori ([metodologia.md](../../metodologia.md)).

## 2. Tablero de estado

Estados: `pendiente` → `en redacción` → `borrador completo` → `revisado por tutor` → `final`.

| Orden de escritura | Capítulo | Archivo | Qué contiene | Estado | Última revisión | Bloqueado por |
|---|---|---|---|---|---|---|
| 1.º | IV. Desarrollo de la propuesta | `04-desarrollo.md` | requerimientos, modelo de datos, arquitectura, motor, verificación R1–R7, adaptadores, ML, UI/API | pendiente | — | — |
| 2.º | V. Resultados y evaluación | `05-resultados.md` | los cinco indicadores con cifra y procedencia; ISO/IEC 25010; IEEE 829 | pendiente | — | juicio de expertos (parcial, declarable) |
| 3.º | III. Marco metodológico | `03-marco-metodologico.md` | tipo y diseño, fases, instrumentos, compuertas como decisión metodológica | pendiente | — | — |
| 4.º | II. Marco teórico | `02-marco-teorico.md` | antecedentes, BIM‑5D, sombra digital, estructura del APU, ML, NLP, verificación por reglas, bases normativas, términos | borrador completo (revisado con la lista de cotejo, [acta R1](../revisiones/R1-capitulo-2.md)) | 2026-09-15 | D4 (como nota); práctica AACE 18R‑97 o 56R‑08; referencias pendientes marcadas |
| 5.º | I. El problema | `01-el-problema.md` | planteamiento con los casos didácticos, formulación, objetivos, justificación, delimitación | borrador completo (revisado con la lista de cotejo, [acta R1](../revisiones/R1-capitulo-1.md)) | 2026-09-15 | D3 (objetivos en dos variantes); referencias pendientes marcadas |
| 6.º | Conclusiones y recomendaciones | `06-conclusiones.md` | respuesta a cada pregunta, limitaciones con nombre, recomendaciones con semilla en el repo | pendiente | — | capítulos IV y V |
| 7.º | Introducción | `00-introduccion.md` | contexto, problema, aporte y estructura del documento | pendiente | — | todo lo demás |

## 3. Protocolo de actualización

1. Al **empezar** a redactar un capítulo: su fila pasa a `en redacción` y se crea el archivo en
   esta carpeta, abriendo con la tabla `capítulo / estado / última revisión`
   ([plan_redaccion.md](../plan_redaccion.md), «Dónde se escribe»).
2. Al **cerrar cada sesión** de redacción: se actualizan `Estado` y `Última revisión`
   (fecha absoluta, AAAA‑MM‑DD) y se anota la bitácora del sprint en
   [docs/bitacora/](../../bitacora/).
3. Toda cifra que entre a un capítulo debe existir en la tabla de cifras citables
   ([plan_redaccion.md §5](../plan_redaccion.md#5-cifras-citables-y-cómo-regenerarlas)); si una
   medición cambia, se actualiza allí y se buscan sus usos en los capítulos.
