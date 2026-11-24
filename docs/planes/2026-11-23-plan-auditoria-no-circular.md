# Plan: una auditoría más robusta y una evaluación que no sea circular

> 2026-11-23. Veredicto del consejo (skill `llm-council`): 5 consejeros, revisión cruzada anónima y un presidente.
> Eugenio lo pidió así: «un plan de backend y de lógica para auditar más robusta… y no ser solo circular».
> Nada de este plan toca `core/`. Los módulos nuevos son instrumentos de medición, no funciones de producto,
> así que respetan el congelamiento.

## El problema

Hoy Sílice mide **consistencia, no acierto**. La evaluación es circular en cuatro puntos:

- las reglas, los libros sintéticos y los errores sembrados los escribió el mismo equipo, con IA;
- F1 «verifica» recalculando con el mismo motor de Sílice;
- los umbrales se fijaron sin datos (8 de los 17 viales son supuestos);
- los 5 libros reales del equipo ya guiaron las reglas y los umbrales, así que están **contaminados por el desarrollo**.

Las 18.600 pruebas verifican que el código hace lo especificado, no que la auditoría acierte.

## Lo que se defiende en 2027

**Afirmación.** «Sílice detecta de forma reproducible errores que un experto independiente confirma: X de N fallas
inyectadas por un tercero, con intervalo de confianza del 95 % amplio. Su tasa de falsos positivos es Y por causa, con
un costo de revisión de Z minutos por libro. No detecta errores de criterio de obra fuera de su taxonomía, y sus 8
umbrales viales son supuestos.»

**Hallazgo verdadero.** Una diferencia que un presupuestista corregiría antes de entregar el presupuesto. Lo decide el
ingeniero de costos externo, que marca a ciegas, sin ver lo que dijeron las reglas.

**Criterio de fracaso.** Se fija y se sella con hash **antes** de medir el lote nuevo. Si se cumple cualquiera de estos
tres, la tesis afirma solo «herramienta de apoyo con cobertura limitada», y lo reporta tal cual:

- detecta menos del 50 % de las fallas que inyectó el tercero;
- más del 40 % de las causas que informa en libros reales son falsos positivos según el experto;
- el kappa entre el experto y Sílice queda por debajo de 0,4.

## Qué técnicas sirven y cuáles no

| Técnica | Veredicto | Por qué |
|---|---|---|
| Oráculo independiente (LibreOffice sin interfaz) | **Sí, primero** | Es lo único barato y ajeno a Sílice. Pero solo cubre F1: prueba que el valor guardado coincide con su fórmula, no que la fórmula sea correcta |
| `formulas` o `pycel` como juez | No | Son menos fieles a Excel; depurar el oráculo se comería semanas |
| Inyección de fallas desde una taxonomía publicada | Sí, **solo si inyecta un tercero** | Si inyecta la misma IA que escribió las reglas, sigue siendo circular |
| Taxonomía escrita antes de releer las reglas | **Sí** | Panko y EuSpRIG más criterio de obra. La cobertura baja se publica tal cual: esa honestidad es parte del resultado |
| Pruebas metamórficas | Sí | Sirven para robustez, no para validar acierto. No se presentan como validación |
| Prerregistro con hash | Sí, **pero sobre un lote nuevo** | Sellar sobre los 5 libros de desarrollo es teatro |
| Sensibilidad ±50 % de los umbrales | Sí, solo como sensibilidad | No se calibra con los mismos economistas que evalúan, porque eso contamina la prueba |
| Matriz de confusión con el experto | **Sí, es la única verdad** | Se cuenta por causa raíz y con intervalos de Wilson |
| Comparación con el procedimiento manual | Solo ilustrativa | Con 3 economistas no hay potencia estadística |
| Tasa de «libro no interpretable» | Sí | Es barata y honesta |
| Benchmark publicable o un cambio de tesis | No | No cabe en los recursos ni en el congelamiento |

## Fases

### Fase 0 (semana 1): protocolo y personas, lo hace Eugenio

- Conseguir la **carta de compromiso del ingeniero de costos externo**, con fechas de marca ciega. Es el único cuello de
  botella real.
- Escribir en media página la definición de «hallazgo verdadero» y quién la decide (ver arriba).
- Escribir la taxonomía de 15 a 20 categorías (Panko, Rajalingham y EuSpRIG, más los errores de criterio de obra:
  rendimientos, depreciación y toneladas) **sin abrir las reglas**. Que la escriba Nicolaz o el tutor.
