"""Geometría de la hoja de metrajes (spec del sprint final, §6.4 y §6.5).

Todo en `Decimal` (NORMAS.md §2.3), sin dependencias nuevas y sin tocar `core/`:

* `recorrido_propuesto`: el camino que se propone para un punto (§6.4). Un punto sin fuente no tiene
  recorrido; los tramos de largo cero se omiten (FR-2).
* `unir_segmentos`: los recorridos de una misma fuente forman un árbol; la unión parte los solapes
  colineales (totales y parciales) en los nodos de toda la fuente y une los segmentos coincidentes a
  0,001 m, de modo que la tubería compartida no se cuenta dos veces (FR-3).
* `clave_segmento`: `fuente|extremo menor|extremo mayor`, cada coordenada con tres decimales; es la
  clave de las sobrescrituras del modelo.
* `contar_accesorios`: codos y tees por grado de nodo y colinealidad (§6.5).
* `analizar`: longitudes por diámetro y por superficie (empotrado o expuesto), accesorios y cajas.

Supuestos declarados (memoria `tests/fixtures/memorias/bano_of001.md`, D-4 y D-5): un tramo de pared
se cuenta empotrado y los demás expuestos cuando el tramo no lo declara; el diámetro de un accesorio
es el mayor de los segmentos que concurren. Un conflicto de empotrado entre tramos solapados, sin
sobrescritura, cuenta como expuesto y queda marcado en `Segmento.conflicto_empotrado` (R9).
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from fractions import Fraction

from adapters.espacio.modelo import (
    TOLERANCIA,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    Punto,
    SuperficieTramo,
    TipoPunto,
    Tramo,
)

CERO = Decimal(0)
MILIMETRO = Decimal("0.001")
SIN_DIAMETRO = "sin_diametro"

Clave3 = tuple[Decimal, Decimal, Decimal]

#: Superficies cuyo tramo va empotrado si nadie lo declara (decisión D-4, tarea 1.5): el drenaje
#: corre enterrado en el piso igual que la bajante en la pared; techo, plafón y bandeja, expuestos.
_EMPOTRADAS = frozenset({SuperficieTramo.PARED, SuperficieTramo.PISO})


# --- utilidades --------------------------------------------------------------------------


def _redondear(v: Decimal) -> Decimal:
    q = v.quantize(MILIMETRO, rounding=ROUND_HALF_EVEN)
    return Decimal("0.000") if q == 0 else q  # sin «-0.000»


def _nodo(p: Coord) -> Clave3:
    return (_redondear(p.x), _redondear(p.y), _redondear(p.z))


def _texto(k: Clave3) -> str:
    return ",".join(f"{v:.3f}" for v in k)


def clave_segmento(fuente_id: str, a: Coord, b: Coord) -> str:
    """Clave de un segmento (§6.5): fuente y extremos a 0,001 m, el menor primero (x, y, z)."""
    ka, kb = sorted((_nodo(a), _nodo(b)))
    return f"{fuente_id}|{_texto(ka)}|{_texto(kb)}"


def normalizar_diametro(valor: str | None) -> str | None:
    """`'3/4"'` -> `'3/4'`. Vacío o ausente -> None."""
    if valor is None:
        return None
    limpio = valor.strip().replace('"', "").replace("″", "").replace("''", "").strip()
    return limpio or None


def _magnitud_diametro(valor: str) -> Fraction:
    try:
        return sum((Fraction(t) for t in valor.split()), Fraction(0))
    except (ValueError, ZeroDivisionError):
        return Fraction(-1)


#: Magnitud de un diámetro normalizado (`'1 1/2'` -> 3/2), para elegir «el mayor» (D-5).
magnitud_diametro = _magnitud_diametro


def longitud_tramos(tramos: Iterable[Tramo]) -> Decimal:
    return sum((t.longitud for t in tramos), CERO)


def _vec(a: Coord, b: Coord) -> tuple[Decimal, Decimal, Decimal]:
    return (b.x - a.x, b.y - a.y, b.z - a.z)


def _punto_escalar(u: tuple[Decimal, ...], v: tuple[Decimal, ...]) -> Decimal:
    return sum((p * q for p, q in zip(u, v, strict=True)), CERO)


def _cruz(u: tuple[Decimal, ...], v: tuple[Decimal, ...]) -> tuple[Decimal, Decimal, Decimal]:
    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )


def _norma(u: tuple[Decimal, ...]) -> Decimal:
    return _punto_escalar(u, u).sqrt()


# --- recorrido propuesto (§6.4) ----------------------------------------------------------


def _tramos_desde_vertices(
    vertices: list[tuple[Coord, SuperficieTramo]],
) -> tuple[Tramo, ...]:
    """Tramos entre vértices consecutivos; los de largo cero (a 0,001 m) se omiten."""
    tramos: list[Tramo] = []
    for (a, _), (b, superficie) in zip(vertices, vertices[1:], strict=False):
        if _nodo(a) == _nodo(b):
            continue
        tramos.append(
            Tramo(
                orden=len(tramos) + 1,
                superficie=superficie,
                vertices=(a, b),
                empotrado=superficie in _EMPOTRADAS,
            )
        )
    return tuple(tramos)


def recorrido_propuesto(espacio: Espacio, punto: Punto) -> tuple[Tramo, ...]:
    """Recorrido que propone el §6.4 para un punto; `()` si no tiene fuente o no es de este tipo.

    Agua fría y datos: de la fuente sube al techo, recorre en x y luego en y, y baja por la pared
    hasta la altura del punto. Drenaje: del punto baja al piso y recorre en x y luego en y por el
    piso hasta el colector, sin pendiente (la pendiente y R10 son de la tarea 1.5). La electricidad
    es por circuito (tarea 2.1) y aquí devuelve `()`.
    """
    if punto.fuente_id is None:
        return ()
    fuente = next((f for f in espacio.fuentes if f.id == punto.fuente_id), None)
    if fuente is None:
        return ()
    ambiente = next((a for a in espacio.ambientes if a.id == punto.ambiente_id), None)
    p, f = punto.posicion, fuente.posicion
    en_techo, en_pared, en_piso = (
        SuperficieTramo.TECHO,
        SuperficieTramo.PARED,
        SuperficieTramo.PISO,
    )
    if punto.tipo in (TipoPunto.AGUA_FRIA, TipoPunto.DATOS):
        if ambiente is None:
            return ()
        techo = ambiente.alto
        return _tramos_desde_vertices(
            [
                (f, en_pared),
                (Coord(f.x, f.y, techo), en_pared),
                (Coord(p.x, f.y, techo), en_techo),
                (Coord(p.x, p.y, techo), en_techo),
                (p, en_pared),
            ]
        )
    if punto.tipo is TipoPunto.DRENAJE:
        return _tramos_desde_vertices(
            [
                (p, en_pared),
                (Coord(p.x, p.y, CERO), en_pared),
                (Coord(f.x, p.y, CERO), en_piso),
                (Coord(f.x, f.y, CERO), en_piso),
            ]
        )
    return ()


def tramos_de(espacio: Espacio, punto: Punto) -> tuple[Tramo, ...]:
    """Tramos de un punto: los del recorrido con tramos (declarado, o propuesto con tramos
    poblados, que se trata como declarado) si existe; si no, el propuesto."""
    for r in espacio.recorridos:
        if r.punto_id == punto.id and r.tramos:
            return r.tramos
    return recorrido_propuesto(espacio, punto)


# --- unión de segmentos (§6.5) -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Segmento:
    clave: str
    fuente_id: str
    a: Coord
    b: Coord
    longitud: Decimal
    sirve: tuple[str, ...]
    diametro: str | None
    empotrado: bool
    conflicto_empotrado: bool = False


@dataclass(frozen=True, slots=True)
class Accesorio:
    tipo: str  # "codo" o "tee"
    fuente_id: str
    nodo: Coord
    diametro: str | None
    cantidad: int = 1


@dataclass(frozen=True, slots=True)
class _Pieza:
    a: Coord
    b: Coord
    sirve: str
    diametro: str | None
    empotrado: bool


def _empotrado_de(t: Tramo) -> bool:
    if t.empotrado is not None:
        return t.empotrado
    return t.superficie in _EMPOTRADAS


def _piezas_de_fuente(espacio: Espacio, fuente: Fuente) -> list[_Pieza]:
    piezas: list[_Pieza] = []

    def agregar(tramos: Iterable[Tramo], sirve: str, diametro: str | None) -> None:
        for t in tramos:
            for a, b in zip(t.vertices, t.vertices[1:], strict=False):
                if _nodo(a) != _nodo(b):
                    piezas.append(_Pieza(a, b, sirve, diametro, _empotrado_de(t)))

    for p in espacio.puntos:
        if p.fuente_id == fuente.id:
            agregar(tramos_de(espacio, p), p.id, normalizar_diametro(p.espec.get("diametro")))
    circuitos = {c.id for c in espacio.circuitos if c.tablero == fuente.id}
    for r in espacio.recorridos:
        if r.circuito_id in circuitos:
            agregar(r.tramos, r.circuito_id, None)
    return piezas


def _agrupar_nodos(coords: Iterable[Coord]) -> dict[Coord, Coord]:
    """Une por vecindad (single-linkage, distancia <= TOLERANCIA) las coordenadas de los extremos.

    Devuelve coordenada -> representante, que es la mínima lexicográfica (x, y, z) del grupo: no
    depende del orden de entrada ni de los ids. Es la única tolerancia de la unión y del corte.

    Límite conocido del single-linkage: una cadena de extremos, cada uno a 0,001 m o menos del
    siguiente, colapsa en un solo nodo aunque sus extremos queden a más de 0,001 m entre sí. No es
    un caso realista (exigiría extremos separados por menos de un milímetro en hilera).
    """
    unicas = sorted(set(coords), key=lambda c: (c.x, c.y, c.z))
    padre = list(range(len(unicas)))

    def raiz(i: int) -> int:
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    tol2 = TOLERANCIA * TOLERANCIA
    for i, a in enumerate(unicas):
        for j in range(i + 1, len(unicas)):
            b = unicas[j]
            if b.x - a.x > TOLERANCIA:
                break  # ordenadas por x: ninguna posterior está a menos de la tolerancia
            dx, dy, dz = b.x - a.x, b.y - a.y, b.z - a.z
            if dx * dx + dy * dy + dz * dz <= tol2:
                ri, rj = raiz(i), raiz(j)
                if ri != rj:
                    padre[max(ri, rj)] = min(ri, rj)  # la raíz es la mínima lexicográfica
    return {c: unicas[raiz(i)] for i, c in enumerate(unicas)}


class _IndiceNodos:
    """Nodos ordenados por x para probar en cada pieza solo los que caen en su caja envolvente
    (con margen TOLERANCIA); el resultado es el mismo que probar todos, sin recorrerlos todos."""

    def __init__(self, nodos: list[Coord]) -> None:
        self.todos = nodos  # ordenados por (x, y, z)
        self._xs = [n.x for n in nodos]

    def cercanos(self, a: Coord, b: Coord) -> list[Coord]:
        t = TOLERANCIA
        x0, x1 = min(a.x, b.x) - t, max(a.x, b.x) + t
        y0, y1 = min(a.y, b.y) - t, max(a.y, b.y) + t
        z0, z1 = min(a.z, b.z) - t, max(a.z, b.z) + t
        banda = self.todos[bisect_left(self._xs, x0) : bisect_right(self._xs, x1)]
        return [n for n in banda if y0 <= n.y <= y1 and z0 <= n.z <= z1]


def _segmentos_de_fuente(espacio: Espacio, fuente: Fuente) -> tuple[list[_Pieza], list[Segmento]]:
    piezas = _piezas_de_fuente(espacio, fuente)
    if not piezas:
        return [], []
    rep = _agrupar_nodos(c for pz in piezas for c in (pz.a, pz.b))
    indice = _IndiceNodos(sorted(set(rep.values()), key=lambda c: (c.x, c.y, c.z)))

    acumulado: dict[tuple[Coord, Coord], dict] = {}
    for pz in piezas:
        a, b = rep[pz.a], rep[pz.b]
        if a == b:
            continue  # largo cero tras unir los nodos vecinos
        d = _vec(a, b)
        largo2 = _punto_escalar(d, d)
        largo = a.distancia(b)
        cortes: list[tuple[Decimal, Coord]] = []
        for n in indice.cercanos(a, b):
            if n in (a, b):
                continue
            t = _punto_escalar(_vec(a, n), d) / largo2
            if not (0 < t < 1):
                continue
            pie = Coord(a.x + t * d[0], a.y + t * d[1], a.z + t * d[2])
            if n.distancia(pie) <= TOLERANCIA:
                cortes.append((t, n))
        # las longitudes se miden sobre el segmento original (t * largo): partirlo en un nodo
        # que se desvía menos de la tolerancia no lo dobla ni lo alarga
        cortes.sort(key=lambda tn: (tn[0], tn[1].x, tn[1].y, tn[1].z))
        ts = [Decimal(0), *(t for t, _ in cortes), Decimal(1)]
        cadena = [a, *(n for _, n in cortes), b]
        for (n1, n2), (t1, t2) in zip(
            zip(cadena, cadena[1:], strict=False), zip(ts, ts[1:], strict=False), strict=False
        ):
            llave = (n1, n2) if (n1.x, n1.y, n1.z) <= (n2.x, n2.y, n2.z) else (n2, n1)
            reg = acumulado.setdefault(
                llave, {"sirve": set(), "diametros": [], "empotrados": set(), "largo": CERO}
            )
            reg["sirve"].add(pz.sirve)
            if pz.diametro is not None:
                reg["diametros"].append(pz.diametro)
            reg["empotrados"].add(pz.empotrado)
            reg["largo"] = max(reg["largo"], (t2 - t1) * largo)

    sobre = {s.clave: s for s in espacio.sobrescrituras}
    segmentos: list[Segmento] = []
    for (a, b), reg in acumulado.items():
        clave = clave_segmento(fuente.id, a, b)
        diametro = max(reg["diametros"], key=_magnitud_diametro) if reg["diametros"] else None
        conflicto = len(reg["empotrados"]) > 1
        empotrado = reg["empotrados"] == {True}
        s = sobre.get(clave)
        if s is not None:
            if s.diametro is not None:
                diametro = normalizar_diametro(s.diametro)
            if s.empotrado is not None:
                empotrado, conflicto = s.empotrado, False
        segmentos.append(
            Segmento(
                clave=clave,
                fuente_id=fuente.id,
                a=a,
                b=b,
                longitud=reg["largo"],
                sirve=tuple(sorted(reg["sirve"])),
                diametro=diametro,
                empotrado=empotrado,
                conflicto_empotrado=conflicto,
            )
        )
    segmentos.sort(key=lambda s: s.clave)
    return piezas, segmentos


def _fuentes(espacio: Espacio, fuente_id: str | None) -> list[Fuente]:
    return [f for f in espacio.fuentes if fuente_id is None or f.id == fuente_id]


def unir_segmentos(espacio: Espacio, fuente_id: str | None = None) -> tuple[Segmento, ...]:
    """Segmentos únicos (solapes partidos y unidos) de una fuente o de todas."""
    segmentos: list[Segmento] = []
    for f in _fuentes(espacio, fuente_id):
        segmentos.extend(_segmentos_de_fuente(espacio, f)[1])
    return tuple(sorted(segmentos, key=lambda s: s.clave))


def sobrescrituras_huerfanas(espacio: Espacio) -> tuple[str, ...]:
    """Claves de sobrescritura que ya no corresponden a ningún segmento (R9)."""
    vigentes = {s.clave for s in unir_segmentos(espacio)}
    return tuple(s.clave for s in espacio.sobrescrituras if s.clave not in vigentes)


# --- accesorios (§6.5) -------------------------------------------------------------------


def contar_accesorios(segmentos: Iterable[Segmento]) -> tuple[Accesorio, ...]:
    """Codos y tees del árbol. Nodo con d segmentos: d = 2 y no colineales, un codo; d >= 3, d - 2
    tees y ningún codo. El diámetro del accesorio es el mayor de los segmentos que concurren."""
    por_nodo: dict[tuple[str, Coord], list[tuple[Segmento, Coord, Coord]]] = defaultdict(list)
    for s in segmentos:
        por_nodo[(s.fuente_id, s.a)].append((s, s.a, s.b))
        por_nodo[(s.fuente_id, s.b)].append((s, s.b, s.a))

    accesorios: list[Accesorio] = []
    for (fuente_id, _), incidentes in sorted(
        por_nodo.items(), key=lambda kv: (kv[0][0], kv[0][1].x, kv[0][1].y, kv[0][1].z)
    ):
        d = len(incidentes)
        if d < 2:
            continue
        diametros = [s.diametro for s, _, _ in incidentes if s.diametro is not None]
        diametro = max(diametros, key=_magnitud_diametro) if diametros else None
        centro = incidentes[0][1]
        if d >= 3:
            accesorios.append(Accesorio("tee", fuente_id, centro, diametro, d - 2))
            continue
        u = _vec(incidentes[0][1], incidentes[0][2])
        v = _vec(incidentes[1][1], incidentes[1][2])
        # colineales: el extremo del tramo corto se desvía de la recta del largo menos que la
        # tolerancia (misma que en la unión de nodos) y van en sentidos opuestos
        desvio = _norma(_cruz(u, v)) / max(_norma(u), _norma(v))
        colineal = desvio <= TOLERANCIA and _punto_escalar(u, v) < 0
        if not colineal:
            accesorios.append(Accesorio("codo", fuente_id, centro, diametro, 1))
    return tuple(accesorios)


# --- resumen -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Geometria:
    segmentos: tuple[Segmento, ...]
    accesorios: tuple[Accesorio, ...]
    longitud_sin_unir: Decimal
    longitud_unida: Decimal
    longitud_por_diametro: dict[str, Decimal]
    longitud_empotrada: Decimal
    longitud_expuesta: Decimal
    codos: dict[str, int]
    tees: dict[str, int]
    cajas: int


def analizar(
    espacio: Espacio, especialidad: Especialidad | str, cajas_declaradas: int = 0
) -> Geometria:
    """Medidas geométricas de una especialidad: longitudes unidas, accesorios y cajas."""
    esp = Especialidad(especialidad)
    sin_unir = CERO
    segmentos: list[Segmento] = []
    for f in espacio.fuentes:
        if f.especialidad is not esp:
            continue
        piezas, segs = _segmentos_de_fuente(espacio, f)
        sin_unir += sum((pz.a.distancia(pz.b) for pz in piezas), CERO)
        segmentos.extend(segs)
    segmentos.sort(key=lambda s: s.clave)

    por_diametro: dict[str, Decimal] = defaultdict(lambda: CERO)
    empotrada = CERO
    for s in segmentos:
        por_diametro[s.diametro or SIN_DIAMETRO] += s.longitud
        if s.empotrado:
            empotrada += s.longitud
    unida = sum((s.longitud for s in segmentos), CERO)

    accesorios = contar_accesorios(segmentos)
    codos: dict[str, int] = defaultdict(int)
    tees: dict[str, int] = defaultdict(int)
    for a in accesorios:
        destino = codos if a.tipo == "codo" else tees
        destino[a.diametro or SIN_DIAMETRO] += a.cantidad

    cajas = sum(1 for p in espacio.puntos if p.especialidad is esp) + cajas_declaradas
    return Geometria(
        segmentos=tuple(segmentos),
        accesorios=accesorios,
        longitud_sin_unir=sin_unir,
        longitud_unida=unida,
        longitud_por_diametro=dict(por_diametro),
        longitud_empotrada=empotrada,
        longitud_expuesta=unida - empotrada,
        codos=dict(codos),
        tees=dict(tees),
        cajas=cajas,
    )
