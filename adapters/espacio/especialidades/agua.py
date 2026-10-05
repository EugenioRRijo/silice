"""Cantidades de agua fría y drenaje derivadas del espacio (spec §7.1).

Cada partida sale de la geometría (`geometria.py`) y cita sus orígenes en `origen_id`, separados por
«;»: segmentos (`esp_segmentos:<clave>`), puntos (`esp_puntos:<id>`) o fuentes (`esp_fuentes:<id>`,
para los accesorios, que son nodos del árbol de la fuente). Todos son `ItemComputo` de origen REGLA,
dominio CIVIL (RS-2) y cantidades `Decimal` exactas, ordenadas por código de partida.

Decisiones de trabajo (bitácora SF, tarea 1.5): D-1 desperdicio de tubería 10 %; D-2 0 % en
accesorios, llaves, salidas y picado; D-4 empotrado por defecto en pared y piso; D-5 el diámetro de
un accesorio es el mayor de los segmentos que concurren; D-6 material PVC por defecto; D-7 la
superficie de un segmento empotrado se deduce de su geometría. Ninguna tiene fuente verificada:
son supuestos declarados y así se ven en la descripción de cada ítem.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from decimal import Decimal

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante, porcentaje
from adapters.espacio.geometria import (
    Accesorio,
    Segmento,
    contar_accesorios,
    magnitud_diametro,
    normalizar_diametro,
    unir_segmentos,
)
from adapters.espacio.modelo import (
    LLAVE_DE_PASO,
    TOLERANCIA,
    Espacio,
    Especialidad,
    Punto,
    TipoFuente,
    TipoPunto,
)
from adapters.espacio.origen import clave_esp
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo

# --- constantes (un solo lugar) ----------------------------------------------------------

_D1 = Constante("D-1", "Desperdicio de tubería de agua fría", Decimal("0.10"), SUPUESTO_DECLARADO)
_D1B = Constante("D-1b", "Desperdicio de tubería de drenaje", Decimal("0.10"), SUPUESTO_DECLARADO)
_D2 = Constante(
    "D-2",
    "Desperdicio de codos, tees, llaves, salidas y picado (conteo exacto)",
    Decimal("0"),
    SUPUESTO_DECLARADO,
)
_D6 = Constante("D-6", "Material de tubería por defecto", "PVC", SUPUESTO_DECLARADO)

CONSTANTES_AGUA: tuple[Constante, ...] = (_D1, _D1B, _D2, _D6)

DESPERDICIO_TUBERIA_AGUA_FRIA = Decimal(_D1.valor)
DESPERDICIO_TUBERIA_DRENAJE = Decimal(_D1B.valor)
DESPERDICIO_ACCESORIOS_Y_PICADO = Decimal(_D2.valor)
MATERIAL_POR_DEFECTO = str(_D6.valor)

UNIDAD_LONGITUD = "m"
UNIDAD_CONTEO = "u"
CERO = Decimal(0)
UNO = Decimal(1)


@dataclass(frozen=True, slots=True)
class _Sistema:
    prefijo: str
    nombre: str
    tipos_fuente: frozenset[TipoFuente]
    tipo_punto: TipoPunto
    desperdicio_tuberia: Constante
    salida: str
    con_llave: bool


_AGUA_FRIA = _Sistema(
    "AF",
    "agua fría",
    frozenset({TipoFuente.ACOMETIDA_AGUA, TipoFuente.MONTANTE_AGUA}),
    TipoPunto.AGUA_FRIA,
    _D1,
    "Salida de agua fría",
    True,
)
_DRENAJE = _Sistema(
    "DR",
    "drenaje",
    frozenset({TipoFuente.COLECTOR_DRENAJE}),
    TipoPunto.DRENAJE,
    _D1B,
    "Salida de drenaje",
    False,
)


# --- utilidades -----------------------------------------------------------------------------


def _referencias(refs: Iterable[str]) -> str:
    return ";".join(sorted(set(refs)))


def _codigo_diametro(diametro: str | None) -> str:
    return diametro.replace(" ", "-") if diametro else "SIN-DIAMETRO"


def _texto_diametro(diametro: str | None) -> str:
    return f'{diametro}"' if diametro else "sin diámetro declarado"


def _etiqueta(c: Constante) -> str:
    return f"desperdicio {porcentaje(Decimal(c.valor))}: {c.fuente}"


def _item(
    codigo: str,
    descripcion: str,
    unidad: str,
    cantidad: Decimal,
    refs: Iterable[str],
    regla: str,
    parametros: dict[str, Decimal],
    especificaciones: dict[str, str],
) -> ItemComputo:
    return ItemComputo(
        codigo_partida=codigo,
        descripcion=descripcion,
        unidad=unidad,
        cantidad=cantidad,
        origen_id=_referencias(refs),
        origen_tipo=OrigenTipo.REGLA,
        dominio=Dominio.CIVIL,
        regla=regla,
        parametros=parametros,
        especificaciones=especificaciones,
    )


def _material_de(segmento: Segmento, puntos: dict[str, Punto]) -> str:
    """Material declarado por el punto de mayor diámetro que sirve el segmento (empate: id menor);
    sin declaración, el material por defecto (D-6)."""
    servidos = [puntos[i] for i in segmento.sirve if i in puntos]

    def orden(p: Punto) -> tuple[Decimal | int, str]:
        d = normalizar_diametro(p.espec.get("diametro"))
        return (-magnitud_diametro(d) if d else 1, p.id)  # type: ignore[return-value]

    if servidos:
        material = min(servidos, key=orden).espec.get("material", "").strip()
        if material:
            return material.upper()
    return MATERIAL_POR_DEFECTO


def _superficie_empotrada(s: Segmento) -> str:
    """D-7: vertical = pared; horizontal a nivel del piso = piso; cualquier otro horizontal
    empotrado (un muro corrido o una losa) se cuenta como pared, que la spec no distingue."""
    if abs(s.a.x - s.b.x) <= TOLERANCIA and abs(s.a.y - s.b.y) <= TOLERANCIA:
        return "PARED"
    if abs(s.a.z) <= TOLERANCIA and abs(s.b.z) <= TOLERANCIA:
        return "PISO"
    return "PARED"


# --- derivación por sistema ------------------------------------------------------------------


def _tuberias(
    sistema: _Sistema, segmentos: list[Segmento], puntos: dict[str, Punto]
) -> Iterator[ItemComputo]:
    grupos: dict[tuple[str, str | None], list[Segmento]] = defaultdict(list)
    for s in segmentos:
        grupos[(_material_de(s, puntos), s.diametro)].append(s)
    desperdicio = Decimal(sistema.desperdicio_tuberia.valor)
    for (material, diametro), segs in grupos.items():
        longitud = sum((s.longitud for s in segs), CERO)
        especificaciones = {"material": material}
        if diametro:
            especificaciones["diametro"] = f"{diametro} pulg"
        yield _item(
            f"{sistema.prefijo}-TUB-{material}-{_codigo_diametro(diametro)}",
            f"Tubería de {sistema.nombre} {material} {_texto_diametro(diametro)} "
            f"({_etiqueta(sistema.desperdicio_tuberia)})",
            UNIDAD_LONGITUD,
            longitud * (UNO + desperdicio),
            (clave_esp("esp_segmentos", s.clave) for s in segs),
            "longitud_unida * (1 + desperdicio)",
            {"longitud_unida": longitud, "desperdicio": desperdicio},
            especificaciones,
        )


def _accesorios(sistema: _Sistema, segmentos: list[Segmento]) -> Iterator[ItemComputo]:
    grupos: dict[tuple[str, str | None], list[Accesorio]] = defaultdict(list)
    for a in contar_accesorios(segmentos):
        grupos[(a.tipo, a.diametro)].append(a)
    for (tipo, diametro), accs in grupos.items():
        conteo = Decimal(sum(a.cantidad for a in accs))
        nombre = "Codo" if tipo == "codo" else "Tee"
        yield _item(
            f"{sistema.prefijo}-{tipo.upper()}-{_codigo_diametro(diametro)}",
            f"{nombre} de {sistema.nombre} {_texto_diametro(diametro)} ({_etiqueta(_D2)})",
            UNIDAD_CONTEO,
            conteo * (UNO + DESPERDICIO_ACCESORIOS_Y_PICADO),
            (clave_esp("esp_fuentes", a.fuente_id) for a in accs),
            "conteo * (1 + desperdicio)",
            {"conteo": conteo, "desperdicio": DESPERDICIO_ACCESORIOS_Y_PICADO},
            {"diametro": f"{diametro} pulg"} if diametro else {},
        )


def _picado(sistema: _Sistema, segmentos: list[Segmento]) -> Iterator[ItemComputo]:
    grupos: dict[str, list[Segmento]] = defaultdict(list)
    for s in segmentos:
        if s.empotrado:
            grupos[_superficie_empotrada(s)].append(s)
    for superficie, segs in grupos.items():
        longitud = sum((s.longitud for s in segs), CERO)
        yield _item(
            f"{sistema.prefijo}-PICADO-{superficie}",
            f"Picado y resane de {superficie.lower()} para tubería de {sistema.nombre} "
            f"({_etiqueta(_D2)})",
            UNIDAD_LONGITUD,
            longitud * (UNO + DESPERDICIO_ACCESORIOS_Y_PICADO),
            (clave_esp("esp_segmentos", s.clave) for s in segs),
            "longitud_empotrada * (1 + desperdicio)",
            {"longitud_empotrada": longitud, "desperdicio": DESPERDICIO_ACCESORIOS_Y_PICADO},
            {},
        )


def _por_punto(sistema: _Sistema, puntos: list[Punto]) -> Iterator[ItemComputo]:
    factor = UNO + DESPERDICIO_ACCESORIOS_Y_PICADO
    con_llave = [p for p in puntos if p.espec.get("llave_de_paso") == LLAVE_DE_PASO]
    if sistema.con_llave and con_llave:
        n = Decimal(len(con_llave))
        yield _item(
            f"{sistema.prefijo}-LLAVE",
            f"Llave de paso de {sistema.nombre} ({_etiqueta(_D2)})",
            UNIDAD_CONTEO,
            n * factor,
            (clave_esp("esp_puntos", p.id) for p in con_llave),
            "puntos_con_llave * (1 + desperdicio)",
            {"puntos_con_llave": n, "desperdicio": DESPERDICIO_ACCESORIOS_Y_PICADO},
            {},
        )
    if puntos:
        n = Decimal(len(puntos))
        yield _item(
            f"{sistema.prefijo}-SALIDA",
            f"{sistema.salida} ({_etiqueta(_D2)})",
            UNIDAD_CONTEO,
            n * factor,
            (clave_esp("esp_puntos", p.id) for p in puntos),
            "puntos * (1 + desperdicio)",
            {"puntos": n, "desperdicio": DESPERDICIO_ACCESORIOS_Y_PICADO},
            {},
        )


def _derivar_sistema(espacio: Espacio, sistema: _Sistema) -> list[ItemComputo]:
    puntos = [
        p
        for p in espacio.puntos
        if p.especialidad is Especialidad.AGUA and p.tipo is sistema.tipo_punto
    ]
    por_id = {p.id: p for p in puntos}
    segmentos: list[Segmento] = []
    for f in espacio.fuentes:
        if f.especialidad is Especialidad.AGUA and f.tipo in sistema.tipos_fuente:
            segmentos.extend(unir_segmentos(espacio, f.id))
    items: list[ItemComputo] = []
    items.extend(_tuberias(sistema, segmentos, por_id))
    items.extend(_accesorios(sistema, segmentos))
    items.extend(_picado(sistema, segmentos))
    items.extend(_por_punto(sistema, puntos))
    return items


def derivar_agua(espacio: Espacio) -> list[ItemComputo]:
    """Partidas de agua fría y de drenaje (spec §7.1), ordenadas por código de partida."""
    items = _derivar_sistema(espacio, _AGUA_FRIA) + _derivar_sistema(espacio, _DRENAJE)
    return sorted(items, key=lambda i: i.codigo_partida)
