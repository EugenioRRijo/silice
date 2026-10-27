# Cierre de F2: el marco nuevo montado y los módulos retirados (2026-10-27)

Tarea 8 del plan `docs/planes/PLAN_REDISENO_MARCO.md` (cierre de la fase F2), rama `inc/ruta-s2-mig-adm-empresa`, base
`feac008e`. El marco nuevo (`frontend-desktop/src/marco/`) reemplaza al armazón de módulos de `shell/`: barra superior
con migas y buscador (Ctrl+K), barra lateral en árbol (Pendientes, Obras, Empresa) y la obra como espacio de trabajo.

## Commits

| Commit | Qué |
|---|---|
| `9450431f` | `test(marco)` rojo: `Marco.test.tsx` (38 pruebas) y la guardia de vocabulario del marco en `sinJergaInterna.test.ts`, con `Marco.tsx` vacío |
| `8384be09` | `feat(marco)`: `App` monta `Marco`; redirecciones; `EspacioDeObra`; confirmación al salir por el marco; «Nueva obra» con un solo diálogo |
| `adb3b68f` | `refactor(marco)`: borrado de los módulos y migración de sus pruebas |
| `fcab86b0` / `ade51ee1` | rojo y arreglo: barra superior fija y sin pedir obras a quien no las lee (hallazgos del navegador) |
| `a99a9f4f` / `38843b19` | rojo y arreglo: los diálogos propios se pintan en el cuerpo del documento (hallazgo del navegador) |

## Líneas antes y después (base `feac008e` → cierre)

| Carpeta | Archivos | Producto TS/TSX | Pruebas TS/TSX | SCSS |
|---|---|---|---|---|
| `shell/` | 72 → 44 | 4.047 → 2.208 | 5.912 → 2.173 | 1.176 → 375 |
| `marco/` | 23 → 31 | 1.037 → 1.755 | 1.381 → 1.918 | 443 → 685 |
| `shell/` + `marco/` | 95 → 75 | 5.084 → 3.963 (−1.121) | 7.293 → 4.091 | 1.619 → 1.060 (−559) |
| todo `src/` | — | 38.248 → 37.182 (−1.066) | 41.955 → 38.794 | 5.123 → 4.616 |

Línea base de la especificación (§6.1, 2026-10-26): 36.250 / 40.255 / 4.608. El producto sigue por encima de esa línea
(lo sumaron las Tareas 1 a 7, 6b y 1b); esta tarea lo baja en 1.066 líneas. Pruebas en Vitest: 3.076 en la base, 3.115 con las nuevas del marco y 2.849 al cierre;
las que se fueron probaban el armazón borrado (barra de módulos, paneles de área, sidebar, selector de obra, diálogo de
carpetas); las de comportamiento que seguían vigentes se movieron a `marco/Marco.test.tsx` o se adaptaron.

Duplicación (jscpd): 0,88 % (29 clones), bajo el umbral de 1 %. `npm run muerto`: sin hallazgos.

## Lo borrado

`shell/Shell.tsx`, `BarraSuperior.*`, `SidebarModulos.*`, `PanelDeArea.tsx`, `AccesosDelModulo.tsx` (su SCSS pasa a
`paginas/obras/LoQuePuedeHacer.scss`), `SelectorObra.*`, `Selectores.*`, `sidebar.*`, `useFijadoPosible.*`,
`navegacion.*`, `preferencias.*`, `anchoBotonesBarra.test.ts`, `carpetas/DialogoCarpetas.tsx`, `shell.scss` (fundido en
`marco/marco.scss`) y el componente `EnlaceSeguro` con `useClicSeguro` (queda `useNavegarSeguro` en
`shell/navegarSeguro.ts`). De `rutas.ts`: `MODULOS`, `ubicacion`, `en()`, `inicioDe`, `modulosVisibles`,
`fueraDeModulos`, `moduloDePagina` y `visible` (las pantallas usan `usable`). `_umbrales.scss` se mueve a `marco/` solo con
los umbrales por letra (se van `$umbrales-por-modulo`, `barra-no-cabe`, `$fijado-desde` y `fijado-posible`). Del contexto,
`modulo`. En Python, `test_front_entrada_por_rol.py` pasa a `test_front_acciones_por_rol.py` (lee las acciones de
`datosDePrueba.tsx`; `ENTRADA_POR_ROL` ya no existe) y de `test_recorrido_ux_playwright.py` salen las dos pruebas del menú
de módulos (`test_los_tres_modulos_con_sus_areas_en_orden`, `test_camino_por_el_menu_de_cada_pantalla`); el script sigue
como estaba y se ajusta al ruteo nuevo en F7.

## Decisiones donde el plan calla (rulings del implementador, por revisar)

