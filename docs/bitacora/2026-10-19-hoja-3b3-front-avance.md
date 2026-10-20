# Hoja 3b-3, frente: avance (Punto de equilibrio, Parámetros, Auditoría, Precios y Trazabilidad)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `146dc59` · Solo `frontend-desktop/src/paginas/hoja/`.
El contrato de rutas es `2026-10-19-hoja-3b3-contrato-rutas.md` (`aa9fbd7`); lo simulado coincide con `api/esquemas_hoja.py`.

## Parejas prueba → implementación

| Pareja | Prueba (rojo visto) | Implementación |
|---|---|---|
| Lógica (rutas, rótulo de origen, filtro de hallazgos, columnas de Precios, fechas) | `logica3b3.test.ts` + datos, commit «logica de las pestanas…» | `logica.ts` («tipos, rutas y ayudas…») |
| Punto de equilibrio y Parámetros (3b-F9) | «pestanas Punto de equilibrio y Parametros… (rojo)» | `PestanaEquilibrio.tsx`, `PestanaParametros.tsx` |
| Auditoría y «Ver en Auditoría» (3b-F6b, 3b-F12) | `4202732` | `f08f1d5` |
| Datos alineados al contrato real (`fecha_precio`, `moneda` de R9, hora ISO, tasa con exacto) | `e4b8eb7` (dos pruebas nuevas en rojo) | en `640a9f0` |
| Precios y búsqueda de atípicos (3b-F10) | `19314c7` | `640a9f0` |
| Trazabilidad (3b-F11) y navegación de las nueve (3b-F3) | `6d1de89` | `032781f` |

## Decisiones

- **Un solo árbol de pestañas.** Ya no hay marcador de lugar: las nueve pestañas montan su vista. Solo la activa pide la suya
  (R9, R10, R11 por borrador; R12, R13, R14 por `proyecto` y `version` de la base abierta).
- **«Ver en Auditoría» (3b-F6b).** Un contexto (`ContextoAuditoria`) ofrece la función a `EstadoDeFila`; el botón sale solo en
  filas con severidad (las `OK` no lo tienen). Filtra los hallazgos de R11 cuyo `origen` contiene la clave de la fila
  (`esp_puntos:P1`; en el Presupuesto, `partida|origen#2`, el origen sin `#n` y el origen suelto). El filtro se quita con
  «Quitar filtro» o al ir a mano a otra pestaña; el foco pasa al aviso del filtro (la fila que lo pidió se desmonta). Si el
  informe no nombra la fila, lo dice sin tabla vacía.
- **Claves en palabras (DESIGN §7.1).** `rotuloDeOrigen`: `esp_puntos:P1` se lee «Punto P1»; en Trazabilidad la clave del
  registro se lee en palabras y la cruda queda en el `title`.
- **Precios.** Tabla con los 9 campos principales + «Detalle» por insumo (botón con `aria-expanded`); los otros 11 campos de
  `COLUMNAS_PRECIOS` están en el detalle (los 21 llegan del servidor y se reparten por rótulo). «Erosión por índice» solo
  aparece si algún valor viene (DV-11). La tasa se muestra con su `exacto` (el contrato lo pide). Una celda sin dato se lee
  «Sin dato» en el detalle. El Estado distinto de «OK» lleva ícono y texto de Advertencia (decisión de la interfaz: el
  servidor manda solo el texto). Es la versión guardada, no el borrador: la pantalla lo dice.
- **Atípicos.** Solo pide al pulsar; avisos del servidor y tabla con el token morado de los atípicos (la severidad dice
  «Advertencia» con su ícono). Error propio sin tumbar la tabla de precios.
- **Cifras:** todo por `Cifra`/`formatoEsVe` sobre el texto; `exacto` en `title` y en texto accesible. La prueba estática
  3b-F5 sigue cubriendo los archivos nuevos (sin `Number`, `parseFloat`, `toFixed` ni `+` unario).
- **Parámetros y Punto de equilibrio** son lectura (la edición y convertir son de 3c y 3d).

## Correcciones de pruebas (declaradas)

- Se quitó y se restituyó el ayudante `pedidas()` del archivo de pruebas nuevo (error propio: dos pruebas daban
  `ReferenceError`); entró en el commit `640a9f0`. No cambió ningún valor esperado.
- Antes de implementar se cambiaron datos de prueba para seguir el contrato real (`fecha_precio`, `moneda` de R9, hora ISO con
  `T`, tasa con texto de 2 decimales y exacto de 4): commit `e4b8eb7`, con dos pruebas nuevas vistas en rojo.

## Límites y deudas

- Sin medición de 1366×768 en navegador: se razona (todas las tablas van en `region` desplazable con foco; la página no se
  desplaza; la columna fija es la de 3b-2). Queda para T11.
- El texto del Estado de Precios (R11 y R12 separados por «; ») se muestra tal cual, sin tildes si el servidor no las trae (D-3).
- La Hoja sigue sin activarse en el menú (`rutas.ts` no se tocó).

## Ronda 2 del árbitro

- Prefijos `esp_*` que emiten los adaptadores y la hoja (barrido `esp_[a-z_]+:` en `adapters/espacio/` y `aplicacion/hoja*.py`):
  `esp_ambientes`, `esp_circuitos`, `esp_fuentes`, `esp_puntos`, `esp_segmentos`; las tablas del espacio añaden `esp_origenes`,
  `esp_recorridos`, `esp_sobrescrituras` y `esp_tramos`. Todos tienen nombre en `rotuloDeOrigen`; uno desconocido cae a
  «Origen X» y una prueba recorre el barrido.
- Una clave sin partida que empieza por un segmento ya no toma su «|» por la partida.
- Diferencia B4 resuelta: un hallazgo PENDIENTE no se atribuye a toda la partida (solo al renglón que lo cita), como la clásica.
