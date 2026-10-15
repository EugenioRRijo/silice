"""Los anexos de S1 y S2 del paquete: filas con huella, SIN cadena propia (spec S3 §8.1).

`anexo_de_tablas` serializa, de las tablas que se le piden, las filas del proyecto (por su
`proyecto_id` o, si no la tienen, por la clave foránea hacia una tabla ya incluida). Cada fila lleva
su propia huella SHA-256; borrar una fila en la base antes de exportar NO se detecta dentro de la
base (límite declarado, S3 §12): solo entre entregas (`anterioridad`).

Los nombres de las tablas son los de S1 y S2 (specs, §5.2 y §6.1). Una tabla que esta versión de
Sílice no conoce se omite sin error: el anexo trae lo que existe. Una prueba recorre los metadatos
y exige que **toda tabla con una columna `responsable`** esté en un anexo o en la lista de las que
no viajan (RF-82), así que una tabla nueva sin dueño hace fallar la lista.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Table, false, select
from sqlalchemy.orm import Session

from core.budget.canonico import huella, json_canonico
from core.models import Base

__all__ = [
    "FORMATO_ANEXO",
    "TABLAS_DE_CONTROL",
    "TABLAS_DE_REAJUSTE",
    "TABLAS_QUE_NO_VIAJAN",
    "anexo_de_tablas",
    "huellas_de_entradas",
]

FORMATO_ANEXO = "silice-anexo"
#: S1 (`anexos/reajuste.json`): índices usados con su fuente y la huella del archivo del BCV;
#: moneda del proyecto, cláusula y estudios de reajuste.
TABLAS_DE_REAJUSTE = (
    "serie_indice",
    "importacion_indice",
    "valor_indice",
    "moneda_proyecto",
    "lista_empresa",
    "clausula_reajuste",
    "componente_clausula",
    "estudio_reajuste",
    "periodo_reajuste",
    "ejecutado_periodo",
)
#: S2 (`anexos/control.json`): línea base y calendario, valuaciones, anulaciones, costos incurridos
#: y decisiones de recuperación, con la fecha de registro de cada valuación.
TABLAS_DE_CONTROL = (
    "linea_base_control",
    "calendario_obra",
    "parametros_control",
    "valuacion",
    "linea_valuacion",
    "anulacion_valuacion",
    "costo_real",
    "decision_recuperacion",
)
#: Tablas con columna `responsable` que NO viajan: ya están en `presupuesto.json` y `cadena.json`
#: (el `RegistroCambio` va en la cadena) o son del catálogo.
TABLAS_QUE_NO_VIAJAN = ("registro_cambio",)


def _valor(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    if isinstance(valor, bytes):
        return base64.b64encode(valor).decode("ascii")
    return valor


def _filas(sesion: Session, tabla: Table, condicion) -> list[dict[str, Any]]:
    consulta = select(tabla)
    if condicion is not None:
        consulta = consulta.where(condicion)
    llaves = list(tabla.primary_key.columns)
    if llaves:
        consulta = consulta.order_by(*llaves)
    return [
        {col: _valor(valor) for col, valor in fila.items()}
        for fila in sesion.execute(consulta).mappings()
    ]


def anexo_de_tablas(
    sesion: Session, nombre: str, tablas: Sequence[str], proyecto_id: int
) -> bytes | None:
    """El JSON canónico del anexo `nombre`, o `None` si no hay ninguna fila que enviar."""
    incluidas: dict[str, list[dict[str, Any]]] = {}
    for tabla_nombre in tablas:
        tabla = Base.metadata.tables.get(tabla_nombre)
        if tabla is None:
            continue
        condicion = None
        if "proyecto_id" in tabla.c:
            condicion = tabla.c.proyecto_id == proyecto_id
        else:  # sin proyecto: por el padre ya incluido, o por un padre con `proyecto_id`
            claves = sorted(tabla.foreign_keys, key=lambda c: c.parent.name)
            for clave in claves:
                padre = clave.column.table.name
                if padre in incluidas:
                    ids = {fila[clave.column.name] for fila in incluidas[padre]}
                    condicion = clave.parent.in_(ids) if ids else false()
                    break
            else:  # p. ej. `clausula_reajuste` -> `presupuesto`; sin ninguno de los dos, global
                for clave in claves:
                    padre_t = clave.column.table
                    if padre_t is not tabla and "proyecto_id" in padre_t.c:
                        del_proyecto = select(clave.column).where(
                            padre_t.c.proyecto_id == proyecto_id
                        )
                        condicion = clave.parent.in_(del_proyecto)
                        break
        incluidas[tabla_nombre] = _filas(sesion, tabla, condicion)
    entradas = [
        {"tabla": tabla, "fila": fila, "huella": huella(json_canonico(fila))}
        for tabla, filas in incluidas.items()
        for fila in filas
    ]
    if not entradas:
        return None
    return json_canonico(
        {"formato": FORMATO_ANEXO, "nombre": nombre, "version_formato": 1, "entradas": entradas}
    )


def huellas_de_entradas(anexo: dict[str, Any]) -> list[str]:
    """Las huellas de cada entrada de un anexo ya leído (para comparar entre entregas, §6.5)."""
    return [entrada["huella"] for entrada in anexo.get("entradas", [])]
