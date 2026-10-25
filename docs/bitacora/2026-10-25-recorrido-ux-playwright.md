# Recorrido de UX/UI con Playwright (2026-10-25)

**Encargo:** Eugenio pidió «un playwright para adaptar mejor la UX y UI». La empresa (reunión del 2026-10-25) pidió:
aceptar cualquier archivo de presupuesto; que «Libro de la empresa» deje de ser una entrada del menú y pase a contexto
opcional dentro de la auditoría; una sola vista de trabajo; auditar directo con los APU en segundo plano y un informe
accionable; elegir el caso o el dominio solo. Eugenio decidió **no retirar** las pantallas actuales: se adaptan.
Este documento es insumo de diseño; no implementa nada.

**Herramienta:** `scripts/recorrido_ux_playwright.py` (sin dependencias nuevas). Se repite después de cada cambio:

```powershell
uv run --active --with playwright python scripts/recorrido_ux_playwright.py --salida <carpeta-fuera-del-repo>
# opciones: --roles admin ana rita  --anchos 1366 1056  --rutas inicio libros  --sin-axe  --sin-flujo  --url <servidor ya en marcha>
```

Arranca Uvicorn en `127.0.0.1` (puerto libre) con una carpeta de datos **temporal** (cuentas de
`tests/fixtures/sesion_web.py` y casos de demostración de `start.py`; nunca `data/`), entra como `admin` (administra),
`ana` (arma) y `rita` (revisa), recorre las 22 rutas de `frontend-desktop/src/shell/rutas.ts` (las lee del archivo, así
que una ruta nueva entra sola) a 1366×768 y 1056×768, y cierra el servidor por su PID y borra los datos temporales.
Por pantalla guarda captura, número de h1, desplazamiento horizontal, alto, errores de consola/red, tiempo hasta el
primer h1 y revisión axe-core (WCAG 2.0/2.1 A y AA; se baja de jsdelivr a la carpeta de salida, sin instalar nada).
Salida: `recorrido.json` y `capturas/`. Además recorre el flujo de subir un presupuesto con libros ficticios.

**Corrida de referencia (2026-10-25):** 132 mediciones (22 rutas × 3 roles × 2 anchos), 140 capturas, axe en las 132.
Libros usados: el libro limpio de `tests/fixtures/libros_empresa.py` (plantilla ficticia), `tests/fixtures/control/ob_s2.xlsx`
(un `.xlsx` ajeno a la plantilla) y un `.csv` fabricado. Ningún dato real.

## 1. Resultado por pantalla (1366 y 1056 px)

Cada fila mide la pantalla con un rol que la ve. «Roles» sale del menú lateral de cada cuenta. Las 68 mediciones de rutas
que el rol no tiene en el menú no cuentan aquí (véase H-8). Ninguna pantalla tuvo error de consola, error de red ni
desplazamiento horizontal a 1056 px. «Alto» es el alto del documento: la mayoría llena el viewport (768) porque el
contenido se desplaza dentro de su propio contenedor, así que **no** mide cuánto contenido hay (límite de la herramienta,
véase §6).

| Pantalla | Roles que la ven | h1 | t. hasta h1 (ms, 1366) | Scroll X 1366/1056 | Alto 1366/1056 | axe A/AA |
|---|---|---|---|---|---|---|
| `inicio` Inicio | admin, ana, rita | 1 | 357-447 | no/no | 768/768 (ana 980/980) | `scrollable-region-focusable` (serious) en rita 1056 |
| `tablero` Tablero del proyecto | ana, rita | 1 | 394-462 | no/no | 768/768 | limpio |
| `catalogo` Catálogo de partidas e insumos | ana, rita | 1 | 356-450 | no/no | 768/768 | limpio |
| `componer` Componer una partida | ana | 1 | 471 | no/no | 2008/2082 | limpio |
| `elaborar` Elaborar un presupuesto | ana | 1 | 409 | no/no | 768/791 | limpio |
| `hoja` Hoja del proyecto | ana | 1 | 484 | no/no | 768/768 | limpio |
| `actualizacion` Actualizar precios | ana | 1 | 465 | no/no | 768/768 | limpio |
| `historico` Histórico de cambios de precio | ana, rita | 1 | 467-555 | no/no | 768/768 | limpio |
| `precios_empresa` Precios de la empresa | admin | 1 | 512 | no/no | 768/768 | limpio |
| `indices` Índices del BCV | admin | 1 | 511 | no/no | 768/768 | limpio |
| `reajuste` Reajuste de precios | ana | 1 | 510 | no/no | 768/768 | limpio |
| `control` Control de obra | ana | 1 | 508 | no/no | 768/768 | limpio |
| `acerca` Acerca de Sílice | admin, ana, rita | 1 | 386-518 | no/no | 828/851 (admin) | limpio |
| `entregar` Entregar paquete | ana | 1 | 503 | no/no | 768/768 | limpio |
| `existencias` Existencias de la arenera | admin, ana | 1 | 396-506 | no/no | 768/768 | limpio |
| `revisar` Revisar un paquete | rita | 1 | 571 | no/no | 768/768 | limpio |
| `libros` Libro de la empresa | ana, rita | 1 | 534-570 | no/no | 768/768 | limpio |
| `historial` Historial de auditorías | ana, rita | 1 | 406-446 | no/no | 768/768 | limpio |
| `escenarios` Escenarios de sensibilidad | ana | 1 | 511 | no/no | 768/768 | limpio |
| `similares` Partidas similares | ana | 1 | 482 | no/no | 768/768 | limpio |
| `simulador` Simulador de listas | ana | 1 | 382 | no/no | 768/796 | limpio |
| `administracion` Administración | admin | 1 | 534 | no/no | 1751/1751 | `color-contrast` (serious, 1 nodo) a ambos anchos |

