# Árbitro Claude xhigh: la ola 2 (re-congelado y plan, front, libro por frentes, PDF e índices en USD) (2026-11-13, ronda 1)

**Juzgado:** `git diff e2dfe116..67bbb7f8` (`feature/ola2`, 57 commits, 109 archivos), unión de `feature/recongelado-hoja`,
`feature/pendientes-front`, `feature/libro-por-frentes` y `feature/presupuesto-pdf`, contra el código del árbol
`.worktrees/s2m4` (no contra los informes).

**VEREDICTO: DEVUELTO** por dos hallazgos MAYOR (1 y 2): 0 BLOQUEANTE, 2 MAYOR, 8 MENOR y 7 NOTA. El resto del código,
aprobado: cálculos, `Decimal`, re-congelado, `core/`, seguridad de las rutas y datos.
**Aprobado si:** (1) llevar el libro rechaza una obra en otra moneda que la del libro, con su prueba en rojo primero, y
(2) `src/comun/arquitectura.test.ts` vuelve a verde sin agrandar la deuda conocida, comprobado con `npx vitest run`
entero. Los MENOR no bloquean; el 3 (prueba de todo o nada), el 7 (código muerto) y el 9 (CHANGELOG y ESTADO) conviene
hacerlos en la misma ronda.

Ronda: 1 · Base: `e2dfe116` · Cabeza: `67bbb7f8`

## Lo que corrió el árbitro (salida real)

- **pytest** (`.worktrees/tanda/.venv`, `-o addopts="" -q -p no:cacheprovider -W error`, cwd en `s2m4`): las 29 pruebas
  nuevas o tocadas por el diff más el congelado, `test_openapi`, `test_arquitectura*`, `test_aplicacion_sin_ciclos`,
  `test_documentos_*`, `test_dependencias_silice`, `test_api_libros*`, `test_api_hoja_versiones`,
  `test_api_hoja_edicion`, `test_api_hoja_exportar` y `test_aplicacion_hoja_desperdicio`, en tres tandas:
  `785 passed`, `878 passed` y `819 passed`. Ninguna omitida.
- **vitest** (`--maxWorkers=2`): `src/paginas/{hoja,componer,auditoria,indices,administracion,control,produccion}`,
  `src/api`, `src/comun` y `App.bienvenida`: `Test Files 1 failed | 153 passed (154)`, `Tests 3 failed | 1897 passed
  (1900)`; el que falla es `src/comun/arquitectura.test.ts` (hallazgo 2). Las pruebas que leen el código fuera de esas
  carpetas (`sinJergaInterna`, `shell`, `estilos`, `indicadores`, `marco`, `bienvenida`, `sinCalculo` y los estilos de
  otras páginas): `65 passed (65)`, `1162 passed`. `npm run lint` (eslint y `tsc -b --noEmit`): sin errores.
- **Rojos de Python**, cada uno en su propio árbol (`git archive <sha>` en el scratchpad, sin escribir en el
  repositorio), con las pruebas que agregó: fallan los 12. `9c472730` 3 fallan · `d1ee7338` 1 · `4bf1e1eb` 10 ·
  `9856ba26` 9 · `741069ba` 7 · `bbf2be11` error de colección (importa `dias_de_las_etiquetas`, que aún no existe) ·
  `1345b45c` 21 · `9ca6f4d6` 14 · `c1283958` 8 · `da399c05` 45 · `1da8b358` 22 · `f16650a0` 45. Los esbozos que
  traen dos rojos (`aplicacion/indices_usd.py` y `aplicacion/presupuesto_pdf.py`) son firmas con
  `NotImplementedError`. Cada rojo va antes de su verde en la historia.
- **Re-congelado:** `congelado.calcular()` en la cabeza da `auditor 1a894166…`, `banco 29446b12…` y `protocolo
  e769c507…`, las del `congelado.json` y las del acta (`verificar()` vacío); la huella del auditor recalculada sobre los
  50 archivos de `e2dfe116` da `18fc3b4a…`, la del congelado anterior; de esos 50 archivos solo cambió
  `aplicacion/hoja.py` (desde `e2dfe116` y desde `dcb3c0a5`), y no después de `ac99137a`, el commit que declara el
  congelado; `ee12cf3c` y `211ed559` solo tocan `congelado.json`. Árbol sintáctico de `hoja.py` con las cadenas
  vaciadas, base contra cabeza: cambian `_cambios_de_especificaciones`, `_especificaciones_propias`,
  `_estado_de_precio`, `_fuentes_heredadas`, `cambios_entre`, `con_plan_por_rendimientos`, `estado_de_items`,
  `precios_de_version` y un import, la lista del acta. Ninguna está en el camino que mide el experimento
  (`ejecucion.py:56` y `:65` leen `elaborar_borrador(...).elaboracion.informe`, que se arma antes de `estado_de_items`).
- `git diff e2dfe116 --stat -- core/`: vacío; `scripts/guardia_nucleo.py --base e2dfe116`: OK; `ruff check` de los 58
  `.py` del diff: «All checks passed!»; `scripts/meta_datos.py`: 4/4.
- **Sondas del árbitro** (pruebas en el scratchpad que reutilizan las fixtures de `tests/integration/test_api_hoja_libro.py`;
  no van al repositorio): todo o nada de llevar el libro (hallazgo 3), libro en Bs a una obra en USD (hallazgo 1),
  auditoría de la Hoja con lo llevado (`CUMPLE`, solo R2 y R7 «no aplicable», INFO) y `patron_banda` catastrófico
  (hallazgo 4).
- **Datos:** búsqueda tolerante a tildes, mayúsculas y separadores de miles y decimales sobre `git log -p
  e2dfe116..HEAD` (todas las versiones intermedias, no solo la cabeza) y sobre los 57 mensajes, con los nombres,
  rótulos, cifras y parámetros de los dos informes locales (leídos solo para comparar): 0 apariciones (nota N1).

## Hallazgos

