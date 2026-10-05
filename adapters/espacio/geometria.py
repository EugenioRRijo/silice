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
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal
from fractions import Fraction
from functools import lru_cache

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


@lru_cache(maxsize=256)
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
    #: superficie declarada por los tramos que lo forman; None si discrepan
    superficie: SuperficieTramo | None = None


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
    superficie: SuperficieTramo


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
                    piezas.append(_Pieza(a, b, sirve, diametro, _empotrado_de(t), t.superficie))

    for p in espacio.puntos:
        if p.fuente_id == fuente.id:
            agregar(tramos_de(espacio, p), p.id, normalizar_diametro(p.espec.get("diametro")))
    circuitos = {c.id for c in espacio.circuitos if c.tablero == fuente.id}
    for r in espacio.recorridos:
        if r.circuito_id in circuitos:
            agregar(r.tramos, r.circuito_id, None)
    return piezas


def _celda(c: Coord) -> tuple[int, int, int]:
    """Celda de la cuadrícula hash: lado TOLERANCIA, piso de cada coordenada (exacto en Decimal)."""
    return (
        int((c.x / TOLERANCIA).to_integral_value(ROUND_FLOOR)),
        int((c.y / TOLERANCIA).to_integral_value(ROUND_FLOOR)),
        int((c.z / TOLERANCIA).to_integral_value(ROUND_FLOOR)),
    )


_VECINAS = tuple((i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1))


