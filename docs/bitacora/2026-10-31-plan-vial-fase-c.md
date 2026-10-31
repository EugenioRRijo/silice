# Plan vial, fase C: riesgo y mejora de la estimación (Tareas 12 a 16)

Rama `inc/vial-agregados` (worktree `.worktrees/s2madm`). La fase B se cerró en 625ee9de. Las decisiones tomadas en
ausencia de Eugenio están en `docs/bitacora/2026-10-30-preguntas-para-eugenio.md`, de la fila 73 en adelante.

| Tarea | Commits | Árbitro |
|---|---|---|
| 12 Series viales y su mapa a insumos | 0effc269, a139bd28 | aprobada r1 |

## Menores y avisos para las tareas siguientes

- T12 → T13: `historia_mensual` con `hasta` a mitad de mes da un último mes parcial (fila 75). La proyección pasa
  `hasta` a fin de mes.
- T12 → T13: el PPI de asfalto (unidad `indice`) se usa solo por su variación mensual, nunca como precio. Solo lo
  protegen el nombre y la unidad.
- T12 → T13: la muestra no trae la tasa BCV de esos 36 meses. Las pruebas de la proyección siembran una tasa ficticia.
