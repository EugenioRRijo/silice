# Hoja del proyecto en la interfaz nueva: diseño de la migración (T10, fase 3a)

**Fecha:** 2026-10-19 · **Rama:** `inc/ruta-s2-mig-adm-empresa` (base `275946c`) · **Estado:** PROPUESTO. Lo juzga el
árbitro (`docs/planes/MANUAL_ARBITRO.md`, criterios B4, B2, C1 y D1 aplicados al diseño). Sin su aprobación no hay
código (`docs/planes/PLAN_MIGRACION_FINAL_STREAMLIT.md`, T10). Las decisiones que no son de ingeniería están en §10
(D-1 a D-10) con la recomendación más conservadora y reversible.

**Alcance de este documento:** solo diseño. No se escribió código de producción ni se tocó ninguna prueba.
**Qué se migra:** la página «Hoja del proyecto» de Streamlit (`ui/paginas/hoja.py`, 2308 líneas, en adelante **P**, y
la lógica de `ui/hoja.py`, 2835 líneas, en adelante **H**) a React + FastAPI. **Qué no:** el panel del asistente de IA
(§2.10 deja el punto de acoplamiento).

**Qué leí (enteros):** P y H; `asistente/` donde se cruzan con la hoja (`servicio.py`, `propuestas.py`,
`orquestador.py`, `privacidad.py`, `validacion.py`, `experimento/congelado.py`); `aplicacion/` (`entrega.py`,
`errores.py`, `subidas.py`, `estilo.py`, `atipicos.py`, `composicion.py` en lo que usa la hoja); `api/` (`main.py`,
`sesion_web.py`, `dependencias.py`, `acceso.py`, `admin_acceso.py`, `sin_cache.py`, `sin_eco.py`, `archivos.py`,
`caso_web.py`, `esquemas_informe.py`, `rutas/entregas.py`, `reajuste.py`, `proyectos.py`, `tablero.py`,
`precios_empresa.py`); `core/budget/cadena.py`, `equilibrio.py`; `seguridad/permisos.py`; `docs/ERS.md` (UC-14 a UC-16,
RF-52 a RF-66, RF-82); `docs/especificaciones/2026-10-04-sprint-final-prototipo-design.md` (§5, §9);
`frontend-desktop/PRODUCT.md`, `DESIGN.md`, `README.md`, `src/comun/*`, `src/paginas/componer`, `reajuste`,
`elaborar`, `src/visor`, `src/replica`; `tests/unit/test_arquitectura.py` (RM-1) y los nombres de las pruebas
`test_ui_hoja*.py`, `tests/integration/test_aceptacion_sf.py`.

**Convención de referencias:** `P:línea` = `ui/paginas/hoja.py`; `H:línea` = `ui/hoja.py`. Todo número de línea es del
commit `275946c`.

---

## 0. Resumen en diez líneas

1. La hoja se migra en **cuatro rebanadas secuenciales**, cada una entregable: **3b** lectura y navegación (más el
   traslado RM-1 de `ui/hoja.py` a `aplicacion/`), **3c** edición y borrador, **3d** guardado y versiones (guardar,
   primera versión, restaurar, cotizar, retirar, convertir moneda), **3e** importar plano y exportar Excel, con el cierre
   de paridad.
2. **El borrador vive en el servidor, en memoria, por ficha de sesión** (`aplicacion/hoja_borradores.py`), no en el
   navegador: es el equivalente exacto de `st.session_state[CLAVE_BORRADOR]` (P:96) y deja el punto de acoplamiento del
   asistente (§3.1). Alternativa descartada con motivo; plan B declarado (D-2).
3. Cada edición es una escritura **por sección** (espacio, cantidades, parámetros, plan, APU) que valida con las
   mismas funciones de H; si es inválida responde 422 con el mensaje de la clásica y el borrador **no cambia** («la hoja
   sigue con el último borrador válido», P:1217).
4. Montos y cantidades viajan como texto: cada cifra mostrada es `{texto, exacto}` (presentado a 2 decimales, como la
   clásica, y exacto). La interfaz no calcula ni redondea.
5. Toda escritura exige **sesión** (RF-82: el responsable es la persona de la sesión, nunca un campo); las lecturas de
   versiones guardadas aceptan clave de API o sesión con `editar_hoja`. Todo `no-store`; 422 sin eco.
6. **Hallazgo grave de proceso:** `ui/hoja.py` está en el congelado del experimento del asistente
   (`asistente/experimento/protocolo.json`, `archivos_del_auditor`). Moverlo a `aplicacion/` (RM-1) cambia su huella;
   la prueba `test_experimento_congelado_vigente.py` **ya falla en `275946c`** por mover `ui/composicion.py` (RM-1) y
   cambiar 5 líneas de `ui/hoja.py` (verificado, §1.1). Hace falta una decisión de Eugenio antes de 3b (D-1).
7. El traslado RM-1 rompe **tres pruebas existentes** por razones concretas (§5.3); se corrigen en 3b.
8. **No se reutiliza Univer** para editar: dibuja en lienzo (`CapaHalos` es «DOM sobre el lienzo»), no ofrece celdas
   accesibles por teclado ni lector de pantalla, y la hoja del proyecto son tablas tipadas con validación por campo en
   el servidor, no un libro (§3.4).
9. Diseño: Carbon g10, densidad `sm`, un solo `h1`, 9 pestañas en el orden de la clásica, tablas de texto editables con
   nombre accesible por celda, teclado (flechas verticales, Enter, Esc), sin desplazamiento horizontal de la página a
   1366×768 (las tablas anchas desplazan dentro de su región) (§7).
10. Paridad: el mismo caso ficticio OF-001 (total 2 703,86 USD, CV 2 137,44, PE 1 530,49 en el Día 23, 56,60 %) debe dar
    las mismas cifras y los mismos mensajes en la clásica y en la nueva (§9).

---

## 1. Hallazgos que cambian el plan (verificados)

### 1.1 `ui/hoja.py` está congelado por el experimento y la prueba que lo vigila ya falla

- `asistente/experimento/protocolo.json`, clave `archivos_del_auditor`, lista `ui/hoja.py` y `ui/composicion.py`
  (entre 49 archivos, junto con `asistente/validacion.py`, `orquestador.py`, `propuestas.py`,
  `privacidad.py`, `herramientas.py` y `catalogo.py`). `asistente/experimento/congelado.py:26-36` hace el SHA-256 de los bytes
  normalizados de cada uno y `congelado.json` guarda la huella (`auditor: 059fce6b…`, commit `cd46732`).
- Corrí `uv run --active pytest tests/unit/test_experimento_congelado_vigente.py -q -W error -p no:cacheprovider`: **falla**
  (`auditor cambio desde el congelado`). `git diff --stat cd46732 HEAD -- <archivos del auditor>` lista solo
  `ui/composicion.py` (777 líneas cambiadas: pasó a ser reexportación, RM-1, commit `a582847`) y `ui/hoja.py` (5 líneas:
  `HojaInvalida` pasó a `aplicacion/errores.py`, commit `bdf77cc`). Es decir, la guardia ya estaba rota antes de este
  diseño; nadie lo registró en bitácora (grep de `congelado` en `docs/bitacora/2026-10-19-*.md`: sin resultados).
- `docs/planes/RUTA_SESIONES.md:256` y la decisión RS-9 (Eugenio, 2026-10-18, opción A) dicen que **ningún archivo de
  `archivos_del_auditor` se toca**. Mover `ui/hoja.py` a `aplicacion/hoja.py` lo contradice. Las alternativas están en
  §5.5 y la decisión es **D-1** (recomendación: traslado byte a byte + re-congelar en un commit aparte, con aval
  expreso de Eugenio; mientras tanto, 3b no empieza).
- No pude determinar (no hay forma de leerlo en el repositorio) si ya se corrió alguna medición con el congelado vigente;
  la bitácora `2026-10-silice-090.md:223` y `:244` dice que el congelado real y la medición quedan pendientes de T20
  (publicación), lo que sugiere que no.

### 1.2 La cadena de sellos exige una sesión envuelta en cada escritura

`P:171` abre la sesión con `entrega.con_anexos_de_cadena(sesion)` → `cadena.anexos_por_omision(session, anexos_de_cadena)`
(`aplicacion/entrega.py:141-143`, `core/budget/cadena.py:255-261`). Cada versión nueva se marca «por sellar» y se sella
en `before_commit` (`cadena.py:275-289`) con el proveedor de anexos de la sesión; sin el envoltorio sella con
`anexos_ninguno` y `verificar_cadena(..., anexos_de=anexos_de_cadena)` da «Cadena rota … uno de sus anexos no coincide»
para una versión que copió filas `esp_*` (guardar y primera versión). `grep con_anexos_de_cadena api/` no encuentra uso:
**ninguna ruta de la API actual lo hace**. Toda ruta de escritura de la hoja debe usar la sesión envuelta (§4.3) y una
prueba de integración debe comprobar que la cadena queda íntegra tras guardar por la API (réplica de
`tests/unit/test_ui_hoja_responsable.py:113`).

### 1.3 Otros hallazgos de la lectura

| # | Hallazgo | Consecuencia |
|---|---|---|
| 1 | `_error_de_base` (P:216-221) y los mensajes `No se guardo nada: {error.orig}` (P:492, 533) incrustan `error.orig`, el texto del driver de SQLite, que puede traer SQL o rutas | C1: la API **no** repite `orig`; manda un mensaje fijo (§4.6). Diferencia deliberada, declarada |
| 2 | La clásica dice en la pestaña Trazabilidad solo historial y registros; el docstring de `aplicacion/entrega.py:150` dice que la pestaña también muestra el estado de la cadena (`estado_de_la_cadena`), pero P:2157-2213 no lo llama | La nueva lo añade (solo lectura, `GET /v1/hoja/cadena`, 3d): mejora declarada, reversible |
| 3 | Los mensajes de H están escritos sin tildes («guardo», «version», «catalogo»); el congelado y los mensajes del asistente dependen de ellos (`HojaInvalida` llega al validador) | B4 manda: los mensajes que salen de la lógica se conservan **idénticos**; los textos nuevos de la interfaz llevan tildes. Diferencia D1 inherente, declarada (D-3) |
| 4 | `precios_de_version` (H:2368) acepta `serie_indice`, pero P:1905 no lo pasa: la columna «Erosión por índice» de la clásica siempre sale vacía | La nueva la muestra solo si algún valor viene (como `InformeAuditoria` con impacto/observado) |
| 5 | `_moneda` (P:2068-2118) corre bajo la acción `editar_hoja` de la página, pero la matriz declara `convertir_y_reajustar` para «moneda del proyecto» (`seguridad/permisos.py:24`) | Hoy ambas son solo `arma`; la nueva exige `convertir_y_reajustar` en `/convertir` (la matriz es «la única fuente») |
| 6 | `HashRouter` (`frontend-desktop/src/App.tsx:3`) no es un enrutador de datos: `useBlocker` de React Router no está disponible (por la documentación de la librería; no lo probé) | No se puede vetar la navegación; no hace falta, porque el borrador sobrevive en el servidor (§3.1) |
| 7 | Ninguna ruta existente combina `RutaSinCache` (solo `auditorias_libro.py` y `produccion.py`) con `RutaSinEco` (las demás); son clases de ruta distintas | Hay que combinarlas **en el orden** `(RutaSinCache, RutaSinEco)`; en el orden inverso `RutaSinCache` atrapa el `RequestValidationError` antes que `RutaSinEco` y devuelve el 422 con eco (lectura de `sin_cache.py:33-42`, `sin_eco.py:36-46`). Una prueba lo fija (§6, 3b-B13) |
| 8 | La API se lanza como un solo proceso de `uvicorn` sin `--workers` (`operacion/lanzador.py:86-103`) | Estado en memoria del proceso es viable (precedente: `api/caso_web.py`, RM-2) |

---

## 2. Inventario de la página clásica

### 2.1 Qué es

- `render()` (P:2250-2306) exige `Accion.EDITAR_HOJA` (P:2252, `ui_sesion.exigir`); solo `arma` la tiene
  (`seguridad/permisos.py:58`). Un revisor no la ve.
- Orden de pintado: mensaje pendiente (P:2265) → selector de proyecto y versión con aviso de cambios sin guardar
  (P:2267) → panel del asistente (P:2268, **no se migra**) → contenedor del panel de guardado que se llena **al final**
  (P:2271, 2304) → control segmentado de 9 pestañas (P:2272) → pestaña activa → resumen publicado a la barra
  (P:2306).
- Solo se ejecuta la pestaña activa (`st.segmented_control`, P:2272-2278); el resultado se calcula **una vez por
  borrador** (`_calculo`, P:299-308).

### 2.2 Estado de sesión (`st.session_state`) y su equivalente

| Clave (P:línea) | Qué guarda | En la nueva |
|---|---|---|
| `hoja_borrador` (96) | el `Borrador` vigente (H:327) | `BorradorVivo.borrador` en el servidor |
| `hoja_partida` (97) | el borrador con que se sembraron los editores (para no reiniciar un editor con su propio recálculo) | el estado de las celdas del navegador lo gobierna React (sin `key` por generación); las semillas se piden al servidor al entrar en una pestaña |
| `hoja_abierta` (98) | la `VersionAbierta` (H:1540) o `None` | `BorradorVivo.abierta` |
| `hoja_abierta_en` (99) | `(ruta, proyecto, codigo)` | `abierta` + la ruta del caso (la ficha ya la fija `caso_web`) |
| `hoja_resultado` (100) | `(borrador, ResultadoHoja, cambios)` del último cálculo | `BorradorVivo.cache` ligado a `rev` |
| `hoja_generacion` (101), `hoja_selectores` (112) | contadores que reinician editores y selectores | no hacen falta en React (la clave de un campo no depende de ellos) |
| `hoja_ultima_pestana` (102) | detectar cambio de pestaña para re-sembrar | al montar una pestaña se piden semillas frescas |
| `hoja_excel` (103) | `(nombre, bytes)` del Excel preparado; se olvida al editar | la descarga se pide con el borrador actual; no hay estado intermedio |
| `hoja_accion_pendiente` (104) | acción que pidió la barra (`guardar_version`, `exportar_excel`, `precios`, `importar_plano`) | botones de la propia página; no hay barra |
| `hoja_importacion`, `hoja_plano`, `hoja_plano_directorio`, `hoja_plano_fusion`, `hoja_plano_mensaje`, `hoja_plano_abierto` (105-111) | flujo de importar plano | `BorradorVivo.importacion` (3e) |
| `hoja_mensaje` (113) | `(tipo, texto)` del último guardar, restaurar o cotizar | notificación de la página |
| `hoja_asistente*` (114-125) | sesión del asistente, pedido, proveedor, aviso, respuesta, resumen hipotético, aplicado, aceptadas | **no se migra** (§2.10) |
| `hoja_proyecto_de_la_barra` (107) | proyecto de la barra visto por última vez | el proyecto sale de `useAplicacion()` (cabecera), una sola fuente |

### 2.3 Selector de proyecto y versión (P:391-456) y aviso de cambios (15c)

- Lista de proyectos del caso, con la opción `SIN_PROYECTO = "(borrador nuevo, sin guardar)"` (P:139). Sigue al
  proyecto que se abre en la barra solo cuando éste **cambia** (P:376-388).
- Versiones: `historial_de_versiones` (H:2190); se ofrecen las no descartadas (si todas están descartadas, todas)
  (P:417); por omisión la vigente, si no la última (P:419); el rótulo marca « (vigente)» (P:427). Sin versiones:
  «Este proyecto aún no tiene versiones» (P:140, 430).
- Un proyecto sin versiones **adopta** el borrador que ya hay (P:434-438).
- Cambiar de versión con cambios sin guardar: advertencia «Tiene N cambios sin guardar. Si abre otra version se
  pierden: guarde primero o descarte.» (P:443-446) y dos botones «Descartar los cambios y abrir la version elegida» y
  «Seguir editando» (P:448, 453). Cerrar la pestaña del navegador **no** se podía interceptar (docstring P:28-30,
  «diferido declarado»).

### 2.4 Panel «Guardar version y exportar a Excel» (P:577-652)

Se pinta arriba y se llena al final de la ejecución (P:2269-2271). Contenido:

- Aviso «{n} cambios sin guardar. Si cierra la hoja o abre otra version se pierden.» (P:583-585) y, sin versiones, el
  aviso «{SIN_VERSIONES}. Describa el espacio (o importe un plano) y guarde la primera version abajo, con su fuente y su
  responsable.» (P:588-591).
- Expansor abierto si hay cambios o la barra pidió guardar (P:592).
- Subtítulos distintos para: sin proyecto (P:594-597), proyecto sin versión (P:598-602), versión abierta (P:603-607);
  advertencia de solo lectura (P:608-612).
