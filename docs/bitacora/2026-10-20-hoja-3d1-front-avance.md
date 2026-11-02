# Hoja 3d-1, frente: avance (modal «Guardar versión», primera versión y resultados de S1)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `b73b2008` · Solo `frontend-desktop/src/paginas/hoja/` (no se tocó
`src/comun/`, ni `rutas.ts`, ni `ui/`, `core/`, `asistente/`, `api/`, `aplicacion/`). El contrato es `2026-10-20-hoja-3d1-contrato-rutas.md`
(S1) más E9 del diseño §4.4. La Hoja sigue sin activarse en el menú.

## Parejas prueba -> implementación

| Pareja | Prueba (rojo visto) | Implementación |
|---|---|---|
| Lógica pura de guardar (rutas, cuerpo, motivo para no guardar, textos de éxito, clasificación de S1) | `42b65a5c` (módulo inexistente) | `13fdc535` |
| La versión más nueva sale del campo `version_mas_nueva` del 409 | `53929b7c` (1 en rojo) | `7f9e0fb5` |
| Lista de versiones si no se pudo releer tras guardar (`conVersionGuardada`) | `528ca6e9` (2 en rojo) | `b56b10e8` |
| Modal, primera versión y resultados de S1 (32 pruebas de página) | `ca2e3f05` (31 en rojo; 1 ya pasaba: sin cambios no hay botón) | `b56b10e8` |

SHAs completos: `git log --oneline b73b2008..HEAD -- frontend-desktop`.

## Qué se hizo

- **Botón «Guardar versión…»** (id `hoja-guardar-version`) en la región «Estado del borrador», visible solo con cambios sin guardar o, en un
  borrador en blanco de un proyecto sin versiones, como «Guardar primera versión…».
- **Modal** (`DialogoDeGuardar.tsx`, `role="dialog"` `aria-modal`): resumen («Se registrarán N cambios en una versión nueva (sale de la X)» o «Es la
  primera versión del proyecto P…»), total en es-VE con el exacto en `title` y texto accesible, fuente (`maxLength` 300, el tope del contrato),
  «Responsable: Nombre <login>» de solo lectura (no hay campo `responsable` en el cuerpo, RF-82) y la lista de cambios de E9 (objeto, clave, campo,
  antes, después; la clave se muestra con `rotuloDeOrigen`, la cruda va en `title`; 200 filas a la vez y se dice cuántas hay). El botón de guardar
  queda deshabilitado con el motivo visible y asociado por `aria-describedby` (sin fuente, sin cambios, solo lectura). La lista se vuelve a leer si
  cambia el `rev` con el modal abierto.
- **Accesibilidad:** el foco entra a la fuente; Tab atrapado (todos los enfocables, no solo botones); Esc cierra; el resto de la página queda `inert`; al
  cerrar, el foco vuelve al botón mediante un efecto tras el commit (no `.focus()` en el manejador): prueba con espía de `HTMLElement.prototype.focus`
  que falla si el botón sigue dentro de `[inert]`. Tras guardar, el botón ya no existe y el foco va al selector de versión. Se extrajo `useDialogo.ts`
  del `DialogoDeVersion` (que ahora lo usa): salda la deuda de DRY que dejó 3c-3 dentro de la carpeta.
- **Una sola petición de guardado** (`useGuardado.ts`, `enVuelo`): botón deshabilitado y `aria-live` «Guardando la versión…». Antes de enviar espera los
  envíos que salieron al desmontar una pestaña (`esperarEnvios`) y manda el `rev` vigente de la página.
- **200:** aviso `role="status"` «Se guardó la versión {c} con {n} cambios registrados.» (1 cambio en singular; el texto lo compone el cliente con tildes y no
  usa el `mensaje` del servidor), el borrador guardado se descarta una sola vez, se vuelve a leer la lista de versiones SIN desmontar la página (la pestaña
  elegida se conserva), se abre la nueva versión (R2) y el estado de cambios queda en cero. Si la lista no se puede releer, se agrega la versión a mano
  (`conVersionGuardada`). Tras retomar un borrador y guardarlo no se vuelve a ofrecer el viejo.
