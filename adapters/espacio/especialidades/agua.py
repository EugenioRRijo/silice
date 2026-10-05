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

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante
from adapters.espacio.especialidades.comun import (
    CERO,
    UNIDAD_CONTEO,
    UNIDAD_LONGITUD,
    UNO,
    codigo_diametro,
    datos_de_valor,
    etiqueta,
    texto_diametro,
    valor_de,
)
from adapters.espacio.especialidades.comun import item as _item_comun
from adapters.espacio.geometria import (
    Accesorio,
    Segmento,
    contar_accesorios,
    unir_segmentos,
)
from adapters.espacio.modelo import (
    LLAVE_DE_PASO,
    TOLERANCIA,
    Espacio,
    Especialidad,
    Punto,
    SuperficieTramo,
    TipoFuente,
    TipoPunto,
)
from adapters.espacio.origen import clave_esp
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo

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

#: R10 (spec §8.2, §7.1): pendiente mínima del drenaje, como fracción (0,01 = 1 %), positiva si el
#: tramo desciende hacia el colector. Fuente candidata: Normas Sanitarias (Gaceta Oficial N.º 4.044
#: Extraordinario, 1988), a verificar; el valor es un supuesto declarado.
LIMITE_PENDIENTE_DRENAJE = Constante(
    "R10-pendiente", "Pendiente mínima del drenaje (m/m)", Decimal("0.01"), SUPUESTO_DECLARADO
)
LIMITES_AGUA: tuple[Constante, ...] = (LIMITE_PENDIENTE_DRENAJE,)

DESPERDICIO_TUBERIA_AGUA_FRIA = Decimal(_D1.valor)
DESPERDICIO_TUBERIA_DRENAJE = Decimal(_D1B.valor)
DESPERDICIO_ACCESORIOS_Y_PICADO = Decimal(_D2.valor)
MATERIAL_POR_DEFECTO = str(_D6.valor)


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


def _item(
    codigo: str,
    descripcion: str,
    unidad: str,
    cantidad: Decimal,
    principales: Iterable[str],
    secundarios: Iterable[str],
    regla: str,
    parametros: dict[str, Decimal],
    especificaciones: dict[str, str],
) -> ItemComputo:
    return _item_comun(
        codigo,
        descripcion,
        unidad,
        cantidad,
        principales,
        secundarios,
        regla,
        parametros,
        especificaciones,
        Dominio.CIVIL,
    )


def superficie_de_segmento(s: Segmento) -> str:
    """Superficie del picado de un segmento empotrado: `PARED` o `PISO` (spec §7.1 no prevé otra).

    Manda la superficie que declaran los tramos. Si discrepan (`None`), se deduce: vertical = pared;
    horizontal con z <= tolerancia en ambos extremos (incluye cotas negativas: pendiente o drenaje
    enterrado) = piso; cualquier otro horizontal = pared. Techo, plafón y bandeja empotrados se
    cuentan como pared (D-7)."""
    if s.superficie is not None:
        return "PISO" if s.superficie is SuperficieTramo.PISO else "PARED"
    if abs(s.a.x - s.b.x) <= TOLERANCIA and abs(s.a.y - s.b.y) <= TOLERANCIA:
        return "PARED"
    if s.a.z <= TOLERANCIA and s.b.z <= TOLERANCIA:
        return "PISO"
    return "PARED"


# --- derivación por sistema ------------------------------------------------------------------


