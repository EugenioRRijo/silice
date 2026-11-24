# F2: inventario del front por tareas de la persona (cuatro perspectivas)

Árbol: `.worktrees/s2mi2`, rama `feature/carga-cognitiva`. Rutas de archivo relativas a `frontend-desktop/src/`.
Método: lectura de código y `grep`. **Nada se probó en el navegador.** Cada hallazgo lleva su marca:
**[V]** verificado en el código citado; **[I]** inferido (depende de datos o del servidor que no se ejecutaron).
Umbrales F0: 8 decisiones o menos por paso, ninguna sigla sola, un solo botón principal por vista, todo éxito con su
paso siguiente, trato de usted. Lo que ya está en `carga-cognitiva §6` o `§1-§4` se cita y no se repite.

## 1. Tabla resumen

| Tarea | P1 | P2 | P3 | ¿Se completa hoy? (inferido, sin navegador) |
|---|---|---|---|---|
| T1 Crear obra y llegar a su presupuesto | 0 | 4 | 3 | Sí. El camino es corto y termina en una franja con botón. |
| T2 Armar el presupuesto (partidas, total) | 1 | 5 | 2 | Sí, para quien viene de Excel; el exceso de controles frena a quien no domina el oficio. |
| T3 Guardar versión y enviar a aprobación | 0 | 5 | 2 | Sí. Se pierde el camino después de enviar y después de aprobada. |
| T4 Valuación o corte en Control y leer el resultado | 3 | 4 | 2 | Con ayuda. No hay puente de «registrar» a «leer el resultado». |
| T5 Calcular un reajuste | 1 | 3 | 1 | Sí con quien conoce la cláusula; difícilmente con quien no domina el oficio (ya en carga-cognitiva §1). |
| T6 Proyectar el riesgo | 1 | 3 | 1 | Sí; el resultado queda lejos de los controles (ya en carga-cognitiva §2). |
| T7 Auditar un libro Excel | 0 | 4 | 2 | Sí. Hay dos entradas y dos principales deshabilitados. |
| T8 Cargar la lista de precios de la empresa | 2 | 4 | 1 | **No en una carpeta sin lista base**: el aviso manda a otra sección sin enlace. |

## 2. Hallazgos por tarea

### T1 Crear una obra y llegar a su presupuesto

Secuencia [V]: `BarraLateral.tsx:238` («Nueva obra») → `shell/obras/DialogoNuevaObra.tsx` → `BarraLateral.tsx:256-260`
(cierra, recarga y navega a `/obra/.../resumen`) → `paginas/obras/index.tsx:54-64` (`FranjaDelPaso` con el paso del
servidor, p. ej. «Agregue la primera partida») → botón a Presupuesto.

**Éxito**
- [V] Bien resuelto: el éxito de crear termina en una franja con su botón (`obras/index.tsx:54-64`). Quien no domina el
  oficio ve «Agregue la primera partida» sin saber qué es una partida. El texto lo da el servidor y la ayuda
  «¿Qué es esto?» no se ofrece ahí. [I] P3.
- [V] `DialogoNuevaObra.tsx:166` «Tipo de obra» queda en «Sin especificar» y no dice para qué sirve (P3).

**Excepción**
- [V] **P2** Un error del servidor al leer la ficha se muestra como vacío. `marco/useFichaDeLaObra.ts:12,29-34` convierte
  403, error y falta de fila en `sin_dato`, y `obras/index.tsx:43` pinta «No hay datos de esta obra todavía.» sin causa
  ni reintento. Incumple UX-27 y es un error disfrazado de estado vacío.
- [V] **P2** Moneda: `DialogoNuevaObra.tsx:184` sin moneda de la carpeta el campo arranca en «Elija…» y es obligatorio
  (bien dicho en `:178`). Sin tasa del BCV la moneda USD/Bs se explica solo en `:33` y `:118-120`. Tolerable.
- [V] Un error al crear conserva lo escrito (`:194`, el diálogo no se cierra). Cumple UX-12.

**Negativa**
- [V] Controles del diálogo: nombre, cliente, ubicación, tipo, moneda, «Cancelar» y «Crear la obra» = 7. Cumple ≤ 8.
- [V] **P2** Dos accesos con el mismo nombre a «Nueva obra»: `BarraLateral.tsx:175` y `:238` (y por `marco/nuevaObra.ts` el
  Resumen vacío). Con el mismo texto no se distinguen; bien que sea un solo diálogo, pero el botón de la barra usa
  `silice-marco-boton-principal`, que cuenta como segundo «principal» frente a la franja del Resumen (UX-13). [I] el
  conteo visual depende del CSS.
- [V] **P2** «Siguiente paso:» y «Te falta:» (`comun/FranjaDelPaso.tsx:25`) tutean. «Te falta» es forma de tú; usted es
  «Le falta». También «Empieza aquí» (`comun/ayuda/AyudaDeSilice.tsx:16,60`, `marco/espacios.ts:215`).

