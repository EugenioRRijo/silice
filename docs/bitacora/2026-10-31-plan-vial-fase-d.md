# Plan vial, fase D: pedidos transversales y cierre (Tareas 16b a 22)

Rama `inc/vial-agregados` (worktree `.worktrees/s2madm`). La fase C se cerró en c15ceffc. Las decisiones tomadas en
ausencia de Eugenio están en `docs/bitacora/2026-10-30-preguntas-para-eugenio.md` (filas 106 a 116) y en los archivos
aparte de las Tareas 17 a 21 (`2026-10-31-preguntas-t17-fcas.md`, `-t18-iva.md`, `-t19-modulos.md`, `-t20-consulta.md`
y `-t21-reportes.md`). `core/` intacto: `git diff --stat c1f436b2 -- core/` vacío.

| Tarea | Commits | Árbitro |
|---|---|---|
| 16b Respuestas de Eugenio (filas 27, 51, 58) y menor 1 del cierre C | d9d96e86, b303086c, 3bf293b3, 72cffe74, 2cfdaf7c; docs 673c44ab, 4b0b3bbf | sus menores quedaron en las filas 34 y 109 (4b0b3bbf); el MENOR 2 (instalación ilegible con `OSError`) se hizo en la Tarea 22. El veredicto no quedó anotado en una bitácora |
| 16c El ligante marcado en la receta | 9c04f881 (solo el plan) | sin construir: va después de la entrega de prueba (fila 109) |
| 17 FCAS por componentes | 7f53bc6f, 815c533f; r2 37e7b053, 9751f91c; unión 7f33a904 | devuelta r1, aprobada r2 (paro forzoso, FAOV e INCES «a cotejar», T17-7) |
| 18 IVA sobre presupuesto y valuaciones | 4df50554, a40e6860; r2 18448cbb, 43bf4518; unión bd10d247 | devuelta r1, aprobada r2 (columnas en el control y aviso de la perspectiva costo, T18-3) |
| 19 Especialidades y módulos activables | f2ab57e9, 6f7911ac; r2 0b8c269c, b7df8dd3; unión e37ad7d4 | devuelta r1, aprobada r2 (edificación oculta planos y espacio; módulo después del acceso en vial, T19-5 y T19-7) |
| 20 Autocompletado con tablas venezolanas | fbbe0fc5, 5d0d45a3, 5f98617d; unión 6a042528 | aprobada r1, con menores hechos en 5f98617d |
| 21 Reportes | 8f77f0c0, 18913e55; unión 88d29ebc; 8435b331 | aprobada r1; al unirla con la 19, los reportes viales también exigen el módulo vial (8435b331) |
| 22 Cierre, pasos 1 y 2 | c6cc004b, 5f50477f, e49976b0, b6db8d4e y el de esta bitácora | pendiente (el orquestador corre la suite, la medida del núcleo y el navegador) |

## Tarea 22, paso 1: de punta a punta por la API

`data/samples/produccion/` es una cantera y una planta **ficticias**, declaradas así en su README, que trae la memoria de
cálculo a mano: materiales (`PC-19`, `AR-01`, `MZ-C`), producción de octubre y noviembre de 2026, costos por centro en
USD y en Bs, la receta, lo que la planta compra, las series (tasa BCV, PPI del asfalto y gasoil, 25 meses), los APU tal
como se teclean en «Componer» y la vía (`via.csv`).

`tests/integration/test_vial_extremo_a_extremo.py` (e49976b0) lo recorre todo por la API, con las cuentas de la
plantilla: materiales, movimientos, receta, producciones y costos (ana); el cálculo sin la tasa del 06/10 se niega
nombrando el costo (foco 1); el administrador importa las series por `/v1/indices` y publica los dos cálculos; ana
compone los APU, crea la obra, guarda V-001 desde la Hoja en blanco, importa la vía y la **lleva** con
`POST /v1/vial/tramos/llevar` (ni `derivar_tramos` ni un `origen_id` escrito en la prueba); la auditoría muestra
VR2, VR3 y VR6 (diseño de la vía) y, al escribir a mano tres cantidades, VR1, VR4 y VR5; corrige y guarda V-002;
luego la conciliación (CV3 en el reporte del APU), la proyección, la comprobación, la mejora y los seis reportes.
Fuera de la API solo quedan las cuentas y la primera lista de la carpeta (fila 113).

Oráculos a mano (todos coincidieron a la primera con lo que dio el sistema):

