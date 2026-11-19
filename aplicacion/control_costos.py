"""Los costos incurridos anotados de una obra, para verlos (prueba en vivo 2026-11-18, hallazgo 3).

Solo existía anotarlos (`POST /v1/control/costos`): un costo mal tecleado no se volvía a ver y
dejaba el AC y el CPI mal sin que nadie lo notara. Aquí se listan, en el orden en que se anotaron.

**Anularlos queda declarado, no hecho**: la anulación necesita expediente de `core/`. El núcleo
lee todas las filas de `costo_real` al armar la instantánea (`core/budget/valuaciones.py`,
`instantanea_control`) y `registrar_costo` rechaza un monto negativo, así que ni una tabla de
anulaciones en `aplicacion` (el núcleo no la leería) ni un asiento de reverso con monto negativo
(el núcleo lo rechaza) sacan un costo del cálculo sin cambiar `core/`. Lo que hace falta: una
tabla `anulacion_costo` (como `anulacion_valuacion`) con su migración de `casos/*.db` y el filtro
en `instantanea_control`, o aceptar un reverso negativo que cite el costo que anula.

El texto de cada fila (fuente, partida, responsable) es de quien lo escribió: viaja como dato y
la pantalla lo pinta como texto. El monto va **exacto**, con punto y la escala con que se guardó:
la pantalla lo presenta a dos decimales en es-VE y deja el exacto en el `title`, así la suma de
la tabla cuadra con el AC (arbitraje de feature/vivo-control).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models

__all__ = ["COLUMNAS_COSTOS", "filas_de_costos"]

COLUMNAS_COSTOS = ("Fecha", "Monto", "Moneda", "Partida", "Fuente", "Responsable")


def filas_de_costos(sesion: Session, proyecto: str) -> list[dict[str, str]]:
    """Los costos incurridos de la obra `proyecto` (su nombre), en el orden en que se anotaron."""
    costos = sesion.scalars(
        select(models.CostoReal)
        .join(models.Proyecto, models.Proyecto.id == models.CostoReal.proyecto_id)
        .where(models.Proyecto.nombre == proyecto)
        .order_by(models.CostoReal.id)
    )
    return [
        {
            "Fecha": f"{c.fecha:%d/%m/%Y}",
            "Monto": format(c.monto, "f"),
            "Moneda": c.moneda,
            "Partida": c.codigo_partida or "",
            "Fuente": c.fuente,
            "Responsable": c.responsable,
        }
        for c in costos
    ]