**Positiva**
- Dejar ya puesto: la moneda ya sale de la carpeta (`:74`); bien. Quitar: «Tipo de obra» y «Ubicación» podrían ir en
  «Más opciones» (quedan 5 a la vista: nombre y moneda + 2 opcionales + botón). [I] P3.
- Se reutiliza `FranjaDelPaso`; no hace falta pieza nueva.

### T2 Armar el presupuesto: agregar partidas con cantidad y revisar el total

Secuencia [V]: `hoja/index.tsx:298` (`FranjaDelPresupuesto`) → pestaña «Partidas» `PestanaPresupuesto.tsx:416-454`
→ «Agregar partida» `:425-437` → `AgregarPartida.tsx:233-355` → aviso «Se agregó X al presupuesto.» `:398` → total en
`EstadoDelBorrador.tsx:30` y `PestanaPresupuesto.tsx:338-341`.

**Éxito**
- [V] **P1** Decisiones a la vista por omisión en el Presupuesto. Fuera de la tabla: 6 o 7 pestañas
  (`hoja/logica.ts:21-28`; «Espacio» solo en obras de instalaciones), `Descargar Excel`, `Agregar partida`, el botón de la
  franja, `¿Qué es esto?` y, con cambios, `Descartar cambios`: ≈ 11. Dentro de la tabla (`PestanaPresupuesto.tsx:192-313`):
  hasta 10 columnas (Partida, Descripción, Unidad, Cantidad, Cómo se midió, Precio unitario, Objetivo de mercado, Total,
  Estado, Quitar) y 3 controles por fila (código que abre el APU, cantidad, Quitar). Supera 8. Es una hoja de cálculo
  y el usuario de Excel lo tolera; quien no domina el oficio no sabe qué mirar. Ya hay frase de respuesta en la franja.
- [V] **P2** Agregar varias partidas es un camino de ida y vuelta: cada «Agregar al presupuesto» cierra el diálogo
  (`PestanaPresupuesto.tsx:394-402`, `cerrar(true)`). Para 30 partidas son 30 aperturas. Falta «Agregar y seguir»
  (`AgregarPartida.tsx:347-354`). Quien viene de Excel espera teclear filas.
- [V] Positivo: el diálogo tiene 7 controles (Partida, Buscar parecidas, Cantidad, Cálculo, Nota, Cancelar, Agregar;
  `AgregarPartida.tsx:248-354`), foco en Cantidad si la partida viene de Componer (`:135`), ejemplos en la ayuda
  (`:37,40,42`). Cumple.
- [V] **P3** «Cálculo (opcional)» y «Nota de medición (opcional)» van siempre a la vista (`:305-332`). Podrían plegarse
  («Más opciones»), con el campo Cálculo recordado.
- [V] El total se ve arriba (`EstadoDelBorrador.tsx:30`) y abajo (`PestanaPresupuesto.tsx:338`), con unidad y valor
  exacto. Cumple UX-24; es duplicado, **P3**, UX-02.

**Excepción**
- [V] Un 422 deja lo escrito y pone el foco en el campo (`AgregarPartida.tsx:209-212`); cumple UX-12.
- [V] Partida sin precio: la fila muestra «Pendiente» (`PestanaPresupuesto.tsx:271,280`) sin frase ni paso siguiente en
  la fila. El aviso `aviso` del servidor sale una vez al agregar (`:49`, `:398`) pero desaparece al volver a la pestaña.
  **P2**: una columna «Precio unitario: Pendiente» no dice qué falta (lista de precios) ni cómo resolverlo.
- [V] **P2** Presupuesto vacío: `vista.vacio_mensaje` se pinta como `<p>` sin acción (`PestanaPresupuesto.tsx:444-446`);
  la acción vive en la franja (aceptable), pero si no tiene permiso de editar no hay paso siguiente.
- [V] Sin tasa del BCV o sin lista: llega como `general: e.detalle` en un aviso dentro del diálogo
  (`AgregarPartida.tsx:63-64`, `:221-223`). Dice qué pasó; el paso siguiente no se ofrece como botón. **P2** [I].

**Negativa**
- [V] Siglas: pestaña «Análisis de precio (APU)» ya cumple (`hoja/logica.ts:24`). «FCAS» solo en
  `componer/ParametrosDelPrecio.tsx:11` y explicada en `hoja/PestanaParametros.tsx:74` (ya en carga-cognitiva §6).
- [V] Dos principales: no. Un solo principal (la franja); «Agregar partida» es terciario (`:428`). Cumple UX-13.
- [V] «Estado» como columna de texto de severidad por fila sin explicación en la cabecera (la ayuda está en
  «¿Qué es esto?»). P3.

