# Fases F5, F7 y F8 · Revisión de correcciones · Árbitro único, xhigh (2026-11-07): DEVUELTO

> Rango `c515ab1a..574a1a4a`. Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: DEVUELTO.** 2 MAYOR: P1 sigue abierto por la vía de las celdas reales lejanas, y la CI de ubuntu quedaría en
rojo por cuatro pruebas omitidas. P2, V1, V2, RF-184, la licencia del SDK (falta que Eugenio confirme el texto), P4–P9,
A1, A2, C1 (interino aceptable), C2 e I3 resueltos; P3 parcial; I1 (ESTADO y CHANGELOG) pendiente del orquestador.

## MAYOR
- **P1 (parcial).** Ya no se materializa la `<dimension>` ni se leen hojas ajenas, pero `_filas`
  (`adapters/hoja_empresa/lector_apu_por_hoja.py:111-118`) guarda una fila vacía por cada fila hasta la última celda real y
  una fila con una celda en XFD llega con 16.384 valores; la guardia solo mira `<dimension ref>` (`guardia.py:77`). Sonda:
  una hoja APU con 2.000 filas con celda en XFD, 11.944 bytes, 32.768.001 celdas y 250,7 MiB; por la ruta completa, 3 hojas,
  33.449 bytes: 751,7 MiB y 302,5 s. La prueba contaba solo celdas. Corrección: `iter_rows(max_row=20_001, max_col=101,
  values_only=True)` y `ArchivoRechazado` si hay una celda real más allá; recortar los `None` finales; prueba roja con
  filas y celdas (variantes C y E de la sonda).
- **N1.** `tests/unit/test_ventana.py:444,453` usan `pytest.importorskip("webview.util")`, pero pywebview solo se instala
  en win32 y el paso «Sin pruebas omitidas» de la CI no tiene excepciones: 4 omitidas en ubuntu, salida 1. Corrección:
  esas pruebas en un archivo que solo se recolecte en Windows, con importación dura allí.

## MENOR
- **N3 (resto de P3).** `1e+20` en cantidad o precio da 500 por `InvalidOperation` en `fusion/apu_por_hoja.py:125`.
- **N4.** `docs/manual_instalacion.md:197-198`: la ruta de registros quedó partida por un `\r`.
- **N5.** Ciclo entre paquetes: `fusion/apu_por_hoja.py` importa `aplicacion.cifras` y `operacion.config`, y
  `aplicacion/desperdicio.py` importa `fusion.desperdicio`; ninguna guardia lo vigila.
- **N6.** `test_medir_capas` fija la capa escritorio en 0,0 aunque V0 midió ~0,6 MB.
- **N7.** La bitácora V0 (:203) dice que los textos de la bienvenida y del manual de usuario no se llevaron, y ya se
  llevaron (`b2257b6c`, `574a1a4a`).
- **N8.** Precios de la empresa mezcla «esta carpeta» con «El caso no tiene listas de precios» y «No se pudo leer el caso».

## Sin defecto
`PuenteCerrado` no rompe la carga ni el respaldo; el traslado a `comun/ayuda` mantiene honesto el trinquete; rechazar el
libro entero ante un valor inválido es coherente; AH10 correcto; la maquetación de pend-front, limitada a su pantalla; el
aviso de solo lectura con tildes llega siempre por `hoja_guardado.py`. Rojos muestreados (`b5587938`, `43e0bf40`,
`7531745b`, `def3db46`) por la razón correcta. `core/` intacto, experimento congelado vigente, `docs/api.json` al día,
metas 4/4, ruff limpio; 738 pytest y 817 vitest puntuales en verde.
