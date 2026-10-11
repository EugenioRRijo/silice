"""IFC de prueba para la importacion de planos (SF5, RF-51), construidos POR PROGRAMA.

Procedencia declarada: `ifcopenshell.api` (0.8.x) arma una oficina minima, en IFC2X3 y en IFC4, con
espacios de geometria extruida y terminales colocados. NO provienen de Revit, ArchiCAD ni Bonsai:
igual que `data/samples/tanquilla.ifc`, heredan la salvedad de RNF-09 (archivo programatico, no
export de un programa de modelado). Las clases por esquema que usa el importador se
comprueban contra el propio esquema de ifcopenshell en `tests/unit/test_planos_ifc.py`
(ninguna se supone).

Las coordenadas son supuestos declarados del caso, no un plano real. Contenido (en metros):

* `SALA`: rectangulo de 4 x 3 en (0; 0), alto 2,8 (piso en z = 0).
* `BANO`: rectangulo de 2 x 3 en (4; 0), alto 2,8.
* `SALON-L`: forma en L (caja envolvente de 6 x 4 en (10; 0)), alto 3: obliga a la caja envolvente.
* terminales: lavamanos y desague (agua), toma de datos, toma de corriente, luminaria y tablero.
* un muro y una toma audiovisual: elementos que la importacion NO reconoce.
"""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.owner
import ifcopenshell.api.owner.settings
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
import ifcopenshell.api.unit
import numpy as np
from ifcopenshell.util.shape_builder import ShapeBuilder

ESQUEMAS = ("IFC2X3", "IFC4")


def _matriz(x: float, y: float, z: float) -> np.ndarray:
    m = np.eye(4)
    m[:, 3] = (x, y, z, 1.0)
    return m


def _propietario(modelo: ifcopenshell.file) -> None:
    """IFC2X3 exige `OwnerHistory`: usuario y aplicacion ficticios para poder crear entidades."""
    persona = modelo.createIfcPerson(Id="prueba", FamilyName="SF5")
    organizacion = modelo.createIfcOrganization(Name="Pruebas")
    usuario = modelo.createIfcPersonAndOrganization(persona, organizacion)
    aplicacion = modelo.createIfcApplication(organizacion, "0", "planos_ifc.py", "planos_ifc")
    ifcopenshell.api.owner.settings.get_user = lambda _f: usuario
    ifcopenshell.api.owner.settings.get_application = lambda _f: aplicacion


