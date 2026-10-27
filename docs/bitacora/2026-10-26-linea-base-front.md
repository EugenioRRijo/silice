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
| Exportaciones sin uso | 38 | 59 |
| Tipos exportados sin uso | 57 | 134 |
| Duplicación (bloques ≥ 8 líneas) | 0,79 % (27 clones) | 0,77 % (27 clones) |

Las líneas crecieron por el trabajo de P0 y de la Tarea 1 posterior a la medición. Las exportaciones y tipos sin uso
no se vigilan en la CI (solo informan); la diferencia con la línea base puede deberse a esa misma obra nueva y a que
la medición original usó otra configuración de knip; no se pudo reproducir con exactitud.

## Cómo repetir

```
cd frontend-desktop
# líneas de producto, de pruebas y de SCSS
find src \( -name '*.ts' -o -name '*.tsx' \) ! -name '*.test.*' | xargs cat | wc -l
find src \( -name '*.ts' -o -name '*.tsx' \) -name '*.test.*' | xargs cat | wc -l
find src -name '*.scss' | xargs cat | wc -l
# código muerto (guardia)
npm run muerto
# exportaciones y tipos sin uso (informativo)
npx knip --include files,exports,types
# duplicación
npm run duplicado
```
