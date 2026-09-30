"""Auditoría técnica del programa del 30/09/2026 (main = f0c102b): datos del informe TI-001.

Instantánea fechada: la lee `scripts/informe_ti001.py` (sección 2 del PDF). Los hallazgos A-1, A-2 y
M-1 a M-3 quedan registrados en `docs/bitacora/2026-09-30-caso-ti001.md`.
"""

VEREDICTO_CORTO = (
    "Nucleo correcto; 1 hallazgo alto de seguridad (UI), 1 alto de verificacion (R4), 3 medios"
)

RESUMEN = [
    "Se audito el repositorio en <b>main = f0c102b</b> (fusion del PR #17, etiqueta gc6), en modo solo lectura: "
    "comprobaciones automaticas, revision manual del motor, la curva y las siete reglas, revision de seguridad de la API "
    "y la interfaz, uso de float en montos y estado de la deuda registrada.",
    "<b>Veredicto.</b> El nucleo de calculo cumple la especificacion: los materiales no se dividen entre el rendimiento, "
    "administracion y utilidad van en cascada, el destajo entra sin FCAS ni bono y la curva cierra por construccion. "
    "Las 1 191 pruebas pasan con -W error. Se encontraron defectos fuera de la aritmetica: en la regla R4, en la interfaz "
    "(subida de archivos) y en la exportacion a Excel.",
]

COMPROBACIONES = [
    [
        "uv run pytest -W error --strict-markers (suite completa)",
        "1 191 pruebas en 95 archivos: todas verdes",
    ],
    [
        "Pruebas del nucleo (arquitectura, costing, destajo, linea base, guardia)",
        "120 de 120 verdes",
    ],
    ["uv run ruff check .", "Sin errores"],
    ["uv run ruff format --check .", "29 archivos sin formato (la CI no lo comprueba)"],
    ["scripts/meta_prototipo.py, scripts/meta_redaccion.py", "12/12 y 12/12"],
    [
        "scripts/meta_datos.py",
        "2/3 en local: D1 lee graphify-out/, carpeta no versionada (en la CI pasa)",
    ],
    [
        "Float en montos (core, adapters, api, ui, scripts)",
        "Ninguno: solo puntajes de ML y geometria IFC",
    ],
    ["Recalculo independiente del caso TI-001 (seccion 10.2)", "Diferencia 0 en las 10 partidas"],
    [
        "Pruebas de control con errores sembrados (seccion 10.1)",
        "6 de 7 detectados; el que se escapa lo explica A-2",
    ],
]

HALLAZGOS = [
    [
        "A-1",
        "ALTO",
        "ui/paginas/actualizacion.py:236, elaborar.py:206, visor.py:90",
        "La interfaz guarda el archivo subido como carpeta_temporal / nombre_del_cliente sin limpiar el nombre. Con un "
        "nombre como '../../x.csv', enviado en una peticion multipart hecha a mano, escribe fuera de la carpeta temporal. "
        "La API ya se corrigio (INV-112, api/archivos.py:22), pero la UI no. Verificado en el codigo; la explotacion "
        "completa no se ejecuto.",
        "Mover guardar_subida a un modulo comun, usarlo en las tres pantallas y anadir una prueba. Si la UI se expone en red, fijar server.address.",
    ],
    [
        "A-2",
        "ALTO",
        "core/verification/reglas.py:398 (R4)",
        "R4 acepta una especificacion si su texto es una subcadena del texto del APU. Reproducido: 4 pulg contra un APU de "
        "3/4 pulg, 2 contra 1/2, 6 contra 16 y 1/2 contra 1 1/2 no se detectan. Como el corpus incluye la descripcion del "
        "propio item, una especificacion repetida en la descripcion se encuentra a si misma. Riesgo para el indicador 1 "
        "(7 de 7): el hallazgo 5 se pierde si la memoria repite el diametro.",
        "Comparar por pares numero-unidad completos (limites de palabra) y sacar item.descripcion del corpus. Toca core/: registrar en bitacora y decidir.",
    ],
    [
        "M-1",
        "MEDIO",
        "core/budget/excel.py:78, 106, 118, 130",
        "Las descripciones se escriben en el Excel sin escapar. openpyxl guarda un texto que empieza por '=' como formula: "
        "un presupuesto importado con una descripcion '=HYPERLINK(...)' se exporta como formula activa.",
        "Forzar tipo texto, o anteponer apostrofo, si el texto empieza por = + - @.",
    ],
    [
        "M-2",
        "MEDIO",
        "core/budget/excel.py:74-87",
        "Cada fila y el total se redondean por separado. En la linea base corregida las filas suman 1 610,93 y el TOTAL dice 1 610,92: "
        "la misma clase de inconsistencia que el sistema audita (hallazgos 3 y 7).",
        "Mostrar como TOTAL la suma de las filas redondeadas, o declarar la convencion en el propio libro.",
    ],
    [
        "M-3",
        "MEDIO",
        "adapters/telecom/adaptador.py:155",
        "El adaptador guarda 'origen' y 'destino' de cada tramo como especificaciones tecnicas. R4 no los encuentra en el APU "
        "y emite un INFO por clave: 40 avisos sin valor en este caso, que tapan los avisos utiles.",
        "Guardarlos como directivas (_origen, _destino), que R4 ignora.",
    ],
    [
        "B-1",
        "BAJO",
        "api/rutas/computos.py:76",
        "El parametro codigos='[1]' devuelve un error 500 en vez de un 422.",
        "Validar que sea un dict[str, str].",
    ],
    [
        "B-2",
        "BAJO",
        "api/archivos.py:26; api/rutas/presupuestos.py:299",
        "La subida se lee entera en memoria, sin limite de tamano. Las rutas de escritura no piden autenticacion. Si "
        "exportar_excel falla, el temporal creado con mkstemp queda sin borrar.",
        "Limitar el tamano, documentar que la API es solo local y borrar el temporal en un finally.",
    ],
    [
        "B-3",
        "BAJO",
        "Contrato ParametrosCosto",
        "El contrato admite un solo bono por obrero, pero MaPreX publica bonos distintos por oficio (2,34 a 6,22 USD/dia). "
        "En este caso el efecto es de -23,04 USD (-0,05 %).",
        "Declararlo como limitacion. No justifica cambiar un contrato estable.",
    ],
    [
        "B-4",
        "BAJO",
        "Repositorio",
        "29 archivos sin ruff format, 2 worktrees vivos con sus ramas ya fusionadas y 53 ramas locales fusionadas. "
        "Deuda abierta: INV-108, INV-109 e INV-116 (importante), pendientes de decision.",
        "Anadir ruff format --check a la CI y retirar los worktrees y las ramas fusionadas.",
    ],
]

FORTALEZAS = [
    "Motor puro con Decimal de punta a punta. Los contratos son inmutables y validan sus invariantes.",
    "La curva cierra por construccion. R2 y R7 no dieron falsos positivos al forzar magnitudes ni al cuantizar.",
    "La prueba de arquitectura y la guardia del nucleo pasan: los adaptadores solo importan core.contracts.",
    "Inventario de deuda trazable y al dia: 122 filas, 86 cerradas y 3 abiertas.",
    "El sistema permitio construir el caso TI-001 de punta a punta sin modificar el nucleo.",
]
