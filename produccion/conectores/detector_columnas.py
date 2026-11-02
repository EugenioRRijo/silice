"""Detector de columnas de un reporte de bascula (Tarea 4.6; RT-S4-5 y RT-S4-6).

Los sinonimos de encabezado de `_SINONIMOS` son un SUPUESTO_DECLARADO (PLAN_FUENTES C-8): no hay
muestras reales (B-4) y solo se prueban con encabezados construidos. Con muestras reales se
ajustan; mientras tanto el usuario puede dar un mapeo explicito que manda sobre la deteccion (ver
`bascula.leer`).

Normalizacion de un encabezado: sin tildes, en minusculas, todo lo que no sea letra o digito pasa a
espacio. Para comparar con los sinonimos se quitan ademas las palabras de relleno (`de`, `del`, `n`,
`no`, `nro`, `numero`...) y las de unidad (`kg`, `t`, `ton`, `toneladas`...), de modo que
`N° Ticket`, `Numero de ticket` y `Ticket` son el mismo encabezado, y `Peso Neto (t)` es
`peso neto`.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from produccion.fuentes import FILAS_DE_ENCABEZADO

CAMPOS = ("ticket", "fecha", "placa", "cliente", "material", "bruto", "tara", "neto")

_PALABRAS_DE_RELLENO = frozenset({"de", "del", "la", "el", "n", "no", "nro", "num", "numero"})
_UNIDADES = {
    "kg": "kg",
    "kgs": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogramo": "kg",
    "kilogramos": "kg",
    "t": "t",
    "tn": "t",
    "ton": "t",
    "tons": "t",
    "tonelada": "t",
    "toneladas": "t",
}

# Sinonimos ya sin relleno ni unidad (SUPUESTO_DECLARADO, RT-S4-5).
_SINONIMOS: dict[str, tuple[str, ...]] = {
    "ticket": ("ticket", "boleto", "tique", "tiquete", "codigo ticket"),
    "fecha": ("fecha", "fecha pesaje", "fecha despacho", "fecha salida", "fecha hora", "dia"),
    "placa": ("placa", "placa camion", "placa vehiculo", "camion", "vehiculo"),
    "cliente": ("cliente", "comprador", "destinatario", "razon social", "nombre cliente"),
    "material": ("material", "producto", "agregado", "arido", "articulo", "descripcion"),
    "bruto": ("bruto", "peso bruto"),
    "tara": ("tara", "peso tara"),
    "neto": ("neto", "peso neto", "peso"),
}

_REQUERIDOS = ("ticket", "fecha", "material")
_CAMPOS_DE_PESO = ("bruto", "tara", "neto")


class MapeoNecesario(ValueError):  # noqa: N818 (nombre fijado por el plan)
    """No se reconocieron las columnas indispensables: el usuario debe indicar el mapeo."""

    def __init__(self, faltan: tuple[str, ...]) -> None:
        self.faltan = faltan
        super().__init__("Indique en qué columna están: " + ", ".join(faltan) + ".")


@dataclass(frozen=True, slots=True)
class MapeoColumnas:
    columnas: Mapping[str, int]  # campo -> indice 0-based
    fila_encabezado: int  # 0-based
    unidad_peso: str | None  # "kg" | "t" | None


def _palabras(texto: object) -> list[str]:
    """Encabezado normalizado en palabras: sin tildes, minusculas, sin signos."""
    if texto is None:
        return []
    sin_tildes = unicodedata.normalize("NFKD", str(texto))
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes.lower()).split()


def _clave(texto: object) -> str:
    """Encabezado sin relleno ni unidad, listo para buscar entre los sinonimos."""
    utiles = [p for p in _palabras(texto) if p not in _PALABRAS_DE_RELLENO and p not in _UNIDADES]
    return " ".join(utiles)


_CAMPO_POR_CLAVE: dict[str, str] = {}
for _campo, _claves in _SINONIMOS.items():
    for _sinonimo in _claves:
        _CAMPO_POR_CLAVE.setdefault(_clave(_sinonimo), _campo)


def _campos_de_la_fila(fila: Sequence[object]) -> dict[str, int]:
    """Campo -> indice de la primera columna de `fila` cuyo encabezado lo nombra."""
    hallados: dict[str, int] = {}
    for indice, celda in enumerate(fila):
        campo = _CAMPO_POR_CLAVE.get(_clave(celda))
        if campo is not None and campo not in hallados:
            hallados[campo] = indice
    return hallados


def unidad_del_encabezado(texto: object) -> str | None:
    """`"kg"` o `"t"` si el encabezado trae la unidad (`(kg)`, `kg`, `ton`, `(t)`, `toneladas`)."""
    unidades = {_UNIDADES[p] for p in _palabras(texto) if p in _UNIDADES}
    return unidades.pop() if len(unidades) == 1 else None


def unidad_de_los_pesos(
    fila_encabezado: Sequence[object], columnas: Mapping[str, int]
) -> str | None:
    """Unidad comun a los encabezados de las columnas de peso; `None` si no hay o se contradicen."""
    unidades = set()
    for campo in _CAMPOS_DE_PESO:
        indice = columnas.get(campo)
        if indice is not None and indice < len(fila_encabezado):
            unidad = unidad_del_encabezado(fila_encabezado[indice])
            if unidad is not None:
                unidades.add(unidad)
    return unidades.pop() if len(unidades) == 1 else None


def faltantes(columnas: Mapping[str, int]) -> tuple[str, ...]:
    """Campos indispensables que no estan en `columnas`, en el orden de `CAMPOS`.

    Se necesitan `ticket`, `fecha`, `material` y el peso: `neto`, o `bruto` y `tara` juntos. Si hay
    solo uno de `bruto`/`tara` y no hay `neto`, falta el otro; si no hay ningun peso, falta `neto`.
    """
    faltan = {campo for campo in _REQUERIDOS if campo not in columnas}
    if "neto" not in columnas:
        sin_bruto, sin_tara = "bruto" not in columnas, "tara" not in columnas
        if sin_bruto and sin_tara:
            faltan.add("neto")
        elif sin_bruto:
            faltan.add("bruto")
        elif sin_tara:
            faltan.add("tara")
    return tuple(campo for campo in CAMPOS if campo in faltan)


def mejor_encabezado(filas: Sequence[Sequence[object]]) -> tuple[int, dict[str, int]]:
    """Fila (0-based, entre las primeras `FILAS_DE_ENCABEZADO`) con mas campos reconocidos.

    Empata la primera. Si ninguna fila reconoce un campo devuelve `(0, {})`.
    """
    mejor: tuple[int, dict[str, int]] = (0, {})
    for indice, fila in enumerate(filas[:FILAS_DE_ENCABEZADO]):
        campos = _campos_de_la_fila(fila)
        if len(campos) > len(mejor[1]):
            mejor = (indice, campos)
    return mejor


def detectar(filas: Sequence[Sequence[object]]) -> MapeoColumnas:
    """Detecta las columnas; `MapeoNecesario` si faltan ticket, fecha, material o peso."""
    indice, columnas = mejor_encabezado(filas)
    faltan = faltantes(columnas)
    if faltan:
        raise MapeoNecesario(faltan)
    return MapeoColumnas(
        columnas=columnas,
        fila_encabezado=indice,
        unidad_peso=unidad_de_los_pesos(filas[indice], columnas),
    )
