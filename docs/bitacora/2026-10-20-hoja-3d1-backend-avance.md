# Hoja 3d-1: avance del backend (S1, guardar el borrador como versión) y verificación

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `b73b2008`
El contrato exacto está en `2026-10-20-hoja-3d1-contrato-rutas.md` (escrito antes de implementar, `903bb0f8`). Fuente final:
`docs/api.json`.

## Parejas prueba → implementación (rojo visto primero)

| Pareja | Prueba | Implementación |
|---|---|---|
| Contrato de S1 | `903bb0f8` (docs, antes de codificar) | — |
| Paridad `guardar_version` y `crear_primera_version` con `ui.hoja` VIVO (3b-B3C) | `caa2966f` (caracterización: la copia ya existía, **12 pasan a la primera**, sin rojo) | — |
| S1: 3d-B1 a B10, B14 y B16 para S1, B17, B18, P25 a P30 y P34 | `705587b4` (rojo: **51 de 52 fallan**, 404 porque la ruta no existía; pasa solo la del cuerpo > 20 MiB, el 413 es del middleware) | `e1886800` (`feat(api): guardar el borrador como version, S1`) |
| Ajustes de las pruebas tras la primera corrida contra la implementación | `a14a6acc` (declarados abajo) | — |
| Mutación M8 que sobrevivía | `800c20c4` (sin cambio de producción) | — |

## Ajustes de prueba hechos tras ver el resultado (declarados)

1. **Orden de sentencias (3d-B7).** La primera corrida verde falló en `sentencias.count("BEGIN IMMEDIATE") == 1`: eran **2**. No era la
   prueba: `guardar_version` lee `nueva.codigo` DESPUÉS de confirmar y, con la expiración por omisión de la sesión, eso abría una
   segunda transacción (`BEGIN IMMEDIATE` de lectura) que retiene el bloqueo de escritura hasta cerrar la sesión (haría esperar a la
   siguiente persona sin motivo). Se arregló en la implementación (`sesion.expire_on_commit = False` en `hoja_guardado.guardar`). Se
   quitó además `"COMMIT" in sentencias` (el commit de pysqlite no pasa por `before_cursor_execute`: error de la prueba).
2. **Primera versión: mi oráculo estaba mal.** Esperaba 2 703,86 con el espacio de OF-001 escrito por el editor (E1). Da **1 794,29**: sin
   los dos circuitos el cable cambia (medido con un guion aparte: con circuitos 2703,86; sin circuitos 1794,29). El editor no puede
   escribir circuitos (se declaran al importar un plano, 3e). La memoria 2 703,86 se prueba ahora con el espacio completo **puesto
   directamente en el borrador vivo** (`_en_blanco_con_el_plano`: equivale a lo que dejará fusionar el plano), y la ruta del editor se
   prueba con «lo guardado es exactamente lo que la vista mostraba» (3d-B17). Limitación: el camino «plano → primera versión» no se puede
   probar de punta a punta hasta 3e.
3. **Moneda:** `VES` no es una moneda del sistema (`Bs` o `USD`); la prueba de la lista de otra moneda declara el proyecto en `Bs`.
4. **Nuevas** (no ajustes): primera versión escrita en el editor, guardia AST (toda función de `api/` que crea versiones usa
   `SesionDeEscrituraDep` y no `SesionDep`) y el bloqueo suelto tras un rechazo (M8).
5. Paridad (`caa2966f`), antes de su primera corrida verde: comparan tuplas (`VersionGuardada` es una clase por módulo), el prefijo del
   código de TI-001 es `TI-` (la versión nueva es `TI-002`), y el volcado excluye `eslabon_version.fecha_hora` y `huella_eslabon` (la
   huella incluye la hora del sello); que el sello sea válido lo dice `estado_de_la_cadena`, que SÍ se compara entre la clásica y la copia.

## Sanidad de las pruebas (mutaciones, código restaurado después)

Guion en el scratchpad, no versionado; cada mutación rompe una línea, corre las pruebas que deben verla y restaura el archivo.

