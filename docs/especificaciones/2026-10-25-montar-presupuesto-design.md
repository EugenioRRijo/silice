# Montar un presupuesto de punta a punta: diseño

**Fecha:** 2026-10-25 · **Rama:** `inc/ruta-s2-mig-adm-empresa` (árbol `.worktrees/s2madm`) · **Estado:** APROBADO por Eugenio (2026-10-25), pendiente de los ajustes del revisor constructor.
**Origen:** prueba en vivo de la partida y del presupuesto (scratchpad `vivo/informe.md`) y obra ficticia completa en vivo con el
navegador visible (scratchpad `obra_vivo/informe.md`, hallazgos O-1 a O-24), más la sesión de diseño con Eugenio del 2026-10-25.
**Prioridad (Eugenio):** va después de la barra superior (hecha) y antes de la Fase 1 de auditoría.

## 1. Intención

El trabajo diario de la empresa es montar presupuestos. Hoy lo hace en sus libros de Excel automatizados:
**INSUMOS** (MaPreX + estudio de mercado) → **APU** → **MEDICIONES** → **PRESUPUESTO** → **fases de aprobación y cambios** →
(después) procura, puntos de equilibrio, plan de pagos. En Sílice, una persona **no puede** hacer una obra propia sin atajos:
- no puede crear el proyecto (O-6);
- la Hoja no deja agregar partidas, y está pensada para instalaciones (O-8, O-10);
- la moneda es una etiqueta: Componer escribe los precios en la lista vigente sin preguntar la moneda; un bloque «a 18 Bs» quedó
  como 18 USD y la obra en Bs no se pudo guardar (O-11);
- el dictamen de quien revisa no vuelve al proyecto: no hay ciclo de aprobación (O-20).

Lo que sí funciona y se reutiliza: Componer (APU), versiones selladas con su fuente y responsable, Entregar y Revisar el paquete
firmado, punto de equilibrio, control de obra.

## 2. Metas, no-metas y anti-metas

**Metas**
1. M1 · **Moneda explícita de punta a punta**: cada precio, lista, APU, versión y total dice su moneda; nunca se mezcla sin aviso.
2. M2 · **Precios para armar**: una lista de precios en la moneda del proyecto, alimentada por MaPreX y por el **estudio de
   mercado** (compra y cobro).
3. M3 · **Crear el proyecto** desde la interfaz (BCP-6) y que la carpeta y el proyecto elegidos **se recuerden**.
4. M4 · **Presupuesto por partidas en la Hoja**: agregar y quitar partidas del catálogo con su cantidad y cómo se midió.
5. M5 · **Ciclo de aprobación** dentro de la empresa: enviar a aprobación → aprobar / aprobar con observaciones / devolver → el
   dictamen vuelve a quien arma → la versión aprobada queda marcada.
6. M6 · Una obra ficticia completa (la vivienda de 80 m²) se hace **sin atajos**, comprobada por un recorrido en vivo con
   Playwright y un video.

**No-metas (pieza siguiente):** procura (explosión de insumos), plan de pagos, plan que se calcule con los rendimientos (O-21),
que Sílice relea su propio Excel (O-24, va con la Fase 1 de auditoría), varias fases de aprobación en cadena (ingeniero → gerente
→ cliente), la Hoja orientada a instalaciones (se conserva tal cual para esas obras).

**Anti-metas:** que un precio cambie de moneda en silencio; que una conversión Bs/USD no diga su tasa y su fecha; que Sílice
elija el precio por la persona; que una versión aprobada se pueda editar; que se pierda el rastro de quién aprobó qué; un `float`
en dinero; tocar `core/`; subir al repositorio datos reales de la empresa (precios de la competencia incluidos).

## 3. Restricciones y hechos del código

- `core/` intacto. El núcleo acepta versiones con renglones distintos a la anterior (cada versión es un documento completo) y
  `guardar_presupuesto` recibe la lista con la que valora (`core/budget/persistencia.py:120-252`); exige que la lista y la versión
  estén en la misma moneda y que la versión use la moneda declarada del proyecto (`:167-179`).
- `Catalogo.lista_vigente` es **global y no filtra por moneda** (`core/catalog/repositorio.py:101-120`); las listas de alcance
  `empresa` no cuentan como vigentes (`core/models/entidades.py:569`). Por eso la elección de la lista correcta se hace en
  `aplicacion/`, pasando la lista explícita.
