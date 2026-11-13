# Ola 2, línea 1: re-congelado de la Hoja, plan por períodos y Control (2026-11-13)

Rama `feature/recongelado-hoja` (desde `e2dfe116`), árbol `.worktrees/s2m3`. Eugenio autorizó hoy hacer todo el pendiente
(«hazlas tú, todo el pendiente, te doy permiso»), incluido un nuevo re-congelado del experimento para `aplicacion/hoja.py`
([acta](2026-11-13-recongelado-experimento-2.md)). Encargo: ESTADO §5, punto 6 (lo que dejó la prueba de punta a punta
para el próximo re-congelado y las notas del árbitro de la ronda 2). Todo con datos **ficticios** (la vivienda de
`tests/fixtures/obra_vivienda.py`, OB-S2 de `tests/fixtures/control_ob_s2.py`, «Empresa ficticia»); ningún dato del libro
real. `core/` no cambia (`git diff e2dfe116 --stat -- core/` vacío).

Las decisiones se **simularon** (guiones del scratchpad de la ola 2: `sim_fuente.py`, `sim_dias.py`, `sim_salida.py`,
`huella_auditor.py`, `ast_diff.py`) y son **provisionales**: Eugenio las ratifica. Segunda opinión corta de Gemini 4 Argon
(§9). Requisitos: RF-196 a RF-199 en `docs/ERS.md`; manual: §4.6, §4.8 (primera versión de una obra larga) y §11.

| Punto del encargo | Hecho | Commits (rojo → verde) |
|---|---|---|
| 1. `_estado_de_precio` mira la fuente declarada (D-17) | sí (§1) | `da399c05` → `f79ad096` |
| 2. `con_plan_por_rendimientos` usa `plan_que_cabe` | sí (§2) | `da399c05` → `f79ad096` |
| 3. «+ Administración» y las tildes de `hoja.py` | sí (§3) | `da399c05` → `f79ad096` |
| 4. `estado_de_items` no reparte un hallazgo que cita su renglón | sí (§4) | `da399c05` → `f79ad096` |
| 5. Un plan por meses o semanas se ve con su unidad | sí (§5) | `9156a5ac` → `4ad7df10` |
| 6. Control: días por período desde el plan | sí (§6) | `bbf2be11` → `d4f741c5` (y `docs/api.json` en `4ad7df10`) |
| 7. La salida del 422 de más de 10.000 días se sigue en pantalla | sí (§7) | `9156a5ac`, `9856ba26` → `4ad7df10` |
| 8. El selector de partida de las valuaciones ofrece cada renglón | sí (§8) | `741069ba` → `dbd78f3b` |
| 9. `cambios_entre` ve un cambio solo de especificaciones (el `_frente` de la línea 3; pedido del orquestador) | sí (§9 bis) | `9c472730` → `b9ef6a80` |
| Acta y congelado al día | sí (acta) | acta y `chore(experimento)` al final de la rama |

## 1. D-17: la fuente declarada de cada precio

**Qué se decidió.** «Sin referencia ni cotización: el precio no tiene fuente» sale solo si el precio no trae Ref, ni
cotización, ni una **fuente declarada**: la de su `PrecioOrigen` que no sea el `origen` de una lista que tiene ese insumo
sin `PrecioOrigen` propio (el texto que `core.catalog.origen.origenes_efectivos` le da como fuente a un precio sin fila y
que las copias de la lista arrastran a su propia fila).

**Cómo.** `aplicacion/hoja.py`: `_fuentes_heredadas(sesion, insumos)` (una consulta: `PrecioInsumo` ⋈ `ListaPrecios`
sin `PrecioOrigen`) y `_estado_de_precio(o, heredadas)`; `precios_de_version` las pasa. Ningún otro archivo.

**Simulación** (`sim_fuente.py`: la vivienda valorada con una lista de empresa en la que el cemento trae «Cotización
ficticia 17» en su fila y el agua la fuente de la lista escrita en su fila; lo demás, heredado de la lista base sembrada
sin `PrecioOrigen`; luego una cotización del andamio, que copia la lista):

