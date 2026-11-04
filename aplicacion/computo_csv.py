"""El CSV de un cómputo con la regla de Eugenio (pulido F5, tanda 2, Tarea 5).

`POST /computos/{dominio}` lee el CSV con el adaptador del dominio (`adapters/<dominio>/`), que
espera columnas separadas por coma y punto decimal. Excel en español guarda los CSV separados por
punto y coma, con coma decimal y punto de miles («1.234,56»), que es la regla de Eugenio para toda
cifra. Este módulo deja ese archivo en la forma de siempre antes de que lo lea el adaptador:

- si la cabecera separa con `;`, las celdas de las columnas numéricas del adaptador se leen con
  `aplicacion.cifras.cifra_escrita` (coma decimal y punto de miles, el único intérprete de la
  regla) y se escriben con punto decimal en un CSV separado por coma; las demás celdas (el código,
  la descripción, las especificaciones) pasan tal cual, y una celda vacía queda vacía;
- si separa con coma, el archivo no se toca: los que ya existen siguen leyéndose igual, con punto
  decimal.

El separador se decide por la cabecera, como en el CSV de tramos (`adapters/vial/tabular.py`). Un
archivo con `;` admite la marca UTF-8 que pone Excel. Todo error es un `ValueError` con el nombre
del archivo y la fila como la numera una hoja de cálculo (la cabecera es la fila 1), que la API
traduce a 422. Va en la capa de aplicación porque un adaptador no puede importar
`aplicacion.cifras` (NORMAS.md §2) y así la regla no se copia en cuatro adaptadores.
"""

from __future__ import annotations

import csv
from collections.abc import Collection
from pathlib import Path

from aplicacion.cifras import CifraInvalida, cifra_escrita

__all__ = ["a_la_forma_de_siempre"]

_PUNTO_Y_COMA = ";"


def _ilegible(nombre: str) -> ValueError:
    return ValueError(f"el archivo {nombre!r} es ilegible: no es un CSV de texto en UTF-8")


def _con_punto(texto: str, nombre: str, fila: int, columna: str) -> str:
    if not texto.strip():
        return ""
    try:
        return format(cifra_escrita(texto), "f")
    except CifraInvalida as error:
        raise ValueError(
            f"el archivo {nombre!r}, fila {fila}: la columna {columna!r} trae {texto!r}. {error}"
        ) from None


def a_la_forma_de_siempre(ruta: Path, numericas: Collection[str], carpeta: Path) -> Path:
    """El CSV que lee el adaptador: `ruta` si separa con coma; si separa con `;`, una copia en
    `carpeta` con el mismo nombre, separada por coma y con las `numericas` en punto decimal.

    `carpeta` no debe ser la de `ruta` (la copia lleva su nombre, que los adaptadores usan en sus
    mensajes y para decidir por la extensión).
    """
    nombre = ruta.name
    try:
        with ruta.open(newline="", encoding="utf-8-sig") as archivo:
            if _PUNTO_Y_COMA not in archivo.readline():
                return ruta
            archivo.seek(0)
            lector = csv.DictReader(archivo, delimiter=_PUNTO_Y_COMA)
            columnas = list(lector.fieldnames or ())
            filas: list[dict[str, str]] = []
            for fila in lector:
                if None in fila:
                    raise ValueError(
                        f"el archivo {nombre!r}, fila {lector.line_num}: trae más celdas que la "
                        "cabecera"
                    )
                filas.append(
                    {
                        columna: (
                            _con_punto(valor or "", nombre, lector.line_num, columna)
                            if columna in numericas
                            else valor or ""
                        )
                        for columna, valor in fila.items()
                    }
                )
    except UnicodeDecodeError:
        raise _ilegible(nombre) from None
    destino = carpeta / nombre
    with destino.open("w", newline="", encoding="utf-8") as salida:
        escritor = csv.DictWriter(salida, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)
    return destino