- Pedir a la empresa **1 o 2 libros nuevos**, mejor si son viales. Serán el conjunto de prueba que nadie ha visto.

### Fase 1 (semanas 2 a 4): backend de evaluación, lo hace Claude con TDD

| Módulo | Qué hace | Salida | Criterio de éxito |
|---|---|---|---|
| `aplicacion/oraculo_libreoffice.py` | Recalcula el libro con LibreOffice sin interfaz, con versión y configuración regional fijas, y compara con lo guardado | JSON de discrepancias por celda | En el libro ficticio de 12 errores, el oráculo y F1 coinciden en el 100 % de las fallas de cálculo y toda diferencia queda explicada |
| `aplicacion/manifiesto_corrida.py` | Registra el hash de las reglas y los umbrales, la versión de LibreOffice, la configuración regional y la semilla | Un manifiesto adjunto a cada auditoría | Dos corridas con el mismo manifiesto dan una salida idéntica byte a byte |
| Traza por causa, campo aditivo sobre `aplicacion/causas_raiz.py` | Guarda por qué avisa cada causa: regla, celdas, valor esperado contra observado y umbral aplicado | En la API y en la planilla de medición | El economista juzga cada causa sin abrir el código |
| `scripts/inyector_fallas.py` | Lee la taxonomía (YAML) y produce copias ficticias con fallas, con semilla; lo opera un tercero | El libro inyectado y su clave sellada | Las fallas se reproducen con la misma semilla |
| Metamórficas en la CI | Renombra hojas, inserta filas vacías, reordena partidas y cambia la escala de moneda | Pruebas | Salen las mismas causas en todos los casos |
| `aplicacion/sensibilidad_umbrales.py` | Barre los umbrales VR1 a VR8 en ±50 % | Tabla de los umbrales que cambian el veredicto | Se publica; no se calibra nada |
| Tasa de «libro no interpretable» | Cuenta los rechazos del lector, con su motivo | Conteo por motivo | Aparece en el capítulo de resultados |

### Fase 2 (meses 2 y 3): congelamiento

- Etiqueta de git más el sha256 de las reglas, los umbrales, la taxonomía y el criterio de fracaso.
- Bitácora obligatoria: todo cambio de reglas posterior se anota con fecha y motivo, y se reporta en la tesis.

### Fase 3 (meses 4 a 8): medición

- El ingeniero y los 3 economistas marcan **a ciegas** el lote nuevo (real, más el sintético del tercero).
- Primero se mide el acuerdo entre los economistas y después la matriz de confusión **por causa**, con intervalos de
  Wilson.
- Se cronometran los minutos de revisión por libro, que son el costo de los falsos positivos.
- La IA puede actuar como segundo anotador ciego, nunca como verdad.
- **Plan B sin ingeniero:** juzgan los economistas, con kappa entre ellos. La afirmación baja a «concordancia con
  revisores del dominio» y se declara como límite.

### Fase 4 (meses 9 a 12): redacción

- Resultados en 3 capas: oráculo, inyección y juicio experto.
- Los resultados negativos se declaran como límite. **No se arregla `core/` a escondidas.**
- La comparación con el procedimiento manual va como caso ilustrativo.

## Puntos ciegos que hay que vigilar

- **Errores de criterio de obra** (rendimientos, depreciación, toneladas): ni Panko ni LibreOffice los ven. Solo el
  experto, con una lista ciega.
- **Falsos negativos fuera de la taxonomía:** nadie mide lo que las reglas no pueden ver. Se declara.
- **Validez de constructo:** un libro inyectado no es un libro real, y un libro de edificación no es vial.
- **Unidad de análisis:** la causa o la celda, no el libro, para tener más casos.
- **Versionarlo todo:** reglas, LibreOffice, configuración regional y coma decimal.

## Primer paso

Esta semana, conseguir el **compromiso escrito del ingeniero de costos externo**, con las fechas de marca ciega. Sin
eso no hay verdad independiente, y todo lo demás solo mide consistencia.

## Estado (2026-11-23)

Ya está hecho:
- la agrupación por causa raíz: `aplicacion/causas_raiz.py`, en la API y en la pantalla, con «Reglas que no aplicaron»
  aparte;
- la herramienta de marca experta: `scripts/medir_auditoria_libro.py`, que mide por causa;
- el libro ficticio con 12 errores, como banco de ensayo.

Falta:
- todo lo de la Fase 0, que depende de personas;
- los módulos de la Fase 1.