| Precio | Lo correcto | Hoy (Ref o cotización) | A (fila con fuente) | C (no es el origen de ninguna lista) | **D (no es un origen heredado)** |
|---|---|---|---|---|---|
| Heredado de la lista base (11 insumos) | sin fuente | sin fuente | con fuente ✘ | sin fuente | sin fuente |
| Cemento, fuente propia en la fila | con fuente | sin fuente ✘ | con fuente | con fuente | con fuente |
| Agua, la fuente de la lista escrita en la fila | con fuente | sin fuente ✘ | con fuente | sin fuente ✘ | con fuente |
| En la copia de la cotización: cemento y agua | con fuente | sin fuente ✘ | con fuente | uno ✘ | con fuente |
| En la copia: heredados de la base | sin fuente | sin fuente | con fuente ✘ | sin fuente | sin fuente |

**Descartadas.** A: toda copia guarda una fila con la fuente heredada, así que todo pasaría por «con fuente» (es lo que
hizo retirar `249a32f2`). C: una fila de empresa cuya fuente coincide con la de su lista quedaría «sin fuente». La
vista (`hoja_vista`) no puede distinguir la propia de la heredada (bitácora de precios §4).

**Revertir.** Volver a `_estado_de_precio(o)` sin `heredadas` y quitar `_fuentes_heredadas` (exige otro re-congelado).
**Pruebas:** `tests/integration/test_precios_fuente_declarada.py` (3).

## 2. La primera versión directa también arma el plan que cabe

**Qué se decidió.** `hoja.con_plan_por_rendimientos` usa `plan_rendimientos.plan_que_cabe` (días → semanas → meses de 20
días hábiles, la primera que cabe en 500 períodos), como ya lo hacía la ruta del producto (`hoja_guardado`, D-2); si ni
en meses cabe, `HojaInvalida` con la salida (antes un `PlanDemasiadoLargo` sin convertir). La simulación es la de D-2
([precios §1](2026-11-13-e2e-precios.md)): 58 días → 58 «Dia n»; 654 → 131 «Semana n»; 3.054 → 153 «Mes n»; 10.055 → no
cabe. **Revertir:** volver a `plan_del_borrador` (re-congelado). **Pruebas:** `tests/unit/test_hoja_recongelado_2.py` (4).

## 3. Tildes de `hoja.py`

«+ Administración», «= Con administración», los dos 422 de guardar («por qué se cambia y con qué respaldo», «quién lo
hace») y los demás mensajes que quedaban (`_enum`, `_vertices`, `cambiar_insumo`, `plan_desde_filas`, `_altura`,
`_entero`, «los puntos máximos»). Los oráculos de 11 archivos de prueba pasan a los textos con tildes (`da399c05`). Los
datos de prueba del front que imitan el 422 viejo («por que se cambia») son textos del servidor falso y no cambian:
la interfaz muestra lo que el servidor manda. No hay decisión que simular (una sola opción correcta).

## 4. El Estado de un renglón no repite el hallazgo de otro renglón

**Qué se decidió.** Un hallazgo que cita el `origen_id` de alguno de los renglones es de ese renglón y no se reparte por
partida a los demás renglones del mismo código; uno que no cita ningún renglón (de la partida) sigue en todos.

**Simulación** (pruebas `test_hoja_recongelado_2.py`: OBRA-04 en tres renglones con un R1 cada uno, y un R5 de la partida):

| Caso | A: hoy (reparte siempre) | **B: no reparte si cita su renglón** | C: no repartir nunca por partida |
|---|---|---|---|
| Tres R1, uno por renglón | cada renglón dice los tres ✘ | cada uno el suyo | cada uno el suyo |
| R1 del renglón 2 con la partida declarada por la regla | los tres renglones ✘ | solo el 2 | solo el 2 |
| R5 de la partida, sin renglón | los tres | los tres | ninguno ✘ |

**Revertir:** quitar el `continue` de `renglones.intersection(...)` (re-congelado).

## 5. Un plan por meses o semanas se ve con su unidad

