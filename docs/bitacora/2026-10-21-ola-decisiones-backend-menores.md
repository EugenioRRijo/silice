# Ola de decisiones (backend): los MENOR del arbitro y dos pendientes

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · Sin push. `core/` no se toco. No se toco `frontend-desktop/` ni `ui/`.
Entorno: venv comun, `SILICE_DATOS` temporal, `PYTHON_KEYRING_BACKEND` nulo. Un commit por tarea (prueba e implementacion juntas; el rojo se vio
antes de implementar, ver la columna).

| Tarea | Commit | Rojo visto |
|---|---|---|
| A. MENOR-1 y B. MENOR-2 (planos) | `9bbcd762` | A: `AssertionError` de `getvalue()` (el tope cargaba los bytes). B: la junction real llegaba a `_borrar` |
| C. MENOR-3 (claves del Excel) | `d7156ea9` | 2 pruebas: el diccionario perdia un valor |
| D. MENOR-4 y E. MENOR-5 (lector del BCV) | `db1f4ce1` | 7 pruebas rojas (5 en `test_bcv_libro_xls.py`, 2 en `test_bcv_libro.py`) |
| G. V-16 en docstring, plan y ERS | `c717a1dd` | solo documentacion (ninguna prueba de API fijaba el sentido: `grep favor` en `tests/` sin coincidencias en libros) |
| H. `entregable` en el resumen | `334935c5` | 3 pruebas con `KeyError: 'entregable'` |

## A. MENOR-1: el tope de bytes del plano se mide sin cargar el archivo
`aplicacion.hoja_plano._tamano_de(subida)` usa `subida.tamano()` si existe y, si no, `len(getvalue())` (la subida de Streamlit y las pruebas siguen
igual). `_Subida` de `api/rutas/hoja_plano.py` implementa `tamano()` con `seek(0, 2)` / `tell()` y vuelve a 0. El orden de errores no cambia
(`rev`, formato, tamano) y el 413 conserva su texto fijo. Despues de aceptado, `guardar_subida` sigue leyendo los bytes (<= 8 o 20 MiB).
**Deuda declarada:** el 413 por `Content-Length` ANTES de que Starlette parsee el multipart (hoy el cuerpo ya se acoto a 20 MiB en `api/proteccion.py`;
el DXF de entre 8 y 20 MiB llega entero a un archivo temporal antes de rechazarse). No se hizo: toca el middleware compartido.

## B. MENOR-2: `barrer_huerfanas` no sigue enlaces ni junctions
Medido en este equipo (Python 3.13.2): `os.symlink` falla sin privilegios (`WinError 1314`), pero `mklink /J` crea una junction real; en ella
`is_symlink()` es `False`, `is_junction()` es `True` y `is_dir()` es `True`. La prueba usa la junction **real** (y un enlace simbolico real fuera de
Windows) y una segunda prueba **simula** `is_symlink` con `monkeypatch` (el simbolico no se puede crear aqui). El guardian era solo `is_symlink()`: la
junction pasaba y `_borrar` la intentaba (`shutil.rmtree` de 3.13 se niega en silencio, y por eso la victima sobrevivia por casualidad). La prueba
espia `_borrar` y exige que ni se intente. Ahora `_es_enlace()` = `is_symlink() or is_junction()` (`requires-python >= 3.12`).

## C. MENOR-3: claves que se sanean al mismo texto
`{"a\x00": 1, "a\x01": 2}` daba `{"a�": 2}` y perdia el 1. Ahora `_sin_choques`: la clave que ya estaba limpia conserva su nombre; las que
chocan toman el sufijo ` (n)` (n desde 2, la menor libre, en el orden de entrada), de modo que ningun valor se pierde. Solo se sufija una clave
de texto (una clave que no es texto no cambia al sanearse). Oraculo a mano: `{"a\x00":1,"a\x01":2,"a�":3,"b":4}` ->
`{"a� (2)":1,"a� (3)":2,"a�":3,"b":4}`; y el sufijo no choca con una clave limpia que ya se llame `a� (2)`.

## D. MENOR-4 y E. MENOR-5: lector del BCV (`adapters/bcv/libro.py`)
- **D:** el aviso era `hojas ajenas no leidas: N`; ahora `hojas ajenas no leidas: N (a, b, ... y K mas)` con hasta `MAX_NOMBRES_AJENOS = 10`
  nombres, cada uno sin caracteres no imprimibles y acotado a 40 caracteres (`...`): el nombre viene del libro y no es de fiar. Viaja en
  `Libro.avisos` -> `InformeImportacion.advertencias` y `texto()` (probado con `leer_tasa`). Quien lo pinte debe escaparlo como cualquier texto.
