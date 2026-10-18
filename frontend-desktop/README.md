# frontend-desktop

Interfaz nueva de Sílice: visor de solo lectura de libros de presupuesto. Vite + React 19 + TypeScript,
IBM Carbon (tema g10) y, desde la tarea 2.4, Univer para dibujar la hoja. Producto y diseño:
[PRODUCT.md](./PRODUCT.md) y [DESIGN.md](./DESIGN.md). Plan: `docs/planes/PLAN_SESION_2_VISUAL.md`.

## Requisitos

Node 22 (el mismo de la CI) y npm. No hace falta nada más: las fuentes IBM Plex vienen en los paquetes
`@ibm/plex-sans` y `@ibm/plex-mono` y Vite las copia al `dist`; la interfaz no pide nada a la red externa.

## Cómo correr

```bash
cd frontend-desktop
npm ci            # instala exactamente lo que dice package-lock.json
npm run dev       # servidor de desarrollo; /v1 se reenvía a http://127.0.0.1:8000 (la API encendida)
```

La interfaz compilada la sirve el FastAPI en `/app` (`http://127.0.0.1:<puerto_api>/app/`).

## Cómo probar

```bash
npm test          # Vitest (jsdom): pruebas de la aplicación y de los scripts de control
npm run lint      # ESLint y tsc -b --noEmit
npm run build     # tsc -b && vite build, deja la interfaz en dist/
npm run licencias # package-lock.json: licencias permisivas y ningún @univerjs-pro/*
npm run dist      # dist/: 15 000 000 bytes como máximo y ninguna URL a otro anfitrión
```

La CI (`interfaz` en `.github/workflows/ci.yml`) corre todo en ese orden.

## Reglas del andamiaje

- Versiones **exactas** en `package.json` (sin `^` ni `~`; `.npmrc` tiene `save-exact=true`) y
  `package-lock.json` versionado. Para sumar un paquete: `npm install --save-exact nombre@version`, con una
  versión publicada hace por lo menos dos semanas.
- Solo paquetes de Univer con licencia Apache-2.0: `@univerjs-pro/*` está prohibido y `npm run licencias` lo
  detecta. MPL-2.0 y CC-BY-4.0 se admiten solo en dependencias de desarrollo (`dev: true` en el lock).
- Colores: nunca hexadecimales sueltos. Los alias `--silice-*` de `src/estilos/tokens.scss` apuntan a colores y
  tokens de Carbon.
- Fuentes: `src/estilos/fuentes.scss` declara IBM Plex desde los paquetes; la carga de fuentes de Carbon está
  apagada (`$css--font-face: false`, `$use-akamai-cdn: false`).
- Sin animaciones decorativas; `prefers-reduced-motion: reduce` quita también las transiciones de Carbon.
