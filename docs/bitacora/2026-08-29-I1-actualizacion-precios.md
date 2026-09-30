# Bitácora — Sesión I1 (UC‑02: actualización masiva de precios y UI mínima)

**Fecha:** 2026‑08‑29 · **Rama:** `inc/I1-actualizacion-precios` (nace de `main`, `da3d951`)
**Meta del sprint alpha:** M7 (UC‑02 actualiza precios con registro de cambios) — **OK**

## Objetivo

Cerrar el primer caso de uso de valor percibido: el usuario carga una lista de precios nueva
(CSV o XLSX), el sistema identifica los insumos afectados, **revalora** el presupuesto guardado sin
editar ninguna composición, registra qué cambió y con qué incidencia por partida, emite el informe
comparativo y audita la versión nueva (el informe se genera siempre, principio 7 de NORMAS.md §2).
Interfaz mínima en Streamlit para hacerlo sin escribir código.

## Qué se hizo

| Archivo | Contenido |
|---|---|
| `core/catalog/precios.py` | `PrecioLeido`, `ResumenLista`, `CambioDetectado`; `leer_lista_precios(ruta)` (CSV/XLSX con pandas `dtype=str`), `crear_lista_desde_archivo(session, ruta, nombre, moneda, fecha_vigencia, origen="")`, `insumos_afectados(session, lista_anterior, lista_nueva)` y `registrar_cambios(session, lista_anterior, lista_nueva)` |
| `core/budget/actualizacion.py` | `COLUMNAS_COMPARATIVO`, `Comparativo` (DataFrame de `Decimal` + totales, con `variacion` y `variacion_pct`) y `actualizar_precios(session, proyecto_nombre, codigo_presupuesto, lista_nueva, codigo_nuevo, plan=None) -> tuple[ResultadoElaboracion, Comparativo]`, que además persiste `CambioPrecio` e `IncidenciaCambio` |
| `core/catalog/__init__.py`, `core/budget/__init__.py` | Solo las líneas de reexport de lo anterior |
| `ui/app.py` | Streamlit: selector de base (`data/apu.db`), botón de siembra, carga del archivo, tabla del comparativo, avisos de insumos desconocidos, informe de auditoría en markdown y descarga del libro de Excel. Solo llama a `core` (y `scripts.seed` para el arranque) |
| `data/samples/precios/lista_2026-06-01.csv` (+ `README.md`) | Nueve insumos de la línea base; solo suben cemento Portland 15 → 18 USD/saco y arena lavada 30 → 33 USD/m3 |
| `tests/integration/test_actualizacion_precios.py` | 11 pruebas de integración sobre la SQLite en memoria sembrada |

Números del caso, exactos y sin tolerancia: el presupuesto pasa de **1 586,613188875** a
**1 636,695803875 USD**; el único renglón que se mueve es `LB-04-CON`, cuyo precio unitario sube de
242,63965 a 272,80990 USD/m3 (+30,17025 = 23,85 × 1,15 × 1,10, es decir el material adicional
atravesando administración y utilidad en cascada) y cuyo total sube 50,082615 USD (1,66 m3). Los
otros cuatro renglones quedan idénticos, con `variacion_pct` e `incidencia_pct` en cero.

Resultado: **293 pruebas verdes, 0 omitidas, sin advertencias**; `ruff check` y `ruff format`
limpios; `scripts/meta_alpha.py` **12/12** (M7 pasa a OK, M9 sigue OK, cobertura de `core/` 97,8 %).

Commit: `feat(core): actualizacion masiva de precios con registro de cambios`.

## Decisiones

