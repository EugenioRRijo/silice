# Expedientes de la fase C5 del cierre (núcleo)

**Fecha:** 2026‑09‑28 · **Rama:** `inc/cierre-C5-nucleo` (pista N de C5) · **Orden de trabajo:**
`C5-orden-de-trabajo.md` del directorio de control de C5 · **Inventario:**
[docs/auditoria/2026-09-inventario.md](../auditoria/2026-09-inventario.md) · **Spec:**
[§5, fila C5, y §10, enmienda del 2026‑09‑28](../superpowers/specs/2026-09-23-plan-cierre-tesis-design.md)
· **Bitácora de la fase:** [2026-09-23-cierre.md, «Fase C5»](2026-09-23-cierre.md).

La enmienda de C5 autoriza exactamente dos commits que tocan `core/`, cada uno con su expediente
previo en este archivo, commiteado antes de su código, sin cambiar ningún contrato de
`core/contracts/` y con la línea base (1 586,61 USD y 7 de 7) intacta. Si un expediente concluyera
que hace falta un contrato, la fase se detiene (CLAUDE.md §5). El método es el de los expedientes
C3.1 y C3.2 ([2026-09-24-C3-expedientes.md](2026-09-24-C3-expedientes.md)).

## C5.1 INV‑095: el informe atribuye cada hallazgo a su partida y su origen

**Problema.** La columna Partida del informe (`InformeAuditoria.a_markdown`) atribuye mal los
hallazgos cuando un mismo `origen_id` produce varias partidas. Reproducido en la pista N sobre
`abeee7e` (rama `inc/cierre-C5-nucleo`) con `AdaptadorCivilTabular` y `elaborar` sobre
`data/samples/civil/tanquillas_y_zanja.csv`, las composiciones de la línea base y `plan_secuencial`
(el mismo flujo que `ui.elaboracion.elaborar_desde_catalogo`): de 6 hallazgos, 3 llevan la partida
equivocada.

| Hallazgo | `origen_ids` | Partida que pinta el informe | Partida correcta |
|---|---|---|---|
| R3 ERROR, «la partida LB-02-TUB se computa en 'm'…» | `('Z-01',)` | LB-01-EXC | LB-02-TUB |
| R4 INFO, «'material' = 'concreto' de LB-01-EXC…» | `('T-01',)` | LB-04-CON | LB-01-EXC |
| R4 INFO, «'material' = 'concreto' de LB-03-ENC…» | `('T-01',)` | LB-04-CON | LB-03-ENC |

Los otros tres (R6 y dos R4 INFO de la excavación de `Z-01`) salen bien por casualidad del orden. La
descripción de cada hallazgo es correcta; la hoja *Auditoria* del Excel no tiene columna Partida y
no se afecta.

**Diagnóstico.** `_indice_de_partidas` (`core/verification/informe.py`) construye
`origen_id -> codigo_partida` con `setdefault`, así que cada origen apunta a la **primera** partida
que lo cita, y `partida_de` consulta ese índice con el primer origen del hallazgo. El núcleo supone
«un `origen_id`, una partida», que el contrato no garantiza: `OrigenTipo.REGLA` define `origen_id`
como el objeto paramétrico (`core/contracts/item_computo.py:19`), y un objeto da varias partidas (la
fila `T-01` da concreto, encofrado y excavación; `Z-01`, excavación y tubería). Con solo el
`origen_id` y el índice, el informe no puede saber de cuál de esas partidas habla un hallazgo: lo
sabe la regla que lo emitió, que lo redactó recorriendo una partida concreta.

**Opciones consideradas.**

- *(a) La clave `(codigo_partida, origen_id)` en `origen_ids`*, como `_clave_pendiente` y R6.
  Descartada: cambia el contenido de `Hallazgo.origen_ids` de todas las reglas por ítem (R1, R3, R4,
  R5 y R7), que hoy son `origen_id` reales (principio 6) y que fijan las pruebas de RF‑21. Medido en
  un prototipo desechado: 15 pruebas existentes en 4 archivos
  (`test_verification.py`, `test_auditoria_arenaza.py`, `test_presupuesto_industrial.py`,
  `test_presupuesto_sistemas.py`) fallan y habría que reescribir sus aserciones; cambiarían además
  la columna *Orígenes* del Excel y los hallazgos persistidos.
- *(b) Un índice de varias partidas por origen*, solo. No elige: para `T-01` puede pintar las tres
  partidas o ninguna, pero no la del hallazgo.
- *(c) Elegida:* la regla declara la partida de cada hallazgo que emite, y el informe la guarda.

