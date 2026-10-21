"""Exportar el borrador vivo de la hoja a Excel (T10, 3e-1; ruta X1 del diseno §4.1).

Es `_preparar_excel` de la pagina clasica (`ui/paginas/hoja.py:556-573`) hecha funcion, sobre la
COPIA `aplicacion.hoja` (Plan C: la clasica esta en el congelado del experimento y no se toca):
el resultado y el borrador VIVOS (`hoja_vista.calculo`) y, si el borrador tiene una version abierta,
ademas la trazabilidad, los precios con su origen y las hojas de control de esa version. Sin version
abierta solo salen las hojas del borrador.

No escribe nada: ni en la base, ni en el borrador (`rev` no cambia), ni deja archivos temporales
(`excel_de_hoja_en_bytes` arma el libro en una carpeta que borra al terminar). Sin FastAPI ni
Streamlit (RM-1): los errores (`ValueError`, `SQLAlchemyError`) los traduce la ruta.

**Caracteres que un .xlsx no puede llevar** (ola de decisiones, 2026-10-21). E1 acepta cualquier
texto (como la clasica) y el libro se rompia: un control C0 en una celda daba
`IllegalCharacterError` (422) y U+FFFE, U+FFFF o un sustituto suelto daban un libro que ni
openpyxl podia leer. Ahora `sanear_para_xlsx` cambia cada uno por U+FFFD en el PUNTO DE SALIDA: se
recorre una copia de lo que se exporta (el borrador vivo, la base y la clasica no cambian) y todo
texto prohibido se sustituye. Se sustituye en vez de borrar para no perder la posicion ni callar
que ahi habia algo. La `IllegalCharacterError` que aun se escape (un tipo que el recorrido no abre)
sigue siendo un `ValueError` con texto fijo.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from datetime import date
from enum import Enum
from typing import Any

from openpyxl.utils.exceptions import IllegalCharacterError
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
#: Lo que XML 1.0 (y por tanto un .xlsx) prohibe en un texto: los controles C0 salvo tabulador,
#: salto de linea y retorno, los sustitutos sueltos U+D800 a U+DFFF y U+FFFE y U+FFFF. Medido con
#: openpyxl (ver la bitacora): U+007F, U+0080 a U+009F, U+FDD0, U+FFFD, U+1FFFE y U+10FFFF SI se
#: leen. Se arma con `chr` para que ninguna herramienta cambie los caracteres del archivo fuente.
_PROHIBIDOS = re.compile(
    "["
    + chr(0x00)
    + "-"
    + chr(0x08)
    + chr(0x0B)
    + chr(0x0C)
    + chr(0x0E)
    + "-"
    + chr(0x1F)
    + chr(0xD800)
    + "-"
    + chr(0xDFFF)
    + chr(0xFFFE)
    + chr(0xFFFF)
    + "]"
)
#: Lo que reemplaza a cada caracter prohibido: el caracter de sustitucion de Unicode.
SUSTITUTO = chr(0xFFFD)
CARACTER_ILEGAL = (
    "una celda trae un carácter de control que Excel no admite (por ejemplo, uno pegado desde otro "
    "programa): quítelo del espacio y vuelva a intentarlo."
)


def sanear_para_xlsx[T](valor: T) -> T:
    """Una copia de `valor` con todo texto sin los caracteres que un .xlsx no admite (cada uno pasa
    a U+FFFD). Recorre textos, dataclasses (tambien las congeladas y con `slots`), tuplas, listas,
    conjuntos y diccionarios (sus claves tambien); numeros, fechas, `Enum` y cualquier otro objeto
    pasan tal cual. Si nada cambia devuelve el MISMO objeto: no copia lo que ya esta limpio."""
    return _sanear(valor)


def _sanear(valor: Any) -> Any:
    if isinstance(valor, Enum):  # un `StrEnum` es un `str`, pero su valor es del codigo
        return valor
    if isinstance(valor, str):
        return _PROHIBIDOS.sub(SUSTITUTO, valor)
    if is_dataclass(valor) and not isinstance(valor, type):
        cambios = {}
        for campo in fields(valor):
            if campo.init:
                antes = getattr(valor, campo.name)
                despues = _sanear(antes)
                if despues is not antes:
                    cambios[campo.name] = despues
        return replace(valor, **cambios) if cambios else valor
    if isinstance(valor, Mapping):
        pares = [(_sanear(k), _sanear(v)) for k, v in valor.items()]
        if all(k is a and v is b for (k, v), (a, b) in zip(pares, valor.items(), strict=True)):
            return valor
        return type(valor)(pares) if isinstance(valor, dict) else dict(pares)
    if isinstance(valor, (list, tuple, set, frozenset)):
        elementos = [_sanear(e) for e in valor]
        if all(a is b for a, b in zip(elementos, valor, strict=True)):
            return valor
        if isinstance(valor, tuple) and hasattr(valor, "_fields"):  # una tupla con nombre
            return type(valor)(*elementos)
        return type(valor)(elementos)
    return valor


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
    try:
        contenido = hoja.excel_de_hoja_en_bytes(
            *sanear_para_xlsx((resultado, borrador)),
            **sanear_para_xlsx(
                {"trazabilidad": trazabilidad, "precios": precios, "control": hojas_de_control}
            ),
        )
    except IllegalCharacterError:  # no es un ValueError; el texto de openpyxl repetiria la celda
        raise ValueError(CARACTER_ILEGAL) from None
    return nombre_de_archivo(abierta.codigo if abierta is not None else None), contenido
