# Sílice S4: asistente con IA verificada (versión 0.9.0)

| Campo | Valor |
|---|---|
| Estado | **propuesta**, pendiente de la aprobación de Eugenio y de los cuatro encargos (requisitos, arquitectura, pruebas y calidad, verificador de hechos). La excepción a RNF‑08 y el experimento como indicador de la tesis necesitan además el visto bueno del tutor (§13) |
| Fecha | 2026‑10‑11 |
| Rama | spec en `inc/silice`; construcción en `inc/silice-s4` (worktree propio), apilada sobre la 0.8.0 (spec maestro §5) |
| Versión que entrega | **0.9.0** |
| Se apoya en | [spec maestro](2026-10-11-silice-1.0.0-design.md) (§3, §4, §7), [horizonte](2026-10-08-horizonte-reorientacion-design.md) (H‑D4, OE‑H2, §5, §6.1), [antecedentes](../tesis/antecedentes-reorientacion-2026-10-08.md) §1, [spec del sprint SF](2026-10-04-sprint-final-prototipo-design.md) (hoja, R8–R10, DA‑SF‑5/6/8) |
| Reemplaza | el diseño de [PLAN_ASISTENTE.md](../../PLAN_ASISTENTE.md) y de su spec retirada del 2026‑09‑15 (commit `545c4fb`). Se conserva su principio: **la IA interpreta y elige; el núcleo calcula y audita**. Cambia el destino de las propuestas (el borrador de la hoja, no un presupuesto aparte), el proveedor (dos, no uno) y la evaluación (un experimento, no umbrales sobre cuatro casos dorados). PLAN_ASISTENTE queda como el plan que fue (INV‑066) |
| Documentos que enmienda | [ERS](../ERS.md) (UC‑09, RF‑32, RF‑90…RF‑95, RNF‑08, RNF‑18), [arquitectura](../arquitectura.md), [modelo de datos](../modelo_datos.md) (tablas `ia_*`), [plan de pruebas](../plan_pruebas.md), [NORMAS.md](../../NORMAS.md) §6 |
| Naturaleza de los datos | [NORMAS.md §1](../../NORMAS.md): los casos son construidos; las tareas del experimento también lo son y se declaran (§9.2) |

Este documento es la **fuente única** del diseño de S4. El plan de sesiones se escribe después de aprobarlo y lo
enlaza; no lo repite.

---

## 1. Qué se quiere y por qué

**Pedido (spec maestro §2.1 y H‑D4).** Un asistente **independiente del proveedor** (Claude como principal y un
modelo local por Ollama sin conexión) que arma el presupuesto a partir de lo que el usuario escribe, y un
**experimento** que mida cuántos errores de cada modelo atrapa el auditor (OE‑H2, horizonte §6.1).

**Por qué es el aporte central.** Los antecedentes (§1) muestran LLM que estiman (Ghimire, Wu, Borkowski) y la
arquitectura neurosimbólica en estructuras (SYNAPSE 2026), pero ninguno que audite con reglas deterministas lo que
la IA propone para un presupuesto; OneEstimate vende «APU con IA» sin describir cómo los verifica. La novedad está
en la **verificación y la trazabilidad**, no en generar.

**Principio rector (invariante del diseño).** *La IA nunca escribe un número final.* Solo invoca herramientas del
sistema que **proponen datos de entrada** (ambientes, puntos, recorridos, partidas) en el **borrador** de la hoja.
Las cantidades derivadas, los precios, los APU, los totales, la curva y el punto de equilibrio los calcula el sistema
(`adapters.espacio.derivar`, `core.budget.elaborar`); el auditor (R1–R10) los revisa siempre; **el usuario
confirma** cada propuesta y **guarda** la versión con su nombre. Ninguna herramienta tiene un campo de precio, de
total ni de cantidad derivada: el esquema lo hace imposible, no una instrucción al modelo.

**Lo que hay en el repositorio (2026‑10‑11).**
- `ui/hoja.py` (sin Streamlit): `Borrador` inmutable, `espacio_desde_filas` (valida una fila como la edita el
  usuario y da `HojaInvalida` con la fila culpable), `elaborar_borrador` (deriva, valora, audita con
  `REGLAS + reglas_espacio`, calcula el PE y el Estado por fila) y `guardar_version` (exige fuente y responsable,
  una sola `Session`).
- `adapters/espacio`: modelo (`Ambiente`, `Fuente`, `Punto`, `Recorrido`, `Tramo`), `OrigenMedida` con
  `TipoOrigen` (plano, dxf, ifc, levantamiento, supuesto) y su referencia obligatoria; R8 marca ERROR un origen
  incompleto y ADVERTENCIA un supuesto.
- `ml/normalization`: `proponedor(partidas)` sobre `NormalizadorPartidas.similares` (UC‑03), con modelo local de
  `sentence-transformers` (módulo opcional del instalador, spec maestro §3).
- `core/verification`: `auditar` y `REGLAS` (R1–R7). R1 ya **advierte** toda cantidad `OrigenTipo.MANUAL` sin regla.
- `core/contracts/item_computo.OrigenTipo` (IFC, REGLA, TABULAR, CSV, MANUAL) **no** distingue una cantidad propuesta
  por una IA. Es el hallazgo de contrato que ya señalaba la spec de 2026‑09‑15; aquí se resuelve sin tocar el
  núcleo (§5.4, RS4‑3).
- No existe código del asistente, ni el SDK `anthropic`, ni `ollama`, ni `keyring` en `pyproject.toml`.

## 2. Alcance

**Dentro:** el caso de uso UC‑09 sobre la hoja del proyecto; las especialidades de la hoja (agua, datos,
electricidad) y las partidas del catálogo que no vienen del espacio (equipos, como en TI‑001); dos proveedores
(Claude por la API de Anthropic y un modelo local servido por Ollama); la clave de cada empresa guardada protegida;
la minimización de lo que viaja; el registro de cada sesión del asistente; el experimento y su protocolo.

**Fuera:** que la IA fije precios, cantidades derivadas o totales (nunca); que la IA guarde una versión (siempre la
guarda una persona); agentes alojados por el proveedor (Managed Agents: el catálogo y la hoja viven en el equipo de
la empresa, como ya descartó la spec de 2026‑09‑15); leer planos o imágenes con la IA; entrenar un modelo propio
(las salidas de la IA nunca cuentan para la compuerta G2, PLAN_ASISTENTE principio 5); un tercer proveedor (la
interfaz lo permite, pero no se construye ni se prueba).

## 3. Requisitos (enmienda a la ERS, IEEE 830)

**Numeración asignada.** UC‑09 (reservado al asistente desde P0.1), **RF‑32** (vacante reservado a UC‑09) y
**RF‑90 a RF‑95**; **RNF‑18**; expediente **SL‑E10** solo si hubiera que tocar `core/`. Se usan UC‑09, RF‑32,
RF‑90…RF‑95 y RNF‑18. **SL‑E10 queda vacante**: este diseño no cambia el núcleo (§5.4). La nota de la ERS que
mandaba los RF de UC‑09 «a partir de RF‑64» se enmienda: queda RF‑32 más RF‑90…RF‑95, por la numeración del spec
maestro. Los conteos de la ERS los ajusta S4.0 con los de S1–S3 ya enmendados.

### 3.1 UC‑09 Armar el presupuesto con el asistente de IA

