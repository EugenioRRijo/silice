# Backlog de mejoras de UX: botones, tableros y barras laterales

Rama `feature/ui-aistudio`. Árbol leído: `.worktrees/tanda/frontend-desktop/src`. Todas las rutas son relativas a `frontend-desktop/`.
Dirección aprobada: «Instrumento de auditoría y control». Las animaciones se quedan.

Esto ya se corrige en paralelo y no entra aquí: el enlace «Portada», la cortina sin porcentaje, el color de la empresa y «Carpeta activa» en la barra, las cifras es-VE de la API, el plan en contorno, el foco y el teclado.

Las 7 tandas de revisión dejaron 92 propuestas verificadas. Al unir duplicados quedan 86. La de Índices se parte en dos, una parte sin back y otra con back, así que el total es de **87 tareas**: 17 para hoy, 66 para después y 4 que necesitan back.

**Duplicados unidos** (se hace una sola tarea):

| Tarea única | Venía de | Se queda con |
|---|---|---|
| Filtro del Visor sin severidades en cero ni vacío mudo | presupuesto (Visor, 20 min) + auditoría (ListaHallazgos, 25 min) | `visor/ListaHallazgos.tsx:250`, 25 min |
| «Hallazgo anterior» y «Hallazgo siguiente» | presupuesto (`Visor.tsx:466`, 70 min) + auditoría (`ListaHallazgos.tsx:247`, 60 min) | en el panel de la lista, `ListaHallazgos.tsx:247`. No hay que subir estado al Visor. 60 min |
| Detalle del Historial en panel lateral | revisión-entrega (`PanelLateral`, 60 min) + auditoría (aside fijo, 90 min) | reutilizar `PanelLateral`, como `archivos/RegistroDeImportaciones.tsx:51`. 60 min |
| Franja de resultados del Historial que filtra | revisión-entrega (50 min, retira el Select) + auditoría (45 min) | la de revisión-entrega: franja más pastilla de severidad, sin el Select «Resultado». 50 min |
| La demostración en la primera vez | inicio (vacío de la cartera, 60 min) + inicio (CarpetasDeTrabajo, 20 min) + marco (lateral, 60 min) | un solo frente con un hook común, `useAbrirDemostracion` |

**Piezas comunes que se construyen una vez** (si no, jscpd marcará copias):

- `comun/FiltroDeSeveridad.tsx`: sale de `visor/ListaHallazgos.tsx:248-261`. Lo usan Revisión, Precios de la empresa, el detalle del Historial, Pendientes y la Vista general.
- Un componente de veredicto común («Resultado de Sílice: Cumple» o «No cumple»). Lo usan el Visor y Auditar APU por hoja.
- `comun/EnlaceComoBoton.tsx`: un `Button` de Carbon con `as={Link}`. Hoy no hay ningún `as={Link}` en `src`. Se crea en el lote C de hoy.
- `textoDeHallazgos`: se mueve de `entregar/logica.ts:20` a `comun/`. `comun/arquitectura.test.ts` prohíbe importar entre páginas.

---

## 1. Para hoy: rápidas que no necesitan back

Son las 17 tareas de 15 minutos o menos. Van ordenadas por impacto y, con el mismo impacto, por esfuerzo.