**Positiva**
- Plegar: «Objetivo de mercado» y «Cómo se midió» a un pliegue por fila o a una vista «Detalle». Quitar: «Descargar
  Excel» a «Más acciones». Reutilizar: `FranjaDelPaso` ya está; `TablaDensa` ya se usa por `TablaPaginada`.

### T3 Guardar la versión y enviarla a aprobación

Secuencia [V]: franja «Guardar versión…» (`textos.ts:80-92`) → `DialogoDeGuardar.tsx` → `AvisoDeGuardado.tsx` → franja
«Envíe la versión X a aprobación» (`pasoDelPresupuesto.ts:59`) → `AprobacionDeVersion.tsx:117-217` → aviso «Se envió…»
(`FranjaDelPresupuesto.tsx:99-105`).

**Éxito**
- [V] **P2** Después de enviar no queda un paso siguiente. `pasoDelPresupuesto.ts:55` da «La versión X espera dictamen»
  con `accion: null` (sin botón) y, **ya aprobada**, `:56` devuelve `null`: la franja desaparece. Ni «Entregar el
  paquete» (existe `aprobaciones/entregar`) ni «Empezar el control» se ofrecen. Un éxito sin paso siguiente (F0).
- [V] **P2** `AvisoDeGuardado.tsx:17` dice «Versión guardada» sin paso; el siguiente se infiere de la franja cuando
  termina de leer la aprobación (`FranjaDelPresupuesto.tsx:86`, la franja desaparece mientras lee: parpadeo, P3).
- [V] **P2** `DialogoDeGuardar.tsx:183-190`: «Fuente del cambio (por qué y con qué respaldo)» (`logicaGuardar.ts:56-57`)
  es obligatoria, sin marca de obligatoria y sin ejemplo. Quien no domina el oficio no sabe qué escribir (la ayuda
  vive en el `motivo` al fallar, `:96-100`: «un plano, un acta»).

**Excepción**
- [V] Sin versión más nueva, rev viejo, ausente: cada clase tiene título, texto y botón (`DialogoDeGuardar.tsx:27-37`,
  `:229-251`). Buen manejo. Conserva lo escrito.
- [V] Fallo al enviar: `AvisoError` en el diálogo, nota conservada (`AprobacionDeVersion.tsx:204`). Cumple UX-12.
- [V] Fallo al leer el estado: «No se pudo leer el estado de aprobación de esta versión.» (`:66`) sin reintento.
  **P3**.

**Negativa**
- [V] **P2** Botón principal deshabilitado para validar: `DialogoDeGuardar.tsx:267` `disabled={motivo !== null …}`; el
  motivo se lee en una nota (`:192-196`) pero el botón no dice por qué está inactivo en su cara. Regla: validar al
  pulsar y dejar el botón activo (carga-cognitiva §5 y UX-11).
- [V] Dos diálogos con un principal cada uno, uno a la vez. Cumple.
- [V] La lista de «Cambios» del diálogo trae tabla de 5 columnas y 200 filas (`DialogoDeGuardar.tsx:23,83`): útil como
  respaldo; sin frase de respuesta, el título «Cambios (N)» lo dice. P3.
- [V] **P3** «Guardar de todos modos» como `danger--tertiary` (`:231`) sin consecuencia nombrada (UX-16).

**Positiva**
- Quitar: «Responsable» (`:206`, solo lectura) a pie de diálogo. Dejar puesto: la fuente puede recordar la anterior
  (carga-cognitiva §5, regla 5). Unir: el aviso «Se envió…» con la franja de estado en una sola línea con el paso
  siguiente. Pieza: `FranjaDelPaso` ya existe.

### T4 Registrar una valuación o corte en Control de obra y leer el resultado

Secuencia [V]: `control/index.tsx:72-119` (6 pestañas, la primera es «Línea base») → `PestanaLineaBase.tsx` (Declarar,
`:180`) → `PestanaValuaciones.tsx:204-282` (Registrar) → resultado en «Valor ganado» (`PestanasDeResultados.tsx:132`).
Reajuste y Escenarios son subvistas de Control (`marco/espacios.ts:152-156`).

**Éxito**
- [V] **P1** Registrar y leer son dos lugares sin puente. Tras «Guardar valuación y recalcular avance»
  (`PestanaValuaciones.tsx:272`) solo aparece el aviso verde `AvisoDeRegistro` (`:277-280`, `:62-82`); no hay botón a
  «Valor ganado» ni frase con el avance. La persona debe saber que el resultado vive en otra pestaña.
- [V] **P1** El formulario no se limpia tras un éxito (en `Registrar` no hay `setV` ni `setLineas` de reinicio; solo
  `setRegistro`, `:168-202`): un segundo clic registra la misma valuación otra vez. [I] el servidor puede rechazar el
  duplicado por número; confirmar.
