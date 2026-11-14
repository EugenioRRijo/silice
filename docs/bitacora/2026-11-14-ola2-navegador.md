# Pasada en navegador de la ola 2: correcciones (2026-11-14)

Rama `feature/ola2` (PR #109), árbol `.worktrees/s2m4`. La pasada en navegador del 14/11 (Edge por Playwright, a 1366 y
a 1056 px, siembra ficticia) dejó doce defectos, D1 a D12. Aquí van las decisiones, las simulaciones y los commits de
cada uno. Todos los datos son ficticios: el libro de `tests/fixtures/libro_apu_por_hoja.py`, el caso OF-001 y los CSV
inventados por el probador. `core/` no cambia (`git diff e2dfe116 --stat -- core/` vacío) y no se tocó ningún archivo
congelado del experimento.

| # | Defecto | Estado | Commits (rojo → verde) |
|---|---|---|---|
| D1 | La «Cantidad» se pintaba sobre la «Descripción» fija | hecho | `e34c54e6` → `67b3a803` |
| D2 | «Desperdicio (%)» cortado a 1366 | hecho | `925e34b9` → `7e1bd3f4` |
| D3 | PDF: palabras partidas, «0 /%», m2, APU sin neta ni % | hecho | `2d74751b` → `41576713`; `b2f32737` → `4bd878ab` |
| D4 | «póngalo abajo» sin nada abajo | hecho | `dcaa0b3e` → `1bea338f` |
| D5 | Los selectores de renglón no nombran el frente | hecho | `8b952062` → `81933ba9`; `dcaa0b3e` → `1bea338f` |
| D6 | Componer no carga un código con «/» (MAYOR) | hecho | `32d0505d` → `896e46d6` |
| D7 | Mensaje con un id interno («insumo 153») | expediente (núcleo) | — |
| D8 | Mensaje sin tildes («mas», «dias») | expediente (núcleo) | — |
| D9 | Precios de la empresa: otra unidad, botón en otra moneda, nombres repetidos | hecho | `1e9a7f40`, `87e919c2` → `f4691185` |
| D10 | Llevar el libro pierde la traza del desperdicio (MAYOR) | hecho | `743517e2` → `580cb2c5` |
| D11 | El borrador llevado no se recupera al volver a entrar | hecho (aviso y enlace; ver la causa) | `629e33a7` → `fa35c2be` |
| D12 | El texto de la zona de subida se oye dos veces | hecho | `00bbbbb1` → `84ccf069` |

## D6 (MAYOR) · un código con «/» en las rutas

**Causa.** La interfaz codifica la «/» (`encodeURIComponent`, «AF-CODO-1%2F2») y Starlette la decodifica antes de
enrutar. Sin `:path`, `{codigo}` no casa con un texto que tiene «/» y la respuesta era el 404 genérico de FastAPI
(«Not Found»), aunque el contrato de la precarga es «nunca 404». La Hoja ya usaba `{partida:path}`.

**Qué se hizo.** `api/rutas/composicion.py`: `GET /v1/composicion/partidas/{codigo:path}`. Al revisar las demás rutas,
las cuatro del estudio de mercado tenían el mismo defecto con un código de partida o de insumo
(`/{lado}/{codigo}`, `/compra/{codigo}/afectados`, `/compra/{codigo}/usar`, `/cobro/{codigo}/usar`); llevan `:path` y
«afectados» se registra antes que `/{lado}/{codigo:path}`, que también casaría con `/compra/X/afectados` (Starlette toma
la primera ruta que casa). El cliente ya codificaba bien en los dos sitios (`componer/cliente.ts`, `mercado/logica.ts`);
las demás rutas del cliente con un segmento variable llevan ids numéricos. `docs/api.json` reexportado.

**Medido en el navegador.** Componer de OF-001 con «AF-CODO-1/2 … con composición»: las tablas se cargan (codo PVC 1/2,
pieza, 1; pegamento…), sin ningún 4xx de `/composicion`.

## D10 (MAYOR) · la traza del desperdicio al llevar el libro

**Causa.** `fusion.apu_por_hoja` lee la traza («0,5 + 4 %») y la usa en el informe, pero `ApuRecalculado` y
`libro_a_la_hoja.ApuDelLibro` no la llevaban: la composición entraba al catálogo con la cantidad bruta (0,520) y sin
traza, así que la Hoja y Componer mostraban 0,520 con el porcentaje vacío.

**Simulación** (guion `sim_d10.py` en la carpeta de la sesión, con las funciones reales: `con_desperdicio` para
Componer, `trazas_de_las_filas` para la Hoja, `calcular_apu` para el P.U. y `con_desperdicio_en_materiales`, la regla de
E6, para «quien arma escribe 4 en el %»). Libro ficticio, VF-001, emulsión 0,50 l + 4 % a 2,00; P.U. impreso 2,08.