| # | Tarea | Archivo:línea | Texto exacto | Impacto | Min | Riesgo | Lote |
|---|---|---|---|---|---|---|---|
| 1 | Ordenar los hallazgos de APU por hoja por severidad: Crítico, Error, Advertencia, Información. Orden estable con `SEVERIDADES.indexOf(normalizarSeveridad(...))` | `paginas/auditoria/AuditarApuPorHoja.tsx:351` | (sin texto) | alto | 10 | bajo | A |
| 2 | Tablero sin control de obra: botón secundario hacia `rutaOPendientes('control', obraAbierta)` | `paginas/tablero/index.tsx:148` | «Abrir el control de obra» | alto | 10 | bajo | C |
| 3 | Mostrar la acción del hallazgo elegido, con el texto que manda el servidor (`accion`, `api/tipos.ts:147`) | `visor/ListaHallazgos.tsx:80` | «Acción: {accion}» | alto | 15 | bajo | A |
| 4 | Poner la propuesta de Sílice en «Su precio» con un clic. El botón solo rellena el campo y no guarda | `paginas/mercado/UsarPrecio.tsx:185` | «Poner la propuesta en «Su precio»» | alto | 15 | bajo | F |
| 5 | El vacío de la cartera lleva un botón principal y no terciario. Se cambia `textos.ts:34` y la frase de DESIGN.md §Vista general | `paginas/inicio/CarteraYAvance.tsx:107` | «Crear la primera obra» | medio | 10 | bajo | D |
| 6 | Estado vacío de Aprobar sin punto final, con descripción y enlace. La ruta se toma de `RUTA_DE_PENDIENTES` y no se escribe a mano | `paginas/aprobar/index.tsx:127` | Título «No hay versiones esperando dictamen». Enlaces «Ver los pendientes» y «Abrirlos en Pendientes» | medio | 10 | bajo | B |
| 7 | Historial vacío: el enlace pasa a botón principal. Con datos, botón terciario pequeño junto al h1. Navega con `useNavegarSeguro` | `paginas/historial/index.tsx:62` (y `:45`) | «Auditar un libro» | medio | 10 | bajo | B |
| 8 | «Sin resultados» del buscador dice qué probar. Se mantiene un solo `role=status` | `marco/Buscador.tsx:122` | «No hay obras ni pantallas con «{texto}». Pruebe con una palabra del nombre de la obra o de la pantalla» | medio | 15 | bajo; avisar a quien corrige el teclado | E |
| 9 | Nueva obra: si el nombre está vacío, se avisa antes de enviar y el foco va al campo. Sigue el patrón de `faltaMoneda` | `shell/obras/DialogoNuevaObra.tsx:86` (botón en `:127`) | «Escriba el nombre de la obra». Botón «Crear la obra» y, mientras trabaja, «Creando la obra…» | medio | 15 | bajo | D |
| 10 | Catálogo: el tipo y el dominio se leen en palabras. `TIPOS_DE_INSUMO` se exporta a `comun/tiposDeInsumo.ts` y `coincide()` busca también por el texto que se muestra | `paginas/catalogo/index.tsx:59` (y `:53`) | «Material», «Equipo», «Mano de obra», «Civil», «Telecomunicaciones», «Industrial», «Sistemas» | medio | 15 | bajo | F |
| 11 | Entregar: dentro del aviso de versión no aprobada, un botón que la elige. Después el foco va al selector «Versión» | `paginas/entregar/index.tsx:172` | «Usar la versión aprobada {versión}» | medio | 15 | bajo | B |
| 12 | Riesgo sin versiones: botón principal al presupuesto. La constante va en Riesgo para no tocar `hoja/logica.ts:10` | `paginas/riesgo/RiesgoDeLaObra.tsx:219` | Botón «Ir al presupuesto». Descripción «Esta obra aún no tiene versiones guardadas. Guarde una en el presupuesto para proyectar su riesgo» | medio | 15 | bajo | C |
| 13 | Valor ganado: se ocultan «En la otra moneda» y «Nota» cuando están vacías en todas las filas. La nota al pie debe decir el motivo verdadero; si la API manda uno, se usa ese | `paginas/control/PestanasDeResultados.tsx:144` | «Sin tasa del BCV para el corte: no se muestran los montos en la otra moneda» | medio | 15 | bajo | C |
| 14 | Tablero: el gráfico «Total por versión» solo sale con 2 versiones o más | `paginas/tablero/index.tsx:222` | (sin texto) | bajo | 10 | nulo | C |
| 15 | Marca «Demostración»: botón terciario a la Ayuda que cierra el panel | `shell/MarcaDemostracion.tsx:44` | «Ver los recorridos guiados» | bajo | 15 | bajo | E |
| 16 | Bienvenida: se quita «en la consola donde ejecutó npm run dev», pero antes hay que confirmar en `api/main.py:100` que el back no escribe ahí. La ruta `data/codigo_instalacion.txt` se queda | `bienvenida/Bienvenida.tsx:52` | (se quita una cláusula) | bajo | 15 | bajo | D |
| 17 | Inicio de auditoría: los dos botones están siempre a la vista, con `disabled={!archivo}`. No cambian ni el orden ni la jerarquía | `paginas/auditoria/index.tsx:65` | «Auditar con recorrido guiado» y «Auditar por mi cuenta» | bajo | 15 | bajo | A |

