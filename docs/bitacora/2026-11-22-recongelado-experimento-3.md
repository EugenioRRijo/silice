# Acta del tercer re-congelado del experimento del 2026-11-22 (`asistente/validacion.py`)

**Fecha:** 2026-11-22 · **Rama:** `fix/asistente-miles` (`.worktrees/s4u`, desde `6286ae3b`) · **Autoriza:** Eugenio,
2026-11-22, con estas palabras: «en nuestro contexto español leemos el punto como mil y la coma como decimal, arreglemos
eso y volvamos a sellar» (eligió la opción A: arreglar y volver a sellar) · **Procedimiento:** el de las actas anteriores
(`2026-10-21-recongelado-del-experimento.md`, `2026-10-31-recongelado-experimento.md`,
[2026-11-06-recongelado-experimento.md](2026-11-06-recongelado-experimento.md),
[2026-11-13-recongelado-experimento-2.md](2026-11-13-recongelado-experimento-2.md)): un solo re-congelado al final, con el
árbol limpio y en un commit aparte.

## Por qué

**El defecto.** La guarda contra el número inventado (capa 3, `validar_citas`) leía el punto como decimal:
`normalizar()` solo cambiaba la coma por punto y `_NUMERO` tomaba «1.200» como 1,2. Con un pedido que dice
«1.200 salidas», una cantidad de la IA mil veces menor (1,2) pasaba y la correcta (1200) se rechazaba con
`numero_ausente_de_la_cita`. En Sílice rige la coma decimal y el punto de miles (NORMAS; decisión de Eugenio del
2026-10-25).

**El cambio** (commit `d3922dc3`, prueba en rojo `c32d85e0`). `normalizar()` quita primero el punto que va entre una cifra
y exactamente tres cifras («1.200» → 1200, «1.234,56» → 1234.56, «1.200.000» → 1200000) y después lee la coma como decimal.
Un punto seguido de otra cantidad de cifras («2.5») se deja como estaba. La cita literal no cambia de criterio, porque el
pedido y la cita pasan por la misma normalización. Son 4 líneas más y 2 menos.

`tests/unit/test_experimento_congelado_vigente.py` falla con «auditor cambio desde el congelado»: de las rutas de
`archivos_del_auditor` (`asistente/experimento/protocolo.json`) cambió una, `asistente/validacion.py`
(`git diff --stat ac99137a HEAD` de esas rutas, del protocolo, de `mutaciones.py`, de `tests/fixtures/asistente/tareas/` y
de `core/`: solo `asistente/validacion.py`, 4 líneas más y 2 menos). Las huellas `banco` y `protocolo` siguen iguales;
solo cambia `auditor`.

Cambia **solo** `asistente/experimento/congelado.json`. `mutaciones.py`, `protocolo.json` y `banco.py` no se tocan, ni las
tareas del banco, ni `core/`.

## Por qué no altera lo que mide el experimento

- **La medición controlada (sin IA).** Clasifica mutantes E1–E8 con `comparador.py` sobre los hallazgos del auditor
  (`ejecucion.py::auditor_de_la_hoja`, que llama a `hoja.elaborar_borrador`). Ese camino no pasa por
  `asistente/validacion.py`: lo usa solo el orquestador (`asistente/orquestador.py:58`) cuando hay una IA que propone.
- **Las corridas con IA.** Sí pasan por la guarda, pero el cambio solo actúa sobre un punto entre una cifra y tres
  cifras. Ninguna de las 16 tareas del banco (`tests/fixtures/asistente/tareas/*.json`) trae ese patrón
  (`grep -rnoE "[0-9]\.[0-9]{3}([^0-9]|$)"` sin resultados), así que sobre el banco la guarda decide igual antes y después.

## Huellas

| Huella | Congelado anterior (commit declarado `ac99137a`) | Re-congelado (2026-11-22, tercero) |
|---|---|---|
| `banco` | `29446b12ebf646d89ef9ccae3b597989e8787757e7fdf9a66024ff098aa3a0b2` | igual |
| `protocolo` | `e769c50778198e0ad354409b6ad8589b344bf4c73eae9c04f715f7fc9b075bb6` | igual |
| `auditor` | `1a89416653b90b11e73237e92d9315b60dd1a4f6da325b494573226914dc6d1f` | `1fbef8fb31eecfc1c62dd58a4c85ba831f804c557ba2f57074477129fc1108bc` |

El commit declarado en el nuevo `congelado.json` es el de esta acta.

## Cómo se re-congela y cómo se revierte

`congelar(<commit de esta acta>)` de `asistente/experimento/congelado.py`, con el árbol limpio y en un commit aparte:
`chore(experimento): tercer re-congelado con acta (2026-11-22)`. Revertir: revertir el commit del congelado y `d3922dc3`
(vuelve `validacion.py` y su huella `1a894166…`) y la prueba `c32d85e0`.

## Pruebas

- **Rojo** (`c32d85e0`), `tests/unit/test_asistente_validacion.py`: 4 fallan (`1.200`, `1.234,56`, `1.200 m` y la partida
  citada «1.200 salidas» con cantidad 1.2 sin rechazo); `0,5` y `12` ya pasaban.
- **Verde** (`d3922dc3`): `tests/unit/test_asistente_validacion.py`, 23 verdes.
- **Pruebas del asistente y del experimento antes de re-congelar** (`tests/unit` y `tests/integration` que nombran
  asistente, experimento, congelado, mutaciones viales o recongelado): **629 pruebas, 628 verdes y 1 roja**; la roja es
  `test_experimento_congelado_vigente::test_los_archivos_del_auditor_siguen_como_se_congelaron`, con «auditor cambio
  desde el congelado» (la que esta acta resuelve). Después del re-congelado, esa prueba pasa (commit siguiente).