- [V] **P1** Cuántos controles: cabecera de 5 campos (Número, Período desde, Período hasta, Fecha, Inspector,
  `:207-211`) + por línea 5 (Partida, Cantidad, Fecha de medición, Observación, Causa del retraso, `:226-263`) +
  «Agregar línea» + Fuente + botón = 13 con una línea, y +5 por cada línea añadida. Ya en carga-cognitiva §6; aquí con
  conteo. El «Número» no se propone (`:207`, valor vacío al inicio) [I].
- [V] **P2** Para quien no domina el oficio, «Línea base» (primera pestaña) no se explica: `control/index.tsx:46-51` y
  `PestanaValuaciones.tsx:512-514` dicen «Se hace en la pestaña «Línea base»» como texto, sin botón. Mismo patrón en
  `precios_empresa/logica.ts:14` (T8).
- [V] **P2** Éxito de la línea base sin paso: `PestanaLineaBase.tsx:125` devuelve «Línea base declarada.»; no ofrece
  «Registrar la primera valuación».

**Excepción**
- [V] Sin obra: `control/index.tsx:91-92` EstadoVacio con descripción. Sin permiso/errores: `AvisoError` con título
  (`:43-44`). Cumple.
- [V] Sin tasa del BCV en el corte: `PestanasDeResultados.tsx:147-151` dice «Sin tasa del BCV para el corte: no se
  muestran los montos en la otra moneda.» Dice qué pasó; no ofrece enlace a «Índices del BCV» como hace Riesgo
  (`RiesgoDeLaObra.tsx:300-305`). **P2**.
- [V] Un error de registro deja lo escrito (el formulario es estado local y `AvisoError` va debajo, `:276`). Cumple.

**Negativa**
- [V] **P2** Principales a la vez: el formulario «Registrar» (abierto, `:204`) lleva un `primary` (`:272`); «Importar»
  (`:349`) lo trae al soltar un libro; «Anotar un costo» (`:451`) y «Procura» (`PestanaProcura.tsx:116`) tienen el suyo.
  Con dos `<details>` abiertos hay dos principales. Solo dos `<details open>` en todo `paginas/` (`grep`).
- [V] Siglas: «Km», «(R)» (`PestanasDeResultados.tsx:102,111`), «SPI y CPI» (`:155`), «PV/EV/AC» (`:169-178`): ya en
  carga-cognitiva §6; siguen vigentes. La guardia `sinJergaInterna.test.ts` **no** las vigila: solo mira `UC-/RF-/RNF-`
  y palabras del marco (`:15`, `:60` ss.).
- [V] **P2** «Fuente (acta, oficio)» (`:270`), «Documento de respaldo de Km y R» (`PestanasDeResultados.tsx:118`),
  «Fuente del costo», «Fuente de la importación», «Fuente del cambio de parámetros»: cinco rótulos «Fuente» sin
  ejemplo ni marca de obligatorio.
- [V] **P3** Importar: nombres de hojas y columnas en minúsculas, sin tildes, en un párrafo (`:323-327`).

**Positiva**
- Plegar: las 5 columnas de la línea a 2 (Partida, Cantidad) más «Más datos de la línea». Dejar puesto: número siguiente,
  fecha de hoy, fuente anterior. Unir: «Registrar» y «Ver el avance» con `FranjaDelPaso`. Pieza: `FranjaDelPaso`,
  `EstadoVacio` con botón hijo, `TablaDensa`. **Necesita back** solo para proponer el número de valuación:
  `aplicacion/control.py` o `api/rutas` (ruta `/v1/control/valuaciones`) [I].

### T5 Calcular un reajuste

Secuencia [V]: Control › Reajuste (`espacios.ts:152-156`) → `reajuste/index.tsx:300-457` (versión + 2 pasos) → «Calcular»
`:449` → resultado `:466-529` → «Guardar estudio» `:511`.

**Éxito**
- [V] **P1** (ya en carga-cognitiva §1) Paso 1 lleva 15 controles propios + componentes (`:300-400`): versión (1), plazo
  (4), cómo se reajusta (5), R y fuentes (4), casilla (1), «Siguiente» (1). Los textos «R», «Km», «Gaceta» y los métodos
  no llevan ejemplo. No lo repito; solo anoto el conteo.
- [V] **P2** Descubribilidad: Reajuste no aparece en la barra de secciones de la obra; es una subvista de Control
  (`espacios.ts:152-156`). Quien busca «reajuste» en la barra no lo encuentra salvo por el buscador. [I] depende de
  `BarraDeEspacio`.
- [V] **P2** Éxito sin paso siguiente: `index.tsx:295` «Estudio N guardado (estado).» en un `<p role="status">`; «estado»
  puede ser «cerrado/parcial» (`estadoDelEstudio`). Nada lleva de ahí al Excel ni a Control; el botón «Descargar Excel»
  solo está arriba (`:514`).