- Costo por tonelada: octubre 6 USD/t los agregados y 49,70 la mezcla; noviembre 7 y 51,65.
- Cantidades: 16 renglones; 840 t de mezcla en T1, 8.400 t·km de transporte en T2, 73 l de pintura en T1.
- V-001: 2.530 (2.000 × 1,265). V-002: costo directo 110.101,40, total **139.278,271**; con IVA: 139.278,27 +
  22.284,52 = **161.562,79**.
- CV3: la base granular usa la piedra a 6 (octubre) y el último cálculo publicado, n.º 2, dice 7.
- Riesgo: P50 = P80 = **159.666,1091212**, reserva 20.387,8381212 (todo de la mezcla), 24 meses usados;
  comprobación: **7 cortes**, cobertura 100 %.
- Mejora con un real inventado de 160.000: 12,95 %, 0,21 % y **12,74 puntos**.

La prueba no añade código de producto, así que entra en verde; se comprobó que discrimina por mutación: con la pintura
por defecto (V-17) en 40 en vez de 36,5, falla (80 ≠ 73); con la mezcla sin escalar en la proyección, falla (P80 = total
base). Tarda unos 13 s.

## Tarea 22, paso 2: menores agrupados

Hechos, cada uno con su rojo antes del arreglo:

- **R11 de TI-001 dependía del reloj** (c6cc004b). `test_r11_los_hallazgos_son_los_de_la_memoria[TI-001]` veía R12 (precio
  vencido) según el día. La prueba toma `_hoy_fijo` (06/10/2026) y `POST /v1/hoja/borradores` abre la versión con
  `_hoy()`, como el resto de la ruta, en vez de `date.today()`. Rojo: `{'R11', 'R12'} == {'R11'}` con la fecha fija y la
  ruta aún con el reloj. Vecinas de la Hoja y de llevar (nueve archivos, unas 400 pruebas) en verde. Fila 115.
- **MENOR 2 del árbitro de la 16b** (5f50477f). Con una instalación que el sistema no deja leer (`OSError`), la excepción
  subía y la Hoja no abría, aunque la prueba se llamaba «…y la hoja abre» (solo probaba la regla, con
  `OperationalError`). Ahora `formulas_de_trabajo` atrapa `SQLAlchemyError` y `OSError`, y la prueba abre de verdad la
  versión con `hoja.abrir_version` en los dos casos; VR2 lo declara como INFO. Rojo: `PermissionError` sin atrapar.
  `aplicacion/hoja.py` no cambia (el comentario viejo de la línea 1915 sigue bajo el congelado, fila 110). Fila 116.
- **Los reportes no tenían pantalla** (b6db8d4e). «Tramos de la vía» ofrece «Reportes en Excel» (cómputos por tramo, APU
  con origen y conciliación, resumen con IVA) con la obra y la versión que se ven; «Riesgo de la obra», «Descargar el
  informe de riesgo» con lo mismo que se proyectó. Rojo: 1 de 18 y 1 de 6 en Vitest; verde 18 de 18 y 6 de 6;
  `npm run lint` limpio. Fila 112.
- **Frase del plan de la Tarea 21** (T21-1): la Tarea 21 dice «857,75 t del tramo T1», que es el T1 de
  `test_vial_derivacion.py`; queda corregida en el plan.

Quedan (anotados, sin cambio):

- Sin pantalla: el reporte de costo de producción y el de mejora; la mejora misma (Tarea 15) no tiene pantalla. Fila 112.
- **La trazabilidad del costo propio se corta en «Componer»** (fila 114): el precio de la mezcla que teclea una persona
  queda como «derivada de la lista…», sin n.º de cálculo; CV3 sí compara con el último publicado. No es un menor.
- R11 escribe «1 insumos no contrastables»: el texto está en `core/verification/precios.py` y `core/` no se toca.
- El IVA del presupuesto sigue sin pantalla (T18-5): Eugenio decidió mostrarlo en la sección Presupuesto del F4.
- Seis pruebas de `test_api_carpeta` esperan la fecha de hoy y fallan si la suite cruza la medianoche (fase A); la de
  `CostosDelPeriodo` de Vitest se cae por tiempo solo bajo carga (el tope global ya es 20 s).
- `scripts/meta_datos.py` D1 falla desde antes de esta tarea por frases de `docs/especificaciones/` y del plan vial que
  nombran «datos reales» sin la marca que lo desmiente. La muestra nueva no añade ninguna (se reescribió su frase).
- Lo anotado sin cambio en las fases B y C (herencia de tramos por consulta, VR6 con una sola vía por obra, matriz de
  detección con VR solas) sigue igual.