### Lotes para constructores en paralelo

Ningún archivo aparece en dos lotes, y eso vale también para las pruebas. Cada lote corre `npm run lint` y `npx vitest run` sobre sus pruebas. La suite completa se corre una vez, al unir los seis lotes.

| Lote | Tareas | Archivos que toca (solo este lote) | Min |
|---|---|---|---|
| **A. Auditoría de libros** | 1, 3, 17 | `visor/ListaHallazgos.tsx`, `paginas/auditoria/AuditarApuPorHoja.tsx` (más la columna «Acción» en `COLUMNAS_HALLAZGOS:149`, solo si el tipo trae `accion`), `paginas/auditoria/index.tsx`; pruebas `ListaHallazgos.test.tsx`, `AuditarApuPorHoja.test.tsx`, `Auditoria.test.tsx` | 40 |
| **B. Revisión y entrega** | 6, 7, 11 | `paginas/aprobar/index.tsx`, `paginas/entregar/index.tsx`, `paginas/historial/index.tsx`; sus pruebas | 35 |
| **C. Control y riesgo** | 2, 12, 13, 14 | `comun/EnlaceComoBoton.tsx` (nuevo; se crea primero, lo usan la 2 y la 12), `paginas/tablero/index.tsx`, `paginas/riesgo/RiesgoDeLaObra.tsx`, `paginas/control/PestanasDeResultados.tsx`; sus pruebas | 50 |
| **D. Inicio y primera vez** | 5, 9, 16 | `paginas/inicio/CarteraYAvance.tsx`, `paginas/inicio/textos.ts`, `shell/obras/DialogoNuevaObra.tsx`, `bienvenida/Bienvenida.tsx`, `DESIGN.md` (solo la frase del vacío); `VistaGeneral.test.tsx`, `NuevaObra.test.tsx`, `Bienvenida.test.tsx` | 40 |
| **E. Marco** | 8, 15 | `marco/Buscador.tsx`, `shell/MarcaDemostracion.tsx`; sus pruebas. Antes de abrir `Buscador.tsx`, avisar a quien corrige el foco y el teclado | 30 |
| **F. Precios** | 4, 10 | `paginas/mercado/UsarPrecio.tsx`, `paginas/catalogo/index.tsx`, `comun/tiposDeInsumo.ts` (nuevo), `paginas/precios_empresa/logica.ts` (solo se exporta `TIPOS_DE_INSUMO`); sus pruebas | 30 |

---

## 2. Siguiente: tareas medias y largas sin back

Van agrupadas por frente. Cada frente lo lleva un solo constructor, porque sus tareas comparten archivos. Dentro de cada frente, primero va lo de mayor impacto.

### S1. Presupuesto: Partidas, APU y Revisión
Archivos: `paginas/hoja/*`, `comun/InformeAuditoria.tsx`

| Tarea | Archivo:línea | Texto | Imp. | Min | Riesgo / dependencia |
|---|---|---|---|---|---|
| La tabla de Partidas cabe a 1440 px. La columna de estado baja a 14rem y 2 líneas; «Quitar» pasa a IconButton con TrashCan | `paginas/hoja/hoja.scss:189`, `PestanaPresupuesto.tsx:290` | «Quitar la partida» | alto | 60 | bajo; medir a 1056, 1366 y 1440 px. **Hacerla primero**: el panel fijo de Aprobar depende de ella |
| Contador de hallazgos en la pestaña «Revisión», con `Pildora` y texto oculto | `paginas/hoja/index.tsx:282` | «, {n} hallazgos por atender» | alto | 20 | bajo; coordinar con el foco de las pestañas |
| «Ver el APU» en cada hallazgo, solo para partidas con precio | `paginas/hoja/PestanaAuditoria.tsx:45` | «Ver el APU de {código}» | alto | 60 | medio; sin el dato del precio no se pinta |
| «Partida anterior», «Partida siguiente» y «2 de 3» en el panel del APU | `paginas/hoja/PanelDeApu.tsx:29` | «Partida anterior», «Partida siguiente» | alto | 75 | medio; depende del foco que se corrige en paralelo |
| Filtros por severidad y por regla en Revisión, con `FiltroDeSeveridad` común | `comun/InformeAuditoria.tsx:42` | «Quitar los filtros»; vacío «Ningún hallazgo tiene los filtros elegidos» | alto | 80 | medio; necesita antes la pieza común (S4) |
| Veredicto con la versión y no con «Presupuesto HOJA» | `comun/InformeAuditoria.tsx:36` | «Versión {v} · Hallazgos: {n} · Resultado: {r}» o «Borrador sin guardar» | medio | 20 | bajo |
| El código de la partida se ve como enlace, con ícono y subrayado. Se hace junto con el ancho de la tabla | `paginas/hoja/PestanaPresupuesto.tsx:198` | ayuda «Abrir el APU» | medio | 20 | bajo |
| Estado vacío de Partidas con otras formas de empezar | `paginas/hoja/PestanaPresupuesto.tsx:437` | «Cargar un cómputo o un plano», «Importar los tramos de la vía» | medio | 40 | bajo |

