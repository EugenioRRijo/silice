# Sprint final del prototipo (SF): hoja del proyecto con metrajes, edición trazable y barra superior

| Campo | Valor |
|---|---|
| Estado | **propuesta, revisión 3**: los cuatro encargos aprobaron con cambios en la ronda 2, sin bloqueantes, y esta revisión aplica esos cambios (§16). Pendiente de la aprobación de Eugenio; los cambios en `core/` necesitan además el visto bueno del tutor (§12.3) |
| Fecha | 2026‑10‑04 |
| Rama | `inc/spec-sf`, desde `main` = `1a02530` (fusión del PR #19, caso TI‑001) |
| Sprint | SF, «sprint final del prototipo»; fases SF0 a SF5 (§13) |
| Documentos que enmienda | [ERS](../ERS.md), [arquitectura](../arquitectura.md), [modelo de datos](../modelo_datos.md), [plan de pruebas](../plan_pruebas.md), [guion de prueba](../guion_prueba_arenia.md), [NORMAS.md](../../NORMAS.md) §6, [PLAN_CIERRE.md](../../PLAN_CIERRE.md) |
| Naturaleza de los datos | igual que [NORMAS.md §1](../../NORMAS.md): los casos son construidos para el proyecto; los precios, referencias publicadas MaPreX de julio de 2026 |

Este documento es la **fuente única** del diseño del sprint. El plan de sesiones (`PLAN_SF.md`) se
escribe después de aprobarlo y no repite este texto: lo enlaza.

---

## 1. Qué se quiere y por qué

### 1.1 Lo que pidió Eugenio (2026‑10‑03 y 2026‑10‑04)

1. Cerrar el prototipo funcional con un sprint final.
2. Que presupuestos, APU, curvas y punto de equilibrio sean **editables dentro del sistema**, como
   una hoja de cálculo: el usuario cambia una línea y el sistema recalcula, se audita y deja
   **trazabilidad de origen** del cambio. Esa misma hoja se exporta a Excel.
3. Que un presupuesto nuevo parta de **metrajes como dato de entrada**. En TI‑001 las cantidades
   (metros de cable, de tubo, número de equipos HP) se dieron por hechas. El dato de entrada es el
   **espacio**: cuántos metros hacen falta para pasar los tubos por pared, techo o piso hasta cada
   punto, por ejemplo una toma de agua en una casa u oficina.
4. Tres especialidades con reglas propias: **agua, datos y electricidad**.
5. **Importar un plano** (DXF de AutoCAD e IFC de Revit) como dato de entrada, con la **hoja de
   metrajes** dentro del sistema como punto fuerte.
6. Saber **de dónde salen los precios**.
7. Una interfaz cómoda con una **barra superior** y las herramientas pertinentes.
8. Este spec, con las metodologías pertinentes, para aprobarlo.

### 1.2 Lo que se encontró en el repositorio (2026‑10‑04)

- **Los metrajes de TI‑001 son supuestos.** `data/samples/telecom/topologia_ti001.csv` declara
  longitudes por puesto (18 m, 19,5 m…) y reservas (10 % en UTP, 5 % en EMT) sin plano ni
  levantamiento ([bitácora del caso](../bitacora/2026-09-30-caso-ti001.md)). R1 comprueba que la
  cantidad coincide con su regla, no que la **medida de entrada** tenga origen.
- **El punto de equilibrio solo existe en un script del caso** (`scripts/analisis_ti001.py:305`).
- **Se edita y persiste poco:** la composición de un APU (UC‑10, UC‑11) y el plan de trabajo en
  Elaborar (`ui/paginas/elaborar.py:377`). Escenarios edita precios de ensayo sin persistirlos
  (`ui/paginas/escenarios.py:145`). Solo UC‑02 deja registro de cambio (`CambioPrecio`).
- **Las composiciones viven una vez por partida en el catálogo** y se reemplazan en el sitio
  (`core/catalog/repositorio.py:188`); `cargar_presupuesto` las reconstruye y exige que el PU cuadre
  con la instantánea (`core/budget/persistencia.py:403-425`). Editar un APU hoy rompe la recarga de
  cualquier presupuesto anterior que lo use. [modelo_datos.md](../modelo_datos.md) (625‑630) declara
  que las composiciones no tienen vigencia y difiere la extensión «hasta que un caso de uso la exija»,
  pero afirma que eso «no afecta a los presupuestos emitidos»; la recarga demuestra lo contrario y SF0
  enmienda esa frase.
- **`descartar_version`** (`core/budget/actualizacion.py:207`) descarta solo la última versión, una
  vez; el esquema no guarda de qué versión salió otra.
- **`elaborar` audita siempre con las siete reglas** (`core/budget/presupuesto.py:155`); `auditar` sí
  admite otras (`core/verification/informe.py:178`). Recarga, revaloración, escenarios, importación y
  la API también auditan con las siete por defecto.
- **`ItemComputo.parametros` es `Mapping[str, Decimal]`** (`core/contracts/item_computo.py:42`): no
  admite textos. Las claves de `especificaciones` que empiezan por `_` son directivas que R4 ignora
  (`core/verification/directivas.py`).
- **`Dominio` tiene cuatro valores**: civil, telecom, industrial y sistemas.
- **La interfaz** es Streamlit 1.62 (`uv.lock`) con diez pantallas y navegación lateral; esa versión
  admite `st.navigation(position="top")`. `pyproject.toml` pide `streamlit>=1.36`.
- **Hallazgos sin corregir de TI‑001:** A‑1 (subidas de la interfaz sin limpiar el nombre), A‑2 (R4
  por subcadena), M‑1 (inyección de fórmulas en el Excel), M‑2 (el TOTAL redondeado del Excel no
  cuadra con la suma de las filas redondeadas) y M‑3 (el adaptador telecom pone `origen` y `destino`
  en `especificaciones` y R4 emite 40 INFO).

### 1.3 De dónde salen los precios (respuesta al punto 6)

Ningún precio se busca en internet. Todos salen de los listados **MaPreX de julio de 2026** que
aportó Eugenio (`data/precios/maprex_2026-07/`: materiales, equipos y mano de obra del software MaPreX
v26, base del 08/07/2026), en bolívares, convertidos con **633,3644 Bs/USD**, la tasa que declara el
propio listado al 01/07/2026. Las laptops y el servidor de TI‑001 se valoraron con referencias de
categoría (OFI058, OFI131) como material, no con una cotización de HP (ruling T‑3 del caso). Los
listados son referencia, no lista vigente ([README](../../data/precios/maprex_2026-07/README.md)).
Este sprint muestra ese origen en la interfaz y permite registrar una cotización con su fuente
(RF‑56).

### 1.4 Criterio de éxito del sprint

Una persona que no es el autor levanta el espacio de una oficina (o lo importa de un plano), obtiene
el presupuesto de agua, datos y electricidad con su auditoría, cambia una línea, ve el recálculo y el
registro de ese cambio, y exporta el Excel, sin ayuda y sin tocar un archivo fuera del sistema. Se
mide con CP‑08 a CP‑11 (§11.4) y RNF‑13.

---

## 2. Relación con el plan de cierre y con Med

[PLAN_CIERRE.md](../../PLAN_CIERRE.md) congeló el alcance funcional hasta cumplir F1–F5. Este spec es
una **enmienda** a ese límite:

- SF se inserta **después de GC6 y antes de Med**. Med mide la interfaz con personas (CP‑07,
  indicador 3, juicio de expertos de RNF‑04); medir antes de cambiarla invalidaría la medición.
- **Los instrumentos de Med se protegen así:**
  - `exportar_excel` (el libro de **cuatro hojas** de Elaborar, que exigen CP‑05, CP‑07, el
    indicador 3 §4, RNF‑04 y `test_exportar_excel_escribe_cuatro_hojas`) **conserva su estructura**.
    La hoja del proyecto se exporta con una función nueva (§9.5). M‑1 se corrige en las dos.
  - Las dos **huellas SHA‑256** que ancla RNF‑04 (la del informe de la fixture de siete
    inconsistencias y la del contenido del libro `.xlsx`) se vuelven pruebas de regresión del sprint.
    Si SF‑E5 (R4) o M‑1 (que también toca `exportar_excel`) cambian alguna, se registra un ruling de
    reanclaje antes de la primera sesión de Med, como el C6‑11.
  - Los **pasos** del guion (CP‑07 incluido, porque la navegación pasa arriba) y de los dos
    protocolos se actualizan **una sola vez, al cerrar la última fase entregada** (GSF5, o GSF4 si
    SF5 cae), con revisión por encargo y registro en la bitácora como cambio previo a la primera
    sesión. El método y los umbrales de los protocolos no cambian.
  - El commit que se mide en Med es posterior a la última compuerta de SF.
- F1–F5 no cambian. `v1.0-tesis` (F3) sigue después de Med.
- La redacción sigue en pausa. Cuando se retome, la Red aclara en el capítulo I (1.5.2) que importar
  un DXF o IFC vectorial no es la «digitalización automática de planos» excluida, y que el punto de
  equilibrio del contrato no es la «evaluación financiera del proyecto de inversión» excluida.

---

## 3. Alcance

**Incluye:** hoja de metrajes con modelo espacial (§6); reglas de cantidades de agua, datos y
electricidad (§7); auditoría espacial y corrección de A‑1, A‑2, M‑1, M‑2 y M‑3 (§8); hoja del proyecto
con edición, versiones, restauración y registro de cambios (§9); punto de equilibrio (§9.4); Excel de
la hoja con fórmulas vivas (§9.5); origen visible de cada precio y cotizaciones por proyecto (§9.6);
creación de proyectos desde la interfaz (§9.7); barra superior (§10); importación de DXF e IFC (§6.6);
caso OF‑001 (§11.1).

**No incluye:**

- Dibujar planos o editar geometría en un lienzo. La hoja es tabular.
- Planos en PDF o escaneados (capítulo I, 1.5.2).
- Volver a importar un Excel editado fuera del sistema (DA‑SF‑4).
- Usuarios con contraseña. El «responsable» es un nombre que el usuario declara.
- Rutas nuevas de la API para la hoja. La API conserva sus rutas; lo que cambia es que sus informes
  conservan los hallazgos de R8–R10 (SF‑E1).
- Una interfaz web nueva (React): trabajo futuro.
- Dimensionar la instalación (caudales, caídas de tensión, cálculo estructural): las reglas cuentan
  materiales, no los dimensionan.
- El cálculo diferencial de RF‑20 sigue sin implementarse; la hoja recalcula completo.

---

## 4. Requisitos (enmienda a la ERS, IEEE 830)

**Numeración.** En la ERS vigente el último UC asignado es UC‑12, el último RF asignado es **RF‑43**
(RF‑32 vacante, reservado a UC‑09) y el último RNF es RNF‑10. Los RF nuevos van de **RF‑44 a RF‑63**.
La nota de la ERS que reserva para UC‑09 «el siguiente al número más alto asignado» se enmienda para
que, tras SF, ese número sea RF‑64. Los conteos de la ERS pasan de 42 a **62 RF** y de once a
**quince UC** (la meta S1 los comprueba). El actor **gerente** se agrega a la tabla de actores.

### 4.1 Casos de uso

Los UC nuevos se escriben completos en la ERS en SF0 (actores, precondiciones, flujo principal,
alternos y postcondiciones). Aquí, su resumen y los flujos alternos ya conocidos:

| UC | Nombre | Actor | Precondición | Flujos alternos conocidos |
|---|---|---|---|---|
| UC‑13 | Levantar el espacio y los metrajes | proyectista | proyecto abierto | 13a fila sin origen de medida: se acepta en la versión y R8 la marca ERROR; 13b punto fuera de su ambiente: R9 |
| UC‑14 | Importar un plano a la hoja | proyectista | proyecto abierto | 14a DXF sin `$INSUNITS`: se detiene y pide la unidad; 14b entidades fuera de convención: van al informe, no a la hoja; 14c reimportar el mismo plano: empareja por *handle* o `GlobalId` (como UC‑04 2a), actualiza, agrega y marca las filas que desaparecieron; 14d archivo malformado o mayor de 20 MB: se rechaza con un mensaje, sin *traceback* |
| UC‑15 | Editar la hoja del proyecto | proyectista | **cualquier** presupuesto guardado, con o sin espacio (clínica, TI‑001, importado de UC‑05) | 15a guardar sin fuente o responsable: se rechaza; 15b plan con una partida que no suma 1: se rechaza (como UC‑01 paso 6); 15c salir con ediciones sin guardar: aviso; 15d restaurar una versión anterior; 15e versión sin instantánea de composiciones (anterior a SF‑E6, o importada de UC‑05): al abrirla, la hoja crea la instantánea desde el catálogo vigente y lo registra; si una partida no tiene composición en el catálogo, su APU queda en solo lectura |
| UC‑16 | Analizar el punto de equilibrio | proyectista, gerente | presupuesto guardado | 16a sin plan: PE sin ubicación en la curva; 16b margen ≤ 0: no existe PE; 16c PE > V: no se alcanza |

UC existentes que se enmiendan:

| UC | Enmienda |
|---|---|
| UC‑01 | La hoja de metrajes es una fuente de cantidades más (flujo alterno). El paso 1 («la interfaz no crea proyectos», C6, INV‑086) se enmienda: la interfaz crea proyectos (RF‑63) |
| UC‑02 | Sin cambios en su pantalla. La cotización de la hoja (RF‑56) es un camino propio que conserva el plan |
| UC‑04 | La hoja realiza el recálculo ante cambio de dimensiones para proyectos con espacio; RF‑20 (diferencial) sigue no implementado |
| UC‑11 | Sigue siendo el único camino para cambiar una composición **del catálogo**. La hoja edita una copia de la versión (DA‑SF‑7) y ofrece «promover al catálogo» por UC‑11 |
| UC‑12 | Los recorridos guiados incluyen la hoja |

### 4.2 Requisitos funcionales

Prioridad: E = esencial, D = deseable.

| RF | Requisito | UC | Pri. | Fase | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑44 | La hoja de metrajes registra ambientes, fuentes, puntos, recorridos y orígenes de medida (§6.2) | UC‑13 | E | SF1 | cada tipo de origen exige su referencia (§6.3); faltando una, la fila se acepta en la versión y R8 la marca ERROR |
| RF‑45 | El sistema propone un recorrido para cada punto (§6.4) y el usuario lo reemplaza declarando vértices | UC‑13 | E | SF1 | longitudes del recorrido propuesto del baño de OF‑001 = memoria de cálculo; un recorrido declarado sustituye al propuesto |
| RF‑46 | La geometría une los segmentos coincidentes, parte los solapes colineales y guarda los segmentos derivados con sobrescritura opcional de diámetro y de empotrado (§6.5) | UC‑13 | E | SF1 | solapes parciales de la memoria de cálculo dan la longitud unida esperada a ± 0,001 m |
| RF‑47 | Reglas de cantidades de **agua** (agua fría y drenaje), con fuente o supuesto declarado (§7.1) | UC‑13 | E | SF1 | cantidades del baño de OF‑001 = memoria de cálculo |
| RF‑48 | Reglas de cantidades de **datos** (§7.2) | UC‑13 | E | SF2 | cantidades de datos de OF‑001 = memoria de cálculo |
| RF‑49 | Reglas de cantidades de **electricidad**, con recorrido por circuito y orden de la cadena propuesto por vecino más cercano y editable (§7.3) | UC‑13 | E | SF2 | cantidades eléctricas de OF‑001 = memoria de cálculo |
| RF‑50 | Importación de DXF con la convención de §6.6.1, detención si falta `$INSUNITS`, informe de importación y reimportación por *handle* | UC‑14 | D | SF5 | el DXF de OF‑001, con alturas cargadas, da las mismas cantidades derivadas que la hoja manual |
| RF‑51 | Importación de espacios, terminales y tableros desde IFC, con informe de importación y reimportación por `GlobalId` | UC‑14 | D | SF5 | el IFC de prueba da las filas esperadas; hereda la salvedad de RNF‑09 si el archivo es programático |
| RF‑52 | La hoja del proyecto edita las celdas de entrada de §9.2 y recalcula y audita en el borrador sin persistir | UC‑15 | E | SF3 | una edición cambia totales, curva, PE y columna Estado sin crear versión |
| RF‑53 | Guardar crea una versión nueva con su informe, la instantánea de sus composiciones y de su espacio, y un `RegistroCambio` por celda cambiada; exige fuente del cambio y responsable | UC‑15 | E | SF3 | sin fuente o sin responsable se rechaza; la versión anterior sigue cargando idéntica |
| RF‑54 | Restaurar una versión N crea una versión nueva copia de N, con su `RegistroCambio`; el historial solo crece | UC‑15 | E | SF3 | tras restaurar, la versión nueva es igual a N y N sigue existiendo |
| RF‑55 | La columna Estado de cada fila muestra el peor hallazgo que la toca y enlaza a su detalle | UC‑15 | E | SF3 | un error sembrado en una fila marca esa fila y ninguna otra |
| RF‑56 | Cada precio muestra lista, referencia, fecha, moneda original y tasa con su fecha; una cotización se registra con su fuente, con alcance del proyecto, y prevalece sobre la lista global para ese insumo hasta que se retire | UC‑15, UC‑02, UC‑07 | E | SF3 | la cotización cambia solo ese insumo en ese proyecto; la versión resultante conserva el plan y la curva; una actualización global posterior por UC‑02 no la pisa |
| RF‑57 | Parámetros del proyecto editables (los de `ParametrosCosto`: FCAS, administración, utilidad y los demás que ya define el contrato) con fuente | UC‑15 | E | SF3 | cambiar el FCAS recalcula todos los APU de la versión y queda en el registro |
| RF‑58 | Punto de equilibrio calculado por el sistema y ubicado en la curva, con los casos límite de §9.4 | UC‑16 | E | SF3 | TI‑001 da 28 586,76 USD en el Día 6 (literal de la bitácora); cada caso límite da su salida declarada |
| RF‑59 | Exportación de la hoja del proyecto a Excel con fórmulas vivas, hojas de la hoja, trazabilidad y auditoría (§9.5) | UC‑15 | E | SF3 | las fórmulas evaluadas dan los totales del sistema dentro de la tolerancia de §9.5 |
| RF‑60 | Barra superior con navegación arriba y las herramientas de §10 | todos | E | SF4 | AppTest: navegación arriba, modo entrega oculta Investigación, cada herramienta lleva a su acción |
| RF‑61 | Reglas de auditoría R8, R9 y R10 (§8.2) | UC‑13, UC‑15 | E | SF1–SF2 | un error sembrado por condición, con valores frontera, se detecta |
| RF‑62 | Los hallazgos de reglas que no están en las siete se conservan al recargar, revalorar, simular escenarios, importar y en la API (§8.4) | UC‑05, UC‑15 | E | SF1 | el informe recargado de una versión con hoja es idéntico al emitido |
| RF‑63 | La interfaz crea proyectos con nombre único y no vacío | UC‑01 | E | SF4 | nombre vacío o repetido se rechaza con mensaje |

### 4.3 Requisitos no funcionales (ISO/IEC 25010)

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑11 | Eficiencia de desempeño | En `ui.hoja`, sin Streamlit, desde aplicar una edición hasta tener presupuesto, informe y PE (sin persistir): mediana ≤ 2 s para un proyecto de 500 puntos | `scripts/medir_rnf11.py` con un generador determinista versionado (en SF0); una corrida de calentamiento y la mediana de cinco. El veredicto se toma en el equipo de desarrollo, como RNF‑03; la CI ejecuta el script en Linux y Windows y **registra** la cifra sin romper la corrida. Todo se anota en plan_pruebas §10 |
| RNF‑12 | Seguridad | Ningún texto exportado se interpreta como fórmula (prefijos `=`, `+`, `-`, `@`, tabulador, retorno de carro) y un número negativo sigue siendo número; ningún archivo subido sale de su carpeta (`..\`, `../`, ruta absoluta, nombres reservados de Windows); DXF/IFC de más de 20 MB o malformados se rechazan con un mensaje | pruebas por caso |
| RNF‑13 | Usabilidad | En las condiciones de CP‑07, con el **mismo número y perfil** de participantes que CP‑07 pero **personas distintas**: cada caso de CP‑08 a CP‑11 se completa sin ayuda en ≤ 15 min por todos los participantes, el bloque B da ≥ 4,0 y ningún ítem queda < 3. Veredicto por caso | guion, en Med; consigna, paradas y criterio fijados antes de medir; el costo en participantes se suma al plan de Med |

---

## 5. Arquitectura (vistas 4+1)

### 5.1 Principio que se conserva

[NORMAS.md §2](../../NORMAS.md): núcleo cerrado, adaptadores abiertos. Lo **propio de una
especialidad o de un formato de plano** va en `adapters/`. Lo **genérico de cualquier presupuesto**
(versionar una edición, registrar el cambio, conservar hallazgos, punto de equilibrio, Excel, origen
de precios) va en `core/` con expediente, como en C5 y C6. Ningún expediente es específico de agua,
datos o electricidad: por eso no contradice RNF‑05 ni RF‑09 («un dominio nuevo no modifica `core/`»).
Cada expediente lo argumenta.

### 5.2 Vista lógica

| Paquete | Qué contiene | Importa | Toca `core/` |
|---|---|---|---|
| `adapters/espacio/` (nuevo) | modelo espacial, geometría (recorridos, unión de segmentos, conteo de accesorios), persistencia propia `esp_*` versionada, derivación de `ItemComputo`, reglas R8–R10 | `core.contracts`, sqlalchemy | no |
| `adapters/espacio/especialidades/` | `agua.py`, `datos.py`, `electricidad.py` | `core.contracts` | no |
| `adapters/espacio/planos/` | `dxf.py` (ezdxf), `ifc.py` (ifcopenshell; duplica lo necesario de `adapters/civil/ifc.py`, porque un adaptador no importa otro) | `core.contracts` | no |
| `adapters/telecom/` | M‑3: deja de emitir `origen` y `destino` como especificaciones (los traza `origen_id`) | `core.contracts` | no |
| `ui/hoja.py` (nuevo, sin Streamlit) | borrador en memoria, derivación, elaboración con reglas extra, PE, guardado en una sola transacción, restauración, exportación | `adapters.espacio`, `core` | no |
| `ui/barra.py` (nuevo) | barra de herramientas; la importa solo `ui/app.py`; delega las acciones en `ui.hoja` | `ui.hoja`, `ui.caso` | no |
| `ui/paginas/hoja.py` (nueva) | la pantalla de la hoja | `ui.*` | no |
| `core/budget/presupuesto.py` | `elaborar(..., reglas=REGLAS)` | — | **SF‑E1** |
| `core/budget/persistencia.py`, `actualizacion.py`, `escenarios.py`, `importacion.py` | conservan los hallazgos guardados de reglas externas (§8.4) | — | **SF‑E1** |
| `core/budget/edicion.py` (nuevo) y `core/models` | versión nueva desde una edición, `RegistroCambio`, restaurar una versión; **toda** versión nueva (edición, restauración, cotización, UC‑02) guarda su `version_origen`; versión vigente = la de mayor id no descartada | — | **SF‑E2** |
| `core/budget/equilibrio.py` (nuevo) | `punto_equilibrio(presupuesto, parametros)`, función pura | — | **SF‑E3** |
| `core/budget/excel.py` | `exportar_hoja(...)` nueva con `hojas_extra: Sequence[TablaExportable]`; M‑1 en las dos exportaciones; `exportar_excel` conserva sus cuatro hojas | — | **SF‑E4** |
| `core/verification/reglas.py` | R4 compara especificaciones normalizadas (A‑2) | — | **SF‑E5** |
| `core/models`, `core/budget/persistencia.py`, `actualizacion.py` | instantánea de la composición y del rendimiento por versión. Todo camino del núcleo (recarga y su verificación de PU, revaloración por UC‑02, escenarios) toma la composición de la instantánea cuando existe y del catálogo solo para versiones anteriores a SF‑E6. Revalorar = líneas de la instantánea con los precios nuevos | — | **SF‑E6** |
| `core/models`, `core/catalog` | origen de precios (referencia por insumo, tasa y fecha de la tasa por lista) y listas con alcance de proyecto; `lista_vigente` excluye las listas de proyecto; al revalorar por UC‑02 una versión con lista de proyecto, la cotización se aplica sobre la nueva lista base | — | **SF‑E7** |

`adapters/espacio` **no** implementa `AdaptadorDominio` (`core/contracts/adaptador.py`): su fuente es
una hoja en base de datos, no un archivo, y emite varias especialidades. Es una «fuente de
cantidades» con su propia interfaz `derivar(espacio, especialidad) -> list[ItemComputo]`.

### 5.3 Vista de procesos: una edición

```
usuario edita una celda de entrada
  -> ui.hoja aplica el cambio al borrador (st.session_state, clave que no es de widget)
  -> adapters.espacio deriva los ItemComputo (si cambió el espacio)
  -> core.budget.elaborar(items, composiciones de la versión, parámetros, plan,
                          reglas = REGLAS + reglas_espacio(instantánea del espacio))
  -> core.budget.equilibrio.punto_equilibrio(presupuesto, parámetros)
  -> la pestaña activa se repinta; la columna Estado va aparte de las celdas editables
usuario pulsa «Guardar versión»
  -> en una sola Session: core.budget.edicion guarda la versión, su informe, la instantánea de
     composiciones y un RegistroCambio por celda; adapters.espacio copia las filas esp_* con la
     clave de la versión nueva
```

Cerrar sin guardar no deja rastro (aviso 15c). Restaurar es RF‑54.

**Espacio de las versiones que no crea la hoja.** Restaurar, cotizar y revalorar por UC‑02 crean
versiones fuera del guardado de la hoja. Esas versiones no copian filas `esp_*`: su espacio es el de
su `version_origen` (SF‑E2), subiendo por la cadena hasta la primera que tenga filas propias. Así
toda versión de un proyecto con espacio se puede volver a auditar con R8–R10.

### 5.4 Vista de desarrollo y física

- Dependencias: `ezdxf` en un extra `planos` (licencia a confirmar en SF0); un evaluador de fórmulas
  de Excel en el grupo de desarrollo, solo para pruebas (§9.5). `ifcopenshell` ya está en `civil`.
  `streamlit>=1.62` en el extra `ui`.
- Persistencia: el mismo SQLite del caso abierto. Las tablas `esp_*` llevan la clave de versión (id
  del presupuesto, sin clave foránea porque el adaptador no importa `core.models`), las crea
  `crear_esquema_espacio()` y un borrado de proyecto limpia sus filas. Se enmiendan
  [modelo_datos.md](../modelo_datos.md) («ninguna tabla es específica de un dominio»),
  `core/models/base.py` («esquema completo») y el conteo de entidades de NORMAS §6.
- `tests/unit/test_arquitectura.py`: `TERCEROS_POR_ADAPTADOR` agrega `"espacio": {sqlalchemy, ezdxf,
  ifcopenshell}` (primer adaptador con base de datos); `PROHIBIDOS_EN_UI` agrega `ui/hoja.py`
  (`streamlit`, `pandas`, `ui.caso`); `ui/barra.py` solo la importa `ui/app.py`.
- Rendimiento en Streamlit: la pestaña activa se elige con un control (`st.segmented_control`) o se
  aísla con `st.fragment`, para no ejecutar las ocho en cada edición; las composiciones de la versión
  se guardan en caché; el Excel se genera solo al pulsar Exportar.

### 5.5 Decisiones de diseño

| # | Decisión | Alternativa descartada | Costo si es errónea |
|---|---|---|---|
| DA‑SF‑1 | Streamlit con `st.data_editor`; si la prueba de SF0 falla, la hoja usa AG Grid (`streamlit-aggrid`) en la misma fase | React sobre la API | rehacer la pantalla de la hoja |
| DA‑SF‑2 | La hoja de metrajes en tablas propias del adaptador (`esp_*`), versionadas con el presupuesto | entidades en `core/models` | mover tablas a `core/` con expediente |
| DA‑SF‑3 | Agua y electricidad con `Dominio.CIVIL` («instalaciones de la edificación», como en la práctica venezolana) y datos con `Dominio.TELECOM`; la especialidad viaja en `especificaciones["_especialidad"]` | `Dominio.ELECTRICO` | expediente de contrato; mientras tanto, los conteos de la compuerta G2 mezclan electricidad con civil, y se declara |
| DA‑SF‑4 | El Excel exportado no se reimporta | importar el Excel editado | cambios hechos fuera sin auditar |
| DA‑SF‑5 | Una cantidad derivada se puede sobrescribir a mano, con fuente; R8 la marca como ADVERTENCIA | prohibirlo | el usuario saca el cálculo del sistema |
| DA‑SF‑6 | El plano importado nunca salta la hoja | importar directo al presupuesto | errores del plano sin revisar |
| DA‑SF‑7 | Editar un APU en la hoja cambia la **copia de la versión** (instantánea, SF‑E6), nunca el catálogo; «promover al catálogo» pasa por UC‑11 | editar el catálogo; o una partida variante con código nuevo | sin SF‑E6, no se puede volver a versiones anteriores |
| DA‑SF‑8 | R8–R10 se construyen con la instantánea del espacio de la versión y la consultan; no se serializa el espacio dentro de los ítems | coordenadas y orígenes en `parametros`/`especificaciones` | `parametros` no admite texto; R4 haría ruido |
| DA‑SF‑9 | Una cotización crea una lista de precios del proyecto (copia de la base con el insumo cambiado), que la versión referencia explícitamente | lista global por vigencia | la cotización de un proyecto cambiaría todos |

---

## 6. La hoja de metrajes

### 6.1 Coordenadas

Metros, eje z hacia arriba desde el piso terminado. Cada ambiente es un rectángulo (origen `x0, y0`,
`largo` en x, `ancho` en y, `alto`). Los no rectangulares se descomponen en rectángulos; el DXF los
aproxima por su caja envolvente y lo declara en el informe. Tolerancia geométrica: 0,001 m.

### 6.2 Tablas (`esp_*`, todas con la clave de versión)

| Tabla | Columnas |
|---|---|
| Ambientes | id, nombre, x0, y0, largo, ancho, alto, origen de medida |
| Fuentes | id, especialidad, tipo (acometida o montante de agua, colector de drenaje, rack, tablero), ambiente, x, y, z, origen |
| Circuitos | id, tablero, número, conductores (fase, neutro, tierra), calibre, puntos máximos, orden de la cadena |
| Puntos | id, especialidad, tipo (agua fría, drenaje, datos, tomacorriente, iluminación), ambiente, superficie (pared, techo, piso), x, y, z, fuente, circuito, especificaciones (diámetro, calibre, categoría), origen |
| Recorridos | id, punto o circuito, propuesto o declarado, vértices declarados |
| Tramos | recorrido, orden, superficie (pared, techo, plafón, piso, bandeja), empotrado o expuesto, vértices, pendiente (drenaje), longitud calculada |
| Segmentos (derivada) | resultado de la unión de tramos (§6.5), con sobrescritura opcional de diámetro y de empotrado |
| Orígenes de medida | id, tipo, referencia, fecha, responsable |

### 6.3 Origen de la medida

| Tipo | Referencia obligatoria |
|---|---|
| Plano | número de plano, lámina y revisión |
| DXF | archivo, capa y *handle* |
| IFC | archivo y `GlobalId` |
| Levantamiento en sitio | fecha y responsable |
| Supuesto | motivo; R8 lo marca como ADVERTENCIA |

El **origen de medida** es de la fila (de dónde sale el dato). La **fuente del cambio** es del
`RegistroCambio` (por qué se cambió y con qué respaldo). Son cosas distintas y se piden por separado.

### 6.4 Recorrido propuesto

- **Agua fría y datos:** desde la fuente sube al techo, recorre en x y luego en y por el techo, y
  baja por la pared hasta la altura del punto.
- **Drenaje:** desde el punto baja al piso y recorre en x y luego en y **por el piso**, con z
  decreciente según la pendiente declarada, hasta el colector.
- **Electricidad:** un recorrido por **circuito**: tablero → punto 1 → punto 2 … en el orden de la
  cadena (propuesto por vecino más cercano, editable); cada paso sube al techo, cruza y baja.

La longitud de un tramo es la distancia entre sus vértices; no se escribe a mano.

### 6.5 Unión de segmentos y conteo de accesorios

Los recorridos de una misma fuente forman un árbol. La geometría parte los solapes colineales
(también parciales) y une los segmentos coincidentes a 0,001 m. Sobre ese árbol:

- **Codo:** cada cambio de dirección entre dos segmentos consecutivos de un mismo camino, incluido el
  paso de vertical a horizontal (pared → techo). Un recorrido «sube, cruza en x, cruza en y, baja»
  tiene tres codos. Un codo sobre un tramo compartido cuenta **una vez** para el árbol, no una por
  recorrido.
- **Tee:** un nodo donde concurren d ≥ 3 segmentos cuenta d − 2 tees. El giro del ramal en una tee
  **no** cuenta además como codo: la tee ya lo resuelve.
- **Clave de un segmento:** sus dos extremos redondeados a 0,001 m más la fuente. Una sobrescritura
  (diámetro, empotrado) se guarda con esa clave; si la geometría cambia y la clave desaparece, R9
  marca la sobrescritura huérfana.
- **Caja:** una por punto, más las que el usuario declare en el recorrido.
- **Diámetro de un segmento compartido:** el mayor de los puntos que sirve, salvo sobrescritura. No se
  dimensiona la instalación (§3).
- **Empotrado o expuesto:** si dos tramos solapados difieren, vale el que declare el segmento; si no
  lo declara, R9 lo marca.

Antes del código de SF1 se versiona una **memoria de cálculo a mano** con un ejemplo dibujado de este
conteo (§11.2).

### 6.6 Importación de planos

El plano crea filas en la hoja con origen DXF o IFC y un **informe de importación** (también para
IFC). Lo que no sigue la convención va al informe y no se adivina. Límite de tamaño de archivo y error
controlado si está malformado (RNF‑12).

#### 6.6.1 DXF (convención de capas)

| Capa | Entidad | Se convierte en |
|---|---|---|
| `AMBIENTES` | polilínea cerrada con un texto adentro (nombre) | ambiente |
| `FTE-AGUA`, `FTE-DRENAJE`, `FTE-DATOS`, `FTE-ELEC` | bloque insertado | fuente |
| `PTO-AGUA`, `PTO-DRENAJE`, `PTO-DATOS`, `PTO-TOMA`, `PTO-LUZ` | bloque con atributos `ALTURA` y opcionales `DIAMETRO`, `CALIBRE`, `CIRCUITO` | punto |
| `REC-<especialidad>` | polilínea abierta | recorrido declarado (opcional) |

Unidades: `$INSUNITS`; si falta, la importación se detiene y pide la unidad. La altura de los
ambientes queda pendiente y R8 la marca hasta cargarla.

#### 6.6.2 IFC

`IfcSpace` (ambientes), terminales sanitarios, de datos, de tomacorriente y de iluminación, y
tableros. Las clases por esquema (IFC2x3 e IFC4) se fijan en SF0 con archivos de prueba de procedencia
declarada, y se enmienda la ERS §2.4 y §2.6, que hoy restringen a IFC 4 y dejan el reconocimiento de
planos como futuro. Si los archivos son programáticos, RF‑51 hereda la salvedad de RNF‑09.

---

## 7. Reglas de cantidades por especialidad

Cada regla produce `ItemComputo` con `origen_tipo = REGLA`, la expresión en `regla` y sus valores
numéricos en `parametros` (R1). `origen_id` cita la fila o el segmento `esp_*` que la produce. Cada
constante (desperdicio, holgura, límite) vive en una tabla de parámetros de la especialidad con su
**fuente**. Las fuentes candidatas se verifican en SF0 y se registran en
[referencias.md](../tesis/referencias.md); una constante sin fuente verificada es un **supuesto
declarado**, visible en la hoja.

**Cómo se mide cada material:**

- tubería y canalización: sobre la unión de segmentos (cada metro cuenta una vez);
- cable de datos: por recorrido (cada punto lleva su cable hasta el rack);
- conductor eléctrico: sobre la cadena del circuito, la misma geometría que su tubería.

### 7.1 Agua (agua fría y drenaje)

| Partida derivada | Regla |
|---|---|
| Tubería por material y diámetro (m) | longitud unida por diámetro × (1 + desperdicio) |
| Codos y tees | conteo de §6.5 |
| Llave de paso | una por punto de agua fría que la declare |
| Picado y resane de pared o piso (m) | longitud unida de segmentos empotrados |
| Salida de agua o de drenaje (punto) | una por punto |

R10: pendiente mínima del drenaje. Fuente candidata: Normas Sanitarias para proyecto, construcción,
reparación y reforma de edificaciones (Gaceta Oficial N.º 4.044 Extraordinario, 1988), a verificar.

### 7.2 Datos

| Partida derivada | Regla |
|---|---|
| Cable UTP por categoría (m) | (longitud del recorrido + holgura en rack + holgura en punto) × (1 + reserva) |
| Canalización por tipo y diámetro (m) | longitud unida |
| Cajas, *face plates* y *jacks* | uno por punto |
| Certificación (punto) | una por punto |

R10: enlace permanente ≤ 90 m. Fuente candidata: ANSI/TIA‑568, a verificar (ya la cita
`scripts/glosario_presupuestos.py`).

### 7.3 Electricidad (tomacorrientes e iluminación)

| Partida derivada | Regla |
|---|---|
| Conductor por calibre (m) | longitud de la cadena × conductores del circuito × (1 + desperdicio) |
| Tubería por tipo y diámetro (m) | longitud unida de las cadenas |
| Cajas (pieza) | conteo de §6.5 |
| Salida de tomacorriente o de iluminación (punto) | una por punto |
| Protección por circuito (pieza) | una por circuito |

R10: puntos por circuito ≤ máximo declarado. Fuente candidata: Código Eléctrico Nacional (COVENIN 200,
hoy FONDONORMA 200; el glosario del caso la cita como COVENIN 200), a verificar y registrar con una
sola denominación.

---

## 8. Auditoría

### 8.1 Lo que no cambia

R1–R7 conservan su enunciado. `elaborar` las corre siempre (principio 7). La línea base sigue dando
7 de 7 (`test_auditoria_7_de_7.py` sin modificarse).

### 8.2 Reglas nuevas (en `adapters/espacio`, implementan `ReglaVerificacion`)

| Regla | Comprueba | Severidad |
|---|---|---|
| R8 Origen de la medida | toda fila del espacio que produce una cantidad cita su **origen de medida** (no se refiere a `origen_id`, que RF‑03 ya garantiza); supuestos, alturas pendientes y sobrescrituras a mano se marcan | ERROR sin origen; ADVERTENCIA si es supuesto, pendiente o sobrescritura |
| R9 Coherencia espacial | punto y fuente dentro de su ambiente; ninguna altura supera la del ambiente; ningún recorrido más corto que la distancia ortogonal mínima entre sus extremos; segmentos solapados con empotrado distinto sin declarar; sobrescrituras de segmento huérfanas | ERROR |
| R10 Límites de la especialidad | pendiente del drenaje, 90 m por enlace de datos, puntos por circuito | ERROR si el límite tiene fuente verificada; ADVERTENCIA si es supuesto |

R8–R10 reciben la instantánea del espacio de la versión (DA‑SF‑8). Sus hallazgos citan en
`origen_ids` las claves `esp_*` de las filas, que es lo que usa la columna Estado. No implementan
`atribuir` (el protocolo `ReglaAtribuible` no es un contrato).

### 8.3 Correcciones de hallazgos pendientes

| Hallazgo | Corrección | Fase |
|---|---|---|
| A‑2 | R4 normaliza cada especificación a un valor comparable por clave (fracciones de pulgada; «2» frente a «1/2», «6» frente a «16», «1/2» frente a «1 1/2») y excluye del corpus la descripción del propio ítem | SF1 (SF‑E5) |
| M‑3 | el adaptador telecom deja de emitir `origen` y `destino` como especificaciones; los traza `origen_id` y la topología | SF2 |
| M‑1 | toda celda de texto con prefijo peligroso (RNF‑12) se exporta como texto, en las dos exportaciones | SF3 (SF‑E4) |
| M‑2 | ver §9.5 y ruling RS‑8 | SF3 (SF‑E4) |
| A‑1 | las pantallas con subida (`actualizacion`, `elaborar`, `visor`) usan una función de guardado seguro para el `UploadedFile` de Streamlit, con las mismas reglas que `api/archivos.py:16` | SF4 |

Se registran como hallazgos nuevos del [inventario](../auditoria/2026-09-inventario.md) al abrir SF0.

**Efecto previsto sobre TI‑001.** Dos pruebas de caracterización cambian a propósito y se registran con
ruling y una adenda a la bitácora del caso: `test_auditoria_cumple_sin_errores` deja de ver los 40
INFO de R4 (M‑3), y `test_pruebas_de_control` pasa a detectar el control de 1/2 pulg (A‑2). El total
(50 503,27 USD), los PU y el punto de equilibrio no cambian.

### 8.4 Hallazgos de reglas externas al recargar (SF‑E1, RF‑62)

`elaborar` admite `reglas=`. En los demás caminos que auditan (recarga, revaloración, escenarios,
importación, API) se sigue el precedente de `CODIGO_ATIPICO` (expediente C6.5): los hallazgos
guardados cuya regla no está en `REGLAS` se vuelven a declarar en el informe. Cuando la hoja abre una
versión con espacio, `ui.hoja` vuelve a auditar con R8–R10 sobre la instantánea de esa versión, y esa
auditoría **reemplaza** los hallazgos guardados de esas mismas reglas; no se suman, así el informe no
duplica nada.

---

## 9. La hoja del proyecto

### 9.1 Pestañas y pantallas existentes

Una pantalla, «Hoja del proyecto», con pestañas: **Espacio y metrajes**, **APU**, **Presupuesto**,
**Plan y curva**, **Punto de equilibrio**, **Precios**, **Parámetros**, **Auditoría** y
**Trazabilidad**. La hoja abre cualquier presupuesto guardado; sin espacio, la primera pestaña queda
vacía y las cantidades se editan como sobrescritura (DA‑SF‑5).

| Pantalla actual | Qué pasa |
|---|---|
| Inicio | sigue; agrega el acceso a la hoja |
| Elaborar | sigue como entrada por CSV o IFC y su Excel de cuatro hojas; al terminar ofrece abrir el resultado en la hoja |
| Componer / editar partida (UC‑10, UC‑11) | siguen: son el catálogo. La hoja edita copias por versión |
| Actualizar precios (UC‑02) | sigue: lista global |
| Catálogo, histórico, visor, escenarios, similares, simulador | siguen |

Pasan a ser **once pantallas**: se enmiendan RF‑39 («diez pantallas»), RF‑37 y RF‑42 (orden del menú
y recorridos).

### 9.2 Qué se edita

| Pestaña | Editable | Calculado (bloqueado) |
|---|---|---|
| Espacio y metrajes | ambientes, fuentes, circuitos, puntos, vértices declarados, sobrescrituras de segmentos, orígenes | longitudes, segmentos unidos, cantidades derivadas |
| APU | cantidad de cada línea, insumo elegido y el rendimiento del APU (en la copia de la versión, DA‑SF‑7) | PU y totales |
| Presupuesto | sobrescritura de una cantidad (DA‑SF‑5) | PU, totales |
| Plan y curva | reparto de cada partida por período (cada partida suma 1) | montos, acumulados y porcentajes |
| Punto de equilibrio | nada propio: se mueve con lo demás (RS‑4) | todo |
| Precios | cotización con su fuente (§9.6) | precio vigente de la versión |
| Parámetros | los de `ParametrosCosto` (FCAS, administración, utilidad…); no se agregan parámetros nuevos al contrato | — |

La columna **Estado** (RF‑55) se pinta aparte de las celdas editables, para que el editor no se
reinicie en cada recálculo.

### 9.3 Versiones, registro y restauración

`RegistroCambio`: proyecto, versión de origen, versión resultante, objeto (metraje, APU, precio, plan,
parámetro), clave de la fila, campo, valor anterior, valor nuevo, **fuente del cambio**, responsable,
fecha y hora. **Todo** cambio guardado exige fuente y responsable. La versión de origen cierra la
limitación C3.2 (de qué versión salió otra) y se declara en el modelo de datos.

Cada versión guarda su instantánea de composiciones y rendimientos (SF‑E6) y la de su espacio
(`esp_*`, o la de su `version_origen`, §5.3), así que cualquier versión se recarga idéntica.
**Restaurar** la versión N crea una versión nueva copia de N (RF‑54); nada se borra. La **versión
vigente** es la de mayor id no descartada; una restauración pasa a ser la vigente.

### 9.4 Punto de equilibrio (SF‑E3)

`punto_equilibrio(presupuesto, parametros)`, con `Decimal`, toma la definición del caso TI‑001
(`scripts/analisis_ti001.py:305-335`):

- CV = Σ cantidad × costo directo de cada partida;
- CF = CV × administración (de los parámetros de la versión);
- V = total del contrato; m = (V − CV) / V; PE = CF / m;
- ubicación: el primer período cuyo acumulado alcanza el PE y la fracción de ese período.

Casos límite: V = 0 → no aplicable; m ≤ 0 → «no existe punto de equilibrio»; PE > V → «no se alcanza
dentro del contrato»; sin curva → PE sin ubicación. El script del caso pasa a importar la función y
conserva sus literales (28 586,76 USD, 56,60 %, Día 6) como oráculo.

### 9.5 Excel de la hoja (SF‑E4)

- `exportar_hoja(...)`: una hoja por pestaña, misma disposición de columnas, más Trazabilidad y
  Auditoría. Las hojas que `core` no conoce (Espacio y metrajes, origen de precios) las arma `ui.hoja`
  como `TablaExportable`, un tipo genérico definido en `core.budget`; el escape de M‑1 se aplica
  también a ellas.
- Cantidades y precios se escriben **sin redondear**, con formato de presentación a dos decimales; los
  totales son fórmulas (`=cantidad*PU`, `=SUM(...)`). El archivo guarda los nombres de función en
  inglés (`SUM`, `ROUND`), que es lo que esperan openpyxl y el evaluador; Excel en español los muestra
  traducidos. Así el total del Excel coincide con
  `Presupuesto.total`, y el principio 3 de NORMAS (redondear solo al presentar) se respeta.
- M‑2: lo que no cuadra es la suma de las filas **mostradas** frente al total mostrado. Se resuelve
  según RS‑8; la propuesta es dejar el total exacto como contractual y agregar al pie una nota con la
  diferencia de redondeo de presentación.
- Prueba: un evaluador de fórmulas (por ejemplo, el paquete `formulas`, en el grupo de desarrollo)
  calcula cada total del libro y se compara con el `Decimal` del sistema con tolerancia de ± 0,005
  por celda presentada, porque Excel trabaja en coma flotante. Oráculo adicional: la línea base sigue
  sumando 1 586,61.

### 9.6 Precios con su origen (SF‑E7)

La pestaña Precios muestra por insumo: lista, referencia (el Ref de MaPreX), fecha del precio, moneda
original y tasa con su fecha. Hoy `ListaPrecios` guarda nombre, moneda, fecha de vigencia y origen,
sin tasa ni fecha de la tasa, y `PrecioInsumo` no guarda referencia; SF‑E7 las agrega. Una
**cotización** (proveedor, número y fecha, con la evidencia del
[protocolo de levantamiento de precios](../protocolo_precios.md)) crea una lista **del proyecto**:
copia de la lista base con ese insumo cambiado, que la versión referencia de forma explícita
(DA‑SF‑9). La versión resultante conserva el plan y la curva. Las listas de proyecto no entran en la
resolución global (`lista_vigente`). Si después UC‑02 carga una lista global nueva, la cotización
**prevalece** para ese insumo en ese proyecto: al revalorar, se aplica sobre la nueva lista base, hasta
que el usuario la retire (con su registro). Un insumo sin fuente o
sin fecha se marca en la columna Estado.

### 9.7 Proyectos

La herramienta Proyecto crea proyectos con nombre único y no vacío (RF‑63), abre el caso y muestra la
versión vigente.

---

## 10. Interfaz: barra superior

- Navegación arriba (`st.navigation(position="top")`) con los grupos Trabajo e Investigación; el modo
  entrega de P5.1 (RF‑43) sigue ocultando Investigación.
- Barra de herramientas fija, pintada por el marco común:

| Herramienta | Acción |
|---|---|
| Proyecto | nuevo (RF‑63), abrir, caso abierto y versión |
| Importar plano | DXF o IFC hacia la hoja (UC‑14); se oculta si SF5 no se entrega |
| Precios | pestaña Precios y cotización |
| Auditar | resumen del informe vigente (se audita siempre; el botón lo muestra) |
| Guardar versión | persiste el borrador (RF‑53) |
| Exportar Excel | genera y descarga el Excel de la hoja |
| Recorrido guiado | abre o retoma UC‑12 |

- La barra lateral queda para el caso abierto y el paso del recorrido.
- En SF4 revisa además un encargo de usabilidad (§12.2).

---

## 11. Pruebas y calidad (IEEE 829, ISO/IEC 25010)

### 11.1 Caso de demostración OF‑001

Una oficina construida para el proyecto sobre la planta de TI‑001: cuarto técnico con rack y tablero,
zonas A y B de puestos, recepción, un baño y una cocineta, con las tres especialidades en el mismo
espacio y precios MaPreX de julio de 2026. Se entrega como hoja cargada a mano y como DXF. El DXF se
**dibuja de forma independiente** (en un programa de CAD, o escrito entidad por entidad desde la
memoria de cálculo, nunca generado desde la hoja), con su procedencia declarada. TI‑001 conserva sus
datos y su total; sus dos pruebas de caracterización cambian según §8.3.

### 11.2 Pruebas automatizadas

Pruebas antes que código (NORMAS principio 5), con **evidencia del rojo**: el commit de la prueba va
antes que el de la implementación en SF‑E1 a SF‑E7 y en las reglas de especialidad (plan_pruebas §4).

**Oráculos independientes del código.** Antes del código de SF1 se versiona
`tests/fixtures/memorias/bano_of001.md`, y antes de SF2 `of001.md`: memorias de cálculo a mano con
longitudes, unión de segmentos, codos, tees, cajas, conductores por circuito y cantidades. Las
pruebas comparan con esas memorias, no con la expresión de R1 (que sería circular).

| RF / RNF | Prueba |
|---|---|
| RF‑44 | referencia obligatoria por tipo de origen; casos negativos |
| RF‑45, RF‑46 | recorridos propuestos y declarados; solapes parciales y totales a ± 0,001 m |
| RF‑47, RF‑48, RF‑49 | cantidades por especialidad = memoria |
| RF‑50 | DXF de OF‑001 con alturas cargadas = cantidades de la hoja manual a ± 0,001 m; DXF fuera de convención → informe sin filas; sin `$INSUNITS` → se detiene; reimportación por *handle* |
| RF‑51 | IFC de prueba → filas esperadas; informe |
| RF‑52, RF‑55 | edición en borrador; Estado marca solo la fila sembrada |
| RF‑53, RF‑54 | guardar sin fuente o responsable se rechaza; versión anterior recarga idéntica; restaurar crea copia |
| RF‑56 | origen visible; la cotización afecta solo al proyecto y conserva la curva |
| RF‑57 | cambio de FCAS recalcula y registra |
| RF‑58 | TI‑001 = 28 586,76 USD, Día 6; cada caso límite |
| RF‑59 | evaluador de fórmulas frente al sistema (§9.5) |
| RF‑60 | AppTest de la navegación arriba y del modo entrega |
| RF‑61 | por condición y con fronteras: 90,00 m pasa y 90,01 m falla; máximo de puntos por circuito y uno más; pendiente mínima y una menos; cada condición de R9; cada severidad de R8 |
| RF‑62 | informe recargado = emitido, en cada camino de §8.4 |
| RF‑63 | nombre vacío y repetido se rechazan |
| A‑2 | caso directo (3/4" en memoria, 4" en el APU, `docs/linea_base.md`) y los cuatro pares de la bitácora de TI‑001 |
| RNF‑11 | `scripts/medir_rnf11.py` (§4.3) |
| RNF‑12 | cada prefijo y cada ruta de §4.3 |
| Arquitectura | importaciones de `adapters.espacio`, `ui.hoja`, `ui.barra` |

**OF‑001 limpio** no da «cero hallazgos»: da el conjunto exacto esperado (regla, severidad y fila),
porque las constantes supuestas producen ADVERTENCIAS de R8; R10 solo marca incumplimientos y baja a ADVERTENCIA mientras su límite sea supuesto (RS‑11, pendiente de ratificar por Eugenio). *(Enmienda SF2, 2026‑10‑05; ver §16.)*

**Regresión en cada compuerta:** los cinco APU de la línea base a ± 0,01; 7 de 7 y
`test_r4_marca_3_4_pulg_y_no_marca_pvc` sin modificarse; total de TI‑001; las dos huellas de RNF‑04
(informe y contenido del `.xlsx`); cuatro hojas de `exportar_excel`.

Las filas nuevas de plan_pruebas §8 (trazabilidad), §8.1 (pasos de UC‑13 a UC‑16) y §9 (RNF‑11 a
RNF‑13) se escriben en SF0.

### 11.3 Prueba corta de SF0 (`st.data_editor`)

AppTest no escribe en `st.data_editor`, así que la prueba se hace en el navegador, con un
procedimiento fijado antes de ejecutar y registrado en la bitácora:

- datos: 500 puntos del generador de RNF‑11, que se escribe en SF0;
- cálculo sustituto (aún no existe `ui.hoja`): cada edición vuelve a llamar a `core.budget.elaborar`
  con los ítems generados, que es el mismo costo que tendrá la hoja sin la derivación espacial;
- ediciones: 20 de celda, 5 altas y 5 bajas de fila, una ordenación y 10 ediciones rápidas seguidas
  mientras el script se reinicia;
- columna Estado aparte de los datos editables; ediciones en `st.session_state` con clave que no es
  de widget; pestaña activa con control o `st.fragment`;
- medición: la propia aplicación registra la marca de tiempo de cada edición recibida y de cada
  Estado pintado, no un cronómetro.

**PASA** si no se pierde ninguna edición y la columna Estado se actualiza en ≤ 2 s tras cada una. Si
falla, la hoja usa AG Grid (DA‑SF‑1).

### 11.4 Casos de prueba con personas (guion, en Med)

CP‑08 a CP‑11 se escriben como casos IEEE 829 completos en el guion (precondición, pasos, resultado
esperado obtenido ejecutando el sistema y cotejado con las memorias), con base propia
`data/prueba_sf.db` vía `ARENIA_CASO` en la copia desechable y comprobación de `data/apu.db` antes y
después, como el guion §4.

| CP | Tarea | Traza |
|---|---|---|
| CP‑08 | Levantar a mano el baño de OF‑001 (un ambiente, una fuente, dos puntos de agua) y obtener su presupuesto auditado | UC‑13; RF‑44 a RF‑47, RF‑61 |
| CP‑09 | Importar el DXF de OF‑001 y corregir la fila que marca el informe (sale si SF5 cae) | UC‑14; RF‑50 |
| CP‑10 | Cambiar la cantidad de una línea de un APU, ver el recálculo y el punto de equilibrio, intentar guardar sin fuente (rechazo) y guardar con fuente | UC‑15, UC‑16; RF‑52, RF‑53, RF‑55, RF‑58 |
| CP‑11 | Ver el origen del precio de un insumo, registrar una cotización, ver la Trazabilidad y exportar el Excel (después de CP‑10) | UC‑15; RF‑56, RF‑59 |

RNF‑13 fija consigna literal, condiciones de parada y criterio antes de medir, y excluye a los
participantes ya expuestos a la tarea en otra medición (CP‑07, indicador 3, RNF‑04), con la misma
regla de exclusión cruzada de esos protocolos.

### 11.5 Calidad y cobertura

[calidad_iso25010.md](../calidad_iso25010.md) se amplía con RNF‑11 a RNF‑13. Cobertura de `core/` ≥ 80 %
(RNF‑06) y la misma meta para `adapters/espacio`, que la CI hace cumplir con un paso propio
(`coverage report --include="adapters/espacio/*" --fail-under=80`) y la meta S10; `ui.hoja` se prueba
aunque `ui/` no se mida. Suite con `-W error` y 0 omitidas en Linux y Windows (vigilar advertencias de ezdxf).

---

## 12. Metodología y gobierno

### 12.1 Marco

- **Scrum‑Cascada** ([metodologia.md](../metodologia.md)): fases SF0–SF5 en orden con compuerta
  (cascada); dentro de cada fase, tareas con *Definition of Done* (Scrum).
- **DRY:** la definición del punto de equilibrio sale del script y pasa a `core/`; el script la
  importa.
- **TDD** con evidencia del rojo (§11.2).
- **IEEE 830** para la ERS, **vistas 4+1** para la arquitectura, **IEEE 829** para el plan de pruebas
  y el guion, **ISO/IEC 25010** para la calidad; **heurísticas de Nielsen** e **ISO 9241‑110** para la
  revisión de la barra.
- **Expediente por cambio en `core/`** (SF‑E1 a SF‑E7): regla que lo motiva, por qué es genérico (no
  de una especialidad), prueba que lo demuestra, impacto y visto bueno del tutor.
- **Bitácora** `docs/bitacora/2026-10-sf.md` con rulings, expedientes y compuertas.

### 12.2 Compuertas, ramas y revisión

- **Ramas separadas para `core/` y adaptadores.** `scripts/guardia_nucleo.py` y la meta M9 fallan si
  una rama que agrega archivos en `adapters/` toca `core/`. Por eso, en cada fase con expedientes, los
  cambios de `core/` van en una rama y PR propios (`inc/sf<n>-nucleo`), fusionados primero; el
  adaptador y la interfaz van después en `inc/sf<n>` sin tocar `core/`.
- **GSF2** comprueba `git diff gsf1..HEAD -- core/` vacío en el momento de evaluarla: agregar datos y
  electricidad no toca el núcleo, que es la evidencia de la hipótesis de la tesis. **GSF5** hace lo
  mismo desde `gsf4`, porque la importación de planos también es de adaptador.
- Una fase se cruza cuando (a) `scripts/meta_sf.py --hasta SF<n>` está en OK, (b) la CI está verde en
  Linux y Windows y (c) aprueban los encargos:

| Encargo | Revisa con |
|---|---|
| Ingeniero de requisitos | IEEE 830 y la ERS enmendada |
| Arquitecto de software | vistas 4+1, NORMAS §2, §5 y §6, expedientes |
| Ingeniero de pruebas y calidad | IEEE 829 e ISO/IEC 25010 |
| Verificador de hechos | cada cita archivo:línea |
| Especialista en usabilidad (SF4) | heurísticas de Nielsen e ISO 9241‑110 |

- Etiquetas: `sf-base` en `main` al abrir SF0 y `gsf0`…`gsf5` por compuerta. Fusión por *merge
  commit*.

**Metas de `scripts/meta_sf.py`** (con su `tests/unit/test_meta_sf.py`; lo que aún no existe da
PENDIENTE, no FALLA):

| Meta | Qué evalúa | Desde |
|---|---|---|
| S1 Requisitos | UC‑13 a UC‑16, RF‑44 a RF‑63 y RNF‑11 a RNF‑13 en la ERS | SF0 |
| S2 Memorias | memorias de cálculo versionadas antes del código de su fase | SF1 |
| S3 Especialidades | pruebas de agua, datos y electricidad en verde | SF1–SF2 |
| S4 Núcleo por adaptadores | `git diff gsf1..HEAD -- core/` vacío al cerrar SF2, y `gsf4..HEAD` al cerrar SF5 | SF2, SF5 |
| S5 Hoja | pruebas de edición, versiones, restauración, PE y Excel en verde | SF3 |
| S6 Barra | AppTest de navegación y herramientas | SF4 |
| S7 Planos | pruebas de DXF e IFC | SF5 |
| S8 Regresión | línea base, 7 de 7, R4 de 3/4 pulg, TI‑001, las dos huellas de RNF‑04, cuatro hojas | todas |
| S9 RNF‑11 | mediana registrada ≤ 2 s en el equipo de desarrollo | SF3 |
| S10 Cobertura del espacio | `adapters/espacio` ≥ 80 % | SF1 |

### 12.3 Lo que decide el tutor

Los expedientes SF‑E1 a SF‑E7 y, si lo pide, DA‑SF‑3 (un `Dominio` propio). Si rechaza un expediente,
la fase se entrega sin esa pieza y se declara. SF‑E6 es requisito de RF‑53 y RF‑54: sin él, la hoja
no edita APU.

---

## 13. Fases

| Fase | Contenido | Funciona al cerrar | Compuerta |
|---|---|---|---|
| **SF0** | ERS, arquitectura, modelo de datos y plan de pruebas enmendados; fuentes de §7 verificadas; licencia de ezdxf; clases IFC; inventario A‑1…M‑3; generador de 500 puntos; prueba corta de §11.3; `meta_sf.py` | documentos aprobados y DA‑SF‑1 confirmada | GSF0 |
| **SF1** | Núcleo: SF‑E1, SF‑E5. Adaptador: `adapters/espacio` (modelo, geometría, unión, `esp_*` versionada, orígenes), **agua**, R8 y R9, memoria del baño, pestaña Espacio y metrajes | el baño de OF‑001 se levanta a mano y sale su presupuesto auditado | GSF1 |
| **SF2** | **Datos** y **electricidad**, R10, M‑3, memoria y OF‑001 completo; sin tocar `core/` | la oficina con tres especialidades | GSF2 |
| **SF3** | Núcleo: SF‑E2, SF‑E3, SF‑E4, SF‑E6, SF‑E7. Hoja: pestañas restantes, borrador, guardado, restauración, cotización, Excel, RNF‑11 | editar una línea, ver el recálculo, guardar con su registro, restaurar y exportar | GSF3 |
| **SF4** | Barra superior y herramientas, creación de proyectos, A‑1, once pantallas y recorridos, manuales | la aplicación completa con la barra | GSF4 |
| **SF5** | Importación DXF e IFC, informe, reimportación, DXF de OF‑001; al cerrar, actualización del guion (CP‑07 a CP‑11) y de los pasos de los protocolos de Med (§2) | el DXF de OF‑001 da las mismas cantidades que la hoja | GSF5 |

**Si el tiempo aprieta**, se cae primero SF5 (la importación pasa a trabajo futuro, CP‑09 sale, la
herramienta se oculta y la actualización del guion se hace al cerrar SF4), y dentro de SF5 primero el
IFC. Recortar SF5 deja sin cumplir un pedido explícito de Eugenio: requiere su aceptación (RS‑7).
SF1–SF4 no se recortan.

---

## 14. Rulings para ratificar

| # | Decisión | Costo si es errónea |
|---|---|---|
| RS‑1 | Streamlit con `st.data_editor` (DA‑SF‑1) | rehacer la pantalla de la hoja con AG Grid |
| RS‑2 | Agua y electricidad con `Dominio.CIVIL` (DA‑SF‑3) | expediente para un `Dominio` nuevo |
| RS‑3 | El Excel no se reimporta (DA‑SF‑4) | una fase extra de importación con auditoría |
| RS‑4 | Definición del punto de equilibrio (§9.4); el PE es derivado, no se edita directamente: se mueve al editar costos, parámetros o plan | cambiar una función pura y sus pruebas |
| RS‑5 | Constantes de especialidad sin fuente verificada como supuesto declarado | cifras discutibles hasta verificarlas |
| RS‑6 | SF va antes de Med (§2) | Med mediría una interfaz que ya no existe |
| RS‑7 | Si falta tiempo, SF5 se difiere con aceptación de Eugenio | la importación de planos queda como trabajo futuro |
| RS‑8 | M‑2: total exacto como contractual y nota de redondeo de presentación (§9.5) | si se prefiere el total como suma de filas redondeadas, hay que enmendar RF‑08 y NORMAS principio 3 con expediente |
| RS‑9 | Editar un APU en la hoja edita la copia de la versión (DA‑SF‑7) | editar el catálogo rompería versiones y otros proyectos |

---

## 15. Riesgos

| Riesgo | Mitigación |
|---|---|
| `st.data_editor` no aguanta la hoja | prueba de §11.3 con criterio fijo y paso a AG Grid |
| Siete cambios en `core/` | expediente por cambio, TDD con rojo observado, ramas de núcleo separadas, guardia en la CI, tutor |
| SF‑E6 (instantánea de composiciones) es el cambio más profundo | va en SF3 con sus propias pruebas de recarga; sin él, la hoja no edita APU y se declara |
| Los DXF reales no siguen la convención | informe de importación; la hoja manual es la entrada completa |
| Fuentes normativas no verificables | supuestos declarados (RS‑5), visibles y marcados por R8 y R10 |
| Los instrumentos de Med cambian | `exportar_excel` intacto, huella RNF‑04 como regresión, actualización única de pasos al final (§2) |
| El sprint alarga el cierre | orden de caída de §13 |

---

## 16. Revisión del spec

| Ronda | Encargos | Veredicto | Qué cambió |
|---|---|---|---|
| 1 (2026‑10‑04) | requisitos, arquitectura, pruebas y calidad, verificador de hechos | los cuatro, «aprueba con cambios»; 11 bloqueantes | numeración desde RF‑44; RF con prioridad, fase y criterio; UC con flujos alternos; instantánea de composiciones (SF‑E6) y de espacio por versión; restauración como versión nueva; R8–R10 con la instantánea del espacio y hallazgos conservados al recargar (SF‑E1 ampliado); M‑3 sin pasar textos a `parametros`; Excel sin redondear con evaluador de fórmulas y `exportar_excel` intacto; ramas de núcleo separadas por la guardia; protección de los instrumentos de Med; cotización por proyecto (SF‑E7); oráculos con memorias de cálculo; conteo de codos y tees definido; pendiente del drenaje y circuito como cadena; matriz de pruebas; metas de `meta_sf.py` |
| 2 (2026‑10‑04) | los mismos cuatro | los cuatro, «aprueba con cambios», sin bloqueantes | versiones sin instantánea (15e); cotización que prevalece sobre la lista global y listas de proyecto fuera de `lista_vigente`; `version_origen` en toda versión y espacio heredado por la cadena; todo camino del núcleo usa la instantánea de composiciones; versión vigente definida; «imprevistos» retirado (no existe en `ParametrosCosto`); clave de segmento y sobrescrituras huérfanas; codos en tramos compartidos y en tees; reauditoría de R8–R10 que reemplaza, no suma; RNF‑13 con personas distintas y ningún ítem < 3; límite de 20 MB; RNF‑11 con veredicto en el equipo de desarrollo; `SUM`/`ROUND` en inglés; segunda huella de RNF‑04; generador y cálculo sustituto en SF0; S4 con `HEAD` y también en SF5; cobertura de `adapters/espacio` en la CI; conteos de la ERS; dos correcciones de redacción del verificador |
| Enmienda SF2 (2026‑10‑05) | los cuatro encargos de SF2 | aprueban SF2 sin bloqueantes | §11.2: las constantes supuestas dan ADVERTENCIAS de R8; R10 solo marca incumplimientos y baja a ADVERTENCIA mientras su límite sea supuesto (RS‑11); R10 evalúa solo tramos de drenaje que declaran pendiente |
