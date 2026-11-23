# Norma de interfaz de Sílice (2026-11-23)

> Pedido de Eugenio: «vamos a hacer lo mismo que core y buscar una ui ux, front que sea amigable para el usuario y dejarlo
> guardado en una guardia en la CI». Plan F0-F5 aprobado el mismo día (umbral de 8 decisiones a la vista; trato de usted).

Esta norma es a la interfaz lo que `NORMAS.md` es al cálculo, con una diferencia a propósito. **La interfaz no se congela
como `core/`**: cambia con lo que se aprende de las personas. Lo que se fija son las reglas, no las pantallas.

## Fuentes

- La ficha de la pantalla y su método: skill `.agents/skills/interfaz-silice/` y la skill personal
  `disenar-desde-la-tarea`.
- Las reglas, con sus estudios: `docs/planes/2026-11-23-estudios-ux.md` (UX-01 a UX-29), `docs/planes/2026-11-23-carga-cognitiva.md`
  (reglas 1 a 12) y `docs/planes/2026-11-23-estudios-disenadores.md` (método en 15 pasos).
- El inventario y su juez: `docs/planes/2026-11-23-inventario-f2.md` y `docs/planes/2026-11-23-juez-f2.md`.

## Lo que vigila la máquina (CI)

| Regla | Prueba | Qué falla |
|---|---|---|
| Trato de usted | `frontend-desktop/src/comun/guardiaInterfaz.test.ts` | Pronombres y formas de tú en un texto visible: tú, te, tu, tienes, puedes; imperativos irregulares como Haz o Pon |
| Ninguna sigla suelta en un rótulo | la misma | Un `labelText`, `etiqueta`, `legend` o `titulo` de columna con SPI, CPI, EAC, BAC, FCAS, PV, EV, AC, Km, R, P50, P80 o AACE, sin su explicación entre paréntesis. IVA y RIF quedan fuera porque se leen como palabras |
| La severidad no se escribe en mayúsculas | la misma | «ERROR:», «ADVERTENCIA:» y similares escritos en el front (el ícono ya la dice) |
| Un vacío dice qué hacer | la misma | Un `<EstadoVacio>` sin `descripcion` ni contenido |
| Pestañas iguales en toda la app | `frontend-desktop/src/comun/pestanasConFondo.test.ts` | Un `<TabList>` sin `contained` |
| Ninguna página importa de otra | `frontend-desktop/src/comun/arquitectura.test.ts` | Una importación entre páginas; lo compartido va en `comun/` |

**Modo trinquete.** Lo que ya incumplía cuando nació la guardia está en `comun/guardiaInterfaz.deuda.json`: 22 casos al
2026-11-23. La CI falla con un caso nuevo, y también con uno de la lista que ya se arregló, para que se borre. La deuda
solo puede bajar.

## Lo que revisa una persona (no se puede medir con una prueba)

- 8 decisiones o menos a la vista por paso. Es una pregunta de revisión, no un cupo rígido para tablas y hojas: el juez
  F2 recordó que ese 8 no tiene base empírica.
- Todo éxito con su paso siguiente, y que sea el paso correcto: en tareas repetitivas el «siguiente» puede no ser
  guardar.
- Una tabla de resultados lleva su frase de respuesta, y las cifras de esa frase vienen del servidor.
- El imperativo de tú de un verbo regular («Empieza aquí»): se escribe igual que la tercera persona y la máquina no lo
  distingue.
- Lo que solo se ve en el navegador: los controles visibles por paso y lo que entra en la primera pantalla. Queda para
  una capa medida con `scripts/recorrido_ux_playwright.py`.

## Lo que ninguna guardia prueba

Una guardia evita que vuelva un error conocido, pero no prueba que una pantalla sea amigable. Eso solo lo dice la gente:
una ronda con 3 a 5 personas de la empresa, con tareas cronometradas y el cuestionario SUS (F5 del plan). Cada vez que
alguien se pierda, su frase va a la tabla de errores de la skill `interfaz-silice`, y la regla, si se puede medir, a la
guardia.
