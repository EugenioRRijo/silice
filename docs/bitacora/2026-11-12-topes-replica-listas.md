# Topes del lector en la réplica sin fórmulas y en las listas y presupuestos subidos (2026-11-12)

Rama `feature/topes-replica-listas`, sobre `feature/lector-topes` (e998291c). Cierra las NOTAS 6 y 7 del
[acta del árbitro de los topes](arbitrajes/lector-topes-claude-xhigh.md) (ESTADO §4.10 a y b).
**Decisión provisional del orquestador, reversible; Eugenio la ratifica.** `core/` sin cambios.

## Qué

- **(a) Réplica del visor, hoja sin fórmulas.** `visual._hoja` pasa cada hoja de la apertura normal por
  `lector.comprobar_topes_de_hoja`: sus celdas (las cubiertas por una combinada también) y sus filas con alto o
  formato propio, en un solo recorrido. Mismos topes (20.000 filas, 100 columnas) y mismo aviso que
  `filas_acotadas`, el de la primera fila que se pasa; los dos avisos viven una sola vez en el lector.
- **(b) Listas, presupuestos y valuaciones subidos.** `lector.comprobar_topes_del_libro(datos, nombre)` recorre
  cada hoja en solo lectura con `filas_acotadas` (una sola cuenta de `MAX_CELDAS_LIBRO` para el libro) antes de
  que el núcleo (`core.catalog.precios.leer_tabla`, que recorre sin tope) abra el libro. Lo llaman:
  `api/rutas/listas.py` `comprobar_libro_legible` (carga y vista previa de listas, listas de la empresa,
  importación y revaloración de presupuestos), `api/rutas/revision.py` (Excel externo) y `api/rutas/control.py`
  (importación de valuaciones). Mismo estilo de respuesta que cada ruta (422; la vista previa, `motivo`).

## Por qué

Sin `<dimension>`, una celda en A1048576 hacía recorrer al núcleo un millón de filas (0,94 s) y 2.000 filas
escritas en XFD, 16.384 valores por fila (5,3 s; crece con las filas). Ahora se rechazan en 0,02 s y 0,08 s
(medido en este equipo con libros construidos); la réplica, en 0,02 s y 0,25 s.

## Decisiones (para ratificar)

1. En la réplica cuentan las celdas cubiertas por una combinada y las filas con alto propio: el visor las
   dibuja. Un libro con una combinada que pasa de la columna CV o de la fila 20.000 se rechaza en la réplica
   aunque el lector (solo lectura) no vea esas celdas si Excel no las escribió.
2. La importación de valuaciones no pasaba por la guardia (F-D10): ahora pasa. Su aviso de libro roto deja de
   ser «El archivo no es un libro .xlsx legible; no se importó nada.» y es el de la guardia más «No se importó
   nada.»; un `.xlsm` de valuaciones, que antes se aceptaba, se rechaza como en el resto de las subidas.
3. `comprobar_libro_legible` ya no abre el libro por su cuenta: el aviso de un libro que openpyxl no abre es el
   del lector (sin el nombre del tipo de excepción).
4. Se recorren todas las hojas, no solo las que lee el núcleo: una hoja ajena al formato que pase de los topes
   también rechaza el libro, igual que en el lector del libro conocido.

## Pruebas

TDD con rojo visto: `tests/unit/test_visual_libro.py` (diez casos hostiles y la frontera CV20000),
`tests/unit/test_api_libros_replica.py` (HTTP), `tests/integration/test_api_topes_subidas.py` (fronteras de
`comprobar_libro_legible` con dimensión falsa y sin dimensión, la cuenta del libro entre hojas, carga y vista
previa de listas, presupuesto de un tercero), `tests/unit/test_api_revision.py` y `tests/unit/test_api_control.py`.
`con_celdas` gana `sin_dimension`. Casos construidos con openpyxl; ningún libro real.

Dos pruebas del primer rojo fallaban por otra causa (`Response.ok` y una base que ya traía valuaciones); se
corrigieron y se volvió a ver su rojo contra el código sin corregir (el núcleo recorría la hoja hostil entera y
respondía con su propio aviso). Suite completa: 12.325 pruebas en verde, ninguna omitida; ruff limpio;
`guardia_nucleo.py --base origin/main` OK; `docs/api.json` sin cambios.

## Índices del BCV subidos (rama `fix/indices-topes`, 2026-11-12)

Hallazgo MENOR de un árbitro independiente, verificado: `api/rutas/indices.py` `_leer_archivo` pasaba el
`.xlsx` por la guardia (`verificar_archivo`) y de ahí a `aplicacion.indices.leer` → `adapters.bcv.libro._xlsx`,
que recorre cada hoja necesaria con `hoja.iter_rows(values_only=True)` sin tope de filas
(`adapters/bcv/libro.py:245`). Su `MAX_CELDAS_TOTAL` cuenta `len(valores)`, y las filas vacías que openpyxl
rellena hasta la última escrita llegan como tuplas vacías: no cuentan. Medido aquí: una hoja `30092026` sin
`<dimension>` con A1048576 entrega 1.048.576 filas (0,47 s por hoja; hasta `MAX_HOJAS_LEIDAS` = 100 hojas
así) y la tasa se **importaba** igual (200, y en `confirmar` se guardaban los valores).