### S2. Resumen de la obra, Tramos y Componer
Archivos: `paginas/obras/index.tsx`, `paginas/vial/Tramos.tsx`, `paginas/componer/TablaInsumos.tsx`

| Tarea | Archivo:línea | Texto | Imp. | Min | Riesgo |
|---|---|---|---|---|---|
| Cada cifra del Resumen lleva a su sección y se quita «Etapa» | `paginas/obras/index.tsx:64` | «Abrir el presupuesto», «Ver el control de obra», «Ver las versiones»; «Sin datos de avance» | alto | 55 | bajo |
| «Llevar al presupuesto» dentro de `FranjaDelPaso` | `paginas/vial/Tramos.tsx:154` | «Llevar al presupuesto» | medio | 35 | bajo |
| En Componer, «Quitar» y «Agregar línea», como en la Hoja | `paginas/componer/TablaInsumos.tsx:499` | «Quitar la fila {n} de {grupo}», «Agregar una línea a {grupo}» | bajo | 20 | bajo |

### S3. Inicio, Vista general y primera vez
Archivos: `paginas/inicio/*`, `paginas/administracion/CarpetasDeTrabajo.tsx`, `shell/carpetas/GestionCarpetas.tsx`, `marco/BarraLateral.tsx` (solo el vacío), `comun/ayuda/empiezaAqui.ts`

| Tarea | Archivo:línea | Texto | Imp. | Min | Riesgo |
|---|---|---|---|---|---|
| **Frente demostración** (unido). (a) Hook `useAbrirDemostracion` sacado de `GestionCarpetas.tsx:520`. (b) Botón en el vacío de la cartera. (c) `CarpetasDeTrabajo` pasa `alAbierta` y lleva a la Vista general. (d) Vacío del lateral con botón terciario y `?agregar=demostracion` | `CarteraYAvance.tsx:99`, `CarpetasDeTrabajo.tsx:20`, `BarraLateral.tsx:120` | «Abrir la demostración»; «Preparando la demostración…»; aviso «La demostración está abierta» | alto | 140 | bajo; el back ya existe |
| Atajo para retomar la obra, con `rutaDeObra(...)` y no con `rutaOPendientes("obras")` | `paginas/inicio/index.tsx:86` | «Seguir con {obra}» | alto | 35 | bajo |
| «Lo que requiere atención» va antes que los lanzadores, y estos llevan verbos propios | `paginas/inicio/index.tsx:90` | «Auditar un libro», «Abrir precios y catálogo», «Abrir costos de producción» | medio | 30 | bajo |
| Filtros por severidad en «Lo que requiere atención», con `FiltroDeSeveridad` | `paginas/inicio/LoQueBloquea.tsx:66` | «Todos {n}», «Bloquean {n}», «Avisos {n}»; «Ver todos» | medio | 50 | bajo; necesita S4 |
| Filtros por etapa en la cartera, con las atrasadas primero | `paginas/inicio/CarteraYAvance.tsx:227` | «Todas {n}», «Atrasadas {n}»; «Ver todas las obras» | medio | 60 | bajo |
| Últimas auditorías: el botón va dentro del vacío | `paginas/inicio/UltimasAuditorias.tsx:53` | «Auditar un libro», «Auditar otro libro» | medio | 20 | bajo |
| Últimas auditorías abren su detalle con `?auditoria=`. El Historial lee el parámetro. Se hace con S6 | `paginas/inicio/UltimasAuditorias.tsx:77`, `historial/index.tsx:40` | «Ver todo el historial» | medio | 40 | bajo |
| «Empieza aquí» más corto y con un enlace que crea la obra | `comun/ayuda/empiezaAqui.ts:20` | «Crear la obra ahora» | medio | 40 | bajo |

