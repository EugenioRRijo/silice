# Prueba corta de `st.data_editor` (spec §11.3, tarea 0.5)

Procedimiento fijado antes de ejecutar. Lo ejecuta Eugenio en el navegador: `AppTest` no puede escribir
en `st.data_editor`, así que ningún agente lo puede hacer. La aplicación es descartable
(`scripts/prueba_data_editor.py`) y su resultado decide DA‑SF‑1 (Streamlit o AG Grid).

## Qué se prueba

- 500 puntos del generador de RNF‑11 (`scripts/generar_hoja_prueba.py`, semilla 0).
- Cálculo sustituto: cada edición recibida llama de nuevo a `core.budget.elaborar` con los ítems del
  borrador (el mismo costo que tendrá la hoja sin la derivación espacial).
- Columna **Estado** en un componente aparte (tabla de la derecha), no dentro del editor.
- Ediciones guardadas en `st.session_state["borrador_prueba"]` (clave que no es de widget).
- Pestaña activa con `st.segmented_control` (Hoja / Resumen).
- Medición: la propia aplicación anota en `scripts/_salida_prueba_editor.log` (ignorado por git) una
  línea por evento: `hora ISO<TAB>marca monotónica<TAB>evento<TAB>detalle`. Eventos: `ARRANQUE`, `RUN`
  (cada ejecución del script), `EDICION_RECIBIDA` (con altas, bajas y celdas cambiadas) y
  `ESTADO_PINTADO` (con `desde_recepcion_s`, el tiempo del servidor hasta pintar el Estado). No se usa
  cronómetro.

## Preparación

1. Desde la raíz del repositorio (o del worktree `sf`):
   `uv run python -m streamlit run scripts/prueba_data_editor.py`
   (con el extra `ui`; si hace falta: `uv run --extra ui python -m streamlit run scripts/prueba_data_editor.py`).
2. Borrar `scripts/_salida_prueba_editor.log` si existe, y abrir la aplicación en el navegador. Debe
   aparecer la línea `ARRANQUE` en el registro.
3. Opcional pero recomendado: grabar la pantalla (Win+Alt+R) para contrastar lo que se ve con el
   registro del servidor.
4. Tener a mano una hoja de papel para anotar cada edición hecha (fila, columna, valor nuevo).

## Pasos (en este orden)

1. **20 ediciones de celda**, de una en una, esperando que el Estado se actualice antes de la
   siguiente: cambiar `cantidad` de 20 filas distintas (p. ej. filas 0 a 19 a un valor reconocible,
   como 111, 112, ...). Anotar cada una.
2. **5 altas de fila**: añadir cinco filas al final (elegir `partida` en la lista y escribir una
   `cantidad`). Anotar cada una.
3. **5 bajas de fila**: seleccionar cinco filas y borrarlas (icono de papelera). Anotar cuáles.
4. **Una ordenación**: ordenar por `cantidad` haciendo clic en el encabezado. Observar si el Estado
   sigue alineado con la fila que le corresponde (la tabla Estado lleva el número de fila) y anotar lo
   que se vea.
5. **10 ediciones rápidas seguidas** mientras el script se reinicia: sin esperar entre una y otra,
   cambiar `cantidad` en 10 celdas distintas (p. ej. filas 100 a 109, valores 901 a 910), pasando de
   celda con Tab/Enter lo más rápido posible. Anotar las diez.
6. Cambiar a la pestaña **Resumen** y volver a **Hoja**: las ediciones hechas deben seguir presentes
   (el borrador vive en `session_state`).
7. Esperar 5 s sin tocar nada y cerrar la medición.

## Criterio (spec §11.3)

**PASA** si se cumplen las dos condiciones:

1. **No se pierde ninguna edición.** Cada edición anotada en papel aparece en el registro como celda
   cambiada, alta o baja de alguna línea `EDICION_RECIBIDA` (las diez rápidas pueden llegar agrupadas
   en pocas líneas, pero ninguna celda debe faltar), y los valores finales visibles en el editor y en
   la pestaña Resumen (conteo de filas = 500 + 5 − 5 = 500) coinciden con lo anotado.
2. **El Estado se actualiza en ≤ 2 s tras cada edición.** Para cada `EDICION_RECIBIDA`, la línea
   `ESTADO_PINTADO` siguiente (mismo `RUN`) cumple `desde_recepcion_s` ≤ 2,0; y en la grabación de
   pantalla el Estado visible cambia dentro de 2 s tras la edición.

Si falla cualquiera: veredicto **FALLA**, la hoja usa AG Grid (DA‑SF‑1; `streamlit-aggrid`) y las
tareas 3.x de PLAN_SF.md lo reflejan.

## Qué anotar en la bitácora (Paso 6 de la tarea 0.5)

- Veredicto PASA o FALLA y la fecha.
- Número de líneas `EDICION_RECIBIDA`, celdas anotadas contra celdas halladas (deben coincidir).
- Máximo y mediana de `desde_recepcion_s` (ver el registro) y `elaborar_s`.
- Lo observado en la ordenación (paso 4) y cualquier edición perdida o reiniciada del editor.
- Versión de Streamlit (`uv run python -c "import streamlit; print(streamlit.__version__)"`) y navegador.

Limitación declarada: las marcas son del servidor; el último tramo (red y pintado del navegador) se
contrasta con la grabación de pantalla, no con el registro.
