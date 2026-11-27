# Notificaciones por evento y qué recibir (C11b)

**Fecha:** 2026-11-26. **Estado:** acordado. Eugenio planteó las ideas («son ideas que se me ocurrren , podemos betir
que tipos de notificaciones vamos a usar»), Claude propuso la lista con el criterio de §2.1 y Eugenio respondió
«ok perfecto».

**Acordado:** se construyen ahora cuatro categorías:
1. una versión espera su dictamen, con un recordatorio a los 2 días hábiles;
2. su versión fue aprobada o devuelta;
3. compras por pedir (procura);
4. se cargó una lista de precios nueva.

**Entregas al cliente: construida el 2026-11-27.** Eugenio la pidió en la lista de pendientes («la fecha de entrega al
cliente en las notificaciones»): campo opcional «Fecha de entrega al cliente» (dd/mm/aaaa, escrito a mano) en Nueva
obra y en el Resumen, tabla `entrega_de_obra` fuera de `core/` (caso_0025) y quinta categoría «entregas».

**Para después de medir:**
- el plazo propio «Responder antes del».

**No serán notificación:**
- cada cambio en un presupuesto, que sería ruido; lo cubren la categoría 2 y la página de Actividad (C10);
- «evaluar» como categoría aparte, que se funde con la 1.

**Recibir:** todas vienen encendidas y cada persona puede apagarlas en Cuenta › Notificaciones, salvo la 1 para quien
revisa.

### 2.1 Criterio

Una notificación vale si pide actuar o si cambia algo que la persona usa. Si solo cuenta que algo pasó, es ruido y
lleva a la fatiga de alertas: la gente deja de mirar la campanita. Es el mismo criterio de GitHub y VS Code, y el de la
guía `content-first-noise-reduction`. Sigue a la fila C11 de
[plan-integracion-cara](../planes/2026-11-26-plan-integracion-cara.md). C11 ya construyó las piezas del front y la tabla
`notificacion` con sus rutas (`f7520d3b`).

**Decisión de Eugenio (2026-11-26):** «elegir qué notificaciones recibir; notificaciones de cambios en un presupuesto, se
cargaron una lista al sistema de precios, por ejemplo otra hoja maprex, se acerca la fecha para entregar,comprar o
evaluar un presupuesto, cosas asi».

## 1. Qué cambia

Hasta ahora una notificación la crea el front de quien hizo algo (por ejemplo «Versión V2 guardada», que solo ve esa
persona). Con C11b, **el servidor crea notificaciones cuando pasa algo** y se las deja a las personas a quienes les
importa. Cada persona elige en **Cuenta › Notificaciones** qué categorías recibir.

## 2. Categorías

| Categoría | Cuándo nace | A quién le llega | Dato de origen (hoy) | Gravedad |
|---|---|---|---|---|
| **Cambios en un presupuesto** | Se guarda una versión nueva de una obra | Quien trabajó en esa obra (guardó o envió una versión), menos quien la guardó | versiones de la obra (`hoja`) | Información |
| **Aprobaciones** | Una versión se envía a aprobación, o se aprueba, se devuelve o se retira | Envío: quienes pueden dictaminar (`revisa`). Dictamen o retiro: quien la envió | rastro de aprobaciones (`aplicacion/aprobaciones.py`) | Información; una devuelta es Advertencia |
| **Listas de precios** | Se carga una lista o referencia nueva (otra MaPreX, la lista de la empresa) | Todas las cuentas que arman (`arma`) | `aplicacion/precios_empresa.py`, `listas_para_armar.py` | Información |
| **Compras por hacer** | Falta poco para «pedir a más tardar» un material (desde 2 días hábiles antes), o ya pasó | Quien trabajó en esa obra | `aplicacion/procura.py` (necesita la línea base) | Advertencia; vencida es Error |
| **Evaluaciones pendientes** | Una versión lleva esperando dictamen 2 días hábiles o más | Quienes pueden dictaminar | rastro de aprobaciones (fecha del envío) | Advertencia |
| **Entregas al cliente** | Falta poco para la fecha de entrega del presupuesto (3 días hábiles antes y el día) | Quien trabajó en esa obra | **No existe**: ver §4 | Advertencia; el día es Error |

Reglas comunes:
- **Días hábiles del recordatorio de dictamen:** se cuentan de lunes a viernes **sin feriados**
  (`aplicacion/mesa.py`, `dias_habiles_entre`), porque una aprobación no tiene línea base de la que leer el calendario
  de la obra; un feriado adelanta el recordatorio un día. Las compras y las entregas sí descuentan los feriados de la
  línea base (auditoría antes de medicion-v1, 2026-11-27).
- **Una sola vez por evento:** la notificación lleva una clave del evento (por ejemplo `aprobacion:V3:enviada`). Si
  la misma clave ya existe para esa persona, no se repite.
- **Las fechas se revisan sin hilo de fondo**, igual que los borradores: un barrido perezoso al listar
  (`GET /v1/notificaciones`) calcula lo que vence hoy para esa persona y crea lo que falte.
- **Enlace al lugar:** cada notificación lleva su ruta interna (la obra y la sección, o Precios de la empresa).
- **Nunca un monto calculado en el front:** si una notificación dice una cifra, es el texto del servidor.

## 3. Elegir qué recibir

- En **Cuenta › Notificaciones**, una lista de las seis categorías con un interruptor cada una y su frase de qué
  avisa. Por omisión, todas encendidas.
- Se guarda por persona: una tabla `preferencia_notificacion (usuario_id, categoria, activa)`, en la misma migración
  de C11b.
- Apagar una categoría no borra lo ya recibido. Solo deja de crear lo nuevo.
- El pie del panel («Elegir qué notificaciones recibir») lleva a esa pantalla.

## 4. Lo que falta para «entregar» y para un plazo de «evaluar»

- **Entregar:** ninguna obra guarda la fecha en que hay que entregarle el presupuesto al cliente. Hace falta un campo
  nuevo y opcional, **«Fecha de entrega al cliente»**, en los datos de la obra (Nueva obra y Resumen de la obra). Sin
  esa fecha, la categoría no avisa nada.
- **Evaluar:** hoy se avisa por antigüedad, a los 2 días hábiles esperando dictamen. Un plazo propio sería otro campo
  opcional, **«Responder antes del»**, al enviar a aprobación.

Los dos campos son datos nuevos: la decisión de incluirlos o no es de Eugenio (§6).

## 5. Pruebas

- Aplicación:
  - cada categoría nace en su evento y solo para quien corresponde;
  - no se repite;
  - la preferencia apagada no crea;
  - el barrido de fechas en los bordes (2 días hábiles, el día, ya vencida, con feriados de la línea base);
  - sin línea base, no hay avisos de compra.
- API:
  - `GET` y `PUT /v1/notificaciones/preferencias`, solo las propias.
- Front:
  - la pantalla de preferencias por rol y nombre;
  - el enlace desde el pie del panel.

## 6. Decisión pendiente

¿Se agregan ahora los campos «Fecha de entrega al cliente» y «Responder antes del», o C11b sale con las cinco
categorías que ya tienen datos y esos dos campos quedan para después de la medición?
