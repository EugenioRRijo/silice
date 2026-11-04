# F6 Espacios: seguimiento de la construcción

**Para Eugenio:** aquí se ve quién hace qué y en qué va cada tarea. Lo actualiza Claude (el orquestador) en cada paso.
Antigravity no trabaja solo: se activa cuando Claude lo llama (`agy -p`, solo lectura) o cuando Eugenio le habla en el
IDE. Para construir usa el modelo Claude Opus 5.5 High y para arbitrar, Gemini 4 Argon High (`agy -p --model …`). Como no
puede escribir ni hacer commits (sus permisos siguen en solo lectura), devuelve el código y Claude lo aplica. Sus veredictos se guardan **palabra por palabra** en [arbitrajes/](arbitrajes/).

**Plan:** [PLAN_REDISENO_F6.md](../planes/PLAN_REDISENO_F6.md) · **Rama:** `feature/f6-espacios` (worktree
`.worktrees/s2m3`) · **Contrato de rutas:** [aquí](../especificaciones/2026-11-04-f6a-contrato-de-rutas.md) ·
**Diseño visual:** [aquí](../especificaciones/2026-11-04-f6a-diseno-visual.md)

## Ahora mismo

| Quién | Qué hace | Desde |
|---|---|---|
| Antigravity (Gemini 4 Argon High) | **Arbitrando T4** (`4078c439..95534d73`) | 2026-11-04 |
| Subagente `silice-backend` | T7: implementación de la cartera por moneda contra las 12 pruebas que escribió Antigravity (no las toca) | 2026-11-04 |
| Antigravity (Claude Opus/Sonnet) | **Sin cuota** hasta ~4 h 25 min después de las 16:20 del 2026-11-04 (`Individual quota reached`). Por eso T7 la termina el subagente (decisión de Eugenio) | — |
| Claude | Verifica cada entrega y vigila la CI del #102 | 2026-11-04 |

## Tareas

| Tarea | Construye | Rojo | Verde | Arbitraje de Antigravity | Veredicto de Claude sobre el arbitraje | Estado |
|---|---|---|---|---|---|---|
| Plan | Claude | — | — | [Ronda 1: DEVUELTO (4 mayores, 2 menores)](arbitrajes/f6-plan-r1.md) · [Ronda 2: APROBADO](arbitrajes/f6-plan-r2.md) | Los 6 hallazgos verificados contra el código y aplicados | ✔ |
| T0 Expediente | Claude (contrato y enmienda) + Antigravity (diseño visual y adenda) | — | — | [APROBADO con 3 menores](arbitrajes/f6-T0.md) | Las 3 verificadas y aplicadas en T5, T6 y T7 | ✔ **Aprobado por Eugenio** |
| T1 Ruta canónica | subagente `silice-frontend` | `177c9279` (falla: el recorrido no marca «Paso 1 de 3» en `/empresa/auditoria`; 7 archivos con rutas escritas a mano) | `545b3f36` (vitest 2.860/2.860 en marco, shell, paginas y comun; lint 0) | [Ronda 1: APROBADO, sin hallazgos](arbitrajes/f6-T1-r1.md) (revisión estática: en el worktree no pudo usar git ni vitest) | De acuerdo; las pruebas las corrió Claude. Desvíos aceptados: 4 enlaces pasan a su ruta canónica (mismo destino, sin redirección) y 2 enlaces más que el plan no listaba | ✔ |
| T2 Tabla de espacios | subagente `silice-frontend` | `aa0a71a0` (6 fallan: `ESPACIOS` no existe, `sueltas` traía 18) | `48d65a34` (541/541 en marco y shell; lint 0) | [Ronda 1 (Argon): APROBADO, sin hallazgos](arbitrajes/f6-T2-r1.md) | De acuerdo. Claude corrió 66/66 pruebas clave. Carpetas: la exigencia de `cambiar_caso` queda para T6 (contrato §3) | ✔ |
| T3 BarraDeEspacio | subagente `silice-frontend` | `67eb8819` (no existía el módulo ni el SCSS) | `0ef1d32f` (339/339 en marco; lint 0) | [Ronda 1 (Argon): APROBADO, sin hallazgos; contraste WCAG AA de 12 pares, el menor 3,79:1](arbitrajes/f6-T3-r1.md) | De acuerdo. Pendiente para T5: la regla `.silice-barra-espacio--subvista + .silice-pagina` de `hoja.scss` (diseño §A.4) | ✔ |
| T4 Producción, Auditoría, Precios | subagente `silice-frontend` | `d0befe7f` (96 pruebas fallan: rutas y enlaces viejos) | `95534d73` (2.962/2.962 en marco, shell, paginas y comun; lint 0) | en curso | Nota: el verde cambió 3 pruebas de T2/T3 que fijaban el mapa viejo (`/empresa/precios`). Pendiente para T9: `scripts/recorrido_ux_playwright.py:763,768,1749`. `main` (con #102) unido después: `44331ebb` | arbitraje |
| T7 Cartera por moneda (servidor) | Pruebas: **Antigravity (Claude Opus 5.5 High)**. Implementación: subagente `silice-backend` (Antigravity quedó sin cuota). Lo arbitra Argon | `ffee9b5f` en `feature/f6-t7-cartera` (12 pruebas escritas por Antigravity; las 12 fallan con 404) | — | — | — | en curso (implementación por el subagente) |
| T5 Obra y barra lateral (cierre A) | — | — | — | — | — | pendiente |
| T6 Cuenta | — | — | — | — | — | pendiente |
| T8 Vista general | — | — | — | — | — | pendiente |
| T9 Cierre (cierre B) | — | — | — | — | — | pendiente |

## Decisiones de Eugenio que gobiernan F6 (2026-11-04)

Cartera por moneda; subvistas de obra; español llano; tamaño de letra solo en la Cuenta; entrada por la Vista general;
Riesgo como sección propia; quien revisa ve solo la carpeta abierta; al cambiar de obra se abre su Resumen; rama desde
`main`. Detalle en el plan.
