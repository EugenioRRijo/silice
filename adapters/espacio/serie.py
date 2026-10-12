"""El espacio como objeto JSON y de vuelta: `anexos/espacio.json` del paquete (spec S3 §6.2, §8.1).

`espacio_a_objeto` escribe cada `Decimal` como texto posicional exacto y cada colección en el
orden que ya garantiza `Espacio` (por id); `espacio_desde_objeto` es la inversa y recibe la
función que convierte un texto en `Decimal` (`seguridad.json_estricto.a_decimal` en la
reauditoría: el adaptador no importa `seguridad`, y así el patrón estricto vive en un solo lugar).
Antes de construir nada, `comprobar_limites` aplica los topes de S3 §8.4 (5 000 ambientes,
50 000 puntos, 1 000 vértices por tramo), para que R15 con `shapely` no reciba un anexo hostil.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any

from adapters.espacio.modelo import (
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Fuente,
    Punto,
    Recorrido,
    SobrescrituraSegmento,
    Tramo,
)
from adapters.espacio.origen import OrigenMedida

__all__ = [
    "LIMITE_AMBIENTES",
    "LIMITE_PUNTOS",
    "LIMITE_VERTICES_POR_TRAMO",
    "LimiteExcedido",
    "comprobar_limites",
    "espacio_a_objeto",
    "espacio_desde_objeto",
]

LIMITE_AMBIENTES = 5000
LIMITE_PUNTOS = 50_000
LIMITE_VERTICES_POR_TRAMO = 1000


class LimiteExcedido(ValueError):  # noqa: N818
    """El anexo de espacio excede un tope de S3 §8.4; el mensaje dice cuál."""


def _t(valor: Decimal | None) -> str | None:
    return None if valor is None else format(valor, "f")


def _coord(c: Coord) -> list[str]:
    return [format(c.x, "f"), format(c.y, "f"), format(c.z, "f")]


def espacio_a_objeto(espacio: Espacio) -> dict[str, Any]:
    return {
        "origenes": [
            {"id": o.id, "tipo": o.tipo.value, "referencia": dict(o.referencia)}
            for o in espacio.origenes
        ],
        "ambientes": [
            {"id": a.id, "nombre": a.nombre, "x0": _t(a.x0), "y0": _t(a.y0), "largo": _t(a.largo),
             "ancho": _t(a.ancho), "alto": _t(a.alto), "origen_id": a.origen_id}
            for a in espacio.ambientes
        ],
        "fuentes": [
            {"id": f.id, "especialidad": f.especialidad.value, "tipo": f.tipo.value,
             "ambiente_id": f.ambiente_id, "posicion": _coord(f.posicion), "origen_id": f.origen_id}
            for f in espacio.fuentes
        ],
        "circuitos": [
            {"id": c.id, "tablero": c.tablero, "numero": c.numero,
             "conductores": list(c.conductores), "calibre": c.calibre,
             "puntos_maximos": c.puntos_maximos, "orden": list(c.orden)}
            for c in espacio.circuitos
        ],
        "puntos": [
            {"id": p.id, "nombre": p.nombre, "especialidad": p.especialidad.value,
             "tipo": p.tipo.value, "ambiente_id": p.ambiente_id, "superficie": p.superficie.value,
             "posicion": _coord(p.posicion), "fuente_id": p.fuente_id, "circuito_id": p.circuito_id,
             "especificaciones": dict(p.especificaciones), "origen_id": p.origen_id}
            for p in espacio.puntos
        ],
        "recorridos": [
            {"id": r.id, "modo": r.modo.value, "punto_id": r.punto_id,
             "circuito_id": r.circuito_id,
             "tramos": [
                 {"orden": t.orden, "superficie": t.superficie.value, "empotrado": t.empotrado,
                  "pendiente": _t(t.pendiente), "vertices": [_coord(v) for v in t.vertices]}
                 for t in r.tramos
             ]}
            for r in espacio.recorridos
        ],
        "sobrescrituras": [
            {"clave": s.clave, "diametro": s.diametro, "empotrado": s.empotrado}
            for s in espacio.sobrescrituras
        ],
    }


def comprobar_limites(objeto: Mapping[str, Any]) -> None:
    """Los topes de S3 §8.4, ANTES de construir el `Espacio`. `LimiteExcedido` si se pasa uno."""
    ambientes = objeto.get("ambientes", [])
    puntos = objeto.get("puntos", [])
    if len(ambientes) > LIMITE_AMBIENTES:
        raise LimiteExcedido(f"el anexo de espacio trae mas de {LIMITE_AMBIENTES} ambientes")
    if len(puntos) > LIMITE_PUNTOS:
        raise LimiteExcedido(f"el anexo de espacio trae mas de {LIMITE_PUNTOS} puntos")
    for recorrido in objeto.get("recorridos", []):
        for tramo in recorrido.get("tramos", []):
            if len(tramo.get("vertices", [])) > LIMITE_VERTICES_POR_TRAMO:
                raise LimiteExcedido(
                    f"un tramo del anexo de espacio trae mas de {LIMITE_VERTICES_POR_TRAMO} "
                    "vertices"
                )


def espacio_desde_objeto(
    objeto: Mapping[str, Any], a_decimal: Callable[[Any], Decimal] = Decimal
) -> Espacio:
    """El `Espacio` de un objeto leído por el lector estricto. `ValueError` si le falta algo."""
    comprobar_limites(objeto)

    def coord(valor: list[Any]) -> Coord:
        x, y, z = (a_decimal(v) for v in valor)
        return Coord(x, y, z)

    def decimal(valor: Any) -> Decimal | None:
        return None if valor is None else a_decimal(valor)

    try:
        return Espacio(
            origenes=tuple(
                OrigenMedida(id=o["id"], tipo=o["tipo"], referencia=o["referencia"])
                for o in objeto.get("origenes", [])
            ),
            ambientes=tuple(
                Ambiente(
                    id=a["id"], nombre=a["nombre"], x0=a_decimal(a["x0"]), y0=a_decimal(a["y0"]),
                    largo=a_decimal(a["largo"]), ancho=a_decimal(a["ancho"]),
                    alto=a_decimal(a["alto"]), origen_id=a["origen_id"],
                )
                for a in objeto.get("ambientes", [])
            ),
            fuentes=tuple(
                Fuente(id=f["id"], especialidad=f["especialidad"], tipo=f["tipo"],
                       ambiente_id=f["ambiente_id"], posicion=coord(f["posicion"]),
                       origen_id=f["origen_id"])
                for f in objeto.get("fuentes", [])
            ),
            circuitos=tuple(
                Circuito(id=c["id"], tablero=c["tablero"], numero=c["numero"],
                         conductores=tuple(c["conductores"]), calibre=c["calibre"],
                         puntos_maximos=c["puntos_maximos"], orden=tuple(c["orden"]))
                for c in objeto.get("circuitos", [])
            ),
            puntos=tuple(
                Punto(id=p["id"], nombre=p["nombre"], especialidad=p["especialidad"],
                      tipo=p["tipo"], ambiente_id=p["ambiente_id"], superficie=p["superficie"],
                      posicion=coord(p["posicion"]), fuente_id=p.get("fuente_id"),
                      circuito_id=p.get("circuito_id"), especificaciones=p["especificaciones"],
                      origen_id=p["origen_id"])
                for p in objeto.get("puntos", [])
            ),
            recorridos=tuple(
                Recorrido(
                    id=r["id"], modo=r["modo"], punto_id=r.get("punto_id"),
                    circuito_id=r.get("circuito_id"),
                    tramos=tuple(
                        Tramo(orden=t["orden"], superficie=t["superficie"],
                              empotrado=t.get("empotrado"), pendiente=decimal(t.get("pendiente")),
                              vertices=tuple(coord(v) for v in t["vertices"]))
                        for t in r.get("tramos", [])
                    ),
                )
                for r in objeto.get("recorridos", [])
            ),
            sobrescrituras=tuple(
                SobrescrituraSegmento(clave=s["clave"], diametro=s.get("diametro"),
                                      empotrado=s.get("empotrado"))
                for s in objeto.get("sobrescrituras", [])
            ),
        )
    except (KeyError, TypeError) as error:
        raise ValueError(f"anexo de espacio incompleto o mal formado: {error!r}") from None
