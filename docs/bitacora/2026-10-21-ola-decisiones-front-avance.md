# Ola de decisiones, frente (2026-10-21)

Rama `inc/ruta-s2-mig-adm-empresa`, base `f2cd316d`. Solo `frontend-desktop/` y esta bitácora. Todo ficticio (OF-001 de las fixtures).

## Commits

| Tarea | Commit |
|---|---|
| H-5 foco de vuelta al botón de descarga | `47c47e8c` |
| H-4 pie fijo y cuerpo desplazable en los diálogos de la Hoja | `0d405510` |
| H-3 cero `role="alert"` vacíos (todo campo pasa por `CampoTexto` / `AreaTexto`) | `5c2b8522` |
| V-16 libro menor en verde, con la palabra visible y contraste AA | `0cf6e462` |
| `CampoTexto` / `AreaTexto` quitan las regiones solo al montar (menos trabajo con 900 campos) | `8abe5201` |
| Tamaño de letra por presbicia (base de 16 px, control, menú en capa, gráficos) | `c734f44d` |

## Qué se hizo

- **V-16.** Para `sentido: "exactitud"` (libro contra Sílice) el delta negativo (libro menor) es favorable y sale verde; el positivo sigue rojo.
  La palabra «favorable» / «desfavorable» ya no es solo para lectores: se ve, y la flecha dice el sentido. Contraste: `--silice-verificado` (green-50)
  da 3,35:1 sobre blanco y 3,05:1 sobre gray-10, suficiente para el ícono (WCAG 1.4.11) pero no para el texto de 12 px (4,5:1); la cifra usa el token nuevo
  `--silice-ibcs-favorable-texto` = green-60 (5,02:1 y 4,56:1). Sin hexadecimales a mano; la prueba `contrasteIbcs.test.ts` calcula las razones.
  La docstring de `api/rutas/libros.py` todavía dice «cualquier desviación es desfavorable»: es del otro frente.
- **H-3.** Los 27 archivos que usaban `TextInput` / `TextArea` de Carbon directamente pasan por `CampoTexto` / `AreaTexto` (movida a `src/comun/`).
  Una prueba estática impide volver a usar los de Carbon fuera de esos dos archivos. Medido en el navegador: 0 alertas vacías en las nueve pestañas de la Hoja.
- **H-4.** `.silice-hoja__dialogo` mide como máximo `100dvh - 2rem`, desplaza por dentro, y su último hijo `.silice-hoja__acciones` es `sticky` abajo con fondo
  opaco y divisor. Aplica a los tres diálogos (guardar, operación, versión). `Cuentas` usa una confirmación en línea, no un diálogo superpuesto, y no cambia.
- **H-5.** `DescargaArchivo` guarda una ref al botón y, al terminar (bien o mal), le devuelve el foco si quedó en el cuerpo; no se lo quita a otro control.
- **Presbicia.** `html { font-size: calc(116,6667 % * var(--silice-escala-letra)) }`: el cuerpo de Carbon (14 px) sale a 16,3 px y la etiqueta de 12 px a 14 px.
  Control «Tamaño de letra» (Normal 100 % / Grande 125 % / Muy grande 150 %, tres botones con una A cada vez mayor, `aria-pressed`, Tab y Enter/Espacio) en la
  cabecera, también antes de entrar. Se guarda en `localStorage` (única excepción a RT-9, una preferencia de pantalla; todo en try/catch, sin él funciona en Normal)
  y `main.tsx` la aplica antes de pintar; mostrar el control no escribe nada. Todo el CSS propio ya iba en rem (cero `font-size` en px); la prueba
  `estilosLetra.test.ts` impide los nuevos. Cambios de rejilla para que la escala no rompa nada: el menú lateral mide `min(16rem, 25vw)`; con Grande y Muy grande
  pasa a ser capa (botón de la cabecera) por debajo de 1536 y 1920 px, como al acercar con el zoom del navegador (Carbon decide con una consulta en rem que no
  sigue a la letra de la raíz); la cabecera cede el nombre de la persona; los selectores se acotan a `min(13rem, 18vw)`; el panel del visor pasa de 320 px a
  `min(20rem, 40vw)`; el texto de los gráficos de Carbon Charts (12 px fijo) pasa a 0,75 rem. `prefers-reduced-motion` y el zoom del navegador no se tocan
  (la raíz está en porcentaje y el control no anima).

