"""Adaptador tabular del dominio telecom (Sesion I5).

Lee una topologia de red en CSV (nodos y enlaces) y devuelve las cantidades de obra trazables que
describe. Un nodo (punto WiFi, switch, rack, UPS...) es una cantidad tabular directa
(`OrigenTipo.CSV`); un enlace (tramo de cable UTP o fibra) deriva su cantidad de la regla
parametrica `longitud_m * (1 + reserva)` -la reserva cubre el excedente de instalacion: curvas,
empalmes y holgura de servicio-, evaluada por `adapters/telecom/evaluador.py` (regla R1 de
verificacion: trazabilidad geometrica).
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from adapters.telecom.evaluador import evaluar_regla
from core.contracts import AdaptadorDominio, Dominio, ItemComputo, OrigenTipo

_TIPO_NODO = "nodo"
_TIPO_ENLACE = "enlace"
_REGLA_LONGITUD_ENLACE = "longitud_m * (1 + reserva)"
_COLUMNAS = ("tipo", "id", "descripcion", "codigo_partida", "unidad")


def _parsear_especificaciones(texto: str | None) -> dict[str, str]:
    """`"clave=valor;clave=valor"` -> `{"clave": "valor", ...}`. Cadena vacia -> diccionario vacio.

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


def _decimal(fila: dict[str, str], columna: str) -> Decimal:
    """Convierte `fila[columna]` a `Decimal`, identificando la fila y la columna en el error.

    `cantidad` (nodo) y `longitud_m` (enlace) deben venir siempre llenos: una celda vacia o no
    numerica lanza `ValueError` con el `id` de la fila y el nombre de la columna, en vez del
    `decimal.InvalidOperation` generico que lanzaria `Decimal("")` sin contexto.
    """
    valor = (fila.get(columna) or "").strip()
    try:
        return Decimal(valor)
    except InvalidOperation as error:
        raise ValueError(
            f"fila {fila.get('id')!r}: columna {columna!r} vacia o no numerica: {valor!r}"
        ) from error


def _reserva(fila: dict[str, str]) -> Decimal:
    """`reserva` vacia equivale a `Decimal("0")` (documentado en data/samples/telecom/README.md);
    un valor presente pero no numerico sigue siendo un error, con la fila identificada.
    """
    valor = (fila.get("reserva") or "").strip()
    if not valor:
        return Decimal("0")
    try:
        return Decimal(valor)
    except InvalidOperation as error:
        raise ValueError(
            f"fila {fila.get('id')!r}: columna 'reserva' no numerica: {valor!r}"
        ) from error


class AdaptadorTelecom(AdaptadorDominio):
    """Extrae cantidades de obra de una topologia de red (nodos y enlaces) desde un CSV.

    Cada fila `nodo` es una cantidad tabular directa; cada fila `enlace` deriva su cantidad de una
    regla trazable. `origen_id` es la clave `id` de la fila del CSV en ambos casos.
    """

    dominio = Dominio.TELECOM

    def extraer(self, fuente: Path | str) -> list[ItemComputo]:
        items: list[ItemComputo] = []
        for fila in _leer_filas(fuente, _COLUMNAS, self.dominio):
            tipo = fila["tipo"].strip()
            if tipo == _TIPO_NODO:
                items.append(self._item_nodo(fila))
            elif tipo == _TIPO_ENLACE:
                items.append(self._item_enlace(fila))
            else:
                raise ValueError(f"tipo de fila no reconocido en {fuente!r}: {tipo!r}")
        return items

    def _item_nodo(self, fila: dict[str, str]) -> ItemComputo:
        return ItemComputo(
            codigo_partida=fila["codigo_partida"],
            descripcion=fila["descripcion"],
            unidad=fila["unidad"],
            cantidad=_decimal(fila, "cantidad"),
            origen_id=fila["id"],
            origen_tipo=OrigenTipo.CSV,
            dominio=Dominio.TELECOM,
            especificaciones=_parsear_especificaciones(fila.get("especificaciones")),
        )

    def _item_enlace(self, fila: dict[str, str]) -> ItemComputo:
        parametros = {
            "longitud_m": _decimal(fila, "longitud_m"),
            "reserva": _reserva(fila),
        }
        cantidad = evaluar_regla(_REGLA_LONGITUD_ENLACE, parametros)
        especificaciones = {
            "origen": fila["origen"],
            "destino": fila["destino"],
            **_parsear_especificaciones(fila.get("especificaciones")),
        }
        return ItemComputo(
            codigo_partida=fila["codigo_partida"],
            descripcion=fila["descripcion"],
            unidad=fila["unidad"],
            cantidad=cantidad,
            origen_id=fila["id"],
            origen_tipo=OrigenTipo.REGLA,
            dominio=Dominio.TELECOM,
            regla=_REGLA_LONGITUD_ENLACE,
            parametros=parametros,
            especificaciones=especificaciones,
        )
