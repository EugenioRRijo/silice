# Acta: consejo sobre auditoría, alertas y estudio de mercado (2026-11-24)

**Fecha:** 2026-11-24 · **Pide:** Eugenio: «convoca al consejo para dar ideas de estos planteamientos para mejorar la
auditacion, las alertas y los estudios de mercado a la hora de montar un presupuesto en el propio sistema e incluso
cargarle uno externo y que se audite en vivo» · **Aprueba el plan:** Eugenio, el mismo día: «ok apruebo eso» ·
**Método:** consejo de cinco consejeros independientes (el Contrario, Primeros Principios, el Expansionista, el
Forastero y el Ejecutor), cinco revisiones cruzadas anónimas y una síntesis del presidente. Claude comprobó en el
repositorio lo que afirmaban y el presidente corrigió lo que no se sostenía.

## Veredicto

**Hasta la defensa no se programa nada nuevo** en auditoría, alertas ni estudio de mercado. Lo que falta son personas,
libros nuevos y un tercero, no funciones. El estudio de mercado falla por la entrada (la carga a mano, la antigüedad de
cada precio) y no por el cálculo. El «10 de 12» del libro de desarrollo no se presenta como resultado
([acta de los huecos](2026-11-24-huecos-de-reglas-antes-del-congelamiento.md)).

**Correcciones verificadas en el repositorio:**
- **Los falsos positivos y el criterio de fracaso ya están en el
  [plan no circular](../planes/2026-11-23-plan-auditoria-no-circular.md).** El criterio se sella con hash antes de
  medir el lote nuevo. Falta ejecutarlo, no diseñarlo.
- **Cerrar los huecos de reglas no rompió el congelamiento.** El plan lo admitía si quedaba anotado, Eugenio lo ordenó,
  hay acta y la etiqueta del congelamiento de reglas (Fase 2) se pone después de fusionar.
- **La tasa del BCV ya tiene límite de antigüedad**: no vale con más de 7 días (regla S1-R2).
- **La pantalla ya muestra el nombre de cada regla en llano**; el código solo lo acompaña.
- **«Las fallas L no ocurren al montar dentro de Sílice» es plausible, pero no está demostrado.** Solo hay prueba para
  la devolución. Sin una prueba propia se presenta como hipótesis.

## Ahora, sin romper el congelamiento

| # | Qué | Quién |
|---|---|---|
| 1 | Fusionar los huecos de reglas y poner la etiqueta del congelamiento con su hash | Claude |
| 2 | **Línea base humana:** un presupuestista revisa a mano los mismos libros con fallas sembradas y se mide cuántas encuentra y en cuánto tiempo (el SUS mide facilidad de uso, no eficacia). Protocolo de una página y planilla | Claude prepara; Eugenio consigue a la persona |
| 3 | En las sesiones del SUS, **prueba de comprensión de las alertas** («¿qué le dice?», «¿qué haría?», «¿qué alerta le faltó?») y **consentimiento informado**. La conduce alguien que no construyó Sílice | Claude prepara; Eugenio consigue a quien la conduce |
| 4 | Declarar en la tesis la **limitación del estudio de mercado**: mínimo de cotizaciones e inflación en bolívares dentro de la ventana de 90 días | Claude redacta |
| 5 | Buscar y **verificar** taxonomías publicadas de errores en hojas de cálculo (Panko, Rajalingham, EuSpRIG) como base para el tercero | Claude |
| 6 | Conseguir al tercero de la taxonomía, los 1 o 2 libros nuevos y 5 presupuestistas con fecha para el SUS | Eugenio |
| 7 | Contrastar el plan con los objetivos del anteproyecto v8 y repartir el trabajo con Nicolaz | Eugenio |

## Lista cerrada: para después de la defensa

Esta lista está **cerrada**: lo que no esté aquí no entra antes de la defensa, y lo que esté aquí tampoco. Una idea
nueva se agrega al final, con su fecha y su primer paso.

1. **Antigüedad de cada precio**, al montar un presupuesto y al cargar uno externo. Las fechas ya existen.
2. **La lista del proveedor entra al estudio de mercado** como cotizaciones con fecha; hoy solo entra a «precios de la
   empresa».
3. **Reauditar cada versión nueva de un libro externo** y mostrar qué hallazgos se resolvieron y cuáles son nuevos. Es
   la lectura elegida de «auditar en vivo»; auditar mientras se edita queda descartado por caro.
4. **Alertas de criterio al montar en Sílice:** rendimientos absurdos, cantidades y componentes olvidados. No hace
   falta llevar ahí las reglas L.
5. **Guardar los precios de los libros auditados** para el estudio de mercado, solo con consentimiento de su dueño.

**Descartado:** llevar Sílice al gremio y armar un índice de precios que compita con MaPreX (riesgo de dispersión).
6. **(Agregado el 2026-11-24, medición con las herramientas de `ub-mode`.)** Quitar el código duplicado que señala
   `dryer`: 44 candidatos, 36 idénticos. Uno está en las reglas congeladas: en `reglas_contexto.py`, `_argumentos` y
   `_partes_concat` son la misma función y solo cambia el separador. No se toca antes de la defensa porque cambiaría la
   huella de `reglas-congeladas-2026-11-24`. Primer paso: un refactor con las pruebas fijadas antes. Además, `mutator`
   no corre en este equipo: en Windows crea enlaces simbólicos y necesita el Modo de programador, que decide Eugenio.
7. **(Agregado el 2026-11-25, medición de crapper con la cobertura real.)** Probar mejor el escritor de la devolución
   (`adapters/hoja_empresa/escritor/`): reúne 33 de las 42 funciones con riesgo CRAP sobre 30, como `extender_semanas`
   (complejidad 43, cobertura 7,8 %) o `insertar_filas` (26 y 2,6 %). Primer paso: pruebas de caracterización que fijen
   lo que hoy escribe, antes de partir esas funciones. Las 2 de las reglas congeladas (`_pieza` y `celda_rotulo`) y
   la del núcleo (`core.budget.reajuste`, con el aval del tutor) van en la misma tanda.
