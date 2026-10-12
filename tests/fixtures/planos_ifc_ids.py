"""El IFC de oficina de SF5 con los requisitos del IDS de Sílice (S3-5, RF-89).

`oficina_ifc4(con=...)` parte de `planos_ifc.crear_ifc("IFC4")` (que NO trae propiedades) y
agrega, a elección, cada uno de los requisitos de `data/ids/silice_instalaciones.ids`:
altura de los espacios, diámetro del aparato sanitario y circuito de la toma de corriente (el
tablero ya trae su nombre). Programático, como los demás (RNF-09).
"""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.api.pset

from tests.fixtures.planos_ifc import crear_ifc

REQUISITOS = ("altura", "diametro", "circuito")


def oficina_ifc4(con: tuple[str, ...] = REQUISITOS) -> ifcopenshell.file:
    modelo = crear_ifc("IFC4")
    if "altura" in con:
        for espacio in modelo.by_type("IfcSpace"):
            qto = ifcopenshell.api.pset.add_qto(
                modelo, product=espacio, name="Qto_SpaceBaseQuantities"
            )
            ifcopenshell.api.pset.edit_qto(modelo, qto=qto, properties={"Height": 2.8})
    if "diametro" in con:
        for aparato in modelo.by_type("IfcSanitaryTerminal"):
            pset = ifcopenshell.api.pset.add_pset(modelo, product=aparato, name="Silice_Hoja")
            ifcopenshell.api.pset.edit_pset(modelo, pset=pset, properties={"DiametroNominal": 0.05})
    if "circuito" in con:
        for toma in modelo.by_type("IfcOutlet"):
            if toma.PredefinedType == "POWEROUTLET":
                pset = ifcopenshell.api.pset.add_pset(modelo, product=toma, name="Silice_Hoja")
                ifcopenshell.api.pset.edit_pset(modelo, pset=pset, properties={"Circuito": "C1"})
    return modelo
