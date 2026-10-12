"""El conjunto EXACTO de los planos limpios (S3 §11.5 y §13.5 b; de S3-0).

`DXF_*` es lo que la hoja diría del DXF de OF-001 (`tests/fixtures/planos/of001.dxf`): los ítems
del informe de importación que no son «importado» y los hallazgos de R8 a R10 y R15 (R9, R10 y
R15 no dan ninguno). `IFC_*` es lo mismo del IFC de oficina de `planos_ifc_ids`. Lo regenera
`uv run python scripts/medir_deteccion_planos.py --limpio`; cambiarlo a mano es cambiar el
oráculo de la medición. Las constantes son tuplas de `(tipo, tabla, mensaje)` y de
`(regla, severidad, descripción)`.
"""

DXF_ITEMS = (
    ("aproximado", "esp_circuitos",
     "circuito C1: conductores 1-1-1 y 6 puntos maximos son supuestos declarados (SF5-1, "
     "SF5-2); ajustelos en la hoja"),
    ("aproximado", "esp_circuitos",
     "circuito C2: conductores 1-1-1 y 6 puntos maximos son supuestos declarados (SF5-1, "
     "SF5-2); ajustelos en la hoja"),
    ("aproximado", "esp_puntos",
     "PA1: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PA2: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PA3: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PB1: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PB2: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PB3: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PR1: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("pendiente", "esp_ambientes",
     "ambiente BAN-01: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente COC-01: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente CT-01: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente REC-01: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente ZA: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente ZB: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
)

DXF_HALLAZGOS = (
    ("R8", "ADVERTENCIA",
     "ambiente BAN-01: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente COC-01: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente CT-01: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente REC-01: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente ZA: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente ZB: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "circuito C1: circuito importado con conductores y puntos supuestos (1-1-1 y 6 puntos "
     "maximos; SF5-1, SF5-2); declarelos en la hoja"),
    ("R8", "ADVERTENCIA",
     "circuito C2: circuito importado con conductores y puntos supuestos (1-1-1 y 6 puntos "
     "maximos; SF5-1, SF5-2); declarelos en la hoja"),
)

IFC_ITEMS = (
    ("aproximado", "esp_ambientes",
     "SALON-L: no es rectangular; se importa su caja envolvente (6.0000 x 4.0000 m)"),
    ("no reconocido", "IfcOutlet",
     "IfcOutlet AUDIOVISUALOUTLET: 1 elemento fuera de la convencion; no se importan"),
    ("no reconocido", "IfcWall",
     "IfcWall: 1 elemento fuera de la convencion; no se importan"),
    ("pendiente", "esp_puntos",
     "1 aparato(s) sanitario(s): se importo su punto de agua fria; el drenaje no se infiere, "
     "se agrega en la hoja"),
    ("pendiente", "esp_puntos",
     "2 punto(s) electricos sin circuito: el IFC no los trae; se declaran en la hoja"),
    ("pendiente", "esp_puntos",
     "3 punto(s) de agua o datos sin fuente: el IFC no trae montante, colector ni rack; se "
     "asignan en la hoja"),
)

IFC_HALLAZGOS = (
)

LIMPIO = {
    "dxf": {"items": DXF_ITEMS, "hallazgos": DXF_HALLAZGOS},
    "ifc": {"items": IFC_ITEMS, "hallazgos": IFC_HALLAZGOS},
}