- **Primera versión:** «Guardar primera versión», fuente «de la medida», mensaje «Se guardó la primera versión 001 del proyecto P (total 2.703,86). Quedó
  registrada su creación, con su fuente y su responsable.».
- **409 versión más nueva:** muestra el texto del servidor, NO reenvía solo; ofrece «Guardar de todos modos» (reenvía con `confirmar_version_mas_nueva`) y
  «Abrir la versión {x}» (la {x} sale del campo `version_mas_nueva` del cuerpo o, sin él, del texto). Abrir esa versión pasa por la confirmación de
  descartar de siempre (nada se pierde en silencio). El botón principal queda deshabilitado mientras se decide.
- **409 `rev`:** texto + «Recargar el borrador» (vuelve a leerlo; la fuente se conserva). **409 ya guardado:** «Abrir la versión {c}» (sin pedir descartar:
  ya está guardado). **409 de otro caso / 404 borrador ausente:** texto del servidor + «Abrir de nuevo»; la fuente no se pierde (3d-F8). **403, 422, 409
  de solo lectura o de núcleo, 503:** el `detalle` de la API tal cual (503 con el texto fijo del cliente si viniera vacío); el diálogo sigue abierto con lo
  escrito. **401:** avisa al marco.

## Ajustes a pruebas (declarados)

Antes de implementar (con rojo visto): `logicaGuardar.test.ts` ganó el caso de `version_mas_nueva` (`53929b7c`) y el de `conVersionGuardada` (`528ca6e9`).
Después de ver verde: en `Guardar.test.tsx` (commit `b56b10e8`) el caso «ya se guardó como la versión 004» fijaba `por_omision: "004"` en mi servidor simulado,
con lo que la hoja abría la 004 en lugar de la 002 y nunca aparecía el botón: error de mi arnés, el valor esperado de la conducta no cambió. En la primera
corrida en verde también falló 1 caso por una omisión de la implementación (el botón principal no tenía `aria-describedby` con el motivo); se corrigió la
implementación, no la prueba.

## Diferencias entre el contrato real y lo simulado

El contrato se leyó antes de implementar la página (no hubo que reescribir pruebas de página); la lógica se ajustó a él:
1. El 409 de versión más nueva trae `version_mas_nueva` en el cuerpo (el diseño §4.5 no lo decía): se usa primero, y el texto es la alternativa.
2. La 200 trae también `proyecto`: se usa para el mensaje de la primera versión.
3. `fuente` ≤ 300 caracteres (el diseño no fijaba tope): `maxLength` 300 en el campo.
4. Los textos de 422 y 409 del servidor llevan «por que», «esta» sin tildes (son los de la clásica, D-3): se muestran tal cual.
5. El `mensaje` de la 200 no se muestra (dice «1 cambios»): el cliente compone el suyo con tildes y singular. Es una diferencia deliberada de ortografía y número
   gramatical respecto de la clásica (P:497-500).
6. E9 se simuló al principio como lista sola; al leer `api/esquemas_hoja.py` (`CambiosHojaRespuesta`) la real es `{rev, cambios: [{objeto, clave, campo,
   antes, despues}]}`: la lógica acepta las dos formas y la prueba de página ahora simula la real (cambio de simulación, la conducta esperada es la misma).

## Límites y deudas

- **Edición en vuelo al guardar:** si una edición está en vuelo (o en la pausa de 400 ms) justo cuando se pulsa Guardar, el servidor puede contestar 409 de
  `rev`; el modal lo dice y ofrece «Recargar el borrador» sin perder la fuente. Solo se esperan los envíos que salieron al desmontar una pestaña.
- **DV-13 no está hecho:** mientras una sección tenga texto no aceptado, Guardar sigue habilitado (el motor de edición de las secciones no publica ese estado a
  la página). Lo que no se aceptó no está en el borrador del servidor y no se guarda; el 422 de la sección ya está a la vista.
- Los 409 se distinguen por el comienzo del `detalle` (como `claseDeConflicto` en 3c): un cambio de redacción en el servidor los degradaría a «otro» (se
  seguiría mostrando el texto, pero sin sus botones).
- Sin medición de 1366x768 en navegador (T11). Restaurar, cotizar, retirar, convertir y la cadena son 3d-2.
