"""Cantidades de obra de los tramos viales (plan vial, Tarea 7).

Cada cantidad es un `ItemComputo` de origen REGLA: `regla` es un producto de parámetros con nombre
(`"longitud*ancho*espesor*densidad"`) y la cantidad se obtiene multiplicando esos mismos
parámetros, así que la expresión guardada y la cantidad no pueden divergir (regla R1).

Orden determinista: tramos en el orden recibido; dentro de cada tramo, las capas en su orden (n = 1,
2, …) y, en cada capa, área, volumen, masa, litros y transporte; después la demarcación, cada línea
con su largo en m y, tras él, su pintura en l (Tarea 16b).

**Pintura** (Tarea 16b, filas 51 y 63): cada línea da también la partida `pintura_demarcacion` en
l, con el mismo origen que la línea: largo pintado × `pintura_l_m`, que es el rendimiento por
defecto (`PINTURA_POR_DEFECTO_L_KM`, V-17, por km de línea de 10 cm) ÷ 1.000 × ancho ÷ 10 cm. El
modelo no trae el ancho de la línea, así que es el supuesto V-14 (10 cm) y va en la directiva
`_ancho_linea_cm`, la que lee VR5. Así llevar los tramos a la Hoja pone la pintura y VR5 la mide.

**Asfalto** (Tarea 16b, filas 58 y 63): si la capa de carpeta o de bacheo declara `asfalto_pct`,
la partida de su mezcla (la de t) lleva la directiva `_porcentaje_asfalto` con ese número; es el
que VR2 compara con la fórmula de trabajo de la planta.

**Partidas nuevas** (F5 vial, tarea 1; diseño 2026-11-03 §6.3), solo si el tramo declara su dato,
así un tramo de hoy deriva lo mismo que antes: la limpieza de la superficie (el área de un riego
con `limpieza`) va antes del riego; el transporte del fresado (volumen × `esponjamiento`) va tras
el fresado; cada línea con `captafaros` da ese número de unidades tras su pintura; la demarcación
de superficie da área de cada elemento × número (sin pintura: VR5 mide líneas). Con `medicion`, el
fresado se mide en m² (`fresado_area`) y la colocación de la carpeta en t
(`carpeta_colocacion_masa`, antes de la mezcla), cada variante con su código propio.

**Lo que el APU ya trae** (prueba de punta a punta del 2026-11-13, D2): un riego con
`suministro` no da la partida de su ligante (el APU del riego lo incluye) y una demarcación de tipo
`captafaros` da solo sus unidades, sin línea ni pintura.

**Transporte por banda** (F5 vial, tarea 2; diseño §5.3): si el tramo declara `transporte =
"banda"`, la mezcla de cada capa da `transporte_mezcla_banda` en t (las mismas toneladas de la
mezcla, con o sin distancia) en vez de la de t·km.

La especialidad y el tipo de capa o de línea van como directivas (`_especialidad`, `_capa`,
`_demarcacion`; convención DA-SF-3, `core/verification/directivas.es_directiva`): clasifican la
cantidad y R4 no las contrasta con el texto del APU.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from adapters.vial.constantes import (
    ANCHO_LINEA_REFERENCIA_CM,
    ANCHO_LINEA_SUPUESTO_CM,
    FRACCION_PINTADA_DISCONTINUA,
    PARTIDAS_VIALES,
    PINTURA_POR_DEFECTO_L_KM,
)
from adapters.vial.modelo import TRANSPORTE_BANDA, Capa, Tramo
from core.contracts import Dominio, ItemComputo, OrigenTipo

AREA = "longitud*ancho"
VOLUMEN = "longitud*ancho*espesor"
MASA = "longitud*ancho*espesor*densidad"
LITROS = "longitud*ancho*dosis"
TRANSPORTE = "longitud*ancho*espesor*densidad*distancia"
TRANSPORTE_FRESADO = "longitud*ancho*espesor*esponjamiento"
SUPERFICIE = "area_elemento*elementos"
CAPTAFAROS = "captafaros"
LINEA_CONTINUA = "longitud*lineas"
LINEA_DISCONTINUA = "longitud*lineas*fraccion_pintada"
PINTURA = "pintura_l_m"
#: Directiva con el porcentaje de asfalto de la capa en la partida de su mezcla (la lee VR2).
PORCENTAJE_ASFALTO = "_porcentaje_asfalto"

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

#: Con otra medición (`Capa.medicion`), la partida que reemplaza a la de siempre.
_VARIANTES: dict[tuple[str, str], tuple[str, str]] = {
    ("fresado", "m2"): ("fresado_area", AREA),
    ("carpeta", "t"): ("carpeta_colocacion_masa", MASA),
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
        ("esponjamiento", capa.esponjamiento),
    ):
        if valor is not None:
            valores[nombre] = valor
    origen_id = f"tramo:{tramo.id}:capa:{n}"
    especificaciones = {"_especialidad": "vial", "_capa": capa.tipo}
    de_la_mezcla = dict(especificaciones)
    if capa.asfalto_pct is not None:
        de_la_mezcla[PORCENTAJE_ASFALTO] = format(capa.asfalto_pct, "f")
    items = []
    if capa.limpieza:
        items.append(
            _item("limpieza_superficie", AREA, valores, tramo, origen_id, especificaciones)
        )
    for n_partida, (clave, regla) in enumerate(_PARTIDAS_POR_CAPA[capa.tipo]):
        if n_partida == 0 and capa.medicion is not None:
            clave, regla = _VARIANTES[(capa.tipo, capa.medicion)]
            items.append(_item(clave, regla, valores, tramo, origen_id, especificaciones))
            continue
        if regla == MASA and "densidad" not in valores:
            continue  # bacheo sin densidad: solo su volumen
        if regla == LITROS and capa.suministro:
            continue  # riego con suministro: el ligante va dentro del APU del riego
        espec = de_la_mezcla if regla == MASA else especificaciones
        items.append(_item(clave, regla, valores, tramo, origen_id, espec))
        if regla == MASA and tramo.transporte == TRANSPORTE_BANDA:
            items.append(
                _item("transporte_mezcla_banda", MASA, valores, tramo, origen_id, especificaciones)
            )
        elif regla == MASA and "distancia" in valores:
            items.append(
                _item("transporte_mezcla", TRANSPORTE, valores, tramo, origen_id, especificaciones)
            )
    if "esponjamiento" in valores:
        items.append(
            _item(
                "transporte_fresado",
                TRANSPORTE_FRESADO,
                valores,
                tramo,
                origen_id,
                especificaciones,
            )
        )
    return items


def _pintura_l_m() -> tuple[Decimal, str]:
    """Los litros por metro de línea pintada y el ancho supuesto de la línea, en cm (texto)."""
    ancho = Decimal(ANCHO_LINEA_SUPUESTO_CM.valor)
    por_km = (
        Decimal(PINTURA_POR_DEFECTO_L_KM.valor) * ancho / Decimal(ANCHO_LINEA_REFERENCIA_CM.valor)
    )
    return por_km / 1000, format(ancho.normalize(), "f")


def derivar_tramos(tramos: Sequence[Tramo]) -> list[ItemComputo]:
    """Las cantidades de obra de `tramos`, trazables a su tramo y a su capa o línea."""
    items: list[ItemComputo] = []
    fraccion = Decimal(FRACCION_PINTADA_DISCONTINUA.valor)
    con_coma = str(fraccion).replace(".", ",")  # se lee en es-VE (solo biblioteca estándar)
    nota_fraccion = f" (fracción pintada {con_coma}: {FRACCION_PINTADA_DISCONTINUA.fuente})"
    pintura_l_m, ancho_cm = _pintura_l_m()
    for tramo in tramos:
        for n, capa in enumerate(tramo.capas, start=1):
            items.extend(_items_de_capa(tramo, n, capa))
        for n, linea in enumerate(tramo.demarcacion, start=1):
            origen = f"tramo:{tramo.id}:demarcacion:{n}"
            especificaciones = {"_especialidad": "vial", "_demarcacion": linea.tipo}
            if linea.tipo == "superficie" and linea.area_m2 is not None:
                valores = {"area_elemento": linea.area_m2, "elementos": Decimal(linea.lineas)}
                items.append(
                    _item(
                        "demarcacion_superficie",
                        SUPERFICIE,
                        valores,
                        tramo,
                        origen,
                        especificaciones,
                    )
                )
                continue
            if linea.tipo == "captafaros" and linea.captafaros is not None:
                items.append(
                    _item(
                        "captafaros",
                        CAPTAFAROS,
                        {CAPTAFAROS: Decimal(linea.captafaros)},
                        tramo,
                        origen,
                        especificaciones,
                    )
                )
                continue
            clave, regla = _PARTIDA_DEMARCACION[linea.tipo]
            valores = {
                "longitud": tramo.longitud_m,
                "lineas": Decimal(linea.lineas),
                "fraccion_pintada": fraccion,
                PINTURA: pintura_l_m,
            }
            nota = nota_fraccion if linea.tipo == "discontinua" else ""
            items.append(_item(clave, regla, valores, tramo, origen, especificaciones, nota))
            items.append(
                _item(
                    "pintura_demarcacion",
                    f"{regla}*{PINTURA}",
                    valores,
                    tramo,
                    origen,
                    {**especificaciones, "_ancho_linea_cm": ancho_cm},
                    nota,
                )
            )
            if linea.captafaros is not None:
                items.append(
                    _item(
                        "captafaros",
                        CAPTAFAROS,
                        {CAPTAFAROS: Decimal(linea.captafaros)},
                        tramo,
                        origen,
                        especificaciones,
                    )
                )
    return items