| # | Sev. | Criterio · `archivo:línea` | Qué falla | Prueba o reproducción | Arreglo propuesto |
|---|---|---|---|---|---|
| 1 | **MAYOR** | B4/C2 · `aplicacion/libro_a_la_hoja.py:324-332` (`_exigir_moneda`), con `aplicacion/hoja_edicion.py:219-230` y `aplicacion/listas_para_armar.py:371-373` | La moneda del libro solo se compara con la de la **lista para armar de la carpeta**, no con la de la **obra**. Si la obra está en la otra moneda (choque 16, caso que la carpeta admite), el libro entra y `hoja_edicion.completar` convierte cada APU con la tasa del BCV de la fecha del borrador: exactamente la opción que D6 descartó («convertir con la tasa del BCV: el libro no dice la fecha de sus precios: la tasa sería inventada») y lo contrario de la cabecera del módulo («ningún precio cambia de moneda en silencio»). La respuesta dice `"moneda": "Bs"` mientras la Hoja está en USD, y todas las partidas salen «no casa» sin decir por qué, mezcladas con las que no casan por redondeo, financiamiento o bono. | Sonda del árbitro (fuera del repositorio) con las fixtures de `tests/integration/test_api_hoja_libro.py`: carpeta con «Lista Bs de prueba», obra «Vía ficticia por frentes» declarada en USD, tasa de venta ficticia 40 al 30/10/2026, `POST /v1/hoja/libro` con `moneda=Bs` → **200**; VF-001 `precio_impreso` 2.08 y `precio_hoja` 0.05; VF-004 820.00 y 20.24; `casa: false` en las 5; `GET …/vistas/presupuesto` → `moneda: USD`, primera fila P.U. exacto 0.0519440625. | Exigir también la moneda de la obra: en `llevar_libro_a_la_hoja`, con `valoracion_de_la_obra(sesion, proyecto.nombre, fecha)` (o `moneda_del_proyecto`), `MonedaDistinta` (409) si `libro.moneda` no es la de la obra, con un mensaje que lo diga («la obra está en USD y el libro en Bs: Sílice no convierte sus precios; lleve el libro a una obra en Bs»). Prueba en rojo primero en `tests/integration/test_api_hoja_libro.py` con esa carpeta (obra en USD, tasa sembrada) y la aserción de que el catálogo y el borrador no cambian. |
| 2 | **MAYOR** | B2/E3 · `frontend-desktop/src/paginas/administracion/PerfilesDeLibros.tsx:8-9`, `frontend-desktop/src/paginas/componer/ComponerPartida.tsx:42-44`, `frontend-desktop/src/paginas/auditoria/AuditarApuPorHoja.tsx:403` | La prueba de arquitectura del front **falla en la rama** (la CI corre `npx vitest run` entero): dos páginas nuevas importan de otra página (Administración de Auditoría, de `0471efa9`; Componer de la Hoja, de `d8834353`) y `AuditarApuPorHoja.tsx` define otra vez `MONEDAS = ["Bs", "USD"]` (de `399027e0`), que vive solo en `comun/monedas.ts`. Ninguna bitácora corrió `src/comun`, así que el «vitest verde» que declaran no cubría esta prueba. | `npx vitest run src/comun/arquitectura.test.ts` → `4 tests \| 3 failed`: «ninguna página importa de otra…» recibe `administracion -> auditoria/AuditarApuPorHoja`, `componer -> hoja/ProveedorDeLaHoja`, `componer -> hoja/logica`; «MONEDAS se define una sola vez» y «las monedas no se escriben a mano…» reciben `paginas/auditoria/AuditarApuPorHoja.tsx`. | `MONEDAS` de `comun/monedas.ts` (con `rotuloDeMoneda`) en «Llevar a la Hoja»; `enumeradas` y `PerfilDisponible` a `comun/` (son de las dos páginas); el contexto de la Hoja y `rutaDeVista`/`VistaParametros` que usa Componer, a `comun/` o pasados por props desde `ComponerEnPanel` (no agrandar la lista `CONOCIDAS` de la deuda, que la prueba solo deja achicar). Cerrar con `npx vitest run` completo. |
| 3 | MENOR | A1/C2 · `tests/integration/test_api_hoja_libro.py` (falta) | «Todo o nada» de llevar el libro no tiene prueba en la suite. El código lo cumple (ver «verificado»), pero nada impide que se rompa. | Sonda del árbitro: con `importaciones.anotar` forzado a fallar después de escribir el catálogo y reemplazar el borrador, la ruta da 500, no queda ninguna partida `VF-%`, el borrador nuevo se descarta (lista vacía) y, en un borrador que ya estaba, sus 10 filas (clave y cantidad) y su `rev` (1) quedan iguales y no entra la variante «VF-001-B» que el segundo libro habría creado; al quitar la falla, llevar entra con las 5 partidas nuevas (sin «-B»). | Agregar esas dos pruebas (borrador nuevo y borrador que ya estaba) a la suite. |
| 4 | MENOR | C1 · `adapters/hoja_empresa/perfil_apu_por_hoja.py:203-210` y `:336-372`; uso en `aplicacion/cifras.py:128` (AH9) y en `aplicacion/vial.py:650-662` (VR4) | `patron_banda` se acepta con solo compilarlo: ni largo máximo ni defensa contra retroceso catastrófico, y ahora se instala desde la interfaz (`POST /v1/admin/empresa/perfiles-libros`). Un patrón descuidado (no hace falta malicia) cuelga el hilo que audita el libro y, si el perfil se llama `apu_por_hoja` (el local manda sobre el del paquete), también cada recálculo de una Hoja con tramos de transporte por banda sin la directiva de la banda (VR4 lee la descripción con él), con el cerrojo del borrador tomado. Solo quien administra puede ponerlo (por eso no es MAYOR). | `instalar_perfil_apu_por_hoja` acepta el perfil del paquete con `patron_banda` `(?P<minimo>(a+)+)(?P<maximo>b)`; `leer_banda` sobre «a»×n + «!»: 18 → 0,07 s, 20 → 0,25 s, 22 → 0,97 s (se duplica con cada letra). | Tope de largo del patrón (p. ej. 200) y rechazo de cuantificadores anidados y referencias hacia atrás al validar el perfil (`PerfilInvalido`), con su prueba en rojo; o, mejor, sustituir la expresión libre por el patrón fijo del paquete con las palabras del perfil. |
| 5 | MENOR | D1 · `frontend-desktop/src/paginas/hoja/PresupuestoPorFrentes.tsx:66-90` | La vista por frente se pide al abrirla y al poner un frente, nunca al cambiar `rev`: si con el panel abierto se edita una cantidad o se quita un renglón, «Total general» y los subtotales siguen viejos mientras «Total del presupuesto», justo arriba, ya cambió. | Lectura del componente: no hay efecto sobre `rev`; `PestanaPresupuesto.tsx:338` lo monta sin `key`. | Volver a pedir la vista cuando cambie `rev` con el panel abierto (o montarlo con `key={rev}`), con su prueba en vitest. |
| 6 | MENOR | D1 · `aplicacion/hoja.py:1613-1628` con `frontend-desktop/src/comun/rotulos.ts:107-110` | El registro de cambios de un frente se lee «Especificaciones: → _frente=FRENTE A»: la clave interna de la directiva llega a la persona («Guardar versión», Versiones y «Quién cambió qué»). | Lectura: `_cambios_de_especificaciones` escribe `_pares_a_texto` de las especificaciones y `valorDeCambio` solo pasa las cifras a es-VE. | Sin tocar `hoja.py` (congelado; la clave forma parte de la huella): en `presentarCambio.ts`, presentar `_frente=X` como «Frente: X» y ocultar las directivas que empiezan por «_» que no tengan rótulo. |
| 7 | MENOR | B2 · `aplicacion/presupuesto_pdf.py:48-52` y `:276` | Interacción entre líneas: la línea 1 puso las tildes en `hoja.filas_de_cierre` («+ Administración»), así que `_TILDES_DEL_CIERRE` de la línea 4 ya no casa con nada y su comentario («como los escribe `aplicacion/hoja.py` (congelado)») es falso. | `grep "+ Administracion"` en el código: solo queda esa tabla (y datos de prueba del front). | Quitar la tabla y su uso. |
| 8 | MENOR | F1/D1 · `api/rutas/hoja_exportar.py:91` | Interacción entre líneas: la Hoja agrupa por frente y el PDF no (la ruta llama a `documento_de_la_hoja` sin `agrupar=`). Un presupuesto llevado desde un libro por frentes sale en el PDF como una lista corrida, sin el subtotal de cada frente que la pantalla sí muestra. Declarado como pendiente en la bitácora de la línea 4, §4. | Lectura de la ruta y de `aplicacion/presupuesto_pdf.py:139-146`. | Un `Agrupador` en `aplicacion/frentes.py` que reparta `FilaDePresupuesto` por `frente_de` del renglón de su `clave` (sin frentes, `sin_agrupar`), y una prueba de que los subtotales del PDF son los de `GET …/vistas/frentes`. |
| 9 | MENOR | E2 · `CHANGELOG.md`, `docs/ESTADO.md` | Ni el CHANGELOG ni ESTADO dicen nada de la ola 2 (`git diff --stat e2dfe116 HEAD -- CHANGELOG.md docs/ESTADO.md` vacío): RF-196 a RF-214, el segundo re-congelado y los pendientes (PDF por frente, `_codigo_libro`, expediente de `core/` propuesto por la línea 3). | — | Ponerlos al día antes del PR. |
| 10 | MENOR | C1 · `adapters/hoja_empresa/perfil_apu_por_hoja.py:362-371` | Con «Reemplazar», un perfil `apu_por_hoja` pisa cualquier `<nombre>.json` de la carpeta, también uno de otro tipo (la lista los salta sin decirlo) y el 409 dice «Ya hay un perfil» de un archivo que la pantalla nunca mostró. | Lectura. | Si el que está no es `"tipo": "apu_por_hoja"`, 409 con ese motivo aunque se pida reemplazar. |
| N1 | NOTA | Datos (NORMAS §1) | Sin datos reales en el diff ni en los 57 mensajes: búsqueda tolerante a tildes, mayúsculas y separadores sobre `git log -p e2dfe116..HEAD` y los mensajes, con los nombres, rótulos, cifras y parámetros de los dos informes locales: ninguna aparición. «Otros impuestos (%)» y los rótulos de la fixture son genéricos y ficticios; la cifra de 28 dígitos (`docs/bitacora/2026-11-13-ola2-front.md:49`, pruebas de Componer) ya estaba en la base y viene de un precio público de MaPreX con tasa ficticia (aceptada en el arbitraje anterior). El incidente de §8 de la bitácora del front quedó limpio en esta historia; lo que Gemini recibió no se puede deshacer y ya está declarado. | | |
| N2 | NOTA | E1 | Asuntos de commit con tildes; las líneas `Co-Authored-By` no se juzgan. | | Como en arbitrajes anteriores: inocuo. |
| N3 | NOTA | E3 · rojos del front | Los rojos de vitest no se volvieron a correr en su commit (no se pueden montar los `node_modules` en un árbol extraído); su orden rojo → verde en la historia sí se comprobó. | | |
| N4 | NOTA | `api/rutas/control.py:239` | `dias_por_periodo` pasa de «5» por omisión a «del plan» (o 20 sin plan): un cliente de la API que no lo mandaba cambia de resultado. Declarado (RF-196); la pantalla siempre lo manda. | | Decisión para Eugenio, ya simulada en la bitácora de la línea 1, §6. |
| N5 | NOTA | `api/rutas/hoja_libro.py:95-108` con `aplicacion/libro_a_la_hoja.py:172-195` | Un APU que la auditoría no pudo evaluar no pasa a `LibroParaLlevar`, y su renglón sale en `sin_apu`, como si el libro no tuviera su hoja: no es la causa. | | Una lista aparte («APU que no se pudieron evaluar») o decirlo en el texto. |
| N6 | NOTA | `api/rutas/hoja_libro.py:128`, `api/rutas/libros.py:937-943` | `hoja_presupuesto` no tiene tope por elemento ni de cantidad; lo acota `LIMITE_CUERPO`. | | Inocuo; un tope de 31 caracteres (el de Excel) y de 100 hojas lo haría explícito. |
| N7 | NOTA | ERS | RF-202 a RF-204 no existen (la numeración salta de RF-201 a RF-205). | | Decir en el ERS si están reservados. |

## Verificado sin hallazgo

- **Montos y subtotales por frente.** `Presupuesto.total` es la suma de los totales de sus partidas
  (`core/contracts/presupuesto.py:55-56`) y `aplicacion/frentes.py:86-118` suma esos mismos totales por frente, cruzando
  cada partida con su renglón por la clave `codigo|origen_id` (`aplicacion/hoja.py:859-872`), que no lleva el frente: la
  suma de los subtotales es el total, sin redondeo intermedio (la pantalla solo redondea al mostrar). Oráculo de la prueba
  a mano y comprobado: 2.814,6756 + 1.876,4504 = 4.691,126. Un renglón pendiente cuenta aparte y no suma.
