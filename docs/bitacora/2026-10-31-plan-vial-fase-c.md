# Plan vial, fase C: riesgo y mejora de la estimación (Tareas 12 a 16)

Rama `inc/vial-agregados` (worktree `.worktrees/s2madm`). La fase B se cerró en 625ee9de. Las decisiones tomadas en
ausencia de Eugenio están en `docs/bitacora/2026-10-30-preguntas-para-eugenio.md`, de la fila 73 en adelante.

| Tarea | Commits | Árbitro |
|---|---|---|
| 12 Series viales y su mapa a insumos | 0effc269, a139bd28 | aprobada r1 |
| 13 Proyección del riesgo | 841e59f3, 0e2ca161 | aprobada r1 |

## Menores y avisos para las tareas siguientes

- T12 → T13: `historia_mensual` con `hasta` a mitad de mes da un último mes parcial (fila 75). La proyección pasa
  `hasta` a fin de mes.
- T12 → T13: el PPI de asfalto (unidad `indice`) se usa solo por su variación mensual, nunca como precio. Solo lo
  protegen el nombre y la unidad.
- T12 → T13: la muestra no trae la tasa BCV de esos 36 meses. Las pruebas de la proyección siembran una tasa ficticia.
- T13 → T16 (fila 79): falta una función en `aplicacion/` (no en la ruta) que saque del cálculo publicado de la
  Tarea 4 la receta, el costo de planta por tonelada y `precio_de_componente` en la moneda del presupuesto. El cálculo
  guarda sus cifras en su moneda, con la tasa del cierre.
- T13 → T16: `proyectar` compara exacto contra el total del presupuesto. Hay que pasarle un `Presupuesto` recalculado
  con el motor, nunca un total guardado ya redondeado.

## Menores para el cierre de la fase C

- Línea del CHANGELOG de las Tareas 12 y 13.
- Fila 81. **Decisión del orquestador** sobre la recomendación del árbitro de la T13: un insumo con el mismo nombre y
  dos precios ya no niega la proyección. Se desdobla en variantes locales («Flete [2]»), sin tocar `core/`, cada una con
  el factor de su serie. Se declara en los supuestos y la contribución se agrupa por el nombre original.
- `proyeccion.py:370`: los meses completos se cuentan solo con las series de insumos y componentes presentes en el
  presupuesto. Hoy, una entrada vieja del mapa baja los meses o niega la proyección.
- Anotados sin cambio:
  - Dos pruebas de la tasa de la T13 entraron con el feat, sin rojo propio. El árbitro las verificó por mutación y
    las dos discriminan.
  - El asunto del commit verde no es el del plan.
  - Rendimiento medido por el árbitro: 18 renglones, 43 insumos y 2.000 trayectorias tardan unos 4 s. Escala lineal.