### S4. Visor y auditoría de libros
Archivos: `visor/*`, `paginas/auditoria/*`, `comun/FiltroDeSeveridad.tsx` y el veredicto común (los dos nuevos)

| Tarea | Archivo:línea | Texto | Imp. | Min | Riesgo |
|---|---|---|---|---|---|
| **Primero**: extraer `comun/FiltroDeSeveridad.tsx` de `ListaHallazgos.tsx:248-261` y unirle el arreglo de los ceros: deshabilitado si está en 0 y no está elegido, «Hallazgos: {n} de {total}» y la salida del filtro | `visor/ListaHallazgos.tsx:250` | «Ver todos»; «Ningún hallazgo tiene las severidades elegidas» | medio | 25 + 30 | medio; revisar que el cero tenga contraste de 4,5:1 o más |
| Veredicto del libro antes de los totales, con un componente común | `visor/Visor.tsx:342` | «Resultado de Sílice: Cumple» o «No cumple»; «Ver en el historial» | alto | 35 | bajo |
| Resultado y conteo por severidad en APU por hoja, con el mismo componente | `paginas/auditoria/AuditarApuPorHoja.tsx:360` | «1 error», «3 advertencias»… | alto | 30 | bajo |
| «Hallazgo anterior», «Hallazgo siguiente» y «2 de 5» (unido) | `visor/ListaHallazgos.tsx:247` | «Hallazgo anterior», «Hallazgo siguiente» | alto | 60 | medio; sin atajos de teclado propios |
| Llevar el foco al resultado cuando termina la auditoría de APU | `paginas/auditoria/AuditarApuPorHoja.tsx:326` | (sin texto) | medio | 20 | bajo |
| «Descargar PDF» junto a «Cambiar libro», con la explicación más corta | `visor/Visor.tsx:357` | «Informe para quien hizo el libro: totales y cada hallazgo con su celda. No guarda nada.» | medio | 40 | medio; la cabecera tiene poco ancho |

### S5. Aprobar, Revisar, Entregar y Pendientes
Archivos: `paginas/aprobar/*`, `paginas/revisar/*`, `paginas/entregar/*`, `paginas/pendientes/*`

| Tarea | Archivo:línea | Texto | Imp. | Min | Riesgo |
|---|---|---|---|---|---|
| El botón del dictamen dice la decisión; el título del diálogo y las notas siguen el mismo verbo | `paginas/aprobar/PanelDictamen.tsx:132` | «Aprobar la versión…», «Aprobar con observaciones…», «Devolver la versión…»; «Notas (obligatorias)» | alto | 20 | bajo |
| Revisar: el dictamen llega sin opción elegida y las opciones van con mayúscula | `paginas/revisar/Paquete.tsx:307` | «Su dictamen», «Elija un dictamen», «Guardar el dictamen» | alto | 20 | bajo |
| Entregar: el botón dice si el paquete sale firmado y explica el bloqueo | `paginas/entregar/index.tsx:352` | «Generar el paquete firmado», «Generar el paquete sin firma» | alto | 20 | bajo |
| Hallazgos en la cabecera del envío. Antes se mueve `textoDeHallazgos` a `comun/` | `paginas/aprobar/index.tsx:225` | «Ver los hallazgos» | alto | 30 | bajo |
| Siguiente paso tras el dictamen, con `FranjaDelPaso`. El enlace de `EntregaDeLaObra` pasa a secundario | `paginas/aprobar/index.tsx:196` | «Entregar el paquete al cliente», «Volver a Pendientes» | alto | 35 | bajo-medio |
| Panel del dictamen fijo a la derecha desde 82 rem | `paginas/aprobar/index.tsx:193` | (sin texto) | alto | 120 | medio; **va después** de la tabla de Partidas a 1440 px (S1) |
| Paquete listo: la descarga pasa a principal y la huella se copia | `paginas/entregar/index.tsx:368` | «Copiar la huella», «Huella copiada» | medio | 25 | bajo-medio |
| Pendientes: el resumen se vuelve filtro, con `FiltroDeSeveridad` o el mismo patrón | `paginas/pendientes/Bandeja.tsx:118` | «Todos ({n})», «Bloquean ({n})», «Avisos ({n})» | medio | 35 | bajo-medio; no romper el listbox |
| Resumen del paquete con saltos a cada bloque (los h2 llevan `tabIndex={-1}`) | `paginas/revisar/Paquete.tsx:120` | «Ver los hallazgos», «Ver los cambios», «Ir al dictamen» | medio | 60 | bajo |

