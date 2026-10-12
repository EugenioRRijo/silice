"""Genera `data/ids/silice_instalaciones.ids` (spec S3 §11.2). Determinista: sin fecha del reloj.

Uso: `uv run --extra ifc python scripts/generar_ids_silice.py` (escribe el archivo) o
`... --comprobar` (sale 1 si el archivo versionado difiere del que se generaría).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
DESTINO = RAIZ / "data" / "ids" / "silice_instalaciones.ids"
FECHA = "2026-10-11"  # fija: el archivo versionado no cambia entre corridas


def generar() -> str:
    from ifctester import ids

    from adapters.espacio.planos.ids import esquema_sin_red

    esquema_sin_red(ids)
    conjunto = ids.Ids(
        title="Silice: requisitos minimos de una instalacion", version="1.0", date=FECHA,
        author="silice@invalid.example",
        description="Lo que la hoja de metrajes necesita y la geometria de un IFC no da.",
    )

    def especificacion(nombre: str, descripcion: str, aplica, requisito):
        espec = ids.Specification(
            name=nombre, ifcVersion=["IFC4"], minOccurs=0, maxOccurs="unbounded",
            description=descripcion,
        )
        espec.applicability.append(aplica)
        espec.requirements.append(requisito)
        conjunto.specifications.append(espec)

    especificacion(
        "Espacio con altura", "La altura del espacio, para las cantidades verticales.",
        ids.Entity(name="IFCSPACE"),
        ids.Property(propertySet="Qto_SpaceBaseQuantities", baseName="Height",
                     cardinality="required"),
    )
    especificacion(
        "Aparato sanitario con diametro", "El diametro nominal de la tuberia que lo sirve.",
        ids.Entity(name="IFCSANITARYTERMINAL"),
        ids.Property(propertySet="Silice_Hoja", baseName="DiametroNominal",
                     cardinality="required"),
    )
    especificacion(
        "Tomacorriente con circuito", "El circuito al que pertenece, para agrupar los puntos.",
        ids.Entity(name="IFCOUTLET", predefinedType="POWEROUTLET"),
        ids.Property(propertySet="Silice_Hoja", baseName="Circuito", cardinality="required"),
    )
    especificacion(
        "Tablero con nombre", "El nombre del tablero, que es la fuente de sus circuitos.",
        ids.Entity(name="IFCELECTRICDISTRIBUTIONBOARD"),
        ids.Attribute(name="Name", cardinality="required"),
    )
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    conjunto.to_xml(str(DESTINO))
    return DESTINO.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comprobar", action="store_true")
    args = parser.parse_args(argv)
    previo = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else None
    nuevo = generar()
    if args.comprobar and previo != nuevo:
        DESTINO.write_text(previo or "", encoding="utf-8")
        print("data/ids/silice_instalaciones.ids difiere de lo que generaria el script")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
