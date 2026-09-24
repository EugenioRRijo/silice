"""Adaptador civil sobre modelos IFC (Sesion I3.1, compuerta G1).

Lee un archivo `.ifc` con ifcopenshell y devuelve una cantidad de obra trazable por cada elemento
que declare el conjunto de propiedades `Pset_APU` (`COVENIN_Codigo`, `Partida_Descripcion`,
`Unidad`). La cantidad no se toma de cualquier propiedad numerica: se busca, dentro de los
`IfcElementQuantity` del elemento, la cantidad cuyo tipo IFC corresponde a la `Unidad` declarada
(`IfcQuantityVolume` para m3, `IfcQuantityArea` para m2, `IfcQuantityLength` para m,
`IfcQuantityCount` para pieza) -asi el adaptador no depende de que la cantidad se llame
"VolumenConcreto" o cualquier otro nombre que use el productor del modelo.

El archivo es reemplazable por un export real de Revit/Bonsai (`scripts/generar_tanquilla_ifc.py`
genera uno programatico para la muestra): el adaptador solo lee `Pset_APU` y el
`IfcElementQuantity` asociado, no distingue el productor del modelo (docs/superpowers/specs/
2026-08-31-f1-api-simulador-design.md, seccion 7).

Regla del nucleo cerrado (CLAUDE.md §5): solo se importa `core.contracts`; ifcopenshell (tercero
declarado para civil) y la biblioteca estandar estan libres. `tests/unit/test_arquitectura.py`
(`TERCEROS_POR_ADAPTADOR`) lo vigila con un analisis AST del paquete.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element

from core.contracts import AdaptadorDominio, Dominio, ItemComputo, OrigenTipo
from core.contracts.unidades import normalizar_unidad

_NOMBRE_PSET = "Pset_APU"
_CLAVE_CODIGO = "COVENIN_Codigo"
_CLAVE_DESCRIPCION = "Partida_Descripcion"
_CLAVE_UNIDAD = "Unidad"
_CLAVES_PSET_APU = frozenset({_CLAVE_CODIGO, _CLAVE_DESCRIPCION, _CLAVE_UNIDAD})

# Unica tabla de correspondencia entre la unidad declarada en Pset_APU (ya normalizada por
# core.contracts.unidades) y el tipo de IfcPhysicalSimpleQuantity que debe traer la cantidad.
_CLASE_IFC_POR_UNIDAD: dict[str, str] = {
    "m3": "IfcQuantityVolume",
    "m2": "IfcQuantityArea",
    "m": "IfcQuantityLength",
    "pieza": "IfcQuantityCount",
}


class AdaptadorCivilIFC(AdaptadorDominio):
    """Extrae cantidades de obra civiles de un modelo IFC.

    Recorre `IfcElement` e `IfcBuildingElementProxy` (deduplicados por `GlobalId`: en IFC4
    `IfcBuildingElementProxy` ya es subtipo de `IfcElement`, pero el modelo puede venir de un
    esquema o productor donde no lo sea). Un elemento sin `Pset_APU` no describe una partida del
    presupuesto: se salta. `origen_id` es el `GlobalId` IFC (22 caracteres) del elemento, lo que
    hace trazable cada `ItemComputo` hasta la geometria de origen (regla R1 de verificacion).
    """

    dominio = Dominio.CIVIL

    def extraer(self, fuente: Path | str) -> list[ItemComputo]:
        modelo = ifcopenshell.open(str(fuente))

        elementos: dict[str, object] = {}
        for coleccion in (
            modelo.by_type("IfcElement"),
            modelo.by_type("IfcBuildingElementProxy"),
        ):
            for elemento in coleccion:
                elementos[elemento.GlobalId] = elemento

        items: list[ItemComputo] = []
        for elemento in elementos.values():
            psets = ifcopenshell.util.element.get_psets(elemento, psets_only=True)
            pset_apu = psets.get(_NOMBRE_PSET)
            if pset_apu is None:
                continue
            items.append(self._item_desde_elemento(elemento, pset_apu, fuente))
        return items

    def _item_desde_elemento(
        self, elemento: object, pset_apu: dict[str, object], fuente: Path | str
    ) -> ItemComputo:
        global_id = elemento.GlobalId
        faltantes = _CLAVES_PSET_APU - pset_apu.keys()
        if faltantes:
            raise ValueError(
                f"{_NOMBRE_PSET} del elemento {global_id!r} en {fuente!r} no declara "
                f"{sorted(faltantes)}"
            )

        codigo_partida = str(pset_apu[_CLAVE_CODIGO])
        descripcion = str(pset_apu[_CLAVE_DESCRIPCION])
        unidad_normalizada = normalizar_unidad(str(pset_apu[_CLAVE_UNIDAD]))
        especificaciones = {
            clave: str(valor)
            for clave, valor in pset_apu.items()
            if clave not in _CLAVES_PSET_APU and clave != "id"
        }

        cantidad = self._cantidad_desde_qto(elemento, unidad_normalizada, fuente, global_id)

        return ItemComputo(
            codigo_partida=codigo_partida,
            descripcion=descripcion,
            unidad=unidad_normalizada,
            cantidad=cantidad,
            origen_id=global_id,
            origen_tipo=OrigenTipo.IFC,
            dominio=Dominio.CIVIL,
            especificaciones=especificaciones,
        )

    def _cantidad_desde_qto(
        self, elemento: object, unidad_normalizada: str, fuente: Path | str, global_id: str
    ) -> Decimal:
        clase_esperada = _CLASE_IFC_POR_UNIDAD.get(unidad_normalizada)
        if clase_esperada is None:
            raise ValueError(
                f"el adaptador IFC no sabe que tipo de cantidad corresponde a la unidad "
                f"{unidad_normalizada!r} (elemento {global_id!r} en {fuente!r}); unidades "
                f"soportadas: {sorted(_CLASE_IFC_POR_UNIDAD)}"
            )

        qtos = ifcopenshell.util.element.get_psets(elemento, qtos_only=True, verbose=True)
        candidatos = [
            info["value"]
            for propiedades in qtos.values()
            for info in propiedades.values()
            if isinstance(info, dict) and info.get("class") == clase_esperada
        ]

        if not candidatos:
            raise ValueError(
                f"no se encontro una cantidad {clase_esperada} (unidad {unidad_normalizada!r}) "
                f"para el elemento {global_id!r} en {fuente!r}"
            )
        if len(candidatos) > 1:
            raise ValueError(
                f"cantidad ambigua: {len(candidatos)} valores {clase_esperada} para el elemento "
                f"{global_id!r} en {fuente!r}"
            )
        return Decimal(str(candidatos[0]))
