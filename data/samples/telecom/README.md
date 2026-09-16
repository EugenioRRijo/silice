# Muestra telecom: `topologia_arenaza.csv`

Entrada del adaptador `AdaptadorTelecom` (`adapters/telecom/adaptador.py`, Sesión I5): una topología
de red pequeña (rack, dos switches, cuatro puntos de acceso WiFi, un UPS, cinco enlaces de cable
UTP), derivada de los dos presupuestos didácticos de ARENAZA:
`data/samples/telecom/Presupuesto_1_ARENAZA.pdf` (instalación de puntos WiFi, 14 renglones,
1 109,29 USD) y `data/samples/telecom/Presupuesto_2_ARENAZA.pdf` (red y CCTV con rack, 26 renglones,
5 410,73 USD); ambos leídos con `python -c "import fitz; ..."` (PyMuPDF global, no está en el venv de
uv).

## Columnas

`tipo,id,descripcion,codigo_partida,unidad,cantidad,origen,destino,longitud_m,reserva,especificaciones`

- `tipo` ∈ {`nodo`, `enlace`}. Una fila `nodo` solo llena `cantidad`; una fila `enlace` solo llena
  `origen,destino,longitud_m,reserva`. Las columnas que no aplican a la fila se dejan vacías.
- `id`: clave de la fila, usada tal cual como `origen_id` del `ItemComputo` (trazabilidad total,
  CLAUDE.md sección 2).
- `codigo_partida`: prefijo `TC-` (partidas propias del dominio telecom; no reutiliza códigos `LB-`
  de la línea base civil).
- `cantidad` (solo `nodo`): cantidad tabular directa, tomada tal cual del CSV.
- `origen`, `destino` (solo `enlace`): extremos del tramo de cable, como `id` de dos filas `nodo`.
  No se validan como referencias existentes en esta sesión (fuera del alcance del adaptador); quedan
  en `ItemComputo.especificaciones["origen"/"destino"]` para que una regla de verificación futura los
  use si hace falta. Nota: no todo nodo tiene un enlace que lo referencie en esta muestra (por
  ejemplo `AP-04` no aparece como `destino` de ningún enlace); es un enlace "colgante" deliberado,
  documentado como alcance de esta sesión, no un error de la muestra.
- `longitud_m`, `reserva` (solo `enlace`): la cantidad del enlace es
  `longitud_m * (1 + reserva)` (`ItemComputo.regla`), evaluada por
  `adapters/telecom/evaluador.py`. `reserva` es la fracción adicional de cable por curvas, empalmes
  y holgura de servicio; vacía equivale a 0 (ver `adapters/telecom/adaptador.py::_reserva`).
- `especificaciones`: pares `clave=valor` separados por `;` (por ejemplo `categoria=cat6;tipo_cable=utp`),
  trazables hacia la regla R4.

## Procedencia de cada nodo (tabla nodo → fuente)

Ningún PDF de ARENAZA es una topología de red (con nodos y tramos identificados): son listas de
materiales. Cada nodo de la muestra toma su **tipo y cantidad de equipo** de un renglón de uno
de los dos PDF; ninguno inventa una cantidad que no esté en la fuente.

| Nodo(s) | Descripción | Fuente | Renglón del PDF | Cantidad en el PDF |
|---|---|---|---|---|
| `RACK-01` | Rack fijo 12U | `Presupuesto_2_ARENAZA.pdf` | "Rack Fijo Onlink 12u" | 1 |
| `SW-CORE` | Switch escritorio gigabit 10 puertos PoE | `Presupuesto_1_ARENAZA.pdf` | "Switch Escritorio Gigabit De 10 Puertos Con Poe" | 1 |
| `SW-DIST` | Switch TP-Link 16 puertos | `Presupuesto_2_ARENAZA.pdf` | "Switch Tp-link 16 Puertos" | 1 |
| `AP-01`..`AP-04` | Punto de acceso WiFi Ruijie | `Presupuesto_2_ARENAZA.pdf` | "Punto De Acceso Rap Ruijie" | 4 (una fila por unidad) |
| `UPS-01` | Mini UPS de respaldo | `Presupuesto_2_ARENAZA.pdf` | "Mini Ups Spidertec 17600mah" | 1 (`capacidad=17600 mah` toma el dato textual del renglón) |
| `ENL-01`..`ENL-05` | Enlaces de cable UTP CAT6 | **supuesto**, ver abajo | — | — |