## `test_huellas_rnf04::test_huella_del_contenido_del_libro` (investigado, sin cambio)

Falla desde antes de la rama y **no es un cambio del producto**: es el entorno. La `.venv` compartida
(`C:\Users\euger\OneDrive\Escritorio\TESIS\.venv`) trae `lxml` 6.1.3, que no está en `uv.lock`: lo instala
`python-docx` (también fuera del lock). Con `lxml` presente, openpyxl escribe el XML del libro con otro serializador y
los bytes cambian; la huella de **contenido** del libro (que excluye `docProps/core.xml`) deja de ser
`386bca1c…`, la anclada en GC5 y GC6 (`docs/protocolo_rnf04.md` §1). La huella de pantalla (el `.md`) no cambia.
Comprobado hoy: con `OPENPYXL_LXML=False` las dos pruebas pasan (2 de 2) sobre esta misma cabeza. Coincide con lo que
ya diagnosticó el cierre de F2 (`2026-10-27-cierre-f2-marco.md`, punto 6) y el de F3. **No se re-ancla la huella**: el
producto genera el mismo libro en una `.venv` sincronizada con `uv.lock` (la de la CI). Arreglo del entorno: `uv sync`
para que la `.venv` vuelva a `uv.lock` (quita `lxml` y `python-docx`), o correr la suite con `OPENPYXL_LXML=False`. El
mismo `lxml` explica las tres de `test_excel_m1` que vio F2 (el retorno de carro sale como CR y no como LF).

## Para la entrega de prueba de mañana

- La laptop de Eugenio: si su `.venv` tiene `lxml`, el Excel exportado es equivalente pero sus bytes difieren; un
  retorno de carro dentro de una celda puede salir como CR (lo de `test_excel_m1`). No afecta las cifras.
- En la demo, el «APU con origen» de una mezcla compuesta a mano dirá «derivada de la lista…» y no el n.º del cálculo
  (fila 114): conviene decirlo antes de que lo pregunten.
- La comprobación hacia atrás tarda: unos 14 a 20 s con las 500 trayectorias por corte de la pantalla en una obra
  mediana, y cerca de 95 s si se suben a 2.000 (medido en la fase C). La pantalla avisa de la espera.

## Suite completa de la versión que se muestra el 2026-11-01 (sobre b8820ad3)

- Pytest (con `OPENPYXL_LXML=False`): 11.665 verdes y 2 rojas, ambas listas literales sin actualizar tras las merges (la ruta del reporte de producción en `test_api_produccion` y `METADATA_MODULOS` en `test_migraciones_metadatos`); corregidas y verdes. Vitest: 3.332 de 3.332. Lint: limpio. Las fallas antiguas (TI-001 por el reloj y la huella RNF-04 por lxml) ya no aparecen.
- F4 queda para una sesión posterior por decisión de Eugenio; la rama vial ya está unida a `inc/rediseno-f4`.

## Llevar en una obra que ya existe: bloqueo de la pasada de navegador (arreglado)

**Lo que se vio.** En la carpeta de demostración, «Llevar al presupuesto» de los 20 renglones de
`data/samples/vial/via_ficticia.csv` en DEMO-001 decía «Se llevaron 20 renglones», pero la auditoría de la Hoja daba
20 errores «PENDIENTE: … no tiene composicion de APU» y NO CUMPLE. Recomponer los APU con fecha 20/09/2026 no lo
cambiaba.

**Causa exacta.** La Hoja arma el APU de cada partida nueva desde el catálogo con **la lista de la versión abierta y a
la fecha de esa versión** (`hoja_edicion.cambiar_borrador` → `hoja.completar_composiciones(catalogo, borrador,
lista=lista_de_version)`), y si `Catalogo.composicion` lanza `CatalogoIncompleto` se lo calla y deja la partida
PENDIENTE. Para DEMO-001 eso es «Lista de referencia del caso de demostracion de Sílice», al 20/09/2026. Llevar, en
cambio, solo miraba que la partida existiera en el catálogo. Un APU compuesto en Componer con la fecha de hoy falla de
dos maneras:

1. **Rendimiento:** `composicion` pide un rendimiento estimado con fecha ≤ 20/09/2026, y el de la partida quedó con la
   fecha en que se compuso (en la carpeta del revisor, 01/11/2026). Volver a guardar con fecha 20/09/2026 **no**
   registra otro rendimiento si el valor y las condiciones son los mismos (`reemplazar_composicion` solo registra uno
   nuevo si algo cambió): por eso repetirlo «con los APU fechados el 20/09/2026» dio lo mismo. Comprobado sobre una
   copia de su `demo.db`: las 15 partidas, «no tiene rendimiento estimado al 2026-09-20».