| Campo | Contenido |
|---|---|
| Actor principal | **quien arma** (proyectista o estimador; rol de S3) |
| Actores secundarios | el **proveedor de IA** (sistema externo en modo nube, proceso local en modo local); el **administrador de la instalación**, que activa el asistente, registra la clave de la empresa y fija el tope de costo |
| Precondiciones | sesión iniciada con rol *quien arma* (S3); proyecto abierto en la hoja (UC‑15) en una versión que no esté en solo lectura; al menos un proveedor **disponible** (§5.3) |
| Disparador | el usuario escribe su pedido en lenguaje natural («baño de 2 × 1,5 m con lavamanos, poceta y ducha; oficina contigua con 4 puntos de datos») |

**Flujo principal.**
1. El usuario abre el panel del asistente en la hoja, elige el proveedor (o queda el de la instalación) y ve la
   **vista previa de lo que se enviará** (§8.2) y la **estimación de costo** (§8.4).
2. Escribe el pedido y pulsa *Proponer*. El sistema abre una **sesión del asistente** (registro en `ia_*`, §5.5).
3. El modelo consulta el borrador y busca partidas con las herramientas de lectura (§6).
4. El modelo propone ambientes, fuentes, puntos, recorridos y partidas con las herramientas de propuesta. Cada
   llamada se **valida** (esquema Pydantic, validación semántica y construcción del modelo espacial, §7) antes de
   quedar como **propuesta pendiente**; una llamada inválida se devuelve al modelo con el motivo.
5. El sistema muestra las propuestas pendientes como un **diff del borrador**, y el resultado que tendrían: presupuesto,
   informe de auditoría completo y Estado por fila, calculados por el sistema sobre un borrador hipotético.
6. El usuario **acepta, edita o rechaza** cada propuesta. Las aceptadas entran al borrador con **origen «propuesta de
   IA»** (§5.4). El borrador se recalcula y se audita (RF‑52): el informe se genera siempre (NORMAS §2.7).
7. El usuario guarda la versión por el camino de siempre (UC‑15, RF‑53): `guardar_version` exige **fuente** (el
   sistema la prellena: «propuesta de IA, sesión N, proveedor y modelo») y **responsable** (el usuario que inició
   sesión). La IA nunca es responsable.

**Flujos alternos.**

| # | Condición | Comportamiento |
|---|---|---|
| 9a | modo nube sin conexión, sin clave o con la clave rechazada | el sistema lo dice con un mensaje claro y ofrece el modo local si está disponible; nunca reintenta en silencio con otro proveedor (RS4‑5) |
| 9b | modo local: el servicio de Ollama no responde o el modelo no está instalado | mensaje con lo que falta; el asistente queda inactivo; la hoja sigue funcionando a mano |
| 9c | una llamada no pasa la validación (§7) | no toca el borrador; el motivo vuelve al modelo como error de la herramienta; tras **3** rechazos seguidos de la misma herramienta la sesión se detiene y lo informa |
| 9d | una necesidad sin partida en el catálogo | el modelo la declara con `declarar_sin_partida`; queda en el informe de la sesión como pendiente (UC‑03 / RF‑16); **no se inventa** una partida |
| 9e | el proveedor rechaza el pedido (`refusal` en Claude) | se informa con la categoría si existe; las propuestas ya validadas se conservan |
| 9f | se alcanza el tope de turnos, de llamadas o de costo de la sesión (§8.4) | la sesión se detiene y conserva las propuestas válidas; el usuario puede abrir otra |
| 9g | el modelo pregunta (`preguntar_al_usuario`) | el turno espera la respuesta del usuario, que entra al registro como parte del pedido (sus cifras se pueden citar, §7.3) |
| 9h | el usuario rechaza todo o cancela | el borrador queda idéntico al de antes de la sesión; el registro de la sesión se conserva |
| 9i | la versión abierta está en solo lectura (UC‑15e) | el asistente no se abre; se explica por qué |
| 9j | respuesta cortada por el límite de salida (`max_tokens`) o turno mal formado | el turno se descarta entero (no se aplican llamadas a medias) y se informa |

**Postcondiciones.** Nada se persiste en el presupuesto sin la confirmación y el guardado del usuario. Toda fila
aceptada cita su origen «propuesta de IA». El registro de la sesión (pedido, turnos, llamadas, validaciones,
decisiones, proveedor, modelo, uso y costo) queda guardado aunque no se guarde la versión.

### 3.2 Requisitos funcionales

Prioridad: E = esencial, D = deseable. Fases en §11.

| RF | Requisito | UC | Pri. | Fase | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑32 | El asistente recibe un pedido en lenguaje natural sobre el proyecto abierto y responde **solo con propuestas** sobre el borrador de la hoja, mediante las herramientas de §6 | UC‑09 | E | S4.2 | con el proveedor guionado (§10.1), un pedido produce propuestas pendientes y **ningún cambio** en el borrador hasta que el usuario acepta |
| RF‑90 | Una interfaz común de proveedor (`ProveedorIA`, §5.3) con dos implementaciones, Claude (API de Anthropic, uso de herramientas) y un modelo local por Ollama; elección por instalación y por sesión; si el proveedor elegido no está disponible, se ofrece el otro sin cambiar de proveedor a mitad de una sesión | UC‑09 | E (Claude), D (local) | S4.2 | las mismas pruebas de contrato pasan con los dos adaptadores sobre respuestas grabadas; sin conexión se ofrece el local (9a) |
| RF‑91 | Cada llamada del modelo se valida antes de tocar el borrador: esquema Pydantic estricto, validación semántica y construcción del modelo espacial (§7); todo dato numérico de entrada trae **cita literal** del pedido o **supuesto declarado**; no existe campo de precio, total ni cantidad derivada | UC‑09 | E | S4.1 | cada causa de rechazo de §7.4 tiene su prueba con el caso frontera; un número sin cita no entra |
| RF‑92 | Las propuestas quedan pendientes, el usuario las acepta, edita o rechaza una por una, y las aceptadas entran al borrador con **origen «propuesta de IA»**; el borrador se audita con R1–R10 siempre; guardar exige fuente y responsable humano | UC‑09, UC‑15 | E | S4.1, S4.3 | una propuesta rechazada deja el borrador igual (comparación exacta); una aceptada aparece con su origen en la hoja, en el Estado y en el Excel; la versión guardada lleva el `RegistroCambio` con la fuente de la sesión |
| RF‑93 | Registro de cada sesión del asistente (`ia_*`): pedido, turnos, llamadas con su resultado de validación, decisiones del usuario, proveedor, modelo que respondió, uso de tokens y costo estimado | UC‑09 | E | S4.2 | una sesión guionada deja exactamente las filas esperadas, en orden; la clave nunca aparece (RNF‑18) |
| RF‑94 | Privacidad: vista previa de lo que se enviará, minimización (§8.2), modo local sin envío fuera del equipo, clave de cada empresa protegida (§8.3) y tope de costo por sesión | UC‑09 | E | S4.2, S4.3 | la instantánea de lo enviado para el borrador de prueba coincide con la lista blanca de §8.2; RNF‑18 |
| RF‑95 | El experimento de §9: banco de tareas de referencia congelado, corrida reproducible con los dos proveedores y cálculo de las métricas, que genera `docs/resultados_asistente.md` | — (tesis, OE‑H2) | E para la tesis, D para el producto | S4.0, S4.4 | el script de métricas, con corridas de prueba hechas a mano, da las cifras calculadas a mano (oráculo independiente, §10.1) |