**Diseño de (c).** Un solo commit de `core/verification/`, asunto
`fix(verification): el informe atribuye cada hallazgo a su partida y su origen`, con sus pruebas en
`tests/unit/test_verification.py`:

- `core/verification/reglas.py`: un protocolo `ReglaAtribuible` (`typing.Protocol`,
  `runtime_checkable`) con `atribuir(presupuesto) -> list[tuple[Hallazgo, str | None]]`: cada
  hallazgo con el código de la partida que lo produjo, o `None` si no es de una partida. Lo
  implementan las cinco reglas cuyos hallazgos nacen de una partida: R1, R3, R4 y R5 (la partida
  evaluada) y R7 (la partida sin período; en una conciliación, la primera partida de la componente
  en el orden del presupuesto, como hasta hoy; un período sin partida, `None`). En esas cinco,
  `evaluar(presupuesto)` pasa a ser los hallazgos de `atribuir`, sin la partida: **la misma lista,
  en el mismo orden y con los mismos campos** que hoy, así que ninguna prueba existente cambia.
  R2 (propiedades del presupuesto completo) y R6 (sus `origen_ids` ya son códigos de partida) no lo
  necesitan.
- `core/verification/informe.py`:
  - `InformeAuditoria.partida_por_hallazgo: Mapping[Hallazgo, str | None]` (campo nuevo del informe,
    no de un contrato; `MappingProxyType` como `partida_por_origen`). `auditar` lo llena con lo que
    declara cada regla atribuible. Si dos hallazgos **iguales** declaran partidas distintas, el
    hallazgo queda en `None`: el informe no elige por su cuenta.
  - `partida_de(hallazgo)`: primero `partida_por_hallazgo`; si la regla no lo declaró (R2, R6, el
    `PENDIENTE` de `core.budget` o una regla ajena al núcleo pasada en `reglas=`), el índice por el
    primer origen, como hoy.
  - `_indice_de_partidas` deja de adivinar: un `origen_id` que citan partidas distintas **no se
    registra**, así que una regla que no declara su partida y cita un origen compartido no se
    atribuye (la columna pinta «-») en vez de atribuirse a la primera partida. La identidad
    `codigo -> codigo` (R6 y `PENDIENTE`) no cambia.
- Ningún contrato cambia: `Hallazgo`, `ReglaVerificacion` y `Presupuesto` quedan iguales. El
  protocolo no es un contrato de `core/contracts/`: vive en `core/verification` y ninguna frontera
  entre paquetes lo cruza (`test_arquitectura.py`).

**Prueba en rojo por comportamiento.** Dos, en `tests/unit/test_verification.py`:

1. La muestra civil de arriba, auditada: cada hallazgo de R1, R3 y R4 se atribuye a la única
   partida del presupuesto que nombra su descripción (oráculo independiente del índice: el texto lo
   redacta la regla desde `item.codigo_partida`), y el R3 de la tubería, a `LB-02-TUB`. R5 queda
   fuera de este oráculo porque su descripción cita también las partidas del balance; su
   declaración la fija una prueba propia con el origen del relleno compartido (ronda 1, QA‑4). En rojo
   fallan los 3 de 6 de la tabla. La prueba no fija cuántos R4 INFO hay: INV‑096 (pista P) quita las
   especificaciones que no corresponden a cada partida y ese número baja.
2. Un presupuesto en memoria, con aritmética a mano: dos ítems con el mismo `origen_id`, la
   excavación primero y la tubería en «m» después; el R3 es de la tubería. Y una regla ajena que no
   declara su partida y cita ese origen compartido: `partida_de` da `None`.

**Límites declarados.**

- **Elaboración con pendientes, hasta C5.2.** `core.budget.presupuesto._declarar_pendientes`
  reconstruye `InformeAuditoria` campo por campo y perdería `partida_por_hallazgo`; ese archivo no
  está entre los permitidos de este commit (`core/verification/*`). Mientras tanto, en una
  elaboración **con** pendientes la columna vuelve al índice (que ya no adivina en un origen
  compartido, pero al que `_declarar_pendientes` agregaba los orígenes de los pendientes; la ronda 1
  los quitó, M‑1). Lo cierra
  el commit de C5.2, que pasa `_declarar_pendientes` a `dataclasses.replace` con una prueba de que
  la atribución sobrevive a los pendientes. Los dos commits van en el mismo PR.
- Una conciliación de R7 que abarca varias partidas se atribuye a la primera (su descripción las
  nombra todas); R6, a la del factor minoritario (primer código), como hasta hoy.