- **`Decimal`, coma decimal y redondeos.** Ningún `float` en montos del diff de Python (el único `float()` nuevo escribe
  el .xlsx ficticio de `tests/fixtures/libro_apu_por_hoja.py`, como las demás hojas de esa fixture); en el front, ningún `Number()`/`parseFloat` sobre montos (el único
  `Number(k)` es un índice) y la lectura en reposo del precio usa `centesimasEsVe` con `BigInt` sobre el texto. PDF: cifras
  con `texto_de_cifra`, las celdas del APU leídas con `cifra_escrita` (el arreglo `d105f092`, rojo visto), el subtotal de
  cada grupo con los totales exactos y el IVA con `con_iva` sobre el total exacto (subtotal y IVA redondeados y sumados,
  como la pestaña). Índice en USD: promedio y división con 28 dígitos y `ROUND_HALF_EVEN`; la tasa de cada día es la de
  mayor fecha ≤ ese día y caduca con `> DIAS_MAXIMOS_SIN_TASA`, la misma comparación de `core/catalog/indices.py:178`;
  oráculo a mano (87 ÷ 43,5 = 2) y huella con el dato provisional; `guardar` confirma o deshace todo y el responsable es
  el de la sesión. La serie en USD lleva la unidad `indice_usd` y el núcleo solo avisa S1-R11 con `indice_bs`
  (`core/budget/reajuste.py:632`). Componer (RF-200): `parametros_desde_textos` lee con `cifra_escrita` y rechaza
  negativos; la composición se guarda sin parámetros y `aplicacion/composicion.py` (congelado) no cambia.
- **Todo o nada de llevar el libro** (`aplicacion/libro_a_la_hoja.py:369-436`): el catálogo se confirma una sola vez al
  final y se deshace ante cualquier excepción; el borrador nuevo se descarta y el que ya estaba recupera borrador, `rev`,
  cálculo, tamaño e importaciones. `cargar_composicion` y `fijar_referencia` solo hacen `flush`; un precio que ya estaba
  en la lista no se pisa (entra una variante del insumo) y uno que ya tenía referencia la conserva. Las sondas lo
  confirman (hallazgo 3).
- **Seguridad de las rutas nuevas.** Las once rutas nuevas están en la tabla de `tests/unit/test_api_acceso_por_ruta.py`, que
  pasa: poner un perfil es `ADMINISTRAR_EMPRESA` con sesión (la clave de API no sirve); llevar el libro y poner frentes,
  `editar_hoja` con sesión, `no-store` y sin eco en el 422. Perfil local: el nombre del archivo sale del campo `nombre`
  validado con `[a-z0-9_]+` (sin recorrido de carpetas), se lee a lo sumo `MAX_BYTES_PERFIL + 1` (64 KiB), se valida
  entero antes de escribir y se escribe en un temporal con `os.replace`. PDF: todo texto de la persona va con
  `escape(_limpio(...))` a `Paragraph` (un «<b>» se ve tal cual, probado) y las demás celdas son texto plano de la tabla,
  que reportlab no interpreta; el nombre del archivo pasa por `nombre_del_pdf`. `POST /v1/libros/hojas` pasa por la
  guardia y solo devuelve nombres.
- **Interacción entre líneas.** El `_frente` de la línea 3 y `cambios_entre` de la línea 1: poner solo frentes es un
  cambio, se guarda con la versión y vuelve al abrirla (pruebas `9c472730`/`b9ef6a80` y la de integración); R4 ignora la
  directiva y la auditoría de la Hoja con lo llevado da `CUMPLE`. El plan que cabe (línea 1) sirve a la primera versión
  de un libro grande llevado (línea 3). Los parámetros de Componer (línea 2) se proponen desde `vistas/parametros` del
  borrador, que son los que deja el libro llevado. Lo que no está conectado (PDF por frente) es el hallazgo 8, y el
  código muerto que dejó la unión, el 7.
- **Re-congelado:** el acta y los hashes son ciertos y el cambio no toca lo que mide el experimento (ver arriba).
- **`core/` intacto**, `docs/api.json` igual a la API (`test_openapi`), ERS con RF-196 a RF-201 y RF-205 a RF-214 y
  manual de usuario al día.
- **Pruebas no circulares:** oráculos a mano en `test_api_hoja_libro.py` (P.U. de la memoria del libro ficticio),
  `test_indices_usd.py`, `test_presupuesto_pdf.py` (OF-001: 2.703,86 y 2.821,42), `test_control_dias_del_plan.py`
  (tabla de la simulación); los arreglos de pruebas intermitentes (`App.bienvenida`, `CostosDelPeriodo`) cambian cómo se
  escribe, no lo que se afirma.


## Ronda 1: correcciones (2026-11-13, corrector)

Árbol `.worktrees/s2m4`, rama `feature/ola2`, desde `7c62dd47`. Sin tocar `core/` ni los 50 archivos congelados del
experimento (comprobado contra `asistente/experimento/protocolo.json`). Cada arreglo con su prueba en rojo vista antes
y commits separados; datos FICTICIOS (las fixtures de `tests/fixtures/libro_apu_por_hoja.py` y `carpeta_aprobaciones`).

| # | Estado | Rojo → verde | Qué se hizo |
|---|---|---|---|
| 1 MAYOR | Hecho | `8d3bcc05` → `9ef1739f` | `_exigir_moneda` compara también con `moneda_del_proyecto` de la obra: 409 `MonedaDistinta` («La obra «…» está en USD y el libro en Bs: Sílice no convierte los precios del libro. Lleve el libro a una obra en Bs.») antes de abrir el borrador ni tocar el catálogo. Rojo: `200 == 409` (VF-001 impreso 2.08, en la Hoja 0.05: la sonda del árbitro). |
| 2 MAYOR | Hecho | (rojo ya en la rama) → `372b3998` | `comun/borradorAbierto.ts` (el id del borrador abierto, que pone `ProveedorDeLaHoja`, y `rutaDeVista`, que `hoja/logica` reexporta) y `comun/perfilesDeLibros.ts` (`PerfilDisponible`, `enumeradas`); «Llevar a la Hoja» usa `MONEDAS` y `rotuloDeMoneda`. `CONOCIDAS` no crece. Rojo visto en `7c62dd47`: `4 tests, 3 failed`. |
| 3 MENOR | Hecho | mutantes → `c569855b` | Dos pruebas de todo o nada (borrador nuevo; borrador que ya estaba, con el libro que crearía «VF-001-B»). Sin código nuevo: el rojo se vio con dos mutantes locales (A: `rollback` → `commit`, 2 failed; B: sin restaurar ni descartar el borrador, 2 failed). |
| 4 MENOR | Hecho | `49282097` → `495e940e` | `patron_banda`: tope de 300 caracteres y rechazo, por su árbol (`re._parser`), de una repetición dentro de otra, una alternativa dentro de una repetición y una referencia hacia atrás, en `_construir` (paquete, carpeta y subida). Rojo: 10 failed (DID NOT RAISE). Simulación abajo. |
| 5 MENOR | Hecho | `5b5f8348` → `aa38ebec` | Un efecto sobre `rev` vuelve a pedir `vistas/frentes` con el panel abierto, una vez por `rev` y no tras «Poner el frente». Rojo: 1 failed («Total general: 4.801,13 Bs» no aparece). |
| 6 MENOR | Hecho | `2df29574` → `758dc690` | `presentarValor("especificaciones", …)` par por par: «_frente=X» → «Frente: X»; otra directiva «_…» sin rótulo no se muestra; cifras con coma. `hoja.py` sin tocar. Rojo: Received «_frente=FRENTE A». |
| 7 MENOR | Hecho | refactor `6a17557e` | Fuera `_TILDES_DEL_CIERRE` y su uso (solo ella tenía «+ Administracion»); `test_presupuesto_pdf` y `test_api_hoja_pdf` siguen viendo «+ Administración». |
| 8 MENOR | Hecho | `f8c440e4` → `1e31aee9` | `frentes.repartir_por_frente` (los grupos y el orden de `por_frentes`) y `presupuesto_pdf.por_frente(vivo)`, el agrupador de la ruta por omisión (`agrupar=frente`); `agrupar=ninguno`, la lista corrida; el agrupador corre bajo el cerrojo. `docs/api.json` regenerado. Rojo: 1 failed (sin «Subtotal de FRENTE A»). |
| 9 MENOR | No es del corrector | — | CHANGELOG y ESTADO los escribe el orquestador (encargo común). |
| 10 MENOR | Hecho | `86ad77f7` → `8eda94b1` | `_de_otro_tipo`: si el `<nombre>.json` que está es un JSON legible sin `"tipo": "apu_por_hoja"`, 409 con ese motivo aunque se pida reemplazar; uno ilegible (que la lista sí muestra con su motivo) se reemplaza. Rojo: «Ya hay un perfil…» y lo pisaba. |
| N6 | Hecho | `e4eec769` → `d1fb1f0f` | `_exigir_hojas`: `hoja_presupuesto` a lo sumo 100 hojas de a lo sumo 31 caracteres, 422 sin eco, en la auditoría y al llevar el libro. Rojo: 3 failed. |
| N7 | Hecho | `7d23cfea` | El ERS dice que RF-202 a RF-204 quedaron reservados sin usar; RF-209, RF-210 y RF-213 y el manual (§4, §12.5, §12.6) al día. |
| N1 a N3 | Sin acción | — | Notas sin pedido. |
| N4 | Anotada | — | Decisión de Eugenio (`dias_por_periodo` por omisión), ya simulada en la bitácora de la línea 1, §6. |
| N5 | Anotada | — | Un APU que la auditoría no pudo evaluar sale en `sin_apu`: decirlo aparte pide un campo nuevo en `LibroLlevado`, en la respuesta, en `docs/api.json` y en la pantalla; no es de minutos. |