**Qué se decidió.** La pestaña «Plan y equilibrio» marca la unidad del plan por sus etiquetas («Semana n» → semanas,
«Mes n» → meses) y ofrece «Meses (20 días hábiles)» junto a días y semanas; la ruta `POST …/plan/rendimientos` acepta
`unidad: "mes"`. Antes un plan «Mes n» abría con «Días hábiles» marcado y no se podía rehacer por meses.

| Opción | Plan de 153 «Mes n» | Rehacerlo por meses |
|---|---|---|
| A: hoy | «Días hábiles» marcado ✘ | no ✘ |
| **B: unidad por la etiqueta + opción de meses** | «Meses» marcado | sí |
| C: decir la unidad en un texto, sin la opción | se lee | no ✘ |

**Cómo.** `PestanaPlan.tsx` (`unidadDelPlan`, `unidadElegida`, el radio), `api/esquemas_hoja.py` (`Literal[…, "mes"]`),
`api/rutas/hoja.py` (el texto de la forma). **Revertir:** quitar el radio y «mes» del `Literal`.

## 6. Control: los días por período salen del plan

**Qué se decidió.** Al declarar la línea base, «Días hábiles por período» se llena con lo que dice el plan de la
versión: «Dia n» (o «Día n») 1, «Semana n» 5, «Mes n» 20; si el plan mezcla unidades, usa otras etiquetas o no existe,
**20 (un mes) con un aviso** (lo que pidió el encargo, y la mitigación de Argon: el valor por omisión no se aplica en
silencio). Lo escrito manda; si el campo queda vacío (o falta en la petición), el servidor los toma del plan.

**Simulación** (`sim_dias.py`, inicio el 02/11/2026; Control cuenta cada período del plan como `dias_por_periodo` días
hábiles, `core.budget.calendario`):

| Plan de la versión | Real | Hoy: 5 a mano | A: 20 fijo | **B: del plan** |
|---|---|---|---|---|
| 58 «Dia n» | 58 d | 290 d, fin 10/12/2027 ✘ | 1.160 d ✘ | 58 d, fin 20/01/2027 ✔ |
| 131 «Semana n» | 655 d | 655 d ✔ | 2.620 d ✘ | 655 d ✔ |
| 153 «Mes n» | 3.060 d | 765 d ✘ | 3.060 d ✔ | 3.060 d ✔ |

Sin unidad reconocible: 20 (el encargo, «un mes»), 5 (el de antes) o exigirlo a mano. Se elige 20 con el aviso; Eugenio
puede cambiarlo en una línea (`DIAS_POR_OMISION`).

**Cómo.** `aplicacion/control.py` (`DIAS_POR_OMISION`, `DiasDelPlan`, `dias_de_las_etiquetas`,
`dias_por_periodo_del_plan`; `declarar_linea_base` con días en blanco), `api/rutas/control.py`
(`GET /v1/control/dias-por-periodo?proyecto=&version=` → `{dias, unidad, aviso}`, 404 si la versión no existe;
`DeclararLineaBase.dias_por_periodo` por omisión `""`), `paginas/control/PestanaLineaBase.tsx` (el campo, su ayuda y lo
escrito). **Revertir:** volver el valor por omisión a `"5"` en la API y en la pantalla y quitar la ruta.

## 7. La salida del 422 de más de 10.000 días se sigue en pantalla

**El defecto.** Guardar la primera versión de una obra que ni en meses cabe decía «en «Plan y equilibrio» cree el plan y
asigne más cuadrillas», pero la pestaña solo mostraba las cuadrillas con un plan hecho, y el plan no se podía hacer
porque no cabía: un callejón sin salida.

**Simulación** (`sim_salida.py`, la vivienda con OBRA-01 de 45.004,5 m3: 10.055 días hábiles con una cuadrilla):

| Unidad | 1 cuadrilla en OBRA-01 | 2 | 3 |
|---|---|---|---|
| Días | 10.055 períodos: 422 | 5.055: 422 | 3.388: 422 |
| Semanas | 2.011: 422 | 1.011: 422 | 678: 422 |
| Meses | 503: 422 | **253 períodos** | 170 |

Así que la salida existe (meses y dos cuadrillas) si la pantalla la permite:

| Opción | ¿Se sigue? |
|---|---|
| A: hoy | no: sin plan no hay cuadrillas ✘ |
| **B: cuadrillas también sin plan + «Meses»** | sí: poner 2 en OBRA-01, «Meses», «Plan desde los rendimientos», guardar |
| C: que el servidor suba las cuadrillas solo | decide por la persona y esconde el supuesto ✘ |
| D: hacer primero un plan por meses | no cabe (503 meses) ✘ |

**Cómo.** `aplicacion/hoja_vista.py`: `VistaPlan.partidas` (las del presupuesto, con plan o sin él); `api/esquemas_hoja.py`
(`VistaPlanRespuesta.partidas`); `PestanaPlan.tsx` toma `vista.partidas` (o las de la matriz, con un servidor
anterior). Los textos (`aplicacion/plan_rendimientos.py`) dicen lo que la pantalla permite: por días «elija semanas o
meses, o más cuadrillas.», por semanas «elija meses o más cuadrillas.», por meses «asigne más cuadrillas a las partidas
largas.»; el de la primera versión: «… en «Plan y equilibrio» asigne más cuadrillas a las partidas largas, haga el plan
desde los rendimientos por meses y vuelva a guardar.». **Revertir:** quitar `partidas` y volver los textos.

## 8. El selector de partida de las valuaciones ofrece cada renglón

**Qué se decidió.** `GET /v1/control/partidas` trae una fila por renglón del presupuesto de la línea base, en su orden,
con `renglon` (su número, desde 1) y `renglones` (cuántos tiene su código). La opción de un código repetido dice
«renglón n del presupuesto»; elegirla escribe el código y, con la observación vacía, «Renglón n»; la ayuda dice «N
renglones con este código: la valuación se revisa con su suma». **La valuación sigue siendo por código**: el núcleo
mide por código y suma sus renglones (`core.budget.valuaciones`, `PartidaBase`); dos líneas del mismo código en una
valuación se suman. Reajuste sigue con una por código (otro modelo de respuesta, `RenglonesDelContratoRespuesta`).

**Simulación** (OB-003 ficticia: OB-A en los renglones 1 y 3, «frente 2»):

| Opción | Quien mide el frente 2 ve | Queda dicho qué renglón midió |
|---|---|---|
| A: hoy, una por código | solo «Excavacion de zanja» (el frente 2 no aparece) ✘ | no ✘ |
| **B: una por renglón + «Renglón n» en la observación** | las dos, con su número | sí (la observación) |
| C: una por código con «2 renglones» | una sola, sin elegir el frente | no ✘ |

**Cómo.** `aplicacion/control.py` (`PartidaDelContrato.renglon/renglones`, `renglones_de_la_version`;
`partidas_de_la_linea_base` la usa), `api/esquemas_partidas.py` (`RenglonDelContratoRespuesta`,
`RenglonesDelContratoRespuesta`, `renglones_a_respuesta`), `api/rutas/control.py`, `comun/partidasDelContrato.ts`
(`codigoRepetido`, la opción), `comun/CampoDePartida.tsx` (`alElegirPartida`, la ayuda), `paginas/control/PestanaValuaciones.tsx`
(`elegirPartida`). **Revertir:** `partidas_de_la_linea_base` vuelve a `partidas_de_la_version` y la ruta a
`PartidasDelContratoRespuesta`; el front ignora los campos que no llegan.

**Lo que exigiría `core/` (expediente propuesto, no aplicado).** Argon advierte que con la valuación por código nadie
impide medir en un renglón más de lo que ese renglón tiene contratado mientras el código no se pase, y que si dos
renglones del mismo código tienen precios unitarios distintos la valuación por código es ambigua. Controlar el saldo por
renglón exige que `LineaValuacion` (`core/verification/valuaciones.py`) y `PartidaBase` (`core/budget/valuaciones.py`)
lleven el `origen_id` del renglón: regla genérica (cualquier presupuesto con un código repetido), prueba en rojo
propuesta: OB-A en dos renglones de 100 y 50, una valuación de 120 en el renglón 2 debe dar R13 por ese renglón (hoy
pasa porque 120 ≤ 150); impacto: las valuaciones guardadas (columna nueva, nula para las de antes), R13/R14 y el valor
ganado por renglón. Necesita el aval del tutor.