- **E:** `MAX_CELDAS_TOTAL = 20_000_000` celdas entre todas las hojas. En `.xls` se suman las **declaradas** (`nrows * ncols`) antes de leer cada
  hoja (la que no cabe ni se recorre); en `.xlsx` se cuentan las **vistas** fila a fila y se corta al pasarse. Error: `FormatoNoReconocido`
  `<archivo>: supera el maximo de 20000000 celdas leidas entre todas las hojas`. Pruebas con el tope reducido por `monkeypatch`, incluido el caso
  justo en el tope (se lee).

## F. MENOR-6: el conteo real del rojo de D-5
La bitacora de la ola decia «3 de la API fallaban». Reproducido ahora extrayendo `e37a3295` (el commit de las pruebas, con el codigo anterior) y
corriendo sus tres archivos con `-W error`: fallan **11**, no 3:
- 3 de `test_api_hoja_guardado.py` (vieja descartada, vieja no descartada, carrera de dos personas con la vieja);
- 1 de `test_aplicacion_hoja_borradores.py` (`vigente_al_abrir` no existia);
- 7 de `test_aplicacion_hoja_vista.py` (6 casos de la tabla de `version_mas_nueva` mas «en blanco nunca avisa»; falta la funcion).
Las otras nuevas de la API (si alguien guarda despues, retomado, reinicio) pasan a proposito: fijan lo que NO debe cambiar. «3 de la API» era cierto
solo para la API.

## G. V-16 (libro menor = favorable) en el contrato escrito
`IndicadorRespuesta` ya no dice «cualquier desviacion es desfavorable». Para `sentido = "exactitud"` (libro contra Silice): `delta = actual - meta`;
**negativo = libro menor = favorable (verde); positivo = libro mayor = desfavorable (rojo); cero = neutro.** El front lo hizo en `0cf6e462`
(`semanticaIbcs`: el signo decide el color como en un costo); la API solo manda el signo y no cambia. Ninguna prueba de API fijaba el sentido anterior
(solo `sentido == "exactitud"`). Anotado «superado por la decision V-16 de Eugenio 2026-10-21 (libro menor = favorable)» en `docs/ERS.md` RF-116 y en
`docs/planes/PLAN_SESION_2_VISUAL.md` (RS2-13 en la tabla, la nota de la linea 106 y la de la linea 408), conservando el texto anterior por
trazabilidad. **Riesgo declarado:** un libro que omite costos puede salir en verde (es justo el motivo por el que RS2-13 lo habia hecho desfavorable);
la compensacion es que la palabra «favorable/desfavorable» siempre se ve y que los hallazgos de la auditoria siguen apareciendo aparte.
(`docs/ERS.md` es un archivo compartido del manual; se edito porque el encargo lo pidio expresamente y es una sola celda.)

## H. Aviso de entregar: contrato nuevo para el agente FRONT
`GET /v1/entregas/resumen?proyecto=&version=` -> `ResumenRespuesta` gana **`entregable: boolean`** (obligatorio, siempre presente):
- `true`: la version se puede entregar (caso normal).
- `false`: la version se sello **antes de la correccion de cifras de VB-1** (formato legado). La cadena sigue integra (`cadena_integra: true`),
  pero `POST /v1/entregas` la rechaza con **409** `{"detalle": "<aviso>"}`. El aviso ya viaja **al final de `mensaje_de_cadena`**
  (`"<mensaje de cadena>. La versión 001 se selló antes de la corrección de cifras y no puede entregarse tal cual; confirme una versión nueva (quedará
  sellada con la cifra corregida) y entregue esa."`).
Lo que debe hacer la pantalla: mostrar `mensaje_de_cadena` (ya lo hace), y con `entregable === false` deshabilitar «Entregar» (y no pedir la
contrasena de firma) dejando visible el aviso y la salida (confirmar una version nueva). Si `cadena_integra` es `false`, el mensaje es el de cadena rota
y `entregable` es `true` (el 409 de la cadena rota ya cubre ese caso). `docs/api.json` regenerado (`app.openapi() == docs/api.json`). Pruebas
(`tests/unit/test_api_entregas.py`): version actual (`MIN-001`) y fraccionaria sellada ahora -> `entregable: true`; fraccionaria sellada con
`canonico.formato_legado()` (`tests/fixtures/vb1_fraccionario.py`) -> `entregable: false`, el aviso al final del mensaje, 409 al entregar con ese mismo
texto y ningun evento «paquete exportado».

## Verificacion
`pytest -W error`, sin `-n` (no hay xdist), en dos tandas: (1) entregas, libros (replica e integracion), acceso por ruta, `test_arquitectura*`, `test_front_rutas_api`, `tests/unit/adapters`, `test_bcv_libro_xls`, `test_ui_indices`, `test_vb1_*`: 793 verdes, 0 fallos (`test_ui_indices` pasa: ya no hay el limite de 50 hojas); (2) `test_api_hoja*` y `test_aplicacion_hoja*`: 1188 verdes, 0 fallos. Cero omitidas. `ruff check` limpio en lo tocado; `ruff format --check` limpio en lo tocado (queda
`aplicacion/hoja.py:2335` sin formatear, preexistente y ajeno).
