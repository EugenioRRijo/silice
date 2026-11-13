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
