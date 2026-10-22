# Hoja 3c-3: avance del backend (E6 a E11, `rev` completo, retomar) y verificación

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `651f771`
El contrato exacto de las rutas está en `2026-10-19-hoja-3c3-contrato-rutas.md` (escrito antes de implementar, `fb58998`).
Fuente final: `docs/api.json`.

## Parejas prueba → implementación (rojo visto primero)

| Pareja | Prueba | Implementación |
|---|---|---|
| Contrato de E6 a E11 | `fb58998` (docs, antes de codificar) | — |
| Paridad `composicion_con_cantidades`, `cambiar_insumo` e `insumos_candidatos` con `ui.hoja` VIVO (3b-B3C) | `c8b649f` (caracterización: la copia ya existía, **45 pasan a la primera**, sin rojo) | — |
| E6 a E11, `rev` con hilos, acceso, B18, E4 completa | `33eeb1c` (rojo: **124 de 130 fallan** en `test_api_hoja_apu_retomar.py`; 3 de las 4 nuevas o cambiadas de E4 en `test_api_hoja_edicion_secciones.py`) | `95ad52d` (`feat(api): edicion del APU, cambio de insumo, cambios, retomar y reemplazar E6 a E11`) |
| Mutación que sobrevivía (E11) y B18 con puntos distintos | `1e28e54` | — (sin cambio de producción) |

**Los 6 de 130 que pasaron en rojo** (caracterización de lo que ya existía, no pruebas de lo nuevo): E11 en acceso (`401`, `403`
de rol y `403` de clave de API sobre `POST /borradores`, que ya existe), `test_e11_un_borrador_con_cambios_revertidos_tampoco_estorba`,
`test_e11_el_borrador_de_otra_ficha_no_estorba_ni_se_confirma` (R2 ignoraba el campo `reemplazar`, así que abría sin problema) y
`test_put_espacio_con_500_puntos...` (el PUT del espacio ya era E1). De las 4 pruebas nuevas de E4, `test_e4_una_fila_con_la_partida_vacia_se_ignora...`
pasó a la primera (ya se ignoraba).

## Pruebas que pasaron a la primera sin que fueran rojas (caracterización, declaradas)

- Las 45 de paridad `3b-B3C` (la copia ya era igual a la clásica).
- **3c-B13 completa** (`test_cuatro_hilos_...`, `test_dos_hilos_...`, `test_con_el_rev_nuevo...`): el cerrojo del borrador y la
  comprobación de `rev` dentro de él ya existían desde 3c-1; la prueba nueva lo fija con hilos de verdad (cuatro rutas distintas con el
  mismo `rev`: exactamente un 200 y tres 409, y de las cuatro ediciones solo deja huella la ganadora) pero no vio rojo. No mutada
  (doble defensa: `_cambiar` y `reemplazar` comprueban el `rev` cada uno dentro de su cerrojo).
- Acceso, CSRF/Origin, ficha ajena y cambio de caso de E6 a E9 se ejecutaron junto con la implementación; su rojo es el de que las
  rutas no existían (404 genérico).

## Ajustes de prueba hechos tras ver el resultado (declarados)

1. `test_e9_en_un_borrador_en_blanco_todo_lo_escrito_cuenta` falló en la primera corrida verde por un **error mío de oráculo**: el borrador
   en blanco parte de otros parámetros por omisión que los de OF-001, así que mandar los cuatro textos cambia varios, no solo
   `administracion`. Ahora comprueba que todo cambio es de objeto `parametro`, que `administracion` termina en `0.20` y que la lista
   tiene el largo de `resumen.cambios`. Sin defecto de producto.
2. **E11 y los borradores sin cambios.** La primera implementación descartaba en silencio un borrador anterior de la misma versión sin
   cambios. Antes de ver verde, al repasar `tests/unit/test_api_hoja.py` vi que eso contradecía `test_el_quinto_borrador_de_una_ficha_descarta_el_primero`
   (abre cinco veces la misma versión). Decisión: **no se descarta nada sin `reemplazar`**; un borrador sin cambios no estorba y se abre otro como
   siempre (el tope de 4 por ficha acota). Se cambió la prueba (`test_e11_sin_cambios_el_borrador_anterior_no_estorba_y_sigue_vivo`) y el contrato
   (commit `95ad52d`). No se tocó `test_api_hoja.py` salvo la lista de rutas.
3. **Mutación que sobrevivía:** M4 (descartar el anterior ANTES de abrir) sobrevivía porque `test_e11_si_abrir_falla...` pedía una versión
   inexistente (`999`), distinta de la del borrador anterior. La prueba ahora fuerza el fallo al abrir la MISMA versión (parche de
   `abrir_version`, 409) y comprueba que el borrador anterior sigue con sus cambios; M4 muere (`1e28e54`).
4. **3c-B18:** la primera medición usó 500 puntos idénticos (copias del mismo punto) y dio una mediana de **16,3 s**: el caso degenera la regla
   de puntos duplicados (`adapters/espacio/planos/geometria_plano.py:_duplicados`, 125 250 pares) y `estado_de_filas` (4 s propio), ambas
   cuadráticas. No es el caso real; se cambió a una cuadrícula de 25 x 20 puntos distintos y la mediana es **1,9 s** (medida en este equipo mientras
   otros agentes corrían pruebas). Perfil de una corrida con la cuadrícula: `editar_espacio` 1,0 s, resumen 2,2 s (la derivación de agua,
   `_segmentos_de_fuente`/`unir_segmentos`, domina). **Solo se registra, ningún umbral** (RNF-11 pide 2 s de elaboración, otra cosa). Hallazgo para
   quien corresponda: `_duplicados` y `estado_de_filas` son O(n²) con puntos coincidentes (500 puntos idénticos = 16 s); ni `core/` ni `adapters/`
   se tocaron aquí.