- La Hoja guarda la primera versión con `hoja.crear_primera_version` y las siguientes con `guardar_edicion`, cuyo `objeto` debe
  estar en `OBJETOS` (`core/budget/edicion.py:57`): agregar o quitar un renglón se registra con un objeto ya válido
  (`cantidad`, campo `alta`/`baja`), sin objeto nuevo. `items_base` del borrador es donde viven los renglones que no salen del
  espacio (`aplicacion/hoja.py:335-361`).
- Crear proyecto ya existe en la API (`POST /v1/proyectos`, BCP-3) y su front está diseñado (BCP-6 del diseño
  `2026-10-21-bienvenida-casos-proyectos-design.md`).
- El dictamen de Revisar ya se guarda atado al SHA-256 del paquete; no se liga al proyecto ni a la versión.
- Regla de cifras (Eugenio, 2026-10-25): **coma decimal, punto de miles**, en todo lo que la persona escribe y ve (en
  construcción en paralelo; este diseño la da por hecha).

## 4. Lo que decidió Eugenio

- El orden: esta pieza antes de la Fase 1 de auditoría.
- Alcance: los pasos 1 a 5 del flujo de la empresa; procura y lo demás después («no creo que falte nada»).
- Estudio de mercado: se estudian los precios de la competencia y del mercado; la empresa estima el suyo con las estadísticas
  «más competitivas sin perder dinero»; sirve **para lo que compra y para lo que cobra**.
- Ciclo de aprobación como se propuso; **quien arma también puede revisar y aprobar** (es válido).
- Coma decimal y punto de miles.

## 5. Diseño

### 5.1 Moneda explícita (M1) y precios para armar (M2)

- **Lista para armar**: para cada moneda (Bs, USD) la carpeta de trabajo tiene, a una fecha, su **lista vigente para armar**. La
  elige `aplicacion/` con una función única `lista_para_armar(sesion, moneda, fecha)` (la más reciente de esa moneda, de alcance
  global, vigente a la fecha). Toda pantalla que valora (Componer, la Hoja, Elaborar) usa esta función con la **moneda del
  proyecto** (o la elegida en Componer); nunca `lista_vigente` a secas.
- **Componer pregunta la moneda**: un selector «Moneda de los precios» (Bs/USD) arriba, por omisión la del proyecto abierto o, sin
  proyecto, la de la lista para armar más reciente de la carpeta. Los precios tecleados se guardan en la lista para armar **de esa
  moneda y de hoy**: si no existe una lista de hoy en esa moneda, se crea una **derivada** de la vigente de esa moneda con la fecha
  de hoy (así el precio nuevo no queda fechado con una lista vieja — O-13). El desglose y el precio unitario muestran la moneda.
- **Sin lista en la moneda**: Componer y la Hoja lo dicen al abrir, con dos salidas: «Crear la lista de precios en Bs a partir de
  MaPreX» (copia la referencia MaPreX de esa moneda como lista para armar) o «Convertir la lista en USD a Bs» (usa la conversión
  existente con la tasa del BCV, declarando tasa y fecha). Nunca se mezcla en silencio.
- **La carpeta dice lo que tiene**: el panel «Carpeta y proyecto» muestra, debajo de la carpeta, sus listas para armar («Bs: MaPreX
  julio 2026, al 25/10/2026 · USD: Línea base, al 28/04/2026»), para que nadie tenga que adivinar (O-1).
- **Estudio de mercado** (pantalla nueva «Estudio de mercado», área Crear o Más; el constructor propone el lugar en la barra):
  - Dos pestañas: **Lo que compramos** (insumos) y **Lo que cobramos** (partidas).
  - Por cada insumo o partida, una tabla de **observaciones de precio**: fuente (proveedor, competidor, cotización, MaPreX),
    fecha, moneda, precio, nota. Las observaciones son **datos de la empresa**: se guardan en la carpeta de trabajo, solo en ese
    equipo; las pruebas usan datos ficticios.
  - Sílice calcula, por moneda y con las observaciones de los últimos N días (por omisión 90, cambiable): n, mínimo, primer
    cuartil, mediana, promedio, máximo.
  - **El piso** (no perder dinero): en «Lo que compramos» no hay piso (el precio que se paga); en «Lo que cobramos», el piso es el
    **costo de la partida** según su APU con la lista para armar (costo directo + administración), mostrado al lado.
  - **Propuesta**, nunca decisión: para compras, la **mediana** como referencia y el mínimo como «más barato visto»; para cobro,
    **el más competitivo que no quede por debajo del piso**: el primer cuartil si supera el piso; si no, el piso (y lo dice:
    «la competencia cobra menos que su costo»). La persona elige el precio y pulsa «Usar este precio»: para compras, entra en la
    lista para armar de su moneda (con la observación como fuente); para cobro, se guarda como **precio de venta objetivo** de la
    partida y se muestra en la Hoja junto al precio del APU («APU 2.074,44 · objetivo de mercado 1.980,00 · margen −4,6 %»).
  - Todo determinista, sin IA; cada cifra dice de qué observaciones sale.