**Excepción**
- [V] Cifras mal escritas: marca cada una y no envía (`:271-279`). Falta lista de series BCV: `CampoDeSerie` cae a
  texto libre (`:82`, `series.ts`) sin aviso de «importe los índices primero». **P2** [I].
- [V] Sin versiones: «La obra no tiene versiones guardadas: guarde la del contrato primero» (`:185`) sin botón (patrón
  de T8). **P2**.
- [V] El resultado se retira al editar (`:242`), lo escrito queda. Cumple UX-12.

**Negativa**
- [V] Un solo principal real: «Calcular» baja a secundario cuando hay resultado (`:449`) y «Guardar estudio» pasa a
  principal (`:511`). Buen patrón; **repetible** (ver §3).
- [V] **P3** Cifras sin unidad: la tabla de resultado viene del servidor (`calculo.columnas`, `:473`); sin frase de
  respuesta encima (el título solo dice «Resultado: escalatoria frente a comprobación directa», `:139`).

**Positiva**
- Dejar puesto: periodicidad y estructura con el valor más común; mecanismo pagadero solo cuando «ambos» (carga-cognitiva
  §1). Plegar: Responsable, Fuente de cláusula, «Excepción». Pieza: `FranjaDelPaso` para «Guardado: descargue el Excel».

### T6 Proyectar el riesgo de la obra

Secuencia [V]: `riesgo/RiesgoDeLaObra.tsx:216-343`: Versión → Parámetros comunes → Serie por insumo → Proyectar → resultado.

**Éxito**
- [V] **P1** (carga-cognitiva §2) Controles a la vista: Versión (1) + meses, semilla, meses de historia (3) + un `Select`
  por cada insumo y componente (`ParametrosDelRiesgo.tsx:98-111`, N) + fecha de inicio, simulaciones, «Proyectar» (3) +
  simulaciones por fecha probada, «Probar precisión…» (2) = **9 + N**. En una versión con 40 insumos son 49. El resultado
  queda abajo (`:309-327`); el foco salta al resultado (`:107`), mitiga.
- [V] **P2** El resultado no empieza con la respuesta: una lista de 4 cifras con «Total base / P50 / P80 / Reserva»
  (`ResultadoDelRiesgo.tsx:52-61`). Las siglas están bien (palabra primero, sigla en paréntesis, `:55,57`), pero falta
  la frase («Reserve X para cubrir 8 de cada 10 casos»).
- [V] **P2** Éxito sin paso siguiente: solo «Descargar el informe de riesgo» (`RiesgoDeLaObra.tsx:316-323`). No hay
  «Llevar la reserva al presupuesto» ni «Probar precisión» como paso sugerido.

**Excepción**
- [V] Sin versión: `EstadoVacio` con botón principal «Ir al presupuesto» (`:225-231`). Buen patrón, **repetible**.
- [V] Falta una serie: aviso con enlace a «Índices del BCV» solo si `administrar_precios` (`:300-306`). Sin ese permiso
  no hay paso siguiente alternativo (decir a quién pedirlo). **P3**.
- [V] Falta la fecha de inicio: el error va al campo y el foco también (`:99-103`). Cumple UX-11.
- [V] Sin tasa del BCV en una obra en Bs: se dice en los supuestos plegados (`ResultadoDelRiesgo.tsx:76-83`). [I] P3.

**Negativa**
- [V] Dos acciones con cálculo: «Proyectar» (principal) y «Probar precisión con meses pasados» (secundario). Cumple UX-13.
- [V] **P2** «Semilla» (`ParametrosDelRiesgo.tsx:64`) es jerga: el rótulo la explica entre paréntesis (`logica.ts:26`); lo
  correcto sería quitarla de la vista (default 1, como pide el propio texto).

**Positiva**
- Plegar «Parámetros comunes» y las series por insumo bajo «Elegir qué serie mueve cada insumo (N)» con el recuento;
  Dejar puesto lo recordado (DS-90 ya lo hace). Pieza: `FranjaDelPaso` para «Siguiente: probar la precisión».

### T7 Auditar un libro Excel de la empresa (Visor o Libros)

Secuencia [V]: `auditoria/index.tsx:59-75` (soltar + dos botones) → `navegar` a `libros` (`:40`) → `visor/Visor.tsx`
(`:365-400` vacío, `:435-520` resultado).

**Éxito**
- [V] **P2** Dos entradas al mismo visor: «Subir y auditar Excel» (`espacios.ts:114`) y «Libro de la empresa»
  (`:115`, `libros/index.tsx`), que pide soltar de nuevo el libro (`Visor.tsx:395-404`). La ruta de Subir lleva a Libro y
  usa `archivoPendiente`. Quien entra por Libro ve otra pantalla vacía con otro texto («Abra un libro para auditarlo»).
- [V] **P2** Éxito sin paso siguiente claro tras auditar: el único control es «Descargar PDF» terciario
  (`Visor.tsx:455-470`); lo que se hace con los hallazgos (corregir, devolver el libro corregido) lo dice una nota
  de la fecha (`:318`). [I] P2.
