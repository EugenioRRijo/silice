# Tanda de detalles · Ronda 3 (breve) · Árbitro de Claude, esfuerzo xhigh (2026-11-06): APROBADO

> Delta `1bd211bc..c8cc4f83`. Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: APROBADO.** Sin BLOQUEANTE ni MAYOR. N2, N3, MENOR 2, MENOR 6 y D17 (en lo pedido) resueltos; N1 PARCIAL;
seis MENOR nuevos. Recomienda corregir A, B, D y E antes de fusionar o llevarlos a F8.

| Hallazgo de la ronda 2 | Estado | Evidencia |
|---|---|---|
| N1 (resúmenes «clave=valor») | PARCIAL | el alta o baja de un **tramo** sale cruda siempre: `vertices` también va unido con «; » (`aplicacion/hoja.py:423-424`) y el trozo sin «=» hace que `presentarCambio.ts:22` devuelva null; en un punto con especificaciones, un dato interno parece un campo; «Id» en vez de «Código» |
| N2 (Guardar versión) | RESUELTO | `["Parámetro","Control de obra: Umbral de SPI para error","Umbral de SPI para error","0,90","0,85"]` |
| N3 (documentos) | RESUELTO | |
| MENOR 2 (Revisar) | RESUELTO | `revisar/logica.tsx:55-59` |
| MENOR 6 (textos) | RESUELTO | |
| D17 | RESUELTO en lo pedido | sondas en la pantalla y en el panel, también con el Esc de D16 |

## Nuevos (MENOR)

- **A.** El presentador común se probó con un resumen que el servidor nunca produce («largo=4.5; ancho=3.2» en un tramo);
  con «; » anidado (vértices, un nombre libre como «Sala; comedor») todo sale crudo. Corrección: partir solo en «; »
  seguido de una columna conocida de la tabla que dice el prefijo de la clave; rotular con la tabla de `ROTULOS_DE_COLUMNA`
  («id» → «Código»), con prueba de contrato; oráculos con un resumen real de tramo y de punto con especificaciones.
- **B.** D17 conserva la descripción o la unidad tecleadas al elegir una partida del catálogo, pero el servidor rechaza
  guardar una partida existente con otra descripción o unidad (`aplicacion/composicion.py:458-470`, en `guardar` y en
  `prever`). Corrección: con una partida del catálogo, poner su descripción y su unidad y decir qué se reemplazó.
- **C.** Teclear el código de otra partida existente («Usar «FIC-03» como código») deja la cabecera de la anterior con las
  tablas de la nueva, sin aviso (anterior a la tanda; el servidor lo rechaza al guardar). Corrección: al cambiar el
  código, vaciar los campos de la cabecera que aún tengan el valor que puso el catálogo.
- **D.** El aviso de D17 no se limpia al teclear en Código (`ComponerPartida.tsx:410`).
- **E.** `comun/presentarCambio.ts:6` importa de `paginas/hoja/logica`: `comun/` depende de una página. Corrección: mover
  `rotuloDeOrigen`, `partirClave` y `rotuloDeFila` a `comun/` y extender el trinquete a `comun → paginas`.
- **F.** `aplicacion/hoja.py:1931` cambió sin prueba que lo fije; ESTADO cuenta 16 mensajes «no existe en este caso» y son
  14; el título de ESTADO dice «D1–D16».

Fuera de alcance: «Esta version esta en solo lectura…» (`aplicacion/hoja.py:2134`, `hoja_guardado.py:77`) y el mensaje de
`motivo_para_no_reemplazar` (`composicion.py:460-469`) siguen sin tildes.

## TDD y sin defecto
Rojos de r2-g, D17 y textos solo con pruebas y antes de su verde, por la razón correcta; las tres aserciones quitadas de
`revisar/logica.test.ts` tienen su cobertura en otras pruebas; `core/` sin cambios; uniones limpias; 140/140 vitest y 8
pytest puntuales en HEAD.
