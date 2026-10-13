# Protocolo del experimento del asistente de IA (OE-H2)

Estado: **BORRADOR** hasta el congelado de la tarea 20 (S4 §9.1). Se versiona aquí; las huellas del
banco, del protocolo y del auditor quedan en `asistente/experimento/congelado.json` cuando se
congela. Los datos son construidos y declarados (NORMAS §1): las tareas no representan obras reales.

## 1. Pregunta

¿Cuántos errores de las propuestas de cada modelo detecta el auditor, con cuántas falsas alarmas, y
cuántas propuestas son válidas? Misma tarea, mismas herramientas, mismas instrucciones y mismo
validador para los dos modelos; solo cambia el proveedor.

## 2. Banco de tareas

- Fichas: `tests/fixtures/asistente/tareas/*.json` (4 de desarrollo, 12 de evaluación; 3 de las 12
  con errores sembrados). Las escribe `scripts/escribir_banco_asistente.py` y no se tocan después
  de la revisión de la segunda persona.
- **Huella del banco** (SHA-256 de nombres y bytes con saltos LF):
  `29446b12ebf646d89ef9ccae3b597989e8787757e7fdf9a66024ff098aa3a0b2`
- Segunda persona que revisó pedido y referencia: ______ (fecha ______).
- Respuestas preparadas: cada una lleva palabras clave; una pregunta del modelo (sin tildes ni
  mayúsculas) recibe la primera respuesta cuyas palabras aparecen todas; si ninguna, «no lo se». El
  experimentador no elige ni redacta durante las corridas.

## 3. Taxonomía, emparejamiento y conteo (reglas cerradas, S4 §9.5)

E1 partida equivocada · E2 unidad · E3 dimensión o posición fuera de 0,001 m · E4 punto en ambiente
equivocado o fuera de todo ambiente · E5 fuente o circuito equivocados · E6 elemento omitido · E7
elemento sobrante o duplicado · E8 dato sembrado del pedido copiado sin objeción.

El comparador **nunca empareja por id**: clase, especialidad y tipo iguales; distancia (esquinas
para ambientes, 3D para fuentes y puntos); vecino más cercano con tolerancia de 0,10 m (empates por
coordenadas, nunca por id); las tareas de posición libre se trasladan por la esquina de su primer
ambiente. Un elemento desplazado más de 0,10 m cuenta como omitido más sobrante (E6 + E7). E8 es el
valor sembrado que **queda en el borrador**; no se cuenta además como E3, ni su punto «fuera» como
E4. Las tolerancias y la fecha de R12 se leen de `protocolo.json`.

**Traducción de ids.** Con los pares tomados se traducen al de la referencia los ids de ambientes,
fuentes, puntos, recorridos, partidas y **circuitos**. Los circuitos vienen de la base de la ficha
(la validación exige que el circuito de una propuesta exista), y se emparejan por sus datos: tablero
traducido, número, conductores, calibre y puntos máximos. Las claves de segmento
(`esp_segmentos:<fuente>|x,y,z|x,y,z`) se traducen por la fuente y por la traslación.

**Hallazgos esperados por construcción.** Un hallazgo del borrador empata con uno de la referencia
por (regla, severidad, claves traducidas). Un `origen_id` **derivado** (las filas que calculan las
reglas de cantidades: `esp_fuentes:F;esp_segmentos:…;esp_puntos:…;+N`) se corta a 120 caracteres,
y cuántas claves secundarias caben y el `+N` dependen del **largo** de los ids que eligió el modelo.
Para empatar, de esos `origen_id` solo cuentan sus fuentes (que van primero y lo identifican junto
con el código de la partida); las secundarias y el `+N` se descartan. La detección (qué filas cita
un hallazgo) sigue usando todas las partes. Se eligió así, y no empatar por el conjunto de claves
secundarias traducidas, porque ese conjunto cambia con el largo de los ids: con un tablero llamado
`TABLERO-PRINCIPAL-DEL-PISO-F0` el `+5` de la referencia pasa a `+6` y un segmento queda fuera.

**Conteo de errores (ruling I1, por ratificar por Eugenio).** Un error **por par y por tipo**: un E3
nombra en su campo todos los campos que difieren (`x,y`; `largo,ancho`), y un E5 la fuente y el
circuito si difieren los dos (el spec dice «par con alguna dimensión o coordenada que difiere →
E3» y «par cuya fuente o circuito difieren → E5»). Las **cascadas no se colapsan**: el recorrido
que sigue a su punto, un E5 por cada punto de una fuente que no empareja, el E7 del punto más el E7
de su recorrido, y el E3 más el E4 del punto que sale de su ambiente, cuentan cada uno. Para que
esa elección no infle la detección, el informe da además la **detección por fila** (filas del
borrador con algún error detectable y, de ellas, las citadas por algún hallazgo).
**Advertencia:** la regla de conteo cambia las tasas; Eugenio debe ratificarla antes del congelado.

