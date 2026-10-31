# Acta del re-congelado del experimento (2026-10-31)

**Fecha:** 2026-10-31 · **Rama:** `inc/vial-agregados` (worktree `.worktrees/s2madm`) · **Autoriza:** Eugenio, 2026-10-31:
«Re-congelar con acta». · **Procedimiento:** el del re-congelado anterior (`2026-10-21-recongelado-del-experimento.md`,
ruling `9832db3a`, `congelado.json` en `1ec20732`).

## Por qué

`tests/unit/test_experimento_congelado_vigente.py` falla con «auditor cambio desde el congelado»: dos archivos de
`archivos_del_auditor` (`asistente/experimento/protocolo.json`) cambiaron después del congelado por trabajo del producto
que el experimento no mide. Las huellas `banco` y `protocolo` siguen iguales; solo cambia `auditor`.

Esta es la única excepción a la regla de no tocar el congelado: cambia **solo** `asistente/experimento/congelado.json`.
`mutaciones.py`, `protocolo.json` y `banco.py` no se tocan (`git diff 9832db3a HEAD` de los tres está vacío), y tampoco las
tareas del banco (`tests/fixtures/asistente/tareas/`).

## Qué archivos del auditor cambiaron y en qué commits

`git log 9832db3a..HEAD -- <las 50 rutas de archivos_del_auditor>` da cambios en dos archivos y en nada más
(`git diff --stat 9832db3a HEAD` de las 50 rutas: `aplicacion/composicion.py` y `aplicacion/hoja.py`):

| Archivo | Commits (del más reciente al más viejo) |
|---|---|
| `aplicacion/hoja.py` | 23120bcd (conciliación vial, T10), 67a63b7c, eeb31081, 09a10130, 515f2527, dbd93d6c, 010855f2, 5f44b70b, 9432e60a, f47a4fbc, 7cc64f14 (coma decimal, D-8), 13e552e5, d3d7afd0 |
| `aplicacion/composicion.py` | 51485411, 13e552e5, 26db12ec, d3d7afd0 |

Son las tareas de la Hoja y de Componer del rediseño del front (25 y 26 de octubre: coma decimal y punto de miles, agregar
y quitar partidas y líneas, plan desde los rendimientos, notas de medición, estudio de mercado) y la conciliación vial
(Tarea 10 del plan vial: VR1 a VR7 en `abrir_version`).

## Por qué no afectan a las mutaciones del experimento

Comparación por AST de las definiciones de nivel superior entre `9832db3a` y la cabeza (sin docstrings):

- **Lo que usa el experimento quedó idéntico.** El banco (`banco.py`) arma cada referencia con `Borrador` y
  `espacio_desde_filas`; la ejecución (`ejecucion.py`) elabora con `hoja.elaborar_borrador`; `orquestador`, `validacion`,
  `propuestas` y `privacidad` usan `Borrador`, `HojaInvalida`, `filas_desde_espacio`, `COLUMNAS` y `PREFIJO_ORIGEN_IA`.
  `elaborar_borrador` y `elaborar_hoja` no cambiaron. `Borrador` gana un campo `notas` con valor por omisión (texto libre
  de medición, no entra en el cálculo) y nadie del experimento lo pasa.
- **`espacio_desde_filas` cambió sin cambiar lo que lee el experimento.** D-8 (7cc64f14) le añadió `tecleado=False`: con
  `tecleado=True` (solo el editor de la Hoja) las celdas de cifra se leen con coma decimal; **sin él siguen leyéndose con
  `decimal_desde_texto`, punto decimal, como antes** («leerlas con la regla convertiría 1.125 metros en mil ciento
  veinticinco», dice su docstring). El banco y el asistente no pasan `tecleado`. Los vértices conservan el punto en los dos
  casos.
- **Las demás funciones cambiadas no están en el camino del experimento:** `cantidades_desde_filas`,
  `composicion_con_cantidades`, `parametros_desde_texto`, `plan_desde_filas` (ahora con `cifra_de_celda`),
  `abrir_version` (VR1 a VR7 y notas), `guardar_version`, `crear_primera_version`, `completar_composiciones` y las de
  cambios (`_cambios_de_*`). Ningún archivo de `asistente/`, `scripts/evaluar_asistente.py`, `scripts/_experimento.py` ni
  de las fixtures del banco las llama (búsqueda en el repositorio).
