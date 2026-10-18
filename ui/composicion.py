"""Reexportación de `aplicacion.composicion` (RM-1, plan de la sesión 2b).

La lógica de composición (tablas a contrato, desglose, referencia MaPreX y ayudas de Sílice) se
movió a `aplicacion/composicion.py` para que la API y la interfaz clásica la compartan sin que
`api/` importe `ui/`. Este módulo conserva los nombres que usan las páginas, los scripts y las
pruebas; no define nada.
"""

from aplicacion.composicion import (
    ComposicionInvalida,
    ContrasteAace,
    FilaReferencia,
    advertencia_precio_atipico,
    buscar_referencia,
    composicion_desde_tablas,
    contrastar_precio_con_reglas,
    decimal_desde_texto,
    desglose,
    etiqueta_referencia,
    fila_equipos_desde_referencia,
    fila_mano_obra_desde_referencia,
    fila_materiales_desde_referencia,
    filas_desde_composicion,
    formulario_vacio,
    item_desde_cantidad,
    motivo_para_no_reemplazar,
    sugerir_partidas_similares,
    texto_de_celda,
    veredicto_ml_rendimiento,
)

__all__ = [
    "ComposicionInvalida",
    "ContrasteAace",
    "FilaReferencia",
    "advertencia_precio_atipico",
    "buscar_referencia",
    "composicion_desde_tablas",
    "contrastar_precio_con_reglas",
    "decimal_desde_texto",
    "desglose",
    "etiqueta_referencia",
    "fila_equipos_desde_referencia",
    "fila_mano_obra_desde_referencia",
    "fila_materiales_desde_referencia",
    "filas_desde_composicion",
    "formulario_vacio",
    "item_desde_cantidad",
    "motivo_para_no_reemplazar",
    "sugerir_partidas_similares",
    "texto_de_celda",
    "veredicto_ml_rendimiento",
]
