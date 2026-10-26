"""Búsqueda con autocompletado: partidas del catálogo (diseño de autocompletado 2026-10-21 §5.1,
§5.2 y §5.4; Tarea 10 del plan de montar un presupuesto).

Una sola regla de búsqueda y orden para los campos con búsqueda de la interfaz nueva
(`CampoConBusqueda`). El texto se normaliza con `normalizar_texto` (la única normalización del
repositorio: minúsculas, sin tildes, una grafía de la pulgada) y se parte en palabras. Una fila
coincide si **todas** las palabras están, como subcadena y en cualquier orden, en su código o su
descripción; la unidad no entra (escribir «m» devolvería todo lo medido en metros).

Rango, menor primero: 0 = el código es el texto; 1 = el código empieza por el texto; 2 = la
descripción empieza por la primera palabra; 3 = alguna palabra de la descripción empieza por ella;
4 = cualquier otra coincidencia. Desempate: descripción normalizada y luego código.

La búsqueda se hace en Python sobre las partidas del catálogo (cientos a pocos miles): `LIKE` de
SQL no quita tildes ni unifica la pulgada. Las demás búsquedas del diseño (insumos, unidades,
línea base) quedan para el plan de autocompletado.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.catalog import Catalogo
from core.contracts.dominio import Dominio
from core.verification.texto import normalizar_texto

__all__ = [
    "LARGO_MAXIMO",
    "LARGO_MINIMO",
    "LIMITE_MAXIMO",
    "LIMITE_POR_OMISION",
    "PartidaHallada",
    "buscar_partidas",
    "rango",
]

#: Menos letras que esto no buscan: un campo que se está tecleando no es un error (§5.1).
LARGO_MINIMO = 2
#: Tope del texto buscado, el mismo `maxLength` del campo de la interfaz (§3.2).
LARGO_MAXIMO = 80
#: Resultados por grupo: por omisión y tope (§5.1).
LIMITE_POR_OMISION = 20
LIMITE_MAXIMO = 50


@dataclass(frozen=True)
class PartidaHallada:
    """Una partida del catálogo que coincide con lo buscado, con su cabecera."""

    codigo: str
    descripcion: str
    unidad: str
    dominio: str
    #: Tiene al menos una línea de composición; una sin ellas también se puede elegir.
    tiene_composicion: bool


def rango(codigo: str, descripcion: str, texto: str) -> int | None:
    """El rango de una fila para `texto` (ya normalizado y sin espacios de sobra), o `None` si no
    coincide. `codigo` y `descripcion` se normalizan aquí."""
    palabras = texto.split()
    if not palabras:
        return None
    codigo_n = normalizar_texto(codigo)
    descripcion_n = normalizar_texto(descripcion)
    pajar = f"{codigo_n} {descripcion_n}"
    if not all(palabra in pajar for palabra in palabras):
        return None
    primera = palabras[0]
    if codigo_n == texto:
        return 0
    if codigo_n.startswith(texto):
        return 1
    if descripcion_n.startswith(primera):
        return 2
    if any(palabra.startswith(primera) for palabra in descripcion_n.split()):
        return 3
    return 4


def buscar_partidas(
    catalogo: Catalogo, q: str, dominio: Dominio | None, limite: int
) -> tuple[list[PartidaHallada], bool]:
    """Las partidas del catálogo (del `dominio`, si se da) que coinciden con `q`, ordenadas por
    relevancia y cortadas en `limite`; el segundo valor dice si quedaron más fuera del corte.

    `q` con menos de `LARGO_MINIMO` caracteres (sin contar los espacios de los bordes) devuelve
    `([], False)`. Un `limite` fuera de 1..`LIMITE_MAXIMO` es un `ValueError`.
    """
    if not 1 <= limite <= LIMITE_MAXIMO:
        raise ValueError(f"el límite va de 1 a {LIMITE_MAXIMO}")
    recortado = q.strip()
    if len(recortado) < LARGO_MINIMO:
        return [], False
    texto = normalizar_texto(recortado)
    candidatas = []
    for partida in catalogo.partidas(dominio):
        orden = rango(partida.codigo, partida.descripcion, texto)
        if orden is not None:
            candidatas.append(
                (orden, normalizar_texto(partida.descripcion), partida.codigo, partida)
            )
    candidatas.sort(key=lambda fila: fila[:3])
    elegidas = [fila[3] for fila in candidatas[:limite]]
    halladas = [
        PartidaHallada(
            codigo=partida.codigo,
            descripcion=partida.descripcion,
            unidad=partida.unidad,
            dominio=partida.dominio,
            tiene_composicion=bool(partida.composicion),
        )
        for partida in elegidas
    ]
    return halladas, len(candidatas) > limite