- Campos: «Fuente de la medida (de donde salen los datos)» (primera versión) o «Fuente del cambio (por que y con que
  respaldo)» (P:613-619) y «Responsable» (P:620; con el acceso encendido no hay cuadro: muestra el usuario de la sesión,
  `ui/sesion.py:125-133`).
- El motivo para no guardar (P:621-635) sale de `motivo_para_no_guardar` (H:1786) o `motivo_para_no_crear_primera`
  (H:1882) o «Elija o cree un proyecto (barra superior) para poder guardar.»; botón «Guardar version» / «Guardar primera
  versión» (P:141, 637-643), deshabilitado si hay motivo o la versión es de solo lectura.
- «Preparar Excel» y, una vez preparado, «Descargar Excel» (P:644-652).

### 2.5 Las nueve pestañas

Orden (`PESTANAS`, P:83-93): **Espacio y metrajes · APU · Presupuesto · Plan y curva · Punto de equilibrio · Precios ·
Parámetros · Auditoría · Trazabilidad**.

#### 2.5.1 Espacio y metrajes (P:1190-1233)

- Flujo «Importar plano (DXF o IFC)» al inicio (§2.5.11).
- Ayuda (P:144-148, `_AYUDA_ESPACIO`).
- **Cinco tablas editables** (`num_rows="dynamic"`, P:1203-1210) con las columnas de `COLUMNAS` (H:148-177) y rótulos de
  `ROTULOS_DE_COLUMNA` (H:194-241). Las celdas son texto; las listas cerradas son selectores (P:1113-1137):

| Tabla (rótulo H:180) | Columnas (clave → rótulo) | Listas cerradas |
|---|---|---|
| origenes de medida | `id` Código · `tipo` Tipo de origen · `referencia` Referencia (`clave=valor; …`) | tipo: plano, dxf, ifc, levantamiento, supuesto, ia (H:246-251) |
| ambientes | `id` · `nombre` · `x0`, `y0` Esquina X/Y (m) · `largo` · `ancho` · `alto` (m) · `origen_id` Origen de la medida | ninguna |
| fuentes | `id` · `especialidad` · `tipo` Tipo de fuente · `ambiente_id` · `x`, `y` Posición X/Y (m) · `z` Altura (m) · `origen_id` | especialidad: agua, datos, electricidad; tipo: acometida_agua, montante_agua, colector_drenaje, rack, tablero |
| puntos | `id` · `nombre` · `especialidad` · `tipo` Tipo de punto · `ambiente_id` · `superficie` · `x`,`y`,`z` · `fuente_id` Fuente que lo alimenta · `circuito_id` · `especificaciones` (`clave=valor; …`) · `origen_id` (13 columnas) | especialidad; tipo: agua_fria, drenaje, datos, tomacorriente, iluminacion; superficie (valores de `SuperficiePunto`) |
| vertices de recorridos | `recorrido_id` · `punto_id` · `circuito_id` · `orden` Orden del vértice · `superficie` · `empotrado` · `pendiente` · `vertices` (`x,y,z; x,y,z`) | superficie (valores de `SuperficieTramo`); empotrado: vacío, si, no |

- Cada valor interno de una lista tiene un rótulo para la persona (`ROTULOS_DE_VALOR`, H:244-276; `rotulo_de_valor`,
  H:279). Se guarda el valor interno, se muestra el rótulo.
- **Validación** (todas en `espacio_desde_filas`, H:601-637, sobre texto): una fila en blanco no es error
  (`_construir`, H:504-519); un error de fila es `HojaInvalida("{rótulo}, fila {n}: {error}")` (H:518); las plantillas
  de error de campo: `"{campo}: {valor!r} no es un valor valido ({validos})"` (H:452), `"{campo}: {trozo!r} no tiene la
  forma clave=valor"` (H:462), `"vertices: {p!r} no tiene la forma x,y,z"` (H:481), `"vertices: un tramo necesita dos
  vertices x,y,z o mas, separados por «;»"` (H:484), `"{campo}: {texto!r} debe ser «si», «no» o quedar vacio"` (H:492),
  `"recorrido_id: el tramo debe nombrar su recorrido"` (H:564), `"orden: {x!r} no es un entero"` (H:568). Los números salen
  de `decimal_desde_texto` (`aplicacion/composicion.py:88`): solo punto decimal; «`'2,5' no es un numero decimal
  valido`». Las referencias cruzadas e ids duplicados los valida `Espacio.__post_init__`
  (`adapters/espacio/modelo.py:281-286`) y el error se envuelve en `HojaInvalida(str(error))` (H:634-637).
- `base` aporta lo que el editor no muestra: **circuitos, sobrescrituras de segmento y recorridos propuestos**
  (H:601-609). Un recorrido propuesto se va con su punto si éste se quita (H:617-623).
- Tras cada edición válida: `_poner_borrador` (P:256-275) completa las composiciones de partidas nuevas desde el
  catálogo (`completar_composiciones`, H:1757) y olvida resultado y Excel.
- Error: `"{error}. La hoja sigue con el ultimo borrador valido."` (P:1217).
- **Estado por fila** (RF-55): columna aparte, `st.dataframe` con «Fila» y «Estado» (P:1144-1157), para ambientes, fuentes
  y puntos (`TABLAS_CON_ESTADO`, H:189). Texto de H:1439-1480: `OK` si nada la toca; si no, los hallazgos agrupados por
  severidad de la más grave a la menos, `SEVERIDAD: a; b | SEVERIDAD2: c`; una partida sin APU en el catálogo se dice
  aparte, `PENDIENTE: sin APU en el catálogo (AF-SALIDA; …)`, y cuenta como `ERROR`.
- **Cantidades derivadas** (P:1167-1187): partida, descripción, unidad, cantidad (2 decimales), origen; vacío: «El
  borrador todavia no deriva cantidades: agregue un ambiente, una fuente y los puntos de agua, de datos o de
  electricidad.» (P:1170-1173).
- «Total del presupuesto» (P:1226); aviso de pendientes «{n} partida(s) no tienen composicion en el catalogo del caso:
  quedan pendientes y no suman al total.» (P:1227-1231); «Informe de auditoria» (P:1232-1233).

#### 2.5.2 APU (P:1488-1738)

- Tres paneles (`ANCHOS_APU = (1.1, 3.2, 1.6)`, P:1589): lista de partidas, tabla del APU, factores y cierre.
- Lista (P:1592-1613): buscador «Buscar partida» (código o descripción; sin tildes ni mayúsculas, `filtrar_partidas`,
  H:882-894); sin coincidencias «Ninguna partida coincide; se muestran todas.»; selección única (radio); texto escapado
  con `texto_seguro`.
- Tabla (P:1633-1677): para materiales, equipos y mano de obra, una tabla por rubro (P:1490-1494) con **solo la columna
  `cantidad` editable** (`disabled=` el resto, P:1658) y «Subtotal de {rubro}: {monto}» (P:1676); «Rendimiento
  (unidades por dia)» editable (P:1662). Validación `composicion_con_cantidades` (H:954-985): tabla con distinto número
  de líneas «`{grupo}: la tabla tiene {n} lineas y el APU {m}; en la hoja solo se edita la cantidad de cada linea (para
  agregar o quitar una, use Componer)`» (H:937-940), cantidad negativa «`{grupo}, fila {n}: la cantidad no puede ser
  negativa`» (H:949); error de pantalla `"{error}. La hoja sigue con el ultimo APU valido."` (P:1674).
- «Cambiar el insumo de una linea (en la copia de esta version)» (P:1518-1584): requiere versión abierta («Abra una
  version guardada: los insumos se eligen de su lista de precios.»); tipo de línea (material, equipo, mano_obra), línea,
  candidatos de la lista de precios de la versión (`insumos_candidatos`, H:1002-1023, hasta `LIMITE_INSUMOS = 300`, P:1515;
  con más pide acotar por descripción) y «Usar este insumo» (`cambiar_insumo`, H:1026-1056: toma descripción, unidad y
  precio; conserva la cantidad).
- Factores de la versión (P:1680-1685): los cuatro parámetros (§2.5.7) editables también aquí, antes de la tabla, para que
  los subtotales salgan con los factores vigentes.
- Cierre de partida (P:1688-1706): `filas_de_cierre` (H:897-930): Materiales, Equipos, Mano de obra, Costo directo,
  Administración, Con administración, Utilidad, Precio unitario, con nota; tres métricas y el Precio unitario (P:1726-1738);
  `Estado de {clave}: …` si la fila del presupuesto no está `OK`. Sin partidas valoradas: «Todavia no hay partidas
  valoradas: derive cantidades en Espacio y metrajes.» (P:1713).

#### 2.5.3 Presupuesto (P:1744-1790)

- Editor de **una sola columna**: `cantidad`; `clave`, `partida`, `descripcion`, `unidad` son de solo lectura (P:1756-1764).
- Escribir una cantidad a mano la saca del cálculo del sistema (DA-SF-5): R8 la marca ADVERTENCIA y queda en el registro
  (leyenda P:1750-1754). Validación `cantidades_desde_filas` (H:839-866): solo cuentan las filas cuyo valor difiere del
  calculado; error `"presupuesto, fila {n} ({partida}): {error}"` (H:855, 859) o `"…: la cantidad no puede ser negativa;
  escriba cero o una cantidad positiva"` (H:861-863); `"{error}. La hoja sigue con las ultimas cantidades validas."`
  (P:1773).
- Tabla «Calculado»: partida, cantidad, precio unitario, total, **Estado** (P:1774-1788); «Total del presupuesto»
  (P:1790). Sin renglones: «El presupuesto no tiene renglones todavia.» (P:1748).
- La clave de un renglón es `partida|origen_id` con `#2`, `#3` si se repite (`claves_de_items`, H:773-786).

#### 2.5.4 Plan y curva (P:1796-1848)

- Sin plan: «Esta version no tiene plan de trabajo, asi que no hay curva de inversion.» y el botón «Crear plan secuencial
  (una partida por periodo)» (P:1803-1806; `con_plan_secuencial`, H:1153-1157).
- Con plan: matriz editable partida × período con fracciones como texto, «Reparta cada partida entre los periodos: cada
  fila debe sumar exactamente 1» (P:1808-1811; `plan_como_filas`, H:1160-1181; `plan_desde_filas`, H:1184-1213). Errores:
  `"plan, partida {c}: …"`, `"…: la fraccion de {etiqueta} no puede ser negativa"` (H:1202-1204), `"plan, partida {c}: las
  fracciones suman {x} y deben sumar exactamente 1; repartala entre los periodos hasta completar 1"` (H:1209-1212); pantalla
  `"{error}. La hoja sigue con el ultimo plan valido."` (P:1827). Una celda vacía vale 0. El plan se ajusta a las partidas
  valoradas (`ajustar_plan`, H:1130-1150).
- «Curva de inversion»: tabla Período, Monto, Acumulado, % acumulado (P:1828-1841, `filas_de_curva`, H:1094-1108) y un
  gráfico de línea del acumulado (P:1842-1848, convierte a `float` solo para dibujar).

#### 2.5.5 Punto de equilibrio (P:1854-1868)

- No se edita (RS-4). Cuatro métricas (Ventas (contrato), Costo variable, Costo fijo, Utilidad), Punto de equilibrio y
  «Como % de las ventas» si hay punto, y una frase `texto_equilibrio` (H:1221-1238) para cada caso límite: «El presupuesto
  no tiene ventas: el punto de equilibrio no aplica.», «No existe punto de equilibrio: el margen de contribución no es
  positivo (los costos directos igualan o superan las ventas).», «El punto de equilibrio ({p}) no se alcanza dentro del
  contrato ({v}).», «Sin curva de inversión: el punto de equilibrio no se ubica en el plan.», «Se alcanza en {período}, al
  {n} % de ese período.». Definición: `core/budget/equilibrio.py:63-69` (CV = Σ cantidad × costo directo; CF = CV ×
  administración; PE = CF / m).

#### 2.5.6 Precios (P:1899-2025)

- Requiere versión abierta («Abra una version guardada para ver el origen de sus precios.»). Tabla de 21 columnas
  (`COLUMNAS_PRECIOS`, H:2266-2288; en pantalla P:1913-1944): Insumo, Código, Precio (2 dec.), Lista, Moneda, Fecha del
  precio, Tasa, Fecha de la tasa, Referencia, Cotización, Moneda original, Precio original, Fuente de la tasa, Fuente,
  Propio/heredado, Erosión USD/Bs/% (×100)/por índice, Estado. Se evalúa a **hoy** (P:1906) y es solo lectura sobre la
  versión **guardada**, no sobre el borrador.
- Botón «Buscar variaciones atípicas de precio» (`atipicos.ROTULO_BOTON`, P:1889-1896): solo lee; sin el extra `ml` lo dice.
- **Cotizar** (formulario P:1954-1993): insumo, precio cotizado (texto), proveedor, número, fecha (por omisión hoy),
  evidencia opcional, responsable. Con cambios pendientes no se ofrece: «Cotizar crea una version nueva desde la guardada:
  guarde o descarte primero los {n} cambios pendientes.» (P:1946-1951). Errores `"{error}. No se guardo nada."` (P:1985);
  éxito «Se guardo la version {n} con la cotizacion de {c}.» y reabre la nueva (P:1989-1993).
- **Retirar cotización** (P:1994-2025): solo si hay cotizadas; motivo y responsable; éxito «Se guardo la version {n} sin la
  cotizacion.». Lógica `cotizar`/`retirar_cotizacion` (H:2074-2126), ambas en `_en_una_transaccion` (H:2030-2045).

#### 2.5.7 Parámetros (P:2028-2118)

- Cuatro cuadros de texto exactos: `fcas`, `bono_alimentacion`, `administracion`, `utilidad` (`CAMPOS_PARAMETROS`, H:1114;
  rótulos P:2030-2035). Validación `parametros_desde_texto` (H:1117-1124): `"parametros: {error}"`; pantalla `"{error}. La
  hoja sigue con los ultimos parametros validos."` (P:2053). Un cambio válido recalcula todos los APU. «Total del
  presupuesto».
- **Moneda** (P:2068-2118): «Moneda del proyecto: {X}»; con cambios pendientes «Cambiar la moneda crea una version nueva
  desde la guardada: guarde o descarte primero los {n} cambios pendientes.»; formulario: moneda destino, tasa del BCV
  (venta o compra), fuente, responsable → `convertir` (H:2129-2165): usa la tasa aplicable a **hoy**; sin tasa en los 7
  días anteriores, `HojaInvalida("No se convirtio nada: …")`; éxito «Se guardo la version {n}, convertida a {destino}.».

#### 2.5.8 Auditoría (P:2124-2128)

El informe de auditoría con todas las reglas sobre el borrador vigente, siempre (`mostrar_informe`, `ui/resultado.py:44-82`):
veredicto, reglas evaluadas con su cuenta, tabla de hallazgos (#, Regla, Severidad, Partida, Descripción, Impacto,
Observado, Esperado, Origen). Lleva **R17** (conexión de cada punto) ligada al espacio que se elabora (§2.6).

#### 2.5.9 Trazabilidad (P:2157-2213)

- Requiere versión abierta. Tabla «Versiones del proyecto» (Versión, Fecha, Motivo (`elaborada` si vacío), Sale de,
  Cambios, Vigente) y «Registro de cambios de la version {c}» (Objeto, Clave, Campo, Antes, Despues, Fuente, Responsable,
  Fecha y hora) o «Esta version no nacio de una edicion: no tiene registros de cambio.» (P:2199).
- **Restaurar** (formulario P:2203-2213; `restaurar`, H:2048-2071): versión a restaurar, fuente, responsable; con cambios
  pendientes «Guarde o descarte los cambios pendientes antes de restaurar otra version.» (P:2201). Éxito «La version {c}
  se restauro como la version {n} (la vigente).» (P:2153); error «No se restauro nada: …» (P:2151).

#### 2.5.10 Crear plan, importar plano (UC-14) (P:1236-1485)

Flujo dentro de la pestaña Espacio, expansor «Importar plano (DXF o IFC)» (P:1253, 1464-1485):

1. Subir `.dxf` o `.ifc` y «Leer plano» (P:1281-1298). `formato_de_plano` (H:2603) rechaza otra extensión **antes de
   escribir**: «El archivo «{nombre}» no es un plano que se pueda importar. Suba un plano en formato DXF o IFC.»; sin archivo:
   «Elija primero un archivo de plano (DXF o IFC) y pulse Leer plano.» (P:1284); el nombre se guarda con
   `guardar_subida` (nombre seguro, `aplicacion/subidas.py:56-85`) en una carpeta temporal de la sesión (P:1268-1274).
2. `leer_plano` (H:2614-2638) nunca lanza por un archivo malo: devuelve `RECHAZADA` o `DETENIDA` (`pide_unidad`); lanza
   `HojaInvalida` si falta instalar el lector (`uv sync --extra planos|civil`).