**Partidas (desviación declarada del paso 4 de §9.5).** Se emparejan primero por código igual y
luego las sobrantes de la misma especialidad, pero los empates **no** se resuelven por el orden de
`items_base`: se toma el par de menor discrepancia (unidad equivalente primero, luego la cantidad
más cercana), luego el orden de la referencia y el contenido de la fila. Motivo: el spec exige
también que la misma corrida con las filas en otro orden dé la misma clasificación, y con el orden
de `items_base` un E1 que copia el código de otra partida le robaba el par y daba dos E3 espurios
de cantidad. Dos filas idénticas salvo el id (un duplicado exacto): cuál es el par y cuál el E7 lo
decide su lugar en la lista; no cambia la clasificación por contenido ni el veredicto.

## 4. Qué regla debería detectar cada tipo (hipótesis, declarada antes de medir)

- **E1**. Regla que debería detectarlo: ninguna; Nota: «mentira consistente» con unidad compatible
  (horizonte H-D9): no detectable por diseño
- **E2**. Regla que debería detectarlo: R3; Nota: unidad incompatible con la del APU
- **E3**. Regla que debería detectarlo: R9, R10; Nota: solo si el desplazamiento rompe la geometría
- **E4**. Regla que debería detectarlo: R9; Nota: punto fuera de su ambiente
- **E5**. Regla que debería detectarlo: R10; Nota: circuito o fuente equivocados
- **E6**. Regla que debería detectarlo: ninguna; Nota: sin fila que citar: no detectable por diseño
- **E7**. Regla que debería detectarlo: R10, R15; Nota: duplicado que excede el límite del circuito
  (R10) o dos puntos a menos de 0,001 m (R15)
- **E8**. Regla que debería detectarlo: R9; Nota: valor imposible copiado del pedido

Las hipótesis se revisan **antes** del congelado y no después. Los tipos sin regla se informan
aparte, con su número.

## 5. Condiciones, reglas y congelado

- A (principal): sin retroalimentación; `pedir_informe_auditoria` desactivada. B (secundaria):
  activada. Si el tiempo o el costo aprietan, B se cae primero.
- 12 tareas × 2 modelos × 2 condiciones × 3 repeticiones = 144 corridas (72 con Claude). Aceptación
  automática de toda propuesta válida (mide al modelo, no a la persona). Respaldo del servidor
  desactivado. Registro de modelo, esfuerzo, versión del SDK, de Ollama y del modelo local.
- Reglas del auditor: las de `protocolo.json::reglas_del_experimento`: R1-R10 y **R15** (maestro
  §3.3, columna «Experimento de S4»; S4 §9.1: las de R8-R16 que apliquen al borrador). Las 16
  referencias del banco dan cero hallazgos de R15. R12 (cuando exista) a la fecha **fija**
  `fecha_de_evaluacion_r12`. La reevaluación es en memoria. `corrida --conjunto evaluacion` y
  `mutaciones` comprueban, **antes de gastar**, que el auditor corre exactamente esas reglas en
  cada referencia de evaluación.
- **`PENDIENTE` (ruling M1).** La elaboración (`core/budget/presupuesto.py`) declara con un
  hallazgo `PENDIENTE` de severidad ERROR cada ítem cuya partida no tiene composición de APU. No es
  una regla del auditor (`protocolo.json::hallazgos_de_la_elaboracion`), pero viaja en el mismo
  informe que ve la persona y que recibe el modelo en la condición B. Criterio: **cuenta** igual en
  A, en B y en la puntuación (como esperado por construcción si lo da la referencia, como detección
  si cita una fila con error, como falsa alarma si no). Por eso `core/budget/presupuesto.py` entra
  en el congelado.
- **Congelado (ruling I5).** `archivos_del_auditor` cubre las reglas y sus umbrales (`LIMITE_*`),
  la elaboración (`core/budget/presupuesto.py`), la hoja (`ui/hoja.py`), la derivación y las
  cantidades por especialidad, el instrumento de medición (banco, modelo, comparador, métricas,
  mutaciones, corrida, congelado, `scripts/evaluar_asistente.py`, `scripts/_experimento.py`, el
  catálogo y las composiciones del experimento) y lo que hace iguales las condiciones de los dos
  modelos: instrucciones (`asistente/privacidad.py`), herramientas, validación, orquestador,
  propuestas, catálogo, tarifas, precios, configuración y adaptadores de los proveedores. Cada
  archivo debe existir (si falta, el cálculo de la huella falla).

