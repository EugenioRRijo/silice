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
- Python: `uv run --active pytest -q` (ver «Menores agrupados» más abajo). Al cerrar la Tarea 8 la rama traía **varias
  fallas previas y ajenas a ella**, con este origen:
  1. `tests/unit/test_arquitectura_s5.py::test_aplicacion_y_api_no_importan_migraciones`: `aplicacion/casos.py` importaba
     `migraciones.metadatos` desde `ded765d7`.
  2. `tests/integration/test_api_auditorias.py::test_toda_ruta_menos_salud_exige_la_clave` y las pruebas por ruta de
     `tests/integration/test_api_clave.py`: `/v1/tema` y `/v1/tema/logo` (Tarea 1) son públicas por diseño y las guardias
     no las conocían.
  3. `tests/unit/test_paquete_anexos.py` (toda tabla con `responsable` viaja o figura entre las que no) y
     `tests/unit/test_responsables.py` (cada tabla con `responsable` con su prueba): faltaban `mp_compra`,
     `mp_observacion`, `mp_precio_corte` y `mp_precio_objetivo` (T23 a T25).
  4. `tests/unit/test_scripts_documentados.py`: `scripts/recorrido_ux_playwright.py` sin fila en `scripts/README.md`.
  5. `tests/unit/test_excel_m1.py`, los tres casos con prefijo CR: el `.venv` trae `lxml` 6.1.3 (lo instala
     `python-docx`, que no está en `uv.lock`) y con él el retorno de carro vuelve como CR y no como LF.
  6. `tests/unit/test_huellas_rnf04.py::test_huella_del_contenido_del_libro`: misma causa (con `OPENPYXL_LXML=False` la
     huella coincide); el producto no cambió.
  7. `tests/unit/test_experimento_congelado_vigente.py`: `aplicacion/hoja.py` y `aplicacion/composicion.py` (listados en
     `archivos_del_auditor`) cambiaron con MP-7 después del re-congelado `1ec20732`.
  8. `tests/integration/test_api_ola2_revision.py::test_revalorar_con_la_cuenta…` (ERROR en la preparación): la fixture
     de cuentas pisaba la instalación ya abierta por `cliente` y dejaba su `-wal` viejo.
  La tanda de menores arregló 1 a 5 y 8 (ver la tabla); quedan 6 (ambiental: depende de si `lxml` está instalado, no
  del producto) y 7 (decisión de Eugenio y del tutor: volver a congelar o sacar esos archivos de la lista; no se toca).
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
- Comparación con la maqueta aprobada (barra lateral marfil, 2026-10-28) sobre las capturas de T8 a 1366 px; lo que no
  estaba anotado:
  - El color de acción sigue siendo el azul de Carbon (botón principal, enlaces, pestañas activas); la maqueta usa el
    ámbar y el carbón de la empresa. El tema de empresa colorea el marco pero no los tokens interactivos de Carbon
    (decidir en F3 si el tema los cubre, con su medida de contraste).
  - El árbol muestra los nombres técnicos de las carpetas (`demo`, `obra_control`, `of001`, `s1`) como títulos de
    grupo; la maqueta solo muestra obras. Falta un nombre legible por carpeta o agrupar de otra forma (F3/F4).
  - Encima de la barra superior queda una franja gris vacía en las capturas: confirmar en navegador si es del marco o
    de la captura (F3).
  - La cuenta se muestra como «Ana» con tres botones de tamaño de letra; la maqueta pone un círculo con iniciales
    (decidir si los tamaños de letra pasan al menú de la cuenta).
- ~~La cabecera de la obra pide `GET /v1/obras/resumen` solo para la moneda~~: resuelto en los menores (punto 40).

## Rondas de la Tarea 8

La Tarea 8 tuvo **3 rondas de árbitro más 1 ronda corta extra** autorizada por el orquestador. La ronda 3 encontró un
MAYOR nuevo y ningún BLOQUEANTE: el aviso «otra pestaña» no se anunciaba ni dejaba el foco tras «Retomar»; se arregló con
el patrón de `a4973d94` (el aviso de la obra caída). La ronda extra la **aprobó**.