### 3.3 Requisitos no funcionales

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑18 | Seguridad (confidencialidad) | **(a)** En modo local, cero conexiones fuera del equipo: el anfitrión de Ollama debe ser de bucle local (`localhost`, `127.0.0.1`, `::1`); si no lo es, se trata como modo nube y se avisa. **(b)** En modo nube, solo viaja lo de la lista blanca de §8.2. **(c)** La clave de la empresa nunca aparece en la base, en el registro `ia_*`, en los registros de la aplicación, en `st.session_state`, en el Excel ni en el paquete auditado, y la pantalla nunca la muestra completa. **(d)** Ninguna prueba de la CI abre la red | pruebas por caso (§10.1): guardia de sockets en las pruebas del asistente; búsqueda de la clave de prueba en todos esos destinos tras una sesión; instantánea de lo enviado |

**Enmienda a RNF‑08** (ejecución local, sin servicios externos). Se agrega una **tercera excepción declarada**: el
asistente en **modo nube**, apagado por defecto, que solo se activa cuando el administrador de la instalación
registra la clave de su empresa; envía al proveedor lo de §8.2 y nada más. El modo local no es excepción. Necesita
el visto bueno del tutor, como lo necesitaba DA‑2 en 2026‑09‑15.

## 4. Enfoques considerados

| Enfoque | Veredicto |
|---|---|
| **A. Bucle de herramientas propio, neutral al proveedor, que propone en el borrador** | **Elegido.** Un solo bucle (`asistente/orquestador.py`) para los dos proveedores; cada adaptador traduce mensajes y herramientas. Toda propuesta entra por la misma puerta que una edición a mano (`espacio_desde_filas`) y pasa por el mismo auditor |
| B. Tool Runner del SDK de Anthropic | Descartado como bucle principal: es solo de Claude (el modelo local necesitaría otro bucle, y el experimento compararía dos bucles distintos) y es beta. Sus ganchos por turno serían suficientes para las aprobaciones, pero no para la neutralidad |
| C. Una sola llamada con salida estructurada que devuelve el presupuesto entero | Descartado (ya lo estaba en 2026‑09‑15): el modelo escribiría cantidades y precios sin trazabilidad |
| D. Agentes alojados por el proveedor | Descartado: habría que subir el catálogo y la hoja; contradice S‑D3 (instalación local) y empeora RNF‑08 |

## 5. Arquitectura (vistas 4+1)

### 5.1 Principio que se conserva

NORMAS §2: núcleo cerrado, adaptadores abiertos. **La IA no vive en `core/` y el núcleo no la conoce.** Tampoco puede
vivir en `adapters/`: un adaptador solo importa `core.contracts`, y el asistente necesita la lógica de la hoja
(`ui.hoja`), el catálogo y la similitud de partidas. Va en un **paquete nuevo de primer nivel, `asistente/`**, del
mismo rango que `api/` y `ui/` (como proponía la spec de 2026‑09‑15). Lo único que S4 agrega en `adapters/` es lo
propio de la hoja de metrajes: el tipo de origen «propuesta de IA» y su lectura en R8 (§5.4).

### 5.2 Vista lógica

| Paquete o módulo | Qué contiene | Importa | Toca `core/` |
|---|---|---|---|
| `asistente/proveedores/base.py` | `ProveedorIA` (Protocol), tipos neutrales: `Mensaje`, `LlamadaHerramienta`, `Turno`, `FinTurno`, `Uso`, `Disponibilidad` | biblioteca estándar | no |
| `asistente/proveedores/claude.py` | adaptador de Claude con el SDK oficial `anthropic` (import diferido, extra `ia`) | `anthropic`, `base` | no |
| `asistente/proveedores/ollama_local.py` | adaptador del modelo local con el cliente oficial de Ollama para Python (a confirmar en S4.0) | `ollama` (a confirmar), `base` | no |
| `asistente/proveedores/guionado.py` | doble de prueba: reproduce turnos grabados (JSON) | `base` | no |
| `asistente/herramientas.py` | modelos Pydantic de cada herramienta (§6), su esquema JSON y su ejecución | `pydantic`, `ui.hoja`, `adapters.espacio`, `ml.normalization` (opcional) | no |
| `asistente/validacion.py` | validación semántica y de citas (§7) | `asistente.herramientas` | no |
| `asistente/propuestas.py` | lista de propuestas pendientes; aplicar las aceptadas al `Borrador` (`dataclasses.replace`) | `ui.hoja`, `adapters.espacio` | no |
| `asistente/orquestador.py` | el bucle de §5.3, topes, registro | todos los anteriores | no |
| `asistente/privacidad.py` | lista blanca y vista previa de lo enviado (§8.2) | `ui.hoja` | no |
| `asistente/clave.py` | guardar y leer la clave de la empresa (§8.3) | `keyring` (a confirmar) | no |
| `asistente/registro.py` | tablas `ia_*` y su escritura | `sqlalchemy` | no |
| `asistente/experimento/` | banco de tareas, comparador con la referencia y métricas (§9) | `asistente`, `ui.hoja` | no |
| `adapters/espacio/origen.py` | `TipoOrigen.IA` y su referencia obligatoria (§5.4) | — | no |
| `adapters/espacio/reglas.py` | R8 lee los supuestos de un origen IA (§5.4) | `core.contracts` | no |
| `ui/paginas/hoja.py` | panel del asistente: pedido, vista previa, costo, diff de propuestas, aceptar o rechazar | `asistente`, `ui.hoja` | no |
| `ui/paginas/configuracion` (de S3/S5) | activar el asistente, registrar la clave, elegir proveedor y modelo, tope de costo (solo el administrador de la instalación) | `asistente.clave` | no |

**Guardia de arquitectura** (`tests/unit/test_arquitectura.py`, ampliada en S4.1): `asistente` entra en
`PAQUETES_FUERA_DEL_NUCLEO` (el núcleo no lo importa); `ui/hoja.py` y `adapters/` no importan `asistente`; de `ui`,
`asistente` solo importa `ui.hoja`; `asistente` no importa `streamlit`; `anthropic` solo se importa en
`asistente/proveedores/claude.py` y el cliente de Ollama solo en `ollama_local.py`.

### 5.3 Vista de procesos: el bucle neutral

```
ProveedorIA (Protocol)
  nombre, modelo, envia_fuera_del_equipo: bool
  disponible() -> Disponibilidad            # clave presente / servicio local arriba y modelo instalado
  turno(sistema, mensajes, herramientas) -> Turno
Turno: texto, llamadas: tuple[LlamadaHerramienta], fin: FinTurno {FIN, HERRAMIENTAS, LIMITE, RECHAZO},
       uso: Uso(entrada, salida, cache_lectura, cache_escritura), modelo_que_respondio, crudo (opaco)

orquestador.ejecutar(sesion, pedido, borrador, proveedor, topes):
  repetir hasta FIN, tope de turnos (12), de llamadas (60) o de costo:
    turno = proveedor.turno(...)                      # el historial es SOLO de agregar (append-only)
    registrar turno y uso
    si turno.fin es LIMITE o RECHAZO: descartar el turno, informar (9e, 9j), terminar
    para cada llamada, en su orden:
      validar (esquema -> semántica -> citas -> construcción del modelo espacial)   # §7
      si es de lectura: ejecutar y devolver el resultado minimizado (§8.2)
      si es de propuesta y es válida: agregarla a las pendientes; devolver su id
      si no es válida: devolver el motivo como error de la herramienta (9c)
    devolver TODOS los resultados del turno en un solo mensaje
  -> propuestas pendientes + resultado hipotético (elaborar_borrador sobre borrador + pendientes)
```

- **Un proveedor por sesión (RS4‑5).** El historial de Claude guarda los bloques del modelo tal como llegaron
  (`Turno.crudo`); con los modelos vigentes los bloques de razonamiento están atados al modelo y a la conversación, y
  editar o mezclar el historial los invalida. Cambiar de proveedor abre **otra sesión** con el mismo pedido y el
  borrador vigente; nunca se mezclan transcripciones.