Tiempo hasta el primer h1 en carga en frío de la ruta: 356-571 ms (media 466 ms sobre 32 pantallas accesibles). Sin
problema de rendimiento.

Lo que cada rol ve hoy (cuántas de las 22 pantallas): `ana` 18, `rita` 8, `admin` 6.

## 2. El flujo de la empresa tal como existe hoy

Medido con la cuenta `ana` (arma) a 1366 px; 2,2-2,7 s desde soltar el archivo hasta ver el resultado.

| Camino | Pantallas | Clics | Archivos | Decisiones | Resultado |
|---|---|---|---|---|---|
| A. Inicio → soltar `.xlsx` en «Audite un presupuesto» → «Auditar por mi cuenta» → ver hallazgos (libro con la forma de la plantilla) | 2 (Inicio, Libro de la empresa) | 2 | 1 | 2 (elegir entre 22 pantallas/herramientas; «guiado» o «por mi cuenta») | Visor con hoja y 2 hallazgos «Información» |
| B. Inicio → menú «Libro de la empresa» → soltar `.xlsx` → ver hallazgos | 2 | 2 | 1 | 2 (ruta; fecha de devolución) | Igual que A |
| C. A o B con un `.xlsx` que no es la plantilla (`ob_s2.xlsx`) | 2 | 2 | 1 | 2 | **Error 422:** «no tiene la hoja PRESUPUESTO: no parece un presupuesto de la plantilla de la empresa» |
| D. A o B con un `.csv` | 1-2 | 0-1 | 1 | 1-2 | Rechazo: «Solo se aceptan archivos .xlsx» |
| E. `rita`: Revisar un paquete → pestaña «Presupuesto en Excel» → soltar el **mismo libro limpio** | 1 | 1 | 1 | 1 (pestaña .silice o Excel) | **Error 422:** «falta la hoja 'Datos'» (otro formato, el UC-05) |

Dónde se rompe: a la primera salida del formato. La empresa acepta hoy exactamente dos formas de libro, y cada una por
una puerta distinta (`libros`: plantilla de la empresa; `revisar › Presupuesto en Excel`: formato UC-05 con hoja
`Datos`); el mismo archivo pasa por una puerta y no por la otra. El camino feliz es corto (2 clics y 1 archivo), pero
termina en una hoja de cálculo que Sílice «muestra tal como está» con la lista de hallazgos al lado, sin un informe
que diga qué corregir primero.

## 3. Hallazgos

### MAYOR

- **H-1. Solo se lee un formato de libro.** `adapters/hoja_empresa/lector.py:733` exige la hoja `PRESUPUESTO` y los
  APU `APU-nn` de la plantilla ARENAZA. Con `ob_s2.xlsx` (camino C) la API contesta 422 en 2 s y la persona se queda sin
  nada. `leer_libro(datos, nombre, perfil)` ya recibe un `Perfil` (`lector.py:~703`): el punto de extensión existe.
  Choca con la petición «aceptar cualquier archivo».
- **H-2. Dos lectores, dos formatos, dos puertas para lo mismo.** `api/rutas/revision.py:572` (`/v1/revision/excel-externo`)
  falla con «falta la hoja 'Datos'» (`core/catalog/precios.py:244`) ante el libro que `libros` acepta, y al revés. La
  persona no puede saber cuál usar; el error no lo orienta.
