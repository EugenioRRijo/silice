# Tarjetas de la prueba de comprensión de las 6 alertas (A1 a A6)

- **Fecha:** 2026-11-28. Tarea T8 del [plan de cierre de la rama](../planes/2026-11-28-plan-cierre-rama-front.md).
- **Para qué:** son las tarjetas que se muestran, una por vez, en la prueba de comprensión de las alertas del
  [guion de la prueba con usuarios](2026-11-23-guion-prueba-con-usuarios.md#prueba-de-comprensión-de-las-alertas-2026-11-24).
- **De dónde sale cada texto:** de la pantalla «Auditar un libro» de la rama `feature/front-b1` (commit `4d04e8d3`), que
  muestra los textos del servidor tal cual. La tabla del §4 da el `archivo:línea` de cada texto.
- **Sin la línea «Qué hacer»** (decisión D3 de la [ficha de B2](../especificaciones/2026-11-26-cara-papel-y-resaltador/b2/ficha-b2.md)).
  Si la tarjeta trajera la guía, la pregunta «¿Qué haría ahora?» mediría lectura y no comprensión. En la pantalla es un
  botón plegado, y en la tarjeta no se imprime.
- **Datos:** todos son ficticios: el libro, los códigos, las celdas, los precios y las tasas del BCV. Ninguno sale de un
  libro de la empresa (NORMAS §1).

> **Antes de imprimir.** El guion pide copiar las tarjetas de la pantalla real con la versión congelada `medicion-v1`.
> Este documento es el texto de referencia para hacer esa copia. Se abre el caso de demostración con `medicion-v1` y se
> coteja cada tarjeta, letra por letra, con lo que muestra la pantalla. Si algo difiere, manda la pantalla: se corrige la
> tarjeta y se anota la fecha y el motivo antes de la primera sesión (riesgo R1 de la ficha de B2).

## 1. El caso de demostración (ficticio)

Con estos datos, Sílice produce los textos de las tarjetas. Si el caso de demostración de `medicion-v1` usa otros datos,
las cifras de las tarjetas se copian de su pantalla.

| Dato | Valor ficticio |
|---|---|
| Libro | «Presupuesto cliente A.xlsx», en dólares |
| Fecha del libro / fecha de la revisión | 2026-10-01 / 2026-11-24 |
| Tasa del BCV cargada en la instalación (ficticia) | 50 al 2026-10-01 y 55 al 2026-11-24 |
| Umbral de las alertas de precio | 5,00 % (el valor por omisión, `fusion/alertas.py:61`) |
| Insumo `MT-04` | 12,00 USD en INSUMOS!E12; su FUENTE dice «POR COTIZAR» |
| Insumo `MT-08` | 18,00 USD, con fuente; la instalación tiene un precio propio de 15,00 USD del 2026-10-15 |
| APU-02 (partida 2) | El costo directo de G36 es `=SUM(G32:G34)` y deja fuera G35 (transporte y disposición, 10 USD/u); CD guardado 90 USD/u, suma de componentes 100 USD/u, administración 0,15, utilidad 0,1, cantidad 100 |
| RESUMEN | B4 y B6 tienen fórmulas con #REF! |
| PRESUPUESTO, columna REND. | Las partidas 1 a 6 (F10 a F15) leen la fila 14 de su APU (valor 0), y el rendimiento está en la fila 19 (valor 120) |

Con este caso, la pantalla muestra:
- **«Alertas de precio (4)»**: Sin fuente de MT-04, Base de la empresa de MT-08, USD-Bs de MT-04 y USD-Bs de MT-08.
- **«Por causa raíz (1)»**: la causa L1 con sus 6 casos.
- **«Uno por uno (2)»**: L4 y L5.

La tarjeta A3 muestra la línea USD-Bs de MT-08. La de MT-04 también aparece en la pantalla, porque una tasa que sube un
10 % mueve igual todos los precios en dólares, pero no tiene tarjeta.

## 2. Cómo se imprime cada tarjeta

- Va una tarjeta por hoja (media carta basta). En el frente se imprime **solo** el recuadro «Lo que se ve en la
  pantalla».
- El rótulo «A1 · Sin fuente» es para quien conduce: va al dorso, en letra pequeña, para ordenar las tarjetas y llenar
  la hoja de registro. La persona no lo ve, porque la pantalla tampoco lo muestra.
- **La gravedad** (A4 a A6) se muestra en la pantalla con un ícono y una palabra. El ícono va antes de la primera línea
  (triángulo relleno de Carbon, `WarningFilled`, en el color de gravedad «Error») y la palabra es «Error». En papel se
  imprime en color, con el ícono. Las alertas de precio (A1 a A3) **no** llevan ícono ni color de gravedad, porque no son
  errores del libro (supuesto S4 de la ficha de B2).
- **Los códigos y las celdas** (`MT-04`, `APU-02!G36`) van en letra monoespaciada, como en la pantalla. Lo que la tarjeta
  pone en **negrita** también va en negrita en la pantalla.
- **La línea de arriba de cada recuadro** es el título de la sección en que aparece la alerta, con su frase de
  introducción. Se imprime porque está en la pantalla (ver la ratificación 1 del §5).
- **No se imprime** el botón «Qué hacer» ni su contenido. La palabra «Impacto», que antecede a la cifra de A4, tampoco se
  imprime: en la pantalla es texto oculto, solo para lectores de pantalla.

## 3. Las tarjetas

En las seis tarjetas se hacen las preguntas del guion, en este orden y sin pistas:

1. «¿Qué le está diciendo?»
2. «¿Qué haría ahora?»

Al terminar las seis se hace la pregunta abierta: «¿Qué alerta le faltó?». Quien conduce no explica nada ni corrige las
respuestas, y las anota en la hoja de registro del guion.

---

### Tarjeta A1 · Sin fuente

**Lo que se ve en la pantalla** (frente):

> *Alertas de precio (4)*
> *No son errores del libro: son precios que conviene confirmar con quien lo hizo.*
>
> **Sin fuente** · `MT-04`
>
> la FUENTE de MT-04 dice «POR COTIZAR»: el precio (INSUMOS!E12) no se puede rastrear

**Preguntas:** «¿Qué le está diciendo?» · «¿Qué haría ahora?»

**Clave para quien conduce** (*propuesta, a ratificar por Eugenio*; no se imprime en la tarjeta). Se anota «sí» si la
persona dice que el precio de ese insumo no tiene de dónde sale, o que no está cotizado, y que por eso no se puede
comprobar. Se anota «a medias» si solo nombra el insumo o la celda, sin decir qué le falta.

---

### Tarjeta A2 · Base de la empresa

**Lo que se ve en la pantalla** (frente):

> *Alertas de precio (4)*
> *No son errores del libro: son precios que conviene confirmar con quien lo hizo.*
>
> **Base de la empresa** · `MT-08`
>
> el libro usa 18,00 USD; precio propio de la instalación 15,00 USD del 2026-10-15: +20,00 %, pasa del umbral de 5,00 %

**Preguntas:** «¿Qué le está diciendo?» · «¿Qué haría ahora?»

**Clave para quien conduce** (*propuesta, a ratificar por Eugenio*). Se anota «sí» si la persona dice que el libro pone
ese insumo más caro (un 20 % más) que el precio que la empresa tiene registrado, y que la diferencia pasa del límite
aceptado. Se anota «a medias» si nota la diferencia pero no sabe con qué se compara.

---

### Tarjeta A3 · USD-Bs

**Lo que se ve en la pantalla** (frente):

> *Alertas de precio (4)*
> *No son errores del libro: son precios que conviene confirmar con quien lo hizo.*
>
> **USD-Bs** · `MT-08`
>
> 900,00 Bs al 2026-10-01 (tasa 50) y 990,00 Bs al 2026-11-24 (tasa 55): +10,00 %, pasa del umbral de 5,00 %

**Preguntas:** «¿Qué le está diciendo?» · «¿Qué haría ahora?»

**Clave para quien conduce** (*propuesta, a ratificar por Eugenio*). Se anota «sí» si la persona dice que el mismo
precio en dólares vale un 10 % más en bolívares entre la fecha del libro y la de la revisión, porque cambió la tasa del
BCV. Se anota «a medias» si lee las dos cifras pero no las relaciona con la tasa o con las fechas.

---

### Tarjeta A4 · Componente fuera del total (L4)

**Lo que se ve en la pantalla** (frente):

> *Uno por uno (2)*
>
> [ícono de gravedad] `APU-02!G36` · Error · Componente fuera del total (`L4`) · 1.265,00
>
> Costo directo de APU-02 (partida 2): la fórmula APU-02!G36 =SUM(G32:G34) deja fuera transporte y disposición
> (APU-02!G35, 10 USD/u). El CD guardado es 90 USD/u y la suma de materiales, mano de obra, equipos y transporte es
> 100 USD/u. Efecto: con administración (0,15) y utilidad (0,1) del APU y la cantidad 100, la partida queda corta en
> 1 265,00 USD sin IVA.

La cifra de la descripción se escribe **«1 265,00», con un espacio de miles**, porque así la manda hoy el servidor. La
primera línea, en cambio, dice «1.265,00». Esa diferencia está en la pantalla y la tarjeta la conserva (ver la
ratificación 3 del §5).

**Preguntas:** «¿Qué le está diciendo?» · «¿Qué haría ahora?»

**Clave para quien conduce** (*propuesta, a ratificar por Eugenio*). Se anota «sí» si la persona dice que la suma del
costo directo de ese APU no incluye el transporte, y que por eso la partida cobra menos de lo que debería (unos
1.265 USD). Se anota «a medias» si entiende que la fórmula está mal pero no dice qué deja fuera o qué efecto tiene.

---

### Tarjeta A5 · Referencia rota o externa (L5)

**Lo que se ve en la pantalla** (frente):

> *Uno por uno (2)*
>
> [ícono de gravedad] `RESUMEN!B4` · Error · Referencia rota o externa (`L5`)
>
> 2 fórmula(s) de RESUMEN con #REF! (la celda u hoja que citaban se borró): B4, B6. Efecto: esas celdas muestran #REF!
> o un valor que ya no se puede rastrear.

**Preguntas:** «¿Qué le está diciendo?» · «¿Qué haría ahora?»

**Clave para quien conduce** (*propuesta, a ratificar por Eugenio*). Se anota «sí» si la persona dice que dos fórmulas
del RESUMEN apuntan a algo que se borró, y que sus valores ya no son de fiar. Se anota «a medias» si reconoce el #REF!
como un error de Excel pero no dice qué pasa con esas celdas.

---

### Tarjeta A6 · Causa raíz (L1, 6 casos)

**Lo que se ve en la pantalla** (frente):

> *Por causa raíz (1)*
> *Corregir una causa arregla todos sus casos.*
>
> [ícono de gravedad] Error · 6 casos · Referencia desalineada (`L1`)
>
> PRESUPUESTO!F10 (partida 1) lee APU-01!E14 (valor 0) como rendimiento
>
> Encontrado 0 · esperado 120
>
> Celdas: PRESUPUESTO!F10, PRESUPUESTO!F11, PRESUPUESTO!F12, PRESUPUESTO!F13 y 2 más

**Preguntas:** «¿Qué le está diciendo?» · «¿Qué haría ahora?»

**Clave para quien conduce** (*propuesta, a ratificar por Eugenio*). Se anota «sí» si la persona dice que la columna de
rendimiento de seis partidas lee una celda equivocada de su APU (toma 0 donde debería haber 120), y que es el mismo
error repetido. Se anota «a medias» si entiende uno de los dos puntos: que la celda está mal o que se repite en seis
partidas.

---

## 4. De dónde sale cada texto (archivo:línea)

Las rutas del front son relativas a `frontend-desktop/src/`. Las líneas son las del commit `4d04e8d3`.

| Tarjeta | Texto | Lo produce |
|---|---|---|
| A1 a A3 | Título de la sección «Alertas de precio (4)» y su frase | `paginas/auditoria/AlertasDePrecio.tsx:22` y `:23-25` |
| A1 a A3 | El conteo de 4 y la regla que calla «dentro del umbral» y agrupa los mensajes iguales | `paginas/auditoria/logicaDelLibro.ts:144-159`; la frase que calla está en `aplicacion/que_hacer.py:273` |
| A1 a A3 | El título en negrita, el código en monoespaciada y el mensaje tal cual | `paginas/auditoria/AlertasDePrecio.tsx:32`, `:40` y `:42` |
| A1 a A3 | «Qué hacer» (no se imprime) | `paginas/auditoria/AlertasDePrecio.tsx:43`, `comun/QueHacer.tsx:13-21` |
| A1 | «Sin fuente» | `aplicacion/que_hacer.py:237` |
| A1 | «la FUENTE de MT-04 dice «POR COTIZAR»: el precio (INSUMOS!E12) no se puede rastrear» | `fusion/alertas.py:329` y `:336-337` |
| A2 | «Base de la empresa» | `aplicacion/que_hacer.py:248` |
| A2 | «el libro usa 18,00 USD; precio propio de la instalación 15,00 USD del 2026-10-15: +20,00 %, pasa del umbral de 5,00 %» | `fusion/alertas.py:164` y `:194-195`; montos en `:85-88`, porcentajes en `:97-100` |
| A3 | «USD-Bs» | `aplicacion/que_hacer.py:266` |
| A3 | «900,00 Bs al 2026-10-01 (tasa 50) y 990,00 Bs al 2026-11-24 (tasa 55): +10,00 %, pasa del umbral de 5,00 %» | `fusion/alertas.py:282-283`, `:287` y `:294`; tasa exacta y sin ceros en `:91-94` |
| A4, A5 | Título de la sección «Uno por uno (2)» | `paginas/auditoria/ProblemasDelLibro.tsx:153`; los hallazgos sueltos en `paginas/auditoria/logicaDelLibro.ts:121-128` |
| A4, A5 | Ícono, celda, palabra de gravedad, nombre de la regla con su código, impacto | `paginas/auditoria/ProblemasDelLibro.tsx:100-109`; «Error» en `severidad/severidad.ts:18`; «Nombre (L4)» en `paginas/auditoria/ProblemasDelLibro.tsx:52` |
| A4 | «1.265,00» de la primera línea | `paginas/auditoria/ProblemasDelLibro.tsx:109` (`formatoEsVe` en `indicadores/formatoEsVe.ts:7-13`) sobre el exacto «1265.00» de `api/rutas/libros.py:170` |
| A4, A5 | Nombres «Componente fuera del total» y «Referencia rota o externa» | `adapters/hoja_empresa/reglas.py:87-88`, pasados por `aplicacion/nombres_reglas.py:81` y `:90-92`, y por `api/rutas/libros.py:166` |
| A4, A5 | La descripción, tal cual | `paginas/auditoria/ProblemasDelLibro.tsx:115` |
| A4 | «Costo directo de APU-02 (partida 2): la fórmula … sin IVA.» | `adapters/hoja_empresa/reglas_calculo.py:176` y `:183-189`; «transporte y disposición» en `adapters/hoja_empresa/reglas_contexto.py:53`; «1 265,00» con espacio de miles en `adapters/hoja_empresa/reglas_contexto.py:103-108`, y «90», «0,15» y «0,1» en `:111-116` |
| A5 | «2 fórmula(s) de RESUMEN con #REF! … ya no se puede rastrear.» | `adapters/hoja_empresa/reglas.py:613-615` |
| A6 | Título de la sección «Por causa raíz (1)» y su frase | `paginas/auditoria/ProblemasDelLibro.tsx:139` y `:141`; solo las causas de 2 casos o más, en `paginas/auditoria/logicaDelLibro.ts:109-111` |
| A6 | «Error · 6 casos · Referencia desalineada (L1)» | `paginas/auditoria/ProblemasDelLibro.tsx:67-71`; «6 casos» en `paginas/auditoria/logicaDelLibro.ts:180-182`; el nombre en `adapters/hoja_empresa/reglas.py:84` |
| A6 | Los 6 casos agrupados en una sola causa | `aplicacion/causas_raiz.py:44-48` (patrón sin celdas ni números) y `api/rutas/libros_causas.py:46-56` |
| A6 | «PRESUPUESTO!F10 (partida 1) lee APU-01!E14 (valor 0) como rendimiento» | `adapters/hoja_empresa/reglas.py:147` (con `:142` y `:173`), cortada en el primer «;» por `paginas/auditoria/logicaDelLibro.ts:175-178` y mostrada en `paginas/auditoria/ProblemasDelLibro.tsx:75` |
| A6 | «Encontrado 0 · esperado 120» | `paginas/auditoria/ProblemasDelLibro.tsx:78`, con los valores del primer caso de `api/rutas/libros_causas.py:54-55` |
| A6 | «Celdas: PRESUPUESTO!F10, … y 2 más» | `paginas/auditoria/ProblemasDelLibro.tsx:82`, `paginas/auditoria/logicaDelLibro.ts:162-166` |

`paginas/auditoria/ConclusionDelLibro.tsx` no aporta texto a ninguna tarjeta. El veredicto «El libro no cumple» y la
franja de totales van en la sección 3 de la pantalla, y la prueba no los muestra.

### Cómo se comprobó

Los textos de A1 a A3 se generaron con `fusion.alertas.alertas_de_precios` sobre un libro ficticio de
`tests/fixtures/libros_empresa.py`, con los insumos y las tasas del §1. La salida coincide con los recuadros de A1 a A3.
Los de A4 a A6 se armaron con las plantillas de las reglas y sus formateadores reales (`_fmt`, `_fu`, `_valor`,
`exacto`). El agrupamiento de A6 se probó con `aplicacion.causas_raiz.patron`, que da un solo patrón para los 6 casos.
Las reglas L1, L4 y L5 también se corrieron sobre libros sembrados del mismo fixture, para confirmar la forma de cada
descripción. Nada de eso se escribió en el repositorio.

## 5. Diferencias con el guion del 2026-11-23 y lo que queda a ratificar

El guion copió formatos anteriores a las correcciones del 2026-11-27. Las tarjetas siguen el código de hoy:

| Alerta | El guion dice | Sílice muestra hoy |
|---|---|---|
| A3 | «(tasa 50,00)» y «(tasa 55,00)» | «(tasa 50)» y «(tasa 55)»: la tasa va exacta y sin ceros finales (`fusion/alertas.py:91-94`) |
| A4 | «queda corta en 1.265,00 USD» en la descripción | «queda corta en 1 265,00 USD», con espacio de miles (`adapters/hoja_empresa/reglas_contexto.py:103-108`) |
| A6 | Sin la línea «Celdas:» | La pantalla agrega «Celdas: PRESUPUESTO!F10, PRESUPUESTO!F11, PRESUPUESTO!F12, PRESUPUESTO!F13 y 2 más» |
| A1 a A6 | Sin el título de la sección | La pantalla muestra cada alerta bajo su sección, con su título y, en dos casos, con una frase de introducción |

**A ratificar por Eugenio:**

1. **Las frases de introducción de las secciones.** «No son errores del libro: son precios que conviene confirmar con
   quien lo hizo» (A1 a A3) y «Corregir una causa arregla todos sus casos» (A6) se ven en la pantalla, y por eso están
   en las tarjetas. Pero adelantan en parte la respuesta a «¿Qué haría ahora?», que es lo mismo que D3 quiso evitar con
   «Qué hacer». **Recomendación:** dejarlas, porque el guion permite mostrar las alertas en el equipo o en papel, y con
   ellas las dos formas muestran lo mismo. Al informar el resultado, se declara que la persona las vio.
2. **Las claves de calificación** (sí, a medias, no) de cada tarjeta. El guion no las define, y sin ellas dos personas
   que conducen pueden calificar distinto la misma respuesta. Son una propuesta. Si el resultado entra en la tesis, las
   validan los 3 expertos junto con la prueba, como pide el guion.
3. **El espacio de miles de A4** («1 265,00»). Rompe la regla de coma decimal y punto de miles, y la misma tarjeta
   muestra «1.265,00» en su primera línea. El texto viene de `adapters/hoja_empresa/reglas_contexto.py`, que está sellado
   por `reglas-congeladas-2026-11-24` (`tests/unit/test_sellos_de_reglas.py:36`). **Recomendación:** medir así y
   declararlo. Cambiarlo exige un acta, porque toca un archivo sellado; también podría hacerse en una capa de presentación
   del front, pero sería una función nueva antes de medir. Mientras no haya decisión, la tarjeta reproduce la pantalla.
4. **Actualizar el guion** (§«Las 6 alertas reales que se muestran») con los textos de este documento, para que las dos
   fuentes no se contradigan.
5. **Con el catálogo de «Qué hacer» sin cargar**, la pantalla cambia. El título de A1 a A3 sale en minúscula («sin
   fuente», `paginas/auditoria/AlertasDePrecio.tsx:32`) y las alertas USD-Bs «dentro del umbral» no se callan
   (`paginas/auditoria/logicaDelLibro.ts:147`). Antes de cada sesión hay que comprobar que la pantalla muestra «Sin
   fuente» con mayúscula: es la señal de que el catálogo cargó.
