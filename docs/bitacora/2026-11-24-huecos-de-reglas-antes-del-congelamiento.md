# Acta: huecos de reglas cerrados antes del congelamiento (2026-11-24)

**Fecha:** 2026-11-24 · **Rama:** `feature/huecos-de-reglas` (desde `9266f6d0`) · **Autoriza:** Eugenio, 2026-11-24,
con estas palabras: «sí, corrige los huecos de reglas antes de congelar» · **Plan:**
[plan no circular, «Segunda medición»](../planes/2026-11-23-plan-auditoria-no-circular.md). El plan pide anotar en la
bitácora todo cambio de reglas previo al congelamiento; este es ese registro.

## Por qué

La medición una falla por vez detectó 5 de 12 fallas inyectadas (41,7 %), por debajo del umbral de fracaso del 50 %.
De las 7 que escaparon, 5 eran huecos reales de reglas y 2 son fallas equivalentes, que no cambian ninguna cifra.

| Falla | Qué deja el inyector | Por qué escapaba |
|---|---|---|
| #1 | `APU-02!C10 = VLOOKUP(B11,PRECIOS,2,0)`, que busca el código de la fila 11 | El APU queda coherente consigo mismo: ninguna regla miraba la fila del código |
| #7 | `APU-02!D12 = VLOOKUP(B13,PRECIOS,3,0)`, con B13 vacía, que da #N/A | Lo mismo, y además nadie miraba las celdas con error de cálculo |
| #3 | `APU-02!G36 = SUM(G32:G34)`, que deja fuera el transporte (G35) | L4 expande el rango de SUM, pero ignoraba un componente que hoy vale 0 |
| #5 y #6 | `SUMPRODUCT(G5:G7, H5:H6)` en RESUMEN, con rangos de distinto tamaño, que da #VALUE! | L9 no puede cuadrar un error: lo saltaba |

El diagnóstico anterior de la #3 («L4 solo revisa sumas escritas con +») era **incorrecto**: L4 sí lee el rango. El
hueco era el componente en cero.

## El cambio

Prueba en rojo `163ccc9c` (`tests/unit/test_hoja_empresa_reglas_calculo.py`, con 5 rojas y 1 de regresión) y verde `b567f4d3`. Las reglas
nuevas viven en `adapters/hoja_empresa/reglas_calculo.py`:

- **L1, BUSCARV con el código de otra fila.** Un BUSCARV de un APU que busca en la lista de precios el código de otra
  fila. Si la cifra cambia es ERROR (por ejemplo, el precio de otro insumo); si es texto es ADVERTENCIA. Una fila sin
  código propio no se juzga.
- **L4, componente en cero fuera del costo directo.** Es ADVERTENCIA sin impacto: el monto de hoy no cambia, pero el
  día en que ese componente tenga valor no entrará al precio. L4 entero se mudó a este módulo sin cambiar su lógica.
- **L5, celda de la cadena de montos con error de cálculo.** Cubre #VALUE!, #N/A, #DIV/0! y los demás errores, en los
  APU, en el PRESUPUESTO y en el RESUMEN. Se informa una fila por hoja. El #REF! queda fuera, porque L5 ya lo informa
  por la fórmula.

Para no crear un ciclo de importación, el contexto común de las reglas (analizador de fórmulas, `_Contexto` y
utilidades) se separó en `adapters/hoja_empresa/reglas_contexto.py`. `reglas.py` baja de 1707 a 1146 líneas. El
catálogo L1-L9 no cambia, ni `core/`. El manifiesto de corrida firma también los dos módulos nuevos.

## Revisión independiente

Un revisor de pruebas (subagente `silice-rev-pruebas`, de solo lectura) confirmó que el movimiento de código es exacto
y que L4 conserva su lógica. Pidió cambios menores, y Claude los verificó y corrigió con pruebas en rojo (`ba97ba85`):

- **El L5 del RESUMEN se informa, no se da por corregido.** La devolución reescribe los APU y el PRESUPUESTO, pero
  copia el RESUMEN con sus fórmulas (solo arregla los #REF!). Un SUMPRODUCT con rangos de distinto tamaño seguiría
  dando error. L1 y L4 sí son «corregido», porque la devolución arma cada BUSCARV con el código de su propia fila y el
  costo directo con los cuatro componentes. Una prueba lo comprueba volviendo a auditar la devolución.
- **La lista de partidas con costos omitidos (V-16) cuenta solo el L4 de gravedad ERROR.** La advertencia por un
  componente en 0 no omite costos.
- **L1 compara lo que trae cada búsqueda**, no la cifra guardada, porque la fórmula puede hacer cuentas alrededor del
  BUSCARV. Compara el código sin distinguir mayúsculas, como Excel.
- **L4 no toma un componente con texto o error como «en 0»**: ese caso lo informa L5.
- **L5 cubre también #CALC! y los demás errores nuevos de Excel**, y deja fuera las plantillas sin partida, igual que
  L4 y L6.
- `reglas.py` importa `reglas_calculo` arriba, sin import diferido, porque ya no hay ciclo.

**Límite declarado:** un #REF! que llega por INDIRECT, sin #REF! escrito en la fórmula, no se ve. Incluir los #REF!
sin fórmula rota repetiría los arrastres que L5 ya informa: en los libros reales hay 7 celdas así en el RESUMEN.

## Evidencia

- **Libros reales (5, solo en el equipo):** los mismos hallazgos por regla y gravedad antes y después. Hubo 0 BUSCARV
  desalineados entre 2.956, 0 componentes en cero fuera del costo directo y ningún error de cálculo distinto de #REF!.
  Solo se compararon conteos; nada sale del equipo.
- **Medición repetida** (mismo libro, misma taxonomía de plantilla, semillas 7 a 18, LibreOffice 26.8.3): **10 de 12
  (83,3 %)**. Escapan solo las dos equivalentes: #4 (signo de un número de ítem) y #9 (fórmula de descripción borrada
  que conserva su texto).

## Límite que se declara

El 83,3 % **no es la cifra de la tesis**. Las reglas se corrigieron viendo estas 12 fallas del libro de desarrollo, así
que la cifra mide lo que se aprendió, no lo que generaliza. La medición válida es la de la Fase 3: los libros nuevos
que nadie ha visto y la taxonomía del tercero, con las reglas ya congeladas. Este acta y la cifra anterior (41,7 %) van
en el capítulo de resultados como historia del desarrollo.

## Cómo se revierte

Se revierten los commits de la rama `feature/huecos-de-reglas`. `reglas_contexto.py` puede quedarse, porque solo mueve
código.