- La hoja *Auditoria* del Excel sigue sin columna Partida (fuera del alcance de INV‑095).
- La recarga (`cargar_elaboracion`) reaudita, así que recalcula la atribución; los hallazgos
  persistidos no cambian de forma.

**Línea base.** Intacta: `tests/fixtures/apu_linea_base.py` no se edita y el conjunto de la línea
base sigue en `27 0 0 0`. El presupuesto del protocolo de RNF‑04 no comparte orígenes: su informe en
pantalla no cambia con este commit (huella SHA‑256 del `a_markdown()` antes y después:
`9469aaf8…ed0063`).

**Para la pista D.** `docs/arquitectura.md` (§3.1, §6.1 y la nota del diagrama de secuencia de la
auditoría, línea 966) y `docs/modelo_datos.md` §2 (`origen_ids`) describen el índice de la primera
partida: pasan a la atribución por regla.

**Ratificar en GC5:** el protocolo `ReglaAtribuible` fuera de los contratos, el `None` ante dos
hallazgos iguales con partidas distintas, el índice que no registra orígenes compartidos y el límite
de los pendientes hasta C5.2.

**Resultado de C5.1** (anotado con el expediente C5.2). Commit de `core/`: `e43fd8b`, hoy `cd68487` tras el fixup de la ronda 1 (un arreglo de
revisión lo reescribiría por `fixup`, regla C5‑1). Rojo por comportamiento, antes del código, en
`tests/unit/test_verification.py`: la muestra civil con 3 hallazgos mal atribuidos (el R3 de la
tubería como `LB-01-EXC` y los dos R4 de `T-01` como `LB-04-CON`), el R3 del objeto `OBJ-1` como
`LB-01-EXC`, la regla ajena y el hallazgo declarado dos veces atribuidos a `LB-01-EXC`. Además de
las dos pruebas del expediente, tres más: la regla ajena sobre el origen compartido, el hallazgo
declarado para dos partidas y la conciliación y la partida sin período de R7 sobre `OBJ-1` (esta
última, porque la mordida de R7 que quita su declaración sobrevivía: con orígenes únicos el índice
de respaldo da la misma partida). Mordidas, cada una restaurada: `partida_de` sin la declaración
(fallan 2), el índice que vuelve a registrar los orígenes compartidos (falla 1), la última
declaración que gana (falla 1), R3 que declara la primera partida del presupuesto (fallan 2) y R7
que no declara la conciliación (falla 1). Línea base `27 0 0 0`; la huella del informe de RNF‑04 no
cambia (`9469aaf8…ed0063`).

## C5.2 INV‑092 (con RF‑21): el informe enumera las reglas evaluadas

**Problema.** UC‑05 5a (`docs/ERS.md`, «No hay hallazgos: el informe se emite igualmente,
declarando las siete reglas evaluadas y sin hallazgos») no está implementado:
`InformeAuditoria.a_markdown` pinta cabecera, resumen por severidad y tabla de hallazgos, pero no
dice qué reglas corrió, y con cero hallazgos emite dos tablas vacías. Ninguna prueba audita un
presupuesto con cero hallazgos, y RF‑21 («devuelve una lista vacía cuando el presupuesto cumple»)
no tiene esa prueba para R2 ni para R4 (`docs/plan_pruebas.md` §8, fila RF‑21, y §8.1, UC‑05 5a).
Ese informe es el objeto del juicio de expertos de RNF‑04 en Med, por eso va antes.

**Diagnóstico.** `auditar` ya recibe las reglas (`reglas=REGLAS`) y cada una declara `codigo` y
`nombre` (`ClassVar` del contrato `ReglaVerificacion`): el dato existe y el informe lo descarta. Hay
una trampa (ARQ‑3 de la revisión de arquitectura de GC4): `core.budget.presupuesto._declarar_pendientes`
reconstruye `InformeAuditoria` campo por campo, así que un campo nuevo se perdería en silencio en
toda elaboración con pendientes y en la recarga (`cargar_elaboracion` la llama). Es la misma trampa
que deja abierto el límite de C5.1 con `partida_por_hallazgo`.

**Diseño.** Un solo commit, asunto `feat(verification): el informe enumera las reglas evaluadas`,
que toca solo `core/verification/informe.py`, `core/budget/presupuesto.py` y
`core/budget/excel.py`, más sus pruebas en `tests/`:

- `InformeAuditoria.reglas_evaluadas: tuple[tuple[str, str], ...]`: `(codigo, nombre)` de cada regla
  que corrió `auditar`, en el orden en que corrieron. Es un campo del informe, no de un contrato; el
  contrato solo se lee.