3. `RECHAZADA`: «No se pudo importar «{archivo}»: {mensaje}» y «Descartar la importación» (P:1443-1446). `DETENIDA`: selector
   «Unidad del dibujo» (`UNIDADES_DE_PLANO`: m, cm, mm, dm, in, ft, H:2577) y «Continuar con esta unidad» (P:1400-1403,
   1301-1311).
4. `IMPORTADA`: «Informe de la importación de {archivo}», cuatro conteos (`resumen_de_importacion`, H:2720), tabla del informe
   (`filas_del_informe`, H:2727), **alturas pendientes** (un campo por ambiente, metros, coma o punto, `0 < h ≤ 250`,
   H:2750-2761; todo o nada, P:1319-1330), **circuitos por declarar** (cuatro enteros por circuito; fase, neutro, tierra ≥
   0 y puntos máximos ≥ 1, H:2790-2819; todo o nada, P:1333-1350), aviso `_AVISO_PENDIENTES` (P:1248-1251).
5. «Fusionar con el espacio del borrador» (P:1353-1374; `fusionar_plano`, H:2822-2835): las filas entran **al borrador**, no
   a una versión (DA-SF-6); mensaje de éxito P:1367-1373; guarda `ResumenDeFusion` (H:2667-2717, que cuenta el informe sin
   repetir) para «Informe de la última fusión».
6. «Descartar la importación» (P:1314-1316).

#### 2.5.11 Barra superior de la clásica

`ui/barra.py` (herramientas Proyecto, Importar plano, Precios, Auditar, Guardar versión, Exportar Excel) le pasa acciones a la
hoja con `pedir_accion` (P:462-469, 2255-2264). En la interfaz nueva no hay barra: cada acción es un botón de la página.

### 2.6 Reglas transversales que hay que conservar

| Regla | Dónde | Cómo se conserva |
|---|---|---|
| El borrador es inmutable; cada edición crea otro con `replace`; hay cambios si `cambios_entre(abierta.borrador, actual)` no es vacío | H:327-354, 1395-1409; P:299-308 | `BorradorVivo` guarda ambos; `cambios` se recalcula una vez por `rev` |
| Una edición inválida no cambia el borrador | P:1213-1217, 1667-1674, 1765-1773, 1821-1827, 2048-2053 | 422 y borrador intacto (§4.5) |
| **R17** se agrega a *cada* elaboración, a guardar y a crear la primera versión, y nunca se guarda en el borrador de sesión | P:286-296, 480-487, 520-529; H congelado | `aplicacion/hoja_vista.elaborar(borrador)` es la única vía; prueba como `test_ui_hoja_conexion.py` |
| Las reglas extra (R11/R12) se evalúan al abrir a la fecha de hoy y no cuentan como cambio | H:1716-1720, 327-354 | idéntico (`fecha_evaluacion=hoy`) |
| Abrir una versión sin instantánea la crea y la registra (UC-15e); si una partida no tiene composición vigente queda **solo lectura** | H:1698-1703, 1556-1562, 1625-1641 | `POST /borradores` (escribe, solo cuenta) |
| El espacio de una versión creada por restaurar/cotizar/revalorar/convertir es el de su `version_origen` | H:1536, 1588-1613 | `espacio_de_version` sin cambios |
| Guardar exige fuente y responsable; sin cambios no hace nada; toda la escritura en una transacción | H:1786-1879 | §4.4 (S1), todo o nada |
| Primera versión: lista **vigente** a la fecha, moneda del proyecto = moneda de la lista, plan secuencial si no hay, un solo `RegistroCambio` `version/creacion` | H:1898-2027 | §4.4 |
| `completar_composiciones`: una partida nueva toma su APU del catálogo y desde entonces es parte de la copia de la versión | H:1757-1780 | dentro de la sección `espacio` |
| El Excel se genera solo al pedirlo | H:2546; P:547-574 | `GET …/excel` |
| `responsable` = usuario de la sesión, diga lo que diga el cuadro (RF-82) | `ui/sesion.py:118-123` | la API no lee un `responsable` del cuerpo |

### 2.7 Permisos por acción

| Acción de la clásica | Control en la clásica | Control en la nueva |
|---|---|---|
| Ver y usar la hoja | `ui_sesion.exigir(Accion.EDITAR_HOJA)` (P:2252) | `EDITAR_HOJA` (clave o sesión) para leer versiones guardadas; **solo sesión** para borradores |
| Abrir (escribe la instantánea) | página | solo sesión, `EDITAR_HOJA` |
| Editar en el borrador | página | solo sesión, `EDITAR_HOJA`; el borrador es de la ficha que lo creó |
| Guardar, primera versión, restaurar, cotizar, retirar | página; responsable = sesión (`responsable_de_la_hoja`, P:202-209) | solo sesión, `EDITAR_HOJA` |
| Convertir moneda | página (acción de la página) | solo sesión, `CONVERTIR_Y_REAJUSTAR` (D-4) |
| Exportar Excel | página (incluye hojas de control, P:560) | `EDITAR_HOJA` (clave o sesión), lectura |
| Importar plano | página | solo sesión, `EDITAR_HOJA` |
| Panel del asistente | `Accion.EDITAR_HOJA` + proveedores de la instalación | fuera de alcance |

Roles: `arma` tiene `EDITAR_HOJA` y `CONVERTIR_Y_REAJUSTAR`; `revisa` y `administrador` no (`seguridad/permisos.py:57-72`).

### 2.8 Guardado, cadena y sello

- `guardar_version` (H:1817-1879): con `cambios_entre` vacío no hace nada (devuelve `None`); si faltan fuente o responsable lanza
  `HojaInvalida(motivo)`; si `solo_lectura` lanza «Esta version esta en solo lectura: alguna de sus partidas ya no tiene
  composicion vigente en el catalogo, asi que recalcularla cambiaria sus precios.». En **una** `Session`: completa
  composiciones con la lista de la versión abierta, `siguiente_codigo`, `elaborar_borrador(borrador, codigo=nuevo)` (con R17),
  `crear_esquema_espacio` si hay espacio, `guardar_edicion(...)` con el gancho que copia las filas `esp_*` con la clave de la
  versión nueva, `commit`; ante cualquier excepción `rollback` y propaga. Devuelve `VersionGuardada(codigo, cambios, total)`.
- `crear_primera_version` (H:1898-2027): ver §2.6; `HojaInvalida` si falta fuente/responsable, el proyecto no existe o ya
  tiene versiones, la hoja está vacía, no hay lista vigente o la moneda no coincide.
- **Sello:** al confirmar, `core/budget/cadena.py` escribe el eslabón de cada versión nueva con `huella_contenido`,
  `huella_cambios` y `huella_anexos` (el anexo de espacio, `anexos/espacio.json`) y el usuario que guardó (§1.2).
- **`RegistroCambio` por celda** con fuente, responsable y fecha-hora; claves por tipo (`metraje`, `apu`, `cantidad`,
  `parametro`, `plan`) en H:1243-1409. Oráculo: `test_aceptacion_sf.py:329-347`.

### 2.9 Excel de la hoja

`excel_de_hoja_en_bytes` (H:2546-2564) → `exportar_excel` (H:2518-2543) → `core.budget.exportar_hoja`: una hoja por pestaña
más Trazabilidad y Auditoría, con fórmulas vivas, más las hojas que `core` no conoce: «Espacio y metrajes» y una por tabla
(`tablas_de_espacio`, H:2477-2515) con su Estado, «Precios» (`tabla_de_precios`, H:2442-2474) y las de control
(`ui.control.tablas_de_control`, `aplicacion/control.py`). Nombre `hoja_{codigo}.xlsx` o `hoja_borrador.xlsx` (P:573).
Error: «No se pudo preparar el Excel: …» (P:571). Oráculo de contenido: `tests/integration/test_aceptacion_sf.py:417-470`.

### 2.10 Dependencias con `asistente/*` y punto de acoplamiento

- **`asistente/*` importa `ui.hoja`** (no `ui.paginas.hoja`): `orquestador.py:59` (`Borrador`, `HojaInvalida`), `privacidad.py:24`
  (`Borrador`), `propuestas.py:20-26` (`PREFIJO_ORIGEN_IA`, `Borrador`, `HojaInvalida`, `espacio_desde_filas`,
  `filas_desde_espacio`), `servicio.py:29-30` (`hoja`, `Borrador`, `HojaInvalida`; usa `hoja.elaborar_borrador` y
  `hoja.guardar_version` en comentario y `:254`), `validacion.py:34`, `experimento/banco.py:30`, `experimento/ejecucion.py:43-44`.
  Los `scripts/` (`medir_rnf11.py`, `seed_of001.py`, `prueba_real_asistente.py`) y 48 archivos de pruebas también.
  **`ui/hoja.py` no desaparece:** queda como reexportación y esos módulos no se tocan (también porque están congelados).
- **Lo que la página entrega al asistente** (P:754-871): `auditar=lambda b: _elaborar(b).elaboracion.informe` (con R17),
  el borrador vigente, el proyecto y la versión abierta, y `ia_servicio.decidir(..., sobre=borrador)` que devuelve un
  `Borrador` nuevo que la página fija con `_poner_borrador(resembrar=True)` (P:861); `CLAVE_FUENTE` se rellena con
  `ia_servicio.fuente_del_cambio` (P:865-866); tras guardar, `_cerrar_asistente_al_guardar` (P:932-952) marca las sesiones con
  propuestas aceptadas con la versión en que entraron.
- **Punto de acoplamiento que deja esta migración** (sin construir el panel):
  1. **Servidor:** `aplicacion/hoja_borradores.py` expone `obtener(huella, id) -> BorradorVivo` y `reemplazar(huella, id,
     borrador, rev) -> BorradorVivo` (sube `rev`, invalida la caché). Un futuro `api/rutas/asistente_hoja.py` toma el borrador
     vivo, llama a `asistente.servicio.proponer/decidir` y lo reemplaza. Nada del asistente entra en `aplicacion/hoja*.py`.
  2. **Auditor:** `aplicacion.hoja_vista.elaborar(borrador)` (con R17) es el `auditar` que necesita `Servicios`.
  3. **Guardar:** `POST …/guardar` devuelve `codigo` y `proyecto`, y acepta un campo `fuente` que el asistente puede
     proponer; la marca «sesión guardada» (`registro.marcar_guardada`) la hará la ruta del asistente al ver el guardado, no
     la hoja.
  4. **Interfaz:** `src/paginas/hoja/` reserva una región `<aside aria-label="Asistente de IA" hidden>` fuera de las
     pestañas (vacía y oculta, sin contenido muerto) y exporta `useBorradorHoja()` (id, `rev`, `alCambiar(resumen)`), que el
     panel futuro usará para pedir de nuevo las vistas después de decidir una propuesta.

### 2.11 Lo que **no** se migra en esta tarea

Panel del asistente de IA (P:655-1103); `_publicar_resumen` y la línea de estado de la barra (P:2227-2247, ahora del marco de
Streamlit); las acciones de la barra (`ACCION_*`); `CLAVE_PROYECTO_DE_LA_BARRA`; la opción «borrador nuevo, sin proyecto»
(D-7); el retiro de Streamlit (decisión pendiente documentada en T12).

### 2.12 Mensajes de la clásica que la nueva debe reproducir o cambiar

(La columna «Nueva» dice si el texto es **idéntico** —sale de `aplicacion/hoja.py`— o **con tildes** —lo compone la
interfaz nueva—. La prueba de paridad compara con `normalizar_texto` (sin tildes ni mayúsculas) cuando cambia solo la
ortografía.)

| Texto de la clásica (origen) | Nueva |
|---|---|
| `parametros: {campo}: {valor!r} no es un numero decimal valido` (H:1124, `composicion.py:97`) | idéntico, en el `detalle` del 422 |
| `{rótulo}, fila {n}: {error}` (H:518) y demás de H (listados en §2.5) | idéntico |
| `El proyecto {p!r} no tiene una version {c!r}: elija una de la lista.` (H:1572) | idéntico, 404 |
| `No hay cambios para guardar: edite alguna celda primero.` (H:1795) · `Escriba la fuente del cambio: por que se cambia y con que respaldo.` (H:1797) | idéntico, 422 |
| `Se guardo la version {c} con {n} cambios registrados.` (P:497-500) | con tildes: «Se guardó la versión {c} con {n} cambios registrados.» |
| `Tiene {n} cambios sin guardar. Si abre otra version se pierden: guarde primero o descarte.` (P:443-446) | con tildes |
| `No se guardo nada: {error.orig}` (P:492, 533) | «No se guardó nada: {mensaje del dominio}»; si es un error de la base, mensaje fijo sin `orig` (§4.6) |
| `La hoja sigue con el ultimo borrador valido.` y variantes (P:1217, 1674, 1773, 1827, 2053) | con tildes, compuesto por el front después del `detalle` |
| `Se creo y registro la instantanea … ({n} partidas): sus APU ya no cambian si cambia el catalogo.` (P:346-351) | con tildes; el servidor manda `instantanea.creadas` y el texto lo arma el servidor (una sola copia) |

---

## 3. Decisiones de arquitectura

### 3.1 Dónde vive el borrador: servidor, en memoria, por ficha (decisión)

| Criterio | A. Borrador en el servidor (elegida) | B. Borrador en el navegador, API sin estado |
|---|---|---|
| Paridad con `st.session_state` (B4) | exacta: es el mismo `Borrador` | hay que serializar y reconstruir (`ediciones` → `Borrador`) en cada recálculo |
| Lo que el editor no muestra (circuitos, sobrescrituras, recorridos propuestos, H:601-609) | queda en el objeto | el navegador debe reenviarlo opaco (un `complemento` del espacio) |
| Tamaño de cada petición | solo la sección editada | el borrador entero, o sus diferencias |
| Recargar la página (F5) / cambiar de proyecto en la cabecera | el borrador se puede **retomar** (`GET /borradores`) | se pierde, salvo `sessionStorage` (datos de la empresa en el navegador; contradice el espíritu de RT-9) |
| Asistente futuro (§2.10) | `proponer/decidir` operan sobre el `Borrador` vivo | habría que convertir `Borrador` → ediciones (inversa) |
| Costo | estado en memoria (se pierde si se reinicia la API); ciclo de vida (TTL, tope) | lógica de ediciones y reconciliación en el navegador |
| Reversibilidad | una capa (`hoja_borradores.py`) detrás de la ruta | — |

- **Precedente:** `api/caso_web.py` ya guarda en memoria del proceso el caso elegido por ficha (RM-2) y declara su costo (se
  pierde al reiniciar). La API corre como un solo proceso (§1.3-8).
- **Ciclo de vida** (valores a ratificar, D-9): como máximo **4 borradores por ficha** (el más antiguo se descarta);
  vencen a las **8 h** sin uso; se olvidan al cerrar sesión o vencer la ficha (se enganchan en `caso_web.olvidar/heredar/
  olvidar_todo`, que ya se llaman en esos eventos: `sesion_web.py:84`); un borrador de otra ficha **no existe** (404, no 403,
  para no confirmar ids ajenos). `id` = `secrets.token_urlsafe(16)`; nunca se registra.
