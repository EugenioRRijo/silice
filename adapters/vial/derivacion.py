"""Cantidades de obra de los tramos viales (plan vial, Tarea 7).

Cada cantidad es un `ItemComputo` de origen REGLA: `regla` es un producto de parámetros con nombre
(`"longitud*ancho*espesor*densidad"`) y la cantidad se obtiene multiplicando esos mismos
parámetros, así que la expresión guardada y la cantidad no pueden divergir (regla R1).

Orden determinista: tramos en el orden recibido; dentro de cada tramo, las capas en su orden (n = 1,
2, …) y, en cada capa, área, volumen, masa, litros y transporte; después la demarcación.

La especialidad y el tipo de capa o de línea van como directivas (`_especialidad`, `_capa`,
`_demarcacion`; convención DA-SF-3, `core/verification/directivas.es_directiva`): clasifican la
cantidad y R4 no las contrasta con el texto del APU.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from adapters.vial.constantes import FRACCION_PINTADA_DISCONTINUA, PARTIDAS_VIALES
from adapters.vial.modelo import Capa, Tramo
from core.contracts import Dominio, ItemComputo, OrigenTipo

AREA = "longitud*ancho"
VOLUMEN = "longitud*ancho*espesor"
MASA = "longitud*ancho*espesor*densidad"
LITROS = "longitud*ancho*dosis"
TRANSPORTE = "longitud*ancho*espesor*densidad*distancia"
LINEA_CONTINUA = "longitud*lineas"
LINEA_DISCONTINUA = "longitud*lineas*fraccion_pintada"

#: Por tipo de capa, las partidas que produce y la regla de cada una, en orden.
_PARTIDAS_POR_CAPA: dict[str, tuple[tuple[str, str], ...]] = {
    "fresado": (("fresado", VOLUMEN),),
    "base_granular": (("base_granular", VOLUMEN),),
    "subbase_granular": (("subbase_granular", VOLUMEN),),
    "imprimacion": (("imprimacion", AREA), ("imprimacion_ligante", LITROS)),
    "riego_adherencia": (("riego_adherencia", AREA), ("riego_adherencia_ligante", LITROS)),
    "carpeta": (("carpeta", AREA), ("carpeta_mezcla", MASA)),
    "bacheo": (("bacheo", VOLUMEN), ("bacheo_mezcla", MASA)),
}

_PARTIDA_DEMARCACION = {
    "continua": ("demarcacion_continua", LINEA_CONTINUA),
    "discontinua": ("demarcacion_discontinua", LINEA_DISCONTINUA),
}


def _producto(regla: str, parametros: dict[str, Decimal]) -> Decimal:
    cantidad = Decimal(1)
    for nombre in regla.split("*"):
        cantidad *= parametros[nombre]
    return cantidad


def _item(
    clave: str,
    regla: str,
    valores: dict[str, Decimal],
    tramo: Tramo,
    origen_id: str,
    especificaciones: dict[str, str],
    nota: str = "",
) -> ItemComputo:
    codigo, descripcion, unidad = PARTIDAS_VIALES[clave]
    parametros = {nombre: valores[nombre] for nombre in regla.split("*")}
    return ItemComputo(
        codigo_partida=codigo,
        descripcion=f"{descripcion}, tramo {tramo.id}{nota}",
        unidad=unidad,
        cantidad=_producto(regla, parametros),
        origen_id=origen_id,
        origen_tipo=OrigenTipo.REGLA,
        dominio=Dominio.CIVIL,
        regla=regla,
        parametros=parametros,
        especificaciones=especificaciones,
    )


def _items_de_capa(tramo: Tramo, n: int, capa: Capa) -> list[ItemComputo]:
    valores = {"longitud": tramo.longitud_m, "ancho": tramo.ancho_m}
    for nombre, valor in (
        ("espesor", capa.espesor_m),
        ("densidad", capa.densidad_t_m3),
        ("dosis", capa.dosis_l_m2),
        ("distancia", tramo.distancia_planta_km),
    ):
        if valor is not None:
            valores[nombre] = valor
    origen_id = f"tramo:{tramo.id}:capa:{n}"
    especificaciones = {"_especialidad": "vial", "_capa": capa.tipo}
    items = []
    for clave, regla in _PARTIDAS_POR_CAPA[capa.tipo]:
        if regla == MASA and "densidad" not in valores:
            continue  # bacheo sin densidad: solo su volumen
        items.append(_item(clave, regla, valores, tramo, origen_id, especificaciones))
        if regla == MASA and "distancia" in valores:
            items.append(
                _item("transporte_mezcla", TRANSPORTE, valores, tramo, origen_id, especificaciones)
            )
    return items


def derivar_tramos(tramos: Sequence[Tramo]) -> list[ItemComputo]:
    """Las cantidades de obra de `tramos`, trazables a su tramo y a su capa o línea."""
    items: list[ItemComputo] = []
    fraccion = Decimal(FRACCION_PINTADA_DISCONTINUA.valor)
    nota_fraccion = f" (fracción pintada {fraccion}: {FRACCION_PINTADA_DISCONTINUA.fuente})"
    for tramo in tramos:
        for n, capa in enumerate(tramo.capas, start=1):
            items.extend(_items_de_capa(tramo, n, capa))
        for n, linea in enumerate(tramo.demarcacion, start=1):
            clave, regla = _PARTIDA_DEMARCACION[linea.tipo]
            valores = {
                "longitud": tramo.longitud_m,
                "lineas": Decimal(linea.lineas),
                "fraccion_pintada": fraccion,
            }
            items.append(
                _item(
                    clave,
                    regla,
                    valores,
                    tramo,
                    f"tramo:{tramo.id}:demarcacion:{n}",
                    {"_especialidad": "vial", "_demarcacion": linea.tipo},
                    nota_fraccion if linea.tipo == "discontinua" else "",
                )
            )
    return items