- **H-3. El resultado no es accionable.** Con el libro limpio, el panel muestra «Hallazgos (2)» de nivel Información
  («R2 no aplicable…», «R7 no aplicable…», «Sin celda»). No hay resumen de qué hacer, orden por impacto en Bs/USD,
  exportación ni siguiente paso; la hoja ocupa la mitad del ancho y es la protagonista (`frontend-desktop/src/visor/Visor.tsx`).
  Las reglas «no aplicable» se muestran como hallazgos en lugar de como controles omitidos.
- **H-4. Duplicados y ruido en el menú.** «Libro de la empresa» aparece dos veces (herramienta principal,
  `rutas.ts:292-293`, y área Auditar, `rutas.ts:229`) e «Inicio» dos veces seguidas (rótulo del área y su única entrada).
  A 768 px de alto, el menú de `ana` (5 áreas) no cabe: «Crear» queda cortada y «Producción»/«Más» ya no se ven sin
  desplazar el menú.
- **H-5. Auditar está repartido por rol y por pantalla.** Audita `ana` (arma) y `rita` (revisa) en `libros`; solo `rita`
  tiene `revisar`; `admin` ve 6 pantallas y no puede auditar (Inicio le dice «pídale a otra cuenta», `inicio/index.tsx`).
  Tres rutas (`libros`, `revisar`, `historial`) responden a una misma pregunta de la empresa.
- **H-6. El caso y el proyecto los elige la persona, y el de omisión no sirve.** Todas las pantallas muestran
  «Caso silice.db / Proyecto: Sin proyecto» aunque la carpeta tiene `demo`, `of001`, `ti001`, `s1` y `obra_control`;
  `silice.db` es el caso vacío por omisión. Pide una decisión que la empresa no quiere tomar y que, si se ignora, deja
  la auditoría guardada en un caso sin contexto.
- **H-7. «Guiado» frente a «por mi cuenta» es una decisión sin diferencia visible.** `inicio/index.tsx:76-79`: dos
  botones tras subir el archivo; el recorrido guiado cambia lo que se verá después, pero el texto no lo dice.

### MENOR

- **H-8. Una ruta sin permiso deja la pantalla sin h1.** 68 de 68 mediciones de rutas fuera del menú del rol muestran
  «Sin permiso» (`Shell.tsx:65`, `EstadoVacio`) sin encabezado de nivel 1; un lector de pantalla no anuncia dónde está.
  El menú oculta bien lo prohibido; esto solo afecta a quien entra por enlace.
- **H-9. Texto obsoleto en «Libro de la empresa».** `Visor.tsx:336` dice «La fecha de devolución (en la barra de
  arriba)», pero el campo está en el cuerpo de la página, justo encima (visible en las capturas a ambos anchos).
- **H-10. Contraste insuficiente en `administracion`** (axe `color-contrast`, serious, 1 nodo, a 1366 y 1056) y región
  desplazable sin foco por teclado en `inicio` de `rita` a 1056 (`scrollable-region-focusable`). Ambos son A/AA.
- **H-11. A 1056 px el menú ocupa 264 px fijos (25 %).** No se pliega; la zona de trabajo queda en ~790 px. No hay
  desbordamiento, pero el visor y su lista de hallazgos se aprietan.
- **H-12. Páginas muy largas sin estructura corta:** `componer` (2008-2082 px) y `administracion` (1751 px) son
  desplazamientos largos sin pestañas ni índice; las demás caben casi siempre en una pantalla.
Sin hallazgos: errores de consola o de red en 132 pantallas (los 422 del flujo son esperados), desplazamiento
horizontal a 1056 px, más de un h1 por pantalla, tiempos de carga.

## 4. Propuesta de adaptación (ninguna pantalla se retira)

**Idea:** una vista única «Auditar un presupuesto» que es la ruta `libros` renombrada (la URL `/libros` se conserva) y
que absorbe las otras puertas de auditar. Lo demás sigue existiendo, con otro lugar.

