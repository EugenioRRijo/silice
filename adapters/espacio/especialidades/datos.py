"""Cantidades de datos (cableado estructurado) derivadas del espacio (spec §7.2).

Cada partida sale de la geometría (`geometria.py`) y cita sus orígenes en `origen_id`, separados por
«;»: el rack (`esp_fuentes:<id>`), los puntos (`esp_puntos:<id>`) o los segmentos
(`esp_segmentos:<clave>`). Todos son `ItemComputo` de origen REGLA, dominio TELECOM (DA-SF-3: los
datos son telecom; la especialidad viaja en `especificaciones["_especialidad"]`) y cantidades
`Decimal` exactas, ordenadas por código de partida.

Cómo se mide cada material (spec §7): el **cable** va por recorrido (cada punto lleva su cable hasta
el rack): `(longitud del recorrido + holgura en rack + holgura en punto) × (1 + reserva)`; la
**canalización** va sobre la unión de segmentos (cada metro cuenta una vez) y no lleva desperdicio;
cajas, *face plates*, *jacks* y certificación, uno por punto.

Decisiones de trabajo (memoria `of001.md`, sección 5): D-8 holgura en el rack 2,0 m; D-9 holgura en
el punto 0,5 m; D-10 reserva del cable 10 %; D-11 categoría por defecto cat 6; D-12 tipo de
canalización por defecto EMT; D-17 y D-18 sin desperdicio. Ninguna tiene fuente verificada (la cita
ANSI/TIA-568 está pendiente en `docs/tesis/referencias.md`): son supuestos declarados y así se ven
en la descripción de cada ítem. El enlace de R10 es el recorrido más las dos holguras, sin la
reserva (D-19): la reserva es de compra, no longitud física.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from decimal import Decimal

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante, porcentaje
from adapters.espacio.especialidades.comun import (
    CERO,
    UNIDAD_LONGITUD,
    UNIDAD_PIEZA,
    UNIDAD_PUNTO,
    UNO,
    codigo_diametro,
    datos_de_valor,
    etiqueta,
    texto_diametro,
    valor_de,
)
from adapters.espacio.especialidades.comun import item as _item_comun
from adapters.espacio.geometria import longitud_tramos, tramos_de, unir_segmentos
from adapters.espacio.modelo import Espacio, Especialidad, Punto, TipoFuente, TipoPunto
from adapters.espacio.origen import clave_esp
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo

# --- constantes (un solo lugar) ----------------------------------------------------------

_D8 = Constante(
    "D-8", "Holgura de cable en el rack (m por enlace)", Decimal("2.0"), SUPUESTO_DECLARADO
)
_D9 = Constante(
    "D-9", "Holgura de cable en el punto (m por enlace)", Decimal("0.5"), SUPUESTO_DECLARADO
)
_D10 = Constante("D-10", "Reserva del cable de datos", Decimal("0.10"), SUPUESTO_DECLARADO)
_D11 = Constante("D-11", "Categoría de cable por defecto", "cat 6", SUPUESTO_DECLARADO)
_D12 = Constante("D-12", "Tipo de canalización por defecto", "EMT", SUPUESTO_DECLARADO)
_D17 = Constante(
    "D-17",
    "Desperdicio de cajas, face plates, jacks y certificación (conteo exacto)",
    Decimal("0"),
    SUPUESTO_DECLARADO,
)
_D18 = Constante(
    "D-18", "Desperdicio de la canalización de datos", Decimal("0"), SUPUESTO_DECLARADO
)
#: R10 (spec §8.2): enlace permanente máximo. Fuente candidata ANSI/TIA-568, a verificar.
LIMITE_ENLACE = Constante(
    "R10-datos", "Enlace permanente máximo (m)", Decimal("90"), SUPUESTO_DECLARADO
)

CONSTANTES_DATOS: tuple[Constante, ...] = (_D8, _D9, _D10, _D11, _D12, _D17, _D18, LIMITE_ENLACE)

HOLGURA_RACK = Decimal(_D8.valor)
HOLGURA_PUNTO = Decimal(_D9.valor)
RESERVA_CABLE = Decimal(_D10.valor)
CATEGORIA_POR_DEFECTO = str(_D11.valor)
CANALIZACION_POR_DEFECTO = str(_D12.valor)
DESPERDICIO_CONTEO = Decimal(_D17.valor)
DESPERDICIO_CANALIZACION = Decimal(_D18.valor)

ESPECIALIDAD = Especialidad.DATOS.value


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
        Dominio.TELECOM,
        ESPECIALIDAD,
    )


# --- utilidades -----------------------------------------------------------------------------


def _es_de_datos(p: Punto) -> bool:
    return p.especialidad is Especialidad.DATOS and p.tipo is TipoPunto.DATOS


def _categoria(p: Punto) -> tuple[str, bool]:
    """Categoría normalizada (minúsculas, un solo espacio) y si es la de por defecto (D-11)."""
    declarada = " ".join(p.espec.get("categoria", "").lower().split())
    if declarada:
        return declarada, False
    return CATEGORIA_POR_DEFECTO, True


def _recorrido(espacio: Espacio, punto: Punto) -> Decimal | None:
    tramos = tramos_de(espacio, punto)
    return longitud_tramos(tramos) if tramos else None


def longitud_enlace(espacio: Espacio, punto: Punto) -> Decimal | None:
    """Longitud del enlace de un punto de datos: recorrido más holguras (D-19), sin la reserva.

    `None` si el punto no es de datos o no tiene recorrido (sin fuente: no se inventa uno). Es la
    cifra que R10 compara contra `LIMITE_ENLACE`."""
    if not _es_de_datos(punto):
        return None
    longitud = _recorrido(espacio, punto)
    return None if longitud is None else longitud + HOLGURA_RACK + HOLGURA_PUNTO


def _n(valor: Decimal) -> str:
    return format(valor.normalize(), "f").replace(".", ",")


def _fuentes_de(puntos: Iterable[Punto]) -> list[str]:
    return [clave_esp("esp_fuentes", p.fuente_id) for p in puntos if p.fuente_id is not None]


# --- derivación -----------------------------------------------------------------------------


def _cables(espacio: Espacio, puntos: list[Punto]) -> Iterator[ItemComputo]:
    grupos: dict[str, list[tuple[Punto, Decimal, bool]]] = defaultdict(list)
    for p in puntos:
        longitud = _recorrido(espacio, p)
        if longitud is None:
            continue  # sin recorrido no hay cable: el punto sigue contando en cajas y jacks
        categoria, por_defecto = _categoria(p)
        grupos[categoria].append((p, longitud, por_defecto))
    holgura = HOLGURA_RACK + HOLGURA_PUNTO
    for categoria, filas in grupos.items():
        recorridos = sum((longitud for _, longitud, _ in filas), CERO)
        enlaces = Decimal(len(filas))
        nota = f"; categoría por defecto: {_D11.fuente}" if any(d for _, _, d in filas) else ""
        yield _item(
            f"DT-UTP-{categoria.upper().replace(' ', '-')}",
            f"Cable UTP {categoria} de datos hasta el rack (holgura en rack {_n(HOLGURA_RACK)} m y "
            f"en punto {_n(HOLGURA_PUNTO)} m, reserva {porcentaje(RESERVA_CABLE)}: "
            f"{_D10.fuente}{nota})",
            UNIDAD_LONGITUD,
            (recorridos + enlaces * holgura) * (UNO + RESERVA_CABLE),
            _fuentes_de(p for p, _, _ in filas),
            (clave_esp("esp_puntos", p.id) for p, _, _ in filas),
            "(longitud_recorridos + enlaces * (holgura_rack + holgura_punto)) * (1 + reserva)",
            {
                "longitud_recorridos": recorridos,
                "enlaces": enlaces,
                "holgura_rack": HOLGURA_RACK,
                "holgura_punto": HOLGURA_PUNTO,
                "reserva": RESERVA_CABLE,
            },
            {"categoria": categoria},
        )


def _canalizacion(espacio: Espacio, puntos: list[Punto]) -> Iterator[ItemComputo]:
    segmentos = []
    for f in espacio.fuentes:
        if f.especialidad is Especialidad.DATOS and f.tipo is TipoFuente.RACK:
            segmentos.extend(unir_segmentos(espacio, f.id))
    datos = datos_de_valor({p.id: p for p in puntos}, "canalizacion")
    grupos: dict[tuple[str, str | None], list[tuple[object, bool]]] = defaultdict(list)
    for s in segmentos:
        tipo, por_defecto = valor_de(s.sirve, datos, CANALIZACION_POR_DEFECTO)
        grupos[(tipo, s.diametro)].append((s, por_defecto))
    for (tipo, diametro), con_flag in grupos.items():
        segs = [s for s, _ in con_flag]
        nota = f"; tipo por defecto: {_D12.fuente}" if any(f for _, f in con_flag) else ""
        longitud = sum((s.longitud for s in segs), CERO)
        especificaciones = {"tipo": tipo}
        if diametro:
            especificaciones["diametro"] = f"{diametro} pulg"
        yield _item(
            f"DT-CAN-{tipo}-{codigo_diametro(diametro)}",
            f"Canalización {tipo} {texto_diametro(diametro)} de datos ({etiqueta(_D18)}{nota})",
            UNIDAD_LONGITUD,
            longitud * (UNO + DESPERDICIO_CANALIZACION),
            (clave_esp("esp_fuentes", s.fuente_id) for s in segs),
            (clave_esp("esp_segmentos", s.clave) for s in segs),
            "longitud_unida * (1 + desperdicio)",
            {"longitud_unida": longitud, "desperdicio": DESPERDICIO_CANALIZACION},
            especificaciones,
        )


def _por_punto(puntos: list[Punto]) -> Iterator[ItemComputo]:
    if not puntos:
        return
    n = Decimal(len(puntos))
    for codigo, nombre, unidad in (
        ("DT-CAJA", "Caja para salida de datos", UNIDAD_PIEZA),
        ("DT-FACEPLATE", "Face plate de salida de datos", UNIDAD_PIEZA),
        ("DT-JACK", "Jack RJ45 de salida de datos", UNIDAD_PIEZA),
        ("DT-CERT", "Certificación de enlace permanente", UNIDAD_PUNTO),
    ):
        yield _item(
            codigo,
            f"{nombre} ({etiqueta(_D17)})",
            unidad,
            n * (UNO + DESPERDICIO_CONTEO),
            _fuentes_de(puntos),
            (clave_esp("esp_puntos", p.id) for p in puntos),
            "puntos * (1 + desperdicio)",
            {"puntos": n, "desperdicio": DESPERDICIO_CONTEO},
            {},
        )


def derivar_datos(espacio: Espacio) -> list[ItemComputo]:
    """Partidas de datos (spec §7.2), ordenadas por código de partida."""
    puntos = [p for p in espacio.puntos if _es_de_datos(p)]
    items: list[ItemComputo] = []
    items.extend(_cables(espacio, puntos))
    items.extend(_canalizacion(espacio, puntos))
    items.extend(_por_punto(puntos))
    return sorted(items, key=lambda i: i.codigo_partida)