- **Determinismo del lado del sistema.** Mismo guion grabado → mismas propuestas, mismo orden, mismo registro. El
  modelo real no es determinista (en Claude Opus 5.5 no se fijan parámetros de muestreo); el experimento lo trata
  con repeticiones (§9.4).
- **Rendimiento.** `pedir_informe_auditoria` y el resultado hipotético usan `elaborar_borrador`, sujeto a RNF‑11
  (≤ 2 s con 500 puntos); el bucle no agrega cálculo propio.

### 5.4 Origen «propuesta de IA» sin tocar el núcleo

| Dónde | Cómo se marca | Quién lo lee |
|---|---|---|
| Filas del espacio (ambientes, fuentes, puntos, recorridos) | un `OrigenMedida` por propuesta aceptada con **`TipoOrigen.IA`** (nuevo, en `adapters/espacio/origen.py`), referencia obligatoria `proveedor`, `modelo`, `sesion`, `propuesta`; opcional `supuestos` (campos que el modelo supuso, con su motivo) | R8: referencia incompleta → ERROR (como cualquier origen); con `supuestos` → **ADVERTENCIA** por campo supuesto («alto supuesto por la IA: …»); sin supuestos y completa → sin hallazgo. La hoja muestra «Propuesta de IA» como rótulo del tipo |
| Partidas que no vienen del espacio | `ItemComputo` en `Borrador.items_base` con `origen_tipo = MANUAL` y `origen_id = "ia:<sesion>:<propuesta>"`; sin texto en `parametros` (DA‑SF‑8) ni en `especificaciones` | R1 ya advierte toda cantidad MANUAL sin regla; el Estado y la pestaña de trazabilidad muestran «Propuesta de IA» por el prefijo `ia:` y la fila de `ia_propuestas` |
| La versión guardada | `RegistroCambio.fuente` = «propuesta de IA, sesión N, <proveedor>/<modelo>»; `responsable` = usuario | trazabilidad de UC‑15; paquete auditado de S3 |

**Por qué no `OrigenTipo.IA` en `core/contracts`.** Sería un cambio aditivo al contrato congelado (NORMAS §5) y
abriría el expediente SL‑E10. Con el prefijo `ia:` y el registro `ia_*` la procedencia queda completa y R1 ya trata
esas cantidades como no derivables. **Costo (RS4‑3):** el núcleo no distingue «manual de una persona» de «manual de
la IA» al agrupar hallazgos; si los encargos o el tutor lo exigen, SL‑E10 se abre con su TDD y su rama de núcleo.

### 5.5 Vista de desarrollo y física

- **Dependencias** en un extra `ia` de `pyproject.toml`: `anthropic` (SDK oficial; versión fijada en S4.0),
  cliente oficial de Ollama para Python (a confirmar nombre, licencia y versión en S4.0), `keyring` (a confirmar
  licencia y backend de Windows en S4.0). `pydantic` ya está. La CI instala todos los extras (`uv sync
  --all-extras`): **ninguna prueba se omite** por falta del extra.
- **Persistencia:** tablas aditivas propias del asistente en el SQLite del caso, creadas por
  `crear_esquema_asistente()` (como `esp_*`, sin clave foránea a `core/models`): `ia_sesiones` (proyecto, versión
  de partida, proveedor, modelo pedido, inicio, fin, motivo de fin, topes), `ia_turnos` (orden, modelo que
  respondió, fin, uso, costo estimado, texto del modelo), `ia_llamadas` (herramienta, argumentos en JSON con claves
  ordenadas, resultado de la validación, motivo), `ia_propuestas` (id, tipo, estado: pendiente, aceptada, editada,
  rechazada; quién y cuándo). Si S5 introduce Alembic antes de construir S4, estas tablas entran como migración.
- **Red:** modo nube = HTTPS al proveedor (único destino); modo local = HTTP al servicio de Ollama en el bucle
  local (puerto por defecto a confirmar en S4.0).
- **Paquete auditado (S3):** las filas con origen IA viajan como cualquier fila; el registro `ia_*` de las sesiones
  cuyas propuestas se aceptaron viaja en el paquete **sin** uso ni costo (pregunta abierta 4).

## 6. Herramientas expuestas al modelo

Reglas comunes:
- Nombres en español sin tildes; esquemas generados desde los modelos Pydantic (`model_json_schema`), con
  `extra="forbid"` (→ `additionalProperties: false`) y **todos los campos requeridos** (los opcionales son
  requeridos y admiten `null`), como pide el modo estricto de Claude.
- **Números como texto decimal** (`"2.40"` o `"2,40"`, hasta 3 decimales, patrón `^-?\d{1,4}([.,]\d{1,3})?$`; las
  dimensiones, además, positivas) que el sistema convierte a `Decimal`; nunca `float` (NORMAS §2.3). Qué palabras clave de JSON Schema acepta el modo
  estricto (p. ej. `pattern`) está **a confirmar en S4.0**: lo que no acepte se valida solo del lado del sistema.
- Las herramientas de propuesta escriben **filas como las de la hoja** (`ui.hoja.COLUMNAS`), de modo que pasan por
  `espacio_desde_filas`, la misma puerta que una edición a mano.
- Todo dato numérico de una propuesta lleva `citas` o `supuestos` (§7.3).
- Orden de la lista de herramientas fijo y JSON con claves ordenadas (estabilidad de la caché, §8.4).

| Herramienta | Tipo | Argumentos (todos requeridos; `?` = admite `null`) | Devuelve al modelo |
|---|---|---|---|
| `consultar_borrador` | lectura | — | resumen minimizado del borrador (§8.2): ambientes, fuentes, puntos y recorridos con ids y geometría; partidas de `items_base` con código, descripción, unidad y cantidad; ids ya usados. Sin precios, montos ni nombres |
| `buscar_partidas` | lectura | `texto`, `especialidad?` (`agua`, `datos`, `electricidad`), `cuantos` (1–10) | código, descripción, unidad y puntaje de similitud (UC‑03, `ml.normalization.proponedor`); si el módulo opcional de similitud no está instalado, búsqueda por palabras declarada como tal. Nunca precios |
| `consultar_partida` | lectura | `codigo` | descripción, unidad y tipos de insumo de la composición, **sin cantidades ni precios** |
| `proponer_ambiente` | propuesta | `id`, `nombre`, `x0`, `y0`, `largo`, `ancho`, `alto`, `citas`, `supuestos` | id de la propuesta o motivo del rechazo |
| `proponer_fuente` | propuesta | `id`, `especialidad`, `tipo` (`TipoFuente`), `ambiente_id`, `x`, `y`, `z`, `citas`, `supuestos` | ídem |
| `proponer_punto` | propuesta | `id`, `nombre`, `especialidad`, `tipo` (`TipoPunto`), `ambiente_id`, `superficie`, `x`, `y`, `z`, `fuente_id?`, `circuito_id?`, `especificaciones` (pares de la lista cerrada de la especialidad), `citas`, `supuestos` | ídem |
| `proponer_recorrido` | propuesta | `punto_id?`, `circuito_id?`, `modo` (`propuesto` o `declarado`), `tramos?` (solo si `declarado`: orden, superficie, vértices), `citas`, `supuestos` | ídem. Con `propuesto` el sistema calcula el camino (spec SF §6.4) |
| `proponer_partida` | propuesta | `codigo`, `unidad`, `cantidad`, `citas`, `supuestos` | ídem; solo para partidas que **no** derivan del espacio (equipos, como en TI‑001) |
| `declarar_sin_partida` | propuesta | `necesidad` (texto del pedido) | queda como pendiente de UC‑03 (9d) |
| `retirar_propuesta` | propuesta | `propuesta_id` | confirmación |
| `pedir_informe_auditoria` | lectura | — | informe del borrador **hipotético** (borrador + pendientes), minimizado (§8.2). Se desactiva en la condición A del experimento (§9.3) |
| `preguntar_al_usuario` | control | `pregunta` | la respuesta del usuario (9g) |
| `terminar` | control | `notas` (lista de hasta 10 textos de ≤ 200 caracteres, sin montos de dinero) | fin de la sesión |