- [V] Visor: pestañas con conteo de hallazgos por hoja, lista con filtros y halos: coherente.

**Excepción**
- [V] Error al mostrar: `InlineNotification` con título y mensaje (`Visor.tsx:381-390`). Archivo no xlsx: la zona
  `accept=[".xlsx"]`. Sin permiso: texto con quién pedirlo (`auditoria/index.tsx:78-86`). Cumple UX-27.

**Negativa**
- [V] **P2** Dos principales deshabilitados en la misma vista: «Auditar con recorrido guiado»
  (`auditoria/index.tsx:69`, `disabled={!archivo}`) y «Auditar el libro de APU»
  (`AuditarApuPorHoja.tsx:~312`, `disabled={libro === null …}`), más una segunda zona de soltar. El segundo flujo
  (libro con un APU por hoja) es otra tarea mezclada en la misma página.
- [V] **P3** Controles del bloque «APU por hoja»: Formato (1) + 2 zonas + una casilla por hoja del presupuesto (n) +
  botón (`AuditarApuPorHoja.tsx:239-318`) = 4 + n.
- [V] **P3** «Auditar con recorrido guiado» como principal y «por mi cuenta» como terciario: para quien viene de Excel el
  camino frecuente es el segundo (el guiado lanza `iniciarRecorrido`, `:39`).

**Positiva**
- Unir los dos accesos en uno («Auditar un Excel») con la zona única y el selector de formato (APU por hoja) plegado.
  Dejar `Visor` como la vista de resultado. Pieza: `FranjaDelPaso` en el visor con «Descargar PDF» como paso.

### T8 Cargar o actualizar la lista de precios de la empresa

Secuencia [V]: `precios/listas` (`espacios.ts:131`) → `precios_empresa/index.tsx:138-153` (4 secciones) →
`SeccionLista :199-407`. La carga de listas base está en otra sección: «Actualizar precios» (`espacios.ts:150`), que es
una subvista de Mercado de una obra.

**Éxito**
- [V] **P1** Sin lista base no se puede crear la de la empresa: `index.tsx:282-283` pinta solo
  `EstadoVacio titulo={SIN_BASES}` y `SIN_BASES = «La carpeta no tiene listas de precios: cargue una en Actualizar
  precios.»` (`logica.ts:14`). No hay botón ni enlace, y «Actualizar precios» **no vive** en «Precios y catálogo» sino
  bajo Mercado de una obra (`espacios.ts:150`): hace falta una obra abierta. Tarea imposible por la propia pantalla.
  Mismo patrón que `control/index.tsx:47,50` y `hoja/index.tsx:269`.
- [V] **P1** Para quien viene de Excel, «Actualizar precios» (`actualizacion/index.tsx:185`) es una pantalla de
  revaloración de un presupuesto con «Presupuesto base», «Código de la versión nueva», «Fecha de vigencia», «Moneda» y
  «Nombre de la lista» (`:199-243`): el nombre no dice «cargar la lista de precios». Rótulo de la tarea ≠ rótulo de la
  pantalla [I].
- [V] **P2** Tras crear la lista: éxito «Lista creada» (`:356`) con «Usarla para armar presupuestos» secundario
  (`:369-377`); luego «Ya puede componer con ella.» (`:384`) como texto, sin botón a Componer ni a Presupuesto.
- [V] **P2** `SeccionLista :285-346`: 7 campos (Empresa, RIF, Lista base, Moneda, Fecha, Fuente, Nombre) + zona de
  soltar + casilla + botón = 10 a la vista. Supera 8; «Nombre (opcional)» no se pliega (carga-cognitiva §6 ya lo marca).

**Excepción**
- [V] **P2** `MENSAJE_FALTA` (`logica.ts:17`, `:351`) dice «Elija la moneda de la lista y el archivo de precios» en un solo
  aviso, sin marcar el campo: la comprobación local solo exige moneda y archivo (`logica.ts:145-147`). Empresa, RIF y
  fuente quedan sin validar ni marcar: [I] el servidor decide.
- [V] Un error del servidor conserva lo escrito (el estado `creacion` no limpia los campos): cumple UX-12.
- [V] **P2** Moneda sin valor por defecto (`:295` «Elija Bs o USD») sin motivo en la cara; el motivo sí está en el aviso.
- [V] Sin tasa del BCV: no aplica a esta pantalla (copiar la lista «sin tasa», `componer/AvisoSinLista.tsx:105`).

**Negativa**
- [V] **P2** Cuatro bloques en una página: referencia MaPreX (botón terciario `:184`), crear lista (principal `:341`),
  hallazgos con dos controles más y «Buscar variaciones atípicas» (`:465-470`, `:523`), y la calculadora del FCAS
  (`SeccionFcas.tsx:22`, otro principal en `CalculadoraFCAS.tsx:164` al abrirse). Dos principales cuando la
  calculadora está abierta.