| Opción | Componer | Hoja (campos) | P.U. del catálogo | Si se escribe 4 % en la Hoja |
|---|---|---|---|---|
| **1. La traza entra con la composición** (como Componer) | 0,5 + 4 % | 0,5 y 4 | 2,0777625 → 2,08 (casa) | 0,520 y 2,08: nada cambia |
| 2. La neta al catálogo y el % solo al borrador | 0,50 sin % | 0,50 sin % | 2,0271625 → 2,03 (no casa) | 0,52 en el borrador; el catálogo sigue mal |
| 3. Dejar la bruta y avisar (hoy) | 0,520 sin % | 0,520 sin % | 2,08 | **0,5408** y 2,13: el desperdicio dos veces |

**Decisión: opción 1.** Es la regla de Componer (la traza se escribe en la misma transacción que la composición del
catálogo, `guardar_trazas`) y la del diseño del presupuesto vial (§4, opción B: la neta y el porcentaje como traza
junto a la cantidad que multiplica el precio). La 2 deja el catálogo con un precio que no es el del libro; la 3 es el defecto.

**Qué hace.** `ApuRecalculado.trazas` y `ApuDelLibro.trazas` llevan la traza de cada hoja; `api/rutas/hoja_libro.py` la
pasa; `aplicacion/libro_a_la_hoja._trazar` la escribe con la composición nueva y, si el código ya estaba con la misma
composición, la une a la vigente (`hoja_desperdicio.unir`): llevar otra vez no escribe otra traza. Una variante «-B»
lleva la suya. Sin `commit` propio: va con el catálogo y el rollback de siempre la deshace.

**Cómo revertirla.** Quitar `_trazar` y los dos campos `trazas`. **Medido en el navegador:** tras llevar el libro, la
Hoja de VF-001 muestra Cantidad 0,5, Desperdicio 4 y «Cantidad con desperdicio» 0,520; Componer precarga 0,5 + 4; el
PDF del APU dice «0,5 4 0,520 2,00».

## D3 · el PDF

**Simulación** (guion `sim_d3.py`: `Paragraph.wrap` de reportlab con la letra Vera a 7,5 pt y los códigos de OF-001
que se vieron en la pasada; una celda «parte una palabra» si alguna línea corta a media palabra y no en un guion).

| Opción | Códigos partidos a media palabra | «unidad» partida | «0 %» separado |
|---|---|---|---|
| A. Hoy (Código 2,3 cm, Unidad 1,3 cm, espacio normal) | 7 de 20 | 1 de 8 | 1 de 5 anchos |
| B. Solo partir en el guion (`embeddedHyphenation`) | 3 de 20 | 1 de 8 | 1 de 5 |
| **C. Anchos nuevos (3,0 y 1,5 cm) + guion + espacio duro** | **0 de 20** | **0 de 8** | **0 de 5** |

**Decisión: C.** Los anchos salen de los montos, que se ciñen (Precio unitario 2,9 cm, Total 2,8 cm); como sus
encabezados ya no caben en una línea, los encabezados de las tablas pasan a ser párrafos y se parten en su columna en
vez de pisar la vecina («Precio unitario / (USD)»; dos pruebas viejas que buscaban la frase en una línea ahora buscan
«Precio unitario»). El número y su «%» van con espacio duro (U+00A0, que reportlab no parte). Las unidades se escriben
como en la interfaz (`comun/unidades.ts`: m2 → m², m3 → m³, dia → día; solo al presentar). Con la traza del desperdicio,
el APU del PDF lleva las columnas de la pestaña APU («Cantidad» es la neta, «Desperdicio (%)» y «Cantidad con
desperdicio»); la ruta del PDF lee la traza vigente de la base, como la vista del APU. Alternativa descartada: una sola
columna «0,5 + 4 %»: más corta, pero distinta de la pestaña que la persona ya conoce.

## D1 y D2 · la tabla del APU a 1366

**D1.** La celda fija (`position: sticky`) no tenía `z-index` y el contenedor del campo de Carbon es `position:
relative`: lleva `z-index: 1`. Medido: con la tabla desplazada 200 px, `elementFromPoint` sobre la columna fija da la
celda fija en los tres puntos.

**D2. Simulación** (guion `sim_d2.py`: en la página servida se inyecta cada opción y se mide si la cabecera
«Desperdicio (%)» queda entera dentro de la región en reposo).