Visto al pasar: el 422 de la auditoría con una hoja que no está repite el nombre escrito («no tiene la hoja X: sus
hojas son…»); es lo que tecleó la persona y le sirve, no un dato ajeno. Sin cambio.

### Decisiones y su simulación

**Hallazgo 1, qué hacer con una obra en otra moneda que el libro** (la prueba con la fixture: carpeta en Bs, obra en
USD, tasa ficticia 40 al 30/10/2026).

| Opción | Resultado |
|---|---|
| Convertir con la tasa del BCV del día del borrador (lo que pasaba) | 200; VF-001 2,08 → 0,05 USD, VF-004 820,00 → 20,24; las 5 «no casa» sin decir por qué; la respuesta dice «Bs» y la Hoja está en USD |
| Cambiar la moneda declarada de la obra (no tiene versiones) | Cambia una decisión de la obra en silencio, al llevar un libro: descartada |
| **Rechazar (409) antes de tocar nada** (elegida, la del árbitro y D6) | 409 con el motivo; ninguna partida VF-% y ningún borrador (la prueba lo comprueba) |

**Hallazgo 2, dónde va lo que Componer lee de la Hoja.**

| Opción | Resultado |
|---|---|
| Pasar el borrador por props desde `ComponerEnPanel` | La pantalla `/presupuesto/componer` (`paginas/componer/index.tsx`) también necesita el borrador y tendría que leer el proveedor de la Hoja: sigue «componer -> hoja/ProveedorDeLaHoja» |
| Mover `ContextoDeLaHoja` entero a `comun/` | `HojaDeLaObra` usa tipos de `hoja/logica`, `logicaRetomar` y `logicaVersiones`: `comun/` importaría de `paginas/` y falla la segunda prueba de arquitectura |
| **Un contexto mínimo en `comun/` con el id del borrador, y `rutaDeVista` con él** (elegida) | `arquitectura.test.ts` 4/4; componer, administración, auditoría y `ProveedorDeLaHoja`: 35 archivos, 422 pruebas |

**Hallazgo 4, la defensa de `patron_banda`** (guion `scratchpad/ola2/corrector/sim_redos.py`, Python 3.13.13 del
`.venv`; tiempos reales).

| Patrón | Tope + árbol (elegida) | Tope + heurística de texto | Probar en otro proceso, 0,5 s | `re.search` sobre «a»×22 + «!» |
|---|---|---|---|---|
| El del paquete | acepta | acepta | acepta (0,21 s por validación) | 0,001 s |
| El de miles de las pruebas | acepta | acepta | acepta (0,24 s) | 0,000 s |
| «(a+)+» (el del árbitro) | rechaza | rechaza | rechaza (0,54 s) | 0,894 s |
| «(a o a)*» | rechaza | **acepta** | rechaza | — |
| «(a*)*» | rechaza | rechaza | rechaza | — |
| «(?:a o aa)+» | rechaza | **acepta** | **acepta** | — |
| «([0-9]+)*» | rechaza | rechaza | **acepta** | — |
| «(a{1,9}){2,}» | rechaza | rechaza | rechaza | — |
| referencia «\1» | rechaza | rechaza | **acepta** | — |
| «a*a*a*a*» (polinómico) | acepta | acepta | acepta | 0,004 s |
| 1.000 caracteres | rechaza | rechaza | **acepta** | — |

(«o» es la barra de la alternativa, que no se puede escribir dentro de una tabla.) El módulo `regex` con tiempo máximo
está en el `.venv`, pero solo como dependencia de `formulas` (grupo `dev` de `pyproject.toml`): no llega al programa
instalado, así que no es una opción. Probar en un hilo no sirve: `re` no suelta el GIL mientras busca. Elegida: tope +
árbol, que rechaza los ocho peligrosos, acepta los legítimos y no cuesta nada al leer el perfil (cada auditoría y cada
recálculo con VR4 lo leen). `re._parser` es interno de la biblioteca estándar (existe desde 3.11; Sílice pide 3.12 o
más): si cambiara, las pruebas de `test_libro_por_frentes.py` lo dirían. Revertir: `git revert 495e940e`. Lo que el
árbitro propuso como «mejor» (un patrón fijo con las palabras del perfil) cambia el formato del perfil y rompe los
locales con patrón propio: queda para otra ronda.

**Hallazgo 5, cómo refrescar la vista por frente.**

| Opción | Resultado (vitest) |
|---|---|
| `key={rev}` en la pestaña | Refresca, pero el panel se cierra en cada edición: tras otro `rev`, «Total general» no se ve y vuelve el botón «Ver el presupuesto por frente» (prueba de simulación, no versionada) |
| **Efecto sobre `rev` con el panel abierto, una vez por `rev`** (elegida) | 6/6: abierto pide la vista nueva; cerrado no pide; tras «Poner el frente» no pide otra vez |

**Hallazgo 6, cómo decir el frente en el registro.** «Frente: X» (elegida, la del árbitro) frente a dejar
«_frente=X» (la clave interna a la vista) o cambiar `hoja.py` (congelado; la clave es parte de la huella). Las demás
directivas «_…» sin rótulo se callan; un frente con «; » queda entero (prueba).

**Hallazgo 8, cuándo agrupa el PDF** (prueba de integración con el libro por frentes).

| Opción | Resultado |
|---|---|
| Solo con `agrupar=frente` | El botón tendría que saber si hay frentes: las filas de la vista no traen el frente, así que sería otra petición a `vistas/frentes` antes de cada descarga o un campo nuevo en el resumen |
| Agrupar siempre | Una obra sin frentes saldría con un grupo «Sin frente» y su subtotal, igual al total |
| **Por frente si algún renglón lo tiene; `agrupar=ninguno` para la lista corrida** (elegida; S10 y Presto imprimen por títulos cuando el presupuesto los tiene) | Con frentes: «Subtotal de FRENTE A 2.814,68», «Subtotal de FRENTE B 1.876,45», total 4.691,13 (los de `vistas/frentes`); sin frentes, como antes; el botón «Descargar PDF» no cambia |

**Hallazgo 10.** 409 aunque se pida reemplazar (la del árbitro), frente a pisarlo con aviso (se pierde un perfil que la
pantalla nunca mostró) o renombrarlo (deja archivos que nadie pidió).

### Lo que corrió el corrector

- **pytest** (`.worktrees/tanda/.venv`, `-o addopts="" -q -p no:cacheprovider -W error`, cwd en `s2m4`):
  `test_api_hoja_libro`, `test_api_acceso_por_ruta`, `test_api_admin*`, `test_api_hoja`, `test_api_libros*`
  (unitarias e integración), `test_fusion_apu_por_hoja`, `test_hoja_empresa_apu_por_hoja`, `test_hoja_recongelado_2`,
  `test_libro_por_frentes`, `test_presupuesto_pdf`, `test_api_hoja_pdf`, `test_api_hoja_exportar`,
  `test_vial_banda_descripcion`, `test_openapi`, `test_aplicacion_sin_ciclos`, `test_arquitectura*`,
  `test_documentos_*` y `test_manuales_s5`: `1518 passed`.
- `ruff check .`: «All checks passed!»; `git diff e2dfe116 --stat -- core/`: vacío; `scripts/guardia_nucleo.py --base
  e2dfe116`: OK; `scripts/meta_datos.py`: 4/4; `scripts/exportar_openapi.py` con el cambio de la ruta del PDF
  (`docs/api.json` en `1e31aee9`).
- **Front:** `npx eslint .` y `npx tsc -b --noEmit`: sin errores. `npm run lint` tal cual falla en este equipo porque
  eslint entra en `frontend-desktop/node_modules.viejo` (la copia vieja local, fuera del repositorio): se corrió con
  `--ignore-pattern "node_modules.viejo/**"`, que es lo que ve la CI.
- **vitest entero** (`npx vitest run --maxWorkers=3`): en la base de la ronda (`7c62dd47`, el front de entonces puesto
  en el árbol y devuelto después) `3 failed | 4472 passed`, los tres de `arquitectura.test.ts` (hallazgo 2) y nada más.
  En la cabeza, dos corridas con `1 failed | 4478 passed`: «quien opera la arenera con su especialidad encendida ve la
  arenera» (`paginas/inicio/VistaGeneral.test.tsx:551`, «expected +0 to be 1»), que pasa sola y con `src/paginas/inicio`
  (61 passed). El bloque se pinta «cargando» en el mismo commit en que se programa el efecto que lo pide y la prueba
  contaba el pedido al ver el bloque: carrera de la prueba, que el cambio del grafo de módulos de esta ronda dejó a la
  vista. Arreglo en `b3bba087` (se espera el pedido con `waitFor`; lo que afirma no cambia). Tercera corrida:
  `Test Files 303 passed (303)`, `Tests 4479 passed (4479)`.
- **Datos:** búsqueda tolerante a tildes y separadores sobre `git log -p 7c62dd47..HEAD` y los mensajes, con las
  palabras y cifras de los dos informes locales (leídos solo para comparar, guion en el scratchpad): 0 cifras; las
  palabras que coinciden son genéricas («estación», «subtotales», «ficticia», «commit»…), ningún nombre, código ni
  rótulo del libro.


## Ronda 2: veredicto (2026-11-13, árbitro Claude xhigh)

