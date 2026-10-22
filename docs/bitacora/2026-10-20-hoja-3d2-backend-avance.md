# Hoja 3d-2: avance del backend (S2 a S6, versiones nuevas desde una guardada y la cadena) y verificación

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `6a7f6af1`
El contrato exacto está en `2026-10-20-hoja-3d2-contrato-rutas.md` (escrito antes de implementar, `d91d1c7`). Fuente final: `docs/api.json`.

## Parejas prueba → implementación (rojo visto primero)

| Pareja | Prueba | Implementación |
|---|---|---|
| Contrato de S2 a S6 | `d91d1c7` (docs, antes de codificar) | — |
| S2 a S6 (API: acceso, forma, 404, 422 de dominio, carrera, todo o nada, cambio de caso, cadena) y paridad contra `ui.hoja` VIVO en tres sabores | `2370d2e` (rojo: **74 fallan** en las dos pruebas de la API: 404 porque las rutas no existían, y `ImportError` en `aplicacion.hoja_versiones`; la paridad entera falla por el `ImportError` del sabor «nueva») | `9420eba` (`feat(api): restaurar, cotizar, retirar cotizacion, convertir y la cadena de la hoja, S2 a S6`) |
| Ajustes tras la primera corrida contra la implementación | `e3320ef` (declarados abajo) | — |

## Ajustes de prueba hechos tras ver el resultado (declarados)

1. **Volcado de «antes».** La primera corrida falló en `volcado(ruta) == antes`: la base se migra al abrirla la primera vez (aparecen `alembic_version`, `ia_*`). No era la implementación: el caso se migra ahora en el fixture (`preparar_base`) antes de tomar el volcado.
2. **La lista de precios cambia de nombre.** En la prueba de cotizar comparaba las 21 columnas de todas las filas entre la 001 y la 002; la columna `lista` cambia (la nueva es la lista del proyecto con cotizaciones, «… + cotizaciones de …»). Se compara todo salvo ese campo y se afirma el prefijo de la lista nueva. Mi oráculo estaba mal; ninguna expectativa de dominio cambió.
3. **Paridad:** se excluye `eslabon_version.anterior` del volcado (es la huella del eslabón previo, que lleva su hora) además de las columnas de reloj ya excluidas en 3d-1. Solo asomó en la secuencia cotizar → retirar (3 versiones).
4. Formato `ruff` (líneas de más de 100 caracteres).
5. **Mutación M4 que sobrevivía** (`expire_on_commit = False`): resultó innecesario (nada se lee de la sesión tras confirmar; `hoja_versiones` solo usa cadenas ya leídas) y se **quitó** de `aplicacion/hoja_versiones.py`; la prueba de «una sola transacción» (`BEGIN IMMEDIATE` una vez, ningún `BEGIN`) lo vigila.

## Sanidad de las pruebas (mutaciones, código restaurado después)

Guion en el scratchpad (no versionado); cada mutación rompe una línea, corre las pruebas que deben verla y restaura el archivo.

| Mutación | Prueba que la mata |
|---|---|
| M2 restaurar con `SesionDep` | orden de sentencias (`BEGIN IMMEDIATE` primero) y la guardia AST |
| M3 sin `rollback` al rechazar antes de escribir | `test_un_rechazo_antes_de_escribir_suelta_el_bloqueo_de_escritura` |
| M5 convertir con `EDITAR_HOJA` en vez de `CONVERTIR_Y_REAJUSTAR` | `test_convertir_exige_convertir_y_reajustar…` |
| M6 convertir con `date.today()` en vez de `_hoy()` | la conversión con la tasa del 05/10/2026 |
| M7 evidencia ignorada | `test_la_evidencia_se_agrega_a_la_fuente_del_registro` |
| M8 `lado` ignorado (siempre venta) | `test_el_lado_compra_usa_la_tasa_de_compra` |
| M9 404 devuelto como 422 | 404 de proyecto y de versión |
| M10 `declaracion` de la cadena perdida | selladas retroactivamente |
| M11 `extra` permitido en el cuerpo | cuerpos con otra forma / el responsable es la sesión |
| M12 `GET /cadena` sin control de acceso | 401 sin sesión |
| M13 sin comprobar la versión | 404 de versión (y paridad) |
| M14 responsable fijo en vez de la sesión | registro de la restauración |
| M15 precio ignorado (siempre «1») | datos de cotización inválidos |
| M16 tope de la fuente 300 → 3000 | cuerpos con otra forma |
| M17 `CatalogoIncompleto` como 500 | núcleo que falla después de escribir |
| **M1 sin `con_anexos_de_cadena`** | **SOBREVIVE (mutación equivalente, ver abajo)** |
| M4 sin `expire_on_commit` | sobrevivía; el código se quitó |

