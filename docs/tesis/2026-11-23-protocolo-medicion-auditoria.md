# Protocolo para medir la auditoría de un libro

> Para Eugenio y Nicolaz. Aplica el §8 del anteproyecto v8. La herramienta es
> `scripts/medir_auditoria_libro.py`. **Nada de lo que produce entra al repositorio:** los libros, las copias
> sembradas, la clave y las planillas marcadas se guardan en una carpeta fuera del proyecto (NORMAS §1). La herramienta
> se niega a escribir dentro del repositorio y a sobrescribir una planilla ya marcada.

## Qué mide

| Medida | Cómo se calcula | Qué responde |
|---|---|---|
| Precisión | hallazgos marcados «Verdadero» / hallazgos marcados | ¿Cuántas de las alertas de Sílice son errores reales? |
| Detección de lo sembrado | errores sembrados que Sílice señaló / errores sembrados | ¿Encuentra los errores que se sabe que están? |
| Exhaustividad aproximada | Verdadero / (Verdadero + «se le escapó») | ¿Cuántos errores reales se le pasan? Depende de cuánto buscó el evaluador y se declara así. |
| Kappa de Cohen | acuerdo entre dos evaluadores, descontado el azar (Cohen, 1960) | ¿La planilla de hallazgos es un instrumento confiable? |

Las filas en blanco se cuentan aparte como pendientes y no entran en la precisión.

**La unidad es la causa raíz, no el síntoma.** Una fórmula copiada con una fila fija produce un hallazgo por cada
partida que la repite. La planilla junta en una sola fila los hallazgos que tienen la misma regla y la misma primera
cláusula (qué lee y de dónde). Para eso no se cuentan las celdas, los números ni el valor que se encontró en cada caso.
La fila trae sus «Ocurrencias», todas sus celdas y la severidad más grave. En 5 libros de prueba locales, 139
hallazgos quedaron en 76 causas, y las 29 alertas L1 de un mismo libro, en 3. El resumen informa esa compactación. Con
`exportar --sin-agrupar` sale un hallazgo por fila, por si se quiere comparar.

Los avisos de regla «no aplicable» (R2 y R7 cuando el libro no trae curva ni plan) no se exportan para marcar: se
anotan en las instrucciones de la planilla.

## Papeles

- **Quien siembra:** el autor que no escribió las reglas de auditoría (v8). Siembra a partir de un catálogo de tipos de
  error sacado del diagnóstico, que se fija antes de mirar las reglas. Si no hay un autor así, siembra el experto en
  ingeniería de costos o un tercero.
- **Evaluadores:** dos economistas de la empresa. Cada uno marca solo y no ve la clave.
- **Los 3 expertos que validan los instrumentos** no participan en nada de esto.

## Pasos

1. **Clave vacía:** `uv run python scripts/medir_auditoria_libro.py clave --salida D:/medicion/clave.xlsx`
2. **Siembra:** en una copia del libro marcada como prueba, quien siembra cambia una celda por error y anota cada uno en
   la hoja «Sembrados» de la clave: número, celda (`HOJA!F12`), tipo de error y qué cambió.
3. **Exportar:** `uv run python scripts/medir_auditoria_libro.py exportar COPIA.xlsx --salida D:/medicion/p1.xlsx`.
   La planilla trae un hallazgo por fila, numerado, y el SHA-256 de la copia auditada. Para el segundo evaluador se
   exporta otra vez la misma copia en `p2.xlsx`.
4. **Marcar:** cada evaluador marca su planilla, Verdadero o Falso en «Veredicto», y anota en «Se le escaparon» los
   errores que encuentre y Sílice no señaló.
5. **Cotejar la siembra:** quien siembra llena en la clave «Detectado por hallazgo N°» cuando el error aparece en otra
   celda (por ejemplo, un rendimiento sembrado en un APU que se señala en el precio de la partida). Si la deja vacía, la
   herramienta cuenta como detectado el primer hallazgo de la misma celda.
6. **Calcular:**
   `uv run python scripts/medir_auditoria_libro.py calcular --planilla p1.xlsx --otra p2.xlsx --clave clave.xlsx --libro COPIA.xlsx --libro-base LIBRO.xlsx`
   (con las mismas opciones de `exportar`; ver «Detección sin acreditar lo previo» más abajo).
   Sale una tabla en Markdown con cifras agregadas, sin celdas ni descripciones: es lo único que va a la tesis.

## Piloto del kappa