def _agrupar_nodos(coords: Iterable[Coord]) -> dict[Coord, Coord]:
    """Une por vecindad (single-linkage, distancia <= TOLERANCIA) las coordenadas de los extremos.

    Devuelve coordenada -> representante, que es la mínima lexicográfica (x, y, z) del grupo: no
    depende del orden de entrada ni de los ids. Es la única tolerancia de la unión y del corte.

    Cuadrícula espacial hash de lado TOLERANCIA: dos coordenadas a TOLERANCIA o menos caen en la
    misma celda o en una vecina, así que cada una solo se prueba contra las 27 celdas de su entorno
    (costo lineal con densidad acotada; el barrido por x era cuadrático si muchos nodos comparten
    x).
    El resultado es el del barrido completo de todos los pares.

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

    celdas: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    claves = [_celda(c) for c in unicas]
    for i, k in enumerate(claves):
        celdas[k].append(i)
    tol2 = TOLERANCIA * TOLERANCIA
    for i, a in enumerate(unicas):
        kx, ky, kz = claves[i]
        for dx, dy, dz in _VECINAS:
            for j in celdas.get((kx + dx, ky + dy, kz + dz), ()):
                if j <= i:
                    continue
                b = unicas[j]
                ex, ey, ez = b.x - a.x, b.y - a.y, b.z - a.z
                if ex * ex + ey * ey + ez * ez <= tol2:
                    ri, rj = raiz(i), raiz(j)
                    if ri != rj:
                        padre[max(ri, rj)] = min(ri, rj)  # la raíz es la mínima lexicográfica
    return {c: unicas[raiz(i)] for i, c in enumerate(unicas)}


class _IndiceNodos:
    """Nodos en una cuadrícula hash de lado TOLERANCIA para probar en cada pieza solo los que caen
    en su caja envolvente (con margen TOLERANCIA); el resultado es el mismo que probar todos.

    `todos` va ordenado por (x, y, z) y se identifica a cada nodo por su posición ahí (su rango),
    así el resto del cálculo compara enteros y no coordenadas. Si la caja cubre pocas celdas se leen
    esas celdas; si cubre más celdas que nodos hay (pieza larga), se toma la banda más estrecha de
    los tres ejes ordenados y se filtra por los otros dos.
    """

    def __init__(self, nodos: list[Coord]) -> None:
        self.todos = nodos
        self._celdas: dict[tuple[int, int, int], list[int]] = defaultdict(list)
        for r, n in enumerate(nodos):
            self._celdas[_celda(n)].append(r)
        self._ejes = [
            sorted((getattr(n, eje), r) for r, n in enumerate(nodos)) for eje in ("x", "y", "z")
        ]
        self._valores = [[v for v, _ in e] for e in self._ejes]
        self.xs = [n.x for n in nodos]
        self.ys = [n.y for n in nodos]
        self.zs = [n.z for n in nodos]

    def cercanos(self, a: Coord, b: Coord) -> list[int]:
        """Rangos de los nodos dentro de la caja de (a, b) con margen TOLERANCIA."""
        t = TOLERANCIA
        lo = Coord(min(a.x, b.x) - t, min(a.y, b.y) - t, min(a.z, b.z) - t)
        hi = Coord(max(a.x, b.x) + t, max(a.y, b.y) + t, max(a.z, b.z) + t)
        (i0, j0, k0), (i1, j1, k1) = _celda(lo), _celda(hi)
        n_celdas = (i1 - i0 + 1) * (j1 - j0 + 1) * (k1 - k0 + 1)
        if n_celdas <= len(self.todos):
            candidatos = (
                r
                for i in range(i0, i1 + 1)
                for j in range(j0, j1 + 1)
                for k in range(k0, k1 + 1)
                for r in self._celdas.get((i, j, k), ())
            )
        else:
            mejor, rango = 0, (0, 0)
            for e, (vl, vh) in enumerate(zip((lo.x, lo.y, lo.z), (hi.x, hi.y, hi.z), strict=True)):
                r = (bisect_left(self._valores[e], vl), bisect_right(self._valores[e], vh))
                if e == 0 or r[1] - r[0] < rango[1] - rango[0]:
                    mejor, rango = e, r
            candidatos = (r for _, r in self._ejes[mejor][rango[0] : rango[1]])
        xs, ys, zs = self.xs, self.ys, self.zs
        lx, ly, lz, hx, hy, hz = lo.x, lo.y, lo.z, hi.x, hi.y, hi.z
        return [
            r for r in candidatos if lx <= xs[r] <= hx and ly <= ys[r] <= hy and lz <= zs[r] <= hz
        ]


_TOL2 = TOLERANCIA * TOLERANCIA
_HOLGURA = Decimal("1e-20")  # relativa; solo separa lo seguro de lo que se confirma con la raiz
_SEGURO_DENTRO = _TOL2 * (1 - _HOLGURA)
_SEGURO_FUERA = _TOL2 * (1 + _HOLGURA)


def _a_tolerancia_del_pie(n: Coord, a: Coord, d: tuple[Decimal, ...], t: Decimal) -> bool:
    """True si `n` queda a TOLERANCIA o menos del pie de su proyeccion sobre el segmento (a, d).

    Es `n.distancia(pie) <= TOLERANCIA` de siempre, sin construir el pie ni sacar la raiz cuando el
    cuadrado de la distancia esta claramente a un lado de TOLERANCIA**2; lo dudoso (a menos de 1e-20
    relativo del limite) se decide con la misma raiz de antes, asi que el resultado no cambia."""
    ex, ey, ez = a.x + t * d[0] - n.x, a.y + t * d[1] - n.y, a.z + t * d[2] - n.z
    d2 = ex * ex + ey * ey + ez * ez
    if d2 < _SEGURO_DENTRO:
        return True
    if d2 > _SEGURO_FUERA:
        return False
    return d2.sqrt() <= TOLERANCIA


@lru_cache(maxsize=8)
def _segmentos_de_fuente(
    espacio: Espacio, fuente: Fuente
) -> tuple[tuple[_Pieza, ...], tuple[Segmento, ...]]:
    """Piezas y segmentos de una fuente. Se calcula UNA vez por `Espacio` (inmutable y hashable):
    derivar, R8 y R9 del mismo ciclo comparten el resultado (RNF-11)."""
    piezas = _piezas_de_fuente(espacio, fuente)
    if not piezas:
        return (), ()
    rep = _agrupar_nodos(c for pz in piezas for c in (pz.a, pz.b))
    nodos = sorted(set(rep.values()), key=lambda c: (c.x, c.y, c.z))
    indice = _IndiceNodos(nodos)
    rango = {n: r for r, n in enumerate(nodos)}

    # llave (rango menor, rango mayor) -> (piezas que la cubren, largo que cada una le aporta)
    acumulado: dict[tuple[int, int], tuple[list[int], list[Decimal]]] = {}
    columnas = (indice.xs, indice.ys, indice.zs)
    for indice_pieza, pz in enumerate(piezas):
        a, b = rep[pz.a], rep[pz.b]
        if a == b:
            continue  # largo cero tras unir los nodos vecinos
        ra, rb = rango[a], rango[b]
        d = _vec(a, b)
        largo2 = _punto_escalar(d, d)
        largo = a.distancia(b)
        cortes: list[tuple[Decimal, int]] = []
        candidatos = [r for r in indice.cercanos(a, b) if r != ra and r != rb]
        ejes = [k for k in range(3) if d[k]]
        if len(ejes) == 1:
            # pieza paralela a un eje (lo habitual: recorridos ortogonales). Misma cuenta que la
            # general, que suma terminos nulos: t es identico y el desvio perpendicular solo pierde
            # un termino ~1e-56 que no cambia el veredicto (lo dudoso lo decide la raiz exacta).
            k = ejes[0]
            c_k, c_p, c_q = columnas[k], columnas[(k + 1) % 3], columnas[(k + 2) % 3]
            origen = (a.x, a.y, a.z)
            a_k, a_p, a_q, d_k = origen[k], origen[(k + 1) % 3], origen[(k + 2) % 3], d[k]
            for r in candidatos:
                t = ((c_k[r] - a_k) * d_k) / largo2
                if not (0 < t < 1):
                    continue
                ep, eq = a_p - c_p[r], a_q - c_q[r]
                d2 = ep * ep + eq * eq
                if d2 < _SEGURO_DENTRO or (
                    d2 <= _SEGURO_FUERA and _a_tolerancia_del_pie(nodos[r], a, d, t)
                ):
                    cortes.append((t, r))
        else:
            ax, ay, az = a.x, a.y, a.z
            dx, dy, dz = d
            xs, ys, zs = columnas
            for r in candidatos:
                t = ((xs[r] - ax) * dx + (ys[r] - ay) * dy + (zs[r] - az) * dz) / largo2
                if not (0 < t < 1):
                    continue
                ex, ey, ez = ax + t * dx - xs[r], ay + t * dy - ys[r], az + t * dz - zs[r]
                d2 = ex * ex + ey * ey + ez * ez
                if d2 < _SEGURO_DENTRO or (
                    d2 <= _SEGURO_FUERA and _a_tolerancia_del_pie(nodos[r], a, d, t)
                ):
                    cortes.append((t, r))
        # las longitudes se miden sobre el segmento original (t * largo): partirlo en un nodo
        # que se desvía menos de la tolerancia no lo dobla ni lo alarga. El rango ordena igual
        # que (x, y, z), asi el desempate de t iguales es el de siempre.
        cortes.sort()
        t_ant, r_ant = Decimal(0), ra
        for t_sig, r_sig in [*cortes, (Decimal(1), rb)]:
            llave = (r_ant, r_sig) if r_ant <= r_sig else (r_sig, r_ant)
            reg = acumulado.get(llave)
            if reg is None:
                reg = acumulado[llave] = ([], [])
            reg[0].append(indice_pieza)
            reg[1].append((t_sig - t_ant) * largo)
            t_ant, r_ant = t_sig, r_sig

    sobre = {s.clave: s for s in espacio.sobrescrituras}
    segmentos: list[Segmento] = []
    for (ia, ib), (cubren, largos) in acumulado.items():
        a, b = nodos[ia], nodos[ib]
        largo_unido = max(CERO, *largos)
        cubiertas = [piezas[i] for i in cubren]
        sirve = {pz.sirve for pz in cubiertas}
        # sin repetir y en orden de aparicion: `max` desempata igual que con la lista entera
        diametros = dict.fromkeys(pz.diametro for pz in cubiertas if pz.diametro is not None)
        empotrados = {pz.empotrado for pz in cubiertas}
        superficies = {pz.superficie for pz in cubiertas}
        clave = clave_segmento(fuente.id, a, b)
        diametro = max(diametros, key=_magnitud_diametro) if diametros else None
        conflicto = len(empotrados) > 1
        empotrado = empotrados == {True}
        superficie = next(iter(superficies)) if len(superficies) == 1 else None
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
                longitud=largo_unido,
                sirve=tuple(sorted(sirve)),
                diametro=diametro,
                empotrado=empotrado,
                conflicto_empotrado=conflicto,
                superficie=superficie,
            )
        )
    segmentos.sort(key=lambda s: s.clave)
    return tuple(piezas), tuple(segmentos)


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
