"""Presupuesto, curva de inversión (cierra al 100 % por construcción) y exportación a Excel.

Sesiones I0.5 e I1.

Flujo completo de la Sesión I0.5::

    from core.budget import elaborar, exportar_excel, plan_secuencial

    resultado = elaborar(
        items, composiciones, parametros, codigo="001", fecha=hoy, plan=plan_secuencial
    )
    exportar_excel(resultado.presupuesto, resultado.informe, Path("presupuesto.xlsx"))

`elaborar` audita siempre: no existe forma de obtener el presupuesto sin su informe (principio 7 de
NORMAS.md §2).

`guardar_presupuesto` y `cargar_presupuesto` implementan el versionado híbrido de
`docs/modelo_datos.md` §5: el renglón guardado congela su `ResultadoAPU` y al cargar se comprueba
que el catálogo sigue reproduciéndolo. `cargar_elaboracion` recarga además el informe del documento
emitido, con los ítems pendientes guardados junto al presupuesto (INV‑080).
"""

from core.budget.actualizacion import (
    COLUMNAS_COMPARATIVO,
    Comparativo,
    actualizar_precios,
    descartar_version,
)
from core.budget.cotizacion import cotizaciones_de_version, cotizar_insumo, retirar_cotizacion
from core.budget.curva import (
    PeriodoPlan,
    PlanInvalido,
    con_curva,
    generar_curva,
    plan_secuencial,
)
from core.budget.edicion import (
    CambioEditado,
    guardar_edicion,
    registros_de_version,
    restaurar_version,
    siguiente_codigo,
    tabla_trazabilidad,
    version_vigente,
)
from core.budget.equilibrio import EstadoEquilibrio, PuntoEquilibrio, punto_equilibrio
from core.budget.escenarios import (
    COLUMNAS_ESCENARIOS,
    Escenario,
    comparar_escenarios,
    comparar_por_partida,
    generar_escenario,
)
from core.budget.excel import TablaExportable, exportar_excel, exportar_hoja
from core.budget.importacion import (
    PresupuestoImportado,
    importar_presupuesto,
    leer_presupuesto_tabular,
)
from core.budget.instantanea import (
    ResultadoInstantanea,
    asegurar_instantanea,
    composiciones_de_presupuesto,
    plan_de_version,
)
from core.budget.moneda import convertir_version, declarar_moneda, moneda_del_proyecto
from core.budget.persistencia import (
    cargar_elaboracion,
    cargar_presupuesto,
    crear_proyecto,
    guardar_presupuesto,
)
from core.budget.presupuesto import (
    CODIGO_ATIPICO,
    CODIGO_PENDIENTE,
    DetectorAtipicos,
    GeneradorPlan,
    MarcaAtipica,
    ResultadoElaboracion,
    elaborar,
    generar_presupuesto,
    hallazgos_externos,
)

__all__ = [
    "CODIGO_ATIPICO",
    "CODIGO_PENDIENTE",
    "COLUMNAS_COMPARATIVO",
    "COLUMNAS_ESCENARIOS",
    "CambioEditado",
    "Comparativo",
    "DetectorAtipicos",
    "Escenario",
    "EstadoEquilibrio",
    "GeneradorPlan",
    "MarcaAtipica",
    "PeriodoPlan",
    "PlanInvalido",
    "PresupuestoImportado",
    "PuntoEquilibrio",
    "ResultadoElaboracion",
    "ResultadoInstantanea",
    "TablaExportable",
    "actualizar_precios",
    "asegurar_instantanea",
    "cargar_elaboracion",
    "cargar_presupuesto",
    "comparar_escenarios",
    "comparar_por_partida",
    "composiciones_de_presupuesto",
    "con_curva",
    "convertir_version",
    "cotizaciones_de_version",
    "cotizar_insumo",
    "crear_proyecto",
    "declarar_moneda",
    "descartar_version",
    "elaborar",
    "exportar_excel",
    "exportar_hoja",
    "generar_curva",
    "generar_escenario",
    "generar_presupuesto",
    "guardar_edicion",
    "guardar_presupuesto",
    "hallazgos_externos",
    "importar_presupuesto",
    "leer_presupuesto_tabular",
    "moneda_del_proyecto",
    "plan_de_version",
    "plan_secuencial",
    "punto_equilibrio",
    "registros_de_version",
    "restaurar_version",
    "retirar_cotizacion",
    "siguiente_codigo",
    "tabla_trazabilidad",
    "version_vigente",
]
