# Ficha de la pantalla: Componer una partida (tarea F4-1)

> Plan: `todo-norma-y-guardia-de-interfaz` (F4: el rediseño empieza por la tarea «componer una partida»). Método: skill
> `disenar-desde-la-tarea` y su capa `.agents/skills/interfaz-silice/`. Análisis de tareas y recorrido cognitivo previos:
> `docs/planes/2026-11-23-estudios-disenadores.md` §2.

**Lo que contó Eugenio (2026-11-23):** «acabo de componer una partida y me perdí» y «al componer no sabía a veces qué
datos colocar porque no domino el lenguaje de este tema».

## 1. Historia de trabajo

Cuando tengo una partida del pliego que no está en el catálogo, quiero armar su precio con los insumos y rendimientos que
uso, **para poder ponerle su cantidad en el presupuesto de la obra** y saber cuánto cuesta.

## 2. De dónde viene y a dónde va

- **Viene de** Presupuesto › Partidas (le falta una partida) o de la subvista Presupuesto › Componer.
- **Va a** Presupuesto › Partidas, con «Agregar partida» abierto, la partida recién compuesta ya elegida y el foco en
  «Cantidad».
- **El defecto de hoy:** la subvista monta `paginas/componer/index.tsx` con `alGuardar={sinMas}`. Al guardar solo dice
  «Composición guardada para la partida X: precio unitario Y» y no ofrece salida. El camino desde «Agregar partida» ›
  «Componer una partida nueva» (`hoja/ComponerEnPanel.tsx`) sí vuelve con la partida elegida. Las dos entradas deben
  terminar igual.

## 3. Quién la usa y qué sabe

- Presupuestistas que vienen de Excel y conocen los APU: quieren rapidez y nada que los frene.
- Personas que **no dominan el oficio** (Eugenio): no saben qué es el rendimiento, qué condiciones escribir ni qué tipo de
  obra elegir.
- Para servir a los dos: cada campo con jerga lleva una línea con un ejemplo, la ayuda larga va a pedido y se arranca
  desde una partida parecida (Similares) en vez de en blanco.

## 4. Camino crítico

1. Identificar la partida: código, descripción y unidad.
2. Elegir los insumos: materiales, equipos y mano de obra con sus cantidades.
3. Poner el rendimiento y sus condiciones.
4. Ver el precio unitario.
5. Guardar.
6. **Llevarla al presupuesto con su cantidad.**

Casi siempre se deja como viene: el tipo de obra, la fecha de precios y los parámetros del precio (FCAS, administración
y utilidad, que salen de la obra).

## 5. Tipo de vista y pregunta

Formulario de captura en una página. Pregunta: «¿Cuánto cuesta una unidad de esta partida?». La respuesta, el precio
unitario con su desglose, se ve en vivo.

## 6. Reparto de controles (lote 3; por confirmar)

- **A la vista:** código, descripción, unidad, rendimiento con sus condiciones, las tres tablas de insumos y el precio
  unitario.
- **En «Más opciones de la partida»,** con su resumen: «Tipo de obra: civil; precios al 23/11/2026; parámetros de la
  obra. Cambiar»: el tipo de obra, la fecha de precios, los parámetros del precio y la referencia MaPreX.
- **Sale:** el párrafo de entrada («declare su cabecera y sus tres tablas…»). Lo dice la propia pantalla, y si hace falta
  va al «¿Qué es esto?».

## 7. Punto de partida (lote 2)

- Al escribir la descripción, «Similares» ya ofrece partidas parecidas. Se vuelve la salida principal para quien no
  sabe: «Empezar desde esta» copia sus tablas.
- Con el código de una partida que ya existe, sus tablas se precargan (ya ocurre).

## 8. Estados

| Estado | Qué ve | Paso siguiente |
|---|---|---|
| Cargando | Esqueleto de la página | — |
| Sin lista de precios | `AvisoSinLista` al abrir (ya existe) | «Crear la lista» |
| Error al guardar | El detalle del servidor junto al botón; **nada de lo escrito se borra** | Corregir y «Guardar composición» |
| **Éxito, dentro de una obra** | «La partida X quedó guardada con un precio unitario de Y. **Todavía no está en el presupuesto de esta obra.**» | Botón principal: **«Agregar X al presupuesto»**, que lleva a Partidas con el diálogo abierto, la partida elegida y el foco en Cantidad |
| Éxito, desde el diálogo «Agregar partida» | Vuelve al diálogo con la partida elegida (ya ocurre) | «Cantidad» |
| Sin permiso | La página dice por qué (ya existe) | — |

## 9. Supuestos por confirmar (con Eugenio)

- S1: los ejemplos de cada campo con jerga (lote 2) salen de partidas reales del catálogo o del historial de
  rendimientos, **no** de valores inventados. Si no hay dato, la línea explica sin cifra.
- S2: el tipo de obra, la fecha de precios y los parámetros pueden plegarse, porque casi siempre se dejan como vienen
  (lote 3).
- S3: las condiciones del rendimiento son obligatorias por diseño (UC-06). Se mantienen a la vista, con un ejemplo de qué
  escribir.

## 10. Pruebas que lo fijan

- Lote 1:
  - en la obra, tras guardar, se ve el texto «Todavía no está en el presupuesto» y el botón «Agregar X al presupuesto»
    recibe el foco;
  - pulsarlo abre Partidas con el diálogo «Agregar partida», la partida elegida y el foco en «Cantidad»;
  - el éxito no desaparece.
- Lote 3: los controles visibles por omisión, contados en la prueba, no pasan del tope acordado.
- Siempre: un error al guardar no borra lo escrito.

## Recorrido cognitivo (con un paso más allá)

| Paso | Hoy | Con el lote 1 |
|---|---|---|
| Guardar | Falla P4: «Guardado», ¿dónde? | «Guardada; todavía no está en el presupuesto» |
| Llevar al presupuesto | Falla P2: no hay control | Botón principal, con el foco |
| Poner la cantidad | La persona debe buscar la partida otra vez | El diálogo abre con la partida elegida y el foco en Cantidad |
| Un paso más: ver el total | — | El Presupuesto muestra la fila nueva y el total (ya ocurre al agregar) |
