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
- `ui/tablero.py` `tarjetas_de_control` lee las claves `no_disponible` "SPI" (sin respaldo),
  "CPI" (cae a "AC") y "EAC" (cae a "CPI" y luego a "AC"). El plan incluía solo las claves en
  minúsculas que `core/budget/valor_ganado.py` nunca escribe.
- Formateo: `ruff format` no se ejecutó sobre archivos grandes preexistentes tras la Tarea 5;
  la Tarea 5 sí refluyó código no relacionado en `ui/app.py` y `ui/paginas/hoja.py` (solo formato).
- Orden de ejecución: 1, 3, 5, 6, 2, 4, 7 porque las Tareas 2 y 4 esperaban PR #63
  (`ui/control.py`).

## Correcciones de la revision final
1. Subtotales por rubro de la pestana APU: se leen los factores, la lista y la tabla antes de
   pintar el subtotal; el rotulo del bloque ya no lleva monto y el subtotal se escribe en un hueco
   tras aplicar la edicion; `_cierre_de_partida` se parte en `_factores` y el cierre.
2. El tablero sirve al rol que solo lee: sin proyecto abierto en la barra ofrece un selector de
   solo lectura con los proyectos del caso (no abre el proyecto); el aviso ya no remite a la barra.
3. `leer_control` captura `ValueError` y `LookupError` de la curva y devuelve el motivo; la pagina
   tambien captura `LookupError` al leer.
4. La linea de estado de la barra ya no repite el prefijo "Proyecto: <nombre>".
5. `_publicar_resumen` publica `None` si no hay version abierta (un borrador nuevo no se atribuye
   al proyecto de la barra).
6. Cambio de insumo: el aviso "Hay mas de ..." aparece solo si hay mas de 300 (se consulta 301) y
   pide acotar por descripcion.
10. `filas_de_curva`: la variable local `porcentaje` pasa a `porcion` para no ocultar la importada.

## Hallazgo fuera de alcance
`ui/barra.py` interpola el nombre del proyecto sin `texto_seguro` en dos `st.markdown` (§0.4 del
plan); `ui/resultado.py::_pendientes` igual con descripciones.

## Pendiente de revisión humana
Recorrido completo de la interfaz: Tablero del proyecto, línea de estado en la barra superior, y
pestaña APU en tres paneles con el caso de Eugenio.
