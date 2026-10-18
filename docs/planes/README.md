# DIRECTORIO DE PLANES MAESTROS Y MANUALES DE ORQUESTACIÓN
## Sílice: Estimación y Auditoría de Presupuestos Multiespecialidad

Este directorio centraliza los planes estratégicos, especificaciones de arquitectura y manuales de orquestación desarrollados para la evolución y cierre técnico de Sílice.

---

## 📑 Índice de Planes y Documentos

| Archivo | Descripción | Estado |
|---|---|---|
| [**RUTA_SESIONES.md**](./RUTA_SESIONES.md) | **Fuente única del orden de trabajo**: sesiones 0–6, subagentes con su modelo (Opus, Sonnet, Haiku) y esfuerzo por tarea, protocolo de cada sesión, decisiones RS-x de Eugenio y rulings técnicos RT-x. | ✅ **Vigente (2026-10-18)** |
| [**PLAN_SESION_1_ASISTENTE.md**](./PLAN_SESION_1_ASISTENTE.md) | Plan detallado de la sesión 1: deudas del asistente de IA (RF-100, clave de IA tras reiniciar, pruebas pendientes, informe del experimento). | ✅ **Vigente** |
| [**PLAN_FUENTES_DATOS_CANTERA.md**](./PLAN_FUENTES_DATOS_CANTERA.md) | Estado de cada cifra y fórmula de cantera (VERIFICADO, DATO DE LA EMPRESA, A COTEJAR, CONSTRUIDO, A MEDIR, SIN FUENTE) y datos que debe aportar la empresa. | ✅ **Vigente** |
| [**MANUAL_MAESTRO_OPTIMIZACION_ORQUESTADOR.md**](./MANUAL_MAESTRO_OPTIMIZACION_ORQUESTADOR.md) | Manual canónico para el Orquestador Claude y los subagentes. Define la arquitectura global, los estándares obligatorios de UI (**IBM Carbon** + **SAP Fiori** + **IBCS**), la matriz de asignación de tareas concurrentes y el protocolo de calidad. | ✅ **Vigente / Ratificado** |
| [**PLAN_GESTOR_PRODUCCION_Y_AUDITORIA_VISUAL.md**](./PLAN_GESTOR_PRODUCCION_Y_AUDITORIA_VISUAL.md) | Plan arquitectónico y técnico detallado para integrar el **Gestor de Producción de Áridos y Canteras** (costos horarios Caterpillar/USBR, balance de masa en trituración, básculas camioneras) y la **Auditoría Visual Interactiva** (Univer Canvas Grid, parser dual de Excel y parches Delta inmutables) sobre **Tauri v2**. Sus enmiendas del 2026-10-18 (§0) prevalecen. | ✅ **Vigente con enmiendas §0** |
| [**PLAN_IMPLEMENTACION_CIERRE_1.0.0.md**](./PLAN_IMPLEMENTACION_CIERRE_1.0.0.md) | Plan de cierre y certificación de la versión 1.0.0 de Sílice bajo metodologías Scrum, Cascada, SOLID y DRY. Detalla las tareas para completar la meta única, pruebas pendientes de la 0.7.0 a 1.5 y corrección del flujo CI. | 🏁 **Completado** |
| [**INFORME_AUDITORIA_ENTREGA_1.0.0.md**](./INFORME_AUDITORIA_ENTREGA_1.0.0.md) | Dictamen formal de auditoría y balance de entrega del release 1.0.0: verificación de metas S0 a S5, inventario de artefactos, cumplimiento normativo y trazabilidad pericial. | 🏁 **Entregado** |

---

## 🛠️ Skills Vinculadas en `.agents/skills/`

Los planes anteriores se apoyan en las 8 skills operativas configuradas en el proyecto. Cada una la usa un subagente con ficha propia en [`.claude/agents/`](../../.claude/agents/) (modelo y esfuerzo en la [ruta §3](./RUTA_SESIONES.md#3-subagentes-modelo-y-esfuerzo)); la skill tiene una sola copia, aquí:
* [`front-carbon-fiori-ibcs`](../../.agents/skills/front-carbon-fiori-ibcs/SKILL.md): Frontend desktop (Carbon, Fiori, IBCS).
* [`back-clean-arch`](../../.agents/skills/back-clean-arch/SKILL.md): Backend FastAPI, Named Pipes y protección de `core/`.
* [`pruebas-cobertura`](../../.agents/skills/pruebas-cobertura/SKILL.md): Rigor de pruebas, pytest `-W error` y RNF-06.
* [`base-datos-migraciones`](../../.agents/skills/base-datos-migraciones/SKILL.md): SQLite multi-caso y migraciones Alembic.
* [`asistente-ia`](../../.agents/skills/asistente-ia/SKILL.md): Claude, Ollama offline, keyring y Isolation Forest.
* [`replicacion-excel`](../../.agents/skills/replicacion-excel/SKILL.md): Extracción dual y réplica en Canvas Univer.
* [`auditoria-forense`](../../.agents/skills/auditoria-forense/SKILL.md): Reglas forenses y parches Delta inmutables.
* [`gestor-produccion-aridos`](../../.agents/skills/gestor-produccion-aridos/SKILL.md): Canteras, maquinaria pesada y básculas camioneras.