## 9 bis. Un cambio solo en las especificaciones de un renglón es un cambio

**El defecto** (pedido del orquestador): la línea 3 (`feature/libro-por-frentes`, aún no unida) guarda el frente de un
renglón como la directiva `_frente` de sus especificaciones, y `cambios_entre` no comparaba especificaciones: en una
versión ya guardada, poner solo frentes no habilitaba «Guardar» (y `guardar_version` devolvía `None`).

**Qué se decidió.** `cambios_entre` compara las especificaciones de cada renglón de la versión (`items_base`, no los
derivados del espacio, que ya cubre el metraje) que está antes y después: si difieren, un `CambioEditado` por renglón,
objeto `cantidad` (el renglón: `core.budget.edicion.OBJETOS` no se toca), campo `especificaciones` y los pares
`clave=valor` ordenados («_frente=Frente norte (ficticio)»). La interfaz ya rotula el campo «Especificaciones»
(`comun/rotulos.ts`).

**Simulación** (pruebas de `test_hoja_recongelado_2.py` y `test_aplicacion_hoja_guardado.py`, casos construidos a mano):

| Caso | Hoy | A: solo `_frente` | **B: cualquier clave** |
|---|---|---|---|
| Se pone solo el frente de un renglón | sin cambio ✘ (no se guarda) | cambio | cambio |
| Cambia otra especificación del renglón (una banda) | sin cambio ✘ (se pierde) | sin cambio ✘ | cambio |
| Las mismas especificaciones | sin cambio | sin cambio | sin cambio |
| TI-001: frente en el renglón 1, guardar y reabrir | `None` ✘ | TI-002 con el frente | TI-002 con el frente |

Se elige B: las especificaciones viajan con la versión guardada (`core.budget.persistencia`) y las reglas las leen
(VR4 la banda, VR3 el suministro), así que cualquier cambio en ellas cambia lo que se guarda; A dejaría perder los demás.
**Revertir:** quitar `_cambios_de_especificaciones` de `cambios_entre` (re-congelado).

## 9. Gemini por `agy`

- **gemini-4-argon-medium** (segunda opinión corta de las decisiones 1, 6, 7 y 8; encargo `l1/encargo_argon.md`):
  «de acuerdo» en las cuatro. Riesgos que dio: (1) colisión de textos (una fuente declarada igual al origen de otra lista
  del mismo insumo se leería heredada): se acepta, es raro y deja el aviso de siempre; (2) etiquetas con tilde o
  abreviadas caerían en 20 en silencio: se aceptan «Día n» y el 20 lleva aviso visible; (3) que el tope sea de períodos
  y no de días, y que no se pierdan las cuadrillas si vuelve a fallar: el tope es de períodos (la simulación lo muestra)
  y las cuadrillas viven en el estado de la pestaña; (4) el saldo por renglón: expediente de `core/` arriba.
- **gemini-4-hydrogen-high** y **gemini-3.8-flash-medium**: no se usaron; los parches eran pequeños y la máquina iba
  cargada por cuatro líneas en paralelo (una corrida de 906 pruebas tardó 27 minutos). Ningún modelo agotó el tiempo.

## 10. Verificación

- Rojo visto en cada paso (los mensajes de los commits `test(...)` dicen cuántas y por qué). Notas: el rojo de
  `test_control_dias_del_plan.py` fue de importación (la función nueva no existía); el de «lo que la persona escribe
  manda» (front de Control) y el de «sin días» por la API ya pasaban con el código anterior por coincidir con el 5 de
  antes, así que la prueba de la API manda `""` (antes 422).
- Verde: 81 + 906 pruebas de la Hoja, Precios, plan y experimento con el `hoja.py` nuevo; 375 de Control (UI, API,
  acceso por ruta, días del plan); 13 de partidas de Control y Reajuste; 233 de plan y `test_api_hoja.py` (y
  `test_docs_api_json_esta_al_dia` tras exportar `docs/api.json`); front: Control (66), partidas del contrato (16) y plan
  (10); `npm run lint` limpio (incluye `tsc -b --noEmit`).
- El experimento: huella de los hallazgos igual antes y después (acta).