**Juzgado:** `git diff 7c62dd47 eb3dbb9b` (las correcciones, 20 commits) contra el código del árbol `.worktrees/s2m4`
en `751b7ed4`. La unión con `origin/main` solo trae `frontend-desktop/src/paginas/pendientes/Bandeja.test.tsx`
(`git diff --stat eb3dbb9b 751b7ed4`).

**VEREDICTO: APROBADO CON CAMBIOS.** 0 BLOQUEANTE, 0 MAYOR, 2 MENOR y 2 NOTA. Los dos MAYOR de la ronda 1 están
cerrados: se cumplen las dos condiciones de «Aprobado si», comprobadas abajo. También están cerrados los MENOR 3, 5, 6,
7, 8 y 10 y las notas N6 y N7. Lo que queda no pide otra ronda: R2-1 (la defensa de `patron_banda` se burla con formas
rebuscadas y rechaza el patrón de miles) y R2-2 (el MENOR 9 de la ronda 1, CHANGELOG y ESTADO), que tiene que estar
hecho antes del PR.

Ronda: 2 · Base: `7c62dd47` · Cabeza: `eb3dbb9b` (árbol en `751b7ed4`)

### Lo que corrió el árbitro (salida real)

- **vitest entero** (`npx vitest run --maxWorkers=2` en `frontend-desktop`): `Test Files 303 passed (303)`,
  `Tests 4479 passed (4479)`. `npx vitest run src/comun/arquitectura.test.ts`: `4 passed (4)`. `npx tsc -b --noEmit` y
  `npx eslint . --ignore-pattern "node_modules.viejo/**"`: sin errores.
- **pytest** (`.worktrees/tanda/.venv`, `-o addopts="" -q -p no:cacheprovider -W error`, cwd en `s2m4`), 31 archivos:
  `test_api_hoja_libro`, `test_libro_por_frentes`, `test_api_libros_frentes`, `test_api_libros*`,
  `test_api_acceso_por_ruta`, `test_api_admin*`, `test_api_hoja_exportar`, `test_api_hoja_pdf`, `test_presupuesto_pdf`,
  `test_fusion_apu_por_hoja`, `test_hoja_empresa_apu_por_hoja`, `test_hoja_recongelado_2`, `test_vial_banda_*`,
  `test_openapi`, `test_aplicacion_sin_ciclos`, `test_arquitectura*` y `test_documentos_*`: `1339 passed`. Ninguna
  omitida.
- **Rojos**, cada uno en su commit (`git archive` en el scratchpad, sin escribir en el repositorio). `8d3bcc05`: 1 failed
  (`assert 200 == 409`; VF-001 impreso 2.08 y en la Hoja 0.05, VF-004 820.00 y 20.24, que es mi sonda de la ronda 1).
  `49282097`: 10 failed y 4 passed (nueve «DID NOT RAISE» más el de la carpeta; pasan los cuatro legítimos).
  `86ad77f7`: 1 failed («Ya hay un pe…»). `f8c440e4`: 1 failed (falta «Subtotal de FRENTE A»). `e4eec769`: 3 failed.
  Front, con los `node_modules` enlazados por una junction que quité al terminar (en esta ronda la nota N3 no hace
  falta): `5b5f8348` 1 failed («Unable to find … Total general: 4.801,13 Bs») y `2df29574` 1 failed (Received
  «_frente=FRENTE A»). El rojo del MAYOR 2 lo vi en la ronda 1 (`7c62dd47`, 3 failed). Cada rojo trae solo pruebas y
  está en la historia antes de su verde.
- **Todo o nada (`c569855b`), que no tiene rojo propio**: los dos mutantes del corrector en el árbol de ese commit. A
  (`rollback` → `commit`): 2 failed (`['VF-001', …] == []`). B (sin descartar ni restaurar el borrador): 2 failed
  (queda un borrador; entra «VF-001-B»). Las pruebas muerden.
- **Sondas** (fuera del repositorio): `patron_banda` (R2-1; `scratchpad/sonda_redos.py`, cada búsqueda en otro proceso
  con tope de 5 s) y el PDF por frente con frentes intercalados y un renglón sin frente (en una copia de la cabeza).
- `git diff --stat 7c62dd47 751b7ed4 -- core/`: vacío. `scripts/guardia_nucleo.py --base 7c62dd47`: OK.
  `congelado.verificar()`: vacío. Ninguno de los 50 `archivos_del_auditor` de `asistente/experimento/protocolo.json`,
  ni el congelado, está en el diff. `ruff check` de los `.py` del diff: «All checks passed!». `scripts/meta_datos.py`:
  4/4. `arquitectura.test.ts` no se tocó (la lista `CONOCIDAS` no crece).
- **Datos**: leí los dos informes locales solo para comparar. Busqué palabras, frases de tres palabras, palabras con
  mayúscula y cifras de 4 o más dígitos, sin distinguir tildes ni mayúsculas, sobre lo agregado en
  `git log -p 7c62dd47..751b7ed4` y sobre los mensajes. Coinciden solo palabras y frases del oficio o de rutas del
  repositorio («lista para armar», «banda de distancia») y las cifras 2026, 1000 y 0001. Ningún nombre, código, rótulo
  ni cifra de los libros. Los valores nuevos de las pruebas (frentes, descripciones) son genéricos.

### Hallazgos

| # | Sev. | Criterio · `archivo:línea` | Qué falla | Prueba o reproducción | Arreglo propuesto |
|---|---|---|---|---|---|
| R2-1 | MENOR | C1 · `adapters/hoja_empresa/perfil_apu_por_hoja.py:257-289` (`_retroceso_catastrofico`; `:269`, `varias = maximo > 1`), con `docs/manual_usuario.md:1556` y RF-209 | La defensa (lo que quedaba del hallazgo 4) rechaza una lista de formas y deja pasar otras que cuelgan igual. Una repetición de a lo sumo una vez (`?`) no cuenta como «repetición dentro de otra», y nada acota una cadena de repeticiones seguidas que se pisan. El manual promete que el patrón «no puede llevar repeticiones una dentro de otra», y `a?` dentro de `+` lo es. Al revés, rechaza patrones legítimos que no retroceden: el de miles con punto (`\d{1,3}(?:\.\d{3})*`, la convención de Sílice, que `cifra_escrita` lee) por «una repetición dentro de otra», y también `\d+(?:[.,]\d+)*` y `(?:\w+ )*`. Sigue en MENOR, como el 4: solo quien administra pone el perfil y las formas que se cuelan son rebuscadas. Los patrones descuidados de verdad, con varios `.*`, fallan rápido (0,017 s con 400 caracteres), y el de miles tiene salida: `[0-9.]+(?:,[0-9]+)?`, que la prueba «con_miles» acepta. | Sonda: `instalar_perfil_apu_por_hoja` ACEPTA y `leer_banda` tarda. `(?:a?a?)+`: más de 5 s con «a»×20 + «!». `(?:a?){28}a{28}`: más de 5 s con 28. Quince `[0-9]*` seguidos: más de 5 s con 15 cifras. Doce `.*` seguidos: 1,44 s con 15 letras y más de 5 s con 25. `(?:a?a)+`: 1,04 s con 30, y crece 1,6 veces por letra. `(?:\d?\d)+`: 1,27 s con 30 cifras. RECHAZA los tres legítimos de arriba. | Contar como peligrosa toda repetición variable (mínimo ≠ máximo, `?` incluido) dentro de otra que se repite, y aceptar la de cuenta fija (`\d{3}`, mínimo = máximo), con lo que el de miles pasa. Poner un tope a las repeticiones sin tope del patrón (el del paquete tiene cuatro). Sumar estos patrones a `test_libro_por_frentes.py`. Si se quiere garantía y no heurística, queda el patrón fijo con las palabras del perfil (la opción «mejor» de la ronda 1). Entretanto, que el manual y el docstring digan que se rechazan esas formas, no que se rechace todo lo que puede colgarse. |
| R2-2 | MENOR | E2 · `CHANGELOG.md`, `docs/ESTADO.md` (el 9 de la ronda 1) | Sigue abierto: `git diff --stat e2dfe116 751b7ed4 -- CHANGELOG.md docs/ESTADO.md` sale vacío. El corrector lo dejó al orquestador. | — | Escribirlos antes del PR: RF-196 a RF-214, el segundo re-congelado, lo de esta ronda y los pendientes. |
| R2-N1 | NOTA | D1 · `frontend-desktop/src/paginas/hoja/PresupuestoPorFrentes.tsx:88-100` y `:118-136` | El pedido de `abrir()` y la respuesta de `poner()` no llevan la guarda `vigente` del efecto nuevo (`:102-116`). Si el `rev` cambia mientras el pedido de `abrir()` está en vuelo, una respuesta vieja puede llegar después de la nueva y dejar la vista atrasada. Para que pase hay que editar la Hoja mientras el panel se abre. | Lectura. La otra carrera que cabía no existe: `fallar` es estable porque `alExpirar` (`marco/Marco.tsx:124`) y `alAusente` (`refrescar`, `useBorrador.ts:88`) son `useCallback`, así que la limpieza del efecto no descarta la vista pedida. | Un contador de pedidos en un `useRef` común a los tres caminos; solo se aplica la respuesta del último. |
| R2-N2 | NOTA | D1 · `aplicacion/frentes.py:136-153` (`SIN_FRENTE`) | Un frente que se llame «Sin frente» y el grupo de los renglones sin frente salen con el mismo título en el PDF, como en la pantalla. | Lectura. | Inocuo. Si importa, rechazar ese nombre en `poner_frentes` o titular el grupo «(sin frente)». |