### 5.2 Crear el proyecto y recordar la elección (M3)

- Se construye BCP-6 tal como está diseñado (diálogo «Nuevo proyecto» con nombre, moneda y tipo de obra), dentro del panel
  «Carpeta y proyecto» de la barra superior, más BCP-5 (carpetas) en el mismo panel.
- **Se recuerda la elección**: la carpeta y el proyecto abiertos se guardan por cuenta (servidor, en `instalacion.db`, ligados al
  usuario) y se restauran al entrar, al recargar y tras reiniciar la API, si siguen existiendo (O-2, O-12, O-16). Cambiar de carpeta
  con un formulario a medio llenar pide confirmación (la deuda de BCP-5).

### 5.3 Presupuesto por partidas en la Hoja (M4)

- La pestaña **Presupuesto** gana **«Agregar partida»**: un buscador de partidas del catálogo (código o descripción; el combobox
  C-1 del diseño de autocompletado, que se construye aquí para este uso) que, al elegir, pide la **cantidad** y **cómo se midió**
  (texto libre opcional, p. ej. «6 m × 3 m de muro, menos vanos»; se guarda como la regla del ítem, así R1 la reconoce como
  reproducible y deja de ser ruido — O-14). Si la partida no existe: «Componer una partida nueva» abre Componer y vuelve.
- Cada fila gana **«Quitar»** (con confirmación). Agregar y quitar son cambios del borrador (como las cantidades): se ven en el
  Estado, se pueden descartar y se guardan como versión con su fuente. En la versión se registran con objeto `cantidad`, campo
  `alta` (antes vacío) o `baja` (después vacío).
- **Hoja de obra civil**: si el proyecto no tiene espacio (ambientes, puntos), la Hoja abre en **Presupuesto**, no en «Espacio y
  metrajes»; el espacio queda para las obras de instalaciones. El total y las cifras van en la moneda del proyecto (O-7).
- La primera versión de un proyecto sin versiones se guarda igual que hoy («Guardar primera versión…»), ahora con renglones
  agregados a mano.
- «Elaborar» (CSV de cómputo) se conserva; gana «Llevar a la Hoja del proyecto», que mete sus ítems en el borrador como renglones
  agregados (sin guardar por su cuenta).

### 5.4 Ciclo de aprobación (M5)

- **Estados de una versión**: borrador (no es versión) → guardada → **en aprobación** → **aprobada** | **aprobada con
  observaciones** | **devuelta**. Una versión en aprobación o aprobada **no se edita**: cambiarla es hacer una versión nueva desde
  ella.
- **Enviar a aprobación** (quien arma, desde la Hoja): elige la versión, escribe una nota opcional; queda «en aprobación».
- **Por aprobar**: quien tiene la acción de revisar ve en su Inicio una lista «Por aprobar» (proyecto, versión, total, quién la
  envió, cuándo) y, al abrir una, la Hoja de esa versión en solo lectura con su auditoría y un panel «Dictamen»: aprobada /
  aprobada con observaciones / devuelta; **notas obligatorias** para devolver y para «con observaciones».
- **Quien arma también puede aprobar** (decisión de Eugenio). Se permite y queda **visible**: el dictamen dice «aprobada por quien
  la armó» y la trazabilidad lo muestra igual.
- **El dictamen vuelve**: quien arma ve en su Inicio «Mis versiones en aprobación» con su estado y las notas; en la Hoja, junto a
  la versión, una etiqueta con el estado («Aprobada · Rita · 25/10/2026»). Si la devolvieron, «Hacer una versión nueva a partir de
  esta» lleva al borrador.