### S6. Historial
Archivos: `paginas/historial/*`

| Tarea | Archivo:línea | Texto | Imp. | Min | Riesgo |
|---|---|---|---|---|---|
| El detalle se abre en `PanelLateral` (unido) y al cerrar el foco vuelve a la fila | `paginas/historial/index.tsx:123` | «Detalle de la auditoría», «Viendo el detalle» | alto | 60 | medio |
| Franja por resultado que filtra, más pastilla de severidad; se retira el Select (unido) | `paginas/historial/index.tsx:118` | «Todas ({n})», «Con errores ({n})», «Solo advertencias ({n})», «Sin errores ni advertencias ({n})» | medio | 50 | bajo |
| Filtro por severidad en los hallazgos guardados, con `FiltroDeSeveridad` | `paginas/historial/Detalle.tsx:127` | «Todos ({n})», «Error ({n})»… | medio | 35 | bajo; necesita S4 |

### S7. Precios: actualización, empresa, mercado, existencias e índices
Archivos: `paginas/actualizacion/*`, `paginas/precios_empresa/*`, `paginas/mercado/*`, `paginas/existencias/*`, `paginas/catalogo/*`, `paginas/indices/*`

| Tarea | Archivo:línea | Texto | Imp. | Min | Riesgo |
|---|---|---|---|---|---|
| El presupuesto base llega elegido con la obra abierta, y el Select agrupa «Esta obra» y «Otras obras» | `paginas/actualizacion/index.tsx:69` | «Esta obra», «Otras obras» | alto | 20 | bajo |
| Abrir la versión revalorada en el Presupuesto, con `?version=` | `paginas/actualizacion/index.tsx:423` | «Abrir la versión {v} en el Presupuesto» | alto | 25 | bajo |
| Estados vacíos de Precios de la empresa que llevan al paso que falta | `paginas/precios_empresa/index.tsx:282`, `logica.ts:13` | «Cargar la referencia MaPreX en Bs» | alto | 30 | bajo |
| El resultado de la revaloración dice cuánto sube y dónde | `paginas/actualizacion/index.tsx:357` | «Solo las partidas que cambiaron ({n})» | alto | 50 | medio |
| «Queda poco» y «Existencia negativa» filtran y llevan a registrar | `paginas/existencias/PestanaExistencias.tsx:159` | «Registrar entrada», «Registrar conteo», «Ver todos los materiales» | alto | 90 | medio |
| «Revalorar presupuesto» dice qué falta en vez de quedar gris | `paginas/actualizacion/index.tsx:291` | «Falta la lista de precios» | medio | 20 | bajo |
| La búsqueda del catálogo sin resultados ofrece borrar la búsqueda | `paginas/catalogo/index.tsx:95` | «Borrar la búsqueda» | medio | 20 | bajo |
| Índices con un solo botón principal y verbos completos; las cuentas pasan por `formatoEsVe` | `paginas/indices/index.tsx:198`, `SeriesViales.tsx:243` | «Leer el archivo», «Importar la serie» | medio | 20 | bajo |
| Pestaña «Pesajes sospechosos ({n})». Se quitan los enlaces repetidos solo si el lateral los ofrece | `paginas/existencias/index.tsx:88` | «Pesajes sospechosos ({n})» | medio | 30 | bajo; toca `EnlacesDeCostos` (coordinar con S8) |
| Días del estudio con atajos | `paginas/mercado/EstudioDelLado.tsx:151` | «30 días», «90 días», «180 días», «1 año», «Otro número de días» | medio | 35 | bajo |
| Filtro por severidad en R11 y R12, con `FiltroDeSeveridad` | `paginas/precios_empresa/index.tsx:473` | «Mostrar todas las severidades» | medio | 45 (ya sin la extracción) | medio; necesita S4 |
| Índices: un índice «En esta página», que es la parte sin back | `paginas/indices/index.tsx:145` | «En esta página» | medio | 25 | bajo |
| Franja del mercado: dónde caen su precio y su costo | `paginas/mercado/Cifras.tsx:47` | «Su costo (piso)» | medio | 120 | medio |

