# Acta del re-congelado del experimento por las tildes de dos avisos (2026-11-13)

**Fecha:** 2026-11-13 · **Rama:** `feature/hoja-desperdicio` (`.worktrees/tanda`) · **Autoriza:** Eugenio, 2026-11-13
(autorizó re-congelar el experimento para las dos tareas de hoy: las tildes de dos avisos y editar el desperdicio en la
Hoja) · **Procedimiento:** el de las actas anteriores (`2026-10-21-recongelado-del-experimento.md`,
`2026-10-31-recongelado-experimento.md`, `2026-11-06-recongelado-experimento.md` y la del 2026-11-04 en la rama del
PR #100): un solo re-congelado al final, con el árbol limpio.

## Por qué

`tests/unit/test_experimento_congelado_vigente.py` falla con «auditor cambio desde el congelado»: de las 50 rutas de
`archivos_del_auditor` (`asistente/experimento/protocolo.json`) cambiaron dos, `aplicacion/hoja.py` y
`aplicacion/composicion.py` (`git diff --stat d4e4b35d HEAD` de esas rutas, del protocolo, de `mutaciones.py` y de
`tests/fixtures/asistente/tareas/`: solo esos dos archivos, 7 líneas más y 7 menos, todas del commit `d2b9a654`). Las
huellas `banco` y `protocolo` siguen iguales; solo cambia `auditor`.

Cambia **solo** `asistente/experimento/congelado.json`. `mutaciones.py`, `protocolo.json` y `banco.py` no se tocan, ni las
tareas del banco, ni `core/` (`git diff --stat d4e4b35d HEAD -- core/` vacío).

## Qué cambió

- **Tarea 1 (tildes; ESTADO §3 y §5.4, arbitraje `tanda-detalles-claude-xhigh-r3.md`, «fuera de alcance»).** Solo el texto
  de dos avisos:
  - `aplicacion/hoja.py`, `guardar_version`: «Esta versión está en solo lectura: alguna de sus partidas ya no tiene
    composición vigente en el catálogo, así que recalcularla cambiaría sus precios.» (antes sin tildes). Es el mismo texto
    que ya daba `aplicacion/hoja_guardado.py` (`MENSAJE_SOLO_LECTURA`) por la ruta del producto.
  - `aplicacion/composicion.py`, `motivo_para_no_reemplazar`: «composición», «línea», «borraría», «descripción» y
    «código» en sus tres motivos.
- **Tarea 2 (editar el desperdicio en la Hoja).** No tocó ningún archivo congelado: se construyó en
  `aplicacion/hoja_desperdicio.py` (nuevo), `hoja_edicion.py`, `hoja_borradores.py`, `hoja_guardado.py`, `hoja_vista.py` y
  `desperdicio.py`, que no están en `archivos_del_auditor` (decisión en
  [2026-11-13-desperdicio-en-la-hoja.md](2026-11-13-desperdicio-en-la-hoja.md)).

## Por qué no altera las reglas del auditor

- **Comprobación.** Se comparó el árbol sintáctico de `hoja.py` y de `composicion.py` en `d4e4b35d` (el commit declarado
  en el congelado anterior) y en HEAD con todas las cadenas de texto vaciadas: **iguales** en los dos archivos. Ninguna
  cifra, regla, rama, llamada ni valor devuelto cambió; solo el texto de dos mensajes.
- **Dónde lo usa el experimento.** El experimento clasifica mutantes E1–E8 con `comparador.py` sobre las salidas del
  auditor (`hoja.elaborar_borrador`, `Borrador`, `HojaInvalida`, `filas_desde_espacio`, `COLUMNAS`, `PREFIJO_ORIGEN_IA`);
  no compara el texto de `HojaInvalida` de `guardar_version` ni llama a `motivo_para_no_reemplazar` (Componer), que no
  están en su camino.

**Pruebas del experimento** en la rama, antes de re-congelar (`tests/unit/test_experimento*.py`,
`test_mutaciones_viales.py`, `test_evaluar_asistente.py`): **120 pruebas, 119 verdes y 1 roja**; la roja es `test_experimento_congelado_vigente` (la que esta acta resuelve), con «auditor cambio desde el congelado».

## Huellas

| Huella | Congelado anterior (commit declarado `d4e4b35d`) | Re-congelado (2026-11-13) |
|---|---|---|
| `banco` | `29446b12ebf646d89ef9ccae3b597989e8787757e7fdf9a66024ff098aa3a0b2` | igual |
| `protocolo` | `e769c50778198e0ad354409b6ad8589b344bf4c73eae9c04f715f7fc9b075bb6` | igual |
| `auditor` | `87d8bb1f717d68165486d8bdf9768c4ea1e7ab40f0ef149fe483a25a03527d7d` | `18fc3b4ac2d0e309fb8e2f280c4cc3322336ef2af4a5ce37fb2f7d704297408a` |

El commit declarado en el nuevo `congelado.json` es el de esta acta.

## Cómo se re-congela

`congelar(<commit de esta acta>)` de `asistente/experimento/congelado.py`, con el árbol limpio y en un commit aparte:
`chore(experimento): re-congelado con acta (2026-11-13)`.

**Nota para el PR #100.** Su rama re-congeló sobre `core/contracts/unidades.py`. Cuando se unan, la huella del auditor
tendrá que volver a calcularse con los cambios juntos, con su acta.