### Lo que se cerró (verificado sin hallazgo)

- **MAYOR 1, cerrado.** `_exigir_moneda` (`aplicacion/libro_a_la_hoja.py:325-345`) compara el libro con la lista para
  armar y con `moneda_del_proyecto` de la obra, antes de abrir el borrador y de tocar el catálogo (`:377`). La Hoja
  decide convertir con esa misma función: `valoracion_de_la_obra` (`aplicacion/listas_para_armar.py:371-372`), que
  `hoja_edicion.completar` usa (`aplicacion/hoja_edicion.py:219-229`). Con las dos comparaciones, la obra está en la
  moneda de la lista, `tasa` es `None` y `completar` no convierte. La obra solo declara su moneda al crearse
  (`aplicacion/proyectos.py:144`; `declarar_moneda` exige que no haya versiones), así que el caso no se reabre después.
  La prueba nueva reproduce mi sonda (rojo arriba) y comprueba que no quedan partidas `VF-%` ni borradores.
- **MAYOR 2, cerrado.** `src/comun/arquitectura.test.ts` 4/4 y vitest entero en verde (arriba).
  `comun/borradorAbierto.ts` solo importa `react`. `ContextoDelBorradorAbierto` lo pone solo `ProveedorDeLaHoja`
  (`:306`), con el valor que Componer leía antes (`estado.estado === "listo" ? estado.borrador.id : null`), y la prueba
  del proveedor lo comprueba en `/presupuesto/componer`. `rutaDeVista` se reexporta sin cambios desde `hoja/logica.ts`.
  «Llevar a la Hoja» usa `MONEDAS` y `rotuloDeMoneda` de `comun/monedas.ts`. `CONOCIDAS` no cambia.
- **PDF por frente (8), cuadra con `vistas/frentes`.** Las filas de `vista_presupuesto` salen de
  `hoja.filas_del_presupuesto`, que recorre `claves_de_items(resultado.todos)` (`aplicacion/hoja.py:1182`). Es el mismo
  recorrido de `por_frentes` y de `repartir_por_frente`: mismas claves, grupos en el mismo orden (el de su primera
  aparición, sin frente al final) y subtotales con los totales exactos de las mismas partidas. En la sonda puse los
  renglones 1 y 8 en «Norte» y el 3 sin frente: `vistas/frentes` da Norte 1.392,84 · FRENTE A 1.348,74 · FRENTE B
  1.730,27 · Sin frente 219,28, y el PDF imprime los mismos cuatro subtotales en el mismo orden y el total 4.691,13. El
  agrupador corre bajo el cerrojo (`aplicacion/presupuesto_pdf.py:309`) y `hoja_vista.calculo` lo vuelve a tomar, como
  ya hacía `resumen` (el cerrojo es reentrante), con el cálculo del mismo `rev`. Un `agrupar` inválido da 422 sin eco
  (`_RutaExportar` hereda de `RutaSinEco`). El PDF por omisión de una obra con frentes cambia, y está declarado en
  RF-213, en el manual y en `docs/api.json` (`test_openapi` pasa).
- **`VistaGeneral.test.tsx` (`b3bba087`) no debilita la prueba.** `PanelArenera` pinta el bloque en «cargando» y el
  pedido sale de un efecto de `useCarga` (`comun/useCarga.ts:18-21`), así que el bloque puede verse antes del pedido.
  `waitFor(... toBe(1))` sigue fallando si nunca se pide o si ya van dos pedidos cuando mira. Lo que la prueba afirma
  (quien opera la arenera la ve y se pide) no cambia, y la de quien no la opera sigue contando 0 al instante.
- **Hallazgo 3**: las dos pruebas fuerzan la falla en `importaciones.anotar`, después de escribir el catálogo y el
  borrador, y matan los dos mutantes (arriba). **5**: con el panel abierto, el efecto vuelve a pedir una vez por `rev`,
  y no tras «Poner el frente» (`pedidaPara`); tiene sus tres pruebas. **6**: `especificacionesLegibles` parte en «; »
  solo antes de otra «clave=», el formato de `_pares_a_texto` (`aplicacion/hoja.py:427-428`); `hoja.py` no cambia.
  **7**: `_TILDES_DEL_CIERRE` ya no está y las pruebas del PDF siguen viendo «+ Administración». **10**: `_de_otro_tipo`
  da 409 aunque se pida reemplazar y deja el archivo igual; uno ilegible sí se puede reemplazar. **N6**: `_exigir_hojas`
  está en las dos rutas, con 422 sin eco. **N7**: el ERS lo dice.
- **`core/` y los congelados, intactos; sin datos reales** (arriba). `aplicacion/libro_a_la_hoja.py` importa
  `core.budget.moneda.moneda_del_proyecto`, que ya usaban `elaboracion` y `listas_para_armar`; leer del núcleo no lo
  cambia.


## Ronda 2: correcciones (2026-11-14, corrector)

Árbol `.worktrees/s2m4`, rama `feature/ola2`, desde `09848bd8`. Sin tocar `core/` ni los 50 archivos congelados del
experimento. Cada arreglo con su prueba en rojo vista antes y en su commit; datos FICTICIOS. R2-2 (CHANGELOG y ESTADO)
sigue siendo del orquestador.

| # | Estado | Rojo → verde | Qué se hizo |
|---|---|---|---|
| R2-1 MENOR | Hecho | `eb7bfb6e` → `74e2dbf9` | `adapters/hoja_empresa/retroceso.py` (nuevo) juzga el árbol de `patron_banda` con tres reglas: sin referencias hacia atrás; una repetición que se repite solo lleva átomos de un carácter, cuentas fijas y a lo sumo una parte variable seguida (en ronda) de un átomo obligatorio que no comparte caracteres con ella; y a lo sumo una parte variable «abierta». Reemplaza `_retroceso_catastrofico`. El banco entra en `test_libro_por_frentes.py` (17 rebuscados y 10 bandas legítimas que además se leen con `leer_banda`). Manual (§12, el párrafo de `patron_banda`) y RF-209 al día. Rojo: 17 failed, 10 passed. |
| R2-N1 NOTA | Hecho | `793ef8f0` → `0b047b0e` | `PresupuestoPorFrentes.tsx`: «Ver», el efecto del `rev` y «Poner el frente» numeran su pedido en un `useRef` común (`ultimo`) y solo se aplica la respuesta del último; el error de «Poner el frente» se dice siempre (el frente no se puso). Rojo: 2 failed, 6 passed. |
| R2-N2 NOTA | Hecho | `11fcecfd` → `c089d3aa` | El grupo de los renglones sin frente se rotula «(sin frente)» en la pantalla y en el PDF («Subtotal (sin frente)»), y un frente no puede llamarse «Sin frente» ni «(sin frente)» (sin distinguir mayúsculas, tildes ni blancos): 422 con `MENSAJE_RESERVADO` al ponerlo a mano y al llevar el libro (`FrenteReservado`, antes de abrir el borrador). `api/rutas/hoja_libro.py` lo suma a sus 422; la API no cambia de forma (`docs/api.json` igual). Rojo: Python 6 failed, 2 passed (`200 == 422`; el PDF imprimía «Subtotal de Sin frente»); front 1 failed. |
| R2-2 MENOR | No es del corrector | — | CHANGELOG y ESTADO los escribe el orquestador (encargo común). |

### R2-1: la defensa de `patron_banda`, simulada

Guion `scratchpad/ola2/corrector2/sim_r2.py` (con `defensas.py`, las opciones A y B, y C desde el módulo del
repositorio), Python 3.13.13 del `.venv`. «t real»: `re.search` con `re.IGNORECASE` (como `leer_banda`) en otro
proceso, con tope de 5 s, sobre un texto ficticio de ataque («a»×n + «!», «1»×n + «!»…; a lo sumo 600 caracteres);
incluye unos 0,22 s de arrancar el proceso. Las tres opciones conservan el tope de 300 caracteres.

- **A** (la del árbitro): toda repetición de cuenta variable (también `?`) dentro de otra que se repite es peligrosa;
  la de cuenta fija `{n}` se acepta; alternativa dentro de una repetición y referencia hacia atrás, rechazadas; a lo
  sumo 8 repeticiones sin tope por patrón.
- **B**: la estructura de A sin el tope de repeticiones, más medir el patrón en otro proceso, con 1 s de límite,
  contra textos construidos desde el propio patrón (cada carácter del patrón repetido 40 veces y la muestra que casa,
  repetida).
- **C** (elegida): `adapters/hoja_empresa/retroceso.py`. Una repetición que se repite solo lleva átomos de un
  carácter, cuentas fijas y a lo sumo una parte variable, seguida (en ronda) de un átomo obligatorio que no comparte
  caracteres con ella (el «.» de `(?:\.\d{3})*`, el espacio de `(?:\w+ )*`: marca dónde acaba cada vuelta); y a lo sumo
  una parte variable **abierta** en el patrón (abierta: lo que puede venir justo detrás comparte caracteres con ella,
  así que más de uno de sus finales sigue adelante; `\d+ km` no tiene ninguna, `.*de.*km` tiene dos).

**Peligrosos** (26: los 6 del árbitro, los 9 de la ronda 1 y 11 nuevos; «o» es la barra de la alternativa, que no se
puede escribir dentro de una tabla):

