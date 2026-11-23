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
   `uv run python scripts/medir_auditoria_libro.py calcular --planilla p1.xlsx --otra p2.xlsx --clave clave.xlsx`.
   Sale una tabla en Markdown con cifras agregadas, sin celdas ni descripciones: es lo único que va a la tesis.

## Piloto del kappa

Según el v8, el kappa se calcula en una prueba piloto con 2 presupuestos que no entran en la evaluación. Si sale bajo,
se revisan las instrucciones de la planilla antes de medir. Para Landis y Koch (1977), de 0,61 a 0,80 es un acuerdo
«sustancial». Esa referencia está **por verificar** antes de citarla.

## Límites que se declaran

- La exhaustividad es aproximada: nadie conoce todos los errores reales de un libro.
- La detección depende del catálogo de siembra; los tipos de error que no estén en el catálogo no se miden.
- Con 3 economistas no hay inferencia estadística: se reportan cuentas, porcentajes y el kappa del piloto.
