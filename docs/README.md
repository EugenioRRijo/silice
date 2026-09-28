# Documentación

Índice de la documentación del repositorio. El estado de cada documento se dice aquí en una
palabra; las cifras y los estados de los requisitos no se repiten: viven en su fuente única
([metodologia.md §5.1](metodologia.md#5-dry)).

## Documentos del producto

| Documento | Estado | Sesión que lo completa |
|---|---|---|
| [../CLAUDE.md](../CLAUDE.md) — constitución del proyecto | completo | — |
| [metodologia.md](metodologia.md) — Scrum‑Cascada, DRY, fuentes únicas e indicadores | completo | se actualiza por fase |
| [linea_base.md](linea_base.md) — el caso didáctico auditado y sus siete inconsistencias | completo | — |
| [ERS.md](ERS.md) — Especificación de Requerimientos de Software (IEEE 830) | completo, pendiente de revisión del tutor (G0) | 0.1 ✔; extensiones P0.1 y U0.1 |
| [modelo_datos.md](modelo_datos.md) — modelo entidad‑relación | completo, pendiente de revisión del tutor (G0) | 0.2 ✔ |
| [arquitectura.md](arquitectura.md) — vistas 4+1 de Kruchten | completo, pendiente de revisión del tutor (G0) | 0.3 ✔ |
| [plan_pruebas.md](plan_pruebas.md) — plan IEEE 829: RF → prueba → estado (§8), RNF (§9) y registro de la ejecución con su corrida de CI (§10) | vigente | F.2 ✔; fase C4 del cierre |
| [calidad_iso25010.md](calidad_iso25010.md) — evaluación ISO/IEC 25010 | vigente; RNF‑04 y RNF‑10 por medir en Med | F.2 ✔; fase C4 del cierre |
| [guion_prueba_arenia.md](guion_prueba_arenia.md) — guion de prueba manual, casos CP‑01 a CP‑07 | vigente; CP‑07 se ejecuta en Med (GU1b) | P4.2 ✔; U0.2 |
| [manual_usuario.md](manual_usuario.md), [manual_tecnico.md](manual_tecnico.md) — operación y extensión (guía del adaptador nuevo) | vigentes | F.3 ✔; fase C4 del cierre |
| [protocolo_precios.md](protocolo_precios.md) — obtención y registro de precios por dominio | vigente | M0.1 |
| [resultados_ml.md](resultados_ml.md) — métricas del módulo predictivo y compuerta G2 | completo, regenerado por la CI | I6.3 ✔; M4.1 |
| [api.json](api.json) — esquema OpenAPI exportado | completo, regenerado por la CI | F.1 ✔ |

## Compuertas, auditoría y mediciones

| Documento | Estado | Sesión que lo completa |
|---|---|---|
| [dossier_g0.md](dossier_g0.md) — decisiones D1–D9 para el tutor e instrumento del anexo A (RNF‑04 y RNF‑10) | listo para la reunión de G0 | post‑PLAN; D9 en P0.1 |
| [auditoria/2026-09-inventario.md](auditoria/2026-09-inventario.md) — inventario de hallazgos del cierre (una fila por hallazgo, con fase y estado) | vivo | C0 del cierre; se actualiza por fase |
| [protocolo_indicador3.md](protocolo_indicador3.md) — medición del indicador 3 (tiempo frente al método manual) | listo para Med | C4 del cierre |
| [protocolo_rnf04.md](protocolo_rnf04.md) — juicio de expertos sobre el informe de auditoría (RNF‑04) | listo para Med | C4 del cierre |
| [bitacora/](bitacora/) — una entrada por sprint, con decisiones y compuertas | en curso | cada sesión |

## Tesis

| Documento | Estado | Sesión que lo completa |
|---|---|---|
| [tesis/esqueleto_tesis.md](tesis/esqueleto_tesis.md) — capítulos y matriz de trazabilidad | completo | se actualiza por fase |
| [tesis/plan_redaccion.md](tesis/plan_redaccion.md) — guion por capítulo, cifras citables y convenciones | vigente | post‑PLAN; enmendado en C4 |
| [tesis/capitulos/README.md](tesis/capitulos/README.md) — índice y estado de los capítulos + resumen del proyecto | en curso | cada sesión de redacción |
| [tesis/referencias.md](tesis/referencias.md) — lista única de referencias (APA 7), con el estado de verificación de cada entrada | en curso | sprint R1 |
| [tesis/rubrica_tutor.md](tesis/rubrica_tutor.md) — lista de cotejo T1–T14 del revisor en rol de tutor | completo | sprint R1 |
| [tesis/revisiones/](tesis/revisiones/) — actas de revisión por capítulo y paquete para el tutor | en curso | cada revisión |

## Planes

| Plan | Estado |
|---|---|
| [../PLAN_DESARROLLO.md](../PLAN_DESARROLLO.md) — las 20 sesiones del desarrollo | completo (20 de 20) |
| [../PLAN_MULTIDOMINIO.md](../PLAN_MULTIDOMINIO.md) — catálogos y precios publicados para telecom, industrial y sistemas (M0–M4, GM1–GM4) | completo (11 de 11) |
| [../PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md) — prototipo AREN.IA: componer una partida a mano (P0–P5) | completo (12 de 12 metas) |
| [../PLAN_UI.md](../PLAN_UI.md) — recorrido guiado de la interfaz (U0–U3) | U0 y U1 hechas (GU1a cruzada); GU1b en Med; U2 y U3 condicionales |
| [../PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md) — asistente de presupuestos con IA (UC‑09) | fuera del límite de la tesis: trabajo futuro |
| [../PLAN_CIERRE.md](../PLAN_CIERRE.md) — el final de la tesis (C0–C4, Med, Red) | en curso |

Los diseños (`superpowers/specs/`) y los planes detallados (`superpowers/plans/`) de cada sprint
están en [superpowers/](superpowers/); registran lo que se decidió en su fecha y no se reescriben.

## Fuentes (`fuentes/`)

Cada archivo de [fuentes/](fuentes/) tiene su ficha en [fuentes/README.md](fuentes/README.md)
(procedencia y uso; lo vigila la meta P2 de `scripts/meta_prototipo.py`). La evidencia primaria del
caso de estudio está en [`../data/linea_base/APUS_CLINICA.pdf`](../data/linea_base/APUS_CLINICA.pdf).