## Sanidad de las pruebas (mutaciones, código restaurado después)

Script en el scratchpad, no versionado; cada mutación rompe una línea, corre las pruebas que deben verla y restaura el archivo:

| Mutación | Prueba que la mata |
|---|---|
| M1: E11 da 409 aunque el anterior no tenga cambios | `test_e11_sin_cambios...` / `..._revertidos_tampoco_estorba` |
| M2: E4 no exige la matriz completa | `test_e4_una_partida_desconocida_o_que_falta...`, `test_e4_la_cobertura_se_mira...`, `test_exactamente_los_topes...` |
| M3: `hay_mas` con `>=` en vez de `>` | `test_e8_el_limite_corta...` |
| M4: reemplazar descarta antes de abrir | `test_e11_si_abrir_falla_el_anterior_queda_intacto` (tras el ajuste 3; antes sobrevivía) |
| M5: E10 renueva el plazo (`obtener` en vez de `listar`) | `test_e10_el_mas_reciente_va_primero_y_listar_no_renueva_el_plazo` |
| M6: E7 sin pedir versión abierta | `test_e7_sin_version_abierta_es_409...` |
| M7: E7 acepta un insumo de otro tipo | `test_e7_un_insumo_que_la_lista_no_valora_o_de_otro_tipo...` |

No se mutó el cerrojo (ver arriba).

## Diferencias y límites declarados

- **E6/E7 y la barra en el código de partida:** `AF-TUB-PVC-1/2` trae «/». La ruta usa `{partida:path}` (admite barras; el front manda
  `encodeURIComponent`). Consecuencia: `PUT .../apu/X/insumo` es una partida llamada `X/insumo` (404 de partida); `POST` es E7. En
  `docs/api.json` aparece como `{partida}`; en la tabla de `test_api_acceso_por_ruta.py`, como `{partida:path}`.
- **E8:** `limite` de 1 a 301 (301 se trata como 300, `LIMITE_INSUMOS`); la clásica pide 301 para saber si hay más. Aquí `hay_mas`
  es exacto para cualquier `limite`. `texto` es el `ilike` de la clásica (no ignora tildes).
- **E9 y E10 envuelven la lista** (`{rev, cambios}` y `{borradores}`) en vez de devolver la lista sola del diseño: llevan el `rev` con que
  se calculó (E9) y dejan crecer el esquema. E10 añade `rev` a cada fila (para reanudar sin pedir R3 antes).
- **E10:** solo los borradores de MI ficha abiertos en el caso de ahora y no guardados. Listar no renueva el plazo (usa `listar`, no `obtener`).
  Calcula la cuenta de cambios con la caché por `rev` (`hoja_vista.calculo`); un borrador nunca calculado se elabora al listar (hasta 4 por ficha).
- **E11:** el chequeo ocurre antes de abrir la versión (`abrir_version` escribe la instantánea): con 409 no se escribe nada. El descarte
  con `reemplazar` ocurre justo antes de crear el nuevo (si abrir falla, el anterior queda). **Hay una ventana** entre el chequeo y la
  creación en la que dos peticiones simultáneas de la misma ficha podrían crear dos borradores (el tope de 4 acota; no pierde datos).
- **E7:** el insumo se busca por código entre los del tipo que la lista de la versión valora; si no, 422 con un texto propio
  (`El insumo 'X' no esta en la lista de precios de la version 001 (o no es de tipo material): elijalo de la lista.`; el diseño no da texto).
  `tipo` desconocido o línea inexistente conservan el texto de la clásica (se obtiene de `cambiar_insumo`).
- **E6:** la tabla de cada rubro la arma el servidor con `[{"cantidad": c}]`; si el número de cantidades no coincide con las líneas del
  APU responde el texto de la clásica («la tabla tiene N lineas y el APU M…», paridad; el diseño decía «imposible por contrato»).
- **E4 (MENOR de 3c-2, cerrado):** 422 `plan: la matriz debe traer exactamente las partidas del presupuesto, una fila por cada una: vuelva a cargarla.`
  si el conjunto de partidas no vacías de `filas` no es exactamente el de las partidas valoradas (las filas de R8). Después de «ya hay plan», `rev`
  y las filas repetidas; antes de las fracciones. Cambió el expected de `test_exactamente_los_topes_de_forma_se_aceptan` (500 periodos con filas
  vacías ya no son 200). El diseño no lo contradice (§4.4: «la matriz es completa»).
- **Topes (D-9, SUPUESTOS declarados):** 500 líneas por rubro de un APU, `indice` ≤ 1 000 000, texto ≤ 500 caracteres, `limite` ≤ 301.

## Corrección heredada de 3c-2

El mensaje del commit `d5eeb9d` (prueba en rojo de E2 a E5) dice «pasan solo las que no necesitan la ruta (401/403 se resuelven antes del 404 de
enrutado no, ver bitacora de avance)». Es impreciso y la frase se contradice a sí misma: **fallaban 107 de 107** (no pasaba ninguna, ni las de
acceso, porque sin la ruta todo es 404). La tabla de `2026-10-19-hoja-3c2-backend-avance.md` ya decía 107 de 107; el mensaje del commit no se reescribe.

## No hecho aquí

El guardado y las versiones (3d), el Excel y los planos (3e), `rutas.ts`, el asistente. No se tocó `ui/hoja.py`, `ui/composicion.py`,
`ui/paginas/hoja.py`, `core/`, `asistente/` ni `aplicacion/hoja.py` (idéntica por AST a la clásica salvo las tres importaciones y el docstring).
