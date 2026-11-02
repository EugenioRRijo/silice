# Hoja 3c-1, frente: avance (tablas editables del espacio)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `647c67e` · Solo `frontend-desktop/src/paginas/hoja/` más
`src/api/cliente.ts` (ver «Archivo fuera de la carpeta»). El contrato es `2026-10-19-hoja-3c1-contrato-rutas.md`.

## Parejas prueba -> implementación

| Pareja | Prueba (rojo visto) | Implementación |
|---|---|---|
| Cliente: `PUT` con el token CSRF | `099eba0` (falló: el token no iba) | `cb286fe` |
| Lógica de E1 (ruta, filas editables, cuerpo, frase de rechazo, ubicar el error, topes) | `94233c0` (9 de 9 en rojo) | `75479e0` |
| Tablas editables: 3c-F1 a F4, F6, F7, F10, F13, `rev`/409, 401/404, descartar cambios | `8ab61ad` (28 de 28 en rojo) | `e501b8c` |

## Decisiones

- **Pausa de 400 ms** tras la última tecla; una sola petición en vuelo; lo escrito mientras vuela sale en una sola más con el
  `rev` que contestó el servidor. Al irse de la pestaña con una edición en la pausa se manda en seguida.
- **Se manda la tabla completa** (las cinco, todas las columnas como texto). La respuesta no pisa lo que se escribe; la
  pestaña vuelve a leer su vista (R5) para el Estado, las derivadas y el total, y la barra de estado recibe el `resumen`.
- **Error 422:** `«{detalle}. La hoja sigue con el último borrador válido.»` en un `role="alert"`; la celda nombrada queda con
  `aria-invalid`, el texto «Valor no válido» (Carbon) y como descripción accesible el aviso completo. El foco **no** se
  mueve solo (robaría el foco mientras se escribe): hay un botón «Ir a la fila n de {tabla}» (3c-F4).
- **409 por `rev`:** aviso con el `detalle` y «Recargar el borrador»; hasta recargar no se manda más. Recargar pide R3 y R5 y
  vuelve a sembrar las celdas.
- **404 de borrador / 401:** igual que en 3b (aviso con «Abrir de nuevo» / `alExpirar`).
- **Coma decimal (D-8):** se manda tal cual y decide el servidor con el mensaje de la clásica; la ayuda dice «Decimales con
  punto, por ejemplo 2.5».
- **Tablas largas:** más de 100 filas se paginan de 50 en 50; «Agregar fila» se cierra en el tope de D-9.
- **Columna fija:** `scroll-padding-inline-start` mayor que su ancho para que el foco no quede detrás (WCAG 2.4.11); solo
  verificado por una prueba estática del fuente. La medición real queda para T11.
- **Descartar cambios** (DELETE y reabrir) con confirmación en línea; `beforeunload` solo con cambios.
- La pestaña del espacio ya no se vuelve a montar con cada `rev` (perdería lo escrito); las demás sí.

## Archivo fuera de la carpeta

`frontend-desktop/src/api/cliente.ts` solo aceptaba GET, POST y DELETE: E1 es PUT. Se agregó `PUT` (método y token CSRF), con su
prueba en `cliente.test.ts`. Es un archivo compartido de la interfaz: el orquestador debe saberlo.

## Correcciones de pruebas (declaradas)

- Se quitó de `Edicion.test.tsx` la aserción `inputmode="decimal"` (el contrato no marca columnas numéricas; se puso a todas
  o a ninguna). Antes de ver verde.
- Con `setTimeout` simulado `findBy*`/`waitFor` se cuelgan: las esperas usan un ayudante propio. No cambia ningún valor esperado.
- Carbon pone un `role="alert"` vacío en cada campo (contador): los avisos se buscan por texto.
- La descripción accesible de la celda inválida es `aria-describedby` (Carbon ocupa `aria-errormessage` con su «Valor no válido»);
  el botón «Recargar el borrador» está junto al aviso, no dentro; los textos de cambios se buscan por expresión regular.
  Estos tres se cambiaron tras ver rojo por la forma de Carbon, no por el comportamiento.
- `Vistas.test.tsx` (columna «Acciones») y `Vistas3b3.test.tsx` (el conteo de botones cuenta solo «Ver en Auditoría»): la tabla
  del espacio ahora tiene botones «Quitar».
- `estilosEdicion.test.ts` es estática y nació verde.

## Diferencias entre el contrato real y lo simulado

Ninguna que rompa la simulación. La respuesta real trae además `espacio` (la vista R5 ya recalculada, canónica); el front no
la usa y vuelve a pedir R5 (una lectura más por edición; optimización posible). El 422 «de forma» trae un texto fijo largo que
se muestra con la frase de rechazo.

## Límites y deudas

- Sin medición de 1366x768 en navegador (T11). Sin retomar borradores ni cambio de versión con confirmación (3c-3).
- Si se sale de la página (no de la pestaña) con una edición en la pausa, la página descarta el borrador si el conteo viejo era
  cero y la edición se pierde. Borde estrecho (<400 ms), declarado.
- La Hoja sigue sin activarse en el menú (`rutas.ts` no se tocó).

## Cierre tras la aprobación del árbitro (ronda 1)

- **409 distinguidos** (MENOR 2): solo el de `rev` viejo («El borrador cambió…») ofrece «Recargar el borrador»; «El caso cambió…» y
  «Este borrador ya se guardó…» ofrecen «Abrir de nuevo» (recargar también fallaría). Prueba en rojo `9895d75` y luego la
  implementación. Se distingue por el comienzo del `detalle`: el contrato no trae un código aparte; si el servidor cambia esos textos,
  el 409 desconocido cae en «Abrir de nuevo».
- **Deuda para 3c-3** (MENOR 3): si la persona sale de la página dentro de los 400 ms de una edición, el PUT del vaciado compite con el
  DELETE del descarte al desmontar y, si gana el DELETE, la edición se pierde. Solución: retomar borradores o esperar el vaciado antes
  del DELETE.
- **Verificar en T11** (MENOR 6): `.silice-hoja__sin-evaluar { opacity: 0.6 }` rebaja el contraste del ícono de «Sin evaluar»; el texto
  acompaña, pero hay que medir el contraste del ícono.
- MENOR 5 anotado: los cambios de pruebas ajenas no deben ir en el commit de implementación.
