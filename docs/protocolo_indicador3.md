# Protocolo de medición del indicador 3 — tiempo de elaboración frente al método manual

| Campo | Valor |
|---|---|
| Indicador | 3, «Reducción del tiempo de elaboración» ([metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis)) |
| Objetivo al que sirve | OE1 (registro de tiempos de elaboración) y OE6 (evaluación), según [tesis/esqueleto_tesis.md](tesis/esqueleto_tesis.md) |
| Escrito en | fase C4 del cierre, 2026‑09‑28 (spec de cierre §5, fila C4) |
| Se ejecuta en | fase Med del cierre ([PLAN_CIERRE.md](../PLAN_CIERRE.md)), antes de congelar |
| Versión del protocolo | el commit que contiene este archivo; se anota en cada hoja de registro |

Este protocolo está escrito **antes de medir** y para que lo ejecute un tercero sin consultar al
autor. Lo que aquí se declara no se cambia después de la primera sesión: si una sesión revela un
defecto del protocolo, se registra en la bitácora de Med y se aplica solo a sesiones futuras, nunca
a las ya medidas (spec de cierre §5, fila Med).

**Naturaleza de los datos.** La tarea usa el caso didáctico de la clínica, un ejercicio académico
ficticio ([NORMAS.md §1](../NORMAS.md#1-qué-es-este-proyecto)). Lo que se mide es el tiempo de las
personas, no la exactitud del caso.

## 1. Qué se mide y qué no

Las Bases del anteproyecto (`docs/fuentes/Bases_Anteproyecto_BIM5D_APU.docx`, §8.3, técnicas e
instrumentos) fijan la técnica: «observación estructurada: registro de tiempos de elaboración en el
procedimiento manual y en el automatizado». Este protocolo la hace operativa.

**Se mide** cuánto tarda una persona en completar **la misma tarea de referencia** (sección 2)
por el método manual (sección 3) y con el sistema (sección 4). Para cada participante *i*:

- `t_manual(i)` y `t_sistema(i)`, en minutos con dos decimales;
- la reducción relativa `r(i) = 1 − t_sistema(i) / t_manual(i)`.

**El indicador 3 es la mediana de `r(i)`**, reportada con su mínimo, su máximo, n, el perfil de
los participantes y el commit probado.

**No se mide aquí:**

- el tiempo de máquina del recálculo masivo (RNF‑03, 1,17 s con 100 partidas): es un requisito
  distinto, verificado por `scripts/medir_rnf03.py`, que el capítulo V cita como complemento;
- la capacidad de aprendizaje de la interfaz (RNF‑10, caso CP‑07 del
  [guion de prueba](guion_prueba_arenia.md));
- la comprensión del informe de auditoría (RNF‑04, [protocolo_rnf04.md](protocolo_rnf04.md)).

**Elecciones conservadoras** (todas favorecen al método manual; la reducción medida es, por eso,
una cota inferior de la real en la tarea descrita):

1. El participante manual recibe las **fórmulas del cómputo** ya escritas (ficha M1): no las
   deriva del plano.
2. Recibe los **precios unitarios ya calculados** (tabla M2): no arma ningún APU.
3. El tiempo del sistema **incluye** la auditoría R1–R7, que el sistema hace siempre y el
   participante manual no hace.
4. El arranque de la hoja de cálculo y de la aplicación **no** cuenta en ninguna condición.

## 2. La tarea de referencia T3

**Enunciado.** Elaborar el presupuesto de la obra de drenaje descrita en la ficha M1 de la variante
asignada: el cómputo de sus seis renglones, el monto de cada partida con el precio unitario de la
tabla M2, el total y una curva de inversión de una partida por día que cierre exactamente en el
total.

**Materiales comunes a las dos condiciones** (se imprimen y se entregan en papel):

- **M1 — ficha de la variante** (V1 o V2; la variante P es solo de práctica): dimensiones y
  fórmulas, abajo.
- **M2 — tabla de partidas del catálogo**, abajo.

**M1. Fichas de las variantes.** Tanquillas de concreto (grupo `T-01`) y una zanja con tubería de
PVC de 4" (`Z-01`):

| Dato | Símbolo | V1 | V2 | P (práctica) |
|---|---|---|---|---|
| Número de tanquillas | n | 4 | 3 | 2 |
| Ancho exterior de la tanquilla (m) | a | 0,80 | 1,00 | 0,60 |
| Altura de la tanquilla (m) | h | 0,80 | 0,90 | 0,60 |
| Espesor de pared (m) | e | 0,10 | 0,15 | 0,10 |
| Sobreancho de excavación por lado (m) | s | 0,10 | 0,10 | 0,10 |
| Espesor de fondo bajo la tanquilla (m) | f | 0,10 | 0,10 | 0,10 |
| Longitud de la zanja (m) | L | 24,00 | 30,00 | 10,00 |
| Ancho de la zanja (m) | b | 0,40 | 0,40 | 0,40 |
| Profundidad de la zanja (m) | p | 0,80 | 0,90 | 0,60 |
| Diámetro de la tubería (m; 4") | D | 0,1016 | 0,1016 | 0,1016 |
| Desperdicio de tubería | d | 0,05 | 0,05 | 0,05 |

Fórmulas del cómputo (las mismas de `adapters/civil/reglas.py`; en la ficha impresa van tal cual):

| Renglón | Partida | Unidad | Fórmula |
|---|---|---|---|
| 1 | LB‑04‑CON | m3 | concreto = n · (a² − (a − 2e)²) · h |
| 2 | LB‑03‑ENC | m2 | encofrado = n · (4·a·h + 4·(a − 2e)·h) |
| 3 | LB‑01‑EXC | m3 | excavación de fosos = n · (a + 2s)² · (h + f) |
| 4 | LB‑01‑EXC | m3 | excavación de zanja = L · b · p |
| 5 | LB‑02‑TUB | m | tubería = L · (1 + d) |
| 6 | LB‑05‑REL | m3 | relleno = (excavación de fosos + excavación de zanja) − concreto − tubería · 0,7854 · D² |

La tubería se valora por metro con el precio unitario de LB‑02‑TUB tal como figura en M2. La
curva: una partida por día, cada una al 100 % en su día, en el orden que el participante elija.

**M2. Partidas del catálogo** (precios del caso didáctico al 28/04/2026, los de
[NORMAS.md §4](../NORMAS.md#4-especificación-del-cálculo-y-línea-base)):

| Código | Descripción | Unidad del APU | Precio unitario (USD) |
|---|---|---|---|
| LB‑01‑EXC | Excavación en tierra para zanja de tubería y fosos de tanquillas | m3 | 8,60 |
| LB‑02‑TUB | Suministro e instalación de tubería PVC de 4 pulgadas | pieza | 10,19 |
| LB‑03‑ENC | Encofrado recto de madera para paredes de tanquillas | m2 | 33,24 |
| LB‑04‑CON | Vaciado de concreto en paredes de tanquillas | m3 | 242,64 |
| LB‑05‑REL | Relleno compactado con material granular | m3 | 52,58 |

**Por qué dos variantes.** Cada participante ejecuta las dos condiciones. Si las dos usaran los
mismos números, la segunda condición heredaría las cantidades y el total de la primera. V1 y V2
tienen la misma estructura (seis renglones, las mismas fórmulas, las mismas partidas) y distintas
dimensiones; la variante se contrabalancea con el orden (sección 7).

**Clave de respuesta** (para el observador; **nunca** se entrega al participante). Se obtuvo
ejecutando la condición sistema de la sección 4 sobre el código de `ceb6b8e` (`main`), con los
precios exactos del catálogo; los montos se presentan redondeados a dos decimales:

| Renglón | V1 cantidad | V1 monto (USD) | V2 cantidad | V2 monto (USD) |
|---|---|---|---|---|
| 1 concreto (m3) | 0,896 | 217,41 | 1,377 | 334,11 |
| 2 encofrado (m2) | 17,92 | 595,62 | 18,36 | 610,25 |
| 3 + 4 excavación (m3) | 3,60 + 7,68 = 11,28 | 97,01 | 4,32 + 10,80 = 15,12 | 130,04 |
| 5 tubería (m) | 25,20 | 256,87 | 31,50 | 321,09 |
| 6 relleno (m3) | 10,1797 | 535,21 | 13,4876 | 709,13 |
| **Total** | | **1 702,13** | | **2 104,62** |

La variante P da 509,35 USD. Los renglones 1 y 2 de V1 coinciden con las cantidades corregidas de
la línea base (0,224 m3 y 4,48 m2 por tanquilla; [linea_base.md §2](linea_base.md)), lo que
contrasta la clave con una fuente independiente del sistema. Con los precios de M2, que están
redondeados a dos decimales, los totales salen 1 702,11 y 2 104,60 USD: por eso la tolerancia de
la sección 10.

## 3. Definición operacional de «manual»

El **método manual** es el procedimiento tradicional que describe
[linea_base.md](linea_base.md) (croquis → cómputo en hoja de cálculo → APU → presupuesto → plan de
trabajo), acotado a la tarea T3:

- **Herramienta:** una hoja de cálculo de escritorio (Microsoft Excel o LibreOffice Calc; la que el
  participante use de costumbre, anotada en el registro), en el equipo de la sesión, con un libro
  **en blanco** ya abierto al empezar. Se permiten calculadora y papel.
- **No se permite:** plantillas, macros o libros propios traídos por el participante; internet;
  el sistema de esta tesis o cualquier otro software de presupuestos (Lulowin, MaPreX u otros).
- **Entregable:** un libro guardado como `data/i3/<código>_manual.xlsx` con (1) el cómputo de los
  seis renglones de M1, (2) el monto de cada partida y el total, y (3) la curva de inversión con
  su acumulado. La forma del libro (hojas, formato) es libre.
- **Fin del tiempo:** el participante guardó el libro y dijo «terminé».

## 4. Definición operacional de «con el sistema»

El **método con el sistema** es la aplicación de esta tesis en el commit probado, tal como la
describe el [manual de usuario §3.1](manual_usuario.md) (UC‑01, pantalla *Elaborar un
presupuesto*):

- **Herramienta:** la aplicación ya arrancada sobre la base del participante, abierta en
  **Inicio**; un editor de texto plano (Bloc de notas o equivalente) con la plantilla
  `data/i3/<código>_plantilla.csv` abierta. La plantilla se prepara con este contenido exacto
  (cabecera y los dos renglones con su `id` y su `tipo`; el resto de las celdas vacías):

  ```
  id,tipo,a,h,e,n,sobreancho,espesor_fondo,longitud,ancho,profundidad,diametro,desperdicio,especificaciones
  T-01,tanquilla,,,,,,,,,,,,
  Z-01,zanja,,,,,,,,,,,,
  ```

- **Material de apoyo M3 (solo en esta condición):** una hoja impresa con los pasos del manual de
  usuario §3.1 y la correspondencia de columnas de la plantilla con los símbolos de M1 (`a`, `h`,
  `e`, `n`, `sobreancho` = s, `espesor_fondo` = f; `longitud` = L, `ancho` = b,
  `profundidad` = p, `diametro` = D, `desperdicio` = d), con la advertencia de que el separador
  decimal es el **punto**. El formato completo está en `data/samples/civil/README.md`.
- **Pasos que el participante ejecuta cronometrados:** completar la plantilla con los datos de M1
  y guardarla; en la aplicación, abrir *Elaborar un presupuesto* (menú superior, sección *Trabajo*),
  elegir el dominio `civil`,
  asociar en la barra lateral cada partida a su código de M2 (concreto, encofrado, excavación,
  tubería y, marcando *Incluir relleno (balance R5)*, el relleno), subir la plantilla, pulsar
  *Extraer cómputo*, *Elaborar presupuesto* y *Exportar a Excel*.
- **Entregable:** el libro descargado `presupuesto_P-001*.xlsx` (el nombre lleva el «Código del
  presupuesto» de la barra lateral, `P-001` por defecto, que al participante no se le pide cambiar;
  no el código del participante), con sus cuatro hojas
  (*Presupuesto*, *APU*, *Curva* y *Auditoria*).
- **Fin del tiempo:** el archivo está en la carpeta de descargas y el participante dijo «terminé».
- **La interfaz desde la integración final del sprint SF (cambio previo a la primera sesión, sin tocar el
  método, los topes ni la prueba estadística):** el menú de pantallas va **arriba** y bajo él hay una barra
  de herramientas. «Exportar Excel» de esa barra produce el libro de la *Hoja del proyecto*
  (`hoja_<código>.xlsx`), no el entregable: si el participante lo usa, el observador lo anota y el
  entregable sigue siendo el `presupuesto_P-001*.xlsx` de *Exportar a Excel* de *Elaborar un presupuesto*.

## 5. Participantes

**Quiénes.** Personas con formación en ingeniería civil, arquitectura o construcción —estudiantes
de los dos últimos años de la carrera o profesionales— que hayan elaborado **al menos un
presupuesto de obra con APU en una hoja de cálculo** y usen Excel o LibreOffice Calc de costumbre.

**Quiénes no** (cualquiera de estas condiciones excluye):

- el autor de la tesis;
- quien tenga **relación personal** con el autor: familia, pareja, amistad, o dependencia laboral o
  académica directa con él (spec de cierre §5, fila Med);
- quien haya trabajado en el proyecto, visto la aplicación o sus documentos, o conozca el caso de
  la clínica;
- quien haya participado en CP‑07 o en el juicio de expertos de RNF‑04.

Cada participante firma, en su hoja de registro (sección 12), la declaración de que no está en
ninguno de esos casos. Se registra su **perfil**, nunca su nombre: formación, años de experiencia
con presupuestos, hoja de cálculo que usa y cuántos presupuestos con APU ha elaborado (1, 2–5,
más de 5). La participación es voluntaria y puede dejarse en cualquier momento; los datos se
publican sin nombres.

**El observador** prepara, lee las consignas, cronometra y verifica. No es participante. Puede ser
el autor; si lo es, se anota en el registro como amenaza a la validez (sección 13).

## 6. Tamaño de la muestra y su justificación

**n planificado = 8; mínimo para inferencia = 6.**

- **Diseño intrasujeto.** Cada participante hace las dos condiciones: la diferencia se mide dentro
  de la misma persona, y su pericia con la hoja de cálculo, que es la mayor fuente de variación, se
  cancela. Con esto, n pequeños bastan si el efecto es grande y de signo constante.
- **Prueba declarada:** Wilcoxon de rangos con signo, **exacta**, bilateral, α = 0,05, sobre
  `d(i) = t_manual(i) − t_sistema(i)`, con la herramienta y el tratamiento de diferencias nulas y
  empates de la sección 11, punto 3. Su menor valor p posible es 2 / 2ⁿ: con n = 5
  es 0,0625 (nunca significativo), con n = 6 es 0,031 y con n = 8, 0,0078. Por eso **6 es el
  mínimo** que permite concluir y **8** deja margen para que una o dos diferencias no vayan en el
  mismo sentido.
- **Contrabalanceo completo.** Hay cuatro secuencias (sección 7); 8 = dos participantes por
  secuencia.
- **Si no se llega a 6,** el resultado se reporta solo de forma descriptiva (tabla por participante
  y mediana de `r`), declarado como limitación en el capítulo V; no se hace prueba ni se afirma una
  reducción general.

## 7. Orden, variantes y contrabalanceo

Dos factores se contrabalancean a la vez: el **orden** de las condiciones (manual primero o sistema
primero) y la **variante** que toca a cada condición (V1 o V2). Resultan cuatro secuencias:

| Secuencia | Primera condición | Segunda condición |
|---|---|---|
| S1 | manual con V1 | sistema con V2 |
| S2 | manual con V2 | sistema con V1 |
| S3 | sistema con V1 | manual con V2 |
| S4 | sistema con V2 | manual con V1 |

**Asignación fija, declarada antes de la primera sesión:** el participante *k*‑ésimo en llegar
(código `P01`, `P02`, …) recibe la secuencia `S((k − 1) mod 4 + 1)`: P01 → S1, P02 → S2, P03 → S3,
P04 → S4, P05 → S1, P06 → S2, P07 → S3, P08 → S4. El observador no elige.

**Práctica con el sistema.** Antes de su condición sistema, cada participante hace una práctica con
la variante P y el material M3, en la que el observador sí contesta preguntas (máximo 15 min; su
tiempo se registra aparte y no cuenta). No hay práctica para el método manual: la hoja de cálculo
es la herramienta habitual del participante (criterio de inclusión de la sección 5). La práctica
ocurre antes de la condición sistema en las cuatro secuencias; su efecto sobre la condición manual
que la sigue en S3 y S4 lo recoge el contrabalanceo. Al terminar la práctica, y antes de la
condición sistema, el observador **retira de la carpeta de descargas** el libro de la práctica
(`presupuesto_P-001.xlsx`, a una carpeta aparte): la condición sistema descarga un libro con el mismo
nombre, y el navegador lo renombraría («(1)»), confundiendo cuál es el entregable.

**Entre condiciones:** pausa de 10 minutos. Al participante **no** se le dice si su primer
entregable fue correcto hasta terminar la segunda condición.

## 8. Preparación (el observador, antes de cada sesión)

1. **Copia desechable** del repositorio, como en la sección 4 del
   [guion de prueba](guion_prueba_arenia.md), nunca la copia de trabajo:
   `git worktree add ../tesis-indicador3 <commit>` y, dentro de ella,
   `uv sync --extra ui --extra ml` (los mismos extras que CP‑07). El `<commit>` es un commit de `main` con su
   corrida de CI en verde; se anotan el commit (`git log -1 --oneline`) y el enlace a esa corrida.
   Todas las sesiones usan **el mismo commit**; si hubiera que cambiarlo, se registra y se
   declara.
2. **Clave al día.** Una sola vez, antes de la primera sesión: el observador ejecuta él mismo la
   condición sistema (sección 4) con V1 y con V2 y compara los totales del Excel con la clave de la
   sección 2. Si difieren, se detiene: la clave se rehace sobre el commit probado y se anota por
   qué cambió.
3. **Base del participante:** `uv run python scripts/seed.py --db data/i3/<código>.db` (la línea
   base: cinco partidas y la lista del 28/04/2026). Nunca sin `--db`: sin esa opción escribe en
   `data/apu.db`.
4. **Aplicación:** en bash, `ARENIA_CASO=data/i3/<código>.db uv run python -m streamlit run ui/app.py`;
   en PowerShell, `$env:ARENIA_CASO = "data/i3/<código>.db"; uv run python -m streamlit run ui/app.py`.
   Comprobar que abre en **Inicio** y que la barra lateral, bajo **Caso abierto**, nombra esa base
   con 5 partidas. Sin modo entrega (`ARENIA_MODO_ENTREGA` sin definir).
5. **Plantillas:** `data/i3/<código>_plantilla.csv` (contenido de la sección 4) y
   `data/i3/<código>_practica.csv` (la misma plantilla, para la práctica con P).
6. **Hoja de cálculo** abierta con un libro en blanco; **carpeta de descargas** vacía (o su
   contenido anotado).
7. **Impresos:** M1 de la variante que toca a cada condición, M1 de P, M2, M3, la consigna y la
   hoja de registro. Cronómetro con precisión de segundos.

## 9. La sesión

**Consigna del método manual** (se lee tal cual, una sola vez):

> «Con estos materiales, elabore en la hoja de cálculo el presupuesto de esta obra: el cómputo de
> cada renglón, el monto de cada partida con el precio unitario de la tabla, el total y una curva
> de inversión de una partida por día. Trabaje a su ritmo habitual; el formato del libro es libre.
> Cuando termine, guarde el libro con el nombre que le indico y dígame "terminé". Yo solo tomo el
> tiempo.»

**Consigna con el sistema** (se lee tal cual, una sola vez):

> «Con estos materiales y la aplicación, obtenga el presupuesto de esta obra en Excel: complete la
> plantilla con los datos de la ficha, extraiga el cómputo, elabore el presupuesto y descárguelo.
> Cuando el archivo esté descargado, dígame "terminé". Yo solo tomo el tiempo.»

**Reglas del observador durante el tiempo cronometrado:**

1. El cronómetro arranca al terminar de leer la consigna y se detiene con «terminé» y el
   entregable guardado (sección 3 o 4).
2. Solo contesta preguntas sobre **lo que dice un impreso** (un número que no se lee). A cualquier
   otra pregunta responde, siempre igual: «Haga lo que haría si yo no estuviera». Anota cada
   pregunta con su minuto.
3. Anota las interrupciones ajenas al participante (fallo del equipo, ruido) con su duración; ese
   tiempo se descuenta.
4. **Tope de tiempo:** 90 minutos en la condición manual y 45 con el sistema. Al llegar al tope la
   condición se detiene, el tiempo se registra como el tope y se marca **censurado**.
5. Si la aplicación muestra una traza de error o deja de responder, se anota como defecto con la
   pantalla y el texto visible; la condición se detiene y se marca **interrumpida por defecto**
   (no se reinicia).

## 10. Verificación del entregable

Al terminar cada condición, sin comentarlo con el participante, el observador compara el
entregable con la clave de la sección 2:

- **Cantidades:** cada uno de los seis renglones dentro de ± 1 % de la clave (si el participante
  sumó los renglones 3 y 4, se compara la excavación total).
- **Total:** dentro de ± 0,5 % de la clave.
- **Curva:** una partida por período y acumulado final igual al total del propio entregable, con
  una diferencia de a lo sumo 0,01 USD.

Un entregable que cumple las tres es **correcto**; si no, **incorrecto**, y se anota qué falló. En
la condición sistema la curva y el total los produce la aplicación: la comprobación recae sobre las
cantidades, que dependen de lo que el participante escribió en la plantilla.

## 11. Análisis, declarado antes de medir

1. **Análisis principal** sobre los participantes con los **dos** entregables correctos: tabla por
   participante (`t_manual`, `t_sistema`, `r`), mediana de `r` con su mínimo y su máximo, y
   medianas de `t_manual` y `t_sistema`.
2. **Censurados e interrumpidos.** Una condición censurada (tope alcanzado, sección 9, regla 4) o
   interrumpida por defecto (regla 5) no tiene entregable terminado: cuenta como **incorrecta** y
   su participante **sale del análisis principal**. Si la censurada es la condición manual, la
   exclusión quita una de las reducciones más grandes y juega en contra del sistema
   (conservadora). Si es la condición sistema, la exclusión lo favorecería; por eso el análisis de
   sensibilidad del punto 5 los vuelve a incluir. Cada exclusión se reporta con su participante,
   su condición y su motivo.
3. **Prueba:** Wilcoxon de rangos con signo, bilateral, α = 0,05, sobre
   `d(i) = t_manual(i) − t_sistema(i)` del análisis principal, calculada con SciPy 1.18.1 (la
   versión fijada en `uv.lock`; se instala con el extra `ml`) así:

   ```
   scipy.stats.wilcoxon(d, alternative="two-sided", zero_method="wilcox",
                        method=scipy.stats.PermutationMethod())
   ```

   - **Diferencias nulas** (`d(i) = 0`, iguales a la centésima de minuto): `zero_method="wilcox"`
     las descarta, y el n de la prueba es el número de diferencias no nulas. Si quedan menos de 6,
     no hay prueba (sección 6).
   - **Empates** entre los `|d(i)|`: reciben el rango promedio. `PermutationMethod()` recorre las
     2ⁿ asignaciones de signo (con n ≤ 8 son a lo sumo 256, menos que sus 9 999 remuestreos por
     defecto, así que la enumeración es completa y p es exacta también con empates). Sin empates da
     el mismo p que `method="exact"`: con n = 8, siete diferencias positivas y una negativa de rango
     1, las dos dan 0,015625 (comprobado con SciPy 1.18.1 al escribir este protocolo).
   - Se reportan el estadístico, p, el n de la prueba y cuántas diferencias nulas y empates hubo.
4. **Enunciado del resultado:** se afirma que el sistema **reduce** el tiempo de elaboración de la
   tarea T3 si y solo si, en el análisis principal, la mediana de `r` es mayor que 0 **y** la
   prueba da p < 0,05, **y** el análisis de sensibilidad (punto 5) no da una mediana de `r` menor
   o igual que 0. En cualquier otro caso se informa el dato sin afirmar una reducción. No se fija
   de antemano un porcentaje mínimo: las Bases nombran el indicador («reducción del tiempo de
   elaboración», §8.3 y §8.5, criterios de validación) sin meta numérica, y este protocolo no la
   inventa.
5. **Análisis de sensibilidad** (descriptivo, sin prueba): todos los participantes que llegaron al
   final de las dos condiciones, correctos o no, censurados o no. Un censurado entra con el tope
   como tiempo; una condición interrumpida por defecto de la aplicación entra, si es la del
   sistema, con el tope de 45 minutos (el defecto juega en contra del sistema). Se reporta la
   mediana de `r` con su mínimo y su máximo.
6. **Análisis secundarios** (descriptivos, sin prueba): la mediana de `r` por orden (S1 y S2 contra
   S3 y S4) y por variante, para ver efectos de orden o de variante; la mediana de
   `r_con_práctica = 1 − (t_sistema + t_práctica) / t_manual`, que carga al sistema el tiempo de su
   práctica (sección 13); el número de entregables incorrectos por condición; las preguntas al
   observador por condición.
7. **Todo participante que empezó se reporta**, también los excluidos del análisis principal y el
   motivo.

## 12. Plantilla de registro

**Hoja por participante** (una por persona; se transcribe sin nombres a la bitácora de Med):

| Campo | Valor |
|---|---|
| Código del participante (`P01`…) | |
| Secuencia (S1–S4) y variantes (manual: V_; sistema: V_) | |
| Perfil: formación · años con presupuestos · hoja de cálculo · presupuestos con APU elaborados (1, 2–5, > 5) | |
| Declaración: «No soy el autor ni tengo relación personal con él; no he visto la aplicación, sus documentos ni el caso; no participé en CP‑07 ni en el juicio de RNF‑04» (firma) | |
| Fecha y hora de inicio | |
| Commit probado (`git log -1 --oneline` en la copia desechable) y corrida de CI en verde de ese commit | |
| Versión del protocolo (commit que contiene este archivo) | |
| Sistema operativo, hoja de cálculo (nombre y versión) y navegador | |
| Observador (¿es el autor? sí/no) | |
| Práctica con P: duración (min) · ¿entregable correcto? | |
| **Condición 1** — método · variante · `t` (min) · ¿censurado? · ¿interrumpida por defecto? | |
| Condición 1 — preguntas al observador (minuto · pregunta) · interrupciones descontadas (min) | |
| Condición 1 — verificación: renglones 1–6 · total · curva · correcto/incorrecto | |
| **Condición 2** — método · variante · `t` (min) · ¿censurado? · ¿interrumpida por defecto? | |
| Condición 2 — preguntas al observador · interrupciones descontadas (min) | |
| Condición 2 — verificación: renglones 1–6 · total · curva · correcto/incorrecto | |
| `r = 1 − t_sistema / t_manual` | |
| Observaciones (incluidos defectos de la aplicación y comentarios espontáneos) | |

**Hoja consolidada** (una fila por participante, más el resumen):

| Participante | Secuencia | Perfil (resumen) | `t_manual` | `t_sistema` | `r` | `t_práctica` | `r_con_práctica` | Ambos correctos | Commit |
|---|---|---|---|---|---|---|---|---|---|
| P01 | S1 | | | | | | | | |
| … | | | | | | | | | |
| **Resumen** | n = | | mediana = | mediana = | mediana (mín–máx) = | mediana = | mediana (mín–máx) = | pares válidos = | |

`t_práctica` es la duración de la práctica con P de la hoja por participante, y
`r_con_práctica = 1 − (t_sistema + t_práctica) / t_manual` (sección 11, punto 6).

Resultado de la prueba de Wilcoxon: estadístico, p, n de pares. Enunciado del resultado según la
regla de la sección 11, punto 4; mediana de `r` del análisis de
sensibilidad (punto 5) y de `r_con_práctica` (punto 6).

## 13. Amenazas a la validez y cómo se controlan

| Amenaza | Control |
|---|---|
| Aprendizaje de la tarea entre condiciones | Dos variantes contrabalanceadas con el orden (sección 7); sin retroalimentación entre condiciones |
| Diferencias de pericia entre personas | Diseño intrasujeto: cada persona es su propio control |
| Tarea hecha a la medida del sistema | Las cuatro elecciones conservadoras de la sección 1 favorecen al método manual |
| Práctica solo con el sistema (hasta 15 min con la variante P, con preguntas permitidas), que el método manual no tiene | Justificada en la sección 7: la hoja de cálculo es la herramienta habitual del participante y el sistema no. Su tiempo se registra; no entra en `t_sistema`, pero el análisis secundario `r_con_práctica` (sección 11, punto 6) lo carga al sistema y se reporta junto al resultado. La variante P no es ninguna de las medidas |
| Exclusión de censurados e interrumpidos | Regla de la sección 11, punto 2, y análisis de sensibilidad (punto 5), que los reincluye en contra del sistema |
| Sesgo del observador | Consignas literales, respuesta fija a las preguntas, asignación de secuencias fija, clave comprobada antes de la primera sesión; si el observador es el autor, se declara |
| Relación con el autor | Criterio de exclusión y declaración firmada (sección 5) |
| Validez externa | Un caso didáctico y una tarea acotada: el resultado vale para T3 y así se cita, no para la elaboración de cualquier presupuesto |
| Versión del software | Un solo commit probado para todas las sesiones, con su corrida de CI |

## 14. Dónde se registra el resultado

- Las hojas transcritas y el enunciado del resultado: la bitácora de la fase Med.
- La cifra citable del indicador 3, con n, perfil, fecha y commit: la tabla de la sección 5 de
  [tesis/plan_redaccion.md](tesis/plan_redaccion.md#5-cifras-citables-y-cómo-regenerarlas), de
  donde la toma el capítulo V.
