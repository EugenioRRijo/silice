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

## Primeros resultados de la Fase 1 (2026-11-23, con datos ficticios)

| Hallazgo | Qué se hizo |
|---|---|
| El inyector puso un precio negativo y **Sílice rechazó el libro entero** («no se puede recalcular»), sin dar ni un hallazgo | Corregido (`fusion/proceso.py`): la partida entra con su monto guardado, F1 informa un ERROR con el dato que falla y se audita el resto. El FCAS global inválido sigue rechazando el libro, porque sin él no se interpreta nada |
| Una cifra con espacio de miles («9 999,90») **partía una misma causa en dos** | Corregido en `aplicacion/causas_raiz.py` |
| `Constante.supuesto_declarado` (umbrales viales) **solo reconoce 4 de los 8 supuestos**: compara el texto exacto y otros 4 llevan una nota pegada | Pendiente. Hoy no lo usa ningún código del producto; la herramienta de sensibilidad ya compara por contenido |
| Escalar los precios por k **no se puede probar sin recalcular el libro**: Sílice lee los valores que guardó Excel | Queda para cuando esté el oráculo de LibreOffice |
| Primer ensayo de detección: **7 de 12 fallas inyectadas**, solo por celda (58,3 %). Se escaparon un error de escala, dos rangos recortados, una fórmula borrada y un signo | Varias no se pueden detectar porque **el libro inyectado no se recalculó**: Excel siempre guarda valores recalculados. La medición válida es **inyectar → recalcular con LibreOffice → auditar** |

Las pruebas metamórficas que sí se cumplen hoy: cambiar el nombre del archivo, mover una hoja de lugar y auditar dos veces
dan las mismas causas.

## Estado (2026-11-23)

Ya está hecho:
- la agrupación por causa raíz: `aplicacion/causas_raiz.py`, en la API y en la pantalla, con «Reglas que no aplicaron»
  aparte;
- la herramienta de marca experta: `scripts/medir_auditoria_libro.py`, que mide por causa;
- el libro ficticio con 12 errores, como banco de ensayo.

Falta:
- todo lo de la Fase 0, que depende de personas;
- los módulos de la Fase 1.

## Segunda medición (2026-11-24): con LibreOffice y una falla por vez

LibreOffice 26.8.3 quedó instalado como oráculo: es gratuito y cualquiera puede repetir la corrida. Excel queda
como comparación eventual.

| Medición | Resultado |
|---|---|
| Oráculo sobre el libro limpio construido | **0 discrepancias en 188 fórmulas**: LibreOffice coincide con los valores guardados |
| Oráculo sobre el libro ficticio de 12 errores | 15 discrepancias en 189 fórmulas. Las raíces son P5 (valor a dedo, que Sílice marca con F1, L3 y L9), F7 (L3) y la cadena #REF! de RESUMEN (L5). Las demás son arrastres de P5 |
| 12 fallas juntas, inyectadas, recalculadas y auditadas, contando solo la celda exacta | 3 de 12. El 7 de 12 anterior estaba **inflado**: sin recalcular, el valor viejo deja la falla a la vista |
| **12 fallas una por vez** (pruebas de mutación: detectada si la auditoría da un hallazgo que el libro limpio no daba) | **5 de 12 (41,7 %)**, por debajo del umbral de fracaso del 50 % |

Cómo se mide: `scripts/medir_inyeccion.py --una-por-vez`. Cada falla se inyecta sola, el libro se recalcula con
LibreOffice y los valores recalculados se trasplantan al libro original (`aplicacion/trasplante_valores.py`, que no
toca nada más del archivo). Después se audita y se compara con el libro limpio, pasado por la misma cadena.

**Las 7 fallas escapadas**, con la taxonomía de plantilla (no es la del tercero) y el libro de desarrollo:

| Falla | Qué pasó | Lectura |
|---|---|---|
| #9 fórmula borrada en APU-01!C10, que queda con su mismo valor | Ningún valor cambia | Casi equivalente: solo una regla de «precio escrito a mano en vez de buscarlo en la lista» la vería. Es justo el «valor a dedo» que preocupa a Eugenio |
| #4 signo en APU-01!A25, el número de ítem | No afecta ningún monto | Equivalente: el inyector debería evitar las celdas que no son montos |
| #3 `SUM(G32:G35)` recortado en el costo directo de APU-02 | L4 solo revisa sumas escritas con «+» | **Hueco de regla** |
| #1 y #7 BUSCARV desplazado en APU-02 (trae el precio de otro insumo) | El APU queda coherente consigo mismo | **Hueco de regla**: comparar el precio de cada renglón con el de la lista para su código |
| #5 y #6 `SUMPRODUCT` recortado en RESUMEN!B4 y B6 | L9 no lo ve | **Hueco de regla, por investigar** |

Cambiar las reglas por estos resultados es un cambio de producto y lo decide Eugenio. Estas fallas salieron del libro
de desarrollo, no del lote de prueba, así que corregirlas antes de congelar no contamina la medición final. Si se
corrigen, se anota en la bitácora como cambio previo al congelamiento.
