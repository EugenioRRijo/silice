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
npm run dev       # inicio rápido: compila y sirve API + /app en un puerto, visible en la red local (scripts/inicio_rapido.mjs)
npm run dev:vite  # servidor de desarrollo con recarga en caliente; /v1 se reenvía a http://127.0.0.1:8000 (la API encendida)
```

La interfaz compilada la sirve el FastAPI en `/app` (`http://127.0.0.1:<puerto>/app/`; un solo proceso sirve la API y esta interfaz).

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

## El visor (tarea 2.4)

Al entrar con una cuenta (`/v1/sesion`, cookie `HttpOnly`; el token anti-CSRF vive solo en memoria) la pantalla
pide el libro `.xlsx`, llama a `/v1/libros/replica` y `/v1/libros/auditoria` en paralelo y dibuja la hoja con Univer
en solo lectura, con un halo de severidad sobre la celda de cada hallazgo.

- `src/replica/aUniver.ts` es el **único** lugar que convierte el contrato neutro (base 1, caracteres, puntos) a la
  instantánea de Univer (base 0, píxeles). `formatoNumero.ts` da el texto que se ve en cada celda.
- `src/visor/hojaVisor.ts` es la interfaz propia detrás de la que vive Univer; `adaptadorUniver.ts` es el único
  archivo que importa Univer y se carga con `import()` (un archivo aparte en el `dist`). En las pruebas de jsdom,
  donde Univer no dibuja, se usa el doble de `hojaFalsa.ts`.
- La capa de halos (`CapaHalos.tsx`) es DOM sobre el lienzo y se recalcula cuando el visor avisa un cambio.
- Univer trae `'unsafe-inline'` en `style-src` por necesidad: inyecta `<style>` con sus variables de tema. No usa
  `eval`, `new Function`, workers ni `blob:` para scripts.

## El marco y cómo se migra una página (sesión 2b)

`src/shell/` es el marco: cabecera de Carbon (nombre, selector de **caso** y de **proyecto**, «Salir»), menú lateral por
rol y modo entrega, y la ruta de cada página. La navegación es de hash (`/app/#/libros`): el servidor de `/app` es
estático y no responde `index.html` a `/app/libros`. El menú, las rutas y los permisos salen de **una** lista:
`src/shell/rutas.ts` (22 páginas, con su sección y su `Accion`). Lo que la persona puede ver sale de
`acciones` y `modo_entrega` de `GET /v1/sesion`; la API vuelve a exigir cada acción.

Para agregar una página (el id es su ruta, p. ej. `catalogo`):

1. Crear `src/paginas/<id>/index.tsx` con un `export default` (el componente, sin props). Lo que necesita sale de
   `useAplicacion()` (`src/shell/contexto.tsx`): `sesion`, `proyecto` elegido (código o `null`), `caso`,
   `recargarProyectos()` y `alExpirar()` (llamarlo ante un 401).
2. En `rutas.ts`, a su línea, agregar `cargar: () => import("../paginas/<id>")` (es obligatorio). Cada página es un archivo aparte en el `dist`.
3. Hablar con la API solo con `pedir` / `pedirBinario` de `src/api/cliente.ts`; los montos llegan como texto y se
   muestran tal cual. Si cambia el caso, el marco vuelve a montar la página (pedir los datos al montar basta).
4. Usar `src/comun/`: `TablaDensa` (Carbon `sm`, montos a la derecha, orden decimal exacto, esqueleto y estado vacío),
   `SubidaArchivo`, `DescargaArchivo`, `AvisoError` (muestra el `detalle` de la API), `EstadoVacio`, `EsqueletoPagina`.
5. Pruebas con Vitest y Testing Library; en las pruebas de página, inyectar un doble de `fetch` como en
   `src/shell/Shell.test.tsx`.

Librerías (RM-5): `react-router` (enrutamiento) y `@carbon/charts-react` con `@carbon/charts` (gráficos del tablero y la
curva de control). Para tablas basta Carbon `DataTable`; no se agregan más paquetes sin ruling.