**Arreglo:** la ruta llama a `lector.comprobar_topes_del_libro(contenido, nombre)` justo después de
`verificar_archivo`, como las listas y el Excel externo. Mismo estilo de respuesta: 422
«No se importo nada: » más el aviso del lector. El rechazo tarda 0,02 s. El lector del BCV no se toca.

**Frente a los libros reales del BCV.** Los topes miden celdas, no hojas: un trimestre de la tasa (hasta 92
hojas diarias de unas decenas de filas y menos de diez columnas) y la hoja del INPC (`4_5_7`: un año por
fila propia y los meses en filas, unos cientos de filas) quedan muy por debajo de 20.000 filas,
100 columnas y `MAX_CELDAS_LIBRO` (4.000.000). El tope de hojas sigue siendo el del lector del BCV
(`MAX_HOJAS_LEIDAS` 100 leídas, `MAX_HOJAS_DECLARADAS` 256). Además, el BCV publica `.xls`, que va por `xlrd`
con su propio tope (`MAX_CELDAS_XLS`) y no pasa por este cambio. Choque posible: un `.xlsx` convertido a
mano con alguna hoja, aunque sea ajena, de más de 20.000 filas o más de 100 columnas (ver la decisión 4 de
arriba: se recorren todas las hojas).

**Pruebas** (`tests/unit/test_api_indices.py`, TDD con rojo visto en ed4f9b14): la hoja sin dimensión con
A1048576 en `leer` y `confirmar`, de tasa y de INPC (422 con el aviso exacto, como mucho 20.001 filas
entregadas por openpyxl y la base sin valores); CW2 (aviso de columna); la frontera A20000 (pasa con la
misma tasa) y A20001 (no pasa); un trimestre entero, 92 hojas diarias con 21 monedas y una hoja ajena
(pasa: 92 valores de compra y 92 de venta). Rojo: 200 o el aviso del INPC, tras 1.048.576 filas.

**Otras subidas revisadas** (`load_workbook`, `leer_tabla`, `replicar_libro`, `leer_libro` y las rutas con
`UploadFile`):

| Ruta | Lector | Estado |
|---|---|---|
| `api/rutas/libros.py` (auditar, devolución, revisión con PDF, réplica, APU por hoja) | `lector.leer_libro`, `replicar_libro`, `leer_libro_apu_por_hoja` (`fusion/proceso.py:569`, `fusion/apu_por_hoja.py:506`, `api/rutas/libros.py:837`) | acotado por `filas_acotadas` / `comprobar_topes_de_hoja`; la devolución (`escritor/devolucion.py:127`, modo normal) abre bytes que `leer_libro` ya acotó en la misma petición |
| `api/rutas/listas.py:158`, `precios_empresa.py:195`, `presupuestos.py:262` | `comprobar_libro_legible` | acotado |
| `api/rutas/revision.py:585`, `api/rutas/control.py:492` | `comprobar_topes_del_libro` | acotado |
| `api/rutas/indices.py` | `adapters/bcv/libro.py:236` | **acotado desde esta rama** |
| `api/rutas/produccion.py:509` (báscula) | `produccion/conectores/bascula.py:300` | filas acotadas por `islice` (100.031), **columnas no**: queda anotado (abajo) |
| `computos.py`, `vial.py`, `casos.py`, `hoja_plano.py`, `admin_empresas_registradas.py` | CSV, `.db`, DXF/IFC, clave | no abren `.xlsx` |

**Queda anotado (sin arreglar, no es el mismo patrón):**

1. **Báscula, filas anchas.** `_filas_de_xlsx` pide hasta 100.031 filas, pero sin `max_col`. openpyxl arma
   la fila entera hasta la última celda escrita, y `_acotada` quita los vacíos del final antes de comparar con
   `MAX_COLUMNAS` (60). Una celda con formato y sin valor en XFD no rechaza el libro y le hace construir
   16.384 valores por fila. Medido: 2.000 filas así (15 KB) cuestan 8,3 s; con 100.000 filas (unos 600 KB)
   serían varios minutos. `comprobar_topes_del_libro` no sirve tal cual: rechazaría los reportes legítimos de
   20.001 a 100.000 filas. Arreglo propuesto: `iter_rows(max_col=MAX_COLUMNAS + 1, ...)` en el conector.
   Cambia el comportamiento (una columna con datos más allá de la 61 se dejaría de ver y no rechazaría), así
   que se decide aparte.
2. **Topes del lector y número de hojas.** Las filas vacías no suman en la cuenta de `MAX_CELDAS_LIBRO`, y
   la guardia no limita las hojas (solo las piezas del ZIP, 5.000). Medido: 1.000 hojas con A20000 (466 KB)
   cuestan 12 s en `comprobar_topes_del_libro`. Afecta a todos sus llamadores. En índices, 256 hojas en el tope
   suman unos 6,5 s (3,3 s de topes y 3,2 s del lector del BCV); antes eran 78 s. Arreglo posible en el lector:
   contar cada fila entregada como al menos una celda, o poner un tope de hojas en la guardia.

`core/` sin cambios; `docs/api.json` sin cambios (no cambian los esquemas).