1. **Sección vieja con consulta y sin obra elegida** (`#/aprobar?envio=12` de quien revisa): se abre en su dirección en vez
   de ir a Pendientes, para no perder el envío. Con obra elegida, redirige a la sección conservando la consulta.
2. **Cambiar de obra a otra carpeta desde el marco** (árbol, migas, buscador) pregunta también por los borradores de la Hoja
   con cambios (`hojasConCambios`), porque el cambio de carpeta los olvida en el servidor; con formularios sucios pregunta
   siempre. Las pantallas siguen preguntando por su cuenta (`useNavegarSeguro`).
3. **«Inicio de producción» exige `operar_arenera`**: antes lo escondía su módulo; sin módulos, toda cuenta lo vería en el
   buscador sin poder usarlo.
4. **Un solo diálogo «Nueva obra»** (`marco/nuevaObra.ts`): la mesa lo pide al de la barra lateral, que dice dónde se creará;
   `DialogoNuevaObra` exige `destino` (ningún camino crea obras sin decir dónde). Al crear, se abre la obra nueva.
5. **La mesa sin obras que leer** (el administrador) muestra «Lo que puede hacer aquí» con las pantallas que su cuenta usa y
   no tienen sitio en el árbol (las del buscador), en vez de los accesos del módulo.
6. **Cabecera de la obra**: nombre, moneda (de `GET /v1/obras/resumen`, solo con `leer_proyecto`), versión y la lista para
   armar de su carpeta (`ListaDeLaCarpeta`, que vivía en el selector de obra; la especificación pide la lista en la
   cabecera). No es un encabezado: el único h1 es el de la sección.
7. **Pruebas de carpetas**: van por Empresa › Empresa y personas › Carpetas de trabajo (el diálogo de la barra se retiró);
   las del foco del botón de la barra y las de «Componer a medio llenar» con el diálogo abierto se retiraron; el cambio de
   carpeta con trabajo sin guardar lo prueban `Marco.test.tsx` y la prueba de Administración con un borrador.
8. **Barra superior fija y diálogos en portal** (hallazgos del navegador): el cuerpo reserva 3 rem para una cabecera fija
   (la de Carbon de las pantallas sin marco), así que la barra del marco también es fija; la barra lateral es sticky y
   apila aparte, así que `MarcoDeDialogo` se pinta en `document.body`.
9. **Sin `leer_proyecto` no se piden las obras** (`useObras` da `sin_permiso`) y la barra lateral no pinta la zona de obras.
10. **Elegir una obra en la mesa** la fija dos veces (`PUT /v1/sesion/proyecto` de la mesa y, al abrir la sección, del
    marco): siempre la misma; se aceptó para no tocar pantallas que leen la obra de la sesión.

## Verificación

- Front (`frontend-desktop`): `npm test` 190 archivos, 2.849 pruebas en verde; `npm run lint` limpio; `npm run muerto` sin
  hallazgos; `npm run duplicado` 0,88 %; `npm run build` correcto.
- Python: `uv run --active pytest -q` (ver el informe de la tarea): una falla previa y ajena,
  `tests/unit/test_arquitectura_s5.py::test_aplicacion_y_api_no_importan_migraciones` (`aplicacion/casos.py`, de
  `ded765d7`), que no se tocó.
- Navegador (una pasada, con el tema local de la empresa y datos ficticios sembrados; capturas solo en el scratchpad, no se
  versionan): Pendientes, una obra en su Presupuesto, el árbol con cinco carpetas, el buscador abierto, «Nueva obra» y
  Empresa › personas, a 1056, 1366 y 1910 px con letra 1 y 1,5. Sin desplazamiento horizontal ni errores de consola en
  ninguna (salvo los 403 del administrador, ya corregidos). Salieron los tres hallazgos de los puntos 8 y 9, que se
  arreglaron con su prueba en rojo y se comprobaron con tres capturas más. No apareció ningún aviso de contraste del tema.

## Pendiente (F3 en adelante, o decisión de Eugenio)

- Pendientes y Resumen muestran la mesa con su h1 «Inicio de presupuestos y obras» (F3 trae la bandeja).
- «Nueva obra» aparece dos veces en Pendientes (barra lateral y cabecera de la mesa); la especificación pide un solo botón
  principal por pantalla.
- Con letra 1,5 a 1056 px las migas se recortan con puntos suspensivos y la barra lateral ocupa cerca del 40 % del ancho.
- El recorrido guiado no marca el paso «Suba el libro» en `#/empresa/auditoria` (compara con `#/auditoria`).
- Precios de la empresa, Índices del BCV, Simulador, Histórico, Tablero, Componer… solo se alcanzan por Ctrl+K (F4/F5).
- `scripts/recorrido_ux_playwright.py` sigue midiendo la barra de módulos (F7).
- La cabecera de la obra pide `GET /v1/obras/resumen` solo para la moneda; una ruta de la obra la daría más barata.
