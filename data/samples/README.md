# Muestras de datos por dominio

Cada subcarpeta tiene su propio `README.md` con las columnas, la procedencia de cada dato y los
supuestos declarados. Este índice solo dice qué hay y qué adaptador lo consume.

| Ruta | Dominio | Adaptador | Contenido | Sesión |
|---|---|---|---|---|
| `civil/tanquillas_y_zanja.csv` | civil | `adapters/civil/tabular.py` (`AdaptadorCivilTabular`) | dos filas (4 tanquillas de 0,80 × 0,80 × 0,80 m, pared 0,10 m; zanja de 24 m × 0,40 × 0,80 con PVC 4") que reproducen la geometría de la línea base; emite 6 `ItemComputo` con regla y parámetros, incluido el relleno con su balance `{LB-01-EXC} - {LB-04-CON} - {LB-02-TUB} * f` | I3.2, 4b |
| `telecom/topologia_arenaza.csv` | telecom | `adapters/telecom/adaptador.py` (`AdaptadorTelecom`) | 8 nodos (rack, 2 switches, 4 puntos de acceso, UPS) y 5 enlaces UTP con longitud y reserva, derivados de los dos presupuestos ARENAZA | I5 |
| `telecom/Presupuesto_1_ARENAZA.pdf` | telecom / sistemas | — (evidencia) | presupuesto de puntos WiFi, ejercicio académico ficticio (14 renglones, 1 109,29 USD) | I5 |
| `telecom/Presupuesto_2_ARENAZA.pdf` | telecom / sistemas | — (evidencia) | presupuesto de red y CCTV con rack, ejercicio académico ficticio (26 renglones, 5 410,73 USD) | I5 |
| `industrial/activos_planta.csv` | industrial | `adapters/industrial/adaptador.py` (`AdaptadorIndustrial`) | 10 activos de planta con frecuencia anual de intervención y horizonte; la cantidad es intervenciones en el horizonte | I5 |
| `sistemas/alcance_funcional.csv` | sistemas | `adapters/sistemas/adaptador.py` (`AdaptadorSistemas`) | 9 casos de uso en 3 módulos con entradas, salidas, consultas, archivos e interfaces; la cantidad son puntos de función sin ajustar | I5 |
| `precios/lista_2026-06-01.csv` | — (transversal) | `core/catalog/precios.py` (UC‑02) | lista de precios de muestra: cemento 15 → 18, arena 30 → 33, resto igual que la línea base | I1 |
| `tanquilla.ifc` | civil | `adapters/civil/` (I3.1) | **pendiente**: modelar una sola tanquilla en Revit o Bonsai, con el Pset `Pset_APU` (`COVENIN_Codigo`, `Partida_Descripcion`, `Unidad`) y exportar a IFC 4. Compuerta G1 abierta; mientras tanto el adaptador tabular es la entrada civil (CLAUDE.md §8.2) | antes de I3.1 |

Nota sobre telecom: los presupuestos ARENAZA usan una política de mano de obra distinta ("50 % del
total") en lugar del APU por rendimiento. El análisis de cómo representarla sin tocar `core/` está en
`docs/bitacora/2026-08-29-I5-telecom.md` (hallazgo 1); no se implementa en el alpha.

La evidencia primaria del caso civil (los cinco APU) está en `../linea_base/APUS_CLINICA.pdf`; su
versión ejecutable es `tests/fixtures/apu_linea_base.py`.
