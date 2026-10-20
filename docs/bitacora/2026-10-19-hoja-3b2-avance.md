# Hoja 3b-2: avance y medición (pestañas Espacio, APU, Presupuesto y Plan en lectura)

**Fecha:** 2026-10-19/20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `bfb7267`

## Parejas prueba → implementación

| Pareja | Prueba (rojo visto) | Implementación |
|---|---|---|
| R5 Espacio y metrajes | `c56df7e` | `2102c6a` |
| R6 Presupuesto | `977b0a1` | `7c61d8f` |
| R7 APU | `c7e6256` | `28b35c9` |
| R8 Plan y curva | `b0066fb` | `828e413` |
| Acceso, no-store, float, caso, R17 y medición ampliados a R5-R8 | `f5b152d` (cobertura y guardia: pasan en la primera corrida porque R5-R8 ya existían; no hay código nuevo) | — |
| Front: cuatro pestañas | `aed4e7b`; corrección propia de las pruebas `d418108` | `28725f7` |

## Medición registrada (3b-B22 y 3b-B23; no afirma ningún tiempo)

Las cuatro vistas de la 3b-2 (R5 a R8) sobre los 500 puntos del generador determinista, mediana de cinco corridas
con una de calentamiento (`tests/unit/test_hoja_vistas_medicion.py`, `scripts/medir_rnf11.medir`), cada corrida
elaborando de nuevo (caché invalidada, R17 incluida): **0,157 a 0,200 s** en este equipo (dos corridas del
procedimiento). Umbral de referencia de RNF-11: 2 s. Tamaño estimado del borrador de 500 puntos: **236 737 bytes**
(el borrador trae un `mappingproxy` que `pickle` no serializa; se usa el recorrido de objetos).
Declarado: no incluye `abrir` por la API ni las vistas R9 a R11 (llegan en 3b-3, que completa la medición).

## Diferencias y límites declarados

- `solo_lectura_insumos` del APU es verdadero cuando el borrador no tiene versión abierta (el cambio de insumo
  exige versión, P:1522); el cambio de insumo mismo es de la 3c.
- Los textos que componen las vistas llevan tildes (ayuda, «Orígenes de medida», «Vértices de recorridos», vacíos); los que
  salen de `aplicacion/hoja.py` van idénticos a la clásica, sin tildes («+ Administracion», «Dia 1»); en pantalla
  la etiqueta de período se lee «Día 1» (`periodoLegible`).
- Tras ver la prueba en rojo se corrigieron expectativas propias de las pruebas del front (totales con el mismo
  exacto que el encabezado, «Día», cifras repetidas, estructura de Carbon: grupo y no radiogroup, «13,20 USD»); no se
  tocó el comportamiento.
- La columna fija (sticky) de las tablas anchas y el aviso «foco no oculto» (T11) quedan para la auditoría visual.
- Sin el enlace «Ver en Auditoría» (3b-F6b, de la 3b-3).