| Ronda | Commits |
|---|---|
| 1 | `9450431f` .. `8cd0848b` |
| 2 | `5e23124b`, `cb60840b`, `45d7bf38` |
| 3 | `2387e70b`, `a4973d94` |
| extra (aprobada) | `99633220`, `7dff871e` |

Proceso: `adb3b68f` (refactor) metió conducta nueva sin commit rojo propio (`alEntrarEnObra`, `LoQuePuedeHacer`, la lista
para armar en la cabecera de la obra); el rojo lo verificó el árbitro. Queda anotado para no repetirlo: la conducta nueva
va en su commit de prueba aunque llegue dentro de un refactor.

## Menores agrupados de P0 y F2 (2026-10-27)

Un solo encargo cerró los detalles menores que dejaron los árbitros y tres decisiones de Eugenio. Cada punto se comprobó
antes contra el código que dejó la Tarea 8. Conducta con TDD: el commit de pruebas en rojo va antes que el arreglo.

| N.º | Estado | Qué |
|---|---|---|
| A1 | hecho `304cd3ff` (rojo) `3ae86bec` `2cfc8626` `2593830d` | raya del activo a `--silice-marco`; par «raya del activo» (marco sobre lateral-activo, 3:1) en `aplicacion/tema.py`; neutro sin avisos (#393939 sobre #e5e0df = 8,83:1 a mano); plan y DESIGN al día |
| A2 | hecho `3be48805` (rojo) `00669425` | el buscador no repite el «Resumen» de la obra: una ruta no sale dos veces |
| A3 | hecho `258c75a9` (rojo) `df7c9009` | 403, 409 y 503 declarados en `POST /v1/proyectos`; `docs/api.json` y CHANGELOG |
| 4 | hecho `ff11c235` | CHANGELOG de T24 |
| 5 | hecho `423e6266` (rojo) `ad9b6e05` | Valuaciones conserva la causa sugerida mientras recarga (`useCargaSuave`) |
| 6 | hecho `ff11c235` | riesgo de la fecha del equipo frente a la del servidor, en la bitácora de T24 |
| 7 | hecho `26cd1b55` | `caso_0017` advierte que bajar borra los precios declarados |
| 8 | hecho `f6d3f61d` | prueba API del 409 `ReglaDelCorte` (obra sin línea base); pasaba ya: la ruta lo traducía bien |
| 9 | hecho `423e6266` (rojo) `ad9b6e05` | el precio de la recepción deja de ser «opcional» con la casilla marcada |
| 10 | hecho `6c472172` | la lista de tablas conocidas pasa a `operacion.base_datos`; `aplicacion` ya no importa `migraciones`; sin cambio de conducta |
| 11 | hecho `5c656e2d` (rojo) `d875e234` | la prueba con Univer que nunca llega a Rendered encontró que `univer.dispose()` lanzaba y tapaba el mensaje; ahora se desecha como en `destruir` |
| 12 | hecho `2cfc8626` | `write_text` con `encoding="utf-8"` en `test_api_tema` |
| 13 | hecho `ff11c235` | la fila de duplicación de la bitácora de T2 dice que compara pasada doble con simple |
| 14 | hecho `ec3550d3` | comentario de la ventana «obra borrada entre el GET y el PUT» |
| 15 | hecho `ec3550d3` | documentado el vigilante estable |
| 16 | hecho `2593830d` | Tarea 5 Paso 1 del plan: texto visible como nombre, oculto solo visualmente, `aria-keyshortcuts` |
| 17 | hecho `c052655e` (rojo) `1b3361f6` | Ctrl+K respeta `contenteditable="plaintext-only"` y todo editable |
| 18 | hecho `c052655e` | caso con `contenteditable=""` sobre el propio destino (pasaba ya) |
| 19 | hecho `52624abc` (rojo) `3ae86bec` | `aria-level`, `aria-setsize` y `aria-posinset` del árbol con carpetas, con prueba de niveles |
| 20 | hecho `52624abc` (rojo) `3ae86bec` | «Cargando obras…» en vez de un `tree` vacío |
| 21 | hecho `52624abc` (rojo) `3ae86bec` | el código de la obra creada se valida (solo dígitos) antes de navegar |
| 22 | hecho `52624abc` (rojo) `3ae86bec` | sin obras que mostrar, «cargando» y «todavía no hay» se distinguen por el estado, también tras una recarga |
| 23 | hecho `ae7eca34` (rojo) `df7c9009` `b0c36fa8` | `GET /v1/obras/todas` suma `carpeta_actual_titulo`; la barra lateral deja de armar el título |
| 24 | ya resuelto | `DialogoNuevaObra` ya no trae restos de `cambio` ni de la vuelta, y no hay `puedeEditar` por omisión (T6b y T8) |
| 25 | hecho `258c75a9` | el 422 de nombres de carpeta con `CON`, `NUL.db`, `silice.db:x` y UNC (pasaba ya) |
| 26 | hecho `258c75a9` | todo o nada del destino con `obras.guardar_ficha` fallando (pasaba ya) |
| 27 | ya resuelto | `DESIGN.md` ya describe la barra lateral en árbol; no queda «Sin menú lateral» |
| 28 | hecho `3be48805` | control positivo del buscador (oferta completa encuentra «Empresa y personas»; sin permisos, nada) |
| 29 | hecho `3be48805` (pruebas) `00669425` | `oferta` obligatoria en `resultadosDe` |
| 30 | hecho `3be48805` (rojo) `00669425` | `aria-expanded` del buscador según haya resultados |
| 31 | hecho `3be48805` | pruebas de Tab atrapado y de foco a `#contenido` al elegir (pasaban ya) |
| 32 | hecho `2593830d` | Tarea 7 del plan: `busqueda.ts` y diálogo propio, con el porqué (RNF-22) |
| 33 | hecho `f9768bb8` | `_NEUTRO` frente a `@carbon/colors` y al tema g10 (prueba de Vitest que lee `aplicacion/tema.py`) |
| 34 | hecho `c469cea5` | sin mock sobrante en `AvisosDelTema.test.tsx` |
| 35 | hecho `1f9b7496` | `/v1/tema` y `/v1/tema/logo` en las guardias reales (`tests/integration/test_api_auditorias.py` y `test_api_clave.py`; los nombres del encargo no existían) |
| 36 | hecho `00043f16` | `mp_compra`, `mp_observacion`, `mp_precio_corte` y `mp_precio_objetivo` en `TABLAS_QUE_NO_VIAJAN` (hoy no se exportan; si algún día viajan, decisión de Eugenio y del tutor) y en la cobertura de responsables (con una prueba nueva del objetivo) |
| 37 | hecho `cb976670` | fila de `recorrido_ux_playwright.py` en `scripts/README.md` |
| 38 | parcial: `49b49cfb` `9284ffe2`; pendientes 6 y 7 | `test_excel_m1` y `test_api_ola2_revision` arreglados; `test_huellas_rnf04` es ambiental (`lxml`) y `test_experimento_congelado_vigente` espera decisión (ver arriba) |
| 39 | hecho | la lista completa de fallas previas de pytest, arriba |
| 40 | hecho `1c32964b` (rojo) `5fdd2ccd` `4529f882` | la cabecera de la obra dice «Moneda: …» una sola vez, sin «de trabajo»; deja de pedir `GET /v1/obras/resumen` solo para eso |
| 41 | hecho `ec3550d3` | comentado por qué no hace falta excluir `.silice-dialogo`: `closest("a[href]")` recorre el DOM y ningún diálogo lleva enlaces |
| 43 | hecho | «Rondas de la Tarea 8», arriba |
| 44 | hecho | nota de proceso sobre `adb3b68f`, arriba |

El pendiente «La cabecera de la obra pide `GET /v1/obras/resumen` solo para la moneda» de la sección anterior queda
resuelto por el punto 40.

### Verificación de los menores

- Front: `npm test` 191 archivos y 2.894 pruebas en verde; `npm run lint`, `npm run muerto` y `npm run build` limpios;
  `npm run duplicado` 0,88 % (29 clones).
- Python: `uv run --active pytest -q` (suite completa): 10.487 pasan, ninguna omitida y 2 fallan, las dos de arriba que no
  son de este encargo: `test_huellas_rnf04` (ambiental, `lxml`) y `test_experimento_congelado_vigente` (decisión de
  Eugenio y del tutor). `ruff check` de lo tocado, limpio.
