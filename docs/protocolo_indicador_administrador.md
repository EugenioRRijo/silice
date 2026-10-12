# Protocolo de medición: el indicador de quien revisa (S3 §13.5 a; horizonte §6.1)

Versión 1, escrita en S3-0 **antes** de la fase Med (maestro §7). Su huella SHA-256 está en
[`protocolos_s3.json`](protocolos_s3.json); la meta (`S3-M1`) la vigila. Cambiar algo exige una
versión 2 con su huella. CP-R1 («revisar un paquete con diferencias sembradas») es la condición
«con el sistema» de este protocolo, y el criterio (b) de RNF-17 se mide en esa misma sesión.

## 1. Qué se mide

Si Sílice ayuda a quien revisa a encontrar las diferencias entre dos entregas de un presupuesto
mejor que hacerlo **a mano**, con el Excel de cada entrega. Dos medidas, más el tiempo:

* **Tasa de detección** = diferencias sembradas que la persona reporta ÷ diferencias sembradas.
* **Falsas alarmas** = diferencias que reporta y no están en la lista congelada ÷ las que reporta.
* **Tiempo** hasta que dice «terminé» (tope de 30 minutos por condición), con cronómetro.

## 2. Material (se fija y se congela antes de medir)

* La obra y el presupuesto base son los mismos para todas las personas y las dos condiciones. Para
  que lo aprendido en una condición no regale la otra, hay **dos entregas paralelas** (P y Q) del
  mismo presupuesto: cada una trae la versión anterior y la nueva, y **5 diferencias sembradas**,
  una de cada tipo de SL-E9: de cantidad, de precio, de ambas, partida eliminada y partida nueva
  (memoria de diferencias §1 para la P y §1b para la Q). Ninguna trae más de una por partida.
* **Lista congelada:** las 10 diferencias (5 de P y 5 de Q), con partida, tipo y monto exacto, se
  escriben en `docs/protocolo_indicador_administrador_lista.md` y su SHA-256 se registra en
  `docs/protocolos_s3.json` **antes** de que nadie las vea. Las cifras del monto salen de la
  memoria de diferencias (`tests/fixtures/memorias/diferencias_s3.md` §1 y §1b), no del sistema.
* Condición **a mano:** los dos Excel de la entrega y una hoja de reporte en blanco. Condición
  **con el sistema:** los dos `.silice` y la vista Revisar; el Excel del sistema no se entrega.
* Consigna escrita (se lee textual, sin añadir): «Encuentre las diferencias entre las dos
  versiones de este presupuesto y anótelas con su partida y su monto. Diga *terminé* cuando
  quiera».

## 3. Personas

* **6 personas**, con experiencia mínima de 2 años elaborando o revisando presupuestos de obra
  (ingenieros civiles, estimadores). Criterio de selección: que **no** hayan participado en
  construir Sílice ni en CP-07 a CP-11, y que no conozcan las listas de diferencias.
* **Orden contrabalanceado:** 3 personas hacen primero «a mano» con la entrega P y después «con el
  sistema» con la Q; las otras 3, primero «con el sistema» con la P y después «a mano» con la Q.
  Ninguna persona ve la misma entrega dos veces. La asignación de personas a órdenes se sortea
  con la semilla 42 antes de citarlas.
* Entre las dos condiciones hay 10 minutos de descanso. Una sesión dura unos 90 minutos con
  la explicación de 10 minutos de cómo se usa la vista Revisar (la misma para todas).

## 4. Cómo se analiza

Estadística **descriptiva**: mediana y rango de cada medida por condición y la diferencia dentro
de cada persona. Con 6 personas no se hace prueba de hipótesis (la mínima probabilidad de un
Wilcoxon exacto de dos colas con n = 6 es 0,0625, mayor que 0,05): se reporta lo observado y se
declara que no es una prueba. RNF-17 (a, b) se reporta en la misma sesión: abrir el paquete y
decir su estado y quién lo emitió en ≤ 5 min; hallar las diferencias sembradas en ≤ 20 min.

## 5. Amenazas a la validez (declaradas)

* **Sesgo del autor como facilitador:** quien construyó Sílice conduce la sesión y quiere que
  funcione. Se mitiga leyendo la consigna textual, sin responder preguntas sobre la tarea durante
  la medición y registrando cada ayuda pedida; si hay otra persona del equipo que no escribió la
  vista Revisar, ella conduce. Queda declarado.
* **Validez de constructo:** las diferencias están sembradas por el autor y son de los tipos que
  la vista sabe mostrar (cantidad, precio, partida nueva o eliminada): una diferencia de otro tipo
  no está en el material. «Encontrar diferencias» no es «revisar bien un presupuesto».
* **Validez externa:** una obra y un presupuesto ficticios; 6 personas de un círculo cercano;
  Excel como línea base «a mano», que es lo habitual, pero no la práctica de cada empresa.
* **Validez interna:** orden y aprendizaje (se contrabalancea, no se elimina); fatiga en la
  segunda condición; el tope de 30 minutos cortaría la condición lenta; el cronómetro lo maneja
  el facilitador.
* **Tamaño:** n = 6 es suficiente para ver una diferencia grande y para mejorar la vista, no para
  afirmar una tasa. La tesis lo presenta como un estudio piloto.

## 6. Qué se registra

Por persona y condición: tasa de detección, falsas alarmas, minutos, ayudas pedidas, orden y
comentarios en voz alta. Todo en `docs/bitacora/2026-10-silice-080.md` (sin nombres: P01 a P06),
con la huella de este protocolo y la de la lista congelada.