Según el v8, el kappa se calcula en una prueba piloto con 2 presupuestos que no entran en la evaluación. Si sale bajo,
se revisan las instrucciones de la planilla antes de medir. Para Landis y Koch (1977), de 0,61 a 0,80 es un acuerdo
«sustancial». Esa referencia está **por verificar** antes de citarla.

## Límites que se declaran

- La exhaustividad es aproximada: nadie conoce todos los errores reales de un libro.
- La detección depende del catálogo de siembra; los tipos de error que no estén en el catálogo no se miden.
- Con 3 economistas no hay inferencia estadística: se reportan cuentas, porcentajes y el kappa del piloto.

## Línea base humana (2026-11-24)

El cuestionario SUS mide facilidad de uso, no si el sistema detecta más o más rápido que una revisión manual.
Para tener una referencia concreta, un presupuestista revisa a mano los **mismos libros con fallas sembradas**
que audita Sílice, sin ver antes los resultados del programa ni la clave sellada (acta del consejo del
2026-11-24).

### Quién puede hacerlo y quién no

- **Puede hacerlo:** un presupuestista o economista con experiencia revisando presupuestos en Excel que **no
  construyó Sílice**, no escribió sus reglas y no participó en la siembra de fallas.
- **No puede hacerlo:** Eugenio, Nicolaz, la persona que sembró las fallas, ninguno de los 3 expertos que
  validan los instrumentos del anteproyecto ni nadie que haya visto antes el informe de Sílice o la clave
  sellada de esos libros.

### Condiciones y resguardo de los libros

- **Los libros con datos reales nunca salen del equipo de Eugenio** (NORMAS §1). Toda la revisión manual se
  hace en ese equipo; los libros sembrados, la clave sellada y las planillas llenas se guardan en una carpeta
  local fuera del repositorio.
- **Orden obligatorio de las tareas:** primero usted revisa cada libro a mano en Excel, con su forma habitual
  de trabajo y sin abrir Sílice. Solo después, si también participa en la evaluación con el sistema, ve los
  resultados de Sílice. **Nunca al revés:** ver antes el informe de Sílice invalida la línea base humana.
- **Tiempo máximo por libro:** por confirmar con Eugenio antes de iniciar la medición. El mismo tope se fija
  por escrito para todo el lote; al cumplirse, se detiene el cronómetro y se anota lo encontrado hasta ese
  minuto.
- **Qué se registra:** cuántas fallas sembradas encuentra, cuáles, el minuto en que señala cada una, cuántas
  cosas marca que no eran fallas y los minutos totales dedicados al libro. La clave sellada se abre solo al
  terminar la revisión manual para cotejar lo encontrado.
- Si usted encuentra un error real del libro original que no estaba en la clave sembrada, se anota en
  «Observación» y no se cuenta como marca errónea.

### Planilla de línea base humana

Se llena en una planilla local (fuera del repositorio), con una fila por cada falla de la clave sellada y el
conteo de marcas que no eran fallas por libro. Al pie se anotan los minutos totales de cada libro.

| Libro | Falla sembrada (clave sellada) | ¿La encontró? | Minuto | Marcas que no eran falla | Observación |
|---|---|---|---|---|---|
| | | Sí / No | | | |
| | | Sí / No | | | |
| | | Sí / No | | | |

**Resumen por libro:** Libro ____ · Minutos totales a mano: ____ · Fallas encontradas: ___ de ___ · Marcas que
no eran falla: ___

### Revisión por partida (kappa experto–Sílice, acta del 2026-11-25)

En la misma revisión ciega, el experto dice **por cada partida** del PRESUPUESTO si tiene un error que un
presupuestista corregiría. La planilla vacía sale del libro, sin nada de Sílice:

`uv run python scripts/medir_auditoria_libro.py revision LIBRO.xlsx --salida D:/medicion/rev.xlsx`

Trae la hoja «Revisión por partida» con una fila por partida (`Fila`, `Partida`, `Código`, `Descripción`,
`¿Tiene error?`, `Nota`) y el SHA-256 del libro. Cada partida se identifica por su **fila del PRESUPUESTO**
(`Fila`), no por su número, porque hay libros con números de partida repetidos. El experto escribe **Sí** o **No**
en «¿Tiene error?»; en blanco cuenta como pendiente y no entra en el kappa. Sirve también un CSV con las columnas
`Fila` y `¿Tiene error?` (separadas por coma o punto y coma). La revisión debe traer exactamente las filas de
partida del libro, y sin esas dos columnas se rechaza aunque no traiga filas. `calcular` coteja el SHA-256 de una
revisión .xlsx con el del libro dado en `--libro` y la rechaza si no coinciden; un CSV no trae huella y no se coteja.

