# Hoja 3c-2: avance del backend (E2 a E5, cantidades, parámetros y plan) y verificación

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `c8bbfc3`
El contrato exacto de las rutas está en `2026-10-19-hoja-3c2-contrato-rutas.md` (escrito antes de implementar, `377bbf0`).

## Parejas prueba → implementación (rojo visto primero)

| Pareja | Prueba | Implementación |
|---|---|---|
| Contrato de E2 a E5 | `377bbf0` (docs, antes de codificar) | — |
| Paridad `cantidades_desde_filas`, `parametros_desde_texto`, `plan_desde_filas`, `con_plan_secuencial` con `ui.hoja` VIVO (3b-B3C) | `c87f4f8` (caracterización: la copia ya existía, **pasa a la primera**; 42 pruebas, 21 casos x 2 módulos) | — |
| E2 a E5 y la batería de acceso (3c-B1 a B5, B12, B13, B19) | `d5eeb9d` (rojo: **107 de 107 fallan** porque las rutas no existen, 404 en todas, también en las de acceso que esperan 401/403) | `59a658b` (`feat(api): edicion de cantidades, parametros y plan E2 a E5`) |

## Ajustes de prueba hechos tras ver el resultado (declarados)

- `test_aplicacion_hoja_paridad_secciones.py`: la primera corrida (contra la clásica Y la copia, ya existentes) dio 4 rojos por
  un error MÍO de oráculo: el periodo de la curva se llama `Dia 30 [EL-TUB-EMT-3/4]` (con corchete), no `Dia 30`. Se corta
  el corchete en la prueba, como ya hace `test_aplicacion_hoja_paridad.py` con el punto de equilibrio. Ningún valor de dominio
  cambió (2 703,86; 26,39748; 19,798; etc.).
- `test_api_hoja_edicion_secciones.py`: **ningún ajuste tras ver verde**; las 107 pasaron a la primera corrida con la
  implementación. Antes de la primera corrida (rojo o verde) y sin ver ningún resultado, quité una prueba que decía mucho y
  comprobaba poco (`test_con_el_rev_bueno...`) y fijé `rev == 1` en la de topes (500 periodos vacíos son válidos y suben `rev`).
- `tests/unit/test_api_acceso_por_ruta.py` y `tests/unit/test_api_hoja.py` (lista de rutas de `docs/api.json`): filas nuevas
  de E2 a E5; se añadieron junto con la implementación, no antes (son contabilidad de rutas, no comportamiento).

## Sanidad de las pruebas (mutaciones, código restaurado después)

Cada una rompe una línea, corre las pruebas que deben verla y restaura el archivo (script en el scratchpad, no versionado):

| Mutación | Prueba que la mata |
|---|---|
| M1: el contenido se valida ANTES que `rev` | `test_el_rev_se_comprueba_antes_que_el_contenido_en_e2_e3_y_e4` (`[422, 422, 422] == [409, 409, 409]`) |
| M2: el plan se compara sin ignorar el orden de las partidas de un periodo | `test_e4_la_matriz_sin_tocar_no_cambia_nada_ni_siquiera_en_ti001` (`rev` sube a 1 en TI-001) |
| M3: E2 arma la tabla solo con las filas tocadas | `test_e2_una_cantidad_negativa_dice_la_fila_de_la_tabla_completa_aunque_se_mande_una_sola` (la fila deja de ser la 3) |
| M4: E5 sin comprobar que ya hay plan | `test_e5_con_plan_es_409_y_nada_cambia` (200 en vez de 409) |

No se mutó el cerrojo de la ruta: `_cambiar` toma el mismo cerrojo por dentro, así que quitar solo el de la ruta no cambia nada
observable (doble defensa).

## Diferencias y límites declarados

- **Respuestas:** `{rev, resumen, presupuesto}` (E2), `{rev, resumen, parametros}` (E3), `{rev, resumen, plan}` (E4 y E5). Cada una es
  la vista de SU pestaña, calculada con el mismo `rev` que el resumen. Las demás vistas (equilibrio, plan tras un cambio de
  cantidades, etc.) se piden al montar su pestaña. No se añadió el punto de equilibrio a la respuesta de E2/E3.
- **E2, tabla completa en el servidor:** el cliente manda solo lo tocado; el servidor arma la tabla en el orden de
  `items_sin_escribir`, así `fila {n}` es la de la clásica (3c-B5, fila 3 para AF-LLAVE). **Diferencia:** una `clave` desconocida
  o repetida es 422 (`Las cantidades enviadas no corresponden a los renglones del presupuesto: vuelva a cargarlo.`); la clásica
  la ignoraba en silencio. La razón: el rev ya se comprobó, así que solo ocurre con un cliente defectuoso.
- **E4, plan:** (a) dos filas con la misma partida son 422 (la clásica no podía producirlo; sumarían 1 cada una y duplicarían la
  ejecución); (b) la comparación «¿cambió el plan?» ignora el orden de las partidas dentro de un periodo (la matriz las ordena por
  partida, el plan guardado como se fueron escribiendo; sin esto, TI-001 subiría `rev` con la matriz sin tocar). La clásica
  reasignaba el plan reordenado; el efecto visible (cambios, curva) es el mismo; (c) sin plan es 409 (`SinPlan`), tras `rev` y antes
  del contenido; (d) las etiquetas deben ser distintas y ninguna puede llamarse `partida` (con etiquetas repetidas
  `plan_desde_filas` cuenta dos veces la misma ejecución).
- **E5:** con plan, 409. En un proyecto sin versiones o sin partidas valoradas el plan secuencial queda **vacío** (`plan = ()`,
  `hay_plan` verdadero, curva vacía) y no revienta; igual que la clásica.
- **Topes (D-9, SUPUESTOS declarados):** 20 000 renglones de cantidades, 1 a 500 periodos, 5 000 filas de plan, 500 valores por fila,
  500 caracteres por texto. No están en el diseño; los puse yo.
- **`_editar` común:** E1 se refactorizó para usar el mismo esqueleto que E2 a E5 (cerrojo del borrador, traducción de errores,
  resumen y vista del mismo `rev`). Las pruebas de E1 no se tocaron.
- **Orden de bloqueos:** borrador → registro, igual que E1. La prueba `test_el_registro_nunca_se_toma_antes_que_el_borrador`
  envuelve ambos cerrojos con un espía y exige que el del borrador nunca se adquiera con el del registro ya tomado.
- **Hardening de 3c-3 no adelantado:** `rev` con dos hilos que compiten (3c-B13 completa) sigue siendo de 3c-3. Aquí se prueba
  solo que una edición espera al cerrojo del borrador y el orden de bloqueos.
- **No hecho aquí:** 3c-B18 (rendimiento), E6 a E11, `rutas.ts`.

## Equivocación en el árbol compartido (honestidad)

Al querer enmendar el mensaje de mi commit `d5eeb9d` con `git commit --amend --only` enmendé por error el commit del agente de
front que acababa de aterrizar encima (`12f77de`, «la frase del rechazo es propia de cada sección»). Lo detecté de inmediato por el
`git log`, recreé el commit con **el mismo árbol, autor y mensaje** (`git commit-tree` + `git update-ref` con comparación del valor
antiguo) y ahora es `ca17084`. El contenido no cambió; cambió el SHA. El mensaje de `d5eeb9d` sigue impreciso (dice «ver bitácora»);
los hechos exactos son los de la tabla de arriba.
