---
name: interfaz-silice
description: Use when designing, changing or reviewing any screen, form, table or flow of Sílice's frontend (frontend-desktop/) — úsala antes de tocar una pantalla de Sílice. Es la capa propia del proyecto sobre la skill general «disenar-desde-la-tarea»: las piezas comunes, las guardias y los errores ya vividos con usuarios.
---

# Interfaz de Sílice: diseñar desde la tarea

## Antes que nada

1. **Aplica la ficha de la pantalla** (10 partes, en orden, antes del código): historia de trabajo, de dónde viene y a
   dónde va, quién la usa y qué sabe, camino crítico, tipo de vista y frase de respuesta, reparto de controles (8 o
   menos a la vista y el resto en «Más opciones» con su omisión), punto de partida, tabla de estados, supuestos de
   negocio y las pruebas que la fijan.
   - Claude la tiene completa en la skill personal `disenar-desde-la-tarea`.
   - Cualquier agente puede leer sus fuentes en el repo: `docs/planes/2026-11-23-estudios-ux.md` (reglas UX-01 a UX-29),
     `docs/planes/2026-11-23-estudios-disenadores.md` (método en 15 pasos, §6, y patrones de React, §3) y
     `docs/planes/2026-11-23-carga-cognitiva.md` (reglas 1 a 12 y el caso de 4 vistas).
2. Lee `frontend-desktop/DESIGN.md` (el aspecto) y la skill `front-carbon-fiori-ibcs` (Carbon, Fiori e IBCS). Esta skill
   no repite la estética: trata de la tarea y de la carga mental.

## Quién usa Sílice

- Presupuestistas e ingenieros de la empresa que viven en Excel: quieren densidad, teclado como en Excel y nada que los
  frene.
- Personas que **no dominan el oficio**, como el propio Eugenio: «no sabía qué datos colocar porque no domino el
  lenguaje de este tema».
- Se sirve a los dos así: cada campo con jerga lleva un ejemplo con un valor típico, la ayuda larga va a pedido
  («¿Qué es esto?») y se arranca desde algo parecido (Similares, la última cláusula o una plantilla).

## Piezas que ya existen: úsalas antes de crear otras

| Necesidad | Pieza |
|---|---|
| Paso siguiente visible | `comun/FranjaDelPaso.tsx` («Siguiente paso: …» con su botón) |
| Tabla densa con cifras exactas | `comun/TablaDensa.tsx` |
| Ayuda a pedido | `comun/QueEsEsto.tsx`; la de pantalla, `comun/ayuda/AyudaDeLaPantalla.tsx`, con sus textos en `comun/ayuda/textos.ts` |
| Estado vacío | `comun/EstadoVacio.tsx` |
| Error con el detalle del servidor | `comun/AvisoError.tsx` |
| Campo de texto con coma decimal | `comun/CampoTexto.tsx` |
| Carga de página | `comun/EsqueletoPagina.tsx` |
| Glosario | `comun/ayuda/textos.ts` (`GLOSARIO`, en orden alfabético) |
| Borrador abierto de la obra y si se puede editar (para pantallas que no son la Hoja) | `comun/borradorAbierto.ts` (`ContextoDelBorradorAbierto`, `ContextoDeLaEdicionDelBorrador`, `rutaDeVista`) |

**Fronteras:** una página no importa de otra (`comun/arquitectura.test.ts`). Lo que dos páginas comparten va en
`comun/`, y antes de crear un archivo ahí, busca uno que ya cumpla ese papel. El 2026-11-23 se creó
`presupuestoAbierto.ts` y hubo que borrarlo, porque `borradorAbierto.ts` ya existía.

## Reglas propias de Sílice (además de la ficha)

- Se trata a la persona de **usted** en todo texto («Escriba», «Su obra»), nunca de tú. En la prueba con la skill, un
  agente escribió «Tu rol no puede…»: es el error que esta regla evita.
- Coma decimal y punto de miles en toda entrada y salida.
- Una cifra la calcula el servidor; la pantalla no recalcula montos.
- **Las pestañas internas van con fondo** (`TabList contained`), como en Control de obra. Lo vigila
  `comun/pestanasConFondo.test.ts`.
- Las secciones de una obra comparten anatomía: cabecera de la obra, pestañas de sección, selector de subvista, título y
  «¿Qué es esto?» en el mismo lugar, y pestañas internas con fondo.
- `core/` no cambia. Un mensaje del núcleo con jerga («ADVERTENCIA: … no es derivable ni reproducible») se traduce en
  `aplicacion/`; por ejemplo, el de la regla R1 se reconoce en `aplicacion/hoja_partidas.py:114`.
- Ninguna sigla sola como rótulo (R, Km, SPI, CPI, EAC, P80, FCAS): primero la palabra, o la sigla con su explicación
  entre paréntesis.
- **La guardia de interfaz** (`comun/guardiaInterfaz.test.ts`, norma en `docs/especificaciones/2026-11-23-norma-de-interfaz.md`)
  vigila en la CI el trato de tú, las siglas sueltas en rótulos, la severidad en mayúsculas y los `EstadoVacio` sin paso
  siguiente, en modo trinquete con `guardiaInterfaz.deuda.json`. Si arreglas un caso de la deuda, borra su línea; si la
  guardia marca algo nuevo, arréglalo: no lo agregues a la deuda.
- TDD: la prueba en rojo antes del código, y suite completa al cerrar.
- No se corre `prettier --write`: el repo no sigue ese formato, y reformatea cientos de líneas ajenas. Lo que manda es
  `npm run lint`.

## Errores ya vividos en Sílice (no repetirlos)

| Fecha | Qué pasó | Qué hacer |
|---|---|---|
| 2026-11-23 | Componer una partida: al guardar solo decía «Composición guardada…», sin saber si la partida quedó en el presupuesto ni cómo seguir (`paginas/componer/index.tsx`, `alGuardar={sinMas}`) | Todo flujo termina con `FranjaDelPaso` o con un estado de éxito que tiene el paso siguiente |
| 2026-11-23 | Componer tiene unos 40 controles y palabras del oficio sin ejemplo | Ficha, partes 3, 6 y 7 |
| 2026-11-23 | Reajuste: 14 campos a la vista y «R» sin explicar | Campos dependientes solo cuando aplican; R se pregunta con un sí o un no |
| 2026-11-23 | Control: «Índice 0,9500», «Fin 41,05» y una matriz de 10 × 12 fracciones | Cifras en % y en fechas, con frase de respuesta; la matriz plegada |
| 2026-11-23 | Pestañas con fondo en Control y de línea en Presupuesto | Cabecera común y guardia de pestañas |
| 2026-11-22 | «Tablero de avión»: siglas y abreviaturas sin explicar | Lenguaje llano y glosario, y aun así la ficha: explicar no basta si hay demasiado a la vista |

Cuando Eugenio o una persona usuaria se pierda o se queje, **agrega aquí una fila** con su frase textual, la causa y la
regla. Si la lección vale para cualquier proyecto, súmala también a `errores-aprendidos.md` de la skill personal
`disenar-desde-la-tarea`.
