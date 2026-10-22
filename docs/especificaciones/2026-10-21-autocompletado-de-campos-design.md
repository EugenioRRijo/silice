# Autocompletado guiado de campos en la interfaz nueva: diseño del componente `CampoConBusqueda` y su contrato

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-adm-empresa` (base `4ad4c576`) · **Estado:** PROPUESTO. Lo juzga el árbitro
(`docs/planes/MANUAL_ARBITRO.md`, criterios B3, B4, C1, D1 y D2 aplicados al diseño). Sin su aprobación no hay código. Las
decisiones que no son de ingeniería están en §11 (D-1 a D-12) con la recomendación más conservadora y reversible.

**Origen (Eugenio, 2026-10-21, probando la interfaz React; no es experto en APU):** «la opción de código al componer un APU es
ambigua porque como usuario no sé qué poner; sería bueno que se especificara colocando un autocompletado para los campos que
necesiten una información relevante, como el de la hoja MaPreX».

**Alcance de este documento:** solo diseño. No se escribió código de producción ni se tocó ninguna prueba. **Qué cubre:** un
componente reutilizable de búsqueda con autocompletado, el contrato de API que necesita, su encaje en Componer, Hoja y Catálogo,
y un barrido de todos los campos del front que piden un dato que la persona no tiene por qué saber de memoria. **Qué no:** crear
insumos o partidas en el catálogo desde el combobox, ampliar la referencia MaPreX, ni tocar `core/`.

**Qué leí (enteros salvo indicación):** `docs/planes/MANUAL_SUBAGENTES_MIGRACION.md`, `MANUAL_ARBITRO.md`,
`frontend-desktop/DESIGN.md`, `PRODUCT.md` (en lo que toca), el modelo `docs/especificaciones/2026-10-19-hoja-react-design.md` (forma y
hallazgos §1.3), `docs/ERS.md` UC-10, UC-11, UC-17 y RF-68; en el front `src/paginas/componer/*` (todos los fuentes),
`catalogo/*`, `hoja/OperacionesDePrecios.tsx`, `CambioDeInsumo.tsx`, `ConvertirMoneda.tsx`, `PestanaApu.tsx`, `logicaVersiones.ts`,
`logicaApu.ts`, `precios_empresa/index.tsx`, `elaborar/index.tsx`, `actualizacion/index.tsx`, `historico/index.tsx`,
`escenarios/index.tsx`, `simulador/index.tsx`, `control/PestanaValuaciones.tsx`, `existencias/PestanaRegistrar.tsx`,
`similares/index.tsx`, `src/comun/CampoTexto.tsx`, `useSinRegionVacia.ts`, `regionesVivasVacias.test.tsx`, `src/api/cliente.ts`,
`src/indicadores/formatoEsVe.ts`; en el servidor `api/rutas/catalogo.py`, `composicion.py`, `precios_empresa.py` (cabecera),
`hoja.py` (E7 y E8), `api/acceso.py`, `api/sin_eco.py`, `api/sin_cache.py`, `aplicacion/composicion.py` (todo lo de MaPreX y el
guardado), `core/catalog/repositorio.py` (`partidas`, `insumos`, `lista_vigente`, `cargar_composicion`, `_codigo_nuevo`),
`core/models/entidades.py` (`ListaPrecios`), `core/contracts/unidades.py`; y los datos `data/precios/maprex_2026-07/` (README y los
cuatro `referencia_*.csv`). **No leí** `api/rutas/control.py` más allá de las rutas de línea base y valuaciones, ni el cuerpo de
`aplicacion/hoja*.py` salvo `candidatos_de_insumo`; lo que de ellos se afirma está marcado.

**Convención de referencias:** `archivo:línea` es del commit `4ad4c576` (rutas relativas a `frontend-desktop/src/paginas/` salvo
que diga otra cosa).

---

## 0. Resumen en doce líneas

1. El «código» que la persona no sabe qué poner es el **código de la partida** (`componer/index.tsx:202-208`). Los insumos **no
   tienen código que escribir**: el catálogo se lo asigna solo (`core/catalog/repositorio.py:455`, `PREFIJO-NNN`) y se identifican
   por (tipo, descripción, unidad). El problema es de **vocabulario**, no de un campo: nada dice qué es un código, de dónde
   sale ni cuándo conviene uno existente.
2. Hay además una **trampa real** que el autocompletado resuelve: si se teclea el código de una partida que ya existe con otra
   descripción o unidad, el guardado se rechaza (`aplicacion/composicion.py:390-436`) y la precarga no trae la cabecera
   (`PrecargaRespuesta` solo tiene tablas y rendimiento, `api/rutas/composicion.py:133-137`). Elegir la partida de una lista
   debe **rellenar descripción, unidad y dominio**.
3. Ya existe un buscador MaPreX en Componer (`BuscadorReferencia.tsx`, uno por tabla). Funciona, pero busca la **frase completa
   como subcadena** (`tuberia` no halla «TUBO PVC…»), no ordena por relevancia, no limita, no busca por código y entrega la
   fila **sin su procedencia ni su fecha** (se pierden al pulsar «Usar esta fila»). El componente nuevo lo **sustituye**.
4. La referencia MaPreX estructurada son **111 filas** (110 referencias únicas; 43 son el tabulador CIV), no las ≈16 000 de los PDF;
   el README (regla 2) prohíbe el volcado completo. Un autocompletado sobre 111 filas fallará seguido: el estado «no lo
   encuentra» no es un adorno, es parte central del diseño (§3.5) y ampliar la referencia es una decisión de Eugenio (D-2).
5. No existe búsqueda con `q` en `GET /partidas` ni `GET /insumos`: ambos devuelven **todo** y el Catálogo filtra en el navegador
   (`catalogo/index.tsx:43-58`, `filtro.ts`). Hace falta un contrato nuevo de búsqueda (§5): `GET /v1/buscar/partidas`,
   `/v1/buscar/insumos`, `/v1/buscar/proveedores` y `/v1/buscar/codigo-sugerido`, con límite, orden por relevancia, `no-store` y sin eco.
6. **Tres fuentes que nunca se mezclan en una misma fila ni se rotulan igual:** «Catálogo de este caso» (insumos y partidas ya
   guardados, con el precio de la lista vigente), «MaPreX jul-2026» (referencia de mercado, solo lectura, fechada) y, en la Hoja,
   «Lista de precios de esta versión». Cada resultado lleva su fuente, su fecha y su moneda a la vista. La lista de precios de la
   empresa (UC-17) **no** se ofrece a quien arma en v1 (D-1).
7. Un solo componente, `CampoConBusqueda`, sobre el `ComboBox` de Carbon 1.117.0 (**condicionado a una prueba de viabilidad F0**
   que no pude correr aquí: si falla, se construye sobre `CampoTexto` con el patrón ARIA 1.2, §4.7).
8. Montos **siempre como texto**: el precio se muestra con `formatoEsVe` (sin `Number`, `parseFloat` ni `toFixed`), el texto de la
   API se pinta como texto de React (nunca HTML), y el `fila` que rellena la tabla lo arma el servidor (como hoy).
9. Texto de ayuda en lenguaje llano en **cada** campo de §2, con ejemplo ficticio. Ninguna ayuda dice «UC-10», «ref_maprex» ni «R3».
10. Se escribe lo que se pide, no lo que el sistema supone: un código o un insumo que no existe **no se bloquea ni se rechaza
    en silencio**; se ofrece como opción explícita de la lista («Crear una partida nueva con el código …»), recomendación D-3 y D-4.
11. Diez sub-rebanadas (§9): backend B1-B4 y front F0-F5 en paralelo tras fijar el contrato; Componer primero (F2), luego Hoja (F3) y Catálogo y
    resto (F4, F5).
12. Pruebas por capa con oráculos escritos a mano desde los CSV de MaPreX (códigos reales `PLOA38`, `MOV027`, `1-1.2`), accesibilidad
    con lector de pantalla simulado, carrera de peticiones y estados 401/403/422/503 (§8).

---

## 1. Hallazgos que cambian el diseño (verificados por lectura)

| # | Hallazgo | Consecuencia |
|---|---|---|
| H-1 | «Código» en Componer es el de la **partida**: `componer/index.tsx:202-208`, `labelText="Código"` sin ayuda ni lista. La tabla de insumos no tiene columna de código (`tablas.ts` `COLUMNAS`: descripción, unidad, consumo, precio…). | El combobox de código es de **partidas**; los de insumo buscan por **nombre o por código MaPreX**, sin pedir un código del catálogo. |
| H-2 | Un código existente con cabecera distinta se rechaza al guardar: «la cabecera de una partida existente no se edita desde esta pantalla. Escriba la descripción registrada o use otro código» (`aplicacion/composicion.py:420-435`). `precargar` solo devuelve tablas y rendimiento (`api/rutas/composicion.py:248-252`, `PrecargaRespuesta`). | La respuesta de precarga se **amplía** (campos aditivos `descripcion`, `unidad`, `dominio`; §5.5) y, si la partida existe, la cabecera queda **de solo lectura** con su explicación. |
| H-3 | La precarga se dispara con **cada código parcial** tecleado (`componer/index.tsx:106-128`, pausa de 300 ms). Con un combobox, cada letra sería una consulta y una precarga posible. | La precarga pasa a dispararse al **elegir o confirmar** un código, no al teclear. |
| H-4 | Buscador MaPreX actual: `buscar_referencia` hace `objetivo in normalizar_texto(fila["insumo"])` (`aplicacion/composicion.py:487-533`): la frase entera debe aparecer **contigua**; solo busca en la descripción; devuelve las filas «en el orden de los archivos», sin límite. Corrida a mano contra los CSV: `tuberia` → 0 filas (la lista dice «TUBO»); `tubo pvc` → 2 (`PLOA38`, `ELE906`); `pvc` → 6. | La búsqueda nueva exige **todas las palabras** (como `coincide` del Catálogo, `catalogo/filtro.ts`), en cualquier orden, busca en descripción **y código MaPreX**, ordena por relevancia y limita. Es un **superconjunto** de la actual (paridad §8.1). |
| H-5 | La fila que entrega el buscador (`fila_*_desde_referencia`, `aplicacion/composicion.py:554-596`) trae solo descripción, unidad, precio (y depreciación o sueldo). El `ref_maprex` se muestra en `BuscadorReferencia.tsx:88` y **se pierde** al usar la fila. | El componente guarda la **procedencia** de cada fila elegida (código MaPreX, fecha, moneda, fuente) en el estado de la página y la muestra bajo la celda (§6). Persistirla en la composición guardada exige tocar el esquema: D-6 (diferido). |
| H-6 | El precio que rellena el buscador es `precio_usd` (`fila_materiales_desde_referencia`: `str(fila.precio_usd)`), derivado de bolívares con la tasa 633,3644 del 01/07/2026 y redondeado a 4 decimales (`README.md` de MaPreX). La lista de precios del caso tiene su propia moneda (`ListaPrecios.moneda`, `core/models/entidades.py:196`). | Si la lista vigente del caso está en Bs, rellenar USD sería un error silencioso. El servidor rellena en **la moneda de la lista vigente**: `precio_bs` (exacto, tal como lo imprime el PDF) o `precio_usd`; ambas se **muestran** (D-7). |
| H-7 | Referencia MaPreX estructurada: 111 filas = 40 materiales, 19 equipos, 52 mano de obra; 59 con fecha 2026-07-09 y 52 con 2026-07-01 (el tabulador). Los PDF (≈16 000 renglones) no se consultan. El tabulador CIV (43 filas) es de referencia y su descripción viene **truncada** en algunas filas («… (14 A 15 AÑOS DE EXP»; README). | La lista se muestra tal cual, sin completar descripciones; el estado vacío explica el alcance real (§3.5). |
| H-8 | Unidades de MaPreX en la referencia: `dia`, `pza`, `und`, `m`, `m3`, `env`, `lt`, `sco`, `rll`, `sg`. Solo algunas están en la tabla de alias (`core/contracts/unidades.py`: `pza`→`pieza`, `und`→`unidad`, `sg`); **`env`, `lt`, `sco` y `rll` no son alias de nada**. La regla R3 (coherencia dimensional) compara unidades. | No lo probé contra R3. El plan incluye una prueba de oráculo (§8.2, P-9) y, si R3 marcara una unidad MaPreX legítima, se **anota como hallazgo** (no se toca `core/` aquí; D-11). |
| H-9 | Catálogo: `GET /partidas` y `GET /insumos` (`api/rutas/catalogo.py`) devuelven todo; `InsumoRespuesta` trae `precio_vigente` pero **no** la moneda, la fecha ni el nombre de la lista. | El contrato nuevo devuelve precio **con** moneda, fecha y nombre de la lista (§5.3). Los dos GET existentes no cambian. |
| H-10 | La Hoja ya tiene búsqueda de insumos de **una versión abierta** (`GET /v1/hoja/borradores/{id}/insumos`, E8, `api/rutas/hoja.py:717`): `texto` en la descripción, a lo sumo 300, ordenado por descripción, 409 sin versión abierta. La interfaz la usa con un campo de búsqueda **más** un `Select` nativo (`hoja/CambioDeInsumo.tsx:142-171`). Cotizar usa un `Select` nativo con **todos** los insumos de la lista (`hoja/OperacionesDePrecios.tsx:73-77`). | Cambiar de insumo **reutiliza E8** (cero backend nuevo). Cotizar filtra en el navegador la lista que la pestaña ya cargó (modo local del componente). |
| H-11 | No existe ningún `ComboBox`, `datalist` ni autocompletado en el front (`grep` de `ComboBox\|FilterableMultiSelect\|Dropdown\|Autocomp\|datalist` en `src/**/*.tsx` → ningún componente propio; los resultados que salieron no los inspeccioné uno a uno). Carbon 1.117.0 trae `ComboBox`. | Es un componente nuevo en `src/comun/`. No pude **ejecutar** el `ComboBox` aquí: la viabilidad (§4.7) es la rebanada F0, antes de construir nada sobre él. |
| H-12 | Regla VB-18: `TextInput` y `TextArea` de Carbon solo se importan en `comun/CampoTexto.tsx` y `AreaTexto.tsx`; `comun/regionesVivasVacias.test.tsx` lo vigila por ruta exacta porque montan un `<span role="alert" aria-live>` vacío por campo. | `CampoConBusqueda` **no puede importar `TextInput`**. Si el `ComboBox` de Carbon monta regiones vivas vacías o usa `TextInput` por dentro, F0 lo detecta y se aplica el plan B (§4.7). La región viva del conteo existe **solo con contenido** (§4.4). |
| H-13 | `pedir` (`src/api/cliente.ts`) no acepta `AbortSignal`: `fetch(ruta, { method, headers, body, credentials })`. Los buscadores actuales descartan por «turno» (`BuscadorReferencia.tsx:26-47`), pero la petición vieja sigue viva. | «Una sola petición en vuelo» necesita que `pedir` acepte `senal?: AbortSignal` (cambio **aditivo** y compartido, §9 F0). |
| H-14 | Acceso: `/v1/composicion/*` exige `EDITAR_HOJA` (arma); `GET /partidas` e `/insumos`, `LEER_PROYECTO` (arma y revisa); `GET /v1/precios-empresa` exige `ADMINISTRAR_PRECIOS` (`api/acceso.py`, `precios_empresa.py:73-77`). | El buscador hereda la acción de la pantalla que lo usa (§5.1). Las listas de la empresa no se exponen a quien arma. |
| H-15 | Códigos de insumo asignados: `PREFIJO-NNN` (`repositorio.py:455-464`); variantes con sufijo si el precio difiere (`_codigo_variante`). Partidas de prueba usan `LB-01-EXC`, `LB-02-TUB` (`tests/fixtures/apu_linea_base.py`). El sistema **no impone** un formato al código de una partida (no encontré validación; no leí `composicion_desde_tablas` entera). | La sugerencia de código (§5.4) es una **ayuda**, nunca una regla. |

---

## 2. Inventario de campos que piden un dato que la persona no tiene por qué saber de memoria

**Clases:** **A** = autocompletado (búsqueda en catálogo, MaPreX o lista de la versión; usa `CampoConBusqueda`); **B** = lista
cerrada o corta con ayuda en lenguaje llano (el campo ya es un `Select`, o debe serlo); **C** = texto libre, con ejemplo y ayuda
(`helperText`), sin búsqueda; **D** = ya correcto, solo se revisa el texto. «Rebanada» remite a §9.

### 2.1 Componer una partida (`componer/`)

| Id | archivo:línea | Campo (rótulo hoy) | Qué se le pide hoy | Clase | Qué pasa en el diseño nuevo | Reb. |
|---|---|---|---|---|---|---|
| C-1 | `index.tsx:202-208` | Código | Un código de partida, en blanco, sin ayuda | **A** | Combobox de **partidas del catálogo**; al elegir una existente rellena descripción, unidad, dominio, tablas y rendimiento y bloquea la cabecera; si no hay coincidencia ofrece «Crear una partida nueva con el código …» y una sugerencia de código (§7.1) | F2 |
| C-2 | `index.tsx:209-218` | Descripción | Texto libre | **C** (+ ayuda existente «Similares») | Ejemplo y ayuda: «Qué se hace, en una frase». Si la partida existe: solo lectura | F2 |
| C-3 | `index.tsx:219-225` | Unidad | Texto libre («m3», «m²»…) | **A/B** (lista con valor libre) | `CampoConBusqueda` en modo local con las unidades del catálogo y de MaPreX y su glosa («m3 · metro cúbico»); se acepta otra con aviso (§7.3) | F2 |
| C-4 | `index.tsx:226-236` | Dominio | `Select` civil/telecom/industrial/sistemas | **B** | Se queda; se añade ayuda («el tipo de obra; define con qué partidas se compara») | F2 |
| C-5 | `index.tsx:237-247` | Fecha | Fecha | **D** | Ayuda: «Desde cuándo vale esta composición» | F2 |
| C-6 | `index.tsx:260-266` | Rendimiento: unidades por día | Un número | **C** | Ayuda llana + ejemplo: «Cuánta obra hace la cuadrilla en un día. Ejemplo: 12 m de tubería por día». Ya existe la propuesta del histórico | F2 |
| C-7 | `index.tsx:274-283` | Condiciones del rendimiento | Texto obligatorio | **C** | Ejemplo: «Cuadrilla de 1 maestro y 2 ayudantes, terreno plano, clima seco» | F2 |
| C-8 | `TablaInsumos.tsx:68-74` (celda `descripcion`) | Descripción, fila n (materiales, equipos, mano de obra) | Texto libre por celda; el buscador está aparte (`BuscadorReferencia.tsx:63-69`) | **A** | La **celda de descripción** pasa a ser un combobox (catálogo + MaPreX por tipo). `BuscadorReferencia` desaparece (§7.2) | F2 |
| C-9 | `TablaInsumos.tsx:68-74` (celda `unidad`, solo materiales) | Unidad | Texto libre | **A** (rellenada) / **B** | Se rellena al elegir el insumo; editable a mano con la lista de unidades (C-3) | F2 |
| C-10 | `TablaInsumos.tsx:68-74` (celdas `cantidad`, `precio`, `depreciacion`, `sueldo`) | Consumo por unidad, Precio, Depreciación, Sueldo | Números como texto | **C** | Ayuda breve por columna (en el encabezado, con `Tooltip` accesible y también en texto visible bajo la tabla): «Consumo por unidad: cuánto de este material entra en una unidad de la partida»; «Depreciación: la fracción del precio que se gasta por día de uso (0,0035 = 0,35 %)»; «Sueldo: lo que gana por día (jornal) o el precio por unidad de obra (destajo)» | F2 |
| C-11 | `TablaInsumos.tsx:54-66` | Modalidad (mano de obra) | `Select` jornal/destajo, primera opción vacía | **B** | Ayuda llana: «Jornal: se paga por día trabajado. Destajo: se paga por cada unidad de obra hecha» (`core/contracts/apu.py:69-80`) | F2 |
| C-12 | `Guardar.tsx:29-31` | Justificación de la advertencia | Texto | **C** | Ejemplo: «El terreno es rocoso; la cuadrilla rinde menos que el histórico» | F2 |

### 2.2 Hoja del proyecto (`hoja/`)

| Id | archivo:línea | Campo | Hoy | Clase | Diseño nuevo | Reb. |
|---|---|---|---|---|---|---|
| H-A1 | `OperacionesDePrecios.tsx:73-77` | Insumo (cotizar) | `Select` nativo con todos los insumos de la lista, rótulo `código · insumo` | **A** (modo local) | Combobox que filtra `vista.filas` en el navegador; muestra descripción, código, precio de la lista y cotización vigente si la hay; sin petición | F3 |
| H-A2 | `OperacionesDePrecios.tsx:79-86` | Precio cotizado | Texto, ayuda «Decimales con punto, por ejemplo 2.5» | **C** | Mostrar al lado el precio de la lista del insumo elegido y su moneda (de la fila ya cargada) para que la persona vea contra qué cotiza | F3 |
| H-A3 | `OperacionesDePrecios.tsx:88-94` | Proveedor | Texto libre | **A/C** | Texto libre **con sugerencias** de los proveedores ya cotizados en este proyecto (`/v1/buscar/proveedores`), nunca de otros casos | F3 |
| H-A4 | `OperacionesDePrecios.tsx:95-101`, `:109-115` | Número de la cotización; Evidencia | Texto | **C** | Ejemplos: «COT-2026-014»; «Correo del 12/10 con la oferta» (ficticios) | F3 |
| H-A5 | `OperacionesDePrecios.tsx:143-147` | Insumo cotizado (retirar) | `Select` con solo los cotizados | **D** | Se queda (lista corta); ayuda | F3 |
| H-A6 | `CambioDeInsumo.tsx:142-171` | «Buscar insumo (por descripción)» + `Select` «Insumo» | Dos controles encadenados; 300 candidatos como máximo | **A** | **Un** combobox sobre E8 (`rutaDeInsumos`), con el mismo límite y el aviso «hay más de 300» | F3 |
| H-A7 | `CambioDeInsumo.tsx:117-135` | Tipo de línea; Línea | `Select` | **B** | Se quedan; el rótulo de la línea ya lleva su descripción | — |
| H-A8 | `PestanaApu.tsx:297-317` | Buscar partida + grupo de opciones | Filtro de una lista visible | **D** | No es un campo de dato; se queda. Ejemplo en el `placeholder` | F3 |
| H-A9 | `ConvertirMoneda.tsx:57`, `:64`, `:74` | Moneda destino; Tasa del BCV; Por qué se cambia (fuente) | `Select`; `Select`; texto | **B/B/C** | Ayuda en la tasa («venta o compra: la que publica el BCV para el día de hoy»); ejemplo en la fuente | F3 |
| H-A10 | Agregar partida a la hoja | No existe en la interfaz React (la hoja edita cantidades y rendimientos, no agrega partidas; no encontré una ruta ni un control) | — | — | **Fuera de alcance**: si se añade, usa `CampoConBusqueda` de partidas (C-1) | — |

### 2.3 Catálogo, precios de la empresa y resto de pantallas

| Id | archivo:línea | Campo | Hoy | Clase | Diseño nuevo | Reb. |
|---|---|---|---|---|---|---|
| K-1 | `catalogo/index.tsx:65-70` | Buscar en el catálogo | `Search` que filtra las dos tablas en el navegador sobre **toda** la lista cargada | **D** (se mantiene) | Es un filtro de tablas visibles, no un campo de dato. Se ajusta el texto de ayuda (§7.4). Si el catálogo crece, usa el contrato nuevo con paginación (no ahora) | F4 |
| P-1 | `precios_empresa/index.tsx:214-215` | Empresa (nombre); RIF | Texto | **C** | Ejemplos ficticios «Contratista Demo, C.A.», «J-00000000-0» | F5 |
| P-2 | `precios_empresa/index.tsx:216`, `:221` | Lista base; Moneda de la lista | `Select` | **B** | Ayuda: «La lista que se toma de punto de partida (por ejemplo, MaPreX)» | F5 |
| P-3 | `precios_empresa/index.tsx:228-234` | Fuente de la lista; Nombre | Texto | **C** | Ejemplo: «Lista de precios del proveedor, PDF del 05/10/2026» | F5 |
| E-1 | `elaborar/index.tsx:358` | Código del presupuesto | Texto | **C** (+ sugerencia) | Sugerencia de siguiente código libre y ejemplo | F4 |
| E-2 | `elaborar/index.tsx:373-379` | Moneda | **Texto libre** (se escribe «Bs» o «USD» a mano) | **B** | `Select` Bs/USD (`core/catalog/moneda.py:20`, `MONEDAS`) | F4 |
| E-3 | `elaborar/index.tsx:396`, `:416` | Selectores de partida civil (y «Relleno») | `Select` nativo con **todas** las partidas civiles | **A** (modo local) | Combobox sobre la lista ya cargada | F4 |
| E-4 | `elaborar/index.tsx:115` | Propuesta para un pendiente | `Select` con los códigos | **D** | Se queda | — |
| U-1 | `actualizacion/index.tsx:206-212` | Código de la versión nueva | Texto | **C** (+ sugerencia) | Ejemplo y sugerencia | F4 |
| U-2 | `actualizacion/index.tsx:219-225` | Moneda | **Texto libre** | **B** | `Select` Bs/USD | F4 |
| U-3 | `actualizacion/index.tsx:228-232` | Nombre de la lista | Texto | **C** | Ejemplo | F4 |
| HI-1 | `historico/index.tsx:61-67` | Insumo (descripción exacta) | Texto: hay que escribir la descripción **exacta** | **A** | Combobox de insumos con historial de precio (`/v1/buscar/insumos`, ámbito `historico`) | F5 |
| ES-1 | `escenarios/index.tsx:293-299` | Insumo (descripción exacta), por fila | Texto exacto | **A** | Combobox de los insumos del presupuesto base | F5 |
| SI-1 | `simulador/index.tsx:116-123` | Insumos («separados por coma; vacío = todos») | Texto con comas | **A** (múltiple) | Combobox de selección múltiple; diferido (D-9) | — |
| CO-1 | `control/PestanaValuaciones.tsx:59` | Partida n (valuación) | Texto | **A** | Combobox de las partidas **de la línea base** del proyecto (ámbito `proyecto`) | F5 |
| CO-2 | `control/PestanaValuaciones.tsx:201` | Partida (opcional) del costo real | Texto | **A** | Igual | F5 |
| CO-3 | `control/PestanaValuaciones.tsx:196` | Moneda del costo | `Select` | **D** | Se queda | — |
| CO-4 | `control/PestanaLineaBase.tsx:83`; `PestanasDeResultados.tsx:83`, `:333` | Fuentes (línea base, Km y R, decisión) | Texto | **C** | Ejemplo en cada una: «Contrato N.º 123, cláusula 8, firmado el 01/10/2026» | F5 |
| RE-1 | `reajuste/index.tsx:263`, `:275-277`, `:395-396` | Fuente de la cláusula, de R, del estudio; Responsable | Texto (ya tienen ayuda parcial) | **C** | Unificar el ejemplo | F5 |
| EX-1 | `existencias/PestanaRegistrar.tsx:249-256` | Código del material nuevo | Texto | **C** | Ejemplo y comprobación de duplicado en vivo contra los materiales ya cargados | F5 |
| EX-2 | `existencias/PestanaRegistrar.tsx:126` | Material | `Select` | **D** | Se queda (lista corta de la arenera) | — |
| SM-1 | `similares/index.tsx:155-160` | Descripción de la partida | Texto | **C** | Ejemplo: «Tubería de PVC de 4 pulgadas, suministro e instalación» | F5 |
| IN-1 | `indices/index.tsx:163-168` | Dirección de la página del BCV | Texto | **C** | Ejemplo con dirección ficticia | F5 |
| AD-1 | `administracion/Empresa.tsx:144-146` | Nombre, RIF, Ciudad de la empresa | Texto | **C** | Ejemplos ficticios | F5 |

**Fuera del inventario por decisión:** campos de contraseña, huellas, claves y modelos de IA de Administración (el usuario es el
administrador y el dato no es de un catálogo), filtros por fecha del Historial y los `Select` que ya son una lista cerrada con
rótulos claros (`reajuste/index.tsx:245-264`, periodicidad/mecanismo/estructura).

**Conteo:** 12 filas de Componer + 10 de la Hoja + 24 del resto = 46 filas del inventario. Los combos de búsqueda (clase A) son
C-1, C-3, C-8, C-9, H-A1, H-A3, H-A6, E-3, HI-1, ES-1, CO-1 y CO-2 (más SI-1, diferido); el resto son listas cerradas, ayudas de texto o
campos que ya están bien.

---

## 3. El componente `CampoConBusqueda`

### 3.1 Qué es y qué no es

Un campo de texto con una lista de sugerencias que se despliega bajo él, accesible por teclado y por lector de pantalla. **Es un
selector con búsqueda, no un cuadro de texto que adivina:** lo que la persona escribe es una búsqueda; lo que queda en el
campo es lo que **eligió** (o, si lo permite el uso, un valor propio explícito). No convierte, no calcula y no guarda nada por sí
mismo: entrega a su padre una **opción elegida** y el padre decide qué campos rellena.

Vive en `src/comun/CampoConBusqueda.tsx` (con `CampoConBusqueda.test.tsx`, `logicaBusqueda.ts` y su prueba, y estilos en
`comun.scss`). No toca `src/shell/rutas.ts`.

### 3.2 Propiedades (contrato del componente)

```ts
interface OpcionDeBusqueda<T> {
  clave: string;          // estable y única en toda la lista: "catalogo:INS-004", "maprex:PLOA38"
  principal: string;      // línea 1: lo que la persona reconoce (la descripción)
  secundaria: string[];   // línea 2: [código, unidad, precio con moneda, fuente y fecha], ya como texto
  grupo: string;          // "Del catálogo de este caso", "Referencia MaPreX jul-2026"
  valor: T;               // lo que recibe el padre al elegir
}
interface GrupoDeResultados<T> { rotulo: string; opciones: OpcionDeBusqueda<T>[]; hayMas: boolean }

interface Props<T> {
  id: string;
  etiqueta: string;                 // visible siempre, lenguaje llano ("Código de la partida")
  ayuda?: string;                   // `helperText` bajo el campo, con ejemplo
  texto: string;                    // el texto del campo (controlado por el padre)
  alCambiarTexto: (texto: string) => void;
  // Exactamente una de las dos fuentes de opciones:
  buscar?: (q: string, senal: AbortSignal) => Promise<GrupoDeResultados<T>[]>;
  opciones?: OpcionDeBusqueda<T>[]; // modo local (lista ya cargada): filtra en el navegador
  alElegir: (opcion: OpcionDeBusqueda<T>) => void;
  valorPropio?: {                   // ofrece la última opción de la lista: usar lo escrito tal cual
    rotulo: (texto: string) => string;   // "Crear una partida nueva con el código «LB-06»"
    alUsar: (texto: string) => void;
  };
  vacio: { titulo: string; pasos: string };  // "¿No lo encuentra?" + qué hacer (§3.5)
  minimoDeLetras?: number;          // 2
  pausaMs?: number;                 // 300 (el mismo retardo que los demás buscadores de la interfaz)
  limiteVisible?: number;           // 20
  alExpirar: () => void;            // 401 → cerrar sesión, como los demás buscadores
  invalido?: boolean; textoInvalido?: string;
  deshabilitado?: boolean; soloLectura?: boolean;
  tamano?: "sm" | "md";             // "sm" por omisión
}
```

La API del componente **no** trae montos como `number`: `secundaria` ya llega como texto formateado por el padre con
`formatoEsVe` (que es sobre cadenas, `formatoEsVe.ts:5-12`).

### 3.3 Comportamiento

1. **Mínimo de letras:** con menos de 2 caracteres no se pide nada; la región de estado dice «Escriba al menos 2 letras o un código» (§3.6).
2. **Pausa (debounce):** 300 ms tras la última tecla (el mismo `RETARDO_MS` de `BuscadorReferencia.tsx:17` y de `componer/index.tsx:20`).
3. **Una sola petición en vuelo:** `useRef` con un `AbortController` y un contador de turno. Al llegar un texto nuevo: si hay una
   petición en curso se **aborta** (`senal`, §9 F0) y se programa la siguiente; la respuesta de un turno viejo se descarta aunque
   no se haya podido abortar (defensa doble, como hoy). Nunca hay dos solicitudes simultáneas del mismo campo.
4. **Texto normalizado en el servidor**, no en el navegador; el navegador solo recorta espacios de los bordes. (El modo local usa
   `coincide`/`normalizar` de `catalogo/filtro.ts`, que se mueve a `comun/` sin cambiar su comportamiento; es una función pura ya probada.)
5. **Límite visible:** 20 resultados en total (8 por grupo si hay dos grupos, ver §5). Si el servidor dice `hay_mas`, se muestra bajo
   la lista «Hay más resultados: escriba más letras para acotar» (texto, **fuera** del `listbox`).
6. **Orden:** el que manda el servidor (relevancia, §5.2). El componente no reordena.
7. **Elegir:** `Enter` o clic sobre una opción llama `alElegir(opcion)`, pone `principal` en el campo, cierra la lista y deja el
   foco en el campo. **Elegir no es enviar:** `Enter` con la lista abierta y una opción activa **no** envía el formulario.
8. **Escribir sin elegir:** al salir (`Tab`/clic fuera) el texto queda **tal cual** y el padre decide (p. ej. Componer trata un
   código escrito como «partida nueva» solo si la persona lo confirmó con la opción explícita, D-3). El componente **nunca** elige
   por su cuenta la primera sugerencia.
9. **Borrar:** `Esc` con la lista cerrada y algo elegido limpia la elección (el padre recibe `alCambiarTexto("")`); un botón
   «Borrar» (icono + nombre accesible) hace lo mismo con el ratón.
10. **Errores:** 401 → `alExpirar()`; 403 → aviso en la propia lista «Su cuenta no puede usar esta búsqueda» (detalle de la API tal cual);
    422 → «La búsqueda no es válida: escriba otra cosa» (mensaje fijo, sin repetir lo escrito); 503 y red caída (`estado` 0) →
    el `detalle` de la API; el campo **sigue siendo de texto libre**: un error de búsqueda no impide teclear ni guardar lo escrito.

### 3.4 Lo que se muestra en cada opción

Dos líneas, sin tabla (la lista cabe en 1056 px; §6.4):

```
TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA                 ← principal (cuerpo, 16 px con la letra Normal)
PLOA38 · m · 13,9291 USD · MaPreX jul-2026 · 09/07/2026      ← secundaria (etiqueta, IBM Plex Mono solo en el código)
```

- El **código** va en Plex Mono (DESIGN.md: «IBM Plex Mono para referencias de celda y códigos»).
- El **precio** va como `formatoEsVe(precio) + " " + moneda`, exacto tal como llega (sin redondear). Si la API manda dos
  monedas (MaPreX), se muestra **la de la lista del caso** y la otra queda en la descripción accesible (`aria-describedby`).
- **Fuente y fecha siempre visibles** (nunca solo en un `Tooltip`); la fecha como `dd/mm/aaaa`, construida **troceando la cadena**
  `AAAA-MM-DD` (sin `new Date`, que corre el día por zona horaria).
- Un resultado sin precio dice «sin precio en la lista vigente» en vez de dejar un hueco.
- El texto de la API es siempre un **nodo de texto de React**; no se usa `dangerouslySetInnerHTML` ni se interpreta Markdown. El resaltado
  de la parte coincidente (negrita) se hace partiendo la cadena por posiciones calculadas sobre el mismo texto y envolviendo los
  tramos en `<strong>`; nunca se inyecta HTML. (Pruebas: una descripción con `<img onerror=…>` y con `&lt;` se ve literal, P-12.)

### 3.5 Estado «no lo encuentro» (central, no accesorio)

Cuando una búsqueda termina sin resultados, **dentro de la lista** aparece (y se anuncia, §3.6):

> **No encontramos «{texto}».**
> {pasos del uso}

`pasos` los define el uso, siempre en tres frases cortas: qué probar, qué es la fuente y qué hacer si de verdad no está. Textos fijos:

| Uso | Pasos |
|---|---|
| Código de partida (C-1) | «Pruebe con una palabra de la descripción (por ejemplo «tubo»). Si la partida no existe todavía, elija «Crear una partida nueva con el código …» al final de la lista y componga sus insumos abajo.» |
| Descripción de insumo, material (C-8) | «Pruebe con una palabra más corta o con otra forma de nombrarlo («tubo» en vez de «tubería»). La referencia MaPreX de este programa tiene unos cientos de renglones, no todo el listado. Si no está, escriba el nombre del insumo y su precio a mano: quedará como insumo propio.» |
| Mano de obra | «Busque por el oficio («ayudante», «ingeniero») o por el código de MaPreX. Si no está, escriba el cargo y el sueldo por día a mano.» |
| Insumo de la lista de la versión (H-A1, H-A6) | «Ese insumo no está en la lista de precios de esta versión. Pruebe con otra palabra. Si no existe en la lista, no se puede cotizar aquí: agréguelo antes en la composición de la partida.» |
| Partida de la línea base (CO-1) | «Esa partida no está en la línea base de este proyecto. Revise el código o la descripción.» |

La frase «tubo en vez de tubería» es un hecho de los datos (H-4), no un chiste: la lista usa «TUBO».

### 3.6 Accesibilidad (patrón combobox ARIA 1.2)

| Elemento | Atributos |
|---|---|
| Campo | `role="combobox"`, `aria-expanded`, `aria-controls` (id del listbox), `aria-autocomplete="list"`, `aria-activedescendant` (id de la opción activa; el foco **no** sale del campo), `aria-describedby` (ayuda + región de estado), `aria-invalid` si procede |
| Lista | `role="listbox"`, `aria-label` con la etiqueta del campo; con dos grupos, `role="group"` con `aria-labelledby` al rótulo del grupo |
| Opción | `role="option"`, `aria-selected` (solo la activa), `id` estable; `aria-setsize` y `aria-posinset` cuando hay más de las visibles |
| Región de estado | `role="status"` (`aria-live="polite"`, `aria-atomic="true"`) **presente solo mientras el campo tiene el foco o la lista está abierta, y siempre con texto** (cumple VB-18: ninguna región viva vacía). Dice, una vez por búsqueda terminada: «12 resultados. Use las flechas para recorrerlos.», «1 resultado.», «Sin resultados para «{texto}».», «Buscando…» (solo si pasan 700 ms), «No se pudo buscar: …». No anuncia cada tecla. El texto del usuario se inserta como texto (`textContent`), recortado a 60 caracteres. |

Teclado: `↓` abre y baja (si ya está abierta, baja; al final vuelve al campo); `↑` sube; `Alt+↓` abre sin mover; `Enter` elige la activa;
`Esc` cierra (y, si ya estaba cerrada, limpia la elección); `Tab` cierra y sigue (no elige); `Inicio` y `Fin` mueven al texto del campo
(no a la lista); `PageDown`/`PageUp` saltan de 5 en 5. La opción activa se desplaza a la vista (`scrollIntoView({ block: "nearest" })`).
Foco visible: el anillo de Carbon (`AnilloDeFoco`, `comun/AnilloDeFoco.test.ts`) en el campo; la opción activa lleva fondo `$layer-hover`
**y** un borde izquierdo de 4 px (el color nunca va solo).

Letra: todo en `rem`, sigue `--silice-escala-letra`. Con Muy grande (150 %) y 1056 px la lista mide a lo sumo `min(20rem, 60vh)` con
desplazamiento interno y **no** produce desplazamiento horizontal de la página; las dos líneas de cada opción **bajan de línea**, no se recortan
(nunca `text-overflow: ellipsis` en la descripción: se necesita entera para distinguir «TUBO PVC A.N.» de «TUBO PVC A.B.»).

### 3.7 Estilo

Carbon g10, esquinas rectas, densidad `sm` (32 px el campo), sin animación decorativa (la lista aparece sin transición),
sin sombra decorativa: el borde de 1 px `$border-strong` y el fondo `$layer`. La lista usa las clases `cds--list-box` del propio
`ComboBox`. Los encabezados de grupo van en `label-01`, sin mayúsculas espaciadas (DESIGN.md «Texto»).

---

## 4. Decisión de implementación y su plan B

### 4.1 Opción elegida: `ComboBox` de Carbon como base

`ComboBox` de `@carbon/react` 1.117.0 ya resuelve el patrón ARIA, el `listbox`, el borrado y los estilos. La interfaz se compromete
con Carbon «nativo, sin recrearlo a mano» (DESIGN.md, «Sistema»). **No pude ejecutarlo en este análisis** (no corrí el front);
tres cosas que no sé y que la rebanada F0 comprueba antes de construir nada:

1. Si **monta regiones vivas vacías** o usa `TextInput` por dentro (VB-18, H-12) y si el truco de `useSinRegionVacia` basta.
2. Si admite **filtrado por el servidor** (`shouldFilterItem={() => true}` con `items` controlados), **dos líneas por opción**
   (`itemToElement`) y **grupos** con encabezado accesible.
3. Si `aria-activedescendant` y el anuncio del conteo se pueden **probar** con Testing Library en jsdom.

### 4.2 Plan B (si F0 falla en 1 o 2)

Construir el patrón ARIA 1.2 sobre `CampoTexto` (que ya cumple VB-18) y un `<ul role="listbox">` con las clases `cds--list-box__*`
de `@carbon/styles`. Es más código (≈200 líneas) pero la interfaz pública (§3.2) **no cambia**: las páginas no se enteran. La
decisión la toma el implementador de F0 con el resultado de las tres comprobaciones y la deja en la bitácora.

---

## 5. Contrato de API

### 5.1 Reglas comunes (todas las rutas de `/v1/buscar`)

- Router nuevo `api/rutas/busqueda.py`, prefijo `/v1/buscar`, **solo lectura** (`GET`), `route_class` que combina `RutaSinCache` y `RutaSinEco`
  (en ese orden: la spec de la hoja §1.3 #7 documenta que el inverso atrapa el `RequestValidationError`; **no lo probé**, la prueba de §8.1 lo fija).
  Respuestas con `Cache-Control: no-store`; el 422 sin eco (`{"detalle": <mensaje fijo>}`), que **no repite** lo buscado.
- Acceso por ruta (`api/acceso.py`): `/partidas`, `/insumos` (catálogo y MaPreX), `/codigo-sugerido`: **`LEER_PROYECTO`** (arma y revisa; clave de API o sesión;
  es lo que ya exige `GET /partidas` e `/insumos`). `/proveedores`: **`EDITAR_HOJA`** (arma). Un revisor que abre Componer recibe 403, igual que hoy.
  La clave de API no se distingue: ninguna ruta escribe.
- Parámetro `q`: `Query(max_length=80)`; se recorta; vacío o de menos de 2 caracteres → **200 con `resultados: []`** (no 422: un campo que se
  está tecleando no es un error). Más de 80 → 422.
- `limite`: 1..50, por omisión 20; con dos fuentes, el tope es **por grupo**.
- Montos y cantidades: **texto** (`"13.9291"`), nunca `float`. Fechas: `AAAA-MM-DD`.
- Un error de base (`SQLAlchemyError`) → 503 con mensaje fijo, sin SQL ni rutas (patrón `_caso_legible`, `precios_empresa.py`).
- Ninguna ruta lee de más de **un caso**: opera sobre el caso de la sesión (`SesionDep`); no hay parámetro de caso. La referencia MaPreX son
  archivos del repositorio (no abre la base), como `referencia` hoy.

### 5.2 Búsqueda y orden por relevancia (una sola implementación, `aplicacion/busqueda.py`)

1. Texto normalizado con `core.verification.texto.normalizar_texto` (la única normalización del repositorio) y separado en palabras.
2. Una fila coincide si **todas** las palabras aparecen como subcadena en la concatenación normalizada de (código, descripción). La unidad **no** entra en la búsqueda: con ella, escribir «dia» o «m» devolvería toda la mano de obra o todo lo medido en metros. *(Paridad: todo lo que halla hoy `buscar_referencia` para una sola palabra o una frase contigua lo sigue hallando.)*
3. Rango (menor es mejor): 0 = el código normalizado es igual al texto; 1 = el código empieza por el texto; 2 = la descripción empieza por la primera palabra;
   3 = alguna palabra de la descripción empieza por la primera palabra; 4 = cualquier otra coincidencia. Desempate: descripción normalizada, luego código.
4. Se deduplica por (tipo, referencia) antes de ordenar.

### 5.3 `GET /v1/buscar/insumos`

Parámetros: `tipo` (`material|equipo|mano_obra`, obligatorio), `q`, `fuentes` (lista separada por comas de `catalogo`, `maprex`; por omisión `catalogo,maprex`), `limite`.

```jsonc
{
  "grupos": [
    {
      "fuente": "catalogo",
      "rotulo": "Del catálogo de este caso",
      "lista": { "nombre": "Lista del caso", "moneda": "USD", "fecha": "2026-08-01" },   // null si no hay lista vigente
      "resultados": [
        { "clave": "catalogo:MAT-004", "codigo": "MAT-004", "descripcion": "…", "unidad": "m",
          "precio": { "texto": "13.9291", "moneda": "USD", "fecha": "2026-08-01" },      // null si la lista no lo valora
          "fila": { "descripcion": "…", "unidad": "m", "cantidad": "", "precio": "13.9291" } }
      ],
      "hay_mas": false
    },
    {
      "fuente": "maprex",
      "rotulo": "Referencia MaPreX jul-2026",
      "lista": { "nombre": "MaPreX julio 2026", "moneda": null, "fecha": "2026-07-09" },
      "resultados": [
        { "clave": "maprex:PLOA38", "codigo": "PLOA38", "descripcion": "TUBO PVC A.N. D=4\" / 110 MM E = 2,2 MM NORMA", "unidad": "m",
          "precio": { "texto": "13.9291", "moneda": "USD", "fecha": "2026-07-09" },
          "precio_alternativo": { "texto": "8822.17", "moneda": "Bs", "fecha": "2026-07-09" },
          "factor_depreciacion": null, "bono_bs": null,
          "fila": { "descripcion": "…", "unidad": "m", "cantidad": "", "precio": "13.9291" } }
      ],
      "hay_mas": false
    }
  ]
}
```

- **Qué se rellena al elegir** (`fila`, armado en el servidor con las funciones que ya existen, `fila_materiales_desde_referencia`, `fila_equipos_desde_referencia`, `fila_mano_obra_desde_referencia`):
  materiales: descripción, unidad, precio; equipos: descripción, precio y **factor de depreciación** (la regla R6 depende de que el factor venga de una sola fuente); mano de obra: descripción y sueldo (el jornal).
  `cantidad` y `modalidad` quedan **en blanco** (la referencia no sabe cuánto consume esta partida). El precio de `fila` está en **la moneda de la lista vigente del caso** (H-6, D-7); si no hay lista vigente, en USD, como hoy.
- Fuente `catalogo`: insumos del tipo cuya descripción o código coincide, con el precio de `Catalogo.lista_vigente()` y los datos de esa lista (`nombre`, `moneda`, `fecha_vigencia`). Sin lista vigente (`CatalogoIncompleto`) → el grupo viene con `lista: null` y precios `null`, **no** 409 (buscar no exige lista).
- Fuente `maprex`: los cuatro `referencia_*.csv`, filtrados por `tipo`; **sin** filas de otro tipo. `precio` es `precio_usd` o `precio_bs` según la moneda de la lista del caso; `precio_alternativo` es el otro. La tasa de conversión no sale en la respuesta (está en la ayuda de §6.2).
- Cuando una misma descripción está en ambas fuentes, **no se fusionan**: aparecen en sus grupos. La persona ve que existe en el catálogo y en MaPreX.
- Errores: 422 si `tipo` o `fuentes` no son válidos (mensaje fijo); 503 si falla la base.

### 5.4 `GET /v1/buscar/partidas` y `GET /v1/buscar/codigo-sugerido`

`/partidas`: `q`, `dominio` (opcional), `ambito` (`catalogo` por omisión | `proyecto`), `proyecto` y `version` (obligatorios con `ambito=proyecto`), `limite`.

```jsonc
{ "rotulo": "Partidas del catálogo", "resultados": [
    { "clave": "partida:LB-02-TUB", "codigo": "LB-02-TUB", "descripcion": "…", "unidad": "m", "dominio": "civil",
      "tiene_composicion": true } ],
  "hay_mas": false }
```

- `ambito=proyecto` devuelve las partidas **del presupuesto** de esa versión (para Control, CO-1/CO-2). *No leí qué función de `aplicacion/` da hoy esas partidas*; la rebanada B4 la localiza y, si no existe, la reutiliza de la hoja (`vista_presupuesto`). Si el proyecto o la versión no existen, 404 con mensaje fijo.
- `tiene_composicion` = existe al menos una línea. Una partida sin composición **se puede elegir** (se compone), con la etiqueta «sin composición todavía».
- `/codigo-sugerido?dominio=`: devuelve `{ "sugerido": "LB-06" | null, "patron": "LB-NN" | null }`. Se calcula **solo** si todos los códigos de partida del dominio siguen el patrón `^([A-Z]+)-(\d+)(-[A-Za-z0-9]+)?$` con **el mismo prefijo**: toma el máximo del número y le suma 1, **sin** sufijo. Si los prefijos difieren o no hay partidas, `sugerido: null` y la interfaz solo muestra el ejemplo. Es una **ayuda**, no una regla (H-15); la persona la edita o la ignora (D-5).

### 5.5 Cambios aditivos a rutas existentes

- `GET /v1/composicion/partidas/{codigo}` (`PrecargaRespuesta`): se añaden `descripcion: str | None`, `unidad: str | None`, `dominio: str | None` (nulos si `existe` es falso). Es **aditivo**: el cliente actual los ignora. Cierra H-2.
- Ninguna ruta existente cambia de acceso ni de semántica. `GET /v1/composicion/referencia` **se conserva** durante la migración (para no romper su prueba y a quien la use) y se marca como reemplazada; se retira en un cambio aparte cuando F2 esté fusionado (D-8).

### 5.6 `GET /v1/buscar/proveedores`

`q`, `proyecto`; devuelve `{ "resultados": [{ "texto": "Ferretería Demo, C.A." }] }`: los proveedores ya cotizados **en ese proyecto**, distintos, por orden de uso reciente, a lo sumo 8. `EDITAR_HOJA`. Nunca mira otros proyectos ni otros casos (D-12).
*(No leí la tabla de cotizaciones para fijar la consulta; B4 lo hace. Si la columna del proveedor se llama distinto, el contrato no cambia.)*

---

## 6. Reglas de datos y presentación

### 6.1 Nada de empresas reales; procedencia visible

- Los únicos datos que el programa **trae** son MaPreX (referencia pública de mercado, julio 2026) y el tabulador CIV (también público; ver memoria del proyecto y
  `data/precios/maprex_2026-07/README.md`). **Ningún** libro ni nombre de empresa real entra en datos, ejemplos, pruebas ni capturas. Los ejemplos de ayuda son ficticios
  («Contratista Demo, C.A.», «J-00000000-0», «Ferretería Demo, C.A.», «COT-2026-014»).
- Los proveedores sugeridos (§5.6) salen **solo** del proyecto de la persona; no hay lista global de proveedores y la columna «Proveedor» de los PDF de MaPreX **no** se
  incorpora (los CSV no la traen).
- Cada resultado y cada fila elegida muestran **fuente + fecha + moneda**: «MaPreX jul-2026 · 09/07/2026 · USD». El rótulo «jul-2026» sale del nombre de la carpeta
  (`maprex_2026-07`) a través de una constante de `aplicacion/busqueda.py`, no de un texto repetido.
- MaPreX es **referencia, no verdad** (spec del prototipo §3.4, ya vigente): el precio rellenado queda **editable** y la tabla lo dice (§6.2).

### 6.2 Cómo se separan las tres fuentes para no confundir

| Fuente | Rótulo en pantalla | Qué es | Dónde aparece | Marca visual |
|---|---|---|---|---|
| Catálogo del caso | «Del catálogo de este caso» | Insumos y partidas **ya guardados** en este caso, con el precio de **su** lista vigente | Componer (insumos y partidas), Hoja (cambiar insumo) | Encabezado de grupo; etiqueta «Catálogo» en la segunda línea |
| Referencia MaPreX | «Referencia MaPreX jul-2026» | Precios de mercado de julio 2026, **solo lectura**, 111 renglones elegidos | Componer (insumos) | Encabezado de grupo; etiqueta «MaPreX jul-2026»; nota en la lista: «Es una referencia: puede cambiar el precio» |
| Lista de la versión | «Lista de precios de esta versión» | Los precios con que está valorado el presupuesto abierto | Hoja (cotizar, cambiar insumo) | Encabezado de grupo; etiqueta «Lista de esta versión» |
| Insumo propio | «Propio» | Lo escrito a mano; sin fuente | Componer | Etiqueta «Propio (escrito a mano)» bajo la celda |

Las tres nunca comparten grupo y **ningún resultado de una fuente se presenta con el rótulo de otra**. En Componer, cada fila de insumo muestra bajo la descripción
una línea de procedencia en `label-01`: «MaPreX jul-2026 · PLOA38 · 09/07/2026 · 13,9291 USD · editable» o «Del catálogo · MAT-004 · lista del 01/08/2026» o «Propio (escrito a mano)».
Esa línea es **estado de la página** (no se guarda en la composición; D-6) y se pierde al recargar: se dice así en la ayuda.

---

## 7. Encaje por pantalla

### 7.1 Componer una partida: flujo exacto

**Antes** (tres pasos separados por el usuario): teclear un código sin saber → teclear descripción y unidad → por cada tabla, un buscador aparte + `Select` de resultados + «Usar esta fila» → «Agregar fila» → cantidades.

**Ahora**, paso a paso:

1. La persona abre **Componer una partida**. El campo **«Código de la partida»** muestra la ayuda: «Es el nombre corto de la partida en el catálogo. Escriba una palabra de su descripción
   (por ejemplo «tubo») para ver las que ya existen, o elija «Crear una partida nueva» si es nueva.» Con el foco, la región de estado dice «Escriba al menos 2 letras o un código».
2. Escribe «tub». A los 300 ms se pide `GET /v1/buscar/partidas?q=tub`. La lista muestra las partidas del catálogo (descripción, y debajo código · unidad · dominio · «con/sin composición»).
   Al final, **siempre**, la opción «Crear una partida nueva con el código «tub»» (si el texto parece un código) o «Crear una partida nueva» (si no); con la sugerencia cuando la hay: «Código sugerido: LB-06».
3. **Si elige una existente:** el campo muestra el código; descripción, unidad y dominio se rellenan y quedan **de solo lectura** con la nota «Esta partida ya existe: su cabecera no se cambia desde aquí.»;
   se pide `GET /v1/composicion/partidas/{código}` y se precargan las tres tablas y el rendimiento (UC-11, como hoy). Un botón «Elegir otra partida» limpia todo (con confirmación si hay filas editadas).
4. **Si elige «Crear una partida nueva»:** el código queda como escribió (o el sugerido), la cabecera se habilita, aparece el aviso ya existente `partida_nueva`, las tablas quedan vacías.
5. **Agregar insumo:** en cada tabla hay un botón **«Agregar insumo»** (sustituye a «Agregar fila» y al buscador de arriba). Agrega una fila vacía y mueve el foco a su celda **Descripción**, que es un combobox.
6. En la celda escribe «retro». Se pide `GET /v1/buscar/insumos?tipo=equipo&q=retro`. La lista muestra el grupo «Del catálogo de este caso» (si hay) y «Referencia MaPreX jul-2026»: `RETROEXCAVADORA CASE O SIM` / `MOV027 · dia · 110.025,9187 USD · MaPreX jul-2026 · 09/07/2026`.
7. Elige. Se rellenan descripción, precio y **depreciación 0,003500** (equipos); el foco pasa a la celda **Cantidad** (lo que falta). Bajo la descripción aparece la línea de procedencia (§6.2).
8. Escribe la cantidad (y la modalidad en mano de obra). El **desglose** se recalcula en vivo, como hoy (`/v1/composicion/evaluar`, 300 ms).
9. Si no encuentra el insumo, ve el mensaje de §3.5 y puede **seguir escribiendo a mano**: descripción libre, unidad y precio. Queda como «Propio (escrito a mano)».
10. Guarda como hoy. El guardado no cambia (D-4: el combobox no crea nada en el catálogo).

**Qué se retira:** `BuscadorReferencia.tsx` (y su prueba, sustituida por las del componente nuevo, P-2) y el botón «Agregar fila» en favor de «Agregar insumo».
**Qué no cambia:** `tablas.ts` (estado de texto), `PanelDesglose`, `Similares`, `Guardar`, `cliente.ts` salvo funciones nuevas.

Detalle de datos: la fila de la tabla sigue siendo `Record<string, string>` (`tablas.ts`). La procedencia vive en un mapa aparte `procedencia: Record<"tipo:índice", Procedencia>`
en `componer/index.tsx`, que se reajusta al borrar/agregar filas (función pura `logicaProcedencia.ts` con su prueba).

### 7.2 Hoja del proyecto

- **Cotizar** (H-A1): el combobox del insumo filtra en el navegador la lista que la pestaña Precios ya cargó; cada opción: descripción · `código` · precio de la lista (con moneda) · «cotizado a …» si ya tiene cotización.
  Elegir fija el `insumo` (código) que el servidor espera; el precio cotizado sigue siendo un campo de texto aparte, con la línea «Precio en la lista: 13,9291 USD» a su lado (texto de la fila, sin calcular).
- **Proveedor** (H-A3): `CampoConBusqueda` con `valorPropio` («Usar «{texto}» como proveedor nuevo»); lo que se escribe se manda tal cual.
- **Cambiar el insumo de una línea** (H-A6): un solo combobox sobre `GET /v1/hoja/borradores/{id}/insumos` (E8): se conservan `LIMITE_DE_INSUMOS = 300`, el aviso «Hay más de 300 insumos…» y el 409 «Abra una versión guardada…» (con `soloLecturaInsumos`). «Usar este insumo» se mantiene como botón (cambia el borrador y recalcula: no debe ocurrir al elegir).
- **Presupuesto/APU:** no hay campo de dato que migrar (H-A8, H-A10).

### 7.3 Unidad (C-3, C-9)

La unidad no tiene una lista maestra en el código (la tabla `_ALIAS` solo unifica grafías, `core/contracts/unidades.py`). El combobox de unidad usa el **modo local** con una lista armada así: las unidades de
las partidas e insumos del caso + las de MaPreX + una **glosa fija** para las más comunes en `aplicacion/glosario.py` (`m` metro, `m2` metro cuadrado, `m3` metro cúbico, `pieza`, `unidad`, `dia`, `h`, `kg`, `saco`, `sg` suma global, `lt` litro, `env` envase, `rll` rollo, `sco` saco (MaPreX);
**las glosas de `lt`, `env`, `rll` y `sco` son mi lectura** de la abreviatura y las confirma Eugenio, D-11). Se acepta cualquier otra unidad escrita a mano **con el aviso**: «Esa unidad no está en la lista; si es la misma que otra con distinto nombre, el programa puede marcarla como diferente.»

### 7.4 Catálogo

K-1 se queda como filtro de tabla. Cambia solo el texto de ayuda en lenguaje llano («Escriba parte del nombre o del código para ver solo esas filas»). El Catálogo **no** muestra moneda ni fecha de la lista en v1: el `InsumoRespuesta` actual no las trae y mostrarlas exigiría una ruta más. Queda como mejora aparte (D-8).

### 7.5 Elaborar, Actualización, Control y resto

Reglas de §2.3, con las mismas piezas. Los combos de partida de **Elaborar** (E-3) son de modo local sobre la lista ya cargada (`partidasCiviles`); los de **Control** usan `ambito=proyecto`; **Histórico** y **Escenarios** usan insumos del presupuesto (E-ámbito `historico` / `presupuesto`, B4).

---

## 8. Pruebas por capa y oráculos

Todas con TDD de **rojo visto**, `-W error` en Python, sin `skip`/`xfail`. Los oráculos se escriben **a mano desde los CSV** (`data/precios/maprex_2026-07/referencia_*.csv`) y de la ERS, nunca desde el código bajo prueba.

### 8.1 Servidor (`tests/unit/test_api_busqueda.py`, `tests/unit/test_busqueda_aplicacion.py`)

| Prueba | Oráculo (escrito a mano) |
|---|---|
| Paridad con la búsqueda actual | para cada `q` de una palabra de `{"pvc","cable","cemento","retro","arena","tubo"}`, `buscar_referencia` (código existente) ⊆ nueva búsqueda, mismo `ref_maprex` (conjunto, no orden) |
| Todas las palabras | `q="tubo pvc"` (material) → exactamente `{PLOA38, ELE906}`; `q="pvc tubo"` → el mismo conjunto; `q="pvc"` → exactamente 6 referencias: `PLOA38, PLO035, PLO560, MT539, ELE906, ELE654` |
| Lo que hoy falla | `q="tuberia"` → `resultados: []` (no existe «tuberia» en la lista; hallazgo H-4) |
| Búsqueda por código MaPreX | `q="PLOA38"` material → 1.º `PLOA38`, descripción `TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA`, unidad `m`, `precio_alternativo` `8822.17` Bs y `precio` `13.9291` USD, fecha `2026-07-09` |
| Equipo con depreciación | `q="retroexcavadora"` equipo → `MOV027`, `factor_depreciacion` `"0.003500"`, `precio` `"110025.9187"` USD, `fila.depreciacion` `"0.003500"` |
| Mano de obra con código «raro» | `q="1-1.2"` mano_obra → `AYUDANTE - TABULADOR CONSTRUCCION -N2`, `precio_alternativo` Bs `1128.42`, `bono_bs` `3939.53`, fecha `2026-07-01` |
| Tabulador | `q="ingeniero"` mano_obra → exactamente 29 coincidencias en total, 20 devueltas con `hay_mas: true` (límite 20); la descripción truncada `INGENIERO CIVIL P-7 CIV (14 A 15 AÑOS DE EXP` sale **sin completar** |
| Relevancia | `q="PLO"` material → exactamente `PLO035, PLOA38, PLO560, PLO887, PLOG46`, en ese orden (todas rango 1 por código; desempate por descripción: CODO < TUBO < UNION < VALVULA CHECK < VALVULA PASO BOLA; comprobé a mano que ninguna otra fila de materiales contiene «plo») |
| Normalización | `q="TUBÓ"` y `q="tubo"` dan lo mismo; espacios sobrantes no cambian el resultado |
| Tope | `limite=51` → 422; `limite=0` → 422; `q` de 81 caracteres → 422 |
| Moneda del caso | con lista vigente en Bs, `fila.precio == "8822.17"` (no el USD); con lista en USD, `"13.9291"`; sin lista, USD |
| Sin lista vigente | grupo catálogo con `lista: null`; **no** 409 |
| Catálogo | insumo sembrado a mano con descripción, unidad y precio conocidos → aparece en `catalogo`, **no** en `maprex`, con la fecha y nombre de **su** lista |
| Separación de fuentes | `fuentes=catalogo` no trae el grupo MaPreX y viceversa; ninguna fila tiene `clave` repetida |
| Partidas | siembra de 3 partidas (`LB-01-EXC`, `LB-02-TUB`, `LB-05-REL`) → `q="tub"` devuelve solo `LB-02-TUB`; código sugerido en el dominio con estas tres = `LB-06`; con prefijos mezclados = `null` |
| Precarga ampliada | la partida existente devuelve `descripcion`, `unidad`, `dominio` de la base; una inexistente, los tres `null` |
| Permisos | `ana` (arma): 200 en todas; `rita` (revisa): 200 en `/partidas`, `/insumos`; 403 en `/proveedores`; sin sesión ni clave: 401; clave de API válida: 200 en las tres de lectura |
| `no-store` y sin eco | `Cache-Control: no-store` en 200, 401, 403, 422; el cuerpo del 422 no contiene el texto enviado (probar con `q` de 81 «X» y con `tipo=<script>`) |
| 503 | con la sesión forzada a `SQLAlchemyError`, 503 y el cuerpo no contiene `SELECT` ni la ruta de la base |
| Cadena de acceso | `test_api_acceso_por_ruta.py` gana las filas nuevas (texto exacto en §12) |

### 8.2 Aplicación y datos

- `test_busqueda_aplicacion.py`: el ranking por casos de §5.2 (rangos 0 a 4) y la deduplicación: las 111 filas tienen 110 referencias únicas; la repetida es `EFO001` (conté a mano) y debe salir una sola vez por (tipo, referencia).
- **Unidades MaPreX contra R3 (P-9):** componer con un material MaPreX en `sco` (unidad que no está en `_ALIAS`) y comprobar a mano si R3 lo marca; el resultado, sea cual sea, se anota en la bitácora (H-8). No es una prueba que "pase": es una **medición** con oráculo escrito antes de correrla.

### 8.3 Interfaz (Vitest + Testing Library, `fetch` simulado)

`CampoConBusqueda.test.tsx`:
- Mínimo de letras: con 1 carácter, **cero** peticiones; con 2, una tras 300 ms (temporizadores falsos).
- Debounce y carrera: teclear «t», «tu», «tub», «tubo» en 100 ms → **una** petición con `q=tubo`; respuesta tardía de «tu» llega después de la de «tubo» → se descarta; con `AbortController` simulado, se verifica `signal.aborted` en la petición vieja. En ningún instante hay dos peticiones abiertas.
- Teclado: `↓` abre y activa la 1.ª; `↓↓` la 2.ª; `Enter` entrega esa opción y **no** envía el formulario; `Esc` cierra; `Tab` no elige; `Alt+↓` abre sin mover.
- ARIA: el campo tiene `role=combobox`, `aria-expanded` verdadero/falso, `aria-controls` existente, `aria-activedescendant` que apunta al `id` de una opción presente; la opción activa tiene `aria-selected="true"` y las demás no.
- Región viva: sin foco no hay región; con foco y 12 resultados contiene «12 resultados…»; con 0, «Sin resultados para «x»»; **nunca** hay un `[role=status]` ni `[aria-live]` vacío en el documento (VB-18); el anuncio se emite **una vez** por búsqueda terminada.
- Estado vacío: se ve el título «No encontramos «x»» y los pasos del uso; el campo conserva lo escrito.
- Valor propio: con `valorPropio`, la última opción existe y al elegirla se llama `alUsar(texto)`; sin él, no existe.
- Escape: una descripción `<img src=x onerror=alert(1)>` y otra con `&lt;b&gt;` se muestran **literales**; no hay `img` en el DOM.
- Montos: un precio `"13.9291"` se ve `13,9291 USD`; un precio de 30 cifras se ve entero (sin pérdida): la prueba verifica el texto, y un barrido del archivo de código (`grep` en la prueba) prohíbe `Number(`, `parseFloat(`, `toFixed(` en `CampoConBusqueda*.ts(x)`.
- Errores: 401 → `alExpirar` llamado una vez; 403 → mensaje con el `detalle`; 422 → mensaje fijo sin eco; 503 → `detalle`; en todos el campo sigue editable.
- Foco: tras elegir, el foco está en el campo (o en la celda siguiente si el padre lo pide).
- Letra: con `--silice-escala-letra: 1.5` y ancho 1056 px, el `scrollWidth` del contenedor de la lista no excede su `clientWidth` (prueba de estilos al estilo de `estilosPlano.test.ts`; en jsdom solo se verifican las reglas CSS —`overflow-x`, `min-width: 0`—, no el pintado).

Pantallas (`componer/index.test.tsx` y nuevas):
- Elegir una partida existente rellena **cabecera** (descripción, unidad, dominio) y la bloquea; elegir «Crear una partida nueva» la habilita y muestra el aviso `partida_nueva`.
- Tras elegir `MOV027` en equipos, la fila queda con `descripcion`, `precio` `110025.9187`, `depreciacion` `0.003500` y el foco en Cantidad; la línea de procedencia dice «MaPreX jul-2026 · MOV027 · 09/07/2026».
- Borrar la fila 1 de 3 reajusta la procedencia de las otras dos.
- Escribir a mano un insumo sin pasar por el combobox → «Propio (escrito a mano)».
- La precarga **no** se dispara por tecla: teclear «LB-0» no llama `partida()`; elegir sí.
- Hoja: cotizar con 5 000 insumos filtra sin red; cambiar insumo usa E8 y respeta el tope de 300; proveedores sugiere de `/proveedores`.
- Regresión VB-18: `regionesVivasVacias.test.tsx` sigue verde con el componente nuevo.

### 8.4 Accesibilidad y letra (revisión humana, sesión de auditoría visual)

Con el programa corriendo (perfil propio del navegador, solo `127.0.0.1`): recorrido solo con teclado de Componer; lector de pantalla (NVDA, el que use Eugenio) leyendo el campo y una lista de 12; tres tamaños de letra (Normal/Grande/Muy grande) a 1366×768 y 1056 px sin desplazamiento horizontal de la página; contraste de la opción activa (≥ 4,5:1).
**No puedo afirmar que esto pase: es un criterio de aceptación a medir (P-14), no un resultado.**

### 8.5 Criterios de aceptación

| P | Criterio |
|---|---|
| P-1 | `CampoConBusqueda` cumple el patrón combobox ARIA 1.2 y las pruebas de §8.3 (teclado, `aria-activedescendant`, región viva con contenido, ninguna región vacía). |
| P-2 | `BuscadorReferencia` queda retirado y todo lo que su prueba cubría (busca, muestra la referencia, entrega la fila, vacío, 401, otros errores) lo cubre una prueba del componente nuevo. |
| P-3 | La búsqueda de insumos es un **superconjunto** de `buscar_referencia` para las consultas de §8.1 y halla por código; `q=tuberia` da vacío con el mensaje de ayuda. |
| P-4 | Los oráculos de §8.1 (`PLOA38`, `MOV027`, `1-1.2`, 29 «ingeniero», orden de `PLO`) pasan con rojo visto previo. |
| P-5 | Una sola petición en vuelo por campo, con aborto real y descarte de turnos viejos; demostrado con temporizadores falsos. |
| P-6 | Ningún monto pasa por `Number`, `parseFloat` ni `toFixed` en el componente, su lógica ni las pantallas tocadas (barrido en prueba); un precio de 30 cifras se ve íntegro. |
| P-7 | Todo texto de la API se pinta como texto; un nombre con `<img onerror>` se ve literal. |
| P-8 | Cada resultado y cada fila elegida muestran fuente, fecha y moneda; ningún resultado de una fuente lleva el rótulo de otra. |
| P-9 | Medición de las unidades MaPreX sin alias (`sco`, `env`, `lt`, `rll`) contra R3, anotada en la bitácora (sea cual sea el resultado). |
| P-10 | Elegir una partida existente rellena y bloquea la cabecera; se elimina la trampa de H-2 (prueba de pantalla + prueba de ruta). |
| P-11 | `GET /v1/buscar/*`: `no-store` en 200/401/403/422, 422 sin eco, 503 sin SQL, permisos por rol según §8.1. |
| P-12 | El 401 de cualquier búsqueda llama `alExpirar` una vez; 403/422/503 muestran su mensaje y el campo sigue siendo editable. |
| P-13 | Cada campo de §2 con clase A, B o C tiene ayuda en lenguaje llano y, donde se pide, un ejemplo ficticio; ninguna ayuda contiene «UC-», «RF-», «R3», «ref_maprex» ni jerga interna (barrido de textos en una prueba). |
| P-14 | A 1366×768 y 1056 px, con letra Normal, Grande y Muy grande, ni Componer ni la Hoja tienen desplazamiento horizontal de la página; recorrido con teclado y lector de pantalla hecho por una persona, con resultado escrito. |
| P-15 | Una moneda tecleada a mano ya no existe en Elaborar ni en Actualización (E-2, U-2): son `Select` Bs/USD. |
| P-16 | `git diff -- core/` vacío; `api/main.py`, `rutas.ts`, `docs/ERS.md`, `docs/api.json` y `CHANGELOG.md` solo los toca el orquestador con el texto de §12. |
| P-17 | `npx vitest run src/comun src/paginas/componer src/paginas/hoja`, `npm run lint` y `npm run build` limpios; `uv run --active pytest` de los archivos nuevos con `-W error`, `ruff check` y `ruff format` limpios. |

---

## 9. Sub-rebanadas, dependencias y agentes

```
F0 ─────────┐                      (prueba de viabilidad del ComboBox + `pedir` con `senal`)
B1 ─┐       ├─> F1 ──> F2 (Componer) ──> F3 (Hoja) ──> F4 (Elaborar/Actualización/Catálogo) ──> F5 (resto) ──> CIERRE
B2 ─┤       │
B3 ─┤───────┘  (B1-B3 en paralelo con F0/F1; F2 necesita B1+B2+B3; F3 solo B4 para proveedores)
B4 ─┘
```

| Rebanada | Qué entrega | Depende de | Paralelo con | Agente sugerido* |
|---|---|---|---|---|
| **F0** | (1) Prueba de viabilidad del `ComboBox` de Carbon en 3 puntos (§4.1) y decisión base/plan B en la bitácora; (2) `pedir` acepta `senal?: AbortSignal` (aditivo) con su prueba. *Toca `src/api/cliente.ts`: archivo compartido, lo hace el orquestador o con su visto bueno.* | — | B1-B4 | `javascript-typescript:typescript-pro` |
| **B1** | `aplicacion/busqueda.py`: normalización, ranking, `buscar_insumos_maprex` (con `precio_alternativo`, `fila` y moneda del caso); `GET /v1/buscar/insumos?fuentes=maprex`; sustituye internamente a `buscar_referencia` por una función compartida (DRY) sin cambiar `GET /v1/composicion/referencia` | — | F0, B2-B4 | `python-development:python-development-fastapi-pro` |
| **B2** | Fuente `catalogo` de insumos con su lista (`nombre`, `moneda`, `fecha`); `GET /v1/buscar/partidas` (ámbito `catalogo`) | B1 (módulo) | F0, B3 | ídem |
| **B3** | `PrecargaRespuesta` ampliada; `GET /v1/buscar/codigo-sugerido` | — | B1, B2 | ídem |
| **B4** | `GET /v1/buscar/proveedores`; `ambito=proyecto` de partidas e insumos (Histórico, Escenarios, Control) | B2 | F2 | ídem |
| **F1** | `CampoConBusqueda` + `logicaBusqueda.ts` + estilos + pruebas de §8.3 (con `fetch` simulado); sin pantallas | F0 | B1-B4 | `javascript-typescript:typescript-pro` + `sf-ingeniero-pruebas` (revisa que las pruebas no sean circulares) |
| **F2** | Componer: combobox de código, de descripción por tabla, procedencia, «Agregar insumo», precarga al elegir, cabecera bloqueada, ayudas C-2 a C-12; retira `BuscadorReferencia` | F1, B1, B2, B3 | B4 | ídem |
| **F3** | Hoja: cotizar (local), proveedor, cambiar insumo (E8), ayudas H-A* | F1 (y B4 solo para proveedor) | F2 (no comparten archivos) | ídem |
| **F4** | Elaborar (E-1..E-3), Actualización (U-1..U-3), Catálogo (K-1) | F1 | F3 | ídem |
| **F5** | Histórico, Escenarios, Control, Precios de la empresa, existencias, similares, índices, administración (ayudas y combos de §2.3) | F1, B4 | F4 | ídem |
| **CIERRE** | Barrido de textos (P-13), manual de usuario (`docs/manual_usuario.md`, sección «Cómo buscar»), auditoría visual con teclado y lector de pantalla (P-14), bitácora, árbitro de la entrega completa | F2-F5 | — | árbitro (`MANUAL_ARBITRO.md`) |

\* Los agentes `silice-*` que menciona la memoria del proyecto no los veo en la lista de este entorno; uso los tipos que sí existen. Cada rebanada pasa por el **árbitro**; máximo 3 rondas.

Cada rebanada entrega con su informe del manual §5 y **un commit por tarea** (Conventional Commits en español, asunto sin tildes, `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`). Ninguna rebanada toca los archivos compartidos del manual §2; su texto exacto va en §12.

**Orden recomendado y por qué:** F2 primero porque es lo que pidió Eugenio y donde está la trampa de H-2; F3 segundo porque reutiliza lo mismo y ya existe E8; F4/F5 son barrido y se pueden dividir entre agentes sin conflicto (no comparten archivos).

---

## 10. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R-1 | **La referencia MaPreX estructurada es chica (111 filas):** el autocompletado se sentirá pobre y la persona verá «no lo encuentro» a menudo. | El estado vacío lo explica con honestidad (§3.5); D-2 propone ampliar por demanda y con verificación; no se promete cobertura. |
| R-2 | El `ComboBox` de Carbon no sirve (regiones vivas vacías, `aria-activedescendant`, dos líneas). | F0 lo mide antes de construir; plan B (§4.2) con la misma interfaz pública. |
| R-3 | Rellenar el precio en la moneda equivocada (H-6) y producir un APU silenciosamente erróneo. | El servidor elige la moneda de la lista del caso; la procedencia muestra moneda; prueba de moneda (§8.1); D-7 pide el visto bueno de Eugenio. |
| R-4 | Unidades MaPreX sin alias hacen saltar R3 en un material legítimo (H-8). | Medición P-9; si ocurre, hallazgo para el tutor (tocar `core/` está fuera de este diseño). |
| R-5 | La precarga al elegir cambia un comportamiento que hoy se dispara al teclear: un caso que dependía de teclear el código completo deja de funcionar. | La entrada manual sigue disponible: escribir el código completo y salir con `Tab` hace la misma precarga (equivale a confirmar con el texto); prueba de pantalla. |
| R-6 | `RutaSinCache` + `RutaSinEco` en el orden equivocado (spec de la hoja §1.3 #7). | Prueba de 422 con `no-store` y sin eco en el mismo caso (§8.1); no lo probé. |
| R-7 | Tamaño de letra Muy grande: la lista de dos líneas por opción crece y tapa el campo de abajo. | Altura máxima `min(20rem, 60vh)` con desplazamiento interno; P-14 la mide. |
| R-8 | Un nombre de proveedor largo o con caracteres raros rompe la lista o inyecta HTML. | Texto de React siempre; `max-length` del dato; prueba P-7. |
| R-9 | Datos reales colados: un proveedor, una empresa o un libro reales en un ejemplo, una prueba o una captura. | Ejemplos solo de la lista ficticia (§6.1); el árbitro revisa (BLOQUEANTE si ve uno); las capturas de pantalla de la auditoría visual usan un caso de prueba. |
| R-10 | Mantener dos buscadores (`/referencia` y `/v1/buscar/insumos`) viola DRY. | B1 hace que ambos usen **la misma** función; `/referencia` se retira en un cambio aparte (D-8). |
| R-11 | La sugerencia de código se confunde con una regla («tengo que usar LB-06»). | Se rotula «Código sugerido (puede cambiarlo)» y el campo sigue siendo libre (§5.4, D-5). |

---

## 11. Decisiones abiertas para Eugenio (recomendación conservadora y reversible)

| D | Pregunta | Recomendación |
|---|---|---|
| D-1 | ¿Qué fuentes se ofrecen en v1? | **Catálogo del caso + referencia MaPreX + lista de la versión** (en la Hoja). **No** la lista de precios de la empresa (UC-17): es del administrador (`ADMINISTRAR_PRECIOS`) y mostrársela a quien arma cambia quién ve qué. Reversible: añadir una fuente es un grupo más. |
| D-2 | La referencia MaPreX estructurada tiene 111 renglones de ≈16 000; el README (regla 2) prohíbe el volcado completo. ¿Se amplía? | **No ahora.** Ampliar por demanda, por dominio y verificando cada fila a mano contra el PDF (como la sesión M0.2), cuando Eugenio o el tutor pidan una familia (tubería, cables…). El estado «no lo encuentro» lo anticipa. |
| D-3 | ¿Qué pasa si se escribe un **código de partida que no existe**? | **Se permite**, pero solo con la opción explícita «Crear una partida nueva con el código …» (nunca por omisión al salir del campo); sale el aviso `partida_nueva` que ya existe. Si la persona sale del campo sin elegir nada, el código queda escrito y el guardado tratará la partida como nueva **como hoy**; la diferencia es que ahora lo ve. |
| D-4 | ¿Se permite **crear un insumo nuevo** desde el combobox? | **No se crea nada en el catálogo desde el combobox.** Se permite un insumo «propio» (descripción libre, unidad y precio a mano), que el guardado ya registra como hoy (identidad tipo + descripción + unidad, `repositorio.py`). El combobox solo **elige o deja escrito**. |
| D-5 | ¿Se sugiere un código para una partida nueva? | **Sí, solo cuando el patrón del dominio es inequívoco** (§5.4) y siempre editable. Si Eugenio o el tutor tienen una convención de códigos para el producto, hay que decírnosla: hoy el código no tiene formato obligatorio. |
| D-6 | ¿Se guarda la **procedencia** de cada insumo (código MaPreX, fecha) dentro de la composición guardada? | **Diferir.** Exige tocar el esquema/`core/` (no hay columna) y el tutor debe avalarlo. En v1 la procedencia se ve en pantalla y se pierde al recargar (la ayuda lo dice). |
| D-7 | **Moneda del precio rellenado:** hoy MaPreX rellena USD (con tasa 633,3644 del 01/07/2026). ¿Se rellena en la moneda de la lista del caso (Bs exacto o USD)? | **Sí.** Evita un APU en la moneda equivocada. Eugenio confirma, porque cambia lo que ve quien ya usa MaPreX en USD. |
| D-8 | ¿Se retira `GET /v1/composicion/referencia` y se muestran moneda y fecha de la lista en el Catálogo? | Retirar `/referencia` **en un cambio aparte** tras fusionar F2. Moneda y fecha en el Catálogo: mejora separada (el `InsumoRespuesta` actual no las trae; §7.4). |
| D-9 | `Simulador`: insumos con selección múltiple (SI-1). | **Diferir**; el texto con comas se queda con ejemplo hasta que haga falta. |
| D-10 | **Sinónimos** (tubería → tubo). | v1: solo el mensaje de ayuda. Más adelante, una lista curada pequeña y verificada. |
| D-11 | **Unidades:** la lista tiene glosa fija; las glosas de `lt`, `env`, `rll`, `sco` son lectura mía. ¿Se amplía la tabla de alias de `core/contracts/unidades.py` para MaPreX? | Confirmar las glosas. **No tocar `core/`** aquí; si P-9 muestra un falso positivo de R3, se lleva al tutor como cambio de núcleo con expediente. |
| D-12 | **Proveedores sugeridos** del mismo proyecto. | **Sí**, solo del proyecto de la persona (sin otros proyectos ni casos). |

---

## 12. Texto exacto para los archivos compartidos (lo aplica el orquestador)

1. **`api/main.py`:** `from api.rutas import busqueda` y `app.include_router(busqueda.router)` (junto al resto de los routers de `/v1`).
2. **`tests/unit/test_api_acceso_por_ruta.py`:** filas (ruta, método, acción) —
   `/v1/buscar/insumos` GET `LEER_PROYECTO`; `/v1/buscar/partidas` GET `LEER_PROYECTO`; `/v1/buscar/codigo-sugerido` GET `LEER_PROYECTO`; `/v1/buscar/proveedores` GET `EDITAR_HOJA`.
3. **`tests/unit/test_arquitectura.py`:** `aplicacion/busqueda.py` y `aplicacion/glosario.py` no importan `streamlit`, `ui`, `api`, `scripts` ni `tests` (RM-1); `api/rutas/busqueda.py` no importa `ui`, `scripts` ni `tests`. Si la prueba enumera módulos, añadirlos.
4. **`docs/ERS.md`:** una enmienda «Autocompletado guiado de campos (Sílice 1.2.x)» que **reserve** (el orquestador confirma la numeración libre al aplicarla): **RF-147** «Los campos que piden un dato que la persona no tiene por qué saber de memoria (código de partida, insumo, unidad, moneda, proveedor) ofrecen una búsqueda con autocompletado sobre el catálogo del caso, la referencia MaPreX o la lista de la versión, con la fuente, la fecha y la moneda de cada resultado a la vista; el precio sugerido queda editable»; **RF-148** «Al elegir una partida existente en Componer, su cabecera se rellena y no se edita»; y **RNF-29** «La búsqueda con autocompletado es operable solo con el teclado y por lector de pantalla, con tres tamaños de letra, sin desplazamiento horizontal a 1366×768 y 1056 px». Enmienda a UC-10 paso 1 y flujos 2b/3b/4b (buscador integrado en la celda). La matriz de trazabilidad (§4) gana las dos filas.
5. **`docs/api.json`:** regenerar con `scripts/exportar_openapi.py` (rutas `/v1/buscar/*` y los tres campos nuevos de `PrecargaRespuesta`).
6. **`CHANGELOG.md`:** «Añadido: autocompletado guiado de campos (`CampoConBusqueda`, `GET /v1/buscar/*`); Componer rellena la cabecera de la partida elegida; el buscador MaPreX de Componer pasa a la celda de cada insumo.»
7. **`frontend-desktop/DESIGN.md`:** nueva sección «Campos con búsqueda» (dos líneas por opción, código en Plex Mono, fuente y fecha siempre visibles, estado «no lo encuentro», región viva solo con contenido).
8. **`frontend-desktop/src/api/cliente.ts`:** `senal?: AbortSignal` en `OpcionesDePeticion` y `signal: opciones.senal` en el `fetch` (F0; aditivo).
9. **`frontend-desktop/src/shell/rutas.ts`:** sin cambios (no hay página nueva).

---

## 13. Lo que no pude determinar

- **Cómo se comporta el `ComboBox` de Carbon 1.117.0** (regiones vivas, `aria-activedescendant`, dos líneas, grupos): no lo ejecuté. F0 lo mide (§4.1).
- Si `RutaSinCache` + `RutaSinEco` combinan bien en el orden propuesto (la spec de la hoja lo afirma; no lo probé).
- **Qué función de `aplicacion/`** da hoy las partidas de un presupuesto por versión (para `ambito=proyecto`) y la consulta exacta de proveedores en cotizaciones: no las leí (B4 las localiza).
- Si R3 marca como diferentes las unidades MaPreX sin alias (`sco`, `env`, `lt`, `rll`): medición P-9.
- Si el sistema valida de algún modo el formato del código de una partida: no encontré validación en lo que leí, pero no leí `composicion_desde_tablas` (líneas 219-267) entero.
- La glosa correcta de `lt`, `env`, `rll` y `sco`: es mi lectura de las abreviaturas (D-11).
- Si la referencia repetida `EFO001` es la misma fila en dos archivos o dos filas distintas con el mismo código: no lo miré; B1 lo decide al escribir la prueba de deduplicación.
- Cuántas partidas e insumos tiene un caso real: no hay un caso real en el repositorio (y no debe haberlo); el diseño supone catálogos de cientos, no de decenas de miles, y por eso el límite de 20 y el filtrado en el servidor.