| Opción | Región central | ¿«Desperdicio (%)» entera? |
|---|---|---|
| A. Hoy (lista 14rem, cierre 18rem) | 400 px | no (empieza a 340, termina a 469) |
| B. Rótulo corto «Desp. (%)» con nombre accesible completo | 400 px | no: la columna empieza a 340 por el campo de la cantidad |
| C. Cabeceras en dos líneas | 400 px | no (ya iba en dos líneas) |
| E. Lista 12rem y cierre 15rem | 493 px | sí, pero el cierre corta más su «Nota» |
| F. Lista 12rem + rótulo corto | 437 px | no por un píxel |
| H. Lista 11rem y cierre 17rem | 475 px | sí, pero a 11rem el buscador de partidas corta su texto de ayuda (captura) |
| **I. Lista 12rem y cierre 16rem** (el mismo ancho total que H) | 475 px | **sí**, sin abreviar (medido tras el cambio) |

**Decisión: I.** Sin abreviaturas (nombre visible igual al accesible, que es lo que recomienda WCAG 2.5.3) y sin
cambiar el orden canónico de las columnas del APU (descripción, unidad, cantidad…). Bajo 75rem las tres columnas ya se
apilan (a 1056 la región mide 743 px). Medido: a 1366 la cabecera termina a 469 px de una región de 475.

## D4 y D5 · los frentes

**D4.** «Ningún renglón tiene frente: póngalo abajo…» solo cuando abajo está el selector (quien edita y hay renglones
propios). Sin renglones propios (los que salen del espacio de la obra no cambian de frente, `frentes.poner_frentes`):
«Los renglones que salen del espacio de la obra no llevan frente a mano: para agruparlos, lleve a la Hoja un libro con
una hoja de presupuesto por frente». Quien solo lee: «Ningún renglón tiene frente.».

**D5.** El renglón de la vista del presupuesto (`FilaDePresupuesto.frente`) y el del contrato
(`PartidaDelContrato.frente`, leído de las especificaciones guardadas del renglón) traen su frente. El selector de
«Poner el frente» dice «1. VF-001 (FRENTE A) · Riego…»; el de Valuaciones, «renglón 3 del presupuesto, frente «FRENTE
B»», y la observación que se escribe sola, «Renglón 3 (frente «FRENTE B»)». La valuación sigue siendo por código
(núcleo). No se agregó la columna del frente a la tabla de Partidas (no la pedía el encargo). Medido: las cuatro
opciones del libro ficticio nombran su frente.

## D9 · precios de la empresa

- **(a)** Un insumo que el catálogo tiene con otra unidad iba a la vez en «Otra unidad» y en «Insumos desconocidos: no
  están en el catálogo». Ahora `desconocidos` son solo los que el catálogo no tiene (`_separar` después del alta). Dos
  pruebas viejas esperaban la contradicción y se corrigieron.
- **(b)** El servidor dice en la respuesta la moneda de la lista y, si la carpeta trabaja en otra, por qué no puede ser
  su lista para armar (`aviso_para_armar`, la regla de `listas_para_armar._desde_empresa`); la página muestra ese texto
  en vez del botón, como ya hacía con el aviso de quien no arma. Opciones simuladas en el navegador: botón que da el 409
  al pulsarlo (hoy), botón deshabilitado (no dice por qué) y **texto en vez del
  botón** (elegida).
- **(c)** Dos listas del mismo día sin nombre se llaman «… 2026-11-14» y «… 2026-11-14 (2)», la convención que ya usa la
  lista para armar (`_nombre_libre`) y la de Excel y Windows con las copias. Descartadas: la hora en el nombre (menos
  legible) y rechazar el segundo con un 409 (fricción sin ganancia).

Medido: dos listas en Bs sobre s1 (USD): «Constructora Ficticia, C.A. 2026-11-14» y «… (2)»; sin botón y con el aviso;
ARENA LAVADA solo en «Otra unidad».

## D11 · el borrador llevado al volver a entrar

**Causa (no es propia de llevar el libro).** El borrador vivo, como todos, vive en memoria del servidor ligado a la
huella de la ficha de sesión (`aplicacion/hoja_borradores.py`, diseño §3.1, costo declarado D-2). Volver a entrar desde el
mismo navegador cierra la ficha anterior y olvida sus borradores (`api/rutas/sesion.py`, `caso_web.olvidar` al entrar y
al salir). En la misma sesión la Hoja ofrece «Retomar borrador» (lo vio el probador y se volvió a medir); en otra, ningún
borrador vivo sobrevive. Hacerlos persistir es un cambio de diseño (y `aplicacion/hoja.py` está congelado).