### S8. Control, Riesgo, Tablero, Escenarios, Reajuste y Producción
Archivos: `paginas/control/*`, `paginas/riesgo/*`, `paginas/tablero/*`, `paginas/escenarios/*`, `paginas/reajuste/*`, `paginas/produccion/*`, `comun/EnlacesDeCostos.tsx`

| Tarea | Archivo:línea | Texto | Imp. | Min | Riesgo |
|---|---|---|---|---|---|
| Los estados vacíos de Control llevan a la pestaña que los resuelve | `paginas/control/index.tsx:47`, `PestanaValuaciones.tsx:513` | «Declarar la línea base», «Registrar una valuación» | alto | 25 | bajo; coordinar con el foco |
| Riesgo avisa antes de proyectar sin series y lleva a elegirlas | `paginas/riesgo/RiesgoDeLaObra.tsx:259` | «Elegir las series» | alto | 40 | bajo |
| Riesgo: la reserva para el P80 como cifra de pantalla | `paginas/riesgo/ResultadoDelRiesgo.tsx:52` | «Reserva para cubrir el P80» | medio | 20 | bajo |
| Escenarios: estado vacío que enseña | `paginas/escenarios/index.tsx:382` | «Aún no hay escenarios que comparar» | medio | 20 | bajo |
| Control recuerda la última pestaña de cada obra (localStorage con try/catch) | `paginas/control/index.tsx:74` | (sin texto) | medio | 25 | bajo |
| Tablero: un enlace por bloque a la pantalla que lo explica | `paginas/tablero/index.tsx:124` | «Ver en Control de obra», «Ver el presupuesto», «Ver las versiones» | medio | 30 | bajo |
| Reajuste: volver al paso anterior, verbo concreto y vacío con salida | `paginas/reajuste/index.tsx:443` | «Anterior: la cláusula», «Calcular el reajuste», «Ir al presupuesto», «Estudio guardado» | medio | 35 | bajo-medio |
| Producción: grupo de acciones bajo «Qué quiere hacer» | `paginas/produccion/index.tsx:29` | «Producir mezcla», «Ver la receta de la planta», «Registrar los costos del período», «Calcular el costo por tonelada» | medio | 35 | bajo; misma persona que Pesajes (S7) |

### S9. Marco: buscador, barra lateral y ayuda
Archivos: `marco/*`, `paginas/.../EspacioDeCuenta.tsx`

| Tarea | Archivo:línea | Texto | Imp. | Min | Riesgo |
|---|---|---|---|---|---|
| Buscador vacío con el grupo «Acciones» (cambia `busqueda.test.ts`) | `marco/busqueda.ts:47` | «Nueva obra», «Ver los pendientes» | alto | 120 | medio |
| Botón de buscar en el riel plegado; revisar el selector de `aria-keyshortcuts` de `Buscador.tsx:19` | `marco/BarraLateral.tsx:171` | «Buscar una obra» | medio | 25 | bajo |
| Pistas de teclado al pie del buscador | `marco/Buscador.tsx:144` | «↑ ↓ Elegir», «Intro Abrir», «Esc Cerrar» | medio | 20 | bajo |
| «Volver a la obra» vuelve de verdad a la obra | `marco/BarraSuperior.tsx:72` | «Volver a la obra», «Volver a la Vista general» | medio | 30 | bajo |
| Los avisos del marco quedan fijos a la vista | `marco/marco.scss:82` | (sin texto) | medio | 30 | bajo; probar a 1366 y 1440 px |
| Sección «Atajos de teclado» en Ayuda. Ctrl+B se anuncia solo si su manejador existe | `marco/EspacioDeCuenta.tsx:101` | «Atajos de teclado» | medio | 45 | bajo |
| Obras recientes primero en el buscador | `marco/busqueda.ts:47` | «Abierta hace poco · {carpeta}» | medio | 60 | bajo |
| Filtro de obras en el lateral cuando hay más de 8 | `marco/BarraLateral.tsx:214` | «Filtrar obras», «Limpiar el filtro» | bajo | 60 | bajo |

