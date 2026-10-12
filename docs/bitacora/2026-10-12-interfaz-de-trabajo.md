# Interfaz de trabajo de Sílice 1.0.0 (PLAN_SILICE_UI)

**Fecha:** 2026-10-12 · **Rama:** `inc/silice-ui`

## Qué se hizo
Tema visual; tablero del proyecto; línea de estado en la barra; pestaña APU en tres paneles. Sin
cambios en core/, adapters/, api/ ni en la base.

## Sin prueba (RU-1, para la auditoría final)
- `ui/estilo.py`, `ui/tablero.py` (desglose que suma el total, pareto con resto, curvas con y sin
  control, control no disponible), `ui/graficos.py`.
- `ui/paginas/tablero.py` (sin proyecto, sin versión, con control, texto ajeno).
- `ui.caso.publicar_resumen` / `ui.barra.pintar_estado` (resumen del mismo ciclo).
- `ui.hoja.filtrar_partidas`, `ui.hoja.filas_de_cierre` (cascada igual a `calcular_apu`) y la
  pestaña APU (filtro vacío, factor inválido, selector de insumo).
- Rama de control del tablero (`tarjetas_de_control` y curva PV/EV/AC) no ejercitada con una obra
  con valuaciones.

## Rulings
RU-1 a RU-12 del plan. RU-2 (enumeraciones de pruebas existentes) ratificado por Eugenio el
2026-10-12.

## Nota sobre RU-2
Tras PR #63 que trajo "Control de obra", las enumeraciones de pruebas existentes se actualizaron
como datos de la lista, sin debilitar ninguna aserción:
- `test_ui_importable.py`: 15 → 16 páginas
- `test_ui_app.py`: nueva entrada "Tablero del proyecto" en `TITULOS_TRABAJO`
- `test_arquitectura_s5.py`: nueva entrada "tablero" en `PAGINAS_QUE_ABREN_EL_CASO`
- `test_ui_app.py`: `test_son_quince_pantallas...` → `test_son_dieciseis_pantallas...` (==16)

## Desviaciones del plan
- `ui/tablero.py` `tarjetas_de_control` lee las claves `no_disponible` "SPI" (fallback "AC"),
  "CPI" (fallback "AC"), y "EAC" (fallback "CPI", luego "AC"). El plan incluía solo las claves en
  minúsculas que `core/budget/valor_ganado.py` nunca escribe.
- Formateo: `ruff format` no se ejecutó sobre archivos grandes preexistentes tras la Tarea 5;
  la Tarea 5 sí refluyó código no relacionado en `ui/app.py` y `ui/paginas/hoja.py` (solo formato).
- Orden de ejecución: 1, 3, 5, 6, 2, 4, 7 porque las Tareas 2 y 4 esperaban PR #63
  (`ui/control.py`).

## Hallazgo fuera de alcance
`ui/barra.py` interpola el nombre del proyecto sin `texto_seguro` en dos `st.markdown` (§0.4 del
plan); `ui/resultado.py::_pendientes` igual con descripciones.

## Pendiente de revisión humana
Recorrido completo de la interfaz: Tablero del proyecto, línea de estado en la barra superior, y
pestaña APU en tres paneles con el caso de Eugenio.