- **Rastro**: cada envío y cada dictamen se registran (quién, cuándo, versión, estado, notas) y quedan en la Trazabilidad; las
  fases de una obra se leen como cadena («VIV-001 devuelta → VIV-002 aprobada»).
- **La aprobada manda**: Entregar propone por omisión la última versión aprobada y avisa si se entrega una no aprobada; Control de
  obra propone la aprobada como línea base.
- Se guarda en la base de la carpeta de trabajo (tabla nueva de aprobaciones, ligada al proyecto y al código de versión), sin
  tocar `core/` (el constructor sigue el precedente de tablas fuera del núcleo, p. ej. `produccion/`).
- El dictamen de **Revisar un paquete** (paquetes de otras empresas o del cliente) se conserva tal cual: es otro caso.

## 6. Pruebas y aceptación

- TDD con rojo visto en cada pieza; oráculos a mano; datos ficticios (fixtures de observaciones de mercado ficticias).
- Fronteras: estadísticas con 0, 1, 2 y muchas observaciones; observaciones en otra moneda (no se mezclan); piso mayor que todo el
  mercado; lista para armar inexistente en una moneda; versión en aprobación que alguien intenta editar; dos dictámenes a la vez;
  quien arma aprueba su propia versión.
- **Aceptación en vivo (M6):** el recorrido de la obra ficticia (`scratchpad/obra_vivo/pasos`) se vuelve un recorrido versionado
  (`scripts/recorrido_obra.py` o filas nuevas del modo funcional) que hace la vivienda de 80 m² **en Bs, sin atajos**: carpeta →
  estudio de mercado (3 insumos, 1 partida) → componer 6 APU en Bs → nuevo proyecto en Bs → agregar las 6 partidas con su
  medición → guardar → enviar a aprobación → Rita devuelve con notas → Ana corrige y reenvía → Rita aprueba → Entregar la aprobada
  → línea base. Más un video grabado de ese recorrido.
- Recorridos visual y funcional de la barra siguen en verde.

## 7. Sub-rebanadas y orden

| Rebanada | Hace | Depende de |
|---|---|---|
| MP-1 | Moneda: `lista_para_armar`, Componer con moneda y lista derivada de hoy, avisos sin lista, listas de la carpeta en el panel | regla de coma |
| MP-2 | BCP-5 + BCP-6 en el panel de la barra; recordar carpeta y proyecto por cuenta; confirmación al cambiar con formulario sucio | — |
| MP-3 | Hoja: agregar/quitar partidas (buscador C-1), cómo se midió, Hoja de obra civil abre en Presupuesto, «Llevar a la Hoja» desde Elaborar | MP-1, MP-2 |
| MP-4 | Ciclo de aprobación: estados, enviar, por aprobar, dictamen, vuelta a quien arma, trazabilidad, Entregar y Control usan la aprobada | MP-3 |
| MP-5 | Estudio de mercado: observaciones, estadísticas, piso, propuesta, usar precio (compra → lista; cobro → objetivo en la Hoja) | MP-1 |
| MP-6 | Recorrido de la obra sin atajos + video + manual | todas |

MP-1 y MP-2 pueden ir en paralelo; MP-5 en paralelo con MP-3/MP-4. Cada rebanada: implementador → árbitro.

## 8. Lo que queda al constructor

La ubicación de «Estudio de mercado» en la barra; los textos finales (con revisión de vocabulario del árbitro); el nombre de la
tabla de aprobaciones y de observaciones y su migración; cómo se muestra la cadena de fases en la Trazabilidad; el ancho y orden de
columnas nuevas.

## 9. Decisiones de ingeniería tomadas aquí (las ratifica Eugenio al leer)

1. La lista correcta la elige `aplicacion/` por moneda (`lista_para_armar`), porque `lista_vigente` del núcleo no filtra por moneda.
2. Un precio tecleado hoy crea, si hace falta, una lista derivada de hoy en esa moneda (no se reescribe una lista vieja).
3. Estudio de mercado: propuesta de compra = mediana; de cobro = primer cuartil si supera el piso, si no el piso; ventana de 90
   días cambiable; la persona decide siempre.
4. Observaciones de mercado y aprobaciones viven en la carpeta de trabajo; la elección de carpeta/proyecto, por cuenta en
   `instalacion.db`.