| Patrón (dentro de `(?P<minimo>…)(?P<maximo>b)`) | A | B | C | t real |
|---|---|---|---|---|
| `(?:a?a)+` (árbitro) | rechaza | rechaza | rechaza (sin separador) | 2,92 s (n=32) |
| `(?:a?a?)+` (árbitro) | rechaza | rechaza | rechaza (dos partes variables) | > 5 s |
| `(?:\d?\d)+` (árbitro) | rechaza | rechaza | rechaza (sin separador) | 3,72 s (n=32) |
| `(?:a?){28}a{28}` (árbitro) | rechaza | rechaza | rechaza (sin separador) | > 5 s |
| quince `[0-9]*` seguidos (árbitro) | rechaza | rechaza | rechaza (14 abiertas) | > 5 s |
| doce `.*` seguidos (árbitro) | rechaza | rechaza | rechaza (12 abiertas) | > 5 s |
| `(a+)+`, `(a*)*`, `([0-9]+)*`, `(a{1,9}){2,}` (ronda 1) | rechaza | rechaza | rechaza (sin separador) | > 5 s |
| `(a o a)*`, `(?:a o aa)+` (ronda 1) | rechaza | rechaza | rechaza (alternativa) | > 5 s |
| `(?P=minimo)`, `\1` (ronda 1) | rechaza | rechaza | rechaza (referencia) | > 5 s (n=2.000) |
| `x?` ×150 (ronda 1) | rechaza | rechaza | rechaza (largo) | 0,23 s |
| `(?:[0-9]+[.,]?)+` (miles mal escritos) | rechaza | rechaza | rechaza (dos partes variables) | > 5 s |
| `(?:\d{1,3}\.?)+` (miles mal escritos) | rechaza | rechaza | rechaza (dos partes variables) | > 5 s |
| `(\w+\s?)*`, `(?:\s*\w+)*` | rechaza | rechaza | rechaza (dos partes variables) | > 5 s |
| `(.*a){12}` | rechaza | rechaza | rechaza (sin separador) | > 5 s |
| `(?:,\d+\d+)*` | rechaza | rechaza | rechaza (dos partes variables) | 4,01 s (n=22) |
| `(?:a o b o ab)*` | rechaza | rechaza | rechaza (alternativa) | 0,22 s (con ese texto) |
| `a?` ×28 y `a` ×28, sin anidar | **acepta** | rechaza | rechaza (28 abiertas) | > 5 s |
| `a*a*a*a*` | **acepta** | **acepta** | rechaza (3 abiertas) | > 5 s (n=300) |
| `\d*\d*\d*` | **acepta** | **acepta** | rechaza (2 abiertas) | > 5 s (n=600) |
| `.*de (\d+).*km.*hasta.*(\d+) km` (descuidado) | **acepta** | **acepta** | rechaza (5 abiertas) | 6,47 s con 560 caracteres de «de 1 hasta km » (`descuidados.py`) |
| **Peligrosos aceptados** | **4** | **3** | **0** | |

**Legítimos** (cada uno lee su descripción ficticia con `leer_banda`, p. ej. «de 1.000 km y hasta 1.200,5 km» →
(1000, 1200,5)):

| Banda | A | B | C |
|---|---|---|---|
| la del paquete, la simple, la de `[0-9.]+` y la de espacios (las 4 de las pruebas) | acepta | acepta (0,25 a 0,28 s cada vez) | acepta |
| miles `\d{1,3}(?:\.\d{3})*(?:,\d+)?` («de X km y hasta Y km») | acepta | acepta | acepta |
| `\d+(?:[.,]\d+)*` | **rechaza** | **rechaza** | acepta |
| `(?:km o kms)?` | acepta | acepta | acepta |
| `(?:\w+ )*de … km y hasta … km` | **rechaza** | **rechaza** | acepta |
| «de X a Y km» con miles | acepta | acepta | acepta |
| «mayor(es) de» con `\s+` y miles (10 repeticiones sin tope) | **rechaza** | acepta | acepta |
| «más de X hasta Y km» con miles | acepta | acepta | acepta |
| un `.*?` entre los dos números | acepta | acepta | acepta |
| «entre X y Y kms?» con miles | acepta | acepta | acepta |
| «desde … kilómetros hasta …» (10 sin tope) | **rechaza** | acepta | acepta |
| miles con espacio o punto `\d{1,3}(?:[. ]\d{3})*` | acepta | acepta | acepta |
| **Legítimos aceptados** | **11 de 15** | **13 de 15** | **15 de 15** |
| aparte: `.*?de (…).*?hasta (…) km` (descuidado, no cuelga: 0,80 s con 1.040 caracteres) | acepta | acepta | **rechaza** (5 abiertas) |

Lo que decide: **A** deja pasar las cadenas polinómicas y no hay tope que sirva (el paquete tiene 4 repeticiones sin
tope y `\d*\d*\d*`, con 3, pasa de 5 s con 600 cifras), y rechaza cuatro bandas buenas. **B** mide con textos que no
siempre son el peor caso (no ve las tres polinómicas), cuesta 0,22 a 0,29 s de otro proceso cada vez que se lee el
perfil (cada auditoría y cada recálculo con VR4) y hereda los dos rechazos de forma de A. **C** rechaza los 26 y acepta
las 15 bandas; validar el patrón del paquete le cuesta 0,6 ms (y se recuerda: caché de 64 patrones). Su único rechazo
de más es el patrón con un `.*?` al principio, que no hace falta (la banda se busca en toda la descripción): el manual
lo dice.

Lo que C no ataja, dicho en su docstring: con una parte abierta lo peor que se acepta es cúbico en el largo del texto
(`\d*\d*b`, 0,1 s con 300 cifras iguales y 5,2 s con 1.000; `grado1.py`); una descripción de APU no trae mil
caracteres iguales. Es una heurística sobre el árbol, como la de la ronda 1, no una garantía: la garantía seguiría
siendo el patrón fijo con las palabras del perfil (la opción «mejor» de la ronda 1), que cambia el formato del perfil.
`re._parser` sigue siendo interno de la biblioteca estándar; si cambiara, las pruebas del banco lo dirían. Los mensajes
cambian de forma («patron_banda: <qué>: con algunos textos tardaría sin fin; escríbalo de otro modo»); los de la
ronda 1 siguen conteniendo su frase. Revertir: `git revert 74e2dbf9 eb7bfb6e`.

### R2-N1: respuestas viejas del presupuesto por frente

| Opción | Resultado (vitest, las dos pruebas nuevas) |
|---|---|
| Dejarlo (lo que había) | 2 failed: la vista pedida al abrir y llegada tarde deja «Total general: 4.701,13 Bs» sobre el del `rev` nuevo; la respuesta de «Poner el frente» que llega después de la del `rev` nuevo la tapa |
| Una guarda `vigente` por camino (como el efecto) | No alcanza: `abrir()` y `poner()` no tienen limpieza que la apague, y la de uno no sabe del pedido del otro |
| **Un contador común en un `useRef`; solo se aplica la respuesta del último pedido** (elegida, la del árbitro) | 8/8; el error de «Poner el frente» se muestra siempre (el frente no se puso) y una respuesta vieja suya no llama a `alAceptar` (la Hoja ya va por un `rev` posterior) |

Revertir: `git revert 0b047b0e 793ef8f0`.

### R2-N2: un frente que se llama como el grupo sin frente

Guion `scratchpad/ola2/corrector2/sim_n2.py`: tres renglones ficticios (uno con el nombre en cuestión, otro en
«FRENTE B», otro sin frente), con el `repartir_por_frente` real (los grupos del PDF) y el título de la pantalla.

| Opción | «Sin frente» a mano | «(sin frente)» a mano | hoja del libro «Sin frente» | hoja del libro «(Sin Frente)» |
|---|---|---|---|---|
| 1. Rechazar «Sin frente» a mano, rótulo «Sin frente» | 422 | aceptado, distinto | **se confunden** | aceptado, distinto |
| 2. Rótulo «(sin frente)», nada rechazado | distinto | **se confunden** | distinto | **se confunden** |
| 3. Rótulo «(sin frente)» y rechazar a mano «sin frente» y «(sin frente)» | 422 | 422 | distinto | **se confunden** |
| **4. La 3 y rechazar también los frentes del libro con esos nombres** (elegida) | 422 | 422 | 422 al llevar el libro, antes de tocar nada | 422 al llevar el libro |

El rótulo entre paréntesis es el de Excel para lo que no tiene valor («(en blanco)» en una tabla dinámica); se
compara sin mayúsculas, tildes ni blancos. Rechazar también «Sin frente» no es por choque sino porque quien lo teclea
casi siempre quiere quitar el frente: el mensaje le dice que deje el campo vacío (y a una hoja del libro con ese
nombre, que la renombre). El mensaje es fijo (no repite lo escrito). El PDF dice «Subtotal (sin frente)». Descartado:
un grupo sin título (la persona no sabe qué son esos renglones) y renombrar el frente que choca (cambia un nombre en
silencio). Revertir: `git revert c089d3aa 11fcecfd`.

### Lo que corrió el corrector

- **Rojos**, cada uno en su commit antes del verde: `eb7bfb6e` 17 failed, 10 passed; `793ef8f0` 2 failed, 6 passed;
  `11fcecfd` Python 6 failed, 2 passed (`assert 200 == 422`; el PDF imprimía «Subtotal de Sin frente 1.246,66») y
  front 1 failed.
