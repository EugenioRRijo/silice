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

1. La muestra civil de arriba, auditada: cada hallazgo de R1, R3, R4 y R5 se atribuye a la única
   partida del presupuesto que nombra su descripción (oráculo independiente del índice: el texto lo
   redacta la regla desde `item.codigo_partida`), y el R3 de la tubería, a `LB-02-TUB`. En rojo
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
  compartido, pero al que `_declarar_pendientes` agrega los orígenes de los pendientes). Lo cierra
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