- **Mensaje cuando falta** (reinicio, vencimiento, descarte): 404 con «Ese borrador ya no está en el servidor (se reinició
  Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.» — es el costo declarado de la
  alternativa A.
- **Concurrencia dentro de un borrador:** cada borrador lleva un cerrojo y un contador `rev` (sube con cada cambio aceptado).
  Toda escritura manda el `rev` que vio; si no coincide, 409 «El borrador cambió en otra ventana…». El navegador manda **una
  petición a la vez** por borrador (cola con coalescencia: la última edición gana) para no chocar consigo mismo.
- **Plan B:** si la medición de 3c (§6) muestra que el estado en memoria no convence a Eugenio o al tutor, pasar a B cambia
  las rutas de `…/borradores/{id}/…` por un solo `POST /v1/hoja/calculo` con las ediciones; el modelo `Borrador` y todas las
  funciones de `aplicacion/hoja.py` no cambian. Es la decisión D-2.

### 3.2 Una escritura por sección; validación en el servidor con las funciones de H

Secciones y la función de H que las valida (tal cual, sin reimplementarla):

| Sección | Petición | Función |
|---|---|---|
| espacio | las 5 tablas de texto | `espacio_desde_filas(filas, base=borrador.espacio)` (H:601) |
| cantidades | filas tocadas `{clave, cantidad}` | `cantidades_desde_filas` (H:839) |
| parámetros | 4 textos | `parametros_desde_texto` (H:1117) |
| plan | matriz | `plan_desde_filas` (H:1184), o `con_plan_secuencial` (H:1153) |
| APU de una partida | cantidades por rubro + rendimiento | `composicion_con_cantidades` (H:954) |
| insumo de una línea | `{tipo, indice, insumo}` | `insumos_candidatos` + `cambiar_insumo` (H:1002, 1026) |

Tras aceptar: `completar_composiciones` (si cambió el espacio o las cantidades), `rev += 1`, caché invalidada.

### 3.3 Cifras: `Monto = {texto, exacto}`

`texto` = `formatear_decimal(x, DECIMALES_PRESENTACION)` (2 decimales, `core/verification/texto.py:216`), como la clásica; `exacto` =
`format(x, "f")`. El navegador pone `formatoEsVe(texto)` a la vista y deja `exacto` en el `title` y en un texto accesible (D1).
Las celdas **editables** (cantidades, rendimiento, parámetros, plan, tablas del espacio) muestran el texto que escribió la
persona o el exacto que devolvió el servidor. Nunca `Number()`/`parseFloat` sobre un monto; la única conversión a número es la
que ya hace `CurvaPlanAvance` para trazar el gráfico (no para mostrar).

### 3.4 Univer no se reutiliza

- `frontend-desktop/README.md` y `DESIGN.md`: el visor es de **solo lectura** («lente»), dibuja con Univer en un lienzo y la
  capa de halos es «DOM sobre el lienzo» (`CapaHalos`). `src/replica/aUniver.ts` convierte el contrato de un **libro**
  `.xlsx` (`/v1/libros/replica`); la hoja del proyecto no es un libro.
- Una celda de lienzo no es un campo con nombre accesible, ni recibe foco de teclado como un `input`, ni la lee un lector de
  pantalla (D2). La edición necesita validación por campo con el mensaje del servidor, listas cerradas con rótulos y filas
  dinámicas: Carbon `TextInput`/`Select` en una `Table` ya lo hace (`componer/TablaInsumos.tsx`, `reajuste/FilasEditables.tsx`).
- Las funciones de edición de Univer fuera del conjunto `@univerjs/preset-sheets-core` pueden ser de pago (`@univerjs-pro/*`
  está prohibido por `npm run licencias`, README); no lo verifiqué más allá de esa regla del repositorio.
- **Posible uso futuro (fuera de este alcance):** mostrar el Excel exportado en el visor existente (solo lectura) como vista
  previa; no es parte de la paridad.

---

## 4. Contrato de API

### 4.1 Reglas comunes (todas las rutas de `/v1/hoja`)

| Regla | Detalle |
|---|---|
| Módulo | `api/rutas/hoja.py` (esquemas en `api/esquemas_hoja.py`); lógica en `aplicacion/hoja*.py`; **la API no importa `ui`** |
| Clase de ruta | `class _RutaHoja(RutaSinCache, RutaSinEco)` en ese orden (§1.3-7); `mensaje_por_omision = "Los datos de la hoja no tienen la forma esperada: escriba cada celda como texto."` |
| Acceso de lectura | `Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))` (`api/sesion_web.py:117`): clave de API **o** sesión con rol `arma`; con sesión, CSRF y `Origin` en métodos que escriben |
| Acceso de escritura y de borradores | el mismo, más **solo cuenta**: con `X-Silice-Clave` → 403 «La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve.» (se generaliza `api/admin_acceso._solo_cuenta` con un parámetro `mensaje`, sin cambiar su comportamiento actual) |
| Sesión del caso | `SesionDep` (caso de la ficha, RM-2). Las escrituras usan `con_anexos_de_cadena(sesion)` (§1.2) |
| Responsable | siempre `activa.usuario` (`Nombre <login>`); **ningún campo `responsable` en el cuerpo** (RF-82) |
| Montos | texto; `Monto {texto, exacto}`; ningún `float` en el JSON (una prueba recorre la respuesta) |
| Errores | `{"detalle": str}` (manejador de `api/main.py`); 401 sin sesión, 403 rol/CSRF/Origin/clave, 404 no existe, 409 conflicto de estado, 422 dato inválido, 503 la base no se pudo abrir |
| Caché | `Cache-Control: no-store` en éxito **y** en error (`RutaSinCache`) |
| 422 | sin eco de lo enviado: `RutaSinEco` con `mensaje_sin_eco` por ruta; los errores de **dominio** (`HojaInvalida`) llevan el mensaje de la clásica |
| Tamaños | cada texto de celda ≤ 500 caracteres (`Annotated[str, Field(max_length=500)]`); filas por tabla: origenes ≤ 5 000, ambientes ≤ 1 000, fuentes ≤ 1 000, puntos ≤ 5 000, tramos ≤ 20 000 (SUPUESTO declarado, D-9: los topes del anexo S3 §8.4 son 5 000 ambientes y 50 000 puntos, `adapters/espacio/serie.py:40-41`; el caso medido por RNF-11 es de 500 puntos); cuerpo ≤ 8 MiB |
| Ids en la ruta | `id` del borrador: `Annotated[str, Path(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]` |
| Nada armado con la entrada | ninguna ruta del servidor se arma con texto del usuario; los planos van a una carpeta temporal propia con `aplicacion.subidas.guardar_subida` |

### 4.2 Esquemas compartidos

```
Monto            { texto: str, exacto: str }
EstadoFila       { severidad: "CRITICO"|"ERROR"|"ADVERTENCIA"|"INFO"|null, texto: str }
BaseAbierta      { proyecto: str, version: str|null, vigente: str|null, lista: str|null,
                   espacio_de: str|null, solo_lectura: bool, moneda: str }
Resumen          { rev: int, moneda: str, total: Monto, cambios: int, pendientes_catalogo: int,
                   hallazgos: [{severidad, total}], hay_plan: bool,
                   version_mas_nueva: str|null,   # el vigente si es distinto del abierto (concurrencia)
                   guardado_como: str|null }      # se llenó al guardar: el borrador queda cerrado
Cambio           { objeto, clave, campo, antes, despues }    # CambioEditado (H:1395)
```

### 4.3 Rebanada 3b: lectura y navegación

| # | Ruta | Acceso | Pide | Responde |
|---|---|---|---|---|
| R1 | `GET /v1/hoja/versiones?proyecto=` | clave o sesión | `proyecto` (código de `/v1/proyectos` o nombre, `resolver_proyecto`) | `{proyecto, moneda, por_omision: str\|null, versiones: [{codigo, fecha (ISO), motivo, origen, vigente, descartada, cambios: int}]}` (de `historial_de_versiones`, H:2190; `por_omision` = la regla de P:417-421, **calculada en el servidor**) |
| R2 | `POST /v1/hoja/borradores` | solo cuenta | `{proyecto, version: str\|null}` | 201 `{id, base: BaseAbierta, resumen: Resumen, instantanea: {creadas: int, mensaje: str\|null}}`. **Escribe** (instantánea, UC-15e) y crea el borrador vivo; `version: null` = proyecto sin versiones, borrador en blanco; 404 si el proyecto o la versión no existen (texto de H:1572) |
| R3 | `GET /v1/hoja/borradores/{id}` | solo cuenta | — | `{id, base, resumen}` |
| R4 | `DELETE /v1/hoja/borradores/{id}` | solo cuenta | — | 204 (idempotente: un id desconocido también es 204) |
| R5 | `GET /v1/hoja/borradores/{id}/vistas/espacio` | solo cuenta | — | `VistaEspacio` |
| R6 | `…/vistas/presupuesto` | solo cuenta | — | `VistaPresupuesto` |
| R7 | `…/vistas/apu?partida=&buscar=` | solo cuenta | `partida` opcional, `buscar` opcional | `VistaApu` |
| R8 | `…/vistas/plan` | solo cuenta | — | `VistaPlan` |
| R9 | `…/vistas/equilibrio` | solo cuenta | — | `VistaEquilibrio` |
| R10 | `…/vistas/parametros` | solo cuenta | — | `VistaParametros` |
| R11 | `…/vistas/auditoria` | solo cuenta | — | `InformeAuditoriaRespuesta` (reutiliza `api/esquemas_informe.informe_a_respuesta`) |
| R12 | `GET /v1/hoja/precios?proyecto=&version=` | clave o sesión | | `{moneda, fecha_evaluacion, columnas: [{clave, rotulo, numerica}], filas: [Fila de precio]}` (21 campos de H:2266; montos `Monto`; `erosion_*` `null` sin evaluación) |
| R13 | `GET /v1/hoja/precios/atipicos?proyecto=&version=` | clave o sesión | | el `AtipicosRespuesta` de `precios_empresa.py` (se sube a `api/esquemas_hoja.py` para no importar entre rutas): `{disponible, avisos: [{nivel, texto}], variaciones: [...]}`; solo lee |
| R14 | `GET /v1/hoja/trazabilidad?proyecto=&version=` | clave o sesión | | `{versiones: [...], registros: [{objeto, clave, campo, antes, despues, fuente, responsable, fecha_hora}], vacio_mensaje}` |

Las vistas leen del borrador vivo (R5 a R11), no de la base; sin ediciones (3b) coinciden con la versión guardada.

**Esquemas de vistas**

```
VistaEspacio    { ayuda: str,
                  tablas: [{ clave, rotulo,                       # "origenes"…"tramos" (H:148, 180)
                             columnas: [{clave, rotulo, lista: [{valor, rotulo}]|null}],
                             con_estado: bool }],
                  filas: { <tabla>: [ {<columna>: texto} ] },     # filas_desde_espacio (H:377)
                  estado: { "esp_puntos:P1": EstadoFila },        # estado_de_filas (H:1439)
                  derivadas: [{partida, descripcion, unidad, cantidad: Monto, origen}],
                  total: Monto, moneda, pendientes: int,
                  vacio_mensaje: str|null }
VistaPresupuesto{ filas: [{clave, partida, descripcion, unidad,
                           cantidad: str, cantidad_calculada: str, escrita: bool,
                           pu: Monto|null, total: Monto|null, estado: EstadoFila}],
                  total: Monto, moneda, vacio_mensaje: str|null }
VistaApu        { partidas: [{codigo, descripcion}], sin_coincidencias: bool,
                  seleccionada: str|null,
                  detalle: { codigo, descripcion, unidad, rendimiento: str,
                             grupos: [{clave: "materiales"|"equipos"|"mano de obra", rotulo, columnas: [...],
                                       filas: [{descripcion, unidad?, cantidad, precio?, depreciacion?, sueldo?,
                                                modalidad?}], subtotal: Monto}],
                             cierre: [{concepto, monto: Monto, nota}],
                             metricas: {materiales, equipos, mano_obra, precio_unitario: Monto},
                             estados: [str], solo_lectura_insumos: bool } | null,
                  vacio_mensaje: str|null }
VistaPlan       { hay_plan: bool, etiquetas: [str], filas: [{partida, valores: {<etiqueta>: str}}],
                  curva: [{periodo, monto: Monto, acumulado: Monto, porcentaje: Monto}], moneda,
                  mensaje: str|null }
VistaEquilibrio { estado, venta: Monto, costo_variable: Monto, costo_fijo: Monto, utilidad: Monto,
                  punto: Monto|null, porcentaje: Monto|null, periodo: str|null,
                  fraccion_periodo: str|null, mensaje: str }     # texto_equilibrio (H:1221)
VistaParametros { campos: [{clave, rotulo, valor: str}], moneda_proyecto: str|null, total: Monto,
                  puede_convertir: bool }
```

Los textos de ayuda y rótulos (`_AYUDA_ESPACIO` P:144, `_ROTULOS_PARAMETROS` P:2030, `ANCHOS_APU`, títulos de los rubros P:1490)
pasan a `aplicacion/hoja_vista.py` y la página clásica los importa de allí (una sola copia, B2).

### 4.4 Rebanada 3c: edición del borrador (todas solo cuenta, `rev` obligatorio)

Cuerpo común: `{"rev": int, …}`. Respuesta de éxito común: `{rev, resumen}` (200). Error de validación: **422 con el
`detalle` de la clásica y el borrador intacto**. `rev` desactualizado: 409 «El borrador cambió en otra ventana: vuelva a
cargarlo.». Borrador ya guardado: 409 «Este borrador ya se guardó como la versión {c}; abra esa versión para seguir.».
Solo lectura: las ediciones de APU/insumo/espacio se aceptan igual que en la clásica (el candado de H:1842 es solo de
guardar).

| # | Ruta | Cuerpo | Notas |
|---|---|---|---|
| E1 | `PUT /v1/hoja/borradores/{id}/espacio` | `{rev, tablas: {origenes: [Fila], ambientes: [Fila], fuentes: [Fila], puntos: [Fila], tramos: [Fila]}}`, `Fila = {columna: texto}` | `espacio_desde_filas`; completa composiciones de partidas nuevas; una tabla ausente cuenta como vacía (H:609) |
| E2 | `PUT …/cantidades` | `{rev, filas: [{clave, cantidad}]}` solo las **tocadas** | el servidor arma la tabla completa en el orden de `items_sin_escribir` para que `fila {n}` sea la de la clásica; un valor igual al calculado deja de ser «escrito» |
| E3 | `PUT …/parametros` | `{rev, fcas, bono_alimentacion, administracion, utilidad}` textos | `parametros_desde_texto` |
| E4 | `PUT …/plan` | `{rev, etiquetas: [str], filas: [{partida, valores: {<etiqueta>: str}}]}` | `plan_desde_filas` |
| E5 | `POST …/plan/secuencial` | `{rev}` | `con_plan_secuencial`; 409 si ya tiene plan |
| E6 | `PUT …/apu/{partida}` | `{rev, rendimiento, materiales: [str], equipos: [str], mano_obra: [str]}` cantidades por línea, en orden | `composicion_con_cantidades` sobre la copia de la versión (DA-SF-7); el código de partida debe ser de una composición del borrador, si no 404 |
| E7 | `POST …/apu/{partida}/insumo` | `{rev, tipo: "material"\|"equipo"\|"mano_obra", indice: int, insumo: str}` (código del insumo) | requiere versión abierta («Abra una version guardada: los insumos se eligen de su lista de precios.», 409); el insumo debe estar en la lista de precios de la versión (si no, 422); `cambiar_insumo` |
| E8 | `GET /v1/hoja/borradores/{id}/insumos?tipo=&texto=&limite=` | — | `insumos_candidatos` (H:1002), `limite` ≤ 301 (P:1515, 1548); `{insumos: [{codigo, descripcion, unidad, precio: Monto}], hay_mas: bool}` |
| E9 | `GET /v1/hoja/borradores/{id}/cambios` | — | `[Cambio]` (lista de `cambios_entre`) para el modal de guardar |
| E10 | `GET /v1/hoja/borradores` | — | los borradores de **mi** ficha: `[{id, proyecto, version, cambios, tocado}]` (retomar tras F5 o cambio de proyecto) |
| E11 | `POST /v1/hoja/borradores` (R2) con `reemplazar: bool = false` | — | si ya hay un borrador de esa `(proyecto, version)` con cambios y `reemplazar` es falso: 409 `{detalle, borrador_id}`; con `true` se descarta el anterior |

### 4.5 Rebanada 3d: guardado y versiones

| # | Ruta | Cuerpo | Responde / errores |
|---|---|---|---|
| S1 | `POST /v1/hoja/borradores/{id}/guardar` | `{rev, fuente: str, confirmar_version_mas_nueva: bool = false}` | 200 `{codigo, cambios: int, total: Monto, primera: bool, mensaje}`. Con versión abierta: `guardar_version`; sin versión (proyecto nuevo): `crear_primera_version`. 422: sin fuente (H:1797 o H:1935), sin cambios (H:1795), hoja vacía, proyecto con versiones, sin lista vigente, moneda distinta (H:1966-1971). 409: solo lectura (H:1842); hay una versión más nueva sin confirmar (nuevo, abajo); `rev`. Marca el borrador `guardado_como` |
| S2 | `POST /v1/hoja/versiones/restaurar` | `{proyecto, version, fuente}` | 200 `{codigo, mensaje}` (versión nueva = copia, queda vigente); `restaurar` (H:2048). 422 sin fuente |
| S3 | `POST /v1/hoja/versiones/cotizar` | `{proyecto, version, insumo, precio: str, proveedor, numero, fecha: "AAAA-MM-DD", evidencia: str\|null}` | 200 `{codigo, mensaje}`; `cotizar` (H:2074); precio con `decimal_desde_texto` («precio: …») |
| S4 | `POST /v1/hoja/versiones/retirar-cotizacion` | `{proyecto, version, insumo, motivo}` | 200 `{codigo, mensaje}`; `retirar_cotizacion` (H:2104) |
| S5 | `POST /v1/hoja/versiones/convertir` | `{proyecto, version, moneda, lado: "venta"\|"compra", fuente}` | 200 `{codigo, mensaje}`; acceso `CONVERTIR_Y_REAJUSTAR` (solo cuenta); fecha de la tasa = hoy; sin tasa: 422 «No se convirtio nada: …» (H:2161) |
| S6 | `GET /v1/hoja/cadena?proyecto=` | — | `{integra, mensaje, declaracion}` (`estado_de_la_cadena`, `aplicacion/entrega.py:155`); clave o sesión; 404 si no existe |

Para S2 a S5 el **front** impide la acción con cambios sin guardar (como P:1946, 2081, 2201: es una regla de pantalla); el
servidor no conoce los borradores de otra ficha y no la exige. Todas devuelven el código de la versión nueva; el front abre
esa versión con R2.

**Concurrencia entre personas (diferencia declarada, D-5).** La clásica guarda «de la versión abierta» aunque ya exista una más
nueva, y la nueva quedaría vigente sin incluir lo de la otra. `Resumen.version_mas_nueva` avisa en pantalla; `S1` responde 409
«Otra persona guardó la versión {x} después de que usted abrió la {y}. Si guarda, su versión saldrá de la {y} y quedará como
vigente sin lo de la {x}.» salvo `confirmar_version_mas_nueva = true`.

### 4.6 Rebanada 3e: importar plano y exportar Excel

| # | Ruta | Cuerpo | Responde |
|---|---|---|---|
| X1 | `GET /v1/hoja/borradores/{id}/excel` | — | `.xlsx` (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`), `Content-Disposition: attachment; filename="hoja_{código seguro}.xlsx"` (`hoja_borrador.xlsx` sin versión), `no-store`; acceso clave o sesión **del dueño del borrador** (solo cuenta, porque es del borrador); 422 «No se pudo preparar el Excel: …» |
| P1 | `POST /v1/hoja/borradores/{id}/plano` | multipart: `archivo` (`.dxf`/`.ifc`, ≤ 25 MiB SUPUESTO), `rev` | 200 `ImportacionRespuesta`; el archivo se guarda en una carpeta temporal del borrador (se borra al descartar o vencer) |
| P2 | `POST …/plano/unidad` | `{rev, unidades}` (una de `UNIDADES_DE_PLANO`) | `ImportacionRespuesta` (reanuda con la unidad) |
| P3 | `POST …/plano/alturas` | `{rev, alturas: {<id>: texto}}` | `ImportacionRespuesta`; todo o nada: una inválida → 422 «… No se cargó ninguna altura.» |
| P4 | `POST …/plano/circuitos` | `{rev, circuitos: {<id>: [fase, neutro, tierra, puntos]}}` | `ImportacionRespuesta`; todo o nada: 422 «… No se declaró ningún circuito.» |
| P5 | `POST …/plano/fusionar` | `{rev}` | 200 `{rev, resumen, fusion: ResumenDeFusion, informe, mensaje}`; la importación se descarta; el borrador cambia |
| P6 | `DELETE …/plano` | — | 204 |

```
ImportacionRespuesta { estado: "importada"|"detenida"|"rechazada", archivo, mensaje,
                       pide_unidad: bool, unidades: [str],
                       conteos: [{rotulo, cantidad}],                       # resumen_de_importacion
                       informe: [{tipo, referencia, fila, mensaje}],        # filas_del_informe
                       alturas_pendientes: [{id, nombre}],
                       circuitos_supuestos: [{id, fase, neutro, tierra, puntos}],
                       aviso_pendientes: str|null }
```

La carga del plano exige: extensión `.dxf` o `.ifc` **antes** de escribir (H:2603), nombre seguro (`aplicacion/subidas.py`), tope de
tamaño, y mensajes de H:2634-2638 si falta el lector. `adapters/hoja_empresa/guardia.py` es solo para `.xlsx`: no aplica a
DXF/IFC (el tope y la extensión son lo único que se reutiliza de ese enfoque).

### 4.7 Errores de base en la API (diferencia C1 declarada)

| Situación | Clásica | Nueva |
|---|---|---|
| `SQLAlchemyError` al leer/escribir | «No se pudo leer o escribir el caso: {orig}. Revise que el archivo exista y no este abierto en otro programa.» (P:217-221) | 503 «No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.» (sin `orig`) |
| Guardado que falla | «No se guardo nada: {orig o error}» (P:492, 533) | 409 «No se guardó nada: {mensaje de dominio}» si es `ValueError`/`CatalogoIncompleto`; 503 fijo si es de la base. La transacción se deshace (`guardar_version` ya hace `rollback`, H:1873-1875) |
| `CatalogoIncompleto` | `st.error` | 409 con su texto (el manejador global de `api/main.py:131` ya lo hace; las rutas de escritura lo prefijan con «No se guardó nada: ») |
| Dos guardados a la vez (mismo `siguiente_codigo`) | violación de unicidad → «No se guardo nada» | el 503/409 anterior; la transacción de uno gana (SQLite serializa) |

---

## 5. Capa de aplicación y reexportación (RM-1)

### 5.1 Qué se mueve y qué no

| Origen | Destino | Cuándo | Nota |
|---|---|---|---|
| `ui/hoja.py` (todo, 2835 líneas) | `aplicacion/hoja.py` (**traslado puro**, `git mv` + cambiar tres importaciones) | 3b, primer commit | `from ui.composicion import …` → `aplicacion.composicion`; `from ui.estilo import porcentaje` → `aplicacion.estilo`; `from ui.subidas import …` → `aplicacion.subidas` (las tres ya existen en `aplicacion/`). `HojaInvalida` ya viene de `aplicacion/errores.py` (H:85). Cero cambios de lógica |
| — | `ui/hoja.py` | 3b | reexportación **explícita** de cada nombre (`from aplicacion.hoja import nombre as nombre`) y `__all__`; ninguna definición propia (como `ui/composicion.py`, `ui/entrega.py`) |
| P:144, 1490-1494, 2030-2035 (textos de ayuda, rubros, rótulos de parámetros) | `aplicacion/hoja_vista.py` | 3b | la página clásica los importa |
| — | `aplicacion/hoja_vista.py` (**nuevo**) | 3b | `elaborar(borrador)` = `elaborar_borrador(con R17)` (la única vía, P:286-296), armado de las vistas (`VistaEspacio`…), `version_por_omision`, textos |
| — | `aplicacion/hoja_borradores.py` (**nuevo**) | 3b/3c | registro en memoria: `crear`, `obtener`, `reemplazar`, `descartar`, `listar`, `olvidar(huella)`, `heredar(a, b)`, `olvidar_todo()`; reloj inyectado; sin FastAPI ni Streamlit |
| — | `aplicacion/hoja_edicion.py` (**nuevo**) | 3c | aplicar una sección a un `Borrador` (§3.2) y `completar_composiciones` |
| — | `aplicacion/hoja_guardado.py` (**nuevo**) | 3d | `guardar(…)` con sesión envuelta, `version_mas_nueva`, mensajes |
| — | `aplicacion/hoja_planos.py` (**nuevo**) | 3e | estado de la importación por borrador, carpeta temporal, tope |

`aplicacion/hoja.py` queda grande (2835 líneas) a propósito: separar H en varios módulos es una refactorización que **no** hace
falta para migrar y que cambiaría más bytes del archivo congelado; se deja como deuda declarada (no se hace en esta tarea).

### 5.2 Qué **no** se mueve

`asistente/*`, `scripts/*`, `ui/paginas/hoja.py` (solo cambian sus importaciones de constantes de texto), `ui/barra.py`,
`ui/composicion.py` (ya es reexportación). `ui/hoja.py` sigue siendo importado por `asistente/*` (§2.10) tal cual.

### 5.3 Pruebas existentes que el traslado rompe (verificado por búsqueda; se corrigen en 3b)

| Prueba | Por qué se rompe | Corrección |
|---|---|---|
| `tests/unit/test_ui_hoja_conexion.py:185` | lee el **código fuente** de `hoja.__file__` (`ui/hoja.py`) y busca `FunctionDef`s; la reexportación no tiene ninguna, así que `{"elaborar_hoja", "elaborar_borrador", "guardar_version"} <= elaboran` falla | apuntar a `aplicacion/hoja.py` |
| `tests/integration/test_hoja_versiones.py:353`, `tests/integration/test_primera_version.py:335` | `monkeypatch.setattr(hoja, "guardar_espacio", roto)` parchea el atributo de `ui.hoja`; el código real llama a `aplicacion.hoja.guardar_espacio`, así que **el fallo inyectado no ocurre** y la prueba de «todo o nada» deja de probar nada | parchear `aplicacion.hoja` |
| `tests/unit/test_arquitectura.py:646-658` (`test_ui_hoja_depende_de_adapters_espacio…`) | lee los imports de `ui/hoja.py`; tras la reexportación no hay ninguno de `adapters` | leer `aplicacion/hoja.py` |
| `tests/unit/test_ui_barra.py:107-136` | usa `monkeypatch.setattr(ui.hoja, "guardar_version"/"exportar_excel", …)` y `delattr` para simular que faltan | sigue funcionando si ambos nombres están en la reexportación (comprobarlo) |
| `tests/unit/test_experimento_congelado_vigente.py` | ya falla en `275946c` (§1.1) | D-1 |

`tests/unit/test_arquitectura.py` es archivo compartido: el texto exacto del cambio está en §11.

### 5.4 Pruebas nuevas de la capa

`aplicacion/hoja*.py` no importa `streamlit`, `ui`, `api`, `scripts` ni `tests` (lo vigilan `test_arquitectura.py:666-704`, que
recorre todo `aplicacion/`). Una prueba nueva fija que **todo nombre público de `aplicacion.hoja` y todo nombre que cualquier
archivo de `ui/`, `scripts/`, `asistente/` o `tests/` accede como `hoja.<nombre>` o importa de `ui.hoja` está en la
reexportación y es el mismo objeto** (oráculo: un barrido AST del repositorio, independiente de la lista que escribe quien
implementa).

### 5.5 Opciones frente al congelado (D-1)

| Opción | Qué pasa | Riesgo | Reversible |
|---|---|---|---|
| **A (recomendada)** | Traslado puro de H a `aplicacion/hoja.py`; `ui/hoja.py` reexporta; en un commit aparte se **re-congela** (`archivos_del_auditor` pasa a listar `aplicacion/hoja.py` y `aplicacion/composicion.py` en lugar de los dos de `ui/`; `congelar` exige árbol limpio, `congelado.py:68-72`), con una nota en bitácora y un test de equivalencia (los bytes de las funciones movidas coinciden: AST sin cambios salvo las 3 importaciones) | modifica el instrumento declarado por RS-9; mitigación: el movimiento es mecánico, lo demuestra una prueba, y el experimento no se ha corrido en limpio (§1.1) | sí, `git revert` de dos commits |
| B | No tocar `ui/hoja.py`; `aplicacion/hoja*.py` nuevos que **copian** lo que la API necesita | duplica ~1500 líneas: dos verdades (viola B2/NORMAS §2.1) | sí, pero deja deuda grave |
| C | La API importa `ui.hoja` | `PROHIBIDOS_EN_API` y la prueba transitiva de `test_arquitectura.py:460-505` lo impiden; habría que debilitar una guardia del proyecto | no recomendable |
| D | Esperar a que el tutor decida sobre el experimento | bloquea 3b indefinidamente | — |

Mientras D-1 no esté resuelta, **3b no empieza**. El resto del diseño (3c a 3e) depende solo de que exista `aplicacion.hoja`.

---

## 6. División en rebanadas

Cada rebanada es una entrega que pasa su propio ciclo implementador → árbitro y deja la interfaz útil por sí sola. Los tamaños
son **estimaciones mías** (líneas nuevas netas, sin contar el traslado de 3b), no medidas.

### 6.1 Rebanada 3b: traslado RM-1 y lectura/navegación

**Hace:** traslado de H a `aplicacion/hoja.py` (+ reexportación); `aplicacion/hoja_vista.py`, `hoja_borradores.py` (solo
`crear/obtener/descartar/olvidar`); rutas R1 a R14; página `src/paginas/hoja/` de **solo lectura** con las 9 pestañas.
**No hace:** edición, guardado, Excel, planos. **Archivos propios:** `aplicacion/hoja*.py`, `ui/hoja.py` (reexportación),
`api/rutas/hoja.py`, `api/esquemas_hoja.py`, `api/admin_acceso.py` (parámetro `mensaje`), `src/paginas/hoja/**`,
`tests/unit/test_aplicacion_hoja*.py`, `tests/unit/test_api_hoja.py`. **Compartidos (los aplica el orquestador):** §11.
**Tamaño:** backend ~900 líneas + pruebas ~1 100; front ~1 800 + pruebas ~1 000.
**La entrada del menú no se activa todavía** (D-6): sin `cargar` en `rutas.ts` la página no es alcanzable; las pruebas la montan directo.

**Pruebas de backend (rojo visto primero; oráculos a mano o de la fuente, nunca del código bajo prueba):**

| Id | Prueba | Valores y oráculo |
|---|---|---|
| 3b-B1 | `ui/hoja.py` no define nada y reexporta los mismos objetos | AST de `ui/hoja.py` sin `FunctionDef`/`ClassDef`; `ui.hoja.X is aplicacion.hoja.X` para cada nombre de `__all__` |
| 3b-B2 | la reexportación cubre todo lo que el repositorio usa | barrido AST de `ui/`, `scripts/`, `asistente/`, `tests/`: todo `hoja.<n>` e `import … from ui.hoja` está en `__all__` (oráculo: el barrido) |
| 3b-B3 | traslado puro | cada función de `aplicacion/hoja.py` tiene el mismo AST que en `git show 275946c:ui/hoja.py`, salvo las 3 líneas de importación (oráculo: el commit base) |
| 3b-B4 | pruebas retargeteadas (§5.3) | las cuatro pruebas pasan sin cambiar sus expectativas |
| 3b-B5 | R1 sobre OF-001 con 001, 002 (edición), 003 (restauración) | `[(001,"","",False),(002,"edicion","001",False),(003,"restauracion","001",True)]` (literal de `test_aceptacion_sf.py:378-383`); `por_omision == "003"`; con la 003 descartada → `"002"`; con todas descartadas → la última |
| 3b-B6 | R2 sobre OF-001 v001 | `total.exacto` entre 2703,85 y 2703,87 (literal de memoria `of001.md`, `test_aceptacion_sf.py:60`); `moneda == "USD"`; `solo_lectura == False`; `cambios == 0` |
| 3b-B7 | R5 sobre OF-001 | derivadas: AF-LLAVE `cantidad.exacto == "3"`; tubería de drenaje 2" `4.345` y de agua fría 1/2" `8.250` (memoria `of001.md` §2.4 líneas 151-170); 5 tablas con las columnas de `COLUMNAS` en su orden; estado `OK` en filas sin hallazgos |
| 3b-B8 | R9 sobre OF-001 | CV `2137.44`, PE `1530.49` (±0,01), `porcentaje 56.60` (±0,01), `periodo` empieza por «Dia 23» (literales de `test_aceptacion_sf.py:62-65`) |
| 3b-B9 | los cuatro casos límite de PE | V=0 → «El presupuesto no tiene ventas: el punto de equilibrio no aplica.»; m≤0, PE>V y sin curva → su frase (H:1221-1238), construidos con `Presupuesto` a mano |
| 3b-B10 | R2 sobre TI-001 (sin espacio) | tablas del espacio vacías; presupuesto con sus `items_base`; **no** crea versiones ni filas `esp_*` (recuento SQL antes y después) |
| 3b-B11 | R2 crea la instantánea si falta y lo informa | `instantanea.creadas == n` y el texto de P:346-351; segunda apertura `creadas == 0`; el `RegistroCambio` de creación lleva `Nombre <login>` de la sesión (RF-82) |
| 3b-B12 | acceso | sin sesión 401; `rita` (revisa) 403 «Su cuenta no tiene permiso para esta acción.»; `ana` 200; con `X-Silice-Clave`: R1/R12/R13/R14 200, R2/R3/R4/R5–R11 403 («… la clave de API no sirve.»); POST sin CSRF 403; `Origin` ajeno 403; `tomas` (clave temporal) 403 |
| 3b-B13 | `Cache-Control: no-store` y 422 sin eco | en 200, 401, 403, 404 y 422 de cada ruta; cuerpo `{"proyecto": {"x": "VALOR-CENTINELA"}}` → el 422 no contiene `VALOR-CENTINELA`; un 422 de ruta **combina** ambas clases (orden §1.3-7) |
| 3b-B14 | un borrador de otra ficha no existe | `ana` crea; `tomas` pide el mismo id → 404; ningún mensaje confirma el id |
| 3b-B15 | ciclo de vida | reloj inyectado: pasadas 8 h → 404; el 5.º borrador de una ficha descarta el 1.º; `olvidar(huella)` los borra todos; `heredar(a, b)` los pasa |
| 3b-B16 | ningún `float` | el JSON de R2, R5 a R12 recorrido: todo número es `int`; todo monto es `str` |
| 3b-B17 | 404 y mensajes | proyecto inexistente «El proyecto «Z» no existe en este caso.»; versión inexistente: el texto exacto de H:1572 |
| 3b-B18 | R12 sobre OF-001 | 21 columnas en el orden de `COLUMNAS_PRECIOS`; filas ordenadas por código de insumo; `Estado == "OK"` o «Sin referencia ni cotización: el precio no tiene fuente» según el insumo; erosiones `null` sin evaluación y con valores con una fecha fija inyectada (valores de la memoria `s1_conversion.md`, ya usados por `test_ui_hoja_moneda.py::test_precios_muestra_origen_y_erosion`) |
| 3b-B19 | R13 | sin el extra `ml`: `disponible == false` y el aviso `AVISO_SIN_ML`; con una serie sembrada: los `warning` de `atipicos.avisos`; no escribe (recuento de filas) |
| 3b-B20 | R14 sobre la versión 002 | `registros == [("cantidad", clave_AF-LLAVE, "cantidad", "3", "5", FUENTE, RESPONSABLE)]` (literal de `test_aceptacion_sf.py:329-347`); versión sin edición: `vacio_mensaje == "Esta version no nacio de una edicion: no tiene registros de cambio."` |
| 3b-B21 | R11 lleva R17 | un punto de agua sin fuente → hallazgo `R17` ADVERTENCIA nombrando el punto (réplica de `test_ui_hoja_conexion.py`); la lista de funciones que elaboran está clasificada |
| 3b-B22 | rendimiento | `abrir` + las 7 vistas de un proyecto de 500 puntos (`scripts/generar_hoja_prueba.py`): se **registra** la mediana de cinco corridas (umbral de referencia 2 s, RNF-11); no rompe la corrida (como RNF-11) |
| 3b-B23 | tamaño del borrador | `pickle.dumps(borrador)` de ese proyecto: se registra el tamaño (insumo para D-9) |
| 3b-B24 | `docs/api.json` regenerado | `scripts/exportar_openapi.py` sin diferencias pendientes |
| 3b-B25 | arquitectura | `aplicacion/hoja*.py` sin `streamlit/ui/api/scripts/tests`; `api/rutas/hoja.py` sin `ui` (guardas existentes) |

**Pruebas de front (Vitest + Testing Library, `fetch` simulado):**

| Id | Prueba |
|---|---|
| 3b-F1 | un solo `h1` «Hoja del proyecto» (`cds--type-heading-04`); los `h2` de sección con `heading-compact-02` |
| 3b-F2 | sin proyecto en la cabecera: `EstadoVacio` «Elija un proyecto»; proyecto sin versiones: «Este proyecto aún no tiene versiones» (P:140) |
| 3b-F3 | las 9 pestañas, en el orden de P:83-93, con `role="tablist"`/`tab`/`tabpanel`; flechas izquierda/derecha cambian de pestaña; solo se piden las vistas de la pestaña activa (el `fetch` simulado registra las rutas) |
| 3b-F4 | el selector de versión ofrece las no descartadas y marca « (vigente)»; la preseleccionada es `por_omision` del servidor |
| 3b-F5 | montos: `formatoEsVe("2703.86")` se ve «2.703,86»; el `title` y el texto accesible llevan `exacto`; un total de 30 cifras no pierde ninguna; no se llama a `Number`/`parseFloat` (prueba estática sobre `src/paginas/hoja/`) |
| 3b-F6 | Estado por fila: ícono + texto de severidad (el color nunca va solo); «Ver en Auditoría» lleva a la pestaña y filtra por `origen` |
| 3b-F7 | APU: lista con búsqueda (el servidor filtra; «Ninguna partida coincide; se muestran todas.»), selección, tres rubros, cierre en el orden de `filas_de_cierre` |
| 3b-F8 | Plan y curva: sin plan, el mensaje de P:1804; con plan, matriz y curva (`CurvaPlanAvance` con tabla equivalente) |
| 3b-F9 | Punto de equilibrio: las cuatro métricas y la frase del caso; el caso «no aplica» no muestra «Punto de equilibrio» |
| 3b-F10 | Precios: columnas principales visibles y el resto en el detalle del insumo; la columna «Erosión por índice» solo si algún valor viene; «Buscar variaciones atípicas de precio» muestra los avisos (atípico en morado, DESIGN) |
| 3b-F11 | Trazabilidad: dos tablas y el mensaje de versión sin registros |
| 3b-F12 | Auditoría usa `InformeAuditoria` (texto plano, sin Markdown: un descripción con `![x](http://…)` no crea imagen) |
| 3b-F13 | un 401 llama a `alExpirar`; un 404 de borrador (reinicio) muestra el aviso del §3.1 y ofrece reabrir; errores con `AvisoError` mostrando el `detalle` tal cual |
| 3b-F14 | ninguna contraseña ni secreto en pantalla ni en `localStorage`/`sessionStorage` (no se escribe nada) |
| 3b-F15 | al desmontar la página se hace `DELETE` del borrador (con `keepalive`) |

**Criterio de «hecho» de 3b:** la página abre cualquier versión del caso ficticio OF-001 y de TI-001 y muestra, pestaña por
pestaña, las mismas cifras y mensajes que la clásica (comparación de §9, filas P1 a P12); las 4 pruebas retargeteadas pasan;
D-1 resuelta y registrada; `npx vitest run src/paginas/hoja`, `npm run lint`, `npm run build` y las pruebas de backend con
`-W error` en verde; el árbitro aprueba.

### 6.2 Rebanada 3c: edición y borrador

**Hace:** `aplicacion/hoja_edicion.py`; rutas E1 a E11; tablas editables (5 del espacio, cantidades, parámetros, plan, APU y
cambio de insumo); aviso de cambios sin guardar; cambio de versión con confirmación; retomar borradores; recálculo y
validación con los mensajes de la clásica. **No hace:** guardar, restaurar, Excel, planos.
**Tamaño:** backend ~600 + pruebas ~1 300; front ~2 200 + pruebas ~1 400.

**Pruebas de backend:**

| Id | Prueba | Valores y oráculo |
|---|---|---|
| 3c-B1 | parámetro válido recalcula | OF-001: `administracion = "0.20"`, utilidad 0,10: total ≈ **2821.42** (= CV 2137,44 × 1,20 × 1,10 = 2821,4208, cuenta a mano de este diseño a partir de la memoria, a confirmar contra `of001.md` antes de fijarla), PE ≈ **1763.39** (= 0,825 × CV), PE % = **62.50**, `cambios == 1`, cambio `("parametro","administracion","valor","0.15","0.20")` |
| 3c-B2 | parámetro inválido | `utilidad = "mucho"` → 422 con `detalle == "parametros: utilidad: 'mucho' no es un numero decimal valido"`; el borrador queda como antes (`rev` no sube; `fcas` previo conservado, réplica de `test_ui_hoja.py:320-339`) |
| 3c-B3 | cantidad escrita a mano | AF-LLAVE de 3 a 5: `Δtotal == 2 × CD(AF-LLAVE) × 1,15 × 1,10` con el CD tomado de la vista APU (aritmética de dos llaves, `test_aceptacion_sf.py:350-360`); R8 ADVERTENCIA en esa fila; cambio `("cantidad", "AF-LLAVE|<origen>", "cantidad", "3", "5")` |
| 3c-B4 | cantidad igual a la calculada deja de ser «escrita» | enviar `"3"` para AF-LLAVE → `cambios == 0` |
| 3c-B5 | errores de cantidad | `"-1"` → «presupuesto, fila {n} (AF-LLAVE): la cantidad no puede ser negativa; escriba cero o una cantidad positiva» con `n` = posición de la fila en la tabla completa, aunque el cliente mande solo esa fila |
| 3c-B6 | espacio | cambiar el alto de un ambiente (2,500 → 3,000) cambia las cantidades derivadas según la memoria; texto `"2,5"` → 422 «ambientes, fila {n}: alto: '2,5' no es un numero decimal valido» (con el rótulo exacto de H:180-186) |
| 3c-B7 | fila en blanco no es error; id duplicado y referencia rota dan el mensaje de `Espacio` envuelto en `HojaInvalida` | casos a mano |
| 3c-B8 | lo que el editor no muestra se conserva | un espacio con circuitos: tras `PUT espacio` los circuitos siguen (`borrador.espacio.circuitos` igual) y los recorridos propuestos de puntos quitados se van (H:617-623) |
| 3c-B9 | partida nueva toma su APU del catálogo | agregar un punto de un tipo que deriva una partida nueva: `composiciones` la incluye y el total sube; una partida sin APU queda pendiente y `pendientes_catalogo` la cuenta |
| 3c-B10 | APU | `rendimiento` y cantidades por línea; tabla con distinto número de líneas imposible por contrato (el servidor arma las filas); `"-1"` → «materiales, fila 2: la cantidad no puede ser negativa» |
| 3c-B11 | cambiar insumo | un insumo de la lista cambia descripción/unidad/precio y conserva la cantidad; fuera de la lista → 422; sin versión abierta → 409 con el texto de P:1522 |
| 3c-B12 | plan | suma ≠ 1 → «plan, partida {c}: las fracciones suman {x} y deben sumar exactamente 1; repartala entre los periodos hasta completar 1»; fracción negativa; celda vacía = 0; plan secuencial sobre una versión sin plan crea la curva; sobre una con plan → 409 |
| 3c-B13 | `rev` | petición con `rev` viejo → 409 y nada cambia; dos peticiones concurrentes (hilos) no pierden una edición |
| 3c-B14 | retomar | tras 2 ediciones, `GET /borradores` lista `{cambios: 2}`; `POST /borradores` de la misma versión → 409 con `borrador_id`; con `reemplazar` se descarta el anterior |
| 3c-B15 | R17 en cada elaboración | un punto agua fría sin fuente → R17 en la vista de auditoría y en `resumen.hallazgos`; al corregir la fuente, desaparece (no queda ligada al espacio viejo) |
| 3c-B16 | `cambios_entre` no cuenta reglas extra | abrir una versión con R11/R12 a una fecha: `cambios == 0` |
| 3c-B17 | tamaño y topes | 5 001 filas de `origenes` → 422 con mensaje fijo sin eco; celda de 501 caracteres → 422; cuerpo > 8 MiB → 413/422 sin eco |
| 3c-B18 | rendimiento | `PUT espacio` + vista de resumen con 500 puntos: mediana de cinco corridas **registrada** (umbral RNF-11 2 s) |
| 3c-B19 | acceso | todas las rutas: 401/403 como 3b-B12; CSRF y `Origin` en PUT/POST/DELETE |

**Pruebas de front:**

| Id | Prueba |
|---|---|
| 3c-F1 | cada celda es un `input` con nombre accesible «{columna}, {tabla} fila {n}»; las listas cerradas son `select` con rótulo claro y valor interno |
| 3c-F2 | edición válida: tras la pausa (400 ms, temporizadores falsos de Vitest) se manda una sola petición con la tabla completa y se actualizan total, estado y derivadas; el total anunciado va en una región `aria-live="polite"` |
| 3c-F3 | edición inválida: aparece el `detalle` del servidor + «La hoja sigue con el último borrador válido.» en `role="alert"`; la celda queda con `aria-invalid="true"`; el total mostrado es el anterior |
| 3c-F4 | si el mensaje empieza por «{tabla}, fila {n}: » el foco puede ir a esa fila (mejora; si no coincide solo se muestra el mensaje) |
| 3c-F5 | una sola petición en vuelo por borrador; dos ediciones seguidas coalescen en la última; un 409 de `rev` recarga las semillas y avisa |
| 3c-F6 | teclado: Tab/Mayús+Tab; ↑/↓ mueven entre filas en la misma columna (en `input` de texto; en `select` no se intercepta); Enter baja; Esc devuelve la celda a lo último aceptado |
| 3c-F7 | «Agregar fila» pone el foco en su primera celda; «Quitar fila» deja el foco en la vecina o en «Agregar fila» (patrón de `PlanDeTrabajo.tsx`) |
| 3c-F8 | cantidades: solo la columna `cantidad` es editable; una fila escrita muestra «(calculada: 3)» y un botón «Volver a la calculada» |
| 3c-F9 | cambiar de versión con cambios: modal «Tiene {n} cambios sin guardar…» con «Descartar y abrir» y «Seguir editando»; el cambio de proyecto en la cabecera no pierde el borrador: se ofrece «Retomar borrador de {proyecto} ({n} cambios)» |
| 3c-F10 | `beforeunload` solo mientras hay cambios |
| 3c-F11 | APU: búsqueda, edición de cantidades y rendimiento, los subtotales y el cierre cambian con los factores; el selector de insumo ofrece candidatos con búsqueda y «Usar este insumo» empieza deshabilitado; con `hay_mas` pide acotar |
| 3c-F12 | plan: «Crear plan secuencial» solo sin plan; la matriz muestra el error por fila |
| 3c-F13 | los textos escritos nunca se interpretan como números en el navegador (prueba estática) |

**Criterio de «hecho» de 3c:** con el caso ficticio OF-001 la secuencia de la prueba de aceptación SF (cambiar parámetro, escribir
una cantidad, editar el espacio) da en la nueva las mismas cifras y los mismos mensajes que en la clásica (§9, P13 a P24); un
dato inválido nunca cambia el borrador; la medición de rendimiento está registrada; D-2 y D-9 resueltas; el árbitro aprueba.

### 6.3 Rebanada 3d: guardado y versiones

**Hace:** `aplicacion/hoja_guardado.py`; S1 a S6; modal «Guardar versión» (fuente obligatoria, responsable = la persona de la
sesión en solo lectura, lista de cambios, aviso de versión más nueva); primera versión; restaurar; cotizar; retirar;
convertir moneda; cadena en Trazabilidad; **activación del menú** si D-6 lo permite.
**Tamaño:** backend ~500 + pruebas ~1 200; front ~1 300 + pruebas ~1 000.

**Pruebas de backend:**

| Id | Prueba | Valores y oráculo |
|---|---|---|
| 3d-B1 | guardar sin fuente | 422 «Escriba la fuente del cambio: por que se cambia y con que respaldo.»; no hay versión nueva (códigos antes y después iguales: `["001","002","003"]`, réplica de `test_aceptacion_sf.py:315-326`) |
| 3d-B2 | guardar con fuente | versión nueva; `RegistroCambio` exacto (objeto, clave, campo, antes, después, fuente, responsable = `Nombre <login>`, fecha) y `cambios == 1` |
| 3d-B3 | la cadena queda íntegra | tras guardar por la API, `estado_de_la_cadena(...)` → `integra True`; **falla** si se usa la sesión sin `con_anexos_de_cadena` (rojo visto del §1.2) |
| 3d-B4 | todo o nada | con `guardar_espacio` forzado a fallar (parcheando `aplicacion.hoja`): 409/503, ninguna versión nueva, ninguna fila `esp_*` ni `RegistroCambio` nuevos (recuento SQL), la cadena sigue íntegra |
| 3d-B5 | solo lectura | partida sin composición vigente: 409 con el texto de H:1842-1846 |
| 3d-B6 | sin cambios | 422 «No hay cambios para guardar: edite alguna celda primero.» |
| 3d-B7 | versión más nueva | otra sesión guarda la 004 después de abrir la 003: S1 → 409 con el texto de §4.5; con `confirmar_version_mas_nueva=true` guarda y queda vigente |
| 3d-B8 | doble guardado | un segundo `guardar` del mismo borrador → 409 «Este borrador ya se guardó como la versión {c}…»; no se crea otra versión |
| 3d-B9 | primera versión | proyecto sin versiones: crea `001`, un solo `RegistroCambio` `("version","001","creacion","","001")` con fuente y responsable, plan secuencial si no hay, total = memoria 2703,86 ±0,01 al importar el espacio de OF-001; lista vigente de la **moneda del proyecto**: otra moneda → 422 con el texto de H:1966-1971; sin lista vigente → texto de H:1961-1964; segundo intento → 422 «ya tiene versiones» |
| 3d-B10 | R17 en el guardado | la versión guardada con un punto sin fuente conserva el hallazgo R17 (como `test_ui_hoja_conexion.py`) |
| 3d-B11 | restaurar | `001` → `003` igual a la `001` (mismo total; `cantidades` vacías), la `001` y la `002` siguen; `por_omision` pasa a `003`; sin fuente → 422 |
| 3d-B12 | cotizar y retirar | cotizar crea versión nueva que conserva plan y curva, solo cambia ese insumo en ese proyecto; precio inválido → 422 «precio: 'x' no es un numero decimal valido»; retirar vuelve al precio de la lista base |
| 3d-B13 | convertir | sin tasa en 7 días → 422 «No se convirtio nada: …» y nada escrito; con tasa de hoy: versión nueva en la otra moneda; total = total ÷ tasa (o × tasa) ±0,01 (oráculo `s1_conversion.md`) |
| 3d-B14 | permisos | guardar/restaurar/cotizar/retirar/convertir: 401, 403 `rita`, 403 clave de API, 403 sin CSRF; convertir exige `convertir_y_reajustar` |
| 3d-B15 | S6 | `integra True` en una base sana; tras alterar a mano una celda de la base, `integra False` con el mensaje de `mensaje_de_cadena` |
| 3d-B16 | errores de base | un `OperationalError` simulado → 503 con el mensaje fijo; el cuerpo no contiene «sqlite», «SELECT» ni una ruta |
| 3d-B17 | `total` guardado | el `total` de S1 es el de la vista de resumen justo antes de guardar |

**Pruebas de front:**

| Id | Prueba |
|---|---|
| 3d-F1 | modal «Guardar versión»: `Modal` con foco atrapado, devuelve el foco al botón; «Fuente» obligatoria (el botón «Guardar» queda deshabilitado y dice por qué); «Responsable: {Nombre <login>}» de solo lectura; lista de cambios (objeto, clave, campo, antes, después) |
| 3d-F2 | éxito: notificación «Se guardó la versión {c} con {n} cambios registrados.» y la página abre la nueva versión |
| 3d-F3 | proyecto sin versiones: «Guardar primera versión» con fuente de la medida |
| 3d-F4 | 409 por versión más nueva: confirmación «Guardar de todos modos» |
| 3d-F5 | con cambios sin guardar no se ofrecen Cotizar, Convertir ni Restaurar (los textos de P:1946, 2081, 2201) |
| 3d-F6 | formularios de cotización, retiro, conversión y restauración con sus textos y errores; el precio se manda como texto |
| 3d-F7 | Trazabilidad muestra el estado de la cadena («Cadena íntegra: N versiones» o el mensaje de cadena rota) con ícono y texto |
| 3d-F8 | tras un 404 de borrador al guardar: mensaje del §3.1 y no se pierde el formulario |

**Criterio de «hecho» de 3d:** la nueva hace todo lo que hace la clásica salvo planos y Excel, con el mismo caso ficticio y las
mismas cifras (§9, P25 a P38); la cadena queda íntegra; el árbitro aprueba; si D-6 lo autoriza, el menú abre la página nueva.

### 6.4 Rebanada 3e: importar plano, exportar Excel y cierre de paridad

**Hace:** `aplicacion/hoja_planos.py`; X1 y P1 a P6; flujo de importación; botón «Descargar Excel»; registro de paridad.
**Tamaño:** backend ~500 + pruebas ~900; front ~1 100 + pruebas ~800.

**Pruebas de backend:**

| Id | Prueba | Valores y oráculo |
|---|---|---|
| 3e-B1 | Excel | el libro de OF-001 tiene las 9 hojas de pestañas en su orden (`test_aceptacion_sf.py:419-429`) y el total evaluado de la hoja Presupuesto coincide con el del sistema a ±0,005 (oráculo: `tests/fixtures/evaluador_excel.py`, el mismo del aceptación SF) |
| 3e-B2 | Excel del borrador sin versión | `hoja_borrador.xlsx` |
| 3e-B3 | Excel lleva espacio, precios, trazabilidad y control | las hojas «Esp origenes» … «Esp vertices», «Precios» y las de control existen y el Estado de las filas coincide con la vista |
| 3e-B4 | nombre seguro | un código de versión con `"` o saltos de línea no rompe `Content-Disposition` |
| 3e-B5 | plano DXF de OF-001 | `tests/fixtures/planos/of001.dxf`: informe con los conteos de `test_planos_dxf_of001.py`; 6 alturas pendientes y 2 circuitos por declarar (`test_aceptacion_sf.py:251`) |
| 3e-B6 | alturas | las seis alturas «2,500» (leída de la memoria, como `_altura_de_la_memoria`) se cargan; una inválida («250,5», «0», «abc») → 422 con el texto de H:2757-2760 y **ninguna** se carga |
| 3e-B7 | circuitos | declarar los dos; un entero inválido → texto de H:2796-2799 y ninguno declarado |
| 3e-B8 | fusionar y total | tras fusionar sobre un borrador en blanco con los parámetros de TI-001, el total es el de la memoria 2703,86 ±0,01 y las cantidades coinciden a una milésima (`test_aceptacion_sf.py:261-273`) |
| 3e-B9 | detenida pide unidad | DXF sin unidad → `detenida`, `pide_unidad`; P2 con `m` reanuda |
| 3e-B10 | rechazada | archivo corrupto → `rechazada` con el mensaje; no se puede fusionar (409 con el texto de H:2833) |
| 3e-B11 | seguridad de la subida | extensión `.exe` → 422 **antes** de escribir (la carpeta temporal queda vacía); nombre `..\..\x.dxf` se guarda como `x.dxf`; archivo > 25 MiB → 413/422; `CON.dxf` → `_CON.dxf` |
| 3e-B12 | limpieza | descartar o vencer el borrador borra su carpeta temporal |
| 3e-B13 | falta el lector | sin `ezdxf`/`ifcopenshell`: 422 con el texto de H:2634-2638 |
| 3e-B14 | `ResumenDeFusion` cuenta una vez | el conteo no se duplica (réplica de `test_ui_hoja_planos.py:265`) |

**Pruebas de front:**

| Id | Prueba |
|---|---|
| 3e-F1 | `SubidaArchivo` con `.dxf`/`.ifc` y «Leer plano»; otra extensión: «Solo se aceptan archivos .dxf o .ifc.» |
| 3e-F2 | estados `rechazada`, `detenida` (selector de unidad) e `importada` (cuatro conteos, tabla del informe, alturas, circuitos, aviso) con los textos de P:1238-1259 |
| 3e-F3 | «Fusionar con el espacio del borrador» deja el informe de la fusión y el mensaje de P:1367-1373 |
| 3e-F4 | «Descargar Excel» usa `DescargaArchivo` (GET), muestra el error «No se pudo preparar el Excel: …» |
| 3e-F5 | toda la pestaña Espacio sigue cabiendo a 1366×768 sin desplazamiento horizontal de la página |

**Criterio de «hecho» de 3e (y de T10):** todas las filas de §9 en verde; auditoría visual a 1366×768 y 1056 px con datos
ficticios (teclado incluido) registrada en bitácora; árbitro aprueba; CHANGELOG, `api.json`, ERS y registro de ciclos al día
(los aplica el orquestador).

---

## 7. Diseño de la interfaz (DESIGN.md, PRODUCT.md)

### 7.1 Reglas que se cumplen

Carbon g10 oficial (`@carbon/react`), esquinas rectas, densidad `sm` (32 px), IBM Plex, cifras tabulares a la derecha; **un solo
`h1`** (`cds--type-heading-04`) «Hoja del proyecto»; secciones con `h2` (`heading-compact-02`); montos con `formatoEsVe` y el
exacto accesible; sin animación decorativa (solo las transiciones de componentes Carbon); morado solo para atípicos; verde/rojo
IBCS solo en variaciones (la hoja no tiene variaciones: nada verde/rojo); severidad con ícono y texto; español con tildes y
sin jerga interna (nada de UC-xx, RF-xx, `esp_puntos:P1` crudo: la clave de fila se muestra como «Punto P1»); 1366×768 sin
desplazamiento horizontal de la **página**.

### 7.2 Estructura de la página

```
┌ Cabecera del marco (48 px): persona · caso · proyecto (único selector de proyecto) · Salir ┐
│ Menú lateral (16 rem, fijo ≥ 1056 px)  │  Contenido (≈ 1078 px a 1366 px de ancho)         │
│                                         │  h1 Hoja del proyecto                              │
│                                         │  Versión [003 (vigente) ▾]  [Abrir]               │
│                                         │  3 cambios sin guardar · Total 2.703,86 USD        │
│                                         │  [Guardar versión…] [Descargar Excel] [Descartar] │
│                                         │  ─ Espacio y metrajes │ APU │ Presupuesto │ Plan y │
│                                         │    curva │ Punto de equilibrio │ Precios │ Paráme- │
│                                         │    tros │ Auditoría │ Trazabilidad ─              │
│                                         │  (panel de la pestaña)                             │
│                                         │  aside "Asistente de IA" (hidden, vacío)           │
└─────────────────────────────────────────┴───────────────────────────────────────────────────┘
```

- La **barra de estado del borrador** (versión, cambios, total, acciones) es una región con `role="region"
  aria-label="Estado del borrador"`; el total se anuncia en `aria-live="polite"` (un mensaje por recálculo, sin repetir lo
  igual). El total sale de `Resumen.total.texto` (formateado) con el exacto en `title`.
- Las 9 pestañas son Carbon `Tabs` (`size="md"`); si el ancho no alcanza (se medirá a 1366 px en la auditoría visual de T11),
  Carbon ofrece sus botones de desplazamiento de pestañas; no hay segundo nivel de pestañas.
- El cambio de pestaña desmonta la anterior; la nueva pide su vista al servidor (equivale al `_resembrar` de P:2280-2281).

### 7.3 Tablas editables accesibles

- Base: Carbon `Table size="sm"` con `TextInput size="sm"`/`Select size="sm"` por celda, como `TablaInsumos.tsx` y
  `FilasEditables.tsx` (no se reutiliza `DataTable` de `TablaDensa`, que es de solo lectura).
- Cada celda: `labelText="{Columna}, {tabla} fila {n}"` (oculto con `hideLabel`); `aria-invalid` y `aria-describedby` hacia el
  mensaje de error; `inputMode="decimal"` en las numéricas; la celda de número va a la derecha.
- Cada tabla es un `section` con `h3` (`heading-compact-01`), `<table aria-label>` y un contador de filas; encabezados `th
  scope="col"`.
- **Tablas anchas** (puntos: 13 columnas + Estado, ≈ 1 400 px): la tabla va dentro de un contenedor `role="region"`
  `aria-label="{tabla}: desplazar horizontalmente"` con `tabindex="0"` y desplazamiento propio; la primera columna (Código) queda
  fija (`position: sticky`); la página no se desplaza horizontalmente. Alternativa si la auditoría visual de T11 la rechaza:
  mostrar solo las columnas básicas y abrir el resto en un panel de la fila.
- **Filas largas**: paginación Carbon de 50 filas por página cuando una tabla pasa de 100 filas (RNF-11 mide 500 puntos); el
  buscador por código filtra en el cliente **sin calcular** (comparación de texto).
- **Estado de fila**: columna de solo lectura al final con `Severidad` (ícono + nombre) y el texto del estado recortado con
  puntos suspensivos y completo en `title` y en el panel «Ver en Auditoría» (RF-55 «enlaza a su detalle»).
- **Teclado:** Tab/Mayús+Tab recorren las celdas; ↑/↓ cambian de fila en la misma columna solo en campos de texto; Enter baja;
  Esc devuelve la celda a lo último aceptado por el servidor; «Agregar fila» y «Quitar fila» como en `PlanDeTrabajo.tsx` (foco
  determinista).
- **Decimales:** la ayuda de cada tabla numérica dice «Decimales con punto, por ejemplo 2.5» (la clásica rechaza `2,5`:
  «`'2,5' no es un numero decimal valido`»); aceptar coma es la decisión D-8.

### 7.4 Bocetos

**Espacio y metrajes**

```
Importar plano (DXF o IFC)  ▸                                   [acordeón, cerrado]
Describa el espacio en metros (eje z hacia arriba desde el piso terminado)…   [ayuda]
Ambientes                                                                      (6 filas)
┌────────┬───────────┬─────────┬─────────┬────────┬───────┬──────┬─────────────────┬──────────────┐
│ Código │ Nombre    │ Esq. X  │ Esq. Y  │ Largo  │ Ancho │ Alto │ Origen medida   │ Estado       │
├────────┼───────────┼─────────┼─────────┼────────┼───────┼──────┼─────────────────┼──────────────┤
│ [A1  ] │ [Baño   ] │ [0    ] │ [0    ] │ [3   ] │ [2  ] │[2.5 ]│ [Plano ▾]       │ ✔ OK         │
└────────┴───────────┴─────────┴─────────┴────────┴───────┴──────┴─────────────────┴──────────────┘
[Agregar fila a ambientes]
… Orígenes de medida · Fuentes · Puntos · Vértices de recorridos …
Cantidades derivadas (tabla de solo lectura) · Total del presupuesto 2.703,86 USD · 0 partidas pendientes
```

**APU (tres paneles a 1366 px)**

```
┌ Partidas (220) ─────┐ ┌ AF-TUB12 · Tubería agua fría ½″ · m (546) ───┐ ┌ Factores y cierre (280) ─┐
│ [Buscar partida   ] │ │ Materiales · 2 líneas            Subtotal 12,40│ │ FCAS [6.00      ]        │
│ (•) AF-TUB12 …      │ │ Descripción │Unid│Cantidad│Precio              │ │ Bono [..] Admin [..]     │
│ ( ) AF-CODO12 …     │ │ …           │ m  │[1.05 ] │ 3,10               │ │ Utilidad [..]            │
│                     │ │ Equipos … · Mano de obra …                      │ │ Cierre de partida        │
│                     │ │ Rendimiento (unid./día) [ 25 ]                  │ │ Materiales 12,40 …       │
│                     │ │ ▸ Cambiar el insumo de una línea                │ │ = Precio unitario 21,07  │
└─────────────────────┘ └──────────────────────────────────────────────────┘ └──────────────────────────┘
```

**Modal «Guardar versión»**

```
Guardar versión 004                                           [×]
Se registrarán 3 cambios en la versión 004 (sale de la 003).
Fuente del cambio (por qué y con qué respaldo)  [__________________]  (obligatoria)
Responsable: Ana Pérez <ana>
Cambios:  Objeto │ Clave │ Campo │ Antes │ Después
          cantidad │ AF-LLAVE|… │ cantidad │ 3 │ 5
                                      [Cancelar]  [Guardar versión]
```

**Precios (resumen + detalle)**

```
Insumo │ Código │ Precio │ Moneda │ Lista │ Fecha del precio │ Referencia │ Cotización │ Estado │ [Detalle]
Detalle de MAT-001: tasa 633,3644 (01/07/2026), moneda original Bs, precio original …, erosión USD …, propio/heredado …
[Buscar variaciones atípicas de precio]   (avisos con ícono; atípico en morado)
Registrar una cotización  ·  Retirar una cotización
```

### 7.5 Textos nuevos (todos con tildes)

Títulos: «Hoja del proyecto», «Guardar versión», «Descartar los cambios», «Retomar borrador»; vacíos: «Elija un proyecto», «Este proyecto
aún no tiene versiones», «El borrador todavía no deriva cantidades: agregue un ambiente, una fuente y los puntos de agua, de datos
o de electricidad.» (misma frase de P:1170-1173 con tildes). Los mensajes que vienen de `aplicacion/hoja.py` se muestran tal
cual (diferencia D-3).

---

## 8. Riesgos

| # | Riesgo | Efecto | Mitigación | Estado |
|---|---|---|---|---|
| R-1 | **Congelado del experimento** (§1.1) | traslado RM-1 contradice RS-9; la prueba de guardia ya falla | D-1; traslado byte a byte + prueba de equivalencia + re-congelar aparte | abierto, bloquea 3b |
| R-2 | **Pérdida de borrador** | reinicio de la API, vencimiento de 8 h, expulsión por tope, cierre de pestaña | el borrador sobrevive a F5 y a cambiar de proyecto (retomar); aviso de cambios sin guardar y `beforeunload`; mensaje claro cuando falta (§3.1); TTL y tope se ratifican (D-9) | mitigado, riesgo residual declarado |
| R-3 | **Concurrencia de edición** entre dos personas | una versión nueva sale de una base ya superada | `version_mas_nueva` + 409 con confirmación (D-5); `rev` dentro de un borrador; SQLite serializa escrituras | mitigado |
| R-4 | **Concurrencia dentro de un borrador** (dos ventanas con el mismo id, ediciones fuera de orden) | edición perdida | `rev` obligatorio, una petición a la vez, 409 y recarga | mitigado |
| R-5 | **Cadena de sellos** rota por una sesión sin envoltorio | «Cadena rota» bloquea entregar el paquete | sesión envuelta en todas las escrituras; prueba 3d-B3 con rojo visto | mitigado |
| R-6 | **Permisos**: la clave de API escribiendo o leyendo borradores | una integración edita sin responsable | borradores y escrituras solo cuenta (403 con clave); lecturas de versiones guardadas con clave | mitigado |
| R-7 | **Datos de la empresa en memoria del servidor** | un borrador ajeno visible | ligado a la huella de la ficha; id impredecible; 404 para ajenos; se olvidan al cerrar sesión | mitigado |
| R-8 | **Tamaño de hojas** (cientos de puntos y de partidas): cuerpo y respuesta grandes, tabla lenta | pantalla pesada, 2 s superados | topes de §4.1 (supuestos); paginación de 50 filas; vistas bajo demanda (solo la pestaña activa); cálculo en caché por `rev`; se **mide** en 3b y 3c con `scripts/generar_hoja_prueba.py` (500 puntos) | abierto: sin medición propia todavía |
| R-9 | **Rendimiento del recálculo** (R17 + `cambios_entre` + `elaborar`) por cada edición | latencia por tecla | pausa de 400 ms, una petición a la vez, caché por `rev`; RNF-11 mide 0,125 s con 500 puntos sin R17 (`docs/bitacora/2026-10-sf.md:708`): se mide de nuevo con R17 | abierto |
| R-10 | **Informe de auditoría enorme** (los hallazgos guardados se acotan a 500, RF-143; el vivo no) | tabla de miles de filas | `TablaDensa` ya ordena y pinta; si 3b mide >1 000 hallazgos se pagina; no se recorta sin declararlo | abierto |
| R-11 | **Subida de planos** (DXF/IFC no confiables, `ezdxf`/`ifcopenshell`) | CPU, memoria o disco | extensión antes de escribir, nombre seguro, tope de 25 MiB (supuesto), carpeta temporal por borrador con limpieza, ruta síncrona en hilo de servidor | abierto: el tope no está medido con planos reales (no disponibles en el repo) |
| R-12 | **Mensajes sin tildes heredados** (D1) | texto del servidor se ve sin tildes | D-3; se corrige en una pasada posterior que también re-congele, no ahora | declarado |
| R-13 | **Tablas anchas** a 1366×768 | desplazamiento interno, columnas ocultas | región con foco y columna fija; alternativa de panel de fila | por verificar en T11 |
| R-14 | **`useBlocker` no disponible** (`HashRouter`) | navegar fuera sin aviso | el borrador persiste en el servidor; no hace falta vetar | mitigado |
| R-15 | **Estado en memoria se duplica en pruebas** | pruebas que se contaminan | `olvidar_todo()` en las fixtures (como `caso_web.olvidar_todo`) | mitigado |
| R-16 | **Catálogo cambia mientras se edita** | una partida nueva toma su APU de un catálogo distinto al visto | el APU entra a la copia de la versión **al aceptar** la edición (como P:268), no al guardar; lo que se guarda es lo que el borrador ya tiene (H:1849 solo completa lo que falta) | igual que la clásica |
| R-17 | **API reiniciada con borradores** | mensaje de 404 | §3.1 | declarado |

---

## 9. Paridad: «la nueva hace lo mismo que la clásica»

### 9.1 Cómo se compara

- **Mismo caso ficticio**, sembrado por los mismos fixtures: OF-001 (`tests/fixtures/caso_of001.py`, `espacio_of001.py`,
  `hoja_en_base.plantilla_of001`), TI-001 (`caso_ti001.py`) y un proyecto nuevo sin versiones. Nunca libros ni nombres reales.
- **Dos lados, un oráculo.** Cada fila de la tabla se prueba (a) en la clásica con `streamlit.testing.AppTest` o llamando a la
  lógica de `aplicacion/hoja.py` y (b) en la nueva por la API/Vitest; **el valor esperado es el literal** de la memoria o de la
  prueba de aceptación SF, no una lectura de ninguno de los dos lados. Las cifras se comparan **exactas** (`exacto`) o con la
  tolerancia que ya fija la prueba de origen (±0,01 en la presentación; ±0,005 en el Excel evaluado).
- **Mismos mensajes:** igualdad de cadena para lo que sale de `aplicacion/hoja.py`; para lo que compone la interfaz, igualdad
  tras `core.verification.texto.normalizar_texto` (sin tildes, sin mayúsculas).
- **Diferencias deliberadas** (todas declaradas, §9.3): no cuentan como fallo de paridad.
- **Registro:** un archivo `docs/bitacora/2026-10-xx-hoja-paridad.md` con una fila por prueba: clásica, nueva, valor esperado,
  resultado, SHA. Lo llena el implementador de 3e; el árbitro lo verifica corriendo las pruebas citadas.

### 9.2 Pruebas de aceptación de paridad

| Id | Qué se hace | Valor esperado (oráculo) | Rebanada |
|---|---|---|---|
| P1 | abrir OF-001 v001, total | 2 703,86 USD ±0,01 (memoria `of001.md`; `test_aceptacion_sf.py:60`) | 3b |
| P2 | cantidades derivadas AF-LLAVE, tubería drenaje 2", tubería agua fría ½" | 3 · 4,345 · 8,250 (memoria §2.4) | 3b |
| P3 | punto de equilibrio: CV, PE, %, período | 2 137,44 · 1 530,49 · 56,60 % · «Dia 23» (`test_aceptacion_sf.py:62-65`) | 3b |
| P4 | frases de PE de los 4 casos límite | texto de H:1221-1238 | 3b |
| P5 | Estado por fila: fila limpia y fila con ERROR/ADVERTENCIA/PENDIENTE | `OK`; `ERROR: …`; `PENDIENTE: sin APU en el catálogo (AF-SALIDA)` (H:1439-1480; casos de `test_hoja.py`) | 3b |
| P6 | abrir TI-001: sin espacio, con plan y PE; no crea versiones ni filas `esp_*` | `test_ui_hoja.py:580-611` | 3b |
| P7 | proyecto sin versiones: borrador en blanco y mensaje | P:140, 588-591 | 3b |
| P8 | historial de versiones tras 001/002/003 | tabla de `test_aceptacion_sf.py:378-383` | 3b |
| P9 | Precios: 21 columnas, estado, erosión con fecha fija | `test_ui_hoja_moneda.py:113`; memoria `s1_conversion.md` | 3b |
| P10 | Trazabilidad: registros de la 002 | `test_aceptacion_sf.py:329-347` | 3b |
| P11 | Auditoría con R17 | `test_ui_hoja_conexion.py` | 3b |
| P12 | cierre de partida (cascada) | `test_ui_hoja_trabajo.py:87-130` (a mano) | 3b |
| P13 | parámetro `administracion = 0.20` | total ≈ 2 821,42; PE ≈ 1 763,39; PE % 62,50; `cambios == 1` (cuenta a mano a confirmar) | 3c |
| P14 | parámetro inválido `utilidad = mucho` | `parametros: utilidad: 'mucho' no es un numero decimal valido`; borrador intacto | 3c |
| P15 | cantidad AF-LLAVE 3 → 5 | `Δ = 2 × CD × 1,15 × 1,10`; R8 ADVERTENCIA | 3c |
| P16 | cantidad negativa | mensaje de H:861-863 | 3c |
| P17 | alto de ambiente `2,5` | `ambientes, fila n: alto: '2,5' no es un numero decimal valido` | 3c |
| P18 | fila en blanco ignorada; id duplicado | sin error; mensaje de `Espacio` | 3c |
| P19 | plan: suma ≠ 1 | H:1209-1212 | 3c |
| P20 | crear plan secuencial | curva que cierra en el total (`test_ui_hoja.py:267`) | 3c |
| P21 | cambiar insumo de una línea | descripción/unidad/precio nuevos, cantidad conservada | 3c |
| P22 | partida nueva toma su APU del catálogo; partida sin APU queda pendiente | `pendientes_catalogo` | 3c |
| P23 | cambiar de versión con cambios | confirmación; nada se descarta solo | 3c |
| P24 | restaurar/cotizar bloqueados con cambios pendientes | textos de P:1946, 2081, 2201 | 3d |
| P25 | guardar sin fuente | H:1797; no hay versión nueva | 3d |
| P26 | guardar con fuente | versión 002, `cambios == 1`, `RegistroCambio` exacto | 3d |
| P27 | cadena íntegra tras guardar | `estado_de_la_cadena(...).integra` | 3d |
| P28 | guardado que falla | nada escrito (recuento SQL) | 3d |
| P29 | solo lectura | H:1842-1846 | 3d |
| P30 | primera versión de un proyecto nuevo | `001`; un solo registro `version/creacion`; moneda y lista (H:1960-1971) | 3d |
| P31 | restaurar la 001 | 003 igual a la 001; 001 y 002 siguen; 003 vigente | 3d |
| P32 | cotizar / retirar | conserva plan y curva; solo cambia ese insumo | 3d |
| P33 | convertir moneda | total ÷ o × tasa ±0,01; sin tasa: «No se convirtio nada: …» | 3d |
| P34 | responsable = la sesión, diga lo que diga el cuerpo | `test_ui_hoja_responsable.py:97-126` | 3d |
| P35 | permisos por rol | `rita` 403; clave de API 403 en escrituras | 3d |
| P36 | Excel de OF-001 | 9 hojas + extras; total evaluado = sistema ±0,005 | 3e |
| P37 | plano DXF de OF-001: alturas, circuitos, fusión | total 2 703,86 ±0,01; cantidades ±0,001 | 3e |
| P38 | plano rechazado, detenido, extensión ajena | mensajes de H:2603-2611 y P:1443-1449 | 3e |
| P39 | interfaz: 1366×768 sin desplazamiento horizontal de la página; teclado; un `h1`; foco visible | auditoría visual (T11) + Vitest | 3b a 3e |

### 9.3 Diferencias deliberadas (declaradas)

| # | Diferencia | Motivo |
|---|---|---|
| DV-1 | No hay mensaje con `error.orig` del driver (§4.7) | C1: ni SQL ni rutas en errores |
| DV-2 | Estado de fila en la misma tabla (no aparte) | en React la clave de la fila evita el reinicio del editor que obligaba a separarlo (P:18) |
| DV-3 | «Preparar Excel» y «Descargar Excel» son un solo botón | no hay estado intermedio que quede viejo |
| DV-4 | Guardar muestra la lista de cambios y bloquea la fuente vacía antes de enviar | menos errores; el servidor sigue validando |
| DV-5 | El proyecto es el de la cabecera; no hay selector de proyecto en la página ni «borrador sin proyecto» | una sola fuente (D-7) |
| DV-6 | Aviso de versión más nueva y 409 (D-5) | concurrencia que la clásica no cubría |
| DV-7 | Estado de la cadena en Trazabilidad | `aplicacion/entrega.py:150` lo declara; la clásica no lo mostraba |
| DV-8 | «Volver a la calculada» en una cantidad escrita | atajo; el servidor aplica la misma regla |
| DV-9 | El borrador se puede retomar tras recargar | mejora; el costo es el estado en memoria (§3.1) |
| DV-10 | `beforeunload` con cambios | la clásica no podía (P:28-30) |
| DV-11 | Columna «Erosión por índice» solo si hay valores | nunca se llenaba en la clásica |
| DV-12 | Los textos nuevos llevan tildes; los de `aplicacion/hoja.py` no | D-3 |
| DV-13 | Mientras haya una sección con texto no aceptado, Guardar y Descargar Excel quedan deshabilitados | la clásica guardaba el último válido ocultando el error; es más seguro. Reversible |

---

## 10. Decisiones abiertas (recomendación conservadora y reversible)

| Id | Decisión | Quién | Recomendación | Si se elige otra cosa |
|---|---|---|---|---|
| **D-1** | Mover `ui/hoja.py` a `aplicacion/hoja.py` toca un archivo congelado del experimento (RS-9) y la guardia ya está en rojo por RM-1 anteriores. ¿Se autoriza el traslado byte a byte y re-congelar? | Eugenio (y tutor si el protocolo es suyo) | **A** (§5.5): traslado puro + prueba de equivalencia + re-congelar en commit aparte + nota en bitácora; antes de 3b | B duplica código; C debilita la arquitectura; D bloquea |
| **D-2** | Borrador en el servidor (A) o en el navegador (B) | ingeniería (informa a Eugenio) | A (§3.1); se revisa con la medición de 3c | B: un solo `POST /calculo` con ediciones |
| **D-3** | Mensajes de `aplicacion/hoja.py` sin tildes | Eugenio | dejarlos (D1 menor declarado) hasta una pasada futura que re-congele | pasada de tildes: cambia texto que ven el asistente y sus pruebas |
| **D-4** | Acción de `/convertir` | ingeniería | `convertir_y_reajustar` (matriz de permisos) | `editar_hoja`, igual por ahora |
| **D-5** | Qué hacer si hay una versión más nueva al guardar | Eugenio | 409 con confirmación | solo aviso, como la clásica |
| **D-6** | Cuándo se activa «Hoja del proyecto» en el menú nuevo | Eugenio | al aprobar 3d (guardar y versiones); antes la clásica sigue siendo la única entrada; 3b y 3c son alcanzables solo por pruebas | activar en 3b con un aviso de «vista previa» |
| **D-7** | Quitar «borrador nuevo, sin proyecto» y el selector de proyecto de la página | Eugenio | quitarlo: se necesita un proyecto en la cabecera | agregar `proyecto: null` (el servidor ya lo admite sin costo) |
| **D-8** | Aceptar coma decimal en las celdas (es-VE) | Eugenio | no en esta migración (paridad: la clásica la rechaza); ayuda visible | normalizar «,»→«.» en el **servidor** para todas las celdas, con prueba |
| **D-9** | Topes y plazos supuestos: 4 borradores por ficha, 8 h de vigencia, tablas de 5 000/1 000/1 000/5 000/20 000 filas, 25 MiB por plano, 8 MiB por cuerpo | Eugenio | adoptarlos y registrarlos como supuestos declarados; se ajustan con la medición de 3b/3c | cambiar números en `aplicacion/hoja_borradores.py` y `api/esquemas_hoja.py` |
| **D-10** | ¿El visor de libros (Univer) debe mostrar el Excel exportado como vista previa? | Eugenio | no ahora | rebanada aparte |

---

## 11. Texto exacto para los archivos compartidos (lo aplica el orquestador)

Estos cambios los hará el orquestador cuando cada rebanada apruebe; no los hace este documento.

**3b**

- `api/main.py`: añadir `hoja` a la lista de `from api.rutas import (...)` (orden alfabético, entre `entregas` e `indices`) y, con
  su comentario, tras `revision`:
  `# Migracion final (T10 · 3b): «Hoja del proyecto»; lecturas con clave o sesion, borradores y escrituras solo con sesion`
  `app.include_router(hoja.router)`
- `tests/unit/test_api_acceso_por_ruta.py`: una fila por ruta de §4.3 con su acceso (lectura: clave o sesión `arma`;
  borradores: solo sesión `arma`), y la comprobación de que `rita`, `admin` y `tomas` reciben 403.
- `tests/unit/test_arquitectura.py`: (1) `test_ui_hoja_depende_de_adapters_espacio_y_este_no_depende_de_ui` pasa a leer
  `RAIZ / "aplicacion" / "hoja.py"`; (2) añadir `test_ui_hoja_reexporta_la_capa_de_aplicacion` igual que
  `test_ui_composicion_reexporta_la_capa_de_aplicacion` (`:725-740`), con `ui/hoja.py` y `aplicacion/hoja.py`; (3)
  `PROHIBIDOS_EN_UI["ui/hoja.py"]` se conserva.
- `CHANGELOG.md`: «Hoja del proyecto en la interfaz nueva, lectura: `/v1/hoja` (versiones, borradores, vistas, precios,
  trazabilidad); `ui/hoja.py` pasa a `aplicacion/hoja.py` (RM-1).» (una línea por cambio).
- `docs/api.json`: regenerar con `scripts/exportar_openapi.py`.
- `asistente/experimento/protocolo.json` y `congelado.json`: **solo** si D-1 = A, en un commit aparte con árbol limpio.
- `frontend-desktop/src/shell/rutas.ts` (línea 61): **no se cambia en 3b** (D-6). Al aprobar 3d:
  `{ id: "hoja", titulo: "Hoja del proyecto", seccion: "Trabajo", accion: "editar_hoja", cargar: () => import("../paginas/hoja") },`
  y su prueba (`rutas.test.ts`).

**3c, 3d, 3e:** una fila de acceso por ruta nueva, una línea de CHANGELOG y `api.json` regenerado en cada una. `docs/ERS.md`: al
cerrar 3e, en la tabla de §4.x (interfaz nueva) anotar que UC-13, UC-14, UC-15 y UC-16 se cubren también en la interfaz nueva
(el texto exacto lo propone el implementador de 3e con las páginas migradas).

---

## 12. Lo que no pude determinar

1. Si ya se corrió alguna medición del experimento con el congelado vigente (§1.1): no hay forma de leerlo en el repositorio.
2. El tiempo real del recálculo con R17 y de `abrir` para 500 puntos en la API: RNF-11 midió 0,125 s sin R17 y sin API; lo
   miden 3b-B22 y 3c-B18. Tampoco el tamaño en memoria de un borrador (3b-B23).
3. El número de hallazgos del informe vivo de una hoja grande (R-10).
4. Si 9 pestañas caben en 1078 px con Carbon `Tabs` a 1366 px sin botones de desplazamiento, y si la tabla de puntos (13
   columnas) es utilizable con columna fija: lo decide la auditoría visual de T11.
5. El tamaño real de planos DXF/IFC de la empresa (no hay en el repositorio; los reales son confidenciales): el tope de 25 MiB
   es un supuesto.
6. Si `useBlocker` es realmente inusable con `HashRouter` (lo afirmo por la documentación de la librería; no lo probé).
7. Los valores 2 821,42, 1 763,39 y 62,50 % de P13 son una cuenta a mano de este diseño sobre las cifras de la memoria (CV
   2 137,44 y cascada 1,20 × 1,10); deben confirmarse contra `tests/fixtures/memorias/of001.md` antes de fijarse en una prueba.
8. Los valores cerrados de `SuperficiePunto` y `SuperficieTramo` (solo conozco los rótulos de H:268-273); el servidor los
   entrega desde los enums, así que no hay que copiarlos.
