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
`IfcElementQuantity` asociado, no distingue el productor del modelo (spec
2026-08-31-f1-api-simulador-design.md, seccion 7).

Regla del nucleo cerrado (NORMAS.md §5): solo se importa `core.contracts`; ifcopenshell (tercero
declarado para civil) y la biblioteca estandar estan libres. `tests/unit/test_arquitectura.py`
(`TERCEROS_POR_ADAPTADOR`) lo vigila con un analisis AST del paquete.
"""

from __future__ import annotations

from codecs import BOM_UTF8
from decimal import Decimal
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element
from ifcopenshell import ifcopenshell_wrapper

from core.contracts import AdaptadorDominio, Dominio, ItemComputo, OrigenTipo
from core.contracts.unidades import normalizar_unidad

# Palabra con que abre todo archivo IFC en formato STEP (ISO 10303-21, «ISO-10303-21;»). Un
# archivo que no empieza asi no es un modelo que ifcopenshell pueda leer.
_CABECERA_STEP = b"ISO-10303-21"

# Por que ifcopenshell no pudo abrir un archivo STEP, segun el estado de `ifcopenshell_wrapper.open`
# (los mismos cuatro estados que `ifcopenshell.file.__init__` traduce a excepciones).
_ESTADO = ifcopenshell_wrapper.file_open_status
_MOTIVO_POR_ESTADO: dict[int, str] = {
    _ESTADO.READ_ERROR: "no se pudo abrir para lectura",
    _ESTADO.NO_HEADER: "su cabecera STEP no se pudo interpretar",
    _ESTADO.UNSUPPORTED_SCHEMA: "declara un esquema IFC que ifcopenshell no soporta",
    _ESTADO.INVALID_SYNTAX: "tiene errores de sintaxis STEP",
}

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
        modelo = _abrir_modelo(Path(fuente))

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
                f"{_NOMBRE_PSET} del elemento {global_id!r} en {Path(fuente).name!r} no declara "
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
                f"{unidad_normalizada!r} (elemento {global_id!r} en {Path(fuente).name!r}); "
                f"unidades soportadas: {sorted(_CLASE_IFC_POR_UNIDAD)}"
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
                f"para el elemento {global_id!r} en {Path(fuente).name!r}"
            )
        if len(candidatos) > 1:
            raise ValueError(
                f"cantidad ambigua: {len(candidatos)} valores {clase_esperada} para el elemento "
                f"{global_id!r} en {Path(fuente).name!r}"
            )
        return Decimal(str(candidatos[0]))


def _abrir_modelo(ruta: Path) -> ifcopenshell.file:
    """Abre el modelo IFC o lo rechaza con `ValueError` nombrando el archivo (UC-01, flujo 2a).

    Solo lee el formato STEP (`.ifc`); la API y la interfaz solo envian aqui archivos `.ifc`, asi
    que ifcXML e ifcZIP no llegan. El rechazo es siempre el `ValueError` que la API traduce a 422
    y la pagina de elaboracion muestra, nunca un `ifcopenshell.Error` u `OSError`, que la API no
    maneja (INV-089). Dos casos:

    - **No es STEP** (binario, vacio, un CSV con extension `.ifc`): no empieza con la cabecera
      `ISO-10303-21`, y se rechaza sin pasar por ifcopenshell.
    - **STEP que ifcopenshell no puede abrir** (cabecera danada, esquema no soportado): se abre
      con `ifcopenshell_wrapper.open`, la misma llamada con que `ifcopenshell.open` empieza, y se
      rechaza si su estado no es bueno, **antes** de construir el `ifcopenshell.file`. Con
      `ifcopenshell.open`, ifcopenshell 0.8.5 lanza el error desde `file.__init__` sin haber
      registrado el objeto, y su `__del__` lanza despues un `KeyError` que Python solo puede
      reportar como excepcion no atrapable (con `-W error`, rompe la prueba que este corriendo
      cuando el recolector lo libere).

    Limite declarado: el analizador de ifcopenshell es tolerante con el cuerpo. Un archivo truncado
    o con lineas de basura despues de una cabecera valida se abre sin error y entrega los elementos
    que alcanzo a leer; eso no se detecta aqui.
    """
    with open(ruta, "rb") as archivo:
        inicio = archivo.read(64)
    if not inicio.removeprefix(BOM_UTF8).lstrip().startswith(_CABECERA_STEP):
        raise ValueError(
            f"el archivo {ruta.name!r} es ilegible: no es un modelo IFC (no empieza con la "
            f"cabecera {_CABECERA_STEP.decode()} del formato STEP)"
        )
    datos = ifcopenshell_wrapper.open(str(ruta.absolute()))
    estado = datos.good()
    if not estado:
        motivo = _MOTIVO_POR_ESTADO.get(estado.value(), f"estado {estado.value()} de ifcopenshell")
        raise ValueError(f"el archivo {ruta.name!r} es ilegible como modelo IFC: {motivo}")
    return ifcopenshell.file(datos)