**Corrección respecto de una versión anterior de esta muestra:** `Presupuesto_1_ARENAZA.pdf` no trae
ninguna cantidad de puntos de acceso WiFi: su nota al pie solo dice que se "reutilizan los
DECODIFICADORES MESH" ya existentes para dar cobertura, sin declarar cuántos. Esa nota **no es la
fuente** de `AP-01`..`AP-04`; la única cantidad de puntos de acceso que aparece en cualquiera de los
dos PDF es el "4" de "Punto De Acceso Rap Ruijie" en `Presupuesto_2_ARENAZA.pdf`, y es la que usa
esta muestra.

## Supuestos declarados (no vienen de ningún PDF)

Ningún PDF discrimina el cableado por tramo. Lo que compran es **cable por bobina, medido en
piezas**, nunca en metros: `Presupuesto_1_ARENAZA.pdf` lleva "BOBINA CABLE UTP CAT 6 (300 M)"
(renglón 1, 1 pieza, 82,68 USD) y "Bobina Cable Utp Cat6 305 m Int" (renglón 7, 1 pieza,
211,21 USD); `Presupuesto_2_ARENAZA.pdf` lleva esas dos mismas bobinas (renglones 1 y 2,
96,99 y 211,21 USD). Son del orden de 605 m disponibles en cada presupuesto, sin reparto por tramo.

**Corrección de la revisión final del sprint alpha (ítem 10).** Una versión anterior de este README
atribuía a esas bobinas "90 m" (`Presupuesto_1`) y "90 m y 80 m" (`Presupuesto_2`). Los PDF no dicen
eso: los 90 y los 80 son **metros de "Tubo Corrugado Flexible 1 Pulgada"** —la canalización, no el
cable—, renglón 3 de `Presupuesto_1_ARENAZA.pdf` y renglón 5 de `Presupuesto_2_ARENAZA.pdf`, la
única partida medida en metros de los dos documentos. Ese renglón, además, **no coincide consigo
mismo** en el segundo presupuesto: sus cómputos métricos dicen 80 m y su presupuesto 90 m (99,75 ×
3 tubos de 30 m = 299,25 USD). Es una inconsistencia de la fuente primaria, del mismo tipo que las
siete de la línea base civil; queda anotada aquí, no corregida.

Por eso, para que la regla `longitud_m * (1 + reserva)` sea evaluable, esta muestra **supone** una
topología plausible (rack -> switch núcleo -> switch de distribución -> puntos de acceso) y reparte
una longitud entre sus cinco enlaces (`ENL-01`..`ENL-05`, que suman 95 m antes de reserva, del orden
de los 90 m de canalización del primer presupuesto y muy por debajo de los ~605 m de bobina
comprados), cada uno con su propia fracción de reserva. Es el mismo tipo de supuesto declarado que
el sobreancho y el espesor de fondo en `data/samples/civil/README.md`: ninguno sale de la fuente
primaria, ambos quedan documentados aquí para no confundirse con un dato medido.

## Política de mano de obra "50 % del total"

Ambos PDF de ARENAZA (`Presupuesto_1_ARENAZA.pdf`, `Presupuesto_2_ARENAZA.pdf`) fijan la mano de obra
como "el equivalente al 50 % del presupuesto total", no un jornal por rendimiento como en el dominio
civil (CLAUDE.md sección 4). Esta muestra y el adaptador **no representan esa política**: el
adaptador solo extrae `ItemComputo` (cantidades de obra), no `ComposicionAPU` ni costeo; la política
de mano de obra pertenece a la capa de costeo (`core.costing`, `core.contracts.apu`), fuera del
alcance de esta sesión. El análisis de cómo representarla sin tocar `core/` está en
`docs/bitacora/2026-08-29-I5-telecom.md`.