| Decisión | Motivo |
|---|---|
| `crear_lista_desde_archivo` devuelve `ResumenLista` (con `lista` y `desconocidos`) en vez de `models.ListaPrecios` a secas | Desviación deliberada del tipo de retorno literal del brief, indicada por el controlador: los insumos desconocidos hay que **reportarlos** (UC‑02, flujo 2a) y perder ese dato en el retorno obligaría a recalcularlo. Sigue el patrón ya existente de `ResumenCarga` en `core/catalog/repositorio.py` |
| Los insumos que el catálogo no conoce **no se crean** | Dar de alta un insumo es una decisión del administrador, no un efecto secundario de leer un archivo. Los desconocidos no intervienen en el recálculo |
| La lista nueva **copia todos** los precios de la vigente y sobrescribe los del archivo | Así vale por sí sola para reconstruir cualquier APU; una lista parcial haría fallar `Catalogo.composicion` con `CatalogoIncompleto` en la primera partida con un insumo sin precio. La lista anterior no se toca: es inmutable desde que un presupuesto la referencia |
| Emparejamiento por (tipo, descripción **normalizada**, unidad **normalizada**), no por código | El archivo lo escribe un proveedor que no conoce los códigos internos. La descripción pasa por `core.verification.texto.normalizar_texto` (única normalización de texto del sistema) y la unidad por `normalizar_unidad` (única tabla de alias): DRY, y `TUBERIA PVC 4"` casa con `Tubería PVC 4 pulg` |
| Una fila del archivo actualiza **todas las variantes** homónimas de esa descripción y unidad | Hallazgo 2. Es la única lectura posible con las cuatro columnas que define el brief |
| `Decimal` construido desde el **texto** del archivo (`dtype=str`, `keep_default_na=False`) | Si pandas leyera los precios como números, el importe ya habría pasado por `float` (NORMAS.md §2.3). Punto como separador decimal; los errores citan archivo y número de fila (UC‑02, flujo 2a) |
| `actualizar_precios` conserva la firma del brief y añade `plan: Sequence[PeriodoPlan] \| None = None` | Sin plan el presupuesto nuevo no lleva curva y R2 lo hace constar como INFO, que es el comportamiento ya definido en `elaborar`; con plan, la curva del presupuesto nuevo cierra en su total |
| El presupuesto nuevo se fecha en `lista_nueva.fecha_vigencia` y hereda moneda y los cuatro parámetros de costo del anterior | Es la fecha en que esos precios pasan a valer. Lo único que se mueve son los precios: las cantidades, los ítems y la estructura de costos son los mismos, que es lo que hace comparables las dos versiones |
| `IncidenciaCambio` guarda el precio unitario de la partida **con la lista anterior** y **con la nueva** | Es la definición literal de las dos columnas en `docs/modelo_datos.md` §2.2. Ver hallazgo 4 |
| `incidencia_pct` del comparativo = aporte de la partida a la variación del **total** (base: total anterior) | Suma exactamente la variación porcentual del presupuesto, porque el precio unitario es una función afín de los precios de los insumos. La prueba lo comprueba con `Decimal` exacto. `variacion_pct` es lo otro: la variación del precio unitario de esa partida |
| `Comparativo` es `frozen` pero con `eq=False` | El `==` de un `DataFrame` devuelve otro `DataFrame`, no un booleano: una igualdad generada por `dataclass` sería una trampa. La igualdad no significa nada aquí |
| `registrar_cambios` es idempotente para un par de listas | `CambioPrecio` no tiene restricción de unicidad; sin la guarda, revalorar dos veces con la misma lista duplicaría el historial que después alimenta al módulo predictivo |
| Ni `crear_lista_desde_archivo` ni `actualizar_precios` confirman la transacción | Misma regla que `guardar_presupuesto`: la transacción es del llamador, que es quien acepta o descarta la versión nueva (UC‑02, flujos 3a y 7a). La UI es la que hace `commit` |
| `actualizacion.py` importa `_buscar` y `_parametros_de` de su módulo hermano `persistencia.py` | Son ayudantes del mismo paquete y la lectura de los `ParametrosCosto` desde las columnas del presupuesto es una definición única (hallazgo 1). Duplicarla habría sido lo contrario del principio DRY |
| `ui/app.py` se ejecuta bajo `if __name__ == "__main__"` | `streamlit run` ejecuta el script como `__main__`, de modo que la guarda no estorba y a cambio el módulo se puede **importar** sin abrir bases ni pintar pantallas: así se comprobó que compila e importa, y así se probaron sus dos ayudantes de presentación |
| La UI redondea a dos decimales con `formatear_decimal(..., DECIMALES_PRESENTACION)` | Único lugar donde se redondea es la presentación, y el número de decimales se importa de su fuente en vez de repetirse |