**M1 es equivalente para estas cuatro operaciones.** Restaurar, cotizar, retirar y convertir no copian filas `esp_*` (el espacio de la versión nueva es el de su `version_origen`): el anexo de espacio de la versión nueva está vacío con o sin el proveedor de anexos, y `verificar_cadena` da igual. No hay forma de observarlo con datos. Se conserva el envoltorio porque el diseño (§1.2) lo manda para toda ruta de escritura y porque la clásica lo hace; la guardia contra olvidarlo en S1 sí tiene rojo propio (3d-1, M1).

## Diferencias y límites declarados

(Todas están también en el contrato.)

- **404 para proyecto o versión inexistentes** (la clásica los elegía de un selector).
- **Errores de dominio sin prefijo ni sufijo** (el texto del núcleo tal cual, 422); en convertir el prefijo `No se convirtio nada: ` viene del propio `convertir`. El front compone «No se guardó nada: » si quiere (P:1985).
- **`CatalogoIncompleto` → 409** `No se guardó nada: …` (la clásica no lo capturaba). Un `ValueError` del núcleo ya llega como `HojaInvalida` (422) por `_en_una_transaccion`.
- **Sin `error.orig`:** `SQLAlchemyError` → 503 fijo.
- **Topes** (SUPUESTO D-9): `fuente`/`motivo` 300, `proveedor` 120, `numero` 60, `evidencia` 90 (así la fuente armada por el núcleo no pasa de 300), `moneda` 20, referencias 500.
- **S5 exige `CONVERTIR_Y_REAJUSTAR`** (hoy igual a `EDITAR_HOJA`: ambas son solo `arma`; la prueba las separa a propósito). La fecha de la tasa la pone el servidor (hoy).
- **Sin `rev` ni 409 de «caso cambió»:** S2 a S5 no usan borrador; actúan sobre el caso de la ficha en ese momento (probado: tras cambiar de caso escriben solo en el nuevo, 404 si ahí no existe el proyecto, ninguna base recibe filas ajenas).
- **Sin «versión más nueva»:** crear la nueva vigente es el objeto de estas operaciones; el código se asigna dentro de `BEGIN IMMEDIATE` (dos a la vez → `003` y `004`, nunca dos iguales).
- **Respuesta con `proyecto`** además de `codigo` y `mensaje` (el diseño decía `{codigo, mensaje}`).
- **«Retirar/descartar versión» del encargo:** el diseño asigna S4 a *retirar la cotización*; no existe en la clásica ni en §4.5 una operación «descartar versión» (la hoja solo marca descartadas vía Actualizar precios). No se implementó otra.
- **Heredado, no corregido:** abrir (R2) una versión anterior a la cadena sin instantánea deja la cadena rota (`2026-10-19-hoja-3b1-cadena-heredada.md`); por eso las pruebas miran la cadena **antes** de abrir nada.
- La paridad corre sobre COPIAS de OF-001 y TI-001 (otras bases del caso, nunca `data/`); los literales (2 703,86; 2 821,42; 50 503,27) salen de las memorias.

## No hecho aquí

Excel y planos (3e), el asistente, `rutas.ts` (lo hace el front), `ui/*`, `core/`, `asistente/`, `aplicacion/hoja.py`.