`citas` = lista de `{campo, texto}`; `supuestos` = lista de `{campo, motivo}`. No hay herramienta que guarde, borre
una versión, cambie parámetros de costo (FCAS, administración, utilidad), precios, cotizaciones ni planes: eso
queda para la persona (UC‑15).

## 7. Validación de cada llamada

### 7.1 Capa 1: esquema (Pydantic)

`Modelo.model_validate(argumentos)` con `extra="forbid"` y tipos cerrados (enumeraciones de `adapters.espacio`).
Para Claude se declara además `strict: true` en cada herramienta: el proveedor ya garantiza el esquema, pero el
sistema **vuelve a validar siempre** (el modelo local no lo garantiza, y con entrada transmitida por partes el SDK
puede entregar argumentos truncados).

### 7.2 Capa 2: semántica

Ids nuevos no repetidos ni en el borrador ni en las pendientes; toda referencia (`ambiente_id`, `fuente_id`,
`circuito_id`, `punto_id`) existe en el borrador o en las pendientes; el código de partida existe en el catálogo
vigente; la unidad de `proponer_partida` es equivalente a la de la partida (`core.contracts.unidades`); la
especialidad del punto coincide con la de su fuente.

### 7.3 Capa 3: citas y supuestos (la guarda contra el número inventado)

Para cada campo numérico de la llamada:
- si tiene **cita**, el `texto` debe aparecer **literalmente** en el pedido o en una respuesta del usuario de la
  misma sesión (comparación tras normalizar espacios y la coma decimal), y el número del campo debe aparecer dentro
  de esa cita, con una conversión de unidades de la lista cerrada (cm → m, mm → m);
- si no tiene cita, debe tener **supuesto** con motivo no vacío; el supuesto queda en la referencia del origen IA y
  R8 lo marca ADVERTENCIA (§5.4);
- un campo sin cita ni supuesto → rechazo.

Las coordenadas que el usuario no da (x0, y0, posición de un punto) son supuestos legítimos («esquina del baño en
el origen»): quedan visibles y marcados, no ocultos.

### 7.4 Capa 4: construcción del modelo

La fila se arma como la edita el usuario y pasa por `espacio_desde_filas` sobre borrador + pendientes; un
`HojaInvalida` (dimensión no positiva, enumeración inválida, vértices mal escritos) es rechazo con el texto de la
hoja. Los errores **geométricos** que el modelo admite (un punto fuera de su ambiente) **no** se rechazan aquí: son
de R9 y se dejan al auditor, porque eso es lo que mide el experimento.

**Causas de rechazo (catálogo cerrado, una prueba cada una):** campo extra; campo faltante; tipo o enumeración
inválidos; número con más de 3 decimales o con formato inválido; id repetido; referencia inexistente; código de
partida inexistente; unidad no equivalente; número sin cita ni supuesto; cita no literal; número ausente de su cita;
fila que la hoja no construye; texto de `terminar` con montos.

## 8. Privacidad, clave y costo

### 8.1 Qué se envía y qué no

| Se envía (modo nube) | No se envía nunca |
|---|---|
| las instrucciones del sistema y los esquemas de las herramientas (fijos, versionados) | precios, montos, totales, APU, curva, punto de equilibrio, cotizaciones, listas de precios |
| el pedido y las respuestas del usuario, **tal como los escribe** (la vista previa lo advierte) | nombre del proyecto (se envía un alias `P1`), nombre de la empresa, de usuarios o del cliente |
| el resumen del borrador de `consultar_borrador` (ids, geometría, códigos, descripciones, unidades, cantidades) | archivos: planos, Excel, PDF de MaPreX o de terceros, el paquete |
| descripciones y unidades de **hasta 10** partidas candidatas por búsqueda | el catálogo completo |
| hallazgos minimizados: regla, severidad, claves de fila y descripción; en R2 y R7 la descripción se reemplaza por un texto fijo sin montos; el campo `impacto` nunca | la clave de la empresa (va en el encabezado de autenticación del SDK, nunca en el contenido), el registro `ia_*`, otras versiones |

**Modo local:** lo mismo se envía al proceso de Ollama **dentro del equipo**; nada sale (RNF‑18 a).

**Límite declarado:** el sistema no filtra datos personales que el usuario escriba en el pedido; la vista previa lo
avisa. Retención y uso de los datos por el proveedor: se declaran con la política vigente del proveedor al
construir (a citar en S4.0, con fecha), no se afirman aquí.

### 8.2 Vista previa

Antes del primer envío de cada sesión, el panel muestra el texto exacto del primer mensaje (pedido + resumen del
borrador) y el destino («Anthropic, en internet» o «este equipo»). Las herramientas de lectura posteriores envían
solo lo de la lista blanca; `asistente/privacidad.py` es su única definición y la prueba de instantánea la congela.

### 8.3 Clave de la empresa

- La registra solo el **administrador de la instalación** (rol de S3); cada empresa pone la suya (spec maestro §4).
- Se guarda con `keyring` en el almacén de credenciales del sistema operativo (en Windows, el Administrador de
  credenciales), bajo un servicio `silice-ia` y el id de la empresa (backend y comportamiento **a confirmar** en
  S4.0 en el equipo de destino). **Respaldo** si el almacén no está disponible (p. ej. servicio sin sesión de
  usuario): la clave se cifra con `cryptography` (ya entra en S3) con una contraseña propia, como la clave privada
  de firma, y se pide al arrancar el asistente. Nunca en texto plano en la base, en archivos de configuración ni en
  variables de entorno escritas por el sistema.
- La pantalla muestra solo los últimos 4 caracteres; los registros de la aplicación la enmascaran; una excepción del
  SDK se registra sin encabezados.

### 8.4 Costo por uso, declarado

**Precios** (fuente: tabla de modelos del skill `claude-api`, en caché al 2026‑09‑25; **se reverifican en S4.0**
contra la página oficial de precios y se guardan con fecha en un archivo de configuración, no en el código):

| Modelo | Id | Entrada (USD por millón) | Salida | Lectura de caché |
|---|---|---|---|---|
| Claude Opus 5.5 (por defecto) | `claude-opus-5-5` | 4,00 | 20,00 | 0,20 |
| Modelo local por Ollama | a elegir en S4.0 | 0 (sin API); se registra tiempo y equipo | — | — |

**Estimación por tarea (cota superior, a reemplazar por la medición del piloto):** ≤ 12 turnos; entrada ≈ 16 000
tokens por turno, de los que ≈ 6 000 (instrucciones y esquemas) se leen de la caché; salida ≈ 3 000 tokens por turno
contando el razonamiento. Entrada sin caché 12 × 10 000 × 4 / 10⁶ = 0,48 USD; caché 12 × 6 000 × 0,20 / 10⁶ ≈
0,01 USD; salida 12 × 3 000 × 20 / 10⁶ = 0,72 USD. **≈ 1,21 USD por tarea**, sin contar la escritura inicial de la
caché. El panel muestra antes de enviar esta estimación y, después de cada turno, el costo real calculado con el
`uso` que devuelve la API. **Tope por sesión** fijado por el administrador (propuesta: 2 USD); al alcanzarlo, 9f.