## Pruebas

- Rojo visto antes de cada implementación: `regionesVivasVacias` (2 fallas), `estilosDialogos` (3), `DescargaArchivo` H-5 (2), `ibcs` / `IndicadorFiori` V-16 (2),
  `contrasteIbcs` (2), `estilosLetra` raíz (1) y las de `preferenciaDeLetra` / `TamanoLetra` (no resolvían el módulo).
- `npx vitest run src`: 122 archivos, 1819 pruebas; la última corrida completa dio 1818 verdes y 1 roja, `App.test.tsx > una dirección con #/libros abre esa
  página`, que agota los 5 s con la máquina cargada y pasa aislada (3,3 s). En corridas anteriores también se agotaron `Edicion.test.tsx > topes` (21 s contra el
  límite de 20 s; aislada 9 a 10 s) y `PlanoEnHoja`; todas pasan aisladas.
- `npm run lint` limpio, `npm run build` limpio, `npm run dist`: 161 archivos, 14 036 817 bytes, sin URLs externas.

## Auditoría visual (Chromium 151 por DevTools con Node 22; API en 127.0.0.1:8000 con `SILICE_DATOS` temporal y OF-001; sin tocar `data/`)

Anchos 1366 y 1056, alto 768, tamaños Normal, Grande y Muy grande (la ronda final, Normal y Muy grande), cuenta `ana`, proyecto OF-001.

- Páginas (Inicio, Tablero, Elaborar, Libros, Historial, Reajuste, Control, Existencias) y las nueve pestañas de la Hoja: `scrollWidth == clientWidth` en todas,
  cero elementos fuera del ancho fuera de un desplazador, un solo `h1`, cero alertas vacías, cero solapes en la cabecera, y el texto más pequeño en pantalla
  ≥ 14 px en Normal, 17,5 px en Grande y 21 px en Muy grande. Sin el ajuste de los gráficos el Tablero medía 12, 11,3 y 10 px.
- Hallazgo propio corregido a mitad de la auditoría: a 1056 con Muy grande la cabecera se pasaba 7 px (el botón «Salir»); se resolvió con los selectores
  acotados y el nombre oculto en ese rango.
- Menú: Normal fijo (299 px a 1366, 264 a 1056, contenido de 1052 y 777 px); Grande y Muy grande en capa (373 y 448 px), con 21 enlaces, sin desborde.
- Diálogo «Registrar una cotización»: Normal 731 de 768 px, Grande 721, Muy grande 712; Cancelar y Cotizar dentro de la ventana en los seis casos; Esc lo cierra y
  devuelve el foco a «Registrar una cotización…».
- H-5: tras «Descargar Excel» el foco queda en el botón (los seis casos).
- Foco: 25 Tab seguidos sin salir de la ventana. Los únicos elementos sin `outline` son el botón del menú y el nombre «Sílice» de la cabecera: Carbon los marca con
  un borde de 1 a 3 px en el color de foco (no es una falla, pero no tienen el anillo de 2 px del resto).

## No verificado, y hallazgos nuevos

- No se probó con lector de pantalla, con Firefox ni con Edge, ni con el zoom del navegador combinado con el 150 % (solo la lógica: la raíz va en porcentaje).
- El lienzo de la hoja de Excel (Univer) dibuja en píxeles: no sigue el control de tamaño de letra; el panel de hallazgos de al lado sí. Se acerca con el zoom
  del navegador. Pendiente de decidir si se quiere escalar el lienzo (cambia el tamaño de celda de la réplica, que ahora es el del libro).
- Con Grande y Muy grande el nombre de la persona no se ve en la cabecera (no cabe); sigue en la sesión. Si Eugenio lo quiere visible, hay que moverlo al menú.
- El umbral de capa del menú (1536 y 1920 px) es un criterio mío calculado para que quede al menos ~50 rem de contenido; es fácil de cambiar en `shell.scss`.
- `git diff f2cd316d..HEAD -- ui core asistente` NO está vacío: trae `core/budget/cadena.py` y `core/budget/canonico.py`, de los commits de VB-1 del frente de backend
  (`08094cfa`, `8e0b8d4b`), no de este frente.
