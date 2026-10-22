# Autocompletado guiado de campos en la interfaz nueva: diseño del componente `CampoConBusqueda` y su contrato

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-adm-empresa` (base `4ad4c576`) · **Estado:** PROPUESTO, **ronda 2** (corrige los 9 MAYOR y 9 MENOR de la ronda 1 del árbitro). Lo juzga el árbitro
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
   (`catalogo/index.tsx:43-58`, `filtro.ts`). Hace falta un contrato nuevo de búsqueda (§5): `GET /v1/buscar/insumos`,
   `/partidas`, `/partidas-linea-base`, `/codigo-sugerido`, `/unidades`, `/insumos-con-historial` y `/proveedores`, con límite por grupo, orden por relevancia, `no-store` y sin eco.
6. **Tres fuentes que nunca se mezclan en una misma fila ni se rotulan igual:** «Catálogo de este caso» (insumos y partidas ya
   guardados, con el precio de la lista vigente a la fecha de la pantalla), «MaPreX jul-2026» (referencia de mercado, solo lectura,
   fechada, con la tasa de conversión a la vista) y, en la Hoja, «Lista de precios de esta versión». Cada resultado lleva su fuente, su
   fecha y su moneda a la vista. La lista de precios de la empresa (UC-17) **no** se ofrece a quien arma en v1 (D-1).
7. Un solo componente, `CampoConBusqueda`, **propio**, sobre `CampoTexto` con el patrón combobox ARIA 1.2. El `ComboBox` de Carbon 1.117.0
   se descartó como base por la evidencia de la ronda 1 del árbitro (§4.1). Cuesta más (≈ 500 líneas con sus pruebas, estimación mía), y por
   eso la rebanada F0 verifica antes, en jsdom y en un navegador real, lo que jsdom no puede medir (§4.3).
8. Montos **siempre como texto**: el precio se muestra con `formatoEsVe` (sin `Number`, `parseFloat` ni `toFixed`), el texto de la
   API se pinta como texto de React (nunca HTML), y el `fila` que rellena la tabla lo arma el servidor (como hoy).
9. Texto de ayuda en lenguaje llano en **cada** campo de §2, con ejemplo ficticio. Ninguna ayuda dice «UC-10», «ref_maprex» ni «R3».
10. Se escribe lo que se pide, no lo que el sistema supone: un código de partida que no existe **no se acepta en silencio**. Queda en
    un estado «escrito, sin confirmar» y **Guardar se deshabilita con el motivo a la vista** hasta que la persona elija una partida de la lista
    o confirme «Crear una partida nueva con el código …» (§7.1, D-3). Un insumo que no está en ninguna fuente sí se puede dejar escrito a
    mano: queda marcado «Propio» (D-4).
11. Diez sub-rebanadas (§9): backend B1-B4 y front F0-F5 con cierre; Componer primero (F2), luego Hoja (F3), Elaborar/Actualización/Catálogo (F4) y el
    resto (F5, solo los campos cuya fuente de datos está verificada). La coordinación con los otros dos diseños del día está en §0.1.
12. Pruebas por capa con oráculos escritos a mano desde los CSV de MaPreX (códigos reales `PLOA38`, `MOV027`, `1-1.2`), accesibilidad
    con lector de pantalla simulado, carrera de peticiones y estados 401/403/422/503 (§8).

### 0.1 Coordinación con los otros diseños del día

- **Bienvenida y ayuda** (`2026-10-21-bienvenida-casos-proyectos-design.md`): su sub-rebanada BCP-8 añade `<AyudaDePagina />` bajo el `h1` de **cada**
  página y espera a que termine este trabajo, porque ambos tocan `componer/`, `hoja/` y `catalogo/`. Su glosario vive en `src/ayuda/glosario.ts`; por eso aquí
  el módulo de unidades se llama `aplicacion/unidades_glosa.py` y no `glosario`. Las ayudas de campo de este diseño (`helperText`) y el «qué hace esta página» de
  aquel no se pisan: uno está en el campo, el otro bajo el título.
- **Asistente en la hoja** (`2026-10-21-hoja-asistente-ia-design.md`): reescribe `hoja/index.tsx`, `hoja/useBorrador.ts` y los mocks de `hoja/Hoja.test.tsx`. F3 **no**
  toca esos tres; trabaja en `OperacionesDePrecios.tsx`, `CambioDeInsumo.tsx` y `ConvertirMoneda.tsx` con pruebas propias nuevas, y se coordina con el
  orquestador el orden de fusión si ambos cambian `Hoja.test.tsx`.
- **`api/main.py`:** el orquestador añade `from api.rutas import busqueda` y `app.include_router(busqueda.router)` **antes de B1** (con el router vacío), para que B1 a B4 no
  editen el archivo compartido. Se coloca junto a los demás routers de `/v1` (después de `produccion.router`, `api/main.py:132`).
- **Contrato compartido entre servidor y mocks:** `docs/api_ejemplos/buscar/` guarda, escritos a mano desde los CSV, los JSON de respuesta de referencia
  (`insumos_maprex.json`, `partidas.json`, `unidades.json`). Las pruebas del servidor comparan la respuesta con ellos y los mocks de F1 los importan; si Vitest no
  puede importar fuera de `src/`, F1 guarda una copia y una prueba del servidor (`test_ejemplos_buscar_sincronizados`) comprueba que ambas son idénticas. Así
  los mocks no se desvían del contrato.

---

## 1. Hallazgos que cambian el diseño (verificados por lectura)

| # | Hallazgo | Consecuencia |
|---|---|---|
| H-1 | «Código» en Componer es el de la **partida**: `componer/index.tsx:202-208`, `labelText="Código"` sin ayuda ni lista. La tabla de insumos no tiene columna de código (`tablas.ts` `COLUMNAS`: descripción, unidad, consumo, precio…). | El combobox de código es de **partidas**; los de insumo buscan por **nombre o por código MaPreX**, sin pedir un código del catálogo. |
| H-2 | Un código existente con cabecera distinta se rechaza al guardar: «la cabecera de una partida existente no se edita desde esta pantalla. Escriba la descripción registrada o use otro código» (`aplicacion/composicion.py:420-435`). `precargar` solo devuelve tablas y rendimiento (`api/rutas/composicion.py:248-252`, `PrecargaRespuesta`). Además `precarga_de_partida` responde `existe=False` para una partida que **sí existe** pero no tiene lista vigente (`aplicacion/composicion.py:1062-1063`, `except (KeyError, CatalogoIncompleto)`), y para una que no existe: la interfaz no puede distinguirlas. | La respuesta de precarga se **amplía** (§5.5): `descripcion`, `unidad`, `dominio` siempre que la partida exista, y `existe` pasa a significar «está en el catálogo» con un campo nuevo `tiene_composicion_vigente`. Si la partida existe, la cabecera queda **de solo lectura** con su explicación. |
| H-3 | La precarga se dispara con **cada código parcial** tecleado (`componer/index.tsx:106-128`, pausa de 300 ms). Con un combobox, cada letra sería una consulta y una precarga posible. | La precarga pasa a dispararse al **elegir o confirmar** un código, no al teclear. |
| H-4 | Buscador MaPreX actual: `buscar_referencia` hace `objetivo in normalizar_texto(fila["insumo"])` (`aplicacion/composicion.py:487-533`): la frase entera debe aparecer **contigua**; solo busca en la descripción; devuelve las filas «en el orden de los archivos», sin límite. Corrida a mano contra los CSV: `tuberia` → 0 filas (la lista dice «TUBO»); `tubo pvc` → 2 (`PLOA38`, `ELE906`); `pvc` → 6. | La búsqueda nueva exige **todas las palabras** (como `coincide` del Catálogo, `catalogo/filtro.ts`), en cualquier orden, busca en descripción **y código MaPreX**, ordena por relevancia y limita. Es un **superconjunto** de la actual (paridad §8.1). |
| H-5 | La fila que entrega el buscador (`fila_*_desde_referencia`, `aplicacion/composicion.py:554-596`) trae solo descripción, unidad, precio (y depreciación o sueldo). El `ref_maprex` se muestra en `BuscadorReferencia.tsx:88` y **se pierde** al usar la fila. | El componente guarda la **procedencia** de cada fila elegida (código MaPreX, fecha, moneda, fuente) en el estado de la página y la muestra bajo la celda (§6). Persistirla en la composición guardada exige tocar el esquema: D-6 (diferido). |
| H-6 | El precio que rellena el buscador es `precio_usd` (`fila_materiales_desde_referencia`: `str(fila.precio_usd)`), derivado de bolívares con la tasa 633,3644 del 01/07/2026 y redondeado a 4 decimales (`README.md` de MaPreX). La lista de precios del caso tiene su propia moneda (`ListaPrecios.moneda`, `core/models/entidades.py:196`). | Si la lista vigente del caso está en Bs, rellenar USD sería un error silencioso. El servidor rellena en **la moneda de la lista vigente**: `precio_bs` (exacto, tal como lo imprime el PDF) o `precio_usd`; ambas se **muestran** (D-7). |
| H-7 | Referencia MaPreX estructurada: 111 filas = 40 materiales, 19 equipos y 52 de mano de obra. 59 llevan fecha 2026-07-09 (materiales y equipos) y las 52 de mano de obra, 2026-07-01; **de esas 52, 43 son el tabulador CIV**. Los PDF (≈16 000 renglones) no se consultan. La descripción del tabulador viene **truncada** en algunas filas («… (14 A 15 AÑOS DE EXP»; README). | La lista se muestra tal cual, sin completar descripciones; el estado vacío explica el alcance real (§3.5). |
| H-8 | Unidades de MaPreX en la referencia: `dia`, `pza`, `und`, `m`, `m3`, `env`, `lt`, `sco`, `rll`, `sg`. Solo algunas están en la tabla de alias (`core/contracts/unidades.py`: `pza`→`pieza`, `und`→`unidad`, `sg`); **`env`, `lt`, `sco` y `rll` no son alias de nada**. La regla R3 (coherencia dimensional) compara unidades. | No lo probé contra R3. El plan incluye una prueba de oráculo (§8.2, P-9) y, si R3 marcara una unidad MaPreX legítima, se **anota como hallazgo** (no se toca `core/` aquí; D-11). |
| H-9 | Catálogo: `GET /partidas` y `GET /insumos` (`api/rutas/catalogo.py`) devuelven todo; `InsumoRespuesta` trae `precio_vigente` pero **no** la moneda, la fecha ni el nombre de la lista. | El contrato nuevo devuelve precio **con** moneda, fecha y nombre de la lista (§5.3). Los dos GET existentes no cambian. |
| H-10 | La Hoja ya tiene búsqueda de insumos de **una versión abierta** (`GET /v1/hoja/borradores/{id}/insumos`, E8, `api/rutas/hoja.py:717`): `texto` en la descripción, a lo sumo 300, ordenado por descripción, 409 sin versión abierta. La interfaz la usa con un campo de búsqueda **más** un `Select` nativo (`hoja/CambioDeInsumo.tsx:142-171`). Cotizar usa un `Select` nativo con **todos** los insumos de la lista (`hoja/OperacionesDePrecios.tsx:73-77`). | Cambiar de insumo **reutiliza E8** (cero backend nuevo). Cotizar filtra en el navegador la lista que la pestaña ya cargó (modo local del componente). |
| H-11 | No existe ningún `ComboBox`, `datalist` ni autocompletado en el front (`grep` de `ComboBox\|FilterableMultiSelect\|Dropdown\|Autocomp\|datalist` en `src/**/*.tsx` → ningún componente propio). Carbon 1.117.0 trae `ComboBox`, pero la ronda 1 del árbitro mostró, sobre Carbon 1.117.0 y downshift 9.4.0, que **no sirve como base** (§4.1). Yo no lo ejecuté. | Es un componente propio nuevo en `src/comun/`. Lo que jsdom no puede medir (posición del menú en una celda, letra Muy grande) se verifica en navegador real en F0 (§4.3). |
| H-12 | Regla VB-18: `TextInput` y `TextArea` de Carbon solo se importan en `comun/CampoTexto.tsx` y `AreaTexto.tsx`; `comun/regionesVivasVacias.test.tsx` lo vigila por ruta exacta porque montan un `<span role="alert" aria-live>` vacío por campo. | `CampoConBusqueda` **no puede importar `TextInput`**. Por eso el componente es propio sobre `CampoTexto` (§4) y su región viva existe **solo con contenido** (§3.6). |
| H-13 | `pedir` (`src/api/cliente.ts`) no acepta `AbortSignal`: `fetch(ruta, { method, headers, body, credentials })`, y su `catch` convierte **cualquier** fallo de `fetch` en `ErrorDeApi(0, "No se pudo hablar con el programa de Sílice…")` (`cliente.ts:68-72`). Un aborto deliberado se mostraría como un servidor caído. Los buscadores actuales descartan por «turno» (`BuscadorReferencia.tsx:26-47`), pero la petición vieja sigue viva. | «Una sola petición en vuelo» necesita que `pedir` acepte `senal?: AbortSignal` (aditivo) **y** que ante un aborto relance el `AbortError` original sin envolverlo en `ErrorDeApi` (prueba P-20). |
| H-14 | Acceso: `/v1/composicion/*` exige `EDITAR_HOJA` (arma); `GET /partidas` e `/insumos`, `LEER_PROYECTO` (arma y revisa); `GET /v1/precios-empresa` exige `ADMINISTRAR_PRECIOS` (`api/acceso.py`, `precios_empresa.py:73-77`). | El buscador hereda la acción de la pantalla que lo usa (§5.1). Las listas de la empresa no se exponen a quien arma. |
| H-15 | Códigos de insumo asignados: `PREFIJO-NNN` (`repositorio.py:455-464`); variantes con sufijo si el precio difiere (`_codigo_variante`). Partidas de prueba usan `LB-01-EXC`, `LB-02-TUB` (`tests/fixtures/apu_linea_base.py`). El sistema **no impone** un formato al código de una partida (no encontré validación; no leí `composicion_desde_tablas` entera). | La sugerencia de código (§5.4) es una **ayuda**, nunca una regla. |
| H-16 | El buscador de la Hoja (E8, `candidatos_de_insumo`, `aplicacion/hoja_edicion.py:384-395`) busca `texto` **solo en la descripción**, ordena por descripción y no por relevancia, y no busca por código. | Cambiar insumo (H-A6) gana el combobox y la lista de resultados, **no** la relevancia ni la búsqueda por código: diferencia declarada. Mejorar E8 (aditivo) queda como mejora aparte. |
| H-17 | Acceso real (`seguridad/permisos.py:58-64`): `LEER_PROYECTO` = arma y revisa; `EDITAR_HOJA` y `CONTROL_DE_OBRA` = solo arma; el **administrador no tiene ninguna de las tres**. Las pantallas de Control usan `CONTROL_DE_OBRA`. Las rutas de control resuelven el proyecto con `_existe` (`api/rutas/control.py:66-72`), cuyo 404 **repite el nombre** que llegó. | Cada ruta de búsqueda declara su acción (§5.1); el administrador recibe 403 en todas; las que reciben `proyecto` devuelven un 404 de mensaje fijo, sin repetirlo (no se reutiliza `_existe`). |
| H-18 | Los insumos del catálogo **no llevan depreciación**: vive en la línea de la composición (`core/models/entidades.py:116`, `ComposicionAPU.depreciacion`; `Insumo` no la tiene). Solo MaPreX la trae (`factor_depreciacion`). | Un equipo elegido del catálogo rellena `depreciacion` en **blanco** y la persona la declara (la ayuda de C-10 la explica); uno de MaPreX la rellena. |
| H-19 | Origen de los datos de las pantallas de Control, Histórico y Escenarios (lo que pidió el árbitro verificar): las partidas **de la línea base** salen de `instantanea_control(sesion, proyecto, catalogo=…).presupuesto.partidas[].item.codigo_partida` (`aplicacion/control.py:436-440`); las de **un presupuesto de la versión**, de `cargar_presupuesto` (`core/budget/persistencia.py:255`, la misma que sirve `GET /presupuestos/{codigo}`); los insumos con historial de precio, de `cambios_precio` (`core/catalog/precios.py:575`, que compara la descripción **exacta**). **No encontré** una función que dé los insumos de un presupuesto (Escenarios). | Define HI-1, CO-1 y CO-2 (§5.4, §5.8) y **retira ES-1** de F5 hasta que B4 fije su fuente. |
| H-20 | `buscar_referencia` la usan `scripts/simular_corpus.py` (líneas 99, 110 y 112) y la reexportación de `ui/composicion.py:14,37`, además de `sugerencias_de_referencia`. | **Se deja intacta** (m-3): la búsqueda nueva es otra función; ambas leen los CSV con un lector común (§5.2). |

---

## 2. Inventario de campos que piden un dato que la persona no tiene por qué saber de memoria

**Clases:** **A** = autocompletado (búsqueda en catálogo, MaPreX o lista de la versión; usa `CampoConBusqueda`); **B** = lista
cerrada o corta con ayuda en lenguaje llano (el campo ya es un `Select`, o debe serlo); **C** = texto libre, con ejemplo y ayuda
(`helperText`), sin búsqueda; **D** = ya correcto, solo se revisa el texto. «Rebanada» remite a §9.

### 2.1 Componer una partida (`componer/`)

| Id | archivo:línea | Campo (rótulo hoy) | Qué se le pide hoy | Clase | Qué pasa en el diseño nuevo | Reb. |
|---|---|---|---|---|---|---|
| C-1 | `index.tsx:202-208` | Código | Un código de partida, en blanco, sin ayuda | **A** | Combobox de **partidas del catálogo**; al elegir una existente rellena descripción, unidad, dominio, tablas y rendimiento y bloquea la cabecera; si no hay coincidencia ofrece «Crear una partida nueva con el código …» y una sugerencia de código. La cabecera tiene **cuatro estados** y Guardar depende de ellos (§7.1) | F2 |
| C-2 | `index.tsx:209-218` | Descripción | Texto libre | **C** (+ ayuda existente «Similares») | Ejemplo y ayuda: «Qué se hace, en una frase». Si la partida existe: solo lectura | F2 |
| C-3 | `index.tsx:219-225` | Unidad | Texto libre («m3», «m²»…) | **A/B** (lista con valor libre) | `CampoConBusqueda` sobre `GET /v1/buscar/unidades` (unidades del caso + MaPreX + glosa); se acepta otra con aviso (§7.3) | F2 |
| C-4 | `index.tsx:226-236` | Dominio | `Select` civil/telecom/industrial/sistemas | **B** | Se queda; se añade ayuda («el tipo de obra; define con qué partidas se compara») | F2 |
| C-5 | `index.tsx:237-247` | Fecha | Fecha | **D** | Ayuda: «Desde cuándo vale esta composición» | F2 |
| C-6 | `index.tsx:260-266` | Rendimiento: unidades por día | Un número | **C** | Ayuda llana + ejemplo: «Cuánta obra hace la cuadrilla en un día. Ejemplo: 12 m de tubería por día». Ya existe la propuesta del histórico | F2 |
| C-7 | `index.tsx:274-283` | Condiciones del rendimiento | Texto obligatorio | **C** | Ejemplo: «Cuadrilla de 1 maestro y 2 ayudantes, terreno plano, clima seco» | F2 |
| C-8 | `TablaInsumos.tsx:68-74` (celda `descripcion`) | Descripción, fila n (materiales, equipos, mano de obra) | Texto libre por celda; el buscador está aparte (`BuscadorReferencia.tsx:63-69`) | **A** | La **celda de descripción** pasa a ser un combobox (catálogo + MaPreX por tipo). `BuscadorReferencia` desaparece (§7.1) | F2 |
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
| H-A9 | `ConvertirMoneda.tsx:57`, `:64`, `:74` | Moneda destino; Tasa del BCV; Por qué se cambia (fuente) | `Select`; `Select` con ayuda «Por omisión, venta.» (`:65`); texto. El diálogo ya dice «Se usa la tasa del BCV de hoy» (`:47`) | **B/B/C** | La ayuda de la tasa se amplía a «Venta o compra: la tasa del BCV de hoy; por omisión, la de venta.» (verificado contra el código: no se promete nada que el diálogo no haga); ejemplo en la fuente | F3 |
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
| HI-1 | `historico/index.tsx:61-67` | Insumo (descripción exacta) | Texto: hay que escribir la descripción **exacta** (`cambios_precio` compara por igualdad, `core/catalog/precios.py:593-594`) | **A** | Combobox de `GET /v1/buscar/insumos-con-historial` (§5.8): solo insumos con al menos un cambio de precio; al elegir se escribe la descripción exacta | F5 |
| ES-1 | `escenarios/index.tsx:289-296` | Insumo (descripción exacta), por fila | Texto exacto | **C** (se queda) | **Retirado de F5** hasta que B4 fije su fuente: no encontré una función que dé los insumos de un presupuesto (H-19). Mientras tanto conserva su ejemplo (`escenarios/logica.ts:20`, `EJEMPLO_PRECIOS`) | — |
| SI-1 | `simulador/index.tsx:116-123` | Insumos («separados por coma; vacío = todos») | Texto con comas | **A** (múltiple) | Combobox de selección múltiple; diferido (D-9) | — |
| CO-1 | `control/PestanaValuaciones.tsx:59` | Partida n (valuación) | Texto | **A** | Combobox de las partidas **de la línea base** del proyecto (`GET /v1/buscar/partidas-linea-base`, §5.4; acción `CONTROL_DE_OBRA`) | F5 |
| CO-2 | `control/PestanaValuaciones.tsx:201` | Partida (opcional) del costo real | Texto (`codigo_partida` opcional, `core/models/control.py:167`) | **A** | Igual que CO-1; el campo sigue siendo opcional y se puede dejar vacío | F5 |
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
  clave: string;          // estable y única en toda la lista: "catalogo:INS-004", "maprex:material:PLOA38"
  principal: string;      // línea 1: lo que la persona reconoce (la descripción)
  secundaria: string[];   // línea 2: [código, unidad, precio con moneda, fuente y fecha], ya como texto
  valor: T;               // lo que recibe el padre al elegir
}
interface GrupoDeResultados<T> {
  rotulo: string;         // "Del catálogo de este caso", "Referencia MaPreX jul-2026"
  opciones: OpcionDeBusqueda<T>[];
  hayMas: boolean;        // viene del servidor, POR GRUPO (§5.1)
  aviso?: string;         // p. ej. "La lista del caso está en …": texto fijo del servidor
}

interface Props<T> {
  id: string;
  etiqueta: string;                 // visible siempre, lenguaje llano ("Código de la partida")
  ayuda?: string;                   // `helperText` bajo el campo, con ejemplo
  texto: string;                    // el texto del campo: lo controla la PÁGINA, no el componente
  alCambiarTexto: (texto: string) => void;
  // Exactamente una de las dos fuentes de opciones:
  buscar?: (q: string, senal: AbortSignal, limitePorGrupo: number) => Promise<GrupoDeResultados<T>[]>;
  opciones?: OpcionDeBusqueda<T>[]; // modo local (lista ya cargada): filtra en el navegador
  alElegir: (opcion: OpcionDeBusqueda<T>) => void;
  valorPropio?: {                   // ofrece una última opción: usar lo escrito tal cual
    rotulo: (texto: string) => string;   // "Crear una partida nueva con el código «LB-06»"
    alUsar: (texto: string) => void;
  };
  vacio: { titulo: string; pasos: string };  // "¿No lo encuentra?" + qué hacer (§3.5)
  minimoDeLetras?: number;          // 2
  pausaMs?: number;                 // 300 (el mismo retardo que los demás buscadores de la interfaz)
  limiteInicial?: number;           // 8 por grupo; «Ver más resultados» pide 20 (§3.3-5)
  enCelda?: boolean;                // true: la lista se pinta en un portal con `position: fixed` (§3.7)
  alExpirar: () => void;            // 401 → cerrar sesión, como los demás buscadores
  invalido?: boolean; textoInvalido?: string;
  deshabilitado?: boolean; soloLectura?: boolean;
  tamano?: "sm" | "md";             // "sm" por omisión
}
```

El campo lleva `maxLength={80}` (el tope de `q` del servidor, §5.1). La API del componente **no** trae montos como `number`: `secundaria` ya llega como
texto formateado por el padre con `formatoEsVe` (que es sobre cadenas, `formatoEsVe.ts:5-12`). El componente **no guarda `inputValue` propio**: lo
escrito es la prop `texto`.

### 3.3 Comportamiento

1. **Mínimo de letras:** con menos de 2 caracteres no se pide nada; la región de estado dice «Escriba al menos 2 letras o un código» (§3.6).
2. **Pausa (debounce):** 300 ms tras la última tecla (el mismo `RETARDO_MS` de `BuscadorReferencia.tsx:17` y de `componer/index.tsx:20`).
3. **Una sola petición en vuelo:** `useRef` con un `AbortController` y un contador de turno. Al llegar un texto nuevo: si hay una
   petición en curso se **aborta** (`senal`, §9 F0) y se programa la siguiente; la respuesta de un turno viejo se descarta aunque
   no se haya podido abortar (defensa doble, como hoy). El `AbortError` se ignora (no es un error que mostrar). Nunca hay dos solicitudes simultáneas del mismo campo.
4. **Texto normalizado en el servidor**, no en el navegador; el navegador solo recorta espacios de los bordes. (El modo local usa
   `coincide`/`normalizar` de `catalogo/filtro.ts`, que se mueve a `comun/` sin cambiar su comportamiento; es una función pura ya probada.)
5. **Límite: una sola regla, por grupo.** El parámetro `limite` del servidor es **por grupo** (por omisión 20, tope 50) y `hay_mas` también es por grupo (§5.1).
   El componente pide `limite=8` y muestra hasta 8 opciones por grupo; si un grupo trae `hayMas`, bajo ese grupo (dentro de la lista, pero **no** como opción)
   hay un botón «Ver más resultados» que repite la misma búsqueda con `limite=20`. Con 20 y `hayMas`, se muestra «Hay más resultados: escriba más letras para acotar».
6. **Orden:** el que manda el servidor (relevancia, §5.2). El componente no reordena.
7. **Elegir:** `Enter` elige **solo si la persona navegó con las flechas** hasta una opción (hay opción activa); sin opción activa, `Enter` no elige nada y no
   cambia el texto (con la lista cerrada sigue su curso normal en el formulario). Un clic sobre una opción también elige. Al elegir se llama `alElegir(opcion)`,
   el padre decide qué texto queda en el campo, se cierra la lista y el foco sigue en el campo. El componente **nunca** elige por su cuenta la primera sugerencia.
8. **Escribir sin elegir:** al salir (`Tab`/clic fuera) el texto queda **tal cual** (ni se restaura ni se borra) y el componente avisa al padre solo con
   `alCambiarTexto`. Qué significa ese texto lo decide la pantalla: en Componer es el estado «escrito, sin confirmar» (§7.1).
9. **`Esc`:** primero cierra la lista; con la lista ya cerrada y un valor elegido, pide al padre limpiar (`alCambiarTexto("")`). Un botón «Borrar» (icono con nombre accesible) hace lo mismo con el ratón.
10. **Errores:** 401 → `alExpirar()`; 403 → aviso en la propia lista «Su cuenta no puede usar esta búsqueda» (detalle de la API tal cual);
    422 → «La búsqueda no es válida: escriba otra cosa» (mensaje fijo, sin repetir lo escrito); 503 y red caída (`estado` 0) →
    el `detalle` de la API; el campo **sigue siendo de texto libre**: un error de búsqueda no impide teclear ni guardar lo escrito.

### 3.4 Lo que se muestra en cada opción

Dos líneas, sin tabla (la lista cabe en 1056 px; §3.6):

```
TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA                 ← principal (cuerpo, 16 px con la letra Normal)
PLOA38 · m · 13,9291 USD · MaPreX jul-2026 · 09/07/2026      ← secundaria (etiqueta, IBM Plex Mono solo en el código)
```

- El **código** va en Plex Mono (DESIGN.md: «IBM Plex Mono para referencias de celda y códigos»).
- El **precio** va como `formatoEsVe(precio) + " " + moneda`, exacto tal como llega (sin redondear). Si la API manda dos
  monedas (MaPreX), se muestra **la de la lista del caso** y la otra queda en la descripción accesible (`aria-describedby`).
- **Fuente y fecha siempre visibles** (nunca solo en un `Tooltip`); la fecha como `dd/mm/aaaa`, construida **troceando la cadena**
- **Conversión a la vista:** un precio MaPreX en USD no es un dato del PDF, es `precio_bs / tasa` redondeado a 4 decimales. La línea de procedencia de la fila elegida lo
  dice: «13,9291 USD · precio del 09/07/2026 · convertido a 633,3644 Bs/USD del 01/07/2026». Si la lista del caso está en Bs se muestra el precio en Bs, que es el del PDF, y no hay conversión. En la lista de
  resultados la tasa va en la descripción accesible de la opción (`aria-describedby`).
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
| Región de estado | `role="status"` (`aria-live="polite"`, `aria-atomic="true"`) **presente solo mientras el campo tiene el foco o la lista está abierta, y siempre con texto** (cumple VB-18: ninguna región viva vacía; al perder el foco se desmonta, no se vacía). El texto cambia con un **retardo corto de 400 ms** después de pintar la lista, para no pisar la lectura del campo, y se deja puesto hasta que cambia el resultado. Dice, una vez por búsqueda terminada: «12 resultados. Use las flechas para recorrerlos.», «1 resultado.», «Sin resultados para «{texto}».», «Buscando…» (solo si pasan 700 ms), «No se pudo buscar: …». No anuncia cada tecla. El texto del usuario se inserta como texto (`textContent`), recortado a 60 caracteres. |

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
sin sombra decorativa: el borde de 1 px `$border-strong` y el fondo `$layer`. La lista reutiliza las clases `cds--list-box*` y los tokens de Carbon **solo si F0 confirma que funcionan fuera del `ComboBox`**; si no, estilos propios con los mismos tokens (`$layer`, `$border-strong`, `$layer-hover`). Dentro de una celda de tabla (`enCelda`) la lista se pinta en un portal en `document.body` con `position: fixed`, calculada con `getBoundingClientRect()` del campo, porque la región `.silice-tabla` desplaza y recorta (`overflow`) un menú absoluto; se recalcula al desplazar y al cambiar el tamaño, y se cierra con `Esc`. Los encabezados de grupo van en `label-01`, sin mayúsculas espaciadas (DESIGN.md «Texto»).

---

## 4. Decisión de implementación: componente propio

### 4.1 Por qué no el `ComboBox` de Carbon

La ronda 1 del árbitro lo examinó sobre Carbon 1.117.0 y downshift 9.4.0 (yo **no** lo ejecuté; lo cito como evidencia ajena) y encontró que:

1. monta una región `role="status"` global que **queda vacía** tras 500 ms (choca con VB-18, H-12);
2. sus mensajes de accesibilidad están en **inglés**;
3. la lista es **plana**, sin grupos con encabezado;
4. guarda su propio `inputValue` (la página no lo controla);
5. `Enter` elige el primer elemento resaltado, aunque la persona no haya navegado;
6. con `allowCustomValue=false` **restaura** el texto al salir del campo (borra lo escrito);
7. `Esc` no limpia;
8. el menú queda **recortado** dentro de la tabla.

Cada punto contradice un requisito de §3.3 o §3.6. Se descarta como base.

### 4.2 Qué se construye

`CampoConBusqueda` propio sobre `CampoTexto` (que ya cumple VB-18) y un `<ul role="listbox">` con grupos `role="group"` y `aria-activedescendant`, según §3.6.
Se **reutiliza** de Carbon: `CampoTexto` (envoltura de `TextInput`), `AnilloDeFoco`, `formatoEsVe`, `EstadoVacio` para el texto de «no lo encuentro», los tokens de color y, si F0 lo confirma, las clases
`cds--list-box*` (§3.7). **Tamaño honesto (estimación mía, sin haberlo escrito):** componente ≈ 250 a 350 líneas de TSX; `logicaBusqueda.ts` (turnos, agrupación, reductor de teclado) ≈ 120; estilos ≈ 80;
pruebas ≈ 500. El mayor riesgo es el posicionamiento del portal dentro de celdas con desplazamiento (R-2).

### 4.3 F0: verificación, no decisión

F0 construye un esqueleto mínimo (campo + lista con datos fijos, sin red) y comprueba, **en jsdom y en un navegador real** (perfil propio en el scratchpad, servidor solo en `127.0.0.1`, cierre por PID):

1. ninguna región viva vacía, ni `[aria-live]` ni `role=status`/`alert` sin texto (VB-18) y la región de estado cambia con el retardo de §3.6;
2. todos los textos en español;
3. los grupos se anuncian con su encabezado;
4. el texto lo controla la página (no hay `inputValue` interno);
5. al salir (`blur`) no se restaura ni se borra lo escrito;
6. `Enter` solo elige tras navegar con flechas; `Esc` cierra y después limpia;
7. el menú dentro de una celda de `TablaInsumos` a **1056 px** no queda recortado, ni tras desplazar la tabla ni al cambiar el tamaño de la ventana;
8. con la letra **Muy grande** (150 %) la lista no produce desplazamiento horizontal de la página;
9. `aria-activedescendant` apunta a una opción que existe aunque la lista esté en un portal;
10. el foco nunca sale del campo mientras se navega la lista.

jsdom no mide diseño: 7 y 8 solo se verifican en navegador real. El resultado va a la bitácora. Si 7 fallara con el portal, el plan de reserva es pintar la lista **en el flujo** de la celda (empujando la fila) en vez de flotante; la interfaz pública (§3.2) no cambia.

## 5. Contrato de API

### 5.1 Reglas comunes (todas las rutas de `/v1/buscar`)

- Router nuevo `api/rutas/busqueda.py`, prefijo `/v1/buscar`, **solo lectura** (`GET`), `route_class` que combina `RutaSinCache` y `RutaSinEco`
  (en ese orden: la spec de la hoja §1.3 #7 documenta que el inverso atrapa el `RequestValidationError`; **no lo probé**, la prueba de §8.1 lo fija).
  Respuestas con `Cache-Control: no-store` (también 401, 403, 404, 422); el 422 sin eco (`{"detalle": <mensaje fijo>}`), que **no repite** lo buscado.
- **Acceso por ruta** (`api/acceso.py`, `seguridad/permisos.py:58-64`; el administrador no tiene ninguna de estas acciones y recibe **403** en todas):

  | Ruta | Acción | Roles |
  |---|---|---|
  | `/insumos`, `/partidas`, `/codigo-sugerido`, `/unidades`, `/insumos-con-historial` | `LEER_PROYECTO` | arma, revisa (o clave de API) |
  | `/partidas-linea-base` | `CONTROL_DE_OBRA` | arma |
  | `/proveedores` | `EDITAR_HOJA` | arma |

  Un revisor que abre Componer recibe 403 en lo que Componer ya le negaba. La clave de API no se distingue: ninguna ruta escribe.
- **Parámetros y validación (todos con respuesta 422 de mensaje fijo si no se cumplen):**
  - `q`: `Query(max_length=80)`; se recorta; vacío o de menos de 2 caracteres → **200 con resultados vacíos** (un campo que se está tecleando no es un error). El campo del front lleva `maxLength=80`.
  - `limite`: **por grupo**, 1..50, por omisión 20; `hay_mas` también es por grupo. Es la única regla de límite del contrato (la repiten §3.3-5 y §8.1).
  - `fecha`: opcional, `AAAA-MM-DD` válida; se pasa a `Catalogo.lista_vigente(fecha)` (`core/catalog/repositorio.py:101`). Sin ella, la fecha de hoy.
  - `proyecto`: 1..120 caracteres, sin caracteres de control; se resuelve con `resolver_proyecto` (`aplicacion/proyectos.py:129`, código o nombre exacto). `version`: el `PATRON_CODIGO` de `api/esquemas_ola2.py:129`.
  - Un proyecto o versión que no existen → **404 con mensaje fijo** («No se encontró el proyecto o la versión.»), que **no** repite lo enviado (no se reutiliza `_existe` de `control.py`, H-17).
- Montos y cantidades: **texto** (`"13.9291"`), nunca `float`. Fechas: `AAAA-MM-DD`.
- Un error de base (`SQLAlchemyError`) → 503 con mensaje fijo, sin SQL ni rutas (patrón `_caso_legible`, `precios_empresa.py`).
- Las rutas operan sobre el caso de la sesión (`SesionDep`); no hay parámetro de caso. La referencia MaPreX son archivos del repositorio (no abre la base).
- **Costo:** la búsqueda del catálogo se normaliza en Python sobre **todas** las filas del tipo del caso (con `normalizar_texto`; no se usa `LIKE` de SQL porque no normaliza acentos ni pulgadas). `Catalogo.insumos()` ya
  carga el catálogo completo en `GET /insumos`, así que el costo es del mismo orden: lineal en el tamaño del catálogo, esperado de cientos a pocos miles de filas. **No lo medí**: B2 siembra 5 000 insumos, comprueba que responde 200 y
  anota el tiempo en la bitácora; el umbral lo fija B2 con esa medición, no este documento.
- **Moneda de respaldo:** la lista del caso puede tener cualquier moneda (la columna admite 10 caracteres, `entidades.py:196`), pero el contrato solo conoce `Bs` y `USD` (`MONEDAS`, `core/catalog/moneda.py:20`). Si la moneda de la lista no es ninguna de las dos,
  `fila.precio` va en USD (como hoy) y el grupo trae `aviso`: «La lista del caso está en {moneda}; el precio de MaPreX se muestra en USD.» (la moneda como texto).

### 5.2 Búsqueda y orden por relevancia (una sola implementación, `aplicacion/busqueda.py`)

1. Texto normalizado con `core.verification.texto.normalizar_texto` (la única normalización del repositorio) y separado en palabras.
2. Una fila coincide si **todas** las palabras aparecen como subcadena en la concatenación normalizada de (código, descripción). La unidad **no** entra en la búsqueda: con ella, escribir «dia» o «m» devolvería toda la mano de obra o todo lo medido en metros.
   *(Paridad: todo lo que halla hoy `buscar_referencia` para una sola palabra o una frase contigua lo sigue hallando.)*
3. Rango (menor es mejor): 0 = el código normalizado es igual al texto; 1 = el código empieza por el texto; 2 = la descripción empieza por la primera palabra;
   3 = alguna palabra de la descripción empieza por la primera palabra; 4 = cualquier otra coincidencia. Desempate: descripción normalizada, luego código.
4. **Claves únicas por tipo:** la clave de una fila MaPreX es `maprex:{tipo}:{ref}`. `EFO001` aparece **dos veces con distinto tipo** (un cable de fibra, material, y una fusionadora, equipo), así que no se deduplica por referencia sola: las 111 filas son 111 claves.
5. **`buscar_referencia` queda intacta** (H-20). B1 extrae el lector de los CSV a una función común (`filas_de_referencia`), que `buscar_referencia` usa sin cambiar su resultado (su prueba y las de `simular_corpus` se corren), y la búsqueda nueva es **otra** función.

### 5.3 `GET /v1/buscar/insumos`

Parámetros: `tipo` (`material|equipo|mano_obra`, obligatorio), `q`, `fuentes` (lista separada por comas de `catalogo`, `maprex`; por omisión `catalogo,maprex`), `fecha` (opcional), `limite` (§5.1).

```jsonc
{
  "grupos": [
    {
      "fuente": "catalogo",
      "rotulo": "Del catálogo de este caso",
      "lista": { "nombre": "Lista del caso", "moneda": "USD", "fecha": "2026-08-01" },   // null si no hay lista vigente a `fecha`
      "resultados": [
        { "clave": "catalogo:MAT-004", "codigo": "MAT-004", "descripcion": "…", "unidad": "m",
          "precio": { "texto": "13.9291", "moneda": "USD", "fecha": "2026-08-01" },      // null si la lista no lo valora
          "fila": { "descripcion": "…", "unidad": "m", "cantidad": "", "precio": "13.9291" } }
      ],
      "hay_mas": false, "aviso": null
    },
    {
      "fuente": "maprex",
      "rotulo": "Referencia MaPreX jul-2026",
      "lista": { "nombre": "MaPreX julio 2026", "moneda": null, "fecha": "2026-07-09",
                 "tasa": "633.3644", "fecha_tasa": "2026-07-01" },
      "resultados": [
        { "clave": "maprex:material:PLOA38", "codigo": "PLOA38", "descripcion": "TUBO PVC A.N. D=4\" / 110 MM E = 2,2 MM NORMA", "unidad": "m",
          "precio": { "texto": "13.9291", "moneda": "USD", "fecha": "2026-07-09" },
          "precio_alternativo": { "texto": "8822.17", "moneda": "Bs", "fecha": "2026-07-09" },
          "factor_depreciacion": null, "bono_bs": null,
          "fila": { "descripcion": "…", "unidad": "m", "cantidad": "", "precio": "13.9291" } }
      ],
      "hay_mas": false, "aviso": null
    }
  ]
}
```

- **Fecha de la lista (M-2):** el grupo `catalogo` toma la lista de `Catalogo.lista_vigente(fecha)`. La pantalla de Componer envía el valor de su campo **Fecha** (cuando es una fecha completa y válida), de modo que el precio sugerido es el de la lista que el guardado usará (`guardar_composicion` llama a `lista_vigente(fecha)`, `aplicacion/composicion.py:828`). Prueba con **dos listas de vigencias distintas**: la misma consulta con dos `fecha` devuelve el precio de cada una.
- **Tasa (M-5):** `lista.tasa` y `lista.fecha_tasa` del grupo MaPreX son las de la fuente (633,3644 Bs/USD al 01/07/2026, `README.md` de MaPreX). Viven como constantes de `aplicacion/busqueda.py` (los scripts no se importan) y una prueba comprueba que el README contiene esa cifra. La interfaz las muestra en la línea de procedencia (§3.4).
- **Qué se rellena al elegir** (`fila`, armado en el servidor con las funciones que ya existen, `fila_materiales_desde_referencia`, `fila_equipos_desde_referencia`, `fila_mano_obra_desde_referencia`):
  materiales: descripción, unidad, precio; equipos: descripción, precio y **factor de depreciación** (la regla R6 depende de que el factor venga de una sola fuente); mano de obra: descripción y sueldo (el jornal).
  `cantidad` y `modalidad` quedan **en blanco**. **Depreciación del catálogo (H-18):** un equipo del catálogo rellena `depreciacion` en blanco (el insumo no la tiene). El precio de `fila` está en **la moneda de la lista vigente del caso** (H-6, D-7); si no hay lista vigente o la moneda es otra, en USD, como hoy.
- Fuente `catalogo`: insumos del tipo cuya descripción o código coincide, con el precio de la lista y los datos de esa lista (`nombre`, `moneda`, `fecha_vigencia`). Sin lista vigente (`CatalogoIncompleto`) → el grupo viene con `lista: null` y precios `null`, **no** 409 (buscar no exige lista).
- Fuente `maprex`: los cuatro `referencia_*.csv`, filtrados por `tipo`. `precio` es `precio_usd` o `precio_bs` según la moneda de la lista del caso; `precio_alternativo` es el otro.
- Cuando una misma descripción está en ambas fuentes, **no se fusionan**: aparecen en sus grupos.
- Errores: 422 si `tipo`, `fuentes` o `fecha` no son válidos (mensaje fijo); 503 si falla la base.

### 5.4 `GET /v1/buscar/partidas`, `GET /v1/buscar/partidas-linea-base` y `GET /v1/buscar/codigo-sugerido`

Dos cosas distintas que no deben confundirse: las **partidas del presupuesto de una versión** y las **partidas de la línea base** de un proyecto.

`/partidas`: `q`, `dominio` (opcional), `ambito` (`catalogo` por omisión | `version`), `proyecto` y `version` (obligatorios con `ambito=version`), `limite`. Acción `LEER_PROYECTO`.

```jsonc
{ "rotulo": "Partidas del catálogo", "resultados": [
    { "clave": "partida:LB-02-TUB", "codigo": "LB-02-TUB", "descripcion": "…", "unidad": "m", "dominio": "civil",
      "tiene_composicion": true } ],
  "hay_mas": false }
```

- `ambito=catalogo`: `Catalogo.partidas(dominio)` filtradas. `ambito=version`: las partidas del presupuesto de esa versión, con la misma lectura que `GET /presupuestos/{codigo}` (`cargar_presupuesto`, `core/budget/persistencia.py:255`, H-19); B4 fija la llamada exacta (cómo se pasa el proyecto) y no la leí.
- `tiene_composicion` = existe al menos una línea. Una partida sin composición **se puede elegir**, con la etiqueta «sin composición todavía».

`/partidas-linea-base`: `q`, `proyecto` (obligatorio), `limite`. Acción **`CONTROL_DE_OBRA`**. Devuelve las partidas de la línea base del proyecto, de `instantanea_control(sesion, proyecto, catalogo=…).presupuesto.partidas[].item.codigo_partida`
(`aplicacion/control.py:436-440`), con su descripción y unidad. Un proyecto sin línea base devuelve 200 con resultados vacíos y `aviso`: «Este proyecto todavía no tiene línea base.» (si `instantanea_control` lanza en ese caso, B4 usa `tiene_linea_base`, `control.py:147-155`; no lo probé).

`/codigo-sugerido?dominio=`: devuelve `{ "sugerido": "LB-06" | null, "patron": "LB-NN" | null }`. Se calcula **solo** si todos los códigos de partida del dominio siguen el patrón `^([A-Z]+)-(\d+)(-[A-Za-z0-9]+)?$` con **el mismo prefijo**: toma el máximo del número y le suma 1, **sin** sufijo. Si los prefijos difieren o no hay partidas, `sugerido: null` y la interfaz solo muestra el ejemplo. Es una **ayuda**, no una regla (H-15); la persona la edita o la ignora (D-5).

### 5.5 Cambios a rutas existentes

- `GET /v1/composicion/partidas/{codigo}` (`PrecargaRespuesta`):
  - se añaden `descripcion: str | None`, `unidad: str | None`, `dominio: str | None`, rellenos **siempre que la partida exista en el catálogo** (aunque no haya lista vigente);
  - se añade `tiene_composicion_vigente: bool`;
  - **`existe` cambia de significado** y es el único cambio de comportamiento: pasa a ser «la partida está en el catálogo» (hoy es falso también si no hay lista vigente, `aplicacion/composicion.py:1062-1063`). Con una partida existente sin lista vigente: `existe=true`, `tiene_composicion_vigente=false`, tablas vacías y rendimiento propuesto si lo hay.
  - Las pruebas existentes que afirman `existe` falso usan un código inexistente (`test_api_composicion.py:267`, `:376`, `:383`, `:403`), así que no cambian; se añade una nueva con una **lista de inicio futuro** (la partida existe, no hay lista vigente a hoy).
  - En el front, `existe && !tiene_composicion_vigente` bloquea la cabecera y muestra «Esta partida existe, pero no tiene composición vigente a la fecha elegida»; el guardado seguirá dando el 409 de siempre.
- Ninguna otra ruta existente cambia de acceso ni de semántica. `GET /v1/composicion/referencia` **se conserva** durante la migración y se marca como reemplazada; se retira en un cambio aparte cuando F2 esté fusionado (D-8).

### 5.6 `GET /v1/buscar/proveedores`

`q`, `proyecto`; devuelve `{ "resultados": [{ "texto": "Ferretería Demo, C.A." }] }`: los proveedores ya cotizados **en ese proyecto**, distintos, por orden de uso reciente, a lo sumo 8. `EDITAR_HOJA`. Nunca mira otros proyectos ni otros casos (D-12).
*(No leí la tabla de cotizaciones para fijar la consulta; B4 lo hace. Si la columna del proveedor se llama distinto, el contrato no cambia.)*

### 5.7 `GET /v1/buscar/unidades`

`q`, `limite`. Acción `LEER_PROYECTO`. Entrega la unión de tres orígenes, **sin repetir** la misma unidad (la clave es `normalizar_unidad`, `core/contracts/unidades.py`):
las unidades distintas de las partidas y los insumos **del caso**; las de la referencia MaPreX; y una **glosa fija** de las comunes (`aplicacion/unidades_glosa.py`, §7.3).

```jsonc
{ "resultados": [ { "unidad": "m3", "glosa": "metro cúbico", "origenes": ["glosa", "maprex"], "variantes": [] } ], "hay_mas": false }
```

Oráculo a mano (§8.1): con el caso vacío, `q="m3"` devuelve `m3` con glosa «metro cúbico» y origen `maprex` y `glosa`; `q="pza"` devuelve la unidad canónica `pieza` con la variante `pza`. El conjunto de unidades de MaPreX es `{dia, pza, und, m, m3, env, lt, sco, rll, sg}` (contado a mano de los CSV).

### 5.8 `GET /v1/buscar/insumos-con-historial`

`q`, `limite`. Acción `LEER_PROYECTO` (la de `GET /cambios-precio`). Devuelve las descripciones distintas de los insumos que tienen al menos un `CambioPrecio` (fuente: `cambios_precio`, `core/catalog/precios.py:575`), ordenadas por relevancia (§5.2).
Cada resultado trae la **descripción exacta** (que es lo que `cambios_precio` compara por igualdad), el tipo y la unidad.

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
Esa línea es **estado de la página** (no se guarda en la composición; D-6) y se pierde al recargar: se dice así en la ayuda. Si la persona **edita la descripción después de elegir**, la procedencia pasa a «Propio (escrito a mano)» (el precio dejó de ser el de la fuente en cuanto lo cambió, o la descripción ya no es la de la fila elegida); editar solo el precio la conserva y la marca «editado».

---

## 7. Encaje por pantalla

### 7.1 Componer una partida: flujo exacto

**Antes** (tres pasos separados por el usuario): teclear un código sin saber → teclear descripción y unidad → por cada tabla, un buscador aparte + `Select` de resultados + «Usar esta fila» → «Agregar fila» → cantidades.

**Cuatro estados de la cabecera** (los gobierna la página con una función pura en `logicaCabecera.ts`):

| Estado | Cuándo | Cabecera (descripción, unidad, dominio) | Guardar |
|---|---|---|---|
| **sin elegir** | el código está vacío | editable pero inerte | deshabilitado; motivo visible: «Elija una partida de la lista o escriba un código y confirme «Crear una partida nueva con el código …»» |
| **existente** | se eligió una partida de la lista (o el código escrito, al salir del campo, coincide exactamente con una que existe) | **de solo lectura**, rellena, con la nota «Esta partida ya existe: su cabecera no se cambia desde aquí.» | habilitado según las condiciones del rendimiento, como hoy |
| **nueva confirmada** | se pulsó «Crear una partida nueva con el código …» | editable; aviso `partida_nueva` ya existente | habilitado según las condiciones, como hoy |
| **escrita, sin confirmar** | hay un código escrito que no se eligió ni se confirmó, y al salir del campo no coincide con una partida existente | editable | **deshabilitado**; motivo visible: «Elija una partida de la lista o confirme «Crear una partida nueva con el código …»» |

El motivo es un párrafo de texto (`<p>`), no una región viva. Es un cambio de comportamiento de la pantalla (hoy se puede guardar con cualquier código escrito) y D-3 lo pide a Eugenio. Se evalúa al salir del campo: `partida(codigo)` decide entre **existente** y **escrita, sin confirmar**; si `existe`, la cabecera se rellena aunque la persona no haya abierto la lista.

Flujo, paso a paso:

1. La persona abre **Componer una partida**. El campo **«Código de la partida»** muestra la ayuda: «Es el nombre corto de la partida en el catálogo. Escriba una palabra de su descripción
   (por ejemplo «tubo») para ver las que ya existen, o elija «Crear una partida nueva» si es nueva.» Con el foco, la región de estado dice «Escriba al menos 2 letras o un código».
2. Escribe «tub». A los 300 ms se pide `GET /v1/buscar/partidas?q=tub`. La lista muestra las partidas del catálogo (descripción, y debajo código · unidad · dominio · «con/sin composición»).
   Al final, **siempre**, la opción «Crear una partida nueva con el código «tub»» (si el texto parece un código) o «Crear una partida nueva» (si no), con la sugerencia cuando la hay: «Código sugerido: LB-06 (puede cambiarlo)».
3. **Si elige una existente:** estado **existente**. Se rellenan descripción, unidad y dominio (de la respuesta de precarga ampliada, §5.5), se piden las tablas y el rendimiento (UC-11, como hoy). Un botón «Elegir otra partida» vuelve a **sin elegir** (con confirmación si hay filas editadas).
4. **Si elige «Crear una partida nueva»:** estado **nueva confirmada**. El código queda como escribió (o el sugerido), la cabecera se habilita, aparece el aviso `partida_nueva`, las tablas quedan vacías.
5. **Agregar insumo:** en cada tabla hay un botón **«Agregar insumo»** (sustituye a «Agregar fila» y al buscador de arriba). Agrega una fila vacía y mueve el foco a su celda **Descripción**, que es un combobox (`enCelda`).
6. En la celda escribe «retro». Se pide `GET /v1/buscar/insumos?tipo=equipo&q=retro&fecha=<la del campo Fecha>&limite=8`. La lista muestra el grupo «Del catálogo de este caso» (si hay) y «Referencia MaPreX jul-2026»: `RETROEXCAVADORA CASE O SIM` / `MOV027 · dia · 110.025,9187 USD · MaPreX jul-2026 · 09/07/2026`.
7. Elige. Se rellenan descripción, precio y **depreciación 0,003500** (equipos de MaPreX; los del catálogo la dejan en blanco, H-18); el foco pasa a la celda **Cantidad**. Bajo la descripción aparece la línea de procedencia (§6.2, con la tasa si es USD derivado).
8. Escribe la cantidad (y la modalidad en mano de obra). El **desglose** se recalcula en vivo, como hoy (`/v1/composicion/evaluar`, 300 ms).
9. Si no encuentra el insumo, ve el mensaje de §3.5 y puede **seguir escribiendo a mano**: descripción libre, unidad y precio. Queda como «Propio (escrito a mano)».
10. Guarda como hoy. El guardado no cambia (D-4: el combobox no crea nada en el catálogo).

**Qué se retira:** `BuscadorReferencia.tsx` y su prueba (sustituida por las del componente nuevo, P-2) y el botón «Agregar fila» en favor de «Agregar insumo».
**Qué no cambia:** `tablas.ts` (estado de texto), `PanelDesglose`, `Similares`, `cliente.ts` salvo funciones nuevas. `Guardar.tsx` gana una propiedad (`motivoDeLaCabecera`).

**Pruebas existentes que se rompen y F2 debe reescribir** (las nombro para que el árbitro vea que no se esconden):
`componer/regiones.test.tsx` (cuenta regiones vivas de la página con la lista de campos de hoy); `componer/TablaInsumos.test.tsx:13` y `:86` (buscan el botón «Agregar fila a Materiales» y «Borrar fila …»);
`componer/index.test.tsx:155` y `:222` (teclean el código «FIC-1» y «NUEVA-1» y siguen: con el estado **escrita, sin confirmar** Guardar queda deshabilitado, así que esas pruebas deben pasar por «Crear una partida nueva»), y `componer/BuscadorReferencia.test.tsx` (se retira).

Detalle de datos: la fila de la tabla sigue siendo `Record<string, string>` (`tablas.ts`). La procedencia vive en un mapa aparte `procedencia: Record<"tipo:índice", Procedencia>`
en `componer/index.tsx`, que se reajusta al borrar/agregar filas (función pura `logicaProcedencia.ts` con su prueba).

### 7.2 Hoja del proyecto

- **Cotizar** (H-A1): el combobox del insumo filtra en el navegador la lista que la pestaña Precios ya cargó; cada opción: descripción · `código` · precio de la lista (con moneda) · «cotizado a …» si ya tiene cotización.
  Elegir fija el `insumo` (código) que el servidor espera; el precio cotizado sigue siendo un campo de texto aparte, con la línea «Precio en la lista: 13,9291 USD» a su lado (texto de la fila, sin calcular).
- **Proveedor** (H-A3): `CampoConBusqueda` con `valorPropio` («Usar «{texto}» como proveedor nuevo»); lo que se escribe se manda tal cual.
- **Cambiar el insumo de una línea** (H-A6): un solo combobox sobre `GET /v1/hoja/borradores/{id}/insumos` (E8). **Limitación declarada (H-16):** E8 busca solo en la descripción y ordena por descripción; este combobox **no** tiene relevancia ni búsqueda por código: se conservan `LIMITE_DE_INSUMOS = 300`, el aviso «Hay más de 300 insumos…» y el 409 «Abra una versión guardada…» (con `soloLecturaInsumos`). «Usar este insumo» se mantiene como botón (cambia el borrador y recalcula: no debe ocurrir al elegir).
- **Presupuesto/APU:** no hay campo de dato que migrar (H-A8, H-A10).

### 7.3 Unidad (C-3, C-9)

La unidad no tiene una lista maestra en el código (la tabla `_ALIAS` solo unifica grafías, `core/contracts/unidades.py`). El combobox de unidad usa `GET /v1/buscar/unidades` (§5.7): las unidades del caso, las de MaPreX y una **glosa fija** de
las más comunes en `aplicacion/unidades_glosa.py`: `m` metro, `m2` metro cuadrado, `m3` metro cúbico, `pieza`, `unidad`, `dia`, `h`, `kg`, `saco`, `sg` suma global. Las de MaPreX que no tienen alias son `lt`, `env`, `rll` y `sco`;
sus glosas (`lt` litro, `env` envase, `rll` rollo, `sco` saco) **son mi lectura** de la abreviatura y las confirma Eugenio (D-11). Se acepta cualquier otra unidad escrita a mano **con el aviso**: «Esa unidad no está en la lista; si es la misma que otra con distinto nombre, el programa puede marcarla como diferente.»

### 7.4 Catálogo

K-1 se queda como filtro de tabla. Cambia solo el texto de ayuda en lenguaje llano («Escriba parte del nombre o del código para ver solo esas filas»). El Catálogo **no** muestra moneda ni fecha de la lista en v1: el `InsumoRespuesta` actual no las trae y mostrarlas exigiría una ruta más. Queda como mejora aparte (D-8).

### 7.5 Elaborar, Actualización, Control y resto

Reglas de §2.3, con las mismas piezas. Los combos de partida de **Elaborar** (E-3) son de modo local sobre la lista ya cargada (`partidasCiviles`); los de **Control** (CO-1, CO-2) usan `/v1/buscar/partidas-linea-base`; **Histórico** (HI-1) usa
`/v1/buscar/insumos-con-historial`. **Escenarios** (ES-1) queda fuera hasta que B4 fije la fuente de los insumos de un presupuesto (H-19).

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
| Tabulador | `q="ingeniero"` mano_obra, con `limite` por omisión → exactamente 29 coincidencias en total, 20 devueltas con `hay_mas: true`; con `limite=8`, 8 devueltas y `hay_mas: true`; la descripción truncada `INGENIERO CIVIL P-7 CIV (14 A 15 AÑOS DE EXP` sale **sin completar** |
| Relevancia | `q="PLO"` material → exactamente `PLO035, PLOA38, PLO560, PLO887, PLOG46`, en ese orden (todas rango 1 por código; desempate por descripción: CODO < TUBO < UNION < VALVULA CHECK < VALVULA PASO BOLA; comprobé a mano que ninguna otra fila de materiales contiene «plo») |
| Normalización | `q="TUBÓ"` y `q="tubo"` dan lo mismo; espacios sobrantes no cambian el resultado |
| Tope | `limite=51` → 422; `limite=0` → 422; `q` de 81 caracteres → 422 |
| Moneda del caso | con lista vigente en Bs, `fila.precio == "8822.17"` (no el USD); con lista en USD, `"13.9291"`; sin lista, USD; con una lista en otra moneda (p. ej. `EUR`), `fila.precio == "13.9291"` y el grupo trae el `aviso` fijo |
| Sin lista vigente | grupo catálogo con `lista: null`; **no** 409 |
| Catálogo | insumo sembrado a mano con descripción, unidad y precio conocidos → aparece en `catalogo`, **no** en `maprex`, con la fecha y nombre de **su** lista |
| Separación de fuentes | `fuentes=catalogo` no trae el grupo MaPreX y viceversa; ninguna fila tiene `clave` repetida |
| Partidas | siembra de 3 partidas (`LB-01-EXC`, `LB-02-TUB`, `LB-05-REL`) → `q="tub"` devuelve solo `LB-02-TUB`; código sugerido en el dominio con estas tres = `LB-06`; con prefijos mezclados = `null` |
| Precarga ampliada | la partida existente devuelve `descripcion`, `unidad`, `dominio` de la base; una inexistente, los tres `null` |
| Permisos | `ana` (arma): 200 en todas; `rita` (revisa): 200 en `/insumos`, `/partidas`, `/codigo-sugerido`, `/unidades`, `/insumos-con-historial`; 403 en `/proveedores` y `/partidas-linea-base`; `admin` (administrador): **403 en todas**; sin sesión ni clave: 401; clave de API válida: 200 en las de `LEER_PROYECTO` |
| `no-store` y sin eco | `Cache-Control: no-store` en 200, 401, 403, 422; el cuerpo del 422 no contiene el texto enviado (probar con `q` de 81 «X» y con `tipo=<script>`) |
| 503 | con la sesión forzada a `SQLAlchemyError`, 503 y el cuerpo no contiene `SELECT` ni la ruta de la base |
| Fecha de la lista | dos listas sembradas a mano (vigencias 2026-08-01 con precio `10.00` y 2026-09-01 con `12.00` para el mismo insumo): `fecha=2026-08-15` devuelve `10.00`; `fecha=2026-09-15` devuelve `12.00`; sin `fecha`, la de hoy; `fecha=2026-13-40` → 422 |
| Unidades | con el caso vacío, `q="m3"` → `m3`, glosa «metro cúbico», orígenes `glosa` y `maprex`; `q="pza"` → `pieza` con variante `pza`; el conjunto sin filtro contiene exactamente `{dia, pza, und, m, m3, env, lt, sco, rll, sg}` de MaPreX |
| Partidas por ámbito | `ambito=version` con una versión de 2 partidas sembradas devuelve esas 2 y no las otras del catálogo; `/partidas-linea-base` devuelve las de la línea base del proyecto y 403 a `rita`; proyecto inexistente → 404 con mensaje fijo que **no** contiene el nombre enviado |
| Historial | `/insumos-con-historial` devuelve solo los insumos con un `CambioPrecio` sembrado y su descripción exacta |
| Validación de `proyecto`/`version` | `proyecto` de 121 caracteres o con un carácter de control → 422; `version` fuera de `PATRON_CODIGO` → 422; ambos sin eco |
| Precarga con lista futura | partida existente + única lista con inicio futuro → `existe: true`, `tiene_composicion_vigente: false`, `descripcion/unidad/dominio` de la base, tablas vacías |
| Cadena de acceso | `test_api_acceso_por_ruta.py` gana las filas nuevas (texto exacto en §12) |

### 8.2 Aplicación y datos

- `test_busqueda_aplicacion.py`: el ranking por casos de §5.2 (rangos 0 a 4) y la deduplicación: las 111 filas son 111 claves únicas **por tipo**: `EFO001` aparece dos veces con distinto tipo (cable de fibra, material; fusionadora, equipo) y la prueba afirma que **ambas** salen y que `clave` incluye el tipo (`maprex:material:EFO001`, `maprex:equipo:EFO001`).
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
| P-4 | Los oráculos de §8.1 (`PLOA38`, `MOV027`, `1-1.2`, 29 «ingeniero» con 20 devueltas por omisión y 8 con `limite=8`, orden de `PLO`, fecha de lista, unidades) pasan con rojo visto previo. `limite` es por grupo y `hay_mas` por grupo, igual en §3.3-5, §5.1 y §8.1. |
| P-5 | Una sola petición en vuelo por campo, con aborto real y descarte de turnos viejos; demostrado con temporizadores falsos. |
| P-6 | Ningún **campo monetario** pasa por `Number`, `parseFloat` ni `toFixed` en los archivos **nuevos** (`CampoConBusqueda*`, `logicaBusqueda`, `logicaCabecera`, `logicaProcedencia`) ni en las líneas que se tocan de las pantallas (barrido en prueba); un precio de 30 cifras se ve íntegro. Los usos existentes de `Number` sobre cosas que no son montos (`Similares.tsx:11` sobre el puntaje de similitud; `BuscadorReferencia.tsx:82` sobre un índice, que se retira) no se tocan. |
| P-7 | Todo texto de la API se pinta como texto; un nombre con `<img onerror>` se ve literal. |
| P-8 | Cada resultado y cada fila elegida muestran fuente, fecha y moneda; ningún resultado de una fuente lleva el rótulo de otra. |
| P-9 | Medición de las unidades MaPreX sin alias (`sco`, `env`, `lt`, `rll`) contra R3, anotada en la bitácora (sea cual sea el resultado). |
| P-10 | Elegir una partida existente rellena y bloquea la cabecera; se elimina la trampa de H-2 (prueba de pantalla + prueba de ruta). |
| P-11 | `GET /v1/buscar/*`: `no-store` en 200/401/403/422, 422 sin eco, 503 sin SQL, permisos por rol según §8.1. |
| P-12 | El 401 de cualquier búsqueda llama `alExpirar` una vez; 403/422/503 muestran su mensaje y el campo sigue siendo editable. |
| P-13 | Cada campo de §2 con clase A, B o C tiene ayuda en lenguaje llano y, donde se pide, un ejemplo ficticio; ninguna ayuda contiene «UC-», «RF-», «R3», «ref_maprex» ni jerga interna (barrido de textos en una prueba). |
| P-14 | A 1366×768 y 1056 px, con letra Normal, Grande y Muy grande, ni Componer ni la Hoja tienen desplazamiento horizontal de la página; el menú de una celda de `TablaInsumos` no queda recortado; la región viva de estado llega con su retardo de 400 ms y nunca está vacía; recorrido con teclado y lector de pantalla hecho por una persona, con resultado escrito. |
| P-15 | Una moneda tecleada a mano ya no existe en Elaborar ni en Actualización (E-2, U-2): son `Select` Bs/USD. |
| P-16 | `git diff -- core/` vacío; `api/main.py`, `rutas.ts`, `docs/ERS.md`, `docs/api.json` y `CHANGELOG.md` solo los toca el orquestador con el texto de §12. |
| P-17 | `npx vitest run src/comun src/paginas/componer src/paginas/hoja src/paginas/catalogo src/paginas/elaborar src/paginas/actualizacion src/paginas/control src/paginas/historico src/paginas/precios_empresa`, `npm run lint` y `npm run build` limpios; `uv run --active pytest` de los archivos nuevos **y** de `tests/unit/test_api_acceso_por_ruta.py`, `tests/unit/test_front_rutas_api.py`, `tests/unit/test_openapi.py`, `tests/unit/test_arquitectura.py` y `test_api_composicion.py` con `-W error`, sin fallos: son la **puerta de cierre**. `ruff check` y `ruff format` limpios. |
| P-18 | Los cuatro estados de la cabecera de Componer (§7.1): en **sin elegir** y **escrita, sin confirmar** Guardar está deshabilitado y el motivo está visible; en **existente** la cabecera está bloqueada; en **nueva confirmada** se guarda como hoy. Prueba de pantalla de cada estado y de la salida del campo con un código que existe y con uno que no. |
| P-19 | El precio sugerido corresponde a la lista vigente a la fecha del campo Fecha de Componer (prueba de pantalla: cambiar la fecha repite la búsqueda con esa `fecha`). |
| P-20 | `pedir` con `senal`: abortar la petición no muestra «No se pudo hablar con el programa de Sílice» (se relanza el `AbortError`); sin `senal`, el comportamiento actual no cambia (las pruebas existentes de `cliente.test.ts` siguen verdes). |
| P-21 | La procedencia de una fila pasa a «Propio (escrito a mano)» si se edita la descripción después de elegir, y se conserva con «editado» si solo se edita el precio. |

---

## 9. Sub-rebanadas, dependencias y agentes

```
F0 ──┐                              (verificación del esqueleto en jsdom y navegador real + `pedir` con `senal`)
B1 ─┐│
B2 ─┤├─> F1 ──> F2 (Componer) ──> F3 (Hoja) ──> F4 (Elaborar/Actualización/Catálogo) ──> F5 (resto) ──> CIERRE
B3 ─┤│
B4 ─┘┘   (B1-B3 en paralelo con F0/F1; F2 necesita B1+B2+B3; F3 solo B4 para proveedores)
```

| Rebanada | Qué entrega | Depende de | Paralelo con | Agente sugerido* |
|---|---|---|---|---|
| **F0** | (1) `pedir` acepta `senal?: AbortSignal` y relanza el `AbortError` sin envolverlo (aditivo; P-20). *Toca `src/api/cliente.ts`: archivo compartido, lo aplica el orquestador.* (2) Esqueleto del campo con lista (datos fijos, sin red) y las 10 comprobaciones de §4.3 en jsdom **y** en navegador real; decisión sobre portal/flujo y estilos, en la bitácora | — | B1-B4 | `javascript-typescript:typescript-pro` |
| **B1** | `aplicacion/busqueda.py`: normalización, ranking, lector común de los CSV (`buscar_referencia` intacta, H-20), `buscar_insumos_maprex` (con `precio_alternativo`, `tasa`, `fila` y moneda del caso, claves por tipo); `GET /v1/buscar/insumos?fuentes=maprex`; JSON de referencia en `docs/api_ejemplos/buscar/` | router vacío en `api/main.py` (orquestador) | F0, B2-B4 | `python-development:python-development-fastapi-pro` |
| **B2** | Fuente `catalogo` de insumos con su lista y `fecha`; `GET /v1/buscar/partidas` (ámbito `catalogo`); medición de costo con 5 000 insumos | B1 (módulo) | F0, B3 | ídem |
| **B3** | `PrecargaRespuesta` ampliada (`descripcion`, `unidad`, `dominio`, `tiene_composicion_vigente`, `existe` redefinido); `GET /v1/buscar/codigo-sugerido`; `GET /v1/buscar/unidades` y `aplicacion/unidades_glosa.py` | — | B1, B2 | ídem |
| **B4** | `GET /v1/buscar/proveedores`; `ambito=version` de partidas; `GET /v1/buscar/partidas-linea-base`; `GET /v1/buscar/insumos-con-historial`; y propone la fuente de los insumos de un presupuesto (ES-1) | B2 | F2 | ídem |
| **F1** | `CampoConBusqueda` completo + `logicaBusqueda.ts` + estilos + pruebas de §8.3 (con los JSON de referencia como mocks) | F0 | B1-B4 | `javascript-typescript:typescript-pro` + `sf-ingeniero-pruebas` (revisa que las pruebas no sean circulares) |
| **F2** | Componer: combobox de código, de descripción por tabla, de unidad, procedencia, «Agregar insumo», cuatro estados de la cabecera, ayudas C-2 a C-12; retira `BuscadorReferencia`; reescribe las pruebas que se rompen (§7.1) | F1, B1, B2, B3 | B4 | ídem |
| **F3** | Hoja: cotizar (local), proveedor, cambiar insumo (E8), ayudas H-A*; **no** toca `hoja/index.tsx`, `useBorrador.ts` ni los mocks de `Hoja.test.tsx` (§0.1) | F1 (y B4 solo para proveedor) | F2 (no comparten archivos) | ídem |
| **F4** | Elaborar (E-1..E-3), Actualización (U-1..U-3), Catálogo (K-1) | F1 | F3 | ídem |
| **F5** | Histórico (HI-1), Control (CO-1, CO-2, CO-4), Precios de la empresa, existencias, similares, índices, administración (ayudas y combos de §2.3). **No incluye ES-1** | F1, B4 | F4 | ídem |
| **CIERRE** | Barrido de textos (P-13), manual de usuario (`docs/manual_usuario.md`, sección «Cómo buscar»), auditoría visual con teclado y lector de pantalla (P-14), bitácora, árbitro de la entrega completa, y la puerta de P-17 | F2-F5 y BCP-8 de bienvenida | — | árbitro (`MANUAL_ARBITRO.md`) |

\* Los agentes `silice-*` que menciona la memoria del proyecto no los veo en la lista de este entorno; uso los tipos que sí existen. Cada rebanada pasa por el **árbitro**; máximo 3 rondas.

Cada rebanada entrega con su informe del manual §5 y **un commit por tarea** (Conventional Commits en español, asunto sin tildes, `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`). Ninguna rebanada toca los archivos compartidos del manual §2; su texto exacto va en §12.

**Orden recomendado y por qué:** F2 primero porque es lo que pidió Eugenio y donde está la trampa de H-2; F3 segundo porque reutiliza lo mismo y ya existe E8; F4/F5 son barrido y se pueden dividir entre agentes sin conflicto (no comparten archivos). El cierre espera a BCP-8 de bienvenida, que añade `<AyudaDePagina />` a cada página tras este trabajo (§0.1).

---

## 10. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R-1 | **La referencia MaPreX estructurada es chica (111 filas):** el autocompletado se sentirá pobre y la persona verá «no lo encuentro» a menudo. | El estado vacío lo explica con honestidad (§3.5); D-2 propone ampliar por demanda y con verificación; no se promete cobertura. |
| R-2 | El componente propio cuesta más que reutilizar Carbon (≈ 500 líneas con pruebas) y el **portal posicionado dentro de celdas con desplazamiento** puede fallar en cierto navegador o con la letra Muy grande. | F0 lo verifica en navegador real antes de construir F1 (§4.3); plan de reserva: lista en el flujo de la celda; la interfaz pública no cambia. |
| R-3 | Rellenar el precio en la moneda equivocada (H-6) y producir un APU silenciosamente erróneo. | El servidor elige la moneda de la lista del caso; la procedencia muestra moneda; prueba de moneda (§8.1); D-7 pide el visto bueno de Eugenio. |
| R-4 | Unidades MaPreX sin alias hacen saltar R3 en un material legítimo (H-8). | Medición P-9; si ocurre, hallazgo para el tutor (tocar `core/` está fuera de este diseño). |
| R-5 | La precarga al elegir cambia un comportamiento que hoy se dispara al teclear, y **Guardar queda deshabilitado** con un código escrito sin confirmar (§7.1): flujos y pruebas que tecleaban el código y guardaban dejan de funcionar tal cual. | La entrada manual sigue disponible: escribir el código completo de una partida que existe y salir del campo la resuelve sola (estado **existente**); para una nueva hay un botón visible. Se nombran las pruebas que se reescriben (§7.1) y P-18 cubre los cuatro estados. D-3 lo somete a Eugenio. |
| R-6 | `RutaSinCache` + `RutaSinEco` en el orden equivocado (spec de la hoja §1.3 #7). | Prueba de 422 con `no-store` y sin eco en el mismo caso (§8.1); no lo probé. |
| R-7 | Tamaño de letra Muy grande: la lista de dos líneas por opción crece y tapa el campo de abajo. | Altura máxima `min(20rem, 60vh)` con desplazamiento interno; P-14 la mide. |
| R-8 | Un nombre de proveedor largo o con caracteres raros rompe la lista o inyecta HTML. | Texto de React siempre; `max-length` del dato; prueba P-7. |
| R-9 | Datos reales colados: un proveedor, una empresa o un libro reales en un ejemplo, una prueba o una captura. | Ejemplos solo de la lista ficticia (§6.1); el árbitro revisa (BLOQUEANTE si ve uno); las capturas de pantalla de la auditoría visual usan un caso de prueba. |
| R-10 | Mantener dos buscadores (`/referencia` y `/v1/buscar/insumos`) viola DRY. | Comparten el lector de CSV y las funciones `fila_*_desde_referencia` (§5.2-5); `buscar_referencia` queda intacta por sus otros usuarios (`simular_corpus`, reexportación) y `/referencia` se retira en un cambio aparte (D-8). |
| R-11 | La sugerencia de código se confunde con una regla («tengo que usar LB-06»). | Se rotula «Código sugerido (puede cambiarlo)» y el campo sigue siendo libre (§5.4, D-5). |

---

## 11. Decisiones abiertas para Eugenio (recomendación conservadora y reversible)

| D | Pregunta | Recomendación |
|---|---|---|
| D-1 | ¿Qué fuentes se ofrecen en v1? | **Catálogo del caso + referencia MaPreX + lista de la versión** (en la Hoja). **No** la lista de precios de la empresa (UC-17): es del administrador (`ADMINISTRAR_PRECIOS`) y mostrársela a quien arma cambia quién ve qué. Reversible: añadir una fuente es un grupo más. |
| D-2 | La referencia MaPreX estructurada tiene 111 renglones de ≈16 000; el README de MaPreX (regla 2) dice «jamás el volcado completo». ¿Se amplía? | **No ahora.** Ampliar *por familia* (tubería, cables…) **exige que Eugenio apruebe una excepción a esa regla 2** del README, y verificar cada fila a mano contra el PDF (como la sesión M0.2). El estado «no lo encuentro» lo anticipa. |
| D-3 | ¿Qué pasa si se escribe un **código de partida que no existe**? Es un **cambio de comportamiento**: hoy se puede guardar con cualquier código escrito. | **No se acepta en silencio:** el campo queda en «escrito, sin confirmar» y **Guardar se deshabilita** con el motivo visible «Elija una partida de la lista o confirme «Crear una partida nueva con el código …»». Con un clic en esa opción pasa a «nueva confirmada» y se guarda como siempre (con el aviso `partida_nueva`). Si Eugenio prefiere la conducta de hoy (guardar sin confirmar), la alternativa es dejar Guardar habilitado y solo avisar; es más permisiva y menos guiada. |
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

1. **`api/main.py`:** `from api.rutas import busqueda` y `app.include_router(busqueda.router)` junto al resto de los routers de `/v1`, **antes de B1** (con el router vacío; §0.1).
2. **`tests/unit/test_api_acceso_por_ruta.py`:** filas (ruta, método, acción) —
   `/v1/buscar/insumos`, `/v1/buscar/partidas`, `/v1/buscar/codigo-sugerido`, `/v1/buscar/unidades`, `/v1/buscar/insumos-con-historial`: GET `LEER_PROYECTO`;
   `/v1/buscar/partidas-linea-base`: GET `CONTROL_DE_OBRA`; `/v1/buscar/proveedores`: GET `EDITAR_HOJA`.
3. **`tests/unit/test_arquitectura.py`:** `aplicacion/busqueda.py` y `aplicacion/unidades_glosa.py` no importan `streamlit`, `ui`, `api`, `scripts` ni `tests` (RM-1); `api/rutas/busqueda.py` no importa `ui`, `scripts` ni `tests`. Si la prueba enumera módulos, añadirlos.
4. **`docs/ERS.md` (numeración provisional):** una enmienda «Autocompletado guiado de campos» con **RF-A**, **RF-B** y **RNF-A**, que son **provisionales y el orquestador asigna al integrar**. El ERS real llega a RF-155 y RNF-28; el diseño de bienvenida toma RF-156 a RF-162 y RNF-29, y el del asistente RF-156 a RF-159 (esos dos chocan entre sí), así que el orquestador renumerará las tres. Texto:
   **RF-A** «Los campos que piden un dato que la persona no tiene por qué saber de memoria (código de partida, insumo, unidad, moneda, proveedor) ofrecen una búsqueda con autocompletado sobre el catálogo del caso, la referencia MaPreX o la lista de la versión, con la fuente, la fecha y la moneda de cada resultado a la vista; el precio sugerido queda editable»;
   **RF-B** «Al elegir una partida existente en Componer, su cabecera se rellena y no se edita; un código escrito sin elegir ni confirmar no se guarda»;
   **RNF-A** «La búsqueda con autocompletado es operable solo con el teclado y por lector de pantalla, con tres tamaños de letra, sin desplazamiento horizontal a 1366×768 y 1056 px». Enmienda a UC-10 paso 1 y flujos 2b/3b/4b (buscador integrado en la celda). La matriz de trazabilidad (§4) gana las filas.
5. **`docs/api.json`:** regenerar con `scripts/exportar_openapi.py` (rutas `/v1/buscar/*` y los campos nuevos de `PrecargaRespuesta`); `tests/unit/test_openapi.py` y `tests/unit/test_front_rutas_api.py` son parte de la puerta de cierre (P-17).
6. **`CHANGELOG.md`:** «Añadido: autocompletado guiado de campos (`CampoConBusqueda`, `GET /v1/buscar/*`); Componer rellena la cabecera de la partida elegida y no guarda un código escrito sin confirmar; el buscador MaPreX de Componer pasa a la celda de cada insumo.»
7. **`frontend-desktop/DESIGN.md`:** nueva sección «Campos con búsqueda» (dos líneas por opción, código en Plex Mono, fuente y fecha siempre visibles, estado «no lo encuentro», región viva solo con contenido y con retardo).
8. **`frontend-desktop/src/api/cliente.ts`:** `senal?: AbortSignal` en `OpcionesDePeticion`, `signal: opciones.senal` en el `fetch` y, en el `catch`, relanzar el error si es un `AbortError` (F0; aditivo).
9. **`frontend-desktop/src/shell/rutas.ts`:** sin cambios (no hay página nueva).

---

## 13. Lo que no pude determinar

- **Cómo se comporta el `ComboBox` de Carbon 1.117.0:** no lo ejecuté; cito la evidencia de la ronda 1 del árbitro (§4.1). Lo que sí queda por medir es el componente propio en navegador real (F0, §4.3).
- Si `RutaSinCache` + `RutaSinEco` combinan bien en el orden propuesto (la spec de la hoja lo afirma; no lo probé).
- Cómo se pasa el proyecto a `cargar_presupuesto` para `ambito=version`, la consulta exacta de proveedores en cotizaciones y qué función da los insumos de un presupuesto (Escenarios, ES-1): no los leí o no existen; B4 los fija.
- Si R3 marca como diferentes las unidades MaPreX sin alias (`sco`, `env`, `lt`, `rll`): medición P-9.
- Si el sistema valida de algún modo el formato del código de una partida: no encontré validación en lo que leí, pero no leí `composicion_desde_tablas` (líneas 219-267) entero.
- La glosa correcta de `lt`, `env`, `rll` y `sco`: es mi lectura de las abreviaturas (D-11).
- Cuántas partidas e insumos tiene un caso real: no hay un caso real en el repositorio (y no debe haberlo); el diseño supone catálogos de cientos, no de decenas de miles, y por eso el límite de 20 y el filtrado en el servidor.
