"""Siembra errores conocidos en el DXF de OF-001 y en el IFC de oficina (S3 §11.5, RF-89).

Cada categoría del catálogo (`tests/fixtures/errores_planos/catalogo.md`) tiene una siembra
determinista: la semilla (`SEMILLA`), la categoría y el índice de la variante fijan el elemento que
se daña, así que la misma corrida da siempre el mismo plano y la misma lista de lo sembrado.
`scripts/medir_deteccion_planos.py` los audita y mide la tasa de detección.

    uv run python scripts/sembrar_errores_planos.py --salida data/errores_planos/
    uv run python scripts/sembrar_errores_planos.py --listar

El DXF de partida es `tests/fixtures/planos/of001.dxf` (la convención de capas del spec §6.6.1).
OF-001 no tiene IFC: las categorías IFC parten del IFC de oficina de `tests/fixtures`
(`oficina_ifc4`, RP8-5). Necesita los extras `planos` e `ifc`.
"""

from __future__ import annotations

import argparse
import io
import random
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

SEMILLA = 42
VARIANTES_POR_CATEGORIA = 3
RUTA_OF001_DXF = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"
RUTA_CATALOGO = RAIZ / "tests" / "fixtures" / "errores_planos" / "catalogo.md"

__all__ = [
    "SEMILLA",
    "SIEMBRAS",
    "Sembrado",
    "Siembra",
    "catalogo",
    "limpio",
    "sembrar",
]


@dataclass(frozen=True, slots=True)
class FilaDelCatalogo:
    id: str
    categoria: str
    como: str
    deteccion: tuple[str, ...]
    consecuencias: tuple[str, ...]
    detectable: bool
    autor: str


@dataclass(frozen=True, slots=True)
class Sembrado:
    """Un plano con un error sembrado. `referencia`: la segunda fuente de R16 (el plano limpio)."""

    id: str
    variante: int
    formato: str  # dxf | ifc
    contenido: bytes
    detalle: str  # qué elemento se dañó
    referencia: bytes | None = None


@dataclass(frozen=True, slots=True)
class Siembra:
    id: str
    formato: str
    variantes: int
    aplicar: Callable  # (modelo, azar) -> detalle
    con_referencia: bool = False


def _etiquetas(texto: str) -> tuple[str, ...]:
    return () if texto in {"—", ""} else tuple(e.strip() for e in texto.split(";"))


def catalogo(ruta: Path = RUTA_CATALOGO) -> dict[str, FilaDelCatalogo]:
    """Los bloques `### ID` del catálogo, con sus campos `- **Campo:** valor`, por id."""
    campos: dict[str, dict[str, str]] = {}
    actual: dict[str, str] | None = None
    ultimo = ""
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.startswith("### "):
            actual = campos.setdefault(linea[4:].strip(), {})
        elif actual is not None and linea.startswith("- **") and ":** " in linea:
            ultimo, _, valor = linea[4:].partition(":** ")
            actual[ultimo] = valor.strip()
        elif actual is not None and ultimo and linea.startswith("  ") and linea.strip():
            actual[ultimo] += " " + linea.strip()  # un campo que sigue en la línea de abajo
    return {
        id_: FilaDelCatalogo(
            id_, c["Categoría"], c["Cómo se siembra"], _etiquetas(c["Detección esperada"]),
            _etiquetas(c["Consecuencias admitidas"]), c["Detectable"] == "sí", c["Autor"],
        )
        for id_, c in campos.items()
    }


# --- el DXF ------------------------------------------------------------------------------------


def _leer_dxf():
    import ezdxf

    return ezdxf.readfile(RUTA_OF001_DXF)


def _bytes_dxf(doc) -> bytes:
    flujo = io.StringIO()
    doc.write(flujo)
    return flujo.getvalue().encode("utf-8")


def _insertados(doc, prefijo: str):
    return [e for e in doc.modelspace()
            if e.dxftype() == "INSERT" and e.dxf.layer.startswith(prefijo)]


def _id_de(insercion) -> str:
    return next(a.dxf.text for a in insercion.attribs if a.dxf.tag == "ID")


def _elegir(doc, prefijo: str, azar: random.Random):
    return azar.choice(sorted(_insertados(doc, prefijo), key=_id_de))