- `a_markdown`: una sección «Reglas evaluadas» (tabla Regla · Nombre · Hallazgos) entre el resumen
  por severidad y la tabla de hallazgos. Con cero hallazgos, el resumen y la tabla de hallazgos
  dicen «Sin hallazgos.» en vez de pintar tablas vacías. Un informe construido a mano sin reglas
  evaluadas no pinta la sección (`auditar` siempre la llena).
- `excel.py`: la hoja *Auditoria* enumera las mismas reglas en un bloque a la derecha (columnas G a
  I: Regla evaluada · Nombre · Hallazgos), separado por la columna F vacía. La tabla de hallazgos
  (columnas A a E) sigue con una fila por hallazgo, que es lo que fijan las pruebas existentes del
  libro (`test_budget.py`, `test_api.py`). Así las dos formas del informe que juzga RNF‑04 declaran
  lo mismo.
- `presupuesto.py`: `_declarar_pendientes` pasa a `dataclasses.replace(informe, hallazgos=…,
  partida_por_origen=…)`: conserva `reglas_evaluadas` y `partida_por_hallazgo` (cierra el límite de
  C5.1) y cualquier campo que el informe gane después. `PENDIENTE` no se enumera como regla: no es
  una de las siete, lo emite la elaboración. `core/budget/persistencia.py` no cambia: la recarga
  llama a `_declarar_pendientes`.

**Pruebas.** En rojo por comportamiento (fallan por aserción, no por importación):

1. `tests/unit/test_verification.py`: el informe del presupuesto auditado enumera las siete reglas
   con su nombre y su cuenta de hallazgos (oráculo: la cuenta por `hallazgo.regla` sobre
   `informe.hallazgos`, y los códigos y nombres de `REGLAS`).
2. `tests/unit/test_verification.py`, UC‑05 5a: un presupuesto con **cero** hallazgos. Es
   `presupuesto_corregido()` (la fixture de 7 de 7), cuyo único hallazgo es la ADVERTENCIA de R1 por
   el relleno transcrito a mano; declarado tabular (trazable por su fila), no queda ninguno.
   Oráculo por la otra ruta: cada una de las siete reglas, llamada por separado, devuelve `[]`. El
   informe dice CUMPLE, enumera las siete con 0 y dice «Sin hallazgos.».
3. `tests/unit/test_budget.py`: la elaboración con pendientes conserva las reglas evaluadas y la
   atribución de C5.1 (la muestra civil sin composición de concreto: el pendiente comparte `T-01` y
   el R3 de la tubería, de `Z-01`, sigue atribuido a `LB-02-TUB`); y el libro enumera las reglas en
   la hoja *Auditoria*.
4. `tests/integration/test_recarga_con_pendientes.py`: el informe recargado con pendientes enumera
   las siete reglas (ARQ‑3).

Pruebas de caracterización de RF‑21 (verdes desde el principio: la conducta existe, faltaba la
prueba), con mordida: R2 y R4 devuelven `[]` sobre `presupuesto_corregido()`, que trae curva que
cierra por construcción y especificaciones que el texto de su APU reconoce.

**Límites declarados.**

- La base no guarda `reglas_evaluadas` (no hay migración de esquema): el informe recargado las
  enumera porque la recarga reaudita con `REGLAS`.
- La cuenta de hallazgos por regla incluye INFO y las declaraciones «no aplicable» (R2 y R7 sin plan
  de trabajo, que sí son hallazgos del contrato).
- **La tabla «Reglas evaluadas» no cuenta los `PENDIENTE`** (no son una de las siete reglas: los
  declara la elaboración). Con pendientes, la suma de la tabla es menor que «Hallazgos: N» de la
  cabecera, y en el Excel el bloque G–I suma menos filas que la tabla A–E; la diferencia son
  exactamente los `PENDIENTE` (M‑2 de la revisión de requisitos). El manual de usuario debe
  decirlo (pista D).
- **La columna Partida es un ancla; la descripción, el detalle.** Una conciliación de R7 que abarca
  varias partidas se atribuye a la primera en el orden del presupuesto y R6, a la del factor
  minoritario (su primer código); en los dos casos la descripción nombra todas las partidas (O‑1 de
  la revisión de requisitos). La fijan `test_r7_atribuye_la_conciliacion_de_varias_partidas_…` y
  `test_partida_de_resuelve_el_origen_y_el_codigo_de_partida`.
