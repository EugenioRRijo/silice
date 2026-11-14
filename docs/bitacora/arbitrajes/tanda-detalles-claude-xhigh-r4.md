# Tanda de detalles · Ronda 4 (breve) · Árbitro de Claude, esfuerzo xhigh (2026-11-06): APROBADO

> Delta `9f79eb28..f5858781`. Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: APROBADO.** Sin BLOQUEANTE ni MAYOR. A–F de la ronda 3 resueltos; seis MENOR nuevos (cinco del delta y uno
anterior a la tanda). Recomienda N2, N3 y N5 antes del PR; N1, N4 y N6 pueden ir a F8.

| | Estado | Evidencia |
|---|---|---|
| A | RESUELTO (residuo en N1) | resúmenes reales de tramo, punto con especificaciones, nombre con «; » y origen con referencia; la prueba de contrato `comun/rotulosDeColumna.test.ts` mata 5 de 5 mutaciones del Python |
| B | RESUELTO | la partida elegida pone siempre su descripción y su unidad; cuerpo enviado `{"codigo":"FIC-02","descripcion":"Relleno compactado ficticio","unidad":"m3"}`; aviso «Se cambió la descripción…» en el panel |
| C | RESUELTO para la cabecera | «Usar «FIC-03» como código» vacía descripción y unidad y trae las tablas de FIC-03 |
| D | RESUELTO | un mutante sin la limpieza hace caer su prueba |
| E | RESUELTO | `comun/rotuloDeOrigen.ts`; trinquete `comun/arquitectura.test.ts:91-100` |
| F | RESUELTO | 14 mensajes «en este caso»; título D1–D17 |

## Nuevos (MENOR)
- **N1.** El presentador elige la primera coincidencia de una columna posterior: un nombre «Toma; x=3» pone «Posición X
  (m)=3» cuando la X real es 2. Corrección: la secuencia que reconozca más columnas.
- **N2.** Cambiar los vértices de un tramo existente sale con punto («1.5,0,2.5; 1.5,0,0.6»), mientras el alta dice
  «(1,5; 0; 2,5), …». Corrección: `campo === "vertices"` → `verticesLegibles`.
- **N3.** El contrato no fija el orden real: el resumen sale en el orden de `filas_desde_espacio` y
  `tests/unit/test_hoja_rotulos.py:42-45` compara conjuntos. Corrección, solo prueba: `tuple(filas_desde_espacio(e)[t][0])
  == tuple(ROTULOS_DE_COLUMNA[t]) == COLUMNAS[t]`.
- **N4.** El aviso de B salta por diferencias que el servidor no ve (espacio final, «m³» frente a «m3»).
- **N5.** La regla «lo que puso el catálogo antes se reemplaza sin aviso» no tiene prueba (un mutante sigue en 29/29):
  falta el camino de elegir otra partida con Flecha abajo, sin teclear.
- **N6 (anterior a la tanda, `c3b0b9fe`).** FIC-02 con tablas y luego FIC-04 del catálogo sin composición deja la cabecera de
  FIC-04 con las tablas de FIC-02, sin aviso (`ComponerPartida.tsx:298` solo reemplaza las tablas si la partida trae
  filas); guardar dejaría a FIC-04 con la composición de FIC-02.

## Lógica nueva de r3-j, TDD y sin defecto
Esc de D16, precarga, foco (WCAG 2.4.3), parecidas, guardado y región viva (4.1.3) sin defecto con «vaciar y devolver».
Rojos `2fe21241` (8 fallan) y `44792ec2` (5 fallan) solo con pruebas y antes de su verde; los dos oráculos que tocó el verde
`182d2212` son más fuertes. Ningún archivo de Python de producción cambió; `core/` intacto; experimento congelado vigente;
CHANGELOG, ESTADO y DESIGN dicen la verdad.