- **`aplicacion/composicion.py` no lo importa el experimento.** Solo entra por `aplicacion/hoja.py`, que importa de él
  `ComposicionInvalida`, `decimal_desde_texto`, `filas_desde_composicion` y `texto_de_celda`: las cuatro idénticas. Lo que
  cambió es Componer (`composicion_desde_tablas`, `guardar_composicion`, `precarga_de_partida`, mensajes) y está en la
  lista porque al congelar era `ui/composicion.py` (re-congelado del 21/10).
- **Las mutaciones son las mismas.** `mutaciones.py` es byte a byte el congelado y opera sobre `Espacio`, `Coord` e
  `ItemComputo` (núcleo y adaptadores, sin cambios: `git diff --stat c1f436b2 -- core/` vacío; `adapters/espacio` sin
  cambios desde el congelado). La huella del banco es la congelada.

**Pruebas del experimento en verde** sobre la cabeza con los dos archivos cambiados: `tests/unit/test_experimento*.py`,
`test_mutaciones_viales.py`, `test_evaluar_asistente.py` y `test_prueba_real_asistente.py`, **130 verdes y 1 roja**, la
roja es `test_experimento_congelado_vigente` (la que este acta resuelve). Entre ellas:
`test_cada_tipo_da_n_mutantes_deterministas_y_el_comparador_los_clasifica` (E1 a E8 con la misma semilla dan los mismos
mutantes y la misma clasificación), `test_cada_referencia_es_una_hoja_valida_que_deriva_y_no_rompe_r9`,
`test_el_modelo_ideal_no_comete_errores_y_tiene_exhaustividad_total`,
`test_un_x_supuesto_5_cm_de_mas_es_un_e3_que_el_auditor_marca_por_el_supuesto` y
`test_el_auditor_del_experimento_corre_exactamente_las_reglas_del_protocolo`.

## Huellas

| Huella | Congelado anterior (`1ec20732`, commit declarado `9832db3a`) | Re-congelado (2026-10-31) |
|---|---|---|
| `banco` | `29446b12ebf646d89ef9ccae3b597989e8787757e7fdf9a66024ff098aa3a0b2` | igual |
| `protocolo` | `e769c50778198e0ad354409b6ad8589b344bf4c73eae9c04f715f7fc9b075bb6` | igual |
| `auditor` | `bc34b17e6e4351433954a5f8ca3515202f17ec86d3cc397d18d05e589931779f` | `63930d4b5e3b9528ca58dcb2ab68680bb9bbb47d19f4d3bafe8395706cdb22c6` |

El commit declarado en el nuevo `congelado.json` es el de esta acta (como el anterior declaraba el de su ruling).

## Cómo se re-congela

`congelar(<commit del acta>)` de `asistente/experimento/congelado.py`, en un commit aparte:
`chore(experimento): re-congelado con acta (2026-10-31)`.

**Árbol limpio (M5).** El worktree tiene archivos **sin seguimiento que no son de esta línea**: `.impeccable/` (1),
`data/instalacion.db.migrando-shm` y `-wal` y `docs/manual_nuevo/capturas/` (130). Ninguno está en
`archivos_del_auditor` ni en el banco, así que no entran en ninguna huella. No se borran ni se mueven (son de otras
líneas). Para que `congelar` no se niegue por ellos, se le pasa un `cambios_sin_commit` que **solo** quita esas rutas
sin seguimiento y deja cualquier otra cosa pendiente (un archivo con cambios sin commit, o algo sin seguimiento en otra
ruta) negando el congelado como siempre. El fin de M5, que el commit declarado sea exactamente lo que se hashea, se
cumple: las 50 rutas del auditor y el banco no tienen cambios sin commit.

## Después

`test_experimento_congelado_vigente` vuelve a verde. Cualquier cambio posterior en `aplicacion/hoja.py` o
`aplicacion/composicion.py` (o en otra ruta de la lista) la vuelve a poner en rojo: hace falta otra acta. **Pendiente:**
avisar al tutor, como el re-congelado del 21/10.