def _tuberias(
    sistema: _Sistema, segmentos: list[Segmento], puntos: dict[str, Punto]
) -> Iterator[ItemComputo]:
    grupos: dict[tuple[str, str | None], list[tuple[Segmento, bool]]] = defaultdict(list)
    datos = datos_de_valor(puntos, "material")
    for s in segmentos:
        material, por_defecto = valor_de(s.sirve, datos, MATERIAL_POR_DEFECTO)
        grupos[(material, s.diametro)].append((s, por_defecto))
    desperdicio = Decimal(sistema.desperdicio_tuberia.valor)
    for (material, diametro), con_flag in grupos.items():
        segs = [s for s, _ in con_flag]
        nota = f"; material por defecto: {_D6.fuente}" if any(f for _, f in con_flag) else ""
        longitud = sum((s.longitud for s in segs), CERO)
        especificaciones = {"material": material}
        if diametro:
            especificaciones["diametro"] = f"{diametro} pulg"
        yield _item(
            f"{sistema.prefijo}-TUB-{material}-{codigo_diametro(diametro)}",
            f"Tubería de {sistema.nombre} {material} {texto_diametro(diametro)} "
            f"({etiqueta(sistema.desperdicio_tuberia)}{nota})",
            UNIDAD_LONGITUD,
            longitud * (UNO + desperdicio),
            (clave_esp("esp_fuentes", s.fuente_id) for s in segs),
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
            f"{sistema.prefijo}-{tipo.upper()}-{codigo_diametro(diametro)}",
            f"{nombre} de {sistema.nombre} {texto_diametro(diametro)} ({etiqueta(_D2)})",
            UNIDAD_CONTEO,
            conteo * (UNO + DESPERDICIO_ACCESORIOS_Y_PICADO),
            (clave_esp("esp_fuentes", a.fuente_id) for a in accs),
            (),
            "conteo * (1 + desperdicio)",
            {"conteo": conteo, "desperdicio": DESPERDICIO_ACCESORIOS_Y_PICADO},
            {"diametro": f"{diametro} pulg"} if diametro else {},
        )


def _picado(sistema: _Sistema, segmentos: list[Segmento]) -> Iterator[ItemComputo]:
    grupos: dict[str, list[Segmento]] = defaultdict(list)
    for s in segmentos:
        if s.empotrado:
            grupos[superficie_de_segmento(s)].append(s)
    for superficie, segs in grupos.items():
        longitud = sum((s.longitud for s in segs), CERO)
        yield _item(
            f"{sistema.prefijo}-PICADO-{superficie}",
            f"Picado y resane de {superficie.lower()} para tubería de {sistema.nombre} "
            f"({etiqueta(_D2)})",
            UNIDAD_LONGITUD,
            longitud * (UNO + DESPERDICIO_ACCESORIOS_Y_PICADO),
            (clave_esp("esp_fuentes", s.fuente_id) for s in segs),
            (clave_esp("esp_segmentos", s.clave) for s in segs),
            "longitud_empotrada * (1 + desperdicio)",
            {"longitud_empotrada": longitud, "desperdicio": DESPERDICIO_ACCESORIOS_Y_PICADO},
            {},
        )


def _fuentes_de(puntos: Iterable[Punto]) -> list[str]:
    return [clave_esp("esp_fuentes", p.fuente_id) for p in puntos if p.fuente_id is not None]


def _por_punto(sistema: _Sistema, puntos: list[Punto]) -> Iterator[ItemComputo]:
    factor = UNO + DESPERDICIO_ACCESORIOS_Y_PICADO
    con_llave = [p for p in puntos if p.espec.get("llave_de_paso") == LLAVE_DE_PASO]
    if sistema.con_llave and con_llave:
        n = Decimal(len(con_llave))
        yield _item(
            f"{sistema.prefijo}-LLAVE",
            f"Llave de paso de {sistema.nombre} ({etiqueta(_D2)})",
            UNIDAD_CONTEO,
            n * factor,
            _fuentes_de(con_llave),
            (clave_esp("esp_puntos", p.id) for p in con_llave),
            "puntos_con_llave * (1 + desperdicio)",
            {"puntos_con_llave": n, "desperdicio": DESPERDICIO_ACCESORIOS_Y_PICADO},
            {},
        )
    if puntos:
        n = Decimal(len(puntos))
        yield _item(
            f"{sistema.prefijo}-SALIDA",
            f"{sistema.salida} ({etiqueta(_D2)})",
            UNIDAD_CONTEO,
            n * factor,
            _fuentes_de(puntos),
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
