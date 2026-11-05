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
| Claude | Ajuste de menores de T5 y T6 («Presupuesto» en el conmutador, los 4 de Opus, `ABSORBIDAS`, textos de Entregar) | 2026-11-05 |
| Antigravity (Gemini 4 Argon) | **Sin cuota por ~6,6 días** desde el 2026-11-04 | — |
| Antigravity (Gemini 3.8 Flash) | Disponible: arbitra tareas chicas con encargo acotado y redacta textos | — |
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
| T4 Producción, Auditoría, Precios | subagente `silice-frontend` | `d0befe7f` (96 pruebas fallan: rutas y enlaces viejos) | `95534d73` (2.962/2.962 en marco, shell, paginas y comun; lint 0) | [Ronda 1 (Argon): APROBADO, 1 menor para T9](arbitrajes/f6-T4-r1.md) | Nota: el verde cambió 3 pruebas de T2/T3 que fijaban el mapa viejo (`/empresa/precios`). Pendiente para T9: `scripts/recorrido_ux_playwright.py:763,768,1749`. `main` (con #102) unido después: `44331ebb` | ✔ |
| T7 Cartera por moneda (servidor) | Pruebas: **Antigravity (Claude Opus 5.5 High)**. Implementación: subagente `silice-backend` (Antigravity quedó sin cuota). Lo arbitra Argon | `ffee9b5f` en `feature/f6-t7-cartera` (12 pruebas escritas por Antigravity; las 12 fallan con 404) | `818d6dd0` (12/12; suite de API 2.654/2.654; `core/` intacto; pruebas de Antigravity sin tocar) | [Ronda 1 (Flash): APROBADO, sin hallazgos](arbitrajes/f6-T7-r1.md) — arbitraje ligero, sin Argon | De acuerdo con reservas; la suma por moneda se vuelve a mirar en T8 con datos de la Vista general | ✔ (unida a `feature/f6-espacios` en `d30af3d2`) |
| T5 Obra y barra lateral (cierre A) | subagente `silice-frontend` | `c0edbfff` (156 fallan: sin lista de obras, sin barra de la obra, sin subvistas) | `5fa8f3fa` (suite completa del front 3.871/3.871; lint y build limpios) | [Flash: APROBADO, sin hallazgos](arbitrajes/f6-T5-flash.md) · [Opus: APROBADO, 4 menores](arbitrajes/f6-T5-opus.md) | En vivo (Chromium, 1366×768, ana): 9 secciones, conmutador «Partidas \| Componer», 1 h1, sin desplazamiento horizontal. Las partidas empiezan a 1.003 px (Normal) y 1.663 px (Muy grande): la causa principal es la cabecera de la página Presupuesto, que ya venía de F4; F6 suma ~50 px. Hallazgo de diseño: dos «Partidas» (conmutador y pestaña de abajo): Eugenio decidió que el conmutador diga «Presupuesto». Los 4 menores de Opus van al ajuste tras T6 | ✔ |
| T6 Cuenta | subagente `silice-frontend` | `e5779b9b` (la Cuenta, la barra superior sin migas y salir sin 401) | `dbff51ac` (suite completa del front 3.941/3.941 en 255 archivos, corrida el 2026-11-05; lint 0) | [Flash: APROBADO, sin hallazgos](arbitrajes/f6-T6-flash.md) | De acuerdo. Claude revisó las dos pruebas cambiadas en el verde (`estilosLetra.test.ts` sustituye la raya que T6 quita por la de la persona activa; `busqueda.test.ts` suma un caso de Carpetas sin `cambiar_caso`): ninguna se debilita | ✔ |
| T8 Vista general | — | — | — | — | — | pendiente |
| T9 Cierre (cierre B) | — | — | — | — | — | pendiente |


## Arbitraje sin Argon (decisión de Eugenio, 2026-11-04)

Argon no tiene cuota hasta ~6,6 días después del 2026-11-04. Mientras tanto:
- **Tareas chicas** (T6 y ajustes): Flash, con encargo acotado al diff y solo comandos git.
- **T5 y T8**: Flash y Opus (dentro de Antigravity), cada uno por separado; Opus es de la misma familia que el
  constructor, así que su veredicto se anota como menos independiente.
- **Cierre de F6 (T9)**: Argon, cuando vuelva, sobre la rama entera, antes de que Eugenio pruebe y fusione.
- Las pruebas siempre las corre Claude, y cada hallazgo se verifica contra el código.

## Decisiones de Eugenio que gobiernan F6 (2026-11-04)

Cartera por moneda; subvistas de obra; español llano; tamaño de letra solo en la Cuenta; entrada por la Vista general;
Riesgo como sección propia; quien revisa ve solo la carpeta abierta; al cambiar de obra se abre su Resumen; rama desde
`main`. Detalle en el plan.
