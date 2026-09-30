# PLAN_UI — recorrido guiado de la interfaz

Continúa a [PLAN_PROTOTIPO.md](PLAN_PROTOTIPO.md), que cerró 12 de 12 metas, y **no** reemplaza a
[PLAN_ASISTENTE.md](PLAN_ASISTENTE.md): el asistente con IA (UC‑09) sigue siendo otro plan.

**Diseño que lo fundamenta:**
2026-09-23-ui-recorrido-guiado-design.md.
**Plan detallado (tarea por tarea):**
2026-09-23-ui-recorrido-guiado-u0-u1.md.

**Por qué existe.** La interfaz tiene nueve pantallas que funcionan y ninguna puerta de entrada.
Frase de origen (Eugenio, 2026‑09‑22): «no sé qué hacer y no hay un camino para llevar al usuario de
la mano». Este plan no agrega capacidades: agrega **orientación**.

**Objetivo al que responde:** medir la usabilidad de ISO/IEC 25010, la única característica sin
medición del proyecto, mediante RNF‑10 y CP‑07.

**Dependencia dura (cumplida).** El PR #7 está auditado y fusionado en `main` (`6fbb977`). U1 se
ejecuta como fase C3 del cierre, en `inc/cierre-C3`, que sale de `main` tras la fusión de C2
(`58ee828`); plan de la fase:
2026-09-24-cierre-c3-interfaz-scripts.md
(enmienda del 2026‑09‑24).

## Sesiones

| Sesión | Contenido | Cierre |
|---|---|---|
| U0.1 | ERS: UC‑12, RF‑36…RF‑43, actor «usuario nuevo / evaluador», RNF‑10, enmienda de la reserva de RF‑32 | ERS sin contradicción interna |
| U0.2 | RNF‑10 en calidad y plan de pruebas; bloque B del anexo A; CP‑07 redactado antes de ejecutarse; `streamlit>=1.36` | **GU0** |
| U1.1 | Hecha en C1 (salvaguarda de aislamiento de `data/apu.db`: `9f6b72b`, `10e3a10`); integración con `main` en C3 | salvaguarda observada en rojo y en verde |
| U1.2 | `ui/recorridos.py` y `ui/caso.py` | pruebas puras verdes |
| U1.3 | Pantalla de Inicio con estado vacío sembrable | `AppTest` verde |
| U1.4 | `ui/app.py`: dos secciones, Inicio por defecto, marco común | `AppTest` verde |
| U1.5 | Las nueve pantallas leen el caso abierto; título y caso de uso los pinta el marco | ninguna pantalla pide la ruta |
| U1.6 | Manual y guion; compuerta GU1a (C3); CP‑07 en Med (GU1b) | **GU1a** (C3) · **GU1b** (Med) |
| U2 | Asistente de cinco pasos. **Solo si CP‑07 resulta FALLA**; su alcance lo fijan los puntos de detención registrados | GU2 |
| U3 | Pulido de navegación y redacción. **Requiere decisión expresa de Eugenio** | — |

## Enfoques B y C: qué son y cuándo se activan

Fuente única: 2026-09-23-ui-recorrido-guiado-design.md §3.7 y
§7.

- **B — asistente de cinco pasos (fase U2).** Un asistente paso a paso —retoma la motivación de
  Eugenio del 2026‑09‑22 («llevar al usuario de la mano»)— apoyado en el caso abierto, el marco y
  los recorridos que construye A (por eso A va primero: un asistente escrito antes que el caso
  abierto tendría que inventárselo). **Se ejecuta solo si CP‑07 resulta FALLA**, y su alcance
  —cuáles son los cinco pasos y qué los compone— lo fijan los puntos de detención registrados en
  CP‑07, no se decide antes de medir. Compuerta GU2: las de GU1a y GU1b más
  `ui/paginas/componer.py` sin cambios salvo extracción de fragmentos.
- **C — pulido de navegación y redacción (fase U3).** Pulido de navegación y redacción de la interfaz
  (incluida la ortografía con tildes de los rótulos, que U1 deja sin tildes por coherencia — Global
  Constraints del plan detallado, no de la spec). **Requiere decisión expresa de Eugenio**,
  cualquiera sea el resultado de CP‑07.

B y C son una secuencia, no un compromiso: si CP‑07 resulta PASA, U2 no se ejecuta.

## Compuertas

- **GU0:** requisitos escritos; CP‑07 redactado antes de ejecutarse; documentos sin contradicción
  interna; aprobación de los cuatro encargos de revisión.
- **GU1a** (U1 completa sin CP‑07; se cruza con GC3 del cierre): línea base en 1 586,61 USD y 7 de
  7; suite verde en Windows y Linux; salvaguarda de aislamiento activa; `core/` cambia **solo** por
  los dos commits que autoriza la fila C3 de la spec de cierre
  (§5): el de INV‑080 (en
  `core/budget/`) y el de INV‑015 7a (tabla `descarte_version` y `descartar_version`), verificados
  como en la Tarea 18, paso 3, del plan de C3; aprobación de los cuatro encargos.
- **GU1b** (en Med): **CP‑07 ejecutado y registrado** (PASA o FALLA: ambos cierran GU1b; FALLA
  abre U2).
- **GU2:** ídem GU1a y GU1b, más `ui/paginas/componer.py` sin cambios salvo extracción de
  fragmentos.

GU1 se partió en GU1a y GU1b por la enmienda de la spec de cierre (§5 y §10, 2026‑09‑23 y
2026‑09‑24).

Cada compuerta se anota en [docs/bitacora/2026-09-23-sprint-ui.md](docs/bitacora/2026-09-23-sprint-ui.md).
