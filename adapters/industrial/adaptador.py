"""Adaptador del dominio industrial: registro de activos con frecuencia de intervención (Sesión I5).

Lee un CSV de activos de planta (bombas, tableros, compresores, transformadores, válvulas, motores…)
y convierte cada fila en un `ItemComputo` trazable: la cantidad de obra es el número de
intervenciones de mantenimiento esperadas en el horizonte de planificación, `frecuencia_anual *
horizonte_anios`, declarada como regla para que el informe de auditoría muestre la expresión exacta
que la produjo (regla R1, CLAUDE.md §7). La muestra y sus supuestos están en
`data/samples/industrial/README.md`.
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from adapters.industrial.evaluador import evaluar_regla
from core.contracts import AdaptadorDominio, Dominio, ItemComputo, OrigenTipo

REGLA_INTERVENCIONES = "frecuencia_anual * horizonte_anios"

_COLUMNAS_NUMERICAS = ("frecuencia_anual", "horizonte_anios")
_COLUMNAS = ("id_activo", "descripcion", "codigo_partida", "unidad", *_COLUMNAS_NUMERICAS)


def _parsear_especificaciones(texto: str | None) -> dict[str, str]:
    """`"clave=valor;clave=valor"` -> `{"clave": "valor", ...}`. Cadena vacía -> diccionario vacío.

    Convierte el texto de la columna `especificaciones` del CSV en el diccionario que espera
    `ItemComputo.especificaciones` (regla R4).
    """
    resultado: dict[str, str] = {}
    for par in (texto or "").split(";"):
        par = par.strip()
        if not par:
            continue
        clave, _, valor = par.partition("=")
        resultado[clave.strip()] = valor.strip()
    return resultado


def _leer_filas(
    fuente: Path | str, columnas: tuple[str, ...], dominio: Dominio
) -> list[dict[str, str]]:
    """Las filas del CSV, o `ValueError` con el nombre del archivo si no es una fuente de `dominio`.

    UC-01, flujo 2a (INV-089): un archivo binario (no es texto UTF-8) o sin las columnas que este
    adaptador lee (la muestra de otro dominio) se rechaza nombrando el archivo, con el
    `ValueError` que la API traduce a 422, en vez de un `KeyError` de la primera columna que
    falte. Cada adaptador tiene su copia: ninguno importa de otro (CLAUDE.md §2).
    """
    nombre = Path(fuente).name
    try:
        with open(fuente, newline="", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            presentes = lector.fieldnames or ()
            faltantes = [columna for columna in columnas if columna not in presentes]
            if faltantes:
                raise ValueError(
                    f"el archivo {nombre!r} no es una fuente del dominio {dominio.value}: "
                    f"faltan las columnas {faltantes}"
                )
            return list(lector)
    except UnicodeDecodeError as error:
        raise ValueError(
            f"el archivo {nombre!r} es ilegible: no es un CSV de texto en UTF-8"
        ) from error


def _decimal(fila: dict[str, str], columna: str, fuente: Path | str) -> Decimal:
    """`fila[columna]` como `Decimal`, o `ValueError` con el archivo, la fila y la columna.

    Una celda vacia o no numerica lanzaria `decimal.InvalidOperation` sin contexto, que la API no
    traduce a 422 (INV-089, UC-01 flujo 2a).
    """
    valor = (fila.get(columna) or "").strip()
    try:
        return Decimal(valor)
    except InvalidOperation as error:
        raise ValueError(
            f"el archivo {Path(fuente).name!r}, fila {fila.get('id_activo')!r}: la columna "
            f"{columna!r} esta vacia o no es numerica: {valor!r}"
        ) from error


class AdaptadorIndustrial(AdaptadorDominio):
    """Extrae cantidades de mantenimiento de un registro de activos de planta.

    Cada fila del CSV es un activo con su frecuencia de intervención anual; la cantidad de obra
    (unidad declarada en la fila, típicamente "intervencion") es esa frecuencia multiplicada por el
    horizonte de planificación en años, evaluada por `REGLA_INTERVENCIONES` (trazable, regla R1).
    """

    dominio = Dominio.INDUSTRIAL

    def extraer(self, fuente: Path | str) -> list[ItemComputo]:
        items: list[ItemComputo] = []
        for fila in _leer_filas(fuente, _COLUMNAS, self.dominio):
            parametros = {
                columna: _decimal(fila, columna, fuente) for columna in _COLUMNAS_NUMERICAS
            }
            cantidad = evaluar_regla(REGLA_INTERVENCIONES, parametros)
            items.append(
                ItemComputo(
                    codigo_partida=fila["codigo_partida"],
                    descripcion=fila["descripcion"],
                    unidad=fila["unidad"],
                    cantidad=cantidad,
                    origen_id=fila["id_activo"],
                    origen_tipo=OrigenTipo.REGLA,
                    dominio=Dominio.INDUSTRIAL,
                    regla=REGLA_INTERVENCIONES,
                    parametros=parametros,
                    especificaciones=_parsear_especificaciones(fila.get("especificaciones")),
                )
            )
        return items