- [V] **P3** «RIF» y «FCAS» solos como rótulos (`:288`, `CalculadoraFCAS.tsx:32`, «Parte del FCAS»). «FCAS» se explica
  en `PestanaParametros.tsx:74`, no aquí.

**Positiva**
- Quitar: el bloque FCAS a su propia sección. Plegar: «Nombre» y «Fuente» tras la elección. Dejar puesto: fecha de hoy
  (ya está, `:207`), lista base la más reciente (`:253`). Pieza: `EstadoVacio` con botón hijo («Ir a cargar una lista
  base») y `FranjaDelPaso` tras crear. **No necesita back** (rutas ya existen en `espacios.ts`); sí un cambio de ruta
  para que «Actualizar precios» cuelgue también de «Precios y catálogo».

## 3. Patrones que se repiten (candidatos a guardia en la CI)

1. **Estado vacío que remite a otro lugar con texto y sin botón.** 32 de 52 `<EstadoVacio` de `paginas/` son
   autocontenidos (`grep`, sin hijo). Casos: `control/index.tsx:47,50`, `PestanaValuaciones.tsx:513`,
   `hoja/index.tsx:269`, `precios_empresa/logica.ts:14`, `reajuste/index.tsx:185`. Guardia: un `EstadoVacio` cuya
   `descripcion` o `titulo` nombre un destino («pestaña», «Actualizar», «guarde») debe llevar hijo. Ejemplo de buen
   patrón: `RiesgoDeLaObra.tsx:225-231`.
2. **Éxito que cierra con texto y sin paso siguiente**: `PestanaLineaBase.tsx:125`, `reajuste/index.tsx:295`,
   `PestanaValuaciones.tsx:277-280`, `precios_empresa/index.tsx:384`, `AvisoDeGuardado.tsx:17`,
   `pasoDelPresupuesto.ts:55-56`. Guardia: todo `InlineNotification kind="success"` y todo `role="status"` de éxito va con
   un enlace o botón hermano, o con la señal «último paso» (lista blanca).
3. **Conteo de controles por vista** (> 8): Registrar valuación (13+), Reajuste (15+), Riesgo (9+N), Precios de la empresa
   (10), Partidas (≈ 11 fuera de la tabla). Guardia: prueba por pantalla que cuente `textbox|combobox|checkbox|button` fuera
   de `<details>` cerrado y de la tabla (carga-cognitiva §5.12).
4. **Dos o más botones `primary` a la vez**: `<details>` abiertos de Control, `auditoria/index.tsx:69` y
   `AuditarApuPorHoja.tsx:~312`, `precios_empresa` con FCAS abierta. Guardia: `.cds--btn--primary` visibles ≤ 1 por
   vista (UX-13). Hoy el repo cuenta primarios por directorio: `administracion` 9, `produccion` 8, `hoja` 7, `control` 7.
5. **Botón principal deshabilitado como validación**: `DialogoDeGuardar.tsx:267`, `auditoria/index.tsx:69-75`,
   `AuditarApuPorHoja.tsx:~312`, `reajuste/index.tsx:511` (aquí tras éxito, aceptable). Guardia: lista blanca de
   `disabled={…}` en primarios solo por `enviando/ocupado`.
6. **Siglas solas como rótulo.** `SKILL.md` dice que `paginas/sinJergaInterna.test.ts` las vigila; **no es cierto**: ese
   archivo solo busca `UC/RF/RNF` y palabras del marco (`:15`, `:60`). Siglas vivas: `Km`, `(R)`, `SPI/CPI`, `PV/EV/AC`
   (`PestanasDeResultados.tsx:102,111,155,169`), `FCAS` (`ParametrosDelPrecio.tsx:11`, `CalculadoraFCAS.tsx:32`),
   `RIF` (`precios_empresa/index.tsx:288`). Guardia nueva: lista de siglas prohibidas en `labelText=`, `titulo:` y
   `<Tab>`.
7. **Trato de usted**: `comun/FranjaDelPaso.tsx:25` «Te falta:», `comun/ayuda/AyudaDeSilice.tsx:16,60` y
   `marco/espacios.ts:215` «Empieza aquí». Guardia: `grep` de formas de tú (`\bTe\b falta|\bEmpieza\b|\bTu\b|\bpuedes\b`)
   en cadenas visibles.
8. **«Fuente» sin ejemplo ni marca de obligatorio** (seis rótulos distintos): `PestanaValuaciones.tsx:270`,
   `PestanaLineaBase` (documento de respaldo), `DialogoDeGuardar` (`logicaGuardar.ts:56-57`), `PestanasDeResultados.tsx:118`,
   `precios_empresa/index.tsx:303`, `reajuste/index.tsx:499`. Guardia: todo campo cuyo rótulo empiece por «Fuente» lleva
   `helperText` con ejemplo y «(opcional)» si no es obligatorio (UX-10).
