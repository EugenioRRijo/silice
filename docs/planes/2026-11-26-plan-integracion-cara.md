# Plan: integrar la cara «Papel y resaltador» en el front (B1)

**Fecha:** 2026-11-26 · **Rama:** `feature/front-b1` · **Tope:** 2026-12-16 (etiqueta `medicion-v1`)
**Pedido de Eugenio:** «cuando termines en el artifact del reformulacion de fornt, empieza a integrar a la rama el
nuevo front y ui ux».
**Fuente del diseño:** [especificación](../especificaciones/2026-11-26-cara-papel-y-resaltador/README.md) y el lienzo
del artifact (tableros `S-*`, «Botones», «Barra lateral» y «Tablero de inicio»).

## Límites (los del acta, sin cambio)

`core/`, los archivos sellados por `reglas-congeladas-2026-11-24` y `aplicacion/hoja.py` no cambian. Las rutas del
contrato de 2026-11-04 no cambian: la cara nueva cambia dónde y cómo se muestran las secciones, no sus direcciones.
TDD (prueba en rojo primero), ub-mode, la guía *modern-web-guidance* consultada en cada lote, la skill
`interfaz-silice` antes de tocar una pantalla, y `sinJergaInterna` en verde. Coma decimal, trato de usted, la cifra la
calcula el servidor, la gravedad siempre con su palabra.

## Lotes, en orden

| Lote | Qué | Archivos principales | Quién construye |
|---|---|---|---|
| **C0** Fundamentos | Tokens claro y oscuro de la especificación como `--silice-*`, con `color-scheme: light dark` y `light-dark()` (respaldo con `prefers-color-scheme`); los tokens de Carbon (`--cds-background`, `--cds-layer-*`, `--cds-text-*`, `--cds-border-*`, `--cds-interactive`, `--cds-focus`, `--cds-button-*`) apuntan a ellos; Instrument Sans y Newsreader empaquetadas desde `@fontsource/instrument-sans@5.3.0` y `@fontsource/newsreader@5.3.0`; `/v1/tema` sigue mandando sobre el acento | `estilos/tokens.scss`, `estilos/fuentes.scss`, `package.json`, `marco/tema.ts` | Carbon, con Neon de revisor |
| **C1** Modo oscuro elegible | Cuenta › Empresa y tema con tres estados (Claro, Oscuro, Como el sistema, que dice cuál rige); `localStorage`; un script propio pequeño (`public/modo-inicial.js`, `script-src 'self'`) junto al `<meta name="color-scheme">` para que no parpadee; el evento `storage` sincroniza pestañas | `index.html`, `public/modo-inicial.js`, la sección de la Cuenta | Hydrogen |
| **C2** Botones | «Contorno de papel» sobre los botones de Carbon: principal en tinta, secundario con trazo de 1,5 px que se rellena al pasar, terciario subrayado, destructivo con trazo rojo; escala 28/32/40; foco dorado; patrón «inactivo que explica por qué» (`aria-disabled`) | `estilos/app.scss` (capa de botones), un componente `comun/BotonInactivo` | Hydrogen |
| **C3** Barra de la empresa | Espacios + «Nueva obra» amarilla fija + Buscar + cuenta | `marco/BarraSuperior.tsx` | Carbon |
| **C4** Barra de la obra | Nombre → Portada; pestañas Presupuestar · Auditar · Anticipar, cada una a la primera sección de su grupo; menú de versión (versiones, pedir aprobación, entregar); la acción principal de la herramienta | `marco/CabeceraDeObra.tsx`, `marco/BarraDeEspacio.tsx`, `marco/secciones.ts` (solo la agrupación, no las rutas) | Carbon |
| **C5** Riel lateral | Panel propio con iconos, reducible a 56 px (se recuerda), bloque de cifras de las otras herramientas (solo lo que la API ya da), carpeta abierta al pie | `marco/BarraLateral.tsx`, `marco/marco.scss` | Carbon |
| **C6** Notas al margen | Componente de notas numeradas unidas a su fila, sobre la lógica pura de B1-1 (`gruposDeProblemas`, `filaDelHallazgo`); Presupuestar › Partidas con la tabla HM (precio con referencia de lista) | `paginas/hoja/superficie/*` | Carbon (con B1-2b, la grilla) |
| **C7** Gráficos | Series validadas (azul, aguamarina, naranja) en los gráficos de Carbon Charts y en los propios; capa de detalle al pasar; «Ver como tabla» | gráficos de Control, Riesgo, Mercado, Escenarios y Producción | Hydrogen |
| **C8** Inicio | Inicio › Resumen con gráficos y la vista «Nueva obra» en lugar del diálogo (mismos datos que `DialogoNuevaObra`) | `paginas/inicio/*`, `shell/obras/*` | Carbon |

Después siguen los lotes de comportamiento de la [ficha de B1](../bitacora/2026-11-25-acta-reestructuracion-front.md)
(B1-2b en adelante), que ya se escriben con la cara nueva.

## Cómo se cierra cada lote

1. Prueba en rojo por cada comportamiento visible (rol, nombre accesible, `aria-current`, `aria-pressed`, el modo).
2. Verde; `npm run lint`, `tsc`, `npx vitest run --maxWorkers=3`, y para estilos las pruebas de `estilos/*.test.ts`.
3. Mutaciones a mano en lo nuevo (ub-mode: matar sobrevivientes).
4. Una mirada en el navegador en claro y oscuro contra el tablero del lienzo.
5. Commit en `feature/front-b1`; revisión de Neon o de Opus al cerrar cada dos lotes.