**Qué se hizo.** El aviso de éxito lo dice («Un borrador sin guardar se pierde al salir de Sílice; si se perdió, vuelva a
llevar el libro: no duplica nada», que es cierto: el catálogo se reutiliza y los renglones de las mismas hojas se
reemplazan) y debajo va el enlace «Abrir la Hoja de «obra»» a `#/hoja`, la dirección corta que abre la Hoja de la obra de
la sesión (la misma a la que se llevó). Carbon no admite controles dentro de un aviso en línea: el enlace va justo debajo.
Opciones: guardar una versión automáticamente al llevar (descartada: la persona debe revisar antes, y el módulo dice «no
guarda versión»); persistir los borradores (fuera del alcance). Medido: el enlace lleva a `#/obra/demo.db/1/presupuesto`
y la Hoja ofrece «Retomar borrador».

## D12 · la zona de subida

Carbon pinta la etiqueta en el botón y otra vez en un `<label>` oculto del `<input type="file">` (tabIndex −1, solo lo
abre el botón). `SubidaArchivo` pone `aria-hidden` en ese `<label>` y en el campo: queda un solo texto accesible, el del
botón, y el «botón sin texto» del perfil (el campo de archivo) sale del árbol. El archivo sigue llegando por el mismo
campo. Opciones: reescribir la zona sin Carbon (más código y se pierde el arrastre probado) o `display: none` en el
`<label>` (no quita el campo del árbol). Medido: las tres zonas de Auditoría tienen la etiqueta una sola vez fuera de
`aria-hidden`.

## D7 y D8 · expedientes propuestos para `core/` (no se tocó)

**D7 · `core/catalog/empresa.py:99` (`_validar_propios`).** Hoy: «insumo 153: precio en Bs sin tasa a USD».
- *Regla:* el mensaje nombra el insumo por su descripción (y su código), no por el id interno: ««ARENA LAVADA»
  (MAT-0027): precio en Bs sin tasa a USD; escriba la tasa en la fila o cree la lista en Bs». Lo mismo en la línea 95
  («dos precios propios para el mismo insumo»).
- *Por qué es genérico:* vale para toda lista de empresa, de cualquier especialidad; el id no es un dato que la persona
  vea en ninguna pantalla.
- *Prueba en rojo propuesta:* en `tests/unit/test_catalogo_empresa*.py`, un `PrecioPropio` en Bs sin tasa sobre una lista
  en USD: `pytest.raises(ValueError, match="«Insumo ficticio»")` y que el texto no contenga `insumo <id>`.
- *Impacto:* `_validar_propios` necesita la descripción (un `session.get(models.Insumo, …)` o que `PrecioPropio` la
  lleve); ningún contrato cambia. Además, la revisión previa (`aplicacion.precios_empresa.revisar_archivo`) podría avisar
  antes de crear (fuera del núcleo, se puede hacer sin expediente).

**D8 · `core/catalog/indices.py:180`.** Hoy: «la tasa venta mas reciente es del …, 44 dias antes … con mas de 7 dias
naturales sin tasa…».
- *Regla:* el texto con sus tildes: «la tasa venta más reciente es del …, 44 días antes … con más de 7 días naturales sin
  tasa no se convierte (S1-R2)».
- *Por qué es genérico:* es el mensaje de toda conversión con el BCV.
- *Prueba en rojo propuesta:* en la prueba de `tasa_aplicable` con una tasa de hace 8 días, `match="más reciente"` y
  `match="8 días"`.
- *Impacto:* solo texto; buscar las pruebas que comparen el mensaje sin tildes (`grep "mas reciente" tests/`) y la ayuda
  que lo cite.

## Lo que no se hizo y por qué

- N1 (subtotales redondeados que no suman el total) y N2 (la tabla del índice en USD muestra primer y último mes) son
  notas, no defectos: no se tocaron.
- La Hoja escribe «m3» en la columna Unidad del APU (no «m³»): no estaba en el encargo; el PDF ya lo escribe como la
  interfaz de Tramos.
- La tabla de Partidas no muestra el frente de cada renglón (D5 lo mencionaba de paso).

## Cómo se re-midió

El `dist` se compiló en una copia (`npx vite build --outDir <carpeta de la sesión>/dist`), servido por `api.main:app`
en 127.0.0.1:8772 con datos sembrados en esa carpeta (`plantilla_con_cuentas` + `start.preparar_demo`, la cuenta mixta
del probador), Edge por Playwright. Guiones `remedir_libro.py` y `remedir_hoja.py` (a 1366 y a 1056): cada pantalla con
un h1, sin desbordamiento horizontal, sin controles sin nombre, sin errores de consola ni peticiones fuera de 127.0.0.1.
El árbol no se compiló.
