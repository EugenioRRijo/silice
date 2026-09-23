**Naturaleza.** Comunicación personal con un profesional de presupuestos de obra, recibida como
mensajes de voz el 2026-09-16. El informante conserva su anonimato por decisión del autor.

**Cómo se cita.** En APA 7 una comunicación personal se cita en el texto y no entra en la lista de
referencias: `(comunicación personal, 16 de septiembre de 2026)`. Esta transcripción existe como
anexo consultable, no como referencia bibliográfica.

**Qué papel cumple.** No prueba la existencia del salario por unidad de obra: eso lo establece el
artículo 114 de la LOTTT. Esta nota testimonia que esa modalidad se usa en obra y cómo se refleja
en el análisis de precios unitarios.

## Transcripción

> *Pendiente de transcribir por el autor a partir de los mensajes de voz originales.*

## Contenido técnico recogido

Resumen fiel de lo que la nota aporta y que el diseño del prototipo
(`docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md`) ya usa:

- **Las tres tablas de insumos.** Un análisis de precios unitarios se arma con tres desgloses
  separados: materiales, equipos y mano de obra.
- **La unidad de cobro por partida.** Cada partida se cobra en una unidad propia (m², m³, pieza,
  etc.), declarada junto con su código y descripción antes de armar los desgloses.
- **El doble sentido de «rendimiento».** El informante usa la misma palabra para dos cosas
  distintas: el consumo de material por unidad de obra (por ejemplo, sacos de cemento por m³) y la
  producción por día de una cuadrilla o de un equipo (por ejemplo, metros cuadrados instalados por
  día). Son magnitudes distintas que el sistema ya modela en campos separados
  (`LineaMaterial.cantidad` frente a `ComposicionAPU.rendimiento`); la nota advierte que, si la
  interfaz no distingue el nombre de una y otra, el error de confundirlas es fácil de cometer.
- **El rendimiento lo declara quien hace el análisis, y debe poder modificarlo.** No existe una
  tabla única de rendimientos de referencia: el rendimiento depende de la cuadrilla, del equipo y
  de las condiciones de la obra, así que quien presupuesta lo declara explícitamente —junto con esas
  condiciones— y lo ajusta partida por partida, en vez de aceptar un valor por defecto.
- **La mano de obra se cobra por jornal o por unidad instalada.** Una línea de mano de obra puede
  pagarse por jornal (sueldo diario, con sus prestaciones y bono de alimentación) o por destajo
  (un precio por unidad de obra instalada). Ambas modalidades conviven en la práctica, a veces
  dentro de la misma partida.
- **Los precios se manejan en dólares.** El profesional trabaja con listados de precios en
  bolívares y los convierte a dólares para el análisis, con una tasa de cambio que debe declararse
  junto con la lista de origen.
