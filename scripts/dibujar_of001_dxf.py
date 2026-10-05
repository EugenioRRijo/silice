"""Dibuja `tests/fixtures/planos/of001.dxf` entidad por entidad desde las memorias a mano.

Oraculo INDEPENDIENTE de la importacion de planos (spec 11.1 y 6.6.1): lee las TABLAS markdown de
`tests/fixtures/memorias/of001.md` (secciones 1.1 a 1.4), `bano_of001.md` y
`bano_drenaje_of001.md` y
escribe cada polilinea, texto y bloque con `ezdxf`. NO importa nada de `adapters/` ni de
`tests/fixtures/espacio_of001.py` (la hoja manual): si lo hiciera, la prueba de equivalencia seria
circular. Una prueba (`test_planos_dxf_of001.py`) vigila esa independencia.

Lo que dibuja, segun la convencion de capas (spec 6.6.1):

* `AMBIENTES`: una polilinea cerrada por ambiente con su identificador como texto adentro.
* `FTE-AGUA`, `FTE-DRENAJE`, `FTE-DATOS`, `FTE-ELEC`: un bloque por fuente (atributos `ID`, `ALTURA`
  y `AMBIENTE` solo si el punto cae en el borde de dos ambientes).
* `PTO-AGUA`, `PTO-DRENAJE`, `PTO-DATOS`, `PTO-TOMA`, `PTO-LUZ`: un bloque por punto con `ID`,
  `ALTURA`
  y los opcionales `DIAMETRO`, `CALIBRE`, `CIRCUITO`, `CATEGORIA`, `LLAVE` y `AMBIENTE` (solo si es
  ambiguo). `ALTURA` es la cota z del punto, en las unidades del dibujo (metros, `$INSUNITS` = 6).

La altura de los AMBIENTES no se dibuja: queda pendiente (spec 6.6.1) y se carga al importar.

Uso: `uv run python scripts/dibujar_of001_dxf.py [--salida RUTA]` (necesita el extra `planos`).
Sin `--salida` escribe `tests/fixtures/planos/of001.dxf`.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import ezdxf

RAIZ = Path(__file__).resolve().parents[1]
MEMORIAS = RAIZ / "tests" / "fixtures" / "memorias"
SALIDA = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"
TOLERANCIA = Decimal("0.001")

#: Capa y bloque de cada fuente segun «especialidad, tipo» de la memoria (seccion 1.2).
FUENTES = {
    "agua, montante de agua": ("FTE-AGUA", "MONTANTE_AGUA"),
    "agua, colector de drenaje": ("FTE-DRENAJE", "COLECTOR_DRENAJE"),
    "datos, rack": ("FTE-DATOS", "RACK"),
    "electricidad, tablero": ("FTE-ELEC", "TABLERO"),
}
#: Capa de cada tipo de punto de la memoria.
CAPA_PUNTO = {
    "agua fría": "PTO-AGUA",
    "drenaje": "PTO-DRENAJE",
    "datos": "PTO-DATOS",
    "tomacorriente": "PTO-TOMA",
    "iluminación": "PTO-LUZ",
}
ATRIBUTOS_PUNTO = (
    "ID",
    "ALTURA",
    "DIAMETRO",
    "CALIBRE",
    "CIRCUITO",
    "CATEGORIA",
    "LLAVE",
    "AMBIENTE",
)


@dataclass(frozen=True)
class Ambiente:
    id: str
    x0: Decimal
    y0: Decimal
    largo: Decimal
    ancho: Decimal

    def toca(self, x: Decimal, y: Decimal) -> bool:
        t = TOLERANCIA
        return (
            self.x0 - t <= x <= self.x0 + self.largo + t
            and self.y0 - t <= y <= self.y0 + self.ancho + t
        )


@dataclass(frozen=True)
class Bloque:
    capa: str
    bloque: str
    atributos: dict[str, str]
    x: Decimal
    y: Decimal


def _num(texto: str) -> Decimal:
    return Decimal(texto.strip().replace(",", ".").replace("−", "-"))


def _terna(texto: str) -> tuple[Decimal, Decimal, Decimal]:
    """«(1; 1,5; 0,9)» -> (1, 1.5, 0.9). La memoria separa con «;» y usa coma decimal."""
    partes = re.search(r"\(([^)]*)\)", texto)
    assert partes, f"sin terna de coordenadas en {texto!r}"
    x, y, z = (_num(p) for p in partes.group(1).replace(",", ".").split(";"))
    return x, y, z


def _celdas(linea: str) -> list[str]:
    return [c.strip().strip("`").strip() for c in linea.strip().strip("|").split("|")]


def _seccion(texto: str, encabezado: str) -> list[list[str]]:
    """Filas (celdas) de la primera tabla bajo el encabezado `### <encabezado>`."""
    inicio = texto.index(f"### {encabezado}")
    cuerpo = texto[inicio:].split("\n")[1:]
    filas: list[list[str]] = []
    for linea in cuerpo:
        if linea.startswith("#"):
            break
        if linea.startswith("|"):
            celdas = _celdas(linea)
            if not set("".join(celdas)) <= set("-: "):
                filas.append(celdas)
    return filas


def _tablas_de_puntos(texto: str, encabezado: str) -> list[list[list[str]]]:
    """Todas las tablas (separadas por lineas en blanco) bajo el encabezado `### <encabezado>`."""
    inicio = texto.index(f"### {encabezado}")
    cuerpo = texto[inicio:].split("\n")[1:]
    tablas: list[list[list[str]]] = []
    actual: list[list[str]] = []
    for linea in cuerpo:
        if linea.startswith("#") or linea.startswith("```"):
            break
        if linea.startswith("|"):
            celdas = _celdas(linea)
            if not set("".join(celdas)) <= set("-: "):
                actual.append(celdas)
        elif actual:
            tablas.append(actual)
            actual = []
    if actual:
        tablas.append(actual)
    return tablas


def leer_ambientes(texto: str) -> list[Ambiente]:
    filas = _seccion(texto, "1.1 Ambientes")[1:]
    return [Ambiente(f[0], _num(f[2]), _num(f[3]), _num(f[4]), _num(f[5])) for f in filas]


def leer_fuentes(texto: str) -> list[tuple[str, str, str, tuple[Decimal, Decimal, Decimal]]]:
    filas = _seccion(texto, "1.2 Fuentes")[1:]
    return [(f[0], f[1], f[2], _terna(f[3])) for f in filas]


def leer_circuitos(texto: str) -> dict[str, str]:
    """Calibre por circuito, de la tabla 1.4 («| C1 | T1 | 1 | (1; 1; 1) | 12 AWG | 6 | ...»)."""
    filas = _seccion(texto, "1.4 Circuitos")[1:]
    return {f[0]: f[4] for f in filas}


def _diametro(texto: str) -> str | None:
    m = re.search(r"di[aá]metro\s+(\d+(?:\s\d+)?(?:/\d+)?\")", texto)
    return m.group(1) if m else None


def puntos_del_bano(bano: str, drenaje: str) -> list[dict]:
    """P1, P2 (`bano_of001.md`) y D1, D2 (`bano_drenaje_of001.md`): filas «| Punto | `P1` |...»."""
    puntos = []
    for texto in (bano, drenaje):
        for linea in texto.splitlines():
            celdas = _celdas(linea) if linea.startswith("| Punto |") else []
            if not celdas:
                continue
            id_, datos = celdas[1], celdas[2]
            tipo = "drenaje" if "drenaje" in datos else "agua fría"
            puntos.append(
                {
                    "id": id_,
                    "capa": CAPA_PUNTO[tipo],
                    "terna": _terna(datos),
                    "DIAMETRO": _diametro(datos),
                    "LLAVE": "si" if "llave de paso" in datos and "Ni" not in datos else None,
                    "ambiente": "BAN-01",
                }
            )
    return puntos


def puntos_de_la_oficina(texto: str, calibres: dict[str, str]) -> list[dict]:
    puntos: list[dict] = []
    tablas = _tablas_de_puntos(texto, "1.3 Puntos")
    # tabla 0: cocineta (agua); tabla 1: datos; tabla 2: electricidad
    for f in tablas[0][1:]:
        tipo = "drenaje" if "drenaje" in f[1] else "agua fría"
        puntos.append(
            {
                "id": f[0],
                "capa": CAPA_PUNTO[tipo],
                "terna": _terna(f[4]),
                "DIAMETRO": _diametro(f[6]),
                "LLAVE": "si" if "llave de paso" in f[6] else None,
                "ambiente": f[2],
            }
        )
    for f in tablas[1][1:]:
        explicita = re.search(r"cat\s*\d+[a-z]?", f[4])
        puntos.append(
            {
                "id": f[0],
                "capa": "PTO-DATOS",
                "terna": _terna(f[2]),
                "DIAMETRO": f[3],
                "CATEGORIA": explicita.group(0) if explicita else None,
                "ambiente": f[1],
            }
        )
    for f in tablas[2][1:]:
        puntos.append(
            {
                "id": f[0],
                "capa": CAPA_PUNTO[f[1]],
                "terna": _terna(f[4]),
                "DIAMETRO": f[6],
                "CIRCUITO": f[5],
                "CALIBRE": calibres[f[5]],
                "ambiente": f[2],
            }
        )
    return puntos


def _ambiguo(ambientes: list[Ambiente], x: Decimal, y: Decimal) -> bool:
    return sum(1 for a in ambientes if a.toca(x, y)) > 1


def _texto(valor: Decimal) -> str:
    return format(valor.normalize(), "f")


def dibujar(salida: Path = SALIDA) -> Path:
    """Escribe el DXF de OF-001 en `salida` y devuelve la ruta."""
    of001 = (MEMORIAS / "of001.md").read_text(encoding="utf-8")
    bano = (MEMORIAS / "bano_of001.md").read_text(encoding="utf-8")
    drenaje = (MEMORIAS / "bano_drenaje_of001.md").read_text(encoding="utf-8")
    ambientes = leer_ambientes(of001)
    calibres = leer_circuitos(of001)

    ezdxf.options.write_fixed_meta_data_for_testing = True  # fechas y GUID fijos
    doc = ezdxf.new("R2010")
    doc.units = 6  # metros ($INSUNITS = 6)
    for capa in ("AMBIENTES", *(c for c, _ in FUENTES.values()), *CAPA_PUNTO.values()):
        if capa not in doc.layers:
            doc.layers.add(capa)
    for bloque in sorted({b for _, b in FUENTES.values()} | {"PUNTO"}):  # orden fijo
        definicion = doc.blocks.new(bloque)
        definicion.add_circle((0, 0), 0.05)
        for i, tag in enumerate(ATRIBUTOS_PUNTO):
            definicion.add_attdef(tag, (0.06, 0.06 - i * 0.02), "", dxfattribs={"height": 0.015})
    msp = doc.modelspace()

    for a in ambientes:
        x1, y1 = a.x0 + a.largo, a.y0 + a.ancho
        msp.add_lwpolyline(
            [
                (float(a.x0), float(a.y0)),
                (float(x1), float(a.y0)),
                (float(x1), float(y1)),
                (float(a.x0), float(y1)),
            ],  # fmt: skip
            close=True,
            dxfattribs={"layer": "AMBIENTES"},
        )
        msp.add_text(
            a.id,
            height=0.12,
            dxfattribs={
                "layer": "AMBIENTES",
                "insert": (float(a.x0 + a.largo / 2), float(a.y0 + a.ancho / 2)),
            },
        )

    bloques: list[Bloque] = []
    for id_, clase, ambiente, (x, y, z) in leer_fuentes(of001):
        capa, nombre = FUENTES[clase]
        atributos = {"ID": id_, "ALTURA": _texto(z)}
        if _ambiguo(ambientes, x, y):
            atributos["AMBIENTE"] = ambiente
        bloques.append(Bloque(capa, nombre, atributos, x, y))
    for p in puntos_del_bano(bano, drenaje) + puntos_de_la_oficina(of001, calibres):
        x, y, z = p["terna"]
        atributos = {"ID": p["id"], "ALTURA": _texto(z)}
        for clave in ("DIAMETRO", "CALIBRE", "CIRCUITO", "CATEGORIA", "LLAVE"):
            if p.get(clave):
                atributos[clave] = p[clave]
        if _ambiguo(ambientes, x, y):
            atributos["AMBIENTE"] = p["ambiente"]
        bloques.append(Bloque(p["capa"], "PUNTO", atributos, x, y))

    for b in bloques:
        ref = msp.add_blockref(
            b.bloque, (float(b.x), float(b.y), 0.0), dxfattribs={"layer": b.capa}
        )
        for i, tag in enumerate(ATRIBUTOS_PUNTO):
            if tag in b.atributos:
                ref.add_attrib(
                    tag,
                    b.atributos[tag],
                    (float(b.x) + 0.06, float(b.y) + 0.06 - i * 0.02),
                    dxfattribs={"layer": b.capa, "height": 0.015},
                )

    salida.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(salida)
    return salida


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dibujar_of001_dxf.py", description=__doc__.split("\n")[0]
    )
    parser.add_argument("--salida", type=Path, default=SALIDA, help="ruta del DXF a escribir")
    args = parser.parse_args(argv)
    print(f"escrito {dibujar(args.salida)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
