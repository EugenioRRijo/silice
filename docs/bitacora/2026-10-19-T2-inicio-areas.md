# T2: Inicio «panel del día», menú por cinco áreas y recorrido «Auditar un libro de la empresa» (2026-10-19)

Fuentes: spec `2026-10-18-silice-ui-inicio-panel-del-dia-design.md` (§2.1 a §2.5) y `MANUAL_INICIO_AREAS_Y_AUDITORIA_VISUAL.md`
(§2.1 y §2.3). Árbol `.worktrees/s2madm`. Solo front (`frontend-desktop/src/shell/`, `src/paginas/inicio/`); `core/` y la API no se tocan.

## Qué quedó

- `rutas.ts`: `AREAS` (cinco, con descripción y los ids de sus pantallas en orden), `areasVisibles`, `HERRAMIENTAS_PRINCIPALES` y
  `herramientasVisibles`. `PAGINAS`, `seccion`, `accion`, `visible` y las rutas URL quedan igual: 21 páginas, 18 en modo entrega.
- `MenuLateral.tsx`: un solo `SideNav` con, de arriba abajo, «Herramientas principales», el «Recorrido en curso» (si lo hay) y las
  áreas. «Más» es un grupo plegable (botón con `aria-expanded`).
- `recorrido.ts` y `PanelRecorrido.tsx`: el recorrido de tres pasos y su panel. El Inicio lo pone en curso con «Auditar con
  recorrido guiado» y lo muestra en «Últimas auditorías guardadas» con un enlace al paso 2.

## Rulings

1. **Un solo menú lateral, sin barra superior de áreas.** El spec habla de barra superior porque nació para Streamlit
   (`st.navigation`); el manual (§2.1) ya fijó el SideNav de Carbon como equivalente. Costo si es erróneo: bajo (las áreas son datos).
2. **El área vive en una lista aparte (`AREAS`), no en un campo `area` de cada `PaginaDef`.** Un solo lugar decide pertenencia y
   orden (el orden del spec, p. ej. Auditar = libros, revisar, historial, no coincide con el de `PAGINAS`) y no obliga a tocar las
   21 entradas ni los datos de prueba de otros. Una página que no esté en ninguna área cae al final de «Más» (nunca se pierde); un
   id de `AREAS` que aún no está en el registro se ignora (hoy `historial`, que construye T3).
3. **`seccion` se queda.** Sigue mandando en el modo entrega («Investigación» desaparece). Cambiarla era riesgo sin ganancia.
4. **`visor` no está en «Más».** El spec lo lista, pero el Visor 3D se retiró el 2026-10-19; no existe en `PAGINAS`.
5. **Sin línea de ayuda por cada pantalla en la lista de áreas.** El spec pide una línea por pantalla; con 21 pantallas a 32 px cada
   una duplicaría la altura del menú a 1366×768. Se mantiene la descripción de cada área (siempre visible) y la línea de ayuda de las
   tres herramientas principales. Diferencia deliberada; reversible añadiendo `ayuda` a `PaginaDef`.
6. **«Más herramientas, plegado»:** se pliega el grupo «Más» (que contiene todo lo que no es de las otras cuatro áreas); se abre
   solo al estar en una de sus páginas. Las otras áreas van abiertas: son el uso diario.
7. **Herramientas principales:** solo se pintan las que la cuenta puede usar y que ya están migradas. Una herramienta cuya pantalla
   sigue en la interfaz clásica aparece en su área, con el rótulo «En la interfaz clásica».
8. **Recorrido sin motor propio de estado.** No existía un motor en React. En vez de uno, el paso actual se deduce de la pantalla
   abierta (`pasoDeRuta`) y solo se recuerda, en memoria (nunca `localStorage`), cuál recorrido está en curso. «Terminar recorrido»
   lo cierra. Costo: salir de las tres pantallas no pierde el recorrido pero tampoco marca avance; es lo mínimo coherente con la
   regla «un paso por pantalla».
9. **Paso 3 del recorrido (Historial).** La pantalla la construye T3. Mientras no esté en el registro, el paso se ve como texto sin
   enlace; cuando exista, se enlaza solo (sin cambios aquí). Falta además añadir `historial` a las pruebas de conteo de
   `rutas.test.ts` cuando T3 lo registre (22 páginas, 19 en modo entrega); el orquestador lo recalcula.
10. **El recorrido arranca solo con «Auditar con recorrido guiado».** «Auditar por mi cuenta» no lo activa.

## No hecho

- El enlace «Probar con un ejemplo» (§2.1): exige un libro `.xlsx` construido y ficticio, un binario que no se genera sin
  dependencias nuevas. Queda para quien arme los datos de ejemplo.
- Barra de «Proyecto» y «Caso abierto» dentro del panel izquierdo (§2.3): ya están en la cabecera (selectores) y en el Inicio; no se
  duplican.
