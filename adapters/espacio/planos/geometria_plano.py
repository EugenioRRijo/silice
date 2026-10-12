"""R15: coherencia geométrica del plano, con `shapely` como índice espacial (spec S3 §11.3).

`ReglaVerificacion` construida con la instantánea del espacio, como R8 a R10 (DA-SF-8). **Toda
medida y toda comparación salen de las coordenadas `Decimal`** (DA-S3-6): `shapely` trabaja en
coma flotante y solo **propone candidatos** (cajas y puntos cercanos con `STRtree`); cada
hallazgo se decide con aritmética exacta, así que las fronteras (0,0100 m² pasa, 0,0101 m² falla)
no dependen del redondeo de un `float`.

| Condición | Severidad | Pasa | Falla |
|---|---|---|---|
| dos ambientes se superponen en más de 0,01 m² | ERROR | 0,0100 m² | 0,0101 m² |
| dos puntos de la misma especialidad y tipo a menos de 0,001 m | ERROR | 0,0010 m | 0,0009 m |
| lado de ambiente < 0,30 m o > 200 m | ADVERTENCIA | 0,300 y 200,000 | 0,299 y 200,001 |
| altura de ambiente < 2,00 m o > 12 m | ADVERTENCIA | 2,000 y 12,000 | 1,999 y 12,001 |
| punto a más de 100 m de su fuente | ADVERTENCIA | 100,000 m | 100,001 m |

Las dos primeras son tolerancias geométricas del sistema y son ERROR; las tres últimas dependen de
umbrales SUPUESTOS (sin fuente normativa, a verificar) y por eso son ADVERTENCIA desde el diseño,
como R10. R15 no repite R9: un punto fuera de su ambiente o un recorrido imposible es de R9.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from shapely.geometry import Point, box
from shapely.strtree import STRtree

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante
from adapters.espacio.modelo import Ambiente, Espacio, Punto
from adapters.espacio.origen import clave_esp
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "CODIGO_R15",
    "CONSTANTES_R15",
    "CoherenciaGeometrica",
    "reglas_plano",
]

CODIGO_R15 = "R15"

SUPERPOSICION_MAXIMA = Constante(
    "R15-superposicion", "Superposición máxima entre ambientes (m2)", Decimal("0.01"),
    "tolerancia geométrica del sistema",
)
DUPLICADO_MENOR_QUE = Constante(
    "R15-duplicado", "Distancia bajo la cual dos puntos son duplicados (m)", Decimal("0.001"),
    "tolerancia geométrica del sistema (adapters.espacio.modelo.TOLERANCIA)",
)
LADO_MINIMO = Constante("R15-lado-min", "Lado mínimo de un ambiente (m)", Decimal("0.30"),
                        SUPUESTO_DECLARADO)
LADO_MAXIMO = Constante("R15-lado-max", "Lado máximo de un ambiente (m)", Decimal("200"),
                        SUPUESTO_DECLARADO)
ALTURA_MINIMA = Constante("R15-alto-min", "Altura mínima de un ambiente (m)", Decimal("2.00"),
                          SUPUESTO_DECLARADO)
ALTURA_MAXIMA = Constante("R15-alto-max", "Altura máxima de un ambiente (m)", Decimal("12"),
                          SUPUESTO_DECLARADO)
DISTANCIA_A_LA_FUENTE = Constante(
    "R15-fuente", "Distancia máxima de un punto a su fuente (m)", Decimal("100"),
    SUPUESTO_DECLARADO,
)
CONSTANTES_R15 = (SUPERPOSICION_MAXIMA, DUPLICADO_MENOR_QUE, LADO_MINIMO, LADO_MAXIMO,
                  ALTURA_MINIMA, ALTURA_MAXIMA, DISTANCIA_A_LA_FUENTE)


def _n(valor: Decimal) -> str:
    return format(valor.normalize(), "f")


def _hallazgo(
    severidad: Severidad, origen: tuple[str, ...], descripcion: str,
    observado: Decimal | None = None, esperado: Decimal | None = None,
) -> Hallazgo:
    return Hallazgo(
        regla=CODIGO_R15, severidad=severidad, descripcion=descripcion, origen_ids=origen,
        valor_observado=observado, valor_esperado=esperado,
    )


def _caja(a: Ambiente):
    return box(float(a.x0), float(a.y0), float(a.x0 + a.largo), float(a.y0 + a.ancho))


def _superposiciones(espacio: Espacio) -> list[Hallazgo]:
    ambientes = espacio.ambientes
    if len(ambientes) < 2:
        return []
    cajas = [_caja(a) for a in ambientes]
    arbol = STRtree(cajas)
    parejas = sorted(
        {tuple(sorted((int(i), int(j)))) for i, caja in enumerate(cajas)
         for j in arbol.query(caja) if int(j) != i}
    )
    limite = Decimal(SUPERPOSICION_MAXIMA.valor)
    hallazgos = []
    for i, j in parejas:
        a, b = ambientes[i], ambientes[j]
        ancho_x = min(a.x0 + a.largo, b.x0 + b.largo) - max(a.x0, b.x0)
        ancho_y = min(a.y0 + a.ancho, b.y0 + b.ancho) - max(a.y0, b.y0)
        area = ancho_x * ancho_y if ancho_x > 0 and ancho_y > 0 else Decimal(0)
        if area > limite:
            hallazgos.append(_hallazgo(
                Severidad.ERROR,
                (clave_esp("esp_ambientes", a.id), clave_esp("esp_ambientes", b.id)),
                f"ambientes {a.id} y {b.id}: se superponen en {_n(area)} m2, mas de "
                f"{_n(limite)} m2",
                area, limite,
            ))
    return hallazgos


def _duplicados(espacio: Espacio) -> list[Hallazgo]:
    grupos: dict[tuple[str, str], list[Punto]] = defaultdict(list)
    for p in espacio.puntos:
        grupos[(p.especialidad.value, p.tipo.value)].append(p)
    minimo = Decimal(DUPLICADO_MENOR_QUE.valor)
    cuadrado = minimo * minimo
    radio = float(minimo) * 1.01 + 1e-9
    hallazgos = []
    for _, puntos in sorted(grupos.items()):
        if len(puntos) < 2:
            continue
        geometrias = [Point(float(p.posicion.x), float(p.posicion.y)) for p in puntos]
        arbol = STRtree(geometrias)
        vistos: set[tuple[int, int]] = set()
        for i, geometria in enumerate(geometrias):
            for j in arbol.query(geometria.buffer(radio)):
                j = int(j)
                if j <= i or (i, j) in vistos:
                    continue
                vistos.add((i, j))
                a, b = puntos[i], puntos[j]
                d = b.posicion
                distancia2 = ((a.posicion.x - d.x) ** 2 + (a.posicion.y - d.y) ** 2
                              + (a.posicion.z - d.z) ** 2)
                if distancia2 < cuadrado:
                    distancia = a.posicion.distancia(b.posicion)
                    hallazgos.append(_hallazgo(
                        Severidad.ERROR,
                        (clave_esp("esp_puntos", a.id), clave_esp("esp_puntos", b.id)),
                        f"puntos {a.id} y {b.id}: duplicados a {_n(distancia)} m, menos de "
                        f"{_n(minimo)} m",
                        distancia, minimo,
                    ))
    return sorted(hallazgos, key=lambda h: h.origen_ids)


def _escala(espacio: Espacio) -> list[Hallazgo]:
    hallazgos = []
    lado_min, lado_max = Decimal(LADO_MINIMO.valor), Decimal(LADO_MAXIMO.valor)
    alto_min, alto_max = Decimal(ALTURA_MINIMA.valor), Decimal(ALTURA_MAXIMA.valor)
    for a in espacio.ambientes:
        clave = (clave_esp("esp_ambientes", a.id),)
        for nombre, lado in (("largo", a.largo), ("ancho", a.ancho)):
            if not lado_min <= lado <= lado_max:
                hallazgos.append(_hallazgo(
                    Severidad.ADVERTENCIA, clave,
                    f"ambiente {a.id}: {nombre} de {_n(lado)} m fuera de [{_n(lado_min)}; "
                    f"{_n(lado_max)}] m (escala imposible; supuesto declarado)",
                    lado, lado_min if lado < lado_min else lado_max,
                ))
        if not alto_min <= a.alto <= alto_max:
            hallazgos.append(_hallazgo(
                Severidad.ADVERTENCIA, clave,
                f"ambiente {a.id}: altura de {_n(a.alto)} m fuera de [{_n(alto_min)}; "
                f"{_n(alto_max)}] m (escala imposible; supuesto declarado)",
                a.alto, alto_min if a.alto < alto_min else alto_max,
            ))
    return hallazgos


def _lejos_de_la_fuente(espacio: Espacio) -> list[Hallazgo]:
    fuentes = {f.id: f for f in espacio.fuentes}
    maximo = Decimal(DISTANCIA_A_LA_FUENTE.valor)
    hallazgos = []
    for p in espacio.puntos:
        fuente = fuentes.get(p.fuente_id) if p.fuente_id is not None else None
        if fuente is None:
            continue
        d, q = p.posicion, fuente.posicion
        if (d.x - q.x) ** 2 + (d.y - q.y) ** 2 + (d.z - q.z) ** 2 > maximo * maximo:
            distancia = p.posicion.distancia(fuente.posicion)
            hallazgos.append(_hallazgo(
                Severidad.ADVERTENCIA,
                (clave_esp("esp_puntos", p.id), clave_esp("esp_fuentes", fuente.id)),
                f"punto {p.id}: a {_n(distancia)} m de su fuente {fuente.id}, mas de "
                f"{_n(maximo)} m (supuesto declarado)",
                distancia, maximo,
            ))
    return hallazgos


class CoherenciaGeometrica(ReglaVerificacion):
    """R15: el plano no se superpone, no duplica puntos y tiene una escala posible."""

    codigo = CODIGO_R15
    nombre = "Coherencia geométrica del plano"

    def __init__(self, espacio: Espacio) -> None:
        self.espacio = espacio

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return [
            *_superposiciones(self.espacio),
            *_duplicados(self.espacio),
            *_escala(self.espacio),
            *_lejos_de_la_fuente(self.espacio),
        ]


def reglas_plano(espacio: Espacio) -> tuple[ReglaVerificacion, ...]:
    """Las reglas de plano para `elaborar(reglas=REGLAS + reglas_espacio(e) + reglas_plano(e))`.
    R16 no entra aquí: necesita una segunda fuente (`planos.contraste.ReglaContraste`)."""
    return (CoherenciaGeometrica(espacio),)
