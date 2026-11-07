# Árbitro: topes del lector del libro conocido (Claude xhigh, 2026-11-07)

Rama `feature/lector-topes` sobre `feature/integracion-fases` (5a1bca93). Revisor nuevo de Claude con esfuerzo xhigh,
sin las conclusiones del orquestador (decisión de Eugenio del 2026-11-05). Objeto: ESTADO §5.3, un `.xlsx` hostil con
celdas lejanas que la `<dimension>` no declara hacía que el lector del libro conocido (`adapters/hoja_empresa/lector.py`)
tardara minutos.

## Ronda 1 (cabeza b4689e32): APROBADO CON CONDICIONES

Lo que comprobó el árbitro: rojo honesto contra 98c50cdd (8 «DID NOT RAISE» y las dos fronteras que deben leerse en
verde); 152 + 407 pruebas de los archivos que leen libros en verde; las tres rutas de `/v1/libros` (auditoría, devolución
y réplica) responden 422 con el aviso completo en 0,09 a 0,24 s; dos hojas en su tope se aceptan en 4,45 s y una tercera
se rechaza en 4,57 s; `core/` sin cambios; ruff limpio.

| # | Gravedad | Hallazgo | Veredicto del orquestador | Corrección |
|---|---|---|---|---|
| 1 | MENOR | ESTADO §5.3, CHANGELOG, manual §12 y los comentarios `SUPUESTO_DECLARADO` de `guardia.py` no decían que los topes valen ahora para los tres recorridos | Confirmado | ESTADO, CHANGELOG, manual §12.1 y `guardia.py` al día |
| 2 | MENOR | La prueba del tope del libro usaba 10: no fijaba el `>` ni que la cuenta es por pasada | Confirmado | `test_el_tope_del_libro_conocido_es_por_pasada_y_su_frontera_se_lee`: N medido con el contador de openpyxl; tope N se lee, N − 1 se rechaza |
| 3 | MENOR | `_miles` duplicado en `lector.py` y `guardia.py` | Confirmado | `guardia.miles`, pública, la única |
| 4 | NOTA | `get_column_letter` falla por encima de 18.278: una fila hostil más ancha daba «alguna hoja está dañada» | Confirmado (rojo: `ValueError: Invalid column index 18279`) | `lector.letra` sin límite, la única (el lector de un APU por hoja la reexporta); prueba con una hoja ficticia de 18.279 celdas |
| 5 | NOTA | Docstrings de `leer_libro`, `replicar_libro` y la cabecera del lector sin el rechazo nuevo | Confirmado | Actualizados |
| 6 | NOTA | La réplica acepta una celda lejana en una hoja sin fórmulas (preexistente; la interfaz descarta las dos respuestas si una falla) | Fuera de alcance | Decisión de Eugenio (ESTADO §4.10 a) |
| 7 | NOTA | `core/catalog/precios.py` (`leer_tabla`) recorre sin tope las listas y presupuestos subidos | Fuera de alcance (núcleo) | Decisión de Eugenio (ESTADO §4.10 b) |
| 8 | NOTA | Las medidas de los libros reales no descartan del todo una hoja de más de 100 columnas | Para Eugenio | Probar en local (ESTADO §4.10 c) |

Commits de la corrección: `test(hoja_empresa): frontera del tope por pasada y fila mas ancha que XFD (rojo)` y
`fix(hoja_empresa): una sola letra de columna sin limite y un solo punto de miles; ...` (verde). Las condiciones del
árbitro (MENOR 1) quedan cumplidas; los MENOR 2 y 3 y las NOTAS 4 y 5, también.
