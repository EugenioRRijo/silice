# Hoja 3b-3: avance del backend (R9 a R14) y medición

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `146dc59`
El contrato exacto de las rutas está en `2026-10-19-hoja-3b3-contrato-rutas.md`.

## Parejas prueba → implementación (rojo visto primero)

| Pareja | Prueba en rojo | Implementación |
|---|---|---|
| R9 punto de equilibrio | `test(hoja): vista del punto de equilibrio R9 en rojo` | `feat(api): vista del punto de equilibrio R9` |
| R10 parámetros | `test(hoja): vista de los parametros R10 en rojo` | `feat(api): vista de los parametros R10` |
| R11 auditoría con R17 y R14 trazabilidad | `test(hoja): auditoria R11 con R17 y trazabilidad R14 en rojo` | `feat(api): auditoria R11 con R17 y trazabilidad R14` |
| R12 precios | `test(hoja): precios con su origen R12 en rojo` | `feat(api): precios con su origen R12` |
| R13 atípicos | `test(hoja): variaciones atipicas R13 en rojo` | `feat(api): variaciones atipicas R13 y esquema compartido` |
| Acceso, no-store, float, caso, paridad con `ui.hoja` y medición ampliados a R9-R14 | `test(hoja): acceso, no-store, float, caso, paridad ... ampliados a R9-R14` (pasan a la primera: R9-R14 ya existían, no hay código nuevo) | — |

Los SHAs están en `git log 146dc59..HEAD`.

## Ajustes de prueba hechos tras ver el resultado (declarados)

- R14, prueba de la clave de API: tomaba el volcado de la base antes de que la primera lectura adoptara el caso (crea el
  esquema) y por eso el «antes» y el «después» diferían. Ahora hace una lectura antes. Ningún valor esperado cambió.
  Lo mismo se escribió ya bien en R12 y R13.
- `test_aplicacion_hoja_conexion.py::test_las_vistas_leen_siempre_el_calculo_que_agrega_r17` falló al añadir
  `vista_precios` y `vista_trazabilidad` (no reciben un borrador: leen la base). Se afinó la guardia: aplica a las
  `vista_*(vivo, ...)` y a `informe_de_auditoria`, exige las siete del borrador (incluida la auditoría, segunda cláusula
  de 3b-B21) y sigue prohibiendo que cualquier otra función llame a `elaborar_borrador`/`elaborar_hoja`.
- `ruff format` reacomodó líneas de las pruebas de R9 (solo formato).

## Medición registrada (3b-B22 y 3b-B23; no afirma ningún tiempo)

Las siete vistas del borrador (R5 a R11) sobre los 500 puntos del generador determinista, mediana de cinco corridas con
una de calentamiento (`tests/unit/test_hoja_vistas_medicion.py`), cada corrida elaborando de nuevo (caché invalidada, R17
incluida): **0,157 y 0,235 s** en este equipo (dos corridas del procedimiento; la variación es de la carga de la máquina).
Umbral de referencia de RNF-11: 2 s. Tamaño estimado del borrador de 500 puntos: **236 737 bytes**. No incluye `abrir` por
la API ni R12 a R14 (leen la base; sin medición propia en esta sub-rebanada).

## Diferencias y límites declarados

- Los textos que componen las vistas llevan tildes (rótulos de los parámetros, «Esta versión no nació de una edición…»);
  los que salen de `aplicacion/hoja.py` van idénticos a la clásica (sin tildes). La prueba de B20 compara el vacío de R14
  con `normalizar_texto` contra el literal de la clásica.
- R9 añade `moneda` a `VistaEquilibrio` (el diseño no la listaba; la clásica da las cifras con moneda). `periodo` va tal cual
  lo entrega `core` (puede traer códigos entre corchetes); la frase `mensaje` los quita.
- R10: `moneda_proyecto` y `puede_convertir` solo existen con versión abierta (como P:2073); `puede_convertir` es el permiso
  `CONVERTIR_Y_REAJUSTAR` de la sesión.
- R12: la erosión «por índice» siempre es `null` (la clásica no pasa serie de índice a `precios_de_version`, H:2368); la
  columna existe y el front la muestra solo si algún valor viene. `erosion_pct` viaja ya multiplicado por 100. La tasa va con
  su `exacto` (puede tener más de dos decimales).
- R12 a R14 no usan borrador: no hay «404 por ficha ajena» ni «409 por cambio de caso» que probar; lo que se prueba es que
  leen el caso de la ficha (TI-001 / OF-001 cruzados) y que la clave de API puede leer y no escribe nada.
- R13: los insumos buscados son los de `precios_de_version` (los de las composiciones de la versión), como el botón de la
  clásica. El esquema `AtipicosRespuesta` salió de `api/rutas/precios_empresa.py` a `api/esquemas_atipicos.py` (el diseño decía
  `api/esquemas_hoja.py`; un módulo propio evita que las dos rutas dependan una de otra y el nombre en OpenAPI no cambia).
- `_hoy()` en `api/rutas/hoja.py` es el día de evaluación de R12; las pruebas lo fijan.
- Deuda de 3b-2 que sigue: `vista_plan` repite la fórmula del porcentaje de `hoja.filas_de_curva`.
