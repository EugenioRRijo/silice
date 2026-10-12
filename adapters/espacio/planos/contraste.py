"""R16: contraste entre dos fuentes del mismo espacio (spec S3 §11.4).

Compara el espacio de la versión («el plano») con otro («la referencia»: un levantamiento, el
plano anterior). Empareja ambientes, fuentes y puntos por especialidad, tipo y posición con el
vecino más cercano de la otra fuente, de forma determinista (pares por distancia creciente y,
a igual distancia, por id) y uno a uno:

| Distancia al vecino más cercano | Resultado | Frontera |
|---|---|---|
| ≤ 0,10 m (tolerancia) | emparejado, sin hallazgo | 0,10 emparejado / 0,11 desplazado |
| > 0,10 m y ≤ 1,00 m (radio de búsqueda) | **desplazado** | 1,00 desplazado / 1,01 faltante |
| > 1,00 m o sin vecino | **faltante** (solo en la referencia) y **sobrante** (solo en el plano) | |

Las distancias se comparan al cuadrado y en `Decimal`, así que las fronteras son exactas. Un
ambiente se ubica por el centro de su rectángulo. Ambas distancias son SUPUESTO_DECLARADO. R16 da
**ADVERTENCIA** siempre (RP8-9): la otra fuente puede ser la desactualizada; ERROR queda para la
geometría imposible (R15). El costo de la diferencia lo calcula la interfaz (`ui/contraste.py`)
con `core.budget.comparacion`. R16 no corre en la reauditoría de un paquete (maestro §3.3).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante
from adapters.espacio.modelo import Coord, Espacio
from adapters.espacio.origen import clave_esp
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "CODIGO_R16",
    "RADIO_DE_BUSQUEDA",
    "TOLERANCIA_DE_EMPAREJADO",
    "Contraste",
    "Diferencia",
    "ReglaContraste",
    "contrastar",
]

CODIGO_R16 = "R16"
TOLERANCIA_DE_EMPAREJADO = Constante(
    "R16-tolerancia", "Distancia bajo la cual dos filas son la misma (m)", Decimal("0.10"),
    SUPUESTO_DECLARADO,
)
RADIO_DE_BUSQUEDA = Constante(
    "R16-radio", "Radio de búsqueda del vecino más cercano (m)", Decimal("1.00"),
    SUPUESTO_DECLARADO,
)
DESPLAZADO, FALTANTE, SOBRANTE = "desplazado", "faltante", "sobrante"


@dataclass(frozen=True, slots=True)
class Diferencia:
    """Una diferencia entre las dos fuentes. `id_plano` o `id_referencia` es `None` si la fila
    existe solo en la otra fuente."""

    tipo: str  # desplazado | faltante | sobrante
    tabla: str  # esp_ambientes | esp_fuentes | esp_puntos
    clase: str  # "especialidad/tipo" o "ambiente"
    id_plano: str | None
    id_referencia: str | None
    distancia: Decimal | None


@dataclass(frozen=True, slots=True)
class Contraste:
    diferencias: tuple[Diferencia, ...]
    emparejadas: int


def _filas(espacio: Espacio) -> dict[tuple[str, str], list[tuple[str, Coord]]]:
    """`(tabla, clase)` -> `[(id, posición)]`."""
    filas: dict[tuple[str, str], list[tuple[str, Coord]]] = defaultdict(list)
    for a in espacio.ambientes:
        centro = Coord(a.x0 + a.largo / 2, a.y0 + a.ancho / 2, Decimal(0))
        filas[("esp_ambientes", "ambiente")].append((a.id, centro))
    for f in espacio.fuentes:
        filas[("esp_fuentes", f"{f.especialidad.value}/{f.tipo.value}")].append(
            (f.id, f.posicion))
    for p in espacio.puntos:
        filas[("esp_puntos", f"{p.especialidad.value}/{p.tipo.value}")].append(
            (p.id, p.posicion))
    return filas


def _cuadrado(a: Coord, b: Coord) -> Decimal:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2


def contrastar(espacio: Espacio, referencia: Espacio) -> Contraste:
    """Las diferencias de `espacio` (el plano) frente a `referencia`, ordenadas por tabla, clase,
    tipo e id. Determinista: el mismo par de espacios da siempre el mismo resultado."""
    tolerancia2 = Decimal(TOLERANCIA_DE_EMPAREJADO.valor) ** 2
    radio2 = Decimal(RADIO_DE_BUSQUEDA.valor) ** 2
    plano, ref = _filas(espacio), _filas(referencia)
    diferencias: list[Diferencia] = []
    emparejadas = 0
    for clave in sorted(set(plano) | set(ref)):
        tabla, clase = clave
        propios, ajenos = plano.get(clave, []), ref.get(clave, [])
        candidatos = sorted(
            (_cuadrado(pos_a, pos_b), id_b, id_a)
            for id_a, pos_a in propios
            for id_b, pos_b in ajenos
            if _cuadrado(pos_a, pos_b) <= radio2
        )
        usados_plano: set[str] = set()
        usados_ref: set[str] = set()
        for distancia2, id_ref, id_plano in candidatos:
            if id_plano in usados_plano or id_ref in usados_ref:
                continue
            usados_plano.add(id_plano)
            usados_ref.add(id_ref)
            if distancia2 <= tolerancia2:
                emparejadas += 1
            else:
                diferencias.append(
                    Diferencia(DESPLAZADO, tabla, clase, id_plano, id_ref, distancia2.sqrt())
                )
        diferencias += [
            Diferencia(FALTANTE, tabla, clase, None, id_ref, None)
            for id_ref, _ in sorted(ajenos) if id_ref not in usados_ref
        ]
        diferencias += [
            Diferencia(SOBRANTE, tabla, clase, id_plano, None, None)
            for id_plano, _ in sorted(propios) if id_plano not in usados_plano
        ]
    orden = {DESPLAZADO: 0, FALTANTE: 1, SOBRANTE: 2}
    diferencias.sort(key=lambda d: (d.tabla, d.clase, orden[d.tipo], d.id_plano or "",
                                    d.id_referencia or ""))
    return Contraste(tuple(diferencias), emparejadas)


def _n(valor: Decimal) -> str:
    return format(valor.normalize(), "f")


class ReglaContraste(ReglaVerificacion):
    """R16 sobre la instantánea del espacio de la versión y el espacio de referencia."""

    codigo = CODIGO_R16
    nombre = "Contraste entre dos fuentes"

    def __init__(self, espacio: Espacio, espacio_referencia: Espacio,
                 nombre_referencia: str = "la otra fuente") -> None:
        self.espacio = espacio
        self.espacio_referencia = espacio_referencia
        self.nombre_referencia = nombre_referencia

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        hallazgos = []
        for d in contrastar(self.espacio, self.espacio_referencia).diferencias:
            fila = d.id_plano or d.id_referencia or ""
            if d.tipo == DESPLAZADO:
                texto = (f"{d.clase} {d.id_plano}: desplazado {_n(d.distancia)} m respecto de "
                         f"{d.id_referencia} en {self.nombre_referencia}")
            elif d.tipo == FALTANTE:
                texto = (f"{d.clase} {fila}: esta en {self.nombre_referencia} y falta en el plano")
            else:
                texto = (f"{d.clase} {fila}: esta en el plano y no en {self.nombre_referencia}")
            hallazgos.append(Hallazgo(
                regla=CODIGO_R16, severidad=Severidad.ADVERTENCIA, descripcion=texto,
                origen_ids=(clave_esp(d.tabla, fila),), valor_observado=d.distancia,
                valor_esperado=Decimal(TOLERANCIA_DE_EMPAREJADO.valor) if d.distancia else None,
            ))
        return hallazgos
