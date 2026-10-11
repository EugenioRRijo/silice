"""Cantidades de electricidad (tomacorrientes e iluminación) derivadas del espacio (spec §7.3).

Cada partida sale de la geometría (`geometria.py`) y cita sus orígenes en `origen_id`, separados por
«;»: el tablero (`esp_fuentes:<id>`), los circuitos (`esp_circuitos:<id>`), los puntos
(`esp_puntos:<id>`) o los segmentos (`esp_segmentos:<clave>`). Todos son `ItemComputo` de origen
REGLA, dominio CIVIL (DA-SF-3: «instalaciones de la edificación»; la especialidad viaja en
`especificaciones["_especialidad"]`) y cantidades `Decimal` exactas, ordenadas por código.

Cómo se mide cada material (spec §7): el **conductor** va sobre la cadena del circuito (tablero →
punto 1 → punto 2 …, §6.4): `longitud de la cadena × conductores × (1 + desperdicio)`; la
**tubería** va sobre la unión de segmentos de las cadenas, la misma geometría (cada metro cuenta
una vez, y bajar a un punto y volver a subir es un solo segmento, D-15), sin desperdicio; cajas y
salidas, una por punto; protección, una por circuito.

Decisiones de trabajo (memoria `of001.md`, sección 5): D-13 desperdicio del conductor 10 %; D-12
tipo de tubería por defecto EMT; D-14 orden de la cadena por vecino más cercano; D-15 subidas y
bajadas coincidentes; D-16 diámetro de un circuito = el mayor de los declarados por sus puntos;
D-17 y D-18 sin desperdicio. Ninguna tiene fuente verificada: son supuestos declarados y así se
ven en la descripción de cada ítem. El máximo de puntos por circuito lo declara cada circuito; su
fuente candidata, el Código Eléctrico Nacional (FONDONORMA 200), no está verificada, así que R10 lo
trata como supuesto.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from decimal import Decimal

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante
from adapters.espacio.especialidades.comun import (
    CANALIZACION_POR_DEFECTO,
    CERO,
    D12,
    D17,
    D18,
    DESPERDICIO_CANALIZACION,
    DESPERDICIO_CONTEO,
    UNIDAD_LONGITUD,
    UNIDAD_PIEZA,
    UNIDAD_PUNTO,
    UNO,
    codigo_diametro,
    etiqueta,
    texto_diametro,
    valor_de,
)
from adapters.espacio.especialidades.comun import item as _item_comun
from adapters.espacio.geometria import (
    diametro_de_circuito,
    longitud_tramos,
    magnitud_diametro,
    tramos_de_circuito,
    unir_segmentos,
)
from adapters.espacio.modelo import (
    Circuito,
    Espacio,
    Especialidad,
    Punto,
    TipoFuente,
    TipoPunto,
    Tramo,
)
from adapters.espacio.origen import clave_esp
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo

# --- constantes (un solo lugar) ----------------------------------------------------------

_D13 = Constante("D-13", "Desperdicio del conductor eléctrico", Decimal("0.10"), SUPUESTO_DECLARADO)
#: R10 (spec §8.2): el máximo lo declara cada circuito. Fuente candidata: Código Eléctrico Nacional
#: (FONDONORMA 200), a verificar.
LIMITE_PUNTOS_POR_CIRCUITO = Constante(
    "R10-circuitos",
    "Puntos máximos por circuito (el declarado en cada circuito)",
    "declarado por circuito",
    SUPUESTO_DECLARADO,
)

CONSTANTES_ELECTRICIDAD: tuple[Constante, ...] = (
    _D13,
    D12,
    D17,
    D18,
    LIMITE_PUNTOS_POR_CIRCUITO,
)

DESPERDICIO_CONDUCTOR = Decimal(_D13.valor)

ESPECIALIDAD = Especialidad.ELECTRICIDAD.value


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
        ESPECIALIDAD,
    )


# --- utilidades -----------------------------------------------------------------------------


def _calibre(c: Circuito) -> str:
    """Calibre normalizado: mayúsculas y un solo espacio (`' 12  awg '` -> `'12 AWG'`)."""
    return " ".join(c.calibre.upper().split())


def _tableros(circuitos: Iterable[Circuito]) -> list[str]:
    return [clave_esp("esp_fuentes", c.tablero) for c in circuitos]


def _circuitos_de(espacio: Espacio, puntos: Iterable[Punto]) -> list[Circuito]:
    ids = {p.circuito_id for p in puntos if p.circuito_id is not None}
    return [c for c in espacio.circuitos if c.id in ids]


# --- derivación -----------------------------------------------------------------------------


def _conductores(
    espacio: Espacio, tramos_por_circuito: dict[str, tuple[Tramo, ...]]
) -> Iterator[ItemComputo]:
    grupos: dict[str, list[tuple[Circuito, Decimal]]] = defaultdict(list)
    for c in espacio.circuitos:
        tramos = tramos_por_circuito[c.id]
        if tramos:
            grupos[_calibre(c)].append((c, longitud_tramos(tramos) * sum(c.conductores)))
    for calibre, filas in grupos.items():
        metros = sum((m for _, m in filas), CERO)
        yield _item(
            f"EL-COND-{calibre.replace(' ', '-')}",
            f"Conductor {calibre}: cadena del circuito por sus conductores ({etiqueta(_D13)})",
            UNIDAD_LONGITUD,
            metros * (UNO + DESPERDICIO_CONDUCTOR),
            _tableros(c for c, _ in filas),
            (clave_esp("esp_circuitos", c.id) for c, _ in filas),
            "metros_de_conductor * (1 + desperdicio)",
            {"metros_de_conductor": metros, "desperdicio": DESPERDICIO_CONDUCTOR},
            {"calibre": calibre},
        )


def _datos_de_circuitos(espacio: Espacio) -> dict[str, tuple[int, str]]:
    """Por circuito: rango de la magnitud de su diámetro (-1 si no lo declara) y su tipo de
    canalización en mayúsculas ('' si ningún punto lo declara; el primero en orden alfabético)."""
    magnitudes: dict[str, object] = {}
    tipos: dict[str, str] = {}
    for c in espacio.circuitos:
        diametro = diametro_de_circuito(espacio, c)
        magnitudes[c.id] = magnitud_diametro(diametro) if diametro else -1
        ids = set(c.orden)
        declarados = sorted(
            p.espec["canalizacion"].strip().upper()
            for p in espacio.puntos
            if (p.circuito_id == c.id or p.id in ids) and p.espec.get("canalizacion", "").strip()
        )
        tipos[c.id] = declarados[0] if declarados else ""
    rango = {m: r for r, m in enumerate(sorted(set(magnitudes.values())))}
    return {c: (rango[m], tipos[c]) for c, m in magnitudes.items()}


def _tuberias(espacio: Espacio) -> Iterator[ItemComputo]:
    segmentos = []
    for f in espacio.fuentes:
        if f.especialidad is Especialidad.ELECTRICIDAD and f.tipo is TipoFuente.TABLERO:
            segmentos.extend(unir_segmentos(espacio, f.id))
    datos = _datos_de_circuitos(espacio)
    grupos: dict[tuple[str, str | None], list[tuple[object, bool]]] = defaultdict(list)
    for s in segmentos:
        tipo, por_defecto = valor_de(s.sirve, datos, CANALIZACION_POR_DEFECTO)
        grupos[(tipo, s.diametro)].append((s, por_defecto))
    for (tipo, diametro), con_flag in grupos.items():
        segs = [s for s, _ in con_flag]
        nota = f"; tipo por defecto: {D12.fuente}" if any(f for _, f in con_flag) else ""
        longitud = sum((s.longitud for s in segs), CERO)
        especificaciones = {"tipo": tipo}
        if diametro:
            especificaciones["diametro"] = f"{diametro} pulg"
        yield _item(
            f"EL-TUB-{tipo}-{codigo_diametro(diametro)}",
            f"Tubería {tipo} {texto_diametro(diametro)} eléctrica ({etiqueta(D18)}{nota})",
            UNIDAD_LONGITUD,
            longitud * (UNO + DESPERDICIO_CANALIZACION),
            (clave_esp("esp_fuentes", s.fuente_id) for s in segs),
            (clave_esp("esp_segmentos", s.clave) for s in segs),
            "longitud_unida * (1 + desperdicio)",
            {"longitud_unida": longitud, "desperdicio": DESPERDICIO_CANALIZACION},
            especificaciones,
        )


def _por_punto(espacio: Espacio, puntos: list[Punto]) -> Iterator[ItemComputo]:
    factor = UNO + DESPERDICIO_CONTEO
    tomas = [p for p in puntos if p.tipo is TipoPunto.TOMACORRIENTE]
    luces = [p for p in puntos if p.tipo is TipoPunto.ILUMINACION]
    for codigo, nombre, unidad, grupo in (
        ("EL-CAJA", "Caja de salida eléctrica", UNIDAD_PIEZA, puntos),
        ("EL-SALIDA-TOMA", "Salida de tomacorriente", UNIDAD_PUNTO, tomas),
        ("EL-SALIDA-ILUM", "Salida de iluminación", UNIDAD_PUNTO, luces),
    ):
        if not grupo:
            continue
        n = Decimal(len(grupo))
        yield _item(
            codigo,
            f"{nombre} ({etiqueta(D17)})",
            unidad,
            n * factor,
            _tableros(_circuitos_de(espacio, grupo)),
            (clave_esp("esp_puntos", p.id) for p in grupo),
            "puntos * (1 + desperdicio)",
            {"puntos": n, "desperdicio": DESPERDICIO_CONTEO},
            {},
        )


def _protecciones(espacio: Espacio) -> Iterator[ItemComputo]:
    if not espacio.circuitos:
        return
    n = Decimal(len(espacio.circuitos))
    yield _item(
        "EL-PROT",
        f"Protección por circuito ({etiqueta(D17)})",
        UNIDAD_PIEZA,
        n * (UNO + DESPERDICIO_CONTEO),
        _tableros(espacio.circuitos),
        (clave_esp("esp_circuitos", c.id) for c in espacio.circuitos),
        "circuitos * (1 + desperdicio)",
        {"circuitos": n, "desperdicio": DESPERDICIO_CONTEO},
        {},
    )


def derivar_electricidad(espacio: Espacio) -> list[ItemComputo]:
    """Partidas de electricidad (spec §7.3), ordenadas por código de partida."""
    puntos = [
        p
        for p in espacio.puntos
        if p.especialidad is Especialidad.ELECTRICIDAD
        and p.tipo in (TipoPunto.TOMACORRIENTE, TipoPunto.ILUMINACION)
    ]
    items: list[ItemComputo] = []
    # los tramos de cada circuito se calculan una sola vez
    tramos_por_circuito = {c.id: tramos_de_circuito(espacio, c) for c in espacio.circuitos}
    items.extend(_conductores(espacio, tramos_por_circuito))
    items.extend(_tuberias(espacio))
    items.extend(_por_punto(espacio, puntos))
    items.extend(_protecciones(espacio))
    return sorted(items, key=lambda i: i.codigo_partida)
