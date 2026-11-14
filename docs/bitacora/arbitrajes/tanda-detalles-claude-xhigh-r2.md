# Tanda de detalles D1–D16 · Ronda 2 · Árbitro de Claude, esfuerzo xhigh (2026-11-06): APROBADO

> Arreglos `d79a8581..ffa23277`. Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: APROBADO.** Los dos MAYOR de la ronda 1 están corregidos y probados (rojos corridos y sondas propias, también
en casos que el oráculo no cubría); los arreglos no traen ningún MAYOR. Quedan cinco MENOR con una raíz común: las tres
tablas del registro de cambios (Guardar, Versiones y Revisar) no comparten un presentador.

## Ronda 1

| Hallazgo | Estado | Evidencia |
|---|---|---|
| MAYOR 1 (flecha izquierda sin `click`) | RESUELTO | `comun/carbonEs.tsx:23-37`; rojo `69a9a1b5`: `expected [] to include 'click'`; en HEAD la izquierda registra `click` y `pointerdown` |
| MAYOR 2 (Esc mezclaba la partida) | RESUELTO | `CampoDelCodigo.tsx:65,79-93`, `ComponerEnPanel.tsx:84`; rojo `8ab7e431` (3 fallan); sondas: teclear y Esc, salir y volver, «Borrar» y Esc: FIC-02 completo |
| MENOR 1 (rótulos en Versiones) | RESUELTO | `comun/rotulos.ts:18-110`, `Versiones.test.tsx:307` |
| MENOR 2 (Revisar) | PARCIAL | La columna Clave sigue cruda (`revisar/logica.ts:54`) y Antes/Después usan `cifraSiLoEs` en vez de `valorDeCambio` |
| MENOR 3 («A1.2») | RESUELTO, con regresión N1 | `formatoEsVe.ts:39-43` |
| MENOR 4 (m3) | RESUELTO | los 9 sitios y 4 más pasan por `unidadEscrita`; al servidor llega «m3» |
| MENOR 5 (reparto por pesos) | RESUELTO | `RepartoPorPesos.tsx:44-47` |
| MENOR 6 (textos de D2) | PARCIAL | quedan `aplicacion/hoja.py:1777` y `:1931` sin tilde en «versión»; `tablero/index.tsx:238` dice «caso» y manda a la cabecera |
| MENOR 7 (plural) | RESUELTO | `aplicacion/plural.py` |
| MENOR 8 (D5) | RESUELTO | prop obligatoria y prueba de la cabecera en sus 3 estados |
| MENOR 9 (rótulo de la versión) | RESUELTO | `version_de_linea_base` del servidor; `docs/api.json` al día |
| MENOR 10 (monedas) | RESUELTO | trinquete `arquitectura.test.ts:98` |
| MENOR 11 (Riesgo) | RESUELTO | `ParametrosDelRiesgo.tsx:28,78` |
| MENOR 12 (higiene de TDD) | en parte | rojos solo con pruebas y antes del verde; `85ae1ad0` y `e3f0b1e8` tocan pruebas fuera del rojo (declarado) |
| MENOR 13 (ESTADO.md) | RESUELTO | pero dice que los MENOR 1–11 están corregidos y el 2 y el 6 están parciales |

## Nuevos (MENOR)

- **N1.** Regresión frente a la ronda 1: los resúmenes «clave=valor; …» del alta o baja de una fila de metraje vuelven a
  salir con punto («largo=4.5») en Guardar, Versiones y Revisar, porque `cifraSiLoEs` no entra en el texto compuesto.
  Corrección: un presentador que parta por «; » y «=» y formatee cada valor, compartido por las tres tablas.
- **N2.** La tabla de «Guardar versión» (la de D1) sigue con nombres técnicos («parametro», «administracion»,
  «control, spi_error»); el oráculo `Guardar.test.tsx:218` lo fija. Corrección: los rótulos de `comun/rotulos.ts`.
- **N3.** Documentos desfasados: el CHANGELOG aún dice que los botones ocultos de las pestañas tienen nombre (revertido
  en `240e4d59`) y no cuenta lo de «Proyectar»; el plan no anota que D10 era un falso positivo del detector; el detector
  no existe en el repositorio: llevarlo a F8.

**Fuera de alcance (anterior a la tanda, `cefd61fc`):** en Componer, elegir FIC-02 y después FIC-03 deja el código y las
tablas de FIC-03 con la descripción y la unidad de FIC-02 (`ComponerPartida.tsx:386-390` solo llena si están vacías);
guardar escribiría eso en el catálogo. Propone abrir un D nuevo.

## TDD
Rojos corridos en extractos: `69a9a1b5`, `8ab7e431`, `2ded28ec`, `8f5a6126`, `f42b9c84`: todos por la razón correcta.

## Pendiente de navegador
D13 y D14 sin cambios en esta ronda; nuevo: la fila «Proyectar» de Riesgo (fecha con su ayuda, Trayectorias y el botón
en `.riesgo-acciones`) a 1366 px y con letra grande.

## Sin defecto
`core/` intacto; las 6 uniones limpias (`merge-tree` igual); `tsc -b` en 0; `docs/api.json` igual a `app.openapi()`;
ruff en verde; sin datos reales; ninguna cifra calculada en el cliente; 215 pruebas del front y las de Python puntuales
pasan en HEAD.
