"""Exportar el borrador vivo de la hoja a Excel (T10, 3e-1; ruta X1 del diseno §4.1).

Es `_preparar_excel` de la pagina clasica (`ui/paginas/hoja.py:556-573`) hecha funcion, sobre la
COPIA `aplicacion.hoja` (Plan C: la clasica esta en el congelado del experimento y no se toca):
el resultado y el borrador VIVOS (`hoja_vista.calculo`) y, si el borrador tiene una version abierta,
ademas la trazabilidad, los precios con su origen y las hojas de control de esa version. Sin version
abierta solo salen las hojas del borrador.

No escribe nada: ni en la base, ni en el borrador (`rev` no cambia), ni deja archivos temporales
(`excel_de_hoja_en_bytes` arma el libro en una carpeta que borra al terminar). Sin FastAPI ni
Streamlit (RM-1): los errores (`ValueError`, `SQLAlchemyError`) los traduce la ruta.
"""

from __future__ import annotations

import re
from datetime import date

from sqlalchemy.orm import Session

from aplicacion import control, hoja, hoja_vista
from aplicacion.hoja_borradores import BorradorVivo
from core.catalog import Catalogo

#: Todo lo que no sea A-Z a-z 0-9 . _ - se reemplaza: un codigo de version con comillas, saltos de
#: linea, barras o letras raras no puede romper `Content-Disposition` ni armar una ruta.
_NO_SEGURO = re.compile(r"[^A-Za-z0-9._-]")
#: Tope del codigo en el nombre (supuesto: ningun codigo real se acerca). El recorte va ANTES de la
#: sustitucion: el costo no depende del largo de lo escrito.
LARGO_MAXIMO_DEL_CODIGO = 100
NOMBRE_SIN_VERSION = "hoja_borrador.xlsx"


def nombre_de_archivo(codigo: str | None) -> str:
    """`hoja_{codigo}.xlsx` con el codigo ya seguro; `hoja_borrador.xlsx` sin version abierta."""
    if codigo is None:
        return NOMBRE_SIN_VERSION
    seguro = _NO_SEGURO.sub("_", codigo[:LARGO_MAXIMO_DEL_CODIGO]) or "version"
    return f"hoja_{seguro}.xlsx"


def excel_del_borrador(vivo: BorradorVivo, sesion: Session, hoy: date) -> tuple[str, bytes]:
    """El nombre y los bytes del libro del borrador vivo, como los arma la clasica (P:556-573).

    `hoy` es el dia de la evaluacion de los precios. Puede lanzar `ValueError` (el libro no se pudo
    armar) o `SQLAlchemyError` (no se pudo leer el caso). El resultado y el borrador se toman
    juntos bajo el cerrojo: son los del mismo `rev`, aunque otra ventana edite despues."""
    with vivo.cerrojo:
        resultado, _ = hoja_vista.calculo(vivo)
        borrador, abierta = vivo.borrador, vivo.abierta
    trazabilidad, precios, hojas_de_control = None, (), []
    if abierta is not None:
        trazabilidad = hoja.tabla_de_trazabilidad(sesion, abierta.proyecto, abierta.codigo)
        precios = hoja.precios_de_version(
            sesion, abierta.proyecto, abierta.codigo, fecha_evaluacion=hoy
        )
        hojas_de_control = control.tablas_de_control(sesion, abierta.proyecto, Catalogo(sesion))
    contenido = hoja.excel_de_hoja_en_bytes(
        resultado,
        borrador,
        trazabilidad=trazabilidad,
        precios=precios,
        control=hojas_de_control,
    )
    return nombre_de_archivo(abierta.codigo if abierta is not None else None), contenido