Sílice dice «Sí» en una partida cuando alguna fila de la planilla exportada cita una celda del renglón de esa partida
en el PRESUPUESTO (también dentro de un rango) o de la hoja APU unida a ella; si varias partidas comparten un APU,
cuenta para todas. **Regla conservadora (acta literal):** un hallazgo cuenta para todas las partidas de sus celdas
de origen, aunque una regla (L1, L2, L3) cite la celda de otra partida solo como referencia; si así marca de más, el
kappa de Sílice baja, nunca sube. Las filas que no caen en ninguna partida (RESUMEN, INSUMOS, filas de totales) se
informan aparte y no entran en el kappa. El kappa se calcula sobre todas las partidas, sanas incluidas, y es el único
que decide el tercer criterio de fracaso; si no hay variación (todas sanas o todas con error para los dos) o no hay
partidas revisadas, el criterio dice que no se puede calcular. El kappa entre dos evaluadores (`--otra`) mide la
fiabilidad entre personas y no decide nada. Con `--libro`, `calcular` audita ese libro con las mismas opciones que
`exportar` (con `--recalcular`, el libro trasplantado) y exige que reproduzca la planilla:

`uv run python scripts/medir_auditoria_libro.py calcular --planilla p1.xlsx --libro LIBRO.xlsx --revision-experto rev.xlsx --fecha AAAA-MM-DD`

**Detección sin acreditar lo previo.** Con `--clave`, `calcular` exige el libro sembrado (`--libro`) y el libro sin
sembrar (`--libro-base`): los audita a los dos con las mismas opciones que `exportar` (`--fecha`, `--perfil`,
`--recalcular`, `--sin-agrupar`), comprueba que la auditoría reproduce la planilla y descuenta lo que el libro base
ya tenía con la misma función que la cifra oficial de `medir_inyeccion.py` (`scripts/hallazgos_previos.py`):

- En las reglas que juntan las celdas de una hoja o una sección en un solo hallazgo (L5, L7 y el L1 de la hoja AUX)
  se descuenta **por celda**: el hallazgo acredita solo las celdas que ningún hallazgo previo de esa regla citaba.
  Por eso, en esas reglas, **no se siembra sobre una celda que ya tiene un hallazgo previo de la misma regla**: esa
  falla no se podría acreditar.
- En las demás reglas, un hallazgo se descuenta solo si coincide entero con uno previo (misma regla y mismas
  celdas). Así una celda que un hallazgo previo citaba solo como referencia (el destino de un L3, la celda correcta
  de un L1) no esconde una falla sembrada después en ella.
- Los hallazgos sin celdas (R2, R7) se emparejan con los previos por su descripción, primero exacta y después por
  el patrón de la causa, nunca por el orden en que llegan.

La columna manual «Detectado por hallazgo N°» de la clave no puede señalar una fila de la planilla que solo trae
hallazgos previos: `calcular` se detiene y pide corregir la clave (o dejar la columna vacía si ningún hallazgo nuevo
señala la falla). **Límite que se declara:** si la fila es mixta (agrupa hallazgos previos y nuevos), la herramienta
no puede saber a cuál de ellos se refiere quien sembró y acepta la columna manual; esa columna es el juicio de quien
sembró, y la regla de no sembrar sobre una celda con hallazgo previo de la misma regla evita el caso.

### Cómo se compara con Sílice

Con los mismos libros sembrados (recalculados con LibreOffice y auditados con las reglas congeladas, según el
plan no circular), se comparan lado a lado la revisión manual y Sílice:

- **Detección de fallas sembradas:** proporción de fallas sembradas encontradas por el presupuestista frente a
  las detectadas por Sílice, reportada con cuentas, porcentaje (coma decimal) e **intervalo de confianza de
  Wilson al 95 %** para cada uno. Se detalla también qué fallas halló solo la persona (por ejemplo, criterio
  de obra) y cuáles solo Sílice.
- **Falsos positivos:** en la revisión manual, marcas que no eran fallas sobre el total de problemas señalados
  por el presupuestista; en Sílice, causas informadas marcadas «Falso» por el experto sobre el total de causas
  informadas. Ambas proporciones se reportan con su **intervalo de Wilson al 95 %**.
- **Tiempo de revisión:** minutos totales por libro a mano frente al tiempo que toma correr Sílice y revisar
  sus causas.
- **Límite que se declara:** con pocos revisores y pocos libros, la comparación con el procedimiento manual es
  descriptiva e ilustrativa (sin pruebas de inferencia estadística) y se presenta así en la tesis.