| Mutación | Prueba que la mata |
|---|---|
| M1: sin `con_anexos_de_cadena(sesion)` | la cadena íntegra tras guardar / la primera versión (rojo visto de diseño §1.2) |
| M2: sesión común en vez de `abrir_sesion_de_escritura` | el orden de sentencias y la carrera de dos personas |
| M3: sin comprobar «versión más nueva» | la prueba de confirmación (D-5) y la carrera |
| M4: no marcar `guardado_como` | el borrador cerrado y los dos hilos sobre el mismo borrador |
| M5: sin R17 en lo guardado (`vivo.borrador` en vez de `con_r17`) | 3d-B10 |
| M6: sin comprobar `rev` | `rev` antes que el contenido |
| M7: sin `expire_on_commit = False` | el orden de sentencias (una sola transacción) |
| M8: sin `rollback` tras rechazar antes de escribir | **sobrevivía** (la dependencia cierra la sesión y eso ya deshace); la prueba `bloqueo_queda_libre` la mata |

## Diferencias y límites declarados

- **D-5, regla de «versión más nueva».** Es la de `Resumen.version_mas_nueva` (ya aprobada en 3b/3c): la versión vigente de ahora es
  *distinta* de la abierta. Consecuencia: abrir a propósito una versión vieja o una descartada también pide confirmar (el texto «Otra
  persona guardó la versión X después de que usted abrió la Y» no es literalmente cierto en ese caso). Falla hacia el lado seguro; se
  fija con una prueba. Alternativa si Eugenio la prefiere: exigir además que la vigente sea posterior a la abierta.
  **Superada el 2026-10-21** por la afinación aprobada de la ola de decisiones (vigente de ahora contra vigente al abrir; ver
  `2026-10-21-ola-decisiones-backend-avance.md`): abrir a propósito una versión vieja ya no pide confirmar.
- **Sin cambios → 422** con el texto de `motivo_para_no_guardar` (la clásica devolvía `None` y mostraba una nota informativa). Se juzga
  antes que la falta de fuente (el orden del motivo, H:1801) y la falta de fuente antes que «solo lectura» (como la clásica).
- **Solo lectura → 409** (la clásica lanzaba `HojaInvalida`); el diseño §4.5 lo pide así.
- **Errores:** `HojaInvalida` → 422 (sin cambios, sin fuente, hoja vacía, ya tiene versiones, sin lista vigente, otra moneda); otro
  `ValueError` o `CatalogoIncompleto` → 409 `No se guardó nada: …`; `SQLAlchemyError` → 503 fijo. **Una excepción inesperada** (no de
  esos tipos) no se traduce: tras deshacer, sube y FastAPI responde su 500 genérico sin detalle (probado con `RuntimeError`).
- **`rev` no sube al guardar:** el borrador queda cerrado con `guardado_como` y todo lo demás responde 409 «ya se guardó» antes de mirar
  `rev`.
- **El bloqueo se espera con el cerrojo del borrador tomado** (hasta 5 s de `busy_timeout` de SQLite si otra persona escribe); orden
  de bloqueos: borrador → base. Dos hilos sobre el mismo borrador se serializan en el cerrojo (el segundo ve «ya se guardó»); dos
  personas sobre la misma versión se serializan en la base (el segundo ve la versión nueva y recibe 409).
- **`fuente` ≤ 300 caracteres** (el ancho de `RegistroCambio.fuente`; SUPUESTO declarado D-9). Se guarda tal cual en la versión; en la
  primera versión la limpia `crear_primera_version` (`strip`).
- **`expire_on_commit = False`** se pone sobre la sesión que recibe `hoja_guardado.guardar` (efecto lateral deliberado y comentado).
- **Heredado, no corregido:** abrir (R2) una versión anterior a la cadena sin instantánea sigue dejando la cadena sin integridad
  (`2026-10-19-hoja-3b1-cadena-heredada.md`); S1 no lo repara.
- `aplicacion/hoja_vista.con_r17` es el `_con_conexion` de la clásica, extraído de `elaborar` (que ahora lo usa): una sola copia.

## Medición

Las pruebas de S1 tardan ≈ 7 s cada una en este equipo (cada una inicia sesión con argon2); la ruta misma no se midió aparte.

## No hecho aquí

Restaurar, cotizar, retirar, convertir y la cadena (S2 a S6, 3d-2), Excel y planos (3e), `rutas.ts`, el asistente. No se tocó `ui/hoja.py`,
`ui/composicion.py`, `ui/paginas/hoja.py`, `core/`, `asistente/` ni `aplicacion/hoja.py` (idéntica por AST a la clásica salvo las
tres importaciones y el docstring).
