# Autocompletado guiado · Ronda 4 · Árbitro de Claude, esfuerzo xhigh (2026-11-06): APROBADO

> Arreglos `78615015..c3b0b9fe`. Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: APROBADO.** Sin BLOQUEANTE ni MAYOR; 4 MENOR nuevos (uno de código, que trajo esta ronda, y tres de
documentos) y 1 MENOR anterior. Recomienda corregir en este PR la pérdida de foco (MENOR 1) y la frase de DESIGN.md
(MENOR 2) antes de fusionar.

## Ronda 3

| Hallazgo | Estado | Evidencia |
|---|---|---|
| MAYOR 1: Esc volvía «tecleado» el precio del catálogo | RESUELTO | Reproducido en HEAD: `R3-N2 TRAS ELEGIR BLANCO: {"descripcion":"Cemento blanco ficticio","unidad":"","precio":"","ayudaPrecio":null,…}` y `R3-N2b TRAS ELEGIR ROJO: {…,"precio":"9,00","ayudaPrecio":null}` (en la ronda 3 daba «25,50»). Con valores de fuera (precarga, MaPreX): «Se cambió el precio 5,00 por el del catálogo, 9,00 Bs.» y «Se quitó el precio 5,00…» |
| MENOR 2: `tecleadas` sobrevivía a la precarga | RESUELTO (ver nuevo 1) | `R3-N1 TRAS ELEGIR CEMENTO GRIS: {…,"unidad":"saco","precio":"25,50","ayudaPrecio":"Se cambió el precio 5,00 por el del catálogo, 25,50 Bs.",…}` |
| MENOR 3: el fallo del aviso de lista no se reintentaba | RESUELTO | `TablaInsumos.tsx:112-118, 277-292`; la consulta va por código (`q=<código>`, rango 0 en `aplicacion/busqueda.py:70-71`) |
| MENOR 4: tope del Simulador en la pantalla | RESUELTO | mismos topes que la API |
| MENOR 5: números del ERS | RESUELTO | RF-167, RF-168 y RNF-29 |
| MENOR 6: aviso de fecha en DESIGN.md | RESUELTO | (con la inexactitud del nuevo 2) |
| MENOR 7: aviso de Control en región viva | RESUELTO | contenedor siempre montado, con prueba |
| MENOR 8 | RESUELTO en lo corregible | los asuntos con tilde de rondas viejas se quedan: reescribir la historia no es proporcional |

## Hallazgos nuevos

**[MENOR] 1.** `ComponerPartida.tsx:492` (`key={vueltaDePrecarga}`): si llega una precarga con el foco dentro de una tabla,
el foco cae en `<body>` (WCAG 2.4.3; en el panel modal). `FOCO DESPUES: BODY mismo nodo: false` en HEAD frente a
`INPUT materiales-0-precio mismo nodo: true` en 41d022eb. Corrección: no remontar; reiniciar el estado de origen durante
el render, con el patrón de `sinSaber`; prueba de foco.

**[MENOR] 2.** `DESIGN.md:250` dice que lo del catálogo también «se dice» al reemplazarse; el código lo reemplaza sin
aviso (`autocompletado.ts:101`).

**[MENOR] 3.** `ERS.md:1660-1661` dice que la matriz §4 suma las tres filas, pero no las tiene.

**[MENOR] 4.** `comun/normalizar.ts:5-6`: el comentario sobre la copia de `plano` en `logicaBusqueda.ts` quedó falso.

**[MENOR, anterior] 5.** `comun/logicaBusqueda.ts:118-135`: con caracteres fuera del plano básico (emoji) el resaltado se
corre un carácter (`indexOf` en UTF-16 frente a `origen` por punto de código). Cosmético; ya pasaba en 41d022eb.

**Sin defecto:** origen por valor y `deFuera`; `sinSaber` sin bucles; el tope del Simulador nunca deja pasar lo que la API
rechazaría (con emoji rechaza de más, aceptable); el resaltado aguanta «½», ancho completo, «é» descompuesta, «İ» y hangul.

## Pregunta del orquestador: vaciar sin aviso un precio que puso el catálogo

**Aceptable.** El diseño obliga a no mezclar fuentes, y vaciar es la dirección segura. La persona eligió una opción que
mostraba «sin precio en la lista para armar», y esa línea forma parte del nombre accesible de la opción. No hay cambio de
contexto (WCAG 3.2.2) y 4.1.3 solo exige exponer lo que se presenta. Con la precarga o MaPreX sí se avisa, porque la
persona no vio de dónde venía. Mejora opcional: que la celda vacía tras elegir un insumo sin precio diga siempre «Este
insumo no tiene precio en la lista para armar: escríbalo.».

## TDD y `core/`
Rojo comprobado sobre 41d022eb: 11 fallos por las razones esperadas (dos pruebas de guarda pasan, como corresponde);
rojos antes que verdes; verde en HEAD 116/116; `core/` intacto y guardia con salida 0.

**Juicio de conjunto:** lista para que Eugenio la pruebe en el navegador y la fusione, con el foco de la precarga y la
frase de DESIGN.md corregidos en el mismo PR.