## Hallazgos

1. **Insuficiencia del contrato (confirmada; ya registrada en I0.5).** `core.contracts.Presupuesto`
   no lleva los `ParametrosCosto` con que se valoró, y revalorar exige conocerlos. Se rodea sin
   tocar `core/contracts/`: se leen de las columnas `fcas`, `bono_alimentacion`, `administracion` y
   `utilidad` de `models.Presupuesto` reutilizando `core.budget.persistencia._parametros_de`. Se
   mantiene la propuesta de añadir `parametros: ParametrosCosto` al contrato en la revisión
   posterior a la Fase 1: es la tercera sesión que lo rodea.
2. **Hallazgo de datos (ampliación del de `docs/modelo_datos.md` §6).** La línea base tiene cuatro
   insumos homónimos con precio distinto cargados como variantes (`Agua`, `Pala`, `Cinta métrica`,
   `Nivel de mano`, con código sufijo `-B`). Como el archivo de precios identifica al insumo por
   (tipo, descripción, unidad), **una fila actualiza todas sus variantes**: hoy no hay forma de
   subir el precio del agua del vaciado de concreto sin subir también el del relleno. Distinguirlas
   exigiría una columna `codigo` en el archivo —que el brief no define— o consolidar las variantes
   en un solo insumo con precios por partida, que es un cambio de modelo de datos. Queda anotado
   para UC‑02 ampliado; la muestra del repositorio evita a propósito los cuatro homónimos.
3. **Flujo 2b de UC‑02 (unidad no equivalente) queda subsumido en «desconocido».** Una fila cuya
   unidad no equivale a la del catálogo no encuentra insumo y se reporta en
   `ResumenLista.desconocidos`, sin distinguirse de un insumo inexistente. Distinguirlas exigiría un
   segundo campo en `ResumenLista`; se prefirió no ampliar el tipo que fijó el controlador. El
   usuario ve la fila reportada, que es lo que la ERS exige; lo que no ve es *por qué*.
4. **`IncidenciaCambio` no puede atribuir el efecto de cada insumo por separado.** Sus columnas son,
   por definición del modelo, el precio unitario de la partida con la lista anterior y con la nueva.
   Cuando dos insumos suben en la misma partida —el caso de la muestra: cemento y arena en
   `LB-04-CON`— las dos filas registran el mismo par de precios unitarios, y sumarlas sobrestimaría
   el efecto. El reparto individual **sí** sería calculable (el precio unitario es afín en los
   precios de los insumos), pero no tiene columna donde vivir. El dato que el usuario necesita —qué
   partida subió y cuánto aportó al total— está en el comparativo.
5. **El separador decimal aceptado es el punto.** Aceptar también la coma obliga a decidir qué
   significa el separador de miles en un archivo que escribe un tercero, y ninguna fuente del
   proyecto lo necesita todavía. Está documentado en el docstring de `leer_lista_precios` y en
   `data/samples/precios/README.md`.
6. **`Catalogo` no tiene consulta de presupuestos de un proyecto.** La UI pide el nombre del
   proyecto y el código del presupuesto en campos de texto, con la línea base como valor por
   defecto, porque no existe `Catalogo.presupuestos(proyecto)`. Es una consulta de lectura que la
   Sesión F.1 necesitará para el selector; no se añadió aquí para no ampliar un archivo compartido
   más allá de las líneas de reexport.
7. **Coherencia del histórico.** `CambioPrecio` se registra entre la lista del presupuesto
   **anterior** y la nueva, no entre la vigente y la nueva: son la misma lista en el caso normal,
   pero divergen si se revalora un presupuesto viejo. El histórico refleja entonces el salto que
   realmente se aplicó, que es lo que después explicará el módulo predictivo.

## Impedimentos

Ninguno. `uv sync --extra ui` no modificó `uv.lock` (ya resolvía todos los extras), de modo que no
hubo que descartar cambios en archivos compartidos: la sesión solo tocó sus rutas exclusivas más las
líneas de reexport de los dos `__init__.py`.