**Ahorros que se aplican:** caché de prompt sobre herramientas e instrucciones (orden fijo, JSON ordenado, nada
variable antes del punto de corte; se verifica con `cache_read_input_tokens` en la prueba manual); topes de turnos y
de llamadas; resultados de herramientas minimizados.

### 8.5 Parámetros del adaptador de Claude (del skill `claude-api`, a reverificar en S4.0)

Modelo `claude-opus-5-5`; razonamiento adaptativo (en este modelo no se puede desactivar) con **esfuerzo fijado
explícitamente** (propuesta: `high`; su valor por defecto es `medium`); `tool_choice` automático (el forzado devuelve
400 en este modelo; se guía con las instrucciones y `strict: true`); se comprueba `stop_reason` antes de leer
(`tool_use`, `end_turn`, `max_tokens`, `refusal` con `stop_details`); el contenido completo del turno se agrega al
historial sin editarlo; varias llamadas de un turno se responden en un solo mensaje, con `is_error` para las
rechazadas; errores del SDK capturados del más específico al más general (autenticación → clave inválida; límite de
tasa y 5xx → reintento del SDK; conexión → 9a). **Respaldo del lado del servidor ante un rechazo** (`fallbacks`):
activado en el producto y **declarado al usuario**, con el modelo que respondió registrado; **desactivado en el
experimento**, donde un rechazo se cuenta como tal (RS4‑7). Ninguna firma del SDK se escribe de memoria: S4.2 relee
el skill antes de programar.

### 8.6 Modelo local por Ollama (todo **a confirmar** en S4.0)

No se afirma ninguna capacidad sin probarla. La prueba exploratoria de S4.0 confirma, con el modelo candidato y en
un equipo de las características de una PYME (a declarar): (1) si el servicio y el cliente de Python admiten
llamadas a herramientas para ese modelo; (2) si admiten salida restringida a un esquema JSON; (3) ventana de
contexto, tiempo por turno y memoria requerida; (4) calidad en español con el banco de **desarrollo**; (5) licencia
del modelo y de Ollama; (6) puerto y anfitrión por defecto. **Plan B** si (1) no se cumple: protocolo de salida
estructurada, en el que el modelo responde un solo objeto `{"herramienta": …, "argumentos": {…}}` que se valida con
los mismos modelos Pydantic; el bucle, las herramientas y la validación no cambian. Si ningún modelo candidato pasa
(4), el modo local se declara «solo para pruebas» y el experimento compara lo que haya, declarándolo.

## 9. Experimento de la tesis (OE‑H2)

### 9.1 Pregunta y diseño

*¿Cuántos errores de las propuestas de cada modelo detecta el auditor, con cuántas falsas alarmas, y cuántas
propuestas son válidas?* Misma tarea, mismas herramientas, mismas instrucciones y mismo validador para los dos
modelos; solo cambia el proveedor. **El protocolo se escribe y se congela (commit y huella SHA‑256 del archivo) en
S4.0, antes de la primera corrida de evaluación**, como los de RNF‑04 y el indicador 3.

### 9.2 Banco de tareas de referencia (construidas y declaradas)

Los datos del repositorio son ficticios (NORMAS §1); las tareas también lo son, se dicen así en la tesis y no
pretenden representar obras reales. Cada tarea es una ficha versionada en `tests/fixtures/asistente/tareas/` con:
el **pedido** en lenguaje natural; las **respuestas preparadas** a las preguntas previsibles (y «no lo sé» para las
demás); el **borrador de partida** (vacío u otro); y la **referencia**: ambientes, fuentes, puntos, recorridos y
partidas esperados, escrita **a mano como memoria de cálculo antes de cualquier corrida** (oráculo independiente: no
sale de ninguna salida de un modelo ni de la derivación que se prueba).

| Conjunto | Tareas | Uso |
|---|---|---|
| **Desarrollo** | 4 (una por especialidad y una mixta) | ajustar instrucciones y herramientas; prueba manual con la API real; prueba exploratoria de Ollama |
| **Evaluación** | 12: 4 de agua, 3 de datos, 3 de electricidad y 2 mixtas con partidas que no derivan del espacio (estilo TI‑001); de las 12, **3 traen errores sembrados en el pedido** (p. ej. un punto a 3,00 m en un ambiente de 2,40 m, un ambiente con ancho cero, una toma «en el pasillo» que no existe) | solo la medición; nadie las ve corriendo un modelo antes de la corrida de evaluación |

Las tareas se basan en OF‑001 (oficina de demostración del sprint SF) y en TI‑001, adaptadas. Una segunda persona
(propuesta: el tutor o un ingeniero de la contratista de Med) revisa que el pedido y la referencia digan lo mismo,
antes de congelar.

### 9.3 Condiciones

| Condición | `pedir_informe_auditoria` | Para qué |
|---|---|---|
| **A, sin retroalimentación** (principal) | desactivada | el auditor actúa solo como verificador de la propuesta final: mide detección pura |
| **B, con retroalimentación** (secundaria) | activada | mide cuántos errores corrige el modelo al ver el informe y cuántos quedan |

Si el tiempo o el costo aprietan, B se cae primero (§11).

### 9.4 Corridas

12 tareas × 2 modelos × 2 condiciones × **3 repeticiones** = 144 corridas (72 con Claude). En cada corrida se acepta
**toda** propuesta válida tal cual (aceptación automática declarada: mide al modelo, no a la persona), se elabora y
audita el borrador resultante y se guarda todo en el registro `ia_*` de una base de experimento aparte (nunca
`data/apu.db`). Respaldo del lado del servidor desactivado; modelo, esfuerzo, versión del SDK, versión de Ollama y
del modelo local quedan registrados. **Costo estimado con §8.4: ≈ 87 USD** de cota superior para la evaluación más
≈ 20 USD de desarrollo; la corrida de evaluación **necesita la aprobación previa de Eugenio** con la cifra medida en
el piloto.

### 9.5 Métricas (definiciones congeladas en S4.0)

**Error de la propuesta:** discrepancia entre el borrador final aceptado y la referencia, clasificada por el
comparador (script determinista, tolerancia 0,001 m) en la taxonomía cerrada: E1 partida equivocada; E2 unidad;
E3 dimensión o posición fuera de tolerancia; E4 punto en ambiente equivocado o fuera de él; E5 fuente o circuito
equivocados; E6 elemento omitido; E7 elemento sobrante o duplicado; E8 dato sembrado del pedido copiado sin
objeción. Antes de medir se declara, por tipo, **qué regla debería detectarlo** (hipótesis) o que **no es
detectable por diseño** (p. ej. E6, E1 con unidad compatible: «mentira consistente», horizonte H‑D9).

**Hallazgos esperados por construcción:** antes de medir se lista, por tarea, el conjunto exacto de hallazgos que
da la **referencia** misma (p. ej. las ADVERTENCIAS de R8 por constantes supuestas, como las 33 de OF‑001 limpia,
y la de R1 por cada partida MANUAL). No cuentan ni como detección ni como falsa alarma.

