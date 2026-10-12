"""Requisitos mínimos de un IFC en IDS (Information Delivery Specification, buildingSMART) con
`ifctester` (spec S3 §11.2).

`data/ids/silice_instalaciones.ids` declara lo mínimo que la hoja necesita y la geometría del
IFC no da: espacio con altura (`Qto_SpaceBaseQuantities.Height`), aparato sanitario con diámetro
nominal, tomacorriente con circuito (propiedades `Silice_Hoja.DiametroNominal` y
`Silice_Hoja.Circuito`: un conjunto propio, porque ningún `Pset_` estándar las trae) y tablero con
nombre. `auditar_ids` valida el modelo y entrega, por cada elemento que falla, un ítem del
informe de importación con su `GlobalId`; lo que falte sigue pendiente y R8 lo marca.

`ifctester` se importa DENTRO de la función (extra `ifc`, RP-6): sin el extra la importación del
IFC sigue funcionando y el informe dice «IDS no comprobado: falta el módulo IFC». El IDS solo
cubre IFC4: un IFC2X3 recibe un ítem que lo dice.
"""

from __future__ import annotations

import os
from pathlib import Path

from adapters.espacio.planos.informe import ItemInforme, TipoItem

__all__ = [
    "MENSAJE_SIN_MODULO",
    "RUTA_IDS",
    "auditar_ids",
    "esquema_sin_red",
    "ids_disponible",
]

RUTA_IDS = Path(__file__).resolve().parents[3] / "data" / "ids" / "silice_instalaciones.ids"
MENSAJE_SIN_MODULO = "IDS no comprobado: falta el módulo IFC (extra `ifc`)"
TABLA = "ids"


def ids_disponible() -> bool:
    try:
        import ifctester  # noqa: F401  (extra `ifc`: importación diferida, RP-6)
    except ImportError:
        return False
    return True


def esquema_sin_red(ids) -> None:
    """Fija el esquema XSD del IDS con `allow="local"`. Sin esto, `ifctester` (vía `xmlschema`)
    intenta descargar de internet el esquema XML que importa `ids.xsd` cada vez que abre un
    archivo: lo atrapó la guardia de red de la suite (RV-17) y violaría RF-98 (ninguna
    conexión saliente) en un equipo sin internet. `xmlschema` trae su propia copia."""
    if getattr(ids, "schema", None) is None:
        from xmlschema import XMLSchema

        local = os.path.join(os.path.dirname(ids.__file__), "ids.xsd")
        ids.schema = XMLSchema(local, allow="local")


def _item(mensaje: str, referencia: str = "") -> ItemInforme:
    return ItemInforme(TipoItem.PENDIENTE, TABLA, referencia, "", mensaje)


def auditar_ids(modelo, ruta_ids: Path | str = RUTA_IDS) -> tuple[ItemInforme, ...]:
    """Los ítems del informe por cada elemento de `modelo` (un `ifcopenshell.file`) que no
    cumple un requisito del IDS. Vacío si todo cumple."""
    if not ids_disponible():
        return (_item(MENSAJE_SIN_MODULO),)
    if str(modelo.schema).upper() != "IFC4":
        return (_item(f"IDS no comprobado: solo cubre IFC4 y este archivo es {modelo.schema}"),)
    from ifctester import ids  # importación diferida: extra `ifc`

    try:
        esquema_sin_red(ids)
        especificaciones = ids.open(str(ruta_ids))
        especificaciones.validate(modelo)
    except Exception as error:  # noqa: BLE001 - una librería ajena no tumba la importación (RNF-12)
        motivo = " ".join(str(error).split())
        return (_item(f"IDS no comprobado: {type(error).__name__}: {motivo}"),)
    items: list[ItemInforme] = []
    for especificacion in especificaciones.specifications:
        for requisito in especificacion.requirements:
            for fallo in requisito.failures:
                elemento = fallo["element"]
                global_id = getattr(elemento, "GlobalId", "") or ""
                nombre = (getattr(elemento, "Name", None) or global_id or "(sin nombre)").strip()
                items.append(
                    _item(
                        f"IDS «{especificacion.name}»: {nombre}: {fallo['reason']}", global_id
                    )
                )
    return tuple(sorted(items, key=lambda i: (i.mensaje, i.referencia)))
