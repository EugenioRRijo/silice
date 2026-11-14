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