| Métrica | Definición | Por modelo y condición |
|---|---|---|
| **Detección del auditor** | errores con al menos un hallazgo (ADVERTENCIA o más) no esperado que cite la fila o el ítem del error ÷ errores | sí, total y por tipo, con intervalo de Wilson al 95 % |
| **Falsas alarmas** | hallazgos no esperados cuyas filas citadas coinciden todas con la referencia ÷ hallazgos no esperados | sí |
| **Errores que escapan** | errores sin hallazgo, por tipo (el límite del auditor, se informa entero) | sí |
| **Propuestas válidas** | llamadas de propuesta que pasan las cuatro capas al primer intento ÷ llamadas de propuesta | sí, más rechazos por causa (§7.4) |
| **Guardas activadas** | números sin cita, códigos inexistentes y demás rechazos: lo que la validación paró **antes** del auditor | sí |
| **Exhaustividad** | elementos de la referencia presentes en el borrador final ÷ elementos de la referencia | sí |
| **Costo y tiempo** | tokens, USD, segundos por tarea; rechazos del proveedor | sí |

Umbrales propuestos para el veredicto (se congelan o corrigen en S4.0, **antes** de medir): detección ≥ 80 % de los
errores declarados detectables; falsas alarmas ≤ 10 %; 100 % de los números finales del presupuesto calculados por
el sistema (invariante, verificado por construcción). La comparación entre modelos se informa **descriptiva**, con
los intervalos; con 12 tareas no se afirma significancia estadística. Si un umbral no se cumple, se declara la brecha
(como GA3 en 2026‑09‑15): el asistente queda como *sugeridor* con revisión obligatoria de cada fila.

`scripts/evaluar_asistente.py` corre el protocolo y **genera** `docs/resultados_asistente.md`; nunca se edita a mano.

## 10. Pruebas y calidad

### 10.1 Automatizadas (CI, sin llamar a ninguna API)

**Ninguna prueba abre la red:** un `conftest.py` del asistente bloquea `socket.connect` (sin dependencia nueva) y la
CI corre con todos los extras; cero pruebas omitidas.

| Grupo | Qué prueba | Oráculo |
|---|---|---|
| Esquemas | cada modelo Pydantic rechaza campos extra, faltantes, `float` y números mal formados; el esquema JSON exportado es estable (instantánea) y tiene `additionalProperties: false` en todos sus objetos | casos frontera escritos a mano |
| Validación | una prueba por causa de rechazo de §7.4, con su frontera (3 vs 4 decimales; cita con «2,4» vs campo «2.40»; cm → m) | tabla de casos escrita antes del código |
| Propuestas | aceptar aplica exactamente la fila esperada; rechazar deja el `Borrador` igual (`==`); editar registra «editada»; el resultado pasa por `elaborar_borrador` (R1–R10) | borradores esperados a mano |
| Origen IA y R8 | origen IA completo sin supuestos → sin hallazgo; con dos supuestos → dos ADVERTENCIAS; referencia incompleta → ERROR; el Estado muestra «Propuesta de IA» | **conjunto exacto** de hallazgos escrito a mano |
| Orquestador | con `ProveedorGuionado` y guiones grabados: camino feliz; inválida y luego corregida; tres rechazos seguidos (9c); `refusal` (9e); `max_tokens` (9j); topes de turnos, llamadas y costo (9f); necesidad sin partida (9d); pregunta (9g); cancelación (9h); mismo guion dos veces → mismo registro y mismo orden | registros esperados a mano |
| Adaptador Claude | con un cliente falso que captura la solicitud: herramientas en orden fijo, `strict: true`, `tool_choice` automático, esfuerzo explícito, sin parámetros de muestreo, punto de caché en su lugar; respuestas grabadas (JSON sanitizado) → `Turno` correcto para cada `stop_reason`; `uso` → costo | solicitudes y turnos esperados a mano; los precios de prueba son de un archivo de configuración de prueba |
| Adaptador Ollama | respuestas grabadas del servicio local → `Turno`; plan B (§8.6) con objeto válido, inválido y con texto alrededor; anfitrión no local → tratado como nube | ídem |
| Privacidad | instantánea exacta de lo enviado para el borrador de prueba: sin precios, montos, nombre de proyecto ni de usuario; R2 y R7 con texto fijo | lista blanca de §8.1 |
| Clave (RNF‑18 c) | tras una sesión guionada con una clave de prueba, la clave no aparece en el volcado de la base, el registro `ia_*`, `caplog`, el Excel, el paquete ni el estado de la pantalla; `keyring` con un almacén falso en memoria | búsqueda literal |
| Arquitectura | la guardia de §5.2 | — |
| Experimento | el comparador y las métricas sobre **corridas de prueba hechas a mano** (no de un modelo) dan las cifras calculadas a mano, incluidos errores no detectables y hallazgos esperados por construcción | memoria de cálculo de las métricas, versionada antes del código |

**Respuestas grabadas:** se graban en la prueba manual con las tareas de **desarrollo**, se sanitizan (sin clave ni
encabezados) y se versionan en `tests/fixtures/asistente/grabaciones/`. La forma de reconstruir los tipos del SDK
desde el JSON grabado se confirma en S4.2 con la documentación del SDK; si no es posible, el adaptador se prueba con
diccionarios equivalentes declarados.

### 10.2 Prueba manual declarada (API real y modelo local)

`scripts/prueba_real_asistente.py --proveedor claude|ollama --tarea <desarrollo> --acepto-costo`: exige la clave
del almacén (nunca un argumento), corre **una** tarea de desarrollo, imprime tokens, `cache_read_input_tokens`,
costo, modelo que respondió y propuestas, y escribe una entrada en la bitácora de S4. No corre en la CI. Se ejecuta
una vez por proveedor en S4.2 y otra al cierre de S4.3, con la aprobación de Eugenio para el gasto.

### 10.3 Con personas

El panel del asistente se agrega al guion de Med como caso nuevo (CP‑12 propuesto): quien arma pide un baño y lo
guarda; se mide si entiende qué propuso la IA y qué calculó el sistema. Su criterio se fija antes de medir, como
RNF‑13.

## 11. Fases y tareas

| Fase | Contenido | Funciona al cerrar | Compuerta |
|---|---|---|---|
| **S4.0** | ERS (UC‑09, RF‑32, RF‑90…95, RNF‑18, enmienda de RNF‑08), arquitectura, modelo de datos; protocolo del experimento, taxonomía, umbrales y banco de tareas **congelados**; verificación de precios, modelo y parámetros contra la documentación vigente; prueba exploratoria de Ollama (§8.6) y de `keyring`; licencias | documentos aprobados; protocolo con huella | GS4‑0 (con el tutor para RNF‑08 y el experimento) |
| **S4.1** | herramientas y validación **sin IA**: modelos Pydantic, validación, propuestas, `TipoOrigen.IA` y R8, guardia de arquitectura | las propuestas escritas a mano de las 4 tareas de desarrollo producen sus referencias | GS4‑1 |
| **S4.2** | `ProveedorIA`, orquestador, `ProveedorGuionado`, adaptadores Claude y Ollama con grabaciones, registro `ia_*`, privacidad, clave, costo; prueba manual con los dos proveedores | suite verde sin red; una tarea de desarrollo real con cada proveedor | GS4‑2 |
| **S4.3** | panel en la hoja (pedido, vista previa, costo, diff, aceptar, editar, rechazar), configuración del administrador, manuales | un pedido real llega a una versión guardada con origen IA | GS4‑3 |
| **S4.4** | piloto, aprobación del costo, corrida de evaluación, `resultados_asistente.md` generado, veredicto | resultado del experimento | GS4‑4 |

**Orden de caída** (horizonte §6): primero la condición B; luego el modelo local (queda solo Claude, declarado);
UC‑09 con Claude, la validación y la condición A no se recortan.