def crear_ifc(esquema: str, milimetros: bool = False) -> ifcopenshell.file:
    """Modelo de oficina en `esquema`. Con `milimetros` las unidades del proyecto son milimetros."""
    escala = 1000.0 if milimetros else 1.0
    modelo = ifcopenshell.api.project.create_file(version=esquema)
    if esquema == "IFC2X3":
        _propietario(modelo)
    proyecto = ifcopenshell.api.root.create_entity(modelo, ifc_class="IfcProject", name="Oficina")
    longitud = ifcopenshell.api.unit.add_si_unit(
        modelo, unit_type="LENGTHUNIT", prefix="MILLI" if milimetros else None
    )
    ifcopenshell.api.unit.assign_unit(modelo, units=[longitud])
    contexto = ifcopenshell.api.context.add_context(modelo, context_type="Model")
    cuerpo = ifcopenshell.api.context.add_context(
        modelo,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=contexto,
    )
    sitio = ifcopenshell.api.root.create_entity(modelo, ifc_class="IfcSite", name="Sitio")
    edificio = ifcopenshell.api.root.create_entity(modelo, ifc_class="IfcBuilding", name="Edificio")
    nivel = ifcopenshell.api.root.create_entity(modelo, ifc_class="IfcBuildingStorey", name="N0")
    ifcopenshell.api.aggregate.assign_object(modelo, products=[sitio], relating_object=proyecto)
    ifcopenshell.api.aggregate.assign_object(modelo, products=[edificio], relating_object=sitio)
    ifcopenshell.api.aggregate.assign_object(modelo, products=[nivel], relating_object=edificio)
    forma = ShapeBuilder(modelo)

    def colocar(producto, x: float, y: float, z: float) -> None:
        ifcopenshell.api.geometry.edit_object_placement(
            modelo,
            product=producto,
            matrix=_matriz(x, y, z),  # la API recibe metros
        )

    def espacio(
        nombre: str, x0: float, y0: float, largo: float, ancho: float, alto: float, en_l=False
    ):
        e = ifcopenshell.api.root.create_entity(modelo, ifc_class="IfcSpace", name=nombre)
        ifcopenshell.api.aggregate.assign_object(modelo, products=[e], relating_object=nivel)
        if en_l:  # en L: el cuadrado de arriba a la derecha queda vacio
            puntos = [
                (0.0, 0.0),
                (largo, 0.0),
                (largo, ancho / 2),
                (largo / 2, ancho / 2),
                (largo / 2, ancho),
                (0.0, ancho),
            ]
            curva = forma.polyline([(px * escala, py * escala) for px, py in puntos], closed=True)
            perfil = forma.profile(curva, name="L")
        else:
            # `position` es la esquina: el rectangulo queda con su rincon en el origen del espacio
            curva = forma.rectangle(size=(largo * escala, ancho * escala), position=(0.0, 0.0))
            perfil = forma.profile(curva, name="R")
        representacion = ifcopenshell.api.geometry.add_profile_representation(
            modelo,
            context=cuerpo,
            profile=perfil,
            depth=alto,  # profundidad en metros (SI)
        )
        ifcopenshell.api.geometry.assign_representation(
            modelo, product=e, representation=representacion
        )
        colocar(e, x0, y0, 0.0)
        return e

    espacio("SALA", 0.0, 0.0, 4.0, 3.0, 2.8)
    espacio("BANO", 4.0, 0.0, 2.0, 3.0, 2.8)
    espacio("SALON-L", 10.0, 0.0, 6.0, 4.0, 3.0, en_l=True)

    def terminal(clase_v4: str, nombre: str, x: float, y: float, z: float, tipo: str | None = None,
                 predefinido: str | None = None, clase_tipo: str | None = None):  # fmt: skip
        """IFC4: la clase propia (`clase_v4`). IFC2X3: `IfcFlowTerminal` con su `IfcXxxType`."""
        if esquema == "IFC4":
            e = ifcopenshell.api.root.create_entity(
                modelo,
                ifc_class=clase_v4,
                name=nombre,
                predefined_type=predefinido or "NOTDEFINED",
            )
        else:
            e = ifcopenshell.api.root.create_entity(
                modelo, ifc_class="IfcFlowTerminal", name=nombre
            )
            if clase_tipo:
                t = ifcopenshell.api.root.create_entity(
                    modelo,
                    ifc_class=clase_tipo,
                    name=f"tipo {nombre}",
                    predefined_type=predefinido or "NOTDEFINED",
                )
                ifcopenshell.api.type.assign_type(modelo, related_objects=[e], relating_type=t)
        ifcopenshell.api.spatial.assign_container(modelo, products=[e], relating_structure=nivel)
        colocar(e, x, y, z)
        return e

    terminal("IfcSanitaryTerminal", "lavamanos", 1.0, 0.0, 0.8, predefinido="WASHHANDBASIN",
             clase_tipo="IfcSanitaryTerminalType")  # fmt: skip
    if esquema == "IFC4":  # IFC2X3 no tiene IfcWasteTerminal: el desague no se modela
        terminal("IfcWasteTerminal", "desague", 5.0, 1.5, 0.0, predefinido="FLOORTRAP",
                 clase_tipo="IfcWasteTerminalType")  # fmt: skip
    terminal("IfcOutlet", "toma de datos", 3.5, 2.0, 0.3,
             predefinido="DATAOUTLET" if esquema == "IFC4" else "COMMUNICATIONSOUTLET",
             clase_tipo="IfcOutletType")  # fmt: skip
    terminal("IfcOutlet", "toma de corriente", 2.0, 3.0, 0.3, predefinido="POWEROUTLET",
             clase_tipo="IfcOutletType")  # fmt: skip
    terminal("IfcOutlet", "toma audiovisual", 2.5, 3.0, 0.3, predefinido="AUDIOVISUALOUTLET",
             clase_tipo="IfcOutletType")  # fmt: skip
    terminal("IfcLightFixture", "luminaria", 2.0, 1.5, 2.8, clase_tipo="IfcLightFixtureType")
    if esquema == "IFC4":
        terminal("IfcElectricDistributionBoard", "tablero", 0.1, 2.9, 1.5,
                 predefinido="DISTRIBUTIONBOARD")  # fmt: skip
    else:
        tablero = ifcopenshell.api.root.create_entity(
            modelo,
            ifc_class="IfcElectricDistributionPoint",
            name="tablero",
            predefined_type=None,
        )
        tablero.DistributionPointFunction = "DISTRIBUTIONBOARD"
        ifcopenshell.api.spatial.assign_container(
            modelo, products=[tablero], relating_structure=nivel
        )
        colocar(tablero, 0.1, 2.9, 1.5)

    muro = ifcopenshell.api.root.create_entity(modelo, ifc_class="IfcWall", name="muro")
    ifcopenshell.api.spatial.assign_container(modelo, products=[muro], relating_structure=nivel)
    colocar(muro, 0.0, 0.0, 0.0)
    return modelo