## Ronda de corrección 1

Revisión sobre `b83171e`: «Necesita correcciones», 3 hallazgos Important. Los tres se corrigen sin
tocar archivos compartidos ni `core/contracts/`.

1. **XLSX por `float` (hallazgo 1).** `_leer_tabla` usaba `pandas.read_excel(dtype=str)`, pero ese
   `dtype` se aplica **después** de que `openpyxl` ya analizó la celda numérica como `float` de
   Python; el docstring afirmaba lo contrario y no había ninguna prueba con un archivo XLSX real.
   Se reemplazó por `_leer_tabla_excel`: lee el libro celda por celda con `openpyxl` y convierte
   cada valor a texto en Python puro (sin el arreglo `numpy` intermedio que usa `pandas` para
   castear una columna completa), antes de construir el `DataFrame`. Se corrigió el docstring del
   módulo y el de `_leer_tabla` para no prometer una garantía que la ruta anterior no cumplía por
   construcción. Prueba nueva: `test_leer_lista_precios_xlsx_lee_decimales_exactos` (crea un XLSX
   en `tmp_path` con `openpyxl`, precios 18,10 y 0,10). **Nota honesta:** en las versiones
   instaladas (`pandas` 3.0.5, `numpy` 2.5.2, `openpyxl` 3.1.5) la ruta anterior YA daba estos dos
   valores exactos por una garantía incidental de `str(float)` (round‑trip más corto de CPython),
   verificado con un barrido de 3000 precios aleatorios de 2 a 6 decimales sin un solo fallo; la
   prueba nueva no queda en rojo contra el código viejo con estos valores. La corrección se hizo
   de todos modos porque el mecanismo interno seguía pasando por `float` (contra la letra de la
   restricción global 3) y dependía de un comportamiento de `numpy`/`pandas` no garantizado entre
   versiones, sin ninguna prueba que lo fijara. Detalle completo en el reporte de la tarea.
2. **Confirmación por `variacion` en vez de `insumos_afectados` (hallazgo 2).** `ui/app.py`
   decidía confirmar la transacción con `comparativo.variacion == 0`: si la lista nueva sube un
   insumo que no participa de ninguna partida del presupuesto, la variación del total es cero y la
   UI descartaba la lista y sus `CambioPrecio`, aunque el cambio de precio fuera real. Se añadió
   `Comparativo.insumos_afectados: int` (cuenta de `CambioPrecio` que ya persiste
   `actualizar_precios`, se construye con el mismo `cambios` que ya calculaba la función, sin
   consultas nuevas) y la UI ahora confirma con ese campo: sin insumos afectados no confirma (UC‑02
   flujo 3a); con insumos afectados confirma siempre, y si además el total no varió lo avisa con un
   mensaje informativo en vez de descartar el historial. Verificado manualmente con un presupuesto
   que excluye la partida `LB-04-CON` (la única que usa cemento y arena) revalorado con la muestra
   del repositorio: `insumos_afectados == 2` y `variacion == 0` a la vez, que es exactamente el
   caso que la corrección distingue.
3. **Variantes homónimas sin prueba (hallazgo 3).** La política (una fila del archivo actualiza
   todas las variantes con la misma `(tipo, descripción, unidad)`) ya estaba implementada
   correctamente; solo faltaba la prueba. Se añadió
   `test_crear_lista_actualiza_todas_las_variantes_homonimas`, que usa el homónimo real del
   catálogo sembrado (`Cinta métrica`, códigos `EQU-007` y `EQU-007-B`) y afirma que ambas
   variantes reciben el precio nuevo. Se verificó que la prueba detecta una regresión real: se
   rompió temporalmente el bucle de `crear_lista_desde_archivo` para actualizar solo la primera
   variante, la prueba falló, y se restauró el código correcto.

Resultado: 295 pruebas verdes (13 en `test_actualizacion_precios.py`, dos nuevas más una aserción
añadida a una existente), `ruff check` y `ruff format` limpios, cero advertencias.
Commit: `fix(core): decimal exacto en xlsx, commit por insumos afectados y prueba de variantes`.
