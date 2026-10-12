# Protocolo de medición: tasa de detección en planos (S3 §11.5 y §13.5 b)

Versión 1, escrita en S3-0 **antes** de medir (maestro §7). Su huella SHA-256 está en
[`protocolos_s3.json`](protocolos_s3.json); la meta (`S3-M1`) comprueba que el texto no cambió
después de escribirla. Si algo de aquí debe cambiar, se escribe una versión 2 con su huella nueva
y la 1 queda como historia.

## 1. Qué se mide y la meta

La auditoría de planos de la 0.8.0 (auditoría de archivo del DXF, requisitos IDS del IFC, R15 y
R16) se evalúa **sembrando errores conocidos** en un plano limpio y viendo qué detecta.

* **Tasa de detección** por categoría = errores detectados ÷ errores sembrados **detectables**.
* **Falsa alarma** = todo ítem del informe de importación, hallazgo de R8 a R15 o diferencia de R16
  que la auditoría **agrega** al sembrar el error y que no está ni en la detección esperada ni en
  las consecuencias admitidas de su fila del catálogo. Se cuentan todas, por archivo sembrado.
* **Meta** (ratificada por Eugenio el 2026-10-11, pregunta P8 del maestro §10.3): **100 % de lo
  detectable y cero falsas alarmas** sobre el plano limpio de OF-001 y sobre los archivos sembrados.

## 2. Material

| Pieza | Dónde |
|---|---|
| Catálogo de errores con la detección esperada y los controles no detectables | `tests/fixtures/errores_planos/catalogo.md` |
| Plano limpio de partida | `tests/fixtures/planos/of001.dxf` y, para el IFC, el IFC de oficina `tests/fixtures/planos_ifc_ids.py` (OF-001 no tiene IFC) |
| Conjunto exacto del plano limpio (ítems y hallazgos), escrito como literal | `tests/fixtures/errores_planos/of001_limpio.py` |
| Sembrador | `scripts/sembrar_errores_planos.py` |
| Medición | `scripts/medir_deteccion_planos.py` |

El catálogo lo escribe **en parte quien no programa las reglas**: las filas marcadas `P` las escribe
el ingeniero de pruebas sin ver la implementación de R15 ni de R16 (columna *Autor*); las marcadas
`A`, quien programa los adaptadores. La meta se cuenta con todas.

## 3. Diseño

* **Semilla fija:** semilla 42. La misma semilla, la misma categoría y el mismo índice de variante
  dan siempre el mismo plano y el mismo elemento dañado. Se recorre con
  `uv run python scripts/medir_deteccion_planos.py`.
* **n por categoría:** 3 variantes de cada categoría de DXF que tiene más de un elemento donde
  dañar (la variante cambia el elemento, el factor o el desplazamiento); 1 variante en las que no
  la tienen (`SIN-UNIDAD`, las tres de IFC, `NO-DET-PERMUTA`, `NO-DET-LUCES`). En total 34
  archivos detectables y 5 controles. Con 34 de 34, el límite inferior unilateral al 95 % de la
  tasa verdadera (regla exacta `0,05^(1/34)`) es **91,6 %**: es el máximo que esta medición permite
  afirmar, no 100 %.
* **Un error por archivo.** Las combinaciones **no se siembran juntas** en la 0.8.0: R15, R16 y
  los ítems de la importación miran un elemento a la vez, y dos errores sobre el mismo elemento se
  enmascaran (un punto duplicado que además queda fuera de todo ambiente se informa una vez). Esa
  interacción queda como límite declarado, no se mide.
* **Controles no detectables** (`NO-DET-*`): un plano coherente pero equivocado, sin segunda
  fuente. Deben dar «no detectado» y se informan con su número; miden el **límite declarado** de
  la auditoría de planos (horizonte H-D9), no entran en la tasa. Un control que la auditoría
  señalara se informa aparte: habría que ampliar el catálogo.
* **Segunda fuente de R16:** el plano limpio. R16 no corre en la reauditoría de un paquete.

## 4. Procedimiento

1. `uv run python scripts/medir_deteccion_planos.py --json > medicion.json` (código de salida 0 solo
   si la tasa es 1 y las falsas alarmas son 0).
2. Se copia la tabla (sin el JSON entero) a `docs/bitacora/2026-10-silice-080.md`, con la huella
   de este protocolo, el commit y la semilla.
3. Una prueba (`tests/unit/test_deteccion_planos.py`) repite la medición en cada corrida de la
   CI y exige la meta; otra comprueba que, si R15 dejara de funcionar, la medición lo nota.

## 5. Amenazas a la validez (declaradas)

* **Validez de constructo:** los errores son **sintéticos**, sembrados por el mismo equipo que
  escribió las reglas; no representan los errores que comete una persona dibujando. Detectar todo
  lo sembrado no prueba detectar lo que ocurre en una obra.
* **Validez externa:** un solo plano de oficina (OF-001, ficticio, programático) y un IFC de
  oficina; sin planos de obras ejecutadas. La tasa no se generaliza a otros dibujantes ni a otros
  programas de CAD.
* **Validez de conclusión:** n pequeño y todo en 100 %: el intervalo de §3 es ancho. Cero falsas
  alarmas se mide sobre OF-001; en otro plano las constantes supuestas de R15 (escala, distancia a
  la fuente) y de R16 (0,10 y 1,00 m) pueden dar alarmas que aquí no aparecen.
* **Circularidad:** las detecciones esperadas se escribieron antes del código (columna *Autor* `P`),
  pero el mismo equipo las eligió; la parte escrita por una persona ajena al equipo es una mejora
  para la fase Med.
