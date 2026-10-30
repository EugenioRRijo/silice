# Plan vial, fase A: decisiones de implementación

## Tarea 3: receta de la planta y consumos al producir mezcla

- **Componente propio solo en toneladas.** Un componente `propio` sale del inventario de la arenera,
  que mueve toneladas o m3; los litros (gasoil, aditivos) solo pueden ser `comprado`. Una receta con
  un propio en litros se rechaza.
- **`TOLERANCIA_MASA` en el registro de `produccion/fuentes.py`**, no en la `Constante` de
  `adapters/espacio/especialidades` que nombra el plan: RT-7 (`tests/unit/test_arquitectura.py:235`)
  prohíbe que `produccion/` importe `adapters/`. Es 0,02 t por t de mezcla, «supuesto declarado» que
  la empresa debe confirmar con su dosificación real.
- **Bajar `ins_0007_prod_receta` borra los movimientos `consumo`**, porque el `CHECK` anterior no los
  admite. Es lo que hacen todas las bajadas del repositorio (DA-S5-6): el downgrade nunca se ofrece
  al usuario, solo existe para las pruebas y el ensayo de migraciones.
- **Una sola regla de cuantización t a unidad de venta** (`produccion.inventario.de_toneladas`): en m3
  es toneladas / densidad con cuatro decimales y redondeo de mitad al par (`ROUND_HALF_EVEN`), la
  que ya usaba la importación de báscula; ahora la reutiliza (`_cantidad_de_despacho`). Oráculo a
  mano: 100 t de mezcla × 0,94 con agregado propio en m3 de densidad 1,7 consume 94 / 1,7 =
  55,29411... = 55,2941 m3. Sin densidad (o no positiva) es error que nombra el material.
- Una receta admite como máximo 50 componentes (422 si trae más).
