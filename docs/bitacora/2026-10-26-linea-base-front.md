# Línea base del front y guardias de la CI (2026-10-26)

Tarea 2 del plan `docs/planes/PLAN_REDISENO_MARCO.md`. Medidas sobre `frontend-desktop/` de la rama
`inc/ruta-s2-mig-adm-empresa`. Herramientas de desarrollo, fijadas sin `^`: `knip` 5.66.1 y `jscpd` 4.0.5.

## Guardias nuevas (en la CI, job «interfaz», tras las pruebas)

- `npm run muerto` = `knip --include files,dependencies,unlisted,unresolved` (configuración en `knip.json`).
  Falla ante archivos sin uso, dependencias sin uso, importaciones sin declarar o sin resolver.
- `npm run duplicado` = `jscpd src` (configuración en `.jscpd.json`: bloques de 8 líneas o más, umbral 1 %, sin
  pruebas). Falla si la duplicación supera 1 %.
- Para resolver «unlisted» se declararon como devDependencies, con la versión ya instalada, `@carbon/colors`
  11.60.0 (usada por `indicadores/contrasteIbcs.test.ts`) y `@univerjs/core` 1.0.3 (usada por
  `replica/aUniver.test.ts`). El import de `paginas/aprobar/Aprobar.test.tsx` ya estaba resuelto desde P0.4.
- Licencias: `jscpd` trae `spark-md5` con licencia dual «(WTFPL OR MIT)» (solo desarrollo). Se registró en
  `ELECCIONES_DE_LICENCIA` de `scripts/verificar_licencias.mjs` eligiendo MIT (ruling RF-T2-1), igual que dompurify.

## Cifras

| Medida | Línea base (spec §6.1) | Tras la Tarea 2 |
|---|---|---|
| Código de producto TS/TSX | 36.250 líneas | 37.131 |
| Pruebas TS/TSX | 40.255 líneas | 40.457 |
| SCSS | 4.608 líneas | 4.675 |
| Archivos sin uso | 0 | 0 |
| Archivos con exportaciones sin uso (`--reporter compact`) | 38 | 37 |
| Archivos con tipos exportados sin uso (`--reporter compact`) | 57 | 59 |
| Símbolos: exportaciones sin uso (reportero por omisión) | sin medir | 59 |
| Símbolos: tipos exportados sin uso (reportero por omisión) | sin medir | 134 |
| Duplicación (bloques ≥ 8 líneas) | 0,79 % (27 clones), medida con la pasada doble (cada `.tsx` contado como `typescript` y como `javascript`) | 0,88 % (29 clones, 36.870 líneas, 255 archivos), una sola pasada |

La línea base de 38 y 57 contaba archivos (reportero `compact`), no símbolos; las cifras 59 y 134 del reportero por
omisión cuentan símbolos, así que no son comparables con ellas. Con la misma unidad, la diferencia es 38 a 37 y 57
a 59. `knip.json` no cambia esas cifras. Las exportaciones y tipos sin uso no se vigilan en la CI (solo informan).

Duplicación: antes jscpd analizaba los `.tsx` dos veces (como `typescript` y como `javascript`) y el total inflaba a
51.762 líneas con 0,77 %. `.jscpd.json` ahora fuerza una sola pasada (`formatsExts` asigna `ts` y `tsx` a
`typescript`); la cifra real es 0,88 % con 29 clones, bajo el umbral de 1 %. Margen estrecho: conviene vigilarlo. Las
dos cifras de la fila no son comparables: la línea base (0,79 %) se midió con la pasada doble y la de la Tarea 2 con la
simple; la línea base con una sola pasada no se midió.

## Cómo repetir

```
cd frontend-desktop
# líneas de producto, de pruebas y de SCSS
find src \( -name '*.ts' -o -name '*.tsx' \) ! -name '*.test.*' | xargs cat | wc -l
find src \( -name '*.ts' -o -name '*.tsx' \) -name '*.test.*' | xargs cat | wc -l
find src -name '*.scss' | xargs cat | wc -l
# código muerto (guardia)
npm run muerto
# exportaciones y tipos sin uso (informativo): archivos y símbolos
npx knip --include exports,types --reporter compact
npx knip --include exports,types
# duplicación
npm run duplicado
```