5. Agregar/quitar renglón se registra con el objeto `cantidad` (campos `alta`/`baja`), sin tocar `OBJETOS` del núcleo.
6. «Cómo se midió» se guarda como la regla del ítem manual, para que R1 no marque como ruido una medición declarada.
7. Una versión en aprobación o aprobada no se edita; se hace una nueva desde ella.
8. Quien arma puede aprobar su propia versión, y queda rotulado así.

## 10. Ajustes tras el revisor constructor (2026-10-25)

**Decididos por Eugenio**
- **D-MP1 · Una moneda por carpeta de trabajo** (opción a). Cada carpeta trabaja en una sola moneda: sus listas para armar,
  precios y APU están en esa moneda. Un proyecto en la otra moneda se valora con la conversión existente con la tasa del BCV,
  declarando tasa y fecha. Así `core/` (que elige la lista vigente sin mirar la moneda) no se toca y no hay mezcla posible. Esto
  **reemplaza** en §5.1 «para cada moneda (Bs, USD) la carpeta tiene su lista para armar»: la carpeta declara su moneda de trabajo
  (al crearla o, en las existentes, por la de su lista vigente); `lista_para_armar` devuelve la vigente de la carpeta; Componer
  muestra la moneda de la carpeta (no la pregunta); si la lista vigente no está en la moneda de la carpeta, se avisa y no se arma.
- **D-MP2 · Precio de un insumo:** en Componer, teclear un precio distinto para un insumo que ya existe crea una **variante solo
  para ese APU** (comportamiento actual del núcleo) y Sílice lo **avisa** antes de guardar; en el estudio de mercado, «Usar este
  precio» cambia el **precio del insumo en la lista para armar** (como la hoja INSUMOS del Excel) y antes muestra qué APU se
  moverán. Si la lista de hoy ya la usa una versión guardada, se crea otra derivada del mismo día («… (2)»).

**Decisiones de ingeniería (las ratifica Eugenio al leer)**
- **«Cómo se midió»**: dos campos. «Cálculo» (opcional): una expresión aritmética con coma decimal (`6*3-2`, `2,5*4`), que
  `aplicacion/` traduce a la sintaxis de `evaluar` y guarda como la regla del ítem **solo si** su resultado coincide con la cantidad
  (si la persona escribe el cálculo, la cantidad se rellena con su resultado); así R1 la reconoce. «Nota de medición» (texto libre,
  opcional) se guarda aparte. Sin cálculo, R1 sigue avisando, y el aviso se presenta en lenguaje llano («cantidad medida a mano sin
  cálculo: escriba cómo se obtuvo si quiere que Sílice la pueda verificar»).
- **Quién aprueba**: una acción nueva `aprobar_version` para los roles **revisa** y **arma** (decisión de Eugenio: quien arma
  también puede aprobar), con su fila en `seguridad/permisos.py` y `test_permisos`; el dictamen de alguien sobre su propia versión
  queda rotulado «aprobada por quien la armó». **Revisa** gana `cambiar_caso` (solo lectura de carpetas: no escribe) para llegar a
  la carpeta de lo que debe aprobar; «Por aprobar» lista los envíos de todas las carpetas (índice en `instalacion.db`: carpeta,
  proyecto, versión, estado) y abrir uno cambia la carpeta de esa sesión. Recordar carpeta y proyecto aplica a todas las cuentas.
- **Piso del estudio de mercado (cobro)**: costo directo + administración con los parámetros del **proyecto abierto** (si no hay,
  los por omisión de `ParametrosCosto`); el precio objetivo vale **por partida en la carpeta** (una sola moneda); el margen se
  compara con el **precio unitario con utilidad, sin IVA**.
- **Máquina de estados**: se puede hacer una versión nueva desde una en aprobación (las versiones ya son inmutables); **un solo
  envío pendiente por proyecto**: enviar otra versión retira la pendiente (queda «retirada», con su rastro); una versión devuelta
  no se reenvía tal cual: se corrige en una versión nueva.
- **Rastro verificable de aprobaciones**: cada envío y dictamen guarda el sello (SHA) del eslabón de la versión a la que se refiere y
  su propia huella encadenada a la anterior de ese proyecto (cadena paralela fuera de `core/`, verificable); la Trazabilidad
  la verifica y lo dice si se rompió.