9. **Error de lectura mostrado como «sin datos»**: `useFichaDeLaObra.ts:12,29-34` → `obras/index.tsx:43`. Guardia:
   ningún `catch` que fije un estado vacío; el estado `error` es explícito (UX-27).
10. **Secciones hermanas armadas distinto**: Control (6 pestañas con fondo), Hoja (7), Mercado (pestañas), Reajuste
    (2 «pasos» como pestañas), Riesgo (fieldsets, sin pestañas), Precios de la empresa (secciones apiladas). La guardia
    de pestañas con fondo existe (`comun/pestanasConFondo.test.ts`); falta una de anatomía común: título, frase,
    franja del paso, bloque.

## 4. Los 10 arreglos de mayor impacto (en orden)

1. **T8 / patrón 1.** `precios_empresa/index.tsx:282-283` y `precios_empresa/logica.ts:14`: `EstadoVacio` con botón a
   cargar la lista base, y que «Actualizar precios» cuelgue también de «Precios y catálogo» (`marco/espacios.ts:131,150`).
   Sin back.
2. **T4.** Puente de registrar a leer: tras guardar la valuación, `FranjaDelPaso` «Ver el avance» hacia Valor ganado y
   reinicio del formulario (`control/PestanaValuaciones.tsx:168-282`, `control/index.tsx:72-119`). Sin back.
3. **T4 / patrón 1.** `EstadoVacio` con botón «Ir a Línea base» / «Ir a Valuaciones» y éxito de la línea base con su paso
   (`control/index.tsx:46-51`, `PestanaValuaciones.tsx:512-514`, `PestanaLineaBase.tsx:125`). Sin back.
4. **T4.** Registrar valuación a ≤ 8 controles: las 5 columnas por línea a 2 más «Más datos de la línea», cabecera con
   número y fecha propuestos (`PestanaValuaciones.tsx:207-264`). **Necesita back** para el número siguiente:
   `aplicacion/control.py` o `api/rutas` de `/v1/control/valuaciones` [I].
5. **T5.** Reajuste: la cláusula en preguntas con sí/no y campos dependientes solo cuando aplican
   (`reajuste/index.tsx:324-384`, ya diseñado en carga-cognitiva §1). Sin back.
6. **T6.** Riesgo: plegar las series por insumo y los parámetros comunes bajo un resumen con recuento; frase de respuesta
   encima del resultado y «siguiente paso» (`riesgo/RiesgoDeLaObra.tsx:251-293`, `ParametrosDelRiesgo.tsx:86-117`,
   `ResultadoDelRiesgo.tsx:52-61`). Sin back.
7. **T3.** Cerrar el ciclo del presupuesto: tras enviar y tras aprobada, un paso siguiente («Entregar el paquete» o
   «Empezar el control»), y sin parpadeo de la franja mientras lee (`hoja/pasoDelPresupuesto.ts:55-58`,
   `hoja/FranjaDelPresupuesto.tsx:86,99-105`). Sin back (las pantallas de Aprobaciones y Control ya existen).
8. **T2.** «Agregar y seguir» en el diálogo y una vista por omisión de la tabla de Partidas con ≤ 6 columnas
   (`hoja/AgregarPartida.tsx:347-354`, `hoja/PestanaPresupuesto.tsx:192-313,394-402`). Sin back.
9. **T3.** Guardar versión: botón principal siempre activo (valida al pulsar) y «Fuente» con ejemplo y marca de
   obligatoria (`hoja/DialogoDeGuardar.tsx:183-196,264-272`, `hoja/logicaGuardar.ts:56-57,90-101`). Sin back.
10. **Patrones 6, 7 y 9.** Tres guardias nuevas en la CI: siglas solas, trato de tú y estado vacío por error; y corregir
    `comun/FranjaDelPaso.tsx:25`, `comun/ayuda/AyudaDeSilice.tsx:16,60`, `marco/espacios.ts:215`,
    `marco/useFichaDeLaObra.ts:12,29-34` + `paginas/obras/index.tsx:43`. Corregir además la línea de `SKILL.md` que
    atribuye a `sinJergaInterna.test.ts` una vigilancia que no existe. Sin back.

## 5. Límites de este inventario

- Todo lo marcado [I] depende del servidor, del CSS o de datos que no se ejecutaron.
- No se auditó Componer (lote 1 hecho), Archivos y planos, Tramos, Mercado, Existencias ni Producción, salvo lo que cruza
  las ocho tareas.
- No se contaron los controles por omisión en `Aprobaciones` (T3 lado de quien dictamina): `aprobar/PanelDictamen.tsx`
  trae dos botones `primary` (`:131`, `:150`, el segundo es la confirmación). Pendiente de revisar si se ven a la vez.
