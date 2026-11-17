# Arbitraje: depuración unida (Claude xhigh, 2026-11-17)

**Rama:** `feature/depuracion-unida` (las 13 ramas `feature/depurar-*` sobre `feature/mejoras-ola2`).
**Diff juzgado:** `feature/mejoras-ola2..feature/depuracion-unida`, 118 archivos, unas 3.700 líneas; `core/` intacto.
**Segunda opinión:** Antigravity, modelo Hydrogen (`agy -p … --model gemini-4-hydrogen-high --sandbox`), una sola área
por el tamaño. **Verificación:** un subagente independiente comprobó cada hallazgo contra el árbol, con `git log -L`
para separar lo que trae el diff de lo que ya estaba y con sondeos (guiones en el scratchpad, casos ficticios).
**Árbitro final:** Claude xhigh, único. Argon no se usó: el único MAYOR se reprodujo con un sondeo, así que un
arbitraje corto no habría cambiado el veredicto.

Antes del arbitraje la unión estaba en verde: pytest `-W error` 12.968 sin omitidas, vitest 4.524, ruff, metas de datos
4/4 y guardia del núcleo (`--base origin/main`).

## Veredicto: APROBADA CON UNA CORRECCIÓN (hecha)

| H | Hydrogen | Verificación | Árbitro | Destino |
|---|---|---|---|---|
| H1 | MAYOR: `_fmt` del PDF de la empresa redondea al par y deja «-0» | PARCIAL, ya estaba; solo pasa con más de 4 decimales, en el texto de L10/L11 | MENOR | Plan de desenredo: barrido del redondeo (con `libros.py:601/614` e `indices.py:351`) |
| H2 | MAYOR: `entregas.py:172` cuantiza al par | REAL, ya estaba; la pantalla usa `totalPresentado` (al alza) | MENOR | Ya en el plan, tarea 2.4 |
| H3 | MAYOR: `_cadena_legible` acepta eslabones que no son objetos | PARCIAL: el mecanismo citado es falso, el defecto es otro y es real. `["x"]`, `[5]`, `[None]` dan **500** en `POST /v1/revision/paquete` (`declaracion_retroactiva` hace `.get` sobre un texto) | **MAYOR** | **Corregido en esta rama** (abajo) |
| H4 | MAYOR: `_rendimientos_por_declarar` duplica la regla de `aplicacion/elaboracion.py` | REAL, ya estaba | MENOR | Ya en el plan, tarea 2.5 |
| H5 | MAYOR: `select()` en `presupuestos.py` | REAL, ya estaba | MENOR | Ya en el plan, tareas 1.2, 3.1 y 2.5 |
| H6 | MAYOR: `select()` en `entregas.py` y admin; `_proyecto` duplicado | REAL, ya estaba | MENOR | Ya en el plan, tareas 1.2, 3.2 y 2.5 |
| H7 | MENOR: `_pct` de `libro_a_la_hoja.py` sin punto de miles | REAL, ya estaba; solo desde 1.000 % | MENOR | Plan de desenredo: barrido de formateadores (usar `texto_de_cifra`) |
| H8 | MENOR: `declarar_rendimiento_propuesto` escribe sin `BEGIN IMMEDIATE` | PARCIAL, ya estaba; también `rendimientos.py:97` | MENOR | Plan de desenredo, con el BEGIN diferido de `control.py` (DS-2) |
| H9 | MENOR: `_carpetas_visibles` en la ruta | REAL (capa), ya estaba | MENOR | Plan de desenredo, ola de rutas |
| H10 | MENOR: `admin_instalacion` mezcla `operacion.*`; `EventosIlegibles` en dos textos | PARCIAL; el texto doble lo trajo el diff | MENOR | Plan de desenredo: un solo texto junto a `EventosIlegibles` |
| H11 | MENOR: `SIN_CACHE` locales redundantes con `RutaSinCache` | REAL e inocuo; no es solo del diff: 18 routers con `RutaSinCache` ponen la cabecera a mano | MENOR | Plan de desenredo: un barrido con guardia de arquitectura, no tres archivos sueltos |
| H12 | MENOR: «Descartar cambios» dentro de la pausa de 400 ms manda un PUT al borrador borrado | PARCIAL: pide dos clics y el DELETE dentro de 400 ms; el 404 cae en `refrescar`, que no hace nada | — | **Rechazado** |
| H13 | MENOR: el `reenviar` diferido no queda registrado en `registrarEnvio` | REAL (mecanismo), ya estaba; ventana de más de 1 s a mano | MENOR | Plan de desenredo (front de la Hoja) |
| H14 | MENOR: sin guarda de desmontaje ante 401; doble POST de «Descartar» | FALSO como defecto: el doble POST no ocurre y `alExpirar` tras desmontar es lo correcto | — | **Rechazado** |

## La corrección (H3)

- Rojo `test(revision): una cadena con eslabones que no son objetos es alterado sin cadena y no un 500`. Son cuatro casos
  nuevos en `test_una_cadena_sin_la_forma_minima_no_se_registra_ni_rompe_el_analisis`; salían `rechazado`. Hay además
  `test_una_cadena_con_eslabones_que_no_son_objetos_es_alterado_y_no_un_500` por la API, que daba
  `assert 500 == 200`.
- Verde: `_cadena_legible` exige que cada eslabón sea un objeto. Así el paquete queda «alterado» sin cadena que leer,
  igual que un código que no es texto. `_sin_datos_minimos` deja la cadena en `None`, para que la ruta nunca lea la
  cadena de un rechazado.
- Queda como está: un eslabón `{}` sigue saliendo «rechazado» (datos mínimos). El docstring lo declara así a propósito,
  y unificar el criterio cambiaría el contrato de la recepción, lo que no le corresponde a esta unión.

## Otras correcciones de la unión

- **DS-2.** `test(hoja): las nueve vistas que releen vivo llevan el cerrojo, con el conjunto exacto`. Es el conjunto
  exacto de las funciones públicas que reciben `vivo`. Antes la conducta estaba probada solo en 2 de las 9; se comprobó
  que quitar el decorador de `vista_plan` la pone en rojo.
- **DS-3.** La mitad de L3 que faltaba: E6 rechaza con 422 la edición que solo cambia el desglose del desperdicio.
  Se hizo en `feature/depurar-desperdicio` y se unió aquí.

Las decisiones simuladas (DS-1 a DS-4) están en [../2026-11-17-decisiones-simuladas.md](../2026-11-17-decisiones-simuladas.md).
