# Hallazgo VB-1 (bloqueante): el paquete que Entregar genera y firma no se puede revisar (decision de Eugenio / tutor)

**Detectado por:** auditoria visual del bloque B (tesis-b9), reproducido aparte. Informe: `docs/bitacora/2026-10-19-auditoria-visual-bloque-b.md`
(commit `9efba7d`, rama `inc/ruta-s2-mig-final-b`).

## Que pasa
Entregar un presupuesto de DEMO-001 genera y firma un `.silice`; al subirlo a Revisar responde **422**
«renglon 0.equipos: cifra fuera del patron estricto: '0.0833…'».

## Causa raiz
`PATRON_CIFRA = ^-?[0-9]{1,20}(\.[0-9]{1,28})?$` (`core/budget/canonico.py:72` y `seguridad/json_estricto.py:22`) admite a lo
sumo 28 decimales, pero un `Decimal` menor que 1 con precision de 28 digitos significativos (p. ej. `Decimal(1)/Decimal(12)` =
`0.08333333333333333333333333333`) tiene 29 decimales. El exportador (`texto_decimal`, `canonico.py:220`) lo escribe y el
importador lo rechaza. Afecta a cualquier equipo cuyo costo o rendimiento no termine en decimales finitos.

## Por que no se arregla aqui
`canonico.py` esta en `core/` y `json_estricto` es un modulo de seguridad: NORMAS §9 (regla que evita el 80 % de los problemas)
exige documentar el hallazgo y no parchear el nucleo, y el cambio necesita expediente de `core` y aval del tutor.

## Opciones (no ejecutadas)
- **(a)** Cuantizar a 28 decimales al exportar (`texto_decimal`): cambia lo que se firma; los paquetes ya firmados siguen igual.
- **(b)** Ensanchar el patron a 29 o mas decimales en los dos sitios: acepta mas, pero cambia una guardia de seguridad.
- En ambos casos: prueba de ida y vuelta exportar -> importar con `1/12` y similares, expediente de `core` y aval del tutor.

## Ruling del orquestador
No se toca `core/` ni `seguridad/`. Queda **bloqueante para la fusion a `main`** de la funcion Entregar -> Revisar y para cualquier demo
que entregue equipos con costos fraccionarios. Decision pendiente de Eugenio y del tutor.
