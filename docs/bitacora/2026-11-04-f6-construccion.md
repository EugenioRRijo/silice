# F6 Espacios: seguimiento de la construcción

**Para Eugenio:** aquí se ve quién hace qué y en qué va cada tarea. Lo actualiza Claude (el orquestador) en cada paso.
Antigravity no trabaja solo: se activa cuando Claude lo llama (`agy -p`, solo lectura) o cuando Eugenio le habla en el
IDE. Sus veredictos se guardan **palabra por palabra** en [arbitrajes/](arbitrajes/).

**Plan:** [PLAN_REDISENO_F6.md](../planes/PLAN_REDISENO_F6.md) · **Rama:** `feature/f6-espacios` (worktree
`.worktrees/s2m3`) · **Contrato de rutas:** [aquí](../especificaciones/2026-11-04-f6a-contrato-de-rutas.md) ·
**Diseño visual:** [aquí](../especificaciones/2026-11-04-f6a-diseno-visual.md)

## Ahora mismo

| Quién | Qué hace | Desde |
|---|---|---|
| Subagente constructor | **T2: tabla de espacios y `primeraUsable`**, con TDD | 2026-11-04 |
| Claude | Espera a T2 para verificarla; vigila la CI del #102 | 2026-11-04 |
| Antigravity | En espera; arbitra T2 cuando Claude se la pase | — |

## Tareas

| Tarea | Construye | Rojo | Verde | Arbitraje de Antigravity | Veredicto de Claude sobre el arbitraje | Estado |
|---|---|---|---|---|---|---|
| Plan | Claude | — | — | [Ronda 1: DEVUELTO (4 mayores, 2 menores)](arbitrajes/f6-plan-r1.md) · [Ronda 2: APROBADO](arbitrajes/f6-plan-r2.md) | Los 6 hallazgos verificados contra el código y aplicados | ✔ |
| T0 Expediente | Claude (contrato y enmienda) + Antigravity (diseño visual y adenda) | — | — | [APROBADO con 3 menores](arbitrajes/f6-T0.md) | Las 3 verificadas y aplicadas en T5, T6 y T7 | ✔ **Aprobado por Eugenio** |
| T1 Ruta canónica | subagente `silice-frontend` | `177c9279` (falla: el recorrido no marca «Paso 1 de 3» en `/empresa/auditoria`; 7 archivos con rutas escritas a mano) | `545b3f36` (vitest 2.860/2.860 en marco, shell, paginas y comun; lint 0) | [Ronda 1: APROBADO, sin hallazgos](arbitrajes/f6-T1-r1.md) (revisión estática: en el worktree no pudo usar git ni vitest) | De acuerdo; las pruebas las corrió Claude. Desvíos aceptados: 4 enlaces pasan a su ruta canónica (mismo destino, sin redirección) y 2 enlaces más que el plan no listaba | ✔ |
| T2 Tabla de espacios | subagente `silice-frontend` | — | — | — | — | en curso |
| T3 BarraDeEspacio | — | — | — | — | — | pendiente |
| T4 Producción, Auditoría, Precios | — | — | — | — | — | pendiente |
| T7 Cartera por moneda (servidor) | — | — | — | — | — | pendiente |
| T5 Obra y barra lateral (cierre A) | — | — | — | — | — | pendiente |
| T6 Cuenta | — | — | — | — | — | pendiente |
| T8 Vista general | — | — | — | — | — | pendiente |
| T9 Cierre (cierre B) | — | — | — | — | — | pendiente |

## Decisiones de Eugenio que gobiernan F6 (2026-11-04)

Cartera por moneda; subvistas de obra; español llano; tamaño de letra solo en la Cuenta; entrada por la Vista general;
Riesgo como sección propia; quien revisa ve solo la carpeta abierta; al cambiar de obra se abre su Resumen; rama desde
`main`. Detalle en el plan.