| Tarea | Rol | Fase |
|---|---|---|
| T1 Enmiendas de ERS, arquitectura, modelo de datos y plan de pruebas | líder de fase | S4.0 |
| T2 Banco de tareas con referencias a mano, taxonomía y protocolo congelado | adaptadores + pruebas | S4.0 |
| T3 Exploración de Ollama y `keyring`; precios y parámetros verificados | adaptadores | S4.0 |
| T4 Pruebas de esquemas, validación y propuestas (rojo visto) | pruebas | S4.1 |
| T5 `asistente/herramientas.py`, `validacion.py`, `propuestas.py` | adaptadores | S4.1 |
| T6 `TipoOrigen.IA` y R8 en `adapters/espacio` (prueba antes que código) | adaptadores | S4.1 |
| T7 Orquestador, proveedor guionado y registro `ia_*` | adaptadores | S4.2 |
| T8 Adaptadores Claude y Ollama; grabaciones; prueba manual | adaptadores | S4.2 |
| T9 Privacidad, clave y costo | adaptadores + revisión de seguridad | S4.2 |
| T10 Panel y configuración en la interfaz | interfaz | S4.3 |
| T11 Comparador, métricas y `evaluar_asistente.py` con oráculo a mano | pruebas | S4.4 |
| T12 Corrida, resultados y veredicto | líder de fase | S4.4 |

**Metas** (`scripts/meta_silice_s4.py --hasta <fase>`): la ERS declara UC‑09 con RF‑32 y RF‑90…95; RNF‑08 enmendado;
protocolo congelado con su huella y sin cambios después; guardia de arquitectura con `asistente`; `git diff
<base>..HEAD -- core/` vacío; ninguna prueba omitida; `ruff check .` limpio; `resultados_asistente.md` generado por
el script. Compuerta de la versión: la del spec maestro §6, más el encargo de **seguridad** (clave, privacidad).

## 12. Rulings para ratificar

| # | Decisión | Costo si es errónea |
|---|---|---|
| RS4‑1 | El asistente es un paquete de primer nivel `asistente/`, no un adaptador (§5.1) | si se exige `adapters/`, hay que inyectarle las funciones de la hoja y del catálogo como parámetros: una capa de puertos más |
| RS4‑2 | Bucle propio neutral en vez del Tool Runner (§4) | más código propio para Claude; a cambio, un solo bucle para los dos modelos y un experimento comparable |
| RS4‑3 | Procedencia de las partidas con `MANUAL` + prefijo `ia:` + registro `ia_*`; **SL‑E10 vacante** (§5.4) | si el tutor exige `OrigenTipo.IA`, un expediente aditivo en `core/contracts` con su rama de núcleo |
| RS4‑4 | `TipoOrigen.IA` en `adapters/espacio`, con R8 marcando ADVERTENCIA solo los supuestos | si se prefiere advertir toda fila de la IA, más ruido en el informe y en las falsas alarmas del experimento |
| RS4‑5 | Un proveedor por sesión; el respaldo abre otra sesión, nunca en silencio (§5.3) | el usuario repite el pedido al cambiar de proveedor |
| RS4‑6 | Todo número de entrada con cita literal o supuesto declarado (§7.3) | más rechazos y más turnos (costo); a cambio, ningún número inventado sin marca |
| RS4‑7 | Respaldo del servidor ante rechazos: activado en el producto, desactivado en el experimento (§8.5) | en el producto, una fila puede venir de otro modelo (queda registrado) |
| RS4‑8 | Clave en el almacén del sistema operativo con `keyring`; respaldo cifrado con contraseña (§8.3) | dependencia nueva; si no se acepta, siempre cifrado con contraseña al arrancar |
| RS4‑9 | Minimización por lista blanca: sin precios, montos ni nombres (§8.1) | el modelo no puede razonar sobre costos; es intencional |
| RS4‑10 | Experimento con 12 tareas construidas, 3 repeticiones, condición A principal y aceptación automática (§9) | conclusiones descriptivas, no generalizables a obras reales; se declara |
| RS4‑11 | Claude Opus 5.5 con esfuerzo fijado en `high` (§8.5) | más costo por tarea que `medium`; se revisa con la medición del piloto, antes de congelar el protocolo |

## 13. Riesgos

| Riesgo | Mitigación |
|---|---|
| **Alucinación**: partidas, medidas o puntos inventados | esquemas sin campos de resultado; citas literales o supuestos marcados; códigos contra el catálogo; R1–R10 siempre; confirmación del usuario; el experimento mide lo que escapa |
| Instrucciones escondidas en el pedido o en textos del borrador (inyección) | las herramientas solo proponen; nada se guarda sin la persona; ninguna herramienta lee archivos ni la red |
| **Costo** de las corridas | estimación previa y real por turno; tope por sesión; caché; topes de turnos; experimento con aprobación previa y piloto |
| **Conexión** (internet inestable) | modo local; mensaje claro; la hoja funciona sin el asistente |
| **Privacidad** | lista blanca, vista previa, modo local, clave protegida, encargo de seguridad; la retención del proveedor se declara con su política vigente |
| El modelo local no sirve en español o en el equipo de una PYME | prueba exploratoria de S4.0; plan B de salida estructurada; caída declarada del modo local |
| **Sesgo del experimento**: quien construye las tareas conoce el sistema; ajuste de instrucciones sobre las tareas de evaluación; aceptación automática distinta del uso real | protocolo congelado antes de medir con huella; conjuntos de desarrollo y de evaluación separados; referencias a mano revisadas por una segunda persona; comparador determinista; se informan **todas** las corridas; mismas instrucciones para los dos modelos; la aceptación automática se declara como límite |
| Deriva de la API o de los precios entre hoy y la construcción | S4.0 y S4.2 releen el skill y la documentación; precios en configuración con fecha |
| La API de Anthropic cambia o retira el modelo | el id vive en un solo lugar (configuración del adaptador); las grabaciones fijan la forma de las respuestas |
| Un antecedente nuevo publica lo mismo | repetir la búsqueda de antecedentes antes de redactar (horizonte §7) |

## 14. Preguntas abiertas

1. **Tutor:** ¿acepta la tercera excepción a RNF‑08 (asistente en la nube, apagado por defecto) y el experimento de
   §9 como medición de OE‑H2?
2. ¿Se pueden enviar a un proveedor externo las **descripciones** de partidas que provienen de MaPreX (hasta 10 por
   búsqueda), según su licencia? Si no, en modo nube `buscar_partidas` solo devuelve partidas propias de la empresa.
3. ¿Qué modelo local y qué equipo de referencia (memoria, tarjeta gráfica) tiene una contratista típica? Define si
   el modo local es de uso real o solo de experimento.
4. ¿El registro `ia_*` viaja en el paquete auditado de S3? Propuesta: sí, sin uso ni costo, para que quien revisa vea
   qué filas propuso la IA. Hay que coordinarlo con el spec S3.
5. ¿Quién es la segunda persona que revisa el banco de tareas antes de congelarlo?
6. ¿Proveedor elegido por instalación o también por usuario? Propuesta: por instalación, con cambio por sesión.
7. ¿Se acepta `keyring` como dependencia nueva (RS4‑8)?
8. Presupuesto del experimento: ¿aprueba Eugenio la cota de ≈ 110 USD, a ajustar con el piloto?
9. ¿El esfuerzo de Claude se fija en `high` o se elige con el piloto sobre las tareas de desarrollo (RS4‑11)?

## 15. Numeración usada y vacante

| Número | Estado |
|---|---|
| UC‑09 | usado (§3.1) |
| RF‑32 | usado (deja de estar vacante) |
| RF‑90 … RF‑95 | usados (§3.2) |
| RNF‑18 | usado (§3.3) |
| SL‑E10 | **vacante**: S4 no toca `core/`; se abriría solo si se ratifica lo contrario de RS4‑3 |