- La huella del informe de RNF‑04 cambia con este commit (sección nueva): la regenera el controlador
  en GC5 sobre el commit de la compuerta (`docs/protocolo_rnf04.md` §1), no esta pista.

**Línea base.** Intacta: `tests/fixtures/apu_linea_base.py` no se edita y el conjunto de la línea
base sigue en `27 0 0 0`. El commit de `core/` no cambia ninguna aserción existente; la ronda 1
cambia una, en un commit de pruebas aparte (O‑2: `test_budget.py` cuenta la columna A de la hoja
*Auditoria* y no `max_row`).

**Para la pista D.** `docs/plan_pruebas.md` §8 (fila RF‑21: las pruebas de lista vacía de R2 y R4) y
§8.1 (UC‑05 5a), `docs/ERS.md` (alcance vigente de RF‑21) y el manual de usuario (la sección nueva
del informe).

**Ratificar en GC5:** el bloque de reglas a la derecha en la hoja *Auditoria*, «Sin hallazgos.» en
lugar de tablas vacías y `PENDIENTE` fuera de la enumeración.

## Ronda de corrección 1 de la pista N (revisiones de arquitectura, requisitos y QA)

Dictámenes `N-rev-arq.md`, `N-rev-req.md` y `N-rev-qa.md` del directorio de control: los tres
aprueban, con observaciones o con condición. Los cambios de `core/` van por `fixup` y autosquash
sobre `abeee7e` (regla C5‑1). Los dos commits de `core/` conservan sus asuntos exactos: `cd68487`
(INV‑095, antes `e43fd8b`) y `aa53201` (INV‑092, antes `07e246d`).

| Hallazgo | Corrección | Dónde |
|---|---|---|
| M‑1 (arq., req.) | `_declarar_pendientes` ya no mete en el índice de respaldo el `origen_id` de cada pendiente: basta la identidad `codigo -> codigo`. Docstring reescrito. Prueba: un hallazgo sin partida declarada que cita la fila `T-01` (compartida por dos valoradas y el pendiente) da `None`, no la partida pendiente. Mordida (reponer la entrada): falla 1 | fixup de `07e246d` |
| O‑1 (arq.) | El docstring de `ReglaAtribuible` dice que los hallazgos de `atribuir`, sin la partida, son exactamente los de `evaluar`, y que quien redefine uno redefine el otro | fixup de `e43fd8b` |
| O‑4 (arq.) | `auditar` materializa `reglas = tuple(reglas)`. Prueba con un generador. Mordida (quitar la línea): falla 1 | fixup de `07e246d` |
| QA‑1 (condición) | R4 sobre el objeto compartido `OBJ-1`, en memoria (la muestra civil deja de producir R4 con INV‑096), y docstring de la prueba de la muestra. Mordida «R4 no declara su partida»: fallan 2 | `test(verification)` |
| QA‑2 | La conciliación de R7 de varias partidas va a la primera del presupuesto. Mordida `partidas[-1]`: falla 1 | `test(verification)` |
| QA‑3 = M‑3 (req.) | La hoja *Auditoria* sin hallazgos: columna A solo con el encabezado, G–I con las siete reglas en 0. Mordida «no escribir el bloque sin hallazgos»: falla 1 | `test(verification)` |
| QA‑4 | R5 con el origen del relleno compartido con la excavación. Mordida «R5 declara `None`»: falla 1. Y el texto del expediente C5.1 (R1, R3 y R4, no R5) | `test(verification)`; este commit |
| O‑2 (arq.) | `test_budget.py` cuenta la columna A de la hoja *Auditoria* y no `max_row` | `test(budget)` |
| M‑2 (req.) | Límite declarado en C5.2: la tabla «Reglas evaluadas» no cuenta los `PENDIENTE` | este commit |
| O‑1 (req.) | Declarado en C5.2: la columna Partida es un ancla (R7 de varias partidas, a la primera; R6, al primer código) | este commit |
| QA‑5 | Las cifras de mordida del reporte son las del momento: «`partida_de` sin la declaración» muerde hoy 4 pruebas, no 2, porque se agregaron después la de R7 y la de pendientes | — |

Queda para el controlador (I‑1 de la revisión de requisitos): `docs/protocolo_rnf04.md` §1, la fila
de las reglas evaluadas y el párrafo de la *Partida*, al regenerar el material de RNF‑04 en GC5. Para
la pista D: O‑3 de arquitectura (`docs/arquitectura.md` :966 y :1334, `InformeAuditoria` como
interfaz pública que evoluciona de forma aditiva) y el manual (M‑2, O‑1 y O‑3 de requisitos).
