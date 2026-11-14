# Tanda de detalles D1–D16 · Ronda 1 · Árbitro de Claude, esfuerzo xhigh (2026-11-06): DEVUELTO

> Rango `6a0e8bcf..feature/tanda-detalles` (HEAD `aa82e86a`). Respuesta literal en lo esencial (sin rutas absolutas
> del equipo); guardada por Claude. El árbitro trabajó en solo lectura, con sondas y rojos en extractos del scratchpad.

**VEREDICTO: DEVUELTO.** 2 MAYOR y 13 MENOR, sin BLOQUEANTE.

## MAYOR

**1. D10 deja sin efecto «Desplazar las pestañas a la izquierda» en todas las `TabList`.** `comun/carbonEs.tsx:41-52`
pasa `ref: ancla` en `leftOverflowButtonProps`; Carbon 1.117 (`Tabs.js:370-377`) pone `ref: previousButton` y después
reparte esas props, así que el `ref` de la tanda pisa el interno y `usePressable(previousButton, …)` no ata `click`.
`bae4d8a4` tapó con `as` el error de `tsc` que avisaba de eso. Sonda: con `carbonEs.TabList` la flecha izquierda no
recibe `click` (`AssertionError: expected [] to include 'click'`). Afecta a la Hoja, el Visor, Control, Mercado,
Existencias, Reajuste, Revisar, Catálogo y Carpetas. Lo ganado es nulo: los botones nombrados son `aria-hidden` y
`cds--visually-hidden` (la app no usa pestañas `dismissable`) y por accname §2A su nombre es vacío; el aviso salió del
detector casero del recorrido. Corrección: revertir el parche de DOM y el `ref`, y que el detector salte lo `aria-hidden`
(como axe); prueba de que la flecha izquierda conserva su `click`.

**2. D16: elegir una partida, corregir un carácter y pulsar Esc sigue dejando la partida mezclada.**
`CampoDelCodigo.tsx:76,82` marca `eligio` solo hasta la siguiente tecla y `ComponerEnPanel.tsx:88-89` devuelve el campo
al valor de antes de buscar. Sondas: `{"codigo":"","descripcion":"Relleno compactado ficticio","unidad":"m3","fila1":"Arena ficticia"}`
y, con código inicial «OBRA-04», `{"codigo":"OBRA-04",…,"fila1":"Arena ficticia","cerro":0}`. El oráculo de
`ComponerEnPanel.test.tsx:259` (`not.toHaveValue("FIC-029")`) acepta ese estado. Corrección (patrón de Fiori: Esc vuelve
al último valor confirmado): al elegir, la línea base del Esc pasa al código elegido; oráculo exacto: tras elegir y
teclear «9», Esc da «FIC-02» con la descripción, la unidad y las tablas de FIC-02, también con código inicial.

## MENOR

1. D4 incompleto: parámetros de control (`control|…`) salen como «Control|spi error», «Penalizacion diaria»; en metraje
   «Ambiente id», «Vertices», «X0»; la instantánea muestra «catalogo» e «instantanea».
2. El mismo defecto de D1 y D4 en Revisar › «Quién cambió qué» (`paginas/revisar/logica.ts:50-68`).
3. D1 y D4 formatean como cifra texto que no lo es («A1.2» → «A1,2»).
4. D6 incompleto: «m3» sigue en `EditorDeApu.tsx:188`, `AgregarPartida.tsx:220`, `LineaDelApu.tsx:75,264,354`,
   `CampoDePartida.tsx:50`, `componer/Similares.tsx:38`, `control/PestanaProcura.tsx:441`, `PestanasDeResultados.tsx:185`.
5. D7: el mismo patrón de 404 por producto en `produccion/RepartoPorPesos.tsx:36-50`.
6. D2: «Elija otro» junto a «obra» (`tablero/index.tsx:238`); `aplicacion/hoja.py:2236` manda a «la barra superior (Nueva
   obra)», que está en la barra lateral; faltan tildes en «créela», «versión», «está» (2236-2260).
7. D3: «(1 partidas)» (`hoja_vista.py:114`, llega a la pantalla) y «con 1 cambios» (`hoja_guardado.py:122`).
8. D5: la conexión de `CabeceraDeObra.tsx:36` no tiene prueba; `"monedaDeLaObra" in props` debería ser prop obligatoria.
9. D11: el rótulo fijo no dice cuál versión se ve; mejor rótulo dinámico («Versión de la línea base» / «Versión vigente»).
10. D15: monedas escritas a mano en `control/PestanaValuaciones.tsx:354-355` y `shell/carpetas/GestionCarpetas.tsx:380-381`.
11. D9: «Fecha de inicio» y «Trayectorias», que solo usa Proyectar, siguen en los parámetros comunes; el grupo
    «Proyectar» solo contiene un botón.
12. Higiene de TDD: `2b335754` («rojo») incluye la implementación del servidor; `23b1ca0c` cambia pruebas que no estaban
    en el rojo; `d3b4a844` reescribe consultas del rojo; las pruebas de D13 y D14 solo copian constantes de CSS.
13. `docs/ESTADO.md` no menciona la tanda.

## TDD
Rojos comprobados en extractos para D1, D3, D4, D7, D8, D12, D15 y D16: todos por la razón correcta.

## Sin defecto
`core/` intacto; los 16 merges limpios; `docs/api.json` igual a `app.openapi()`; la ruta nueva va con `OPERAR_ARENERA` y
está en la tabla de acceso; D1, D3, D8, D12, D14 bien; D15 solo mueve importaciones y su prueba de arquitectura es un
trinquete en las dos direcciones; D2 completo en pantalla y servidor; sin oráculos debilitados; sin datos reales.

## Pendiente de navegador
D13 a 1056, 1366 y 1920 px con las tres letras (Estado entero, «Ver en Revisión» sin desbordar, altura de fila) y D14
con el contenedor bajo 42 rem (rótulo y dato en una línea, barra de avance, ícono de etapa, dato largo).

**Juicio de conjunto:** la tanda corrige bien la mayoría y su TDD es real, pero D10 rompe un control de todas las
pantallas a cambio de nada y D16 no cierra su defecto. Con los dos MAYOR corregidos y probados, y de preferencia los MENOR
1, 2, 4 y 6, queda lista para la pasada de navegador de Eugenio.