def _mover(insercion, dx: float = 0.0, dy: float = 0.0) -> None:
    x, y, z = insercion.dxf.insert
    insercion.dxf.insert = (x + dx, y + dy, z)
    for atributo in insercion.attribs:
        ax, ay, az = atributo.dxf.insert
        atributo.dxf.insert = (ax + dx, ay + dy, az)


def _sin_unidad(doc, azar):
    doc.header["$INSUNITS"] = 0
    return "sin $INSUNITS"


def _entidad_danada(doc, azar):
    x, y = azar.choice((1, 2, 3, 4, 5)), azar.choice((1, 2, 3, 4, 5))
    doc.modelspace().add_line((x, y), (x + 1, y), dxfattribs={
        "layer": "OTRA", "linetype": "NO_EXISTE"})
    return f"línea en ({x}; {y}) con un tipo de línea que no existe"


def _capa_equivocada(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    punto.dxf.layer = "PTO-DATO"
    return f"punto {_id_de(punto)} en la capa PTO-DATO"


def _altura_faltante(doc, azar):
    punto = _elegir(doc, "PTO-", azar)
    punto.attribs[:] = [a for a in punto.attribs if a.dxf.tag != "ALTURA"]
    return f"punto {_id_de(punto)} sin ALTURA"


def _escala(doc, azar):
    from ezdxf.math import Matrix44

    factor = azar.choice((250, 500, 1000))
    for entidad in doc.modelspace():
        entidad.transform(Matrix44.scale(factor, factor, factor))
    return f"dibujo × {factor}"


def _superpuesto(doc, azar):
    s = azar.choice((0.5, 0.4, 0.3))
    x0, y0 = 6 - s, 4 - s
    msp = doc.modelspace()
    msp.add_lwpolyline([(x0, y0), (x0 + 2, y0), (x0 + 2, y0 + 2), (x0, y0 + 2)], close=True,
                       dxfattribs={"layer": "AMBIENTES"})
    msp.add_text("ZX", dxfattribs={"layer": "AMBIENTES", "insert": (x0 + 1.5, y0 + 1.5, 0)})
    return f"ambiente ZX que pisa {s:g} m de ZA y de ZB"


def _punto_duplicado(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    copia = punto.copy()
    doc.modelspace().add_entity(copia)
    for atributo in copia.attribs:
        if atributo.dxf.tag == "ID":
            atributo.dxf.text = _id_de(punto) + "D"
    return f"punto {_id_de(punto)} copiado como {_id_de(punto)}D"


def _fuera_de_ambiente(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    desde = punto.dxf.insert
    _mover(punto, 30 - desde[0], 30 - desde[1])
    return f"punto {_id_de(punto)} en (30; 30)"


def _sin_fuente(doc, azar):
    capa = azar.choice(("FTE-DATOS", "FTE-ELEC"))
    for e in list(_insertados(doc, capa)):
        doc.modelspace().delete_entity(e)
    return f"se borra la fuente de la capa {capa}"


def _elemento_borrado(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    ident = _id_de(punto)
    doc.modelspace().delete_entity(punto)
    return f"punto {ident} borrado"


def _desplazado(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    hacia = -0.5 if punto.dxf.insert[0] > 3 else 0.5  # hacia el interior de su ambiente
    _mover(punto, hacia, 0.0)
    return f"punto {_id_de(punto)} corrido 0,50 m hacia el interior de su ambiente"


def _traslado(doc, azar):
    dx, dy = azar.choice(((0.5, 0.0), (0.0, 0.5), (0.5, 0.5)))
    for e in doc.modelspace():
        e.translate(dx, dy, 0)
    return f"todo el dibujo corrido ({dx:g}; {dy:g}) m"


def _permuta(doc, azar):
    a, b = (e for e in _insertados(doc, "PTO-DATOS") if _id_de(e) in {"PA1", "PA2"})
    for e, nuevo in ((a, _id_de(b)), (b, _id_de(a))):
        for atributo in e.attribs:
            if atributo.dxf.tag == "ID":
                atributo.dxf.text = nuevo
    return "PA1 y PA2 cambian de id"


def _luces(doc, azar):
    for e in _insertados(doc, "PTO-LUZ"):
        _mover(e, 0.0, 0.3)
    return "las cuatro luminarias corridas 0,30 m en y"


# --- el IFC de oficina -------------------------------------------------------------------------


def _ifc(faltante: str):
    def aplicar(_modelo, _azar):
        return f"el IFC de oficina sin {faltante}"

    return aplicar


def _crear_ifc(sin: str | None) -> bytes:
    from tests.fixtures.planos_ifc_ids import REQUISITOS, oficina_ifc4

    modelo = oficina_ifc4(tuple(r for r in REQUISITOS if r != sin))
    return modelo.to_string().encode("utf-8")


SIEMBRAS: dict[str, Siembra] = {s.id: s for s in (
    Siembra("SIN-UNIDAD", "dxf", 1, _sin_unidad),
    Siembra("ENTIDAD-DANADA", "dxf", VARIANTES_POR_CATEGORIA, _entidad_danada),
    Siembra("CAPA-EQUIVOCADA", "dxf", VARIANTES_POR_CATEGORIA, _capa_equivocada),
    Siembra("ALTURA-FALTANTE", "dxf", VARIANTES_POR_CATEGORIA, _altura_faltante),
    Siembra("ESCALA-X1000", "dxf", VARIANTES_POR_CATEGORIA, _escala),
    Siembra("SUPERPUESTO", "dxf", VARIANTES_POR_CATEGORIA, _superpuesto),
    Siembra("PUNTO-DUPLICADO", "dxf", VARIANTES_POR_CATEGORIA, _punto_duplicado),
    Siembra("FUERA-DE-AMBIENTE", "dxf", VARIANTES_POR_CATEGORIA, _fuera_de_ambiente),
    Siembra("SIN-FUENTE", "dxf", VARIANTES_POR_CATEGORIA, _sin_fuente),
    Siembra("IFC-SIN-ALTURA", "ifc", 1, _ifc("altura")),
    Siembra("IFC-SIN-DIAMETRO", "ifc", 1, _ifc("diametro")),
    Siembra("IFC-SIN-CIRCUITO", "ifc", 1, _ifc("circuito")),
    Siembra("ELEMENTO-BORRADO", "dxf", VARIANTES_POR_CATEGORIA, _elemento_borrado, True),
    Siembra("DESPLAZADO-0-50", "dxf", VARIANTES_POR_CATEGORIA, _desplazado, True),
    Siembra("NO-DET-TRASLADO", "dxf", VARIANTES_POR_CATEGORIA, _traslado),
    Siembra("NO-DET-PERMUTA", "dxf", 1, _permuta),
    Siembra("NO-DET-LUCES", "dxf", 1, _luces),
)}
_FALTANTE_IFC = {"IFC-SIN-ALTURA": "altura", "IFC-SIN-DIAMETRO": "diametro",
                 "IFC-SIN-CIRCUITO": "circuito"}


def limpio(formato: str) -> bytes:
    """El plano sin errores del que parten todas las siembras."""
    return _bytes_dxf(_leer_dxf()) if formato == "dxf" else _crear_ifc(None)


def sembrar(id_: str, variante: int = 0, semilla: int = SEMILLA) -> Sembrado:
    """El plano con el error `id_` sembrado en su `variante`-ésima forma."""
    siembra = SIEMBRAS[id_]
    azar = random.Random(f"{semilla}:{id_}:{variante}")
    if siembra.formato == "ifc":
        detalle = siembra.aplicar(None, azar)
        return Sembrado(id_, variante, "ifc", _crear_ifc(_FALTANTE_IFC[id_]), detalle)
    doc = _leer_dxf()
    detalle = siembra.aplicar(doc, azar)
    return Sembrado(id_, variante, "dxf", _bytes_dxf(doc), detalle,
                    limpio("dxf") if siembra.con_referencia else None)


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--salida", type=Path, help="carpeta donde escribir los planos")
    analizador.add_argument("--listar", action="store_true", help="solo lista lo que se siembra")
    args = analizador.parse_args(argv)
    for id_, siembra in SIEMBRAS.items():
        for variante in range(siembra.variantes):
            sembrado = sembrar(id_, variante)
            print(f"{id_}#{variante}: {sembrado.detalle}")
            if args.salida and not args.listar:
                args.salida.mkdir(parents=True, exist_ok=True)
                (args.salida / f"{id_}-{variante}.{sembrado.formato}").write_bytes(
                    sembrado.contenido)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