2. **Precios:** Componer escribe los precios en la lista para armar de la fecha que se teclea, o en una derivada de esa
   fecha (`listas_para_armar.lista_de_hoy`): con fecha de hoy quedan en «… al 31/10/2026», no en la lista de DEMO-001.

La prueba de punta a punta pasaba porque cataloga las partidas directamente en la lista de su versión y a su fecha.

**Arreglo** (`aplicacion/hoja_vial.py`, sin tocar `hoja.py`, `composicion.py` ni `core/`): dentro del cerrojo del
borrador y antes de cambiar nada, llevar arma cada partida que el borrador aún no compone exactamente como lo hará la
Hoja (misma lista, misma fecha). Si alguna falla: `PartidasSinValorar`, 409, **no lleva nada** (el borrador abierto
para llevar se descarta; el que ya estaba no cambia) y el mensaje dice qué partidas, qué insumos faltan en qué lista y
en cuál están, qué rendimiento falta a esa fecha y qué hacer. Si todas se arman, llevar las deja compuestas: así,
llevar otra vez después de arreglar el APU compone la partida aunque los renglones no cambien (antes seguía
pendiente). Pruebas: `tests/integration/test_api_vial_llevar_valorable.py` (por la API, con Componer) y cuatro nuevas
en `tests/unit/test_aplicacion_vial_llevar.py`. `docs/api.json` no cambia.

Ronda 2 (MAYOR del árbitro, DRY): la primera versión copiaba la regla de la Hoja (un bucle de `catalogo.composicion`
y la elección de lista). Ahora la decisión es la de la Hoja misma: `hoja_edicion._completar` pasó a pública como
`hoja_edicion.completar` (misma conducta) y la elección de lista quedó en un único sitio,
`hoja_edicion.lista_para_completar`, que usan `completar` y llevar. `hoja_edicion.py` no está bajo el congelado
(`asistente/experimento/protocolo.json`, `archivos_del_auditor`); `hoja.py` sí y no se tocó. Llevar mira qué partidas
no salen compuestas de `completar`; `catalogo.composicion` y `_por_que` quedan solo para redactar el motivo. Dos
pruebas lo vigilan: si `hoja.completar_composiciones` o `lista_para_completar` cambian, llevar cambia con ellas.

**Lo que Eugenio debe preparar para mostrar Llevar en la carpeta de demostración (DEMO-001):**

- **La lista:** «Lista de referencia del caso de demostracion de Sílice» (USD), la de DEMO-001, vigente desde el
  20/09/2026. No hay que crear otra.
- **Las partidas:** las 15 de la vía, `C-000.000.001` a `C-000.000.015`, compuestas en **Componer con el campo Fecha en
  20/09/2026** (Componer trae la fecha de hoy: hay que cambiarla). Así sus precios quedan en esa lista y su rendimiento
  a esa fecha. Insumos y precios ficticios: los de `data/samples/produccion/apu.csv` (en USD); ese archivo no trae
  `C-000.000.001` (fresado), `C-000.000.003` (sub-base) ni `C-000.000.013` (línea discontinua): el revisor usó
  «Fresado (ficticio)» 3,50 USD/m3, «Granzón (ficticio)» 1,3 m3 a 4 USD y «Señalización (ficticia)» 0,80 USD/m.
- **Si esas partidas ya existen en la carpeta** con otra fecha (como en la del revisor): al guardarlas otra vez con
  fecha 20/09/2026, **cambiar también el texto de «Condiciones»** (por ejemplo, añadir «al 20/09/2026») para que el
  rendimiento se registre con esa fecha. O empezar limpio con `uv run start.py --reiniciar-demo` (recopia demo, of001,
  ti001, s1 y obra_control: se pierde lo hecho en esos casos).
- **El orden en vivo:** con las partidas ya compuestas antes de la reunión, en la obra «Sílice: caso de demostracion»
  → Tramos (DEMO-001) → importar `via_ficticia.csv` → «Llevar al presupuesto» → Hoja: los 20 renglones con precio y
  ninguno PENDIENTE. Si algo falta, llevar ahora responde con un aviso que dice qué partida, qué insumo y qué lista, y
  no lleva nada.
- Comprobado sobre una copia de la `demo.db` del revisor: recompuestas las 15 con fecha 20/09/2026 y otras
  condiciones, llevar deja los 20 renglones y las 15 partidas compuestas.