| Pantalla actual | Qué pasa | Dónde queda |
|---|---|---|
| `libros` «Libro de la empresa» | **Se reubica y se renombra** en «Auditar un presupuesto»; deja de ser entrada propia con el nombre del libro | Área Auditar, primera entrada y única herramienta principal de auditoría |
| Zona «Audite un presupuesto» del Inicio | Se conserva como atajo: soltar el archivo y se audita, sin la pregunta guiado/propio (un solo botón; el recorrido guiado pasa a un enlace «Ver el recorrido») | Inicio |
| `revisar` › pestaña «Presupuesto en Excel» | **Se fusiona:** misma API de auditoría, el lector detecta el formato (UC-05 con `Datos`, plantilla de la empresa, genérico); la pestaña queda con un enlace a la vista única | Revisar un paquete |
| `revisar` › pestaña «Paquete .silice» | Sin cambios (otro objeto: el paquete del contratista) | Área Auditar |
| «Libro de la empresa» como idea | **Se rebaja a contexto opcional** dentro de la vista: panel plegado «Contexto (opcional)» con el libro de referencia de la empresa, la lista de precios, la fecha de devolución y el caso/proyecto | Panel dentro de la vista única |
| `historial` | Se muestra como panel «Auditorías anteriores» dentro de la vista; la ruta se conserva | Área Auditar y panel de la vista |
| Selector de caso en la cabecera | Elige solo según el archivo y el contexto (dominio detectado por el adaptador); queda manual bajo «Más opciones» | Cabecera / contexto |

**Menú resultante (por rol):**

- *Herramientas principales (3, sin duplicar):* Auditar un presupuesto · Componer una partida · Existencias de la arenera.
- *Áreas:* **Inicio** (una sola entrada, sin repetirla como rótulo y como herramienta) · **Auditar** (Auditar un
  presupuesto, Historial, Revisar un paquete) · **Crear** (sin cambios) · **Producción** · **Más**.
- Permisos sin cambios: lo que ve `admin` (hoy no audita) es decisión de Eugenio; esta propuesta no toca seguridad.

**Cómo debe leerse cualquier archivo (H-1, H-2):** un despachador que prueba, en orden, plantilla de la empresa →
UC-05 → formato genérico (cabeceras tipo código/descripción/unidad/cantidad/precio unitario) usando el `Perfil` que
`leer_libro` ya acepta; solo si falla, un mapeo guiado de columnas (1 paso extra). Los APU se calculan en segundo
plano: la lista de partidas aparece de inmediato y cada partida se completa con su estado.

**Informe accionable (H-3):** arriba, cuánto dinero está en juego y cuántos hallazgos hay por severidad; después las
partidas ordenadas por impacto en Bs/USD, cada una con celda, valor del libro, valor de Sílice, diferencia y la acción;
reglas «no aplicable» en un pie «Controles omitidos»; exportar a Excel/PDF. La hoja del libro pasa a vista secundaria
(se abre al elegir un hallazgo).

**Flujo objetivo:**

| | Hoy (camino feliz, solo plantilla) | Objetivo |
|---|---|---|
| Pasos | 6 (pantalla, decidir, soltar, decidir, clic, leer) | 2: soltar el archivo → leer el informe |
| Clics | 2 | 0-1 |
| Decisiones obligatorias | 2 (+ fecha, caso, proyecto, dominio en la sombra) | 0 (fecha = hoy, caso y dominio automáticos, contexto opcional) |
| Archivos aceptados | 1 formato, por la puerta correcta | cualquier `.xlsx`; error solo si no hay nada que leer |
| Caso de fallo | 422 sin salida | mapeo guiado (+1 paso) |

## 5. Orden sugerido (cada paso se verifica repitiendo el recorrido)

1. Despachador de formatos y lector genérico (H-1, H-2): lo único bloqueante; backend, requiere pruebas y probablemente expediente de `adapters/`.
2. Vista única: renombrar `libros`, mover el contexto a un panel, un botón en el Inicio (H-5, H-6, H-7).
3. Informe accionable y «controles omitidos» (H-3).
4. Menú sin duplicados (H-4) y limpieza de H-8, H-9, H-10.

## 6. Límites y pendientes de la herramienta

- «Alto» es el del documento, no el del contenido de un contenedor con desplazamiento propio. Falta medir el
  `scrollHeight` del contenedor principal para saber cuánto hay que desplazar en cada pantalla.
- Solo se auditó con libros ficticios de tres clases (plantilla, `.xlsx` ajeno, `.csv`); falta un conjunto de formatos
  ajenos realistas (de otras herramientas) para probar el despachador de la propuesta.
- El navegador es el Chromium de Playwright en modo sin interfaz; no prueba teclado ni lector de pantalla reales.
  axe cubre una parte de WCAG; contraste en tema oscuro y el foco visible quedan para la revisión manual.
- Se probó con tres cuentas ficticias; el modo entrega (`SILICE_MODO_ENTREGA=1`) y el recorrido guiado no se recorrieron.
- Dato de entorno: sin `-u` y con la salida redirigida, Python bufferiza y la consola parece muda 10 minutos; el
  script ya imprime una línea por pantalla, pero conviene correrlo con `python -u`.

Capturas y JSON de la corrida: carpeta de salida del scratchpad (`recorrido_ux/`, `recorrido_ux_flujo/`); no se
versionan.
