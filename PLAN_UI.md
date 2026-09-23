# PLAN_UI — recorrido guiado de la interfaz

Continúa a [PLAN_PROTOTIPO.md](PLAN_PROTOTIPO.md), que cerró 12 de 12 metas, y **no** reemplaza a
[PLAN_ASISTENTE.md](PLAN_ASISTENTE.md): el asistente con IA (UC‑09) sigue siendo otro plan.

**Diseño que lo fundamenta:**
[docs/superpowers/specs/2026-09-23-ui-recorrido-guiado-design.md](docs/superpowers/specs/2026-09-23-ui-recorrido-guiado-design.md).
**Plan detallado (tarea por tarea):**
[docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md](docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md).

**Por qué existe.** La interfaz tiene nueve pantallas que funcionan y ninguna puerta de entrada.
Frase de origen (Eugenio, 2026‑09‑22): «no sé qué hacer y no hay un camino para llevar al usuario de
la mano». Este plan no agrega capacidades: agrega **orientación**.

**Dependencia dura.** U1 no empieza hasta que el PR #7 esté auditado y fusionado en `main`.

## Sesiones

| Sesión | Contenido | Cierre |
|---|---|---|
| U0.1 | ERS: UC‑12, RF‑36…RF‑43, actor «usuario nuevo / evaluador», RNF‑10, enmienda de la reserva de RF‑32 | ERS sin contradicción interna |
| U0.2 | RNF‑10 en calidad y plan de pruebas; bloque B del anexo A; CP‑07 redactado antes de ejecutarse; `streamlit>=1.36` | **GU0** |
| U1.1 | Reasentar sobre `main`; salvaguarda de aislamiento de `data/apu.db` | salvaguarda observada en rojo y en verde |
| U1.2 | `ui/recorridos.py` y `ui/caso.py` | pruebas puras verdes |
| U1.3 | Pantalla de Inicio con estado vacío sembrable | `AppTest` verde |
| U1.4 | `ui/app.py`: dos secciones, Inicio por defecto, marco común | `AppTest` verde |
| U1.5 | Las nueve pantallas leen el caso abierto; título y caso de uso los pinta el marco | ninguna pantalla pide la ruta |
| U1.6 | Manual y guion al día; compuerta automatizada; CP‑07 con dos personas | **GU1** |
| U2 | Asistente de cinco pasos. **Solo si CP‑07 resulta FALLA**; su alcance lo fijan los puntos de detención registrados | GU2 |
| U3 | Pulido de navegación y redacción. **Requiere decisión expresa de Eugenio** | — |

## Compuertas

- **GU0:** requisitos escritos; CP‑07 redactado antes de ejecutarse; documentos sin contradicción
  interna; aprobación de los cuatro encargos de revisión.
- **GU1:** línea base en 1 586,61 USD y 7 de 7; suite verde en Windows y Linux; salvaguarda de
  aislamiento activa; `git diff --stat main -- core/` vacío; aprobación de los cuatro encargos;
  **CP‑07 ejecutado y registrado** (PASA o FALLA: ambos cierran GU1; FALLA abre U2).
- **GU2:** ídem GU1, más `ui/paginas/componer.py` sin cambios salvo extracción de fragmentos.

Cada compuerta se anota en [docs/bitacora/2026-09-23-sprint-ui.md](docs/bitacora/2026-09-23-sprint-ui.md).
