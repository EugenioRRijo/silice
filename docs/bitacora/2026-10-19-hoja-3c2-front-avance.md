# Hoja 3c-2, frente: avance (cantidades, parámetros y plan editables)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `c8bbfc3` · Solo `frontend-desktop/src/paginas/hoja/`
(no se tocó `src/comun/`, ni `rutas.ts`, ni `ui/`, `core/`, `asistente/`). El contrato es `2026-10-19-hoja-3c2-contrato-rutas.md`.

## Parejas prueba -> implementación

| Pareja | Prueba (rojo visto) | Implementación |
|---|---|---|
| Lógica pura (rutas E2 a E5, cuerpos, ubicar error, clases del 409) | `e3eaf5b` (módulo inexistente) | `b6386b7` |
| Frase del rechazo por sección | `ca17084` (2 en rojo) | `b6d0e80` |
| Las tres pestañas (50 en rojo con la lectura de 3b) | `f8a013c` | Parámetros y motor común `b6d0e80`, Presupuesto `9fd5e02`, Plan `bb15fea` (y `a180817`, tipo del cuerpo para tsc) |

SHAs completos: `git log --oneline c8bbfc3..HEAD -- frontend-desktop`.

## Qué se hizo

- **Motor común** `useEdicionDeSeccion` (estado editable `E` cualquiera): pausa de 400 ms, una petición en vuelo con coalescencia,
  `rev`, `bloqueado` tras un 409 de `rev`/caso/guardado, 422 con `«{detalle}. La hoja sigue con {…}.»` (frase propia de cada sección,
  `FRASES_DE_RECHAZO`), 401, 404 de borrador, vaciado al irse de la pestaña. `accionar` manda sin pausa (E5).
- **Parámetros (E3):** cuatro `TextInput` con etiqueta visible (el rótulo de la clásica), valor como texto; error por campo con
  `aria-invalid`, texto propio del campo y `aria-describedby` al aviso completo; ayuda «Decimales con punto, por ejemplo 2.5».
- **Cantidades (E2):** la columna Cantidad del Presupuesto es un campo por renglón («Cantidad, Presupuesto fila n»); solo viajan
  las filas **tocadas** (se acumulan hasta recargar), en el orden de la tabla; la escrita a mano dice «(calculada: x)» y tiene
  «Volver a la calculada»; fila inválida por el `n` de «presupuesto, fila n (…)»; ↑/↓/Enter/Esc.
- **Plan (E4, E5):** matriz de fracciones editable («Día 1, Plan de trabajo fila n»), matriz completa en cada envío, curva releída;
  partida inválida marcada en todas sus celdas con «Ir a la partida X»; «Crear plan secuencial (una partida por periodo)» solo
  sin plan, deshabilitado mientras vuela, y su aviso (p. ej. «ya tiene plan») sobrevive a la aparición de la matriz.
- Las tres pestañas ya no se vuelven a montar con cada `rev` (`key={borrador.id}`), como la del espacio; cada una relee su vista.
- Ningún `Number`/`parseFloat`/`toFixed`/`+` unario (prueba estática ampliada a los archivos nuevos). Los índices se leen con
  `enteroDeDigitos` (ahora exportado de `logica.ts`).

## Decisiones

- **409 distinguidos:** `rev` viejo -> «Recargar el borrador»; caso cambiado / ya guardado -> «Abrir de nuevo»; **cualquier otro 409**
  (p. ej. E5 «ya tiene plan») es un aviso que **no bloquea** y fuerza una relectura (la persona ve lo que hay). En E1 (3c-1) un 409
  desconocido sigue cayendo en «Abrir de nuevo»; no se tocó.
- **Se ignora la vista de la respuesta** (`presupuesto`/`parametros`/`plan`): se vuelve a pedir la vista, como en 3c-1 (una lectura
  más por edición; optimización posible y sencilla).
- Coma decimal: se manda tal cual; decide el servidor (D-8).

## Ajustes a pruebas (declarados)

Antes de implementar (sin verde de por medio):
- Se reescribieron **4 pruebas de lectura de 3b** porque la pestaña pasa de lectura a edición por diseño: `Vistas.test.tsx`
  («5 (calculada: 3)» -> campo con 5 y «(calculada: 3)»; celdas de la matriz del plan -> valores de los campos) y `Vistas3b3.test.tsx`
  (ayuda «solo se leen» -> «Cambiarlos recalcula»; `dl` de parámetros -> cuatro campos). Fallan sin la implementación.
- `ca17084`: mi prueba común esperaba la frase del borrador para las tres pestañas; contrato y clásica dicen una por sección.

Tras correr contra la implementación (errores míos de prueba, valores esperados intactos):
- `8cbc1a1`: el servidor simulado no contestaba `/vistas/auditoria`; y P13 tomaba el conteo de lecturas después de la pausa.
- `3e9c77b`: `findBy*` se cuelga con el reloj simulado (se usa `getBy`) y el total aparece dos veces con el mismo `title`.
- Las 99 pruebas de `Edicion3c2` + `Vistas` pasaron en la primera corrida de las tres pestañas completas.

## Diferencias entre el contrato real y lo simulado

Ninguna que rompa la simulación: las claves de renglón, los 422/409 y los textos son los del contrato (los literales de los mocks
son los de `…3c2-contrato-rutas.md`). El 422 de forma («Las cantidades no tienen la forma esperada…»), el de clave desconocida o
repetida y el 409 «no tiene plan» no los provoca la interfaz; si llegan se muestran con su `detalle` (los 422 con la frase).

## Límites y deudas

- `PestanaEspacio` conserva su propio bloque de aviso: es el mismo que `AvisoDeEdicion` y `useEdicionDelEspacio` es el mismo motor que
  `useEdicionDeSeccion` para las cinco tablas. Unificarlos cambia código ya aprobado en 3c-1; queda como deuda de DRY (3c-3 o T11).
- «Ir a la partida X» no cambia de página si el plan tiene más de 100 partidas (la paginación de `TablaPaginada` es interna).
- Sin medición de 1366x768 en navegador (T11): la matriz y el Presupuesto van en una región desplazable con foco.
- Los campos de los parámetros miden la mitad del ancho (dos columnas); a 1056 px por verificar en T11.
- La Hoja sigue sin activarse en el menú (`rutas.ts` no se tocó). No se guarda nada (3d).
