"""Genera `data/samples/tanquilla.ifc`: el modelo IFC de muestra de la Sesion I3.1 (compuerta G1).

Construye, con ifcopenshell, un unico elemento (`IfcBuildingElementProxy` "Tanquilla") que
representa una tanquilla cuadrada de paredes macizas: lado exterior `a`, altura `h` y espesor de
pared `e`. El solido es la extrusion del anillo cuadrado (cuadrado exterior a x a menos el hueco
interior (a-2e) x (a-2e)) usando `IfcArbitraryProfileDefWithVoids`, para que el visor 3D de la
Sesion T7 tenga geometria real que teselar.

El elemento lleva:
- `Pset_APU`: COVENIN_Codigo, Partida_Descripcion, Unidad — la trazabilidad hacia la partida del
  presupuesto (2026-08-31-f1-api-simulador-design.md, seccion 7).
- `Qto_APU`: VolumenConcreto, calculado con `Decimal` -- (a**2 - (a - 2*e)**2) * h -- la misma
  formula de I3.2 que produce 0,224 m3 para a=h=0,80 y e=0,10 (tests/unit/test_reglas_civil.py).
  IFC solo admite `float` en sus magnitudes: se convierte al final, no antes, y el valor
  sobrevive el viaje de ida y vuelta (`Decimal(str(valor)) == Decimal("0.224")`).

El archivo generado es reemplazable por un export real de Revit/Bonsai: el adaptador civil
(`adapters/civil/ifc.py`, Tarea 6) no distingue el productor, solo lee Pset_APU y el
IfcElementQuantity.

Uso:
    uv run python scripts/generar_tanquilla_ifc.py  # crea data/samples/tanquilla.ifc
    uv run python scripts/generar_tanquilla_ifc.py --salida otra.ifc  # otra ruta
    uv run python scripts/generar_tanquilla_ifc.py --a 0.80 --h 0.80 --e 0.10
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

# Ejecutado como `python scripts/generar_tanquilla_ifc.py`, sys.path[0] es scripts/, no la raiz
# del repositorio (pyproject declara `package = false`). pytest lo arregla con
# `pythonpath = ["."]`; aqui se hace explicito antes de que el modulo se ejecute como script.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import ifcopenshell  # noqa: E402
import ifcopenshell.api.aggregate  # noqa: E402
import ifcopenshell.api.context  # noqa: E402
import ifcopenshell.api.geometry  # noqa: E402
import ifcopenshell.api.project  # noqa: E402
import ifcopenshell.api.pset  # noqa: E402
import ifcopenshell.api.root  # noqa: E402
import ifcopenshell.api.spatial  # noqa: E402
import ifcopenshell.api.unit  # noqa: E402
from ifcopenshell.util.shape_builder import ShapeBuilder  # noqa: E402

RUTA_POR_DEFECTO = Path("data/samples/tanquilla.ifc")

A_POR_DEFECTO = Decimal("0.80")
H_POR_DEFECTO = Decimal("0.80")
E_POR_DEFECTO = Decimal("0.10")

CODIGO_COVENIN = "LB-04-CON"
DESCRIPCION_PARTIDA = "Vaciado de concreto en tanquilla"
UNIDAD_PARTIDA = "m3"


def calcular_volumen_concreto(a: Decimal, h: Decimal, e: Decimal) -> Decimal:
    """Volumen del anillo cuadrado macizo: (a^2 - (a - 2e)^2) * h, con `Decimal` sin redondeos."""
    return (a**2 - (a - 2 * e) ** 2) * h


def generar(
    ruta: Path, a: Decimal = A_POR_DEFECTO, h: Decimal = H_POR_DEFECTO, e: Decimal = E_POR_DEFECTO
) -> None:
    """Construye el modelo IFC de la tanquilla y lo escribe en `ruta`.

    :param ruta: archivo .ifc de salida (se crean los directorios padres si faltan).
    :param a: lado exterior de la tanquilla, en metros.
    :param h: altura de la tanquilla, en metros.
    :param e: espesor de pared, en metros.
    """
    volumen = calcular_volumen_concreto(a, h, e)

    modelo = ifcopenshell.api.project.create_file(version="IFC4")

    proyecto = ifcopenshell.api.root.create_entity(
        modelo, ifc_class="IfcProject", name="Tanquilla de muestra"
    )
    longitud = ifcopenshell.api.unit.add_si_unit(modelo, unit_type="LENGTHUNIT")
    area = ifcopenshell.api.unit.add_si_unit(modelo, unit_type="AREAUNIT")
    volumen_unidad = ifcopenshell.api.unit.add_si_unit(modelo, unit_type="VOLUMEUNIT")
    ifcopenshell.api.unit.assign_unit(modelo, units=[longitud, area, volumen_unidad])

    contexto_modelo = ifcopenshell.api.context.add_context(modelo, context_type="Model")
    contexto_cuerpo = ifcopenshell.api.context.add_context(
        modelo,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=contexto_modelo,
    )

    sitio = ifcopenshell.api.root.create_entity(modelo, ifc_class="IfcSite", name="Sitio")
    edificacion = ifcopenshell.api.root.create_entity(
        modelo, ifc_class="IfcBuilding", name="Clinica"
    )
    nivel = ifcopenshell.api.root.create_entity(
        modelo, ifc_class="IfcBuildingStorey", name="Nivel 0"
    )
    ifcopenshell.api.aggregate.assign_object(modelo, products=[sitio], relating_object=proyecto)
    ifcopenshell.api.aggregate.assign_object(modelo, products=[edificacion], relating_object=sitio)
    ifcopenshell.api.aggregate.assign_object(modelo, products=[nivel], relating_object=edificacion)

    tanquilla = ifcopenshell.api.root.create_entity(
        modelo, ifc_class="IfcBuildingElementProxy", name="Tanquilla"
    )
    ifcopenshell.api.spatial.assign_container(
        modelo, products=[tanquilla], relating_structure=nivel
    )

    a_f, h_f, e_f = float(a), float(h), float(e)
    lado_exterior = a_f
    lado_interior = a_f - 2 * e_f
    generador_forma = ShapeBuilder(modelo)
    curva_exterior = generador_forma.rectangle(
        size=(lado_exterior, lado_exterior), position=(-lado_exterior / 2, -lado_exterior / 2)
    )
    curva_interior = generador_forma.rectangle(
        size=(lado_interior, lado_interior), position=(-lado_interior / 2, -lado_interior / 2)
    )
    perfil = generador_forma.profile(
        outer_curve=curva_exterior, inner_curves=[curva_interior], name="AnilloTanquilla"
    )
    representacion = ifcopenshell.api.geometry.add_profile_representation(
        modelo, context=contexto_cuerpo, profile=perfil, depth=h_f
    )
    ifcopenshell.api.geometry.assign_representation(
        modelo, product=tanquilla, representation=representacion
    )
    ifcopenshell.api.geometry.edit_object_placement(modelo, product=tanquilla)

    conjunto_apu = ifcopenshell.api.pset.add_pset(modelo, product=tanquilla, name="Pset_APU")
    ifcopenshell.api.pset.edit_pset(
        modelo,
        pset=conjunto_apu,
        properties={
            "COVENIN_Codigo": CODIGO_COVENIN,
            "Partida_Descripcion": DESCRIPCION_PARTIDA,
            "Unidad": UNIDAD_PARTIDA,
        },
    )

    cantidades_apu = ifcopenshell.api.pset.add_qto(modelo, product=tanquilla, name="Qto_APU")
    ifcopenshell.api.pset.edit_qto(
        modelo, qto=cantidades_apu, properties={"VolumenConcreto": float(volumen)}
    )

    ruta.parent.mkdir(parents=True, exist_ok=True)
    modelo.write(str(ruta))


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--salida",
        default=str(RUTA_POR_DEFECTO),
        help=f"ruta del archivo .ifc de salida (por defecto {RUTA_POR_DEFECTO})",
    )
    analizador.add_argument(
        "--a", type=Decimal, default=A_POR_DEFECTO, help="lado exterior en metros"
    )
    analizador.add_argument("--h", type=Decimal, default=H_POR_DEFECTO, help="altura en metros")
    analizador.add_argument(
        "--e", type=Decimal, default=E_POR_DEFECTO, help="espesor de pared en metros"
    )
    argumentos = analizador.parse_args(argv)

    ruta = Path(argumentos.salida)
    generar(ruta, a=argumentos.a, h=argumentos.h, e=argumentos.e)
    volumen = calcular_volumen_concreto(argumentos.a, argumentos.h, argumentos.e)
    print(f"Modelo IFC escrito en: {ruta}")
    print(
        f"Tanquilla a={argumentos.a} h={argumentos.h} e={argumentos.e} "
        f"-> VolumenConcreto={volumen} m3"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
