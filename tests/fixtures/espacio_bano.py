"""El baño de OF-001 como `Espacio` (datos de `tests/fixtures/memorias/bano_of001.md`, sección 1).

Coordenadas supuestas y declaradas como tales (NORMAS.md §1): no provienen de un plano.
"""

from __future__ import annotations

from decimal import Decimal

from adapters.espacio import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    ModoRecorrido,
    OrigenMedida,
    Punto,
    Recorrido,
    SobrescrituraSegmento,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoOrigen,
    TipoPunto,
    Tramo,
)

D = Decimal


def _tramo(orden, superficie, empotrado, a, b) -> Tramo:
    return Tramo(
        orden=orden,
        superficie=superficie,
        empotrado=empotrado,
        vertices=(Coord(*(D(v) for v in a)), Coord(*(D(v) for v in b))),
    )


def espacio_bano() -> Espacio:
    origen = OrigenMedida(
        id="O1",
        tipo=TipoOrigen.SUPUESTO,
        referencia={"motivo": "ejemplo de memoria de cálculo"},
    )
    return Espacio(
        origenes=(origen,),
        ambientes=(
            Ambiente(
                id="BAN-01",
                nombre="Baño",
                x0=D("0"),
                y0=D("0"),
                largo=D("2.000"),
                ancho=D("1.500"),
                alto=D("2.500"),
                origen_id="O1",
            ),
        ),
        fuentes=(
            Fuente(
                id="F1",
                especialidad=Especialidad.AGUA,
                tipo=TipoFuente.MONTANTE_AGUA,
                ambiente_id="BAN-01",
                posicion=Coord(D("0"), D("0"), D("0")),
                origen_id="O1",
            ),
        ),
        puntos=(
            Punto(
                id="P1",
                nombre="lavamanos",
                especialidad=Especialidad.AGUA,
                tipo=TipoPunto.AGUA_FRIA,
                ambiente_id="BAN-01",
                superficie=SuperficiePunto.PARED,
                posicion=Coord(D("1.500"), D("0"), D("0.600")),
                fuente_id="F1",
                especificaciones={"diametro": '1/2"', "llave_de_paso": "si"},
                origen_id="O1",
            ),
            Punto(
                id="P2",
                nombre="ducha",
                especialidad=Especialidad.AGUA,
                tipo=TipoPunto.AGUA_FRIA,
                ambiente_id="BAN-01",
                superficie=SuperficiePunto.PARED,
                posicion=Coord(D("1.000"), D("1.500"), D("1.200")),
                fuente_id="F1",
                especificaciones={"diametro": '3/4"', "llave_de_paso": "si"},
                origen_id="O1",
            ),
        ),
        recorridos=(
            Recorrido(
                id="R-P1",
                punto_id="P1",
                modo=ModoRecorrido.DECLARADO,
                tramos=(
                    _tramo(1, SuperficieTramo.PARED, True, ("0", "0", "0"), ("0", "0", "2.5")),
                    _tramo(2, SuperficieTramo.TECHO, False, ("0", "0", "2.5"), ("1.5", "0", "2.5")),
                    _tramo(
                        3, SuperficieTramo.PARED, True, ("1.5", "0", "2.5"), ("1.5", "0", "0.6")
                    ),
                ),
            ),
            Recorrido(id="R-P2", punto_id="P2", modo=ModoRecorrido.PROPUESTO),
        ),
        sobrescrituras=(
            SobrescrituraSegmento(
                clave="F1|0.000,0.000,0.000|0.000,0.000,2.500", diametro='3/4"', empotrado=True
            ),
        ),
    )