- **pytest** (`.worktrees/tanda/.venv`, `-o addopts="" -q -p no:cacheprovider -W error`, cwd en `s2m4`):
  `test_api_hoja_libro`, `test_presupuesto_pdf`, `test_api_hoja_pdf`, `test_libro_por_frentes`,
  `test_api_libros_frentes`, `test_fusion_apu_por_hoja`, `test_hoja_empresa_apu_por_hoja`,
  `test_vial_banda_descripcion`, `test_aplicacion_sin_ciclos`, `test_openapi`, `test_api_hoja_exportar`,
  `test_arquitectura*`, `test_documentos_*` y `test_manuales_s5`: `854 passed`.
- **Front**: `npx vitest run src/paginas/hoja --maxWorkers=2`: `Test Files 47 passed (47)`, `Tests 790 passed (790)`;
  `npx eslint . --ignore-pattern "node_modules.viejo/**"` y `npx tsc -b --noEmit`: sin errores.
- `ruff check .`: «All checks passed!»; `git diff e2dfe116 --stat -- core/`: vacío. Ninguno de los 50
  `archivos_del_auditor` está en el diff. La API no cambia de forma (`test_openapi` pasa sin regenerar
  `docs/api.json`).
- **Datos**: todo lo nuevo es ficticio (patrones construidos, «FRENTE A/B», «Norte», «Acarreo ficticio…»); en esta
  ronda no se leyó ningún informe local.


## Ronda 3: veredicto (2026-11-14, árbitro Claude xhigh)

**Juzgado:** `git diff 09848bd8 eda4c374` (las correcciones de la ronda 2, 7 commits) en el árbol `.worktrees/s2m4`.

**VEREDICTO: APROBADO CON CAMBIOS.** 0 BLOQUEANTE, 0 MAYOR, 1 MENOR y 2 NOTA. R2-1, R2-N1 y R2-N2 están cerrados,
con una salvedad en R2-N1 (R3-1): la numeración de pedidos abre otra carrera más estrecha que la que cierra. No pide
otra ronda: R3-1 se arregla con su prueba antes del PR.

Ronda: 3 · Base: `09848bd8` · Cabeza: `eda4c374`

### Lo que corrió el árbitro (salida real)

- **Rojos**, cada uno en su commit (`git archive` en el scratchpad, sin escribir en el repositorio) y antes de su verde
  en la historia (`git rev-list --ancestry-path`). Cada commit rojo trae solo pruebas. `eb7bfb6e`: `17 failed, 10
  passed` (10 patrones rebuscados que se aceptaban y 7 bandas legítimas que se rechazaban, «una repetición dentro de
  otra»). `793ef8f0`: `2 failed | 6 passed` (las dos pruebas de R2-N1). `11fcecfd`: Python `6 failed` (cinco `assert 200
  == 422` y el PDF sin «Subtotal (sin frente) 1.246,66»); front `1 failed` (Received «Sin frente», Expected «(sin
  frente)»).
- **pytest de la cabeza** (`.worktrees/tanda/.venv`, `-o addopts="" -q -p no:cacheprovider -W error`, cwd `s2m4`):
  `test_libro_por_frentes`, `test_api_hoja_libro`, `test_presupuesto_pdf` y `test_vial_banda_descripcion`: `132 passed`.
- **vitest de la cabeza** (`npx vitest run src/paginas/hoja --maxWorkers=2`): `Test Files 47 passed (47)`, `Tests 790
  passed (790)`.
- **`retroceso.py`**: `retroceso_peligroso` devuelve `None` (acepta) para el patrón del paquete
  (`adapters/hoja_empresa/perfiles/apu_por_hoja.json:66`), para `\d{1,3}(?:\.\d{3})*` y para la banda completa con
  miles. El banco del diff (17 rebuscados rechazados, 10 bandas aceptadas y leídas con `leer_banda`) está en los 132
  verdes. En esta ronda no medí patrones nuevos en otro proceso: el juicio se apoya en ese banco y en la simulación del
  corrector.
- **Sonda del nombre reservado por la hoja del presupuesto** (el tercer camino, que no tiene prueba en el repositorio;
  en una copia de la cabeza): una hoja «Sin Frente» o «(sin frente)» con `hoja_presupuesto` → `422` con
  `MENSAJE_RESERVADO`, sin repetir el nombre y sin borrador: `2 passed`.
- **Sonda de R3-1** (front, en una copia; abajo): `2 failed` con el componente de la cabeza y `2 passed` con el
  anterior a la corrección (el de `793ef8f0`).
- `git diff --stat 09848bd8 eda4c374 -- core/ asistente/experimento/protocolo.json`: vacío. Ninguno de los 50
  `archivos_del_auditor` está en el diff.
- **Datos**: las palabras nuevas de las pruebas y del front son del oficio o ficticias («Acarreo», «Norte», «Frente»).
  No hay ningún nombre, código ni cifra de los libros.
- Las dos junctions de `node_modules` de las copias se quitaron con `rmdir` al terminar; la compartida sigue en pie.

### Hallazgos

| # | Sev. | Criterio · `archivo:línea` | Qué falla | Prueba o reproducción | Arreglo propuesto |
|---|---|---|---|---|---|
| R3-1 | MENOR | D1 · `frontend-desktop/src/paginas/hoja/PresupuestoPorFrentes.tsx:139` (`if (pedido !== ultimo.current) return;`), con `:99` y `:206` | La guarda de «Poner el frente» trata como vieja cualquier respuesta con un pedido posterior, también el de «Ver» en el mismo `rev`. Mientras el PUT está en vuelo, «Ocultar el presupuesto por frente» no se deshabilita (`ocupado` solo apaga el selector, el campo y «Poner»). Si se pulsa «Ocultar» y luego «Ver», `abrir()` toma un número nuevo y la respuesta aceptada del PUT se descarta: no se llama a `alAceptar`, así que la Hoja sigue en el `rev` viejo con la barra de estado atrasada hasta que la próxima edición choca con un 409 y recarga. Si además el GET de «Ver» se respondió antes que el PUT, la tabla queda sin el frente puesto: la vista atrasada que R2-N1 quería evitar. Es una regresión de esta corrección: el componente anterior pasaba la sonda. Es MENOR y no MAYOR porque la carrera es estrecha (ocultar y volver a abrir el panel durante un PUT) y la Hoja se recupera sola con el 409. | Sonda `SondaR3.test.tsx` (copia en el scratchpad): «Poner», «Ocultar» y «Ver» con el PUT diferido; luego el PUT responde `rev 4`. Cabeza: `alAceptar=0` en los dos casos; con el GET servido antes del PUT, las celdas no traen «Norte». `793ef8f0` (componente sin la corrección): `2 passed`. | Lo más simple: deshabilitar «Ocultar» mientras `ocupado`. Así el único pedido posterior a un PUT en vuelo es el del efecto de un `rev` nuevo, donde descartar es lo correcto. Si no, decidir por `rev` y no por número: aplicar una vista solo si su `rev` no es menor que el de la que se muestra, y llamar a `alAceptar` siempre que el PUT se aceptó y `r.rev` pase al `rev` más reciente de las props. Sumar la sonda como prueba (rojo antes del verde). |
| R3-N1 | NOTA | E1 · `aplicacion/frentes.py:166` (docstring de `repartir_por_frente`) | Dice «en «Sin frente»», pero el rótulo es ahora `SIN_FRENTE` = «(sin frente)» (`:66`). | Lectura. | Cambiar el texto a «(sin frente)» o nombrar `SIN_FRENTE`. |
| R3-N2 | NOTA | C2 · `tests/integration/test_api_hoja_libro.py` (bloque R2-N2) | El comentario del bloque promete los tres caminos («ni con una hoja del presupuesto»), pero solo hay pruebas para el frente a mano y para el frente del libro sin presupuesto. El código del tercero (`aplicacion/libro_a_la_hoja.py:370`, el mismo `any(es_reservado(r.frente) …)` sobre `r.hoja`) funciona: lo comprobé con la sonda de arriba. | Sonda: `2 passed`. | Sumar la prueba con `libro_presupuesto_por_hojas({"Sin Frente": …})` y `hoja_presupuesto=["Sin Frente"]`. |

### Lo que se cerró (verificado sin hallazgo)

- **R2-1, cerrado.** `retroceso.py` reemplaza `_retroceso_catastrofico` y lo usa `_construir`
  (`perfil_apu_por_hoja.py:213`), también al leer el perfil de la carpeta. Acepta el patrón del paquete y la banda de
  miles, y rechaza el banco de la ronda 2. El docstring y el manual (§12) ya no prometen una garantía: dicen que es un
  control de la forma. Sigue siendo una heurística sobre `re._parser`, como declara el módulo; la garantía seguiría
  siendo el patrón fijo con las palabras del perfil.
- **R2-N1, cerrado salvo R3-1.** Los dos caminos de la ronda 2 (la vista pedida al abrir que llega tarde y el PUT que
  llega después del `rev` nuevo) ya no dejan la vista atrasada (sus dos pruebas). No se pierden errores: el pedido que
  manda siempre informa el suyo, y el error de «Poner el frente» se muestra siempre (`:143-144`).
- **R2-N2, cerrado.** El nombre reservado se rechaza en los tres caminos con 422 y el mensaje fijo
  `MENSAJE_RESERVADO`, sin repetir lo escrito: a mano (`poner_frentes`, `frentes.py:193`), con el frente del libro sin
  presupuesto y con una hoja del presupuesto (`libro_a_la_hoja.py:370`, antes de abrir el borrador y de tocar el
  catálogo). `es_reservado` compara sin mayúsculas, tildes ni blancos (las cuatro variantes de la prueba). El PDF dice
  «Subtotal (sin frente)» y la pantalla «(sin frente)».
- **`core/` y los congelados, intactos; sin datos reales** (arriba).