---

## 3. Necesita back

| Tarea | Pantalla | Qué falta en el back | Imp. | Min |
|---|---|---|---|---|
| «Obras que se desvían del plan»: barras animadas, real relleno, plan en contorno y diferencia con su palabra. Se retira el anillo «Distribución por estado» | `paginas/inicio/CarteraYAvance.tsx:199` | `desviacion_avance` y `desviacion_texto` en `ObraDeLaCartera`, GET `/v1/obras/resumen/todas` (`api/rutas/obras.py`). Hoy el navegador calcula las barras | alto | 180 |
| Historial: tabla Libro, Sílice y Diferencia en el detalle | `paginas/historial/Detalle.tsx:67` | `diferencia_total` y `diferencia_texto` en GET `/v1/auditorias-libro/{id}` | medio | 45 |
| Índices: tabla «Índices guardados» con «Último mes cargado» y «Descargado el». El aviso «Desactualizado» espera el umbral que fije Eugenio | `paginas/indices/index.tsx:145` | Las dos columnas en GET `/v1/reajuste/series` | medio | 50 |
| «Descargar PDF» en Auditar APU por hoja | `paginas/auditoria/AuditarApuPorHoja.tsx:385` | La ruta `/v1/libros/apu-por-hoja/pdf`. Hoy solo hay POST en `api/rutas/libros.py:873` y `:905` | medio | 150 |

---

## 4. Diagnóstico por grupo

- **Marco global.** La demostración no se ofrece la primera vez, el buscador sirve para ir pero no para hacer, y con la barra plegada no se puede cambiar de obra. Los atajos y los avisos tampoco se ven: falta la tabla de atajos y un aviso puede quedar fuera de la vista en un lienzo desplazado.
- **Inicio y obras.** La Vista general no lleva a un primer resultado rápido: el vacío tiene un solo botón terciario y la demostración queda a cuatro clics, sin salida después. Con datos, el orden contradice DESIGN.md y los pendientes no se filtran por severidad.
- **Presupuesto.** La información está, pero cuesta encontrarla: Revisión no dice cuántos hallazgos tiene, no los filtra y sus filas no llevan a la partida. La tabla de Partidas desborda a 1440 px, el APU solo se recorre cerrando el panel y el Resumen no lleva a ninguna parte.
- **Precios.** Las pantallas de precios no dicen cuál es el siguiente paso: la revaloración termina sin salida y los vacíos mandan a pantallas con otro permiso. Tampoco ordenan sus resultados: cinco cifras del mismo tamaño y resúmenes que cuentan pero no dejan actuar.
- **Revisión y entrega.** Cuesta saber qué decidir y qué viene después: los botones del dictamen no dicen la decisión, Revisar llega con «conforme» ya marcado y nada lleva a Entregar. Los hallazgos y los motivos de bloqueo están lejos del botón que dependen de ellos.
- **Auditoría.** El veredicto `cumple` y el conteo `por_severidad` llegan de la API y no se pintan, y los hallazgos de APU por hoja salen sin priorizar el Error. En el Visor faltan la acción del hallazgo y el paso de uno a otro, y el Historial no abre un detalle desde fuera.
- **Control y riesgo.** Los estados vacíos de Control, Tablero, Reajuste y Riesgo dicen adónde ir pero no tienen un botón que lleve allí, y Control siempre abre en «Línea base». Riesgo avisa de la proyección plana en USD solo después de proyectar.

### Descartadas en la verificación (no se construyen)
- Una fila «Pendientes» propia y «Nueva obra» como botón secundario: contradicen DESIGN.md:134 y :101. Podrían volver si Eugenio enmienda DESIGN.md.
- Quitar el gráfico animado de la cartera y mover la píldora del lateral: las animaciones se quedan, y la píldora la fija DESIGN.md.
- «Descargar Excel» y «Descargar PDF» como ghost, y quitar los ceros de Observado y Esperado.
- Un acuse al cambiar la fecha: la fase «cargando» ya muestra la franja de esqueleto.
- Cambiar la acción principal del inicio de auditoría.
- «Proponer series» en Riesgo: el back no tiene esa función.
- Cuatro tarjetas KPI en Valor ganado: van contra DESIGN.md:4.
- Atajos anidados en la barra lateral: rompen las tres zonas.
