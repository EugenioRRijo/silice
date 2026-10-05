"""Cálculo independiente de la memoria `of001.md` (SF2), con fracciones exactas.

Solo importa la biblioteca estándar: no usa nada de `adapters/` ni de `core/`. Lee el bloque JSON de
`of001.md` (posiciones, orden de las cadenas y diámetros por punto), reconstruye los recorridos
(sube al techo, cruza en x, cruza en y, baja; el tramo de largo cero se omite), une los segmentos
partiéndolos en cada nodo y calcula longitudes, cable y conductor.
`tests/unit/test_memoria_of001.py`
compara este resultado con las cifras del mismo bloque JSON.

Ejecutable: `python tests/fixtures/memorias/calculo_of001.py` imprime el resumen.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

MEMORIA = Path(__file__).resolve().parent / "of001.md"

#: Diámetro de la canalización declarado por cada punto (tablas de la sección 1.3 de la memoria).
DIAMETRO_PUNTO = {
    **dict.fromkeys(("PA1", "PA2", "PA3", "PB1", "PB2", "PB3"), "3/4"),
    "PR1": "1/2",
    "C1": "3/4",
    "C2": "1/2",
}

Punto3 = tuple[Fraction, Fraction, Fraction]


def cargar() -> dict:
    texto = MEMORIA.read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", texto, flags=re.DOTALL)[0])


def _pos(memoria: dict, nombre: str) -> Punto3:
    x, y, z = (Fraction(v) for v in memoria["posiciones"][nombre])
    return x, y, z


def _paso(memoria: dict, a: str, b: str) -> list[tuple[Punto3, Punto3]]:
    """Segmentos de un paso a -> b: sube, cruza en x, cruza en y, baja (sin largo cero)."""
    techo = Fraction(memoria["techo"])
    (ax, ay, az), (bx, by, bz) = _pos(memoria, a), _pos(memoria, b)
    nodos = [(ax, ay, az), (ax, ay, techo), (bx, ay, techo), (bx, by, techo), (bx, by, bz)]
    return [(p, q) for p, q in zip(nodos, nodos[1:], strict=False) if p != q]


def _largo(seg: tuple[Punto3, Punto3]) -> Fraction:
    return sum((abs(q - p) for p, q in zip(*seg, strict=True)), Fraction(0))


def _clave(fuente: str, seg: tuple[Punto3, Punto3]) -> str:
    a, b = sorted(seg)
    return "|".join(
        [fuente] + [",".join(f"{float(c):.3f}" for c in p) for p in (a, b)]
    )  # tres decimales, como la memoria


def _unir(
    fuente: str, caminos: dict[str, list[tuple[Punto3, Punto3]]], diametros: dict[str, str]
) -> list[dict]:
    """Une los caminos partiendo cada segmento en los nodos que caen dentro de él."""
    nodos = {p for segs in caminos.values() for s in segs for p in s}

    def partir(seg: tuple[Punto3, Punto3]) -> list[tuple[Punto3, Punto3]]:
        a, b = sorted(seg)
        dentro = [
            n
            for n in nodos
            if n not in (a, b)
            and all(min(p, q) <= c <= max(p, q) for c, p, q in zip(n, a, b, strict=True))
            and sum(1 for p, q in zip(a, b, strict=True) if p != q) == 1
            and all(c == p for c, p, q in zip(n, a, b, strict=True) if p == q)
        ]
        corte = [a, *sorted(dentro), b]
        return [(p, q) for p, q in zip(corte, corte[1:], strict=False)]

    sirve: dict[tuple[Punto3, Punto3], set[str]] = defaultdict(set)
    for quien, segs in caminos.items():
        for s in segs:
            for trozo in partir(s):
                sirve[trozo].add(quien)
    return [
        {
            "clave": _clave(fuente, s),
            "longitud": _largo(s),
            "diametro": max((diametros[q] for q in quienes), key=Fraction),
            "sirve": sorted(quienes),
        }
        for s, quienes in sorted(sirve.items())
    ]


def _resumen(segmentos: list[dict]) -> tuple[Fraction, dict[str, Fraction]]:
    por_diametro: dict[str, Fraction] = defaultdict(Fraction)
    for s in segmentos:
        por_diametro[s["diametro"]] += s["longitud"]
    return sum(por_diametro.values(), Fraction(0)), dict(por_diametro)


def _cadena_vecino_mas_cercano(memoria: dict, puntos: list[str]) -> list[str]:
    restantes, actual, orden = sorted(puntos), "T1", []
    while restantes:
        elegido = min(
            restantes,
            key=lambda p: (sum((_largo(s) for s in _paso(memoria, actual, p)), Fraction(0)), p),
        )
        orden.append(elegido)
        restantes.remove(elegido)
        actual = elegido
    return orden


def calcular(memoria: dict | None = None) -> dict:
    """Todas las cifras de OF-001 que se pueden derivar de las posiciones, en `Fraction`."""
    memoria = memoria or cargar()
    k = memoria["constantes"]
    holgura = Fraction(k["holgura_rack"]) + Fraction(k["holgura_punto"])

    # --- datos
    puntos_datos = sorted(memoria["datos"]["recorridos"])
    caminos_d = {p: _paso(memoria, "RK1", p) for p in puntos_datos}
    recorrido = {p: sum((_largo(s) for s in segs), Fraction(0)) for p, segs in caminos_d.items()}
    seg_d = _unir("RK1", caminos_d, DIAMETRO_PUNTO)
    unida_d, por_diametro_d = _resumen(seg_d)
    datos = {
        "recorrido": recorrido,
        "sin_unir": sum(recorrido.values(), Fraction(0)),
        "unida": unida_d,
        "por_diametro": por_diametro_d,
        "segmentos": seg_d,
        "cable": sum(
            ((r + holgura) * (1 + Fraction(k["reserva_cable"])) for r in recorrido.values()),
            Fraction(0),
        ),
    }

    # --- electricidad (el orden de C2 sale del vecino más cercano; el de C1 es el declarado)
    circuitos = memoria["electricidad"]["circuitos"]
    ordenes = {
        c: (d["orden"] if c == "C1" else _cadena_vecino_mas_cercano(memoria, d["orden"]))
        for c, d in circuitos.items()
    }
    caminos_e: dict[str, list[tuple[Punto3, Punto3]]] = {}
    cadena: dict[str, Fraction] = {}
    for c, orden in ordenes.items():
        segs: list[tuple[Punto3, Punto3]] = []
        anterior = "T1"
        for p in orden:
            segs.extend(_paso(memoria, anterior, p))
            anterior = p
        caminos_e[c] = segs
        cadena[c] = sum((_largo(s) for s in segs), Fraction(0))
    seg_e = _unir("T1", caminos_e, DIAMETRO_PUNTO)
    unida_e, por_diametro_e = _resumen(seg_e)
    desperdicio = 1 + Fraction(k["desperdicio_conductor"])
    elec = {
        "ordenes": ordenes,
        "cadena": cadena,
        "sin_unir": sum(cadena.values(), Fraction(0)),
        "unida": unida_e,
        "por_diametro": por_diametro_e,
        "segmentos": seg_e,
        "conductor": {
            circuitos[c]["calibre"]: cadena[c] * sum(circuitos[c]["conductores"]) * desperdicio
            for c in circuitos
        },
    }
    return {"datos": datos, "electricidad": elec}


def main() -> None:
    r = calcular()
    for nombre in ("datos", "electricidad"):
        b = r[nombre]
        print(nombre, "sin unir", float(b["sin_unir"]), "unida", float(b["unida"]))
    print("cable cat 6", float(r["datos"]["cable"]))
    print({k: float(v) for k, v in r["electricidad"]["conductor"].items()})


if __name__ == "__main__":
    main()