## 6. Métricas y umbrales (se congelan con el protocolo)

Detección del auditor (errores detectables con un hallazgo no esperado que cite su fila ÷ errores
detectables, total y por tipo, con bootstrap agrupado por tarea: 10 000 réplicas, percentiles 2,5 y
97,5, semilla fija); **detección por fila** (§3); falsas alarmas; errores que escapan; propuestas
válidas al primer intento; guardas activadas; exhaustividad; costo y tiempo. Los hallazgos que da la
propia referencia no cuentan. Si ningún error es detectable, el intervalo se informa como «sin
errores detectables». Umbrales propuestos: detección ≥ 80 %, falsas alarmas ≤ 10 %, 100 % de los
números finales calculados por el sistema. La comparación entre modelos es descriptiva (12 tareas
no dan significancia).

## 7. Corridas, lo pagado y la reanudación (ruling I3)

- Cada sesión se guarda **antes de puntuar**: `motivo` de la sesión, `uso` (fichas), costo y las
  propuestas serializadas, que con la ficha bastan para reconstruir el borrador final y volver a
  puntuar sin pagar. Así el gasto acumulado nunca se queda corto.
- La puntuación va en un `try`: si `aplicar`, `comparar` o el auditor fallan, la corrida queda
  guardada como `fallo_al_puntuar`, con su costo y el error, y el proceso **se detiene** (código 5):
  si el instrumento falla, no se sigue pagando.
- Al reanudar, **ninguna corrida guardada se vuelve a pagar**. Las `sin_puntuar` y
  `fallo_al_puntuar` se puntúan de nuevo desde sus propuestas, sin pagar (también con
  `evaluar_asistente.py repuntuar`); si alguna sigue fallando, se detiene antes de gastar más. Una
  caída del proveedor (`error_de_proveedor`) queda como corrida, no se reemplaza ni se repite.
- El informe cuenta solo las corridas normales; las de `error_de_proveedor` y las que no se pudieron
  puntuar se listan aparte («excluidas»), y su costo sí suma. `informe` exige el congelado vigente y
  las corridas completas: cada (modelo, condición) presente con las 12 tareas × 3 repeticiones y
  ninguna sin puntuar (código 3 si no).
- **Diferido a T20:** el registro `ia_*` de cada corrida en una base de experimento aparte (S4
  §9.4). Hasta entonces, lo reauditable es el archivo de corridas.

## 8. Medición controlada con mutaciones

Sembrador determinista con semilla fija: `n = 24` mutantes por tipo, repartidos por turno entre las
tareas de evaluación donde el tipo aplica (RP9-7: E1 y E2 solo en las 2 mixtas; E8 solo donde la
ficha declara un sembrado construible). Los mutantes repetidos se descartan (el auditor es
determinista: un duplicado no es un ensayo independiente) y se informa el **n efectivo** por tipo;
Wilson se calcula con ese n. Intervalo de Wilson al 95 % por tipo. Se corre **después** del
congelado. El mutante E3 mueve un punto 0,05 m en un sentido que lo deja **dentro** de su ambiente
(si ninguno, se descarta), para no medir E4 bajo el nombre de E3; un mutante idéntico a la
referencia se descarta; los sembrados se aplican a ambientes, fuentes, puntos y partidas.

## 9. Costo y aprobación

Estimación por tarea con la tarifa de `asistente/precios_ia.json`. El piloto (solo tareas de
desarrollo, ≈ 20 USD) y la corrida de evaluación (≈ 87 USD de cota) necesitan la **aprobación
escrita de Eugenio** con la cifra medida. `--tope-usd` es finito y mayor que cero; con Ollama, cuyo
costo es 0, basta un tope de 1 USD.

## 10. Orden

1. Banco congelado con huella (S4.0).
2. Piloto con tareas de desarrollo: fija el esfuerzo de Claude, mide el costo y prueba el
   comparador.
3. **Congelado** del protocolo y de la huella del auditor, DESPUÉS del piloto y ANTES de la primera
   corrida de evaluación, con el árbol de git limpio (`congelar` lo exige).
4. Corrida de evaluación y medición controlada.
5. `docs/resultados_asistente.md`, generado por el script.

## 11. Amenazas a la validez

Quien construye las tareas conoce el sistema; 12 tareas y 3 con errores sembrados dan intervalos
anchos; la aceptación automática es distinta del uso real; los modelos no son deterministas (por
eso 3 repeticiones); un hallazgo de R8 por un supuesto declarado cuenta como detección aunque el
supuesto sea inocuo; la regla de conteo (un error por par y tipo, sin colapsar cascadas) pesa en la
tasa por error, y por eso se informa también por fila. Cada una se declara en la tesis.
